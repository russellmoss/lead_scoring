# Cursor.ai Data Exploration Prompt: ML Lead Scoring Model Development

**Purpose**: Comprehensive data exploration to inform XGBoost ML model development for lead scoring  
**MCP Connection**: BigQuery (savvy-gtm-analytics, northamerica-northeast2)  
**Dataset**: `FinTrx_data_CA` (Canadian region tables)

---

## 🎯 Exploration Objectives

Before building the ML model, we need to deeply understand:
1. Feature distributions and correlations
2. Target variable characteristics and class imbalance
3. Data quality and missingness patterns
4. Temporal patterns and potential drift
5. Feature-target relationships (univariate lift)
6. Potential leakage risks

---

## Phase 1: Target Variable Deep Dive

### 1.1 Conversion Rate by Time Period
```sql
-- Check for temporal drift in conversion rates
SELECT 
    DATE_TRUNC(DATE(stage_entered_contacting__c), MONTH) as contact_month,
    COUNT(*) as contacted_leads,
    COUNTIF(Stage_Entered_Call_Scheduled__c IS NOT NULL) as mql_conversions,
    ROUND(COUNTIF(Stage_Entered_Call_Scheduled__c IS NOT NULL) / COUNT(*) * 100, 2) as conversion_rate_pct
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
    AND stage_entered_contacting__c >= '2024-01-01'
GROUP BY 1
ORDER BY 1;
```

**Analysis Questions:**
- Is conversion rate stable over time or trending?
- Are there seasonal patterns?
- Any anomalous months to investigate?

### 1.2 Time-to-Conversion Distribution
```sql
-- Understand conversion timing for maturity window decision
WITH conversions AS (
    SELECT 
        DATE_DIFF(DATE(Stage_Entered_Call_Scheduled__c), 
                  DATE(stage_entered_contacting__c), DAY) as days_to_conversion
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE stage_entered_contacting__c IS NOT NULL
        AND Stage_Entered_Call_Scheduled__c IS NOT NULL
        AND Stage_Entered_Call_Scheduled__c >= stage_entered_contacting__c
)
SELECT
    APPROX_QUANTILES(days_to_conversion, 100)[OFFSET(50)] as median_days,
    APPROX_QUANTILES(days_to_conversion, 100)[OFFSET(75)] as p75_days,
    APPROX_QUANTILES(days_to_conversion, 100)[OFFSET(90)] as p90_days,
    APPROX_QUANTILES(days_to_conversion, 100)[OFFSET(95)] as p95_days,
    APPROX_QUANTILES(days_to_conversion, 100)[OFFSET(99)] as p99_days,
    MAX(days_to_conversion) as max_days
FROM conversions;
```

### 1.3 Conversion Rate by Lead Source
```sql
-- Critical: V2 failed due to lead source distribution shift
SELECT 
    COALESCE(LeadSource, 'Unknown') as lead_source,
    COUNT(*) as total_contacted,
    COUNTIF(Stage_Entered_Call_Scheduled__c IS NOT NULL) as mql_conversions,
    ROUND(COUNTIF(Stage_Entered_Call_Scheduled__c IS NOT NULL) / COUNT(*) * 100, 2) as conversion_rate_pct,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 1) as pct_of_total
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
    AND stage_entered_contacting__c >= '2024-01-01'
GROUP BY 1
ORDER BY total_contacted DESC
LIMIT 20;
```

### 1.4 Lead Source Distribution Drift Over Time
```sql
-- Check if lead source mix is changing (V2 failure mode)
SELECT 
    DATE_TRUNC(DATE(stage_entered_contacting__c), QUARTER) as contact_quarter,
    COALESCE(LeadSource, 'Unknown') as lead_source,
    COUNT(*) as count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER(PARTITION BY DATE_TRUNC(DATE(stage_entered_contacting__c), QUARTER)) * 100, 1) as pct_of_quarter
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
    AND stage_entered_contacting__c >= '2024-01-01'
GROUP BY 1, 2
ORDER BY 1, count DESC;
```

---

## Phase 2: Feature Availability & Quality

### 2.1 CRD Match Rate Analysis
```sql
-- How many leads can we enrich with FINTRX data?
WITH lead_crds AS (
    SELECT 
        Id,
        SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd,
        DATE(stage_entered_contacting__c) as contacted_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE stage_entered_contacting__c IS NOT NULL
        AND stage_entered_contacting__c >= '2024-01-01'
),
matched AS (
    SELECT 
        l.*,
        CASE WHEN c.RIA_CONTACT_CRD_ID IS NOT NULL THEN 1 ELSE 0 END as has_fintrx_match
    FROM lead_crds l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON l.advisor_crd = c.RIA_CONTACT_CRD_ID
)
SELECT
    COUNT(*) as total_leads,
    SUM(has_fintrx_match) as matched_leads,
    ROUND(SUM(has_fintrx_match) / COUNT(*) * 100, 2) as match_rate_pct,
    COUNT(*) - SUM(has_fintrx_match) as unmatched_leads
FROM matched;
```

### 2.2 Employment History Coverage
```sql
-- Can we calculate tenure/mobility for matched leads?
WITH lead_crds AS (
    SELECT 
        Id,
        SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd,
        DATE(stage_entered_contacting__c) as contacted_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE stage_entered_contacting__c IS NOT NULL
        AND stage_entered_contacting__c >= '2024-01-01'
        AND FA_CRD__c IS NOT NULL
),
emp_coverage AS (
    SELECT 
        l.*,
        CASE WHEN eh.RIA_CONTACT_CRD_ID IS NOT NULL THEN 1 ELSE 0 END as has_employment_history
    FROM lead_crds l
    LEFT JOIN (
        SELECT DISTINCT RIA_CONTACT_CRD_ID 
        FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    ) eh ON l.advisor_crd = eh.RIA_CONTACT_CRD_ID
)
SELECT
    COUNT(*) as leads_with_crd,
    SUM(has_employment_history) as has_employment_history,
    ROUND(SUM(has_employment_history) / COUNT(*) * 100, 2) as coverage_pct
FROM emp_coverage;
```

### 2.3 Firm Historicals Coverage by Contact Month
```sql
-- Do we have firm data for the month leads were contacted?
WITH lead_firms AS (
    SELECT 
        l.Id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd,
        DATE(l.stage_entered_contacting__c) as contacted_date,
        EXTRACT(YEAR FROM l.stage_entered_contacting__c) as contact_year,
        EXTRACT(MONTH FROM l.stage_entered_contacting__c) as contact_month
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
),
with_current_firm AS (
    SELECT 
        lf.*,
        eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd
    FROM lead_firms lf
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON lf.advisor_crd = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= lf.contacted_date
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= lf.contacted_date)
    QUALIFY ROW_NUMBER() OVER(PARTITION BY lf.Id ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC) = 1
),
with_firm_snapshot AS (
    SELECT 
        wcf.*,
        CASE WHEN fh.RIA_INVESTOR_CRD_ID IS NOT NULL THEN 1 ELSE 0 END as has_firm_snapshot
    FROM with_current_firm wcf
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals` fh
        ON wcf.firm_crd = fh.RIA_INVESTOR_CRD_ID
        AND fh.YEAR = wcf.contact_year
        AND fh.MONTH = wcf.contact_month - 1  -- Use prior month for PIT safety
)
SELECT
    contact_year,
    contact_month,
    COUNT(*) as total_leads,
    SUM(CASE WHEN firm_crd IS NOT NULL THEN 1 ELSE 0 END) as has_firm_crd,
    SUM(has_firm_snapshot) as has_firm_snapshot,
    ROUND(SUM(has_firm_snapshot) / COUNT(*) * 100, 1) as snapshot_coverage_pct
FROM with_firm_snapshot
GROUP BY 1, 2
ORDER BY 1, 2;
```

### 2.4 Key Feature Null Rates
```sql
-- Check null rates for features we plan to use
SELECT
    COUNT(*) as total_contacts,
    ROUND(COUNTIF(INDUSTRY_TENURE_MONTHS IS NULL) / COUNT(*) * 100, 1) as industry_tenure_null_pct,
    ROUND(COUNTIF(PRIMARY_FIRM IS NULL) / COUNT(*) * 100, 1) as primary_firm_null_pct,
    ROUND(COUNTIF(PRIMARY_FIRM_TOTAL_AUM IS NULL) / COUNT(*) * 100, 1) as firm_aum_null_pct,
    ROUND(COUNTIF(EMAIL IS NULL) / COUNT(*) * 100, 1) as email_null_pct,
    ROUND(COUNTIF(LINKEDIN_PROFILE_URL IS NULL) / COUNT(*) * 100, 1) as linkedin_null_pct,
    ROUND(COUNTIF(REP_LICENSES IS NULL OR REP_LICENSES = '[]') / COUNT(*) * 100, 1) as licenses_null_pct,
    ROUND(COUNTIF(TITLE_NAME IS NULL) / COUNT(*) * 100, 1) as title_null_pct,
    ROUND(COUNTIF(CONTACT_BIO IS NULL) / COUNT(*) * 100, 1) as bio_null_pct,
    ROUND(COUNTIF(PRODUCING_ADVISOR IS NULL) / COUNT(*) * 100, 1) as producing_advisor_null_pct
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`;
```

---

## Phase 3: Feature-Target Relationships (Univariate Analysis)

### 3.1 Conversion by Industry Tenure Buckets
```sql
-- Does experience predict conversion?
WITH features AS (
    SELECT 
        l.Id,
        CASE WHEN c.RIA_CONTACT_CRD_ID IS NOT NULL THEN 1 ELSE 0 END as has_fintrx,
        COALESCE(c.INDUSTRY_TENURE_MONTHS, 0) / 12.0 as experience_years,
        CASE 
            WHEN c.INDUSTRY_TENURE_MONTHS IS NULL THEN 'Unknown'
            WHEN c.INDUSTRY_TENURE_MONTHS / 12 < 5 THEN '0-5 years'
            WHEN c.INDUSTRY_TENURE_MONTHS / 12 < 10 THEN '5-10 years'
            WHEN c.INDUSTRY_TENURE_MONTHS / 12 < 15 THEN '10-15 years'
            WHEN c.INDUSTRY_TENURE_MONTHS / 12 < 20 THEN '15-20 years'
            ELSE '20+ years'
        END as experience_bucket,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
)
SELECT 
    experience_bucket,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM features), 2) as lift_vs_baseline
FROM features
GROUP BY 1
ORDER BY 
    CASE experience_bucket
        WHEN 'Unknown' THEN 0
        WHEN '0-5 years' THEN 1
        WHEN '5-10 years' THEN 2
        WHEN '10-15 years' THEN 3
        WHEN '15-20 years' THEN 4
        ELSE 5
    END;
```

### 3.2 Conversion by Mobility (Prior Moves in 3 Years)
```sql
-- Does mobility predict conversion? (Key V3 signal)
WITH mobility AS (
    SELECT 
        l.Id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd,
        DATE(l.stage_entered_contacting__c) as contacted_date,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
),
moves AS (
    SELECT 
        m.Id,
        m.converted,
        COUNT(DISTINCT eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as moves_3yr
    FROM mobility m
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON m.advisor_crd = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE_SUB(m.contacted_date, INTERVAL 3 YEAR)
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= m.contacted_date
    GROUP BY 1, 2
)
SELECT 
    CASE 
        WHEN moves_3yr IS NULL OR moves_3yr = 0 THEN '0 moves (Stable)'
        WHEN moves_3yr = 1 THEN '1 move'
        WHEN moves_3yr = 2 THEN '2 moves'
        ELSE '3+ moves (Highly Mobile)'
    END as mobility_tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM moves), 2) as lift_vs_baseline
FROM moves
GROUP BY 1
ORDER BY 
    CASE 
        WHEN moves_3yr IS NULL OR moves_3yr = 0 THEN 0
        WHEN moves_3yr = 1 THEN 1
        WHEN moves_3yr = 2 THEN 2
        ELSE 3
    END;
```

### 3.3 Conversion by Firm Stability (Net Change 12mo)
```sql
-- Do bleeding firms produce better leads?
-- This requires the PIT firm stability calculation from V3
-- For exploration, we'll use a simplified current-state proxy

WITH firm_stability AS (
    SELECT 
        eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
        COUNTIF(eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)) as departures_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
    WHERE eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    GROUP BY 1
),
lead_features AS (
    SELECT 
        l.Id,
        eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(l.stage_entered_contacting__c))
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
    QUALIFY ROW_NUMBER() OVER(PARTITION BY l.Id ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC) = 1
),
with_stability AS (
    SELECT 
        lf.*,
        COALESCE(fs.departures_12mo, 0) as departures_12mo,
        CASE 
            WHEN fs.departures_12mo IS NULL OR fs.departures_12mo = 0 THEN 'Stable (0 departures)'
            WHEN fs.departures_12mo BETWEEN 1 AND 5 THEN 'Light Bleeding (1-5)'
            WHEN fs.departures_12mo BETWEEN 6 AND 10 THEN 'Moderate Bleeding (6-10)'
            ELSE 'Heavy Bleeding (10+)'
        END as stability_tier
    FROM lead_features lf
    LEFT JOIN firm_stability fs ON lf.firm_crd = fs.firm_crd
)
SELECT 
    stability_tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM with_stability), 2) as lift_vs_baseline
FROM with_stability
GROUP BY 1
ORDER BY 
    CASE stability_tier
        WHEN 'Stable (0 departures)' THEN 1
        WHEN 'Light Bleeding (1-5)' THEN 2
        WHEN 'Moderate Bleeding (6-10)' THEN 3
        ELSE 4
    END;
```

### 3.4 Conversion by Certifications (CFP, Series 65)
```sql
-- Do certifications predict conversion?
-- Note: This is current state (potential PIT issue)
WITH cert_features AS (
    SELECT 
        l.Id,
        c.TITLE_NAME,
        c.CONTACT_BIO,
        c.REP_LICENSES,
        CASE 
            WHEN c.TITLE_NAME LIKE '%CFP%' OR c.CONTACT_BIO LIKE '%CFP%' OR c.CONTACT_BIO LIKE '%Certified Financial Planner%'
            THEN 1 ELSE 0 
        END as has_cfp,
        CASE 
            WHEN c.REP_LICENSES LIKE '%Series 65%' 
                 AND c.REP_LICENSES NOT LIKE '%Series 7%' 
                 AND c.REP_LICENSES NOT LIKE '%Series 6%'
            THEN 1 ELSE 0 
        END as series_65_only,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
)
SELECT 
    'Has CFP' as feature,
    has_cfp as value,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM cert_features), 2) as lift_vs_baseline
FROM cert_features
GROUP BY 1, 2

UNION ALL

SELECT 
    'Series 65 Only (Pure RIA)' as feature,
    series_65_only as value,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM cert_features), 2) as lift_vs_baseline
FROM cert_features
GROUP BY 1, 2
ORDER BY 1, 2;
```

### 3.5 Conversion by Wirehouse Flag
```sql
-- Wirehouse exclusion was key in V3
WITH wirehouse_patterns AS (
    SELECT 
        l.Id,
        eh.PREVIOUS_REGISTRATION_COMPANY_NAME as firm_name,
        CASE 
            WHEN UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%MERRILL%'
                OR UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%MORGAN STANLEY%'
                OR UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%UBS%'
                OR UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%WELLS FARGO%'
                OR UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%EDWARD JONES%'
                OR UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%RAYMOND JAMES%'
                OR UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%AMERIPRISE%'
                OR UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%LPL%'
                OR UPPER(eh.PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%NORTHWESTERN MUTUAL%'
            THEN 1 ELSE 0
        END as is_wirehouse,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(l.stage_entered_contacting__c))
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
    QUALIFY ROW_NUMBER() OVER(PARTITION BY l.Id ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC) = 1
)
SELECT 
    CASE is_wirehouse WHEN 1 THEN 'Wirehouse' ELSE 'Non-Wirehouse' END as firm_type,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM wirehouse_patterns), 2) as lift_vs_baseline
FROM wirehouse_patterns
GROUP BY 1
ORDER BY 1;
```

---

## Phase 4: Potential New Features to Explore

### 4.1 Current Tenure at Firm (PIT-Safe)
```sql
-- Calculate tenure at firm at time of contact
WITH tenure_calc AS (
    SELECT 
        l.Id,
        eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE,
        DATE(l.stage_entered_contacting__c) as contacted_date,
        DATE_DIFF(DATE(l.stage_entered_contacting__c), 
                  eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE, MONTH) as tenure_months,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(l.stage_entered_contacting__c))
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
    QUALIFY ROW_NUMBER() OVER(PARTITION BY l.Id ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC) = 1
)
SELECT 
    CASE 
        WHEN tenure_months IS NULL THEN 'Unknown'
        WHEN tenure_months < 12 THEN '0-1 years'
        WHEN tenure_months < 24 THEN '1-2 years'
        WHEN tenure_months < 48 THEN '2-4 years'
        WHEN tenure_months < 120 THEN '4-10 years'
        ELSE '10+ years'
    END as tenure_bucket,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM tenure_calc), 2) as lift_vs_baseline
FROM tenure_calc
GROUP BY 1
ORDER BY 
    CASE 
        WHEN tenure_months IS NULL THEN 0
        WHEN tenure_months < 12 THEN 1
        WHEN tenure_months < 24 THEN 2
        WHEN tenure_months < 48 THEN 3
        WHEN tenure_months < 120 THEN 4
        ELSE 5
    END;
```

### 4.2 Firm AUM Tiers
```sql
-- Does firm size matter?
WITH firm_aum AS (
    SELECT 
        l.Id,
        fh.TOTAL_AUM,
        CASE 
            WHEN fh.TOTAL_AUM IS NULL THEN 'Unknown'
            WHEN fh.TOTAL_AUM < 100000000 THEN 'Small (<$100M)'
            WHEN fh.TOTAL_AUM < 500000000 THEN 'Medium ($100M-$500M)'
            WHEN fh.TOTAL_AUM < 1000000000 THEN 'Large ($500M-$1B)'
            ELSE 'Enterprise ($1B+)'
        END as aum_tier,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(l.stage_entered_contacting__c))
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals` fh
        ON eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = fh.RIA_INVESTOR_CRD_ID
        AND fh.YEAR = EXTRACT(YEAR FROM l.stage_entered_contacting__c)
        AND fh.MONTH = EXTRACT(MONTH FROM l.stage_entered_contacting__c) - 1
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-02-01'  -- Need Feb+ for PIT firm data
    QUALIFY ROW_NUMBER() OVER(PARTITION BY l.Id ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC) = 1
)
SELECT 
    aum_tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM firm_aum), 2) as lift_vs_baseline
FROM firm_aum
GROUP BY 1
ORDER BY 
    CASE aum_tier
        WHEN 'Unknown' THEN 0
        WHEN 'Small (<$100M)' THEN 1
        WHEN 'Medium ($100M-$500M)' THEN 2
        WHEN 'Large ($500M-$1B)' THEN 3
        ELSE 4
    END;
```

### 4.3 Number of Prior Firms (Career Mover Signal)
```sql
-- Total career moves (not just recent)
WITH prior_firms AS (
    SELECT 
        l.Id,
        COUNT(DISTINCT eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as num_prior_firms,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
    GROUP BY l.Id, l.Stage_Entered_Call_Scheduled__c
)
SELECT 
    CASE 
        WHEN num_prior_firms IS NULL OR num_prior_firms <= 1 THEN '0-1 firms (Lifer)'
        WHEN num_prior_firms = 2 THEN '2 firms'
        WHEN num_prior_firms = 3 THEN '3 firms'
        WHEN num_prior_firms <= 5 THEN '4-5 firms'
        ELSE '6+ firms (Career Mover)'
    END as prior_firms_bucket,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM prior_firms), 2) as lift_vs_baseline
FROM prior_firms
GROUP BY 1
ORDER BY 
    CASE 
        WHEN num_prior_firms IS NULL OR num_prior_firms <= 1 THEN 1
        WHEN num_prior_firms = 2 THEN 2
        WHEN num_prior_firms = 3 THEN 3
        WHEN num_prior_firms <= 5 THEN 4
        ELSE 5
    END;
```

### 4.4 Broker Protocol Membership
```sql
-- Does broker protocol membership affect conversion?
WITH bp_check AS (
    SELECT 
        l.Id,
        CASE WHEN bp.firm_crd_id IS NOT NULL THEN 1 ELSE 0 END as is_broker_protocol,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(l.stage_entered_contacting__c))
    LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members` bp
        ON eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = bp.firm_crd_id
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
    QUALIFY ROW_NUMBER() OVER(PARTITION BY l.Id ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC) = 1
)
SELECT 
    CASE is_broker_protocol WHEN 1 THEN 'Broker Protocol Member' ELSE 'Not BP Member' END as bp_status,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM bp_check), 2) as lift_vs_baseline
FROM bp_check
GROUP BY 1
ORDER BY 1;
```

---

## Phase 5: Feature Correlation & Interaction Analysis

### 5.1 Feature Correlation Matrix (Numeric Features)
```sql
-- Check for multicollinearity among key numeric features
-- This is a simplified version - full analysis should be done in Python
WITH feature_values AS (
    SELECT 
        l.Id,
        COALESCE(c.INDUSTRY_TENURE_MONTHS, 0) / 12.0 as experience_years,
        DATE_DIFF(DATE(l.stage_entered_contacting__c), 
                  eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE, MONTH) / 12.0 as tenure_years,
        COALESCE(fh.TOTAL_AUM, 0) / 1000000000.0 as firm_aum_billions
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(l.stage_entered_contacting__c)
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(l.stage_entered_contacting__c))
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals` fh
        ON eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = fh.RIA_INVESTOR_CRD_ID
        AND fh.YEAR = EXTRACT(YEAR FROM l.stage_entered_contacting__c)
        AND fh.MONTH = EXTRACT(MONTH FROM l.stage_entered_contacting__c) - 1
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-02-01'
    QUALIFY ROW_NUMBER() OVER(PARTITION BY l.Id ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC) = 1
)
SELECT 
    ROUND(CORR(experience_years, tenure_years), 3) as corr_exp_tenure,
    ROUND(CORR(experience_years, firm_aum_billions), 3) as corr_exp_aum,
    ROUND(CORR(tenure_years, firm_aum_billions), 3) as corr_tenure_aum
FROM feature_values;
```

### 5.2 Mobility × Firm Stability Interaction
```sql
-- Key interaction: mobile reps at bleeding firms
WITH interaction AS (
    SELECT 
        l.Id,
        -- Mobility
        CASE 
            WHEN COUNT(DISTINCT CASE 
                WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE_SUB(DATE(l.stage_entered_contacting__c), INTERVAL 3 YEAR)
                THEN eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID END) >= 2 
            THEN 'Mobile'
            ELSE 'Stable'
        END as mobility_status,
        -- Bleeding (simplified - departures > arrivals)
        CASE 
            WHEN COUNT(DISTINCT CASE 
                WHEN eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
                THEN eh.RIA_CONTACT_CRD_ID END) > 5
            THEN 'Bleeding'
            ELSE 'Stable'
        END as firm_status,
        MAX(CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END) as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.RIA_CONTACT_CRD_ID
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
    GROUP BY l.Id, l.Stage_Entered_Call_Scheduled__c
)
SELECT 
    mobility_status,
    firm_status,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM interaction), 2) as lift_vs_baseline
FROM interaction
GROUP BY 1, 2
ORDER BY 1, 2;
```

---

## Phase 6: Sample Size & Statistical Power

### 6.1 Sample Sizes by Key Segments
```sql
-- Check if we have enough samples in important segments
WITH segments AS (
    SELECT 
        l.Id,
        -- Experience bucket
        CASE 
            WHEN c.INDUSTRY_TENURE_MONTHS / 12 BETWEEN 5 AND 15 THEN 'Sweet Spot (5-15yr)'
            ELSE 'Other'
        END as exp_segment,
        -- Mobility
        CASE WHEN moves.move_count >= 2 THEN 'Mobile' ELSE 'Stable' END as mobility_segment,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
    LEFT JOIN (
        SELECT 
            RIA_CONTACT_CRD_ID,
            COUNT(DISTINCT PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as move_count
        FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
        WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)
        GROUP BY 1
    ) moves ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = moves.RIA_CONTACT_CRD_ID
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
)
SELECT 
    exp_segment,
    mobility_segment,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    -- Minimum sample size check for 95% confidence
    CASE 
        WHEN COUNT(*) >= 385 THEN '✅ Sufficient (n>=385)'
        WHEN COUNT(*) >= 100 THEN '⚠️ Marginal (100<=n<385)'
        ELSE '❌ Insufficient (n<100)'
    END as sample_size_status
FROM segments
GROUP BY 1, 2
ORDER BY 1, 2;
```

---

## Phase 7: Output Summary Tables

### 7.1 Final Feature Inventory
After running all explorations, create a summary:

```sql
-- Template for final feature inventory
SELECT 
    'experience_years' as feature_name,
    'Numeric' as feature_type,
    'INDUSTRY_TENURE_MONTHS / 12' as calculation,
    '6.1%' as null_rate,
    'FINTRX current' as source,
    'No' as pit_safe,
    '1.5x (10-15yr bucket)' as max_lift
UNION ALL
SELECT 'tenure_years', 'Numeric', 'DATE_DIFF from employment start', '~15%', 'Employment History', 'Yes', '2.0x (1-4yr bucket)'
UNION ALL
SELECT 'pit_moves_3yr', 'Integer', 'Count firms in 3yr lookback', '~5%', 'Employment History', 'Yes', '3.78x (3+ moves)'
-- ... add all features
;
```

---

## 🎯 Execution Instructions for Cursor.ai

1. **Run each query in Phase 1-6 sequentially**
2. **Document results in a markdown file** with:
   - Query results as tables
   - Key insights
   - Concerns or anomalies
3. **Flag any data quality issues** (high null rates, unexpected distributions)
4. **Identify top features by univariate lift**
5. **Note sample size concerns** for small segments
6. **Save outputs to**: `Version-3/data/exploration/ml_data_exploration_results.md`

---

## Expected Outputs

After running this exploration, we should have:

1. **Feature Inventory**: List of all usable features with lift values
2. **PIT Compliance Report**: Which features are truly PIT-safe
3. **Sample Size Analysis**: Where we have statistical power
4. **Drift Analysis**: How lead source mix has changed
5. **Correlation Matrix**: Which features are redundant
6. **Interaction Effects**: Key feature combinations

This will inform the XGBoost model architecture and feature engineering decisions.
