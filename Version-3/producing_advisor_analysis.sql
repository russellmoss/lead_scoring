-- ============================================================================
-- PRODUCING_ADVISOR ANALYSIS
-- Purpose: Determine if the PRODUCING_ADVISOR boolean from FINTRX can help
--          filter out non-advisors (compliance, operations, wholesalers, etc.)
-- 
-- Key Questions:
-- 1. What % of historical MQLs had PRODUCING_ADVISOR = TRUE?
-- 2. What's the conversion rate for TRUE vs FALSE/NULL?
-- 3. How does this overlap with our title exclusions?
-- 4. Should this be a required filter for lead list generation?
-- ============================================================================

-- ============================================================================
-- QUERY 1: Basic distribution of PRODUCING_ADVISOR in FINTRX
-- ============================================================================
SELECT 
    PRODUCING_ADVISOR,
    COUNT(*) as contact_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct_of_total
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
GROUP BY PRODUCING_ADVISOR
ORDER BY contact_count DESC;

-- ============================================================================
-- QUERY 2: PRODUCING_ADVISOR for ALL historical contacted leads
-- ============================================================================
WITH all_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        CASE WHEN l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity') 
             THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2022-01-01'
)
SELECT 
    c.PRODUCING_ADVISOR,
    COUNT(*) as total_leads,
    SUM(al.converted) as conversions,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0) / 1.73, 2) as lift_vs_baseline
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
GROUP BY c.PRODUCING_ADVISOR
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 3: PRODUCING_ADVISOR breakdown for MQLs only
-- ============================================================================
WITH mqls AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        l.Status
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity')
      AND l.CreatedDate >= '2022-01-01'
)
SELECT 
    c.PRODUCING_ADVISOR,
    COUNT(*) as mql_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct_of_mqls
FROM mqls m
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON m.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
GROUP BY c.PRODUCING_ADVISOR
ORDER BY mql_count DESC;

-- ============================================================================
-- QUERY 4: Overlap with Title Exclusions
-- Do our excluded titles have PRODUCING_ADVISOR = FALSE?
-- ============================================================================
WITH all_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        CASE WHEN l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity') 
             THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2022-01-01'
),
enriched AS (
    SELECT 
        al.lead_id,
        al.converted,
        c.PRODUCING_ADVISOR,
        c.TITLE_NAME,
        -- Our existing title exclusion logic
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTIONS ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%PARAPLANNER%'
            OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS%'
            OR UPPER(c.TITLE_NAME) LIKE '%FIRST VICE PRESIDENT%'
            OR UPPER(c.TITLE_NAME) LIKE '%WHOLESALER%'
            OR UPPER(c.TITLE_NAME) LIKE '%INTERNAL SALES%'
            OR UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE%'
        ) THEN 1 ELSE 0 END as is_excluded_title
    FROM all_leads al
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON al.crd = c.RIA_CONTACT_CRD_ID
)
SELECT 
    CASE 
        WHEN PRODUCING_ADVISOR = TRUE AND is_excluded_title = 0 THEN 'KEEP: Producing + Good Title'
        WHEN PRODUCING_ADVISOR = TRUE AND is_excluded_title = 1 THEN 'CONFLICT: Producing but Bad Title'
        WHEN PRODUCING_ADVISOR = FALSE AND is_excluded_title = 1 THEN 'EXCLUDE BOTH: Non-Producing + Bad Title'
        WHEN PRODUCING_ADVISOR = FALSE AND is_excluded_title = 0 THEN 'PRODUCING ONLY: Non-Producing + Good Title'
        WHEN PRODUCING_ADVISOR IS NULL AND is_excluded_title = 1 THEN 'NULL + Bad Title'
        WHEN PRODUCING_ADVISOR IS NULL AND is_excluded_title = 0 THEN 'NULL + Good Title'
        ELSE 'Other'
    END as filter_scenario,
    COUNT(*) as lead_count,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct_of_total
FROM enriched
GROUP BY 1
ORDER BY lead_count DESC;

-- ============================================================================
-- QUERY 5: What titles do NON-PRODUCING advisors have?
-- This tells us what PRODUCING_ADVISOR = FALSE catches
-- ============================================================================
WITH all_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        CASE WHEN l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity') 
             THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2022-01-01'
)
SELECT 
    c.TITLE_NAME,
    COUNT(*) as lead_count,
    SUM(al.converted) as conversions,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
WHERE c.PRODUCING_ADVISOR = FALSE
GROUP BY c.TITLE_NAME
ORDER BY lead_count DESC
LIMIT 30;

-- ============================================================================
-- QUERY 6: What titles do PRODUCING advisors have?
-- Sanity check - are these actual advisors?
-- ============================================================================
WITH all_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        CASE WHEN l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity') 
             THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2022-01-01'
)
SELECT 
    c.TITLE_NAME,
    COUNT(*) as lead_count,
    SUM(al.converted) as conversions,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
WHERE c.PRODUCING_ADVISOR = TRUE
GROUP BY c.TITLE_NAME
ORDER BY lead_count DESC
LIMIT 30;

-- ============================================================================
-- QUERY 7: PRODUCING_ADVISOR by TIER
-- Does this signal add value within existing tiers?
-- ============================================================================
WITH scored_leads AS (
    SELECT 
        ls.lead_id,
        ls.advisor_crd,
        ls.score_tier,
        ls.converted,
        c.PRODUCING_ADVISOR
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3` ls
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(ls.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    WHERE ls.converted IS NOT NULL
)
SELECT 
    score_tier,
    PRODUCING_ADVISOR,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM scored_leads
GROUP BY score_tier, PRODUCING_ADVISOR
HAVING COUNT(*) >= 10
ORDER BY score_tier, PRODUCING_ADVISOR DESC;

-- ============================================================================
-- QUERY 8: Impact on January 2026 List
-- How many leads would be affected by a PRODUCING_ADVISOR filter?
-- ============================================================================
WITH jan_leads AS (
    SELECT 
        jl.advisor_crd,
        jl.score_tier,
        c.PRODUCING_ADVISOR,
        c.TITLE_NAME
    FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(jl.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
)
SELECT 
    score_tier,
    SUM(CASE WHEN PRODUCING_ADVISOR = TRUE THEN 1 ELSE 0 END) as producing_count,
    SUM(CASE WHEN PRODUCING_ADVISOR = FALSE THEN 1 ELSE 0 END) as non_producing_count,
    SUM(CASE WHEN PRODUCING_ADVISOR IS NULL THEN 1 ELSE 0 END) as null_count,
    COUNT(*) as total,
    ROUND(SUM(CASE WHEN PRODUCING_ADVISOR = TRUE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_producing,
    ROUND(SUM(CASE WHEN PRODUCING_ADVISOR = FALSE THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_non_producing
FROM jan_leads
GROUP BY score_tier
ORDER BY 
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2
        WHEN 'TIER_1_PRIME_MOVER' THEN 3
        WHEN 'TIER_2_PROVEN_MOVER' THEN 4
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 5
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 6
    END;

-- ============================================================================
-- QUERY 9: What NON-PRODUCING leads are in January list?
-- These would be removed by a PRODUCING_ADVISOR filter
-- ============================================================================
SELECT 
    jl.advisor_crd,
    jl.first_name,
    jl.last_name,
    jl.firm_name,
    jl.score_tier,
    c.TITLE_NAME,
    c.PRODUCING_ADVISOR
FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON jl.advisor_crd = c.RIA_CONTACT_CRD_ID
WHERE c.PRODUCING_ADVISOR = FALSE
ORDER BY jl.score_tier
LIMIT 50;

-- ============================================================================
-- QUERY 10: Combined Filter Analysis
-- What if we use BOTH PRODUCING_ADVISOR AND Title Exclusions?
-- ============================================================================
WITH all_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        CASE WHEN l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity') 
             THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2022-01-01'
),
enriched AS (
    SELECT 
        al.lead_id,
        al.converted,
        c.PRODUCING_ADVISOR,
        c.TITLE_NAME,
        -- Title exclusion logic
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTIONS ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%PARAPLANNER%'
            OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS%'
            OR UPPER(c.TITLE_NAME) LIKE '%FIRST VICE PRESIDENT%'
            OR UPPER(c.TITLE_NAME) LIKE '%WHOLESALER%'
            OR UPPER(c.TITLE_NAME) LIKE '%INTERNAL SALES%'
            OR UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE%'
        ) THEN 1 ELSE 0 END as is_excluded_title
    FROM all_leads al
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON al.crd = c.RIA_CONTACT_CRD_ID
)
SELECT 
    'PRODUCING_ADVISOR = TRUE only' as filter_strategy,
    SUM(CASE WHEN PRODUCING_ADVISOR = TRUE THEN 1 ELSE 0 END) as leads_kept,
    SUM(CASE WHEN PRODUCING_ADVISOR = TRUE THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN PRODUCING_ADVISOR = TRUE THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(CASE WHEN PRODUCING_ADVISOR = TRUE THEN 1 ELSE 0 END), 0), 2) as conversion_rate
FROM enriched

UNION ALL

SELECT 
    'Title Exclusions only' as filter_strategy,
    SUM(CASE WHEN is_excluded_title = 0 THEN 1 ELSE 0 END) as leads_kept,
    SUM(CASE WHEN is_excluded_title = 0 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN is_excluded_title = 0 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(CASE WHEN is_excluded_title = 0 THEN 1 ELSE 0 END), 0), 2) as conversion_rate
FROM enriched

UNION ALL

SELECT 
    'BOTH Filters (PRODUCING + Title)' as filter_strategy,
    SUM(CASE WHEN PRODUCING_ADVISOR = TRUE AND is_excluded_title = 0 THEN 1 ELSE 0 END) as leads_kept,
    SUM(CASE WHEN PRODUCING_ADVISOR = TRUE AND is_excluded_title = 0 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN PRODUCING_ADVISOR = TRUE AND is_excluded_title = 0 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(CASE WHEN PRODUCING_ADVISOR = TRUE AND is_excluded_title = 0 THEN 1 ELSE 0 END), 0), 2) as conversion_rate
FROM enriched

UNION ALL

SELECT 
    'No Filters (baseline)' as filter_strategy,
    COUNT(*) as leads_kept,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate
FROM enriched

ORDER BY conversion_rate DESC;

-- ============================================================================
-- QUERY 11: Check for NULL PRODUCING_ADVISOR
-- Are NULLs problematic or just missing data?
-- ============================================================================
WITH all_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        CASE WHEN l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity') 
             THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2022-01-01'
)
SELECT 
    c.TITLE_NAME,
    COUNT(*) as lead_count,
    SUM(al.converted) as conversions,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
WHERE c.PRODUCING_ADVISOR IS NULL
GROUP BY c.TITLE_NAME
ORDER BY lead_count DESC
LIMIT 30;

-- ============================================================================
-- QUERY 12: Summary Statistics
-- Quick view of the potential impact
-- ============================================================================
WITH all_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        CASE WHEN l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity') 
             THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2022-01-01'
)
SELECT 
    'Total Leads Analyzed' as metric,
    COUNT(*) as value
FROM all_leads

UNION ALL

SELECT 
    'PRODUCING_ADVISOR = TRUE' as metric,
    COUNT(*) as value
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
WHERE c.PRODUCING_ADVISOR = TRUE

UNION ALL

SELECT 
    'PRODUCING_ADVISOR = FALSE' as metric,
    COUNT(*) as value
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
WHERE c.PRODUCING_ADVISOR = FALSE

UNION ALL

SELECT 
    'PRODUCING_ADVISOR IS NULL' as metric,
    COUNT(*) as value
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
WHERE c.PRODUCING_ADVISOR IS NULL

UNION ALL

SELECT 
    'MQLs with PRODUCING = TRUE' as metric,
    COUNT(*) as value
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
WHERE al.converted = 1 AND c.PRODUCING_ADVISOR = TRUE

UNION ALL

SELECT 
    'MQLs with PRODUCING = FALSE' as metric,
    COUNT(*) as value
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
WHERE al.converted = 1 AND c.PRODUCING_ADVISOR = FALSE;
