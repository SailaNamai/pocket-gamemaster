// static/js/clear_user_action.js

function clearAndRender(paragraphs, midMemory, longMemory) {
  // 1) clear the player input
  const actionEl = document.getElementById('player-action');
  actionEl.value = '';

  // append each paragraph with both data-paragraph-id and data-story-id
  const storyEl = document.getElementById('story-history');
  paragraphs.forEach(p => {
      if (!p) return; // skip null/undefined entries

      const pEl = document.createElement('p');
      pEl.dataset.paragraphId = p.id;
      pEl.dataset.storyId     = p.story_id;
      pEl.textContent = p.content;
      storyEl.appendChild(pEl);
      window.Snapshot.notifyBackendUpdate('#story-history');
    });
  // 3) inject memory if provided
  if (midMemory  !== undefined) document.querySelector('.mid-synopsis-area').innerHTML  = midMemory;
  if (midMemory  !== undefined) window.Snapshot.notifyBackendUpdate('.mid-synopsis-area');
  if (longMemory !== undefined) document.querySelector('.long-synopsis-area').innerHTML = longMemory;
  if (longMemory !== undefined) window.Snapshot.notifyBackendUpdate('.long-synopsis-area');
}

window.clearAndRender = clearAndRender;