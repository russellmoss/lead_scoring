"""
Score all prospects with V4 model and upload to BigQuery.
Run monthly BEFORE lead list generation.

Working Directory: Lead_List_Generation
Usage: python scripts/score_prospects_monthly.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from google.cloud import bigquery
import pickle
import json
from datetime import datetime
import xgboost as xgb

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
# Working directory (where this script runs from)
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation")

# V4 Model files (read-only, from Version-4)
V4_MODEL_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4\models\v4.0.0")
V4_FEATURES_FILE = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4\data\processed\final_features.json")

# Output directories (in Lead_List_Generation)
EXPORTS_DIR = WORKING_DIR / "exports"
LOGS_DIR = WORKING_DIR / "logs"

# Ensure output directories exist
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# BIGQUERY CONFIGURATION
# ============================================================================
PROJECT_ID = "savvy-gtm-analytics"
DATASET = "ml_features"
FEATURES_TABLE = "v4_prospect_features"
SCORES_TABLE = "v4_prospect_scores"

# Deprioritization threshold
DEPRIORITIZE_PERCENTILE = 20

def load_model():
    """Load the V4 XGBoost model from Version-4 directory."""
    model_path = V4_MODEL_DIR / "model.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    print(f"[INFO] Loaded model from {model_path}")
    return model

def load_features_list():
    """Load the final feature list from Version-4 directory."""
    if not V4_FEATURES_FILE.exists():
        raise FileNotFoundError(f"Features file not found: {V4_FEATURES_FILE}")
    
    with open(V4_FEATURES_FILE, 'r') as f:
        data = json.load(f)
    features = data['final_features']
    print(f"[INFO] Loaded {len(features)} features")
    return features

def fetch_prospect_features(client):
    """Fetch prospect features from BigQuery."""
    query = f"""
    SELECT *
    FROM `{PROJECT_ID}.{DATASET}.{FEATURES_TABLE}`
    """
    print(f"[INFO] Fetching features from {FEATURES_TABLE}...")
    df = client.query(query).to_dataframe()
    print(f"[INFO] Loaded {len(df):,} prospects")
    return df

def prepare_features(df, feature_list):
    """Prepare features for model inference."""
    X = df.copy()
    
    # Select only required features
    missing = set(feature_list) - set(X.columns)
    if missing:
        raise ValueError(f"Missing features: {missing}")
    
    X = X[feature_list].copy()
    
    # Encode categoricals (matching training logic)
    categorical_cols = ['tenure_bucket', 'experience_bucket', 'mobility_tier', 'firm_stability_tier']
    for col in categorical_cols:
        if col in X.columns:
            # Convert to category and then to codes
            X[col] = X[col].astype('category').cat.codes
            # Replace -1 (missing) with 0
            X[col] = X[col].replace(-1, 0)
    
    # Fill NaN
    X = X.fillna(0)
    
    # Ensure numeric types
    for col in X.columns:
        if X[col].dtype == 'object':
            try:
                X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)
            except:
                pass
    
    return X

def score_prospects(model, X):
    """Generate V4 scores."""
    dmatrix = xgb.DMatrix(X)
    scores = model.predict(dmatrix)
    print(f"[INFO] Scored {len(scores):,} prospects")
    print(f"[INFO] Score range: {scores.min():.4f} - {scores.max():.4f}")
    return scores

def calculate_percentiles(scores):
    """Calculate percentile ranks (1-100)."""
    percentiles = pd.Series(scores).rank(pct=True, method='min') * 100
    return percentiles.astype(int).values

def upload_scores(client, df_scores):
    """Upload scores to BigQuery."""
    table_id = f"{PROJECT_ID}.{DATASET}.{SCORES_TABLE}"
    
    # Configure job
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("crd", "INT64"),
            bigquery.SchemaField("v4_score", "FLOAT64"),
            bigquery.SchemaField("v4_percentile", "INT64"),
            bigquery.SchemaField("v4_deprioritize", "BOOLEAN"),
            bigquery.SchemaField("scored_at", "TIMESTAMP"),
        ]
    )
    
    job = client.load_table_from_dataframe(df_scores, table_id, job_config=job_config)
    job.result()
    print(f"[INFO] Uploaded {len(df_scores):,} scores to {table_id}")

def main():
    print("=" * 70)
    print("V4 MONTHLY PROSPECT SCORING")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Working Directory: {WORKING_DIR}")
    print("=" * 70)
    
    # Initialize
    client = bigquery.Client(project=PROJECT_ID)
    model = load_model()
    feature_list = load_features_list()
    
    # Fetch features
    df = fetch_prospect_features(client)
    
    # Prepare and score
    X = prepare_features(df, feature_list)
    scores = score_prospects(model, X)
    
    # Calculate percentiles
    percentiles = calculate_percentiles(scores)
    
    # Build output DataFrame
    df_scores = pd.DataFrame({
        'crd': df['crd'].astype(int),
        'v4_score': scores,
        'v4_percentile': percentiles,
        'v4_deprioritize': percentiles <= DEPRIORITIZE_PERCENTILE,
        'scored_at': datetime.now()
    })
    
    # Upload to BigQuery
    upload_scores(client, df_scores)
    
    # Summary
    summary = f"""
{"=" * 70}
SCORING SUMMARY
{"=" * 70}
Total prospects scored: {len(df_scores):,}
Deprioritize (bottom {DEPRIORITIZE_PERCENTILE}%): {df_scores['v4_deprioritize'].sum():,}
Prioritize (top {100-DEPRIORITIZE_PERCENTILE}%): {(~df_scores['v4_deprioritize']).sum():,}
Score Statistics:
  Mean: {df_scores['v4_score'].mean():.4f}
  Min: {df_scores['v4_score'].min():.4f}
  Max: {df_scores['v4_score'].max():.4f}
  Median: {df_scores['v4_score'].median():.4f}
Percentile Distribution:
  Min: {df_scores['v4_percentile'].min()}
  Max: {df_scores['v4_percentile'].max()}
  Mean: {df_scores['v4_percentile'].mean():.1f}
{"=" * 70}
"""
    print(summary)
    
    # Log to file
    log_file = LOGS_DIR / "EXECUTION_LOG.md"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n## Step 2: V4 Scoring - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Status**: ✅ SUCCESS\n\n")
        f.write(f"**Results:**\n")
        f.write(f"- Total scored: {len(df_scores):,}\n")
        f.write(f"- Deprioritize (bottom {DEPRIORITIZE_PERCENTILE}%): {df_scores['v4_deprioritize'].sum():,}\n")
        f.write(f"- Prioritize (top {100-DEPRIORITIZE_PERCENTILE}%): {(~df_scores['v4_deprioritize']).sum():,}\n")
        f.write(f"- Score range: {df_scores['v4_score'].min():.4f} - {df_scores['v4_score'].max():.4f}\n")
        f.write(f"- Average score: {df_scores['v4_score'].mean():.4f}\n")
        f.write(f"- Average percentile: {df_scores['v4_percentile'].mean():.1f}\n")
        f.write(f"\n**Table Created**: `{PROJECT_ID}.{DATASET}.{SCORES_TABLE}`\n\n")
        f.write("---\n\n")
    print(f"[INFO] Logged to {log_file}")
    
    return df_scores

if __name__ == "__main__":
    main()

