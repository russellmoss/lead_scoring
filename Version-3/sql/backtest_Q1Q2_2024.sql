
-- V3.1 Backtest: Train on 2024-02-01 to 2024-05-31, Test on 2024-06-01 to 2024-08-31

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

-- Test period leads with features
test_leads AS (
    SELECT 
        l.Id as lead_id,
        l.FirstName, l.LastName, l.Email, l.Phone,
        l.Company, l.Title, l.Status, l.LeadSource,
        l.FA_CRD__c as advisor_crd,
        DATE(l.stage_entered_contacting__c) as contacted_date,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted,
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.firm_rep_count_at_contact,
        f.firm_net_change_12mo,
        f.pit_moves_3yr,
        
        -- Derived flags (CORRECTED thresholds)
        f.current_firm_tenure_months / 12.0 as tenure_years,
        f.industry_tenure_months / 12.0 as experience_years,
        UPPER(l.Company) as company_upper
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    INNER JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
        ON l.Id = f.lead_id
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.FA_CRD__c IS NOT NULL
        AND l.Company NOT LIKE '%Savvy%'
        AND DATE(l.stage_entered_contacting__c) >= '2024-06-01'
        AND DATE(l.stage_entered_contacting__c) <= '2024-08-31'
        -- Only include leads that are mature enough (30+ days old)
        AND DATE_DIFF(CURRENT_DATE(), DATE(l.stage_entered_contacting__c), DAY) >= 30
),

-- Add wirehouse flag
leads_with_flags AS (
    SELECT 
        tl.*,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM excluded_firms ef 
                WHERE tl.company_upper LIKE ef.pattern
            ) THEN 1 ELSE 0 
        END as is_wirehouse
    FROM test_leads tl
),

-- Assign tiers (V3.1 CORRECTED definitions)
tiered_test AS (
    SELECT 
        *,
        CASE 
            -- TIER 1: PRIME MOVERS (3.40x actual lift)
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = 0
            THEN 'TIER_1_PRIME_MOVER'
            
            -- TIER 2: MODERATE BLEEDERS (2.77x actual lift)
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND experience_years >= 5
            THEN 'TIER_2_MODERATE_BLEEDER'
            
            -- TIER 3: EXPERIENCED MOVERS (2.65x actual lift)
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 'TIER_3_EXPERIENCED_MOVER'
            
            -- TIER 4: HEAVY BLEEDERS (2.28x actual lift)
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 'TIER_4_HEAVY_BLEEDER'
            
            -- STANDARD: Everything else
            ELSE 'STANDARD'
        END as score_tier
    FROM leads_with_flags
)

-- Calculate tier performance
SELECT 
    score_tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (
        SELECT AVG(converted) 
        FROM tiered_test
    ), 2) as lift_vs_pool,
    '2024-02-01' as train_start,
    '2024-05-31' as train_end,
    '2024-06-01' as test_start,
    '2024-08-31' as test_end
FROM tiered_test
GROUP BY score_tier
ORDER BY 
    CASE score_tier
        WHEN 'TIER_1_PRIME_MOVER' THEN 1
        WHEN 'TIER_2_MODERATE_BLEEDER' THEN 2
        WHEN 'TIER_3_EXPERIENCED_MOVER' THEN 3
        WHEN 'TIER_4_HEAVY_BLEEDER' THEN 4
        ELSE 99
    END
