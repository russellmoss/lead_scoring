"""Quick verification of interaction feature sample sizes after tenure fix."""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")

print("=" * 70)
print("INTERACTION FEATURE SAMPLE SIZES (POST-FIX)")
print("=" * 70)

train = pd.read_csv(BASE_DIR / 'data' / 'splits' / 'train.csv')
test = pd.read_csv(BASE_DIR / 'data' / 'splits' / 'test.csv')

for feat in ['mobility_x_heavy_bleeding', 'short_tenure_x_high_mobility']:
    train_pos = train[train[feat] == 1]
    test_pos = test[test[feat] == 1]
    
    print(f"\n{feat}:")
    print(f"  Train: {len(train_pos)} leads, {train_pos['target'].sum()} conversions ({train_pos['target'].mean()*100:.2f}%)")
    print(f"  Test:  {len(test_pos)} leads, {test_pos['target'].sum()} conversions ({test_pos['target'].mean()*100:.2f}%)")

# Also check tenure coverage
print(f"\n" + "=" * 70)
print("TENURE COVERAGE")
print("=" * 70)
print(f"Train - Unknown tenure: {(train['tenure_bucket'] == 'Unknown').sum()} ({(train['tenure_bucket'] == 'Unknown').mean()*100:.1f}%)")
print(f"Test - Unknown tenure: {(test['tenure_bucket'] == 'Unknown').sum()} ({(test['tenure_bucket'] == 'Unknown').mean()*100:.1f}%)")

print("\n" + "=" * 70)
print("COMPARISON TO PRE-FIX")
print("=" * 70)
print("Before fix (from Phase 6 diagnostic):")
print("  mobility_x_heavy_bleeding: 53 leads (9 conversions)")
print("  short_tenure_x_high_mobility: 93 leads (15 conversions)")
print("\nAfter fix (current):")
train_mob = train[train['mobility_x_heavy_bleeding'] == 1]
train_ten = train[train['short_tenure_x_high_mobility'] == 1]
print(f"  mobility_x_heavy_bleeding: {len(train_mob)} leads ({train_mob['target'].sum()} conversions)")
print(f"  short_tenure_x_high_mobility: {len(train_ten)} leads ({train_ten['target'].sum()} conversions)")

if len(train_mob) > 100 and len(train_ten) > 100:
    print("\n[SUCCESS] Sample sizes are now sufficient for model learning!")
else:
    print("\n[WARNING] Sample sizes are still small - model may struggle to learn these patterns")

