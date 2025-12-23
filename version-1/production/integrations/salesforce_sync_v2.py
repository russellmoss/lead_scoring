"""
Phase 7.4: Salesforce Sync (Dry Run)
Generates JSON payloads for syncing lead scores to Salesforce
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class SalesforceSyncV2:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.output_dir = Path("reports/salesforce_sync")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Salesforce field mappings
        self.field_mappings = {
            'lead_score': 'Lead_Score__c',
            'score_bucket': 'Lead_Score_Bucket__c',
            'action_recommended': 'Lead_Action_Recommended__c',
            'narrative': 'Lead_Score_Narrative__c',
            'model_version': 'Lead_Score_Model_Version__c',
            'scoring_timestamp': 'Lead_Score_Timestamp__c',
            'pit_restlessness_ratio': 'Lead_Restlessness_Ratio__c',
            'flight_risk_score': 'Lead_Flight_Risk_Score__c',
            'is_fresh_start': 'Lead_Is_Fresh_Start__c'
        }
    
    def create_salesforce_payload(self, lead_id: str, score_data: Dict[str, Any], 
                                 narrative: str = None) -> Dict[str, Any]:
        """
        Create Salesforce update payload for a lead
        
        Args:
            lead_id: Salesforce Lead ID
            score_data: Scoring result from LeadScorerV2
            narrative: Optional narrative text
            
        Returns:
            Dictionary with Salesforce field updates
        """
        payload = {
            'Id': lead_id,
            self.field_mappings['lead_score']: round(score_data['lead_score'], 4),
            self.field_mappings['score_bucket']: score_data['score_bucket'],
            self.field_mappings['action_recommended']: score_data['action_recommended'],
            self.field_mappings['model_version']: score_data.get('model_version', 'v2-boosted-20251221-b796831a'),
            self.field_mappings['scoring_timestamp']: datetime.now().isoformat(),
            self.field_mappings['pit_restlessness_ratio']: round(score_data['engineered_features']['pit_restlessness_ratio'], 2),
            self.field_mappings['flight_risk_score']: round(score_data['engineered_features']['flight_risk_score'], 2),
            self.field_mappings['is_fresh_start']: int(score_data['engineered_features']['is_fresh_start'])
        }
        
        if narrative:
            payload[self.field_mappings['narrative']] = narrative
        
        return payload
    
    def create_batch_payload(self, scores_df: pd.DataFrame, 
                            narratives_df: pd.DataFrame = None) -> List[Dict[str, Any]]:
        """
        Create batch payload for multiple leads
        
        Args:
            scores_df: DataFrame with scores
            narratives_df: Optional DataFrame with narratives
            
        Returns:
            List of Salesforce payload dictionaries
        """
        print(f"\nCreating Salesforce payloads for {len(scores_df):,} leads...")
        
        payloads = []
        
        # Merge narratives if provided
        if narratives_df is not None:
            merged = scores_df.merge(
                narratives_df[['lead_id', 'narrative']], 
                on='lead_id', 
                how='left'
            )
        else:
            merged = scores_df.copy()
            merged['narrative'] = None
        
        for idx, row in merged.iterrows():
            score_data = {
                'lead_score': row['lead_score'],
                'score_bucket': row['score_bucket'],
                'action_recommended': row['action_recommended'],
                'model_version': row.get('model_version', 'v2-boosted-20251221-b796831a'),
                'engineered_features': {
                    'pit_restlessness_ratio': row.get('pit_restlessness_ratio', 0),
                    'flight_risk_score': row.get('flight_risk_score', 0),
                    'is_fresh_start': row.get('is_fresh_start', 0)
                }
            }
            
            payload = self.create_salesforce_payload(
                lead_id=row['lead_id'],
                score_data=score_data,
                narrative=row.get('narrative')
            )
            
            payloads.append(payload)
        
        print(f"[OK] Created {len(payloads):,} payloads")
        return payloads
    
    def save_payloads(self, payloads: List[Dict[str, Any]], 
                     filename: str = "salesforce_payloads_v2.json"):
        """
        Save payloads to JSON file
        
        Args:
            payloads: List of payload dictionaries
            filename: Output filename
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(payloads, f, indent=2)
        
        print(f"[OK] Payloads saved to: {output_path}")
        return output_path
    
    def log_sample_payloads(self, payloads: List[Dict[str, Any]], n: int = 3):
        """
        Log sample payloads for review
        
        Args:
            payloads: List of payload dictionaries
            n: Number of samples to show
        """
        print(f"\n{'='*60}")
        print(f"SAMPLE SALESFORCE PAYLOADS (Top {n})")
        print("="*60)
        
        # Sort by lead_score descending
        sorted_payloads = sorted(payloads, key=lambda x: x.get(self.field_mappings['lead_score'], 0), reverse=True)
        
        for i, payload in enumerate(sorted_payloads[:n], 1):
            print(f"\n--- Payload {i} ---")
            print(json.dumps(payload, indent=2))
        
        print("="*60 + "\n")
    
    def run_sync_dry_run(self, scores_df: pd.DataFrame, 
                        narratives_df: pd.DataFrame = None,
                        top_n: int = 50):
        """
        Run Salesforce sync in dry-run mode
        
        Args:
            scores_df: DataFrame with scores
            narratives_df: Optional DataFrame with narratives
            top_n: Number of top leads to sync
        """
        print("\n" + "="*60)
        print("SALESFORCE SYNC (DRY RUN)")
        print("="*60)
        
        # Get top N leads
        top_scores = scores_df.nlargest(top_n, 'lead_score')
        
        # Create payloads
        payloads = self.create_batch_payload(top_scores, narratives_df)
        
        # Save payloads
        output_path = self.save_payloads(payloads)
        
        # Log samples
        self.log_sample_payloads(payloads, n=3)
        
        print(f"[OK] Dry run complete. {len(payloads):,} payloads ready for Salesforce")
        print(f"     Output: {output_path}")
        
        if self.dry_run:
            print("\n[DRY RUN] No actual Salesforce updates performed")
        
        return payloads


if __name__ == "__main__":
    print("Salesforce Sync V2 - Test Mode")
    print("="*60)
    
    # Example usage
    sync = SalesforceSyncV2(dry_run=True)
    
    # Sample score data
    sample_scores = pd.DataFrame([
        {
            'lead_id': '00Q000000000001',
            'lead_score': 0.75,
            'score_bucket': 'Very Hot',
            'action_recommended': 'Call immediately',
            'pit_restlessness_ratio': 0.33,
            'flight_risk_score': 10.0,
            'is_fresh_start': 1,
            'model_version': 'v2-boosted-20251221-b796831a'
        }
    ])
    
    sample_narratives = pd.DataFrame([
        {
            'lead_id': '00Q000000000001',
            'narrative': 'High flight risk detected: 2 firm moves in the last 3 years...'
        }
    ])
    
    payloads = sync.run_sync_dry_run(sample_scores, sample_narratives, top_n=1)

