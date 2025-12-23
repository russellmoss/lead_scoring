# V6 with Financials Model Training Report

**Generated:** 2025-11-04 23:04:36
**Version:** 20251104

## Dataset Summary

- **Total Samples:** 43,269
- **Positive Class:** 1,466 (3.39%)
- **Negative Class:** 41,803 (96.61%)
- **Features:** 115
- **CV Folds:** 5

## Cross-Validation Results

- **Mean AUC-PR:** 0.0674 ± 0.0133
- **CV Coefficient:** 19.79%
- **Winning Strategy:** scale_pos_weight
- **Strategy Wins:** SMOTE=0, scale_pos_weight=5
- **Fold Details:**
  - Fold 1 (scale_pos_weight): AUC-PR=0.0608, AUC-ROC=0.6299
  - Fold 2 (scale_pos_weight): AUC-PR=0.0641, AUC-ROC=0.6308
  - Fold 3 (scale_pos_weight): AUC-PR=0.0893, AUC-ROC=0.6821
  - Fold 4 (scale_pos_weight): AUC-PR=0.0683, AUC-ROC=0.6527
  - Fold 5 (scale_pos_weight): AUC-PR=0.0542, AUC-ROC=0.6311

## Model Configuration

- **XGBoost Parameters:**
  - n_estimators: 200
  - max_depth: 4
  - learning_rate: 0.02
  - subsample: 0.7
  - colsample_bytree: 0.7
  - reg_alpha: 1.0
  - reg_lambda: 5.0
  - scale_pos_weight: 28.52 (used if scale_pos_weight strategy)
  - **Imbalance Strategy:** scale_pos_weight

## Top 20 Features

AssetsInMillions_Individuals: 0.038684
Firm_Stability_Score: 0.037078
Home_MetropolitanArea: 0.031474
DateOfHireAtCurrentFirm_NumberOfYears: 0.028188
NumberClients_RetirementPlans: 0.028124
Is_BreakawayRep: 0.027002
Accelerating_Growth: 0.026580
AssetsInMillions_Equity_ExchangeTraded: 0.026468
TotalAssets_SeparatelyManagedAccounts: 0.021295
AssetsInMillions_MutualFunds: 0.019860
Home_State: 0.019500
high_turnover_flag: 0.019437
Branch_State: 0.018854
Is_IndependentContractor: 0.017270
AssetsInMillions_PrivateFunds: 0.016492
Home_USPS_Certified: 0.015895
Clients_per_IARep: 0.015600
TotalAssetsInMillions: 0.015324
AUM_per_IARep: 0.015130
branch_vs_home_mismatch: 0.014336

## Artifacts Saved

- Model: `model_v6_with_financials_20251104.pkl`
- Baseline: `model_v6_with_financials_20251104_baseline_logit.pkl`
- Feature Order: `feature_order_v6_with_financials_20251104.json`
- Feature Importance: `feature_importance_v6_with_financials_20251104.csv`

## Validation Gates

- **CV AUC-PR > 0.15:** FAIL (0.0674)
- **CV Coefficient < 20%:** PASS (19.79%)
