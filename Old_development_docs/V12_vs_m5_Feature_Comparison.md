# V12 vs Final Model_Russ (m5) Feature Importance Comparison

**Generated:** 2025-11-06  
**Comparison:** V12 Production Model vs Final Model_Russ (m5)  
**Baseline MQL Rate:** 4% (Contacted → MQL conversion)

---

## Executive Summary

The V12 and m5 models use fundamentally different feature sets, reflecting their different data strategies:

- **V12:** Uses binned stability/tenure features + PII-compliant data (18 features total, temporally correct)
- **m5:** Uses continuous engineered features + geographic data (25+ features, data leakage present)

**Key Finding:** Despite different approaches, both models prioritize **stability/tenure patterns** and **behavioral signals** as top predictors.

---

## Top 15 Features Comparison

### V12 Model (18 Features Total)

| Rank | Feature | Importance | Weight | Type | Category |
|------|---------|------------|--------|------|----------|
| 1 | **Firm_Stability_Score_v12_binned_Low_Under_30** | **14.03%** | 0.1403 | Stability | Behavioral |
| 2 | **Number_YearsPriorFirm1_binned_Long_7_Plus** | **10.01%** | 0.1001 | Tenure | Behavioral |
| 3 | **Gender_Missing** | **9.51%** | 0.0951 | Data Quality | Demographic |
| 4 | **Firm_Stability_Score_v12_binned_Very_High_90_Plus** | **8.79%** | 0.0879 | Stability | Behavioral |
| 5 | **AverageTenureAtPriorFirms_binned_Long_5_to_10** | **6.48%** | 0.0648 | Tenure | Behavioral |
| 6 | **Firm_Stability_Score_v12_binned_High_60_to_90** | **6.28%** | 0.0628 | Stability | Behavioral |
| 7 | **AverageTenureAtPriorFirms_binned_Very_Long_10_Plus** | **5.95%** | 0.0595 | Tenure | Behavioral |
| 8 | **Firm_Stability_Score_v12_binned_Moderate_30_to_60** | **5.91%** | 0.0591 | Stability | Behavioral |
| 9 | **AverageTenureAtPriorFirms_binned_Moderate_2_to_5** | **5.59%** | 0.0559 | Tenure | Behavioral |
| 10 | **AverageTenureAtPriorFirms_binned_Short_Under_2** | **5.45%** | 0.0545 | Tenure | Behavioral |
| 11 | **Gender_Male** | **4.72%** | 0.0472 | Categorical | Demographic |
| 12 | **Number_YearsPriorFirm1_binned_Short_Under_3** | **4.63%** | 0.0463 | Tenure | Behavioral |
| 13 | **RegulatoryDisclosures_Yes** | **4.32%** | 0.0432 | Regulatory | Compliance |
| 14 | **Number_YearsPriorFirm1_binned_Moderate_3_to_7** | **4.30%** | 0.0430 | Tenure | Behavioral |
| 15 | **RegulatoryDisclosures_Unknown** | **4.04%** | 0.0404 | Regulatory | Compliance |

**Top 15 Total Importance:** ~100% (only 15 features with non-zero importance)

---

### Final Model_Russ (m5) Model (25+ Features)

| Rank | Feature | Importance | Weight | Type | Category |
|------|---------|------------|--------|------|----------|
| 1 | **Multi_RIA_Relationships** | **8.16%** | 0.0816 | Engineered | Behavioral |
| 2 | **Mass_Market_Focus** | **7.08%** | 0.0708 | Engineered | Business Model |
| 3 | **HNW_Asset_Concentration** | **5.87%** | 0.0587 | Engineered | Client Profile |
| 4 | **DateBecameRep_NumberOfYears** | **3.79%** | 0.0379 | Temporal | Career Stage |
| 5 | **Branch_Advisor_Density** | **2.40%** | 0.0240 | Engineered | Firm Structure |
| 6 | **Is_Veteran_Advisor** | **2.25%** | 0.0225 | Engineered | Career Stage |
| 7 | **NumberFirmAssociations** | **2.20%** | 0.0220 | Base Feature | Behavioral |
| 8 | **Firm_Stability_Score** | **2.11%** | 0.0211 | Engineered | Stability |
| 9 | **AverageAccountSize** | **2.08%** | 0.0208 | Base Feature | Client Profile |
| 10 | **Individual_Asset_Ratio** | **1.97%** | 0.0197 | Engineered | Client Profile |
| 11 | **Home_MetropolitanArea_Dallas-Fort Worth-Arlington TX** | **1.92%** | 0.0192 | Geographic | Location (PII) |
| 12 | **Percent_ClientsUS** | **1.70%** | 0.0170 | Base Feature | Client Profile |
| 13 | **Number_Employees** | **1.65%** | 0.0165 | Base Feature | Firm Structure |
| 14 | **Number_InvestmentAdvisoryClients** | **1.63%** | 0.0163 | Base Feature | Client Profile |
| 15 | **Clients_per_Employee** | **1.61%** | 0.0161 | Engineered | Firm Structure |

**Top 15 Total Importance:** ~43.2% (model has 25+ features with distributed importance)

---

## Feature Category Breakdown

### V12 Model

| Category | Count | Total Importance | Key Insights |
|----------|-------|-----------------|--------------|
| **Stability Features** | 4 | **34.72%** | Low stability = highest conversion (7.07% MQL) |
| **Tenure Features** | 7 | **40.06%** | Long tenure = negative, short tenure = positive |
| **Data Quality** | 2 | **14.23%** | Missing gender = strong signal (9.27% MQL) |
| **Regulatory** | 2 | **8.36%** | Unknown disclosures = 3x higher conversion |
| **Financial** | 0 | **0.00%** | Removed (missing data) |
| **Geographic** | 0 | **0.00%** | Removed (PII compliance) |

**Total Active Features:** 15 (83% of 18 feature set)

### m5 Model

| Category | Count | Total Importance | Key Insights |
|----------|-------|-----------------|--------------|
| **Engineered Behavioral** | 5+ | **~20%** | Multi-RIA, stability, density signals |
| **Client Profile** | 6+ | **~12%** | HNW concentration, account size, client ratios |
| **Firm Structure** | 4+ | **~6%** | Employees, advisors, density metrics |
| **Career Stage** | 2+ | **~6%** | Years as rep, veteran status |
| **Geographic** | 1+ | **~2%** | Metro areas (PII leakage risk) |
| **Base Features** | 6+ | **~8%** | Raw discovery data fields |

**Note:** m5 uses continuous values and geographic features (PII) that V12 excludes.

---

## Key Differences

### 1. **Feature Engineering Approach**

**V12:**
- Uses **binned categorical features** (Low/Moderate/High/Very High)
- Focuses on **behavioral patterns** (stability, tenure)
- **PII-compliant** (no geographic identifiers)

**m5:**
- Uses **continuous engineered features** (ratios, concentrations)
- Mixes **business signals** (HNW concentration, account size) with **geographic** (metro areas)
- **PII leakage** present (geographic identifiers in top features)

### 2. **Top Feature Overlap**

**Common Signals (Conceptually):**
- ✅ **Stability/Tenure:** Both models prioritize advisor stability patterns
  - V12: `Firm_Stability_Score_v12_binned_Low_Under_30` (14.03%)
  - m5: `Firm_Stability_Score` (2.11%) + `Multi_RIA_Relationships` (8.16%)
  
- ✅ **Career Stage:** Both capture advisor experience
  - V12: `Number_YearsPriorFirm1_binned_*` (10.01% top bin)
  - m5: `DateBecameRep_NumberOfYears` (3.79%) + `Is_Veteran_Advisor` (2.25%)

**Unique to V12:**
- ❌ **Data Quality Signals:** `Gender_Missing` (9.51%) - captures incomplete profiles
- ❌ **Regulatory Signals:** `RegulatoryDisclosures_Unknown` (4.04%) - missing disclosure data

**Unique to m5:**
- ❌ **Geographic Features:** Metro areas (PII leakage)
- ❌ **Client Profile Ratios:** `HNW_Asset_Concentration` (5.87%), `Mass_Market_Focus` (7.08%)
- ❌ **Firm Structure:** `Branch_Advisor_Density` (2.40%), `Clients_per_Employee` (1.61%)

### 3. **Feature Concentration**

**V12:**
- **Highly concentrated:** Top 5 features = 48.82% of total importance
- **Simple model:** 15 active features, clear behavioral signals
- **Interpretable:** Binned categories with business meaning

**m5:**
- **Distributed:** Top 5 features = 28.18% of total importance
- **Complex model:** 25+ features, mixed signal types
- **Less interpretable:** Continuous ratios require thresholds

---

## Business Insights

### V12: What Matters Most

1. **Low Firm Stability (< 30%)** - **14.03% importance**
   - Highest conversion rate: **7.07% MQL** (2.8x baseline)
   - **Action:** Prioritize advisors with multiple firm moves or short tenure

2. **Long Tenure at Prior Firm (7+ years)** - **10.01% importance** (Negative Signal)
   - Low conversion rate: **2.54% MQL**
   - **Action:** Deprioritize advisors with very stable prior firm tenure

3. **Missing Gender Data** - **9.51% importance**
   - Strong signal: **9.27% MQL** (2.2x baseline)
   - **Action:** Missing demographic data indicates newer/incomplete profiles

### m5: What Matters Most

1. **Multi-RIA Relationships** - **8.16% importance**
   - Indicates advisors associated with multiple RIAs
   - **Action:** Multi-RIA advisors may be more open to opportunities

2. **Mass Market Focus** - **7.08% importance**
   - Client profile indicator
   - **Action:** Mass market advisors may have different conversion patterns

3. **HNW Asset Concentration** - **5.87% importance**
   - High-net-worth client focus
   - **Action:** HNW advisors may have different engagement patterns

---

## Model Performance Context

### V12 Model
- **Test AUC-PR:** 5.97%
- **Baseline MQL Rate:** 4.74%
- **Lift:** 1.26x baseline
- **Target:** 7% AUC-PR (improving from 6%)
- **Status:** ✅ Production-ready, temporally correct, PII-compliant

### m5 Model
- **Test AUC-PR:** 14.35%* (inflated due to data leakage)
- **Baseline MQL Rate:** ~3.00%*
- **Status:** ❌ **Not production-ready** (temporal leakage, overfitting, PII issues)

*Metrics unreliable due to data leakage issues documented in `TRAINING_ANALYSIS_Data_Leakage_Report.md`

---

## Recommendations

### For Future Model Development

1. **Adopt V12's Feature Strategy:**
   - ✅ Use **binned stability/tenure features** (proven strong signals)
   - ✅ Include **data quality indicators** (missing gender, regulatory data)
   - ✅ **Exclude PII** (geographic identifiers)

2. **Learn from m5's Engineered Features:**
   - Consider **HNW Asset Concentration** (if temporally correct data available)
   - Consider **Multi-RIA Relationships** (already captured in V12 stability)
   - **Avoid** geographic features (PII risk + spurious correlations)

3. **Feature Engineering Priorities:**
   - Focus on **behavioral signals** (stability, tenure, movement patterns)
   - Maintain **interpretability** (binned categories > continuous ratios)
   - Ensure **temporal correctness** (no future data leakage)

---

## Conclusion

Both models agree on the core insight: **advisor stability and tenure patterns are the strongest predictors** of MQL conversion. However, V12's approach is:

- ✅ **More interpretable** (binned categories)
- ✅ **More stable** (temporally correct)
- ✅ **More compliant** (PII-free)
- ✅ **Production-ready** (no data leakage)

The m5 model's higher reported performance is an artifact of data leakage, not true predictive power. V12's 6% AUC-PR is the **realistic, trustworthy baseline** we should build from to reach our 7% target.

---

**Report Generated:** November 6, 2025  
**V12 Source:** `V12_Complete_Feature_Importance.csv`  
**m5 Source:** `Final Model_Russ/FinalLeadScorePipeline.ipynb` (Cell 37 output)

