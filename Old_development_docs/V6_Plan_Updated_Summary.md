# V6 Plan Updated - Working Without Financial Metrics

**Date:** 2025-11-04  
**Status:** ✅ Plan updated to work with RIARepDataFeed files only (no financial metrics)

---

## 🎯 **Decision Made:**

**Use RIARepDataFeed files entirely** - accept that financial metrics (AUM, client counts, custodian AUM) are not available in these files. The model will work with:
- Rep metadata (licenses, designations, tenure)
- Location data (states, metro areas)
- Firm associations
- Prior firm history
- Geographic diversity

**Financial metrics will be NULL for all rows** - XGBoost can handle NULLs well, and these features will simply not contribute to the model.

---

## ✅ **What's Available in RIARepDataFeed:**

### **Rep-Level Features:**
- ✅ `RepCRD`, `RIAFirmCRD` (identifiers)
- ✅ `DateBecameRep_NumberOfYears`, `DateOfHireAtCurrentFirm_NumberOfYears` (tenure)
- ✅ `Number_YearsPriorFirm1-4` (prior firm tenure)
- ✅ `AverageTenureAtPriorFirms`, `NumberOfPriorFirms` (derived)
- ✅ `NumberFirmAssociations`, `NumberRIAFirmAssociations` (firm links)
- ✅ `Number_BranchAdvisors` (from `Number_OfficeReps`)
- ✅ `Number_RegisteredStates`
- ✅ `Has_Series_7/65/66/24`, `Has_CFP/CFA/CIMA/AIF`, `Has_Disclosure` (boolean flags)
- ✅ `IsPrimaryRIAFirm`, `DuallyRegisteredBDRIARep` (boolean)
- ✅ `Home_MetropolitanArea`, `Branch_State`, `Home_State`, `MilesToWork`
- ✅ `SocialMedia_LinkedIn`

### **Firm-Level Features (Aggregated):**
- ✅ `total_reps` (count of reps per firm)
- ✅ `pct_reps_with_series_7/65/66/24`, `pct_reps_with_cfp`, `pct_reps_with_disclosure`
- ✅ `avg_rep_experience_years`, `avg_tenure_at_firm_years`, `avg_tenure_at_prior_firms`
- ✅ `states_represented`, `metro_areas_represented` (geographic diversity)
- ✅ `multi_state_firm`, `national_firm` (boolean flags)
- ✅ `primary_state`, `primary_metro_area`, `primary_branch_state`

### **NOT Available (Will be NULL):**
- ❌ `TotalAssetsInMillions`, `AUMGrowthRate_1Year/5Year`
- ❌ `NumberClients_Individuals/HNWIndividuals/RetirementPlans`
- ❌ `AssetsInMillions_*` (all asset breakdowns)
- ❌ `PercentClients_*`, `PercentAssets_*`
- ❌ `Number_IAReps`
- ❌ `CustodianAUM_*` (all custodian AUM fields)
- ❌ `Custodian1-5` (custodian names)

---

## 📋 **Changes Made to Plan:**

### **Step 1.5: Transform Raw CSV**
- ✅ Updated SQL to set all financial metrics to `NULL`
- ✅ Mapped `Number_OfficeReps` → `Number_BranchAdvisors`
- ✅ Derived `IsPrimaryRIAFirm` from `PrimaryRIAFirmCRD`
- ✅ Converted `DuallyRegisteredBDRIARep` to boolean (1/0)
- ✅ Set all custodian relationship flags to `0`
- ✅ Added `Number_RegisteredStates` to output

### **Step 1.6: Create Firm Snapshots**
- ✅ Updated to set financial metrics to `NULL`
- ✅ Added tenure aggregations (`avg_rep_experience_years`, etc.)
- ✅ Added license percentage aggregations
- ✅ Set `firm_size_tier` and `aum_per_rep` to `NULL`

### **Step 3.1: Staging Join**
- ✅ Added comments noting which fields are NULL
- ✅ Kept all columns in SELECT (XGBoost will handle NULLs)

---

## 🎯 **Model Training Implications:**

### **What the Model Will Use:**
1. **Tenure & Experience:**
   - `DateBecameRep_NumberOfYears`
   - `DateOfHireAtCurrentFirm_NumberOfYears`
   - `AverageTenureAtPriorFirms`
   - `NumberOfPriorFirms`

2. **Licenses & Qualifications:**
   - `Has_Series_7/65/66/24`
   - `Has_CFP/CFA/CIMA/AIF`
   - `Has_Disclosure`
   - Firm-level: `pct_reps_with_*`

3. **Firm Associations:**
   - `NumberFirmAssociations`
   - `NumberRIAFirmAssociations`
   - `IsPrimaryRIAFirm`
   - `DuallyRegisteredBDRIARep`

4. **Geographic:**
   - `Home_MetropolitanArea`
   - `Branch_State`, `Home_State`
   - `MilesToWork`
   - Firm-level: `multi_state_firm`, `national_firm`

5. **Firm Size (proxy):**
   - `total_reps` (firm-level)
   - `Number_BranchAdvisors`

### **What the Model Will NOT Have:**
- AUM metrics (won't know firm size by assets)
- Client counts (won't know client base size)
- Growth rates (won't know firm growth trajectory)
- Custodian relationships (won't know which custodians they use)

### **Expected Impact:**
- **Model will still work** - XGBoost handles NULLs well
- **May have lower predictive power** - financial metrics are often strong signals
- **Will rely more heavily on:**
  - Tenure/experience signals
  - License/designation signals
  - Geographic signals
  - Firm size proxies (rep count)

---

## ✅ **Next Steps:**

1. ✅ **Step 1.2:** Continue uploading remaining 7 CSV files
2. ✅ **Step 1.5:** Execute transformation SQL (financial metrics set to NULL)
3. ✅ **Step 1.6:** Create firm snapshots (without financial aggregations)
4. ✅ **Step 3.1:** Create training dataset (with NULL financial metrics)
5. ✅ **Step 4.1:** Train model - XGBoost will handle NULLs natively

---

## 📊 **Data Contract Updates Needed:**

The `config/v6_feature_contract.json` should be updated to reflect that financial metrics are optional (nullable) and may be NULL for all rows. The model training script should handle this gracefully.

---

## 🚦 **Status:**

**READY TO PROCEED** - Plan is updated and ready for execution. Financial metrics are explicitly set to NULL, and the model will train on available features only.

