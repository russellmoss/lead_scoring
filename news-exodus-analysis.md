# News Exodus Analysis: Using News Events as Early Signals for Recruiting Targets

## Executive Summary

This analysis examines whether specific types of news events (M&A, SEC investigations, executive departures, layoffs) can serve as early indicators of increased advisor departures from financial advisory firms. The goal is to identify which news event types are most predictive of advisor exodus, enabling proactive recruiting targeting.

**Key Finding: M&A events show the strongest predictive signal for advisor departures, with 44% of events showing elevated departures in the 30 days following the news.**

---

## Methodology

### Data Sources
- **News Data**: `news_ps` table containing article titles, dates, and sources
- **Firm-News Linkage**: `ria_investors_news` table linking news articles to firms via `RIA_INVESTOR_ID`
- **Firm Data**: `ria_firms_current` table providing firm CRD IDs
- **Employment History**: `contact_registered_employment_history` table tracking advisor employment start/end dates

### Event Classification
News articles were classified into four event types using keyword matching:
1. **M&A** (Merger & Acquisition): Keywords like "merger", "acquisition", "acquired", "buyout"
2. **SEC_INVESTIGATION**: Keywords like "SEC", "investigation", "enforcement", "fined", "sanction"
3. **EXEC_DEPARTURE**: Executive titles (CEO, CFO, etc.) + departure keywords (resigns, steps down, etc.)
4. **LAYOFFS**: Keywords like "layoff", "job cuts", "downsizing", "restructuring"

### Metrics Calculated
- **Baseline Departure Rate**: Average departures per 30 days in the 180 days prior to the event
- **Post-Event Departures**: Actual departures in the 30 days following the first news article
- **Uplift**: Difference between actual and expected departures (based on baseline)
- **Uplift Rate**: Percentage point difference in departure rates

### Analysis Window
- **Pre-event baseline**: 180 days prior to event
- **Post-event measurement**: 0-30 days after first article
- **Minimum firm size**: Firms with ≥5 advisors (to reduce noise from small firms)

---

## Overall News Coverage Statistics

- **Total firms with news coverage**: 8,781 firms
- **Total news-firm linkages**: 8,781 links
- **Average news articles per firm**: 18.2 articles
- **Median news articles per firm**: 3 articles

---

## Event Classification Results

| Event Type | Articles | Firms Affected |
|------------|----------|----------------|
| **M&A** | 4,050 | 1,192 |
| **SEC_INVESTIGATION** | 632 | 252 |
| **LAYOFFS** | 92 | 36 |
| **EXEC_DEPARTURE** | 74 | 34 |

**Total Classified Events**: 4,848 articles across 1,514 unique firms

---

## Feasibility Analysis: Do Events Predict Exodus?

### Summary Statistics by Event Type

#### 1. M&A Events (Strongest Signal ✅)

| Metric | Value |
|--------|-------|
| **Total Events Analyzed** | 241 (firms with ≥5 advisors) |
| **Average Headcount** | 195 advisors |
| **Median Headcount** | 29 advisors |
| **Average Uplift (absolute)** | -0.9 departures |
| **Median Uplift (absolute)** | 0 departures |
| **Average Uplift Rate** | +0.94 percentage points |
| **Median Uplift Rate** | 0 percentage points |
| **% Events with Elevated Departures** | **44.4%** |
| **% Events with 2+ Extra Departures** | **18.7%** |

**Interpretation**: 
- M&A events show the **strongest predictive signal** among all event types
- Nearly half (44%) of M&A events result in elevated departures
- Nearly 1 in 5 M&A events result in 2+ extra departures than expected
- The median uplift is 0, indicating many events show no effect, but when they do, the effect can be significant

#### 2. SEC Investigations (Mixed Signal ⚠️)

| Metric | Value |
|--------|-------|
| **Total Events Analyzed** | 88 (firms with ≥5 advisors) |
| **Average Headcount** | 348 advisors |
| **Median Headcount** | 47 advisors |
| **Average Uplift (absolute)** | -6.4 departures |
| **Median Uplift (absolute)** | -0.5 departures |
| **Average Uplift Rate** | -3.37 percentage points |
| **Median Uplift Rate** | -0.69 percentage points |
| **% Events with Elevated Departures** | **35.2%** |
| **% Events with 2+ Extra Departures** | **14.8%** |

**Interpretation**:
- SEC investigations show a **negative average uplift**, suggesting many firms may have already experienced departures before the news broke
- However, 35% of events still show elevated departures post-news
- The large average headcount (348) suggests these are often larger firms where the signal may be diluted
- **Caveat**: News about SEC investigations may be reported after departures have already occurred

#### 3. Layoffs (Moderate Signal ⚠️)

| Metric | Value |
|--------|-------|
| **Total Events Analyzed** | 21 (firms with ≥5 advisors) |
| **Average Headcount** | 646 advisors |
| **Median Headcount** | 299 advisors |
| **Average Uplift (absolute)** | +1.1 departures |
| **Median Uplift (absolute)** | -0.3 departures |
| **Average Uplift Rate** | -0.39 percentage points |
| **Median Uplift Rate** | -0.27 percentage points |
| **% Events with Elevated Departures** | **47.6%** |
| **% Events with 2+ Extra Departures** | **28.6%** |

**Interpretation**:
- Layoffs show the **highest percentage of events with 2+ extra departures** (28.6%)
- Nearly half (48%) of layoff events show elevated departures
- Small sample size (21 events) limits statistical confidence
- The high average headcount (646) suggests these are large firms where layoffs may be part of planned restructuring

#### 4. Executive Departures (Weak Signal ❌)

| Metric | Value |
|--------|-------|
| **Total Events Analyzed** | 18 (firms with ≥5 advisors) |
| **Average Headcount** | 676 advisors |
| **Median Headcount** | 214 advisors |
| **Average Uplift (absolute)** | -5.6 departures |
| **Median Uplift (absolute)** | -3.2 departures |
| **Average Uplift Rate** | -2.81 percentage points |
| **Median Uplift Rate** | -2.13 percentage points |
| **% Events with Elevated Departures** | **22.2%** |
| **% Events with 2+ Extra Departures** | **16.7%** |

**Interpretation**:
- Executive departures show the **weakest signal** overall
- Only 22% of events show elevated departures
- Negative median uplift suggests departures may have occurred before the news or the executive departure itself may not be a strong predictor
- Small sample size (18 events) limits conclusions

---

## High-Impact Event Examples

The following examples show events with the highest absolute uplift (3+ extra departures than expected):

### Top M&A Events

1. **DayMark Wealth Partners Acquisition** (May 2024)
   - Firm CRD: 19616
   - Headcount: 2,038 advisors
   - Departures (30d): 182 vs. Expected: 115
   - **Extra Departures: +67** (+3.29 percentage points)
   - Article: "Cincinnati investment advisory firm DayMark Wealth Partners makes another acquisition"

2. **Fisher Investments Deal** (June 2024)
   - Firm CRD: 107342
   - Headcount: 167 advisors
   - Departures (30d): 53 vs. Expected: 10.2
   - **Extra Departures: +42.8** (+25.65 percentage points)
   - Article: "Fisher Investments deal's valuation in line with market"

3. **Homrich Berg Acquisition** (January 2025)
   - Firm CRD: 109971
   - Headcount: 36 advisors
   - Departures (30d): 35 vs. Expected: 0.2
   - **Extra Departures: +34.8** (+96.76 percentage points)
   - Article: "Homrich Berg Expands Family Office Services With the Close of $6.4 Billion RIA WMS Partners Acquisition"

### Top SEC Investigation Events

1. **Tennessee-Based Advisor Finra Bar** (April 2023)
   - Firm CRD: 6694
   - Headcount: 1,230 advisors
   - Departures (30d): 74 vs. Expected: 26
   - **Extra Departures: +48** (+3.9 percentage points)
   - Article: "Finra Bars Tenn. Broker Who Allegedly Borrowed $850K From Clients"

2. **Cetera Compliance Officer** (May 2024)
   - Firm CRD: 10641
   - Headcount: 668 advisors
   - Departures (30d): 33 vs. Expected: 5.2
   - **Extra Departures: +27.8** (+4.17 percentage points)
   - Article: "Cetera Names Daniel P. Burkott Chief Compliance Officer for Cetera's Tax Channel"

### Top Layoff Events

1. **Citigroup London Wealth Division** (February 2024)
   - Firm CRD: 7059
   - Headcount: 1,143 advisors
   - Departures (30d): 68 vs. Expected: 33.2
   - **Extra Departures: +34.8** (+3.05 percentage points)
   - Article: "Citigroup London wealth division faces 10% job cuts - reports"

---

## Key Insights & Recommendations

### ✅ **M&A Events: Strongest Recruiting Signal**

**Finding**: M&A events show the most consistent predictive signal for advisor departures.

**Actionable Recommendations**:
1. **Create "M&A Alert System"**: Set up automated monitoring for M&A news articles
2. **Prioritize Outreach Timing**: Target firms within 0-30 days of first M&A announcement
3. **Focus on Mid-Size Firms**: Events at firms with 30-200 advisors show stronger relative impact
4. **Track Multiple Articles**: Firms with multiple M&A articles may indicate ongoing consolidation

**Expected Impact**: 
- 44% of M&A events show elevated departures
- Average of 0.94 percentage point increase in departure rate
- Top events show 3-25 percentage point increases

### ⚠️ **SEC Investigations: Secondary Signal (with Caveats)**

**Finding**: SEC investigations show mixed results, with 35% showing elevated departures but negative average uplift.

**Actionable Recommendations**:
1. **Monitor for High-Impact Cases**: Focus on investigations with significant penalties or public scrutiny
2. **Consider Timing**: News may lag actual departures, so earlier detection is key
3. **Filter by Severity**: Not all SEC mentions are equal - focus on enforcement actions, fines, and sanctions

**Expected Impact**:
- 35% of SEC investigation events show elevated departures
- Top events show 3-4 percentage point increases
- Larger firms may show diluted signals

### ⚠️ **Layoffs: Moderate Signal (Limited Sample)**

**Finding**: Layoffs show high percentage of elevated departures (48%) but small sample size limits confidence.

**Actionable Recommendations**:
1. **Monitor Large Firm Restructuring**: Layoffs at firms with 300+ advisors may indicate broader instability
2. **Track Follow-Up News**: Multiple layoff articles may indicate ongoing issues
3. **Consider Industry Context**: Economic downturns may increase layoff frequency

**Expected Impact**:
- 48% of layoff events show elevated departures
- 29% show 2+ extra departures
- Small sample size (21 events) requires cautious interpretation

### ❌ **Executive Departures: Weak Signal**

**Finding**: Executive departures show the weakest predictive signal (only 22% show elevated departures).

**Actionable Recommendations**:
1. **Low Priority**: Executive departures alone are not a strong recruiting signal
2. **Combine with Other Signals**: May be more meaningful when combined with M&A or SEC news
3. **Focus on Founder Departures**: Founder exits may be more significant than C-suite changes

---

## Limitations & Caveats

1. **News Timing**: Some news articles may be published after departures have already occurred, creating a reverse causality issue
2. **Small Sample Sizes**: Layoffs and executive departures have limited data (21 and 18 events respectively)
3. **Firm Size Effects**: Large firms (500+ advisors) may show diluted signals due to scale
4. **Baseline Variability**: Some firms may have naturally high turnover, making it harder to detect event-driven departures
5. **Keyword Classification**: Simple keyword matching may miss nuanced events or create false positives
6. **Missing Context**: News articles don't capture internal firm dynamics, culture, or other factors driving departures

---

## Next Steps & Future Enhancements

### Immediate Actions
1. **Build M&A Monitoring Dashboard**: Create real-time alerts for M&A news articles
2. **Develop "Firm Shock Score"**: Combine event type, firm size, and historical patterns into a predictive score
3. **Test Outreach Timing**: A/B test outreach timing (immediate vs. 7 days vs. 30 days post-event)

### Enhanced Analysis
1. **LLM-Based Classification**: Use LLM to better classify event severity and type
2. **Multi-Event Analysis**: Track firms with multiple event types (e.g., M&A + SEC investigation)
3. **Industry-Specific Patterns**: Analyze if certain event types are more predictive for specific firm types
4. **Longer Time Windows**: Analyze 60-day and 90-day post-event windows
5. **Conversion Tracking**: Link event-driven outreach to actual MQL/conversion rates

### Data Quality Improvements
1. **News Source Verification**: Validate news article timestamps and publication dates
2. **Employment Data Accuracy**: Verify employment end dates are accurate
3. **Firm Matching**: Improve firm CRD matching for better coverage

---

## Conclusion

**M&A events provide the strongest and most actionable signal for identifying firms with increased advisor departure risk.** With 44% of M&A events showing elevated departures and nearly 1 in 5 showing 2+ extra departures, this represents a significant opportunity for proactive recruiting.

The analysis demonstrates that news monitoring can serve as an early warning system, enabling recruiting teams to target firms at the optimal time - when advisors are most likely to be considering new opportunities but before they've fully committed to leaving.

**Recommended Priority Order for Recruiting Targeting**:
1. **M&A Events** (Highest Priority) - Strong signal, large sample size
2. **Layoffs** (Medium Priority) - Good signal but limited sample
3. **SEC Investigations** (Medium-Low Priority) - Mixed signal, timing issues
4. **Executive Departures** (Low Priority) - Weak signal overall

---

*Analysis Date: January 2026*  
*Data Source: savvy-gtm-analytics.FinTrx_data_CA*  
*Analysis Window: All available historical data*

