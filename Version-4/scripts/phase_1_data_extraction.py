"""
Phase 1: Data Extraction & Target Definition

This script:
1. Executes the target definition SQL
2. Validates the output
3. Creates the base dataset for feature engineering
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

# Import utilities and constants
from utils.execution_logger import ExecutionLogger
from config.constants import (
    BASE_DIR,
    PROJECT_ID,
    LOCATION,
    DATASET_ML,
    DATASET_FINTRX,
    DATASET_SALESFORCE,
    MATURITY_WINDOW_DAYS,
    BASELINE_CONVERSION_RATE,
    TRAINING_START_DATE,
    TRAINING_END_DATE,
    TEST_START_DATE,
    TEST_END_DATE
)

from google.cloud import bigquery


def run_phase_1() -> bool:
    """Execute Phase 1: Data Extraction & Target Definition."""
    
    logger = ExecutionLogger(BASE_DIR)
    logger.start_phase("1", "Data Extraction & Target Definition")
    
    # Track all gates
    all_blocking_gates_passed = True
    
    # Initialize BigQuery client
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    
    # =========================================================================
    # STEP 1.1: Execute Target Definition SQL
    # =========================================================================
    logger.log_action("Executing target definition SQL")
    
    sql_file = BASE_DIR / "sql" / "phase_1_target_definition.sql"
    
    if not sql_file.exists():
        logger.log_error(f"SQL file not found: {sql_file}")
        all_blocking_gates_passed = False
        status = logger.end_phase()
        return False
    
    # Read SQL file
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_query = f.read()
    
    logger.log_action(f"Read SQL file: {sql_file.name}")
    logger.log_action("Executing query against BigQuery...")
    
    try:
        # Execute query
        job = client.query(sql_query, location=LOCATION)
        job.result()  # Wait for job to complete
        
        logger.log_metric("BigQuery Job", "Completed successfully")
        logger.log_file_created(
            "v4_target_variable",
            f"BigQuery: {PROJECT_ID}.{DATASET_ML}.v4_target_variable"
        )
        
    except Exception as e:
        logger.log_error(f"Failed to execute SQL query: {str(e)}", exception=e)
        all_blocking_gates_passed = False
        status = logger.end_phase()
        return False
    
    # =========================================================================
    # STEP 1.2: Validate Target Distribution
    # =========================================================================
    logger.log_action("Validating target distribution")
    
    try:
        # Load target variable table
        query = f"""
        SELECT 
            COUNT(*) as total_leads,
            SUM(target) as conversions,
            AVG(target) as conversion_rate,
            COUNTIF(target IS NULL) as right_censored,
            COUNT(DISTINCT advisor_crd) as unique_advisors
        FROM `{PROJECT_ID}.{DATASET_ML}.v4_target_variable`
        """
        
        result = list(client.query(query).result())[0]
        
        total_leads = result.total_leads
        conversions = result.conversions
        conversion_rate = result.conversion_rate
        right_censored = result.right_censored
        unique_advisors = result.unique_advisors
        
        logger.log_metric("Total Leads", f"{total_leads:,}")
        logger.log_metric("Conversions", f"{conversions:,}")
        logger.log_metric("Conversion Rate", f"{conversion_rate*100:.2f}%")
        logger.log_metric("Unique Advisors", f"{unique_advisors:,}")
        
        # Gate G1.1: >= 10,000 mature leads (BLOCKING)
        gate_1_1 = total_leads >= 10000
        logger.log_gate(
            "G1.1", "Minimum Sample Size",
            passed=gate_1_1,
            expected=">= 10,000 mature leads",
            actual=f"{total_leads:,} leads"
        )
        
        if not gate_1_1:
            all_blocking_gates_passed = False
        
        # Gate G1.2: Conversion rate between 2% - 8% (WARNING)
        gate_1_2 = 0.02 <= conversion_rate <= 0.08
        logger.log_gate(
            "G1.2", "Conversion Rate Range",
            passed=gate_1_2,
            expected="2% - 8%",
            actual=f"{conversion_rate*100:.2f}%"
        )
        
        if not gate_1_2:
            logger.log_warning(
                f"Conversion rate ({conversion_rate*100:.2f}%) outside expected range (2%-8%)",
                action_taken="Continue but monitor"
            )
        
        # Gate G1.3: Right-censoring rate <= 40% (WARNING)
        # Note: Right-censored leads are already excluded in the SQL WHERE clause
        # So this should be 0, but we check anyway
        right_censoring_rate = right_censored / total_leads if total_leads > 0 else 0
        gate_1_3 = right_censoring_rate <= 0.40
        logger.log_gate(
            "G1.3", "Right-Censoring Rate",
            passed=gate_1_3,
            expected="<= 40%",
            actual=f"{right_censoring_rate*100:.2f}% ({right_censored:,} leads)"
        )
        
        if not gate_1_3:
            logger.log_warning(
                f"Right-censoring rate ({right_censoring_rate*100:.2f}%) higher than expected",
                action_taken="Continue but note for analysis"
            )
        
    except Exception as e:
        logger.log_error(f"Failed to validate target distribution: {str(e)}", exception=e)
        all_blocking_gates_passed = False
    
    # =========================================================================
    # STEP 1.3: Check FINTRX Coverage
    # =========================================================================
    logger.log_action("Checking FINTRX coverage")
    
    try:
        # Check how many leads have FINTRX matches
        query = f"""
        SELECT 
            COUNT(*) as total_leads,
            COUNTIF(advisor_crd IS NOT NULL) as with_crd,
            COUNTIF(advisor_crd IS NULL) as without_crd
        FROM `{PROJECT_ID}.{DATASET_ML}.v4_target_variable`
        """
        
        result = list(client.query(query).result())[0]
        
        total = result.total_leads
        with_crd = result.with_crd
        fintrx_match_rate = with_crd / total if total > 0 else 0
        
        logger.log_metric("Leads with CRD", f"{with_crd:,}")
        logger.log_metric("FINTRX Match Rate", f"{fintrx_match_rate*100:.2f}%")
        
        # Gate G1.4: FINTRX match rate >= 75% (WARNING)
        gate_1_4 = fintrx_match_rate >= 0.75
        logger.log_gate(
            "G1.4", "FINTRX Match Rate",
            passed=gate_1_4,
            expected=">= 75%",
            actual=f"{fintrx_match_rate*100:.2f}%"
        )
        
        if not gate_1_4:
            logger.log_warning(
                f"FINTRX match rate ({fintrx_match_rate*100:.2f}%) below expected threshold",
                action_taken="Continue but note limited feature availability"
            )
        
    except Exception as e:
        logger.log_error(f"Failed to check FINTRX coverage: {str(e)}", exception=e)
    
    # =========================================================================
    # STEP 1.4: Check Employment History Coverage
    # =========================================================================
    logger.log_action("Checking employment history coverage")
    
    try:
        # Check how many leads have employment history in FINTRX
        query = f"""
        SELECT 
            COUNT(DISTINCT tv.lead_id) as total_leads,
            COUNT(DISTINCT eh.RIA_CONTACT_CRD_ID) as with_employment_history
        FROM `{PROJECT_ID}.{DATASET_ML}.v4_target_variable` tv
        LEFT JOIN `{PROJECT_ID}.{DATASET_FINTRX}.contact_registered_employment_history` eh
            ON tv.advisor_crd = eh.RIA_CONTACT_CRD_ID
        WHERE tv.advisor_crd IS NOT NULL
        """
        
        result = list(client.query(query).result())[0]
        
        total = result.total_leads
        with_history = result.with_employment_history
        employment_coverage = with_history / total if total > 0 else 0
        
        logger.log_metric("Leads with Employment History", f"{with_history:,}")
        logger.log_metric("Employment History Coverage", f"{employment_coverage*100:.2f}%")
        
        # Gate G1.5: Employment history coverage >= 70% (WARNING)
        gate_1_5 = employment_coverage >= 0.70
        logger.log_gate(
            "G1.5", "Employment History Coverage",
            passed=gate_1_5,
            expected=">= 70%",
            actual=f"{employment_coverage*100:.2f}%"
        )
        
        if not gate_1_5:
            logger.log_warning(
                f"Employment history coverage ({employment_coverage*100:.2f}%) below expected threshold",
                action_taken="Continue but note limited tenure/mobility features"
            )
        
    except Exception as e:
        logger.log_error(f"Failed to check employment history: {str(e)}", exception=e)
    
    # =========================================================================
    # STEP 1.5: Analyze Lead Source Distribution
    # =========================================================================
    logger.log_action("Analyzing lead source distribution")
    
    try:
        # Overall distribution
        query = f"""
        SELECT 
            lead_source_grouped,
            COUNT(*) as count,
            SUM(target) as conversions,
            AVG(target) as conversion_rate
        FROM `{PROJECT_ID}.{DATASET_ML}.v4_target_variable`
        GROUP BY lead_source_grouped
        ORDER BY count DESC
        """
        
        source_df = client.query(query).to_dataframe()
        
        logger.log_action("Lead Source Distribution (Overall)")
        for _, row in source_df.iterrows():
            logger.log_metric(
                f"{row['lead_source_grouped']}",
                f"{row['count']:,} leads ({row['count']/source_df['count'].sum()*100:.1f}%), "
                f"{row['conversion_rate']*100:.2f}% conversion"
            )
        
        # Distribution over time (by quarter)
        query = f"""
        SELECT 
            DATE_TRUNC(DATE(contacted_date), QUARTER) as quarter,
            lead_source_grouped,
            COUNT(*) as count
        FROM `{PROJECT_ID}.{DATASET_ML}.v4_target_variable`
        GROUP BY quarter, lead_source_grouped
        ORDER BY quarter, count DESC
        """
        
        quarterly_df = client.query(query).to_dataframe()
        
        # Calculate drift for LinkedIn and Provided Lists
        if len(quarterly_df) > 0:
            quarterly_df['quarter_str'] = quarterly_df['quarter'].astype(str)
            
            # Get first and last quarter
            first_quarter = quarterly_df['quarter'].min()
            last_quarter = quarterly_df['quarter'].max()
            
            first_q_data = quarterly_df[quarterly_df['quarter'] == first_quarter]
            last_q_data = quarterly_df[quarterly_df['quarter'] == last_quarter]
            
            logger.log_action("Lead Source Distribution Over Time")
            
            for source in ['LinkedIn', 'Provided List']:
                first_count = first_q_data[first_q_data['lead_source_grouped'] == source]['count'].sum()
                last_count = last_q_data[last_q_data['lead_source_grouped'] == source]['count'].sum()
                
                first_total = first_q_data['count'].sum()
                last_total = last_q_data['count'].sum()
                
                if first_total > 0 and last_total > 0:
                    first_pct = first_count / first_total * 100
                    last_pct = last_count / last_total * 100
                    drift = last_pct - first_pct
                    
                    logger.log_metric(
                        f"{source} Drift",
                        f"Q1: {first_pct:.1f}% -> Q4: {last_pct:.1f}% (Delta {drift:+.1f}%)"
                    )
                    
                    if abs(drift) > 20:
                        logger.log_warning(
                            f"Significant drift detected for {source}: {drift:+.1f}%",
                            action_taken="Will use stratified sampling in train/test split"
                        )
        
        # Save lead source distribution CSV
        csv_path = BASE_DIR / "data" / "exploration" / "lead_source_distribution.csv"
        source_df.to_csv(csv_path, index=False)
        logger.log_file_created("lead_source_distribution.csv", str(csv_path))
        
    except Exception as e:
        logger.log_error(f"Failed to analyze lead source distribution: {str(e)}", exception=e)
    
    # =========================================================================
    # STEP 1.6: Save Exploration Data
    # =========================================================================
    logger.log_action("Saving exploration data")
    
    try:
        # Compile summary statistics
        summary_stats = {
            "phase": "1",
            "timestamp": datetime.now().isoformat(),
            "target_variable_table": f"{PROJECT_ID}.{DATASET_ML}.v4_target_variable",
            "statistics": {
                "total_leads": int(total_leads),
                "conversions": int(conversions),
                "conversion_rate": float(conversion_rate),
                "right_censored": int(right_censored),
                "unique_advisors": int(unique_advisors),
                "fintrx_match_rate": float(fintrx_match_rate),
                "employment_history_coverage": float(employment_coverage)
            },
            "gates": {
                "G1.1_minimum_sample_size": {
                    "passed": gate_1_1,
                    "expected": ">= 10,000",
                    "actual": int(total_leads)
                },
                "G1.2_conversion_rate_range": {
                    "passed": gate_1_2,
                    "expected": "2% - 8%",
                    "actual": f"{conversion_rate*100:.2f}%"
                },
                "G1.3_right_censoring_rate": {
                    "passed": gate_1_3,
                    "expected": "<= 40%",
                    "actual": f"{right_censoring_rate*100:.2f}%"
                },
                "G1.4_fintrx_match_rate": {
                    "passed": gate_1_4,
                    "expected": ">= 75%",
                    "actual": f"{fintrx_match_rate*100:.2f}%"
                },
                "G1.5_employment_history_coverage": {
                    "passed": gate_1_5,
                    "expected": ">= 70%",
                    "actual": f"{employment_coverage*100:.2f}%"
                }
            },
            "lead_source_distribution": source_df.to_dict('records') if 'source_df' in locals() else []
        }
        
        # Save to JSON
        json_path = BASE_DIR / "data" / "raw" / "target_variable_analysis.json"
        with open(json_path, 'w') as f:
            json.dump(summary_stats, f, indent=2, default=str)
        
        logger.log_file_created("target_variable_analysis.json", str(json_path))
        
    except Exception as e:
        logger.log_error(f"Failed to save exploration data: {str(e)}", exception=e)
    
    # =========================================================================
    # PHASE SUMMARY
    # =========================================================================
    status = logger.end_phase(next_steps=["Phase 2: Point-in-Time Feature Engineering"])
    
    return all_blocking_gates_passed and status in ["PASSED", "PASSED WITH WARNINGS"]


if __name__ == "__main__":
    success = run_phase_1()
    sys.exit(0 if success else 1)

