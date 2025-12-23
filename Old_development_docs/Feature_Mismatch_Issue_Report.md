# Feature Mismatch Issue Report: V4 Model Pipeline

**Date:** November 3, 2025  
**Status:** PERSISTENT ISSUE - Feature name/order mismatch between training, calibration, and backtesting  
**Impact:** Blocking Unit 6 (Backtesting and Performance Validation)

---

## Executive Summary

We are experiencing a persistent `ValueError: feature_names mismatch` error when attempting to use the calibrated V4 model (`model_v4_calibrated.pkl`) for predictions in Unit 6. The error indicates that the feature names and/or order expected by the model do not match what we're providing, despite multiple attempts to align them.

**Root Cause:** The feature names stored in the XGBoost booster (inside the calibrated model) differ from the feature names we're providing in the same order. Specifically, there's a mismatch in:
1. **Feature order**: The model expects features in a specific order (e.g., `Day_of_Contact`, `Is_Weekend_Contact` first), but we're providing them in a different order (e.g., `AUMGrowthRate_1Year` first).
2. **Feature naming**: Possible case-sensitivity or naming inconsistencies (e.g., `AUM_Per_Client` vs `AUM_per_Client`).

---

## Error Details

### Error Message
```
ValueError: feature_names mismatch: ['Day_of_Contact', 'Is_Weekend_Contact', 'Branch_Latitude', ...] 
['AUMGrowthRate_1Year', 'AUMGrowthRate_5Year', 'AUM_Per_BranchAdvisor', ...]
```

### Error Location
- **File:** `unit_6_backtesting_v4.py`
- **Line:** 797 (`y_proba = model_v4.predict_proba(X)[:, 1]`)
- **Stack Trace:** `xgboost.core.py` → `_validate_features()` → Raises `ValueError` when feature names/order don't match

---

## Data Flow and Feature Processing

### Stage 1: Training (Unit 4 - `unit_4_train_model_v4.py`)

**Input Data:**
- BigQuery table: `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2`
- 43,854 rows, 131 columns (includes PII and all features)

**Processing Steps:**

1. **Load data from BigQuery:**
```python
def load_data_from_bigquery() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{BQ_TABLE}`'
    df = client.query(query).to_dataframe()
    return df
```

2. **Create m5 engineered features:**
```python
df = create_m5_engineered_features(df)
# Creates 31 engineered features (e.g., AUM_per_Client, Firm_Stability_Score, etc.)
```

3. **Drop PII features:**
```python
PII_TO_DROP = [
    'FirstName', 'LastName', 
    'Branch_City', 'Branch_County', 'Branch_ZipCode',
    'Home_City', 'Home_County', 'Home_ZipCode',
    'RIAFirmCRD', 'RIAFirmName',
    'PersonalWebpage', 'Notes'
]

pii_cols_to_drop = [col for col in PII_TO_DROP if col in df.columns]
df = df.drop(columns=pii_cols_to_drop)
```

4. **Extract feature columns:**
```python
# Remove metadata columns
metadata_cols = {
    "Id", "FA_CRD__c", "Stage_Entered_Contacting__c",
    "Stage_Entered_Call_Scheduled__c", "target_label",
    "is_eligible_for_mutable_features", "is_in_right_censored_window",
    "days_to_conversion"
}
feature_cols = [c for c in df.columns if c not in metadata_cols]
X = df[feature_cols].copy()
y = df["target_label"].astype(int).values
```

5. **Train XGBoost model:**
```python
model = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    scale_pos_weight=pos_weight,
    random_state=seed,
    enable_categorical=True  # CRITICAL: Handles categorical features natively
)
model.fit(X, y)
```

**Result:**
- Model saved as `model_v4.pkl`
- Model expects **120 features** (after PII removal and m5 feature engineering)
- Feature order: Determined by the order of columns in `X` DataFrame when `model.fit()` is called
- **Critical:** The feature order is determined by pandas DataFrame column order, which may not be deterministic

**Expected Features (from model):**
- The model's `feature_names_in_` attribute contains the feature names in the order they were provided during training
- The XGBoost booster's `feature_names` attribute contains the same names in the same order

---

### Stage 2: Calibration (Unit 5 - `unit_5_calibration_v4.py`)

**Input:**
- `model_v4.pkl` (base model from Unit 4)
- Training data from BigQuery (same table as Unit 4)

**Processing Steps:**

1. **Load base model:**
```python
base_model = joblib.load("model_v4.pkl")
```

2. **Load data from BigQuery:**
```python
df = load_data_from_bigquery()  # Same function as Unit 4
```

3. **Drop PII and create m5 features (SAME AS TRAINING):**
```python
# CRITICAL: Must match training exactly
pii_cols_to_drop = [col for col in PII_TO_DROP if col in df.columns]
df = df.drop(columns=pii_cols_to_drop)

df = create_m5_engineered_features(df)  # Same function as Unit 4
```

4. **Prepare features:**
```python
# Get feature names from base model
expected_features = list(base_model.feature_names_in_)

# Ensure X has features in the same order as training
X = df[expected_features].copy()
y = df["target_label"].astype(int).values
```

5. **Calibrate model:**
```python
global_calibrator = CalibratedClassifierCV(
    base_model,
    method='isotonic',
    cv='prefit',
    n_jobs=1
)
global_calibrator.fit(X, y)
```

6. **Save calibrated model:**
```python
calibrated_model_data = {
    'model': base_model,
    'global_calibrator': global_calibrator,
    'segment_calibrators': segment_calibrators,
    'ece_by_segment': ece_by_segment
}
joblib.dump(calibrated_model_data, "model_v4_calibrated.pkl")
```

**Result:**
- Calibrated model saved as `model_v4_calibrated.pkl`
- The calibrated model wraps the base model, which contains the XGBoost booster with feature names

**Critical Issue Identified:**
- The calibrated model's base estimator (XGBoost) has feature names stored in its booster
- These feature names are in the order they were provided during training
- When we calibrate, we must provide features in the **exact same order** as training

---

### Stage 3: Backtesting (Unit 6 - `unit_6_backtesting_v4.py`)

**Input:**
- `model_v4_calibrated.pkl` (calibrated model from Unit 5)
- Training data from BigQuery (same table as Unit 4/5)

**Processing Steps:**

1. **Load calibrated model:**
```python
calibrated_model_data = joblib.load("model_v4_calibrated.pkl")
model_v4 = calibrated_model_data['global_calibrator']  # CalibratedClassifierCV
base_model = calibrated_model_data['model']  # Base XGBoost model
```

2. **Load data from BigQuery:**
```python
df = load_data_from_bigquery()  # Same function as Unit 4/5
```

3. **Drop PII and create m5 features (SAME AS TRAINING):**
```python
pii_cols_to_drop = [col for col in PII_TO_DROP if col in df.columns]
df = df.drop(columns=pii_cols_to_drop)

df = create_m5_engineered_features(df)  # Same function as Unit 4/5
```

4. **Get expected features from model:**
```python
# Try to get feature names from booster (most accurate)
if hasattr(model_v4, 'calibrated_classifiers_'):
    first_cal = model_v4.calibrated_classifiers_[0]
    if hasattr(first_cal, 'base_estimator'):
        base_est = first_cal.base_estimator
        if hasattr(base_est, 'get_booster'):
            booster = base_est.get_booster()
            expected_features = list(booster.feature_names)  # Feature names from booster
```

5. **Prepare X with features in expected order:**
```python
# Add missing features as NaN
for feat in expected_features:
    if feat not in df.columns:
        df[feat] = np.nan

# Create X with features in EXACT order
X = df[expected_features].copy()
```

6. **Generate predictions:**
```python
y_proba = model_v4.predict_proba(X)[:, 1]  # ERROR OCCURS HERE
```

**Error:**
```
ValueError: feature_names mismatch: 
  Model expects: ['Day_of_Contact', 'Is_Weekend_Contact', 'Branch_Latitude', ...]
  We provided: ['AUMGrowthRate_1Year', 'AUMGrowthRate_5Year', 'AUM_Per_BranchAdvisor', ...]
```

**Observation:**
- The model expects features starting with `Day_of_Contact`, `Is_Weekend_Contact`
- We're providing features starting with `AUMGrowthRate_1Year`, `AUMGrowthRate_5Year`
- This indicates a **feature order mismatch**

---

## What We've Tried

### Attempt 1: Get feature names from booster
**Code:**
```python
# Get feature names from booster inside calibrated model
booster = model_v4.calibrated_classifiers_[0].base_estimator.get_booster()
expected_features = list(booster.feature_names)
X = df[expected_features].copy()
```

**Result:** Still getting feature mismatch error

### Attempt 2: Reorder X to match expected features
**Code:**
```python
# Ensure X columns match exactly
X = X.reindex(columns=expected_features)
# Add missing features as NaN
for feat in expected_features:
    if feat not in X.columns:
        X[feat] = np.nan
```

**Result:** Still getting feature mismatch error

### Attempt 3: Convert to numpy array in exact order
**Code:**
```python
X_array = X[expected_features].values
# But CalibratedClassifierCV expects DataFrame, not array
```

**Result:** Not applicable (CalibratedClassifierCV needs DataFrame)

### Attempt 4: Use feature_names_in_ from base model
**Code:**
```python
expected_features = list(base_model.feature_names_in_)
X = df[expected_features].copy()
```

**Result:** Still getting feature mismatch error

### Attempt 5: Handle case-sensitivity in feature names
**Code:**
```python
# Map feature names (case-insensitive)
feature_name_mapping = {}
for model_feat in expected_features:
    if model_feat not in df.columns:
        possible_matches = [c for c in df.columns if c.lower() == model_feat.lower()]
        if possible_matches:
            feature_name_mapping[model_feat] = possible_matches[0]
            df[model_feat] = df[possible_matches[0]].copy()
```

**Result:** Still getting feature mismatch error

### Attempt 6: Multiple fallback strategies for getting feature names
**Code:**
```python
# Try 1: Get from booster
# Try 2: Get from calibrated base estimator
# Try 3: Get from base model
# Try 4: Use all non-metadata columns
```

**Result:** All strategies still result in feature mismatch error

---

## Data Structure Analysis

### Feature Counts at Each Stage

| Stage | Input Columns | After PII Drop | After m5 Features | Final Feature Count |
|-------|--------------|----------------|-------------------|---------------------|
| **Training** | 131 | 119 | 120 | 120 |
| **Calibration** | 131 | 119 | 120 | 120 |
| **Backtesting** | 131 | 119 | 120 | 120 |

**Observation:** Feature counts are consistent across all stages.

### Feature Order Analysis

**Training (Unit 4):**
- Feature order is determined by pandas DataFrame column order after:
  1. Loading from BigQuery
  2. Creating m5 features
  3. Dropping PII
  4. Removing metadata columns
- **Problem:** This order may not be deterministic (depends on SQL SELECT * order, pandas DataFrame column order, etc.)

**Calibration (Unit 5):**
- Uses `base_model.feature_names_in_` to get expected features
- Orders DataFrame columns to match `expected_features`
- **Assumption:** `base_model.feature_names_in_` contains the correct order

**Backtesting (Unit 6):**
- Tries multiple strategies to get expected features:
  1. From booster (inside calibrated model)
  2. From calibrated base estimator
  3. From base model
- Orders DataFrame columns to match `expected_features`
- **Problem:** The order from booster doesn't match what we're providing

---

## Root Cause Hypothesis

### Hypothesis 1: Feature Order Non-Determinism
**Theory:** The feature order during training is non-deterministic because:
- BigQuery `SELECT *` may return columns in different orders
- Pandas DataFrame column order may vary
- `create_m5_engineered_features()` adds features in a specific order, but existing features may be in a different order

**Evidence:**
- The error shows model expects `Day_of_Contact` first, but we're providing `AUMGrowthRate_1Year` first
- This suggests the order during training was different from what we're providing now

### Hypothesis 2: Feature Name Mismatch
**Theory:** There are subtle differences in feature names (case, underscores, etc.) that cause the mismatch.

**Evidence:**
- Error message shows feature names, but they appear to be the same (just in different order)
- However, there may be case-sensitivity issues (e.g., `AUM_Per_Client` vs `AUM_per_Client`)

### Hypothesis 3: Calibration Wrapper Issue
**Theory:** The `CalibratedClassifierCV` wrapper may be storing feature names differently than the base model.

**Evidence:**
- We're getting feature names from the booster inside the calibrated model
- But the calibrated model may have a different feature order expectation

---

## Code Snippets

### Training (Unit 4) - Feature Preparation
```python
# unit_4_train_model_v4.py

# Load data
df = load_data_from_bigquery()  # 131 columns

# Create m5 features
df = create_m5_engineered_features(df)  # Adds ~8 features

# Drop PII
pii_cols_to_drop = [col for col in PII_TO_DROP if col in df.columns]
df = df.drop(columns=pii_cols_to_drop)  # Removes 12 PII features

# Extract feature columns (order determined by DataFrame column order)
metadata_cols = {"Id", "FA_CRD__c", ...}
feature_cols = [c for c in df.columns if c not in metadata_cols]
X = df[feature_cols].copy()  # 120 features, order = DataFrame column order

# Train model
model.fit(X, y)  # Model stores feature names in XGBoost booster
```

### Calibration (Unit 5) - Feature Preparation
```python
# unit_5_calibration_v4.py

# Load data
df = load_data_from_bigquery()  # 131 columns

# Drop PII and create m5 features (SAME AS TRAINING)
pii_cols_to_drop = [col for col in PII_TO_DROP if col in df.columns]
df = df.drop(columns=pii_cols_to_drop)
df = create_m5_engineered_features(df)

# Get expected features from base model
expected_features = list(base_model.feature_names_in_)  # 120 features

# Prepare X in expected order
X = df[expected_features].copy()  # Order matches base_model.feature_names_in_

# Calibrate
global_calibrator.fit(X, y)
```

### Backtesting (Unit 6) - Feature Preparation
```python
# unit_6_backtesting_v4.py

# Load data
df = load_data_from_bigquery()  # 131 columns

# Drop PII and create m5 features (SAME AS TRAINING)
pii_cols_to_drop = [col for col in PII_TO_DROP if col in df.columns]
df = df.drop(columns=pii_cols_to_drop)
df = create_m5_engineered_features(df)

# Get expected features from booster (inside calibrated model)
booster = model_v4.calibrated_classifiers_[0].base_estimator.get_booster()
expected_features = list(booster.feature_names)  # 120 features, order from booster

# Prepare X in expected order
for feat in expected_features:
    if feat not in df.columns:
        df[feat] = np.nan
X = df[expected_features].copy()  # Order matches booster.feature_names

# ERROR: Feature mismatch
y_proba = model_v4.predict_proba(X)[:, 1]
```

---

## Recommended Solutions

### Solution 1: Save Feature Order During Training
**Approach:** Save the feature order (as a list) during training and use it in all subsequent stages.

**Implementation:**
```python
# In unit_4_train_model_v4.py
feature_order = list(X.columns)
joblib.dump(feature_order, "feature_order_v4.pkl")

# In unit_5_calibration_v4.py and unit_6_backtesting_v4.py
feature_order = joblib.load("feature_order_v4.pkl")
X = df[feature_order].copy()
```

**Pros:**
- Guarantees consistent feature order
- Simple to implement
- No changes to model structure

**Cons:**
- Requires saving an additional artifact
- Must ensure feature_order is used consistently

### Solution 2: Use XGBoost's Feature Names Validation Off
**Approach:** Disable feature name validation in XGBoost (not recommended for production, but useful for debugging).

**Implementation:**
```python
# When making predictions
X_array = X[expected_features].values  # Convert to numpy array
y_proba = model_v4.predict_proba(X_array)[:, 1]  # But this may not work with CalibratedClassifierCV
```

**Pros:**
- Bypasses feature name validation

**Cons:**
- Not recommended for production
- May not work with CalibratedClassifierCV
- Loses feature name safety checks

### Solution 3: Ensure Deterministic Feature Order During Training
**Approach:** Sort feature columns alphabetically (or by a predefined order) before training.

**Implementation:**
```python
# In unit_4_train_model_v4.py
feature_cols = sorted([c for c in df.columns if c not in metadata_cols])
X = df[feature_cols].copy()
model.fit(X, y)
```

**Pros:**
- Ensures deterministic order
- No additional artifacts needed

**Cons:**
- May change model behavior (if feature order matters for XGBoost)
- Must apply same sorting in all stages

### Solution 4: Re-train Model with Explicit Feature Order
**Approach:** Define a canonical feature order (e.g., from config file) and use it consistently.

**Implementation:**
```python
# Load canonical feature order from config
with open("config/v1_feature_schema.json") as f:
    schema = json.load(f)
canonical_feature_order = [f["name"] for f in schema["features"]]

# In all stages, use canonical order
X = df[canonical_feature_order].copy()
```

**Pros:**
- Single source of truth for feature order
- Guarantees consistency

**Cons:**
- Requires updating config file
- Must ensure all features in config exist in data

---

## Next Steps

1. **Immediate:** Implement Solution 1 (save feature order during training) and re-run Unit 4 training
2. **Short-term:** Verify feature order consistency across all stages
3. **Long-term:** Consider Solution 4 (canonical feature order from config) for future models

---

## Questions for Further Investigation

1. **Why does the booster have a different feature order than `feature_names_in_`?**
   - Are they supposed to be the same?
   - Is there a transformation happening during calibration?

2. **Is the feature order deterministic in BigQuery `SELECT *`?**
   - Should we explicitly order columns in SQL?

3. **Does XGBoost care about feature order?**
   - Or only feature names?
   - The error suggests both order and names matter

4. **Should we use `validate_features=False` in XGBoost predictions?**
   - This would bypass the validation, but is not recommended for production

---

## Appendix: Error Traceback

```
ValueError: feature_names mismatch: 
  ['Day_of_Contact', 'Is_Weekend_Contact', 'Branch_Latitude', 'Branch_Longitude', 'Branch_State', 'BreakawayRep', 'Brochure_Keywords', 'Custodian1', 'Custodian2', 'Custodian3', 'Custodian4', 'Custodian5', 'CustomKeywords', 'DuallyRegisteredBDRIARep', 'Education', 'Email_BusinessType', 'Email_PersonalType', 'FirmWebsite', 'Gender', 'Has_AIF', 'Has_CFA', 'Has_CFP', 'Has_CIMA', 'Has_Series_24', 'Has_Series_65', 'Has_Series_66', 'Has_Series_7', 'Home_Latitude', 'Home_Longitude', 'Home_MetropolitanArea', 'Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN', 'Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX', 'Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA', 'Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL', 'Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ', 'Home_State', 'IsPrimaryRIAFirm', 'Is_Known_Non_Advisor', 'KnownNonAdvisor', 'Licenses', 'MilesToWork', 'Multi_Firm_Associations', 'Multi_RIA_Relationships', 'NumberFirmAssociations', 'NumberRIAFirmAssociations', 'RegulatoryDisclosures', 'SocialMedia_LinkedIn', 'Title', 'DateBecameRep_NumberOfYears', 'DateOfHireAtCurrentFirm_NumberOfYears', 'Number_Of_Prior_Firms', 'Number_YearsPriorFirm1', 'Number_YearsPriorFirm2', 'Number_YearsPriorFirm3', 'Number_YearsPriorFirm4', 'Total_Prior_Firm_Years', 'AUMGrowthRate_1Year', 'AUMGrowthRate_5Year', 'AUM_Per_BranchAdvisor', 'AUM_Per_Client', 'AUM_Per_IARep', 'Accelerating_Growth', 'AssetsInMillions_Equity_ExchangeTraded', 'AssetsInMillions_HNWIndividuals', 'AssetsInMillions_Individuals', 'AssetsInMillions_MutualFunds', 'AssetsInMillions_PrivateFunds', 'Clients_per_BranchAdvisor', 'Clients_per_IARep', 'CustodianAUM_Fidelity_NationalFinancial', 'CustodianAUM_Pershing', 'CustodianAUM_Schwab', 'CustodianAUM_TDAmeritrade', 'Firm_Stability_Score', 'Growth_Momentum', 'HNW_Asset_Concentration', 'HNW_Client_Ratio', 'Has_Disclosure', 'Has_ETF_Focus', 'Has_Fidelity_Relationship', 'Has_Mutual_Fund_Focus', 'Has_Pershing_Relationship', 'Has_Private_Funds', 'Has_Scale', 'Has_Schwab_Relationship', 'Has_TDAmeritrade_Relationship', 'Individual_Asset_Ratio', 'Is_Boutique_Firm', 'Is_Breakaway_Rep', 'Is_Dually_Registered', 'Is_Large_Firm', 'Is_New_To_Firm', 'Is_Primary_RIA', 'Is_Veteran_Advisor', 'Local_Advisor', 'NumberClients_HNWIndividuals', 'NumberClients_Individuals', 'NumberClients_RetirementPlans', 'Number_BranchAdvisors', 'Number_IAReps', 'Number_Of_Prior_Firms', 'Number_YearsPriorFirm1', 'Number_YearsPriorFirm2', 'Number_YearsPriorFirm3', 'Number_YearsPriorFirm4', 'PercentAssets_Equity_ExchangeTraded', 'PercentAssets_HNWIndividuals', 'PercentAssets_Individuals', 'PercentAssets_MutualFunds', 'PercentAssets_PrivateFunds', 'PercentClients_HNWIndividuals', 'PercentClients_Individuals', 'Positive_Growth_Trajectory', 'Remote_Work_Indicator', 'TotalAssetsInMillions', 'TotalAssets_PooledVehicles', 'TotalAssets_SeparatelyManagedAccounts', 'AUM_per_Client', 'AUM_per_IARep', 'Growth_Acceleration', 'Experience_Efficiency', 'Alternative_Investment_Focus', 'High_Turnover_Flag', 'Complex_Registration', 'Quality_Score']
  
  ['AUMGrowthRate_1Year', 'AUMGrowthRate_5Year', 'AUM_Per_BranchAdvisor', 'AUM_Per_Client', 'AUM_Per_IARep', 'AUM_per_Client', 'AUM_per_IARep', 'Accelerating_Growth', 'Alternative_Investment_Focus', 'AssetsInMillions_Equity_ExchangeTraded', 'AssetsInMillions_HNWIndividuals', 'AssetsInMillions_Individuals', 'AssetsInMillions_MutualFunds', 'AssetsInMillions_PrivateFunds', 'Branch_Latitude', 'Branch_Longitude', 'Branch_State', 'BreakawayRep', 'Brochure_Keywords', 'Clients_per_BranchAdvisor', 'Clients_per_IARep', 'Complex_Registration', 'Custodian1', 'Custodian2', 'Custodian3', 'Custodian4', 'Custodian5', 'CustodianAUM_Fidelity_NationalFinancial', 'CustodianAUM_Pershing', 'CustodianAUM_Schwab', 'CustodianAUM_TDAmeritrade', 'CustomKeywords', 'DateBecameRep_NumberOfYears', 'DateOfHireAtCurrentFirm_NumberOfYears', 'Day_of_Contact', 'DuallyRegisteredBDRIARep', 'Education', 'Email_BusinessType', 'Email_PersonalType', 'Experience_Efficiency', 'FirmWebsite', 'Firm_Stability_Score', 'Gender', 'Growth_Acceleration', 'Growth_Momentum', 'HNW_Asset_Concentration', 'HNW_Client_Ratio', 'Has_AIF', 'Has_CFA', 'Has_CFP', 'Has_CIMA', 'Has_Disclosure', 'Has_ETF_Focus', 'Has_Fidelity_Relationship', 'Has_Mutual_Fund_Focus', 'Has_Pershing_Relationship', 'Has_Private_Funds', 'Has_Scale', 'Has_Schwab_Relationship', 'Has_Series_24', 'Has_Series_65', 'Has_Series_66', 'Has_Series_7', 'Has_TDAmeritrade_Relationship', 'High_Turnover_Flag', 'Home_Latitude', 'Home_Longitude', 'Home_MetropolitanArea', 'Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN', 'Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX', 'Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA', 'Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL', 'Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ', 'Home_State', 'Individual_Asset_Ratio', 'IsPrimaryRIAFirm', 'Is_Boutique_Firm', 'Is_Breakaway_Rep', 'Is_Dually_Registered', 'Is_Known_Non_Advisor', 'Is_Large_Firm', 'Is_New_To_Firm', 'Is_Primary_RIA', 'Is_Veteran_Advisor', 'Is_Weekend_Contact', 'KnownNonAdvisor', 'Licenses', 'Local_Advisor', 'MilesToWork', 'Multi_Firm_Associations', 'Multi_RIA_Relationships', 'NumberClients_HNWIndividuals', 'NumberClients_Individuals', 'NumberClients_RetirementPlans', 'NumberFirmAssociations', 'NumberRIAFirmAssociations', 'Number_BranchAdvisors', 'Number_IAReps', 'Number_Of_Prior_Firms', 'Number_YearsPriorFirm1', 'Number_YearsPriorFirm2', 'Number_YearsPriorFirm3', 'Number_YearsPriorFirm4', 'PercentAssets_Equity_ExchangeTraded', 'PercentAssets_HNWIndividuals', 'PercentAssets_Individuals', 'PercentAssets_MutualFunds', 'PercentAssets_PrivateFunds', 'PercentClients_HNWIndividuals', 'PercentClients_Individuals', 'Positive_Growth_Trajectory', 'Quality_Score', 'RegulatoryDisclosures', 'Remote_Work_Indicator', 'SocialMedia_LinkedIn', 'Title', 'TotalAssetsInMillions', 'TotalAssets_PooledVehicles', 'TotalAssets_SeparatelyManagedAccounts', 'Total_Prior_Firm_Years']
```

**Key Observation:**
- Model expects: `Day_of_Contact`, `Is_Weekend_Contact` **first**
- We provide: `AUMGrowthRate_1Year`, `AUMGrowthRate_5Year` **first**
- All features are present, just in different order

---

**End of Report**

