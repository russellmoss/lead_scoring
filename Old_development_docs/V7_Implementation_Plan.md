# V7 Lead Scoring Model Implementation Plan

**Date:** November 4, 2025  
**Status:** Ready for Implementation  
**Objective:** Bridge gap between V6 (6.74% AUC-PR) and m5 (14.92% AUC-PR)

---

## Executive Summary

V7 implements a hybrid approach that:
1. Uses current financial data across all historical leads (like m5)
2. Maintains temporal integrity for non-financial features
3. Adds m5's 31 engineered features
4. Creates temporal dynamics from 8 quarters of snapshots
5. Aligns training methodology with production usage

**Expected Outcome:** AUC-PR of 10-12% (between V6 and m5)

---

## Key Files Created

### 1. `v7_data_pipeline.py` ✅
- Creates V7 training dataset with hybrid financial data approach
- Point-in-time joins for non-financial features
- Current snapshot joins for financial features
- Output: `step_3_3_training_dataset_v7_{VERSION}`

### 2. `v7_feature_engineering.py` (To Be Created)
- Ports m5's 31 engineered features
- Creates temporal dynamics features
- Career stage and market position indicators
- Business model features

### 3. `train_model_v7.py` (To Be Created)
- Ensemble approach (XGBoost + LightGBM)
- Temporal blocking cross-validation
- Hyperparameter optimization
- Feature importance analysis

### 4. `v7_validation.py` (To Be Created)
- Comprehensive validation gates
- Performance comparison (V6 vs V7 vs m5)
- Production readiness checks

### 5. `V7_Model_Documentation.md` (To Be Created)
- Complete model documentation
- Feature catalog
- Performance metrics
- Deployment guide

---

## Implementation Steps

### Step 1: Create V7 Dataset ✅
```bash
python v7_data_pipeline.py
```

**Output:**
- BigQuery table: `step_3_3_training_dataset_v7_{VERSION}`
- Metadata file: `v7_dataset_metadata_{VERSION}.json`

**Verification:**
```bash
python v7_data_pipeline.py --verify-only --table-name {TABLE_NAME}
```

### Step 2: Feature Engineering (Next)
```bash
python v7_feature_engineering.py --input-table {V7_TABLE} --output-table {FEATURED_TABLE}
```

**Adds:**
- m5's 31 engineered features
- Temporal dynamics (8 features)
- Career stage indicators
- Market position features

### Step 3: Model Training (Next)
```bash
python train_model_v7.py --input-table {FEATURED_TABLE} --cv-folds 5
```

**Outputs:**
- `model_v7.pkl`
- `model_training_report_v7.md`
- `feature_importance_v7.csv`

### Step 4: Validation (Next)
```bash
python v7_validation.py --model-file model_v7.pkl
```

**Validates:**
- CV AUC-PR > 0.12
- Train-Test Gap < 20%
- CV Coefficient < 15%
- Business signals in top 5

### Step 5: Documentation (Next)
```bash
python generate_v7_docs.py --output V7_Model_Documentation.md
```

---

## Key Differences from V6

| Aspect | V6 | V7 |
|--------|----|----|
| **Financial Data** | Point-in-time from snapshots | Current snapshot for all leads |
| **Non-Financial** | Point-in-time from snapshots | Point-in-time from snapshots |
| **Engineered Features** | Basic V6 features | m5's 31 features + temporal |
| **Training-Production** | Mismatch | Aligned (like m5) |
| **Expected AUC-PR** | 6.74% | 10-12% |

---

## Next Actions

1. ✅ **Complete:** `v7_data_pipeline.py` - Dataset creation
2. 🔄 **Next:** Create `v7_feature_engineering.py` with m5 features
3. ⏳ **Next:** Create `train_model_v7.py` with ensemble approach
4. ⏳ **Next:** Create validation and documentation scripts

---

## Notes

- V7 uses the same temporal blocking CV as V6 (5 folds, 30-day gaps)
- Financial features come from `discovery_reps_current` (current snapshot)
- Non-financial features come from `v_discovery_reps_all_vintages` (point-in-time)
- This matches production methodology where we use current financial data

---

**Status:** Step 1 Complete ✅  
**Next:** Implement feature engineering module

