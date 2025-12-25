-- ============================================================================
-- CLOSED/LOST LEADS WITH SUBSEQUENT FIRM CHANGES
-- Identifies leads we contacted but didn't close, who later changed firms
-- ============================================================================

WITH 
-- Step 1: Get all leads we've contacted (Provided Lead List)
contacted_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd_clean,
        l.FirstName,
        l.LastName,
        l.Company as company_at_contact,
        l.LeadSource,
        l.Status,
        l.stage_entered_contacting__c as contacted_date,
        l.Stage_Entered_Call_Scheduled__c as call_scheduled_date,
        l.Stage_Entered_Closed__c as closed_date,
        l.Disposition__c,
        l.DoNotCall,
        l.CreatedDate,
        -- Determine outcome (using correct fields from recycling_infrastructure.md)
        CASE 
            WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 'CONVERTED_MQL'
            WHEN l.Status = 'Closed' THEN 'CLOSED_LOST'
            WHEN l.Status IN ('Contacting', 'New', 'Nurture', 'Qualified', 'Replied') THEN 'ACTIVE'
            ELSE 'OTHER'
        END as outcome,
        -- Days since contact
        DATE_DIFF(CURRENT_DATE(), DATE(l.stage_entered_contacting__c), DAY) as days_since_contact
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.LeadSource LIKE '%Provided Lead List%'
      AND l.stage_entered_contacting__c IS NOT NULL
      AND DATE(l.stage_entered_contacting__c) >= '2022-01-01'  -- 3 years of history
      AND l.IsDeleted = false
),

-- Step 2: Get employment history for these advisors (PIT-compliant)
-- Find NEXT firm change AFTER we contacted them
next_firm_changes AS (
    SELECT 
        cl.lead_id,
        cl.crd_clean,
        cl.contacted_date,
        cl.outcome,
        -- Find the NEXT firm they joined after contact date
        MIN(CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE(cl.contacted_date) 
            THEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE 
        END) as next_firm_start_date,
        -- Get firm name from current snapshot
        c.PRIMARY_FIRM_NAME as current_firm_name,
        c.PRIMARY_FIRM_START_DATE as current_firm_start_date,
        -- Get previous firm name (at time of contact)
        eh_contact.PREVIOUS_REGISTRATION_COMPANY_NAME as firm_at_contact
    FROM contacted_leads cl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON cl.crd_clean = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE(cl.contacted_date)  -- Started AFTER contact
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c 
        ON cl.crd_clean = c.RIA_CONTACT_CRD_ID
    -- Get firm at time of contact (PIT-compliant)
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_contact
        ON cl.crd_clean = eh_contact.RIA_CONTACT_CRD_ID
        AND eh_contact.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(cl.contacted_date)
        AND (eh_contact.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh_contact.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(cl.contacted_date))
    WHERE cl.crd_clean IS NOT NULL
    GROUP BY cl.lead_id, cl.crd_clean, cl.contacted_date, cl.outcome, 
             c.PRIMARY_FIRM_NAME, c.PRIMARY_FIRM_START_DATE, eh_contact.PREVIOUS_REGISTRATION_COMPANY_NAME
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY cl.lead_id 
        ORDER BY eh_contact.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
    ) = 1
),

-- Step 3: Find firm changes AFTER we contacted them
leads_with_firm_changes AS (
    SELECT 
        cl.*,
        nfc.firm_at_contact,
        nfc.current_firm_name,
        nfc.next_firm_start_date as joined_new_firm_date,
        nfc.current_firm_start_date,
        -- Calculate timing (days from contact to new firm start)
        DATE_DIFF(DATE(COALESCE(nfc.next_firm_start_date, nfc.current_firm_start_date)), 
                  DATE(cl.contacted_date), DAY) as days_contact_to_move,
        -- Flag if they moved AFTER we contacted them
        CASE 
            WHEN nfc.next_firm_start_date IS NOT NULL 
                 AND DATE(nfc.next_firm_start_date) > DATE(cl.contacted_date) THEN TRUE
            WHEN nfc.current_firm_start_date IS NOT NULL 
                 AND DATE(nfc.current_firm_start_date) > DATE(cl.contacted_date) THEN TRUE
            ELSE FALSE
        END as moved_after_contact,
        -- Flag if they changed firms (firm name different)
        CASE 
            WHEN nfc.current_firm_name IS NOT NULL 
                 AND nfc.firm_at_contact IS NOT NULL
                 AND UPPER(nfc.firm_at_contact) != UPPER(nfc.current_firm_name)
                 AND DATE(COALESCE(nfc.next_firm_start_date, nfc.current_firm_start_date)) > DATE(cl.contacted_date)
            THEN TRUE
            ELSE FALSE
        END as changed_firms_since_contact
    FROM contacted_leads cl
    LEFT JOIN next_firm_changes nfc 
        ON cl.lead_id = nfc.lead_id
)

-- Final output: All leads with firm change analysis
SELECT 
    lead_id,
    crd_clean as advisor_crd,
    FirstName,
    LastName,
    company_at_contact,
    outcome,
    contacted_date,
    days_since_contact,
    firm_at_contact,
    current_firm_name,
    joined_new_firm_date,
    days_contact_to_move,
    changed_firms_since_contact,
    moved_after_contact,
    -- Categorize the timing
    CASE 
        WHEN NOT moved_after_contact THEN 'MOVED_BEFORE_CONTACT'
        WHEN days_contact_to_move IS NULL THEN 'NO_MOVE_DETECTED'
        WHEN days_contact_to_move <= 30 THEN 'MOVED_WITHIN_30_DAYS'
        WHEN days_contact_to_move <= 60 THEN 'MOVED_31-60_DAYS'
        WHEN days_contact_to_move <= 90 THEN 'MOVED_61-90_DAYS'
        WHEN days_contact_to_move <= 180 THEN 'MOVED_91-180_DAYS'
        WHEN days_contact_to_move <= 365 THEN 'MOVED_181-365_DAYS'
        ELSE 'MOVED_AFTER_1_YEAR'
    END as move_timing_category
FROM leads_with_firm_changes
WHERE moved_after_contact = TRUE  -- Focus on those who moved AFTER we contacted
  AND days_contact_to_move IS NOT NULL
ORDER BY days_contact_to_move ASC;

