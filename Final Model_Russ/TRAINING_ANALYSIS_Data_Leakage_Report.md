# Training Analysis: Data Leakage Report
## FinalLeadScorePipeline.ipynb Investigation

**Date:** 2025  
**Model:** Final Model (m5)  
**Notebook:** `FinalLeadScorePipeline.ipynb`

---

## 🔴 **CRITICAL FINDINGS: Multiple Data Leakage Issues Identified**

### **1. Temporal Data Leakage - Random Split Instead of Temporal Split**

**Issue Location:** Cell 31 (lines 805-806)

```python
X_train_m5, X_test_m5, y_train_m5, y_test_m5 = train_test_split(
    X_m5, y_m5, test_size=0.2, random_state=42, stratify=y_m5
)
```

**Problem:**
- Uses **random train-test split** instead of **temporal split**
- Training data may include leads created AFTER test set leads
- Model learns patterns from future data that shouldn't be available at prediction time
- This violates the fundamental principle of time-based machine learning

**Expected Behavior:**
- Should split by `CreatedDate` or `Stage_Entered_Contacting__c`
- Training: Leads created before cutoff date
- Test: Leads created after cutoff date
- This ensures the model only sees historical data

---

### **2. Preprocessing Leakage - Fitting on ALL Data Including Future/Test Data**

**Issue Location:** Cell 21 (lines 380-386)

```python
## Fit scalers on known population data
X_scalers = model_data.copy().drop(columns=descriptive_columns + [target])
Standard_Scaler = StandardScaler()
Standard_Scaler.fit(X_scalers)  # ⚠️ Fitting on ALL data!

# Create an iterative imputer
imputer = IterativeImputer(max_iter=25, random_state=42)
imputer.fit(X_scalers)  # ⚠️ Fitting on ALL data!
```

**Problem:**
- Scalers and imputers are fit on **ENTIRE `model_data`** dataset
- This includes:
  - Training data ✓ (should be here)
  - Test data ✗ (leakage - shouldn't see test distribution)
  - Future/unlabeled data ✗ (leakage - shouldn't see future patterns)
- Model learns statistics (mean, std, correlations) from test/future data
- This inflates performance metrics artificially

**Expected Behavior:**
- Fit scalers/imputers **ONLY on training data** after temporal split
- Apply fitted transformers to test data
- This ensures preprocessing doesn't see test distribution

---

### **3. Target Variable Creation - No Temporal Filtering**

**Issue Location:** `feature_engineering_functions.py` (line 172)

```python
model_data['EverCalled'] = model_data['Stage_Entered_Call_Scheduled__c'].notna().astype(bool)
```

**Problem:**
- Target is created simply by checking if `Stage_Entered_Call_Scheduled__c` exists
- **No temporal validation** to ensure the call happened AFTER the lead was contacted
- **No right-censoring window** to exclude leads that are too recent
- Leads created in the last 30 days might be incorrectly labeled as "Never Called" when they just haven't had time yet

**Expected Behavior (from V6 guide):**
```sql
CASE 
    WHEN s.Stage_Entered_Call_Scheduled__c IS NOT NULL 
    AND DATE(s.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(s.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
    THEN 1 
    ELSE 0 
END as target_label,
CASE 
    WHEN DATE(s.Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    THEN 1
    ELSE 0
END as is_in_right_censored_window
```
- Exclude leads contacted in last 30 days (right-censored)
- Only label as "Called" if call scheduled within 30 days of contact
- This ensures temporal correctness

---

### **4. Feature Engineering on Entire Dataset Before Split**

**Issue Location:** Cell 29 (lines 671-678)

```python
# Apply feature engineering to your model_data
model_data_m5 = create_advanced_features(model_data)

# Get labeled data only (matching your existing filter)
labeled_data_m5 = model_data_m5[
    model_data_m5["FA_CRD__c"].notna() & 
    model_data_m5["RepCRD"].notna() & 
    model_data_m5["RIAFirmCRD"].notna()
]
```

**Problem:**
- Advanced features (like quantiles, medians) are calculated on **ENTIRE dataset**
- Features like `Is_Boutique_Firm` use `df["AverageAccountSize"].quantile(0.75)` from ALL data
- Features like `Premium_Positioning` use `df["AverageAccountSize"].quantile(0.75)` from ALL data
- This means test data influences feature creation for training data

**Example from `create_advanced_features()`:**
```python
df["Is_Boutique_Firm"] = (
    (df["Number_Employees"] <= 20) & 
    (df["AverageAccountSize"] > df["AverageAccountSize"].quantile(0.75))  # ⚠️ Uses ALL data!
).astype(int)

df["Premium_Positioning"] = (
    (df["AverageAccountSize"] > df["AverageAccountSize"].quantile(0.75)) &  # ⚠️ Uses ALL data!
    (df["PercentClients_Individuals"] < 50)
).astype(int)
```

**Expected Behavior:**
- Calculate quantiles/medians **ONLY from training data**
- Apply thresholds to test data
- Or use global thresholds from a separate reference dataset

---

### **5. Static Dataset with No Point-in-Time Features**

**Issue Location:** Entire notebook approach

**Problem:**
- Model uses **current snapshot** of Discovery data for ALL historical leads
- Discovery data features (AUM, clients, etc.) are from TODAY, not from when the lead was contacted
- This means:
  - A lead contacted in 2023 uses 2024/2025 Discovery data
  - Model sees "future" information about firm growth, changes, etc.
  - This is a form of **temporal leakage**

**Expected Behavior (from V6 guide):**
- Use **point-in-time snapshots** of Discovery data
- For a lead contacted on 2023-03-15, use Discovery snapshot from 2023 Q1
- Join to `snapshot_reps_2023_q1` and `snapshot_firms_2023_q1`
- This ensures features reflect what was known AT THE TIME of contact

---

## 📊 **Summary of Issues**

| Issue | Severity | Location | Impact |
|-------|----------|----------|--------|
| Random split (not temporal) | 🔴 Critical | Cell 31 | Model sees future data patterns |
| Preprocessing fit on all data | 🔴 Critical | Cell 21 | Test distribution leaks into training |
| Target creation - no temporal filter | 🔴 Critical | feature_engineering_functions.py:172 | Labels may be incorrect |
| Feature engineering on all data | 🟡 High | Cell 29 | Quantiles/medians use test data |
| Static dataset (no point-in-time) | 🔴 Critical | Entire approach | Features from wrong time period |

---

## ✅ **What Was Done Correctly**

1. **Target variable exclusion from features:** ✓ Correctly excluded from feature columns
2. **Descriptive columns exclusion:** ✓ Correctly excluded from training features
3. **Feature selection:** ✓ Properly separated features from descriptive columns
4. **Model architecture:** ✓ XGBoost with SMOTE is reasonable
5. **Calibration:** ✓ Using CalibratedClassifierCV for probability calibration

---

## 🎯 **Recommended Fixes**

### **Priority 1: Temporal Split**
```python
# Sort by CreatedDate or Stage_Entered_Contacting__c
labeled_data_m5 = labeled_data_m5.sort_values('CreatedDate')

# Temporal split (80/20)
split_idx = int(len(labeled_data_m5) * 0.8)
train_data = labeled_data_m5.iloc[:split_idx]
test_data = labeled_data_m5.iloc[split_idx:]

X_train_m5 = train_data[m5_features]
y_train_m5 = train_data[target]
X_test_m5 = test_data[m5_features]
y_test_m5 = test_data[target]
```

### **Priority 2: Fix Preprocessing**
```python
# Fit scalers/imputers ONLY on training data
Standard_Scaler = StandardScaler()
Standard_Scaler.fit(X_train_m5)  # Only training!

imputer = IterativeImputer(max_iter=25, random_state=42)
imputer.fit(X_train_m5)  # Only training!
```

### **Priority 3: Fix Target Creation**
```python
# Add temporal validation
def create_target_with_temporal_validation(df, contact_date_col='CreatedDate', 
                                           call_scheduled_col='Stage_Entered_Call_Scheduled__c',
                                           cutoff_days=30):
    """
    Create target with proper temporal validation
    """
    # Exclude right-censored leads (too recent)
    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=cutoff_days)
    df['is_right_censored'] = pd.to_datetime(df[contact_date_col]) > cutoff_date
    
    # Create target: called within 30 days of contact
    df['EverCalled'] = (
        df[call_scheduled_col].notna() &
        (pd.to_datetime(df[call_scheduled_col]) <= 
         pd.to_datetime(df[contact_date_col]) + pd.Timedelta(days=30))
    ).astype(bool)
    
    # Set right-censored leads to NaN (exclude from training)
    df.loc[df['is_right_censored'], 'EverCalled'] = np.nan
    
    return df
```

### **Priority 4: Fix Feature Engineering**
```python
# Calculate thresholds on training data only
def create_advanced_features(df, reference_df=None):
    """
    Create advanced features using reference dataset for quantiles
    """
    if reference_df is None:
        reference_df = df  # Fallback to current data
    
    # Use reference_df for quantiles/medians
    df["Is_Boutique_Firm"] = (
        (df["Number_Employees"] <= 20) & 
        (df["AverageAccountSize"] > reference_df["AverageAccountSize"].quantile(0.75))
    ).astype(int)
    
    # ... rest of features
```

### **Priority 5: Use Point-in-Time Data**
- Follow the V6 guide approach
- Join to historical snapshot tables based on contact date
- Use Discovery data from the appropriate quarter

---

## 📈 **Expected Impact of Fixes**

After implementing these fixes:

1. **Model performance will likely DECREASE** (more realistic)
   - Current metrics (ROC AUC: 0.79, Top 10% Lift: 3.93x) are likely inflated
   - Real performance will be lower but more trustworthy

2. **Model will be production-ready**
   - No data leakage means predictions will generalize
   - Can confidently deploy to score new leads

3. **Temporal correctness**
   - Model learns from truly historical patterns
   - Predictions use only information available at contact time

---

## 🔍 **Comparison with V6 Approach**

The **V6_Historical_Data_Processing_Guide.md** shows a much better approach:

✅ **V6 Approach (Correct):**
- Uses temporal split
- Point-in-time feature joins
- Right-censoring window
- Proper target labeling with 30-day window
- Stable vs. Mutable feature classification

❌ **FinalLeadScorePipeline.ipynb (Current):**
- Random split
- Current snapshot for all leads
- No right-censoring
- Simple target creation
- No temporal validation

**Recommendation:** Use the V6 approach as the foundation for future models.

---

## 📝 **Conclusion**

The FinalLeadScorePipeline.ipynb model was trained on a **static dataset with significant data leakage**. The model likely performs better than it should due to:

1. Seeing future data patterns (random split)
2. Learning test distribution (preprocessing leakage)
3. Using incorrect labels (no temporal validation)
4. Using future information (static dataset)

**This model should NOT be used in production without fixing these issues first.**

The V6 approach addresses all these concerns and should be the standard going forward.

