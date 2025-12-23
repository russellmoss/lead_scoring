# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\velocity_test_diagnostic.py
# Quick diagnostic to understand test set velocity patterns

import sys
from pathlib import Path
VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

import pandas as pd
import numpy as np
from google.cloud import bigquery

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("VELOCITY FEATURE DIAGNOSTIC: TRAIN vs TEST")
print("=" * 70)

# Load data with velocity features
query = """
SELECT 
    s.lead_id,
    s.contacted_date,
    s.target,
    s.split,
    v.days_at_current_firm,
    v.in_danger_zone,
    v.tenure_bucket,
    v.moves_3yr_from_starts,
    v.total_jobs_pit as total_jobs
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2` s
LEFT JOIN `savvy-gtm-analytics.ml_features.lead_velocity_features` v
    ON s.lead_id = v.lead_id
WHERE s.split IN ('TRAIN', 'TEST')
"""

print("\nLoading data...")
df = client.query(query).result().to_dataframe()
df['contacted_date'] = pd.to_datetime(df['contacted_date'])

train_df = df[df['split'] == 'TRAIN'].copy()
test_df = df[df['split'] == 'TEST'].copy()

print(f"Train: {len(train_df):,} leads")
print(f"Test: {len(test_df):,} leads")

# =============================================================================
# ANALYSIS 1: Danger Zone by Split
# =============================================================================
print("\n" + "=" * 70)
print("ANALYSIS 1: DANGER ZONE CONVERSION BY SPLIT")
print("=" * 70)

for split_name, split_df in [("TRAIN", train_df), ("TEST", test_df)]:
    print(f"\n{split_name}:")
    dz_counts = split_df.groupby('in_danger_zone')['target'].agg(['count', 'mean', 'sum'])
    for idx, row in dz_counts.iterrows():
        status = "DANGER ZONE" if idx == 1 else "NOT danger zone"
        print(f"  {status}: {int(row['count']):,} leads, {row['mean']*100:.2f}% conv ({int(row['sum'])} conversions)")
    
    # Calculate lift
    dz_rate = split_df[split_df['in_danger_zone'] == 1]['target'].mean()
    baseline = split_df['target'].mean()
    if dz_rate > 0 and baseline > 0:
        lift = dz_rate / baseline
        print(f"  Danger Zone Lift: {lift:.2f}x")

# =============================================================================
# ANALYSIS 2: Tenure Bucket by Split
# =============================================================================
print("\n" + "=" * 70)
print("ANALYSIS 2: TENURE BUCKET CONVERSION BY SPLIT")
print("=" * 70)

for split_name, split_df in [("TRAIN", train_df), ("TEST", test_df)]:
    print(f"\n{split_name}:")
    bucket_stats = split_df.groupby('tenure_bucket')['target'].agg(['count', 'mean']).sort_values('mean', ascending=False)
    for bucket, row in bucket_stats.iterrows():
        print(f"  {bucket:25s}: {int(row['count']):5,} leads, {row['mean']*100:.2f}% conv")

# =============================================================================
# ANALYSIS 3: Date Range Check
# =============================================================================
print("\n" + "=" * 70)
print("ANALYSIS 3: DATE RANGES")
print("=" * 70)

print(f"\nTRAIN date range: {train_df['contacted_date'].min()} to {train_df['contacted_date'].max()}")
print(f"TEST date range:  {test_df['contacted_date'].min()} to {test_df['contacted_date'].max()}")

# Check monthly conversion rates in test
print("\nTest set monthly conversion rates:")
test_df['month'] = test_df['contacted_date'].dt.to_period('M')
monthly = test_df.groupby('month')['target'].agg(['count', 'mean', 'sum'])
for month, row in monthly.iterrows():
    print(f"  {month}: {int(row['count']):,} leads, {row['mean']*100:.2f}% conv ({int(row['sum'])} conversions)")

# =============================================================================
# ANALYSIS 4: 2024-Only Danger Zone
# =============================================================================
print("\n" + "=" * 70)
print("ANALYSIS 4: 2024-ONLY DATA (Matching Original Diagnostic)")
print("=" * 70)

df_2024 = df[df['contacted_date'].dt.year == 2024].copy()
print(f"\n2024 leads: {len(df_2024):,}")

dz_2024 = df_2024.groupby('in_danger_zone')['target'].agg(['count', 'mean', 'sum'])
for idx, row in dz_2024.iterrows():
    status = "DANGER ZONE" if idx == 1 else "NOT danger zone"
    print(f"  {status}: {int(row['count']):,} leads, {row['mean']*100:.2f}% conv ({int(row['sum'])} conversions)")

dz_rate_2024 = df_2024[df_2024['in_danger_zone'] == 1]['target'].mean()
baseline_2024 = df_2024['target'].mean()
if dz_rate_2024 > 0 and baseline_2024 > 0:
    lift_2024 = dz_rate_2024 / baseline_2024
    print(f"\n2024 Danger Zone Lift: {lift_2024:.2f}x")

# =============================================================================
# ANALYSIS 5: The 22% Missing Velocity Data
# =============================================================================
print("\n" + "=" * 70)
print("ANALYSIS 5: MISSING VELOCITY DATA")
print("=" * 70)

has_velocity = df['days_at_current_firm'].notna()
print(f"\nLeads with velocity data: {has_velocity.sum():,} ({has_velocity.mean()*100:.1f}%)")
print(f"Leads WITHOUT velocity data: {(~has_velocity).sum():,} ({(~has_velocity).mean()*100:.1f}%)")

# Conversion rates by velocity data availability
print("\nConversion rates:")
print(f"  WITH velocity data:    {df[has_velocity]['target'].mean()*100:.2f}%")
print(f"  WITHOUT velocity data: {df[~has_velocity]['target'].mean()*100:.2f}%")

# =============================================================================
# RECOMMENDATION
# =============================================================================
print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)

print("""
If the danger zone signal holds in 2024 but NOT in 2025/test:
  → Train on 2024 only, test on early 2025
  
If the danger zone signal is weak overall:
  → The signal might be statistical noise
  
If missing velocity data has higher conversion:
  → The feature engineering is introducing bias
""")
