# XGBoost Lead Scoring V4 - Cursor.ai Agentic Development Prompts

**Purpose:** This document transforms the V4 Development Plan into discrete, executable prompts for Cursor.ai  
**Target Directory:** `C:\Users\russe\Documents\Lead Scoring\Version-4`  
**Reference Document:** `XGBoost_ML_Lead_Scoring_V4_Development_Plan.md`  
**Created:** December 2024  

---

## 🎯 How to Use This Document

1. **Execute prompts in order** - Each prompt depends on previous outputs
2. **Wait for validation** before proceeding to next prompt
3. **Copy each prompt section** to Cursor's chat interface
4. **Check the validation criteria** after each prompt completes
5. **If validation fails**, address the issue before continuing

---

## Prerequisites Check

Before starting, ensure:
- [ ] BigQuery access to `savvy-gtm-analytics` project
- [ ] Python 3.10+ with `xgboost`, `pandas`, `google-cloud-bigquery`, `shap` installed
- [ ] The V4 Development Plan document is in the Version-4 folder
- [ ] You have read access to Version-3 folder for reference

---

## PROMPT 0.1: Create Directory Structure

**Copy this entire block to Cursor:**

```
@workspace Create the Version-4 directory structure for the XGBoost Lead Scoring project.

Context: We are building Version 4 of our lead scoring model. Version 3 used a rules-based approach that achieved 1.74x top decile lift. Version 4 will attempt an XGBoost ML approach with proper leakage prevention and regularization.

Task: Create the following directory structure in C:\Users\russe\Documents\Lead Scoring\Version-4\

Required directories:
- config/
- data/raw/
- data/processed/
- data/splits/
- data/exploration/
- sql/
- scripts/
- utils/
- models/v4.0.0/
- reports/
- tests/

Required files (create as empty placeholders):
- README.md
- VERSION_4_MODEL_REPORT.md
- EXECUTION_LOG.md
- config/constants.py
- config/feature_config.yaml
- config/model_config.yaml
- models/registry.json

Create a Python script at scripts/create_directory_structure.py that creates all of this, then run it.

Output: Print confirmation of each directory and file created.
```

**Validation Criteria:**
- [ ] All directories exist
- [ ] All placeholder files created
- [ ] Script runs without errors

---

## PROMPT 0.2: Create the Execution Logger Utility

**Copy this entire block to Cursor:**

```
@workspace Create the execution logging utility for the V4 lead scoring project.

Context: We need a logging framework that writes structured logs to EXECUTION_LOG.md as we execute each phase. This is critical for debugging and reproducibility.

Task: Create utils/execution_logger.py with the following class:

class ExecutionLogger:
    """Logs all phase execution to EXECUTION_LOG.md"""
    
    Required methods:
    1. __init__(self, base_dir: Path) - Initialize with BASE_DIR
    2. start_phase(self, phase_id: str, phase_name: str) - Start a new phase section
    3. log_action(self, action: str) - Log an action taken
    4. log_metric(self, name: str, value: Any) - Log a metric value
    5. log_gate(self, gate_id: str, name: str, passed: bool, expected: str, actual: str) - Log gate results
    6. log_warning(self, warning: str, action_taken: str = None) - Log warnings
    7. log_error(self, error: str, exception: Exception = None) - Log errors
    8. log_dataframe_summary(self, df: pd.DataFrame, name: str) - Log DF stats
    9. log_file_created(self, filename: str, filepath: str) - Log file creation
    10. end_phase(self, next_steps: List[str] = None) -> str - End phase, return status
    11. save_phase_metrics(self, metrics: Dict, filename: str) - Save metrics JSON

Key requirements:
- Use markdown format for the log
- Include timestamps
- Track gate pass/fail counts
- Support both console output and file writing
- Phase status should be PASSED, PASSED WITH WARNINGS, or FAILED

Reference: See the V4 Development Plan document for the full implementation.

Output: Create the file and print a test usage showing log output.
```

**Validation Criteria:**
- [ ] File created at `utils/execution_logger.py`
- [ ] All 11 methods implemented
- [ ] Test demonstrates markdown output format
- [ ] EXECUTION_LOG.md gets updated when logger is used

---

## PROMPT 0.3: Create the Constants Configuration

**Copy this entire block to Cursor:**

```
@workspace Create the constants configuration file for V4 lead scoring.

Context: All thresholds, paths, and configuration values must be centralized for reproducibility. This prevents magic numbers scattered through the code.

Task: Create config/constants.py with these sections:

1. PATHS SECTION:
   BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")
   DATA_DIR, MODELS_DIR, REPORTS_DIR, SQL_DIR derived from BASE_DIR

2. BIGQUERY CONFIGURATION:
   PROJECT_ID = "savvy-gtm-analytics"
   LOCATION = "northamerica-northeast2"
   DATASET_FINTRX = "FinTrx_data_CA"
   DATASET_SALESFORCE = "SavvyGTMData"
   DATASET_ML = "ml_features"

3. DATE CONFIGURATION:
   ANALYSIS_DATE = date(2025, 10, 31)  # Fixed for reproducibility
   TRAINING_START_DATE = date(2024, 2, 1)
   TRAINING_END_DATE = date(2025, 7, 31)
   TEST_START_DATE = date(2025, 8, 1)
   TEST_END_DATE = date(2025, 10, 31)
   TRAIN_TEST_GAP_DAYS = 30
   MATURITY_WINDOW_DAYS = 43

4. TARGET VARIABLE:
   TARGET_COLUMN = "converted"
   BASELINE_CONVERSION_RATE = 0.042

5. GATE CLASSES (create as dataclasses or classes with class attributes):
   - LeakageGates: MAX_INFORMATION_VALUE = 0.5
   - MulticollinearityGates: MAX_CORRELATION = 0.7, MAX_VIF = 5.0
   - OverfittingGates: MAX_TRAIN_TEST_LIFT_GAP = 0.5, MAX_TRAIN_TEST_AUC_GAP = 0.05
   - PerformanceGates: MIN_TOP_DECILE_LIFT = 1.5, MIN_AUC_ROC = 0.60

6. MODEL HYPERPARAMETERS (ModelConfig class):
   MAX_DEPTH = 4, MIN_CHILD_WEIGHT = 10, GAMMA = 0.1
   SUBSAMPLE = 0.8, COLSAMPLE_BYTREE = 0.8
   REG_ALPHA = 0.1, REG_LAMBDA = 1.0
   LEARNING_RATE = 0.05, N_ESTIMATORS = 500, EARLY_STOPPING_ROUNDS = 50

7. FEATURE LISTS:
   FEATURES_PRIMARY = ["tenure_months", "tenure_bucket", "mobility_3yr", ...]
   FEATURES_FIRM = ["firm_net_change_12mo", "firm_stability_tier", ...]
   FEATURES_EXCLUDE = ["state", "city", "days_to_conversion", "lead_id", ...]

Output: Create the file and print a summary of all gate thresholds.
```

**Validation Criteria:**
- [ ] File created at `config/constants.py`
- [ ] All 7 sections present
- [ ] Can import and access BASE_DIR, all Gate classes
- [ ] No hardcoded paths outside this file

---

## PROMPT 0.4: Create Phase 0 Environment Validation Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 0 environment validation script.

Context: Before any model development, we must validate the environment, BigQuery access, and data availability. This prevents wasted effort if dependencies are missing.

Task: Create scripts/phase_0_setup.py that:

1. STEP 0.1 - Check Python Dependencies:
   Required packages: pandas, numpy, xgboost, sklearn, google.cloud.bigquery, shap, matplotlib, seaborn, scipy, yaml
   Gate G0.1: All packages installed (BLOCKING)

2. STEP 0.2 - Test BigQuery Connectivity:
   - Connect to savvy-gtm-analytics project
   - Run "SELECT 1 as test" query
   Gate G0.2: Connection successful (BLOCKING)

3. STEP 0.3 - Validate Dataset Access:
   Test access to these tables:
   - FinTrx_data_CA.contact_registered_employment_history
   - FinTrx_data_CA.Firm_historicals
   - FinTrx_data_CA.ria_contacts_current
   - SavvyGTMData.Lead
   - SavvyGTMData.broker_protocol_members
   Gate G0.3: All datasets accessible (BLOCKING)

4. STEP 0.4 - Verify Directory Structure:
   Check all Version-4 directories exist
   Gate G0.4: All directories created (BLOCKING)

5. STEP 0.5 - Check Data Volume:
   Query count of contacted leads with FA_CRD__c
   Gate G0.5: >= 10,000 contacted leads (BLOCKING)

Requirements:
- Use ExecutionLogger from utils/execution_logger.py
- Use constants from config/constants.py
- Print clear pass/fail for each gate
- Return True only if all BLOCKING gates pass
- Write results to EXECUTION_LOG.md

Structure:
def run_phase_0() -> bool:
    logger = ExecutionLogger(BASE_DIR)
    logger.start_phase("0", "Environment Setup & Preflight")
    # ... implementation
    logger.end_phase(next_steps=["Phase 1: Data Extraction"])
    return all_gates_passed

if __name__ == "__main__":
    success = run_phase_0()
    sys.exit(0 if success else 1)

Output: Create the script and RUN IT. Report all gate results.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_0_setup.py`
- [ ] Script runs without import errors
- [ ] All BLOCKING gates pass (or report what's failing)
- [ ] EXECUTION_LOG.md updated with Phase 0 results

---

## PROMPT 1.1: Create the Target Definition SQL

**Copy this entire block to Cursor:**

```
@workspace Create the SQL query that defines our target variable for lead scoring.

Context: Our target is whether a "Contacted" lead converts to "MQL" within 43 days. We must use Point-in-Time (PIT) methodology to prevent data leakage.

Task: Create sql/phase_1_target_definition.sql with:

Target Definition Rules:
1. Lead must have stage_entered_contacting__c IS NOT NULL
2. Lead must have FA_CRD__c IS NOT NULL (FINTRX match)
3. Convert = 1 if stage_entered_mql__c within 43 days of contacted date
4. Convert = 0 if 43+ days passed without MQL conversion
5. Exclude leads too recent to determine outcome (right-censored)

Required CTEs:
1. contacted_leads: All leads that entered Contacted status
2. mql_outcomes: Leads that converted to MQL
3. maturity_check: Calculate days since contact
4. final_target: Join and apply target definition

Key columns in output:
- lead_id
- advisor_crd (FA_CRD__c)
- contacted_date
- mql_date (NULL if not converted)
- days_to_conversion (NULL if not converted)
- target (1 = converted, 0 = not converted, NULL = right-censored)
- is_mature (1 if >= 43 days since contact)
- lead_source_original
- lead_source_grouped (LinkedIn, Provided Lists, Organic/Other)

Important:
- Use DATE(stage_entered_contacting__c) for contacted_date
- Use DATE(stage_entered_mql__c) for mql_date
- Filter: contacted_date >= '2024-02-01' AND contacted_date <= '2025-10-31'
- Exclude Company LIKE '%Savvy%'

Output table: `savvy-gtm-analytics.ml_features.v4_target_variable`

Create the SQL file. Do NOT run it yet.
```

**Validation Criteria:**
- [ ] SQL file created at `sql/phase_1_target_definition.sql`
- [ ] All CTEs present
- [ ] Maturity window is 43 days
- [ ] Right-censored leads are excluded or marked NULL
- [ ] Lead source grouping is correct

---

## PROMPT 1.2: Create Phase 1 Data Extraction Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 1 data extraction script that runs the target definition SQL.

Context: This script executes the target definition SQL, validates the output, and creates the base dataset for feature engineering.

Task: Create scripts/phase_1_data_extraction.py that:

1. STEP 1.1 - Execute Target Definition SQL:
   - Read sql/phase_1_target_definition.sql
   - Execute against BigQuery
   - Create table ml_features.v4_target_variable

2. STEP 1.2 - Validate Target Distribution:
   Gate G1.1: >= 10,000 mature leads (BLOCKING)
   Gate G1.2: Conversion rate between 2% - 8% (WARNING)
   Gate G1.3: Right-censoring rate <= 40% (WARNING)

3. STEP 1.3 - Check FINTRX Coverage:
   Gate G1.4: FINTRX match rate >= 75% (WARNING)

4. STEP 1.4 - Check Employment History:
   Gate G1.5: Employment history coverage >= 70% (WARNING)

5. STEP 1.5 - Analyze Lead Source Distribution:
   - Calculate % Provided Lists, % LinkedIn, % Other
   - Log distribution over time (by quarter)
   - Log any significant drift

6. STEP 1.6 - Save Exploration Data:
   - Save target_variable_analysis.json to data/raw/
   - Save lead_source_distribution.csv to data/exploration/

Requirements:
- Use ExecutionLogger throughout
- All gate results must be logged
- Save summary statistics to JSON
- Continue even if WARNING gates fail, STOP if BLOCKING gates fail

Output: Create the script and RUN IT. Report all gate results and the conversion rate.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_1_data_extraction.py`
- [ ] BigQuery table `ml_features.v4_target_variable` created
- [ ] G1.1 passes (>= 10,000 leads)
- [ ] Conversion rate logged (should be ~4.2%)
- [ ] JSON summary saved

---

## PROMPT 2.1: Create Point-in-Time Feature Engineering SQL

**Copy this entire block to Cursor:**

```
@workspace Create the SQL for Point-in-Time (PIT) feature engineering.

Context: Data leakage is the #1 risk in lead scoring models. Every feature must be calculated using ONLY data available at the time of contact. We use contacted_date as our "prediction time" and never look forward.

Task: Create sql/phase_2_feature_engineering.sql with these feature groups:

GROUP 1 - TENURE FEATURES (from employment history):
- current_firm_tenure_months: Months at current firm as of contacted_date
- tenure_bucket: Categorized (0-12, 12-24, 24-48, 48-120, 120+)
- industry_tenure_months: Total months in industry as of contacted_date
- experience_years: industry_tenure_months / 12

GROUP 2 - MOBILITY FEATURES:
- pit_moves_3yr: Number of firm changes in 3 years BEFORE contacted_date
- mobility_tier: Stable (0), Low (1), High (2+)
- is_wirehouse: 1 if current employer matches wirehouse patterns

GROUP 3 - FIRM STABILITY (from Firm_historicals):
- firm_net_change_12mo: Rep count change in 12 months BEFORE contacted_date
- firm_departures_12mo: Departures in 12 months BEFORE contacted_date
- firm_arrivals_12mo: Arrivals in 12 months BEFORE contacted_date
- firm_stability_tier: Heavy_Bleeding (<-10), Light_Bleeding (-10 to 0), Stable (0), Growing (>0)
- has_firm_data: 1 if firm data exists

GROUP 4 - INTERACTION FEATURES (Prioritized by exploration results):
- mobility_x_heavy_bleeding: TOP PRIORITY - Mobile (2+ moves) AND Heavy Bleeding (<-10 net change) - 4.85x lift
- short_tenure_x_high_mobility: HIGH PRIORITY - Short tenure (<24 months) AND High mobility (2+ moves) - 4.59x lift
- tenure_bucket_x_mobility: Numeric interaction for gradient boosting

GROUP 5 - DATA QUALITY FLAGS:
- has_email, has_linkedin, has_fintrx_match, has_employment_history

CRITICAL PIT RULES:
1. For employment_history: WHERE pit_start_date <= contacted_date
2. For Firm_historicals: WHERE historical_date <= contacted_date
3. NEVER use *_current tables directly for calculations
4. Each feature must have a comment explaining its PIT compliance

Output table: `savvy-gtm-analytics.ml_features.v4_features_pit`

Join back to v4_target_variable to preserve lead_id and target.

Create the SQL file. Do NOT run it yet.
```

**Validation Criteria:**
- [ ] SQL file created at `sql/phase_2_feature_engineering.sql`
- [ ] All 5 feature groups present
- [ ] PIT date filters on all historical tables
- [ ] Comments explaining PIT compliance for each feature
- [ ] Interaction features correctly calculated

---

## PROMPT 2.2: Create Phase 2 Feature Engineering Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 2 feature engineering execution script.

Context: This script executes the feature engineering SQL and validates the outputs for leakage and completeness.

Task: Create scripts/phase_2_feature_engineering.py that:

1. STEP 2.1 - Execute Feature Engineering SQL:
   - Read sql/phase_2_feature_engineering.sql
   - Execute against BigQuery
   - Create table ml_features.v4_features_pit

2. STEP 2.2 - Validate Feature Count:
   Gate G2.1: >= 15 features created (WARNING)

3. STEP 2.3 - PIT Compliance Check:
   - For each feature, verify no future data by checking correlation with target
   Gate G2.2: No features with suspiciously high correlation (>0.3) (BLOCKING)

4. STEP 2.4 - Null Rate Analysis:
   - Calculate null rate for each feature
   Gate G2.3: No feature with >50% null rate (WARNING)

5. STEP 2.5 - Validate Interaction Features:
   Gate G2.4: All interaction features calculated correctly (WARNING)

6. STEP 2.6 - Row Count Preservation:
   Gate G2.5: Same row count as target table (BLOCKING)

7. STEP 2.7 - Feature Summary:
   - Save feature_summary.csv with: feature_name, null_rate, mean, std, correlation_with_target
   - Save to data/processed/

Requirements:
- Log all feature statistics
- Flag any suspiciously predictive features (potential leakage)
- Save feature list for Phase 3 audit

Output: Create the script and RUN IT. Report feature count and any warnings.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_2_feature_engineering.py`
- [ ] BigQuery table `ml_features.v4_features_pit` created
- [ ] All gates evaluated and logged
- [ ] feature_summary.csv saved
- [ ] Row count matches target table

---

## PROMPT 3.1: Create the Leakage Audit Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 3 leakage audit script.

Context: Data leakage is the silent killer of ML models. We need to audit every feature to ensure it doesn't use future information.

Task: Create scripts/phase_3_leakage_audit.py that:

1. STEP 3.1 - Document All Features:
   - Load v4_features_pit from BigQuery
   - Create feature inventory with: name, data_type, source_table, is_pit_safe
   Gate G3.1: 0 features undocumented (WARNING)

2. STEP 3.2 - Calculate Information Value (IV):
   - Calculate IV for each feature vs target
   - IV = sum( (% of events - % of non-events) * ln(% events / % non-events) )
   Gate G3.2: 0 features with IV > 0.5 (BLOCKING - likely leakage)

3. STEP 3.3 - Validate Tenure Logic:
   - Check that tenure_months >= 0 for all records
   - Check that tenure_months <= industry_tenure_months
   Gate G3.3: 0 negative tenure values (BLOCKING)

4. STEP 3.4 - Validate Mobility Logic:
   - Check pit_moves_3yr is reasonable (0-10 range)
   Gate G3.4: Max moves <= 10 (WARNING)

5. STEP 3.5 - Validate Interaction Features:
   - Recalculate interactions and compare to stored values
   Gate G3.5: All interactions match recalculation (BLOCKING)

6. STEP 3.6 - Lift Consistency Check:
   - Calculate lift for top signals vs V3 validation (should be similar)
   - Expected: mobility_x_heavy_bleeding ~4.85x (20.37% conversion), short_tenure_x_high_mobility ~4.59x (19.27% conversion)
   Gate G3.6: Lifts within 20% of expected (WARNING)

7. STEP 3.7 - Generate Leakage Report:
   - Create reports/leakage_audit_report.md with all findings
   - List any suspicious features
   - Recommend features to exclude

Output: Create the script and RUN IT. Report any leakage concerns.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_3_leakage_audit.py`
- [ ] All gates evaluated
- [ ] leakage_audit_report.md generated
- [ ] No features with IV > 0.5 (if any, investigate before proceeding)
- [ ] Tenure validation passes

---

## PROMPT 4.1: Create the Multicollinearity Analysis Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 4 multicollinearity analysis script.

Context: Correlated features cause unstable model coefficients and make interpretation unreliable. We need to identify and remove highly correlated features.

Task: Create scripts/phase_4_multicollinearity.py that:

1. STEP 4.1 - Load Feature Data:
   - Load v4_features_pit from BigQuery
   - Separate features from target

2. STEP 4.2 - Calculate Correlation Matrix:
   - Calculate Pearson correlations between all numeric features
   - Save correlation heatmap to reports/
   - List all pairs with |correlation| > 0.7
   Gate G4.1: <= 3 feature pairs with correlation > 0.7 (WARNING)

3. STEP 4.3 - Calculate VIF (Variance Inflation Factor):
   - Calculate VIF for each feature
   - VIF = 1 / (1 - R²) where R² is from regressing feature on all others
   Gate G4.2: <= 2 features with VIF > 5 (WARNING)

4. STEP 4.4 - Feature Removal Decision:
   - For each high-correlation pair:
     - Keep the feature with higher lift/IV
     - Log the decision
   - Remove high-VIF features if they're not among top predictors

5. STEP 4.5 - Final Feature Set:
   - Create final_features list after removals
   Gate G4.3: Max VIF in final set <= 7.5 (WARNING)

6. STEP 4.6 - Save Outputs:
   - reports/multicollinearity_report.md
   - data/processed/final_features.json
   - reports/correlation_heatmap.png

Output: Create the script and RUN IT. Report removed features and final count.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_4_multicollinearity.py`
- [ ] Correlation matrix calculated
- [ ] VIF calculated for all features
- [ ] final_features.json saved
- [ ] Clear log of which features removed and why

---

## PROMPT 5.1: Create the Train/Test Split Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 5 train/test split script.

Context: We use temporal splitting to prevent leakage. Training data is from before July 2025, test data is Aug-Oct 2025, with a 30-day gap between them.

Task: Create scripts/phase_5_train_test_split.py that:

1. STEP 5.1 - Load Feature Data:
   - Load v4_features_pit from BigQuery
   - Parse contacted_date as datetime

2. STEP 5.2 - Define Split Boundaries:
   - Training: Feb 2024 to July 31, 2025
   - Gap: August 2025 (30 days)
   - Test: Aug 1, 2025 to Oct 31, 2025
   - Log exact date ranges

3. STEP 5.3 - Create Temporal Splits:
   - Assign 'TRAIN', 'TEST', or 'EXCLUDE' (gap period)
   - Log count in each split
   Gate G5.1: Training set >= 20,000 leads (BLOCKING)
   Gate G5.2: Test set >= 3,000 leads (BLOCKING)

4. STEP 5.4 - Check Lead Source Distribution:
   - Calculate % LinkedIn in train vs test
   - Log distribution for each split
   Gate G5.3: LinkedIn % drift <= 20% between train/test (WARNING)

5. STEP 5.5 - Check Conversion Rate Consistency:
   - Compare train conversion rate vs test conversion rate
   Gate G5.4: Relative difference <= 30% (WARNING)

6. STEP 5.6 - Create CV Folds (Time-Based):
   - Create 5 time-based folds within training set
   - Assign cv_fold column (1-5, sorted by contacted_date)
   - Log fold statistics

7. STEP 5.7 - Save Splits:
   - Upload to BigQuery: ml_features.v4_splits
   - Save locally: data/splits/train.csv, data/splits/test.csv
   Gate G5.5: Train/Test gap >= 30 days (BLOCKING)

Output: Create the script and RUN IT. Report split sizes and conversion rates.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_5_train_test_split.py`
- [ ] BigQuery table `ml_features.v4_splits` created
- [ ] Train and test CSVs saved locally
- [ ] All gates evaluated
- [ ] CV folds properly assigned

---

## PROMPT 6.1: Create the Model Training Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 6 XGBoost model training script.

Context: We train XGBoost with strong regularization to prevent overfitting. We use early stopping and validate against a holdout test set.

Task: Create scripts/phase_6_model_training.py that:

1. STEP 6.1 - Load Split Data:
   - Load train and test from data/splits/
   - Load final_features.json for feature list
   - Separate X and y for train and test

2. STEP 6.2 - Calculate Class Weight:
   - scale_pos_weight = count(negative) / count(positive)
   - Log the calculated value (~22.8 for 4.2% positive rate)

3. STEP 6.3 - Configure Model Parameters:
   Use ModelConfig from constants.py:
   - max_depth=4, min_child_weight=10, gamma=0.1
   - subsample=0.8, colsample_bytree=0.8
   - reg_alpha=0.1, reg_lambda=1.0
   - learning_rate=0.05, n_estimators=500
   - early_stopping_rounds=50
   - scale_pos_weight (calculated)
   - eval_metric=['auc', 'aucpr', 'logloss']

4. STEP 6.4 - Train with Early Stopping:
   - Use eval_set=[(X_train, y_train), (X_test, y_test)]
   - Enable verbose logging
   - Record best_iteration
   Gate G6.1: Early stopping triggered before max rounds (WARNING)

5. STEP 6.5 - Evaluate Performance:
   Calculate on BOTH train and test:
   - AUC-ROC
   - AUC-PR
   - Top 10% lift
   - Top 5% lift

6. STEP 6.6 - Check for Overfitting:
   - Calculate train-test lift gap
   - Calculate train-test AUC gap
   Gate G6.2: Lift gap <= 0.5x (BLOCKING)
   Gate G6.3: AUC gap <= 0.05 (WARNING)

7. STEP 6.7 - Save Model Artifacts:
   - models/v4.0.0/model.pkl (pickle)
   - models/v4.0.0/model.json (XGBoost native)
   - models/v4.0.0/feature_importance.csv
   - models/v4.0.0/training_metrics.json

Output: Create the script and RUN IT. Report train/test metrics and overfitting assessment.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_6_model_training.py`
- [ ] Model trained successfully
- [ ] Early stopping triggered (best_iteration < 500)
- [ ] Test AUC-ROC >= 0.60
- [ ] Lift gap reasonable (< 0.5x)
- [ ] All artifacts saved

---

## PROMPT 7.1: Create the Overfitting Detection Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 7 overfitting detection script.

Context: Beyond train/test comparison, we need cross-validation analysis and learning curves to confirm the model generalizes.

Task: Create scripts/phase_7_overfitting_check.py that:

1. STEP 7.1 - Load Model and Data:
   - Load model from models/v4.0.0/model.pkl
   - Load training data with CV folds

2. STEP 7.2 - Time-Based Cross-Validation:
   - Use the 5 time-based folds
   - For each fold: train on folds 1-N, test on fold N+1
   - Calculate AUC-ROC for each fold
   Gate G7.1: CV score std dev < 0.1 (WARNING)

3. STEP 7.3 - Learning Curve Analysis:
   - Train models on 20%, 40%, 60%, 80%, 100% of data
   - Plot training and validation AUC vs training size
   - Save reports/learning_curve.png
   Gate G7.2: Validation curve converges (no divergence) (WARNING)

4. STEP 7.4 - Segment Performance Analysis:
   - Calculate performance by lead_source_grouped
   - Calculate performance by tenure_bucket
   - Identify any segments with dramatically different performance

5. STEP 7.5 - Generate Report:
   - Create reports/overfitting_report.md
   - Include CV results, learning curve, segment analysis
   - Recommendation: proceed or investigate

Output: Create the script and RUN IT. Report CV variance and learning curve convergence.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_7_overfitting_check.py`
- [ ] CV completed for all 5 folds
- [ ] Learning curve plot saved
- [ ] overfitting_report.md generated
- [ ] No major overfitting signals

---

## PROMPT 8.1: Create the Model Validation Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 8 model validation script.

Context: This is the final validation before deployment. We need to confirm the model beats baseline and V3 rules.

Task: Create scripts/phase_8_validation.py that:

1. STEP 8.1 - Load Test Data and Model:
   - Load holdout test set
   - Load trained model
   - Generate predictions

2. STEP 8.2 - Calculate Core Metrics:
   - AUC-ROC
   - AUC-PR
   - Log loss
   Gate G8.1: Top decile lift >= 1.5x (BLOCKING)
   Gate G8.2: AUC-ROC >= 0.60 (WARNING)
   Gate G8.3: AUC-PR >= 0.10 (WARNING)

3. STEP 8.3 - Lift by Decile:
   - Sort predictions, divide into deciles
   - Calculate lift for each decile
   - Create lift chart
   - Save reports/lift_chart.png

4. STEP 8.4 - Statistical Significance:
   - Calculate 95% confidence intervals for top decile lift
   - Use bootstrap with 1000 samples
   Gate G8.4: p-value < 0.05 for lift > 1.0 (WARNING)

5. STEP 8.5 - Segment Performance:
   - Calculate metrics by lead_source_grouped
   - Calculate metrics by tenure_bucket
   - Identify any weak segments

6. STEP 8.6 - Comparison to V3:
   - V3 rules achieved 1.74x top decile lift
   - Log comparison: V4 vs V3

7. STEP 8.7 - Generate Validation Report:
   - Create reports/validation_report.md
   - Include all metrics, charts, comparisons
   - Final recommendation

Output: Create the script and RUN IT. Report if V4 beats V3 baseline.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_8_validation.py`
- [ ] All gates evaluated
- [ ] Lift chart generated
- [ ] validation_report.md complete
- [ ] Clear comparison to V3 (1.74x baseline)

---

## PROMPT 9.1: Create the SHAP Analysis Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 9 SHAP analysis script.

Context: SHAP values provide interpretability. We need to understand which features drive predictions.

Task: Create scripts/phase_9_shap_analysis.py that:

1. STEP 9.1 - Load Model and Sample:
   - Load model from models/v4.0.0/
   - Sample 1000-2000 records from test set for SHAP (memory constraint)

2. STEP 9.2 - Calculate SHAP Values:
   - Use shap.TreeExplainer for XGBoost
   - Calculate SHAP values for sampled records
   - Save shap_values.pkl to models/v4.0.0/

3. STEP 9.3 - Generate Summary Plots:
   - SHAP summary plot (beeswarm)
   - SHAP bar plot (mean absolute)
   - Save to reports/shap_summary.png, reports/shap_bar.png

4. STEP 9.4 - Feature Importance Comparison:
   - Compare XGBoost native importance vs SHAP importance
   - Log any discrepancies

5. STEP 9.5 - Dependence Plots:
   - Create dependence plots for top 3 features
   - Save to reports/

6. STEP 9.6 - Validate Against Domain Knowledge:
   - Confirm signs align with expectations:
     - Short tenure → higher score
     - High mobility → higher score
     - Bleeding firm → higher score
     - Wirehouse → higher score (POSITIVE signal - 2.15x lift, contradicts V3 exclusion)
     - Broker Protocol → higher score

7. STEP 9.7 - Generate SHAP Report:
   - Create reports/shap_report.md
   - List top 10 features by SHAP importance
   - Include interpretation of each

Output: Create the script and RUN IT. Report top 5 features by SHAP importance.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_9_shap_analysis.py`
- [ ] SHAP values calculated
- [ ] All plots generated
- [ ] shap_report.md complete
- [ ] Feature signs align with domain expectations

---

## PROMPT 10.1: Create the Production Deployment SQL

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 10 production deployment SQL.

Context: We need to create a BigQuery view/table that can score new leads daily using the trained model features.

Task: Create sql/production_scoring.sql that:

1. Create a view ml_features.v4_production_features that:
   - Pulls leads from SavvyGTMData.Lead
   - Joins to FINTRX employment history
   - Calculates all PIT-safe features
   - Uses CURRENT_DATE() as the "prediction time"

2. Create a table ml_features.v4_daily_scores that:
   - Calculates scores for all leads with:
     - status = 'Contacted'
     - FA_CRD__c IS NOT NULL
     - NOT already in MQL status
   - Includes all features needed for model inference

3. Include these columns:
   - lead_id, advisor_crd
   - All feature columns
   - scored_at (timestamp)
   - model_version ('v4.0.0')

4. Add comments explaining:
   - How to refresh daily
   - What triggers a rescore
   - Data freshness expectations

Note: The actual ML scoring will happen in Python. This SQL prepares the features.

Output: Create the SQL file. Do NOT run it yet.
```

**Validation Criteria:**
- [ ] SQL file created at `sql/production_scoring.sql`
- [ ] View and table definitions present
- [ ] All features match training features
- [ ] Comments explain usage

---

## PROMPT 10.2: Create the Deployment Script

**Copy this entire block to Cursor:**

```
@workspace Create the Phase 10 deployment script.

Context: This script packages the model for production and updates the model registry.

Task: Create scripts/phase_10_deployment.py that:

1. STEP 10.1 - Validate Model Artifacts:
   - Check all required files exist in models/v4.0.0/
   - model.pkl, model.json, feature_importance.csv, training_metrics.json

2. STEP 10.2 - Execute Production SQL:
   - Run sql/production_scoring.sql
   - Verify table creation

3. STEP 10.3 - Create Model Scorer Class:
   - Create inference/lead_scorer_v4.py with:
     - load_model() - load from pickle
     - prepare_features(df) - ensure feature order matches training
     - score_leads(df) - return predictions
     - get_feature_importance() - return importance dict

4. STEP 10.4 - Update Model Registry:
   - Update models/registry.json with:
     - model_version: 'v4.0.0'
     - training_date: ISO timestamp
     - test_metrics: from training_metrics.json
     - feature_count: number of features
     - status: 'production' or 'candidate'

5. STEP 10.5 - Generate Final Report:
   - Create VERSION_4_MODEL_REPORT.md with:
     - Executive summary
     - Model performance
     - Feature importance
     - Comparison to V3
     - Deployment instructions
     - Monitoring recommendations

6. STEP 10.6 - Finalize Execution Log:
   - Close out EXECUTION_LOG.md
   - Calculate total development time
   - List all gates passed/failed

Output: Create the script and RUN IT. Report final model status.
```

**Validation Criteria:**
- [ ] Script created at `scripts/phase_10_deployment.py`
- [ ] production_scoring.sql executed successfully
- [ ] lead_scorer_v4.py created
- [ ] registry.json updated
- [ ] VERSION_4_MODEL_REPORT.md complete
- [ ] EXECUTION_LOG.md finalized

---

## PROMPT 11.1: Create Unit Tests

**Copy this entire block to Cursor:**

```
@workspace Create unit tests for the V4 lead scoring model.

Context: We need automated tests to validate PIT compliance and model behavior.

Task: Create the following test files:

1. tests/test_pit_compliance.py:
   - test_no_future_dates: Verify all features use dates <= contacted_date
   - test_tenure_positive: Verify tenure >= 0
   - test_mobility_range: Verify mobility in expected range
   - test_interaction_formulas: Verify interactions calculated correctly

2. tests/test_feature_engineering.py:
   - test_feature_count: Verify expected number of features
   - test_no_nulls_in_required: Verify key features have values
   - test_wirehouse_detection: Verify wirehouse patterns match
   - test_tenure_bucket_logic: Verify bucket assignments

3. tests/test_model_predictions.py:
   - test_predictions_in_range: All predictions between 0 and 1
   - test_high_signal_leads_score_higher: Known high-signal profiles score above median
   - test_feature_order_matches: Verify inference uses correct feature order
   - test_model_load_and_predict: End-to-end test

Use pytest for all tests. Create a conftest.py with fixtures for sample data.

Output: Create all test files. Run pytest and report results.
```

**Validation Criteria:**
- [ ] All 3 test files created
- [ ] conftest.py with fixtures
- [ ] All tests pass
- [ ] Coverage includes critical paths

---

## Error Handling Guide

### If a BLOCKING Gate Fails

1. **STOP immediately** - Do not proceed to next phase
2. **Investigate the cause** - Check the logged actual vs expected values
3. **Address the issue** - Fix data, SQL, or code as needed
4. **Re-run the phase** - Execute the script again from the beginning
5. **Document in EXECUTION_LOG.md** - Note what failed and how it was fixed

### If a WARNING Gate Fails

1. **Log the warning** - Document in EXECUTION_LOG.md
2. **Assess severity** - Is this a known issue or unexpected?
3. **Continue if acceptable** - Proceed to next phase if within tolerance
4. **Monitor in production** - Add to monitoring checklist

### Common Issues and Solutions

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| G0.2 BigQuery fails | Auth not configured | Run `gcloud auth application-default login` |
| G1.1 Too few leads | Date range too narrow | Check TRAINING_START_DATE and END_DATE |
| G3.2 High IV feature | Data leakage | Remove feature, investigate source |
| G6.2 Large lift gap | Overfitting | Increase regularization, reduce depth |
| G8.1 Low lift | Weak features | Review feature engineering, add interactions |

---

## Summary Checklist

After completing all prompts:

- [ ] Phase 0: Environment validated, directories created
- [ ] Phase 1: Target variable defined, 10K+ leads
- [ ] Phase 2: 15+ PIT-safe features engineered
- [ ] Phase 3: Leakage audit passed, no suspicious features
- [ ] Phase 4: Multicollinearity addressed, final feature set defined
- [ ] Phase 5: Train/test splits created with 30-day gap
- [ ] Phase 6: XGBoost trained, lift gap < 0.5x
- [ ] Phase 7: CV variance < 0.1, learning curves converge
- [ ] Phase 8: Top decile lift >= 1.5x, compared to V3
- [ ] Phase 9: SHAP analysis complete, interpretable
- [ ] Phase 10: Production SQL deployed, registry updated
- [ ] Tests: All unit tests pass

---

**Document Version:** 1.0.0  
**Created:** December 2024  
**Status:** Ready for Cursor.ai Execution
