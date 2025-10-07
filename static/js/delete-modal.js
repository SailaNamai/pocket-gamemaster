// delete-modal.js
// Modal behavior + integration with tab_data parameter updates when "Del All" is used.

(function () {
  const modal = document.getElementById('delete-modal');
  if (!modal) return;

  const backdrop = modal.querySelector('[data-action="backdrop"]');
  const btnClose = modal.querySelector('[data-action="close"]');
  const btnDelStory = document.getElementById('confirm-delete_story');
  const btnDelAll = document.getElementById('confirm-delete_all');
  const deleteButton = document.getElementById('delete-button');

  const selectors = {
    storyHistory: '#story-history',
    playerAction: '#player-action',
    params: [
      '#param-style',
      '#param-world',
      '#param-rules',
      '#param-player',
      '#param-characters'
    ],
    midMemory: '.mid-synopsis-area',
    longMemory: '.long-synopsis-area'
  };

  // Map textarea IDs to backend parameter names (same mapping as tab_data.js)
  const paramMap = {
    'param-style': 'writing_style',
    'param-world': 'world_setting',
    'param-rules': 'rules',
    'param-characters': 'characters',
    'param-player': 'player'
  };

  let lastFocused = null;
  let clickGuard = false;

  function openModal(triggerElement) {
    lastFocused = triggerElement || document.activeElement;
    modal.classList.remove('hidden');
    modal.removeAttribute('aria-hidden');
    if (deleteButton) {
      deleteButton.setAttribute('aria-pressed', 'true');
      deleteButton.classList.add('pressed');
    }
    const firstFocusable = modal.querySelector('button, [href], input, textarea, [tabindex]:not([tabindex="-1"])');
    if (firstFocusable) firstFocusable.focus();
    document.addEventListener('keydown', onKeyDown);
  }

  function closeModal() {
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    if (deleteButton) {
      deleteButton.setAttribute('aria-pressed', 'false');
      deleteButton.classList.remove('pressed');
    }
    document.removeEventListener('keydown', onKeyDown);
    if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
  }

  function onKeyDown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      closeModal();
    }
  }

  function clearContentEditable(el) {
    if (!el) return;
    el.innerHTML = '';
  }

  function clearTextarea(el) {
    if (!el) return;
    el.value = '';
    // fire input event so any listeners (like tab_data.js) notice the change
    const evt = new Event('input', { bubbles: true, cancelable: true });
    el.dispatchEvent(evt);
  }

  function clearAllTextFields() {
    clearContentEditable(document.querySelector(selectors.storyHistory));
    clearTextarea(document.querySelector(selectors.playerAction));
    selectors.params.forEach(sel => {
      const t = document.querySelector(sel);
      if (t) clearTextarea(t);
    });
    clearContentEditable(document.querySelector(selectors.midMemory));
    clearContentEditable(document.querySelector(selectors.longMemory));

    // Ensure backend parameters are updated to empty values.
    // Prefer existing global update function if present, otherwise call fetch directly.
    Object.keys(paramMap).forEach(textareaId => {
      const paramName = paramMap[textareaId];
      const el = document.getElementById(textareaId);
      // already cleared above for textareas, but ensure backend gets update
      if (typeof window.sendUpdate === 'function') {
        try {
          window.sendUpdate(paramName, el ? el.value : '');
        } catch (err) {
          // noop: fallback to fetch below
          sendUpdateFallback(paramName, el ? el.value : '');
        }
      } else {
        sendUpdateFallback(paramName, el ? el.value : '');
      }
    });
  }

  function clearStoryMemoryOnly() {
    clearContentEditable(document.querySelector(selectors.storyHistory));
    clearContentEditable(document.querySelector(selectors.midMemory));
    clearContentEditable(document.querySelector(selectors.longMemory));
  }

  // Fallback implementation that mirrors tab_data.js sendUpdate behavior
  function sendUpdateFallback(parameter, value) {
    fetch('/update_story_parameter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parameter, value })
    }).catch(() => { /* silence fallback errors */ });
  }

  // Expose programmatic API
  window.deleteModal = {
    open: () => openModal(deleteButton || null),
    close: closeModal
  };

  if (backdrop) backdrop.addEventListener('click', closeModal);
  if (btnClose) btnClose.addEventListener('click', closeModal);

  function guard(cb) {
    return function (ev) {
      ev && ev.preventDefault();
      if (clickGuard) return;
      clickGuard = true;
      try {
        cb(ev);
      } finally {
        setTimeout(() => (clickGuard = false), 250);
      }
    };
  }

  if (btnDelAll) {
    btnDelAll.addEventListener('click', guard(() => {
      clearAllTextFields();
      closeModal();
    }));
  }

  if (btnDelStory) {
    btnDelStory.addEventListener('click', guard(() => {
      clearStoryMemoryOnly();
      closeModal();
    }));
  }

  if (deleteButton) {
    deleteButton.setAttribute('aria-pressed', 'false');
    deleteButton.addEventListener('click', (e) => openModal(e.currentTarget));
    deleteButton.addEventListener('mousedown', () => deleteButton.classList.add('pressed-immediate'));
    document.addEventListener('mouseup', () => deleteButton.classList.remove('pressed-immediate'));
  }

  // Trap focus inside modal while open
  modal.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    const focusable = modal.querySelectorAll('button, [href], input, textarea, [tabindex]:not([tabindex="-1"])');
    const nodes = Array.prototype.filter.call(focusable, (n) => n.offsetParent !== null);
    if (!nodes.length) return;
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
})();
