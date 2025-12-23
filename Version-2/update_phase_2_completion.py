"""
Update Phase 2 execution log with split table creation results
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

# Log the successful split table creation
logger.log_action("Split table created successfully in BigQuery")
logger.log_file_created("lead_scoring_splits", 
                       "savvy-gtm-analytics.ml_features.lead_scoring_splits", 
                       "Temporal train/test split assignments")

# Log split distribution metrics
logger.log_metric("Train Samples", 30727)
logger.log_metric("Train Positives", 1124)
logger.log_metric("Train Positive Rate", "3.66%")
logger.log_metric("Test Samples", 6919)
logger.log_metric("Test Positives", 288)
logger.log_metric("Test Positive Rate", "4.16%")
logger.log_metric("Gap Days", 32)

logger.log_validation_gate("G2.1.1", "Gap Days", True, 
                           f"32 days gap between train and test (need ≥30)")
logger.log_validation_gate("G2.1.2", "Class Balance", True,
                           f"Positive rates: Train 3.66%, Test 4.16% (within ±1% tolerance)")
logger.log_validation_gate("G2.1.3", "Sample Size", True,
                           f"Train: 30,727 samples, Test: 6,919 samples (both ≥1000)")
logger.log_validation_gate("G2.1.4", "No Overlap", True,
                           f"Train max: 2025-07-03, Test min: 2025-08-04 (32-day gap)")

logger.log_learning("Temporal split successfully created with 32-day gap")
logger.log_learning("Class balance is consistent across splits (3.66% vs 4.16%)")
logger.log_learning("Test set has slightly higher conversion rate, which is expected for more recent data")

print("\n✅ Phase 2.1 Temporal Split - COMPLETED")
print(f"   Table: savvy-gtm-analytics.ml_features.lead_scoring_splits")
print(f"   Train: 30,727 samples (3.66% positive)")
print(f"   Test: 6,919 samples (4.16% positive)")
print(f"   Gap: 32 days")

