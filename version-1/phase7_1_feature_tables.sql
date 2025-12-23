"""
Phase 7.1: BigQuery Infrastructure Setup
Creates production tables for feature storage and scoring results
"""

-- ========================================================================
-- TABLE 1: lead_scoring_features
-- Stores the 11 base features required for scoring
-- ========================================================================
CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_features`
PARTITION BY DATE(contacted_date)
CLUSTER BY advisor_crd
AS
SELECT
    lb.lead_id,
    lb.advisor_crd,
    DATE(lb.stage_entered_contacting__c) as contacted_date,
    
    -- Base features (11 total - required for LeadScorerV2)
    COALESCE(features.aum_growth_since_jan2024_pct, 0) as aum_growth_since_jan2024_pct,
    COALESCE(features.current_firm_tenure_months, 0) as current_firm_tenure_months,
    COALESCE(features.firm_aum_pit, 0) as firm_aum_pit,
    COALESCE(features.firm_net_change_12mo, 0) as firm_net_change_12mo,
    COALESCE(features.firm_rep_count_at_contact, 0) as firm_rep_count_at_contact,
    COALESCE(features.industry_tenure_months, 0) as industry_tenure_months,
    COALESCE(features.num_prior_firms, 0) as num_prior_firms,
    COALESCE(features.pit_mobility_tier_Highly Mobile, 0) as pit_mobility_tier_Highly_Mobile,
    COALESCE(features.pit_mobility_tier_Mobile, 0) as pit_mobility_tier_Mobile,
    COALESCE(features.pit_mobility_tier_Stable, 0) as pit_mobility_tier_Stable,
    COALESCE(features.pit_moves_3yr, 0) as pit_moves_3yr,
    
    -- Metadata
    CURRENT_TIMESTAMP() as feature_extraction_timestamp,
    'v2-boosted' as model_version_required
    
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` lb
LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` features
    ON lb.Id = features.lead_id
WHERE lb.stage_entered_contacting__c IS NOT NULL
    AND lb.FA_CRD__c IS NOT NULL
    AND DATE(lb.stage_entered_contacting__c) >= '2024-02-01'
    AND DATE(lb.stage_entered_contacting__c) <= CURRENT_DATE()
;

-- ========================================================================
-- TABLE 2: lead_scores_daily
-- Stores the final scores and predictions
-- ========================================================================
CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scores_daily`
PARTITION BY DATE(score_date)
CLUSTER BY lead_id, score_bucket
AS
SELECT
    CAST(NULL AS STRING) as lead_id,
    CAST(NULL AS STRING) as advisor_crd,
    CAST(NULL AS DATE) as contacted_date,
    CAST(NULL AS DATE) as score_date,
    CAST(NULL AS FLOAT64) as lead_score,
    CAST(NULL AS STRING) as score_bucket,
    CAST(NULL AS STRING) as action_recommended,
    CAST(NULL AS FLOAT64) as uncalibrated_score,
    CAST(NULL AS FLOAT64) as pit_restlessness_ratio,
    CAST(NULL AS FLOAT64) as flight_risk_score,
    CAST(NULL AS INT64) as is_fresh_start,
    CAST(NULL AS STRING) as narrative,
    CAST(NULL AS STRING) as model_version,
    CAST(NULL AS TIMESTAMP) as scoring_timestamp
WHERE FALSE  -- Create empty table with schema
;

-- Add schema explicitly
ALTER TABLE `savvy-gtm-analytics.ml_features.lead_scores_daily`
ADD COLUMN IF NOT EXISTS lead_id STRING,
ADD COLUMN IF NOT EXISTS advisor_crd STRING,
ADD COLUMN IF NOT EXISTS contacted_date DATE,
ADD COLUMN IF NOT EXISTS score_date DATE,
ADD COLUMN IF NOT EXISTS lead_score FLOAT64,
ADD COLUMN IF NOT EXISTS score_bucket STRING,
ADD COLUMN IF NOT EXISTS action_recommended STRING,
ADD COLUMN IF NOT EXISTS uncalibrated_score FLOAT64,
ADD COLUMN IF NOT EXISTS pit_restlessness_ratio FLOAT64,
ADD COLUMN IF NOT EXISTS flight_risk_score FLOAT64,
ADD COLUMN IF NOT EXISTS is_fresh_start INT64,
ADD COLUMN IF NOT EXISTS narrative STRING,
ADD COLUMN IF NOT EXISTS model_version STRING,
ADD COLUMN IF NOT EXISTS scoring_timestamp TIMESTAMP
;

-- ========================================================================
-- VALIDATION QUERIES
-- ========================================================================

-- Check feature table
SELECT 
    COUNT(*) as total_leads,
    COUNT(DISTINCT DATE(contacted_date)) as unique_dates,
    MIN(contacted_date) as earliest_date,
    MAX(contacted_date) as latest_date,
    COUNTIF(pit_moves_3yr > 0) as leads_with_moves,
    COUNTIF(firm_net_change_12mo < 0) as leads_at_bleeding_firms
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features`
;

