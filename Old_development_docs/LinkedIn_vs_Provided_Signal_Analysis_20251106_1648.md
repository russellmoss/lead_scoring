# LinkedIn Self Sourced vs Provided Lead List Signal Analysis

**Generated:** 2025-11-06 16:48:06  
**Purpose:** Identify what signals/characteristics distinguish LinkedIn Self Sourced leads from Provided Lead List leads

---

## Executive Summary

This analysis uses a classification model to predict whether a lead came from "LinkedIn (Self Sourced)" or "Provided Lead List" based on lead characteristics. The model identifies which features are most predictive, revealing what signals people are looking for when they manually source leads from LinkedIn.

### Key Results

- **Model Performance:** AUC-ROC = 0.5432
- **Training Samples:** 32,622 leads
- **Test Samples:** 8,156 leads
- **LinkedIn Leads:** 10,452 (25.6%)
- **Provided Lead List Leads:** 30,326 (74.4%)

---

## Model Performance

### Classification Metrics

**AUC-ROC:** 0.5432

**Interpretation:**
- AUC-ROC > 0.70: Model can distinguish between sources
- AUC-ROC > 0.80: Strong predictive power
- AUC-ROC > 0.90: Excellent predictive power

---

## Top Signals That Distinguish LinkedIn Self Sourced Leads

### Top 30 Most Important Features

| Rank | Feature | Importance | % of Total |
|------|---------|------------|------------|
| 1 | `Gender_Missing` | 0.4303 | 43.03% |
| 2 | `Firm_Stability_Score` | 0.1216 | 12.16% |
| 3 | `RegulatoryDisclosures_Unknown` | 0.0806 | 8.06% |
| 4 | `RegulatoryDisclosures_Yes` | 0.0709 | 7.09% |
| 5 | `AverageTenureAtPriorFirms` | 0.0567 | 5.67% |
| 6 | `Number_YearsPriorFirm1` | 0.0517 | 5.17% |
| 7 | `Number_YearsPriorFirm4` | 0.0486 | 4.86% |
| 8 | `Gender_Male` | 0.0479 | 4.79% |
| 9 | `Number_YearsPriorFirm3` | 0.0472 | 4.72% |
| 10 | `Number_YearsPriorFirm2` | 0.0447 | 4.47% |
| 11 | `PercentAssets_MutualFunds` | 0.0000 | 0.00% |
| 12 | `PercentAssets_Individuals` | 0.0000 | 0.00% |
| 13 | `PercentAssets_HNWIndividuals` | 0.0000 | 0.00% |
| 14 | `PercentClients_Individuals` | 0.0000 | 0.00% |
| 15 | `PercentClients_HNWIndividuals` | 0.0000 | 0.00% |
| 16 | `AssetsInMillions_Equity_ExchangeTraded` | 0.0000 | 0.00% |
| 17 | `AssetsInMillions_PrivateFunds` | 0.0000 | 0.00% |
| 18 | `AssetsInMillions_MutualFunds` | 0.0000 | 0.00% |
| 19 | `TotalAssets_PooledVehicles` | 0.0000 | 0.00% |
| 20 | `TotalAssets_SeparatelyManagedAccounts` | 0.0000 | 0.00% |
| 21 | `CustodianAUM_Schwab` | 0.0000 | 0.00% |
| 22 | `CustodianAUM_TDAmeritrade` | 0.0000 | 0.00% |
| 23 | `PercentAssets_Equity_ExchangeTraded` | 0.0000 | 0.00% |
| 24 | `PercentAssets_PrivateFunds` | 0.0000 | 0.00% |
| 25 | `CustodianAUM_Fidelity_NationalFinancial` | 0.0000 | 0.00% |
| 26 | `CustodianAUM_Pershing` | 0.0000 | 0.00% |

---

## Signal Analysis: What Makes LinkedIn Leads Different?

### Comparison of Feature Means

| Feature | LinkedIn Mean | Provided Mean | Difference | Difference % | Direction |
|---------|---------------|---------------|------------|--------------|-----------|
| `Gender_Missing` | 0.085 | 0.013 | +0.072 | +552.3% | ↑ Higher |
| `Firm_Stability_Score` | 0.395 | 0.468 | -0.073 | -15.7% | ↓ Lower |
| `RegulatoryDisclosures_Unknown` | 0.806 | 0.837 | -0.031 | -3.7% | ↓ Lower |
| `RegulatoryDisclosures_Yes` | 0.121 | 0.160 | -0.039 | -24.7% | ↓ Lower |
| `AverageTenureAtPriorFirms` | 3.527 | 3.521 | +0.005 | +0.2% | ↑ Higher |
| `Number_YearsPriorFirm1` | 3.732 | 3.796 | -0.063 | -1.7% | ↓ Lower |
| `Number_YearsPriorFirm4` | 1.181 | 1.273 | -0.092 | -7.3% | ↓ Lower |
| `Gender_Male` | 0.738 | 0.808 | -0.071 | -8.7% | ↓ Lower |
| `Number_YearsPriorFirm3` | 1.688 | 1.851 | -0.163 | -8.8% | ↓ Lower |
| `Number_YearsPriorFirm2` | 2.490 | 2.579 | -0.089 | -3.5% | ↓ Lower |
| `PercentAssets_MutualFunds` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `PercentAssets_Individuals` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `PercentAssets_HNWIndividuals` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `PercentClients_Individuals` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `PercentClients_HNWIndividuals` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `AssetsInMillions_Equity_ExchangeTraded` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `AssetsInMillions_PrivateFunds` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `AssetsInMillions_MutualFunds` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `TotalAssets_PooledVehicles` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |
| `TotalAssets_SeparatelyManagedAccounts` | 0.000 | 0.000 | +0.000 | +0.0% | ↓ Lower |

---

## Key Insights

### What Signals Are People Using When Sourcing LinkedIn Leads?

Based on the feature importance analysis, the following characteristics appear to be key signals:


**2. Tenure & Career Stage:**
- `Firm_Stability_Score`
- `AverageTenureAtPriorFirms`
- `Number_YearsPriorFirm1`
- `Number_YearsPriorFirm4`
- `Number_YearsPriorFirm3`

**6. Other Signals:**
- `Gender_Missing`
- `RegulatoryDisclosures_Unknown`
- `RegulatoryDisclosures_Yes`
- `Gender_Male`
- `PercentAssets_MutualFunds`

---

## Recommendations

### For Lead Sourcing Strategy

1. **Focus on High-Value Signals:** The top features identified can guide what to look for when manually sourcing LinkedIn leads
2. **Automate Signal Detection:** Consider building automated filters based on these signals to identify high-quality LinkedIn prospects
3. **Training for Sourcers:** Use these insights to train team members on what characteristics to prioritize when sourcing from LinkedIn

### For Model Development

1. **Feature Engineering:** Consider creating composite features based on the top signals
2. **Validation:** Test whether leads with these characteristics actually convert better
3. **Monitoring:** Track whether these signals remain predictive over time

---

## Data Details

- **Data Source:** `savvy-gtm-analytics.SavvyGTMData.Lead`
- **Discovery Source:** `savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages`
- **Filter Period:** 2024-01-01 to 2025-09-30
- **Total Features:** 26
- **Model Type:** XGBoost Classifier

---

**Report Generated:** 2025-11-06 16:48:06  
**Analysis Period:** 2024-01-01 to 2025-09-30
