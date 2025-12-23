"""
Execute Phase 1.1 Feature Engineering SQL
"""
from google.cloud import bigquery
import sys

# Initialize BigQuery client
client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

# Read SQL file
print("Reading SQL file...")
with open('phase1_1_complete.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

print(f"SQL loaded: {len(sql)} characters")
print("Executing SQL query...")
print("This may take several minutes...")

# Execute query
try:
    job = client.query(sql)
    result = job.result()  # Wait for completion
    
    print("Query completed successfully!")
    print(f"Table created: savvy-gtm-analytics.ml_features.lead_scoring_features_pit")
    
    # Get row count
    count_query = "SELECT COUNT(*) as row_count FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`"
    count_job = client.query(count_query)
    count_result = count_job.result()
    for row in count_result:
        print(f"Rows in table: {row.row_count}")
        
except Exception as e:
    print(f"Error executing query: {e}")
    sys.exit(1)

