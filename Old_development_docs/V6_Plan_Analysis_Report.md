# V6 Historical Data Processing Plan - Analysis Report

**Date:** December 2025  
**Purpose:** Evaluate whether the V6 plan has everything needed to process the 8 RIARepDataFeed CSV files into usable BigQuery tables with engineered features, proper quarter mapping, and temporal leakage prevention.

---

## 📊 **Current Data Inventory**

### Available Files:
- **8 RIARepDataFeed CSV files** (Rep-level data):
  - `RIARepDataFeed_20240107.csv` (2024 Q1 - Jan 7, 2024)
  - `RIARepDataFeed_20240331.csv` (2024 Q1 - Mar 31, 2024)
  - `RIARepDataFeed_20240707.csv` (2024 Q3 - Jul 7, 2024)
  - `RIARepDataFeed_20241006.csv` (2024 Q4 - Oct 6, 2024)
  - `RIARepDataFeed_20250105.csv` (2025 Q1 - Jan 5, 2025)
  - `RIARepDataFeed_20250406.csv` (2025 Q2 - Apr 6, 2025)
  - `RIARepDataFeed_20250706.csv` (2025 Q3 - Jul 6, 2025)
  - `RIARepDataFeed_20251005.csv` (2025 Q4 - Oct 5, 2025)

- **8 BDRepDataFeed CSV files** (Broker-Dealer Rep data - may be separate or merged):
  - Similar date pattern as RIARepDataFeed files

### CSV Structure:
Based on sample header analysis, the CSV files contain:
- **Identifiers:** `RepCRD`, `RIAFirmCRD`, `DiscoveryRepID`
- **Personal Info:** `FirstName`, `LastName`, `FullName`, `Title`, `Gender`
- **Location Data:** `Office_State`, `Office_City`, `Office_ZipCode`, `Home_State`, `Home_City`, `Home_ZipCode`, `Home_MetropolitanArea`
- **Firm Info:** `RIAFirmName`, `DateOfHireAtCurrentFirm_YYYY_MM`, `DateBecameRep_YYYY_MM`
- **Licenses:** Multiple Series licenses (Series7, Series65, Series66, etc.)
- **Prior Firms:** `PriorFirm1_NumberOfYears`, `PriorFirm2_NumberOfYears`, etc.
- **And many more columns...**

---

## ✅ **What the V6 Plan DOES Cover**

### 1. **Temporal Leakage Prevention** ✅
The plan correctly implements point-in-time joins:

- **Step 3.1** correctly uses `DATE_TRUNC(DATE(Stage_Entered_Contacting__c), QUARTER) as contact_quarter`
- Joins discovery data using `l.contact_quarter = reps.snapshot_quarter`
- This ensures we only use data that was available at the time the rep entered the funnel
- **Result:** ✅ No temporal leakage - model sees data as it would have been available historically

### 2. **Quarter Mapping** ✅
The plan includes:
- `snapshot_quarter` column added in Step 2.1 (union views)
- Quarter dates correctly mapped: `DATE('2024-01-01')` for Q1 2024, etc.
- Quarter integrity check in Step 3.2 assertions

**However, there's a mismatch:**
- **Plan expects:** 2023 Q1 - 2024 Q4 (8 quarters)
- **Files available:** 2024 Q1 - 2025 Q4 (8 quarters)
- **Action needed:** Update Step 2.1 to use 2024-2025 quarters instead of 2023-2024

### 3. **Feature Engineering** ✅
The plan includes:
- Step 3.1: Selects all "Keep" features from Reps and Firms
- Step 3.2: Applies engineered features (AUM_per_Client, HNW_Client_Ratio, etc.)
- All engineered features from V4/V5 are included

### 4. **Firm-Level Aggregation** ✅
The plan correctly:
- Uses `v_discovery_firms_all_vintages` view (Step 3.1)
- Firms are aggregated from Reps data (not separate files)
- Firm features match `create_discovery_firms_current.sql` structure

---

## ⚠️ **Critical Gaps & Issues**

### 1. **Missing: Data Transformation Layer** 🚨

**Problem:** The V6 plan assumes CSV files can be directly uploaded to BigQuery with column names matching `discovery_reps_current`. However:

- **CSV columns use different naming:** `Office_State` vs `Branch_State`, `Office_City` vs `Branch_City`
- **Missing columns mapping:** The CSV may not have direct matches for all expected columns
- **Data type conversion needed:** Some fields need parsing (e.g., `"< 5"` → `2` for client counts)

**What's Missing:**
- Step to transform raw CSV columns to match `discovery_reps_current` schema
- Column mapping/transformation logic (similar to `create_discovery_reps_current_complete.sql` lines 88-178)
- Handling of special values (`"< 5"`, currency formatting, etc.)

**Required Addition:**
```
Step 1.5: Transform Raw CSV to discovery_reps_current Schema
- Map Office_* → Branch_*
- Handle special values ("< 5" → 2)
- Parse currency fields (TotalAssetsInMillions)
- Create derived boolean flags (Has_Series_7, Has_CFP, etc.)
- Apply all transformations from create_discovery_reps_current_complete.sql
```

### 2. **Missing: License/Designation Flag Derivation** 🚨

**Problem:** The V6 plan Step 3.1 expects boolean flags like:
- `Has_Series_7`
- `Has_Series_65`
- `Has_CFP`
- `Has_CFA`
- `Has_CIMA`
- `Has_AIF`
- `Has_Disclosure`

**But CSV has:**
- Individual Series columns: `Series7_GeneralSecuritiesRepresentative` (Yes/No)
- `LicensesDesignations` (string field)
- `RegulatoryDisclosures` (string field)

**Required Addition:**
Need to derive boolean flags from CSV columns:
```sql
CASE WHEN Series7_GeneralSecuritiesRepresentative = 'Yes' THEN 1 ELSE 0 END as Has_Series_7,
CASE WHEN Series65_InvestmentAdviserRepresentative = 'Yes' THEN 1 ELSE 0 END as Has_Series_65,
CASE WHEN Designations_CFP = 'Yes' THEN 1 ELSE 0 END as Has_CFP,
-- etc.
```

### 3. **Missing: Asset/Client Metrics Columns** ⚠️

**Problem:** The V6 plan expects columns like:
- `TotalAssetsInMillions`
- `Number_IAReps`
- `NumberClients_Individuals`
- `AssetsInMillions_MutualFunds`
- `CustodianAUM_Schwab`

**CSV may have:**
- Different column names or missing fields
- Need to verify column mapping exists

**Action Required:**
- Compare CSV column names to expected schema
- Create mapping document
- Add transformation SQL if columns don't match

### 4. **Quarter Mapping Issue** ⚠️

**Problem:** 
- Plan expects 2023 Q1 - 2024 Q4
- Files are 2024 Q1 - 2025 Q4

**Required Fix:**
Update Step 2.1 to use:
```sql
DATE('2024-01-01') as snapshot_quarter  -- Q1 2024
DATE('2024-04-01') as snapshot_quarter  -- Q2 2024
DATE('2024-07-01') as snapshot_quarter  -- Q3 2024
DATE('2024-10-01') as snapshot_quarter  -- Q4 2024
DATE('2025-01-01') as snapshot_quarter  -- Q1 2025
DATE('2025-04-01') as snapshot_quarter  -- Q2 2025
DATE('2025-07-01') as snapshot_quarter  -- Q3 2025
DATE('2025-10-01') as snapshot_quarter  -- Q4 2025
```

### 5. **Missing: Firm Snapshot Creation** ⚠️

**Problem:** The plan creates `v_discovery_firms_all_vintages` but doesn't specify:
- How to create firm snapshots from rep snapshots
- Should each quarter's firm table be created separately?
- Or should firms be aggregated in the view?

**Current Plan:** Step 2.2 creates firm view from firm tables, but we need to create those firm tables first.

**Required Addition:**
```
Step 1.6: Create Firm Snapshot Tables
- For each quarter's rep snapshot, aggregate to firm level
- Use same logic as create_discovery_firms_current.sql
- Create snapshot_firms_2024_q1, snapshot_firms_2024_q2, etc.
```

---

## 📋 **Recommended Additions to V6 Plan**

### **Step 1.5: Transform Raw CSV to Standardized Schema** (NEW)

**Objective:** Transform uploaded CSV files to match `discovery_reps_current` schema before creating snapshot tables.

**AGENTIC TASK:**

1. **Create transformation SQL** that:
   - Maps CSV column names to target schema names:
     - `Office_State` → `Branch_State`
     - `Office_City` → `Branch_City`
     - `Office_ZipCode` → `Branch_ZipCode`
     - `Office_MetropolitanArea` → (check if exists, or derive from ZIP)
   - Derives boolean flags from Series columns
   - Handles special values (`"< 5"` → `2`)
   - Parses currency/numeric fields

2. **Apply transformation** to each uploaded snapshot table:
   ```sql
   CREATE OR REPLACE TABLE `LeadScoring.snapshot_reps_2024_q1_transformed` AS
   SELECT
     -- Column mappings and transformations
     CAST(RepCRD AS STRING) as RepCRD,
     CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
     SAFE_CAST(REGEXP_REPLACE(TotalAssetsInMillions, r'[$,]', '') AS FLOAT64) as TotalAssetsInMillions,
     -- ... (all transformations from create_discovery_reps_current_complete.sql)
   FROM `LeadScoring.snapshot_reps_2024_q1_raw`;
   ```

3. **Validate transformed schema** against `config/v6_feature_contract.json`

### **Step 1.6: Create Firm Snapshot Tables** (NEW)

**Objective:** Aggregate rep snapshots to firm-level snapshots for each quarter.

**AGENTIC TASK:**

For each quarter:
1. Create firm snapshot table from rep snapshot:
   ```sql
   CREATE OR REPLACE TABLE `LeadScoring.snapshot_firms_2024_q1` AS
   -- Use same aggregation logic as create_discovery_firms_current.sql
   -- But filter by snapshot_quarter = DATE('2024-01-01')
   ```

2. Validate firm snapshot row counts and schema

### **Step 1.7: Update Quarter Mappings** (MODIFICATION)

**Objective:** Update all quarter references from 2023-2024 to 2024-2025.

**AGENTIC TASK:**

1. Update Step 2.1 SQL with correct quarter dates (2024-2025)
2. Update Step 2.2 SQL with correct quarter dates
3. Update Step 3.2 assertion queries with correct quarter dates

---

## ✅ **Final Assessment**

### **What Works:**
- ✅ Temporal leakage prevention (point-in-time joins)
- ✅ Feature engineering logic
- ✅ Firm aggregation approach
- ✅ Overall workflow structure
- ✅ Validation gates and assertions

### **What Needs to be Added:**
- 🚨 **Data transformation layer** (Step 1.5) - CRITICAL
- 🚨 **License/designation flag derivation** - CRITICAL
- ⚠️ **Quarter mapping update** (2024-2025 instead of 2023-2024) - REQUIRED
- ⚠️ **Firm snapshot creation** (Step 1.6) - REQUIRED
- ⚠️ **Column mapping verification** - NEEDED

### **Recommendation:**

**YES, the V6 plan has the right structure and logic**, but needs these additions:

1. **Add Step 1.5:** Transform raw CSV to standardized schema
2. **Add Step 1.6:** Create firm snapshot tables from rep snapshots
3. **Update Step 1.1-1.2:** Clarify that 8 files are for 2024-2025, not 2023-2024
4. **Update Step 2.1-2.2:** Use 2024-2025 quarter dates
5. **Add column mapping document:** Map CSV columns to target schema

**With these additions, the plan will be complete and ready to process the 8 RIARepDataFeed files.**

---

## 📝 **Next Steps**

1. **Create column mapping document** comparing CSV headers to expected schema
2. **Add Step 1.5** transformation SQL (port from `create_discovery_reps_current_complete.sql`)
3. **Add Step 1.6** firm aggregation SQL (port from `create_discovery_firms_current.sql`)
4. **Update all quarter references** from 2023-2024 to 2024-2025
5. **Test with one file** before processing all 8 files

**Status:** Plan is **~85% complete** - needs transformation layer and quarter updates.

