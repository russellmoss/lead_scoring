# Current Lead Scoring Model Documentation

## Overview

This document defines the Lead Scoring Model (m5) built to predict the likelihood that a financial advisor lead will be called (`EverCalled`). The model uses a calibrated XGBoost classifier with SMOTE oversampling to handle class imbalance.

---

## 1. Data Sources

The model relies on three primary data sources that are merged together:

### 1.1 Salesforce Leads (`sf_leads.pkl`)
**Source**: Salesforce Lead object query  
**Key Fields**:
- `FA_CRD__c`: Financial Advisor CRD number (unique identifier)
- `Full_Prospect_ID__c`: Full prospect identifier
- `ConvertedDate`, `CreatedDate`: Lead lifecycle dates
- `IsConverted`: Boolean indicating if lead was converted
- `Stage_Entered_Call_Scheduled__c`: Timestamp when call was scheduled
- `Savvy_Lead_Score__c`: Existing lead score (descriptive only)
- `Owner`, `Owner.Name`: Lead owner information
- Contact information: `Email`, `FirstName`, `LastName`, `MobilePhone`, etc.
- Location: `Address`, `City`, `State`
- Lead metadata: `LeadSource`, `Status`, `Title`, `Company`, etc.

**Size**: ~69,809 records

### 1.2 Discovery Rep Data (`discovery_data.pkl`)
**Source**: Discovery data processing pipeline (see README in `/data/raw_discovery_data`)  
**Key Fields**:
- `RepCRD`: Representative CRD number (primary key)
- `RIAFirmCRD`: RIA Firm CRD number
- `KnownNonAdvisor`: Boolean flag indicating if rep is known non-advisor
- Rep characteristics: `Title_rep`, `TitleCategories`, `FullName`
- Professional metrics: `DuallyRegisteredBDRIARep`, `NumberFirmAssociations`, `NumberRIAFirmAssociations`
- Experience metrics: Years as rep, years at current firm, prior firm tenure
- Client and asset metrics: Number of clients, assets under management by category
- Location: `Home_MetropolitanArea`, `MilesToWork`

**Size**: Variable (contains rep-level information)

### 1.3 Firm Data (`FirmData.csv`)
**Source**: RIA Firm information  
**Key Fields**:
- `RIAFirmCRD`: RIA Firm CRD number (primary key)
- `RIALegalFirmName`: Legal firm name
- Firm metrics: `Number_Employees`, `Number_BranchAdvisors`, `Number_IAReps`
- AUM and growth metrics: `TotalAssetsInMillions`, `AUMGrowthRate_1Year`, `AUMGrowthRate_5Year`
- Client composition: Client counts and asset breakdowns by type
- Operational metrics: `AverageAccountSize`, `OwnershipType`, `Licenses`

**Size**: Variable (contains firm-level information)

---

## 2. Data Merging Process

### 2.1 Merge Operations

The data merging follows this sequence:

1. **Salesforce ↔ Discovery Rep Merge**: Links Salesforce leads to rep records via `FA_CRD__c` → `RepCRD`
   - Result: `data_sf_rep`

2. **Salesforce+Rep ↔ Firm Merge**: Links the combined SF+Rep data to firm records via `RIAFirmCRD`
   - Result: `data_sf_rep_firm` (final merged dataset)

3. **Column Cleaning**: Uses `ColumnCleaner` class to standardize merged columns
   - Handles naming conflicts, data type conversions, and duplicate column resolution

### 2.2 Merge Statistics

- **Total Salesforce Records**: 69,809
- **Matched with Rep**: 75,966 (108.8% - indicates multiple rep matches per SF record)
- **Matched with Rep + Firm**: 75,966 (108.8%)
- **No matches**: 14,228 (20.4%)

---

## 3. Feature Engineering

### 3.1 Initial Feature Selection

The model starts with **31 base features** from the merged dataset:

**Rep Characteristics**:
- `NumberFirmAssociations`: Number of firm associations
- `NumberRIAFirmAssociations`: Number of RIA firm associations
- `IsPrimaryRIAFirm`: Boolean indicating primary RIA firm
- `DuallyRegisteredBDRIARep`: Boolean for dual registration status
- `KnownNonAdvisor`: Boolean flag
- `DateBecameRep_NumberOfYears`: Years since becoming a rep
- `DateOfHireAtCurrentFirm_NumberOfYears`: Years at current firm
- `Number_YearsPriorFirm1` through `Number_YearsPriorFirm4`: Tenure at prior firms

**Firm Characteristics**:
- `Number_Employees`: Firm employee count
- `Number_BranchAdvisors`: Number of branch advisors
- `Number_IAReps`: Number of IA representatives
- `TotalAssetsInMillions`: Total assets under management
- `Number_InvestmentAdvisoryClients`: Count of advisory clients
- `OwnershipType`: Ownership structure

**Asset and Client Metrics**:
- `NumberClients_HNWIndividuals`: High net worth individual clients
- `NumberClients_Individuals`: Total individual clients
- `AssetsInMillions_HNWIndividuals`: HNW client assets
- `AssetsInMillions_Individuals`: Individual client assets
- `AssetsInMillions_MutualFunds`: Mutual fund assets
- `AssetsInMillions_PrivateFunds`: Private fund assets
- `AverageAccountSize`: Average account size
- `PercentClients_Individuals`: Percentage of individual clients
- `Percent_ClientsUS`: Percentage of US-based clients

**Growth Metrics**:
- `AUMGrowthRate_5Year`: 5-year AUM growth rate
- `AUMGrowthRate_1Year`: 1-year AUM growth rate

**Geographic**:
- `Home_MetropolitanArea`: Metropolitan area (categorical)
- `MilesToWork`: Commute distance

### 3.2 Basic Feature Transformations

The `FeatureEngineer` class performs initial transformations:

1. **Boolean Conversions**:
   - `DuallyRegisteredBDRIARep` → `IsDuallyRegistered`
   - `OwnershipType` → `IsIndependent`
   - `IsPrimaryRIAFirm` → boolean
   - `KnownNonAdvisor` → boolean

2. **Data Type Conversions**:
   - Numeric fields: `Number_InvestmentAdvisoryClients`, `Number_Employees`, `Percent_ClientsUS`
   - Datetime fields: `ConvertedDate`, `CreatedDate`, `Stage_Entered_Call_Scheduled__c`

3. **Geographic Encoding**:
   - Creates 5 dummy variables for major metropolitan areas:
     - Chicago-Naperville-Elgin IL-IN
     - Dallas-Fort Worth-Arlington TX
     - Los Angeles-Long Beach-Anaheim CA
     - Miami-Fort Lauderdale-West Palm Beach FL
     - New York-Newark-Jersey City NY-NJ

4. **Tenure Aggregations**:
   - `AverageTenureAtPriorFirms`: Average tenure across prior firms
   - `NumberOfPriorFirms`: Count of prior firms with tenure data

5. **Target Variable Creation**:
   - `EverCalled`: Boolean indicating if lead was ever called (based on `Stage_Entered_Call_Scheduled__c` not null)

### 3.3 Advanced Feature Engineering

The `create_advanced_features()` function creates **31 additional engineered features**:

#### Efficiency Metrics (3 features):
- `AUM_per_Client`: TotalAssetsInMillions / Number_InvestmentAdvisoryClients
- `AUM_per_Employee`: TotalAssetsInMillions / Number_Employees
- `AUM_per_IARep`: TotalAssetsInMillions / Number_IAReps

#### Growth Indicators (2 features):
- `Growth_Momentum`: AUMGrowthRate_1Year × AUMGrowthRate_5Year
- `Growth_Acceleration`: AUMGrowthRate_1Year - (AUMGrowthRate_5Year / 5)

#### Stability Scores (2 features):
- `Firm_Stability_Score`: DateOfHireAtCurrentFirm_NumberOfYears / (NumberOfPriorFirms + 1)
- `Experience_Efficiency`: TotalAssetsInMillions / (DateBecameRep_NumberOfYears + 1)

#### Client Composition (2 features):
- `HNW_Client_Ratio`: NumberClients_HNWIndividuals / NumberClients_Individuals
- `HNW_Asset_Concentration`: AssetsInMillions_HNWIndividuals / TotalAssetsInMillions

#### Client Focus (2 features):
- `Individual_Asset_Ratio`: AssetsInMillions_Individuals / TotalAssetsInMillions
- `Alternative_Investment_Focus`: (AssetsInMillions_MutualFunds + AssetsInMillions_PrivateFunds) / TotalAssetsInMillions

#### Scale Indicators (3 features):
- `Is_Large_Firm`: Boolean (Number_Employees > 100)
- `Is_Boutique_Firm`: Boolean (Employees ≤ 20 AND AverageAccountSize > 75th percentile)
- `Has_Scale`: Boolean (TotalAssetsInMillions > 500 OR Number_InvestmentAdvisoryClients > 100)

#### Advisor Tenure Patterns (3 features):
- `Is_New_To_Firm`: Boolean (DateOfHireAtCurrentFirm_NumberOfYears < 2)
- `Is_Veteran_Advisor`: Boolean (DateBecameRep_NumberOfYears > 10)
- `High_Turnover_Flag`: Boolean (NumberOfPriorFirms > 3 AND AverageTenureAtPriorFirms < 3)

#### Market Positioning (2 features):
- `Premium_Positioning`: Boolean (AverageAccountSize > 75th percentile AND PercentClients_Individuals < 50)
- `Mass_Market_Focus`: Boolean (PercentClients_Individuals > 80 AND AverageAccountSize < median)

#### Operational Efficiency (3 features):
- `Clients_per_Employee`: Number_InvestmentAdvisoryClients / Number_Employees
- `Branch_Advisor_Density`: Number_BranchAdvisors / Number_Employees
- `Clients_per_IARep`: Number_InvestmentAdvisoryClients / Number_IAReps

#### Geographic Factors (2 features):
- `Remote_Work_Indicator`: Boolean (MilesToWork > 50)
- `Local_Advisor`: Boolean (MilesToWork ≤ 10)

#### Firm Relationships (2 features):
- `Multi_RIA_Relationships`: Boolean (NumberRIAFirmAssociations > 1)
- `Complex_Registration`: Boolean (NumberFirmAssociations > 2 OR NumberRIAFirmAssociations > 1)

#### Client Geography (2 features):
- `Primarily_US_Clients`: Boolean (Percent_ClientsUS > 90)
- `International_Presence`: Boolean (Percent_ClientsUS < 80)

#### Composite Scores (2 features):
- `Quality_Score`: Weighted composite (0.25 × Is_Veteran_Advisor + 0.25 × Has_Scale + 0.15 × Firm_Stability + 0.15 × IsPrimaryRIAFirm + 0.10 × AUM_per_Client_above_median + 0.10 × (1 - High_Turnover_Flag))
- `Positive_Growth_Trajectory`: Boolean (both growth rates > 0)
- `Accelerating_Growth`: Boolean (1-year growth > 5-year average)

### 3.4 Final Feature Set

**Total Features**: 67
- **Base features**: 31
- **Metropolitan area dummies**: 5
- **Engineered features**: 31

**Dummy/Boolean Features** (not scaled): 24 features including all metropolitan dummies and boolean flags

---

## 4. Training Data Preparation

### 4.1 Data Eligibility

**Labeled Data Criteria**: Records must have all three identifiers:
- `FA_CRD__c` not null (Salesforce lead ID)
- `RepCRD` not null (Discovery rep ID)
- `RIAFirmCRD` not null (Firm ID)

**Deduplication**: Remove duplicates based on `FA_CRD__c` to ensure one record per lead.

### 4.2 Train-Test Split

- **Split Ratio**: 80/20 (training/test)
- **Random State**: 42 (for reproducibility)
- **Stratification**: Yes (preserves class distribution)
- **Training Set**: 60,772 records
- **Test Set**: 15,194 records

### 4.3 Class Distribution

- **Positive Class Ratio**: 3.36%
- **Negative Class Ratio**: 96.64%
- **Class Imbalance Handling**: 
  - Positive class weight: 28.7 (calculated as negative_count / positive_count)
  - SMOTE oversampling (see Model Architecture)

---

## 5. Model Architecture

### 5.1 Model Pipeline

The model uses an `imblearn.Pipeline` with the following stages:

#### Stage 1: Feature Selection
- `ColumnTransformer` with passthrough for all 67 features

#### Stage 2: Scaling
- `ColumnTransformer` with conditional scaling:
  - **Scaled**: All numeric features (43 features)
  - **Passthrough**: All dummy/boolean features (24 features)
- `StandardScaler`: Standardizes numeric features (mean=0, std=1)

#### Stage 3: Imputation
- `IterativeImputer`: 
  - Max iterations: 25
  - Random state: 42
  - Initial strategy: 'median'
  - Uses other features to predict missing values

#### Stage 4: Oversampling
- `SMOTE` (Synthetic Minority Oversampling Technique):
  - Sampling strategy: 0.1 (brings minority class to 10% of majority)
  - K-neighbors: 5
  - Random state: 42

#### Stage 5: Classification
- `XGBClassifier` (XGBoost Gradient Boosting):
  - **Tree Parameters**:
    - `n_estimators`: 600 (number of boosting rounds)
    - `max_depth`: 6 (maximum tree depth)
    - `min_child_weight`: 2 (minimum sum of instance weight in child)
  
  - **Sampling Parameters**:
    - `subsample`: 0.8 (80% row sampling)
    - `colsample_bytree`: 0.7 (70% column sampling per tree)
    - `colsample_bylevel`: 0.7 (70% column sampling per level)
  
  - **Learning Parameters**:
    - `learning_rate`: 0.015 (shrinkage rate)
    - `scale_pos_weight`: 28.7 (handles class imbalance)
  
  - **Regularization**:
    - `reg_alpha`: 0.5 (L1 regularization)
    - `reg_lambda`: 2.0 (L2 regularization)
    - `gamma`: 2 (minimum loss reduction for split)
  
  - **Objective & Metrics**:
    - `objective`: 'binary:logistic'
    - `eval_metric`: ['aucpr', 'map'] (Area Under Precision-Recall Curve, Mean Average Precision)
  
  - **Performance**:
    - `random_state`: 42
    - `n_jobs`: -1 (use all cores)
    - `tree_method`: 'hist' (histogram-based algorithm)

### 5.2 Model Calibration

A **calibrated version** is created using `CalibratedClassifierCV`:
- **Base Model**: The trained m5 pipeline
- **Method**: 'sigmoid' (Platt scaling)
- **Cross-Validation**: 3-fold CV
- **Purpose**: Improves probability calibration for better probability estimates

**Final Model Used**: `m5_calibrated` (calibrated version used for scoring)

---

## 6. Model Performance

### 6.1 Evaluation Metrics

**m5_calibrated Performance** (on test set):

- **Average Precision**: 0.1435
- **ROC AUC**: 0.7910
- **Top 20% Precision**: 0.1001
- **Top 20% Lift**: 2.98x (vs. baseline rate of 3.36%)
- **Top 10% Precision**: 0.1317
- **Top 10% Lift**: 3.91x (vs. baseline rate of 3.36%)

### 6.2 Top 25 Most Important Features

1. `Multi_RIA_Relationships` (0.0816)
2. `Mass_Market_Focus` (0.0708)
3. `HNW_Asset_Concentration` (0.0587)
4. `DateBecameRep_NumberOfYears` (0.0379)
5. `Branch_Advisor_Density` (0.0240)
6. `Is_Veteran_Advisor` (0.0225)
7. `NumberFirmAssociations` (0.0220)
8. `Firm_Stability_Score` (0.0211)
9. `AverageAccountSize` (0.0208)
10. `Individual_Asset_Ratio` (0.0197)
11. `Home_MetropolitanArea_Dallas-Fort Worth-Arlington TX` (0.0192)
12. `Percent_ClientsUS` (0.0170)
13. `Number_Employees` (0.0165)
14. `Number_InvestmentAdvisoryClients` (0.0163)
15. `Clients_per_Employee` (0.0161)
16. `Clients_per_IARep` (0.0157)
17. `AssetsInMillions_Individuals` (0.0152)
18. `Complex_Registration` (0.0152)
19. `NumberClients_Individuals` (0.0150)
20. `NumberClients_HNWIndividuals` (0.0143)
21. `PercentClients_Individuals` (0.0135)
22. `Remote_Work_Indicator` (0.0131)
23. `Is_New_To_Firm` (0.0130)
24. `Primarily_US_Clients` (0.0130)
25. `Accelerating_Growth` (0.0128)

---

## 7. Scoring Process

### 7.1 Scoring Pipeline

1. **Input Data**: All records from `model_data_m5` (includes both labeled and unlabeled)
2. **Feature Extraction**: Extract 67 features for each record
3. **Model Prediction**: Apply `m5_calibrated.predict_proba()` to get probability scores
4. **Score Assignment**: Assign `Score_m5` (probability between 0 and 1)

### 7.2 Score Buckets

Scores are categorized into 5 buckets:

| Bucket | Score Range | Count | Action Recommended |
|--------|-------------|-------|-------------------|
| **Cold** | 0.00 - 0.02 | 270,859 | Do Not Contact |
| **Cool** | 0.02 - 0.05 | 118,597 | Nurture Campaign |
| **Warm** | 0.05 - 0.10 | 77,802 | Contact This Month |
| **Hot** | 0.10 - 0.20 | 42,490 | Contact This Week |
| **Very Hot** | 0.20 - 1.00 | 103 | Immediate Outreach - High Priority |

### 7.3 Additional Output Fields

- **Score_Percentile**: Percentile rank of the score (0-100)
- **Action_Recommended**: Action based on score bucket
- **Was_Scored**: Boolean indicating if record was successfully scored
- **Scoring_Date**: Timestamp of when scoring was performed

### 7.4 Output Statistics

- **Total Records Scored**: 509,851
- **Successfully Scored**: 509,851 (100%)
- **Not Scored**: 0

---

## 8. Output Format

### 8.1 Final Output Schema

The final output (`final_output.csv`) contains:

**Identification Fields**:
- `RepCRD`: Representative CRD number
- `RIAFirmCRD`: RIA Firm CRD number
- `FA_CRD__c`: Financial Advisor CRD from Salesforce

**Scoring Fields**:
- `Score_m5`: Raw probability score (0-1)
- `Score_Bucket`: Categorical bucket (Cold, Cool, Warm, Hot, Very Hot)
- `Score_Percentile`: Percentile rank (0-100)
- `Action_Recommended`: Recommended action based on bucket

**Metadata Fields**:
- `Was_Scored`: Boolean flag
- `Scoring_Date`: Timestamp

**All Original Fields**: All columns from the original `data_sf_rep_firm` dataset are preserved

### 8.2 Merge Back to Original Data

The scoring output is merged back to the original `data_sf_rep_firm` dataset using:
- Join keys: `['RepCRD', 'RIAFirmCRD', 'FA_CRD__c']`
- Join type: Left join (preserves all original records)
- Deduplication: Removes duplicate combinations before merging

---

## 9. Model Dependencies

### 9.1 Python Libraries

- `pandas`: Data manipulation
- `numpy`: Numerical operations
- `scikit-learn`: Machine learning utilities (StandardScaler, IterativeImputer, train_test_split, CalibratedClassifierCV)
- `xgboost`: XGBoost classifier
- `imbalanced-learn`: SMOTE and pipeline utilities
- `dataload_functions`: Custom data loading functions
- `column_cleaning_functions`: ColumnCleaner class
- `feature_engineering_functions`: FeatureEngineer class
- `model_visualizer`: ModelEvaluationVisualizer class (for evaluation)

### 9.2 Data Dependencies

- `data/sf_leads.pkl`: Salesforce lead data (must be refreshed periodically)
- `data/discovery_data.pkl`: Discovery rep data (created from raw Discovery data)
- `data/FirmData.csv`: Firm-level data

### 9.3 Model Artifacts

- Trained `m5_calibrated` model pipeline (includes all preprocessing steps)
- Feature list (`m5_features`: 67 features)
- Dummy feature list (`dummy_features_m5`: 24 features)

---

## 10. Model Retraining

### 10.1 When to Retrain

The model should be retrained when:
- Significant changes in lead characteristics or distributions
- New data becomes available that could improve predictions
- Model performance degrades over time (drift detection)
- Business objectives or target variable definition changes

### 10.2 Retraining Process

1. Refresh Salesforce leads via query
2. Regenerate Discovery data PKL from raw data
3. Run merge operations
4. Apply feature engineering
5. Split into train/test sets
6. Train model pipeline
7. Calibrate model
8. Evaluate performance
9. Compare with previous model version
10. Deploy if performance is acceptable

---

## 11. Limitations and Considerations

### 11.1 Data Quality Dependencies

- Model requires all three identifiers (`FA_CRD__c`, `RepCRD`, `RIAFirmCRD`) for training
- Missing matches between data sources result in unlabeled records (cannot be used for training)
- Data freshness: Salesforce and Discovery data should be refreshed regularly

### 11.2 Class Imbalance

- Highly imbalanced dataset (3.36% positive class)
- Model uses SMOTE and class weights to handle imbalance
- Precision at 0.5 threshold may be low; focus on top percentile metrics for business decisions

### 11.3 Feature Engineering

- Many engineered features rely on ratios and divisions (risk of division by zero handled with `.replace(0, np.nan)`)
- Some features use quantiles calculated on training data (these should be stored and reused during scoring)

### 11.4 Model Interpretability

- XGBoost provides feature importance but is a black-box model
- SHAP values could be calculated for deeper interpretability if needed

---

## 12. Future Improvements

### 12.1 Potential Enhancements

1. **Feature Engineering**:
   - Incorporate time-based features (seasonality, recency)
   - Add interaction terms between top features
   - Include text features from lead descriptions

2. **Model Architecture**:
   - Experiment with ensemble methods
   - Try alternative algorithms (LightGBM, CatBoost)
   - Implement automated hyperparameter tuning

3. **Data**:
   - Incorporate additional external data sources
   - Add lead interaction history
   - Include firm-level market data

4. **Evaluation**:
   - Implement model monitoring and drift detection
   - Add business-specific evaluation metrics (ROI, conversion value)
   - Create A/B testing framework

---

## Appendix A: Feature List

### Base Features (31)
1. NumberFirmAssociations
2. TotalAssetsInMillions
3. NumberRIAFirmAssociations
4. IsPrimaryRIAFirm
5. Number_Employees
6. Number_BranchAdvisors
7. DateBecameRep_NumberOfYears
8. DateOfHireAtCurrentFirm_NumberOfYears
9. Number_InvestmentAdvisoryClients
10. KnownNonAdvisor
11. Number_YearsPriorFirm1
12. Number_YearsPriorFirm2
13. Number_YearsPriorFirm3
14. Number_YearsPriorFirm4
15. MilesToWork
16. Number_IAReps
17. NumberClients_HNWIndividuals
18. NumberClients_Individuals
19. AssetsInMillions_HNWIndividuals
20. AssetsInMillions_Individuals
21. AssetsInMillions_MutualFunds
22. AssetsInMillions_PrivateFunds
23. AUMGrowthRate_5Year
24. AUMGrowthRate_1Year
25. AverageAccountSize
26. PercentClients_Individuals
27. Percent_ClientsUS
28. IsDuallyRegistered
29. IsIndependent
30. AverageTenureAtPriorFirms
31. NumberOfPriorFirms

### Metropolitan Area Dummies (5)
1. Home_MetropolitanArea_Chicago-Naperville-Elgin IL-IN
2. Home_MetropolitanArea_Dallas-Fort Worth-Arlington TX
3. Home_MetropolitanArea_Los Angeles-Long Beach-Anaheim CA
4. Home_MetropolitanArea_Miami-Fort Lauderdale-West Palm Beach FL
5. Home_MetropolitanArea_New York-Newark-Jersey City NY-NJ

### Engineered Features (31)
1. AUM_per_Client
2. AUM_per_Employee
3. AUM_per_IARep
4. Growth_Momentum
5. Growth_Acceleration
6. Firm_Stability_Score
7. Experience_Efficiency
8. HNW_Client_Ratio
9. HNW_Asset_Concentration
10. Individual_Asset_Ratio
11. Alternative_Investment_Focus
12. Is_Large_Firm
13. Is_Boutique_Firm
14. Has_Scale
15. Is_New_To_Firm
16. Is_Veteran_Advisor
17. High_Turnover_Flag
18. Premium_Positioning
19. Mass_Market_Focus
20. Clients_per_Employee
21. Branch_Advisor_Density
22. Clients_per_IARep
23. Remote_Work_Indicator
24. Local_Advisor
25. Multi_RIA_Relationships
26. Complex_Registration
27. Primarily_US_Clients
28. International_Presence
29. Quality_Score
30. Positive_Growth_Trajectory
31. Accelerating_Growth

---

## Document Version

**Version**: 1.0  
**Last Updated**: Based on FinalLeadScorePipeline.ipynb  
**Author**: Model Development Team

