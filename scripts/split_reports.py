import os
import json
import ijson
import sys
from datetime import datetime
from collections import defaultdict

def process_reports(input_dir, output_dir):
    # --- NEW DEBUG LOGGING ---
    abs_input = os.path.abspath(input_dir)
    print(f"DEBUG: Input directory (Absolute): {abs_input}")
    if not os.path.exists(abs_input):
        print(f"ERROR: Input directory does not exist: {abs_input}")
        return

    print(f"DEBUG: Scanning top-level: {os.listdir(abs_input)[:10]}...")
    # -------------------------

    game_reports = defaultdict(list)
    total_reports = 0
    
    # Recursively find all .json files in the official-data/reports directory
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        # Extract the appID from the filename (assuming it's {appID}.json)
                        app_id = os.path.splitext(file)[0]
                        
                        # Use ijson to handle potentially large files
                        parser = ijson.items(f, 'item')
                        for report in parser:
                            # Simplify the report structure
                            simplified = {
                                "v": report.get("verdict"),
                                "p": report.get("protonVersion"),
                                "t": report.get("timestamp")
                            }
                            game_reports[app_id].append(simplified)
                            total_reports += 1
                except Exception as e:
                    print(f"Warning: Failed to process {file_path}: {e}")

    # Ensure output directories exist
    data_dir = os.path.join(output_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    # Write per-game JSON files
    for app_id, reports in game_reports.items():
        # Sort by timestamp descending
        reports.sort(key=lambda x: x.get('t', ''), reverse=True)
        with open(os.path.join(data_dir, f"{app_id}.json"), 'w') as f:
            json.dump(reports, f)

    # Create health-check manifest
    manifest = {
        "last_updated": datetime.utcnow().isoformat(),
        "total_games": len(game_reports),
        "total_reports": total_reports
    }
    
    with open(os.path.join(output_dir, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"Success! {total_reports} reports across {len(game_reports)} games.")
    print(f"Manifest written to: {os.path.join(output_dir, 'manifest.json')}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 split_reports.py <input_dir> <output_dir>")
        sys.exit(1)
    process_reports(sys.argv[1], sys.argv[2])
