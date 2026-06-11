// Entry point for the app page: bootstraps routing and search wiring.
// (Replaces the inline bootstrap that lived at the top/bottom of app.js.)
import { route } from './router.js?v=d22937ba';
import { wireSearch } from './components/search.js?v=5c8b29f2';

window.addEventListener('hashchange', () => route());
window.addEventListener('popstate', () => route());

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', wireSearch);
} else {
  wireSearch();
}

route();
