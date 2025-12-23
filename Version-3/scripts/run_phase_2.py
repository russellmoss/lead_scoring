"""
Phase 2: Training Dataset Construction
Creates temporally correct train/validation/test splits
"""

import sys
from pathlib import Path
from google.cloud import bigquery
from datetime import datetime
import json

# Add Version-3 to path
BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-3")
sys.path.insert(0, str(BASE_DIR))

from utils.execution_logger import ExecutionLogger
from utils.date_configuration import load_date_configuration

def generate_temporal_split_sql(date_config: dict) -> str:
    """Generate SQL to create temporal train/validation/test splits"""
    
    sql = f"""
-- ============================================================================
-- PHASE 2.1: TEMPORAL TRAIN/VALIDATION/TEST SPLIT
-- ============================================================================
-- Using date configuration from Phase 0.0
--
-- Split Strategy:
-- - TRAIN: contacted_date <= train_end_date (oldest 70-80% of data)
-- - GAP: Between train_end_date and test_start_date (excluded to prevent leakage)
-- - TEST: contacted_date >= test_start_date AND <= test_end_date (newest 15-20% of data)
--
-- CRITICAL: Gap of {date_config['gap_days']} days prevents temporal leakage
-- ============================================================================

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
        WHEN contacted_date <= '{date_config['train_end_date']}' THEN 'TRAIN'
        WHEN contacted_date >= '{date_config['test_start_date']}' 
             AND contacted_date <= '{date_config['test_end_date']}' THEN 'TEST'
        ELSE 'GAP'  -- Leads in gap period (excluded from training)
    END as split_set,
    '{date_config['train_end_date']}' as train_end_date,
    '{date_config['test_start_date']}' as test_start_date,
    '{date_config['test_end_date']}' as test_end_date,
    {date_config['gap_days']} as gap_days
FROM lead_dates
"""
    return sql

def run_phase_2():
    """Execute Phase 2: Training Dataset Construction"""
    logger = ExecutionLogger()
    logger.start_phase("2.1", "Temporal Train/Validation/Test Split")
    
    # Load date configuration
    logger.log_action("Loading date configuration from Phase 0.0")
    date_config = load_date_configuration()
    
    logger.log_metric("Training Start", date_config['training_start_date'])
    logger.log_metric("Train End", date_config['train_end_date'])
    logger.log_metric("Test Start", date_config['test_start_date'])
    logger.log_metric("Test End", date_config['test_end_date'])
    logger.log_metric("Gap Days", date_config['gap_days'])
    
    # Generate SQL
    logger.log_action("Generating temporal split SQL")
    split_sql = generate_temporal_split_sql(date_config)
    
    # Save SQL to file
    sql_path = BASE_DIR / "sql" / "phase_2_temporal_split.sql"
    with open(sql_path, 'w', encoding='utf-8') as f:
        f.write(split_sql)
    logger.log_file_created("phase_2_temporal_split.sql", str(sql_path),
                           "Temporal split SQL")
    
    # Execute SQL
    logger.log_action("Executing temporal split SQL")
    client = bigquery.Client(project="savvy-gtm-analytics", location="northamerica-northeast2")
    
    try:
        job = client.query(split_sql, location="northamerica-northeast2")
        job.result()  # Wait for completion
        
        logger.log_learning("Temporal split table created successfully")
        
        # Validate split distribution
        logger.log_action("Validating split distribution")
        validation_query = """
        SELECT 
            split_set,
            COUNT(*) as lead_count,
            SUM(target) as positive_count,
            ROUND(AVG(target) * 100, 2) as positive_rate,
            MIN(contacted_date) as min_date,
            MAX(contacted_date) as max_date
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
        GROUP BY split_set
        ORDER BY 
            CASE split_set
                WHEN 'TRAIN' THEN 1
                WHEN 'GAP' THEN 2
                WHEN 'TEST' THEN 3
            END
        """
        validation_result = client.query(validation_query, location="northamerica-northeast2").to_dataframe()
        
        # Log split statistics
        for _, row in validation_result.iterrows():
            logger.log_metric(f"{row['split_set']} Count", f"{row['lead_count']:,}")
            logger.log_metric(f"{row['split_set']} Positive Rate", f"{row['positive_rate']}%")
            logger.log_metric(f"{row['split_set']} Date Range", 
                            f"{row['min_date']} to {row['max_date']}")
        
        # Get train and test counts
        train_row = validation_result[validation_result['split_set'] == 'TRAIN']
        test_row = validation_result[validation_result['split_set'] == 'TEST']
        gap_row = validation_result[validation_result['split_set'] == 'GAP']
        
        train_count = train_row['lead_count'].iloc[0] if len(train_row) > 0 else 0
        test_count = test_row['lead_count'].iloc[0] if len(test_row) > 0 else 0
        gap_count = gap_row['lead_count'].iloc[0] if len(gap_row) > 0 else 0
        
        # Validation gates
        if train_count >= 2000:
            logger.log_validation_gate("G2.1.1", "Train Set Size", True,
                                      f"{train_count:,} leads (>=2,000 required)")
        else:
            logger.log_validation_gate("G2.1.1", "Train Set Size", False,
                                      f"Only {train_count:,} leads (need >=2,000)")
        
        if test_count >= 500:
            logger.log_validation_gate("G2.1.2", "Test Set Size", True,
                                      f"{test_count:,} leads (>=500 required)")
        else:
            logger.log_validation_gate("G2.1.2", "Test Set Size", False,
                                      f"Only {test_count:,} leads (need >=500)")
        
        if date_config['gap_days'] >= 30:
            logger.log_validation_gate("G2.1.3", "Gap Days", True,
                                      f"{date_config['gap_days']} days gap (>=30 required)")
        else:
            logger.log_validation_gate("G2.1.3", "Gap Days", False,
                                      f"Only {date_config['gap_days']} days gap (need >=30)")
        
        # Validate temporal integrity (no overlap)
        logger.log_action("Validating temporal integrity (no overlap)")
        integrity_query = """
        WITH split_ranges AS (
            SELECT
                split_set,
                MIN(contacted_date) as min_date,
                MAX(contacted_date) as max_date
            FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
            WHERE split_set != 'GAP'
            GROUP BY split_set
        )
        SELECT
            t.split_set as train_split,
            t.max_date as train_max,
            ts.split_set as test_split,
            ts.min_date as test_min,
            DATE_DIFF(ts.min_date, t.max_date, DAY) as train_test_gap_days
        FROM split_ranges t
        JOIN split_ranges ts ON t.split_set = 'TRAIN' AND ts.split_set = 'TEST'
        """
        integrity_result = client.query(integrity_query, location="northamerica-northeast2").to_dataframe()
        
        if len(integrity_result) > 0:
            gap_days_actual = integrity_result['train_test_gap_days'].iloc[0]
            logger.log_metric("Actual Train-Test Gap", f"{gap_days_actual} days")
            
            if gap_days_actual >= 30:
                logger.log_validation_gate("G2.1.4", "Temporal Integrity", True,
                                          f"Gap of {gap_days_actual} days prevents temporal leakage")
            else:
                logger.log_validation_gate("G2.1.4", "Temporal Integrity", False,
                                          f"Gap of only {gap_days_actual} days (need >=30)")
        
        # Check positive rate consistency
        train_pos_rate = train_row['positive_rate'].iloc[0] if len(train_row) > 0 else 0
        test_pos_rate = test_row['positive_rate'].iloc[0] if len(test_row) > 0 else 0
        
        if abs(train_pos_rate - test_pos_rate) < 2.0:  # Within 2 percentage points
            logger.log_validation_gate("G2.1.5", "Positive Rate Consistency", True,
                                      f"Train: {train_pos_rate}%, Test: {test_pos_rate}% (difference < 2pp)")
        else:
            logger.log_validation_gate("G2.1.5", "Positive Rate Consistency", False,
                                      f"Train: {train_pos_rate}%, Test: {test_pos_rate}% (difference >= 2pp)")
        
        # Save split statistics
        split_stats = {
            'timestamp': datetime.now().isoformat(),
            'date_config': date_config,
            'split_distribution': validation_result.to_dict('records'),
            'temporal_integrity': integrity_result.to_dict('records') if len(integrity_result) > 0 else []
        }
        
        stats_path = BASE_DIR / "data" / "raw" / "split_statistics.json"
        with open(stats_path, 'w') as f:
            json.dump(split_stats, f, indent=2, default=str)
        logger.log_file_created("split_statistics.json", str(stats_path),
                               "Split distribution and validation statistics")
        
        logger.log_learning(f"Temporal split ensures no data leakage with {date_config['gap_days']}-day gap")
        logger.log_learning(f"Train set: {train_count:,} leads, Test set: {test_count:,} leads")
        
        logger.end_phase(
            status="PASSED",
            next_steps=["Proceed to Phase 3: Feature Selection & Validation"]
        )
        
    except Exception as e:
        logger.log_validation_gate("G2.1.0", "SQL Execution", False, str(e))
        logger.end_phase(status="FAILED")
        raise

if __name__ == "__main__":
    run_phase_2()
    print("\n=== PHASE 2.1 COMPLETE ===")
    print("Temporal split table created: ml_features.lead_scoring_splits")

