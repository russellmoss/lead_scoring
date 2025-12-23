# V6 Training Dataset - NULL Analysis & Data Quality Assessment

**Generated:** November 4, 2025  
**Dataset:** `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_20251104_2217`  
**Total Samples:** 41,942

---

## Executive Summary

✅ **GOOD NEWS:** We have sufficient data quality for model training. The NULLs are primarily:
1. **Expected NULLs:** Financial metrics (0% coverage) - intentionally set to NULL because `RIARepDataFeed` files don't contain financial data
2. **Sparse but usable:** Some geographic features (Home_State 52.9%, MilesToWork 38.7%) - XGBoost handles missing values well
3. **High coverage:** Core features (97.7%+ coverage) - tenure, licenses, firm data, engineered features

**XGBoost handles NULLs natively** - it can learn splits on missing values as a feature, so missing data becomes signal rather than noise.

---

## Feature Coverage Analysis

### ✅ Identifiers (100% Coverage)
- **FA_CRD__c:** 100% (41,942/41,942)
- **RIAFirmCRD:** 97.7% (40,958/41,942)
  - **Note:** 2.3% of leads don't have firm data, but this is expected for some reps

### ✅ Tenure Features (95.8-97.7% Coverage)
- **DateOfHireAtCurrentFirm_NumberOfYears:** 95.8% (40,194/41,942)
- **DateBecameRep_NumberOfYears:** 97.7% (40,957/41,942)
- **NumberOfPriorFirms:** 97.7% (40,958/41,942)
- **AverageTenureAtPriorFirms:** 78.5% (32,924/41,942)
  - **Note:** Lower coverage because some reps have no prior firm history - this is expected and informative

### ✅ License & Designation Features (97.7-100% Coverage)
- **Has_Series_65:** 97.7% (40,958/41,942)
- **Has_CFP:** 97.7% (40,958/41,942)
- **license_count:** 100% (41,942/41,942) - Engineered feature, always populated
- **designation_count:** 100% (41,942/41,942) - Engineered feature, always populated
- **All boolean license flags:** 97.7% coverage (for samples with rep data)

### ⚠️ Geographic Features (38.7-97.6% Coverage)
- **Branch_State:** 97.6% (40,941/41,942) ✅
- **Home_State:** 52.9% (22,194/41,942) ⚠️
- **MilesToWork:** 38.7% (16,227/41,942) ⚠️
  - **Note:** Lower coverage is acceptable - XGBoost will learn that missing = "data not available" which can be predictive

### ✅ Firm Features (97.7% Coverage)
- **total_reps:** 97.7% (40,958/41,942)
- **pct_reps_with_cfp:** 97.7% (40,958/41,942)
- **pct_reps_with_disclosure:** 97.7% (40,958/41,942)
- **multi_state_firm:** 97.7% (40,958/41,942)
- **national_firm:** 97.7% (40,958/41,942)

### ✅ Engineered Features (95.8-100% Coverage)
- **is_veteran_advisor:** 100% (41,942/41,942) ✅
- **is_new_to_firm:** 100% (41,942/41,942) ✅
- **license_count:** 100% (41,942/41,942) ✅
- **designation_count:** 100% (41,942/41,942) ✅
- **Firm_Stability_Score:** 95.8% (40,194/41,942) ✅
- **firm_rep_count_bin:** 97.7% (40,958/41,942) ✅
- **All missingness flags:** 100% (41,942/41,942) ✅

### ❌ Financial Features (0% Coverage - Expected)
- **TotalAssetsInMillions:** 0% (0/41,942) - **Expected NULL** (not in RIARepDataFeed)
- **NumberClients_Individuals:** 0% (0/41,942) - **Expected NULL**
- **AUMGrowthRate_1Year:** 0% (0/41,942) - **Expected NULL**
- **All financial-derived engineered features:** 0% - **Expected NULL**

**These will be dropped as features during training** (they're all NULL, so no signal).

---

## Data Quality Assessment

### ✅ Core Signal Strength: **STRONG**

**Features with 90%+ coverage (High Signal):**
- Rep identifiers: 97.7%
- Tenure features: 95.8-97.7%
- License flags: 97.7%
- Firm features: 97.7%
- Most engineered features: 95.8-100%

**Features with 50-90% coverage (Moderate Signal):**
- AverageTenureAtPriorFirms: 78.5% (some reps have no prior firms - expected)
- Home_State: 52.9% (some reps don't have home address - acceptable)

**Features with <50% coverage (Low Signal, but Usable):**
- MilesToWork: 38.7% (XGBoost will treat missing as a feature)

### ✅ Missing Data Pattern Analysis

**Pattern 1: Rep Data Missing (2.3% of samples)**
- 984 samples (2.3%) don't have rep data
- These are leads that couldn't be matched to discovery data
- **Action:** XGBoost will learn patterns from the 97.7% that do have rep data

**Pattern 2: Prior Firm History Missing (21.5% of samples)**
- 9,018 samples (21.5%) don't have `AverageTenureAtPriorFirms`
- These are likely new reps or first-time advisors
- **Action:** This is informative - we have `num_prior_firms_is_missing` flag to capture this signal

**Pattern 3: Geographic Data Missing**
- Home_State: 47.1% missing (some reps don't provide home address)
- MilesToWork: 61.3% missing (some reps don't report commute distance)
- **Action:** XGBoost handles this natively - missing becomes a split condition

---

## XGBoost NULL Handling

**✅ XGBoost handles NULLs natively:**
1. **Sparsity-aware splits:** XGBoost can split on missing values (sends NULLs left or right)
2. **No imputation needed:** Missing values become part of the model's decision tree
3. **Feature importance:** NULL patterns can be informative (e.g., "missing MilesToWork" might indicate remote work)

**Example:** If `MilesToWork` is missing for 61.3% of samples, XGBoost might learn:
- "If MilesToWork is NULL → check other indicators of remote work"
- Or: "Missing MilesToWork + Has_LinkedIn = higher conversion"

---

## Model Training Readiness

### ✅ **READY FOR TRAINING**

**Why we're confident:**
1. **41,942 samples** - sufficient for XGBoost (typically needs 1,000+)
2. **97.7% have core rep data** - strong signal for most features
3. **100% have engineered features** - all our derived features are complete
4. **XGBoost handles NULLs** - missing data becomes part of the model
5. **Missingness flags** - we explicitly capture missing data patterns as features

**Expected Model Behavior:**
- Model will primarily use features with >90% coverage (tenure, licenses, firm data)
- Sparse features (Home_State, MilesToWork) will contribute but with lower importance
- Financial features will be dropped (all NULL) - no impact on model

**Performance Expectations:**
- **Baseline:** With 97.7% rep data coverage, we expect strong predictive signal
- **Feature richness:** 40+ features with good coverage should provide sufficient signal
- **Class imbalance:** 3.39% positive class is manageable with proper XGBoost parameters

---

## Recommendations

### ✅ **Proceed with Training**

1. **Drop all-NULL features:** Remove financial features (TotalAssetsInMillions, etc.) - they're 100% NULL
2. **Keep sparse features:** Home_State, MilesToWork - XGBoost handles them well
3. **Use missingness flags:** We already created `doh_current_years_is_missing`, etc. - these are informative
4. **Monitor feature importance:** After training, check which sparse features contribute

### ⚠️ **Consider During Training**

1. **Feature selection:** After initial training, consider dropping features with <20% coverage if they don't contribute
2. **Missing value handling:** XGBoost default (handle as-is) is fine, but we could also try:
   - Explicit missing indicators (already have these)
   - Simple imputation for numeric features (not recommended - XGBoost handles NULLs better)
3. **Class balancing:** With 28.5:1 imbalance, consider:
   - `scale_pos_weight` parameter in XGBoost
   - SMOTE or other resampling (if needed)

---

## Conclusion

**✅ Dataset is ready for model training.**

The NULLs are:
- **Expected:** Financial features (intentionally NULL)
- **Acceptable:** Geographic features (XGBoost handles well)
- **Informative:** Prior firm history missing (captured by missingness flags)

**Core signal strength is strong** with 97.7% coverage on key features. XGBoost will handle the missing values natively and learn patterns from available data.

**Next Steps:**
1. Proceed with Step 3.3 (Promote dataset to production view)
2. Proceed with Phase 2 (Model Training)
3. Monitor feature importance during training to identify which sparse features contribute

