import logging
import time

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReportSplitter:
    def __init__(self, reports):
        self.reports = reports
        self.total_reports = len(reports)

    def split_reports(self):
        for i, report in enumerate(self.reports):
            logging.info(f"Processing report {i + 1}/{self.total_reports}: {report}")
            # Simulate processing time
            time.sleep(1)  # Placeholder for actual processing logic
            logging.info(f"Completed report {i + 1}/{self.total_reports}")

# Example usage
if __name__ == '__main__':
    reports = ['report1', 'report2', 'report3', 'report4']  # Placeholder for report list
    splitter = ReportSplitter(reports)
    splitter.split_reports()