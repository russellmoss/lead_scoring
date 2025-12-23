
-- Phase 2.1: Temporal Train/Validation/Test Split
-- Using date configuration from Phase 0.0

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_splits` AS

WITH lead_dates AS (
    SELECT
        lead_id,
        contacted_date,
        target
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
    WHERE target IS NOT NULL
        AND contacted_date >= '2024-02-01'
        AND contacted_date <= '2025-10-01'
)

SELECT
    lead_id,
    contacted_date,
    target,
    CASE
        WHEN contacted_date <= '2025-07-03' THEN 'TRAIN'
        WHEN contacted_date >= '2025-08-02' AND contacted_date <= '2025-10-01' THEN 'TEST'
        ELSE 'GAP'  -- Leads in gap period (excluded from training)
    END as split,
    '2025-07-03' as train_end_date,
    '2025-08-02' as test_start_date,
    '2025-10-01' as test_end_date,
    30 as gap_days
FROM lead_dates
