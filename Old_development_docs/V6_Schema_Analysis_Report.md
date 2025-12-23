# V6 Schema Analysis Report

**Date:** 2025-11-04  
**Table Analyzed:** `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240331_raw`  
**Purpose:** Validate actual schema against transformation plan

---

## 🚨 **CRITICAL FINDING: Missing Financial Metrics**

The `RIARepDataFeed` CSV files **DO NOT** contain financial metrics columns that are referenced in Step 1.5 of the plan:

### **Missing Columns (Expected in Plan but NOT in Raw CSV):**
- ❌ `TotalAssetsInMillions`
- ❌ `NumberClients_Individuals`
- ❌ `NumberClients_HNWIndividuals`
- ❌ `NumberClients_RetirementPlans`
- ❌ `AssetsInMillions_Individuals`
- ❌ `AssetsInMillions_HNWIndividuals`
- ❌ `TotalAssets_SeparatelyManagedAccounts`
- ❌ `TotalAssets_PooledVehicles`
- ❌ `AssetsInMillions_MutualFunds`
- ❌ `AssetsInMillions_PrivateFunds`
- ❌ `AssetsInMillions_Equity_ExchangeTraded`
- ❌ `PercentClients_Individuals`
- ❌ `PercentClients_HNWIndividuals`
- ❌ `PercentAssets_HNWIndividuals`
- ❌ `PercentAssets_Individuals`
- ❌ `PercentAssets_MutualFunds`
- ❌ `PercentAssets_PrivateFunds`
- ❌ `PercentAssets_Equity_ExchangeTraded`
- ❌ `AUMGrowthRate_1Year`
- ❌ `AUMGrowthRate_5Year`
- ❌ `Number_IAReps`
- ❌ `Number_BranchAdvisors`
- ❌ `CustodianAUM_Fidelity_NationalFinancial`
- ❌ `CustodianAUM_Pershing`
- ❌ `CustodianAUM_Schwab`
- ❌ `CustodianAUM_TDAmeritrade`
- ❌ `Custodian1`, `Custodian2`, `Custodian3`, `Custodian4`, `Custodian5`
- ❌ `Brochure_Keywords`
- ❌ `CustomKeywords`
- ❌ `KnownNonAdvisor`

---

## ✅ **Columns That DO Exist in Raw CSV:**

### **Identifiers:**
- ✅ `RepCRD` (INT64)
- ✅ `RIAFirmCRD` (INT64)
- ✅ `DiscoveryRepID` (INT64)
- ✅ `PrimaryRIAFirmCRD` (INT64)
- ✅ `PrimaryFirmCRD` (INT64)
- ✅ `PrimaryBDFirmCRD` (FLOAT64)

### **PII (Will be dropped):**
- ✅ `FirstName` (STRING)
- ✅ `LastName` (STRING)
- ✅ `MiddleName` (STRING)
- ✅ `FullName` (STRING)
- ✅ `Suffix` (STRING)
- ✅ `Title` (STRING)
- ✅ `RIAFirmName` (STRING)

### **Location (Office → Branch mapping needed):**
- ✅ `Office_State` → Map to `Branch_State`
- ✅ `Office_City` → Map to `Branch_City`
- ✅ `Office_County` → Map to `Branch_County`
- ✅ `Office_ZipCode` → Map to `Branch_ZipCode` (FLOAT64)
- ✅ `Office_MetropolitanArea` → Map to `Branch_MetropolitanArea`
- ✅ `Office_Longitude` → Map to `Branch_Longitude`
- ✅ `Office_Latitude` → Map to `Branch_Latitude`

### **Location (Home - keep as-is):**
- ✅ `Home_State` (STRING)
- ✅ `Home_City` (STRING) - **PII - will drop**
- ✅ `Home_County` (STRING) - **PII - will drop**
- ✅ `Home_ZipCode` (FLOAT64) - **PII - will drop**
- ✅ `Home_MetropolitanArea` (STRING) - **Keep (aggregated)**
- ✅ `Home_Longitude` (FLOAT64)
- ✅ `Home_Latitude` (FLOAT64)

### **Tenure & Dates:**
- ✅ `DateBecameRep_NumberOfYears` (FLOAT64)
- ✅ `DateOfHireAtCurrentFirm_NumberOfYears` (FLOAT64)
- ✅ `DateBecameRep_Year` (FLOAT64)
- ✅ `DateBecameRep_YYYY_MM` (STRING)
- ✅ `DateBecameRep_YYYY_MM_DD` (STRING)

### **Prior Firms:**
- ✅ `PriorFirm1_NumberOfYears` → Map to `Number_YearsPriorFirm1` (FLOAT64)
- ✅ `PriorFirm2_NumberOfYears` → Map to `Number_YearsPriorFirm2` (FLOAT64)
- ✅ `PriorFirm3_NumberOfYears` → Map to `Number_YearsPriorFirm3` (FLOAT64)
- ✅ `PriorFirm4_NumberOfYears` → Map to `Number_YearsPriorFirm4` (FLOAT64)
- ✅ `PriorFirm5_NumberOfYears` (FLOAT64) - **Note: Plan only uses 4 prior firms**

### **Licenses & Designations (Series columns → Boolean flags):**
- ✅ `Series7_GeneralSecuritiesRepresentative` (STRING: "Yes"/"No") → `Has_Series_7`
- ✅ `Series65_InvestmentAdviserRepresentative` (STRING) → `Has_Series_65`
- ✅ `Series66_CombinedUniformStateLawAndIARepresentative` (STRING) → `Has_Series_66`
- ✅ `Series24_GeneralSecuritiesPrincipal` (STRING) → `Has_Series_24`
- ✅ `Designations_CFP` (STRING) → `Has_CFP`
- ✅ `Designations_CFA` (STRING) → `Has_CFA`
- ✅ `Designations_CIMA` (STRING) → `Has_CIMA`
- ✅ `Designations_AIF` (STRING) → `Has_AIF`
- ✅ `RegulatoryDisclosures` (STRING: "Yes"/"No") → `Has_Disclosure`

### **Firm Associations:**
- ✅ `NumberFirmAssociations` (INT64)
- ✅ `NumberRIAFirmAssociations` (INT64)
- ✅ `NumberBDFirmAssociations` (FLOAT64)
- ✅ `Number_OfficeReps` (INT64) - **Note: This might map to `Number_BranchAdvisors`?**

### **Other Fields:**
- ✅ `LicensesDesignations` (STRING) → `Licenses`
- ✅ `Education1` → `Education` (STRING)
- ✅ `Gender` (STRING)
- ✅ `DuallyRegisteredBDRIARep` (STRING: "Yes"/"No")
- ✅ `IsPrimaryRIAFirm` (STRING) - **Note: Need to check if this exists or derive from `PrimaryRIAFirmCRD`**
- ✅ `BreakawayRep` (STRING)
- ✅ `MilesToWork` (FLOAT64)
- ✅ `Email_BusinessType` (STRING)
- ✅ `Email_PersonalType` (STRING)
- ✅ `SocialMedia_LinkedIn` (STRING)
- ✅ `PersonalWebsite` (STRING) → `PersonalWebpage` - **PII - will drop**
- ✅ `FirmWebsite` (STRING)
- ✅ `Notes` (STRING) - **PII - will drop**

### **Registered States:**
- ✅ `Number_RegisteredStates` (INT64)
- ✅ `RegisteredStates` (STRING) - Comma-separated list

---

## ❓ **Questions to Resolve:**

1. **Where do financial metrics come from?**
   - Are they in separate CSV files?
   - Do they come from a different data source?
   - Are they in the `discovery_t1`, `discovery_t2`, `discovery_t3` tables that were previously processed?

2. **What is `Number_OfficeReps` vs `Number_BranchAdvisors`?**
   - The raw CSV has `Number_OfficeReps` (INT64)
   - The plan expects `Number_BranchAdvisors` (INT64)
   - Are these the same thing?

3. **What is `IsPrimaryRIAFirm`?**
   - The raw CSV doesn't have this as a string column
   - But it has `PrimaryRIAFirmCRD` (INT64)
   - Should we derive it as: `CASE WHEN RIAFirmCRD = PrimaryRIAFirmCRD THEN 'Yes' ELSE 'No' END`?

4. **Missing `KnownNonAdvisor`:**
   - Not in raw CSV
   - Not sure if this is needed

---

## 📋 **Recommended Actions:**

1. **Immediate:** Check if financial metrics exist in:
   - Other CSV files in `discovery_data/` folder
   - Previously processed `discovery_t1`, `discovery_t2`, `discovery_t3` tables
   - A separate data feed

2. **Update Step 1.5:** 
   - Remove all financial metric columns from the transformation SQL
   - Only transform columns that actually exist in the raw CSV
   - Add note that financial metrics will be added later (if available)

3. **Create PII Drop List:**
   - `config/v6_pii_droplist.json` should include:
     - `FirstName`, `LastName`, `MiddleName`, `FullName`, `Suffix`
     - `Branch_City`, `Branch_County`, `Branch_ZipCode`
     - `Home_City`, `Home_County`, `Home_ZipCode`
     - `RIAFirmName`
     - `PersonalWebsite` (mapped to `PersonalWebpage`)
     - `Notes`
     - `Title` (optional - may be predictive)

4. **Update Data Contract:**
   - `config/v6_feature_contract.json` should only include features that will actually exist after transformation
   - Remove all financial metrics from the contract until we know their source

---

## ✅ **What We CAN Transform:**

Based on the actual schema, Step 1.5 can transform:
- ✅ Identifiers (RepCRD, RIAFirmCRD)
- ✅ Location mappings (Office_* → Branch_*)
- ✅ Prior firm tenure (PriorFirmN_NumberOfYears → Number_YearsPriorFirmN)
- ✅ Boolean flags from Series/Designation columns
- ✅ Tenure metrics (DateBecameRep_NumberOfYears, DateOfHireAtCurrentFirm_NumberOfYears)
- ✅ Firm association counts
- ✅ String fields (Licenses, Education, Gender, etc.)
- ✅ Contact info (Email, SocialMedia, Websites)
- ✅ Distance (MilesToWork)
- ✅ Derived features (AverageTenureAtPriorFirms, NumberOfPriorFirms)
- ✅ Snapshot metadata (snapshot_at)

---

## 🚨 **BLOCKER: Cannot Proceed with Full Plan Until Financial Metrics Source is Identified**

The model training requires financial metrics (AUM, client counts, etc.). These are critical features for the model. We need to:
1. Identify where these metrics come from
2. Either join them to the rep data or update the plan to reflect their absence

