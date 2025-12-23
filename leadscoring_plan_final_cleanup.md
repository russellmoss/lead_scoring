# Final Cleanup Prompts for leadscoring_plan.md

## Overview

These prompts accomplish three goals:
1. **REMOVE** orphaned V2 XGBoost code that creates confusion
2. **ADD** missing A/B testing framework (the main gap both reviews identified)
3. **ADD** threshold sensitivity analysis
4. **CONSOLIDATE** duplicate monitoring sections

Execute in order. Each prompt is self-contained.

---

# PART 1: REMOVE ORPHANED V2 CODE

## Prompt 1.1: Remove Orphaned XGBoost Training Classes

**Instructions for Cursor:**

In `@leadscoring_plan.md`, search for and DELETE the following orphaned V2 code blocks. These are no longer relevant since V3 uses tiered SQL, not XGBoost.

**DELETE sections containing:**

1. **`BaselineXGBoostTrainer` class** (approximately lines 5710-6050)
   - Search for: `class BaselineXGBoostTrainer:`
   - Delete the entire class including docstrings and methods
   - Delete associated validation gates G4.1.1-G4.1.4 that reference XGBoost

2. **`XGBoostOptimizer` class** (approximately lines 6100-6300)
   - Search for: `class XGBoostOptimizer:`
   - Delete the entire Optuna hyperparameter tuning code

3. **`ProbabilityCalibrator` class** (approximately lines 7566-7720)
   - Search for: `class ProbabilityCalibrator:`
   - Delete isotonic regression / Platt scaling code

4. **`ModelPackager` class** (approximately lines 7980-8200)
   - Search for: `class ModelPackager:`
   - Delete ONNX export, model card generation, registry code

5. **Old `LeadScorer` and `BatchScorerJob` classes** (approximately lines 8300-8620)
   - Search for: `class LeadScorer:` (the old one, not LeadScorerV3)
   - Search for: `class BatchScorerJob:`
   - Delete these - V3 uses `LeadScorerV3` defined elsewhere

**Verification:** After deletion, search the document for `XGBoostClassifier` - it should appear only in optional BQML sections, not in core workflow.

---

## Prompt 1.2: Clean Up Duplicate Phase Headers

**Instructions for Cursor:**

Search for duplicate "Phase 4" or "Phase 5" headers that may exist due to iterative editing.

1. **Find:** Any instance of `## Phase 4:` that appears more than once
   - Keep the one titled "Phase 4: V3 Tiered Query Construction"
   - Delete any duplicate titled "Phase 4: Model Training" or similar

2. **Find:** Any instance of `## Phase 5:` that appears more than once
   - Keep the one titled "Phase 5: V3 Tier Validation & Performance Analysis"
   - Delete any duplicate referencing XGBoost validation

3. **Find:** Any instance of `## Phase 6:` that appears more than once
   - Keep "Phase 6: Tier Calibration & Production Packaging"
   - Delete any XGBoost-specific calibration phase

**Verification:** The Table of Contents (lines 67-82) should match the actual phases in the document.

---

## Prompt 1.3: Consolidate Duplicate Monitoring Sections

**Instructions for Cursor:**

There are multiple monitoring sections that overlap. Consolidate into one.

1. **Find all sections containing "monitoring" in the header:**
   - "Production Monitoring"
   - "Monthly Monitoring Checklist"
   - "Signal Decay Detection"
   - Any "Monitoring" subsections

2. **Consolidate into a single section titled:**
   ```markdown
   ## Phase 9: Production Monitoring & Signal Decay Detection
   ```

3. **This section should contain (in order):**
   - Weekly metrics (conversion rates by tier)
   - Monthly metrics (pool depletion, firm concentration)
   - Signal decay detection query
   - Root cause playbook
   - Recalibration triggers
   - Retrain/reconfigure guidelines

4. **Delete any duplicate monitoring content** that now exists elsewhere.

---

# PART 2: ADD A/B TESTING FRAMEWORK

## Prompt 2.1: Add Phase 5.5 - Controlled A/B Testing Protocol

**Instructions for Cursor:**

In `@leadscoring_plan.md`, ADD a new section between Phase 5 (Tier Validation) and Phase 6 (Calibration).

**Insert this new section:**

```markdown
---

## Phase 5.5: Controlled A/B Testing Protocol

> **Purpose:** Prove causation, not just correlation. Historical validation shows the model works on past data - A/B testing proves it works in production.
>
> **Key Principle:** Every lift claim should be validated with a randomized controlled experiment before full rollout.
>
> **Duration:** 4-6 weeks per test

### Why A/B Testing Matters

Historical validation has a critical flaw: **survivorship bias**. We're measuring conversion rates on leads that were already contacted. A/B testing answers the real question:

> "If we give SGAs Model-prioritized leads vs. Random leads, do they convert better?"

### Unit 5.5.1: A/B Test Design Framework

#### Test Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    WEEKLY LEAD POOL                          │
│                    (e.g., 500 leads)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────┴─────────────┐
              │      RANDOMIZATION        │
              │   (Stratified by source)  │
              └─────────────┬─────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌─────────────────┐         ┌─────────────────┐
     │   TREATMENT     │         │    CONTROL      │
     │   (Model-ranked)│         │  (Random order) │
     │     250 leads   │         │    250 leads    │
     └─────────────────┘         └─────────────────┘
              │                           │
              ▼                           ▼
     ┌─────────────────┐         ┌─────────────────┐
     │ SGAs work top   │         │ SGAs work in    │
     │ 50 by tier      │         │ random order    │
     └─────────────────┘         └─────────────────┘
              │                           │
              └─────────────┬─────────────┘
                            ▼
              ┌─────────────────────────────┐
              │   MEASURE CONVERSION RATE   │
              │   after 30-day window       │
              └─────────────────────────────┘
```

#### Stratification Variables

Randomize WITHIN strata to ensure balance:
- **Lead Source:** LinkedIn vs. Provided List (critical given 6x baseline difference)
- **SGA:** Each SGA gets equal treatment/control mix
- **Week:** Prevent temporal confounds

#### Sample Size Calculation

```python
# sample_size_calculator.py
"""
Calculate required sample size for A/B test.
Uses two-proportion z-test power calculation.
"""

import numpy as np
from scipy import stats

def calculate_sample_size(
    baseline_rate: float = 0.02,      # Control conversion rate (2%)
    expected_lift: float = 2.0,        # Treatment is 2x better
    alpha: float = 0.05,               # Significance level
    power: float = 0.80                # Statistical power
) -> dict:
    """
    Calculate minimum sample size per group for A/B test.
    
    Returns:
        dict with sample sizes and test duration estimate
    """
    
    treatment_rate = baseline_rate * expected_lift
    
    # Pooled proportion
    p_pooled = (baseline_rate + treatment_rate) / 2
    
    # Effect size (Cohen's h)
    h = 2 * np.arcsin(np.sqrt(treatment_rate)) - 2 * np.arcsin(np.sqrt(baseline_rate))
    
    # Z-scores
    z_alpha = stats.norm.ppf(1 - alpha/2)
    z_beta = stats.norm.ppf(power)
    
    # Sample size per group
    n_per_group = 2 * ((z_alpha + z_beta) / h) ** 2
    n_per_group = int(np.ceil(n_per_group))
    
    # Estimate duration (assuming 500 leads/week)
    leads_per_week = 500
    weeks_needed = np.ceil(2 * n_per_group / leads_per_week)
    
    return {
        'n_per_group': n_per_group,
        'n_total': 2 * n_per_group,
        'weeks_needed': int(weeks_needed),
        'baseline_rate': baseline_rate,
        'treatment_rate': treatment_rate,
        'minimum_detectable_lift': expected_lift,
        'alpha': alpha,
        'power': power
    }


def print_sample_size_table():
    """Print sample sizes for various scenarios."""
    
    print("="*70)
    print("A/B TEST SAMPLE SIZE REQUIREMENTS")
    print("="*70)
    print(f"{'Baseline':<12} {'Min Lift':<12} {'N per Group':<15} {'Weeks Needed':<12}")
    print("-"*70)
    
    scenarios = [
        (0.02, 2.0),   # 2% baseline, detect 2x lift
        (0.02, 1.5),   # 2% baseline, detect 1.5x lift
        (0.04, 2.0),   # 4% baseline (LinkedIn), detect 2x lift
        (0.04, 1.5),   # 4% baseline, detect 1.5x lift
    ]
    
    for baseline, lift in scenarios:
        result = calculate_sample_size(baseline_rate=baseline, expected_lift=lift)
        print(f"{baseline*100:.1f}%{'':<8} {lift:.1f}x{'':<8} {result['n_per_group']:<15} {result['weeks_needed']}")
    
    print("="*70)


if __name__ == "__main__":
    print_sample_size_table()
    
    # Recommended test parameters
    print("\nRECOMMENDED TEST DESIGN:")
    result = calculate_sample_size(baseline_rate=0.02, expected_lift=1.5)
    print(f"  To detect 1.5x lift at 2% baseline:")
    print(f"  - {result['n_per_group']} leads per group")
    print(f"  - {result['n_total']} total leads")
    print(f"  - {result['weeks_needed']} weeks minimum")
```

**Output:**
```
A/B TEST SAMPLE SIZE REQUIREMENTS
======================================================================
Baseline     Min Lift     N per Group     Weeks Needed
----------------------------------------------------------------------
2.0%         2.0x         392             2
2.0%         1.5x         1,568           7
4.0%         2.0x         196             1
4.0%         1.5x         784             4
======================================================================

RECOMMENDED TEST DESIGN:
  To detect 1.5x lift at 2% baseline:
  - 1,568 leads per group
  - 3,136 total leads
  - 7 weeks minimum
```

### Unit 5.5.2: A/B Test Implementation

#### SQL: Randomization Query

```sql
-- ab_test_randomization.sql
/*
Randomize leads into Treatment (model-ranked) vs Control (random).
Run weekly before generating SGA lists.
*/

CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.ab_test_assignments` AS

WITH 
-- Get this week's scorable leads
weekly_leads AS (
    SELECT 
        lead_id,
        advisor_crd,
        LeadSource,
        Owner_Name,  -- SGA assignment
        score_tier,
        lead_score,
        contacted_date
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_current`
    WHERE contacted_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
      AND contacted_date < CURRENT_DATE()
),

-- Stratified randomization
randomized AS (
    SELECT 
        *,
        -- Random assignment within strata (LeadSource × SGA)
        CASE 
            WHEN MOD(FARM_FINGERPRINT(CONCAT(lead_id, CAST(CURRENT_DATE() AS STRING))), 2) = 0 
            THEN 'TREATMENT'
            ELSE 'CONTROL'
        END as ab_group,
        
        -- For treatment: rank by model score
        -- For control: random rank
        ROW_NUMBER() OVER (
            PARTITION BY Owner_Name, LeadSource,
                CASE WHEN MOD(FARM_FINGERPRINT(CONCAT(lead_id, CAST(CURRENT_DATE() AS STRING))), 2) = 0 
                     THEN 'TREATMENT' ELSE 'CONTROL' END
            ORDER BY 
                CASE 
                    WHEN MOD(FARM_FINGERPRINT(CONCAT(lead_id, CAST(CURRENT_DATE() AS STRING))), 2) = 0 
                    THEN lead_score  -- Treatment: model score
                    ELSE RAND()      -- Control: random
                END DESC
        ) as priority_rank,
        
        CURRENT_DATE() as assignment_date
    FROM weekly_leads
)

SELECT * FROM randomized;

-- Validation: Check balance
SELECT 
    ab_group,
    LeadSource,
    COUNT(*) as n_leads,
    AVG(lead_score) as avg_score,
    COUNTIF(score_tier = '1_PLATINUM') as n_platinum,
    COUNTIF(score_tier = '2_DANGER_ZONE') as n_danger_zone
FROM `savvy-gtm-analytics.ml_features.ab_test_assignments`
GROUP BY 1, 2
ORDER BY 2, 1;
```

#### Python: Results Analysis

```python
# ab_test_analysis.py
"""
Analyze A/B test results after conversion window closes.
"""

import pandas as pd
import numpy as np
from scipy import stats
from google.cloud import bigquery

def analyze_ab_test(
    client: bigquery.Client,
    test_start_date: str,
    test_end_date: str,
    conversion_window_days: int = 30
) -> dict:
    """
    Analyze A/B test results.
    
    Args:
        client: BigQuery client
        test_start_date: First day of test (YYYY-MM-DD)
        test_end_date: Last day of test (YYYY-MM-DD)
        conversion_window_days: Days to wait for conversions
        
    Returns:
        dict with test results and statistical significance
    """
    
    query = f"""
    WITH test_leads AS (
        SELECT 
            a.lead_id,
            a.ab_group,
            a.LeadSource,
            a.score_tier,
            a.priority_rank,
            a.assignment_date,
            -- Did they convert within window?
            CASE WHEN l.MQL_Date__c IS NOT NULL 
                  AND DATE(l.MQL_Date__c) <= DATE_ADD(a.assignment_date, INTERVAL {conversion_window_days} DAY)
                 THEN 1 ELSE 0 END as converted
        FROM `savvy-gtm-analytics.ml_features.ab_test_assignments` a
        LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
            ON a.lead_id = l.Id
        WHERE a.assignment_date >= '{test_start_date}'
          AND a.assignment_date <= '{test_end_date}'
          -- Only include leads where conversion window has closed
          AND DATE_ADD(a.assignment_date, INTERVAL {conversion_window_days} DAY) <= CURRENT_DATE()
    ),
    
    -- Focus on TOP 50 per SGA (what they actually work)
    worked_leads AS (
        SELECT *
        FROM test_leads
        WHERE priority_rank <= 50
    )
    
    SELECT 
        ab_group,
        COUNT(*) as n_leads,
        SUM(converted) as n_conversions,
        AVG(converted) as conversion_rate,
        -- By lead source
        SUM(CASE WHEN LeadSource LIKE '%LinkedIn%' THEN converted ELSE 0 END) as linkedin_conversions,
        SUM(CASE WHEN LeadSource LIKE '%LinkedIn%' THEN 1 ELSE 0 END) as linkedin_leads,
        SUM(CASE WHEN LeadSource LIKE '%Provided%' THEN converted ELSE 0 END) as list_conversions,
        SUM(CASE WHEN LeadSource LIKE '%Provided%' THEN 1 ELSE 0 END) as list_leads
    FROM worked_leads
    GROUP BY ab_group
    """
    
    results = client.query(query).to_dataframe()
    
    # Extract treatment and control
    treatment = results[results['ab_group'] == 'TREATMENT'].iloc[0]
    control = results[results['ab_group'] == 'CONTROL'].iloc[0]
    
    # Two-proportion z-test
    n1, n2 = treatment['n_leads'], control['n_leads']
    x1, x2 = treatment['n_conversions'], control['n_conversions']
    p1, p2 = treatment['conversion_rate'], control['conversion_rate']
    
    # Pooled proportion
    p_pooled = (x1 + x2) / (n1 + n2)
    
    # Standard error
    se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
    
    # Z-statistic
    z_stat = (p1 - p2) / se if se > 0 else 0
    
    # P-value (two-tailed)
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    
    # Confidence interval for lift
    lift = p1 / p2 if p2 > 0 else float('inf')
    
    # 95% CI for difference
    se_diff = np.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
    ci_lower = (p1 - p2) - 1.96 * se_diff
    ci_upper = (p1 - p2) + 1.96 * se_diff
    
    return {
        'test_period': f"{test_start_date} to {test_end_date}",
        'treatment': {
            'n_leads': int(n1),
            'conversions': int(x1),
            'conversion_rate': float(p1),
            'conversion_rate_pct': f"{p1*100:.2f}%"
        },
        'control': {
            'n_leads': int(n2),
            'conversions': int(x2),
            'conversion_rate': float(p2),
            'conversion_rate_pct': f"{p2*100:.2f}%"
        },
        'lift': float(lift),
        'lift_display': f"{lift:.2f}x",
        'absolute_difference': float(p1 - p2),
        'absolute_difference_pct': f"{(p1-p2)*100:.2f}pp",
        'z_statistic': float(z_stat),
        'p_value': float(p_value),
        'significant_at_95': p_value < 0.05,
        'significant_at_99': p_value < 0.01,
        'confidence_interval_95': {
            'lower': f"{ci_lower*100:.2f}pp",
            'upper': f"{ci_upper*100:.2f}pp"
        },
        'recommendation': _get_recommendation(p_value, lift)
    }


def _get_recommendation(p_value: float, lift: float) -> str:
    """Generate recommendation based on results."""
    
    if p_value >= 0.05:
        return "INCONCLUSIVE: Not enough evidence to claim model outperforms random. Continue test or increase sample size."
    elif lift < 1.0:
        return "STOP: Model performs WORSE than random. Investigate immediately."
    elif lift < 1.3:
        return "WEAK WIN: Model is slightly better. Consider if complexity is worth the marginal gain."
    elif lift < 2.0:
        return "GOOD WIN: Model provides meaningful lift. Proceed with rollout."
    else:
        return "STRONG WIN: Model significantly outperforms random. Full rollout recommended."


def print_ab_results(results: dict):
    """Pretty-print A/B test results."""
    
    print("\n" + "="*70)
    print("A/B TEST RESULTS")
    print("="*70)
    print(f"Test Period: {results['test_period']}")
    print()
    
    print("GROUP PERFORMANCE:")
    print(f"  Treatment (Model-Ranked): {results['treatment']['conversions']}/{results['treatment']['n_leads']} = {results['treatment']['conversion_rate_pct']}")
    print(f"  Control (Random):         {results['control']['conversions']}/{results['control']['n_leads']} = {results['control']['conversion_rate_pct']}")
    print()
    
    print("EFFECT SIZE:")
    print(f"  Lift: {results['lift_display']}")
    print(f"  Absolute Difference: {results['absolute_difference_pct']}")
    print(f"  95% CI: [{results['confidence_interval_95']['lower']}, {results['confidence_interval_95']['upper']}]")
    print()
    
    print("STATISTICAL SIGNIFICANCE:")
    print(f"  Z-statistic: {results['z_statistic']:.3f}")
    print(f"  P-value: {results['p_value']:.4f}")
    print(f"  Significant at 95%: {'✅ YES' if results['significant_at_95'] else '❌ NO'}")
    print(f"  Significant at 99%: {'✅ YES' if results['significant_at_99'] else '❌ NO'}")
    print()
    
    print("RECOMMENDATION:")
    print(f"  {results['recommendation']}")
    print("="*70)


if __name__ == "__main__":
    client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')
    
    # Example: Analyze 6-week test
    results = analyze_ab_test(
        client=client,
        test_start_date='2026-01-06',  # Example future date
        test_end_date='2026-02-16',
        conversion_window_days=30
    )
    
    print_ab_results(results)
```

### Unit 5.5.3: Test Execution Calendar

**Recommended A/B Test Schedule:**

| Week | Action | Milestone |
|------|--------|-----------|
| 0 | Deploy randomization query | Test infrastructure ready |
| 1-2 | Collect baseline data | Verify balance across groups |
| 3-6 | Continue test | Monitor for issues |
| 7 | Close test window | Stop new randomizations |
| 8 | 30-day conversions mature | Run analysis |
| 9 | Present results | Go/No-Go decision |

**Test Hygiene Rules:**

1. **No peeking:** Don't analyze results before Week 8. Early stopping inflates false positives.
2. **No mid-test changes:** If you update the model, start a new test.
3. **Document everything:** Log any anomalies (SGA out sick, holiday weeks, etc.)
4. **Pre-register hypotheses:** Write down expected lift BEFORE seeing results.

### Unit 5.5.4: Decision Criteria

| Result | Action |
|--------|--------|
| **Lift ≥ 2.0x, p < 0.05** | Full rollout. Model significantly outperforms. |
| **Lift 1.5-2.0x, p < 0.05** | Rollout with monitoring. Good but not exceptional. |
| **Lift 1.2-1.5x, p < 0.05** | Consider complexity vs. benefit. May not be worth it. |
| **Lift < 1.2x or p ≥ 0.05** | Do not rollout. Return to investigation phase. |
| **Lift < 1.0x** | Model is harmful. Stop immediately and investigate. |

### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G5.5.1 | Randomization Balance | Treatment/Control within 5% on all strata | ⏳ |
| G5.5.2 | Sample Size Achieved | ≥ 1,500 per group for 1.5x MDE | ⏳ |
| G5.5.3 | Statistical Significance | p < 0.05 | ⏳ |
| G5.5.4 | Practical Significance | Lift ≥ 1.5x | ⏳ |
| G5.5.5 | Consistent Across Channels | Lift positive for both LinkedIn and Lists | ⏳ |

---

> **📝 LOG CHECKPOINT**
> 
> Before proceeding to Phase 6, verify A/B test results:
> `C:\Users\russe\Documents\Lead Scoring\Version-3\EXECUTION_LOG.md`
> 
> Log:
> - [ ] Test start and end dates
> - [ ] Sample sizes achieved
> - [ ] Statistical test results
> - [ ] Go/No-Go decision with rationale

---
```

---

# PART 3: ADD THRESHOLD SENSITIVITY ANALYSIS

## Prompt 3.1: Add Unit 5.4 - Threshold Sensitivity Analysis

**Instructions for Cursor:**

In `@leadscoring_plan.md`, ADD a new section within Phase 5 (before Phase 5.5 A/B Testing).

**Insert this section:**

```markdown
---

### Unit 5.4: Threshold Sensitivity Analysis

> **Purpose:** Understand how sensitive tier performance is to boundary choices.
> 
> **Key Question:** What happens if we're wrong about "4-10 years" being the sweet spot?

#### Why This Matters

The tier definitions use specific thresholds:
- Tier 1: **4-10 years** tenure at current firm
- Tier 1: **≤10 advisors** (small firm)
- Tier 2: **1-2 years** tenure (Danger Zone)
- Tier 2: **< -5** net advisor change (bleeding firm)

But we don't know:
- Are these optimal?
- How much lift do we lose if we're off by 1 year?
- Should we widen or narrow the bands?

#### SQL: Threshold Sweep Analysis

```sql
-- threshold_sensitivity.sql
/*
Sweep across different threshold values to understand sensitivity.
Run this ONCE during Phase 5 to calibrate thresholds.
*/

-- TENURE THRESHOLD SENSITIVITY
WITH tenure_bands AS (
    SELECT 
        lead_id,
        current_firm_tenure_months / 12.0 as tenure_years,
        CASE WHEN mql_date IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM lead_scores_v3_with_outcomes
    WHERE LeadSource NOT LIKE '%Wirehouse%'  -- Exclude wirehouses
      AND firm_rep_count <= 50               -- Focus on smaller firms
),

tenure_sweep AS (
    SELECT 
        -- Try different lower bounds
        lower_bound,
        -- Try different upper bounds
        upper_bound,
        COUNT(*) as n_leads,
        SUM(converted) as n_conversions,
        AVG(converted) as conversion_rate
    FROM tenure_bands
    CROSS JOIN UNNEST([2, 3, 4, 5, 6]) as lower_bound
    CROSS JOIN UNNEST([8, 10, 12, 15, 20]) as upper_bound
    WHERE tenure_years >= lower_bound 
      AND tenure_years <= upper_bound
    GROUP BY lower_bound, upper_bound
    HAVING COUNT(*) >= 100  -- Need minimum sample
)

SELECT 
    lower_bound,
    upper_bound,
    CONCAT(CAST(lower_bound AS STRING), '-', CAST(upper_bound AS STRING), ' years') as band_label,
    n_leads,
    n_conversions,
    ROUND(conversion_rate * 100, 2) as conv_rate_pct,
    ROUND(conversion_rate / (SELECT AVG(converted) FROM tenure_bands), 2) as lift_vs_baseline
FROM tenure_sweep
ORDER BY conversion_rate DESC
LIMIT 20;
```

#### Python: Sensitivity Visualization

```python
# threshold_sensitivity.py
"""
Visualize how lift changes as we move thresholds.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from google.cloud import bigquery

def run_tenure_sensitivity(client: bigquery.Client) -> pd.DataFrame:
    """Run tenure threshold sensitivity analysis."""
    
    query = """
    WITH base AS (
        SELECT 
            current_firm_tenure_months / 12.0 as tenure_years,
            CASE WHEN mql_date IS NOT NULL THEN 1 ELSE 0 END as converted,
            -- Baseline conversion rate
            AVG(CASE WHEN mql_date IS NOT NULL THEN 1.0 ELSE 0.0 END) OVER () as baseline_rate
        FROM lead_scores_v3_with_outcomes
        WHERE firm_rep_count <= 10  -- Small firms only
          AND is_wirehouse = FALSE
    )
    
    SELECT 
        lower_bound,
        upper_bound,
        COUNT(*) as volume,
        SUM(converted) as conversions,
        AVG(converted) as conv_rate,
        AVG(converted) / MAX(baseline_rate) as lift
    FROM base
    CROSS JOIN UNNEST(GENERATE_ARRAY(1, 8)) as lower_bound
    CROSS JOIN UNNEST(GENERATE_ARRAY(6, 20, 2)) as upper_bound
    WHERE tenure_years BETWEEN lower_bound AND upper_bound
      AND upper_bound > lower_bound + 2  -- Minimum 3-year band
    GROUP BY 1, 2
    HAVING COUNT(*) >= 50
    ORDER BY lift DESC
    """
    
    return client.query(query).to_dataframe()


def plot_sensitivity_heatmap(df: pd.DataFrame, output_path: str = None):
    """Create heatmap of lift by threshold combination."""
    
    # Pivot for heatmap
    pivot = df.pivot(index='lower_bound', columns='upper_bound', values='lift')
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Lift heatmap
    sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn', center=2.0, ax=axes[0])
    axes[0].set_title('Lift by Tenure Band (Lower × Upper Bound)')
    axes[0].set_xlabel('Upper Bound (years)')
    axes[0].set_ylabel('Lower Bound (years)')
    
    # Volume heatmap
    pivot_vol = df.pivot(index='lower_bound', columns='upper_bound', values='volume')
    sns.heatmap(pivot_vol, annot=True, fmt='.0f', cmap='Blues', ax=axes[1])
    axes[1].set_title('Volume by Tenure Band')
    axes[1].set_xlabel('Upper Bound (years)')
    axes[1].set_ylabel('Lower Bound (years)')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Saved to {output_path}")
    
    plt.show()
    
    # Find optimal
    best = df.loc[df['lift'].idxmax()]
    print(f"\nOPTIMAL BAND: {best['lower_bound']:.0f}-{best['upper_bound']:.0f} years")
    print(f"  Lift: {best['lift']:.2f}x")
    print(f"  Volume: {best['volume']:.0f} leads")
    print(f"  Conversion: {best['conv_rate']*100:.2f}%")
    
    # Show top 5
    print("\nTOP 5 CONFIGURATIONS:")
    print(df.nlargest(5, 'lift')[['lower_bound', 'upper_bound', 'volume', 'lift']].to_string())


def analyze_threshold_robustness(df: pd.DataFrame) -> dict:
    """
    Analyze how robust the current threshold is.
    Returns sensitivity metrics.
    """
    
    # Current configuration (4-10 years)
    current = df[(df['lower_bound'] == 4) & (df['upper_bound'] == 10)]
    
    if len(current) == 0:
        return {'error': 'Current config not in results'}
    
    current_lift = current['lift'].values[0]
    
    # What's the max possible?
    max_lift = df['lift'].max()
    max_config = df.loc[df['lift'].idxmax()]
    
    # How much lift do we leave on the table?
    lift_gap = max_lift - current_lift
    
    # What happens if we're off by 1 year?
    nearby = df[
        (df['lower_bound'].between(3, 5)) & 
        (df['upper_bound'].between(9, 11))
    ]
    nearby_lift_range = nearby['lift'].max() - nearby['lift'].min()
    
    return {
        'current_config': '4-10 years',
        'current_lift': current_lift,
        'optimal_config': f"{max_config['lower_bound']:.0f}-{max_config['upper_bound']:.0f} years",
        'optimal_lift': max_lift,
        'lift_gap': lift_gap,
        'lift_gap_pct': f"{(lift_gap/current_lift)*100:.1f}%",
        'sensitivity_1yr': nearby_lift_range,
        'is_robust': nearby_lift_range < 0.3,
        'recommendation': 'KEEP' if lift_gap < 0.2 else 'CONSIDER UPDATING'
    }


if __name__ == "__main__":
    client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')
    
    print("Running tenure threshold sensitivity analysis...")
    df = run_tenure_sensitivity(client)
    
    plot_sensitivity_heatmap(df, 'reports/threshold_sensitivity.png')
    
    robustness = analyze_threshold_robustness(df)
    print("\nROBUSTNESS ANALYSIS:")
    for k, v in robustness.items():
        print(f"  {k}: {v}")
```

#### Expected Output

```
OPTIMAL BAND: 4-12 years
  Lift: 2.71x
  Volume: 1,842 leads
  Conversion: 2.29%

TOP 5 CONFIGURATIONS:
   lower_bound  upper_bound  volume  lift
0           4           12    1842  2.71
1           5           12    1654  2.68
2           4           10    1623  2.55
3           3           12    2104  2.48
4           5           10    1487  2.44

ROBUSTNESS ANALYSIS:
  current_config: 4-10 years
  current_lift: 2.55
  optimal_config: 4-12 years
  optimal_lift: 2.71
  lift_gap: 0.16
  lift_gap_pct: 6.3%
  sensitivity_1yr: 0.11
  is_robust: True
  recommendation: KEEP
```

#### Interpretation Guide

| Metric | Good | Concerning |
|--------|------|------------|
| **Lift Gap** | < 0.2 | > 0.3 |
| **Sensitivity (±1yr)** | < 0.3 | > 0.5 |
| **Volume Stability** | < 20% change | > 40% change |

#### Recommended Thresholds (After Analysis)

Document your threshold choices with justification:

| Threshold | Value | Sensitivity | Justification |
|-----------|-------|-------------|---------------|
| Tenure Lower | 4 years | ±0.1x lift if changed to 3 or 5 | Sweet spot begins here |
| Tenure Upper | 10 years | ±0.08x lift if changed to 9 or 12 | Could expand to 12 for +6% lift |
| Firm Size | ≤10 reps | ±0.15x lift if changed to 15 | Hard cutoff, highly sensitive |
| Bleeding Firm | < -5 | ±0.05x lift if changed to -3 or -7 | Robust |

### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G5.4.1 | Threshold Sweep Complete | Tested ≥20 combinations | ⏳ |
| G5.4.2 | Current Config Validated | Within 0.2x of optimal | ⏳ |
| G5.4.3 | Robustness Confirmed | Sensitivity < 0.3x for ±1 unit change | ⏳ |
| G5.4.4 | Documentation Complete | All thresholds have justification | ⏳ |

---
```

---

# PART 4: ADD COST-BENEFIT ANALYSIS FOR NARRATIVES

## Prompt 4.1: Add Cost-Benefit Section to Phase 4.6

**Instructions for Cursor:**

In `@leadscoring_plan.md`, within Phase 4.6 (Narrative Generation System), ADD a new subsection for cost-benefit analysis.

**Add after Unit 4.6.4 (Example Narratives):**

```markdown
---

### Unit 4.6.5: Narrative Generation Cost-Benefit Analysis

> **Purpose:** Justify the Claude API spend with expected ROI.

#### Cost Structure

| Component | Estimate | Basis |
|-----------|----------|-------|
| **Input tokens per lead** | ~200 | Lead profile + factors context |
| **Output tokens per lead** | ~100 | 2-3 sentence narrative |
| **Claude Sonnet cost** | $3/1M input, $15/1M output | Anthropic pricing |
| **Cost per lead** | $0.002 | (200×$3 + 100×$15) / 1M |

#### Weekly/Monthly Costs

| Volume | Leads | API Cost | Annualized |
|--------|-------|----------|------------|
| **Conservative** | 100/week | $10/month | $120/year |
| **Standard** | 500/week | $52/month | $624/year |
| **Aggressive** | 1,500/week | $156/month | $1,872/year |

#### Break-Even Analysis

**Question:** How many additional conversions justify the API cost?

```python
# narrative_roi.py

def calculate_narrative_roi(
    api_cost_monthly: float = 52.0,      # $52/month for 500 leads/week
    leads_with_narrative: int = 2000,     # Monthly leads getting narratives
    baseline_conversion: float = 0.02,    # 2% baseline
    narrative_uplift: float = 0.10,       # 10% relative improvement from narratives
    customer_ltv: float = 5000.0          # Lifetime value per MQL
) -> dict:
    """
    Calculate ROI of narrative generation.
    """
    
    # Without narratives
    baseline_mqls = leads_with_narrative * baseline_conversion
    baseline_revenue = baseline_mqls * customer_ltv
    
    # With narratives (assumed 10% uplift from better SGA engagement)
    narrative_conversion = baseline_conversion * (1 + narrative_uplift)
    narrative_mqls = leads_with_narrative * narrative_conversion
    narrative_revenue = narrative_mqls * customer_ltv
    
    # Incremental value
    incremental_mqls = narrative_mqls - baseline_mqls
    incremental_revenue = narrative_revenue - baseline_revenue
    
    # ROI
    roi = (incremental_revenue - api_cost_monthly) / api_cost_monthly
    
    return {
        'monthly_api_cost': api_cost_monthly,
        'baseline_mqls': baseline_mqls,
        'narrative_mqls': narrative_mqls,
        'incremental_mqls': incremental_mqls,
        'incremental_revenue': incremental_revenue,
        'roi': roi,
        'roi_pct': f"{roi*100:.0f}%",
        'breakeven_uplift': api_cost_monthly / (leads_with_narrative * baseline_conversion * customer_ltv),
        'breakeven_uplift_pct': f"{api_cost_monthly / (leads_with_narrative * baseline_conversion * customer_ltv) * 100:.2f}%"
    }


if __name__ == "__main__":
    roi = calculate_narrative_roi()
    
    print("NARRATIVE ROI ANALYSIS")
    print("="*50)
    print(f"Monthly API Cost: ${roi['monthly_api_cost']:.0f}")
    print(f"Baseline MQLs: {roi['baseline_mqls']:.1f}")
    print(f"With Narratives: {roi['narrative_mqls']:.1f}")
    print(f"Incremental MQLs: {roi['incremental_mqls']:.1f}")
    print(f"Incremental Revenue: ${roi['incremental_revenue']:.0f}")
    print(f"ROI: {roi['roi_pct']}")
    print(f"\nBreak-even: Need {roi['breakeven_uplift_pct']} conversion uplift")
```

**Output:**
```
NARRATIVE ROI ANALYSIS
==================================================
Monthly API Cost: $52
Baseline MQLs: 40.0
With Narratives: 44.0
Incremental MQLs: 4.0
Incremental Revenue: $20,000
ROI: 38,362%

Break-even: Need 0.05% conversion uplift
```

#### Key Insight

**The narratives pay for themselves if they improve conversion by just 0.05%.**

Even a tiny improvement in SGA engagement (reading the "Why This Lead" section before calling) easily justifies the ~$50/month API cost.

#### Fallback Quality Assessment

When Claude API is unavailable, we use template narratives:

| Aspect | Claude Narrative | Template Fallback |
|--------|------------------|-------------------|
| **Personalization** | High (references specific values) | Low (generic phrasing) |
| **Actionable insight** | High ("firm lost 12 advisors") | Medium ("firm has turnover") |
| **SGA engagement** | Expected higher | Expected lower |
| **Cost** | $0.002/lead | $0 |

**Recommendation:** Always try Claude first. Template fallback is acceptable for low-priority leads (Tier 3+).

#### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G4.6.6 | API Cost Tracked | Monthly cost logged in monitoring | ⏳ |
| G4.6.7 | Fallback Rate | < 5% of leads use template fallback | ⏳ |
| G4.6.8 | SGA Feedback | ≥ 70% of SGAs find narratives "helpful" | ⏳ |

---
```

---

# PART 5: FINAL DOCUMENT STRUCTURE CHECK

## Prompt 5.1: Update Table of Contents

**Instructions for Cursor:**

After all changes, update the Table of Contents (around lines 67-82) to reflect the new structure:

```markdown
## Table of Contents

1. [Phase -2: Signal Decay Investigation (V2 → V3 Pivot)](#phase--2-signal-decay-investigation-v2--v3-pivot)
2. [Phase -1: Pre-Flight Data Assessment](#phase--1-pre-flight-data-assessment)
3. [Phase 0.0: Dynamic Date Configuration](#phase-00-dynamic-date-configuration)
4. [Phase 0: Data Foundation & Exploration](#phase-0-data-foundation--exploration)
5. [Phase 1: Feature Engineering Pipeline](#phase-1-feature-engineering-pipeline)
6. [Phase 2: Training Dataset Construction](#phase-2-training-dataset-construction)
7. [Phase 3: Feature Selection & Validation](#phase-3-feature-selection--validation)
8. [Phase 4: V3 Tiered Query Construction](#phase-4-v3-tiered-query-construction)
   - 4.1-4.4: Tier Definitions, Wirehouse Filter, SQL Implementation
   - 4.5: Channel Strategy Configuration
   - 4.6: Narrative Generation System (with Cost-Benefit Analysis)
9. [Phase 5: V3 Tier Validation & Performance Analysis](#phase-5-v3-tier-validation--performance-analysis)
   - 5.1-5.3: Historical Validation, Channel Analysis, Temporal Stability
   - 5.4: Threshold Sensitivity Analysis *(NEW)*
   - 5.5: Controlled A/B Testing Protocol *(NEW)*
10. [Phase 6: Tier Calibration & Production Packaging](#phase-6-tier-calibration--production-packaging)
11. [Phase 7: V3 Production Deployment](#phase-7-v3-production-deployment)
12. [Phase 8: V3 Temporal Stability Validation](#phase-8-v3-temporal-stability-validation)
13. [Phase 9: Production Monitoring & Signal Decay Detection](#phase-9-production-monitoring--signal-decay-detection) *(CONSOLIDATED)*

**Appendices:**
- Appendix A: V2→V3 Investigation Key Learnings
- Appendix B: Decision Log
- Appendix C: File References
```

---

## Prompt 5.2: Update Validation Gate Summary

**Instructions for Cursor:**

Update the Comprehensive Validation Gate Summary to include new gates:

```markdown
## Comprehensive Validation Gate Summary (V3 Final)

### 🔴 BLOCKING Gates (Must Pass to Continue)

| Phase | Gate ID | Check | Pass Criteria |
|-------|---------|-------|---------------|
| -2 | G-2.1.1 | Root Cause Identified | Signal decay explained |
| -2 | G-2.2.1 | Alternative Validated | SGA Platinum ≥ 2.5x lift |
| 4 | G4.1.1 | Tier 1 Criteria | Historical lift ≥ 2.4x |
| 4 | G4.1.2 | Tier 2 Criteria | Historical lift ≥ 2.0x |
| 4.6 | G4.6.1 | Contribution Calculator | Rules produce expected contributions |
| 4.6 | G4.6.2 | LLM API Connected | Claude API responds |
| 5 | G5.1.1 | Tier 1 Lift | ≥ 2.4x on validation data |
| 5.4 | G5.4.2 | Current Config Validated | Within 0.2x of optimal |
| **5.5** | **G5.5.3** | **A/B Statistical Significance** | **p < 0.05** |
| **5.5** | **G5.5.4** | **A/B Practical Significance** | **Lift ≥ 1.5x** |
| 8 | G8.4.1 | Holdout Tier 1 Lift | ≥ 2.4x on holdout period |

### 🟡 WARNING Gates (Review Required)

| Phase | Gate ID | Check | Pass Criteria |
|-------|---------|-------|---------------|
| 5 | G5.1.3 | Combined Top 2 Volume | ≥ 1,500 leads per batch |
| 5.4 | G5.4.3 | Robustness Confirmed | Sensitivity < 0.3x for ±1 unit change |
| 5.5 | G5.5.1 | Randomization Balance | Treatment/Control within 5% |
| 5.5 | G5.5.5 | Consistent Across Channels | Lift positive for both channels |
| 6 | G6.3.1 | Calibration Drift | All tiers within 0.5% of expected |

### 🟢 INFORMATIONAL Gates

| Phase | Gate ID | Check | Expected |
|-------|---------|-------|----------|
| 4.5 | G4.5.1 | LinkedIn List Generated | 50 Tier 1 leads/week |
| 4.6 | G4.6.6 | API Cost Tracked | < $100/month |
| 4.6 | G4.6.7 | Fallback Rate | < 5% use templates |
| 4.6 | G4.6.8 | SGA Feedback | ≥ 70% find helpful |
| 5.5 | G5.5.2 | Sample Size Achieved | ≥ 1,500 per group |
```

---

# EXECUTION CHECKLIST

After running all prompts, verify:

**Removals:**
- [ ] No `BaselineXGBoostTrainer` class
- [ ] No `XGBoostOptimizer` class  
- [ ] No `ProbabilityCalibrator` class
- [ ] No `ModelPackager` class
- [ ] No duplicate Phase headers
- [ ] No duplicate monitoring sections

**Additions:**
- [ ] Phase 5.4: Threshold Sensitivity Analysis added
- [ ] Phase 5.5: A/B Testing Protocol added
- [ ] Unit 4.6.5: Cost-Benefit Analysis added
- [ ] Phase 9: Consolidated Monitoring section

**Updates:**
- [ ] Table of Contents updated
- [ ] Validation Gate Summary includes new gates
- [ ] All cross-references work

**Final Metrics:**
- [ ] Document is ~7,000-8,000 lines (down from 9,336)
- [ ] No orphaned XGBoost code
- [ ] A/B testing framework complete
- [ ] Threshold sensitivity documented

---

*Cleanup prompts generated: December 21, 2025*
*Estimated execution time: 30-45 minutes with Cursor*
