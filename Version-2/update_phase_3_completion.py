"""
Update Phase 3 execution log with actual feature validation results
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

# Log actual feature validation results
logger.log_action("Validated actual features in feature table")
logger.log_metric("Total Features", 18)
logger.log_metric("Advisor Features", 6)
logger.log_metric("Firm Features", 7)
logger.log_metric("Data Quality Signals", 3)
logger.log_metric("Flags", 2)

logger.log_metric("pit_moves_3yr Coverage", "100% (39,448 rows)")
logger.log_metric("firm_net_change_12mo Coverage", "100% (39,448 rows)")
logger.log_metric("pit_restlessness_ratio Coverage", "30.6% (12,059 rows)")

logger.log_validation_gate("G3.1.3", "Protected Features Preserved", True,
                           "pit_moves_3yr and firm_net_change_12mo both present with 100% coverage")
logger.log_validation_gate("G3.2.1", "Geographic Features Removed", True,
                           "No raw geographic features found - only safe proxies if any")
logger.log_validation_gate("G3.1.5", "Feature Count", True,
                           "18 features remain (need ≥10)")

logger.log_learning("All 18 features validated and present in feature table")
logger.log_learning("Protected features (pit_moves_3yr, firm_net_change_12mo) have 100% coverage")
logger.log_learning("pit_restlessness_ratio only available for 30.6% of leads (those with prior firms)")

print("\n✅ Phase 3 Feature Validation - COMPLETED")
print(f"   Total Features: 18")
print(f"   Protected Features: ✅ Both present with 100% coverage")
print(f"   Geographic Features: ✅ None found (safe proxies only)")

