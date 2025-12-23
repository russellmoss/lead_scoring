# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\deep_diagnostic.py

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from google.cloud import bigquery
import json

VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("DEEP DIAGNOSTIC: TARGET VARIABLE & FEATURE ANALYSIS")
print("=" * 70)

# =============================================================================
# DIAGNOSTIC 1: TARGET VARIABLE DEFINITION
# =============================================================================
print("\n" + "=" * 70)
print("DIAGNOSTIC 1: TARGET VARIABLE DEFINITION")
print("=" * 70)

# Check how target is defined in v3
query_v3_target = """
-- How is the target defined in lead_scoring_splits?
SELECT 
    split,
    COUNT(*) as total,
    SUM(CASE WHEN target = 1 THEN 1 ELSE 0 END) as positives,
    ROUND(AVG(CASE WHEN target = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) as positive_rate
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
GROUP BY split
"""

print("\nV3 Target Distribution:")
df_v3 = client.query(query_v3_target).to_dataframe()
print(df_v3.to_string(index=False))

# Check the raw Lead table to understand MQL definition
query_mql_check = """
-- Check MQL stages and conversion patterns
SELECT 
    Status,
    COUNT(*) as count,
    COUNT(DISTINCT Id) as unique_leads
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE stage_entered_contacting__c IS NOT NULL
GROUP BY Status
ORDER BY count DESC
LIMIT 20
"""

print("\n\nLead Status Distribution (Contacted Leads):")
df_status = client.query(query_mql_check).to_dataframe()
print(df_status.to_string(index=False))

# Check v2's target definition from the original feature table if it exists
query_v2_compare = """
-- Compare with original v2 feature table if it exists
SELECT 
    'v2_features' as source,
    COUNT(*) as total,
    SUM(CASE WHEN converted_to_mql = 1 THEN 1 ELSE 0 END) as positives,
    ROUND(AVG(CASE WHEN converted_to_mql = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) as positive_rate
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features`
WHERE contacted_date BETWEEN '2024-02-01' AND '2024-11-30'

UNION ALL

SELECT 
    'v3_splits_same_period' as source,
    COUNT(*) as total,
    SUM(CASE WHEN target = 1 THEN 1 ELSE 0 END) as positives,
    ROUND(AVG(CASE WHEN target = 1 THEN 1.0 ELSE 0.0 END) * 100, 2) as positive_rate
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
WHERE contacted_date BETWEEN '2024-02-01' AND '2024-11-30'
"""

print("\n\nV2 vs V3 Target Comparison (Same Date Range):")
try:
    df_compare = client.query(query_v2_compare).to_dataframe()
    print(df_compare.to_string(index=False))
    
    # Check if positive rates match
    v2_rate = df_compare[df_compare['source'] == 'v2_features']['positive_rate'].values
    v3_rate = df_compare[df_compare['source'] == 'v3_splits_same_period']['positive_rate'].values
    
    if len(v2_rate) > 0 and len(v3_rate) > 0:
        if abs(v2_rate[0] - v3_rate[0]) > 0.5:
            print(f"\n⚠️ WARNING: Target rates differ! v2={v2_rate[0]}%, v3={v3_rate[0]}%")
            print("   This could indicate different target definitions!")
        else:
            print(f"\n✅ Target rates similar: v2={v2_rate[0]}%, v3={v3_rate[0]}%")
except Exception as e:
    print(f"Could not compare with v2 table: {e}")

# =============================================================================
# DIAGNOSTIC 2: FLIGHT_RISK_SCORE DISTRIBUTION
# =============================================================================
print("\n" + "=" * 70)
print("DIAGNOSTIC 2: FLIGHT_RISK_SCORE DISTRIBUTION")
print("=" * 70)

# Load the splits data with features
query_data = """
SELECT 
    s.split,
    s.target,
    s.contacted_date,
    f.pit_moves_3yr,
    f.firm_net_change_12mo,
    f.num_prior_firms,
    f.current_firm_tenure_months
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits` s
INNER JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
    ON s.lead_id = f.lead_id
"""

df = client.query(query_data).to_dataframe()

# Calculate flight_risk_score
df['flight_risk_score'] = df['pit_moves_3yr'] * np.maximum(-df['firm_net_change_12mo'], 0)

print(f"\nTotal leads: {len(df):,}")

# Sparsity analysis
zero_frs = (df['flight_risk_score'] == 0).sum()
nonzero_frs = (df['flight_risk_score'] > 0).sum()

print(f"\nflight_risk_score Sparsity:")
print(f"  Zero values: {zero_frs:,} ({zero_frs/len(df)*100:.1f}%)")
print(f"  Non-zero values: {nonzero_frs:,} ({nonzero_frs/len(df)*100:.1f}%)")

# Why is it zero?
zero_moves = (df['pit_moves_3yr'] == 0).sum()
positive_change = (df['firm_net_change_12mo'] >= 0).sum()

print(f"\nWhy flight_risk_score = 0:")
print(f"  pit_moves_3yr = 0: {zero_moves:,} ({zero_moves/len(df)*100:.1f}%)")
print(f"  firm_net_change_12mo >= 0: {positive_change:,} ({positive_change/len(df)*100:.1f}%)")

# Signal by flight_risk_score buckets
df['frs_bucket'] = pd.cut(df['flight_risk_score'], 
                          bins=[-0.001, 0, 10, 50, 100, float('inf')],
                          labels=['Zero', '1-10', '11-50', '51-100', '>100'])

print(f"\nConversion Rate by flight_risk_score Bucket:")
bucket_analysis = df.groupby('frs_bucket').agg({
    'target': ['count', 'sum', 'mean']
}).round(4)
bucket_analysis.columns = ['count', 'positives', 'conversion_rate']
bucket_analysis['pct_of_total'] = (bucket_analysis['count'] / len(df) * 100).round(1)
print(bucket_analysis.to_string())

# Compare positives vs negatives
print(f"\nflight_risk_score by Target Class:")
for target_val in [0, 1]:
    subset = df[df['target'] == target_val]
    zero_pct = (subset['flight_risk_score'] == 0).mean() * 100
    mean_frs = subset['flight_risk_score'].mean()
    print(f"  Target={target_val}: {zero_pct:.1f}% are zero, mean={mean_frs:.2f}")

# =============================================================================
# DIAGNOSTIC 3: TIME PERIOD PERFORMANCE
# =============================================================================
print("\n" + "=" * 70)
print("DIAGNOSTIC 3: TIME PERIOD PERFORMANCE")
print("=" * 70)

df['year'] = pd.to_datetime(df['contacted_date']).dt.year
df['quarter'] = pd.to_datetime(df['contacted_date']).dt.quarter
df['year_quarter'] = df['year'].astype(str) + '-Q' + df['quarter'].astype(str)

# Conversion rate by time period
print(f"\nConversion Rate by Year-Quarter:")
time_analysis = df.groupby('year_quarter').agg({
    'target': ['count', 'sum', 'mean']
}).round(4)
time_analysis.columns = ['count', 'positives', 'conversion_rate']
time_analysis = time_analysis.sort_index()
print(time_analysis.to_string())

# Feature signals by year
print(f"\nKey Feature Signals by Year:")
for year in sorted(df['year'].unique()):
    subset = df[df['year'] == year]
    pos = subset[subset['target'] == 1]
    neg = subset[subset['target'] == 0]
    
    frs_diff = pos['flight_risk_score'].mean() - neg['flight_risk_score'].mean()
    moves_diff = pos['pit_moves_3yr'].mean() - neg['pit_moves_3yr'].mean()
    change_diff = pos['firm_net_change_12mo'].mean() - neg['firm_net_change_12mo'].mean()
    
    print(f"\n  {year}:")
    print(f"    Leads: {len(subset):,}, Positive rate: {subset['target'].mean()*100:.2f}%")
    print(f"    flight_risk_score signal: {frs_diff:+.2f}")
    print(f"    pit_moves_3yr signal: {moves_diff:+.2f}")
    print(f"    firm_net_change_12mo signal: {change_diff:+.2f}")

# =============================================================================
# DIAGNOSTIC 4: TRAIN A SIMPLE MODEL ON JUST FLIGHT_RISK_SCORE
# =============================================================================
print("\n" + "=" * 70)
print("DIAGNOSTIC 4: SINGLE FEATURE MODEL TEST")
print("=" * 70)

from sklearn.metrics import roc_auc_score, average_precision_score

# Split data
train_df = df[df['split'] == 'TRAIN'].copy()
test_df = df[df['split'] == 'TEST'].copy()

# Sort by date
train_df = train_df.sort_values('contacted_date').reset_index(drop=True)
test_df = test_df.sort_values('contacted_date').reset_index(drop=True)

# Test: What if we just used flight_risk_score as the prediction?
# (Higher score = more likely to convert)
y_test = test_df['target']
y_pred_frs = test_df['flight_risk_score']

# Calculate metrics using just flight_risk_score as the score
frs_auc_roc = roc_auc_score(y_test, y_pred_frs)
frs_auc_pr = average_precision_score(y_test, y_pred_frs)

print(f"\nUsing ONLY flight_risk_score as predictor:")
print(f"  AUC-ROC: {frs_auc_roc:.4f}")
print(f"  AUC-PR: {frs_auc_pr:.4f}")

# Calculate lift using just flight_risk_score
test_df['frs_decile'] = pd.qcut(test_df['flight_risk_score'].rank(method='first'), 
                                 10, labels=False, duplicates='drop')
top_decile_frs = test_df[test_df['frs_decile'] == test_df['frs_decile'].max()]
frs_lift = top_decile_frs['target'].mean() / y_test.mean() if y_test.mean() > 0 else 0

print(f"  Top Decile Lift: {frs_lift:.2f}x")

# Compare with other single features
print(f"\nSingle Feature AUC-ROC Comparison:")
single_features = ['pit_moves_3yr', 'firm_net_change_12mo', 'flight_risk_score',
                   'num_prior_firms', 'current_firm_tenure_months']

for feat in single_features:
    if feat in test_df.columns:
        # Handle the direction (some features should be negated)
        feat_values = test_df[feat].fillna(0)
        if feat == 'firm_net_change_12mo':
            feat_values = -feat_values  # Lower (more negative) = better
        
        try:
            auc = roc_auc_score(y_test, feat_values)
            print(f"  {feat}: {auc:.4f}")
        except:
            print(f"  {feat}: Could not calculate")

# =============================================================================
# DIAGNOSTIC 5: CHECK V2 FEATURE SET
# =============================================================================
print("\n" + "=" * 70)
print("DIAGNOSTIC 5: V2 FEATURE SET COMPARISON")
print("=" * 70)

# V2 used these 11 base features (from documentation)
V2_BASE_FEATURES = [
    'aum_growth_since_jan2024_pct',
    'current_firm_tenure_months',
    'firm_aum_pit',
    'firm_net_change_12mo',
    'firm_rep_count_at_contact',
    'industry_tenure_months',
    'num_prior_firms',
    'pit_mobility_tier_Highly Mobile',
    'pit_mobility_tier_Mobile',
    'pit_mobility_tier_Stable',
    'pit_moves_3yr'
]

# V2 engineered features
V2_ENGINEERED = [
    'flight_risk_score',
    'pit_restlessness_ratio',
    'is_fresh_start'
]

# Check which v2 features are in v3
query_v3_columns = """
SELECT column_name
FROM `savvy-gtm-analytics.ml_features.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'lead_scoring_features_pit'
"""

v3_columns = client.query(query_v3_columns).to_dataframe()['column_name'].tolist()

print("\nV2 Base Features - Presence in V3:")
for feat in V2_BASE_FEATURES:
    status = "✅" if feat in v3_columns else "❌ MISSING"
    print(f"  {feat}: {status}")

print("\nV2 Engineered Features - Calculated at Runtime:")
for feat in V2_ENGINEERED:
    print(f"  {feat}: (calculated)")

# Check for pit_mobility_tier columns
mobility_cols = [c for c in v3_columns if 'mobility' in c.lower()]
print(f"\nMobility-related columns in v3: {mobility_cols}")

# =============================================================================
# SUMMARY & RECOMMENDATIONS
# =============================================================================
print("\n" + "=" * 70)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 70)

findings = {
    'flight_risk_score_sparsity': f"{zero_frs/len(df)*100:.1f}% zero",
    'frs_auc_roc': float(frs_auc_roc),
    'frs_lift': float(frs_lift),
    'zero_moves_pct': float(zero_moves/len(df)*100),
    'positive_change_pct': float(positive_change/len(df)*100),
}

print(f"""
Key Findings:
1. flight_risk_score Sparsity: {findings['flight_risk_score_sparsity']}
   - {zero_moves/len(df)*100:.1f}% of leads have pit_moves_3yr = 0
   - {positive_change/len(df)*100:.1f}% of leads have firm_net_change_12mo >= 0

2. Single-Feature Performance:
   - flight_risk_score alone: AUC-ROC={frs_auc_roc:.4f}, Lift={frs_lift:.2f}x

3. Missing V2 Features:
""")

missing_features = [f for f in V2_BASE_FEATURES if f not in v3_columns]
if missing_features:
    for f in missing_features:
        print(f"   ❌ {f}")
else:
    print("   ✅ All v2 base features present")

# Save findings
findings_path = VERSION_2_DIR / 'reports' / 'deep_diagnostic_findings.json'
findings_path.parent.mkdir(parents=True, exist_ok=True)
with open(findings_path, 'w', encoding='utf-8') as f:
    json.dump(findings, f, indent=2, default=str)
print(f"\nFindings saved to: {findings_path}")

