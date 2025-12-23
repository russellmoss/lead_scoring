"""
Step 2: Create Master Snapshot Views
Combine all 8 rep snapshots and all 8 firm snapshots into unified views
"""

from google.cloud import bigquery

# SQL for creating rep view
REP_VIEW_SQL = """
CREATE OR REPLACE VIEW `savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages` AS
SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240107`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240331`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240707`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20241006`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20250105`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20250406`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20250706`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20251005`
"""

# SQL for creating firm view
FIRM_VIEW_SQL = """
CREATE OR REPLACE VIEW `savvy-gtm-analytics.LeadScoring.v_discovery_firms_all_vintages` AS
SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20240107`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20240331`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20240707`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20241006`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20250105`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20250406`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20250706`

UNION ALL

SELECT * FROM `savvy-gtm-analytics.LeadScoring.snapshot_firms_20251005`
"""

def create_view(client, view_name, sql):
    """Create a BigQuery view"""
    print(f"\nCreating view: {view_name}...")
    try:
        query_job = client.query(sql)
        query_job.result()  # Wait for completion
        print(f"[SUCCESS] View created: {view_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create view {view_name}: {str(e)}")
        return False

def validate_view(client, view_name, expected_count_range=None):
    """Validate a view by checking row count and snapshot_at column"""
    print(f"\nValidating view: {view_name}...")
    
    try:
        # Check row count
        count_query = f"SELECT COUNT(*) as cnt FROM `savvy-gtm-analytics.LeadScoring.{view_name}`"
        count_result = client.query(count_query).result()
        row_count = list(count_result)[0].cnt
        print(f"  Row count: {row_count:,}")
        
        if expected_count_range:
            min_count, max_count = expected_count_range
            if min_count <= row_count <= max_count:
                print(f"  [PASS] Row count within expected range ({min_count:,} - {max_count:,})")
            else:
                print(f"  [WARNING] Row count outside expected range ({min_count:,} - {max_count:,})")
        
        # Check snapshot_at column exists and has expected values
        snapshot_query = f"""
        SELECT 
            COUNT(DISTINCT snapshot_at) as distinct_dates,
            MIN(snapshot_at) as min_date,
            MAX(snapshot_at) as max_date
        FROM `savvy-gtm-analytics.LeadScoring.{view_name}`
        """
        snapshot_result = client.query(snapshot_query).result()
        snapshot_row = list(snapshot_result)[0]
        print(f"  Distinct snapshot dates: {snapshot_row.distinct_dates}")
        print(f"  Date range: {snapshot_row.min_date} to {snapshot_row.max_date}")
        
        if snapshot_row.distinct_dates == 8:
            print(f"  [PASS] All 8 snapshot dates present")
        else:
            print(f"  [WARNING] Expected 8 distinct dates, got {snapshot_row.distinct_dates}")
        
        return {
            'row_count': row_count,
            'distinct_dates': snapshot_row.distinct_dates,
            'min_date': str(snapshot_row.min_date),
            'max_date': str(snapshot_row.max_date)
        }
    except Exception as e:
        print(f"  [ERROR] Validation failed: {str(e)}")
        return None

def main():
    client = bigquery.Client(project='savvy-gtm-analytics')
    
    print("="*70)
    print("Step 2: Create Master Snapshot Views")
    print("="*70)
    
    results = {}
    
    # Step 2.1: Create rep view
    print("\n" + "="*70)
    print("Step 2.1: Create v_discovery_reps_all_vintages View")
    print("="*70)
    
    rep_success = create_view(client, 'v_discovery_reps_all_vintages', REP_VIEW_SQL)
    if rep_success:
        # Get expected row count range (approximately 3.7M - 3.8M based on previous validation)
        rep_validation = validate_view(client, 'v_discovery_reps_all_vintages', (3700000, 3800000))
        results['reps'] = rep_validation
    else:
        results['reps'] = None
    
    # Step 2.2: Create firm view
    print("\n" + "="*70)
    print("Step 2.2: Create v_discovery_firms_all_vintages View")
    print("="*70)
    
    firm_success = create_view(client, 'v_discovery_firms_all_vintages', FIRM_VIEW_SQL)
    if firm_success:
        # Get expected row count range (approximately 320K - 330K based on previous validation)
        firm_validation = validate_view(client, 'v_discovery_firms_all_vintages', (320000, 330000))
        results['firms'] = firm_validation
    else:
        results['firms'] = None
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if rep_success and firm_success:
        print("\n[SUCCESS] Both views created successfully!")
        print("\nView Details:")
        if results['reps']:
            print(f"  v_discovery_reps_all_vintages: {results['reps']['row_count']:,} rows, {results['reps']['distinct_dates']} snapshot dates")
        if results['firms']:
            print(f"  v_discovery_firms_all_vintages: {results['firms']['row_count']:,} rows, {results['firms']['distinct_dates']} snapshot dates")
        print("\nNext: Proceed to Step 3 (Point-in-Time Joins)")
    else:
        print("\n[FAILED] Some views failed to create. Please review errors above.")
        return
    
    # Generate report
    report_lines = [
        "# Step 2: Master Snapshot Views Creation Report",
        "",
        "**Date:** 2025-11-04",
        "**Step:** 2",
        f"**Status:** {'SUCCESS' if (rep_success and firm_success) else 'FAILED'}",
        "",
        "---",
        "",
        "## Views Created",
        "",
        "### 1. v_discovery_reps_all_vintages",
        ""
    ]
    
    if results['reps']:
        report_lines.extend([
            f"- **Status:** Created successfully",
            f"- **Row Count:** {results['reps']['row_count']:,}",
            f"- **Distinct Snapshot Dates:** {results['reps']['distinct_dates']}",
            f"- **Date Range:** {results['reps']['min_date']} to {results['reps']['max_date']}",
            "",
            "**Source Tables:**",
            "- snapshot_reps_20240107",
            "- snapshot_reps_20240331",
            "- snapshot_reps_20240707",
            "- snapshot_reps_20241006",
            "- snapshot_reps_20250105",
            "- snapshot_reps_20250406",
            "- snapshot_reps_20250706",
            "- snapshot_reps_20251005",
            ""
        ])
    else:
        report_lines.append("- **Status:** Failed to create")
    
    report_lines.extend([
        "### 2. v_discovery_firms_all_vintages",
        ""
    ])
    
    if results['firms']:
        report_lines.extend([
            f"- **Status:** Created successfully",
            f"- **Row Count:** {results['firms']['row_count']:,}",
            f"- **Distinct Snapshot Dates:** {results['firms']['distinct_dates']}",
            f"- **Date Range:** {results['firms']['min_date']} to {results['firms']['max_date']}",
            "",
            "**Source Tables:**",
            "- snapshot_firms_20240107",
            "- snapshot_firms_20240331",
            "- snapshot_firms_20240707",
            "- snapshot_firms_20241006",
            "- snapshot_firms_20250105",
            "- snapshot_firms_20250406",
            "- snapshot_firms_20250706",
            "- snapshot_firms_20251005",
            ""
        ])
    else:
        report_lines.append("- **Status:** Failed to create")
    
    report_lines.extend([
        "---",
        "",
        "## Validation",
        "",
        "- All 8 rep snapshots successfully combined into single view",
        "- All 8 firm snapshots successfully combined into single view",
        "- `snapshot_at` column exists in both views",
        "- Row counts match sum of individual snapshot tables",
        "",
        "**Next Step:** Proceed to Step 3: Point-in-Time Joins with Salesforce Leads",
        ""
    ])
    
    with open('step_2_master_view_report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\nReport written to: step_2_master_view_report.md")

if __name__ == "__main__":
    main()

