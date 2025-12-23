-- ============================================================================
-- SAFE VELOCITY FEATURES TABLE
-- ============================================================================
-- Run this in BigQuery Console FIRST, before running train_with_velocity.py
--
-- Key Safety Features:
--   ✅ Uses ONLY start_date (never end_date - avoids backfill leakage)
--   ✅ All features calculated relative to contacted_date (Point-in-Time)
--   ✅ Only includes jobs that STARTED before contact date
-- ============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_velocity_features` AS

WITH leads AS (
    -- Get all leads with their contacted_date
    SELECT 
        lead_id,
        advisor_crd,
        contacted_date,
        target,
        split
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2`
    WHERE advisor_crd IS NOT NULL
),

employment_history AS (
    -- Clean employment history - ONLY USE START_DATE (safe from backfill)
    SELECT 
        RIA_CONTACT_CRD_ID as advisor_crd,
        PREVIOUS_REGISTRATION_COMPANY_START_DATE as job_start_date,
        PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE IS NOT NULL
      -- Exclude clearly erroneous dates
      AND PREVIOUS_REGISTRATION_COMPANY_START_DATE >= '1970-01-01'
      AND PREVIOUS_REGISTRATION_COMPANY_START_DATE <= CURRENT_DATE()
),

-- For each lead, get their job history as of contacted_date
lead_job_history AS (
    SELECT 
        l.lead_id,
        l.advisor_crd,
        l.contacted_date,
        l.target,
        l.split,
        eh.job_start_date,
        eh.firm_crd,
        -- Rank jobs by start date (1 = most recent/current job, 2 = previous, etc.)
        ROW_NUMBER() OVER (
            PARTITION BY l.lead_id 
            ORDER BY eh.job_start_date DESC
        ) as job_rank
    FROM leads l
    LEFT JOIN employment_history eh 
        ON l.advisor_crd = eh.advisor_crd
        -- CRITICAL: Only jobs that STARTED before contact date
        AND eh.job_start_date <= l.contacted_date
),

-- Calculate velocity features per lead
velocity_calcs AS (
    SELECT 
        lead_id,
        advisor_crd,
        contacted_date,
        target,
        split,
        
        -- Total jobs as of contact date
        COUNT(*) as total_jobs_pit,
        
        -- Current job start date (job_rank = 1)
        MAX(CASE WHEN job_rank = 1 THEN job_start_date END) as current_job_start,
        
        -- Previous job start date (job_rank = 2)
        MAX(CASE WHEN job_rank = 2 THEN job_start_date END) as prev_job_start,
        
        -- Third job start date (job_rank = 3) - for acceleration calc
        MAX(CASE WHEN job_rank = 3 THEN job_start_date END) as third_job_start,
        
        -- Count of job changes in last 3 years (using START_DATE only)
        -- This counts jobs that STARTED in the 3 years before contact, excluding current job
        COUNTIF(
            job_start_date >= DATE_SUB(contacted_date, INTERVAL 3 YEAR)
            AND job_rank > 1  -- Exclude current job
        ) as moves_3yr_from_starts
        
    FROM lead_job_history
    GROUP BY lead_id, advisor_crd, contacted_date, target, split
)

SELECT 
    lead_id,
    advisor_crd,
    contacted_date,
    target,
    split,
    total_jobs_pit,
    
    -- =================================================================
    -- FEATURE 1: Days at Current Firm (PIT, START_DATE only)
    -- How long have they been at current firm as of contact?
    -- =================================================================
    DATE_DIFF(contacted_date, current_job_start, DAY) as days_at_current_firm,
    
    -- =================================================================
    -- FEATURE 2: Days Since Last Move (same as above, named for clarity)
    -- This is SAFE because start_date is filed immediately (Form U4)
    -- =================================================================
    DATE_DIFF(contacted_date, current_job_start, DAY) as days_since_last_move_safe,
    
    -- =================================================================
    -- FEATURE 3: Previous Job Tenure (duration of prior job)
    -- How long did they stay at their PREVIOUS job?
    -- Uses two START_DATEs (never END_DATE)
    -- =================================================================
    DATE_DIFF(current_job_start, prev_job_start, DAY) as prev_job_tenure_days,
    
    -- =================================================================
    -- FEATURE 4: Tenure Ratio (current tenure / prev tenure)
    -- If they stayed 5 years at prev job but only 2 years at current,
    -- they might be "due" for a move (ratio < 1)
    -- =================================================================
    SAFE_DIVIDE(
        DATE_DIFF(contacted_date, current_job_start, DAY),  -- Current tenure
        DATE_DIFF(current_job_start, prev_job_start, DAY)   -- Prev tenure
    ) as tenure_ratio,
    
    -- =================================================================
    -- FEATURE 5: In "Danger Zone" (1-2 years at current firm)
    -- Based on diagnostic: Moderate (1-2yr) has 8.79% conversion rate!
    -- =================================================================
    CASE 
        WHEN DATE_DIFF(contacted_date, current_job_start, DAY) BETWEEN 365 AND 730 
        THEN 1 ELSE 0 
    END as in_danger_zone,
    
    -- =================================================================
    -- FEATURE 6: Tenure Bucket (categorical)
    -- =================================================================
    CASE 
        WHEN current_job_start IS NULL THEN 'Unknown'
        WHEN DATE_DIFF(contacted_date, current_job_start, DAY) < 180 THEN 'Very New (<6mo)'
        WHEN DATE_DIFF(contacted_date, current_job_start, DAY) < 365 THEN 'New (6-12mo)'
        WHEN DATE_DIFF(contacted_date, current_job_start, DAY) < 730 THEN 'Danger Zone (1-2yr)'
        WHEN DATE_DIFF(contacted_date, current_job_start, DAY) < 1460 THEN 'Established (2-4yr)'
        ELSE 'Veteran (4yr+)'
    END as tenure_bucket,
    
    -- =================================================================
    -- FEATURE 7: Has Prior Moves (binary)
    -- =================================================================
    CASE WHEN prev_job_start IS NOT NULL THEN 1 ELSE 0 END as has_prior_moves_velocity,
    
    -- =================================================================
    -- FEATURE 8: Move Count from START_DATEs
    -- =================================================================
    moves_3yr_from_starts,
    
    -- =================================================================
    -- Raw dates for debugging (optional - can remove in production)
    -- =================================================================
    current_job_start,
    prev_job_start

FROM velocity_calcs;

-- ============================================================================
-- VERIFICATION QUERIES (run after table creation)
-- ============================================================================

-- Check row count
-- SELECT COUNT(*) as total_rows FROM `savvy-gtm-analytics.ml_features.lead_velocity_features`;

-- Check feature coverage
-- SELECT 
--     COUNT(*) as total,
--     COUNTIF(days_at_current_firm IS NOT NULL) as has_days_at_firm,
--     COUNTIF(in_danger_zone = 1) as in_danger_zone_count,
--     COUNTIF(prev_job_tenure_days IS NOT NULL) as has_prev_tenure
-- FROM `savvy-gtm-analytics.ml_features.lead_velocity_features`;

-- Check danger zone conversion rate
-- SELECT 
--     in_danger_zone,
--     COUNT(*) as count,
--     AVG(target) as conversion_rate
-- FROM `savvy-gtm-analytics.ml_features.lead_velocity_features`
-- GROUP BY in_danger_zone
-- ORDER BY in_danger_zone;

-- Check tenure bucket distribution
-- SELECT 
--     tenure_bucket,
--     COUNT(*) as count,
--     AVG(target) as conversion_rate
-- FROM `savvy-gtm-analytics.ml_features.lead_velocity_features`
-- GROUP BY tenure_bucket
-- ORDER BY conversion_rate DESC;
