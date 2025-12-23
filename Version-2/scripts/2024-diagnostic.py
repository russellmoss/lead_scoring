# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\2024-diagnostic-fixed.py

import sys
from pathlib import Path
VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

import pandas as pd
import numpy as np
from google.cloud import bigquery
import xgboost as xgb
from sklearn.metrics import roc_auc_score, average_precision_score
import warnings
warnings.filterwarnings('ignore')

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("DIAGNOSTIC: 2024-ONLY vs DATA QUALITY REMOVAL")
print("=" * 70)

# =============================================================================
# FIRST: CHECK WHAT COLUMNS EXIST
# =============================================================================
print("\nChecking available columns...")

query_columns = """
SELECT column_name
FROM `savvy-gtm-analytics.ml_features.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'lead_scoring_splits_v2'
"""

columns_df = client.query(query_columns).result().to_dataframe()
print(f"Available columns: {columns_df['column_name'].tolist()[:20]}...")  # First 20

# Check for split_set or similar
split_cols = [c for c in columns_df['column_name'] if 'split' in c.lower() or 'set' in c.lower()]
print(f"Split-related columns: {split_cols}")

# =============================================================================
# LOAD DATA
# =============================================================================
query = """
SELECT *
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2`
ORDER BY contacted_date
"""

df = client.query(query).result().to_dataframe()
print(f"\nTotal data: {len(df):,} leads")
print(f"Columns: {df.columns.tolist()}")

# Find the split column (might be named differently)
potential_split_cols = ['split_set', 'split', 'dataset', 'data_split']
split_col = None
for col in potential_split_cols:
    if col in df.columns:
        split_col = col
        break

if split_col is None:
    # Maybe we need to derive it from dates
    print("\nNo split column found. Deriving from dates...")
    # Use the same logic as v2: train = before Nov 2024, test = Nov 2024
    df['contacted_date'] = pd.to_datetime(df['contacted_date'])
    df['split_set'] = np.where(df['contacted_date'] < '2024-11-01', 'TRAIN', 'TEST')
    split_col = 'split_set'
else:
    print(f"\nUsing split column: {split_col}")

# Add year
df['year'] = pd.to_datetime(df['contacted_date']).dt.year

# Check year distribution
print(f"\nYear distribution:")
print(df.groupby(['year', split_col]).agg({'target': ['count', 'mean']}).round(4))

# =============================================================================
# DEFINE FEATURE SETS
# =============================================================================

# Data quality features (potential leakage)
DATA_QUALITY_FEATURES = [
    'has_valid_virtual_snapshot',
    'is_personal_email_missing',
    'has_firm_aum',
]

# Check which features exist
available_features = df.columns.tolist()

# Core features (without data quality)
CORE_FEATURES_CANDIDATES = [
    'industry_tenure_months',
    'num_prior_firms',
    'current_firm_tenure_months',
    'pit_moves_3yr',
    'pit_avg_prior_tenure_months',
    'pit_restlessness_ratio',
    'pit_mobility_tier_Stable',
    'pit_mobility_tier_Mobile',
    'pit_mobility_tier_Highly_Mobile',
    'firm_aum_pit',
    'log_firm_aum',
    'firm_net_change_12mo',
    'firm_departures_12mo',
    'firm_arrivals_12mo',
    'firm_stability_percentile',
    'has_prior_moves',
    'is_bleeding_firm',
    'is_flight_risk',
    'flight_risk_tier',
]

CORE_FEATURES = [f for f in CORE_FEATURES_CANDIDATES if f in available_features]
DATA_QUALITY_FEATURES = [f for f in DATA_QUALITY_FEATURES if f in available_features]

print(f"\nCore features available: {len(CORE_FEATURES)}")
print(f"Data quality features available: {len(DATA_QUALITY_FEATURES)}")

# Runtime features
RUNTIME_FEATURES = ['flight_risk_score', 'is_fresh_start']

TARGET = 'target'

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def engineer_runtime_features(df):
    df = df.copy()
    df['flight_risk_score'] = df['pit_moves_3yr'] * np.maximum(-df['firm_net_change_12mo'], 0)
    df['is_fresh_start'] = (df['current_firm_tenure_months'] < 12).astype(int)
    return df

def prepare_features(df, features):
    # Only use features that exist
    existing = [f for f in features if f in df.columns]
    X = df[existing].copy().fillna(0).astype(np.float32)
    return X

def calculate_lift(y_true, y_pred):
    df_eval = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred})
    df_eval['decile'] = pd.qcut(df_eval['y_pred'].rank(method='first'), 10, labels=False)
    top_decile = df_eval[df_eval['decile'] == 9]
    return top_decile['y_true'].mean() / df_eval['y_true'].mean()

def train_and_evaluate(X_train, y_train, X_test, y_test, name):
    """Train XGBoost and evaluate."""
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_pos_weight = n_neg / n_pos
    
    # Quick training (no tuning)
    model = xgb.XGBClassifier(
        objective='binary:logistic',
        eval_metric='aucpr',
        tree_method='hist',
        random_state=42,
        scale_pos_weight=scale_pos_weight,
        max_depth=6,
        learning_rate=0.1,
        n_estimators=100,
        subsample=0.8,
        colsample_bytree=0.8,
        verbosity=0
    )
    
    model.fit(X_train, y_train)
    y_pred = model.predict_proba(X_test)[:, 1]
    
    auc_roc = roc_auc_score(y_test, y_pred)
    auc_pr = average_precision_score(y_test, y_pred)
    lift = calculate_lift(y_test, y_pred)
    
    print(f"\n{name}:")
    print(f"  Train: {len(X_train):,} ({y_train.mean()*100:.2f}% pos)")
    print(f"  Test: {len(X_test):,} ({y_test.mean()*100:.2f}% pos)")
    print(f"  AUC-ROC: {auc_roc:.4f}")
    print(f"  AUC-PR: {auc_pr:.4f}")
    print(f"  Top Decile Lift: {lift:.2f}x")
    
    return {'name': name, 'auc_roc': auc_roc, 'auc_pr': auc_pr, 'lift': lift, 'model': model}

# =============================================================================
# PREPARE DATA
# =============================================================================

df = engineer_runtime_features(df)
features_with_runtime = CORE_FEATURES + DATA_QUALITY_FEATURES + RUNTIME_FEATURES
features_no_dq = CORE_FEATURES + RUNTIME_FEATURES

print(f"\nFeatures with DQ: {len(features_with_runtime)}")
print(f"Features without DQ: {len(features_no_dq)}")

# =============================================================================
# TEST 1: 2024 DATA ONLY (Like V2)
# =============================================================================
print("\n" + "=" * 70)
print("TEST 1: 2024 DATA ONLY (Replicating V2 Setup)")
print("=" * 70)

# Filter to 2024 only
df_2024 = df[df['year'] == 2024].copy()

# Split: Use same temporal split as v2 (before Nov = train, Nov = test)
train_2024 = df_2024[pd.to_datetime(df_2024['contacted_date']) < '2024-11-01'].sort_values('contacted_date')
test_2024 = df_2024[pd.to_datetime(df_2024['contacted_date']) >= '2024-11-01'].sort_values('contacted_date')

print(f"\n2024 Data:")
print(f"  Train: {len(train_2024):,} leads (before Nov 2024)")
print(f"  Test: {len(test_2024):,} leads (Nov 2024)")
print(f"  Train positive rate: {train_2024['target'].mean()*100:.2f}%")
print(f"  Test positive rate: {test_2024['target'].mean()*100:.2f}%")

if len(test_2024) > 0 and test_2024['target'].sum() > 0:
    X_train_2024 = prepare_features(train_2024, features_with_runtime)
    y_train_2024 = train_2024[TARGET].astype(int)
    X_test_2024 = prepare_features(test_2024, features_with_runtime)
    y_test_2024 = test_2024[TARGET].astype(int)
    
    result_2024 = train_and_evaluate(X_train_2024, y_train_2024, X_test_2024, y_test_2024, "2024 Only (All Features)")
else:
    print("⚠️ Not enough 2024 test data")
    result_2024 = None

# =============================================================================
# TEST 2: 2024 DATA WITHOUT DATA QUALITY FEATURES
# =============================================================================
print("\n" + "=" * 70)
print("TEST 2: 2024 DATA WITHOUT DATA QUALITY FEATURES")
print("=" * 70)

if result_2024 is not None:
    X_train_2024_nodq = prepare_features(train_2024, features_no_dq)
    X_test_2024_nodq = prepare_features(test_2024, features_no_dq)
    
    result_2024_nodq = train_and_evaluate(X_train_2024_nodq, y_train_2024, X_test_2024_nodq, y_test_2024, "2024 Only (No Data Quality)")
else:
    result_2024_nodq = None

# =============================================================================
# TEST 3: FULL DATA WITHOUT DATA QUALITY FEATURES
# =============================================================================
print("\n" + "=" * 70)
print("TEST 3: FULL DATA (2024+2025) WITHOUT DATA QUALITY FEATURES")
print("=" * 70)

# Use the existing split from the table
train_full = df[df[split_col] == 'TRAIN'].sort_values('contacted_date')
test_full = df[df[split_col] == 'TEST'].sort_values('contacted_date')

X_train_full_nodq = prepare_features(train_full, features_no_dq)
y_train_full = train_full[TARGET].astype(int)
X_test_full_nodq = prepare_features(test_full, features_no_dq)
y_test_full = test_full[TARGET].astype(int)

result_full_nodq = train_and_evaluate(X_train_full_nodq, y_train_full, X_test_full_nodq, y_test_full, "Full Data (No Data Quality)")

# =============================================================================
# TEST 4: FULL DATA WITH ALL FEATURES (BASELINE)
# =============================================================================
print("\n" + "=" * 70)
print("TEST 4: FULL DATA WITH ALL FEATURES (BASELINE)")
print("=" * 70)

X_train_full = prepare_features(train_full, features_with_runtime)
X_test_full = prepare_features(test_full, features_with_runtime)

result_full = train_and_evaluate(X_train_full, y_train_full, X_test_full, y_test_full, "Full Data (All Features)")

# =============================================================================
# TEST 5: INVESTIGATE DATA QUALITY FEATURE LEAKAGE
# =============================================================================
print("\n" + "=" * 70)
print("TEST 5: DATA QUALITY FEATURE ANALYSIS")
print("=" * 70)

if len(DATA_QUALITY_FEATURES) > 0:
    print("\nData Quality Feature Distribution by Target (Test Set):")
    for feat in DATA_QUALITY_FEATURES:
        if feat in test_full.columns:
            pos_mean = test_full[test_full['target'] == 1][feat].mean()
            neg_mean = test_full[test_full['target'] == 0][feat].mean()
            diff_pct = (pos_mean - neg_mean) / max(neg_mean, 0.001) * 100
            print(f"  {feat}:")
            print(f"    Positive: {pos_mean:.3f}")
            print(f"    Negative: {neg_mean:.3f}")
            print(f"    Difference: {diff_pct:+.1f}%")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("SUMMARY: COMPARISON OF ALL TESTS")
print("=" * 70)

results = [r for r in [result_2024, result_2024_nodq, result_full_nodq, result_full] if r is not None]

print(f"\n{'Test':<40} {'AUC-ROC':<10} {'AUC-PR':<10} {'Lift':<10}")
print("-" * 70)
for r in results:
    print(f"{r['name']:<40} {r['auc_roc']:.4f}     {r['auc_pr']:.4f}     {r['lift']:.2f}x")

print("\n" + "=" * 70)
print("KEY FINDINGS")
print("=" * 70)

# Best result
if results:
    best = max(results, key=lambda x: x['lift'])
    print(f"\n🏆 Best Configuration: {best['name']}")
    print(f"   Lift: {best['lift']:.2f}x")
    print(f"   AUC-ROC: {best['auc_roc']:.4f}")

    # Compare 2024 vs full
    if result_2024 and result_full:
        if result_2024['lift'] > result_full['lift'] + 0.1:
            print(f"\n✅ 2024 data performs BETTER: {result_2024['lift']:.2f}x vs {result_full['lift']:.2f}x")
            print("   → Consider training on 2024 data only")
        else:
            print(f"\n⚠️ 2024 and full data perform similarly")

    # Compare with/without DQ
    if result_2024 and result_2024_nodq:
        if result_2024_nodq['lift'] > result_2024['lift'] + 0.1:
            print(f"\n✅ Removing DQ features IMPROVES: {result_2024_nodq['lift']:.2f}x vs {result_2024['lift']:.2f}x")
        elif result_2024['lift'] > result_2024_nodq['lift'] + 0.1:
            print(f"\n⚠️ Removing DQ features HURTS: {result_2024_nodq['lift']:.2f}x vs {result_2024['lift']:.2f}x")
            print("   → DQ features provide real signal, not leakage")
        else:
            print(f"\n⚠️ DQ features have minimal impact")

print("\n" + "=" * 70)