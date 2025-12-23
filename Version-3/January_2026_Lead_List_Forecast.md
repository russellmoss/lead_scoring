# January 2026 Lead List Performance Forecast

**Report Date:** 2025-12-22  
**Model Version:** V3.2_12212025  
**Deployed Table:** `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025`  
**Forecast Period:** January 2026

---

## Executive Summary

### V3.2 Model Performance (Validated)

| Tier | Conversion Rate | Lift vs Baseline | Volume in Model |
|------|-----------------|------------------|-----------------|
| TIER_1_PRIME_MOVER | 15.92% | 4.63x | 245 |
| TIER_2_PROVEN_MOVER | 8.59% | 2.50x | 1,281 |
| TIER_3_MODERATE_BLEEDER | 9.52% | 2.77x | 84 |
| TIER_4_EXPERIENCED_MOVER | 11.54% | 3.35x | 130 |
| TIER_5_HEAVY_BLEEDER | 7.27% | 2.11x | 674 |
| STANDARD | 3.44% | 1.00x | 37,034 |

**Total Scored Leads:** 39,448  
**Priority Tier Leads:** 2,414 (6.12% of total)

### January 2026 Forecast (2,250 Leads - Natural V3.2 Distribution)

| Metric | Low 50 CI | Median | High 50 CI |
|--------|-----------|--------|------------|
| **Contacted → MQL** | 3.64% | 3.80% | 3.95% |
| **Expected Conversions** | 82 | 85.4 | 89 |

**Distribution Used:** Natural V3.2 tier proportions (matches deployed model distribution)

---

## Available Lead Pool

### From V3.2 Scored Table

| Metric | Count |
|--------|-------|
| Total Scored Leads | 39,448 |
| Priority Tier Leads | 2,414 |
| % Priority | 6.12% |

**Tier Distribution in V3.2 Table:**

| Tier | Count | % of Total | Expected Rate |
|------|-------|------------|---------------|
| TIER_1_PRIME_MOVER | 245 | 0.62% | 16.00% |
| TIER_2_PROVEN_MOVER | 1,281 | 3.25% | 9.00% |
| TIER_3_MODERATE_BLEEDER | 84 | 0.21% | 9.33% |
| TIER_4_EXPERIENCED_MOVER | 130 | 0.33% | 11.97% |
| TIER_5_HEAVY_BLEEDER | 674 | 1.71% | 7.38% |
| STANDARD | 37,034 | 93.88% | 3.21% |

### New Prospects (Not in Salesforce)

| Status | Count |
|--------|-------|
| Scoreable New Prospects | 664,197 |
| Missing Start Date | 51,695 |
| Missing Name | 1 |
| **Total New Prospects** | **715,893** |

**Note:** 664,197 new prospects are scoreable (have required fields for V3.2 scoring). These would need to be scored using the V3.2 tier logic before inclusion in forecasts.

### Recyclable Leads (180+ Days)

**Total Eligible Recyclable:** 5,927 leads

**Breakdown:**
- 180+ Days No Activity, Eligible: 569
- No Activity Ever, Eligible: 5,358
- 180+ Days, Bad Status: 14,864 (excluded)
- 180+ Days, DNC: 457 (excluded)
- No Activity Ever, Bad Status: 33,113 (excluded)
- No Activity Ever, DNC: 170 (excluded)

**Recyclable Leads with V3.2 Scores:**

| Tier | Count | % of Recyclable |
|------|-------|-----------------|
| TIER_1_PRIME_MOVER | 41 | 2.51% |
| TIER_2_PROVEN_MOVER | 119 | 7.29% |
| TIER_3_MODERATE_BLEEDER | 11 | 0.67% |
| TIER_4_EXPERIENCED_MOVER | 10 | 0.61% |
| TIER_5_HEAVY_BLEEDER | 49 | 3.00% |
| STANDARD | 1,403 | 85.92% |
| **Total Scored** | **1,633** | **27.6%** |

**Note:** Only 1,633 of 5,927 recyclable leads have V3.2 scores (27.6%). The remaining 4,294 leads would need to be scored before inclusion.

---

## January 2026 Forecast Scenarios

### Scenario A: Natural V3.2 Distribution (2,250 leads)

Uses the same tier distribution as the deployed V3.2 model (6.12% priority tiers):

| Tier | Count | % of List | Expected Conversions | Low 50 CI | High 50 CI |
|------|-------|-----------|---------------------|-----------|------------|
| TIER_1_PRIME_MOVER | 14 | 0.62% | 2.2 | 1.9 | 2.5 |
| TIER_2_PROVEN_MOVER | 73 | 3.25% | 6.3 | 5.7 | 6.8 |
| TIER_3_MODERATE_BLEEDER | 5 | 0.21% | 0.5 | 0.3 | 0.6 |
| TIER_4_EXPERIENCED_MOVER | 7 | 0.33% | 0.8 | 0.6 | 1.0 |
| TIER_5_HEAVY_BLEEDER | 38 | 1.71% | 2.8 | 2.4 | 3.1 |
| STANDARD | 2,113 | 93.88% | 72.6 | 70.8 | 74.8 |
| **TOTAL** | **2,250** | **100%** | **85.4** | **81.9** | **88.9** |

**Expected Conversion Rate:** 85.4 / 2,250 = **3.80%** (50% CI: 3.64% - 3.95%)

**Use Case:** Conservative baseline forecast matching current V3.2 production distribution

---

### Scenario B: Priority Tiers Only (2,250 leads)

Focus exclusively on Tiers 1-5 (higher rate, assumes we can source enough priority leads):

| Tier | Count | % of List | Expected Conversions | Low 50 CI | High 50 CI |
|------|-------|-----------|---------------------|-----------|------------|
| TIER_1_PRIME_MOVER | 50 | 2.22% | 8.0 | 6.8 | 9.1 |
| TIER_2_PROVEN_MOVER | 1,000 | 44.44% | 85.9 | 78.2 | 93.6 |
| TIER_3_MODERATE_BLEEDER | 50 | 2.22% | 4.8 | 3.2 | 6.3 |
| TIER_4_EXPERIENCED_MOVER | 100 | 4.44% | 11.5 | 8.8 | 14.3 |
| TIER_5_HEAVY_BLEEDER | 1,050 | 46.67% | 76.3 | 66.0 | 86.6 |
| STANDARD | 0 | 0% | 0.0 | 0.0 | 0.0 |
| **TOTAL** | **2,250** | **100%** | **186.5** | **163.0** | **209.9** |

**Expected Conversion Rate:** 186.5 / 2,250 = **8.29%** (50% CI: 7.24% - 9.33%)

**Use Case:** Maximum conversion rate scenario (if sufficient priority tier leads are available)

**Note:** This scenario requires sourcing from the 664,197 new prospects pool (where 42.5% would be priority tiers based on previous analysis).

---

### Scenario C: Tier 1 + 2 Focus (Highest Quality)

Only use TIER_1_PRIME_MOVER and TIER_2_PROVEN_MOVER (highest volume priority tiers):

| Tier | Count | % of List | Expected Conversions | Low 50 CI | High 50 CI |
|------|-------|-----------|---------------------|-----------|------------|
| TIER_1_PRIME_MOVER | 100 | 4.44% | 15.9 | 13.6 | 18.2 |
| TIER_2_PROVEN_MOVER | 2,150 | 95.56% | 184.7 | 168.1 | 201.2 |
| STANDARD | 0 | 0% | 0.0 | 0.0 | 0.0 |
| **TOTAL** | **2,250** | **100%** | **200.6** | **181.7** | **219.4** |

**Expected Conversion Rate:** 200.6 / 2,250 = **8.92%** (50% CI: 8.08% - 9.75%)

**Use Case:** Focus on proven high-converting tiers with good volume availability

---

### Scenario D: Balanced Mix (Recommended)

Balanced approach mixing priority tiers with standard:

| Tier | Count | % of List | Expected Conversions | Low 50 CI | High 50 CI |
|------|-------|-----------|---------------------|-----------|------------|
| TIER_1_PRIME_MOVER | 30 | 1.33% | 4.8 | 4.1 | 5.5 |
| TIER_2_PROVEN_MOVER | 150 | 6.67% | 12.9 | 11.7 | 14.0 |
| TIER_3_MODERATE_BLEEDER | 15 | 0.67% | 1.4 | 1.0 | 1.9 |
| TIER_4_EXPERIENCED_MOVER | 20 | 0.89% | 2.3 | 1.8 | 2.9 |
| TIER_5_HEAVY_BLEEDER | 75 | 3.33% | 5.5 | 4.7 | 6.2 |
| STANDARD | 1,960 | 87.11% | 67.4 | 65.7 | 69.4 |
| **TOTAL** | **2,250** | **100%** | **94.3** | **89.0** | **99.9** |

**Expected Conversion Rate:** 94.3 / 2,250 = **4.19%** (50% CI: 3.96% - 4.44%)

**Use Case:** Practical balance between volume and conversion rate, achievable with current pool

**Lift vs Baseline:** 1.22x (4.19% vs 3.44%)

---

## Recommendations

### 1. Prioritize Tier 1 (Prime Mover)
- **15.92% conversion rate** (4.63x lift)
- Limited supply (0.62% of V3.2 table, ~4.67% of new prospects pool)
- **Action:** Reserve Tier 1 leads for highest-priority outreach

### 2. Leverage Tier 2 (Proven Mover) for Volume
- **8.59% conversion rate** (2.50x lift)
- Largest priority tier (3.25% of V3.2 table, ~11.25% of new prospects pool)
- **Action:** Primary tier for volume targets

### 3. Include Recyclable Leads Strategically
- 5,927 eligible recyclable leads (1,633 already scored)
- Lower priority tier percentage (14.08% vs 42.5% for new prospects)
- **Action:** Prioritize new prospects, supplement with scored recyclable leads

### 4. Monitor Weekly Performance
- Track actual vs expected conversions by tier
- Adjust tier mix if certain tiers underperform
- **Action:** Weekly review of tier performance metrics

### 5. Source from New Prospects Pool
- 664,197 scoreable new prospects available
- Higher priority tier concentration than scored leads
- **Action:** Score and prioritize new prospects over recyclable leads when possible

---

## Key Assumptions & Risks

### Assumptions

1. **V3.2 conversion rates apply to January 2026**
   - Based on 39,448 historical leads
   - Validated on training/test splits
   - **Confidence: HIGH**

2. **Natural distribution reflects available pool**
   - Scenario A uses V3.2 table distribution
   - New prospects may have different distribution (42.5% priority vs 6.12%)
   - **Confidence: MEDIUM**

3. **No seasonality adjustment**
   - January rates assumed same as historical average
   - **Confidence: LOW** (no seasonal analysis performed)

4. **Recyclable leads convert at same rates as new**
   - May be fatigued from previous contact
   - **Confidence: MEDIUM** (no fatigue analysis)

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Priority tier supply constraints | Can't source enough Tier 1/4 | Have Scenario D (balanced) as fallback |
| Recyclable lead fatigue | Lower conversion than expected | Weight new prospects higher |
| Seasonality effects | -10-20% vs baseline | Monitor weekly, adjust expectations |
| Distribution differences | New prospects don't match V3.2 table | Validate sample before full rollout |

---

## Appendix: V3.2 Model Details

### Tier Definitions

- **TIER_1_PRIME_MOVER:** Mobile advisor (1-4yr tenure) + bleeding firm + optimal experience (5-15yr) OR very small firm (<10 reps)
- **TIER_2_PROVEN_MOVER:** 3+ prior firms, proven mobility, 5+ years experience
- **TIER_3_MODERATE_BLEEDER:** At firm losing 1-10 advisors, 5+ years experience
- **TIER_4_EXPERIENCED_MOVER:** Industry veterans (20+ years) with recent move (1-4yr tenure)
- **TIER_5_HEAVY_BLEEDER:** At firm losing 10+ advisors, 5+ years experience
- **STANDARD:** Does not meet priority tier criteria (baseline)

### Validation Basis

- **Total Leads Analyzed:** 39,448
- **Priority Tier Leads:** 2,414 (6.12%)
- **Baseline Conversion (STANDARD):** 3.44%
- **All priority tiers statistically significant** (95% CIs don't overlap baseline)

### Conversion Rate Reference (50% Confidence Intervals)

| Tier | Median Rate | Low 50 CI | High 50 CI |
|------|-------------|-----------|------------|
| TIER_1_PRIME_MOVER | 15.92% | 13.63% | 18.21% |
| TIER_2_PROVEN_MOVER | 8.59% | 7.82% | 9.36% |
| TIER_3_MODERATE_BLEEDER | 9.52% | 6.39% | 12.66% |
| TIER_4_EXPERIENCED_MOVER | 11.54% | 8.80% | 14.29% |
| TIER_5_HEAVY_BLEEDER | 7.27% | 6.29% | 8.25% |
| STANDARD | 3.44% | 3.35% | 3.54% |

### Quick Reference: Expected Conversions per 100 Leads

| If you contact... | Expected MQLs | Expected Rate |
|-------------------|---------------|---------------|
| 100 TIER_1_PRIME_MOVER | 16 | 15.92% |
| 100 TIER_2_PROVEN_MOVER | 9 | 8.59% |
| 100 TIER_4_EXPERIENCED_MOVER | 12 | 11.54% |
| 100 TIER_5_HEAVY_BLEEDER | 7 | 7.27% |
| 100 STANDARD | 3 | 3.44% |

### Key Insight

**Priority tiers (6.12% of scored leads) convert at 2-5x the rate of STANDARD leads.** Focusing on priority tiers will significantly improve conversion efficiency, with the highest impact from Tier 1 (Prime Mover) at 4.63x lift.

---

**Report Generated By:** Lead Scoring Analytics  
**Model:** V3.2_12212025 (Deployed Production Model)  
**Next Update:** After January 2026 actuals available  
**Questions/Issues:** Review tier performance weekly and adjust allocation as needed
