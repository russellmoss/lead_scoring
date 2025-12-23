"""
Phase 6.3: Inference Pipeline for Boosted Model (v2)
Creates the LeadScorer class that calculates derived features at runtime
"""

import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

class LeadScorerV2:
    """
    Production-ready lead scoring class for Boosted Model (v2).
    
    This class calculates the 3 engineered features at runtime from raw inputs:
    - pit_restlessness_ratio
    - flight_risk_score
    - is_fresh_start
    
    Usage:
        scorer = LeadScorerV2(model_version="v2-boosted-20251221-abc123")
        result = scorer.score_lead(lead_features_dict)
    """
    
    def __init__(self, model_version: Optional[str] = None, 
                 model_dir: str = "models/production"):
        """
        Initialize LeadScorerV2
        
        Args:
            model_version: Version ID (e.g., "v2-boosted-20251221-abc123"). 
                         If None, loads latest from registry.
            model_dir: Directory containing production models
        """
        self.model_dir = Path(model_dir)
        self.registry_dir = Path("models/registry")
        
        # Load registry to get model version
        if model_version is None:
            with open(self.registry_dir / "registry.json", 'r') as f:
                registry = json.load(f)
            # Prefer v2 if available, otherwise latest
            v2_models = [m for m in registry['models'] if m.get('model_type') == 'boosted_v2']
            if v2_models:
                model_version = v2_models[-1]['version_id']
            else:
                model_version = registry['latest_version']
        
        self.model_version = model_version
        print(f"Loading boosted model version: {model_version}")
        
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
        print(f"     Engineered features will be calculated at runtime")
        
    def _calculate_engineered_features(self, lead_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate the 3 engineered features from raw inputs
        
        Args:
            lead_data: Dictionary with raw feature values
            
        Returns:
            Dictionary with engineered feature values
        """
        engineered = {}
        
        # Feature 1: pit_restlessness_ratio
        # Formula: current_firm_tenure_months / (avg_prior_firm_tenure_months + 1)
        current_tenure = lead_data.get('current_firm_tenure_months', 0) or 0
        industry_tenure = lead_data.get('industry_tenure_months', 0) or 0
        num_prior_firms = lead_data.get('num_prior_firms', 0) or 0
        
        # Calculate avg_prior_firm_tenure
        if num_prior_firms > 0:
            avg_prior_tenure = (industry_tenure - current_tenure) / max(num_prior_firms, 1)
            avg_prior_tenure = max(0, avg_prior_tenure)  # Ensure non-negative
        else:
            avg_prior_tenure = 0
        
        # Calculate restlessness ratio
        if avg_prior_tenure > 0.1:
            restlessness_ratio = current_tenure / avg_prior_tenure
        else:
            restlessness_ratio = current_tenure  # If no prior history, use current tenure
        
        # Handle edge cases
        if np.isinf(restlessness_ratio) or np.isnan(restlessness_ratio):
            restlessness_ratio = current_tenure
        
        engineered['pit_restlessness_ratio'] = float(np.clip(restlessness_ratio, 0, 100))
        
        # Feature 2: flight_risk_score
        # Formula: pit_moves_3yr * (firm_net_change_12mo * -1)
        pit_moves = lead_data.get('pit_moves_3yr', 0) or 0
        firm_net_change = lead_data.get('firm_net_change_12mo', 0) or 0
        
        # Clip firm_net_change to reasonable range
        firm_net_change_clipped = np.clip(firm_net_change, -100, 100)
        flight_risk = pit_moves * (firm_net_change_clipped * -1)
        
        engineered['flight_risk_score'] = float(np.clip(flight_risk, -1000, 1000))
        
        # Feature 3: is_fresh_start
        # Formula: 1 if current_firm_tenure_months < 12 else 0
        is_fresh = 1 if current_tenure < 12 else 0
        engineered['is_fresh_start'] = float(is_fresh)
        
        return engineered
    
    def _prepare_features(self, lead_data: Dict[str, Any]) -> np.ndarray:
        """
        Prepare feature vector from lead data dictionary
        Calculates engineered features at runtime
        
        Args:
            lead_data: Dictionary with feature names as keys
            
        Returns:
            Feature vector as numpy array
        """
        # Calculate engineered features
        engineered_features = self._calculate_engineered_features(lead_data)
        
        # Merge with input data
        full_data = {**lead_data, **engineered_features}
        
        # Create feature vector in correct order
        feature_vector = []
        missing_features = []
        
        for feature_name in self.feature_names:
            if feature_name in full_data:
                value = full_data[feature_name]
                # Handle None/NaN
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    feature_vector.append(0.0)
                else:
                    feature_vector.append(float(value))
            else:
                missing_features.append(feature_name)
                feature_vector.append(0.0)
        
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
            lead_data: Dictionary with raw feature values
                      The 3 engineered features will be calculated automatically
                      Example: {
                          'current_firm_tenure_months': 12.0,
                          'pit_moves_3yr': 2.0,
                          'firm_net_change_12mo': -5.0,
                          'industry_tenure_months': 120.0,
                          'num_prior_firms': 3.0,
                          ...
                      }
        
        Returns:
            Dictionary with scoring results:
            {
                'lead_score': 0.65,
                'score_bucket': 'Hot',
                'action_recommended': 'Prioritize in next outreach cycle',
                'model_version': 'v2-boosted-20251221-abc123',
                'uncalibrated_score': 0.58,
                'engineered_features': {
                    'pit_restlessness_ratio': 46.2,
                    'flight_risk_score': 10.0,
                    'is_fresh_start': 1.0
                }
            }
        """
        # Prepare features (includes engineered feature calculation)
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
        
        # Get engineered features for transparency
        engineered_features = self._calculate_engineered_features(lead_data)
        
        return {
            'lead_score': float(calibrated_score),
            'score_bucket': score_bucket,
            'action_recommended': action_recommended,
            'model_version': self.model_version,
            'uncalibrated_score': float(uncalibrated_score),
            'engineered_features': engineered_features
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


def create_cloud_function_code_v2(model_version: str) -> str:
    """
    Generate Cloud Function code template for v2 boosted model
    
    Args:
        model_version: Model version ID
        
    Returns:
        Cloud Function code as string
    """
    code = f'''"""
Cloud Function for Lead Scoring - Boosted Model (v2)
Model Version: {model_version}
"""

import json
import os
from inference_pipeline_v2 import LeadScorerV2

# Initialize scorer (loads once on cold start)
scorer = LeadScorerV2(model_version="{model_version}")

def score_lead_cloud_function(request):
    """
    Cloud Function entry point for lead scoring (v2 boosted model)
    
    Expected request format:
    {{
        "lead_id": "abc123",
        "features": {{
            "current_firm_tenure_months": 12.0,
            "pit_moves_3yr": 2.0,
            "firm_net_change_12mo": -5.0,
            "industry_tenure_months": 120.0,
            "num_prior_firms": 3.0,
            ...
            // Note: pit_restlessness_ratio, flight_risk_score, is_fresh_start
            // will be calculated automatically from the above inputs
        }}
    }}
    
    Returns:
    {{
        "lead_id": "abc123",
        "lead_score": 0.65,
        "score_bucket": "Hot",
        "action_recommended": "Prioritize in next outreach cycle",
        "model_version": "{model_version}",
        "engineered_features": {{
            "pit_restlessness_ratio": 46.2,
            "flight_risk_score": 10.0,
            "is_fresh_start": 1.0
        }}
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
        
        # Score lead (engineered features calculated automatically)
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
    print("INFERENCE PIPELINE V2 TEST")
    print("="*60 + "\n")
    
    # Load latest v2 model version from registry
    registry_path = Path("models/registry/registry.json")
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        v2_models = [m for m in registry['models'] if m.get('model_type') == 'boosted_v2']
        if v2_models:
            model_version = v2_models[-1]['version_id']
        else:
            print("Warning: No v2 model found in registry. Using default.")
            model_version = "v2-boosted-20251221-default"
    else:
        print("Warning: No registry found. Using default version.")
        model_version = "v2-boosted-20251221-default"
    
    # Initialize scorer
    try:
        scorer = LeadScorerV2(model_version=model_version)
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Note: Model may need to be calibrated and packaged first.")
        exit(1)
    
    # Test with sample lead (raw features only - engineered features calculated automatically)
    sample_lead = {
        'current_firm_tenure_months': 12.0,
        'pit_moves_3yr': 2.0,
        'firm_net_change_12mo': -5.0,
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
    
    # Verify engineered features were calculated
    print("\n" + "="*60)
    print("ENGINEERED FEATURES VERIFICATION")
    print("="*60)
    print(f"pit_restlessness_ratio: {result['engineered_features']['pit_restlessness_ratio']:.2f}")
    print(f"flight_risk_score: {result['engineered_features']['flight_risk_score']:.2f}")
    print(f"is_fresh_start: {result['engineered_features']['is_fresh_start']:.0f}")
    print("="*60 + "\n")
    
    # Generate Cloud Function code
    cloud_function_code = create_cloud_function_code_v2(model_version)
    
    output_path = Path("models/production/cloud_function_code_v2.py")
    with open(output_path, 'w') as f:
        f.write(cloud_function_code)
    
    print(f"[OK] Cloud Function code saved to: {output_path}")
    print(f"[OK] Inference pipeline v2 ready for deployment!")
    print(f"Model Version: {model_version}")

