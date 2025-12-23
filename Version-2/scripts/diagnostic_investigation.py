"""
Diagnostic Investigation: v3 Performance Regression
Investigates why v3 model (1.46x lift) underperforms v2 model (2.62x lift)
"""

import sys
from pathlib import Path

# Add Version-2 to path
VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

import pandas as pd
import numpy as np
import json
from datetime import datetime
from google.cloud import bigquery
import xgboost as xgb
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
logger.start_phase("4-DIAG", "Diagnostic Investigation: Performance Regression")
client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("DIAGNOSTIC INVESTIGATION: v3 Performance Regression")
print("=" * 70)
print("\n⚠️  v2 Model: 2.62x lift with ~8,000 samples")
print("⚠️  v3 Model: 1.46x lift with 30,000+ samples")
print("⚠️  This is a significant regression - investigating root cause\n")

# ============================================================================
# STEP 1: Load Data and Verify Target Variable
# ============================================================================
logger.log_action("Step 1: Loading data and verifying target variable")

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
"""

print("Loading data from BigQuery...")
df = client.query(query).to_dataframe()
print(f"Loaded {len(df):,} total samples\n")

train_df = df[df['split'] == 'TRAIN'].copy()
test_df = df[df['split'] == 'TEST'].copy()

# Verify target variable
print("=" * 70)
print("STEP 1: Target Variable Verification")
print("=" * 70)
print(f"\nTraining set target distribution:")
print(train_df['target'].value_counts().sort_index())
print(f"\nTest set target distribution:")
print(test_df['target'].value_counts().sort_index())
print(f"\nUnique target values (train): {sorted(train_df['target'].unique())}")
print(f"Unique target values (test): {sorted(test_df['target'].unique())}")
print(f"\nTrain positive rate: {train_df['target'].mean()*100:.2f}%")
print(f"Test positive rate: {test_df['target'].mean()*100:.2f}%")

# Check for any anomalies
if train_df['target'].nunique() != 2:
    print(f"\n⚠️  WARNING: Target has {train_df['target'].nunique()} unique values (expected 2)")
if train_df['target'].isna().sum() > 0:
    print(f"\n⚠️  WARNING: {train_df['target'].isna().sum()} NaN values in target")

logger.log_metric("Train Target Unique Values", train_df['target'].nunique())
logger.log_metric("Train Positive Rate", f"{train_df['target'].mean()*100:.2f}%")

# ============================================================================
# STEP 2: Check CV Fold Distribution
# ============================================================================
logger.log_action("Step 2: Checking CV fold distribution")

def engineer_runtime_features(df):
    """Calculate runtime-engineered features."""
    df = df.copy()
    df['flight_risk_score'] = df['pit_moves_3yr'] * np.maximum(-df['firm_net_change_12mo'], 0)
    df['is_fresh_start'] = (df['current_firm_tenure_months'] < 12).astype(int)
    return df

train_df = engineer_runtime_features(train_df)
test_df = engineer_runtime_features(test_df)

ALL_FEATURES = [
    'industry_tenure_months', 'num_prior_firms', 'current_firm_tenure_months',
    'pit_moves_3yr', 'pit_avg_prior_tenure_months', 'pit_restlessness_ratio',
    'firm_aum_pit', 'log_firm_aum', 'firm_net_change_12mo',
    'firm_departures_12mo', 'firm_arrivals_12mo', 'firm_stability_percentile',
    'firm_stability_tier', 'is_gender_missing', 'is_linkedin_missing',
    'is_personal_email_missing', 'has_firm_aum', 'has_valid_virtual_snapshot',
    'flight_risk_score', 'is_fresh_start'
]

def prepare_features(df, features):
    """Prepare feature matrix."""
    X = df[features].copy()
    X = X.fillna(0)
    if 'firm_stability_tier' in X.columns and X['firm_stability_tier'].dtype == 'object':
        tier_map = {'Severe_Bleeding': 0, 'Moderate_Bleeding': 1, 'Slight_Bleeding': 2, 
                   'Stable': 3, 'Growing': 4}
        X['firm_stability_tier'] = X['firm_stability_tier'].map(tier_map).fillna(2)
    return X.astype(np.float32)

X_train = prepare_features(train_df, ALL_FEATURES)
y_train = train_df['target'].astype(int)

print("\n" + "=" * 70)
print("STEP 2: CV Fold Distribution Analysis")
print("=" * 70)

tscv = TimeSeriesSplit(n_splits=5)
fold_info = []

for i, (train_idx, val_idx) in enumerate(tscv.split(X_train)):
    y_train_fold = y_train.iloc[train_idx]
    y_val_fold = y_train.iloc[val_idx]
    
    train_pos_rate = y_train_fold.mean()
    val_pos_rate = y_val_fold.mean()
    
    fold_info.append({
        'fold': i+1,
        'train_size': len(train_idx),
        'val_size': len(val_idx),
        'train_pos_rate': train_pos_rate,
        'val_pos_rate': val_pos_rate,
        'train_pos_count': y_train_fold.sum(),
        'val_pos_count': y_val_fold.sum()
    })
    
    print(f"\nFold {i+1}:")
    print(f"  Train: {len(train_idx):,} samples ({train_pos_rate*100:.2f}% positive, {y_train_fold.sum():,} positives)")
    print(f"  Val:   {len(val_idx):,} samples ({val_pos_rate*100:.2f}% positive, {y_val_fold.sum():,} positives)")
    
    # CRITICAL: Check if fold has any positives
    if y_train_fold.sum() == 0:
        print(f"  ⚠️  WARNING: Fold {i+1} train set has ZERO positive examples!")
    if y_val_fold.sum() == 0:
        print(f"  ⚠️  WARNING: Fold {i+1} validation set has ZERO positive examples!")

fold_df = pd.DataFrame(fold_info)
print(f"\nFold summary:")
print(f"  Train sizes: {fold_df['train_size'].min():,} - {fold_df['train_size'].max():,}")
print(f"  Val sizes: {fold_df['val_size'].min():,} - {fold_df['val_size'].max():,}")
print(f"  Train pos rates: {fold_df['train_pos_rate'].min()*100:.2f}% - {fold_df['train_pos_rate'].max()*100:.2f}%")
print(f"  Val pos rates: {fold_df['val_pos_rate'].min()*100:.2f}% - {fold_df['val_pos_rate'].max()*100:.2f}%")

# Check if folds are too similar (would explain identical CV scores)
if fold_df['val_pos_rate'].std() < 0.001:
    print(f"\n⚠️  WARNING: Val positive rates are nearly identical (std={fold_df['val_pos_rate'].std():.6f})")
    print("   This could explain why all Optuna trials returned the same CV score")

logger.log_metric("CV Fold Pos Rate Std", round(fold_df['val_pos_rate'].std(), 6))

# ============================================================================
# STEP 3: Test Model WITHOUT Data Quality Signals
# ============================================================================
logger.log_action("Step 3: Testing model without data quality signals")

CORE_FEATURES = [f for f in ALL_FEATURES if f not in [
    'has_valid_virtual_snapshot', 
    'is_personal_email_missing',
    'is_linkedin_missing',
    'is_gender_missing',
    'has_firm_aum'
]]

print("\n" + "=" * 70)
print("STEP 3: Model WITHOUT Data Quality Signals")
print("=" * 70)
print(f"\nRemoved {len(ALL_FEATURES) - len(CORE_FEATURES)} data quality features")
print(f"Remaining features: {len(CORE_FEATURES)}")

X_train_core = prepare_features(train_df, CORE_FEATURES)
X_test_core = prepare_features(test_df, CORE_FEATURES)
y_test = test_df['target'].astype(int)

n_pos = y_train.sum()
n_neg = len(y_train) - n_pos
scale_pos_weight = n_neg / n_pos

# Quick baseline model
params_core = {
    'objective': 'binary:logistic',
    'eval_metric': 'aucpr',
    'tree_method': 'hist',
    'random_state': 42,
    'scale_pos_weight': scale_pos_weight,
    'max_depth': 5,
    'learning_rate': 0.1,
    'n_estimators': 100,
}

model_core = xgb.XGBClassifier(**params_core, verbosity=0)
model_core.fit(X_train_core, y_train, eval_set=[(X_test_core, y_test)], verbose=False)

y_pred_core = model_core.predict_proba(X_test_core)[:, 1]
test_auc_roc_core = roc_auc_score(y_test, y_pred_core)
test_auc_pr_core = average_precision_score(y_test, y_pred_core)

# Calculate lift
df_eval = pd.DataFrame({'y_true': y_test, 'y_pred': y_pred_core})
df_eval['decile'] = pd.qcut(df_eval['y_pred'], 10, labels=False, duplicates='drop')
top_decile = df_eval[df_eval['decile'] == df_eval['decile'].max()]
lift_core = (top_decile['y_true'].mean() / df_eval['y_true'].mean()) if df_eval['y_true'].mean() > 0 else 0

print(f"\nPerformance WITHOUT data quality signals:")
print(f"  Test AUC-ROC: {test_auc_roc_core:.4f}")
print(f"  Test AUC-PR: {test_auc_pr_core:.4f}")
print(f"  Top Decile Lift: {lift_core:.2f}x")

logger.log_metric("Core Model AUC-ROC", round(test_auc_roc_core, 4))
logger.log_metric("Core Model AUC-PR", round(test_auc_pr_core, 4))
logger.log_metric("Core Model Lift", round(lift_core, 2))

# ============================================================================
# STEP 4: Test Model with v2 Feature Set Only
# ============================================================================
logger.log_action("Step 4: Testing model with v2 feature set only")

# v2 features (approximate - adjust based on actual v2 feature list)
V2_FEATURES = [
    'current_firm_tenure_months',
    'pit_moves_3yr',
    'firm_net_change_12mo',
    'industry_tenure_months',
    'num_prior_firms',
    'firm_aum_pit',
    'flight_risk_score',
    'pit_restlessness_ratio',
    'is_fresh_start'
]

# Filter to features that exist
V2_FEATURES = [f for f in V2_FEATURES if f in ALL_FEATURES]

print("\n" + "=" * 70)
print("STEP 4: Model with v2 Feature Set Only")
print("=" * 70)
print(f"\nUsing {len(V2_FEATURES)} v2 features:")
for f in V2_FEATURES:
    print(f"  - {f}")

X_train_v2 = prepare_features(train_df, V2_FEATURES)
X_test_v2 = prepare_features(test_df, V2_FEATURES)

model_v2 = xgb.XGBClassifier(**params_core, verbosity=0)
model_v2.fit(X_train_v2, y_train, eval_set=[(X_test_v2, y_test)], verbose=False)

y_pred_v2 = model_v2.predict_proba(X_test_v2)[:, 1]
test_auc_roc_v2 = roc_auc_score(y_test, y_pred_v2)
test_auc_pr_v2 = average_precision_score(y_test, y_pred_v2)

df_eval_v2 = pd.DataFrame({'y_true': y_test, 'y_pred': y_pred_v2})
df_eval_v2['decile'] = pd.qcut(df_eval_v2['y_pred'], 10, labels=False, duplicates='drop')
top_decile_v2 = df_eval_v2[df_eval_v2['decile'] == df_eval_v2['decile'].max()]
lift_v2 = (top_decile_v2['y_true'].mean() / df_eval_v2['y_true'].mean()) if df_eval_v2['y_true'].mean() > 0 else 0

print(f"\nPerformance with v2 features only:")
print(f"  Test AUC-ROC: {test_auc_roc_v2:.4f}")
print(f"  Test AUC-PR: {test_auc_pr_v2:.4f}")
print(f"  Top Decile Lift: {lift_v2:.2f}x")

logger.log_metric("V2 Features AUC-ROC", round(test_auc_roc_v2, 4))
logger.log_metric("V2 Features AUC-PR", round(test_auc_pr_v2, 4))
logger.log_metric("V2 Features Lift", round(lift_v2, 2))

# ============================================================================
# STEP 5: Feature Distribution Analysis
# ============================================================================
logger.log_action("Step 5: Analyzing feature distributions by target")

print("\n" + "=" * 70)
print("STEP 5: Feature Distribution by Target")
print("=" * 70)

# Compare feature means between positive and negative cases
feature_comparison = []
for feat in ALL_FEATURES:
    if feat in train_df.columns:
        # Skip categorical columns for mean calculation
        if train_df[feat].dtype == 'object':
            # For categorical, calculate mode or distribution
            pos_mode = train_df[train_df['target'] == 1][feat].mode()[0] if len(train_df[train_df['target'] == 1][feat].mode()) > 0 else 'N/A'
            neg_mode = train_df[train_df['target'] == 0][feat].mode()[0] if len(train_df[train_df['target'] == 0][feat].mode()) > 0 else 'N/A'
            feature_comparison.append({
                'feature': feat,
                'pos_mode': pos_mode,
                'neg_mode': neg_mode,
                'difference': 'N/A (categorical)',
                'pct_difference': 'N/A'
            })
        else:
            pos_mean = train_df[train_df['target'] == 1][feat].mean()
            neg_mean = train_df[train_df['target'] == 0][feat].mean()
            diff = pos_mean - neg_mean
            pct_diff = (diff / neg_mean * 100) if neg_mean != 0 else 0
            
            feature_comparison.append({
                'feature': feat,
                'pos_mean': pos_mean,
                'neg_mean': neg_mean,
                'difference': diff,
                'pct_difference': pct_diff
            })

comp_df = pd.DataFrame(feature_comparison)
# Sort numeric features by absolute difference
numeric_df = comp_df[comp_df['difference'] != 'N/A (categorical)'].copy()
if len(numeric_df) > 0:
    numeric_df['abs_pct_diff'] = numeric_df['pct_difference'].abs()
    numeric_df = numeric_df.sort_values('abs_pct_diff', ascending=False)

print("\nTop 10 numeric features by absolute difference (positive vs negative):")
if len(numeric_df) > 0:
    print(numeric_df.head(10)[['feature', 'pos_mean', 'neg_mean', 'difference', 'pct_difference']].to_string(index=False))
else:
    print("No numeric features to compare")

# Check protected features
print("\nProtected Features Analysis:")
for feat in ['pit_moves_3yr', 'firm_net_change_12mo', 'flight_risk_score']:
    if feat in comp_df['feature'].values:
        row = comp_df[comp_df['feature'] == feat].iloc[0]
        print(f"  {feat}:")
        print(f"    Positive mean: {row['pos_mean']:.4f}")
        print(f"    Negative mean: {row['neg_mean']:.4f}")
        print(f"    Difference: {row['difference']:.4f} ({row['pct_difference']:+.1f}%)")

# ============================================================================
# STEP 6: Check for Temporal Leakage
# ============================================================================
logger.log_action("Step 6: Checking for temporal patterns in data quality signals")

print("\n" + "=" * 70)
print("STEP 6: Temporal Pattern Analysis")
print("=" * 70)

# Check if data quality signals correlate with time period
train_df['year_month'] = pd.to_datetime(train_df['contacted_date']).dt.to_period('M')

print("\nData quality signal rates by month:")
quality_by_month = train_df.groupby('year_month').agg({
    'has_valid_virtual_snapshot': 'mean',
    'is_personal_email_missing': 'mean',
    'is_linkedin_missing': 'mean',
    'target': 'mean'
}).round(3)

print(quality_by_month)

# Check correlation between data quality and time
if len(train_df['year_month'].unique()) > 1:
    train_df['month_num'] = pd.to_datetime(train_df['contacted_date']).dt.month
    corr_time = train_df[['has_valid_virtual_snapshot', 'is_personal_email_missing', 
                         'is_linkedin_missing', 'month_num']].corr()
    print("\nCorrelation with month number:")
    print(corr_time['month_num'].sort_values(key=abs, ascending=False))

# ============================================================================
# STEP 7: Summary and Recommendations
# ============================================================================
print("\n" + "=" * 70)
print("DIAGNOSTIC SUMMARY")
print("=" * 70)

print("\n📊 Performance Comparison:")
print(f"  Full model (with data quality): 1.46x lift")
print(f"  Core model (no data quality):  {lift_core:.2f}x lift")
print(f"  V2 features only:               {lift_v2:.2f}x lift")
print(f"  Target (v2 performance):       2.62x lift")

print("\n🔍 Key Findings:")
if lift_core > 1.46:
    print(f"  ✅ Removing data quality signals improves lift to {lift_core:.2f}x")
else:
    print(f"  ⚠️  Removing data quality signals doesn't help (lift: {lift_core:.2f}x)")

if lift_v2 > 1.46:
    print(f"  ✅ V2 features perform better: {lift_v2:.2f}x vs 1.46x")
else:
    print(f"  ⚠️  V2 features don't improve performance (lift: {lift_v2:.2f}x)")

if fold_df['val_pos_rate'].std() < 0.001:
    print(f"  ⚠️  CV folds have nearly identical positive rates (std={fold_df['val_pos_rate'].std():.6f})")
    print("      This explains why all Optuna trials returned identical scores")

print("\n💡 Recommendations:")
if lift_core > 1.46:
    print("  1. Remove data quality signals from feature set")
if lift_v2 > 1.46:
    print("  2. Consider using v2 feature set or investigate why new features hurt")
if fold_df['val_pos_rate'].std() < 0.001:
    print("  3. Fix CV implementation - folds are too similar")
print("  4. Investigate why 2025 data performs differently than 2024 data")
print("  5. Check if target variable definition changed between v2 and v3")

# Save diagnostic report
report = {
    'diagnostic_date': datetime.now().isoformat(),
    'target_verification': {
        'train_unique_values': int(train_df['target'].nunique()),
        'train_positive_rate': float(train_df['target'].mean()),
        'test_positive_rate': float(test_df['target'].mean())
    },
    'cv_analysis': {
        'fold_positive_rate_std': float(fold_df['val_pos_rate'].std()),
        'fold_info': fold_info
    },
    'model_comparison': {
        'full_model_lift': 1.46,
        'core_model_lift': float(lift_core),
        'v2_features_lift': float(lift_v2),
        'target_v2_lift': 2.62
    },
    'feature_analysis': comp_df.to_dict('records')
}

report_path = PATHS['REPORTS_DIR'] / 'diagnostic_investigation.json'
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, default=str)

logger.log_file_created("diagnostic_investigation.json", str(report_path), "Diagnostic investigation results")
logger.log_learning(f"Core model (no data quality) lift: {lift_core:.2f}x")
logger.log_learning(f"V2 features only lift: {lift_v2:.2f}x")
logger.log_learning(f"CV fold positive rate std: {fold_df['val_pos_rate'].std():.6f}")

logger.end_phase(
    status="PASSED",
    next_steps=[
        "Review diagnostic findings",
        "Decide on feature set adjustments",
        "Fix CV implementation if needed",
        "Retrain model with optimal feature set"
    ]
)

print(f"\n✅ Diagnostic report saved: {report_path}")
print(f"📝 Execution log updated: {PATHS['EXECUTION_LOG']}")

