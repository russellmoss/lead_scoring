-- ============================================================================
-- COMBINED HIGH-VALUE WEALTH TITLES ANALYSIS
-- Purpose: Test if grouping multiple high-performing "Wealth" titles together
--          creates enough volume and signal for a viable tier boost
--
-- Titles to combine (all showed 4x+ lift individually):
--   - "Wealth Manager" variants (6.99% conversion, 4.04x)
--   - "Director, Wealth Advisor" (7.55%, 4.51x)
--   - "Senior Vice-President, Wealth Advisor" (7.46%, 4.46x)
--   - "Senior Wealth Advisor" (3.80%, 2.27x) 
--   - "Founder & Wealth Advisor" (4.82%, 2.88x)
--   - Other ownership + wealth combinations
-- ============================================================================

-- ============================================================================
-- QUERY 1: Define and Test the Combined "High-Value Wealth Title" Category
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
title_classification AS (
    SELECT 
        al.lead_id,
        al.converted,
        c.TITLE_NAME,
        -- HIGH-VALUE WEALTH TITLES (combined category)
        -- Includes ownership signals (Founder, Director, Principal, Partner, SVP) + Wealth
        CASE WHEN (
            -- Wealth Manager variants (exclude "Wealth Management Advisor" = wirehouse)
            (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSISTANT%')
            -- Director + Wealth
            OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
            -- Senior VP + Wealth (but NOT "SVP, Wealth Management Advisor")
            OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR (UPPER(c.TITLE_NAME) LIKE '%SVP%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            -- Senior Wealth Advisor
            OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
            -- Founder + Wealth
            OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%FOUNDER%'
            -- Principal + Wealth
            OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRINCIPAL%'
            -- Partner + Wealth Manager/Advisor
            OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            -- President + Wealth
            OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRESIDENT%'
            -- Managing Director + Wealth
            OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
        ) THEN 1 ELSE 0 END as is_high_value_wealth_title,
        
        -- For comparison: the narrow "Wealth Manager only" definition
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
        ) THEN 1 ELSE 0 END as is_wealth_manager_only
        
    FROM all_leads al
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
),
baseline AS (
    SELECT SUM(converted) * 100.0 / COUNT(*) as baseline_rate FROM title_classification
)
SELECT 
    'HIGH-VALUE WEALTH TITLES (Combined)' as category,
    SUM(is_high_value_wealth_title) as leads,
    SUM(CASE WHEN is_high_value_wealth_title = 1 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN is_high_value_wealth_title = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(is_high_value_wealth_title), 0), 2) as conversion_rate_pct,
    ROUND(SUM(CASE WHEN is_high_value_wealth_title = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(is_high_value_wealth_title), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM title_classification CROSS JOIN baseline b
GROUP BY b.baseline_rate

UNION ALL

SELECT 
    'Wealth Manager Only (narrow)' as category,
    SUM(is_wealth_manager_only) as leads,
    SUM(CASE WHEN is_wealth_manager_only = 1 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN is_wealth_manager_only = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(is_wealth_manager_only), 0), 2) as conversion_rate_pct,
    ROUND(SUM(CASE WHEN is_wealth_manager_only = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(is_wealth_manager_only), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM title_classification CROSS JOIN baseline b
GROUP BY b.baseline_rate

UNION ALL

SELECT 
    'All Other Titles' as category,
    SUM(CASE WHEN is_high_value_wealth_title = 0 THEN 1 ELSE 0 END) as leads,
    SUM(CASE WHEN is_high_value_wealth_title = 0 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN is_high_value_wealth_title = 0 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(CASE WHEN is_high_value_wealth_title = 0 THEN 1 ELSE 0 END), 0), 2) as conversion_rate_pct,
    ROUND(SUM(CASE WHEN is_high_value_wealth_title = 0 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(CASE WHEN is_high_value_wealth_title = 0 THEN 1 ELSE 0 END), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM title_classification CROSS JOIN baseline b
GROUP BY b.baseline_rate

ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 2: What specific titles are captured by this combined definition?
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
baseline AS (
    SELECT SUM(converted) * 100.0 / COUNT(*) as baseline_rate FROM all_leads
)
SELECT 
    c.TITLE_NAME,
    COUNT(*) as leads,
    SUM(al.converted) as conversions,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = c.RIA_CONTACT_CRD_ID
CROSS JOIN baseline b
WHERE (
    -- Same definition as above
    (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
     AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
     AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
     AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSISTANT%')
    OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
    OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
    OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%FOUNDER%'
    OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRINCIPAL%'
    OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRESIDENT%'
    OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
)
GROUP BY c.TITLE_NAME, b.baseline_rate
HAVING COUNT(*) >= 10
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 3: THE KEY TEST - Combined titles BY EXISTING TIER
-- Does the combined category show up in Tier 1? Is it additive?
-- ============================================================================
WITH scored_leads AS (
    SELECT 
        ls.lead_id,
        ls.advisor_crd,
        ls.score_tier,
        ls.converted,
        c.TITLE_NAME,
        CASE WHEN (
            (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSISTANT%')
            OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
            OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%FOUNDER%'
            OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRINCIPAL%'
            OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRESIDENT%'
            OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
        ) THEN 1 ELSE 0 END as is_high_value_wealth_title
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3` ls
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(ls.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    WHERE ls.converted IS NOT NULL
)
SELECT 
    score_tier,
    is_high_value_wealth_title as has_hv_wealth_title,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM scored_leads
GROUP BY score_tier, is_high_value_wealth_title
HAVING COUNT(*) >= 5  -- Lower threshold to see if ANY overlap exists
ORDER BY score_tier, is_high_value_wealth_title DESC;

-- ============================================================================
-- QUERY 4: Prime Mover Criteria + High-Value Wealth Title Simulation
-- Would this work as a TIER_1C?
-- ============================================================================
WITH scored_leads AS (
    SELECT 
        ls.lead_id,
        ls.advisor_crd,
        ls.score_tier,
        ls.converted,
        ls.current_firm_tenure_months,
        ls.industry_tenure_months,
        ls.firm_net_change_12mo,
        ls.firm_rep_count_at_contact,
        c.TITLE_NAME,
        c.CONTACT_BIO,
        c.REP_LICENSES,
        -- Existing boosts
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' 
             OR c.CONTACT_BIO LIKE '%Certified Financial Planner%'
             OR c.TITLE_NAME LIKE '%CFP%'
             THEN 1 ELSE 0 END as has_cfp,
        CASE WHEN (c.REP_LICENSES LIKE '%Series 65%' OR c.REP_LICENSES LIKE '%Series 66%')
             AND c.REP_LICENSES NOT LIKE '%Series 7%'
             THEN 1 ELSE 0 END as has_series_65_only,
        -- HIGH-VALUE WEALTH TITLE (combined)
        CASE WHEN (
            (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSISTANT%')
            OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
            OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%FOUNDER%'
            OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRINCIPAL%'
            OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRESIDENT%'
            OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
        ) THEN 1 ELSE 0 END as is_high_value_wealth_title
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3` ls
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(ls.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    WHERE ls.converted IS NOT NULL
),
tier1_criteria AS (
    SELECT 
        *,
        -- Replicate Tier 1 criteria (looser version to catch more)
        CASE WHEN (
            current_firm_tenure_months BETWEEN 12 AND 48  -- 1-4 years
            AND industry_tenure_months >= 60  -- 5+ years (removed upper bound)
            AND firm_net_change_12mo < 0  -- Bleeding
        ) THEN 1 ELSE 0 END as meets_prime_mover_criteria
    FROM scored_leads
),
proposed_tiers AS (
    SELECT 
        *,
        CASE 
            WHEN meets_prime_mover_criteria = 1 AND has_cfp = 1 THEN 'TIER_1A_CFP'
            WHEN meets_prime_mover_criteria = 1 AND has_series_65_only = 1 THEN 'TIER_1B_SERIES65'
            WHEN meets_prime_mover_criteria = 1 AND is_high_value_wealth_title = 1 THEN 'TIER_1C_HV_WEALTH'
            WHEN meets_prime_mover_criteria = 1 THEN 'TIER_1_PRIME_MOVER'
            WHEN is_high_value_wealth_title = 1 THEN 'HV_WEALTH_NOT_PRIME_MOVER'
            ELSE 'OTHER_TIERS'
        END as proposed_tier
    FROM tier1_criteria
)
SELECT 
    proposed_tier,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0) / 3.82, 2) as lift_vs_baseline
FROM proposed_tiers
GROUP BY proposed_tier
HAVING COUNT(*) >= 3  -- Very low threshold to see any overlap
ORDER BY 
    CASE proposed_tier
        WHEN 'TIER_1A_CFP' THEN 1
        WHEN 'TIER_1B_SERIES65' THEN 2
        WHEN 'TIER_1C_HV_WEALTH' THEN 3
        WHEN 'TIER_1_PRIME_MOVER' THEN 4
        WHEN 'HV_WEALTH_NOT_PRIME_MOVER' THEN 5
        ELSE 6
    END;

-- ============================================================================
-- QUERY 5: What if we BROADEN Tier 1 criteria for HV Wealth titles?
-- Maybe these advisors have different tenure/experience patterns
-- ============================================================================
WITH scored_leads AS (
    SELECT 
        ls.lead_id,
        ls.advisor_crd,
        ls.converted,
        ls.current_firm_tenure_months,
        ls.industry_tenure_months,
        ls.firm_net_change_12mo,
        ls.firm_rep_count_at_contact,
        c.TITLE_NAME,
        CASE WHEN (
            (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%')
            OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
            OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
            OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
            OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
        ) THEN 1 ELSE 0 END as is_high_value_wealth_title
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3` ls
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(ls.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    WHERE ls.converted IS NOT NULL
)
SELECT 
    -- Tenure buckets
    CASE 
        WHEN current_firm_tenure_months < 12 THEN '< 1 year'
        WHEN current_firm_tenure_months BETWEEN 12 AND 24 THEN '1-2 years'
        WHEN current_firm_tenure_months BETWEEN 25 AND 48 THEN '2-4 years'
        WHEN current_firm_tenure_months BETWEEN 49 AND 96 THEN '4-8 years'
        ELSE '8+ years'
    END as tenure_bucket,
    -- Firm bleeding status
    CASE 
        WHEN firm_net_change_12mo < -10 THEN 'Heavy Bleeder (<-10)'
        WHEN firm_net_change_12mo < 0 THEN 'Moderate Bleeder (-1 to -10)'
        WHEN firm_net_change_12mo = 0 THEN 'Stable'
        ELSE 'Growing'
    END as firm_status,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM scored_leads
WHERE is_high_value_wealth_title = 1
GROUP BY 1, 2
HAVING COUNT(*) >= 10
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 6: Population size of combined HV Wealth titles in FINTRX
-- ============================================================================
SELECT 
    'High-Value Wealth Titles (Combined)' as category,
    COUNT(*) as contacts_in_fintrx,
    (SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`) as total_contacts,
    ROUND(COUNT(*) * 100.0 / 
          (SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`), 3) as pct_of_population
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
WHERE (
    (UPPER(TITLE_NAME) LIKE '%WEALTH MANAGER%' 
     AND UPPER(TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
     AND UPPER(TITLE_NAME) NOT LIKE '%ASSOCIATE%'
     AND UPPER(TITLE_NAME) NOT LIKE '%ASSISTANT%')
    OR UPPER(TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
    OR UPPER(TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
    OR (UPPER(TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
        AND UPPER(TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR UPPER(TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
    OR UPPER(TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
    OR UPPER(TITLE_NAME) LIKE '%WEALTH%FOUNDER%'
    OR UPPER(TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
    OR UPPER(TITLE_NAME) LIKE '%WEALTH%PRINCIPAL%'
    OR (UPPER(TITLE_NAME) LIKE '%PARTNER%WEALTH%'
        AND UPPER(TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR UPPER(TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
    OR UPPER(TITLE_NAME) LIKE '%WEALTH%PRESIDENT%'
    OR (UPPER(TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
        AND UPPER(TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
);

-- ============================================================================
-- QUERY 7: Impact on January 2026 List
-- How many HV Wealth title leads are in the current list?
-- ============================================================================
WITH jan_leads AS (
    SELECT 
        jl.advisor_crd,
        jl.score_tier,
        jl.expected_rate_pct,
        c.TITLE_NAME,
        CASE WHEN (
            (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%')
            OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
            OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
            OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
            OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
        ) THEN 1 ELSE 0 END as is_high_value_wealth_title
    FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(jl.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
)
SELECT 
    score_tier,
    SUM(is_high_value_wealth_title) as hv_wealth_count,
    COUNT(*) as tier_total,
    ROUND(SUM(is_high_value_wealth_title) * 100.0 / COUNT(*), 2) as pct_hv_wealth
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
-- QUERY 8: Which specific HV Wealth titles are in the January list?
-- ============================================================================
SELECT 
    c.TITLE_NAME,
    jl.score_tier,
    COUNT(*) as count_in_list
FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON jl.advisor_crd = c.RIA_CONTACT_CRD_ID
WHERE (
    (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
     AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
     AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%')
    OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
    OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
    OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
    OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
    OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
)
GROUP BY c.TITLE_NAME, jl.score_tier
ORDER BY count_in_list DESC;

-- ============================================================================
-- QUERY 9: Alternative approach - HV Wealth as a STANDALONE tier
-- What if instead of boosting Tier 1, we created a separate tier?
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
        c.TITLE_NAME,
        CASE WHEN (
            (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%')
            OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
            OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
            OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
        ) THEN 1 ELSE 0 END as is_high_value_wealth_title,
        -- Add firm bleeding signal
        eh.firm_net_change_12mo,
        -- Add mobility signal (num prior firms)
        eh.num_prior_firms
    FROM all_leads al
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    LEFT JOIN (
        SELECT DISTINCT advisor_crd, firm_net_change_12mo, num_prior_firms
        FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
    ) eh ON al.crd = eh.advisor_crd
)
SELECT 
    CASE 
        WHEN is_high_value_wealth_title = 1 AND firm_net_change_12mo < 0 
            THEN 'HV Wealth + Bleeding Firm'
        WHEN is_high_value_wealth_title = 1 AND num_prior_firms >= 3 
            THEN 'HV Wealth + Career Mover (3+ firms)'
        WHEN is_high_value_wealth_title = 1 
            THEN 'HV Wealth Only'
        ELSE 'No HV Wealth Title'
    END as segment,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0) / 1.73, 2) as lift_vs_baseline
FROM enriched
GROUP BY 1
HAVING COUNT(*) >= 20
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 10: Compare "High-Value Wealth" to existing top-performing segments
-- Where would this rank if it were a tier?
-- ============================================================================
WITH scored_leads AS (
    SELECT 
        ls.lead_id,
        ls.advisor_crd,
        ls.score_tier,
        ls.converted,
        c.TITLE_NAME,
        CASE WHEN (
            (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
             AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%')
            OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
            OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
            OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
            OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
                AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
        ) THEN 1 ELSE 0 END as is_high_value_wealth_title
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3` ls
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(ls.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    WHERE ls.converted IS NOT NULL
)
-- Existing tier performance
SELECT 
    score_tier as segment,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM scored_leads
GROUP BY score_tier

UNION ALL

-- High-Value Wealth Title (all, regardless of tier)
SELECT 
    'ALL_HV_WEALTH_TITLES' as segment,
    SUM(is_high_value_wealth_title) as leads,
    SUM(CASE WHEN is_high_value_wealth_title = 1 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN is_high_value_wealth_title = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(is_high_value_wealth_title), 0), 2) as conversion_rate_pct
FROM scored_leads

ORDER BY conversion_rate_pct DESC;