-- Create safe velocity features table
-- Uses START_DATE only (no END_DATE leakage)
-- All features calculated as of contacted_date (PIT)

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_velocity_features` AS

WITH leads AS (
    -- Get all leads from splits table
    SELECT DISTINCT
        s.lead_id,
        s.advisor_crd,
        s.contacted_date,
        s.target
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2` s
    WHERE s.advisor_crd IS NOT NULL
),

employment_history AS (
    -- Get employment history ordered by start date
    SELECT 
        RIA_CONTACT_CRD_ID as advisor_crd,
        PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
        PREVIOUS_REGISTRATION_COMPANY_START_DATE as start_date,
        PREVIOUS_REGISTRATION_COMPANY_END_DATE as end_date
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE IS NOT NULL
),

-- For each lead, get their job history as of contact date
lead_job_history AS (
    SELECT 
        l.lead_id,
        l.advisor_crd,
        l.contacted_date,
        l.target,
        eh.firm_crd,
        eh.start_date,
        eh.end_date,
        -- Calculate tenure using ONLY start_date (safe)
        -- For current job: tenure = contacted_date - start_date
        -- For past jobs: tenure = end_date - start_date (only if end_date <= contacted_date)
        CASE 
            WHEN eh.end_date IS NULL OR eh.end_date >= l.contacted_date 
            THEN DATE_DIFF(l.contacted_date, eh.start_date, DAY)
            ELSE DATE_DIFF(eh.end_date, eh.start_date, DAY)
        END as tenure_days,
        -- Is this job current as of contact date?
        CASE 
            WHEN eh.end_date IS NULL OR eh.end_date >= l.contacted_date 
            THEN TRUE ELSE FALSE 
        END as is_current,
        -- Job sequence number (most recent = 1)
        ROW_NUMBER() OVER (
            PARTITION BY l.lead_id 
            ORDER BY eh.start_date DESC
        ) as job_seq
    FROM leads l
    INNER JOIN employment_history eh ON l.advisor_crd = eh.advisor_crd
    WHERE eh.start_date <= l.contacted_date  -- Only jobs started before contact
),

-- Get previous job start date for each lead
previous_job_dates AS (
    SELECT 
        lead_id,
        MAX(CASE WHEN job_seq = 2 THEN start_date END) as prev_job_start_date
    FROM lead_job_history
    GROUP BY lead_id
),

-- Calculate velocity features per lead
velocity_features AS (
    SELECT 
        ljh.lead_id,
        ljh.advisor_crd,
        ljh.contacted_date,
        ljh.target,
        
        -- Total jobs as of contact date (from START_DATEs only)
        COUNT(*) as total_jobs_pit,
        
        -- Days at current firm (from START_DATE only)
        MAX(CASE WHEN ljh.is_current THEN ljh.tenure_days ELSE NULL END) as days_at_current_firm,
        
        -- Days since last move (safe: uses start_date of current job - start_date of previous job)
        MAX(CASE 
            WHEN ljh.job_seq = 1 AND ljh.is_current AND pjd.prev_job_start_date IS NOT NULL
            THEN DATE_DIFF(ljh.contacted_date, pjd.prev_job_start_date, DAY)
            ELSE NULL 
        END) as days_since_last_move_safe,
        
        -- Previous job tenure (from START_DATEs only)
        MAX(CASE WHEN ljh.job_seq = 2 THEN ljh.tenure_days ELSE NULL END) as prev_job_tenure_days,
        
        -- Average prior job tenure (excluding current)
        AVG(CASE WHEN NOT ljh.is_current THEN ljh.tenure_days ELSE NULL END) as avg_prior_tenure_days,
        
        -- Number of moves in last 3 years (from START_DATEs only)
        -- Count jobs that STARTED in last 3 years (excluding current job)
        COUNTIF(
            ljh.start_date >= DATE_SUB(ljh.contacted_date, INTERVAL 3 YEAR)
            AND ljh.start_date < ljh.contacted_date
            AND NOT ljh.is_current
        ) as moves_3yr_from_starts
        
    FROM lead_job_history ljh
    LEFT JOIN previous_job_dates pjd ON ljh.lead_id = pjd.lead_id
    GROUP BY ljh.lead_id, ljh.advisor_crd, ljh.contacted_date, ljh.target
)

SELECT 
    vf.*,
    
    -- Tenure ratio: current / previous (if both exist)
    CASE 
        WHEN vf.prev_job_tenure_days > 0 AND vf.days_at_current_firm IS NOT NULL
        THEN SAFE_DIVIDE(vf.days_at_current_firm, vf.prev_job_tenure_days)
        ELSE NULL
    END as tenure_ratio,
    
    -- In danger zone: 1-2 years at current firm (high conversion period)
    CASE 
        WHEN vf.days_at_current_firm >= 365 AND vf.days_at_current_firm < 730
        THEN 1
        ELSE 0
    END as in_danger_zone,
    
    -- Tenure bucket (categorical)
    CASE 
        WHEN vf.days_at_current_firm IS NULL THEN 'Unknown'
        WHEN vf.days_at_current_firm < 180 THEN 'New (< 6mo)'
        WHEN vf.days_at_current_firm < 365 THEN 'Early (6-12mo)'
        WHEN vf.days_at_current_firm < 730 THEN 'Danger Zone (1-2yr)'
        WHEN vf.days_at_current_firm < 1095 THEN 'Established (2-3yr)'
        ELSE 'Veteran (> 3yr)'
    END as tenure_bucket
    
FROM velocity_features vf
