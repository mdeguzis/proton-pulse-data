#!/usr/bin/env python3
import gzip
import ijson
import json
import os
import sys
import argparse
from collections import defaultdict

def flush_buffer(buffer, data_dir):
    """Writes accumulated reports to individual appId.json files."""
    for app_id, reports in buffer.items():
        file_path = os.path.join(data_dir, f"{app_id}.json")
        
        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
        
        existing_data.extend(reports)
        
        # Deduplicate reports to prevent file growth during daily runs
        seen = set()
        unique_reports = []
        for r in existing_data:
            # Create a unique key based on timestamp and verdict
            fingerprint = f"{r.get('timestamp')}-{r.get('verdict')}"
            if fingerprint not in seen:
                unique_reports.append(r)
                seen.add(fingerprint)
        
        with open(file_path, "w") as f:
            # Minified output for Steam Deck performance
            json.dump(unique_reports, f, separators=(",", ":"))

def process_dump(dump_path, output_dir):
    """Streams the ProtonDB dump to keep memory usage low."""
    print(f"Opening active dump: {dump_path}")
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    buffer = defaultdict(list)
    report_count = 0
    unique_apps = set()

    try:
        with gzip.open(dump_path, "rb") as f:
            # ijson.items streams the array to avoid loading 2GB into RAM
            parser = ijson.items(f, "item")
            
            for report in parser:
                app_id = report.get("app", {}).get("appId")
                if not app_id:
                    continue

                # Filter fields to only what the Decky plugin needs
                simplified = {
                    "appId": app_id,
                    "verdict": report.get("responses", {}).get("verdict"),
                    "protonVersion": report.get("responses", {}).get("protonVersion"),
                    "timestamp": report.get("timestamp")
                }

                buffer[app_id].append(simplified)
                unique_apps.add(app_id)
                report_count += 1

                # Flush every 20,000 reports
                if report_count % 20000 == 0:
                    print(f"Processed {report_count} active reports...")
                    flush_buffer(buffer, data_dir)
                    buffer.clear()

        # Final flush for remaining reports
        flush_buffer(buffer, data_dir)
        
        with open(os.path.join(output_dir, "index.json"), "w") as f:
            json.dump({
                "total_reports": report_count,
                "total_games": len(unique_apps),
                "last_updated": report_count
            }, f, indent=2)

        print(f"\nProcessing complete: {report_count} reports for {len(unique_apps)} games.")

    except Exception as e:
        print(f"Critical Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dump")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    process_dump(args.dump, args.output_dir)

if __name__ == "__main__":
    main()
