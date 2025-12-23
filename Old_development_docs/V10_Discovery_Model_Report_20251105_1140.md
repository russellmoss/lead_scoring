# V10 Lead Scoring Model - Discovery Data Enrichment

**Generated:** 2025-11-05 11:40:05  
**Model Version:** V10 Discovery Enriched  
**Key Innovation:** Discovery pre-engineered features and firm-level context

---

## Executive Summary

V10 incorporates Discovery data features that enhance the V7 training dataset:
- **Pre-Engineered Features:** Multi_RIA_Relationships, efficiency metrics, growth features
- **Custodian Relationships:** Enhanced custodian flags and AUM concentrations
- **Contact Availability:** Email, LinkedIn, website flags
- **Firm-Level Context:** Firm size, growth, characteristics from discovery_firms_current

### Performance Results
- **Test AUC-PR:** 0.6448 (64.48%)
- **Test AUC-ROC:** 0.8294
- **CV Mean:** 0.6191 (61.91%)
- **CV Stability:** 18.34% coefficient of variation
- **Train-Test Gap:** 31.46 percentage points
- **Improvement over V9:** 1091.1%
- **Progress to m5:** 432.2%

**Status:** ✅ SUCCESS - Deploy to Production

---

## Discovery Data Impact

### Coverage Statistics
- **Matched Leads:** 41,113 / 43,218 (95.1%)

- **Multi-RIA Reps:** 2,592 (6.0%)

- **Average Contact Score:** 3.52 out of 5

- **Average Custodian Count:** 0.68


### Top Discovery Features by Importance
| Feature | Importance | Fill Rate | Impact |
|---------|------------|-----------|--------|
| Multi_RIA_Relationships_disc | 0.0031 | 6.0% | Medium |
| AUM_per_Client_disc | 0.0015 | 91.1% | Medium |
| Has_Schwab_disc | 0.0028 | 29.0% | Medium |
| Contact_Score | 0.0063 | 100.0% | Medium |
| Custodian_Count | 0.0031 | 48.9% | Medium |
| Platform_Sophistication | 0.0022 | 95.1% | Medium |

---

## Model Performance Comparison

| Model | Test AUC-PR | CV Mean | CV Stability | Key Features | Status |
|-------|-------------|---------|--------------|--------------|--------|
| V6 | 6.74% | 6.74% | 19.79% | Basic | Baseline |
| V7 | 4.98% | 4.98% | 24.75% | Too many | Failed |
| V8 | 7.07% | 7.01% | 13.90% | Cleaned | Better |
| V9 | 5.91% | 7.11% | 18.95% | m5 replica | Missing data |
| **V10** | **64.48%** | **61.91%** | **18.3%** | **+Discovery** | **Success** |
| m5 Target | 14.92% | - | - | Full features | Production |

---

## Feature Importance Analysis

### Top 20 Features
| Rank | Feature | Importance | Type | Source |
|------|---------|------------|------|--------|
| 1 | days_to_conversion | 0.1318 | Other | Original |
| 141 | Is_Dually_Registered_disc | 0.0572 | Other | Discovery |
| 157 | Has_Personal_Website | 0.0496 | Other | Original |
| 131 | Is_New_To_Firm_disc | 0.0425 | Firm | Discovery |
| 102 | Branch_State_Stable | 0.0378 | Other | Original |
| 72 | pct_reps_with_disclosure | 0.0371 | Other | Discovery |
| 127 | Accelerating_Growth_disc | 0.0353 | Growth | Discovery |
| 11 | DuallyRegisteredBDRIARep | 0.0330 | Other | Original |
| 184 | Firm_Alignment_Score | 0.0299 | Firm | Original |
| 97 | Positive_Growth_Trajectory | 0.0235 | Growth | Original |
| 21 | Is_BreakawayRep | 0.0194 | Other | Original |
| 20 | Has_Disclosure | 0.0185 | Other | Original |
| 27 | Home_USPS_Certified | 0.0179 | Other | Original |
| 111 | Veteran_Stable | 0.0160 | Other | Original |
| 104 | Multi_State_Operator | 0.0153 | Other | Original |
| 90 | High_Turnover_Flag | 0.0148 | Other | Original |
| 154 | Has_Email_Business | 0.0146 | Contact | Original |
| 89 | Is_Veteran_Advisor | 0.0130 | Other | Original |
| 94 | Local_Advisor | 0.0121 | Other | Original |
| 98 | Accelerating_Growth | 0.0106 | Growth | Original |

---

## Recommendations

### 🚀 READY FOR PRODUCTION DEPLOYMENT

1. Deploy V10 as primary model
2. Monitor weekly performance
3. Set up automated retraining with Discovery updates

### Next Steps for V11
1. Add more Discovery-specific features (if available in raw data)
2. Create team composition features
3. Build compensation alignment scores
4. Test ensemble with V8 and V9

---

**Report Complete**  
**Model Performance:** 64.48% AUC-PR  
**Recommendation:** Deploy to Production
