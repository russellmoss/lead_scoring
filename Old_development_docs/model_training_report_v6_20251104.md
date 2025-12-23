# V6 Model Training Report

**Generated:** 2025-11-04 22:41:16
**Version:** 20251104

## Dataset Summary

- **Total Samples:** 41,942
- **Positive Class:** 1,422 (3.39%)
- **Negative Class:** 40,520 (96.61%)
- **Features:** 111
- **CV Folds:** 5

## Cross-Validation Results

- **Mean AUC-PR:** 0.0588 ± 0.0014
- **CV Coefficient:** 2.36%
- **Winning Strategy:** scale_pos_weight
- **Strategy Wins:** SMOTE=0, scale_pos_weight=5
- **Fold Details:**
  - Fold 1 (scale_pos_weight): AUC-PR=0.0594, AUC-ROC=0.6257
  - Fold 2 (scale_pos_weight): AUC-PR=0.0600, AUC-ROC=0.6293
  - Fold 3 (scale_pos_weight): AUC-PR=0.0601, AUC-ROC=0.6332
  - Fold 4 (scale_pos_weight): AUC-PR=0.0579, AUC-ROC=0.6410
  - Fold 5 (scale_pos_weight): AUC-PR=0.0565, AUC-ROC=0.6224

## Model Configuration

- **XGBoost Parameters:**
  - n_estimators: 200
  - max_depth: 4
  - learning_rate: 0.02
  - subsample: 0.7
  - colsample_bytree: 0.7
  - reg_alpha: 1.0
  - reg_lambda: 5.0
  - scale_pos_weight: 28.50 (used if scale_pos_weight strategy)
  - **Imbalance Strategy:** scale_pos_weight

## Top 20 Features

Home_MetropolitanArea: 0.054305
multi_state_registered: 0.049732
Firm_Stability_Score: 0.047531
DateOfHireAtCurrentFirm_NumberOfYears: 0.040981
Is_BreakawayRep: 0.033914
DuallyRegisteredBDRIARep: 0.029617
Branch_State: 0.028380
Home_State: 0.028061
is_new_to_firm: 0.027213
Is_IndependentContractor: 0.026641
total_reps: 0.025419
multi_state_firm: 0.023786
Branch_Advisors_per_Firm_Association: 0.023294
national_firm: 0.023010
avg_prior_firm_tenure_lt3: 0.022034
AverageTenureAtPriorFirms: 0.021387
Number_RegisteredStates: 0.021278
Has_Series_7: 0.020130
branch_vs_home_mismatch: 0.019957
Has_Series_24: 0.017711

## Artifacts Saved

- Model: `model_v6_20251104.pkl`
- Baseline: `model_v6_20251104_baseline_logit.pkl`
- Feature Order: `feature_order_v6_20251104.json`
- Feature Importance: `feature_importance_v6_20251104.csv`

## Validation Gates

- **CV AUC-PR > 0.15:** FAIL (0.0588)
- **CV Coefficient < 20%:** PASS (2.36%)
