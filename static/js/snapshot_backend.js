// static/js/snapshot_backend.js
// Usage: include <script src="{{ url_for('static', filename='js/snapshot.js') }}"></script>
// Behavior: only make a snapshot when the backend signals an update via:
// Save to localStorage as storySnapshots
// Calling window.Snapshot.notifyBackendUpdate(selector) after updating an element
// localStorage.getItem('storySnapshots') to view raw JSON.

(function () {
  'use strict';

  // Config
  const FIELD_SELECTORS = [
    '#story-history',
    '.mid-synopsis-area',
    '.long-synopsis-area'
  ];
  const LOCAL_STORAGE_KEY = 'storySnapshots';
  const MAX_SNAPSHOTS = 2;

  // State
  let snapshots = loadSnapshots();

  // Helpers
  function nowIso() {
    return new Date().toISOString();
  }

  function loadSnapshots() {
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      console.warn('snapshot: failed to read storage, starting fresh');
      return [];
    }
  }

  function saveSnapshots() {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(snapshots));
    } catch (e) {
      console.warn('snapshot: failed to persist snapshots');
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

  function buildSnapshot() {
    return {
      ts: nowIso(),
      fields: readFields()
    };
  }

  function pushSnapshot() {
    const snap = buildSnapshot();
    const last = snapshots.length ? snapshots[snapshots.length - 1] : null;
    if (last && JSON.stringify(last.fields) === JSON.stringify(snap.fields)) {
      last.ts = snap.ts;
      saveSnapshots();
      return;
    }
    snapshots.push(snap);
    trimSnapshots();
    saveSnapshots();
  }

  // Primary public API: notify the script that backend updated a selector
  function notifyBackendUpdate(selector) {
    const el = document.querySelector(selector);
    if (!el) return;
    el.dataset.backendUpdated = 'true';
    // Immediately snapshot once for this update
    pushSnapshot();
    // Remove the marker to keep DOM clean
    delete el.dataset.backendUpdated;
  }

  // Listen for the custom event 'backend:update'. Event detail: { selector: '#id' } or { selectors: ['#a', '.b'] }
  function onBackendUpdateEvent(e) {
    const detail = e && e.detail;
    if (!detail) return;
    if (detail.selector) {
      notifyBackendUpdate(detail.selector);
      return;
    }
    if (Array.isArray(detail.selectors)) {
      detail.selectors.forEach(s => notifyBackendUpdate(s));
      return;
    }
    // fallback: snapshot all known fields
    pushSnapshot();
  }

  // Public functions exposed on window
  window.Snapshot = {
    notifyBackendUpdate,
    listSnapshots: () => snapshots.slice(),
    clearSnapshots: () => {
      snapshots = [];
      saveSnapshots();
    }
  };

})();
