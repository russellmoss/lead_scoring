"""
Phase 7.1: Execute BigQuery Infrastructure Setup
Creates production tables for feature storage and scoring results
"""

from google.cloud import bigquery
from pathlib import Path
import time

PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

# SQL for creating feature table
# Note: We need to calculate aum_growth_since_jan2024_pct from the PIT table data
CREATE_FEATURES_TABLE = f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.ml_features.lead_scoring_features`
PARTITION BY contacted_date
CLUSTER BY advisor_crd
AS
SELECT
    lb.Id as lead_id,
    features.advisor_crd,
    DATE(lb.stage_entered_contacting__c) as contacted_date,
    
    -- Base features (11 total - required for LeadScorerV2)
    -- Calculate aum_growth_since_jan2024_pct from firm AUM data at PIT month vs Jan 2024
    COALESCE(
        CASE 
            WHEN fh_jan24.TOTAL_AUM > 0 AND features.firm_aum_pit IS NOT NULL
            THEN (features.firm_aum_pit - fh_jan24.TOTAL_AUM) * 100.0 / fh_jan24.TOTAL_AUM
            ELSE 0
        END,
        0
    ) as aum_growth_since_jan2024_pct,
    COALESCE(features.current_firm_tenure_months, 0) as current_firm_tenure_months,
    COALESCE(features.firm_aum_pit, 0) as firm_aum_pit,
    COALESCE(features.firm_net_change_12mo, 0) as firm_net_change_12mo,
    COALESCE(features.firm_rep_count_at_contact, 0) as firm_rep_count_at_contact,
    COALESCE(features.industry_tenure_months, 0) as industry_tenure_months,
    COALESCE(features.num_prior_firms, 0) as num_prior_firms,
    CASE WHEN features.pit_mobility_tier = 'Highly Mobile' THEN 1 ELSE 0 END as pit_mobility_tier_Highly_Mobile,
    CASE WHEN features.pit_mobility_tier = 'Mobile' THEN 1 ELSE 0 END as pit_mobility_tier_Mobile,
    CASE WHEN features.pit_mobility_tier = 'Stable' THEN 1 ELSE 0 END as pit_mobility_tier_Stable,
    COALESCE(features.pit_moves_3yr, 0) as pit_moves_3yr,
    
    -- Metadata
    CURRENT_TIMESTAMP() as feature_extraction_timestamp,
    'v2-boosted' as model_version_required
    
FROM `{PROJECT_ID}.SavvyGTMData.Lead` lb
LEFT JOIN `{PROJECT_ID}.ml_features.lead_scoring_features_pit` features
    ON lb.Id = features.lead_id
-- Get Jan 2024 AUM baseline for growth calculation
LEFT JOIN `{PROJECT_ID}.FinTrx_data_CA.Firm_historicals` fh_jan24
    ON features.firm_crd_at_contact = SAFE_CAST(fh_jan24.RIA_INVESTOR_CRD_ID AS INT64)
    AND fh_jan24.YEAR = 2024
    AND fh_jan24.MONTH = 1
WHERE lb.stage_entered_contacting__c IS NOT NULL
    AND lb.FA_CRD__c IS NOT NULL
    AND DATE(lb.stage_entered_contacting__c) >= '2024-02-01'
    AND DATE(lb.stage_entered_contacting__c) <= CURRENT_DATE()
"""

# SQL for creating scores table
CREATE_SCORES_TABLE = f"""
CREATE OR REPLACE TABLE `{PROJECT_ID}.ml_features.lead_scores_daily`
(
    lead_id STRING,
    advisor_crd STRING,
    contacted_date DATE,
    score_date DATE,
    lead_score FLOAT64,
    score_bucket STRING,
    action_recommended STRING,
    uncalibrated_score FLOAT64,
    pit_restlessness_ratio FLOAT64,
    flight_risk_score FLOAT64,
    is_fresh_start INT64,
    narrative STRING,
    model_version STRING,
    scoring_timestamp TIMESTAMP
)
PARTITION BY score_date
CLUSTER BY lead_id, score_bucket
"""

print("="*60)
print("PHASE 7.1: BIGQUERY INFRASTRUCTURE SETUP")
print("="*60)

print("\nCreating feature table...")
job = client.query(CREATE_FEATURES_TABLE)
job.result()
print("[OK] Feature table created")

print("\nCreating scores table...")
job = client.query(CREATE_SCORES_TABLE)
job.result()
print("[OK] Scores table created")

# Validation query
VALIDATION_QUERY = f"""
SELECT 
    COUNT(*) as total_leads,
    COUNT(DISTINCT DATE(contacted_date)) as unique_dates,
    MIN(contacted_date) as earliest_date,
    MAX(contacted_date) as latest_date,
    COUNTIF(pit_moves_3yr > 0) as leads_with_moves,
    COUNTIF(firm_net_change_12mo < 0) as leads_at_bleeding_firms
FROM `{PROJECT_ID}.ml_features.lead_scoring_features`
"""

print("\nValidating feature table...")
try:
    results = client.query(VALIDATION_QUERY).result()
    for row in results:
        print(f"  Total leads: {row.total_leads:,}")
        print(f"  Unique dates: {row.unique_dates}")
        print(f"  Date range: {row.earliest_date} to {row.latest_date}")
        print(f"  Leads with moves: {row.leads_with_moves:,}")
        print(f"  Leads at bleeding firms: {row.leads_at_bleeding_firms:,}")
except Exception as e:
    print(f"  Warning: Validation query failed (table may be empty): {e}")

print("\n[OK] Phase 7.1 complete!")
print("="*60)
