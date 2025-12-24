"""
Score Historical Leads with V4 Model

Working Directory: C:/Users/russe/Documents/Lead Scoring/V3+V4_testing
"""

import pandas as pd
import numpy as np
from pathlib import Path
from google.cloud import bigquery
import pickle
import json
from datetime import datetime

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
WORKING_DIR = Path("C:/Users/russe/Documents/Lead Scoring/V3+V4_testing")
V4_MODEL_DIR = Path("C:/Users/russe/Documents/Lead Scoring/Version-4/models/v4.0.0")
V4_FEATURES_FILE = Path("C:/Users/russe/Documents/Lead Scoring/Version-4/data/processed/final_features.json")

LOGS_DIR = WORKING_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "savvy-gtm-analytics"

def load_model():
    """Load V4 XGBoost model."""
    model_path = V4_MODEL_DIR / "model.pkl"
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    print(f"[INFO] Loaded model from {model_path}")
    return model

def load_features_list():
    """Load V4 feature list."""
    with open(V4_FEATURES_FILE, 'r') as f:
        data = json.load(f)
    features = data['final_features']
    print(f"[INFO] Loaded {len(features)} features")
    return features

def fetch_historical_features(client):
    """Fetch historical lead features from BigQuery."""
    query = """
    SELECT *
    FROM `savvy-gtm-analytics.ml_features.historical_leads_v4_features`
    """
    df = client.query(query).to_dataframe()
    print(f"[INFO] Loaded {len(df):,} historical leads with features")
    return df

def prepare_features(df, feature_list):
    """Prepare features for model scoring."""
    X = df.copy()
    
    # Encode categoricals
    categorical_cols = ['tenure_bucket', 'experience_bucket', 'mobility_tier', 'firm_stability_tier']
    for col in categorical_cols:
        if col in X.columns:
            X[col] = X[col].astype('category').cat.codes.replace(-1, 0)
    
    # Select only required features
    missing = set(feature_list) - set(X.columns)
    if missing:
        print(f"[WARNING] Missing features: {missing}")
        for m in missing:
            X[m] = 0
    
    X = X[feature_list].copy()
    X = X.fillna(0)
    
    return X

def score_leads(model, X):
    """Generate V4 scores (probability of conversion)."""
    import xgboost as xgb
    # XGBoost model is a Booster, need to use DMatrix
    dmatrix = xgb.DMatrix(X)
    scores = model.predict(dmatrix)  # Already returns probabilities for binary:logistic
    return scores

def calculate_percentiles(scores):
    """Calculate percentile ranks."""
    percentiles = pd.Series(scores).rank(pct=True, method='min') * 100
    return percentiles.astype(int).values

def upload_scores(client, df_scores):
    """Upload scores to BigQuery."""
    table_id = f"{PROJECT_ID}.ml_features.historical_leads_v4_scores"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )
    
    job = client.load_table_from_dataframe(df_scores, table_id, job_config=job_config)
    job.result()
    print(f"[INFO] Uploaded {len(df_scores):,} scores to {table_id}")

def main():
    print("=" * 70)
    print("SCORE HISTORICAL LEADS WITH V4 MODEL")
    print("=" * 70)
    
    client = bigquery.Client(project=PROJECT_ID)
    model = load_model()
    feature_list = load_features_list()
    
    # Fetch and prepare features
    df = fetch_historical_features(client)
    X = prepare_features(df, feature_list)
    
    # Score
    scores = score_leads(model, X)
    percentiles = calculate_percentiles(scores)
    
    # Build output
    df_scores = pd.DataFrame({
        'lead_id': df['lead_id'],
        'crd': df['advisor_crd'],
        'v4_score': scores,
        'v4_percentile': percentiles,
        'v4_deprioritize': percentiles <= 20,
        'scored_at': datetime.now()
    })
    
    # Upload
    upload_scores(client, df_scores)
    
    # Log
    log_path = LOGS_DIR / "INVESTIGATION_LOG.md"
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n\n## Step 4: V4 Scoring - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Total scored: {len(df_scores):,}\n")
        f.write(f"- Score range: {scores.min():.4f} - {scores.max():.4f}\n")
        f.write(f"- Avg score: {scores.mean():.4f}\n")
        f.write(f"- Deprioritize (bottom 20%): {df_scores['v4_deprioritize'].sum():,}\n")
    
    print("\n[INFO] V4 scoring complete!")
    return df_scores

if __name__ == "__main__":
    main()

