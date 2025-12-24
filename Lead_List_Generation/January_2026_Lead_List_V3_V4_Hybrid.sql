-- ============================================================================
-- JANUARY 2026 LEAD LIST GENERATOR (V3.2.5 + V4 UPGRADE PATH)
-- Model: V3.2.5 + V4 XGBoost Hybrid v2
-- 
-- UPDATED HYBRID APPROACH (Based on V3 vs V4 Investigation):
-- - V3 Rules: Tier assignment (T1A, T1B, T1, T2, T3, T4, T5) - VALIDATED
-- - V4 XGBoost: UPGRADE PATH for STANDARD tier leads with V4 >= 80th percentile
-- 
-- KEY CHANGES FROM PREVIOUS VERSION:
-- 1. REMOVED: V4 deprioritization filter (not adding value within V3 tiers)
-- 2. ADDED: V4 upgrade path (STANDARD leads with V4 >= 80% convert at 4.60%)
-- 3. ADDED: is_v4_upgrade flag for tracking
--
-- INVESTIGATION FINDINGS:
-- - T1 converts at 7.41% vs T2 at 3.20% (V3 tier ordering validated)
-- - V4 AUC-ROC (0.6141) > V3 AUC-ROC (0.5095) - V4 better at prediction
-- - STANDARD leads with V4 >= 80% convert at 4.60% (1.42x baseline)
-- - V4 deprioritization was NOT adding value (90% of V3 leads scored in top 10%)
--
-- EXPECTED IMPROVEMENT: +6-12% conversion rate by including V4 upgraded leads
-- ============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.january_2026_lead_list_v4` AS

WITH 
-- ============================================================================
-- A. EXCLUSIONS (Wirehouses + Insurance)
-- ============================================================================
excluded_firms AS (
    SELECT firm_pattern FROM UNNEST([
        '%J.P. MORGAN%', '%MORGAN STANLEY%', '%MERRILL%', '%WELLS FARGO%', 
        '%UBS %', '%UBS,%', '%EDWARD JONES%', '%AMERIPRISE%', 
        '%NORTHWESTERN MUTUAL%', '%PRUDENTIAL%', '%RAYMOND JAMES%',
        '%FIDELITY%', '%SCHWAB%', '%VANGUARD%', '%GOLDMAN SACHS%', '%CITIGROUP%',
        '%LPL FINANCIAL%', '%COMMONWEALTH%', '%CETERA%', '%CAMBRIDGE%',
        '%OSAIC%', '%PRIMERICA%',
        '%STATE FARM%', '%ALLSTATE%', '%NEW YORK LIFE%', '%NYLIFE%',
        '%TRANSAMERICA%', '%FARM BUREAU%', '%NATIONWIDE%',
        '%LINCOLN FINANCIAL%', '%MASS MUTUAL%', '%MASSMUTUAL%',
        '%INSURANCE%'
    ]) as firm_pattern
),

-- ============================================================================
-- B. EXISTING SALESFORCE CRDs
-- ============================================================================
salesforce_crds AS (
    SELECT DISTINCT 
        SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        Id as lead_id
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE FA_CRD__c IS NOT NULL AND IsDeleted = false
),

-- ============================================================================
-- C. RECYCLABLE LEADS (180+ days no contact)
-- ============================================================================
lead_task_activity AS (
    SELECT 
        t.WhoId as lead_id,
        MAX(GREATEST(
            COALESCE(DATE(t.ActivityDate), DATE('1900-01-01')),
            COALESCE(DATE(t.CompletedDateTime), DATE('1900-01-01')),
            COALESCE(DATE(t.CreatedDate), DATE('1900-01-01'))
        )) as last_activity_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
    WHERE t.IsDeleted = false AND t.WhoId IS NOT NULL
      AND (t.Type IN ('Outgoing SMS', 'Incoming SMS')
           OR UPPER(t.Subject) LIKE '%SMS%' OR UPPER(t.Subject) LIKE '%TEXT%'
           OR t.TaskSubtype = 'Call' OR t.Type = 'Call'
           OR UPPER(t.Subject) LIKE '%CALL%' OR t.CallType IS NOT NULL)
    GROUP BY t.WhoId
),

recyclable_lead_ids AS (
    SELECT l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN lead_task_activity la ON l.Id = la.lead_id
    WHERE l.IsDeleted = false AND l.FA_CRD__c IS NOT NULL
      AND (la.last_activity_date IS NULL OR DATE_DIFF(CURRENT_DATE(), la.last_activity_date, DAY) > 180)
      AND (l.DoNotCall IS NULL OR l.DoNotCall = false)
      AND l.Status NOT IN ('Closed', 'Converted', 'Dead', 'Unqualified', 'Disqualified', 
                           'Do Not Contact', 'Not Qualified', 'Bad Data', 'Duplicate')
),

-- ============================================================================
-- D. ADVISOR EMPLOYMENT HISTORY (For mobility metrics)
-- ============================================================================
advisor_moves AS (
    SELECT 
        RIA_CONTACT_CRD_ID as crd,
        COUNT(DISTINCT PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as total_firms,
        COUNT(DISTINCT CASE 
            WHEN PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)
            THEN PREVIOUS_REGISTRATION_COMPANY_CRD_ID END) as moves_3yr,
        MIN(PREVIOUS_REGISTRATION_COMPANY_START_DATE) as career_start_date
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    GROUP BY RIA_CONTACT_CRD_ID
),

-- ============================================================================
-- E. FIRM HEADCOUNT (from ria_contacts_current)
-- ============================================================================
firm_headcount AS (
    SELECT 
        SAFE_CAST(PRIMARY_FIRM AS INT64) as firm_crd,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as current_reps
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
    WHERE PRIMARY_FIRM IS NOT NULL
    GROUP BY PRIMARY_FIRM
),

-- ============================================================================
-- F. FIRM DEPARTURES (12 months)
-- ============================================================================
firm_departures AS (
    SELECT
        SAFE_CAST(PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) as firm_crd,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as departures_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
      AND PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY 1
),

-- ============================================================================
-- G. FIRM ARRIVALS (12 months) - from ria_contacts_current
-- ============================================================================
firm_arrivals AS (
    SELECT
        SAFE_CAST(PRIMARY_FIRM AS INT64) as firm_crd,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as arrivals_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
    WHERE PRIMARY_FIRM_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
      AND PRIMARY_FIRM IS NOT NULL
    GROUP BY 1
),

-- ============================================================================
-- H. COMBINED FIRM METRICS
-- ============================================================================
firm_metrics AS (
    SELECT
        h.firm_crd,
        h.current_reps as firm_rep_count,
        COALESCE(d.departures_12mo, 0) as departures_12mo,
        COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
        COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as firm_net_change_12mo,
        CASE WHEN h.current_reps > 0 
             THEN COALESCE(d.departures_12mo, 0) * 100.0 / h.current_reps 
             ELSE 0 END as turnover_pct
    FROM firm_headcount h
    LEFT JOIN firm_departures d ON h.firm_crd = d.firm_crd
    LEFT JOIN firm_arrivals a ON h.firm_crd = a.firm_crd
    WHERE h.current_reps >= 20
),

-- ============================================================================
-- I. BASE PROSPECT DATA
-- ============================================================================
base_prospects AS (
    SELECT 
        c.RIA_CONTACT_CRD_ID as crd,
        c.CONTACT_FIRST_NAME as first_name,
        c.CONTACT_LAST_NAME as last_name,
        c.PRIMARY_FIRM_NAME as firm_name,
        SAFE_CAST(c.PRIMARY_FIRM AS INT64) as firm_crd,
        c.EMAIL as email,
        COALESCE(c.MOBILE_PHONE_NUMBER, c.OFFICE_PHONE_NUMBER) as phone,
        c.PRIMARY_FIRM_START_DATE as current_firm_start_date,
        c.PRIMARY_FIRM_EMPLOYEE_COUNT as firm_employee_count,
        DATE_DIFF(CURRENT_DATE(), c.PRIMARY_FIRM_START_DATE, MONTH) as tenure_months,
        DATE_DIFF(CURRENT_DATE(), c.PRIMARY_FIRM_START_DATE, YEAR) as tenure_years,
        CASE WHEN sf.crd IS NULL THEN 'NEW_PROSPECT' ELSE 'IN_SALESFORCE' END as prospect_type,
        sf.lead_id as existing_lead_id
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    LEFT JOIN salesforce_crds sf ON c.RIA_CONTACT_CRD_ID = sf.crd
    WHERE c.CONTACT_FIRST_NAME IS NOT NULL AND c.CONTACT_LAST_NAME IS NOT NULL
      AND c.PRIMARY_FIRM_START_DATE IS NOT NULL AND c.PRIMARY_FIRM_NAME IS NOT NULL
      AND c.PRIMARY_FIRM IS NOT NULL
      AND c.PRODUCING_ADVISOR = TRUE
      AND NOT EXISTS (SELECT 1 FROM excluded_firms ef WHERE UPPER(c.PRIMARY_FIRM_NAME) LIKE ef.firm_pattern)
      -- Title exclusions (V3.2.1)
      AND NOT (
          UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTIONS ADVISOR%'
          OR UPPER(c.TITLE_NAME) LIKE '%PARAPLANNER%'
          OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE ADVISOR%'
          OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS%'
          OR UPPER(c.TITLE_NAME) LIKE '%WHOLESALER%'
          OR UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE%'
          OR UPPER(c.TITLE_NAME) LIKE '%ASSISTANT%'
          OR UPPER(c.TITLE_NAME) LIKE '%INSURANCE AGENT%'
          OR UPPER(c.TITLE_NAME) LIKE '%INSURANCE%'
      )
),

-- ============================================================================
-- J. ENRICH WITH ADVISOR HISTORY, FIRM METRICS, AND CERTIFICATIONS
-- ============================================================================
enriched_prospects AS (
    SELECT 
        bp.*,
        COALESCE(am.total_firms, 1) as total_firms,
        COALESCE(am.total_firms, 1) - 1 as num_prior_firms,
        COALESCE(am.moves_3yr, 0) as moves_3yr,
        DATE_DIFF(CURRENT_DATE(), am.career_start_date, YEAR) as industry_tenure_years,
        DATE_DIFF(CURRENT_DATE(), am.career_start_date, MONTH) as industry_tenure_months,
        COALESCE(fm.firm_rep_count, bp.firm_employee_count, 1) as firm_rep_count,
        COALESCE(fm.arrivals_12mo, 0) as firm_arrivals_12mo,
        COALESCE(fm.departures_12mo, 0) as firm_departures_12mo,
        COALESCE(fm.firm_net_change_12mo, 0) as firm_net_change_12mo,
        COALESCE(fm.turnover_pct, 0) as firm_turnover_pct,
        CASE WHEN EXISTS (SELECT 1 FROM excluded_firms ef WHERE UPPER(bp.firm_name) LIKE ef.firm_pattern) THEN 1 ELSE 0 END as is_wirehouse,
        
        -- Certifications
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' OR c.TITLE_NAME LIKE '%CFP%' THEN 1 ELSE 0 END as has_cfp,
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' AND c.REP_LICENSES NOT LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_65_only,
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7,
        CASE WHEN c.CONTACT_BIO LIKE '%CFA%' OR c.TITLE_NAME LIKE '%CFA%' THEN 1 ELSE 0 END as has_cfa,
        
        -- High-value wealth title
        CASE WHEN (
            UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
            OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
            OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
        ) THEN 1 ELSE 0 END as is_hv_wealth_title,
        
        -- LinkedIn
        c.LINKEDIN_PROFILE_URL as linkedin_url,
        CASE WHEN c.LINKEDIN_PROFILE_URL IS NOT NULL AND TRIM(c.LINKEDIN_PROFILE_URL) != '' THEN 1 ELSE 0 END as has_linkedin,
        c.TITLE_NAME as fintrx_title,
        c.PRODUCING_ADVISOR as producing_advisor
        
    FROM base_prospects bp
    LEFT JOIN advisor_moves am ON bp.crd = am.crd
    LEFT JOIN firm_metrics fm ON bp.firm_crd = fm.firm_crd
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c ON bp.crd = c.RIA_CONTACT_CRD_ID
    WHERE COALESCE(fm.turnover_pct, 0) < 100
),

-- ============================================================================
-- J2. JOIN V4 SCORES (V4 XGBoost Integration)
-- ============================================================================
v4_enriched AS (
    SELECT 
        ep.*,
        COALESCE(v4.v4_score, 0.5) as v4_score,
        COALESCE(v4.v4_percentile, 50) as v4_percentile,
        COALESCE(v4.v4_deprioritize, FALSE) as v4_deprioritize
    FROM enriched_prospects ep
    LEFT JOIN `savvy-gtm-analytics.ml_features.v4_prospect_scores` v4 
        ON ep.crd = v4.crd
),

-- ============================================================================
-- K. APPLY V3.2 TIER LOGIC (uses v4_enriched)
-- ============================================================================
scored_prospects AS (
    SELECT 
        ep.*,
        
        -- Tier qualification path
        CASE 
            WHEN (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years >= 5 AND firm_net_change_12mo < 0 AND has_cfp = 1 AND is_wirehouse = 0) THEN 'TIER_1A_CFP'
            WHEN (((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0))
                  AND has_series_65_only = 1) THEN 'TIER_1B_SERIES65'
            WHEN (tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0) THEN 'TIER_1_PATH_1A'
            WHEN (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0) THEN 'TIER_1_PATH_1B'
            WHEN (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0) THEN 'TIER_1_PATH_1C'
            WHEN (is_hv_wealth_title = 1 AND firm_net_change_12mo < 0 AND is_wirehouse = 0) THEN 'TIER_1F_HV_WEALTH'
            WHEN (num_prior_firms >= 3 AND industry_tenure_years >= 5) THEN 'TIER_2_PROVEN_MOVER'
            WHEN (firm_net_change_12mo BETWEEN -10 AND -1 AND industry_tenure_years >= 5) THEN 'TIER_3_MODERATE_BLEEDER'
            WHEN (industry_tenure_years >= 20 AND tenure_years BETWEEN 1 AND 4) THEN 'TIER_4_EXPERIENCED_MOVER'
            WHEN (firm_net_change_12mo <= -10 AND industry_tenure_years >= 5) THEN 'TIER_5_HEAVY_BLEEDER'
            ELSE 'STANDARD'
        END as tier_qualification_path,
        
        -- Score tier (with V4 upgrade logic)
        CASE 
            WHEN (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years >= 5 AND firm_net_change_12mo < 0 AND has_cfp = 1 AND is_wirehouse = 0) THEN 'TIER_1A_PRIME_MOVER_CFP'
            WHEN (((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0))
                  AND has_series_65_only = 1) THEN 'TIER_1B_PRIME_MOVER_SERIES65'
            WHEN ((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0)) THEN 'TIER_1_PRIME_MOVER'
            WHEN (is_hv_wealth_title = 1 AND firm_net_change_12mo < 0 AND is_wirehouse = 0) THEN 'TIER_1F_HV_WEALTH_BLEEDER'
            WHEN (num_prior_firms >= 3 AND industry_tenure_years >= 5) THEN 'TIER_2_PROVEN_MOVER'
            WHEN (firm_net_change_12mo BETWEEN -10 AND -1 AND industry_tenure_years >= 5) THEN 'TIER_3_MODERATE_BLEEDER'
            WHEN (industry_tenure_years >= 20 AND tenure_years BETWEEN 1 AND 4) THEN 'TIER_4_EXPERIENCED_MOVER'
            WHEN (firm_net_change_12mo <= -10 AND industry_tenure_years >= 5) THEN 'TIER_5_HEAVY_BLEEDER'
            ELSE 'STANDARD'
        END as score_tier,
        
        -- Priority rank (V4 upgrades rank as 5.5 - between T2 and T3)
        CASE 
            WHEN (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years >= 5 AND firm_net_change_12mo < 0 AND has_cfp = 1 AND is_wirehouse = 0) THEN 1
            WHEN (((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0))
                  AND has_series_65_only = 1) THEN 2
            WHEN ((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0)) THEN 3
            WHEN (is_hv_wealth_title = 1 AND firm_net_change_12mo < 0 AND is_wirehouse = 0) THEN 4
            WHEN (num_prior_firms >= 3 AND industry_tenure_years >= 5) THEN 5
            WHEN (firm_net_change_12mo BETWEEN -10 AND -1 AND industry_tenure_years >= 5) THEN 6
            WHEN (industry_tenure_years >= 20 AND tenure_years BETWEEN 1 AND 4) THEN 7
            WHEN (firm_net_change_12mo <= -10 AND industry_tenure_years >= 5) THEN 8
            ELSE 99
        END as priority_rank,
        
        -- Expected conversion rate (V4 upgrades get 4.60% based on historical data)
        CASE 
            WHEN (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years >= 5 AND firm_net_change_12mo < 0 AND has_cfp = 1 AND is_wirehouse = 0) THEN 0.087
            WHEN (((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0))
                  AND has_series_65_only = 1) THEN 0.079
            WHEN ((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0)) THEN 0.071
            WHEN (is_hv_wealth_title = 1 AND firm_net_change_12mo < 0 AND is_wirehouse = 0) THEN 0.065
            WHEN (num_prior_firms >= 3 AND industry_tenure_years >= 5) THEN 0.052
            WHEN (firm_net_change_12mo BETWEEN -10 AND -1 AND industry_tenure_years >= 5) THEN 0.044
            WHEN (industry_tenure_years >= 20 AND tenure_years BETWEEN 1 AND 4) THEN 0.041
            WHEN (firm_net_change_12mo <= -10 AND industry_tenure_years >= 5) THEN 0.038
            ELSE 0.025
        END as expected_conversion_rate,
        
        -- Score narrative
        CASE 
            WHEN (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years >= 5 AND firm_net_change_12mo < 0 AND has_cfp = 1 AND is_wirehouse = 0) 
                THEN 'CFP at bleeding firm with 1-4 year tenure - highest priority'
            WHEN (((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0))
                  AND has_series_65_only = 1) 
                THEN 'Series 65 only advisor meeting Tier 1 criteria'
            WHEN ((tenure_years BETWEEN 1 AND 3 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND firm_rep_count <= 50 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 3 AND firm_rep_count <= 10 AND is_wirehouse = 0)
                  OR (tenure_years BETWEEN 1 AND 4 AND industry_tenure_years BETWEEN 5 AND 15 AND firm_net_change_12mo < 0 AND is_wirehouse = 0)) 
                THEN 'Prime mover - short tenure at small/bleeding firm'
            ELSE 'Scored lead'
        END as score_narrative
        
    FROM v4_enriched ep
),

-- ============================================================================
-- L. RANK PROSPECTS
-- ============================================================================
ranked_prospects AS (
    SELECT 
        sp.*,
        CASE 
            WHEN sp.prospect_type = 'NEW_PROSPECT' THEN 1
            WHEN sp.existing_lead_id IN (SELECT lead_id FROM recyclable_lead_ids) THEN 2
            ELSE 99
        END as source_priority,
        ROW_NUMBER() OVER (
            PARTITION BY sp.firm_crd 
            ORDER BY 
                CASE WHEN sp.prospect_type = 'NEW_PROSPECT' THEN 0 ELSE 1 END,
                sp.priority_rank,
                sp.v4_percentile DESC,
                sp.crd
        ) as rank_within_firm
    FROM scored_prospects sp
    WHERE sp.prospect_type = 'NEW_PROSPECT'
       OR sp.existing_lead_id IN (SELECT lead_id FROM recyclable_lead_ids)
),

-- ============================================================================
-- M. APPLY FIRM DIVERSITY CAP (REMOVED V4 DEPRIORITIZATION - NOT ADDING VALUE)
-- ============================================================================
diversity_filtered AS (
    SELECT * FROM ranked_prospects
    WHERE rank_within_firm <= 50 
      AND source_priority < 99
    -- REMOVED: AND v4_deprioritize = FALSE (investigation showed this wasn't helping)
),

-- ============================================================================
-- N. APPLY TIER QUOTAS + V4 UPGRADE PATH
-- V4 Upgrade: STANDARD leads with V4 >= 80th percentile convert at 4.60%
-- ============================================================================
tier_limited AS (
    SELECT 
        df.*,
        -- Flag V4 upgraded leads for tracking
        CASE 
            WHEN df.score_tier = 'STANDARD' AND df.v4_percentile >= 80 THEN 1 
            ELSE 0 
        END as is_v4_upgrade,
        -- Override tier for V4 upgrades
        CASE 
            WHEN df.score_tier = 'STANDARD' AND df.v4_percentile >= 80 THEN 'V4_UPGRADE'
            ELSE df.score_tier 
        END as final_tier,
        -- Override expected rate for V4 upgrades (4.60% based on historical data)
        CASE 
            WHEN df.score_tier = 'STANDARD' AND df.v4_percentile >= 80 THEN 0.046
            ELSE df.expected_conversion_rate 
        END as final_expected_rate,
        ROW_NUMBER() OVER (
            PARTITION BY 
                CASE 
                    WHEN df.score_tier = 'STANDARD' AND df.v4_percentile >= 80 THEN 'V4_UPGRADE'
                    ELSE df.score_tier 
                END
            ORDER BY 
                df.source_priority,
                df.has_linkedin DESC,
                df.v4_percentile DESC,
                df.priority_rank,
                CASE WHEN df.firm_net_change_12mo < 0 THEN ABS(df.firm_net_change_12mo) ELSE 0 END DESC,
                df.crd
        ) as tier_rank
    FROM diversity_filtered df
    WHERE df.score_tier != 'STANDARD'  -- Original V3 tiers
       OR (df.score_tier = 'STANDARD' AND df.v4_percentile >= 80)  -- V4 UPGRADE PATH
),

-- ============================================================================
-- O. LINKEDIN PRIORITIZATION
-- ============================================================================
linkedin_prioritized AS (
    SELECT 
        tl.*,
        ROW_NUMBER() OVER (
            ORDER BY 
                CASE final_tier
                    WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1
                    WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2
                    WHEN 'TIER_1_PRIME_MOVER' THEN 3
                    WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 4
                    WHEN 'TIER_2_PROVEN_MOVER' THEN 5
                    WHEN 'V4_UPGRADE' THEN 6  -- V4 upgrades rank between T2 and T3
                    WHEN 'TIER_3_MODERATE_BLEEDER' THEN 7
                    WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 8
                    WHEN 'TIER_5_HEAVY_BLEEDER' THEN 9
                END,
                source_priority,
                has_linkedin DESC,
                v4_percentile DESC,
                crd
        ) as overall_rank,
        CASE 
            WHEN has_linkedin = 0 THEN
                ROW_NUMBER() OVER (
                    PARTITION BY CASE WHEN has_linkedin = 0 THEN 1 ELSE 0 END
                    ORDER BY 
                        CASE final_tier
                            WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1
                            WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2
                            WHEN 'TIER_1_PRIME_MOVER' THEN 3
                            WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 4
                            WHEN 'TIER_2_PROVEN_MOVER' THEN 5
                            WHEN 'V4_UPGRADE' THEN 6
                            WHEN 'TIER_3_MODERATE_BLEEDER' THEN 7
                            WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 8
                            WHEN 'TIER_5_HEAVY_BLEEDER' THEN 9
                        END,
                        source_priority,
                        v4_percentile DESC,
                        crd
                )
            ELSE NULL
        END as no_linkedin_rank
    FROM tier_limited tl
    WHERE 
        -- Original tier quotas
        (final_tier = 'TIER_1A_PRIME_MOVER_CFP' AND tier_rank <= 50)
        OR (final_tier = 'TIER_1B_PRIME_MOVER_SERIES65' AND tier_rank <= 60)
        OR (final_tier = 'TIER_1_PRIME_MOVER' AND tier_rank <= 300)
        OR (final_tier = 'TIER_1F_HV_WEALTH_BLEEDER' AND tier_rank <= 50)
        OR (final_tier = 'TIER_2_PROVEN_MOVER' AND tier_rank <= 1500)
        OR (final_tier = 'TIER_3_MODERATE_BLEEDER' AND tier_rank <= 300)
        OR (final_tier = 'TIER_4_EXPERIENCED_MOVER' AND tier_rank <= 300)
        OR (final_tier = 'TIER_5_HEAVY_BLEEDER' AND tier_rank <= 1500)
        -- V4 UPGRADE quota: up to 500 leads (based on ~1,174 historical leads at 4.60%)
        OR (final_tier = 'V4_UPGRADE' AND tier_rank <= 500)
)

-- ============================================================================
-- P. FINAL OUTPUT
-- ============================================================================
SELECT 
    crd as advisor_crd,
    existing_lead_id as salesforce_lead_id,
    first_name,
    last_name,
    email,
    phone,
    linkedin_url,
    has_linkedin,
    fintrx_title,
    producing_advisor,
    firm_name,
    firm_crd,
    firm_rep_count,
    firm_net_change_12mo,
    firm_arrivals_12mo,
    firm_departures_12mo,
    ROUND(firm_turnover_pct, 1) as firm_turnover_pct,
    tenure_months,
    tenure_years,
    industry_tenure_years,
    num_prior_firms,
    moves_3yr,
    score_tier as original_v3_tier,  -- Keep original V3 tier for reference
    final_tier as score_tier,  -- Use final tier (includes V4_UPGRADE)
    tier_qualification_path,
    priority_rank,
    final_expected_rate as expected_conversion_rate,
    ROUND(final_expected_rate * 100, 2) as expected_rate_pct,
    score_narrative,
    has_cfp,
    has_series_65_only,
    has_series_7,
    has_cfa,
    is_hv_wealth_title,
    prospect_type,
    CASE 
        WHEN prospect_type = 'NEW_PROSPECT' THEN 'New - Not in Salesforce'
        ELSE 'Recyclable - 180+ days no contact'
    END as lead_source_description,
    
    -- V4 Score columns
    ROUND(v4_score, 4) as v4_score,
    v4_percentile,
    
    -- V4 UPGRADE FLAG (NEW - for tracking performance)
    is_v4_upgrade,
    CASE 
        WHEN is_v4_upgrade = 1 THEN 'V4 Upgrade (STANDARD with V4 >= 80%)'
        ELSE 'V3 Tier Qualified'
    END as v4_status,
    
    overall_rank as list_rank,
    CURRENT_TIMESTAMP() as generated_at

FROM linkedin_prioritized
WHERE 
    has_linkedin = 1 
    OR (has_linkedin = 0 AND no_linkedin_rank <= 240)
ORDER BY 
    overall_rank
LIMIT 2400;