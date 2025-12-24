"""Analyze V4 model as a deprioritization filter."""

import sys
import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")

def prepare_features(df, feature_list):
    """Prepare features for XGBoost (handle categoricals)."""
    X = df[feature_list].copy()
    
    # Identify categorical features
    categorical_features = []
    for feat in feature_list:
        if df[feat].dtype == 'object' or df[feat].dtype.name == 'category':
            categorical_features.append(feat)
    
    # Convert categoricals to codes
    for feat in categorical_features:
        if feat in X.columns:
            X[feat] = X[feat].astype('category').cat.codes
    
    # Fill NaN
    X = X.fillna(0)
    
    return X

# Load test data
test = pd.read_csv(BASE_DIR / 'data' / 'splits' / 'test.csv')

# Load model
with open(BASE_DIR / 'models' / 'v4.0.0' / 'model.pkl', 'rb') as f:
    model = pickle.load(f)

# Get features
with open(BASE_DIR / 'data' / 'processed' / 'final_features.json', 'r') as f:
    features = json.load(f)['final_features']

# Prepare features and get predictions
X_test = prepare_features(test, features)
import xgboost as xgb
dtest = xgb.DMatrix(X_test)
test['v4_score'] = model.predict(dtest)

# Bottom 20% by V4 score
bottom_20_pct = int(len(test) * 0.2)
bottom_20 = test.nsmallest(bottom_20_pct, 'v4_score')

# Top 80% by V4 score
top_80_pct = int(len(test) * 0.8)
top_80 = test.nlargest(top_80_pct, 'v4_score')

print("=" * 70)
print("V4 AS DEPRIORITIZATION FILTER")
print("=" * 70)

baseline_conv_rate = test['target'].mean()

print(f"\nOverall Test Set:")
print(f"  Leads: {len(test):,}")
print(f"  Conversions: {test['target'].sum():,}")
print(f"  Conv Rate: {baseline_conv_rate*100:.2f}%")

print(f"\nBottom 20% by V4 score (DEPRIORITIZE):")
print(f"  Leads: {len(bottom_20):,}")
print(f"  Conversions: {bottom_20['target'].sum():,}")
print(f"  Conv Rate: {bottom_20['target'].mean()*100:.2f}%")
print(f"  Lift: {bottom_20['target'].mean() / baseline_conv_rate:.2f}x")

print(f"\nTop 80% by V4 score (PRIORITIZE):")
print(f"  Leads: {len(top_80):,}")
print(f"  Conversions: {top_80['target'].sum():,}")
print(f"  Conv Rate: {top_80['target'].mean()*100:.2f}%")
print(f"  Lift: {top_80['target'].mean() / baseline_conv_rate:.2f}x")

# Calculate efficiency gain
print(f"\n" + "=" * 70)
print("EFFICIENCY ANALYSIS")
print("=" * 70)

# If we skip bottom 20%, how many conversions do we lose?
conversions_lost = bottom_20['target'].sum()
conversions_kept = top_80['target'].sum()
total_conversions = test['target'].sum()

print(f"\nIf we SKIP bottom 20%:")
print(f"  Conversions Lost: {conversions_lost} ({conversions_lost/total_conversions*100:.1f}% of total)")
print(f"  Conversions Kept: {conversions_kept} ({conversions_kept/total_conversions*100:.1f}% of total)")
print(f"  Leads Skipped: {len(bottom_20):,} ({len(bottom_20)/len(test)*100:.1f}% of total)")
print(f"  Efficiency Gain: Focus on {len(top_80):,} leads instead of {len(test):,}")

# Calculate by deciles for more granular analysis
print(f"\n" + "=" * 70)
print("DECILE ANALYSIS (Bottom vs Top)")
print("=" * 70)

test_sorted = test.sort_values('v4_score', ascending=False).reset_index(drop=True)
decile_size = len(test_sorted) // 10

print(f"\n{'Decile':<10} {'Leads':<10} {'Conv':<10} {'Conv Rate':<12} {'Lift':<10}")
print("-" * 70)

for i in range(10):
    start_idx = i * decile_size
    end_idx = (i + 1) * decile_size if i < 9 else len(test_sorted)
    decile_data = test_sorted.iloc[start_idx:end_idx]
    
    decile_num = 10 - i  # Reverse so decile 10 = top
    conv_rate = decile_data['target'].mean() * 100
    lift = decile_data['target'].mean() / baseline_conv_rate
    
    print(f"{decile_num:<10} {len(decile_data):<10} {decile_data['target'].sum():<10} {conv_rate:>10.2f}% {lift:>9.2f}x")

# Bottom 3 deciles combined
bottom_3_deciles = test_sorted.tail(decile_size * 3)
print(f"\nBottom 3 Deciles Combined (30% of leads):")
print(f"  Leads: {len(bottom_3_deciles):,}")
print(f"  Conversions: {bottom_3_deciles['target'].sum():,}")
print(f"  Conv Rate: {bottom_3_deciles['target'].mean()*100:.2f}%")
print(f"  Lift: {bottom_3_deciles['target'].mean() / baseline_conv_rate:.2f}x")

print("\n" + "=" * 70)
if bottom_20['target'].mean() < 0.01:  # Less than 1% conversion
    print("[SUCCESS] V4 IS VALUABLE AS DEPRIORITIZATION FILTER")
    print(f"   Bottom 20% converts at {bottom_20['target'].mean()*100:.2f}% - safe to skip")
else:
    print("[INFO] V4 deprioritization value:")
    print(f"   Bottom 20% converts at {bottom_20['target'].mean()*100:.2f}% (vs {baseline_conv_rate*100:.2f}% baseline)")
    if bottom_20['target'].mean() < baseline_conv_rate * 0.6:  # At least 40% reduction
        print("   [VALUABLE] Bottom 20% has significantly lower conversion - safe to deprioritize")
    else:
        print("   [LIMITED] Bottom 20% still has meaningful conversion")
print("=" * 70)

