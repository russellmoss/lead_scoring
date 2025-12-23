# Step 3.3: Class Imbalance Analysis - Hybrid (Stable/Mutable) Approach

**Analysis Date:** Step 3.3 Re-execution  
**Training Data Policy:** `hybrid_stable_mutable`  
**Dataset:** Hybrid approach using all historical leads with temporal masking

---

## 📊 Class Distribution Metrics

### Overall Dataset Metrics

| Metric | Value |
|--------|-------|
| **Total Samples** | 45,923 |
| **Positive Samples** | 1,616 |
| **Negative Samples** | 44,307 |
| **Positive Class Percentage** | 3.52% |
| **Imbalance Ratio** | 27.42:1 |

### Temporal Eligibility Breakdown

| Category | Count | Percentage |
|----------|-------|------------|
| **Eligible for Mutable Features** (contacted ≥ snapshot date) | 564 | 1.23% |
| **Historical Leads** (contacted < snapshot date) | 45,359 | 98.77% |

---

## ✅ Data Integrity Checks

### Integrity Assertions (POST-FILTER)

After applying filters for right-censored data and logically impossible records:

- **`negative_days_to_conversion`**: 235 records removed (call scheduled before contact)
- **`labels_in_right_censored_window`**: 200 records removed (incomplete outcome window)

**Status:** ✅ PASS  
**Filtered Dataset:** 45,923 samples (from original ~46,358)

---

## 🔄 Hybrid Approach Benefits

### Expanded Dataset

- **Previous (Eligible-Only):** ~590 samples
- **Current (Hybrid):** 45,923 samples
- **Expansion:** **77.8x increase** in training data

### Feature Availability

- **Stable Features (63 features):** Available for all 45,923 leads
  - Examples: FirstName, Title, Branch_State, Has_CFP, SocialMedia_LinkedIn
  - These features are historically stable and don't change over time

- **Mutable Features (61 features):** Available for 564 eligible leads, NULL for 45,359 historical leads
  - Examples: AUMGrowthRate_5Year, AUM_per_Client, NumberClients_HNWIndividuals
  - These features are NULLed for historical leads to prevent temporal leakage
  - XGBoost will handle NULL values natively during training

### Temporal Integrity Maintained

✅ **No Leakage:** Historical leads cannot see future data  
✅ **Full Feature Richness:** Eligible leads (564) have all 124 features available  
✅ **Stable Signal:** Historical leads (45,359) contribute via 63 stable features

---

## 📈 Comparison to Step 3.1 Baseline

| Metric | Step 3.1 (All-time) | Step 3.3 Hybrid |
|--------|---------------------|----------------|
| Total Leads | 40,595 | 45,923 |
| Positive Class % | 3.89% | 3.52% |
| Imbalance Ratio | 24.18:1 | 27.42:1 |

**Note:** Slight differences due to:
- Additional filtering for data integrity (negative days removed)
- Right-censored window exclusion (last 30 days)
- Inclusion of leads without discovery data match (LEFT JOIN)

---

## 🎯 Validation Status

### ✅ VALIDATION GATES PASSED

1. **Data Integrity:** ✅
   - Negative conversion times removed
   - Right-censored data excluded
   
2. **Class Imbalance:** ✅
   - Ratio 27.42:1 within acceptable range (15:1 to 30:1)
   - Positive class percentage 3.52% aligns with baseline expectations

3. **Dataset Size:** ✅
   - 45,923 samples significantly exceeds minimum threshold
   - Provides sufficient data for robust model training

4. **Feature Coverage:** ✅
   - All 124 features (122 discovery + 2 temporal) accounted for
   - Stable/Mutable classification applied correctly

---

## 📝 Next Steps

### Ready for Step 3.4

- ✅ Training dataset ready for export
- ✅ Class imbalance metrics validated
- ✅ Hybrid approach successfully implemented
- ✅ Temporal integrity maintained

### Week 4 Training Notes

- Model must be trained with `enable_categorical=True`
- XGBoost handles NULL values natively in mutable features
- Expected training sample size: 45,923 leads
- ~1.23% of leads will have full feature richness (all mutable features)
- ~98.77% of leads will rely on stable features only (mutable features NULL)

---

## 🔍 Implementation Details

### SQL Query Used

- **File:** `Step_3_3_Hybrid_Training_Set.sql`
- **Approach:** Hybrid (Stable/Mutable) with temporal masking
- **Feature Source:** `discovery_reps_current` (122 features including all engineered features)
- **Snapshot Source:** `discovery_reps_current.snapshot_as_of` (same table)
- **Optional Firm Features:** `discovery_firms_current` (commented out, can be added via RIAFirmCRD join)

### Feature Classification

- **Stable Features (63):** Pass-through for all leads
- **Mutable Features (61):** CASE WHEN logic applied based on `is_eligible_for_mutable_features`
- **Temporal Features (2):** Will be derived during Week 4 training from `Stage_Entered_Contacting__c`

---

**Status:** ✅ **READY FOR STEP 3.4 AND WEEK 4 MODEL TRAINING**
