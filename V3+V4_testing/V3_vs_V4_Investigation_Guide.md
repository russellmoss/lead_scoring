# V3 vs V4 Model Investigation: Which Model Predicts Conversions Better?

**Version**: 1.0  
**Created**: 2025-12-24  
**Purpose**: Determine if V3 tier rules or V4 XGBoost scores better predict actual conversions  
**Key Question**: Did T1A leads historically convert better than T2 leads?

---

## ⚠️ CRITICAL: Working Directory Configuration

**ALL WORK MUST BE DONE FROM THIS DIRECTORY:**
```
C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
```

**Directory Structure (Cursor.ai should create if not exists):**
```
V3+V4_testing/
├── sql/                              # SQL queries
│   ├── 01_historical_leads.sql
│   ├── 02_conversion_outcomes.sql
│   ├── 03_tier_performance.sql
│   └── 04_v4_backtest_features.sql
├── scripts/                          # Python analysis scripts
│   ├── score_historical_leads.py
│   ├── analyze_tier_performance.py
│   └── compare_v3_v4.py
├── data/                             # Exported data
│   └── historical_analysis.csv
├── reports/                          # Final reports
│   └── v3_vs_v4_testing.md
└── logs/
    └── INVESTIGATION_LOG.md
```

**V4 Model Files (READ ONLY):**
```
C:\Users\russe\Documents\Lead Scoring\Version-4\models\v4.0.0\model.pkl
C:\Users\russe\Documents\Lead Scoring\Version-4\data\processed\final_features.json
```

---

## Executive Summary

### The Problem We're Investigating

Our January 2026 lead list analysis revealed:

| Finding | Value | Concern |
|---------|-------|---------|
| V3-V4 Correlation | **-0.27** | Models disagree! |
| T1A (best V3) avg V4 score | **0.56** | Lowest of all tiers |
| T2 avg V4 score | **0.67** | Higher than T1A |
| Leads in 90th+ percentile | **90.3%** | V4 not differentiating |

### The Question

> **Did T1A leads (CFPs at bleeding firms, 1-4yr tenure) historically convert better than T2 leads (proven movers with 3+ prior firms)?**

- **If YES**: V3 rules are correct, V4 is wrong → trust V3 tiers
- **If NO**: V4 may be smarter → reconsider tier logic

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    V3 vs V4 INVESTIGATION PIPELINE                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  STEP 1: Extract Historical Lead Data (Q1-Q3 2025)                  │
│     └─> Get all leads with tier assignments and contact dates       │
│                                                                      │
│  STEP 2: Get Conversion Outcomes                                    │
│     └─> Match leads to MQL conversions from Salesforce              │
│                                                                      │
│  STEP 3: Calculate Actual Conversion Rates by V3 Tier               │
│     └─> Compare actual vs expected rates per tier                   │
│                                                                      │
│  STEP 4: Score Historical Leads with V4 Model (PIT-compliant)       │
│     └─> Calculate V4 scores as of contact date                      │
│                                                                      │
│  STEP 5: Compare V3 Tiers vs V4 Scores on Actual Outcomes           │
│     └─> Which better predicted conversions?                         │
│                                                                      │
│  STEP 6: Generate Final Report                                      │
│     └─> v3_vs_v4_testing.md with conclusions                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## STEP 1: Extract Historical Lead Data

### Cursor Prompt 1.1: Create Historical Leads Query

```
@workspace Extract historical lead data with V3 tier assignments for Q1-Q3 2025.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
OUTPUT: V3+V4_testing/sql/01_historical_leads.sql
LOG: V3+V4_testing/logs/INVESTIGATION_LOG.md

Context:
- We need leads that were contacted in Q1-Q3 2025 (Jan 1 - Sep 30, 2025)
- Each lead needs V3 tier assignment based on their characteristics AT TIME OF CONTACT
- Source: Salesforce Lead table + FINTRX data
- We need to reconstruct what tier each lead WOULD have been assigned

Task:
1. Create sql/ directory if not exists
2. Create 01_historical_leads.sql that:
   - Gets all leads contacted in Q1-Q3 2025 from Salesforce
   - Joins to FINTRX to get advisor characteristics
   - Calculates V3 tier assignment using the same rules as January 2026 query
   - Outputs: crd, lead_id, contact_date, first_name, last_name, firm_name,
     tenure_years, industry_tenure_years, num_prior_firms, firm_net_change_12mo,
     has_cfp, is_wirehouse, score_tier, expected_conversion_rate
3. Execute via MCP BigQuery
4. Create table: ml_features.historical_leads_with_tiers
5. Log row count and tier distribution to INVESTIGATION_LOG.md

Key V3 Tier Rules to Apply:
- T1A: tenure 1-4yr, industry_tenure >= 5yr, firm_net_change < 0, has_cfp = 1, not wirehouse
- T1B: Same as T1A but has_series_65_only = 1 instead of CFP
- T1: tenure 1-3yr, industry_tenure 5-15yr, firm_net_change < 0, firm_rep_count <= 50
- T2: num_prior_firms >= 3, industry_tenure >= 5yr
- T3: firm_net_change between -10 and -1, industry_tenure >= 5yr
- T4: industry_tenure >= 20yr, tenure 1-4yr
- T5: firm_net_change <= -10, industry_tenure >= 5yr
```

### SQL Template for Step 1

```sql
-- ============================================================================
-- STEP 1: HISTORICAL LEADS WITH V3 TIER ASSIGNMENTS
-- Purpose: Get all contacted leads from Q1-Q3 2025 with retrospective tier assignment
-- ============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.historical_leads_with_tiers` AS

WITH 
-- ============================================================================
-- A. GET ALL CONTACTED LEADS FROM Q1-Q3 2025
-- ============================================================================
contacted_leads AS (
    SELECT DISTINCT
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
        l.FirstName as first_name,
        l.LastName as last_name,
        l.Company as company,
        DATE(l.CreatedDate) as lead_created_date,
        -- Get first contact date from tasks
        (
            SELECT MIN(DATE(t.ActivityDate))
            FROM `savvy-gtm-analytics.SavvyGTMData.Task` t
            WHERE t.WhoId = l.Id
              AND t.IsDeleted = false
              AND (t.TaskSubtype = 'Call' OR t.Type = 'Call' OR t.Type LIKE '%SMS%')
              AND t.ActivityDate IS NOT NULL
        ) as first_contact_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND l.FA_CRD__c IS NOT NULL
      AND l.CreatedDate >= '2025-01-01'
      AND l.CreatedDate < '2025-10-01'
),

-- Filter to leads actually contacted
contacted_only AS (
    SELECT *
    FROM contacted_leads
    WHERE first_contact_date IS NOT NULL
      AND first_contact_date >= '2025-01-01'
      AND first_contact_date < '2025-10-01'
),

-- ============================================================================
-- B. GET ADVISOR CHARACTERISTICS AT TIME OF CONTACT
-- ============================================================================
-- Note: Using current snapshot as proxy (PIT would require historical snapshots)
advisor_data AS (
    SELECT 
        cl.lead_id,
        cl.crd,
        cl.first_name,
        cl.last_name,
        cl.first_contact_date,
        c.PRIMARY_FIRM_NAME as firm_name,
        SAFE_CAST(c.PRIMARY_FIRM AS INT64) as firm_crd,
        
        -- Tenure at time of contact (approximate using current start date)
        DATE_DIFF(cl.first_contact_date, c.LATEST_REGISTERED_EMPLOYMENT_START_DATE, YEAR) as tenure_years,
        DATE_DIFF(cl.first_contact_date, c.LATEST_REGISTERED_EMPLOYMENT_START_DATE, MONTH) as tenure_months,
        
        -- Industry tenure
        COALESCE(c.INDUSTRY_TENURE_MONTHS, 0) / 12 as industry_tenure_years,
        
        -- Certifications
        CASE WHEN c.CONTACT_BIO LIKE '%CFP%' OR c.TITLE_NAME LIKE '%CFP%' THEN 1 ELSE 0 END as has_cfp,
        CASE WHEN c.REP_LICENSES LIKE '%Series 65%' AND c.REP_LICENSES NOT LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_65_only,
        CASE WHEN c.REP_LICENSES LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7,
        
        -- Firm rep count
        c.PRIMARY_FIRM_EMPLOYEE_COUNT as firm_rep_count
        
    FROM contacted_only cl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
        ON cl.crd = c.RIA_CONTACT_CRD_ID
),

-- ============================================================================
-- C. GET PRIOR FIRMS COUNT (MOBILITY)
-- ============================================================================
mobility AS (
    SELECT 
        ad.crd,
        COUNT(DISTINCT eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as num_prior_firms,
        COUNT(DISTINCT CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(ad.first_contact_date, INTERVAL 3 YEAR)
            THEN eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID 
        END) as moves_3yr
    FROM advisor_data ad
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON ad.crd = eh.RIA_CONTACT_CRD_ID
    GROUP BY ad.crd
),

-- ============================================================================
-- D. GET FIRM NET CHANGE (DEPARTURES - ARRIVALS)
-- ============================================================================
firm_departures AS (
    SELECT
        SAFE_CAST(PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) as firm_crd,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as departures_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
      AND PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
    GROUP BY 1
),

firm_arrivals AS (
    SELECT
        SAFE_CAST(PRIMARY_FIRM AS INT64) as firm_crd,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as arrivals_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
    WHERE PRIMARY_FIRM_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    GROUP BY 1
),

firm_metrics AS (
    SELECT 
        COALESCE(fd.firm_crd, fa.firm_crd) as firm_crd,
        COALESCE(fa.arrivals_12mo, 0) - COALESCE(fd.departures_12mo, 0) as firm_net_change_12mo
    FROM firm_departures fd
    FULL OUTER JOIN firm_arrivals fa ON fd.firm_crd = fa.firm_crd
),

-- ============================================================================
-- E. DETECT WIREHOUSE
-- ============================================================================
wirehouse_check AS (
    SELECT 
        ad.crd,
        CASE
            WHEN UPPER(ad.firm_name) LIKE '%MERRILL%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%MORGAN STANLEY%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%UBS%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%WELLS FARGO%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%EDWARD JONES%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%RAYMOND JAMES%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%AMERIPRISE%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%LPL%' THEN 1
            WHEN UPPER(ad.firm_name) LIKE '%NORTHWESTERN MUTUAL%' THEN 1
            ELSE 0
        END as is_wirehouse
    FROM advisor_data ad
),

-- ============================================================================
-- F. COMBINE AND ASSIGN V3 TIERS
-- ============================================================================
enriched_leads AS (
    SELECT 
        ad.*,
        COALESCE(m.num_prior_firms, 0) as num_prior_firms,
        COALESCE(m.moves_3yr, 0) as moves_3yr,
        COALESCE(fm.firm_net_change_12mo, 0) as firm_net_change_12mo,
        COALESCE(wh.is_wirehouse, 0) as is_wirehouse
    FROM advisor_data ad
    LEFT JOIN mobility m ON ad.crd = m.crd
    LEFT JOIN firm_metrics fm ON ad.firm_crd = fm.firm_crd
    LEFT JOIN wirehouse_check wh ON ad.crd = wh.crd
),

tiered_leads AS (
    SELECT 
        el.*,
        
        -- V3 Tier Assignment (same logic as January 2026 query)
        CASE 
            -- T1A: CFP at bleeding firm, 1-4yr tenure
            WHEN (el.tenure_years BETWEEN 1 AND 4 
                  AND el.industry_tenure_years >= 5 
                  AND el.firm_net_change_12mo < 0 
                  AND el.has_cfp = 1 
                  AND el.is_wirehouse = 0) 
            THEN 'TIER_1A_PRIME_MOVER_CFP'
            
            -- T1B: Series 65 only at bleeding firm
            WHEN (el.tenure_years BETWEEN 1 AND 4 
                  AND el.industry_tenure_years >= 5 
                  AND el.firm_net_change_12mo < 0 
                  AND el.has_series_65_only = 1 
                  AND el.is_wirehouse = 0) 
            THEN 'TIER_1B_PRIME_MOVER_SERIES65'
            
            -- T1: Prime mover (short tenure at small/bleeding firm)
            WHEN ((el.tenure_years BETWEEN 1 AND 3 
                   AND el.industry_tenure_years BETWEEN 5 AND 15 
                   AND el.firm_net_change_12mo < 0 
                   AND el.firm_rep_count <= 50 
                   AND el.is_wirehouse = 0)
                  OR (el.tenure_years BETWEEN 1 AND 3 
                      AND el.firm_rep_count <= 10 
                      AND el.is_wirehouse = 0)
                  OR (el.tenure_years BETWEEN 1 AND 4 
                      AND el.industry_tenure_years BETWEEN 5 AND 15 
                      AND el.firm_net_change_12mo < 0 
                      AND el.is_wirehouse = 0)) 
            THEN 'TIER_1_PRIME_MOVER'
            
            -- T2: Proven mover (3+ prior firms)
            WHEN (el.num_prior_firms >= 3 AND el.industry_tenure_years >= 5) 
            THEN 'TIER_2_PROVEN_MOVER'
            
            -- T3: Moderate bleeder
            WHEN (el.firm_net_change_12mo BETWEEN -10 AND -1 AND el.industry_tenure_years >= 5) 
            THEN 'TIER_3_MODERATE_BLEEDER'
            
            -- T4: Experienced mover
            WHEN (el.industry_tenure_years >= 20 AND el.tenure_years BETWEEN 1 AND 4) 
            THEN 'TIER_4_EXPERIENCED_MOVER'
            
            -- T5: Heavy bleeder
            WHEN (el.firm_net_change_12mo <= -10 AND el.industry_tenure_years >= 5) 
            THEN 'TIER_5_HEAVY_BLEEDER'
            
            ELSE 'STANDARD'
        END as score_tier,
        
        -- Expected conversion rate per V3 model
        CASE 
            WHEN (el.tenure_years BETWEEN 1 AND 4 AND el.industry_tenure_years >= 5 AND el.firm_net_change_12mo < 0 AND el.has_cfp = 1 AND el.is_wirehouse = 0) THEN 0.087
            WHEN (el.tenure_years BETWEEN 1 AND 4 AND el.industry_tenure_years >= 5 AND el.firm_net_change_12mo < 0 AND el.has_series_65_only = 1 AND el.is_wirehouse = 0) THEN 0.079
            WHEN ((el.tenure_years BETWEEN 1 AND 3 AND el.industry_tenure_years BETWEEN 5 AND 15 AND el.firm_net_change_12mo < 0 AND el.firm_rep_count <= 50 AND el.is_wirehouse = 0)
                  OR (el.tenure_years BETWEEN 1 AND 3 AND el.firm_rep_count <= 10 AND el.is_wirehouse = 0)
                  OR (el.tenure_years BETWEEN 1 AND 4 AND el.industry_tenure_years BETWEEN 5 AND 15 AND el.firm_net_change_12mo < 0 AND el.is_wirehouse = 0)) THEN 0.071
            WHEN (el.num_prior_firms >= 3 AND el.industry_tenure_years >= 5) THEN 0.052
            WHEN (el.firm_net_change_12mo BETWEEN -10 AND -1 AND el.industry_tenure_years >= 5) THEN 0.044
            WHEN (el.industry_tenure_years >= 20 AND el.tenure_years BETWEEN 1 AND 4) THEN 0.041
            WHEN (el.firm_net_change_12mo <= -10 AND el.industry_tenure_years >= 5) THEN 0.038
            ELSE 0.025
        END as expected_conversion_rate
        
    FROM enriched_leads el
)

SELECT * FROM tiered_leads;
```

### Cursor Prompt 1.2: Run and Validate

```
@workspace Execute the historical leads query and validate results.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing

Task:
1. Execute sql/01_historical_leads.sql via MCP BigQuery
2. Validate table ml_features.historical_leads_with_tiers:
   - Total row count
   - Tier distribution
   - Date range coverage
3. Log results to logs/INVESTIGATION_LOG.md

Validation queries to run:
- SELECT COUNT(*) as total FROM ml_features.historical_leads_with_tiers
- SELECT score_tier, COUNT(*) as count FROM ml_features.historical_leads_with_tiers GROUP BY 1 ORDER BY 2 DESC
- SELECT MIN(first_contact_date), MAX(first_contact_date) FROM ml_features.historical_leads_with_tiers
```

---

## STEP 2: Get Conversion Outcomes

### Cursor Prompt 2.1: Create Conversion Outcomes Query

```
@workspace Get conversion outcomes (contacted → MQL) for historical leads.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
OUTPUT: V3+V4_testing/sql/02_conversion_outcomes.sql

Context:
- We need to know which leads from Step 1 converted to MQL
- MQL = Lead.Status changed to 'MQL' or similar qualified status
- Need to match lead_id to conversion events

Task:
1. Create sql/02_conversion_outcomes.sql that:
   - Joins historical_leads_with_tiers to Lead status history
   - Identifies leads that reached MQL status
   - Calculates days from first contact to MQL
2. Execute via MCP BigQuery
3. Update table ml_features.historical_leads_with_tiers with conversion column
   OR create new table ml_features.historical_leads_with_outcomes
4. Log conversion rate by tier to INVESTIGATION_LOG.md
```

### SQL Template for Step 2

```sql
-- ============================================================================
-- STEP 2: ADD CONVERSION OUTCOMES TO HISTORICAL LEADS
-- ============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.historical_leads_with_outcomes` AS

WITH 
-- Get historical leads from Step 1
historical_leads AS (
    SELECT * FROM `savvy-gtm-analytics.ml_features.historical_leads_with_tiers`
),

-- Get MQL conversions from Lead table
-- MQL status typically: 'MQL', 'Marketing Qualified', 'Qualified', etc.
mql_conversions AS (
    SELECT 
        l.Id as lead_id,
        1 as converted_to_mql,
        l.Status as final_status,
        DATE(l.LastModifiedDate) as status_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.IsDeleted = false
      AND (
          l.Status IN ('MQL', 'Marketing Qualified', 'Qualified', 'Sales Qualified', 
                       'Working', 'Contacted - Interested', 'Meeting Scheduled',
                       'Opportunity', 'Converted')
          OR l.IsConverted = true
      )
)

SELECT 
    hl.*,
    COALESCE(mc.converted_to_mql, 0) as converted_to_mql,
    mc.final_status,
    mc.status_date as conversion_date,
    DATE_DIFF(mc.status_date, hl.first_contact_date, DAY) as days_to_conversion
FROM historical_leads hl
LEFT JOIN mql_conversions mc ON hl.lead_id = mc.lead_id;
```

### Cursor Prompt 2.2: Validate Conversions

```
@workspace Validate conversion data and calculate initial metrics.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing

Task:
1. Execute sql/02_conversion_outcomes.sql via MCP BigQuery
2. Run validation queries:
   - Overall conversion rate
   - Conversion rate by tier
   - Conversion count by tier
3. Log results to INVESTIGATION_LOG.md

Key validation query:
SELECT 
    score_tier,
    COUNT(*) as total_leads,
    SUM(converted_to_mql) as conversions,
    ROUND(SUM(converted_to_mql) * 100.0 / COUNT(*), 2) as actual_conversion_rate,
    ROUND(AVG(expected_conversion_rate) * 100, 2) as expected_conversion_rate
FROM ml_features.historical_leads_with_outcomes
GROUP BY score_tier
ORDER BY 
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2
        WHEN 'TIER_1_PRIME_MOVER' THEN 3
        WHEN 'TIER_2_PROVEN_MOVER' THEN 4
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 5
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 6
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 7
        ELSE 8
    END;
```

---

## STEP 3: Analyze V3 Tier Performance

### Cursor Prompt 3.1: Calculate Actual vs Expected by Tier

```
@workspace Analyze V3 tier performance: actual vs expected conversion rates.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
OUTPUT: V3+V4_testing/scripts/analyze_tier_performance.py

Task:
1. Create scripts/analyze_tier_performance.py that:
   - Loads data from ml_features.historical_leads_with_outcomes
   - Calculates actual conversion rate per tier
   - Compares to V3's expected conversion rate
   - Calculates lift (actual / baseline)
   - Tests statistical significance (chi-square or Fisher's exact)
   - Creates visualizations
2. Save results to data/tier_performance.csv
3. Log findings to INVESTIGATION_LOG.md

Key analysis:
- Does T1A actually convert at 8.7% as V3 predicts?
- Does T2 convert at 5.2% as V3 predicts?
- Which tier has highest ACTUAL lift?
```

### Python Script Template for Step 3

```python
"""
Analyze V3 Tier Performance: Actual vs Expected Conversion Rates

Working Directory: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
Output: data/tier_performance.csv, reports/tier_analysis.md
"""

import pandas as pd
import numpy as np
from scipy import stats
from google.cloud import bigquery
from pathlib import Path
from datetime import datetime

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\V3+V4_testing")
DATA_DIR = WORKING_DIR / "data"
REPORTS_DIR = WORKING_DIR / "reports"
LOGS_DIR = WORKING_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "savvy-gtm-analytics"

# V3 Expected Conversion Rates
V3_EXPECTED_RATES = {
    'TIER_1A_PRIME_MOVER_CFP': 0.087,
    'TIER_1B_PRIME_MOVER_SERIES65': 0.079,
    'TIER_1_PRIME_MOVER': 0.071,
    'TIER_1F_HV_WEALTH_BLEEDER': 0.065,
    'TIER_2_PROVEN_MOVER': 0.052,
    'TIER_3_MODERATE_BLEEDER': 0.044,
    'TIER_4_EXPERIENCED_MOVER': 0.041,
    'TIER_5_HEAVY_BLEEDER': 0.038,
    'STANDARD': 0.025
}

def load_historical_data():
    """Load historical leads with outcomes from BigQuery."""
    client = bigquery.Client(project=PROJECT_ID)
    query = """
    SELECT *
    FROM `savvy-gtm-analytics.ml_features.historical_leads_with_outcomes`
    """
    df = client.query(query).to_dataframe()
    print(f"[INFO] Loaded {len(df):,} historical leads")
    return df

def calculate_tier_performance(df):
    """Calculate actual conversion rates by tier."""
    
    # Overall baseline
    baseline_rate = df['converted_to_mql'].mean()
    print(f"\n[INFO] Overall conversion rate: {baseline_rate*100:.2f}%")
    
    # By tier
    tier_stats = df.groupby('score_tier').agg({
        'lead_id': 'count',
        'converted_to_mql': ['sum', 'mean']
    }).round(4)
    
    tier_stats.columns = ['total_leads', 'conversions', 'actual_rate']
    tier_stats['expected_rate'] = tier_stats.index.map(V3_EXPECTED_RATES)
    tier_stats['actual_lift'] = tier_stats['actual_rate'] / baseline_rate
    tier_stats['expected_lift'] = tier_stats['expected_rate'] / 0.025  # V3 baseline
    tier_stats['rate_vs_expected'] = tier_stats['actual_rate'] / tier_stats['expected_rate']
    
    # Sort by tier priority
    tier_order = ['TIER_1A_PRIME_MOVER_CFP', 'TIER_1B_PRIME_MOVER_SERIES65', 
                  'TIER_1_PRIME_MOVER', 'TIER_1F_HV_WEALTH_BLEEDER',
                  'TIER_2_PROVEN_MOVER', 'TIER_3_MODERATE_BLEEDER',
                  'TIER_4_EXPERIENCED_MOVER', 'TIER_5_HEAVY_BLEEDER', 'STANDARD']
    tier_stats = tier_stats.reindex([t for t in tier_order if t in tier_stats.index])
    
    return tier_stats, baseline_rate

def statistical_significance(df, tier1, tier2):
    """Test if two tiers have significantly different conversion rates."""
    t1_data = df[df['score_tier'] == tier1]
    t2_data = df[df['score_tier'] == tier2]
    
    # Create contingency table
    table = [
        [t1_data['converted_to_mql'].sum(), len(t1_data) - t1_data['converted_to_mql'].sum()],
        [t2_data['converted_to_mql'].sum(), len(t2_data) - t2_data['converted_to_mql'].sum()]
    ]
    
    # Fisher's exact test (better for small samples)
    odds_ratio, p_value = stats.fisher_exact(table)
    
    return {
        'tier1': tier1,
        'tier2': tier2,
        'tier1_rate': t1_data['converted_to_mql'].mean(),
        'tier2_rate': t2_data['converted_to_mql'].mean(),
        'odds_ratio': odds_ratio,
        'p_value': p_value,
        'significant': p_value < 0.05
    }

def generate_report(tier_stats, baseline_rate, comparisons):
    """Generate markdown report."""
    report = f"""# V3 Tier Performance Analysis

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data Period**: Q1-Q3 2025
**Baseline Conversion Rate**: {baseline_rate*100:.2f}%

---

## Tier Performance Summary

| Tier | Leads | Conversions | Actual Rate | Expected Rate | Actual Lift | Rate vs Expected |
|------|-------|-------------|-------------|---------------|-------------|------------------|
"""
    
    for tier, row in tier_stats.iterrows():
        report += f"| {tier} | {int(row['total_leads']):,} | {int(row['conversions'])} | {row['actual_rate']*100:.2f}% | {row['expected_rate']*100:.2f}% | {row['actual_lift']:.2f}x | {row['rate_vs_expected']:.2f}x |\n"
    
    report += f"""

---

## Key Findings

### T1A vs T2 Comparison (The Critical Question)

"""
    
    # Find T1A vs T2 comparison
    for comp in comparisons:
        if comp['tier1'] == 'TIER_1A_PRIME_MOVER_CFP' and comp['tier2'] == 'TIER_2_PROVEN_MOVER':
            report += f"""
| Metric | T1A (CFP) | T2 (Proven Mover) |
|--------|-----------|-------------------|
| Conversion Rate | {comp['tier1_rate']*100:.2f}% | {comp['tier2_rate']*100:.2f}% |
| Odds Ratio | {comp['odds_ratio']:.2f} | - |
| P-Value | {comp['p_value']:.4f} | - |
| Statistically Significant | {'Yes' if comp['significant'] else 'No'} | - |

**Interpretation**: 
"""
            if comp['tier1_rate'] > comp['tier2_rate']:
                report += f"T1A converts **{comp['tier1_rate']/comp['tier2_rate']:.2f}x better** than T2. V3 tier ordering is correct.\n"
            else:
                report += f"T2 converts **{comp['tier2_rate']/comp['tier1_rate']:.2f}x better** than T1A. V3 tier ordering may be wrong!\n"
    
    report += """

---

## Conclusions

"""
    
    # Determine if V3 ordering is correct
    if 'TIER_1A_PRIME_MOVER_CFP' in tier_stats.index and 'TIER_2_PROVEN_MOVER' in tier_stats.index:
        t1a_rate = tier_stats.loc['TIER_1A_PRIME_MOVER_CFP', 'actual_rate']
        t2_rate = tier_stats.loc['TIER_2_PROVEN_MOVER', 'actual_rate']
        
        if t1a_rate > t2_rate:
            report += "✅ **V3 Tier Ordering is Correct**: T1A (CFP) leads convert better than T2 (Proven Mover) leads.\n"
            report += "   - Recommendation: Trust V3 tiers, V4 disagreement may be noise.\n"
        else:
            report += "⚠️ **V3 Tier Ordering May Be Wrong**: T2 leads convert better than T1A leads.\n"
            report += "   - Recommendation: Investigate V4's signal more closely.\n"
    
    return report

def main():
    print("=" * 70)
    print("V3 TIER PERFORMANCE ANALYSIS")
    print("=" * 70)
    
    # Load data
    df = load_historical_data()
    
    # Calculate tier performance
    tier_stats, baseline_rate = calculate_tier_performance(df)
    
    print("\n" + "=" * 70)
    print("TIER PERFORMANCE SUMMARY")
    print("=" * 70)
    print(tier_stats.to_string())
    
    # Statistical comparisons
    comparisons = []
    if 'TIER_1A_PRIME_MOVER_CFP' in df['score_tier'].values and 'TIER_2_PROVEN_MOVER' in df['score_tier'].values:
        comp = statistical_significance(df, 'TIER_1A_PRIME_MOVER_CFP', 'TIER_2_PROVEN_MOVER')
        comparisons.append(comp)
        print(f"\n[INFO] T1A vs T2: p-value = {comp['p_value']:.4f}")
    
    # Save results
    tier_stats.to_csv(DATA_DIR / "tier_performance.csv")
    print(f"\n[INFO] Saved tier performance to {DATA_DIR / 'tier_performance.csv'}")
    
    # Generate report
    report = generate_report(tier_stats, baseline_rate, comparisons)
    report_path = REPORTS_DIR / "tier_analysis.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"[INFO] Saved report to {report_path}")
    
    # Log to investigation log
    log_path = LOGS_DIR / "INVESTIGATION_LOG.md"
    with open(log_path, 'a') as f:
        f.write(f"\n\n## Step 3: Tier Performance Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Baseline conversion rate: {baseline_rate*100:.2f}%\n")
        f.write(f"- Total leads analyzed: {len(df):,}\n")
        f.write(f"- Total conversions: {df['converted_to_mql'].sum():,}\n")
        for tier, row in tier_stats.iterrows():
            f.write(f"- {tier}: {row['actual_rate']*100:.2f}% actual (vs {row['expected_rate']*100:.2f}% expected)\n")
    
    return tier_stats

if __name__ == "__main__":
    main()
```

---

## STEP 4: Score Historical Leads with V4 Model

### Cursor Prompt 4.1: Create V4 Features for Historical Leads

```
@workspace Calculate V4 features for historical leads (PIT-compliant).

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
OUTPUT: V3+V4_testing/sql/04_v4_backtest_features.sql

Context:
- We need to score historical leads with V4 model
- Features must be calculated AS OF the contact date (PIT-compliant)
- Use same feature engineering as v4_prospect_features.sql

Task:
1. Create sql/04_v4_backtest_features.sql that:
   - Calculates V4 features for each lead AS OF their first_contact_date
   - Uses same feature definitions as production V4
   - Joins to historical_leads_with_outcomes
2. Execute via MCP BigQuery
3. Create table: ml_features.historical_leads_v4_features
4. Log feature coverage to INVESTIGATION_LOG.md

Note: For simplicity, we can use current snapshot features as proxy
(historical PIT would require employment history snapshots)
```

### Cursor Prompt 4.2: Score Historical Leads with V4 Model

```
@workspace Score historical leads using V4 XGBoost model.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
OUTPUT: V3+V4_testing/scripts/score_historical_leads.py

Context:
- V4 model: C:\Users\russe\Documents\Lead Scoring\Version-4\models\v4.0.0\model.pkl
- Features: C:\Users\russe\Documents\Lead Scoring\Version-4\data\processed\final_features.json
- Historical features: ml_features.historical_leads_v4_features

Task:
1. Create scripts/score_historical_leads.py that:
   - Loads V4 model from Version-4 directory
   - Loads historical lead features from BigQuery
   - Scores each lead
   - Calculates percentiles
   - Uploads scores to ml_features.historical_leads_v4_scores
2. Run the script
3. Log results to INVESTIGATION_LOG.md
```

### Python Script Template for Step 4

```python
"""
Score Historical Leads with V4 Model

Working Directory: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
"""

import pandas as pd
import numpy as np
from pathlib import Path
from google.cloud import bigquery
import pickle
import json
from datetime import datetime

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\V3+V4_testing")
V4_MODEL_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4\models\v4.0.0")
V4_FEATURES_FILE = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4\data\processed\final_features.json")

LOGS_DIR = WORKING_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "savvy-gtm-analytics"

def load_model():
    """Load V4 XGBoost model."""
    model_path = V4_MODEL_DIR / "model.pkl"
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    print(f"[INFO] Loaded model from {model_path}")
    return model

def load_features_list():
    """Load V4 feature list."""
    with open(V4_FEATURES_FILE, 'r') as f:
        data = json.load(f)
    features = data['final_features']
    print(f"[INFO] Loaded {len(features)} features")
    return features

def fetch_historical_features(client):
    """Fetch historical lead features from BigQuery."""
    query = """
    SELECT *
    FROM `savvy-gtm-analytics.ml_features.historical_leads_v4_features`
    """
    df = client.query(query).to_dataframe()
    print(f"[INFO] Loaded {len(df):,} historical leads with features")
    return df

def prepare_features(df, feature_list):
    """Prepare features for model scoring."""
    X = df.copy()
    
    # Encode categoricals
    categorical_cols = ['tenure_bucket', 'experience_bucket', 'mobility_tier', 'firm_stability_tier']
    for col in categorical_cols:
        if col in X.columns:
            X[col] = X[col].astype('category').cat.codes.replace(-1, 0)
    
    # Select only required features
    missing = set(feature_list) - set(X.columns)
    if missing:
        print(f"[WARNING] Missing features: {missing}")
        for m in missing:
            X[m] = 0
    
    X = X[feature_list].copy()
    X = X.fillna(0)
    
    return X

def score_leads(model, X):
    """Generate V4 scores."""
    import xgboost as xgb
    dmatrix = xgb.DMatrix(X)
    scores = model.predict(dmatrix)
    return scores

def calculate_percentiles(scores):
    """Calculate percentile ranks."""
    percentiles = pd.Series(scores).rank(pct=True, method='min') * 100
    return percentiles.astype(int).values

def upload_scores(client, df_scores):
    """Upload scores to BigQuery."""
    table_id = f"{PROJECT_ID}.ml_features.historical_leads_v4_scores"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )
    
    job = client.load_table_from_dataframe(df_scores, table_id, job_config=job_config)
    job.result()
    print(f"[INFO] Uploaded {len(df_scores):,} scores to {table_id}")

def main():
    print("=" * 70)
    print("SCORE HISTORICAL LEADS WITH V4 MODEL")
    print("=" * 70)
    
    client = bigquery.Client(project=PROJECT_ID)
    model = load_model()
    feature_list = load_features_list()
    
    # Fetch and prepare features
    df = fetch_historical_features(client)
    X = prepare_features(df, feature_list)
    
    # Score
    scores = score_leads(model, X)
    percentiles = calculate_percentiles(scores)
    
    # Build output
    df_scores = pd.DataFrame({
        'lead_id': df['lead_id'],
        'crd': df['crd'],
        'v4_score': scores,
        'v4_percentile': percentiles,
        'v4_deprioritize': percentiles <= 20,
        'scored_at': datetime.now()
    })
    
    # Upload
    upload_scores(client, df_scores)
    
    # Log
    log_path = LOGS_DIR / "INVESTIGATION_LOG.md"
    with open(log_path, 'a') as f:
        f.write(f"\n\n## Step 4: V4 Scoring - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Total scored: {len(df_scores):,}\n")
        f.write(f"- Score range: {scores.min():.4f} - {scores.max():.4f}\n")
        f.write(f"- Avg score: {scores.mean():.4f}\n")
        f.write(f"- Deprioritize (bottom 20%): {df_scores['v4_deprioritize'].sum():,}\n")
    
    print("\n[INFO] V4 scoring complete!")
    return df_scores

if __name__ == "__main__":
    main()
```

---

## STEP 5: Compare V3 vs V4 on Actual Outcomes

### Cursor Prompt 5.1: Create Comparison Analysis

```
@workspace Compare V3 tier performance vs V4 score performance on actual conversions.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
OUTPUT: V3+V4_testing/scripts/compare_v3_v4.py

Context:
- We now have historical leads with:
  - V3 tier assignment (from Step 1)
  - Actual conversion outcomes (from Step 2)
  - V4 scores (from Step 4)
- We need to determine which better predicts conversions

Task:
1. Create scripts/compare_v3_v4.py that:
   - Joins all data sources
   - Calculates conversion rate by V3 tier
   - Calculates conversion rate by V4 percentile bucket
   - Calculates AUC-ROC for both V3 (tier priority) and V4 (score)
   - Creates comparison visualizations
   - Determines winner
2. Output findings to reports/v3_vs_v4_comparison.md
3. Log summary to INVESTIGATION_LOG.md
```

### Python Script Template for Step 5

```python
"""
Compare V3 Tiers vs V4 Scores on Historical Conversion Data

Working Directory: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
"""

import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc
from scipy import stats
from google.cloud import bigquery
from pathlib import Path
from datetime import datetime

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\V3+V4_testing")
DATA_DIR = WORKING_DIR / "data"
REPORTS_DIR = WORKING_DIR / "reports"
LOGS_DIR = WORKING_DIR / "logs"

for d in [DATA_DIR, REPORTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "savvy-gtm-analytics"

# V3 tier priority (1 = highest)
TIER_PRIORITY = {
    'TIER_1A_PRIME_MOVER_CFP': 1,
    'TIER_1B_PRIME_MOVER_SERIES65': 2,
    'TIER_1_PRIME_MOVER': 3,
    'TIER_1F_HV_WEALTH_BLEEDER': 4,
    'TIER_2_PROVEN_MOVER': 5,
    'TIER_3_MODERATE_BLEEDER': 6,
    'TIER_4_EXPERIENCED_MOVER': 7,
    'TIER_5_HEAVY_BLEEDER': 8,
    'STANDARD': 9
}

def load_combined_data():
    """Load historical leads with outcomes and V4 scores."""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = """
    SELECT 
        o.*,
        s.v4_score,
        s.v4_percentile,
        s.v4_deprioritize
    FROM `savvy-gtm-analytics.ml_features.historical_leads_with_outcomes` o
    LEFT JOIN `savvy-gtm-analytics.ml_features.historical_leads_v4_scores` s
        ON o.lead_id = s.lead_id
    WHERE s.v4_score IS NOT NULL
    """
    
    df = client.query(query).to_dataframe()
    print(f"[INFO] Loaded {len(df):,} leads with outcomes and V4 scores")
    return df

def calculate_auc_scores(df):
    """Calculate AUC-ROC for V3 tier priority and V4 score."""
    
    # V3: Convert tier to numeric (inverted so higher = better)
    df['v3_score'] = df['score_tier'].map(TIER_PRIORITY)
    df['v3_score_inverted'] = 10 - df['v3_score']  # Higher = better priority
    
    # V4: Already a score (higher = better)
    
    # Calculate AUC-ROC
    v3_auc = roc_auc_score(df['converted_to_mql'], df['v3_score_inverted'])
    v4_auc = roc_auc_score(df['converted_to_mql'], df['v4_score'])
    
    print(f"\n[INFO] V3 Tier AUC-ROC: {v3_auc:.4f}")
    print(f"[INFO] V4 Score AUC-ROC: {v4_auc:.4f}")
    
    return v3_auc, v4_auc

def calculate_lift_by_decile(df, score_col, label=''):
    """Calculate conversion rate by score decile."""
    df['decile'] = pd.qcut(df[score_col], q=10, labels=False, duplicates='drop') + 1
    
    baseline = df['converted_to_mql'].mean()
    
    decile_stats = df.groupby('decile').agg({
        'lead_id': 'count',
        'converted_to_mql': ['sum', 'mean']
    })
    decile_stats.columns = ['leads', 'conversions', 'rate']
    decile_stats['lift'] = decile_stats['rate'] / baseline
    
    return decile_stats

def analyze_disagreement(df):
    """Analyze cases where V3 and V4 disagree."""
    
    # High V3 tier but low V4 score
    high_v3_low_v4 = df[
        (df['score_tier'].isin(['TIER_1A_PRIME_MOVER_CFP', 'TIER_1B_PRIME_MOVER_SERIES65', 'TIER_1_PRIME_MOVER'])) &
        (df['v4_percentile'] < 50)
    ]
    
    # Low V3 tier but high V4 score
    low_v3_high_v4 = df[
        (df['score_tier'].isin(['TIER_3_MODERATE_BLEEDER', 'TIER_4_EXPERIENCED_MOVER', 'TIER_5_HEAVY_BLEEDER', 'STANDARD'])) &
        (df['v4_percentile'] >= 80)
    ]
    
    results = {
        'high_v3_low_v4': {
            'count': len(high_v3_low_v4),
            'conversion_rate': high_v3_low_v4['converted_to_mql'].mean() if len(high_v3_low_v4) > 0 else 0
        },
        'low_v3_high_v4': {
            'count': len(low_v3_high_v4),
            'conversion_rate': low_v3_high_v4['converted_to_mql'].mean() if len(low_v3_high_v4) > 0 else 0
        }
    }
    
    return results

def generate_comparison_report(df, v3_auc, v4_auc, disagreement):
    """Generate final comparison report."""
    
    baseline = df['converted_to_mql'].mean()
    
    # T1A vs T2 head-to-head
    t1a = df[df['score_tier'] == 'TIER_1A_PRIME_MOVER_CFP']
    t2 = df[df['score_tier'] == 'TIER_2_PROVEN_MOVER']
    
    report = f"""# V3 vs V4 Model Comparison Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Leads Analyzed**: {len(df):,}
**Total Conversions**: {df['converted_to_mql'].sum():,}
**Baseline Conversion Rate**: {baseline*100:.2f}%

---

## 1. Model Performance Summary

| Metric | V3 (Tier Rules) | V4 (XGBoost) | Winner |
|--------|-----------------|--------------|--------|
| AUC-ROC | {v3_auc:.4f} | {v4_auc:.4f} | {'V3' if v3_auc > v4_auc else 'V4'} |

**Interpretation**: 
- AUC-ROC measures how well the model ranks leads (higher score → higher conversion probability)
- {'V3 rules better predict conversions' if v3_auc > v4_auc else 'V4 XGBoost better predicts conversions'}
- Difference: {abs(v3_auc - v4_auc):.4f} ({'significant' if abs(v3_auc - v4_auc) > 0.02 else 'marginal'})

---

## 2. The Critical Question: T1A vs T2

| Metric | T1A (CFP) | T2 (Proven Mover) |
|--------|-----------|-------------------|
| Lead Count | {len(t1a):,} | {len(t2):,} |
| Conversions | {t1a['converted_to_mql'].sum()} | {t2['converted_to_mql'].sum()} |
| Conversion Rate | {t1a['converted_to_mql'].mean()*100:.2f}% | {t2['converted_to_mql'].mean()*100:.2f}% |
| Lift vs Baseline | {t1a['converted_to_mql'].mean()/baseline:.2f}x | {t2['converted_to_mql'].mean()/baseline:.2f}x |
| Avg V4 Score | {t1a['v4_score'].mean():.4f} | {t2['v4_score'].mean():.4f} |
| Avg V4 Percentile | {t1a['v4_percentile'].mean():.1f} | {t2['v4_percentile'].mean():.1f} |

"""
    
    if len(t1a) > 0 and len(t2) > 0:
        t1a_rate = t1a['converted_to_mql'].mean()
        t2_rate = t2['converted_to_mql'].mean()
        
        if t1a_rate > t2_rate:
            report += f"""
### ✅ CONCLUSION: V3 Tier Ordering is CORRECT

T1A leads convert at **{t1a_rate/t2_rate:.2f}x** the rate of T2 leads.

Despite V4 giving T1A leads lower scores (avg {t1a['v4_score'].mean():.4f} vs T2's {t2['v4_score'].mean():.4f}), 
the actual conversion data shows V3's prioritization of CFPs at bleeding firms is correct.

**Recommendation**: 
- Trust V3 tier ordering
- V4's disagreement is likely noise or overfitting
- Consider removing V4 deprioritization filter OR using V4 only within tiers (not across tiers)
"""
        else:
            report += f"""
### ⚠️ CONCLUSION: V3 Tier Ordering May Be WRONG

T2 leads convert at **{t2_rate/t1a_rate:.2f}x** the rate of T1A leads.

V4's lower scores for T1A leads appear to be correct - these leads don't convert as well as V3 predicts.

**Recommendation**:
- Reconsider V3 tier ordering
- V4 may be capturing real signal that V3 rules miss
- Consider promoting T2 above T1A in prioritization
"""
    
    report += f"""

---

## 3. Disagreement Analysis

### When V3 Says High Priority but V4 Says Low

Leads with V3 Tier 1 but V4 Percentile < 50:
- Count: {disagreement['high_v3_low_v4']['count']:,}
- Conversion Rate: {disagreement['high_v3_low_v4']['conversion_rate']*100:.2f}%
- vs Baseline: {disagreement['high_v3_low_v4']['conversion_rate']/baseline:.2f}x

### When V3 Says Low Priority but V4 Says High

Leads with V3 Tier 3+ but V4 Percentile >= 80:
- Count: {disagreement['low_v3_high_v4']['count']:,}
- Conversion Rate: {disagreement['low_v3_high_v4']['conversion_rate']*100:.2f}%
- vs Baseline: {disagreement['low_v3_high_v4']['conversion_rate']/baseline:.2f}x

"""
    
    # Determine which disagreement group performs better
    if disagreement['high_v3_low_v4']['count'] > 0 and disagreement['low_v3_high_v4']['count'] > 0:
        if disagreement['high_v3_low_v4']['conversion_rate'] > disagreement['low_v3_high_v4']['conversion_rate']:
            report += "**Finding**: V3 is right when they disagree - high V3/low V4 leads convert better.\n"
        else:
            report += "**Finding**: V4 is right when they disagree - low V3/high V4 leads convert better.\n"
    
    report += f"""

---

## 4. Final Recommendations

Based on this analysis:

"""
    
    if v3_auc > v4_auc and len(t1a) > 0 and t1a['converted_to_mql'].mean() > t2['converted_to_mql'].mean():
        report += """
1. **Keep V3 tier ordering** - it correctly predicts which leads convert better
2. **Reconsider V4 deprioritization** - it may be filtering good leads
3. **Use V4 only for tie-breaking** within the same V3 tier
4. **Monitor T1A performance** in January 2026 to validate
"""
    else:
        report += """
1. **Investigate V3 tier logic** - T1A may not be the best tier
2. **Consider V4 for cross-tier ranking** - it may have better signal
3. **A/B test both approaches** in January 2026
4. **Collect more T1A data** - sample size may be too small
"""
    
    return report

def main():
    print("=" * 70)
    print("V3 vs V4 MODEL COMPARISON")
    print("=" * 70)
    
    # Load data
    df = load_combined_data()
    
    # Calculate AUC
    v3_auc, v4_auc = calculate_auc_scores(df)
    
    # Analyze disagreement
    disagreement = analyze_disagreement(df)
    
    # Generate report
    report = generate_comparison_report(df, v3_auc, v4_auc, disagreement)
    
    # Save report
    report_path = REPORTS_DIR / "v3_vs_v4_testing.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\n[INFO] Report saved to {report_path}")
    
    # Save comparison data
    df.to_csv(DATA_DIR / "v3_v4_comparison.csv", index=False)
    
    # Log summary
    log_path = LOGS_DIR / "INVESTIGATION_LOG.md"
    with open(log_path, 'a') as f:
        f.write(f"\n\n## Step 5: V3 vs V4 Comparison - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- V3 AUC-ROC: {v3_auc:.4f}\n")
        f.write(f"- V4 AUC-ROC: {v4_auc:.4f}\n")
        f.write(f"- Winner: {'V3' if v3_auc > v4_auc else 'V4'}\n")
    
    print("\n[INFO] Comparison complete!")
    return df

if __name__ == "__main__":
    main()
```

---

## STEP 6: Generate Final Report

### Cursor Prompt 6.1: Compile Final Report

```
@workspace Compile all findings into the final v3_vs_v4_testing.md report.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
OUTPUT: V3+V4_testing/reports/v3_vs_v4_testing.md

Task:
1. Combine findings from all previous steps:
   - Tier performance analysis (Step 3)
   - V4 scoring results (Step 4)
   - V3 vs V4 comparison (Step 5)
2. Create comprehensive final report that answers:
   - Did T1A leads historically convert better than T2?
   - Which model (V3 or V4) better predicts conversions?
   - Should we trust V3 tiers or V4 scores for prioritization?
   - What should we do for January 2026 lead list?
3. Include visualizations if possible
4. Finalize INVESTIGATION_LOG.md

Report sections:
1. Executive Summary
2. Methodology
3. Key Findings
4. T1A vs T2 Analysis
5. V3 vs V4 AUC Comparison
6. Disagreement Analysis
7. Recommendations
8. Appendix: Raw Data
```

---

## Quick Reference: All Cursor Prompts

### Step 1: Historical Leads
```
@workspace Extract historical lead data with V3 tier assignments for Q1-Q3 2025.
WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
...
```

### Step 2: Conversion Outcomes
```
@workspace Get conversion outcomes (contacted → MQL) for historical leads.
WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
...
```

### Step 3: Tier Performance
```
@workspace Analyze V3 tier performance: actual vs expected conversion rates.
WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
...
```

### Step 4: V4 Scoring
```
@workspace Score historical leads using V4 XGBoost model.
WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
...
```

### Step 5: Comparison
```
@workspace Compare V3 tier performance vs V4 score performance on actual conversions.
WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
...
```

### Step 6: Final Report
```
@workspace Compile all findings into the final v3_vs_v4_testing.md report.
WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing
...
```

---

## Expected Outcomes

| Scenario | T1A vs T2 | V3 AUC vs V4 AUC | Recommendation |
|----------|-----------|------------------|----------------|
| **V3 is Right** | T1A > T2 | V3 > V4 | Trust V3 tiers, reduce V4 influence |
| **V4 is Right** | T2 > T1A | V4 > V3 | Reconsider tier ordering, trust V4 |
| **Both Add Value** | T1A > T2 | V4 > V3 | Keep hybrid, but prioritize V3 tiers |
| **Neither is Great** | T1A ≈ T2 | V3 ≈ V4 | Need more data, test both approaches |

---

**Document Version**: 1.0  
**Created**: 2025-12-24  
**Working Directory**: `C:\Users\russe\Documents\Lead Scoring\V3+V4_testing`
