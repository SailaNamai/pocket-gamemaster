// buttons.js
// -----------------------------------------------------------------------------
// This file manages UI button states and orchestrates calls to the backend API
// endpoints: new story, continue, redo, force, summarize, and evaluation.
// It ensures that only one summarize request runs at a time, and that the
// evaluation pipeline is executed before any player_action request.
// -----------------------------------------------------------------------------

// Cache DOM elements for quick access
const statusEl    = document.getElementById('status-indicator');
const historyEl   = document.getElementById('story-history');
const actionEl    = document.getElementById('player-action');
const continueBtn = document.getElementById('continue-btn');
const redoBtn     = document.getElementById('redo-btn');
const forceBtn    = document.getElementById('force-btn');

// -----------------------------------------------------------------------------
// Button Locking
// -----------------------------------------------------------------------------

/**
 * Lock/unlock the buttons and input field.
 * @param {boolean} shouldLock - true = lock, false = unlock
 */
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

  if (lock && statusEl) statusEl.innerText = '…loading';
}

// -----------------------------------------------------------------------------
// Summarize Pipeline
// -----------------------------------------------------------------------------

// Keep a single controller so we never run concurrent summarize requests
let summarizeController = null;

/**
 * Call the summarize API, with support for aborting.
 * @param {"abort"|"start_summarize"} signalOrFlag
 */
async function callSummarize(signalOrFlag) {
  // Allow callers to explicitly cancel an in‑flight summarize
  if (signalOrFlag === 'abort') {
    if (summarizeController) {
      summarizeController.abort();
      summarizeController = null;
    }
    return;
  }

  // If a summarize is already running, do nothing
  if (summarizeController) return;

  // Start a new summarize run
  summarizeController = new AbortController();
  const { signal } = summarizeController;

  // Show locked UI while summarizing
  button_lock(true);
  if (statusEl) statusEl.innerText = '…summarizing';

  try {
    const res = await fetch('/api/summarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    // Server returns plain text "backend_done"
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
    // Always unlock UI and clear controller when finished
    summarizeController = null;
    button_lock(false);
  }
}

// -----------------------------------------------------------------------------
// Payload Builder
// -----------------------------------------------------------------------------

/**
 * Build a payload that always contains an `action` field (empty string if no
 * user input) and optionally a `candidate` snapshot.
 * This guarantees that player_action requests are persisted.
 */
function buildBasePayload() {
  const payload = {};

  // Player‑action text – always present (may be empty)
  const playerInput = actionEl?.value?.trim() ?? '';
  payload.action = playerInput;

  // Candidate snapshot
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

// -----------------------------------------------------------------------------
// Core Action Pipeline
// -----------------------------------------------------------------------------

/**
 * Generic API call handler for story actions.
 * Handles rendering paragraphs and updating memory areas.
 */
async function callAction(endpoint, payload = {}) {
  button_lock(true);
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const json = await res.json();
    console.log('API response:', json);

    // Render a single paragraph
    if (json.story) {
      const { id, content, story_id } = json.story;
      const pEl = document.createElement('p');
      pEl.dataset.paragraphId = id;
      pEl.dataset.storyId     = story_id;
      pEl.textContent         = content;
      historyEl.appendChild(pEl);
      if (actionEl) actionEl.value = '';
      styleStoryHistory();
      window.Snapshot.notifyBackendUpdate('#story-history');
    }

    // Update Mid‑Term Memory
    if (json.mid_memory !== undefined) {
      document.querySelector('.mid-synopsis-area').innerHTML = json.mid_memory;
      window.Snapshot.notifyBackendUpdate('.mid-synopsis-area');
    }

    // Update Long‑Term Memory
    if (json.long_memory !== undefined) {
      document.querySelector('.long-synopsis-area').innerHTML = json.long_memory;
      window.Snapshot.notifyBackendUpdate('.long-synopsis-area');
    }

    return res; // return raw response for caller
  } finally {
    // Call the summarize pipeline after every action
    callSummarize('start_summarize');
  }
}

/**
 * Evaluation + Action wrapper.
 * Ensures evaluation runs before any player_action request.
 */
async function callEvalThenAction(endpoint, payload = {}) {
  button_lock(true)
  try {
    // ---- Evaluation -------------------------------------------------
    const evalRes = await fetch('/api/eval', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)   // payload includes `action`
    });
    if (!evalRes.ok) throw new Error(`Eval HTTP ${evalRes.status}`);
    const evalJson = await evalRes.json();

    // Depending on your backend, evalJson may look like:
    // { action: { id, content, story_id, outcome } }
    const { action } = evalJson;
    console.log('Eval outcome:', action);

    if (statusEl) statusEl.innerText = `Outcome: ${action.outcome}`;

    // ---- Render evaluation paragraph --------------------------------
    if (action) {
      const { id, content, story_id, outcome } = action;
      const pEl = document.createElement('p');
      pEl.dataset.paragraphId = id;
      pEl.dataset.storyId     = story_id;
      pEl.dataset.outcome     = outcome;

      // This makes the browser show the outcome on hover
      pEl.title = `${outcome}`;

      pEl.textContent = content;
      historyEl.appendChild(pEl);
      if (actionEl) actionEl.value = '';
      styleStoryHistory();
      window.Snapshot.notifyBackendUpdate('#story-history');
    }

    // ---- Real player action -----------------------------------------
    return await callAction(endpoint, payload);
  } catch (err) {
    console.error('Evaluation or action failed', err);
    if (statusEl) statusEl.innerText = 'evaluation error';
    throw err;
  }
}


// -----------------------------------------------------------------------------
// Button Handlers
// -----------------------------------------------------------------------------

/**
 * Handle "Continue" button click.
 * Decides which endpoint to call based on story state and player input.
 */
function handleContinue() {
  const storyText = historyEl.innerText.trim();

  // Build a payload that always contains `action`
  const payload = buildBasePayload();

  let endpoint;
  if (!storyText) {
    // Brand new story
    endpoint = '/api/new';
  } else if (payload.action) {
    // Explicit player input
    endpoint = '/api/player_action';
  } else {
    // No input – decide based on last paragraph
    const lastPara = historyEl.querySelector('p[data-paragraph-id]:last-of-type');
    const needsAction = lastPara && (
      lastPara.classList.contains('user-action') ||
      lastPara.dataset.storyId === 'continue_with_UserAction'
    );
    endpoint = needsAction ? '/api/player_action' : '/api/continue';
    // payload.action is already '' (empty)
  }

  const runner = endpoint === '/api/player_action' ? callEvalThenAction : callAction;

  runner(endpoint, payload)
    .then(res => {
      if (res?.ok) localStorage.removeItem('candidateSnapshot');
    })
    .catch(err => console.error('handleContinue failed', err));
}

/**
 * Handle "Redo" button click.
 * Removes last paragraph and replays pipeline.
 */
function handleRedo() {
  const paragraphs = historyEl.querySelectorAll('p[data-paragraph-id]');

  // No paragraphs → start a fresh story
  if (!paragraphs.length) {
    const payload = buildBasePayload(); // action will be '' (no input)
    callAction('/api/new', payload)
      .then(res => { if (res?.ok) localStorage.removeItem('candidateSnapshot'); })
      .catch(err => console.error('redo‑new failed', err));
    return;
  }

  // Remove the last paragraph
  paragraphs[paragraphs.length - 1].remove();

  // Snapshot after removal (unchanged)
  if (window.UserSnapshot?.pushNow) {
    window.UserSnapshot.pushNow
    // Snapshot after removal (unchanged)
    if (window.UserSnapshot?.pushNow) {
      window.UserSnapshot.pushNow({ reason: 'redo-remove-last-paragraph' });
    }
  }

  // Determine the next endpoint based on the new last paragraph (after removal)
  const remaining = historyEl.querySelectorAll('p[data-paragraph-id]');
  let endpoint;
  if (!remaining.length) {
    endpoint = '/api/new';
  } else {
    const newLast = remaining[remaining.length - 1];
    const storyId = newLast.dataset.storyId || '';
    endpoint = storyId === 'continue_with_UserAction'
      ? '/api/player_action'
      : '/api/continue';
  }

  // Build payload (includes current action text and candidate snapshot)
  const payload = buildBasePayload();

  const runner = endpoint === '/api/player_action' ? callEvalThenAction : callAction;

  runner(endpoint, payload)
    .then(res => {
      if (res?.ok) localStorage.removeItem('candidateSnapshot');
    })
    .catch(err => console.error('handleRedo failed', err));
}

/**
 * Handle "Force" button click.
 * Sends the entire story text to the backend.
 */
function handleForce() {
  const payload = { story: historyEl.innerText.trim() };
  callAction('/api/force', payload);
}

// -----------------------------------------------------------------------------
// Event Listeners
// -----------------------------------------------------------------------------

continueBtn?.addEventListener('click', handleContinue);
redoBtn?.addEventListener('click', handleRedo);
forceBtn?.addEventListener('click', handleForce);