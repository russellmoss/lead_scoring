"""
Cloud Function for Lead Scoring - Boosted Model (v2)
Model Version: v2-boosted-20251221-b796831a
"""

import json
import os
from inference_pipeline_v2 import LeadScorerV2

# Initialize scorer (loads once on cold start)
scorer = LeadScorerV2(model_version="v2-boosted-20251221-b796831a")

def score_lead_cloud_function(request):
    """
    Cloud Function entry point for lead scoring (v2 boosted model)
    
    Expected request format:
    {
        "lead_id": "abc123",
        "features": {
            "current_firm_tenure_months": 12.0,
            "pit_moves_3yr": 2.0,
            "firm_net_change_12mo": -5.0,
            "industry_tenure_months": 120.0,
            "num_prior_firms": 3.0,
            ...
            // Note: pit_restlessness_ratio, flight_risk_score, is_fresh_start
            // will be calculated automatically from the above inputs
        }
    }
    
    Returns:
    {
        "lead_id": "abc123",
        "lead_score": 0.65,
        "score_bucket": "Hot",
        "action_recommended": "Prioritize in next outreach cycle",
        "model_version": "v2-boosted-20251221-b796831a",
        "engineered_features": {
            "pit_restlessness_ratio": 46.2,
            "flight_risk_score": 10.0,
            "is_fresh_start": 1.0
        }
    }
    """
    try:
        # Parse request
        request_json = request.get_json(silent=True)
        if not request_json:
            return {"error": "Invalid JSON"}, 400
        
        lead_id = request_json.get("lead_id")
        features = request_json.get("features", {})
        
        if not lead_id:
            return {"error": "lead_id is required"}, 400
        
        # Score lead (engineered features calculated automatically)
        result = scorer.score_lead(features)
        result["lead_id"] = lead_id
        
        return json.dumps(result), 200
        
    except Exception as e:
        return {"error": str(e)}, 500
