-- ============================================================================
-- WEALTH MANAGER BOOST ANALYSIS
-- Purpose: Determine if "Wealth Manager" title should be added as a tier boost
--          similar to how CFP and Series 65 boost Tier 1
-- 
-- Key Question: Does "Wealth Manager" title add predictive value ON TOP OF
--               existing tier criteria, or is it just correlated?
-- ============================================================================

-- ============================================================================
-- QUERY 1: Baseline - Wealth Manager conversion across ALL leads
-- Confirm the 4.18x lift finding from initial analysis
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
title_data AS (
    SELECT 
        al.lead_id,
        al.converted,
        c.TITLE_NAME,
        -- Wealth Manager variants (EXCLUDE "Wealth Management Advisor" which is wirehouse)
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSISTANT%'
        ) THEN 1 ELSE 0 END as is_wealth_manager
    FROM all_leads al
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
),
baseline AS (
    SELECT SUM(converted) * 100.0 / COUNT(*) as baseline_rate FROM title_data
)
SELECT 
    CASE WHEN is_wealth_manager = 1 THEN 'Wealth Manager Title' ELSE 'All Other Titles' END as title_group,
    COUNT(*) as total_leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / COUNT(*), 2) as conversion_rate_pct,
    ROUND(SUM(converted) * 100.0 / COUNT(*) / b.baseline_rate, 2) as lift_vs_baseline
FROM title_data
CROSS JOIN baseline b
GROUP BY is_wealth_manager, b.baseline_rate
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 2: Wealth Manager conversion BY EXISTING TIER
-- Does the title boost help WITHIN each tier?
-- ============================================================================
WITH scored_leads AS (
    SELECT 
        ls.lead_id,
        ls.advisor_crd,
        ls.score_tier,
        ls.converted,
        c.TITLE_NAME,
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSISTANT%'
        ) THEN 1 ELSE 0 END as is_wealth_manager
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3` ls
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(ls.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    WHERE ls.converted IS NOT NULL  -- Only mature leads with known outcomes
)
SELECT 
    score_tier,
    is_wealth_manager,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM scored_leads
GROUP BY score_tier, is_wealth_manager
HAVING COUNT(*) >= 10  -- Minimum sample size
ORDER BY score_tier, is_wealth_manager DESC;

-- ============================================================================
-- QUERY 3: Wealth Manager vs. Existing Boosts (CFP, Series 65)
-- How does Wealth Manager compare to certifications we already boost?
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
        -- Wealth Manager title
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
        ) THEN 1 ELSE 0 END as is_wealth_manager,
        -- CFP certification
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' 
             OR c.CONTACT_BIO LIKE '%Certified Financial Planner%'
             OR c.TITLE_NAME LIKE '%CFP%'
             THEN 1 ELSE 0 END as has_cfp,
        -- Series 65 only (no Series 7)
        CASE WHEN (c.REP_LICENSES LIKE '%Series 65%' OR c.REP_LICENSES LIKE '%Series 66%')
             AND c.REP_LICENSES NOT LIKE '%Series 7%'
             THEN 1 ELSE 0 END as has_series_65_only
    FROM all_leads al
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
),
baseline AS (
    SELECT SUM(converted) * 100.0 / COUNT(*) as baseline_rate FROM enriched
)
SELECT 
    'Wealth Manager Title' as boost_type,
    SUM(is_wealth_manager) as leads_with_signal,
    SUM(CASE WHEN is_wealth_manager = 1 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN is_wealth_manager = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(is_wealth_manager), 0), 2) as conversion_rate_pct,
    ROUND(SUM(CASE WHEN is_wealth_manager = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(is_wealth_manager), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM enriched CROSS JOIN baseline b
GROUP BY b.baseline_rate

UNION ALL

SELECT 
    'CFP Certification' as boost_type,
    SUM(has_cfp) as leads_with_signal,
    SUM(CASE WHEN has_cfp = 1 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN has_cfp = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(has_cfp), 0), 2) as conversion_rate_pct,
    ROUND(SUM(CASE WHEN has_cfp = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(has_cfp), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM enriched CROSS JOIN baseline b
GROUP BY b.baseline_rate

UNION ALL

SELECT 
    'Series 65 Only (No 7)' as boost_type,
    SUM(has_series_65_only) as leads_with_signal,
    SUM(CASE WHEN has_series_65_only = 1 THEN converted ELSE 0 END) as conversions,
    ROUND(SUM(CASE WHEN has_series_65_only = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(has_series_65_only), 0), 2) as conversion_rate_pct,
    ROUND(SUM(CASE WHEN has_series_65_only = 1 THEN converted ELSE 0 END) * 100.0 / 
          NULLIF(SUM(has_series_65_only), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM enriched CROSS JOIN baseline b
GROUP BY b.baseline_rate

ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 4: Combination Analysis - Wealth Manager + Other Signals
-- Does Wealth Manager stack with existing boost signals?
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
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
        ) THEN 1 ELSE 0 END as is_wealth_manager,
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' 
             OR c.CONTACT_BIO LIKE '%Certified Financial Planner%'
             OR c.TITLE_NAME LIKE '%CFP%'
             THEN 1 ELSE 0 END as has_cfp,
        CASE WHEN (c.REP_LICENSES LIKE '%Series 65%' OR c.REP_LICENSES LIKE '%Series 66%')
             AND c.REP_LICENSES NOT LIKE '%Series 7%'
             THEN 1 ELSE 0 END as has_series_65_only
    FROM all_leads al
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON al.crd = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
),
baseline AS (
    SELECT SUM(converted) * 100.0 / COUNT(*) as baseline_rate FROM enriched
)
SELECT 
    CASE 
        WHEN is_wealth_manager = 1 AND has_cfp = 1 THEN 'Wealth Manager + CFP'
        WHEN is_wealth_manager = 1 AND has_series_65_only = 1 THEN 'Wealth Manager + Series 65 Only'
        WHEN is_wealth_manager = 1 THEN 'Wealth Manager Only'
        WHEN has_cfp = 1 THEN 'CFP Only (no WM title)'
        WHEN has_series_65_only = 1 THEN 'Series 65 Only (no WM title)'
        ELSE 'None of these signals'
    END as signal_combination,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM enriched
CROSS JOIN baseline b
GROUP BY 
    CASE 
        WHEN is_wealth_manager = 1 AND has_cfp = 1 THEN 'Wealth Manager + CFP'
        WHEN is_wealth_manager = 1 AND has_series_65_only = 1 THEN 'Wealth Manager + Series 65 Only'
        WHEN is_wealth_manager = 1 THEN 'Wealth Manager Only'
        WHEN has_cfp = 1 THEN 'CFP Only (no WM title)'
        WHEN has_series_65_only = 1 THEN 'Series 65 Only (no WM title)'
        ELSE 'None of these signals'
    END,
    b.baseline_rate
HAVING COUNT(*) >= 20
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 5: Wealth Manager + Tier 1 Criteria (Prime Mover Simulation)
-- What if we applied Wealth Manager boost like we do CFP?
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
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
        ) THEN 1 ELSE 0 END as is_wealth_manager
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3` ls
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(ls.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    WHERE ls.converted IS NOT NULL
),
tier1_criteria AS (
    SELECT 
        *,
        -- Replicate Tier 1 criteria
        CASE WHEN (
            current_firm_tenure_months BETWEEN 12 AND 48  -- 1-4 years
            AND industry_tenure_months BETWEEN 60 AND 180  -- 5-15 years
            AND firm_net_change_12mo < 0  -- Bleeding
        ) THEN 1 ELSE 0 END as meets_prime_mover_criteria
    FROM scored_leads
)
SELECT 
    CASE 
        WHEN meets_prime_mover_criteria = 1 AND is_wealth_manager = 1 
            THEN 'TIER_1_WM: Prime Mover + Wealth Manager'
        WHEN meets_prime_mover_criteria = 1 AND is_wealth_manager = 0 
            THEN 'TIER_1: Prime Mover (no WM title)'
        WHEN meets_prime_mover_criteria = 0 AND is_wealth_manager = 1 
            THEN 'Wealth Manager (not Prime Mover)'
        ELSE 'Neither'
    END as segment,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct
FROM tier1_criteria
GROUP BY 
    CASE 
        WHEN meets_prime_mover_criteria = 1 AND is_wealth_manager = 1 
            THEN 'TIER_1_WM: Prime Mover + Wealth Manager'
        WHEN meets_prime_mover_criteria = 1 AND is_wealth_manager = 0 
            THEN 'TIER_1: Prime Mover (no WM title)'
        WHEN meets_prime_mover_criteria = 0 AND is_wealth_manager = 1 
            THEN 'Wealth Manager (not Prime Mover)'
        ELSE 'Neither'
    END
HAVING COUNT(*) >= 10
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 6: Specific "Wealth Manager" Title Variants Performance
-- Which exact title strings perform best?
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
WHERE UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
GROUP BY c.TITLE_NAME, b.baseline_rate
HAVING COUNT(*) >= 20
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 7: Impact on January 2026 List
-- How many leads would be affected by a Wealth Manager boost?
-- ============================================================================
WITH jan_leads AS (
    SELECT 
        jl.advisor_crd,
        jl.score_tier,
        jl.expected_rate_pct,
        c.TITLE_NAME,
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
        ) THEN 1 ELSE 0 END as is_wealth_manager
    FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(jl.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
)
SELECT 
    score_tier,
    SUM(is_wealth_manager) as wealth_manager_count,
    COUNT(*) as tier_total,
    ROUND(SUM(is_wealth_manager) * 100.0 / COUNT(*), 2) as pct_wealth_manager
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
-- QUERY 8: Wealth Manager vs. "Senior Wealth Advisor" (high performer from earlier)
-- Compare similar but distinct titles
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
    CASE 
        WHEN UPPER(c.TITLE_NAME) = 'WEALTH MANAGER' THEN 'Wealth Manager (exact)'
        WHEN UPPER(c.TITLE_NAME) = 'SENIOR WEALTH MANAGER' THEN 'Senior Wealth Manager'
        WHEN UPPER(c.TITLE_NAME) = 'SENIOR WEALTH ADVISOR' THEN 'Senior Wealth Advisor'
        WHEN UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT%' THEN 'Other Wealth Manager variants'
        WHEN UPPER(c.TITLE_NAME) LIKE '%WEALTH ADVISOR%' THEN 'Wealth Advisor variants'
        WHEN UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGEMENT ADVISOR%' THEN 'Wealth Management Advisor (wirehouse)'
        ELSE 'Other'
    END as title_category,
    COUNT(*) as leads,
    SUM(al.converted) as conversions,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct,
    ROUND(SUM(al.converted) * 100.0 / NULLIF(COUNT(*), 0) / b.baseline_rate, 2) as lift_vs_baseline
FROM all_leads al
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON al.crd = c.RIA_CONTACT_CRD_ID
CROSS JOIN baseline b
WHERE UPPER(c.TITLE_NAME) LIKE '%WEALTH%'
GROUP BY 
    CASE 
        WHEN UPPER(c.TITLE_NAME) = 'WEALTH MANAGER' THEN 'Wealth Manager (exact)'
        WHEN UPPER(c.TITLE_NAME) = 'SENIOR WEALTH MANAGER' THEN 'Senior Wealth Manager'
        WHEN UPPER(c.TITLE_NAME) = 'SENIOR WEALTH ADVISOR' THEN 'Senior Wealth Advisor'
        WHEN UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
             AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT%' THEN 'Other Wealth Manager variants'
        WHEN UPPER(c.TITLE_NAME) LIKE '%WEALTH ADVISOR%' THEN 'Wealth Advisor variants'
        WHEN UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGEMENT ADVISOR%' THEN 'Wealth Management Advisor (wirehouse)'
        ELSE 'Other'
    END,
    b.baseline_rate
HAVING COUNT(*) >= 30
ORDER BY conversion_rate_pct DESC;

-- ============================================================================
-- QUERY 9: Population Size - How rare is "Wealth Manager" title?
-- Is there enough volume to create a dedicated tier?
-- ============================================================================
SELECT 
    'Wealth Manager (all variants, excl. WM Advisor)' as title_group,
    COUNT(*) as contacts_in_fintrx,
    (SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`) as total_contacts,
    ROUND(COUNT(*) * 100.0 / 
          (SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`), 2) as pct_of_population
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
WHERE UPPER(TITLE_NAME) LIKE '%WEALTH MANAGER%'
  AND UPPER(TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
  AND UPPER(TITLE_NAME) NOT LIKE '%ASSOCIATE%'
  AND UPPER(TITLE_NAME) NOT LIKE '%ASSISTANT%'

UNION ALL

SELECT 
    'Senior Wealth Advisor' as title_group,
    COUNT(*) as contacts_in_fintrx,
    (SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`) as total_contacts,
    ROUND(COUNT(*) * 100.0 / 
          (SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`), 2) as pct_of_population
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
WHERE UPPER(TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'

UNION ALL

SELECT 
    'CFP in title/bio (current boost)' as title_group,
    COUNT(*) as contacts_in_fintrx,
    (SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`) as total_contacts,
    ROUND(COUNT(*) * 100.0 / 
          (SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`), 2) as pct_of_population
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
WHERE CONTACT_BIO LIKE '%CFP%' 
   OR CONTACT_BIO LIKE '%Certified Financial Planner%'
   OR TITLE_NAME LIKE '%CFP%';

-- ============================================================================
-- QUERY 10: Final Recommendation Analysis
-- If we added TIER_1C_WEALTH_MANAGER, what would the distribution look like?
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
        -- Proposed boost
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
            AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
        ) THEN 1 ELSE 0 END as is_wealth_manager
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3` ls
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(ls.advisor_crd AS INT64) = SAFE_CAST(c.RIA_CONTACT_CRD_ID AS INT64)
    WHERE ls.converted IS NOT NULL
),
tier1_eligible AS (
    SELECT 
        *,
        -- Replicate basic Tier 1 criteria
        CASE WHEN (
            current_firm_tenure_months BETWEEN 12 AND 48
            AND industry_tenure_months BETWEEN 60 AND 180
            AND firm_net_change_12mo < 0
        ) THEN 1 ELSE 0 END as meets_prime_mover_base
    FROM scored_leads
),
proposed_tiers AS (
    SELECT 
        *,
        CASE 
            -- Existing Tier 1A: CFP + Prime Mover
            WHEN meets_prime_mover_base = 1 AND has_cfp = 1 THEN 'TIER_1A_CFP'
            -- Existing Tier 1B: Series 65 Only + Prime Mover
            WHEN meets_prime_mover_base = 1 AND has_series_65_only = 1 THEN 'TIER_1B_SERIES65'
            -- PROPOSED: Wealth Manager + Prime Mover
            WHEN meets_prime_mover_base = 1 AND is_wealth_manager = 1 THEN 'TIER_1C_WEALTH_MANAGER'
            -- Base Prime Mover
            WHEN meets_prime_mover_base = 1 THEN 'TIER_1_PRIME_MOVER'
            ELSE 'OTHER_TIERS'
        END as proposed_tier
    FROM tier1_eligible
)
SELECT 
    proposed_tier,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0), 2) as conversion_rate_pct,
    ROUND(SUM(converted) * 100.0 / NULLIF(COUNT(*), 0) / 3.82, 2) as lift_vs_baseline
FROM proposed_tiers
GROUP BY proposed_tier
ORDER BY 
    CASE proposed_tier
        WHEN 'TIER_1A_CFP' THEN 1
        WHEN 'TIER_1B_SERIES65' THEN 2
        WHEN 'TIER_1C_WEALTH_MANAGER' THEN 3
        WHEN 'TIER_1_PRIME_MOVER' THEN 4
        ELSE 5
    END;