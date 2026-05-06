document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const introScreen = document.getElementById("intro-screen");
  const introDuration = prefersReducedMotion ? 80 : 1650;

  const revealApp = () => {
    body.classList.add("is-ready");
    body.classList.remove("is-loading");

    if (introScreen) {
      setTimeout(() => introScreen.remove(), 560);
    }
  };

  setTimeout(revealApp, introDuration);

  document.querySelectorAll(".btn, .text-link").forEach((element) => {
    element.addEventListener("click", () => {
      if (!prefersReducedMotion && navigator.vibrate) {
        navigator.vibrate(25);
      }
    });
  });

  const carousel = document.getElementById("ig-carousel");
  const swipeHint = document.getElementById("swipe-hint");
  const instagramEmbeds = document.querySelectorAll(".instagram-media");

  const loadInstagramEmbeds = () => {
    if (!instagramEmbeds.length) return;

    if (window.instgrm?.Embeds) {
      window.instgrm.Embeds.process();
      return;
    }

    if (document.getElementById("ig-embed-script")) return;

    const script = document.createElement("script");
    script.id = "ig-embed-script";
    script.async = true;
    script.src = "https://www.instagram.com/embed.js";
    document.body.appendChild(script);
  };

  if (carousel && swipeHint) {
    const updateSwipeHint = () => {
      const canScroll = carousel.scrollWidth > carousel.clientWidth + 4;
      swipeHint.style.display = canScroll ? "block" : "none";
      swipeHint.style.opacity = carousel.scrollLeft > 12 ? "0" : "1";
    };

    carousel.addEventListener("scroll", updateSwipeHint, { passive: true });
    window.addEventListener("resize", updateSwipeHint);
    updateSwipeHint();

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries, obs) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          loadInstagramEmbeds();
          obs.disconnect();
        }
      }, { rootMargin: "220px 0px" });
      observer.observe(carousel);
    } else {
      loadInstagramEmbeds();
    }
  }
});
