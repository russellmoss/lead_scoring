# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\phase_4_model_training.py

import sys
from pathlib import Path

# Add Version-2 to path
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

# Import logger
from utils.execution_logger import ExecutionLogger
from utils.paths import PATHS

# Initialize
logger = ExecutionLogger()
logger.start_phase("4", "Model Training & Hyperparameter Tuning")
client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 60)
print("PHASE 4: MODEL TRAINING & HYPERPARAMETER TUNING")
print("=" * 60)

# Step 4.2: Load Data from BigQuery
logger.log_action("Loading training and test data from BigQuery")

query = """
SELECT 
    s.lead_id,
    s.split,
    s.target,
    s.contacted_date,
    f.*
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits` s
INNER JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
    ON s.lead_id = f.lead_id
WHERE s.split IN ('TRAIN', 'TEST')
ORDER BY s.contacted_date  -- CRITICAL: Ensure chronological order
"""

print("Querying BigQuery (this may take 30-60 seconds)...")
df = client.query(query).to_dataframe()
print(f"Loaded {len(df):,} total samples")

# Split into train/test
train_df = df[df['split'] == 'TRAIN'].copy()
test_df = df[df['split'] == 'TEST'].copy()

# =============================================================================
# CRITICAL FIX: SORT BY contacted_date
# =============================================================================
print("\n🔧 CRITICAL FIX: Sorting data by contacted_date...")
train_df = train_df.sort_values('contacted_date').reset_index(drop=True)
test_df = test_df.sort_values('contacted_date').reset_index(drop=True)

print(f"\nTraining set: {len(train_df):,} samples ({train_df['target'].sum():,} positives, {train_df['target'].mean()*100:.2f}%)")
print(f"  Date range: {train_df['contacted_date'].min()} to {train_df['contacted_date'].max()}")
print(f"Test set: {len(test_df):,} samples ({test_df['target'].sum():,} positives, {test_df['target'].mean()*100:.2f}%)")
print(f"  Date range: {test_df['contacted_date'].min()} to {test_df['contacted_date'].max()}")

logger.log_action("CRITICAL FIX: Sorted training data by contacted_date")
logger.log_learning("Previous run had unsorted data causing CV folds with 0% positive rate")

logger.log_metric("Training Samples", len(train_df))
logger.log_metric("Test Samples", len(test_df))
logger.log_metric("Training Positive Rate", f"{train_df['target'].mean()*100:.2f}%")
logger.log_metric("Test Positive Rate", f"{test_df['target'].mean()*100:.2f}%")

# Step 4.3: Engineer Runtime Features
logger.log_action("Engineering runtime features")

def engineer_runtime_features(df):
    """
    Calculate runtime-engineered features.
    These are NOT stored in BigQuery to avoid leakage and ensure consistency.
    """
    df = df.copy()
    
    # Feature 1: flight_risk_score
    # Mobile person at bleeding firm = multiplicative signal
    # pit_moves_3yr * max(-firm_net_change_12mo, 0)
    df['flight_risk_score'] = df['pit_moves_3yr'] * np.maximum(-df['firm_net_change_12mo'], 0)
    
    # Feature 2: is_fresh_start
    # New hire flag (< 12 months at current firm)
    df['is_fresh_start'] = (df['current_firm_tenure_months'] < 12).astype(int)
    
    return df

# Apply to both sets
train_df = engineer_runtime_features(train_df)
test_df = engineer_runtime_features(test_df)

# Log statistics
print(f"\nEngineered Features Statistics (Training):")
print(f"  flight_risk_score: mean={train_df['flight_risk_score'].mean():.2f}, max={train_df['flight_risk_score'].max():.2f}")
print(f"  is_fresh_start: {train_df['is_fresh_start'].mean()*100:.1f}% are fresh starts")

logger.log_metric("Mean Flight Risk Score (Train)", round(train_df['flight_risk_score'].mean(), 2))
logger.log_metric("Fresh Start Rate (Train)", f"{train_df['is_fresh_start'].mean()*100:.1f}%")
logger.log_learning("Engineered flight_risk_score and is_fresh_start at runtime")

# Step 4.4: Define Feature Set
BASE_FEATURES = [
    # Advisor features
    'industry_tenure_months',
    'num_prior_firms',
    'current_firm_tenure_months',
    'pit_moves_3yr',
    'pit_avg_prior_tenure_months',
    'pit_restlessness_ratio',
    
    # Firm features
    'firm_aum_pit',
    'log_firm_aum',
    'firm_net_change_12mo',
    'firm_departures_12mo',
    'firm_arrivals_12mo',
    'firm_stability_percentile',
    'firm_stability_tier',
    
    # Data quality signals
    'is_gender_missing',
    'is_linkedin_missing',
    'is_personal_email_missing',
    
    # Flags
    'has_firm_aum',
    'has_valid_virtual_snapshot',
]

ENGINEERED_FEATURES = [
    'flight_risk_score',
    'is_fresh_start',
]

ALL_FEATURES = BASE_FEATURES + ENGINEERED_FEATURES

# Target column
TARGET = 'target'

print(f"\nFeature set: {len(ALL_FEATURES)} features")
print(f"  Base features: {len(BASE_FEATURES)}")
print(f"  Engineered features: {len(ENGINEERED_FEATURES)}")

logger.log_metric("Total Features", len(ALL_FEATURES))

# Step 4.5: Prepare Feature Matrices
logger.log_action("Preparing feature matrices")

def prepare_features(df, features, target):
    """Prepare feature matrix and target vector."""
    X = df[features].copy()
    y = df[target].copy()
    
    # Fill NaN with 0 for numeric columns (safe default for our features)
    X = X.fillna(0)
    
    # Convert firm_stability_tier to numeric if it's categorical
    if 'firm_stability_tier' in X.columns and X['firm_stability_tier'].dtype == 'object':
        tier_map = {'Severe_Bleeding': 0, 'Moderate_Bleeding': 1, 'Slight_Bleeding': 2, 
                   'Stable': 3, 'Growing': 4}
        X['firm_stability_tier'] = X['firm_stability_tier'].map(tier_map).fillna(2)
    
    return X.astype(np.float32), y.astype(int)

X_train, y_train = prepare_features(train_df, ALL_FEATURES, TARGET)
X_test, y_test = prepare_features(test_df, ALL_FEATURES, TARGET)

print(f"\nFeature matrix shapes:")
print(f"  X_train: {X_train.shape}")
print(f"  X_test: {X_test.shape}")

# Verify no NaN values
assert X_train.isna().sum().sum() == 0, "NaN values in training features!"
assert X_test.isna().sum().sum() == 0, "NaN values in test features!"

logger.log_validation_gate("G4.0.1", "Feature Matrix Valid", True, "No NaN values")

# Step 4.6: Calculate Class Imbalance Weight
logger.log_action("Calculating class imbalance weight")

n_pos = y_train.sum()
n_neg = len(y_train) - n_pos
scale_pos_weight = n_neg / n_pos

print(f"\nClass Balance:")
print(f"  Positive samples: {n_pos:,}")
print(f"  Negative samples: {n_neg:,}")
print(f"  Ratio: {n_neg/n_pos:.1f}:1")
print(f"  scale_pos_weight: {scale_pos_weight:.2f}")

logger.log_metric("Positive Samples", n_pos)
logger.log_metric("Negative Samples", n_neg)
logger.log_metric("scale_pos_weight", round(scale_pos_weight, 2))

# Step 4.6.5: VERIFY CV FOLDS (THE FIX!)
print("\n" + "="*60)
print("VERIFYING CV FOLDS (This was broken before!)")
print("="*60)

tscv = TimeSeriesSplit(n_splits=5)

cv_valid = True
for i, (train_idx, val_idx) in enumerate(tscv.split(X_train)):
    y_train_fold = y_train.iloc[train_idx]
    y_val_fold = y_train.iloc[val_idx]
    
    train_pos = y_train_fold.sum()
    val_pos = y_val_fold.sum()
    train_rate = y_train_fold.mean() * 100
    val_rate = y_val_fold.mean() * 100
    
    status = "✅" if train_pos > 0 and val_pos > 0 else "❌"
    print(f"Fold {i+1}: Train={len(train_idx):,} ({train_rate:.2f}%, {train_pos} pos), Val={len(val_idx):,} ({val_rate:.2f}%, {val_pos} pos) {status}")
    
    if train_pos == 0 or val_pos == 0:
        cv_valid = False

if cv_valid:
    print("\n✅ CV FOLDS VERIFIED: All folds have positive examples!")
    logger.log_validation_gate("G4.0.2", "CV Folds Valid", True, "All folds have positives")
else:
    print("\n❌ CV STILL BROKEN - Check data sorting!")
    logger.log_validation_gate("G4.0.2", "CV Folds Valid", False, "Some folds missing positives")
    raise ValueError("CV folds are invalid - cannot proceed with training")

# Step 4.7: Optuna Hyperparameter Tuning
logger.log_action("Running Optuna hyperparameter optimization with VALID CV folds")

print("\n" + "="*60)
print("OPTUNA HYPERPARAMETER TUNING (50 trials)")
print("="*60)
print("Now CV scores should VARY across trials (not all identical)!\n")

def objective(trial):
    """Optuna objective function for XGBoost tuning."""
    
    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'aucpr',  # AUC-PR for imbalanced data
        'tree_method': 'hist',
        'random_state': 42,
        'scale_pos_weight': scale_pos_weight,
        
        # Hyperparameters to tune
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
    
    # Cross-validation scores
    cv_scores = []
    
    for train_idx, val_idx in tscv.split(X_train):
        X_cv_train, X_cv_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
        y_cv_train, y_cv_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
        
        model = xgb.XGBClassifier(**params, verbosity=0)
        model.fit(
            X_cv_train, y_cv_train,
            eval_set=[(X_cv_val, y_cv_val)],
            verbose=False
        )
        
        y_pred_proba = model.predict_proba(X_cv_val)[:, 1]
        score = average_precision_score(y_cv_val, y_pred_proba)
        cv_scores.append(score)
    
    return np.mean(cv_scores)

# Run optimization
print("\nStarting Optuna optimization (this may take 5-15 minutes)...")
print("Optimizing for AUC-PR with 5-fold temporal CV...")

study = optuna.create_study(direction='maximize', study_name='xgb_lead_scoring_v3_fixed')
study.optimize(objective, n_trials=50, show_progress_bar=True)

# Check for variation in trials
trial_values = [t.value for t in study.trials if t.value is not None]
cv_std = np.std(trial_values) if len(trial_values) > 1 else 0
cv_range = max(trial_values) - min(trial_values) if len(trial_values) > 1 else 0

print(f"\nOptuna Results:")
print(f"  Best CV AUC-PR: {study.best_value:.4f}")
print(f"  CV Score Range: {min(trial_values):.4f} - {max(trial_values):.4f}")
print(f"  CV Score Std Dev: {cv_std:.4f}")

if cv_std > 0.001:
    print("  ✅ CV scores vary across trials - tuning is working!")
    logger.log_learning(f"CV scores now vary (std={cv_std:.4f}) - tuning effective")
else:
    print("  ⚠️ CV scores still identical - something may still be wrong")
    logger.log_learning(f"CV scores still identical (std={cv_std:.4f}) - investigate further")

print(f"\nBest Parameters:")
for k, v in study.best_params.items():
    print(f"  {k}: {v}")

logger.log_metric("Optuna Trials", 50)
logger.log_metric("Best CV AUC-PR", round(study.best_value, 4))
logger.log_metric("CV Score Std Dev", round(cv_std, 4))

# Step 4.8: Train Final Model
logger.log_action("Training final model with best hyperparameters")

# Best hyperparameters
best_params = {
    'objective': 'binary:logistic',
    'eval_metric': 'aucpr',
    'tree_method': 'hist',
    'random_state': 42,
    'scale_pos_weight': scale_pos_weight,
    **study.best_params
}

print("\nTraining final model with best parameters...")
final_model = xgb.XGBClassifier(**best_params, verbosity=1)
final_model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=True
)

print("✅ Model training complete")
logger.log_validation_gate("G4.1.1", "Model Trains Successfully", True, "No errors during training")

# Step 4.9: Evaluate on Test Set
logger.log_action("Evaluating model on test set")

# Predictions
y_pred_proba = final_model.predict_proba(X_test)[:, 1]
y_pred = (y_pred_proba >= 0.5).astype(int)

# Metrics
test_auc_roc = roc_auc_score(y_test, y_pred_proba)
test_auc_pr = average_precision_score(y_test, y_pred_proba)

print(f"\nTest Set Performance:")
print(f"  AUC-ROC: {test_auc_roc:.4f}")
print(f"  AUC-PR: {test_auc_pr:.4f}")
print(f"  Baseline (positive rate): {y_test.mean():.4f}")

logger.log_metric("Test AUC-ROC", round(test_auc_roc, 4))
logger.log_metric("Test AUC-PR", round(test_auc_pr, 4))

# Calculate top decile lift
def calculate_top_decile_lift(y_true, y_pred_proba):
    """Calculate lift in top decile."""
    df_eval = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred_proba})
    df_eval['decile'] = pd.qcut(df_eval['y_pred'], 10, labels=False, duplicates='drop')
    
    top_decile = df_eval[df_eval['decile'] == df_eval['decile'].max()]
    top_decile_rate = top_decile['y_true'].mean()
    baseline_rate = df_eval['y_true'].mean()
    lift = top_decile_rate / baseline_rate if baseline_rate > 0 else 0
    
    return lift, top_decile_rate, baseline_rate

lift, top_rate, base_rate = calculate_top_decile_lift(y_test, y_pred_proba)

print(f"\nTop Decile Performance:")
print(f"  Baseline conversion rate: {base_rate*100:.2f}%")
print(f"  Top decile conversion rate: {top_rate*100:.2f}%")
print(f"  Top decile LIFT: {lift:.2f}x")

logger.log_metric("Top Decile Lift", round(lift, 2))
logger.log_metric("Top Decile Conversion Rate", f"{top_rate*100:.2f}%")
logger.log_metric("Baseline Conversion Rate", f"{base_rate*100:.2f}%")

# Validation gate
if lift >= 1.9:
    logger.log_validation_gate("G5.1.1", "Top Decile Lift ≥ 1.9x", True, f"Achieved {lift:.2f}x")
    print(f"\n✅ G5.1.1 PASSED: Top decile lift {lift:.2f}x ≥ 1.9x target")
else:
    logger.log_validation_gate("G5.1.1", "Top Decile Lift ≥ 1.9x", False, f"Only {lift:.2f}x")
    print(f"\n⚠️ G5.1.1 WARNING: Top decile lift {lift:.2f}x < 1.9x target")

# Step 4.10: Feature Importance
logger.log_action("Calculating feature importance")

# Get feature importance
importance_df = pd.DataFrame({
    'feature': ALL_FEATURES,
    'importance': final_model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nTop 10 Features by Importance:")
print(importance_df.head(10).to_string(index=False))

# Check protected features are contributing
protected = ['pit_moves_3yr', 'firm_net_change_12mo', 'flight_risk_score']
for feat in protected:
    if feat in importance_df['feature'].values:
        imp = importance_df[importance_df['feature'] == feat]['importance'].values[0]
        rank = importance_df[importance_df['feature'] == feat].index[0] + 1
        print(f"\n✅ Protected feature '{feat}': importance={imp:.4f}, rank={rank}")

logger.log_learning(f"Top feature: {importance_df.iloc[0]['feature']} with importance {importance_df.iloc[0]['importance']:.4f}")

# Step 4.11: Save Model Artifacts
logger.log_action("Saving model artifacts")

# Generate version ID
date_str = datetime.now().strftime('%Y%m%d')
hash_str = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
model_version = f"v3-boosted-{date_str}-{hash_str}"

# Create model directory
model_dir = PATHS['MODELS_DIR'] / model_version
model_dir.mkdir(parents=True, exist_ok=True)

# Save model
model_path = model_dir / 'model.pkl'
with open(model_path, 'wb') as f:
    pickle.dump(final_model, f)
print(f"✅ Model saved: {model_path}")
logger.log_file_created("model.pkl", str(model_path), "Trained XGBoost model")

# Save hyperparameters
params_path = model_dir / 'hyperparameters.json'
with open(params_path, 'w') as f:
    json.dump(best_params, f, indent=2, default=str)
print(f"✅ Hyperparameters saved: {params_path}")
logger.log_file_created("hyperparameters.json", str(params_path), "Best hyperparameters from Optuna")

# Save feature names
features_path = model_dir / 'feature_names.json'
with open(features_path, 'w') as f:
    json.dump({
        'base_features': BASE_FEATURES,
        'engineered_features': ENGINEERED_FEATURES,
        'all_features': ALL_FEATURES,
        'target': TARGET
    }, f, indent=2)
print(f"✅ Feature names saved: {features_path}")
logger.log_file_created("feature_names.json", str(features_path), "Feature configuration")

# Save feature importance
importance_path = model_dir / 'feature_importance.csv'
importance_df.to_csv(importance_path, index=False)
print(f"✅ Feature importance saved: {importance_path}")
logger.log_file_created("feature_importance.csv", str(importance_path), "Feature importance rankings")

# Save training metrics
metrics = {
    'model_version': model_version,
    'training_date': datetime.now().isoformat(),
    'train_samples': len(X_train),
    'test_samples': len(X_test),
    'n_features': len(ALL_FEATURES),
    'scale_pos_weight': scale_pos_weight,
    'optuna_trials': 50,
    'cv_fix_applied': True,
    'cv_score_std': float(cv_std),
    'best_cv_auc_pr': float(study.best_value),
    'test_auc_roc': float(test_auc_roc),
    'test_auc_pr': float(test_auc_pr),
    'top_decile_lift': float(lift),
    'top_decile_rate': float(top_rate),
    'baseline_rate': float(base_rate),
}
metrics_path = model_dir / 'training_metrics.json'
with open(metrics_path, 'w') as f:
    json.dump(metrics, f, indent=2)
print(f"✅ Training metrics saved: {metrics_path}")
logger.log_file_created("training_metrics.json", str(metrics_path), "Model performance metrics")

# Update model registry
registry_path = PATHS['REGISTRY']
if registry_path.exists():
    with open(registry_path, 'r') as f:
        registry = json.load(f)
else:
    registry = {'models': []}

registry['models'].append({
    'version_id': model_version,
    'status': 'trained',  # Will become 'production' after calibration
    'created_at': datetime.now().isoformat(),
    'metrics': metrics
})
registry['latest'] = model_version

with open(registry_path, 'w') as f:
    json.dump(registry, f, indent=2)
print(f"✅ Registry updated: {registry_path}")
logger.log_file_created("registry.json", str(registry_path), "Model registry")

print(f"\n{'='*60}")
print(f"MODEL VERSION: {model_version}")
print(f"{'='*60}")

# Step 4.12: Complete Phase
print("\n" + "=" * 60)
print("PHASE 4 COMPLETE: MODEL TRAINING")
print("=" * 60)

print(f"\nModel: {model_version}")
print(f"CV Fix Applied: ✅ Data sorted by contacted_date")
print(f"Training samples: {len(X_train):,}")
print(f"Features: {len(ALL_FEATURES)}")
print(f"\nPerformance:")
print(f"  Test AUC-ROC: {test_auc_roc:.4f}")
print(f"  Test AUC-PR: {test_auc_pr:.4f}")
print(f"  Top Decile Lift: {lift:.2f}x {'✅' if lift >= 1.9 else '⚠️'}")

print(f"\nComparison to Previous (Broken CV):")
print(f"  Previous Lift: 1.46x")
print(f"  New Lift: {lift:.2f}x")
if lift > 1.46:
    print(f"  Improvement: {(lift - 1.46) / 1.46 * 100:.1f}%")
else:
    print(f"  Change: {(lift - 1.46) / 1.46 * 100:.1f}%")

# End phase logging
logger.log_learning(f"CV fix applied - data sorted by contacted_date before CV")
if lift > 1.46:
    logger.log_learning(f"CV fix improved lift from 1.46x to {lift:.2f}x")
else:
    logger.log_learning(f"CV fix applied but lift is {lift:.2f}x (previous: 1.46x)")

logger.end_phase(
    status="PASSED" if lift >= 1.9 else "PASSED WITH WARNINGS",
    next_steps=[
        "Phase 5: Model Evaluation & SHAP Analysis",
        "Phase 6: Probability Calibration",
        "Review feature importance for business insights"
    ]
)

print(f"\n✅ Model saved to: {model_dir}")
print(f"📝 Execution log updated: {PATHS['EXECUTION_LOG']}")

