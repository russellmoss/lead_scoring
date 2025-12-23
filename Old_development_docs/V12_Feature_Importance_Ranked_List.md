# V12 Model: Feature Importance Ranking

**Generated:** November 5, 2025  
**Model:** V12 with Binned Features + Fixed Gender Encoding  
**Performance:** 6.00% AUC-PR, 1.27x lift over baseline  
**Total Features:** 53

---

## Complete Feature Importance List (Ranked)

| Rank | Feature Name | Importance | Weight | Type | Interpretation |
|------|--------------|------------|--------|------|----------------|
| 1 | **Firm_Stability_Score_v12_binned_Low_Under_30** | **11.18%** | **11.18%** | Stability | **Low stability = Highest conversion (7.07% MQL rate)** |
| 2 | **Gender_Missing** | **8.03%** | **8.03%** | Data Quality | **Missing gender = Strong signal (9.27% MQL rate)** |
| 3 | **Number_YearsPriorFirm1_binned_Long_7_Plus** | **7.41%** | **7.41%** | Tenure | Long tenure at prior firm = Negative signal (2.54% MQL rate) |
| 4 | **Firm_Stability_Score_v12_binned_Very_High_90_Plus** | **5.75%** | **5.75%** | Stability | Very high stability = Negative signal (2.53% MQL rate) |
| 5 | **AverageTenureAtPriorFirms_binned_Long_5_to_10** | **4.39%** | **4.39%** | Tenure | Long average tenure = Lower conversion |
| 6 | **AverageTenureAtPriorFirms_binned_Very_Long_10_Plus** | **4.26%** | **4.26%** | Tenure | Very long average tenure = Lowest conversion (1.99% MQL rate) |
| 7 | **AverageTenureAtPriorFirms_binned_Moderate_2_to_5** | **3.59%** | **3.59%** | Tenure | Moderate average tenure |
| 8 | **Number_YearsPriorFirm3_binned_Long_7_Plus** | **3.52%** | **3.52%** | Tenure | Long tenure at prior firm 3 = Negative signal |
| 9 | **Number_YearsPriorFirm3_binned_Short_Under_3** | **3.46%** | **3.46%** | Tenure | Short tenure at prior firm 3 = Positive signal |
| 10 | **Gender_Male** | **3.46%** | **3.46%** | Categorical | Male gender indicator |
| 11 | **Firm_Stability_Score_v12_binned_Moderate_30_to_60** | **3.44%** | **3.44%** | Stability | Moderate stability |
| 12 | **Number_YearsPriorFirm4_binned_Long_7_Plus** | **3.37%** | **3.37%** | Tenure | Long tenure at prior firm 4 = Negative signal |
| 13 | **Number_YearsPriorFirm2_binned_Long_7_Plus** | **3.35%** | **3.35%** | Tenure | Long tenure at prior firm 2 = Negative signal |
| 14 | **Number_YearsPriorFirm2_binned_Short_Under_3** | **3.31%** | **3.31%** | Tenure | Short tenure at prior firm 2 = Positive signal |
| 15 | **Number_YearsPriorFirm2_binned_Moderate_3_to_7** | **3.30%** | **3.30%** | Tenure | Moderate tenure at prior firm 2 |
| 16 | **Number_YearsPriorFirm4_binned_Short_Under_3** | **3.26%** | **3.26%** | Tenure | Short tenure at prior firm 4 = Positive signal |
| 17 | **Firm_Stability_Score_v12_binned_High_60_to_90** | **3.21%** | **3.21%** | Stability | High stability = Lower conversion |
| 18 | **Number_YearsPriorFirm4_binned_Moderate_3_to_7** | **3.20%** | **3.20%** | Tenure | Moderate tenure at prior firm 4 |
| 19 | **Number_YearsPriorFirm1_binned_Moderate_3_to_7** | **3.18%** | **3.18%** | Tenure | Moderate tenure at prior firm 1 |
| 20 | **Number_YearsPriorFirm3_binned_Moderate_3_to_7** | **3.11%** | **3.11%** | Tenure | Moderate tenure at prior firm 3 |
| 21 | **Number_YearsPriorFirm1_binned_Short_Under_3** | **3.10%** | **3.10%** | Tenure | Short tenure at prior firm 1 = Positive signal (3.96% MQL rate) |
| 22 | **AverageTenureAtPriorFirms_binned_Short_Under_2** | **3.09%** | **3.09%** | Tenure | Short average tenure = Positive signal (4.30% MQL rate) |
| 23 | **RegulatoryDisclosures_Unknown** | **3.04%** | **3.04%** | Regulatory | Unknown disclosures = Strong signal (9.84% MQL rate) |
| 24 | **RegulatoryDisclosures_Yes** | **3.00%** | **3.00%** | Regulatory | Has disclosures = Lower conversion (3.24% MQL rate) |
| 25-53 | *(All other features have 0.0% importance)* | **0.00%** | **0.00%** | Various | Not used by model |

---

## Features by Category

### 🏆 Stability Features (Top Importance)

| Feature | Importance | MQL Rate | Signal |
|---------|------------|----------|--------|
| Firm_Stability_Score_v12_binned_Low_Under_30 | **11.18%** | 7.07% | ✅ **Strong Positive** |
| Firm_Stability_Score_v12_binned_Very_High_90_Plus | **5.75%** | 2.53% | ❌ Strong Negative |
| Firm_Stability_Score_v12_binned_Moderate_30_to_60 | **3.44%** | 5.42% | ✅ Moderate Positive |
| Firm_Stability_Score_v12_binned_High_60_to_90 | **3.21%** | 3.89% | ⚠️ Weak Negative |

**Total Stability Importance:** 23.58%

---

### 📊 Data Quality Features

| Feature | Importance | MQL Rate | Signal |
|---------|------------|----------|--------|
| Gender_Missing | **8.03%** | 9.27% | ✅ **Strong Positive** |
| Gender_Male | **3.46%** | 4.22% | ✅ Moderate Positive |

**Total Data Quality Importance:** 11.49%

---

### ⏱️ Tenure Features (Prior Firms)

| Feature | Importance | Signal |
|---------|------------|--------|
| Number_YearsPriorFirm1_binned_Long_7_Plus | **7.41%** | ❌ Strong Negative |
| AverageTenureAtPriorFirms_binned_Long_5_to_10 | **4.39%** | ❌ Moderate Negative |
| AverageTenureAtPriorFirms_binned_Very_Long_10_Plus | **4.26%** | ❌ Strong Negative |
| AverageTenureAtPriorFirms_binned_Moderate_2_to_5 | **3.59%** | ⚠️ Neutral |
| Number_YearsPriorFirm3_binned_Long_7_Plus | **3.52%** | ❌ Negative |
| Number_YearsPriorFirm3_binned_Short_Under_3 | **3.46%** | ✅ Positive |
| Number_YearsPriorFirm4_binned_Long_7_Plus | **3.37%** | ❌ Negative |
| Number_YearsPriorFirm2_binned_Long_7_Plus | **3.35%** | ❌ Negative |
| Number_YearsPriorFirm2_binned_Short_Under_3 | **3.31%** | ✅ Positive |
| Number_YearsPriorFirm2_binned_Moderate_3_to_7 | **3.30%** | ⚠️ Neutral |
| Number_YearsPriorFirm4_binned_Short_Under_3 | **3.26%** | ✅ Positive |
| Number_YearsPriorFirm4_binned_Moderate_3_to_7 | **3.20%** | ⚠️ Neutral |
| Number_YearsPriorFirm1_binned_Moderate_3_to_7 | **3.18%** | ⚠️ Neutral |
| Number_YearsPriorFirm3_binned_Moderate_3_to_7 | **3.11%** | ⚠️ Neutral |
| Number_YearsPriorFirm1_binned_Short_Under_3 | **3.10%** | ✅ Positive |
| AverageTenureAtPriorFirms_binned_Short_Under_2 | **3.09%** | ✅ Positive |

**Total Tenure Importance:** 52.35%

---

### ⚖️ Regulatory Features

| Feature | Importance | MQL Rate | Signal |
|---------|------------|----------|--------|
| RegulatoryDisclosures_Unknown | **3.04%** | 9.84% | ✅ **Strong Positive** |
| RegulatoryDisclosures_Yes | **3.00%** | 3.24% | ❌ Negative |

**Total Regulatory Importance:** 6.04%

---

## Summary Statistics

### Top 5 Features (Cumulative)

1. Firm_Stability_Score_v12_binned_Low_Under_30: 11.18%
2. Gender_Missing: 8.03%
3. Number_YearsPriorFirm1_binned_Long_7_Plus: 7.41%
4. Firm_Stability_Score_v12_binned_Very_High_90_Plus: 5.75%
5. AverageTenureAtPriorFirms_binned_Long_5_to_10: 4.39%

**Top 5 Cumulative:** 36.76%

### Top 10 Features (Cumulative)

**Top 10 Cumulative:** 50.68%

### Top 15 Features (Cumulative)

**Top 15 Cumulative:** 64.89%

### Top 24 Features (All Non-Zero)

**Top 24 Cumulative:** 100.00%

---

## Key Insights

1. **Stability is #1:** Low firm stability (11.18%) is the most important positive signal
2. **Data Quality Matters:** Missing gender (8.03%) is the #2 feature
3. **Tenure Patterns:** Long tenure at prior firms is a strong negative signal (7.41%)
4. **24 Active Features:** Only 24 of 53 features have non-zero importance
5. **Financial Features Unused:** AUM, growth rates, and asset features all have 0% importance

---

## Feature Categories Summary

| Category | Count | Total Importance | % of Model |
|----------|-------|------------------|------------|
| **Stability** | 4 | 23.58% | 23.58% |
| **Tenure (Prior Firms)** | 16 | 52.35% | 52.35% |
| **Data Quality** | 2 | 11.49% | 11.49% |
| **Regulatory** | 2 | 6.04% | 6.04% |
| **Financial** | 0 | 0.00% | 0.00% |
| **Geographic** | 0 | 0.00% | 0.00% |
| **Other** | 0 | 0.00% | 0.00% |

---

**Report Generated:** November 5, 2025  
**Model Version:** V12 with Binned Features (20251105_1646)  
**Key Takeaway:** **Stability and tenure patterns dominate the model - 76% of importance comes from these behavioral signals.**

