# Firm Stability Analysis: Cursor.ai Agentic Workflow

**Objective**: Build a comprehensive "Firm Stability Score" to identify firms that are "bleeding" (losing reps and AUM) vs "winning" (gaining reps and AUM) for targeted recruiting.

**Output Location**: `C:\Users\russe\Big_Query\documentation\`

---

## Overview

This workflow will:
1. Explore data freshness and structure
2. Analyze rep movement patterns (arrivals vs departures)
3. Analyze AUM growth/decline trends
4. Build three scoring systems:
   - **Rep Stability Score** (people leaving/joining)
   - **AUM Growth Score** (asset growth/decline)
   - **Composite Firm Stability Score** (holistic)
5. Generate a comprehensive report

---

## Step 1: Verify Data Freshness & Structure

### Cursor.ai Prompt:
```
Using the BigQuery MCP, run the following SQL queries to understand the data freshness and structure for firm stability analysis. Execute each query and capture the results.
```

### SQL Query 1.1: Check Firm_historicals Date Range and Coverage
```sql
-- Check the date range and monthly coverage of Firm_historicals
SELECT 
  MIN(CONCAT(CAST(YEAR AS STRING), '-', LPAD(CAST(MONTH AS STRING), 2, '0'))) as earliest_snapshot,
  MAX(CONCAT(CAST(YEAR AS STRING), '-', LPAD(CAST(MONTH AS STRING), 2, '0'))) as latest_snapshot,
  COUNT(DISTINCT CONCAT(CAST(YEAR AS STRING), '-', LPAD(CAST(MONTH AS STRING), 2, '0'))) as num_months,
  COUNT(DISTINCT RIA_INVESTOR_CRD_ID) as unique_firms,
  COUNT(*) as total_snapshots
FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`;
```

### SQL Query 1.2: Check if Employee Counts are in Historical Snapshots
```sql
-- Check if NUM_OF_EMPLOYEES exists in Firm_historicals and its coverage
SELECT 
  YEAR,
  MONTH,
  COUNT(*) as total_firms,
  COUNTIF(NUM_OF_EMPLOYEES IS NOT NULL) as firms_with_employee_count,
  ROUND(COUNTIF(NUM_OF_EMPLOYEES IS NOT NULL) / COUNT(*) * 100, 2) as coverage_pct,
  AVG(NUM_OF_EMPLOYEES) as avg_employees
FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
GROUP BY YEAR, MONTH
ORDER BY YEAR DESC, MONTH DESC
LIMIT 24;
```

### SQL Query 1.3: Check Employment History Date Freshness
```sql
-- Check how recent the employment history data is
SELECT 
  MAX(PREVIOUS_REGISTRATION_COMPANY_START_DATE) as most_recent_start,
  MAX(PREVIOUS_REGISTRATION_COMPANY_END_DATE) as most_recent_end,
  COUNT(*) as total_employment_records,
  COUNT(DISTINCT RIA_CONTACT_CRD_ID) as unique_reps,
  COUNT(DISTINCT PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as unique_firms
FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`;
```

### SQL Query 1.4: Sample Employment History Structure
```sql
-- Look at recent employment changes to understand the data structure
SELECT 
  RIA_CONTACT_CRD_ID,
  PREVIOUS_REGISTRATION_COMPANY_CRD_ID,
  PREVIOUS_REGISTRATION_COMPANY_NAME,
  PREVIOUS_REGISTRATION_COMPANY_START_DATE,
  PREVIOUS_REGISTRATION_COMPANY_END_DATE,
  DATE_DIFF(
    COALESCE(PREVIOUS_REGISTRATION_COMPANY_END_DATE, CURRENT_DATE()),
    PREVIOUS_REGISTRATION_COMPANY_START_DATE,
    DAY
  ) as tenure_days
FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
ORDER BY PREVIOUS_REGISTRATION_COMPANY_END_DATE DESC
LIMIT 20;
```

### Expected Output:
Document findings about:
- Latest available snapshot date
- Whether employee counts are tracked historically
- How recent employment change data is
- Data freshness comparison (firm vs rep level)

---

## Step 2: Analyze Rep Movement Patterns

### Cursor.ai Prompt:
```
Execute the following SQL queries to analyze rep movement patterns at the firm level. We want to count departures and arrivals for each firm over 6, 12, and 18 month periods.
```

### SQL Query 2.1: Calculate Rep Departures by Firm (Last 18 Months)
```sql
-- Count rep departures (ended employment) by firm over different time periods
WITH departure_periods AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    PREVIOUS_REGISTRATION_COMPANY_NAME as firm_name,
    RIA_CONTACT_CRD_ID as rep_crd,
    PREVIOUS_REGISTRATION_COMPANY_END_DATE as departure_date,
    CASE 
      WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) THEN '6_months'
      WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) THEN '12_months'
      WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH) THEN '18_months'
      ELSE 'older'
    END as period
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    AND PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)
)
SELECT 
  firm_crd,
  firm_name,
  COUNTIF(period IN ('6_months')) as departures_6mo,
  COUNTIF(period IN ('6_months', '12_months')) as departures_12mo,
  COUNT(*) as departures_18mo
FROM departure_periods
GROUP BY firm_crd, firm_name
HAVING departures_18mo >= 5  -- Focus on firms with meaningful movement
ORDER BY departures_18mo DESC
LIMIT 100;
```

### SQL Query 2.2: Calculate Rep Arrivals by Firm (Last 18 Months)
```sql
-- Count rep arrivals (started employment) by firm over different time periods
WITH arrival_periods AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    PREVIOUS_REGISTRATION_COMPANY_NAME as firm_name,
    RIA_CONTACT_CRD_ID as rep_crd,
    PREVIOUS_REGISTRATION_COMPANY_START_DATE as arrival_date,
    CASE 
      WHEN PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH) THEN '6_months'
      WHEN PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) THEN '12_months'
      WHEN PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH) THEN '18_months'
      ELSE 'older'
    END as period
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)
)
SELECT 
  firm_crd,
  firm_name,
  COUNTIF(period IN ('6_months')) as arrivals_6mo,
  COUNTIF(period IN ('6_months', '12_months')) as arrivals_12mo,
  COUNT(*) as arrivals_18mo
FROM arrival_periods
GROUP BY firm_crd, firm_name
HAVING arrivals_18mo >= 5
ORDER BY arrivals_18mo DESC
LIMIT 100;
```

### SQL Query 2.3: Net Rep Movement by Firm (Combined View)
```sql
-- Calculate net rep movement (arrivals - departures) by firm
WITH departures AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    PREVIOUS_REGISTRATION_COMPANY_NAME as firm_name,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)) as departures_6mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)) as departures_12mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)) as departures_18mo
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    AND PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)
  GROUP BY firm_crd, firm_name
),
arrivals AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)) as arrivals_6mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)) as arrivals_12mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)) as arrivals_18mo
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)
  GROUP BY firm_crd
),
firm_size AS (
  SELECT 
    PRIMARY_FIRM as firm_crd,
    COUNT(*) as current_rep_count
  FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
  GROUP BY PRIMARY_FIRM
)
SELECT 
  d.firm_crd,
  d.firm_name,
  fs.current_rep_count,
  
  -- 6 month metrics
  COALESCE(a.arrivals_6mo, 0) as arrivals_6mo,
  d.departures_6mo,
  COALESCE(a.arrivals_6mo, 0) - d.departures_6mo as net_change_6mo,
  
  -- 12 month metrics
  COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
  d.departures_12mo,
  COALESCE(a.arrivals_12mo, 0) - d.departures_12mo as net_change_12mo,
  
  -- 18 month metrics
  COALESCE(a.arrivals_18mo, 0) as arrivals_18mo,
  d.departures_18mo,
  COALESCE(a.arrivals_18mo, 0) - d.departures_18mo as net_change_18mo,
  
  -- Turnover rate (departures as % of current headcount)
  CASE 
    WHEN fs.current_rep_count > 0 
    THEN ROUND(d.departures_12mo * 100.0 / fs.current_rep_count, 2)
    ELSE NULL
  END as turnover_rate_12mo_pct

FROM departures d
LEFT JOIN arrivals a ON d.firm_crd = a.firm_crd
LEFT JOIN firm_size fs ON d.firm_crd = fs.firm_crd
WHERE d.departures_18mo >= 3  -- At least some meaningful movement
ORDER BY net_change_12mo ASC  -- Most negative (bleeding) first
LIMIT 200;
```

### Expected Output:
- List of firms with most departures
- List of firms with most arrivals
- Net rep movement by firm (arrivals - departures)
- Turnover rates as percentage of current headcount

---

## Step 3: Analyze AUM Trends

### Cursor.ai Prompt:
```
Execute the following SQL queries to analyze AUM growth/decline trends for firms. We'll calculate AUM changes over 6, 12, and 18 month periods using the Firm_historicals monthly snapshots.
```

### SQL Query 3.1: Calculate AUM Growth by Firm
```sql
-- Calculate AUM growth rates over 6, 12, and 18 month periods
WITH monthly_aum AS (
  SELECT 
    RIA_INVESTOR_CRD_ID as firm_crd,
    YEAR,
    MONTH,
    TOTAL_AUM,
    DATE(YEAR, MONTH, 1) as snapshot_date
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
  WHERE TOTAL_AUM IS NOT NULL
),
current_aum AS (
  SELECT 
    firm_crd,
    TOTAL_AUM as current_aum,
    snapshot_date as current_date
  FROM monthly_aum
  WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM monthly_aum)
),
historical_aum AS (
  SELECT 
    m.firm_crd,
    c.current_aum,
    c.current_date,
    MAX(CASE WHEN DATE_DIFF(c.current_date, m.snapshot_date, MONTH) BETWEEN 5 AND 7 THEN m.TOTAL_AUM END) as aum_6mo_ago,
    MAX(CASE WHEN DATE_DIFF(c.current_date, m.snapshot_date, MONTH) BETWEEN 11 AND 13 THEN m.TOTAL_AUM END) as aum_12mo_ago,
    MAX(CASE WHEN DATE_DIFF(c.current_date, m.snapshot_date, MONTH) BETWEEN 17 AND 19 THEN m.TOTAL_AUM END) as aum_18mo_ago
  FROM monthly_aum m
  INNER JOIN current_aum c ON m.firm_crd = c.firm_crd
  GROUP BY m.firm_crd, c.current_aum, c.current_date
)
SELECT 
  h.firm_crd,
  f.NAME as firm_name,
  f.ENTITY_CLASSIFICATION,
  
  -- Current AUM
  h.current_aum,
  
  -- Historical AUM
  h.aum_6mo_ago,
  h.aum_12mo_ago,
  h.aum_18mo_ago,
  
  -- Absolute changes
  h.current_aum - h.aum_6mo_ago as aum_change_6mo,
  h.current_aum - h.aum_12mo_ago as aum_change_12mo,
  h.current_aum - h.aum_18mo_ago as aum_change_18mo,
  
  -- Percentage changes
  CASE WHEN h.aum_6mo_ago > 0 THEN ROUND((h.current_aum - h.aum_6mo_ago) * 100.0 / h.aum_6mo_ago, 2) END as aum_growth_pct_6mo,
  CASE WHEN h.aum_12mo_ago > 0 THEN ROUND((h.current_aum - h.aum_12mo_ago) * 100.0 / h.aum_12mo_ago, 2) END as aum_growth_pct_12mo,
  CASE WHEN h.aum_18mo_ago > 0 THEN ROUND((h.current_aum - h.aum_18mo_ago) * 100.0 / h.aum_18mo_ago, 2) END as aum_growth_pct_18mo

FROM historical_aum h
LEFT JOIN `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f ON h.firm_crd = f.CRD_ID
WHERE h.current_aum >= 100000000  -- Focus on firms with at least $100M AUM
  AND h.aum_12mo_ago IS NOT NULL
ORDER BY aum_growth_pct_12mo ASC  -- Most negative (bleeding) first
LIMIT 200;
```

### SQL Query 3.2: AUM Distribution Analysis
```sql
-- Understand the distribution of AUM changes to help with scoring thresholds
WITH aum_changes AS (
  SELECT 
    h1.RIA_INVESTOR_CRD_ID as firm_crd,
    h1.TOTAL_AUM as current_aum,
    h2.TOTAL_AUM as aum_12mo_ago,
    CASE 
      WHEN h2.TOTAL_AUM > 0 
      THEN (h1.TOTAL_AUM - h2.TOTAL_AUM) * 100.0 / h2.TOTAL_AUM 
    END as growth_pct_12mo
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h1
  INNER JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h2 
    ON h1.RIA_INVESTOR_CRD_ID = h2.RIA_INVESTOR_CRD_ID
  WHERE h1.YEAR = 2025 AND h1.MONTH = 11  -- Adjust to latest month
    AND h2.YEAR = 2024 AND h2.MONTH = 11  -- 12 months prior
    AND h1.TOTAL_AUM IS NOT NULL
    AND h2.TOTAL_AUM IS NOT NULL
    AND h2.TOTAL_AUM > 0
)
SELECT 
  'All Firms' as segment,
  COUNT(*) as firm_count,
  ROUND(AVG(growth_pct_12mo), 2) as avg_growth_pct,
  ROUND(STDDEV(growth_pct_12mo), 2) as stddev_growth_pct,
  APPROX_QUANTILES(growth_pct_12mo, 100)[OFFSET(10)] as p10_growth,
  APPROX_QUANTILES(growth_pct_12mo, 100)[OFFSET(25)] as p25_growth,
  APPROX_QUANTILES(growth_pct_12mo, 100)[OFFSET(50)] as median_growth,
  APPROX_QUANTILES(growth_pct_12mo, 100)[OFFSET(75)] as p75_growth,
  APPROX_QUANTILES(growth_pct_12mo, 100)[OFFSET(90)] as p90_growth,
  COUNTIF(growth_pct_12mo < 0) as firms_losing_aum,
  COUNTIF(growth_pct_12mo > 0) as firms_gaining_aum
FROM aum_changes
WHERE growth_pct_12mo BETWEEN -100 AND 500;  -- Exclude extreme outliers
```

### Expected Output:
- AUM growth rates by firm (6, 12, 18 months)
- Distribution statistics for setting scoring thresholds
- Identification of firms losing vs gaining AUM

---

## Step 4: Build Combined Firm Stability View

### Cursor.ai Prompt:
```
Execute the following SQL to create a comprehensive view combining rep movement and AUM trends. This will be the foundation for the firm stability scores.
```

### SQL Query 4.1: Comprehensive Firm Stability Analysis
```sql
-- Comprehensive firm stability analysis combining rep movement and AUM trends
WITH 
-- Rep departures by firm
departures AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)) as departures_6mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)) as departures_12mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)) as departures_18mo
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    AND PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)
  GROUP BY firm_crd
),

-- Rep arrivals by firm
arrivals AS (
  SELECT
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)) as arrivals_6mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)) as arrivals_12mo,
    COUNTIF(PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)) as arrivals_18mo
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 18 MONTH)
  GROUP BY firm_crd
),

-- Current firm stats
firm_stats AS (
  SELECT 
    PRIMARY_FIRM as firm_crd,
    COUNT(*) as current_rep_count
  FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
  GROUP BY PRIMARY_FIRM
),

-- AUM trends
aum_trends AS (
  SELECT 
    h_current.RIA_INVESTOR_CRD_ID as firm_crd,
    h_current.TOTAL_AUM as current_aum,
    h_6mo.TOTAL_AUM as aum_6mo_ago,
    h_12mo.TOTAL_AUM as aum_12mo_ago,
    h_18mo.TOTAL_AUM as aum_18mo_ago,
    
    -- Growth percentages
    CASE WHEN h_6mo.TOTAL_AUM > 0 
      THEN (h_current.TOTAL_AUM - h_6mo.TOTAL_AUM) * 100.0 / h_6mo.TOTAL_AUM 
    END as aum_growth_pct_6mo,
    CASE WHEN h_12mo.TOTAL_AUM > 0 
      THEN (h_current.TOTAL_AUM - h_12mo.TOTAL_AUM) * 100.0 / h_12mo.TOTAL_AUM 
    END as aum_growth_pct_12mo,
    CASE WHEN h_18mo.TOTAL_AUM > 0 
      THEN (h_current.TOTAL_AUM - h_18mo.TOTAL_AUM) * 100.0 / h_18mo.TOTAL_AUM 
    END as aum_growth_pct_18mo
    
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h_current
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h_6mo
    ON h_current.RIA_INVESTOR_CRD_ID = h_6mo.RIA_INVESTOR_CRD_ID
    AND h_6mo.YEAR = 2025 AND h_6mo.MONTH = 5  -- Adjust based on current date
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h_12mo
    ON h_current.RIA_INVESTOR_CRD_ID = h_12mo.RIA_INVESTOR_CRD_ID
    AND h_12mo.YEAR = 2024 AND h_12mo.MONTH = 11
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h_18mo
    ON h_current.RIA_INVESTOR_CRD_ID = h_18mo.RIA_INVESTOR_CRD_ID
    AND h_18mo.YEAR = 2024 AND h_18mo.MONTH = 5
  WHERE h_current.YEAR = 2025 AND h_current.MONTH = 11  -- Latest snapshot
    AND h_current.TOTAL_AUM IS NOT NULL
)

SELECT 
  f.CRD_ID as firm_crd,
  f.NAME as firm_name,
  f.ENTITY_CLASSIFICATION,
  f.MAIN_OFFICE_STATE,
  
  -- Current metrics
  COALESCE(fs.current_rep_count, 0) as current_rep_count,
  aum.current_aum,
  
  -- Rep movement metrics
  COALESCE(d.departures_6mo, 0) as departures_6mo,
  COALESCE(d.departures_12mo, 0) as departures_12mo,
  COALESCE(d.departures_18mo, 0) as departures_18mo,
  COALESCE(a.arrivals_6mo, 0) as arrivals_6mo,
  COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
  COALESCE(a.arrivals_18mo, 0) as arrivals_18mo,
  
  -- Net rep movement
  COALESCE(a.arrivals_6mo, 0) - COALESCE(d.departures_6mo, 0) as net_reps_6mo,
  COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as net_reps_12mo,
  COALESCE(a.arrivals_18mo, 0) - COALESCE(d.departures_18mo, 0) as net_reps_18mo,
  
  -- Turnover rate
  CASE 
    WHEN fs.current_rep_count > 0 
    THEN ROUND(COALESCE(d.departures_12mo, 0) * 100.0 / fs.current_rep_count, 2)
    ELSE 0
  END as turnover_rate_12mo_pct,
  
  -- AUM metrics
  aum.aum_6mo_ago,
  aum.aum_12mo_ago,
  aum.aum_18mo_ago,
  ROUND(aum.aum_growth_pct_6mo, 2) as aum_growth_pct_6mo,
  ROUND(aum.aum_growth_pct_12mo, 2) as aum_growth_pct_12mo,
  ROUND(aum.aum_growth_pct_18mo, 2) as aum_growth_pct_18mo

FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f
LEFT JOIN departures d ON f.CRD_ID = d.firm_crd
LEFT JOIN arrivals a ON f.CRD_ID = a.firm_crd
LEFT JOIN firm_stats fs ON f.CRD_ID = fs.firm_crd
LEFT JOIN aum_trends aum ON f.CRD_ID = aum.firm_crd
WHERE f.CRD_ID IS NOT NULL
  AND (
    COALESCE(d.departures_12mo, 0) > 0  -- Has some rep movement
    OR COALESCE(a.arrivals_12mo, 0) > 0
    OR aum.current_aum >= 50000000  -- Or has significant AUM
  )
ORDER BY net_reps_12mo ASC, aum_growth_pct_12mo ASC
LIMIT 500;
```

### Expected Output:
- Complete firm stability data combining rep movement and AUM trends
- Base data for building scoring models

---

## Step 5: Build Scoring Methodologies

### Cursor.ai Prompt:
```
Execute the following SQL queries to develop and validate three scoring methodologies: Rep Stability Score, AUM Growth Score, and Composite Firm Stability Score.
```

### SQL Query 5.1: Calculate Percentile-Based Scores
```sql
-- Calculate percentile-based scores for rep stability and AUM growth
WITH base_data AS (
  -- [Use the comprehensive query from Step 4, abbreviated here]
  SELECT 
    f.CRD_ID as firm_crd,
    f.NAME as firm_name,
    COALESCE(fs.current_rep_count, 0) as current_rep_count,
    COALESCE(d.departures_12mo, 0) as departures_12mo,
    COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
    COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as net_reps_12mo,
    CASE 
      WHEN fs.current_rep_count > 0 
      THEN COALESCE(d.departures_12mo, 0) * 100.0 / fs.current_rep_count
      ELSE 0
    END as turnover_rate_12mo,
    aum.current_aum,
    aum.aum_growth_pct_12mo
  FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f
  LEFT JOIN (
    SELECT PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
           COUNT(*) as departures_12mo
    FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY firm_crd
  ) d ON f.CRD_ID = d.firm_crd
  LEFT JOIN (
    SELECT PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
           COUNT(*) as arrivals_12mo
    FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY firm_crd
  ) a ON f.CRD_ID = a.firm_crd
  LEFT JOIN (
    SELECT PRIMARY_FIRM as firm_crd, COUNT(*) as current_rep_count
    FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
    GROUP BY PRIMARY_FIRM
  ) fs ON f.CRD_ID = fs.firm_crd
  LEFT JOIN (
    SELECT 
      h1.RIA_INVESTOR_CRD_ID as firm_crd,
      h1.TOTAL_AUM as current_aum,
      CASE WHEN h2.TOTAL_AUM > 0 
        THEN (h1.TOTAL_AUM - h2.TOTAL_AUM) * 100.0 / h2.TOTAL_AUM 
      END as aum_growth_pct_12mo
    FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h1
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h2
      ON h1.RIA_INVESTOR_CRD_ID = h2.RIA_INVESTOR_CRD_ID
      AND h2.YEAR = 2024 AND h2.MONTH = 11
    WHERE h1.YEAR = 2025 AND h1.MONTH = 11
      AND h1.TOTAL_AUM IS NOT NULL
  ) aum ON f.CRD_ID = aum.firm_crd
  WHERE f.CRD_ID IS NOT NULL
    AND (COALESCE(d.departures_12mo, 0) > 0 OR COALESCE(a.arrivals_12mo, 0) > 0 OR aum.current_aum >= 10000000)
),

scored_data AS (
  SELECT 
    *,
    
    -- Rep Stability Score (0-100, lower = more bleeding/unstable)
    -- Based on turnover rate and net rep change
    100 - LEAST(100, 
      COALESCE(turnover_rate_12mo, 0) * 2  -- Penalize high turnover
      + CASE WHEN net_reps_12mo < 0 THEN ABS(net_reps_12mo) * 5 ELSE 0 END  -- Penalize net losses
    ) as rep_stability_score_raw,
    
    -- AUM Growth Score (0-100, higher = better growth)
    -- Normalized growth rate
    50 + LEAST(50, GREATEST(-50, COALESCE(aum_growth_pct_12mo, 0))) as aum_growth_score_raw
    
  FROM base_data
)

SELECT 
  firm_crd,
  firm_name,
  current_rep_count,
  departures_12mo,
  arrivals_12mo,
  net_reps_12mo,
  ROUND(turnover_rate_12mo, 2) as turnover_rate_12mo_pct,
  current_aum,
  ROUND(aum_growth_pct_12mo, 2) as aum_growth_pct_12mo,
  
  -- Individual Scores (0-100)
  ROUND(GREATEST(0, LEAST(100, rep_stability_score_raw)), 1) as rep_stability_score,
  ROUND(GREATEST(0, LEAST(100, aum_growth_score_raw)), 1) as aum_growth_score,
  
  -- Composite Firm Stability Score (weighted average)
  ROUND(GREATEST(0, LEAST(100, 
    0.6 * GREATEST(0, LEAST(100, rep_stability_score_raw))  -- 60% weight on rep stability
    + 0.4 * GREATEST(0, LEAST(100, aum_growth_score_raw))   -- 40% weight on AUM growth
  )), 1) as composite_stability_score,
  
  -- Categorical labels
  CASE 
    WHEN rep_stability_score_raw < 30 AND aum_growth_score_raw < 40 THEN 'BLEEDING'
    WHEN rep_stability_score_raw < 50 OR aum_growth_score_raw < 40 THEN 'AT_RISK'
    WHEN rep_stability_score_raw >= 70 AND aum_growth_score_raw >= 60 THEN 'WINNING'
    ELSE 'STABLE'
  END as firm_status

FROM scored_data
WHERE current_rep_count >= 5  -- Focus on firms with meaningful headcount
ORDER BY composite_stability_score ASC  -- Lowest (bleeding) first
LIMIT 500;
```

### SQL Query 5.2: Identify Top Bleeding Firms for Recruiting Targets
```sql
-- Identify top "bleeding" firms (losing reps and/or AUM) as recruiting targets
WITH firm_scores AS (
  -- [Same base calculation as above, abbreviated]
  SELECT 
    f.CRD_ID as firm_crd,
    f.NAME as firm_name,
    f.ENTITY_CLASSIFICATION,
    f.MAIN_OFFICE_STATE,
    COALESCE(fs.current_rep_count, 0) as current_rep_count,
    COALESCE(d.departures_12mo, 0) as departures_12mo,
    COALESCE(a.arrivals_12mo, 0) as arrivals_12mo,
    COALESCE(a.arrivals_12mo, 0) - COALESCE(d.departures_12mo, 0) as net_reps_12mo,
    CASE WHEN fs.current_rep_count > 0 
      THEN COALESCE(d.departures_12mo, 0) * 100.0 / fs.current_rep_count
      ELSE 0
    END as turnover_rate_12mo,
    aum.current_aum,
    COALESCE(aum.aum_growth_pct_12mo, 0) as aum_growth_pct_12mo
  FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f
  LEFT JOIN (
    SELECT PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd, COUNT(*) as departures_12mo
    FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY firm_crd
  ) d ON f.CRD_ID = d.firm_crd
  LEFT JOIN (
    SELECT PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd, COUNT(*) as arrivals_12mo
    FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY firm_crd
  ) a ON f.CRD_ID = a.firm_crd
  LEFT JOIN (
    SELECT PRIMARY_FIRM as firm_crd, COUNT(*) as current_rep_count
    FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
    GROUP BY PRIMARY_FIRM
  ) fs ON f.CRD_ID = fs.firm_crd
  LEFT JOIN (
    SELECT 
      h1.RIA_INVESTOR_CRD_ID as firm_crd,
      h1.TOTAL_AUM as current_aum,
      CASE WHEN h2.TOTAL_AUM > 0 
        THEN (h1.TOTAL_AUM - h2.TOTAL_AUM) * 100.0 / h2.TOTAL_AUM 
      END as aum_growth_pct_12mo
    FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h1
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h2
      ON h1.RIA_INVESTOR_CRD_ID = h2.RIA_INVESTOR_CRD_ID
      AND h2.YEAR = 2024 AND h2.MONTH = 11
    WHERE h1.YEAR = 2025 AND h1.MONTH = 11
  ) aum ON f.CRD_ID = aum.firm_crd
  WHERE f.CRD_ID IS NOT NULL
)

SELECT 
  firm_crd,
  firm_name,
  ENTITY_CLASSIFICATION,
  MAIN_OFFICE_STATE,
  current_rep_count,
  departures_12mo,
  arrivals_12mo,
  net_reps_12mo,
  ROUND(turnover_rate_12mo, 1) as turnover_rate_pct,
  ROUND(current_aum / 1000000, 1) as current_aum_millions,
  ROUND(aum_growth_pct_12mo, 1) as aum_growth_pct,
  
  -- Bleeding indicators
  CASE WHEN net_reps_12mo < -5 THEN 'HIGH' 
       WHEN net_reps_12mo < 0 THEN 'MODERATE' 
       ELSE 'LOW' END as rep_bleeding_level,
  CASE WHEN aum_growth_pct_12mo < -10 THEN 'HIGH'
       WHEN aum_growth_pct_12mo < 0 THEN 'MODERATE'
       ELSE 'LOW' END as aum_bleeding_level,
  
  -- Combined bleeding score (for sorting)
  (CASE WHEN net_reps_12mo < 0 THEN ABS(net_reps_12mo) * 2 ELSE 0 END)
  + (CASE WHEN turnover_rate_12mo > 20 THEN turnover_rate_12mo ELSE 0 END)
  + (CASE WHEN aum_growth_pct_12mo < 0 THEN ABS(aum_growth_pct_12mo) ELSE 0 END) as bleeding_score

FROM firm_scores
WHERE current_rep_count >= 10  -- Focus on larger firms
  AND (
    net_reps_12mo < -3  -- Losing reps
    OR turnover_rate_12mo > 25  -- High turnover
    OR aum_growth_pct_12mo < -5  -- Losing AUM
  )
ORDER BY bleeding_score DESC
LIMIT 100;
```

### Expected Output:
- Scoring formulas for all three scores
- List of "bleeding" firms to target
- Validation of score distributions

---

## Step 6: Data Freshness Analysis

### Cursor.ai Prompt:
```
Execute the following SQL to analyze data freshness and determine optimal update frequency for the stability scores.
```

### SQL Query 6.1: Compare Rep vs Firm Level Reporting Timeliness
```sql
-- Analyze how quickly rep moves are reflected in the data
-- Compare rep-level employment changes vs firm-level employee counts

WITH recent_departures AS (
  SELECT 
    PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
    PREVIOUS_REGISTRATION_COMPANY_END_DATE as departure_date,
    DATE_DIFF(CURRENT_DATE(), PREVIOUS_REGISTRATION_COMPANY_END_DATE, DAY) as days_since_departure
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
    AND PREVIOUS_REGISTRATION_COMPANY_END_DATE < CURRENT_DATE()
)
SELECT 
  'Employment History' as data_source,
  COUNT(*) as total_departures_3mo,
  MIN(departure_date) as earliest_departure,
  MAX(departure_date) as latest_departure,
  AVG(days_since_departure) as avg_days_since_departure,
  COUNTIF(days_since_departure <= 7) as departures_last_week,
  COUNTIF(days_since_departure <= 30) as departures_last_month
FROM recent_departures;
```

### SQL Query 6.2: Check Snapshot Freshness
```sql
-- Check how recent the firm historical snapshots are
SELECT 
  YEAR,
  MONTH,
  COUNT(*) as firms_in_snapshot,
  MAX(DATE(YEAR, MONTH, 1)) as snapshot_date,
  DATE_DIFF(CURRENT_DATE(), MAX(DATE(YEAR, MONTH, 1)), DAY) as days_old
FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
GROUP BY YEAR, MONTH
ORDER BY YEAR DESC, MONTH DESC
LIMIT 12;
```

### Expected Output:
- How recent employment change data is
- How fresh firm snapshots are
- Recommended update frequency for scores

---

## Step 7: Generate Final Report

### Cursor.ai Prompt:
```
Based on all the query results above, generate a comprehensive markdown report documenting:
1. Data freshness findings
2. Scoring methodology
3. Top bleeding firms
4. Recommendations for score update frequency
5. Integration with lead scoring models

Save the report to: C:\Users\russe\Big_Query\documentation\Firm_Stability_Score_Report.md
```

### Report Template Structure:

```markdown
# Firm Stability Score Analysis Report

## Executive Summary
[Summary of findings]

## Data Freshness Analysis
### Firm-Level Data
- Latest snapshot: [date]
- Update frequency: Monthly
- AUM coverage: [X]%

### Rep-Level Data
- Most recent employment change: [date]
- Typical lag: [X] days
- Coverage: [X]%

### Recommendation
[Which source to use and how often to update]

## Scoring Methodology

### 1. Rep Stability Score (0-100)
**Components:**
- Turnover rate (departures as % of headcount)
- Net rep change (arrivals - departures)

**Formula:**
```
Rep_Stability_Score = 100 - MIN(100, 
  turnover_rate * 2 
  + IF(net_reps < 0, ABS(net_reps) * 5, 0)
)
```

**Interpretation:**
- 0-30: BLEEDING (high priority target)
- 31-50: AT_RISK
- 51-70: STABLE
- 71-100: WINNING

### 2. AUM Growth Score (0-100)
**Components:**
- 12-month AUM growth percentage

**Formula:**
```
AUM_Growth_Score = 50 + MIN(50, MAX(-50, aum_growth_pct))
```

**Interpretation:**
- 0-40: Significant AUM decline
- 41-60: Flat/minimal change
- 61-100: Strong growth

### 3. Composite Firm Stability Score (0-100)
**Weighted combination:**
```
Composite_Score = 0.6 * Rep_Stability_Score + 0.4 * AUM_Growth_Score
```

## Top Bleeding Firms
[Table of top 50 bleeding firms]

## Integration with Lead Scoring
### How to Use These Scores
1. Join firm stability score to contacts by PRIMARY_FIRM
2. Add as feature in lead scoring model
3. Contacts at low-stability firms = higher priority

### Update Frequency
- **Rep-level scores**: Weekly (employment changes are timely)
- **AUM-based scores**: Monthly (aligned with Firm_historicals updates)

## SQL for Production Use
[Final production-ready queries]

## Appendix
[Detailed data quality notes]
```

---

## Summary: Recommended Approach

### Data Sources
| Metric | Source | Freshness | Recommendation |
|--------|--------|-----------|----------------|
| Rep Movement | `contact_registered_employment_history` | Days | Use as primary - most timely |
| AUM | `Firm_historicals` | Monthly | Use monthly snapshots |
| Employee Count | Calculate from contacts | Current | Derive from rep count |

### Score Types
1. **Rep Stability Score** - Based on turnover and net rep movement (update weekly)
2. **AUM Growth Score** - Based on AUM trends (update monthly)
3. **Composite Stability Score** - Weighted average (update weekly with monthly AUM)

### Key Insight
Rep-level employment history updates faster than firm-level reporting, so use `contact_registered_employment_history` for the most timely view of which firms are losing people.

---

## Next Steps for Cursor.ai

After completing these queries:
1. Save all query results
2. Generate the comprehensive report
3. Create production SQL views for ongoing use
4. Document data update schedule
