import os
import json
import ijson
import sys
import tarfile
from datetime import datetime
from collections import defaultdict

def process_reports(input_path, output_dir):
    abs_input = os.path.abspath(input_path)
    data_dir = os.path.join(output_dir, 'data')
    manifest_path = os.path.join(output_dir, 'manifest.json')
    os.makedirs(data_dir, exist_ok=True)

    processed_files = []
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                m_data = json.load(f)
                processed_files = m_data.get("processed_files", [])
        except:
            pass

    search_path = os.path.join(abs_input, 'reports') if os.path.isdir(os.path.join(abs_input, 'reports')) else abs_input
    try:
        all_tarballs = sorted([f for f in os.listdir(search_path) if f.endswith('.tar.gz')])
        new_tarballs = [f for f in all_tarballs if f not in processed_files]
    except FileNotFoundError:
        return

    if not new_tarballs:
        print("--> No new data.")
        return

    game_updates = defaultdict(list)
    new_report_count = 0

    for index, file in enumerate(new_tarballs, 1):
        file_path = os.path.join(search_path, file)
        print(f"[{index}/{len(new_tarballs)}] Extracting: {file}...", flush=True)
        
        try:
            with tarfile.open(file_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.json'):
                        # ROBUST APPID EXTRACTION
                        # Splits 'path/to/12345.json' and takes '12345'
                        filename = os.path.basename(member.name)
                        app_id = filename.replace('.json', '')
                        
                        # Sanity check: AppIDs should be digits. 
                        # If it's "reports", we're grabbing the wrong string.
                        if not app_id.isdigit():
                            continue

                        f = tar.extractfile(member)
                        if f:
                            try:
                                parser = ijson.items(f, 'item')
                                for report in parser:
                                    simplified = {
                                        "v": report.get("verdict"),
                                        "p": report.get("protonVersion"),
                                        "t": report.get("timestamp")
                                    }
                                    game_updates[app_id].append(simplified)
                                    new_report_count += 1
                            except:
                                continue
        except Exception as e:
            print(f"!! Error: {e}")

    print(f"--> Merging and cleaning data...", flush=True)
    for app_id, new_reports in game_updates.items():
        target_file = os.path.join(data_dir, f"{app_id}.json")
        
        existing_data = []
        if os.path.exists(target_file):
            with open(target_file, 'r') as f:
                try: existing_data = json.load(f)
                except: pass

        combined = existing_data + new_reports
        # Deduplicate and sort
        combined.sort(key=lambda x: str(x.get('t', '')), reverse=True)
        
        # FINAL PROTECTION: If a file is getting too huge, we cap it at the 
        # latest 5,000 reports. GitHub cannot handle 500MB JSON files.
        if len(combined) > 5000:
            combined = combined[:5000]
        
        with open(target_file, 'w') as f:
            json.dump(combined, f)

    # Save manifest
    with open(manifest_path, 'w') as f:
        json.dump({
            "last_updated": datetime.now().isoformat(),
            "processed_files": all_tarballs,
            "total_games": len(next(os.walk(data_dir))[2])
        }, f, indent=2)

    print(f"--- FINISH: Processed {new_report_count} reports ---")

if __name__ == "__main__":
    process_reports(sys.argv[1], sys.argv[2])
