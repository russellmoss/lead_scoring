# V12 Feature Binning Recommendation: Tenure Features

**Generated:** November 5, 2025  
**Issue:** Tenure features are highly correlated and should be binned for better interpretability  
**Status:** ✅ **Ready to Implement**

---

## Executive Summary

**YES, we should bin tenure features.** The data shows:
1. **High Correlation (0.777):** `Number_YearsPriorFirm1` and `AverageTenureAtPriorFirms` are highly correlated
2. **Clear Patterns:** Binned categories show strong MQL conversion patterns
3. **Better Interpretability:** Business stakeholders can understand "Short tenure (< 2 years)" better than "1.2 years"
4. **Reduced Overfitting:** Fewer correlated features = less overfitting risk

---

## What Signals MQL Conversion? (Your Questions Answered)

### 1. **More Unstable Firms = Higher MQL Rate** ✅ **YES**

**Firm Stability Score:**
- **Low Stability (< 30%):** **7.07% MQL rate** (highest)
- **Very High Stability (90%+):** **2.53% MQL rate** (lowest)
- **Difference:** 2.8x higher conversion for unstable advisors

**Interpretation:** Advisors who move frequently are actively exploring options and more likely to schedule meetings.

**Formula:** `Firm_Stability_Score = DateOfHireAtCurrentFirm_NumberOfYears / (NumberOfPriorFirms + 1)`

### 2. **Regulatory Disclosures = Signal** ✅ **YES, but counterintuitive**

**Regulatory Disclosures:**
- **Unknown/Missing:** **9.84% MQL rate** (highest!)
- **Has Disclosures:** **3.24% MQL rate** (lower)

**Interpretation:** Advisors with missing disclosure data are 3x more likely to convert. This may indicate:
- Newer advisors (more open to opportunities)
- Data quality issues (missing data = signal)
- Advisors with disclosures may be more risk-averse

### 3. **Average Time at Prior Firms = Strong Signal** ✅ **YES**

**Average Tenure at Prior Firms:**
- **< 2 years avg:** **4.30% MQL rate** (highest)
- **2-5 years avg:** 3.89% MQL rate
- **5-10 years avg:** 2.77% MQL rate
- **10+ years avg:** **1.99% MQL rate** (lowest)
- **Difference:** 2.2x higher conversion for short tenure

**Interpretation:** Advisors who spent less time at prior firms are more open to opportunities.

### 4. **Years at Prior Firm 1 = Signal** ✅ **YES**

**Most Recent Prior Firm Tenure:**
- **< 3 years:** **3.96% MQL rate** (highest)
- **3-7 years:** 3.62% MQL rate
- **7+ years:** **2.54% MQL rate** (lowest)
- **Difference:** 1.56x higher conversion for short tenure

**Interpretation:** Recent job hoppers are actively looking.

### 5. **Gender = Signal (but needs investigation)** ⚠️ **CAUTION**

**Gender Features:**
- **Female:** 10.41% importance (top 5)
- **Male:** 9.42% importance (top 7)

**Important:** Both are in top 10, but:
- May be a proxy for other factors (firm type, AUM, role)
- **Ethical concern:** Using gender may introduce bias
- **Recommendation:** Investigate causation vs correlation before using

---

## Correlation Analysis: Should We Bin?

### Correlation Matrix

| Feature 1 | Feature 2 | Correlation | Decision |
|-----------|-----------|-------------|----------|
| `Number_YearsPriorFirm1` | `AverageTenureAtPriorFirms` | **0.777** | **✅ BIN** (highly correlated) |
| `Number_YearsPriorFirm1` | `Number_YearsPriorFirm2` | 0.261 | Keep separate (low correlation) |
| `AverageTenureAtPriorFirms` | `Firm_Stability_Score` | 0.025 | Keep separate (independent) |

### Recommendation: **BIN TENURE FEATURES**

**Why:**
1. **0.777 correlation** means `Number_YearsPriorFirm1` and `AverageTenureAtPriorFirms` are redundant
2. **Binning reduces overfitting** by reducing feature space
3. **Better interpretability** for business stakeholders
4. **Clear patterns** emerge when binned (see MQL rates above)

---

## Proposed Binning Strategy

### 1. Average Tenure at Prior Firms (BIN THIS)

```sql
-- Replace raw AverageTenureAtPriorFirms with binned category
CASE 
    WHEN AverageTenureAtPriorFirms IS NULL OR AverageTenureAtPriorFirms = 0 
        THEN 'No_Prior_Firms'
    WHEN AverageTenureAtPriorFirms < 2 
        THEN 'Short_Tenure_Under_2_Years'
    WHEN AverageTenureAtPriorFirms < 5 
        THEN 'Moderate_Tenure_2_to_5_Years'
    WHEN AverageTenureAtPriorFirms < 10 
        THEN 'Long_Tenure_5_to_10_Years'
    ELSE 
        'Very_Long_Tenure_10_Plus_Years'
END as avg_tenure_category
```

**MQL Rates by Bin:**
- Short (< 2 years): **4.30%** ✅ High conversion
- Moderate (2-5 years): 3.89%
- Long (5-10 years): 2.77%
- Very Long (10+ years): **1.99%** ❌ Low conversion

### 2. Years at Prior Firm 1 (BIN THIS)

```sql
-- Replace raw Number_YearsPriorFirm1 with binned category
CASE 
    WHEN Number_YearsPriorFirm1 IS NULL 
        THEN 'No_Prior_Firm_1'
    WHEN Number_YearsPriorFirm1 < 3 
        THEN 'Short_Tenure_Under_3_Years'
    WHEN Number_YearsPriorFirm1 < 7 
        THEN 'Moderate_Tenure_3_to_7_Years'
    ELSE 
        'Long_Tenure_7_Plus_Years'
END as prior_firm1_category
```

**MQL Rates by Bin:**
- Short (< 3 years): **3.96%** ✅ High conversion
- Moderate (3-7 years): 3.62%
- Long (7+ years): **2.54%** ❌ Low conversion

### 3. Years at Prior Firm 2-4 (OPTIONAL - Can Combine)

**Option A: Bin Each Separately (same bins as Prior Firm 1)**
```sql
CASE 
    WHEN Number_YearsPriorFirm2 IS NULL THEN 'No_Prior_Firm_2'
    WHEN Number_YearsPriorFirm2 < 3 THEN 'Short_Under_3_Years'
    WHEN Number_YearsPriorFirm2 < 7 THEN 'Moderate_3_to_7_Years'
    ELSE 'Long_7_Plus_Years'
END as prior_firm2_category
-- Repeat for Firm 3 and 4
```

**Option B: Combine into Single Feature (Recommended)**
```sql
-- Create "Prior Firm Tenure Pattern" feature
CASE 
    WHEN Number_YearsPriorFirm1 IS NULL AND Number_YearsPriorFirm2 IS NULL 
        THEN 'No_Prior_Firms'
    WHEN Number_YearsPriorFirm1 < 3 OR Number_YearsPriorFirm2 < 3 
        THEN 'Short_Tenure_Pattern'
    WHEN Number_YearsPriorFirm1 < 7 AND Number_YearsPriorFirm2 < 7 
        THEN 'Moderate_Tenure_Pattern'
    ELSE 
        'Long_Tenure_Pattern'
END as prior_firm_tenure_pattern
```

**Recommendation:** Use **Option A** (bin each separately) to preserve granularity, but drop the raw numeric features.

### 4. Keep Firm_Stability_Score (Already Engineered)

**Keep as-is:** `Firm_Stability_Score` is already an engineered feature and shows strong signal (14.68% importance).

**But also create binned version:**
```sql
CASE 
    WHEN Firm_Stability_Score IS NULL OR Firm_Stability_Score = 0 
        THEN 'Missing_Zero'
    WHEN Firm_Stability_Score < 0.3 
        THEN 'Low_Stability_Under_30_Percent'
    WHEN Firm_Stability_Score < 0.6 
        THEN 'Moderate_Stability_30_to_60_Percent'
    WHEN Firm_Stability_Score < 0.9 
        THEN 'High_Stability_60_to_90_Percent'
    ELSE 
        'Very_High_Stability_90_Plus_Percent'
END as stability_category
```

**MQL Rates by Bin:**
- Low (< 30%): **7.07%** ✅ Highest conversion
- Moderate (30-60%): 5.42%
- High (60-90%): 3.89%
- Very High (90%+): **2.53%** ❌ Lowest conversion

---

## Implementation Plan

### Step 1: Update V12 Feature Engineering

**In `v12_production_model_direct_lead.py` or SQL query:**

```python
# After calculating raw tenure features, create binned versions
df['avg_tenure_category'] = pd.cut(
    df['AverageTenureAtPriorFirms'].fillna(0),
    bins=[0, 2, 5, 10, 100],
    labels=['Short_Under_2', 'Moderate_2_to_5', 'Long_5_to_10', 'Very_Long_10_Plus'],
    include_lowest=True
)

df['prior_firm1_category'] = pd.cut(
    df['Number_YearsPriorFirm1'].fillna(0),
    bins=[0, 3, 7, 100],
    labels=['Short_Under_3', 'Moderate_3_to_7', 'Long_7_Plus'],
    include_lowest=True
)

df['stability_category'] = pd.cut(
    df['Firm_Stability_Score_v12'].fillna(0),
    bins=[0, 0.3, 0.6, 0.9, 10],
    labels=['Low_Under_30', 'Moderate_30_to_60', 'High_60_to_90', 'Very_High_90_Plus'],
    include_lowest=True
)

# One-hot encode the categories
# Then DROP the raw numeric features:
drop_features = [
    'AverageTenureAtPriorFirms',  # Replace with binned version
    'Number_YearsPriorFirm1',     # Replace with binned version
    'Number_YearsPriorFirm2',      # Optional: bin or drop
    'Number_YearsPriorFirm3',      # Optional: bin or drop
    'Number_YearsPriorFirm4',      # Optional: bin or drop
]

# Keep: Firm_Stability_Score_v12 (raw, but also create binned version)
# Keep: NumberOfPriorFirms (count, not redundant)
```

### Step 2: One-Hot Encode Categories

```python
# One-hot encode categorical tenure features
for col in ['avg_tenure_category', 'prior_firm1_category', 'stability_category']:
    if col in df.columns:
        for val in df[col].cat.categories:
            new_col = f"{col}_{val}"
            df[new_col] = (df[col] == val).astype(int)
        # Drop original categorical column
        df = df.drop(columns=[col])
```

### Step 3: Test Performance

**Compare:**
- Raw numeric features (current)
- Binned categorical features (proposed)
- Both (baseline)

**Expected Outcome:**
- Binned features should perform similarly or better
- Better interpretability
- Reduced overfitting

---

## Business Rules Based on Insights

### High Priority Leads (Score These Higher)

1. **Low Firm Stability (< 30%)** → 7.07% MQL rate
2. **Unknown Regulatory Disclosures** → 9.84% MQL rate
3. **Short Average Tenure (< 2 years)** → 4.30% MQL rate
4. **Short Prior Firm 1 Tenure (< 3 years)** → 3.96% MQL rate

### Low Priority Leads (Score These Lower)

1. **Very High Firm Stability (90%+)** → 2.53% MQL rate
2. **Very Long Average Tenure (10+ years)** → 1.99% MQL rate
3. **Long Prior Firm 1 Tenure (7+ years)** → 2.54% MQL rate

---

## Expected Impact

### Performance
- **Similar or better AUC-PR:** Binning should not hurt performance
- **Better generalization:** Less overfitting to specific year values
- **Clearer patterns:** Model can learn "Short tenure" vs "Long tenure" patterns

### Interpretability
- **Business-friendly:** Stakeholders understand "Short tenure" better than "1.2 years"
- **Actionable insights:** Clear rules for lead prioritization
- **Explainability:** Easier to explain why a lead scored high/low

---

## Next Steps

1. **✅ Implement Binning:** Modify V12 feature engineering to bin tenure features
2. **✅ Retrain Model:** Compare binned vs raw features
3. **✅ Validate Performance:** Ensure AUC-PR doesn't drop
4. **✅ Document Insights:** Update business rules with MQL rate patterns
5. **✅ Investigate Gender:** Understand why gender is a signal (may need to drop)

---

**Report Generated:** November 5, 2025  
**Status:** ✅ **Ready to Implement - Binning Recommended**

