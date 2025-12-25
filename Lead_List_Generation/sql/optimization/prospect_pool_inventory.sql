-- ============================================================================
-- PROSPECT POOL INVENTORY BY TIER (V3.2.5 Logic)
-- Shows total available prospects and tier distribution
-- ============================================================================

WITH 
-- Exclusions (wirehouses, insurance, internal firms)
excluded_firms AS (
    SELECT firm_pattern FROM UNNEST([
        '%J.P. MORGAN%', '%MORGAN STANLEY%', '%MERRILL%', '%WELLS FARGO%', 
        '%UBS %', '%EDWARD JONES%', '%AMERIPRISE%', '%NORTHWESTERN MUTUAL%',
        '%PRUDENTIAL%', '%RAYMOND JAMES%', '%FIDELITY%', '%SCHWAB%', 
        '%VANGUARD%', '%GOLDMAN SACHS%', '%LPL FINANCIAL%', '%COMMONWEALTH%',
        '%CETERA%', '%PRIMERICA%', '%STATE FARM%', '%ALLSTATE%', 
        '%NEW YORK LIFE%', '%TRANSAMERICA%', '%INSURANCE%'
    ]) as firm_pattern
),

-- Firm headcount (current reps per firm)
firm_headcount AS (
    SELECT
        SAFE_CAST(PRIMARY_FIRM AS INT64) as firm_crd,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as current_reps
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
    WHERE PRIMARY_FIRM IS NOT NULL
      AND PRODUCING_ADVISOR = TRUE
      AND ACTIVE = TRUE
    GROUP BY 1
),

-- Firm departures (last 12 months)
firm_departures AS (
    SELECT
        SAFE_CAST(PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) as firm_crd,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as departures_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
      AND PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY 1
),

-- Firm arrivals (last 12 months)
firm_arrivals AS (
    SELECT
        SAFE_CAST(PRIMARY_FIRM AS INT64) as firm_crd,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as arrivals_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
    WHERE PRIMARY_FIRM_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
      AND PRIMARY_FIRM IS NOT NULL
    GROUP BY 1
),

-- Combined firm metrics
firm_metrics AS (
    SELECT
        h.firm_crd,
        h.current_reps as firm_rep_count,
        COALESCE(d.departures_12mo, 0) as departures_12mo,
        COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
        COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as firm_net_change_12mo
    FROM firm_headcount h
    LEFT JOIN firm_departures d ON h.firm_crd = d.firm_crd
    LEFT JOIN firm_arrivals a ON h.firm_crd = a.firm_crd
    WHERE h.current_reps >= 20
),

-- All producing advisors from FINTRX
all_prospects AS (
    SELECT 
        c.RIA_CONTACT_CRD_ID as crd,
        SAFE_CAST(c.PRIMARY_FIRM AS INT64) as firm_crd,
        c.PRIMARY_FIRM_NAME as firm_name,
        c.PRIMARY_FIRM_START_DATE as firm_start_date,
        c.LINKEDIN_PROFILE_URL,
        DATE_DIFF(CURRENT_DATE(), c.PRIMARY_FIRM_START_DATE, MONTH) as tenure_months,
        COALESCE(fm.firm_rep_count, 0) as firm_rep_count,
        COALESCE(fm.firm_net_change_12mo, 0) as firm_net_change_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    LEFT JOIN firm_metrics fm ON SAFE_CAST(c.PRIMARY_FIRM AS INT64) = fm.firm_crd
    WHERE c.RIA_CONTACT_CRD_ID IS NOT NULL
      AND c.PRODUCING_ADVISOR = TRUE
      AND c.ACTIVE = TRUE
      -- Exclude wirehouses/insurance
      AND NOT EXISTS (
          SELECT 1 FROM excluded_firms ef 
          WHERE UPPER(c.PRIMARY_FIRM_NAME) LIKE ef.firm_pattern
      )
      -- Exclude internal firms
      AND SAFE_CAST(c.PRIMARY_FIRM AS INT64) NOT IN (318493, 168652)  -- Savvy Wealth, Ritholtz
),

-- Prospects NOT already in Salesforce (new prospects)
new_prospects AS (
    SELECT ap.*
    FROM all_prospects ap
    LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l 
        ON CAST(ap.crd AS STRING) = l.FA_CRD__c
    WHERE l.Id IS NULL
),

-- Apply V3.2.5 tier logic (simplified for counting)
tiered_prospects AS (
    SELECT 
        np.*,
        CASE 
            -- Tier 1: Prime movers (tenure 12-48 months, small firm, bleeding)
            WHEN tenure_months BETWEEN 12 AND 48 
                 AND firm_rep_count <= 50 
                 AND firm_net_change_12mo < -3
            THEN 'TIER_1_PRIME_MOVER'
            
            -- Tier 2: Proven movers (tenure 24-120 months)
            WHEN tenure_months BETWEEN 24 AND 120
            THEN 'TIER_2_PROVEN_MOVER'
            
            -- Tier 3: Moderate bleeders
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
            THEN 'TIER_3_MODERATE_BLEEDER'
            
            -- Tier 5: Heavy bleeders
            WHEN firm_net_change_12mo < -10
            THEN 'TIER_5_HEAVY_BLEEDER'
            
            ELSE 'STANDARD'
        END as estimated_tier
    FROM new_prospects np
)

SELECT 
    estimated_tier,
    COUNT(*) as prospect_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct_of_total,
    COUNT(CASE WHEN LINKEDIN_PROFILE_URL IS NOT NULL THEN 1 END) as with_linkedin,
    ROUND(COUNT(CASE WHEN LINKEDIN_PROFILE_URL IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as linkedin_pct
FROM tiered_prospects
GROUP BY estimated_tier
ORDER BY 
    CASE estimated_tier
        WHEN 'TIER_1_PRIME_MOVER' THEN 1
        WHEN 'TIER_2_PROVEN_MOVER' THEN 2
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 3
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 4
        ELSE 99
    END

