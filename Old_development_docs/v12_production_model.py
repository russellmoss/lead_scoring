"""
V12 Production Model - Built on Temporally Correct V6 Data

Filters V6 dataset to 2024-2025 only to match production's 11% MQL rate

No temporal leakage - uses historical snapshots properly

Target: Stage_Entered_Call_Scheduled__c (Call Scheduled = MQL)

"""

import pandas as pd
import numpy as np
from google.cloud import bigquery
from datetime import datetime, timedelta
import warnings
import pickle
import json
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit, train_test_split
from sklearn.metrics import average_precision_score, roc_auc_score
import xgboost as xgb
try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except:
    CATBOOST_AVAILABLE = False
    print("CatBoost not available")

warnings.filterwarnings('ignore')

# ========================================
# CONFIGURATION
# ========================================

PROJECT = 'savvy-gtm-analytics'
DATASET = 'LeadScoring'
OUTPUT_DIR = Path("C:/Users/russe/Documents/Lead Scoring")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# THE CORRECT APPROACH: Use V6 dataset which already has temporal correctness
V6_DATASET = f"{PROJECT}.{DATASET}.step_3_3_training_dataset_v6_20251104_2217"

print("="*60)
print("V12 MODEL - TEMPORALLY CORRECT WITH 2024-2025 DATA")
print("="*60)
print(f"Base Dataset: V6 (temporally correct)")
print(f"Filter Period: 2024-01-01 to 2025-11-04")
print(f"Expected MQL Rate: ~11%")
print("="*60)

client = bigquery.Client(project=PROJECT)

# ========================================
# STEP 1: LOAD V6 DATA AND FILTER TO 2024-2025
# ========================================

print("\n[STEP 1] LOADING TEMPORALLY CORRECT V6 DATA")
print("-"*40)

query = f"""
WITH v6_with_correct_target AS (
    -- V6 already has point-in-time historical snapshots joined correctly
    SELECT 
        *,
        
        -- Correct MQL definition: Call Scheduled
        CASE 
            WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
            THEN 1 ELSE 0 
        END as is_mql_correct,
        
        -- FilterDate logic (matching production)
        -- Use Stage_Entered_Contacting__c as primary date
        COALESCE(
            Stage_Entered_Contacting__c,
            TIMESTAMP('1900-01-01')
        ) AS FilterDate_v12
        
    FROM 
        `{V6_DATASET}`
    WHERE 
        -- Must be contacted (V6 should already have this)
        Stage_Entered_Contacting__c IS NOT NULL
        AND FA_CRD__c IS NOT NULL
),
filtered_2024_2025 AS (
    -- CRITICAL: Filter to 2024-2025 to get the 11% MQL rate
    SELECT 
        *
    FROM 
        v6_with_correct_target
    WHERE 
        DATE(FilterDate_v12) >= '2024-01-01'
        AND DATE(FilterDate_v12) <= '2025-11-04'
),
final_dataset AS (
    SELECT 
        *,
        
        -- Additional engineered features that V6 might not have
        -- (V6 already has most of these from historical snapshots)
        
        -- Multi-RIA flag (if not already in V6)
        CASE 
            WHEN NumberRIAFirmAssociations > 1 THEN 1 
            WHEN multi_ria_relationships = 1 THEN 1
            ELSE 0 
        END as Multi_RIA_Relationships_v12,
        
        -- AUM per client (if not already calculated)
        CASE 
            WHEN COALESCE(NumberClients_Individuals, 0) > 0 
                AND TotalAssetsInMillions IS NOT NULL
            THEN TotalAssetsInMillions / NumberClients_Individuals 
            WHEN AUM_per_Client IS NOT NULL
            THEN AUM_per_Client
            ELSE 0 
        END as AUM_per_Client_v12,
        
        -- HNW concentration
        CASE 
            WHEN COALESCE(NumberClients_Individuals, 0) > 0 
                AND NumberClients_HNWIndividuals IS NOT NULL
            THEN NumberClients_HNWIndividuals / NumberClients_Individuals 
            WHEN HNW_Client_Ratio IS NOT NULL
            THEN HNW_Client_Ratio
            ELSE 0 
        END as HNW_Concentration_v12,
        
        -- Temporal features
        EXTRACT(DAYOFWEEK FROM FilterDate_v12) as contact_dow,
        EXTRACT(MONTH FROM FilterDate_v12) as contact_month,
        EXTRACT(QUARTER FROM FilterDate_v12) as contact_quarter,
        
        -- Growth indicators (if AUM growth is available)
        CASE WHEN AUMGrowthRate_1Year > 0.15 THEN 1 ELSE 0 END as Positive_Growth_v12,
        CASE WHEN AUMGrowthRate_1Year > 0.30 THEN 1 ELSE 0 END as High_Growth_v12
        
    FROM 
        filtered_2024_2025
)
SELECT 
    *,
    is_mql_correct as target_label_v12
FROM 
    final_dataset
ORDER BY 
    FilterDate_v12  -- Maintain temporal order
"""

print("Executing query on V6 dataset with 2024-2025 filter...")
df = client.query(query).to_dataframe()

print(f"\n[OK] Loaded {len(df):,} leads from 2024-2025")
print(f"  - Base dataset: V6 (temporally correct)")
print(f"  - Date range: {df['FilterDate_v12'].min().date()} to {df['FilterDate_v12'].max().date()}")

# Check MQL rate
target_col = 'target_label_v12' if 'target_label_v12' in df.columns else 'target_label'
mql_rate = df[target_col].mean()

print(f"  - MQL rate: {mql_rate*100:.2f}%")
print(f"  - MQLs: {df[target_col].sum():,}")

if mql_rate < 0.08:
    print("\n[WARNING] MQL rate lower than expected 8-14%")
    print("   This might be because V6 uses old target definition")
    print("   Checking alternative target columns...")
    
    # Check if Stage_Entered_Call_Scheduled__c exists
    if 'Stage_Entered_Call_Scheduled__c' in df.columns:
        alt_rate = df['Stage_Entered_Call_Scheduled__c'].notna().mean()
        print(f"   Stage_Entered_Call_Scheduled__c rate: {alt_rate*100:.2f}%")
elif mql_rate > 0.14:
    print("\n[WARNING] MQL rate higher than expected 8-14%")
else:
    print(f"\n[OK] MQL rate {mql_rate*100:.2f}% is within expected range!")

# ========================================
# STEP 2: VERIFY TEMPORAL CORRECTNESS
# ========================================

print("\n[STEP 2] VERIFYING TEMPORAL CORRECTNESS")
print("-"*40)

# Check that we have historical snapshot data (not current)
snapshot_cols = [col for col in df.columns if 'snapshot' in col.lower() or 'vintage' in col.lower()]
if snapshot_cols:
    print(f"[OK] Found {len(snapshot_cols)} snapshot-related columns")
    print(f"  Sample: {snapshot_cols[:3]}")

# Check for V6 temporal features
temporal_features = ['DateBecameRep_NumberOfYears', 'DateOfHireAtCurrentFirm_NumberOfYears']
for feat in temporal_features:
    if feat in df.columns:
        print(f"[OK] {feat}: min={df[feat].min():.1f}, max={df[feat].max():.1f}")

# ========================================
# STEP 3: FEATURE SELECTION
# ========================================

print("\n[STEP 3] FEATURE SELECTION")
print("-"*40)

# Identify columns to exclude
id_cols = ['Id', 'FA_CRD__c', 'Full_prospect_id__c', 'FilterDate', 'FilterDate_v12',
           'CreatedDate', 'Stage_Entered_Contacting__c', 'Stage_Entered_Call_Scheduled__c',
           'ConvertedDate', 'IsConverted', 'Stage_Entered_New__c', 'Stage_Entered_Closed__c']

target_cols = ['target_label', 'target_label_v12', 'is_mql_correct', 'is_sql', 
               'is_contacted', 'is_mql', 'rep_snapshot_at', 'firm_snapshot_at', 'days_to_conversion']

timestamp_cols = [col for col in df.columns if 'stage_entered' in col.lower() or 
                  'date' in col.lower() or 'timestamp' in col.lower() or 'snapshot' in col.lower()]

# Get feature columns
all_cols = df.columns.tolist()
exclude_all = list(set(id_cols + target_cols + timestamp_cols))
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
            df[col] = df[col].fillna(0).astype(float)
        elif df[col].dtype == 'object' and df[col].nunique() < 20:
            categorical_features.append(col)

print(f"  - Numeric features: {len(numeric_features)}")
print(f"  - Categorical features: {len(categorical_features)}")

# One-hot encode categoricals
for col in categorical_features:
    if col in ['Home_State', 'Branch_State']:
        # Only top 5 states
        top_values = df[col].value_counts().head(5).index
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

# Check for key features
key_features = ['Multi_RIA_Relationships', 'TotalAssetsInMillions', 'NumberClients_Individuals',
                'Has_Series_7', 'Has_Series_65', 'NumberRIAFirmAssociations']

print("\nKey features check:")
for feat in key_features:
    found = False
    for col in final_features:
        if feat.lower() in col.lower():
            print(f"  [OK] {feat} -> {col}")
            found = True
            break
    if not found:
        print(f"  [MISSING] {feat} not found")

# Ensure all features are numeric and finite
X_data = df[final_features].values
X_data = np.nan_to_num(X_data, nan=0.0, posinf=0.0, neginf=0.0)

# ========================================
# STEP 4: TEMPORAL TRAIN/TEST SPLIT
# ========================================

print("\n[STEP 4] TEMPORAL TRAIN/TEST SPLIT")
print("-"*40)

# Sort by date
df = df.sort_values('FilterDate_v12')

# 80/20 temporal split
split_date = df['FilterDate_v12'].quantile(0.8)
train_mask = df['FilterDate_v12'] < split_date
test_mask = ~train_mask

X_train = X_data[train_mask]
y_train = df.loc[train_mask, target_col].values
X_test = X_data[test_mask]
y_test = df.loc[test_mask, target_col].values

print(f"Split date: {split_date}")
print(f"Train: {len(X_train):,} samples")
print(f"  - Date range: {df[train_mask]['FilterDate_v12'].min().date()} to {df[train_mask]['FilterDate_v12'].max().date()}")
print(f"  - MQL rate: {y_train.mean()*100:.2f}%")
print(f"Test: {len(X_test):,} samples")
print(f"  - Date range: {df[test_mask]['FilterDate_v12'].min().date()} to {df[test_mask]['FilterDate_v12'].max().date()}")
print(f"  - MQL rate: {y_test.mean()*100:.2f}%")

# ========================================
# STEP 5: MODEL TRAINING
# ========================================

print("\n[STEP 5] MODEL TRAINING")
print("-"*40)

# Adjust class weight based on actual imbalance
scale_pos_weight = (1 - y_train.mean()) / y_train.mean()
print(f"Scale pos weight: {scale_pos_weight:.2f}")

# XGBoost parameters
xgb_params = {
    'max_depth': 5 if y_train.mean() < 0.05 else 6,
    'n_estimators': 500,
    'learning_rate': 0.02 if y_train.mean() < 0.05 else 0.03,
    'subsample': 0.7,
    'colsample_bytree': 0.7,
    'reg_alpha': 1.0 if y_train.mean() < 0.05 else 0.5,
    'reg_lambda': 2.0 if y_train.mean() < 0.05 else 1.0,
    'gamma': 1.0,
    'min_child_weight': 5 if y_train.mean() < 0.05 else 3,
    'scale_pos_weight': scale_pos_weight,
    'objective': 'binary:logistic',
    'eval_metric': 'aucpr',
    'random_state': 42,
    'tree_method': 'hist'
}

print("Training XGBoost model...")
xgb_model = xgb.XGBClassifier(**xgb_params)
eval_set = [(X_test, y_test)]

xgb_model.fit(
    X_train, y_train,
    eval_set=eval_set,
    verbose=True
)

if hasattr(xgb_model, 'best_iteration') and xgb_model.best_iteration is not None:
    print(f"Best iteration: {xgb_model.best_iteration}")
else:
    print(f"Training completed with {xgb_params['n_estimators']} trees")

# Optional: Train CatBoost
if CATBOOST_AVAILABLE:
    print("\nTraining CatBoost for comparison...")
    cat_model = CatBoostClassifier(
        iterations=500,
        depth=5 if y_train.mean() < 0.05 else 6,
        learning_rate=0.02 if y_train.mean() < 0.05 else 0.03,
        auto_class_weights='Balanced',
        early_stopping_rounds=50,
        verbose=False,
        random_state=42
    )
    cat_model.fit(X_train, y_train, eval_set=(X_test, y_test))

# ========================================
# STEP 6: EVALUATION
# ========================================

print("\n[STEP 6] MODEL EVALUATION")
print("-"*40)

# XGBoost evaluation
y_pred_xgb = xgb_model.predict_proba(X_test)[:, 1]
auc_pr_xgb = average_precision_score(y_test, y_pred_xgb)
auc_roc_xgb = roc_auc_score(y_test, y_pred_xgb)

print("XGBoost Performance:")
print(f"  AUC-PR:  {auc_pr_xgb:.4f} ({auc_pr_xgb*100:.2f}%)")
print(f"  AUC-ROC: {auc_roc_xgb:.4f}")
print(f"  Baseline: {y_test.mean():.4f} ({y_test.mean()*100:.2f}%)")
print(f"  Lift: {auc_pr_xgb/y_test.mean():.2f}x")

# CatBoost evaluation (if available)
if CATBOOST_AVAILABLE:
    y_pred_cat = cat_model.predict_proba(X_test)[:, 1]
    auc_pr_cat = average_precision_score(y_test, y_pred_cat)
    auc_roc_cat = roc_auc_score(y_test, y_pred_cat)
    
    print("\nCatBoost Performance:")
    print(f"  AUC-PR:  {auc_pr_cat:.4f} ({auc_pr_cat*100:.2f}%)")
    print(f"  AUC-ROC: {auc_roc_cat:.4f}")
    
    # Select best model
    if auc_pr_cat > auc_pr_xgb:
        best_model = cat_model
        best_name = "CatBoost"
        best_auc_pr = auc_pr_cat
        y_pred = y_pred_cat
    else:
        best_model = xgb_model
        best_name = "XGBoost"
        best_auc_pr = auc_pr_xgb
        y_pred = y_pred_xgb
else:
    best_model = xgb_model
    best_name = "XGBoost"
    best_auc_pr = auc_pr_xgb
    y_pred = y_pred_xgb

print(f"\n[OK] Best Model: {best_name} with {best_auc_pr:.4f} AUC-PR")

# ========================================
# STEP 7: BUSINESS METRICS
# ========================================

print("\n[STEP 7] BUSINESS METRICS")
print("-"*40)

percentiles = [99, 95, 90, 80, 70, 50]
print("Percentile | Threshold | Leads | MQLs | Conv Rate | Lift")
print("-"*60)

baseline = y_test.mean()
for p in percentiles:
    thresh = np.percentile(y_pred, p)
    mask = y_pred >= thresh
    n_leads = mask.sum()
    n_mqls = y_test[mask].sum()
    conv_rate = n_mqls/n_leads if n_leads > 0 else 0
    lift = conv_rate/baseline if baseline > 0 else 0
    print(f"Top {100-p:2d}% | {thresh:.4f} | {n_leads:5d} | {n_mqls:4d} | {conv_rate*100:6.1f}% | {lift:.1f}x")

# ========================================
# STEP 8: FEATURE IMPORTANCE
# ========================================

print("\n[STEP 8] TOP FEATURES")
print("-"*40)

if hasattr(best_model, 'feature_importances_'):
    importance_df = pd.DataFrame({
        'feature': final_features,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("Top 15 Features:")
    for i, row in importance_df.head(15).iterrows():
        print(f"  {i+1:2d}. {row['feature']:40s} {row['importance']:.4f}")

# ========================================
# STEP 9: CROSS-VALIDATION
# ========================================

print("\n[STEP 9] TIME SERIES CROSS-VALIDATION")
print("-"*40)

tscv = TimeSeriesSplit(n_splits=5)
cv_scores = []

for fold, (train_idx, val_idx) in enumerate(tscv.split(df), 1):
    if len(val_idx) < 100:  # Skip if validation set too small
        continue
        
    X_cv_train = X_data[train_idx]
    y_cv_train = df.iloc[train_idx][target_col].values
    X_cv_val = X_data[val_idx]
    y_cv_val = df.iloc[val_idx][target_col].values
    
    cv_model = xgb.XGBClassifier(**xgb_params)
    cv_model.fit(X_cv_train, y_cv_train, eval_set=[(X_cv_val, y_cv_val)],
                verbose=False)
    
    cv_pred = cv_model.predict_proba(X_cv_val)[:, 1]
    cv_auc = average_precision_score(y_cv_val, cv_pred)
    cv_scores.append(cv_auc)
    print(f"  Fold {fold}: {cv_auc:.4f} ({cv_auc*100:.2f}%)")

if cv_scores:
    print(f"\nCV Mean: {np.mean(cv_scores):.4f} ({np.mean(cv_scores)*100:.2f}%)")
    print(f"CV Std:  {np.std(cv_scores):.4f}")

# ========================================
# STEP 10: SAVE MODEL
# ========================================

print("\n[STEP 10] SAVING MODEL")
print("-"*40)

timestamp = datetime.now().strftime("%Y%m%d_%H%M")

# Save model
model_path = OUTPUT_DIR / f"v12_{best_name.lower()}_{timestamp}.pkl"
with open(model_path, 'wb') as f:
    pickle.dump(best_model, f)
print(f"[OK] Model saved: {model_path}")

# Save metadata
metadata = {
    'model_type': best_name,
    'base_dataset': 'V6 (temporally correct)',
    'filter_period': '2024-01-01 to 2025-11-04',
    'features': final_features,
    'mql_rate': float(y_train.mean()),
    'test_mql_rate': float(y_test.mean()),
    'auc_pr': float(best_auc_pr),
    'auc_roc': float(auc_roc_xgb),
    'cv_mean': float(np.mean(cv_scores)) if cv_scores else None,
    'cv_std': float(np.std(cv_scores)) if cv_scores else None,
    'timestamp': timestamp
}

metadata_path = OUTPUT_DIR / f"v12_metadata_{timestamp}.json"
with open(metadata_path, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"[OK] Metadata saved: {metadata_path}")

# Save feature importance
if hasattr(best_model, 'feature_importances_'):
    importance_path = OUTPUT_DIR / f"v12_importance_{timestamp}.csv"
    importance_df.to_csv(importance_path, index=False)
    print(f"[OK] Importance saved: {importance_path}")

# ========================================
# FINAL SUMMARY
# ========================================

print("\n" + "="*60)
print("V12 MODEL COMPLETE - TEMPORALLY CORRECT")
print("="*60)
print(f"Base: V6 dataset (point-in-time snapshots)")
print(f"Period: 2024-2025 only")
print(f"MQL Rate: {y_test.mean()*100:.2f}%")
print(f"Model: {best_name}")
print(f"AUC-PR: {best_auc_pr*100:.2f}%")
print("-"*60)

if y_test.mean() > 0.08:  # If we got the 11% rate
    if best_auc_pr > 0.15:
        print("[OK] EXCELLENT: Ready for production!")
    elif best_auc_pr > 0.10:
        print("[OK] GOOD: Solid performance")
    else:
        print("[WARNING] INVESTIGATE: Lower than expected for 11% base rate")
else:  # If we still have ~3% rate
    if best_auc_pr > 0.07:
        print("[OK] GOOD: Strong performance for low base rate")
    elif best_auc_pr > 0.05:
        print("[OK] ACCEPTABLE: Matches V11 performance")
    else:
        print("[WARNING] INVESTIGATE: Check feature quality")

print("="*60)

