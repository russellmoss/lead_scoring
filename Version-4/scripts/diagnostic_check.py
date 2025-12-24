"""Diagnostic check for model performance concerns."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

import pandas as pd

train = pd.read_csv('data/splits/train.csv')
test = pd.read_csv('data/splits/test.csv')

print("=" * 70)
print("DIAGNOSTIC CHECK")
print("=" * 70)

# 1. has_email distribution
print("\n1. has_email distribution (train):")
email_stats = train.groupby('has_email')['target'].agg(['count', 'sum', 'mean'])
email_stats.columns = ['leads', 'conversions', 'conv_rate']
email_stats['conv_rate_pct'] = email_stats['conv_rate'] * 100
print(email_stats[['leads', 'conversions', 'conv_rate_pct']])

# Check test too
print("\n   has_email distribution (test):")
email_stats_test = test.groupby('has_email')['target'].agg(['count', 'sum', 'mean'])
email_stats_test.columns = ['leads', 'conversions', 'conv_rate']
email_stats_test['conv_rate_pct'] = email_stats_test['conv_rate'] * 100
print(email_stats_test[['leads', 'conversions', 'conv_rate_pct']])

# 2. Interaction feature counts
print("\n2. Interaction feature sample sizes (train):")
print(f"  mobility_x_heavy_bleeding=1: {(train['mobility_x_heavy_bleeding']==1).sum():,}")
print(f"  short_tenure_x_high_mobility=1: {(train['short_tenure_x_high_mobility']==1).sum():,}")

print("\n   Interaction feature sample sizes (test):")
print(f"  mobility_x_heavy_bleeding=1: {(test['mobility_x_heavy_bleeding']==1).sum():,}")
print(f"  short_tenure_x_high_mobility=1: {(test['short_tenure_x_high_mobility']==1).sum():,}")

# 3. Interaction feature lift (train)
print("\n3. Interaction feature lift (train):")
baseline = train['target'].mean()
print(f"  Baseline conversion rate: {baseline*100:.2f}%")
for feat in ['mobility_x_heavy_bleeding', 'short_tenure_x_high_mobility']:
    feat_data = train[train[feat]==1]
    if len(feat_data) > 0:
        feat_rate = feat_data['target'].mean()
        lift = feat_rate / baseline if baseline > 0 else 0
        conversions = feat_data['target'].sum()
        print(f"  {feat}: {feat_rate*100:.2f}% ({lift:.2f}x lift, {conversions} conversions, {len(feat_data)} leads)")
    else:
        print(f"  {feat}: No positive cases")

# 4. Check has_email correlation with other features
print("\n4. has_email correlation with target:")
print(f"  Train: {train['has_email'].corr(train['target']):.4f}")
print(f"  Test: {test['has_email'].corr(test['target']):.4f}")

# 5. Check if has_email is capturing something else
print("\n5. has_email vs other data quality flags:")
print(f"  has_email=1 AND has_linkedin=1: {((train['has_email']==1) & (train['has_linkedin']==1)).sum():,} leads")
print(f"  has_email=1 AND has_linkedin=0: {((train['has_email']==1) & (train['has_linkedin']==0)).sum():,} leads")
print(f"  has_email=0 AND has_linkedin=1: {((train['has_email']==0) & (train['has_linkedin']==1)).sum():,} leads")
print(f"  has_email=0 AND has_linkedin=0: {((train['has_email']==0) & (train['has_linkedin']==0)).sum():,} leads")

# Check conversion rates for these combinations
print("\n   Conversion rates by email/linkedin combination:")
for email_val in [0, 1]:
    for linkedin_val in [0, 1]:
        subset = train[(train['has_email']==email_val) & (train['has_linkedin']==linkedin_val)]
        if len(subset) > 0:
            conv_rate = subset['target'].mean() * 100
            print(f"  email={email_val}, linkedin={linkedin_val}: {conv_rate:.2f}% ({len(subset):,} leads)")

print("=" * 70)

