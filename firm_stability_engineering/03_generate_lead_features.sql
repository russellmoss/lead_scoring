-- ============================================================================
-- PIT FIRM STABILITY SCORING: GENERATE LEAD FEATURES
-- ============================================================================
-- Run this THIRD after firm scores are populated
-- Creates ML training dataset with PIT features for each lead

-- Clear existing data (optional)
-- TRUNCATE TABLE `savvy-gtm-analytics.ml_features.lead_pit_features`;

INSERT INTO `savvy-gtm-analytics.ml_features.lead_pit_features`

WITH 
-- Get leads with entry dates and target variable
leads AS (
  SELECT
    l.Id as lead_id,
    SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) as advisor_crd,
    CAST(l.stage_entered_contacting__c AS DATE) as stage_entered_contacting,
    
    -- PIT month: first day of month BEFORE entry (to ensure data was available)
    DATE_TRUNC(DATE_SUB(CAST(l.stage_entered_contacting__c AS DATE), INTERVAL 1 MONTH), MONTH) as pit_score_month,
    
    -- Target: converted to MQL?
    CASE WHEN l.stage_entered_MQL__c IS NOT NULL THEN TRUE ELSE FALSE END as converted_to_mql,
    
    -- Days to MQL (NULL if not converted)
    CASE 
      WHEN l.stage_entered_MQL__c IS NOT NULL 
      THEN DATE_DIFF(CAST(l.stage_entered_MQL__c AS DATE), CAST(l.stage_entered_contacting__c AS DATE), DAY)
      ELSE NULL 
    END as days_to_mql
    
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.FA_CRD__c IS NOT NULL
    -- Focus on leads from 2024 onwards (when we have firm scores)
    AND CAST(l.stage_entered_contacting__c AS DATE) >= '2024-02-01'
    -- Exclude Savvy's own advisors
    AND (l.Company IS NULL OR l.Company NOT LIKE '%Savvy%')
),

-- Get advisor's firm at entry time using employment history
advisor_firm_at_entry AS (
  SELECT
    l.lead_id,
    l.advisor_crd,
    l.stage_entered_contacting,
    l.pit_score_month,
    l.converted_to_mql,
    l.days_to_mql,
    h.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd_at_entry,
    h.PREVIOUS_REGISTRATION_COMPANY_NAME as firm_name_at_entry
  FROM leads l
  INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
    ON l.advisor_crd = h.RIA_CONTACT_CRD_ID
  WHERE 
    -- Was employed at this firm when they entered contacting
    h.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= l.stage_entered_contacting
    AND (h.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
         OR h.PREVIOUS_REGISTRATION_COMPANY_END_DATE > l.stage_entered_contacting)
  -- Take most recent employment if multiple
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY l.lead_id
    ORDER BY h.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
  ) = 1
)

-- Join to pre-calculated firm scores
SELECT
  af.lead_id,
  af.advisor_crd,
  af.stage_entered_contacting,
  af.pit_score_month,
  af.firm_crd_at_entry,
  af.firm_name_at_entry,
  
  -- PIT Firm Stability Features
  fs.departures_12mo as pit_departures_12mo,
  fs.arrivals_12mo as pit_arrivals_12mo,
  fs.net_change_12mo as pit_net_change_12mo,
  fs.rep_count_at_month as pit_rep_count,
  fs.turnover_rate_pct as pit_turnover_rate_pct,
  fs.net_change_score as pit_net_change_score,
  fs.net_change_percentile as pit_net_change_percentile,
  fs.recruiting_priority as pit_recruiting_priority,
  
  -- Target Variable
  af.converted_to_mql,
  af.days_to_mql,
  
  CURRENT_TIMESTAMP() as created_at

FROM advisor_firm_at_entry af
LEFT JOIN `savvy-gtm-analytics.ml_features.firm_stability_scores_monthly` fs
  ON af.firm_crd_at_entry = fs.firm_crd
  AND af.pit_score_month = fs.score_month;


-- ============================================================================
-- VERIFICATION: Check coverage and conversion rates
-- ============================================================================
-- Run this after the insert to verify results

-- SELECT
--   'COVERAGE CHECK' as section,
--   COUNT(*) as total_leads,
--   COUNTIF(pit_net_change_score IS NOT NULL) as leads_with_scores,
--   ROUND(COUNTIF(pit_net_change_score IS NOT NULL) * 100.0 / COUNT(*), 1) as coverage_pct,
--   COUNTIF(converted_to_mql) as mql_conversions,
--   ROUND(COUNTIF(converted_to_mql) * 100.0 / COUNT(*), 2) as overall_conversion_rate
-- FROM `savvy-gtm-analytics.ml_features.lead_pit_features`;

-- SELECT
--   'CONVERSION BY PRIORITY' as section,
--   pit_recruiting_priority,
--   COUNT(*) as leads,
--   COUNTIF(converted_to_mql) as conversions,
--   ROUND(COUNTIF(converted_to_mql) * 100.0 / COUNT(*), 2) as conversion_rate_pct
-- FROM `savvy-gtm-analytics.ml_features.lead_pit_features`
-- WHERE pit_recruiting_priority IS NOT NULL
-- GROUP BY pit_recruiting_priority
-- ORDER BY conversion_rate_pct DESC;
