"""Quick verification of train/test splits."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

import pandas as pd

train = pd.read_csv('data/splits/train.csv')
test = pd.read_csv('data/splits/test.csv')

print("=" * 70)
print("SPLIT VERIFICATION")
print("=" * 70)
print(f"\nTrain: {len(train):,} rows")
print(f"  Conversions: {train['target'].sum():,} ({train['target'].mean()*100:.2f}%)")
print(f"  CV Folds: {sorted(train['cv_fold'].unique().tolist())}")

print(f"\nTest: {len(test):,} rows")
print(f"  Conversions: {test['target'].sum():,} ({test['target'].mean()*100:.2f}%)")
print(f"  CV Fold: {sorted(test['cv_fold'].unique().tolist())}")

print("\n" + "=" * 70)

