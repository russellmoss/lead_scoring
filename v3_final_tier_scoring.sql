-- =============================================================================
-- V3 FINAL TIER SCORING SQL
-- =============================================================================
-- Based on empirical validation:
--   - Tier 1: Prime Movers (1-4yr tenure, 5-15yr exp) = 3.51x-6.59x lift
--   - Tier 2: Heavy Bleeders (<-10 net change) = 2.24x-3.56x lift
--   - Tier 3: Experienced Movers (1-4yr tenure, 20+ yr exp) = 2.74x lift
--   - Tier 4: Known Medium/Large Firms = 2.43x-2.58x lift
--
-- Key insight: Small firm rule was INVERTED - medium/large firms convert better
-- Key insight: firm_rep_count = 0 means UNKNOWN, not small
-- =============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scores_v3_final` AS

WITH lead_features AS (
    -- Base features from the V2 feature table (with firm_rep_count added)
    SELECT
        f.lead_id,
        f.advisor_crd,
        f.contacted_date,
        f.target as converted,
        
        -- Tenure and experience
        f.current_firm_tenure_months,
        f.current_firm_tenure_months / 12.0 as tenure_years,
        f.industry_tenure_months,
        f.industry_tenure_months / 12.0 as experience_years,
        
        -- Firm metrics
        f.firm_crd_at_contact,
        f.firm_net_change_12mo,
        f.firm_rep_count_at_contact,
        f.firm_aum_pit,
        
        -- Mobility
        f.pit_moves_3yr,
        f.num_prior_firms,
        
        -- Company name for wirehouse detection
        l.Company as company_name,
        l.FirstName as first_name,
        l.LastName as last_name,
        l.Email as email
        
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2` f
    INNER JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
        ON f.lead_id = l.Id
),

wirehouse_flagged AS (
    SELECT
        *,
        -- Wirehouse detection
        CASE 
            WHEN UPPER(company_name) LIKE '%MERRILL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%MORGAN STANLEY%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%UBS %' THEN TRUE
            WHEN UPPER(company_name) LIKE '%WELLS FARGO%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%EDWARD JONES%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%RAYMOND JAMES%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%AMERIPRISE%' THEN TRUE
            WHEN UPPER(company_name) LIKE '% LPL %' THEN TRUE
            WHEN UPPER(company_name) LIKE '%LPL FINANCIAL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%NORTHWESTERN MUTUAL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%STIFEL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%RBC %' THEN TRUE
            WHEN UPPER(company_name) LIKE '%JANNEY%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%BAIRD%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%OPPENHEIMER%' THEN TRUE
            ELSE FALSE
        END as is_wirehouse,
        
        -- Firm size category (only when data exists)
        CASE
            WHEN firm_rep_count_at_contact IS NULL OR firm_rep_count_at_contact = 0 THEN 'UNKNOWN'
            WHEN firm_rep_count_at_contact <= 10 THEN 'SMALL'
            WHEN firm_rep_count_at_contact <= 50 THEN 'MEDIUM'
            WHEN firm_rep_count_at_contact <= 200 THEN 'LARGE'
            ELSE 'VERY_LARGE'
        END as firm_size_category,
        
        -- Has valid firm size data
        (firm_rep_count_at_contact IS NOT NULL AND firm_rep_count_at_contact > 0) as has_firm_size_data
        
    FROM lead_features
),

scored AS (
    SELECT
        *,
        
        -- =================================================================
        -- TIER ASSIGNMENT (Priority Order)
        -- =================================================================
        CASE
            -- -----------------------------------------------------------------
            -- TIER 1: PRIME MOVERS (Expected 3.5x-6.6x lift)
            -- Recent hires (1-4yr) with mid-career experience (5-15yr)
            -- at unstable firms, not wirehouses
            -- -----------------------------------------------------------------
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 1
            
            -- -----------------------------------------------------------------
            -- TIER 2: HEAVY BLEEDERS (Expected 2.2x-3.6x lift)
            -- Experienced advisors at firms losing 10+ reps
            -- -----------------------------------------------------------------
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 2
            
            -- -----------------------------------------------------------------
            -- TIER 3: EXPERIENCED MOVERS (Expected 2.7x lift)
            -- Recent hires with long careers (20+ years)
            -- -----------------------------------------------------------------
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 3
            
            -- -----------------------------------------------------------------
            -- TIER 4: MEDIUM/LARGE FIRM BOOST (Expected 2.4x-2.6x lift)
            -- Advisors at medium/large firms (when we have data)
            -- Note: Counterintuitively, these convert BETTER than small firms
            -- -----------------------------------------------------------------
            WHEN has_firm_size_data = TRUE
                 AND firm_size_category IN ('MEDIUM', 'LARGE')
            THEN 4
            
            -- -----------------------------------------------------------------
            -- TIER 5: MODERATE BLEEDERS (Expected 1.6x-2.0x lift)
            -- Firms with some churn but not heavy bleeding
            -- -----------------------------------------------------------------
            WHEN firm_net_change_12mo < 0
                 AND firm_net_change_12mo >= -10
                 AND experience_years >= 5
            THEN 5
            
            -- -----------------------------------------------------------------
            -- STANDARD: Everything else
            -- -----------------------------------------------------------------
            ELSE 99
            
        END as tier_rank,
        
        -- Tier name for readability
        CASE
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 'TIER_1_PRIME_MOVER'
            
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 'TIER_2_HEAVY_BLEEDER'
            
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 'TIER_3_EXPERIENCED_MOVER'
            
            WHEN has_firm_size_data = TRUE
                 AND firm_size_category IN ('MEDIUM', 'LARGE')
            THEN 'TIER_4_KNOWN_MED_LARGE_FIRM'
            
            WHEN firm_net_change_12mo < 0
                 AND firm_net_change_12mo >= -10
                 AND experience_years >= 5
            THEN 'TIER_5_MODERATE_BLEEDER'
            
            ELSE 'STANDARD'
        END as tier_name,
        
        -- Expected lift (for prioritization within tiers)
        CASE
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 3.51
            
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 2.46
            
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 2.74
            
            WHEN has_firm_size_data = TRUE
                 AND firm_size_category IN ('MEDIUM', 'LARGE')
            THEN 2.50
            
            WHEN firm_net_change_12mo < 0
                 AND firm_net_change_12mo >= -10
                 AND experience_years >= 5
            THEN 1.80
            
            ELSE 1.00
        END as expected_lift,
        
        -- Individual rule flags (for debugging/analysis)
        (tenure_years BETWEEN 1 AND 4) as rule_short_tenure,
        (experience_years BETWEEN 5 AND 15) as rule_mid_career,
        (experience_years >= 20) as rule_veteran,
        (firm_net_change_12mo != 0) as rule_unstable_firm,
        (firm_net_change_12mo < -10) as rule_heavy_bleeding,
        (firm_net_change_12mo < 0 AND firm_net_change_12mo >= -10) as rule_moderate_bleeding
        
    FROM wirehouse_flagged
)

SELECT
    -- Identifiers
    lead_id,
    advisor_crd,
    contacted_date,
    
    -- Contact info
    first_name,
    last_name,
    email,
    company_name,
    
    -- Tier assignment
    tier_rank,
    tier_name,
    expected_lift,
    
    -- Key features
    tenure_years,
    experience_years,
    firm_net_change_12mo,
    firm_rep_count_at_contact,
    firm_size_category,
    is_wirehouse,
    pit_moves_3yr,
    
    -- Rule flags
    rule_short_tenure,
    rule_mid_career,
    rule_veteran,
    rule_unstable_firm,
    rule_heavy_bleeding,
    rule_moderate_bleeding,
    has_firm_size_data,
    
    -- Outcome (for validation)
    converted,
    
    -- Metadata
    CURRENT_TIMESTAMP() as scored_at,
    'v3-final-20251221' as model_version

FROM scored
ORDER BY tier_rank, expected_lift DESC, contacted_date DESC;


-- =============================================================================
-- VALIDATION QUERY: Check tier distribution and lift
-- =============================================================================

SELECT
    tier_name,
    tier_rank,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`), 2) as actual_lift,
    ROUND(AVG(expected_lift), 2) as expected_lift
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
GROUP BY 1, 2
ORDER BY tier_rank;
