# V12 Feature Insights: What Signals MQL Conversion?

**Generated:** November 5, 2025  
**Purpose:** Understand what business signals indicate higher MQL conversion rates  
**Data Source:** V6 Training Dataset (2024-2025)

---

## Key Findings Summary

### 🎯 **Critical Insight: Lower Firm Stability = Higher MQL Rate**

**Firm Stability Score (MQL Conversion Rates):**

| Stability Level | MQL Rate | Total Leads | Interpretation |
|----------------|----------|-------------|----------------|
| **Low Stability (< 30%)** | **7.07%** | 1,145 | **Highest conversion** - Unstable advisors are actively looking |
| Moderate Stability (30-60%) | 5.42% | 2,416 | Medium conversion |
| High Stability (60-90%) | 3.89% | 3,800 | Lower conversion |
| **Very High Stability (90%+)** | **2.53%** | 29,293 | **Lowest conversion** - Very stable, less likely to move |
| Missing/Zero | 6.10% | 5,249 | Missing data treated as signal |

**Key Insight:** Advisors with **lower firm stability** (more firm moves, shorter tenures) are **2.8x more likely** to convert to MQL than highly stable advisors.

**Why This Makes Sense:**
- Advisors who move frequently are actively exploring options
- They're more open to meetings and new opportunities
- High stability advisors are satisfied and less likely to engage

---

## Regulatory Disclosures Analysis

| Disclosure Status | MQL Rate | Total Leads | Interpretation |
|-------------------|----------|-------------|----------------|
| **Unknown/Missing** | **9.84%** | 945 | **Highest conversion** - Missing data may indicate newer advisors |
| **Has Disclosures** | **3.24%** | 40,958 | Lower conversion - More established, may be risk-averse |

**Key Insight:** Advisors with **unknown disclosure status** have **3x higher** MQL rate.

**Possible Explanations:**
- Missing disclosure data may indicate newer advisors (more open to opportunities)
- Advisors with disclosures may be more cautious about new relationships
- Data quality artifact (missing data = signal)

---

## Average Tenure at Prior Firms

| Average Tenure Bin | MQL Rate | Total Leads | Avg Years | Interpretation |
|-------------------|----------|-------------|-----------|----------------|
| **< 2 years avg** | **4.30%** | 5,610 | 1.2 | **Highest conversion** - Job hoppers, actively exploring |
| 2-5 years avg | 3.89% | 15,652 | 3.14 | Moderate tenure |
| 5-10 years avg | 2.77% | 8,673 | 6.54 | Longer tenure |
| **10+ years avg** | **1.99%** | 2,458 | 13.91 | **Lowest conversion** - Very stable at prior firms |
| Missing | 3.08% | 8,987 | - | Missing data |
| Zero (No Prior Firms) | 1.15% | 523 | 0 | First firm (career starters) |

**Key Insight:** Advisors with **short average tenure (< 2 years)** at prior firms have **2.2x higher** MQL rate than those with very long tenure (10+ years).

**Pattern Confirmed:** More movement = more openness to opportunities.

---

## Years at Prior Firm 1 (Most Recent Prior Firm)

| Prior Firm 1 Tenure | MQL Rate | Total Leads | Avg Years | Interpretation |
|---------------------|----------|-------------|-----------|----------------|
| **< 3 years** | **3.96%** | 12,800 | 1.2 | **Highest conversion** - Recent job hoppers |
| 3-7 years | 3.62% | 11,810 | 4.24 | Moderate tenure |
| **No Prior Firm 1** | **3.08%** | 8,987 | - | First firm (career starters) |
| **7+ years** | **2.54%** | 8,306 | 11.07 | **Lowest conversion** - Stable at prior firm |

**Key Insight:** Shorter tenure at prior firm = higher MQL rate. Advisors who spent < 3 years at their prior firm are **1.56x more likely** to convert than those with 7+ years.

**Pattern:** More movement = more openness to new opportunities.

---

## Gender Analysis

| Gender | Feature Importance | Weight | MQL Rate | Interpretation |
|--------|-------------------|--------|----------|----------------|
| **Female** | 10.41% | 10.41% | Need to query | Top 5 feature |
| **Male** | 9.42% | 9.42% | Need to query | Top 7 feature |

**Note:** Both gender features are in top 10, indicating gender is a signal. However, Gender field is not available in V6 dataset (may have been dropped during PII removal).

**Important Considerations:**
- Gender may be a proxy for other factors (firm type, AUM level, advisor role, etc.)
- **Ethical concern:** Using gender as a predictive feature may introduce bias
- **Recommendation:** Investigate why gender is a signal - is it causation or correlation?
- Consider dropping gender features if they're not causally related to MQL conversion

---

## Feature Correlation Analysis

### Correlation Between Tenure Features

| Feature 1 | Feature 2 | Correlation | Interpretation |
|-----------|-----------|-------------|----------------|
| `Number_YearsPriorFirm1` | `AverageTenureAtPriorFirms` | **0.777** | **Highly correlated** - Should bin or combine |
| `Number_YearsPriorFirm1` | `Number_YearsPriorFirm2` | 0.261 | Low correlation - OK to keep separate |
| `AverageTenureAtPriorFirms` | `Firm_Stability_Score` | 0.025 | Very low correlation - Independent signals |

### Recommendation: **BIN TENURE FEATURES**

**Why:**
1. **High Correlation (0.777):** `Number_YearsPriorFirm1` and `AverageTenureAtPriorFirms` are highly correlated
2. **Redundancy:** `Number_YearsPriorFirm1-4` are similar signals (just different prior firms)
3. **Better Interpretability:** Binned categories are easier to understand and act on
4. **Reduced Overfitting:** Fewer correlated features = less overfitting risk

**Proposed Bins:**

```sql
-- Average Tenure at Prior Firms
CASE 
    WHEN AverageTenureAtPriorFirms IS NULL OR AverageTenureAtPriorFirms = 0 THEN 'No Prior Firms'
    WHEN AverageTenureAtPriorFirms < 2 THEN 'Short Tenure (< 2 years)'
    WHEN AverageTenureAtPriorFirms < 5 THEN 'Moderate Tenure (2-5 years)'
    WHEN AverageTenureAtPriorFirms < 10 THEN 'Long Tenure (5-10 years)'
    ELSE 'Very Long Tenure (10+ years)'
END as avg_tenure_category

-- Years at Prior Firm 1 (Most Recent)
CASE 
    WHEN Number_YearsPriorFirm1 IS NULL THEN 'No Prior Firm 1'
    WHEN Number_YearsPriorFirm1 < 3 THEN 'Short (< 3 years)'
    WHEN Number_YearsPriorFirm1 < 7 THEN 'Moderate (3-7 years)'
    ELSE 'Long (7+ years)'
END as prior_firm1_category

-- Years at Prior Firm 2-4 (can combine or use same bins)
-- Option: Combine into single "Prior Firm Tenure Pattern" feature
```

---

## Business Interpretation: What Makes an Advisor More Likely to Convert?

### High MQL Conversion Signals (Ranked by Strength)

1. **Unknown Regulatory Disclosures** - **9.84% MQL rate** (3x baseline)
   - **Interpretation:** Missing disclosure data is a strong signal
   - **Action:** Treat missing disclosure data as positive signal
   - **Note:** May indicate newer advisors or data quality issues

2. **Low Firm Stability (< 30%)** - **7.07% MQL rate** (2.8x high stability)
   - **Interpretation:** Advisors who move frequently are actively exploring
   - **Action:** Prioritize advisors with recent firm changes
   - **Formula:** `DateOfHireAtCurrentFirm_NumberOfYears / (NumberOfPriorFirms + 1) < 0.3`

3. **Short Average Tenure at Prior Firms (< 2 years)** - **4.30% MQL rate** (2.2x long tenure)
   - **Interpretation:** Job hoppers are more open to opportunities
   - **Action:** Prioritize advisors with short average tenure across prior firms

4. **Short Tenure at Prior Firm 1 (< 3 years)** - **3.96% MQL rate** (1.56x long tenure)
   - **Interpretation:** Recent job hoppers are actively looking
   - **Action:** Prioritize advisors with short tenure at most recent prior firm

5. **Combination: Short Prior Firm 1 + Short Avg Tenure** - **4.38% MQL rate**
   - **Interpretation:** Consistent pattern of short tenures = high openness
   - **Action:** Highest priority for advisors with both signals

### Low MQL Conversion Signals

1. **Very High Firm Stability (90%+)** - 2.53% MQL rate
   - **Interpretation:** Very stable advisors are satisfied and less likely to engage
   - **Action:** Lower priority unless other strong signals present

2. **Long Tenure at Prior Firm (7+ years)** - 2.54% MQL rate
   - **Interpretation:** Stable at prior firm = less likely to move again
   - **Action:** Lower priority

---

## Recommendations for Feature Engineering

### 1. **Bin Tenure Features** ✅ **HIGH PRIORITY**

**Current Issues:**
- `Number_YearsPriorFirm1-4` are highly correlated with `AverageTenureAtPriorFirms` (0.777)
- Raw numeric values are hard to interpret
- Risk of overfitting to specific year values

**Proposed Solution:**
```python
# Create binned categories
df['avg_tenure_category'] = pd.cut(
    df['AverageTenureAtPriorFirms'], 
    bins=[0, 2, 5, 10, 100],
    labels=['Short (< 2)', 'Moderate (2-5)', 'Long (5-10)', 'Very Long (10+)'],
    include_lowest=True
)

df['prior_firm1_category'] = pd.cut(
    df['Number_YearsPriorFirm1'], 
    bins=[0, 3, 7, 100],
    labels=['Short (< 3)', 'Moderate (3-7)', 'Long (7+)'],
    include_lowest=True
)

# Drop raw numeric features after binning
# Keep: binned categories, Firm_Stability_Score (already engineered)
# Drop: Number_YearsPriorFirm1-4, AverageTenureAtPriorFirms (raw)
```

### 2. **Create Composite Stability Features**

Instead of using all tenure features separately, create:
- `Job_Hopper_Flag`: `AverageTenureAtPriorFirms < 2 AND NumberOfPriorFirms > 2`
- `Recent_Firm_Change`: `DateOfHireAtCurrentFirm_NumberOfYears < 2`
- `Stable_At_Prior_Firms`: `AverageTenureAtPriorFirms >= 7`

### 3. **Investigate Gender Signal**

- Check if gender is a proxy for other factors (AUM level, firm type, etc.)
- Consider dropping if ethical concerns or if it's just correlation
- If keeping, document why it's a signal

### 4. **Regulatory Disclosures**

- Create explicit flag: `Has_Disclosure_Data` (0/1)
- Treat missing as its own category (it's a strong signal)
- Don't impute missing values

---

## Next Steps

1. **✅ Implement Binning:** Modify V12 to bin tenure features
2. **✅ Test Performance:** Compare binned vs raw features
3. **✅ Validate Insights:** Confirm firm stability and tenure patterns hold
4. **✅ Document Gender:** Understand why gender is a signal
5. **✅ Create Business Rules:** Use insights to create lead prioritization rules

---

**Report Generated:** November 5, 2025  
**Status:** ⚠️ **Action Required - Feature Engineering Needed**

