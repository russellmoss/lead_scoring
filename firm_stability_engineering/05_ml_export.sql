-- ============================================================================
-- PIT FIRM STABILITY SCORING: ML TRAINING DATA EXPORT
-- ============================================================================
-- Use this query to export data for model training
-- Target: Contacting → MQL conversion prediction

-- ============================================================================
-- OPTION 1: Simple Feature Export
-- ============================================================================
-- Core features for initial model

SELECT
  lead_id,
  stage_entered_contacting,
  firm_crd_at_entry,
  firm_name_at_entry,
  
  -- Primary Features (most predictive)
  pit_net_change_12mo,
  pit_net_change_percentile,
  pit_net_change_score,
  
  -- Secondary Features
  pit_turnover_rate_pct,
  pit_rep_count,
  pit_departures_12mo,
  pit_arrivals_12mo,
  
  -- Categorical
  pit_recruiting_priority,
  
  -- Target
  CASE WHEN converted_to_mql THEN 1 ELSE 0 END as target,
  days_to_mql

FROM `savvy-gtm-analytics.ml_features.lead_pit_features`
WHERE 
  -- Only leads with firm scores
  pit_net_change_score IS NOT NULL
  -- Focus on reasonable time window
  AND stage_entered_contacting >= '2024-02-01'
ORDER BY stage_entered_contacting;


-- ============================================================================
-- OPTION 2: Enhanced Feature Export with Derived Features
-- ============================================================================
-- Includes additional engineered features

SELECT
  lead_id,
  stage_entered_contacting,
  firm_crd_at_entry,
  
  -- Primary Features
  pit_net_change_12mo,
  pit_net_change_percentile,
  pit_net_change_score,
  pit_turnover_rate_pct,
  pit_rep_count,
  
  -- Derived: Firm Size Category
  CASE
    WHEN pit_rep_count < 50 THEN 'SMALL'
    WHEN pit_rep_count < 200 THEN 'MEDIUM'
    WHEN pit_rep_count < 1000 THEN 'LARGE'
    ELSE 'ENTERPRISE'
  END as firm_size_category,
  
  -- Derived: High Velocity Flag (lots of movement)
  CASE
    WHEN pit_departures_12mo >= 15 OR pit_arrivals_12mo >= 10 THEN 1
    ELSE 0
  END as high_velocity_flag,
  
  -- Derived: Severe Bleeding Flag
  CASE
    WHEN pit_net_change_percentile <= 10 THEN 1
    ELSE 0
  END as severe_bleeding_flag,
  
  -- Derived: Small Bleeding Firm (may be more responsive)
  CASE
    WHEN pit_net_change_12mo < -5 AND pit_rep_count < 100 THEN 1
    ELSE 0
  END as small_bleeding_flag,
  
  -- Derived: Log-transformed rep count
  LOG(GREATEST(1, pit_rep_count)) as log_rep_count,
  
  -- One-hot encode priority (for models that need it)
  CASE WHEN pit_recruiting_priority = 'HIGH_PRIORITY' THEN 1 ELSE 0 END as is_high_priority,
  CASE WHEN pit_recruiting_priority = 'MEDIUM_PRIORITY' THEN 1 ELSE 0 END as is_medium_priority,
  CASE WHEN pit_recruiting_priority = 'MONITOR' THEN 1 ELSE 0 END as is_monitor,
  CASE WHEN pit_recruiting_priority = 'STABLE' THEN 1 ELSE 0 END as is_stable,
  
  -- Target
  CASE WHEN converted_to_mql THEN 1 ELSE 0 END as target,
  days_to_mql

FROM `savvy-gtm-analytics.ml_features.lead_pit_features`
WHERE pit_net_change_score IS NOT NULL
  AND stage_entered_contacting >= '2024-02-01';


-- ============================================================================
-- OPTION 3: Summary Statistics for Model Evaluation
-- ============================================================================
-- Check if features have predictive power before training

SELECT
  'FEATURE ANALYSIS' as section,
  pit_recruiting_priority,
  
  -- Sample size
  COUNT(*) as n_leads,
  
  -- Conversion metrics
  COUNTIF(converted_to_mql) as n_converted,
  ROUND(AVG(CASE WHEN converted_to_mql THEN 1.0 ELSE 0.0 END) * 100, 2) as conversion_rate_pct,
  
  -- Feature distributions
  ROUND(AVG(pit_net_change_12mo), 1) as avg_net_change,
  ROUND(AVG(pit_rep_count), 0) as avg_rep_count,
  ROUND(AVG(pit_turnover_rate_pct), 1) as avg_turnover_pct

FROM `savvy-gtm-analytics.ml_features.lead_pit_features`
WHERE pit_net_change_score IS NOT NULL
  AND stage_entered_contacting >= '2024-02-01'
GROUP BY pit_recruiting_priority
ORDER BY conversion_rate_pct DESC;


-- ============================================================================
-- OPTION 4: Train/Test Split Export
-- ============================================================================
-- Export with pre-defined train/test split (80/20 by time)

WITH ranked_leads AS (
  SELECT
    *,
    NTILE(5) OVER (ORDER BY stage_entered_contacting) as time_bucket
  FROM `savvy-gtm-analytics.ml_features.lead_pit_features`
  WHERE pit_net_change_score IS NOT NULL
    AND stage_entered_contacting >= '2024-02-01'
)

SELECT
  *,
  CASE 
    WHEN time_bucket <= 4 THEN 'TRAIN'  -- 80% oldest for training
    ELSE 'TEST'                          -- 20% newest for testing
  END as split
FROM ranked_leads
ORDER BY stage_entered_contacting;


-- ============================================================================
-- DATA QUALITY CHECK: Run before exporting
-- ============================================================================
SELECT
  'DATA QUALITY CHECK' as section,
  COUNT(*) as total_leads,
  COUNTIF(pit_net_change_score IS NOT NULL) as leads_with_features,
  ROUND(COUNTIF(pit_net_change_score IS NOT NULL) * 100.0 / COUNT(*), 1) as feature_coverage_pct,
  
  COUNTIF(converted_to_mql) as total_conversions,
  ROUND(COUNTIF(converted_to_mql) * 100.0 / COUNTIF(pit_net_change_score IS NOT NULL), 2) as conversion_rate_pct,
  
  MIN(stage_entered_contacting) as earliest_lead,
  MAX(stage_entered_contacting) as latest_lead,
  
  COUNT(DISTINCT firm_crd_at_entry) as unique_firms

FROM `savvy-gtm-analytics.ml_features.lead_pit_features`
WHERE stage_entered_contacting >= '2024-02-01';
