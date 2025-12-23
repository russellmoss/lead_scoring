# Performance Validation Report V4

**Generated:** 2025-11-03 19:45:08

## Overall Performance Metrics

- **AUC-PR:** 0.8277
- **AUC-ROC:** 0.9326
- **Precision:** 0.9964
- **Recall:** 0.7848
- **F1 Score:** 0.8780
- **Precision @ 10%:** 0.2677
- **Precision @ 20%:** 0.1385
- **Lift @ 10%:** 8.39x
- **Lift @ 20%:** 4.34x

## Cross-Validation Consistency

- **Mean Test AUC-PR:** 0.7689
- **Std Dev Test AUC-PR:** 0.3173
- **CV Coefficient:** 41.27%
- **Range:** 0.2286 to 1.0000

## Validation Gates

- **AUC-PR > 0.20:** ✅ PASS
- **CV Coefficient < 15%:** ❌ FAIL
- **Train-Test Gap < 10%:** ❌ FAIL
