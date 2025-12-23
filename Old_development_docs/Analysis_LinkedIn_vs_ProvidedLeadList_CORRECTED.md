# CORRECTED Statistical Analysis: LinkedIn (Self Sourced) vs. Provided Lead List
## Using TOTAL SQOs (Not Just From Contacted Leads)
## Q1 2024 - Q3 2025

---

## Data Correction Notice

**Previous Analysis Errors:**
1. The initial analysis only counted SQOs that came from contacted leads (`is_contacted = 1`), which excluded SQOs from alternative paths
2. The initial analysis used `FilterDate` for date filtering, but the correct field for SQO attribution is `Date_Became_SQO__c` (as used in `vw_actual_vs_forecast_by_source`)

**Corrected Analysis:** This analysis uses:
- **TOTAL SQOs** regardless of whether they came from contacted leads
- **`Date_Became_SQO__c`** for date attribution (matching `vw_actual_vs_forecast_by_source` view)
- This ensures alignment with the numbers visible in Looker Studio dashboards

---

## Executive Summary

**Which lead source is better, and is the difference statistically significant?**

**Answer: LinkedIn (Self Sourced) produces significantly more SQOs and has a statistically significantly higher SQO rate, but the magnitude of the advantage depends on the denominator used.**

### Primary Finding: Total SQO Production

**For Jan 1 to Sep 30, 2024-2025 (using Date_Became_SQO__c):**
- **LinkedIn (Self Sourced):** 178 total SQOs
- **Provided Lead List:** 166 total SQOs
- **Difference:** LinkedIn produced 12 more SQOs (7% more)

**For Q2 2024 to Q3 2025 (Apr 1 - Sep 30, using Date_Became_SQO__c):**
- **LinkedIn (Self Sourced):** 171 total SQOs
- **Provided Lead List:** 152 total SQOs
- **Difference:** LinkedIn produced 19 more SQOs (13% more)

### Statistical Significance: SQO Rate (All Records)

When comparing SQO rates using total records (filtered by FilterDate) as the denominator, but SQOs filtered by Date_Became_SQO__c:

- **LinkedIn Rate:** 1.30% (176 SQOs from 13,580 total records)*
- **Provided Lead List Rate:** 0.39% (161 SQOs from 41,240 total records)*
- **Difference:** +0.91 percentage points (3.3x higher rate)
- **Z-Score:** 11.71
- **P-Value:** < 0.001 (highly statistically significant)
- **95% Confidence Interval:** +0.75% to +1.06%

*Note: Slight difference from absolute counts (178 vs. 176, 166 vs. 161) due to using FilterDate for denominator vs. Date_Became_SQO__c for numerator. The absolute counts (178 vs. 166) are the correct numbers for comparison.

---

## Analysis 1: Total SQO Production (Absolute Numbers)

### Jan 1 to Sep 30, 2024-2025 (using Date_Became_SQO__c)

| Source | Total SQOs | Total Records* | SQO Rate (All Records) |
|--------|------------|--------------|------------------------|
| **LinkedIn (Self Sourced)** | **178** | 13,580 | **1.31%** |
| **Provided Lead List** | **166** | 41,240 | **0.40%** |
| **Difference** | **+12 SQOs** | -27,660 records | **+0.91%** |

*Total Records filtered by FilterDate (cohort-based attribution)

### Q2 2024 to Q3 2025 (Apr 1 - Sep 30, using Date_Became_SQO__c)

| Source | Total SQOs | Total Records* | SQO Rate (All Records) |
|--------|------------|--------------|------------------------|
| **LinkedIn (Self Sourced)** | **171** | 13,541 | **1.26%** |
| **Provided Lead List** | **152** | 38,753 | **0.39%** |
| **Difference** | **+19 SQOs** | -25,212 records | **+0.87%** |

*Total Records filtered by FilterDate (cohort-based attribution)

### Key Insight

LinkedIn produces more SQOs despite having **67% fewer total records** (13,580 vs. 41,240). This demonstrates superior efficiency at converting records to SQOs.

---

## Analysis 2: Statistical Test - SQO Rate (All Records)

### Two-Proportion Z-Test Results

**Null Hypothesis (H₀):** The SQO rate (SQOs / Total Records) for LinkedIn equals the rate for Provided Lead List

**Alternative Hypothesis (H₁):** The rates are not equal

**Results (Jan 1 to Sep 30, 2024-2025):**
- **LinkedIn Rate:** 1.30% (176 SQOs / 13,580 records)*
- **Provided Lead List Rate:** 0.39% (161 SQOs / 41,240 records)*
- **Rate Difference:** +0.91 percentage points
- **Z-Score:** 11.71
- **P-Value:** < 0.001 (highly statistically significant)
- **95% Confidence Interval:** +0.75% to +1.06%

*Note: For statistical test, denominator uses FilterDate (cohort attribution) while numerator uses Date_Became_SQO__c (when SQO occurred). Absolute counts are 178 vs. 166.

**Conclusion:** We reject the null hypothesis with extremely high confidence (p < 0.001). LinkedIn (Self Sourced) has a statistically significantly higher SQO rate than Provided Lead List when using total records as the denominator.

---

## Analysis 3: SQL → SQO Rate Comparison

### SQL to SQO Conversion Rates

| Source | Total SQLs | Total SQOs | SQL → SQO Rate |
|--------|------------|------------|----------------|
| **LinkedIn (Self Sourced)** | 317 | 184 | **58.04%** |
| **Provided Lead List** | 310 | 167 | **53.87%** |
| **Difference** | +7 SQLs | +17 SQOs | **+4.17%** |

**Note:** This is a different metric than the "Contacted → SQO" rate from the previous analysis. This shows that once leads become SQLs, LinkedIn converts them to SQOs at a slightly higher rate (though this difference would need statistical testing to confirm significance).

---

## Analysis 4: Breakdown of SQOs

### SQOs by Source

| Source | SQOs from Contacted Leads | SQOs NOT from Contacted Leads | Total SQOs |
|--------|---------------------------|------------------------------|------------|
| **LinkedIn (Self Sourced)** | 154 | 30 | **184** |
| **Provided Lead List** | 144 | 23 | **167** |

**Key Finding:** Approximately 16% of LinkedIn SQOs and 14% of Provided Lead List SQOs did not come from contacted leads. This suggests there are alternative paths to SQO that don't require the "contacted" stage.

---

## Comparison: Previous Analysis vs. Corrected Analysis

### Previous Analysis (Contacted → SQO Only)

- **LinkedIn:** 154 SQOs from 12,067 contacted (1.28% rate)
- **Provided Lead List:** 144 SQOs from 30,799 contacted (0.47% rate)
- **Z-Score:** 9.06 (p < 0.001)
- **Conclusion:** LinkedIn significantly better for contacted leads

### Corrected Analysis (Total SQOs)

- **LinkedIn:** 184 total SQOs from 13,580 records (1.35% rate)
- **Provided Lead List:** 167 total SQOs from 41,240 records (0.40% rate)
- **Z-Score:** 12.04 (p < 0.001)
- **Conclusion:** LinkedIn significantly better overall

**Both analyses reach the same conclusion:** LinkedIn (Self Sourced) is statistically significantly better. The corrected analysis using Date_Became_SQO__c shows a strong advantage (z = 11.71, p < 0.001).

---

## Key Findings Summary

1. **Absolute Volume:** LinkedIn produced 178 total SQOs vs. Provided Lead List's 166 SQOs (7% more) for Jan 1 to Sep 30, 2024-2025

2. **Efficiency (All Records):** LinkedIn converts records to SQOs at a **3.3x higher rate** (1.30% vs. 0.39%), and this difference is **highly statistically significant** (z = 11.71, p < 0.001)

3. **Efficiency (Contacted Leads Only):** LinkedIn converts contacted leads to SQOs at a **2.7x higher rate** (1.28% vs. 0.47%), also highly significant (z = 9.06, p < 0.001)

4. **SQL → SQO Rate:** LinkedIn shows a slightly higher rate (58.04% vs. 53.87%), but this needs separate statistical testing

5. **Alternative Paths:** 16% of LinkedIn SQOs and 14% of Provided Lead List SQOs came from non-contacted leads, suggesting multiple paths to SQO

---

## Recommendations

### Based on Total SQO Production

1. **LinkedIn (Self Sourced) is the superior source** for both absolute volume and conversion efficiency

2. **The advantage is robust** - LinkedIn outperforms across multiple metrics:
   - Total SQOs: 184 vs. 167 (+10%)
   - SQO Rate (All Records): 1.35% vs. 0.40% (3.3x higher)
   - SQO Rate (Contacted Only): 1.28% vs. 0.47% (2.7x higher)

3. **Investigation Needed:**
   - Why do 30 LinkedIn SQOs and 23 Provided Lead List SQOs not come from contacted leads?
   - What are these alternative paths to SQO?
   - Should we optimize for these alternative paths?

4. **Cost Analysis Still Critical:** Without Cost Per SQO data, we cannot make final ROI recommendations, but the efficiency advantage is clear.

---

## Limitations

1. **No Cost Data:** This analysis does not include Cost Per Lead (CPL) or Cost Per SQO (CPSQO)

2. **Denominator Choice:** The "SQO Rate (All Records)" uses total records as denominator, which includes leads at all stages. Alternative denominators (e.g., total SQLs, total contacted) yield different rates.

3. **Alternative Paths:** The presence of SQOs not from contacted leads suggests complex conversion paths that need further investigation.

4. **Data Discrepancy:** The user reported slightly different numbers (178 vs. 184 for LinkedIn, 166 vs. 167 for Provided Lead List). This may be due to:
   - Different date filters
   - Different views or data sources
   - Different counting methods

**Recommendation:** Verify the exact query/view the user is using to ensure alignment.

---

*Report Generated: Corrected Analysis Using Total SQOs*
*Date Attribution: Date_Became_SQO__c (matching vw_actual_vs_forecast_by_source)*
*Date Range: Jan 1, 2024 to Sep 30, 2025*
*Data Source: vw_funnel_lead_to_joined_v2*
*Aligned with: vw_actual_vs_forecast_by_source view counts*

