"""Diagnostic script to investigate overfitting after tenure fix."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")

train = pd.read_csv(BASE_DIR / 'data' / 'splits' / 'train.csv')
test = pd.read_csv(BASE_DIR / 'data' / 'splits' / 'test.csv')

print("=" * 70)
print("TENURE DISTRIBUTION: TRAIN vs TEST")
print("=" * 70)

print("\nTraining Period:")
print(train['tenure_bucket'].value_counts(normalize=True).round(3) * 100)
print(f"\nMean tenure_months: {train['tenure_months'].mean():.1f}")
print(f"Median tenure_months: {train['tenure_months'].median():.1f}")

print("\n" + "-" * 40)
print("\nTest Period:")
print(test['tenure_bucket'].value_counts(normalize=True).round(3) * 100)
print(f"\nMean tenure_months: {test['tenure_months'].mean():.1f}")
print(f"Median tenure_months: {test['tenure_months'].median():.1f}")

print("\n" + "=" * 70)
print("CONVERSION RATE BY TENURE BUCKET")
print("=" * 70)

print(f"{'Bucket':<15} | {'Train Rate':<12} | {'Train N':<10} | {'Test Rate':<12} | {'Test N':<10} | {'Difference':<12}")
print("-" * 70)

for bucket in sorted(train['tenure_bucket'].unique()):
    train_sub = train[train['tenure_bucket'] == bucket]
    test_sub = test[test['tenure_bucket'] == bucket]
    
    train_rate = train_sub['target'].mean() * 100 if len(train_sub) > 0 else 0
    test_rate = test_sub['target'].mean() * 100 if len(test_sub) > 0 else 0
    diff = train_rate - test_rate
    
    print(f"{bucket:<15} | {train_rate:>10.2f}% | {len(train_sub):>8,} | {test_rate:>10.2f}% | {len(test_sub):>8,} | {diff:>+10.2f}%")

print("\n" + "=" * 70)
print("TENURE MONTHS DISTRIBUTION")
print("=" * 70)

print("\nTraining Period:")
print(f"  Min: {train['tenure_months'].min():.1f}")
print(f"  25th: {train['tenure_months'].quantile(0.25):.1f}")
print(f"  50th: {train['tenure_months'].quantile(0.50):.1f}")
print(f"  75th: {train['tenure_months'].quantile(0.75):.1f}")
print(f"  Max: {train['tenure_months'].max():.1f}")

print("\nTest Period:")
print(f"  Min: {test['tenure_months'].min():.1f}")
print(f"  25th: {test['tenure_months'].quantile(0.25):.1f}")
print(f"  50th: {test['tenure_months'].quantile(0.50):.1f}")
print(f"  75th: {test['tenure_months'].quantile(0.75):.1f}")
print(f"  Max: {test['tenure_months'].max():.1f}")

print("\n" + "=" * 70)
print("CHECKING FOR PIT VIOLATION")
print("=" * 70)

# Check if tenure_months could be negative (would indicate PIT violation)
train_negative = (train['tenure_months'] < 0).sum()
test_negative = (test['tenure_months'] < 0).sum()

print(f"\nNegative tenure_months (would indicate PIT violation):")
print(f"  Train: {train_negative} leads")
print(f"  Test: {test_negative} leads")

# Check if tenure_months is suspiciously high (might indicate data quality issues)
train_high = (train['tenure_months'] > 600).sum()  # > 50 years
test_high = (test['tenure_months'] > 600).sum()

print(f"\nTenure > 50 years (suspicious):")
print(f"  Train: {train_high} leads")
print(f"  Test: {test_high} leads")

# Check conversion rate by tenure_months ranges
print("\n" + "=" * 70)
print("CONVERSION RATE BY TENURE MONTHS RANGES")
print("=" * 70)

ranges = [
    (0, 12, "0-12 months"),
    (12, 24, "12-24 months"),
    (24, 48, "24-48 months"),
    (48, 120, "48-120 months"),
    (120, 600, "120-600 months"),
    (600, float('inf'), "600+ months")
]

print(f"{'Range':<20} | {'Train Rate':<12} | {'Train N':<10} | {'Test Rate':<12} | {'Test N':<10}")
print("-" * 70)

for min_months, max_months, label in ranges:
    train_sub = train[(train['tenure_months'] >= min_months) & (train['tenure_months'] < max_months)]
    test_sub = test[(test['tenure_months'] >= min_months) & (test['tenure_months'] < max_months)]
    
    train_rate = train_sub['target'].mean() * 100 if len(train_sub) > 0 else 0
    test_rate = test_sub['target'].mean() * 100 if len(test_sub) > 0 else 0
    
    print(f"{label:<20} | {train_rate:>10.2f}% | {len(train_sub):>8,} | {test_rate:>10.2f}% | {len(test_sub):>8,}")

