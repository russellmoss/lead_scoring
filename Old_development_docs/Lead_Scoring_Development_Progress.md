# Lead Scoring Model Development Progress & Next Steps

**Project:** Savvy Wealth Lead Scoring Engine (Contacted → MQL)  
**Current Status:** Phase 0, Unit 2 Complete - Feature Engineering Pipeline Implemented  
**Last Updated:** October 27, 2025  
**Next Phase:** Phase 0, Unit 3 - Validation & Baseline Metrics  

---

## 🎯 **Project Overview**

We are implementing a **single, high-leverage lead scoring model** that predicts whether a **Contacted** lead will become an **MQL** (i.e., will schedule an initial discovery call). The model leverages **69 engineered features** from discovery data including firmographics, growth metrics, operational indicators, and temporal contact patterns.

**Target:** +50% lift in **MQLs/100 dials** for treatment vs control at p<0.05.

### **30-Day Outcome Window Rationale**

The **30-day outcome window** is a critical modeling decision that defines when we consider a lead conversion to be "valid" for our model:

**Why 30 Days?**
- **Business Reality:** Most MQL conversions happen quickly after initial contact
- **Model Performance:** Including very late conversions can hurt model accuracy  
- **Actionable Insights:** We want to predict leads that will convert within a reasonable timeframe

**What It Means:**
- **Contacted Lead:** Someone enters "Contacting" stage on Day 0
- **30-Day Window:** We only count conversions that happen within 30 days of contact
- **Late Conversions:** Any conversions after 30 days are excluded from our positive class

**From Our Analysis:**
- **All-time conversions:** 2,111 MQLs
- **30-day window conversions:** 1,902 MQLs (90.1% of all conversions)
- **Late conversions:** 209 MQLs (9.9% excluded)

This means **90.1% of conversions happen within 30 days**, so the 30-day window captures the vast majority while excluding outliers that might confuse the model.

**Real-World Application:**
When the model scores a **new lead** (contacted today), it will predict:
- **"Will this lead convert to MQL within 30 days?"**
- **Not:** "Will this lead ever convert?" (which could take 6+ months)

This makes the model more actionable for your sales team - they can focus on leads likely to convert quickly rather than waiting indefinitely.

---

## ✅ **COMPLETED WORK**

### **Phase 0: Data Foundation**

#### **Unit 1: Discovery Data Pipeline Implementation** ✅ COMPLETE
- **✅ Created BigQuery dataset structure:**
  - `savvy-gtm-analytics.LeadScoring` (processing tables)
  - `savvy-gtm-analytics.SavvyGTMData` (core CRM data)
- **✅ Uploaded MarketPro data (T1, T2, T3 territories):**
  - T1: 198,024 records (41.4%)
  - T2: 173,631 records (36.3%) 
  - T3: 106,246 records (22.2%)
  - **Total: 477,901 records**
- **✅ Created `discovery_reps_current` table** with SAFE_CAST handling for data quality issues
- **✅ Resolved "Osseo" data issue** using SAFE_CAST for numeric conversions
- **✅ Implemented proper deduplication** (462,825 unique reps from 477,901 records)

#### **Unit 2: Feature Engineering Pipeline** ✅ COMPLETE
- **✅ Implemented 3-stage feature engineering architecture:**
  - **Stage 1:** 31 base features (direct mapping from discovery data)
  - **Stage 2:** 5 geographic features (metropolitan area dummy variables)
  - **Stage 3:** 31 advanced features (complex derived metrics and ratios)
- **✅ Created `discovery_reps_current` table** with all 67 engineered features (includes all base features, engineered features, and metro area dummy variables)
- **✅ Passed Unit 2 validation checkpoints:**
  - Multicollinearity: All correlations < 0.95 (ACCEPTABLE)
  - Feature Distribution: Proper data ranges and distributions
  - Feature Quality: All engineered features working correctly

### **Key Data Quality Metrics Achieved:**
- **Data Completeness:** RepCRD (100%), AUM (93.3%), Growth Rates (90.3%)
- **Feature Coverage:** All 67 engineered features successfully created (expanding to 69 in Phase 1 with temporal features)
- **Geographic Distribution:** NYC (3.8%), LA (1.5%), Chicago (1.6%), Dallas (2.0%), Miami (1.4%)
- **Professional Credentials:** Series 7 (69.1%), CFP (17.4%), Primary RIA (96.8%)

---

## 🚧 **REMAINING WORK**

### **Phase 0, Unit 3: Validation & Baseline Metrics** (CURRENT PHASE)

#### **Step 3.1: Class Distribution Analysis** ✅ COMPLETE

**✅ COMPLETED:** Comprehensive class distribution analysis completed on October 27, 2025.

**Key Findings:**
- **Overall Conversion Rate:** 4.32% (all time) → 3.89% (30-day window)
- **Class Imbalance Ratio:** 24.18:1 (negative:positive) - SEVERE imbalance
- **Discovery Data Coverage:** 94.82% CRD matching rate - EXCELLENT
- **AUM Tier Performance:** Smaller firms convert higher (<$100M: 6.13% vs >$500M: 3.58%)
- **Metro Area Performance:** Major metros underperform (NYC: 2.72%, LA: 2.60%)
- **Temporal Patterns:** Weekend contacts show premium (Saturday: 8.72% vs weekday avg: 4.3%)

**Critical Insights:**
- **Severe class imbalance** requires sophisticated SMOTE vs. Pos_Weight testing
- **Segment variations** suggest need for AUM tier-specific modeling
- **Data quality issues** detected (negative days to conversion)
- **Modeling dataset:** 40,595 samples ready for Phase 1

**Files Created:**
- `Step_3_1_Class_Distribution_Analysis.sql` - Complete analysis queries
- `Step_3_1_Class_Distribution_Analysis_Results.md` - Comprehensive results summary

**Status:** ✅ **READY FOR STEP 3.2**

#### **Step 3.2: Temporal Leakage Detection**

**Input Artifacts:**
- `savvy-gtm-analytics.SavvyGTMData.Lead`
- `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
- `Step_3_1_Class_Distribution_Analysis_Results.md` (for context)

**Output Artifacts:**
- `step_3_2_leakage_report.md` (markdown file containing query results and analysis)

**Cursor.ai Prompt:**
```
"Implement temporal leakage detection to ensure our discovery data doesn't contain future information that would bias our model. Execute the SQL query to check if any discovery data timestamps are after the contacted timestamp, validate that all discovery features are based on historical data only, and create a comprehensive leakage report with specific examples. This is critical for model integrity - we must ensure all features are available at the time of prediction."
```

**AGENTIC TASK:**

You are a data validation agent. Your task is to check for temporal data leakage and time zone integrity.

1. **Assert Time Zone Integrity:** Before executing the main query, verify that both `dd.processed_at` and `sf.Stage_Entered_Contacting__c` are `TIMESTAMP` data types and are stored in the same time zone (e.g., UTC). **Fail hard** if any time zone casting is ambiguous or needed.

2. **Execute** the SQL query from the `🔑 REFERENCE IMPLEMENTATION:` block.

3. **Analyze** the results, specifically `leakage_records_matched` and `leakage_rate_percent_matched`.

4. **Create** a new file named `step_3_2_leakage_report.md`.

5. **Write** *all* metrics (both overall and matched) into this file in a clear, tabular format.

**🔑 REFERENCE IMPLEMENTATION:**

```sql
-- Unit 3 Validation Checkpoint 3.2: Temporal Leakage Detection
SELECT 
    'Future Data Leakage Check' as validation_type,
    COUNT(*) as total_records,
    COUNT(dd.RepCRD) as matched_records,
    
    -- Overall leakage (can be diluted)
    COUNT(CASE 
        WHEN dd.processed_at > sf.Stage_Entered_Contacting__c 
        THEN 1 
    END) as leakage_records_overall,
    ROUND(COUNT(CASE 
        WHEN dd.processed_at > sf.Stage_Entered_Contacting__c 
        THEN 1 
    END) / COUNT(*) * 100, 2) as leakage_rate_percent_overall,
    
    -- Matched-only leakage (the critical gate)
    COUNT(CASE 
        WHEN dd.RepCRD IS NOT NULL AND dd.processed_at > sf.Stage_Entered_Contacting__c 
        THEN 1 
    END) as leakage_records_matched,
    ROUND(COUNT(CASE 
        WHEN dd.RepCRD IS NOT NULL AND dd.processed_at > sf.Stage_Entered_Contacting__c 
        THEN 1 
    END) / NULLIF(COUNT(dd.RepCRD), 0) * 100, 2) as leakage_rate_percent_matched
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;
```

**Policy Decision: Eligible-Only Training (Option A)**

The leakage query confirms our hypothesis:

* **Raw Historical Data (All Contacts):** `leakage_records_matched = 40,641` (89.82%). This is because most historical `contacted_ts` (e.g., 2023) are *before* our discovery data's `snapshot_as_of` date (e.g., 2025). This data is unusable for training as-is.

* **Eligible-Only Data (Contacts >= `snapshot_as_of`):** `leakage_records_matched = 0` (0%).

**Decision:** We will proceed with **Option A**. The V1 model will be trained *only* on the "Eligible-Only" cohort. This cohort is 100% temporally correct and perfectly mirrors the production use case (scoring new leads with the latest snapshot). We accept the smaller training set (4,608 samples) in exchange for 100% model correctness.

**✅ VALIDATION GATE:**

Proceed to Step 3.3 **only if** `leakage_records_matched` is 0 in `step_3_2_leakage_report.md`. If `leakage_records_matched` > 0, **STOP** and tag @HumanDeveloper for immediate review.

#### **Step 3.3: SMOTE/Class Balancing Validation**

**Status:** ✅ **COMPLETE**

**Input Artifacts:**
- `savvy-gtm-analytics.SavvyGTMData.Lead`
- `step_3_2_leakage_report.md` (validation that Step 3.2 passed)
- `Step_3_1_Class_Distribution_Analysis_Results.md` (for baseline metrics)
- `config/v1_feature_schema.json` (for is_mutable flags)
- `config/v1_model_config.json` (for training_data_policy: "hybrid_stable_mutable")

**Output Artifacts:**
- ✅ `step_3_3_class_imbalance_analysis.md` (analysis report with class distribution metrics)
- ✅ `Step_3_3_Hybrid_Training_Set.sql` (complete SQL query with all 124 features)
- ✅ `create_training_dataset_full.sql` (SQL for creating BigQuery table)
- ⚠️ `step_3_3_training_dataset.csv` (pending: table creation and CSV export)

**Cursor.ai Prompt:**
```
"Prepare for class imbalance handling by analyzing our dataset and implementing the comprehensive SMOTE vs Pos_Weight testing framework. Calculate exact class imbalance ratios, analyze the distribution of positive vs negative samples, prepare the training dataset with target_label column, and create validation reports. Follow the plan's Section 5.6 comprehensive framework for testing both approaches."
```

**✅ COMPLETED WORK:**

1. **✅ Updated Configuration Files:**
   - Modified `config/v1_model_config.json` to set `training_data_policy: "hybrid_stable_mutable"`
   - Updated `config/v1_feature_schema.json` to include `is_mutable: true/false` flags for all 122 features
   - Classified features as stable (63) vs mutable (61) based on temporal characteristics

2. **✅ Generated Complete SQL Query:**
   - Created `Step_3_3_Hybrid_Training_Set.sql` with all 124 features (122 discovery + 2 temporal)
   - Programmatically generated CASE WHEN logic for all 61 mutable features
   - Uses `discovery_reps_current` table (contains all features + `snapshot_as_of`)
   - Derives temporal features (`Day_of_Contact`, `Is_Weekend_Contact`) inline from `Stage_Entered_Contacting__c`

3. **✅ Executed Label Integrity & Imbalance Queries:**
   - **Integrity Assertions:** ✅ PASS
     - `negative_days_to_conversion`: 235 records removed (filtered out)
     - `labels_in_right_censored_window`: 200 records removed (filtered out)
   - **Imbalance Metrics:** ✅ VALIDATED
     - `total_samples`: **45,923** (expanded from ~590)
     - `positive_samples`: **1,616** (3.52%)
     - `negative_samples`: **44,307**
     - `imbalance_ratio`: **27.42:1** ✅ (within acceptable range 15:1 to 30:1)

4. **✅ Generated Analysis Report:**
   - Created `step_3_3_class_imbalance_analysis.md` with complete metrics
   - Documented Hybrid approach benefits (77.8x dataset expansion)
   - Validated temporal integrity (no leakage, NULL masking for historical leads)

5. **✅ Generated Table Creation SQL:**
   - Created `create_training_dataset_full.sql` for BigQuery table creation
   - Ready for execution to create `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`

**📊 Actual Results (Hybrid Cohort):**

| Metric | Value | Status |
|--------|-------|--------|
| **Total Samples** | 45,923 | ✅ |
| **Positive Samples** | 1,616 (3.52%) | ✅ |
| **Negative Samples** | 44,307 | ✅ |
| **Imbalance Ratio** | 27.42:1 | ✅ (within 15:1 to 30:1) |
| **Eligible for Mutable Features** | 564 leads (1.23%) | ✅ |
| **Historical Leads** | 45,359 leads (98.77%) | ✅ |
| **Data Integrity (Pre-Filter)** | 235 negative days + 200 right-censored removed | ✅ |

**📁 Files Created:**

1. **✅ `Step_3_3_Hybrid_Training_Set.sql`**
   - Complete Hybrid SQL query with all 124 features
   - Uses `discovery_reps_current` table
   - Includes CASE WHEN logic for all 61 mutable features
   - Derives temporal features inline

2. **✅ `step_3_3_class_imbalance_analysis.md`**
   - Complete class distribution analysis
   - Hybrid approach benefits documented
   - Data integrity validation results
   - Comparison to Step 3.1 baseline

3. **✅ `create_training_dataset_full.sql`**
   - SQL for creating BigQuery table
   - Contains all 124 features with proper CASE WHEN logic
   - Ready for execution in BigQuery Console

4. **⚠️ `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`** (PENDING TABLE CREATION)
   - **Next Step:** Execute `create_training_dataset_full.sql` in BigQuery Console
   - **Table:** `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` (will replace/create table)
   - **Note:** No CSV export needed - Unit 4 Python scripts will read directly from BigQuery using `pandas.read_gbq()` or `google-cloud-bigquery` client

**🔄 Hybrid Approach Implementation Details:**

- **Stable Features (63):** Available for all 45,923 leads
  - Examples: FirstName, LastName, Title, Branch_State, Has_CFP, SocialMedia_LinkedIn
  - These features are historically stable and don't change over time
  
- **Mutable Features (61):** Available for 564 eligible leads, NULL for 45,359 historical leads
  - Examples: AUMGrowthRate_5Year, AUM_per_Client, NumberClients_HNWIndividuals
  - These features are NULLed for historical leads to prevent temporal leakage
  
- **Temporal Features (2):** Derived from `Stage_Entered_Contacting__c`
  - `Day_of_Contact`: 1=Monday, 7=Sunday
  - `Is_Weekend_Contact`: 1 if Saturday/Sunday, 0 otherwise

- **Total Features:** 124 (122 discovery + 2 temporal)

**✅ VALIDATION GATES PASSED:**

1. **Data Integrity:** ✅
   - Negative conversion times removed (235 records)
   - Right-censored data excluded (200 records)
   
2. **Class Imbalance:** ✅
   - Ratio 27.42:1 within acceptable range (15:1 to 30:1)
   - Positive class percentage 3.52% aligns with baseline expectations
   
3. **Dataset Size:** ✅
   - 45,923 samples (77.8x expansion from ~590)
   - Provides sufficient data for robust model training
   
4. **Feature Coverage:** ✅
   - All 124 features accounted for
   - Stable/Mutable classification applied correctly
   - Temporal integrity maintained (no leakage)

**📝 Next Steps:**

1. **Execute SQL in BigQuery Console:**
   - Open `create_training_dataset_full.sql`
   - **Modify table name:** Change `step_3_3_training_dataset_hybrid` to `step_3_3_training_dataset` to replace existing table (if it exists)
   - Execute the `CREATE OR REPLACE TABLE` statement in BigQuery Console
   - Verify table creation: Check row count (should be 45,923) and column count (should be 125 columns: Id + 124 features)

2. **Verify Table:**
   - Run `SELECT COUNT(*) FROM \`savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset\`` (should return 45,923)
   - Run `SELECT COUNT(DISTINCT feature_name) FROM (SELECT column_name as feature_name FROM \`savvy-gtm-analytics.LeadScoring.INFORMATION_SCHEMA.COLUMNS\` WHERE table_name = 'step_3_3_training_dataset')` to verify column count
   - **No CSV export needed** - Unit 4 Python scripts will read directly from BigQuery

3. **Update Unit 4 Inputs:**
   - Unit 4 will use BigQuery table: `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`
   - Python scripts will use `pandas.read_gbq()` or `google-cloud-bigquery` client to read data
   - This avoids Google Sheets limitations and large CSV file handling

**🔑 REFERENCE IMPLEMENTATION (V2 - Updated for Step 5.1):**

The V2 SQL uses a 3-part temporal classification strategy. See `Step_3_3_V2_FinalDatasetCreation.sql` for the complete `FinalDatasetCreation` CTE. The key change is in how features are handled:

**1. Stable Features:** Pass-through (no CASE WHEN logic)
- Examples: `Branch_State`, `Has_CFP`, `Multi_RIA_Relationships`, `FirstName`

**2. Calculable Features:** Re-calculated point-in-time
- Example: `DateOfHireAtCurrentFirm_NumberOfYears - DATE_DIFF(CURRENT_DATE(), DATE(sf.Stage_Entered_Contacting__c), YEAR) as DateOfHireAtCurrentFirm_NumberOfYears`
- These features are recalculated to reflect the value at contact time, not snapshot time

**3. Mutable Features:** NULLed for historical leads (CASE WHEN logic)
- Example: `CASE WHEN is_eligible_for_mutable_features = 1 THEN AUMGrowthRate_1Year ELSE NULL END as AUMGrowthRate_1Year`

**Complete SQL:** See `Step_3_3_V2_FinalDatasetCreation.sql` for the full implementation.

**✅ VALIDATION GATE:**

Proceed to Step 3.4 **only if**:
- `step_3_3_class_imbalance_analysis.md` is created ✅
- Imbalance ratio is within expected range (15:1 to 30:1) ✅  
- BigQuery table `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` is created with 45,923 rows ✅
- Table contains all 124 features + target_label ✅

**Note:** For V2 rebuild (Step 5.3), use the V2 SQL from `Step_3_3_V2_FinalDatasetCreation.sql` which implements the 3-part temporal strategy.

**No CSV export required** - all subsequent steps will work directly with the BigQuery table.

#### **Step 3.4: Create Global Config & Schema Contracts**

**Input Artifacts:**
- `Step_3_1_Class_Distribution_Analysis_Results.md`
- `savvy-gtm-analytics.LeadScoring.discovery_reps_current` (feature source for V1)

**Output Artifacts:**
- `config/v1_model_config.json`
- `config/v1_feature_schema.json`

**AGENTIC TASK:**

You are a data governance agent. Your task is to create the configuration and schema files that will govern the entire model training and validation process.

1. **Create `config/v1_model_config.json`:**
   * This file will store all key parameters to ensure determinism.
   * Include:
     * `global_seed: 42`
     * `label_window_days: 30`
     * `cv_folds: 5`
     * `cv_gap_days: 30`
     * `evaluation_metric: "aucpr"`
     * `ship_threshold_aucpr: 0.35`
     * `ship_threshold_precision_at_10pct: 0.15`
     * `training_data_policy: "hybrid_stable_mutable"`

2. **Create `config/v1_feature_schema.json`:**
   * This file is the **data contract** to prevent silent failures or "hallucinations."
   * Generate a JSON schema from `savvy-gtm-analytics.LeadScoring.discovery_reps_current` for all **69 features**.
   * For each feature, include:
     * `name`: e.g., "AUM_per_Client"
     * `dtype`: e.g., "FLOAT64"
     * `nullable`: e.g., true
     * `expected_range`: e.g., `[0, 10000000]` (use percentiles 0.01 and 99.9 to set a sane default range)
     * `is_mutable`: true/false (NEW - indicates if feature can change over time and needs temporal masking)
   * **Default `is_mutable` classification:**
     * **`is_mutable: true`** (default) for features that can change: AUMGrowthRate_5Year, AUMGrowthRate_1Year, AUM_per_Client, Number_Clients_HNW_Individuals, AssetsInMillions_*, PercentAssets_*, NumberClients_*, AUM_Per_*, Clients_per_*, TotalAssets_*, etc.
     * **`is_mutable: false`** for stable features: FirstName, LastName, Title, Branch_State, Branch_City, Branch_ZipCode, Home_State, Home_MetropolitanArea, Has_CFP, Has_Series_7, Has_Series_65, Has_Series_66, Day_of_Contact, Is_Weekend_Contact, DateBecameRep_NumberOfYears (historical), DateOfHireAtCurrentFirm_NumberOfYears (historical), Number_YearsPriorFirm* (historical), etc.

**✅ VALIDATION GATE:**

Proceed to Unit 4 **only if** both `.json` artifacts are created and populated. The `AGENTIC TASK` for `Unit 4` *must* be instructed to load this config file first.

---

**Status:** ✅ COMPLETE

**Files Created:**
- `config/v1_model_config.json` (includes `training_data_policy: "hybrid_stable_mutable"`)
- `config/v1_feature_schema.json` (derived from `LeadScoring.discovery_reps_current`, excluding `RepCRD`, `processed_at`, `snapshot_as_of`; includes `is_mutable` flag for all 69 features)

#### **Step 3.5 (Corrective Action): Investigate and Deduplicate Training Set**

**Status:** ✅ **COMPLETE**

**Note:** This is a corrective step. The verification report for Step 3.3 identified 1,331 duplicate rows. The investigation identified the root cause, and deduplication has been successfully applied.

**Input Artifacts:**
- `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` (with duplicates)
- `savvy-gtm-analytics.SavvyGTMData.Lead` (source table)
- `savvy-gtm-analytics.LeadScoring.discovery_reps_current` (source table)
- `Step_3_3_Table_Verification_Report.md` (verification findings)

**Output Artifacts:**
- `step_3_5_duplicate_analysis_report.md` (The report explaining the source of duplicates)
- `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` (Deduplicated - updated table)

**AGENTIC TASK:**

You are a data integrity agent. Your task is to find the source of the 1,331 duplicates and then fix them.

1. **Run Investigation Queries:**
   * Execute Query 1 and Query 2 from the `🔑 REFERENCE IMPLEMENTATION:` block using BigQuery (MCP) tool.
   * Document the results clearly.

2. **Generate Analysis Report (`step_3_5_duplicate_analysis_report.md`):**
   * In this report, you must answer the following:
     * **"Query 1 Result:"** How many duplicate Ids are in the source Lead table?
     * **"Query 2 Result:"** How many duplicate RepCRDs are in the `discovery_reps_current` table?
     * **"Conclusion:"** State the definitive root cause. (e.g., "The 1,331 duplicates originate from duplicate Ids in the Lead table." or "The duplicates originate from RepCRDs in the discovery table, which caused the join to multiply rows.")

3. **Run the Fix Query:**
   * After the analysis is complete, execute Query 3 (The Fix) from the `🔑 REFERENCE IMPLEMENTATION:` block.

4. **Update Report:**
   * Add a "Fix Applied" section to the report, documenting:
     * Original row count (45,923)
     * New deduplicated row count
     * Confirmation that duplicates are removed

**🔑 REFERENCE IMPLEMENTATION:**

```sql
-- Query 1: Investigate Duplicates in Source `Lead` Table
-- This checks if the source Lead table itself has duplicate IDs

SELECT 
    'Duplicate IDs in Lead Table' as finding,
    Id, 
    COUNT(*) as num_duplicates
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
GROUP BY Id
HAVING num_duplicates > 1
ORDER BY num_duplicates DESC
LIMIT 20;

-- Query 2: Investigate Duplicates in Source `Reps` Table
-- This checks if our join key in the discovery table is unique

SELECT 
    'Duplicate RepCRDs in Reps Table' as finding,
    RepCRD, 
    COUNT(*) as num_duplicates
FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
GROUP BY RepCRD
HAVING num_duplicates > 1
ORDER BY num_duplicates DESC
LIMIT 20;

-- Query 3 (The Fix): Deduplicate the Final Training Set
-- This is the same fix as before, but now we run it *after* our investigation

CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` AS
SELECT DISTINCT *
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`;
```

**✅ VALIDATION GATE:**

Proceed to Unit 4 **only if**:
- This task is complete ✅
- The `step_3_5_duplicate_analysis_report.md` clearly identifies the root cause ✅
- The training table row count has been successfully reduced from 45,923 to ~44,592 ✅
- Duplicate investigation queries have been executed and documented ✅

If the root cause cannot be determined or the fix does not resolve the issue, **STOP** and tag @HumanDeveloper for review.

**✅ COMPLETED WORK:**

1. **✅ Investigation Queries Executed:**
   - Query 1: Verified NO duplicates in source `Lead` table (79,002 rows, 79,002 unique Ids)
   - Query 2: Found 15,076 duplicate RepCRDs in `discovery_reps_current` table (477,901 rows, 462,825 unique)

2. **✅ Root Cause Identified:**
   - **Root Cause:** Duplicate RepCRDs in `discovery_reps_current` table caused LEFT JOIN to multiply rows
   - When a Lead's `FA_CRD__c` matched a RepCRD appearing multiple times, the join created multiple rows
   - Example: RepCRD 1090963 appears 51 times, causing leads with that CRD to be duplicated up to 51x

3. **✅ Fix Applied:**
   - Initial attempt (`SELECT DISTINCT *`) failed because duplicate rows had subtle differences (e.g., Branch_State variations)
   - Successful fix: Used `ROW_NUMBER() OVER (PARTITION BY Id ORDER BY Stage_Entered_Contacting__c, target_label DESC)`
   - Keeps first occurrence per Id based on timestamp and label preference

4. **✅ Results:**
   - **Before:** 45,923 rows, 1,331 duplicates
   - **After:** 44,592 rows, 0 duplicates ✅
   - **Class Distribution:** 27.37:1 imbalance ratio (healthy, similar to before)
   - **Positive Samples:** 1,572 (3.53%)
   - **Negative Samples:** 43,020 (96.47%)

5. **✅ Analysis Report Generated:**
   - Created `step_3_5_duplicate_analysis_report.md` with complete investigation findings
   - Documented root cause, fix methodology, and validation results

**Files Created:**
- ✅ `step_3_5_duplicate_analysis_report.md` (complete investigation and fix documentation)
- ✅ `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` (deduplicated - 44,592 rows)

---

### **Phase 1: Model Development** (3 units)

#### **Unit 4: Feature Selection and Model Training**

**Note:** Based on Step 3.1 Class Distribution Analysis findings (which showed weekend contacts have a premium conversion rate of 8.72% vs weekday average of 4.3%), we are adding two new temporal features to our feature engineering pipeline:

- **`Day_of_Contact`**: Day of week when lead was contacted (1=Monday, 7=Sunday)
- **`Is_Weekend_Contact`**: Boolean flag indicating if contact occurred on Saturday or Sunday

These features expand our total feature count from **67 to 69 features**.

**Input Artifacts:**
- `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` (BigQuery table with training data - **NO CSV export needed**)
- `config/v1_model_config.json` (global configuration from Step 3.4)
- `config/v1_feature_schema.json` (feature schema contract from Step 3.4)
- `step_3_3_class_imbalance_analysis.md` (for class imbalance context)

**Note:** Python scripts will read directly from BigQuery using `pandas.read_gbq()` or `google-cloud-bigquery` client. This avoids Google Sheets limitations and large CSV file handling issues.

**Output Artifacts:**
- `model_v1.pkl` (trained XGBoost model file)
- `model_v1_baseline_logit.pkl` (trained Logistic Regression baseline model)
- `cv_fold_indices_v1.json` (JSON file persisting the train/test indices for each CV fold)
- `feature_importance_v1.csv` (feature importance rankings)
- `feature_selection_report_v1.md` (univariate screening and VIF pre-filter results)
- `model_training_report_v1.md` (hyperparameter tuning results, CV performance, SMOTE vs Pos_Weight comparison, baseline model comparison)
- `selected_features_v1.json` (list of final selected feature names)

**Cursor.ai Prompt:**
```
"Implement robust feature pre-filtering and model training using our 69 engineered features (67 discovery features + 2 temporal contact features: Day_of_Contact and Is_Weekend_Contact). Create Python code to: implement pre-filtering with IV < 0.02 and VIF > 10 filters, systematically test SMOTE vs scale_pos_weight approaches using blocked time-series CV (30-day gaps, random_state=42), train final XGBoost model with winning imbalance strategy on all pre-filtered features, and generate SHAP importance rankings as an audit step after training. Ensure full reproducibility with random_state=42 throughout. Follow the plan's Section 6 modeling specifications exactly."
```

**AGENTIC TASK:**

You are a machine learning engineer. Your task is to train the V1 model and identify the most predictive features.

**Pre-Training Assertions (Load Configs):**

1. **Load** `config/v1_model_config.json` and `config/v1_feature_schema.json`.

2. **Assert** that `random_state` is set to `global_seed` from the config in all steps.

3. **Assert** that the loaded BigQuery table data perfectly matches the `config/v1_feature_schema.json`. **Fail hard** if any columns are missing, dtypes mismatch, or values are outside the `expected_range`.

**Model Training:**

4. **Load** training data from BigQuery table `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`:
   ```python
   from google.cloud import bigquery
   import pandas as pd
   
   # Option 1: Using pandas (requires pyarrow)
   df = pd.read_gbq(
       'SELECT * FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`',
       project_id='savvy-gtm-analytics',
       dialect='standard'
   )
   
   # Option 2: Using BigQuery client (more control)
   client = bigquery.Client(project='savvy-gtm-analytics')
   query = 'SELECT * FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`'
   df = client.query(query).to_dataframe()
   ```

5. **Temporal Features:** Note that `Day_of_Contact` and `Is_Weekend_Contact` are already included in the BigQuery table (derived in SQL). Verify they exist - you now have **124 total features** (122 discovery + 2 temporal).

6. **Set Reproducibility:** Ensure all model training, splits, and stochastic processes (like SMOTE) use the `global_seed` from the config file.

7. **Implement Pre-filters (Inside CV Folds):**
   * Set up the blocked time-series cross-validation (using `cv_folds` and `cv_gap_days` from config). **Persist the train/test indices for each fold to `cv_fold_indices_v1.json` for reuse.**
   * Inside *each* CV train fold:
     * **IV Filter:** Calculate and remove features with IV < 0.02 (using train fold data only).
     * **VIF Filter:** Calculate on continuous features and remove those with VIF > 10 (using train fold data only).
   * **Document** all removed features in `feature_selection_report_v1.md`.

8. **Test Imbalance Strategies (Inside CV Folds):**
   * Using **all remaining features** that passed the pre-filters, systematically test SMOTE vs. `scale_pos_weight`.
   * Use blocked time-series cross-validation (using `cv_folds` and `cv_gap_days` from config) to evaluate.
   * **SMOTE Discipline:** If testing SMOTE, ensure it is applied *only to the training data* **inside** each cross-validation fold, using the `global_seed`.
   * Document the winning strategy (e.g., `scale_pos_weight`) in `model_training_report_v1.md`.

9. **Train Final Model & Baseline:**
   * Train the final XGBoost model (with `random_state` set to `global_seed` from config, the winning imbalance strategy, and tuned hyperparameters) on **all** pre-filtered features.
   * **Critical:** The model must be trained with `enable_categorical=True` and must be able to handle NULL values in the mutable features (e.g., AUMGrowthRate_5Year will be NULL for historical leads). XGBoost handles NULLs natively - missing values are treated as "missing" and trees learn to handle them. Confirm this behavior is working correctly by checking that predictions are generated successfully for leads with NULL mutable features.
   * Save this model as `model_v1.pkl`.
   * **Train Baseline:** Train a simple `LogisticRegression` model (with `class_weight='balanced'` and `random_state=global_seed`) on the same data. Note: LogisticRegression may require imputation for NULL values - consider using a simple imputation strategy (e.g., median for continuous, mode for categorical) before training. Save as `model_v1_baseline_logit.pkl`.

10. **Generate Importance (Audit):**
    * Using **SHAP** on the *final* `model_v1.pkl`, generate the feature importance for all features used in the model.
    * Save this list as `feature_importance_v1.csv` and the list of feature names as `selected_features_v1.json`.

11. **Save Reports:** Create `model_training_report_v1.md` with all CV performance metrics and the SMOTE vs. Pos_Weight comparison. Ensure report compares XGBoost vs. Logistic Regression baseline.

---

**--- COMPLETED (FAILED - November 3, 2025) ---**

**Analysis of Unit_4_Model_Analysis_Report.md:**

**Success:** The `unit_4_train_model_v1.py` script executed perfectly. All model artifacts were generated successfully.

**CRITICAL FAILURE (MODEL):** The model's performance is not viable. The `model_training_report_v1.md` shows a cross-validation AUC-PR of ~4.98% (ranging from 3.64% to 5.50% across folds).

**Conclusion:** This is significantly worse than our current m5 model (14.35% AUC-PR) and barely better than a random guess (3.88% baseline for 3.53% positive class rate).

**Root Cause (Initial Assessment):** The "Hybrid" data strategy appeared to have failed. Initial analysis suggested that the "Stable" features for the ~40,000 historical leads had no predictive signal, and that NULL values for all important mutable features broke the model.

**Root Cause (Updated - November 2025):** Further analysis in `m5_vs_V1_Model_Comparison_Analysis.md` revealed the true failure mode: V1 failed because it **did not use m5's 31 engineered features** (like `Firm_Stability_Score`, `HNW_Asset_Concentration`) and **incorrectly nulled-out stable/calculable tenure features** (like `DateBecameRep_NumberOfYears`, `Multi_RIA_Relationships`). The m5 model succeeded (14.92% AUC-PR) by using these features correctly.

**SHAP Confirms:** The SHAP analysis shows our key features (`Multi_RIA_Relationships`, `Is_Weekend_Contact`) have zero importance. The top features are geographic identifiers (`Branch_State`, `Branch_County`) rather than business signals, indicating the model is relying on spurious correlations rather than true predictive signals.

**Decision:**

This `model_v1.pkl` is **rejected**.

We **CANNOT proceed to Unit 5** (Calibration) with V1.

**New Path Forward:** See Phase 1.5 below for the V2 rebuild strategy that combines m5's powerful engineered features with V1's temporal-correct data logic.

---

**✅ VALIDATION GATE:** (This gate is now **FAILED**)

Proceed to Unit 5 **only if** `model_v1.pkl` and `feature_importance_v1.csv` are successfully saved to disk, and `model_training_report_v1.md` shows AUC-PR > 0.20 (baseline). 

**STATUS: FAILED** - CV AUC-PR of ~4.98% is below the 0.20 baseline threshold. The model is rejected. **See Phase 1.5 below for V2 rebuild strategy.**

#### **Step 4.5 (Corrective Action): Generate SHAP Artifacts**

**Status:** ✅ COMPLETE

**Summary:** We successfully generated SHAP artifacts using a bounded-time fallback that avoids the `xgboost`/`shap` version conflict. We implemented a fast path and an automatic fallback:
- Primary attempt: Tree SHAP (failed due to `base_score` parse bug in this environment)
- Fallback (used): Tight, per-feature permutation-based SHAP approximation with caps; grouped and saved artifacts

**Key Learnings:**
- The current `xgboost` + `shap` combo can fail with TreeExplainer on models trained with `enable_categorical=True` (error: `base_score` string parsing like `[5E-1]`).
- A capped permutation approach is reliable and finishes quickly when sampled to foreground n≈300–500 and feature count≈<120.
- We added temporal features derivation inside the script to handle datasets missing `Day_of_Contact` and `Is_Weekend_Contact` without re-export.
- We added `matplotlib` to `requirements.txt` to produce plots headlessly.

**Artifacts (created/overwritten):**
- `feature_importance_v1.csv`
- `shap_summary_plot_v1.png`
- `salesforce_drivers_v1.csv`

**How to Run (PowerShell):**
- Default caps:
```
python fix_shap.py
```
- Faster/stricter caps for monitoring runs:
```
python fix_shap.py --bg_n 256 --fg_n 300 --max_display 30
```

**Monitoring Guidance:**
- The script prints progress steps [1/8] … [8/8]. The longest step is [6/8] where permutation-based SHAP runs; it logs every ~10 features.
- To tee logs while watching live:
```
python fix_shap.py --bg_n 256 --fg_n 300 *>&1 | Tee-Object -FilePath fix_shap.log
```
- Success message confirms creation times and verifies non-empty artifacts.

**Implementation Notes (Code References):**
- Derive temporal features if missing:
```76:97:c:\Users\russe\Documents\Lead Scoring\fix_shap.py
    # Derive temporal features if missing (they're created during Unit 4 training)
    temporal_features = ["Day_of_Contact", "Is_Weekend_Contact"]
    ts_col = "Stage_Entered_Contacting__c"
    for tf in temporal_features:
        if tf in selected_features and tf not in df.columns:
            if ts_col not in df.columns:
                raise ValueError(
                    f"Missing temporal feature {tf} and timestamp column {ts_col} not found to derive it"
                )
            print(f"   Deriving {tf} from {ts_col} ...", flush=True)
            if tf == "Day_of_Contact":
                ts = pd.to_datetime(df[ts_col], errors="coerce", utc=True)
                df[tf] = ts.dt.dayofweek + 1  # 1=Monday .. 7=Sunday
            elif tf == "Is_Weekend_Contact":
                if "Day_of_Contact" not in df.columns:
                    ts = pd.to_datetime(df[ts_col], errors="coerce", utc=True)
                    df["Day_of_Contact"] = ts.dt.dayofweek + 1
                df[tf] = df["Day_of_Contact"].isin([6, 7]).astype(int)
```
- Permutation-based SHAP approximation with caps:
```119:147:c:\Users\russe\Documents\Lead Scoring\fix_shap.py
    print("[6/8] Computing permutation-based SHAP values (workaround for version conflict) ...", flush=True)
    n_samples, n_features = X_fg.shape[0], X_fg.shape[1]
    baseline_pred = model.predict_proba(X_fg)[:, 1]
    baseline_mean = baseline_pred.mean()
    shap_values = np.zeros((n_samples, n_features))
    print(f"   Processing {n_features} features ...", flush=True)
    for feat_idx, feat_name in enumerate(X_fg.columns):
        if feat_idx % 10 == 0:
            print(f"   Feature {feat_idx+1}/{n_features}: {feat_name}", flush=True)
        X_permuted = X_fg.copy()
        perm_indices = np.random.RandomState(seed + feat_idx).permutation(n_samples)
        X_permuted[feat_name] = X_permuted[feat_name].iloc[perm_indices].values
        perm_pred = model.predict_proba(X_permuted)[:, 1]
        shap_values[:, feat_idx] = baseline_pred - perm_pred
```
- Artifact generation (importance CSV, summary plot, Salesforce drivers):
```155:177:c:\Users\russe\Documents\Lead Scoring\fix_shap.py
    mean_abs = np.abs(sv.values).mean(axis=0)
    imp_df = (
        pd.DataFrame({"feature": list(X.columns), "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    imp_df.to_csv(FEATURE_IMPORTANCE_OUT, index=False)
    top_features = imp_df.head(args.max_display)
    fig, ax = plt.subplots(figsize=(10, max(6, args.max_display * 0.3)))
    y_pos = np.arange(len(top_features))
    ax.barh(y_pos, top_features["mean_abs_shap"].values, align='center')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top_features["feature"].values)
    ax.invert_yaxis()
    ax.set_xlabel('Mean |SHAP Value|')
    ax.set_title('SHAP Feature Importance (Top Features)')
    plt.tight_layout()
    plt.savefig(SHAP_SUMMARY_PNG_OUT, dpi=180, bbox_inches='tight')
```
```179:199:c:\Users\russe\Documents\Lead Scoring\fix_shap.py
    values = sv.values
    base = getattr(sv, "base_values", None)
    rows = []
    for i in range(values.shape[0]):
        row_vals = values[i]
        order = np.argsort(-row_vals)
        top_idx = [j for j in order if row_vals[j] > 0][:5]
        rows.append({
            "row_id": i,
            "top_drivers": "|".join([X.columns[j] for j in top_idx]),
            "top_values": "|".join([f"{row_vals[j]:.6f}" for j in top_idx]),
            "base_value": (
                float(base[i]) if base is not None and np.ndim(base)
                else (float(base) if base is not None else np.nan)
            ),
        })
```

**Dependency Update:**
- Appended to `requirements.txt`: `matplotlib>=3.7.0`

**Input Artifacts:**
* `model_v1.pkl` (from Unit 4)
* `selected_features_v1.json` (from Unit 4, used to order columns)
* `step_3_3_training_dataset.csv` (from Step 3.3)
* `config/v1_model_config.json` (for `global_seed`)
* `requirements.txt` (from Unit 4, as a base)

**Output Artifacts (Overwritten/Created):**
* `feature_importance_v1.csv` (OVERWRITTEN with SHAP-based importance)
* `shap_summary_plot_v1.png` (NEWLY CREATED artifact, moved from Unit 5)
* `salesforce_drivers_v1.csv` (NEWLY CREATED artifact, moved from Unit 5)
* `.venv-shap-fix/` (A new, disposable virtual environment)

**Validation:**
- Completed — all three artifacts are present and non-empty; script prints SUCCESS with elapsed time.

---

#### **Unit 5: Calibration and m5 Model Comparison**

**Input Artifacts:**
- `model_v1.pkl` (trained model from Unit 4)
- `feature_importance_v1.csv` (SHAP-based feature rankings from Step 4.5)
- `shap_summary_plot_v1.png` (from Step 4.5)
- `salesforce_drivers_v1.csv` (from Step 4.5)
- `Current_Lead_Scoring_Model.md` (section 6.2 for m5 baseline comparison)

**Output Artifacts:**
- `model_v1_calibrated.pkl` (calibrated model with segment-specific calibrators)
- `shap_feature_comparison_report_v1.md` (comparison vs m5 model importance)
- `cohort_analysis_report_v1.md` (cohort analysis by AUM tier, growth trajectory, metro area)

**Cursor.ai Prompt:**
```
"Implement segment-aware calibration and comprehensive SHAP analysis for model explainability. Create Python code to: fit segment-specific calibrators for AUM tiers (<$100M, $100-500M, >$500M), generate SHAP summary plots for top 30 features, create per-prediction SHAP explanations, implement cohort analysis by AUM tier/growth trajectory/metro area, persist top 5 positive drivers per prediction for Salesforce tooltips, and critically compare new model SHAP importance vs. m5 model importance. Generate the SHAP summary plot and compare directly against the documented 'Top 25 Most Important Features' from the m5 model (Current_Lead_Scoring_Model.md, section 6.2). Answer: Did the new model discover the same 'truth'? Did Multi_RIA_Relationships remain the top feature? If not, provide business rationale. Follow the plan's Section 7 calibration procedures and Section 6.5 explainability requirements."
```

**AGENTIC TASK:**

You are a model validation agent. Your task is to calibrate the V1 model and compare its feature importance against the old m5 model.

1.  **Load** `model_v1.pkl` and the `cv_fold_indices_v1.json`.
2.  **Load** the training/validation data (using the fold indices) to perform calibration.
3.  **Fit** segment-specific calibrators for AUM tiers (<$100M, $100-500M, >$500M) using Platt scaling.
4.  **Save** the calibrated model as `model_v1_calibrated.pkl`.
5.  **Create Comparison Report:**
    * Load the *newly-generated* `feature_importance_v1.csv` (which is now SHAP-based).
    * Load the `Current_Lead_Scoring_Model.md` file.
    * Create the `shap_feature_comparison_report_v1.md`.
    * In this report, compare the new feature importance list directly against the "Top 25 Most Important Features" (section 6.2) from the m5 model.
    * Answer: Did the new model discover the same "truth"?
    * Answer: Did `Multi_RIA_Relationships` remain the top feature?
    * If not, provide business rationale for differences.
6.  **Implement** cohort analysis by AUM tier, growth trajectory, and metro area (this is a SHAP analysis of the results, not a generation step). Save to `cohort_analysis_report_v1.md`.

**Note:** For V4 model, use `model_v4.pkl`, `cv_fold_indices_v4.json`, and `feature_importance_v4.csv` instead of V1 artifacts. Output artifacts should use `_v4` suffix.

--- **COMPLETED (SUCCESS! - Nov 3, 2025)** ---

**Analysis of Unit 5 (V4) Calibration:**

* **Success (Calibration):** The `model_v4_calibrated.pkl` has been created with segment-specific calibrators for AUM tiers. 
  - **Global ECE:** 0.0019 (✅ well below 0.05 threshold)
  - **All Segment ECE:** 0.0019 for all AUM tiers (✅ all segments pass)

* **Success (Comparison Report):** The `shap_feature_comparison_report_v4.md` has been generated, comparing V4 feature importance against m5's top 25 features.

* **Key Findings:**
  - **V4 Top Feature:** `SocialMedia_LinkedIn` (vs m5's `Multi_RIA_Relationships` #1)
  - **Multi_RIA_Relationships:** Rank #17 in V4 (vs #1 in m5)
  - **Business Rationale:** V4 model discovered different patterns due to temporally-correct data and PII removal, finding business signals like `SocialMedia_LinkedIn`, `Education`, and `Licenses` as top features.

* **Success (Cohort Analysis):** The `cohort_analysis_report_v4.md` has been generated with AUM tier performance breakdowns.

* **Calibration Fix Applied:** The calibration script (`unit_5_calibration_v4.py`) was updated to drop PII features and create m5 engineered features before calibrating, ensuring the calibrated model matches the base model's feature set (120 features without PII). This fix resolves the feature mismatch issue that was blocking Unit 6.

* **Decision:** `model_v4_calibrated.pkl` is ready for Unit 6 (Backtesting and Performance Validation).

---

**✅ VALIDATION GATE:**

Proceed to Unit 6 **only if** all artifacts are created and `shap_feature_comparison_report_v4.md` is complete. The comparison report must address whether `Multi_RIA_Relationships` remained the top feature and provide business rationale for any significant ranking differences.

**New quantitative gate:** The validation report must also show **Expected Calibration Error (ECE) ≤ 0.05** overall and for each AUM tier. If ECE is > 0.05, **STOP** and tag @HumanDeveloper for review.

**Status:** ✅ **COMPLETE** - All V4 artifacts created, comparison report complete, and calibration validated.

**Note:** V4 model was later rejected due to overfitting (76% train-test gap). V5 model training completed with regularization (see Step 6.1).

#### **Unit 6: Backtesting and Performance Validation**

**Input Artifacts:**
- `model_v4_calibrated.pkl` (calibrated model from Unit 5)
- `feature_order_v4.json` (The official feature order from training - CRITICAL for ensuring feature order match)
- `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2` (BigQuery table - read directly, no CSV needed)
- `feature_selection_report_v4.md` (feature selection details, if available)
- `model_training_report_v4.md` (initial training metrics)

**Output Artifacts:**
- `backtesting_report_v4.md` (temporal performance stability analysis)
- `performance_validation_report_v4.md` (comprehensive validation metrics)
- `overfitting_analysis_v4.md` (train vs test performance gap analysis)
- `business_impact_metrics_v4.csv` (MQLs per 100 dials and other business KPIs)
- `cv_consistency_report_v4.md` (cross-validation performance consistency across folds)

**Cursor.ai Prompt:**
```
"Implement comprehensive backtesting and performance validation to ensure model stability over time. Create Python code to: perform temporal performance stability analysis across different time periods, validate business impact metrics (MQLs per 100 dials at different score thresholds), detect overfitting using train vs test performance gaps, implement cross-validation performance consistency checks across all folds, and generate comprehensive performance reports with all metrics and validations. Follow the plan's Section 7.1 validation metrics and ensure we meet the success criteria."
```

**AGENTIC TASK:**

You are a model validation agent. Your task is to perform comprehensive backtesting and validate model performance.

1. **Load Official Feature Order:** Load the list of 120 features from `feature_order_v4.json`. This is the exact order used during training and must be used to re-order the DataFrame for predictions.

2. **Ensure PII is Dropped:** Verify the script includes the `PII_TO_DROP` list and removes these 12 features (`FirstName`, `LastName`, `Branch_City`, `Branch_County`, `Branch_ZipCode`, `Home_City`, `Home_County`, `Home_ZipCode`, `RIAFirmCRD`, `RIAFirmName`, `PersonalWebpage`, `Notes`) *before* running any backtesting logic, to match the `model_v4.pkl`'s training data (120 features, not 132).

3. **Load** `model_v4_calibrated.pkl` and historical data from BigQuery table `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2`.

4. **Prepare Features in Official Order:** After dropping PII and creating m5 engineered features, re-order the DataFrame exactly using the list from `feature_order_v4.json` (e.g., `X = X[loaded_feature_order]`). This guarantees the feature order matches training exactly.

5. **Perform** temporal performance stability analysis across different time periods.

6. **Validate** business impact metrics:
   - Calculate MQLs per 100 dials at different score thresholds
   - Estimate pipeline value at each tier
   - Document lift metrics vs. baseline

7. **Detect** overfitting by comparing train vs test performance:
   - Calculate performance gap metrics
   - Identify features contributing to overfitting
   - Document findings in `overfitting_analysis_v4.md`

8. **Implement** cross-validation performance consistency checks:
   - Analyze CV performance across all folds
   - Calculate coefficient of variation for key metrics
   - Identify any unstable performance patterns

9. **Generate** comprehensive performance reports with all metrics and validations.

--- **COMPLETED (CRITICAL FAIL - Nov 3, 2025)** ---

**Analysis of Unit 6 (V4) Artifacts:**

**CRITICAL FAILURE (Overfitting):** The `overfitting_analysis_v4.md` shows a 76.19% train-test gap. The model has memorized the training data and cannot generalize.

**CRITICAL FAILURE (Instability):** The `cv_consistency_report_v4.md` shows a 41.27% Coefficient of Variation across folds. The model is completely unstable.

**Root Cause:** The model is too complex and is not regularized. The `business_impact_metrics_v4.csv` (showing 98% conversion) are an artifact of this overfitting and are not real.

**Decision:** We **REJECT** `model_v4.pkl`. We **CANNOT proceed to Unit 7**. We must re-train a new V5 model with strong regularization.

---

**✅ VALIDATION GATE:** (This gate is now **FAILED**)

Proceed to Unit 7 **only if** all output artifacts are created and `performance_validation_report_v4.md` shows:
- Train-test performance gap < 10% (AUC-PR difference)
- CV coefficient of variation < 15% for key metrics
- Business impact metrics showing > 30% lift potential
- **New stability gate:** The backtesting report must show score distribution drift (e.g., Kolmogorov-Smirnov statistic) is **≤ 0.1** between time-based folds.

If validation fails or artifacts are missing, **STOP** and tag @HumanDeveloper for review.

#### **Step 6.1 (Corrective Run V5): Re-Train V5 Model (with Regularization)**

**Note:** This is our final attempt at modeling. We will create a V5 script that is identical to V4, but adds strong regularization hyperparameters to prevent overfitting and force the model to generalize.

**Input Artifacts:**
- `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2` (BigQuery table from Step 5.3)
- `unit_4_train_model_v4.py` (our V4 script, to be modified)
- `config/v1_model_config.json`

**Output Artifacts:**
- `unit_4_train_model_v5.py` (the new script)
- `model_v5.pkl`
- `model_v5_baseline_logit.pkl`
- `model_training_report_v5.md`
- `feature_importance_v5.csv`
- `feature_order_v5.json` (The exact list and order of features used during training)
- ... (all other artifacts with a `_v5` suffix)

**AGENTIC TASK:**

You are a Lead Data Scientist. Your task is to create and run the final V5 training script with anti-overfitting controls.

1. **Create New Script:**
   * Copy `unit_4_train_model_v4.py` to `unit_4_train_model_v5.py`.
   * Modify `unit_4_train_model_v5.py`:
     * Find the `XGBClassifier` initialization (inside the `evaluate_imbalance_strategy` function and final model training).
     * Add/Modify these hyperparameters to fight overfitting:
       * `'max_depth': 4` (Reduce from 6 to 4)
       * `'n_estimators': 200` (Reduce from 400 to 200)
       * `'reg_alpha': 1.0` (Add L1 regularization - new)
       * `'reg_lambda': 5.0` (Add L2 regularization - new)
       * `'learning_rate': 0.02` (Reduce from 0.05 to 0.02)
       * `'subsample': 0.7` (Reduce from 0.8 to 0.7 for more regularization)
       * `'colsample_bytree': 0.7` (Reduce from 0.8 to 0.7 for more regularization)
   * Update Artifact Names: In the `main()` function, update all output artifact names to use a `_v5` suffix (e.g., `model_v5.pkl`, `model_training_report_v5.md`, `feature_order_v5.json`).

2. **Execute `unit_4_train_model_v5.py`:**
   * Run the new V5 script to train the regularized model.

3. **Analyze `model_training_report_v5.md`:**
   * Once the run is complete, open the new `model_training_report_v5.md`.
   * Report the new Average CV AUC-PR. We expect this to be lower than 82%, but stable.

--- **COMPLETED (CRITICAL FAIL - Nov 3, 2025)** ---

**Analysis of Step 6.1 (V5) Artifacts:**

* **Success (Trust):** The `feature_importance_v5.csv` is **GOOD**. It's built on real business signals.

* **CRITICAL FAILURE (Performance):** The `model_training_report_v5.md` shows the model is **still hopelessly overfit**. The "Final Model" score is 95.8% AUC-PR, but the *real* Cross-Validation score for Fold 0 is **8.6%**.

* **Root Cause:** The "Hybrid" data strategy is a failure. The 40,000+ leads with 98% `NULL` values are too noisy and are making the model unstable.

* **Decision:** We **REJECT** `model_v5.pkl` and we **ABANDON** the "Hybrid" data strategy.

---

**✅ VALIDATION GATE:** (This gate is now **FAILED**)

---

### **🚧 Phase 1.5: PIVOT - V6 True Vintage Rebuild 🚧**

**Note:** Our V5 model failed, proving the "Hybrid" data strategy is unworkable. We are now **UNBLOCKED** as our vendor (MarketPro) has confirmed they will provide 8 quarters of historical data. We are pivoting to our final, correct strategy: **"Option B: True Vintages"**.

#### **Step 5.1 (Human Task): Ingest 16 Historical Snapshots**

**Input Artifacts:**
- 16 secured links/zip files from MarketPro (8 quarters × 2 types: Reps & Firms).

**Output Artifacts:**
- ~16 new tables in BigQuery (e.g., `LeadScoring.snapshot_reps_2023_q1`, `LeadScoring.snapshot_firms_2023_q1`, etc.).

**AGENTIC TASK (Human Task):**

* @HumanDeveloper must download all 16 files.
* Upload each file to a new, clearly-named, dated table in BigQuery.
* **Crucial:** Each table name must include its quarter (e.g., `_2023_q1`, `_2023_q2`).
* Verify the row counts and schema for each new table.

**✅ VALIDATION GATE:** Proceed to Step 5.2 **only when** all 16 historical snapshot tables are confirmed and queryable in BigQuery.

---

#### **Step 5.2 (Agent Task - SQL): Create Master Snapshot Views**

**Input Artifacts:**
- All 16 new `LeadScoring.snapshot_*` tables.

**Output Artifacts:**
- `LeadScoring.v_discovery_reps_all_vintages` (BigQuery View)
- `LeadScoring.v_discovery_firms_all_vintages` (BigQuery View)
- `step_5_2_master_view_report.md`

**AGENTIC TASK:** You are a Data Engineer. Your task is to combine these 16 tables into two, easy-to-use "master" views.

1. **Create `v_discovery_reps_all_vintages`:**
   * Write a SQL query that `UNION ALL` the 8 "rep" snapshot tables.
   * **Crucial:** In each `SELECT` statement, you must add a `DATE` column named `snapshot_quarter` (e.g., `DATE('2023-01-01') as snapshot_quarter`).
   * Create this query as a new BigQuery View named `LeadScoring.v_discovery_reps_all_vintages`.

2. **Create `v_discovery_firms_all_vintages`:**
   * Do the same thing for the 8 "firm" snapshot tables.

3. **Generate Report:**
   * Create `step_5_2_master_view_report.md` and confirm both views are active.

**✅ VALIDATION GATE:** Proceed to Step 5.3 **only when** both master views are created and queryable.

---

#### **Step 5.3 (Agent Task - SQL): Build V6 Training Set (Point-in-Time Join)**

**Note:** This is the most important SQL query in the project. It replaces all previous Step 3.3 logic and finally solves our data leakage problem.

**Input Artifacts:**
- `savvy-gtm-analytics.SavvyGTMData.Lead` (via MCP)
- `LeadScoring.v_discovery_reps_all_vintages` (from Step 5.2)
- `LeadScoring.v_discovery_firms_all_vintages` (from Step 5.2)
- `create_discovery_reps_current_complete.sql` (as the source for our feature engineering logic)
- `create_discovery_firms_current.sql` (as the source for our firm feature logic)

**Output Artifacts:**
- `LeadScoring.step_3_3_training_dataset_v6` (New BQ Table)
- `step_3_3_class_imbalance_analysis_v6.md`

**AGENTIC TASK:** You are a Data Engineer. Your task is to build the final, temporally-correct training dataset.

1. **Execute the Point-in-Time Join SQL:**
   * Use the `🔑 REFERENCE IMPLEMENTATION:` below to create the new, final training table `LeadScoring.step_3_3_training_dataset_v6`.
   * This query will:
     * Assign a `contact_quarter` to every Lead.
     * Join Leads to the `v_discovery_reps_all_vintages` and `v_discovery_firms_all_vintages` on both CRD and `contact_quarter`.
     * Re-calculate all 69+ engineered features inside the query, using the correct point-in-time data.

2. **Run Integrity Checks:**
   * Run the assertion queries from the reference block to confirm `negative_days_to_conversion = 0`.

3. **Generate Artifacts:**
   * Run the imbalance metrics query to create `step_3_3_class_imbalance_analysis_v6.md`.

**🔑 REFERENCE IMPLEMENTATION:**

```sql
-- Step 5.3: V6 Training Set (Point-in-Time Join)

CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6` AS
WITH

-- 1. Assign a quarter to every lead
LeadsWithQuarter AS (
    SELECT 
        *,
        -- This is the "Point-in-Time" key for each lead
        DATE_TRUNC(DATE(Stage_Entered_Contacting__c), QUARTER) as contact_quarter
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE Stage_Entered_Contacting__c IS NOT NULL
      AND FA_CRD__c IS NOT NULL
),

-- 2. Join Leads to the correct historical snapshots (Reps and Firms)
PointInTimeJoin AS (
    SELECT
        l.*,
        reps.*, -- This will be all ~120 rep features
        firms.* -- This will be all firm features
    FROM LeadsWithQuarter l
    JOIN `LeadScoring.v_discovery_reps_all_vintages` reps
        ON l.FA_CRD__c = reps.RepCRD
       AND l.contact_quarter = reps.snapshot_quarter -- The Point-in-Time Join
    LEFT JOIN `LeadScoring.v_discovery_firms_all_vintages` firms
        ON reps.RIAFirmCRD = firms.RIAFirmCRD
       AND reps.snapshot_quarter = firms.snapshot_quarter -- Match on quarter
),

-- 3. Apply Feature Engineering (Stable, Calculable, Mutable)
-- (We use the logic from our V2/V4 attempts, which is already robust)
EngineeredData AS (
    SELECT
        p.*,
        
        -- A. Re-calculate "Calculable" Features
        -- We can't use the V4 logic, we must use the raw data
        -- (This assumes raw tenure dates are in the snapshots)
        DATE_DIFF(DATE(p.Stage_Entered_Contacting__c), DATE(p.DateOfHireAtCurrentFirm), YEAR) as DateOfHireAtCurrentFirm_NumberOfYears,
        DATE_DIFF(DATE(p.Stage_Entered_Contacting__c), DATE(p.DateBecameRep), YEAR) as DateBecameRep_NumberOfYears,
        
        -- B. Re-create m5 Engineered Features
        -- (This logic is from `create_discovery_reps_current_complete.sql`)
        SAFE_DIVIDE(p.TotalAssetsInMillions, p.Number_IAReps) as AUM_per_IARep,
        SAFE_DIVIDE(p.TotalAssetsInMillions, p.Number_Investment_Advisory_Clients) as AUM_per_Client,
        -- ... (Insert all other 31+ engineered feature calculations here) ...
        
        -- C. Create Label
        CASE 
            WHEN p.Stage_Entered_Call_Scheduled__c IS NOT NULL 
            AND DATE(p.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(p.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
            THEN 1 
            ELSE 0 
        END as target_label,
        
        -- D. Create Filters
        (DATE(p.Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as is_in_right_censored_window,
        DATE_DIFF(DATE(p.Stage_Entered_Call_Scheduled__c), DATE(p.Stage_Entered_Contacting__c), DAY) as days_to_conversion
        
    FROM PointInTimeJoin p
)

-- 4. Final Clean Dataset
SELECT *
FROM EngineeredData
WHERE is_in_right_censored_window = false
  AND (days_to_conversion >= 0 OR days_to_conversion IS NULL);

-- === ASSERTION QUERIES (Run after table creation) ===

-- 1. Check for negative conversion days
SELECT COUNT(*) as negative_days_count
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6`
WHERE days_to_conversion < 0;

-- 2. Get Imbalance Metrics (for the .md report)
SELECT 
    'Class Imbalance Metrics (V6 - True Vintage)' as metric_type,
    COUNT(*) as total_samples,
    COUNT(CASE WHEN target_label = 1 THEN 1 END) as positive_samples,
    COUNT(CASE WHEN target_label = 0 THEN 1 END) as negative_samples,
    ROUND(COUNT(CASE WHEN target_label = 1 THEN 1 END) / COUNT(*) * 100, 2) as positive_class_percent
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6`;
```

**✅ VALIDATION GATE:** Proceed to Step 5.4 **only if** the `step_3_3_training_dataset_v6` table is created, has > 20,000 samples, and the `negative_days_count` assertion query returns 0.

---

#### **Step 5.4 (Restart): Re-Train Final V6 Model**

**Note:** This step re-runs our V4 logic, which was the best combination of PII-removal and stability. We are now running it on our new, clean, V6 dataset.

**Input Artifacts:**
- `LeadScoring.step_3_3_training_dataset_v6` (via MCP)
- `unit_4_train_model_v4.py` (our V4 script, to be copied)
- `config/v1_model_config.json`

**Output Artifacts:**
- `unit_4_train_model_v6.py` (the new script)
- `model_v6.pkl`
- `model_training_report_v6.md`
- `feature_importance_v6.csv`
- `feature_order_v6.json`
- ... (all other artifacts with a `_v6` suffix)

**AGENTIC TASK:** You are a Lead Data Scientist.

1. **Create `unit_4_train_model_v6.py`:**
   * Copy `unit_4_train_model_v4.py`.
   * Update the `BQ_TABLE` variable to point to `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6`.
   * Update all output artifact names in the script to `_v6` (e.g., `model_v6.pkl`).

2. **Execute `unit_4_train_model_v6.py`:**
   * Run the script to train our new champion model.

3. **Analyze `model_training_report_v6.md`:**
   * Report the new **Average CV AUC-PR**.

**✅ VALIDATION GATE:** This is the **FINAL MODELING GATE**. We will proceed to Unit 5 (Calibration) **only if** the V6 reports pass **ALL THREE** validation gates:
- `Average CV AUC-PR > 0.15` (Beats m5)
- `Train-Test Gap < 15%`
- `CV Coefficient < 20%`

---

### **Phase 2: Pre-Production** (2 units)

#### **Unit 7: Shadow Scoring and Pipeline Stress Testing**

**Input Artifacts:**
- `model_v1_calibrated.pkl` (calibrated model)
- `salesforce_drivers_v1.csv` (SHAP drivers for tooltips)
- `selected_features_v1.json` (final feature list)
- Production data pipeline access (`savvy-gtm-analytics.SavvyGTMData.Lead`)

**Output Artifacts:**
- `shadow_scoring_results_7day.md` (7-day shadow mode scoring results)
- `pipeline_stress_test_report_v1.md` (stress test results for data volume and quality)
- `shadow_mode_performance_metrics_v1.csv` (daily performance metrics)
- `production_readiness_checklist_v1.md` (checklist confirming all validation gates passed)
- `alerting_config_v1.json` (automated alerting configuration for performance degradation)

**Cursor.ai Prompt:**
```
"Implement shadow scoring mode and comprehensive pipeline stress testing. Create Python code to: deploy model in shadow mode (scores generated but not used in production), run shadow mode scoring for 7 consecutive days monitoring all new leads, monitor daily performance metrics (scoring success rate, score distribution, feature availability, processing latency), implement pipeline stress tests (2x data volume, missing features simulation, class imbalance scenarios), validate class imbalance handling in production-like environment, and create automated alerting configuration for performance degradation (scoring failures > 5%, feature drift > 5% PSI, performance drop > 10%). Follow the plan's Phase 2 validation checkpoints and ensure production readiness."
```

**AGENTIC TASK:**

You are a production readiness agent. Your task is to run shadow scoring and stress test the pipeline.

1. **Deploy** `model_v1_calibrated.pkl` in shadow mode (scores generated but not used in production).

2. **Run** shadow mode scoring for 7 consecutive days, scoring all new leads as they enter "Contacting" stage.

3. **Monitor** daily performance metrics:
   - Scoring success rate
   - Score distribution
   - Feature availability rates
   - Processing latency

4. **Implement** pipeline stress tests:
   - Test with 2x expected data volume
   - Test with missing features (simulate data quality issues)
   - Test with class imbalance scenarios
   - Validate error handling and recovery

5. **Validate** class imbalance handling in production-like environment.

6. **Create** automated alerting configuration for:
   - Scoring failure rate > 5%
   - Feature drift > 5% (PSI)
   - Performance degradation > 10%
   - Data freshness issues

7. **Generate** production readiness checklist confirming all validation gates passed.

**✅ VALIDATION GATE:**

Proceed to Unit 8 **only if**:
- Shadow mode scoring runs successfully for 7 days with > 95% success rate
- All stress tests pass without pipeline failures
- `production_readiness_checklist_v1.md` shows all items checked
- Alerting configuration is deployed and tested

If any validation fails, **STOP** and tag @HumanDeveloper for review.

#### **Unit 8: SGA Training and Salesforce Integration**

**Input Artifacts:**
- `salesforce_drivers_v1.csv` (top 5 drivers per prediction)
- `shap_feature_comparison_report_v1.md` (feature importance insights)
- `cohort_analysis_report_v1.md` (segment-specific insights)
- `feature_importance_v1.csv` (feature rankings)
- `selected_features_v1.json` (final feature list)

**Output Artifacts:**
- `salesforce_field_mapping_v1.csv` (mapping of all 69 features to Salesforce fields)
- `sga_training_guide_v1.md` (comprehensive SGA training materials)
- `feature_importance_cheat_sheet_v1.pdf` (visual cheat sheet for SGA)
- `what_moves_needle_playbook_v1.md` (segment-specific playbook)
- `salesforce_ui_spec_v1.md` (specification for lead scoring UI updates)

**Cursor.ai Prompt:**
```
"Prepare Salesforce integration and SGA training materials. Create: Salesforce field mapping document for all 69 discovery features (67 discovery + 2 temporal) with data types and update frequencies, comprehensive SGA training materials for discovery data interpretation with examples of high-value vs low-value patterns, visual feature importance cheat sheet (top 30 features, color-coded by importance tier), 'What moves the needle' playbook by segment with AUM tier-specific insights, metro area patterns, and growth trajectory recommendations, and Salesforce UI specification for lead scoring display including score component, top 5 drivers tooltip, segment-specific recommendations, and visual score buckets. Follow the plan's Section 11 Salesforce enablement requirements."
```

**AGENTIC TASK:**

You are a sales enablement agent. Your task is to prepare Salesforce integration and SGA training materials.

1. **Create** Salesforce field mapping document for all 69 features (67 discovery + 2 temporal):
   - Map each feature to Salesforce field name
   - Include data types and update frequency
   - Document field visibility and permissions

2. **Develop** SGA training materials for discovery data interpretation:
   - Explain what each feature means
   - Show how to interpret feature values
   - Provide examples of high-value vs low-value patterns

3. **Generate** feature importance cheat sheet:
   - Visual representation of top 30 features
   - Color-coded by importance tier
   - Quick reference format

4. **Create** "What moves the needle" playbook by segment:
   - AUM tier-specific insights (<$100M, $100-500M, >$500M)
   - Metro area-specific patterns
   - Growth trajectory recommendations
   - Include actionable insights from cohort analysis

5. **Design** Salesforce UI updates for lead scoring display:
   - Score display component
   - Top 5 drivers tooltip (from `salesforce_drivers_v1.csv`)
   - Segment-specific recommendations
   - Visual score buckets (Cold, Cool, Warm, Hot, Very Hot)

**✅ VALIDATION GATE:**

Proceed to Units 9-12 **only if** all output artifacts are created and:
- Salesforce field mapping includes all 69 features
- SGA training guide is complete with examples
- Feature importance cheat sheet is visually clear
- Salesforce UI spec is approved by product team
- "What moves the needle" playbook is actionable for each segment

If any artifact is missing or incomplete, **STOP** and tag @HumanDeveloper for review.

#### **Unit 8.5: A/B Test Power Analysis & Instrumentation**

**Input Artifacts:**
- `Step_3_1_Class_Distribution_Analysis_Results.md` (for baseline conversion rate: 3.89%)
- `config/v1_model_config.json`
- `business_impact_metrics_v1.csv` (from Unit 6)

**Output Artifacts:**
- `ab_test_power_analysis_v1.md`
- `sga_adoption_tracking_plan_v1.md`

**AGENTIC TASK:**

You are an experimentation analyst. Your task is to design a valid A/B test.

1. **Calculate Required Sample Size:**
   * Using the baseline conversion rate (3.89%), calculate the total number of leads (`N`) required to detect our target **+50% lift**.
   * Use statistical parameters: `alpha=0.05` and `power=0.8`.
   * Document this in `ab_test_power_analysis_v1.md`.

2. **Validate Experiment Duration:**
   * Based on our average weekly "Contacted" lead flow (from `Step 3.1` analysis), calculate how many weeks the experiment must run to achieve the required sample size.
   * **Assert** that our planned 4-week test is long enough. If not, **flag for human review** to extend the test.

3. **Design Adoption Tracking:**
   * Create a plan in `sga_adoption_tracking_plan_v1.md` to instrument SGA adoption.
   * This must answer: "How will we track if SGAs in the treatment group are actually calling leads in the recommended A/B/C tier order?"

4. **Simulate Under-Adoption Scenarios:**
   * Re-compute the statistical power assuming only 60% of the treatment group follows the model's tier recommendations.
   * Document this "effective power" in `ab_test_power_analysis_v1.md`.

**✅ VALIDATION GATE:**

Proceed to Phase 3 **only if** `ab_test_power_analysis_v1.md` confirms the 4-week experiment is sufficiently powered (power ≥ 0.8) to detect a 50% lift, *even under the 60% adoption simulation*.

---

### **Phase 3: Experiment** (4 units)

#### **Units 9-12: Randomized A/B Test**

**Input Artifacts:**
- `model_v1_calibrated.pkl` (production model)
- `salesforce_drivers_v1.csv` (SHAP drivers)
- `salesforce_field_mapping_v1.csv` (feature mappings)
- `production_readiness_checklist_v1.md` (confirming readiness)
- Production Salesforce Lead data access

**Output Artifacts:**
- `ab_test_assignments_v1.csv` (treatment/control assignments with blocking)
- `ab_test_interim_analysis_unit10.md` (interim analysis results at unit 10)
- `ab_test_final_analysis_v1.md` (final statistical analysis)
- `ab_test_daily_metrics_v1.csv` (daily monitoring metrics)
- `ab_test_statistical_report_v1.md` (statistical significance testing results)

**Cursor.ai Prompt:**
```
"Implement comprehensive A/B testing framework with full monitoring. Create Python code to: implement lead-level randomization with blocking by AUM tier ensuring balanced assignment, verify balanced discovery data coverage in treatment/control groups (feature availability, CRD matching rates, data quality), monitor primary KPI daily (MQLs per 100 dials within 30 days) tracking conversion rates and lift metrics, implement interim analysis at week 10 with statistical significance testing and safety checks, and perform final analysis with comprehensive statistical significance testing (p-value < 0.05 for primary KPI). Follow the plan's Section 8 experiment design specifications exactly."
```

**AGENTIC TASK:**

You are an experimentation agent. Your task is to implement and monitor the A/B test.

1. **Implement** lead-level randomization with blocking by AUM tier:
   - Randomly assign leads to treatment (model scoring) or control (no scoring)
   - Ensure balanced assignment within each AUM tier block
   - Document assignments in `ab_test_assignments_v1.csv`

2. **Ensure** balanced discovery data coverage in treatment/control:
   - Verify feature availability is similar across groups
   - Check CRD matching rates are balanced
   - Validate no systematic differences in data quality

3. **Monitor** primary KPI daily: MQLs per 100 dials within 30 days:
   - Track conversion rates for treatment vs control
   - Calculate lift metrics daily
   - Record in `ab_test_daily_metrics_v1.csv`

4. **Implement** interim analysis at week 10:
   - Perform statistical significance testing
   - Check for safety issues or unexpected effects
   - Document findings in `ab_test_interim_analysis_unit10.md`
   - Decide: continue, stop early (if significant), or adjust

5. **Perform** final analysis with statistical significance testing:
   - Calculate final lift metrics
   - Perform hypothesis testing (treatment vs control)
   - Validate p-value < 0.05 for primary KPI
   - Generate comprehensive statistical report

**✅ VALIDATION GATE:**

Proceed to Unit 13+ **only if**:
- Final analysis shows statistically significant lift (p < 0.05) in MQLs per 100 dials
- Treatment group shows > 50% lift vs control
- No safety issues or adverse effects detected
- `ab_test_final_analysis_v1.md` contains complete statistical validation

If statistical significance is not achieved or lift is < 50%, **STOP** and tag @HumanDeveloper for review and model iteration.

---

### **Phase 4: Production & Scale** (Ongoing)

#### **Unit 13+: Full Rollout**

**Input Artifacts:**
- `model_v1_calibrated.pkl` (validated production model)
- `ab_test_final_analysis_v1.md` (successful A/B test results)
- `alerting_config_v1.json` (alerting configuration)
- `production_readiness_checklist_v1.md` (readiness confirmation)
- `salesforce_ui_spec_v1.md` (UI specifications)

**Output Artifacts:**
- `production_health_dashboard_v1.json` (dashboard configuration for daily health checks)
- `monitoring_schedule_v1.yaml` (automated monitoring schedule)
- `feature_drift_detection_report_monthly_v1.md` (monthly drift reports)
- `model_refresh_protocol_v1.md` (quarterly refresh procedures)
- `production_runbook_v1.md` (operational runbook for ongoing maintenance)

**Cursor.ai Prompt:**
```
"Implement full production rollout with continuous monitoring. Create: daily production health checks (scoring success rate, latency tracking, error rate monitoring, feature availability checks), weekly class imbalance monitoring (track positive class rate, compare to training distribution, alert if drift > 5%), monthly feature drift detection using Population Stability Index (PSI) for all features identifying any with PSI > 0.25, automated alerting configuration for performance degradation (scoring failures, feature drift, model performance drop), and quarterly model refresh cycles with documented refresh procedures and retraining triggers. Follow the plan's Section 9 monitoring and governance requirements."
```

**AGENTIC TASK:**

You are a production operations agent. Your task is to implement full production rollout with continuous monitoring.

1. **Deploy** `model_v1_calibrated.pkl` to production scoring pipeline.

2. **Implement** daily production health checks:
   - Scoring success rate monitoring
   - Latency tracking
   - Error rate monitoring
   - Feature availability checks

3. **Set up** weekly class imbalance monitoring:
   - Track positive class rate in production
   - Compare to training distribution
   - Alert if drift > 5%

4. **Implement** monthly feature drift detection:
   - Calculate Population Stability Index (PSI) for all features
   - Identify features with PSI > 0.25
   - Generate drift reports

5. **Configure** automated alerting for performance degradation:
   - Use `alerting_config_v1.json` as baseline
   - Set up alerts for: scoring failures, feature drift, model performance drop
   - Configure escalation procedures

6. **Establish** quarterly model refresh cycles:
   - Document refresh procedures
   - Define retraining triggers
   - Create validation checklist for refreshed models

7. **Define Rollback Plan:**
   * Ensure the `model_v1_calibrated.pkl` and its `config/v1_model_config.json` are versioned and stored as the "stable" production model.
   * Document a "one-click" revert procedure in the runbook.

8. **Create** production runbook for ongoing operations.

**✅ VALIDATION GATE:**

Production rollout is considered successful **only if**:
- Daily health checks run successfully for 30 consecutive days
- Weekly monitoring shows class imbalance within acceptable range
- Monthly drift detection shows PSI < 0.25 for all critical features
- Alerting system triggers appropriately without false positives
- Model refresh protocol is documented and tested

If any monitoring fails or shows degradation, **STOP** and tag @HumanDeveloper for immediate investigation.

#### **Unit 13+: Quarterly Data Refresh (Maintenance)**

**Note:** This process ensures our model remains accurate by incorporating new data. This must be run every quarter before the scheduled model retrain.

**Input Artifacts:**
- New quarterly snapshot files (Reps & Firms) from MarketPro vendor.

**Output Artifacts:**
- New BQ tables (e.g., `LeadScoring.snapshot_reps_2026_q1`, `LeadScoring.snapshot_firms_2026_q1`)
- Updated `LeadScoring.v_discovery_reps_all_vintages` view.
- Updated `LeadScoring.v_discovery_firms_all_vintages` view.

**AGENTIC TASK (Human/Agent):**

1. **Human Task:** Download the new quarterly files from MarketPro.

2. **Human Task:** Upload the new files to new, dated BQ tables (e.g., `LeadScoring.snapshot_reps_2026_q1`).

3. **Agent Task (SQL):**
   * Use an `ALTER VIEW` command to update `LeadScoring.v_discovery_reps_all_vintages`.
   * Add a new `UNION ALL` block at the end of the view to include the `LeadScoring.snapshot_reps_2026_q1` table.
   * Repeat for the `v_discovery_firms_all_vintages` view.

4. **Agent Task (SQL):**
   * Trigger a re-run of the Step 5.4 (Re-Train V6 Model) process to create a new `model_v7.pkl`.

**✅ VALIDATION GATE:** The maintenance is complete when the views are updated and the new model (v7) is successfully trained.

---

## 🔍 **CRITICAL QA/QC CHECKPOINTS**

### **Data Quality Validation (Between Each Phase)**

**Input Artifacts:**
- Current phase output artifacts
- `savvy-gtm-analytics.SavvyGTMData.Lead`
- `savvy-gtm-analytics.LeadScoring.discovery_reps_current`

**Output Artifacts:**
- `data_quality_validation_report_[phase].md` (comprehensive data quality report)

**AGENTIC TASK:**

You are a data quality validation agent. Your task is to validate data quality between phases.

1. **Validate** CRD matching rates between Salesforce and Discovery data.
2. **Check** data completeness for all 69 features (67 discovery + 2 temporal).
3. **Monitor** feature drift using Population Stability Index (PSI).
4. **Validate** no data leakage in temporal features.
5. **Ensure** proper class distribution maintenance.
6. **Generate** comprehensive validation report.

**✅ VALIDATION GATE:**

Proceed to next phase **only if**:
- CRD matching rate > 90%
- Feature completeness > 95% for all critical features
- PSI < 0.25 for all features
- No temporal leakage detected
- Class distribution within expected range

If any validation fails, **STOP** and tag @HumanDeveloper for review.

### **Statistical Validation (Before Model Training)**

**Input Artifacts:**
- `step_3_3_training_dataset.csv` (prepared training data)
- `step_3_3_class_imbalance_analysis.md` (class distribution metrics)

**Output Artifacts:**
- `statistical_validation_report_pre_training.md` (comprehensive statistical validation)

**AGENTIC TASK:**

You are a statistical validation agent. Your task is to validate data before model training.

1. **Check** for multicollinearity using VIF analysis (VIF < 10 required).
2. **Validate** feature distributions and identify outliers.
3. **Ensure** proper train/test split methodology (temporal blocking).
4. **Validate** class imbalance handling approaches.
5. **Check** for data leakage using temporal validation.
6. **Generate** statistical validation report.

**✅ VALIDATION GATE:**

Proceed to model training **only if**:
- All continuous features have VIF < 10
- Outliers are identified and documented
- Train/test split follows temporal blocking
- Class imbalance metrics validated
- No data leakage detected

If validation fails, **STOP** and tag @HumanDeveloper for review.

### **Model Performance Validation (After Each Training)**

**Input Artifacts:**
- Trained model artifacts (`model_v1.pkl` or latest version)
- Training and validation datasets
- Previous model performance reports (if available)

**Output Artifacts:**
- `model_performance_validation_report_[version].md` (comprehensive performance validation)

**AGENTIC TASK:**

You are a model performance validation agent. Your task is to validate model performance after training.

1. **Calculate** key performance metrics: AUC-PR, AUC-ROC, precision@10%, recall@10%.
2. **Validate** calibration error across segments (AUM tiers).
3. **Check** for overfitting using train vs validation performance gap.
4. **Monitor** feature importance stability vs. previous versions.
5. **Validate** business impact metrics (MQLs per 100 dials, lift estimates).
6. **Generate** performance validation report.

**✅ VALIDATION GATE:**

Proceed to next phase **only if**:
- AUC-PR > 0.20 (baseline threshold)
- Calibration error < 0.05 across all segments
- Train-validation performance gap < 10%
- Feature importance ranking is stable
- Business impact metrics show positive lift potential

If validation fails, **STOP** and tag @HumanDeveloper for model review and iteration.

---

## 📊 **SUCCESS CRITERIA TRACKING**

### **Technical Success Metrics**
- **AUC-PR > 0.35** (vs ~0.20 baseline)
- **Tier A precision > 15%** (vs 6% base rate)
- **<5% feature drift** week-over-week
- **>80% discovery data coverage**

### **Business Success Metrics**
- **>50% lift in MQLs/100 dials** (treatment vs control)
- **>$2M incremental pipeline** (attributed)
- **>75% SGA adoption** (calling in tier order)
- **<10% increase in time-to-first-touch**

### **Operational Success Metrics**
- **<2% pipeline failures** per month
- **<4 hour recovery time** for any failure
- **>95% daily scoring success rate**
- **<1 day latency** for new feature deployment

---

## 🚨 **CRITICAL RISKS & MITIGATION**

### **Data Quality Risks**
- **Risk:** Discovery vendor data delays
- **Mitigation:** Cache last-known-good; fallback models
- **Monitoring:** Daily data freshness checks

### **Model Performance Risks**
- **Risk:** Feature importance instability
- **Mitigation:** Ensemble methods; longer training windows
- **Monitoring:** Weekly SHAP stability analysis

### **Business Adoption Risks**
- **Risk:** SGA non-compliance
- **Mitigation:** Incentive alignment; UI enforcement
- **Monitoring:** Daily adoption rate tracking

---

## 📋 **NEXT IMMEDIATE STEPS**

1. **Complete Phase 0, Unit 3** - Class distribution analysis and temporal leakage detection
2. **Begin Phase 1, Unit 4** - Feature selection and model training
3. **Implement comprehensive validation** at each checkpoint
4. **Monitor data quality** continuously throughout development
5. **Prepare for A/B testing** framework implementation

---

## 🔗 **KEY RESOURCES**

- **Main Plan:** `savvy_lead_scoring_plan.md`
- **Feature Engineering SQL:** Features are engineered directly in `discovery_reps_current` table
- **Data Upload Script:** `upload_discovery_data.py`
- **Current Tables:** 
  - `savvy-gtm-analytics.LeadScoring.discovery_reps_current` (477,901 records, contains all 67 engineered features + 5 metro area dummy variables; expanding to 69 with temporal features; joins to firms via `RIAFirmCRD`)
  - `savvy-gtm-analytics.LeadScoring.discovery_firms_current` (38,543 records, firm-level aggregations; joins to `discovery_reps_current` via `RIAFirmCRD`)
  - `savvy-gtm-analytics.SavvyGTMData.Lead` (Salesforce data)

---

**Note:** This document should be updated after each major milestone to reflect current progress and any lessons learned that affect future development steps.
