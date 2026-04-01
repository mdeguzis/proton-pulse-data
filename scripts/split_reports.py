import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Define the maximum number of reports per file
MAX_REPORTS_PER_FILE = 5000

# Function to process JSON reports

def process_reports(input_file):
    report_count = 0
    file_index = 0
    output_file = None
    output = []

    with open(input_file, 'r') as f:
        reports = json.load(f)

        total_reports = len(reports)
        logging.info(f'Total reports to process: {total_reports}') 

        for index, report in enumerate(reports):
            
            app_id = report.get('appId')
            v = report.get('rating')
            p = report.get('protonVersion')
            t = report.get('timestamp')

            # Process the report only if the necessary fields are present
            if app_id is not None and v is not None and p is not None and t is not None:
                output.append({'appId': app_id, 'v': v, 'p': p, 't': t})
                report_count += 1

                # Log progress
                logging.info(f'Processed report {index + 1}/{total_reports} from appId: {app_id}')

                # When max reports per file are reached, write to file
                if report_count >= MAX_REPORTS_PER_FILE:
                    if output_file:
                        output_file.close()
                    output_file_path = f'output_reports_{file_index}.json'
                    with open(output_file_path, 'w') as output_file:
                        json.dump(output, output_file)
                    logging.info(f'Written {report_count} reports to {output_file_path}')
                    file_index += 1
                    report_count = 0
                    output = []

        # Write any remaining reports to a new file
        if output:
            if output_file:
                output_file.close()
            output_file_path = f'output_reports_{file_index}.json'
            with open(output_file_path, 'w') as output_file:
                json.dump(output, output_file)
            logging.info(f'Written {report_count} reports to {output_file_path}')

# Call the function with the path to your input file
process_reports('input_reports.json')
