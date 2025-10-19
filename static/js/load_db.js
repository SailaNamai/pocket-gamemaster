// static/js/load_db.js

function loadInitialStateAndHistory() {
  Promise.all([
    fetch('/api/initial_state').then(r => r.json()),
    fetch('/api/story_history?story_id=new').then(r => r.json())
  ])
  .then(([initial, historyData]) => {
    // 1) Populate story parameters + memory
    const rawStyle = initial.story_parameters.writing_style;
    // Strip any leading or trailing indentation before putting it in the UI
    let cleanStyle = '';
    if (typeof rawStyle === 'string') {
      cleanStyle = rawStyle
        .split('\n')
        .map(line => line.trim())
        .join('\n');
    }

    document.getElementById('param-style').value      = cleanStyle;
    document.getElementById('param-world').value      = initial.story_parameters.world_setting;
    document.getElementById('param-rules').value      = initial.story_parameters.rules;
    document.getElementById('param-player').value     = initial.story_parameters.player;
    document.getElementById('param-characters').value = initial.story_parameters.characters;

    document.querySelector('.mid-synopsis-area').innerHTML  = initial.memory.mid_memory;
    document.querySelector('.long-synopsis-area').innerHTML = initial.memory.long_memory;

    // 1b) Populate settings modal fields (n_ctx, recent, mid, long) when available.
    try {
      const budget = initial.budget || initial.settings || null;
      if (budget) {
        const vals = [
          Number.isFinite(budget.n_ctx) ? budget.n_ctx : null,
          Number.isFinite(budget.recent) ? budget.recent : null,
          Number.isFinite(budget.mid) ? budget.mid : null,
          Number.isFinite(budget.long) ? budget.long : null,
        ];

        if (window.MinimalSettings && typeof window.MinimalSettings.write === 'function') {
          window.MinimalSettings.write(vals);
          if (typeof window.MinimalSettings.updateRemaining === 'function') {
            window.MinimalSettings.updateRemaining();
          }
        } else {
          const fieldIds = ['field-a', 'field-b', 'field-c', 'field-d'];
          fieldIds.forEach((id, i) => {
            const el = document.getElementById(id);
            if (el) el.value = Number.isFinite(vals[i]) ? vals[i] : '';
          });
          if (window.MinimalSettings && typeof window.MinimalSettings.updateRemaining === 'function') {
            window.MinimalSettings.updateRemaining();
          } else {
            const remainingEl = document.getElementById('remaining-value');
            if (remainingEl) {
              const a = parseInt(document.getElementById('field-a')?.value || '0', 10);
              const b = parseInt(document.getElementById('field-b')?.value || '0', 10);
              const c = parseInt(document.getElementById('field-c')?.value || '0', 10);
              const d = parseInt(document.getElementById('field-d')?.value || '0', 10);
              const remaining = a - (b + c + d + 750);
              remainingEl.textContent = String(remaining);
              remainingEl.style.color = remaining < 1000 ? 'crimson' : '';
            }
          }
        }
      }
    } catch (e) {
      console.warn('Failed to populate budget fields from initial state', e);
    }

    // 1c) Populate difficulty dropdown from initial state
    try {
      const diff = initial.difficulty?.diff_setting;
      if (diff) {
        const select = document.getElementById('difficulty-select');
        if (select) {
          select.value = diff; // sets the dropdown to easy/medium/hard
        }
      }
    } catch (e) {
      console.warn('Failed to populate difficulty from initial state', e);
    }

    // 2) Render the story paragraphs
    const storyEl = document.getElementById('story-history');
    storyEl.innerHTML = '';

    historyData.paragraphs.forEach(p => {
      const el = document.createElement('p');
      el.dataset.paragraphId = p.id;
      el.dataset.storyId     = p.story_id;

      // Only attach outcome + tooltip if this is a user action paragraph
      if (p.story_id === 'continue_with_UserAction') {
        el.dataset.outcome = p.outcome || '';
        el.title           = p.outcome || '';
      }

      el.textContent = p.content;   // safe: no HTML parsing
      storyEl.appendChild(el);
    });

    window.Snapshot.notifyBackendUpdate('#story-history');
    styleStoryHistory();

  })
  .catch(err => {
    console.error('Failed to load story history', err);
    document.getElementById('status-indicator').textContent = 'Error loading history';
  });
}

// Run on normal load
document.addEventListener('DOMContentLoaded', loadInitialStateAndHistory);

// Run again if Firefox restores from bfcache/session restore
window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    loadInitialStateAndHistory();
  }
});
