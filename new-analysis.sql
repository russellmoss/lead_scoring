-- ============================================================================
-- FIRM SHOCK → ADVISOR EXODUS FEASIBILITY ANALYSIS
-- ============================================================================
-- Purpose: Test if news events (M&A, SEC investigations, Exec Departures) 
--          correlate with increased advisor departures from firms
-- 
-- If this works, you can create a "Firm Shock Score" to prioritize outreach
-- when the first article hits about a firm's instability
--
-- Dataset: savvy-gtm-analytics.FinTrx_data_CA
-- ============================================================================

-- ============================================================================
-- STEP 0: SCHEMA DISCOVERY (Run this first!)
-- ============================================================================
-- This tells us the exact column names for news tables

SELECT 
    table_name, 
    column_name, 
    data_type
FROM `savvy-gtm-analytics.FinTrx_data_CA.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name IN ('news_ps', 'ria_investors_news')
ORDER BY table_name, ordinal_position;

-- Expected: Look for timestamp field (written_at, published_at, created_at)
--           Look for join keys (article_id, ID, CRD_ID, etc.)


-- ============================================================================
-- STEP 1: NEWS TABLE SAMPLE (Understand what we're working with)
-- ============================================================================

-- Sample news articles
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data_CA.news_ps`
LIMIT 10;

-- Sample news-to-firm linkages
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_investors_news`
LIMIT 10;


-- ============================================================================
-- STEP 2: NEWS COVERAGE STATISTICS
-- ============================================================================

-- How many firms have news coverage?
SELECT 
    COUNT(DISTINCT firm_crd) as firms_with_news,
    COUNT(*) as total_news_links,
    AVG(news_count) as avg_news_per_firm,
    APPROX_QUANTILES(news_count, 10)[OFFSET(5)] as median_news_per_firm
FROM (
    SELECT 
        f.CRD_ID as firm_crd,
        COUNT(*) as news_count
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_investors_news` inv
    JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
        ON inv.RIA_INVESTOR_ID = f.ID
    GROUP BY 1
);


-- ============================================================================
-- STEP 3: KEYWORD-BASED EVENT CLASSIFICATION (MVP)
-- ============================================================================
-- This creates a temp table of news events classified by type

CREATE TEMP TABLE firm_event_candidates AS
WITH news_with_firms AS (
    SELECT
        f.CRD_ID AS firm_crd_id,
        n.ID AS article_id,
        n.TITLE AS title,
        n.SOURCE_URL AS source_url,
        DATE(n.WRITTEN_AT) AS article_date
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_investors_news` inv
    JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
        ON inv.RIA_INVESTOR_ID = f.ID
    JOIN `savvy-gtm-analytics.FinTrx_data_CA.news_ps` n
        ON inv.NEWS_ID = n.ID
    WHERE n.TITLE IS NOT NULL
)
SELECT
    firm_crd_id,
    article_id,
    title,
    source_url,
    article_date,
    CASE
        -- M&A signals
        WHEN REGEXP_CONTAINS(LOWER(title), r'\b(merger|merge|acquir|acquisition|acquired|buyout|sale to|sold to|purchase|deal)\b')
            THEN 'MA'

        -- SEC / Regulatory investigations & enforcement
        WHEN REGEXP_CONTAINS(LOWER(title), r'\b(sec|securities and exchange commission|wells notice|subpoena|probe|investigation|enforcement|charged|settlement|fined|sanction|finra|regulatory|compliance|fraud|violation)\b')
            THEN 'SEC_INVESTIGATION'

        -- Executive departures
        WHEN REGEXP_CONTAINS(LOWER(title), r'\b(ceo|cfo|coo|president|chair|founder|chief|executive)\b')
         AND REGEXP_CONTAINS(LOWER(title), r'\b(resign|resigns|resigned|steps down|stepping down|departure|leaves|leaving|fired|terminated|exit|retires|retiring)\b')
            THEN 'EXEC_DEPARTURE'

        -- Layoffs / downsizing
        WHEN REGEXP_CONTAINS(LOWER(title), r'\b(layoff|layoffs|job cuts|downsizing|restructuring|workforce reduction)\b')
            THEN 'LAYOFFS'

        ELSE NULL
    END AS event_type
FROM news_with_firms
WHERE article_date IS NOT NULL;

-- Check what we classified
SELECT 
    event_type,
    COUNT(*) as article_count,
    COUNT(DISTINCT firm_crd_id) as firms_affected
FROM firm_event_candidates
GROUP BY event_type
ORDER BY article_count DESC;


-- ============================================================================
-- STEP 4: FIRST ARTICLE PER FIRM PER EVENT TYPE
-- ============================================================================
-- This is the "trigger" - when did we first see this event type for this firm?

CREATE TEMP TABLE firm_event_first_article AS
SELECT
    firm_crd_id,
    event_type,
    MIN(article_date) AS first_article_date,
    COUNT(*) AS total_articles_this_type,
    ARRAY_AGG(STRUCT(article_id, title, source_url, article_date)
              ORDER BY article_date ASC LIMIT 1)[OFFSET(0)] AS first_article_details
FROM firm_event_candidates
WHERE event_type IS NOT NULL
GROUP BY firm_crd_id, event_type;

-- Summary of first events
SELECT 
    event_type,
    COUNT(*) as n_firms_with_first_event,
    MIN(first_article_date) as earliest_event,
    MAX(first_article_date) as latest_event
FROM firm_event_first_article
GROUP BY event_type
ORDER BY n_firms_with_first_event DESC;


-- ============================================================================
-- STEP 5: COMPUTE EXODUS METRICS (Pre vs Post Event)
-- ============================================================================
-- For each event, measure:
-- - Headcount at event date
-- - Departures in 0-30, 31-60, 61-90 days after
-- - Baseline departures in prior 180 days

CREATE TEMP TABLE firm_event_exodus_metrics AS
WITH events AS (
    SELECT
        firm_crd_id,
        event_type,
        first_article_date AS event_date
    FROM firm_event_first_article
),

emp AS (
    SELECT
        RIA_CONTACT_CRD_ID AS contact_crd_id,
        SAFE_CAST(PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) AS firm_crd_id,
        PREVIOUS_REGISTRATION_COMPANY_START_DATE AS start_date,
        PREVIOUS_REGISTRATION_COMPANY_END_DATE AS end_date
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_CRD_ID IS NOT NULL
),

-- Count active headcount at event date
headcount AS (
    SELECT
        e.firm_crd_id,
        e.event_type,
        e.event_date,
        COUNT(DISTINCT emp.contact_crd_id) AS headcount_at_event
    FROM events e
    JOIN emp
        ON emp.firm_crd_id = e.firm_crd_id
       AND emp.start_date <= e.event_date
       AND (emp.end_date IS NULL OR emp.end_date >= e.event_date)
    GROUP BY 1, 2, 3
),

-- Count departures in various windows
departures AS (
    SELECT
        e.firm_crd_id,
        e.event_type,
        e.event_date,

        -- Post-event departures (0-30 days)
        COUNT(DISTINCT IF(
            emp.end_date > e.event_date 
            AND emp.end_date <= DATE_ADD(e.event_date, INTERVAL 30 DAY),
            emp.contact_crd_id, NULL
        )) AS dep_0_30,

        -- Post-event departures (31-60 days)
        COUNT(DISTINCT IF(
            emp.end_date > DATE_ADD(e.event_date, INTERVAL 30 DAY)
            AND emp.end_date <= DATE_ADD(e.event_date, INTERVAL 60 DAY),
            emp.contact_crd_id, NULL
        )) AS dep_31_60,

        -- Post-event departures (61-90 days)
        COUNT(DISTINCT IF(
            emp.end_date > DATE_ADD(e.event_date, INTERVAL 60 DAY)
            AND emp.end_date <= DATE_ADD(e.event_date, INTERVAL 90 DAY),
            emp.contact_crd_id, NULL
        )) AS dep_61_90,

        -- Baseline: departures in prior 180 days
        COUNT(DISTINCT IF(
            emp.end_date > DATE_SUB(e.event_date, INTERVAL 180 DAY)
            AND emp.end_date <= e.event_date,
            emp.contact_crd_id, NULL
        )) AS dep_prev_180

    FROM events e
    JOIN emp
        ON emp.firm_crd_id = e.firm_crd_id
    GROUP BY 1, 2, 3
)

SELECT
    d.firm_crd_id,
    d.event_type,
    d.event_date,
    h.headcount_at_event,

    -- Raw departure counts
    d.dep_0_30,
    d.dep_31_60,
    d.dep_61_90,
    d.dep_prev_180,

    -- Expected departures based on baseline (180 days / 6 = expected per 30-day period)
    SAFE_DIVIDE(d.dep_prev_180, 6.0) AS expected_dep_30d_from_baseline,

    -- Uplift: actual vs expected
    (d.dep_0_30 - SAFE_DIVIDE(d.dep_prev_180, 6.0)) AS uplift_dep_0_30_abs,

    -- Departure rates (as % of headcount)
    SAFE_DIVIDE(d.dep_0_30, h.headcount_at_event) * 100 AS dep_rate_0_30_pct,
    SAFE_DIVIDE(SAFE_DIVIDE(d.dep_prev_180, 6.0), h.headcount_at_event) * 100 AS baseline_rate_30d_pct,

    -- Rate uplift (percentage points)
    (SAFE_DIVIDE(d.dep_0_30, h.headcount_at_event) - 
     SAFE_DIVIDE(SAFE_DIVIDE(d.dep_prev_180, 6.0), h.headcount_at_event)) * 100 AS uplift_rate_0_30_pp

FROM departures d
LEFT JOIN headcount h
    USING (firm_crd_id, event_type, event_date);


-- ============================================================================
-- STEP 6: FEASIBILITY SUMMARY - DO EVENTS PREDICT EXODUS?
-- ============================================================================
-- This is the key output - shows if event types correlate with departures

SELECT
    event_type,
    
    -- Sample size
    COUNT(*) AS n_events,
    SUM(IF(headcount_at_event >= 5, 1, 0)) AS n_events_min_5_reps,
    
    -- Headcount context
    AVG(headcount_at_event) AS avg_headcount,
    APPROX_QUANTILES(headcount_at_event, 4)[OFFSET(2)] AS median_headcount,
    
    -- Average absolute uplift (# more departures than expected)
    AVG(uplift_dep_0_30_abs) AS avg_uplift_dep_0_30,
    APPROX_QUANTILES(uplift_dep_0_30_abs, 4)[OFFSET(2)] AS median_uplift_dep_0_30,
    
    -- Average rate uplift (percentage points above baseline)
    AVG(uplift_rate_0_30_pp) AS avg_uplift_rate_pp,
    APPROX_QUANTILES(uplift_rate_0_30_pp, 4)[OFFSET(2)] AS median_uplift_rate_pp,
    
    -- % of events that showed elevated departures
    AVG(IF(uplift_dep_0_30_abs > 0, 1, 0)) * 100 AS pct_events_with_elevated_departures,
    
    -- Effect size for "big" events (2+ more departures than expected)
    AVG(IF(uplift_dep_0_30_abs >= 2, 1, 0)) * 100 AS pct_events_2plus_extra_departures

FROM firm_event_exodus_metrics
WHERE headcount_at_event IS NOT NULL
  AND headcount_at_event >= 5  -- Exclude tiny firms for cleaner signal
GROUP BY event_type
ORDER BY n_events DESC;


-- ============================================================================
-- STEP 7: DETAILED EVENT EXAMPLES (Top Shock Events)
-- ============================================================================
-- Show specific examples of high-impact events for validation

SELECT
    event_type,
    firm_crd_id,
    event_date,
    headcount_at_event,
    dep_0_30 AS departures_30d,
    ROUND(expected_dep_30d_from_baseline, 1) AS expected_30d,
    ROUND(uplift_dep_0_30_abs, 1) AS extra_departures,
    ROUND(uplift_rate_0_30_pp, 2) AS uplift_pct_points
FROM firm_event_exodus_metrics
WHERE headcount_at_event >= 10
  AND uplift_dep_0_30_abs >= 3  -- At least 3 extra departures
ORDER BY uplift_dep_0_30_abs DESC
LIMIT 50;


-- ============================================================================
-- STEP 8: JOIN TO YOUR MQL OUTCOMES (If feasible)
-- ============================================================================
-- This would connect the analysis to your actual conversion data
-- Uncomment and adjust if you want to measure impact on contacting→MQL

/*
WITH event_firms AS (
    SELECT DISTINCT 
        firm_crd_id,
        event_type,
        first_article_date as event_date
    FROM firm_event_first_article
    WHERE event_type IN ('MA', 'SEC_INVESTIGATION', 'EXEC_DEPARTURE')
),

leads_with_event_context AS (
    SELECT 
        l.lead_id,
        l.advisor_crd,
        l.contacted_date,
        l.target,
        ef.event_type,
        ef.event_date,
        DATE_DIFF(l.contacted_date, ef.event_date, DAY) AS days_since_event
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON l.advisor_crd = c.RIA_CONTACT_CRD_ID
    LEFT JOIN event_firms ef
        ON SAFE_CAST(c.PRIMARY_FIRM AS INT64) = ef.firm_crd_id
       AND l.contacted_date BETWEEN ef.event_date AND DATE_ADD(ef.event_date, INTERVAL 90 DAY)
)

SELECT
    CASE 
        WHEN event_type IS NOT NULL THEN CONCAT('Event: ', event_type)
        ELSE 'No Recent Event'
    END AS event_context,
    COUNT(*) AS n_leads,
    SUM(target) AS conversions,
    AVG(target) * 100 AS conversion_rate_pct,
    AVG(target) / (SELECT AVG(target) FROM leads_with_event_context) AS lift_vs_baseline
FROM leads_with_event_context
GROUP BY 1
ORDER BY conversion_rate_pct DESC;
*/


-- ============================================================================
-- INTERPRETATION GUIDE
-- ============================================================================
/*
WHAT TO LOOK FOR IN STEP 6 RESULTS:

✅ FEASIBILITY CONFIRMED if:
   - median_uplift_dep_0_30 > 0 for at least one event type
   - pct_events_with_elevated_departures > 50% for any event type
   - n_events is sufficient for stability (ideally 50+)

📊 EFFECT SIZE INTERPRETATION:
   - avg_uplift_rate_pp = 2.0 means "2 percentage points more departures"
     (e.g., 5% baseline → 7% after event = significant)
   - pct_events_2plus_extra_departures > 30% is a strong signal

🎯 ACTIONABLE THRESHOLDS:
   If SEC_INVESTIGATION shows median_uplift_rate_pp > 1.0:
   → Worth building a "Firm Shock Score" for this event type
   
   If EXEC_DEPARTURE shows high variance but median = 0:
   → May need better severity classification (LLM step)

⚠️ CAVEATS:
   - Small firms (< 5 reps) create noisy percentages
   - Some news may be post-hoc (reported after departures started)
   - Need to verify news timestamp field is reliable
*/