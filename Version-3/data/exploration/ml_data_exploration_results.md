# ML Lead Scoring Model - Data Exploration Results

**Date**: December 2025  
**Purpose**: Comprehensive data exploration to inform XGBoost ML model development  
**Dataset**: `FinTrx_data_CA` (Canadian region tables)  
**Time Period**: January 2024 - December 2025

---

## Executive Summary

This document presents the results of comprehensive data exploration for building an ML lead scoring model to predict MQL (Marketing Qualified Lead) conversion. Key findings:

- **Overall Conversion Rate**: ~4.2% (Contacted → MQL)
- **FINTRX Match Rate**: 88.3% of leads can be enriched with FINTRX data
- **Top Predictive Features**: Mobility (3+ moves = 2.98x lift), Tenure at Firm (1-2 years = 4.05x lift), Broker Protocol membership (2.03x lift)
- **Lead Source Drift**: Significant shift from "Provided Lead List" (94% in Q1 2024) to "LinkedIn Self Sourced" (53% in Q4 2025)
- **Time to Conversion**: Median 1 day, 90th percentile 39 days, 99th percentile 343 days

---

## Phase 1: Target Variable Deep Dive

### 1.1 Conversion Rate by Time Period

**Query**: Monthly conversion rates from January 2024 to December 2025

| Contact Month | Contacted Leads | MQL Conversions | Conversion Rate % |
|---------------|-----------------|-----------------|-------------------|
| 2024-01 | 4 | 1 | 25.00% |
| 2024-02 | 126 | 6 | 4.76% |
| 2024-03 | 102 | 9 | 8.82% |
| 2024-04 | 775 | 29 | 3.74% |
| 2024-05 | 925 | 22 | 2.38% |
| 2024-06 | 1,120 | 45 | 4.02% |
| 2024-07 | 1,872 | 52 | 2.78% |
| 2024-08 | 2,769 | 120 | 4.33% |
| 2024-09 | 1,889 | 76 | 4.02% |
| 2024-10 | 2,902 | 109 | 3.76% |
| 2024-11 | 3,249 | 126 | 3.88% |
| 2024-12 | 2,553 | 130 | 5.09% |
| 2025-01 | 2,519 | 130 | 5.16% |
| 2025-02 | 2,039 | 128 | 6.28% |
| 2025-03 | 1,927 | 89 | 4.62% |
| 2025-04 | 2,699 | 144 | 5.34% |
| 2025-05 | 2,606 | 117 | 4.49% |
| 2025-06 | 1,710 | 83 | 4.85% |
| 2025-07 | 2,496 | 116 | 4.65% |
| 2025-08 | 3,975 | 159 | 4.00% |
| 2025-09 | 3,549 | 189 | 5.33% |
| 2025-10 | 5,436 | 251 | 4.62% |
| 2025-11 | 4,718 | 150 | 3.18% |
| 2025-12 | 5,564 | 135 | 2.43% |

**Key Insights**:
- Conversion rate is relatively stable around 4-5% after initial ramp-up
- Early months (Jan-Mar 2024) have small sample sizes and high variance
- Recent months (Nov-Dec 2025) show declining conversion rates (3.18%, 2.43%) - **investigate**
- Peak conversion: February 2025 (6.28%) and September 2025 (5.33%)

**Recommendations**:
- Use 90-day maturity window for conversion (covers 90% of conversions)
- Monitor recent decline in conversion rates - may indicate lead quality shift
- Consider seasonal adjustments if patterns emerge

---

### 1.2 Time-to-Conversion Distribution

**Query**: Days between contact and MQL conversion

| Metric | Days |
|--------|------|
| Median | 1 |
| 75th Percentile | 7 |
| 90th Percentile | 39 |
| 95th Percentile | 111 |
| 99th Percentile | 343 |
| Maximum | 573 |

**Key Insights**:
- **50% of conversions happen within 1 day** - very fast initial response
- 75% convert within 1 week
- 90% convert within ~6 weeks
- Long tail: Some conversions take up to 573 days (likely recycled leads)

**Recommendations**:
- **Maturity Window**: Use 90 days for model training (covers 90% of conversions)
- Consider separate models for "fast" vs "slow" converters
- Long-tail conversions may be from recycled leads - investigate FilterDate relationship

---

### 1.3 Conversion Rate by Lead Source

**Query**: Overall conversion rates by lead source (top 20)

| Lead Source | Total Contacted | MQL Conversions | Conversion Rate % | % of Total |
|-------------|----------------|-----------------|-------------------|------------|
| Provided Lead List | 36,232 | 980 | 2.70% | 63.0% |
| LinkedIn (Self Sourced) | 19,547 | 1,100 | 5.63% | 34.0% |
| Provided Lead List (Marketing) | 548 | 7 | 1.28% | 1.0% |
| Unknown | 274 | 14 | 5.11% | 0.5% |
| Event | 183 | 37 | 20.22% | 0.3% |
| RB2B | 168 | 11 | 6.55% | 0.3% |
| Advisor Waitlist | 149 | 89 | 59.73% | 0.3% |
| Direct Traffic | 113 | 1 | 0.88% | 0.2% |
| Recruitment Firm | 88 | 72 | 81.82% | 0.2% |
| Re-Engagement | 68 | 22 | 32.35% | 0.1% |
| Other | 45 | 18 | 40.00% | 0.1% |
| Dover | 38 | 16 | 42.11% | 0.1% |
| Ashby | 25 | 19 | 76.00% | 0.0% |
| Advisor Referral | 17 | 16 | 94.12% | 0.0% |
| LinkedIn (Automation) | 8 | 6 | 75.00% | 0.0% |
| LinkedIn (Content) | 5 | 2 | 40.00% | 0.0% |
| Manatal | 4 | 2 | 50.00% | 0.0% |
| Reddit | 4 | 0 | 0.00% | 0.0% |
| LinkedIn Lead Gen Form | 4 | 2 | 50.00% | 0.0% |
| Employee Referral | 2 | 1 | 50.00% | 0.0% |

**Key Insights**:
- **LinkedIn Self Sourced** has 2.1x higher conversion rate (5.63%) than Provided Lead List (2.70%)
- High-intent sources (Advisor Referral 94%, Recruitment Firm 82%, Advisor Waitlist 60%) have very high conversion but small volumes
- **Provided Lead List** dominates volume (63%) but has lowest conversion rate
- **Event** leads convert at 20% - strong signal

**Recommendations**:
- **Lead source is a critical feature** - high predictive power
- Consider separate models for different source categories
- Monitor source distribution drift (see 1.4)

---

### 1.4 Lead Source Distribution Drift Over Time

**Query**: Lead source mix by quarter (showing distribution shift)

**Key Findings** (Selected Quarters):

| Quarter | Lead Source | Count | % of Quarter |
|---------|-------------|-------|--------------|
| 2024 Q1 | Provided Lead List | 218 | 94.0% |
| 2024 Q1 | LinkedIn (Self Sourced) | 4 | 1.7% |
| 2024 Q4 | Provided Lead List | 6,959 | 80.0% |
| 2024 Q4 | LinkedIn (Self Sourced) | 1,648 | 18.9% |
| 2025 Q1 | Provided Lead List | 4,186 | 64.5% |
| 2025 Q1 | LinkedIn (Self Sourced) | 2,150 | 33.2% |
| 2025 Q4 | **LinkedIn (Self Sourced)** | **8,312** | **52.9%** |
| 2025 Q4 | Provided Lead List | 6,484 | 41.3% |

**Key Insights**:
- **Massive distribution shift**: LinkedIn Self Sourced grew from 1.7% (Q1 2024) to 52.9% (Q4 2025)
- Provided Lead List declined from 94% (Q1 2024) to 41.3% (Q4 2025)
- This is the **V2 failure mode** - model trained on old distribution failed on new distribution

**Critical Recommendations**:
- **Must account for lead source drift** in model design
- Use time-based train/test splits that reflect current distribution
- Consider ensemble models or separate models by source category
- Monitor source distribution continuously
- **Feature importance may shift** as source mix changes

---

## Phase 2: Feature Availability & Quality

### 2.1 CRD Match Rate Analysis

**Query**: How many leads can be enriched with FINTRX data?

| Metric | Count | Percentage |
|--------|-------|------------|
| Total Leads | 57,524 | 100% |
| Matched Leads | 50,775 | 88.3% |
| Unmatched Leads | 6,749 | 11.7% |

**Key Insights**:
- **88.3% match rate** - excellent coverage for feature engineering
- 11.7% of leads cannot be enriched - need to handle missing FINTRX data

**Recommendations**:
- Create "has_fintrx_match" indicator feature
- Use FINTRX features for 88% of leads, fallback to Salesforce-only features for 12%
- Consider imputation strategies for missing FINTRX data

---

### 2.2 Employment History Coverage

**Query**: Can we calculate tenure/mobility for matched leads?

| Metric | Count | Percentage |
|--------|-------|------------|
| Leads with CRD | 53,054 | 100% |
| Has Employment History | 40,688 | 76.7% |
| Missing Employment History | 12,366 | 23.3% |

**Key Insights**:
- **76.7% coverage** for employment history features (tenure, mobility)
- 23.3% missing - need to handle missing values

**Recommendations**:
- Mobility features can be calculated for ~77% of leads
- Use "has_employment_history" flag
- Consider proxy features for missing employment data

---

### 2.3 Key Feature Null Rates

**Query**: Null rates for important FINTRX features

| Feature | Null Rate % | Notes |
|---------|-------------|-------|
| Industry Tenure Months | 6.1% | Low null rate - good |
| Primary Firm | 0% | Always present |
| Firm AUM | 30.2% | **High null rate** - need strategy |
| Email | 41.1% | **High null rate** - common |
| LinkedIn Profile URL | 22.8% | Moderate null rate |
| Licenses | 7.4% | Low null rate |
| Title Name | 1.3% | Very low null rate |
| Contact Bio | 0% | Always present |
| Producing Advisor | 0% | Always present (boolean) |

**Key Insights**:
- **Firm AUM has 30% null rate** - significant missing data
- Email and LinkedIn have high null rates but may not be critical for model
- Most core features (tenure, title, bio) have low null rates

**Recommendations**:
- Create "has_firm_aum" indicator
- Consider firm size categories instead of exact AUM
- Use median/mode imputation for AUM with indicator flag
- Email/LinkedIn nulls may be acceptable if not used as features

---

## Phase 3: Feature-Target Relationships (Univariate Analysis)

### 3.1 Conversion by Industry Tenure Buckets

**Query**: Does experience predict conversion?

| Experience Bucket | N Leads | N Converted | Conversion Rate % | Lift vs Baseline |
|-------------------|---------|-------------|-------------------|------------------|
| Unknown | 6,816 | 448 | 6.57% | 1.56x |
| 0-5 years | 3,570 | 180 | 5.04% | 1.20x |
| 5-10 years | 10,334 | 488 | 4.72% | 1.12x |
| 10-15 years | 11,609 | 470 | 4.05% | 0.96x |
| 15-20 years | 8,922 | 352 | 3.95% | 0.94x |
| 20+ years | 16,273 | 478 | 2.94% | 0.70x |

**Key Insights**:
- **Inverse relationship**: More experience = lower conversion rate
- **Unknown/0-5 years** have highest conversion (6.57%, 5.04%)
- **20+ years** have lowest conversion (2.94%)
- Sweet spot appears to be **0-10 years** (5.04-4.72%)

**Recommendations**:
- **Experience is a strong feature** - inverse relationship with conversion
- Consider non-linear encoding (buckets or polynomial)
- "Unknown" category has high conversion - may indicate data quality issue or different population

---

### 3.2 Conversion by Mobility (Prior Moves in 3 Years)

**Query**: Does mobility predict conversion? (Key V3 signal)

| Mobility Tier | N Leads | N Converted | Conversion Rate % | Lift vs Baseline |
|---------------|---------|-------------|-------------------|------------------|
| 0 moves (Stable) | 53,716 | 2,098 | 3.91% | 0.93x |
| 1 move | 2,820 | 219 | 7.77% | 1.85x |
| 2 moves | 748 | 69 | 9.22% | 2.20x |
| 3+ moves (Highly Mobile) | 240 | 30 | 12.50% | **2.98x** |

**Key Insights**:
- **Mobility is the strongest univariate predictor** - 2.98x lift for 3+ moves
- Clear positive relationship: More moves = higher conversion
- **1 move**: 1.85x lift
- **2 moves**: 2.20x lift
- **3+ moves**: 2.98x lift (highest)

**Critical Recommendations**:
- **Mobility is a top-tier feature** - must include in model
- Consider interaction with firm stability (mobile reps at bleeding firms)
- Small sample size for 3+ moves (240 leads) - monitor for stability
- This aligns with V3 rules-based model findings

---

### 3.3 Conversion by Certifications

**Query**: Do certifications predict conversion?

| Feature | Value | N Leads | N Converted | Conversion Rate % | Lift vs Baseline |
|---------|-------|---------|-------------|-------------------|------------------|
| Has CFP | 0 (No) | 55,940 | 2,347 | 4.20% | 1.00x |
| Has CFP | 1 (Yes) | 1,584 | 69 | 4.36% | 1.04x |
| Series 65 Only | 0 (No) | 57,524 | 2,416 | 4.20% | 1.00x |
| Series 65 Only | 1 (Yes) | 0 | 0 | N/A | N/A |

**Key Insights**:
- **CFP has minimal lift** (1.04x) - not a strong predictor
- **Series 65 Only** has no data (query may need adjustment)
- Certifications appear to be weak signals individually

**Recommendations**:
- CFP may be useful in combination with other features
- Re-examine Series 65 detection logic
- Consider license combinations rather than individual licenses
- May need to extract from bio text more carefully

---

### 3.4 Conversion by Wirehouse Flag

**Query**: Wirehouse exclusion was key in V3

| Firm Type | N Leads | N Converted | Conversion Rate % | Lift vs Baseline |
|-----------|---------|-------------|-------------------|------------------|
| Non-Wirehouse | 56,859 | 2,356 | 4.14% | 0.99x |
| Wirehouse | 665 | 60 | 9.02% | **2.15x** |

**Key Insights**:
- **Wirehouse leads convert at 2.15x higher rate** - opposite of V3 exclusion logic!
- This is a **critical finding** - contradicts previous model assumptions
- Wirehouse leads are actually **better** converters, not worse

**Critical Recommendations**:
- **Re-evaluate wirehouse exclusion** - data shows they convert better
- May have been excluded for other reasons (fit, AUM, etc.)
- Include wirehouse flag as feature (positive signal)
- Investigate why V3 excluded wirehouses if they convert better

---

## Phase 4: Potential New Features

### 4.1 Current Tenure at Firm (PIT-Safe)

**Query**: Calculate tenure at firm at time of contact

| Tenure Bucket | N Leads | N Converted | Conversion Rate % | Lift vs Baseline |
|---------------|---------|-------------|-------------------|------------------|
| Unknown | 54,108 | 2,091 | 3.86% | 0.92x |
| 0-1 years | 303 | 42 | 13.86% | 3.30x |
| 1-2 years | 229 | 39 | 17.03% | **4.05x** |
| 2-4 years | 760 | 89 | 11.71% | 2.79x |
| 4-10 years | 1,528 | 117 | 7.66% | 1.82x |
| 10+ years | 596 | 38 | 6.38% | 1.52x |

**Key Insights**:
- **Tenure at firm is a STRONG predictor** - inverse U-shape relationship
- **1-2 years tenure = 4.05x lift** (highest conversion)
- **0-1 years = 3.30x lift** (second highest)
- **10+ years = 1.52x lift** (lowest, but still positive)
- Clear pattern: Short tenure (1-4 years) = high conversion, long tenure = lower conversion

**Critical Recommendations**:
- **Tenure at firm is a top-tier feature** - must include
- Use non-linear encoding (buckets) to capture U-shape
- Interaction with mobility: Short tenure + mobile = very high conversion?
- Small sample sizes for short tenure buckets (303, 229) - monitor

---

### 4.2 Broker Protocol Membership

**Query**: Does broker protocol membership affect conversion?

| BP Status | N Leads | N Converted | Conversion Rate % | Lift vs Baseline |
|-----------|---------|-------------|-------------------|------------------|
| Not BP Member | 56,704 | 2,346 | 4.14% | 0.99x |
| Broker Protocol Member | 820 | 70 | 8.54% | **2.03x** |

**Key Insights**:
- **Broker Protocol members convert at 2.03x higher rate**
- Strong signal - firms that enable transitions produce better leads
- 820 leads (1.4% of total) - small but significant segment

**Recommendations**:
- **Include broker protocol flag** as feature
- May interact with mobility (BP + mobile = very high conversion?)
- Consider firm-level features from broker protocol data

---

## Summary: Top Features by Univariate Lift

| Feature | Max Lift | Key Finding |
|---------|----------|-------------|
| **Tenure at Firm (1-2 years)** | **4.05x** | Short tenure = high conversion |
| **Mobility (3+ moves)** | **2.98x** | Highly mobile = high conversion |
| **Tenure at Firm (0-1 years)** | **3.30x** | Very short tenure = high conversion |
| **Wirehouse** | **2.15x** | Wirehouse = better conversion (contradicts V3) |
| **Broker Protocol** | **2.03x** | BP membership = higher conversion |
| **Mobility (2 moves)** | **2.20x** | Moderate mobility = good conversion |
| **Mobility (1 move)** | **1.85x** | Some mobility = better than stable |
| **Tenure at Firm (2-4 years)** | **2.79x** | Medium tenure = good conversion |
| **Experience (Unknown)** | **1.56x** | Unknown experience = higher conversion |
| **Experience (0-5 years)** | **1.20x** | Less experience = slightly better |

---

## Phase 5: Feature Correlation & Interaction Analysis

### 5.1 Feature Correlation Matrix (Numeric Features)

**Query**: Check for multicollinearity among key numeric features

| Correlation Pair | Correlation Coefficient | Interpretation |
|------------------|------------------------|----------------|
| Experience × Tenure | 0.352 | Moderate positive correlation |
| Experience × Firm AUM | 0.011 | Negligible correlation |
| Tenure × Firm AUM | 0.067 | Weak positive correlation |

**Key Insights**:
- **Experience and Tenure have moderate correlation (0.352)** - not high enough to cause multicollinearity issues
- Firm AUM is largely independent of experience/tenure (0.011, 0.067)
- **No severe multicollinearity** - all features can be included in model

**Recommendations**:
- All three features can be included without concern
- XGBoost handles moderate correlations well
- Consider interaction terms to capture non-linear relationships

---

### 5.2 Mobility × Firm Stability Interaction

**Query**: Key interaction - mobile reps at bleeding firms (PIT-safe calculation)

| Mobility Status | Firm Status | N Leads | N Converted | Conversion Rate % | Lift vs Baseline | Avg Net Change |
|-----------------|-------------|---------|-------------|-------------------|------------------|----------------|
| Mobile | Heavy Bleeding | 108 | 22 | **20.37%** | **4.85x** | -361.6 |
| Mobile | Growing | 84 | 16 | **19.05%** | **4.54x** | 198.2 |
| Mobile | Stable | 20 | 3 | 15.00% | 3.57x | 0.0 |
| Mobile | Light Bleeding | 32 | 4 | 12.50% | 2.98x | -4.1 |
| Mobile | Unknown Firm | 744 | 54 | 7.26% | 1.73x | 0.0 |
| Stable | Light Bleeding | 376 | 44 | 11.70% | 2.79x | -4.1 |
| Stable | Stable | 383 | 44 | 11.49% | 2.74x | 0.0 |
| Stable | Heavy Bleeding | 1,619 | 154 | 9.51% | 2.26x | -455.6 |
| Stable | Growing | 794 | 38 | 4.79% | 1.14x | 255.2 |
| Stable | Unknown Firm | 53,364 | 2,037 | 3.82% | 0.91x | 0.0 |

**Key Insights**:
- **Mobile reps at Heavy Bleeding firms = 4.85x lift (20.37% conversion)** - STRONGEST combination
- **Mobile reps at Growing firms = 4.54x lift (19.05% conversion)** - Also very strong
- **Mobility is the dominant signal** - mobile reps convert well regardless of firm status
- Stable reps at bleeding firms convert better (9.51%, 2.26x) than stable reps at growing firms (4.79%, 1.14x)
- **Counter-intuitive**: Bleeding firms produce better leads (for both mobile and stable reps)

**Critical Findings**:
1. **Mobility dominates** - mobile reps convert 2-5x better regardless of firm status
2. **Bleeding firms are actually better** - leads from bleeding firms convert better than growing firms
3. **Best combination**: Mobile + Heavy Bleeding = 20.37% conversion (4.85x lift)
4. **Second best**: Mobile + Growing = 19.05% conversion (4.54x lift)

**Recommendations**:
- **Mobility is the primary feature** - firm stability is secondary
- Include firm stability as contextual feature, but mobility is the driver
- Consider interaction feature: `mobile_at_bleeding_firm` (mobility >= 2 AND net_change < -10)
- Re-evaluate V3's "bleeding firm" exclusion logic - data shows they convert better

---

### 5.3 Tenure × Mobility Interaction

**Query**: Combined effect of tenure and mobility

| Tenure Bucket | Mobility Bucket | N Leads | N Converted | Conversion Rate % | Lift vs Baseline |
|---------------|----------------|---------|-------------|-------------------|------------------|
| Unknown Tenure | Stable (0 moves) | 51,171 | 1,899 | 3.71% | 0.88x |
| Unknown Tenure | Some Mobility (1 move) | 2,193 | 138 | 6.29% | 1.50x |
| Unknown Tenure | High Mobility (2+ moves) | 744 | 54 | 7.26% | 1.73x |
| Short Tenure (<2yr) | Some Mobility (1 move) | 340 | 44 | 12.94% | 3.08x |
| Short Tenure (<2yr) | High Mobility (2+ moves) | 192 | 37 | 19.27% | **4.59x** |
| Medium Tenure (2-5yr) | Stable (0 moves) | 755 | 79 | 10.46% | 2.49x |
| Medium Tenure (2-5yr) | Some Mobility (1 move) | 278 | 36 | 12.95% | 3.08x |
| Medium Tenure (2-5yr) | High Mobility (2+ moves) | 52 | 8 | 15.38% | 3.66x |
| Long Tenure (5yr+) | Stable (0 moves) | 1,790 | 120 | 6.70% | 1.60x |
| Long Tenure (5yr+) | Some Mobility (1 move) | 9 | 1 | 11.11% | 2.65x |

**Key Insights**:
- **Strongest combination: Short Tenure + High Mobility = 4.59x lift (19.27% conversion)**
- Short Tenure + Some Mobility = 3.08x lift (12.94%)
- Medium Tenure + High Mobility = 3.66x lift (15.38%)
- **Clear pattern**: Short tenure + mobility = highest conversion
- Long tenure + mobility has small sample (9 leads) - unreliable

**Critical Recommendations**:
- **Tenure × Mobility interaction is the strongest signal** - must include
- Create interaction feature: `short_tenure_and_mobile` (tenure < 2yr AND moves >= 2)
- This combination should be top priority for targeting
- Small sample sizes for some combinations - monitor for stability

---

## Phase 6: Sample Size & Statistical Power

### 6.1 Sample Sizes by Key Segments

**Query**: Check if we have enough samples in important segments

| Experience Segment | Mobility Segment | N Leads | N Converted | Conversion Rate % | Sample Size Status |
|-------------------|-----------------|---------|-------------|-------------------|-------------------|
| Other | Mobile | 378 | 32 | 8.47% | ⚠️ Marginal (100≤n<385) |
| Other | Stable | 35,057 | 1,419 | 4.05% | ✅ Sufficient (n>=385) |
| Sweet Spot (5-15yr) | Mobile | 316 | 34 | 10.76% | ⚠️ Marginal (100≤n<385) |
| Sweet Spot (5-15yr) | Stable | 21,773 | 931 | 4.28% | ✅ Sufficient (n>=385) |

**Key Insights**:
- **Mobile segments have marginal sample sizes** (316-378 leads)
  - Sweet Spot + Mobile: 316 leads (⚠️ marginal)
  - Other + Mobile: 378 leads (⚠️ marginal)
- **Stable segments have sufficient samples** (21K-35K leads)
- Overall dataset is large enough (57K+ leads) but mobile segments are smaller

**Recommendations**:
- **Mobile segments need monitoring** - may need more data or regularization
- Consider grouping mobile segments if sample sizes remain small
- Use cross-validation to ensure model stability on mobile segments
- Monitor performance on mobile segments separately in production

---

### 6.2 Overall Sample Size Assessment

**Total Dataset**:
- **57,524 contacted leads** (Jan 2024 - Dec 2025)
- **2,416 MQL conversions** (4.2% positive class)
- **Sufficient for ML model** (rule of thumb: 10-20 samples per feature)

**Segment Breakdown**:
- **Sufficient (n>=385)**: Stable segments, most experience buckets
- **Marginal (100≤n<385)**: Mobile segments, some tenure+mobility combinations
- **Insufficient (n<100)**: Some rare combinations (long tenure + mobility)

**Statistical Power**:
- For 95% confidence, need ~385 samples per segment
- Most segments meet this threshold
- Mobile segments are borderline - monitor closely

**Recommendations**:
- **Overall dataset size is sufficient** for model development
- Use stratified sampling to ensure mobile segments are represented
- Consider ensemble approach if mobile segment models are unstable
- Continue collecting data to strengthen mobile segment models

---

## Summary: Interaction Effects

| Interaction | Max Lift | Key Finding |
|-------------|----------|-------------|
| **Mobile + Heavy Bleeding Firm** | **4.85x** | **STRONGEST** combination (20.37% conversion) |
| **Short Tenure + High Mobility** | **4.59x** | Very strong (19.27% conversion) |
| **Mobile + Growing Firm** | **4.54x** | Very strong (19.05% conversion) |
| **Medium Tenure + High Mobility** | **3.66x** | Strong (15.38% conversion) |
| **Short Tenure + Some Mobility** | **3.08x** | Strong (12.94% conversion) |
| **Medium Tenure + Some Mobility** | **3.08x** | Good (12.95% conversion) |
| **Mobile + Stable Firm** | **3.57x** | Good (15.00% conversion) |
| **Stable + Light Bleeding Firm** | **2.79x** | Moderate (11.70% conversion) |

**Critical Findings**:
1. **Mobile + Heavy Bleeding Firm = 4.85x lift (20.37% conversion)** - STRONGEST signal
2. **Tenure × Mobility interaction is also very strong** - short tenure + high mobility = 4.59x lift
3. **Mobility is the dominant signal** - works well with any firm status (bleeding, growing, stable)
4. **Bleeding firms produce better leads** - contradicts V3 exclusion logic

---

## Data Quality Concerns

1. **Lead Source Drift**: Massive shift from Provided Lead List (94%) to LinkedIn (53%) - must account for in model
2. **Firm AUM Null Rate**: 30% missing - need imputation strategy
3. **Employment History**: 23% missing - affects mobility/tenure features
4. **Recent Conversion Decline**: Nov-Dec 2025 showing 3.18%, 2.43% (down from 4-5%) - investigate
5. **Wirehouse Contradiction**: Data shows wirehouses convert better, but V3 excluded them - investigate reasoning

---

## Recommendations for Model Development

### Feature Engineering

1. **Must-Have Features**:
   - Mobility (moves in 3 years) - **top priority**
   - Tenure at firm (bucketed) - **top priority**
   - Lead source (categorical) - account for drift
   - Broker Protocol membership
   - Wirehouse flag (positive signal)
   - Experience (bucketed, inverse relationship)

2. **Interaction Features** (Priority Order):
   - **Mobility × Firm Bleeding** - **TOP PRIORITY** (4.85x lift for mobile + heavy bleeding)
   - **Tenure × Mobility** - **HIGH PRIORITY** (4.59x lift for short tenure + high mobility)
   - Lead Source × Experience
   - Broker Protocol × Mobility
   - **Create explicit features**:
     - `mobile_at_bleeding_firm` (moves >= 2 AND net_change_12mo < -10)
     - `short_tenure_and_mobile` (tenure < 2yr AND moves >= 2)

3. **Temporal Features**:
   - Days since contact
   - Month/Quarter (seasonality)
   - Time since last activity

### Model Architecture

1. **Train/Test Split**: Use temporal split (train on 2024, test on 2025) to account for source drift
2. **Maturity Window**: 90 days (covers 90% of conversions)
3. **Class Imbalance**: 4.2% positive class - use appropriate sampling or class weights
4. **Feature Selection**: Start with top univariate features, add interactions

### Monitoring

1. **Lead Source Distribution**: Track continuously for drift
2. **Conversion Rate Trends**: Monitor monthly conversion rates
3. **Feature Stability**: Monitor feature distributions over time
4. **Model Performance by Segment**: Track performance by lead source, mobility tier, etc.

---

## Next Steps

1. **Build Feature Engineering Pipeline**: Implement PIT-safe feature extraction
2. **Create Training Dataset**: Filter to contacted leads, 90-day maturity window
3. **Develop XGBoost Model**: Start with top univariate features
4. **Validate on Recent Data**: Test on Q4 2025 to account for source drift
5. **Compare to V3 Rules-Based**: Benchmark against existing model

---

---

## Final Feature Priority Ranking

Based on univariate and interaction analysis:

### Tier 1: Must-Have Features (Strongest Signals)
1. **Mobility × Firm Bleeding Interaction** (4.85x lift) - Mobile + Heavy Bleeding = 20.37% conversion
2. **Tenure × Mobility Interaction** (4.59x lift) - Short tenure + high mobility = 19.27% conversion
3. **Mobility** (2.98x lift) - 3+ moves in 3 years (dominant univariate signal)
4. **Tenure at Firm** (4.05x lift) - 1-2 years tenure
5. **Wirehouse Flag** (2.15x lift) - Positive signal
6. **Broker Protocol** (2.03x lift) - Membership indicator

### Tier 2: Important Features (Moderate Signals)
6. **Lead Source** (2.1x lift for LinkedIn vs Provided List) - Critical for drift handling
7. **Tenure at Firm (0-1 years)** (3.30x lift)
8. **Mobility (2 moves)** (2.20x lift)
9. **Tenure at Firm (2-4 years)** (2.79x lift)

### Tier 3: Supporting Features (Weaker but Useful)
10. **Experience** (inverse relationship, 1.56x lift for unknown)
11. **Firm AUM** (needs imputation strategy)
12. **Certifications** (CFP: 1.04x lift - weak but may help in combinations)

---

**Document Status**: Complete  
**Last Updated**: December 2025  
**Next Review**: After initial model development

