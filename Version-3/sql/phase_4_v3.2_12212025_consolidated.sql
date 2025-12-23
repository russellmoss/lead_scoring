
-- ============================================================================
-- V3.2.1_12212025 CONSOLIDATED TIER SCORING WITH CERTIFICATIONS
-- ============================================================================
-- Version: V3.2.1_12212025
-- Date: 2025-01-22
-- Change: Added Tier 1A (CFP) and Tier 1B (Series 65) certification tiers
-- Historical Validation: Tier 1A (16.44%, n=73), Tier 1B (16.48%, n=91)
-- ============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025` AS

WITH 
-- Wirehouse exclusion patterns
excluded_firms AS (
    SELECT pattern FROM UNNEST([
        '%MERRILL%', '%MORGAN STANLEY%', '%UBS%', '%WELLS FARGO%',
        '%EDWARD JONES%', '%RAYMOND JAMES%', '%LPL FINANCIAL%',
        '%NORTHWESTERN MUTUAL%', '%MASS MUTUAL%', '%MASSMUTUAL%',
        '%NEW YORK LIFE%', '%NYLIFE%', '%PRUDENTIAL%', '%PRINCIPAL%',
        '%LINCOLN FINANCIAL%', '%TRANSAMERICA%', '%ALLSTATE%',
        '%STATE FARM%', '%FARM BUREAU%', '%BANK OF AMERICA%',
        '%JP MORGAN%', '%JPMORGAN%', '%AMERIPRISE%', '%FIDELITY%',
        '%SCHWAB%', '%CHARLES SCHWAB%', '%VANGUARD%',
        '%FISHER INVESTMENTS%', '%CREATIVE PLANNING%', '%EDELMAN%',
        '%FIRST COMMAND%', '%T. ROWE PRICE%'
    ]) AS pattern
),

-- Base lead data with features
lead_features AS (
    SELECT 
        l.Id as lead_id,
        l.FirstName, l.LastName, l.Email, l.Phone,
        l.Company, l.Title, l.Status, l.LeadSource,
        l.FA_CRD__c as advisor_crd,
        DATE(l.stage_entered_contacting__c) as contacted_date,
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.firm_rep_count_at_contact,
        f.firm_net_change_12mo,
        f.num_prior_firms,
        f.pit_moves_3yr,
        f.target,
        
        -- Convert months to years for tier logic
        SAFE_DIVIDE(f.current_firm_tenure_months, 12) as tenure_years,
        SAFE_DIVIDE(f.industry_tenure_months, 12) as experience_years,
        
        -- Derived flags
        UPPER(l.Company) as company_upper
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    INNER JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
        ON l.Id = f.lead_id
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.FA_CRD__c IS NOT NULL
        AND l.Company NOT LIKE '%Savvy%'  -- Exclude own company
),

-- Add wirehouse flag
leads_with_flags AS (
    SELECT 
        lf.*,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM excluded_firms ef 
                WHERE lf.company_upper LIKE ef.pattern
            ) THEN 1 ELSE 0 
        END as is_wirehouse
    FROM lead_features lf
),

-- Certification and license detection from FINTRX
lead_certifications AS (
    SELECT 
        l.lead_id,
        
        -- CFP from CONTACT_BIO or TITLE_NAME (professional certification)
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' 
             OR c.CONTACT_BIO LIKE '%Certified Financial Planner%'
             OR c.TITLE_NAME LIKE '%CFP%'
             THEN 1 ELSE 0 END as has_cfp,
        
        -- Series 65 only (pure RIA - NOT dual-registered)
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' 
             AND c.REP_LICENSES NOT LIKE '%Series 7%' 
             THEN 1 ELSE 0 END as has_series_65_only,
        
        -- Series 7 (broker-dealer registered - negative signal)
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' 
             THEN 1 ELSE 0 END as has_series_7,
        
        -- CFA (institutional focus - potential exclusion signal)
        CASE WHEN c.CONTACT_BIO LIKE '%CFA%' 
             OR c.CONTACT_BIO LIKE '%Chartered Financial Analyst%'
             OR c.TITLE_NAME LIKE '%CFA%'
             THEN 1 ELSE 0 END as has_cfa
        
    FROM leads_with_flags l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.advisor_crd AS STRING), r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
),

-- Join certifications to leads
leads_with_certs AS (
    SELECT 
        l.*,
        COALESCE(cert.has_cfp, 0) as has_cfp,
        COALESCE(cert.has_series_65_only, 0) as has_series_65_only,
        COALESCE(cert.has_series_7, 0) as has_series_7,
        COALESCE(cert.has_cfa, 0) as has_cfa
    FROM leads_with_flags l
    LEFT JOIN lead_certifications cert
        ON l.lead_id = cert.lead_id
),

-- Tier assignment with CERTIFICATION-BOOSTED tiers
tier_assignment AS (
    SELECT 
        *,
        CASE
            -- ============================================================
            -- TIER 1A: PRIME MOVER + CFP at BLEEDING FIRM
            -- CFP holders (book ownership signal) at unstable firms
            -- Expected: 16.44% conversion, 4.3x lift
            -- Historical validation: 73 leads, 12 conversions
            -- ============================================================
            WHEN (
                tenure_years BETWEEN 1 AND 4
                AND experience_years >= 5
                AND firm_net_change_12mo < 0
                AND has_cfp = 1
                AND is_wirehouse = 0
            )
            THEN 'TIER_1A_PRIME_MOVER_CFP'
            
            -- ============================================================
            -- TIER 1B: PRIME MOVER + SERIES 65 ONLY (Pure RIA)
            -- Series 65 (no Series 7) = fee-only RIA, easier to move
            -- Expected: 16.48% conversion, 4.3x lift
            -- Historical validation: 91 leads, 15 conversions
            -- ============================================================
            WHEN (
                -- Standard Tier 1 criteria
                (tenure_years BETWEEN 1 AND 3
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo < 0
                 AND firm_rep_count_at_contact <= 50
                 AND is_wirehouse = 0)
                OR
                (tenure_years BETWEEN 1 AND 3
                 AND firm_rep_count_at_contact <= 10
                 AND is_wirehouse = 0)
                OR
                (tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo < 0
                 AND is_wirehouse = 0)
            )
            AND has_series_65_only = 1
            THEN 'TIER_1B_PRIME_MOVER_SERIES65'
            
            -- ============================================================
            -- TIER 1: PRIME MOVER (CONSOLIDATED - no certification boost)
            -- Combines: 1A (small bleeding), 1B (very small), 1C (original)
            -- Expected: 13.21% conversion, 3.46x lift (UPDATED)
            -- ============================================================
            WHEN (
                -- Original 1A criteria: Small bleeding firm, mid-career
                (tenure_years BETWEEN 1 AND 3
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo < 0
                 AND firm_rep_count_at_contact <= 50
                 AND is_wirehouse = 0)
                OR
                -- Original 1B criteria: Very small firm
                (tenure_years BETWEEN 1 AND 3
                 AND firm_rep_count_at_contact <= 10
                 AND is_wirehouse = 0)
                OR
                -- Original 1C criteria: Original prime mover
                (tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo < 0
                 AND is_wirehouse = 0)
            )
            THEN 'TIER_1_PRIME_MOVER'
            
            -- ============================================================
            -- TIER 2: PROVEN MOVER (formerly 2A)
            -- Career movers with 3+ prior firms
            -- Expected: ~9% conversion, ~2.5x lift
            -- ============================================================
            WHEN num_prior_firms >= 3
                 AND experience_years >= 5
                 AND is_wirehouse = 0
            THEN 'TIER_2_PROVEN_MOVER'
            
            -- ============================================================
            -- TIER 3: MODERATE BLEEDER (formerly 2B)
            -- Firms losing 1-10 advisors
            -- Expected: ~9.3% conversion, ~2.6x lift
            -- ============================================================
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND experience_years >= 5
            THEN 'TIER_3_MODERATE_BLEEDER'
            
            -- ============================================================
            -- TIER 4: EXPERIENCED MOVER (formerly Tier 3)
            -- Veterans who recently moved
            -- Expected: ~12% conversion, ~3.3x lift
            -- ============================================================
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 'TIER_4_EXPERIENCED_MOVER'
            
            -- ============================================================
            -- TIER 5: HEAVY BLEEDER (formerly Tier 4)
            -- Firms in crisis (losing 10+ advisors)
            -- Expected: ~7.4% conversion, ~2.0x lift
            -- ============================================================
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 'TIER_5_HEAVY_BLEEDER'
            
            -- ============================================================
            -- STANDARD: All other leads
            -- Expected: 3.82% conversion (baseline - UPDATED)
            -- ============================================================
            ELSE 'STANDARD'
        END as score_tier
    FROM leads_with_certs
)

-- Final output with all metadata
SELECT 
    -- Lead identifiers
    lead_id,
    advisor_crd,
    contacted_date,
    FirstName,
    LastName,
    Company,
    Email,
    Phone,
    Title,
    Status,
    LeadSource,
    
    -- Tier assignment
    score_tier,
    
    -- Tier display names (user-friendly)
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN '🏆 Tier 1A: Prime Mover + CFP'
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN '🥇 Tier 1B: Prime Mover (Pure RIA)'
        WHEN 'TIER_1_PRIME_MOVER' THEN '🥇 Tier 1: Prime Mover'
        WHEN 'TIER_2_PROVEN_MOVER' THEN '🥈 Tier 2: Proven Mover'
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN '🥉 Tier 3: Moderate Bleeder'
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN '🏅 Tier 4: Experienced Mover'
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN '🎖️ Tier 5: Heavy Bleeder'
        ELSE '⬜ Standard'
    END as tier_display,
    
    -- Expected conversion rates (calibrated from 3-year historical data)
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 0.1644      -- NEW: 16.44% (n=73)
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 0.1648 -- NEW: 16.48% (n=91)
        WHEN 'TIER_1_PRIME_MOVER' THEN 0.1321           -- UPDATED: 13.21% (was 16.00%)
        WHEN 'TIER_2_PROVEN_MOVER' THEN 0.0900
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 0.0933
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 0.1197
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 0.0738
        ELSE 0.0382                                       -- UPDATED: 3.82% baseline
    END as expected_conversion_rate,
    
    -- Expected lift vs baseline (3.82%)
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 4.30        -- 16.44% / 3.82%
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 4.31   -- 16.48% / 3.82%
        WHEN 'TIER_1_PRIME_MOVER' THEN 3.46             -- 13.21% / 3.82%
        WHEN 'TIER_2_PROVEN_MOVER' THEN 2.46
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 2.55
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 3.27
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 2.02
        ELSE 1.00
    END as expected_lift,
    
    -- Priority rank (for sorting - lower = higher priority)
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1           -- NEW: Highest priority
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2      -- NEW: Second highest
        WHEN 'TIER_1_PRIME_MOVER' THEN 3                -- UPDATED: Was 1, now 3
        WHEN 'TIER_2_PROVEN_MOVER' THEN 4
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 5
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 6
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 7
        ELSE 8
    END as priority_rank,
    
    -- Action recommendations
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN '🔥 ULTRA-PRIORITY: Call immediately - CFP at unstable firm'
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN '🔥 Call immediately - pure RIA (no BD ties)'
        WHEN 'TIER_1_PRIME_MOVER' THEN 'Call immediately - highest priority'
        WHEN 'TIER_2_PROVEN_MOVER' THEN 'High priority outreach'
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 'Priority follow-up'
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 'Priority outreach - veteran advisor'
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 'Priority follow-up - firm in crisis'
        ELSE 'Standard workflow'
    END as action_recommended,
    
    -- Tier explanations (V3.2.1 - includes certification context for SGAs)
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 'CFP holder (Certified Financial Planner) at bleeding firm - CFP designation indicates book ownership and client relationships, making this advisor highly portable. Highest conversion potential at 16.44% (4.30x baseline).'
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 'Fee-only RIA (Series 65 only, no Series 7) meeting Prime Mover criteria - pure RIA advisors have no broker-dealer ties, making transitions easier. Expected 16.48% conversion (4.31x baseline).'
        WHEN 'TIER_1_PRIME_MOVER' THEN 'Mid-career advisor (1-4yr tenure, 5-15yr exp) at small/unstable firm OR very small firm (<10 reps) - standard Prime Mover without certification boost. Expected 13.21% conversion (3.46x baseline).'
        WHEN 'TIER_2_PROVEN_MOVER' THEN 'Career mover with 3+ prior firms and 5+ years experience - demonstrated willingness to change firms'
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 'Experienced advisor (5+ years) at firm losing 1-10 advisors - moderate instability signal'
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 'Veteran advisor (20+ years) who recently moved (1-4yr tenure) - has broken inertia'
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 'Experienced advisor (5+ years) at firm losing 10+ advisors - firm in crisis'
        ELSE 'Does not match priority tier criteria'
    END as tier_explanation,
    
    -- Key features (for debugging/analysis)
    current_firm_tenure_months,
    industry_tenure_months,
    tenure_years,
    experience_years,
    firm_net_change_12mo,
    firm_rep_count_at_contact,
    num_prior_firms,
    is_wirehouse,
    
    -- Target variable (for validation)
    target,
    
    -- Certification flags (for analysis/tracking)
    has_cfp,
    has_series_65_only,
    has_series_7,
    has_cfa,
    
    -- Model version
    'V3.2.1_12212025' as model_version,
    
    -- Timestamp
    CURRENT_TIMESTAMP() as scored_at

FROM tier_assignment
ORDER BY priority_rank, expected_conversion_rate DESC, contacted_date DESC;

