document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const introScreen = document.getElementById('intro-screen');
  const isMobile = window.matchMedia('(max-width: 899px)').matches;
  const desktopQuery = window.matchMedia('(min-width: 900px)');
  const INTRO_DURATION_MS = prefersReducedMotion ? 120 : (isMobile ? 1900 : 2200);

  const updateDesktopScrollMode = () => {
    if (!desktopQuery.matches) {
      body.classList.remove('desktop-locked', 'desktop-scrollable');
      return;
    }

    body.classList.remove('desktop-locked');
    body.classList.add('desktop-scrollable');

    const needsScroll = document.documentElement.scrollHeight > window.innerHeight + 2;
    body.classList.toggle('desktop-locked', !needsScroll);
    body.classList.toggle('desktop-scrollable', needsScroll);
  };

  let rafId = 0;
  const scheduleDesktopScrollModeUpdate = () => {
    if (rafId) {
      cancelAnimationFrame(rafId);
    }

    rafId = requestAnimationFrame(() => {
      updateDesktopScrollMode();
      rafId = 0;
    });
  };

  const revealApp = () => {
    body.classList.add('is-ready');
    body.classList.remove('is-loading');

    if (introScreen) {
      setTimeout(() => {
        introScreen.remove();
      }, 620);
    }

    scheduleDesktopScrollModeUpdate();
  };

  setTimeout(revealApp, INTRO_DURATION_MS);

  const buttons = document.querySelectorAll('.btn-primary, .btn-icon, .action-card');
  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (!prefersReducedMotion && navigator.vibrate) {
        navigator.vibrate(35);
      }
    });
  });

  const carousel = document.getElementById('ig-carousel');
  const swipeHint = document.getElementById('swipe-hint');
  const instagramEmbeds = document.querySelectorAll('.instagram-media');

  const loadInstagramEmbeds = () => {
    if (!instagramEmbeds.length) {
      return;
    }

    if (window.instgrm && window.instgrm.Embeds) {
      window.instgrm.Embeds.process();
      return;
    }

    if (document.getElementById('ig-embed-script')) {
      return;
    }

    const script = document.createElement('script');
    script.id = 'ig-embed-script';
    script.async = true;
    script.src = 'https://www.instagram.com/embed.js';
    script.onload = () => {
      if (window.instgrm && window.instgrm.Embeds) {
        window.instgrm.Embeds.process();
      }
      scheduleDesktopScrollModeUpdate();
    };
    document.body.appendChild(script);
  };

  if (carousel && swipeHint) {
    const updateSwipeHint = () => {
      const hasHorizontalOverflow = carousel.scrollWidth > carousel.clientWidth + 4;

      if (!hasHorizontalOverflow) {
        swipeHint.style.display = 'none';
        return;
      }

      swipeHint.style.display = 'flex';
      const hasScrolled = carousel.scrollLeft > 16;
      swipeHint.style.opacity = hasScrolled ? '0' : '1';
    };

    carousel.addEventListener('scroll', updateSwipeHint, { passive: true });
    window.addEventListener('resize', updateSwipeHint);
    updateSwipeHint();

    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries, obs) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          loadInstagramEmbeds();
          obs.disconnect();
        }
      }, { rootMargin: '220px 0px' });
      observer.observe(carousel);
    } else {
      loadInstagramEmbeds();
    }
  }

  window.addEventListener('resize', scheduleDesktopScrollModeUpdate);
  window.addEventListener('load', scheduleDesktopScrollModeUpdate);
  desktopQuery.addEventListener('change', scheduleDesktopScrollModeUpdate);
  scheduleDesktopScrollModeUpdate();
});