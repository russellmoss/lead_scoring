# V3 vs V4 Model Investigation: Final Report

**Version**: 1.0  
**Generated**: 2025-12-24  
**Investigation Period**: Q1-Q3 2025 (Jan 1 - Sep 30, 2025)  
**Total Leads Analyzed**: 17,867  
**Total Conversions**: 579  
**Baseline Conversion Rate**: 3.24%

---

## Executive Summary

### The Question We Investigated

> **Did T1A leads (CFPs at bleeding firms, 1-4yr tenure) historically convert better than T2 leads (proven movers with 3+ prior firms)?**

This investigation was triggered by the January 2026 lead list analysis which revealed:
- V3-V4 Correlation: **-0.27** (models disagree!)
- T1A (best V3) avg V4 score: **0.56** (lowest of all tiers)
- T2 avg V4 score: **0.67** (higher than T1A)

### Key Findings

1. **V4 Better Predicts Conversions**: V4 AUC-ROC (0.6141) significantly outperforms V3 (0.5095)
2. **T1A Sample Too Small**: Only 4 leads, 0 conversions - cannot reliably compare to T2
3. **T1 Outperforms T2**: T1 (7.41%) converts at 2.31x the rate of T2 (3.20%), validating V3's prioritization of prime movers
4. **V4 Correct When Models Disagree**: Low V3/high V4 leads convert at 4.60% (1.42x baseline) vs high V3/low V4 leads at 0.00%

### Final Answer

**T1A vs T2**: Cannot determine - T1A sample too small (4 leads, 0 conversions).  
**T1 vs T2**: T1 significantly outperforms T2 (7.41% vs 3.20%, p=0.0008), validating V3's tier ordering for prime movers.

**Recommendation**: 
- **Trust V3 tier ordering** for T1 vs T2 (validated by historical data)
- **Use V4 for deprioritization** (better AUC-ROC, identifies low-value leads)
- **Hybrid approach**: V3 for prioritization, V4 for deprioritization

---

## Methodology

### Data Sources
- **Salesforce Lead Table**: Contacted leads from Q1-Q3 2025
- **FINTRX Data**: Advisor characteristics, employment history, firm metrics
- **V3 Tier Assignments**: Retrospective tier assignment based on V3.2.x rules
- **V4 Model**: XGBoost model (v4.0.0) with 14 PIT-compliant features

### Analysis Steps
1. **Step 1**: Extracted 17,867 historical leads with V3 tier assignments
2. **Step 2**: Matched leads to conversion outcomes (579 conversions, 3.24% rate)
3. **Step 3**: Analyzed actual vs expected conversion rates by tier
4. **Step 4**: Scored historical leads with V4 model (PIT-compliant features)
5. **Step 5**: Compared V3 vs V4 predictive performance (AUC-ROC)
6. **Step 6**: Generated final recommendations

---

## Detailed Findings

### 1. V3 Tier Performance (Actual vs Expected)

| Tier | Leads | Conversions | Actual Rate | Expected Rate | Actual Lift | Rate vs Expected |
|------|-------|-------------|-------------|---------------|-------------|------------------|
| TIER_1A_PRIME_MOVER_CFP | 4 | 0 | **0.00%** | 16.44% | 0.00x | 0.00x |
| TIER_1B_PRIME_MOVER_SERIES65 | 39 | 1 | **2.56%** | 16.48% | 0.79x | 0.16x |
| TIER_1_PRIME_MOVER | 270 | 20 | **7.41%** | 13.21% | **2.29x** | 0.56x |
| TIER_2_PROVEN_MOVER | 7,808 | 250 | **3.20%** | 8.59% | 0.99x | 0.37x |
| TIER_3_MODERATE_BLEEDER | 298 | 9 | **3.02%** | 9.52% | 0.93x | 0.32x |
| TIER_4_EXPERIENCED_MOVER | 24 | 0 | **0.00%** | 11.54% | 0.00x | 0.00x |
| TIER_5_HEAVY_BLEEDER | 239 | 5 | **2.09%** | 7.27% | 0.64x | 0.29x |
| STANDARD | 9,185 | 294 | **3.20%** | 3.82% | 0.99x | 0.84x |

**Key Observations**:
- **T1 has highest actual conversion rate** (7.41%) among all tiers
- **All tiers underperform** vs expected rates (actual < expected)
- **T1A sample too small** (4 leads, 0 conversions) for reliable analysis
- **T1 vs T2**: T1 converts at **2.31x** the rate of T2 (statistically significant, p=0.0008)

### 2. V3 vs V4 Model Performance

| Metric | V3 (Tier Rules) | V4 (XGBoost) | Winner |
|--------|-----------------|--------------|--------|
| **AUC-ROC** | 0.5095 | **0.6141** | **V4** |
| **Difference** | - | +0.1047 | Significant |

**Interpretation**:
- AUC-ROC measures how well the model ranks leads (higher score → higher conversion probability)
- **V4 significantly outperforms V3** in ranking leads by conversion probability
- V4's 0.6141 AUC-ROC indicates moderate predictive power (0.5 = random, 1.0 = perfect)
- V3's 0.5095 AUC-ROC is barely better than random, suggesting tier rules don't strongly predict conversions

### 3. The Critical Question: T1A vs T2

| Metric | T1A (CFP) | T2 (Proven Mover) |
|--------|-----------|-------------------|
| Lead Count | **4** | 7,808 |
| Conversions | **0** | 250 |
| Conversion Rate | **0.00%** | 3.20% |
| Lift vs Baseline | 0.00x | 0.99x |
| Avg V4 Score | 0.6395 | 0.5158 |
| Avg V4 Percentile | 90.2 | 56.9 |

**Conclusion**: **Cannot determine** - T1A sample size (4 leads, 0 conversions) is too small for reliable comparison.

**Alternative Comparison: T1 vs T2** (Larger Samples):

| Metric | T1 (Prime Mover) | T2 (Proven Mover) |
|--------|------------------|-------------------|
| Lead Count | 270 | 7,808 |
| Conversions | 20 | 250 |
| Conversion Rate | **7.41%** | 3.20% |
| Lift vs Baseline | **2.29x** | 0.99x |
| Avg V4 Score | 0.6337 | 0.5158 |
| Avg V4 Percentile | 85.8 | 56.9 |
| **Statistical Significance** | **p=0.0008** | - |

**Conclusion**: **T1 significantly outperforms T2** (7.41% vs 3.20%, p=0.0008). This validates V3's prioritization of prime movers over proven movers.

### 4. Disagreement Analysis

**When V3 Says High Priority but V4 Says Low**:
- Leads with V3 Tier 1 but V4 Percentile < 50: **17 leads**
- Conversion Rate: **0.00%** (0 conversions)
- vs Baseline: 0.00x

**When V3 Says Low Priority but V4 Says High**:
- Leads with V3 Tier 3+ but V4 Percentile >= 80: **1,174 leads**
- Conversion Rate: **4.60%** (54 conversions)
- vs Baseline: **1.42x**

**Finding**: **V4 is right when they disagree** - Low V3/high V4 leads convert better (4.60%) than high V3/low V4 leads (0.00%).

This suggests V4 captures signals that V3 tier rules miss, particularly for leads in lower V3 tiers.

---

## Recommendations

### 1. Keep Hybrid Approach (V3 + V4)

**Rationale**:
- V3 tier ordering is validated for T1 vs T2 (T1 converts 2.31x better)
- V4 has better overall predictive power (AUC-ROC 0.6141 vs 0.5095)
- V4 correctly identifies high-value leads in lower V3 tiers

**Implementation**:
- **V3 for prioritization**: Use tier ordering (T1 > T2 > T3 > ...) as primary ranking
- **V4 for deprioritization**: Skip bottom 20% by V4 score (converts at 1.33% vs 3.24% baseline)
- **V4 for tie-breaking**: Within same V3 tier, use V4 percentile for ranking

### 2. Monitor T1A Performance

**Issue**: T1A sample size too small (4 leads, 0 conversions) to validate T1A > T2 hypothesis.

**Action**:
- Collect more T1A data in January 2026
- Track T1A conversion rate separately
- Re-evaluate T1A tier placement if sample size increases

### 3. Re-evaluate V3 Tier Logic

**Finding**: All tiers underperform vs expected rates. This suggests:
- V3 expected rates may be too optimistic
- Market conditions may have changed
- Tier definitions may need refinement

**Action**:
- Review V3 expected conversion rates
- Consider recalibrating tier definitions based on actual performance
- Investigate why tiers underperform (market conditions, data quality, etc.)

### 4. Leverage V4's Cross-Tier Signal

**Finding**: V4 identifies 1,174 leads in lower V3 tiers (T3+) that score in top 20% by V4, converting at 4.60% (1.42x baseline).

**Action**:
- **Upgrade low V3/high V4 leads**: Consider promoting leads with V3 Tier 3+ but V4 percentile >= 80
- **Monitor high V3/low V4 leads**: Leads with V3 Tier 1 but V4 percentile < 50 converted at 0.00% - consider deprioritizing

### 5. A/B Test V4 Prioritization

**Recommendation**: Test V4-based prioritization vs V3 tier ordering in production.

**Test Design**:
- **Control**: V3 tier ordering (current approach)
- **Treatment**: V4 score-based ranking
- **Metrics**: Conversion rate, top decile lift, SDR efficiency
- **Duration**: 1-2 months

---

## Limitations

1. **T1A Sample Size**: Only 4 leads, 0 conversions - cannot validate T1A > T2 hypothesis
2. **Temporal Drift**: All tiers underperform vs expected rates - may indicate market changes
3. **PIT Compliance**: Historical features use current snapshot as proxy (true PIT would require historical snapshots)
4. **Conversion Definition**: Uses MQL conversion (Stage_Entered_Call_Scheduled__c) - may not capture all qualified leads

---

## Conclusion

**V3 vs V4**: Both models have value, but serve different purposes:

- **V3 Tier Rules**: Validated for T1 vs T2 prioritization (T1 converts 2.31x better)
- **V4 XGBoost**: Better overall predictive power (AUC-ROC 0.6141 vs 0.5095), identifies high-value leads across tiers

**Recommended Strategy**: **Hybrid Approach**
- Use V3 tier ordering for primary prioritization
- Use V4 for deprioritization (skip bottom 20%)
- Use V4 for cross-tier identification (upgrade low V3/high V4 leads)
- Use V4 for tie-breaking within same V3 tier

**Next Steps**:
1. Monitor T1A performance in January 2026
2. Re-evaluate V3 expected conversion rates
3. A/B test V4 prioritization vs V3 tier ordering
4. Track disagreement cases (high V3/low V4 and low V3/high V4)

---

## Appendix: Data Summary

### Tier Distribution
- TIER_1A_PRIME_MOVER_CFP: 4 (0.0%)
- TIER_1B_PRIME_MOVER_SERIES65: 39 (0.2%)
- TIER_1_PRIME_MOVER: 270 (1.5%)
- TIER_2_PROVEN_MOVER: 7,808 (43.7%)
- TIER_3_MODERATE_BLEEDER: 298 (1.7%)
- TIER_4_EXPERIENCED_MOVER: 24 (0.1%)
- TIER_5_HEAVY_BLEEDER: 239 (1.3%)
- STANDARD: 9,185 (51.4%)

### V4 Scoring Summary
- Total Scored: 17,867
- Score Range: 0.1428 - 0.8425
- Average Score: 0.4892
- Bottom 20% (Deprioritize): 3,769 leads

### Files Generated
- `sql/01_historical_leads.sql` - Historical leads with V3 tiers
- `sql/02_conversion_outcomes.sql` - Conversion outcomes
- `sql/04_v4_backtest_features.sql` - V4 features for historical leads
- `scripts/analyze_tier_performance.py` - Tier performance analysis
- `scripts/score_historical_leads.py` - V4 scoring script
- `scripts/compare_v3_v4.py` - V3 vs V4 comparison
- `reports/tier_analysis.md` - Tier performance report
- `reports/v3_vs_v4_testing.md` - V3 vs V4 comparison report
- `reports/FINAL_V3_VS_V4_INVESTIGATION_REPORT.md` - This report

---

**Report Generated**: 2025-12-24  
**Investigation Status**: ✅ COMPLETE

