"""
Phase 7.3: Batch Scoring for Production
Scores active leads from the last 30 days using LeadScorerV2
"""

import sys
from pathlib import Path
# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from google.cloud import bigquery
from inference_pipeline_v2 import LeadScorerV2
import warnings
warnings.filterwarnings('ignore')

# ... (rest of the file remains the same)
class BatchScorerV2:
    def __init__(self, model_version: str = None, 
                 project_id: str = "savvy-gtm-analytics",
                 location: str = "northamerica-northeast2"):
        self.project_id = project_id
        self.location = location
        self.client = bigquery.Client(project=project_id, location=location)
        
        # Initialize scorer
        print("Initializing LeadScorerV2...")
        self.scorer = LeadScorerV2(model_version=model_version)
        print(f"[OK] Model loaded: {self.scorer.model_version}")
        
    def fetch_active_leads(self, days_back: int = 30) -> pd.DataFrame:
        """
        Fetch active leads from the last N days
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            DataFrame with lead features
        """
        print(f"\nFetching active leads from last {days_back} days...")
        
        # Use fixed date range based on available data (2024-02-01 to 2024-11-27)
        # For production, use: cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        cutoff_date = '2024-09-01'  # Score leads from Sept 2024 onwards
        
        query = f"""
        SELECT
            lf.lead_id,
            lf.advisor_crd,
            lf.contacted_date,
            
            -- Base features (11 required)
            lf.aum_growth_since_jan2024_pct,
            lf.current_firm_tenure_months,
            lf.firm_aum_pit,
            lf.firm_net_change_12mo,
            lf.firm_rep_count_at_contact,
            lf.industry_tenure_months,
            lf.num_prior_firms,
            lf.pit_mobility_tier_Highly_Mobile,
            lf.pit_mobility_tier_Mobile,
            lf.pit_mobility_tier_Stable,
            lf.pit_moves_3yr,
            
            -- Lead metadata
            l.Company as company_name,
            l.LeadSource as lead_source
            
        FROM `{self.project_id}.ml_features.lead_scoring_features` lf
        INNER JOIN `{self.project_id}.SavvyGTMData.Lead` l
            ON lf.lead_id = l.Id
        WHERE lf.contacted_date >= '{cutoff_date}'
            AND lf.contacted_date <= CURRENT_DATE()
        ORDER BY lf.contacted_date DESC
        """
        
        print(f"  Querying leads from {cutoff_date} to today...")
        df = self.client.query(query).result().to_dataframe()
        
        print(f"[OK] Fetched {len(df):,} active leads")
        return df
    
    def score_leads(self, leads_df: pd.DataFrame) -> pd.DataFrame:
        """
        Score leads using LeadScorerV2
        
        Args:
            leads_df: DataFrame with lead features
            
        Returns:
            DataFrame with scores and predictions
        """
        print(f"\nScoring {len(leads_df):,} leads...")
        
        results = []
        
        for idx, row in leads_df.iterrows():
            try:
                # Prepare feature dictionary (raw features only)
                features = {
                    'aum_growth_since_jan2024_pct': float(row.get('aum_growth_since_jan2024_pct', 0) or 0),
                    'current_firm_tenure_months': float(row.get('current_firm_tenure_months', 0) or 0),
                    'firm_aum_pit': float(row.get('firm_aum_pit', 0) or 0),
                    'firm_net_change_12mo': float(row.get('firm_net_change_12mo', 0) or 0),
                    'firm_rep_count_at_contact': float(row.get('firm_rep_count_at_contact', 0) or 0),
                    'industry_tenure_months': float(row.get('industry_tenure_months', 0) or 0),
                    'num_prior_firms': float(row.get('num_prior_firms', 0) or 0),
                    'pit_mobility_tier_Highly Mobile': float(row.get('pit_mobility_tier_Highly_Mobile', 0) or 0),
                    'pit_mobility_tier_Mobile': float(row.get('pit_mobility_tier_Mobile', 0) or 0),
                    'pit_mobility_tier_Stable': float(row.get('pit_mobility_tier_Stable', 0) or 0),
                    'pit_moves_3yr': float(row.get('pit_moves_3yr', 0) or 0)
                }
                
                # Score lead (engineered features calculated automatically)
                result = self.scorer.score_lead(features)
                
                results.append({
                    'lead_id': row['lead_id'],
                    'advisor_crd': str(row.get('advisor_crd', '')),
                    'contacted_date': pd.to_datetime(row['contacted_date']).date() if pd.notna(row['contacted_date']) else None,
                    'score_date': datetime.now().date(),
                    'lead_score': result['lead_score'],
                    'score_bucket': result['score_bucket'],
                    'action_recommended': result['action_recommended'],
                    'uncalibrated_score': result['uncalibrated_score'],
                    'pit_restlessness_ratio': result['engineered_features']['pit_restlessness_ratio'],
                    'flight_risk_score': result['engineered_features']['flight_risk_score'],
                    'is_fresh_start': int(result['engineered_features']['is_fresh_start']),
                    'narrative': None,  # Will be populated by narrative generator
                    'model_version': result['model_version'],
                    'scoring_timestamp': datetime.now()
                })
                
            except Exception as e:
                print(f"  Warning: Failed to score lead {row.get('lead_id', 'unknown')}: {e}")
                continue
        
        results_df = pd.DataFrame(results)
        print(f"[OK] Scored {len(results_df):,} leads successfully")
        
        return results_df
    
    def write_to_bigquery(self, scores_df: pd.DataFrame, 
                         table_id: str = "savvy-gtm-analytics.ml_features.lead_scores_daily"):
        """
        Write scores to BigQuery
        
        Args:
            scores_df: DataFrame with scores
            table_id: BigQuery table ID
        """
        if len(scores_df) == 0:
            print("No scores to write")
            return
        
        print(f"\nWriting {len(scores_df):,} scores to BigQuery...")
        print(f"  Table: {table_id}")
        
        # Write to BigQuery
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=[
                bigquery.SchemaField("lead_id", "STRING"),
                bigquery.SchemaField("advisor_crd", "STRING"),
                bigquery.SchemaField("contacted_date", "DATE"),
                bigquery.SchemaField("score_date", "DATE"),
                bigquery.SchemaField("lead_score", "FLOAT64"),
                bigquery.SchemaField("score_bucket", "STRING"),
                bigquery.SchemaField("action_recommended", "STRING"),
                bigquery.SchemaField("uncalibrated_score", "FLOAT64"),
                bigquery.SchemaField("pit_restlessness_ratio", "FLOAT64"),
                bigquery.SchemaField("flight_risk_score", "FLOAT64"),
                bigquery.SchemaField("is_fresh_start", "INT64"),
                bigquery.SchemaField("narrative", "STRING"),
                bigquery.SchemaField("model_version", "STRING"),
                bigquery.SchemaField("scoring_timestamp", "TIMESTAMP")
            ]
        )
        
        job = self.client.load_table_from_dataframe(scores_df, table_id, job_config=job_config)
        job.result()
        
        print(f"[OK] Scores written to BigQuery")
    
    def validate_scores(self, scores_df: pd.DataFrame):
        """
        Validate scoring results
        
        Args:
            scores_df: DataFrame with scores
        """
        print("\n" + "="*60)
        print("SCORING VALIDATION")
        print("="*60)
        
        print(f"\nTotal Leads Scored: {len(scores_df):,}")
        print(f"Mean Score: {scores_df['lead_score'].mean():.4f}")
        print(f"Median Score: {scores_df['lead_score'].median():.4f}")
        print(f"Min Score: {scores_df['lead_score'].min():.4f}")
        print(f"Max Score: {scores_df['lead_score'].max():.4f}")
        
        print(f"\nScore Bucket Distribution:")
        bucket_counts = scores_df['score_bucket'].value_counts()
        for bucket, count in bucket_counts.items():
            pct = count / len(scores_df) * 100
            print(f"  {bucket:15s}: {count:5,} ({pct:5.1f}%)")
        
        print(f"\nVery Hot Leads (>= 0.7): {len(scores_df[scores_df['lead_score'] >= 0.7]):,}")
        print(f"Hot Leads (0.5-0.7): {len(scores_df[(scores_df['lead_score'] >= 0.5) & (scores_df['lead_score'] < 0.7)]):,}")
        print(f"Warm Leads (0.3-0.5): {len(scores_df[(scores_df['lead_score'] >= 0.3) & (scores_df['lead_score'] < 0.5)]):,}")
        print(f"Cold Leads (< 0.3): {len(scores_df[scores_df['lead_score'] < 0.3]):,}")
        
        print(f"\nEngineered Features:")
        print(f"  Mean Restlessness Ratio: {scores_df['pit_restlessness_ratio'].mean():.2f}")
        print(f"  Mean Flight Risk Score: {scores_df['flight_risk_score'].mean():.2f}")
        print(f"  Fresh Start Rate: {scores_df['is_fresh_start'].mean()*100:.1f}%")
        
        print("="*60 + "\n")
    
    def run_batch_scoring(self, days_back: int = 30, write_to_bq: bool = True):
        """
        Execute complete batch scoring pipeline
        
        Args:
            days_back: Number of days to look back
            write_to_bq: Whether to write results to BigQuery
        """
        print("\n" + "="*60)
        print("BATCH SCORING PIPELINE (v2 Boosted Model)")
        print("="*60 + "\n")
        
        # Step 1: Fetch leads
        leads_df = self.fetch_active_leads(days_back=days_back)
        
        if len(leads_df) == 0:
            print("No active leads found. Exiting.")
            return None
        
        # Step 2: Score leads
        scores_df = self.score_leads(leads_df)
        
        # Step 3: Validate
        self.validate_scores(scores_df)
        
        # Step 4: Write to BigQuery
        if write_to_bq:
            self.write_to_bigquery(scores_df)
        
        return scores_df


if __name__ == "__main__":
    scorer = BatchScorerV2()
    scores_df = scorer.run_batch_scoring(days_back=90, write_to_bq=True)
    
    if scores_df is not None:
        print(f"\n[OK] Batch scoring complete!")
        print(f"Scored {len(scores_df):,} leads")
        print(f"Top 5 scores:")
        print(scores_df.nlargest(5, 'lead_score')[['lead_id', 'lead_score', 'score_bucket', 'flight_risk_score']].to_string())
    else:
        print("\n[WARNING] No leads scored")

