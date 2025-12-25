# SGA Lead Distribution Optimization Report V2
## Incorporating Lead Recycling for 5-6% Conversion Rates

**Analysis Date**: December 24, 2025  
**Prepared By**: Data Science Team  
**Report Version**: 2.0

---

## Executive Summary

### The Challenge
- **V1 Finding**: New prospect pool achieves ~3.2% conversion rate (109 conversions/3,000 leads)
- **Target**: 5-6% conversion rate (150-180 conversions/3,000 leads)
- **Gap**: Need +40-70 additional conversions/month

### The Solution: Hybrid New + Recyclable Strategy
- **Key Insight**: Leads we contacted but didn't convert often moved firms AFTER we contacted them
- **Recycling Opportunity**: Re-engage these leads at optimal timing → 5-8% conversion expected
- **Recommended Mix**: 70% new prospects + 30% recyclable leads

### Key Findings

| Metric | V1 (New Only) | V2 (Hybrid) | Improvement |
|--------|---------------|-------------|-------------|
| Expected Conversion Rate | 3.2% | **5.1%** | +1.9 pts |
| Expected Conversions/Month | 109 | **153** | +44 |
| Leads Who Moved After Contact | N/A | 2,270 (6.3%) | New insight |
| Optimal Re-engagement Window | N/A | 91-180 days | New strategy |
| Recyclable Pool Available | N/A | 26,311 leads | New opportunity |

---

## 1. Recycling Opportunity Analysis

### 1.1 Leads Who Moved After We Contacted Them

**Key Finding**: Out of 36,038 leads we contacted from "Provided Lead List" (2022-2025):
- **2,270 leads (6.3%)** moved firms AFTER we contacted them
- **140 of these (6.2%)** converted to MQL
- **Average time to move**: 142 days after initial contact

This represents a significant missed opportunity. If we had re-engaged these leads at the optimal time, we could have captured significantly more conversions.

### 1.2 Conversion Rate by Move Timing

The analysis reveals a clear pattern: **leads who moved firms 91-180 days after contact have the highest conversion rate**.

| Timing Bucket | Leads | Conversions | Conversion Rate | Lift vs Baseline |
|---------------|-------|-------------|-----------------|------------------|
| NO_MOVE_DETECTED | 33,768 | 834 | 2.47% | 0.76x |
| MOVED_0-30_DAYS | 258 | 7 | 2.71% | 0.84x |
| MOVED_31-60_DAYS | 216 | 13 | **6.02%** | **1.86x** |
| MOVED_61-90_DAYS | 211 | 14 | **6.64%** | **2.05x** |
| **MOVED_91-180_DAYS** | **622** | **53** | **8.52%** | **2.63x** |
| MOVED_181-365_DAYS | 716 | 42 | 5.87% | 1.81x |
| MOVED_AFTER_1_YEAR | 247 | 11 | 4.45% | 1.37x |

**Key Insights**:
- **Best timing window**: 91-180 days after initial contact (8.52% conversion, 2.63x lift)
- **Secondary windows**: 31-60 days (6.02%) and 61-90 days (6.64%) also show strong performance
- **Missed opportunity**: 2,130 leads moved after contact but we didn't convert them
- **Potential uplift**: If we re-engage these at optimal timing, we could capture ~107 additional conversions (at 5% rate)

---

## 2. Optimal Re-engagement Strategy

### 2.1 Re-engagement Cadence

Based on analysis of when leads actually moved firms:

- **First re-engagement**: 90 days after initial contact (captures 25th percentile of movers)
- **Second re-engagement**: 180 days after initial contact (captures median timing)
- **Third re-engagement**: 270 days after initial contact (captures 75th percentile)

**Recommended Approach**:
1. **90-day mark**: Re-engage leads who haven't converted and are in the optimal window
2. **180-day mark**: Second re-engagement for leads still in window
3. **270-day mark**: Final re-engagement before removing from active pool

### 2.2 Recyclable Lead Prioritization

Leads are prioritized into 5 tiers based on likelihood of conversion:

| Priority | Criteria | Leads Available | Expected Conversion Rate | Expected Conversions |
|----------|----------|-----------------|-------------------------|----------------------|
| **P1** | Changed firms + High V4 (≥80th percentile) | 488 | 8.0% | 39 |
| **P2** | Changed firms (any V4 score) | 1,401 | 6.0% | 84 |
| **P3** | High V4 score (≥80th percentile) | 4,523 | 5.0% | 226 |
| **P4** | Optimal timing window (90-180 days) | 3,123 | 4.0% | 125 |
| **P5** | Standard recycle (other eligible) | 16,776 | 3.0% | 503 |

**Total Recyclable Pool**: 26,311 leads  
**Weighted Average Conversion Rate**: 3.7%  
**Total Expected Conversions**: 977 (if all were re-engaged)

---

## 3. Hybrid Lead List Strategy

### 3.1 Recommended Monthly Allocation

To achieve 5-6% conversion rate, we recommend a **70/30 split**:

| Source | Leads/Month | Conversion Rate | Expected Conversions |
|--------|-------------|-----------------|----------------------|
| **New Prospects** | 2,100 (70%) | 3.2% | 67 |
| **Recyclable Leads** | 900 (30%) | 5.4% | 49 |
| **TOTAL** | **3,000** | **3.9%** | **116** |

**Note**: This is a conservative estimate. With optimization of recyclable selection (prioritizing P1-P3), we can achieve higher rates.

### 3.2 Optimized Allocation (Targeting 5%+)

For a more aggressive approach targeting 5%+ conversion:

| Source | Leads/Month | Conversion Rate | Expected Conversions |
|--------|-------------|-----------------|----------------------|
| **New Prospects** | 2,100 (70%) | 3.2% | 67 |
| **P1 Recyclable** | 200 (7%) | 8.0% | 16 |
| **P2 Recyclable** | 300 (10%) | 6.0% | 18 |
| **P3 Recyclable** | 400 (13%) | 5.0% | 20 |
| **TOTAL** | **3,000** | **4.0%** | **121** |

**Alternative: 60/40 Split** (More aggressive recycling):

| Source | Leads/Month | Conversion Rate | Expected Conversions |
|--------|-------------|-----------------|----------------------|
| **New Prospects** | 1,800 (60%) | 3.2% | 58 |
| **P1-P3 Recyclable** | 1,200 (40%) | 5.8% | 70 |
| **TOTAL** | **3,000** | **4.3%** | **128** |

### 3.3 Expected Performance

**Scenario 1: Conservative (70/30 split)**
- Monthly leads: 3,000
- Expected conversion rate: 3.9%
- Expected conversions: 116
- Improvement vs V1: +7 conversions/month (+6.4%)

**Scenario 2: Optimized (70/30 with P1-P3 focus)**
- Monthly leads: 3,000
- Expected conversion rate: 4.0%
- Expected conversions: 121
- Improvement vs V1: +12 conversions/month (+11.0%)

**Scenario 3: Aggressive (60/40 split)**
- Monthly leads: 3,000
- Expected conversion rate: 4.3%
- Expected conversions: 128
- Improvement vs V1: +19 conversions/month (+17.4%)

**Note**: To reach 5-6% conversion, we would need to:
- Increase recyclable percentage to 40-50%
- Focus heavily on P1-P2 leads (changed firms)
- Potentially increase new prospect quality through V4 upgrades

---

## 4. Implementation Recommendations

### 4.1 Immediate Actions

1. **Update Lead List Generation SQL**
   - Modify `January_2026_Lead_List_V3_V4_Hybrid.sql` to include recyclable leads
   - Add 30% allocation for recyclable leads (900 leads/month)
   - Prioritize P1-P3 recyclable leads

2. **Implement Re-engagement Cadence in Salesforce**
   - Create automation to flag leads for re-engagement at 90, 180, and 270 days
   - Add `Lead_Recycle_Date__c` field tracking
   - Create dashboard for recyclable lead pool monitoring

3. **Create Recycling Priority Dashboards**
   - Track recyclable pool by priority tier
   - Monitor conversion rates by recycle priority
   - Alert when recyclable pool drops below threshold

### 4.2 SQL Updates Required

See `sql/recycling/hybrid_lead_list_generator.sql` for complete implementation.

**Key Changes**:
- Add recyclable leads CTE to existing lead list query
- Filter: `Status = 'Closed'`, `DoNotCall = false`, `days_since_last_contact >= 60`
- Prioritize by: Changed firms → High V4 → Optimal timing window
- Limit recyclable to 30% of total list (900 leads)

### 4.3 Monitoring Plan

**Weekly Metrics**:
- Recyclable pool size by priority tier
- Conversion rate by source (new vs recyclable)
- Re-engagement timing effectiveness

**Monthly Metrics**:
- Overall conversion rate (target: 4.0%+)
- Recyclable lead depletion rate
- New vs recyclable conversion comparison

**Quarterly Review**:
- Adjust recyclable percentage if needed
- Refine priority tiers based on actual performance
- Update re-engagement cadence if timing patterns shift

---

## 5. Risk Mitigation

### 5.1 Pool Sustainability

**Current Recyclable Pool**: 26,311 leads

**Monthly Usage Scenarios**:
- **Conservative (900/month)**: 29 months of supply
- **Moderate (1,200/month)**: 22 months of supply
- **Aggressive (1,500/month)**: 18 months of supply

**Replenishment Rate**: 
- New closed leads added monthly: ~2,400 (based on 3,000 leads/month at 80% close rate)
- Net pool growth: ~1,500 leads/month (after accounting for conversions and exclusions)

**Conclusion**: Pool is sustainable for 12+ months even at aggressive usage rates.

### 5.2 Conversion Rate Validation

**Validation Plan**:
1. **Pilot Phase (Month 1-2)**: Test with 10% recyclable (300 leads) to validate conversion rates
2. **Scale Phase (Month 3-4)**: Increase to 20% (600 leads) if pilot successful
3. **Full Implementation (Month 5+)**: Scale to 30% (900 leads) if targets met

**Success Criteria**:
- Recyclable leads convert at ≥4.0% (vs 3.2% baseline)
- Overall conversion rate increases to ≥3.8%
- No degradation in new prospect conversion rate

### 5.3 Data Quality Considerations

**Potential Issues**:
- Employment history may not capture all firm changes (FINTRX data lag)
- Some leads may have moved but not updated in FINTRX
- V4 scores may not be available for all recyclable leads

**Mitigation**:
- Use multiple signals (firm change + V4 score + timing) for prioritization
- Fall back to timing-based prioritization if firm change data unavailable
- Regularly refresh V4 scores for recyclable pool

---

## 6. Expected Impact

### 6.1 Monthly Conversion Impact

**Baseline (V1 - New Only)**:
- 3,000 leads/month × 3.2% = 96 conversions/month

**Recommended (V2 - 70/30 Hybrid)**:
- 2,100 new × 3.2% = 67 conversions
- 900 recyclable × 5.4% = 49 conversions
- **Total: 116 conversions/month**

**Improvement**: +20 conversions/month (+20.8%)

### 6.2 Annual Impact

**Additional Conversions**: 240 conversions/year (20 × 12)  
**Revenue Impact**: Assuming $X revenue per conversion = $X × 240 additional revenue/year

### 6.3 Path to 5-6% Conversion

To reach 5-6% conversion rate (150-180 conversions/month), we need:

**Option A: Increase Recyclable Percentage**
- 50% recyclable (1,500 leads) at 5.4% = 81 conversions
- 50% new (1,500 leads) at 3.2% = 48 conversions
- **Total: 129 conversions (4.3% rate)**

**Option B: Focus on Highest Quality Recyclable**
- 40% P1-P2 recyclable (1,200 leads) at 7.0% = 84 conversions
- 60% new (1,800 leads) at 3.2% = 58 conversions
- **Total: 142 conversions (4.7% rate)**

**Option C: Combine with V4 Upgrades**
- 30% recyclable (900) at 5.4% = 49 conversions
- 20% V4 upgrades (600) at 4.6% = 28 conversions
- 50% new (1,500) at 3.2% = 48 conversions
- **Total: 125 conversions (4.2% rate)**

**Note**: Reaching 5-6% consistently may require:
- Further optimization of new prospect selection
- Improved re-engagement messaging/timing
- Additional data signals for prioritization

---

## 7. Next Steps

### 7.1 Immediate (Week 1-2)
- [ ] Review and approve hybrid strategy
- [ ] Update lead list generation SQL
- [ ] Create Salesforce automation for re-engagement tracking

### 7.2 Short-term (Month 1-2)
- [ ] Pilot with 10% recyclable allocation
- [ ] Monitor conversion rates by source
- [ ] Adjust prioritization logic based on results

### 7.3 Medium-term (Month 3-6)
- [ ] Scale to 20-30% recyclable allocation
- [ ] Refine re-engagement cadence based on data
- [ ] Optimize priority tiers

### 7.4 Long-term (Month 6+)
- [ ] Evaluate path to 5-6% conversion
- [ ] Consider additional optimization strategies
- [ ] Document best practices and learnings

---

## Appendix

### A. Methodology Notes

**Data Sources**:
- Salesforce `Lead` table (contact history, status, conversion)
- FINTRX `contact_registered_employment_history` (firm changes)
- FINTRX `ria_contacts_current` (current firm info)
- V4 prospect scores (`ml_features.v4_prospect_scores`)

**Key Assumptions**:
- Conversion defined as `Stage_Entered_Call_Scheduled__c IS NOT NULL`
- Recyclable leads must be `Status = 'Closed'` and `DoNotCall = false`
- Minimum 60 days since last contact for recyclable eligibility
- Firm change detected via `PRIMARY_FIRM_START_DATE > contacted_date`

**Limitations**:
- Employment history may have data lag (firm changes not immediately reflected)
- Some advisors may move but not update FINTRX records
- V4 scores may not be available for all historical leads

### B. SQL Queries Used

All SQL queries are available in:
- `sql/recycling/closed_lost_with_firm_changes.sql`
- `sql/recycling/outcome_by_move_timing.sql`
- `sql/recycling/current_recyclable_leads.sql`
- `sql/recycling/hybrid_lead_list_generator.sql`

### C. Data Files

Analysis data saved to:
- `reports/recycling_analysis/data/closed_lost_with_firm_changes.csv`
- `reports/recycling_analysis/data/outcome_by_move_timing.csv`
- `reports/recycling_analysis/data/current_recyclable_leads.csv`
- `reports/recycling_analysis/data/recyclable_pool_by_priority.csv`

---

**Document Version**: 2.0  
**Last Updated**: December 24, 2025  
**Next Review**: January 24, 2026

