# V6 Lead Scoring Master Production Plan

**Status:** ✅ **Phase 1 Complete - Ready for Phase 2 (Model Development)**  
**Date Created:** November 3, 2025  
**Last Updated:** November 4, 2025  
**Purpose:** Step-by-step agentic plan to ingest, build, validate, deploy, and monitor the V6 production lead scoring model.

## 🎯 **Current Progress**

**✅ Phase 1: Data Pipeline (COMPLETE)**
- ✅ Step 0: Data Contracts Defined
- ✅ Step 1: All 8 Historical Snapshots Ingested & Transformed
- ✅ Step 2: Master Snapshot Views Created
- ✅ Step 3.1: Staging Join Table Created (46,299 leads, 97.4% match rate)
- ✅ Step 3.2: Final Training Dataset Created (41,942 samples, all validations passed)
- ⏭️ Step 3.3: Promote New Data Build (NEXT STEP)

**Ready for:** Phase 2 - Model Development (Train & Validate)

---

## 📋 **Overview**

This master plan provides a complete, end-to-end, agentically executable workflow for the Savvy Wealth V6 Lead Scoring model. It covers:

1. **Phase 1: Data Pipeline** - Ingest historical snapshots, validate schemas, build temporally-correct training datasets
2. **Phase 2: Model Development** - Train, calibrate, validate, and backtest the model
3. **Phase 3: Production Deployment** - Shadow scoring, A/B testing, and controlled rollout
4. **Phase 4: Maintenance & Monitoring** - Ongoing health checks, drift detection, and quarterly refreshes

**Expected Deliverable:** Production-ready, monitored, and maintainable `model_v6_[version].pkl` with full observability

---

## 🎯 **Prerequisites**

Before starting, ensure you have:
- ✅ Confirmation from MarketPro (Jamie Nennecke) that data is ready
- ✅ Secured download links for all 16 files
- ✅ Access to BigQuery project: `savvy-gtm-analytics`
- ✅ Write permissions to `LeadScoring` dataset
- ✅ Python environment with required packages (from `requirements.txt`)
- ✅ Access to `unit_4_train_model_v4.py` script (to be copied for V6)

---

## 🎯 **Phase 1: Data Pipeline (Ingest & Transform)**

### **Step 0: Define Data Contracts (Agent Task)**

**Objective:** Create golden schema contracts that define the expected structure of all snapshot files. These contracts will be used to validate all incoming data.

**AGENTIC TASK:**

You are a data architect. Your task is to create two JSON schema contract files that define the exact structure expected for Reps and Firms snapshot data.

1. **Create `config/v6_feature_contract.json`:**
   - Extract all "Keep" features from Step 3.1's SQL query (the Reps features selected in `PointInTimeJoin`)
   - For each feature, define:
     - `name`: The exact column name
     - `bq_type`: The BigQuery data type (STRING, FLOAT, INTEGER, BOOLEAN, DATE, etc.)
     - `nullable`: `true` or `false`
   - Include all ~60+ Reps features from the approved Keep list
   - Format as JSON array of objects

2. **Create `config/v6_firm_feature_contract.json`:**
   - Extract all "Keep" features for Firms from Step 3.1's SQL query
   - Use the same structure as the Reps contract
   - Include all firm-level aggregated features

**Example Structure:**
```json
[
  {
    "name": "RepCRD",
    "bq_type": "STRING",
    "nullable": false
  },
  {
    "name": "TotalAssetsInMillions",
    "bq_type": "FLOAT",
    "nullable": true
  },
  ...
]
```

**Validation Checklist:**
- [x] `config/v6_feature_contract.json` created with all Reps Keep features - **Updated to match Step 1.5/3.1**
- [x] `config/v6_firm_feature_contract.json` created with all Firms Keep features - **Updated to match Step 1.6/3.1**
- [x] Both files are valid JSON - **Validated**
- [x] All features from Step 3.1 SQL are included - **All 60+ rep features and 16 firm features included**

**Contract Updates:**
- Added new boolean flags: `Is_BreakawayRep`, `Has_Insurance_License`, `Is_NonProducer`, `Is_IndependentContractor`, `Is_Owner`, `Office_USPS_Certified`, `Home_USPS_Certified`, `Has_LinkedIn`
- Corrected data types: `IsPrimaryRIAFirm` and `DuallyRegisteredBDRIARep` are now INT64 (not STRING)
- All fields match Step 3.1 PointInTimeJoin SELECT statement

**✅ Gate:** Proceed to Step 1.1 only when these contract files are created and validated.

---

## 📦 **Step 1: Ingest 8 Historical Snapshots**

**Objective:** Download, upload, and transform all historical snapshot CSV files to BigQuery. Note: We have 8 rep-level CSV files, and firms are aggregated from reps (not separate files).

### **Step 1.1 (Human Task): Download Files**

1. **Receive secured links** from MarketPro (Jamie Nennecke)
   - Expected: 8 RIARepDataFeed CSV files (one per quarter)
   - Format: 8 quarters of Rep-level data
   - Quarters: 2024 Q1, 2024 Q2, 2024 Q3, 2024 Q4, 2025 Q1, 2025 Q2, 2025 Q3, 2025 Q4
   - File naming pattern: `RIARepDataFeed_YYYYMMDD.csv` (e.g., `RIARepDataFeed_20240107.csv` for Q1 2024)

2. **Download all 8 files** to a local directory
   - Recommended: Create folder `discovery_data/`
   - Verify file integrity (check file sizes match expectations)

### **Step 1.2 (Human/Agent Task): Upload Raw CSV Files to BigQuery Staging Tables**

**Objective:** Upload ALL 8 RIARepDataFeed CSV files to BigQuery staging tables. Each file gets its own date-based table name. These will be transformed in Step 1.5.

**⚠️ IMPORTANT:** We upload ALL 8 files (no filtering). Each file uses its date from the filename for the table name.

1. **Determine staging table name** based on date in filename:
   - Extract date from filename: `RIARepDataFeed_YYYYMMDD.csv` → `YYYYMMDD`
   - Raw staging: `LeadScoring.snapshot_reps_YYYYMMDD_raw` (e.g., `snapshot_reps_20240107_raw`, `snapshot_reps_20240331_raw`)
   - **Critical:** Use date format from filename (`_20240107`, not `_2024_q1`) and append `_raw` suffix

2. **Upload file to BigQuery:**
   - Use the provided Python script: `python step_1_2_upload_ria_reps_raw.py`
   - Or use BigQuery Console: Upload → Create table from file
   - Or use `bq` command-line tool
   - **Important:** Use `autodetect=True` to let BigQuery infer schema from CSV

3. **Expected tables (8 total):**
   - `snapshot_reps_20240107_raw` (Jan 7, 2024)
   - `snapshot_reps_20240331_raw` (Mar 31, 2024)
   - `snapshot_reps_20240707_raw` (Jul 7, 2024)
   - `snapshot_reps_20241006_raw` (Oct 6, 2024)
   - `snapshot_reps_20250105_raw` (Jan 5, 2025)
   - `snapshot_reps_20250406_raw` (Apr 6, 2025)
   - `snapshot_reps_20250706_raw` (Jul 6, 2025)
   - `snapshot_reps_20251005_raw` (Oct 5, 2025)

4. **Verify upload:**
   - Check row count matches expected (run `SELECT COUNT(*) FROM LeadScoring.snapshot_reps_20240107_raw`)
   - Confirm CSV columns are present (will be transformed in Step 1.5)

### **Step 1.3: Validation Checklist (Raw Upload)**

- [x] All 8 raw staging tables created successfully (date-based naming: `snapshot_reps_20240107_raw`, `snapshot_reps_20240331_raw`, etc.)
- [x] All table names follow naming convention: `snapshot_reps_YYYYMMDD_raw` (date from filename)
- [x] All 8 files uploaded (no filtering - both Jan 7 and Mar 31 for Q1 2024 are included)
- [x] Row counts verified for each table
- [x] All tables are queryable in BigQuery

**Validation Report:** See `step_1_3_validation_report.md` for detailed results.

**Expected Tables:**
- `snapshot_reps_20240107_raw`, `snapshot_reps_20240331_raw`, `snapshot_reps_20240707_raw`, `snapshot_reps_20241006_raw`
- `snapshot_reps_20250105_raw`, `snapshot_reps_20250406_raw`, `snapshot_reps_20250706_raw`, `snapshot_reps_20251005_raw`

**✅ Gate:** Proceed to Step 1.5 only when all 8 raw staging tables are confirmed and queryable.

---

### **Step 1.5 (Agent Task - SQL): Transform Raw CSV to Standardized Schema**

**Objective:** Transform raw CSV files (with `Office_*` column names) to standardized schema. **Note:** `RIARepDataFeed` files do NOT contain financial metrics (AUM, client counts, custodian AUM). We use only rep metadata, licenses, tenure, location, and firm associations.

**Input Artifacts:**
- `LeadScoring.snapshot_reps_20240107_raw`, `LeadScoring.snapshot_reps_20240331_raw`, `LeadScoring.snapshot_reps_20240707_raw`, `LeadScoring.snapshot_reps_20241006_raw`, `LeadScoring.snapshot_reps_20250105_raw`, `LeadScoring.snapshot_reps_20250406_raw`, `LeadScoring.snapshot_reps_20250706_raw`, `LeadScoring.snapshot_reps_20251005_raw` (8 raw staging tables with date-based names)

**Output Artifacts:**
- `LeadScoring.snapshot_reps_20240107`, `LeadScoring.snapshot_reps_20240331`, `LeadScoring.snapshot_reps_20240707`, `LeadScoring.snapshot_reps_20241006`, `LeadScoring.snapshot_reps_20250105`, `LeadScoring.snapshot_reps_20250406`, `LeadScoring.snapshot_reps_20250706`, `LeadScoring.snapshot_reps_20251005` (8 transformed rep snapshot tables with date-based names)

**AGENTIC TASK:**

You are a data transformation agent. For each file's raw table, create a transformed table that:

1. **Maps CSV column names to target schema:**
   - `Office_State` → `Branch_State`
   - `Office_City` → `Branch_City`
   - `Office_ZipCode` → `Branch_ZipCode`
   - `Office_County` → `Branch_County`
   - `Office_Longitude` → `Branch_Longitude`
   - `Office_Latitude` → `Branch_Latitude`
   - `Office_MetropolitanArea` → `Branch_MetropolitanArea`
   - `Home_MetropolitanArea` → `Home_MetropolitanArea` (keep as-is)
   - `PriorFirm1_NumberOfYears` → `Number_YearsPriorFirm1`
   - `PriorFirm2_NumberOfYears` → `Number_YearsPriorFirm2`
   - `PriorFirm3_NumberOfYears` → `Number_YearsPriorFirm3`
   - `PriorFirm4_NumberOfYears` → `Number_YearsPriorFirm4`
   - `Number_OfficeReps` → `Number_BranchAdvisors` (map office reps to branch advisors)

2. **Derives boolean flags from Series columns:**
   - `Series7_GeneralSecuritiesRepresentative` → `Has_Series_7` (1 if = 'Yes', else 0)
   - `Series65_InvestmentAdviserRepresentative` → `Has_Series_65` (1 if = 'Yes', else 0)
   - `Series66_CombinedUniformStateLawAndIARepresentative` → `Has_Series_66` (1 if = 'Yes', else 0)
   - `Series24_GeneralSecuritiesPrincipal` → `Has_Series_24` (1 if = 'Yes', else 0)
   - `Designations_CFP` → `Has_CFP` (1 if = 'Yes', else 0)
   - `Designations_CFA` → `Has_CFA` (1 if = 'Yes', else 0)
   - `Designations_CIMA` → `Has_CIMA` (1 if = 'Yes', else 0)
   - `Designations_AIF` → `Has_AIF` (1 if = 'Yes', else 0)
   - `RegulatoryDisclosures` → `Has_Disclosure` (1 if != 'No', else 0)

3. **Handles special values:**
   - Empty strings → `NULL`
   - All numeric fields use `SAFE_CAST` to handle conversion errors gracefully

4. **Derives additional features:**
   - `AverageTenureAtPriorFirms`: Average of `Number_YearsPriorFirm1` through `Number_YearsPriorFirm4` (excluding NULLs)
   - `NumberOfPriorFirms`: Count of non-NULL prior firm fields (1-4)
   - `IsPrimaryRIAFirm`: Derive from `CASE WHEN RIAFirmCRD = PrimaryRIAFirmCRD THEN 1 ELSE 0 END` (since raw CSV doesn't have string column)
   - `DuallyRegisteredBDRIARep`: Convert `DuallyRegisteredBDRIARep` string to boolean (1 if = 'Yes', else 0)
   - `Number_IAReps`: Set to NULL (not available in RIARepDataFeed - will be NULL for all rows)

**SQL Template (for each file):**

Replace `[DATE_STR]` (YYYYMMDD format) and `[SNAPSHOT_DATE]` (DATE format) with actual values from the filename.

**⚠️ IMPORTANT: Use actual snapshot dates from CSV filenames!**
- `[DATE_STR]` = Date from filename (e.g., `20240107`, `20240331`)
- `[SNAPSHOT_DATE]` = Converted to DATE format (e.g., `DATE('2024-01-07')`, `DATE('2024-03-31')`)

**⚠️ NOTE: Financial metrics (AUM, client counts, custodian AUM) are NOT available in RIARepDataFeed and will be set to NULL.**

```sql
-- Step 1.5: Transform Raw CSV to Standardized Schema (Date: YYYYMMDD)
-- Replace [DATE_STR] and [SNAPSHOT_DATE] with actual values from filename
-- NOTE: Financial metrics are NOT available in RIARepDataFeed files - set to NULL
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.snapshot_reps_[DATE_STR]` AS
SELECT 
  -- Identifiers
  CAST(RepCRD AS STRING) as RepCRD,
  CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
  
  -- Financial metrics (NOT AVAILABLE - set to NULL)
  CAST(NULL AS FLOAT64) as TotalAssetsInMillions,
  CAST(NULL AS INT64) as Number_IAReps,
  CAST(NULL AS FLOAT64) as AUMGrowthRate_1Year,
  CAST(NULL AS FLOAT64) as AUMGrowthRate_5Year,
  
  -- Tenure metrics
  SAFE_CAST(DateBecameRep_NumberOfYears AS FLOAT64) as DateBecameRep_NumberOfYears,
  SAFE_CAST(DateOfHireAtCurrentFirm_NumberOfYears AS FLOAT64) as DateOfHireAtCurrentFirm_NumberOfYears,
  
  -- Client metrics (NOT AVAILABLE - set to NULL)
  CAST(NULL AS INT64) as NumberClients_Individuals,
  CAST(NULL AS INT64) as NumberClients_HNWIndividuals,
  CAST(NULL AS INT64) as NumberClients_RetirementPlans,
  
  -- Asset metrics (NOT AVAILABLE - set to NULL)
  CAST(NULL AS FLOAT64) as AssetsInMillions_Individuals,
  CAST(NULL AS FLOAT64) as AssetsInMillions_HNWIndividuals,
  CAST(NULL AS FLOAT64) as TotalAssets_SeparatelyManagedAccounts,
  CAST(NULL AS FLOAT64) as TotalAssets_PooledVehicles,
  CAST(NULL AS FLOAT64) as AssetsInMillions_MutualFunds,
  CAST(NULL AS FLOAT64) as AssetsInMillions_PrivateFunds,
  CAST(NULL AS FLOAT64) as AssetsInMillions_Equity_ExchangeTraded,
  
  -- Percent metrics (NOT AVAILABLE - set to NULL)
  CAST(NULL AS FLOAT64) as PercentClients_HNWIndividuals,
  CAST(NULL AS FLOAT64) as PercentClients_Individuals,
  CAST(NULL AS FLOAT64) as PercentAssets_HNWIndividuals,
  CAST(NULL AS FLOAT64) as PercentAssets_Individuals,
  CAST(NULL AS FLOAT64) as PercentAssets_MutualFunds,
  CAST(NULL AS FLOAT64) as PercentAssets_PrivateFunds,
  CAST(NULL AS FLOAT64) as PercentAssets_Equity_ExchangeTraded,
  
  -- Firm associations
  SAFE_CAST(NumberFirmAssociations AS INT64) as NumberFirmAssociations,
  SAFE_CAST(NumberRIAFirmAssociations AS INT64) as NumberRIAFirmAssociations,
  SAFE_CAST(Number_OfficeReps AS INT64) as Number_BranchAdvisors,
  
  -- Custodian AUM (NOT AVAILABLE - set to NULL)
  CAST(NULL AS FLOAT64) as CustodianAUM_Fidelity_NationalFinancial,
  CAST(NULL AS FLOAT64) as CustodianAUM_Pershing,
  CAST(NULL AS FLOAT64) as CustodianAUM_Schwab,
  CAST(NULL AS FLOAT64) as CustodianAUM_TDAmeritrade,
  
  -- Prior firm tenure (map PriorFirmN_NumberOfYears to Number_YearsPriorFirmN)
  SAFE_CAST(PriorFirm1_NumberOfYears AS FLOAT64) as Number_YearsPriorFirm1,
  SAFE_CAST(PriorFirm2_NumberOfYears AS FLOAT64) as Number_YearsPriorFirm2,
  SAFE_CAST(PriorFirm3_NumberOfYears AS FLOAT64) as Number_YearsPriorFirm3,
  SAFE_CAST(PriorFirm4_NumberOfYears AS FLOAT64) as Number_YearsPriorFirm4,
  
  -- Derived: Average tenure at prior firms
  SAFE_CAST(
    (COALESCE(PriorFirm1_NumberOfYears, 0) + 
     COALESCE(PriorFirm2_NumberOfYears, 0) + 
     COALESCE(PriorFirm3_NumberOfYears, 0) + 
     COALESCE(PriorFirm4_NumberOfYears, 0)) / 
    NULLIF(
      (CASE WHEN PriorFirm1_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN PriorFirm2_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN PriorFirm3_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN PriorFirm4_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END), 0
    ) AS FLOAT64
  ) as AverageTenureAtPriorFirms,
  
  -- Derived: Number of prior firms
  (CASE WHEN PriorFirm1_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
   CASE WHEN PriorFirm2_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
   CASE WHEN PriorFirm3_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
   CASE WHEN PriorFirm4_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END) as NumberOfPriorFirms,
  
  -- String fields (keep for reference, but will be dropped as features)
  CAST(LicensesDesignations AS STRING) as Licenses,  -- Redundant with boolean flags, will be dropped as feature
  CAST(RegulatoryDisclosures AS STRING) as RegulatoryDisclosures,  -- Redundant with Has_Disclosure, will be dropped as feature
  CAST(Education1 AS STRING) as Education,  -- High cardinality, consider dropping or creating boolean flags
  CAST(Gender AS STRING) as Gender,  -- Low cardinality, consider dropping (ethical concerns)
  CAST(NULL AS STRING) as KnownNonAdvisor,  -- Not available in raw CSV
  CASE WHEN DuallyRegisteredBDRIARep = 'Yes' THEN 1 ELSE 0 END as DuallyRegisteredBDRIARep,  -- Convert to boolean
  CASE WHEN RIAFirmCRD = PrimaryRIAFirmCRD THEN 1 ELSE 0 END as IsPrimaryRIAFirm,  -- Derive from PrimaryRIAFirmCRD
  
  -- Boolean flags from Yes/No fields (presence matters more than value)
  CASE WHEN BreakawayRep = 'Yes' THEN 1 ELSE 0 END as Is_BreakawayRep,  -- Convert to boolean
  CASE WHEN InsuranceLicensed = 'Yes' THEN 1 ELSE 0 END as Has_Insurance_License,  -- Convert to boolean
  CASE WHEN NonProducer = 'Yes' THEN 1 ELSE 0 END as Is_NonProducer,  -- Convert to boolean
  CASE WHEN IndependentContractor = 'Yes' THEN 1 ELSE 0 END as Is_IndependentContractor,  -- Convert to boolean
  CASE WHEN Owner = 'Yes' THEN 1 ELSE 0 END as Is_Owner,  -- Convert to boolean
  CASE WHEN Office_USPSCertified = 'Yes' THEN 1 ELSE 0 END as Office_USPS_Certified,  -- Convert to boolean
  CASE WHEN Home_USPSCertified = 'Yes' THEN 1 ELSE 0 END as Home_USPS_Certified,  -- Convert to boolean
  
  -- Custodian strings (NOT AVAILABLE - set to NULL)
  CAST(NULL AS STRING) as Custodian1,
  CAST(NULL AS STRING) as Custodian2,
  CAST(NULL AS STRING) as Custodian3,
  CAST(NULL AS STRING) as Custodian4,
  CAST(NULL AS STRING) as Custodian5,
  
  -- Location: Map Office_* to Branch_*
  CAST(Office_State AS STRING) as Branch_State,
  CAST(Home_State AS STRING) as Home_State,
  CAST(Office_City AS STRING) as Branch_City,
  CAST(Home_City AS STRING) as Home_City,
  CAST(Office_County AS STRING) as Branch_County,
  CAST(Home_County AS STRING) as Home_County,
  SAFE_CAST(Office_ZipCode AS FLOAT64) as Branch_ZipCode,
  SAFE_CAST(Home_ZipCode AS FLOAT64) as Home_ZipCode,
  SAFE_CAST(Office_Longitude AS FLOAT64) as Branch_Longitude,
  SAFE_CAST(Office_Latitude AS FLOAT64) as Branch_Latitude,
  SAFE_CAST(Home_Longitude AS FLOAT64) as Home_Longitude,
  SAFE_CAST(Home_Latitude AS FLOAT64) as Home_Latitude,
  CAST(Office_MetropolitanArea AS STRING) as Branch_MetropolitanArea,
  CAST(Home_MetropolitanArea AS STRING) as Home_MetropolitanArea,
  
  -- Distance
  SAFE_CAST(MilesToWork AS FLOAT64) as MilesToWork,
  
  -- Personal info (for later PII drop)
  CAST(FirstName AS STRING) as FirstName,
  CAST(LastName AS STRING) as LastName,
  CAST(Title AS STRING) as Title,
  CAST(RIAFirmName AS STRING) as RIAFirmName,
  
  -- Contact info
  CAST(Email_BusinessType AS STRING) as Email_BusinessType,
  CAST(Email_PersonalType AS STRING) as Email_PersonalType,
  CAST(SocialMedia_LinkedIn AS STRING) as SocialMedia_LinkedIn,  -- Keep URL for reference
  CASE WHEN SocialMedia_LinkedIn IS NOT NULL THEN 1 ELSE 0 END as Has_LinkedIn,  -- Boolean flag for presence
  CAST(PersonalWebsite AS STRING) as PersonalWebpage,
  CAST(FirmWebsite AS STRING) as FirmWebsite,
  CAST(NULL AS STRING) as Brochure_Keywords,  -- Not available
  CAST(NULL AS STRING) as Notes,  -- Note: There is a Notes field but it's not in the raw CSV we saw
  CAST(NULL AS STRING) as CustomKeywords,  -- Not available
  
  -- Derived: Boolean flags from Series columns
  CASE WHEN Series7_GeneralSecuritiesRepresentative = 'Yes' THEN 1 ELSE 0 END as Has_Series_7,
  CASE WHEN Series65_InvestmentAdviserRepresentative = 'Yes' THEN 1 ELSE 0 END as Has_Series_65,
  CASE WHEN Series66_CombinedUniformStateLawAndIARepresentative = 'Yes' THEN 1 ELSE 0 END as Has_Series_66,
  CASE WHEN Series24_GeneralSecuritiesPrincipal = 'Yes' THEN 1 ELSE 0 END as Has_Series_24,
  CASE WHEN Designations_CFP = 'Yes' THEN 1 ELSE 0 END as Has_CFP,
  CASE WHEN Designations_CFA = 'Yes' THEN 1 ELSE 0 END as Has_CFA,
  CASE WHEN Designations_CIMA = 'Yes' THEN 1 ELSE 0 END as Has_CIMA,
  CASE WHEN Designations_AIF = 'Yes' THEN 1 ELSE 0 END as Has_AIF,
  CASE WHEN RegulatoryDisclosures != 'No' THEN 1 ELSE 0 END as Has_Disclosure,
  
  -- Derived: Custodian relationship flags (NOT AVAILABLE - set to 0)
  CAST(0 AS INT64) as Has_Schwab_Relationship,
  CAST(0 AS INT64) as Has_Fidelity_Relationship,
  CAST(0 AS INT64) as Has_Pershing_Relationship,
  CAST(0 AS INT64) as Has_TDAmeritrade_Relationship,
  
  -- Additional metadata
  SAFE_CAST(Number_RegisteredStates AS INT64) as Number_RegisteredStates,
  
  -- Snapshot metadata: Use actual date from CSV filename
  [SNAPSHOT_DATE] as snapshot_at
  
FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_[DATE_STR]_raw`;
```

**Execution Pattern:**
Execute this SQL 8 times, once for each file, using **actual dates from CSV filenames**:
- `20240107` → Table: `snapshot_reps_20240107`, `snapshot_at = DATE('2024-01-07')` (from `RIARepDataFeed_20240107.csv`)
- `20240331` → Table: `snapshot_reps_20240331`, `snapshot_at = DATE('2024-03-31')` (from `RIARepDataFeed_20240331.csv`)
- `20240707` → Table: `snapshot_reps_20240707`, `snapshot_at = DATE('2024-07-07')` (from `RIARepDataFeed_20240707.csv`)
- `20241006` → Table: `snapshot_reps_20241006`, `snapshot_at = DATE('2024-10-06')` (from `RIARepDataFeed_20241006.csv`)
- `20250105` → Table: `snapshot_reps_20250105`, `snapshot_at = DATE('2025-01-05')` (from `RIARepDataFeed_20250105.csv`)
- `20250406` → Table: `snapshot_reps_20250406`, `snapshot_at = DATE('2025-04-06')` (from `RIARepDataFeed_20250406.csv`)
- `20250706` → Table: `snapshot_reps_20250706`, `snapshot_at = DATE('2025-07-06')` (from `RIARepDataFeed_20250706.csv`)
- `20251005` → Table: `snapshot_reps_20251005`, `snapshot_at = DATE('2025-10-05')` (from `RIARepDataFeed_20251005.csv`)

**Note:** All 8 files are processed. There is no filtering - both Jan 7 and Mar 31 files are included.

**Validation Checklist:**
- [x] All 8 transformed rep tables created successfully
- [x] Row counts match raw staging tables (no data loss) - **Perfect match: 100%**
- [x] Column names match `discovery_reps_current` schema
- [x] Boolean flags are 0 or 1 (not NULL) - **All valid**
- [x] `snapshot_at` column exists and has correct dates (from filenames) - **All correct**

**Validation Report:** See `step_1_5_validation_report.md` for detailed results.

**✅ Gate:** Proceed to Step 1.6 only when all 8 transformed rep tables are created and validated.

---

### **Step 1.6 (Agent Task - SQL): Create Firm Snapshot Tables from Rep Snapshots**

**Objective:** Aggregate rep-level snapshots to firm-level snapshots for each date. Firms are derived from reps, not separate files. **Note:** Financial metrics are NOT available from RIARepDataFeed, so firm aggregations will only include rep counts, license percentages, and geographic diversity.

**Input Artifacts:**
- `LeadScoring.snapshot_reps_20240107`, `LeadScoring.snapshot_reps_20240331`, `LeadScoring.snapshot_reps_20240707`, `LeadScoring.snapshot_reps_20241006`, `LeadScoring.snapshot_reps_20250105`, `LeadScoring.snapshot_reps_20250406`, `LeadScoring.snapshot_reps_20250706`, `LeadScoring.snapshot_reps_20251005` (8 transformed rep snapshot tables)

**Output Artifacts:**
- `LeadScoring.snapshot_firms_20240107`, `LeadScoring.snapshot_firms_20240331`, `LeadScoring.snapshot_firms_20240707`, `LeadScoring.snapshot_firms_20241006`, `LeadScoring.snapshot_firms_20250105`, `LeadScoring.snapshot_firms_20250406`, `LeadScoring.snapshot_firms_20250706`, `LeadScoring.snapshot_firms_20251005` (8 firm snapshot tables)

**AGENTIC TASK:**

You are a firm aggregation agent. For each date-based rep snapshot, create a firm snapshot by aggregating rep-level data by `RIAFirmCRD`.

**SQL Template (for each file):**

Replace `[DATE_STR]` (YYYYMMDD format) with actual value from the filename.

```sql
-- Step 1.6: Create Firm Snapshot from Rep Snapshot (Date: YYYYMMDD)
-- Replace [DATE_STR] with actual date from filename (e.g., 20240107, 20240331)
-- NOTE: Financial metrics are NOT available - set to NULL
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.snapshot_firms_[DATE_STR]` AS
WITH firm_base_data AS (
  SELECT 
    RIAFirmCRD,
    RIAFirmName,
    
    -- Basic firm metrics (aggregated from reps)
    COUNT(DISTINCT RepCRD) as total_reps,
    COUNT(*) as total_records,
    
    -- Financial metrics (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as total_firm_aum_millions,
    CAST(NULL AS FLOAT64) as avg_rep_aum_millions,
    CAST(NULL AS FLOAT64) as max_rep_aum_millions,
    CAST(NULL AS FLOAT64) as min_rep_aum_millions,
    
    -- Growth metrics (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as avg_firm_growth_1y,
    CAST(NULL AS FLOAT64) as avg_firm_growth_5y,
    
    -- Client metrics (NOT AVAILABLE - set to NULL)
    CAST(NULL AS INT64) as total_firm_clients,
    CAST(NULL AS INT64) as total_firm_hnw_clients,
    CAST(NULL AS FLOAT64) as avg_clients_per_rep,
    
    -- Professional metrics (percentages)
    AVG(Has_Series_7) as pct_reps_with_series_7,
    AVG(Has_CFP) as pct_reps_with_cfp,
    AVG(Has_Disclosure) as pct_reps_with_disclosure,
    AVG(Has_Series_65) as pct_reps_with_series_65,
    AVG(Has_Series_66) as pct_reps_with_series_66,
    AVG(Has_Series_24) as pct_reps_with_series_24,
    
    -- Firm characteristics (most common values)
    APPROX_TOP_COUNT(Home_State, 1)[OFFSET(0)].value as primary_state,
    APPROX_TOP_COUNT(Home_MetropolitanArea, 1)[OFFSET(0)].value as primary_metro_area,
    APPROX_TOP_COUNT(Branch_State, 1)[OFFSET(0)].value as primary_branch_state,
    
    -- Geographic diversity metrics
    COUNT(DISTINCT Home_State) as states_represented,
    COUNT(DISTINCT Home_MetropolitanArea) as metro_areas_represented,
    COUNT(DISTINCT Branch_State) as branch_states,
    
    -- Tenure metrics (aggregated)
    AVG(DateBecameRep_NumberOfYears) as avg_rep_experience_years,
    AVG(DateOfHireAtCurrentFirm_NumberOfYears) as avg_tenure_at_firm_years,
    AVG(AverageTenureAtPriorFirms) as avg_tenure_at_prior_firms,
    AVG(NumberOfPriorFirms) as avg_prior_firms_per_rep,
    
    -- Custodian relationships (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as total_schwab_aum,
    CAST(NULL AS FLOAT64) as total_fidelity_aum,
    CAST(NULL AS FLOAT64) as total_pershing_aum,
    CAST(NULL AS FLOAT64) as total_tdameritrade_aum,
    
    -- Investment focus (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as total_mutual_fund_aum,
    CAST(NULL AS FLOAT64) as total_private_fund_aum,
    CAST(NULL AS FLOAT64) as total_etf_aum,
    
    -- Snapshot date (all reps in same snapshot have same snapshot_at)
    MAX(snapshot_at) as snapshot_at
    
  FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_[DATE_STR]`
  WHERE RIAFirmCRD IS NOT NULL AND RIAFirmCRD != ''
  GROUP BY RIAFirmCRD, RIAFirmName
),
firm_engineered_features AS (
  SELECT 
    *,
    
    -- Firm size classification (NOT AVAILABLE - set to NULL)
    CAST(NULL AS STRING) as firm_size_tier,
    
    -- Rep efficiency metrics (NOT AVAILABLE - set to NULL)
    CAST(NULL AS FLOAT64) as aum_per_rep,
    
    -- Geographic diversity scores
    CASE WHEN states_represented > 5 THEN 1 ELSE 0 END as multi_state_firm,
    CASE WHEN states_represented > 10 THEN 1 ELSE 0 END as national_firm
    
  FROM firm_base_data
)
SELECT * FROM firm_engineered_features;
```

**Execution Pattern:**
Execute this SQL 8 times, once for each date-based table (same dates as Step 1.5):
- `20240107`, `20240331`, `20240707`, `20241006`, `20250105`, `20250406`, `20250706`, `20251005`

**Validation Checklist:**
- [x] All 8 firm snapshot tables created successfully
- [x] Firm count is reasonable (expected: ~30,000-40,000 firms per quarter) - **All within range: 40K-42K**
- [x] `snapshot_at` column exists and has correct dates (from filenames) - **All correct**
- [x] `total_reps` > 0 for all firms (no zero-rep firms) - **0 zero-rep firms across all tables**

**Validation Report:** See `step_1_6_validation_report.md` for detailed results.

**✅ Gate:** Proceed to Step 1.7 only when all 8 firm snapshot tables are created and validated.

---

### **Step 1.7: Validate Snapshot Schemas Against Data Contracts**

**Objective:** Verify that all 8 rep tables and all 8 firm tables match their respective data contracts created in Step 0. This is critical before creating the UNION ALL views in Step 2.

**AGENTIC TASK:**

You are a data validation agent. You must:

- Load the golden schema contracts from `config/v6_feature_contract.json` and `config/v6_firm_feature_contract.json` (created in Step 0).
- Write and execute SQL queries that compare each snapshot table's `INFORMATION_SCHEMA.COLUMNS` against the contract schemas.
- For each of the 8 rep snapshots (`snapshot_reps_20240107`, `snapshot_reps_20240331`, etc.), validate:
  - Column count matches the contract
  - All required column names exist
  - Column data types match the contract (allowing for compatible type variations)
  - Nullable constraints match where specified
- Repeat this process for all 8 firm snapshots against `v6_firm_feature_contract.json`.
- Create a validation report `step_1_7_schema_validation_report.md`.
  - If all schemas match, the report should state: `STATUS: ✅ SUCCESS - All 8 rep tables and 8 firm tables match their data contracts.`
  - If there is a mismatch, the report must state: `STATUS: 🛑 FAILED` and list:
    - Exact table names that failed
    - Missing columns
    - Type mismatches
    - Nullable constraint violations

**Validation Checklist:**

- [x] `step_1_7_schema_validation_report.md` generated - **Report created**
- [x] Report status is ✅ SUCCESS for both Reps and Firms - **All 16 tables validated successfully**
- [x] All 16 tables validated against their contracts - **8 rep tables + 8 firm tables = 16/16 PASS**

**Validation Results:**
- ✅ All 8 rep tables match `v6_feature_contract.json` (all contract fields present)
- ✅ All 8 firm tables match `v6_firm_feature_contract.json` (all contract fields present)
- ✅ Extra columns in tables are acceptable (tables have more fields than Step 3.1 selects)

**Validation Report:** See `step_1_7_schema_validation_report.md` for detailed results.

**✅ Gate:** **STOP** if any snapshot file mismatches the data contract. Proceed to Step 2 only if this validation passes. A schema mismatch will cause Step 2 to fail.

---

## 🔗 **Step 2: Create Master Snapshot Views**

**Objective:** Combine 16 individual tables (8 rep snapshots + 8 firm snapshots) into 2 unified views for easy point-in-time joins

### **Step 2.1: Create `v_discovery_reps_all_vintages` View**

1. **Open BigQuery Console** → SQL Editor

2. **Create the view** with this SQL pattern:

```sql
CREATE OR REPLACE VIEW `savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages` AS
SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240107`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240331`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240707`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20241006`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20250105`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20250406`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20250706`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20251005`  -- snapshot_at already included
```

3. **Verify view creation:**
   - Run: `SELECT COUNT(*) FROM LeadScoring.v_discovery_reps_all_vintages`
   - Should return sum of all 8 rep tables
   - Verify `snapshot_at` column exists

### **Step 2.2: Create `v_discovery_firms_all_vintages` View**

1. **Repeat the same process** for firms data:

```sql
CREATE OR REPLACE VIEW `savvy-gtm-analytics.LeadScoring.v_discovery_firms_all_vintages` AS
SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20240107`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20240331`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20240707`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20241006`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20250105`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20250406`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20250706`  -- snapshot_at already included

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20251005`  -- snapshot_at already included
```

2. **Verify view creation:**
   - Run: `SELECT COUNT(*) FROM LeadScoring.v_discovery_firms_all_vintages`
   - Should return sum of all 8 firm tables

### **Step 2.3: Validation**

**Validation Checklist:**
- [x] `v_discovery_reps_all_vintages` view created successfully
- [x] `v_discovery_firms_all_vintages` view created successfully
- [x] Both views have `snapshot_at` column
- [x] Row counts match sum of individual snapshot tables
- [x] All 8 snapshot dates present in both views

**Validation Results:**
- ✅ Rep view: 3,845,530 rows across 8 snapshots
- ✅ Firm view: 328,184 rows across 8 snapshots
- ✅ Date range: 2024-01-07 to 2025-10-05 (all 8 dates present)

**Validation Report:** See `step_2_master_view_report.md` for detailed results.

**✅ Gate:** Proceed to Step 3 only when both views are created and validated.

---

### **Step 2.4: Generate Validation Report**

1. **Create `step_2_master_view_report.md`** with:

```markdown
# Master View Creation Report

**Generated:** [Date]

## View Summary

### v_discovery_reps_all_vintages
- **Total Rows:** [count]
- **Quarters Covered:** 2024 Q1 - 2025 Q4
- **Status:** ✅ ACTIVE

### v_discovery_firms_all_vintages
- **Total Rows:** [count]
- **Quarters Covered:** 2024 Q1 - 2025 Q4
- **Status:** ✅ ACTIVE

## Validation Queries

[Include sample queries and results]
```

### **Step 2.4: Validation Checklist**

- [ ] `v_discovery_reps_all_vintages` view created successfully
- [ ] `v_discovery_firms_all_vintages` view created successfully
- [ ] Both views are queryable
- [ ] `snapshot_at` column exists in both views
- [ ] Row counts match sum of individual tables
- [ ] `step_5_2_master_view_report.md` generated

**✅ Gate:** Proceed to Step 3 only when both master views are created and queryable.

---

## 🎯 **Step 3: Build V6 Training Set (Point-in-Time Join)**

#### **Step 3.1 (Agent Task - SQL): Create Staging Join Table (V6)**

**Note:** This step only performs the point-in-time join and selects raw Keep features into a staging table. This makes debugging joins and upstream data issues much easier.

**Input Artifacts:**
- `savvy-gtm-analytics.SavvyGTMData.Lead`
- `LeadScoring.v_discovery_reps_all_vintages` (Step 2)
- `LeadScoring.v_discovery_firms_all_vintages` (Step 2)

**Output Artifacts:**
- `LeadScoring.step_3_1_staging_join_v6_[YYYYMMDD_HHMM]` (Versioned BQ table)

**AGENTIC TASK:** Execute the SQL below to create a versioned staging join table. The agent must:

1. Generate a timestamp version string: `YYYYMMDD_HHMM` (e.g., `20241215_1430`)
2. Replace `[VERSION]` in the table name with this timestamp
3. Execute the query to create the versioned table

```sql
-- Step 3.1: V6 Staging Join Table (Versioned)
-- Replace [VERSION] with actual timestamp: YYYYMMDD_HHMM
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_1_staging_join_v6_[VERSION]` AS
WITH
LeadsWithContactDate AS (
    SELECT 
        Id,
        FA_CRD__c,
        Stage_Entered_Contacting__c,
        Stage_Entered_Call_Scheduled__c,
        DATE(Stage_Entered_Contacting__c) as contact_date  -- ⭐ Use actual date, not quarter
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE Stage_Entered_Contacting__c IS NOT NULL
      AND FA_CRD__c IS NOT NULL
),
PointInTimeJoin AS (
    SELECT
        l.*,
        -- Reps Keep Features (Note: Financial metrics are NULL from RIARepDataFeed)
        reps.RepCRD,
        reps.RIAFirmCRD,
        reps.TotalAssetsInMillions,  -- NULL (not available)
        reps.TotalAssets_PooledVehicles,  -- NULL (not available)
        reps.TotalAssets_SeparatelyManagedAccounts,  -- NULL (not available)
        reps.NumberClients_Individuals,  -- NULL (not available)
        reps.NumberClients_HNWIndividuals,  -- NULL (not available)
        reps.NumberClients_RetirementPlans,  -- NULL (not available)
        reps.PercentClients_Individuals,  -- NULL (not available)
        reps.PercentClients_HNWIndividuals,  -- NULL (not available)
        reps.AssetsInMillions_MutualFunds,  -- NULL (not available)
        reps.AssetsInMillions_PrivateFunds,  -- NULL (not available)
        reps.AssetsInMillions_Equity_ExchangeTraded,  -- NULL (not available)
        reps.PercentAssets_MutualFunds,  -- NULL (not available)
        reps.PercentAssets_PrivateFunds,  -- NULL (not available)
        reps.PercentAssets_Equity_ExchangeTraded,  -- NULL (not available)
        reps.Number_IAReps,  -- NULL (not available)
        reps.Number_BranchAdvisors,
        reps.NumberFirmAssociations,
        reps.NumberRIAFirmAssociations,
        reps.AUMGrowthRate_1Year,  -- NULL (not available)
        reps.AUMGrowthRate_5Year,  -- NULL (not available)
        reps.DateBecameRep_NumberOfYears,
        reps.DateOfHireAtCurrentFirm_NumberOfYears,
        reps.Number_YearsPriorFirm1,
        reps.Number_YearsPriorFirm2,
        reps.Number_YearsPriorFirm3,
        reps.Number_YearsPriorFirm4,
        reps.AverageTenureAtPriorFirms,
        reps.NumberOfPriorFirms,
        reps.IsPrimaryRIAFirm,
        reps.DuallyRegisteredBDRIARep,
        reps.Has_Series_7,
        reps.Has_Series_65,
        reps.Has_Series_66,
        reps.Has_Series_24,
        reps.Has_CFP,
        reps.Has_CFA,
        reps.Has_CIMA,
        reps.Has_AIF,
        reps.Has_Disclosure,
        reps.Is_BreakawayRep,
        reps.Has_Insurance_License,
        reps.Is_NonProducer,
        reps.Is_IndependentContractor,
        reps.Is_Owner,
        reps.Office_USPS_Certified,
        reps.Home_USPS_Certified,
        reps.Has_LinkedIn,
        reps.Home_MetropolitanArea,
        reps.Branch_State,
        reps.Home_State,
        reps.Home_ZipCode,
        reps.Branch_ZipCode,
        reps.MilesToWork,
        reps.SocialMedia_LinkedIn,
        reps.CustodianAUM_Schwab,  -- NULL (not available)
        reps.CustodianAUM_Fidelity_NationalFinancial,  -- NULL (not available)
        reps.CustodianAUM_Pershing,  -- NULL (not available)
        reps.CustodianAUM_TDAmeritrade,  -- NULL (not available)
        reps.Has_Schwab_Relationship,  -- 0 (not available)
        reps.Has_Fidelity_Relationship,  -- 0 (not available)
        reps.Has_Pershing_Relationship,  -- 0 (not available)
        reps.Has_TDAmeritrade_Relationship,  -- 0 (not available)
        reps.Number_RegisteredStates,
        reps.snapshot_at as rep_snapshot_at,  -- Track which snapshot was used
        -- Firms Keep Features (Note: Financial metrics are NULL from RIARepDataFeed)
        firms.total_firm_aum_millions,  -- NULL (not available)
        firms.total_reps,
        firms.total_firm_clients,  -- NULL (not available)
        firms.total_firm_hnw_clients,  -- NULL (not available)
        firms.avg_clients_per_rep,  -- NULL (not available)
        firms.aum_per_rep,  -- NULL (not available)
        firms.avg_firm_growth_1y,  -- NULL (not available)
        firms.avg_firm_growth_5y,  -- NULL (not available)
        firms.pct_reps_with_cfp,
        firms.pct_reps_with_disclosure,
        firms.firm_size_tier,  -- NULL (not available)
        firms.multi_state_firm,
        firms.national_firm,
        firms.snapshot_at as firm_snapshot_at  -- Track which snapshot was used
    FROM LeadsWithContactDate l
    -- ⭐ KEY CHANGE: Use most recent snapshot_at <= contact_date
    -- Use QUALIFY to get the most recent snapshot for each rep
    LEFT JOIN (
        SELECT 
            l2.FA_CRD__c,
            l2.contact_date,
            reps.*
        FROM LeadsWithContactDate l2
        JOIN `LeadScoring.v_discovery_reps_all_vintages` reps
            ON reps.RepCRD = l2.FA_CRD__c
            AND reps.snapshot_at <= l2.contact_date
        QUALIFY ROW_NUMBER() OVER (PARTITION BY l2.FA_CRD__c, l2.contact_date ORDER BY reps.snapshot_at DESC) = 1
    ) reps
        ON reps.FA_CRD__c = l.FA_CRD__c
        AND reps.contact_date = l.contact_date
    -- Get firm data using the same approach
    LEFT JOIN (
        SELECT 
            reps_lookup.RepCRD,
            l3.contact_date,
            firms.*
        FROM LeadsWithContactDate l3
        JOIN `LeadScoring.v_discovery_reps_all_vintages` reps_lookup
            ON reps_lookup.RepCRD = l3.FA_CRD__c
            AND reps_lookup.snapshot_at <= l3.contact_date
        QUALIFY ROW_NUMBER() OVER (PARTITION BY reps_lookup.RepCRD, l3.contact_date ORDER BY reps_lookup.snapshot_at DESC) = 1
        LEFT JOIN `LeadScoring.v_discovery_firms_all_vintages` firms
            ON firms.RIAFirmCRD = reps_lookup.RIAFirmCRD
            AND firms.snapshot_at <= l3.contact_date
        QUALIFY ROW_NUMBER() OVER (PARTITION BY firms.RIAFirmCRD, l3.contact_date ORDER BY firms.snapshot_at DESC) = 1
    ) firms
        ON firms.RepCRD = l.FA_CRD__c
        AND firms.contact_date = l.contact_date
)
SELECT * FROM PointInTimeJoin;
```

**Validation Checklist:**
- [x] Staging table created successfully: `step_3_1_staging_join_v6_20251104_2217`
- [x] Row count verified: 46,299 total leads
- [x] Rep match rate: 97.4% (45,108 leads with rep data)
- [x] Firm match rate: 97.4% (45,108 leads with firm data)
- [x] All 8 snapshot dates used correctly (2024-01-07 to 2025-10-05)

**✅ Gate:** Proceed to Step 3.2 only when the staging table is populated. Run a `SELECT COUNT(*)` to verify rows exist.

#### **Step 3.2 (Agent Task - SQL): Apply Feature Engineering & Create Final Training Set (V6)**

**Input Artifacts:**
- `LeadScoring.step_3_1_staging_join_v6_[VERSION]` (Step 3.1 - use the latest versioned table)

**Output Artifacts:**
- `LeadScoring.step_3_3_training_dataset_v6_[VERSION]` (Versioned BQ table)
- `step_3_3_class_imbalance_analysis_v6_[VERSION].md`

**AGENTIC TASK:** Execute the SQL below to read from the versioned staging table, compute engineered features optimized for **30-day MQL conversion** using XGBoost, create labels/filters, and filter out invalid records. The agent must:

1. Identify the latest versioned staging table from Step 3.1
2. Use the same version string for the output table
3. Replace `[VERSION]` and `[STAGING_VERSION]` in the SQL below

**Target:** `target_label = 1` if `Call_Scheduled` occurred **≤ 30 days** after `Stage_Entered_Contacting__c`; else 0.

**Feature Philosophy:** All engineered features are designed to expose **maturity, reachability, and operational friction**—drivers of fast (≤30-day) meeting scheduling—without any financial fields. They are **PIT-safe** (computed only from snapshots ≤ contact date) and **auditable**.

```sql
-- Step 3.2: V6 Final Training Set with Engineering (Versioned)
-- Replace [VERSION] with same timestamp used in Step 3.1
-- Replace [STAGING_VERSION] with the version from Step 3.1
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]` AS
WITH
StagingData AS (
    SELECT * FROM `savvy-gtm-analytics.LeadScoring.step_3_1_staging_join_v6_[STAGING_VERSION]`
),
EngineeredData AS (
    SELECT
        p.*,
        
        -- ===== FINANCIAL-DERIVED FEATURES (NULL - Not Available) =====
        -- Note: Financial metrics are NOT available in RIARepDataFeed files
        CAST(NULL AS FLOAT64) as AUM_per_Client,  -- Requires TotalAssetsInMillions and NumberClients_Individuals
        CAST(NULL AS FLOAT64) as AUM_per_IARep,  -- Requires TotalAssetsInMillions and Number_IAReps
        CAST(NULL AS FLOAT64) as Clients_per_IARep,  -- Requires NumberClients_Individuals and Number_IAReps
        CAST(NULL AS FLOAT64) as Clients_per_BranchAdvisor,  -- Requires NumberClients_Individuals
        CAST(NULL AS FLOAT64) as Branch_Advisor_Density,  -- Requires Number_IAReps
        CAST(NULL AS FLOAT64) as HNW_Client_Ratio,  -- Requires NumberClients_HNWIndividuals and NumberClients_Individuals
        CAST(NULL AS FLOAT64) as HNW_Asset_Concentration,  -- Requires AssetsInMillions_HNWIndividuals and TotalAssetsInMillions
        CAST(NULL AS FLOAT64) as Individual_Asset_Ratio,  -- Requires AssetsInMillions_Individuals and TotalAssetsInMillions
        CAST(NULL AS FLOAT64) as Alternative_Investment_Focus,  -- Requires AssetsInMillions_MutualFunds/PrivateFunds and TotalAssetsInMillions
        CAST(NULL AS INT64) as Positive_Growth_Trajectory,  -- Requires AUMGrowthRate_1Year and 5Year
        CAST(NULL AS INT64) as Accelerating_Growth,  -- Requires AUMGrowthRate_1Year and 5Year
        
        -- ===== A) REP & FIRM MATURITY PROXIES (PIT-Safe) =====
        -- Why: Seniority, stability, and registration breadth correlate with fast scheduling behavior within 30 days
        CASE WHEN p.DateBecameRep_NumberOfYears >= 10 THEN 1 ELSE 0 END as is_veteran_advisor,
        CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears < 2 THEN 1 ELSE 0 END as is_new_to_firm,
        CASE WHEN p.AverageTenureAtPriorFirms < 3 THEN 1 ELSE 0 END as avg_prior_firm_tenure_lt3,
        CASE WHEN p.NumberOfPriorFirms > 3 AND p.AverageTenureAtPriorFirms < 3 THEN 1 ELSE 0 END as high_turnover_flag,
        CASE WHEN p.NumberRIAFirmAssociations > 1 THEN 1 ELSE 0 END as multi_ria_relationships,
        CASE WHEN (p.NumberFirmAssociations > 2 OR p.NumberRIAFirmAssociations > 1) THEN 1 ELSE 0 END as complex_registration,
        CASE WHEN p.Number_RegisteredStates > 10 THEN 1 ELSE 0 END as multi_state_registered,
        -- Firm stability (m5 formula: tenure at current firm / (number of prior firms + 1))
        SAFE_DIVIDE(p.DateOfHireAtCurrentFirm_NumberOfYears, NULLIF((p.NumberOfPriorFirms + 1), 0)) as Firm_Stability_Score,
        
        -- ===== B) LICENSES/DESIGNATIONS FOOTPRINT (Boolean Rollups) =====
        -- Why: Professional footprint often proxies engagement and readiness to take a meeting quickly
        (COALESCE(p.Has_Series_7, 0) + COALESCE(p.Has_Series_65, 0) + COALESCE(p.Has_Series_66, 0) + COALESCE(p.Has_Series_24, 0)) AS license_count,
        (COALESCE(p.Has_CFP, 0) + COALESCE(p.Has_CFA, 0) + COALESCE(p.Has_CIMA, 0) + COALESCE(p.Has_AIF, 0)) AS designation_count,
        
        -- ===== C) GEOGRAPHY & LOGISTICS (Operational Friction) =====
        -- Why: Lower travel/logistics friction can speed time-to-meeting
        CASE 
            WHEN p.Branch_State IS NOT NULL AND p.Home_State IS NOT NULL AND p.Branch_State != p.Home_State THEN 1 
            ELSE 0 
        END AS branch_vs_home_mismatch,
        CASE 
            WHEN p.Home_MetropolitanArea IS NULL AND p.Home_ZipCode IS NOT NULL THEN SUBSTR(CAST(CAST(p.Home_ZipCode AS INT64) AS STRING), 1, 3)
            ELSE NULL
        END as Home_Zip_3Digit,
        CASE WHEN p.MilesToWork > 50 THEN 1 ELSE 0 END as remote_work_indicator,
        CASE WHEN p.MilesToWork <= 10 THEN 1 ELSE 0 END as local_advisor,
        
        -- ===== D) FIRM CONTEXT (Rep-Level Aggregates from Firm Snapshot) =====
        -- Why: Team size and credential density proxy go-to-market sophistication and response speed
        CASE
            WHEN p.total_reps IS NULL THEN NULL
            WHEN p.total_reps = 1 THEN '1'
            WHEN p.total_reps BETWEEN 2 AND 5 THEN '2_5'
            WHEN p.total_reps BETWEEN 6 AND 20 THEN '6_20'
            ELSE '21_plus'
        END AS firm_rep_count_bin,
        
        -- ===== E) CONTACTABILITY & PRESENCE =====
        -- Why: Reachable contacts are more likely to convert inside 30 days
        CASE WHEN p.Has_LinkedIn = 1 THEN 1 ELSE 0 END AS has_linkedin,
        CASE WHEN p.Email_BusinessType IS NOT NULL THEN 1 ELSE 0 END AS email_business_type_flag,
        CASE WHEN p.Email_PersonalType IS NOT NULL THEN 1 ELSE 0 END AS email_personal_type_flag,
        
        -- ===== F) MISSINGNESS AS SIGNAL (Never Silently Impute) =====
        -- Why: Structured missingness carries signal (data quality and maturity)
        CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears IS NULL THEN 1 ELSE 0 END AS doh_current_years_is_missing,
        CASE WHEN p.DateBecameRep_NumberOfYears IS NULL THEN 1 ELSE 0 END AS became_rep_years_is_missing,
        CASE WHEN p.AverageTenureAtPriorFirms IS NULL THEN 1 ELSE 0 END AS avg_prior_firm_tenure_is_missing,
        CASE WHEN p.NumberOfPriorFirms IS NULL THEN 1 ELSE 0 END AS num_prior_firms_is_missing,
        CASE WHEN p.Number_RegisteredStates IS NULL THEN 1 ELSE 0 END AS num_registered_states_is_missing,
        CASE WHEN p.total_reps IS NULL THEN 1 ELSE 0 END AS firm_total_reps_is_missing,
        (
            (CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.DateBecameRep_NumberOfYears IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.AverageTenureAtPriorFirms IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.NumberOfPriorFirms IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.Number_RegisteredStates IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.total_reps IS NULL THEN 1 ELSE 0 END)
        ) AS missing_feature_count,
        
        -- ===== G) SIMPLE INTERACTIONS (Bounded; Avoid Blow-ups) =====
        -- Why: Amplify consistent patterns without overfitting
        (CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears < 2 THEN 1 ELSE 0 END) * COALESCE(p.Has_Series_65, 0) AS is_new_to_firm_x_has_series65,
        (CASE WHEN p.DateBecameRep_NumberOfYears >= 10 THEN 1 ELSE 0 END) * COALESCE(p.Has_CFP, 0) AS veteran_x_cfp,
        
        -- Additional derived features (from existing data)
        SAFE_DIVIDE(p.Number_BranchAdvisors, NULLIF(p.NumberFirmAssociations, 0)) as Branch_Advisors_per_Firm_Association,
        -- Labels
        CASE 
            WHEN p.Stage_Entered_Call_Scheduled__c IS NOT NULL 
             AND DATE(p.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(p.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
            THEN 1 ELSE 0 
        END as target_label,
        -- Filters
        (DATE(p.Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as is_in_right_censored_window,
        DATE_DIFF(DATE(p.Stage_Entered_Call_Scheduled__c), DATE(p.Stage_Entered_Contacting__c), DAY) as days_to_conversion
    FROM StagingData p
)
SELECT 
    Id,
    FA_CRD__c,
    RIAFirmCRD,
    target_label,
    -- Reps Keep
    TotalAssetsInMillions, TotalAssets_PooledVehicles, TotalAssets_SeparatelyManagedAccounts,
    NumberClients_Individuals, NumberClients_HNWIndividuals, NumberClients_RetirementPlans,
    PercentClients_Individuals, PercentClients_HNWIndividuals, AssetsInMillions_MutualFunds,
    AssetsInMillions_PrivateFunds, AssetsInMillions_Equity_ExchangeTraded, PercentAssets_MutualFunds,
    PercentAssets_PrivateFunds, PercentAssets_Equity_ExchangeTraded, Number_IAReps,
    Number_BranchAdvisors, NumberFirmAssociations, NumberRIAFirmAssociations, AUMGrowthRate_1Year,
    AUMGrowthRate_5Year, DateBecameRep_NumberOfYears, DateOfHireAtCurrentFirm_NumberOfYears,
    Number_YearsPriorFirm1, Number_YearsPriorFirm2, Number_YearsPriorFirm3, Number_YearsPriorFirm4,
    AverageTenureAtPriorFirms, NumberOfPriorFirms, IsPrimaryRIAFirm, DuallyRegisteredBDRIARep,
    Has_Series_7, Has_Series_65, Has_Series_66, Has_Series_24, Has_CFP, Has_CFA, Has_CIMA,
    Has_AIF, Has_Disclosure, Is_BreakawayRep, Has_Insurance_License, Is_NonProducer,
    Is_IndependentContractor, Is_Owner, Office_USPS_Certified, Home_USPS_Certified, Has_LinkedIn,
    Home_MetropolitanArea, Branch_State, Home_State,
    MilesToWork, SocialMedia_LinkedIn, CustodianAUM_Schwab, CustodianAUM_Fidelity_NationalFinancial,
    CustodianAUM_Pershing, CustodianAUM_TDAmeritrade, Has_Schwab_Relationship,
    Has_Fidelity_Relationship, Has_Pershing_Relationship, Has_TDAmeritrade_Relationship,
    -- Firms Keep
    total_firm_aum_millions, total_reps, total_firm_clients, total_firm_hnw_clients,
    avg_clients_per_rep, aum_per_rep, avg_firm_growth_1y, avg_firm_growth_5y,
    pct_reps_with_cfp, pct_reps_with_disclosure, firm_size_tier, multi_state_firm, national_firm,
    -- Engineered Features (No-Financials, 30-Day MQL Target)
    -- A) Rep & Firm Maturity Proxies
    is_veteran_advisor, is_new_to_firm, avg_prior_firm_tenure_lt3, high_turnover_flag,
    multi_ria_relationships, complex_registration, multi_state_registered, Firm_Stability_Score,
    -- B) Licenses/Designations Footprint
    license_count, designation_count,
    -- C) Geography & Logistics
    branch_vs_home_mismatch, Home_Zip_3Digit, remote_work_indicator, local_advisor,
    -- D) Firm Context
    firm_rep_count_bin,
    -- E) Contactability & Presence
    has_linkedin, email_business_type_flag, email_personal_type_flag,
    -- F) Missingness as Signal
    doh_current_years_is_missing, became_rep_years_is_missing, avg_prior_firm_tenure_is_missing,
    num_prior_firms_is_missing, num_registered_states_is_missing, firm_total_reps_is_missing, missing_feature_count,
    -- G) Simple Interactions
    is_new_to_firm_x_has_series65, veteran_x_cfp,
    Branch_Advisors_per_Firm_Association,
    -- Financial-derived (NULL - not available)
    AUM_per_Client, AUM_per_IARep, Clients_per_IARep, Clients_per_BranchAdvisor,
    Branch_Advisor_Density, HNW_Client_Ratio, HNW_Asset_Concentration, Individual_Asset_Ratio,
    Alternative_Investment_Focus, Positive_Growth_Trajectory, Accelerating_Growth,
    -- Add key filter columns (temp)
    days_to_conversion
FROM EngineeredData
WHERE is_in_right_censored_window = false
  AND (days_to_conversion >= 0 OR days_to_conversion IS NULL);
```

**Note:** Financial-based engineered features (AUM_per_Client, AUM_per_IARep, etc.) are set to NULL because financial metrics are not available in RIARepDataFeed files. The model will train using tenure-based, license-based, geographic, contactability, and missingness features optimized for 30-day MQL conversion.

**Why These Features (30-Day MQL Target):**
- **Maturity Proxies (A):** Seniority, stability, and registration breadth correlate with fast scheduling behavior within 30 days
- **License/Designation Footprint (B):** Professional footprint often proxies engagement and readiness to take a meeting quickly
- **Geography & Logistics (C):** Lower travel/logistics friction can speed time-to-meeting
- **Firm Context (D):** Team size and credential density proxy go-to-market sophistication and response speed
- **Contactability (E):** Reachable contacts are more likely to convert inside 30 days
- **Missingness as Signal (F):** Structured missingness carries signal (data quality and maturity)
- **Simple Interactions (G):** Amplify consistent patterns without overfitting

**MANDATORY ASSERTION QUERIES (post-create):**

The agent must execute all four assertions below. Replace `[VERSION]` with the actual version string.

**1. Negative Days to Conversion Check:**
```sql
SELECT COUNT(*) AS negative_days_count
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`
WHERE days_to_conversion < 0;
```
**Expected:** `negative_days_count = 0`

**2. Rep Match Rate Check:**
```sql
WITH 
LeadsWithQuarter AS (
    SELECT DISTINCT FA_CRD__c
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE Stage_Entered_Contacting__c IS NOT NULL AND FA_CRD__c IS NOT NULL
),
MatchedReps AS (
    SELECT DISTINCT FA_CRD__c
    FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`
)
SELECT 
    (SELECT COUNT(*) FROM MatchedReps) / (SELECT COUNT(*) FROM LeadsWithQuarter) AS rep_match_rate;
```
**Expected:** `rep_match_rate >= 0.85` (85%+ match rate)

**3. Firm Match Rate Check:**
```sql
SELECT 
    COUNT(DISTINCT CASE WHEN RIAFirmCRD IS NOT NULL THEN FA_CRD__c END) / COUNT(DISTINCT FA_CRD__c) AS firm_match_rate
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`;
```
**Expected:** `firm_match_rate >= 0.75` (75%+ firm match rate)

**4. Snapshot Date Integrity Check:**
```sql
-- Verify snapshot_at dates are valid (from our 8 snapshot files)
SELECT COUNTIF(rep_snapshot_at NOT IN (
    DATE('2024-01-07'), DATE('2024-03-31'), DATE('2024-07-07'), DATE('2024-10-06'),
    DATE('2025-01-05'), DATE('2025-04-06'), DATE('2025-07-06'), DATE('2025-10-05')
)) AS invalid_snapshot_count
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`
WHERE rep_snapshot_at IS NOT NULL;
```
**Expected:** `invalid_snapshot_count = 0`

**5. PIT Integrity Check (Zero Tolerance for Future-Dated Features):**
```sql
-- Zero tolerance for future-dated features (hard fail)
SELECT COUNT(*) AS post_contact_features
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`
WHERE rep_snapshot_at > DATE(Stage_Entered_Contacting__c)
   OR firm_snapshot_at > DATE(Stage_Entered_Contacting__c);
```
**Expected:** `post_contact_features = 0` (HARD FAIL if > 0)

**6. Value Domain Checks (Boolean Features):**
```sql
-- Verify boolean features are in {0, 1}
SELECT 
  COUNTIF(is_veteran_advisor NOT IN (0, 1)) AS invalid_veteran,
  COUNTIF(is_new_to_firm NOT IN (0, 1)) AS invalid_new_to_firm,
  COUNTIF(high_turnover_flag NOT IN (0, 1)) AS invalid_turnover,
  COUNTIF(multi_ria_relationships NOT IN (0, 1)) AS invalid_multi_ria,
  COUNTIF(complex_registration NOT IN (0, 1)) AS invalid_complex_reg,
  COUNTIF(remote_work_indicator NOT IN (0, 1)) AS invalid_remote,
  COUNTIF(local_advisor NOT IN (0, 1)) AS invalid_local,
  COUNTIF(has_linkedin NOT IN (0, 1)) AS invalid_linkedin,
  COUNTIF(email_business_type_flag NOT IN (0, 1)) AS invalid_email_business,
  COUNTIF(email_personal_type_flag NOT IN (0, 1)) AS invalid_email_personal
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`;
```
**Expected:** All counts = 0

**7. Enum Domain Check (Firm Rep Count Bin):**
```sql
-- Verify firm_rep_count_bin values are valid
SELECT COUNTIF(firm_rep_count_bin NOT IN ('1', '2_5', '6_20', '21_plus') AND firm_rep_count_bin IS NOT NULL) AS invalid_bin
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`;
```
**Expected:** `invalid_bin = 0`

**8. Null Safety Check (No Implicit Imputation):**
```sql
-- Verify missingness flags are deterministic (0 or 1)
SELECT 
  COUNTIF(doh_current_years_is_missing NOT IN (0, 1)) AS invalid_doh_missing,
  COUNTIF(became_rep_years_is_missing NOT IN (0, 1)) AS invalid_became_missing,
  COUNTIF(missing_feature_count < 0 OR missing_feature_count > 6) AS invalid_missing_count
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`;
```
**Expected:** All counts = 0

**Imbalance Metrics (write to `step_3_3_class_imbalance_analysis_v6_[VERSION].md`):**
```sql
SELECT 
  'Class Imbalance Metrics (V6 - True Vintage)' AS metric_type,
  COUNT(*) AS total_samples,
  COUNT(CASE WHEN target_label = 1 THEN 1 END) AS positive_samples,
  COUNT(CASE WHEN target_label = 0 THEN 1 END) AS negative_samples,
  ROUND(COUNT(CASE WHEN target_label = 1 THEN 1 END) / COUNT(*) * 100, 2) AS positive_class_percent,
  ROUND(COUNT(CASE WHEN target_label = 0 THEN 1 END) / COUNT(CASE WHEN target_label = 1 THEN 1 END), 2) AS imbalance_ratio
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`;
```

**Validation Checklist:**
- [x] Training dataset created successfully: `step_3_3_training_dataset_v6_20251104_2217`
- [x] All 8 validation assertions passed:
  - [x] Negative days check: 0 negative days ✓
  - [x] Rep match rate: 90.6% (≥85% threshold) ✓
  - [x] Firm match rate: 97.7% (≥75% threshold) ✓
  - [x] Snapshot date integrity: 0 invalid dates ✓
  - [x] PIT integrity: 0 post-contact features ✓ (HARD PASS - no temporal leakage)
  - [x] Boolean domain checks: All valid ✓
  - [x] Enum domain check: All valid ✓
  - [x] Null safety check: All valid ✓
- [x] Class imbalance analysis completed: `step_3_3_class_imbalance_analysis_v6_20251104_2217.md`
- [x] Final dataset: 41,942 samples (after filtering right-censored window)
- [x] Positive class: 3.39% (1,422 samples), Imbalance ratio: 28.50:1

**Validation Results:**
- ✅ All assertions passed - dataset is temporally correct and ready for training
- ✅ Class imbalance: 28.50:1 (expected for lead scoring - consider class balancing techniques)

**✅ Gate:** Proceed to Step 3.3 only if:
- `negative_days_count = 0` ✓
- `rep_match_rate >= 0.85` ✓ (90.6%)
- `firm_match_rate >= 0.75` ✓ (97.7%)
- `invalid_snapshot_count = 0` ✓
- `post_contact_features = 0` ✓ (HARD PASS - no future-dated features)
- All boolean value domain checks pass (counts = 0) ✓
- `invalid_bin = 0` (firm_rep_count_bin domain check) ✓
- All null safety checks pass (counts = 0) ✓

**STATUS:** ✅ **ALL GATES PASSED** - Ready for Step 3.3

---

### **Step 3.3 (Agent Task - SQL): Promote New Data Build**

**Objective:** Atomically promote the validated, versioned training dataset to production for model training.

**AGENTIC TASK:**

After all assertions in Step 3.2 pass, execute the following SQL to atomically swap the new data into production via a view. Replace `[VERSION]` with the actual version string.

```sql
-- Step 3.3: Promote New Data Build (Atomic View Update)
CREATE OR REPLACE VIEW `savvy-gtm-analytics.LeadScoring.v_latest_training_dataset_v6` AS
SELECT * FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_[VERSION]`;
```

**Validation Checklist:**
- [ ] View `v_latest_training_dataset_v6` created/updated
- [ ] View returns expected row count (should match: 41,942)
- [x] All assertions from Step 3.2 have passed ✅

**Current Status:** Step 3.2 complete - Ready to execute Step 3.3 to promote dataset to production view.

**✅ Gate:** Proceed to Phase 2 only when this view is updated and all Step 3.2 assertions passed.

---

## 🤖 **Phase 2: Model Development (Train & Validate)**

### **Step 4.1 (Agent Task - Python): Train V6 Model**

**Note:** The SQL in Step 3.3 has already selected only Keep features and built Engineered features. This training step is streamlined: load, encode, train, validate, and save artifacts.

**Input Artifacts:**
- `LeadScoring.v_latest_training_dataset_v6` (stable view from Step 3.3)
- `config/v1_model_config.json`

**Output Artifacts:**
- `unit_4_train_model_v6.py`
- `model_v6_[YYYYMMDD].pkl` (Versioned model)
- `model_training_report_v6_[YYYYMMDD].md`
- `feature_importance_v6_[YYYYMMDD].csv`
- `feature_order_v6_[YYYYMMDD].json`

**AGENTIC TASK:**
1) Create `unit_4_train_model_v6.py` that:
   - Loads data from the stable view: `LeadScoring.v_latest_training_dataset_v6` (drop IDs, keep `target_label`).
   - **Critical:** Load and enforce PII drop list from `config/v6_pii_droplist.json` (created in Step 4.2). Assert these features are dropped before training.
   - Applies only minimal preprocessing (encode categoricals, handle booleans).
   - Uses regularized XGBoost with V5-style defaults: `max_depth=4`, `reg_alpha=1.0`, `reg_lambda=5.0`, `learning_rate=0.02`, `subsample=0.7`, `colsample_bytree=0.7`.
   - Cross-validation: `BlockedTimeSeriesSplit` (fallback to `StratifiedKFold` if needed) using contact date ordering.
   - Generates version string `YYYYMMDD` (e.g., `20241215`) and uses it for all output artifacts.
   - Saves all artifacts listed above with versioning.

2) Run the script:
```bash
python unit_4_train_model_v6.py
```

3) Produce `model_training_report_v6_[YYYYMMDD].md` with CV metrics and holdout performance. Save feature importances and the final feature order.

**✅ VALIDATION GATE:** Proceed to Step 4.2 only if ALL pass:
1. Average CV AUC-PR > 0.15
2. Train-Test Gap < 15%
3. CV Coefficient < 20%

---

### **Step 4.2 (Governance): Define PII & Feature Policy**

**Objective:** This model version (V6) is based on the V4/V5 lessons. It explicitly removes all PII to prevent spurious correlations and protect data.

**AGENTIC TASK:**

You are a data governance agent. Your task is to create the PII drop list configuration file.

1. **Create `config/v6_pii_droplist.json`:**
   - Based on `Lead_Scoring_Development_Progress.md` (Unit 6, V4 model lessons), this list must include:
     - **PII Fields:**
       - `FirstName`
       - `LastName`
       - `Branch_City`
       - `Branch_County`
       - `Branch_ZipCode`
       - `Home_City`
       - `Home_County`
       - `Home_ZipCode` (Note: We keep `Home_Zip_3Digit` engineered feature, but drop raw ZIP)
       - `RIAFirmName`
       - `PersonalWebpage`
       - `Notes`
     - **Identifiers (not features, but keep for linking):**
       - `RepCRD` (Keep for joining, but drop as feature - it's an identifier, not a predictor)
       - `RIAFirmCRD` (Keep for joining, but drop as feature - it's an identifier, not a predictor)
       - `Id` (from Lead table - keep for joining, but drop as feature)
     - **Redundant String Fields (replaced by boolean flags):**
       - `Licenses` (Redundant with `Has_Series_7`, `Has_Series_65`, etc. boolean flags)
       - `RegulatoryDisclosures` (Redundant with `Has_Disclosure` boolean flag)
       - `BreakawayRep` (Replaced by `Is_BreakawayRep` boolean flag)
       - `SocialMedia_LinkedIn` (Keep URL for reference, but we have `Has_LinkedIn` boolean flag)
     - **High Cardinality / Low Signal Fields (consider dropping):**
       - `Title` (High cardinality, may not be predictive - consider creating boolean flags for common titles)
       - `Education1` (High cardinality, may not be predictive - consider creating boolean flags for common degrees)
       - `Gender` (Low cardinality, may not be predictive, raises ethical concerns - consider dropping)
   - Format as JSON array of strings: `["FirstName", "LastName", ...]`

2. **Modify Step 4.1 Python script:**
   - Add assertion to load `config/v6_pii_droplist.json`
   - Ensure these features are dropped before training (if they exist in the dataset)
   - Log which PII features were found and dropped

**Validation Checklist:**
- [ ] `config/v6_pii_droplist.json` created with all required PII fields
- [ ] Step 4.1 script includes PII drop assertion
- [ ] PII features are logged when dropped

**✅ Gate:** Proceed to Step 4.3 only when PII policy is defined and enforced.

---

### **Step 4.3 (Agent Task - Python): Model Calibration (Unit 5)**

**Objective:** Calibrate the trained model to ensure probability estimates are well-calibrated across segments.

**Input Artifacts:**
- `model_v6_[YYYYMMDD].pkl` (from Step 4.1)
- `feature_order_v6_[YYYYMMDD].json` (from Step 4.1)
- `LeadScoring.v_latest_training_dataset_v6`

**Output Artifacts:**
- `unit_5_calibration_v6.py`
- `model_v6_calibrated_[YYYYMMDD].pkl`
- `calibration_report_v6_[YYYYMMDD].md`
- `shap_feature_comparison_report_v6_[YYYYMMDD].md`

**AGENTIC TASK:**

You are a model calibration agent. Port the calibration logic from `Lead_Scoring_Development_Progress.md` (Unit 5).

1. **Create `unit_5_calibration_v6.py`:**
   - Load the trained model from Step 4.1
   - Load the training data from `LeadScoring.v_latest_training_dataset_v6`
   - Apply PII drop list (same as Step 4.1)
   - Create segment-specific calibrators (e.g., by AUM tier)
   - Use `CalibratedClassifierCV` with `method='sigmoid'` (Platt scaling)
   - Calculate Expected Calibration Error (ECE) overall and per segment
   - Generate SHAP feature importance comparison (base vs calibrated)
   - Save calibrated model with versioning

2. **Run the script:**
```bash
python unit_5_calibration_v6.py
```

3. **Generate `calibration_report_v6_[YYYYMMDD].md`:**
   - Overall ECE
   - ECE by AUM tier segment
   - Calibration curves (before/after)
   - Feature importance comparison

**✅ VALIDATION GATE:** Proceed to Step 4.4 only if:
- Expected Calibration Error (ECE) <= 0.05 overall
- ECE <= 0.05 for each AUM tier segment
- `calibration_report_v6_[YYYYMMDD].md` is complete

If ECE > 0.05, **STOP** and tag @HumanDeveloper for review.

---

### **Step 4.4 (Agent Task - Python): Model Backtesting (Unit 6)**

**Objective:** Validate train-test gap and CV consistency to ensure no overfitting.

**Input Artifacts:**
- `model_v6_calibrated_[YYYYMMDD].pkl` (from Step 4.3)
- `feature_order_v6_[YYYYMMDD].json` (from Step 4.1)
- `LeadScoring.v_latest_training_dataset_v6`

**Output Artifacts:**
- `unit_6_backtesting_v6.py`
- `backtesting_report_v6_[YYYYMMDD].md`
- `performance_validation_report_v6_[YYYYMMDD].md`
- `overfitting_analysis_v6_[YYYYMMDD].md`

**AGENTIC TASK:**

You are a model validation agent. Port the backtesting logic from `Lead_Scoring_Development_Progress.md` (Unit 6).

1. **Create `unit_6_backtesting_v6.py`:**
   - Load the calibrated model from Step 4.3
   - Perform temporal backtesting (split by time periods)
   - Calculate train-test gap across temporal folds
   - Calculate CV coefficient of variation
   - Generate overfitting analysis (feature importance stability, performance drift)
   - Validate business impact metrics (MQLs per 100 dials)

2. **Run the script:**
```bash
python unit_6_backtesting_v6.py
```

3. **Generate reports:**
   - `backtesting_report_v6_[YYYYMMDD].md`: Temporal performance stability
   - `performance_validation_report_v6_[YYYYMMDD].md`: Comprehensive validation metrics
   - `overfitting_analysis_v6_[YYYYMMDD].md`: Train vs test gap analysis

**✅ VALIDATION GATE:** Proceed to Phase 3 only if:
- Train-Test Gap < 15% (re-confirmed)
- CV Coefficient < 20% (re-confirmed)
- No significant overfitting indicators
- Feature importance is stable

If validation fails, **STOP** and tag @HumanDeveloper for model review.

---

## 🚀 **Phase 3: Production Deployment (Test & Rollout)**

### **Step 5.1 (Agent Task): Shadow Scoring (Unit 7)**

**Objective:** Deploy the calibrated model in shadow mode to validate production readiness without impacting live operations.

**Input Artifacts:**
- `model_v6_calibrated_[YYYYMMDD].pkl` (from Step 4.3)
- `feature_order_v6_[YYYYMMDD].json` (from Step 4.1)
- `config/v6_pii_droplist.json` (from Step 4.2)

**Output Artifacts:**
- `unit_7_shadow_scoring_v6.py`
- `shadow_scoring_report_v6_[YYYYMMDD].md`
- `shadow_scoring_metrics_v6_[YYYYMMDD].csv`

**AGENTIC TASK:**

You are a production deployment agent. Port the shadow scoring logic from `Lead_Scoring_Development_Progress.md` (Unit 7).

1. **Create `unit_7_shadow_scoring_v6.py`:**
   - Deploy model in shadow mode (scores are generated but not used for routing decisions)
   - Score all new leads entering the system
   - Track scoring success rate, latency, and error rates
   - Compare shadow scores to current production model scores (if available)
   - Log all scores and metrics for analysis

2. **Run shadow scoring for 7 days:**
   - Monitor daily: scoring success rate, average latency, error rate
   - Track feature availability and data quality
   - Compare shadow model performance to baseline

3. **Generate `shadow_scoring_report_v6_[YYYYMMDD].md`:**
   - 7-day success rate summary
   - Latency analysis
   - Error analysis
   - Feature availability summary
   - Comparison to baseline model (if available)

**✅ VALIDATION GATE:** Proceed to Step 5.2 only if:
- Shadow mode runs for 7 days with > 95% success rate
- Average latency < 500ms per lead
- Error rate < 1%
- No critical feature availability issues

If shadow scoring fails, **STOP** and tag @HumanDeveloper for review.

---

### **Step 5.2 (Agent Task): A/B Test Power Analysis (Unit 8.5)**

**Objective:** Design a statistically valid A/B test to measure the impact of the new model.

**Input Artifacts:**
- `step_3_3_class_imbalance_analysis_v6_[VERSION].md` (for baseline conversion rate)
- `config/v1_model_config.json`
- `business_impact_metrics_v6_[YYYYMMDD].csv` (from Step 4.4, if available)

**Output Artifacts:**
- `unit_8_5_ab_power_analysis_v6.py`
- `ab_test_power_analysis_v6.md`
- `sga_adoption_tracking_plan_v6.md`

**AGENTIC TASK:**

You are an experimentation analyst. Port the power analysis logic from `Lead_Scoring_Development_Progress.md` (Unit 8.5).

1. **Create `unit_8_5_ab_power_analysis_v6.py`:**
   - Calculate required sample size to detect a 50% lift in MQLs per 100 dials
   - Use baseline conversion rate from imbalance analysis (typically ~3-4%)
   - Statistical parameters: `alpha=0.05`, `power=0.8`
   - Calculate experiment duration based on weekly lead flow
   - Validate that 4-week test is sufficient (or flag for extension)

2. **Run the script:**
```bash
python unit_8_5_ab_power_analysis_v6.py
```

3. **Generate `ab_test_power_analysis_v6.md`:**
   - Required sample size (N)
   - Expected experiment duration
   - Minimum detectable effect size
   - Statistical power analysis

4. **Create `sga_adoption_tracking_plan_v6.md`:**
   - Plan to instrument SGA adoption tracking
   - Define adoption metrics
   - Define tracking instrumentation requirements

**✅ VALIDATION GATE:** Proceed to Step 5.3 only if:
- Power >= 0.8 to detect a 50% lift
- Experiment duration is feasible (≤ 8 weeks)
- Sample size requirements are achievable

If power < 0.8, **STOP** and tag @HumanDeveloper to adjust experiment design.

---

### **Step 5.3 (Agent Task): Execute A/B Test (Units 9-12)**

**Objective:** Implement and monitor the A/B test to validate model impact.

**Input Artifacts:**
- `model_v6_calibrated_[YYYYMMDD].pkl` (from Step 4.3)
- `ab_test_power_analysis_v6.md` (from Step 5.2)
- `sga_adoption_tracking_plan_v6.md` (from Step 5.2)

**Output Artifacts:**
- `unit_9_12_ab_test_execution_v6.py`
- `ab_test_assignments_v6.csv`
- `ab_test_daily_metrics_v6.csv`
- `ab_test_interim_analysis_unit10_v6.md`
- `ab_test_final_analysis_v6.md`

**AGENTIC TASK:**

You are an experimentation agent. Port the A/B test execution logic from `Lead_Scoring_Development_Progress.md` (Units 9-12).

1. **Create `unit_9_12_ab_test_execution_v6.py`:**
   - Implement lead-level randomization with blocking by AUM tier
   - Ensure balanced assignment within each block
   - Verify balanced discovery data coverage (treatment vs control)
   - Monitor primary KPI daily: MQLs per 100 dials within 30 days
   - Track conversion rates and lift metrics daily
   - Implement interim analysis at week 10
   - Perform final statistical significance testing

2. **Run the A/B test:**
   - Execute for planned duration (typically 4-8 weeks)
   - Monitor daily metrics
   - Perform interim analysis at week 10
   - Generate final analysis at experiment end

3. **Generate reports:**
   - `ab_test_daily_metrics_v6.csv`: Daily tracking of conversion rates and lift
   - `ab_test_interim_analysis_unit10_v6.md`: Week 10 interim analysis with safety checks
   - `ab_test_final_analysis_v6.md`: Final statistical validation

**✅ VALIDATION GATE (Final Go/No-Go):** Proceed to Phase 4 only if:
- Final analysis shows statistically significant lift (p-value < 0.05) in MQLs per 100 dials
- Treatment group shows > 50% lift vs control
- No safety issues or adverse effects detected
- `ab_test_final_analysis_v6.md` contains complete statistical validation

If statistical significance is not achieved or lift is < 50%, **STOP** and tag @HumanDeveloper for review and model iteration.

---

## 🔄 **Phase 4: Maintenance & Monitoring (Ongoing)**

### **Step 6.1 (Agent Task): Full Production Rollout & Monitoring (Unit 13+)**

**Objective:** Deploy the validated model to full production with continuous monitoring and health checks.

**Input Artifacts:**
- `model_v6_calibrated_[YYYYMMDD].pkl` (validated from Phase 3)
- `ab_test_final_analysis_v6.md` (successful A/B test results)
- `feature_order_v6_[YYYYMMDD].json` (from Step 4.1)

**Output Artifacts:**
- `unit_13_production_rollout_v6.py`
- `production_health_dashboard_v6.json`
- `monitoring_schedule_v6.yaml`
- `alerting_config_v6.json`
- `production_runbook_v6.md`

**AGENTIC TASK:**

You are a production operations agent. Port the production rollout logic from `Lead_Scoring_Development_Progress.md` (Unit 13+).

1. **Create `unit_13_production_rollout_v6.py`:**
   - Deploy model to production scoring pipeline
   - Implement daily production health checks:
     - Scoring success rate (target: > 99%)
     - Average latency tracking (target: < 500ms)
     - Error rate monitoring (target: < 0.5%)
     - Feature availability checks
   - Implement weekly class imbalance monitoring:
     - Track positive class rate
     - Compare to training distribution
     - Alert if drift > 5%
   - Implement monthly feature drift detection:
     - Calculate Population Stability Index (PSI) for all features
     - Identify features with PSI > 0.25 (significant drift)
     - Generate monthly drift reports
   - Set up automated alerting:
     - Performance degradation alerts
     - Scoring failure alerts
     - Feature drift alerts
     - Model performance drop alerts

2. **Create monitoring configuration:**
   - `production_health_dashboard_v6.json`: Dashboard configuration
   - `monitoring_schedule_v6.yaml`: Automated monitoring schedule
   - `alerting_config_v6.json`: Alert thresholds and recipients

3. **Create `production_runbook_v6.md`:**
   - Operational procedures for ongoing maintenance
   - Troubleshooting guides
   - Escalation procedures
   - Monthly/quarterly maintenance tasks

**✅ VALIDATION GATE:** Production is healthy when:
- Daily health checks pass (> 99% success rate)
- Weekly class imbalance is stable (drift < 5%)
- Monthly feature drift is acceptable (PSI < 0.25 for all features)
- No critical alerts triggered

---

### **Step 6.2 (Agentic Loop): Quarterly Data Refresh (Maintenance Loop)**

**Objective:** This plan is a living document. This step describes the agentic process for quarterly model refreshes.

**AGENTIC TASK:**

On receipt of new quarterly snapshot files (e.g., Q1 2025), restart this plan from Step 1.1 with the following modifications:

1. **Data Ingestion (Steps 1.1-1.7):**
   - New snapshot files will be transformed (Step 1.5) and validated against `config/v6_feature_contract.json` (Step 1.7)
   - All 8 rep tables + 8 firm tables (now 9 rep + 9 firm with new quarter) must pass schema validation

2. **Master Views Update (Step 2):**
   - Update `v_discovery_reps_all_vintages` to include new quarter's data
   - Update `v_discovery_firms_all_vintages` to include new quarter's data
   - Add new snapshot's DATE for `snapshot_at` (e.g., `DATE('2025-01-15')` from the new CSV filename)

3. **New Training Dataset (Steps 3.1-3.3):**
   - Build new versioned training dataset with expanded historical data
   - All assertions must pass (Step 3.2)
   - Promote new dataset via view update (Step 3.3)

4. **New Model Training (Phase 2):**
   - Train new model version: `model_v6_[YYYYMMDD].pkl`
   - Calibrate and validate new model (Steps 4.1-4.4)
   - All validation gates must pass

5. **Shadow Comparison (Step 5.1):**
   - Shadow score new model against current production champion
   - Compare performance metrics (AUC-PR, ECE, business impact)

6. **Promotion Decision:**
   - **Gate:** New model is promoted to production champion only if:
     - AUC-PR is superior to current champion
     - ECE <= 0.05 (equal or better calibration)
     - Train-test gap < 15% (maintained)
     - CV coefficient < 20% (maintained)
     - Shadow scoring shows no degradation
   - If new model is superior, update production to use new model version
   - If new model is not superior, keep current champion and document why

7. **Documentation:**
   - Update `production_runbook_v6.md` with new model version
   - Archive old model version
   - Document performance comparison

**✅ VALIDATION GATE:** Quarterly refresh is complete when:
- New model is trained and validated
- Shadow comparison is performed
- Promotion decision is documented
- Production model is updated (if new model is superior) or kept (if not)

---

## 📊 **Expected Outcomes**

### **Success Criteria:**

1. **Dataset:**
   - ~40,000+ training samples
   - Full feature richness (no excessive NULLs)
   - Temporally correct (no data leakage)

2. **Model Performance:**
   - CV AUC-PR > 15% (beats m5)
   - Train-Test Gap < 15%
   - CV Coefficient < 20%

3. **Model Trust:**
   - Top features are business signals (not PII)
   - Feature importance aligns with business logic
   - No overfitting indicators

### **Artifacts Generated:**

- ✅ `LeadScoring.step_3_3_training_dataset_v6` (BigQuery table)
- ✅ `step_3_3_class_imbalance_analysis_v6.md`
- ✅ `unit_4_train_model_v6.py`
- ✅ `model_v6.pkl`
- ✅ `model_v6_baseline_logit.pkl`
- ✅ `model_training_report_v6.md`
- ✅ `feature_importance_v6.csv`
- ✅ `feature_order_v6.json`
- ✅ `cv_fold_indices_v6.json`
- ✅ `feature_selection_report_v6.md`
- ✅ `selected_features_v6.json`

---

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **View creation fails:**
   - Check table names match exactly
   - Verify `snapshot_quarter` DATE format is correct
   - Ensure all UNION ALL statements have matching column counts

2. **Point-in-time join returns no matches:**
   - Verify `contact_quarter` calculation uses `DATE_TRUNC(..., QUARTER)`
   - Check that `snapshot_quarter` dates align with quarter boundaries
   - Verify CRD matching (RepCRD = FA_CRD__c)

3. **Training script fails:**
   - Check BigQuery table name is correct
   - Verify Python environment has all dependencies
   - Check for missing features (should match V4 feature set)

4. **Low AUC-PR (< 15%):**
   - Review feature engineering logic
   - Check for data quality issues
   - Verify point-in-time join is working correctly

---

**Document Version:** 2.0  
**Last Updated:** December 2025  
**Status:** Complete master production plan - Ready for agentic execution

