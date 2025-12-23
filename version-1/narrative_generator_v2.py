"""
Phase 7.5: Narrative Generation for Boosted Model (v2)
Generates natural language explanations for lead scores, including new engineered features
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import warnings
warnings.filterwarnings('ignore')

class NarrativeGeneratorV2:
    def __init__(self):
        self.output_dir = Path("reports/narratives")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_narrative(self, lead_data: Dict[str, Any], score_result: Dict[str, Any]) -> str:
        """
        Generate natural language narrative for a lead
        
        Args:
            lead_data: Raw lead features
            score_result: Scoring result from LeadScorerV2
            
        Returns:
            Narrative string
        """
        score = score_result['lead_score']
        bucket = score_result['score_bucket']
        engineered = score_result['engineered_features']
        
        # Extract key features
        current_tenure = lead_data.get('current_firm_tenure_months', 0) or 0
        pit_moves = lead_data.get('pit_moves_3yr', 0) or 0
        firm_net_change = lead_data.get('firm_net_change_12mo', 0) or 0
        industry_tenure = lead_data.get('industry_tenure_months', 0) or 0
        num_prior_firms = lead_data.get('num_prior_firms', 0) or 0
        firm_aum = lead_data.get('firm_aum_pit', 0) or 0
        
        # Engineered features
        restlessness_ratio = engineered.get('pit_restlessness_ratio', 0)
        flight_risk = engineered.get('flight_risk_score', 0)
        is_fresh = engineered.get('is_fresh_start', 0)
        
        # Build narrative
        narrative_parts = []
        
        # Opening
        narrative_parts.append(f"This lead has a {bucket.lower()} score of {score:.1%}.")
        
        # Flight Risk (NEW FEATURE)
        if flight_risk > 20:
            narrative_parts.append(
                f"**High flight risk detected:** {pit_moves} firm moves in the last 3 years, "
                f"combined with a firm losing {abs(firm_net_change)} advisors in the past 12 months. "
                f"This multiplicative risk signal suggests strong conversion potential."
            )
        elif flight_risk > 10:
            narrative_parts.append(
                f"**Moderate flight risk:** {pit_moves} recent moves and firm instability "
                f"({firm_net_change} net advisor change) indicate potential openness to new opportunities."
            )
        
        # Restlessness Ratio (NEW FEATURE)
        if restlessness_ratio < 0.5 and num_prior_firms > 0:
            narrative_parts.append(
                f"**Restlessness indicator:** Current tenure ({current_tenure:.0f} months) is shorter than "
                f"historical average, suggesting this advisor may be ready for a change."
            )
        elif restlessness_ratio > 2.0:
            narrative_parts.append(
                f"**Stability indicator:** Current tenure ({current_tenure:.0f} months) is significantly longer "
                f"than historical average, indicating strong firm loyalty."
            )
        
        # Fresh Start (NEW FEATURE)
        if is_fresh == 1:
            narrative_parts.append(
                f"**New hire alert:** Advisor has been at current firm for less than 12 months. "
                f"New hires are often more open to exploring opportunities."
            )
        
        # Mobility
        if pit_moves >= 3:
            narrative_parts.append(
                f"**Highly mobile advisor:** {pit_moves} firm changes in the last 3 years indicates "
                f"a pattern of seeking new opportunities."
            )
        elif pit_moves == 2:
            narrative_parts.append(
                f"**Mobile advisor:** {pit_moves} recent firm changes suggest openness to change."
            )
        
        # Firm Stability
        if firm_net_change < -5:
            narrative_parts.append(
                f"**Bleeding firm:** Firm has lost {abs(firm_net_change)} advisors in the past 12 months, "
                f"indicating instability that may drive advisor departures."
            )
        elif firm_net_change > 5:
            narrative_parts.append(
                f"**Growing firm:** Firm has gained {firm_net_change} advisors, suggesting positive momentum."
            )
        
        # Tenure
        if current_tenure < 12:
            narrative_parts.append(
                f"**Short tenure:** {current_tenure:.0f} months at current firm suggests limited commitment."
            )
        elif current_tenure > 60:
            narrative_parts.append(
                f"**Long tenure:** {current_tenure:.0f} months at current firm indicates strong loyalty."
            )
        
        # Industry Experience
        if industry_tenure > 120:
            narrative_parts.append(
                f"**Veteran advisor:** {industry_tenure:.0f} months of industry experience."
            )
        
        # Firm Size
        if firm_aum > 1e9:  # > $1B
            narrative_parts.append(
                f"**Large firm:** Firm AUM exceeds $1B, indicating established presence."
            )
        
        # Action recommendation
        narrative_parts.append(f"\n**Recommended Action:** {score_result['action_recommended']}")
        
        return " ".join(narrative_parts)
    
    def generate_narratives_batch(self, scores_df: pd.DataFrame, 
                                 leads_df: pd.DataFrame = None,
                                 top_n: int = 50) -> pd.DataFrame:
        """
        Generate narratives for top N scoring leads
        
        Args:
            scores_df: DataFrame with scores (must have lead_id)
            leads_df: Optional DataFrame with lead features
            top_n: Number of top leads to generate narratives for
            
        Returns:
            DataFrame with narratives
        """
        print(f"\nGenerating narratives for top {top_n} leads...")
        
        # Get top N leads
        top_leads = scores_df.nlargest(top_n, 'lead_score').copy()
        
        narratives = []
        
        for idx, row in top_leads.iterrows():
            lead_id = row['lead_id']
            
            # Try to get lead features
            if leads_df is not None and lead_id in leads_df['lead_id'].values:
                lead_features = leads_df[leads_df['lead_id'] == lead_id].iloc[0].to_dict()
            else:
                # Use minimal features from score result
                lead_features = {
                    'current_firm_tenure_months': 0,
                    'pit_moves_3yr': 0,
                    'firm_net_change_12mo': 0,
                    'industry_tenure_months': 0,
                    'num_prior_firms': 0,
                    'firm_aum_pit': 0
                }
            
            # Create score result dict
            score_result = {
                'lead_score': row['lead_score'],
                'score_bucket': row['score_bucket'],
                'action_recommended': row['action_recommended'],
                'engineered_features': {
                    'pit_restlessness_ratio': row.get('pit_restlessness_ratio', 0),
                    'flight_risk_score': row.get('flight_risk_score', 0),
                    'is_fresh_start': row.get('is_fresh_start', 0)
                }
            }
            
            # Generate narrative
            narrative = self.generate_narrative(lead_features, score_result)
            
            narratives.append({
                'lead_id': lead_id,
                'advisor_crd': row.get('advisor_crd', ''),
                'lead_score': row['lead_score'],
                'score_bucket': row['score_bucket'],
                'narrative': narrative
            })
        
        narratives_df = pd.DataFrame(narratives)
        
        # Save to CSV
        output_path = self.output_dir / f"narratives_top_{top_n}_v2.csv"
        narratives_df.to_csv(output_path, index=False)
        print(f"[OK] Narratives saved to: {output_path}")
        
        return narratives_df


if __name__ == "__main__":
    # Example usage
    print("Narrative Generator V2 - Test Mode")
    print("="*60)
    
    generator = NarrativeGeneratorV2()
    
    # Sample lead data
    sample_lead = {
        'current_firm_tenure_months': 12.0,
        'pit_moves_3yr': 2.0,
        'firm_net_change_12mo': -5.0,
        'industry_tenure_months': 120.0,
        'num_prior_firms': 3.0,
        'firm_aum_pit': 500000000.0
    }
    
    sample_score = {
        'lead_score': 0.65,
        'score_bucket': 'Hot',
        'action_recommended': 'Prioritize in next outreach cycle',
        'engineered_features': {
            'pit_restlessness_ratio': 0.33,
            'flight_risk_score': 10.0,
            'is_fresh_start': 1.0
        }
    }
    
    narrative = generator.generate_narrative(sample_lead, sample_score)
    print("\nSample Narrative:")
    print("-" * 60)
    print(narrative)
    print("-" * 60)

