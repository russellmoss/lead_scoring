# Step 3.3 Re-Execution Summary - Hybrid Approach

**Date:** Step 3.3 Re-execution  
**Status:** ✅ **COMPLETE**

---

## 🔧 What Was Fixed

### 1. **Table Structure Correction**
- **Issue:** SQL referenced non-existent `discovery_reps_with_features` table
- **Solution:** Updated to use `discovery_reps_current` which:
  - Contains all 122 engineered features
  - Has `snapshot_as_of` column for temporal masking
  - Includes all base + engineered features in one table

### 2. **Firm-Level Features (Optional)**
- `discovery_firms_current` exists and can be joined via `RIAFirmCRD`
- Currently commented out in SQL (can add if needed for V1)
- Firm features would likely be mutable (aggregated metrics change over time)

### 3. **Temporal Features**
- `Day_of_Contact` and `Is_Weekend_Contact` don't exist in `discovery_reps_current`
- **Solution:** Derived in SQL from `Stage_Entered_Contacting__c`:
  - `Day_of_Contact`: 1=Monday, 7=Sunday (converted from BigQuery's 1=Sunday, 7=Saturday)
  - `Is_Weekend_Contact`: 1 if Saturday/Sunday, 0 otherwise

---

## 📊 Validation Results

### Hybrid Dataset Metrics (POST-FILTER)

| Metric | Value |
|--------|-------|
| **Total Samples** | 45,923 |
| **Positive Samples** | 1,616 (3.52%) |
| **Negative Samples** | 44,307 |
| **Imbalance Ratio** | 27.42:1 ✅ |
| **Eligible for Mutable** | 564 leads |
| **Historical Leads** | 45,359 leads |

### Data Integrity ✅
- **Negative conversion times:** 235 records removed
- **Right-censored data:** 200 records removed
- **Final filtered dataset:** 45,923 samples

---

## 📁 Files Created/Updated

### 1. **`Step_3_3_Hybrid_Training_Set.sql`**
- Complete Hybrid (Stable/Mutable) SQL query
- Uses `discovery_reps_current` directly
- Includes all 122 discovery features + 2 temporal features = 124 total
- CASE WHEN logic for all 61 mutable features
- Direct pass-through for all 63 stable features
- Temporal feature derivation inline

### 2. **`step_3_3_class_imbalance_analysis.md`**
- Comprehensive analysis report
- Documents Hybrid approach benefits
- Validates all metrics

### 3. **Config Updates**
- `config/v1_model_config.json`: Updated to `training_data_policy: "hybrid_stable_mutable"`
- `config/v1_feature_schema.json`: Added `is_mutable` flags to all features

### 4. **Support Scripts**
- `update_feature_schema_mutable.py`: Classified all features as mutable/stable
- `generate_step_3_3_hybrid_sql_fixed.py`: Generated complete SQL from schema

---

## 🚀 Next Steps

### Immediate: Export Training Dataset

**Option 1: BigQuery Table Export**
```sql
-- Run the complete FinalDatasetCreation CTE from Step_3_3_Hybrid_Training_Set.sql
-- Export to BigQuery table or CSV
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_hybrid` AS
SELECT * FROM FinalDatasetCreation;
```

**Option 2: CSV Export**
- Use BigQuery console to export `step_3_3_training_dataset_hybrid` to CSV
- Save as `step_3_3_training_dataset.csv` in project root

### Before Week 4 Training

1. **Verify Feature Count:**
   - Expected: 124 features (122 from discovery + 2 temporal)
   - Stable features should have no NULLs
   - Mutable features should have NULLs for ~98.77% of leads (historical)

2. **Check Data Types:**
   - Ensure categorical features are properly typed
   - Verify numeric features have appropriate ranges

3. **Add Firm Features (Optional):**
   - If desired, uncomment firm-level features in SQL
   - Join `discovery_firms_current` on `RIAFirmCRD`
   - Classify firm features as mutable in schema

---

## ✅ Validation Checklist

- [x] SQL query uses correct tables (`discovery_reps_current`)
- [x] Temporal features derived correctly (Day_of_Contact, Is_Weekend_Contact)
- [x] All 122 discovery features included
- [x] Mutable features have CASE WHEN logic
- [x] Stable features pass through directly
- [x] Dataset size validated (45,923 samples)
- [x] Imbalance ratio acceptable (27.42:1)
- [x] Data integrity checks passed

---

## 📝 Notes

### About Firm-Level Features

`discovery_firms_current` contains aggregated firm metrics like:
- `total_firm_aum_millions`
- `avg_rep_aum_millions`
- `firm_growth_momentum`
- `cfp_heavy_firm` (percentage-based flags)
- etc.

**Recommendation:** 
- These are **firm-level** features (one per RIAFirmCRD)
- They would likely be **mutable** (firm metrics change over time)
- For V1, we can proceed without them
- For V2, consider adding if they improve model performance

### Temporal Feature Mapping

- BigQuery `EXTRACT(DAYOFWEEK)` returns: 1=Sunday, 2=Monday, ..., 7=Saturday
- Our spec requires: 1=Monday, 2=Tuesday, ..., 7=Sunday
- Conversion logic in SQL handles this correctly

---

**Status:** ✅ **READY FOR DATASET EXPORT AND WEEK 4 MODEL TRAINING**

