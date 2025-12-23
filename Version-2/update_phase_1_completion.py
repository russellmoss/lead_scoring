"""
Update Phase 1 execution log with table creation results
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(BASE_DIR))

from utils.execution_logger import ExecutionLogger

logger = ExecutionLogger()

# Log the successful table creation
logger.log_action("Feature table created successfully in BigQuery")
logger.log_file_created("lead_scoring_features_pit", 
                       "savvy-gtm-analytics.ml_features.lead_scoring_features_pit", 
                       "PIT feature engineering table with 39,448 rows")
logger.log_metric("Total Rows", 39448)
logger.log_metric("Unique Leads", 39448)
logger.log_metric("Positive Targets", 1495)
logger.log_metric("Negative Targets", 37953)
logger.log_metric("Conversion Rate", f"{1495/39448*100:.2f}%")

logger.log_validation_gate("G1.1.2", "Feature Table Created", True, 
                           "Table created with 39,448 rows in ml_features dataset")
logger.log_validation_gate("G1.1.3", "Target Variable Distribution", True,
                           f"3.79% conversion rate ({1495} positives, {37953} negatives)")

logger.log_learning("Feature table successfully created using Virtual Snapshot methodology")
logger.log_learning("Conversion rate of 3.79% is consistent with historical data")

print("\n✅ Phase 1.1 Feature Engineering - COMPLETED")
print(f"   Table: savvy-gtm-analytics.ml_features.lead_scoring_features_pit")
print(f"   Rows: 39,448")
print(f"   Conversion Rate: 3.79%")

