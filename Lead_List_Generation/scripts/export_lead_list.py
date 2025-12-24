"""
Export lead list from BigQuery to CSV for Salesforce import.
Run after Step 3 (hybrid lead list generation).

Working Directory: Lead_List_Generation
Usage: python scripts/export_lead_list.py
"""

import pandas as pd
from pathlib import Path
from google.cloud import bigquery
from datetime import datetime
import sys

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation")
EXPORTS_DIR = WORKING_DIR / "exports"
LOGS_DIR = WORKING_DIR / "logs"

# Ensure output directories exist
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# BIGQUERY CONFIGURATION
# ============================================================================
PROJECT_ID = "savvy-gtm-analytics"
DATASET = "ml_features"
TABLE_NAME = "january_2026_lead_list_v4"

# ============================================================================
# EXPORT CONFIGURATION
# ============================================================================
# Columns to export (in order)
EXPORT_COLUMNS = [
    'advisor_crd',
    'salesforce_lead_id',
    'first_name',
    'last_name',
    'email',
    'phone',
    'linkedin_url',
    'firm_name',
    'firm_crd',
    'score_tier',
    'expected_rate_pct',
    'v4_score',
    'v4_percentile',
    'prospect_type',
    'list_rank'
]

def fetch_lead_list(client):
    """Fetch lead list from BigQuery."""
    query = f"""
    SELECT 
        advisor_crd,
        salesforce_lead_id,
        first_name,
        last_name,
        email,
        phone,
        linkedin_url,
        firm_name,
        firm_crd,
        score_tier,
        expected_rate_pct,
        v4_score,
        v4_percentile,
        prospect_type,
        list_rank
    FROM `{PROJECT_ID}.{DATASET}.{TABLE_NAME}`
    ORDER BY list_rank
    """
    
    print(f"[INFO] Fetching lead list from {TABLE_NAME}...")
    df = client.query(query).to_dataframe()
    print(f"[INFO] Loaded {len(df):,} leads")
    return df

def validate_export(df):
    """Validate the exported data."""
    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)
    
    validation_results = {
        "row_count": len(df),
        "expected_rows": 2400,
        "duplicate_crds": df['advisor_crd'].duplicated().sum(),
        "missing_first_name": df['first_name'].isna().sum(),
        "missing_last_name": df['last_name'].isna().sum(),
        "missing_email": df['email'].isna().sum(),
        "missing_firm_name": df['firm_name'].isna().sum(),
        "missing_score_tier": df['score_tier'].isna().sum(),
        "missing_v4_score": df['v4_score'].isna().sum(),
        "missing_v4_percentile": df['v4_percentile'].isna().sum(),
        "has_linkedin": (df['linkedin_url'].notna() & (df['linkedin_url'] != '')).sum(),
        "linkedin_pct": (df['linkedin_url'].notna() & (df['linkedin_url'] != '')).sum() / len(df) * 100
    }
    
    # Print validation results
    print(f"Row Count: {validation_results['row_count']:,} (expected: {validation_results['expected_rows']:,})")
    print(f"  {'[PASS]' if validation_results['row_count'] == validation_results['expected_rows'] else '[FAIL]'}")
    
    print(f"\nDuplicate CRDs: {validation_results['duplicate_crds']}")
    print(f"  {'[PASS]' if validation_results['duplicate_crds'] == 0 else '[FAIL]'}")
    
    print(f"\nMissing Required Fields:")
    print(f"  First Name: {validation_results['missing_first_name']}")
    print(f"  Last Name: {validation_results['missing_last_name']}")
    print(f"  Email: {validation_results['missing_email']}")
    print(f"  Firm Name: {validation_results['missing_firm_name']}")
    print(f"  Score Tier: {validation_results['missing_score_tier']}")
    print(f"  V4 Score: {validation_results['missing_v4_score']}")
    print(f"  V4 Percentile: {validation_results['missing_v4_percentile']}")
    
    all_required_present = (
        validation_results['missing_first_name'] == 0 and
        validation_results['missing_last_name'] == 0 and
        validation_results['missing_firm_name'] == 0 and
        validation_results['missing_score_tier'] == 0 and
        validation_results['missing_v4_score'] == 0 and
        validation_results['missing_v4_percentile'] == 0
    )
    print(f"  {'[PASS]' if all_required_present else '[FAIL]'}")
    
    print(f"\nLinkedIn Coverage: {validation_results['has_linkedin']:,} ({validation_results['linkedin_pct']:.1f}%)")
    
    # Summary statistics
    print(f"\nSummary Statistics:")
    print(f"  V4 Score Range: {df['v4_score'].min():.4f} - {df['v4_score'].max():.4f}")
    print(f"  V4 Percentile Range: {df['v4_percentile'].min()} - {df['v4_percentile'].max()}")
    print(f"  Average V4 Percentile: {df['v4_percentile'].mean():.1f}")
    
    # Tier distribution
    print(f"\nTier Distribution:")
    tier_dist = df['score_tier'].value_counts().sort_index()
    for tier, count in tier_dist.items():
        pct = count / len(df) * 100
        print(f"  {tier}: {count:,} ({pct:.1f}%)")
    
    print("=" * 70 + "\n")
    
    return validation_results

def export_to_csv(df, output_path):
    """Export DataFrame to CSV."""
    print(f"[INFO] Exporting to {output_path}...")
    
    # Ensure columns are in the correct order
    df_export = df[EXPORT_COLUMNS].copy()
    
    # Export to CSV
    df_export.to_csv(output_path, index=False, encoding='utf-8')
    
    file_size = output_path.stat().st_size / 1024  # Size in KB
    print(f"[INFO] Exported {len(df_export):,} rows to {output_path}")
    print(f"[INFO] File size: {file_size:.1f} KB")
    
    return output_path

def log_results(validation_results, output_path, df):
    """Log export results to execution log."""
    log_file = LOGS_DIR / "EXECUTION_LOG.md"
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    log_entry = f"""
## Step 4: Export Lead List to CSV - {timestamp}

**Status**: ✅ SUCCESS

**Export File**: `{output_path.name}`  
**Location**: `{output_path}`

### Export Summary

**Basic Metrics:**
- Total Rows: **{validation_results['row_count']:,}** (expected: {validation_results['expected_rows']:,})
- File Size: **{output_path.stat().st_size / 1024:.1f} KB**

**Validation Results:**
- Row Count Match: **{'PASS' if validation_results['row_count'] == validation_results['expected_rows'] else 'FAIL'}**
- Duplicate CRDs: **{validation_results['duplicate_crds']}** (should be 0)
- Missing Required Fields: **{'PASS' if validation_results['missing_first_name'] == 0 and validation_results['missing_last_name'] == 0 and validation_results['missing_firm_name'] == 0 and validation_results['missing_score_tier'] == 0 else 'FAIL'}**
  - Missing First Name: {validation_results['missing_first_name']}
  - Missing Last Name: {validation_results['missing_last_name']}
  - Missing Email: {validation_results['missing_email']}
  - Missing Firm Name: {validation_results['missing_firm_name']}
  - Missing Score Tier: {validation_results['missing_score_tier']}
  - Missing V4 Score: {validation_results['missing_v4_score']}
  - Missing V4 Percentile: {validation_results['missing_v4_percentile']}

**Data Quality:**
- LinkedIn Coverage: **{validation_results['has_linkedin']:,}** ({validation_results['linkedin_pct']:.1f}%)
- V4 Score Range: **{df['v4_score'].min():.4f} - {df['v4_score'].max():.4f}**
- V4 Percentile Range: **{df['v4_percentile'].min()} - {df['v4_percentile'].max()}**
- Average V4 Percentile: **{df['v4_percentile'].mean():.1f}**

**Tier Distribution:**
"""
    
    tier_dist = df['score_tier'].value_counts().sort_index()
    for tier, count in tier_dist.items():
        pct = count / len(df) * 100
        log_entry += f"- {tier}: **{count:,}** ({pct:.1f}%)\n"
    
    log_entry += f"""
### Export Columns

The CSV includes the following columns (in order):
1. `advisor_crd` - FINTRX CRD ID
2. `salesforce_lead_id` - Salesforce Lead ID (if exists)
3. `first_name` - Contact first name
4. `last_name` - Contact last name
5. `email` - Email address
6. `phone` - Phone number
7. `linkedin_url` - LinkedIn profile URL
8. `firm_name` - Firm name
9. `firm_crd` - Firm CRD ID
10. `score_tier` - V3 tier assignment
11. `expected_rate_pct` - Expected conversion rate (%)
12. `v4_score` - V4 XGBoost score
13. `v4_percentile` - V4 percentile rank (1-100)
14. `prospect_type` - NEW_PROSPECT or recyclable
15. `list_rank` - Overall ranking in list

### Next Steps

**Step 4 Complete** - Lead list exported to CSV  
**Ready for**: Salesforce import and SDR outreach

---

"""
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    print(f"[INFO] Logged results to {log_file}")

def main():
    print("=" * 70)
    print("EXPORT LEAD LIST TO CSV")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Working Directory: {WORKING_DIR}")
    print("=" * 70)
    
    # Initialize BigQuery client
    client = bigquery.Client(project=PROJECT_ID)
    
    # Fetch data
    df = fetch_lead_list(client)
    
    # Validate
    validation_results = validate_export(df)
    
    # Export to CSV
    timestamp = datetime.now().strftime('%Y%m%d')
    output_filename = f"january_2026_lead_list_{timestamp}.csv"
    output_path = EXPORTS_DIR / output_filename
    
    export_to_csv(df, output_path)
    
    # Log results
    log_results(validation_results, output_path, df)
    
    print("\n" + "=" * 70)
    print("EXPORT COMPLETE")
    print("=" * 70)
    print(f"File: {output_path}")
    print(f"Rows: {len(df):,}")
    print(f"Size: {output_path.stat().st_size / 1024:.1f} KB")
    print("=" * 70)
    
    return output_path

if __name__ == "__main__":
    try:
        output_path = main()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

