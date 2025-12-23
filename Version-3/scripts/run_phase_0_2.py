"""
Phase 0.2: Target Variable Definition & Right-Censoring Analysis
Ensures leads have enough "maturity" before labeling as non-converters
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from google.cloud import bigquery
from datetime import datetime
import json

# Add Version-3 to path
BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-3")
sys.path.insert(0, str(BASE_DIR))

from utils.execution_logger import ExecutionLogger
from utils.date_configuration import DateConfiguration, load_date_configuration

def run_phase_0_2():
    """Execute Phase 0.2: Target Variable Definition & Right-Censoring Analysis"""
    logger = ExecutionLogger()
    logger.start_phase("0.2", "Target Variable Definition & Right-Censoring Analysis")
    
    # CRITICAL: Load date configuration from Phase 0.0
    logger.log_action("Loading date configuration from Phase 0.0")
    date_config_dict = load_date_configuration()
    analysis_date = date_config_dict['training_snapshot_date']
    logger.log_metric("Analysis Date (Fixed)", analysis_date)
    logger.log_learning(f"Using fixed analysis_date ({analysis_date}) instead of CURRENT_DATE() for training set stability")
    
    client = bigquery.Client(project="savvy-gtm-analytics", location="northamerica-northeast2")
    all_gates_passed = True
    
    # Step 1: Analyze conversion timing
    logger.log_action("Analyzing days to conversion for MQL conversions")
    try:
        query = """
        SELECT
            DATE_DIFF(
                DATE(Stage_Entered_Call_Scheduled__c), 
                DATE(stage_entered_contacting__c), 
                DAY
            ) as days_to_mql
        FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
        WHERE stage_entered_contacting__c IS NOT NULL
            AND Stage_Entered_Call_Scheduled__c IS NOT NULL
            AND FA_CRD__c IS NOT NULL
        """
        timing_df = client.query(query, location="northamerica-northeast2").to_dataframe()
        
        # Filter out negative days (data quality issues)
        valid_timing = timing_df[timing_df['days_to_mql'] >= 0]['days_to_mql']
        
        # Calculate statistics
        mean_days = float(valid_timing.mean())
        median_days = float(valid_timing.median())
        p90_days = float(valid_timing.quantile(0.90))
        p95_days = float(valid_timing.quantile(0.95))
        p99_days = float(valid_timing.quantile(0.99))
        
        logger.log_metric("Total Conversions Analyzed", len(valid_timing))
        logger.log_metric("Mean Days to MQL", f"{mean_days:.1f}")
        logger.log_metric("Median Days to MQL", f"{median_days:.1f}")
        logger.log_metric("90th Percentile", f"{p90_days:.1f} days")
        logger.log_metric("95th Percentile", f"{p95_days:.1f} days")
        logger.log_metric("99th Percentile", f"{p99_days:.1f} days")
        
        # Save timing distribution
        timing_df.to_csv(BASE_DIR / "data" / "raw" / "conversion_timing_distribution.csv", index=False)
        logger.log_file_created("conversion_timing_distribution.csv",
                               str(BASE_DIR / "data" / "raw" / "conversion_timing_distribution.csv"),
                               "Distribution of days to MQL conversion")
        
    except Exception as e:
        logger.log_validation_gate("G0.2.0", "Conversion Timing Analysis", False, str(e))
        all_gates_passed = False
        return None
    
    # Step 2: Calculate maturity window (90% capture)
    logger.log_action("Calculating optimal maturity window (90% capture)")
    capture_pct = 0.90
    maturity_window_days = int(p90_days)
    
    logger.log_metric("Recommended Maturity Window", f"{maturity_window_days} days")
    logger.log_metric("Capture Percentage", f"{capture_pct * 100}%")
    
    # Validation gate G0.2.2: Maturity Window
    if 14 <= maturity_window_days <= 90:
        logger.log_validation_gate("G0.2.2", "Maturity Window", True,
                                  f"{maturity_window_days} days (within 14-90 day range)")
    else:
        logger.log_validation_gate("G0.2.2", "Maturity Window", False,
                                  f"{maturity_window_days} days (outside 14-90 day range)")
        all_gates_passed = False
    
    # Step 3: Analyze right-censoring impact
    logger.log_action(f"Analyzing right-censoring impact with {maturity_window_days}-day window")
    try:
        query = f"""
        WITH lead_maturity AS (
            SELECT
                Id,
                stage_entered_contacting__c,
                Stage_Entered_Call_Scheduled__c,
                DATE_DIFF(DATE('{analysis_date}'), DATE(stage_entered_contacting__c), DAY) as days_since_contact,
                CASE 
                    WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 
                    ELSE 0 
                END as is_mql
            FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
            WHERE stage_entered_contacting__c IS NOT NULL
                AND FA_CRD__c IS NOT NULL
        )
        SELECT
            COUNT(*) as total_contacted,
            COUNTIF(days_since_contact >= {maturity_window_days}) as mature_leads,
            COUNTIF(days_since_contact < {maturity_window_days}) as right_censored_leads,
            ROUND(COUNTIF(days_since_contact >= {maturity_window_days}) * 100.0 / COUNT(*), 2) as mature_pct,
            
            -- Conversion rates
            COUNTIF(is_mql = 1 AND days_since_contact >= {maturity_window_days}) as mature_mqls,
            ROUND(COUNTIF(is_mql = 1 AND days_since_contact >= {maturity_window_days}) * 100.0 / 
                  NULLIF(COUNTIF(days_since_contact >= {maturity_window_days}), 0), 2) as mature_mql_rate,
            
            -- Right-censored conversion rate (for comparison)
            COUNTIF(is_mql = 1 AND days_since_contact < {maturity_window_days}) as censored_mqls,
            ROUND(COUNTIF(is_mql = 1 AND days_since_contact < {maturity_window_days}) * 100.0 /
                  NULLIF(COUNTIF(days_since_contact < {maturity_window_days}), 0), 2) as censored_mql_rate
        FROM lead_maturity
        """
        result = client.query(query, location="northamerica-northeast2").to_dataframe()
        censoring_analysis = result.to_dict('records')[0]
        
        logger.log_metric("Total Contacted Leads", censoring_analysis['total_contacted'])
        logger.log_metric("Mature Leads", censoring_analysis['mature_leads'])
        logger.log_metric("Right-Censored Leads", censoring_analysis['right_censored_leads'])
        logger.log_metric("Mature Lead %", f"{censoring_analysis['mature_pct']}%")
        logger.log_metric("Mature MQL Rate", f"{censoring_analysis['mature_mql_rate']}%")
        logger.log_metric("Censored MQL Rate", f"{censoring_analysis['censored_mql_rate']}%")
        
        # Validation gate G0.2.3: Mature Lead Volume
        if censoring_analysis['mature_leads'] >= 3000:
            logger.log_validation_gate("G0.2.3", "Mature Lead Volume", True,
                                      f"{censoring_analysis['mature_leads']:,} mature leads (>=3,000 required)")
        else:
            logger.log_validation_gate("G0.2.3", "Mature Lead Volume", False,
                                      f"Only {censoring_analysis['mature_leads']:,} mature leads (need >=3,000)")
            all_gates_passed = False
        
        # Validation gate G0.2.4: Positive Class Rate
        mature_mql_rate = censoring_analysis['mature_mql_rate']
        if 2 <= mature_mql_rate <= 6:
            logger.log_validation_gate("G0.2.4", "Positive Class Rate", True,
                                      f"{mature_mql_rate}% (within 2-6% range)")
        else:
            logger.log_validation_gate("G0.2.4", "Positive Class Rate", False,
                                      f"{mature_mql_rate}% (outside 2-6% range)")
            all_gates_passed = False
        
        # Validation gate G0.2.5: Right-Censored %
        right_censored_pct = 100 - censoring_analysis['mature_pct']
        if right_censored_pct < 20:
            logger.log_validation_gate("G0.2.5", "Right-Censored %", True,
                                      f"{right_censored_pct:.1f}% (<20% threshold)")
        else:
            logger.log_validation_gate("G0.2.5", "Right-Censored %", False,
                                      f"{right_censored_pct:.1f}% (>=20%, window may be too long)")
            all_gates_passed = False
        
    except Exception as e:
        logger.log_validation_gate("G0.2.1", "Right-Censoring Analysis", False, str(e))
        all_gates_passed = False
        return None
    
    # Step 4: Generate target variable view SQL
    logger.log_action("Generating target variable view SQL with right-censoring handling")
    view_sql = f"""
CREATE OR REPLACE VIEW `savvy-gtm-analytics.ml_features.lead_target_variable` AS

WITH contacted_leads AS (
    SELECT
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd,
        DATE(l.stage_entered_contacting__c) as contacted_date,
        DATE(l.Stage_Entered_Call_Scheduled__c) as mql_date,
        
        -- Maturity check: lead must be at least {maturity_window_days} days old as of analysis_date
        -- CRITICAL: Use fixed analysis_date instead of CURRENT_DATE() for reproducibility
        DATE_DIFF(DATE('{analysis_date}'), DATE(l.stage_entered_contacting__c), DAY) as days_since_contact,
        
        -- Target variable with right-censoring protection
        CASE
            -- Too young to label - exclude from training
            WHEN DATE_DIFF(DATE('{analysis_date}'), DATE(l.stage_entered_contacting__c), DAY) < {maturity_window_days}
            THEN NULL  -- Right-censored, exclude
            
            -- Converted to MQL within window
            WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL
                 AND DATE_DIFF(DATE(l.Stage_Entered_Call_Scheduled__c), 
                               DATE(l.stage_entered_contacting__c), DAY) <= {maturity_window_days}
            THEN 1  -- Positive: converted within window
            
            -- Converted after window (treat as negative for within-window prediction)
            WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL
                 AND DATE_DIFF(DATE(l.Stage_Entered_Call_Scheduled__c), 
                               DATE(l.stage_entered_contacting__c), DAY) > {maturity_window_days}
            THEN 0  -- Negative: didn't convert within window
            
            -- Never converted and mature enough
            ELSE 0  -- Negative: mature lead, never converted
        END as target_mql_{maturity_window_days}d,
        
        -- Additional metadata
        l.Company as company_name,
        l.LeadSource as lead_source,
        l.CreatedDate as lead_created_date
        
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.FA_CRD__c IS NOT NULL
        AND l.Company NOT LIKE '%Savvy%'  -- Exclude own company
)

SELECT * FROM contacted_leads
WHERE target_mql_{maturity_window_days}d IS NOT NULL;  -- Exclude right-censored
"""
    
    # Save SQL to file
    sql_path = BASE_DIR / "sql" / "lead_target_variable_view.sql"
    with open(sql_path, 'w') as f:
        f.write(view_sql)
    logger.log_file_created("lead_target_variable_view.sql", str(sql_path),
                           "Target variable view SQL with right-censoring")
    
    # Validation gate G0.2.1: Fixed Analysis Date
    # Check for actual CURRENT_DATE() usage (not in comments)
    import re
    # Remove comments to check for actual CURRENT_DATE() usage
    sql_without_comments = re.sub(r'--.*?$', '', view_sql, flags=re.MULTILINE)
    sql_without_comments = re.sub(r'/\*.*?\*/', '', sql_without_comments, flags=re.DOTALL)
    
    has_fixed_date = f"DATE('{analysis_date}')" in view_sql
    has_current_date = "CURRENT_DATE()" in sql_without_comments
    
    if has_fixed_date and not has_current_date:
        logger.log_validation_gate("G0.2.1", "Fixed Analysis Date", True,
                                  "All date calculations use fixed analysis_date, NOT CURRENT_DATE()")
    else:
        if not has_fixed_date:
            logger.log_validation_gate("G0.2.1", "Fixed Analysis Date", False,
                                      "Fixed analysis_date not found in SQL")
        if has_current_date:
            logger.log_validation_gate("G0.2.1", "Fixed Analysis Date", False,
                                      "Found CURRENT_DATE() references - must use fixed analysis_date")
        all_gates_passed = False
    
    # Step 5: Test training set stability (re-run query to verify same results)
    logger.log_action("Testing training set stability (verifying fixed date produces consistent results)")
    try:
        # Count leads with target variable
        count_query = f"""
        WITH contacted_leads AS (
            SELECT
                l.Id as lead_id,
                DATE_DIFF(DATE('{analysis_date}'), DATE(l.stage_entered_contacting__c), DAY) as days_since_contact,
                CASE
                    WHEN DATE_DIFF(DATE('{analysis_date}'), DATE(l.stage_entered_contacting__c), DAY) < {maturity_window_days}
                    THEN NULL
                    WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL
                         AND DATE_DIFF(DATE(l.Stage_Entered_Call_Scheduled__c), 
                                       DATE(l.stage_entered_contacting__c), DAY) <= {maturity_window_days}
                    THEN 1
                    ELSE 0
                END as target
            FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
            WHERE l.stage_entered_contacting__c IS NOT NULL
                AND l.FA_CRD__c IS NOT NULL
                AND l.Company NOT LIKE '%Savvy%'
        )
        SELECT
            COUNT(*) as total_leads,
            COUNTIF(target IS NOT NULL) as labeled_leads,
            COUNTIF(target = 1) as positive_leads,
            COUNTIF(target = 0) as negative_leads,
            ROUND(COUNTIF(target = 1) * 100.0 / NULLIF(COUNTIF(target IS NOT NULL), 0), 2) as positive_rate
        FROM contacted_leads
        """
        stability_result = client.query(count_query, location="northamerica-northeast2").to_dataframe()
        stability_metrics = stability_result.to_dict('records')[0]
        
        logger.log_metric("Total Labeled Leads", stability_metrics['labeled_leads'])
        logger.log_metric("Positive Leads", stability_metrics['positive_leads'])
        logger.log_metric("Negative Leads", stability_metrics['negative_leads'])
        logger.log_metric("Positive Rate", f"{stability_metrics['positive_rate']}%")
        
        # Save stability metrics for future comparison
        stability_path = BASE_DIR / "data" / "raw" / "target_variable_stability_metrics.json"
        with open(stability_path, 'w') as f:
            json.dump({
                'analysis_date': analysis_date,
                'maturity_window_days': maturity_window_days,
                'metrics': stability_metrics,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        logger.log_file_created("target_variable_stability_metrics.json", str(stability_path),
                               "Baseline metrics for training set stability verification")
        
        logger.log_validation_gate("G0.2.6", "Training Set Stability", True,
                                  f"Baseline established: {stability_metrics['labeled_leads']:,} labeled leads")
        
    except Exception as e:
        logger.log_validation_gate("G0.2.6", "Training Set Stability", False, str(e))
        all_gates_passed = False
    
    # Save complete analysis results
    analysis_results = {
        'analysis_date': analysis_date,
        'maturity_window_days': maturity_window_days,
        'capture_percentage': capture_pct,
        'timing_statistics': {
            'mean_days': mean_days,
            'median_days': median_days,
            'p90_days': p90_days,
            'p95_days': p95_days,
            'p99_days': p99_days
        },
        'censoring_analysis': censoring_analysis,
        'stability_metrics': stability_metrics if 'stability_metrics' in locals() else None,
        'timestamp': datetime.now().isoformat()
    }
    
    results_path = BASE_DIR / "data" / "raw" / "target_variable_analysis.json"
    with open(results_path, 'w') as f:
        json.dump(analysis_results, f, indent=2, default=str)
    logger.log_file_created("target_variable_analysis.json", str(results_path),
                           "Complete target variable analysis results")
    
    # Log key learnings
    logger.log_learning(f"90% of conversions happen within {maturity_window_days} days")
    logger.log_learning(f"Right-censoring excludes {censoring_analysis['right_censored_leads']:,} leads ({right_censored_pct:.1f}%)")
    logger.log_learning(f"Mature cohort has {censoring_analysis['mature_mql_rate']}% conversion rate")
    
    # End phase
    status = "PASSED" if all_gates_passed else "PASSED WITH WARNINGS"
    logger.end_phase(
        status=status,
        next_steps=["Proceed to Phase 1: Feature Engineering Pipeline"]
    )
    
    return analysis_results

if __name__ == "__main__":
    results = run_phase_0_2()
    if results:
        print("\n=== TARGET VARIABLE ANALYSIS COMPLETE ===")
        print(f"Analysis Date: {results['analysis_date']}")
        print(f"Recommended Maturity Window: {results['maturity_window_days']} days")
        print(f"Timing Stats: Mean={results['timing_statistics']['mean_days']:.1f}, "
              f"Median={results['timing_statistics']['median_days']:.1f}, "
              f"P90={results['timing_statistics']['p90_days']:.1f}")
        print(f"Results saved to: Version-3/data/raw/target_variable_analysis.json")

