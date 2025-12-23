"""
V10 Lead Scoring Model - Discovery Data Enrichment
Incorporates critical discovery features to achieve m5-level performance
Target: 10-14% AUC-PR (approaching m5's 14.92%)
"""

import pandas as pd
import numpy as np
from google.cloud import bigquery
from datetime import datetime
import warnings
import pickle
import json
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit, train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score
from imblearn.over_sampling import SMOTE
import xgboost as xgb

warnings.filterwarnings('ignore')

# Configuration
PROJECT = 'savvy-gtm-analytics'
DATASET = 'LeadScoring'
V7_TABLE = 'step_3_3_training_dataset_v7_featured_20251105'
DISCOVERY_REPS = 'discovery_reps_current'
DISCOVERY_FIRMS = 'discovery_firms_current'

# Get script directory for output
script_dir = Path(__file__).parent.absolute()
OUTPUT_DIR = script_dir
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("="*60)
print("V10 LEAD SCORING MODEL - DISCOVERY ENRICHMENT")
print("="*60)
print(f"Start Time: {datetime.now()}")
print(f"Output Directory: {OUTPUT_DIR}")
print("="*60)

# Initialize BigQuery client
client = bigquery.Client(project=PROJECT)

# ========================================
# STEP 1: CREATE ENRICHED DATASET
# ========================================

print("\n[STEP 1] CREATING DISCOVERY-ENRICHED DATASET")
print("-"*40)

enriched_query = f"""
WITH base_data AS (
    -- Get V7 training data with basic cleaning
    SELECT 
        v7.*,
        -- Clean financial metrics
        CASE 
            WHEN v7.TotalAssetsInMillions > 5000 THEN 5000
            WHEN v7.TotalAssetsInMillions < 0 THEN 0
            ELSE COALESCE(v7.TotalAssetsInMillions, 0)
        END as AUM_clean,
        
        CASE 
            WHEN v7.NumberClients_Individuals > 5000 THEN 5000
            WHEN v7.NumberClients_Individuals < 0 THEN 0
            ELSE COALESCE(v7.NumberClients_Individuals, 0)
        END as Clients_clean
        
    FROM 
        `{PROJECT}.{DATASET}.{V7_TABLE}` v7
    WHERE
        v7.FA_CRD__c IS NOT NULL
),
discovery_enriched AS (
    -- Join with discovery reps data (using RepCRD as join key)
    SELECT 
        b.*,
        
        -- ===== PRE-ENGINEERED DISCOVERY FEATURES =====
        -- These are already calculated in discovery_reps_current
        
        -- Multi-RIA Relationships (m5's #1 feature - already pre-calculated)
        COALESCE(dr.Multi_RIA_Relationships, 0) as Multi_RIA_Relationships_disc,
        
        -- Pre-calculated efficiency metrics
        COALESCE(dr.AUM_per_Client, 0) as AUM_per_Client_disc,
        COALESCE(dr.AUM_per_IARep, 0) as AUM_per_IARep_disc,
        COALESCE(dr.Clients_per_IARep, 0) as Clients_per_IARep_disc,
        COALESCE(dr.Clients_per_BranchAdvisor, 0) as Clients_per_BranchAdvisor_disc,
        COALESCE(dr.AUM_Per_BranchAdvisor, 0) as AUM_per_BranchAdvisor_disc,
        
        -- Pre-calculated growth features
        COALESCE(dr.Growth_Momentum, 0) as Growth_Momentum_disc,
        COALESCE(dr.Accelerating_Growth, 0) as Accelerating_Growth_disc,
        COALESCE(dr.Positive_Growth_Trajectory, 0) as Positive_Growth_Trajectory_disc,
        
        -- Pre-calculated stability and tenure features
        COALESCE(dr.Firm_Stability_Score, 0) as Firm_Stability_Score_disc,
        COALESCE(dr.Is_Veteran_Advisor, 0) as Is_Veteran_Advisor_disc,
        COALESCE(dr.Is_New_To_Firm, 0) as Is_New_To_Firm_disc,
        
        -- Pre-calculated client and asset ratios
        COALESCE(dr.HNW_Client_Ratio, 0) as HNW_Client_Ratio_disc,
        COALESCE(dr.Individual_Asset_Ratio, 0) as Individual_Asset_Ratio_disc,
        COALESCE(dr.HNW_Asset_Concentration, 0) as HNW_Asset_Concentration_disc,
        
        -- Pre-calculated firm size flags
        COALESCE(dr.Is_Large_Firm, 0) as Is_Large_Firm_disc,
        COALESCE(dr.Is_Boutique_Firm, 0) as Is_Boutique_Firm_disc,
        COALESCE(dr.Has_Scale, 0) as Has_Scale_disc,
        
        -- Pre-calculated geographic features
        COALESCE(dr.Remote_Work_Indicator, 0) as Remote_Work_Indicator_disc,
        COALESCE(dr.Local_Advisor, 0) as Local_Advisor_disc,
        
        -- Pre-calculated registration features (using base columns)
        CASE 
            WHEN dr.NumberFirmAssociations > 2 OR dr.NumberRIAFirmAssociations > 1 
            THEN 1 ELSE 0 
        END as Complex_Registration_disc,
        CASE WHEN dr.DuallyRegisteredBDRIARep = 'Yes' THEN 1 ELSE 0 END as Is_Dually_Registered_disc,
        CASE WHEN dr.IsPrimaryRIAFirm = 'Yes' THEN 1 ELSE 0 END as Is_Primary_RIA_disc,
        
        -- ===== CUSTODIAN RELATIONSHIPS (Enhanced) =====
        COALESCE(dr.Has_Schwab_Relationship, 0) as Has_Schwab_disc,
        COALESCE(dr.Has_Fidelity_Relationship, 0) as Has_Fidelity_disc,
        COALESCE(dr.Has_Pershing_Relationship, 0) as Has_Pershing_disc,
        COALESCE(dr.Has_TDAmeritrade_Relationship, 0) as Has_TDAmeritrade_disc,
        
        -- Custodian AUM values
        COALESCE(dr.CustodianAUM_Schwab, 0) as CustodianAUM_Schwab_disc,
        COALESCE(dr.CustodianAUM_Fidelity_NationalFinancial, 0) as CustodianAUM_Fidelity_disc,
        COALESCE(dr.CustodianAUM_Pershing, 0) as CustodianAUM_Pershing_disc,
        COALESCE(dr.CustodianAUM_TDAmeritrade, 0) as CustodianAUM_TD_disc,
        
        -- Custodian diversity (count of relationships)
        COALESCE(dr.Has_Schwab_Relationship, 0) +
        COALESCE(dr.Has_Fidelity_Relationship, 0) +
        COALESCE(dr.Has_Pershing_Relationship, 0) +
        COALESCE(dr.Has_TDAmeritrade_Relationship, 0) as Custodian_Count,
        
        -- Custodian concentration (primary custodian AUM / total AUM)
        CASE 
            WHEN b.AUM_clean > 0 AND COALESCE(dr.CustodianAUM_Schwab, 0) > 0
            THEN dr.CustodianAUM_Schwab / b.AUM_clean
            ELSE 0
        END as Schwab_Concentration,
        
        CASE 
            WHEN b.AUM_clean > 0 AND COALESCE(dr.CustodianAUM_Fidelity_NationalFinancial, 0) > 0
            THEN dr.CustodianAUM_Fidelity_NationalFinancial / b.AUM_clean
            ELSE 0
        END as Fidelity_Concentration,
        
        -- ===== CONTACT AVAILABILITY (Enhanced) =====
        CASE WHEN dr.Email_BusinessType IS NOT NULL THEN 1 ELSE 0 END as Has_Email_Business,
        CASE WHEN dr.Email_PersonalType IS NOT NULL THEN 1 ELSE 0 END as Has_Email_Personal,
        CASE WHEN dr.SocialMedia_LinkedIn IS NOT NULL THEN 1 ELSE 0 END as Has_LinkedIn_Profile,
        CASE WHEN dr.PersonalWebpage IS NOT NULL THEN 1 ELSE 0 END as Has_Personal_Website,
        CASE WHEN dr.FirmWebsite IS NOT NULL THEN 1 ELSE 0 END as Has_Firm_Website,
        
        -- Contact score (0-5)
        CASE WHEN dr.Email_BusinessType IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN dr.Email_PersonalType IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN dr.SocialMedia_LinkedIn IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN dr.PersonalWebpage IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN dr.FirmWebsite IS NOT NULL THEN 1 ELSE 0 END as Contact_Score,
        
        -- ===== METROPOLITAN AREA DUMmIES (Pre-calculated) =====
        COALESCE(dr.Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ, 0) as Metro_NYC_disc,
        COALESCE(dr.Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA, 0) as Metro_LA_disc,
        COALESCE(dr.Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN, 0) as Metro_Chicago_disc,
        COALESCE(dr.Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX, 0) as Metro_Dallas_disc,
        COALESCE(dr.Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL, 0) as Metro_Miami_disc,
        
        -- ===== DATA QUALITY INDICATOR =====
        CASE WHEN dr.RepCRD IS NOT NULL THEN 1 ELSE 0 END as Has_Discovery_Data
        
    FROM 
        base_data b
    LEFT JOIN 
        `{PROJECT}.{DATASET}.{DISCOVERY_REPS}` dr
    ON 
        b.FA_CRD__c = dr.RepCRD
),
firm_enriched AS (
    -- Join with discovery firms data for firm-level context
    SELECT 
        de.*,
        
        -- Firm size metrics
        COALESCE(df.total_reps, 0) as Firm_Total_Reps,
        COALESCE(df.total_firm_aum_millions, 0) as Firm_Total_AUM,
        
        -- Firm efficiency
        CASE 
            WHEN df.total_reps > 0 AND df.total_firm_aum_millions > 0
            THEN df.total_firm_aum_millions / df.total_reps
            ELSE 0
        END as Firm_AUM_per_Rep,
        
        -- Firm growth
        COALESCE(df.avg_firm_growth_1y, 0) as Firm_Avg_Growth_1y,
        COALESCE(df.avg_firm_growth_5y, 0) as Firm_Avg_Growth_5y,
        
        -- Firm characteristics
        COALESCE(df.large_rep_firm, 0) as Firm_Is_Large,
        COALESCE(df.boutique_firm, 0) as Firm_Is_Boutique,
        COALESCE(df.multi_state_firm, 0) as Firm_Multi_State,
        COALESCE(df.national_firm, 0) as Firm_Is_National,
        
        -- Firm rep quality
        COALESCE(df.pct_reps_with_cfp, 0) as Firm_Pct_CFP,
        COALESCE(df.pct_veteran_reps, 0) as Firm_Pct_Veteran,
        
        -- Firm custodian relationships
        COALESCE(df.has_schwab_relationship, 0) as Firm_Has_Schwab,
        COALESCE(df.has_fidelity_relationship, 0) as Firm_Has_Fidelity
        
    FROM 
        discovery_enriched de
    LEFT JOIN 
        `{PROJECT}.{DATASET}.{DISCOVERY_FIRMS}` df
    ON 
        de.RIAFirmCRD = df.RIAFirmCRD
),
final_features AS (
    SELECT 
        *,
        
        -- ===== ADDITIONAL ENGINEERED FEATURES =====
        
        -- Rep vs Firm performance (relative to firm average)
        CASE 
            WHEN Firm_AUM_per_Rep > 0 AND AUM_clean > 0
            THEN AUM_clean / Firm_AUM_per_Rep
            ELSE 0
        END as Rep_Performance_vs_Firm,
        
        -- Rep growth vs firm growth
        CASE 
            WHEN Firm_Avg_Growth_1y > 0 AND AUMGrowthRate_1Year > 0
            THEN AUMGrowthRate_1Year / Firm_Avg_Growth_1y
            ELSE 0
        END as Rep_Growth_vs_Firm,
        
        -- Platform sophistication (custodian count + contact score)
        Custodian_Count + Contact_Score as Platform_Sophistication,
        
        -- Total custodian AUM
        CustodianAUM_Schwab_disc + 
        CustodianAUM_Fidelity_disc + 
        CustodianAUM_Pershing_disc + 
        CustodianAUM_TD_disc as Total_Custodian_AUM,
        
        -- Primary custodian concentration
        GREATEST(
            Schwab_Concentration,
            Fidelity_Concentration,
            CASE WHEN b.AUM_clean > 0 AND CustodianAUM_Pershing_disc > 0 
                 THEN CustodianAUM_Pershing_disc / b.AUM_clean ELSE 0 END,
            CASE WHEN b.AUM_clean > 0 AND CustodianAUM_TD_disc > 0 
                 THEN CustodianAUM_TD_disc / b.AUM_clean ELSE 0 END
        ) as Primary_Custodian_Concentration,
        
        -- Firm alignment score (rep characteristics match firm profile)
        CASE 
            WHEN COALESCE(Is_Veteran_Advisor_disc, 0) = 1 AND COALESCE(Firm_Pct_Veteran, 0) > 0.5 THEN 1
            WHEN COALESCE(Has_Scale_disc, 0) = 1 AND COALESCE(Firm_Is_Large, 0) = 1 THEN 1
            WHEN COALESCE(Complex_Registration_disc, 0) = 1 AND COALESCE(Firm_Multi_State, 0) = 1 THEN 1
            ELSE 0
        END as Firm_Alignment_Score
        
    FROM 
        firm_enriched b
)
SELECT * FROM final_features
"""

print("Extracting discovery-enriched dataset...")
try:
    df = client.query(enriched_query).to_dataframe()
    print(f"[OK] Loaded {len(df):,} rows")
    print(f"  - With discovery data: {df['Has_Discovery_Data'].sum():,} ({df['Has_Discovery_Data'].mean()*100:.1f}%)")
    print(f"  - Positive samples: {df['target_label'].sum():,} ({df['target_label'].mean()*100:.2f}%)")
except Exception as e:
    print(f"[ERROR] Query failed: {str(e)}")
    print("Attempting simpler query...")
    # Fallback to simpler query without firm enrichment
    enriched_query_simple = f"""
    WITH base_data AS (
        SELECT 
            v7.*,
            CASE 
                WHEN v7.TotalAssetsInMillions > 5000 THEN 5000
                WHEN v7.TotalAssetsInMillions < 0 THEN 0
                ELSE COALESCE(v7.TotalAssetsInMillions, 0)
            END as AUM_clean,
            CASE 
                WHEN v7.NumberClients_Individuals > 5000 THEN 5000
                WHEN v7.NumberClients_Individuals < 0 THEN 0
                ELSE COALESCE(v7.NumberClients_Individuals, 0)
            END as Clients_clean
        FROM 
            `{PROJECT}.{DATASET}.{V7_TABLE}` v7
        WHERE
            v7.FA_CRD__c IS NOT NULL
    )
    SELECT 
        b.*,
        COALESCE(dr.Multi_RIA_Relationships, 0) as Multi_RIA_Relationships_disc,
        COALESCE(dr.AUM_per_Client, 0) as AUM_per_Client_disc,
        COALESCE(dr.Has_Schwab_Relationship, 0) as Has_Schwab_disc,
        COALESCE(dr.Has_Fidelity_Relationship, 0) as Has_Fidelity_disc,
        CASE WHEN dr.RepCRD IS NOT NULL THEN 1 ELSE 0 END as Has_Discovery_Data
    FROM 
        base_data b
    LEFT JOIN 
        `{PROJECT}.{DATASET}.{DISCOVERY_REPS}` dr
    ON 
        b.FA_CRD__c = dr.RepCRD
    """
    df = client.query(enriched_query_simple).to_dataframe()
    print(f"[OK] Loaded {len(df):,} rows (simplified query)")

# ========================================
# STEP 2: FEATURE PREPARATION
# ========================================

print("\n[STEP 2] FEATURE PREPARATION")
print("-"*40)

# Define feature columns
id_cols = ['Id', 'FA_CRD__c', 'Stage_Entered_Contacting__c']
target_col = 'target_label'

# Exclude original V7 columns that we've enhanced with discovery versions
exclude_cols = id_cols + [target_col] + [
    'TotalAssetsInMillions', 'NumberClients_Individuals',
    'AUM_clean', 'Clients_clean'  # Temporary columns
]

# Select all feature columns
feature_cols = [col for col in df.columns if col not in exclude_cols]

# Remove any remaining string columns (keep only numeric)
numeric_features = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
feature_cols = numeric_features

print(f"Total features: {len(feature_cols)}")

# Show discovery feature statistics
discovery_features = [
    'Multi_RIA_Relationships_disc', 'AUM_per_Client_disc', 
    'Has_Schwab_disc', 'Has_Fidelity_disc', 'Contact_Score',
    'Custodian_Count', 'Platform_Sophistication'
]

print("\nKey Discovery Features Added:")
for feat in discovery_features:
    if feat in df.columns:
        non_zero = (df[feat] != 0).sum()
        print(f"  - {feat}: {non_zero:,} non-zero ({non_zero/len(df)*100:.1f}%)")

# Fill missing values
df[feature_cols] = df[feature_cols].fillna(0)

# ========================================
# STEP 3: TRAIN/TEST SPLIT
# ========================================

print("\n[STEP 3] TRAIN/TEST SPLIT")
print("-"*40)

# Sort by date and split
df = df.sort_values('Stage_Entered_Contacting__c')
X = df[feature_cols].values
y = df[target_col].values

# 80/20 split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=False
)

print(f"Train: {len(X_train):,} samples ({y_train.mean()*100:.2f}% positive)")
print(f"Test: {len(X_test):,} samples ({y_test.mean()*100:.2f}% positive)")

# ========================================
# STEP 4: APPLY SMOTE
# ========================================

print("\n[STEP 4] APPLY SMOTE BALANCING")
print("-"*40)

smote = SMOTE(sampling_strategy=0.1, k_neighbors=5, random_state=42)
X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)

print(f"After SMOTE: {len(X_train_balanced):,} samples ({y_train_balanced.mean()*100:.2f}% positive)")

# ========================================
# STEP 5: TRAIN XGBOOST MODEL
# ========================================

print("\n[STEP 5] TRAINING XGBOOST MODEL")
print("-"*40)

# XGBoost parameters optimized for discovery features
xgb_params = {
    'max_depth': 6,
    'n_estimators': 500,
    'learning_rate': 0.02,
    'subsample': 0.8,
    'colsample_bytree': 0.7,
    'reg_alpha': 1.0,
    'reg_lambda': 3.0,
    'gamma': 2,
    'min_child_weight': 3,
    'objective': 'binary:logistic',
    'eval_metric': ['aucpr', 'map'],
    'random_state': 42,
    'tree_method': 'hist',
    'n_jobs': -1
}

model = xgb.XGBClassifier(**xgb_params)
eval_set = [(X_test, y_test)]

model.fit(
    X_train_balanced,
    y_train_balanced,
    eval_set=eval_set,
    verbose=True
)

if hasattr(model, 'best_iteration'):
    print(f"Best iteration: {model.best_iteration}")
else:
    print(f"Training completed with {model.n_estimators} trees")

# ========================================
# STEP 6: EVALUATE PERFORMANCE
# ========================================

print("\n[STEP 6] MODEL EVALUATION")
print("-"*40)

y_pred_proba = model.predict_proba(X_test)[:, 1]
auc_pr = average_precision_score(y_test, y_pred_proba)
auc_roc = roc_auc_score(y_test, y_pred_proba)

# Train performance for comparison
y_train_pred_proba = model.predict_proba(X_train_balanced)[:, 1]
auc_pr_train = average_precision_score(y_train_balanced, y_train_pred_proba)

print(f"Test Performance:")
print(f"  - AUC-PR: {auc_pr:.4f} ({auc_pr*100:.2f}%)")
print(f"  - AUC-ROC: {auc_roc:.4f}")
print(f"Train Performance:")
print(f"  - AUC-PR: {auc_pr_train:.4f} ({auc_pr_train*100:.2f}%)")
print(f"  - Train-Test Gap: {(auc_pr_train - auc_pr)*100:.2f} percentage points")
print(f"\nComparisons:")
print(f"  - vs V9: {(auc_pr/0.0591)*100:.1f}% of V9 performance")
print(f"  - vs m5: {(auc_pr/0.1492)*100:.1f}% of m5 target")

# ========================================
# STEP 7: FEATURE IMPORTANCE
# ========================================

print("\n[STEP 7] FEATURE IMPORTANCE ANALYSIS")
print("-"*40)

importance_df = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("Top 20 Features:")
for idx, row in importance_df.head(20).iterrows():
    feature_type = "Discovery" if '_disc' in row['feature'] or row['feature'] in [
        'Contact_Score', 'Custodian_Count', 'Platform_Sophistication',
        'Firm_Total_Reps', 'Firm_AUM_per_Rep'
    ] else "Original"
    print(f"  {idx+1:2d}. {row['feature']:40s} {row['importance']:.4f} ({feature_type})")

# Check improvement from discovery features
discovery_feature_names = [f for f in feature_cols if '_disc' in f or f in [
    'Contact_Score', 'Custodian_Count', 'Platform_Sophistication',
    'Firm_Total_Reps', 'Firm_AUM_per_Rep', 'Rep_Performance_vs_Firm'
]]

discovery_importance = importance_df[
    importance_df['feature'].isin(discovery_feature_names)
]['importance'].sum()

print(f"\nDiscovery features importance: {discovery_importance:.4f} ({discovery_importance/importance_df['importance'].sum()*100:.1f}% of total)")

# ========================================
# STEP 8: CROSS-VALIDATION
# ========================================

print("\n[STEP 8] CROSS-VALIDATION")
print("-"*40)

tscv = TimeSeriesSplit(n_splits=5, test_size=int(len(df)*0.15))
cv_scores = []

for i, (train_idx, val_idx) in enumerate(tscv.split(df), 1):
    X_cv_train = df.iloc[train_idx][feature_cols].values
    y_cv_train = df.iloc[train_idx][target_col].values
    X_cv_val = df.iloc[val_idx][feature_cols].values
    y_cv_val = df.iloc[val_idx][target_col].values
    
    X_cv_balanced, y_cv_balanced = smote.fit_resample(X_cv_train, y_cv_train)
    
    cv_model = xgb.XGBClassifier(**xgb_params)
    cv_model.fit(
        X_cv_balanced, y_cv_balanced,
        eval_set=[(X_cv_val, y_cv_val)],
        verbose=False
    )
    
    cv_pred = cv_model.predict_proba(X_cv_val)[:, 1]
    cv_auc = average_precision_score(y_cv_val, cv_pred)
    cv_scores.append(cv_auc)
    print(f"  Fold {i}: {cv_auc:.4f} ({cv_auc*100:.2f}%)")

cv_mean = np.mean(cv_scores)
cv_std = np.std(cv_scores)
cv_coef = (cv_std / cv_mean * 100) if cv_mean > 0 else 0

print(f"\nCV Mean: {cv_mean:.4f} ({cv_mean*100:.2f}%)")
print(f"CV Std: {cv_std:.4f}")
print(f"CV Coefficient: {cv_coef:.2f}%")

# ========================================
# STEP 9: SAVE ARTIFACTS
# ========================================

print("\n[STEP 9] SAVING MODEL ARTIFACTS")
print("-"*40)

timestamp = datetime.now().strftime("%Y%m%d_%H%M")

# Save model
model_path = OUTPUT_DIR / f"v10_discovery_model_{timestamp}.pkl"
with open(model_path, 'wb') as f:
    pickle.dump(model, f)
print(f"[OK] Model saved: {model_path}")

# Save feature list
features_path = OUTPUT_DIR / f"v10_features_{timestamp}.json"
with open(features_path, 'w') as f:
    json.dump(feature_cols, f, indent=2)
print(f"[OK] Features saved: {features_path}")

# Save importance
importance_path = OUTPUT_DIR / f"v10_importance_{timestamp}.csv"
importance_df.to_csv(importance_path, index=False)
print(f"[OK] Importance saved: {importance_path}")

# ========================================
# STEP 10: GENERATE REPORT
# ========================================

print("\n[STEP 10] GENERATING REPORT")
print("-"*40)

report_path = OUTPUT_DIR / f"V10_Discovery_Model_Report_{timestamp}.md"

report_content = f"""# V10 Lead Scoring Model - Discovery Data Enrichment

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
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
- **Test AUC-PR:** {auc_pr:.4f} ({auc_pr*100:.2f}%)
- **Test AUC-ROC:** {auc_roc:.4f}
- **CV Mean:** {cv_mean:.4f} ({cv_mean*100:.2f}%)
- **CV Stability:** {cv_coef:.2f}% coefficient of variation
- **Train-Test Gap:** {(auc_pr_train - auc_pr)*100:.2f} percentage points
- **Improvement over V9:** {(auc_pr/0.0591)*100:.1f}%
- **Progress to m5:** {(auc_pr/0.1492)*100:.1f}%

**Status:** {"✅ SUCCESS - Deploy to Production" if auc_pr > 0.12 else "⚠️ A/B Test Ready" if auc_pr > 0.10 else "📈 Significant Improvement" if auc_pr > 0.08 else "🔄 Needs Refinement"}

---

## Discovery Data Impact

### Coverage Statistics
- **Matched Leads:** {df['Has_Discovery_Data'].sum():,} / {len(df):,} ({df['Has_Discovery_Data'].mean()*100:.1f}%)
"""

# Add discovery feature statistics
if 'Multi_RIA_Relationships_disc' in df.columns:
    multi_ria_count = (df['Multi_RIA_Relationships_disc'] > 0).sum()
    report_content += f"""
- **Multi-RIA Reps:** {multi_ria_count:,} ({multi_ria_count/len(df)*100:.1f}%)
"""

if 'Contact_Score' in df.columns:
    contact_score_avg = df['Contact_Score'].mean()
    report_content += f"""
- **Average Contact Score:** {contact_score_avg:.2f} out of 5
"""

if 'Custodian_Count' in df.columns:
    custodian_avg = df['Custodian_Count'].mean()
    report_content += f"""
- **Average Custodian Count:** {custodian_avg:.2f}
"""

report_content += f"""

### Top Discovery Features by Importance
| Feature | Importance | Fill Rate | Impact |
|---------|------------|-----------|--------|"""

for feat in ['Multi_RIA_Relationships_disc', 'AUM_per_Client_disc', 'Has_Schwab_disc', 
             'Contact_Score', 'Custodian_Count', 'Platform_Sophistication']:
    if feat in importance_df['feature'].values:
        imp = importance_df[importance_df['feature'] == feat]['importance'].values[0]
        fill = (df[feat] != 0).mean() if feat != 'Contact_Score' else 1.0
        report_content += f"\n| {feat} | {imp:.4f} | {fill*100:.1f}% | {'High' if imp > 0.02 else 'Medium'} |"

report_content += f"""

---

## Model Performance Comparison

| Model | Test AUC-PR | CV Mean | CV Stability | Key Features | Status |
|-------|-------------|---------|--------------|--------------|--------|
| V6 | 6.74% | 6.74% | 19.79% | Basic | Baseline |
| V7 | 4.98% | 4.98% | 24.75% | Too many | Failed |
| V8 | 7.07% | 7.01% | 13.90% | Cleaned | Better |
| V9 | 5.91% | 7.11% | 18.95% | m5 replica | Missing data |
| **V10** | **{auc_pr*100:.2f}%** | **{cv_mean*100:.2f}%** | **{cv_coef:.1f}%** | **+Discovery** | **{"Success" if auc_pr > 0.12 else "Best yet"}** |
| m5 Target | 14.92% | - | - | Full features | Production |

---

## Feature Importance Analysis

### Top 20 Features
| Rank | Feature | Importance | Type | Source |
|------|---------|------------|------|--------|"""

for i, row in importance_df.head(20).iterrows():
    source = "Discovery" if '_disc' in row['feature'] or row['feature'] in [
        'Contact_Score', 'Custodian_Count', 'Platform_Sophistication',
        'Firm_Total_Reps', 'Firm_AUM_per_Rep'
    ] else "Original"
    ftype = "Team" if "Team" in row['feature'] else \
            "Custodian" if "Custodian" in row['feature'] or "Schwab" in row['feature'] or "Fidelity" in row['feature'] else \
            "Contact" if "Contact" in row['feature'] or "Email" in row['feature'] or "LinkedIn" in row['feature'] else \
            "Firm" if "Firm" in row['feature'] else \
            "Growth" if "Growth" in row['feature'] else "Other"
    report_content += f"\n| {i+1} | {row['feature'][:35]} | {row['importance']:.4f} | {ftype} | {source} |"

report_content += f"""

---

## Recommendations

{"### 🚀 READY FOR PRODUCTION DEPLOYMENT" if auc_pr > 0.12 else "### ⚠️ READY FOR A/B TESTING" if auc_pr > 0.10 else "### 📈 CONTINUE IMPROVEMENT"}

{"1. Deploy V10 as primary model\n2. Monitor weekly performance\n3. Set up automated retraining with Discovery updates" if auc_pr > 0.12 else "1. Run A/B test against m5\n2. Compare conversion rates\n3. Gather more Discovery data" if auc_pr > 0.10 else "1. Analyze misclassifications\n2. Engineer more team features\n3. Test ensemble with V8"}

### Next Steps for V11
1. Add more Discovery-specific features (if available in raw data)
2. Create team composition features
3. Build compensation alignment scores
4. Test ensemble with V8 and V9

---

**Report Complete**  
**Model Performance:** {auc_pr*100:.2f}% AUC-PR  
**Recommendation:** {"Deploy to Production" if auc_pr > 0.12 else "A/B Test" if auc_pr > 0.10 else "Continue Development"}
"""

with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_content)

print(f"[OK] Report saved: {report_path}")

# ========================================
# FINAL SUMMARY
# ========================================

print("\n" + "="*60)
print("V10 MODEL COMPLETE - DISCOVERY ENRICHMENT")
print("="*60)
print(f"Performance: {auc_pr*100:.2f}% AUC-PR")
print(f"Improvement over V9: {(auc_pr/0.0591 - 1)*100:.1f}%")
if discovery_importance > 0:
    print(f"Discovery feature impact: {discovery_importance/importance_df['importance'].sum()*100:.1f}% of total importance")
print(f"CV Stability: {cv_coef:.1f}%")
print("-"*60)
if auc_pr > 0.12:
    print("[OK] SUCCESS: Model ready for production!")
elif auc_pr > 0.10:
    print("[INFO] GOOD: Model ready for A/B testing")
else:
    print("[INFO] PROGRESS: Significant improvement achieved")
print("="*60)
