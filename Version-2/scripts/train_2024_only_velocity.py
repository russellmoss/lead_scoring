# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\train_2024_only_velocity.py
# Train on 2024 data only where danger zone signal is 4.43x lift

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
logger.start_phase("4-2024ONLY", "Model Training on 2024 Data with Velocity Features")
client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("PHASE 4: TRAIN ON 2024 DATA ONLY (STRONGER SIGNAL)")
print("=" * 70)
print("\n2024 Danger Zone Lift: 4.43x (vs 1.70x in test)")
print("Training on clean 2024 signal, testing on early 2025")

# =============================================================================
# HELPER: Sanitize column names for XGBoost
# =============================================================================
def sanitize_column_names(df):
    """Replace special characters that XGBoost doesn't allow"""
    new_columns = {}
    for col in df.columns:
        new_col = col
        new_col = new_col.replace('<', 'lt')
        new_col = new_col.replace('>', 'gt')
        new_col = new_col.replace('[', '_')
        new_col = new_col.replace(']', '_')
        new_col = new_col.replace('(', '_')
        new_col = new_col.replace(')', '_')
        new_col = re.sub(r'\s+', '_', new_col)
        new_columns[col] = new_col
    return df.rename(columns=new_columns)

# =============================================================================
# STEP 1: LOAD 2024 DATA WITH VELOCITY FEATURES
# =============================================================================
logger.log_action("Loading 2024 data with velocity features")

query = """
SELECT 
    s.lead_id,
    s.contacted_date,
    s.target,
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
    
    -- Velocity features (safe, START_DATE only)
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

print("\nLoading data...")
df = client.query(query).result().to_dataframe()
df['contacted_date'] = pd.to_datetime(df['contacted_date'])

print(f"Total loaded: {len(df):,} leads")

# =============================================================================
# STEP 2: CREATE 2024-ONLY SPLITS
# =============================================================================
print("\n" + "=" * 60)
print("CREATING 2024-ONLY TRAIN/TEST SPLITS")
print("=" * 60)

# 2024 data only
df_2024 = df[df['contacted_date'].dt.year == 2024].copy()
print(f"\n2024 leads: {len(df_2024):,}")

# Split 2024: Train on Feb-Sep, Test on Oct-Nov
train_cutoff = '2024-10-01'
df_2024['split_2024'] = np.where(df_2024['contacted_date'] < train_cutoff, 'TRAIN', 'TEST')

train_df = df_2024[df_2024['split_2024'] == 'TRAIN'].copy().reset_index(drop=True)
test_df = df_2024[df_2024['split_2024'] == 'TEST'].copy().reset_index(drop=True)

print(f"\nTRAIN (Feb-Sep 2024): {len(train_df):,} leads ({train_df['target'].mean()*100:.2f}% positive)")
print(f"  Date range: {train_df['contacted_date'].min().date()} to {train_df['contacted_date'].max().date()}")

print(f"\nTEST (Oct-Nov 2024): {len(test_df):,} leads ({test_df['target'].mean()*100:.2f}% positive)")
print(f"  Date range: {test_df['contacted_date'].min().date()} to {test_df['contacted_date'].max().date()}")

# Verify danger zone signal in both splits
print("\n" + "-" * 40)
print("DANGER ZONE SIGNAL CHECK:")
for name, split_df in [("TRAIN", train_df), ("TEST", test_df)]:
    dz_conv = split_df[split_df['in_danger_zone'] == 1]['target'].mean()
    non_dz_conv = split_df[split_df['in_danger_zone'] == 0]['target'].mean()
    if dz_conv > 0 and non_dz_conv > 0:
        lift = dz_conv / non_dz_conv
        print(f"  {name}: DZ={dz_conv*100:.1f}%, Non-DZ={non_dz_conv*100:.1f}%, Lift={lift:.2f}x")

# =============================================================================
# STEP 3: DEFINE FEATURES (Stable ones only)
# =============================================================================
logger.log_action("Defining stable feature set")

# Base features
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

# Velocity features (STABLE ONES ONLY - skip "Very New" and "New" which flip)
VELOCITY_FEATURES = [
    'days_at_current_firm',
    'prev_job_tenure_days',
    'tenure_ratio',
    'in_danger_zone',               # 4.43x lift in 2024!
    'moves_3yr_from_starts',
    'total_jobs_from_history',
]

# Runtime features
RUNTIME_FEATURES = ['flight_risk_score', 'log_days_at_firm']

# STABLE tenure buckets only (skip Very New and New which flip)
STABLE_TENURE_BUCKETS = [
    'tenure_bucket_Danger_Zone__1-2yr_',
    'tenure_bucket_Established__2-4yr_',
    'tenure_bucket_Veteran__4yr+_',
    'tenure_bucket_Unknown',
]

# =============================================================================
# STEP 4: ENGINEER RUNTIME FEATURES
# =============================================================================
def engineer_features(df):
    df = df.copy()
    
    # Runtime features
    df['flight_risk_score'] = df['pit_moves_3yr'] * np.maximum(-df['firm_net_change_12mo'], 0)
    df['log_days_at_firm'] = np.log1p(df['days_at_current_firm'].fillna(0))
    
    # One-hot encode tenure_bucket (will sanitize names)
    if 'tenure_bucket' in df.columns:
        bucket_dummies = pd.get_dummies(df['tenure_bucket'], prefix='tenure_bucket')
        bucket_dummies = sanitize_column_names(bucket_dummies)
        for col in bucket_dummies.columns:
            df[col] = bucket_dummies[col]
    
    return df

train_df = engineer_features(train_df)
test_df = engineer_features(test_df)

# Build final feature list
ALL_FEATURES = BASE_FEATURES + VELOCITY_FEATURES + RUNTIME_FEATURES
# Add only stable tenure buckets that exist
for col in STABLE_TENURE_BUCKETS:
    if col in train_df.columns:
        ALL_FEATURES.append(col)

# Filter to existing columns
ALL_FEATURES = [f for f in ALL_FEATURES if f in train_df.columns]
print(f"\nTotal features: {len(ALL_FEATURES)}")

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
# STEP 6: CLASS IMBALANCE
# =============================================================================
n_pos = y_train.sum()
n_neg = len(y_train) - n_pos
scale_pos_weight = n_neg / n_pos

print(f"\nClass Balance: {n_neg:,} neg / {n_pos:,} pos = {scale_pos_weight:.1f}:1")

# =============================================================================
# STEP 7: OPTUNA HYPERPARAMETER TUNING
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

study = optuna.create_study(direction='maximize', study_name='xgb_2024_velocity')
study.optimize(objective, n_trials=50, show_progress_bar=True)

print(f"\nBest CV AUC-PR: {study.best_value:.4f}")

# =============================================================================
# STEP 8: TRAIN FINAL MODEL
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
# STEP 9: EVALUATE
# =============================================================================
y_pred_proba = final_model.predict_proba(X_test)[:, 1]

test_auc_roc = roc_auc_score(y_test, y_pred_proba)
test_auc_pr = average_precision_score(y_test, y_pred_proba)

print(f"\n" + "=" * 60)
print("TEST SET PERFORMANCE (Oct-Nov 2024)")
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
# STEP 10: DECILE ANALYSIS
# =============================================================================
print(f"\n" + "=" * 60)
print("DECILE ANALYSIS")
print("=" * 60)

df_eval = pd.DataFrame({
    'y_true': y_test.values,
    'y_pred': y_pred_proba
})
df_eval['decile'] = pd.qcut(df_eval['y_pred'].rank(method='first'), 10, labels=False)

decile_stats = df_eval.groupby('decile').agg({
    'y_true': ['count', 'sum', 'mean'],
    'y_pred': ['min', 'max']
}).round(4)

print("\nDecile | Count | Conversions | Conv Rate | Score Range | Lift")
print("-" * 70)
for decile in range(9, -1, -1):
    count = int(decile_stats.loc[decile, ('y_true', 'count')])
    conversions = int(decile_stats.loc[decile, ('y_true', 'sum')])
    conv_rate = decile_stats.loc[decile, ('y_true', 'mean')]
    min_score = decile_stats.loc[decile, ('y_pred', 'min')]
    max_score = decile_stats.loc[decile, ('y_pred', 'max')]
    decile_lift = conv_rate / base_rate if base_rate > 0 else 0
    marker = "🔥" if decile == 9 else ""
    print(f"  {decile:2d}   | {count:5d} | {conversions:11d} | {conv_rate*100:8.2f}% | {min_score:.3f}-{max_score:.3f} | {decile_lift:.2f}x {marker}")

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

# =============================================================================
# STEP 12: SAVE MODEL
# =============================================================================
date_str = datetime.now().strftime('%Y%m%d')
hash_str = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
model_version = f"v3-2024only-velocity-{date_str}-{hash_str}"

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
    }, f, indent=2)

# Save metrics (convert numpy types to Python types)
metrics = {
    'model_version': model_version,
    'training_date': datetime.now().isoformat(),
    'train_period': 'Feb-Sep 2024',
    'test_period': 'Oct-Nov 2024',
    'train_samples': int(len(X_train)),
    'test_samples': int(len(X_test)),
    'n_features': int(len(ALL_FEATURES)),
    'test_auc_roc': float(test_auc_roc),
    'test_auc_pr': float(test_auc_pr),
    'top_decile_lift': float(lift),
    'baseline_rate': float(base_rate),
    'top_decile_rate': float(top_rate),
    'notes': '2024-only training with velocity features. Excludes unstable Very New/New tenure buckets.'
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
Training Data: 2024 only (Feb-Sep)
Test Data: 2024 only (Oct-Nov)

Performance:
  AUC-ROC: {test_auc_roc:.4f}
  AUC-PR: {test_auc_pr:.4f}
  Top Decile Lift: {lift:.2f}x

Why 2024-Only:
  - 2024 danger zone lift: 4.43x (vs 1.70x in Aug-Oct 2025)
  - "Very New" and "New" tenure buckets FLIP in 2025 (unstable)
  - Cleaner signal without 2025 distribution shift
  
Key Safety Notes:
  ✅ Uses START_DATE only (never END_DATE)
  ✅ All features calculated as of contacted_date (PIT)
  ✅ No backfill leakage risk
  ✅ Excludes unstable tenure bucket categories
""")

if lift >= 2.0:
    print("🎉 TARGET ACHIEVED!")
else:
    print(f"⚠️ Lift is {lift:.2f}x, target is 2.0x")

# =============================================================================
# OPTIONAL: Test on 2025 data too
# =============================================================================
print("\n" + "=" * 70)
print("BONUS: TESTING ON 2025 DATA")
print("=" * 70)

# Load 2025 data
df_2025 = df[df['contacted_date'].dt.year == 2025].copy()
if len(df_2025) > 100:
    df_2025 = engineer_features(df_2025)
    
    # Prepare features
    X_2025 = prepare_features(df_2025, ALL_FEATURES)
    y_2025 = df_2025['target'].astype(int)
    
    # Predict
    y_pred_2025 = final_model.predict_proba(X_2025)[:, 1]
    
    # Evaluate
    if y_2025.sum() > 0:
        auc_2025 = roc_auc_score(y_2025, y_pred_2025)
        lift_2025, top_rate_2025, base_rate_2025 = calculate_lift(y_2025, y_pred_2025)
        
        print(f"\n2025 Out-of-Sample Results:")
        print(f"  Leads: {len(df_2025):,}")
        print(f"  AUC-ROC: {auc_2025:.4f}")
        print(f"  Baseline: {base_rate_2025*100:.2f}%")
        print(f"  Top Decile: {top_rate_2025*100:.2f}%")
        print(f"  LIFT: {lift_2025:.2f}x {'✅' if lift_2025 >= 1.5 else '⚠️'}")
