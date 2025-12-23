# Week 4: Model Training Analysis & Recommendations

**Generated:** 2025-11-03  
**Status:** ⚠️ **CRITICAL ISSUES IDENTIFIED**

---

## Executive Summary

Week 4 training completed successfully with model artifacts generated, but **critical performance issues** have been identified that require immediate attention before deployment.

### Key Findings:
1. ✅ Model artifacts created successfully (XGBoost + Baseline Logistic)
2. ⚠️ **CV AUC-PR scores are very low (0.036-0.055)** - indicating poor predictive power
3. 🚨 **Data leakage suspected**: Final model AUC-PR (0.8536) is 15-20x higher than CV scores
4. ✅ Model is significantly better than Logistic Regression baseline (AUC-ROC: 0.99 vs 0.58)
5. ❌ **Model underperforms m5 baseline** (CV AUC-PR: ~0.05 vs m5: 0.1492)

---

## Performance Comparison

### V1 Model (Current Week 4)
| Metric | CV Score (Realistic) | Final Model (Leakage?) | Baseline Logistic |
|--------|---------------------|------------------------|-------------------|
| **AUC-PR** | **0.036-0.055** ⚠️ | 0.8536 🚨 | 0.0488 |
| **AUC-ROC** | ~0.50-0.58 | 0.9895 🚨 | 0.5756 |
| **Training Samples** | 44,592 | 44,592 | 44,592 |
| **Positive Class %** | 3.53% | 3.53% | 3.53% |

### m5 Model (Reference Benchmark)
| Metric | Value |
|--------|-------|
| **AUC-PR** | **0.1492** ✅ |
| **AUC-ROC** | 0.7916 |
| **Training Samples** | 60,772 |
| **Positive Class %** | 3.36% |
| **Top 10% Precision** | 13.23% |
| **Top 10% Lift** | 3.93x |

### Key Differences:
1. **m5 has 36% more training data** (60,772 vs 44,592)
2. **m5 uses SMOTE** with sophisticated feature engineering
3. **m5 uses proper train/test split** (not evaluating on training data)
4. **m5 has better regularization** (reg_alpha=0.5, reg_lambda=2.0, gamma=2)

---

## Critical Issue #1: Data Leakage

### Problem
The final model shows AUC-PR of **0.8536** when evaluated on the full training dataset, but CV folds show **0.036-0.055**. This 15-20x gap indicates **severe data leakage**.

### Root Cause
Looking at the code in `week_4_train_model_v1.py` lines 796-799:
```python
final_preds = final_model.predict_proba(X_all)[:, 1]  # Evaluating on TRAINING data!
final_aucpr = average_precision_score(y_all, final_preds)
```

**The model is being evaluated on the same data it was trained on**, which inflates performance metrics artificially.

### Fix Required
1. **Hold out a test set** (20% of data) before any training or CV
2. **Never use training data for final evaluation**
3. **Report CV scores as primary metrics**, not training set performance

---

## Critical Issue #2: Low CV Performance

### Problem
Cross-validation AUC-PR scores (0.036-0.055) indicate the model has **minimal predictive power**. This is only slightly better than:
- Random baseline: ~0.035 (3.53% positive rate)
- Logistic Regression: 0.0488

### Potential Root Causes

#### 1. **Feature Quality Issues**
Looking at feature importance, top features are:
- `Branch_State` (0.053) - Geographic identifier (potential leakage)
- `DateOfHireAtCurrentFirm_NumberOfYears` (0.033)
- `Custodian1` (0.018)
- `Branch_County`, `Branch_City` (0.014, 0.011) - More geography

**Issue**: Top features are geographic/demographic identifiers rather than business signals. This suggests:
- Core business features (AUM, client metrics) were filtered out too aggressively
- Feature engineering may not be capturing predictive signals

#### 2. **Aggressive Pre-Filtering**
- **18 features removed by IV filter** (< 0.02 threshold)
- Many removed features include core business metrics:
  - `AUMGrowthRate_1Year`, `AUMGrowthRate_5Year`
  - `AUM_Per_Client`, `AUM_Per_BranchAdvisor`
  - `NumberClients_HNWIndividuals`
  - `Multi_RIA_Relationships` (was #1 in m5 model!)

**Critical**: `Multi_RIA_Relationships` had **zero importance** in V1 but was the **#1 feature in m5**. This is a red flag.

#### 3. **Temporal Leakage Prevention Impact**
The Hybrid (Stable/Mutable) approach may be:
- NULLing out too many valuable features for historical leads
- Creating a dataset where predictive signals are diluted
- The 44,592 samples may have insufficient signal density

#### 4. **Class Imbalance Handling**
- `scale_pos_weight=27.37` (27:1 ratio)
- SMOTE failed/underperformed in all folds
- May need more sophisticated imbalance handling

---

## Recommendations for Improvement

### Immediate Actions (Priority 1)

#### 1. **Fix Data Leakage Evaluation**
```python
# BEFORE training, split data
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X_all, y_all, test_size=0.2, random_state=42, stratify=y_all
)

# Train on X_train, evaluate on X_test ONLY
final_model.fit(X_train, y_train)
final_aucpr = average_precision_score(y_test, final_model.predict_proba(X_test)[:, 1])
```

#### 2. **Investigate Feature Removal**
- **Re-examine IV threshold**: 0.02 may be too strict for this imbalanced dataset
- **Analyze why `Multi_RIA_Relationships` was removed**: This was the top feature in m5
- **Check if IV calculation is correct** for highly imbalanced data (3.53% positive)

#### 3. **Compare Feature Sets with m5**
Create a diagnostic script to:
- List features used in m5 vs V1
- Identify features present in m5 but missing/removed in V1
- Re-run IV calculation with m5's feature set

### Short-Term Improvements (Priority 2)

#### 4. **Improve Imbalance Handling**
- Test **SMOTE with different sampling strategies** (m5 used 0.1, we used default)
- Consider **ADASYN** or **BorderlineSMOTE**
- Test **ensemble methods** (EasyEnsemble, BalancedBaggingClassifier)

#### 5. **Feature Engineering Review**
- **Re-examine temporal feature derivation**: `Day_of_Contact` was removed by IV filter - why?
- **Check NULL handling for mutable features**: Are NULLs being used correctly by XGBoost?
- **Review geographic features**: Top importance on `Branch_State` may indicate:
  - Geographic bias in training data
  - Need for geographic normalization
  - Potential leakage (future knowledge about conversion locations)

#### 6. **Hyperparameter Tuning**
Current XGBoost params:
```python
n_estimators=400,
max_depth=6,
learning_rate=0.05,
subsample=0.8,
colsample_bytree=0.8,
# NO regularization!
```

**m5 used stronger regularization**:
```python
n_estimators=600,
max_depth=6,
learning_rate=0.015,  # Lower = more conservative
reg_alpha=0.5,        # L1 regularization
reg_lambda=2.0,       # L2 regularization  
gamma=2,              # Min split loss
colsample_bytree=0.7, # More feature subsampling
colsample_bylevel=0.7,
```

**Recommendation**: Add regularization to prevent overfitting:
```python
reg_alpha=0.5,
reg_lambda=2.0,
gamma=1.0,
min_child_weight=2,
```

### Long-Term Improvements (Priority 3)

#### 7. **Expand Training Dataset**
- Current: 44,592 samples (Hybrid approach)
- m5: 60,772 samples (36% more)
- **Goal**: Phase 1.5 - Source historical snapshots to expand dataset

#### 8. **Revisit Feature Selection Strategy**
- Consider **model-based feature selection** (tree-based importance) instead of IV/VIF
- Use **recursive feature elimination** with XGBoost
- **Feature interaction analysis**: Check if important interactions are being captured

#### 9. **Advanced Modeling Techniques**
- **Calibration**: m5 used `CalibratedClassifierCV` - add this to V1
- **Ensemble methods**: Try combining multiple models
- **Cost-sensitive learning**: Adjust for business costs (false positives vs false negatives)

---

## Model Comparison: V1 vs m5 vs Baseline

| Model | AUC-PR | AUC-ROC | Training N | Key Features | Notes |
|-------|--------|---------|------------|--------------|-------|
| **V1 XGBoost (CV)** | **0.036-0.055** ❌ | ~0.50-0.58 | 44,592 | 106 features, scale_pos_weight | Current model - poor performance |
| **V1 XGBoost (Train)** | **0.8536** 🚨 | 0.9895 | 44,592 | Same | **Data leakage - invalid** |
| **V1 Logistic** | 0.0488 | 0.5756 | 44,592 | Label encoded | Baseline - slightly better than V1 CV |
| **m5 (Test)** | **0.1492** ✅ | 0.7916 | 60,772 | 67 features, SMOTE+Regularization | Reference benchmark |

**Conclusion**: V1 underperforms m5 by **3-4x** on CV metrics. The model needs significant improvements before it can be considered for deployment.

---

## Action Plan

### Week 4 Immediate Fixes
1. ✅ Fix data leakage evaluation (hold out test set)
2. ✅ Re-run IV calculation with relaxed threshold (0.01 instead of 0.02)
3. ✅ Analyze why `Multi_RIA_Relationships` and other m5 top features were removed
4. ✅ Add regularization parameters to XGBoost
5. ✅ Test SMOTE with sampling_strategy=0.1 (matching m5)

### Week 5 Validation
1. ✅ Re-train model with fixes
2. ✅ Validate on held-out test set
3. ✅ Compare feature importance with m5
4. ✅ Document improvements in AUC-PR

### Week 6 Deployment Readiness
1. ✅ If AUC-PR > 0.10: Proceed with backtesting
2. ✅ If AUC-PR < 0.10: Consider using m5 as interim model while improving V1

---

## Questions for Investigation

1. **Why was `Multi_RIA_Relationships` removed?** 
   - This was the #1 feature in m5 but had zero importance in V1
   - Check if feature exists in BigQuery table
   - Check IV calculation for this specific feature

2. **Why are geographic features dominating?**
   - `Branch_State` is top feature - is this geographic bias or actual signal?
   - Check if conversion rates vary significantly by geography
   - Consider geographic normalization

3. **Is the IV threshold too strict?**
   - 0.02 threshold removed many business metrics
   - For 3.53% positive class, IV may need lower threshold
   - Consider using 0.01 or model-based selection

4. **Are mutable features being used correctly?**
   - NULL values in mutable features for historical leads
   - Verify XGBoost is learning from NULL patterns correctly
   - Check if missingness itself is predictive

---

## Next Steps

1. **Review this report with team**
2. **Prioritize fixes** based on impact and effort
3. **Re-run training** with fixes applied
4. **Re-evaluate** on proper test set
5. **Update development progress** document with findings

---

**Generated by:** Week 4 Training Pipeline Analysis  
**Model Version:** V1  
**Status:** ⚠️ Requires Fixes Before Deployment

