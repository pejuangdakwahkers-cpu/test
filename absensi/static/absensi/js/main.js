/**
 * Sistem Absensi RFID — Main JavaScript
 * Handles mobile menu toggle, active nav highlighting,
 * and other interactive behaviors.
 */

document.addEventListener('DOMContentLoaded', function () {

  /* ========== Mobile Menu Toggle ========== */
  const menuBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  const hamburgerIcon = document.getElementById('hamburger-icon');
  const closeIcon = document.getElementById('close-icon');

  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', function () {
      const isOpen = !mobileMenu.classList.contains('hidden');

      if (isOpen) {
        mobileMenu.classList.add('hidden');
        hamburgerIcon.classList.remove('hidden');
        closeIcon.classList.add('hidden');
        menuBtn.setAttribute('aria-label', 'Buka menu');
      } else {
        mobileMenu.classList.remove('hidden');
        hamburgerIcon.classList.add('hidden');
        closeIcon.classList.remove('hidden');
        menuBtn.setAttribute('aria-label', 'Tutup menu');
      }
    });
  }

  /* ========== Active Nav Link Highlighting ========== */
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');

  navLinks.forEach(function (link) {
    if (link.getAttribute('href') === currentPath) {
      link.classList.remove('text-muted');
      link.classList.add('text-primary', 'bg-blue-50', 'font-semibold');
    }
  });

  /* Also highlight mobile menu items */
  const mobileLinks = mobileMenu ? mobileMenu.querySelectorAll('a') : [];
  mobileLinks.forEach(function (link) {
    if (link.getAttribute('href') === currentPath) {
      link.classList.remove('text-muted');
      link.classList.add('text-primary', 'bg-blue-50', 'font-semibold');
    }
  });

  /* ========== Kelas Filter Auto-Submit ========== */
  const kelasFilter = document.getElementById('kelas-filter');
  if (kelasFilter) {
    kelasFilter.addEventListener('change', function () {
      this.closest('form').submit();
    });
  }

  /* ========== Animate Progress Bars on Scroll ========== */
  const progressBars = document.querySelectorAll('.progress-bar-fill');

  if (progressBars.length > 0 && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          const bar = entry.target;
          bar.style.width = bar.dataset.width || '0%';
          observer.unobserve(bar);
        }
      });
    }, { threshold: 0.1 });

    progressBars.forEach(function (bar) {
      const width = bar.style.width;
      bar.dataset.width = width;
      bar.style.width = '0%';
      observer.observe(bar);
    });
  }

  /* ========== Close Mobile Menu on Outside Click ========== */
  document.addEventListener('click', function (e) {
    if (menuBtn && mobileMenu && !mobileMenu.classList.contains('hidden')) {
      if (!menuBtn.contains(e.target) && !mobileMenu.contains(e.target)) {
        mobileMenu.classList.add('hidden');
        hamburgerIcon.classList.remove('hidden');
        closeIcon.classList.add('hidden');
        menuBtn.setAttribute('aria-label', 'Buka menu');
      }
    }
  });

});
