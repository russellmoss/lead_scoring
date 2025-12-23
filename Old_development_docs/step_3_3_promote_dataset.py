"""
Step 3.3: Promote New Data Build (Atomic View Update)

This script creates/updates the production view to point to the latest validated training dataset.
"""

from google.cloud import bigquery
import os

# Configuration
PROJECT_ID = "savvy-gtm-analytics"
DATASET_ID = "LeadScoring"
VERSION = "20251104_2217"  # From Step 3.2
TRAINING_TABLE = f"step_3_3_training_dataset_v6_{VERSION}"
VIEW_NAME = "v_latest_training_dataset_v6"

def create_production_view():
    """Create or replace the production view pointing to the latest training dataset."""
    client = bigquery.Client(project=PROJECT_ID)
    
    # SQL to create/update the view
    sql = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.{VIEW_NAME}` AS
    SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TRAINING_TABLE}`;
    """
    
    print(f"Creating/updating view: {VIEW_NAME}")
    print(f"Pointing to table: {TRAINING_TABLE}")
    
    try:
        query_job = client.query(sql)
        query_job.result()  # Wait for completion
        print(f"[SUCCESS] View {VIEW_NAME} created/updated successfully")
        
        # Validate the view
        validate_view(client)
        
    except Exception as e:
        print(f"[ERROR] Failed to create view: {str(e)}")
        raise

def validate_view(client):
    """Validate that the view is working correctly."""
    print("\n" + "="*60)
    print("Validating Production View")
    print("="*60)
    
    # Check row count
    sql = f"""
    SELECT COUNT(*) as row_count
    FROM `{PROJECT_ID}.{DATASET_ID}.{VIEW_NAME}`
    """
    
    try:
        query_job = client.query(sql)
        result = query_job.result()
        row_count = list(result)[0].row_count
        
        print(f"[VALIDATION] View row count: {row_count:,}")
        
        # Check column count
        sql = f"""
        SELECT COUNT(*) as column_count
        FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{VIEW_NAME}'
        """
        query_job = client.query(sql)
        result = query_job.result()
        column_count = list(result)[0].column_count
        
        print(f"[VALIDATION] View column count: {column_count}")
        
        # Check target_label distribution
        sql = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN target_label = 1 THEN 1 END) as positive,
            COUNT(CASE WHEN target_label = 0 THEN 1 END) as negative,
            ROUND(COUNT(CASE WHEN target_label = 1 THEN 1 END) / COUNT(*) * 100, 2) as positive_pct
        FROM `{PROJECT_ID}.{DATASET_ID}.{VIEW_NAME}`
        """
        query_job = client.query(sql)
        result = query_job.result()
        row = list(result)[0]
        
        print(f"[VALIDATION] Target distribution:")
        print(f"  Total samples: {row.total:,}")
        print(f"  Positive (1): {row.positive:,} ({row.positive_pct}%)")
        print(f"  Negative (0): {row.negative:,}")
        
        # Check for NULLs in key features
        sql = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(FA_CRD__c) as has_rep_crd,
            COUNT(RIAFirmCRD) as has_firm_crd,
            COUNT(is_veteran_advisor) as has_veteran_flag,
            COUNT(license_count) as has_license_count,
            COUNT(total_reps) as has_total_reps
        FROM `{PROJECT_ID}.{DATASET_ID}.{VIEW_NAME}`
        """
        query_job = client.query(sql)
        result = query_job.result()
        row = list(result)[0]
        
        print(f"\n[VALIDATION] Key feature coverage:")
        print(f"  FA_CRD__c: {row.has_rep_crd:,} / {row.total:,} ({row.has_rep_crd/row.total*100:.1f}%)")
        print(f"  RIAFirmCRD: {row.has_firm_crd:,} / {row.total:,} ({row.has_firm_crd/row.total*100:.1f}%)")
        print(f"  is_veteran_advisor: {row.has_veteran_flag:,} / {row.total:,} ({row.has_veteran_flag/row.total*100:.1f}%)")
        print(f"  license_count: {row.has_license_count:,} / {row.total:,} ({row.has_license_count/row.total*100:.1f}%)")
        print(f"  total_reps: {row.has_total_reps:,} / {row.total:,} ({row.has_total_reps/row.total*100:.1f}%)")
        
        print("\n[SUCCESS] View validation complete!")
        print(f"[READY] Production view is ready for model training")
        
    except Exception as e:
        print(f"[ERROR] Validation failed: {str(e)}")
        raise

if __name__ == "__main__":
    print("="*60)
    print("Step 3.3: Promote New Data Build")
    print("="*60)
    print()
    
    create_production_view()
    
    print("\n" + "="*60)
    print("Step 3.3 Complete - Ready for Phase 2 (Model Training)")
    print("="*60)

