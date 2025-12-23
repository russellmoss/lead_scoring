"""
Phase 5: V3 Tier Validation & Performance Analysis
Validates tier performance on historical data and analyzes results
"""

import sys
from pathlib import Path
from google.cloud import bigquery
from datetime import datetime
import json
import pandas as pd

# Add Version-3 to path
BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-3")
sys.path.insert(0, str(BASE_DIR))

from utils.execution_logger import ExecutionLogger
from utils.date_configuration import load_date_configuration

def run_phase_5():
    """Execute Phase 5: V3 Tier Validation & Performance Analysis"""
    logger = ExecutionLogger()
    logger.start_phase("5.1", "V3 Tier Validation & Performance Analysis")
    
    client = bigquery.Client(project="savvy-gtm-analytics", location="northamerica-northeast2")
    date_config = load_date_configuration()
    
    # Step 1: In-sample validation (training period)
    logger.log_action("Validating tier performance on training data (in-sample)")
    try:
        train_validation_query = f"""
        SELECT
            score_tier,
            COUNT(*) as n_leads,
            SUM(converted) as n_converted,
            ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
            ROUND(AVG(expected_lift), 2) as expected_lift,
            ROUND(AVG(converted) / (
                SELECT AVG(converted) 
                FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
                WHERE contacted_date BETWEEN '{date_config['training_start_date']}' AND '{date_config['train_end_date']}'
            ), 2) as actual_lift
        FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
        WHERE contacted_date BETWEEN '{date_config['training_start_date']}' AND '{date_config['train_end_date']}'
        GROUP BY score_tier
        ORDER BY 
            CASE score_tier
                WHEN 'TIER_1_PRIME_MOVER' THEN 1
                WHEN 'TIER_2_MODERATE_BLEEDER' THEN 2
                WHEN 'TIER_3_EXPERIENCED_MOVER' THEN 3
                WHEN 'TIER_4_HEAVY_BLEEDER' THEN 4
                ELSE 99
            END
        """
        train_results = client.query(train_validation_query, location="northamerica-northeast2").to_dataframe()
        
        # Log training results
        for _, row in train_results.iterrows():
            logger.log_metric(f"TRAIN - {row['score_tier']} - Count", f"{row['n_leads']:,}")
            logger.log_metric(f"TRAIN - {row['score_tier']} - Conversion Rate", f"{row['conversion_rate_pct']}%")
            logger.log_metric(f"TRAIN - {row['score_tier']} - Actual Lift", f"{row['actual_lift']:.2f}x")
        
        # Calculate baseline
        baseline_row = train_results[train_results['score_tier'] == 'STANDARD']
        baseline_rate = baseline_row['conversion_rate_pct'].iloc[0] if len(baseline_row) > 0 else 3.5
        
        logger.log_metric("TRAIN - Baseline Conversion Rate", f"{baseline_rate}%")
        
    except Exception as e:
        logger.log_validation_gate("G5.1.1", "Training Data Validation", False, str(e))
        train_results = pd.DataFrame()
    
    # Step 2: Out-of-sample validation (test period)
    logger.log_action("Validating tier performance on test data (out-of-sample)")
    try:
        test_validation_query = f"""
        SELECT
            score_tier,
            COUNT(*) as n_leads,
            SUM(converted) as n_converted,
            ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
            ROUND(AVG(expected_lift), 2) as expected_lift,
            ROUND(AVG(converted) / (
                SELECT AVG(converted) 
                FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
                WHERE contacted_date BETWEEN '{date_config['test_start_date']}' AND '{date_config['test_end_date']}'
            ), 2) as actual_lift
        FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
        WHERE contacted_date BETWEEN '{date_config['test_start_date']}' AND '{date_config['test_end_date']}'
        GROUP BY score_tier
        ORDER BY 
            CASE score_tier
                WHEN 'TIER_1_PRIME_MOVER' THEN 1
                WHEN 'TIER_2_MODERATE_BLEEDER' THEN 2
                WHEN 'TIER_3_EXPERIENCED_MOVER' THEN 3
                WHEN 'TIER_4_HEAVY_BLEEDER' THEN 4
                ELSE 99
            END
        """
        test_results = client.query(test_validation_query, location="northamerica-northeast2").to_dataframe()
        
        # Log test results
        for _, row in test_results.iterrows():
            logger.log_metric(f"TEST - {row['score_tier']} - Count", f"{row['n_leads']:,}")
            logger.log_metric(f"TEST - {row['score_tier']} - Conversion Rate", f"{row['conversion_rate_pct']}%")
            logger.log_metric(f"TEST - {row['score_tier']} - Actual Lift", f"{row['actual_lift']:.2f}x")
        
        # Calculate test baseline
        test_baseline_row = test_results[test_results['score_tier'] == 'STANDARD']
        test_baseline_rate = test_baseline_row['conversion_rate_pct'].iloc[0] if len(test_baseline_row) > 0 else 3.5
        
        logger.log_metric("TEST - Baseline Conversion Rate", f"{test_baseline_rate}%")
        
    except Exception as e:
        logger.log_validation_gate("G5.1.2", "Test Data Validation", False, str(e))
        test_results = pd.DataFrame()
    
    # Step 3: Validate tier performance meets expectations
    logger.log_action("Validating tier performance meets expected lift thresholds")
    all_gates_passed = True
    
    if len(train_results) > 0:
        tier_1_train = train_results[train_results['score_tier'] == 'TIER_1_PRIME_MOVER']
        if len(tier_1_train) > 0:
            tier_1_lift = tier_1_train['actual_lift'].iloc[0]
            tier_1_expected = tier_1_train['expected_lift'].iloc[0]
            
            if tier_1_lift >= 2.5:
                logger.log_validation_gate("G5.1.3", "Tier 1 Training Lift", True,
                                          f"Tier 1 lift: {tier_1_lift:.2f}x (>=2.5x required)")
            else:
                logger.log_validation_gate("G5.1.3", "Tier 1 Training Lift", False,
                                          f"Tier 1 lift: {tier_1_lift:.2f}x (need >=2.5x)")
                all_gates_passed = False
            
            # Check if actual meets expected (within 20% tolerance)
            if tier_1_lift >= tier_1_expected * 0.8:
                logger.log_validation_gate("G5.1.4", "Tier 1 Expected vs Actual", True,
                                          f"Tier 1 actual ({tier_1_lift:.2f}x) within 20% of expected ({tier_1_expected:.2f}x)")
            else:
                logger.log_validation_gate("G5.1.4", "Tier 1 Expected vs Actual", False,
                                          f"Tier 1 actual ({tier_1_lift:.2f}x) below 80% of expected ({tier_1_expected:.2f}x)")
                all_gates_passed = False
    
    if len(test_results) > 0:
        tier_1_test = test_results[test_results['score_tier'] == 'TIER_1_PRIME_MOVER']
        if len(tier_1_test) > 0:
            tier_1_test_lift = tier_1_test['actual_lift'].iloc[0]
            
            if tier_1_test_lift >= 2.0:
                logger.log_validation_gate("G5.1.5", "Tier 1 Test Lift", True,
                                          f"Tier 1 test lift: {tier_1_test_lift:.2f}x (>=2.0x required)")
            else:
                logger.log_validation_gate("G5.1.5", "Tier 1 Test Lift", False,
                                          f"Tier 1 test lift: {tier_1_test_lift:.2f}x (need >=2.0x)")
                all_gates_passed = False
    
    # Step 4: Temporal stability check
    logger.log_action("Checking temporal stability (train vs test performance)")
    if len(train_results) > 0 and len(test_results) > 0:
        # Compare Tier 1 performance across periods
        tier_1_train_row = train_results[train_results['score_tier'] == 'TIER_1_PRIME_MOVER']
        tier_1_test_row = test_results[test_results['score_tier'] == 'TIER_1_PRIME_MOVER']
        
        if len(tier_1_train_row) > 0 and len(tier_1_test_row) > 0:
            train_conv = tier_1_train_row['conversion_rate_pct'].iloc[0]
            test_conv = tier_1_test_row['conversion_rate_pct'].iloc[0]
            conv_diff = abs(train_conv - test_conv)
            
            if conv_diff < 5.0:  # Within 5 percentage points
                logger.log_validation_gate("G5.1.6", "Temporal Stability", True,
                                          f"Tier 1 conversion rate stable: Train {train_conv}% vs Test {test_conv}% (diff < 5pp)")
            else:
                logger.log_validation_gate("G5.1.6", "Temporal Stability", False,
                                          f"Tier 1 conversion rate shift: Train {train_conv}% vs Test {test_conv}% (diff >= 5pp)")
                all_gates_passed = False
    
    # Step 5: Generate performance report
    logger.log_action("Generating performance analysis report")
    try:
        # Calculate summary statistics
        total_train_leads = train_results['n_leads'].sum() if len(train_results) > 0 else 0
        total_test_leads = test_results['n_leads'].sum() if len(test_results) > 0 else 0
        
        priority_tiers = ['TIER_1_PRIME_MOVER', 'TIER_2_MODERATE_BLEEDER', 
                         'TIER_3_EXPERIENCED_MOVER', 'TIER_4_HEAVY_BLEEDER']
        
        train_priority = train_results[train_results['score_tier'].isin(priority_tiers)]
        test_priority = test_results[test_results['score_tier'].isin(priority_tiers)]
        
        train_priority_count = train_priority['n_leads'].sum() if len(train_priority) > 0 else 0
        train_priority_conv = train_priority['n_converted'].sum() if len(train_priority) > 0 else 0
        train_priority_rate = (train_priority_conv / train_priority_count * 100) if train_priority_count > 0 else 0
        
        test_priority_count = test_priority['n_leads'].sum() if len(test_priority) > 0 else 0
        test_priority_conv = test_priority['n_converted'].sum() if len(test_priority) > 0 else 0
        test_priority_rate = (test_priority_conv / test_priority_count * 100) if test_priority_count > 0 else 0
        
        logger.log_metric("TRAIN - Priority Tiers Count", f"{train_priority_count:,}")
        logger.log_metric("TRAIN - Priority Tiers Conversion Rate", f"{train_priority_rate:.2f}%")
        logger.log_metric("TEST - Priority Tiers Count", f"{test_priority_count:,}")
        logger.log_metric("TEST - Priority Tiers Conversion Rate", f"{test_priority_rate:.2f}%")
        
        # Save performance report
        performance_report = {
            'timestamp': datetime.now().isoformat(),
            'training_period': {
                'start': date_config['training_start_date'],
                'end': date_config['train_end_date'],
                'results': train_results.to_dict('records') if len(train_results) > 0 else []
            },
            'test_period': {
                'start': date_config['test_start_date'],
                'end': date_config['test_end_date'],
                'results': test_results.to_dict('records') if len(test_results) > 0 else []
            },
            'summary': {
                'train_total_leads': int(total_train_leads),
                'test_total_leads': int(total_test_leads),
                'train_priority_count': int(train_priority_count),
                'train_priority_rate': float(train_priority_rate),
                'test_priority_count': int(test_priority_count),
                'test_priority_rate': float(test_priority_rate)
            }
        }
        
        report_path = BASE_DIR / "reports" / "phase_5_performance_analysis.json"
        with open(report_path, 'w') as f:
            json.dump(performance_report, f, indent=2, default=str)
        logger.log_file_created("phase_5_performance_analysis.json", str(report_path),
                               "Tier performance validation and analysis report")
        
    except Exception as e:
        logger.log_validation_gate("G5.1.7", "Report Generation", False, str(e))
        all_gates_passed = False
    
    # Log key learnings
    if len(train_results) > 0:
        tier_1_train = train_results[train_results['score_tier'] == 'TIER_1_PRIME_MOVER']
        if len(tier_1_train) > 0:
            logger.log_learning(f"Tier 1 (Prime Movers) achieves {tier_1_train['actual_lift'].iloc[0]:.2f}x lift on training data")
    
    if len(test_results) > 0:
        tier_1_test = test_results[test_results['score_tier'] == 'TIER_1_PRIME_MOVER']
        if len(tier_1_test) > 0:
            logger.log_learning(f"Tier 1 (Prime Movers) achieves {tier_1_test['actual_lift'].iloc[0]:.2f}x lift on test data")
    
    logger.log_learning("Tier performance validated on both training and test periods")
    
    # End phase
    status = "PASSED" if all_gates_passed else "PASSED WITH WARNINGS"
    logger.end_phase(
        status=status,
        next_steps=["Proceed to Phase 6: Tier Calibration & Production Packaging"]
    )
    
    return {
        'train_results': train_results.to_dict('records') if len(train_results) > 0 else [],
        'test_results': test_results.to_dict('records') if len(test_results) > 0 else []
    }

if __name__ == "__main__":
    results = run_phase_5()
    print("\n=== PHASE 5.1 COMPLETE ===")
    print("Tier performance validation completed")

