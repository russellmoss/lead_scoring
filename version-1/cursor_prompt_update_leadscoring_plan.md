# Cursor.ai Prompt: Update Lead Scoring Agentic Plan

## Target File
`C:\Users\russe\Documents\Lead Scoring\leadscoring_plan.md`

---

## Prompt for Cursor.ai

```
I need you to comprehensively update my lead scoring agentic plan at C:\Users\russe\Documents\Lead Scoring\leadscoring_plan.md

This plan was originally written in late 2024 and has been executed, but we discovered several critical issues during development that must be incorporated. The current plan has hardcoded dates from 2024 and is missing important lessons learned about data leakage, feature engineering, and validation.

## CRITICAL ISSUE #1: HARDCODED DATES

The plan has hardcoded 2024 dates throughout that caused the model to train only on 2024 data even though we're now in December 2025. Find and fix ALL instances of hardcoded dates.

### Specific hardcoded dates to find and replace with dynamic logic:

1. `analysis_date: str = "2024-12-31"` in class constructors (lines ~377, ~661)
2. `TRAINING_SNAPSHOT_DATE = "2024-12-31"` (lines ~539, ~1577)
3. `contacted_date >= '2024-02-01'` training floor (lines ~2367-2371)
4. `contacted_date < '2024-10-01'` training ceiling (line ~6604-6605)
5. `contacted_date < '2024-08-01'` train/test split (line ~6624)
6. Any other hardcoded year references

### Replace with: Dynamic Date Configuration

Add a new **Phase 0.0: Dynamic Date Configuration** as the VERY FIRST step in the plan, before Phase 0. This phase MUST run before anything else and set all date parameters dynamically:

```python
# =============================================================================
# PHASE 0.0: DYNAMIC DATE CONFIGURATION (MANDATORY FIRST STEP)
# =============================================================================
# This module MUST execute first. All downstream phases import dates from here.
# NEVER hardcode dates in other phases - always reference these variables.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class DateConfiguration:
    """
    Central date configuration for the entire pipeline.
    All dates are calculated relative to execution date.
    """
    
    def __init__(self, execution_date: datetime = None):
        """
        Initialize date configuration.
        
        Args:
            execution_date: Override for testing. Defaults to today.
        """
        self.execution_date = execution_date or datetime.now()
        self._calculate_all_dates()
    
    def _calculate_all_dates(self):
        """Calculate all pipeline dates from execution date."""
        
        # TRAINING_SNAPSHOT_DATE: End of last complete month
        # This is our "as-of" date for the training set
        first_of_current_month = self.execution_date.replace(day=1)
        self.training_snapshot_date = (first_of_current_month - timedelta(days=1))
        
        # MATURITY_WINDOW: Days to wait for conversion outcome (30 days)
        self.maturity_window_days = 30
        
        # TRAINING_END_DATE: Latest contacted_date we can use
        # Must be at least maturity_window before snapshot to observe outcomes
        self.training_end_date = self.training_snapshot_date - timedelta(days=self.maturity_window_days)
        
        # TRAINING_START_DATE: Earliest contacted_date we can use
        # Constrained by Firm_historicals availability (starts Jan 2024)
        # Use Feb 2024 to ensure first month has prior month for comparison
        self.training_start_date = datetime(2024, 2, 1).date()
        
        # TEST_SPLIT_DATE: Where to split train vs test
        # Use 80/20 temporal split, or at minimum 60 days for test
        total_days = (self.training_end_date - self.training_start_date).days
        test_days = max(60, int(total_days * 0.2))
        self.test_split_date = self.training_end_date - timedelta(days=test_days)
        
        # GAP_DAYS: Minimum gap between train and test to prevent leakage
        self.gap_days = 30
        
        # Adjusted train end (with gap)
        self.train_end_date = self.test_split_date - timedelta(days=self.gap_days)
        
        # TEST dates
        self.test_start_date = self.test_split_date
        self.test_end_date = self.training_end_date
    
    def validate(self):
        """Validate date configuration is sensible."""
        errors = []
        
        # Check we have enough training data
        train_days = (self.train_end_date - self.training_start_date).days
        if train_days < 180:
            errors.append(f"Insufficient training data: only {train_days} days (need 180+)")
        
        # Check we have enough test data
        test_days = (self.test_end_date - self.test_start_date).days
        if test_days < 30:
            errors.append(f"Insufficient test data: only {test_days} days (need 30+)")
        
        # Check dates are in correct order
        if self.training_start_date >= self.train_end_date:
            errors.append("training_start_date must be before train_end_date")
        
        if self.test_start_date >= self.test_end_date:
            errors.append("test_start_date must be before test_end_date")
        
        # Check snapshot isn't in the future
        if self.training_snapshot_date > datetime.now().date():
            errors.append("training_snapshot_date cannot be in the future")
        
        if errors:
            raise ValueError("Date configuration validation failed:\n" + "\n".join(errors))
        
        return True
    
    def print_summary(self):
        """Print date configuration summary."""
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║           DYNAMIC DATE CONFIGURATION                         ║
╠══════════════════════════════════════════════════════════════╣
║  Execution Date:        {self.execution_date.strftime('%Y-%m-%d'):>20}         ║
║  Training Snapshot:     {self.training_snapshot_date.strftime('%Y-%m-%d'):>20}         ║
║  Maturity Window:       {self.maturity_window_days:>20} days       ║
╠══════════════════════════════════════════════════════════════╣
║  TRAINING DATA                                               ║
║    Start:               {self.training_start_date.strftime('%Y-%m-%d'):>20}         ║
║    End:                 {self.train_end_date.strftime('%Y-%m-%d'):>20}         ║
║    Days:                {(self.train_end_date - self.training_start_date).days:>20}         ║
╠══════════════════════════════════════════════════════════════╣
║  GAP (Leakage Prevention): {self.gap_days:>10} days                     ║
╠══════════════════════════════════════════════════════════════╣
║  TEST DATA                                                   ║
║    Start:               {self.test_start_date.strftime('%Y-%m-%d'):>20}         ║
║    End:                 {self.test_end_date.strftime('%Y-%m-%d'):>20}         ║
║    Days:                {(self.test_end_date - self.test_start_date).days:>20}         ║
╚══════════════════════════════════════════════════════════════╝
        """)
    
    def to_dict(self):
        """Export configuration as dictionary for SQL templating."""
        return {
            'execution_date': self.execution_date.strftime('%Y-%m-%d'),
            'training_snapshot_date': self.training_snapshot_date.strftime('%Y-%m-%d'),
            'maturity_window_days': self.maturity_window_days,
            'training_start_date': self.training_start_date.strftime('%Y-%m-%d'),
            'training_end_date': self.training_end_date.strftime('%Y-%m-%d'),
            'train_end_date': self.train_end_date.strftime('%Y-%m-%d'),
            'test_split_date': self.test_split_date.strftime('%Y-%m-%d'),
            'test_start_date': self.test_start_date.strftime('%Y-%m-%d'),
            'test_end_date': self.test_end_date.strftime('%Y-%m-%d'),
            'gap_days': self.gap_days
        }


# VALIDATION GATE G0.0.1: Date Configuration
def validate_date_configuration():
    """
    Mandatory validation gate - must pass before any other phase executes.
    """
    config = DateConfiguration()
    config.validate()
    config.print_summary()
    
    # Store in environment or config file for other phases
    import json
    with open('date_config.json', 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    
    print("✅ G0.0.1 PASSED: Date configuration validated and saved")
    return config


if __name__ == "__main__":
    config = validate_date_configuration()
```

Add a validation gate table for Phase 0.0:

| Gate ID | Check | Pass Criteria | Action on Fail |
|---------|-------|---------------|----------------|
| G0.0.1 | Date Configuration Valid | All dates in correct order, sufficient data window | Fix date calculation logic |
| G0.0.2 | Training Data Recency | training_end_date within 90 days of execution | Update and re-run |
| G0.0.3 | Minimum Training Window | At least 180 days of training data | Adjust start date or wait for more data |
| G0.0.4 | Minimum Test Window | At least 30 days of test data | Adjust split ratio |

Then update ALL subsequent phases to import dates from this configuration rather than hardcoding them.


## CRITICAL ISSUE #2: DATA LEAKAGE FROM `end_date` FIELD

During model development, we discovered a critical data leakage issue that the plan doesn't warn about. Add this as a prominent warning section.

### The Problem We Discovered

We built a feature called `days_in_gap` that calculated days since an advisor left their last firm using the `end_date` field from employment records. This feature:
- Had IV = 0.478 (strongest predictor)
- Was #2 most important feature by SHAP
- Gave us 3.03x lift

**BUT IT WAS DATA LEAKAGE.**

Here's why: FINTRX **retrospectively backfills** the `end_date` when they learn about a new job:

```
Timeline:
Jan 1:   Advisor leaves Firm A (FINTRX doesn't know yet)
Jan 15:  Sales contacts advisor (end_date shows NULL - still "employed")
Feb 1:   Advisor joins Firm B, files Form U4
Feb 2:   FINTRX BACKFILLS Firm A's end_date to "Jan 1"

What our training data showed: end_date = Jan 1, days_in_gap = 14 ✓
What was available on Jan 15: end_date = NULL, days_in_gap = UNKNOWN ✗
```

The feature was essentially predicting "this person moved soon after contact" which is correlated with conversion but unknowable at prediction time.

### Add This Warning Section

Add a new section called "## ⚠️ CRITICAL DATA LEAKAGE WARNINGS" immediately after the BigQuery Contract section:

```markdown
## ⚠️ CRITICAL DATA LEAKAGE WARNINGS

### Forbidden: `end_date` from Employment Records

**NEVER use `end_date` from `contact_registered_employment_history` for ANY feature calculation.**

The `end_date` field is **retrospectively backfilled** by FINTRX when they learn about a new job. At inference time (when we contact the lead), this field typically shows NULL even if the advisor has already left.

**Forbidden patterns:**
```sql
-- ❌ FORBIDDEN: Uses backfilled end_date
DATEDIFF(contacted_date, end_date, DAY) as days_since_left

-- ❌ FORBIDDEN: Uses end_date for gap detection  
CASE WHEN end_date IS NOT NULL AND contacted_date > end_date 
     THEN 1 ELSE 0 END as is_in_gap

-- ❌ FORBIDDEN: Any calculation involving end_date timing
DATE_DIFF(contacted_date, end_date, DAY) as days_in_gap
```

**Safe patterns:**
```sql
-- ✅ SAFE: Uses start_date (filed immediately for payment)
DATE_DIFF(contacted_date, start_date, MONTH) as current_tenure_months

-- ✅ SAFE: Counts completed historical moves (end_date in distant past)
COUNTIF(end_date < DATE_SUB(contacted_date, INTERVAL 30 DAY)) as historical_moves

-- ✅ SAFE: Aggregate firm metrics (other people's movements)
firm_net_change_12mo  -- Based on arrivals/departures of OTHER advisors
```

### Safe vs. Unsafe Data Fields

| Field | Safety | Reasoning |
|-------|--------|-----------|
| `start_date` | ✅ SAFE | Filed immediately via Form U4 (required for payment) |
| `end_date` | ❌ UNSAFE | Retrospectively backfilled when new job detected |
| Aggregate firm metrics | ✅ SAFE | Based on other advisors' historical movements |
| `*_current` table values | ❌ UNSAFE | Contains today's state, not state at contact time |

### The Leakage Lesson

Standard PIT (Point-in-Time) audit queries will NOT catch this type of leakage. The `days_in_gap` feature passed all technical PIT checks because it was calculated from "historical" data. The leak was only discovered through **domain knowledge review** of how FINTRX actually updates their records.

**New Validation Requirement:** Before using any employment-related feature, document:
1. Which date fields it uses
2. When those fields are populated by FINTRX
3. Whether the field could be retrospectively updated
```


## CRITICAL ISSUE #3: MISSING ENGINEERED FEATURES

The deployed model uses 3 engineered features that were developed AFTER the original plan was written. Add these to the feature engineering section.

### Add These Features to Phase 1

```python
# ENGINEERED FEATURES (Calculated at Runtime)
# These features are NOT stored in BigQuery - they are calculated by LeadScorerV2 at scoring time

# Feature 12: flight_risk_score
# The "Golden Signal" - Mobile Person + Bleeding Firm
flight_risk_score = pit_moves_3yr * max(-firm_net_change_12mo, 0)
"""
Purpose: Multiplicative signal combining advisor mobility with firm instability.
Neither signal alone is highly predictive, but the combination is powerful.

Leakage Audit: ✅ SAFE
- pit_moves_3yr = historical moves (>30 days ago)
- firm_net_change_12mo = aggregate of OTHER people's movements
- Neither uses the lead's future behavior

Business Insight: "Mobile people at bleeding firms are 2x more likely to convert"
"""

# Feature 13: pit_restlessness_ratio
# The "Itch Cycle" Detector
def calculate_restlessness_ratio(current_tenure, industry_tenure, num_prior_firms):
    if num_prior_firms > 0 and industry_tenure > current_tenure:
        avg_prior_tenure = (industry_tenure - current_tenure) / num_prior_firms
        return current_tenure / max(avg_prior_tenure, 1)
    return 0.0
"""
Purpose: Detects advisors who have stayed longer than their historical "itch cycle".
Ratio > 1.0 means they're past their typical tenure and may be "due" to move.

Leakage Audit: ✅ SAFE
- Uses start_date only (filed immediately for payment)
- Does NOT use end_date (retrospectively backfilled)
"""

# Feature 14: is_fresh_start
# The "New Hire" Flag
is_fresh_start = 1 if current_firm_tenure_months < 12 else 0
"""
Purpose: Binary flag for advisors less than 12 months at current firm.
New hires may still be evaluating their situation.

Leakage Audit: ✅ SAFE
- Derived from start_date (same safety as pit_restlessness_ratio)
"""
```

### Update Feature Count

The model uses **14 features total**: 11 base features stored in BigQuery + 3 engineered features calculated at runtime.

### Add Feature Engineering Validation Gate

| Gate ID | Check | Pass Criteria | Action on Fail |
|---------|-------|---------------|----------------|
| G1.X.1 | Engineered Features Safe | All 3 engineered features pass leakage audit | Review feature definitions |
| G1.X.2 | No end_date Usage | Zero features use end_date for timing | Remove offending features |
| G1.X.3 | Runtime Calculation | LeadScorerV2 correctly calculates engineered features | Fix inference pipeline |


## CRITICAL ISSUE #4: ADD TEMPORAL BACKTEST PHASE

The original plan has no temporal backtest. Add a new **Phase 8: Temporal Backtest Validation** after Phase 7.

```markdown
## Phase 8: Temporal Backtest Validation ("Time Machine Test")

### Purpose

The temporal backtest is the ultimate validation: **simulate what would have happened if we deployed the model in the past.** This tests whether the model truly generalizes to future unseen data.

### Unit 8.1: Temporal Backtest Execution

#### Methodology

1. Pick a historical "deployment date" (e.g., 6 months before current date)
2. Train using ONLY data available before that date
3. Predict on data AFTER that date
4. Compare predictions to actual outcomes

This is deliberately harsh:
- Training data is limited (simulates early deployment)
- Test data is large (simulates production volume)
- Market conditions may differ between periods

#### Code Snippet

```python
# temporal_backtest.py
"""
Phase 8.1: Temporal Backtest Validation
Simulates historical deployment to validate model generalization
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score
from typing import Tuple

class TemporalBacktester:
    def __init__(self, 
                 backtest_deployment_date: str,
                 date_config: dict):
        """
        Initialize temporal backtester.
        
        Args:
            backtest_deployment_date: Simulated deployment date (YYYY-MM-DD)
            date_config: Date configuration from Phase 0.0
        """
        self.deployment_date = datetime.strptime(backtest_deployment_date, '%Y-%m-%d').date()
        self.date_config = date_config
        self.maturity_days = date_config['maturity_window_days']
    
    def create_backtest_splits(self, 
                               features_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create train/test splits as if deploying on backtest_deployment_date.
        
        Train: All data BEFORE deployment_date - maturity_window
        Test: All data AFTER deployment_date (with sufficient maturity)
        """
        # Training cutoff: deployment date minus maturity window
        train_cutoff = self.deployment_date - timedelta(days=self.maturity_days)
        
        # Test starts at deployment date, ends at maturity window before "now"
        test_start = self.deployment_date
        test_end = datetime.strptime(self.date_config['training_end_date'], '%Y-%m-%d').date()
        
        # Split data
        train_mask = features_df['contacted_date'] < train_cutoff
        test_mask = (features_df['contacted_date'] >= test_start) & \
                    (features_df['contacted_date'] <= test_end)
        
        train_df = features_df[train_mask].copy()
        test_df = features_df[test_mask].copy()
        
        print(f"""
        TEMPORAL BACKTEST SPLITS
        ========================
        Simulated Deployment Date: {self.deployment_date}
        
        TRAIN (Pre-deployment):
          Date Range: {train_df['contacted_date'].min()} to {train_df['contacted_date'].max()}
          Samples: {len(train_df):,}
          Positive Rate: {train_df['target'].mean()*100:.2f}%
        
        TEST (Post-deployment):
          Date Range: {test_df['contacted_date'].min()} to {test_df['contacted_date'].max()}
          Samples: {len(test_df):,}
          Positive Rate: {test_df['target'].mean()*100:.2f}%
        
        Train:Test Ratio: 1:{len(test_df)/len(train_df):.1f}
        """)
        
        return train_df, test_df
    
    def run_backtest(self, 
                     model,
                     train_df: pd.DataFrame,
                     test_df: pd.DataFrame,
                     feature_cols: list) -> dict:
        """
        Run the temporal backtest.
        """
        # Train model on historical data only
        X_train = train_df[feature_cols]
        y_train = train_df['target']
        
        model.fit(X_train, y_train)
        
        # Predict on future data
        X_test = test_df[feature_cols]
        y_test = test_df['target']
        
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Calculate metrics
        auc = roc_auc_score(y_test, y_pred_proba)
        
        # Calculate top decile lift
        test_df_scored = test_df.copy()
        test_df_scored['score'] = y_pred_proba
        test_df_scored = test_df_scored.sort_values('score', ascending=False)
        
        n_decile = len(test_df_scored) // 10
        top_decile = test_df_scored.head(n_decile)
        
        baseline_rate = y_test.mean()
        top_decile_rate = top_decile['target'].mean()
        lift = top_decile_rate / baseline_rate if baseline_rate > 0 else 0
        
        results = {
            'deployment_date': str(self.deployment_date),
            'train_samples': len(train_df),
            'test_samples': len(test_df),
            'train_positive_rate': y_train.mean(),
            'test_positive_rate': y_test.mean(),
            'test_auc': auc,
            'baseline_conversion': baseline_rate,
            'top_decile_conversion': top_decile_rate,
            'top_decile_lift': lift
        }
        
        return results
    
    def validate_results(self, results: dict) -> bool:
        """
        Validate backtest results meet minimum thresholds.
        """
        # Minimum thresholds for temporal backtest
        MIN_LIFT = 1.5  # At least 1.5x lift in harsh conditions
        MIN_AUC = 0.55  # Better than random
        
        passed = True
        
        if results['top_decile_lift'] < MIN_LIFT:
            print(f"⚠️ WARNING: Top decile lift ({results['top_decile_lift']:.2f}x) below threshold ({MIN_LIFT}x)")
            passed = False
        else:
            print(f"✅ Top decile lift: {results['top_decile_lift']:.2f}x (threshold: {MIN_LIFT}x)")
        
        if results['test_auc'] < MIN_AUC:
            print(f"⚠️ WARNING: AUC ({results['test_auc']:.3f}) below threshold ({MIN_AUC})")
            passed = False
        else:
            print(f"✅ AUC: {results['test_auc']:.3f} (threshold: {MIN_AUC})")
        
        return passed


# Run temporal backtest at multiple deployment dates
def run_multi_period_backtest(features_df, model, feature_cols, date_config):
    """
    Run backtests at multiple simulated deployment dates.
    """
    # Test at 3 deployment dates: 6mo, 9mo, 12mo ago
    deployment_dates = []
    today = datetime.now().date()
    
    for months_ago in [6, 9, 12]:
        deploy_date = today - timedelta(days=months_ago * 30)
        # Ensure deploy date is after training start
        if deploy_date > datetime.strptime(date_config['training_start_date'], '%Y-%m-%d').date():
            deployment_dates.append(deploy_date.strftime('%Y-%m-%d'))
    
    all_results = []
    for deploy_date in deployment_dates:
        print(f"\n{'='*60}")
        print(f"BACKTEST: Simulated deployment on {deploy_date}")
        print('='*60)
        
        backtester = TemporalBacktester(deploy_date, date_config)
        train_df, test_df = backtester.create_backtest_splits(features_df)
        
        if len(train_df) < 500 or len(test_df) < 100:
            print(f"Skipping {deploy_date}: insufficient data")
            continue
        
        results = backtester.run_backtest(model, train_df, test_df, feature_cols)
        backtester.validate_results(results)
        all_results.append(results)
    
    return pd.DataFrame(all_results)
```

#### Validation Gates

| Gate ID | Check | Pass Criteria | Action on Fail |
|---------|-------|---------------|----------------|
| G8.1.1 | Temporal Lift | Top decile lift ≥ 1.5x on ALL backtest periods | Investigate feature drift or data issues |
| G8.1.2 | Temporal AUC | AUC ≥ 0.55 on ALL backtest periods | Model may not generalize |
| G8.1.3 | Consistent Performance | Lift variance across periods < 0.5x | Model may be period-dependent |
| G8.1.4 | Data Sufficiency | ≥ 500 train, ≥ 100 test for each backtest | Adjust deployment dates |


### Unit 8.2: Backtest Interpretation Guide

#### Expected Results

| Scenario | Expected Lift | Interpretation |
|----------|---------------|----------------|
| Optimistic | 2.5x+ | Ideal conditions, high confidence |
| Realistic | 1.9-2.2x | Normal production expectations |
| Conservative | 1.5-1.8x | Tough market or limited data |
| Concerning | < 1.5x | Model may not generalize; investigate |

#### Why Backtest Lift Is Often Lower Than Primary Test

1. **Data Starvation:** Less training data in historical simulation
2. **Market Shifts:** Conversion patterns may change over time
3. **Harsh Test Ratio:** Often 1:5 or 1:7 train:test ratio

A model that achieves 2.6x lift on primary test and 1.9x on temporal backtest is **well-validated** - the backtest confirms it works under realistic constraints.
```


## CRITICAL ISSUE #5: UPDATE VALIDATION GATES SUMMARY

Add a comprehensive validation gate summary at the end of the document that includes ALL gates across ALL phases, organized by criticality.

```markdown
## Comprehensive Validation Gate Summary

### 🔴 BLOCKING Gates (Must Pass to Continue)

| Phase | Gate ID | Check | Pass Criteria |
|-------|---------|-------|---------------|
| 0.0 | G0.0.1 | Date Configuration | All dates valid and in correct order |
| 0.0 | G0.0.2 | Training Data Recency | Training end within 90 days of execution |
| 1.1 | G1.1.1 | Virtual Snapshot Integrity | 100% leads have valid rep state |
| 1.1 | G1.1.9 | PIT Integrity | Zero features use future data |
| 1.X | G1.X.2 | No end_date Usage | Zero features use end_date for timing |
| 3.1 | G3.1.1 | VIF Check | All VIF < 10 |
| 4.1 | G4.1.1 | Model Trains | No errors during training |
| 5.1 | G5.1.1 | Top Decile Lift | Primary test lift ≥ 1.9x |
| 8.1 | G8.1.1 | Temporal Lift | Backtest lift ≥ 1.5x |

### 🟡 WARNING Gates (Review Required)

| Phase | Gate ID | Check | Pass Criteria |
|-------|---------|-------|---------------|
| 1.1 | G1.1.7 | Feature Coverage | ≥ 80% non-null for key features |
| 3.2 | G3.2.1 | Suspicious IV | No features with IV > 0.5 |
| 5.1 | G5.1.2 | AUC-PR | AUC-PR > baseline (positive rate) |
| 6.1 | G6.1.1 | Calibration | Brier Score < 0.05 |

### 🟢 INFORMATIONAL Gates (Log and Continue)

| Phase | Gate ID | Check | Expected |
|-------|---------|-------|----------|
| 0.1 | G0.1.1 | Data Availability | All source tables accessible |
| 1.1 | G1.1.8 | Positive Rate | 2-6% in feature table |
| 7.1 | G7.1.1 | Scoring Complete | All eligible leads scored |
```


## ADDITIONAL UPDATES

### Update 1: Fix the "Last Updated" footer
Change `*Last Updated: 2024-01-XX*` to use dynamic date or remove it.

### Update 2: Add Model Versioning Standard
Add a section on model version naming:
```
Model Version Format: v{major}-{type}-{YYYYMMDD}-{hash}
Example: v2-boosted-20251221-b796831a

Components:
- major: Increment on breaking changes
- type: Model type (baseline, boosted, etc.)
- YYYYMMDD: Training date
- hash: First 8 chars of git commit or random UUID
```

### Update 3: Add Monitoring Section
Add a brief section on production monitoring after Phase 7:
- Track actual conversion rates by score bucket monthly
- Alert if top decile lift drops below 1.5x
- Retrain trigger: 90 days since last training OR lift degradation

### Update 4: Reference the Handoff Documentation
Add a note that comprehensive handoff documentation exists at:
`Lead_Scoring_Model_Technical_Documentation.md`


## EXECUTION INSTRUCTIONS

1. Read the entire existing plan first
2. Make ALL the changes described above
3. Ensure the dynamic date configuration is in Phase 0.0 (before Phase 0)
4. Add the data leakage warning section prominently (right after BigQuery Contract)
5. Add the 3 engineered features to the feature engineering section
6. Add Phase 8 (Temporal Backtest) after Phase 7
7. Update the validation gates summary
8. Remove or parameterize ALL hardcoded 2024 dates
9. Update the "Last Updated" date to current
10. Verify the document is internally consistent

When complete, the plan should be executable at ANY future date without requiring manual date updates.
```

---

## How to Use This Prompt

1. Open Cursor.ai
2. Open the file `C:\Users\russe\Documents\Lead Scoring\leadscoring_plan.md`
3. Open Cursor's AI chat (Cmd/Ctrl + L)
4. Paste the entire prompt above
5. Let Cursor make the changes
6. Review the diff carefully before accepting

The updated plan will:
- Calculate all dates dynamically based on execution date
- Include critical warnings about data leakage from `end_date`
- Include all 14 features (11 base + 3 engineered)
- Include temporal backtest validation (Phase 8)
- Have a comprehensive validation gate summary
- Be executable at any future date without modification
