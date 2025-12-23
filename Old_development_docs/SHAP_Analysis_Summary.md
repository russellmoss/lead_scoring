# SHAP Analysis Summary - Model V1 Feature Importance

**Analysis Date:** Step 4.5 Completion  
**Model:** `model_v1.pkl`  
**Method:** Permutation-based SHAP approximation (fallback due to xgboost/shap version conflict)  
**Sample Size:** 300 foreground samples (configurable)

---

## 🔍 Key Findings

### Top 10 Most Important Features

1. **`SocialMedia_LinkedIn`** (0.0376) - **Dominant Signal** (~20x higher than #2)
2. **`AUMGrowthRate_5Year`** (0.0019)
3. **`FirstName`** (0.0017)
4. **`Number_YearsPriorFirm1`** (0.0016)
5. **`Title`** (0.0015)
6. **`MilesToWork`** (0.0012)
7. **`DateBecameRep_NumberOfYears`** (0.0011)
8. **`Total_Prior_Firm_Years`** (0.0010)
9. **`DateOfHireAtCurrentFirm_NumberOfYears`** (0.0010)
10. **`Has_CFP`** (0.0010)

---

## 🚨 Critical Comparison: V1 vs. m5 Model

### **Major Discrepancy: Multi_RIA_Relationships**

**m5 Model (Previous):**
- **#1 Feature:** `Multi_RIA_Relationships` (0.0816) - Top feature
- **#6 Feature:** `Is_Veteran_Advisor` (0.0225)

**V1 Model (Current):**
- **`Multi_RIA_Relationships`**: **0.0 importance** (completely unused)
- **`Is_Veteran_Advisor`**: **0.0 importance** (completely unused)

### Why This Difference Matters:

1. **Different Training Data:**
   - m5: Trained on ~40k+ historical samples (potentially with temporal leakage)
   - V1: Trained on ~590 eligible-only samples (temporally correct)

2. **Different Feature Availability:**
   - The eligible-only cohort may have different data completeness for `Multi_RIA_Relationships`
   - This feature might not be available or populated for the recent leads

3. **Data Quality:**
   - The feature may exist in the dataset but have low variance or no predictive signal in the smaller, temporally-correct cohort

**Action Required:** Investigate `Multi_RIA_Relationships` feature availability and distribution in `step_3_3_training_dataset.csv` to understand why it has zero importance.

---

## 📊 Patterns in Individual Predictions

From `salesforce_drivers_v1.csv` (top 5 positive drivers per lead):

### Most Frequently Appearing Drivers:

1. **Career Stability Features:**
   - `DateBecameRep_NumberOfYears`
   - `DateOfHireAtCurrentFirm_NumberOfYears`
   - `Total_Prior_Firm_Years`
   - `Number_YearsPriorFirm1/2/3/4`

2. **Growth Metrics:**
   - `AUMGrowthRate_5Year` (appears in ~15% of top drivers)
   - `AUMGrowthRate_1Year`

3. **Wealth Concentration:**
   - `HNW_Asset_Concentration`

4. **Geographic Features:**
   - `Branch_State`, `Branch_City`, `Branch_ZipCode`, `Branch_Latitude`

5. **Credentials:**
   - `Has_CFP`

6. **Operational:**
   - `Custodian1`
   - `Clients_per_BranchAdvisor`
   - `AUM_Per_BranchAdvisor`

---

## ⚠️ Unexpected Zero-Importance Features

Features with **0.0 mean |SHAP|** (potentially removed by pre-filters or have no signal):

### Temporal Features:
- **`Is_Weekend_Contact`** ❌ (Despite Step 3.1 showing 8.72% weekend conversion rate)
- `Day_of_Contact` (minimal: 0.00014)

### Engineered Business Logic Features:
- `Multi_RIA_Relationships` (m5's #1 feature)
- `Is_Veteran_Advisor` (m5's #6 feature)
- `Is_Boutique_Firm`
- `Has_Scale`
- `Local_Advisor`
- `Remote_Work_Indicator`
- `Positive_Growth_Trajectory`
- `Accelerating_Growth` (minimal: 0.00019)
- `Multi_Firm_Associations`

### Registration/Relationship Flags:
- `Is_Primary_RIA`
- `Is_Large_Firm`
- `DuallyRegisteredBDRIARep`
- `Has_Schwab_Relationship`
- `Has_Pershing_Relationship`
- `Has_Fidelity_Relationship`
- `Has_TDAmeritrade_Relationship`

### Professional Designations:
- `Has_CFA`
- `Has_CIMA`
- `Has_AIF`

---

## 💡 Business Implications

### What Works:
1. **LinkedIn Presence is Strongest Signal** - Advisors with LinkedIn profiles show higher conversion likelihood
2. **Career Stability Matters** - Years of experience and firm tenure are predictive
3. **Long-term Growth > Short-term** - 5-year AUM growth more predictive than 1-year
4. **Geographic Patterns Exist** - Branch location features appear in many predictions

### What Doesn't Work (in this cohort):
1. **Multi-RIA relationships** - No predictive signal despite being m5's top feature
2. **Temporal contact timing** - Weekend contact feature unused despite observed premium
3. **Many engineered flags** - Complex business logic features have zero importance

### Recommendations:

1. **Investigate `Multi_RIA_Relationships`:**
   - Check feature availability in eligible cohort
   - Verify data quality and distribution
   - Understand why it lost importance vs. m5

2. **Review Feature Engineering:**
   - Consider removing zero-importance features from future iterations
   - Focus engineering efforts on features that actually drive predictions

3. **Validate Temporal Features:**
   - Investigate why `Is_Weekend_Contact` has zero importance despite observed premium
   - May be due to small sample size or feature interaction

4. **LinkedIn Signal Investigation:**
   - Understand why LinkedIn presence is so predictive
   - Consider incorporating this insight into sales strategy

---

## 📈 Next Steps (Week 5 Tasks)

Per the plan, Week 5 should:
1. Compare this SHAP analysis directly against m5's "Top 25 Most Important Features"
2. Document rationale for differences in `shap_feature_comparison_report_v1.md`
3. Answer: "Did the new model discover the same 'truth'?" → **No - dramatically different top features**
4. Answer: "Did `Multi_RIA_Relationships` remain the top feature?" → **No - it has zero importance**

---

## 🔧 Technical Notes

- **Method:** Permutation-based SHAP (fallback due to TreeExplainer version conflict)
- **Sample Size:** 300 foreground samples (configurable via `--fg_n`)
- **Categorical Handling:** Features cast to category dtype to match training
- **Temporal Features:** Auto-derived from `Stage_Entered_Contacting__c` if missing

---

**Files Generated:**
- `feature_importance_v1.csv` - Mean absolute SHAP per feature
- `shap_summary_plot_v1.png` - Visual bar plot of top 30 features
- `salesforce_drivers_v1.csv` - Top 5 positive drivers per sampled lead


