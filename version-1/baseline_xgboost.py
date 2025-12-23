"""
Phase 4.1: Baseline XGBoost with Class Imbalance Handling
Establishes baseline performance with proper imbalance handling
"""

import numpy as np
import pandas as pd
from pathlib import Path
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_recall_curve,
    confusion_matrix, classification_report, roc_curve
)
from sklearn.model_selection import TimeSeriesSplit
import json
import pickle
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class BaselineXGBoostTrainer:
    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path("models/baseline")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load data from parquet (more reliable)
        print("Loading training data...")
        train_df = pd.read_parquet(self.data_dir / "X_train.parquet")
        target_df = pd.read_parquet(self.data_dir / "y_train.parquet")
        
        with open(self.data_dir / "feature_names.json", 'r') as f:
            feature_data = json.load(f)
            self.all_feature_names = feature_data['feature_names']
        
        # Ensure columns match
        if list(train_df.columns) != self.all_feature_names:
            train_df.columns = self.all_feature_names
        
        # DROP WEAK FEATURES identified in Phase 3
        # CRITICAL: Remove 'days_in_gap' due to DATA LEAKAGE (retrospective backfilling)
        weak_features_to_drop = [
            'firm_stability_score',  # IV=0.004 - Noise
            'pit_mobility_tier_Average',  # IV=0.004 - Noise
            'days_in_gap'  # DATA LEAKAGE: Not available at inference time (retrospective backfilling)
        ]
        
        print(f"\nDropping features: {weak_features_to_drop}")
        print(f"  CRITICAL: 'days_in_gap' removed due to DATA LEAKAGE")
        print(f"  Other features removed per Phase 3 analysis")
        features_to_keep = [f for f in self.all_feature_names if f not in weak_features_to_drop]
        train_df = train_df[features_to_keep]
        
        self.feature_names = features_to_keep
        self.X_train = train_df.values
        self.y_train = target_df['target'].values
        
        # Load test data
        print("Loading test data...")
        test_df = pd.read_parquet(self.data_dir / "X_test.parquet")
        target_test_df = pd.read_parquet(self.data_dir / "y_test.parquet")
        
        if list(test_df.columns) != self.all_feature_names:
            test_df.columns = self.all_feature_names
        
        test_df = test_df[features_to_keep]
        self.X_test = test_df.values
        self.y_test = target_test_df['target'].values
        
        # Calculate class weight
        n_pos = self.y_train.sum()
        n_neg = len(self.y_train) - n_pos
        self.scale_pos_weight = n_neg / n_pos
        
        print(f"\n{'='*60}")
        print("DATA SUMMARY")
        print(f"{'='*60}")
        print(f"Training samples: {len(self.y_train):,}")
        print(f"  Positive class: {n_pos} ({n_pos/len(self.y_train)*100:.2f}%)")
        print(f"  Negative class: {n_neg} ({n_neg/len(self.y_train)*100:.2f}%)")
        print(f"Test samples: {len(self.y_test):,}")
        print(f"  Positive class: {self.y_test.sum()} ({self.y_test.mean()*100:.2f}%)")
        print(f"scale_pos_weight: {self.scale_pos_weight:.2f}")
        print(f"Features: {len(self.feature_names)}")
        print(f"{'='*60}\n")
        
        # Results storage
        self.cv_results = []
        self.model = None
        self.test_metrics = {}
        
    def train_with_tscv(self, n_splits: int = 5):
        """
        Train with Time-Series Cross-Validation
        Since we don't have a static validation set, use TSCV on training data
        """
        
        print(f"Running {n_splits}-Fold Time-Series Cross-Validation...")
        print(f"{'='*60}")
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        cv_scores_auc_pr = []
        cv_scores_auc_roc = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(self.X_train), 1):
            print(f"\nFold {fold}/{n_splits}:")
            print(f"  Train: {len(train_idx):,} samples")
            print(f"  Val:   {len(val_idx):,} samples")
            
            X_train_fold = self.X_train[train_idx]
            y_train_fold = self.y_train[train_idx]
            X_val_fold = self.X_train[val_idx]
            y_val_fold = self.y_train[val_idx]
            
            # Train model
            model = xgb.XGBClassifier(
                objective='binary:logistic',
                scale_pos_weight=self.scale_pos_weight,
                max_depth=6,
                learning_rate=0.1,
                n_estimators=100,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric='aucpr',  # Optimize for AUC-PR
                n_jobs=-1
            )
            
            model.fit(
                X_train_fold, y_train_fold,
                eval_set=[(X_train_fold, y_train_fold), (X_val_fold, y_val_fold)],
                verbose=False
            )
            
            # Predictions
            y_train_pred = model.predict_proba(X_train_fold)[:, 1]
            y_val_pred = model.predict_proba(X_val_fold)[:, 1]
            
            # Metrics
            train_auc_pr = average_precision_score(y_train_fold, y_train_pred)
            val_auc_pr = average_precision_score(y_val_fold, y_val_pred)
            train_auc_roc = roc_auc_score(y_train_fold, y_train_pred)
            val_auc_roc = roc_auc_score(y_val_fold, y_val_pred)
            
            cv_scores_auc_pr.append(val_auc_pr)
            cv_scores_auc_roc.append(val_auc_roc)
            
            print(f"  Train AUC-PR: {train_auc_pr:.4f}, Train AUC-ROC: {train_auc_roc:.4f}")
            print(f"  Val   AUC-PR: {val_auc_pr:.4f}, Val   AUC-ROC: {val_auc_roc:.4f}")
            
            self.cv_results.append({
                'fold': fold,
                'train_auc_pr': float(train_auc_pr),
                'val_auc_pr': float(val_auc_pr),
                'train_auc_roc': float(train_auc_roc),
                'val_auc_roc': float(val_auc_roc),
                'train_size': len(train_idx),
                'val_size': len(val_idx)
            })
        
        # Summary
        mean_auc_pr = np.mean(cv_scores_auc_pr)
        std_auc_pr = np.std(cv_scores_auc_pr)
        mean_auc_roc = np.mean(cv_scores_auc_roc)
        std_auc_roc = np.std(cv_scores_auc_roc)
        
        print(f"\n{'='*60}")
        print("CROSS-VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Mean AUC-PR:  {mean_auc_pr:.4f} (+/- {std_auc_pr:.4f})")
        print(f"Mean AUC-ROC: {mean_auc_roc:.4f} (+/- {std_auc_roc:.4f})")
        print(f"{'='*60}\n")
        
        return {
            'mean_auc_pr': float(mean_auc_pr),
            'std_auc_pr': float(std_auc_pr),
            'mean_auc_roc': float(mean_auc_roc),
            'std_auc_roc': float(std_auc_roc),
            'cv_scores_auc_pr': [float(s) for s in cv_scores_auc_pr],
            'cv_scores_auc_roc': [float(s) for s in cv_scores_auc_roc]
        }
    
    def train_final_model(self):
        """Train final model on full training set"""
        
        print("Training final model on full training set...")
        print(f"{'='*60}")
        
        self.model = xgb.XGBClassifier(
            objective='binary:logistic',
            scale_pos_weight=self.scale_pos_weight,
            max_depth=6,
            learning_rate=0.1,
            n_estimators=100,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='aucpr',
            n_jobs=-1
        )
        
        self.model.fit(
            self.X_train, self.y_train,
            eval_set=[(self.X_train, self.y_train)],
            verbose=False
        )
        
        # Training metrics
        y_train_pred = self.model.predict_proba(self.X_train)[:, 1]
        train_auc_pr = average_precision_score(self.y_train, y_train_pred)
        train_auc_roc = roc_auc_score(self.y_train, y_train_pred)
        
        print(f"Training AUC-PR:  {train_auc_pr:.4f}")
        print(f"Training AUC-ROC: {train_auc_roc:.4f}")
        print(f"{'='*60}\n")
        
        return {
            'train_auc_pr': float(train_auc_pr),
            'train_auc_roc': float(train_auc_roc)
        }
    
    def evaluate_test_set(self):
        """Evaluate on held-out test set"""
        
        print("Evaluating on test set...")
        print(f"{'='*60}")
        
        y_test_pred = self.model.predict_proba(self.X_test)[:, 1]
        
        # Metrics
        test_auc_pr = average_precision_score(self.y_test, y_test_pred)
        test_auc_roc = roc_auc_score(self.y_test, y_test_pred)
        
        # Calculate lift chart
        lift_results = self.calculate_lift_chart(self.y_test, y_test_pred)
        
        self.test_metrics = {
            'test_auc_pr': float(test_auc_pr),
            'test_auc_roc': float(test_auc_roc),
            'baseline_rate': float(self.y_test.mean()),
            'top_decile_rate': float(lift_results['top_decile_rate']),
            'top_decile_lift': float(lift_results['top_decile_lift']),
            'lift_chart': lift_results['decile_rates']
        }
        
        print(f"Test AUC-PR:  {test_auc_pr:.4f}")
        print(f"Test AUC-ROC: {test_auc_roc:.4f}")
        print(f"\nLift Chart:")
        print(f"  Baseline conversion rate: {self.test_metrics['baseline_rate']:.2%}")
        print(f"  Top decile conversion rate: {self.test_metrics['top_decile_rate']:.2%}")
        print(f"  Top decile lift: {self.test_metrics['top_decile_lift']:.2f}x")
        print(f"{'='*60}\n")
        
        return self.test_metrics
    
    def calculate_lift_chart(self, y_true, y_pred, n_deciles: int = 10):
        """Calculate lift chart by deciles"""
        
        # Create dataframe for sorting
        df = pd.DataFrame({
            'y_true': y_true,
            'y_pred': y_pred
        })
        
        # Sort by predicted probability (descending)
        df = df.sort_values('y_pred', ascending=False).reset_index(drop=True)
        
        # Calculate deciles
        n_samples = len(df)
        decile_size = n_samples // n_deciles
        
        decile_rates = []
        for i in range(n_deciles):
            start_idx = i * decile_size
            end_idx = (i + 1) * decile_size if i < n_deciles - 1 else n_samples
            decile_df = df.iloc[start_idx:end_idx]
            decile_rate = decile_df['y_true'].mean()
            decile_rates.append({
                'decile': i + 1,
                'conversion_rate': float(decile_rate),
                'n_samples': len(decile_df)
            })
        
        baseline_rate = y_true.mean()
        top_decile_rate = decile_rates[0]['conversion_rate']
        top_decile_lift = top_decile_rate / baseline_rate if baseline_rate > 0 else 0
        
        return {
            'decile_rates': decile_rates,
            'top_decile_rate': top_decile_rate,
            'top_decile_lift': top_decile_lift,
            'baseline_rate': float(baseline_rate)
        }
    
    def plot_lift_chart(self, save_path: Path = None):
        """Plot lift chart visualization"""
        
        if not self.test_metrics:
            print("Error: Must evaluate test set first")
            return
        
        decile_rates = self.test_metrics['lift_chart']
        baseline_rate = self.test_metrics['baseline_rate']
        
        deciles = [d['decile'] for d in decile_rates]
        rates = [d['conversion_rate'] for d in decile_rates]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.bar(deciles, rates, alpha=0.7, color='steelblue')
        ax.axhline(y=baseline_rate, color='r', linestyle='--', 
                  label=f'Baseline ({baseline_rate:.2%})')
        ax.set_xlabel('Decile (1 = Highest Score)')
        ax.set_ylabel('Conversion Rate')
        ax.set_title('Lift Chart: Conversion Rate by Decile')
        ax.legend()
        ax.grid(alpha=0.3)
        
        # Add value labels on bars
        for i, (decile, rate) in enumerate(zip(deciles, rates)):
            ax.text(decile, rate, f'{rate:.2%}', 
                   ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150)
            plt.close()
            print(f"Lift chart saved to: {save_path}")
        else:
            plt.show()
    
    def save_model(self):
        """Save model and metadata"""
        
        # Save model
        model_path = self.output_dir / "baseline_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        print(f"Model saved to: {model_path}")
        
        # Save feature names
        feature_path = self.output_dir / "feature_names.json"
        with open(feature_path, 'w') as f:
            json.dump(self.feature_names, f, indent=2)
        print(f"Feature names saved to: {feature_path}")
        
        # Save metrics
        metrics = {
            'cv_results': self.cv_results,
            'test_metrics': self.test_metrics,
            'scale_pos_weight': float(self.scale_pos_weight),
            'n_features': len(self.feature_names),
            'n_train': len(self.y_train),
            'n_test': len(self.y_test)
        }
        
        metrics_path = self.output_dir / "baseline_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        print(f"Metrics saved to: {metrics_path}")
        
        return {
            'model_path': str(model_path),
            'feature_path': str(feature_path),
            'metrics_path': str(metrics_path)
        }
    
    def run_full_pipeline(self):
        """Execute complete training pipeline"""
        
        print("\n" + "="*60)
        print("BASELINE XGBOOST TRAINING PIPELINE")
        print("="*60 + "\n")
        
        # Step 1: Time-series cross-validation
        cv_summary = self.train_with_tscv(n_splits=5)
        
        # Step 2: Train final model
        train_metrics = self.train_final_model()
        
        # Step 3: Evaluate on test set
        test_metrics = self.evaluate_test_set()
        
        # Step 4: Generate lift chart
        self.plot_lift_chart(self.output_dir / "lift_chart.png")
        
        # Step 5: Save model
        saved_paths = self.save_model()
        
        # Final summary
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        print(f"Cross-Validation AUC-PR:  {cv_summary['mean_auc_pr']:.4f} (+/- {cv_summary['std_auc_pr']:.4f})")
        print(f"Cross-Validation AUC-ROC: {cv_summary['mean_auc_roc']:.4f} (+/- {cv_summary['std_auc_roc']:.4f})")
        print(f"\nTest AUC-PR:  {test_metrics['test_auc_pr']:.4f}")
        print(f"Test AUC-ROC: {test_metrics['test_auc_roc']:.4f}")
        print(f"\nTop Decile Lift: {test_metrics['top_decile_lift']:.2f}x")
        print(f"  Baseline: {test_metrics['baseline_rate']:.2%}")
        print(f"  Top Decile: {test_metrics['top_decile_rate']:.2%}")
        print("="*60 + "\n")
        
        return {
            'cv_summary': cv_summary,
            'train_metrics': train_metrics,
            'test_metrics': test_metrics,
            'saved_paths': saved_paths
        }


if __name__ == "__main__":
    trainer = BaselineXGBoostTrainer()
    results = trainer.run_full_pipeline()
    
    print("[OK] Baseline XGBoost training complete!")

