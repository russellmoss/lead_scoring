#!/usr/bin/env python3
"""
Discovery Data Upload Script for Lead Scoring Pipeline
Uploads T1, T2, T3 MarketPro CSV files to BigQuery staging tables
"""

import pandas as pd
from google.cloud import bigquery
import os
import sys
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

def upload_discovery_territory(territory, csv_path, project_id="savvy-gtm-analytics"):
    """ONE-TIME helper: Upload MarketPro CSV to BigQuery staging table"""
    
    print(f"[START] Starting upload for {territory.upper()} territory...")
    print(f"[FILE] Source file: {csv_path}")
    
    # Check if file exists
    if not os.path.exists(csv_path):
        print(f"[ERROR] File {csv_path} not found!")
        return False
    
    try:
        # Read CSV with proper type inference (matching your plan's requirements)
        print("[READ] Reading CSV file...")
        df = pd.read_csv(
            csv_path,
            low_memory=False,  # Critical for proper type inference
            na_values=['', 'NA', 'N/A', 'null', 'NULL', 'None'],
            keep_default_na=True
        )
        
        print(f"[SUCCESS] Successfully read {len(df):,} records with {len(df.columns)} columns")
        
        # Clean column names for BigQuery compatibility
        print("[CLEAN] Cleaning column names for BigQuery...")
        df.columns = df.columns.str.replace('/', '_').str.replace(' ', '_').str.replace('-', '_')
        df.columns = df.columns.str.replace('(', '').str.replace(')', '').str.replace('.', '_')
        df.columns = df.columns.str.replace('__', '_')  # Remove double underscores
        
        print(f"[CLEAN] Cleaned {len(df.columns)} column names")
        
        # Upload to BigQuery staging table
        print("[BIGQUERY] Connecting to BigQuery...")
        client = bigquery.Client(project=project_id)
        table_id = f"{project_id}.LeadScoring.staging_discovery_{territory}"
        
        print(f"[TARGET] Target table: {table_id}")
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",  # Replace existing data
            autodetect=True,  # Auto-detect schema
            create_disposition="CREATE_IF_NEEDED"  # Create table if doesn't exist
        )
        
        print("[UPLOAD] Uploading to BigQuery...")
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        
        # Wait for job to complete
        print("[WAIT] Waiting for upload to complete...")
        job.result()
        
        print(f"[SUCCESS] Successfully uploaded {len(df):,} rows to {table_id}")
        
        # Get table info to confirm
        table = client.get_table(table_id)
        print(f"[INFO] Table info: {table.num_rows:,} rows, {len(table.schema)} columns")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error uploading {territory}: {str(e)}")
        return False

def main():
    """Main upload function for all territories"""
    
    print("Discovery Data Upload to BigQuery")
    print("=" * 50)
    
    # Define territories and their file paths
    territories = {
        't1': 'discovery_data/discovery_t1_2025_10.csv',
        't2': 'discovery_data/discovery_t2_2025_10.csv', 
        't3': 'discovery_data/discovery_t3_2025_10.csv'
    }
    
    success_count = 0
    total_count = len(territories)
    
    for territory, csv_path in territories.items():
        print(f"\nProcessing {territory.upper()} Territory")
        print("-" * 30)
        
        success = upload_discovery_territory(territory, csv_path)
        
        if success:
            success_count += 1
            print(f"[SUCCESS] {territory.upper()} upload completed successfully!")
        else:
            print(f"[FAILED] {territory.upper()} upload failed!")
    
    print("\n" + "=" * 50)
    print(f"[SUMMARY] Upload Summary: {success_count}/{total_count} territories successful")
    
    if success_count == total_count:
        print("[COMPLETE] All discovery data uploaded successfully!")
        print("\nNext Steps:")
        print("1. Run BigQuery data processing pipeline")
        print("2. Execute feature engineering SQL")
        print("3. Validate data quality metrics")
    else:
        print("[WARNING] Some uploads failed. Please check errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
