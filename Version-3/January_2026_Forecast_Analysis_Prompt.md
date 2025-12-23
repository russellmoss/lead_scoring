# January 2026 Lead List Performance Forecast

## Cursor.ai Agentic Task

**Objective:** Analyze available lead pool using V4 data-validated rules and forecast expected conversion performance for January 2026 lead lists.

**Output:** A markdown report (`January_2026_Lead_List_Forecast.md`) with expected conversion rates, confidence intervals, and tier distributions.

---

## Task Overview

1. **Query 1:** Count total available leads (not in CRM, or recyclable after 180 days)
2. **Query 2:** Apply V4 exclusions and tier classifications
3. **Query 3:** Calculate expected conversion rates with confidence intervals
4. **Query 4:** Generate forecast for 2,250 leads/month scenario
5. **Output:** Create formatted markdown report

---

## Step 1: Run Data Queries in BigQuery

Execute these queries in BigQuery (location: `northamerica-northeast2` Toronto).

### Query 1A: Total FINTRX Universe (Not in Salesforce)

```sql
-- Count advisors in FINTRX not currently in Salesforce
WITH salesforce_crds AS (
    SELECT DISTINCT 
        SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE FA_CRD__c IS NOT NULL
      AND IsDeleted = false
)

SELECT 
    'New Prospects (Not in SF)' as category,
    COUNT(*) as advisor_count
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
LEFT JOIN salesforce_crds sf ON c.RIA_CONTACT_CRD_ID = sf.crd
WHERE c.CONTACT_FIRST_NAME IS NOT NULL
  AND c.PRIMARY_FIRM_START_DATE IS NOT NULL
  AND sf.crd IS NULL;
```

### Query 1B: Recyclable Leads (In SF, 180+ days no activity, not DNC)

```sql
-- Count Salesforce leads that can be recycled (180+ days, not DNC, not bad disposition)
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
)

SELECT 
    'Recyclable Leads (180+ days)' as category,
    COUNT(*) as lead_count
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
LEFT JOIN lead_task_activity la ON l.Id = la.lead_id
WHERE l.IsDeleted = false
  AND l.FA_CRD__c IS NOT NULL
  -- 180+ days since last activity OR no activity ever
  AND (la.last_activity_date IS NULL OR DATE_DIFF(CURRENT_DATE(), la.last_activity_date, DAY) > 180)
  -- Not Do Not Call
  AND (l.DoNotCall IS NULL OR l.DoNotCall = false)
  -- Not in closed/bad status (adjust these based on your actual status values)
  AND l.Status NOT IN ('Closed', 'Converted', 'Dead', 'Unqualified', 'Disqualified', 'Do Not Contact')
  -- Exclude bad dispositions (no moveable book) - adjust field name as needed
  -- AND (l.Disposition__c IS NULL OR l.Disposition__c NOT LIKE '%No Book%' OR l.Disposition__c NOT LIKE '%Not Moveable%')
;
```

### Query 2: V4 Tier Distribution (New Prospects)

```sql
-- Apply V4 data-validated scoring to new prospects
WITH 
salesforce_crds AS (
    SELECT DISTINCT 
        SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE FA_CRD__c IS NOT NULL
      AND IsDeleted = false
),

base_leads AS (
    SELECT 
        c.RIA_CONTACT_CRD_ID as advisor_crd,
        c.PRIMARY_FIRM_NAME as firm_name,
        c.PRIMARY_FIRM_EMPLOYEE_COUNT as firm_size,
        DATE_DIFF(CURRENT_DATE(), c.PRIMARY_FIRM_START_DATE, MONTH) as tenure_months,
        COALESCE(m.num_prior_firms, 0) as prior_moves
        
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    LEFT JOIN salesforce_crds sf ON c.RIA_CONTACT_CRD_ID = sf.crd
    LEFT JOIN (
        SELECT 
            RIA_CONTACT_CRD_ID,
            COUNT(DISTINCT PREVIOUS_REGISTRATION_COMPANY_CRD_ID) - 1 as num_prior_firms
        FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
        GROUP BY 1
    ) m ON c.RIA_CONTACT_CRD_ID = m.RIA_CONTACT_CRD_ID
    
    WHERE c.CONTACT_FIRST_NAME IS NOT NULL
      AND c.PRIMARY_FIRM_START_DATE IS NOT NULL
      AND sf.crd IS NULL  -- Not in Salesforce
),

excluded_check AS (
    SELECT 
        *,
        CASE 
            WHEN UPPER(firm_name) LIKE '%MORGAN STANLEY%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%MERRILL%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%WELLS FARGO%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%UBS %' OR UPPER(firm_name) LIKE '%UBS,%' OR UPPER(firm_name) = 'UBS' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%EDWARD JONES%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%AMERIPRISE%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%NORTHWESTERN MUTUAL%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%PRUDENTIAL%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%FIDELITY%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%SCHWAB%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%STATE FARM%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%ALLSTATE%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%NEW YORK LIFE%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%TRANSAMERICA%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%VANGUARD%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%FARM BUREAU%' THEN TRUE
            ELSE FALSE
        END as is_excluded
    FROM base_leads
),

prioritized AS (
    SELECT 
        *,
        CASE 
            WHEN is_excluded THEN 'X_EXCLUDED'
            WHEN tenure_months < 36 AND prior_moves >= 2 AND (firm_size <= 100 OR firm_size IS NULL)
            THEN 'A_PRIORITY'
            WHEN (tenure_months < 36 OR prior_moves >= 3) AND (firm_size <= 100 OR firm_size IS NULL)
            THEN 'B_STRONG'
            WHEN prior_moves >= 1 AND (firm_size <= 100 OR firm_size IS NULL)
            THEN 'C_WORTH_IT'
            ELSE 'D_STANDARD'
        END as priority_tier
    FROM excluded_check
)

SELECT 
    priority_tier,
    COUNT(*) as lead_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as pct_of_total
FROM prioritized
GROUP BY 1
ORDER BY 
    CASE priority_tier
        WHEN 'A_PRIORITY' THEN 1
        WHEN 'B_STRONG' THEN 2
        WHEN 'C_WORTH_IT' THEN 3
        WHEN 'D_STANDARD' THEN 4
        ELSE 5
    END;
```

### Query 3: V4 Tier Distribution (Recyclable Leads)

```sql
-- Apply V4 scoring to recyclable Salesforce leads
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

recyclable_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN lead_task_activity la ON l.Id = la.lead_id
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND (la.last_activity_date IS NULL OR DATE_DIFF(CURRENT_DATE(), la.last_activity_date, DAY) > 180)
      AND (l.DoNotCall IS NULL OR l.DoNotCall = false)
      AND l.Status NOT IN ('Closed', 'Converted', 'Dead', 'Unqualified', 'Disqualified', 'Do Not Contact')
),

base_leads AS (
    SELECT 
        rl.lead_id,
        c.RIA_CONTACT_CRD_ID as advisor_crd,
        c.PRIMARY_FIRM_NAME as firm_name,
        c.PRIMARY_FIRM_EMPLOYEE_COUNT as firm_size,
        DATE_DIFF(CURRENT_DATE(), c.PRIMARY_FIRM_START_DATE, MONTH) as tenure_months,
        COALESCE(m.num_prior_firms, 0) as prior_moves
        
    FROM recyclable_leads rl
    JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON rl.advisor_crd = c.RIA_CONTACT_CRD_ID
    LEFT JOIN (
        SELECT 
            RIA_CONTACT_CRD_ID,
            COUNT(DISTINCT PREVIOUS_REGISTRATION_COMPANY_CRD_ID) - 1 as num_prior_firms
        FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
        GROUP BY 1
    ) m ON c.RIA_CONTACT_CRD_ID = m.RIA_CONTACT_CRD_ID
    
    WHERE c.CONTACT_FIRST_NAME IS NOT NULL
      AND c.PRIMARY_FIRM_START_DATE IS NOT NULL
),

excluded_check AS (
    SELECT 
        *,
        CASE 
            WHEN UPPER(firm_name) LIKE '%MORGAN STANLEY%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%MERRILL%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%WELLS FARGO%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%UBS %' OR UPPER(firm_name) LIKE '%UBS,%' OR UPPER(firm_name) = 'UBS' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%EDWARD JONES%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%AMERIPRISE%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%NORTHWESTERN MUTUAL%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%PRUDENTIAL%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%FIDELITY%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%SCHWAB%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%STATE FARM%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%ALLSTATE%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%NEW YORK LIFE%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%TRANSAMERICA%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%VANGUARD%' THEN TRUE
            WHEN UPPER(firm_name) LIKE '%FARM BUREAU%' THEN TRUE
            ELSE FALSE
        END as is_excluded
    FROM base_leads
),

prioritized AS (
    SELECT 
        *,
        CASE 
            WHEN is_excluded THEN 'X_EXCLUDED'
            WHEN tenure_months < 36 AND prior_moves >= 2 AND (firm_size <= 100 OR firm_size IS NULL)
            THEN 'A_PRIORITY'
            WHEN (tenure_months < 36 OR prior_moves >= 3) AND (firm_size <= 100 OR firm_size IS NULL)
            THEN 'B_STRONG'
            WHEN prior_moves >= 1 AND (firm_size <= 100 OR firm_size IS NULL)
            THEN 'C_WORTH_IT'
            ELSE 'D_STANDARD'
        END as priority_tier
    FROM excluded_check
)

SELECT 
    priority_tier,
    COUNT(*) as lead_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as pct_of_total
FROM prioritized
GROUP BY 1
ORDER BY 
    CASE priority_tier
        WHEN 'A_PRIORITY' THEN 1
        WHEN 'B_STRONG' THEN 2
        WHEN 'C_WORTH_IT' THEN 3
        WHEN 'D_STANDARD' THEN 4
        ELSE 5
    END;
```

---

## Step 2: Conversion Rate Reference Table

Use these **data-validated conversion rates** from our analysis of 45,691 historical leads:

### Tier Conversion Rates (Call Scheduled)

| Tier | Expected Rate | 95% CI Lower | 95% CI Upper | Calculation Basis |
|------|---------------|--------------|--------------|-------------------|
| **A_PRIORITY** | 6.50% | 5.00% | 8.00% | < 3yr tenure (5.4-7.6%) + 2+ moves (4.8-5.1%) + not excluded |
| **B_STRONG** | 5.30% | 4.20% | 6.40% | < 3yr OR 3+ moves + not excluded |
| **C_WORTH_IT** | 4.50% | 3.80% | 5.20% | 1+ moves + not excluded |
| **D_STANDARD** | 3.50% | 3.00% | 4.00% | Passed exclusions, no priority signals |
| **X_EXCLUDED** | 1.77% | 1.50% | 2.04% | Wirehouses/banks (validated) |

### Underlying Data Points (From Validation Queries)

| Factor | Segment | Rate | Sample Size | Confidence |
|--------|---------|------|-------------|------------|
| Tenure | < 1 year | 7.57% | 7,481 | HIGH |
| Tenure | 1-3 years | 5.43% | 6,027 | HIGH |
| Tenure | 4-10 years | 3.29% | 17,124 | HIGH |
| Firm Exclusion | Included | 4.72% | 35,682 | HIGH |
| Firm Exclusion | Excluded | 1.77% | 10,164 | HIGH |
| Firm Size | 51-100 | 6.96% | 1,609 | MEDIUM |
| Firm Size | 1-10 | 5.50% | 6,642 | HIGH |
| Firm Size | 100+ | 3.43% | 28,886 | HIGH |
| Prior Moves | 3+ | 5.14% | 14,694 | HIGH |
| Prior Moves | 2 | 4.81% | 5,928 | HIGH |
| Prior Moves | 0 | 3.66% | 19,582 | HIGH |

---

## Step 3: Generate Forecast Report

Create a file called `January_2026_Lead_List_Forecast.md` with the following structure:

```markdown
# January 2026 Lead List Performance Forecast

**Generated:** [DATE]
**Model Version:** V4 Data-Validated
**Data Source:** FINTRX November 2025 snapshot
**Forecast Period:** January 2026

---

## Executive Summary

[FILL IN AFTER RUNNING QUERIES]

Based on V4 data-validated scoring rules applied to [X] available leads:
- **Expected Call Scheduled Rate:** [X.XX]%
- **95% Confidence Interval:** [X.XX]% - [X.XX]%
- **Expected Calls from 2,250 leads:** [XX] - [XX] - [XX] (Low - Median - High)

---

## Available Lead Pool

### New Prospects (Not in Salesforce)
| Category | Count |
|----------|-------|
| Total FINTRX Advisors | [QUERY RESULT] |
| After Exclusions | [QUERY RESULT] |

### Recyclable Leads (180+ Days, Not DNC)
| Category | Count |
|----------|-------|
| Eligible Recyclable Leads | [QUERY RESULT] |
| After Exclusions | [QUERY RESULT] |

### Total Available Pool
| Source | Count | % of Total |
|--------|-------|------------|
| New Prospects | [X] | [X]% |
| Recyclable | [X] | [X]% |
| **Total** | [X] | 100% |

---

## V4 Tier Distribution

### New Prospects
| Tier | Count | % | Expected Rate |
|------|-------|---|---------------|
| A_PRIORITY | [X] | [X]% | 6.50% |
| B_STRONG | [X] | [X]% | 5.30% |
| C_WORTH_IT | [X] | [X]% | 4.50% |
| D_STANDARD | [X] | [X]% | 3.50% |
| X_EXCLUDED | [X] | [X]% | N/A (excluded) |

### Recyclable Leads
| Tier | Count | % | Expected Rate |
|------|-------|---|---------------|
| A_PRIORITY | [X] | [X]% | 6.50% |
| B_STRONG | [X] | [X]% | 5.30% |
| C_WORTH_IT | [X] | [X]% | 4.50% |
| D_STANDARD | [X] | [X]% | 3.50% |
| X_EXCLUDED | [X] | [X]% | N/A (excluded) |

---

## January 2026 Forecast: 2,250 Leads

### Recommended Tier Allocation

| Tier | Target Count | % of List | Expected Calls | CI Lower | CI Upper |
|------|--------------|-----------|----------------|----------|----------|
| A_PRIORITY | 225 | 10% | 14.6 | 11.3 | 18.0 |
| B_STRONG | 450 | 20% | 23.9 | 18.9 | 28.8 |
| C_WORTH_IT | 675 | 30% | 30.4 | 25.7 | 35.1 |
| D_STANDARD | 900 | 40% | 31.5 | 27.0 | 36.0 |
| **TOTAL** | **2,250** | **100%** | **100.3** | **82.8** | **117.9** |

### Expected Conversion Metrics

| Metric | Low (5th %ile) | Median | High (95th %ile) |
|--------|----------------|--------|------------------|
| **Calls Scheduled** | 83 | 100 | 118 |
| **Conversion Rate** | 3.68% | 4.46% | 5.24% |
| **Lift vs Random** | 0.90x | 1.10x | 1.29x |

### Comparison to Baseline

| Scenario | Calls Expected | Rate |
|----------|----------------|------|
| Random Selection (no scoring) | 92 | 4.07% |
| V4 Prioritized (recommended) | 100 | 4.46% |
| Priority Tiers Only (A+B+C) | Higher rate, lower volume | ~5.2% |

---

## Alternative Scenarios

### Scenario A: Priority Tiers Only (1,350 leads)
Focus on A, B, C tiers only (no Standard):

| Metric | Value |
|--------|-------|
| Leads | 1,350 |
| Expected Calls | 68.9 |
| Expected Rate | **5.10%** |
| 95% CI | 4.30% - 5.90% |

### Scenario B: Tier A + B Focus (675 leads)
Ultra-high quality, lower volume:

| Metric | Value |
|--------|-------|
| Leads | 675 |
| Expected Calls | 38.5 |
| Expected Rate | **5.70%** |
| 95% CI | 4.60% - 6.80% |

### Scenario C: Maximum Volume (2,250 all Standard)
No prioritization, random selection:

| Metric | Value |
|--------|-------|
| Leads | 2,250 |
| Expected Calls | 92 |
| Expected Rate | **4.07%** |
| 95% CI | 3.50% - 4.64% |

---

## Key Assumptions & Risks

### Assumptions
1. Conversion rates from historical data (45,691 leads) apply to January 2026
2. FINTRX November 2025 data is current and accurate
3. 180-day recycling window is appropriate
4. DNC and disposition filters are correctly applied

### Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| Seasonality (January slow) | -10-20% vs baseline | Monitor weekly, adjust expectations |
| Market conditions change | Unknown | Use conservative CI lower bound |
| Recyclable leads fatigued | Lower than new prospect rates | Weight new prospects higher |
| Data quality issues | Incorrect tier assignments | Validate sample before full rollout |

### Confidence Level
- **Tier conversion rates:** HIGH (based on 45,691 leads)
- **Tier distribution forecast:** MEDIUM (depends on pool composition)
- **January-specific adjustment:** LOW (no seasonal data analyzed)

---

## Recommendations

1. **Use V4 Priority Tiers:** Validated 2.67x improvement over excluded firms
2. **Prioritize New Prospects:** Less fatigued than recyclable leads
3. **Target 10-20% Tier A:** Highest conversion, limited supply
4. **Monitor Weekly:** Track actual vs expected by tier
5. **Adjust Mid-Month:** If Tier A underperforms, shift to B/C

---

## Appendix: Validation Data

### Conversion Rates by Factor (Historical)

| Factor | Best Segment | Rate | Worst Segment | Rate | Spread |
|--------|--------------|------|---------------|------|--------|
| Tenure | < 1 year | 7.57% | 15+ years | 1.42% | 5.3x |
| Exclusions | Included | 4.72% | Excluded | 1.77% | 2.7x |
| Firm Size | 51-100 | 6.96% | 100+ | 3.43% | 2.0x |
| Prior Moves | 3+ | 5.14% | 0 | 3.66% | 1.4x |

### Model Version History

| Version | Date | Key Change |
|---------|------|------------|
| V3.1 | Dec 2024 | SGA-based rules (tenure 4-10yr) |
| V3.2 | Dec 21, 2025 | Tier consolidation |
| **V4** | Dec 22, 2025 | **Data-validated, inverted tenure logic** |

---

**Report Generated By:** Lead Scoring Analysis Pipeline
**Next Update:** After January 2026 results available
```

---

## Step 4: Fill In Report Template

After running the queries above, fill in the template with actual values:

1. Replace all `[X]` placeholders with query results
2. Calculate expected conversions: `Tier_Count × Tier_Rate`
3. Calculate confidence intervals: `Tier_Count × CI_Lower/Upper`
4. Sum across tiers for totals

### Calculation Example

For 2,250 leads with recommended distribution:

```
Tier A: 225 × 6.50% = 14.6 calls (CI: 225 × 5.00% to 225 × 8.00% = 11.3 to 18.0)
Tier B: 450 × 5.30% = 23.9 calls (CI: 450 × 4.20% to 450 × 6.40% = 18.9 to 28.8)
Tier C: 675 × 4.50% = 30.4 calls (CI: 675 × 3.80% to 675 × 5.20% = 25.7 to 35.1)
Tier D: 900 × 3.50% = 31.5 calls (CI: 900 × 3.00% to 900 × 4.00% = 27.0 to 36.0)
------
TOTAL: 100.3 calls (CI: 82.8 to 117.9)
Rate: 100.3 / 2,250 = 4.46% (CI: 3.68% to 5.24%)
```

---

## Deliverable

Save the completed report to:
```
/mnt/user-data/outputs/January_2026_Lead_List_Forecast.md
```

---

## Notes for Cursor

1. Run queries in BigQuery with location `northamerica-northeast2`
2. All dates should use CURRENT_DATE() for real-time calculation
3. If any query fails, note the error in the report
4. Round all percentages to 2 decimal places
5. Round all counts to whole numbers
