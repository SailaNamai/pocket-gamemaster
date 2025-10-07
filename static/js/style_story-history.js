// static/js/style_story-history.js

(function(){
  // Main entry point
  function styleStoryHistory() {
    const container = document.getElementById('story-history');
    if (!container) return;

    const paragraphs = container.querySelectorAll('p');
    paragraphs.forEach(p => {
      const sid = p.getAttribute('data-story-id');

      // 1) User action paragraphs
      if (sid === 'continue_with_UserAction') {
        // avoid re-wrapping
        if (!p.querySelector('.user-action')) {
          const wrapper = document.createElement('span');
          wrapper.className = 'user-action';
          wrapper.appendChild(document.createTextNode('>> '));
          // move all existing nodes into our wrapper
          while (p.firstChild) {
            wrapper.appendChild(p.firstChild);
          }
          p.appendChild(wrapper);
        }

      // 2) All other paragraphs: wrap "speech"
      } else {
        wrapSpeechInNode(p);
      }
    });
  }

  // Recursive function: replaces text nodes containing "…"
  function wrapSpeechInNode(node) {
    // Only process text nodes
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent;
      const regex = /"([^"]+)"/g;
      let lastIndex = 0;
      let match;
      const frag = document.createDocumentFragment();

      while ((match = regex.exec(text)) !== null) {
        // text before the quote
        const before = text.slice(lastIndex, match.index);
        if (before) {
          frag.appendChild(document.createTextNode(before));
        }

        // speech span (including the quotes)
        const span = document.createElement('span');
        span.className = 'speech';
        span.textContent = match[0];
        frag.appendChild(span);

        lastIndex = regex.lastIndex;
      }

      // any trailing text
      const after = text.slice(lastIndex);
      if (after) {
        frag.appendChild(document.createTextNode(after));
      }

      // if we found any quotes, replace the node
      if (frag.childNodes.length > 0) {
        node.parentNode.replaceChild(frag, node);
      }

    // Recurse into element nodes—skip ones we’ve already styled
    } else if (
      node.nodeType === Node.ELEMENT_NODE &&
      !node.classList.contains('speech') &&
      !node.classList.contains('user-action')
    ) {
      Array.from(node.childNodes).forEach(wrapSpeechInNode);
    }
  }

  // Expose and auto-run on load
  window.styleStoryHistory = styleStoryHistory;
  styleStoryHistory();
})();
