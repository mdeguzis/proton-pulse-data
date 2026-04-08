[![Update ProtonDB Data](https://github.com/mdeguzis/proton-pulse-data/actions/workflows/update-data.yml/badge.svg)](https://github.com/mdeguzis/proton-pulse-data/actions/workflows/update-data.yml) [![pages-build-deployment](https://github.com/mdeguzis/proton-pulse-data/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/mdeguzis/proton-pulse-data/actions/workflows/pages/pages-build-deployment)

# proton-pulse-data

Monthly-updated GitHub Pages CDN for ProtonDB per-game community reports.
Consumed by the [decky-proton-pulse](https://github.com/mdeguzis/decky-proton-pulse) plugin.

## Endpoints

```
GET https://mdeguzis.github.io/proton-pulse-data/data/{appId}/index.json
GET https://mdeguzis.github.io/proton-pulse-data/data/{appId}/{year}.json
GET https://mdeguzis.github.io/proton-pulse-data/data/{appId}/latest.json
GET https://mdeguzis.github.io/proton-pulse-data/
```

## Data format

Each `data/{appId}/{year}.json` and `data/{appId}/latest.json` is a JSON array
of normalized Proton Pulse report objects:

```json
[
  {
    "appId": "730",
    "cpu": "AMD Ryzen 7 5800X3D",
    "duration": "severalHours",
    "gpu": "AMD Radeon RX 6800 XT",
    "gpuDriver": "Mesa 23.1.0",
    "kernel": "6.8.0",
    "notes": "Runs great.",
    "os":  "Arch Linux",
    "protonVersion": "Proton 8.0-5",
    "ram": "32 GB",
    "rating": "platinum",
    "timestamp": 1693526400,
    "title": ""
  }
]
```

`data/{appId}/index.json` contains the sorted list of year files available for
that game, and `latest.json` mirrors the most recent year bucket.

## Update schedule

Runs automatically each day via GitHub Actions.
Source: [bdefore/protondb-data](https://github.com/bdefore/protondb-data) monthly dumps.

## Live backfills

Some games are missing from the monthly upstream dump even though ProtonDB live
detailed report data exists. Those games can be added to
`config/live_backfill_app_ids.json`, and the pipeline will materialize normal
`data/{appId}/...` files for them during the build.

## Triggering manually

Go to **Actions → Update ProtonDB Data → Run workflow**.

## Supabase backups

This repo includes a helper for creating downloadable logical Supabase backups
with the Supabase CLI, following the documented `db dump` flow for `roles`,
`schema`, and `data` exports.

The default `make` target uses an already-linked local Supabase CLI project, so
you can avoid putting your database URL or password in shell history:

```bash
cd proton-pulse-data
npx --yes supabase link
make backup-supabase
```

If you prefer a non-interactive or CI-style flow, the script still supports an
explicit database URL:

```bash
cd proton-pulse-data
SUPABASE_DB_URL='postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres' \
  bash scripts/backup_supabase.sh
```

Outputs are written to `data/supabase/<timestamp>/` plus a matching
`.tar.gz` archive, and are ignored by git. You can override the location or
name with:

```bash
SUPABASE_BACKUP_DIR=artifacts/supabase
SUPABASE_BACKUP_LABEL=nightly
```

This is intended to be easy to lift into GitHub Actions later by supplying
`SUPABASE_DB_URL` from repository secrets and uploading the generated archive
as a workflow artifact.

## Steam catalog coverage

The coverage report can optionally expand to the full Steam game catalog when
`STEAM_API_KEY` is available. For local runs, place the key in a local `.env`
file at the repo root:

```env
STEAM_API_KEY=your_key_here
```

That file is ignored by git. In GitHub Actions, the workflow writes the secret
into the same `.env` shape during the build so local and CI behavior stay
consistent.

The Steam app ID pull is backed by the vendored
`vendor/Steam-Games-Scraper` git submodule while that project remains active.
After cloning this repo, initialize submodules before running local commands:

```bash
make setup
```

or:

```bash
git submodule update --init --recursive
```

The GitHub Actions probe pass is chunked into resumable cache-backed checkpoints.
Each chunk saves `.cache/protondb-summary-probe-cache.json` under a fresh cache key
so an interrupted multi-hour run can resume from the latest completed chunk rather
than restarting the whole probe sweep.

## Local development setup

Bootstrap the local toolchain with:

```bash
make setup
```

That setup flow now:
- initializes git submodules
- installs `shellcheck` with `sudo apt install -y shellcheck` when missing
- installs the Python dev environment with `uv`

## Storage strategy

The `gh-pages` branch is an orphan with a single commit — it is force-pushed
each run so no history accumulates. Repo size equals the current dataset only.
