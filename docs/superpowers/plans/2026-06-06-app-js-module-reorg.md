# app.js ES-module Reorg Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `app.js` (1962 lines) into focused ES modules under `js/app/`, and convert its shared sibling scripts into `js/shared/` modules, matching the existing `js/admin/` structure, so the site is easier to maintain and debug.

**Architecture:** Two phases on an isolated branch/worktree. Phase A decomposes `app.js` into ~14 single-responsibility modules loaded via one `<script type="module" src="js/app/main.js">`, temporarily bridging the `scoring`/`submit` globals through `js/app/config.js`. Phase B converts the four shared siblings to `js/shared/` ES modules, swaps every consumer page (app, submit, game-stats, confidence) to import them, and removes the temporary bridge. Production keeps serving raw files copied from `main` via `gh-pages-manifest.txt`; shared infra (`topbar.js`, `supabase-client.js`, supabase UMD) stays classic-global.

**Tech Stack:** Vanilla ES modules (no bundler in prod), Vite (dev only), Jest + jsdom, GitHub Pages deploy via `update-data.yml`.

**Spec:** `docs/superpowers/specs/2026-06-06-app-js-module-reorg-design.md`

**Reference game for manual checks:** Cyberpunk 2077, appId `1091500`.

---

## Module map (Phase A: `app.js` -> `js/app/`)

| Module | Functions / state moved from app.js |
|---|---|
| `config.js` | `SB_URL`, `SB_KEY`, `STEAM_IMG`, `SITE_BASE`, `IS_LOCAL_DEV`, `CDN`, `dataFilesHref`, `isNonSteamAppId`, `RATING_COLORS`, `RATING_TEXT`; plus the temporary `scoring`/`submit` bridge re-exports |
| `utils.js` | `normalizeOs`, `withTimeout`, `fmtDuration`, `fmtMinutes`, `reportKey`, `daysAgo`, `utcStamp`, `confColor`, `confTextColor`, `truncate`, `esc`, `cfgNa`, `downloadJson`, `configKey`, `hashReportKey`, `latestPerApp`, `latestPerClient`, `NA_SPAN` |
| `data.js` | `fetchCdn`, `fetchProtonDbLive`, `fetchSupabase`, `fetchNativeReports`, `fetchConfigPlaytimeTotals`, `_protonDbLiveCache` |
| `votes.js` | `fetchVotes`, `fetchUserVotes`, `castVote` |
| `signals.js` | `renderSignalIcon`, `renderSignalStrip`, `SIGNAL_ICON_SVG`, `ATOM_ICON_SVG` |
| `deck-status.js` | `fetchDeckStatusForApp`, `getDeckStatusForApp`, `fetchMinRequirements`, `renderDeckStatusButton`, `renderDeckStatusModalContent`, `isSteamDeckHardware`, `_deckCache`, `_reqsCache`, `DECK_STATUS_LABELS`, `DECK_CRITERIA_LABELS`, `DECK_CAT_MAP`, `DECK_DISPLAY_MAP`, `DECK_STATUS_ICON_SVG`, `_DECK_LCD_RE`, `_DECK_OLED_RE` |
| `author.js` | `getAuthorIdentity`, `fetchAuthorStats`, `fetchAuthorAvatar`, `renderAuthorBlock`, `enhanceAuthorBlocks`, `_authorCache` |
| `config-cards.js` | `buildFormRows`, `renderConfigCard`, `renderConfigsSection`, `FORM_RESPONSE_LABELS` |
| `report-card.js` | `renderPermalink`, `renderCard` |
| `home.js` | `renderHomePage`, `renderHomeFallback`, `renderActivityCard`, `renderPulseReportCards`, `fetchRecentPulseReports`, `fetchMatchingPulseConfigs`, `fetchMatchingPulseReportAppIds` |
| `game-page.js` | `renderGamePage`, `trendSummary` |
| `search.js` | `wireSearch` + former `app-search.js` body |
| `router.js` | `getRoute`, `route` |
| `main.js` | bootstrap: `hashchange`/`popstate`/`resize` listeners, `DOMContentLoaded` -> `route()` |

Import direction flows downward: `main.js` -> `router.js` -> `home.js`/`game-page.js` -> (`data.js`, `votes.js`, `report-card.js`, `author.js`, `signals.js`, `deck-status.js`, `config-cards.js`) -> `utils.js`/`config.js`. No cycles expected; `utils.js` and `config.js` import nothing from sibling app modules.

---

## Task A0: Create isolated worktree and branch

**Files:** none (git setup)

- [ ] **Step 1: Create worktree**

Run: `git -C /home/mike/src/decky-proton-pulse-project/proton-pulse-data worktree add -b reorg/app-js-modules ../pp-data-reorg origin/main`

(If worktree tooling is unavailable, fall back to `git checkout -b reorg/app-js-modules`.)

- [ ] **Step 2: Set author + confirm clean baseline**

Run: `git -C <worktree> config user.name "mdeguzis" && git -C <worktree> config user.email "mdeguzis@gmail.com" && git -C <worktree> status -sb`
Expected: clean tree on `reorg/app-js-modules`.

- [ ] **Step 3: Establish green baseline**

Run: `cd <worktree> && npx jest 2>&1 | tail -15`
Expected: all suites pass, coverage at/above 91/82/97/93. Record the numbers.

---

## Task A1: Derive the scoring/submit bridge symbols

**Files:** scratch only (informs `config.js`)

- [ ] **Step 1: List functions the siblings define**

Run: `grep -noE "^(async )?function [A-Za-z_]+|^const [A-Za-z_]+ *= *(async )?\(" app-scoring.js app-submit.js | sed -E 's/.*(function|const) ([A-Za-z_]+).*/\2/' | sort -u`

- [ ] **Step 2: Intersect with what app.js calls**

For each name from Step 1, run: `grep -nE "\b<name>\b" app.js | grep -v "function <name>"`
Record every sibling symbol app.js actually calls. This exact set becomes the bridge in `config.js` (Task A2).

---

## Task A2: js/app/config.js

**Files:**
- Create: `js/app/config.js`

- [ ] **Step 1: Write config.js**

```js
// Environment + constants for the app page, plus a temporary bridge to the
// scoring/submit functions that are still classic global scripts (removed in
// Phase B once those become js/shared/ modules).

export const SB_URL = 'https://ilsgdshkaocrmibwdezk.supabase.co/rest/v1';
export const SB_KEY = 'sb_publishable_3Oqhm4JneafJNQw9BuUaxw_L9qZa-5V';
export const STEAM_IMG = id => `https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/${id}/header.jpg`;
export const IS_LOCAL_DEV = ['localhost', '127.0.0.1', '0.0.0.0'].includes(window.location.hostname);

export const SITE_BASE = (() => {
  const parts = window.location.pathname.split('/').filter(Boolean);
  // (copy the exact body from app.js lines 7-13)
})();

export const CDN = IS_LOCAL_DEV /* copy exact ternary from app.js lines 15-20 */;
export const dataFilesHref = appId => IS_LOCAL_DEV /* copy app.js lines 21-26 */;
export const isNonSteamAppId = id => Number(id) > 10_000_000;
export const RATING_COLORS = { /* copy app.js lines 29-32 */ };
export const RATING_TEXT   = { /* copy app.js lines 33-39 */ };

// TEMPORARY Phase-A bridge: re-export the scoring/submit globals the app modules
// call. Replace with real imports from ../shared/ in Phase B (Task B6).
// One line per symbol found in Task A1, e.g.:
// export const computeConfidence = window.computeConfidence;
```

- [ ] **Step 2: Fill the bridge** with the exact symbols from Task A1 (`export const X = window.X;` per symbol), and copy the exact bodies marked `(copy ...)` from `app.js`.

- [ ] **Step 3: Verify syntax**

Run: `node --check js/app/config.js`
Expected: no output (pass).

- [ ] **Step 4: Commit**

Run: `git add js/app/config.js && git commit -m "refactor(app): add js/app/config.js (env + temp scoring/submit bridge)"`

---

## Task A3: js/app/utils.js

**Files:**
- Create: `js/app/utils.js`

- [ ] **Step 1: Move the pure helpers** listed in the module map (`normalizeOs` ... `latestPerClient`, `NA_SPAN`) verbatim from `app.js` into `js/app/utils.js`, prefixing each top-level declaration with `export`. `utils.js` imports nothing from sibling app modules. If any helper references `esc`/`NA_SPAN`, they are in this same file.

- [ ] **Step 2: Verify**

Run: `node --check js/app/utils.js`
Expected: pass.

- [ ] **Step 3: Commit**

Run: `git add js/app/utils.js && git commit -m "refactor(app): extract js/app/utils.js helpers"`

---

## Task A4-A10: Extract leaf render/data modules

Repeat this pattern for each module in order: **data.js, votes.js, signals.js, deck-status.js, author.js, config-cards.js, report-card.js.**

**Files (per task):**
- Create: `js/app/<module>.js`

- [ ] **Step 1: Move functions + private state** for that module (see map) verbatim from `app.js`, `export` each function that another module or `main.js`/`router.js` will call. Keep module-private caches/constants un-exported.

- [ ] **Step 2: Add imports.** Run `grep -oE "\b[a-zA-Z_]+\(" js/app/<module>.js | sed 's/($//' | sort -u` and, for any identifier defined in another already-created app module, add an `import { name } from './<other>.js';`. Pull shared constants/helpers from `./utils.js` and `./config.js`. Scoring/submit calls import from `./config.js` (the temp bridge).

- [ ] **Step 3: Verify**

Run: `node --check js/app/<module>.js`
Expected: pass.

- [ ] **Step 4: Commit**

Run: `git add js/app/<module>.js && git commit -m "refactor(app): extract js/app/<module>.js"`

Dependency notes for imports:
- `data.js` imports from `config.js` (`SB_URL`, `SB_KEY`, `CDN`, `dataFilesHref`, `withTimeout` from `utils.js`), `utils.js` (`latestPerClient`).
- `votes.js` imports `SB_URL`/`SB_KEY` from `config.js`.
- `signals.js` imports `esc` from `utils.js`.
- `deck-status.js` imports from `config.js`, `utils.js`, and `signals.js` (icon helpers if used).
- `author.js` imports `SB_URL`/`SB_KEY` from `config.js`, `esc` from `utils.js`.
- `config-cards.js` imports `esc`/`cfgNa`/`NA_SPAN`/`configKey` from `utils.js`, vote helpers from `votes.js` if referenced.
- `report-card.js` imports from `utils.js`, `signals.js`, `author.js`, `config-cards.js`, `votes.js`, `deck-status.js` as referenced.

---

## Task A11: js/app/home.js

**Files:**
- Create: `js/app/home.js`

- [ ] **Step 1: Move** `renderHomePage`, `renderHomeFallback`, `renderActivityCard`, `renderPulseReportCards`, `fetchRecentPulseReports`, `fetchMatchingPulseConfigs`, `fetchMatchingPulseReportAppIds`; `export renderHomePage` (called by router).
- [ ] **Step 2: Add imports** from `config.js`, `utils.js`, `data.js`, `report-card.js` as referenced (grep method from A4-A10 Step 2).
- [ ] **Step 3: Verify** `node --check js/app/home.js`
- [ ] **Step 4: Commit** `git add js/app/home.js && git commit -m "refactor(app): extract js/app/home.js"`

---

## Task A12: js/app/game-page.js

**Files:**
- Create: `js/app/game-page.js`

- [ ] **Step 1: Move** `renderGamePage` (whole, ~600 lines) and `trendSummary`; `export renderGamePage`.
- [ ] **Step 2: Add imports** — this is the heaviest importer: `config.js`, `utils.js`, `data.js`, `votes.js`, `report-card.js`, `author.js`, `signals.js`, `deck-status.js`, `config-cards.js`. Use the grep method, then add every matched cross-module symbol.
- [ ] **Step 3: Verify** `node --check js/app/game-page.js`
- [ ] **Step 4: Commit** `git add js/app/game-page.js && git commit -m "refactor(app): extract js/app/game-page.js"`

---

## Task A13: js/app/search.js

**Files:**
- Create: `js/app/search.js`
- Reference: `app-search.js`

- [ ] **Step 1: Move** `wireSearch` from `app.js` and the body of `app-search.js` into `js/app/search.js`; `export wireSearch` (and anything `main.js` needs). Convert the module-level `searchInput`/`searchResults` lookups to run inside `wireSearch` or on import.
- [ ] **Step 2: Add imports** from `config.js`/`utils.js`/`data.js` as referenced.
- [ ] **Step 3: Verify** `node --check js/app/search.js`
- [ ] **Step 4: Commit** `git add js/app/search.js && git commit -m "refactor(app): merge app-search.js into js/app/search.js"`

---

## Task A14: js/app/router.js + js/app/main.js

**Files:**
- Create: `js/app/router.js`, `js/app/main.js`

- [ ] **Step 1: router.js** — move `getRoute`, `route`; `export route`; import `renderHomePage` from `home.js`, `renderGamePage` from `game-page.js`.
- [ ] **Step 2: main.js**

```js
import { route } from './router.js';
import { wireSearch } from './search.js';

window.addEventListener('hashchange', () => route());
window.addEventListener('popstate', () => route());
window.addEventListener('resize', () => { /* copy app.js resize handler body */ });

document.addEventListener('DOMContentLoaded', () => {
  wireSearch();
  route();
});
```

(Copy the exact `resize` handler body from `app.js` lines ~1950.)

- [ ] **Step 3: Verify** `node --check js/app/router.js && node --check js/app/main.js`
- [ ] **Step 4: Commit** `git add js/app/router.js js/app/main.js && git commit -m "refactor(app): add js/app/router.js and main.js entry"`

---

## Task A15: Swap app.html and delete app.js / app-search.js

**Files:**
- Modify: `app.html:52-56`
- Delete: `app.js`, `app-search.js`

- [ ] **Step 1: Edit app.html** — remove these four lines:

```html
<script src="app-scoring.js?v=2"></script>
<script src="app-search.js?v=1"></script>
<script src="app-submit.js?v=4"></script>
<script src="app.js?v=f8bea2358"></script>
```

Keep `app-scoring.js` and `app-submit.js` **as classic scripts** (still bridged in Phase A) but drop their `?v=`:

```html
<script src="app-scoring.js"></script>
<script src="app-submit.js"></script>
<script type="module" src="js/app/main.js"></script>
```

Remove the `app-search.js` line entirely (now inside the module graph).

- [ ] **Step 2: Delete** `git rm app.js app-search.js`
- [ ] **Step 3: Commit** `git add app.html && git commit -m "refactor(app): load js/app/main.js module, drop classic app.js"`

---

## Task A16: Rewrite app-targeted tests

**Files:**
- Modify: `tests/appRenderCallers.test.js`, `tests/appPublishFilters.test.js`

- [ ] **Step 1: Inspect** what each asserts: `cat tests/appRenderCallers.test.js tests/appPublishFilters.test.js`. They currently `readFileSync(app.js)` / `vm`-eval. Identify the functions under test and which new module each now lives in.
- [ ] **Step 2: Rewrite** to `require`/`import` the specific `js/app/<module>.js`. For jsdom + ESM, use dynamic `await import('../js/app/<module>.js')` inside the test, or add a small `module.exports` shim only if the existing test harness needs CommonJS (match the pattern already used in `tests/adminAuth.test.js` for the admin modules).
- [ ] **Step 3: Run** `npx jest tests/appRenderCallers.test.js tests/appPublishFilters.test.js -v`
Expected: PASS.
- [ ] **Step 4: Full suite + coverage** `npx jest 2>&1 | tail -15`
Expected: all pass, thresholds held.
- [ ] **Step 5: Commit** `git add tests/ && git commit -m "test(app): point app tests at js/app/ modules"`

---

## Task A17: Manifest + smoke-test Phase A

**Files:**
- Modify: `gh-pages-manifest.txt`

- [ ] **Step 1: Manifest** — remove `app.js` and `app-search.js`; add `js/app/config.js`, `js/app/utils.js`, `js/app/data.js`, `js/app/votes.js`, `js/app/signals.js`, `js/app/deck-status.js`, `js/app/author.js`, `js/app/config-cards.js`, `js/app/report-card.js`, `js/app/home.js`, `js/app/game-page.js`, `js/app/search.js`, `js/app/router.js`, `js/app/main.js`.
- [ ] **Step 2: Serve + smoke** — `make serve` (background), then headless-Firefox smoke the app home page and a game page:

Run: `firefox --headless --new-instance -profile $(mktemp -d) --window-size=1400,900 --screenshot $HOME/storage/screenshots/reorg-app-home.png http://localhost:5173/app.html` and again with `http://localhost:5173/app.html#/app/1091500` -> `reorg-app-game.png`. Read both screenshots; confirm home cards and the Cyberpunk game page render with no blank/error state.

- [ ] **Step 3: Console-error check** — `make smoke` (the Selenium harness asserts DOM state and catches console errors on local staging).
Expected: pass.
- [ ] **Step 4: Stop server, commit** `git add gh-pages-manifest.txt && git commit -m "build(app): add js/app/ modules to gh-pages manifest"`

**Phase A done: app.html runs entirely on js/app/ modules, all other pages untouched and still green.**

---

## Phase B: Shared siblings -> js/shared/

## Task B1-B4: Convert siblings to modules

For each of **scoring (from app-scoring.js), submit (from app-submit.js), hardware (from app-hardware.js), chart-interactions (from app-chart-interactions.js):**

**Files:**
- Create: `js/shared/<name>.js`

- [ ] **Step 1: Copy** the sibling file body to `js/shared/<name>.js` and add `export` to each top-level function/const that any consumer calls (derive the consumer-called set with `grep` across `app.html` module + `submit.html`/`game-stats.html`/`confidence.html` inline + `game-stats.js`).
- [ ] **Step 2: Internal imports** — if a shared module calls another (e.g. hardware uses scoring), add `import { x } from './scoring.js';`.
- [ ] **Step 3: Verify** `node --check js/shared/<name>.js`
- [ ] **Step 4: Commit** `git add js/shared/<name>.js && git commit -m "refactor(shared): add js/shared/<name>.js"`

---

## Task B5: Point app at shared modules, remove temp bridge

**Files:**
- Modify: `js/app/config.js`, every `js/app/*.js` that used the bridge, `app.html`

- [ ] **Step 1: Replace bridge** — in `js/app/config.js`, delete the `window.*` bridge re-exports. In each app module that imported a scoring/submit symbol from `./config.js`, change the import to `import { x } from '../shared/scoring.js';` (or `submit.js`). Use `grep -rn "from './config.js'" js/app` to find them.
- [ ] **Step 2: app.html** — remove the classic `<script src="app-scoring.js">` and `<script src="app-submit.js">` lines (now imported by the module graph).
- [ ] **Step 3: Verify** `node --check` all changed files; `npx jest -v` for app tests.
- [ ] **Step 4: Commit** `git add js/app app.html && git commit -m "refactor(app): import scoring/submit from js/shared, drop temp bridge"`

---

## Task B6: Migrate submit.html

**Files:**
- Create: `js/submit/main.js`
- Modify: `submit.html`

- [ ] **Step 1:** Move `submit.html`'s inline `<script>` body (line 48) into `js/submit/main.js`; add `import { ... } from '../shared/scoring.js'` and `'../shared/submit.js'` for the symbols it uses (grep the inline body first).
- [ ] **Step 2:** In `submit.html`, remove `<script src="app-scoring.js">`, `<script src="app-submit.js">`, and the inline block; add `<script type="module" src="js/submit/main.js"></script>`.
- [ ] **Step 3: Verify** `node --check js/submit/main.js`
- [ ] **Step 4: Commit** `git add js/submit submit.html && git commit -m "refactor(submit): load js/submit/main.js module"`

---

## Task B7: Migrate game-stats.html

**Files:**
- Create: `js/game-stats/main.js`
- Modify: `game-stats.html`; Delete: `game-stats.js`

- [ ] **Step 1:** Move `game-stats.js` body into `js/game-stats/main.js`; add imports from `../shared/scoring.js`, `../shared/hardware.js`, `../shared/chart-interactions.js`, and keep `lib/scoring/gameStats.js` (load it as a module import if it has exports, else as a preceding classic script — check first with `grep -c "export" lib/scoring/gameStats.js`).
- [ ] **Step 2:** In `game-stats.html`, remove the `app-scoring.js`, `app-hardware.js?v=1`, `app-chart-interactions.js?v=1`, and `game-stats.js?v=1` scripts; add `<script type="module" src="js/game-stats/main.js"></script>`.
- [ ] **Step 3: Verify** `node --check js/game-stats/main.js`
- [ ] **Step 4: Commit** `git add js/game-stats game-stats.html && git rm game-stats.js && git commit -m "refactor(game-stats): load js/game-stats/main.js module"`

---

## Task B8: Migrate confidence.html

**Files:**
- Create: `js/confidence/main.js`
- Modify: `confidence.html`

- [ ] **Step 1:** Move `confidence.html`'s inline `<script>` (line 223) into `js/confidence/main.js`; add imports from `../shared/scoring.js`, `../shared/hardware.js`, `../shared/chart-interactions.js`.
- [ ] **Step 2:** In `confidence.html`, remove the three classic sibling scripts + inline block; add `<script type="module" src="js/confidence/main.js"></script>`.
- [ ] **Step 3: Verify** `node --check js/confidence/main.js`
- [ ] **Step 4: Commit** `git add js/confidence confidence.html && git commit -m "refactor(confidence): load js/confidence/main.js module"`

---

## Task B9: Rewrite shared-sibling tests

**Files:**
- Modify: `tests/submitReport.test.js`, `tests/chartInteractions.test.js`, `tests/hardware.test.js`, `tests/gameStats.test.js`

- [ ] **Step 1:** For each test, change the source path / require to the new `js/shared/<name>.js` (or `js/game-stats/main.js`) and assert on exports instead of vm-evaluated globals. Match the `tests/adminAuth.test.js` ESM pattern.
- [ ] **Step 2: Run each** `npx jest tests/submitReport.test.js tests/chartInteractions.test.js tests/hardware.test.js tests/gameStats.test.js -v`
Expected: PASS.
- [ ] **Step 3: Commit** `git add tests/ && git commit -m "test(shared): point sibling tests at js/shared modules"`

---

## Task B10: Manifest, full verification, delete old siblings

**Files:**
- Modify: `gh-pages-manifest.txt`; Delete: `app-scoring.js`, `app-submit.js`, `app-hardware.js`, `app-chart-interactions.js`

- [ ] **Step 1: Confirm no references remain** — `grep -rnE "app-(scoring|submit|hardware|chart-interactions)\.js" *.html` returns nothing.
- [ ] **Step 2: Delete** `git rm app-scoring.js app-submit.js app-hardware.js app-chart-interactions.js`
- [ ] **Step 3: Manifest** — remove those four entries; add `js/shared/*.js`, `js/submit/main.js`, `js/game-stats/main.js`, `js/confidence/main.js`.
- [ ] **Step 4: Full suite** `npx jest 2>&1 | tail -15`
Expected: all pass, coverage at/above 91/82/97/93.
- [ ] **Step 5: Smoke all four pages** — `make serve`, then headless-screenshot `app.html`, `app.html#/app/1091500`, `submit.html`, `game-stats.html`, `confidence.html`; read each, confirm render + no console errors via `make smoke`.
- [ ] **Step 6: Commit** `git add -A && git commit -m "build: finalize js/shared modules, remove classic siblings"`

---

## Task B11: Merge and deploy

- [ ] **Step 1:** `node --check` sweep: `for f in $(git ls-files 'js/**/*.js'); do node --check "$f" || echo "FAIL $f"; done` -> no FAIL lines.
- [ ] **Step 2:** Merge branch to `main` (PR or fast-forward per user preference). Confirm author `mdeguzis` on all commits: `git log origin/main..HEAD --pretty='%an <%ae>' | sort -u`.
- [ ] **Step 3:** Push `main`, then `gh workflow run update-data.yml --ref main -f pages_only=true -R mdeguzis/proton-pulse-data`.
- [ ] **Step 4: Verify deploy on branch, not CDN** — `git fetch origin gh-pages && git show origin/gh-pages:js/app/main.js | head -1` and confirm `js/shared/scoring.js` exists on `gh-pages`. (Live CDN caches ~10 min; see [[reference_ppdata_deploy_verify]].)
- [ ] **Step 5:** Remove worktree: `git worktree remove ../pp-data-reorg`.

---

## Notes / risks

- **No `?v=` cache-busters** on the new modules; the entry-path change busts the HTML reference, Pages TTL covers the rest (matches admin).
- **Missed cross-module import** is the top risk -> `node --check` is only syntax; rely on jest + the per-page smoke screenshots to catch runtime `ReferenceError`s.
- **`lib/scoring/gameStats.js`** may or may not be a module; check `grep -c export` before deciding how Task B7 loads it.
- Keep commits small (one module per commit) so a regression bisects to a single module.
