# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\phase_4_retrain_with_v2_features.py

import sys
from pathlib import Path

VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

import pandas as pd
import numpy as np
import json
import pickle
import hashlib
from datetime import datetime
from google.cloud import bigquery
import xgboost as xgb
import optuna
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, average_precision_score
import warnings
warnings.filterwarnings('ignore')

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from utils.execution_logger import ExecutionLogger
from utils.paths import PATHS

# Initialize
logger = ExecutionLogger()
logger.start_phase("4-V2-FEATURES", "Model Training with V2 Feature Set")
client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("PHASE 4 (V2 FEATURES): RETRAIN WITH MOBILITY TIERS & FIXED SPARSITY")
print("=" * 70)

# =============================================================================
# STEP 1: CREATE ENHANCED FEATURE TABLE IN BIGQUERY
# =============================================================================
logger.log_action("Creating enhanced feature table with v2-style features")

create_table_sql = """
CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2` AS

WITH base_data AS (
    SELECT 
        s.*,
        f.* EXCEPT(lead_id, contacted_date, target, pit_month, feature_extraction_ts)
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits` s
    INNER JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
        ON s.lead_id = f.lead_id
)

SELECT 
    *,
    
    -- MOBILITY TIERS (v2 style - one-hot encoded)
    CASE WHEN pit_moves_3yr = 0 THEN 1 ELSE 0 END AS pit_mobility_tier_Stable,
    CASE WHEN pit_moves_3yr IN (1, 2) THEN 1 ELSE 0 END AS pit_mobility_tier_Mobile,
    CASE WHEN pit_moves_3yr >= 3 THEN 1 ELSE 0 END AS pit_mobility_tier_Highly_Mobile,
    
    -- BINARY FLAGS (handle sparsity by decomposing)
    CASE WHEN pit_moves_3yr > 0 THEN 1 ELSE 0 END AS has_prior_moves,
    CASE WHEN firm_net_change_12mo < 0 THEN 1 ELSE 0 END AS is_bleeding_firm,
    CASE WHEN pit_moves_3yr > 0 AND firm_net_change_12mo < 0 THEN 1 ELSE 0 END AS is_flight_risk,
    
    -- FLIGHT RISK TIER (binned to handle sparsity)
    CASE 
        WHEN pit_moves_3yr = 0 OR firm_net_change_12mo >= 0 THEN 0
        WHEN pit_moves_3yr * GREATEST(-firm_net_change_12mo, 0) <= 10 THEN 1
        WHEN pit_moves_3yr * GREATEST(-firm_net_change_12mo, 0) <= 50 THEN 2
        ELSE 3
    END AS flight_risk_tier
    
FROM base_data
"""

print("Creating enhanced feature table...")
client.query(create_table_sql).result()
print("✅ Table created: lead_scoring_splits_v2")
logger.log_file_created("lead_scoring_splits_v2", "BigQuery", "Enhanced feature table with v2-style features")

# =============================================================================
# STEP 2: VERIFY NEW FEATURES
# =============================================================================
logger.log_action("Verifying new feature distributions")

verify_sql = """
SELECT 
    split,
    COUNT(*) as total,
    
    -- Mobility tier distribution
    ROUND(AVG(pit_mobility_tier_Stable) * 100, 1) as pct_stable,
    ROUND(AVG(pit_mobility_tier_Mobile) * 100, 1) as pct_mobile,
    ROUND(AVG(pit_mobility_tier_Highly_Mobile) * 100, 1) as pct_highly_mobile,
    
    -- Flag distribution
    ROUND(AVG(has_prior_moves) * 100, 1) as pct_has_moves,
    ROUND(AVG(is_bleeding_firm) * 100, 1) as pct_bleeding_firm,
    ROUND(AVG(is_flight_risk) * 100, 1) as pct_flight_risk,
    
    -- Conversion by mobility tier
    ROUND(AVG(CASE WHEN pit_mobility_tier_Stable = 1 THEN target END) * 100, 2) as conv_stable,
    ROUND(AVG(CASE WHEN pit_mobility_tier_Mobile = 1 THEN target END) * 100, 2) as conv_mobile,
    ROUND(AVG(CASE WHEN pit_mobility_tier_Highly_Mobile = 1 THEN target END) * 100, 2) as conv_highly_mobile,
    
    -- Conversion by flight risk tier
    ROUND(AVG(CASE WHEN flight_risk_tier = 0 THEN target END) * 100, 2) as conv_no_risk,
    ROUND(AVG(CASE WHEN flight_risk_tier >= 1 THEN target END) * 100, 2) as conv_any_risk
    
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2`
GROUP BY split
"""

print("\nFeature Distribution & Conversion Rates:")
df_verify = client.query(verify_sql).to_dataframe()
print(df_verify.to_string(index=False))

# Log key findings
for _, row in df_verify.iterrows():
    if row['split'] == 'TRAIN':
        logger.log_metric(f"Stable %", row['pct_stable'])
        logger.log_metric(f"Mobile %", row['pct_mobile'])
        logger.log_metric(f"Highly Mobile %", row['pct_highly_mobile'])
        logger.log_metric(f"Flight Risk %", row['pct_flight_risk'])
        
        # Check for conversion lift in mobility tiers
        if pd.notna(row['conv_highly_mobile']) and pd.notna(row['conv_stable']) and row['conv_stable'] > 0:
            mobility_lift = row['conv_highly_mobile'] / row['conv_stable']
            logger.log_metric("Highly Mobile vs Stable Lift", f"{mobility_lift:.2f}x")
            print(f"\n✅ Highly Mobile vs Stable conversion lift: {mobility_lift:.2f}x")

# =============================================================================
# STEP 3: LOAD DATA
# =============================================================================
logger.log_action("Loading enhanced feature data")

query = """
SELECT *
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2`
WHERE split IN ('TRAIN', 'TEST')
ORDER BY contacted_date
"""

df = client.query(query).to_dataframe()
print(f"\nLoaded {len(df):,} samples")

train_df = df[df['split'] == 'TRAIN'].copy().reset_index(drop=True)
test_df = df[df['split'] == 'TEST'].copy().reset_index(drop=True)

print(f"Training: {len(train_df):,} samples ({train_df['target'].mean()*100:.2f}% positive)")
print(f"Test: {len(test_df):,} samples ({test_df['target'].mean()*100:.2f}% positive)")

# =============================================================================
# STEP 4: DEFINE V2-STYLE FEATURE SET
# =============================================================================
logger.log_action("Defining v2-style feature set")

# Core advisor features
ADVISOR_FEATURES = [
    'industry_tenure_months',
    'num_prior_firms',
    'current_firm_tenure_months',
    'pit_moves_3yr',
    'pit_avg_prior_tenure_months',
    'pit_restlessness_ratio',
]

# Mobility tiers (v2 style)
MOBILITY_FEATURES = [
    'pit_mobility_tier_Stable',
    'pit_mobility_tier_Mobile',
    'pit_mobility_tier_Highly_Mobile',
]

# Firm features
FIRM_FEATURES = [
    'firm_aum_pit',
    'log_firm_aum',
    'firm_net_change_12mo',
    'firm_departures_12mo',
    'firm_arrivals_12mo',
    'firm_stability_percentile',
]

# Sparsity-handled features (NEW)
SPARSITY_FEATURES = [
    'has_prior_moves',
    'is_bleeding_firm',
    'is_flight_risk',
    'flight_risk_tier',
]

# Data quality signals (keep - they were helping)
DATA_QUALITY_FEATURES = [
    'has_valid_virtual_snapshot',
    'is_personal_email_missing',
    'has_firm_aum',
]

# Combine all features
ALL_FEATURES = (
    ADVISOR_FEATURES + 
    MOBILITY_FEATURES + 
    FIRM_FEATURES + 
    SPARSITY_FEATURES +
    DATA_QUALITY_FEATURES
)

# We'll still calculate these at runtime for compatibility
RUNTIME_FEATURES = ['flight_risk_score', 'is_fresh_start']

TARGET = 'target'

print(f"\nFeature Set ({len(ALL_FEATURES)} features):")
print(f"  Advisor: {len(ADVISOR_FEATURES)}")
print(f"  Mobility Tiers: {len(MOBILITY_FEATURES)}")
print(f"  Firm: {len(FIRM_FEATURES)}")
print(f"  Sparsity-Handled: {len(SPARSITY_FEATURES)}")
print(f"  Data Quality: {len(DATA_QUALITY_FEATURES)}")

logger.log_metric("Total Features", len(ALL_FEATURES))

# =============================================================================
# STEP 5: ENGINEER RUNTIME FEATURES
# =============================================================================
def engineer_runtime_features(df):
    """Calculate runtime features (for backward compatibility)."""
    df = df.copy()
    df['flight_risk_score'] = df['pit_moves_3yr'] * np.maximum(-df['firm_net_change_12mo'], 0)
    df['is_fresh_start'] = (df['current_firm_tenure_months'] < 12).astype(int)
    return df

train_df = engineer_runtime_features(train_df)
test_df = engineer_runtime_features(test_df)

# Add runtime features to the list
ALL_FEATURES_WITH_RUNTIME = ALL_FEATURES + RUNTIME_FEATURES

print(f"\nTotal features with runtime: {len(ALL_FEATURES_WITH_RUNTIME)}")

# =============================================================================
# STEP 6: PREPARE FEATURE MATRICES
# =============================================================================
logger.log_action("Preparing feature matrices")

def prepare_features(df, features):
    """Prepare feature matrix."""
    X = df[features].copy()
    X = X.fillna(0)
    
    # Convert any remaining object columns to numeric
    for col in X.columns:
        if X[col].dtype == 'object':
            # Create dummy variables or map to numeric
            unique_vals = X[col].unique()
            mapping = {v: i for i, v in enumerate(unique_vals)}
            X[col] = X[col].map(mapping).fillna(0)
    
    return X.astype(np.float32)

X_train = prepare_features(train_df, ALL_FEATURES_WITH_RUNTIME)
y_train = train_df[TARGET].astype(int)
X_test = prepare_features(test_df, ALL_FEATURES_WITH_RUNTIME)
y_test = test_df[TARGET].astype(int)

print(f"\nFeature matrices:")
print(f"  X_train: {X_train.shape}")
print(f"  X_test: {X_test.shape}")

# Verify no NaN
assert X_train.isna().sum().sum() == 0, "NaN in training features!"
logger.log_validation_gate("G4.0.1", "Feature Matrix Valid", True, "No NaN values")

# =============================================================================
# STEP 7: VERIFY CV FOLDS
# =============================================================================
print("\n" + "="*60)
print("VERIFYING CV FOLDS")
print("="*60)

tscv = TimeSeriesSplit(n_splits=5)
for i, (train_idx, val_idx) in enumerate(tscv.split(X_train)):
    y_fold_train = y_train.iloc[train_idx]
    y_fold_val = y_train.iloc[val_idx]
    print(f"Fold {i+1}: Train={len(train_idx):,} ({y_fold_train.mean()*100:.2f}%), Val={len(val_idx):,} ({y_fold_val.mean()*100:.2f}%)")
    
    assert y_fold_train.sum() > 0, f"Fold {i+1} train has no positives!"
    assert y_fold_val.sum() > 0, f"Fold {i+1} val has no positives!"

print("✅ All folds verified")
logger.log_validation_gate("G4.0.2", "CV Folds Valid", True, "All folds have positives")

# =============================================================================
# STEP 8: CLASS IMBALANCE
# =============================================================================
n_pos = y_train.sum()
n_neg = len(y_train) - n_pos
scale_pos_weight = n_neg / n_pos

print(f"\nClass Balance: {n_neg:,} neg / {n_pos:,} pos = {scale_pos_weight:.1f}:1")

# =============================================================================
# STEP 9: OPTUNA HYPERPARAMETER TUNING
# =============================================================================
logger.log_action("Running Optuna hyperparameter optimization")

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
        
        model = xgb.XGBClassifier(**params, verbosity=0)
        model.fit(X_cv_train, y_cv_train, eval_set=[(X_cv_val, y_cv_val)], verbose=False)
        
        y_pred = model.predict_proba(X_cv_val)[:, 1]
        cv_scores.append(average_precision_score(y_cv_val, y_pred))
    
    return np.mean(cv_scores)

print("\n" + "="*60)
print("OPTUNA HYPERPARAMETER TUNING (50 trials)")
print("="*60)

study = optuna.create_study(direction='maximize', study_name='xgb_v3_with_v2_features')
study.optimize(objective, n_trials=50, show_progress_bar=True)

trial_values = [t.value for t in study.trials if t.value is not None]
print(f"\nBest CV AUC-PR: {study.best_value:.4f}")
print(f"CV Score Range: {min(trial_values):.4f} - {max(trial_values):.4f}")
print(f"CV Score Std: {np.std(trial_values):.4f}")

logger.log_metric("Best CV AUC-PR", round(study.best_value, 4))

# =============================================================================
# STEP 10: TRAIN FINAL MODEL
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

print("✅ Model trained")
logger.log_validation_gate("G4.1.1", "Model Trains Successfully", True, "No errors")

# =============================================================================
# STEP 11: EVALUATE
# =============================================================================
logger.log_action("Evaluating on test set")

y_pred_proba = final_model.predict_proba(X_test)[:, 1]

test_auc_roc = roc_auc_score(y_test, y_pred_proba)
test_auc_pr = average_precision_score(y_test, y_pred_proba)

print(f"\n" + "="*60)
print("TEST SET PERFORMANCE")
print("="*60)
print(f"AUC-ROC: {test_auc_roc:.4f}")
print(f"AUC-PR: {test_auc_pr:.4f}")

# Top decile lift
def calculate_lift(y_true, y_pred):
    df_eval = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred})
    df_eval['decile'] = pd.qcut(df_eval['y_pred'].rank(method='first'), 10, labels=False, duplicates='drop')
    
    top_decile = df_eval[df_eval['decile'] == df_eval['decile'].max()]
    top_rate = top_decile['y_true'].mean()
    base_rate = df_eval['y_true'].mean()
    
    return top_rate / base_rate if base_rate > 0 else 0, top_rate, base_rate

lift, top_rate, base_rate = calculate_lift(y_test, y_pred_proba)

print(f"\nTOP DECILE:")
print(f"  Baseline: {base_rate*100:.2f}%")
print(f"  Top Decile: {top_rate*100:.2f}%")
print(f"  LIFT: {lift:.2f}x {'✅' if lift >= 1.9 else '⚠️'}")

logger.log_metric("Test AUC-ROC", round(test_auc_roc, 4))
logger.log_metric("Test AUC-PR", round(test_auc_pr, 4))
logger.log_metric("Top Decile Lift", round(lift, 2))

if lift >= 1.9:
    logger.log_validation_gate("G5.1.1", "Top Decile Lift >= 1.9x", True, f"{lift:.2f}x")
else:
    logger.log_validation_gate("G5.1.1", "Top Decile Lift >= 1.9x", False, f"{lift:.2f}x")

# =============================================================================
# STEP 12: FEATURE IMPORTANCE
# =============================================================================
importance_df = pd.DataFrame({
    'feature': ALL_FEATURES_WITH_RUNTIME,
    'importance': final_model.feature_importances_
}).sort_values('importance', ascending=False)

print(f"\nTOP 10 FEATURES:")
for i, (_, row) in enumerate(importance_df.head(10).iterrows()):
    marker = ""
    if row['feature'] in MOBILITY_FEATURES:
        marker = "🎯 MOBILITY"
    elif row['feature'] in SPARSITY_FEATURES:
        marker = "🔧 SPARSITY-FIX"
    print(f"  {i+1}. {row['feature']}: {row['importance']:.4f} {marker}")

# Check if new features are being used
mobility_importance = importance_df[importance_df['feature'].isin(MOBILITY_FEATURES)]['importance'].sum()
sparsity_importance = importance_df[importance_df['feature'].isin(SPARSITY_FEATURES)]['importance'].sum()

print(f"\nFeature Group Importance:")
print(f"  Mobility Tiers: {mobility_importance:.4f}")
print(f"  Sparsity-Handled: {sparsity_importance:.4f}")

logger.log_learning(f"Mobility tiers total importance: {mobility_importance:.4f}")
logger.log_learning(f"Sparsity-handled features importance: {sparsity_importance:.4f}")

# =============================================================================
# STEP 13: SAVE MODEL
# =============================================================================
logger.log_action("Saving model artifacts")

date_str = datetime.now().strftime('%Y%m%d')
hash_str = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
model_version = f"v3-v2features-{date_str}-{hash_str}"

model_dir = PATHS['MODELS_DIR'] / model_version
model_dir.mkdir(parents=True, exist_ok=True)

# Save model
with open(model_dir / 'model.pkl', 'wb') as f:
    pickle.dump(final_model, f)
logger.log_file_created("model.pkl", str(model_dir / 'model.pkl'), "Trained XGBoost model")

# Save config
with open(model_dir / 'feature_names.json', 'w', encoding='utf-8') as f:
    json.dump({
        'all_features': ALL_FEATURES_WITH_RUNTIME,
        'advisor_features': ADVISOR_FEATURES,
        'mobility_features': MOBILITY_FEATURES,
        'firm_features': FIRM_FEATURES,
        'sparsity_features': SPARSITY_FEATURES,
        'data_quality_features': DATA_QUALITY_FEATURES,
        'runtime_features': RUNTIME_FEATURES,
        'target': TARGET
    }, f, indent=2)
logger.log_file_created("feature_names.json", str(model_dir / 'feature_names.json'), "Feature configuration")

# Save hyperparameters
with open(model_dir / 'hyperparameters.json', 'w', encoding='utf-8') as f:
    json.dump(best_params, f, indent=2, default=str)
logger.log_file_created("hyperparameters.json", str(model_dir / 'hyperparameters.json'), "Best hyperparameters")

# Save importance
importance_df.to_csv(model_dir / 'feature_importance.csv', index=False)
logger.log_file_created("feature_importance.csv", str(model_dir / 'feature_importance.csv'), "Feature importance rankings")

# Save metrics
metrics = {
    'model_version': model_version,
    'training_date': datetime.now().isoformat(),
    'train_samples': len(X_train),
    'test_samples': len(X_test),
    'n_features': len(ALL_FEATURES_WITH_RUNTIME),
    'test_auc_roc': float(test_auc_roc),
    'test_auc_pr': float(test_auc_pr),
    'top_decile_lift': float(lift),
    'baseline_rate': float(base_rate),
    'top_decile_rate': float(top_rate),
    'mobility_tiers_added': True,
    'sparsity_handling_added': True,
}
with open(model_dir / 'training_metrics.json', 'w', encoding='utf-8') as f:
    json.dump(metrics, f, indent=2)
logger.log_file_created("training_metrics.json", str(model_dir / 'training_metrics.json'), "Performance metrics")

print(f"\n✅ Model saved: {model_dir}")

# Update registry
registry_path = PATHS['REGISTRY']
if registry_path.exists():
    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
else:
    registry = {'models': []}

registry['models'].append({
    'version_id': model_version,
    'status': 'trained',
    'created_at': datetime.now().isoformat(),
    'metrics': metrics,
    'notes': 'Added v2-style mobility tiers and sparsity handling'
})
registry['latest'] = model_version

with open(registry_path, 'w', encoding='utf-8') as f:
    json.dump(registry, f, indent=2)

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "="*70)
print("PHASE 4 (V2 FEATURES) COMPLETE")
print("="*70)

print(f"""
Model: {model_version}
Features: {len(ALL_FEATURES_WITH_RUNTIME)} (added mobility tiers + sparsity handling)

Performance:
  AUC-ROC: {test_auc_roc:.4f}
  AUC-PR: {test_auc_pr:.4f}
  Top Decile Lift: {lift:.2f}x {'✅ TARGET MET!' if lift >= 1.9 else '⚠️ Below target'}

Comparison:
  Previous (broken features): 1.50x
  Current (v2 features): {lift:.2f}x
  Target (v2 model): 2.62x
  
Key Changes:
  ✅ Added mobility tiers (Stable/Mobile/Highly Mobile)
  ✅ Added sparsity-handling features (has_prior_moves, is_bleeding_firm, is_flight_risk)
  ✅ Added flight_risk_tier (binned version)
  ✅ Kept data quality signals (they were helping)
""")

logger.end_phase(
    status="PASSED" if lift >= 1.9 else "PASSED WITH WARNINGS",
    next_steps=[
        "Phase 5: SHAP Analysis" if lift >= 1.9 else "Investigate remaining gap to 2.62x target",
        "Phase 6: Probability Calibration",
        "Phase 8: Temporal Backtest"
    ]
)

print(f"\n📁 Model saved to: {model_dir}")
print(f"📝 Execution log updated: {PATHS['EXECUTION_LOG']}")

