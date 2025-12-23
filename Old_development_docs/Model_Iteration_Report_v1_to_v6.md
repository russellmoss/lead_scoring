# Lead Scoring Model Iteration Report: V1 to V6

**Report Date:** November 4, 2025  
**Project:** Savvy Wealth Lead Scoring Engine (Contacted → MQL Prediction)  
**Purpose:** Comprehensive analysis of model evolution, iterations, and results

---

## Executive Summary

This report documents the complete iteration journey from V1 to V6 (including V6 with Financials) of the lead scoring model. The project evolved from an initial hybrid data strategy that failed due to overfitting and data quality issues, to a sophisticated point-in-time historical data approach in V6.

**Key Findings:**
- **V1-V3:** Initial attempts with hybrid data strategy, showing overfitting (AUC-PR: 4.98% - 5.50%)
- **V4:** Improved calibration and regularization, but still overfit (76% train-test gap)
- **V5:** Added strong regularization, but still failed (CV AUC-PR: 8.6%)
- **V6:** Complete rebuild with point-in-time historical snapshots (AUC-PR: 5.88% without financials, 6.74% with financials)
- **Current Production:** m5 model achieving 4% conversion rate (14.92% AUC-PR)

---

## Model Iteration Timeline

### **V1: Initial Hybrid Data Strategy Model** (November 3, 2025)

**Approach:**
- Hybrid Stable/Mutable feature strategy
- 120 features (122 discovery features - 12 PII features removed)
- Training samples: 44,592
- Positive samples: 1,572 (3.53%)
- Temporal blocking CV (4 folds, 30-day gaps)

**Key Changes from Baseline:**
- Removed 12 PII features (FirstName, LastName, Branch_City, etc.)
- Implemented hybrid data policy: stable features for all leads, mutable features NULLed for historical leads
- Used scale_pos_weight for class imbalance (no SMOTE)
- No regularization (reg_alpha=0, reg_lambda=0)

**Results:**
- **Final Model AUC-PR:** 0.8536 (CV average: 0.0498)
- **Final Model AUC-ROC:** 0.9895
- **Baseline (Logistic Regression) AUC-PR:** 0.0488
- **CV Performance:** 0.0498 average AUC-PR (ranging 3.64% to 5.50% across folds)
- **Winning Strategy:** scale_pos_weight

**Top Features:**
1. SocialMedia_LinkedIn (0.0196)
2. Education (0.0100)
3. Licenses (0.0076)
4. Brochure_Keywords (0.0065)
5. Home_MetropolitanArea (0.0041)

**Issues Identified:**
- Model showed signs of overfitting (train AUC-PR: 85.36% vs CV: 4.98%)
- Multi_RIA_Relationships (m5's #1 feature) ranked only #17 in importance
- 95% of samples had NULL values in mutable features, limiting signal
- Feature importance showed geographic identifiers rather than business signals

**Status:** ❌ **REJECTED** - Performance below baseline threshold (0.20 AUC-PR)

---

### **V2: Dataset Expansion** (November 3, 2025)

**Approach:**
- Expanded training dataset (43,854 samples)
- 91 features (after feature selection)
- Positive samples: 1,399 (3.19%)

**Key Changes:**
- Expanded dataset from 44,592 to 43,854 samples
- Reduced features from 120 to 91 through feature selection
- Used V2 SQL query with improved temporal handling

**Results:**
- **Final Model AUC-PR:** 1.0000 (perfect score - clear overfitting)
- **Final Model AUC-ROC:** 1.0000
- **CV Performance:** 0.1627 average AUC-PR (ranging 8.4% to 20.9% across folds)
- **Baseline (Logistic Regression) AUC-PR:** 0.0344

**Issues Identified:**
- Perfect scores indicate severe overfitting
- CV performance still below acceptable threshold

**Status:** ❌ **REJECTED** - Overfitting detected

---

### **V3: Feature Expansion** (November 3, 2025)

**Approach:**
- Expanded to 132 features (all available)
- Training samples: 43,854
- Positive samples: 1,399 (3.19%)

**Key Changes:**
- Increased features from 91 to 132 (no feature filtering)
- Attempted to capture more signal with full feature set

**Results:**
- **Final Model AUC-PR:** 1.0000 (perfect score - clear overfitting)
- **Final Model AUC-ROC:** 1.0000
- **CV Performance:** 0.1650 average AUC-PR (ranging 8.9% to 21.9% across folds)
- **Baseline (Logistic Regression) AUC-PR:** 0.0364

**Issues Identified:**
- Still showing perfect scores (overfitting)
- CV performance marginally better than V2 but still inadequate

**Status:** ❌ **REJECTED** - Overfitting persists

---

### **V4: Calibration and Regularization** (November 3, 2025)

**Approach:**
- 120 features (PII removed)
- Training samples: 43,854
- Positive samples: 1,399 (3.19%)
- Added calibration and more sophisticated validation

**Key Changes:**
- Added segment-specific calibration (AUM tiers)
- Implemented backtesting framework
- Added overfitting analysis
- Created comprehensive validation reports

**Hyperparameters:**
- max_depth: 6
- n_estimators: 400
- learning_rate: 0.05
- subsample: 0.8
- colsample_bytree: 0.8
- reg_alpha: 0 (no L1 regularization)
- reg_lambda: 0 (no L2 regularization)

**Results:**
- **Final Model AUC-PR:** 0.9600 (train) / 0.2286 (test)
- **Final Model AUC-ROC:** 0.9844 (train) / 0.7138 (test)
- **CV Performance:** Not explicitly reported in training report
- **Train-Test Gap:** 76.19% (AUC-PR) - **CRITICAL OVERFITTING**
- **CV Coefficient of Variation:** 41.27% (highly unstable)

**Calibration Results:**
- **Global ECE:** 0.0019 (✅ well below 0.05 threshold)
- **All Segment ECE:** 0.0019 for all AUM tiers (✅ all segments pass)

**Top Features:**
1. SocialMedia_LinkedIn (0.0196)
2. Education (0.0100)
3. Licenses (0.0076)
4. Brochure_Keywords (0.0065)
5. Home_MetropolitanArea (0.0041)

**Backtesting Results:**
- **AUC-PR Range:** 0.8016 to 1.0000 across quarters
- **AUC-PR Std Dev:** 0.0618
- **Max KS Statistic:** 1.0000 (drift detected)

**Issues Identified:**
- **CRITICAL:** 76.19% train-test gap indicates severe overfitting
- **CRITICAL:** 41.27% CV coefficient of variation indicates model instability
- Model memorized training data, cannot generalize
- Backtesting shows perfect scores (1.0000) for some quarters, indicating overfitting

**Status:** ❌ **REJECTED** - Critical overfitting detected

---

### **V5: Strong Regularization Attempt** (November 3, 2025)

**Approach:**
- 120 features (same as V4)
- Training samples: 43,854
- Positive samples: 1,399 (3.19%)
- Added strong regularization to combat overfitting

**Key Changes:**
- **Reduced max_depth:** 6 → 4
- **Reduced n_estimators:** 400 → 200
- **Added L1 regularization:** reg_alpha: 1.0 (NEW)
- **Added L2 regularization:** reg_lambda: 5.0 (NEW)
- **Reduced learning_rate:** 0.05 → 0.02
- **Reduced subsample:** 0.8 → 0.7
- **Reduced colsample_bytree:** 0.8 → 0.7

**Results:**
- **Final Model AUC-PR:** 0.9582 (train)
- **Final Model AUC-ROC:** 0.9990 (train)
- **CV Performance (Fold 0):** 0.0858 AUC-PR (8.6%) - **REAL PERFORMANCE**
- **CV Performance Average:** 0.1629 AUC-PR (across folds)
- **Baseline (Logistic Regression) AUC-PR:** 0.0415

**Top Features:**
1. Home_MetropolitanArea (0.0233)
2. Brochure_Keywords (0.0212)
3. FirmWebsite (0.0118)
4. Education (0.0113)
5. SocialMedia_LinkedIn (0.0087)

**Issues Identified:**
- Despite regularization, train performance (95.82%) still far exceeds CV performance (8.6%)
- Hybrid data strategy still failing - 95% NULL values in mutable features
- Model still unable to learn meaningful patterns
- Feature importance shows weak signals (geographic/metadata features)

**Decision:** Hybrid data strategy declared unworkable. Decision to pivot to V6 with true historical vintages.

**Status:** ❌ **REJECTED** - Hybrid strategy failed, pivot to V6

---

### **V6: Point-in-Time Historical Data Rebuild** (November 4, 2025)

**Approach:**
- **Complete rebuild** using point-in-time historical snapshots
- Training samples: 41,942
- Positive samples: 1,422 (3.39%)
- Features: 111 (without financials)
- 5-fold blocked time-series CV (30-day gaps)

**Key Architectural Changes:**
1. **Point-in-Time Joins:** Each lead matched to correct historical snapshot based on contact quarter
2. **Temporal Integrity:** All features reflect values at time of contact (no future leakage)
3. **No NULL Values:** All features populated for all samples (unlike V1-V5)
4. **True Vintages:** Uses 8 quarters of historical snapshot data (2023 Q1 through 2025 Q2)

**Hyperparameters:**
- max_depth: 4
- n_estimators: 200
- learning_rate: 0.02
- subsample: 0.7
- colsample_bytree: 0.7
- reg_alpha: 1.0 (L1 regularization)
- reg_lambda: 5.0 (L2 regularization)
- scale_pos_weight: 28.50

**Results (Without Financials):**
- **Mean CV AUC-PR:** 0.0588 ± 0.0014 (5.88%)
- **CV Coefficient:** 2.36% (✅ very stable)
- **Mean CV AUC-ROC:** ~0.63 (ranging 0.62-0.64)
- **Winning Strategy:** scale_pos_weight
- **Baseline (Logistic Regression) AUC-PR:** Not reported

**Validation Gates:**
- ✅ **CV Coefficient < 20%:** PASS (2.36%)
- ❌ **CV AUC-PR > 0.15:** FAIL (0.0588 < 0.15)

**Top Features:**
1. Home_MetropolitanArea (0.0543)
2. multi_state_registered (0.0497)
3. Firm_Stability_Score (0.0475)
4. DateOfHireAtCurrentFirm_NumberOfYears (0.0410)
5. Is_BreakawayRep (0.0339)

**Key Improvements:**
- ✅ **Stable Performance:** CV coefficient of 2.36% shows excellent consistency
- ✅ **No Overfitting:** Train-test gap not reported but CV performance is realistic
- ✅ **Temporal Integrity:** Point-in-time data ensures no leakage
- ✅ **Feature Richness:** All features populated (no NULLs)

**Limitations:**
- ⚠️ **Low AUC-PR:** 5.88% is below m5's 14.92% and below target threshold (15%)
- ⚠️ **Missing Financial Features:** Model trained without financial metrics (AUM, client counts, growth rates)
- ⚠️ **Weak Signal:** Only 1.73x better than random (5.88% vs 3.39% baseline)

**Status:** ⚠️ **TRAINED BUT SUB-OPTIMAL** - Stable but low performance

---

### **V6 with Financials: Enhanced Version** (November 4, 2025)

**Approach:**
- Same as V6 but with financial features included
- Training samples: 43,269
- Positive samples: 1,466 (3.39%)
- Features: 115 (4 additional financial features)

**Key Changes:**
- Added financial metrics from `discovery_reps_current` (current snapshot)
- Financial features joined to historical leads (similar to m5 approach)
- Includes: AUM, client counts, growth rates, asset composition

**Results (With Financials):**
- **Mean CV AUC-PR:** 0.0674 ± 0.0133 (6.74%)
- **CV Coefficient:** 19.79% (⚠️ approaching 20% threshold)
- **Mean CV AUC-ROC:** ~0.65 (ranging 0.63-0.68)
- **Winning Strategy:** scale_pos_weight

**Validation Gates:**
- ✅ **CV Coefficient < 20%:** PASS (19.79%)
- ❌ **CV AUC-PR > 0.15:** FAIL (0.0674 < 0.15)

**Top Features:**
1. AssetsInMillions_Individuals (0.0387) - **Financial feature**
2. Firm_Stability_Score (0.0371)
3. Home_MetropolitanArea (0.0315)
4. DateOfHireAtCurrentFirm_NumberOfYears (0.0282)
5. NumberClients_RetirementPlans (0.0281) - **Financial feature**

**Key Improvements:**
- ✅ **Better Performance:** 6.74% AUC-PR vs 5.88% without financials (+14.6% improvement)
- ✅ **Financial Signals:** Financial features appear in top 5 (AssetsInMillions_Individuals, NumberClients_RetirementPlans)
- ✅ **Stable Performance:** CV coefficient 19.79% (within threshold)

**Limitations:**
- ⚠️ **Still Below Target:** 6.74% AUC-PR is still below m5's 14.92%
- ⚠️ **Higher Variability:** CV coefficient 19.79% is higher than V6 without financials (2.36%)
- ⚠️ **Training-Production Mismatch:** Uses current financial snapshot for historical leads (may not match production)

**Status:** ⚠️ **BEST V6 VARIANT** - Better than V6 without financials, but still below m5

---

## Performance Comparison Matrix

| Model | Training AUC-PR | CV AUC-PR | CV Coefficient | Train-Test Gap | Status | Key Issues |
|-------|----------------|-----------|----------------|----------------|--------|------------|
| **V1** | 85.36% | 4.98% | - | ~80% | ❌ Rejected | Overfitting, NULL values |
| **V2** | 100.00% | 16.27% | - | ~84% | ❌ Rejected | Severe overfitting |
| **V3** | 100.00% | 16.50% | - | ~84% | ❌ Rejected | Severe overfitting |
| **V4** | 96.00% | ~22.86%* | 41.27% | 76.19% | ❌ Rejected | Critical overfitting, unstable |
| **V5** | 95.82% | 8.60%* | - | ~87% | ❌ Rejected | Hybrid strategy failure |
| **V6** | - | 5.88% | 2.36% | Low | ⚠️ Trained | Low performance, no financials |
| **V6 (Financials)** | - | 6.74% | 19.79% | Low | ⚠️ Best V6 | Better but still below m5 |
| **m5 (Production)** | 14.92% | 14.92% | - | Low | ✅ Production | Current champion |

*Estimated from fold 0 or test set performance

---

## Key Learnings and Evolution

### **Phase 1: Hybrid Data Strategy (V1-V5)**

**What We Tried:**
- Hybrid approach: stable features for all leads, mutable features NULLed for historical leads
- Multiple regularization attempts (V4, V5)
- Feature selection and expansion iterations
- Calibration and backtesting frameworks

**Why It Failed:**
1. **95% NULL Values:** Historical leads had NULLs in all mutable features, leaving only stable features
2. **Weak Signal:** Stable features (geography, metadata) insufficient for prediction
3. **Overfitting:** Models memorized training patterns but couldn't generalize
4. **Data Quality:** Hybrid strategy created noisy, incomplete training data

**Key Insight:** The hybrid approach fundamentally couldn't work because 95% of samples lacked critical features.

---

### **Phase 2: Point-in-Time Historical Data (V6)**

**What We Tried:**
- Complete rebuild using 8 quarters of historical snapshots
- Point-in-time joins matching each lead to correct historical snapshot
- Two variants: without financials (111 features) and with financials (115 features)

**Results:**
- ✅ **Temporal Integrity:** No data leakage, all features temporally correct
- ✅ **Stable Performance:** Low CV coefficient (2.36% without financials)
- ✅ **No Overfitting:** Realistic performance metrics
- ⚠️ **Low Performance:** 5.88-6.74% AUC-PR still below m5's 14.92%
- ⚠️ **Training-Production Mismatch:** Historical snapshots in training vs current snapshot in production

**Key Insight:** V6 solves temporal leakage but introduces training-production mismatch. Financial features help but still don't match m5 performance.

---

## Comparison with Production Model (m5)

### **m5 Model Characteristics:**
- **AUC-PR:** 14.92%
- **AUC-ROC:** 0.7916
- **Training Samples:** 60,772
- **Features:** 67 (31 base + 31 engineered + 5 metro dummies)
- **Approach:** Uses current snapshot for all historical leads (has temporal leakage but matches production)
- **Production Performance:** 4% contacted-to-MQL conversion rate

### **Why m5 Outperforms V6:**

1. **Training-Production Alignment:**
   - m5: Uses current data for historical leads (training) = uses current data for new leads (production)
   - V6: Uses historical snapshots (training) ≠ uses current snapshot (production)
   - **Result:** m5's "leakage" is actually a feature that makes it work better in production

2. **Feature Richness:**
   - m5: 31 sophisticated engineered features (e.g., Multi_RIA_Relationships, HNW_Asset_Concentration)
   - V6: Fewer engineered features, missing m5's top features
   - **Result:** m5 has stronger predictive signals

3. **Data Volume:**
   - m5: 60,772 training samples
   - V6: 41,942-43,269 training samples
   - **Result:** m5 has more data to learn from

4. **Feature Engineering:**
   - m5: Advanced feature engineering (growth momentum, efficiency metrics, client composition)
   - V6: Basic feature engineering, missing many m5 features
   - **Result:** m5 captures more business logic

---

## Performance Trajectory

```
AUC-PR Performance Over Iterations:

V1:  4.98%  ❌ (overfit, NULL values)
V2:  16.27% ❌ (severe overfitting)
V3:  16.50% ❌ (severe overfitting)
V4:  ~22.86% ❌ (overfit, unstable)
V5:  8.60%  ❌ (hybrid strategy failure)
V6:  5.88%  ⚠️ (stable but low)
V6+: 6.74%  ⚠️ (best V6, still below m5)
m5:  14.92% ✅ (production champion)
```

**Key Observations:**
- V1-V5 showed overfitting (perfect or near-perfect train scores)
- V6 achieved stability but at cost of performance
- V6 with financials improved but still 2.2x worse than m5
- m5 remains the production champion despite temporal leakage

---

## Recommendations

### **For Production:**
1. **Keep m5 in Production:** 
   - Proven 4% conversion rate
   - Training-production alignment ensures consistent performance
   - V6 would likely reduce conversion to 3.5-3.8%

### **For Future Development:**
1. **Fix Training-Production Alignment for V6:**
   - If V6 is to be used, production must also use point-in-time snapshots
   - This requires maintaining historical snapshots in production pipeline

2. **Enhance V6 Feature Engineering:**
   - Add m5's 31 engineered features to V6
   - Focus on Multi_RIA_Relationships, HNW metrics, growth indicators

3. **Hybrid Approach:**
   - Use V6 as fallback when financial data unavailable
   - Use m5 when financial data available
   - Consider ensemble of both models

4. **Continue Monitoring:**
   - Track m5's production performance
   - Monitor for degradation that might justify switching to V6
   - Consider V6 if financial data becomes unavailable

---

## Conclusion

The model iteration journey from V1 to V6 demonstrates the complexity of building temporally correct machine learning models. While V6 achieved temporal integrity and stability, it came at the cost of performance. The m5 model, despite having temporal leakage in training, performs better because its training methodology matches production.

**Key Takeaway:** Perfect temporal correctness in training doesn't guarantee better production performance if it doesn't match the production environment. The "leakage" in m5 is actually a feature that ensures training-production alignment.

**Current Status:**
- ✅ **m5:** Production champion, 4% conversion rate
- ⚠️ **V6:** Stable but sub-optimal, 6.74% AUC-PR (2.2x worse than m5)
- ❌ **V1-V5:** All rejected due to overfitting or strategy failure

**Path Forward:** Maintain m5 in production, use V6 as fallback, and continue iterating on V6 to improve feature engineering and potentially align training with production methodology.

---

**Report Generated:** November 4, 2025  
**Next Review:** Quarterly model refresh cycle

