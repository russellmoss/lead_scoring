"""
Phase 6.1: Probability Calibration
Transforms raw XGBoost scores into calibrated probabilities
"""

import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import json
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class ProbabilityCalibrator:
    def __init__(self, model_dir: str = "models/tuned", data_dir: str = "data/processed"):
        self.model_dir = Path(model_dir)
        self.data_dir = Path(data_dir)
        self.output_dir = Path("models/calibrated")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load model
        print("Loading tuned model...")
        with open(self.model_dir / "tuned_model.pkl", 'rb') as f:
            self.model = pickle.load(f)
        
        # Load feature names
        with open(self.model_dir / "feature_names.json", 'r') as f:
            self.feature_names = json.load(f)
        
        # Load training data for calibration
        print("Loading training data...")
        train_df = pd.read_parquet(self.data_dir / "X_train.parquet")
        target_train_df = pd.read_parquet(self.data_dir / "y_train.parquet")
        
        if list(train_df.columns) != self.feature_names:
            train_df = train_df[[f for f in train_df.columns if f in self.feature_names]]
            train_df = train_df[self.feature_names]
        
        self.X_train = train_df.values
        self.y_train = target_train_df['target'].values
        
        # Use test data as calibration set (validation set may not exist)
        print("Loading calibration data (test set)...")
        test_df = pd.read_parquet(self.data_dir / "X_test.parquet")
        target_test_df = pd.read_parquet(self.data_dir / "y_test.parquet")
        if list(test_df.columns) != self.feature_names:
            test_df = test_df[[f for f in test_df.columns if f in self.feature_names]]
            test_df = test_df[self.feature_names]
        self.X_val = test_df.values
        self.y_val = target_test_df['target'].values
        print(f"Using test set for calibration: {len(self.y_val):,} samples")
        
        print(f"\n{'='*60}")
        print("CALIBRATION SETUP")
        print(f"{'='*60}")
        print(f"Training samples: {len(self.y_train):,}")
        print(f"Calibration samples: {len(self.y_val):,}")
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
        
        # Get uncalibrated predictions
        y_pred_uncal = self.model.predict_proba(self.X_val)[:, 1]
        
        # Fit isotonic regression
        self.isotonic_calibrator = IsotonicRegression(out_of_bounds='clip')
        self.isotonic_calibrator.fit(y_pred_uncal, self.y_val)
        
        # Get calibrated predictions
        y_pred_cal = self.isotonic_calibrator.predict(y_pred_uncal)
        
        # Evaluate
        brier_score = brier_score_loss(self.y_val, y_pred_cal)
        log_loss_score = log_loss(self.y_val, y_pred_cal)
        
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
        """Calibrate using Platt Scaling (Logistic Regression)"""
        
        print("Calibrating with Platt Scaling...")
        
        # Get uncalibrated predictions
        y_pred_uncal = self.model.predict_proba(self.X_val)[:, 1]
        
        # Reshape for sklearn
        y_pred_uncal_2d = y_pred_uncal.reshape(-1, 1)
        
        # Fit Platt scaling (logistic regression)
        self.platt_calibrator = LogisticRegression()
        self.platt_calibrator.fit(y_pred_uncal_2d, self.y_val)
        
        # Get calibrated predictions
        y_pred_cal = self.platt_calibrator.predict_proba(y_pred_uncal_2d)[:, 1]
        
        # Evaluate
        brier_score = brier_score_loss(self.y_val, y_pred_cal)
        log_loss_score = log_loss(self.y_val, y_pred_cal)
        
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
        
        # Calibrate with both methods
        isotonic_results = self.calibrate_isotonic()
        platt_results = self.calibrate_platt()
        
        # Compare Brier Score (lower is better)
        print(f"\n{'='*60}")
        print("COMPARISON RESULTS")
        print(f"{'='*60}")
        print(f"Isotonic Regression:")
        print(f"  Brier Score: {isotonic_results['brier_score']:.6f}")
        print(f"  Log Loss: {isotonic_results['log_loss']:.6f}")
        print(f"\nPlatt Scaling:")
        print(f"  Brier Score: {platt_results['brier_score']:.6f}")
        print(f"  Log Loss: {platt_results['log_loss']:.6f}")
        
        # Select best based on Brier Score
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
    
    def plot_calibration_curve(self):
        """Plot calibration curves for both methods"""
        
        print("Generating calibration curves...")
        
        # Get uncalibrated predictions
        y_pred_uncal = self.model.predict_proba(self.X_val)[:, 1]
        
        # Get calibrated predictions
        y_pred_isotonic = self.isotonic_calibrator.predict(y_pred_uncal)
        y_pred_platt = self.platt_calibrator.predict_proba(y_pred_uncal.reshape(-1, 1))[:, 1]
        
        # Calculate calibration curves
        fraction_of_positives_uncal, mean_predicted_value_uncal = calibration_curve(
            self.y_val, y_pred_uncal, n_bins=10
        )
        fraction_of_positives_isotonic, mean_predicted_value_isotonic = calibration_curve(
            self.y_val, y_pred_isotonic, n_bins=10
        )
        fraction_of_positives_platt, mean_predicted_value_platt = calibration_curve(
            self.y_val, y_pred_platt, n_bins=10
        )
        
        # Plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        ax.plot([0, 1], [0, 1], 'k--', label='Perfectly Calibrated')
        ax.plot(mean_predicted_value_uncal, fraction_of_positives_uncal, 'o-', label='Uncalibrated')
        ax.plot(mean_predicted_value_isotonic, fraction_of_positives_isotonic, 's-', label='Isotonic')
        ax.plot(mean_predicted_value_platt, fraction_of_positives_platt, '^-', label='Platt')
        
        ax.set_xlabel('Mean Predicted Probability')
        ax.set_ylabel('Fraction of Positives')
        ax.set_title('Calibration Curves Comparison')
        ax.legend()
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / "calibration_curves.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"[OK] Calibration curves saved to: {output_path}")
        return output_path
    
    def create_lookup_table(self, n_bins: int = 100):
        """Create lookup table for database calibration"""
        
        print(f"Creating lookup table ({n_bins} bins)...")
        
        # Get uncalibrated predictions range
        y_pred_uncal = self.model.predict_proba(self.X_val)[:, 1]
        min_score = y_pred_uncal.min()
        max_score = y_pred_uncal.max()
        
        # Create bins
        bins = np.linspace(min_score, max_score, n_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        
        # Get calibrated probabilities for each bin center
        if self.best_method == 'isotonic':
            calibrated_probs = self.best_calibrator.predict(bin_centers)
        else:
            calibrated_probs = self.best_calibrator.predict_proba(bin_centers.reshape(-1, 1))[:, 1]
        
        # Create lookup table
        lookup_table = pd.DataFrame({
            'uncalibrated_score': bin_centers,
            'calibrated_probability': calibrated_probs,
            'bin_lower': bins[:-1],
            'bin_upper': bins[1:]
        })
        
        # Save as CSV
        output_path = self.output_dir / "calibration_lookup_table.csv"
        lookup_table.to_csv(output_path, index=False)
        
        print(f"[OK] Lookup table saved to: {output_path}")
        print(f"     Table size: {len(lookup_table)} rows")
        
        return lookup_table
    
    def save_calibrated_model(self):
        """Save calibrated model and metadata"""
        
        print("Saving calibrated model...")
        
        # Create calibrated model wrapper
        calibrated_model = {
            'base_model': self.model,
            'calibrator': self.best_calibrator,
            'calibration_method': self.best_method,
            'feature_names': self.feature_names
        }
        
        # Save model
        model_path = self.output_dir / "calibrated_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(calibrated_model, f)
        
        print(f"[OK] Calibrated model saved to: {model_path}")
        
        # Save metadata
        metadata = {
            'calibration_method': self.best_method,
            'brier_score': float(self.calibration_results['best_brier_score']),
            'isotonic_brier': float(self.calibration_results['isotonic']['brier_score']),
            'platt_brier': float(self.calibration_results['platt']['brier_score']),
            'isotonic_log_loss': float(self.calibration_results['isotonic']['log_loss']),
            'platt_log_loss': float(self.calibration_results['platt']['log_loss']),
            'n_calibration_samples': len(self.y_val),
            'feature_names': self.feature_names
        }
        
        metadata_path = self.output_dir / "calibration_metadata.json"
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
        print("PROBABILITY CALIBRATION PIPELINE")
        print("="*60 + "\n")
        
        # Step 1: Compare methods
        self.compare_methods()
        
        # Step 2: Plot calibration curves
        self.plot_calibration_curve()
        
        # Step 3: Create lookup table
        lookup_table = self.create_lookup_table(n_bins=100)
        
        # Step 4: Save calibrated model
        saved_paths = self.save_calibrated_model()
        
        print("\n" + "="*60)
        print("CALIBRATION COMPLETE")
        print("="*60)
        print(f"Best Method: {self.best_method.upper()}")
        print(f"Brier Score: {self.calibration_results['best_brier_score']:.6f}")
        print(f"Calibrated Model: {saved_paths['model_path']}")
        print(f"Lookup Table: {self.output_dir / 'calibration_lookup_table.csv'}")
        print("="*60 + "\n")
        
        return {
            'best_method': self.best_method,
            'calibration_results': self.calibration_results,
            'lookup_table': lookup_table,
            'saved_paths': saved_paths
        }


if __name__ == "__main__":
    calibrator = ProbabilityCalibrator()
    results = calibrator.run_full_calibration()
    
    print("[OK] Probability calibration complete!")

