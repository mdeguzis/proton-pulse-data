# Frontend JS Architecture

How JavaScript is organized in this static site. New code follows this layout.
The goal is that anyone can tell what a file does from its path alone.

## Context

This is a multi-page static site (one HTML file per page: `index.html`,
`app.html`, `submit.html`, `game-stats.html`, `confidence.html`, `admin.html`,
`profile.html`, ...). There is no production bundler. The browser loads raw ES
modules directly, and the deploy step copies the files listed in
`gh-pages-manifest.txt` to the `gh-pages` branch as-is.

Because the browser runs the modules untransformed, imports use real relative
paths with the `.js` extension (e.g. `import { esc } from '../utils.js'`).

## Top-level layout

```
js/
  shared/        Modules used by two or more pages.
  <page>/        One folder per HTML page (app, admin, submit, game-stats, ...).
```

A page named `foo.html` is driven by `js/foo/main.js`, loaded with a single
module script tag:

```html
<script type="module" src="js/foo/main.js"></script>
```

## Per-page layout (layered)

Inside a page folder, code is split by responsibility (a layered architecture),
not lumped into one file or a generic `modules/` bucket:

```
js/<page>/
  main.js            Entry point. Bootstraps the page: wires events, kicks off
                     routing/initial render. No business logic of its own.
  router.js          Client-side routing (only pages that route, e.g. app).
  config.js          Environment + constants for the page (URLs, colors, etc.).
  utils.js           Pure helpers: formatting, escaping, small data shaping.
                     No DOM writes, no fetching.
  api/               DATA layer. Everything that fetches or talks to a backend
                     (Supabase REST, the CDN, ProtonDB, vote writes) plus the
                     caches and data-shape maps those fetches use. No DOM.
  components/        VIEW layer. Everything that builds HTML / writes the DOM.
                     Takes data, returns markup or updates elements. No fetching.
```

Split files within `api/` and `components/` by feature (`supabase.js`,
`votes.js`, `deck-status.js`, `report-card.js`, ...). A feature that both
fetches and renders is split across the two layers: `api/deck-status.js` holds
its fetches and caches, `components/deck-status.js` holds its render functions.

## The one rule: dependencies point one way

```
components/  ->  api/  ->  utils.js / config.js
     |________________________^
```

- `components/` may import from `api/`, `utils.js`, `config.js`, and other
  `components/`.
- `api/` may import from `utils.js` and `config.js`. It must not import from
  `components/`.
- `utils.js` and `config.js` import nothing from the page (leaves of the graph).

If you find yourself wanting `api/` to import a component, the logic is in the
wrong layer. Move the rendering to `components/` and have the component call the
api function.

## Shared modules (`js/shared/`)

Code used by more than one page lives in `js/shared/` and is imported by each
page that needs it. Example: the scoring and submit-form logic is used by the
app, submit, game-stats, and confidence pages, so it lives in
`js/shared/scoring.js` and `js/shared/submit.js`.

Because any file containing `export` can only be loaded as a module, every page
that uses a shared module must load via `type="module"` and import it. A classic
`<script src>` cannot consume an ES module.

## Exception: shared infrastructure stays classic-global

A few third-party / cross-cutting scripts are still loaded the old way, as
classic `<script>` tags before the module entry, and expose globals on `window`:

- the Supabase UMD bundle
- `supabase-client.js`
- `topbar.js`
- `gh-gist.js`

A page's `config.js` bridges the globals it needs into the module world, e.g.
`export const SupaAuth = window.SupaAuth;`. This keeps the shared infra in one
place and out of every module's import list. See `js/admin/config.js` for the
reference pattern.

## Adding things

**A new page `foo.html`:**
1. Create `js/foo/main.js` and load it with `<script type="module" src="js/foo/main.js">`.
2. Add `api/` and `components/` folders as the page grows; keep `main.js` thin.
3. Add every new file to `gh-pages-manifest.txt` (and any deploy step in
   `.github/workflows/update-data.yml` that lists site files).

**A new feature on an existing page:**
1. Fetching goes in `api/<feature>.js`. Rendering goes in `components/<feature>.js`.
2. Pure helpers go in `utils.js`.
3. Wire it from `main.js` (or the relevant component), respecting the one-way
   dependency rule.

**Something used by a second page:** move it to `js/shared/` and import it from
both pages.

## Testing

Tests live in `tests/*.test.js` (Jest + jsdom). Jest here has no ESM transform,
so module-targeting tests read the source files, strip `import`/`export` lines,
concatenate them, and evaluate the result in a `vm` context with browser stubs.
See `tests/adminAuth.test.js` and `tests/appRenderCallers.test.js` for the
pattern. Keep coverage at or above the thresholds in `package.json`.
