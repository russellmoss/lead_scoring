"""
Phase 4.2: Hyperparameter Tuning with Optuna
Optimizes XGBoost parameters to reduce overfitting and improve generalization
"""

import numpy as np
import pandas as pd
from pathlib import Path
import xgboost as xgb
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import TimeSeriesSplit
import json
import pickle
import optuna
from optuna.samplers import TPESampler
import warnings
warnings.filterwarnings('ignore')

class HyperparameterTuner:
    def __init__(self, data_dir: str = "data/processed", baseline_dir: str = "models/baseline"):
        self.data_dir = Path(data_dir)
        self.baseline_dir = Path(baseline_dir)
        self.output_dir = Path("models/tuned")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load data from parquet
        print("Loading training data...")
        train_df = pd.read_parquet(self.data_dir / "X_train.parquet")
        target_df = pd.read_parquet(self.data_dir / "y_train.parquet")
        
        # Load feature names (should match baseline)
        with open(self.baseline_dir / "feature_names.json", 'r') as f:
            self.feature_names = json.load(f)
        
        # Ensure columns match
        if list(train_df.columns) != self.feature_names:
            # Filter to only features we're using
            train_df = train_df[[f for f in train_df.columns if f in self.feature_names]]
            train_df = train_df[self.feature_names]  # Reorder
        
        self.X_train = train_df.values
        self.y_train = target_df['target'].values
        
        # Load test data
        print("Loading test data...")
        test_df = pd.read_parquet(self.data_dir / "X_test.parquet")
        target_test_df = pd.read_parquet(self.data_dir / "y_test.parquet")
        
        if list(test_df.columns) != self.feature_names:
            test_df = test_df[[f for f in test_df.columns if f in self.feature_names]]
            test_df = test_df[self.feature_names]
        
        self.X_test = test_df.values
        self.y_test = target_test_df['target'].values
        
        # Calculate class weight
        n_pos = self.y_train.sum()
        n_neg = len(self.y_train) - n_pos
        self.scale_pos_weight = n_neg / n_pos
        
        # Load baseline metrics for comparison
        with open(self.baseline_dir / "baseline_metrics.json", 'r') as f:
            self.baseline_metrics = json.load(f)
        
        print(f"\n{'='*60}")
        print("HYPERPARAMETER TUNING SETUP")
        print(f"{'='*60}")
        print(f"Training samples: {len(self.y_train):,}")
        print(f"Test samples: {len(self.y_test):,}")
        print(f"Features: {len(self.feature_names)}")
        print(f"scale_pos_weight: {self.scale_pos_weight:.2f}")
        print(f"Baseline Test AUC-PR: {self.baseline_metrics['test_metrics']['test_auc_pr']:.4f}")
        print(f"Baseline Test AUC-ROC: {self.baseline_metrics['test_metrics']['test_auc_roc']:.4f}")
        print(f"Baseline Top Decile Lift: {self.baseline_metrics['test_metrics']['top_decile_lift']:.2f}x")
        print(f"{'='*60}\n")
        
        # Results storage
        self.best_params = None
        self.best_model = None
        self.study = None
        self.test_metrics = {}
        
    def objective(self, trial):
        """
        Optuna objective function - optimizes for AUC-PR using Time-Series CV
        """
        
        # Suggest hyperparameters
        params = {
            'objective': 'binary:logistic',
            'scale_pos_weight': self.scale_pos_weight,
            'max_depth': trial.suggest_int('max_depth', 3, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 50, 200),
            'subsample': trial.suggest_float('subsample', 0.6, 0.95),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.95),
            'gamma': trial.suggest_float('gamma', 0, 5),  # Regularization
            'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),  # L1 regularization
            'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),  # L2 regularization
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'eval_metric': 'aucpr',
            'random_state': 42,
            'n_jobs': -1
        }
        
        # 3-Fold Time-Series Cross-Validation
        tscv = TimeSeriesSplit(n_splits=3)
        cv_scores = []
        
        for train_idx, val_idx in tscv.split(self.X_train):
            X_train_fold = self.X_train[train_idx]
            y_train_fold = self.y_train[train_idx]
            X_val_fold = self.X_train[val_idx]
            y_val_fold = self.y_train[val_idx]
            
            # Train model
            model = xgb.XGBClassifier(**params)
            model.fit(
                X_train_fold, y_train_fold,
                eval_set=[(X_val_fold, y_val_fold)],
                verbose=False
            )
            
            # Evaluate on validation fold
            y_val_pred = model.predict_proba(X_val_fold)[:, 1]
            val_auc_pr = average_precision_score(y_val_fold, y_val_pred)
            cv_scores.append(val_auc_pr)
        
        # Return mean CV score (Optuna maximizes)
        return np.mean(cv_scores)
    
    def optimize(self, n_trials: int = 50):
        """
        Run Optuna optimization
        """
        
        print(f"Starting Optuna optimization with {n_trials} trials...")
        print(f"{'='*60}\n")
        
        # Create study
        self.study = optuna.create_study(
            direction='maximize',  # Maximize AUC-PR
            sampler=TPESampler(seed=42)
        )
        
        # Run optimization
        self.study.optimize(
            self.objective,
            n_trials=n_trials,
            show_progress_bar=True
        )
        
        # Get best parameters
        self.best_params = self.study.best_params.copy()
        self.best_params.update({
            'objective': 'binary:logistic',
            'scale_pos_weight': self.scale_pos_weight,
            'eval_metric': 'aucpr',
            'random_state': 42,
            'n_jobs': -1
        })
        
        print(f"\n{'='*60}")
        print("OPTIMIZATION COMPLETE")
        print(f"{'='*60}")
        print(f"Best CV AUC-PR: {self.study.best_value:.4f}")
        print(f"\nBest Parameters:")
        for key, value in self.best_params.items():
            if key not in ['objective', 'scale_pos_weight', 'eval_metric', 'random_state', 'n_jobs']:
                print(f"  {key}: {value}")
        print(f"{'='*60}\n")
        
        # Save best parameters
        params_to_save = {k: v for k, v in self.best_params.items() 
                         if k not in ['objective', 'eval_metric', 'random_state', 'n_jobs']}
        with open(self.output_dir / "best_params.json", 'w') as f:
            json.dump(params_to_save, f, indent=2)
        
        print(f"Best parameters saved to: {self.output_dir / 'best_params.json'}")
        
        return self.best_params
    
    def train_final_model(self):
        """Train final model with best parameters on full training set"""
        
        print("Training final model on full training set...")
        print(f"{'='*60}")
        
        self.best_model = xgb.XGBClassifier(**self.best_params)
        
        self.best_model.fit(
            self.X_train, self.y_train,
            eval_set=[(self.X_train, self.y_train)],
            verbose=False
        )
        
        # Training metrics
        y_train_pred = self.best_model.predict_proba(self.X_train)[:, 1]
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
        
        y_test_pred = self.best_model.predict_proba(self.X_test)[:, 1]
        
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
        
        df = pd.DataFrame({
            'y_true': y_true,
            'y_pred': y_pred
        })
        
        df = df.sort_values('y_pred', ascending=False).reset_index(drop=True)
        
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
    
    def compare_with_baseline(self):
        """Compare tuned model with baseline"""
        
        print("\n" + "="*60)
        print("BASELINE vs TUNED MODEL COMPARISON")
        print("="*60)
        
        baseline_auc_pr = self.baseline_metrics['test_metrics']['test_auc_pr']
        baseline_auc_roc = self.baseline_metrics['test_metrics']['test_auc_roc']
        baseline_lift = self.baseline_metrics['test_metrics']['top_decile_lift']
        
        tuned_auc_pr = self.test_metrics['test_auc_pr']
        tuned_auc_roc = self.test_metrics['test_auc_roc']
        tuned_lift = self.test_metrics['top_decile_lift']
        
        print(f"\nTest AUC-PR:")
        print(f"  Baseline: {baseline_auc_pr:.4f}")
        print(f"  Tuned:    {tuned_auc_pr:.4f}")
        print(f"  Change:   {tuned_auc_pr - baseline_auc_pr:+.4f} ({((tuned_auc_pr / baseline_auc_pr - 1) * 100):+.2f}%)")
        
        print(f"\nTest AUC-ROC:")
        print(f"  Baseline: {baseline_auc_roc:.4f}")
        print(f"  Tuned:    {tuned_auc_roc:.4f}")
        print(f"  Change:   {tuned_auc_roc - baseline_auc_roc:+.4f} ({((tuned_auc_roc / baseline_auc_roc - 1) * 100):+.2f}%)")
        
        print(f"\nTop Decile Lift:")
        print(f"  Baseline: {baseline_lift:.2f}x")
        print(f"  Tuned:    {tuned_lift:.2f}x")
        print(f"  Change:   {tuned_lift - baseline_lift:+.2f}x ({((tuned_lift / baseline_lift - 1) * 100):+.2f}%)")
        
        # Determine if targets met
        auc_pr_improved = tuned_auc_pr > baseline_auc_pr
        lift_improved = tuned_lift > baseline_lift
        
        print(f"\n{'='*60}")
        print("TARGET ACHIEVEMENT:")
        print(f"{'='*60}")
        print(f"AUC-PR Improvement (>0.0802): {'[YES]' if auc_pr_improved else '[NO]'} ({tuned_auc_pr:.4f})")
        print(f"Lift Improvement (>2.2x): {'[YES]' if lift_improved else '[NO]'} ({tuned_lift:.2f}x)")
        print(f"{'='*60}\n")
        
        return {
            'auc_pr_improved': auc_pr_improved,
            'lift_improved': lift_improved,
            'baseline_metrics': {
                'auc_pr': baseline_auc_pr,
                'auc_roc': baseline_auc_roc,
                'lift': baseline_lift
            },
            'tuned_metrics': {
                'auc_pr': tuned_auc_pr,
                'auc_roc': tuned_auc_roc,
                'lift': tuned_lift
            }
        }
    
    def save_model(self):
        """Save tuned model and metadata"""
        
        # Save model
        model_path = self.output_dir / "tuned_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(self.best_model, f)
        print(f"Model saved to: {model_path}")
        
        # Save feature names
        feature_path = self.output_dir / "feature_names.json"
        with open(feature_path, 'w') as f:
            json.dump(self.feature_names, f, indent=2)
        
        # Save metrics
        metrics = {
            'best_cv_auc_pr': float(self.study.best_value),
            'test_metrics': self.test_metrics,
            'best_params': {k: v for k, v in self.best_params.items() 
                          if k not in ['objective', 'eval_metric', 'random_state', 'n_jobs']},
            'scale_pos_weight': float(self.scale_pos_weight),
            'n_features': len(self.feature_names),
            'n_train': len(self.y_train),
            'n_test': len(self.y_test)
        }
        
        metrics_path = self.output_dir / "tuned_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        print(f"Metrics saved to: {metrics_path}")
        
        return {
            'model_path': str(model_path),
            'feature_path': str(feature_path),
            'metrics_path': str(metrics_path)
        }
    
    def run_full_pipeline(self, n_trials: int = 50):
        """Execute complete hyperparameter tuning pipeline"""
        
        print("\n" + "="*60)
        print("HYPERPARAMETER TUNING PIPELINE")
        print("="*60 + "\n")
        
        # Step 1: Optimize hyperparameters
        self.optimize(n_trials=n_trials)
        
        # Step 2: Train final model
        train_metrics = self.train_final_model()
        
        # Step 3: Evaluate on test set
        test_metrics = self.evaluate_test_set()
        
        # Step 4: Compare with baseline
        comparison = self.compare_with_baseline()
        
        # Step 5: Save model
        saved_paths = self.save_model()
        
        return {
            'best_params': self.best_params,
            'best_cv_score': float(self.study.best_value),
            'train_metrics': train_metrics,
            'test_metrics': test_metrics,
            'comparison': comparison,
            'saved_paths': saved_paths
        }


if __name__ == "__main__":
    tuner = HyperparameterTuner()
    results = tuner.run_full_pipeline(n_trials=50)
    
    print("[OK] Hyperparameter tuning complete!")

