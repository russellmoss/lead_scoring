"""Check temporal distribution of Provided List leads."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

from google.cloud import bigquery
from config.constants import PROJECT_ID, LOCATION, DATASET_ML, TEST_START_DATE, TEST_END_DATE

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

query = """
SELECT 
  FORMAT_DATE('%Y-Q%Q', contacted_date) as quarter,
  COUNT(*) as leads,
  SUM(target) as conversions,
  ROUND(AVG(target) * 100, 2) as conv_rate
FROM `savvy-gtm-analytics.ml_features.v4_target_variable`
GROUP BY quarter
ORDER BY quarter
"""

df = client.query(query).to_dataframe()

print("=" * 70)
print("TEMPORAL DISTRIBUTION: PROVIDED LEAD LIST ONLY")
print("=" * 70)
print("\nQuarterly Breakdown:")
print("-" * 70)
print(f"{'Quarter':<12} {'Leads':>10} {'Conversions':>12} {'Conv Rate':>10}")
print("-" * 70)
for _, row in df.iterrows():
    print(f"{row['quarter']:<12} {row['leads']:>10,} {row['conversions']:>12,} {row['conv_rate']:>9.2f}%")
print("-" * 70)

# Check test period (Q3-Q4 2025)
test_df = df[df['quarter'].isin(['2025-Q3', '2025-Q4'])]
test_leads = test_df['leads'].sum()
test_conversions = test_df['conversions'].sum()

print(f"\nTest Period (Q3-Q4 2025):")
print(f"  Total Leads: {test_leads:,}")
print(f"  Conversions: {test_conversions:,}")
if test_leads > 0:
    print(f"  Conversion Rate: {test_conversions/test_leads*100:.2f}%")
else:
    print(f"  Conversion Rate: N/A")

print(f"\n[CHECK] Test period has >= 3,000 leads: {test_leads >= 3000}")
print(f"[CHECK] Test period has >= 50 conversions: {test_conversions >= 50}")

# Check training period
train_df = df[~df['quarter'].isin(['2025-Q3', '2025-Q4'])]
train_leads = train_df['leads'].sum()
train_conversions = train_df['conversions'].sum()

print(f"\nTraining Period (Q1 2024 - Q2 2025):")
print(f"  Total Leads: {train_leads:,}")
print(f"  Conversions: {train_conversions:,}")
if train_leads > 0:
    print(f"  Conversion Rate: {train_conversions/train_leads*100:.2f}%")

print("=" * 70)

