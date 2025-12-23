-- ============================================================================
-- LICENSE ANALYSIS: Do Converted Leads Have Series 65 / Series 7?
-- Purpose: Determine if requiring Series 65 or Series 7 would exclude converters
-- ============================================================================

-- ============================================================================
-- QUERY 1: License distribution for ALL converted leads (MQL+)
-- ============================================================================
WITH converted_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        l.Status,
        l.CreatedDate,
        l.ConvertedDate
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity')
      AND l.CreatedDate >= '2022-01-01'  -- Last 3 years
),
license_data AS (
    SELECT 
        cl.lead_id,
        cl.crd,
        cl.Status,
        -- Check for Series 65 (REP_LICENSES is a JSON array string)
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' THEN 1 ELSE 0 END as has_series_65,
        -- Check for Series 7
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7,
        -- Check for Series 66 (combines 63 + 65 requirements)
        CASE WHEN c.REP_LICENSES LIKE '%Series 66%' THEN 1 ELSE 0 END as has_series_66,
        -- CFP for reference (from CONTACT_BIO or TITLE_NAME)
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' 
             OR c.CONTACT_BIO LIKE '%Certified Financial Planner%'
             OR c.TITLE_NAME LIKE '%CFP%'
             THEN 1 ELSE 0 END as has_cfp
    FROM converted_leads cl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON cl.crd = c.RIA_CONTACT_CRD_ID
)
SELECT 
    -- License combination breakdown
    CASE 
        WHEN has_series_65 = 1 AND has_series_7 = 1 THEN 'Both Series 65 + Series 7'
        WHEN has_series_65 = 1 AND has_series_7 = 0 THEN 'Series 65 Only'
        WHEN has_series_65 = 0 AND has_series_7 = 1 THEN 'Series 7 Only'
        WHEN has_series_66 = 1 THEN 'Series 66 (no 65/7)'
        ELSE 'Neither 65 nor 7'
    END as license_status,
    COUNT(*) as converted_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct_of_conversions
FROM license_data
GROUP BY 1
ORDER BY converted_count DESC;

-- ============================================================================
-- QUERY 2: Same analysis but with Series 66 counted as having 65
-- (Series 66 = Series 63 + Series 65 combined exam, so functionally = Series 65)
-- ============================================================================
WITH converted_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        l.Status
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity')
      AND l.CreatedDate >= '2022-01-01'
),
license_data AS (
    SELECT 
        cl.lead_id,
        cl.crd,
        -- Series 65 OR Series 66 (66 includes 65 content)
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' 
                  OR c.REP_LICENSES LIKE '%Series 66%'
             THEN 1 ELSE 0 END as has_65_or_66,
        -- Series 7
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7
    FROM converted_leads cl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON cl.crd = c.RIA_CONTACT_CRD_ID
)
SELECT 
    CASE 
        WHEN has_65_or_66 = 1 AND has_series_7 = 1 THEN 'Both (65/66) + Series 7'
        WHEN has_65_or_66 = 1 AND has_series_7 = 0 THEN 'Series 65/66 Only (Fee-Only RIA)'
        WHEN has_65_or_66 = 0 AND has_series_7 = 1 THEN 'Series 7 Only (Broker)'
        ELSE 'Neither - NO INVESTMENT LICENSE'
    END as license_status,
    COUNT(*) as converted_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct_of_conversions,
    CASE 
        WHEN has_65_or_66 = 1 OR has_series_7 = 1 THEN 'WOULD KEEP'
        ELSE 'WOULD EXCLUDE'
    END as filter_impact
FROM license_data
GROUP BY has_65_or_66, has_series_7
ORDER BY converted_count DESC;

-- ============================================================================
-- QUERY 3: What licenses do the "Neither" converters have?
-- (Are they insurance-only? Something else?)
-- ============================================================================
WITH converted_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        l.FirstName,
        l.LastName,
        l.Company
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.Status IN ('MQL', 'Qualified', 'Converted', 'Customer', 'Opportunity')
      AND l.CreatedDate >= '2022-01-01'
)
SELECT 
    cl.lead_id,
    cl.crd,
    cl.FirstName,
    cl.LastName,
    cl.Company,
    c.TITLE_NAME,
    c.REP_LICENSES,
    CASE WHEN c.REP_LICENSES LIKE '%Series 65%' THEN 1 ELSE 0 END as has_series_65,
    CASE WHEN c.REP_LICENSES LIKE '%Series 66%' THEN 1 ELSE 0 END as has_series_66,
    CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7,
    CASE WHEN c.REP_LICENSES LIKE '%Series 63%' THEN 1 ELSE 0 END as has_series_63,
    CASE WHEN c.CONTACT_BIO LIKE '%CFP%' OR c.CONTACT_BIO LIKE '%Certified Financial Planner%' OR c.TITLE_NAME LIKE '%CFP%' THEN 1 ELSE 0 END as has_cfp,
    CASE WHEN c.CONTACT_BIO LIKE '%CFA%' OR c.CONTACT_BIO LIKE '%Chartered Financial Analyst%' OR c.TITLE_NAME LIKE '%CFA%' THEN 1 ELSE 0 END as has_cfa
FROM converted_leads cl
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON cl.crd = c.RIA_CONTACT_CRD_ID
WHERE 
    (c.REP_LICENSES IS NULL OR c.REP_LICENSES NOT LIKE '%Series 65%')
    AND (c.REP_LICENSES IS NULL OR c.REP_LICENSES NOT LIKE '%Series 66%')
    AND (c.REP_LICENSES IS NULL OR c.REP_LICENSES NOT LIKE '%Series 7%')
ORDER BY cl.Company;

-- ============================================================================
-- QUERY 4: Conversion rate BY license type
-- (Do certain licenses convert better?)
-- ============================================================================
WITH all_contacted_leads AS (
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
license_data AS (
    SELECT 
        acl.lead_id,
        acl.converted,
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' 
                  OR c.REP_LICENSES LIKE '%Series 66%'
             THEN 1 ELSE 0 END as has_65_or_66,
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7
    FROM all_contacted_leads acl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON acl.crd = c.RIA_CONTACT_CRD_ID
),
baseline AS (
    SELECT SUM(converted) * 100.0 / COUNT(*) as baseline_rate
    FROM license_data
)
SELECT 
    CASE 
        WHEN has_65_or_66 = 1 AND has_series_7 = 1 THEN 'Both (65/66) + Series 7'
        WHEN has_65_or_66 = 1 AND has_series_7 = 0 THEN 'Series 65/66 Only'
        WHEN has_65_or_66 = 0 AND has_series_7 = 1 THEN 'Series 7 Only'
        ELSE 'Neither 65/66 nor 7'
    END as license_status,
    COUNT(*) as total_leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / COUNT(*), 2) as conversion_rate,
    ROUND(SUM(converted) * 100.0 / COUNT(*) / b.baseline_rate, 2) as lift_vs_baseline
FROM license_data
CROSS JOIN baseline b
GROUP BY has_65_or_66, has_series_7, b.baseline_rate
ORDER BY conversion_rate DESC;

-- ============================================================================
-- QUERY 5: How many leads in January 2026 list have NO investment license?
-- (Would be excluded if we required Series 65/66 OR Series 7)
-- ============================================================================
WITH jan_leads AS (
    SELECT 
        jl.advisor_crd,
        jl.first_name,
        jl.last_name,
        jl.firm_name,
        jl.score_tier,
        c.TITLE_NAME,
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' 
                  OR c.REP_LICENSES LIKE '%Series 66%'
             THEN 1 ELSE 0 END as has_65_or_66,
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7
    FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON jl.advisor_crd = c.RIA_CONTACT_CRD_ID
)
SELECT 
    score_tier,
    COUNT(*) as total_in_tier,
    SUM(CASE WHEN has_65_or_66 = 1 OR has_series_7 = 1 THEN 1 ELSE 0 END) as has_investment_license,
    SUM(CASE WHEN has_65_or_66 = 0 AND has_series_7 = 0 THEN 1 ELSE 0 END) as no_investment_license,
    ROUND(SUM(CASE WHEN has_65_or_66 = 0 AND has_series_7 = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_no_license
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
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 7
    END;

-- ============================================================================
-- QUERY 6: What titles do the "no license" people in January list have?
-- (Are they the same compliance/operations people?)
-- ============================================================================
WITH jan_leads AS (
    SELECT 
        jl.advisor_crd,
        jl.score_tier,
        c.TITLE_NAME,
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' 
                  OR c.REP_LICENSES LIKE '%Series 66%'
             THEN 1 ELSE 0 END as has_65_or_66,
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7
    FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON jl.advisor_crd = c.RIA_CONTACT_CRD_ID
)
SELECT 
    TITLE_NAME,
    COUNT(*) as count_no_license
FROM jan_leads
WHERE has_65_or_66 = 0 AND has_series_7 = 0
GROUP BY TITLE_NAME
ORDER BY count_no_license DESC
LIMIT 30;

-- ============================================================================
-- QUERY 7: Overlap analysis - Title exclusions vs License requirement
-- How much overlap is there between the two filtering approaches?
-- ============================================================================
WITH jan_leads AS (
    SELECT 
        jl.advisor_crd,
        c.TITLE_NAME,
        -- License check
        CASE WHEN (c.REP_LICENSES LIKE '%Series 65%' 
                   OR c.REP_LICENSES LIKE '%Series 66%'
                   OR c.REP_LICENSES LIKE '%Series 7%')
             THEN 1 ELSE 0 END as has_investment_license,
        -- Title exclusion check (same logic as Cursor prompt)
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
    FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON jl.advisor_crd = c.RIA_CONTACT_CRD_ID
)
SELECT 
    CASE 
        WHEN has_investment_license = 1 AND is_excluded_title = 0 THEN 'KEEP: Has license + Good title'
        WHEN has_investment_license = 1 AND is_excluded_title = 1 THEN 'CONFLICT: Has license but Bad title'
        WHEN has_investment_license = 0 AND is_excluded_title = 1 THEN 'EXCLUDE BOTH: No license + Bad title'
        WHEN has_investment_license = 0 AND is_excluded_title = 0 THEN 'LICENSE ONLY: No license but Good title'
    END as filter_scenario,
    COUNT(*) as lead_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct_of_total
FROM jan_leads
GROUP BY 1
ORDER BY lead_count DESC;
