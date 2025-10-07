// static/js/snapshot_candidate.js
// Compares storySnapshots (backend) vs userSnapshots (user edits) and writes candidateSnapshot to localStorage.
// Exposed API: SnapshotCandidate.generate(), SnapshotCandidate.get(), SnapshotCandidate.clear()
// Inspect the result with window.SnapshotCandidate.get() or by reading localStorage.getItem('candidateSnapshot')

(function () {
  'use strict';

  const STORY_KEY = 'storySnapshots';
  const USER_KEY = 'userSnapshots';
  const CANDIDATE_KEY = 'candidateSnapshot';

  // Helpers
  function safeParse(raw) {
    try {
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      console.warn('SnapshotCandidate: failed to parse JSON', e);
      return [];
    }
  }

  function getLatestSnapshotArray(key) {
    const raw = localStorage.getItem(key);
    const arr = safeParse(raw);
    if (!Array.isArray(arr) || arr.length === 0) return null;
    return arr[arr.length - 1];
  }

  // Parse fields array (from snapshot.fields) into a map of selectors -> array of paragraph objects
  // Each paragraph object: { paragraphId, storyId, html, text }
  function parseFieldsToParagraphs(fields) {
    if (!Array.isArray(fields)) return {};
    const out = {};
    for (const f of fields) {
      const sel = f.selector || 'unknown';
      const html = f.html || '';
      // create a DOM fragment to parse p elements safely
      const container = document.createElement('div');
      container.innerHTML = html;
      const ps = Array.from(container.querySelectorAll('p'));
      out[sel] = ps.map(p => {
        // read dataset attributes, allow numeric and string ids
        const paragraphId = p.dataset && p.dataset.paragraphId !== undefined ? String(p.dataset.paragraphId) : null;
        const storyId = p.dataset && p.dataset.storyId !== undefined ? String(p.dataset.storyId) : null;
        // trim text content for reliable comparison
        const text = p.textContent != null ? p.textContent : '';
        return {
          paragraphId,
          storyId,
          html: p.outerHTML,
          text: text.replace(/\u00A0/g, ' ') // normalize non-breaking spaces
        };
      });
    }
    return out;
  }

  // Build lookup maps by paragraphId (if present) or by synthetic index if no id
  function makeParagraphMap(paragraphs) {
    // returns { byId: Map, byIndex: Map, list: paragraphs }
    const byId = new Map();
    const byIndex = new Map();
    (paragraphs || []).forEach((p, i) => {
      if (p.paragraphId !== null && p.paragraphId !== undefined) {
        byId.set(p.paragraphId, p);
      }
      byIndex.set(String(i), p);
    });
    return { byId, byIndex, list: paragraphs || [] };
  }

  // Compare two paragraph maps and produce candidate entries for differences.
  // userMap takes precedence: if a paragraph exists in user but not story => addition (include user content).
  // If paragraph exists in story but not user => DELETE.
  // If both exist and text differs => replace with user text.
  function compareField(storyParagraphs = [], userParagraphs = []) {
    const story = makeParagraphMap(storyParagraphs);
    const user = makeParagraphMap(userParagraphs);

    const result = [];

    // First, iterate through story paragraphs to detect deletions or modifications
    story.list.forEach((sP, idx) => {
      const id = sP.paragraphId;
      let uP = null;
      if (id && user.byId.has(id)) {
        uP = user.byId.get(id);
      } else if (!id) {
        // fallback: try match by index if no paragraphId
        const byIdx = user.byIndex.get(String(idx));
        if (byIdx) uP = byIdx;
      }

      if (!uP) {
        // paragraph existed in story but missing in user => mark DELETE
        result.push({
          action: 'delete',
          paragraphId: sP.paragraphId,
          storyId: sP.storyId,
          originalText: sP.text,
          selector: null // caller should attach selector
        });
      } else {
        // both exist: compare text trim-normalized
        if (!textEquals(sP.text, uP.text)) {
          // user changed content => user takes precedence
          result.push({
            action: 'update',
            paragraphId: uP.paragraphId || sP.paragraphId,
            storyId: uP.storyId || sP.storyId,
            originalText: sP.text,
            newText: uP.text,
            selector: null
          });
        }
      }
    });

    // Next, find paragraphs present in user but not in story (additions)
    user.list.forEach((uP, idx) => {
      const id = uP.paragraphId;
      let sP = null;
      if (id && story.byId.has(id)) {
        sP = story.byId.get(id);
      } else if (!id) {
        const byIdx = story.byIndex.get(String(idx));
        if (byIdx) sP = byIdx;
      }
      if (!sP) {
        // user-created paragraph that does not exist in story => addition
        result.push({
          action: 'insert',
          paragraphId: uP.paragraphId,
          storyId: uP.storyId,
          newText: uP.text,
          selector: null
        });
      }
    });

    return result;
  }

  function textEquals(a, b) {
  // Normalize whitespace, strip leading ">> ", and trim before comparison
  const norm = s => {
    if (s == null) return '';
    return String(s)
      .replace(/\u00A0/g, ' ')
      .replace(/\s+/g, ' ')
      .replace(/^>>\s+/, '')
      .trim();
  };
  return norm(a) === norm(b);
}


  // Main generator: reads latest story and user snapshots and writes candidateSnapshot
  function generateCandidate() {
    const storySnap = getLatestSnapshotArray(STORY_KEY);
    const userSnap = getLatestSnapshotArray(USER_KEY);

    // Build per-selector paragraph lists
    const storyFields = storySnap ? parseFieldsToParagraphs(storySnap.fields) : {};
    const userFields = userSnap ? parseFieldsToParagraphs(userSnap.fields) : {};

    // Collect selectors to consider (union of both)
    const selectors = new Set(Object.keys(storyFields).concat(Object.keys(userFields)));

    const candidate = {
      ts: new Date().toISOString(),
      diffs: [] // each diff: { selector, action, paragraphId, storyId, originalText?, newText? }
    };

    selectors.forEach(sel => {
      const sList = storyFields[sel] || [];
      const uList = userFields[sel] || [];

      const diffs = compareField(sList, uList);
      diffs.forEach(d => {
        d.selector = sel;
        // If delete action, set newText explicitly to "DELETE" per requirements
        if (d.action === 'delete') d.newText = 'DELETE';
        candidate.diffs.push(d);
      });
    });

    // Remove diffs where the update/insert's newText exactly matches originalText (shouldn't really happen)
    candidate.diffs = candidate.diffs.filter(d => {
      if (d.action === 'delete') return true;
      if (d.action === 'insert') return (d.newText || '').trim() !== '';
      if (d.action === 'update') return !textEquals(d.originalText, d.newText);
      return true;
    });

    // If there are no diffs, remove diffs array for compactness
    if (!candidate.diffs.length) {
      localStorage.removeItem(CANDIDATE_KEY);
      return null;
    }

    // Save to localStorage
    try {
      localStorage.setItem(CANDIDATE_KEY, JSON.stringify(candidate));
    } catch (e) {
      console.warn('SnapshotCandidate: failed to save candidate', e);
    }
    return candidate;
  }

  function getCandidate() {
    const raw = localStorage.getItem(CANDIDATE_KEY);
    return safeParse(raw) || null;
  }

  function clearCandidate() {
    localStorage.removeItem(CANDIDATE_KEY);
  }

  // Expose API
  window.SnapshotCandidate = {
    generate: generateCandidate,
    get: getCandidate,
    clear: clearCandidate,
    _internals: { // exported only for debugging in-console if needed
      parseFieldsToParagraphs,
      compareField,
      textEquals
    }
  };

})();
