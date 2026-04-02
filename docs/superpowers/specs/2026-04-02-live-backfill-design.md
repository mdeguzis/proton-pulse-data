# Design: proton-pulse-data Live Backfill

**Date:** 2026-04-02
**Status:** Approved

## Summary

Move the "missing mirror data" recovery path out of the Decky plugin and into
`proton-pulse-data`.

The pipeline will keep using the monthly `bdefore/protondb-data` dump as the
primary source, but it will also support a curated manifest of app IDs whose
`data/{appId}/index.json` would otherwise be missing. For those app IDs, the
pipeline will fetch ProtonDB live detailed report data during the build and
emit the same per-app year-bucket files the plugin already consumes.

## Goals

- Eliminate runtime "mirror miss" complexity for known missing games
- Preserve the existing CDN shape:
  - `data/{appId}/index.json`
  - `data/{appId}/{year}.json`
  - `data/{appId}/latest.json`
- Keep the plugin’s normal mirror code path working unchanged
- Make backfills explicit and reviewable in-repo

## Non-Goals

- Backfilling every Steam app automatically
- Replacing the monthly upstream dump
- Encoding live-summary-only placeholder records

## Architecture

Add a manifest file:

`config/live_backfill_app_ids.json`

This file is a JSON array of numeric Steam app IDs. During `scripts/split_reports.py`:

1. Split the official dump exactly as today.
2. Discover which manifest app IDs are still missing from `data/`.
3. Fetch ProtonDB live `counts.json` once.
4. Derive each app’s live detailed report hash using the same algorithm already
   proven in the plugin.
5. Fetch the live detailed page for each missing app.
6. Normalize the response into Proton Pulse CDN report objects.
7. Bucket the reports by year and write:
   - `data/{appId}/{year}.json`
8. Fold those new `(appId, year)` pairs into the normal:
   - `index.json`
   - `latest.json`
   - root `index.html`

## Why Curated Manifest Instead Of "All Missing Apps"

The pipeline has no authoritative global list of Steam app IDs that "should"
exist but do not appear in the monthly dump. A curated manifest is the smallest
reliable step that:

- removes the runtime pain for known problem titles
- keeps the build cost bounded
- avoids speculative scraping breadth
- gives us a simple review surface when we add more backfills later

## Initial Seed

Seed the manifest with:

- `2561580` — Horizon Zero Dawn Remastered

This is the app ID already confirmed in plugin logs as a real mirror miss with
working live detailed fallback data.

## Testing

Add unit coverage for:

- manifest parsing
- hash-based live backfill fetch flow
- year-bucket file generation for a missing app
- skip behavior when the app already exists locally
