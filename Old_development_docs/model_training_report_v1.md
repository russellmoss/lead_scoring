# Model Training Report V1

**Generated:** 2025-11-03 13:54:39

## Summary

- **Winning Imbalance Strategy:** spw
- **Final Features Used:** 106
- **Training Samples:** 44,592
- **Positive Samples:** 1,572 (3.53%)
- **Negative Samples:** 43,020 (96.47%)

## Final Model Performance

### XGBoost (Final Model)

- **AUC-PR:** 0.8536
- **AUC-ROC:** 0.9895

### Logistic Regression (Baseline)

- **AUC-PR:** 0.0488
- **AUC-ROC:** 0.5756

## Cross-Validation Results

### Strategy Comparison by Fold

|   fold |   train_size |   test_size |   features_kept |   smote_aucpr |   spw_aucpr | best_strategy   |   best_aucpr |
|-------:|-------------:|------------:|----------------:|--------------:|------------:|:----------------|-------------:|
|      0 |         5728 |        8918 |              55 |     0.0550348 |   0.0550348 | spw             |    0.0550348 |
|      1 |        13783 |        8918 |              85 |     0.0544602 |   0.0544602 | spw             |    0.0544602 |
|      2 |        24500 |        8918 |              94 |     0.0533328 |   0.0533328 | spw             |    0.0533328 |
|      3 |        33713 |        8918 |              99 |     0.036402  |   0.036402  | spw             |    0.036402  |

## SMOTE vs Scale_Pos_Weight Analysis

- **Average SMOTE AUC-PR:** 0.0498
- **Average Scale_Pos_Weight AUC-PR:** 0.0498
- **Winning Strategy:** spw (Scale_Pos_Weight)
