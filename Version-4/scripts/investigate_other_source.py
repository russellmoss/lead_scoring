"""Quick investigation of 'Other' lead source category."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

from google.cloud import bigquery
from config.constants import PROJECT_ID, LOCATION, DATASET_ML

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

query = """
SELECT 
  lead_source_original as LeadSource,
  COUNT(*) as cnt,
  SUM(target) as conversions,
  AVG(CASE WHEN target = 1 THEN 1.0 ELSE 0.0 END) as conv_rate
FROM `savvy-gtm-analytics.ml_features.v4_target_variable`
WHERE lead_source_grouped = 'Other'
GROUP BY lead_source_original
ORDER BY cnt DESC
"""

df = client.query(query).to_dataframe()

print("=" * 70)
print("INVESTIGATING 'OTHER' LEAD SOURCE CATEGORY")
print("=" * 70)
print(f"\nTotal 'Other' leads: {df['cnt'].sum():,}")
print(f"Total conversions: {df['conversions'].sum():,}")
overall_conv = df['conversions'].sum() / df['cnt'].sum() * 100
print(f"Overall conversion rate: {overall_conv:.2f}%")
print("\nBreakdown by LeadSource:")
print("-" * 70)
print(f"{'LeadSource':<50} {'Count':>8} {'Conv':>6} {'Rate':>8}")
print("-" * 70)
for _, row in df.iterrows():
    source = row['LeadSource'] if row['LeadSource'] else '(NULL)'
    if len(source) > 48:
        source = source[:45] + "..."
    print(f"{source:<50} {row['cnt']:>8,} {row['conversions']:>6,} {row['conv_rate']*100:>7.2f}%")
print("=" * 70)

