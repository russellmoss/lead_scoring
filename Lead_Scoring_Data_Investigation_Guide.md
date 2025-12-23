# Lead Scoring Data Investigation Guide

## Purpose

This document provides step-by-step SQL queries for Cursor.ai to execute via MCP BigQuery connection. The goal is to thoroughly investigate all available data to understand what signals drive conversion from **Contacted → MQL**, and to identify the optimal lead scoring methodology.

## Context

| Metric | Provided Lead List | Self-Sourced (LinkedIn) |
|--------|-------------------|-------------------------|
| **Contacted → MQL** | 2% | 5% |
| **MQL → SQL** | 35% | 36% |
| **SQL → SQO** | 54% | 61% |

**Key Insight**: Self-sourced leads convert at 2.5x the rate of provided leads. We need to understand WHY and engineer provided lists to match self-sourced performance.

**Operational Requirements**:
- 15 SGAs need 150-250 leads/month each = **2,250-3,750 leads/month**
- Small pond problem: Limited pool of advisors in FINTRX
- Severe class imbalance: Only 2-5% convert

---

## Instructions for Cursor.ai

1. Execute each query section in order via MCP BigQuery connection
2. Record ALL results in the findings document (create `Lead_Scoring_Investigation_Findings.md`)
3. Include actual numbers, percentages, and sample sizes
4. Flag any surprising findings or data quality issues
5. Note any queries that fail and the error message

**BigQuery Datasets**:
- `savvy-gtm-analytics.SavvyGTMData` - Salesforce data
- `savvy-gtm-analytics.FinTrx_data_CA` - FINTRX data
- `savvy-gtm-analytics.ml_features` - Feature tables

---

# PHASE 1: Baseline Understanding

## 1.1 Overall Funnel by Lead Source

**Purpose**: Establish baseline conversion rates by Original_Source to confirm the 2% vs 5% gap.

```sql
-- Query 1.1.1: Conversion funnel by Original_Source
SELECT 
  Original_Source__c,
  COUNT(*) as total_leads,
  COUNTIF(stage_entered_contacting__c IS NOT NULL) as contacted,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  COUNTIF(stage_entered_SQL__c IS NOT NULL) as sql_stage,
  COUNTIF(stage_entered_SQO__c IS NOT NULL) as sqo,
  
  -- Conversion rates
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / 
        NULLIF(COUNTIF(stage_entered_contacting__c IS NOT NULL), 0) * 100, 2) as contacted_to_mql_pct,
  ROUND(COUNTIF(stage_entered_SQL__c IS NOT NULL) / 
        NULLIF(COUNTIF(stage_entered_MQL__c IS NOT NULL), 0) * 100, 2) as mql_to_sql_pct,
  ROUND(COUNTIF(stage_entered_SQO__c IS NOT NULL) / 
        NULLIF(COUNTIF(stage_entered_SQL__c IS NOT NULL), 0) * 100, 2) as sql_to_sqo_pct

FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND Company NOT LIKE '%Savvy%'
GROUP BY Original_Source__c
ORDER BY contacted DESC;
```

**Record in findings**: The actual conversion rates by source. Confirm the 2% vs 5% gap.

---

## 1.2 Lead Volume Over Time by Source

**Purpose**: Understand lead volume trends and seasonality.

```sql
-- Query 1.2.1: Monthly lead volume and conversion by source
SELECT 
  FORMAT_DATE('%Y-%m', DATE(stage_entered_contacting__c)) as month,
  Original_Source__c,
  COUNT(*) as contacted,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND Company NOT LIKE '%Savvy%'
  AND Original_Source__c IN ('Provided Lead List', 'LinkedIn (Self Sourced)')
GROUP BY 1, 2
ORDER BY 1, 2;
```

**Record in findings**: Monthly trends, any seasonality patterns, volume changes.

---

## 1.3 Matured Lead Analysis (for reliable conversion rates)

**Purpose**: Only count leads with enough time to convert (30+ days since contact).

```sql
-- Query 1.3.1: Conversion rates for matured leads only
SELECT 
  Original_Source__c,
  COUNT(*) as matured_leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate,
  
  -- Days to conversion stats
  AVG(DATE_DIFF(DATE(stage_entered_MQL__c), DATE(stage_entered_contacting__c), DAY)) as avg_days_to_mql,
  APPROX_QUANTILES(DATE_DIFF(DATE(stage_entered_MQL__c), DATE(stage_entered_contacting__c), DAY), 100)[OFFSET(50)] as median_days_to_mql,
  APPROX_QUANTILES(DATE_DIFF(DATE(stage_entered_MQL__c), DATE(stage_entered_contacting__c), DAY), 100)[OFFSET(90)] as p90_days_to_mql

FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
  AND Company NOT LIKE '%Savvy%'
GROUP BY Original_Source__c
ORDER BY matured_leads DESC;
```

**Record in findings**: Matured conversion rates, time to conversion distribution.

---

# PHASE 2: What Makes Self-Sourced Leads Different?

## 2.1 Profile Comparison: Provided vs Self-Sourced

**Purpose**: Identify systematic differences between lead sources.

```sql
-- Query 2.1.1: Compare lead profiles by source
SELECT 
  Original_Source__c,
  
  -- Volume
  COUNT(*) as leads,
  
  -- Firm size distribution
  AVG(SAFE_CAST(REGEXP_REPLACE(Number_of_Employees__c, r'[^0-9]', '') AS INT64)) as avg_employees,
  
  -- Has CRD match
  ROUND(COUNTIF(FA_CRD__c IS NOT NULL AND FA_CRD__c != '') / COUNT(*) * 100, 1) as has_crd_pct,
  
  -- Has email
  ROUND(COUNTIF(Email IS NOT NULL) / COUNT(*) * 100, 1) as has_email_pct,
  
  -- Has phone
  ROUND(COUNTIF(Phone IS NOT NULL OR MobilePhone IS NOT NULL) / COUNT(*) * 100, 1) as has_phone_pct,
  
  -- Title patterns (look for founders, owners)
  ROUND(COUNTIF(LOWER(Title) LIKE '%founder%' OR LOWER(Title) LIKE '%owner%' OR LOWER(Title) LIKE '%partner%') / COUNT(*) * 100, 1) as founder_owner_pct

FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND Company NOT LIKE '%Savvy%'
  AND Original_Source__c IN ('Provided Lead List', 'LinkedIn (Self Sourced)')
GROUP BY Original_Source__c;
```

**Record in findings**: Key differences in lead profiles between sources.

---

## 2.2 Company/Firm Type Comparison

**Purpose**: See if self-sourced leads target different firm types.

```sql
-- Query 2.2.1: Firm type distribution by source
SELECT 
  Original_Source__c,
  
  -- Check for wirehouse/large firms
  ROUND(COUNTIF(
    UPPER(Company) LIKE '%MORGAN STANLEY%' OR
    UPPER(Company) LIKE '%MERRILL%' OR
    UPPER(Company) LIKE '%WELLS FARGO%' OR
    UPPER(Company) LIKE '%UBS%' OR
    UPPER(Company) LIKE '%EDWARD JONES%' OR
    UPPER(Company) LIKE '%AMERIPRISE%' OR
    UPPER(Company) LIKE '%NORTHWESTERN MUTUAL%' OR
    UPPER(Company) LIKE '%PRUDENTIAL%'
  ) / COUNT(*) * 100, 1) as wirehouse_pct,
  
  -- Small firm indicators
  ROUND(COUNTIF(
    LOWER(Company) LIKE '%wealth%' OR
    LOWER(Company) LIKE '%advisor%' OR
    LOWER(Company) LIKE '%financial planning%'
  ) / COUNT(*) * 100, 1) as small_ria_indicator_pct,
  
  COUNT(*) as total

FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND Company NOT LIKE '%Savvy%'
  AND Original_Source__c IN ('Provided Lead List', 'LinkedIn (Self Sourced)')
GROUP BY Original_Source__c;
```

**Record in findings**: Firm type differences between sources.

---

## 2.3 SGA Sourcing Patterns

**Purpose**: See which SGAs source leads and their respective conversion rates.

```sql
-- Query 2.3.1: SGA performance by lead source
SELECT 
  OwnerId,
  Owner_Name__c,
  Original_Source__c,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND Company NOT LIKE '%Savvy%'
  AND Original_Source__c IN ('Provided Lead List', 'LinkedIn (Self Sourced)')
GROUP BY 1, 2, 3
HAVING leads >= 50
ORDER BY Original_Source__c, conv_rate DESC;
```

**Record in findings**: SGA-level performance differences. Are some SGAs much better at provided leads?

---

# PHASE 3: Univariate Feature Analysis

## 3.1 Tenure Analysis (Critical - V4 Finding to Validate)

**Purpose**: Validate V4's finding that < 1 year tenure converts best.

```sql
-- Query 3.1.1: Conversion by tenure at current firm
WITH lead_tenure AS (
  SELECT 
    l.Id,
    l.FA_CRD__c,
    DATE(l.stage_entered_contacting__c) as contact_date,
    l.stage_entered_MQL__c,
    l.Original_Source__c,
    
    -- Get tenure from FINTRX employment history
    DATE_DIFF(
      DATE(l.stage_entered_contacting__c),
      MAX(h.PREVIOUS_REGISTRATION_COMPANY_START_DATE),
      MONTH
    ) as tenure_months
    
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = h.RIA_CONTACT_CRD_ID
    AND h.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
    AND (h.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
         OR h.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(l.stage_entered_contacting__c))
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
  GROUP BY 1, 2, 3, 4, 5
)
SELECT 
  CASE 
    WHEN tenure_months < 12 THEN '< 1 year'
    WHEN tenure_months < 36 THEN '1-3 years'
    WHEN tenure_months < 48 THEN '3-4 years'
    WHEN tenure_months < 120 THEN '4-10 years'
    WHEN tenure_months < 180 THEN '10-15 years'
    ELSE '15+ years'
  END as tenure_bucket,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) / 0.04 * 100, 2) as lift_vs_4pct_baseline
FROM lead_tenure
WHERE tenure_months IS NOT NULL
GROUP BY 1
ORDER BY 
  CASE tenure_bucket
    WHEN '< 1 year' THEN 1
    WHEN '1-3 years' THEN 2
    WHEN '3-4 years' THEN 3
    WHEN '4-10 years' THEN 4
    WHEN '10-15 years' THEN 5
    ELSE 6
  END;
```

**Record in findings**: Actual tenure vs conversion relationship. Does it match V4's finding?

---

## 3.2 Prior Moves Analysis

**Purpose**: Validate that advisors with more prior moves convert better.

```sql
-- Query 3.2.1: Conversion by number of prior firms
WITH lead_moves AS (
  SELECT 
    l.Id,
    l.FA_CRD__c,
    l.stage_entered_MQL__c,
    
    -- Count prior firms
    COUNT(DISTINCT h.PREVIOUS_REGISTRATION_COMPANY_CRD_ID) - 1 as prior_firms
    
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = h.RIA_CONTACT_CRD_ID
    AND h.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
  GROUP BY 1, 2, 3
)
SELECT 
  CASE 
    WHEN prior_firms = 0 THEN '0 (never moved)'
    WHEN prior_firms = 1 THEN '1 prior firm'
    WHEN prior_firms = 2 THEN '2 prior firms'
    ELSE '3+ prior firms'
  END as moves_bucket,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_moves
WHERE prior_firms IS NOT NULL
GROUP BY 1
ORDER BY 
  CASE moves_bucket
    WHEN '0 (never moved)' THEN 0
    WHEN '1 prior firm' THEN 1
    WHEN '2 prior firms' THEN 2
    ELSE 3
  END;
```

**Record in findings**: Prior moves vs conversion relationship.

---

## 3.3 Firm Size Analysis (Employee Count)

**Purpose**: Identify optimal firm size for targeting.

```sql
-- Query 3.3.1: Conversion by firm employee count
WITH lead_firm AS (
  SELECT 
    l.Id,
    l.FA_CRD__c,
    l.stage_entered_MQL__c,
    f.NUM_OF_EMPLOYEES as employee_count
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON c.PRIMARY_FIRM = f.CRD_ID
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE 
    WHEN employee_count IS NULL THEN 'Unknown'
    WHEN employee_count <= 10 THEN '1-10'
    WHEN employee_count <= 50 THEN '11-50'
    WHEN employee_count <= 100 THEN '51-100'
    WHEN employee_count <= 500 THEN '101-500'
    ELSE '500+'
  END as size_bucket,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_firm
GROUP BY 1
ORDER BY 
  CASE size_bucket
    WHEN '1-10' THEN 1
    WHEN '11-50' THEN 2
    WHEN '51-100' THEN 3
    WHEN '101-500' THEN 4
    WHEN '500+' THEN 5
    ELSE 6
  END;
```

**Record in findings**: Firm size vs conversion. Does V4's 51-100 finding hold?

---

## 3.4 Firm AUM Analysis

**Purpose**: Identify if firm AUM correlates with conversion.

```sql
-- Query 3.4.1: Conversion by firm AUM band
WITH lead_aum AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    f.TOTAL_AUM
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON c.PRIMARY_FIRM = f.CRD_ID
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE 
    WHEN TOTAL_AUM IS NULL THEN 'Unknown'
    WHEN TOTAL_AUM < 100000000 THEN '< $100M'
    WHEN TOTAL_AUM < 500000000 THEN '$100M-$500M'
    WHEN TOTAL_AUM < 1000000000 THEN '$500M-$1B'
    WHEN TOTAL_AUM < 5000000000 THEN '$1B-$5B'
    ELSE '$5B+'
  END as aum_bucket,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_aum
GROUP BY 1
ORDER BY 
  CASE aum_bucket
    WHEN '< $100M' THEN 1
    WHEN '$100M-$500M' THEN 2
    WHEN '$500M-$1B' THEN 3
    WHEN '$1B-$5B' THEN 4
    WHEN '$5B+' THEN 5
    ELSE 6
  END;
```

**Record in findings**: Firm AUM vs conversion relationship.

---

## 3.5 Firm Net Change (Bleeding) Analysis

**Purpose**: Validate that "bleeding" firms have higher conversion.

```sql
-- Query 3.5.1: Conversion by firm net change
WITH lead_bleeding AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    fs.pit_net_change_12mo as net_change
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` fs
    ON l.Id = fs.lead_id
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE 
    WHEN net_change IS NULL THEN 'Unknown'
    WHEN net_change < -10 THEN 'Heavy bleeding (< -10)'
    WHEN net_change < -1 THEN 'Moderate bleeding (-10 to -1)'
    WHEN net_change = 0 THEN 'Stable (0)'
    WHEN net_change <= 5 THEN 'Growing (1-5)'
    ELSE 'Fast growing (5+)'
  END as bleeding_bucket,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_bleeding
GROUP BY 1
ORDER BY 
  CASE bleeding_bucket
    WHEN 'Heavy bleeding (< -10)' THEN 1
    WHEN 'Moderate bleeding (-10 to -1)' THEN 2
    WHEN 'Stable (0)' THEN 3
    WHEN 'Growing (1-5)' THEN 4
    WHEN 'Fast growing (5+)' THEN 5
    ELSE 6
  END;
```

**Record in findings**: Firm bleeding vs conversion. How strong is this signal?

---

## 3.6 Industry Experience Analysis

**Purpose**: Identify optimal experience level for targeting.

```sql
-- Query 3.6.1: Conversion by industry tenure
WITH lead_experience AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    c.INDUSTRY_TENURE_MONTHS as experience_months
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE 
    WHEN experience_months IS NULL THEN 'Unknown'
    WHEN experience_months < 60 THEN '< 5 years'
    WHEN experience_months < 120 THEN '5-10 years'
    WHEN experience_months < 180 THEN '10-15 years'
    WHEN experience_months < 240 THEN '15-20 years'
    WHEN experience_months < 300 THEN '20-25 years'
    ELSE '25+ years'
  END as experience_bucket,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_experience
GROUP BY 1
ORDER BY 
  CASE experience_bucket
    WHEN '< 5 years' THEN 1
    WHEN '5-10 years' THEN 2
    WHEN '10-15 years' THEN 3
    WHEN '15-20 years' THEN 4
    WHEN '20-25 years' THEN 5
    WHEN '25+ years' THEN 6
    ELSE 7
  END;
```

**Record in findings**: Experience vs conversion. Is there a sweet spot?

---

## 3.7 Wirehouse/Excluded Firm Analysis

**Purpose**: Validate that wirehouses convert poorly and should be excluded.

```sql
-- Query 3.7.1: Conversion for excluded vs non-excluded firms
WITH lead_exclusion AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    l.Company,
    CASE 
      WHEN UPPER(l.Company) LIKE '%MORGAN STANLEY%' THEN 'Wirehouse'
      WHEN UPPER(l.Company) LIKE '%MERRILL%' THEN 'Wirehouse'
      WHEN UPPER(l.Company) LIKE '%WELLS FARGO%' THEN 'Wirehouse'
      WHEN UPPER(l.Company) LIKE '%UBS %' OR UPPER(l.Company) LIKE '%UBS,%' OR UPPER(l.Company) = 'UBS' THEN 'Wirehouse'
      WHEN UPPER(l.Company) LIKE '%EDWARD JONES%' THEN 'Wirehouse'
      WHEN UPPER(l.Company) LIKE '%AMERIPRISE%' THEN 'Wirehouse'
      WHEN UPPER(l.Company) LIKE '%NORTHWESTERN MUTUAL%' THEN 'Insurance'
      WHEN UPPER(l.Company) LIKE '%PRUDENTIAL%' THEN 'Insurance'
      WHEN UPPER(l.Company) LIKE '%NEW YORK LIFE%' THEN 'Insurance'
      WHEN UPPER(l.Company) LIKE '%STATE FARM%' THEN 'Insurance'
      WHEN UPPER(l.Company) LIKE '%FIDELITY%' THEN 'Large Custodian'
      WHEN UPPER(l.Company) LIKE '%SCHWAB%' THEN 'Large Custodian'
      WHEN UPPER(l.Company) LIKE '%VANGUARD%' THEN 'Large Custodian'
      ELSE 'Independent/Other'
    END as firm_category
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  firm_category,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_exclusion
GROUP BY 1
ORDER BY conv_rate DESC;
```

**Record in findings**: Conversion by firm category. Which should be excluded?

---

## 3.8 Accolades Analysis

**Purpose**: Do advisors with Forbes/Barron's recognition convert differently?

```sql
-- Query 3.8.1: Conversion by accolade status
WITH lead_accolades AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    CASE WHEN a.RIA_CONTACT_CRD_ID IS NOT NULL THEN 1 ELSE 0 END as has_accolade,
    a.OUTLET
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_accolades_historicals` a
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = a.RIA_CONTACT_CRD_ID
    AND a.YEAR <= EXTRACT(YEAR FROM DATE(l.stage_entered_contacting__c))
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE WHEN has_accolade = 1 THEN 'Has Accolade' ELSE 'No Accolade' END as accolade_status,
  COUNT(DISTINCT Id) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(DISTINCT Id) * 100, 2) as conv_rate
FROM lead_accolades
GROUP BY 1;
```

**Record in findings**: Accolade vs conversion. Is this a positive or negative signal?

---

## 3.9 Disclosure Analysis

**Purpose**: Do advisors with disclosures convert differently? Should they be filtered?

```sql
-- Query 3.9.1: Conversion by disclosure status
WITH lead_disclosures AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    CASE 
      WHEN c.CONTACT_HAS_DISCLOSED_CRIMINAL = TRUE THEN 'Criminal'
      WHEN c.CONTACT_HAS_DISCLOSED_REGULATORY_EVENT = TRUE THEN 'Regulatory'
      WHEN c.CONTACT_HAS_DISCLOSED_CUSTOMER_DISPUTE = TRUE THEN 'Customer Dispute'
      WHEN c.CONTACT_HAS_DISCLOSED_TERMINATION = TRUE THEN 'Termination'
      WHEN c.CONTACT_HAS_DISCLOSED_BANKRUPT = TRUE 
        OR c.CONTACT_HAS_DISCLOSED_JUDGMENT_OR_LIEN = TRUE 
        OR c.CONTACT_HAS_DISCLOSED_CIVIL_EVENT = TRUE THEN 'Financial/Civil'
      ELSE 'No Disclosure'
    END as disclosure_category
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  disclosure_category,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_disclosures
GROUP BY 1
ORDER BY conv_rate DESC;
```

**Record in findings**: Disclosure status vs conversion. Any surprises?

---

## 3.10 License Complexity Analysis

**Purpose**: Do advisors with more/different licenses convert differently?

```sql
-- Query 3.10.1: Conversion by license type
WITH lead_licenses AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    c.REP_LICENSES,
    CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7,
    CASE WHEN c.REP_LICENSES LIKE '%Series 65%' THEN 1 ELSE 0 END as has_series_65,
    CASE WHEN c.REP_LICENSES LIKE '%Series 66%' THEN 1 ELSE 0 END as has_series_66,
    CASE WHEN c.REP_LICENSES LIKE '%Series 24%' THEN 1 ELSE 0 END as has_series_24
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  'Has Series 7' as license_type,
  SUM(has_series_7) as leads,
  SUM(CASE WHEN has_series_7 = 1 AND stage_entered_MQL__c IS NOT NULL THEN 1 ELSE 0 END) as mql,
  ROUND(SUM(CASE WHEN has_series_7 = 1 AND stage_entered_MQL__c IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(SUM(has_series_7), 0) * 100, 2) as conv_rate
FROM lead_licenses
UNION ALL
SELECT 
  'Has Series 65',
  SUM(has_series_65),
  SUM(CASE WHEN has_series_65 = 1 AND stage_entered_MQL__c IS NOT NULL THEN 1 ELSE 0 END),
  ROUND(SUM(CASE WHEN has_series_65 = 1 AND stage_entered_MQL__c IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(SUM(has_series_65), 0) * 100, 2)
FROM lead_licenses
UNION ALL
SELECT 
  'Has Series 66',
  SUM(has_series_66),
  SUM(CASE WHEN has_series_66 = 1 AND stage_entered_MQL__c IS NOT NULL THEN 1 ELSE 0 END),
  ROUND(SUM(CASE WHEN has_series_66 = 1 AND stage_entered_MQL__c IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(SUM(has_series_66), 0) * 100, 2)
FROM lead_licenses
UNION ALL
SELECT 
  'Has Series 24 (Supervisor)',
  SUM(has_series_24),
  SUM(CASE WHEN has_series_24 = 1 AND stage_entered_MQL__c IS NOT NULL THEN 1 ELSE 0 END),
  ROUND(SUM(CASE WHEN has_series_24 = 1 AND stage_entered_MQL__c IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(SUM(has_series_24), 0) * 100, 2)
FROM lead_licenses;
```

**Record in findings**: License types vs conversion.

---

# PHASE 4: Feature Interactions

## 4.1 Tenure × Firm Bleeding Interaction

**Purpose**: Test if the "Prime Mover" hypothesis holds - short tenure + bleeding firm.

```sql
-- Query 4.1.1: Tenure x Bleeding interaction
WITH lead_features AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    fs.current_firm_tenure_months,
    fs.firm_net_change_12mo
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` fs
    ON l.Id = fs.lead_id
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE 
    WHEN current_firm_tenure_months < 48 THEN 'Short Tenure (<4yr)'
    ELSE 'Long Tenure (4yr+)'
  END as tenure_category,
  CASE 
    WHEN firm_net_change_12mo < -1 THEN 'Bleeding Firm'
    ELSE 'Stable/Growing Firm'
  END as bleeding_category,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_features
WHERE current_firm_tenure_months IS NOT NULL
  AND firm_net_change_12mo IS NOT NULL
GROUP BY 1, 2
ORDER BY conv_rate DESC;
```

**Record in findings**: Does the interaction (short tenure + bleeding) outperform either signal alone?

---

## 4.2 Experience × Prior Moves Interaction

**Purpose**: Are experienced movers better than inexperienced movers?

```sql
-- Query 4.2.1: Experience x Prior moves interaction
WITH lead_features AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    c.INDUSTRY_TENURE_MONTHS,
    fs.num_prior_firms
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
  LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` fs
    ON l.Id = fs.lead_id
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE 
    WHEN INDUSTRY_TENURE_MONTHS < 120 THEN 'Less Experienced (<10yr)'
    ELSE 'Experienced (10yr+)'
  END as experience_category,
  CASE 
    WHEN num_prior_firms >= 2 THEN 'Mobile (2+ prior firms)'
    ELSE 'Stable (0-1 prior firms)'
  END as mobility_category,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_features
WHERE INDUSTRY_TENURE_MONTHS IS NOT NULL
  AND num_prior_firms IS NOT NULL
GROUP BY 1, 2
ORDER BY conv_rate DESC;
```

**Record in findings**: Which combination performs best?

---

## 4.3 Firm Size × Firm AUM Interaction

**Purpose**: Are small high-AUM firms different from small low-AUM firms?

```sql
-- Query 4.3.1: Firm size x AUM interaction
WITH lead_features AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    f.NUM_OF_EMPLOYEES,
    f.TOTAL_AUM
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON c.PRIMARY_FIRM = f.CRD_ID
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE 
    WHEN NUM_OF_EMPLOYEES <= 50 THEN 'Small Firm (≤50)'
    WHEN NUM_OF_EMPLOYEES <= 500 THEN 'Medium Firm (51-500)'
    ELSE 'Large Firm (500+)'
  END as size_category,
  CASE 
    WHEN TOTAL_AUM < 500000000 THEN 'Low AUM (<$500M)'
    WHEN TOTAL_AUM < 2000000000 THEN 'Medium AUM ($500M-$2B)'
    ELSE 'High AUM ($2B+)'
  END as aum_category,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_features
WHERE NUM_OF_EMPLOYEES IS NOT NULL
  AND TOTAL_AUM IS NOT NULL
GROUP BY 1, 2
ORDER BY conv_rate DESC;
```

**Record in findings**: Which size/AUM combination is optimal?

---

# PHASE 5: Temporal Patterns

## 5.1 Seasonality Analysis

**Purpose**: Are there months/quarters when advisors are more receptive?

```sql
-- Query 5.1.1: Conversion by month of contact
SELECT 
  EXTRACT(MONTH FROM DATE(stage_entered_contacting__c)) as contact_month,
  FORMAT_DATE('%B', DATE(stage_entered_contacting__c)) as month_name,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
  AND Company NOT LIKE '%Savvy%'
GROUP BY 1, 2
ORDER BY 1;
```

**Record in findings**: Best/worst months for outreach.

---

## 5.2 Day of Week Analysis

**Purpose**: Are certain days better for contact?

```sql
-- Query 5.2.1: Conversion by day of week
SELECT 
  EXTRACT(DAYOFWEEK FROM DATE(stage_entered_contacting__c)) as day_num,
  FORMAT_DATE('%A', DATE(stage_entered_contacting__c)) as day_name,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
  AND Company NOT LIKE '%Savvy%'
GROUP BY 1, 2
ORDER BY 1;
```

**Record in findings**: Best/worst days for outreach.

---

## 5.3 Time Since Last Move

**Purpose**: Is there an optimal time to contact after an advisor changes firms?

```sql
-- Query 5.3.1: Conversion by time since last move
WITH lead_recent_move AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    DATE(l.stage_entered_contacting__c) as contact_date,
    MAX(h.PREVIOUS_REGISTRATION_COMPANY_START_DATE) as last_move_date
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = h.RIA_CONTACT_CRD_ID
    AND h.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
  GROUP BY 1, 2, 3
)
SELECT 
  CASE 
    WHEN DATE_DIFF(contact_date, last_move_date, MONTH) < 6 THEN '< 6 months ago'
    WHEN DATE_DIFF(contact_date, last_move_date, MONTH) < 12 THEN '6-12 months ago'
    WHEN DATE_DIFF(contact_date, last_move_date, MONTH) < 24 THEN '1-2 years ago'
    WHEN DATE_DIFF(contact_date, last_move_date, MONTH) < 48 THEN '2-4 years ago'
    ELSE '4+ years ago'
  END as time_since_move,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_recent_move
WHERE last_move_date IS NOT NULL
GROUP BY 1
ORDER BY 
  CASE time_since_move
    WHEN '< 6 months ago' THEN 1
    WHEN '6-12 months ago' THEN 2
    WHEN '1-2 years ago' THEN 3
    WHEN '2-4 years ago' THEN 4
    ELSE 5
  END;
```

**Record in findings**: Is there a "honeymoon period" after moving where advisors won't move again?

---

# PHASE 6: Prior Contact History

## 6.1 Repeat Contact Analysis

**Purpose**: How many leads have been contacted multiple times?

```sql
-- Query 6.1.1: Conversion by prior contact attempts
-- Note: This requires a field tracking prior contacts - adjust field names as needed
SELECT 
  CASE 
    WHEN COALESCE(CAST(Number_of_Prior_Contacts__c AS INT64), 0) = 0 THEN 'First contact'
    WHEN COALESCE(CAST(Number_of_Prior_Contacts__c AS INT64), 0) = 1 THEN '2nd contact'
    WHEN COALESCE(CAST(Number_of_Prior_Contacts__c AS INT64), 0) = 2 THEN '3rd contact'
    ELSE '4+ contacts'
  END as contact_attempt,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND Company NOT LIKE '%Savvy%'
GROUP BY 1
ORDER BY 1;
```

**Record in findings**: Does repeated contact help or hurt? (If this field doesn't exist, note that.)

---

## 6.2 Pool Exhaustion Analysis

**Purpose**: How much of the FINTRX pool have we already contacted?

```sql
-- Query 6.2.1: Total advisors in FINTRX vs contacted
WITH fintrx_pool AS (
  SELECT 
    COUNT(DISTINCT RIA_CONTACT_CRD_ID) as total_fintrx_advisors,
    COUNTIF(
      UPPER(PRIMARY_FIRM_NAME) NOT LIKE '%MORGAN STANLEY%' AND
      UPPER(PRIMARY_FIRM_NAME) NOT LIKE '%MERRILL%' AND
      UPPER(PRIMARY_FIRM_NAME) NOT LIKE '%WELLS FARGO%' AND
      UPPER(PRIMARY_FIRM_NAME) NOT LIKE '%UBS%' AND
      UPPER(PRIMARY_FIRM_NAME) NOT LIKE '%EDWARD JONES%' AND
      UPPER(PRIMARY_FIRM_NAME) NOT LIKE '%AMERIPRISE%'
    ) as non_wirehouse_advisors
  FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
),
contacted_pool AS (
  SELECT 
    COUNT(DISTINCT FA_CRD__c) as unique_crds_contacted
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
  WHERE stage_entered_contacting__c IS NOT NULL
    AND FA_CRD__c IS NOT NULL
    AND FA_CRD__c != ''
)
SELECT 
  f.total_fintrx_advisors,
  f.non_wirehouse_advisors,
  c.unique_crds_contacted,
  ROUND(c.unique_crds_contacted / f.non_wirehouse_advisors * 100, 1) as pct_of_pool_contacted
FROM fintrx_pool f
CROSS JOIN contacted_pool c;
```

**Record in findings**: What % of the addressable pool has already been contacted?

---

## 6.3 Lead Recycling Opportunity

**Purpose**: How many old leads could be re-contacted?

```sql
-- Query 6.3.1: Leads not contacted in 6+ months that didn't convert
SELECT 
  CASE 
    WHEN DATE_DIFF(CURRENT_DATE(), DATE(stage_entered_contacting__c), MONTH) BETWEEN 6 AND 12 THEN '6-12 months ago'
    WHEN DATE_DIFF(CURRENT_DATE(), DATE(stage_entered_contacting__c), MONTH) BETWEEN 12 AND 18 THEN '12-18 months ago'
    WHEN DATE_DIFF(CURRENT_DATE(), DATE(stage_entered_contacting__c), MONTH) BETWEEN 18 AND 24 THEN '18-24 months ago'
    ELSE '24+ months ago'
  END as last_contact_window,
  COUNT(*) as recyclable_leads,
  COUNTIF(FA_CRD__c IS NOT NULL) as has_crd_match
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_MQL__c IS NULL  -- Never converted
  AND DATE_DIFF(CURRENT_DATE(), DATE(stage_entered_contacting__c), MONTH) >= 6
  AND Company NOT LIKE '%Savvy%'
  AND Original_Source__c = 'Provided Lead List'
GROUP BY 1
ORDER BY 1;
```

**Record in findings**: How many recyclable leads exist? This could supplement new list creation.

---

# PHASE 7: MQL Quality Analysis

## 7.1 MQL to SQL Progression by Segment

**Purpose**: Are high-converting segments also producing quality MQLs?

```sql
-- Query 7.1.1: MQL to SQL rate by tenure bucket
WITH lead_tenure AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    l.stage_entered_SQL__c,
    DATE_DIFF(
      DATE(l.stage_entered_contacting__c),
      MAX(h.PREVIOUS_REGISTRATION_COMPANY_START_DATE),
      MONTH
    ) as tenure_months
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = h.RIA_CONTACT_CRD_ID
    AND h.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_MQL__c IS NOT NULL  -- Only MQLs
    AND l.Company NOT LIKE '%Savvy%'
  GROUP BY 1, 2, 3
)
SELECT 
  CASE 
    WHEN tenure_months < 12 THEN '< 1 year'
    WHEN tenure_months < 36 THEN '1-3 years'
    WHEN tenure_months < 48 THEN '3-4 years'
    ELSE '4+ years'
  END as tenure_bucket,
  COUNT(*) as mqls,
  COUNTIF(stage_entered_SQL__c IS NOT NULL) as sqls,
  ROUND(COUNTIF(stage_entered_SQL__c IS NOT NULL) / COUNT(*) * 100, 2) as mql_to_sql_rate
FROM lead_tenure
WHERE tenure_months IS NOT NULL
GROUP BY 1
ORDER BY 
  CASE tenure_bucket
    WHEN '< 1 year' THEN 1
    WHEN '1-3 years' THEN 2
    WHEN '3-4 years' THEN 3
    ELSE 4
  END;
```

**Record in findings**: Do short-tenure MQLs become SQLs at the same rate?

---

## 7.2 End-to-End Funnel by Segment

**Purpose**: Calculate complete funnel for each key segment.

```sql
-- Query 7.2.1: Complete funnel by firm bleeding status
WITH lead_bleeding AS (
  SELECT 
    l.Id,
    l.stage_entered_contacting__c,
    l.stage_entered_MQL__c,
    l.stage_entered_SQL__c,
    l.stage_entered_SQO__c,
    fs.firm_net_change_12mo
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` fs
    ON l.Id = fs.lead_id
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  CASE 
    WHEN firm_net_change_12mo < -10 THEN 'Heavy Bleeding'
    WHEN firm_net_change_12mo < -1 THEN 'Moderate Bleeding'
    WHEN firm_net_change_12mo IS NULL THEN 'Unknown'
    ELSE 'Stable/Growing'
  END as bleeding_status,
  COUNT(*) as contacted,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  COUNTIF(stage_entered_SQL__c IS NOT NULL) as sql,
  COUNTIF(stage_entered_SQO__c IS NOT NULL) as sqo,
  
  -- Step conversion rates
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as contacted_to_mql,
  ROUND(COUNTIF(stage_entered_SQL__c IS NOT NULL) / NULLIF(COUNTIF(stage_entered_MQL__c IS NOT NULL), 0) * 100, 2) as mql_to_sql,
  ROUND(COUNTIF(stage_entered_SQO__c IS NOT NULL) / NULLIF(COUNTIF(stage_entered_SQL__c IS NOT NULL), 0) * 100, 2) as sql_to_sqo,
  
  -- End-to-end
  ROUND(COUNTIF(stage_entered_SQO__c IS NOT NULL) / COUNT(*) * 100, 2) as contacted_to_sqo

FROM lead_bleeding
GROUP BY 1
ORDER BY contacted_to_sqo DESC;
```

**Record in findings**: Which segments have the best end-to-end conversion?

---

# PHASE 8: Custodian & Technology Analysis

## 8.1 Custodian Impact

**Purpose**: Do advisors at firms using certain custodians convert better?

```sql
-- Query 8.1.1: Conversion by primary custodian
WITH lead_custodian AS (
  SELECT 
    l.Id,
    l.stage_entered_MQL__c,
    f.CUSTODIAN_PRIMARY_BUSINESS_NAME as custodian
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON c.PRIMARY_FIRM = f.CRD_ID
  WHERE l.stage_entered_contacting__c IS NOT NULL
    AND l.stage_entered_contacting__c >= '2023-01-01'
    AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
    AND l.Company NOT LIKE '%Savvy%'
)
SELECT 
  COALESCE(custodian, 'Unknown') as custodian,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM lead_custodian
GROUP BY 1
HAVING leads >= 50
ORDER BY conv_rate DESC;
```

**Record in findings**: Custodian vs conversion. Any tech stack indicators?

---

## 8.2 Custodian Change Signal

**Purpose**: Do firms that recently changed custodians have more receptive advisors?

```sql
-- Query 8.2.1: Identify firms with custodian changes
WITH custodian_changes AS (
  SELECT 
    RIA_INVESTOR_CRD_ID as firm_crd,
    COUNT(DISTINCT PRIMARY_BUSINESS_NAME) as num_custodians,
    MIN(period) as first_period,
    MAX(period) as last_period
  FROM `savvy-gtm-analytics.FinTrx_data_CA.custodians_historicals`
  WHERE period >= '2023-01'
  GROUP BY 1
  HAVING num_custodians > 1  -- Had multiple custodians = changed
)
SELECT 
  CASE WHEN cc.firm_crd IS NOT NULL THEN 'Changed Custodian' ELSE 'Stable Custodian' END as custodian_status,
  COUNT(*) as leads,
  COUNTIF(l.stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(l.stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
  ON SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
LEFT JOIN custodian_changes cc
  ON c.PRIMARY_FIRM = cc.firm_crd
WHERE l.stage_entered_contacting__c IS NOT NULL
  AND l.stage_entered_contacting__c >= '2023-01-01'
  AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
  AND l.Company NOT LIKE '%Savvy%'
GROUP BY 1;
```

**Record in findings**: Is custodian change a signal?

---

# PHASE 9: Geographic Analysis

## 9.1 State-Level Conversion

**Purpose**: Are certain states/regions better for conversion?

```sql
-- Query 9.1.1: Conversion by state
SELECT 
  State,
  COUNT(*) as leads,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as mql,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
  AND Company NOT LIKE '%Savvy%'
  AND State IS NOT NULL
GROUP BY 1
HAVING leads >= 100
ORDER BY conv_rate DESC;
```

**Record in findings**: Geographic patterns. Any states to prioritize or avoid?

---

# PHASE 10: Summary Statistics for Model Design

## 10.1 Class Balance Check

**Purpose**: Confirm class imbalance for model design.

```sql
-- Query 10.1.1: Class balance by source
SELECT 
  Original_Source__c,
  COUNT(*) as total,
  COUNTIF(stage_entered_MQL__c IS NOT NULL) as positive_class,
  COUNTIF(stage_entered_MQL__c IS NULL) as negative_class,
  ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as positive_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
  AND stage_entered_contacting__c >= '2023-01-01'
  AND Company NOT LIKE '%Savvy%'
GROUP BY 1
ORDER BY total DESC;
```

**Record in findings**: Exact class imbalance for scale_pos_weight calculation.

---

## 10.2 Feature Coverage Check

**Purpose**: What % of leads have each key feature?

```sql
-- Query 10.2.1: Feature coverage
SELECT 
  COUNT(*) as total_leads,
  
  -- CRD match
  ROUND(COUNTIF(FA_CRD__c IS NOT NULL AND FA_CRD__c != '') / COUNT(*) * 100, 1) as has_crd_pct,
  
  -- Can calculate tenure (has employment history)
  ROUND(COUNTIF(l.Id IN (
    SELECT DISTINCT l2.Id 
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l2
    JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
      ON SAFE_CAST(REGEXP_REPLACE(l2.FA_CRD__c, r'[^0-9]', '') AS INT64) = h.RIA_CONTACT_CRD_ID
  )) / COUNT(*) * 100, 1) as has_employment_history_pct,
  
  -- Has firm AUM
  ROUND(COUNTIF(l.Id IN (
    SELECT DISTINCT l2.Id 
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l2
    JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
      ON SAFE_CAST(REGEXP_REPLACE(l2.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
    JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
      ON c.PRIMARY_FIRM = f.CRD_ID
    WHERE f.TOTAL_AUM IS NOT NULL
  )) / COUNT(*) * 100, 1) as has_firm_aum_pct

FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
WHERE l.stage_entered_contacting__c IS NOT NULL
  AND l.stage_entered_contacting__c >= '2023-01-01'
  AND l.Company NOT LIKE '%Savvy%';
```

**Record in findings**: Feature coverage for model input planning.

---

# PHASE 11: Create Findings Document

After running all queries, create `Lead_Scoring_Investigation_Findings.md` with:

1. **Executive Summary**: Key findings that will inform model design
2. **Confirmed Signals**: Features with clear, strong conversion patterns
3. **Rejected Signals**: Features with no clear pattern or insufficient coverage
4. **Contradictions Found**: Where data conflicts with assumptions (like V4 tenure finding)
5. **Feature Interaction Insights**: Which combinations outperform individual features
6. **Pool Exhaustion Status**: How much of the addressable market remains
7. **Recommended Model Approach**: Rules-based vs ML, tier definitions
8. **Data Quality Issues**: Any problems discovered during investigation

---

# Appendix: Quick Reference SQL Patterns

## CRD Matching Pattern
```sql
SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
```

## Matured Lead Filter
```sql
AND stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 45 DAY)
```

## Exclude Savvy Leads
```sql
AND Company NOT LIKE '%Savvy%'
```

## Conversion Rate Calculation
```sql
ROUND(COUNTIF(stage_entered_MQL__c IS NOT NULL) / COUNT(*) * 100, 2) as conv_rate
```
