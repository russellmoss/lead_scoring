"""
Phase 0.0: Dynamic Date Configuration
Execute this script to run Phase 0.0 and set up the date configuration.
"""

import sys
import json
import os
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add Version-2 to path for imports
BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(BASE_DIR))

# Directory creation function
def create_directory_structure():
    """Create Version-2 directory structure."""
    DIRECTORIES = [
        BASE_DIR / "utils",
        BASE_DIR / "data" / "raw",
        BASE_DIR / "data" / "features",
        BASE_DIR / "data" / "scored",
        BASE_DIR / "models",
        BASE_DIR / "reports" / "shap",
        BASE_DIR / "notebooks",
        BASE_DIR / "sql",
        BASE_DIR / "inference",
    ]
    
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # Create __init__.py in utils
    init_file = BASE_DIR / "utils" / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# Lead Scoring v3 Utilities\n")
    
    print(f"\n📁 Directory structure created at: {BASE_DIR}")
    return BASE_DIR

# Main execution
if __name__ == "__main__":
    # Step 1: Create directory structure
    BASE_DIR = create_directory_structure()
    
    # Step 2: Import modules
    from utils.execution_logger import ExecutionLogger
    from utils.date_configuration import DateConfiguration
    
    # Step 3: Initialize logger and start phase
    logger = ExecutionLogger()
    logger.start_phase("0.0", "Dynamic Date Configuration")
    logger.log_action("Created Version-2 directory structure")
    logger.log_file_created("Version-2/", str(BASE_DIR), "Base directory for model v3")
    
    # Step 4: Create and validate date configuration
    logger.log_action("Calculating dynamic dates based on execution date")
    config = DateConfiguration()
    
    try:
        config.validate()
        logger.log_validation_gate("G0.0.1", "Date Configuration Valid", True, "All dates in correct order")
    except ValueError as e:
        logger.log_validation_gate("G0.0.1", "Date Configuration Valid", False, str(e))
        logger.end_phase(status="FAILED")
        raise
    
    # Step 5: Save configuration to Version-2 directory
    config_path = BASE_DIR / "date_config.json"
    with open(config_path, 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    
    logger.log_file_created("date_config.json", str(config_path), "Date configuration for all phases")
    
    # Log key metrics
    logger.log_metric("Execution Date", config.execution_date.strftime('%Y-%m-%d'))
    logger.log_metric("Training Start", config.training_start_date.strftime('%Y-%m-%d'))
    logger.log_metric("Training End", config.train_end_date.strftime('%Y-%m-%d'))
    logger.log_metric("Test Start", config.test_start_date.strftime('%Y-%m-%d'))
    logger.log_metric("Test End", config.test_end_date.strftime('%Y-%m-%d'))
    
    train_days = (config.train_end_date - config.training_start_date).days
    test_days = (config.test_end_date - config.test_start_date).days
    logger.log_metric("Training Days", train_days)
    logger.log_metric("Test Days", test_days)
    
    # Log learnings
    logger.log_learning(f"Training window covers {train_days} days ({train_days/30:.1f} months)")
    logger.log_learning(f"Firm data lag of {config.firm_data_lag_months} month(s) accounted for")
    
    # End phase
    logger.end_phase(
        status="PASSED",
        next_steps=[
            "Run Phase -1 pre-flight queries to verify data availability",
            "Proceed to Phase 0.1 Data Landscape Assessment"
        ]
    )
    
    # Print summary
    config.print_summary()
    print(f"\n✅ G0.0.1 PASSED: Date configuration validated and saved to {config_path}")

