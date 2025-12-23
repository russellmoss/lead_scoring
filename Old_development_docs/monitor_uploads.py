#!/usr/bin/env python3
"""
Monitor Step 1.2 Upload Progress
Run this in a separate terminal window to monitor BigQuery uploads in real-time
"""

from google.cloud import bigquery
import time
from datetime import datetime

client = bigquery.Client(project="savvy-gtm-analytics")

# Expected tables (date-based naming from filenames)
tables = [
    "snapshot_reps_20240107_raw",  # Q1 2024 (Jan 7)
    "snapshot_reps_20240331_raw",  # Q1 2024 (Mar 31)
    "snapshot_reps_20240707_raw",  # Q3 2024
    "snapshot_reps_20241006_raw",  # Q4 2024
    "snapshot_reps_20250105_raw",  # Q1 2025
    "snapshot_reps_20250406_raw",  # Q2 2025
    "snapshot_reps_20250706_raw",  # Q3 2025
    "snapshot_reps_20251005_raw",  # Q4 2025
]

print("=" * 80)
print("Step 1.2 Upload Monitor")
print("=" * 80)
print("Monitoring upload progress... (Press Ctrl+C to stop)\n")

try:
    while True:
        print(f"\n{'='*80}")
        print(f"Status at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        completed = 0
        total = len(tables)
        
        for table_name in tables:
            try:
                table = client.get_table(f"savvy-gtm-analytics.LeadScoring.{table_name}")
                size_mb = table.num_bytes / 1024 / 1024
                print(f"✅ {table_name:40} | {table.num_rows:>10,} rows | {size_mb:>8.2f} MB")
                completed += 1
            except Exception as e:
                if "Not found" in str(e) or "404" in str(e):
                    print(f"⏳ {table_name:40} | Not created yet...")
                else:
                    print(f"❌ {table_name:40} | Error: {str(e)[:50]}")
        
        print(f"\n📊 Progress: {completed}/{total} tables completed")
        
        if completed == total:
            print("\n🎉 All uploads complete!")
            break
        
        print("\nRefreshing in 30 seconds... (Ctrl+C to stop)")
        time.sleep(30)
        
except KeyboardInterrupt:
    print("\n\nMonitoring stopped by user.")
except Exception as e:
    print(f"\n\n❌ Error: {e}")

