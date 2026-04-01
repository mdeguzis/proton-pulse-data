#!/usr/bin/env python3
import gzip
import ijson
import json
import os
import sys
import argparse
from collections import defaultdict

def flush_buffer(buffer, data_dir):
    """
    Writes accumulated reports to their respective appId.json files.
    """
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
        
        with open(file_path, "w") as f:
            # Minify JSON to save space on GitHub Pages
            json.dump(existing_data, f, separators=(",", ":"))

def process_dump(dump_path, output_dir):
    """
    Streams a large .json.gz file and splits it into per-game files.
    """
    print(f"Opening dump: {dump_path}")
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    buffer = defaultdict(list)
    report_count = 0
    unique_apps = set()

    try:
        # Open the gzipped file in binary mode for ijson
        with gzip.open(dump_path, "rb") as f:
            # ijson.items streams objects from the root array
            parser = ijson.items(f, "item")
            
            for report in parser:
                app_data = report.get("app", {})
                app_id = app_data.get("appId")
                
                if not app_id:
                    continue

                # Filter and simplify data to keep the Decky plugin fast
                # We only keep what the ProtonDBReport type actually uses
                simplified = {
                    "appId": app_id,
                    "verdict": report.get("responses", {}).get("verdict"),
                    "protonVersion": report.get("responses", {}).get("protonVersion"),
                    "gpu": report.get("systemInfo", {}).get("gpu"),
                    "timestamp": report.get("timestamp")
                }

                buffer[app_id].append(simplified)
                unique_apps.add(app_id)
                report_count += 1

                # Flush to disk every 15,000 records to balance RAM and Speed
                if report_count % 15000 == 0:
                    print(f"Processed {report_count} reports...")
                    flush_buffer(buffer, data_dir)
                    buffer.clear()

        # Final flush for remaining reports
        flush_buffer(buffer, data_dir)
        
        # Create an index.json for general stats or debugging
        index_path = os.path.join(output_dir, "index.json")
        with open(index_path, "w") as f:
            json.dump({
                "total_reports": report_count,
                "total_games": len(unique_apps),
                "last_updated": sys.argv[0] # or use a timestamp
            }, f, indent=2)

        print(f"\nSuccess!")
        print(f"Total Reports: {report_count}")
        print(f"Total Games:   {len(unique_apps)}")

    except Exception as e:
        print(f"Error processing dump: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Split ProtonDB dump into per-game JSON files.")
    parser.add_argument("dump", help="Path to reports.json.gz")
    parser.add_argument("output_dir", help="Directory to output the 'data/' folder")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.dump):
        print(f"Error: {args.dump} not found.")
        sys.exit(1)

    process_dump(args.dump, args.output_dir)

if __name__ == "__main__":
    main()
