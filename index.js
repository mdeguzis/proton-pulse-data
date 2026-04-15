  var toggle  = document.getElementById('sidebar-toggle');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebar-overlay');

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
  }

  toggle.addEventListener('click', function() {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('open');
  });

  overlay.addEventListener('click', closeSidebar);

  // close sidebar when a nav link is clicked (mobile)
  sidebar.querySelectorAll('a').forEach(function(a) {
    a.addEventListener('click', closeSidebar);
  });

  // -- Search (same as app.html) --
  var STEAM_IMG = function(id) {
    return 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/' + id + '/header.jpg';
  };
  function esc(s) { var d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

  var searchTimer = null;
  var searchInput   = document.getElementById('search');
  var searchResults = document.getElementById('search-results');

  // Search: navigate to data-index with filter query (avoids CORS issues
  // with Steam storesearch API on GitHub Pages)
  searchInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      var q = searchInput.value.trim();
      if (!q) return;
      // Numeric = go directly to game page; text = grouped search results
      if (/^\d+$/.test(q)) {
        window.location.href = 'app.html#/app/' + q;
      } else {
        window.location.href = 'app.html?q=' + encodeURIComponent(q);
      }
    }
  });
})();
