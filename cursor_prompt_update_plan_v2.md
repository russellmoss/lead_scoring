# Cursor.ai Prompt: Update Lead Scoring Agentic Plan (v2 - With Data Assessment)

## Target File
`C:\Users\russe\Documents\Lead Scoring\leadscoring_plan.md`

---

## Context for Cursor

I ran data assessment queries on December 21, 2025 and discovered critical information that must be incorporated into the lead scoring agentic plan. The original plan has hardcoded 2024 dates and is missing important lessons learned.

### Data Assessment Results (December 21, 2025)

**Firm_historicals Coverage:**
- Earliest snapshot: 2024-01-01
- Latest snapshot: 2025-11-01
- Total months available: 23 (Jan 2024 - Nov 2025)
- ⚠️ December 2025 firm data is NOT YET AVAILABLE

**Salesforce Leads:**
- 2024: 18,337 contacted leads, 726 MQLs (3.96% conversion)
- 2025: 38,645 contacted leads, 1,687 MQLs (4.37% conversion)
- Total available: 56,982 leads with 2,413 MQLs
- Most recent contact: December 19, 2025 (2 days ago)

**CRD Match Rate:** 95.72% (50,322 of 52,574 leads match FINTRX)

**Employment History:** 2.2M records covering 456,647 unique advisors (dates 1942-present)

**Critical Finding:** The original plan only trained on ~8,000 leads from 2024, missing 38,645 leads from 2025 - we have 5.5x more usable data than we used!

---

## Prompt for Cursor.ai

```
I need you to comprehensively update my lead scoring agentic plan at C:\Users\russe\Documents\Lead Scoring\leadscoring_plan.md

This plan was originally written in late 2024 and executed, but we discovered several critical issues. I've run a data assessment on December 21, 2025 that reveals important constraints.

## DATA ASSESSMENT FINDINGS TO INCORPORATE

### Finding 1: Firm_historicals Date Range
The Firm_historicals table has these constraints:
- **Starts:** January 2024
- **Ends:** November 2025 (as of Dec 21, 2025)
- **December 2025 data is NOT available yet**

This means:
- Training data floor: February 2024 (need Jan 2024 for prior month comparison)
- For December 2025 leads, we must use November 2025 firm data (last known value)
- The plan must handle this "firm data lag" gracefully

### Finding 2: Massive 2025 Data Availability
We have MUCH more 2025 data than 2024:
```
2024: 18,337 leads, 726 MQLs (3.96%)
2025: 38,645 leads, 1,687 MQLs (4.37%)
```

The original plan's hardcoded dates caused us to miss 38,645 leads and 1,687 MQLs from 2025!

### Finding 3: Monthly Lead Volumes (for reference)
2025 monthly breakdown:
- Jan: 2,522 leads, 131 MQLs (5.19%)
- Feb: 2,043 leads, 128 MQLs (6.27%)
- Mar: 1,928 leads, 89 MQLs (4.62%)
- Apr: 2,714 leads, 144 MQLs (5.31%)
- May: 2,626 leads, 117 MQLs (4.46%)
- Jun: 1,711 leads, 84 MQLs (4.91%)
- Jul: 2,496 leads, 116 MQLs (4.65%)
- Aug: 3,981 leads, 159 MQLs (3.99%)
- Sep: 3,549 leads, 189 MQLs (5.33%)
- Oct: 5,436 leads, 251 MQLs (4.62%)
- Nov: 4,718 leads, 150 MQLs (3.18%) ⚠️ Some may not be matured
- Dec: 4,921 leads, 129 MQLs (2.62%) ⚠️ Only 2 days old - NOT matured

### Finding 4: Right-Censoring Requirements
- December 2025 leads are only 2 days old - CANNOT be used for training
- November 2025 leads are 20-50 days old - some may not have full 30-day maturity
- October 2025 and earlier have full maturity

### Finding 5: Employment History Data Quality
- Contains some future dates (up to 2029) - likely data entry errors
- Must filter: `start_date <= contacted_date` to prevent issues


## CRITICAL ISSUE #1: HARDCODED DATES

The plan has hardcoded 2024 dates that caused us to miss a full year of data. Find and fix ALL instances:

1. `analysis_date: str = "2024-12-31"` in class constructors
2. `TRAINING_SNAPSHOT_DATE = "2024-12-31"`
3. `contacted_date >= '2024-02-01'` training floor
4. `contacted_date < '2024-10-01'` training ceiling
5. `contacted_date < '2024-08-01'` train/test split
6. Any other hardcoded year references

### Replace with: Dynamic Date Configuration (Phase 0.0)

Add this as the VERY FIRST phase, before Phase 0:

```python
# =============================================================================
# PHASE 0.0: DYNAMIC DATE CONFIGURATION (MANDATORY FIRST STEP)
# =============================================================================
"""
This module MUST execute first. All downstream phases import dates from here.
NEVER hardcode dates in other phases - always reference these variables.

Based on data assessment from December 21, 2025:
- Firm_historicals: Jan 2024 - Nov 2025 (23 months)
- Salesforce Leads: 56,982 total (18,337 in 2024, 38,645 in 2025)
- CRD Match Rate: 95.72%
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class DateConfiguration:
    """
    Central date configuration for the entire pipeline.
    All dates are calculated relative to execution date.
    
    Key Constraints (from data assessment):
    - Firm_historicals starts Jan 2024, so training floor is Feb 2024
    - Firm_historicals has ~1 month lag (Dec data not available in Dec)
    - 30-day maturity window required for conversion observation
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
        
        # FIRM_HISTORICALS_LAG: Firm data is typically 1 month behind
        # If we're in Dec 2025, latest firm data is Nov 2025
        self.firm_data_lag_months = 1
        
        # TRAINING_SNAPSHOT_DATE: End of last month with firm data
        first_of_current_month = self.execution_date.replace(day=1)
        last_month_end = first_of_current_month - timedelta(days=1)
        # Go back one more month for firm data lag
        self.training_snapshot_date = (last_month_end.replace(day=1) - timedelta(days=1))
        
        # MATURITY_WINDOW: Days to wait for conversion outcome
        self.maturity_window_days = 30
        
        # TRAINING_END_DATE: Latest contacted_date we can use
        # Must be maturity_window before snapshot to observe outcomes
        self.training_end_date = self.training_snapshot_date - timedelta(days=self.maturity_window_days)
        
        # TRAINING_START_DATE: Earliest contacted_date we can use
        # Firm_historicals starts Jan 2024, need Feb 2024 for prior month comparison
        self.training_start_date = datetime(2024, 2, 1).date()
        
        # Ensure training_end_date is a date object
        if hasattr(self.training_end_date, 'date'):
            self.training_end_date = self.training_end_date.date()
        if hasattr(self.training_snapshot_date, 'date'):
            self.training_snapshot_date = self.training_snapshot_date.date()
        
        # TEST_SPLIT_DATE: Where to split train vs test
        # Use approximately 80/20 split, with test being most recent 60 days
        total_days = (self.training_end_date - self.training_start_date).days
        test_days = min(60, int(total_days * 0.15))  # 15% or 60 days, whichever is smaller
        self.test_split_date = self.training_end_date - timedelta(days=test_days)
        
        # GAP_DAYS: Minimum gap between train and test to prevent leakage
        self.gap_days = 30
        
        # Adjusted train end (with gap before test)
        self.train_end_date = self.test_split_date - timedelta(days=self.gap_days)
        
        # TEST dates
        self.test_start_date = self.test_split_date
        self.test_end_date = self.training_end_date
        
        # LATEST_FIRM_SNAPSHOT: For scoring new leads without current month data
        self.latest_firm_snapshot_date = self.training_snapshot_date.replace(day=1)
    
    def validate(self):
        """Validate date configuration is sensible."""
        errors = []
        
        # Check we have enough training data (should be 500+ days with 2024+2025)
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
        
        # Check training start is after Firm_historicals start
        firm_data_start = datetime(2024, 1, 1).date()
        if self.training_start_date < firm_data_start:
            errors.append(f"training_start_date ({self.training_start_date}) is before Firm_historicals start ({firm_data_start})")
        
        if errors:
            raise ValueError("Date configuration validation failed:\n" + "\n".join(errors))
        
        return True
    
    def print_summary(self):
        """Print date configuration summary."""
        train_days = (self.train_end_date - self.training_start_date).days
        test_days = (self.test_end_date - self.test_start_date).days
        
        print(f"""
╔══════════════════════════════════════════════════════════════════╗
║           DYNAMIC DATE CONFIGURATION (v2)                        ║
║           Based on Data Assessment: Dec 21, 2025                 ║
╠══════════════════════════════════════════════════════════════════╣
║  Execution Date:           {self.execution_date.strftime('%Y-%m-%d'):>20}              ║
║  Training Snapshot:        {self.training_snapshot_date.strftime('%Y-%m-%d'):>20}              ║
║  Latest Firm Data:         {self.latest_firm_snapshot_date.strftime('%Y-%m-%d'):>20}              ║
║  Maturity Window:          {self.maturity_window_days:>20} days            ║
╠══════════════════════════════════════════════════════════════════╣
║  DATA CONSTRAINTS (from assessment)                              ║
║    Firm_historicals:       Jan 2024 - Nov 2025 (23 months)       ║
║    Firm data lag:          ~1 month                              ║
║    Total leads available:  56,982                                ║
║    Total MQLs available:   2,413                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  TRAINING DATA                                                   ║
║    Start:                  {self.training_start_date.strftime('%Y-%m-%d'):>20}              ║
║    End:                    {self.train_end_date.strftime('%Y-%m-%d'):>20}              ║
║    Days:                   {train_days:>20}              ║
╠══════════════════════════════════════════════════════════════════╣
║  GAP (Leakage Prevention): {self.gap_days:>10} days                          ║
╠══════════════════════════════════════════════════════════════════╣
║  TEST DATA                                                       ║
║    Start:                  {self.test_start_date.strftime('%Y-%m-%d'):>20}              ║
║    End:                    {self.test_end_date.strftime('%Y-%m-%d'):>20}              ║
║    Days:                   {test_days:>20}              ║
╚══════════════════════════════════════════════════════════════════╝
        """)
    
    def to_dict(self):
        """Export configuration as dictionary for SQL templating."""
        return {
            'execution_date': self.execution_date.strftime('%Y-%m-%d'),
            'training_snapshot_date': self.training_snapshot_date.strftime('%Y-%m-%d'),
            'latest_firm_snapshot_date': self.latest_firm_snapshot_date.strftime('%Y-%m-%d'),
            'maturity_window_days': self.maturity_window_days,
            'training_start_date': self.training_start_date.strftime('%Y-%m-%d'),
            'training_end_date': self.training_end_date.strftime('%Y-%m-%d'),
            'train_end_date': self.train_end_date.strftime('%Y-%m-%d'),
            'test_split_date': self.test_split_date.strftime('%Y-%m-%d'),
            'test_start_date': self.test_start_date.strftime('%Y-%m-%d'),
            'test_end_date': self.test_end_date.strftime('%Y-%m-%d'),
            'gap_days': self.gap_days,
            'firm_data_lag_months': self.firm_data_lag_months
        }
    
    def get_sql_parameters(self):
        """Get parameters formatted for SQL queries."""
        d = self.to_dict()
        return {
            'TRAINING_START': d['training_start_date'],
            'TRAINING_END': d['training_end_date'],
            'TRAIN_END': d['train_end_date'],
            'TEST_START': d['test_start_date'],
            'TEST_END': d['test_end_date'],
            'SNAPSHOT_DATE': d['training_snapshot_date'],
            'MATURITY_DAYS': d['maturity_window_days']
        }


# VALIDATION GATE G0.0.1: Date Configuration
def validate_date_configuration():
    """
    Mandatory validation gate - must pass before any other phase executes.
    """
    config = DateConfiguration()
    config.validate()
    config.print_summary()
    
    # Store configuration for other phases
    import json
    with open('date_config.json', 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    
    print("✅ G0.0.1 PASSED: Date configuration validated and saved to date_config.json")
    return config


# Helper function to load config in other phases
def load_date_configuration():
    """Load date configuration from saved file."""
    import json
    with open('date_config.json', 'r') as f:
        config_dict = json.load(f)
    return config_dict


if __name__ == "__main__":
    config = validate_date_configuration()
```

Add validation gates for Phase 0.0:

| Gate ID | Check | Pass Criteria | Action on Fail |
|---------|-------|---------------|----------------|
| G0.0.1 | Date Configuration Valid | All dates in correct order, sufficient data window | Fix date calculation logic |
| G0.0.2 | Training Data Recency | training_end_date within 90 days of execution | Update and re-run |
| G0.0.3 | Minimum Training Window | At least 180 days of training data | Adjust start date or wait for more data |
| G0.0.4 | Minimum Test Window | At least 30 days of test data | Adjust split ratio |
| G0.0.5 | Firm Data Available | training_end_date has corresponding Firm_historicals | Check Firm_historicals coverage |


## CRITICAL ISSUE #2: FIRM DATA LAG HANDLING

Add a new section explaining how to handle the firm data lag. The Firm_historicals table is typically 1 month behind (e.g., in December, latest data is November).

Add this to the BigQuery Contract section:

```markdown
### Firm Data Lag Handling

**Constraint:** Firm_historicals data has approximately 1 month lag. When executing in month M, the latest available firm snapshot is typically month M-1.

**Implications:**
1. Leads contacted in the current month cannot use current-month firm data
2. Must use "last known value" approach: use most recent available firm snapshot
3. Training data ceiling must account for this lag

**SQL Pattern for Firm Join with Lag Tolerance:**
```sql
-- Join to Firm_historicals with fallback to most recent available
WITH firm_snapshot AS (
    SELECT 
        RIA_INVESTOR_CRD_ID as firm_crd,
        YEAR,
        MONTH,
        TOTAL_AUM,
        -- other firm metrics
        ROW_NUMBER() OVER (
            PARTITION BY RIA_INVESTOR_CRD_ID 
            ORDER BY YEAR DESC, MONTH DESC
        ) as recency_rank
    FROM `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals`
    WHERE DATE(YEAR, MONTH, 1) <= @SNAPSHOT_DATE
)
SELECT *
FROM firm_snapshot
WHERE recency_rank = 1  -- Most recent available
```

**Validation Gate:**
- G0.0.5: Verify Firm_historicals coverage for training date range
- Alert if > 5% of leads have no matching firm data
```


## CRITICAL ISSUE #3: DATA LEAKAGE FROM `end_date` FIELD

Add this as a prominent warning section immediately after the BigQuery Contract section:

```markdown
## ⚠️ CRITICAL DATA LEAKAGE WARNINGS

### Lesson Learned: The `days_in_gap` Disaster

During our initial model development, we built a feature called `days_in_gap` that appeared to be our strongest predictor:
- **Information Value:** 0.478 (highest of all features)
- **SHAP Importance:** #2 feature
- **Apparent Lift:** 3.03x

**But it was data leakage.**

The feature used `end_date` from employment records to calculate days since an advisor left their last firm. We discovered that FINTRX **retrospectively backfills** this field:

```
What actually happens:
────────────────────────────────────────────────────────────
Jan 1:   Advisor leaves Firm A (FINTRX doesn't know yet)
Jan 15:  Sales contacts advisor (end_date = NULL in FINTRX)
Feb 1:   Advisor joins Firm B, files Form U4
Feb 2:   FINTRX sees U4, BACKFILLS Firm A's end_date to "Jan 1"

In training data: end_date = Jan 1, days_in_gap = 14 days ✓
At inference time: end_date = NULL, days_in_gap = UNKNOWN ✗
```

When we removed this leaking feature, our lift dropped from 3.03x to 1.65x. We recovered to 2.62x through legitimate feature engineering.

### Forbidden: `end_date` from Employment Records

**NEVER use `end_date` from `contact_registered_employment_history` for ANY feature calculation.**

**Forbidden patterns:**
```sql
-- ❌ FORBIDDEN: Uses backfilled end_date
DATE_DIFF(contacted_date, end_date, DAY) as days_since_left

-- ❌ FORBIDDEN: Gap detection using end_date  
CASE WHEN end_date IS NOT NULL AND contacted_date > end_date 
     THEN 1 ELSE 0 END as is_in_gap

-- ❌ FORBIDDEN: Any timing calculation with end_date
```

**Safe patterns:**
```sql
-- ✅ SAFE: Uses start_date (filed immediately for payment)
DATE_DIFF(contacted_date, start_date, MONTH) as current_tenure_months

-- ✅ SAFE: Historical moves only (end_date > 30 days before contact)
COUNTIF(end_date < DATE_SUB(contacted_date, INTERVAL 30 DAY)) as historical_moves

-- ✅ SAFE: Aggregate firm metrics (other people's movements)
firm_net_change_12mo
```

### Safe vs. Unsafe Data Fields

| Field | Safety | Reasoning |
|-------|--------|-----------|
| `start_date` | ✅ SAFE | Filed immediately via Form U4 (required for payment) |
| `end_date` | ❌ UNSAFE | Retrospectively backfilled when new job detected |
| Aggregate firm metrics | ✅ SAFE | Based on other advisors' historical movements |
| `*_current` table values | ❌ UNSAFE | Contains today's state, not state at contact time |

### Employment History Data Quality Note

The data assessment revealed:
- Employment history contains dates from 1942 to 2029
- Future dates (2026+) are data entry errors
- **Always filter:** `start_date <= contacted_date`
```


## CRITICAL ISSUE #4: ADD THE 3 ENGINEERED FEATURES

The deployed model uses 3 engineered features developed after the original plan. Add these to Phase 1:

```python
# =============================================================================
# ENGINEERED FEATURES (Calculated at Runtime by LeadScorerV2)
# =============================================================================
# These 3 features are NOT stored in BigQuery. They are calculated from base
# features at scoring time. This ensures consistency between training and inference.

# Feature 12: flight_risk_score
# The "Golden Signal" - combines Mobile Person + Bleeding Firm
def calculate_flight_risk_score(pit_moves_3yr: float, firm_net_change_12mo: float) -> float:
    """
    Multiplicative interaction between advisor mobility and firm instability.
    
    Formula: pit_moves_3yr × max(-firm_net_change_12mo, 0)
    
    Interpretation:
    - pit_moves_3yr: How many times this advisor changed firms in 3 years
    - firm_net_change_12mo: Net advisor arrivals - departures at their firm
    - Negative firm_net_change means advisors are LEAVING (firm is "bleeding")
    - We multiply by -1 so higher = more bleeding
    
    Leakage Audit: ✅ SAFE
    - pit_moves_3yr counts moves that happened >30 days ago (historical)
    - firm_net_change_12mo measures OTHER people's movements, not the lead's future
    
    Business Insight:
    "Mobile advisors at bleeding firms are the golden cohort - 
     they're predisposed to move AND their firm is giving them reasons to leave."
    """
    bleeding_severity = max(-firm_net_change_12mo, 0)
    return pit_moves_3yr * bleeding_severity


# Feature 13: pit_restlessness_ratio
# The "Itch Cycle" Detector
def calculate_restlessness_ratio(
    current_firm_tenure_months: float,
    industry_tenure_months: float, 
    num_prior_firms: float
) -> float:
    """
    Detects advisors who have stayed longer than their historical pattern.
    
    Formula: current_tenure / avg_prior_tenure
    
    Interpretation:
    - Ratio < 1.0: Advisor is BELOW typical tenure (may stay longer)
    - Ratio = 1.0: Advisor is AT typical tenure (neutral)
    - Ratio > 1.0: Advisor is PAST typical tenure (may be "due" to move)
    
    Leakage Audit: ✅ SAFE
    - Uses start_date only (filed immediately for payment)
    - Does NOT use end_date (retrospectively backfilled)
    """
    if num_prior_firms > 0 and industry_tenure_months > current_firm_tenure_months:
        avg_prior_tenure = (industry_tenure_months - current_firm_tenure_months) / num_prior_firms
        if avg_prior_tenure > 0.1:  # Avoid division by tiny numbers
            return current_firm_tenure_months / avg_prior_tenure
    return 0.0


# Feature 14: is_fresh_start
# The "New Hire" Flag
def calculate_is_fresh_start(current_firm_tenure_months: float) -> int:
    """
    Binary flag for advisors with less than 12 months at current firm.
    
    Interpretation:
    - 1: New hire, still in "evaluation period", may be open to alternatives
    - 0: Established at firm
    
    Leakage Audit: ✅ SAFE
    - Derived from start_date (same safety as restlessness_ratio)
    """
    return 1 if current_firm_tenure_months < 12 else 0
```

Update the feature count: **14 features total** (11 base + 3 engineered)

Add validation gate:
| Gate ID | Check | Pass Criteria | Action on Fail |
|---------|-------|---------------|----------------|
| G1.X.1 | Engineered Features Safe | All 3 engineered features pass leakage audit | Review feature definitions |
| G1.X.2 | No end_date Usage | Zero features use end_date for timing | Remove offending features |
| G1.X.3 | Runtime Calculation Test | LeadScorerV2 correctly calculates all 3 | Fix inference pipeline |


## CRITICAL ISSUE #5: ADD PHASE 8 - TEMPORAL BACKTEST

Add a new Phase 8 after Phase 7 for temporal validation:

```markdown
## Phase 8: Temporal Backtest Validation ("Time Machine Test")

### Purpose

The temporal backtest simulates what would have happened if we deployed the model in the past. This is the ultimate test of whether the model generalizes to truly unseen future data.

### Unit 8.1: Multi-Period Backtest

#### Methodology

1. Pick historical "deployment dates" (6, 9, 12 months ago)
2. For each date: train on data BEFORE, predict data AFTER
3. Compare predictions to actual outcomes
4. Model must achieve ≥1.5x lift across ALL periods

#### Code Snippet

```python
# temporal_backtest.py
"""
Phase 8: Temporal Backtest Validation
Simulates historical deployment to validate generalization
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

class TemporalBacktester:
    def __init__(self, date_config: dict):
        self.date_config = date_config
        self.maturity_days = date_config['maturity_window_days']
        self.results = []
    
    def run_backtest_at_date(self, 
                              features_df: pd.DataFrame,
                              model,
                              feature_cols: list,
                              deployment_date: str) -> dict:
        """
        Simulate deploying model on a historical date.
        
        Args:
            features_df: Full feature dataset with 'contacted_date' and 'target'
            model: Untrained model instance (will be cloned and trained)
            feature_cols: List of feature column names
            deployment_date: Simulated deployment date (YYYY-MM-DD)
        """
        deploy_date = datetime.strptime(deployment_date, '%Y-%m-%d').date()
        
        # Training cutoff: deployment date minus maturity window
        train_cutoff = deploy_date - timedelta(days=self.maturity_days)
        
        # Split data
        features_df['contacted_date'] = pd.to_datetime(features_df['contacted_date']).dt.date
        
        train_mask = features_df['contacted_date'] < train_cutoff
        test_mask = (features_df['contacted_date'] >= deploy_date) & \
                    (features_df['contacted_date'] <= datetime.strptime(
                        self.date_config['test_end_date'], '%Y-%m-%d').date())
        
        train_df = features_df[train_mask].copy()
        test_df = features_df[test_mask].copy()
        
        if len(train_df) < 500 or len(test_df) < 100:
            return {'error': 'Insufficient data', 'deployment_date': deployment_date}
        
        # Train
        X_train = train_df[feature_cols]
        y_train = train_df['target']
        
        from sklearn.base import clone
        model_clone = clone(model)
        model_clone.fit(X_train, y_train)
        
        # Predict
        X_test = test_df[feature_cols]
        y_test = test_df['target']
        y_pred = model_clone.predict_proba(X_test)[:, 1]
        
        # Calculate lift
        test_df['score'] = y_pred
        test_df = test_df.sort_values('score', ascending=False)
        
        n_decile = len(test_df) // 10
        top_decile = test_df.head(n_decile)
        
        baseline_rate = y_test.mean()
        top_decile_rate = top_decile['target'].mean()
        lift = top_decile_rate / baseline_rate if baseline_rate > 0 else 0
        
        return {
            'deployment_date': deployment_date,
            'train_samples': len(train_df),
            'test_samples': len(test_df),
            'train_positive_rate': float(y_train.mean()),
            'test_positive_rate': float(y_test.mean()),
            'test_auc': float(roc_auc_score(y_test, y_pred)),
            'baseline_conversion': float(baseline_rate),
            'top_decile_conversion': float(top_decile_rate),
            'top_decile_lift': float(lift)
        }
    
    def run_multi_period_backtest(self, 
                                   features_df: pd.DataFrame,
                                   model,
                                   feature_cols: list,
                                   periods_months: list = [6, 9, 12]) -> pd.DataFrame:
        """Run backtests at multiple deployment dates."""
        
        today = datetime.now().date()
        training_start = datetime.strptime(
            self.date_config['training_start_date'], '%Y-%m-%d').date()
        
        results = []
        for months_ago in periods_months:
            deploy_date = today - timedelta(days=months_ago * 30)
            
            # Skip if deployment date is before training data starts
            if deploy_date <= training_start + timedelta(days=180):
                print(f"Skipping {months_ago}mo backtest: insufficient pre-deployment data")
                continue
            
            print(f"\n{'='*60}")
            print(f"BACKTEST: Simulated deployment {months_ago} months ago ({deploy_date})")
            print('='*60)
            
            result = self.run_backtest_at_date(
                features_df, model, feature_cols, deploy_date.strftime('%Y-%m-%d')
            )
            
            if 'error' not in result:
                results.append(result)
                
                # Validate
                if result['top_decile_lift'] >= 1.5:
                    print(f"✅ PASSED: Lift = {result['top_decile_lift']:.2f}x")
                else:
                    print(f"⚠️ WARNING: Lift = {result['top_decile_lift']:.2f}x (below 1.5x threshold)")
        
        return pd.DataFrame(results)


def validate_temporal_stability(results_df: pd.DataFrame) -> bool:
    """
    Validate that model performs consistently across time periods.
    
    Pass criteria:
    - All periods have lift ≥ 1.5x
    - Lift variance < 0.5x across periods
    """
    if len(results_df) == 0:
        print("❌ No backtest results to validate")
        return False
    
    min_lift = results_df['top_decile_lift'].min()
    max_lift = results_df['top_decile_lift'].max()
    variance = max_lift - min_lift
    
    passed = True
    
    if min_lift < 1.5:
        print(f"❌ G8.1.1 FAILED: Minimum lift ({min_lift:.2f}x) below 1.5x threshold")
        passed = False
    else:
        print(f"✅ G8.1.1 PASSED: All periods have lift ≥ 1.5x (min: {min_lift:.2f}x)")
    
    if variance > 0.5:
        print(f"⚠️ G8.1.3 WARNING: High lift variance ({variance:.2f}x) - model may be period-dependent")
    else:
        print(f"✅ G8.1.3 PASSED: Lift variance ({variance:.2f}x) within acceptable range")
    
    return passed
```

#### Validation Gates

| Gate ID | Check | Pass Criteria | Action on Fail |
|---------|-------|---------------|----------------|
| G8.1.1 | Temporal Lift | Top decile lift ≥ 1.5x on ALL backtest periods | Investigate feature drift |
| G8.1.2 | Temporal AUC | AUC ≥ 0.55 on ALL backtest periods | Model may not generalize |
| G8.1.3 | Consistent Performance | Lift variance across periods < 0.5x | Model may be period-dependent |

#### Expected Results

Based on our December 2024 deployment, we observed:
- Primary test lift: 2.62x
- Temporal backtest lift: 1.90x

The backtest lift is typically lower due to:
1. Less training data (simulated early deployment)
2. Market condition shifts
3. Harsh train:test ratios

A model achieving 2.6x on primary and 1.9x on temporal is well-validated.
```


## CRITICAL ISSUE #6: UPDATE VALIDATION GATES SUMMARY

Add a comprehensive validation gate summary organized by criticality:

```markdown
## Comprehensive Validation Gate Summary

### 🔴 BLOCKING Gates (Must Pass to Continue)

| Phase | Gate ID | Check | Pass Criteria |
|-------|---------|-------|---------------|
| 0.0 | G0.0.1 | Date Configuration | All dates valid and in correct order |
| 0.0 | G0.0.2 | Training Data Recency | Training end within 90 days of execution |
| 0.0 | G0.0.5 | Firm Data Coverage | Firm_historicals covers training date range |
| 1.1 | G1.1.1 | Virtual Snapshot Integrity | 100% leads have valid rep state |
| 1.1 | G1.1.9 | PIT Integrity | Zero features use future data |
| 1.X | G1.X.2 | No end_date Usage | Zero features use end_date for timing |
| 3.1 | G3.1.1 | VIF Check | All VIF < 10 |
| 4.1 | G4.1.1 | Model Trains | No errors during training |
| 5.1 | G5.1.1 | Top Decile Lift | Primary test lift ≥ 1.9x |
| 8.1 | G8.1.1 | Temporal Lift | Backtest lift ≥ 1.5x on all periods |

### 🟡 WARNING Gates (Review Required)

| Phase | Gate ID | Check | Pass Criteria |
|-------|---------|-------|---------------|
| 1.1 | G1.1.7 | Feature Coverage | ≥ 80% non-null for key features |
| 3.2 | G3.2.1 | Suspicious IV | No features with IV > 0.5 (leakage risk!) |
| 5.1 | G5.1.2 | AUC-PR | AUC-PR > baseline positive rate |
| 6.1 | G6.1.1 | Calibration | Brier Score < 0.05 |
| 8.1 | G8.1.3 | Temporal Consistency | Lift variance < 0.5x across periods |

### 🟢 INFORMATIONAL Gates (Log and Continue)

| Phase | Gate ID | Check | Expected |
|-------|---------|-------|----------|
| 0.1 | G0.1.1 | Data Availability | All source tables accessible |
| 1.1 | G1.1.8 | Positive Rate | 2-6% in feature table |
| 7.1 | G7.1.1 | Scoring Complete | All eligible leads scored |
```


## ADDITIONAL UPDATES

### Update 1: Add Data Assessment Query Section

Add a new section "Phase -1: Data Assessment" that contains the queries to run BEFORE executing the plan:

```markdown
## Phase -1: Pre-Flight Data Assessment (Run Before Plan Execution)

Before executing this plan, run these queries to validate data availability:

```sql
-- 1. Firm_historicals date range
SELECT 
    MIN(DATE(YEAR, MONTH, 1)) as earliest_snapshot,
    MAX(DATE(YEAR, MONTH, 1)) as latest_snapshot,
    COUNT(DISTINCT DATE(YEAR, MONTH, 1)) as total_months
FROM `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals`;

-- 2. Lead volumes by year
SELECT 
    EXTRACT(YEAR FROM stage_entered_contacting__c) as year,
    COUNT(*) as leads,
    COUNTIF(Stage_Entered_Call_Scheduled__c IS NOT NULL OR ConvertedDate IS NOT NULL) as mqls
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
GROUP BY 1 ORDER BY 1;

-- 3. Most recent lead
SELECT MAX(stage_entered_contacting__c) as most_recent,
       DATE_DIFF(CURRENT_DATE(), MAX(DATE(stage_entered_contacting__c)), DAY) as days_ago
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`;

-- 4. CRD match rate
WITH leads AS (
    SELECT DISTINCT SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` WHERE FA_CRD__c IS NOT NULL
),
fintrx AS (
    SELECT DISTINCT RIA_CONTACT_CRD_ID as crd FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
)
SELECT COUNT(DISTINCT l.crd) as total, 
       COUNT(DISTINCT CASE WHEN f.crd IS NOT NULL THEN l.crd END) as matched,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN f.crd IS NOT NULL THEN l.crd END) / COUNT(DISTINCT l.crd), 2) as match_pct
FROM leads l LEFT JOIN fintrx f ON l.crd = f.crd;
```

**Expected Results (as of Dec 2025):**
- Firm_historicals: Jan 2024 - Nov 2025
- Leads: 56,982 total (18K in 2024, 38K in 2025)
- MQLs: 2,413 total
- CRD match rate: ~95%
```


### Update 2: Fix the "Last Updated" footer

Change:
```
*Last Updated: 2024-01-XX*
```

To:
```
*Last Updated: [Dynamically generated at execution time]*
*Data Assessment Date: December 21, 2025*
*Plan Version: 2.0 (includes dynamic dates, leakage warnings, temporal backtest)*
```


### Update 3: Add Expected Training Data Size

Add a note about expected data volume based on assessment:

```markdown
### Expected Data Volumes (Based on Dec 2025 Assessment)

| Metric | 2024 Only (Old Plan) | 2024+2025 (New Plan) | Improvement |
|--------|----------------------|----------------------|-------------|
| Training Leads | ~8,000 | ~45,000 | 5.6x more |
| Training MQLs | ~300 | ~1,800 | 6x more |
| Test Leads | ~1,700 | ~9,000 | 5.3x more |
| Test MQLs | ~70 | ~400 | 5.7x more |

More training data generally improves:
- Feature learning robustness
- Rare pattern detection
- Model stability
- Temporal validation strength
```


## EXECUTION INSTRUCTIONS

1. Read the entire existing plan first
2. Add Phase -1 (Data Assessment) and Phase 0.0 (Date Configuration) at the start
3. Add the data leakage warning section prominently after BigQuery Contract
4. Add firm data lag handling to BigQuery Contract section
5. Add the 3 engineered features to Phase 1
6. Add Phase 8 (Temporal Backtest) after Phase 7
7. Update the validation gates summary
8. Replace ALL hardcoded 2024 dates with references to DateConfiguration
9. Update the footer and version information
10. Add expected data volumes based on assessment

When complete, the plan should:
- Calculate dates dynamically based on execution date
- Handle firm data lag gracefully
- Warn about end_date leakage
- Include all 14 features
- Validate with temporal backtesting
- Work correctly at any future execution date
```

---

## Summary of Key Changes

This updated prompt includes:

1. **Data Assessment Results** - All findings from the Dec 21, 2025 queries
2. **Firm Data Lag Handling** - New section for the 1-month lag in Firm_historicals
3. **Dynamic Date Configuration** - Updated to account for firm data lag
4. **Right-Censoring Logic** - Explicit handling of Nov/Dec 2025 maturity issues
5. **Expected Data Volumes** - Based on actual assessment numbers
6. **Phase -1 Pre-Flight Queries** - So future runs can validate data first
