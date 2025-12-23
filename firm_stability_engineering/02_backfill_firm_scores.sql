-- ============================================================================
-- PIT FIRM STABILITY SCORING: BACKFILL HISTORICAL SCORES
-- ============================================================================
-- Run this SECOND to populate historical firm scores
-- This creates monthly scores from January 2024 to current month
-- Takes ~10-15 minutes to run

-- Clear existing data (optional - for fresh start)
-- TRUNCATE TABLE `savvy-gtm-analytics.ml_features.firm_stability_scores_monthly`;

-- ============================================================================
-- BACKFILL PROCEDURE
-- ============================================================================
-- This query calculates scores for ALL months in a single pass

INSERT INTO `savvy-gtm-analytics.ml_features.firm_stability_scores_monthly`

WITH 
-- Generate list of months to calculate
months_to_calculate AS (
  SELECT score_month
  FROM UNNEST(GENERATE_DATE_ARRAY(
    DATE('2024-01-01'),
    DATE_TRUNC(CURRENT_DATE(), MONTH),
    INTERVAL 1 MONTH
  )) as score_month
),

-- Get current headcount for all firms (proxy for historical - acceptable approximation)
firm_headcount AS (
  SELECT 
    PRIMARY_FIRM as firm_crd,
    COUNT(DISTINCT RIA_CONTACT_CRD_ID) as rep_count
  FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
  WHERE PRIMARY_FIRM IS NOT NULL
  GROUP BY PRIMARY_FIRM
  HAVING rep_count >= 5
),

-- Calculate departures for each firm-month combination
departures AS (
  SELECT
    eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    m.score_month,
    COUNT(DISTINCT eh.RIA_CONTACT_CRD_ID) as departures_12mo
  FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
  CROSS JOIN months_to_calculate m
  WHERE eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE > DATE_SUB(m.score_month, INTERVAL 12 MONTH)
    AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE <= m.score_month
  GROUP BY firm_crd, score_month
),

-- Calculate arrivals for each firm-month combination
arrivals AS (
  SELECT
    eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    m.score_month,
    COUNT(DISTINCT eh.RIA_CONTACT_CRD_ID) as arrivals_12mo
  FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
  CROSS JOIN months_to_calculate m
  WHERE eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE_SUB(m.score_month, INTERVAL 12 MONTH)
    AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= m.score_month
  GROUP BY firm_crd, score_month
),

-- Combine all firm-month combinations
firm_months AS (
  SELECT DISTINCT
    h.firm_crd,
    m.score_month,
    h.rep_count as rep_count_at_month
  FROM firm_headcount h
  CROSS JOIN months_to_calculate m
),

-- Calculate metrics
firm_metrics AS (
  SELECT
    fm.firm_crd,
    fm.score_month,
    fm.rep_count_at_month,
    COALESCE(d.departures_12mo, 0) as departures_12mo,
    COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
    COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as net_change_12mo,
    
    -- Turnover rate
    CASE 
      WHEN fm.rep_count_at_month > 0 
      THEN ROUND(COALESCE(d.departures_12mo, 0) * 100.0 / fm.rep_count_at_month, 2)
      ELSE 0
    END as turnover_rate_pct,
    
    -- Net change score (0-100)
    ROUND(GREATEST(0, LEAST(100, 
      50 + ((COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0)) * 3.5)
    )), 1) as net_change_score
    
  FROM firm_months fm
  LEFT JOIN departures d ON fm.firm_crd = d.firm_crd AND fm.score_month = d.score_month
  LEFT JOIN arrivals a ON fm.firm_crd = a.firm_crd AND fm.score_month = a.score_month
),

-- Calculate percentiles within each month
firm_with_percentiles AS (
  SELECT
    fm.*,
    ROUND(PERCENT_RANK() OVER (
      PARTITION BY fm.score_month 
      ORDER BY fm.net_change_12mo
    ) * 100, 1) as net_change_percentile
  FROM firm_metrics fm
)

-- Final output
SELECT
  fp.firm_crd,
  fp.score_month,
  fp.departures_12mo,
  fp.arrivals_12mo,
  fp.net_change_12mo,
  fp.rep_count_at_month,
  fp.turnover_rate_pct,
  fp.net_change_score,
  fp.net_change_percentile,
  
  -- Priority classification
  CASE
    WHEN fp.net_change_percentile <= 10 THEN 'HIGH_PRIORITY'
    WHEN fp.net_change_percentile <= 25 THEN 'MEDIUM_PRIORITY'
    WHEN fp.net_change_12mo < 0 THEN 'MONITOR'
    ELSE 'STABLE'
  END as recruiting_priority,
  
  f.NAME as firm_name,
  f.MAIN_OFFICE_STATE as firm_state,
  CURRENT_TIMESTAMP() as created_at

FROM firm_with_percentiles fp
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
  ON fp.firm_crd = f.CRD_ID;

-- ============================================================================
-- VERIFICATION QUERY (run after backfill)
-- ============================================================================
-- SELECT
--   score_month,
--   COUNT(*) as firms,
--   ROUND(AVG(net_change_score), 2) as avg_score,
--   COUNTIF(recruiting_priority = 'HIGH_PRIORITY') as high_priority,
--   COUNTIF(recruiting_priority = 'STABLE') as stable
-- FROM `savvy-gtm-analytics.ml_features.firm_stability_scores_monthly`
-- GROUP BY score_month
-- ORDER BY score_month;
