# Model Training Report V1

**Generated:** 2025-11-03 17:16:13

## Summary

- **Winning Imbalance Strategy:** spw
- **Final Features Used:** 132
- **Training Samples:** 43,854
- **Positive Samples:** 1,399 (3.19%)
- **Negative Samples:** 42,455 (96.81%)

## Final Model Performance

### XGBoost (Final Model)

- **AUC-PR:** 1.0000
- **AUC-ROC:** 1.0000

### Logistic Regression (Baseline)

- **AUC-PR:** 0.0364
- **AUC-ROC:** 0.5315

## Cross-Validation Results

### Strategy Comparison by Fold

|   fold |   train_size |   test_size |   features_kept |   smote_aucpr |   spw_aucpr | best_strategy   |   best_aucpr |
|-------:|-------------:|------------:|----------------:|--------------:|------------:|:----------------|-------------:|
|      0 |         5743 |        8770 |             132 |     0.0890167 |   0.0890167 | spw             |    0.0890167 |
|      1 |        13506 |        8770 |             132 |     0.159076  |   0.159076  | spw             |    0.159076  |
|      2 |        24185 |        8770 |             132 |     0.19327   |   0.19327   | spw             |    0.19327   |
|      3 |        33375 |        8770 |             132 |     0.218703  |   0.218703  | spw             |    0.218703  |

## SMOTE vs Scale_Pos_Weight Analysis

- **Average SMOTE AUC-PR:** 0.1650
- **Average Scale_Pos_Weight AUC-PR:** 0.1650
- **Winning Strategy:** spw (Scale_Pos_Weight)
