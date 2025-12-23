# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\train_with_velocity.py
# FIXED: Sanitize column names for XGBoost compatibility

import sys
from pathlib import Path
VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

import pandas as pd
import numpy as np
import json
import pickle
import hashlib
import re
from datetime import datetime
from google.cloud import bigquery
import xgboost as xgb
import optuna
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, average_precision_score
import warnings
warnings.filterwarnings('ignore')

from utils.execution_logger import ExecutionLogger
from utils.paths import PATHS

# Initialize
logger = ExecutionLogger()
logger.start_phase("4-VELOCITY", "Model Training with Safe Velocity Features")
client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("PHASE 4: TRAIN WITH SAFE VELOCITY FEATURES")
print("=" * 70)
print("\nUsing BOTH 2024 and 2025 data with velocity features")

# =============================================================================
# HELPER: Sanitize column names for XGBoost
# =============================================================================
def sanitize_column_names(df):
    """Replace special characters that XGBoost doesn't allow: [, ], <, >, (, )"""
    new_columns = {}
    for col in df.columns:
        new_col = col
        new_col = new_col.replace('<', 'lt')
        new_col = new_col.replace('>', 'gt')
        new_col = new_col.replace('[', '_')
        new_col = new_col.replace(']', '_')
        new_col = new_col.replace('(', '_')
        new_col = new_col.replace(')', '_')
        new_col = re.sub(r'\s+', '_', new_col)  # Replace whitespace with underscore
        new_columns[col] = new_col
    return df.rename(columns=new_columns)

# =============================================================================
# STEP 1: LOAD DATA WITH VELOCITY FEATURES
# =============================================================================
logger.log_action("Loading data with velocity features")

query = """
SELECT 
    -- Base features from splits table
    s.lead_id,
    s.contacted_date,
    s.target,
    s.split,
    s.advisor_crd,
    
    -- Existing base features
    s.industry_tenure_months,
    s.num_prior_firms,
    s.current_firm_tenure_months,
    s.pit_moves_3yr,
    s.pit_avg_prior_tenure_months,
    s.pit_restlessness_ratio,
    s.firm_aum_pit,
    s.log_firm_aum,
    s.firm_net_change_12mo,
    s.firm_departures_12mo,
    s.firm_arrivals_12mo,
    s.firm_stability_percentile,
    
    -- Mobility tiers
    s.pit_mobility_tier_Stable,
    s.pit_mobility_tier_Mobile,
    s.pit_mobility_tier_Highly_Mobile,
    
    -- Sparsity-handled features
    s.has_prior_moves,
    s.is_bleeding_firm,
    s.is_flight_risk,
    s.flight_risk_tier,
    
    -- NEW: Velocity features (safe, START_DATE only)
    v.days_at_current_firm,
    v.days_since_last_move_safe,
    v.prev_job_tenure_days,
    v.tenure_ratio,
    v.in_danger_zone,
    v.tenure_bucket,
    v.moves_3yr_from_starts,
    v.total_jobs_pit as total_jobs_from_history
    
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2` s
LEFT JOIN `savvy-gtm-analytics.ml_features.lead_velocity_features` v
    ON s.lead_id = v.lead_id
WHERE s.split IN ('TRAIN', 'TEST')
ORDER BY s.contacted_date
"""

print("\nLoading data with velocity features...")
df = client.query(query).result().to_dataframe()
print(f"✅ Loaded {len(df):,} leads")

# Check velocity feature coverage
velocity_coverage = df['days_at_current_firm'].notna().mean() * 100
print(f"\nVelocity feature coverage: {velocity_coverage:.1f}%")

# =============================================================================
# STEP 2: SPLIT DATA
# =============================================================================
df['contacted_date'] = pd.to_datetime(df['contacted_date'])

train_df = df[df['split'] == 'TRAIN'].copy().reset_index(drop=True)
test_df = df[df['split'] == 'TEST'].copy().reset_index(drop=True)

print(f"\nTrain: {len(train_df):,} leads ({train_df['target'].mean()*100:.2f}% positive)")
print(f"  Date range: {train_df['contacted_date'].min()} to {train_df['contacted_date'].max()}")

print(f"\nTest: {len(test_df):,} leads ({test_df['target'].mean()*100:.2f}% positive)")
print(f"  Date range: {test_df['contacted_date'].min()} to {test_df['contacted_date'].max()}")

# =============================================================================
# STEP 3: DEFINE FEATURES
# =============================================================================
logger.log_action("Defining feature set with velocity features")

# Base features (existing)
BASE_FEATURES = [
    'industry_tenure_months',
    'num_prior_firms',
    'current_firm_tenure_months',
    'pit_moves_3yr',
    'pit_avg_prior_tenure_months',
    'pit_restlessness_ratio',
    'firm_aum_pit',
    'log_firm_aum',
    'firm_net_change_12mo',
    'firm_departures_12mo',
    'firm_arrivals_12mo',
    'firm_stability_percentile',
    'pit_mobility_tier_Stable',
    'pit_mobility_tier_Mobile',
    'pit_mobility_tier_Highly_Mobile',
    'has_prior_moves',
    'is_bleeding_firm',
    'is_flight_risk',
    'flight_risk_tier',
]

# NEW: Velocity features (safe, START_DATE only)
VELOCITY_FEATURES = [
    'days_at_current_firm',          # How long at current firm
    'days_since_last_move_safe',     # Same as above (named for clarity)
    'prev_job_tenure_days',          # How long at previous job
    'tenure_ratio',                  # Current tenure / prev tenure
    'in_danger_zone',                # Binary: 1-2 years at current firm
    'moves_3yr_from_starts',         # Moves in 3yr (from START_DATEs)
    'total_jobs_from_history',       # Total jobs ever
]

# Runtime features (calculated here)
RUNTIME_FEATURES = ['flight_risk_score', 'is_fresh_start', 'log_days_at_firm']

# =============================================================================
# STEP 4: ENGINEER RUNTIME FEATURES (with sanitized names)
# =============================================================================
def engineer_features(df):
    df = df.copy()
    
    # Existing runtime features
    df['flight_risk_score'] = df['pit_moves_3yr'] * np.maximum(-df['firm_net_change_12mo'], 0)
    df['is_fresh_start'] = (df['current_firm_tenure_months'] < 12).astype(int)
    
    # New: Log-transform days_at_current_firm (handles wide range)
    df['log_days_at_firm'] = np.log1p(df['days_at_current_firm'].fillna(0))
    
    # One-hot encode tenure_bucket with SANITIZED names
    if 'tenure_bucket' in df.columns:
        bucket_dummies = pd.get_dummies(df['tenure_bucket'], prefix='tenure_bucket')
        # Sanitize the column names!
        bucket_dummies = sanitize_column_names(bucket_dummies)
        for col in bucket_dummies.columns:
            df[col] = bucket_dummies[col]
    
    return df

train_df = engineer_features(train_df)
test_df = engineer_features(test_df)

# Get tenure bucket columns (after sanitization)
TENURE_BUCKET_COLS = [c for c in train_df.columns if c.startswith('tenure_bucket_')]
print(f"\nTenure bucket columns (sanitized): {TENURE_BUCKET_COLS}")

ALL_FEATURES = BASE_FEATURES + VELOCITY_FEATURES + RUNTIME_FEATURES + TENURE_BUCKET_COLS

# Filter to features that exist
available_cols = train_df.columns.tolist()
ALL_FEATURES = [f for f in ALL_FEATURES if f in available_cols]

print(f"\nTotal features: {len(ALL_FEATURES)}")
print(f"  Base: {len([f for f in BASE_FEATURES if f in available_cols])}")
print(f"  Velocity: {len([f for f in VELOCITY_FEATURES if f in available_cols])}")
print(f"  Runtime: {len([f for f in RUNTIME_FEATURES if f in available_cols])}")
print(f"  Tenure Buckets: {len(TENURE_BUCKET_COLS)}")

# =============================================================================
# STEP 5: PREPARE FEATURE MATRICES
# =============================================================================
logger.log_action("Preparing feature matrices")

def prepare_features(df, features):
    X = df[features].copy().fillna(0).astype(np.float32)
    return X

X_train = prepare_features(train_df, ALL_FEATURES)
y_train = train_df['target'].astype(int)
X_test = prepare_features(test_df, ALL_FEATURES)
y_test = test_df['target'].astype(int)

print(f"\nFeature matrices:")
print(f"  X_train: {X_train.shape}")
print(f"  X_test: {X_test.shape}")

# =============================================================================
# STEP 6: VELOCITY FEATURE SIGNAL CHECK
# =============================================================================
print(f"\n{'='*60}")
print("VELOCITY FEATURE SIGNAL CHECK")
print("="*60)

for feat in VELOCITY_FEATURES:
    if feat in train_df.columns:
        valid_mask = train_df[feat].notna() & (train_df[feat] != 0)
        coverage = valid_mask.mean() * 100
        if valid_mask.sum() > 100:
            auc = roc_auc_score(train_df.loc[valid_mask, 'target'], train_df.loc[valid_mask, feat])
        else:
            auc = 0.5
        print(f"  {feat}: AUC={auc:.4f} (coverage={coverage:.1f}%)")

# Check in_danger_zone conversion rates
if 'in_danger_zone' in train_df.columns:
    dz = train_df.groupby('in_danger_zone')['target'].agg(['count', 'mean'])
    print(f"\nin_danger_zone conversion rates:")
    print(dz.to_string())

# =============================================================================
# STEP 7: CLASS IMBALANCE
# =============================================================================
n_pos = y_train.sum()
n_neg = len(y_train) - n_pos
scale_pos_weight = n_neg / n_pos

print(f"\nClass Balance: {n_neg:,} neg / {n_pos:,} pos = {scale_pos_weight:.1f}:1")

# =============================================================================
# STEP 8: OPTUNA HYPERPARAMETER TUNING
# =============================================================================
logger.log_action("Running Optuna hyperparameter optimization (50 trials)")

tscv = TimeSeriesSplit(n_splits=5)

def objective(trial):
    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'aucpr',
        'tree_method': 'hist',
        'random_state': 42,
        'scale_pos_weight': scale_pos_weight,
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'n_estimators': trial.suggest_int('n_estimators', 50, 300),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'gamma': trial.suggest_float('gamma', 0, 10),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
    }
    
    cv_scores = []
    for train_idx, val_idx in tscv.split(X_train):
        X_cv_train, X_cv_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
        y_cv_train, y_cv_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
        
        if y_cv_val.sum() == 0:
            continue
        
        model = xgb.XGBClassifier(**params, verbosity=0)
        model.fit(X_cv_train, y_cv_train, eval_set=[(X_cv_val, y_cv_val)], verbose=False)
        
        y_pred = model.predict_proba(X_cv_val)[:, 1]
        cv_scores.append(average_precision_score(y_cv_val, y_pred))
    
    return np.mean(cv_scores) if cv_scores else 0.0

print("\n" + "=" * 60)
print("OPTUNA HYPERPARAMETER TUNING (50 trials)")
print("=" * 60)

study = optuna.create_study(direction='maximize', study_name='xgb_v3_velocity')
study.optimize(objective, n_trials=50, show_progress_bar=True)

print(f"\nBest CV AUC-PR: {study.best_value:.4f}")

# =============================================================================
# STEP 9: TRAIN FINAL MODEL
# =============================================================================
logger.log_action("Training final model")

best_params = {
    'objective': 'binary:logistic',
    'eval_metric': 'aucpr',
    'tree_method': 'hist',
    'random_state': 42,
    'scale_pos_weight': scale_pos_weight,
    **study.best_params
}

print("\nTraining final model...")
final_model = xgb.XGBClassifier(**best_params, verbosity=1)
final_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=True)

# =============================================================================
# STEP 10: EVALUATE
# =============================================================================
y_pred_proba = final_model.predict_proba(X_test)[:, 1]

test_auc_roc = roc_auc_score(y_test, y_pred_proba)
test_auc_pr = average_precision_score(y_test, y_pred_proba)

print(f"\n" + "=" * 60)
print("TEST SET PERFORMANCE")
print("=" * 60)
print(f"AUC-ROC: {test_auc_roc:.4f}")
print(f"AUC-PR: {test_auc_pr:.4f}")

# Top decile lift
def calculate_lift(y_true, y_pred):
    df_eval = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred})
    df_eval['decile'] = pd.qcut(df_eval['y_pred'].rank(method='first'), 10, labels=False)
    
    top_decile = df_eval[df_eval['decile'] == 9]
    top_rate = top_decile['y_true'].mean()
    base_rate = df_eval['y_true'].mean()
    
    return top_rate / base_rate, top_rate, base_rate

lift, top_rate, base_rate = calculate_lift(y_test, y_pred_proba)

print(f"\nTOP DECILE:")
print(f"  Baseline: {base_rate*100:.2f}%")
print(f"  Top Decile: {top_rate*100:.2f}%")
print(f"  LIFT: {lift:.2f}x {'✅ TARGET MET!' if lift >= 2.0 else '⚠️'}")

# =============================================================================
# STEP 11: FEATURE IMPORTANCE
# =============================================================================
print(f"\n" + "=" * 60)
print("FEATURE IMPORTANCE")
print("=" * 60)

importance_df = pd.DataFrame({
    'feature': ALL_FEATURES,
    'importance': final_model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nTOP 15 FEATURES:")
for i, (_, row) in enumerate(importance_df.head(15).iterrows()):
    marker = ""
    if row['feature'] in VELOCITY_FEATURES or 'tenure_bucket' in row['feature'] or row['feature'] == 'log_days_at_firm':
        marker = "🚀 VELOCITY"
    elif 'mobility_tier' in row['feature']:
        marker = "🎯 MOBILITY"
    print(f"  {i+1}. {row['feature']}: {row['importance']:.4f} {marker}")

# Calculate velocity feature importance
velocity_importance = importance_df[
    importance_df['feature'].isin(VELOCITY_FEATURES) | 
    importance_df['feature'].str.contains('tenure_bucket') |
    (importance_df['feature'] == 'log_days_at_firm')
]['importance'].sum()
print(f"\nTotal Velocity Feature Importance: {velocity_importance*100:.1f}%")

# =============================================================================
# STEP 12: SAVE MODEL
# =============================================================================
date_str = datetime.now().strftime('%Y%m%d')
hash_str = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
model_version = f"v3-velocity-{date_str}-{hash_str}"

model_dir = PATHS['MODELS_DIR'] / model_version
model_dir.mkdir(parents=True, exist_ok=True)

# Save model
with open(model_dir / 'model.pkl', 'wb') as f:
    pickle.dump(final_model, f)

# Save feature names
with open(model_dir / 'feature_names.json', 'w') as f:
    json.dump({
        'all_features': ALL_FEATURES,
        'base_features': [f for f in BASE_FEATURES if f in ALL_FEATURES],
        'velocity_features': [f for f in VELOCITY_FEATURES if f in ALL_FEATURES],
        'runtime_features': [f for f in RUNTIME_FEATURES if f in ALL_FEATURES],
        'tenure_bucket_features': TENURE_BUCKET_COLS,
    }, f, indent=2)

# Save metrics
metrics = {
    'model_version': model_version,
    'training_date': datetime.now().isoformat(),
    'train_samples': len(X_train),
    'test_samples': len(X_test),
    'n_features': len(ALL_FEATURES),
    'test_auc_roc': test_auc_roc,
    'test_auc_pr': test_auc_pr,
    'top_decile_lift': lift,
    'baseline_rate': base_rate,
    'top_decile_rate': top_rate,
    'velocity_importance': velocity_importance,
    'notes': 'Trained with safe velocity features (START_DATE only, no END_DATE leakage)'
}
with open(model_dir / 'training_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print(f"\n✅ Model saved: {model_dir}")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("TRAINING COMPLETE")
print("=" * 70)

print(f"""
Model: {model_version}
Training Data: 2024 + 2025 (TRAIN split)
Test Data: TEST split

Performance:
  AUC-ROC: {test_auc_roc:.4f}
  AUC-PR: {test_auc_pr:.4f}
  Top Decile Lift: {lift:.2f}x

Velocity Features:
  Total importance: {velocity_importance*100:.1f}%
  
Key Safety Notes:
  ✅ Uses START_DATE only (never END_DATE)
  ✅ All features calculated as of contacted_date (PIT)
  ✅ No backfill leakage risk
""")

if lift >= 2.0:
    print("🎉 TARGET ACHIEVED! Ready for Phase 5 (SHAP) and Phase 6 (Calibration)")
else:
    print(f"⚠️ Lift is {lift:.2f}x, target is 2.0x")
    print("   Consider: Train on 2024 only, or add more velocity features")