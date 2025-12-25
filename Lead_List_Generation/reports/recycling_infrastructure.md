# Lead and Opportunity Recycling Infrastructure Documentation

**Generated**: December 24, 2025  
**Purpose**: Document Salesforce object fields and structures for lead/opportunity recycling logic  
**Data Source**: `savvy-gtm-analytics.SavvyGTMData` (BigQuery)

---

## Executive Summary

This document provides a comprehensive reference for identifying:
1. **Closed Leads and Opportunities** - How to determine when records are closed
2. **Do Not Call Status** - Fields that indicate leads should not be contacted
3. **Close Lost Details** - Fields containing close lost reasons, dispositions, and details
4. **Last Task Dates** - How to determine when a lead/opportunity can be recycled based on last activity

---

## 1. Identifying Closed Leads and Opportunities

### 1.1 Lead Object - Closed Status

**Primary Field**: `Status` (STRING)

**Closed Status Values**:
- `"Closed"` - Most common closed status (68,883 leads)
- Other statuses: `"Contacting"`, `"New"`, `"Nurture"`, `"Qualified"`, `"Replied"`, `"Call Scheduled"`, `"Interested"`

**Additional Closed Indicators**:
- `IsConverted` (BOOLEAN) - `true` if lead was converted to Opportunity/Contact
- `Stage_Entered_Closed__c` (TIMESTAMP) - Timestamp when lead entered "Closed" stage (may be NULL)
- `Disposition__c` (STRING) - Disposition reason (see Section 3)

**SQL Query Example**:
```sql
SELECT 
    Id,
    Status,
    IsConverted,
    Stage_Entered_Closed__c,
    Disposition__c
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE Status = 'Closed'
  AND IsDeleted = false
```

**Key Observations**:
- `Status = 'Closed'` is the primary indicator
- `IsConverted = true` means lead was successfully converted (not a loss)
- `Stage_Entered_Closed__c` provides timestamp of when closed (useful for recycling logic)

---

### 1.2 Opportunity Object - Closed Status

**Primary Fields**:
- `IsClosed` (BOOLEAN) - `true` if opportunity is closed
- `IsWon` (BOOLEAN) - `true` if opportunity was won, `false` if lost
- `StageName` (STRING) - Current stage name

**Closed Stage Values**:
- `"Closed Lost"` - Opportunity was lost (1,625 opportunities)
- `"Joined"` - Opportunity was won (102 opportunities)
- `"Re-Engaged"` - Re-engaged opportunity that was won (14 opportunities)

**Additional Closed Indicators**:
- `CloseDate` (DATE) - Date the opportunity was closed
- `Stage_Entered_Closed__c` (TIMESTAMP) - Timestamp when opportunity entered "Closed" stage
- `Closed_Lost_Checkbox__c` (BOOLEAN) - Explicit checkbox for closed lost status

**SQL Query Example**:
```sql
SELECT 
    Id,
    StageName,
    IsClosed,
    IsWon,
    CloseDate,
    Stage_Entered_Closed__c,
    Closed_Lost_Checkbox__c
FROM `savvy-gtm-analytics.SavvyGTMData.Opportunity`
WHERE IsClosed = true
  AND IsDeleted = false
```

**Key Observations**:
- `IsClosed = true` AND `IsWon = false` = Closed Lost (recyclable)
- `IsClosed = true` AND `IsWon = true` = Closed Won (not recyclable)
- `StageName = 'Closed Lost'` is the most common closed lost stage

---

## 2. Do Not Call Status

### 2.1 Lead Object - Do Not Call Fields

**Primary Field**: `DoNotCall` (BOOLEAN)
- `true` = Lead should not be called (1,043 leads)
- `false` = Lead can be called (88,140 leads)

**Additional Opt-Out Fields**:
- `HasOptedOutOfEmail` (BOOLEAN) - Email opt-out status
  - `true` = Lead opted out of emails
  - `false` = Lead can receive emails (88,140 leads)
  - Note: `HasOptedOutOfCall` field does NOT exist in the Lead object

**SQL Query Example**:
```sql
SELECT 
    Id,
    DoNotCall,
    HasOptedOutOfEmail,
    Status,
    Disposition__c
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE DoNotCall = true
  AND IsDeleted = false
```

**Key Observations**:
- `DoNotCall = true` is the primary indicator for "do not call"
- Only 1.2% of leads have `DoNotCall = true` (1,043 out of 89,183)
- `HasOptedOutOfEmail` is separate from `DoNotCall` (email vs phone)

---

### 2.2 Opportunity Object - Do Not Call Status

**Note**: Opportunity object does not have a direct `DoNotCall` field. However, you can infer "do not call" status from:
- `IsClosed = true` AND `IsWon = false` - Closed lost opportunities may be recyclable
- `Closed_Lost_Reason__c` - Some reasons may indicate permanent opt-out (see Section 3)

---

## 3. Close Lost Details, Reasons, and Disposition__c

### 3.1 Lead Object - Disposition__c Field

**Field Name**: `Disposition__c` (STRING)

**Common Disposition Values** (by frequency):
1. `"Auto-Closed by Operations"` - 31,110 leads (35%)
2. `"No Response"` - 14,492 leads (16%)
3. `"Other"` - 8,196 leads (9%)
4. `"Not Interested in Moving"` - 5,890 leads (7%)
5. `"Not a Fit"` - 5,791 leads (6%)
6. `"Bad Contact Info - Uncontacted"` - 2,244 leads (3%)
7. `"Withdrawn or Rejected Application"` - 1,757 leads (2%)
8. `"No Book"` - 1,126 leads (1%)
9. `"AUM / Revenue too Low"` - 700 leads (<1%)
10. `"Book Not Transferable"` - 593 leads (<1%)
11. `"Timing"` - 408 leads (<1%)
12. `"Wrong Phone Number - Contacted"` - 405 leads (<1%)
13. `"No Show / Ghosted"` - 169 leads (<1%)
14. `"Restrictive Covenants"` - 153 leads (<1%)
15. `"Compensation Model Issues"` - 42 leads (<1%)
16. `"Bad Lead Provided"` - 11 leads (<1%)
17. `"Wants Platform Only"` - 10 leads (<1%)
18. `"Interested in M&A"` - 3 leads (<1%)

**SQL Query Example**:
```sql
SELECT 
    Id,
    Status,
    Disposition__c,
    Stage_Entered_Closed__c
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE Disposition__c IS NOT NULL
  AND Status = 'Closed'
ORDER BY Disposition__c
```

**Recycling Considerations**:
- **Recyclable Dispositions**: `"No Response"`, `"Timing"`, `"Auto-Closed by Operations"` (if enough time has passed)
- **Not Recyclable**: `"Not Interested in Moving"`, `"Not a Fit"`, `"No Book"`, `"Book Not Transferable"`, `"Restrictive Covenants"`
- **Conditional**: `"Other"`, `"Bad Contact Info - Uncontacted"` (may be recyclable if contact info updated)

---

### 3.2 Opportunity Object - Closed Lost Fields

**Field 1**: `Closed_Lost_Reason__c` (STRING)

**Common Closed Lost Reason Values** (by frequency):
1. `"No Longer Responsive"` - 216 opportunities (13%)
2. `"No Show – Intro Call"` - 214 opportunities (13%)
3. `"Savvy Declined - No Book of Business"` - 213 opportunities (13%)
4. `"Candidate Declined - Timing"` - 200 opportunities (12%)
5. `"Savvy Declined - Insufficient Revenue"` - 186 opportunities (11%)
6. `"Savvy Declined – Book Not Transferable"` - 146 opportunities (9%)
7. `"Candidate Declined - Fear of Change"` - 112 opportunities (7%)
8. `"Candidate Declined - Economics"` - 106 opportunities (7%)
9. `"Candidate Declined - Lost to Competitor"` - 78 opportunities (5%)
10. `"Savvy Declined - Poor Culture Fit"` - 72 opportunities (4%)
11. `"Other"` - 46 opportunities (3%)
12. `"Candidate Declined - Operational Constraints"` - 10 opportunities (<1%)
13. `"Savvy Declined - Compliance"` - 6 opportunities (<1%)

**Field 2**: `Closed_Lost_Details__c` (STRING)
- Free-text field for additional details about why opportunity was closed lost
- May contain notes, context, or specific circumstances
- Example: `"JB Re-Engagement opportunity Set 9/5/25"`

**Field 3**: `Closed_Lost_Checkbox__c` (BOOLEAN)
- Explicit checkbox indicating closed lost status
- `true` = Confirmed closed lost
- Used in conjunction with `IsClosed = true` AND `IsWon = false`

**SQL Query Example**:
```sql
SELECT 
    Id,
    StageName,
    IsClosed,
    IsWon,
    Closed_Lost_Reason__c,
    Closed_Lost_Details__c,
    Closed_Lost_Checkbox__c,
    CloseDate
FROM `savvy-gtm-analytics.SavvyGTMData.Opportunity`
WHERE IsClosed = true
  AND IsWon = false
  AND IsDeleted = false
```

**Recycling Considerations**:
- **Recyclable Reasons**: `"No Longer Responsive"`, `"Candidate Declined - Timing"`, `"No Show – Intro Call"` (if enough time has passed)
- **Not Recyclable**: `"Savvy Declined - No Book of Business"`, `"Savvy Declined - Insufficient Revenue"`, `"Savvy Declined – Book Not Transferable"`, `"Savvy Declined - Poor Culture Fit"`, `"Savvy Declined - Compliance"`
- **Conditional**: `"Candidate Declined - Economics"`, `"Candidate Declined - Fear of Change"`, `"Candidate Declined - Lost to Competitor"` (may be recyclable after significant time)

---

## 4. Last Task Date for Recycling Logic

### 4.1 Task Object Structure

**Key Fields for Recycling**:
- `WhoId` (STRING) - ID of Lead (starts with `00Q`) or Contact (starts with `003`)
- `WhatId` (STRING) - ID of Opportunity (starts with `006`) or Account (starts with `001`)
- `ActivityDate` (DATE) - Scheduled/completed date of the task
- `CreatedDate` (TIMESTAMP) - When the task was created
- `CompletedDateTime` (TIMESTAMP) - When the task was completed (may be NULL)
- `IsDeleted` (BOOLEAN) - `false` for active tasks
- `Status` (STRING) - Task status (`"Open"`, `"Completed"`, etc.)
- `Type` (STRING) - Task type (may be NULL)
- `Subject` (STRING) - Task subject/description

**ID Prefixes**:
- Lead: `00Q` (e.g., `00QDn0000051gvWMAQ`)
- Contact: `003` (e.g., `003Dn00000aoew5IAA`)
- Opportunity: `006` (e.g., `006Dn00000Aa1BeIAJ`)
- Account: `001` (e.g., `001Dn00000kM5bzIAC`)

---

### 4.2 Finding Last Task Date for Leads

**SQL Query Example**:
```sql
-- Last task date for Leads
SELECT 
    t.WhoId as LeadId,
    MAX(t.ActivityDate) as last_task_activity_date,
    MAX(t.CreatedDate) as last_task_created_date,
    MAX(t.CompletedDateTime) as last_task_completed_date,
    COUNT(*) as total_tasks
FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
WHERE t.WhoId LIKE '00Q%'  -- Lead ID prefix
  AND t.IsDeleted = false
GROUP BY 1
```

**Key Fields for Recycling Logic**:
- `last_task_activity_date` - Most recent `ActivityDate` (scheduled date)
- `last_task_created_date` - Most recent `CreatedDate` (when task was created)
- `last_task_completed_date` - Most recent `CompletedDateTime` (when task was completed)

**Recommendation**: Use `MAX(ActivityDate)` as the primary "last task date" for recycling logic, as it represents the most recent scheduled/completed activity.

---

### 4.3 Finding Last Task Date for Opportunities

**SQL Query Example**:
```sql
-- Last task date for Opportunities
SELECT 
    t.WhatId as OpportunityId,
    MAX(t.ActivityDate) as last_task_activity_date,
    MAX(t.CreatedDate) as last_task_created_date,
    MAX(t.CompletedDateTime) as last_task_completed_date,
    COUNT(*) as total_tasks
FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
WHERE t.WhatId LIKE '006%'  -- Opportunity ID prefix
  AND t.IsDeleted = false
GROUP BY 1
```

---

### 4.4 Combined Query for Both Leads and Opportunities

**SQL Query Example**:
```sql
-- Last task date for both Leads and Opportunities
WITH lead_tasks AS (
    SELECT 
        t.WhoId as record_id,
        'Lead' as record_type,
        MAX(t.ActivityDate) as last_task_date,
        MAX(t.CreatedDate) as last_task_created,
        COUNT(*) as task_count
    FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
    WHERE t.WhoId LIKE '00Q%'
      AND t.IsDeleted = false
    GROUP BY 1, 2
),
opp_tasks AS (
    SELECT 
        t.WhatId as record_id,
        'Opportunity' as record_type,
        MAX(t.ActivityDate) as last_task_date,
        MAX(t.CreatedDate) as last_task_created,
        COUNT(*) as task_count
    FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
    WHERE t.WhatId LIKE '006%'
      AND t.IsDeleted = false
    GROUP BY 1, 2
)
SELECT * FROM lead_tasks
UNION ALL
SELECT * FROM opp_tasks
```

---

### 4.5 Recycling Logic Recommendations

**For Leads**:
```sql
-- Example: Find leads that can be recycled (closed, no recent tasks, not do not call)
SELECT 
    l.Id,
    l.Status,
    l.Disposition__c,
    l.DoNotCall,
    l.Stage_Entered_Closed__c,
    t.last_task_date,
    DATE_DIFF(CURRENT_DATE(), t.last_task_date, DAY) as days_since_last_task
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
LEFT JOIN (
    SELECT 
        WhoId as LeadId,
        MAX(ActivityDate) as last_task_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task`
    WHERE WhoId LIKE '00Q%'
      AND IsDeleted = false
    GROUP BY 1
) t ON l.Id = t.LeadId
WHERE l.Status = 'Closed'
  AND l.IsConverted = false
  AND l.DoNotCall = false
  AND l.IsDeleted = false
  AND (t.last_task_date IS NULL OR DATE_DIFF(CURRENT_DATE(), t.last_task_date, DAY) >= 180)  -- 6 months
```

**For Opportunities**:
```sql
-- Example: Find opportunities that can be recycled (closed lost, no recent tasks)
SELECT 
    o.Id,
    o.StageName,
    o.Closed_Lost_Reason__c,
    o.CloseDate,
    t.last_task_date,
    DATE_DIFF(CURRENT_DATE(), t.last_task_date, DAY) as days_since_last_task
FROM `savvy-gtm-analytics.SavvyGTMData.Opportunity` o
LEFT JOIN (
    SELECT 
        WhatId as OpportunityId,
        MAX(ActivityDate) as last_task_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task`
    WHERE WhatId LIKE '006%'
      AND IsDeleted = false
    GROUP BY 1
) t ON o.Id = t.OpportunityId
WHERE o.IsClosed = true
  AND o.IsWon = false
  AND o.IsDeleted = false
  AND (t.last_task_date IS NULL OR DATE_DIFF(CURRENT_DATE(), t.last_task_date, DAY) >= 180)  -- 6 months
```

---

## 5. Field Reference Summary

### 5.1 Lead Object - Key Fields

| Field Name | Data Type | Purpose | Example Values |
|------------|-----------|---------|----------------|
| `Status` | STRING | Lead status | `"Closed"`, `"Contacting"`, `"New"` |
| `IsConverted` | BOOLEAN | Converted to Opportunity | `true`, `false` |
| `Stage_Entered_Closed__c` | TIMESTAMP | When lead entered closed stage | `2025-07-24T22:12:07Z` |
| `DoNotCall` | BOOLEAN | Do not call flag | `true`, `false` |
| `HasOptedOutOfEmail` | BOOLEAN | Email opt-out | `true`, `false` |
| `Disposition__c` | STRING | Close disposition reason | `"Auto-Closed by Operations"`, `"No Response"` |
| `LastActivityDate` | DATE | Last activity date (from Salesforce) | `2023-11-29` |
| `Lead_Recycle_Date__c` | DATE | Custom recycle date field | `2025-12-24` |

---

### 5.2 Opportunity Object - Key Fields

| Field Name | Data Type | Purpose | Example Values |
|------------|-----------|---------|----------------|
| `IsClosed` | BOOLEAN | Opportunity is closed | `true`, `false` |
| `IsWon` | BOOLEAN | Opportunity was won | `true`, `false` |
| `StageName` | STRING | Current stage | `"Closed Lost"`, `"Joined"` |
| `CloseDate` | DATE | Close date | `2023-06-14` |
| `Stage_Entered_Closed__c` | TIMESTAMP | When entered closed stage | `2025-09-18T14:24:29Z` |
| `Closed_Lost_Checkbox__c` | BOOLEAN | Closed lost checkbox | `true`, `false` |
| `Closed_Lost_Reason__c` | STRING | Close lost reason | `"No Longer Responsive"`, `"Timing"` |
| `Closed_Lost_Details__c` | STRING | Close lost details (free text) | `"JB Re-Engagement opportunity Set 9/5/25"` |
| `LastActivityDate` | DATE | Last activity date (from Salesforce) | `2023-06-27` |

---

### 5.3 Task Object - Key Fields

| Field Name | Data Type | Purpose | Example Values |
|------------|-----------|---------|----------------|
| `WhoId` | STRING | Lead/Contact ID | `00QDn0000051gvWMAQ` (Lead) |
| `WhatId` | STRING | Opportunity/Account ID | `006Dn00000Aa1BeIAJ` (Opp) |
| `ActivityDate` | DATE | Task activity date | `2023-02-09` |
| `CreatedDate` | TIMESTAMP | Task created date | `2023-02-06T19:10:30Z` |
| `CompletedDateTime` | TIMESTAMP | Task completed date | `2025-12-03T19:32:54Z` |
| `IsDeleted` | BOOLEAN | Task deleted flag | `true`, `false` |
| `Status` | STRING | Task status | `"Open"`, `"Completed"` |
| `Type` | STRING | Task type | `NULL` (often NULL) |
| `Subject` | STRING | Task subject | `"Review (Sample)"` |

---

## 6. Recommended Recycling Criteria

### 6.1 Lead Recycling Criteria

**Eligible for Recycling**:
- `Status = 'Closed'`
- `IsConverted = false` (not converted to opportunity)
- `DoNotCall = false` (not marked as do not call)
- `Disposition__c` IN (`"No Response"`, `"Timing"`, `"Auto-Closed by Operations"`, `"Other"`)
- `Last Task Date` >= 180 days ago (6 months) OR `Last Task Date IS NULL`
- `Stage_Entered_Closed__c` >= 180 days ago (6 months) OR `Stage_Entered_Closed__c IS NULL`

**NOT Eligible for Recycling**:
- `DoNotCall = true`
- `IsConverted = true` (successfully converted)
- `Disposition__c` IN (`"Not Interested in Moving"`, `"Not a Fit"`, `"No Book"`, `"Book Not Transferable"`, `"Restrictive Covenants"`)
- `Last Task Date` < 180 days ago (recent activity)

---

### 6.2 Opportunity Recycling Criteria

**Eligible for Recycling**:
- `IsClosed = true`
- `IsWon = false` (closed lost)
- `StageName = 'Closed Lost'`
- `Closed_Lost_Reason__c` IN (`"No Longer Responsive"`, `"Candidate Declined - Timing"`, `"No Show – Intro Call"`)
- `Last Task Date` >= 180 days ago (6 months) OR `Last Task Date IS NULL`
- `CloseDate` >= 180 days ago (6 months)

**NOT Eligible for Recycling**:
- `IsWon = true` (closed won)
- `Closed_Lost_Reason__c` IN (`"Savvy Declined - No Book of Business"`, `"Savvy Declined - Insufficient Revenue"`, `"Savvy Declined – Book Not Transferable"`, `"Savvy Declined - Poor Culture Fit"`, `"Savvy Declined - Compliance"`)
- `Last Task Date` < 180 days ago (recent activity)

---

## 7. SQL Query Templates

### 7.1 Find Recyclable Leads

```sql
-- Find leads eligible for recycling
WITH lead_last_tasks AS (
    SELECT 
        WhoId as LeadId,
        MAX(ActivityDate) as last_task_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task`
    WHERE WhoId LIKE '00Q%'
      AND IsDeleted = false
    GROUP BY 1
)
SELECT 
    l.Id,
    l.Status,
    l.Disposition__c,
    l.DoNotCall,
    l.Stage_Entered_Closed__c,
    t.last_task_date,
    DATE_DIFF(CURRENT_DATE(), COALESCE(t.last_task_date, l.Stage_Entered_Closed__c, l.CreatedDate), DAY) as days_since_last_activity
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
LEFT JOIN lead_last_tasks t ON l.Id = t.LeadId
WHERE l.Status = 'Closed'
  AND l.IsConverted = false
  AND l.DoNotCall = false
  AND l.IsDeleted = false
  AND l.Disposition__c IN ('No Response', 'Timing', 'Auto-Closed by Operations', 'Other')
  AND DATE_DIFF(CURRENT_DATE(), COALESCE(t.last_task_date, l.Stage_Entered_Closed__c, l.CreatedDate), DAY) >= 180
```

---

### 7.2 Find Recyclable Opportunities

```sql
-- Find opportunities eligible for recycling
WITH opp_last_tasks AS (
    SELECT 
        WhatId as OpportunityId,
        MAX(ActivityDate) as last_task_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Task`
    WHERE WhatId LIKE '006%'
      AND IsDeleted = false
    GROUP BY 1
)
SELECT 
    o.Id,
    o.StageName,
    o.Closed_Lost_Reason__c,
    o.Closed_Lost_Details__c,
    o.CloseDate,
    t.last_task_date,
    DATE_DIFF(CURRENT_DATE(), COALESCE(t.last_task_date, o.CloseDate), DAY) as days_since_last_activity
FROM `savvy-gtm-analytics.SavvyGTMData.Opportunity` o
LEFT JOIN opp_last_tasks t ON o.Id = t.OpportunityId
WHERE o.IsClosed = true
  AND o.IsWon = false
  AND o.IsDeleted = false
  AND o.Closed_Lost_Reason__c IN ('No Longer Responsive', 'Candidate Declined - Timing', 'No Show – Intro Call')
  AND DATE_DIFF(CURRENT_DATE(), COALESCE(t.last_task_date, o.CloseDate), DAY) >= 180
```

---

## 8. Additional Notes

### 8.1 Data Quality Considerations

- **NULL Values**: Many fields may be NULL. Use `COALESCE()` to handle NULLs in date calculations.
- **Deleted Records**: Always filter `IsDeleted = false` to exclude soft-deleted records.
- **Task Deletion**: Tasks can be soft-deleted (`IsDeleted = true`). Filter these out when calculating last task dates.

### 8.2 Performance Optimization

- **Indexing**: Consider creating views or materialized tables for frequently queried combinations (e.g., `lead_recycling_candidates`, `opportunity_recycling_candidates`).
- **Date Filtering**: Add date filters early in queries to reduce data scanned (e.g., `Stage_Entered_Closed__c >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR)`).

### 8.3 Custom Fields

- **Lead_Recycle_Date__c**: Custom field on Lead object (DATE) - may be used to track when a lead was last recycled.
- **Re_Engagement_Reason__c**: Custom field on Opportunity object (STRING) - tracks reason for re-engagement.
- **Re_Engagement_Next_Touch_Date__c**: Custom field on Opportunity object (DATE) - tracks next touch date for re-engagement.

---

## 9. Quick Reference Checklist

### For Lead Recycling:
- [ ] `Status = 'Closed'`
- [ ] `IsConverted = false`
- [ ] `DoNotCall = false`
- [ ] `Disposition__c` is recyclable
- [ ] Last task date >= 180 days OR NULL
- [ ] `IsDeleted = false`

### For Opportunity Recycling:
- [ ] `IsClosed = true`
- [ ] `IsWon = false`
- [ ] `Closed_Lost_Reason__c` is recyclable
- [ ] Last task date >= 180 days OR NULL
- [ ] `IsDeleted = false`

---

**Document Version**: 1.0  
**Last Updated**: December 24, 2025  
**Maintained By**: Data Science Team

