"""
Phase 0.1: Data Landscape Assessment
Connects to BigQuery and catalogs available data for lead scoring
"""

import sys
from pathlib import Path
import pandas as pd
from google.cloud import bigquery
from datetime import datetime
import json

# Add Version-3 to path
BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-3")
sys.path.insert(0, str(BASE_DIR))

from utils.execution_logger import ExecutionLogger

def run_phase_0_1():
    """Execute Phase 0.1: Data Landscape Assessment"""
    logger = ExecutionLogger()
    logger.start_phase("0.1", "Data Landscape Assessment")
    
    client = bigquery.Client(project="savvy-gtm-analytics", location="northamerica-northeast2")
    assessment_results = {}
    all_gates_passed = True
    
    # 1. Assess FINTRX tables
    logger.log_action("Cataloging FINTRX_data_CA tables")
    try:
        query = """
        SELECT 
            table_name,
            table_type
        FROM `savvy-gtm-analytics.FinTrx_data_CA.INFORMATION_SCHEMA.TABLES`
        ORDER BY table_name
        """
        fintrx_df = client.query(query, location="northamerica-northeast2").to_dataframe()
        assessment_results['fintrx_tables'] = fintrx_df.to_dict('records')
        logger.log_metric("FINTRX Tables Count", len(fintrx_df))
        logger.log_file_created("fintrx_tables_summary.csv", 
                               str(BASE_DIR / "data" / "raw" / "fintrx_tables_summary.csv"),
                               "FINTRX table catalog")
        fintrx_df.to_csv(BASE_DIR / "data" / "raw" / "fintrx_tables_summary.csv", index=False)
        logger.log_validation_gate("G0.1.0", "FINTRX Table Catalog", True, 
                                  f"Found {len(fintrx_df)} tables")
    except Exception as e:
        logger.log_validation_gate("G0.1.0", "FINTRX Table Catalog", False, str(e))
        # Don't fail entire phase for this
    
    # 2. Assess lead funnel
    logger.log_action("Analyzing lead funnel stages and conversion rates")
    try:
        query = """
        WITH lead_stages AS (
            SELECT
                COUNT(*) as total_leads,
                COUNTIF(stage_entered_contacting__c IS NOT NULL) as contacted,
                COUNTIF(Stage_Entered_Call_Scheduled__c IS NOT NULL) as mql,
                COUNTIF(IsConverted = TRUE) as converted,
                MIN(CreatedDate) as earliest_lead,
                MAX(CreatedDate) as latest_lead
            FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
            WHERE FA_CRD__c IS NOT NULL
        )
        SELECT 
            *,
            ROUND(mql * 100.0 / NULLIF(contacted, 0), 2) as contacted_to_mql_rate,
            ROUND(converted * 100.0 / NULLIF(mql, 0), 2) as mql_to_sql_rate
        FROM lead_stages
        """
        result = client.query(query, location="northamerica-northeast2").to_dataframe()
        lead_funnel = result.to_dict('records')[0]
        assessment_results['lead_funnel'] = lead_funnel
        
        logger.log_metric("Total Leads", lead_funnel['total_leads'])
        logger.log_metric("Contacted Leads", lead_funnel['contacted'])
        logger.log_metric("MQLs", lead_funnel['mql'])
        logger.log_metric("Contacted-to-MQL Rate", f"{lead_funnel['contacted_to_mql_rate']}%")
        logger.log_metric("Earliest Lead", str(lead_funnel['earliest_lead']))
        logger.log_metric("Latest Lead", str(lead_funnel['latest_lead']))
        
        # Validation gate G0.1.2: Lead Volume
        if lead_funnel['contacted'] >= 5000:
            logger.log_validation_gate("G0.1.2", "Lead Volume", True, 
                                      f"{lead_funnel['contacted']:,} contacted leads (>=5,000 required)")
        else:
            logger.log_validation_gate("G0.1.2", "Lead Volume", False, 
                                      f"Only {lead_funnel['contacted']:,} contacted leads (need >=5,000)")
            all_gates_passed = False
        
        # Validation gate G0.1.5: MQL Rate
        mql_rate = lead_funnel['contacted_to_mql_rate'] if lead_funnel.get('contacted_to_mql_rate') else 0
        if 2 <= mql_rate <= 6:
            logger.log_validation_gate("G0.1.5", "MQL Rate", True, f"{mql_rate}% (expected 2-6%)")
        else:
            logger.log_validation_gate("G0.1.5", "MQL Rate", False, 
                                      f"{mql_rate}% (outside expected 2-6% range)")
    except Exception as e:
        logger.log_validation_gate("G0.1.2", "Lead Funnel Analysis", False, str(e))
        all_gates_passed = False
    
    # 3. Assess CRD match rate
    logger.log_action("Checking CRD match rate between Salesforce and FINTRX")
    try:
        query = """
        WITH lead_crds AS (
            SELECT DISTINCT
                SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
            FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
            WHERE FA_CRD__c IS NOT NULL
                AND stage_entered_contacting__c IS NOT NULL
        ),
        fintrx_crds AS (
            SELECT DISTINCT RIA_CONTACT_CRD_ID as crd
            FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
        )
        SELECT
            COUNT(DISTINCT l.crd) as total_lead_crds,
            COUNT(DISTINCT CASE WHEN f.crd IS NOT NULL THEN l.crd END) as matched_crds,
            ROUND(COUNT(DISTINCT CASE WHEN f.crd IS NOT NULL THEN l.crd END) * 100.0 / 
                  NULLIF(COUNT(DISTINCT l.crd), 0), 2) as match_rate_pct
        FROM lead_crds l
        LEFT JOIN fintrx_crds f ON l.crd = f.crd
        """
        result = client.query(query, location="northamerica-northeast2").to_dataframe()
        match_rate = result.to_dict('records')[0]
        assessment_results['crd_match_rate'] = match_rate
        
        logger.log_metric("Total Lead CRDs", match_rate['total_lead_crds'])
        logger.log_metric("Matched CRDs", match_rate['matched_crds'])
        logger.log_metric("CRD Match Rate", f"{match_rate['match_rate_pct']}%")
        
        # Validation gate G0.1.1: CRD Match Rate
        if match_rate['match_rate_pct'] >= 75:
            logger.log_validation_gate("G0.1.1", "CRD Match Rate", True, 
                                      f"{match_rate['match_rate_pct']}% (>=75% required)")
        else:
            logger.log_validation_gate("G0.1.1", "CRD Match Rate", False, 
                                      f"{match_rate['match_rate_pct']}% (need >=75%)")
            all_gates_passed = False
    except Exception as e:
        logger.log_validation_gate("G0.1.1", "CRD Match Rate", False, str(e))
        all_gates_passed = False
    
    # 4. Assess Firm_historicals coverage
    logger.log_action("Validating Firm_historicals monthly snapshots")
    try:
        query = """
        SELECT 
            YEAR,
            MONTH,
            COUNT(DISTINCT RIA_INVESTOR_CRD_ID) as unique_firms,
            COUNT(*) as total_rows,
            COUNTIF(TOTAL_AUM IS NOT NULL) as firms_with_aum,
            ROUND(COUNTIF(TOTAL_AUM IS NOT NULL) * 100.0 / COUNT(*), 2) as aum_coverage_pct
        FROM `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals`
        GROUP BY YEAR, MONTH
        ORDER BY YEAR, MONTH
        """
        firm_df = client.query(query, location="northamerica-northeast2").to_dataframe()
        assessment_results['firm_historicals_coverage'] = firm_df.to_dict('records')
        
        months_with_aum = len(firm_df[firm_df['aum_coverage_pct'] > 0])
        earliest_month = f"{firm_df['YEAR'].min()}-{firm_df['MONTH'].min():02d}"
        latest_month = f"{firm_df['YEAR'].max()}-{firm_df['MONTH'].max():02d}"
        
        logger.log_metric("Firm Historicals Months", len(firm_df))
        logger.log_metric("Months with AUM Data", months_with_aum)
        logger.log_metric("Date Range", f"{earliest_month} to {latest_month}")
        
        logger.log_file_created("firm_historicals_coverage.csv",
                               str(BASE_DIR / "data" / "raw" / "firm_historicals_coverage.csv"),
                               "Firm historicals monthly snapshot coverage")
        firm_df.to_csv(BASE_DIR / "data" / "raw" / "firm_historicals_coverage.csv", index=False)
        
        # Validation gate G0.1.3: Firm Historicals Coverage
        if months_with_aum >= 12:
            logger.log_validation_gate("G0.1.3", "Firm Historicals Coverage", True,
                                      f"{months_with_aum} months with AUM data (>=12 required)")
        else:
            logger.log_validation_gate("G0.1.3", "Firm Historicals Coverage", False,
                                      f"Only {months_with_aum} months with AUM data (need >=12)")
            all_gates_passed = False
    except Exception as e:
        logger.log_validation_gate("G0.1.3", "Firm Historicals Coverage", False, str(e))
        all_gates_passed = False
    
    # 5. Assess employment history coverage
    logger.log_action("Validating employment history coverage")
    try:
        query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT RIA_CONTACT_CRD_ID) as unique_reps,
            COUNT(DISTINCT PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as unique_firms,
            MIN(PREVIOUS_REGISTRATION_COMPANY_START_DATE) as earliest_start,
            MAX(COALESCE(PREVIOUS_REGISTRATION_COMPANY_END_DATE, CURRENT_DATE())) as latest_end,
            COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL) as current_employments,
            ROUND(COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL) * 100.0 / COUNT(*), 2) as current_employment_pct
        FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
        """
        result = client.query(query, location="northamerica-northeast2").to_dataframe()
        emp_coverage = result.to_dict('records')[0]
        assessment_results['employment_history_coverage'] = emp_coverage
        
        logger.log_metric("Employment History Records", emp_coverage['total_records'])
        logger.log_metric("Unique Reps", emp_coverage['unique_reps'])
        logger.log_metric("Unique Firms", emp_coverage['unique_firms'])
        logger.log_metric("Date Range", f"{emp_coverage['earliest_start']} to {emp_coverage['latest_end']}")
        
        # Check employment history coverage for leads
        query_lead_coverage = """
        WITH lead_crds AS (
            SELECT DISTINCT
                SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
            FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
            WHERE FA_CRD__c IS NOT NULL
                AND stage_entered_contacting__c IS NOT NULL
        ),
        emp_reps AS (
            SELECT DISTINCT RIA_CONTACT_CRD_ID as crd
            FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
        )
        SELECT
            COUNT(DISTINCT l.crd) as total_lead_crds,
            COUNT(DISTINCT CASE WHEN e.crd IS NOT NULL THEN l.crd END) as leads_with_emp_history,
            ROUND(COUNT(DISTINCT CASE WHEN e.crd IS NOT NULL THEN l.crd END) * 100.0 /
                  NULLIF(COUNT(DISTINCT l.crd), 0), 2) as emp_coverage_pct
        FROM lead_crds l
        LEFT JOIN emp_reps e ON l.crd = e.crd
        """
        lead_emp_result = client.query(query_lead_coverage, location="northamerica-northeast2").to_dataframe()
        lead_emp_coverage = lead_emp_result.to_dict('records')[0]
        
        logger.log_metric("Leads with Employment History", lead_emp_coverage['leads_with_emp_history'])
        logger.log_metric("Employment History Coverage %", f"{lead_emp_coverage['emp_coverage_pct']}%")
        
        # Validation gate G0.1.4: Employment History Coverage
        if lead_emp_coverage['emp_coverage_pct'] >= 80:
            logger.log_validation_gate("G0.1.4", "Employment History Coverage", True,
                                      f"{lead_emp_coverage['emp_coverage_pct']}% (>=80% required)")
        else:
            logger.log_validation_gate("G0.1.4", "Employment History Coverage", False,
                                      f"{lead_emp_coverage['emp_coverage_pct']}% (need >=80%)")
            all_gates_passed = False
    except Exception as e:
        logger.log_validation_gate("G0.1.4", "Employment History Coverage", False, str(e))
        all_gates_passed = False
    
    # Save full assessment report
    assessment_results['timestamp'] = datetime.now().isoformat()
    assessment_results['location'] = "northamerica-northeast2"
    
    report_path = BASE_DIR / "data" / "raw" / "data_landscape_report.json"
    with open(report_path, 'w') as f:
        json.dump(assessment_results, f, indent=2, default=str)
    logger.log_file_created("data_landscape_report.json", str(report_path), "Complete data landscape assessment")
    
    # Log key learnings
    if 'fintrx_tables' in assessment_results:
        logger.log_learning(f"FINTRX dataset contains {len(assessment_results['fintrx_tables'])} tables")
    if 'firm_historicals_coverage' in assessment_results:
        logger.log_learning(f"Firm_historicals covers {months_with_aum} months of data")
    if 'lead_funnel' in assessment_results:
        logger.log_learning(f"Lead funnel shows {lead_funnel['contacted_to_mql_rate']}% contacted-to-MQL conversion rate")
    
    # End phase
    status = "PASSED" if all_gates_passed else "PASSED WITH WARNINGS"
    logger.end_phase(
        status=status,
        next_steps=["Proceed to Phase 0.2: Target Variable Definition & Right-Censoring Analysis"]
    )
    
    return assessment_results

if __name__ == "__main__":
    results = run_phase_0_1()
    print("\n=== DATA LANDSCAPE ASSESSMENT COMPLETE ===")
    print(f"Report saved to: Version-3/data/raw/data_landscape_report.json")

