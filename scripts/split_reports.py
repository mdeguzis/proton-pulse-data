#!/usr/bin/env python3
import json
import os
import argparse
from collections import defaultdict

def process_reports(input_dir, output_dir):
    print(f"Scanning for reports in: {input_dir}")
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    report_count = 0
    apps_processed = set()
    buffer = defaultdict(list)

    # bdefore/protondb-data stores reports in subdirectories (reports/A/filename.json)
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith(".json"):
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r") as f:
                    report = json.load(f)
                
                app_id = report.get("app", {}).get("appId")
                if not app_id:
                    continue

                entry = {
                    "v": report.get("responses", {}).get("verdict"),
                    "p": report.get("responses", {}).get("protonVersion"),
                    "ts": report.get("timestamp")
                }

                buffer[str(app_id)].append(entry)
                apps_processed.add(str(app_id))
                report_count += 1

                if report_count % 10000 == 0:
                    flush_to_disk(buffer, data_dir)
                    buffer.clear()
                    print(f"Processed {report_count} reports...")

            except Exception as e:
                pass 

    flush_to_disk(buffer, data_dir)
    
    # Create the Health Check manifest
    manifest = {
        "total_reports": report_count,
        "total_games": len(apps_processed),
        "last_sync": "$(date -u +%Y-%m-%dT%H:%M:%SZ)" # Placeholder for shell replacement
    }
    
    with open(os.path.join(output_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f)

    print(f"Success! {report_count} reports across {len(apps_processed)} games.")

def flush_to_disk(buffer, data_dir):
    for app_id, new_reports in buffer.items():
        target_path = os.path.join(data_dir, f"{app_id}.json")
        existing = []
        if os.path.exists(target_path):
            with open(target_path, "r") as f:
                try: existing = json.load(f)
                except: existing = []
        
        combined = existing + new_reports
        unique = []
        seen = set()
        for r in combined:
            key = f"{r.get('ts')}-{r.get('v')}"
            if key not in seen:
                unique.append(r)
                seen.add(key)
        
        unique.sort(key=lambda x: x.get('ts', 0), reverse=True)
        with open(target_path, "w") as f:
            json.dump(unique, f, separators=(",", ":"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args()
    process_reports(args.input_dir, args.output_dir)
