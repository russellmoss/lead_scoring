-- ============================================================================
-- STEP 1: HISTORICAL LEADS WITH V3 TIER ASSIGNMENTS
-- Purpose: Get all contacted leads from Q1-Q3 2025 with retrospective tier assignment
-- ============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.historical_leads_with_tiers` AS

WITH 
-- ============================================================================
-- A. GET ALL CONTACTED LEADS FROM Q1-Q3 2025
-- ============================================================================
contacted_leads AS (
    SELECT DISTINCT
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        l.FirstName as first_name,
        l.LastName as last_name,
        l.Company as company,
        DATE(l.CreatedDate) as lead_created_date,
        -- Get first contact date from tasks
        (
            SELECT MIN(DATE(t.ActivityDate))
            FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
            WHERE t.WhoId = l.Id
              AND t.IsDeleted = false
              AND (t.TaskSubtype = 'Call' OR t.Type = 'Call' OR t.Type LIKE '%SMS%')
              AND t.ActivityDate IS NOT NULL
        ) as first_contact_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2025-01-01'
      AND l.CreatedDate < '2025-10-01'
),

-- Filter to leads actually contacted
contacted_only AS (
    SELECT *
    FROM contacted_leads
    WHERE first_contact_date IS NOT NULL
      AND first_contact_date >= '2025-01-01'
      AND first_contact_date < '2025-10-01'
),

-- ============================================================================
-- B. GET ADVISOR CHARACTERISTICS AT TIME OF CONTACT
-- ============================================================================
-- Note: Using current snapshot as proxy (PIT would require historical snapshots)
advisor_data AS (
    SELECT 
        cl.lead_id,
        cl.crd,
        cl.first_name,
        cl.last_name,
        cl.first_contact_date,
        c.PRIMARY_FIRM_NAME as firm_name,
        SAFE_CAST(c.PRIMARY_FIRM AS INT64) as firm_crd,
        
        -- Tenure at time of contact (approximate using current start date)
        DATE_DIFF(cl.first_contact_date, c.LATEST_REGISTERED_EMPLOYMENT_START_DATE, YEAR) as tenure_years,
        DATE_DIFF(cl.first_contact_date, c.LATEST_REGISTERED_EMPLOYMENT_START_DATE, MONTH) as tenure_months,
        
        -- Industry tenure
        COALESCE(c.INDUSTRY_TENURE_MONTHS, 0) / 12 as industry_tenure_years,
        
        -- Certifications
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' OR c.TITLE_NAME LIKE '%CFP%' THEN 1 ELSE 0 END as has_cfp,
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' AND c.REP_LICENSES NOT LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_65_only,
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7,
        
        -- Firm rep count
        c.PRIMARY_FIRM_EMPLOYEE_COUNT as firm_rep_count
        
    FROM contacted_only cl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON cl.crd = c.RIA_CONTACT_CRD_ID
),

-- ============================================================================
-- C. GET PRIOR FIRMS COUNT (MOBILITY)
-- ============================================================================
mobility AS (
    SELECT 
        ad.crd,
        ad.first_contact_date,
        COUNT(DISTINCT eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as num_prior_firms,
        COUNT(DISTINCT CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(ad.first_contact_date, INTERVAL 3 YEAR)
            THEN eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID 
        END) as moves_3yr
    FROM advisor_data ad
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON ad.crd = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE < ad.first_contact_date
    GROUP BY ad.crd, ad.first_contact_date
),

-- ============================================================================
-- D. GET FIRM NET CHANGE (DEPARTURES - ARRIVALS) - PIT COMPLIANT
-- ============================================================================
-- Calculate firm metrics AS OF first_contact_date for each lead
firm_departures_pit AS (
    SELECT
        ad.firm_crd,
        ad.first_contact_date,
        COUNT(DISTINCT eh.RIA_CONTACT_CRD_ID) as departures_12mo
    FROM advisor_data ad
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON ad.firm_crd = SAFE_CAST(eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64)
        AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(ad.first_contact_date, INTERVAL 12 MONTH)
        AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE < ad.first_contact_date
        AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    WHERE ad.firm_crd IS NOT NULL
    GROUP BY ad.firm_crd, ad.first_contact_date
),

firm_arrivals_pit AS (
    SELECT
        ad.firm_crd,
        ad.first_contact_date,
        COUNT(DISTINCT c.RIA_CONTACT_CRD_ID) as arrivals_12mo
    FROM advisor_data ad
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON ad.firm_crd = SAFE_CAST(c.PRIMARY_FIRM AS INT64)
        AND c.PRIMARY_FIRM_START_DATE >= DATE_SUB(ad.first_contact_date, INTERVAL 12 MONTH)
        AND c.PRIMARY_FIRM_START_DATE < ad.first_contact_date
    WHERE ad.firm_crd IS NOT NULL
    GROUP BY ad.firm_crd, ad.first_contact_date
),

firm_metrics AS (
    SELECT 
        COALESCE(fd.firm_crd, fa.firm_crd) as firm_crd,
        COALESCE(fd.first_contact_date, fa.first_contact_date) as first_contact_date,
        COALESCE(fa.arrivals_12mo, 0) - COALESCE(fd.departures_12mo, 0) as firm_net_change_12mo
    FROM firm_departures_pit fd
    FULL OUTER JOIN firm_arrivals_pit fa 
        ON fd.firm_crd = fa.firm_crd 
        AND fd.first_contact_date = fa.first_contact_date
),

-- ============================================================================
-- E. DETECT WIREHOUSE
-- ============================================================================
wirehouse_check AS (
    SELECT 
        ad.crd,
        CASE
            WHEN UPPER(ad.firm_name) LIKE '%MERRILL%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%MORGAN STANLEY%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%UBS%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%WELLS FARGO%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%EDWARD JONES%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%RAYMOND JAMES%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%AMERIPRISE%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%LPL%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%NORTHWESTERN MUTUAL%' THEN 1
            ELSE 0
        END as is_wirehouse
    FROM advisor_data ad
),

-- ============================================================================
-- F. COMBINE AND ASSIGN V3 TIERS
-- ============================================================================
enriched_leads AS (
    SELECT 
        ad.*,
        COALESCE(m.num_prior_firms, 0) as num_prior_firms,
        COALESCE(m.moves_3yr, 0) as moves_3yr,
        COALESCE(fm.firm_net_change_12mo, 0) as firm_net_change_12mo,
        COALESCE(wh.is_wirehouse, 0) as is_wirehouse
    FROM advisor_data ad
    LEFT JOIN mobility m ON ad.crd = m.crd AND ad.first_contact_date = m.first_contact_date
    LEFT JOIN firm_metrics fm ON ad.firm_crd = fm.firm_crd AND ad.first_contact_date = fm.first_contact_date
    LEFT JOIN wirehouse_check wh ON ad.crd = wh.crd
),

tiered_leads AS (
    SELECT 
        el.*,
        
        -- V3 Tier Assignment (same logic as January 2026 query)
        CASE 
            -- T1A: CFP at bleeding firm, 1-4yr tenure
            WHEN (el.tenure_years BETWEEN 1 AND 4 
                  AND el.industry_tenure_years >= 5 
                  AND el.firm_net_change_12mo < 0 
                  AND el.has_cfp = 1 
                  AND el.is_wirehouse = 0) 
            THEN 'TIER_1A_PRIME_MOVER_CFP'
            
            -- T1B: Series 65 only at bleeding firm
            WHEN (el.tenure_years BETWEEN 1 AND 4 
                  AND el.industry_tenure_years >= 5 
                  AND el.firm_net_change_12mo < 0 
                  AND el.has_series_65_only = 1 
                  AND el.is_wirehouse = 0) 
            THEN 'TIER_1B_PRIME_MOVER_SERIES65'
            
            -- T1: Prime mover (short tenure at small/bleeding firm)
            WHEN ((el.tenure_years BETWEEN 1 AND 3 
                   AND el.industry_tenure_years BETWEEN 5 AND 15 
                   AND el.firm_net_change_12mo < 0 
                   AND el.firm_rep_count <= 50 
                   AND el.is_wirehouse = 0)
                  OR (el.tenure_years BETWEEN 1 AND 3 
                      AND el.firm_rep_count <= 10 
                      AND el.is_wirehouse = 0)
                  OR (el.tenure_years BETWEEN 1 AND 4 
                      AND el.industry_tenure_years BETWEEN 5 AND 15 
                      AND el.firm_net_change_12mo < 0 
                      AND el.is_wirehouse = 0)) 
            THEN 'TIER_1_PRIME_MOVER'
            
            -- T2: Proven mover (3+ prior firms)
            WHEN (el.num_prior_firms >= 3 AND el.industry_tenure_years >= 5) 
            THEN 'TIER_2_PROVEN_MOVER'
            
            -- T3: Moderate bleeder
            WHEN (el.firm_net_change_12mo BETWEEN -10 AND -1 AND el.industry_tenure_years >= 5) 
            THEN 'TIER_3_MODERATE_BLEEDER'
            
            -- T4: Experienced mover
            WHEN (el.industry_tenure_years >= 20 AND el.tenure_years BETWEEN 1 AND 4) 
            THEN 'TIER_4_EXPERIENCED_MOVER'
            
            -- T5: Heavy bleeder
            WHEN (el.firm_net_change_12mo <= -10 AND el.industry_tenure_years >= 5) 
            THEN 'TIER_5_HEAVY_BLEEDER'
            
            ELSE 'STANDARD'
        END as score_tier,
        
        -- Expected conversion rate per V3 model
        CASE 
            WHEN (el.tenure_years BETWEEN 1 AND 4 AND el.industry_tenure_years >= 5 AND el.firm_net_change_12mo < 0 AND el.has_cfp = 1 AND el.is_wirehouse = 0) THEN 0.1644
            WHEN (el.tenure_years BETWEEN 1 AND 4 AND el.industry_tenure_years >= 5 AND el.firm_net_change_12mo < 0 AND el.has_series_65_only = 1 AND el.is_wirehouse = 0) THEN 0.1648
            WHEN ((el.tenure_years BETWEEN 1 AND 3 AND el.industry_tenure_years BETWEEN 5 AND 15 AND el.firm_net_change_12mo < 0 AND el.firm_rep_count <= 50 AND el.is_wirehouse = 0)
                  OR (el.tenure_years BETWEEN 1 AND 3 AND el.firm_rep_count <= 10 AND el.is_wirehouse = 0)
                  OR (el.tenure_years BETWEEN 1 AND 4 AND el.industry_tenure_years BETWEEN 5 AND 15 AND el.firm_net_change_12mo < 0 AND el.is_wirehouse = 0)) THEN 0.1321
            WHEN (el.num_prior_firms >= 3 AND el.industry_tenure_years >= 5) THEN 0.0859
            WHEN (el.firm_net_change_12mo BETWEEN -10 AND -1 AND el.industry_tenure_years >= 5) THEN 0.0952
            WHEN (el.industry_tenure_years >= 20 AND el.tenure_years BETWEEN 1 AND 4) THEN 0.1154
            WHEN (el.firm_net_change_12mo <= -10 AND el.industry_tenure_years >= 5) THEN 0.0727
            ELSE 0.0382
        END as expected_conversion_rate
        
    FROM enriched_leads el
)

SELECT * FROM tiered_leads;

