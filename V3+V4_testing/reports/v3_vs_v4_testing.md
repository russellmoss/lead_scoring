# V3 vs V4 Model Comparison Report

**Generated**: 2025-12-24 16:44:28
**Total Leads Analyzed**: 17,867
**Total Conversions**: 579
**Baseline Conversion Rate**: 3.24%

---

## 1. Model Performance Summary

| Metric | V3 (Tier Rules) | V4 (XGBoost) | Winner |
|--------|-----------------|--------------|--------|
| AUC-ROC | 0.5095 | 0.6141 | V4 |

**Interpretation**: 
- AUC-ROC measures how well the model ranks leads (higher score → higher conversion probability)
- V4 XGBoost better predicts conversions
- Difference: 0.1047 (significant)

---

## 2. The Critical Question: T1A vs T2

| Metric | T1A (CFP) | T2 (Proven Mover) |
|--------|-----------|-------------------|
| Lead Count | 4 | 7,808 |
| Conversions | 0 | 250 |
| Conversion Rate | 0.00% | 3.20% |
| Lift vs Baseline | 0.00x | 0.99x |
| Avg V4 Score | 0.6395 | 0.5158 |
| Avg V4 Percentile | 90.2 | 56.9 |


### T1 vs T2 Comparison (Larger Samples)

| Metric | T1 (Prime Mover) | T2 (Proven Mover) |
|--------|------------------|-------------------|
| Lead Count | 270 | 7,808 |
| Conversions | 20 | 250 |
| Conversion Rate | 7.41% | 3.20% |
| Lift vs Baseline | 2.29x | 0.99x |
| Avg V4 Score | 0.6337 | 0.5158 |
| Avg V4 Percentile | 85.8 | 56.9 |



---

## 3. Disagreement Analysis

### When V3 Says High Priority but V4 Says Low

Leads with V3 Tier 1 but V4 Percentile < 50:
- Count: 17
- Conversion Rate: 0.00%
- vs Baseline: 0.00x

### When V3 Says Low Priority but V4 Says High

Leads with V3 Tier 3+ but V4 Percentile >= 80:
- Count: 1,174
- Conversion Rate: 4.60%
- vs Baseline: 1.42x

**Finding**: V4 is right when they disagree - low V3/high V4 leads convert better.


---

## 4. Final Recommendations

Based on this analysis:


1. **V4 has better predictive power** - Higher AUC-ROC indicates better ranking
2. **Consider V4 for cross-tier ranking** - V4 may capture signals V3 misses
3. **Re-evaluate V3 tier logic** - Some tier assignments may not align with actual performance
4. **A/B test both approaches** - Test V4 prioritization vs V3 in production
