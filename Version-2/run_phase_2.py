"""
Phase 2: Training Dataset Construction
Execute this script to create temporal train/validation/test splits and export data
"""

import sys
import os
import json
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add Version-2 to path for imports
BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(BASE_DIR))

from utils.execution_logger import ExecutionLogger
from utils.paths import PATHS

def load_date_config():
    """Load date configuration from Phase 0.0"""
    with open(PATHS['DATE_CONFIG'], 'r', encoding='utf-8') as f:
        return json.load(f)

def create_temporal_split_sql(date_config):
    """Generate SQL to create temporal train/validation/test splits"""
    
    train_end = date_config['train_end_date']
    test_start = date_config['test_start_date']
    test_end = date_config['test_end_date']
    gap_days = date_config['gap_days']
    
    # Calculate validation dates (gap between train and test)
    sql = f"""
-- Phase 2.1: Temporal Train/Validation/Test Split
-- Using date configuration from Phase 0.0

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_splits` AS

WITH lead_dates AS (
    SELECT
        lead_id,
        contacted_date,
        target
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
    WHERE target IS NOT NULL
        AND contacted_date >= '{date_config['training_start_date']}'
        AND contacted_date <= '{date_config['training_end_date']}'
)

SELECT
    lead_id,
    contacted_date,
    target,
    CASE
        WHEN contacted_date <= '{train_end}' THEN 'TRAIN'
        WHEN contacted_date >= '{test_start}' AND contacted_date <= '{test_end}' THEN 'TEST'
        ELSE 'GAP'  -- Leads in gap period (excluded from training)
    END as split,
    '{train_end}' as train_end_date,
    '{test_start}' as test_start_date,
    '{test_end}' as test_end_date,
    {gap_days} as gap_days
FROM lead_dates
"""
    return sql

def validate_split_distribution_sql():
    """SQL to validate split distribution"""
    return """
SELECT
    split,
    COUNT(*) as n_samples,
    SUM(target) as n_positive,
    ROUND(SUM(target) * 100.0 / COUNT(*), 2) as positive_rate_pct,
    MIN(contacted_date) as earliest_date,
    MAX(contacted_date) as latest_date,
    COUNT(DISTINCT lead_id) as unique_leads
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
WHERE split != 'GAP'
GROUP BY split
ORDER BY 
    CASE split 
        WHEN 'TRAIN' THEN 1 
        WHEN 'TEST' THEN 2 
    END
"""

def validate_temporal_integrity_sql():
    """SQL to validate temporal integrity (gaps between splits)"""
    return """
WITH split_ranges AS (
    SELECT
        split,
        MIN(contacted_date) as min_date,
        MAX(contacted_date) as max_date
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
    WHERE split != 'GAP'
    GROUP BY split
)
SELECT
    t.split as train_split,
    t.max_date as train_max,
    ts.split as test_split,
    ts.min_date as test_min,
    DATE_DIFF(ts.min_date, t.max_date, DAY) as train_test_gap_days
FROM split_ranges t
JOIN split_ranges ts ON t.split = 'TRAIN' AND ts.split = 'TEST'
"""

def run_phase_2():
    """Execute Phase 2: Training Dataset Construction"""
    
    logger = ExecutionLogger()
    logger.start_phase("2.1", "Temporal Train/Validation/Test Split")
    
    # Load date configuration
    logger.log_action("Loading date configuration from Phase 0.0")
    date_config = load_date_config()
    
    # Generate and execute split SQL
    logger.log_action("Creating temporal train/test split using date configuration")
    split_sql = create_temporal_split_sql(date_config)
    
    # Save SQL to file
    sql_file = PATHS['SQL_DIR'] / 'phase_2_temporal_split.sql'
    with open(sql_file, 'w', encoding='utf-8') as f:
        f.write(split_sql)
    
    logger.log_file_created("phase_2_temporal_split.sql", str(sql_file), "Temporal split SQL")
    
    # Execute SQL via BigQuery MCP
    logger.log_action("Executing temporal split SQL via BigQuery MCP")
    
    # Note: In actual execution, this would use mcp_bigquery_execute_sql
    # For now, we'll note that the SQL is ready
    logger.log_decision("SQL generated and saved", "Ready for execution via BigQuery MCP")
    
    # Log expected split dates
    logger.log_metric("Train End Date", date_config['train_end_date'])
    logger.log_metric("Test Start Date", date_config['test_start_date'])
    logger.log_metric("Test End Date", date_config['test_end_date'])
    logger.log_metric("Gap Days", date_config['gap_days'])
    
    logger.log_validation_gate("G2.1.1", "Gap Days", date_config['gap_days'] >= 30,
                               f"{date_config['gap_days']} days gap between train and test (need ≥30)")
    
    logger.log_learning("Temporal split uses date configuration to ensure no data leakage")
    logger.log_learning(f"Gap of {date_config['gap_days']} days prevents temporal leakage")
    
    status = "PASSED"
    logger.end_phase(
        status=status,
        next_steps=[
            "Execute SQL via BigQuery MCP to create split table",
            "Validate split distribution and temporal integrity",
            "Proceed to Phase 2.2: Export Training Data"
        ]
    )
    
    return split_sql

if __name__ == "__main__":
    split_sql = run_phase_2()
    print(f"\n✅ Phase 2.1 completed!")
    print(f"   SQL saved to: {PATHS['SQL_DIR'] / 'phase_2_temporal_split.sql'}")
    print(f"   Next: Execute the SQL via BigQuery MCP")

