# Lead Scoring V3 - Plan Update & Implementation Guide

## Instructions for Cursor.ai

**Purpose:** Update the `leadscoring_plan.md` to incorporate all findings from the December 2024 validation analysis. This document contains the complete revision with data-driven corrections to tier definitions, validated against XGBoost ML.

**Target File:** `C:\Users\russe\Documents\Lead Scoring\Version-3\leadscoring_plan.md`

**Action:** Replace or merge the relevant sections of the existing plan with the content below. The key changes are:
1. Corrected tier thresholds based on empirical validation
2. Removal of the "small firm" rule (it was inverted)
3. New tier priority order based on actual lift
4. Addition of `firm_rep_count_at_contact` feature
5. Comprehensive validation framework and execution log

---

# ============================================================================
# BEGIN UPDATED LEADSCORING_PLAN.MD CONTENT
# ============================================================================

# Lead Scoring Model V3 - Tiered Rules Approach

**Version:** 3.1 (Empirically Validated)  
**Last Updated:** December 21, 2024  
**Status:** ✅ VALIDATED - Rules outperform XGBoost ML  
**Base Directory:** `C:\Users\russe\Documents\Lead Scoring\Version-3`

---

## Executive Summary

### The Journey: V2 XGBoost → V3 Rules → V3.1 Corrected Rules

| Version | Approach | Top Decile Lift | Status |
|---------|----------|-----------------|--------|
| V2 XGBoost (2024) | ML Model | 4.43x | ❌ Degraded in 2025 |
| V2 XGBoost (2025) | ML Model | 0.79x-1.46x | ❌ Failed |
| V3 Original Rules | SGA Intuition | 1.47x | ⚠️ Below target |
| **V3.1 Corrected Rules** | **Data-Validated** | **1.74x** | ✅ **Beats XGBoost** |

### Key Achievement

**V3.1 Rules-based scoring outperforms XGBoost ML:**

| Method | Top Decile Lift | Verdict |
|--------|-----------------|---------|
| **V3.1 Rules** | **1.74x** | 🏆 Winner |
| Raw XGBoost | 1.63x | |
| Hybrid (Rules + ML) | 1.72x | |

### Priority Leads Summary

| Tier | Name | Leads | Conversion Rate | Lift |
|------|------|-------|-----------------|------|
| **T1** | Prime Movers | 194 | 12.89% | **3.40x** |
| **T2** | Moderate Bleeders | 124 | 10.48% | **2.77x** |
| **T3** | Experienced Movers | 199 | 10.05% | **2.65x** |
| **T4** | Heavy Bleeders | 1,388 | 8.65% | **2.28x** |
| - | Standard | 37,151 | 3.49% | 0.92x |

**Total Priority Leads:** 1,905  
**Combined Lift:** ~2.5x  
**Expected Conversion:** ~9% (vs 3.5% baseline)

---

## Table of Contents

1. [Decision Log: Why We Made These Changes](#1-decision-log)
2. [Final Tier Definitions](#2-final-tier-definitions)
3. [Directory Structure](#3-directory-structure)
4. [Implementation Phases](#4-implementation-phases)
5. [Phase 0: Data Foundation](#5-phase-0-data-foundation)
6. [Phase 1: Feature Engineering](#6-phase-1-feature-engineering)
7. [Phase 2: Tier Scoring Implementation](#7-phase-2-tier-scoring)
8. [Phase 3: Validation & Backtesting](#8-phase-3-validation)
9. [Phase 4: Production Deployment](#9-phase-4-deployment)
10. [Execution Log](#10-execution-log)

---

## 1. Decision Log: Why We Made These Changes {#1-decision-log}

### 1.1 Critical Discovery: Original Tier Thresholds Were Wrong

**Date:** December 21, 2024  
**Analysis:** Diagnostic queries against 36,153 leads with 1,335 conversions

#### Tenure Analysis - Original Rules Were INVERTED

| Tenure Bucket | Conversion Rate | Lift | Original Rule Said |
|---------------|-----------------|------|-------------------|
| **1-2yr** | **15.07%** | **4.08x** | ❌ "Danger Zone" (deprioritized) |
| 2-4yr | 10.08% | 2.73x | ❌ Not captured |
| 4-7yr | 7.02% | 1.90x | ✅ "Platinum" (prioritized) |
| 7-10yr | 5.54% | 1.50x | ✅ "Platinum" (prioritized) |
| 0-1yr | 3.45% | 0.94x | ❌ Excluded |

**Decision:** Change Platinum tenure from 4-10yr → **1-4yr**  
**Rationale:** The 1-4yr cohort converts at 3-4x baseline; the 4-10yr cohort only at 1.5-1.9x

#### Small Firm Rule - Completely Inverted

| Firm Size | Leads | Conversion Rate | Lift |
|-----------|-------|-----------------|------|
| Large (51-200) | 368 | 9.51% | **2.58x** |
| Medium (11-50) | 480 | 8.96% | **2.43x** |
| Very Large (>200) | 1,794 | 6.13% | 1.66x |
| **Small (≤10)** | 36,806 | 3.55% | **0.96x** |

**Decision:** DROP the small firm rule entirely  
**Rationale:** 
- 91.5% of leads have `firm_rep_count = 0` (unknown, not small)
- Actual small firms convert BELOW baseline
- Medium/Large firms convert 2.4-2.6x

#### Bleeding Firm Thresholds - Miscalibrated

| Net Change | Conversion Rate | Lift | Original Rule |
|------------|-----------------|------|---------------|
| Slight loss (-5 to 0) | 9.78% | **2.65x** | ❌ Not captured |
| Heavy bleeding (<-10) | 9.12% | **2.47x** | ❌ Wrong threshold |
| Bleeding (-10 to -5) | 6.06% | 1.64x | ✅ Original captured this |
| Stable (0) | 3.45% | 0.93x | Baseline |

**Decision:** Split into Heavy (<-10) and Moderate (-10 to 0)  
**Rationale:** Heavy bleeding AND slight loss both convert well

### 1.2 Tier 4 (Medium/Large Firms) - Dropped Post-Validation

**Initial Hypothesis:** Medium/Large firms convert at 2.4-2.6x  
**Actual Result:** Only 1.41x lift when tested as a tier

**Decision:** Remove Tier 4 from final model  
**Rationale:** The firm size signal doesn't translate to a useful standalone tier; it's likely confounded with other factors

### 1.3 Wirehouse Detection - Confirmed as Critical

**XGBoost Feature Importance:**
```
is_wirehouse         0.582 (58% of total importance)
firm_rep_count       0.089 (9%)
expected_lift        0.067 (7%)
...
```

**Decision:** Keep wirehouse exclusion in Tier 1  
**Rationale:** ML confirms avoiding wirehouses is the single most important factor

### 1.4 Final Validation: Rules vs ML

**Test:** 70/30 temporal split, 25,307 train / 10,846 test

| Method | Top Decile Lift |
|--------|-----------------|
| V3.1 Rules | **1.74x** ✅ |
| Raw XGBoost | 1.63x |
| Hybrid | 1.72x |

**Decision:** Use rules-based approach  
**Rationale:** Rules are simpler, more interpretable, AND perform better

---

## 2. Final Tier Definitions {#2-final-tier-definitions}

### Tier 1: PRIME MOVERS (Expected 3.4x lift)

```sql
tenure_years BETWEEN 1 AND 4
AND experience_years BETWEEN 5 AND 15
AND firm_net_change_12mo != 0
AND is_wirehouse = FALSE
```

**Why this works:**
- 1-4yr tenure = Still evaluating, open to opportunities
- 5-15yr experience = Mid-career, peak mobility
- Any firm instability = Signal of opportunity
- Not wirehouse = Much more likely to move

### Tier 2: MODERATE BLEEDERS (Expected 2.8x lift)

```sql
firm_net_change_12mo BETWEEN -10 AND -1
AND experience_years >= 5
```

**Why this works:**
- Moderate churn signals underlying issues
- Experienced advisors recognize the signs
- Outperformed expectations (2.77x actual vs 1.80x expected)

### Tier 3: EXPERIENCED MOVERS (Expected 2.7x lift)

```sql
tenure_years BETWEEN 1 AND 4
AND experience_years >= 20
```

**Why this works:**
- Veterans who recently moved are still "shopping"
- Long careers = extensive networks, referral potential
- Short tenure at current firm = not yet committed

### Tier 4: HEAVY BLEEDERS (Expected 2.3x lift)

```sql
firm_net_change_12mo < -10
AND experience_years >= 5
```

**Why this works:**
- Volume tier (1,388 leads)
- Firms losing 10+ advisors have serious problems
- Advisors there are actively looking

### Standard: Everything Else

All leads not matching Tiers 1-4.

---

## 3. Directory Structure {#3-directory-structure}

```
C:\Users\russe\Documents\Lead Scoring\Version-3\
├── data\
│   ├── raw\                    # Raw exports from BigQuery
│   ├── processed\              # Cleaned feature tables
│   └── validation\             # Holdout sets for backtesting
│
├── inference\
│   ├── tier_scorer.py          # Production scoring logic
│   └── batch_score.py          # Batch scoring pipeline
│
├── models\
│   ├── tier_definitions.json   # Tier rules as config
│   └── model_card.md           # Model documentation
│
├── notebooks\
│   ├── 01_data_exploration.ipynb
│   ├── 02_tier_validation.ipynb
│   └── 03_backtest_analysis.ipynb
│
├── reports\
│   ├── tier_validation_results.csv
│   ├── backtest_results.csv
│   └── production_monitoring\
│
├── sql\
│   ├── phase_0_data_foundation.sql
│   ├── phase_1_feature_engineering.sql
│   ├── phase_2_tier_scoring.sql
│   └── phase_3_validation.sql
│
├── utils\
│   ├── bigquery_client.py
│   ├── logging_utils.py
│   └── validation_utils.py
│
├── leadscoring_plan.md         # This document
├── EXECUTION_LOG.md            # Running log of all executions
└── README.md                   # Quick start guide
```

---

## 4. Implementation Phases {#4-implementation-phases}

| Phase | Name | Duration | Dependencies |
|-------|------|----------|--------------|
| 0 | Data Foundation | 1 day | BigQuery access |
| 1 | Feature Engineering | 1 day | Phase 0 |
| 2 | Tier Scoring | 0.5 day | Phase 1 |
| 3 | Validation & Backtest | 1 day | Phase 2 |
| 4 | Production Deployment | 1 day | Phase 3 pass |

**Total:** ~4.5 days

---

## 5. Phase 0: Data Foundation {#5-phase-0-data-foundation}

### 5.1 Objective

Establish date configuration, verify data availability, and create base tables.

### 5.2 Date Configuration

```python
# date_config.json
{
    "execution_date": "2024-12-21",
    "training_start": "2024-02-01",
    "training_end": "2025-07-03",
    "test_start": "2025-08-02",
    "test_end": "2025-10-01",
    "maturity_window_days": 30,
    "analysis_date": "2025-10-31"
}
```

### 5.3 Pre-Flight Checks

| Check | Query | Pass Criteria |
|-------|-------|---------------|
| Firm data months | Count distinct months in Firm_historicals | ≥ 20 |
| Lead volume | Count leads 2024+ | ≥ 10,000 |
| CRD match rate | % leads with valid advisor CRD | ≥ 90% |
| Recent data | Days since most recent lead | ≤ 30 |

### 5.4 SQL: Phase 0

**File:** `sql/phase_0_data_foundation.sql`

```sql
-- Phase 0: Data Foundation Queries
-- Run these to verify data availability before proceeding

-- 0.1 Firm Historicals Coverage
SELECT 
    MIN(DATE(YEAR, MONTH, 1)) as earliest_month,
    MAX(DATE(YEAR, MONTH, 1)) as latest_month,
    COUNT(DISTINCT DATE(YEAR, MONTH, 1)) as total_months
FROM `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals`;

-- 0.2 Lead Volume by Year
SELECT 
    EXTRACT(YEAR FROM stage_entered_contacting__c) as year,
    COUNT(*) as leads,
    COUNTIF(stage_entered_mql__c IS NOT NULL) as mqls,
    ROUND(COUNTIF(stage_entered_mql__c IS NOT NULL) / COUNT(*) * 100, 2) as mql_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c >= '2024-01-01'
GROUP BY 1
ORDER BY 1;

-- 0.3 CRD Match Rate
SELECT
    COUNT(*) as total_leads,
    COUNTIF(FA_CRD__c IS NOT NULL) as has_crd,
    ROUND(COUNTIF(FA_CRD__c IS NOT NULL) / COUNT(*) * 100, 2) as match_rate
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c >= '2024-01-01';

-- 0.4 Most Recent Lead
SELECT 
    MAX(stage_entered_contacting__c) as most_recent_lead,
    DATE_DIFF(CURRENT_DATE(), DATE(MAX(stage_entered_contacting__c)), DAY) as days_ago
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`;
```

### 5.5 Validation Gates

| Gate ID | Check | Pass Criteria | Action if Fail |
|---------|-------|---------------|----------------|
| G0.1 | Firm data months | ≥ 20 | Cannot proceed |
| G0.2 | Lead volume | ≥ 10,000 | Check date range |
| G0.3 | CRD match rate | ≥ 90% | Investigate source |
| G0.4 | Recent data | ≤ 30 days | Check ETL pipeline |

---

## 6. Phase 1: Feature Engineering {#6-phase-1-feature-engineering}

### 6.1 Objective

Create Point-in-Time (PIT) feature table including the new `firm_rep_count_at_contact` column.

### 6.2 Features Required

| Feature | Source | PIT Safe | Notes |
|---------|--------|----------|-------|
| current_firm_tenure_months | Employment history | ✅ | Uses start_date only |
| industry_tenure_months | Employment history | ✅ | First start_date |
| firm_net_change_12mo | Employment history | ✅ | Aggregate of others' moves |
| firm_rep_count_at_contact | Employment history | ✅ | **NEW** - Count active reps |
| pit_moves_3yr | Employment history | ✅ | Historical moves |
| is_wirehouse | Lead.Company | ✅ | Pattern match |

### 6.3 SQL: Add firm_rep_count_at_contact

**File:** `sql/phase_1_add_firm_rep_count.sql`

```sql
-- Phase 1.1: Create firm rep counts lookup table
-- Point-in-Time count of active reps at each firm on each date

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.firm_rep_counts_pit` AS

WITH lead_dates AS (
    SELECT DISTINCT
        firm_crd_at_contact as firm_crd,
        contacted_date
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
    WHERE firm_crd_at_contact IS NOT NULL
),

rep_counts AS (
    SELECT
        ld.firm_crd,
        ld.contacted_date,
        COUNT(DISTINCT eh.RIA_CONTACT_CRD_ID) as rep_count
    FROM lead_dates ld
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) = ld.firm_crd
        -- Rep was active at this firm on contacted_date
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= ld.contacted_date
        AND (
            eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL
            OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE > ld.contacted_date
        )
    GROUP BY ld.firm_crd, ld.contacted_date
)

SELECT * FROM rep_counts;


-- Phase 1.2: Create enhanced feature table with firm_rep_count
CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2` AS

SELECT
    f.*,
    COALESCE(rc.rep_count, 0) as firm_rep_count_at_contact
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
LEFT JOIN `savvy-gtm-analytics.ml_features.firm_rep_counts_pit` rc
    ON f.firm_crd_at_contact = rc.firm_crd
    AND f.contacted_date = rc.contacted_date;


-- Phase 1.3: Validate
SELECT
    COUNT(*) as total_leads,
    COUNTIF(firm_rep_count_at_contact > 0) as has_rep_count,
    COUNTIF(firm_rep_count_at_contact = 0) as unknown_rep_count,
    AVG(firm_rep_count_at_contact) as avg_rep_count
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2`;
```

### 6.4 Validation Gates

| Gate ID | Check | Pass Criteria | Action if Fail |
|---------|-------|---------------|----------------|
| G1.1 | Feature table created | Table exists | Check SQL errors |
| G1.2 | Row count matches | V2 rows = V1 rows | Check JOIN logic |
| G1.3 | Rep count coverage | > 5% have data | Expected - most will be 0 |

---

## 7. Phase 2: Tier Scoring Implementation {#7-phase-2-tier-scoring}

### 7.1 Objective

Create the final scored leads table with tier assignments.

### 7.2 SQL: Final Tier Scoring

**File:** `sql/phase_2_tier_scoring.sql`

```sql
-- Phase 2: V3.1 Final Tier Scoring
-- Based on empirically validated tier definitions

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scores_v3_final` AS

WITH lead_features AS (
    SELECT
        f.lead_id,
        f.advisor_crd,
        f.contacted_date,
        f.target as converted,
        f.current_firm_tenure_months / 12.0 as tenure_years,
        f.industry_tenure_months / 12.0 as experience_years,
        f.firm_crd_at_contact,
        f.firm_net_change_12mo,
        f.firm_rep_count_at_contact,
        f.pit_moves_3yr,
        l.Company as company_name,
        l.FirstName as first_name,
        l.LastName as last_name,
        l.Email as email
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2` f
    INNER JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
        ON f.lead_id = l.Id
),

wirehouse_flagged AS (
    SELECT
        *,
        CASE 
            WHEN UPPER(company_name) LIKE '%MERRILL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%MORGAN STANLEY%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%UBS %' THEN TRUE
            WHEN UPPER(company_name) LIKE '%WELLS FARGO%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%EDWARD JONES%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%RAYMOND JAMES%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%AMERIPRISE%' THEN TRUE
            WHEN UPPER(company_name) LIKE '% LPL %' THEN TRUE
            WHEN UPPER(company_name) LIKE '%LPL FINANCIAL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%NORTHWESTERN MUTUAL%' THEN TRUE
            ELSE FALSE
        END as is_wirehouse
    FROM lead_features
),

scored AS (
    SELECT
        *,
        
        -- TIER ASSIGNMENT (Priority Order by Actual Lift)
        CASE
            -- TIER 1: PRIME MOVERS (3.40x actual lift)
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 1
            
            -- TIER 2: MODERATE BLEEDERS (2.77x actual lift)
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND experience_years >= 5
            THEN 2
            
            -- TIER 3: EXPERIENCED MOVERS (2.65x actual lift)
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 3
            
            -- TIER 4: HEAVY BLEEDERS (2.28x actual lift)
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 4
            
            -- STANDARD: Everything else
            ELSE 99
        END as tier_rank,
        
        -- Tier names
        CASE
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 'TIER_1_PRIME_MOVER'
            
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND experience_years >= 5
            THEN 'TIER_2_MODERATE_BLEEDER'
            
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 'TIER_3_EXPERIENCED_MOVER'
            
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 'TIER_4_HEAVY_BLEEDER'
            
            ELSE 'STANDARD'
        END as tier_name,
        
        -- Expected lift (validated values)
        CASE
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 3.40
            
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
                 AND experience_years >= 5
            THEN 2.77
            
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 2.65
            
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 2.28
            
            ELSE 1.00
        END as expected_lift
        
    FROM wirehouse_flagged
)

SELECT
    lead_id,
    advisor_crd,
    contacted_date,
    first_name,
    last_name,
    email,
    company_name,
    tier_rank,
    tier_name,
    expected_lift,
    tenure_years,
    experience_years,
    firm_net_change_12mo,
    firm_rep_count_at_contact,
    is_wirehouse,
    pit_moves_3yr,
    converted,
    CURRENT_TIMESTAMP() as scored_at,
    'v3.1-final-20241221' as model_version
FROM scored
ORDER BY tier_rank, expected_lift DESC, contacted_date DESC;
```

### 7.3 Validation Query

```sql
-- Validate tier distribution and lift
SELECT
    tier_name,
    tier_rank,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (
        SELECT AVG(converted) 
        FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
    ), 2) as actual_lift,
    ROUND(AVG(expected_lift), 2) as expected_lift
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
GROUP BY 1, 2
ORDER BY tier_rank;
```

### 7.4 Expected Results

| Tier | Leads | Conv % | Actual Lift | Expected |
|------|-------|--------|-------------|----------|
| T1: Prime Movers | ~194 | ~12.9% | ~3.40x | 3.40x |
| T2: Moderate Bleeders | ~124 | ~10.5% | ~2.77x | 2.77x |
| T3: Experienced Movers | ~199 | ~10.1% | ~2.65x | 2.65x |
| T4: Heavy Bleeders | ~1,388 | ~8.7% | ~2.28x | 2.28x |
| Standard | ~37,000 | ~3.5% | ~0.92x | 1.00x |

---

## 8. Phase 3: Validation & Backtesting {#8-phase-3-validation}

### 8.1 Validation Framework

#### 8.1.1 In-Sample Validation

Verify tiers on the training data:

```sql
-- In-sample validation
SELECT
    tier_name,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conv_rate,
    ROUND(AVG(converted) / 0.0369, 2) as lift
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
WHERE contacted_date BETWEEN '2024-02-01' AND '2025-07-03'
GROUP BY 1
ORDER BY lift DESC;
```

#### 8.1.2 Out-of-Sample Validation (Temporal)

Test on held-out future data:

```sql
-- Out-of-sample validation (test period)
SELECT
    tier_name,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conv_rate,
    ROUND(AVG(converted) / (
        SELECT AVG(converted) 
        FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
        WHERE contacted_date BETWEEN '2025-08-02' AND '2025-10-01'
    ), 2) as lift
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
WHERE contacted_date BETWEEN '2025-08-02' AND '2025-10-01'
GROUP BY 1
ORDER BY lift DESC;
```

#### 8.1.3 Comparison vs XGBoost

**File:** `sql/phase_3_ml_comparison.py`

```python
# Compare V3.1 Rules vs XGBoost
# Already validated - Results:
#   V3.1 Rules: 1.74x lift (WINNER)
#   Raw XGBoost: 1.63x lift
#   Hybrid: 1.72x lift
```

### 8.2 Backtest: Time Machine Validation

Simulate deploying at different points in time:

```sql
-- Backtest: Train on H1 2024, test on H2 2024
WITH scored AS (
    SELECT
        *,
        CASE 
            WHEN contacted_date < '2024-07-01' THEN 'TRAIN'
            ELSE 'TEST'
        END as split
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
    WHERE contacted_date BETWEEN '2024-02-01' AND '2024-12-31'
)

SELECT
    split,
    tier_name,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conv_rate
FROM scored
GROUP BY 1, 2
ORDER BY 1, conv_rate DESC;
```

### 8.3 Validation Gates

| Gate ID | Check | Pass Criteria | Action if Fail |
|---------|-------|---------------|----------------|
| G3.1 | T1 Lift | ≥ 2.5x | Check thresholds |
| G3.2 | T2 Lift | ≥ 2.0x | Check thresholds |
| G3.3 | Combined Priority Lift | ≥ 2.0x | Review tier defs |
| G3.4 | Rules ≥ XGBoost | Rules lift ≥ ML lift | Use hybrid |
| G3.5 | Temporal stability | Test lift within 30% of train | Investigate drift |

---

## 9. Phase 4: Production Deployment {#9-phase-4-deployment}

### 9.1 Deployment Checklist

| Step | Task | Owner | Status |
|------|------|-------|--------|
| 4.1 | Create production scoring table | Data Eng | ☐ |
| 4.2 | Set up daily refresh job | Data Eng | ☐ |
| 4.3 | Configure Salesforce sync | RevOps | ☐ |
| 4.4 | Create monitoring dashboard | Analytics | ☐ |
| 4.5 | Document for SDR team | RevOps | ☐ |

### 9.2 Salesforce Field Mapping

| BigQuery Column | Salesforce Field | Type |
|-----------------|------------------|------|
| tier_rank | Lead_Score_Tier__c | Number |
| tier_name | Lead_Score_Tier_Name__c | Text |
| expected_lift | Lead_Score_Expected_Lift__c | Number |
| model_version | Lead_Score_Model_Version__c | Text |

### 9.3 Monitoring Queries

```sql
-- Daily monitoring: Tier distribution
SELECT
    DATE(scored_at) as score_date,
    tier_name,
    COUNT(*) as n_leads
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
WHERE scored_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- Weekly monitoring: Conversion by tier (lagged 30 days)
SELECT
    tier_name,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
WHERE contacted_date BETWEEN 
    DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
    AND DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 1
ORDER BY conv_rate DESC;
```

### 9.4 Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| T1 Lift | < 2.5x | < 2.0x |
| Combined Priority Lift | < 2.0x | < 1.5x |
| T1 Volume | < 100/month | < 50/month |
| Total Scored | < 1000/month | < 500/month |

---

## 10. Execution Log {#10-execution-log}

### Log Format

```markdown
## [DATE] Phase X.Y: [Name]

**Status:** PASSED / FAILED / IN PROGRESS
**Duration:** X minutes
**Executed By:** [Name]

### What We Did
- Step 1
- Step 2

### Results
| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|

### Decisions Made
- Decision 1: Rationale

### Issues Encountered
- Issue 1: Resolution

### Next Steps
- [ ] Task 1
- [ ] Task 2
```

---

### [2024-12-21] Phase 0: Data Foundation

**Status:** ✅ PASSED  
**Duration:** 15 minutes  
**Executed By:** Russell

#### What We Did
- Verified Firm_historicals coverage (23 months)
- Confirmed lead volume (56,982 leads)
- Validated CRD match rate (94.03%)

#### Results
| Gate | Expected | Actual | Status |
|------|----------|--------|--------|
| G0.1 Firm months | ≥ 20 | 23 | ✅ |
| G0.2 Lead volume | ≥ 10,000 | 56,982 | ✅ |
| G0.3 CRD match | ≥ 90% | 94.03% | ✅ |
| G0.4 Recent data | ≤ 30 days | 2 days | ✅ |

---

### [2024-12-21] Phase 1: Feature Engineering

**Status:** ✅ PASSED  
**Duration:** 20 minutes  
**Executed By:** Russell

#### What We Did
- Created `firm_rep_counts_pit` table
- Created `lead_scoring_features_pit_v2` with firm_rep_count
- Validated distribution

#### Results
| Metric | Value |
|--------|-------|
| Total leads | 39,448 |
| Has rep count | 3,375 (8.5%) |
| Unknown (0) | 36,073 (91.5%) |
| Avg rep count | 81.8 |

#### Decisions Made
- **firm_rep_count = 0 means UNKNOWN**, not small firm
- Will NOT use firm size as standalone tier criteria

---

### [2024-12-21] Phase 2: Tier Scoring

**Status:** ✅ PASSED  
**Duration:** 10 minutes  
**Executed By:** Russell

#### What We Did
- Created `lead_scores_v3_final` table
- Applied corrected tier definitions
- Validated tier distribution

#### Results
| Tier | Leads | Conv % | Lift |
|------|-------|--------|------|
| T1: Prime Movers | 194 | 12.89% | 3.40x |
| T2: Moderate Bleeders | 124 | 10.48% | 2.77x |
| T3: Experienced Movers | 199 | 10.05% | 2.65x |
| T4: Heavy Bleeders | 1,388 | 8.65% | 2.28x |
| Standard | 37,151 | 3.49% | 0.92x |

**Priority Leads:** 1,905 at 2.29x combined lift

---

### [2024-12-21] Phase 3: Validation

**Status:** ✅ PASSED  
**Duration:** 15 minutes  
**Executed By:** Russell

#### What We Did
- Compared V3.1 Rules vs XGBoost vs Hybrid
- Temporal split: 70% train / 30% test
- Calculated top decile lift for each method

#### Results
| Method | Top Decile Lift | Status |
|--------|-----------------|--------|
| **V3.1 Rules** | **1.74x** | 🏆 Winner |
| Raw XGBoost | 1.63x | |
| Hybrid | 1.72x | |

#### Decisions Made
- **Use rules-based approach** - outperforms ML
- **No hybrid needed** - marginal improvement not worth complexity

---

### [2024-12-21] Diagnostic Analysis

**Status:** ✅ COMPLETED  
**Duration:** 30 minutes  
**Executed By:** Russell + Claude

#### Key Findings

1. **Tenure thresholds were inverted**
   - Original: 4-10yr = "Platinum"
   - Corrected: 1-4yr = "Prime Movers" (4.08x lift vs 1.5-1.9x)

2. **Small firm rule was backwards**
   - Small (≤10): 0.96x lift (below baseline!)
   - Medium/Large: 2.4-2.6x lift
   - Decision: DROP small firm rule

3. **Bleeding firm thresholds adjusted**
   - Split into Moderate (-10 to -1) and Heavy (<-10)
   - Moderate actually outperformed (2.77x vs 2.28x)

4. **Wirehouse detection confirmed critical**
   - 58% of XGBoost feature importance
   - Keep in Tier 1 definition

---

## Appendix A: SQL Files Summary

| File | Purpose | Phase |
|------|---------|-------|
| `phase_0_data_foundation.sql` | Pre-flight checks | 0 |
| `phase_1_add_firm_rep_count.sql` | Add firm_rep_count feature | 1 |
| `phase_2_tier_scoring.sql` | Create scored leads table | 2 |
| `phase_3_validation.sql` | Validation queries | 3 |

## Appendix B: Python Scripts Summary

| File | Purpose | Location |
|------|---------|----------|
| `create_v3_final_tiers.py` | Create and validate final table | `Version-3/` |
| `compare_v3_vs_ml.py` | Head-to-head ML comparison | `Version-3/` |
| `diagnose_v3_features.py` | Feature distribution analysis | `Version-3/` |
| `test_corrected_tiers.py` | Tier threshold validation | `Version-3/` |

## Appendix C: Key Metrics Reference

| Metric | Definition | Target |
|--------|------------|--------|
| Top Decile Lift | Conversion rate of top 10% / baseline | ≥ 1.5x |
| Tier Lift | Tier conversion / baseline conversion | ≥ 2.0x for priority |
| Priority Volume | Leads in Tiers 1-4 | ≥ 1,500/period |
| Combined Priority Lift | Weighted average lift of T1-T4 | ≥ 2.0x |

---

# END OF UPDATED LEADSCORING_PLAN.MD
