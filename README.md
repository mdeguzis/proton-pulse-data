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

## Storage strategy

The `gh-pages` branch is an orphan with a single commit — it is force-pushed
each run so no history accumulates. Repo size equals the current dataset only.
