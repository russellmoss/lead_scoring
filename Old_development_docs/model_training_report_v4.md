# Model Training Report V1

**Generated:** 2025-11-03 19:33:02

## Summary

- **Winning Imbalance Strategy:** spw
- **Final Features Used:** 120
- **Training Samples:** 43,854
- **Positive Samples:** 1,399 (3.19%)
- **Negative Samples:** 42,455 (96.81%)

## Final Model Performance

### XGBoost (Final Model)

- **AUC-PR:** 1.0000
- **AUC-ROC:** 1.0000

### Logistic Regression (Baseline)

- **AUC-PR:** 0.0415
- **AUC-ROC:** 0.5551

## Cross-Validation Results

### Strategy Comparison by Fold

|   fold |   train_size |   test_size |   features_kept |   smote_aucpr |   spw_aucpr | best_strategy   |   best_aucpr |
|-------:|-------------:|------------:|----------------:|--------------:|------------:|:----------------|-------------:|
|      0 |         5743 |        8770 |             120 |     0.0857905 |   0.0857905 | spw             |    0.0857905 |
|      1 |        13506 |        8770 |             120 |     0.138941  |   0.138941  | spw             |    0.138941  |
|      2 |        24185 |        8770 |             120 |     0.198264  |   0.198264  | spw             |    0.198264  |
|      3 |        33375 |        8770 |             120 |     0.228448  |   0.228448  | spw             |    0.228448  |

## SMOTE vs Scale_Pos_Weight Analysis

- **Average SMOTE AUC-PR:** 0.1629
- **Average Scale_Pos_Weight AUC-PR:** 0.1629
- **Winning Strategy:** spw (Scale_Pos_Weight)
