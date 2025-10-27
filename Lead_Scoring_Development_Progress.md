# Lead Scoring Model Development Progress & Next Steps

**Project:** Savvy Wealth Lead Scoring Engine (Contacted → MQL)  
**Current Status:** Phase 0, Week 2 Complete - Feature Engineering Pipeline Implemented  
**Last Updated:** October 27, 2025  
**Next Phase:** Phase 0, Week 3 - Validation & Baseline Metrics  

---

## 🎯 **Project Overview**

We are implementing a **single, high-leverage lead scoring model** that predicts whether a **Contacted** lead will become an **MQL** (i.e., will schedule an initial discovery call). The model leverages **67 engineered features** from discovery data including firmographics, growth metrics, and operational indicators.

**Target:** +50% lift in **MQLs/100 dials** for treatment vs control at p<0.05.

### **30-Day Outcome Window Rationale**

The **30-day outcome window** is a critical modeling decision that defines when we consider a lead conversion to be "valid" for our model:

**Why 30 Days?**
- **Business Reality:** Most MQL conversions happen quickly after initial contact
- **Model Performance:** Including very late conversions can hurt model accuracy  
- **Actionable Insights:** We want to predict leads that will convert within a reasonable timeframe

**What It Means:**
- **Contacted Lead:** Someone enters "Contacting" stage on Day 0
- **30-Day Window:** We only count conversions that happen within 30 days of contact
- **Late Conversions:** Any conversions after 30 days are excluded from our positive class

**From Our Analysis:**
- **All-time conversions:** 2,111 MQLs
- **30-day window conversions:** 1,902 MQLs (90.1% of all conversions)
- **Late conversions:** 209 MQLs (9.9% excluded)

This means **90.1% of conversions happen within 30 days**, so the 30-day window captures the vast majority while excluding outliers that might confuse the model.

**Real-World Application:**
When the model scores a **new lead** (contacted today), it will predict:
- **"Will this lead convert to MQL within 30 days?"**
- **Not:** "Will this lead ever convert?" (which could take 6+ months)

This makes the model more actionable for your sales team - they can focus on leads likely to convert quickly rather than waiting indefinitely.

---

## ✅ **COMPLETED WORK**

### **Phase 0: Data Foundation**

#### **Week 1: Discovery Data Pipeline Implementation** ✅ COMPLETE
- **✅ Created BigQuery dataset structure:**
  - `savvy-gtm-analytics.LeadScoring` (processing tables)
  - `savvy-gtm-analytics.SavvyGTMData` (core CRM data)
- **✅ Uploaded MarketPro data (T1, T2, T3 territories):**
  - T1: 198,024 records (41.4%)
  - T2: 173,631 records (36.3%) 
  - T3: 106,246 records (22.2%)
  - **Total: 477,901 records**
- **✅ Created `discovery_reps_current` table** with SAFE_CAST handling for data quality issues
- **✅ Resolved "Osseo" data issue** using SAFE_CAST for numeric conversions
- **✅ Implemented proper deduplication** (462,825 unique reps from 477,901 records)

#### **Week 2: Feature Engineering Pipeline** ✅ COMPLETE
- **✅ Implemented 3-stage feature engineering architecture:**
  - **Stage 1:** 31 base features (direct mapping from discovery data)
  - **Stage 2:** 5 geographic features (metropolitan area dummy variables)
  - **Stage 3:** 31 advanced features (complex derived metrics and ratios)
- **✅ Created `discovery_reps_with_features` table** with all 67 engineered features
- **✅ Passed Week 2 validation checkpoints:**
  - Multicollinearity: All correlations < 0.95 (ACCEPTABLE)
  - Feature Distribution: Proper data ranges and distributions
  - Feature Quality: All engineered features working correctly

### **Key Data Quality Metrics Achieved:**
- **Data Completeness:** RepCRD (100%), AUM (93.3%), Growth Rates (90.3%)
- **Feature Coverage:** All 67 engineered features successfully created
- **Geographic Distribution:** NYC (3.8%), LA (1.5%), Chicago (1.6%), Dallas (2.0%), Miami (1.4%)
- **Professional Credentials:** Series 7 (69.1%), CFP (17.4%), Primary RIA (96.8%)

---

## 🚧 **REMAINING WORK**

### **Phase 0, Week 3: Validation & Baseline Metrics** (CURRENT PHASE)

#### **Step 3.1: Class Distribution Analysis** ✅ COMPLETE

**✅ COMPLETED:** Comprehensive class distribution analysis completed on October 27, 2025.

**Key Findings:**
- **Overall Conversion Rate:** 4.32% (all time) → 3.89% (30-day window)
- **Class Imbalance Ratio:** 24.18:1 (negative:positive) - SEVERE imbalance
- **Discovery Data Coverage:** 94.82% CRD matching rate - EXCELLENT
- **AUM Tier Performance:** Smaller firms convert higher (<$100M: 6.13% vs >$500M: 3.58%)
- **Metro Area Performance:** Major metros underperform (NYC: 2.72%, LA: 2.60%)
- **Temporal Patterns:** Weekend contacts show premium (Saturday: 8.72% vs weekday avg: 4.3%)

**Critical Insights:**
- **Severe class imbalance** requires sophisticated SMOTE vs. Pos_Weight testing
- **Segment variations** suggest need for AUM tier-specific modeling
- **Data quality issues** detected (negative days to conversion)
- **Modeling dataset:** 40,595 samples ready for Phase 1

**Files Created:**
- `Step_3_1_Class_Distribution_Analysis.sql` - Complete analysis queries
- `Step_3_1_Class_Distribution_Analysis_Results.md` - Comprehensive results summary

**Status:** ✅ **READY FOR STEP 3.2**

#### **Step 3.2: Temporal Leakage Detection**

**Cursor.ai Prompt:**
```
"Implement temporal leakage detection to ensure our discovery data doesn't contain future information that would bias our model. Create SQL queries to:

1. Check if any discovery data timestamps are after the contacted timestamp
2. Validate that all discovery features are based on historical data only
3. Ensure no future data leakage in our engineered features
4. Create a comprehensive leakage report with specific examples

This is critical for model integrity - we must ensure all features are available at the time of prediction."
```

**Expected SQL Implementation:**
```sql
-- Week 3 Validation Checkpoint 3.2: Temporal Leakage Detection
SELECT 
    'Future Data Leakage Check' as validation_type,
    COUNT(*) as total_records,
    COUNT(CASE 
        WHEN dd.processed_at > sf.Stage_Entered_Contacting__c 
        THEN 1 
    END) as leakage_records,
    ROUND(COUNT(CASE 
        WHEN dd.processed_at > sf.Stage_Entered_Contacting__c 
        THEN 1 
    END) / COUNT(*) * 100, 2) as leakage_rate_percent
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;
```

#### **Step 3.3: SMOTE/Class Balancing Validation**

**Cursor.ai Prompt:**
```
"Prepare for class imbalance handling by analyzing our dataset and implementing the comprehensive SMOTE vs Pos_Weight testing framework from the plan. Create SQL queries to:

1. Calculate exact class imbalance ratios
2. Analyze the distribution of positive vs negative samples
3. Prepare data for SMOTE and Pos_Weight testing
4. Create validation queries to monitor class balancing effectiveness

Follow the plan's Section 5.6 comprehensive framework for testing both approaches."
```

**Expected SQL Implementation:**
```sql
-- Week 3 Validation Checkpoint 3.3: SMOTE/Class Balancing Validation
SELECT 
    'Class Imbalance Metrics' as metric_type,
    COUNT(*) as total_samples,
    COUNT(CASE WHEN target_label = 1 THEN 1 END) as positive_samples,
    COUNT(CASE WHEN target_label = 0 THEN 1 END) as negative_samples,
    ROUND(COUNT(CASE WHEN target_label = 1 THEN 1 END) / COUNT(*) * 100, 2) as positive_class_percent,
    ROUND(COUNT(CASE WHEN target_label = 0 THEN 1 END) / COUNT(CASE WHEN target_label = 1 THEN 1 END), 2) as imbalance_ratio
FROM (
    SELECT 
        sf.Id,
        CASE 
            WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL 
            AND DATE(sf.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(sf.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
            THEN 1 
            ELSE 0 
        END as target_label
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
    WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
        AND DATE(sf.Stage_Entered_Contacting__c) <= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
);
```

---

### **Phase 1: Model Development** (3 weeks)

#### **Week 4: Feature Selection and Model Training**

**Cursor.ai Prompt:**
```
"Implement comprehensive feature selection and model training using our 67 engineered features. Create Python code to:

1. Implement univariate screening (remove features with IV < 0.02)
2. Perform multicollinearity checks (VIF < 10 for continuous features)
3. Apply recursive feature elimination (top 50 features by SHAP importance)
4. Train XGBoost models with expanded hyperparameter grid
5. Implement blocked time-series CV with 30-day gaps
6. Test both SMOTE and Pos_Weight approaches systematically

Follow the plan's Section 6 modeling specifications exactly, ensuring we handle the 100+ features properly."
```

**Expected Implementation:**
```python
# Feature Selection Pipeline
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb

def feature_selection_pipeline(X, y):
    # 1. Univariate screening
    selector = SelectKBest(f_classif, k=50)
    X_selected = selector.fit_transform(X, y)
    
    # 2. Multicollinearity check
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    vif_data = pd.DataFrame()
    vif_data["Feature"] = X.columns
    vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(len(X.columns))]
    
    # 3. Recursive feature elimination
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rfe = RFE(rf, n_features_to_select=50)
    X_rfe = rfe.fit_transform(X_selected, y)
    
    return X_rfe, rfe.support_
```

#### **Week 5: Calibration and SHAP Analysis**

**Cursor.ai Prompt:**
```
"Implement segment-aware calibration and comprehensive SHAP analysis for model explainability. Create Python code to:

1. Fit segment-specific calibrators for AUM tiers (<$100M, $100-500M, >$500M)
2. Generate SHAP summary plots for top 30 features
3. Create per-prediction SHAP explanations
4. Implement cohort analysis by AUM tier, growth trajectory, metro area
5. Persist top 5 positive drivers per prediction for Salesforce tooltips

Follow the plan's Section 7 calibration procedures and Section 6.5 explainability requirements."
```

#### **Week 6: Backtesting and Performance Validation**

**Cursor.ai Prompt:**
```
"Implement comprehensive backtesting and performance validation to ensure model stability over time. Create Python code to:

1. Perform temporal performance stability analysis
2. Validate business impact metrics (MQLs per 100 dials)
3. Detect overfitting using train vs test performance gaps
4. Implement cross-validation performance consistency checks
5. Generate comprehensive performance reports

Follow the plan's Section 7.1 validation metrics and ensure we meet the success criteria."
```

---

### **Phase 2: Pre-Production** (2 weeks)

#### **Week 7: Shadow Scoring and Pipeline Stress Testing**

**Cursor.ai Prompt:**
```
"Implement shadow scoring mode and comprehensive pipeline stress testing. Create Python code to:

1. Run shadow mode scoring for 7 days
2. Implement pipeline stress tests for data volume and quality
3. Monitor shadow mode performance metrics
4. Validate class imbalance handling in production-like environment
5. Create automated alerting for performance degradation

Follow the plan's Phase 2 validation checkpoints and ensure production readiness."
```

#### **Week 8: SGA Training and Salesforce Integration**

**Cursor.ai Prompt:**
```
"Prepare Salesforce integration and SGA training materials. Create:

1. Salesforce field mapping for all 67 discovery features
2. SGA training materials for discovery data interpretation
3. Feature importance cheat sheet
4. 'What moves the needle' playbook by segment
5. Salesforce UI updates for lead scoring display

Follow the plan's Section 11 Salesforce enablement requirements."
```

---

### **Phase 3: Experiment** (4 weeks)

#### **Weeks 9-12: Randomized A/B Test**

**Cursor.ai Prompt:**
```
"Implement comprehensive A/B testing framework with full monitoring. Create Python code to:

1. Implement lead-level randomization with blocking by AUM tier
2. Ensure balanced discovery data coverage in treatment/control
3. Monitor primary KPI: MQLs per 100 dials within 30 days
4. Implement interim analysis at week 10
5. Perform final analysis with statistical significance testing

Follow the plan's Section 8 experiment design specifications exactly."
```

---

### **Phase 4: Production & Scale** (Ongoing)

#### **Week 13+: Full Rollout**

**Cursor.ai Prompt:**
```
"Implement full production rollout with continuous monitoring. Create:

1. Daily production health checks
2. Weekly class imbalance monitoring
3. Monthly feature drift detection
4. Automated alerting for performance degradation
5. Quarterly model refresh cycles

Follow the plan's Section 9 monitoring and governance requirements."
```

---

## 🔍 **CRITICAL QA/QC CHECKPOINTS**

### **Data Quality Validation (Between Each Phase)**

**Cursor.ai Prompt:**
```
"Run comprehensive data quality validation between phases. Create SQL queries to:

1. Validate CRD matching rates between Salesforce and Discovery data
2. Check data completeness for all 67 features
3. Monitor feature drift using Population Stability Index (PSI)
4. Validate no data leakage in temporal features
5. Ensure proper class distribution maintenance

Use the plan's validation checkpoints from Section 13 Implementation Roadmap."
```

### **Statistical Validation (Before Model Training)**

**Cursor.ai Prompt:**
```
"Perform comprehensive statistical validation before model training. Create Python code to:

1. Check for multicollinearity using VIF analysis
2. Validate feature distributions and outliers
3. Ensure proper train/test split methodology
4. Validate class imbalance handling approaches
5. Check for data leakage using temporal validation

Follow statistical best practices and the plan's validation requirements."
```

### **Model Performance Validation (After Each Training)**

**Cursor.ai Prompt:**
```
"Validate model performance after each training iteration. Create Python code to:

1. Calculate AUC-PR, AUC-ROC, precision@10%, recall@10%
2. Validate calibration error across segments
3. Check for overfitting using train vs validation performance
4. Monitor feature importance stability
5. Validate business impact metrics

Ensure we meet the plan's success criteria from Section 14."
```

---

## 📊 **SUCCESS CRITERIA TRACKING**

### **Technical Success Metrics**
- **AUC-PR > 0.35** (vs ~0.20 baseline)
- **Tier A precision > 15%** (vs 6% base rate)
- **<5% feature drift** week-over-week
- **>80% discovery data coverage**

### **Business Success Metrics**
- **>50% lift in MQLs/100 dials** (treatment vs control)
- **>$2M incremental pipeline** (attributed)
- **>75% SGA adoption** (calling in tier order)
- **<10% increase in time-to-first-touch**

### **Operational Success Metrics**
- **<2% pipeline failures** per month
- **<4 hour recovery time** for any failure
- **>95% daily scoring success rate**
- **<1 day latency** for new feature deployment

---

## 🚨 **CRITICAL RISKS & MITIGATION**

### **Data Quality Risks**
- **Risk:** Discovery vendor data delays
- **Mitigation:** Cache last-known-good; fallback models
- **Monitoring:** Daily data freshness checks

### **Model Performance Risks**
- **Risk:** Feature importance instability
- **Mitigation:** Ensemble methods; longer training windows
- **Monitoring:** Weekly SHAP stability analysis

### **Business Adoption Risks**
- **Risk:** SGA non-compliance
- **Mitigation:** Incentive alignment; UI enforcement
- **Monitoring:** Daily adoption rate tracking

---

## 📋 **NEXT IMMEDIATE STEPS**

1. **Complete Phase 0, Week 3** - Class distribution analysis and temporal leakage detection
2. **Begin Phase 1, Week 4** - Feature selection and model training
3. **Implement comprehensive validation** at each checkpoint
4. **Monitor data quality** continuously throughout development
5. **Prepare for A/B testing** framework implementation

---

## 🔗 **KEY RESOURCES**

- **Main Plan:** `savvy_lead_scoring_plan.md`
- **Feature Engineering SQL:** `create_discovery_reps_with_features.sql`
- **Data Upload Script:** `upload_discovery_data.py`
- **Current Tables:** 
  - `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` (477,901 records, 67 features)
  - `savvy-gtm-analytics.LeadScoring.discovery_reps_current` (base data)
  - `savvy-gtm-analytics.SavvyGTMData.Lead` (Salesforce data)

---

**Note:** This document should be updated after each major milestone to reflect current progress and any lessons learned that affect future development steps.
