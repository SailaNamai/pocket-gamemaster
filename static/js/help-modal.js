// static/js/help-modal.js
// Assumes help-modal.html was included server-side ({% include 'help-modal.html' %})
// and there is a button with id="open-help" in the DOM.

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', init);

  function init() {
    const openBtn = document.getElementById('open-help');
    if (!openBtn) return;

    const modal = document.getElementById('help-modal');
    if (!modal) return;

    const closeBtn = modal.querySelector('.help-close');
    const focusableSelector = 'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';
    let lastFocused = null;

    openBtn.addEventListener('click', onOpenClick);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', onOverlayClick);
    modal.addEventListener('keydown', onModalKeyDown);

    // Ensure modal initially hidden and aria attributes set
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');

    function onOpenClick(e) {
      e.preventDefault();
      openModal();
    }

    function openModal() {
      lastFocused = document.activeElement;
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');

      const focusable = Array.prototype.slice.call(modal.querySelectorAll(focusableSelector));
      if (focusable.length) {
        focusable[0].focus();
      } else {
        // Fallback focus on close button or modal itself
        if (closeBtn) closeBtn.focus();
        else modal.setAttribute('tabindex', '-1'), modal.focus();
      }

      document.addEventListener('keydown', onDocumentKeyDown, true);
      trapFocus(true);
    }

    function closeModal() {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
      trapFocus(false);

      if (lastFocused && typeof lastFocused.focus === 'function') {
        lastFocused.focus();
      } else {
        openBtn.focus();
      }

      document.removeEventListener('keydown', onDocumentKeyDown, true);
    }

    function onOverlayClick(e) {
      if (e.target === modal) closeModal();
    }

    function onDocumentKeyDown(e) {
      if (e.key === 'Escape' || e.key === 'Esc') {
        e.preventDefault();
        closeModal();
      }
    }

    function onModalKeyDown(e) {
      if (e.key !== 'Tab') return;

      const nodes = Array.prototype.slice.call(modal.querySelectorAll(focusableSelector)).filter(isVisible);
      if (nodes.length === 0) {
        e.preventDefault();
        return;
      }
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      const active = document.activeElement;

      if (e.shiftKey) {
        if (active === first || active === modal) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    function trapFocus(enable) {
      if (enable) {
        // add inert to everything outside modal for better screen-reader behaviour when supported
        Array.prototype.forEach.call(document.querySelectorAll('body > *'), function (el) {
          if (el === modal || el.contains(modal)) return;
          el.inert = true; // progressive enhancement; may be unsupported in some browsers
          el.setAttribute('data-help-inert', 'true');
        });
      } else {
        Array.prototype.forEach.call(document.querySelectorAll('[data-help-inert]'), function (el) {
          try { el.inert = false; } catch (e) {}
          el.removeAttribute('data-help-inert');
        });
      }
    }

    function isVisible(el) {
      return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
    }
  }
})();