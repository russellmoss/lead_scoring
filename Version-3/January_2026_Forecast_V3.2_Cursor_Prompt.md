# January 2026 Lead List Performance Forecast - Cursor.ai Analysis

## Task Overview

**Objective:** Analyze the available lead pool for January 2026 using the **deployed V3.2 model** and generate a forecast report with expected conversion rates and confidence intervals.

**Deployed Model:** `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025`  
**Model Version:** V3.2_12212025

**Output Required:** A markdown report (`January_2026_Lead_List_Forecast.md`) suitable for team presentation.

---

## V3.2 Tier Conversion Rates (From Validation)

These are the **validated conversion rates** from the deployed V3.2 model:

| Tier | Conversion Rate | 95% CI Lower | 95% CI Upper | Lift | Volume |
|------|-----------------|--------------|--------------|------|--------|
| **TIER_1_PRIME_MOVER** | 15.92% | 11.34% | 20.50% | 4.63x | 245 |
| **TIER_2_PROVEN_MOVER** | 8.59% | 7.05% | 10.12% | 2.50x | 1,281 |
| **TIER_3_MODERATE_BLEEDER** | 9.52% | 3.25% | 15.80% | 2.77x | 84 |
| **TIER_4_EXPERIENCED_MOVER** | 11.54% | 6.05% | 17.03% | 3.35x | 130 |
| **TIER_5_HEAVY_BLEEDER** | 7.27% | 5.31% | 9.23% | 2.11x | 674 |
| **STANDARD** | 3.44% | 3.25% | 3.63% | 1.00x | 37,034 |

### 50% Confidence Intervals (Interquartile Range)

For forecasting, use these narrower 50% CIs (approximated from 95% CIs):

| Tier | Median Rate | Low 50 CI | High 50 CI |
|------|-------------|-----------|------------|
| **TIER_1_PRIME_MOVER** | 15.92% | 13.63% | 18.21% |
| **TIER_2_PROVEN_MOVER** | 8.59% | 7.82% | 9.36% |
| **TIER_3_MODERATE_BLEEDER** | 9.52% | 6.39% | 12.66% |
| **TIER_4_EXPERIENCED_MOVER** | 11.54% | 8.80% | 14.29% |
| **TIER_5_HEAVY_BLEEDER** | 7.27% | 6.29% | 8.25% |
| **STANDARD** | 3.44% | 3.35% | 3.54% |

---

## Step 1: Execute Data Queries

Run these queries in BigQuery (project: `savvy-gtm-analytics`, location: `northamerica-northeast2`).

### Query 1: Current V3.2 Scored Leads - Tier Distribution

```sql
-- ============================================================================
-- V3.2 DEPLOYED MODEL: Current Tier Distribution
-- ============================================================================
SELECT 
    score_tier,
    COUNT(*) as lead_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as pct_of_total,
    ROUND(AVG(expected_conversion_rate) * 100, 2) as expected_conv_rate_pct
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025`
GROUP BY score_tier
ORDER BY priority_rank;
```

### Query 2: New Prospects Available (Not in Salesforce, Scoreable)

```sql
-- ============================================================================
-- NEW PROSPECTS: Advisors in FINTRX not yet in Salesforce
-- ============================================================================
WITH 
-- Existing Salesforce CRDs (to exclude)
salesforce_crds AS (
    SELECT DISTINCT 
        SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE FA_CRD__c IS NOT NULL
      AND IsDeleted = false
),

-- Count new prospects by whether they'd be scoreable
new_prospects AS (
    SELECT 
        c.RIA_CONTACT_CRD_ID as advisor_crd,
        c.PRIMARY_FIRM_NAME as firm_name,
        c.PRIMARY_FIRM_START_DATE,
        CASE 
            WHEN c.PRIMARY_FIRM_START_DATE IS NULL THEN 'Missing Start Date'
            WHEN c.CONTACT_FIRST_NAME IS NULL THEN 'Missing Name'
            ELSE 'Scoreable'
        END as status
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    LEFT JOIN salesforce_crds sf ON c.RIA_CONTACT_CRD_ID = sf.crd
    WHERE sf.crd IS NULL  -- NOT in Salesforce
)

SELECT 
    status,
    COUNT(*) as advisor_count
FROM new_prospects
GROUP BY status
ORDER BY advisor_count DESC;
```

### Query 3: Recyclable Leads (180+ Days No Activity, Not DNC)

```sql
-- ============================================================================
-- RECYCLABLE LEADS: In Salesforce, 180+ days no SMS/Call, eligible for re-contact
-- ============================================================================
WITH 
-- Last SMS/Call activity per lead
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

-- Recyclable Salesforce leads
recyclable_leads AS (
    SELECT 
        l.Id as lead_id,
        l.Status,
        l.DoNotCall,
        la.last_activity_date,
        CASE 
            WHEN la.last_activity_date IS NULL THEN 'No Activity Ever'
            WHEN DATE_DIFF(CURRENT_DATE(), la.last_activity_date, DAY) > 180 THEN '180+ Days'
            ELSE 'Recent Activity'
        END as activity_status,
        CASE
            WHEN l.DoNotCall = true THEN 'DNC'
            WHEN l.Status IN ('Closed', 'Converted', 'Dead', 'Unqualified', 'Disqualified', 'Do Not Contact', 'Not Qualified') THEN 'Bad Status'
            ELSE 'Eligible'
        END as eligibility
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN lead_task_activity la ON l.Id = la.lead_id
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
)

SELECT 
    activity_status,
    eligibility,
    COUNT(*) as lead_count
FROM recyclable_leads
WHERE activity_status IN ('No Activity Ever', '180+ Days')
GROUP BY activity_status, eligibility
ORDER BY activity_status, eligibility;
```

### Query 4: Recyclable Leads with V3.2 Scores

```sql
-- ============================================================================
-- RECYCLABLE LEADS: Join with V3.2 scores to get tier distribution
-- ============================================================================
WITH 
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

recyclable_eligible AS (
    SELECT 
        l.Id as lead_id
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN lead_task_activity la ON l.Id = la.lead_id
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND (la.last_activity_date IS NULL OR DATE_DIFF(CURRENT_DATE(), la.last_activity_date, DAY) > 180)
      AND (l.DoNotCall IS NULL OR l.DoNotCall = false)
      AND l.Status NOT IN ('Closed', 'Converted', 'Dead', 'Unqualified', 'Disqualified', 'Do Not Contact', 'Not Qualified')
)

SELECT 
    s.score_tier,
    COUNT(*) as recyclable_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as pct_of_recyclable
FROM recyclable_eligible r
JOIN `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025` s
    ON r.lead_id = s.lead_id
GROUP BY s.score_tier
ORDER BY 
    CASE s.score_tier
        WHEN 'TIER_1_PRIME_MOVER' THEN 1
        WHEN 'TIER_2_PROVEN_MOVER' THEN 2
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 3
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 4
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 5
        WHEN 'STANDARD' THEN 6
        ELSE 7
    END;
```

### Query 5: Total Pool Summary

```sql
-- ============================================================================
-- POOL SUMMARY: Total available leads for January 2026
-- ============================================================================
WITH 
-- Count scored leads in V3.2
scored_leads AS (
    SELECT COUNT(*) as total_scored
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025`
),

-- Count priority tier leads
priority_leads AS (
    SELECT COUNT(*) as total_priority
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025`
    WHERE score_tier != 'STANDARD'
),

-- Count new prospects (not in SF)
new_prospects AS (
    SELECT COUNT(*) as total_new
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    WHERE c.CONTACT_FIRST_NAME IS NOT NULL
      AND c.PRIMARY_FIRM_START_DATE IS NOT NULL
      AND c.RIA_CONTACT_CRD_ID NOT IN (
          SELECT DISTINCT 
              SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64)
          FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
          WHERE FA_CRD__c IS NOT NULL AND IsDeleted = false
      )
),

-- Count recyclable leads
lead_task_activity AS (
    SELECT 
        t.WhoId as lead_id,
        MAX(DATE(COALESCE(t.ActivityDate, t.CreatedDate))) as last_activity_date
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

recyclable AS (
    SELECT COUNT(*) as total_recyclable
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN lead_task_activity la ON l.Id = la.lead_id
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND (la.last_activity_date IS NULL OR DATE_DIFF(CURRENT_DATE(), la.last_activity_date, DAY) > 180)
      AND (l.DoNotCall IS NULL OR l.DoNotCall = false)
      AND l.Status NOT IN ('Closed', 'Converted', 'Dead', 'Unqualified', 'Disqualified', 'Do Not Contact', 'Not Qualified')
)

SELECT 
    s.total_scored as v3_2_scored_leads,
    p.total_priority as v3_2_priority_tier_leads,
    n.total_new as new_prospects_available,
    r.total_recyclable as recyclable_leads_180d
FROM scored_leads s, priority_leads p, new_prospects n, recyclable r;
```

---

## Step 2: Calculate Expected Conversions

After running queries, use these V3.2 validated rates:

### Conversion Rate Reference Table

| Tier | Median Rate | Low 50 CI | High 50 CI | Use For Calculation |
|------|-------------|-----------|------------|---------------------|
| TIER_1_PRIME_MOVER | 15.92% | 13.63% | 18.21% | Highest priority |
| TIER_2_PROVEN_MOVER | 8.59% | 7.82% | 9.36% | Large volume tier |
| TIER_3_MODERATE_BLEEDER | 9.52% | 6.39% | 12.66% | Wide CI (small n) |
| TIER_4_EXPERIENCED_MOVER | 11.54% | 8.80% | 14.29% | Good performer |
| TIER_5_HEAVY_BLEEDER | 7.27% | 6.29% | 8.25% | Solid volume |
| STANDARD | 3.44% | 3.35% | 3.54% | Baseline |

### Calculation Formula

For a list of 2,250 leads with a given tier distribution:

```
Expected Conversions = Σ (Tier_Count × Tier_Median_Rate)
Low 50 CI = Σ (Tier_Count × Tier_Low50_Rate)
High 50 CI = Σ (Tier_Count × Tier_High50_Rate)
```

### Example: Recommended Allocation (2,250 leads)

Based on V3.2 validated tier distribution (~6% priority tiers):

| Tier | Recommended Count | % of List | Expected Calls | Low 50 CI | High 50 CI |
|------|-------------------|-----------|----------------|-----------|------------|
| TIER_1_PRIME_MOVER | 15 | 0.7% | 2.4 | 2.0 | 2.7 |
| TIER_2_PROVEN_MOVER | 75 | 3.3% | 6.4 | 5.9 | 7.0 |
| TIER_3_MODERATE_BLEEDER | 5 | 0.2% | 0.5 | 0.3 | 0.6 |
| TIER_4_EXPERIENCED_MOVER | 8 | 0.4% | 0.9 | 0.7 | 1.1 |
| TIER_5_HEAVY_BLEEDER | 40 | 1.8% | 2.9 | 2.5 | 3.3 |
| STANDARD | 2,107 | 93.6% | 72.5 | 70.6 | 74.6 |
| **TOTAL** | **2,250** | **100%** | **85.6** | **82.0** | **89.4** |

**Expected Conversion Rate:** 85.6 / 2,250 = **3.80%** (50% CI: 3.64% - 3.97%)

---

## Step 3: Generate Report

Create `January_2026_Lead_List_Forecast.md` with this structure:

```markdown
# January 2026 Lead List Performance Forecast

**Report Date:** [DATE]  
**Model Version:** V3.2_12212025  
**Deployed Table:** `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025`  
**Forecast Period:** January 2026

---

## Executive Summary

### V3.2 Model Performance (Validated)

| Tier | Conversion Rate | Lift vs Baseline | Volume in Model |
|------|-----------------|------------------|-----------------|
| TIER_1_PRIME_MOVER | 15.92% | 4.63x | 245 |
| TIER_2_PROVEN_MOVER | 8.59% | 2.50x | 1,281 |
| TIER_3_MODERATE_BLEEDER | 9.52% | 2.77x | 84 |
| TIER_4_EXPERIENCED_MOVER | 11.54% | 3.35x | 130 |
| TIER_5_HEAVY_BLEEDER | 7.27% | 2.11x | 674 |
| STANDARD | 3.44% | 1.00x | 37,034 |

### January 2026 Forecast (2,250 Leads)

| Metric | Low 50 CI | Median | High 50 CI |
|--------|-----------|--------|------------|
| **Contacted → MQL** | [X]% | [X]% | [X]% |
| **Expected Conversions** | [X] | [X] | [X] |

---

## Available Lead Pool

### From V3.2 Scored Table
| Metric | Count |
|--------|-------|
| Total Scored Leads | [QUERY 5: v3_2_scored_leads] |
| Priority Tier Leads | [QUERY 5: v3_2_priority_tier_leads] |
| % Priority | [calculated]% |

### New Prospects (Not in Salesforce)
| Status | Count |
|--------|-------|
| Scoreable New Prospects | [QUERY 2] |

### Recyclable Leads (180+ Days)
| Status | Count |
|--------|-------|
| Eligible for Re-contact | [QUERY 3/4] |

---

## V3.2 Tier Distribution

### Current Scored Leads
[INSERT QUERY 1 RESULTS]

### Recyclable Leads by Tier
[INSERT QUERY 4 RESULTS]

---

## January 2026 Forecast Scenarios

### Scenario A: Natural Distribution (2,250 leads)
Use whatever tier distribution exists in pool:

| Tier | Count | Expected Conversions | 50% CI |
|------|-------|---------------------|--------|
| [FILL FROM QUERY RESULTS] | | | |

### Scenario B: Priority Tiers Only
Focus exclusively on Tiers 1-5 (higher rate, lower volume):

| Tier | Count | Expected Conversions | 50% CI |
|------|-------|---------------------|--------|
| [FILL FROM QUERY RESULTS] | | | |

### Scenario C: Tier 1 + 2 Focus (Highest Quality)
Only use TIER_1_PRIME_MOVER and TIER_2_PROVEN_MOVER:

| Tier | Count | Expected Conversions | 50% CI |
|------|-------|---------------------|--------|
| [FILL FROM QUERY RESULTS] | | | |

---

## Recommendations

1. **Prioritize Tier 1 (Prime Mover)** — 15.92% conversion, 4.63x lift
2. **Volume from Tier 2 (Proven Mover)** — 8.59% conversion, largest priority tier
3. **Include recyclable leads** — 180+ days since contact, not DNC
4. **Monitor weekly** — Track actual vs expected by tier

---

## Appendix: V3.2 Model Details

### Tier Definitions
- **TIER_1_PRIME_MOVER:** Mobile advisor (3+ moves) + bleeding firm + optimal tenure
- **TIER_2_PROVEN_MOVER:** 3+ prior firms, proven mobility
- **TIER_3_MODERATE_BLEEDER:** At firm with moderate advisor departures
- **TIER_4_EXPERIENCED_MOVER:** Industry veterans with mobility history
- **TIER_5_HEAVY_BLEEDER:** At firm with significant advisor departures
- **STANDARD:** Does not meet priority tier criteria

### Validation Basis
- **Total Leads Analyzed:** 39,448
- **Priority Tier Leads:** 2,414 (6.12%)
- **Baseline Conversion:** 3.44%
- **All priority tiers statistically significant** (95% CIs don't overlap baseline)

---

**Report Generated By:** Lead Scoring Analytics  
**Model:** V3.2_12212025 (Deployed)  
**Next Update:** After January 2026 actuals
```

---

## Step 4: Save Output Files

Save to these locations:

1. `/mnt/user-data/outputs/January_2026_Lead_List_Forecast.md` — Final team report
2. Query results as CSVs if needed

---

## Execution Checklist

- [ ] Run Query 1 (V3.2 current tier distribution)
- [ ] Run Query 2 (New prospects count)
- [ ] Run Query 3 (Recyclable leads eligibility)
- [ ] Run Query 4 (Recyclable leads by V3.2 tier)
- [ ] Run Query 5 (Pool summary)
- [ ] Fill in report template with query results
- [ ] Calculate expected conversions using V3.2 rates
- [ ] Calculate 50% confidence intervals
- [ ] Save final report

---

## Notes for Cursor

1. **BigQuery Location:** `northamerica-northeast2` (Toronto)
2. **Project:** `savvy-gtm-analytics`
3. **Model Table:** `ml_features.lead_scores_v3_2_12212025`
4. Use CURRENT_DATE() for real-time calculations
5. Round percentages to 2 decimal places
6. Round counts to whole numbers

---

## V3.2 Quick Reference

### Priority Tier Expected Performance

| If you contact... | Expected MQLs | Expected Rate |
|-------------------|---------------|---------------|
| 100 TIER_1_PRIME_MOVER | 16 | 15.92% |
| 100 TIER_2_PROVEN_MOVER | 9 | 8.59% |
| 100 TIER_4_EXPERIENCED_MOVER | 12 | 11.54% |
| 100 TIER_5_HEAVY_BLEEDER | 7 | 7.27% |
| 100 STANDARD | 3 | 3.44% |

### Key Insight

**Priority tiers (6.12% of leads) convert at 2-5x the rate of STANDARD leads.** Focusing on priority tiers will significantly improve conversion efficiency.
