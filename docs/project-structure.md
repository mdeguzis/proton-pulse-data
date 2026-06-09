# Project Structure

A map of how `proton-pulse-web` is laid out: the companion static site for
proton-pulse.com plus the data pipeline that feeds it. Use this to find where a
thing lives and where a new thing should go.

For the rules that govern the front-end JavaScript specifically (the layered
`api/` + `components/` + `utils`/`config` split, the one-way dependency rule,
shared vs. classic-global code), see [`js-architecture.md`](./js-architecture.md).
This document is the higher-level repo map; that one is the JS standard.

Last verified: 2026-06-08.

## Top-level tree

```
proton-pulse-web/
|-- *.html                      Page markup, one file per page. Stays at root:
|                               each file is a live URL (proton-pulse.com/<page>.html).
|-- css/                        Styles, one folder per page + shared.
|   |-- shared/site.css         Global styles, loaded by every page.
|   `-- <page>/<page>.css       Page-specific styles.
|-- js/                         Front-end ES modules, loaded with <script type="module">.
|   |-- <page>/                 One folder per page. Larger pages are layered
|   |                           (api/ + components/ + main/config/utils); see js-architecture.md.
|   |-- shared/                 ES modules used by more than one page.
|   `-- lib/                    Cross-cutting infra: classic-global scripts (supabase
|                               client, topbar, gh-*) + the synced scoring lib.
|-- assets/                     Images and static media referenced by pages.
|-- scripts/                    Python data pipeline + shell/dev tooling.
|   `-- pipeline/               The split-reports pipeline package (CLI + stages).
|-- supabase/                   Edge functions + SQL migrations (the backend).
|-- workers/                    Cloudflare Worker(s), deployed separately.
|-- config/                     Pipeline config data (hardcoded path, do not move).
|-- vendor/                     Git submodule(s).
|-- tests/                      Jest (front-end) + pytest (pipeline) suites.
|-- docs/                       This file, js-architecture.md, and plans/.
|-- gh-pages-manifest.txt       The deploy allowlist (source -> gh-pages).
|-- Makefile                    Build / test / deploy / pipeline entry points.
`-- <tooling files>             package.json, lockfiles, pyproject.toml, etc.
```

`node_modules/` and `.git/` are omitted.

## Front-end

The site is a multi-page static site with no production bundler. The browser
loads raw ES modules directly, so imports use real relative paths with the
`.js` extension. Files are split by concern: markup, styles, and scripts never
share a file (no inline `<style>` or `<script>` blocks).

### Pages (root)

HTML files live at the repo root because each one is a public URL. They are
referenced by bare filename across internal nav (`js/lib/topbar.js`), in-page
links, and the data pipeline's generated pages, and at least
`plugin-link.html` is part of the live plugin companion-link flow. Moving them
would change those URLs, so they stay put.

### Styles (`css/`)

`css/shared/site.css` holds the global styles every page loads. Per-page styles
live in `css/<page>/<page>.css`. A few pages share another page's stylesheet
(the app-family pages all use `css/app/app.css`; the content pages use
`css/index/index.css`).

### Scripts (`js/`)

Each page is driven by `js/<page>/main.js`. Simple pages are a single module;
larger pages (`app`, `admin`, `profile`) are split into a layered structure:

```
js/<page>/
  main.js          Entry point: bootstraps the page, wires events, kicks off render.
  config.js        Env + constants; bridges classic-global infra into module scope.
  utils.js         Pure helpers (formatting, parsing, escaping). No DOM, no fetch.
  api/             Data layer: everything that fetches or talks to a backend.
  components/      View layer: everything that builds HTML / writes the DOM.
```

Dependencies point one way: `components/ -> api/ -> utils.js / config.js`. The
full standard is in [`js-architecture.md`](./js-architecture.md).

- `js/shared/` holds ES modules used by more than one page (`scoring.js`,
  `submit.js`, `hardware.js`, `chart-interactions.js`, `config.js`).
- `js/lib/` holds cross-cutting infrastructure: the classic-global scripts
  loaded before the module entry (`supabase-client.js`, `topbar.js`,
  `gh-gist.js`, `gh-auth.js`) and `scoring/` (the game-stats scoring lib,
  kept in sync with the plugin's canonical scoring source).

### Page -> assets map

| Page (`*.html`)      | Page CSS                       | Page JS module            | Notes                          |
|----------------------|--------------------------------|---------------------------|--------------------------------|
| `index.html`         | `css/index/index.css`          | `js/index/main.js`        | Landing page                   |
| `app.html`           | `css/app/app.css`              | `js/app/` (layered)       | Main browse/report app         |
| `admin.html`         | `css/admin/admin.css`          | `js/admin/` (layered)     | Moderation console             |
| `profile.html`       | `css/profile/profile.css`      | `js/profile/` (layered)   | My Account                     |
| `auth.html`          | `css/auth/auth.css`            | `js/auth/main.js`         | Sign-in                        |
| `plugin-link.html`   | `css/plugin-link/plugin-link.css` | `js/plugin-link/main.js` | Plugin companion-link flow     |
| `submit.html`        | `css/app/app.css`              | `js/submit/main.js`       | Submit a report                |
| `game-stats.html`    | `css/app/app.css`              | `js/game-stats/main.js`   | Per-game stats                 |
| `confidence.html`    | `css/app/app.css`              | `js/confidence/main.js`   | Confidence breakdown           |
| `stats.html`         | (shared `site.css`)            | `js/stats/main.js`        | Aggregate stats                |
| `scoring.html`       | (shared `site.css`)            | (topbar only)             | Static explainer page          |
| `privacy.html`       | `css/index/index.css`          | (topbar only)             | Content page                   |
| `terms.html`         | `css/index/index.css`          | (topbar only)             | Content page                   |
| `googled7b1...html`  | none                           | none                      | Google site-verification stub  |

Every page also loads `css/shared/site.css` and `js/lib/topbar.js`.

## Back-end and data

- `scripts/pipeline/` is the split-reports pipeline (a Python package): `cli.py`
  is the entry point, with stages in `catalog.py`, `process.py`, `backfill.py`,
  `metadata.py`, `stats.py`, `finalize.py`, plus `common.py` and `state.py`.
  `scripts/split_reports.py` is the thin CLI wrapper the Makefile and CI call.
- Other `scripts/` are dev/ops tooling: `smoke.sh` + `smoke-test.py` (the
  render-path smoke test), `backup_supabase.sh`, `cache-bust.sh`,
  `setup_dev.sh`, `analyse_scoring.py`, etc.
- `supabase/` is the backend: `functions/` holds the edge functions (the
  `plugin-link-*` flow, `steam-callback`, `user-system-upload`), and
  `migrations/` holds the timestamped SQL migrations.
- `workers/gh-token-proxy.js` is a Cloudflare Worker, deployed on its own (not
  part of the static-site deploy).
- `config/live_backfill_app_ids.json` is pipeline config. Its path is hardcoded
  in `scripts/pipeline/common.py` (`parents[2]/config/...`), so it must stay at
  `config/`.
- `vendor/Steam-Games-Scraper` is a git submodule (see `.gitmodules`).
- `assets/` holds images (`steam-logo*.png`, `logo-wide.svg`) and the
  `steam-login-button-preview.html` snippet.

## Build, test, deploy

- Deploy is driven by `gh-pages-manifest.txt`: the GitHub Actions workflow
  copies exactly the files listed there from the source branch to the
  `gh-pages` branch. Any new site file (html/css/js/asset) must be added to the
  manifest or it will not deploy. `gh-pages-exclude-manifest.txt` lists
  intentional exclusions.
- `Makefile` is the entry point for everything: `make install` (pnpm deps),
  `make serve` (vite dev server), `make smoke` (render-path smoke test in
  headless Firefox), `make test` (lint + pytest), plus the `gh-*` deploy/data
  targets.
- Tests:
  - Front-end: Jest + jsdom in `tests/*.test.js`. Jest has no ESM transform, so
    module-targeting tests read the source, strip `import`/`export`, and run the
    bundle in a `vm` (see `tests/_esm-vm.js`, `tests/adminAuth.test.js`).
  - Pipeline: pytest in `tests/test_*.py`, run via `uv`.
  - Smoke: `scripts/smoke.sh` serves a staged copy and drives each page in a
    real browser to catch render-path errors the unit tests cannot.

## Where to put new things

- A new page `foo.html`: markup at root; styles in `css/foo/foo.css`; script in
  `js/foo/main.js` loaded with `<script type="module">`. Add `api/` +
  `components/` as it grows. Add every new file to `gh-pages-manifest.txt`.
- A new feature on an existing page: fetching in `api/<feature>.js`, rendering
  in `components/<feature>.js`, pure helpers in `utils.js`, wired from `main.js`.
- Code needed by a second page: move it to `js/shared/`.
- A new pipeline stage: a module under `scripts/pipeline/`, wired into `cli.py`.
- A new backend change: an edge function under `supabase/functions/` and/or a
  timestamped migration under `supabase/migrations/`.
