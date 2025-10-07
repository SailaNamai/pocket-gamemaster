// settings-modal.js
(() => {
  const modal = document.getElementById('settings-modal');
  const openBtn = document.getElementById('open-settings');
  const saveBtn = document.getElementById('settings-save');
  const cancelBtn = document.getElementById('settings-cancel');
  const closeTriggers = modal ? modal.querySelectorAll('[data-action="close"]') : [];

  const presetSelect = document.getElementById('preset-select');
  const fields = {
    a: document.getElementById('field-a'), // n_ctx
    b: document.getElementById('field-b'), // recent
    c: document.getElementById('field-c'), // mid
    d: document.getElementById('field-d'), // long
  };
  const remainingEl = document.getElementById('remaining-value');

  const PRESETS = {
    '1': [8000, 1500, 2000, 2500],
    '2': [7000, 1500, 1500, 2000],
    '3': [6000, 1200, 1200, 1600],
    '4': [5000, 1200, 1200, 1200],
    '5': [4000, 1000, 900, 900],
  };

  function toInt(v) {
    const n = parseInt(String(v || '').trim(), 10);
    return Number.isNaN(n) ? 0 : n;
  }

  function writeFields(vals) {
    if (!vals) return;
    fields.a.value = Number.isFinite(vals[0]) ? vals[0] : '';
    fields.b.value = Number.isFinite(vals[1]) ? vals[1] : '';
    fields.c.value = Number.isFinite(vals[2]) ? vals[2] : '';
    fields.d.value = Number.isFinite(vals[3]) ? vals[3] : '';
    updateRemaining();
  }

  function readFields() {
    return {
      a: toInt(fields.a.value),
      b: toInt(fields.b.value),
      c: toInt(fields.c.value),
      d: toInt(fields.d.value),
      preset: (presetSelect && presetSelect.value) || null,
    };
  }

  function calculateRemaining(data) {
    const a = toInt(data.a);
    const sum = toInt(data.b) + toInt(data.c) + toInt(data.d) + 750;
    return a - sum;
  }

  function updateRemaining() {
    const vals = readFields();
    const remaining = calculateRemaining(vals);
    if (remainingEl) {
      remainingEl.textContent = String(remaining);
      remainingEl.style.color = remaining < 1000 ? 'crimson' : '';
    }
  }

  function applyPreset(value) {
    if (!value) return;
    const p = PRESETS[value];
    if (p) {
      writeFields(p);
    }
  }

  function openModal() {
  if (!modal) return;

  const presetSelect = document.getElementById('preset-select');
  if (presetSelect && presetSelect.options.length > 0) {
    // choose the first option which is "Custom" in your markup
    presetSelect.selectedIndex = 0;
  }

  modal.removeAttribute('hidden');
  setTimeout(() => fields.a && fields.a.focus(), 0);
  document.addEventListener('keydown', onKeyDown);
  updateRemaining();
}


  function closeModal() {
    if (!modal) return;
    modal.setAttribute('hidden', '');
    document.removeEventListener('keydown', onKeyDown);
  }

  function onKeyDown(e) {
    if (e.key === 'Escape') closeModal();
  }

  async function parseResponseBody(resp) {
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      try {
        return await resp.json();
      } catch (e) {
        return { parseError: true, raw: await resp.text() };
      }
    }
    // fallback to text if not JSON
    const text = await resp.text();
    return text;
  }

  function showError(message) {
    const errorEl = document.getElementById('settings-error');
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.style.display = 'block';
  }

  function clearError() {
    const errorEl = document.getElementById('settings-error');
    if (!errorEl) return;
    errorEl.textContent = '';
    errorEl.style.display = 'none';
  }

  function init() {
    if (!modal) return;

    if (openBtn) openBtn.addEventListener('click', openModal);

    if (saveBtn) saveBtn.addEventListener('click', async () => {
      const data = readFields();
      clearError();

      try {
        const resp = await fetch('/api/update_budget', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            n_ctx: data.a,
            recent: data.b,
            mid: data.c,
            long: data.d,
          }),
        });

        const body = await parseResponseBody(resp);

        if (!resp.ok) {
          // Prefer server-provided message if available
          if (body && typeof body === 'object' && body.message) {
            showError(`Server error: ${body.message}`);
            return;
          }
          showError(`Server error: ${resp.status} ${resp.statusText}`);
          return;
        }

        // Handle JSON { message: ... } responses
        if (body && typeof body === 'object' && body.message) {
          const msg = body.message;
          if (msg === 'insane_request') {
            showError('Invalid budget parameters. Please adjust values and try again.');
            return;
          }
          if (msg === 'update_successful') {
            console.log('Settings saved', { n_ctx: data.a, recent: data.b, mid: data.c, long: data.d });
            closeModal();
            return;
          }
          showError(`Unexpected server response: ${JSON.stringify(body)}`);
          return;
        }

        // Handle plain text responses
        if (typeof body === 'string') {
          if (body === 'insane_request') {
            showError('Invalid budget parameters. Please adjust values and try again.');
            return;
          }
          if (body === 'update_successful') {
            console.log('Settings saved', { n_ctx: data.a, recent: data.b, mid: data.c, long: data.d });
            closeModal();
            return;
          }
          showError(`Unexpected server response: ${body}`);
          return;
        }

        // Unknown format
        showError('Unexpected server response. Please try again.');
      } catch (err) {
        showError('Network error. Please try again.');
      }
    });

    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
    closeTriggers.forEach(el => el.addEventListener('click', closeModal));
    const backdrop = modal.querySelector('.modal-backdrop');
    if (backdrop) backdrop.addEventListener('click', closeModal);

    if (presetSelect) {
      presetSelect.addEventListener('change', (e) => {
        const v = e.target.value;
        if (v && PRESETS[v]) {
          applyPreset(v);
        }
      });
    }

    Object.values(fields).forEach(input => {
      if (!input) return;
      input.addEventListener('input', () => {
        if (presetSelect && presetSelect.value) presetSelect.value = '';
        updateRemaining();
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.MinimalSettings = {
    open: openModal,
    close: closeModal,
    read: readFields,
    write: writeFields,
    applyPreset,
    updateRemaining,
  };
})();
