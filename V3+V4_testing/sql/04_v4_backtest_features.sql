-- ============================================================================
-- STEP 4.1: V4 FEATURES FOR HISTORICAL LEADS (PIT-COMPLIANT)
-- Purpose: Calculate V4 model features for historical leads AS OF their first_contact_date
-- ============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.historical_leads_v4_features` AS

WITH 
-- ============================================================================
-- BASE: Get historical leads with first_contact_date
-- ============================================================================
base AS (
    SELECT 
        lead_id,
        crd as advisor_crd,
        first_contact_date as contacted_date
    FROM `savvy-gtm-analytics.ml_features.historical_leads_with_outcomes`
),

-- ============================================================================
-- FEATURE GROUP 1: TENURE FEATURES
-- ============================================================================
history_firm AS (
    SELECT 
        b.lead_id,
        b.contacted_date,
        b.advisor_crd,
        eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
        eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE as firm_start_date,
        DATE_DIFF(b.contacted_date, eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE, MONTH) as tenure_months
    FROM base b
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON b.advisor_crd = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= b.contacted_date
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= b.contacted_date)
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY b.lead_id 
        ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
    ) = 1
),

current_snapshot AS (
    SELECT 
        b.lead_id,
        b.contacted_date,
        b.advisor_crd,
        c.LATEST_REGISTERED_EMPLOYMENT_COMPANY_CRD_ID as firm_crd,
        c.LATEST_REGISTERED_EMPLOYMENT_START_DATE as firm_start_date,
        CASE 
            WHEN c.LATEST_REGISTERED_EMPLOYMENT_START_DATE <= b.contacted_date 
            THEN DATE_DIFF(b.contacted_date, c.LATEST_REGISTERED_EMPLOYMENT_START_DATE, MONTH)
            ELSE NULL
        END as tenure_months
    FROM base b
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON b.advisor_crd = c.RIA_CONTACT_CRD_ID
    WHERE c.LATEST_REGISTERED_EMPLOYMENT_START_DATE IS NOT NULL
      AND c.LATEST_REGISTERED_EMPLOYMENT_START_DATE <= b.contacted_date
),

current_firm AS (
    SELECT 
        COALESCE(hf.lead_id, cs.lead_id) as lead_id,
        COALESCE(hf.contacted_date, cs.contacted_date) as contacted_date,
        COALESCE(hf.advisor_crd, cs.advisor_crd) as advisor_crd,
        COALESCE(hf.firm_crd, cs.firm_crd) as firm_crd,
        COALESCE(hf.firm_start_date, cs.firm_start_date) as firm_start_date,
        COALESCE(hf.tenure_months, cs.tenure_months) as tenure_months
    FROM history_firm hf
    FULL OUTER JOIN current_snapshot cs
        ON hf.lead_id = cs.lead_id
    WHERE COALESCE(hf.lead_id, cs.lead_id) IS NOT NULL
),

industry_tenure AS (
    SELECT
        cf.lead_id,
        COALESCE((
            SELECT SUM(
                DATE_DIFF(
                    COALESCE(eh2.PREVIOUS_REGISTRATION_COMPANY_END_DATE, cf.contacted_date),
                    eh2.PREVIOUS_REGISTRATION_COMPANY_START_DATE,
                    MONTH
                )
            )
            FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh2
            WHERE eh2.RIA_CONTACT_CRD_ID = cf.advisor_crd
                AND eh2.PREVIOUS_REGISTRATION_COMPANY_START_DATE < cf.firm_start_date
                AND (eh2.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
                     OR eh2.PREVIOUS_REGISTRATION_COMPANY_END_DATE <= cf.contacted_date)
        ), 0) as industry_tenure_months
    FROM current_firm cf
    WHERE cf.firm_start_date IS NOT NULL
),

-- ============================================================================
-- FEATURE GROUP 2: MOBILITY FEATURES
-- ============================================================================
mobility AS (
    SELECT 
        b.lead_id,
        b.contacted_date,
        COUNT(DISTINCT CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(b.contacted_date, INTERVAL 3 YEAR)
                AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE < b.contacted_date
            THEN eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID 
        END) as mobility_3yr
    FROM base b
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON b.advisor_crd = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE < b.contacted_date
    GROUP BY b.lead_id, b.contacted_date
),

-- ============================================================================
-- FEATURE GROUP 3: FIRM STABILITY FEATURES
-- ============================================================================
firm_stability AS (
    SELECT
        cf.lead_id,
        cf.contacted_date,
        cf.firm_crd,
        -- Firm rep count at contact
        COALESCE((
            SELECT COUNT(DISTINCT eh_current.RIA_CONTACT_CRD_ID)
            FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_current
            WHERE eh_current.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = cf.firm_crd
              AND eh_current.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= cf.contacted_date
              AND (eh_current.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL OR eh_current.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= cf.contacted_date)
        ), 0) as firm_rep_count_at_contact,
        -- Departures in 12 months before contact
        COALESCE((
            SELECT COUNT(DISTINCT eh_d.RIA_CONTACT_CRD_ID)
            FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_d
            WHERE eh_d.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = cf.firm_crd
              AND eh_d.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(cf.contacted_date, INTERVAL 12 MONTH)
              AND eh_d.PREVIOUS_REGISTRATION_COMPANY_END_DATE < cf.contacted_date
              AND eh_d.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
        ), 0) as firm_departures_12mo,
        -- Arrivals in 12 months before contact
        COALESCE((
            SELECT COUNT(DISTINCT eh_a.RIA_CONTACT_CRD_ID)
            FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_a
            WHERE eh_a.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = cf.firm_crd
              AND eh_a.PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(cf.contacted_date, INTERVAL 12 MONTH)
              AND eh_a.PREVIOUS_REGISTRATION_COMPANY_START_DATE < cf.contacted_date
        ), 0) as firm_arrivals_12mo
    FROM current_firm cf
    WHERE cf.firm_crd IS NOT NULL
),

-- ============================================================================
-- FEATURE GROUP 4: WIREHOUSE & BROKER PROTOCOL
-- ============================================================================
wirehouse AS (
    SELECT 
        cf.lead_id,
        CASE 
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%MERRILL%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%MORGAN STANLEY%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%UBS%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%WELLS FARGO%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%EDWARD JONES%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%RAYMOND JAMES%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%AMERIPRISE%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%LPL%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%NORTHWESTERN MUTUAL%' THEN 1
            WHEN UPPER(c.PRIMARY_FIRM_NAME) LIKE '%STIFEL%' THEN 1
            ELSE 0
        END as is_wirehouse
    FROM current_firm cf
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON cf.advisor_crd = c.RIA_CONTACT_CRD_ID
),

broker_protocol AS (
    SELECT DISTINCT
        cf.lead_id,
        CASE WHEN bp.firm_crd_id IS NOT NULL THEN 1 ELSE 0 END as is_broker_protocol
    FROM current_firm cf
    LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members` bp
        ON cf.firm_crd = bp.firm_crd_id
),

-- ============================================================================
-- FEATURE GROUP 5: EXPERIENCE
-- ============================================================================
experience AS (
    SELECT 
        b.lead_id,
        COALESCE(it.industry_tenure_months, c.INDUSTRY_TENURE_MONTHS, 0) / 12.0 as experience_years,
        CASE WHEN COALESCE(it.industry_tenure_months, c.INDUSTRY_TENURE_MONTHS) IS NULL THEN 1 ELSE 0 END as is_experience_missing
    FROM base b
    LEFT JOIN industry_tenure it ON b.lead_id = it.lead_id
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON b.advisor_crd = c.RIA_CONTACT_CRD_ID
),

-- ============================================================================
-- FEATURE GROUP 6: DATA QUALITY FLAGS
-- ============================================================================
data_quality AS (
    SELECT
        b.lead_id,
        CASE WHEN l.Email IS NOT NULL THEN 1 ELSE 0 END as has_email,
        CASE WHEN l.LinkedIn_Profile_Apollo__c IS NOT NULL THEN 1 ELSE 0 END as has_linkedin
    FROM base b
    LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
        ON b.lead_id = l.Id
),

-- ============================================================================
-- COMBINE ALL FEATURES (14 final features)
-- ============================================================================
all_features AS (
    SELECT
        b.lead_id,
        b.advisor_crd,
        b.contacted_date,
        
        -- 1. tenure_bucket
        CASE 
            WHEN cf.tenure_months IS NULL THEN 'Unknown'
            WHEN cf.tenure_months < 12 THEN '0-12'
            WHEN cf.tenure_months < 24 THEN '12-24'
            WHEN cf.tenure_months < 48 THEN '24-48'
            WHEN cf.tenure_months < 120 THEN '48-120'
            ELSE '120+'
        END as tenure_bucket,
        
        -- 2. experience_bucket
        CASE 
            WHEN e.experience_years < 5 THEN '0-5'
            WHEN e.experience_years < 10 THEN '5-10'
            WHEN e.experience_years < 15 THEN '10-15'
            WHEN e.experience_years < 20 THEN '15-20'
            ELSE '20+'
        END as experience_bucket,
        
        -- 3. is_experience_missing
        e.is_experience_missing,
        
        -- 4. mobility_tier
        CASE 
            WHEN COALESCE(m.mobility_3yr, 0) = 0 THEN 'Stable'
            WHEN COALESCE(m.mobility_3yr, 0) = 1 THEN 'Low_Mobility'
            ELSE 'High_Mobility'
        END as mobility_tier,
        
        -- 5. firm_rep_count_at_contact
        COALESCE(fs.firm_rep_count_at_contact, 0) as firm_rep_count_at_contact,
        
        -- 6. firm_net_change_12mo
        COALESCE(fs.firm_arrivals_12mo, 0) - COALESCE(fs.firm_departures_12mo, 0) as firm_net_change_12mo,
        
        -- 7. firm_stability_tier
        CASE 
            WHEN cf.firm_crd IS NULL THEN 'Unknown'
            WHEN COALESCE(fs.firm_arrivals_12mo, 0) - COALESCE(fs.firm_departures_12mo, 0) < -10 THEN 'Heavy_Bleeding'
            WHEN COALESCE(fs.firm_arrivals_12mo, 0) - COALESCE(fs.firm_departures_12mo, 0) < 0 THEN 'Light_Bleeding'
            WHEN COALESCE(fs.firm_arrivals_12mo, 0) - COALESCE(fs.firm_departures_12mo, 0) = 0 THEN 'Stable'
            ELSE 'Growing'
        END as firm_stability_tier,
        
        -- 8. has_firm_data
        CASE WHEN cf.firm_crd IS NULL THEN 0 ELSE 1 END as has_firm_data,
        
        -- 9. is_wirehouse
        COALESCE(w.is_wirehouse, 0) as is_wirehouse,
        
        -- 10. is_broker_protocol
        COALESCE(bp.is_broker_protocol, 0) as is_broker_protocol,
        
        -- 11. has_email
        COALESCE(dq.has_email, 0) as has_email,
        
        -- 12. has_linkedin
        COALESCE(dq.has_linkedin, 0) as has_linkedin,
        
        -- 13. mobility_x_heavy_bleeding
        CASE 
            WHEN COALESCE(m.mobility_3yr, 0) >= 2 
                AND (COALESCE(fs.firm_arrivals_12mo, 0) - COALESCE(fs.firm_departures_12mo, 0)) < -10
            THEN 1 ELSE 0
        END as mobility_x_heavy_bleeding,
        
        -- 14. short_tenure_x_high_mobility
        CASE 
            WHEN COALESCE(cf.tenure_months, 9999) < 24 
                AND COALESCE(m.mobility_3yr, 0) >= 2
            THEN 1 ELSE 0
        END as short_tenure_x_high_mobility
        
    FROM base b
    LEFT JOIN current_firm cf ON b.lead_id = cf.lead_id
    LEFT JOIN industry_tenure it ON b.lead_id = it.lead_id
    LEFT JOIN mobility m ON b.lead_id = m.lead_id
    LEFT JOIN firm_stability fs ON b.lead_id = fs.lead_id
    LEFT JOIN wirehouse w ON b.lead_id = w.lead_id
    LEFT JOIN broker_protocol bp ON b.lead_id = bp.lead_id
    LEFT JOIN experience e ON b.lead_id = e.lead_id
    LEFT JOIN data_quality dq ON b.lead_id = dq.lead_id
)

SELECT * FROM all_features;

