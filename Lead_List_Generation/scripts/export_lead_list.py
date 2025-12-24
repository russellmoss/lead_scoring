"""
Export lead list from BigQuery to CSV for Salesforce import.
Run after Step 3 (hybrid lead list generation with V4 upgrade path).

UPDATED: Includes V4 upgrade tracking column

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
# EXPORT CONFIGURATION (UPDATED - includes V4 upgrade columns)
# ============================================================================
EXPORT_COLUMNS = [
    'advisor_crd',
    'salesforce_lead_id',
    'first_name',
    'last_name',
    'job_title',                # NEW!
    'email',
    'phone',
    'linkedin_url',
    'firm_name',
    'firm_crd',
    'score_tier',
    'original_v3_tier',
    'expected_rate_pct',
    'score_narrative',          # NEW!
    'v4_score',
    'v4_percentile',
    'is_v4_upgrade',
    'v4_status',
    'shap_top1_feature',        # NEW!
    'shap_top2_feature',        # NEW!
    'shap_top3_feature',        # NEW!
    'prospect_type',
    'list_rank'
]

def fetch_lead_list(client):
    """Fetch lead list from BigQuery."""
    query = f"""
    SELECT *
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
    
    # Check if is_v4_upgrade column exists
    has_v4_upgrade_col = 'is_v4_upgrade' in df.columns
    v4_upgrade_count = df['is_v4_upgrade'].sum() if has_v4_upgrade_col else 0
    
    validation_results = {
        "row_count": len(df),
        "expected_rows": 2400,
        "duplicate_crds": df['advisor_crd'].duplicated().sum(),
        "has_job_title": df['job_title'].notna().sum() if 'job_title' in df.columns else 0,
        "has_narrative": df['score_narrative'].notna().sum() if 'score_narrative' in df.columns else 0,
        "has_linkedin": (df['linkedin_url'].notna() & (df['linkedin_url'] != '')).sum(),
        "v4_upgrade_count": v4_upgrade_count,
    }
    
    validation_results['job_title_pct'] = validation_results['has_job_title'] / len(df) * 100 if len(df) > 0 else 0
    validation_results['narrative_pct'] = validation_results['has_narrative'] / len(df) * 100 if len(df) > 0 else 0
    validation_results['linkedin_pct'] = validation_results['has_linkedin'] / len(df) * 100 if len(df) > 0 else 0
    validation_results['v4_upgrade_pct'] = validation_results['v4_upgrade_count'] / len(df) * 100 if len(df) > 0 else 0
    
    # Print validation results
    print(f"Row Count: {validation_results['row_count']:,}")
    print(f"Duplicate CRDs: {validation_results['duplicate_crds']}")
    
    print(f"\nJob Title Coverage: {validation_results['has_job_title']:,} ({validation_results['job_title_pct']:.1f}%)")
    print(f"Narrative Coverage: {validation_results['has_narrative']:,} ({validation_results['narrative_pct']:.1f}%)")
    print(f"LinkedIn Coverage: {validation_results['has_linkedin']:,} ({validation_results['linkedin_pct']:.1f}%)")
    
    print(f"\nV4 Upgrades: {validation_results['v4_upgrade_count']:,} ({validation_results['v4_upgrade_pct']:.1f}%)")
    
    # Check for excluded firms
    savvy_count = len(df[df['firm_crd'] == 318493]) if 'firm_crd' in df.columns else 0
    ritholtz_count = len(df[df['firm_crd'] == 168652]) if 'firm_crd' in df.columns else 0
    
    print(f"\nExcluded Firm Check:")
    print(f"  Savvy (CRD 318493): {savvy_count} {'[OK]' if savvy_count == 0 else '[FAIL]'}")
    print(f"  Ritholtz (CRD 168652): {ritholtz_count} {'[OK]' if ritholtz_count == 0 else '[FAIL]'}")
    
    # Tier distribution
    print(f"\nTier Distribution:")
    if 'score_tier' in df.columns:
        tier_dist = df['score_tier'].value_counts().sort_index()
        for tier, count in tier_dist.items():
            pct = count / len(df) * 100
            print(f"  {tier}: {count:,} ({pct:.1f}%)")
    
    print("=" * 70 + "\n")
    
    return validation_results

def export_to_csv(df, output_path):
    """Export DataFrame to CSV."""
    print(f"[INFO] Exporting to {output_path}...")
    
    # Select columns (handle case where some columns may not exist)
    available_cols = [c for c in EXPORT_COLUMNS if c in df.columns]
    df_export = df[available_cols].copy()
    
    # Export to CSV
    df_export.to_csv(output_path, index=False, encoding='utf-8')
    
    file_size = output_path.stat().st_size / 1024  # Size in KB
    print(f"[INFO] Exported {len(df_export):,} rows to {output_path}")
    print(f"[INFO] File size: {file_size:.1f} KB")
    print(f"[INFO] Columns exported: {len(available_cols)}")
    
    return output_path

def log_results(validation_results, output_path, df):
    """Log export results to execution log."""
    log_file = LOGS_DIR / "EXECUTION_LOG.md"
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    savvy_count = len(df[df['firm_crd'] == 318493]) if 'firm_crd' in df.columns else 0
    ritholtz_count = len(df[df['firm_crd'] == 168652]) if 'firm_crd' in df.columns else 0
    
    log_entry = f"""
## Step 4: Export Lead List to CSV - {timestamp}

**Status**: ✅ SUCCESS

**Export File**: `{output_path.name}`  
**Location**: `{output_path}`

### Export Summary

**Basic Metrics:**
- Total Rows: **{validation_results['row_count']:,}**
- File Size: **{output_path.stat().st_size / 1024:.1f} KB**

**New Features:**
- Job Title Coverage: **{validation_results['has_job_title']:,}** ({validation_results['job_title_pct']:.1f}%)
- Narrative Coverage: **{validation_results['has_narrative']:,}** ({validation_results['narrative_pct']:.1f}%)
- LinkedIn Coverage: **{validation_results['has_linkedin']:,}** ({validation_results['linkedin_pct']:.1f}%)

**V4 Upgrade Path:**
- V4 Upgraded Leads: **{validation_results['v4_upgrade_count']:,}** ({validation_results['v4_upgrade_pct']:.1f}%)

**Firm Exclusions:**
- Savvy (CRD 318493): **{savvy_count}** {'✅ EXCLUDED' if savvy_count == 0 else '❌ PRESENT'}
- Ritholtz (CRD 168652): **{ritholtz_count}** {'✅ EXCLUDED' if ritholtz_count == 0 else '❌ PRESENT'}

**Tier Distribution:**
"""
    
    if 'score_tier' in df.columns:
        tier_dist = df['score_tier'].value_counts().sort_index()
        for tier, count in tier_dist.items():
            pct = count / len(df) * 100
            marker = " ⬆️ V4 UPGRADE" if tier == 'V4_UPGRADE' else ""
            log_entry += f"- {tier}: **{count:,}** ({pct:.1f}%){marker}\n"
    
    log_entry += f"""
### Export Columns

The CSV includes the following columns:
1. `advisor_crd` - FINTRX CRD ID
2. `salesforce_lead_id` - Salesforce Lead ID (if exists)
3. `first_name` - Contact first name
4. `last_name` - Contact last name
5. `job_title` - **NEW!** Advisor's job title from FINTRX
6. `email` - Email address
7. `phone` - Phone number
8. `linkedin_url` - LinkedIn profile URL
9. `firm_name` - Firm name
10. `firm_crd` - Firm CRD ID
11. `score_tier` - Final tier (V3 tier or V4_UPGRADE)
12. `original_v3_tier` - Original V3 tier before upgrade
13. `expected_rate_pct` - Expected conversion rate (%)
14. `score_narrative` - **NEW!** Human-readable explanation (V3 rules or V4 SHAP)
15. `v4_score` - V4 XGBoost score
16. `v4_percentile` - V4 percentile rank (1-100)
17. `is_v4_upgrade` - **1 = V4 upgraded lead, 0 = V3 tier lead**
18. `v4_status` - Description of V4 status
19. `shap_top1_feature` - **NEW!** Most important ML feature
20. `shap_top2_feature` - **NEW!** Second most important feature
21. `shap_top3_feature` - **NEW!** Third most important feature
22. `prospect_type` - NEW_PROSPECT or recyclable
23. `list_rank` - Overall ranking in list

### Next Steps

**Step 4 Complete** - Lead list exported to CSV with SHAP narratives, job titles, and firm exclusions  
**Ready for**: Salesforce import and SDR outreach

---

"""
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    print(f"[INFO] Logged results to {log_file}")

def main():
    print("=" * 70)
    print("EXPORT LEAD LIST TO CSV (V4 UPGRADE PATH)")
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
    print(f"Includes: job_title, score_narrative, SHAP features")
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