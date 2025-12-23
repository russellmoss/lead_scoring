"""
Phase 6.3: Inference Pipeline Construction
Creates the LeadScorer class for Cloud Function deployment
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

class LeadScorer:
    """
    Production-ready lead scoring class for Cloud Function deployment.
    
    Usage:
        scorer = LeadScorer(model_version="v1-20241221-abc123")
        result = scorer.score_lead(lead_features_dict)
    """
    
    def __init__(self, model_version: Optional[str] = None, 
                 model_dir: str = "models/production"):
        """
        Initialize LeadScorer
        
        Args:
            model_version: Version ID (e.g., "v1-20241221-abc123"). 
                         If None, loads latest from registry.
            model_dir: Directory containing production models
        """
        self.model_dir = Path(model_dir)
        self.registry_dir = Path("models/registry")
        
        # Load registry to get model version
        if model_version is None:
            with open(self.registry_dir / "registry.json", 'r') as f:
                registry = json.load(f)
            model_version = registry['latest_version']
        
        self.model_version = model_version
        print(f"Loading model version: {model_version}")
        
        # Load model
        model_path = self.model_dir / f"model_{model_version}.pkl"
        with open(model_path, 'rb') as f:
            calibrated_model = pickle.load(f)
        
        self.base_model = calibrated_model['base_model']
        self.calibrator = calibrated_model['calibrator']
        self.calibration_method = calibrated_model['calibration_method']
        self.feature_names = calibrated_model['feature_names']
        
        # Load feature names for validation
        feature_path = self.model_dir / f"feature_names_{model_version}.json"
        with open(feature_path, 'r') as f:
            self.expected_features = json.load(f)
        
        print(f"[OK] Model loaded: {len(self.feature_names)} features")
        
    def _prepare_features(self, lead_data: Dict[str, Any]) -> np.ndarray:
        """
        Prepare feature vector from lead data dictionary
        
        Args:
            lead_data: Dictionary with feature names as keys
            
        Returns:
            Feature vector as numpy array
        """
        # Create feature vector in correct order
        feature_vector = []
        missing_features = []
        
        for feature_name in self.feature_names:
            if feature_name in lead_data:
                value = lead_data[feature_name]
                # Handle None/NaN
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    feature_vector.append(0.0)  # Default to 0 for missing
                else:
                    feature_vector.append(float(value))
            else:
                missing_features.append(feature_name)
                feature_vector.append(0.0)  # Default to 0 for missing
        
        if missing_features:
            print(f"Warning: Missing features (defaulted to 0): {missing_features[:5]}")
        
        return np.array(feature_vector).reshape(1, -1)
    
    def _get_score_bucket(self, score: float) -> str:
        """Convert score to bucket"""
        if score >= 0.7:
            return "Very Hot"
        elif score >= 0.5:
            return "Hot"
        elif score >= 0.3:
            return "Warm"
        else:
            return "Cold"
    
    def _get_action_recommended(self, score: float) -> str:
        """Get recommended action based on score"""
        if score >= 0.7:
            return "Call immediately"
        elif score >= 0.5:
            return "Prioritize in next outreach cycle"
        elif score >= 0.3:
            return "Include in standard outreach"
        else:
            return "Low priority"
    
    def score_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a single lead
        
        Args:
            lead_data: Dictionary with feature names as keys
                      Example: {
                          'current_firm_tenure_months': 12.0,
                          'days_in_gap': 0.0,
                          'firm_net_change_12mo': -5.0,
                          ...
                      }
        
        Returns:
            Dictionary with scoring results:
            {
                'lead_score': 0.65,
                'score_bucket': 'Hot',
                'action_recommended': 'Prioritize in next outreach cycle',
                'model_version': 'v1-20241221-abc123',
                'uncalibrated_score': 0.58
            }
        """
        # Prepare features
        X = self._prepare_features(lead_data)
        
        # Get uncalibrated prediction
        uncalibrated_score = self.base_model.predict_proba(X)[0, 1]
        
        # Apply calibration
        if self.calibration_method == 'isotonic':
            calibrated_score = self.calibrator.predict([uncalibrated_score])[0]
        else:  # platt
            calibrated_score = self.calibrator.predict_proba([[uncalibrated_score]])[0, 1]
        
        # Ensure score is in [0, 1] range
        calibrated_score = max(0.0, min(1.0, calibrated_score))
        
        # Get bucket and action
        score_bucket = self._get_score_bucket(calibrated_score)
        action_recommended = self._get_action_recommended(calibrated_score)
        
        return {
            'lead_score': float(calibrated_score),
            'score_bucket': score_bucket,
            'action_recommended': action_recommended,
            'model_version': self.model_version,
            'uncalibrated_score': float(uncalibrated_score)
        }
    
    def score_batch(self, leads_data: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        Score multiple leads in batch
        
        Args:
            leads_data: List of dictionaries, each containing lead features
        
        Returns:
            List of scoring results
        """
        results = []
        for lead_data in leads_data:
            result = self.score_lead(lead_data)
            results.append(result)
        return results


def create_cloud_function_code(model_version: str) -> str:
    """
    Generate Cloud Function code template
    
    Args:
        model_version: Model version ID
        
    Returns:
        Cloud Function code as string
    """
    # Escape braces for f-string
    code = f'''"""
Cloud Function for Lead Scoring
Model Version: {model_version}
"""

import json
import os
from inference_pipeline import LeadScorer

# Initialize scorer (loads once on cold start)
scorer = LeadScorer(model_version="{model_version}")

def score_lead_cloud_function(request):
    """
    Cloud Function entry point for lead scoring
    
    Expected request format:
    {{
        "lead_id": "abc123",
        "features": {{
            "current_firm_tenure_months": 12.0,
            "days_in_gap": 0.0,
            "firm_net_change_12mo": -5.0,
            ...
        }}
    }}
    
    Returns:
    {{
        "lead_id": "abc123",
        "lead_score": 0.65,
        "score_bucket": "Hot",
        "action_recommended": "Prioritize in next outreach cycle",
        "model_version": "{model_version}"
    }}
    """
    try:
        # Parse request
        request_json = request.get_json(silent=True)
        if not request_json:
            return {{"error": "Invalid JSON"}}, 400
        
        lead_id = request_json.get("lead_id")
        features = request_json.get("features", {{}})
        
        if not lead_id:
            return {{"error": "lead_id is required"}}, 400
        
        # Score lead
        result = scorer.score_lead(features)
        result["lead_id"] = lead_id
        
        return json.dumps(result), 200
        
    except Exception as e:
        return {{"error": str(e)}}, 500
'''
    
    return code


if __name__ == "__main__":
    # Test the inference pipeline
    print("\n" + "="*60)
    print("INFERENCE PIPELINE TEST")
    print("="*60 + "\n")
    
    # Load latest model version from registry
    registry_path = Path("models/registry/registry.json")
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        model_version = registry['latest_version']
    else:
        print("Warning: No registry found. Using default version.")
        model_version = "v1-20241221-default"
    
    # Initialize scorer
    scorer = LeadScorer(model_version=model_version)
    
    # Test with sample lead
    sample_lead = {
        'current_firm_tenure_months': 12.0,
        'days_in_gap': 0.0,
        'firm_net_change_12mo': -5.0,
        'pit_moves_3yr': 2.0,
        'firm_aum_pit': 100000000.0,
        'firm_rep_count_at_contact': 50.0,
        'industry_tenure_months': 120.0,
        'num_prior_firms': 3.0,
        'aum_growth_since_jan2024_pct': 5.0,
        'pit_mobility_tier_Highly Mobile': 0.0,
        'pit_mobility_tier_Mobile': 1.0,
        'pit_mobility_tier_Stable': 0.0
    }
    
    result = scorer.score_lead(sample_lead)
    
    print("Sample Lead Scoring Result:")
    print(json.dumps(result, indent=2))
    
    # Generate Cloud Function code
    cloud_function_code = create_cloud_function_code(model_version)
    
    output_path = Path("models/production/cloud_function_code.py")
    with open(output_path, 'w') as f:
        f.write(cloud_function_code)
    
    print(f"\n[OK] Cloud Function code saved to: {output_path}")
    print(f"[OK] Inference pipeline ready for deployment!")
    print(f"Model Version: {model_version}")

