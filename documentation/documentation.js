document.addEventListener('DOMContentLoaded', () => {
  const installLabel = document.querySelector('label[for="install"]');
  const promptsLabel = document.querySelector('label[for="prompts"]');
  const issueLabel = document.querySelector('label[for="issue"]');
  const installRadio = document.getElementById('install');
  const promptsRadio = document.getElementById('prompts');
  const issueRadio = document.getElementById('issue');

  const installPanel = document.getElementById('install-panel');
  const promptPanel = document.getElementById('prompt-panel');
  const issuePanel = document.getElementById('issue-panel');

  const navHeading = document.getElementById('navHeading');
  const contentTitle = document.getElementById('contentTitle');
  const contentBody = document.getElementById('contentBody');

  const navSubLists = document.querySelectorAll('.nav-sublist');

  // helper to show a top tab and its nav sublist
  function showTab(tabKey) {
    const isInstall = tabKey === 'install';
    const isPrompts = tabKey === 'prompts';
    const isIssue = tabKey === 'issue';

    // panels: show the matching panel, hide others
    installPanel.classList.toggle('is-visible', isInstall);
    promptPanel.classList.toggle('is-visible', isPrompts);
    issuePanel.classList.toggle('is-visible', isIssue);

    // radios for accessibility
    if (installRadio) installRadio.checked = isInstall;
    if (promptsRadio) promptsRadio.checked = isPrompts;
    if (issueRadio) issueRadio.checked = isIssue;

    // heading
    if (isInstall) navHeading.textContent = 'Installation:';
    else if (isPrompts) navHeading.textContent = 'Prompt adjustment:';
    else if (isIssue) navHeading.textContent = 'Known issues:';
    else navHeading.textContent = '';

    // show matching nav sublist
    navSubLists.forEach((sub) => {
      sub.classList.toggle('is-visible', sub.dataset.tab === tabKey);
    });

    // choose an active nav-item inside visible sublist (or fallback)
    const active = document.querySelector('.nav-sublist.is-visible .nav-item.active')
                    || document.querySelector('.nav-sublist.is-visible .nav-item');
    if (active) {
      // ensure only one active in that sublist
      const parent = active.closest('.nav-sublist');
      if (parent) parent.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      active.classList.add('active');
      setContentFromNavItem(active);
    } else {
      // no nav items in this sublist: clear content
      contentTitle.textContent = '';
      contentBody.innerHTML = '<p></p>';
    }
  }

  // update right content area from a nav item
  function setContentFromNavItem(navItem, { pushHistory = true } = {}) {
    if (!navItem) return;

    // use target card if present
    const targetSelector = navItem.dataset.target;
    const targetCard = targetSelector ? document.querySelector(targetSelector) : null;

    // title preference: navItem dataset-title -> card h3 -> nav text
    const titleFromNav = navItem.dataset.title || navItem.textContent.trim();
    const titleFromCard = targetCard && targetCard.querySelector('h3') ? targetCard.querySelector('h3').textContent : null;
    contentTitle.textContent = titleFromNav || titleFromCard || '';

    // populate contentBody: clone card content (remove its heading if we used it as contentTitle)
    if (targetCard) {
      const clone = targetCard.cloneNode(true);
      const heading = clone.querySelector('h3');
      if (heading) heading.remove();
      contentBody.innerHTML = clone.innerHTML.trim() || '<p></p>';
    } else {
      // fallback to inline data-content or simple text
      const html = navItem.dataset.content || `<p>${navItem.textContent.trim()} content here.</p>`;
      contentBody.innerHTML = html;
    }

    // reset the content pane's scroll position
    if (typeof contentBody.scrollTo === 'function') {
      contentBody.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    } else {
      contentBody.scrollTop = 0;
    }
    // ensure pane is visible at top of viewport
    contentBody.scrollIntoView({ block: 'start', behavior: 'auto' });

    // accessibility: focus the content body so screen readers know it changed
    contentBody.setAttribute('tabindex', '-1');
    contentBody.focus({ preventScroll: true });

    // update URL hash so the view is linkable and restorable
    if (pushHistory) {
      const tabKey = document.querySelector('.nav-sublist.is-visible')?.dataset.tab || 'install';
      const targetId = (targetSelector || '#').replace(/^#/, '') || navItem.textContent.trim().toLowerCase().replace(/\s+/g, '-');
      history.replaceState(null, '', `#${tabKey}/${encodeURIComponent(targetId)}`);
    }
  }

  // restore state from URL hash on load
  function restoreFromHash() {
    const hash = location.hash.replace(/^#/, '');
    if (!hash) return;
    const [tabKey, targetId] = hash.split('/');
    if (tabKey === 'prompts' || tabKey === 'install' || tabKey === 'issue') {
      showTab(tabKey);
      if (targetId) {
        const decoded = decodeURIComponent(targetId);
        const targetSelector = `#${decoded}`;
        const navItem = document.querySelector(`.nav-item[data-target="${targetSelector}"]`)
                      || Array.from(document.querySelectorAll('.nav-sublist[data-tab="'+tabKey+'"] .nav-item'))
                           .find(n => (n.dataset.target || '').replace(/^#/, '') === decoded
                                    || n.textContent.trim().toLowerCase() === decoded);
        if (navItem) {
          const parent = navItem.closest('.nav-sublist');
          if (parent) parent.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
          navItem.classList.add('active');
          setContentFromNavItem(navItem, { pushHistory: false });
        }
      }
    }
  }

  // attach listeners to nav items (works for items in any sublist)
  document.querySelectorAll('.nav-item').forEach((navItem) => {
    navItem.tabIndex = 0;
    navItem.addEventListener('click', () => {
      // set active class within its parent sublist
      const parent = navItem.closest('.nav-sublist');
      if (parent) {
        parent.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      }
      navItem.classList.add('active');

      // ensure we are on the right top tab
      const subTab = navItem.closest('.nav-sublist')?.dataset.tab;
      if (subTab) showTab(subTab);

      setContentFromNavItem(navItem);
    });

    navItem.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        navItem.click();
      }
    });
  });

  // wire top tab labels
  if (installLabel) installLabel.addEventListener('click', () => showTab('install'));
  if (promptsLabel) promptsLabel.addEventListener('click', () => showTab('prompts'));
  if (issueLabel) issueLabel.addEventListener('click', () => showTab('issue'));

  // keyboard activation for labels
  function keyActivate(label, fn) {
    if (!label) return;
    label.tabIndex = 0;
    label.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        fn();
      }
    });
  }
  keyActivate(installLabel, () => showTab('install'));
  keyActivate(promptsLabel, () => showTab('prompts'));
  keyActivate(issueLabel, () => showTab('issue'));

  // initial state
  showTab('install');
  // restore if there's a hash
  restoreFromHash();
});
