"""
Phase 6.1: Calibrate Boosted Model (v2)
Calibrates the boosted model with the 3 new engineered features
"""

import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import json
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class BoostedModelCalibrator:
    def __init__(self, model_dir: str = "models/boosted", data_dir: str = "data/processed"):
        self.model_dir = Path(model_dir)
        self.data_dir = Path(data_dir)
        self.output_dir = Path("models/production")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load boosted model
        print("Loading boosted model...")
        with open(self.model_dir / "model_v2_boosted.pkl", 'rb') as f:
            self.model = pickle.load(f)
        
        # Load feature names
        with open(self.model_dir / "feature_names_v2_boosted.json", 'r') as f:
            self.feature_names = json.load(f)
        
        print(f"Model loaded with {len(self.feature_names)} features")
        
        # Load training data and engineer features
        print("Loading and engineering features for calibration data...")
        train_df = pd.read_parquet(self.data_dir / "X_train.parquet")
        test_df = pd.read_parquet(self.data_dir / "X_test.parquet")
        
        # Load feature names from original data
        with open(self.data_dir / "feature_names.json", 'r') as f:
            feature_data = json.load(f)
            self.all_feature_names = feature_data['feature_names']
        
        # Ensure columns match
        if list(train_df.columns) != self.all_feature_names:
            train_df.columns = self.all_feature_names
        if list(test_df.columns) != self.all_feature_names:
            test_df.columns = self.all_feature_names
        
        # Drop leaking/weak features
        features_to_drop = [
            'firm_stability_score',
            'pit_mobility_tier_Average',
            'days_in_gap'
        ]
        features_base = [f for f in self.all_feature_names if f not in features_to_drop]
        
        train_df = train_df[features_base]
        test_df = test_df[features_base]
        
        # ENGINEER THE 3 NEW FEATURES (same logic as train_feature_boost.py)
        print("Engineering booster features...")
        
        # Feature 1: pit_restlessness_ratio
        train_df['avg_prior_firm_tenure_months'] = (
            (train_df['industry_tenure_months'] - train_df['current_firm_tenure_months']) / 
            train_df['num_prior_firms'].clip(lower=1)
        ).fillna(0).clip(lower=0)
        
        test_df['avg_prior_firm_tenure_months'] = (
            (test_df['industry_tenure_months'] - test_df['current_firm_tenure_months']) / 
            test_df['num_prior_firms'].clip(lower=1)
        ).fillna(0).clip(lower=0)
        
        train_df['pit_restlessness_ratio'] = np.where(
            train_df['avg_prior_firm_tenure_months'] > 0.1,
            train_df['current_firm_tenure_months'] / train_df['avg_prior_firm_tenure_months'],
            train_df['current_firm_tenure_months']
        )
        train_df['pit_restlessness_ratio'] = train_df['pit_restlessness_ratio'].replace([np.inf, -np.inf], 0).fillna(0).clip(upper=100)
        
        test_df['pit_restlessness_ratio'] = np.where(
            test_df['avg_prior_firm_tenure_months'] > 0.1,
            test_df['current_firm_tenure_months'] / test_df['avg_prior_firm_tenure_months'],
            test_df['current_firm_tenure_months']
        )
        test_df['pit_restlessness_ratio'] = test_df['pit_restlessness_ratio'].replace([np.inf, -np.inf], 0).fillna(0).clip(upper=100)
        
        # Feature 2: flight_risk_score
        train_df['flight_risk_score'] = (
            train_df['pit_moves_3yr'] * (train_df['firm_net_change_12mo'].clip(-100, 100) * -1)
        ).fillna(0).clip(-1000, 1000)
        
        test_df['flight_risk_score'] = (
            test_df['pit_moves_3yr'] * (test_df['firm_net_change_12mo'].clip(-100, 100) * -1)
        ).fillna(0).clip(-1000, 1000)
        
        # Feature 3: is_fresh_start
        train_df['is_fresh_start'] = (train_df['current_firm_tenure_months'] < 12).astype(int)
        test_df['is_fresh_start'] = (test_df['current_firm_tenure_months'] < 12).astype(int)
        
        # Compile final feature set
        train_df = train_df[self.feature_names]
        test_df = test_df[self.feature_names]
        
        # Use test set for calibration
        self.X_cal = test_df.values
        
        # Load targets
        target_test_df = pd.read_parquet(self.data_dir / "y_test.parquet")
        self.y_cal = target_test_df['target'].values
        
        print(f"\n{'='*60}")
        print("CALIBRATION SETUP")
        print(f"{'='*60}")
        print(f"Calibration samples: {len(self.y_cal):,}")
        print(f"Features: {len(self.feature_names)}")
        print(f"{'='*60}\n")
        
        # Results storage
        self.isotonic_calibrator = None
        self.platt_calibrator = None
        self.best_calibrator = None
        self.best_method = None
        self.calibration_results = {}
        
    def calibrate_isotonic(self):
        """Calibrate using Isotonic Regression"""
        
        print("Calibrating with Isotonic Regression...")
        
        y_pred_uncal = self.model.predict_proba(self.X_cal)[:, 1]
        
        self.isotonic_calibrator = IsotonicRegression(out_of_bounds='clip')
        self.isotonic_calibrator.fit(y_pred_uncal, self.y_cal)
        
        y_pred_cal = self.isotonic_calibrator.predict(y_pred_uncal)
        
        brier_score = brier_score_loss(self.y_cal, y_pred_cal)
        log_loss_score = log_loss(self.y_cal, y_pred_cal)
        
        print(f"  Brier Score: {brier_score:.6f}")
        print(f"  Log Loss: {log_loss_score:.6f}")
        
        return {
            'method': 'isotonic',
            'calibrator': self.isotonic_calibrator,
            'brier_score': brier_score,
            'log_loss': log_loss_score,
            'y_pred_cal': y_pred_cal
        }
    
    def calibrate_platt(self):
        """Calibrate using Platt Scaling"""
        
        print("Calibrating with Platt Scaling...")
        
        y_pred_uncal = self.model.predict_proba(self.X_cal)[:, 1]
        y_pred_uncal_2d = y_pred_uncal.reshape(-1, 1)
        
        self.platt_calibrator = LogisticRegression()
        self.platt_calibrator.fit(y_pred_uncal_2d, self.y_cal)
        
        y_pred_cal = self.platt_calibrator.predict_proba(y_pred_uncal_2d)[:, 1]
        
        brier_score = brier_score_loss(self.y_cal, y_pred_cal)
        log_loss_score = log_loss(self.y_cal, y_pred_cal)
        
        print(f"  Brier Score: {brier_score:.6f}")
        print(f"  Log Loss: {log_loss_score:.6f}")
        
        return {
            'method': 'platt',
            'calibrator': self.platt_calibrator,
            'brier_score': brier_score,
            'log_loss': log_loss_score,
            'y_pred_cal': y_pred_cal
        }
    
    def compare_methods(self):
        """Compare Isotonic vs. Platt and select best"""
        
        print("\n" + "="*60)
        print("CALIBRATION COMPARISON")
        print("="*60 + "\n")
        
        isotonic_results = self.calibrate_isotonic()
        platt_results = self.calibrate_platt()
        
        print(f"\n{'='*60}")
        print("COMPARISON RESULTS")
        print(f"{'='*60}")
        print(f"Isotonic Regression:")
        print(f"  Brier Score: {isotonic_results['brier_score']:.6f}")
        print(f"  Log Loss: {isotonic_results['log_loss']:.6f}")
        print(f"\nPlatt Scaling:")
        print(f"  Brier Score: {platt_results['brier_score']:.6f}")
        print(f"  Log Loss: {platt_results['log_loss']:.6f}")
        
        if isotonic_results['brier_score'] < platt_results['brier_score']:
            self.best_calibrator = isotonic_results['calibrator']
            self.best_method = 'isotonic'
            print(f"\n[SELECTED] Isotonic Regression (lower Brier Score)")
        else:
            self.best_calibrator = platt_results['calibrator']
            self.best_method = 'platt'
            print(f"\n[SELECTED] Platt Scaling (lower Brier Score)")
        
        self.calibration_results = {
            'isotonic': isotonic_results,
            'platt': platt_results,
            'best_method': self.best_method,
            'best_brier_score': min(isotonic_results['brier_score'], platt_results['brier_score'])
        }
        
        print(f"{'='*60}\n")
        
        return self.calibration_results
    
    def create_lookup_table(self, n_bins: int = 100):
        """Create lookup table for database calibration"""
        
        print(f"Creating lookup table ({n_bins} bins)...")
        
        y_pred_uncal = self.model.predict_proba(self.X_cal)[:, 1]
        min_score = y_pred_uncal.min()
        max_score = y_pred_uncal.max()
        
        bins = np.linspace(min_score, max_score, n_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        
        if self.best_method == 'isotonic':
            calibrated_probs = self.best_calibrator.predict(bin_centers)
        else:
            calibrated_probs = self.best_calibrator.predict_proba(bin_centers.reshape(-1, 1))[:, 1]
        
        lookup_table = pd.DataFrame({
            'uncalibrated_score': bin_centers,
            'calibrated_probability': calibrated_probs,
            'bin_lower': bins[:-1],
            'bin_upper': bins[1:]
        })
        
        output_path = self.output_dir / "calibration_lookup_v2_boosted.csv"
        lookup_table.to_csv(output_path, index=False)
        
        print(f"[OK] Lookup table saved to: {output_path}")
        print(f"     Table size: {len(lookup_table)} rows")
        
        return lookup_table
    
    def save_calibrated_model(self):
        """Save calibrated model and metadata"""
        
        print("Saving calibrated boosted model...")
        
        calibrated_model = {
            'base_model': self.model,
            'calibrator': self.best_calibrator,
            'calibration_method': self.best_method,
            'feature_names': self.feature_names,
            'model_version': 'v2-boosted'
        }
        
        model_path = self.output_dir / "calibrated_model_v2_boosted.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(calibrated_model, f)
        
        print(f"[OK] Calibrated model saved to: {model_path}")
        
        metadata = {
            'model_version': 'v2-boosted',
            'calibration_method': self.best_method,
            'brier_score': float(self.calibration_results['best_brier_score']),
            'isotonic_brier': float(self.calibration_results['isotonic']['brier_score']),
            'platt_brier': float(self.calibration_results['platt']['brier_score']),
            'isotonic_log_loss': float(self.calibration_results['isotonic']['log_loss']),
            'platt_log_loss': float(self.calibration_results['platt']['log_loss']),
            'n_calibration_samples': len(self.y_cal),
            'feature_names': self.feature_names,
            'n_features': len(self.feature_names)
        }
        
        metadata_path = self.output_dir / "calibration_metadata_v2_boosted.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"[OK] Calibration metadata saved to: {metadata_path}")
        
        return {
            'model_path': str(model_path),
            'metadata_path': str(metadata_path)
        }
    
    def run_full_calibration(self):
        """Execute complete calibration pipeline"""
        
        print("\n" + "="*60)
        print("BOOSTED MODEL CALIBRATION PIPELINE")
        print("="*60 + "\n")
        
        self.compare_methods()
        lookup_table = self.create_lookup_table(n_bins=100)
        saved_paths = self.save_calibrated_model()
        
        print("\n" + "="*60)
        print("CALIBRATION COMPLETE")
        print("="*60)
        print(f"Best Method: {self.best_method.upper()}")
        print(f"Brier Score: {self.calibration_results['best_brier_score']:.6f}")
        print(f"Calibrated Model: {saved_paths['model_path']}")
        print("="*60 + "\n")
        
        return {
            'best_method': self.best_method,
            'calibration_results': self.calibration_results,
            'lookup_table': lookup_table,
            'saved_paths': saved_paths
        }


if __name__ == "__main__":
    calibrator = BoostedModelCalibrator()
    results = calibrator.run_full_calibration()
    
    print("[OK] Boosted model calibration complete!")

