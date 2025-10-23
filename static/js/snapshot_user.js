// static/js/snapshot_user.js
// Behavior: On user edit: captures a snapshot of '#story-history', '.mid-synopsis-area', '.long-synopsis-area'
// Save to localStorage as userSnapshots
// You can force a snapshot programmatically with window.UserSnapshot.pushNow({ reason: 'your-reason' })
// Use window.UserSnapshot.listSnapshots() in the console to inspect snapshots and
// localStorage.getItem('userSnapshots') to view raw JSON.

// Configuration
(function () {
  'use strict';

  const FIELD_SELECTORS = [
    '#story-history',
    '.mid-synopsis-area',
    '.long-synopsis-area'
  ];
  const LOCAL_STORAGE_KEY = 'userSnapshots';
  const MAX_SNAPSHOTS = 2;
  const DEBOUNCE_MS = 700;

  // Internal state
  let snapshots = loadSnapshots();
  let debounceTimer = null;

  // Helpers
  function nowIso() {
    return new Date().toISOString();
  }

  function loadSnapshots() {
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (err) {
      console.warn('UserSnapshot: failed to parse storage, starting fresh', err);
      return [];
    }
  }

  function saveSnapshots() {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(snapshots));
      SnapshotCandidate.generate()
    } catch (err) {
      console.warn('UserSnapshot: failed to save snapshots', err);
    }
  }

  function trimSnapshots() {
    if (snapshots.length > MAX_SNAPSHOTS) {
      snapshots = snapshots.slice(-MAX_SNAPSHOTS);
    }
  }

  function readFields() {
    return FIELD_SELECTORS.map(sel => {
      const el = document.querySelector(sel);
      return {
        selector: sel,
        html: el ? el.innerHTML : null,
        text: el ? el.innerText : null
      };
    });
  }

  function buildSnapshot(meta = {}) {
    return Object.assign({
      ts: nowIso(),
      fields: readFields()
    }, meta);
  }

  function pushSnapshot(meta) {
    const snap = buildSnapshot(meta);
    const last = snapshots.length ? snapshots[snapshots.length - 1] : null;
    if (last && JSON.stringify(last.fields) === JSON.stringify(snap.fields)) {
      last.ts = snap.ts; // refresh timestamp for identical content
      if (meta && Object.keys(meta).length) Object.assign(last, meta);
      saveSnapshots();
      return;
    }
    snapshots.push(snap);
    trimSnapshots();
    saveSnapshots();
  }

  // Debounced entry point for user edits
  function scheduleSnapshot(meta) {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      pushSnapshot(meta);
      debounceTimer = null;
    }, DEBOUNCE_MS);
  }

  // Event handlers
  function onInputEvent(e) {
    // Only treat this as a user edit if target is one of our fields (protect against bubbling)
    const target = e.target;
    if (!target) return;
    if (!FIELD_SELECTORS.some(sel => target.matches && target.matches(sel))) return;
    scheduleSnapshot({ trigger: 'input', selector: selectorForElement(target) });
  }

  function onBlurEvent(e) {
    const target = e.target;
    if (!target) return;
    if (!FIELD_SELECTORS.some(sel => target.matches && target.matches(sel))) return;
    // immediate snapshot on blur
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    pushSnapshot({ trigger: 'blur', selector: selectorForElement(target) });
  }

  function onKeydownEvent(e) {
    // Ctrl/Cmd+S triggers an immediate snapshot
    const isSaveCombo = (e.ctrlKey || e.metaKey) && e.key && e.key.toLowerCase() === 's';
    if (!isSaveCombo) return;
    // find focused element and snapshot if it's one of ours
    const active = document.activeElement;
    if (!active) return;
    if (!FIELD_SELECTORS.some(sel => active.matches && active.matches(sel))) return;
    e.preventDefault();
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
    pushSnapshot({ trigger: 'manual-save', selector: selectorForElement(active) });
  }

  function selectorForElement(el) {
    for (const sel of FIELD_SELECTORS) {
      if (el.matches && el.matches(sel)) return sel;
    }
    return null;
  }

  // MutationObserver fallback: detect user-driven text changes where possible (covers paste, execCommand, etc.)
  function installObserver() {
    const observedEls = FIELD_SELECTORS.map(sel => document.querySelector(sel)).filter(Boolean);
    if (!observedEls.length) return;
    const mo = new MutationObserver(mutations => {
      // If any mutation appears on one of the observed elements and it's not from backend update,
      // we schedule a snapshot with a 'mutation' trigger.
      let triggered = false;
      let selector = null;
      for (const m of mutations) {
        const target = m.target && (m.target.closest ? m.target.closest(FIELD_SELECTORS.join(',')) : null);
        if (!target) continue;
        // If backend marker exists, skip (we only want user edits here)
        if (target.dataset && target.dataset.backendUpdated === 'true') continue;
        triggered = true;
        selector = selector || selectorForElement(target);
        break;
      }
      if (triggered) scheduleSnapshot({ trigger: 'mutation', selector });
    });

    observedEls.forEach(el => mo.observe(el, { childList: true, subtree: true, characterData: true }));
  }

  // Attach listeners to each field (when DOM ready)
  function attachListeners() {
    FIELD_SELECTORS.forEach(sel => {
      const el = document.querySelector(sel);
      if (!el) return;
      // contenteditable fields usually emit 'input' on user changes; also listen for 'paste'
      el.addEventListener('input', onInputEvent, { passive: true });
      el.addEventListener('paste', () => scheduleSnapshot({ trigger: 'paste', selector: sel }), { passive: true });
      el.addEventListener('blur', onBlurEvent, { passive: true });
    });
    // global keydown for manual save
    document.addEventListener('keydown', onKeydownEvent, true);

    // fallback observer
    installObserver();
  }

  // Public API
  window.UserSnapshot = {
    listSnapshots: () => snapshots.slice(),
    clearSnapshots: () => {
      snapshots = [];
      saveSnapshots();
    },
    pushNow: (meta) => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
        debounceTimer = null;
      }
      pushSnapshot(meta || { trigger: 'manual' });
    },
    getKey: () => LOCAL_STORAGE_KEY
  };

  // Init
  document.addEventListener('DOMContentLoaded', () => {
    attachListeners();
  });

})();
