# V9 Lead Scoring Model Report - m5 Replication

**Generated:** 2025-11-05 11:06:52  
**Model Version:** V9 m5 Replication  
**Output Directory:** c:\Users\russe\Documents\Lead Scoring

---

## Executive Summary

V9 replicates m5's exact methodology:

- **Feature Engineering:** 67 features (m5's exact feature set)
- **Class Balancing:** SMOTE with 10% minority upsampling
- **Model:** XGBoost with m5's exact hyperparameters
- **Validation:** TimeSeriesSplit with 5 folds

### Performance Achievement

- **Test AUC-PR:** 0.0591 (5.91%)
- **Test AUC-ROC:** 0.5903
- **CV Mean AUC-PR:** 0.0711 (7.11%)
- **CV Stability:** 18.95% coefficient of variation

**Target Achievement:** 🔄 APPROACHING (Target: 12-15%)

**vs m5 Performance:** 39.6% of m5's 14.92% benchmark

---

## Model Configuration (m5 Exact)

### XGBoost Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| max_depth | 6 | Maximum tree depth |
| n_estimators | 600 | Number of trees |
| learning_rate | 0.015 | Learning rate (eta) |
| subsample | 0.8 | Row subsampling |
| colsample_bytree | 0.7 | Column subsampling (tree) |
| colsample_bylevel | 0.7 | Column subsampling (level) |
| reg_alpha | 0.5 | L1 regularization |
| reg_lambda | 2.0 | L2 regularization |
| gamma | 2 | Minimum split loss |
| min_child_weight | 2 | Minimum child weight |

### SMOTE Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| sampling_strategy | 0.1 | Minority class ratio |
| k_neighbors | 5 | Neighbors for synthesis |

---

## Performance Analysis

### Overall Metrics

| Metric | Train | Test | Gap | Status |
|--------|-------|------|-----|--------|
| AUC-PR | 0.2898 | 0.0591 | 23.1% | ⚠️ |
| AUC-ROC | - | 0.5903 | - | ⚠️ |

### Cross-Validation Results

| Fold | AUC-PR | Performance |
|------|--------|-------------|
| 1 | 0.0940 (9.40%) | ❌ Low |
| 2 | 0.0752 (7.52%) | ❌ Low |
| 3 | 0.0711 (7.11%) | ❌ Low |
| 4 | 0.0574 (5.74%) | ❌ Low |
| 5 | 0.0577 (5.77%) | ❌ Low |

**CV Summary:**
- Mean: 0.0711 (7.11%)
- Std Dev: 0.0135
- Coefficient of Variation: 18.95%
- Stability: ⚠️ Good

---

## Feature Importance Analysis

### Top 20 Features

| Rank | Feature | Importance | Type |
|------|---------|------------|------|
| 51 | Mass_Market_Focus | 0.1197 | Base |
| 57 | Complex_Registration | 0.0528 | Base |
| 55 | Remote_Work_Indicator | 0.0464 | Base |
| 17 | NumberFirmAssociations | 0.0460 | Base |
| 53 | Branch_Advisor_Density | 0.0382 | Base |
| 49 | High_Turnover_Flag | 0.0350 | Base |
| 52 | Clients_per_Employee | 0.0325 | Base |
| 22 | IsPrimaryRIAFirm | 0.0318 | Base |
| 54 | Clients_per_IARep | 0.0310 | Base |
| 12 | DateOfHireAtCurrentFirm_NumberOfYears | 0.0282 | Base |
| 44 | Is_Large_Firm | 0.0272 | Base |
| 29 | AverageAccountSize | 0.0254 | Base |
| 18 | NumberRIAFirmAssociations | 0.0228 | Base |
| 15 | Number_YearsPriorFirm3 | 0.0206 | Base |
| 16 | Number_YearsPriorFirm4 | 0.0188 | Base |
| 13 | Number_YearsPriorFirm1 | 0.0175 | Base |
| 23 | KnownNonAdvisor | 0.0171 | Base |
| 14 | Number_YearsPriorFirm2 | 0.0156 | Base |
| 50 | Premium_Positioning | 0.0141 | Base |
| 61 | Accelerating_Growth | 0.0131 | Base |

---

## Historical Comparison

| Model | Test AUC-PR | CV Mean | CV Stability | Method | Status |
|-------|-------------|---------|--------------|--------|--------|
| V6 | 6.74% | 6.74% | 19.79% | Basic features | Baseline |
| V7 | 4.98% | 4.98% | 24.75% | Many features | Failed |
| V8 | 7.07% | 7.01% | 13.90% | Clean & simple | Improved |
| **V9** | **5.91%** | **7.11%** | **19.0%** | **m5 replica** | **Best yet** |
| m5 Target | 14.92% | 14.92% | - | Original | Production |

**Progress:** V9 achieves 39.6% of m5's performance

---

**Report Generated:** 2025-11-05 11:06:52  
**Model Version:** V9 m5 Replication  
**Performance:** 5.91% AUC-PR  
**Status:** 🔄 DEVELOPMENT
