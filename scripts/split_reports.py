#!/usr/bin/env python3
import gzip
import ijson
import json
import os
import sys
import argparse
from collections import defaultdict

def flush_buffer(buffer, data_dir):
    for app_id, reports in buffer.items():
        file_path = os.path.join(data_dir, f"{app_id}.json")
        
        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    existing_data = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    existing_data = []
        
        existing_data.extend(reports)
        
        # Deduplicate to prevent file bloat during daily syncs
        seen = set()
        unique_reports = []
        for r in existing_data:
            fp = f"{r.get('ts')}-{r.get('v')}"
            if fp not in seen:
                unique_reports.append(r)
                seen.add(fp)
        
        # Sort by timestamp (newest first)
        unique_reports.sort(key=lambda x: x.get('ts', 0), reverse=True)
        
        with open(file_path, "w") as f:
            json.dump(unique_reports, f, separators=(",", ":"))

def process_dump(dump_path, output_dir):
    print(f"Opening active dump: {dump_path}")
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    buffer = defaultdict(list)
    count = 0
    apps = set()

    try:
        with gzip.open(dump_path, "rb") as f:
            # ijson streams the 2GB file so the GH Runner doesn't crash
            items = ijson.items(f, "item")
            for report in items:
                app_id = report.get("app", {}).get("appId")
                if not app_id:
                    continue

                # Short keys (v=verdict, p=proton, ts=timestamp) to save bandwidth
                buffer[app_id].append({
                    "v": report.get("responses", {}).get("verdict"),
                    "p": report.get("responses", {}).get("protonVersion"),
                    "ts": report.get("timestamp")
                })
                
                count += 1
                apps.add(app_id)

                if count % 25000 == 0:
                    print(f"Syncing... {count} reports processed.")
                    flush_buffer(buffer, data_dir)
                    buffer.clear()

        flush_buffer(buffer, data_dir)
        
        with open(os.path.join(output_dir, "status.json"), "w") as f:
            json.dump({"total": count, "games": len(apps)}, f, indent=2)

        print(f"Done! {count} reports synced for {len(apps)} games.")

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
