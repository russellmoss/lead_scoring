# Data Leakage Remediation Report

**Date:** December 21, 2024  
**Issue:** Critical data leakage identified in `days_in_gap` feature  
**Action:** Removed leaking feature and retrained model

---

## Executive Summary

The `days_in_gap` feature was identified as a **data leakage** issue because it relies on retrospective data backfilling that would not be available at inference time. The model has been retrained without this feature to establish an **honest performance baseline**.

### Critical Finding

**The model performance dropped significantly after removing the leaking feature:**
- **Old Lift (with leakage):** 3.03x
- **New Lift (honest):** 1.65x
- **Performance Drop:** -45.5% reduction in lift

**However, the model still maintains predictive power above baseline (1.65x > 1.0x).**

---

## Performance Comparison

### Test Set Metrics

| Metric | With `days_in_gap` (Leaking) | Without `days_in_gap` (Honest) | Change |
|--------|------------------------------|--------------------------------|--------|
| **Test AUC-PR** | 0.1070 | 0.0631 | **-41.0%** |
| **Test AUC-ROC** | 0.7002 | 0.6320 | **-9.7%** |
| **Top Decile Lift** | **3.03x** | **1.65x** | **-45.5%** |
| **Top Decile Conversion** | 12.72% | 6.94% | -45.5% |
| **Baseline Conversion** | 4.20% | 4.20% | - |

### Cross-Validation Metrics

| Metric | With `days_in_gap` | Without `days_in_gap` | Change |
|--------|-------------------|----------------------|--------|
| **Mean CV AUC-PR** | 0.0655 | 0.0464 | **-29.2%** |
| **Mean CV AUC-ROC** | 0.7002 | 0.5831 | **-16.7%** |
| **CV Std AUC-PR** | ±0.0116 | ±0.0164 | +41.4% (less stable) |

---

## Impact Analysis

### Why `days_in_gap` Was Leaking

The `days_in_gap` feature calculates the number of days between:
- The end date of the last known employment record
- The `contacted_date` of the lead

**Problem:** This calculation requires knowing the employment end date **after** the contact occurred, which is retrospective data that wouldn't be available at inference time when scoring new leads.

**Example:**
- Lead contacted on: 2024-11-15
- Last employment ended on: 2024-10-20
- `days_in_gap` = 26 days

At inference time (2024-11-15), we wouldn't know the employment ended on 2024-10-20 until that data is backfilled later.

### Feature Importance Impact

**Before Removal (with `days_in_gap`):**
1. `current_firm_tenure_months` (Mean |SHAP| = 0.151)
2. **`days_in_gap`** (Mean |SHAP| = 0.086) ← **REMOVED**
3. `firm_net_change_12mo` (Mean |SHAP| = 0.052)

**After Removal (honest model):**
- `days_in_gap` was the **#2 most important feature**
- Removing it significantly reduced model performance
- Other features must compensate for the loss

---

## Model Survival Assessment

### ✅ Model Still Has Predictive Power

**Lift: 1.65x** (above baseline of 1.0x)
- Top decile conversion: 6.94% vs. baseline 4.20%
- Model can still identify higher-probability leads
- **However, lift is below the 2.0x target threshold**

### ⚠️ Performance Degradation

**Key Concerns:**
1. **Lift dropped from 3.03x to 1.65x** (-45.5%)
2. **AUC-PR dropped from 0.1070 to 0.0631** (-41.0%)
3. **CV stability decreased** (std increased from ±0.0116 to ±0.0164)

### 📊 Business Impact

**Before (with leakage):**
- Top 10% of leads: 12.72% conversion rate
- 3.03x improvement over baseline
- Strong business case for deployment

**After (honest):**
- Top 10% of leads: 6.94% conversion rate
- 1.65x improvement over baseline
- **Weaker business case** (below 2.0x target)

---

## Recommendations

### Option 1: Accept Honest Performance (Recommended)

**Pros:**
- No data leakage
- Realistic performance expectations
- Model still provides value (1.65x lift)

**Cons:**
- Below 2.0x target threshold
- Reduced business impact
- May need additional features to improve

**Action:** Deploy with honest model, set realistic expectations

### Option 2: Feature Engineering to Replace `days_in_gap`

**Potential Replacements:**
1. **`is_recently_moved`** - Binary flag if advisor moved in last 6 months (available at contact time)
2. **`months_since_last_move`** - Time since last known move (if available)
3. **`employment_status_at_contact`** - Current employment status (active/inactive) at contact time

**Action:** Investigate if these features can be derived without retrospective data

### Option 3: Accept Leakage with Disclosure

**Pros:**
- Higher performance (3.03x lift)
- Strong business case

**Cons:**
- **Not recommended** - violates ML best practices
- Performance will degrade in production
- Misleading to stakeholders

**Action:** **DO NOT PROCEED** - This violates data integrity principles

---

## Next Steps

1. ✅ **Completed:** Removed `days_in_gap` from feature set
2. ✅ **Completed:** Retrained model with honest features
3. ⏳ **Pending:** Decision on deployment strategy
4. ⏳ **Pending:** Feature engineering to replace `days_in_gap` (if Option 2 chosen)
5. ⏳ **Pending:** Update all downstream artifacts (calibration, packaging) if proceeding with honest model

---

## Updated Feature Set (11 features)

After removing `days_in_gap`, the model uses:

1. `aum_growth_since_jan2024_pct`
2. `current_firm_tenure_months`
3. `firm_aum_pit`
4. `firm_net_change_12mo`
5. `firm_rep_count_at_contact`
6. `industry_tenure_months`
7. `num_prior_firms`
8. `pit_mobility_tier_Highly Mobile`
9. `pit_mobility_tier_Mobile`
10. `pit_mobility_tier_Stable`
11. `pit_moves_3yr`

**Removed:**
- ❌ `days_in_gap` (data leakage)
- ❌ `firm_stability_score` (weak IV)
- ❌ `pit_mobility_tier_Average` (weak IV)

---

## Conclusion

The removal of `days_in_gap` revealed that **this feature was contributing significantly to model performance** (45.5% of lift). The honest model still maintains predictive power (1.65x lift) but falls below the 2.0x target threshold.

**Recommendation:** Proceed with the honest model, but acknowledge the performance degradation. Consider feature engineering to replace `days_in_gap` with inference-time-available features to improve performance.

**Status:** ✅ **Model retrained and evaluated with honest feature set**

