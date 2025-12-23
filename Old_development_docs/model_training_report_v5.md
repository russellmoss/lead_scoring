# Model Training Report V5

**Generated:** 2025-11-03 20:00:43

## Summary

- **Winning Imbalance Strategy:** spw
- **Final Features Used:** 120
- **Training Samples:** 43,854
- **Positive Samples:** 1,399 (3.19%)
- **Negative Samples:** 42,455 (96.81%)

## Final Model Performance

### XGBoost (Final Model)

- **AUC-PR:** 0.9582
- **AUC-ROC:** 0.9990

### Logistic Regression (Baseline)

- **AUC-PR:** 0.0415
- **AUC-ROC:** 0.5551

## Cross-Validation Results

### Strategy Comparison by Fold

|   fold |   train_size |   test_size |   features_kept |   smote_aucpr |   spw_aucpr | best_strategy   |   best_aucpr |
|-------:|-------------:|------------:|----------------:|--------------:|------------:|:----------------|-------------:|
|      0 |         5743 |        8770 |             120 |      0.051806 |   0.0857905 | spw             |    0.0857905 |
|      1 |        13506 |        8770 |             120 |      0.117777 |   0.138941  | spw             |    0.138941  |
|      2 |        24185 |        8770 |             120 |      0.162221 |   0.198264  | spw             |    0.198264  |
|      3 |        33375 |        8770 |             120 |      0.173921 |   0.228448  | spw             |    0.228448  |

## SMOTE vs Scale_Pos_Weight Analysis

- **Average SMOTE AUC-PR:** 0.1264
- **Average Scale_Pos_Weight AUC-PR:** 0.1629
- **Winning Strategy:** spw (Scale_Pos_Weight)
