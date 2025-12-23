#!/usr/bin/env python3
"""
Step 1.2: Upload RIARepDataFeed CSV Files to BigQuery Raw Staging Tables
Uploads 8 quarterly RIARepDataFeed CSV files to BigQuery with _raw suffix
"""

import pandas as pd
from google.cloud import bigquery
import os
import sys
from datetime import datetime
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())


def get_quarter_from_date(date_str):
    """
    Extract quarter from date string (YYYYMMDD format)
    Returns: (year, quarter) tuple, e.g., (2024, 1)
    """
    date_obj = datetime.strptime(date_str, '%Y%m%d')
    year = date_obj.year
    quarter = (date_obj.month - 1) // 3 + 1
    return (year, quarter)

def get_date_from_string(date_str):
    """
    Convert YYYYMMDD string to DATE object
    Returns: datetime.date object
    """
    return datetime.strptime(date_str, '%Y%m%d').date()


def upload_ria_reps_file(csv_path, project_id="savvy-gtm-analytics"):
    """
    Upload a single RIARepDataFeed CSV file to BigQuery raw staging table
    
    Args:
        csv_path: Path to RIARepDataFeed_YYYYMMDD.csv file
        project_id: BigQuery project ID
    """
    csv_file = Path(csv_path)
    
    if not csv_file.exists():
        print(f"[ERROR] File {csv_path} not found!")
        return False
    
    # Extract date from filename (RIARepDataFeed_YYYYMMDD.csv)
    filename = csv_file.stem  # Get filename without extension
    parts = filename.split('_')
    if len(parts) < 2:
        print(f"[ERROR] Cannot parse date from filename: {filename}")
        return False
    
    date_str = parts[1]  # Should be YYYYMMDD
    snapshot_date = get_date_from_string(date_str)  # Convert to DATE object
    
    # Use date-based table name (YYYYMMDD format)
    table_name = f"snapshot_reps_{date_str}_raw"
    table_id = f"{project_id}.LeadScoring.{table_name}"
    
    print(f"[START] Uploading {csv_file.name} to {table_name}")
    print(f"[INFO] File date: {date_str} → snapshot_at will be: {snapshot_date}")
    
    try:
        # Read CSV with proper type inference
        print("[READ] Reading CSV file...")
        df = pd.read_csv(
            csv_path,
            low_memory=False,  # Critical for proper type inference
            na_values=['', 'NA', 'N/A', 'null', 'NULL', 'None'],
            keep_default_na=True,
            encoding='utf-8'
        )
        
        print(f"[SUCCESS] Successfully read {len(df):,} records with {len(df.columns)} columns")
        
        # Clean column names for BigQuery compatibility (if needed)
        # Note: We'll keep original column names for now, transformation happens in Step 1.5
        print("[INFO] Column names will be preserved (transformation in Step 1.5)")
        
        # Upload to BigQuery staging table
        print("[BIGQUERY] Connecting to BigQuery...")
        client = bigquery.Client(project=project_id)
        
        print(f"[TARGET] Target table: {table_id}")
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",  # Replace existing data
            autodetect=True,  # Auto-detect schema from DataFrame
            create_disposition="CREATE_IF_NEEDED"  # Create table if doesn't exist
        )
        
        print("[UPLOAD] Uploading to BigQuery...")
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        
        # Wait for job to complete
        print("[WAIT] Waiting for upload to complete...")
        job.result()
        
        # Get table info to confirm
        table = client.get_table(table_id)
        print(f"[SUCCESS] Successfully uploaded {table.num_rows:,} rows to {table_id}")
        print(f"[INFO] Table schema: {len(table.schema)} columns")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error uploading {csv_file.name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main upload function for all 8 RIARepDataFeed files"""
    
    print("=" * 70)
    print("Step 1.2: Upload RIARepDataFeed CSV Files to BigQuery Raw Staging")
    print("=" * 70)
    
    # Find all RIARepDataFeed CSV files - upload ALL of them (no filtering)
    discovery_data_path = Path("discovery_data")
    ria_files = list(discovery_data_path.glob("RIARepDataFeed_*.csv"))
    
    if len(ria_files) != 8:
        print(f"[WARNING] Expected 8 files, found {len(ria_files)}")
    
    # Process ALL files - each gets its own table with date-based naming
    files = []  # List of (file_path, date_str, snapshot_date)
    
    print("\n[INFO] Processing all RIARepDataFeed files (no filtering):")
    for file_path in sorted(ria_files):
        filename = file_path.stem
        parts = filename.split('_')
        if len(parts) >= 2:
            date_str = parts[1]  # YYYYMMDD format
            snapshot_date = get_date_from_string(date_str)  # Convert to DATE object
            files.append((str(file_path), date_str, snapshot_date))
            print(f"  ✓ {filename} → date: {date_str} → snapshot_at: {snapshot_date}")
    
    if not files:
        print("[ERROR] No RIARepDataFeed CSV files found in discovery_data/")
        sys.exit(1)
    
    # Verify all files exist
    print("\n[VERIFY] Checking files exist...")
    missing_files = []
    for file_path, _, _ in files:  # Unpack (file_path, date_str, snapshot_date)
        if not Path(file_path).exists():
            missing_files.append(file_path)
            print(f"  ❌ Missing: {file_path}")
        else:
            print(f"  ✅ Found: {file_path}")
    
    if missing_files:
        print(f"\n[ERROR] {len(missing_files)} file(s) not found. Please check file paths.")
        sys.exit(1)
    
    print(f"\n[INFO] Found {len(files)} file(s). Starting upload...\n")
    
    # Show file mapping with snapshot dates
    print("\n[FILE MAPPING WITH SNAPSHOT DATES]")
    for file_path, date_str, snapshot_date in files:
        print(f"  {Path(file_path).name} → snapshot_reps_{date_str}_raw (snapshot_at: {snapshot_date})")
    print()
    
    success_count = 0
    failed_files = []
    
    for file_path, date_str, snapshot_date in files:
        print("\n" + "-" * 70)
        
        success = upload_ria_reps_file(file_path)
        
        if success:
            success_count += 1
            print(f"[✓] {Path(file_path).name} uploaded successfully to snapshot_reps_{date_str}_raw")
            print(f"[INFO] Snapshot date: {snapshot_date} (will be used as snapshot_at in Step 1.5)")
        else:
            failed_files.append(file_path)
            print(f"[✗] {Path(file_path).name} upload failed")
    
    # Summary
    print("\n" + "=" * 70)
    print(f"[SUMMARY] Upload Summary: {success_count}/{len(files)} files successful")
    print("=" * 70)
    
    if success_count == len(files):
        print(f"[COMPLETE] ✅ All {len(files)} RIARepDataFeed files uploaded successfully!")
        print("\nNext Steps:")
        print("1. Verify uploads in BigQuery Console")
        print("2. Run Step 1.3 validation checklist")
        print("3. Proceed to Step 1.5 (Transform Raw CSV to Standardized Schema)")
        print(f"\nNote: Each file has its own table with date-based naming (snapshot_reps_YYYYMMDD_raw)")
        print("      The snapshot_at date will be set from the filename date in Step 1.5")
    else:
        print(f"[WARNING] ⚠️  {len(failed_files)} file(s) failed to upload:")
        for file_path in failed_files:
            print(f"  - {file_path}")
        print("\nPlease review errors above and retry failed uploads.")
        sys.exit(1)


if __name__ == "__main__":
    main()

