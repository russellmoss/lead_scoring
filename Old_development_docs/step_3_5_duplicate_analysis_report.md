# Step 3.5: Duplicate Analysis and Deduplication Report

**Date:** Step 3.5 Execution  
**Status:** ✅ **COMPLETE**  
**Investigation Approach:** Root cause analysis before fix application

---

## 🔍 Investigation Results

### Query 1 Result: Duplicate IDs in Source `Lead` Table

**Query:**
```sql
SELECT 
    'Duplicate IDs in Lead Table' as finding,
    Id, 
    COUNT(*) as num_duplicates
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
GROUP BY Id
HAVING num_duplicates > 1
ORDER BY num_duplicates DESC
LIMIT 20;
```

**Result:**
- **Total Rows in Lead Table:** 79,002
- **Unique Ids:** 79,002
- **Duplicate Ids:** **0**

**Finding:** ✅ **NO DUPLICATES** in the source `Lead` table. All Lead Ids are unique.

**Conclusion:** The duplicates are **NOT** originating from duplicate Ids in the Lead table.

---

### Query 2 Result: Duplicate RepCRDs in Source `discovery_reps_current` Table

**Query:**
```sql
SELECT 
    'Duplicate RepCRDs in Reps Table' as finding,
    RepCRD, 
    COUNT(*) as num_duplicates
FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
GROUP BY RepCRD
HAVING num_duplicates > 1
ORDER BY num_duplicates DESC
LIMIT 20;
```

**Result:**
- **Total Rows in discovery_reps_current:** 477,901
- **Unique RepCRDs:** 462,825
- **Duplicate RepCRDs:** **15,076**

**Top Duplicate Examples:**
| RepCRD | Number of Duplicates |
|--------|---------------------|
| 1090963 | 51 |
| 6571587 | 16 |
| 3070864 | 13 |
| 5867442 | 13 |
| 4157107 | 12 |
| ... | ... |

**Finding:** ⚠️ **DUPLICATES FOUND** in the source `discovery_reps_current` table. Many RepCRDs appear multiple times.

**Conclusion:** The duplicates **ARE** originating from duplicate RepCRDs in the discovery table.

---

## 🎯 Root Cause Analysis

### **CONCLUSION: Root Cause Identified**

**The 1,331 duplicates in the training dataset originate from duplicate RepCRDs in the `discovery_reps_current` table, which caused the LEFT JOIN to multiply rows.**

**Explanation:**

1. **Source Lead Table:** ✅ Clean - No duplicate Ids (79,002 rows, 79,002 unique)

2. **Source Discovery Table:** ⚠️ Has Duplicates - 15,076 duplicate RepCRDs (477,901 rows, 462,825 unique)

3. **Join Behavior:**
   - When a Lead's `FA_CRD__c` matches a `RepCRD` that appears multiple times in `discovery_reps_current`
   - The LEFT JOIN creates multiple rows (one for each matching discovery record)
   - This is standard SQL JOIN behavior: if the right table has duplicates, the result set multiplies

4. **Example Scenario:**
   ```
   Lead Table:
   - Id: "ABC123"
   - FA_CRD__c: 1090963
   
   discovery_reps_current Table:
   - RepCRD: 1090963 (appears 51 times!)
   
   Result: Lead "ABC123" gets joined 51 times, creating 51 duplicate rows in training dataset
   ```

**Why RepCRDs Are Duplicated:**
- Likely due to multiple records for the same rep across different territories (T1, T2, T3)
- Or multiple snapshots/updates of the same rep
- Or data quality issues in the source discovery data

---

## 🔧 Fix Applied

### Query 3: Deduplication

**Initial Attempt (SELECT DISTINCT *):**
```sql
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` AS
SELECT DISTINCT *
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`;
```

**Result:** ❌ **DID NOT WORK** - Duplicates remained (45,923 rows, still 1,331 duplicates)

**Root Cause of Failure:**
- Duplicate rows have **subtle differences** in some columns (e.g., Branch_State: "CA" vs "WY")
- These differences come from different discovery records for the same RepCRD
- `SELECT DISTINCT *` treats rows as different if ANY column differs

**Successful Fix Applied (ROW_NUMBER approach):**
```sql
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` AS
SELECT *
FROM (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY Id ORDER BY Stage_Entered_Contacting__c, target_label DESC) as rn
    FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`
)
WHERE rn = 1;
```

**Rationale:**
- Deduplicates by `Id` (ensures each lead appears once)
- Keeps first occurrence based on `Stage_Entered_Contacting__c` (most logical ordering)
- Prefers positive labels (`target_label DESC`) if same timestamp

**Results:**

| Metric | Before Fix | After Fix | Change |
|--------|------------|-----------|--------|
| **Total Rows** | 45,923 | **44,592** | -1,331 ✅ |
| **Unique Ids** | 44,592 | **44,592** | 0 (now matches) ✅ |
| **Duplicate Rows Removed** | 1,331 | **0** | ✅ Fixed |
| **Positive Samples** | 1,616 | **1,572** | -44 |
| **Negative Samples** | 44,307 | **43,020** | -1,287 |
| **Imbalance Ratio** | 27.42:1 | **27.37:1** | ✅ Similar |

**Validation:** ✅ **COMPLETE**
- [x] Row count verified: Dropped from 45,923 to 44,592 (-1,331)
- [x] Duplicate check verified: 0 remaining duplicates
- [x] Class distribution checked: Imbalance ratio 27.37:1 (acceptable, similar to before)
- [x] All Ids unique: Confirmed 44,592 unique Ids matching row count

---

## 📊 Impact Assessment

### Before Fix:
- **Risk of Data Leakage:** ⚠️ HIGH - Same lead could appear in both train and test CV folds
- **Inflated Sample Weights:** ⚠️ Some leads counted 2-51x depending on RepCRD duplicates
- **Model Bias:** ⚠️ Features associated with duplicated RepCRDs would have inflated importance

### After Fix:
- **Data Leakage Risk:** ✅ ELIMINATED - Each lead appears exactly once
- **Sample Weights:** ✅ CORRECT - Each lead counted exactly once
- **Model Bias:** ✅ ELIMINATED - Fair representation of all leads

---

## ✅ Validation Status

### Investigation ✅ COMPLETE
- [x] Query 1 executed: No duplicates in Lead table
- [x] Query 2 executed: Duplicates found in discovery_reps_current table
- [x] Root cause identified: JOIN multiplication due to duplicate RepCRDs

### Fix Application ✅ COMPLETE
- [x] Query 3 executed: Deduplication applied (ROW_NUMBER approach)
- [x] Row count verified: Dropped from 45,923 to 44,592 ✅
- [x] Duplicate check verified: 0 duplicates remaining ✅
- [x] Class distribution checked: 27.37:1 imbalance ratio (healthy) ✅

---

## 📝 Recommendations

### Immediate Actions:
1. ✅ **Apply Fix:** Deduplicate training dataset (Query 3)
2. ✅ **Verify Fix:** Confirm row count reduction and no remaining duplicates
3. ✅ **Re-check Class Distribution:** Ensure positive/negative sample counts are still reasonable

### Long-Term Considerations:
1. **Source Data Quality:** Consider deduplicating `discovery_reps_current` table to prevent future issues
2. **Join Strategy:** Current LEFT JOIN with `SELECT DISTINCT` is appropriate for this use case
3. **Monitoring:** Add duplicate detection to data quality checks for future table updates

---

## 🔄 Next Steps

**Ready for Week 4:** ✅ **READY**

All validation gates passed:
- [x] Table structure confirmed
- [x] Root cause identified: Duplicate RepCRDs in discovery_reps_current causing JOIN multiplication
- [x] Deduplication applied and verified: 44,592 rows, 0 duplicates
- [x] Class distribution validated: 27.37:1 imbalance ratio (acceptable)
- [x] Proceed to Week 4: Feature Selection and Model Training

---

## 📊 Summary

**Investigation Complete:** ✅
- Root cause: Duplicate RepCRDs in `discovery_reps_current` table (15,076 duplicates)
- Source Lead table: Clean (no duplicate Ids)
- Join behavior: LEFT JOIN multiplied rows when RepCRD appeared multiple times

**Fix Complete:** ✅
- Method: ROW_NUMBER() with PARTITION BY Id
- Result: 1,331 duplicate rows removed
- Final dataset: 44,592 rows, all unique Ids
- Class distribution: Healthy (27.37:1 imbalance ratio)

**Data Quality:** ✅ **IMPROVED**
- No risk of data leakage in cross-validation
- Fair sample weights (each lead counted once)
- No bias toward duplicated RepCRDs

---

**Report Generated:** Step 3.5 Execution  
**Status:** ✅ **COMPLETE - Ready for Week 4**

