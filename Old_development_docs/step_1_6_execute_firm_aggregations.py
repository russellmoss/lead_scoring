"""
Step 1.6: Create Firm Snapshot Tables from Rep Snapshots
Execute all 8 firm aggregations from rep-level snapshots
"""

from google.cloud import bigquery
import sys

# Date mappings: (DATE_STR, SNAPSHOT_DATE)
DATE_MAPPINGS = [
    ('20240107', "DATE('2024-01-07')"),
    ('20240331', "DATE('2024-03-31')"),
    ('20240707', "DATE('2024-07-07')"),
    ('20241006', "DATE('2024-10-06')"),
    ('20250105', "DATE('2025-01-05')"),
    ('20250406', "DATE('2025-04-06')"),
    ('20250706', "DATE('2025-07-06')"),
    ('20251005', "DATE('2025-10-05')"),
]

SQL_TEMPLATE = """
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.snapshot_firms_{DATE_STR}` AS
WITH firm_base_data AS (
  SELECT 
    RIAFirmCRD,
    RIAFirmName,
    
    -- Basic firm metrics (aggregated from reps)
    COUNT(DISTINCT RepCRD) as total_reps,
    COUNT(*) as total_records,
    
    -- Financial metrics (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as total_firm_aum_millions,
    CAST(NULL AS FLOAT64) as avg_rep_aum_millions,
    CAST(NULL AS FLOAT64) as max_rep_aum_millions,
    CAST(NULL AS FLOAT64) as min_rep_aum_millions,
    
    -- Growth metrics (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as avg_firm_growth_1y,
    CAST(NULL AS FLOAT64) as avg_firm_growth_5y,
    
    -- Client metrics (NOT AVAILABLE - set to NULL)
    CAST(NULL AS INT64) as total_firm_clients,
    CAST(NULL AS INT64) as total_firm_hnw_clients,
    CAST(NULL AS FLOAT64) as avg_clients_per_rep,
    
    -- Professional metrics (percentages)
    AVG(Has_Series_7) as pct_reps_with_series_7,
    AVG(Has_CFP) as pct_reps_with_cfp,
    AVG(Has_Disclosure) as pct_reps_with_disclosure,
    AVG(Has_Series_65) as pct_reps_with_series_65,
    AVG(Has_Series_66) as pct_reps_with_series_66,
    AVG(Has_Series_24) as pct_reps_with_series_24,
    
    -- Firm characteristics (most common values)
    APPROX_TOP_COUNT(Home_State, 1)[OFFSET(0)].value as primary_state,
    APPROX_TOP_COUNT(Home_MetropolitanArea, 1)[OFFSET(0)].value as primary_metro_area,
    APPROX_TOP_COUNT(Branch_State, 1)[OFFSET(0)].value as primary_branch_state,
    
    -- Geographic diversity metrics
    COUNT(DISTINCT Home_State) as states_represented,
    COUNT(DISTINCT Home_MetropolitanArea) as metro_areas_represented,
    COUNT(DISTINCT Branch_State) as branch_states,
    
    -- Tenure metrics (aggregated)
    AVG(DateBecameRep_NumberOfYears) as avg_rep_experience_years,
    AVG(DateOfHireAtCurrentFirm_NumberOfYears) as avg_tenure_at_firm_years,
    AVG(AverageTenureAtPriorFirms) as avg_tenure_at_prior_firms,
    AVG(NumberOfPriorFirms) as avg_prior_firms_per_rep,
    
    -- Custodian relationships (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as total_schwab_aum,
    CAST(NULL AS FLOAT64) as total_fidelity_aum,
    CAST(NULL AS FLOAT64) as total_pershing_aum,
    CAST(NULL AS FLOAT64) as total_tdameritrade_aum,
    
    -- Investment focus (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as total_mutual_fund_aum,
    CAST(NULL AS FLOAT64) as total_private_fund_aum,
    CAST(NULL AS FLOAT64) as total_etf_aum,
    
    -- Snapshot date (all reps in same snapshot have same snapshot_at)
    MAX(snapshot_at) as snapshot_at
    
  FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_{DATE_STR}`
  WHERE RIAFirmCRD IS NOT NULL AND RIAFirmCRD != ''
  GROUP BY RIAFirmCRD, RIAFirmName
),
firm_engineered_features AS (
  SELECT 
    *,
    
    -- Firm size classification (NOT AVAILABLE - set to NULL)
    CAST(NULL AS STRING) as firm_size_tier,
    
    -- Rep efficiency metrics (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as aum_per_rep,
    
    -- Geographic diversity scores
    CASE WHEN states_represented > 5 THEN 1 ELSE 0 END as multi_state_firm,
    CASE WHEN states_represented > 10 THEN 1 ELSE 0 END as national_firm
    
  FROM firm_base_data
)
SELECT * FROM firm_engineered_features;
"""

def execute_aggregation(client, date_str, snapshot_date):
    """Execute firm aggregation for a single date"""
    sql = SQL_TEMPLATE.format(DATE_STR=date_str, SNAPSHOT_DATE=snapshot_date)
    print(f"\n{'='*70}")
    print(f"Executing firm aggregation for {date_str} (snapshot_at = {snapshot_date})")
    print(f"{'='*70}")
    
    try:
        query_job = client.query(sql)
        query_job.result()  # Wait for completion
        print(f"[SUCCESS] Successfully created: snapshot_firms_{date_str}")
        return True
    except Exception as e:
        print(f"[ERROR] Error creating snapshot_firms_{date_str}: {str(e)}")
        return False

def main():
    client = bigquery.Client(project='savvy-gtm-analytics')
    
    print("="*70)
    print("Step 1.6: Create Firm Snapshot Tables from Rep Snapshots")
    print("="*70)
    print(f"\nExecuting {len(DATE_MAPPINGS)} firm aggregations...")
    
    results = []
    for date_str, snapshot_date in DATE_MAPPINGS:
        success = execute_aggregation(client, date_str, snapshot_date)
        results.append((date_str, success))
    
    # Summary
    print("\n" + "="*70)
    print("FIRM AGGREGATION SUMMARY")
    print("="*70)
    successful = sum(1 for _, success in results if success)
    failed = len(results) - successful
    
    for date_str, success in results:
        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"  {date_str}: {status}")
    
    print(f"\nTotal: {successful} successful, {failed} failed")
    
    if failed > 0:
        print("\n[ERROR] Some aggregations failed. Please review errors above.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All firm aggregations completed successfully!")
        print("\nNext: Proceed to Step 1.7 (Validate Snapshot Schemas Against Data Contracts)")

if __name__ == "__main__":
    main()

