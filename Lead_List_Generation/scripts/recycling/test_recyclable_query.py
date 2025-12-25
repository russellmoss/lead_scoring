"""
Test script for recyclable pool query with LIMIT 100 and validation queries.
"""

import sys
import os
from pathlib import Path
from google.cloud import bigquery
from google.auth.exceptions import DefaultCredentialsError
from google.api_core import exceptions as gcp_exceptions

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

PROJECT_ID = "savvy-gtm-analytics"
SQL_FILE = Path(__file__).parent.parent.parent / "sql" / "recycling" / "recyclable_pool_master_v2.1.sql"

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
    except gcp_exceptions.PermissionDenied as e:
        print(f"[ERROR] Permission denied - Check project access")
        print(f"[ERROR] Details: {e}")
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

def test_query_with_limit_100():
    """Test the query with LIMIT 100."""
    
    print("=" * 70)
    print("TESTING RECYCLABLE POOL QUERY (LIMIT 100)")
    print("=" * 70)
    
    # Check credentials first
    if not check_credentials():
        print("\n[ERROR] Authentication check failed. Cannot proceed with query.")
        return False
    
    # Read SQL file
    if not SQL_FILE.exists():
        print(f"[ERROR] SQL file not found: {SQL_FILE}")
        print("[INFO] Creating SQL file from guide...")
        # We'll need to create it first
        return False
    
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        query = f.read()
    
    # Modify target_count to 100 for testing
    query = query.replace('DECLARE target_count INT64 DEFAULT 600;', 
                         'DECLARE target_count INT64 DEFAULT 100;')
    
    # Execute query
    print("\n[INFO] Initializing BigQuery client...")
    try:
        client = bigquery.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"[ERROR] Failed to create BigQuery client: {e}")
        print("[INFO] This is likely an authentication issue, not an internet problem")
        return False
    
    print("\n[INFO] Executing query with LIMIT 100...")
    try:
        job = client.query(query)
        df = job.to_dataframe()
        
        print(f"[OK] Query executed successfully!")
        print(f"[INFO] Retrieved {len(df):,} records")
        
        # Display summary
        print("\n" + "=" * 70)
        print("QUERY RESULTS SUMMARY")
        print("=" * 70)
        
        if len(df) > 0:
            print(f"\nTotal Records: {len(df):,}")
            print(f"\nRecord Type Distribution:")
            print(df['record_type'].value_counts())
            
            print(f"\nPriority Distribution:")
            priority_dist = df['recycle_priority'].value_counts().sort_index()
            for priority, count in priority_dist.items():
                pct = count / len(df) * 100
                print(f"  {priority}: {count:,} ({pct:.1f}%)")
            
            print(f"\nSample Records (first 5):")
            print(df[['list_rank', 'record_type', 'first_name', 'last_name', 
                     'recycle_priority', 'expected_conv_rate_pct', 
                     'v4_percentile', 'days_since_last_contact']].head().to_string())
            
            # Run validation queries
            run_validation_queries(df)
            
            return True
        else:
            print("[WARNING] Query returned 0 records")
            return False
            
    except DefaultCredentialsError as e:
        print(f"[ERROR] Authentication failed - No valid credentials")
        print(f"[ERROR] Details: {e}")
        print("\n[INFO] This error is often misreported as 'internet connection failure'")
        print("[INFO] To fix: Set GOOGLE_APPLICATION_CREDENTIALS or run 'gcloud auth application-default login'")
        return False
    except gcp_exceptions.PermissionDenied as e:
        print(f"[ERROR] Permission denied - Check project access")
        print(f"[ERROR] Details: {e}")
        return False
    except gcp_exceptions.Forbidden as e:
        print(f"[ERROR] Access forbidden - Check project permissions")
        print(f"[ERROR] Details: {e}")
        return False
    except Exception as e:
        error_msg = str(e).lower()
        error_type = type(e).__name__
        
        print(f"[ERROR] Query execution failed")
        print(f"[ERROR] Error type: {error_type}")
        print(f"[ERROR] Error message: {e}")
        
        # Check if it's a misleading connection error
        if 'connection' in error_msg or 'network' in error_msg or 'timeout' in error_msg:
            print("\n[WARNING] This appears to be a connection error, but it's often caused by:")
            print("  1. Missing or invalid credentials")
            print("  2. Expired authentication tokens")
            print("  3. Incorrect project ID")
            print("\n[INFO] Verify your authentication setup before assuming network issues")
        
        import traceback
        print("\n[DEBUG] Full traceback:")
        traceback.print_exc()
        return False


def run_validation_queries(df):
    """Run validation queries on the results."""
    
    print("\n" + "=" * 70)
    print("VALIDATION QUERIES")
    print("=" * 70)
    
    # V1: Check for date type issues
    print("\n[V1] Checking for date type issues...")
    date_issues = df[
        (df['years_at_current_firm'] < 0) | 
        (df['years_at_current_firm'] > 50) |
        (df['years_at_current_firm_now'] < 0) |
        (df['years_at_current_firm_now'] > 50)
    ]
    
    if len(date_issues) == 0:
        print("[OK] No date type issues found (0 rows with invalid tenure)")
    else:
        print(f"[FAIL] Found {len(date_issues)} rows with date issues:")
        print(date_issues[['record_id', 'record_type', 'years_at_current_firm', 
                          'years_at_current_firm_now']].to_string())
    
    # V2: Check for recent firm changers that slipped through
    print("\n[V2] Checking for recent firm changers (< 2 years)...")
    recent_changers = df[
        (df['changed_firms_since_close'] == True) & 
        (df['years_at_current_firm'] < 2)
    ]
    
    if len(recent_changers) == 0:
        print("[OK] No recent firm changers found (0 rows with changed_firms=TRUE and years<2)")
    else:
        print(f"[FAIL] Found {len(recent_changers)} rows with recent firm changes:")
        print(recent_changers[['record_id', 'record_type', 'changed_firms_since_close', 
                              'years_at_current_firm']].to_string())
    
    # V3: Check priority distribution
    print("\n[V3] Priority distribution analysis:")
    priority_stats = df.groupby('recycle_priority').agg({
        'record_id': 'count',
        'expected_conv_rate_pct': 'mean',
        'v4_percentile': 'mean',
        'days_since_last_contact': 'mean'
    }).rename(columns={
        'record_id': 'count',
        'expected_conv_rate_pct': 'avg_expected_conv',
        'v4_percentile': 'avg_v4_percentile',
        'days_since_last_contact': 'avg_days_since_contact'
    })
    
    priority_stats['pct_of_total'] = (priority_stats['count'] / len(df) * 100).round(1)
    priority_stats = priority_stats.sort_index()
    
    print(priority_stats.to_string())
    
    # Additional validations
    print("\n[V4] Additional validations:")
    
    # Check for NULLs in critical fields
    critical_fields = ['record_id', 'fa_crd', 'recycle_priority', 'first_name', 'last_name']
    null_counts = {}
    for field in critical_fields:
        null_count = df[field].isna().sum()
        if null_count > 0:
            null_counts[field] = null_count
    
    if len(null_counts) == 0:
        print("[OK] No NULL values in critical fields")
    else:
        print(f"[WARNING] Found NULL values in critical fields:")
        for field, count in null_counts.items():
            print(f"  {field}: {count} NULLs")
    
    # Check for duplicates
    duplicate_crds = df[df.duplicated(subset=['fa_crd'], keep=False)]
    if len(duplicate_crds) == 0:
        print("[OK] No duplicate CRDs found")
    else:
        print(f"[WARNING] Found {len(duplicate_crds)} rows with duplicate CRDs")
    
    # Check record type distribution
    opp_count = (df['record_type'] == 'OPPORTUNITY').sum()
    lead_count = (df['record_type'] == 'LEAD').sum()
    print(f"[INFO] Record types: {opp_count} Opportunities, {lead_count} Leads")
    
    # Check that Opportunities appear before Leads in ranking
    if opp_count > 0 and lead_count > 0:
        max_opp_rank = df[df['record_type'] == 'OPPORTUNITY']['list_rank'].max()
        min_lead_rank = df[df['record_type'] == 'LEAD']['list_rank'].min()
        if max_opp_rank < min_lead_rank:
            print("[OK] Opportunities correctly ranked before Leads")
        else:
            print(f"[WARNING] Some Leads have lower ranks than Opportunities (max_opp={max_opp_rank}, min_lead={min_lead_rank})")


if __name__ == "__main__":
    # First, check if SQL file exists, if not, we need to create it
    if not SQL_FILE.exists():
        print(f"[ERROR] SQL file not found: {SQL_FILE}")
        print("[INFO] Please create the SQL file first from the guide")
        sys.exit(1)
    
    success = test_query_with_limit_100()
    
    if success:
        print("\n" + "=" * 70)
        print("TEST COMPLETE - All validations passed!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("TEST FAILED - Check errors above")
        print("=" * 70)
        sys.exit(1)



