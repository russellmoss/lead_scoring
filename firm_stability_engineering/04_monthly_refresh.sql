-- ============================================================================
-- PIT FIRM STABILITY SCORING: MONTHLY REFRESH
-- ============================================================================
-- Schedule this to run monthly (e.g., 5th of each month at 6 AM)
-- Calculates scores for the prior month only

-- ============================================================================
-- STEP 1: Set the score month (prior month)
-- ============================================================================
DECLARE score_month DATE DEFAULT DATE_TRUNC(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH);

-- ============================================================================
-- STEP 2: Delete existing data for this month (if re-running)
-- ============================================================================
DELETE FROM `savvy-gtm-analytics.ml_features.firm_stability_scores_monthly`
WHERE score_month = score_month;

-- ============================================================================
-- STEP 3: Insert new scores for this month
-- ============================================================================
INSERT INTO `savvy-gtm-analytics.ml_features.firm_stability_scores_monthly`

WITH 
-- Get current headcount for all firms
firm_headcount AS (
  SELECT 
    PRIMARY_FIRM as firm_crd,
    COUNT(DISTINCT RIA_CONTACT_CRD_ID) as rep_count
  FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
  WHERE PRIMARY_FIRM IS NOT NULL
  GROUP BY PRIMARY_FIRM
  HAVING rep_count >= 5
),

-- Calculate departures (12 months ending at score_month)
departures AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    COUNT(DISTINCT RIA_CONTACT_CRD_ID) as departures_12mo
  FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    AND PREVIOUS_REGISTRATION_COMPANY_END_DATE > DATE_SUB(score_month, INTERVAL 12 MONTH)
    AND PREVIOUS_REGISTRATION_COMPANY_END_DATE <= score_month
  GROUP BY firm_crd
),

-- Calculate arrivals (12 months ending at score_month)
arrivals AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    COUNT(DISTINCT RIA_CONTACT_CRD_ID) as arrivals_12mo
  FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE_SUB(score_month, INTERVAL 12 MONTH)
    AND PREVIOUS_REGISTRATION_COMPANY_START_DATE <= score_month
  GROUP BY firm_crd
),

-- Combine metrics
firm_metrics AS (
  SELECT
    h.firm_crd,
    score_month as score_month,
    h.rep_count as rep_count_at_month,
    COALESCE(d.departures_12mo, 0) as departures_12mo,
    COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
    COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as net_change_12mo,
    
    CASE 
      WHEN h.rep_count > 0 
      THEN ROUND(COALESCE(d.departures_12mo, 0) * 100.0 / h.rep_count, 2)
      ELSE 0
    END as turnover_rate_pct,
    
    ROUND(GREATEST(0, LEAST(100, 
      50 + ((COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0)) * 3.5)
    )), 1) as net_change_score
    
  FROM firm_headcount h
  LEFT JOIN departures d ON h.firm_crd = d.firm_crd
  LEFT JOIN arrivals a ON h.firm_crd = a.firm_crd
),

-- Calculate percentiles
firm_with_percentiles AS (
  SELECT
    fm.*,
    ROUND(PERCENT_RANK() OVER (ORDER BY fm.net_change_12mo) * 100, 1) as net_change_percentile
  FROM firm_metrics fm
)

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
-- STEP 4: Log the refresh
-- ============================================================================
SELECT
  FORMAT('Monthly refresh completed for %t', score_month) as status,
  COUNT(*) as firms_scored,
  COUNTIF(recruiting_priority = 'HIGH_PRIORITY') as high_priority_count,
  COUNTIF(recruiting_priority = 'STABLE') as stable_count
FROM `savvy-gtm-analytics.ml_features.firm_stability_scores_monthly`
WHERE score_month = score_month;
