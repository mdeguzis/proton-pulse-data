import os
import sys
import json
import tarfile
import ijson
import argparse
import subprocess
import tempfile
import time
from urllib import error, request
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

DEBUG = False
LIVE_COUNTS_URL = "https://www.protondb.com/data/counts.json"
LIVE_REPORTS_URL = "https://www.protondb.com/data/reports/{device}/app/{hash}.json"
LIVE_REPORT_DEVICE = "all-devices"
BACKFILL_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "config" / "live_backfill_app_ids.json"


def log(msg, debug=False):
    """Flush-safe print for CI environments. Skipped if debug=True and DEBUG is off."""
    if debug and not DEBUG:
        return
    print(msg, flush=True)


def clone_repo(url, target_dir):
    log(f"[clone] Cloning {url} -> {target_dir}", debug=True)
    result = subprocess.run(
        ["git", "clone", "--depth=1", url, target_dir],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log(f"!! git clone failed:\n{result.stderr}")
        sys.exit(1)
    log(f"[clone] Clone complete.", debug=True)


def process_data(input_dir, output_dir):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    data_output_path = output_path / "data"
    data_output_path.mkdir(parents=True, exist_ok=True)

    log(f"[init] Input dir : {input_path.resolve()}")
    log(f"[init] Output dir: {data_output_path.resolve()}")

    if not input_path.exists():
        log(f"!! ERROR: Input directory does not exist: {input_path}")
        sys.exit(1)

    all_files = list(input_path.iterdir())
    log(f"[init] Files found in input dir: {len(all_files)}", debug=True)
    for f in sorted(all_files)[:20]:
        size = f.stat().st_size if f.is_file() else 0
        log(f"  {f.name}  ({size:,} bytes)", debug=True)
    if len(all_files) > 20:
        log(f"  ... and {len(all_files) - 20} more", debug=True)

    parsed_count = 0
    index_keys: set[tuple] = set()
    pipeline_start = time.time()

    # 1. Handle Raw JSON files
    json_files = sorted(input_path.glob("*.json"))
    log(f"\n[json] Found {len(json_files)} raw JSON file(s)")
    for index, json_file in enumerate(json_files, start=1):
        size = json_file.stat().st_size
        log(f"[json] Processing {index}/{len(json_files)}: {json_file.name} ({size:,} bytes)")
        t0 = time.time()
        with open(json_file, 'r') as f:
            count, src_keys = parse_and_split(f, data_output_path, source_label=json_file.name)
        elapsed = time.time() - t0
        log(f"[json] Done: {count:,} reports in {elapsed:.1f}s")
        parsed_count += count
        index_keys.update(src_keys)

    # 2. Handle Tarballs (backwards compatibility)
    tar_files = sorted(input_path.glob("*.tar.gz"))
    log(f"\n[tar] Found {len(tar_files)} tarball(s)")
    for index, tar_file in enumerate(tar_files, start=1):
        size = tar_file.stat().st_size
        log(f"[tar] Processing {index}/{len(tar_files)}: {tar_file.name} ({size:,} bytes)")
        t0 = time.time()
        try:
            with tarfile.open(tar_file, "r:gz") as tar:
                members = [m for m in tar.getmembers() if m.name.endswith(".json")]
                log(f"[tar]   Streaming {len(members)} JSON member(s) from archive", debug=True)
                for member in members:
                    log(f"[tar]   -> {member.name} ({member.size:,} bytes)", debug=True)
                    f = tar.extractfile(member)
                    if f:
                        count, src_keys = parse_and_split(f, data_output_path, source_label=member.name)
                        log(f"[tar]      {count:,} reports parsed")
                        parsed_count += count
                        index_keys.update(src_keys)
        except Exception as e:
            log(f"!! Failed to process {tar_file.name}: {e}")
        elapsed = time.time() - t0
        log(f"[tar] Done: {elapsed:.1f}s")

    if parsed_count == 0:
        log(f"!! ERROR: No reports were parsed from {input_dir}.")
        log(f"!! Found {len(json_files)} JSONs and {len(tar_files)} tarballs.")
        sys.exit(1)

    backfilled_keys = backfill_missing_apps(data_output_path)
    index_keys.update(backfilled_keys)
    generate_latest_files(data_output_path)
    generate_app_indexes(index_keys, data_output_path)
    generate_index_html(index_keys, output_path)
    log_summary(parsed_count, data_output_path, output_path, pipeline_start, backfilled_keys)
    log("Done!")


def parse_and_split(file_handle, data_output_path, source_label="?"):
    """
    Stream-parse a report array and write output as:
        data/{appId}/{year}.json
    Each year file is a JSON array of all reports for that app in that year.
    Appends to existing year files so multiple source archives merge correctly.
    Deduplicates by timestamp to guard against the same archive appearing both
    as a loose .json and inside a .tar.gz in the same reports/ folder.
    """
    count = 0
    skipped = 0

    # Buffer in-memory per (appId, year) to minimize file open/close churn
    buffer: dict[tuple, list] = defaultdict(list)

    parser = ijson.items(file_handle, 'item')

    for report in parser:
        app_id = report.get("appId")
        if not app_id:
            skipped += 1
            continue

        ts = report.get("timestamp")
        try:
            year = str(datetime.fromtimestamp(int(ts), tz=timezone.utc).year) if ts else "unknown"
        except (ValueError, OSError):
            year = "unknown"

        buffer[(str(app_id), year)].append(report)
        count += 1

        if count % 10000 == 0:
            log(f"  [parse] {source_label}: {count:,} reports buffered...", debug=True)

    log(f"  [parse] {source_label}: flushing {len(buffer)} app/year buckets to disk...", debug=True)
    flush_start = time.time()

    for (app_id, year), new_reports in buffer.items():
        app_dir = data_output_path / app_id
        app_dir.mkdir(exist_ok=True)
        year_file = app_dir / f"{year}.json"

        existing = []
        if year_file.exists():
            try:
                with open(year_file, "r") as yf:
                    existing = json.load(yf)
            except Exception:
                existing = []

        # Deduplicate by timestamp — guards against the same archive appearing
        # both as a loose .json and inside a .tar.gz in the same reports/ folder.
        seen_timestamps = {r.get("timestamp") for r in existing}
        added = 0
        for r in new_reports:
            ts = r.get("timestamp")
            if ts not in seen_timestamps:
                existing.append(r)
                seen_timestamps.add(ts)
                added += 1

        if added < len(new_reports):
            dupes = len(new_reports) - added
            log(f"  [dedup] appId={app_id} year={year}: skipped {dupes} duplicate(s)", debug=True)

        with open(year_file, "w") as yf:
            json.dump(existing, yf, indent=2)

    flush_elapsed = time.time() - flush_start
    log(f"  [parse] {source_label}: flush done in {flush_elapsed:.1f}s", debug=True)

    if skipped:
        log(f"  [parse] {source_label}: skipped {skipped} records missing appId", debug=True)

    return count, set(buffer.keys())


def fetch_json(url: str):
    with request.urlopen(url) as response:
        return json.load(response)


def load_backfill_app_ids(manifest_path: Path = BACKFILL_MANIFEST_PATH) -> list[str]:
    if not manifest_path.exists():
        log(f"[backfill] No manifest found at {manifest_path}; skipping live backfill", debug=True)
        return []

    raw = json.loads(manifest_path.read_text())
    if not isinstance(raw, list):
        raise ValueError(f"Backfill manifest must be a JSON array: {manifest_path}")

    app_ids: list[str] = []
    for entry in raw:
        app_id = str(entry).strip()
        if not app_id or not app_id.isdigit():
            raise ValueError(f"Invalid app id in backfill manifest: {entry!r}")
        app_ids.append(app_id)
    return sorted(set(app_ids), key=int)


def compute_js_hash(seed: str) -> int:
    hash_value = 0
    for ch in f"{seed}m":
        hash_value = ((hash_value << 5) - hash_value + ord(ch)) & 0xFFFFFFFF
    if hash_value & 0x80000000:
        hash_value -= 0x100000000
    return abs(hash_value)


def compute_live_report_hash(app_id: int, report_count: int, timestamp: int, page: str | int) -> int:
    left = f"{report_count}p{app_id * (report_count % timestamp)}"
    try:
        page_value = int(page)
        right_multiplier = str(page_value * (app_id % timestamp))
    except (TypeError, ValueError):
        right_multiplier = "nan"
    right = f"{app_id}p{right_multiplier}"
    return compute_js_hash(f"p{left}*vRT{right}{str(None)}")


def normalize_whitespace(value):
    return value.strip() if isinstance(value, str) else ""


def infer_duration(playtime_minutes):
    if not playtime_minutes or playtime_minutes <= 0:
        return "unreported"
    if playtime_minutes < 60:
        return "underOneHour"
    if playtime_minutes < 240:
        return "oneToFourHours"
    if playtime_minutes < 900:
        return "severalHours"
    return "allTheTime"


LIVE_REPORT_FAULT_KEYS = [
    "audioFaults",
    "graphicalFaults",
    "inputFaults",
    "performanceFaults",
    "saveGameFaults",
    "significantBugs",
    "stabilityFaults",
    "windowingFaults",
]


def infer_live_rating(responses: dict | None) -> str:
    verdict = normalize_whitespace((responses or {}).get("verdict")).lower()
    if not verdict:
        return "pending"
    if verdict == "no":
        return "borked"
    if verdict != "yes":
        return "pending"

    fault_count = sum(1 for key in LIVE_REPORT_FAULT_KEYS if (responses or {}).get(key) == "yes")
    if fault_count >= 3:
        return "bronze"
    if fault_count == 2:
        return "silver"
    if fault_count == 1:
        return "gold"
    if (responses or {}).get("triedOob") == "yes" or (responses or {}).get("verdictOob") == "yes":
        return "platinum"
    return "gold"


def normalize_live_detailed_reports(app_id: str, raw_reports: list[dict]) -> list[dict]:
    normalized = []
    for report in raw_reports:
        responses = report.get("responses") or {}
        steam = (((report.get("device") or {}).get("inferred") or {}).get("steam") or {})
        contributor_steam = ((report.get("contributor") or {}).get("steam") or {})
        playtime = contributor_steam.get("playtimeLinux", contributor_steam.get("playtime"))
        notes = normalize_whitespace(
            ((responses.get("notes") or {}).get("concludingNotes"))
            or ((responses.get("notes") or {}).get("verdict"))
            or (responses.get("notes") if isinstance(responses.get("notes"), str) else "")
        )
        timestamp = report.get("timestamp")
        if not isinstance(timestamp, int) or timestamp <= 0:
            continue

        normalized.append({
            "appId": app_id,
            "cpu": normalize_whitespace(steam.get("cpu")),
            "duration": infer_duration(playtime),
            "gpu": normalize_whitespace(steam.get("gpu")),
            "gpuDriver": normalize_whitespace(steam.get("gpuDriver")),
            "kernel": normalize_whitespace(steam.get("kernel")),
            "notes": notes,
            "os": normalize_whitespace(steam.get("os")),
            "protonVersion": normalize_whitespace(responses.get("protonVersion")) or "Unknown",
            "ram": normalize_whitespace(steam.get("ram")),
            "rating": infer_live_rating(responses),
            "timestamp": timestamp,
            "title": "",
        })

    return normalized


def bucket_reports_by_year(reports: list[dict]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for report in reports:
        ts = report.get("timestamp")
        try:
            year = str(datetime.fromtimestamp(int(ts), tz=timezone.utc).year) if ts else "unknown"
        except (ValueError, OSError):
            year = "unknown"
        buckets[year].append(report)
    return dict(buckets)


def count_year_bucket_files(data_output_path: Path) -> int:
    count = 0
    for app_dir in data_output_path.iterdir():
        if not app_dir.is_dir():
            continue
        for json_file in app_dir.glob("*.json"):
            if json_file.stem in {"index", "latest", "votes"}:
                continue
            count += 1
    return count


def write_bucketed_reports(data_output_path: Path, app_id: str, year_buckets: dict[str, list[dict]]) -> set[tuple]:
    app_dir = data_output_path / app_id
    app_dir.mkdir(parents=True, exist_ok=True)
    written_keys: set[tuple] = set()

    for year, reports in year_buckets.items():
        year_file = app_dir / f"{year}.json"
        year_file.write_text(json.dumps(reports, indent=2))
        written_keys.add((app_id, year))

    return written_keys


def backfill_missing_apps(
    data_output_path: Path,
    fetch_json_impl=fetch_json,
    manifest_path: Path = BACKFILL_MANIFEST_PATH,
) -> set[tuple]:
    configured_app_ids = load_backfill_app_ids(manifest_path)
    existing_app_ids = {path.name for path in data_output_path.iterdir() if path.is_dir()}
    missing_app_ids = [app_id for app_id in configured_app_ids if app_id not in existing_app_ids]

    if not missing_app_ids:
        log("[backfill] No missing app IDs require live backfill", debug=True)
        return set()

    log(f"[backfill] Resolving {len(missing_app_ids)} missing app(s) via live ProtonDB detailed data")
    counts = fetch_json_impl(LIVE_COUNTS_URL)
    if not isinstance(counts, dict):
        raise ValueError("Live ProtonDB counts payload was not a JSON object")

    report_count = counts.get("reports")
    timestamp = counts.get("timestamp")
    if not isinstance(report_count, int) or not isinstance(timestamp, int) or report_count <= 0 or timestamp <= 0:
        raise ValueError("Live ProtonDB counts payload did not contain usable report/timestamp seeds")

    written_keys: set[tuple] = set()
    for app_id in missing_app_ids:
        hash_value = compute_live_report_hash(int(app_id), report_count, timestamp, "all")
        live_url = LIVE_REPORTS_URL.replace("{device}", LIVE_REPORT_DEVICE).replace("{hash}", str(hash_value))
        log(f"[backfill] Fetching app {app_id} from {live_url}")
        try:
            payload = fetch_json_impl(live_url)
        except error.HTTPError as exc:
            log(f"[backfill] Skipping {app_id}: live detailed request returned HTTP {exc.code}")
            continue
        except error.URLError as exc:
            log(f"[backfill] Skipping {app_id}: live detailed request failed: {exc}")
            continue

        reports = normalize_live_detailed_reports(app_id, payload.get("reports") or [])
        if not reports:
            log(f"[backfill] Skipping {app_id}: live detailed payload had no usable reports")
            continue

        year_buckets = bucket_reports_by_year(reports)
        written_keys.update(write_bucketed_reports(data_output_path, app_id, year_buckets))
        log(f"[backfill] Wrote {sum(len(rows) for rows in year_buckets.values())} reports across {len(year_buckets)} year file(s) for {app_id}")

    return written_keys


def log_summary(
    parsed_count: int,
    data_output_path: Path,
    output_path: Path,
    pipeline_start: float,
    backfilled_keys: set[tuple],
) -> None:
    total_elapsed = time.time() - pipeline_start
    unique_apps = sum(1 for p in data_output_path.iterdir() if p.is_dir())
    total_year_files = count_year_bucket_files(data_output_path)
    backfilled_apps = len({app_id for app_id, _year in backfilled_keys})
    backfilled_year_files = len(backfilled_keys)

    log(f"\n[summary] Total reports parsed    : {parsed_count:,}")
    log(f"[summary] Unique app directories  : {unique_apps:,}")
    log(f"[summary] Total year bucket files : {total_year_files:,}")
    log(f"[summary] Backfilled app IDs      : {backfilled_apps:,}")
    log(f"[summary] Backfilled year buckets : {backfilled_year_files:,}")
    log(f"[summary] Main index file         : {(output_path / 'index.html').resolve()}")
    log(f"[summary] Total time              : {total_elapsed:.1f}s")
    log(f"[summary] Output dir              : {data_output_path.resolve()}")


def generate_latest_files(data_output_path: Path) -> None:
    """
    For each app directory, create latest.json containing the reports
    from the most recent year file.
    """
    count = 0
    for app_dir in data_output_path.iterdir():
        if not app_dir.is_dir():
            continue
        year_files = sorted(app_dir.glob("*.json"), key=lambda p: p.stem)
        # Exclude any existing latest.json from the sort
        year_files = [f for f in year_files if f.stem != "latest"]
        if not year_files:
            continue
        latest_src = year_files[-1]
        latest_dst = app_dir / "latest.json"
        latest_dst.write_bytes(latest_src.read_bytes())
        count += 1
    log(f"[latest] Generated {count} latest.json files", debug=True)


def generate_app_indexes(index_keys: set, data_output_path: Path) -> None:
    """
    Write data/{appId}/index.json for each app — a sorted list of available years.
    The plugin fetches this to discover which year files to merge for a game.
    """
    app_years: dict[str, list[str]] = {}
    for (app_id, year) in index_keys:
        app_years.setdefault(app_id, []).append(year)

    for app_id, years in app_years.items():
        sorted_years = sorted(years, key=lambda y: (0, int(y)) if y.isdigit() else (1, y))
        app_dir = data_output_path / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        index_file = app_dir / "index.json"
        index_file.write_text(json.dumps(sorted_years))
        log(f"[app-index] {app_id}/index.json -> {sorted_years}")


def generate_index_html(index_keys: set, output_path: Path) -> None:
    """
    Write index.html to output_path listing all data/{appId}/{year}.json files
    as a collapsible tree using native <details>/<summary> elements.
    index_keys is a set of (appId, year) tuples.
    """
    # Collect {appId: [year, ...]} sorted numerically
    app_years: dict[str, list[str]] = {}
    for (app_id, year) in index_keys:
        app_years.setdefault(app_id, []).append(year)

    sorted_app_ids = sorted(app_years.keys(), key=lambda a: (0, int(a)) if a.isdigit() else (1, a))
    for app_id in sorted_app_ids:
        app_years[app_id] = sorted(app_years[app_id], key=lambda y: (0, int(y)) if y.isdigit() else (1, y))

    # Well-known Steam app IDs for quick reference
    SAMPLE_APPS = {
        "730": "Counter-Strike 2",
        "570": "Dota 2",
        "440": "Team Fortress 2",
        "292030": "The Witcher 3",
        "1245620": "Elden Ring",
        "1091500": "Cyberpunk 2077",
        "1174180": "Red Dead Redemption 2",
        "413150": "Stardew Valley",
        "814380": "Sekiro",
        "1086940": "Baldur's Gate 3",
    }

    # Build sample links for apps that exist in the dataset
    sample_entries = []
    for app_id, name in SAMPLE_APPS.items():
        if app_id in app_years:
            sample_entries.append(f'<a href="data/{app_id}/latest.json">{name}</a> ({app_id})')

    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        "  <title>proton-pulse-data index</title>",
        "</head>",
        "<body>",
        "<h1>proton-pulse-data index</h1>",
        "<p>Monthly-updated ProtonDB per-game community reports. "
        f"<strong>{len(sorted_app_ids)}</strong> games tracked.</p>",
    ]

    if sample_entries:
        lines.append("<h2>Popular titles</h2>")
        lines.append("<p>" + " &middot; ".join(sample_entries) + "</p>")

    lines += [
        "<h2>All games (by app ID)</h2>",
        "<ul>",
    ]

    for app_id in sorted_app_ids:
        lines.append("  <li>")
        lines.append("    <details>")
        lines.append(f"      <summary>{app_id}/</summary>")
        lines.append("      <ul>")
        latest_href = f"data/{app_id}/latest.json"
        lines.append(f'        <li><a href="{latest_href}"><strong>latest.json</strong></a></li>')
        for year in app_years[app_id]:
            href = f"data/{app_id}/{year}.json"
            lines.append(f'        <li><a href="{href}">{year}.json</a></li>')
        lines.append("      </ul>")
        lines.append("    </details>")
        lines.append("  </li>")

    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines += [
        "</ul>",
        f"<p>Generated: {now}</p>",
        "</body>",
        "</html>",
    ]

    index_file = output_path / "index.html"
    index_file.write_text("\n".join(lines) + "\n")
    log(f"[index] Written: {index_file}", debug=True)


def main():
    parser = argparse.ArgumentParser(
        description="Split ProtonDB reports into data/{appId}/{year}.json buckets"
    )
    parser.add_argument(
        "input_dir", nargs="?",
        help="Local directory containing JSON/tar.gz report files"
    )
    parser.add_argument(
        "output_dir", nargs="?",
        help="Output directory root (split files go under <output_dir>/data/)"
    )
    parser.add_argument(
        "--url",
        help="Git repo URL to clone as data source (e.g. https://github.com/bdefore/protondb-data)"
    )
    parser.add_argument(
        "--subfolder", default="reports",
        help="Subfolder within the cloned repo to use as input (default: reports)"
    )
    parser.add_argument(
        "--output", dest="output_dir_flag",
        help="Output directory (alternative to positional arg)"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable verbose debug logging"
    )
    args = parser.parse_args()

    global DEBUG
    DEBUG = args.debug

    output_dir = args.output_dir or args.output_dir_flag
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix="protondb-output-")
        log(f"[init] No output_dir specified, using temp dir: {output_dir}")

    if args.url:
        tmp_dir = tempfile.mkdtemp(prefix="protondb-clone-")
        clone_repo(args.url, tmp_dir)
        input_dir = os.path.join(tmp_dir, args.subfolder)
        log(f"[init] Using cloned subfolder: {input_dir}", debug=True)
    elif args.input_dir:
        input_dir = args.input_dir
    else:
        log("!! ERROR: provide input_dir or --url")
        parser.print_help()
        sys.exit(1)

    process_data(input_dir, output_dir)


if __name__ == "__main__":
    main()
