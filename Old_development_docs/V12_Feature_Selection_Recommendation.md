# V12 Feature Selection Recommendation: Geographic/PII Fields

**Generated:** November 5, 2025  
**Issue:** V12 model is using geographic PII fields that should be excluded per V6 data governance policy  
**Status:** ⚠️ **CRITICAL - Model violates PII policy**

---

## Executive Summary

The V12 model (`v12_production_model_direct_lead.py`) is currently using geographic fields that are:
1. **Explicitly prohibited** by the V6 Historical Data Processing Guide (Step 4.2 - PII Policy)
2. **Showing high importance** but likely capturing spurious correlations rather than business signals
3. **Not available in V6 dataset** (already cleaned per governance policy)

**Recommendation:** **Use V6 dataset** (`step_3_3_training_dataset_v6_20251104_2217`) and **strictly enforce PII drop list** to ensure model uses only business signals.

---

## Current Problem: V12 Using Prohibited Fields

### Geographic Fields in V12 Top Features

From `v12_direct_importance_20251105_1408.csv`:

| Rank | Feature | Importance | Status |
|------|---------|------------|--------|
| #2 | `Home_ZipCode` | 0.0785 | ❌ **PII - Should be dropped** |
| #3 | `Home_Longitude` | 0.0750 | ❌ **PII - Should be dropped** |
| #5 | `MilesToWork` | 0.0678 | ⚠️ **Questionable - Low coverage** |
| #7 | `Branch_Latitude` | 0.0584 | ❌ **PII - Should be dropped** |
| #8 | `Home_Latitude` | 0.0562 | ❌ **PII - Should be dropped** |
| #9 | `Branch_ZipCode` | 0.0555 | ❌ **PII - Should be dropped** |
| #10 | `Branch_Longitude` | 0.0533 | ❌ **PII - Should be dropped** |

**Total geographic importance:** ~0.387 (38.7% of top 10 features)

---

## V6 Data Governance Policy (Step 4.2)

### Explicitly Prohibited PII Fields

From `V6_Historical_Data_Processing_Guide.md` (Step 4.2):

```json
{
  "PII Fields": [
    "Branch_City",
    "Branch_County",
    "Branch_ZipCode",      // ❌ V12 is using this!
    "Home_City",
    "Home_County",
    "Home_ZipCode",         // ❌ V12 is using this!
    "RIAFirmName",
    "PersonalWebpage",
    "Notes"
  ]
}
```

**Note:** The guide explicitly states:
> "We keep `Home_Zip_3Digit` engineered feature, but drop raw ZIP"

### Latitude/Longitude Not Mentioned But Should Be Excluded

While not explicitly listed, latitude/longitude are:
- **Personally identifiable** (can pinpoint exact location)
- **High cardinality** (thousands of unique values)
- **Likely spurious** (correlate with location, not advisor quality)
- **Not used in V6** (already cleaned dataset doesn't have them)

---

## V6 Dataset Analysis

### What's Actually Available in V6

From `step_3_3_training_dataset_v6_20251104_2217`:

| Field | Type | Unique Values | Coverage | Status |
|-------|------|---------------|----------|--------|
| `Branch_State` | STRING | 51 | 97.6% (40,926/41,942) | ✅ **Keep** (low cardinality, business signal) |
| `Home_State` | STRING | 52 | 52.9% (22,190/41,942) | ✅ **Keep** (low cardinality, business signal) |
| `Home_MetropolitanArea` | STRING | 677 | 52.4% (21,957/41,942) | ⚠️ **Consider dropping** (high cardinality) |
| `Home_Zip_3Digit` | STRING | 156 | 0.6% (233/41,942) | ✅ **Keep** (engineered, low cardinality) |
| `MilesToWork` | FLOAT64 | 4,511 | 38.7% (16,218/41,942) | ⚠️ **Questionable** (low coverage, may be spurious) |
| `Number_RegisteredStates` | INT64 | - | - | ✅ **Keep** (business signal) |

**Missing from V6 (correctly dropped):**
- ❌ `Home_ZipCode` (raw)
- ❌ `Branch_ZipCode` (raw)
- ❌ `Home_Latitude` / `Home_Longitude`
- ❌ `Branch_Latitude` / `Branch_Longitude`
- ❌ `Branch_City` / `Home_City`
- ❌ `Branch_County` / `Home_County`

---

## Why These Fields Are Problematic

### 1. **Privacy Concerns (PII)**
- ZIP codes can identify individuals (especially in rural areas)
- Latitude/longitude can pinpoint exact locations
- Combined with other data, can re-identify advisors

### 2. **Spurious Correlations**
- Geographic location ≠ advisor quality
- Model may learn "advisors in ZIP code X are better" (data artifact)
- Will not generalize to new geographic areas
- Creates bias against underrepresented regions

### 3. **Low Business Signal**
- ZIP code doesn't indicate advisor sophistication, AUM, or conversion likelihood
- Latitude/longitude are just coordinates
- These are **correlates**, not **causes** of conversion

### 4. **High Cardinality Risk**
- ZIP codes: ~40,000 unique values in US
- Latitude/Longitude: Continuous (thousands of unique values)
- High risk of overfitting to specific locations

### 5. **Data Quality Issues**
- `MilesToWork`: Only 38.7% coverage
- `Home_Zip_3Digit`: Only 0.6% coverage (233 rows)
- Geographic fields often have missing values

---

## Recommendation: Use V6 Dataset

### Why V6 is Better

1. **Already PII-Compliant**
   - V6 dataset has already been cleaned per governance policy
   - No raw ZIP codes, lat/long, or city/county fields
   - Only safe, engineered features remain

2. **Temporally Correct**
   - Point-in-time joins already implemented
   - No data leakage risk
   - Validated against 8 assertion checks

3. **Feature Engineering Complete**
   - Engineered features optimized for 30-day MQL conversion
   - Missingness flags, interaction terms, stability scores
   - Business signals (not geographic artifacts)

4. **Consistent with Previous Models**
   - V4, V5, V6, V7 all used PII drop list
   - V12 should follow same governance

### V6 Dataset Schema Summary

**Geographic Fields (Safe):**
- ✅ `Branch_State` (STRING, 51 unique) - Low cardinality, business signal
- ✅ `Home_State` (STRING, 52 unique) - Low cardinality, business signal  
- ✅ `Home_Zip_3Digit` (STRING, 156 unique) - Engineered, low cardinality
- ✅ `Number_RegisteredStates` (INT64) - Business signal
- ✅ `remote_work_indicator` (INT64) - Engineered binary flag
- ✅ `local_advisor` (INT64) - Engineered binary flag (MilesToWork <= 10)
- ✅ `branch_vs_home_mismatch` (INT64) - Engineered binary flag

**Geographic Fields (Questionable):**
- ⚠️ `Home_MetropolitanArea` (STRING, 677 unique) - High cardinality, consider dropping
- ⚠️ `MilesToWork` (FLOAT64, 38.7% coverage) - Low coverage, consider engineered flags only

**Missing (Correctly Excluded):**
- ❌ `Home_ZipCode` / `Branch_ZipCode` (raw)
- ❌ `Home_Latitude` / `Home_Longitude`
- ❌ `Branch_Latitude` / `Branch_Longitude`
- ❌ `Branch_City` / `Home_City`
- ❌ `Branch_County` / `Home_County`

---

## Recommended Feature Set for V12

### Use V6 Dataset with These Geographic Features:

**✅ Keep (Low Cardinality, Business Signals):**
1. `Branch_State` (one-hot encode top 5 states)
2. `Home_State` (one-hot encode top 5 states)
3. `Number_RegisteredStates` (numeric)
4. `remote_work_indicator` (binary engineered)
5. `local_advisor` (binary engineered)
6. `branch_vs_home_mismatch` (binary engineered)

**⚠️ Consider Dropping (High Cardinality or Low Coverage):**
1. `Home_MetropolitanArea` (677 unique values - high cardinality)
2. `MilesToWork` (38.7% coverage - use engineered flags instead)
3. `Home_Zip_3Digit` (0.6% coverage - too sparse)

**❌ Explicitly Exclude (PII Policy):**
1. `Home_ZipCode` / `Branch_ZipCode` (raw)
2. `Home_Latitude` / `Home_Longitude`
3. `Branch_Latitude` / `Branch_Longitude`
4. `Branch_City` / `Home_City`
5. `Branch_County` / `Home_County`

---

## Action Plan

### Option 1: Switch to V6 Dataset (RECOMMENDED)

**Modify `v12_production_model_direct_lead.py`:**

1. **Change data source:**
   ```python
   # FROM:
   LEAD_TABLE = f"{PROJECT}.SavvyGTMData.Lead"
   DISCOVERY_REPS_VIEW = f'{PROJECT}.{DATASET}.v_discovery_reps_all_vintages'
   
   # TO:
   V6_TABLE = f"{PROJECT}.{DATASET}.step_3_3_training_dataset_v6_20251104_2217"
   ```

2. **Add PII drop list enforcement:**
   ```python
   PII_TO_DROP = [
       'Home_ZipCode', 'Branch_ZipCode',           # Raw ZIP codes
       'Home_Latitude', 'Home_Longitude',          # Coordinates
       'Branch_Latitude', 'Branch_Longitude',       # Coordinates
       'Branch_City', 'Home_City',                  # Cities
       'Branch_County', 'Home_County',             # Counties
       'RIAFirmName', 'PersonalWebpage', 'Notes'   # Other PII
   ]
   
   # Enforce drop before training
   feature_cols = [f for f in feature_cols if f not in PII_TO_DROP]
   ```

3. **Filter to 2024-2025 data:**
   ```python
   # Add WHERE clause to filter by Stage_Entered_Contacting__c date
   WHERE DATE(Stage_Entered_Contacting__c) >= '2024-01-01'
     AND DATE(Stage_Entered_Contacting__c) <= '2025-11-04'
   ```

4. **Update target definition:**
   ```python
   # V6 uses 30-day conversion, but you can redefine:
   # Option A: Use V6's target_label (30-day conversion)
   # Option B: Redefine as Call Scheduled (no time window)
   ```

### Option 2: Keep Direct Query but Enforce PII Policy

**Modify `v12_production_model_direct_lead.py`:**

1. **Add explicit PII exclusion:**
   ```python
   # In feature selection section (around line 235)
   PII_TO_DROP = [
       'Home_ZipCode', 'Branch_ZipCode',
       'Home_Latitude', 'Home_Longitude',
       'Branch_Latitude', 'Branch_Longitude',
       'Branch_City', 'Home_City',
       'Branch_County', 'Home_County',
       'RIAFirmName', 'PersonalWebpage', 'Notes'
   ]
   
   # Also exclude low-coverage fields
   LOW_COVERAGE_TO_DROP = [
       'Home_Zip_3Digit',  # Only 0.6% coverage
       'MilesToWork'       # Only 38.7% coverage - use engineered flags instead
   ]
   
   exclude_all = list(set(id_cols + target_cols + timestamp_cols + 
                          PII_TO_DROP + LOW_COVERAGE_TO_DROP))
   ```

2. **Use engineered geographic flags instead:**
   ```python
   # Keep engineered features that use geographic data safely:
   # - remote_work_indicator (binary: MilesToWork > 50)
   # - local_advisor (binary: MilesToWork <= 10)
   # - branch_vs_home_mismatch (binary: Home_State != Branch_State)
   # - Number_RegisteredStates (count of registered states)
   ```

---

## Expected Impact

### Performance Impact

**Potential Performance Loss:**
- Geographic features account for ~38.7% of top 10 feature importance
- Removing them may reduce AUC-PR by 1-2 percentage points initially

**However:**
- This is **correct** - geographic features are spurious
- Model should learn **business signals** (AUM, tenure, licenses, etc.)
- Better generalization to new geographic areas
- Compliance with governance policy

### Long-Term Benefits

1. **Trustworthy Model:** Uses business signals, not location artifacts
2. **Better Generalization:** Works across all geographic regions
3. **Compliance:** Meets V6 governance requirements
4. **Interpretability:** Top features will be business-relevant (AUM, licenses, tenure)

---

## Next Steps

1. **✅ Decision:** Choose Option 1 (V6 dataset) or Option 2 (direct query with PII enforcement)

2. **✅ Implementation:** Modify `v12_production_model_direct_lead.py` to exclude PII fields

3. **✅ Retrain:** Run V12 with PII-compliant feature set

4. **✅ Validation:** Verify top features are business signals (not geographic)

5. **✅ Documentation:** Update model metadata to reflect PII compliance

---

## Conclusion

**V12 is currently violating PII governance policy** by using raw ZIP codes, latitude/longitude, and other geographic PII fields. These fields:
- Show high importance but are likely spurious correlations
- Violate V6 data governance policy
- Are not available in the cleaned V6 dataset

**Recommendation:** **Use V6 dataset** (`step_3_3_training_dataset_v6_20251104_2217`) which is already PII-compliant and temporally correct, or **strictly enforce PII drop list** if continuing with direct query approach.

**Expected Outcome:** Model will use business signals (AUM, tenure, licenses, designations) instead of geographic artifacts, resulting in better generalization and compliance.

---

**Report Generated:** November 5, 2025  
**Status:** ⚠️ **Action Required - PII Policy Violation**

