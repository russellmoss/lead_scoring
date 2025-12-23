# V6 Readiness Assessment Summary

**Date:** 2025-11-04  
**Status:** ⚠️ **BLOCKER IDENTIFIED** - Need to resolve financial metrics source

---

## ✅ **What We Know:**

1. **Upload Working:** `snapshot_reps_20240331_raw` successfully uploaded (471,145 rows)
2. **Schema Verified:** Raw CSV has 471 columns - mostly rep metadata, licenses, prior firms, location
3. **PII Identified:** All PII fields are present and will be dropped (FirstName, LastName, addresses, etc.)

---

## 🚨 **CRITICAL BLOCKER: Missing Financial Metrics**

### **The Problem:**
The `RIARepDataFeed_YYYYMMDD.csv` files **DO NOT** contain financial metrics that are essential for the model:

**Missing Columns:**
- `TotalAssetsInMillions`
- `NumberClients_Individuals`, `NumberClients_HNWIndividuals`, `NumberClients_RetirementPlans`
- `AssetsInMillions_Individuals`, `AssetsInMillions_HNWIndividuals`
- `TotalAssets_SeparatelyManagedAccounts`, `TotalAssets_PooledVehicles`
- `AssetsInMillions_MutualFunds`, `AssetsInMillions_PrivateFunds`, `AssetsInMillions_Equity_ExchangeTraded`
- `PercentClients_*`, `PercentAssets_*`
- `AUMGrowthRate_1Year`, `AUMGrowthRate_5Year`
- `Number_IAReps`, `Number_BranchAdvisors`
- `CustodianAUM_*` (Schwab, Fidelity, Pershing, TDAmeritrade)
- `Custodian1-5` (strings)
- `Brochure_Keywords`, `CustomKeywords`

### **Where These Metrics Come From:**
Looking at `create_discovery_reps_current_complete.sql`, financial metrics come from:
- `staging_discovery_t1` table (from `discovery_t1_2025_10.csv`)
- `staging_discovery_t2` table (from `discovery_t2_2025_10.csv`)
- `staging_discovery_t3` table (from `discovery_t3_2025_10.csv`)

**Files in `discovery_data/`:**
- ✅ `discovery_t1_2025_10.csv`
- ✅ `discovery_t2_2025_10.csv`
- ✅ `discovery_t3_2025_10.csv`

---

## ❓ **Questions to Resolve:**

1. **Do we need to process `discovery_t1/t2/t3` files?**
   - These appear to have quarterly snapshots (only one file per territory, dated 2025-10)
   - Do we have 8 quarterly snapshots for each territory (T1, T2, T3)?
   - Or do we join the current `discovery_reps_current` table (which has all territories combined)?

2. **Should we join with existing BigQuery tables?**
   - `LeadScoring.discovery_reps_current` already exists and has all financial metrics
   - Could we join `RIARepDataFeed` snapshots with `discovery_reps_current` to get financial data?
   - But this would lose temporal accuracy (snapshot dates)

3. **Alternative: Do financial metrics exist in `RIARepDataFeed` under different column names?**
   - Need to check if there are any columns with financial data that we're missing
   - From the schema inspection, we didn't see any

---

## 📋 **What We CAN Do Right Now:**

### **Step 1.5 Transformation (Partial - No Financial Metrics):**

We can transform the columns that exist:
- ✅ Identifiers (RepCRD, RIAFirmCRD)
- ✅ Location mappings (Office_* → Branch_*)
- ✅ Prior firm tenure
- ✅ Boolean flags from Series/Designation columns
- ✅ Tenure metrics
- ✅ Firm associations
- ✅ String fields
- ✅ Contact info
- ✅ Derived features (AverageTenureAtPriorFirms, NumberOfPriorFirms)

**But we CANNOT create the full model training dataset without financial metrics.**

---

## 🎯 **Recommended Next Steps:**

### **Option 1: Process T1/T2/T3 Files (If Available)**
If you have 8 quarterly snapshots for each territory:
1. Upload all `discovery_t1_YYYYMMDD.csv`, `discovery_t2_YYYYMMDD.csv`, `discovery_t3_YYYYMMDD.csv` files
2. Join financial metrics from T1/T2/T3 with rep metadata from `RIARepDataFeed`
3. Create unified snapshot tables with both metadata and financial data

### **Option 2: Join with Existing Table (Temporal Accuracy Risk)**
If T1/T2/T3 files don't have quarterly snapshots:
1. Transform `RIARepDataFeed` snapshots (rep metadata only)
2. Join with `discovery_reps_current` to get financial metrics
3. ⚠️ **Risk:** Financial metrics may not match snapshot dates (temporal leakage risk)

### **Option 3: Check for Other Data Sources**
1. Check if MarketPro provides financial metrics separately
2. Check if there are other CSV files with financial data
3. Verify if `BDRepDataFeed` files have financial metrics (8 files exist)

---

## ✅ **PII Drop List (Ready to Create):**

Based on actual schema, `config/v6_pii_droplist.json` should include:

```json
[
  "FirstName",
  "LastName",
  "MiddleName",
  "FullName",
  "Suffix",
  "Branch_City",
  "Branch_County",
  "Branch_ZipCode",
  "Home_City",
  "Home_County",
  "Home_ZipCode",
  "RIAFirmName",
  "PersonalWebpage",
  "Notes"
]
```

**Note:** `Title` may be kept (could be predictive), but should be reviewed.

---

## 📊 **Schema Validation Status:**

- ✅ **Rep Metadata:** Fully mapped and ready
- ✅ **Location Data:** Mapping logic defined (Office_* → Branch_*)
- ✅ **Prior Firm Data:** Mapping logic defined
- ✅ **License/Designation Flags:** Conversion logic defined
- ❌ **Financial Metrics:** Source not identified
- ❌ **Custodian Data:** Source not identified
- ❌ **Client Counts:** Source not identified

---

## 🚦 **Current Status:**

**READY FOR:**
- ✅ Step 1.2: Upload remaining 7 CSV files
- ✅ Step 1.5: Transform rep metadata (partial - no financial metrics)
- ✅ Step 4.2: Create PII drop list

**BLOCKED ON:**
- ❌ Step 1.5: Full transformation (needs financial metrics source)
- ❌ Step 3.1: Training dataset creation (needs financial metrics)
- ❌ Step 4.1: Model training (needs financial metrics)

---

## 💡 **Recommendation:**

**Before proceeding with Step 1.5, we need to:**
1. ✅ Confirm if `discovery_t1/t2/t3` files have 8 quarterly snapshots
2. ✅ Or confirm if we should join with existing `discovery_reps_current` table
3. ✅ Or identify where financial metrics come from for these 8 snapshots

**Once resolved, we can:**
- Update Step 1.5 SQL to include financial metrics join/transformation
- Update data contracts to reflect actual available columns
- Proceed with full pipeline

