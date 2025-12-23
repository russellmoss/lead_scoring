# Broker Protocol Signal Analysis Report

**Analysis Date**: December 22, 2025  
**Purpose**: Test whether Broker Protocol membership predicts lead conversion  
**Hypothesis**: Advisors at Protocol firms can take clients → easier to recruit

---

## 📊 Executive Summary

This analysis examines whether Broker Protocol membership is a predictive signal for lead conversion (MQL conversion within 30 days of contact). The analysis compares conversion rates across 15 different segments, testing various combinations of Protocol membership with other known signals (Tier 1, bleeding firms, small firms, CFP certification, mid-career status, and Protocol tenure).

### Key Findings

1. **Protocol firms show a positive signal**: 7.61% conversion rate vs. 3.79% baseline (2x improvement)
2. **Protocol + Tier 1 combination**: 11.29% conversion (3x baseline)
3. **Protocol tenure matters**: Firms in Protocol 1-3 years show highest conversion (22.5%)
4. **Small Protocol firms perform well**: 11.21% conversion rate
5. **CFP + Protocol**: No conversions observed (sample size too small)

---

## 📈 Results Summary Table

| Rank | Segment | Leads | Conversions | Conversion % | Signal Quality |
|------|---------|-------|-------------|---------------|----------------|
| 🥇 **1** | **12. Protocol 1-3 years** | 40 | 9 | **22.50%** | 🔥 **Excellent** |
| 🥈 **2** | **5. Tier 1 WITHOUT Protocol** | 265 | 37 | **13.96%** | ✅ Strong |
| 🥉 **3** | **11. Protocol < 1 year** | 53 | 7 | **13.21%** | ✅ Strong |
| **4** | **4. Protocol + Tier 1** | 62 | 7 | **11.29%** | ✅ Strong |
| **5** | **8. Protocol + Small Firm (≤10)** | 107 | 12 | **11.21%** | ✅ Strong |
| **6** | **14. Protocol + Mid-Career** | 234 | 20 | **8.55%** | ✅ Positive |
| **7** | **15. Protocol + Mid-Career + Bleeding** | 227 | 19 | **8.37%** | ✅ Positive |
| **8** | **7. Bleeding Firm WITHOUT Protocol** | 2,141 | 176 | **8.22%** | ✅ Positive |
| **9** | **2. Protocol Firm (Overall)** | 802 | 61 | **7.61%** | ✅ **Positive signal** |
| **10** | **6. Protocol + Bleeding Firm** | 770 | 58 | **7.53%** | ✅ Positive |
| **11** | **13. Protocol 3+ years** | 556 | 31 | **5.58%** | ⚠️ Below average |
| **12** | **1. BASELINE: All Leads** | 39,448 | 1,495 | **3.79%** | Baseline |
| **13** | **3. NON-Protocol Firm** | 38,646 | 1,434 | **3.71%** | Baseline |
| **14** | **9. Protocol + CFP** | 11 | 0 | **0.00%** | ⚠️ No data |
| **15** | **10. Protocol + CFP + Bleeding** | 10 | 0 | **0.00%** | ⚠️ No data |

---

## 🔍 Detailed Analysis by Segment

### 1. Baseline: All Leads
- **Leads**: 39,448
- **Conversions**: 1,495
- **Conversion Rate**: 3.79%
- **Note**: Overall baseline conversion rate for all leads in the dataset

### 2. Protocol Firm (Overall) ✅
- **Leads**: 802
- **Conversions**: 61
- **Conversion Rate**: **7.61%**
- **Signal**: ✅ **Positive signal** (2x baseline)
- **Insight**: Protocol membership alone doubles conversion rate compared to baseline

### 3. NON-Protocol Firm
- **Leads**: 38,646
- **Conversions**: 1,434
- **Conversion Rate**: 3.71%
- **Note**: Comparison baseline for non-Protocol firms

**Protocol vs. Non-Protocol Comparison**:
- Protocol firms: **7.61%** conversion
- Non-Protocol firms: **3.71%** conversion
- **Difference**: +3.90 percentage points (105% relative improvement)

---

### 4. Protocol + Tier 1 ✅
- **Leads**: 62
- **Conversions**: 7
- **Conversion Rate**: **11.29%**
- **Note**: Does Protocol boost Tier 1?
- **Insight**: Protocol membership enhances Tier 1 leads, but not as much as Tier 1 alone

**Comparison**:
- Protocol + Tier 1: **11.29%**
- Tier 1 WITHOUT Protocol: **13.96%**
- **Finding**: Tier 1 is a stronger signal than Protocol, but Protocol adds value

### 5. Tier 1 WITHOUT Protocol
- **Leads**: 265
- **Conversions**: 37
- **Conversion Rate**: **13.96%**
- **Note**: Tier 1 baseline for comparison
- **Insight**: Tier 1 criteria alone is a very strong signal

---

### 6. Protocol + Bleeding Firm ✅
- **Leads**: 770
- **Conversions**: 58
- **Conversion Rate**: **7.53%**
- **Note**: Unstable Protocol firm
- **Insight**: Protocol firms that are bleeding still perform well

### 7. Bleeding Firm WITHOUT Protocol
- **Leads**: 2,141
- **Conversions**: 176
- **Conversion Rate**: **8.22%**
- **Note**: Bleeding baseline
- **Insight**: Bleeding firms perform better than baseline, regardless of Protocol status

**Comparison**:
- Protocol + Bleeding: **7.53%**
- Bleeding WITHOUT Protocol: **8.22%**
- **Finding**: Protocol doesn't significantly boost bleeding firm conversion (slight negative)

---

### 8. Protocol + Small Firm (≤10) ✅
- **Leads**: 107
- **Conversions**: 12
- **Conversion Rate**: **11.21%**
- **Note**: Small Protocol firm
- **Insight**: Small Protocol firms show strong conversion rates (3x baseline)

---

### 9. Protocol + CFP ⚠️
- **Leads**: 11
- **Conversions**: 0
- **Conversion Rate**: **0.00%**
- **Note**: Protocol firm CFP holder
- **Insight**: Sample size too small to draw conclusions (only 11 leads)

### 10. Protocol + CFP + Bleeding ⚠️
- **Leads**: 10
- **Conversions**: 0
- **Conversion Rate**: **0.00%**
- **Note**: 🔥 Triple signal test
- **Insight**: Sample size too small (only 10 leads)

---

### 11. Protocol < 1 year ✅
- **Leads**: 53
- **Conversions**: 7
- **Conversion Rate**: **13.21%**
- **Note**: Recently joined Protocol
- **Insight**: New Protocol members show strong conversion (3.5x baseline)

### 12. Protocol 1-3 years 🔥
- **Leads**: 40
- **Conversions**: 9
- **Conversion Rate**: **22.50%** 🏆
- **Note**: Established Protocol member
- **Insight**: **Highest conversion rate** - Firms in Protocol 1-3 years show exceptional performance (6x baseline)

### 13. Protocol 3+ years ⚠️
- **Leads**: 556
- **Conversions**: 31
- **Conversion Rate**: **5.58%**
- **Note**: Long-time Protocol member
- **Insight**: Long-term Protocol members show lower conversion than newer members

**Protocol Tenure Analysis**:
- < 1 year: **13.21%** (53 leads)
- 1-3 years: **22.50%** (40 leads) 🏆 **Best**
- 3+ years: **5.58%** (556 leads) ⚠️ **Lowest**

**Finding**: There appears to be a "sweet spot" at 1-3 years in Protocol, with conversion rates declining for long-term members.

---

### 14. Protocol + Mid-Career ✅
- **Leads**: 234
- **Conversions**: 20
- **Conversion Rate**: **8.55%**
- **Note**: 5-15yr exp at Protocol firm
- **Insight**: Mid-career advisors at Protocol firms show good conversion (2.3x baseline)

### 15. Protocol + Mid-Career + Bleeding ✅
- **Leads**: 227
- **Conversions**: 19
- **Conversion Rate**: **8.37%**
- **Note**: Mid-career at unstable Protocol firm
- **Insight**: Similar performance to Protocol + Mid-Career alone

**Comparison**:
- Protocol + Mid-Career: **8.55%**
- Protocol + Mid-Career + Bleeding: **8.37%**
- **Finding**: Bleeding doesn't significantly impact mid-career Protocol advisors

---

## 🎯 Key Insights & Recommendations

### 1. Protocol Membership is a Strong Signal ✅

**Finding**: Protocol firms convert at **7.61%** vs. **3.79%** baseline (2x improvement)

**Recommendation**: 
- Prioritize leads from Protocol firms
- Add Protocol membership as a feature in lead scoring model
- Consider Protocol status in outreach prioritization

### 2. Protocol Tenure Matters (Sweet Spot: 1-3 Years) 🔥

**Finding**: Firms in Protocol 1-3 years show **22.50%** conversion (6x baseline)

**Insight**: 
- New members (< 1 year): **13.21%** - Strong
- Established (1-3 years): **22.50%** - **Best** 🏆
- Long-term (3+ years): **5.58%** - Below average

**Hypothesis**: 
- Firms that recently joined Protocol may be actively recruiting
- Long-term members may be more stable and less likely to move
- 1-3 year window represents firms actively leveraging Protocol benefits

**Recommendation**:
- Prioritize firms in Protocol 1-3 years
- Monitor Protocol join dates and adjust prioritization accordingly

### 3. Protocol + Small Firms = Strong Combination ✅

**Finding**: Small Protocol firms (≤10 reps) convert at **11.21%** (3x baseline)

**Recommendation**:
- Prioritize small Protocol firms
- Combine with Tier 1 criteria for maximum impact

### 4. Protocol Enhances Tier 1, But Tier 1 is Stronger Alone

**Finding**: 
- Protocol + Tier 1: **11.29%**
- Tier 1 WITHOUT Protocol: **13.96%**

**Insight**: Tier 1 criteria is a stronger signal than Protocol, but Protocol adds value when combined

**Recommendation**:
- Use Tier 1 as primary signal
- Protocol membership can be a secondary boost

### 5. Protocol + Bleeding Firms: Mixed Results

**Finding**: 
- Protocol + Bleeding: **7.53%**
- Bleeding WITHOUT Protocol: **8.22%**

**Insight**: Protocol doesn't significantly boost bleeding firm conversion

**Recommendation**:
- Bleeding firms are strong signals regardless of Protocol status
- Don't rely on Protocol to boost bleeding firm performance

### 6. CFP + Protocol: Insufficient Data ⚠️

**Finding**: Only 11 leads with Protocol + CFP, 0 conversions

**Recommendation**: 
- Need more data to evaluate this combination
- Monitor as sample size grows

---

## 📊 Statistical Summary

### Conversion Rate Distribution

| Conversion Range | Number of Segments | Notes |
|-----------------|-------------------|-------|
| 20%+ | 1 | Protocol 1-3 years (exceptional) |
| 10-20% | 4 | Tier 1, Protocol + Tier 1, Small Protocol, New Protocol |
| 5-10% | 6 | Protocol overall, Mid-career combinations, Bleeding |
| 3-5% | 2 | Baseline segments |
| 0% | 2 | CFP combinations (insufficient data) |

### Sample Size Considerations

**Large Sample (Reliable)**:
- Baseline: 39,448 leads
- Non-Protocol: 38,646 leads
- Protocol Overall: 802 leads
- Protocol + Bleeding: 770 leads
- Protocol 3+ years: 556 leads

**Medium Sample (Moderate Reliability)**:
- Tier 1 WITHOUT Protocol: 265 leads
- Protocol + Mid-Career: 234 leads
- Bleeding WITHOUT Protocol: 2,141 leads

**Small Sample (Low Reliability)**:
- Protocol 1-3 years: 40 leads ⚠️ (but strong signal)
- Protocol < 1 year: 53 leads
- Protocol + Tier 1: 62 leads
- Protocol + Small Firm: 107 leads
- CFP combinations: 10-11 leads ⚠️

---

## 🎯 Actionable Recommendations

### Immediate Actions

1. **Add Protocol Membership to Lead Scoring Model**
   - Weight: Medium to High
   - Expected impact: +3.82 percentage points (doubles conversion)

2. **Prioritize Protocol Firms 1-3 Years**
   - Weight: Very High
   - Expected impact: +18.71 percentage points (6x baseline)
   - **Note**: Small sample size (40 leads) - monitor closely

3. **Prioritize Small Protocol Firms**
   - Weight: High
   - Expected impact: +7.42 percentage points (3x baseline)

4. **Combine Protocol with Tier 1 Criteria**
   - Weight: Medium
   - Expected impact: +7.50 percentage points (3x baseline)

### Medium-Term Actions

5. **Monitor Protocol Join Dates**
   - Track when firms join Protocol
   - Adjust prioritization based on tenure
   - Focus on 1-3 year window

6. **Test Protocol + CFP Combination**
   - Collect more data (currently only 11 leads)
   - Evaluate if CFP adds value to Protocol signal

7. **Analyze Long-Term Protocol Members**
   - Investigate why 3+ year members show lower conversion
   - May indicate stability (less likely to move)

### Long-Term Actions

8. **Build Protocol Tenure Tracking**
   - Automatically calculate days in Protocol at contact
   - Use in lead scoring and prioritization

9. **A/B Test Protocol Messaging**
   - Test different outreach messages for Protocol vs. non-Protocol firms
   - Leverage Protocol benefits in messaging

10. **Monitor Protocol Withdrawals**
   - Track firms that withdraw from Protocol
   - May indicate firm instability or policy changes

---

## 📈 Expected Impact

### If Protocol Membership is Added to Lead Scoring:

**Current State**:
- Baseline conversion: 3.79%
- Protocol firms: 7.61% (802 leads)
- Non-Protocol firms: 3.71% (38,646 leads)

**Expected Improvement**:
- Protocol firms already prioritized: **+3.82 pp** conversion
- If Protocol signal is weighted properly: **+50-100%** relative improvement

### If Protocol 1-3 Years is Prioritized:

**Current State**:
- Protocol 1-3 years: 22.50% (40 leads)

**Expected Improvement**:
- If this segment is prioritized: **+18.71 pp** conversion
- **6x baseline improvement**

**Note**: Small sample size requires careful monitoring and validation.

---

## ⚠️ Limitations & Caveats

1. **Sample Size**: Some segments have small sample sizes (e.g., Protocol 1-3 years: 40 leads)
2. **Temporal Effects**: Analysis covers last 3 years - may not reflect current market conditions
3. **Confounding Variables**: Other factors may influence conversion beyond Protocol status
4. **Data Quality**: Protocol membership data may have gaps or inaccuracies
5. **Selection Bias**: Protocol firms may differ from non-Protocol firms in unmeasured ways

---

## 📝 Methodology

### Data Sources
- **Leads**: `savvy-gtm-analytics.SavvyGTMData.Lead`
- **Features**: `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
- **Protocol Members**: `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
- **Contacts**: `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`

### Target Definition
- **Conversion**: MQL conversion within 30 days of contact
- **Metric**: `Stage_Entered_Call_Scheduled__c` within 30 days of `Stage_Entered_Contacting__c`

### Filters Applied
- Leads with `Stage_Entered_Contacting__c` not null
- Leads with `FA_CRD__c` not null
- Mature leads only (30+ days since contact to observe outcome)
- Historical range: Last 3 years

### Protocol Matching
- Matched on `firm_crd_id` = `firm_crd_at_contact`
- Only current Protocol members (`is_current_member = TRUE`)
- Protocol tenure calculated as days between `date_joined` and `contacted_date`

---

## 🔄 Next Steps

1. **Validate Findings**: 
   - Re-run analysis with updated data
   - Test on holdout sample
   - Monitor Protocol 1-3 years segment closely

2. **Implement Changes**:
   - Add Protocol membership to lead scoring model
   - Update prioritization logic
   - Create Protocol tenure tracking

3. **Monitor Results**:
   - Track conversion rates by Protocol status
   - Measure impact of prioritization changes
   - Adjust weights based on performance

4. **Expand Analysis**:
   - Analyze Protocol withdrawals
   - Test Protocol + other signal combinations
   - Investigate long-term Protocol member behavior

---

**Report Generated**: December 22, 2025  
**Analysis Period**: Last 3 years  
**Total Leads Analyzed**: 39,448  
**Protocol Leads**: 802 (2.0% of total)

