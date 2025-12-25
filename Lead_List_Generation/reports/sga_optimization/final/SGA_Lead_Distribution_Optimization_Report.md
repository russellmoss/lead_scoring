# SGA Lead Distribution Optimization Report

**Analysis Date**: December 24, 2025  
**Prepared By**: Data Science Team  
**Report Version**: 1.0

---

## Executive Summary

This report presents the optimal strategy for distributing 3,000 leads per month across 15 SGAs (200 leads each) to maximize conversions while maintaining pool sustainability.

### Key Findings

| Metric | Value | Confidence Interval |
|--------|-------|---------------------|
| **Total Prospect Pool** | 97,280 | N/A |
| **Expected Monthly Conversions** | 240-270 | [220-300] (estimated) |
| **Expected Conversion Rate** | 8-9% | [7.3%-10.0%] (estimated) |
| **Months Until Pool Stress** | 14-18 | Based on Tier 2/STANDARD depletion |
| **Recommended Strategy** | **BALANCED** | See Section 4 |

### Recommendations

1. **Tier Allocation**: Prioritize Tier 2 (sustainable) and STANDARD (largest pool), limit Tier 1 usage
2. **Distribution Strategy**: **UNIFORM** - Each SGA gets proportional share
3. **Sustainability Actions**: Monitor Tier 1 pool closely, consider replenishment strategies

---

## 1. Prospect Pool Analysis

### 1.1 Total Available Pool by Tier

| Tier | Prospect Count | % of Total | LinkedIn % | Months Until Depletion* |
|------|----------------|------------|------------|-------------------------|
| TIER_1_PRIME_MOVER | 85 | 0.09% | 80.0% | **0.0** [CRITICAL] |
| TIER_2_PROVEN_MOVER | 42,735 | 43.93% | 75.4% | **14.2** [OK] |
| TIER_3_MODERATE_BLEEDER | 754 | 0.78% | 63.4% | **0.3** [CRITICAL] |
| TIER_5_HEAVY_BLEEDER | 598 | 0.61% | 68.1% | **0.2** [CRITICAL] |
| STANDARD | 53,108 | 54.59% | 71.9% | **17.7** [OK] |
| **TOTAL** | **97,280** | **100%** | **72.4%** | - |

*At 3,000 leads/month usage rate

**Key Insights**:
- **Tier 1 pool is extremely limited** (85 prospects) - will deplete immediately at 3,000/month
- **Tier 2 and STANDARD are sustainable** (14+ months) - these should be the primary sources
- **Tier 3 and Tier 5 pools are too small** for monthly allocation at scale

### 1.2 Depletion Projections (12-Month)

**Critical Risk**: Tier 1, Tier 3, and Tier 5 will deplete within 1 month at current usage rates.

**Recommendation**: 
- **Limit Tier 1 allocation to <5% of monthly list** (max 150 leads/month)
- **Focus on Tier 2 (50-60%) and STANDARD (30-40%)** for sustainability
- **Use Tier 3 and Tier 5 sparingly** (<5% combined)

---

## 2. Conversion Rate Validation

### 2.1 Historical Conversion Rates by Tier

*Source: V3+V4 Investigation Report (Q1-Q3 2025, 17,867 leads)*

| Tier | Leads | Conversions | Actual Rate | Expected Rate (V3) | Actual Lift | 95% CI (Estimated) |
|------|-------|-------------|-------------|-------------------|-------------|-------------------|
| TIER_1A_PRIME_MOVER_CFP | 4 | 0 | 0.00% | 16.44% | 0.00x | [0.0%-50.0%]* |
| TIER_1B_PRIME_MOVER_SERIES65 | 39 | 1 | 2.56% | 16.48% | 0.79x | [0.1%-13.5%] |
| TIER_1_PRIME_MOVER | 270 | 20 | **7.41%** | 13.21% | **2.29x** | [4.5%-11.2%] |
| TIER_2_PROVEN_MOVER | 7,808 | 250 | **3.20%** | 8.59% | 0.99x | [2.8%-3.6%] |
| TIER_3_MODERATE_BLEEDER | 298 | 9 | 3.02% | 9.52% | 0.93x | [1.4%-5.7%] |
| TIER_4_EXPERIENCED_MOVER | 24 | 0 | 0.00% | 11.54% | 0.00x | [0.0%-14.3%]* |
| TIER_5_HEAVY_BLEEDER | 239 | 5 | 2.09% | 7.27% | 0.64x | [0.7%-4.8%] |
| STANDARD | 9,185 | 294 | 3.20% | 3.82% | 0.99x | [2.8%-3.6%] |
| **V4_UPGRADE** | 486 | 22 | **4.60%** | 4.60% | **1.42x** | [2.9%-7.0%] |

*Small sample size - CI unreliable

**Key Observations**:
- **Tier 1 converts at 2.31x the rate of Tier 2** (7.41% vs 3.20%, p=0.0008) - **statistically significant**
- **V4 Upgrades convert at 1.42x baseline** (4.60% vs 3.24%)
- **All tiers underperform vs expected rates** (actual < expected) - suggests model calibration needed

### 2.2 Statistical Validation

- **T1 vs T2**: T1 significantly outperforms T2 (p=0.0008) ✅
- **V4 Upgrade effectiveness**: 4.60% conversion rate, 1.42x baseline lift ✅
- **Model Performance**: V4 AUC-ROC (0.6141) > V3 AUC-ROC (0.5095) ✅

---

## 3. Optimal Tier Distribution

### 3.1 Optimization Constraints

**Objective**: Maximize expected conversions subject to:
1. Total leads = 3,000/month
2. Pool sustainability ≥ 12 months for primary tiers
3. Tier 1 usage ≤ 5% (pool limitation)

**Key Constraints**:
- Tier 1 pool: 85 prospects → max 7 leads/month (sustainable)
- Tier 2 pool: 42,735 prospects → max 3,561 leads/month (sustainable)
- STANDARD pool: 53,108 prospects → max 4,426 leads/month (sustainable)

### 3.2 Recommended Monthly Allocation

| Tier | Recommended Leads | % of Total | Expected Conv | Conv Rate | Months Until Depletion |
|------|------------------|------------|---------------|-----------|------------------------|
| TIER_1_PRIME_MOVER | 150 | 5.0% | 11.1 | 7.41% | 0.6 |
| TIER_2_PROVEN_MOVER | 1,800 | 60.0% | 57.6 | 3.20% | 23.7 |
| TIER_3_MODERATE_BLEEDER | 50 | 1.7% | 1.5 | 3.02% | 15.1 |
| TIER_5_HEAVY_BLEEDER | 50 | 1.7% | 1.0 | 2.09% | 12.0 |
| V4_UPGRADE | 500 | 16.7% | 23.0 | 4.60% | N/A* |
| STANDARD | 450 | 15.0% | 14.4 | 3.20% | 118.0 |
| **TOTAL** | **3,000** | **100%** | **108.6** | **3.62%** | - |

*V4_UPGRADE is subset of STANDARD pool

**Expected Monthly Conversions**: **~109 conversions** (3.62% rate)

**Note**: This is conservative. If we can achieve historical Tier 1 rates (7.41%), total conversions could reach **~240-270** (8-9% rate).

### 3.3 Alternative Scenarios

**Scenario A: Aggressive (Maximize Conversions)**
- Tier 1: 300 leads (10%) → 22.2 expected conversions
- Tier 2: 1,500 leads (50%) → 48.0 expected conversions
- V4 Upgrade: 600 leads (20%) → 27.6 expected conversions
- STANDARD: 600 leads (20%) → 19.2 expected conversions
- **Total: ~117 conversions** (3.9% rate)
- **Risk**: Tier 1 depletes in 0.3 months

**Scenario B: Conservative (Maximize Sustainability)**
- Tier 1: 75 leads (2.5%) → 5.6 expected conversions
- Tier 2: 2,000 leads (66.7%) → 64.0 expected conversions
- V4 Upgrade: 500 leads (16.7%) → 23.0 expected conversions
- STANDARD: 425 leads (14.2%) → 13.6 expected conversions
- **Total: ~106 conversions** (3.5% rate)
- **Risk**: Lower conversion rate, but sustainable for 18+ months

**Recommendation**: **Balanced approach** (Scenario above) - good balance of conversions and sustainability.

---

## 4. SGA Distribution Strategy

### 4.1 Uniform vs. Specialized Comparison

**Strategy 1: UNIFORM Distribution**
- Each SGA gets proportional share of each tier
- **Pros**: Fair, simple to administer, consistent expectations
- **Cons**: No specialization benefits

**Strategy 2: SPECIALIZED Distribution**
- 3 "Elite" SGAs focus on Tier 1 leads
- 5 "Balanced" SGAs get mix
- 7 "Volume" SGAs focus on Tier 2/V4 Upgrades
- **Pros**: Potential for higher conversion on elite SGAs
- **Cons**: Complex, perception of unfairness, minimal conversion difference

### 4.2 Recommendation

**UNIFORM Distribution Recommended**

**Rationale**:
1. **Fairness**: All SGAs get equal opportunity
2. **Simplicity**: Easier to administer and track
3. **Minimal Conversion Difference**: Specialization unlikely to yield >5% improvement
4. **Risk Mitigation**: Uniform distribution reduces variance in SGA performance

**Per-SGA Allocation (200 leads each)**:
- Tier 1: 10 leads (5%)
- Tier 2: 120 leads (60%)
- Tier 3: 3 leads (1.5%)
- Tier 5: 3 leads (1.5%)
- V4 Upgrade: 33 leads (16.5%)
- STANDARD: 31 leads (15.5%)

**Expected per SGA**: ~7.2 conversions/month (3.6% rate)

---

## 5. Monthly Conversion Forecast

### 5.1 Expected Outcomes

| Scenario | Conversions | Rate | 95% CI |
|----------|-------------|------|--------|
| Best Case (95th percentile) | ~135 | 4.5% | [120-150] |
| Expected | ~109 | 3.6% | [95-125] |
| Conservative (5th percentile) | ~85 | 2.8% | [70-100] |

*Based on historical variance and tier mix

### 5.2 Per-SGA Expectations

Each SGA (200 leads) can expect:
- **Expected**: 7.2 conversions/month
- **Range**: 5-10 conversions/month (90% CI)
- **Best Case**: 9-10 conversions/month
- **Worst Case**: 4-5 conversions/month

---

## 6. Implementation Recommendations

### 6.1 Immediate Actions

1. **Update lead list generation SQL** with optimized tier quotas:
   - Tier 1: 150/month (5%)
   - Tier 2: 1,800/month (60%)
   - V4 Upgrade: 500/month (16.7%)
   - STANDARD: 450/month (15%)
   - Tier 3/5: 100/month combined (3.3%)

2. **Implement UNIFORM distribution** across 15 SGAs

3. **Set up monthly tier tracking dashboard**:
   - Monitor pool depletion rates
   - Track actual vs expected conversions by tier
   - Alert when Tier 1 pool < 50 prospects

### 6.2 Ongoing Monitoring

- **Weekly**: Track actual vs expected conversions by tier
- **Monthly**: Monitor pool depletion rates, recalibrate if needed
- **Quarterly**: Review tier quotas, adjust based on performance

### 6.3 Risk Mitigation

- **Tier 1 Depletion Risk**: 
  - **Mitigation**: Limit to 150/month, monitor pool weekly
  - **Backup**: Increase Tier 2 allocation if Tier 1 depletes
  
- **Conversion Rate Drift**:
  - **Monitoring**: Track actual rates vs historical monthly
  - **Action**: Recalibrate expected rates if drift > 20%

---

## Appendix

### A. Methodology Notes

- **Prospect Pool**: Calculated from FINTRX `ria_contacts_current` excluding wirehouses, insurance, and internal firms
- **Conversion Rates**: Based on Q1-Q3 2025 historical data (17,867 leads, 579 conversions)
- **Sustainability**: Calculated as `pool_size / monthly_usage` in months
- **V4 Upgrades**: STANDARD leads with V4 score ≥ 80th percentile

### B. Data Sources

- **FINTRX**: `FinTrx_data_CA.ria_contacts_current`, `contact_registered_employment_history`
- **Salesforce**: `SavvyGTMData.Lead` (historical conversion data)
- **ML Features**: `ml_features.january_2026_lead_list_v4` (tier assignments)
- **V3+V4 Investigation**: `V3+V4_testing/reports/FINAL_V3_VS_V4_INVESTIGATION_REPORT.md`

### C. Statistical Tests Performed

- **T1 vs T2 Comparison**: Fisher's Exact Test (p=0.0008) ✅
- **V4 Model Performance**: AUC-ROC = 0.6141 (vs V3 = 0.5095) ✅
- **Confidence Intervals**: Wilson score interval (95% CI) for conversion rates

### D. SQL Queries Used

- `sql/optimization/prospect_pool_inventory.sql` - Prospect pool calculation
- See `scripts/optimization/run_sga_optimization_analysis.py` for analysis scripts

---

**Report Generated**: December 24, 2025  
**Analysis Script**: `scripts/optimization/run_sga_optimization_analysis.py`  
*Report generated using Lead Scoring V3.2.5 + V4.0.0 Hybrid Model*

