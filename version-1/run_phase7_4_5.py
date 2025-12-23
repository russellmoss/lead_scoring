"""
Phase 7.4 & 7.5: Narrative Generation & Salesforce Sync
Generates narratives for top leads and creates Salesforce payloads
"""

import pandas as pd
from google.cloud import bigquery
from pathlib import Path
from narrative_generator_v2 import NarrativeGeneratorV2
from salesforce_sync_v2 import SalesforceSyncV2
import warnings
warnings.filterwarnings('ignore')

PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"

def main():
    print("="*60)
    print("PHASE 7.4 & 7.5: NARRATIVE GENERATION & SALESFORCE SYNC")
    print("="*60)
    
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    
    # Fetch top 50 scored leads
    print("\nFetching top 50 scored leads...")
    query = f"""
    SELECT 
        scores.*,
        features.current_firm_tenure_months,
        features.pit_moves_3yr,
        features.firm_net_change_12mo,
        features.industry_tenure_months,
        features.num_prior_firms,
        features.firm_aum_pit
    FROM `{PROJECT_ID}.ml_features.lead_scores_daily` scores
    LEFT JOIN `{PROJECT_ID}.ml_features.lead_scoring_features` features
        ON scores.lead_id = features.lead_id
    ORDER BY scores.lead_score DESC
    LIMIT 50
    """
    
    scores_df = client.query(query).result().to_dataframe()
    print(f"[OK] Fetched {len(scores_df):,} top leads")
    
    # Prepare lead features for narrative generation
    leads_df = scores_df[[
        'lead_id', 'current_firm_tenure_months', 'pit_moves_3yr',
        'firm_net_change_12mo', 'industry_tenure_months', 
        'num_prior_firms', 'firm_aum_pit'
    ]].copy()
    
    # Generate narratives
    print("\nGenerating narratives...")
    generator = NarrativeGeneratorV2()
    narratives_df = generator.generate_narratives_batch(
        scores_df=scores_df,
        leads_df=leads_df,
        top_n=50
    )
    
    # Update scores_df with narratives
    scores_df = scores_df.merge(
        narratives_df[['lead_id', 'narrative']],
        on='lead_id',
        how='left'
    )
    
    # Update BigQuery with narratives (optional)
    print("\nUpdating BigQuery with narratives...")
    # For now, just save locally - can update BQ later if needed
    
    # Create Salesforce payloads
    print("\nCreating Salesforce payloads...")
    sync = SalesforceSyncV2(dry_run=True)
    payloads = sync.run_sync_dry_run(
        scores_df=scores_df,
        narratives_df=narratives_df,
        top_n=50
    )
    
    print("\n" + "="*60)
    print("PHASE 7.4 & 7.5 COMPLETE")
    print("="*60)
    print(f"[OK] Narratives generated: {len(narratives_df):,}")
    print(f"[OK] Salesforce payloads created: {len(payloads):,}")
    print("="*60)
    
    return scores_df, narratives_df, payloads

if __name__ == "__main__":
    scores_df, narratives_df, payloads = main()
    
    # Show 3 example payloads
    print("\n" + "="*60)
    print("SAMPLE PAYLOADS (Top 3)")
    print("="*60)
    for i, payload in enumerate(payloads[:3], 1):
        print(f"\n--- Payload {i} ---")
        import json
        print(json.dumps(payload, indent=2))
    print("="*60)

