"""
time_to_close_diagnostic.py
---------------------------
Determines if the 'Decay' is real or just a Maturity Lag.
"""
from google.cloud import bigquery
import pandas as pd
import numpy as np

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("⏳ Analyzing Sales Cycle Velocity...")

# FIX: Added DATE() cast to CreatedDate so types match
query = """
SELECT 
    l.Id as lead_id,
    l.CreatedDate,
    l.ConvertedDate,
    DATE_DIFF(l.ConvertedDate, DATE(l.CreatedDate), DAY) as days_to_convert
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
WHERE l.IsConverted = TRUE
  AND l.CreatedDate >= '2024-01-01'
  AND l.ConvertedDate IS NOT NULL
"""

print("   Querying BigQuery...")
try:
    df = client.query(query).to_dataframe()

    print(f"✅ Analyzed {len(df)} converted leads from 2024-2025.")

    if len(df) > 0:
        # 1. Calculate Lag Stats
        avg_days = df['days_to_convert'].mean()
        median_days = df['days_to_convert'].median()
        p90_days = df['days_to_convert'].quantile(0.9)

        print(f"\n📊 SALES CYCLE STATS:")
        print(f"   - Median Time to Convert: {median_days:.0f} days")
        print(f"   - Average Time to Convert: {avg_days:.0f} days")
        print(f"   - 90% of deals close within: {p90_days:.0f} days")

        # 2. The "Maturity Multiplier"
        # How many deals happen AFTER the 3-month mark?
        late_bloomers = len(df[df['days_to_convert'] > 90])
        pct_late = late_bloomers / len(df)

        print(f"\n🐢 THE 'LATE BLOOMER' FACTOR:")
        print(f"   - Deals closing AFTER 90 days: {pct_late:.1%}")

        print("\n⚖️ VERDICT:")
        if pct_late > 0.25: # Slightly adjusted threshold
            print("   👉 The drop in 2025 is likely an ILLUSION (Lag Effect).")
            print("      A significant portion of wins take >3 months.")
            print("      RECOMMENDATION: Train on 2024 (Mature Data) to capture these slow-burn winners.")
        else:
            print("   👉 The drop in 2025 is likely REAL (Market Shift).")
            print("      Most deals close fast. The 2025 leads should have converted by now if they were going to.")
            print("      RECOMMENDATION: Train on 2024+2025 but weight recent data higher.")
    else:
        print("❌ No converted leads found in the date range.")

except Exception as e:
    print(f"❌ Query Error: {e}")