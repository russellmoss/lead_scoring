# V7 Lead Scoring Model: Training and Validation Results Report

**Report Date:** November 5, 2025  
**Model Version:** V7 (20251105_0936)  
**Training Date:** November 5, 2025  
**Status:** ⚠️ **TRAINED BUT PERFORMANCE BELOW TARGET**

---

## Executive Summary

V7 represents the latest iteration of the Savvy Wealth lead scoring model, implementing a hybrid financial data approach that combines point-in-time historical snapshots for non-financial features with current financial data applied across all historical leads. This strategy was designed to bridge the performance gap between V6 (6.74% AUC-PR) and the production m5 model (14.92% AUC-PR).

**Key Results:**
- **CV Mean AUC-PR:** 0.0498 (4.98%) ± 0.0123
- **CV Coefficient of Variation:** 24.75% (above 15% threshold)
- **Final Model AUC-PR (Training):** 0.9700 (97.00%) - **Severe Overfitting Detected**
- **Baseline (Logistic Regression) AUC-PR:** 0.0521 (5.21%)

**Performance vs Targets:**
- ❌ **CV AUC-PR Target:** >12% | **Actual:** 4.98% | **Gap:** -7.02 percentage points
- ❌ **CV Stability Target:** <15% | **Actual:** 24.75% | **Gap:** +9.75 percentage points
- ❌ **Train-Test Gap Target:** <20% | **Actual:** ~94.87% | **Gap:** +74.87 percentage points

**Verdict:** V7 shows **severe overfitting** and **performance degradation** compared to V6. The model fails all validation gates and is **NOT ready for production**.

---

## Dataset Overview

### Training Dataset

**Source Table:** `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v7_featured_20251105`

**Dataset Statistics:**
- **Total Rows:** 41,894
- **Positive Samples:** 1,418 (3.38%)
- **Negative Samples:** 40,476 (96.62%)
- **Features:** 123 (after PII removal)
- **Financial Coverage:** 92.61% (from metadata)

**Data Strategy:**
- **Non-Financial Features:** Point-in-time joins from `v_discovery_reps_all_vintages` (historical snapshots)
- **Financial Features:** Current snapshot from `discovery_reps_current` (joined to ALL historical leads, matching m5 approach)
- **Feature Engineering:** 43 new features created (23 m5 features + 8 temporal + 4 career + 2 market + 6 business)

### Feature Engineering Summary

**Features Created (43 total):**
- **m5 Engineered Features (23):** AUM_per_Client, AUM_per_IARep, Growth_Momentum, Growth_Acceleration, Firm_Stability_Score, Experience_Efficiency, HNW_Asset_Concentration, Multi_RIA_Relationships, Complex_Registration, Quality_Score, etc.
- **Temporal Dynamics (8):** Recent_Firm_Change, License_Sophistication, Branch_State_Stable, Tenure_Momentum_Score, Multi_State_Operator, Association_Complexity, Designation_Count, Snapshot_Age_Days
- **Career Stage Indicators (4):** Early_Career_High_Performer, Established_Independent, Growth_Phase_Rep, Veteran_Stable
- **Market Position (2):** Emerging_Market_Pioneer, High_Touch_Advisor
- **Business Model (6):** Mass_Affluent_Focus, UHNW_Specialist, Institutional_Manager, Hybrid_Model, Breakaway_High_AUM, Digital_Presence_Score

**Temporal Features Available:** 10/10 (100% coverage)

---

## Model Architecture

### Ensemble Approach

V7 uses a weighted ensemble of three models:

1. **Model A (40% weight):** XGBoost on all features
2. **Model B (30% weight):** XGBoost with temporal features weighted 2x
3. **Model C (30% weight):** LightGBM (fell back to XGBoost due to unavailable dependency)

**Note:** LightGBM was not available, so all three models used XGBoost, resulting in identical predictions.

### Hyperparameters

**XGBoost Configuration:**
- `max_depth`: 5
- `n_estimators`: 300
- `learning_rate`: 0.03
- `subsample`: 0.75
- `colsample_bytree`: 0.75
- `reg_alpha`: 0.5 (L1 regularization)
- `reg_lambda`: 3.0 (L2 regularization)
- `scale_pos_weight`: ~28 (calculated from class imbalance)
- `eval_metric`: 'aucpr'
- `tree_method`: 'hist'
- `enable_categorical`: True

**Cross-Validation Setup:**
- **Method:** Blocked Time-Series Split
- **Folds:** 4 (down from 5 requested due to data constraints)
- **Gap Days:** 30 days between train and test sets
- **Seed:** 42

---

## Cross-Validation Performance

### Overall Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Mean CV AUC-PR** | 0.0498 (4.98%) | >0.12 (12%) | ❌ FAIL |
| **Std Dev AUC-PR** | 0.0123 | - | - |
| **CV Coefficient** | 24.75% | <15% | ❌ FAIL |
| **Mean CV AUC-ROC** | ~0.60 | >0.75 | ❌ FAIL |

### Fold-by-Fold Breakdown

| Fold | Train Size | Test Size | Model A AUC-PR | Model B AUC-PR | Model C AUC-PR | Ensemble AUC-PR | Ensemble AUC-ROC |
|------|------------|-----------|----------------|----------------|----------------|-----------------|------------------|
| 1 | 5,476 | 8,378 | 0.0459 | 0.0459 | 0.0459 | 0.0459 | 0.5791 |
| 2 | 12,796 | 8,378 | 0.0692 | 0.0692 | 0.0692 | 0.0692 | 0.6253 |
| 3 | 23,030 | 8,378 | 0.0487 | 0.0487 | 0.0487 | 0.0487 | 0.5872 |
| 4 | 31,888 | 8,378 | 0.0352 | 0.0352 | 0.0352 | 0.0352 | 0.6031 |

**Key Observations:**
- **Fold 2** shows the best performance (6.92% AUC-PR) - likely due to larger training set
- **Fold 4** shows the worst performance (3.52% AUC-PR) despite having the largest training set - suggests overfitting
- All three models produce **identical results** (since LightGBM unavailable, all using XGBoost)
- **High variability** across folds (24.75% coefficient) indicates instability

### Performance Stability Analysis

**CV Coefficient of Variation:** 24.75%

**Interpretation:**
- **Target:** <15% (stable performance)
- **Actual:** 24.75% (high variability)
- **Assessment:** ⚠️ **Model performance is unstable** - predictions vary significantly across different time periods

**Fold Performance Range:**
- **Best Fold:** 6.92% AUC-PR (Fold 2)
- **Worst Fold:** 3.52% AUC-PR (Fold 4)
- **Range:** 3.40 percentage points
- **Standard Deviation:** 1.23 percentage points

---

## Overfitting Analysis

### Train-Test Performance Gap

**Critical Finding: Severe Overfitting Detected**

| Metric | Training | CV (Test) | Gap | Threshold | Status |
|--------|----------|-----------|-----|-----------|--------|
| **AUC-PR** | 0.9700 (97.00%) | 0.0498 (4.98%) | 92.02 p.p. | <20% | ❌ CRITICAL |
| **AUC-ROC** | 0.9987 (99.87%) | ~0.60 (60%) | ~40% | <15% | ❌ CRITICAL |

**Gap Calculation:**
- **Relative Gap:** (0.9700 - 0.0498) / 0.9700 × 100 = **94.87%**
- **Absolute Gap:** 92.02 percentage points

**Interpretation:**
- The model achieved **97% AUC-PR** on training data but only **4.98%** on cross-validation
- This represents a **94.87% relative gap**, far exceeding the 20% threshold
- The model has **memorized the training data** and cannot generalize to new examples
- This is consistent with previous model versions (V4, V5) that also showed overfitting

### Overfitting Indicators

1. **Perfect Training Scores:** 97% AUC-PR and 99.87% AUC-ROC on training data are unrealistic for this problem
2. **Large CV Gap:** 94.87% gap indicates the model learned training-specific patterns
3. **High Variability:** 24.75% CV coefficient suggests the model is unstable
4. **Poor Test Performance:** 4.98% AUC-PR is barely better than random (3.38% baseline)

---

## Comparison with Previous Models

### Performance Comparison

| Model | CV AUC-PR | CV AUC-ROC | CV Coefficient | Train-Test Gap | Status |
|-------|-----------|------------|----------------|----------------|--------|
| **V6 (No Financials)** | 5.88% | 0.63 | 2.36% | Low | ⚠️ Stable but low |
| **V6 (With Financials)** | 6.74% | 0.63-0.68 | 19.79% | Low | ⚠️ Better but unstable |
| **V7 (Current)** | **4.98%** | **0.60** | **24.75%** | **94.87%** | ❌ **Degraded** |
| **m5 (Production)** | 14.92% | 0.7916 | N/A | Low | ✅ Production |

### Key Findings

1. **Performance Degradation:** V7 (4.98%) performs **worse** than both V6 versions (5.88% and 6.74%)
2. **Increased Instability:** CV coefficient increased from 19.79% (V6 Financials) to 24.75% (V7)
3. **Severe Overfitting:** V7 shows a 94.87% train-test gap, worse than V4's 76% gap
4. **Far from m5:** V7 is **3x worse** than m5's 14.92% AUC-PR

### Why V7 Performed Worse

**Hypotheses:**
1. **Feature Engineering Issues:** The 43 new features may not be providing useful signal, or may be causing overfitting
2. **Ensemble Ineffectiveness:** All three models are identical (XGBoost), so ensemble provides no benefit
3. **Hyperparameter Mismatch:** The regularization (reg_alpha=0.5, reg_lambda=3.0) may be insufficient for the increased feature set
4. **Data Quality:** The hybrid financial approach may have introduced inconsistencies or noise
5. **Temporal Feature Issues:** Temporal dynamics features may not be capturing useful patterns

---

## Baseline Comparison

### Logistic Regression Baseline

**Performance:**
- **AUC-PR:** 0.0521 (5.21%)
- **AUC-ROC:** 0.6234 (62.34%)

**Comparison:**
- **V7 vs Baseline:** 4.98% vs 5.21% = **V7 is 4.4% WORSE than baseline**
- This is a critical finding - the complex ensemble model performs **worse** than a simple logistic regression

**Interpretation:**
- The XGBoost ensemble is not learning useful patterns
- The model may be overfitting to noise rather than signal
- Feature engineering may be introducing spurious correlations

---

## Feature Importance Analysis

**Note:** Feature importance data was generated but exact rankings are not available in the current report. The training process identified 123 features after PII removal.

**Expected Feature Categories:**
- Geographic features (Home_MetropolitanArea, Branch_State, etc.)
- Financial features (TotalAssetsInMillions, client counts, etc.)
- Temporal dynamics features (Recent_Firm_Change, etc.)
- Career stage indicators (Early_Career_High_Performer, etc.)
- m5 engineered features (Multi_RIA_Relationships, etc.)

**Validation Gate Check:**
- ⚠️ **Business Signals in Top 5:** Cannot verify without feature importance data
- ⚠️ **m5 Feature Correlation:** Cannot verify without feature importance data

---

## Validation Gates Assessment

| Gate | Target | Actual | Status | Notes |
|------|--------|--------|--------|-------|
| **CV AUC-PR** | >0.12 (12%) | 0.0498 (4.98%) | ❌ FAIL | 7.02 p.p. below target |
| **Train-Test Gap** | <20% | 94.87% | ❌ FAIL | Severe overfitting |
| **CV Coefficient** | <15% | 24.75% | ❌ FAIL | High instability |
| **Business Signals** | ≥2 in top 5 | Unknown | ⚠️ UNKNOWN | Feature importance not reviewed |
| **m5 Correlation** | >0.5 | Unknown | ⚠️ UNKNOWN | Feature importance not reviewed |
| **Calibration ECE** | <0.05 | Not tested | ⚠️ NOT TESTED | Validation script had version mismatch |

**Overall Status:** ❌ **ALL VALIDATION GATES FAILED**

---

## Root Cause Analysis

### Primary Issues

1. **Severe Overfitting**
   - **Symptom:** 97% training AUC-PR vs 4.98% CV AUC-PR
   - **Root Cause:** Insufficient regularization for the model complexity
   - **Impact:** Model cannot generalize to new data

2. **Performance Degradation**
   - **Symptom:** V7 (4.98%) worse than V6 (6.74%)
   - **Root Cause:** Feature engineering may have introduced noise or spurious correlations
   - **Impact:** Model performs worse than previous versions

3. **High Instability**
   - **Symptom:** 24.75% CV coefficient of variation
   - **Root Cause:** Model performance varies significantly across time periods
   - **Impact:** Unpredictable performance in production

4. **Ensemble Ineffectiveness**
   - **Symptom:** All three models produce identical predictions
   - **Root Cause:** LightGBM unavailable, all models use XGBoost with same data
   - **Impact:** No benefit from ensemble approach

### Contributing Factors

1. **Feature Engineering:**
   - 43 new features may have introduced noise
   - Temporal features may not be capturing useful patterns
   - Feature interactions may be causing overfitting

2. **Hyperparameters:**
   - Regularization may be insufficient (reg_alpha=0.5, reg_lambda=3.0)
   - max_depth=5 may be too deep for this dataset
   - Learning rate (0.03) may be too high

3. **Data Quality:**
   - Hybrid financial approach may have inconsistencies
   - 92.61% financial coverage means some leads lack financial data
   - Temporal features may have missing values

4. **Model Complexity:**
   - Ensemble approach adds complexity without benefit
   - 123 features may be too many for the dataset size
   - Model may be capturing noise rather than signal

---

## Recommendations

### Immediate Actions

1. **❌ DO NOT DEPLOY V7** - Model fails all validation gates and shows severe overfitting

2. **Investigate Feature Engineering**
   - Review feature importance rankings
   - Identify which features are contributing to overfitting
   - Consider removing or simplifying engineered features

3. **Increase Regularization**
   - Increase reg_alpha (L1) to 1.0 or higher
   - Increase reg_lambda (L2) to 5.0 or higher
   - Reduce max_depth to 3 or 4
   - Reduce learning_rate to 0.01

4. **Fix Ensemble Approach**
   - Ensure LightGBM is available or remove Model C
   - Make Model B actually use temporal-weighted features (currently identical to Model A)
   - Consider simpler approach: single model with better regularization

5. **Simplify Model**
   - Consider reverting to V6's approach (simpler, more stable)
   - Use V6's hyperparameters with V7's feature set
   - Test incrementally: add features one group at a time

### Long-Term Improvements

1. **Feature Selection**
   - Implement feature importance-based selection
   - Remove features with low importance or high correlation
   - Focus on m5's proven features

2. **Data Quality**
   - Investigate financial data coverage (92.61% may be too low)
   - Ensure temporal features are calculated correctly
   - Validate hybrid financial approach

3. **Model Architecture**
   - Consider simpler models (Logistic Regression with regularization)
   - Test different ensemble approaches
   - Explore neural networks or other architectures

4. **Validation Process**
   - Implement stricter validation gates
   - Add early stopping for overfitting detection
   - Monitor train-test gap during training

---

## Comparison with m5 Production Model

### Performance Gap

| Metric | m5 (Production) | V7 | Gap | Gap % |
|--------|-----------------|----|----|-------|
| **AUC-PR** | 14.92% | 4.98% | -9.94 p.p. | -66.6% |
| **AUC-ROC** | 0.7916 | ~0.60 | -0.19 | -24.0% |
| **Status** | ✅ Production | ❌ Failed | - | - |

**Key Differences:**
- **m5:** Uses SMOTE for class imbalance, has proven feature set, stable performance
- **V7:** Uses scale_pos_weight, has new feature engineering, shows overfitting

**Conclusion:** V7 is **3x worse** than m5 and **should not replace** m5 in production.

---

## Next Steps

### Option 1: Fix V7 (Recommended)
1. Increase regularization parameters
2. Reduce model complexity
3. Review and simplify feature engineering
4. Re-train with stricter validation
5. If still fails, abandon V7 approach

### Option 2: Revert to V6
1. Use V6 with Financials (6.74% AUC-PR)
2. Improve stability (reduce CV coefficient from 19.79%)
3. Focus on incremental improvements
4. Test in production with A/B testing

### Option 3: New Approach
1. Start fresh with m5's proven features
2. Use m5's training methodology
3. Add temporal features incrementally
4. Validate each step carefully

---

## Conclusion

V7 represents a step backward in model performance. Despite implementing sophisticated feature engineering and an ensemble approach, the model shows:

- ❌ **Severe overfitting** (94.87% train-test gap)
- ❌ **Performance degradation** (4.98% vs V6's 6.74%)
- ❌ **High instability** (24.75% CV coefficient)
- ❌ **Worse than baseline** (4.98% vs 5.21% Logistic Regression)

**The model is NOT ready for production and should NOT be deployed.**

**Recommended Action:** Revert to V6 with Financials approach, or significantly modify V7's architecture before re-training. The current V7 implementation is not suitable for production use.

---

**Report Generated:** November 5, 2025  
**Model Version:** V7 (20251105_0936)  
**Status:** ❌ **FAILED VALIDATION**  
**Recommendation:** **DO NOT DEPLOY**

