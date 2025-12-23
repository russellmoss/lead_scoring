"""
Broker Protocol Data Updater
Merges new scrape data with existing data, tracking changes.
"""

from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import uuid
import sys
import json
from pathlib import Path
import config


def _normalize_value(val):
    """Normalize value for comparison (handle None, NaN, empty strings)"""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        if val == '':
            return None
    return val


def _values_equal(val1, val2):
    """Compare two values, handling None/NaN/empty strings"""
    val1 = _normalize_value(val1)
    val2 = _normalize_value(val2)
    
    # Both None/NaN
    if val1 is None and val2 is None:
        return True
    
    # One is None, other is not
    if val1 is None or val2 is None:
        return False
    
    # Both are dates - compare as strings
    if isinstance(val1, (pd.Timestamp, datetime)) and isinstance(val2, (pd.Timestamp, datetime)):
        return str(val1.date()) == str(val2.date())
    if hasattr(val1, 'date') and hasattr(val2, 'date'):
        return str(val1.date()) == str(val2.date())
    
    # Regular comparison
    return val1 == val2


def compare_records(old_row: dict, new_row: dict) -> dict:
    """
    Compare two records and identify changes.
    
    Returns:
        dict with 'has_changes' (bool) and 'changes' (list of change descriptions)
    """
    changes = []
    
    # Check for withdrawal
    old_withdrawn = old_row.get('date_withdrawn')
    new_withdrawn = new_row.get('date_withdrawn')
    if pd.isna(old_withdrawn) and pd.notna(new_withdrawn):
        changes.append({
            'type': 'WITHDREW',
            'field': 'date_withdrawn',
            'old_value': None,
            'new_value': str(new_withdrawn)
        })
    
    # Check for name change (using broker_protocol_firm_name)
    old_name = old_row.get('broker_protocol_firm_name')
    new_name = new_row.get('firm_name')  # New data uses 'firm_name'
    if not _values_equal(old_name, new_name):
        changes.append({
            'type': 'NAME_CHANGED',
            'field': 'broker_protocol_firm_name',
            'old_value': old_name,
            'new_value': new_name
        })
    
    # Check for matching update
    old_crd = old_row.get('firm_crd_id')
    new_crd = new_row.get('firm_crd_id')
    if pd.isna(old_crd) and pd.notna(new_crd):
        # New match found
        changes.append({
            'type': 'MATCHED',
            'field': 'firm_crd_id',
            'old_value': None,
            'new_value': int(new_crd)
        })
    elif pd.notna(old_crd) and pd.notna(new_crd) and int(old_crd) != int(new_crd):
        # Match changed
        changes.append({
            'type': 'MATCHED',
            'field': 'firm_crd_id',
            'old_value': int(old_crd),
            'new_value': int(new_crd)
        })
    
    # Check for info updates (other fields) - only check meaningful changes
    check_fields = ['former_names', 'dbas', 'joinder_qualifications']
    for field in check_fields:
        old_val = old_row.get(field)
        new_val = new_row.get(field)
        if not _values_equal(old_val, new_val):
            changes.append({
                'type': 'INFO_UPDATED',
                'field': field,
                'old_value': old_val,
                'new_value': new_val
            })
    
    # Check date_joined separately (only if it actually changed)
    old_date = old_row.get('date_joined')
    new_date = new_row.get('date_joined')
    if not _values_equal(old_date, new_date):
        changes.append({
            'type': 'INFO_UPDATED',
            'field': 'date_joined',
            'old_value': str(old_date) if pd.notna(old_date) else None,
            'new_value': str(new_date) if pd.notna(new_date) else None
        })
    
    return {
        'has_changes': len(changes) > 0,
        'changes': changes
    }


def merge_broker_protocol_data(new_data_path: str, scrape_run_id: str = None, dry_run: bool = False):
    """
    Merge new broker protocol data with existing data.
    
    Args:
        new_data_path: Path to CSV with new data
        scrape_run_id: Unique ID for this scrape run (auto-generated if None)
        dry_run: If True, don't actually update database
    """
    
    if scrape_run_id is None:
        scrape_run_id = f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    client = bigquery.Client(project=config.GCP_PROJECT_ID)
    
    print(f"=== BROKER PROTOCOL DATA MERGE ===")
    print(f"Scrape Run ID: {scrape_run_id}")
    print(f"Dry Run: {dry_run}\n")
    
    if not Path(new_data_path).exists():
        print(f"ERROR: File not found: {new_data_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load new data
    print("Loading new data...")
    new_df = pd.read_csv(new_data_path)
    print(f"  New data: {len(new_df)} firms")
    
    # Load existing data
    print("Loading existing data from BigQuery...")
    query = f"""
    SELECT 
        broker_protocol_firm_name,
        firm_crd_id,
        fintrx_firm_name,
        former_names,
        dbas,
        date_joined,
        date_withdrawn,
        is_current_member,
        joinder_qualifications,
        match_confidence,
        match_method,
        first_seen_date,
        last_seen_date
    FROM `{config.TABLE_MEMBERS}`
    """
    existing_df = client.query(query).to_dataframe()
    print(f"  Existing data: {len(existing_df)} firms")
    
    # Compare and categorize
    print("\nAnalyzing changes...")
    
    existing_names = set(existing_df['broker_protocol_firm_name'].values)
    new_names = set(new_df['firm_name'].values)
    
    newly_joined = new_names - existing_names
    newly_withdrawn = existing_names - new_names
    potentially_updated = existing_names & new_names
    
    print(f"  Newly joined firms: {len(newly_joined)}")
    print(f"  Newly withdrawn firms: {len(newly_withdrawn)}")
    print(f"  Existing firms (checking for updates): {len(potentially_updated)}")
    
    # Track changes
    changes_to_log = []
    
    # Process newly joined firms
    new_firms = []
    for firm_name in newly_joined:
        row = new_df[new_df['firm_name'] == firm_name].iloc[0]
        
        # Handle date conversion
        date_joined = row.get('date_joined')
        if pd.notna(date_joined):
            if isinstance(date_joined, str):
                date_joined = pd.to_datetime(date_joined, errors='coerce').date()
            elif isinstance(date_joined, pd.Timestamp):
                date_joined = date_joined.date()
        
        date_withdrawn = row.get('date_withdrawn')
        if pd.notna(date_withdrawn):
            if isinstance(date_withdrawn, str):
                date_withdrawn = pd.to_datetime(date_withdrawn, errors='coerce').date()
            elif isinstance(date_withdrawn, pd.Timestamp):
                date_withdrawn = date_withdrawn.date()
        
        new_firm = {
            'broker_protocol_firm_name': row['firm_name'],
            'firm_crd_id': row.get('firm_crd_id') if pd.notna(row.get('firm_crd_id')) else None,
            'fintrx_firm_name': row.get('fintrx_firm_name'),
            'former_names': row.get('former_names'),
            'dbas': row.get('dbas'),
            'has_name_change': row.get('has_name_change', False),
            'date_joined': date_joined,
            'date_withdrawn': date_withdrawn,
            'is_current_member': row.get('is_current_member', True),
            'joinder_qualifications': row.get('joinder_qualifications'),
            'date_notes_cleaned': row.get('date_notes_cleaned'),
            'firm_name_raw': row.get('firm_name_raw'),
            'date_notes_raw': row.get('date_notes_raw'),
            'match_confidence': row.get('match_confidence'),
            'match_method': row.get('match_method'),
            'needs_manual_review': row.get('needs_manual_review', False),
            'scrape_timestamp': pd.Timestamp.now(),
            'scrape_run_id': scrape_run_id,
            'first_seen_date': pd.Timestamp.now().date(),
            'last_seen_date': pd.Timestamp.now().date(),
            'last_updated': pd.Timestamp.now()
        }
        
        new_firms.append(new_firm)
        
        # Log change
        changes_to_log.append({
            'history_id': str(uuid.uuid4()),
            'broker_protocol_firm_name': firm_name,
            'firm_crd_id': new_firm['firm_crd_id'],
            'change_type': 'JOINED',
            'change_date': date_joined if date_joined else pd.Timestamp.now().date(),
            'detected_at': pd.Timestamp.now(),
            'previous_values': None,
            'new_values': json.dumps(new_firm, default=str),
            'scrape_run_id': scrape_run_id,
            'notes': 'Newly joined firm detected'
        })
    
    # Process newly withdrawn firms
    for firm_name in newly_withdrawn:
        old_row = existing_df[existing_df['broker_protocol_firm_name'] == firm_name].iloc[0].to_dict()
        
        # Log withdrawal
        changes_to_log.append({
            'history_id': str(uuid.uuid4()),
            'broker_protocol_firm_name': firm_name,
            'firm_crd_id': old_row.get('firm_crd_id'),
            'change_type': 'WITHDREW',
            'change_date': pd.Timestamp.now().date(),
            'detected_at': pd.Timestamp.now(),
            'previous_values': json.dumps({'is_current_member': True}),
            'new_values': json.dumps({'is_current_member': False}),
            'scrape_run_id': scrape_run_id,
            'notes': 'Firm no longer in broker protocol list'
        })
    
    # Process existing firms - check for updates
    updated_firms = []
    for firm_name in potentially_updated:
        old_row = existing_df[existing_df['broker_protocol_firm_name'] == firm_name].iloc[0].to_dict()
        new_row = new_df[new_df['firm_name'] == firm_name].iloc[0].to_dict()
        
        comparison = compare_records(old_row, new_row)
        
        if comparison['has_changes']:
            # Update record
            updated_firm = {
                'broker_protocol_firm_name': firm_name,
                'last_seen_date': pd.Timestamp.now().date(),
                'last_updated': pd.Timestamp.now(),
                'scrape_run_id': scrape_run_id
            }
            
            # Apply changes
            for change in comparison['changes']:
                field = change['field']
                new_value = new_row.get(field) if field != 'broker_protocol_firm_name' else new_row.get('firm_name')
                
                # Handle date fields
                if field in ['date_joined', 'date_withdrawn'] and pd.notna(new_value):
                    if isinstance(new_value, str):
                        new_value = pd.to_datetime(new_value, errors='coerce').date()
                    elif isinstance(new_value, pd.Timestamp):
                        new_value = new_value.date()
                
                updated_firm[field] = new_value
                
                if change['type'] == 'WITHDREW':
                    updated_firm['is_current_member'] = False
            
            updated_firms.append(updated_firm)
            
            # Log each change
            for change in comparison['changes']:
                changes_to_log.append({
                    'history_id': str(uuid.uuid4()),
                    'broker_protocol_firm_name': firm_name,
                    'firm_crd_id': old_row.get('firm_crd_id'),
                    'change_type': change['type'],
                    'change_date': pd.Timestamp.now().date(),
                    'detected_at': pd.Timestamp.now(),
                    'previous_values': json.dumps({'field': change['field'], 'value': change['old_value']}, default=str),
                    'new_values': json.dumps({'field': change['field'], 'value': change['new_value']}, default=str),
                    'scrape_run_id': scrape_run_id,
                    'notes': f"Field '{change['field']}' changed"
                })
        else:
            # No changes, just update last_seen_date
            updated_firms.append({
                'broker_protocol_firm_name': firm_name,
                'last_seen_date': pd.Timestamp.now().date(),
                'scrape_run_id': scrape_run_id
            })
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"New firms to add: {len(new_firms)}")
    print(f"Firms withdrawn: {len(newly_withdrawn)}")
    print(f"Existing firms to update: {len(updated_firms)}")
    print(f"Changes to log: {len(changes_to_log)}")
    
    if dry_run:
        print("\n[DRY RUN] No changes will be made to database")
        
        if len(new_firms) > 0:
            print("\nSample new firms:")
            for firm in new_firms[:5]:
                print(f"  - {firm['broker_protocol_firm_name']}")
        
        if len(newly_withdrawn) > 0:
            print("\nSample withdrawn firms:")
            for firm_name in list(newly_withdrawn)[:5]:
                print(f"  - {firm_name}")
        
        if len(changes_to_log) > 0:
            print("\nSample changes:")
            for change in changes_to_log[:5]:
                print(f"  - {change['change_type']}: {change['broker_protocol_firm_name']}")
        
        return {
            'new_firms': len(new_firms),
            'withdrawn_firms': len(newly_withdrawn),
            'updated_firms': len(updated_firms),
            'changes': len(changes_to_log)
        }
    
    # Execute updates
    print("\n=== EXECUTING UPDATES ===")
    
    # Insert new firms
    if len(new_firms) > 0:
        print(f"Inserting {len(new_firms)} new firms...")
        new_df_to_insert = pd.DataFrame(new_firms)
        
        job_config = bigquery.LoadJobConfig(
            write_disposition='WRITE_APPEND',
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        )
        
        job = client.load_table_from_dataframe(new_df_to_insert, config.TABLE_MEMBERS, job_config=job_config)
        job.result()
        print(f"[SUCCESS] Inserted {len(new_firms)} new firms")
    
    # Update existing firms (including withdrawals)
    if len(updated_firms) > 0 or len(newly_withdrawn) > 0:
        print(f"Updating {len(updated_firms)} existing firms...")
        
        # Update regular firms
        for firm in updated_firms:
            update_fields = []
            update_fields.append(f"last_seen_date = DATE('{firm['last_seen_date']}')")
            update_fields.append(f"last_updated = TIMESTAMP('{firm['last_updated']}')")
            update_fields.append(f"scrape_run_id = '{firm['scrape_run_id']}'")
            
            # Add field updates if present
            # Fields that should NOT be updated (already handled or not in schema)
            skip_fields = ['broker_protocol_firm_name', 'last_seen_date', 'last_updated', 'scrape_run_id',
                          'matched_on_variant', 'top2_confidence', 'confidence_margin']  # New optional fields
            
            for key, value in firm.items():
                if key not in skip_fields:
                    if pd.notna(value):
                        if key == 'firm_crd_id':
                            # Ensure firm_crd_id is int
                            update_fields.append(f"{key} = {int(value)}")
                        elif isinstance(value, (int, float)):
                            # For float values, check if they should be int
                            if key in ['firm_crd_id']:
                                update_fields.append(f"{key} = {int(value)}")
                            else:
                                update_fields.append(f"{key} = {value}")
                        elif isinstance(value, bool):
                            update_fields.append(f"{key} = {str(value).upper()}")
                        elif isinstance(value, str):
                            # Escape single quotes and remove newlines that could break SQL
                            # Also escape backslashes to prevent issues
                            escaped_value = value.replace("\\", "\\\\").replace("'", "''").replace('\n', ' ').replace('\r', ' ')
                            # Truncate very long strings to avoid SQL issues
                            if len(escaped_value) > 10000:
                                escaped_value = escaped_value[:10000]
                            update_fields.append(f"{key} = '{escaped_value}'")
                        elif isinstance(value, (pd.Timestamp, datetime)):
                            update_fields.append(f"{key} = TIMESTAMP('{value}')")
                        elif hasattr(value, 'date'):  # date object
                            update_fields.append(f"{key} = DATE('{value}')")
            
            # Escape firm name for WHERE clause
            firm_name_escaped = firm['broker_protocol_firm_name'].replace("'", "''").replace('\n', ' ').replace('\r', ' ')
            
            update_query = f"""
            UPDATE `{config.TABLE_MEMBERS}`
            SET {', '.join(update_fields)}
            WHERE broker_protocol_firm_name = '{firm_name_escaped}'
            """
            
            client.query(update_query).result()
        
        # Mark withdrawn firms
        if len(newly_withdrawn) > 0:
            print(f"Marking {len(newly_withdrawn)} firms as withdrawn...")
            for firm_name in newly_withdrawn:
                firm_name_escaped = firm_name.replace("'", "''").replace('\n', ' ').replace('\r', ' ')
                update_query = f"""
                UPDATE `{config.TABLE_MEMBERS}`
                SET 
                    is_current_member = FALSE,
                    last_seen_date = DATE('{pd.Timestamp.now().date()}'),
                    last_updated = TIMESTAMP('{pd.Timestamp.now()}'),
                    scrape_run_id = '{scrape_run_id}'
                WHERE broker_protocol_firm_name = '{firm_name_escaped}'
                """
                client.query(update_query).result()
        
        print(f"[SUCCESS] Updated {len(updated_firms) + len(newly_withdrawn)} firms")
    
    # Log changes to history table
    if len(changes_to_log) > 0:
        print(f"Logging {len(changes_to_log)} changes to history table...")
        changes_df = pd.DataFrame(changes_to_log)
        
        job_config = bigquery.LoadJobConfig(
            write_disposition='WRITE_APPEND',
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        )
        
        job = client.load_table_from_dataframe(changes_df, config.TABLE_HISTORY, job_config=job_config)
        job.result()
        print(f"[SUCCESS] Logged {len(changes_to_log)} changes")
    
    # Update scrape log
    print("Updating scrape log...")
    log_entry = pd.DataFrame([{
        'scrape_run_id': scrape_run_id,
        'scrape_timestamp': pd.Timestamp.now(),
        'scrape_status': 'SUCCESS',
        'firms_downloaded': len(new_df),
        'firms_parsed': len(new_df),
        'firms_matched': (new_df['firm_crd_id'].notna()).sum(),
        'firms_needing_review': new_df['needs_manual_review'].sum(),
        'avg_match_confidence': new_df[new_df['firm_crd_id'].notna()]['match_confidence'].mean() if (new_df['firm_crd_id'].notna()).sum() > 0 else None,
        'new_firms': len(new_firms),
        'withdrawn_firms': len(newly_withdrawn),
        'info_updates': len([c for c in changes_to_log if c['change_type'] == 'INFO_UPDATED'])
    }])
    
    job = client.load_table_from_dataframe(log_entry, config.TABLE_SCRAPE_LOG)
    job.result()
    print(f"[SUCCESS] Updated scrape log")
    
    print("\n=== MERGE COMPLETE ===")
    
    return {
        'new_firms': len(new_firms),
        'withdrawn_firms': len(newly_withdrawn),
        'updated_firms': len(updated_firms),
        'changes': len(changes_to_log)
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Merge broker protocol data')
    parser.add_argument('data_file', help='Path to matched CSV file',
                       default=str(config.get_matched_csv_path()), nargs='?')
    parser.add_argument('--scrape-id', help='Scrape run ID', 
                       default=None)
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no changes)')
    
    args = parser.parse_args()
    
    try:
        merge_broker_protocol_data(args.data_file, args.scrape_id, args.dry_run)
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

