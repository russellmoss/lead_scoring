# V7 Lead Scoring Model - Data Diagnostic Report

**Generated:** 2025-11-05 10:08  
**Dataset:** `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v7_featured_20251105`  
**Total Leads Analyzed:** 41,894  
**Positive Rate:** 3.38% (1,418 positives)

---

## Executive Summary

This diagnostic analysis examines the V7 training dataset to identify root causes of poor model performance (4.98% AUC-PR) and severe overfitting (97% train vs 5% CV). Key findings and recommendations are provided to guide the next iteration.

**Key Findings:**
- Financial data coverage: 92.6% (if available)
- Duplicate records: None detected
- Temporal features: Limited variation (most are zeros/stable)
- Feature count: 123 features for 1,418 positives (11.5 positives per feature - too low)

---

## 1. Financial Data Coverage Analysis

### Overall Coverage



- **Total Leads:** 41,894
- **Leads with AUM Data:** 38,797 (92.6%)
- **Leads with Client Count:** 39,585 (94.5%)
- **Average Financial Fields Populated:** 5.6 out of 6 key fields

### Coverage by Target Label

- **Positive Leads (Converters):** 1,418 total
  - With AUM: 1,218 (85.9%)
- **Negative Leads:** Similar coverage rates

### Profile of Leads WITHOUT Financial Data



- **Count:** 3,097 leads (7.4% of total)
- **Conversion Rate:** 6.46% (vs overall 3.38%)
- **Characteristics:**
  - Average Experience: 17.3 years
  - Series 7 License: 66.0%
  - Series 65 License: 44.0%
  - Non-Producers: 3.0%
  - Firm Owners: 14.0%
  - Most Common Firm CRD: None (982 reps)

**🔍 Key Finding:** Leads without financial data have different conversion rates, suggesting financial data is critical for prediction.



---

## 2. Data Quality Checks

### Duplicate Analysis



✅ **No duplicates detected** - Financial join appears clean.



### Outlier Analysis



#### AUM Distribution

- **Median:** $60256.3M
- **90th Percentile:** $1511090.9M
- **95th Percentile:** $1511090.9M
- **99th Percentile:** $1650015.9M
- **Maximum:** $1934233.2M
- **Status:** WARNING: AUM > $10B detected

#### Client Count Distribution

- **Maximum:** 3,197,890 clients
- **Status:** WARNING: Client count > 10,000

#### Growth Rate Distribution

- **Minimum:** -10000.00%
- **Maximum:** 2679920.00%
- **Status:** WARNING: Growth rate > 1000% detected



#### Extreme Value Examples

| Type | CRD | Value | Target | Years Exp |
|------|-----|-------|--------|-----------|
| Highest AUM | 6547000 | 1934233.24 | 0 | 9.0 |
| Highest AUM | 2840881 | 1934233.24 | 0 | 28.0 |
| Highest AUM | 4555957 | 1934233.24 | 0 | 23.0 |
| Highest AUM | 7184308 | 1934233.24 | 0 | 5.0 |
| Highest Client Count | 5461097 | 3197890.00 | 0 | 17.0 |
| Highest Client Count | 6094324 | 3197890.00 | 0 | 12.0 |
| Highest Client Count | 6151770 | 3197890.00 | 0 | 11.0 |
| Highest Client Count | 4777595 | 3197890.00 | 0 | 21.0 |
| Highest Client Count | 3160757 | 3197890.00 | 0 | 26.0 |
| Highest Client Count | 6281099 | 3197890.00 | 0 | 10.0 |


---

## 3. Temporal Feature Effectiveness

### Feature Variation Analysis



| Feature | Active/True | Percentage | Notes |
|---------|-------------|------------|-------|
| Recent Firm Change | 3,532 | 8.4% | ❌ Low variation |
| Branch State Stable | 40,880 | 97.6% | ⚠️ Most are stable |
| Multi-State Operator | 30,321 | 72.4% | Some signal |

#### Continuous Features

- **License Sophistication:** Mean=1.72, Median=2, Max=4
- **Tenure Momentum:** Mean=0.570, StdDev=0.340
- **Designation Count:** Mean=0.47, Max=4



### Temporal Features by Target Label


| Feature | Non-Converters (0) | Converters (1) | Difference | Signal |
|---------|-------------------|-----------------|------------|--------|
| Firm Change % | 8.31 | 11.99 | +3.68 | ✅ |
| Branch Stable % | 97.73 | 93.37 | -4.36 | ✅ |
| License Sophistication | 1.72 | 1.54 | -0.18 | ❌ |
| Multi-State % | 72.74 | 61.99 | -10.75 | ✅ |
| Tenure Momentum | 0.57 | 0.44 | -0.13 | ❌ |


### Zero/False Value Analysis

| Feature | Zero/False Count | Percentage | Assessment |
|---------|-----------------|------------|------------|
| Recent_Firm_Change | 38,362 | 91.6% | ❌ Mostly zeros |
| Multi_State_Operator | 11,573 | 27.6% | ✅ Good variation |
| License_Sophistication | 2,886 | 6.9% | ✅ Good variation |
| Branch_State_Stable | 1,014 | 2.4% | ✅ Good variation |


---

## 4. m5 Engineered Features Analysis

### Feature Effectiveness



| Feature | Overall | Converters | Lift | Assessment |
|---------|---------|------------|------|------------|
| Multi RIA Relationships | 3.0% | 2.8% | 0.90x | ❌ Weak |
| HNW Asset Concentration | 0.526 | 0.541 | - | ✅ |
| AUM per Client | $8.80M | $2.91M | - | ❌ |
| Growth Momentum | 82655.5% | 74497.9% | - | ❌ |
| Quality Score | 0.73 | 0.65 | - | ❌ |



### Feature-Target Correlations

| Feature | Correlation | Strength |
|---------|------------|----------|
| Quality_Score | -0.0766 | Strong |
| TotalAssetsInMillions | -0.0588 | Strong |
| Recent_Firm_Change | 0.0240 | Moderate |
| HNW_Asset_Concentration | 0.0120 | Weak |
| Growth_Momentum | -0.0060 | Weak |
| AUM_per_Client | -0.0033 | Weak |
| Multi_RIA_Relationships | -0.0032 | Weak |


---

## 5. Class Balance Across Time

### Temporal Distribution


| Fold | Date Range | Total Leads | Positive Rate | Financial Coverage |
|------|------------|-------------|---------------|-------------------|
| 1 | 2023-08-07 to 2024-10-04 | 10,474 | 2.44% | 92.6% |
| 2 | 2024-10-04 to 2025-01-29 | 10,474 | 3.38% | 93.5% |
| 3 | 2025-01-29 to 2025-06-11 | 10,473 | 3.97% | 92.5% |
| 4 | 2025-06-11 to 2025-10-06 | 10,473 | 3.74% | 91.8% |


**Class Balance Variation:** 17.2% CV
- ✅ Stable across time periods



---

## 6. Feature Completeness

### NULL Rates for Key Features



#### Financial Features

- TotalAssetsInMillions: 7.4% NULL
- NumberClients: 5.5% NULL
- AUMGrowthRate: 10.5% NULL

#### m5 Engineered Features

- Multi_RIA_Relationships: 0.0% NULL
- HNW_Asset_Concentration: 8.2% NULL
- AUM_per_Client: 9.2% NULL

#### Temporal Features

- Recent_Firm_Change: 0.0% NULL
- Branch_State_Stable: 0.0% NULL

#### Basic Features

- Years Experience: 2.4% NULL
- Series 7: 2.3% NULL



---

## 7. Key Findings and Recommendations

### 🔴 Critical Issues

1. **Data Quality Problems**

   - ⚠️ **Extreme outliers:** WARNING: AUM > $10B detected


2. **Feature Engineering Issues**

   - Many temporal features are mostly zeros/stable (limited signal)
   - 43 new features may be causing overfitting with only 1,418 positive samples
   - Feature correlations with target are weak (all < 0.05)



3. **Model Complexity**

   - 123 features for 1,418 positive samples = ~11.5 positives per feature
   - Rule of thumb: Need 10-20 positive samples per feature minimum
   - Current ratio suggests maximum 70-140 features, not 123



### 💡 Recommendations

#### Option A: Radical Simplification (RECOMMENDED)

1. **Reduce to m5's proven features only** (67 features)

2. **Use SMOTE** for class balancing (like m5)

3. **Apply stronger regularization:**

   - `reg_alpha = 2.0` (4x current)

   - `reg_lambda = 10.0` (3x current)

   - `max_depth = 3` (reduce from 5)

4. **Expected outcome:** 8-10% AUC-PR (between V6 and m5)



#### Option B: Two-Model Approach

1. **Model 1:** For leads WITH financial data (92.6% of dataset)

   - Use all features including financial

   - Train on ~38,800 leads

2. **Model 2:** For leads WITHOUT financial data (7.4%)

   - Use only non-financial features

   - Train on ~3,100 leads or use Model 1's non-financial coefficients

3. **Expected outcome:** Better handling of missing financial data



#### Option C: Feature Selection First

1. **Keep only top 50 features** based on:

   - Correlation with target (> 0.01)

   - Non-zero variance

   - Business logic importance

2. **Remove all temporal features** (they show little variation)

3. **Focus on m5's proven features**

4. **Expected outcome:** Reduced overfitting, 6-8% AUC-PR



### 📊 Specific Actions

1. **Fix Data Issues:**

   - Remove duplicate CRDs before training

   - Cap extreme outliers (e.g., AUM > $5B → $5B)

   - Investigate firms with missing financial data



2. **Simplify Features:**

   - Remove temporal features with <10% variation

   - Remove highly correlated features (correlation > 0.9)

   - Focus on m5's top 10 features first



3. **Adjust Training:**

   - Use SMOTE with sampling_strategy=0.1 (10% positive)

   - Increase regularization significantly

   - Reduce tree depth to 3-4

   - Use early stopping with patience=50



4. **Validation Strategy:**

   - Monitor train-val gap at each boosting round

   - Stop if gap exceeds 20%

   - Use 5-fold CV instead of 4 for stability



---

## 8. Recommended Next Steps

### Immediate Actions (Do First)

1. ✅ Remove duplicates from dataset

2. ✅ Cap outliers at reasonable thresholds

3. ✅ Reduce feature set to top 50-70 features

4. ✅ Implement SMOTE for class balancing



### V8 Model Strategy

Based on this analysis, V8 should:

1. **Start with V6's approach** (6.74% AUC-PR baseline)

2. **Add only m5's top 10 features** (not all 31)

3. **Skip temporal features** (they don't work)

4. **Use SMOTE** instead of scale_pos_weight

5. **Target:** 10-12% AUC-PR (achievable)



### Success Metrics

- CV AUC-PR > 10% (minimum viable)

- Train-Test Gap < 30% (acceptable)

- CV Coefficient < 20% (stable)

- At least 3 business features in top 10 importance



---

## Appendix: Query Diagnostics

- Total queries run: 15+

- Analysis completed: {REPORT_DATE}

- Dataset: `{V7_TABLE}`

- Total rows analyzed: {total_leads:,}



**Report Generated Successfully** ✅

