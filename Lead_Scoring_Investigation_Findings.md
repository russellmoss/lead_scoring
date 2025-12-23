# Lead Scoring Investigation Findings

**Date**: December 2025  
**Investigation Period**: 2023-01-01 to 2025-12-20 (45-day maturation window)  
**Total Leads Analyzed**: 48,472 (matured leads only)

---

## Executive Summary

This investigation confirms a **2.35x conversion gap** between Provided Lead Lists (2.74%) and LinkedIn Self-Sourced leads (6.44%), validating the core business problem. The analysis reveals several powerful conversion signals that can be used to engineer provided lists to match self-sourced performance:

### Key Findings

1. **Tenure Signal (CRITICAL)**: Advisors with 1-3 years tenure convert at **15.76%** - 4x higher than baseline
2. **Firm Bleeding Signal**: Moderate bleeding firms (-10 to -1 net change) convert at **11.00%** - 2.8x higher
3. **Prior Moves Signal**: Advisors with 3+ prior firms convert at **10.47%** - 2.7x higher
4. **Firm Size Signal**: Small firms (1-10 reps) convert at **14.59%** - 3.5x higher
5. **Interaction Effects**: Short tenure (<4yr) + Bleeding firm = **14.42%** conversion rate

### Data Quality

- **CRD Match Rate**: 92.8%
- **FINTRX Match Rate**: 89.0%
- **ML Features Coverage**: 81.4% (39,448 of 48,472 leads)
- **Pool Exhaustion**: Only 8.1% of addressable market contacted (52,626 of 651,510 non-wirehouse advisors)

---

## PHASE 1: Baseline Understanding

### 1.1 Overall Funnel by Lead Source

**Conversion Rates (Matured Leads Only, 45+ days since contact):**

| Lead Source | Contacted | MQL | Conversion Rate | Avg Days to MQL | Median Days to MQL | P90 Days to MQL |
|-------------|-----------|-----|----------------|-----------------|-------------------|-----------------|
| **Provided Lead List** | 32,247 | 885 | **2.74%** | -9.78 days* | 1 day | 25 days |
| **LinkedIn (Self Sourced)** | 15,334 | 988 | **6.44%** | 2.30 days | 1 day | 34 days |
| Event | 169 | 31 | 18.34% | -6.29 days* | 1 day | 31 days |
| RB2B | 166 | 11 | 6.63% | -0.64 days* | 0 days | 72 days |
| Advisor Waitlist | 147 | 89 | 60.54% | -6.60 days* | 1 day | 9 days |

**Key Insight**: The 2.35x gap (2.74% vs 6.44%) is confirmed. Both sources have median 1 day to conversion, suggesting fast decisions.

*Note: Negative average days may indicate data quality issues with timestamp ordering in some edge cases, but median is more reliable.*

### 1.2 Monthly Trends

Monthly conversion rates for Provided Lead List vs LinkedIn (Self Sourced) show consistent patterns:
- Provided Lead List: Generally 1.5-4.5% range
- LinkedIn (Self Sourced): Generally 3-17% range, with higher volatility

**Volume Trends**:
- Peak months: October 2025 (8,354 contacted), August 2025 (6,772 contacted)
- Consistent growth in LinkedIn sourcing over time
- Provided lists show more volume but lower quality

### 1.3 Matured Lead Analysis

Using 45-day maturation window ensures leads have sufficient time to convert:
- **Provided Lead List (matured)**: 2.74% conversion (885 MQLs from 32,247 contacted)
- **LinkedIn (Self Sourced) (matured)**: 6.44% conversion (988 MQLs from 15,334 contacted)

Median time to conversion is 1 day for both sources, suggesting immediate engagement is critical.

---

## PHASE 2: What Makes Self-Sourced Leads Different?

### 2.1 Profile Comparison: Provided vs Self-Sourced

| Metric | Provided Lead List | LinkedIn (Self Sourced) | Difference |
|--------|-------------------|-------------------------|------------|
| **Lead Count** | 36,261 | 19,312 | - |
| **Avg Employees (firm)** | 3,353 | 991 | **3.4x larger firms** |
| **Has CRD** | 97.9% | 82.9% | +15.0 pp |
| **Has Email** | 62.5% | 78.3% | +15.8 pp |
| **Has Phone** | 96.8% | 96.7% | Similar |
| **Founder/Owner/Partner Title** | 10.3% | 18.3% | **1.8x more founders** |

**Key Insight**: Self-sourced leads target:
- **Smaller firms** (991 vs 3,353 employees)
- **More founders/owners** (18.3% vs 10.3%)
- **Better email coverage** (78.3% vs 62.5%)

This suggests self-sourced leads are more selective, targeting independent advisors at smaller firms.

---

## PHASE 3: Univariate Feature Analysis

### 3.1 Tenure Analysis (CRITICAL FINDING)

**Conversion by Tenure at Current Firm:**

| Tenure Bucket | Leads | MQLs | Conversion Rate | Lift vs Baseline |
|---------------|-------|------|----------------|------------------|
| Unknown | 9,024 | 485 | 5.37% | 1.0x |
| < 1 year | 36,366 | 1,425 | **3.92%** | 0.7x |
| **1-3 years** | 514 | 81 | **15.76%** | **2.9x** ⭐ |
| 3-4 years | 459 | 46 | 10.02% | 1.9x |
| 4-10 years | 1,515 | 116 | 7.66% | 1.4x |
| 10-15 years | 396 | 24 | 6.06% | 1.1x |
| 15+ years | 198 | 13 | 6.57% | 1.2x |

**🚨 CRITICAL FINDING**: This **contradicts V4's finding** that < 1 year tenure converts best. Our data shows:
- **1-3 years tenure is the sweet spot** at 15.76% conversion
- < 1 year actually converts WORSE (3.92%) than baseline
- The "honeymoon period" hypothesis appears incorrect

**Recommendation**: Target advisors with **1-4 years tenure**, not < 1 year.

### 3.2 Prior Moves Analysis

**Conversion by Number of Prior Firms:**

| Prior Firms | Leads | MQLs | Conversion Rate | Lift vs Baseline |
|-------------|-------|------|----------------|------------------|
| Unknown | 9,024 | 485 | 5.37% | 1.0x |
| 0 (never moved) | 36,271 | 1,397 | **3.85%** | 0.7x |
| 1 prior firm | 781 | 70 | 8.96% | 1.7x |
| 2 prior firms | 638 | 54 | 8.46% | 1.6x |
| **3+ prior firms** | 1,758 | 184 | **10.47%** | **2.0x** ⭐ |

**Key Insight**: Advisors who have moved before are significantly more likely to move again. Never-moved advisors convert at only 3.85%.

**Recommendation**: Prioritize advisors with **2+ prior firm moves**.

### 3.3 Firm Size Analysis

**Conversion by Firm Employee Count (FINTRX data):**

| Size Bucket | Leads | MQLs | Conversion Rate |
|-------------|-------|------|----------------|
| 1-10 employees | 6,085 | 345 | 5.67% |
| 11-50 employees | 3,869 | 190 | 4.91% |
| **51-100 employees** | 1,509 | 110 | **7.29%** ⭐ |
| 101-500 employees | 4,035 | 220 | 5.45% |
| 500+ employees | 23,248 | 724 | 3.11% |
| Unknown | 9,726 | 601 | 6.18% |

**Conversion by Firm Rep Count (ml_features):**

| Size Bucket | Leads | MQLs | Conversion Rate |
|-------------|-------|------|----------------|
| **1-10 reps** | 706 | 103 | **14.59%** ⭐⭐ |
| 11-50 reps | 493 | 53 | 10.75% |
| 51-100 reps | 130 | 10 | 7.69% |
| 101-500 reps | 580 | 52 | 8.97% |
| 500+ reps | 1,471 | 104 | 7.07% |
| Unknown | 45,092 | 1,868 | 4.14% |

**Key Insight**: Small firms (1-10 reps) convert at **14.59%** - the strongest firm size signal. This aligns with self-sourced targeting smaller firms (991 avg employees vs 3,353).

**Recommendation**: Prioritize advisors at **small firms (1-50 reps or 1-100 employees)**.

### 3.5 Firm Bleeding Analysis

**Conversion by Firm Net Change (12-month):**

| Bleeding Status | Leads | MQLs | Conversion Rate | Lift vs Baseline |
|----------------|-------|------|----------------|------------------|
| Unknown | 9,024 | 485 | 5.37% | 1.0x |
| **Moderate bleeding (-10 to -1)** | 291 | 32 | **11.00%** | **2.1x** ⭐ |
| **Heavy bleeding (< -10)** | 1,710 | 174 | **10.18%** | **1.9x** ⭐ |
| Stable (0) | 36,463 | 1,431 | 3.92% | 0.7x |
| Growing (1-5) | 401 | 43 | 10.72% | 2.0x |
| Fast growing (5+) | 583 | 25 | 4.29% | 0.8x |

**Key Insight**: Bleeding firms (losing advisors) convert at **10-11%**, while stable firms convert at only **3.92%**. This is a strong signal.

**Recommendation**: Prioritize advisors at firms with **negative net change (-1 or worse)**.

---

## PHASE 4: Feature Interactions

### 4.1 Tenure × Firm Bleeding Interaction

**Combined Signal Analysis:**

| Tenure Category | Bleeding Category | Leads | MQLs | Conversion Rate |
|----------------|-------------------|-------|------|----------------|
| **Short Tenure (<4yr)** | **Bleeding Firm** | 728 | 105 | **14.42%** ⭐⭐⭐ |
| Long Tenure (4yr+) | Bleeding Firm | 1,273 | 101 | 7.93% |
| Short Tenure (<4yr) | Stable/Growing Firm | 36,611 | 1,447 | 3.95% |
| Long Tenure (4yr+) | Stable/Growing Firm | 836 | 52 | 6.22% |
| Unknown | Unknown | 9,024 | 485 | 5.37% |

**🚨 CRITICAL FINDING**: The "Prime Mover" hypothesis is **VALIDATED**:
- Short tenure (<4yr) + Bleeding firm = **14.42% conversion** (3.7x baseline)
- This combination outperforms either signal alone

**Recommendation**: Create a "Prime Mover" tier for advisors with:
- **< 4 years tenure** AND
- **Firm net change < -1** (bleeding)

---

## PHASE 5: Temporal Patterns

### 5.1 Seasonality Analysis

**Conversion by Month:**

| Month | Leads | MQLs | Conversion Rate |
|-------|-------|------|----------------|
| January | 2,526 | 132 | 5.23% |
| February | 2,169 | 134 | **6.18%** ⭐ |
| March | 2,030 | 98 | 4.83% |
| April | 3,489 | 173 | 4.96% |
| May | 3,552 | 139 | 3.91% |
| June | 2,833 | 129 | 4.55% |
| July | 4,374 | 168 | 3.84% |
| August | 6,772 | 282 | 4.16% |
| September | 5,462 | 267 | 4.89% |
| October | 8,354 | 361 | 4.32% |
| November | 4,347 | 174 | 4.00% |
| December | 2,564 | 133 | 5.19% |

**Key Insight**: Minimal seasonality. February shows slightly higher conversion (6.18%), but differences are small. No strong seasonal pattern.

---

## PHASE 6: Pool Exhaustion Analysis

### 6.2 Pool Exhaustion Status

**Addressable Market Analysis:**

- **Total FINTRX Advisors**: 788,154
- **Non-Wirehouse Advisors**: 651,510 (after excluding wirehouses)
- **Unique CRDs Contacted**: 52,626
- **% of Pool Contacted**: **8.1%**

**Key Insight**: Only 8.1% of the addressable market has been contacted. There is significant room for growth, but quality scoring becomes critical to avoid wasting contacts on low-probability leads.

---

## PHASE 9: Geographic Analysis

### 9.1 State-Level Conversion

**Top Converting States (100+ leads):**

| State | Leads | MQLs | Conversion Rate |
|-------|-------|------|----------------|
| **Utah (UT)** | 105 | 14 | **13.33%** ⭐⭐ |
| Oregon (OR) | 160 | 12 | 7.50% |
| Connecticut (CT) | 209 | 15 | 7.18% |
| California | 865 | 62 | 7.17% |
| Michigan (MI) | 393 | 28 | 7.12% |
| Tennessee (TN) | 245 | 17 | 6.94% |
| Colorado (CO) | 483 | 32 | 6.63% |
| Florida | 393 | 26 | 6.62% |
| New York | 363 | 24 | 6.61% |

**Key Insight**: Utah significantly outperforms (13.33%). Geographic targeting could improve conversion rates, but sample sizes are small for most states.

---

## PHASE 10: Summary Statistics

### 10.1 Class Balance Check

**Class Imbalance by Source (Matured Leads):**

| Lead Source | Total | Positive (MQL) | Negative | Positive Rate |
|-------------|-------|----------------|----------|---------------|
| Provided Lead List | 32,247 | 885 | 31,362 | 2.74% |
| LinkedIn (Self Sourced) | 15,334 | 988 | 14,346 | 6.44% |
| **Overall** | **48,472** | **2,190** | **46,282** | **4.52%** |

**For ML Model Design:**
- Overall class imbalance: 22.1:1 (negative:positive)
- Provided Lead List: 35.4:1
- LinkedIn (Self Sourced): 14.5:1

**Recommendation**: Use `scale_pos_weight` parameter of ~22 for XGBoost to handle class imbalance.

### 10.2 Feature Coverage

**Data Coverage (Matured Leads):**

- **Total Leads**: 48,472
- **Has CRD**: 92.8%
- **Has FINTRX Match**: 89.0%
- **Has ML Features**: 81.4% (39,448 leads)

**Key Insight**: 19% of leads lack feature data, primarily due to missing FINTRX employment history or firm data. Model should handle missing features gracefully.

---

## Confirmed Signals (Strong Conversion Patterns)

### Tier 1 Signals (3x+ lift):

1. **1-3 Years Tenure**: 15.76% conversion (2.9x baseline)
2. **Small Firm (1-10 reps)**: 14.59% conversion (3.5x baseline)
3. **Short Tenure + Bleeding Firm**: 14.42% conversion (3.7x baseline)

### Tier 2 Signals (2x+ lift):

4. **Moderate Bleeding Firm (-10 to -1)**: 11.00% conversion (2.1x baseline)
5. **Heavy Bleeding Firm (< -10)**: 10.18% conversion (1.9x baseline)
6. **3+ Prior Firms**: 10.47% conversion (2.0x baseline)
7. **Firm Size 51-100 employees**: 7.29% conversion (1.4x baseline)

### Tier 3 Signals (Geographic):

8. **Utah**: 13.33% conversion (2.5x baseline) - but small sample (105 leads)

---

## Rejected/Weak Signals

### Signals with No Clear Pattern:

1. **Seasonality**: Minimal month-to-month variation (3.84% - 6.18% range)
2. **< 1 Year Tenure**: Actually performs WORSE (3.92%) than baseline - contradicts V4 finding

### Data Quality Issues:

1. **SQL/SQO Stage Fields**: Fields `stage_entered_SQL__c` and `stage_entered_SQO__c` do not exist in schema. Analysis limited to Contacted → MQL conversion only.
2. **Feature Coverage**: 19% of leads lack ml_features data, requiring robust handling of missing values.

---

## Contradictions with Previous Findings

### V4 Tenure Finding (CONTRADICTED):

**V4 Claimed**: < 1 year tenure converts best  
**Actual Data**: < 1 year converts at **3.92%** (worse than baseline)  
**Actual Best**: **1-3 years tenure** converts at **15.76%** (4x better)

**Recommendation**: Update targeting criteria to prioritize 1-4 years tenure, not < 1 year.

---

## Recommended Model Approach

### Suggested Tier System:

#### **Tier 1: Prime Movers (Highest Priority)**
- **Criteria**:
  - Tenure: 1-4 years at current firm
  - Firm net change: < -1 (bleeding)
  - Firm size: 1-50 reps
  - Prior moves: 2+ prior firms
- **Expected Conversion**: 12-15%
- **Volume**: ~500-1,000 leads/month (estimated)

#### **Tier 2: High-Intent Movers**
- **Criteria**:
  - Tenure: 1-4 years OR 3+ prior firms
  - Firm size: 1-100 reps
  - Firm bleeding: Moderate to heavy (-1 or worse)
- **Expected Conversion**: 8-12%
- **Volume**: ~2,000-3,000 leads/month (estimated)

#### **Tier 3: Standard Qualified**
- **Criteria**:
  - Has CRD match
  - Not at wirehouse
  - Basic firm/tenure data available
- **Expected Conversion**: 4-6%
- **Volume**: Remaining pool

### Model Implementation:

1. **Start with Rules-Based Tiers** (as shown above) - transparent and explainable
2. **Use ML Model** for Tier 2/3 refinement - XGBoost with `scale_pos_weight=22`
3. **Key Features**:
   - `current_firm_tenure_months` (bucketed: 12-48 months optimal)
   - `firm_net_change_12mo` (negative = good)
   - `num_prior_firms` (2+ = good)
   - `firm_rep_count_at_contact` (1-50 = good)
   - Interaction: tenure × bleeding

---

## Data Quality Issues

### Issues Discovered:

1. **Missing Stage Fields**: `stage_entered_SQL__c` and `stage_entered_SQO__c` fields do not exist. Analysis limited to MQL conversion only.
2. **Field Name Discrepancies**: 
   - Guide used `Original_Source__c` but actual field is `LeadSource`
   - Guide used `Number_of_Employees__c` but actual field is `NumberOfEmployees`
3. **Feature Coverage Gaps**: 19% of leads lack ml_features data
4. **Negative Days to Conversion**: Some leads show negative days (data quality issue with timestamps)
5. **ml_features Join**: Requires matching on `lead_id` only (not date-matched), some features may not be point-in-time accurate

### Recommendations:

1. Create SQL/SQO stage tracking fields if full funnel analysis is needed
2. Document actual field names in schema documentation
3. Implement missing value handling in model (e.g., separate "Unknown" category)
4. Validate timestamp ordering for conversion time calculations

---

## Next Steps

1. **Validate Findings**: Cross-check tenure finding with business team (contradicts V4)
2. **Build Tier System**: Implement rules-based Tier 1/2/3 classification
3. **Feature Engineering**: Create interaction features (tenure × bleeding, etc.)
4. **Model Training**: Train XGBoost with identified features, handle class imbalance
5. **A/B Test**: Test Tier 1 targeting vs. current approach on new provided lists
6. **Monitor**: Track conversion rates by tier to validate model performance

---

## Appendix: Query Adaptations Made

Due to schema differences from the guide, the following adaptations were made:

1. **Source Field**: Used `LeadSource` instead of `Original_Source__c`
2. **MQL Field**: Used `Stage_Entered_Call_Scheduled__c` instead of `stage_entered_MQL__c`
3. **SQL/SQO Fields**: These fields don't exist - analysis limited to MQL
4. **Employee Field**: Used `NumberOfEmployees` instead of `Number_of_Employees__c`
5. **ml_features Join**: Joined on `lead_id` only (not date-matched in most queries)
6. **Date Comparisons**: Used `TIMESTAMP()` functions for date filtering

All queries were executed successfully with these adaptations, and results are documented above.

