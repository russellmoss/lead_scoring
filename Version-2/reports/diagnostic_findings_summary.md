# Diagnostic Investigation: v3 Performance Regression

**Date:** December 21, 2025  
**Issue:** v3 model (1.46x lift) underperforms v2 model (2.62x lift) despite 4x more training data

---

## 🔴 CRITICAL FINDING #1: CV Fold Distribution Broken

### Problem
**All CV folds 1-4 have ZERO positive examples!**

```
Fold 1: Train=5,122 (0.00% positive), Val=5,121 (0.00% positive) ⚠️
Fold 2: Train=10,243 (0.00% positive), Val=5,121 (0.00% positive) ⚠️
Fold 3: Train=15,364 (0.00% positive), Val=5,121 (0.00% positive) ⚠️
Fold 4: Train=20,485 (0.00% positive), Val=5,121 (0.00% positive) ⚠️
Fold 5: Train=25,606 (0.00% positive), Val=5,121 (21.95% positive) ⚠️
```

### Root Cause
The training data is likely **not sorted by `contacted_date`** when loaded from BigQuery. TimeSeriesSplit assumes data is chronologically ordered, but if it's not, it creates invalid folds.

### Impact
- **All Optuna trials returned identical CV score (0.0439)** because folds 1-4 can't learn (no positives)
- **CV is completely broken** - not a valid evaluation method
- **Hyperparameter tuning is meaningless** - all trials train on the same invalid folds

### Fix Required
1. **Sort data by `contacted_date` BEFORE CV**
2. **Verify fold distribution** - each fold should have ~3.66% positive rate
3. **Re-run Optuna** with properly sorted data

---

## 📊 Performance Comparison

| Model Variant | Test AUC-ROC | Test AUC-PR | Top Decile Lift |
|---------------|--------------|-------------|----------------|
| **Full model (20 features)** | 0.5853 | 0.0562 | **1.46x** |
| **Core model (no data quality)** | 0.5771 | 0.0544 | **1.26x** ❌ |
| **V2 features only (9 features)** | 0.5677 | 0.0495 | **1.40x** |
| **Target (v2 performance)** | ~0.65-0.70 | ~0.07-0.10 | **2.62x** |

### Key Observations

1. **Removing data quality signals HURTS performance** (1.26x < 1.46x)
   - Data quality signals are actually helping, not hurting
   - `has_valid_virtual_snapshot` being #1 feature may be legitimate

2. **V2 features perform slightly better** (1.40x vs 1.26x)
   - But still far below v2's 2.62x target
   - Suggests the issue is NOT just feature engineering

3. **All variants underperform v2**
   - Even with v2's exact feature set, performance is poor
   - This suggests a **data or target variable issue**, not a feature issue

---

## 🔍 Feature Signal Analysis

### Strong Signals (Large Difference Between Pos/Neg)

| Feature | Pos Mean | Neg Mean | Difference | % Diff |
|---------|----------|----------|------------|--------|
| **flight_risk_score** | 63.99 | 8.45 | +55.54 | **+657%** 🔥 |
| is_personal_email_missing | 0.164 | 0.058 | +0.105 | +180% |
| num_prior_firms | 0.845 | 0.310 | +0.535 | +172% |
| **firm_net_change_12mo** | -39.49 | -14.74 | -24.75 | **+168%** 🔥 |
| has_firm_aum | 0.216 | 0.086 | +0.130 | +150% |
| log_firm_aum | 4.89 | 1.99 | +2.89 | +145% |
| has_valid_virtual_snapshot | 0.233 | 0.095 | +0.138 | +145% |
| industry_tenure_months | 64.86 | 27.83 | +37.03 | +133% |
| firm_departures_12mo | 75.66 | 35.59 | +40.07 | +113% |
| current_firm_tenure_months | 13.87 | 7.29 | +6.59 | +90% |

### Protected Features Status

✅ **pit_moves_3yr**: +77.6% difference (positive cases have more moves)  
✅ **firm_net_change_12mo**: +167.9% difference (positive cases at more bleeding firms)  
✅ **flight_risk_score**: +657% difference (HUGE signal!)

**All protected features show strong signals**, but model still performs poorly. This suggests the model isn't learning effectively, possibly due to:
- CV issue preventing proper training
- Class imbalance too severe (26:1 ratio)
- Feature interactions not being captured

---

## ⚠️ Potential Issues

### 1. Data Sorting Issue
- Training data may not be sorted by `contacted_date`
- TimeSeriesSplit requires chronological order
- **FIX: Sort by `contacted_date` before CV**

### 2. Target Variable Definition
- Verify target definition matches v2 exactly
- Check if maturity window changed
- Check if conversion definition changed

### 3. Class Imbalance
- 26:1 ratio is very severe
- `scale_pos_weight = 26.34` may be too high
- Consider stratified sampling or different class weights

### 4. Temporal Distribution
- Early 2024 data may have different characteristics than 2025 data
- Conversion rates vary by month (2.6% to 5.2%)
- Model may be learning time period rather than lead quality

---

## 🎯 Recommended Actions (Priority Order)

### IMMEDIATE (Blocking)

1. **Fix CV Implementation**
   ```python
   # Sort by contacted_date BEFORE CV
   train_df = train_df.sort_values('contacted_date').reset_index(drop=True)
   X_train = prepare_features(train_df, ALL_FEATURES)
   y_train = train_df['target']
   
   # Verify folds have positive examples
   tscv = TimeSeriesSplit(n_splits=5)
   for train_idx, val_idx in tscv.split(X_train):
       assert y_train.iloc[train_idx].sum() > 0, "Train fold has no positives!"
       assert y_train.iloc[val_idx].sum() > 0, "Val fold has no positives!"
   ```

2. **Re-run Optuna with sorted data**
   - Should see variation in CV scores across trials
   - Should find better hyperparameters

### HIGH PRIORITY

3. **Compare target variable definition**
   - Verify v2 vs v3 target calculation matches
   - Check maturity window (30 days in both?)
   - Verify conversion definition (Call Scheduled OR Converted?)

4. **Test with stratified CV**
   - Use StratifiedTimeSeriesSplit if available
   - Or manually ensure each fold has ~3.66% positive rate

### MEDIUM PRIORITY

5. **Investigate temporal patterns**
   - Train separate models for 2024 vs 2025
   - Check if conversion patterns changed over time
   - Verify if early 2024 data quality is different

6. **Feature engineering refinement**
   - `flight_risk_score` shows +657% signal but low importance
   - Consider feature interactions or transformations
   - Test polynomial features for key signals

---

## 📝 Next Steps

**DO NOT proceed to Phase 5/6 until:**

1. ✅ CV issue is fixed and verified
2. ✅ Optuna re-run with sorted data shows variation
3. ✅ Target variable definition verified against v2
4. ✅ New model achieves >2.0x lift on test set

**Expected outcome after fixes:**
- CV scores should vary across Optuna trials
- Model should achieve 2.0-2.5x lift (closer to v2's 2.62x)
- Feature importance should show protected features in top 5

---

## Files Created

- `diagnostic_investigation.json` - Full diagnostic results
- `diagnostic_findings_summary.md` - This summary document

