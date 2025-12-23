
-- =============================================================================
-- LEAD SCORING V3.2: UPDATED TIER MODEL (December 2024)
-- =============================================================================
-- Version: v3.2-updated-20241222
-- Changes: Added small firm signals, tightened tenure, added proven movers tier
-- Expected Lift: T1A = 4.0x+, T1B = 3.5x+, T1C = 3.0x+, T2A = 2.5x, T2B = 2.5x
-- =============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scores_v3` AS

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
        f.target as converted,
        
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

-- Assign tiers (V3.2 UPDATED definitions)
tiered_leads AS (
    SELECT 
        *,
        CASE 
            -- ============================================================
            -- TIER 1A: PRIME MOVERS - SMALL FIRM (Expected ~15% conversion)
            -- Tightest criteria: short tenure + small bleeding firm
            -- ============================================================
            WHEN current_firm_tenure_months BETWEEN 12 AND 36  -- 1-3 years (tightened from 1-4)
                 AND industry_tenure_months BETWEEN 60 AND 180  -- 5-15 years experience
                 AND firm_net_change_12mo < 0                   -- Bleeding firm (changed from != 0)
                 AND firm_rep_count_at_contact <= 50            -- Small/mid firm (NEW)
                 AND is_wirehouse = 0
            THEN 'TIER_1A_PRIME_MOVER_SMALL'
            
            -- ============================================================
            -- TIER 1B: SMALL FIRM ADVISORS (Expected ~14% conversion)
            -- Very small firms convert well even without bleeding signal
            -- ============================================================
            WHEN current_firm_tenure_months BETWEEN 12 AND 36  -- 1-3 years tenure
                 AND firm_rep_count_at_contact <= 10            -- Very small firm (NEW)
                 AND is_wirehouse = 0
            THEN 'TIER_1B_SMALL_FIRM'
            
            -- ============================================================
            -- TIER 1C: PRIME MOVERS - ORIGINAL (Expected ~13% conversion)
            -- Original Tier 1 logic for larger firms
            -- ============================================================
            WHEN current_firm_tenure_months BETWEEN 12 AND 48  -- 1-4 years (original)
                 AND industry_tenure_months BETWEEN 60 AND 180  -- 5-15 years experience
                 AND firm_net_change_12mo < 0                   -- Bleeding firm
                 AND is_wirehouse = 0
            THEN 'TIER_1C_PRIME_MOVER'
            
            -- ============================================================
            -- TIER 2A: PROVEN MOVERS (Expected ~10% conversion) - NEW
            -- Career movers who have changed firms 3+ times
            -- ============================================================
            WHEN num_prior_firms >= 3                           -- 3+ prior employers (NEW)
                 AND industry_tenure_months >= 60               -- 5+ years experience
                 AND is_wirehouse = 0
            THEN 'TIER_2A_PROVEN_MOVER'
            
            -- ============================================================
            -- TIER 2B: MODERATE BLEEDERS (Expected ~11% conversion)
            -- Firms losing 1-10 advisors (original Tier 2)
            -- ============================================================
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND industry_tenure_months >= 60               -- 5+ years experience
            THEN 'TIER_2B_MODERATE_BLEEDER'
            
            -- ============================================================
            -- TIER 3: EXPERIENCED MOVERS (Expected ~10% conversion)
            -- Veterans who recently moved (original Tier 3)
            -- ============================================================
            WHEN current_firm_tenure_months BETWEEN 12 AND 48  -- 1-4 years tenure
                 AND industry_tenure_months >= 240              -- 20+ years experience
            THEN 'TIER_3_EXPERIENCED_MOVER'
            
            -- ============================================================
            -- TIER 4: HEAVY BLEEDERS (Expected ~10% conversion)
            -- Firms in crisis losing 10+ advisors (original Tier 4)
            -- ============================================================
            WHEN firm_net_change_12mo < -10
                 AND industry_tenure_months >= 60               -- 5+ years experience
            THEN 'TIER_4_HEAVY_BLEEDER'
            
            -- ============================================================
            -- STANDARD: All other leads
            -- ============================================================
            ELSE 'STANDARD'
        END as score_tier,
        
        -- Tier Display Names (for SGA dashboard)
        CASE 
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND firm_rep_count_at_contact <= 50
                 AND is_wirehouse = 0
            THEN '🥇 Prime Mover (Small Firm)'
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND firm_rep_count_at_contact <= 10
                 AND is_wirehouse = 0
            THEN '🥇 Small Firm Advisor'
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND is_wirehouse = 0
            THEN '🥇 Prime Mover'
            WHEN num_prior_firms >= 3
                 AND industry_tenure_months >= 60
                 AND is_wirehouse = 0
            THEN '🥈 Proven Mover'
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND industry_tenure_months >= 60
            THEN '🥈 Moderate Bleeder'
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months >= 240
            THEN '🥉 Experienced Mover'
            WHEN firm_net_change_12mo < -10
                 AND industry_tenure_months >= 60
            THEN '🎖️ Heavy Bleeder'
            ELSE 'Standard'
        END as tier_display,
        
        -- Expected Conversion Rate (calibrated)
        CASE 
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND firm_rep_count_at_contact <= 50
                 AND is_wirehouse = 0
            THEN 0.15
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND firm_rep_count_at_contact <= 10
                 AND is_wirehouse = 0
            THEN 0.14
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND is_wirehouse = 0
            THEN 0.13
            WHEN num_prior_firms >= 3
                 AND industry_tenure_months >= 60
                 AND is_wirehouse = 0
            THEN 0.10
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND industry_tenure_months >= 60
            THEN 0.11
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months >= 240
            THEN 0.10
            WHEN firm_net_change_12mo < -10
                 AND industry_tenure_months >= 60
            THEN 0.10
            ELSE 0.04
        END as expected_conversion_rate,
        
        -- Expected Lift
        CASE 
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND firm_rep_count_at_contact <= 50
                 AND is_wirehouse = 0
            THEN 3.5
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND firm_rep_count_at_contact <= 10
                 AND is_wirehouse = 0
            THEN 3.5
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND is_wirehouse = 0
            THEN 3.0
            WHEN num_prior_firms >= 3
                 AND industry_tenure_months >= 60
                 AND is_wirehouse = 0
            THEN 2.5
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND industry_tenure_months >= 60
            THEN 2.5
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months >= 240
            THEN 2.5
            WHEN firm_net_change_12mo < -10
                 AND industry_tenure_months >= 60
            THEN 2.3
            ELSE 1.0
        END as expected_lift,
        
        -- Priority Ranking (for sorting)
        CASE 
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND firm_rep_count_at_contact <= 50
                 AND is_wirehouse = 0
            THEN 1
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND firm_rep_count_at_contact <= 10
                 AND is_wirehouse = 0
            THEN 2
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND is_wirehouse = 0
            THEN 3
            WHEN num_prior_firms >= 3
                 AND industry_tenure_months >= 60
                 AND is_wirehouse = 0
            THEN 4
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND industry_tenure_months >= 60
            THEN 5
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months >= 240
            THEN 6
            WHEN firm_net_change_12mo < -10
                 AND industry_tenure_months >= 60
            THEN 7
            ELSE 99
        END as priority_rank,
        
        -- Action Recommended
        CASE 
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND firm_rep_count_at_contact <= 50
                 AND is_wirehouse = 0
            THEN 'Call immediately - highest priority'
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND firm_rep_count_at_contact <= 10
                 AND is_wirehouse = 0
            THEN 'Call immediately - highest priority'
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND is_wirehouse = 0
            THEN 'Call immediately - highest priority'
            WHEN num_prior_firms >= 3
                 AND industry_tenure_months >= 60
                 AND is_wirehouse = 0
            THEN 'Priority outreach within 24 hours'
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND industry_tenure_months >= 60
            THEN 'Priority outreach within 24 hours'
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months >= 240
            THEN 'Priority follow-up this week'
            WHEN firm_net_change_12mo < -10
                 AND industry_tenure_months >= 60
            THEN 'Priority follow-up this week'
            ELSE 'Standard outreach cadence'
        END as action_recommended,
        
        -- Tier Explanation (for sales team)
        CASE 
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND firm_rep_count_at_contact <= 50
                 AND is_wirehouse = 0
            THEN 'Mid-career advisor (1-3yr tenure, 5-15yr exp) at small bleeding firm - highest conversion signal'
            WHEN current_firm_tenure_months BETWEEN 12 AND 36
                 AND firm_rep_count_at_contact <= 10
                 AND is_wirehouse = 0
            THEN 'Recent joiner at very small firm (<10 reps) - high portability signal'
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months BETWEEN 60 AND 180
                 AND firm_net_change_12mo < 0
                 AND is_wirehouse = 0
            THEN 'Mid-career advisor at bleeding firm - proven high-converting segment'
            WHEN num_prior_firms >= 3
                 AND industry_tenure_months >= 60
                 AND is_wirehouse = 0
            THEN 'Has changed firms 3+ times - demonstrated willingness to move'
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND industry_tenure_months >= 60
            THEN 'Experienced advisor at firm losing 1-10 reps - instability signal'
            WHEN current_firm_tenure_months BETWEEN 12 AND 48
                 AND industry_tenure_months >= 240
            THEN 'Veteran (20+ yrs) who recently moved - has broken inertia'
            WHEN firm_net_change_12mo < -10
                 AND industry_tenure_months >= 60
            THEN 'Experienced advisor at firm in crisis (losing 10+ reps)'
            ELSE 'Standard lead - no priority signals detected'
        END as tier_explanation
    FROM leads_with_flags
)

-- Final output
SELECT 
    lead_id,
    advisor_crd,
    contacted_date,
    FirstName,
    LastName,
    Email,
    Phone,
    Company,
    Title,
    Status,
    LeadSource,
    score_tier,
    tier_display,
    expected_conversion_rate,
    expected_lift,
    priority_rank,
    action_recommended,
    tier_explanation,
    -- Include key features for transparency
    current_firm_tenure_months,
    industry_tenure_months,
    firm_net_change_12mo,
    firm_rep_count_at_contact,
    num_prior_firms,
    is_wirehouse,
    converted,
    CURRENT_TIMESTAMP() as scored_at,
    'v3.2-updated-20241222' as model_version
FROM tiered_leads
ORDER BY priority_rank, expected_conversion_rate DESC, contacted_date DESC
