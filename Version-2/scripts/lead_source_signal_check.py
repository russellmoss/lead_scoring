# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\lead_source_signal_check.py
# Check if danger zone signal works WITHIN each lead source

from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("LEAD SOURCE SIGNAL CHECK")
print("Does the Danger Zone signal work WITHIN each lead source?")
print("=" * 70)

query = """
SELECT 
    l.LeadSource as lead_source,
    v.in_danger_zone,
    s.target,
    EXTRACT(YEAR FROM s.contacted_date) as year
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2` s
LEFT JOIN `savvy-gtm-analytics.ml_features.lead_velocity_features` v
    ON s.lead_id = v.lead_id
LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
    ON s.lead_id = l.Id
WHERE s.split IN ('TRAIN', 'TEST')
"""

print("\nLoading data...")
df = client.query(query).result().to_dataframe()

# Get top lead sources
top_sources = df['lead_source'].value_counts().head(5).index.tolist()

print("\n" + "=" * 70)
print("DANGER ZONE LIFT BY LEAD SOURCE")
print("=" * 70)

print(f"\n{'Lead Source':<30} | {'Year':<6} | {'Non-DZ':<12} | {'DZ':<12} | {'Lift':<8}")
print("-" * 80)

for source in top_sources:
    for year in [2024, 2025]:
        subset = df[(df['lead_source'] == source) & (df['year'] == year)]
        
        dz = subset[subset['in_danger_zone'] == 1]
        non_dz = subset[subset['in_danger_zone'] == 0]
        
        if len(dz) >= 10 and len(non_dz) >= 50:
            dz_conv = dz['target'].mean()
            non_dz_conv = non_dz['target'].mean()
            lift = dz_conv / non_dz_conv if non_dz_conv > 0 else 0
            
            lift_marker = "🔥" if lift >= 2.5 else ("✅" if lift >= 1.5 else "⚠️")
            
            print(f"{str(source)[:30]:<30} | {year:<6} | {non_dz_conv*100:<10.1f}% | {dz_conv*100:<10.1f}% | {lift:.2f}x {lift_marker}")

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)

print("""
If DZ lift is HIGH within each source:
  → The DZ signal is REAL and works regardless of source
  → You DON'T need lead_source as a feature
  → Just use DZ features and set expectations by source

If DZ lift is HIGH for some sources but LOW for others:
  → The signal is SOURCE-DEPENDENT
  → Consider: Separate models per source, OR lead_source as feature

If DZ lift is LOW across all sources:
  → The original DZ signal was confounded with lead source mix
  → The "signal" might have been just "Provided Lead List" in disguise
""")

# Summary table
print("\n" + "=" * 70)
print("SUMMARY: 2025 DZ LIFT BY SOURCE (The realistic picture)")
print("=" * 70)

for source in top_sources:
    subset_2025 = df[(df['lead_source'] == source) & (df['year'] == 2025)]
    
    dz = subset_2025[subset_2025['in_danger_zone'] == 1]
    non_dz = subset_2025[subset_2025['in_danger_zone'] == 0]
    
    if len(dz) >= 5 and len(non_dz) >= 20:
        dz_conv = dz['target'].mean()
        non_dz_conv = non_dz['target'].mean()
        lift = dz_conv / non_dz_conv if non_dz_conv > 0 else 0
        
        print(f"\n{source}:")
        print(f"  DZ leads: {len(dz):,} ({dz_conv*100:.1f}% conv)")
        print(f"  Non-DZ leads: {len(non_dz):,} ({non_dz_conv*100:.1f}% conv)")
        print(f"  Lift: {lift:.2f}x")
