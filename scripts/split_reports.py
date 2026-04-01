#!/usr/bin/env python3
import gzip
import ijson
import json
import os
import sys
import argparse
from collections import defaultdict

def flush_buffer(buffer, data_dir):
    """Saves buffered reports to app-specific JSON files."""
    for app_id, reports in buffer.items():
        file_path = os.path.join(data_dir, f"{app_id}.json")
        
        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    existing_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    existing_data = []
        
        # Merge and deduplicate
        existing_data.extend(reports)
        seen = set()
        unique_reports = []
        for r in existing_data:
            # Fingerprint to avoid duplicate entries in active pulls
            fp = f"{r.get('timestamp')}-{r.get('verdict')}"
            if fp not in seen:
                unique_reports.append(r)
                seen.add(fp)
        
        with open(file_path, "w") as f:
            json.dump(unique_reports, f, separators=(",", ":"))

def process_dump(dump_path, output_dir):
    """Streams the gzipped JSON dump to prevent OOM errors."""
    print(f"Processing dump: {dump_path}")
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    buffer = defaultdict(list)
    count = 0
    apps = set()

    try:
        with gzip.open(dump_path, "rb") as f:
            # Stream items array
            items = ijson.items(f, "item")
            for report in items:
                app_id = report.get("app", {}).get("appId")
                if not app_id:
                    continue

                buffer[app_id].append({
                    "appId": app_id,
                    "verdict": report.get("responses", {}).get("verdict"),
                    "proton": report.get("responses", {}).get("protonVersion"),
                    "ts": report.get("timestamp")
                })
                
                count += 1
                apps.add(app_id)

                if count % 20000 == 0:
                    print(f"Syncing... {count} reports handled.")
                    flush_buffer(buffer, data_dir)
                    buffer.clear()

        flush_buffer(buffer, data_dir)
        
        # Write stats for Proton Pulse dashboarding
        with open(os.path.join(output_dir, "status.json"), "w") as f:
            json.dump({"total": count, "games": len(apps)}, f, indent=2)

        print(f"Success! {count} reports updated.")

    except Exception as e:
        print(f"Python Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dump")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    process_dump(args.dump, args.output_dir)

if __name__ == "__main__":
    main()
