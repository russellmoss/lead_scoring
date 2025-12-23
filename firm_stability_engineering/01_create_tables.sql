-- ============================================================================
-- PIT FIRM STABILITY SCORING: TABLE CREATION
-- ============================================================================
-- Run this FIRST to create the required tables
-- Dataset: savvy-gtm-analytics.ml_features (create if doesn't exist)

-- Create dataset if needed (run in BigQuery console)
-- CREATE SCHEMA IF NOT EXISTS `savvy-gtm-analytics.ml_features`
-- OPTIONS(location = 'northamerica-northeast2');

-- ============================================================================
-- TABLE 1: Monthly Firm Stability Scores
-- ============================================================================
CREATE TABLE IF NOT EXISTS `savvy-gtm-analytics.ml_features.firm_stability_scores_monthly`
(
  -- Keys
  firm_crd INT64 NOT NULL,
  score_month DATE NOT NULL,
  
  -- Raw Metrics
  departures_12mo INT64,
  arrivals_12mo INT64,
  net_change_12mo INT64,
  rep_count_at_month INT64,
  
  -- Calculated Scores
  turnover_rate_pct FLOAT64,
  net_change_score FLOAT64,
  net_change_percentile FLOAT64,
  recruiting_priority STRING,
  
  -- Firm Info
  firm_name STRING,
  firm_state STRING,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY score_month
CLUSTER BY firm_crd
OPTIONS(
  description = 'Monthly firm stability scores for PIT lead scoring. Updated monthly after FINTRX refresh.'
);

-- ============================================================================
-- TABLE 2: Lead PIT Features
-- ============================================================================
CREATE TABLE IF NOT EXISTS `savvy-gtm-analytics.ml_features.lead_pit_features`
(
  -- Lead Identifiers
  lead_id STRING NOT NULL,
  advisor_crd INT64,
  
  -- Timing
  stage_entered_contacting DATE,
  pit_score_month DATE,
  
  -- Firm at Entry
  firm_crd_at_entry INT64,
  firm_name_at_entry STRING,
  
  -- PIT Features
  pit_departures_12mo INT64,
  pit_arrivals_12mo INT64,
  pit_net_change_12mo INT64,
  pit_rep_count INT64,
  pit_turnover_rate_pct FLOAT64,
  pit_net_change_score FLOAT64,
  pit_net_change_percentile FLOAT64,
  pit_recruiting_priority STRING,
  
  -- Target Variable
  converted_to_mql BOOLEAN,
  days_to_mql INT64,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY stage_entered_contacting
CLUSTER BY firm_crd_at_entry
OPTIONS(
  description = 'Lead-level PIT firm stability features for ML training. Target: Contacting to MQL conversion.'
);
