# Cursor Prompt: Fix Phase 4 - Sort Data Before Training

## Critical Issue Found

The training data was **NOT sorted by `contacted_date`**, causing TimeSeriesSplit to create invalid CV folds with zero positive examples in folds 1-4. This made Optuna hyperparameter tuning completely ineffective.

## The Fix

Re-run Phase 4 with **ONE CRITICAL CHANGE**: Sort the data by `contacted_date` before CV and training.

---

## Updated Phase 4 Script

```python
# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\phase_4_model_training_fixed.py

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

# Import logger
from utils.execution_logger import ExecutionLogger
from utils.paths import PATHS

# Initialize
logger = ExecutionLogger()
logger.start_phase("4-FIXED", "Model Training (Fixed CV)")
client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 60)
print("PHASE 4 (FIXED): MODEL TRAINING WITH SORTED DATA")
print("=" * 60)

# =============================================================================
# STEP 1: LOAD DATA FROM BIGQUERY
# =============================================================================
logger.log_action("Loading training and test data from BigQuery")

query = """
SELECT *
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
ORDER BY contacted_date  -- Ensure chronological order from BigQuery
"""

df = client.query(query).result().to_dataframe()
print(f"Loaded {len(df):,} total samples")

# Split into train/test
train_df = df[df['split_set'] == 'TRAIN'].copy()
test_df = df[df['split_set'] == 'TEST'].copy()

# =============================================================================
# CRITICAL FIX: SORT BY contacted_date
# =============================================================================
print("\n🔧 CRITICAL FIX: Sorting data by contacted_date...")

train_df = train_df.sort_values('contacted_date').reset_index(drop=True)
test_df = test_df.sort_values('contacted_date').reset_index(drop=True)

print(f"Training set: {len(train_df):,} samples")
print(f"  Date range: {train_df['contacted_date'].min()} to {train_df['contacted_date'].max()}")
print(f"Test set: {len(test_df):,} samples")
print(f"  Date range: {test_df['contacted_date'].min()} to {test_df['contacted_date'].max()}")

logger.log_action("CRITICAL FIX: Sorted training data by contacted_date")
logger.log_learning("Previous run had unsorted data causing CV folds with 0% positive rate")

# =============================================================================
# STEP 2: ENGINEER RUNTIME FEATURES
# =============================================================================
logger.log_action("Engineering runtime features")

def engineer_runtime_features(df):
    """Calculate runtime-engineered features."""
    df = df.copy()
    
    # Feature 1: flight_risk_score (showed +657% signal in diagnostics!)
    df['flight_risk_score'] = df['pit_moves_3yr'] * np.maximum(-df['firm_net_change_12mo'], 0)
    
    # Feature 2: is_fresh_start
    df['is_fresh_start'] = (df['current_firm_tenure_months'] < 12).astype(int)
    
    return df

train_df = engineer_runtime_features(train_df)
test_df = engineer_runtime_features(test_df)

print(f"\nEngineered Features (Training):")
print(f"  flight_risk_score: mean={train_df['flight_risk_score'].mean():.2f}, max={train_df['flight_risk_score'].max():.2f}")
print(f"  is_fresh_start: {train_df['is_fresh_start'].mean()*100:.1f}% fresh starts")

# =============================================================================
# STEP 3: DEFINE FEATURE SET
# =============================================================================
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
    'firm_stability_tier',
    'is_gender_missing',
    'is_linkedin_missing',
    'is_personal_email_missing',
    'has_firm_aum',
    'has_valid_virtual_snapshot',
]

ENGINEERED_FEATURES = ['flight_risk_score', 'is_fresh_start']
ALL_FEATURES = BASE_FEATURES + ENGINEERED_FEATURES

# Identify target column (check what exists in dataframe)
target_candidates = ['converted_to_mql', 'is_mql', 'target', 'label', 'mql_flag']
TARGET = None
for col in target_candidates:
    if col in train_df.columns:
        TARGET = col
        break

if TARGET is None:
    # Find boolean/binary columns that might be the target
    for col in train_df.columns:
        if train_df[col].nunique() == 2 and train_df[col].dtype in ['int64', 'bool', 'int32']:
            if 'mql' in col.lower() or 'convert' in col.lower() or 'target' in col.lower():
                TARGET = col
                break

print(f"\nTarget column: {TARGET}")
print(f"Total features: {len(ALL_FEATURES)}")

# =============================================================================
# STEP 4: PREPARE FEATURE MATRICES
# =============================================================================
logger.log_action("Preparing feature matrices")

def prepare_features(df, features, target):
    """Prepare feature matrix and target vector."""
    X = df[features].copy()
    y = df[target].copy()
    
    # Fill NaN with 0 for numeric columns
    X = X.fillna(0)
    
    # Convert firm_stability_tier to numeric if categorical
    if 'firm_stability_tier' in X.columns and X['firm_stability_tier'].dtype == 'object':
        tier_map = {'High Attrition': 0, 'Moderate': 1, 'Stable': 2, 'Growing': 3}
        X['firm_stability_tier'] = X['firm_stability_tier'].map(tier_map).fillna(1)
    
    return X.astype(np.float32), y.astype(int)

X_train, y_train = prepare_features(train_df, ALL_FEATURES, TARGET)
X_test, y_test = prepare_features(test_df, ALL_FEATURES, TARGET)

print(f"\nFeature matrices:")
print(f"  X_train: {X_train.shape}")
print(f"  X_test: {X_test.shape}")

# =============================================================================
# STEP 5: VERIFY CV FOLDS (THE FIX!)
# =============================================================================
print("\n" + "="*60)
print("VERIFYING CV FOLDS (This was broken before!)")
print("="*60)

tscv = TimeSeriesSplit(n_splits=5, gap=0)  # No gap within CV, gap is in train/test split

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

# =============================================================================
# STEP 6: CLASS IMBALANCE
# =============================================================================
n_pos = y_train.sum()
n_neg = len(y_train) - n_pos
scale_pos_weight = n_neg / n_pos

print(f"\nClass Balance:")
print(f"  Positive: {n_pos:,} ({n_pos/len(y_train)*100:.2f}%)")
print(f"  Negative: {n_neg:,} ({n_neg/len(y_train)*100:.2f}%)")
print(f"  scale_pos_weight: {scale_pos_weight:.2f}")

# =============================================================================
# STEP 7: OPTUNA HYPERPARAMETER TUNING (NOW WITH VALID CV!)
# =============================================================================
logger.log_action("Running Optuna with VALID CV folds")

def objective(trial):
    """Optuna objective function."""
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
        
        y_pred_proba = model.predict_proba(X_cv_val)[:, 1]
        score = average_precision_score(y_cv_val, y_pred_proba)
        cv_scores.append(score)
    
    return np.mean(cv_scores)

print("\n" + "="*60)
print("OPTUNA HYPERPARAMETER TUNING (50 trials)")
print("="*60)
print("Now CV scores should VARY across trials (not all identical)!\n")

study = optuna.create_study(direction='maximize', study_name='xgb_lead_scoring_v3_fixed')
study.optimize(objective, n_trials=50, show_progress_bar=True)

# Check for variation in trials
trial_values = [t.value for t in study.trials if t.value is not None]
cv_std = np.std(trial_values)
cv_range = max(trial_values) - min(trial_values)

print(f"\nOptuna Results:")
print(f"  Best CV AUC-PR: {study.best_value:.4f}")
print(f"  CV Score Range: {min(trial_values):.4f} - {max(trial_values):.4f}")
print(f"  CV Score Std Dev: {cv_std:.4f}")

if cv_std > 0.001:
    print("  ✅ CV scores vary across trials - tuning is working!")
    logger.log_learning(f"CV scores now vary (std={cv_std:.4f}) - tuning effective")
else:
    print("  ⚠️ CV scores still identical - something may still be wrong")

logger.log_metric("Best CV AUC-PR", round(study.best_value, 4))
logger.log_metric("CV Score Std Dev", round(cv_std, 4))

print(f"\nBest Parameters:")
for k, v in study.best_params.items():
    print(f"  {k}: {v}")

# =============================================================================
# STEP 8: TRAIN FINAL MODEL
# =============================================================================
logger.log_action("Training final model with best hyperparameters")

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

print("✅ Model training complete")
logger.log_validation_gate("G4.1.1", "Model Trains Successfully", True, "No errors")

# =============================================================================
# STEP 9: EVALUATE ON TEST SET
# =============================================================================
logger.log_action("Evaluating on test set")

y_pred_proba = final_model.predict_proba(X_test)[:, 1]

test_auc_roc = roc_auc_score(y_test, y_pred_proba)
test_auc_pr = average_precision_score(y_test, y_pred_proba)

print(f"\n" + "="*60)
print("TEST SET PERFORMANCE")
print("="*60)
print(f"AUC-ROC: {test_auc_roc:.4f}")
print(f"AUC-PR: {test_auc_pr:.4f} (baseline: {y_test.mean():.4f})")

# Top decile lift
def calculate_top_decile_lift(y_true, y_pred_proba):
    df_eval = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred_proba})
    df_eval['decile'] = pd.qcut(df_eval['y_pred'], 10, labels=False, duplicates='drop')
    
    top_decile = df_eval[df_eval['decile'] == df_eval['decile'].max()]
    top_rate = top_decile['y_true'].mean()
    base_rate = df_eval['y_true'].mean()
    lift = top_rate / base_rate
    
    return lift, top_rate, base_rate

lift, top_rate, base_rate = calculate_top_decile_lift(y_test, y_pred_proba)

print(f"\nTOP DECILE PERFORMANCE:")
print(f"  Baseline conversion: {base_rate*100:.2f}%")
print(f"  Top decile conversion: {top_rate*100:.2f}%")
print(f"  LIFT: {lift:.2f}x")

logger.log_metric("Test AUC-ROC", round(test_auc_roc, 4))
logger.log_metric("Test AUC-PR", round(test_auc_pr, 4))
logger.log_metric("Top Decile Lift", round(lift, 2))
logger.log_metric("Top Decile Rate", f"{top_rate*100:.2f}%")
logger.log_metric("Baseline Rate", f"{base_rate*100:.2f}%")

# Validation gate
if lift >= 1.9:
    print(f"\n✅ G5.1.1 PASSED: Top decile lift {lift:.2f}x >= 1.9x target")
    logger.log_validation_gate("G5.1.1", "Top Decile Lift >= 1.9x", True, f"{lift:.2f}x")
else:
    print(f"\n⚠️ G5.1.1 WARNING: Top decile lift {lift:.2f}x < 1.9x target")
    logger.log_validation_gate("G5.1.1", "Top Decile Lift >= 1.9x", False, f"{lift:.2f}x")

# =============================================================================
# STEP 10: FEATURE IMPORTANCE
# =============================================================================
logger.log_action("Calculating feature importance")

importance_df = pd.DataFrame({
    'feature': ALL_FEATURES,
    'importance': final_model.feature_importances_
}).sort_values('importance', ascending=False)

print(f"\nTOP 10 FEATURES:")
for i, row in importance_df.head(10).iterrows():
    marker = "🔥" if row['feature'] in ['flight_risk_score', 'pit_moves_3yr', 'firm_net_change_12mo'] else ""
    print(f"  {importance_df.index.get_loc(i)+1}. {row['feature']}: {row['importance']:.4f} {marker}")

# =============================================================================
# STEP 11: SAVE MODEL ARTIFACTS
# =============================================================================
logger.log_action("Saving model artifacts")

date_str = datetime.now().strftime('%Y%m%d')
hash_str = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
model_version = f"v3-boosted-{date_str}-{hash_str}"

model_dir = PATHS['MODELS_DIR'] / model_version
model_dir.mkdir(parents=True, exist_ok=True)

# Save model
with open(model_dir / 'model.pkl', 'wb') as f:
    pickle.dump(final_model, f)
logger.log_file_created("model.pkl", str(model_dir / 'model.pkl'), "Trained XGBoost model")

# Save hyperparameters
with open(model_dir / 'hyperparameters.json', 'w') as f:
    json.dump(best_params, f, indent=2, default=str)
logger.log_file_created("hyperparameters.json", str(model_dir / 'hyperparameters.json'), "Best hyperparameters")

# Save feature names
with open(model_dir / 'feature_names.json', 'w') as f:
    json.dump({
        'base_features': BASE_FEATURES,
        'engineered_features': ENGINEERED_FEATURES,
        'all_features': ALL_FEATURES,
        'target': TARGET
    }, f, indent=2)
logger.log_file_created("feature_names.json", str(model_dir / 'feature_names.json'), "Feature configuration")

# Save feature importance
importance_df.to_csv(model_dir / 'feature_importance.csv', index=False)
logger.log_file_created("feature_importance.csv", str(model_dir / 'feature_importance.csv'), "Feature rankings")

# Save metrics
metrics = {
    'model_version': model_version,
    'training_date': datetime.now().isoformat(),
    'train_samples': len(X_train),
    'test_samples': len(X_test),
    'n_features': len(ALL_FEATURES),
    'scale_pos_weight': scale_pos_weight,
    'cv_fix_applied': True,
    'cv_score_std': cv_std,
    'best_cv_auc_pr': study.best_value,
    'test_auc_roc': test_auc_roc,
    'test_auc_pr': test_auc_pr,
    'top_decile_lift': lift,
    'top_decile_rate': top_rate,
    'baseline_rate': base_rate,
}
with open(model_dir / 'training_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)
logger.log_file_created("training_metrics.json", str(model_dir / 'training_metrics.json'), "Performance metrics")

# Update registry
registry_path = PATHS['REGISTRY']
if registry_path.exists():
    with open(registry_path, 'r') as f:
        registry = json.load(f)
else:
    registry = {'models': []}

registry['models'].append({
    'version_id': model_version,
    'status': 'trained',
    'created_at': datetime.now().isoformat(),
    'cv_fix_applied': True,
    'metrics': metrics
})
registry['latest'] = model_version

with open(registry_path, 'w') as f:
    json.dump(registry, f, indent=2)

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "="*60)
print("PHASE 4 (FIXED) COMPLETE")
print("="*60)

print(f"\nModel: {model_version}")
print(f"CV Fix Applied: ✅ Data sorted by contacted_date")
print(f"\nPerformance:")
print(f"  Test AUC-ROC: {test_auc_roc:.4f}")
print(f"  Test AUC-PR: {test_auc_pr:.4f}")
print(f"  Top Decile Lift: {lift:.2f}x {'✅' if lift >= 1.9 else '⚠️'}")

print(f"\nComparison to Previous (Broken CV):")
print(f"  Previous Lift: 1.46x")
print(f"  New Lift: {lift:.2f}x")
print(f"  Improvement: {(lift - 1.46) / 1.46 * 100:.1f}%")

logger.log_learning(f"CV fix improved lift from 1.46x to {lift:.2f}x")
logger.end_phase(
    status="PASSED" if lift >= 1.9 else "PASSED WITH WARNINGS",
    next_steps=[
        "Phase 5: SHAP Analysis",
        "Phase 6: Probability Calibration",
        "Phase 8: Temporal Backtest"
    ]
)

print(f"\n📁 Model saved to: {model_dir}")
print(f"📝 Execution log updated: {PATHS['EXECUTION_LOG']}")
```

---

## Expected Outcome

After running with sorted data, you should see:

| Metric | Before (Broken CV) | After (Fixed CV) | Target |
|--------|-------------------|------------------|--------|
| CV Score Variation | 0 (all identical) | > 0.001 std dev | ✅ |
| Test AUC-ROC | 0.5853 | ~0.65-0.70 | > 0.60 |
| Top Decile Lift | 1.46x | ~2.0-2.5x | ≥ 1.9x |

The `flight_risk_score` showed **+657% signal** in diagnostics - once CV is working, the model should learn to use this!

---

## Key Changes from Original

1. **Added `ORDER BY contacted_date`** in BigQuery query
2. **Added explicit sort** after loading: `train_df.sort_values('contacted_date')`
3. **Added CV fold verification** - will fail if any fold has 0 positives
4. **Added CV variation check** - reports std dev of trial scores
5. **Logs the fix** in execution log for audit trail
