"""
Execute the training dataset SQL via BigQuery Python client
"""
from google.cloud import bigquery
import json

# Read the SQL file
with open('create_training_dataset_full.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

# Initialize BigQuery client
client = bigquery.Client(project='savvy-gtm-analytics')

print(f"Executing SQL query to create training dataset table...")
print(f"SQL length: {len(sql)} characters")

# Execute the query
query_job = client.query(sql, location='northamerica-northeast2')
result = query_job.result()  # Wait for the job to complete

print(f"Query completed!")
print(f"Rows created: {query_job.num_dml_affected_rows if hasattr(query_job, 'num_dml_affected_rows') else 'N/A'}")
print(f"Table created: savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_hybrid")

