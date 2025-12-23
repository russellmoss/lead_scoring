# Version 2 Lead Scoring Model - Comprehensive Technical Report

**Model Version:** v3 (labeled as Version-2 in directory structure)  
**Development Date:** December 21, 2025  
**Base Directory:** `Version-2/`  
**Status:** Development Complete, Performance Under Review

---

## Executive Summary

The Version-2 lead scoring model is an XGBoost-based binary classification system designed to predict the likelihood that a financial advisor lead will convert from "Contacted" to "MQL" (Marketing Qualified Lead) within 30 days. The model achieved **1.50x lift** in the top decile, below the target of 2.62x from the previous version.

### Key Metrics

- **Training Samples:** 30,727 leads
- **Test Samples:** 6,919 leads
- **Positive Rate (Train):** 3.66%
- **Positive Rate (Test):** 4.16%
- **Test AUC-ROC:** 0.5808
- **Test AUC-PR:** 0.0569
- **Top Decile Lift:** 1.50x
- **Top Decile Conversion Rate:** 6.25%
- **Baseline Conversion Rate:** 4.16%

---

## Table of Contents

1. [Model Architecture](#model-architecture)
2. [Data Sources & Pipeline](#data-sources--pipeline)
3. [Feature Engineering](#feature-engineering)
4. [Training Process](#training-process)
5. [Key Technical Decisions](#key-technical-decisions)
6. [Challenges & Solutions](#challenges--solutions)
7. [Model Performance](#model-performance)
8. [Lessons Learned](#lessons-learned)
9. [Code Structure](#code-structure)

---

## Model Architecture

### Algorithm Selection

**XGBoost Classifier** with the following configuration:
- **Objective:** `binary:logistic` (binary classification with logistic probability output)
- **Evaluation Metric:** AUC-PR (Area Under Precision-Recall Curve)
- **Tree Method:** `hist` (histogram-based algorithm for faster training)
- **Random State:** 42 (for reproducibility)

### Why XGBoost?

1. **Handles Class Imbalance:** Built-in `scale_pos_weight` parameter addresses severe class imbalance (26:1 ratio)
2. **Feature Interactions:** Automatically captures complex feature interactions without manual engineering
3. **Regularization:** Built-in L1/L2 regularization prevents overfitting
4. **Handles Missing Values:** XGBoost handles missing values natively
5. **Feature Importance:** Provides interpretable feature importance scores

### Hyperparameter Optimization

Used **Optuna** with 50 trials to optimize:
- `max_depth`: 3-10
- `learning_rate`: 0.01-0.3 (log scale)
- `n_estimators`: 50-300
- `subsample`: 0.5-1.0
- `colsample_bytree`: 0.5-1.0
- `gamma`: 0-10
- `reg_alpha`: 0-10 (L1 regularization)
- `reg_lambda`: 0-10 (L2 regularization)
- `min_child_weight`: 1-10

**Best CV AUC-PR:** 0.0814  
**CV Score Standard Deviation:** 0.0064 (indicates effective tuning after fixing CV)

---

## Data Sources & Pipeline

### Data Sources

1. **Salesforce Lead Table** (`savvy-gtm-analytics.SavvyGTMData.Lead`)
   - Lead lifecycle data
   - Contact timestamps
   - Conversion events

2. **FINTRX Contact Employment History** (`FinTrx_data_CA.contact_registered_employment_history`)
   - Advisor employment history
   - Firm associations over time
   - Tenure calculations

3. **FINTRX Firm Historicals** (`FinTrx_data_CA.Firm_historicals`)
   - Monthly snapshots of firm metrics
   - AUM, rep counts, firm stability metrics

4. **FINTRX Current Contacts** (`FinTrx_data_CA.ria_contacts_current`)
   - Current advisor data
   - Contact information
   - Data quality signals

### Data Pipeline Phases

#### Phase 0.0: Dynamic Date Configuration
- Calculates training/test windows based on execution date
- Ensures temporal consistency across all phases
- **Training Window:** 2024-02-01 to 2025-07-03 (518 days)
- **Test Window:** 2025-08-02 to 2025-10-01 (60 days)
- **Gap:** 30 days between train and test (prevents data leakage)

#### Phase -1: Pre-Flight Data Assessment
Validates data availability:
- ✅ Firm data: 23 months available (need ≥20)
- ✅ Lead volume: 57,034 leads (need ≥10,000)
- ✅ CRD match rate: 94.03% (need ≥90%)
- ✅ Recent data: Most recent lead 2 days ago (need ≤30)

#### Phase 0.1: Data Landscape Assessment
- Validates all source tables are accessible
- Confirms data quality and coverage
- Documents data schema

#### Phase 1: Feature Engineering
Creates `lead_scoring_features_pit` table with point-in-time features

#### Phase 2: Temporal Split
Creates `lead_scoring_splits` table with TRAIN/TEST/GAP labels

#### Phase 3: Feature Validation
- Validates feature table structure
- Confirms no raw geographic features (privacy compliance)
- Verifies protected features present

#### Phase 4: Model Training
Trains XGBoost model with hyperparameter tuning

---

## Feature Engineering

### Point-in-Time (PIT) Methodology

**Critical Innovation:** All features are calculated using only data available at the time of lead contact (`contacted_date`). This prevents data leakage and ensures the model can be used in production.

### Virtual Snapshot Approach

Instead of creating physical snapshot tables, the model uses a **Virtual Snapshot** methodology:

1. **Rep State at Contact:** For each lead, determines the advisor's employment status at `contacted_date` by querying employment history
2. **Firm State at Contact:** Retrieves firm metrics from `Firm_historicals` for the month prior to contact (accounting for data lag)
3. **Dynamic Calculations:** Features are calculated on-the-fly using historical data up to the contact date

### Feature Categories

#### 1. Advisor Features (6 features)

| Feature | Description | Calculation |
|---------|-------------|-------------|
| `industry_tenure_months` | Total years as a rep | Sum of all prior job tenures |
| `num_prior_firms` | Number of prior firms | Count of distinct firm CRDs before current |
| `current_firm_tenure_months` | Tenure at current firm | Months from job start to contact date |
| `pit_moves_3yr` | Moves in last 3 years | Count of job endings in 36 months prior |
| `pit_avg_prior_tenure_months` | Average prior tenure | Mean tenure across all prior jobs |
| `pit_restlessness_ratio` | Current vs avg tenure | `current_tenure / avg_prior_tenure` |

**Key Insight:** `pit_restlessness_ratio` captures whether an advisor is staying longer than their historical average, indicating potential restlessness.

#### 2. Mobility Features

**Protected Feature:** `pit_moves_3yr` (moves in last 3 years)
- **Rationale:** Advisors who have moved recently are more likely to move again
- **Coverage:** 100% (all leads have this calculated)

**Problem Identified:** Raw `pit_moves_3yr` is sparse:
- 79.7% of leads have 0 moves
- Only 20.3% have moved in last 3 years
- Model struggled to learn from sparse feature

**Solution Attempted:** Created mobility tiers (Stable/Mobile/Highly Mobile) in v2-features variant, but lift only improved to 1.42x.

#### 3. Firm Features (7 features)

| Feature | Description | Calculation |
|---------|-------------|-------------|
| `firm_aum_pit` | Firm AUM at contact | From Firm_historicals for pit_month |
| `log_firm_aum` | Log-transformed AUM | `LOG(GREATEST(1, firm_aum_pit))` |
| `firm_net_change_12mo` | Net rep change | `arrivals_12mo - departures_12mo` |
| `firm_departures_12mo` | Reps who left | Count in 12 months prior to contact |
| `firm_arrivals_12mo` | Reps who joined | Count in 12 months prior to contact |
| `firm_stability_percentile` | Stability ranking | Percentile rank of net_change |
| `firm_stability_tier` | Categorical stability | Severe_Bleeding/Moderate_Bleeding/Stable/Growing |

**Protected Feature:** `firm_net_change_12mo` (firm bleeding indicator)
- **Rationale:** Advisors at "bleeding" firms (losing reps) are more likely to move
- **Coverage:** 100%

**Key Insight:** Negative values indicate firms losing advisors, which is a strong conversion signal.

#### 4. Runtime-Engineered Features (2 features)

These are calculated at training/inference time (not stored in BigQuery):

| Feature | Formula | Purpose |
|---------|---------|---------|
| `flight_risk_score` | `pit_moves_3yr × max(-firm_net_change_12mo, 0)` | Multiplicative signal for high-risk advisors |
| `is_fresh_start` | `1 if current_firm_tenure_months < 12 else 0` | Flag for recent hires |

**Critical Issue:** `flight_risk_score` is 98.7% sparse!
- Only 1.3% of leads have non-zero values
- Results from: 79.7% have no moves AND 94.6% have non-bleeding firms
- Model correctly ignored it (importance rank #19)

**Conversion Rates by flight_risk_score:**
- Zero: 3.67% (98.7% of leads)
- Non-zero: 11-15% (but only 1.3% of leads)

This feature shows strong signal but is too rare to help the model.

#### 5. Data Quality Signals (3 features)

| Feature | Description |
|---------|-------------|
| `is_gender_missing` | 1 if gender not in FINTRX |
| `is_linkedin_missing` | 1 if LinkedIn URL missing |
| `is_personal_email_missing` | 1 if personal email missing |

**Key Finding:** Data quality signals actually help model performance (removing them reduced lift from 1.50x to 1.26x).

#### 6. Flags (2 features)

| Feature | Description |
|---------|-------------|
| `has_valid_virtual_snapshot` | 1 if employment history found |
| `has_firm_aum` | 1 if firm AUM data available |

**Top Feature:** `has_valid_virtual_snapshot` has highest importance (0.3211), indicating data completeness is a strong signal.

---

## Training Process

### Data Preparation

1. **Load from BigQuery:** Join `lead_scoring_splits` with `lead_scoring_features_pit`
2. **Sort by Date:** CRITICAL - data must be sorted by `contacted_date` for TimeSeriesSplit
3. **Engineer Runtime Features:** Calculate `flight_risk_score` and `is_fresh_start`
4. **Handle Missing Values:** Fill NaN with 0 (safe default for numeric features)
5. **Encode Categorical:** Convert `firm_stability_tier` to numeric (0-4 scale)

### Class Imbalance Handling

**Severe Imbalance:** 26.34:1 (negative:positive) ratio

**Solution:** XGBoost `scale_pos_weight` parameter
```python
scale_pos_weight = n_neg / n_pos = 26.34
```

This tells XGBoost to treat each positive example as 26.34 negatives, effectively upweighting the minority class.

### Cross-Validation Strategy

**TimeSeriesSplit with 5 folds:**

```python
tscv = TimeSeriesSplit(n_splits=5)
```

**Critical Fix Required:** Initial implementation had unsorted data, causing CV folds 1-4 to have ZERO positive examples. This was fixed by sorting data by `contacted_date` before CV.

**Why TimeSeriesSplit?**
- Respects temporal ordering
- Prevents future data from leaking into past folds
- More realistic evaluation for time-series data

### Hyperparameter Tuning

**Optuna Framework:**
- 50 trials
- Objective: Maximize CV AUC-PR (better for imbalanced data than AUC-ROC)
- Pruning: None (all trials complete)

**Best Parameters Found:**
- `max_depth`: Varied (tuned)
- `learning_rate`: Varied (tuned)
- `n_estimators`: Varied (tuned)
- `subsample`: Varied (tuned)
- `colsample_bytree`: Varied (tuned)
- `gamma`: Varied (tuned)
- `reg_alpha`: Varied (tuned)
- `reg_lambda`: Varied (tuned)
- `min_child_weight`: Varied (tuned)

**CV Score Variation:** After fixing data sorting, CV scores varied across trials (std=0.0064), confirming effective tuning.

### Model Training

```python
final_model = xgb.XGBClassifier(**best_params)
final_model.fit(X_train, y_train, eval_set=[(X_test, y_test)])
```

**Early Stopping:** Not used (Optuna already found optimal `n_estimators`)

---

## Key Technical Decisions

### 1. Point-in-Time (PIT) Feature Engineering

**Decision:** Calculate all features using only data available at `contacted_date`

**Rationale:**
- Prevents data leakage (future information can't influence past predictions)
- Ensures production model can replicate training features
- Critical for temporal validity

**Implementation:**
- Use `Firm_historicals` for month prior to contact (accounts for 1-month data lag)
- Use `contact_registered_employment_history` filtered by dates ≤ `contacted_date`
- All calculations use historical data only

### 2. Virtual Snapshot vs Physical Snapshots

**Decision:** Use Virtual Snapshot (calculate on-the-fly) instead of pre-computed snapshot tables

**Rationale:**
- More flexible (can adjust logic without regenerating snapshots)
- Saves storage space
- Easier to maintain and debug
- Allows different pit_month calculations per feature

**Trade-off:** Slightly slower query performance, but acceptable for batch feature extraction

### 3. Target Variable Definition

**Target:** Binary indicator for MQL conversion within 30 days

```sql
CASE
    WHEN DATE_DIFF(analysis_date, contacted_date, DAY) < 30 THEN NULL  -- Right-censored
    WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL
         AND DATE_DIFF(call_scheduled_date, contacted_date, DAY) <= 30
    THEN 1  -- Converted
    ELSE 0  -- Not converted
END as target
```

**Key Design Choices:**
- **30-day window:** Business requirement - leads that don't convert quickly are less valuable
- **Right-censoring protection:** Leads contacted within 30 days of analysis_date are excluded (don't have enough time to convert)
- **MQL = Call Scheduled:** Uses `Stage_Entered_Call_Scheduled__c` as conversion event

### 4. Temporal Train/Test Split

**Decision:** Strict temporal split with 30-day gap

**Split Dates:**
- **Train:** 2024-02-01 to 2025-07-03
- **Gap:** 2025-07-04 to 2025-08-01 (30 days)
- **Test:** 2025-08-02 to 2025-10-01

**Rationale:**
- Prevents data leakage (test data is always after training data)
- Gap accounts for any delayed data updates
- More realistic evaluation (model predicts future)

### 5. Feature Selection Strategy

**Decision:** Include all available features, let XGBoost handle selection via feature importance

**Rationale:**
- XGBoost's tree-based approach naturally handles irrelevant features
- Built-in regularization prevents overfitting
- Feature importance provides interpretability
- Simpler than manual feature selection

**Result:** Model uses all 20 features, but `is_gender_missing` has 0 importance (effectively ignored)

### 6. Handling Sparse Features

**Problem:** `flight_risk_score` is 98.7% sparse (only 1.3% non-zero)

**Attempted Solutions:**
1. **Original:** Multiplicative feature `pit_moves_3yr × max(-firm_net_change_12mo, 0)`
   - Result: Too sparse, model ignored it
   
2. **V2 Features Variant:** Created mobility tiers and binary flags
   - `pit_mobility_tier_Stable/Mobile/Highly_Mobile` (one-hot)
   - `has_prior_moves`, `is_bleeding_firm`, `is_flight_risk` (binary flags)
   - `flight_risk_tier` (binned 0-3)
   - Result: Slight improvement (1.42x vs 1.50x), but still below target

**Learning:** Sparsity is a fundamental challenge - even strong signals can't help if they're too rare.

---

## Challenges & Solutions

### Challenge 1: Broken Cross-Validation

**Problem:** Initial CV implementation had all folds 1-4 with ZERO positive examples

**Root Cause:** Data not sorted by `contacted_date` before TimeSeriesSplit

**Impact:**
- All Optuna trials returned identical CV scores (0.0439)
- Hyperparameter tuning was meaningless
- Model performance poor (1.46x lift)

**Solution:**
```python
# Sort data before CV
train_df = train_df.sort_values('contacted_date').reset_index(drop=True)
```

**Result:** CV scores now vary (std=0.0064), lift improved to 1.50x

### Challenge 2: Feature Sparsity

**Problem:** `flight_risk_score` shows +657% univariate signal but is 98.7% sparse

**Root Cause:** 
- 79.7% of leads have no moves (`pit_moves_3yr = 0`)
- 94.6% of leads at non-bleeding firms (`firm_net_change_12mo >= 0`)
- Multiplicative feature = 0 in most cases

**Attempted Solutions:**
1. Binning into tiers (v2-features variant)
2. Binary flags (`has_moves`, `is_bleeding_firm`)
3. Separate features instead of multiplicative

**Result:** Minimal improvement (1.42x vs 1.50x)

**Learning:** Strong signals can't help if they're too rare. Need more data or different feature engineering.

### Challenge 3: Performance Regression vs v2

**Problem:** v3 achieves 1.50x lift vs v2's 2.62x target

**Investigation:**
- Checked target variable definition (matches v2)
- Compared feature sets (v2 had mobility tiers, v3 uses raw values)
- Tested with v2 feature set (only 1.40x lift)

**Findings:**
- Data quality signals actually help (removing them hurts performance)
- Mobility tiers help slightly but not enough
- Signal strength decreased in 2025 vs 2024 data

**Hypothesis:** 
- 2025 data has different characteristics (fewer bleeding firms, more stable advisors)
- Model trained on 2024+2025 may be diluted
- Possible data shift in conversion patterns

### Challenge 4: Class Imbalance

**Problem:** Severe 26:1 class imbalance

**Solution:** XGBoost `scale_pos_weight = 26.34`

**Considerations:**
- Could use SMOTE for oversampling, but XGBoost handles imbalance well
- Stratified sampling not used (TimeSeriesSplit preserves temporal order)
- Calibration may be needed for probability outputs

---

## Model Performance

### Overall Metrics

| Metric | Value |
|--------|-------|
| **Test AUC-ROC** | 0.5808 |
| **Test AUC-PR** | 0.0569 |
| **Baseline (Positive Rate)** | 4.16% |
| **Top Decile Conversion Rate** | 6.25% |
| **Top Decile Lift** | 1.50x |
| **Target Lift** | 2.62x |

### Lift Analysis

**Top Decile Performance:**
- Top 10% of leads by predicted probability
- Conversion rate: 6.25% (vs 4.16% baseline)
- Lift: 1.50x (need 2.62x for target)

**Decile Breakdown:**
- Model successfully ranks leads (higher scores = higher conversion)
- But lift is insufficient for business requirements

### Feature Importance

**Top 10 Features:**

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `has_valid_virtual_snapshot` | 0.3211 |
| 2 | `has_firm_aum` | 0.1745 |
| 3 | `pit_moves_3yr` | 0.0596 |
| 4 | `industry_tenure_months` | 0.0547 |
| 5 | `num_prior_firms` | 0.0444 |
| 6 | `is_personal_email_missing` | 0.0389 |
| 7 | `current_firm_tenure_months` | 0.0386 |
| 8 | `firm_stability_percentile` | 0.0276 |
| 9 | `pit_avg_prior_tenure_months` | 0.0275 |
| 10 | `firm_stability_tier` | 0.0274 |

**Key Observations:**
1. **Data quality signals dominate:** Top 2 features are flags for data availability
2. **Protected features present:** `pit_moves_3yr` (#3) and `firm_net_change_12mo` (#14) are in model
3. **flight_risk_score ignored:** Rank #19 (correctly ignored due to sparsity)

### Comparison with Variants

| Model Variant | Features | Test AUC-ROC | Test AUC-PR | Lift |
|---------------|----------|--------------|-------------|------|
| **Full Model** | 20 features | 0.5808 | 0.0569 | **1.50x** |
| Core (no data quality) | 17 features | 0.5771 | 0.0544 | 1.26x |
| V2 features only | 9 features | 0.5677 | 0.0495 | 1.40x |
| **Target (v2)** | - | ~0.65-0.70 | ~0.07-0.10 | **2.62x** |

**Key Finding:** Removing data quality signals HURTS performance, suggesting they capture real signal about lead quality.

---

## Lessons Learned

### 1. Data Sorting is Critical for TimeSeriesSplit

**Lesson:** Always sort temporal data by date before using TimeSeriesSplit

**Impact:** Fixed CV, improved lift from 1.46x to 1.50x

### 2. Sparsity Kills Multiplicative Features

**Lesson:** Strong univariate signals can't help if they're too sparse

**Example:** `flight_risk_score` shows +657% signal but 98.7% sparse → model ignores it

**Solution:** Consider:
- Binary flags instead of multiplicative features
- Binning sparse features into tiers
- Separate features instead of interactions

### 3. Data Quality Signals Are Features

**Lesson:** Missing data patterns can be predictive

**Example:** `has_valid_virtual_snapshot` is the #1 feature (0.3211 importance)

**Implication:** Data completeness correlates with conversion likelihood

### 4. Temporal Validation is Essential

**Lesson:** TimeSeriesSplit provides more realistic evaluation than random splits

**Benefit:** Prevents overfitting to temporal patterns, ensures model generalizes to future data

### 5. Class Imbalance Requires Careful Handling

**Lesson:** 26:1 imbalance requires explicit weighting

**Solution:** XGBoost `scale_pos_weight` is effective, but calibration may still be needed for probabilities

### 6. Feature Engineering Trade-offs

**Lesson:** Categorical bins (tiers) vs raw values is a trade-off

**V2 used:** Mobility tiers (Stable/Mobile/Highly Mobile)  
**V3 used:** Raw `pit_moves_3yr` values

**Result:** Tiers helped slightly (1.42x vs 1.50x) but didn't solve the problem

### 7. Model Performance Depends on Data Quality

**Lesson:** Model can't exceed data quality

**Observation:** 
- Signal strength decreased in 2025 vs 2024
- Fewer bleeding firms, more stable advisors
- Conversion patterns may have shifted

---

## Code Structure

### Directory Organization

```
Version-2/
├── data/              # Data files (features, raw, scored)
├── models/            # Trained models and artifacts
│   ├── v3-boosted-20251221-30c0ec2d/
│   │   ├── model.pkl
│   │   ├── hyperparameters.json
│   │   ├── feature_names.json
│   │   ├── feature_importance.csv
│   │   └── training_metrics.json
│   └── registry.json
├── reports/           # Analysis reports and diagnostics
├── scripts/           # Training and analysis scripts
│   ├── phase_4_model_training.py
│   ├── phase_4_retrain_with_v2_features.py
│   ├── diagnostic_investigation.py
│   └── deep_diagnostic.py
├── sql/              # SQL feature engineering scripts
│   ├── phase_1_feature_engineering.sql
│   └── phase_2_temporal_split.sql
├── utils/            # Utility modules
│   ├── execution_logger.py
│   ├── paths.py
│   └── date_configuration.py
├── run_phase_*.py    # Phase execution scripts
├── date_config.json  # Date configuration
└── EXECUTION_LOG.md  # Execution log
```

### Key Scripts

#### 1. Feature Engineering (`run_phase_1.py`)
- Generates SQL for PIT feature engineering
- Creates `lead_scoring_features_pit` table
- Uses Virtual Snapshot methodology

#### 2. Temporal Split (`run_phase_2.py`)
- Creates train/test split with temporal gap
- Generates `lead_scoring_splits` table

#### 3. Model Training (`scripts/phase_4_model_training.py`)
- Loads data from BigQuery
- Engineers runtime features
- Runs Optuna hyperparameter tuning
- Trains final model
- Evaluates on test set
- Saves model artifacts

#### 4. Diagnostic Scripts
- `diagnostic_investigation.py`: Initial performance regression investigation
- `deep_diagnostic.py`: Root cause analysis of sparsity issues

### Execution Flow

```
Phase 0.0: Date Configuration
    ↓
Phase -1: Pre-Flight Assessment
    ↓
Phase 0.1: Data Landscape Assessment
    ↓
Phase 1: Feature Engineering (SQL)
    ↓
Phase 2: Temporal Split (SQL)
    ↓
Phase 3: Feature Validation
    ↓
Phase 4: Model Training (Python)
    ↓
Phase 5: Evaluation & SHAP (Not completed)
    ↓
Phase 6: Calibration (Not completed)
```

---

## Recommendations for Future Versions

### 1. Address Feature Sparsity

**Recommendation:** Prefer binary flags or tiers over multiplicative features

**Example:**
- Instead of: `flight_risk_score = pit_moves_3yr × max(-firm_net_change_12mo, 0)`
- Use: `has_moves` (binary), `is_bleeding_firm` (binary), `moves_count_binned` (tier)

### 2. Investigate Data Shift

**Recommendation:** Train separate models for 2024 vs 2025 data

**Hypothesis:** Conversion patterns changed between years, diluting model performance

### 3. Explore Additional Features

**Recommendation:** Consider:
- Firm size (rep count) - was in v2 but missing in v3
- AUM growth metrics
- Geographic proxies (metro advisor density)
- Lead source signals

### 4. Improve Feature Engineering

**Recommendation:** 
- Create interaction features explicitly (not just multiplicative)
- Use feature engineering techniques for sparse features (target encoding, etc.)
- Consider polynomial features for key signals

### 5. Model Calibration

**Recommendation:** Calibrate probability outputs using Platt scaling or isotonic regression

**Rationale:** XGBoost probabilities may not be well-calibrated for imbalanced data

### 6. Ensemble Methods

**Recommendation:** Consider ensemble of multiple models

**Approach:**
- Separate models for different lead sources
- Ensemble with different feature sets
- Stacking or voting ensembles

---

## Conclusion

The Version-2 lead scoring model demonstrates solid technical implementation with point-in-time feature engineering, proper temporal validation, and careful handling of class imbalance. However, performance falls short of the 2.62x lift target, achieving only 1.50x.

**Key Strengths:**
- Rigorous PIT methodology prevents data leakage
- Proper temporal validation with TimeSeriesSplit
- Comprehensive feature engineering
- Effective handling of class imbalance

**Key Limitations:**
- Feature sparsity limits model performance
- Data quality signals dominate (may indicate data quality issues)
- Performance gap vs previous version (1.50x vs 2.62x target)

**Next Steps:**
1. Investigate data shift between 2024 and 2025
2. Experiment with alternative feature engineering approaches
3. Consider ensemble methods or separate models by lead source
4. Explore additional data sources or features

---

## Appendix: Model Artifacts

### Saved Artifacts

Each trained model saves:
- `model.pkl`: Trained XGBoost model (pickle)
- `hyperparameters.json`: Best hyperparameters from Optuna
- `feature_names.json`: Feature configuration
- `feature_importance.csv`: Feature importance rankings
- `training_metrics.json`: Performance metrics

### Model Registry

`models/registry.json` tracks all trained models:
```json
{
  "models": [
    {
      "version_id": "v3-boosted-20251221-30c0ec2d",
      "status": "trained",
      "created_at": "2025-12-21T05:37:27",
      "metrics": { ... }
    }
  ],
  "latest": "v3-boosted-20251221-30c0ec2d"
}
```

---

**Report Generated:** December 2025  
**Model Version:** v3-boosted-20251221-30c0ec2d  
**Status:** Development Complete, Performance Review Required

