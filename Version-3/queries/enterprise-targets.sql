-- ============================================================================
-- ENTERPRISE & ECI OPPORTUNITY LEAD GENERATION
-- "Colorado Wealth Group Look-Alike" Query
-- ============================================================================
-- Target: Independent RIAs ($200M - $600M AUM) with Founder-Led Ownership
-- Based on Colorado Wealth Group Profile Analysis
-- ============================================================================
-- Criteria:
-- 1. Independent RIA (ENTITY_CLASSIFICATION contains "Independent RIA")
-- 2. AUM: $200M - $600M
-- 3. Small Teams: 5-25 employees (prioritize ≤10 reps)
-- 4. HNW Focus: >50% of AUM from HNW individuals
-- 5. Custodian: Fidelity or Charles Schwab
-- 6. Founder/Owner titles with ownership verification (>5%)
-- 7. Exclude non-decision makers (COO, CCO unless Partner, Operations, etc.)
-- 8. Smart producing advisor filter
-- ============================================================================

WITH 
-- ============================================================================
-- PHASE 1: FIRM IDENTIFICATION (CWG Filter)
-- ============================================================================
qualified_firms AS (
    SELECT 
        f.CRD_ID,
        f.NAME as firm_name,
        f.TOTAL_AUM,
        f.DISCRETIONARY_AUM,
        f.NON_DISCRETIONARY_AUM,
        f.AUM_YOY,
        f.AUM_3YOY,
        f.AUM_5YOY,
        f.NUM_OF_EMPLOYEES,
        f.EMPLOYEE_PERFORM_INVESTMENT_ADVISORY_FUNCTIONS_AND_RESEARCH as advisory_employees,
        f.ENTITY_CLASSIFICATION,
        f.CUSTODIAN_PRIMARY_BUSINESS_NAME,
        f.AMT_OF_AUM_HIGH_NET_WORTH_INDIVIDUALS,
        f.AMT_OF_AUM_NON_HIGH_NET_WORTH_INDIVIDUALS,
        f.INVESTMENTS_UTILIZED,
        f.MAIN_OFFICE_CITY_NAME,
        f.MAIN_OFFICE_STATE,
        f.MAIN_OFFICE_ADDRESS_1,
        f.MAIN_OFFICE_ADDRESS_2,
        f.ZIP_CODE,
        f.PHONE,
        f.FINTRX_URL as firm_fintrx_url,
        f.TEAM_PAGE,
        f.CLIENT_BASE,
        f.FEE_STRUCTURE,
        f.TOTAL_ACCOUNTS,
        f.TOTAL_DISCRETIONARY_ACCOUNTS,
        f.AVERAGE_ACCOUNT_SIZE,
        f.CAPITAL_ALLOCATOR,
        f.ACTIVE_ESG_INVESTOR,
        f.TAMP_AND_TECH_USED,
        f.LATEST_UPDATE as firm_latest_update,
        
        -- Calculate HNW percentage
        ROUND(SAFE_DIVIDE(f.AMT_OF_AUM_HIGH_NET_WORTH_INDIVIDUALS, f.TOTAL_AUM) * 100, 2) as hnw_aum_pct,
        
        -- Check for Exchange-Traded Equity Securities (active allocator check)
        CASE WHEN f.INVESTMENTS_UTILIZED LIKE '%Exchange-Traded Equities Securities%' THEN 1 ELSE 0 END as has_active_allocation,
        
        -- Custodian extraction (for sorting)
        CASE 
            WHEN f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%FIDELITY%' AND f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%SCHWAB%' THEN 'Both'
            WHEN f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%FIDELITY%' THEN 'Fidelity'
            WHEN f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%SCHWAB%' OR f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%CHARLES SCHWAB%' THEN 'Schwab'
            ELSE 'Other'
        END as primary_custodian,
        
        -- Count active advisors at firm
        (SELECT COUNT(DISTINCT c.RIA_CONTACT_CRD_ID)
         FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
         WHERE c.PRIMARY_FIRM = f.CRD_ID
           AND c.ACTIVE = TRUE
           AND c.PRODUCING_ADVISOR = TRUE
        ) as active_producing_reps
        
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    WHERE f.TOTAL_AUM BETWEEN 200000000 AND 600000000  -- $200M - $600M AUM
      AND f.ACTIVE = TRUE
      AND f.ENTITY_CLASSIFICATION LIKE '%Independent RIA%'  -- Must be Independent RIA
      AND (
          f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%FIDELITY%'
          OR f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%SCHWAB%'
          OR f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%CHARLES SCHWAB%'
      )  -- Fidelity or Schwab custodian
      AND f.NUM_OF_EMPLOYEES BETWEEN 5 AND 25  -- Small teams: 5-25 employees
      AND SAFE_DIVIDE(f.AMT_OF_AUM_HIGH_NET_WORTH_INDIVIDUALS, f.TOTAL_AUM) > 0.50  -- >50% HNW AUM
      AND f.INVESTMENTS_UTILIZED LIKE '%Exchange-Traded Equities Securities%'  -- Active allocator check
),

-- ============================================================================
-- PHASE 2: FINDING THE "TRUE" OWNERS (Tier 1F Logic)
-- ============================================================================
owner_candidates AS (
    SELECT 
        c.RIA_CONTACT_CRD_ID,
        c.CONTACT_FIRST_NAME,
        c.CONTACT_LAST_NAME,
        c.TITLE_NAME,
        c.EMAIL,
        c.ADDITIONAL_EMAIL,
        c.MOBILE_PHONE_NUMBER,
        c.OFFICE_PHONE_NUMBER,
        c.LINKEDIN_PROFILE_URL,
        c.FINTRX_URL as owner_fintrx_url,
        c.CONTACT_BIO,
        c.PRODUCING_ADVISOR,
        c.ACTIVE,
        c.PRIMARY_FIRM,
        c.PRIMARY_FIRM_START_DATE,
        c.CONTACT_OWNERSHIP_PERCENTAGE,
        c.REP_LICENSES,
        c.INDUSTRY_TENURE_MONTHS,
        c.PRIMARY_LOCATION_CITY,
        c.PRIMARY_LOCATION_STATE,
        c.INVESTMENT_COMMITTEE_MEMBER,
        c.CONTACT_ROLES,
        c.UNIVERSITY_NAMES,
        c.ACCOLADES,
        c.LATEST_UPDATE as contact_latest_update,
        
        -- Ownership verification: Extract numeric ownership percentage
        CASE 
            WHEN c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%100%' OR c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%75% or more%' THEN 75
            WHEN c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%50% but less than 75%' THEN 62.5
            WHEN c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%25% but less than 50%' THEN 37.5
            WHEN c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%10% but less than 25%' THEN 17.5
            WHEN c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%5% but less than 10%' THEN 7.5
            WHEN c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%less than 5%' THEN 2.5
            WHEN c.CONTACT_OWNERSHIP_PERCENTAGE = 'No Ownership' THEN 0
            ELSE NULL
        END as ownership_pct_numeric,
        
        -- Title-based owner identification (Tier 1F logic)
        CASE 
            WHEN (
                UPPER(c.TITLE_NAME) LIKE '%FOUNDER%'
                OR UPPER(c.TITLE_NAME) LIKE '%CEO%'
                OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%'
                OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%'
                OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%' AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%')
                OR UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%'
                OR (UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%' AND UPPER(c.TITLE_NAME) LIKE '%WEALTH%')
            ) THEN 1 ELSE 0 
        END as is_owner_title,
        
        -- Exclude non-decision makers (V3.2.1 logic)
        CASE 
            WHEN (
                (UPPER(c.TITLE_NAME) LIKE '%COO%' AND UPPER(c.TITLE_NAME) NOT LIKE '%PARTNER%')
                OR (UPPER(c.TITLE_NAME) LIKE '%CCO%' AND UPPER(c.TITLE_NAME) NOT LIKE '%PARTNER%')
                OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS%'
                OR UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE%' AND UPPER(c.TITLE_NAME) NOT LIKE '%PARTNER%'
                OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE%'
                OR UPPER(c.TITLE_NAME) LIKE '%ASSISTANT%'
                OR UPPER(c.TITLE_NAME) LIKE '%PARAPLANNER%'
            ) THEN 1 ELSE 0 
        END as is_excluded_title,
        
        -- CFP/CFA certification boost (Tier 1A logic)
        CASE 
            WHEN (
                UPPER(c.CONTACT_BIO) LIKE '%CFP%'
                OR UPPER(c.TITLE_NAME) LIKE '%CFP%'
                OR UPPER(c.CONTACT_BIO) LIKE '%CFA%'
                OR UPPER(c.TITLE_NAME) LIKE '%CFA%'
            ) THEN 1 ELSE 0 
        END as has_certification,
        
        -- Smart producing advisor filter
        CASE 
            WHEN c.PRODUCING_ADVISOR = TRUE THEN 1
            WHEN c.PRODUCING_ADVISOR = FALSE AND (
                UPPER(c.TITLE_NAME) LIKE '%FOUNDER%'
                OR UPPER(c.TITLE_NAME) LIKE '%CEO%'
                OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%'
                OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%'
                OR UPPER(c.TITLE_NAME) LIKE '%MANAGING PARTNER%'
            ) THEN 1  -- Include founders/CEOs even if not marked as producing
            ELSE 0
        END as passes_producing_filter
        
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    INNER JOIN qualified_firms qf ON c.PRIMARY_FIRM = qf.CRD_ID
    WHERE c.ACTIVE = TRUE
      AND (
          -- Owner title check
          (
              UPPER(c.TITLE_NAME) LIKE '%FOUNDER%'
              OR UPPER(c.TITLE_NAME) LIKE '%CEO%'
              OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%'
              OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%'
              OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%' AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%')
              OR UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%'
              OR (UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%' AND UPPER(c.TITLE_NAME) LIKE '%WEALTH%')
          )
      )
      -- Ownership verification: >5% or owner title
      AND (
          c.CONTACT_OWNERSHIP_PERCENTAGE NOT IN ('No Ownership', 'less than 5%')
          OR c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%5%'
          OR c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%10%'
          OR c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%25%'
          OR c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%50%'
          OR c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%75%'
          OR c.CONTACT_OWNERSHIP_PERCENTAGE LIKE '%100%'
          OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%'
          OR UPPER(c.TITLE_NAME) LIKE '%CEO%'
          OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%'
      )
      -- Exclude non-decision makers
      AND NOT (
          (UPPER(c.TITLE_NAME) LIKE '%COO%' AND UPPER(c.TITLE_NAME) NOT LIKE '%PARTNER%')
          OR (UPPER(c.TITLE_NAME) LIKE '%CCO%' AND UPPER(c.TITLE_NAME) NOT LIKE '%PARTNER%')
          OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS%'
          OR (UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE%' AND UPPER(c.TITLE_NAME) NOT LIKE '%PARTNER%')
          OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE%'
          OR UPPER(c.TITLE_NAME) LIKE '%ASSISTANT%'
          OR UPPER(c.TITLE_NAME) LIKE '%PARAPLANNER%'
      )
),

-- ============================================================================
-- PHASE 3: QUALITY CONTROL & FINAL SELECTION
-- ============================================================================
final_owners AS (
    SELECT 
        oc.*,
        qf.*,
        
        -- CWG Match Score (High/Med)
        CASE 
            WHEN qf.NUM_OF_EMPLOYEES <= 10 
                 AND qf.hnw_aum_pct >= 70 
                 AND qf.active_producing_reps <= 10 
                 AND oc.ownership_pct_numeric >= 25
            THEN 'High'
            WHEN qf.NUM_OF_EMPLOYEES <= 15 
                 AND qf.hnw_aum_pct >= 50 
                 AND oc.ownership_pct_numeric >= 10
            THEN 'Med'
            ELSE 'Low'
        END as cwg_match_score,
        
        -- Priority rank (for sorting)
        CASE 
            WHEN qf.primary_custodian = 'Fidelity' THEN 1
            WHEN qf.primary_custodian = 'Both' THEN 2
            WHEN qf.primary_custodian = 'Schwab' THEN 3
            ELSE 4
        END as custodian_priority
        
    FROM owner_candidates oc
    INNER JOIN qualified_firms qf ON oc.PRIMARY_FIRM = qf.CRD_ID
    WHERE oc.is_owner_title = 1
      AND oc.is_excluded_title = 0
      AND oc.passes_producing_filter = 1
)

-- ============================================================================
-- FINAL OUTPUT: Sorted by Custodian (Fidelity First), then AUM (Descending)
-- ============================================================================
SELECT 
    -- Firm Information
    final_owners.firm_name,
    final_owners.CRD_ID as firm_crd,
    final_owners.TOTAL_AUM as firm_aum,
    final_owners.DISCRETIONARY_AUM,
    final_owners.NON_DISCRETIONARY_AUM,
    final_owners.AUM_YOY as firm_aum_yoy_pct,
    final_owners.AUM_3YOY as firm_aum_3yoy_pct,
    final_owners.AUM_5YOY as firm_aum_5yoy_pct,
    
    -- Headcount
    final_owners.NUM_OF_EMPLOYEES as total_employees,
    final_owners.advisory_employees,
    final_owners.active_producing_reps,
    
    -- Custodian
    final_owners.primary_custodian,
    final_owners.CUSTODIAN_PRIMARY_BUSINESS_NAME as custodian_details,
    
    -- Owner/Founder Information
    final_owners.CONTACT_FIRST_NAME as owner_first_name,
    final_owners.CONTACT_LAST_NAME as owner_last_name,
    CONCAT(final_owners.CONTACT_FIRST_NAME, ' ', final_owners.CONTACT_LAST_NAME) as owner_full_name,
    final_owners.TITLE_NAME as owner_title,
    final_owners.CONTACT_OWNERSHIP_PERCENTAGE as ownership_percentage,
    final_owners.ownership_pct_numeric,
    final_owners.RIA_CONTACT_CRD_ID as owner_crd,
    
    -- Contact Information
    final_owners.EMAIL as owner_email,
    final_owners.ADDITIONAL_EMAIL,
    final_owners.MOBILE_PHONE_NUMBER,
    final_owners.OFFICE_PHONE_NUMBER,
    final_owners.LINKEDIN_PROFILE_URL,
    final_owners.owner_fintrx_url,
    final_owners.firm_fintrx_url,
    
    -- Professional Details
    final_owners.PRODUCING_ADVISOR,
    final_owners.INDUSTRY_TENURE_MONTHS,
    final_owners.PRIMARY_FIRM_START_DATE as owner_firm_start_date,
    final_owners.REP_LICENSES,
    final_owners.CONTACT_BIO,
    final_owners.has_certification,
    final_owners.INVESTMENT_COMMITTEE_MEMBER,
    final_owners.CONTACT_ROLES,
    final_owners.UNIVERSITY_NAMES,
    final_owners.ACCOLADES,
    
    -- Location
    final_owners.PRIMARY_LOCATION_CITY as owner_city,
    final_owners.PRIMARY_LOCATION_STATE as owner_state,
    final_owners.MAIN_OFFICE_CITY_NAME as firm_city,
    final_owners.MAIN_OFFICE_STATE as firm_state,
    final_owners.MAIN_OFFICE_ADDRESS_1,
    final_owners.MAIN_OFFICE_ADDRESS_2,
    final_owners.ZIP_CODE,
    final_owners.PHONE as firm_phone,
    
    -- Firm Characteristics
    final_owners.hnw_aum_pct,
    final_owners.ENTITY_CLASSIFICATION,
    final_owners.CLIENT_BASE,
    final_owners.FEE_STRUCTURE,
    final_owners.TOTAL_ACCOUNTS,
    final_owners.TOTAL_DISCRETIONARY_ACCOUNTS,
    final_owners.AVERAGE_ACCOUNT_SIZE,
    final_owners.INVESTMENTS_UTILIZED,
    final_owners.CAPITAL_ALLOCATOR,
    final_owners.ACTIVE_ESG_INVESTOR,
    final_owners.TAMP_AND_TECH_USED,
    final_owners.TEAM_PAGE,
    
    -- Match Score
    final_owners.cwg_match_score,
    
    -- Metadata
    final_owners.firm_latest_update,
    final_owners.contact_latest_update

FROM final_owners
WHERE final_owners.cwg_match_score IN ('High', 'Med')  -- Only High and Med matches
ORDER BY 
    final_owners.custodian_priority,  -- Fidelity first
    final_owners.TOTAL_AUM DESC,  -- Then by AUM descending
    final_owners.ownership_pct_numeric DESC  -- Then by ownership percentage

