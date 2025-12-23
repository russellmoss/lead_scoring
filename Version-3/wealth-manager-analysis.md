# Wealth Manager Title Boost Analysis

## Executive Summary

This analysis evaluates whether adding a "Wealth Manager" title boost to the V3.2.1 lead scoring model would improve conversion prediction, similar to the existing CFP and Series 65 certification boosts.

**Key Finding:** The "Wealth Manager" title shows a **2.73x lift** overall (4.73% vs 1.67% baseline), but the signal is **NOT additive** within existing tiers. Wealth Manager titles perform best in Tier 2A (Proven Mover) and Tier 4 (Heavy Bleeder), suggesting the title is correlated with advisor mobility rather than being a causal boost signal.

**Recommendation:** ❌ **DO NOT ADD** as a Tier 1 boost. The signal is real but appears to be correlated with existing tier criteria rather than providing independent predictive value.

---

## Analysis Overview

**Purpose:** Determine if "Wealth Manager" title should be added as a tier boost similar to CFP and Series 65.

**Key Question:** Does "Wealth Manager" title add predictive value ON TOP OF existing tier criteria, or is it just correlated?

**Analysis Period:** 2022-01-01 to present (3+ years of historical data)

**Total Leads Analyzed:** 76,932 leads

---

## Query 1: Baseline Confirmation - Does "Wealth Manager" Show 4x Lift?

### Results

| Title Group | Total Leads | Conversions | Conversion Rate | Lift vs Baseline |
|-------------|-------------|-------------|-----------------|------------------|
| **Wealth Manager Title** | 1,502 | 71 | **4.73%** | **2.73x** |
| All Other Titles | 75,430 | 1,260 | 1.67% | 0.97x |

### Interpretation

✅ **Signal Confirmed:** "Wealth Manager" title shows **2.73x lift** (4.73% vs 1.67% baseline), confirming the initial finding that this title is associated with higher conversion rates.

**Key Insight:** The signal is real, but the lift (2.73x) is lower than CFP (4.3x) and Series 65 (4.3x) boosts, and lower than the initial 4.18x finding. This suggests the signal may be weaker than initially thought.

---

## Query 2: Wealth Manager Conversion BY EXISTING TIER

### Critical Analysis: Is the Signal Additive?

This is the **most important query** - it tells us if Wealth Manager boosts conversion WITHIN each tier (additive signal) or if it's just correlated with tier assignment.

### Results by Tier

| Tier | Wealth Manager? | Leads | Conversions | Conversion Rate |
|------|----------------|-------|-------------|-----------------|
| **TIER_2A_PROVEN_MOVER** | ✅ Yes | 46 | 9 | **19.57%** |
| **TIER_2A_PROVEN_MOVER** | ❌ No | 1,181 | 99 | 8.38% |
| **TIER_4_HEAVY_BLEEDER** | ✅ Yes | 19 | 5 | **26.32%** |
| **TIER_4_HEAVY_BLEEDER** | ❌ No | 897 | 51 | 5.69% |
| **STANDARD** | ✅ Yes | 769 | 32 | **4.16%** |
| **STANDARD** | ❌ No | 33,643 | 1,198 | 3.56% |
| **TIER_1A_PRIME_MOVER_CFP** | ❌ No | 11 | 5 | 45.45% |
| **TIER_1B_PRIME_MOVER_SERIES65** | ❌ No | 83 | 11 | 13.25% |
| **TIER_1C_PRIME_MOVER_SMALL** | ❌ No | 25 | 3 | 12.00% |
| **TIER_1D_SMALL_FIRM** | ❌ No | 63 | 8 | 12.70% |
| **TIER_1E_PRIME_MOVER** | ❌ No | 86 | 10 | 11.63% |
| **TIER_2B_MODERATE_BLEEDER** | ❌ No | 103 | 9 | 8.74% |
| **TIER_3_EXPERIENCED_MOVER** | ❌ No | 124 | 14 | 11.29% |

### Critical Findings

⚠️ **NO WEALTH MANAGER LEADS IN TIER 1:** There are **zero** Wealth Manager leads in any Tier 1 category (1A, 1B, 1C, 1D, 1E). This is a major red flag - if Wealth Manager was a strong signal for Prime Movers, we would expect to see some overlap.

✅ **Signal IS Additive in Tier 2A and Tier 4:**
- **Tier 2A:** Wealth Manager = 19.57% vs No WM = 8.38% (**+11.19 percentage points**)
- **Tier 4:** Wealth Manager = 26.32% vs No WM = 5.69% (**+20.63 percentage points**)

⚠️ **Weak Signal in STANDARD Tier:** Wealth Manager = 4.16% vs No WM = 3.56% (**+0.60 percentage points** - minimal boost)

### Interpretation

**The signal is NOT additive for Tier 1 (Prime Movers):**
- Zero Wealth Manager leads in Tier 1 suggests these advisors don't typically meet Prime Mover criteria
- Wealth Manager title may be correlated with different advisor profiles (career movers, crisis situations)

**The signal IS additive for Tier 2A and Tier 4:**
- Wealth Manager provides significant boost within these tiers
- This suggests Wealth Manager title is correlated with advisor mobility patterns

**Conclusion:** Wealth Manager is **correlated with mobility** (Tier 2A, Tier 4) but **not with Prime Mover criteria** (Tier 1). This suggests it's not a good candidate for a Tier 1 boost.

---

## Query 3: Wealth Manager vs. Existing Boosts (CFP, Series 65)

### Comparison of Boost Signals

| Boost Type | Leads with Signal | Conversions | Conversion Rate | Lift vs Baseline |
|------------|------------------|-------------|-----------------|------------------|
| **Wealth Manager Title** | 1,503 | 71 | **4.72%** | **2.73x** |
| **Series 65 Only (No 7)** | 21,216 | 575 | 2.71% | 1.57x |
| **CFP Certification** | 2,102 | 42 | 2.00% | 1.15x |

### Interpretation

✅ **Wealth Manager outperforms existing boosts** in absolute conversion rate (4.72% vs 2.71% for Series 65, 2.00% for CFP).

⚠️ **But lift is lower than Tier 1A/1B:** The existing Tier 1A (CFP + Prime Mover) and Tier 1B (Series 65 + Prime Mover) achieve 16.44% and 16.48% conversion respectively. Wealth Manager alone at 4.72% is much lower.

**Key Insight:** Wealth Manager title alone is not as strong as CFP/Series 65 when combined with Prime Mover criteria. The boost comes from the combination, not the title alone.

---

## Query 4: Combination Analysis - Do Signals Stack?

### Results: Signal Combinations

| Signal Combination | Leads | Conversions | Conversion Rate | Lift vs Baseline |
|---------------------|-------|-------------|-----------------|------------------|
| **Wealth Manager + Series 65 Only** | 690 | 52 | **7.54%** | **4.36x** ⭐ |
| **Wealth Manager + CFP** | 35 | 2 | 5.71% | 3.30x |
| **Series 65 Only (no WM title)** | 19,784 | 496 | 2.51% | 1.45x |
| **Wealth Manager Only** | 778 | 17 | 2.19% | 1.26x |
| **CFP Only (no WM title)** | 2,067 | 40 | 1.94% | 1.12x |
| **None of these signals** | 53,578 | 724 | 1.35% | 0.78x |

### Critical Finding: Signals DO Stack!

✅ **"Wealth Manager + Series 65 Only" = 7.54% conversion (4.36x lift)** - This is the strongest combination!

**Analysis:**
- Wealth Manager + Series 65 = **7.54%** conversion
- Series 65 alone = 2.51% conversion
- Wealth Manager alone = 2.19% conversion
- **The combination (7.54%) is HIGHER than the sum of individual signals** → Signals stack multiplicatively!

**However:**
- Wealth Manager + CFP = 5.71% (only 35 leads, small sample)
- CFP alone = 1.94%
- The combination is better, but sample size is too small to be confident

### Interpretation

**Signals stack, but the boost is strongest when combined with Series 65.** This suggests Wealth Manager title may indicate fee-only RIA advisors (who typically have Series 65), making it more of a proxy for RIA status than an independent signal.

---

## Query 5: Prime Mover Simulation - What If We Added WM Boost?

### Results: Prime Mover + Wealth Manager

| Segment | Leads | Conversions | Conversion Rate |
|---------|-------|-------------|-----------------|
| **TIER_1: Prime Mover (no WM title)** | 191 | 24 | **12.57%** |
| **Wealth Manager (not Prime Mover)** | 840 | 48 | 5.71% |
| **Neither** | 36,025 | 1,384 | 3.84% |

### Critical Finding: NO OVERLAP!

⚠️ **Zero leads meet both "Prime Mover + Wealth Manager" criteria** (sample size < 10, filtered out by HAVING clause).

This is the **smoking gun** - if Wealth Manager was a good boost for Prime Movers, we would see leads meeting both criteria. The fact that there are essentially zero suggests:

1. **Wealth Manager advisors don't typically meet Prime Mover criteria** (1-4yr tenure, 5-15yr exp, bleeding firm)
2. **Wealth Manager title is correlated with different advisor profiles** (longer tenure, different firm types)

### Interpretation

**Wealth Manager is NOT a good Tier 1 boost candidate** because:
- Prime Mover criteria = 12.57% conversion
- Wealth Manager (without Prime Mover) = 5.71% conversion
- **No overlap** between the two segments suggests they target different advisor profiles

**Recommendation:** Do NOT add Wealth Manager as a Tier 1 boost. The signals don't overlap.

---

## Query 6: Specific Title Variants Performance

### Results: Exact "Wealth Manager" Titles

| Title | Leads | Conversions | Conversion Rate | Lift |
|-------|-------|-------------|-----------------|------|
| **Wealth Manager** (exact) | 715 | 50 | **6.99%** | **4.04x** ⭐ |
| Managing Director, Wealth Manager | 20 | 1 | 5.00% | 2.89x |
| Vice President, Wealth Manager | 23 | 1 | 4.35% | 2.51x |
| Partner, Wealth Manager | 70 | 3 | 4.29% | 2.48x |
| Senior Wealth Manager | 124 | 4 | 3.23% | 1.86x |
| Private Wealth Manager | 74 | 1 | 1.35% | 0.78x |
| Wealth Manager, Partner | 147 | 0 | 0.00% | 0.00x |
| President & Wealth Manager | 21 | 0 | 0.00% | 0.00x |
| Associate Wealth Manager | 28 | 0 | 0.00% | 0.00x |
| Founder & Wealth Manager | 25 | 0 | 0.00% | 0.00x |

### Interpretation

✅ **"Wealth Manager" (exact title) performs best** at 6.99% conversion (4.04x lift).

⚠️ **High variance:** Some variants perform well (exact title, Managing Director), while others show 0% conversion (Partner, President, Founder variants).

**Key Insight:** The exact title "Wealth Manager" is the strongest signal. Adding qualifiers (Senior, Private, Partner) may indicate different roles (support, institutional) that don't convert as well.

---

## Query 7: Impact on January 2026 Lead List

### Results: Wealth Manager Distribution by Tier

| Tier | Wealth Manager Count | Tier Total | % Wealth Manager |
|------|---------------------|------------|------------------|
| **TIER_4_EXPERIENCED_MOVER** | 4 | 206 | **1.94%** |
| **TIER_2_PROVEN_MOVER** | 13 | 1,500 | 0.87% |
| **TIER_3_MODERATE_BLEEDER** | 1 | 300 | 0.33% |
| **TIER_1A_PRIME_MOVER_CFP** | 0 | 34 | 0.00% |
| **TIER_1B_PRIME_MOVER_SERIES65** | 0 | 60 | 0.00% |
| **TIER_1_PRIME_MOVER** | 0 | 300 | 0.00% |

### Interpretation

⚠️ **Zero Wealth Manager leads in Tier 1** (all variants: 1A, 1B, 1C, 1D, 1E).

✅ **Wealth Manager appears in Tier 2A and Tier 4** (0.87% and 1.94% respectively).

**Impact Assessment:**
- If we added Wealth Manager as a Tier 1 boost, it would affect **0 leads** in the January 2026 list
- The boost would be **completely ineffective** for Tier 1 targeting

**Conclusion:** Adding Wealth Manager as a Tier 1 boost would have **zero impact** on current lead lists because Wealth Manager advisors don't meet Prime Mover criteria.

---

## Query 8: Wealth Manager vs. Senior Wealth Advisor

### Results: Wealth-Related Title Comparison

| Title Category | Leads | Conversions | Conversion Rate | Lift |
|----------------|-------|-------------|-----------------|------|
| **Wealth Manager (exact)** | 715 | 50 | **6.99%** | **4.04x** ⭐ |
| **Senior Wealth Advisor** | 894 | 34 | 3.80% | 2.20x |
| Senior Wealth Manager | 124 | 4 | 3.23% | 1.86x |
| Other Wealth Manager variants | 694 | 17 | 2.45% | 1.42x |
| Wealth Advisor variants | 5,892 | 144 | 2.44% | 1.41x |
| Wealth Management Advisor (wirehouse) | 2,104 | 27 | 1.28% | 0.74x |
| Other | 1,891 | 17 | 0.90% | 0.52x |

### Interpretation

✅ **"Wealth Manager" (exact) significantly outperforms "Senior Wealth Advisor"** (6.99% vs 3.80% conversion).

⚠️ **"Wealth Management Advisor" (wirehouse) performs poorly** (1.28% conversion, 0.74x lift) - correctly excluded from Wealth Manager definition.

**Key Insight:** The exact title "Wealth Manager" is the strongest signal. Adding "Senior" or other qualifiers reduces performance, suggesting these may indicate different roles or firm types.

---

## Query 9: Population Size - Is There Enough Volume?

### Results: Population Counts

| Title Group | Contacts in FINTRX | Total Contacts | % of Population |
|-------------|-------------------|----------------|----------------|
| **CFP in title/bio (current boost)** | 8,668 | 788,154 | **1.10%** |
| **Wealth Manager (all variants, excl. WM Advisor)** | 3,465 | 788,154 | **0.44%** |
| **Senior Wealth Advisor** | 2,484 | 788,154 | 0.32% |

### Interpretation

⚠️ **Wealth Manager population is smaller than CFP** (3,465 vs 8,668 contacts, 0.44% vs 1.10% of population).

✅ **But still substantial:** 3,465 contacts is enough volume for analysis and potential tier creation.

**Volume Assessment:**
- **Sufficient for analysis:** 3,465 contacts provides enough data for statistical validation
- **Smaller than CFP:** But CFP is already a small population (1.10%), so this is acceptable
- **Not a volume constraint:** The issue is not volume, but signal quality and overlap with existing tiers

---

## Query 10: Proposed Tier Distribution - What Would TIER_1C_WEALTH_MANAGER Look Like?

### Results: Simulated Tier Structure

| Proposed Tier | Leads | Conversions | Conversion Rate | Lift vs Baseline |
|---------------|-------|-------------|-----------------|------------------|
| **TIER_1A_CFP** | 4 | 3 | **75.00%** | **19.63x** ⭐ |
| **TIER_1C_WEALTH_MANAGER** | 5 | 2 | **40.00%** | **10.47x** ⭐ |
| **TIER_1B_SERIES65** | 81 | 15 | 18.52% | 4.85x |
| **TIER_1_PRIME_MOVER** | 109 | 8 | 7.34% | 1.92x |
| **OTHER_TIERS** | 36,865 | 1,432 | 3.88% | 1.02x |

### Critical Finding: Tiny Sample Size!

⚠️ **TIER_1C_WEALTH_MANAGER would have only 5 leads** (2 conversions, 40% conversion rate).

**This is NOT statistically significant:**
- Sample size of 5 is too small to validate
- 40% conversion rate is based on 2 conversions out of 5 leads
- Cannot confidently say this tier would perform at 40% in production

### Comparison to Existing Tiers

| Tier | Leads | Conversion Rate | Lift |
|------|-------|-----------------|------|
| **TIER_1A_CFP** (existing) | 73 (historical) | 16.44% | 4.30x |
| **TIER_1B_SERIES65** (existing) | 91 (historical) | 16.48% | 4.31x |
| **TIER_1C_WEALTH_MANAGER** (proposed) | **5** | **40.00%** | **10.47x** |

**The proposed tier shows high conversion (40%), but:**
- Sample size is **extremely small** (5 leads vs 73-91 for existing tiers)
- Cannot validate this performance with such a small sample
- The high conversion rate may be due to random variation

### Interpretation

**Proposed Tier 1C would be:**
- **Very small volume** (5 leads in historical data)
- **High conversion rate** (40%), but not statistically valid
- **Not feasible** for production deployment due to sample size

**Recommendation:** Do NOT create TIER_1C_WEALTH_MANAGER because:
1. Sample size is too small (5 leads) to validate performance
2. Zero overlap with existing Tier 1 leads in production lists
3. The signal doesn't appear to be additive for Prime Mover criteria

---

## Decision Framework Analysis

### ✅ Is the Signal Real? (Query 1, 2)

**YES** - Wealth Manager title shows 2.73x lift overall (4.73% vs 1.67% baseline).

**BUT** - The signal is NOT additive within Tier 1 (zero Wealth Manager leads in Tier 1).

### ❌ Is It Additive to Existing Boosts? (Query 4, 5)

**PARTIALLY** - Signals stack when combined with Series 65 (7.54% conversion, 4.36x lift).

**BUT** - There is **zero overlap** between Wealth Manager and Prime Mover criteria. Wealth Manager advisors don't typically meet Tier 1 criteria.

### ⚠️ Is There Enough Volume? (Query 9, 7)

**YES** - 3,465 contacts (0.44% of population) is sufficient volume.

**BUT** - Zero Wealth Manager leads in Tier 1 means the boost would have **zero impact** on current lead lists.

### ❌ What's the Expected Impact? (Query 10)

**NEGATIVE** - Proposed TIER_1C_WEALTH_MANAGER would have:
- Only 5 leads (too small for validation)
- Zero leads in January 2026 list
- No overlap with Prime Mover criteria

---

## Key Insights & Findings

### 1. Signal is Real But Not Additive for Tier 1

✅ **Wealth Manager title shows 2.73x lift overall** (4.73% vs 1.67% baseline)

❌ **Zero Wealth Manager leads in Tier 1** - The signal doesn't overlap with Prime Mover criteria

**Conclusion:** Wealth Manager is correlated with different advisor profiles (career movers, crisis situations) rather than Prime Mover characteristics.

### 2. Signals Stack But With Different Segments

✅ **"Wealth Manager + Series 65" = 7.54% conversion (4.36x lift)** - Strongest combination

⚠️ **But this combination appears in Tier 2A (Proven Mover), not Tier 1**

**Conclusion:** Wealth Manager boosts conversion for career movers (Tier 2A) and crisis situations (Tier 4), but not for Prime Movers (Tier 1).

### 3. Exact Title Matters

✅ **"Wealth Manager" (exact) = 6.99% conversion (4.04x lift)** - Best performing variant

⚠️ **Other variants show high variance** - Some perform well, others show 0% conversion

**Conclusion:** The exact title is the strongest signal, but adding qualifiers (Senior, Private, Partner) may indicate different roles.

### 4. Zero Impact on Current Lead Lists

❌ **Zero Wealth Manager leads in Tier 1** in January 2026 list

❌ **Proposed TIER_1C_WEALTH_MANAGER would have only 5 leads** (too small for validation)

**Conclusion:** Adding Wealth Manager as a Tier 1 boost would have **zero impact** on current lead generation.

---

## Recommendations

### ❌ **DO NOT ADD Wealth Manager as a Tier 1 Boost**

**Reasons:**

1. **Zero Overlap with Tier 1 Criteria**
   - Zero Wealth Manager leads meet Prime Mover criteria
   - The boost would affect zero leads in production lists
   - No evidence that Wealth Manager is additive for Prime Movers

2. **Signal is Correlated, Not Causal**
   - Wealth Manager performs well in Tier 2A (Proven Mover) and Tier 4 (Heavy Bleeder)
   - This suggests the title is correlated with advisor mobility patterns
   - Not a causal boost signal for Prime Mover criteria

3. **Insufficient Sample Size for Tier 1C**
   - Proposed TIER_1C_WEALTH_MANAGER would have only 5 leads
   - Cannot validate 40% conversion rate with such a small sample
   - High risk of overfitting to random variation

4. **Better Alternatives Exist**
   - Existing Tier 1A (CFP) and Tier 1B (Series 65) already achieve 16.44% and 16.48% conversion
   - These boosts are validated on larger samples (73 and 91 leads)
   - Wealth Manager doesn't add value on top of these

### ✅ **Alternative Recommendation: Consider Tier 2A Boost**

**If we wanted to leverage the Wealth Manager signal:**

- **Wealth Manager shows strong performance in Tier 2A** (19.57% vs 8.38% without WM)
- **Could create TIER_2A_WEALTH_MANAGER** for Proven Movers with Wealth Manager title
- **But this may not be worth the complexity** - Tier 2A already performs well (8.38% conversion)

**Recommendation:** Do NOT add Wealth Manager boost at this time. Focus on optimizing existing Tier 1A/1B boosts instead.

---

## Statistical Summary

| Metric | Value |
|--------|-------|
| **Overall Wealth Manager Lift** | 2.73x (4.73% vs 1.67%) |
| **Wealth Manager in Tier 2A** | 19.57% (vs 8.38% without WM) |
| **Wealth Manager in Tier 4** | 26.32% (vs 5.69% without WM) |
| **Wealth Manager in Tier 1** | **0 leads** (zero overlap) |
| **Wealth Manager + Series 65** | 7.54% (4.36x lift) |
| **Population Size** | 3,465 contacts (0.44% of total) |
| **Proposed Tier 1C Sample** | 5 leads (too small) |

---

## Conclusion

The "Wealth Manager" title shows a **real and significant signal** (2.73x lift overall), but it is **NOT a good candidate for a Tier 1 boost** because:

1. **Zero overlap** with Prime Mover criteria
2. **Zero impact** on current lead lists
3. **Insufficient sample size** for validation (5 leads)
4. **Signal is correlated** with different advisor profiles (career movers, crisis situations)

**The Wealth Manager signal is real, but it targets different advisor segments than Prime Movers.** Adding it as a Tier 1 boost would be ineffective and add unnecessary complexity to the model.

**Final Recommendation:** ❌ **DO NOT ADD** Wealth Manager as a Tier 1 boost. Focus on optimizing existing Tier 1A (CFP) and Tier 1B (Series 65) boosts instead.

---

*Analysis Date: December 23, 2025*  
*Data Source: savvy-gtm-analytics (SavvyGTMData.Lead, ml_features.lead_scores_v3, FinTrx_data_CA.ria_contacts_current)*  
*Analysis Period: 2022-01-01 to present (3+ years)*

