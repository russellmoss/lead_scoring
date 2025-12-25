"""
Generate monthly recyclable lead list (V2.2 - With V3 Tier Scoring).

KEY INSIGHT: People who RECENTLY changed firms are NOT good recycle targets.
They just settled in and won't want to move again for 2+ years.

Priority Order:
  P1: "Timing" disposition (they said bad timing, try again)
  P2: High V4 + No firm change + Long tenure (about to move)
  P3: "No Response" + High V4 (good prospect who didn't engage)
  P4: Changed firms 2-3 years ago (proven mover, may be restless)
  P5: Changed firms 3+ years ago (overdue for another change)
  P6: Standard recycle candidates

Usage: python scripts/recycling/generate_recyclable_list_v2.1.py --month january --year 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from google.cloud import bigquery
from google.auth.exceptions import DefaultCredentialsError
from google.api_core import exceptions as gcp_exceptions
import argparse
import json
import sys
import os

# ============================================================================
# CONFIGURATION
# ============================================================================
PROJECT_ID = "savvy-gtm-analytics"
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation")
SQL_DIR = WORKING_DIR / "sql" / "recycling"
EXPORTS_DIR = WORKING_DIR / "exports"
REPORTS_DIR = WORKING_DIR / "reports" / "recycling_analysis"

EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_RECYCLABLE = 600


def estimate_conversion_rate(score: float) -> float:
    """
    Estimate conversion rate from unified recyclable score.
    
    Calibration based on historical data:
    - Score 50 (baseline) → 3.2% conversion
    - Score 100 → 6.0% conversion  
    - Score 135+ → 10.0%+ conversion
    """
    if pd.isna(score) or score <= 50:
        return 3.2
    elif score <= 100:
        # Linear: 50→3.2%, 100→6%
        return 3.2 + (score - 50) * (6.0 - 3.2) / 50
    elif score <= 135:
        # Linear: 100→6%, 135→10%
        return 6.0 + (score - 100) * (10.0 - 6.0) / 35
    else:
        # Cap at ~12% for very high scores
        return min(12.0, 10.0 + (score - 135) * 0.05)


def check_credentials():
    """Check if BigQuery credentials are available."""
    print("\n[INFO] Checking BigQuery authentication...")
    
    # Check for environment variable
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path:
        print(f"[INFO] Found GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
        if not os.path.exists(creds_path):
            print(f"[ERROR] Credentials file not found at: {creds_path}")
            return False
    else:
        print("[INFO] GOOGLE_APPLICATION_CREDENTIALS not set, using default credentials")
    
    # Try to create client to test authentication
    try:
        client = bigquery.Client(project=PROJECT_ID)
        # Try a simple operation to verify credentials work
        client.get_dataset(f"{PROJECT_ID}.SavvyGTMData")
        print("[OK] BigQuery authentication successful")
        return True
    except DefaultCredentialsError as e:
        print(f"[ERROR] Authentication failed - No credentials found")
        print(f"[ERROR] Details: {e}")
        print("\n[INFO] To fix this, run one of:")
        print("  1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable to your service account JSON file")
        print("  2. Run: gcloud auth application-default login")
        return False
    except Exception as e:
        error_msg = str(e).lower()
        if 'connection' in error_msg or 'network' in error_msg or 'timeout' in error_msg:
            print(f"[ERROR] Connection issue detected (but may be authentication): {e}")
            print("[INFO] This error often appears when credentials are missing or invalid")
            print("[INFO] Verify your authentication setup")
        else:
            print(f"[ERROR] Unexpected error during authentication check: {e}")
        return False


def generate_narrative(row: pd.Series) -> str:
    """Generate clear narrative explaining why this lead is being recycled."""
    
    parts = []
    
    # 1. Record type and firm
    if row.get('record_type') == 'OPPORTUNITY':
        parts.append(f"**Previously engaged opportunity** at {row.get('current_firm', 'Unknown')}.")
    else:
        parts.append(f"**Previously contacted lead** at {row.get('current_firm', 'Unknown')}.")
    
    # 2. Score breakdown - why they're ranked high
    score_factors = []
    
    v3_tier = row.get('v3_tier', 'STANDARD')
    if v3_tier and v3_tier != 'STANDARD':
        tier_display = v3_tier.replace('_', ' ').replace('TIER ', 'T')
        score_factors.append(f"V3: {tier_display}")
    
    v4_pct = row.get('v4_percentile')
    if v4_pct and not pd.isna(v4_pct) and float(v4_pct) >= 70:
        score_factors.append(f"V4: {int(v4_pct)}th pct")
    
    timing_reasons = ['Timing', 'Candidate Declined - Timing', 'Candidate Declined - Fear of Change']
    if row.get('close_reason') in timing_reasons:
        score_factors.append("Said 'timing was bad'")
    
    if row.get('at_bleeding_firm'):
        score_factors.append("At bleeding firm")
    
    days = row.get('days_since_last_contact', 0)
    if days and not pd.isna(days) and 180 <= float(days) <= 365:
        score_factors.append(f"Optimal window ({int(days)}d)")
    
    if score_factors:
        parts.append(f"**Signals**: {'; '.join(score_factors)}.")
    
    # 3. Previous contact
    close_reason = row.get('close_reason', 'Unknown')
    close_date = row.get('close_date')
    if pd.notna(close_date):
        try:
            close_str = pd.to_datetime(close_date).strftime('%b %Y')
            parts.append(f"Closed {close_str}: '{close_reason}'.")
        except:
            pass
    
    last_by = row.get('last_contacted_by')
    if last_by and last_by != 'Unknown' and pd.notna(last_by):
        parts.append(f"Last contact: {last_by}.")
    
    # 4. Score and expected conversion
    score = row.get('recyclable_score', 0)
    if score and not pd.isna(score):
        expected_conv = estimate_conversion_rate(float(score))
        parts.append(f"**Score: {float(score):.0f}** | Expected: {expected_conv:.1f}%")
    
    return " ".join(parts)


def query_recyclable_pool(client: bigquery.Client, target_count: int = TARGET_RECYCLABLE) -> pd.DataFrame:
    """Execute the recyclable pool query."""
    
    sql_file = SQL_DIR / "recyclable_pool_master_v2.1.sql"
    
    if not sql_file.exists():
        print(f"[ERROR] SQL file not found: {sql_file}")
        return pd.DataFrame()
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        query = f.read()
    
    query = query.replace('DECLARE target_count INT64 DEFAULT 600;', 
                         f'DECLARE target_count INT64 DEFAULT {target_count};')
    
    print(f"[INFO] Querying recyclable pool (target: {target_count})...")
    try:
        df = client.query(query).to_dataframe()
        print(f"[INFO] Retrieved {len(df):,} recyclable records")
        return df
    except Exception as e:
        print(f"[ERROR] Query execution failed: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def generate_summary_report(df: pd.DataFrame, month: str, year: int) -> str:
    """Generate summary report for recyclable list."""
    
    # Calculate expected conversions
    df['expected_conv_pct'] = df['recyclable_score'].apply(estimate_conversion_rate)
    total_expected = (df['expected_conv_pct'] / 100).sum()
    avg_rate = df['expected_conv_pct'].mean()
    
    report = f"""# Recyclable Lead List - {month.title()} {year}

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Total Records**: {len(df):,}  
**Expected Conversions**: {total_expected:.1f} ({avg_rate:.1f}% avg rate)

---

## Unified Scoring Approach

Each lead scored using:
- **V4 ML Score** (0-100 pts) - Machine learning prediction
- **V3 Tier Boost** (0-35 pts) - CFP, bleeding firm, proven mover signals
- **Timing Boost** (+15 pts) - Previously said "timing was bad"
- **Opportunity Boost** (+10 pts) - Warmer than lead
- **Optimal Window** (+10 pts) - 180-365 days since contact
- **Bleeding Firm** (+8 pts) - Currently at unstable firm

Top 600 by score selected.

---

## Score Distribution

| Metric | Value |
|--------|-------|
| Highest | {df['recyclable_score'].max():.0f} |
| Lowest | {df['recyclable_score'].min():.0f} |
| Average | {df['recyclable_score'].mean():.1f} |
| Median | {df['recyclable_score'].median():.1f} |

---

## By Record Type

| Type | Count | Avg Score | Expected Conv |
|------|-------|-----------|---------------|
"""
    
    for rtype in ['OPPORTUNITY', 'LEAD']:
        subset = df[df['record_type'] == rtype]
        if len(subset) > 0:
            avg_score = subset['recyclable_score'].mean()
            expected = (subset['expected_conv_pct'] / 100).sum()
            report += f"| {rtype} | {len(subset):,} | {avg_score:.1f} | {expected:.1f} |\n"
    
    report += """
---

## V3 Tier Distribution

| V3 Tier | Count | Avg Score |
|---------|-------|-----------|
"""
    
    if 'v3_tier' in df.columns:
        v3_summary = df.groupby('v3_tier').agg({
            'record_id': 'count',
            'recyclable_score': 'mean'
        }).sort_values('recyclable_score', ascending=False)
        
        for tier, row in v3_summary.iterrows():
            report += f"| {tier} | {int(row['record_id']):,} | {row['recyclable_score']:.1f} |\n"
    
    report += f"""
---

## Score Buckets

| Score Range | Count | Avg Conv Rate | Expected Conv |
|-------------|-------|---------------|---------------|
"""
    
    buckets = [(120, 999, '120+'), (90, 120, '90-119'), (60, 90, '60-89'), (0, 60, '<60')]
    for low, high, label in buckets:
        subset = df[(df['recyclable_score'] >= low) & (df['recyclable_score'] < high)]
        if len(subset) > 0:
            avg_conv = subset['expected_conv_pct'].mean()
            expected = (subset['expected_conv_pct'] / 100).sum()
            report += f"| {label} | {len(subset):,} | {avg_conv:.1f}% | {expected:.1f} |\n"
    
    report += f"""
---

**Summary**: Top 600 recyclable leads by unified score. Expected {total_expected:.0f} conversions.
"""
    
    return report


def main():
    parser = argparse.ArgumentParser(description='Generate monthly recyclable lead list (V2.2)')
    parser.add_argument('--month', type=str, default='january', help='Month name')
    parser.add_argument('--year', type=int, default=2026, help='Year')
    parser.add_argument('--target', type=int, default=TARGET_RECYCLABLE, help='Target count')
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"RECYCLABLE LEAD LIST GENERATOR V2.2 - {args.month.upper()} {args.year}")
    print("=" * 70)
    print("\nKEY LOGIC: Excluding people who changed firms < 2 years ago")
    print("          (they just settled in and won't move again soon)\n")
    
    # Check credentials first
    if not check_credentials():
        print("\n[ERROR] Authentication check failed. Cannot proceed with query.")
        sys.exit(1)
    
    # Initialize client
    try:
        client = bigquery.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"[ERROR] Failed to create BigQuery client: {e}")
        sys.exit(1)
    
    # Query
    df = query_recyclable_pool(client, args.target)
    
    if len(df) == 0:
        print("[ERROR] No recyclable records found")
        sys.exit(1)
    
    # Calculate expected conversion from score
    df['expected_conv_pct'] = df['recyclable_score'].apply(estimate_conversion_rate)
    
    # Generate narratives
    print("[INFO] Generating recycling narratives...")
    df['recycle_narrative'] = df.apply(generate_narrative, axis=1)
    
    # Export
    export_file = EXPORTS_DIR / f"{args.month}_{args.year}_recyclable_leads.csv"
    df.to_csv(export_file, index=False)
    print(f"[INFO] Exported to {export_file}")
    
    # Report
    report = generate_summary_report(df, args.month, args.year)
    report_file = REPORTS_DIR / f"{args.month}_{args.year}_recyclable_list_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"[INFO] Report: {report_file}")
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Total: {len(df):,}")
    print(f"Score range: {df['recyclable_score'].min():.0f} - {df['recyclable_score'].max():.0f}")
    print(f"Opportunities: {(df['record_type'] == 'OPPORTUNITY').sum():,}")
    print(f"Leads: {(df['record_type'] == 'LEAD').sum():,}")
    total_expected = (df['expected_conv_pct'] / 100).sum()
    print(f"Expected conversions: {total_expected:.1f}")


if __name__ == "__main__":
    main()

