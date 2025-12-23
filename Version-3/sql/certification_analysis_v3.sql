-- Certification Analysis on Historical Conversion Data
-- Analyzes the impact of professional certifications (CFP, CFA) and Series licenses on lead conversion
-- Uses CONTACT_BIO and TITLE_NAME for certifications (not REP_LICENSES which only has Series licenses)
-- Target: Conversion to MQL (Stage_Entered_Call_Scheduled__c) within 30 days of contact

WITH cert_features AS (
    SELECT 
        l.Id as lead_id,
        
        -- DEFINE TARGET: Lead converted to MQL within 30 days
        CASE 
            WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL 
                 AND DATE_DIFF(
                     DATE(l.Stage_Entered_Call_Scheduled__c), 
                     DATE(l.Stage_Entered_Contacting__c), 
                     DAY
                 ) <= 30 
            THEN 1 
            ELSE 0 
        END as target,
        
        -- Current V3.2 tier
        t.score_tier,
        
        -- Series licenses from REP_LICENSES (regulatory only - does NOT contain certifications)
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' 
             AND c.REP_LICENSES NOT LIKE '%Series 7%' 
             THEN 1 ELSE 0 END as has_series_65_only,
        
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' 
             THEN 1 ELSE 0 END as has_series_7,
        
        -- Professional certifications from CONTACT_BIO (primary source)
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' 
             OR c.CONTACT_BIO LIKE '%Certified Financial Planner%'
             THEN 1 ELSE 0 END as has_cfp,
        
        CASE WHEN c.CONTACT_BIO LIKE '%CFA%' 
             OR c.CONTACT_BIO LIKE '%Chartered Financial Analyst%'
             OR c.CONTACT_BIO LIKE '%CFA charterholder%'
             THEN 1 ELSE 0 END as has_cfa,
        
        -- Also check TITLE_NAME for certifications (secondary source)
        CASE WHEN c.TITLE_NAME LIKE '%CFP%' 
             THEN 1 ELSE 0 END as has_cfp_title,
        
        CASE WHEN c.TITLE_NAME LIKE '%CFA%' 
             THEN 1 ELSE 0 END as has_cfa_title
        
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025` t
        ON l.Id = t.lead_id
    WHERE l.Stage_Entered_Contacting__c IS NOT NULL
      AND l.FA_CRD__c IS NOT NULL
      -- Only mature leads (30+ days since contact to observe outcome)
      AND DATE_DIFF(CURRENT_DATE(), DATE(l.Stage_Entered_Contacting__c), DAY) >= 30
),

-- Combine CFP/CFA from both sources (CONTACT_BIO and TITLE_NAME)
cert_combined AS (
    SELECT 
        *,
        CASE WHEN has_cfp = 1 OR has_cfp_title = 1 THEN 1 ELSE 0 END as has_cfp_any,
        CASE WHEN has_cfa = 1 OR has_cfa_title = 1 THEN 1 ELSE 0 END as has_cfa_any
    FROM cert_features
)

SELECT
    -- Overall baseline
    'All Contacted Leads' as segment,
    COUNT(*) as leads,
    SUM(target) as conversions,
    ROUND(AVG(target) * 100, 2) as conversion_pct,
    'Baseline' as note
FROM cert_combined

UNION ALL

-- CFP holders (from CONTACT_BIO or TITLE_NAME)
SELECT
    'Has CFP (any source)',
    COUNT(*),
    SUM(target),
    ROUND(AVG(target) * 100, 2),
    CASE 
        WHEN ROUND(AVG(target) * 100, 2) > (SELECT ROUND(AVG(target) * 100, 2) FROM cert_combined) 
        THEN '✅ Higher than baseline'
        ELSE '⬇️ Lower than baseline'
    END
FROM cert_combined
WHERE has_cfp_any = 1

UNION ALL

-- Series 65 only (pure RIA)
SELECT
    'Series 65 Only (No Series 7)',
    COUNT(*),
    SUM(target),
    ROUND(AVG(target) * 100, 2),
    CASE 
        WHEN ROUND(AVG(target) * 100, 2) > (SELECT ROUND(AVG(target) * 100, 2) FROM cert_combined) 
        THEN '✅ Higher than baseline'
        ELSE '⬇️ Lower than baseline'
    END
FROM cert_combined
WHERE has_series_65_only = 1

UNION ALL

-- CFA holders (from CONTACT_BIO or TITLE_NAME)
SELECT
    'Has CFA (any source)',
    COUNT(*),
    SUM(target),
    ROUND(AVG(target) * 100, 2),
    CASE 
        WHEN ROUND(AVG(target) * 100, 2) < (SELECT ROUND(AVG(target) * 100, 2) FROM cert_combined) 
        THEN '⚠️ Negative signal - consider excluding'
        ELSE 'Neutral or positive'
    END
FROM cert_combined
WHERE has_cfa_any = 1

UNION ALL

-- Series 7 (BD-registered)
SELECT
    'Has Series 7 (BD-registered)',
    COUNT(*),
    SUM(target),
    ROUND(AVG(target) * 100, 2),
    'Dual-registered signal'
FROM cert_combined
WHERE has_series_7 = 1

UNION ALL

-- Tier 1 + CFP
SELECT
    'Tier 1 + CFP',
    COUNT(*),
    SUM(target),
    ROUND(AVG(target) * 100, 2),
    'Does CFP boost Tier 1?'
FROM cert_combined
WHERE score_tier = 'TIER_1_PRIME_MOVER'
  AND has_cfp_any = 1

UNION ALL

-- Tier 1 WITHOUT CFP
SELECT
    'Tier 1 WITHOUT CFP',
    COUNT(*),
    SUM(target),
    ROUND(AVG(target) * 100, 2),
    'Tier 1 baseline'
FROM cert_combined
WHERE score_tier = 'TIER_1_PRIME_MOVER'
  AND has_cfp_any = 0

UNION ALL

-- Tier 1 + Series 65 only
SELECT
    'Tier 1 + Series 65 Only',
    COUNT(*),
    SUM(target),
    ROUND(AVG(target) * 100, 2),
    'Pure RIA signal in Tier 1'
FROM cert_combined
WHERE score_tier = 'TIER_1_PRIME_MOVER'
  AND has_series_65_only = 1

ORDER BY conversion_pct DESC;

