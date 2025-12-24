-- ============================================================================
-- STEP 2: ADD CONVERSION OUTCOMES TO HISTORICAL LEADS
-- Purpose: Identify which leads converted to MQL
-- ============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.historical_leads_with_outcomes` AS

WITH 
-- Get historical leads from Step 1
historical_leads AS (
    SELECT * FROM `savvy-gtm-analytics.ml_features.historical_leads_with_tiers`
),

-- Get MQL conversions from Lead table
-- MQL status typically: 'MQL', 'Marketing Qualified', 'Qualified', etc.
-- Also check for Stage_Entered_Call_Scheduled__c as conversion indicator
mql_conversions AS (
    SELECT DISTINCT
        l.Id as lead_id,
        1 as converted_to_mql,
        l.Status as final_status,
        DATE(l.Stage_Entered_Call_Scheduled__c) as conversion_date,
        DATE(l.LastModifiedDate) as status_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND (
          -- MQL status indicators
          l.Status IN ('MQL', 'Marketing Qualified', 'Qualified', 'Sales Qualified', 
                       'Working', 'Contacted - Interested', 'Meeting Scheduled',
                       'Opportunity', 'Converted')
          OR l.IsConverted = true
          OR l.Stage_Entered_Call_Scheduled__c IS NOT NULL  -- Call scheduled = conversion
      )
)

SELECT 
    hl.*,
    COALESCE(mc.converted_to_mql, 0) as converted_to_mql,
    mc.final_status,
    mc.conversion_date,
    CASE 
        WHEN mc.conversion_date IS NOT NULL AND hl.first_contact_date IS NOT NULL
        THEN DATE_DIFF(mc.conversion_date, hl.first_contact_date, DAY)
        ELSE NULL
    END as days_to_conversion
FROM historical_leads hl
LEFT JOIN mql_conversions mc ON hl.lead_id = mc.lead_id;

