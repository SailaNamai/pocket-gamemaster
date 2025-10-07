// buttons.js

const statusEl    = document.getElementById('status-indicator');
const historyEl   = document.getElementById('story-history');
const actionEl    = document.getElementById('player-action');
const continueBtn = document.getElementById('continue-btn');
const redoBtn     = document.getElementById('redo-btn');
const forceBtn    = document.getElementById('force-btn');

// Lock/unlock the buttons with a bool call True=Lock, False=Unlock
function button_lock(shouldLock) {
  const lock = Boolean(shouldLock);
  const elements = [continueBtn, redoBtn, forceBtn];

  elements.forEach(btn => {
    if (!btn) return;
    btn.disabled = lock;
    btn.setAttribute('aria-disabled', String(lock));
    btn.classList.toggle('locked', lock);
  });

  if (actionEl) {
    if (lock) actionEl.setAttribute('disabled', 'disabled');
    else actionEl.removeAttribute('disabled');
  }

  if (lock) statusEl.innerText = '…loading';
}

// keep a single controller so we never run concurrent summarize requests
let summarizeController = null;
async function callSummarize(signalOrFlag) {
  // allow callers to explicitly cancel an in-flight summarize
  if (signalOrFlag === 'abort') {
    if (summarizeController) {
      summarizeController.abort();
      summarizeController = null;
    }
    return;
  }

  // if a summarize is already running, do nothing
  if (summarizeController) return;

  // start a new summarize run
  summarizeController = new AbortController();
  const { signal } = summarizeController;

  // show locked UI while summarizing
  button_lock(true);
  if (statusEl) statusEl.innerText = '…summarizing';

  try {
    const res = await fetch('/api/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    // server returns plain text "backend_done"
    const text = await res.text();
    console.log('summarize response:', text);

    if (statusEl) statusEl.innerText = '';
    return text;
  } catch (err) {
    if (err.name === 'AbortError') {
      console.warn('summarize aborted');
      if (statusEl) statusEl.innerText = 'summarize aborted';
      return;
    }
    console.error('callSummarize failed', err);
    if (statusEl) statusEl.innerText = 'summarize error';
    throw err;
  } finally {
    // always unlock UI and clear controller when finished
    summarizeController = null;
    button_lock(false);
  }
}

async function callAction(endpoint, payload = {}) {
  button_lock(true)
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const json = await res.json();
    console.log('API response:', json);

    // 1) Render an array of paragraphs (player_action / force)
    if (Array.isArray(json.paragraphs)) {
      clearAndRender(
        json.paragraphs,
        json.mid_memory,
        json.long_memory
      );
      styleStoryHistory();
    }

    // 2) Render a single appended paragraph ( new / continue / redo)
    else if (json.story) {
      const { id, content, story_id } = json.story;
      const pEl = document.createElement('p');
      pEl.dataset.paragraphId = id;
      pEl.dataset.storyId     = story_id;
      pEl.textContent         = content;
      historyEl.appendChild(pEl);
      actionEl.value = '';
      styleStoryHistory();
      window.Snapshot.notifyBackendUpdate('#story-history');
    }

    // 3) Update Mid-Term Memory
    if (json.mid_memory !== undefined) {
      document.querySelector('.mid-synopsis-area').innerHTML = json.mid_memory;
      window.Snapshot.notifyBackendUpdate('.mid-synopsis-area');
    }

    // 4) Update Long-Term Memory
    if (json.long_memory !== undefined) {
      document.querySelector('.long-synopsis-area').innerHTML = json.long_memory;
      window.Snapshot.notifyBackendUpdate('.long-synopsis-area');
    }
  }
  finally {
    // Call the summarize pipeline.
    callSummarize("start_summarize");
  }
}

function handleContinue() {
  const storyText   = historyEl.innerText.trim();
  const playerInput = actionEl.value.trim();

  // Read candidate from localStorage
  let candidate = null;
  try {
    const raw = localStorage.getItem('candidateSnapshot');
    candidate = raw ? JSON.parse(raw) : null;
  } catch (e) {
    console.warn('Failed to parse candidateSnapshot', e);
    candidate = null;
  }

  const endpoint = !storyText ? '/api/new' :
                   playerInput ? '/api/player_action' :
                   '/api/continue';

  const payload = {};
  if (playerInput) payload.action = playerInput;

  // Attach candidate only if present and non-empty
  if (candidate && Array.isArray(candidate.diffs) && candidate.diffs.length) {
    // Keep the payload shape simple and explicit
    payload.candidate = candidate;
  }

  callAction(endpoint, payload)
    .then(res => {
      // On success: clear candidate so we don't re-send the same diff
      if (res && res.ok) {
        localStorage.removeItem('candidateSnapshot');
      }
      return res;
    })
    .catch(err => {
      // keep candidateSnapshot so user can retry; optionally surface an error
      console.error('callAction failed', err);
      throw err;
    });
}

function handleRedo() {
  // find existing paragraphs
  const paragraphs = historyEl.querySelectorAll('p[data-paragraph-id]');

  // If there are none, start a new story
  if (!paragraphs.length) {
    const payload = buildRedoPayload();
    // snapshot current (empty) state after removal attempt
    if (window.UserSnapshot && typeof window.UserSnapshot.pushNow === 'function') {
      window.UserSnapshot.pushNow({ reason: 'redo-empty' });
    }
    callAction('/api/new', payload)
      .then(res => {
        if (res && res.ok) localStorage.removeItem('candidateSnapshot');
        return res;
      })
      .catch(err => {
        console.error('callAction failed', err);
        throw err;
      });
    return;
  }

  // remove the last paragraph
  const lastPara = paragraphs[paragraphs.length - 1];
  lastPara.remove();

  // Immediately snapshot the user-visible state after removal
  if (window.UserSnapshot && typeof window.UserSnapshot.pushNow === 'function') {
    window.UserSnapshot.pushNow({ reason: 'redo-remove-last-paragraph' });
  }

  // Decide endpoint based on the new last paragraph (after removal)
  const remaining = historyEl.querySelectorAll('p[data-paragraph-id]');
  let endpoint;
  if (!remaining.length) {
    endpoint = '/api/new';
  } else {
    const newLast = remaining[remaining.length - 1];
    const storyId = newLast.dataset.storyId || '';
    endpoint = storyId === 'continue_with_UserAction' ? '/api/player_action' : '/api/continue';
  }

  // Build payload and include candidateSnapshot if present
  const payload = buildRedoPayload();

  // Call API and clear candidate on success
  callAction(endpoint, payload)
    .then(res => {
      if (res && res.ok) localStorage.removeItem('candidateSnapshot');
      return res;
    })
    .catch(err => {
      console.error('callAction failed', err);
      throw err;
    });
}

// helper to build payload (keeps handleRedo tidy and matches handleContinue behavior)
function buildRedoPayload() {
  const payload = {};
  const playerInput = actionEl.value && actionEl.value.trim();
  if (playerInput) payload.action = playerInput;

  try {
    const raw = localStorage.getItem('candidateSnapshot');
    const candidate = raw ? JSON.parse(raw) : null;
    if (candidate && Array.isArray(candidate.diffs) && candidate.diffs.length) {
      payload.candidate = candidate;
    }
  } catch (e) {
    console.warn('Failed to parse candidateSnapshot', e);
  }

  return payload;
}

function handleForce() {
  callAction('/api/force', { story: historyEl.innerText.trim() });
}

continueBtn.addEventListener('click', handleContinue);
redoBtn    .addEventListener('click', handleRedo);
forceBtn   .addEventListener('click', handleForce);