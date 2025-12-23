"""
Test script for broker_protocol_automation.py
Validates the complete automation pipeline.
"""

import pandas as pd
from google.cloud import bigquery
import config
from pathlib import Path


def validate_automation_results():
    """
    Validate results of automation run by checking BigQuery.
    """
    print("=== VALIDATING AUTOMATION RESULTS ===\n")
    
    client = bigquery.Client(project=config.GCP_PROJECT_ID)
    
    # Check 1: Match quality
    print("Check 1: Match Quality...")
    try:
        query = f"""
        SELECT * FROM `{config.TABLE_MEMBERS.replace('.broker_protocol_members', '.broker_protocol_match_quality')}`
        """
        quality = client.query(query).to_dataframe()
        print("  Match Quality:")
        print(quality.to_string())
        print("  [PASS] Match quality view accessible")
    except Exception as e:
        print(f"  [WARNING] Could not query match quality: {e}")
    
    # Check 2: Recent scrape log
    print("\nCheck 2: Recent Scrape Log...")
    query = f"""
    SELECT 
        scrape_run_id,
        scrape_timestamp,
        scrape_status,
        firms_matched,
        avg_match_confidence,
        new_firms,
        withdrawn_firms
    FROM `{config.TABLE_SCRAPE_LOG}`
    ORDER BY scrape_timestamp DESC
    LIMIT 3
    """
    log = client.query(query).to_dataframe()
    print("  Recent Scrape Logs:")
    print(log.to_string())
    print("  [PASS] Scrape log accessible")
    
    # Check 3: Recent changes
    print("\nCheck 3: Recent Changes...")
    try:
        query = f"""
        SELECT * FROM `{config.TABLE_MEMBERS.replace('.broker_protocol_members', '.broker_protocol_recent_changes')}`
        LIMIT 10
        """
        changes = client.query(query).to_dataframe()
        print(f"  Recent Changes: {len(changes)} records")
        if len(changes) > 0:
            print(changes[['broker_protocol_firm_name', 'change_type', 'change_date']].head(5).to_string())
        print("  [PASS] Recent changes view accessible")
    except Exception as e:
        print(f"  [WARNING] Could not query recent changes: {e}")
    
    # Check 4: Total firms
    print("\nCheck 4: Total Firms...")
    query = f"SELECT COUNT(*) as count FROM `{config.TABLE_MEMBERS}`"
    result = client.query(query).to_dataframe()
    total = result['count'].iloc[0]
    print(f"  Total firms in BigQuery: {total}")
    print(f"  [PASS] Total firms check complete")
    
    print("\n=== VALIDATION COMPLETE ===")


if __name__ == '__main__':
    validate_automation_results()

