"""
LinkedIn Self Sourced vs Provided Lead List Signal Analysis

This script analyzes what signals/characteristics distinguish LinkedIn Self Sourced leads
from Provided Lead List leads. This helps understand what people are looking for when
they manually source leads from LinkedIn.

Approach:
1. Load leads with LeadSource field
2. Filter for "LinkedIn (Self Sourced)" vs "Provided Lead List"
3. Join with Discovery data (point-in-time)
4. Train classification model to predict lead source
5. Analyze feature importance to identify distinguishing signals
"""

import pandas as pd
import numpy as np
from google.cloud import bigquery
from datetime import datetime
import warnings
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import xgboost as xgb

warnings.filterwarnings('ignore')

# ========================================
# CONFIGURATION
# ========================================

PROJECT = 'savvy-gtm-analytics'
DATASET = 'LeadScoring'
LEAD_TABLE = f"{PROJECT}.SavvyGTMData.Lead"
OUTPUT_DIR = Path("C:/Users/russe/Documents/Lead Scoring")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Use the view for point-in-time joins
DISCOVERY_REPS_VIEW = f'{PROJECT}.{DATASET}.v_discovery_reps_all_vintages'

print("="*60)
print("LINKEDIN VS PROVIDED LEAD LIST SIGNAL ANALYSIS")
print("="*60)
print(f"Lead Source: {LEAD_TABLE}")
print(f"Filter Period: 2024-01-01 to 2025-09-30")
print(f"Target: Predict LeadSource (LinkedIn Self Sourced vs Provided Lead List)")
print("="*60)

client = bigquery.Client(project=PROJECT)

# ========================================
# STEP 1: LOAD LEADS WITH LEADSOURCE
# ========================================

print("\n[STEP 1] LOADING LEADS WITH LEADSOURCE")
print("-"*40)

query = f"""
WITH leads_filtered AS (
    SELECT 
        Id,
        FA_CRD__c,
        LeadSource,
        Stage_Entered_Contacting__c,
        Stage_Entered_New__c,
        CreatedDate,
        -- FilterDate: use earliest of CreatedDate, Stage_Entered_New__c, or Stage_Entered_Contacting__c
        COALESCE(
            Stage_Entered_Contacting__c,
            Stage_Entered_New__c,
            CreatedDate,
            TIMESTAMP('1900-01-01')
        ) AS FilterDate,
        -- Target: LinkedIn Self Sourced = 1, Provided Lead List = 0
        CASE 
            WHEN LeadSource = 'LinkedIn (Self Sourced)' THEN 1
            WHEN LeadSource = 'Provided Lead List' THEN 0
            ELSE NULL
        END as is_linkedin_sourced
    FROM 
        `{LEAD_TABLE}`
    WHERE 
        FA_CRD__c IS NOT NULL
        AND Stage_Entered_Contacting__c IS NOT NULL
        AND DATE(Stage_Entered_Contacting__c) >= '2024-01-01'
        AND DATE(Stage_Entered_Contacting__c) <= '2025-09-30'
        AND LeadSource IN ('LinkedIn (Self Sourced)', 'Provided Lead List')
),
leads_with_snapshot AS (
    -- Point-in-time join: get most recent snapshot <= contact date
    SELECT 
        l.*,
        reps.* EXCEPT(RepCRD, snapshot_at)
    FROM 
        leads_filtered l
    LEFT JOIN 
        `{DISCOVERY_REPS_VIEW}` reps
    ON 
        reps.RepCRD = l.FA_CRD__c
        AND DATE(reps.snapshot_at) <= DATE(l.Stage_Entered_Contacting__c)
    QUALIFY 
        ROW_NUMBER() OVER (
            PARTITION BY l.Id 
            ORDER BY reps.snapshot_at DESC
        ) = 1
),
engineered_features AS (
    SELECT 
        *,
        -- Multi-RIA relationships
        CASE 
            WHEN NumberRIAFirmAssociations > 1 THEN 1 
            ELSE 0 
        END as Multi_RIA_Relationships,
        -- License count
        COALESCE(Has_Series_7, 0) + 
        COALESCE(Has_Series_65, 0) + 
        COALESCE(Has_Series_66, 0) + 
        COALESCE(Has_Series_24, 0) as license_count,
        -- Designation count
        COALESCE(Has_CFP, 0) + 
        COALESCE(Has_CFA, 0) + 
        COALESCE(Has_CIMA, 0) + 
        COALESCE(Has_AIF, 0) as designation_count,
        -- Firm stability
        CASE 
            WHEN DateBecameRep_NumberOfYears > 0 
            THEN DateOfHireAtCurrentFirm_NumberOfYears / DateBecameRep_NumberOfYears 
            ELSE 0 
        END as Firm_Stability_Score,
        -- Growth indicators
        CASE WHEN AUMGrowthRate_1Year > 0.15 THEN 1 ELSE 0 END as Positive_Growth,
        CASE WHEN AUMGrowthRate_1Year > 0.30 THEN 1 ELSE 0 END as High_Growth,
        -- Temporal features
        EXTRACT(DAYOFWEEK FROM FilterDate) as contact_dow,
        EXTRACT(MONTH FROM FilterDate) as contact_month,
        EXTRACT(QUARTER FROM FilterDate) as contact_quarter,
        -- Contactability
        COALESCE(Has_LinkedIn, 0) as has_linkedin,
        -- Career stage
        CASE WHEN DateBecameRep_NumberOfYears >= 20 THEN 1 ELSE 0 END as is_veteran_advisor,
        CASE WHEN DateOfHireAtCurrentFirm_NumberOfYears < 1 THEN 1 ELSE 0 END as is_new_to_firm,
        -- Complex registration
        CASE WHEN Number_RegisteredStates > 3 THEN 1 ELSE 0 END as complex_registration,
        CASE WHEN Number_RegisteredStates > 1 THEN 1 ELSE 0 END as multi_state_registered,
        -- Remote work indicator
        CASE 
            WHEN Home_State IS NOT NULL 
                AND Branch_State IS NOT NULL 
                AND Home_State != Branch_State 
            THEN 1 
            ELSE 0 
        END as remote_work_indicator
    FROM 
        leads_with_snapshot
)
SELECT 
    *
FROM 
    engineered_features
WHERE 
    is_linkedin_sourced IS NOT NULL
ORDER BY 
    FilterDate
"""

print("Executing query with point-in-time joins...")
print("This may take a few minutes...")
df = client.query(query).to_dataframe()

print(f"\n[OK] Loaded {len(df):,} leads with Discovery data")
print(f"  - Date range: {df['FilterDate'].min().date()} to {df['FilterDate'].max().date()}")

# Check class distribution
target_col = 'is_linkedin_sourced'
linkedin_count = df[target_col].sum()
provided_count = (df[target_col] == 0).sum()
linkedin_pct = linkedin_count / len(df) * 100

print(f"  - LinkedIn (Self Sourced): {linkedin_count:,} ({linkedin_pct:.1f}%)")
print(f"  - Provided Lead List: {provided_count:,} ({100-linkedin_pct:.1f}%)")

# ========================================
# STEP 2: FEATURE SELECTION
# ========================================

print("\n[STEP 2] FEATURE SELECTION")
print("-"*40)

# Identify columns to exclude
id_cols = ['Id', 'FA_CRD__c', 'RepCRD', 'DiscoveryRepID', 'FullName', 'FirstName', 'LastName',
           'RIAFirmName', 'FilterDate', 'CreatedDate', 'Stage_Entered_Contacting__c', 
           'Stage_Entered_New__c', 'snapshot_date', 'LeadSource', 'is_linkedin_sourced']

target_cols = ['is_linkedin_sourced']

timestamp_cols = [col for col in df.columns if 'stage_entered' in col.lower() or 
                  'date' in col.lower() or 'timestamp' in col.lower() or 'snapshot' in col.lower()]

# Missing Data Features (0% coverage - all NULL)
MISSING_DATA_TO_DROP = [
    'TotalAssetsInMillions',
    'AUMGrowthRate_1Year',
    'AUMGrowthRate_5Year',
    'AssetsInMillions_Individuals',
    'AssetsInMillions_HNWIndividuals',
    'NumberClients_Individuals',
    'NumberClients_HNWIndividuals',
    'AUM_per_Client_v12',
    'HNW_Concentration_v12',
]

# PII Drop List
PII_TO_DROP = [
    'Home_ZipCode', 'Branch_ZipCode',
    'Home_Latitude', 'Home_Longitude',
    'Branch_Latitude', 'Branch_Longitude',
    'Branch_City', 'Home_City',
    'Branch_County', 'Home_County',
    'RIAFirmName', 'PersonalWebpage', 'Notes',
    'Home_Zip_3Digit',
    'MilesToWork',
]

# High cardinality geographic features
HIGH_CARDINALITY_TO_DROP = [
    'Home_MetropolitanArea',
]

# Get feature columns
all_cols = df.columns.tolist()
exclude_all = list(set(id_cols + target_cols + timestamp_cols + PII_TO_DROP + 
                       HIGH_CARDINALITY_TO_DROP + MISSING_DATA_TO_DROP))
feature_cols = [col for col in all_cols if col not in exclude_all]

print(f"Total columns: {len(all_cols)}")
print(f"Excluded: {len(exclude_all)}")
print(f"Features: {len(feature_cols)}")

# Filter to numeric and low-cardinality categorical
numeric_features = []
categorical_features = []

for col in feature_cols:
    if col in df.columns:
        if df[col].dtype in ['int64', 'float64', 'bool']:
            numeric_features.append(col)
            # Fill missing values
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)
            # Replace inf
            df[col] = df[col].replace([np.inf, -np.inf], 0)
        elif df[col].dtype == 'object' and df[col].nunique() < 20:
            categorical_features.append(col)

print(f"  - Numeric features: {len(numeric_features)}")
print(f"  - Categorical features: {len(categorical_features)}")

# One-hot encode categoricals
for col in categorical_features:
    if col in ['Home_State', 'Branch_State', 'Office_State']:
        # Only top 5 states
        top_values = df[col].value_counts().head(5).index
    elif col == 'Gender':
        # Binary encoding for Gender
        df['Gender_Male'] = (df[col] == 'Male').astype(int)
        df['Gender_Missing'] = (df[col].isna() | ((df[col] != 'Male') & (df[col] != 'Female'))).astype(int)
        numeric_features.append('Gender_Male')
        numeric_features.append('Gender_Missing')
        print(f"  [OK] Encoded {col}: Created Gender_Male and Gender_Missing")
        continue
    else:
        top_values = df[col].value_counts().head(10).index
    
    for val in top_values:
        if pd.notna(val):
            new_col = f"{col}_{str(val)[:20].replace(' ', '_').replace('-', '_')}"
            df[new_col] = (df[col] == val).astype(int)
            numeric_features.append(new_col)

# Final feature set
final_features = [f for f in numeric_features if f in df.columns]
print(f"Final feature count: {len(final_features)}")

# Ensure all features are numeric and finite
X_data = df[final_features].values
X_data = np.nan_to_num(X_data, nan=0.0, posinf=0.0, neginf=0.0)
y_data = df[target_col].values

# ========================================
# STEP 3: TRAIN/TEST SPLIT
# ========================================

print("\n[STEP 3] TRAIN/TEST SPLIT")
print("-"*40)

# Temporal split (80/20)
df = df.sort_values('FilterDate')
split_idx = int(len(df) * 0.8)

X_train = X_data[:split_idx]
y_train = y_data[:split_idx]
X_test = X_data[split_idx:]
y_test = y_data[split_idx:]

print(f"Train: {len(X_train):,} samples")
print(f"  - LinkedIn: {(y_train == 1).sum():,} ({(y_train == 1).mean()*100:.1f}%)")
print(f"  - Provided: {(y_train == 0).sum():,} ({(y_train == 0).mean()*100:.1f}%)")
print(f"Test: {len(X_test):,} samples")
print(f"  - LinkedIn: {(y_test == 1).sum():,} ({(y_test == 1).mean()*100:.1f}%)")
print(f"  - Provided: {(y_test == 0).sum():,} ({(y_test == 0).mean()*100:.1f}%)")

# ========================================
# STEP 4: MODEL TRAINING
# ========================================

print("\n[STEP 4] MODEL TRAINING")
print("-"*40)

# Adjust class weight based on imbalance
scale_pos_weight = (1 - y_train.mean()) / y_train.mean()
print(f"Scale pos weight: {scale_pos_weight:.2f}")

# XGBoost parameters
xgb_params = {
    'max_depth': 6,
    'n_estimators': 500,
    'learning_rate': 0.03,
    'subsample': 0.7,
    'colsample_bytree': 0.7,
    'reg_alpha': 0.5,
    'reg_lambda': 1.0,
    'gamma': 1.0,
    'min_child_weight': 3,
    'scale_pos_weight': scale_pos_weight,
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'random_state': 42,
    'tree_method': 'hist'
}

print("Training XGBoost model...")
xgb_model = xgb.XGBClassifier(**xgb_params)
eval_set = [(X_test, y_test)]

xgb_model.fit(
    X_train, y_train,
    eval_set=eval_set,
    verbose=False
)

# ========================================
# STEP 5: EVALUATION
# ========================================

print("\n[STEP 5] MODEL EVALUATION")
print("-"*40)

# Predictions
y_pred = xgb_model.predict(X_test)
y_pred_proba = xgb_model.predict_proba(X_test)[:, 1]

# Metrics
auc_roc = roc_auc_score(y_test, y_pred_proba)
print(f"AUC-ROC: {auc_roc:.4f}")

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Provided Lead List', 'LinkedIn Self Sourced']))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# ========================================
# STEP 6: FEATURE IMPORTANCE ANALYSIS
# ========================================

print("\n[STEP 6] FEATURE IMPORTANCE ANALYSIS")
print("-"*40)

if hasattr(xgb_model, 'feature_importances_'):
    importance_df = pd.DataFrame({
        'feature': final_features,
        'importance': xgb_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    # Calculate normalized importance (percentage)
    total_importance = importance_df['importance'].sum()
    importance_df['importance_pct'] = (importance_df['importance'] / total_importance * 100)
    
    print("\nTop 30 Features That Distinguish LinkedIn Self Sourced Leads:")
    print("-"*80)
    for i, (idx, row) in enumerate(importance_df.head(30).iterrows(), 1):
        print(f"{i:2d}. {row['feature']:50s} {row['importance']:.4f} ({row['importance_pct']:.2f}%)")
    
    # Analyze what LinkedIn leads have more/less of
    print("\n" + "="*80)
    print("SIGNAL ANALYSIS: What Makes LinkedIn Leads Different?")
    print("="*80)
    
    # Compare feature means between LinkedIn and Provided leads
    linkedin_mask = df[target_col] == 1
    provided_mask = df[target_col] == 0
    
    signal_analysis = []
    for feat in importance_df.head(30)['feature']:
        if feat in df.columns:
            linkedin_mean = df.loc[linkedin_mask, feat].mean()
            provided_mean = df.loc[provided_mask, feat].mean()
            diff = linkedin_mean - provided_mean
            diff_pct = (diff / provided_mean * 100) if provided_mean != 0 else 0
            
            signal_analysis.append({
                'feature': feat,
                'importance': importance_df[importance_df['feature'] == feat]['importance'].iloc[0],
                'linkedin_mean': linkedin_mean,
                'provided_mean': provided_mean,
                'difference': diff,
                'difference_pct': diff_pct
            })
    
    signal_df = pd.DataFrame(signal_analysis).sort_values('importance', ascending=False)
    
    print("\nTop Signals (LinkedIn vs Provided Lead List):")
    print("-"*80)
    print(f"{'Feature':<50s} {'LinkedIn':>12s} {'Provided':>12s} {'Diff':>12s} {'Diff %':>10s}")
    print("-"*80)
    
    for _, row in signal_df.head(20).iterrows():
        direction = "↑" if row['difference'] > 0 else "↓"
        print(f"{row['feature']:<50s} {row['linkedin_mean']:>12.3f} {row['provided_mean']:>12.3f} "
              f"{row['difference']:>+12.3f} {row['difference_pct']:>+9.1f}% {direction}")

# ========================================
# STEP 7: GENERATE REPORT
# ========================================

print("\n[STEP 7] GENERATING REPORT")
print("-"*40)

timestamp = datetime.now().strftime("%Y%m%d_%H%M")

report_content = f"""# LinkedIn Self Sourced vs Provided Lead List Signal Analysis

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Purpose:** Identify what signals/characteristics distinguish LinkedIn Self Sourced leads from Provided Lead List leads

---

## Executive Summary

This analysis uses a classification model to predict whether a lead came from "LinkedIn (Self Sourced)" or "Provided Lead List" based on lead characteristics. The model identifies which features are most predictive, revealing what signals people are looking for when they manually source leads from LinkedIn.

### Key Results

- **Model Performance:** AUC-ROC = {auc_roc:.4f}
- **Training Samples:** {len(X_train):,} leads
- **Test Samples:** {len(X_test):,} leads
- **LinkedIn Leads:** {linkedin_count:,} ({linkedin_pct:.1f}%)
- **Provided Lead List Leads:** {provided_count:,} ({100-linkedin_pct:.1f}%)

---

## Model Performance

### Classification Metrics

**AUC-ROC:** {auc_roc:.4f}

**Interpretation:**
- AUC-ROC > 0.70: Model can distinguish between sources
- AUC-ROC > 0.80: Strong predictive power
- AUC-ROC > 0.90: Excellent predictive power

---

## Top Signals That Distinguish LinkedIn Self Sourced Leads

### Top 30 Most Important Features

| Rank | Feature | Importance | % of Total |
|------|---------|------------|------------|
"""

if hasattr(xgb_model, 'feature_importances_'):
    for i, (idx, row) in enumerate(importance_df.head(30).iterrows(), 1):
        report_content += f"| {i} | `{row['feature']}` | {row['importance']:.4f} | {row['importance_pct']:.2f}% |\n"

report_content += f"""
---

## Signal Analysis: What Makes LinkedIn Leads Different?

### Comparison of Feature Means

| Feature | LinkedIn Mean | Provided Mean | Difference | Difference % | Direction |
|---------|---------------|---------------|------------|--------------|-----------|
"""

if hasattr(xgb_model, 'feature_importances_'):
    for _, row in signal_df.head(20).iterrows():
        direction = "↑ Higher" if row['difference'] > 0 else "↓ Lower"
        report_content += f"| `{row['feature']}` | {row['linkedin_mean']:.3f} | {row['provided_mean']:.3f} | {row['difference']:+.3f} | {row['difference_pct']:+.1f}% | {direction} |\n"

report_content += f"""
---

## Key Insights

### What Signals Are People Using When Sourcing LinkedIn Leads?

Based on the feature importance analysis, the following characteristics appear to be key signals:

"""

if hasattr(xgb_model, 'feature_importances_'):
    # Group features by category
    top_features = importance_df.head(15)['feature'].tolist()
    
    # Categorize features
    professional_features = [f for f in top_features if any(x in f.lower() for x in ['series', 'cfp', 'cfa', 'cima', 'license', 'designation'])]
    tenure_features = [f for f in top_features if any(x in f.lower() for x in ['tenure', 'years', 'firm', 'stability', 'prior'])]
    geographic_features = [f for f in top_features if any(x in f.lower() for x in ['state', 'home', 'branch', 'registered'])]
    relationship_features = [f for f in top_features if any(x in f.lower() for x in ['ria', 'association', 'relationship'])]
    contact_features = [f for f in top_features if any(x in f.lower() for x in ['linkedin', 'email', 'contact'])]
    other_features = [f for f in top_features if f not in professional_features + tenure_features + geographic_features + relationship_features + contact_features]
    
    if professional_features:
        report_content += f"\n**1. Professional Credentials:**\n"
        for feat in professional_features[:5]:
            report_content += f"- `{feat}`\n"
    
    if tenure_features:
        report_content += f"\n**2. Tenure & Career Stage:**\n"
        for feat in tenure_features[:5]:
            report_content += f"- `{feat}`\n"
    
    if geographic_features:
        report_content += f"\n**3. Geographic Indicators:**\n"
        for feat in geographic_features[:5]:
            report_content += f"- `{feat}`\n"
    
    if relationship_features:
        report_content += f"\n**4. Firm Relationships:**\n"
        for feat in relationship_features[:5]:
            report_content += f"- `{feat}`\n"
    
    if contact_features:
        report_content += f"\n**5. Contactability:**\n"
        for feat in contact_features[:5]:
            report_content += f"- `{feat}`\n"
    
    if other_features:
        report_content += f"\n**6. Other Signals:**\n"
        for feat in other_features[:5]:
            report_content += f"- `{feat}`\n"

report_content += f"""
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

- **Data Source:** `{LEAD_TABLE}`
- **Discovery Source:** `{DISCOVERY_REPS_VIEW}`
- **Filter Period:** 2024-01-01 to 2025-09-30
- **Total Features:** {len(final_features)}
- **Model Type:** XGBoost Classifier

---

**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Analysis Period:** 2024-01-01 to 2025-09-30
"""

report_path = OUTPUT_DIR / f"LinkedIn_vs_Provided_Signal_Analysis_{timestamp}.md"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_content)
print(f"[OK] Report saved: {report_path}")

# Save feature importance CSV
if hasattr(xgb_model, 'feature_importances_'):
    importance_path = OUTPUT_DIR / f"LinkedIn_vs_Provided_Feature_Importance_{timestamp}.csv"
    importance_df.to_csv(importance_path, index=False)
    print(f"[OK] Feature importance saved: {importance_path}")
    
    # Save signal analysis
    signal_path = OUTPUT_DIR / f"LinkedIn_vs_Provided_Signal_Analysis_{timestamp}.csv"
    signal_df.to_csv(signal_path, index=False)
    print(f"[OK] Signal analysis saved: {signal_path}")

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
print("="*60)
print(f"Model AUC-ROC: {auc_roc:.4f}")
print(f"Report: {report_path}")
print("="*60)









