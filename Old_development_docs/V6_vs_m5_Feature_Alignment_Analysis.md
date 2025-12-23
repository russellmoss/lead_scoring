# V6 vs m5 Feature Alignment Analysis

**Date:** 2025-11-04  
**Purpose:** Compare V6 dataset (RIARepDataFeed, no financial metrics) with m5 model features

---

## 🎯 **Quick Answer: NO - V6 is LESS aligned with m5 than the original dataset**

**Why:** m5 was trained on data WITH financial metrics. V6 has NO financial metrics. However, m5's **#1 most important feature** (`Multi_RIA_Relationships`) IS available in V6.

---

## 📊 **m5 Model Features (67 total)**

From `FinalLeadScorePipeline.ipynb`:

### **Base Features (31):**
```python
base_feature_columns = [
    'NumberFirmAssociations', 'TotalAssetsInMillions',  # ❌ Missing
    'NumberRIAFirmAssociations', 'IsPrimaryRIAFirm', 'Number_Employees',  # ❌ Missing
    'Number_BranchAdvisors', 'DateBecameRep_NumberOfYears',  # ✅ Available
    'DateOfHireAtCurrentFirm_NumberOfYears', 'Number_InvestmentAdvisoryClients',  # ❌ Missing
    'KnownNonAdvisor', 'Number_YearsPriorFirm1', 'Number_YearsPriorFirm2',  # ✅ Available (except KnownNonAdvisor)
    'Number_YearsPriorFirm3', 'Number_YearsPriorFirm4', 'MilesToWork',  # ✅ Available
    'Number_IAReps', 'NumberClients_HNWIndividuals', 'NumberClients_Individuals',  # ❌ All Missing
    'AssetsInMillions_HNWIndividuals', 'AssetsInMillions_Individuals',  # ❌ Missing
    'AssetsInMillions_MutualFunds', 'AssetsInMillions_PrivateFunds',  # ❌ Missing
    'AUMGrowthRate_5Year', 'AUMGrowthRate_1Year', 'AverageAccountSize',  # ❌ Missing
    'PercentClients_Individuals', 'Percent_ClientsUS', 'IsDuallyRegistered',  # ❌ Missing (Percent_ClientsUS)
    'IsIndependent', 'AverageTenureAtPriorFirms', 'NumberOfPriorFirms'  # ✅ Available (IsIndependent might be missing)
]
```

### **Engineered Features (31):**
Many depend on financial metrics:
- `AUM_per_Client`, `AUM_per_Employee`, `AUM_per_IARep` - ❌ Requires financial metrics
- `HNW_Asset_Concentration`, `Individual_Asset_Ratio` - ❌ Requires financial metrics
- `Alternative_Investment_Focus` - ❌ Requires financial metrics
- `Is_Large_Firm`, `Is_Boutique_Firm`, `Has_Scale` - ❌ Requires financial metrics
- `Premium_Positioning`, `Mass_Market_Focus` - ❌ Requires financial metrics
- `Clients_per_Employee`, `Clients_per_IARep` - ❌ Requires financial metrics
- `Branch_Advisor_Density` - ⚠️ Requires `Number_IAReps` (not available)

**But some DON'T require financial metrics:**
- ✅ `Multi_RIA_Relationships` - **#1 most important feature in m5!**
- ✅ `Complex_Registration`
- ✅ `Is_Veteran_Advisor`
- ✅ `Is_New_To_Firm`
- ✅ `High_Turnover_Flag`
- ✅ `Firm_Stability_Score` (can derive from tenure)
- ✅ `Remote_Work_Indicator`, `Local_Advisor`
- ✅ `Positive_Growth_Trajectory`, `Accelerating_Growth` (will be NULL but that's fine)

---

## 🔍 **m5 Top 25 Features vs V6 Availability**

From `FinalLeadScorePipeline.ipynb` (lines 1117-1144):

| Rank | Feature | Importance | V6 Available? | Notes |
|------|---------|------------|----------------|-------|
| 1 | `Multi_RIA_Relationships` | 0.0816 | ✅ **YES** | **Most important - we have it!** |
| 2 | `Mass_Market_Focus` | 0.0708 | ❌ No | Requires `PercentClients_Individuals` + `AverageAccountSize` |
| 3 | `HNW_Asset_Concentration` | 0.0587 | ❌ No | Requires `AssetsInMillions_HNWIndividuals` + `TotalAssetsInMillions` |
| 4 | `DateBecameRep_NumberOfYears` | 0.0379 | ✅ **YES** | |
| 5 | `Branch_Advisor_Density` | 0.0240 | ❌ No | Requires `Number_IAReps` |
| 6 | `Is_Veteran_Advisor` | 0.0225 | ✅ **YES** | Can derive from `DateBecameRep_NumberOfYears > 10` |
| 7 | `NumberFirmAssociations` | 0.0220 | ✅ **YES** | |
| 8 | `Firm_Stability_Score` | 0.0211 | ✅ **YES** | Can derive from tenure |
| 9 | `AverageAccountSize` | 0.0208 | ❌ No | Financial metric |
| 10 | `Individual_Asset_Ratio` | 0.0197 | ❌ No | Requires financial metrics |
| 11 | `Home_MetropolitanArea_Dallas...` | 0.0192 | ✅ **YES** | |
| 12 | `Percent_ClientsUS` | 0.0170 | ❌ No | Not in RIARepDataFeed |
| 13 | `Number_Employees` | 0.0165 | ❌ No | Not in RIARepDataFeed |
| 14 | `Number_InvestmentAdvisoryClients` | 0.0163 | ❌ No | Not in RIARepDataFeed |
| 15 | `Clients_per_Employee` | 0.0161 | ❌ No | Requires financial metrics |
| 16 | `Clients_per_IARep` | 0.0157 | ❌ No | Requires financial metrics |
| 17 | `AssetsInMillions_Individuals` | 0.0152 | ❌ No | Financial metric |
| 18 | `Complex_Registration` | 0.0152 | ✅ **YES** | |
| 19 | `NumberClients_Individuals` | 0.0150 | ❌ No | Financial metric |
| 20 | `NumberClients_HNWIndividuals` | 0.0143 | ❌ No | Financial metric |
| 21 | `PercentClients_Individuals` | 0.0135 | ❌ No | Financial metric |
| 22 | `Remote_Work_Indicator` | 0.0131 | ✅ **YES** | Can derive from `MilesToWork > 50` |
| 23 | `Is_New_To_Firm` | 0.0130 | ✅ **YES** | Can derive from `DateOfHireAtCurrentFirm_NumberOfYears < 2` |
| 24 | `Primarily_US_Clients` | 0.0130 | ❌ No | Requires `Percent_ClientsUS` |
| 25 | `Accelerating_Growth` | 0.0128 | ❌ No | Requires `AUMGrowthRate_*` |

**Summary:**
- ✅ **Available in V6:** 8 of top 25 (32%)
- ❌ **Missing in V6:** 17 of top 25 (68%)
- 🎯 **Critical:** #1 feature (`Multi_RIA_Relationships`) IS available!

---

## 💡 **What This Means:**

### **Bad News:**
1. **Most top features are missing** - Only 8 of 25 top m5 features are available in V6
2. **Financial metrics are critical** - m5 relies heavily on AUM, client counts, growth rates
3. **Many engineered features can't be created** - They depend on financial metrics

### **Good News:**
1. **#1 feature is available** - `Multi_RIA_Relationships` (0.0816 importance) is in V6
2. **Tenure features are available** - `DateBecameRep_NumberOfYears`, `Is_Veteran_Advisor`, `Firm_Stability_Score`
3. **License/designation features** - We can create boolean flags from Series columns
4. **Geographic features** - Metro areas, states, miles to work
5. **Firm association features** - `NumberFirmAssociations`, `Complex_Registration`

---

## 🎯 **V6 vs Original m5 Training Data:**

| Aspect | m5 Training Data | V6 Dataset (RIARepDataFeed) |
|--------|------------------|----------------------------|
| **Financial Metrics** | ✅ Full (AUM, clients, growth) | ❌ None (all NULL) |
| **Tenure Features** | ✅ Full | ✅ Full |
| **Licenses/Designations** | ✅ Full | ✅ Full (as strings, convert to boolean) |
| **Firm Associations** | ✅ Full | ✅ Full |
| **Geographic** | ✅ Full | ✅ Full |
| **Top Feature (#1)** | ✅ `Multi_RIA_Relationships` | ✅ Available |
| **Top Features (#2-5)** | ✅ Financial-based | ❌ Missing |

---

## 📊 **Expected Model Performance:**

### **If we use m5 model directly on V6 data:**
- **Will fail** - Model expects 67 features, many financial-based
- **Missing features** will cause errors or NULL predictions

### **If we train NEW model on V6 data:**
- **Will work** - XGBoost handles NULLs well
- **Expected performance:** Lower than m5 (maybe 0.10-0.12 AUC-PR vs m5's 0.1492)
- **Why lower:**
  - Missing financial signals (AUM, growth, client counts)
  - Missing top features (#2-5 are all financial-based)
  - But #1 feature (`Multi_RIA_Relationships`) is available

---

## ✅ **Recommendation:**

**V6 is NOT aligned with m5's training data**, but:

1. **We can't use m5 model directly** - It expects financial metrics
2. **We MUST train a new model** - V6 with available features only
3. **The new model will be different** - Will rely on:
   - `Multi_RIA_Relationships` (strong signal)
   - Tenure/experience features
   - License/designation features
   - Geographic features
   - Firm association features

4. **Performance expectations:** Lower than m5, but still useful for ranking leads

---

## 🔧 **What We Need to Do:**

1. **Update Step 4.1 (Training)** to:
   - Drop all financial-based features from training
   - Focus on tenure, licenses, geographic, firm associations
   - Use same XGBoost hyperparameters as m5 (but adapted for fewer features)

2. **Feature engineering for V6:**
   - ✅ `Multi_RIA_Relationships` (from `NumberRIAFirmAssociations > 1`)
   - ✅ `Complex_Registration` (from `NumberFirmAssociations > 2 OR NumberRIAFirmAssociations > 1`)
   - ✅ `Is_Veteran_Advisor` (from `DateBecameRep_NumberOfYears > 10`)
   - ✅ `Is_New_To_Firm` (from `DateOfHireAtCurrentFirm_NumberOfYears < 2`)
   - ✅ `High_Turnover_Flag` (from tenure patterns)
   - ✅ `Firm_Stability_Score` (from tenure)
   - ✅ `Remote_Work_Indicator` (from `MilesToWork > 50`)
   - ✅ License/designation boolean flags (from Series columns)

3. **Accept lower performance** - Model will be less powerful than m5, but still useful

---

## 📋 **Conclusion:**

**V6 is NOT aligned with m5's training data** - m5 was trained WITH financial metrics, V6 has NONE.

However, **V6 DOES have m5's #1 most important feature** (`Multi_RIA_Relationships`), which is a strong signal.

**We need to train a NEW model** on V6 data, accepting that:
- Performance will be lower than m5
- But still useful for lead ranking
- Will rely more on tenure, licenses, and firm associations than financial metrics

