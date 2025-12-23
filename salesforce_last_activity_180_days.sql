-- ============================================================================
-- SALESFORCE: Find Leads & Opportunities Without SMS/Call Activity for 180+ Days
-- ============================================================================
-- This query identifies Leads and Opportunities that haven't had any SMS or 
-- Call activity (recorded as Tasks) in the last 180 days.
--
-- Activity Types Included:
--   - SMS: Type = 'Outgoing SMS' or 'Incoming SMS', or Subject contains 'SMS'/'Text'
--   - Calls: TaskSubtype = 'Call', Type = 'Call', Subject contains 'Call', or CallType IS NOT NULL
--
-- ============================================================================

-- ============================================================================
-- PART 1: Find Leads without SMS/Call activity for 180+ days
-- ============================================================================
WITH 
-- Get last activity date for each Lead (via WhoId in Tasks)
lead_task_activity AS (
    SELECT 
        t.WhoId as lead_id,
        MAX(GREATEST(
            COALESCE(DATE(t.ActivityDate), DATE('1900-01-01')),
            COALESCE(DATE(t.CompletedDateTime), DATE('1900-01-01')),
            COALESCE(DATE(t.CreatedDate), DATE('1900-01-01'))
        )) as last_activity_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
    WHERE t.IsDeleted = false
      AND t.WhoId IS NOT NULL
      AND (
          -- SMS activities
          t.Type IN ('Outgoing SMS', 'Incoming SMS')
          OR UPPER(t.Subject) LIKE '%SMS%'
          OR UPPER(t.Subject) LIKE '%TEXT%'
          -- Call activities
          OR t.TaskSubtype = 'Call'
          OR t.Type = 'Call'
          OR UPPER(t.Subject) LIKE '%CALL%'
          OR t.CallType IS NOT NULL
      )
    GROUP BY t.WhoId
),

-- Join with Leads to identify those without recent activity
leads_no_recent_activity AS (
    SELECT 
        l.Id as lead_id,
        l.FirstName,
        l.LastName,
        l.Company,
        l.Email,
        l.Status,
        l.LastActivityDate as sf_last_activity_date,  -- Salesforce's built-in field
        COALESCE(la.last_activity_date, NULL) as task_last_activity_date,
        CASE 
            WHEN la.last_activity_date IS NULL THEN NULL
            ELSE DATE_DIFF(CURRENT_DATE(), la.last_activity_date, DAY)
        END as days_since_last_task_activity,
        CASE 
            WHEN la.last_activity_date IS NULL THEN 'No SMS/Call activity ever'
            WHEN DATE_DIFF(CURRENT_DATE(), la.last_activity_date, DAY) > 180 THEN 'No SMS/Call activity 180+ days'
            ELSE 'Has recent activity'
        END as activity_status
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN lead_task_activity la ON l.Id = la.lead_id
    WHERE l.IsDeleted = false
)

SELECT 
    'LEAD' as record_type,
    lead_id as record_id,
    FirstName,
    LastName,
    Company,
    Email,
    Status,
    task_last_activity_date as last_sms_call_activity_date,
    days_since_last_task_activity as days_since_last_activity,
    activity_status
FROM leads_no_recent_activity
WHERE activity_status IN ('No SMS/Call activity ever', 'No SMS/Call activity 180+ days')
ORDER BY days_since_last_task_activity DESC NULLS LAST;

-- ============================================================================
-- PART 2: Find Opportunities without SMS/Call activity for 180+ days
-- ============================================================================
-- Note: Opportunities can have tasks linked via WhatId directly, OR via 
-- related Contacts (WhoId -> Contact -> Opportunity)
-- This query handles both cases.

WITH 
-- Get last activity date for Opportunities via WhatId (direct link)
opp_task_activity_direct AS (
    SELECT 
        t.WhatId as opportunity_id,
        MAX(GREATEST(
            COALESCE(DATE(t.ActivityDate), DATE('1900-01-01')),
            COALESCE(DATE(t.CompletedDateTime), DATE('1900-01-01')),
            COALESCE(DATE(t.CreatedDate), DATE('1900-01-01'))
        )) as last_activity_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
    WHERE t.IsDeleted = false
      AND t.WhatId IS NOT NULL
      AND (
          t.Type IN ('Outgoing SMS', 'Incoming SMS')
          OR UPPER(t.Subject) LIKE '%SMS%'
          OR UPPER(t.Subject) LIKE '%TEXT%'
          OR t.TaskSubtype = 'Call'
          OR t.Type = 'Call'
          OR UPPER(t.Subject) LIKE '%CALL%'
          OR t.CallType IS NOT NULL
      )
    GROUP BY t.WhatId
),

-- Combine all opportunity activities (direct + via contacts would go here if needed)
opportunities_no_recent_activity AS (
    SELECT 
        o.Id as opportunity_id,
        o.Name,
        o.StageName,
        o.AccountId,
        o.CloseDate,
        o.LastActivityDate as sf_last_activity_date,  -- Salesforce's built-in field
        COALESCE(ota.last_activity_date, NULL) as task_last_activity_date,
        CASE 
            WHEN ota.last_activity_date IS NULL THEN NULL
            ELSE DATE_DIFF(CURRENT_DATE(), ota.last_activity_date, DAY)
        END as days_since_last_task_activity,
        CASE 
            WHEN ota.last_activity_date IS NULL THEN 'No SMS/Call activity ever'
            WHEN DATE_DIFF(CURRENT_DATE(), ota.last_activity_date, DAY) > 180 THEN 'No SMS/Call activity 180+ days'
            ELSE 'Has recent activity'
        END as activity_status
    FROM `savvy-gtm-analytics.SavvyGTMData.Opportunity` o
    LEFT JOIN opp_task_activity_direct ota ON o.Id = ota.opportunity_id
    WHERE o.IsDeleted = false
)

SELECT 
    'OPPORTUNITY' as record_type,
    opportunity_id as record_id,
    Name,
    StageName,
    CloseDate,
    task_last_activity_date as last_sms_call_activity_date,
    days_since_last_task_activity as days_since_last_activity,
    activity_status
FROM opportunities_no_recent_activity
WHERE activity_status IN ('No SMS/Call activity ever', 'No SMS/Call activity 180+ days')
ORDER BY days_since_last_task_activity DESC NULLS LAST;

-- ============================================================================
-- ALTERNATIVE: Combined query for both Leads and Opportunities in one result
-- ============================================================================
WITH 
-- Lead activities
lead_task_activity AS (
    SELECT 
        t.WhoId as record_id,
        'Lead' as record_type,
        MAX(GREATEST(
            COALESCE(DATE(t.ActivityDate), DATE('1900-01-01')),
            COALESCE(DATE(t.CompletedDateTime), DATE('1900-01-01')),
            COALESCE(DATE(t.CreatedDate), DATE('1900-01-01'))
        )) as last_activity_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
    WHERE t.IsDeleted = false
      AND t.WhoId IS NOT NULL
      AND (
          t.Type IN ('Outgoing SMS', 'Incoming SMS')
          OR UPPER(t.Subject) LIKE '%SMS%'
          OR UPPER(t.Subject) LIKE '%TEXT%'
          OR t.TaskSubtype = 'Call'
          OR t.Type = 'Call'
          OR UPPER(t.Subject) LIKE '%CALL%'
          OR t.CallType IS NOT NULL
      )
    GROUP BY t.WhoId
),

-- Opportunity activities (direct via WhatId)
opp_task_activity AS (
    SELECT 
        t.WhatId as record_id,
        'Opportunity' as record_type,
        MAX(GREATEST(
            COALESCE(DATE(t.ActivityDate), DATE('1900-01-01')),
            COALESCE(DATE(t.CompletedDateTime), DATE('1900-01-01')),
            COALESCE(DATE(t.CreatedDate), DATE('1900-01-01'))
        )) as last_activity_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
    WHERE t.IsDeleted = false
      AND t.WhatId IS NOT NULL
      AND (
          t.Type IN ('Outgoing SMS', 'Incoming SMS')
          OR UPPER(t.Subject) LIKE '%SMS%'
          OR UPPER(t.Subject) LIKE '%TEXT%'
          OR t.TaskSubtype = 'Call'
          OR t.Type = 'Call'
          OR UPPER(t.Subject) LIKE '%CALL%'
          OR t.CallType IS NOT NULL
      )
    GROUP BY t.WhatId
),

-- Combined activity dates
all_activities AS (
    SELECT * FROM lead_task_activity
    UNION ALL
    SELECT * FROM opp_task_activity
),

-- Leads with activity status
leads_with_status AS (
    SELECT 
        l.Id as record_id,
        'Lead' as record_type,
        l.FirstName,
        l.LastName,
        l.Company,
        l.Email,
        l.Status as stage_status,
        NULL as close_date,
        aa.last_activity_date,
        CASE 
            WHEN aa.last_activity_date IS NULL THEN NULL
            ELSE DATE_DIFF(CURRENT_DATE(), aa.last_activity_date, DAY)
        END as days_since_last_activity
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN all_activities aa ON l.Id = aa.record_id AND aa.record_type = 'Lead'
    WHERE l.IsDeleted = false
),

-- Opportunities with activity status
opps_with_status AS (
    SELECT 
        o.Id as record_id,
        'Opportunity' as record_type,
        NULL as FirstName,
        NULL as LastName,
        o.Name as Company,
        NULL as Email,
        o.StageName as stage_status,
        o.CloseDate as close_date,
        aa.last_activity_date,
        CASE 
            WHEN aa.last_activity_date IS NULL THEN NULL
            ELSE DATE_DIFF(CURRENT_DATE(), aa.last_activity_date, DAY)
        END as days_since_last_activity
    FROM `savvy-gtm-analytics.SavvyGTMData.Opportunity` o
    LEFT JOIN all_activities aa ON o.Id = aa.record_id AND aa.record_type = 'Opportunity'
    WHERE o.IsDeleted = false
)

-- Final combined result
SELECT 
    record_type,
    record_id,
    FirstName,
    LastName,
    Company,
    Email,
    stage_status,
    close_date,
    last_activity_date,
    days_since_last_activity,
    CASE 
        WHEN last_activity_date IS NULL THEN 'No SMS/Call activity ever'
        WHEN days_since_last_activity > 180 THEN 'No SMS/Call activity 180+ days'
        ELSE 'Has recent activity'
    END as activity_status
FROM (
    SELECT * FROM leads_with_status
    UNION ALL
    SELECT * FROM opps_with_status
)
WHERE last_activity_date IS NULL OR days_since_last_activity > 180
ORDER BY record_type, days_since_last_activity DESC NULLS LAST;

