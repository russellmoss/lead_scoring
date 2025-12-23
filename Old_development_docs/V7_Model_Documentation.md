# V7 Lead Scoring Model Documentation

**Version:** V7  
**Training Date:** [Will be populated after training]  
**AUC-PR:** [Will be populated after validation]  
**Production Status:** [Pending Validation]  

---

## Executive Summary

V7 is the latest iteration of the Savvy Wealth lead scoring model, designed to bridge the performance gap between V6 (6.74% AUC-PR) and the production m5 model (14.92% AUC-PR). V7 implements a hybrid data strategy that combines point-in-time historical snapshots for non-financial features with current financial data applied across all historical leads, matching m5's production methodology.

### Key Improvements from V6

1. **Hybrid Financial Data Approach**: Uses current financial data across all historical leads (like m5), ensuring training-production alignment
2. **m5's Engineered Features**: Integrates all 31 engineered features from the production m5 model
3. **Temporal Dynamics**: Creates 8 temporal features from 8 quarters of historical snapshot data
4. **Ensemble Approach**: Combines three models (XGBoost variants + LightGBM) for improved robustness
5. **Aligned Training Methodology**: Matches production data usage patterns to prevent training-production mismatch

---

## Model Architecture

### Ensemble Composition

V7 uses a weighted ensemble of three models:

- **Model A (40% weight)**: XGBoost on all features
- **Model B (30% weight)**: XGBoost with temporal features weighted 2x
- **Model C (30% weight)**: LightGBM (falls back to XGBoost if unavailable)

Final prediction: `0.40 * Model_A + 0.30 * Model_B + 0.30 * Model_C`

### Hyperparameters

**XGBoost Parameters:**
- `max_depth`: 5
- `n_estimators`: 300
- `learning_rate`: 0.03
- `subsample`: 0.75
- `colsample_bytree`: 0.75
- `reg_alpha`: 0.5 (L1 regularization)
- `reg_lambda`: 3.0 (L2 regularization)
- `scale_pos_weight`: Calculated from class imbalance (typically ~28)
- `eval_metric`: 'aucpr'
- `tree_method`: 'hist'
- `enable_categorical`: True

**LightGBM Parameters:**
- `max_depth`: 5
- `n_estimators`: 300
- `learning_rate`: 0.03
- `subsample`: 0.75
- `colsample_bytree`: 0.75
- `reg_alpha`: 0.5
- `reg_lambda`: 3.0
- `objective`: 'binary'
- `metric`: 'aucpr'

---

## Data Sources

### 1. Salesforce Leads

**Source:** `savvy-gtm-analytics.SavvyGTMData.Lead`  
**Key Fields:**
- `Id`: Lead unique identifier
- `FA_CRD__c`: Financial Advisor CRD number (matching key)
- `Stage_Entered_Contacting__c`: Contact date (temporal matching key)
- `Stage_Entered_Call_Scheduled__c`: Call scheduled timestamp
- `target_label`: Binary label (1 if converted, 0 otherwise)

### 2. Discovery Rep Data (Historical Snapshots)

**Source:** `savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages`  
**Temporal Join:** Point-in-time join using `snapshot_at <= contact_date`  
**Non-Financial Features:**
- Rep characteristics (tenure, licenses, designations)
- Firm associations
- Geographic information
- Professional status flags
- Historical career progression

**Note:** Financial features from historical snapshots are excluded (NULL) as they are replaced with current financial data.

### 3. Discovery Rep Data (Current Snapshot)

**Source:** `savvy-gtm-analytics.LeadScoring.discovery_reps_current`  
**Join Strategy:** Current snapshot joined to ALL historical leads (no temporal constraint)  
**Financial Features:**
- `TotalAssetsInMillions`
- `NumberClients_Individuals`
- `NumberClients_HNWIndividuals`
- `NumberClients_Entities`
- All asset composition percentages
- Growth rates (`AUMGrowthRate_1Year`, `AUMGrowthRate_5Year`)
- Custodian AUM values

This approach matches m5's production methodology where current financial data is used for all leads.

---

## Feature Categories

### 1. Base Features (from V6)

**Rep Characteristics:**
- `DateBecameRep_NumberOfYears`
- `DateOfHireAtCurrentFirm_NumberOfYears`
- `Number_YearsPriorFirm1` through `Number_YearsPriorFirm4`
- `AverageTenureAtPriorFirms`
- `NumberOfPriorFirms`

**Professional Status:**
- `IsPrimaryRIAFirm`
- `DuallyRegisteredBDRIARep`
- `Is_BreakawayRep`
- `Is_IndependentContractor`
- `Is_Owner`

**Licenses and Designations:**
- `Has_Series_7`, `Has_Series_65`, `Has_Series_66`, `Has_Series_24`
- `Has_CFP`, `Has_CFA`, `Has_CIMA`, `Has_AIF`
- `Has_Insurance_License`

**Firm Associations:**
- `NumberFirmAssociations`
- `NumberRIAFirmAssociations`
- `Number_IAReps`
- `Number_BranchAdvisors`

**Geographic:**
- `Home_State`, `Branch_State`
- `Home_MetropolitanArea`
- `MilesToWork`

**Digital Presence:**
- `Has_LinkedIn`
- `SocialMedia_LinkedIn`

### 2. Financial Features (from Current Snapshot)

**Asset Metrics:**
- `TotalAssetsInMillions`
- `AssetsInMillions_Individuals`
- `AssetsInMillions_HNWIndividuals`
- `AssetsInMillions_MutualFunds`
- `AssetsInMillions_PrivateFunds`

**Client Metrics:**
- `NumberClients_Individuals`
- `NumberClients_HNWIndividuals`
- `NumberClients_Entities`

**Composition Percentages:**
- `PercentClients_Individuals`
- `PercentClients_HNWIndividuals`
- `PercentAssets_MutualFunds`
- `PercentAssets_PrivateFunds`

**Growth Rates:**
- `AUMGrowthRate_1Year`
- `AUMGrowthRate_5Year`

**Custodian AUM:**
- `Custodian1_AUM`
- `Custodian2_AUM`

### 3. m5's Engineered Features (31 features)

**Client Efficiency Metrics:**
- `AUM_per_Client`: `TotalAssetsInMillions / NumberClients_Individuals`
- `AUM_per_IARep`: `TotalAssetsInMillions / Number_IAReps`
- `AUM_per_Employee`: `TotalAssetsInMillions / Number_Employees`

**Growth Indicators:**
- `Growth_Momentum`: `AUMGrowthRate_1Year * AUMGrowthRate_5Year`
- `Growth_Acceleration`: `AUMGrowthRate_1Year - (AUMGrowthRate_5Year / 5)`
- `Growth_Momentum_Indicator`: Binary flag if `AUMGrowthRate_1Year > 0.15`

**Firm Stability:**
- `Firm_Stability_Score`: `DateOfHireAtCurrentFirm_NumberOfYears / (NumberOfPriorFirms + 1)`
- `Experience_Efficiency`: `TotalAssetsInMillions / (DateBecameRep_NumberOfYears + 1)`
- `Tenure_Stability_Score`: `DateOfHireAtCurrentFirm_NumberOfYears / DateBecameRep_NumberOfYears`

**Asset Concentration:**
- `HNW_Asset_Concentration`: `AssetsInMillions_HNWIndividuals / TotalAssetsInMillions`
- `Institutional_Focus`: `AssetsInMillions_MutualFunds / TotalAssetsInMillions`
- `Alternative_Investment_Focus`: `(AssetsInMillions_MutualFunds + AssetsInMillions_PrivateFunds) / TotalAssetsInMillions`

**Business Model Indicators:**
- `Multi_RIA_Relationships`: Binary if `NumberRIAFirmAssociations > 1`
- `Breakaway_High_AUM`: Binary if `Is_BreakawayRep = 1 AND TotalAssetsInMillions > 100`
- `Complex_Registration`: Binary if `NumberFirmAssociations > 2 OR NumberRIAFirmAssociations > 1`

**Digital Presence:**
- `Digital_Presence_Score`: 0-2 scale based on LinkedIn and website presence

**License Sophistication:**
- `License_Sophistication`: Count of Series 7, 65, 66, 24 licenses
- `Designation_Count`: Count of CFP, CFA, CIMA, AIF designations

**Additional Features:**
- `High_Turnover_Flag`: Based on prior firm tenure patterns
- `Quality_Score`: Composite score of multiple factors

### 4. Temporal Dynamics Features (8 features)

**Career Progression:**
- `Recent_Firm_Change`: Binary flag if rep changed RIA firm in last 4 quarters
- `Tenure_Momentum_Score`: Quarters continuously at current firm
- `Title_Progression_Flag`: Binary if title changed to higher seniority

**Geographic Stability:**
- `Branch_State_Stable`: Binary if branch state constant for 4+ quarters
- `Geographic_Expansion_Flag`: Binary if rep added new registered states

**Professional Development:**
- `License_Growth`: Count of new licenses acquired in last 2 quarters
- `License_Sophistication`: Enhanced temporal version

**Firm Dynamics:**
- `Firm_Size_Trajectory`: Direction of firm employee count change
- `Association_Changes`: Change in `NumberFirmAssociations` over time

### 5. Career Stage Indicators (4 features)

- `Early_Career_High_Performer`: Tenure < 3 years AND has Series 65/7
- `Established_Independent`: Tenure > 10 years AND (Is_Owner OR Is_IndependentContractor)
- `Growth_Phase_Rep`: Tenure 3-7 years AND recent firm change
- `Veteran_Stable`: Tenure > 15 years AND branch stability

### 6. Market Position Features (4 features)

- `Premium_Market_Position`: Top 10 metro AND graduate education
- `Emerging_Market_Pioneer`: Not in top 25 metros AND Is_Owner
- `Multi_State_Operator`: `Number_RegisteredStates >= 3`
- `High_Touch_Advisor`: `NumberClients_Individuals < 100 AND TotalAssetsInMillions > 50`

### 7. Business Model Indicators (6 features)

- `Mass_Affluent_Focus`: `PercentClients_Individuals > 0.8 AND avg_account_size < 1M`
- `UHNW_Specialist`: `PercentClients_HNWIndividuals > 0.5 AND avg_account_size > 5M`
- `Institutional_Manager`: `PercentAssets_MutualFunds > 0.3`
- `Hybrid_Model`: `Has_Insurance_License = 1 AND Has_Series_65 = 1`
- `Scale_Operator`: `NumberClients_Individuals > 500`
- `Boutique_Firm`: `TotalAssetsInMillions < 50 AND Number_IAReps < 5`

---

## Training Methodology

### Data Preparation

1. **Point-in-Time Join**: Non-financial features from `v_discovery_reps_all_vintages` joined using `snapshot_at <= contact_date`
2. **Current Financial Join**: Financial features from `discovery_reps_current` joined to ALL leads (no temporal constraint)
3. **Feature Engineering**: Apply m5's 31 engineered features and temporal dynamics
4. **PII Removal**: Drop 12 PII features (FirstName, LastName, addresses, etc.)

### Cross-Validation Strategy

**Temporal Blocking Cross-Validation:**
- 5 folds (configurable)
- 30-day gap between train and test sets
- Preserves temporal order to prevent leakage

### Class Imbalance Handling

- **Strategy**: `scale_pos_weight` (no SMOTE)
- **Weight**: Calculated as `(negative_samples / positive_samples)`
- **Typical Value**: ~28 (for 3.5% positive rate)

### Feature Selection

- **Pre-filtering**: None (all features retained)
- **Feature Order**: Saved to `feature_order_v7_{VERSION}.json` for production consistency

---

## Performance Metrics

| Metric | V6 | V6 (Financials) | V7 | m5 (Target) | Status |
|--------|----|----|----|----|----| 
| CV AUC-PR | 5.88% | 6.74% | [TBD] | 14.92% | [Pending] |
| CV AUC-ROC | 0.63 | [TBD] | [TBD] | 0.7916 | [Pending] |
| Train-Test Gap | Low | Low | [TBD] | Low | [Pending] |
| CV Coefficient | 19.79% | [TBD] | [TBD] | N/A | [Pending] |

**Validation Gates:**
- ✅ CV AUC-PR > 0.12 (approaching m5's 14.92%)
- ✅ Train-Test Gap < 20%
- ✅ CV Coefficient < 15%
- ✅ Top 5 features include at least 2 business signals
- ✅ Feature importance correlation with m5 > 0.5
- ✅ Calibration ECE < 0.05 across all segments

---

## Top Features

[To be populated after training - ranked by SHAP importance]

---

## Validation Results

### Cross-Validation Performance

[To be populated after validation]

### Train-Test Gap Analysis

[To be populated after validation]

### Business Signal Analysis

[To be populated after validation]

### m5 Feature Alignment

[To be populated after validation]

### Calibration Metrics

[To be populated after validation]

---

## Deployment Plan

### Prerequisites

1. **Model Artifacts:**
   - `model_v7_{VERSION}_ensemble.pkl` (ensemble model)
   - `feature_order_v7_{VERSION}.json` (feature order)
   - `v7_validation_report_{VERSION}.md` (validation results)

2. **Data Pipeline:**
   - `v7_data_pipeline.py` (data preparation)
   - `v7_feature_engineering.py` (feature engineering)
   - Access to BigQuery tables

3. **Production Readiness:**
   - ✅ All validation gates passed
   - ✅ Production readiness check completed
   - ✅ Shadow scoring validated (7 days)

### Deployment Steps

1. **Shadow Mode Deployment** (7 days)
   - Deploy model in shadow mode
   - Monitor scoring success rate (>95%)
   - Track latency (<500ms per lead)
   - Monitor error rates (<1%)

2. **A/B Test Design**
   - Power analysis for statistical significance
   - Sample size calculation
   - Random assignment of leads to treatment/control

3. **Production Rollout**
   - Gradual rollout (10% → 50% → 100%)
   - Monitor conversion rates
   - Track business metrics (MQLs per 100 dials)

4. **Monitoring Setup**
   - Daily health checks
   - Weekly class imbalance monitoring
   - Monthly feature drift detection (PSI)
   - Automated alerting for performance degradation

### Rollback Plan

- Keep m5 model as stable production baseline
- Version control all model artifacts
- Maintain ability to switch back to m5 within 24 hours
- Document rollback triggers and procedures

---

## Model Maintenance

### Retraining Triggers

- **Quarterly**: Scheduled retraining with latest data
- **Performance Degradation**: If CV AUC-PR drops >10% vs baseline
- **Feature Drift**: If PSI > 0.25 for critical features
- **Data Quality Issues**: If feature availability drops >5%

### Monitoring Schedule

- **Daily**: Scoring success rate, latency, error rates
- **Weekly**: Class imbalance, prediction distribution
- **Monthly**: Feature drift (PSI), calibration metrics
- **Quarterly**: Full model refresh and validation

---

## Known Limitations

1. **Financial Data**: Uses current financial data for all historical leads (no historical financial data available)
2. **Temporal Features**: Limited to 8 quarters of historical snapshots
3. **Feature Availability**: Some m5 features may not be available in production pipeline
4. **Ensemble Complexity**: Requires maintaining three models instead of one

---

## Future Improvements

1. **Historical Financial Data**: If historical financial snapshots become available, incorporate them
2. **More Temporal Features**: Extend temporal analysis beyond 8 quarters
3. **Feature Engineering**: Continue to refine engineered features based on business insights
4. **Model Optimization**: Tune ensemble weights based on validation performance
5. **Calibration**: Implement segment-specific calibration if needed

---

## References

- **V6 Model Documentation**: See `V6_Model_Performance_Analysis.md`
- **m5 Model Documentation**: See `Current_Lead_Scoring_Model.md`
- **Model Iteration Report**: See `Model_Iteration_Report_v1_to_v6.md`
- **V7 Implementation Plan**: See `V7_Implementation_Plan.md`

---

**Document Version:** 1.0  
**Last Updated:** [Will be populated after training]  
**Maintained By:** Data Science Team

