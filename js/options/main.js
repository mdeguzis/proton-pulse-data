// Entry module for options.html. Browser-local site preferences saved to
// localStorage (not tied to an account). First option: animations on/off,
// applied live here and honored site-wide by js/lib/topbar.js on every page.

const MOTION_KEY = 'proton-pulse:motion';

// Current animations state: explicit choice wins; otherwise default to ON
// unless the OS asks to reduce motion.
function animationsOn() {
  const stored = localStorage.getItem(MOTION_KEY); // 'on' | 'off' | null
  if (stored === 'on') return true;
  if (stored === 'off') return false;
  return !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Apply live: data-motion gates CSS animations/transitions; SMIL (<animateMotion>)
// is paused/unpaused directly since CSS cannot stop it.
function applyAnimations(on) {
  const svgs = document.querySelectorAll('svg');
  if (on) {
    document.documentElement.removeAttribute('data-motion');
    svgs.forEach((s) => { try { s.unpauseAnimations && s.unpauseAnimations(); } catch (e) { /* ignore */ } });
  } else {
    document.documentElement.setAttribute('data-motion', 'off');
    svgs.forEach((s) => { try { s.pauseAnimations && s.pauseAnimations(); } catch (e) { /* ignore */ } });
  }
}

const toggle = document.getElementById('opt-animations');
if (toggle) {
  toggle.checked = animationsOn();
  toggle.addEventListener('change', () => {
    localStorage.setItem(MOTION_KEY, toggle.checked ? 'on' : 'off');
    applyAnimations(toggle.checked);
  });
}
