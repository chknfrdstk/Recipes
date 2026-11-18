// Fuzzy search for the Recipes site. Loads assets/data/recipes.json
// once, builds a Fuse.js index over titles + normalized ingredient
// cores, and renders live results as you type. The same JSON powers
// the fridge matcher and the serving scaler (see DESIGN.md).
//
// Loaded site-wide from _layouts/default.html, but does nothing on
// pages without a #recipe-search box. No login, no tracking —
// everything runs in the browser.
(function () {
  var input = document.getElementById('recipe-search');
  var resultsEl = document.getElementById('search-results');
  if (!input || !resultsEl) return;

  var SECTIONS = ['beef', 'chicken', 'pork', 'seafood', 'soups',
    'sides', 'sauce', 'no-meat', 'desserts'];
  var RESULT_LIMIT = 12;

  // The site root, derived from the page URL so the same code works
  // on GitHub Pages (/Recipes/...) and Forgejo Pages
  // (/mritchie/Recipes/...). The last path segment is a section
  // folder on protein pages; drop it to get the root.
  function siteRoot() {
    var parts = window.location.pathname.split('/').filter(Boolean);
    if (parts.length && SECTIONS.indexOf(parts[parts.length - 1]) !== -1) {
      parts.pop();
    }
    return '/' + parts.join('/') + '/';
  }

  function statusLine(text) {
    resultsEl.innerHTML = '';
    var p = document.createElement('p');
    p.className = 'search-status';
    p.textContent = text;
    resultsEl.appendChild(p);
  }

  function render(results) {
    resultsEl.innerHTML = '';
    if (!results.length) {
      statusLine('No recipes match — try a different spelling.');
      return;
    }
    statusLine(results.length + (results.length === 1 ? ' recipe' : ' recipes'));
    results.forEach(function (entry) {
      var recipe = entry.item;
      var root = siteRoot();
      var slugParts = recipe.slug.split('/');
      var card = document.createElement('div');
      card.className = 'recipe-card';
      var link = document.createElement('a');
      link.href = root + recipe.slug + '.html';
      var img = document.createElement('img');
      img.src = root + slugParts[0] + '/images/' + slugParts[1] + '.jpg';
      img.alt = recipe.title;
      img.loading = 'lazy';
      var title = document.createElement('span');
      title.className = 'recipe-title';
      title.textContent = recipe.title;
      link.appendChild(img);
      link.appendChild(title);
      card.appendChild(link);
      resultsEl.appendChild(card);
    });
  }

  function start(recipes) {
    if (typeof Fuse === 'undefined') {
      statusLine('Search couldn\u2019t load (Fuse.js didn\u2019t load). Check your connection and reload.');
      return;
    }
    var fuse = new Fuse(recipes, {
      keys: [
        { name: 'title', weight: 0.65 },
        { name: 'ingredients.core', weight: 0.35 }
      ],
      includeScore: true,
      threshold: 0.35,
      ignoreLocation: true,
      minMatchCharLength: 2
    });
    var timer = null;
    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        var query = input.value.trim();
        if (query.length < 2) {
          resultsEl.innerHTML = '';
          return;
        }
        render(fuse.search(query, { limit: RESULT_LIMIT }));
      }, 150);
    });
  }

  fetch(siteRoot() + 'assets/data/recipes.json')
    .then(function (response) {
      if (!response.ok) throw new Error('index not found');
      return response.json();
    })
    .then(start)
    .catch(function () {
      statusLine('Couldn\u2019t load the recipe index. Try reloading the page.');
    });
})();
