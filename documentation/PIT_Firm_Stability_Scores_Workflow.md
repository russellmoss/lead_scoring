# Point-in-Time (PIT) Firm Stability Scores

**Objective**: Calculate historical firm stability scores that reflect the firm's state at the time each contact entered our pipeline - NOT the current state.

**Why This Matters**: For lead scoring models, we need to use information that was available at the time of contact. Using today's firm stability score for a contact from June 2024 would be data leakage.

---

## Data Availability Check

### What We Have:

| Data | Table | Date Range | PIT Capability |
|------|-------|------------|----------------|
| Firm AUM Snapshots | `Firm_historicals` | Jan 2024 - Nov 2025 | ✅ Monthly snapshots |
| Rep Employment History | `contact_registered_employment_history` | Full history | ✅ Start/end dates |
| Contact Pipeline Data | Salesforce (your data) | Your date range | Need `created_date` |

### Limitation:
- **Firm AUM history starts Jan 2024** - contacts created before this can only get rep stability scores, not AUM scores
- **23 months of snapshots** - enough for 12-month lookback calculations starting from Jan 2025

---

## Step 1: Understand Your Pipeline Data Structure

### Cursor.ai Prompt:
```
First, I need to understand our Salesforce/pipeline data structure. Run a query to see what contact data we have and the date range of contacts entering our pipeline.
```

### SQL Query 1.1: Check Pipeline Data Structure
```sql
-- Adjust this query based on your actual Salesforce/pipeline table
-- This is a template - replace with your actual table and field names

SELECT 
  MIN(created_date) as earliest_contact,
  MAX(created_date) as latest_contact,
  COUNT(*) as total_contacts,
  COUNT(DISTINCT firm_crd) as unique_firms  -- or whatever field links to FINTRX
FROM `your_project.your_dataset.pipeline_contacts`
WHERE created_date >= '2024-01-01';
```

### Expected Output:
- Date range of contacts in pipeline
- Whether contacts have firm CRD linkage

---

## Step 2: Build Point-in-Time Rep Stability Score Function

### Cursor.ai Prompt:
```
Create a query that calculates the Rep Stability Score for a firm as of a specific historical date. This needs to look at departures and arrivals in the 12 months PRIOR to that date.
```

### SQL Query 2.1: PIT Rep Movement Calculation
```sql
-- Calculate rep departures and arrivals for a firm as of a specific point in time
-- This is a reusable pattern for any historical date

DECLARE target_date DATE DEFAULT DATE('2024-06-01');  -- Example: calculate as of June 2024
DECLARE lookback_months INT64 DEFAULT 12;

WITH 
-- Calculate departures in the 12 months before target_date
pit_departures AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    COUNT(*) as departures_12mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(target_date, INTERVAL 6 MONTH)) as departures_6mo
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    AND PREVIOUS_REGISTRATION_COMPANY_END_DATE < target_date  -- Before our point in time
    AND PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(target_date, INTERVAL lookback_months MONTH)
  GROUP BY firm_crd
),

-- Calculate arrivals in the 12 months before target_date
pit_arrivals AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    COUNT(*) as arrivals_12mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(target_date, INTERVAL 6 MONTH)) as arrivals_6mo
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE < target_date  -- Before our point in time
    AND PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(target_date, INTERVAL lookback_months MONTH)
  GROUP BY firm_crd
),

-- Estimate headcount as of target_date
-- Count reps whose employment spans the target date
pit_headcount AS (
  SELECT 
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    COUNT(DISTINCT RIA_CONTACT_CRD_ID) as rep_count_at_date
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE <= target_date
    AND (PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
         OR PREVIOUS_REGISTRATION_COMPANY_END_DATE > target_date)
  GROUP BY firm_crd
)

SELECT 
  f.CRD_ID as firm_crd,
  f.NAME as firm_name,
  target_date as score_as_of_date,
  
  -- Raw metrics
  COALESCE(h.rep_count_at_date, 0) as rep_count,
  COALESCE(d.departures_12mo, 0) as departures_12mo,
  COALESCE(d.departures_6mo, 0) as departures_6mo,
  COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
  COALESCE(a.arrivals_6mo, 0) as arrivals_6mo,
  
  -- Net change
  COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as net_reps_12mo,
  
  -- Turnover rate
  CASE 
    WHEN h.rep_count_at_date > 0 
    THEN ROUND(COALESCE(d.departures_12mo, 0) * 100.0 / h.rep_count_at_date, 2)
    ELSE 0
  END as turnover_rate_12mo_pct,
  
  -- REP STABILITY SCORE (0-100, higher = more stable)
  ROUND(GREATEST(0, LEAST(100,
    100 - (
      -- Penalize high turnover (2 points per percentage point of turnover)
      CASE WHEN h.rep_count_at_date > 0 
        THEN (COALESCE(d.departures_12mo, 0) * 100.0 / h.rep_count_at_date) * 2
        ELSE 0 
      END
      -- Penalize net losses (5 points per net rep lost)
      + CASE WHEN COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) < 0 
          THEN ABS(COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0)) * 5
          ELSE 0 
        END
    )
  )), 1) as rep_stability_score

FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f
LEFT JOIN pit_departures d ON f.CRD_ID = d.firm_crd
LEFT JOIN pit_arrivals a ON f.CRD_ID = a.firm_crd
LEFT JOIN pit_headcount h ON f.CRD_ID = h.firm_crd
WHERE f.CRD_ID IS NOT NULL
  AND COALESCE(h.rep_count_at_date, 0) >= 5  -- Focus on firms with meaningful headcount
ORDER BY rep_stability_score ASC
LIMIT 100;
```

---

## Step 3: Build Point-in-Time AUM Growth Score Function

### Cursor.ai Prompt:
```
Create a query that calculates the AUM Growth Score for a firm as of a specific historical date, using the Firm_historicals monthly snapshots.
```

### SQL Query 3.1: PIT AUM Growth Calculation
```sql
-- Calculate AUM growth score for a firm as of a specific point in time
-- Uses Firm_historicals monthly snapshots

DECLARE target_date DATE DEFAULT DATE('2024-06-01');  -- Calculate as of June 2024
DECLARE target_year INT64 DEFAULT EXTRACT(YEAR FROM target_date);
DECLARE target_month INT64 DEFAULT EXTRACT(MONTH FROM target_date);

WITH 
-- Get the snapshot closest to (but before) target date
current_snapshot AS (
  SELECT 
    RIA_INVESTOR_CRD_ID as firm_crd,
    TOTAL_AUM as current_aum,
    YEAR,
    MONTH
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
  WHERE DATE(YEAR, MONTH, 1) < target_date  -- Before target date
    AND TOTAL_AUM IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY RIA_INVESTOR_CRD_ID 
    ORDER BY YEAR DESC, MONTH DESC
  ) = 1
),

-- Get snapshot from ~12 months before target
historical_snapshot AS (
  SELECT 
    RIA_INVESTOR_CRD_ID as firm_crd,
    TOTAL_AUM as aum_12mo_ago,
    YEAR,
    MONTH
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
  WHERE DATE(YEAR, MONTH, 1) < DATE_SUB(target_date, INTERVAL 11 MONTH)
    AND DATE(YEAR, MONTH, 1) >= DATE_SUB(target_date, INTERVAL 13 MONTH)
    AND TOTAL_AUM IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY RIA_INVESTOR_CRD_ID 
    ORDER BY YEAR DESC, MONTH DESC
  ) = 1
),

-- Get snapshot from ~6 months before target
snapshot_6mo AS (
  SELECT 
    RIA_INVESTOR_CRD_ID as firm_crd,
    TOTAL_AUM as aum_6mo_ago
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
  WHERE DATE(YEAR, MONTH, 1) < DATE_SUB(target_date, INTERVAL 5 MONTH)
    AND DATE(YEAR, MONTH, 1) >= DATE_SUB(target_date, INTERVAL 7 MONTH)
    AND TOTAL_AUM IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY RIA_INVESTOR_CRD_ID 
    ORDER BY YEAR DESC, MONTH DESC
  ) = 1
)

SELECT 
  f.CRD_ID as firm_crd,
  f.NAME as firm_name,
  target_date as score_as_of_date,
  
  -- AUM values
  c.current_aum,
  s6.aum_6mo_ago,
  h.aum_12mo_ago,
  
  -- Growth percentages
  CASE WHEN s6.aum_6mo_ago > 0 
    THEN ROUND((c.current_aum - s6.aum_6mo_ago) * 100.0 / s6.aum_6mo_ago, 2)
  END as aum_growth_pct_6mo,
  
  CASE WHEN h.aum_12mo_ago > 0 
    THEN ROUND((c.current_aum - h.aum_12mo_ago) * 100.0 / h.aum_12mo_ago, 2)
  END as aum_growth_pct_12mo,
  
  -- AUM GROWTH SCORE (0-100, higher = better growth)
  -- Score of 50 = flat, >50 = growing, <50 = declining
  ROUND(GREATEST(0, LEAST(100,
    50 + COALESCE(
      CASE WHEN h.aum_12mo_ago > 0 
        THEN LEAST(50, GREATEST(-50, (c.current_aum - h.aum_12mo_ago) * 100.0 / h.aum_12mo_ago))
      END, 
      0
    )
  )), 1) as aum_growth_score

FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f
LEFT JOIN current_snapshot c ON f.CRD_ID = c.firm_crd
LEFT JOIN historical_snapshot h ON f.CRD_ID = h.firm_crd
LEFT JOIN snapshot_6mo s6 ON f.CRD_ID = s6.firm_crd
WHERE f.CRD_ID IS NOT NULL
  AND c.current_aum IS NOT NULL
ORDER BY aum_growth_score ASC
LIMIT 100;
```

---

## Step 4: Build Complete PIT Firm Stability Score Table

### Cursor.ai Prompt:
```
Now combine both scores into a complete point-in-time firm stability calculation that we can run for any historical month. This will create a table of firm scores by month.
```

### SQL Query 4.1: Generate Monthly Firm Stability Scores (Jan 2024 - Nov 2025)
```sql
-- Generate firm stability scores for each month from Jan 2024 to Nov 2025
-- This creates a lookup table we can join to pipeline contacts

WITH 
-- Generate all months we want to score
months_to_score AS (
  SELECT DATE(year, month, 1) as score_month
  FROM UNNEST(GENERATE_ARRAY(2024, 2025)) as year,
       UNNEST(GENERATE_ARRAY(1, 12)) as month
  WHERE DATE(year, month, 1) <= DATE('2025-11-01')
    AND DATE(year, month, 1) >= DATE('2024-02-01')  -- Need at least 1 month of history
),

-- Get all firms
firms AS (
  SELECT DISTINCT CRD_ID as firm_crd, NAME as firm_name
  FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current`
  WHERE CRD_ID IS NOT NULL
),

-- Cross join to create firm x month combinations
firm_months AS (
  SELECT 
    f.firm_crd,
    f.firm_name,
    m.score_month
  FROM firms f
  CROSS JOIN months_to_score m
),

-- Calculate departures for each firm-month combination
departures AS (
  SELECT
    fm.firm_crd,
    fm.score_month,
    COUNTIF(
      e.PREVIOUS_REGISTRATION_COMPANY_END_DATE < fm.score_month
      AND e.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(fm.score_month, INTERVAL 12 MONTH)
    ) as departures_12mo,
    COUNTIF(
      e.PREVIOUS_REGISTRATION_COMPANY_END_DATE < fm.score_month
      AND e.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(fm.score_month, INTERVAL 6 MONTH)
    ) as departures_6mo
  FROM firm_months fm
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history` e
    ON e.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = fm.firm_crd
    AND e.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
  GROUP BY fm.firm_crd, fm.score_month
),

-- Calculate arrivals for each firm-month combination
arrivals AS (
  SELECT
    fm.firm_crd,
    fm.score_month,
    COUNTIF(
      e.PREVIOUS_REGISTRATION_COMPANY_START_DATE < fm.score_month
      AND e.PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(fm.score_month, INTERVAL 12 MONTH)
    ) as arrivals_12mo,
    COUNTIF(
      e.PREVIOUS_REGISTRATION_COMPANY_START_DATE < fm.score_month
      AND e.PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(fm.score_month, INTERVAL 6 MONTH)
    ) as arrivals_6mo
  FROM firm_months fm
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history` e
    ON e.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = fm.firm_crd
  GROUP BY fm.firm_crd, fm.score_month
),

-- Calculate headcount at each point in time
headcount AS (
  SELECT 
    fm.firm_crd,
    fm.score_month,
    COUNT(DISTINCT e.RIA_CONTACT_CRD_ID) as rep_count_at_date
  FROM firm_months fm
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history` e
    ON e.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = fm.firm_crd
    AND e.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= fm.score_month
    AND (e.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
         OR e.PREVIOUS_REGISTRATION_COMPANY_END_DATE > fm.score_month)
  GROUP BY fm.firm_crd, fm.score_month
),

-- Get AUM from historical snapshots
aum_current AS (
  SELECT 
    fm.firm_crd,
    fm.score_month,
    h.TOTAL_AUM as current_aum
  FROM firm_months fm
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h
    ON h.RIA_INVESTOR_CRD_ID = fm.firm_crd
    AND DATE(h.YEAR, h.MONTH, 1) = DATE_SUB(fm.score_month, INTERVAL 1 MONTH)
),

aum_12mo_ago AS (
  SELECT 
    fm.firm_crd,
    fm.score_month,
    h.TOTAL_AUM as aum_12mo_ago
  FROM firm_months fm
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h
    ON h.RIA_INVESTOR_CRD_ID = fm.firm_crd
    AND DATE(h.YEAR, h.MONTH, 1) = DATE_SUB(fm.score_month, INTERVAL 13 MONTH)
)

SELECT 
  fm.firm_crd,
  fm.firm_name,
  fm.score_month,
  EXTRACT(YEAR FROM fm.score_month) as score_year,
  EXTRACT(MONTH FROM fm.score_month) as score_month_num,
  
  -- Raw metrics
  COALESCE(hc.rep_count_at_date, 0) as rep_count,
  COALESCE(d.departures_12mo, 0) as departures_12mo,
  COALESCE(d.departures_6mo, 0) as departures_6mo,
  COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
  COALESCE(a.arrivals_6mo, 0) as arrivals_6mo,
  COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as net_reps_12mo,
  
  -- Turnover rate
  CASE 
    WHEN hc.rep_count_at_date > 0 
    THEN ROUND(COALESCE(d.departures_12mo, 0) * 100.0 / hc.rep_count_at_date, 2)
    ELSE 0
  END as turnover_rate_12mo_pct,
  
  -- AUM metrics
  ac.current_aum,
  ah.aum_12mo_ago,
  CASE WHEN ah.aum_12mo_ago > 0 
    THEN ROUND((ac.current_aum - ah.aum_12mo_ago) * 100.0 / ah.aum_12mo_ago, 2)
  END as aum_growth_pct_12mo,
  
  -- SCORES --
  
  -- Rep Stability Score (0-100, higher = more stable)
  ROUND(GREATEST(0, LEAST(100,
    100 - (
      CASE WHEN hc.rep_count_at_date > 0 
        THEN (COALESCE(d.departures_12mo, 0) * 100.0 / hc.rep_count_at_date) * 2
        ELSE 0 
      END
      + CASE WHEN COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) < 0 
          THEN ABS(COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0)) * 5
          ELSE 0 
        END
    )
  )), 1) as rep_stability_score,
  
  -- AUM Growth Score (0-100, 50 = flat)
  ROUND(GREATEST(0, LEAST(100,
    50 + COALESCE(
      CASE WHEN ah.aum_12mo_ago > 0 
        THEN LEAST(50, GREATEST(-50, (ac.current_aum - ah.aum_12mo_ago) * 100.0 / ah.aum_12mo_ago))
      END, 
      0
    )
  )), 1) as aum_growth_score,
  
  -- Composite Firm Stability Score (weighted: 60% rep, 40% AUM)
  ROUND(GREATEST(0, LEAST(100,
    0.6 * GREATEST(0, LEAST(100,
      100 - (
        CASE WHEN hc.rep_count_at_date > 0 
          THEN (COALESCE(d.departures_12mo, 0) * 100.0 / hc.rep_count_at_date) * 2
          ELSE 0 
        END
        + CASE WHEN COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) < 0 
            THEN ABS(COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0)) * 5
            ELSE 0 
          END
      )
    ))
    + 0.4 * GREATEST(0, LEAST(100,
      50 + COALESCE(
        CASE WHEN ah.aum_12mo_ago > 0 
          THEN LEAST(50, GREATEST(-50, (ac.current_aum - ah.aum_12mo_ago) * 100.0 / ah.aum_12mo_ago))
        END, 
        0
      )
    ))
  )), 1) as composite_stability_score,
  
  -- Categorical status
  CASE 
    WHEN GREATEST(0, LEAST(100,
      100 - (
        CASE WHEN hc.rep_count_at_date > 0 
          THEN (COALESCE(d.departures_12mo, 0) * 100.0 / hc.rep_count_at_date) * 2
          ELSE 0 
        END
        + CASE WHEN COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) < 0 
            THEN ABS(COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0)) * 5
            ELSE 0 
          END
      )
    )) < 30 THEN 'BLEEDING'
    WHEN GREATEST(0, LEAST(100,
      100 - (
        CASE WHEN hc.rep_count_at_date > 0 
          THEN (COALESCE(d.departures_12mo, 0) * 100.0 / hc.rep_count_at_date) * 2
          ELSE 0 
        END
        + CASE WHEN COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) < 0 
            THEN ABS(COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0)) * 5
            ELSE 0 
          END
      )
    )) < 50 THEN 'AT_RISK'
    WHEN GREATEST(0, LEAST(100,
      100 - (
        CASE WHEN hc.rep_count_at_date > 0 
          THEN (COALESCE(d.departures_12mo, 0) * 100.0 / hc.rep_count_at_date) * 2
          ELSE 0 
        END
        + CASE WHEN COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) < 0 
            THEN ABS(COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0)) * 5
            ELSE 0 
          END
      )
    )) >= 70 THEN 'WINNING'
    ELSE 'STABLE'
  END as firm_status

FROM firm_months fm
LEFT JOIN departures d ON fm.firm_crd = d.firm_crd AND fm.score_month = d.score_month
LEFT JOIN arrivals a ON fm.firm_crd = a.firm_crd AND fm.score_month = a.score_month
LEFT JOIN headcount hc ON fm.firm_crd = hc.firm_crd AND fm.score_month = hc.score_month
LEFT JOIN aum_current ac ON fm.firm_crd = ac.firm_crd AND fm.score_month = ac.score_month
LEFT JOIN aum_12mo_ago ah ON fm.firm_crd = ah.firm_crd AND fm.score_month = ah.score_month

WHERE COALESCE(hc.rep_count_at_date, 0) >= 5  -- Only firms with meaningful headcount
ORDER BY fm.firm_crd, fm.score_month;
```

### ⚠️ Performance Note:
This query will be VERY large (45K firms × 22 months = ~1M rows). Consider:
1. Running for a subset of firms first (e.g., firms with contacts in your pipeline)
2. Saving results to a table rather than running ad-hoc
3. Breaking into batches by date range

---

## Step 5: Create Persistent Table for Firm Stability Scores

### Cursor.ai Prompt:
```
Create a permanent table to store the monthly firm stability scores. This will be our lookup table for joining to pipeline contacts.
```

### SQL Query 5.1: Create the Scores Table
```sql
-- Create a table to store monthly firm stability scores
CREATE OR REPLACE TABLE `savvy-gtm-analytics.FinTrx_data.firm_stability_scores_monthly` AS

-- [Insert the full query from Step 4 here]
-- This creates a persistent table we can query quickly

SELECT 
  firm_crd,
  firm_name,
  score_month,
  score_year,
  score_month_num,
  rep_count,
  departures_12mo,
  arrivals_12mo,
  net_reps_12mo,
  turnover_rate_12mo_pct,
  current_aum,
  aum_growth_pct_12mo,
  rep_stability_score,
  aum_growth_score,
  composite_stability_score,
  firm_status
FROM (
  -- [Full query from Step 4]
);
```

---

## Step 6: Join Pipeline Contacts to PIT Firm Stability Scores

### Cursor.ai Prompt:
```
Now create a query that joins our pipeline contacts to their point-in-time firm stability scores based on when they entered the pipeline.
```

### SQL Query 6.1: Join Contacts to PIT Scores
```sql
-- Join pipeline contacts to point-in-time firm stability scores
-- Each contact gets the firm score from the month BEFORE they entered the pipeline

WITH pipeline_contacts AS (
  -- Replace with your actual pipeline/Salesforce data
  SELECT 
    contact_id,
    contact_name,
    firm_crd,  -- The FINTRX firm CRD linked to this contact
    created_date,
    -- Calculate the score month (1 month before contact creation)
    DATE_TRUNC(DATE_SUB(created_date, INTERVAL 1 MONTH), MONTH) as score_lookup_month
  FROM `your_project.your_dataset.pipeline_contacts`
  WHERE created_date >= '2024-02-01'  -- Must have historical data available
)

SELECT 
  pc.contact_id,
  pc.contact_name,
  pc.firm_crd,
  pc.created_date,
  pc.score_lookup_month,
  
  -- Firm stability scores AS OF when contact entered pipeline
  fs.firm_name,
  fs.rep_count,
  fs.departures_12mo,
  fs.arrivals_12mo,
  fs.net_reps_12mo,
  fs.turnover_rate_12mo_pct,
  fs.current_aum as aum_at_contact_date,
  fs.aum_growth_pct_12mo,
  
  -- THE KEY SCORES (Point-in-Time)
  fs.rep_stability_score,
  fs.aum_growth_score,
  fs.composite_stability_score,
  fs.firm_status

FROM pipeline_contacts pc
LEFT JOIN `savvy-gtm-analytics.FinTrx_data.firm_stability_scores_monthly` fs
  ON pc.firm_crd = fs.firm_crd
  AND DATE_TRUNC(pc.score_lookup_month, MONTH) = fs.score_month;
```

### SQL Query 6.2: Analyze Score Distribution for Pipeline Contacts
```sql
-- Analyze the distribution of firm stability scores for pipeline contacts
-- Useful for understanding if "bleeding firm" contacts convert differently

WITH scored_contacts AS (
  -- [Use query 6.1 to get contacts with scores]
  SELECT 
    pc.*,
    fs.rep_stability_score,
    fs.aum_growth_score,
    fs.composite_stability_score,
    fs.firm_status
  FROM pipeline_contacts pc
  LEFT JOIN firm_stability_scores_monthly fs
    ON pc.firm_crd = fs.firm_crd
    AND DATE_TRUNC(DATE_SUB(pc.created_date, INTERVAL 1 MONTH), MONTH) = fs.score_month
)

SELECT 
  firm_status,
  COUNT(*) as contact_count,
  ROUND(AVG(rep_stability_score), 1) as avg_rep_stability,
  ROUND(AVG(aum_growth_score), 1) as avg_aum_growth,
  ROUND(AVG(composite_stability_score), 1) as avg_composite,
  
  -- Add conversion metrics if available
  -- COUNTIF(converted = TRUE) as conversions,
  -- ROUND(COUNTIF(converted = TRUE) * 100.0 / COUNT(*), 2) as conversion_rate
  
FROM scored_contacts
WHERE rep_stability_score IS NOT NULL
GROUP BY firm_status
ORDER BY avg_composite ASC;
```

---

## Step 7: Validate Historical Scores

### Cursor.ai Prompt:
```
Validate the historical scores by checking a few specific firms at specific points in time to make sure the calculations are working correctly.
```

### SQL Query 7.1: Spot Check a Known Firm
```sql
-- Spot check: Look at score history for a specific firm
-- Replace with a firm you know had significant changes

SELECT 
  score_month,
  rep_count,
  departures_12mo,
  arrivals_12mo,
  net_reps_12mo,
  turnover_rate_12mo_pct,
  ROUND(current_aum / 1000000, 1) as aum_millions,
  aum_growth_pct_12mo,
  rep_stability_score,
  aum_growth_score,
  composite_stability_score,
  firm_status
FROM `savvy-gtm-analytics.FinTrx_data.firm_stability_scores_monthly`
WHERE firm_name LIKE '%Cambridge Investment%'  -- Example firm
ORDER BY score_month;
```

### SQL Query 7.2: Check Score Trends Over Time
```sql
-- See how firm stability scores have trended over time
SELECT 
  score_month,
  COUNT(*) as firms_scored,
  ROUND(AVG(rep_stability_score), 1) as avg_rep_stability,
  ROUND(AVG(aum_growth_score), 1) as avg_aum_growth,
  ROUND(AVG(composite_stability_score), 1) as avg_composite,
  COUNTIF(firm_status = 'BLEEDING') as bleeding_firms,
  COUNTIF(firm_status = 'AT_RISK') as at_risk_firms,
  COUNTIF(firm_status = 'STABLE') as stable_firms,
  COUNTIF(firm_status = 'WINNING') as winning_firms
FROM `savvy-gtm-analytics.FinTrx_data.firm_stability_scores_monthly`
GROUP BY score_month
ORDER BY score_month;
```

---

## Summary: What You Get

After running this workflow, you'll have:

### 1. A Monthly Firm Stability Score Table
- One row per firm per month (Feb 2024 - Nov 2025)
- Three scores: Rep Stability, AUM Growth, Composite
- Categorical status: BLEEDING, AT_RISK, STABLE, WINNING

### 2. Point-in-Time Scoring for Pipeline Contacts
- Each contact gets the firm's score from BEFORE they entered the pipeline
- No data leakage - scores reflect what was known at the time
- Ready to use as features in lead scoring models

### 3. Historical Trend Analysis
- Track how firm stability has changed over time
- Identify firms that are newly bleeding vs. chronically unstable
- Validate score calculations against known events

---

## Limitations

1. **AUM History Limited**: Firm_historicals starts Jan 2024, so AUM growth scores before Feb 2025 have less than 12 months of lookback

2. **Employment History Completeness**: Some older employment records may be incomplete

3. **Score Coverage**: Not all firms will have scores (need ≥5 reps and some activity)

4. **Query Performance**: Full historical generation is compute-intensive - use batching

---

## Next Steps

1. Run Step 1-3 queries to validate data availability
2. Generate the full monthly scores table (Step 4-5)
3. Join to your pipeline data (Step 6)
4. Validate with spot checks (Step 7)
5. Analyze conversion rates by firm stability to validate predictive value
