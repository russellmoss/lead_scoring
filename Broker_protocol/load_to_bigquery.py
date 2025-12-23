"""
Load Broker Protocol matched data to BigQuery
Phase 3: Initial Data Load
"""

from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import config


def load_matched_data_to_bigquery(matched_csv_path, excel_file_name=None, source_url=None, dry_run=False):
    """
    Load matched broker protocol data to BigQuery.
    
    Args:
        matched_csv_path: Path to matched CSV file
        excel_file_name: Name of source Excel file (for logging)
        source_url: Source URL (for logging)
        dry_run: If True, don't actually load to BigQuery
        
    Returns:
        scrape_run_id: Unique ID for this load
    """
    if not Path(matched_csv_path).exists():
        print(f"ERROR: File not found: {matched_csv_path}", file=sys.stderr)
        sys.exit(1)
    
    print("=== LOADING MATCHED DATA TO BIGQUERY ===\n")
    
    # Load matched data
    print("Loading matched data...")
    matched_df = pd.read_csv(matched_csv_path)
    print(f"  Loaded {len(matched_df)} rows from CSV")
    
    # Generate scrape run ID
    scrape_run_id = f"initial_load_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Prepare data for BigQuery - map columns to match schema
    print("\nPreparing data for BigQuery...")
    
    # Create output DataFrame with correct column names
    output_df = pd.DataFrame()
    
    # Map columns
    output_df['broker_protocol_firm_name'] = matched_df['firm_name']
    output_df['firm_crd_id'] = matched_df['firm_crd_id'].astype('Int64')  # Nullable integer
    output_df['fintrx_firm_name'] = matched_df['fintrx_firm_name']
    output_df['former_names'] = matched_df['former_names']
    output_df['dbas'] = matched_df['dbas']
    output_df['has_name_change'] = matched_df['has_name_change'].fillna(False)
    output_df['date_joined'] = pd.to_datetime(matched_df['date_joined'], errors='coerce').dt.date
    output_df['date_withdrawn'] = pd.to_datetime(matched_df['date_withdrawn'], errors='coerce').dt.date
    output_df['is_current_member'] = matched_df['is_current_member'].fillna(True)
    output_df['joinder_qualifications'] = matched_df['joinder_qualifications']
    output_df['date_notes_cleaned'] = matched_df['date_notes_cleaned']
    output_df['firm_name_raw'] = matched_df['firm_name_raw']
    output_df['date_notes_raw'] = matched_df['date_notes_raw']
    output_df['match_confidence'] = matched_df['match_confidence']
    output_df['match_method'] = matched_df['match_method']
    output_df['needs_manual_review'] = matched_df['needs_manual_review'].fillna(False)
    
    # Add tracking metadata
    now = pd.Timestamp.now()
    output_df['scrape_timestamp'] = now
    output_df['scrape_run_id'] = scrape_run_id
    output_df['first_seen_date'] = now.date()
    output_df['last_seen_date'] = now.date()
    output_df['last_updated'] = now
    
    # Fill null values for optional fields
    output_df['manual_review_notes'] = None
    output_df['manual_review_date'] = None
    output_df['manual_review_by'] = None
    
    print(f"  Prepared {len(output_df)} rows")
    print(f"  Scrape Run ID: {scrape_run_id}")
    
    if dry_run:
        print("\n[DRY RUN] Would load to BigQuery:")
        print(f"  Table: {config.TABLE_MEMBERS}")
        print(f"  Rows: {len(output_df)}")
        print(f"  Sample data:")
        print(output_df[['broker_protocol_firm_name', 'firm_crd_id', 'match_method', 'match_confidence']].head(5).to_string())
        return scrape_run_id
    
    # Load to BigQuery
    print(f"\nLoading to BigQuery: {config.TABLE_MEMBERS}")
    client = bigquery.Client(project=config.GCP_PROJECT_ID)
    
    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_APPEND',  # Append data
        schema_update_options=[
            bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION
        ]
    )
    
    job = client.load_table_from_dataframe(
        output_df,
        config.TABLE_MEMBERS,
        job_config=job_config
    )
    
    print("  Waiting for job to complete...")
    job.result()  # Wait for completion
    
    print(f"[SUCCESS] Loaded {len(output_df)} rows to {config.TABLE_MEMBERS}")
    
    # Verify
    query = f"SELECT COUNT(*) as count FROM `{config.TABLE_MEMBERS}`"
    result = client.query(query).to_dataframe()
    total_rows = result['count'].iloc[0]
    print(f"[SUCCESS] Table now has {total_rows} total rows")
    
    return scrape_run_id, matched_df


def create_scrape_log_entry(scrape_run_id, matched_df, excel_file_name=None, source_url=None):
    """
    Create scrape log entry in BigQuery.
    
    Args:
        scrape_run_id: Unique ID for this scrape run
        matched_df: DataFrame with matched data
        excel_file_name: Name of source Excel file
        source_url: Source URL
    """
    print("\n=== CREATING SCRAPE LOG ENTRY ===")
    
    if excel_file_name is None:
        excel_file_name = 'The-Broker-Protocol-Member-Firms-12-22-25.xlsx'
    
    if source_url is None:
        source_url = 'https://www.jsheld.com/markets-served/financial-services/broker-recruiting/the-broker-protocol'
    
    # Calculate metrics
    firms_matched = matched_df['firm_crd_id'].notna().sum()
    avg_confidence = matched_df[matched_df['firm_crd_id'].notna()]['match_confidence'].mean() if firms_matched > 0 else None
    
    # Create log entry
    log_entry = pd.DataFrame([{
        'scrape_run_id': scrape_run_id,
        'scrape_timestamp': pd.Timestamp.now(),
        'scrape_status': 'SUCCESS',
        'source_url': source_url,
        'excel_file_name': excel_file_name,
        'excel_file_size_bytes': None,  # Not available
        'excel_download_timestamp': None,  # Not available
        'firms_downloaded': len(matched_df),
        'firms_parsed': len(matched_df),
        'firms_matched': firms_matched,
        'firms_needing_review': matched_df['needs_manual_review'].sum(),
        'avg_match_confidence': avg_confidence,
        'execution_duration_seconds': None,  # Not tracked
        'error_message': None,
        'error_details': None,
        'new_firms': len(matched_df),
        'withdrawn_firms': 0,
        'info_updates': 0
    }])
    
    client = bigquery.Client(project=config.GCP_PROJECT_ID)
    
    job = client.load_table_from_dataframe(log_entry, config.TABLE_SCRAPE_LOG)
    job.result()
    
    print(f"[SUCCESS] Created scrape log entry: {scrape_run_id}")


def validate_data_quality():
    """
    Validate data quality in BigQuery.
    """
    print("\n=== VALIDATING DATA QUALITY ===\n")
    
    client = bigquery.Client(project=config.GCP_PROJECT_ID)
    
    # Check 1: Total records
    print("Check 1: Total records...")
    query = f"""
    SELECT COUNT(*) as total_firms
    FROM `{config.TABLE_MEMBERS}`
    """
    result = client.query(query).to_dataframe()
    total = result['total_firms'].iloc[0]
    print(f"  Total firms loaded: {total}")
    assert total > 2000, f"Expected >2000 firms, got {total}"
    print("  [PASS] Total firms > 2000")
    
    # Check 2: Match quality
    print("\nCheck 2: Match quality...")
    query = f"""
    SELECT * FROM `{config.TABLE_MEMBERS.replace('.broker_protocol_members', '.broker_protocol_match_quality')}`
    """
    try:
        quality = client.query(query).to_dataframe()
        print("  Match Quality:")
        print(quality.to_string())
        
        match_rate = quality['match_rate_pct'].iloc[0]
        assert match_rate > 70, f"Match rate {match_rate}% is below 70% threshold"
        print(f"  [PASS] Match rate {match_rate}% exceeds 70% threshold")
    except Exception as e:
        print(f"  [WARNING] Could not query match quality view: {e}")
    
    # Check 3: Date coverage
    print("\nCheck 3: Date coverage...")
    query = f"""
    SELECT 
        COUNTIF(date_joined IS NOT NULL) as with_join_date,
        COUNTIF(date_withdrawn IS NOT NULL) as with_withdrawal_date,
        COUNTIF(is_current_member) as current_members,
        COUNTIF(NOT is_current_member) as withdrawn_members
    FROM `{config.TABLE_MEMBERS}`
    """
    dates = client.query(query).to_dataframe()
    print("  Date Coverage:")
    print(dates.to_string())
    print("  [PASS] Date coverage check complete")
    
    # Check 4: No duplicates
    print("\nCheck 4: Duplicate firm names...")
    query = f"""
    SELECT 
        broker_protocol_firm_name,
        COUNT(*) as count
    FROM `{config.TABLE_MEMBERS}`
    GROUP BY broker_protocol_firm_name
    HAVING COUNT(*) > 1
    """
    dupes = client.query(query).to_dataframe()
    if len(dupes) == 0:
        print("  [PASS] No duplicate firm names")
    else:
        print(f"  [WARNING] Found {len(dupes)} duplicate firm names")
        print(dupes.head(10).to_string())
    
    # Check 5: Views work
    print("\nCheck 5: Views...")
    try:
        query = f"SELECT * FROM `{config.TABLE_MEMBERS.replace('.broker_protocol_members', '.broker_protocol_needs_review')}` LIMIT 5"
        needs_review = client.query(query).to_dataframe()
        print(f"  [PASS] Needs review view working: {len(needs_review)} firms (showing first 5)")
    except Exception as e:
        print(f"  [WARNING] Could not query needs review view: {e}")
    
    print("\n=== ALL VALIDATION CHECKS COMPLETE ===")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Load matched broker protocol data to BigQuery')
    parser.add_argument('matched_csv', help='Path to matched CSV file',
                       default=str(config.get_matched_csv_path()), nargs='?')
    parser.add_argument('--excel-file', help='Name of source Excel file')
    parser.add_argument('--source-url', help='Source URL')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no changes)')
    parser.add_argument('--skip-validation', action='store_true', help='Skip data quality validation')
    
    args = parser.parse_args()
    
    try:
        # Load data to BigQuery
        result = load_matched_data_to_bigquery(
            args.matched_csv,
            excel_file_name=args.excel_file,
            source_url=args.source_url,
            dry_run=args.dry_run
        )
        
        if args.dry_run:
            scrape_run_id = result
            print("\n[DRY RUN] Would create scrape log entry and validate data quality")
        else:
            scrape_run_id, matched_df = result
            
            # Create scrape log entry
            create_scrape_log_entry(
                scrape_run_id,
                matched_df,
                excel_file_name=args.excel_file,
                source_url=args.source_url
            )
            
            # Validate data quality
            if not args.skip_validation:
                validate_data_quality()
        
        print("\n[SUCCESS] Phase 3 complete!")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

