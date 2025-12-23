# Model Training Report V1

**Generated:** 2025-11-03 16:35:26

## Summary

- **Winning Imbalance Strategy:** spw
- **Final Features Used:** 91
- **Training Samples:** 43,854
- **Positive Samples:** 1,399 (3.19%)
- **Negative Samples:** 42,455 (96.81%)

## Final Model Performance

### XGBoost (Final Model)

- **AUC-PR:** 1.0000
- **AUC-ROC:** 1.0000

### Logistic Regression (Baseline)

- **AUC-PR:** 0.0344
- **AUC-ROC:** 0.5288

## Cross-Validation Results

### Strategy Comparison by Fold

|   fold |   train_size |   test_size |   features_kept |   smote_aucpr |   spw_aucpr | best_strategy   |   best_aucpr |
|-------:|-------------:|------------:|----------------:|--------------:|------------:|:----------------|-------------:|
|      0 |         5743 |        8770 |              88 |     0.0841031 |   0.0841031 | spw             |    0.0841031 |
|      1 |        13506 |        8770 |              94 |     0.161951  |   0.161951  | spw             |    0.161951  |
|      2 |        24185 |        8770 |              95 |     0.195981  |   0.195981  | spw             |    0.195981  |
|      3 |        33375 |        8770 |              89 |     0.208941  |   0.208941  | spw             |    0.208941  |

## SMOTE vs Scale_Pos_Weight Analysis

- **Average SMOTE AUC-PR:** 0.1627
- **Average Scale_Pos_Weight AUC-PR:** 0.1627
- **Winning Strategy:** spw (Scale_Pos_Weight)
