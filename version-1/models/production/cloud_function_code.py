"""
Cloud Function for Lead Scoring
Model Version: v1-20251221-b374197e
"""

import json
import os
from inference_pipeline import LeadScorer

# Initialize scorer (loads once on cold start)
scorer = LeadScorer(model_version="v1-20251221-b374197e")

def score_lead_cloud_function(request):
    """
    Cloud Function entry point for lead scoring
    
    Expected request format:
    {
        "lead_id": "abc123",
        "features": {
            "current_firm_tenure_months": 12.0,
            "days_in_gap": 0.0,
            "firm_net_change_12mo": -5.0,
            ...
        }
    }
    
    Returns:
    {
        "lead_id": "abc123",
        "lead_score": 0.65,
        "score_bucket": "Hot",
        "action_recommended": "Prioritize in next outreach cycle",
        "model_version": "v1-20251221-b374197e"
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
        
        # Score lead
        result = scorer.score_lead(features)
        result["lead_id"] = lead_id
        
        return json.dumps(result), 200
        
    except Exception as e:
        return {"error": str(e)}, 500
