"""
Phase 4.3: Feature Boost
Engineers new features to recover performance without data leakage
"""

import numpy as np
import pandas as pd
from pathlib import Path
import xgboost as xgb
from sklearn.metrics import (
    roc_auc_score, average_precision_score
)
from sklearn.model_selection import TimeSeriesSplit
import json
import pickle
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class FeatureBoostTrainer:
    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path("models/boosted")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load data
        print("Loading training data...")
        train_df = pd.read_parquet(self.data_dir / "X_train.parquet")
        target_train_df = pd.read_parquet(self.data_dir / "y_train.parquet")
        
        test_df = pd.read_parquet(self.data_dir / "X_test.parquet")
        target_test_df = pd.read_parquet(self.data_dir / "y_test.parquet")
        
        # Load feature names
        with open(self.data_dir / "feature_names.json", 'r') as f:
            feature_data = json.load(f)
            self.all_feature_names = feature_data['feature_names']
        
        # Ensure columns match
        if list(train_df.columns) != self.all_feature_names:
            train_df.columns = self.all_feature_names
        if list(test_df.columns) != self.all_feature_names:
            test_df.columns = self.all_feature_names
        
        # Drop leaking/weak features (same as honest model)
        features_to_drop = [
            'firm_stability_score',
            'pit_mobility_tier_Average',
            'days_in_gap'  # DATA LEAKAGE
        ]
        
        print(f"\nDropping features: {features_to_drop}")
        features_base = [f for f in self.all_feature_names if f not in features_to_drop]
        
        train_df = train_df[features_base]
        test_df = test_df[features_base]
        
        # ENGINEER NEW FEATURES
        print("\n" + "="*60)
        print("ENGINEERING BOOSTER FEATURES")
        print("="*60)
        
        # Feature 1: pit_restlessness_ratio
        print("\n1. Creating 'pit_restlessness_ratio'...")
        # Calculate average prior firm tenure from num_prior_firms and industry_tenure
        # avg_prior_firm_tenure = (industry_tenure - current_firm_tenure) / max(num_prior_firms, 1)
        train_df['avg_prior_firm_tenure_months'] = (
            (train_df['industry_tenure_months'] - train_df['current_firm_tenure_months']) / 
            train_df['num_prior_firms'].clip(lower=1)
        ).fillna(0).clip(lower=0)  # Ensure non-negative
        
        test_df['avg_prior_firm_tenure_months'] = (
            (test_df['industry_tenure_months'] - test_df['current_firm_tenure_months']) / 
            test_df['num_prior_firms'].clip(lower=1)
        ).fillna(0).clip(lower=0)  # Ensure non-negative
        
        # Calculate restlessness ratio with safe division
        # If avg_prior is 0 or very small, use current_tenure directly (no prior history)
        train_df['pit_restlessness_ratio'] = np.where(
            train_df['avg_prior_firm_tenure_months'] > 0.1,  # Threshold to avoid division by tiny numbers
            train_df['current_firm_tenure_months'] / train_df['avg_prior_firm_tenure_months'],
            train_df['current_firm_tenure_months']  # If no prior history, use current tenure as proxy
        )
        train_df['pit_restlessness_ratio'] = train_df['pit_restlessness_ratio'].replace([np.inf, -np.inf], 0).fillna(0).clip(upper=100)  # Cap at 100
        
        test_df['pit_restlessness_ratio'] = np.where(
            test_df['avg_prior_firm_tenure_months'] > 0.1,
            test_df['current_firm_tenure_months'] / test_df['avg_prior_firm_tenure_months'],
            test_df['current_firm_tenure_months']
        )
        test_df['pit_restlessness_ratio'] = test_df['pit_restlessness_ratio'].replace([np.inf, -np.inf], 0).fillna(0).clip(upper=100)  # Cap at 100
        
        print(f"   Mean restlessness ratio (train): {train_df['pit_restlessness_ratio'].mean():.2f}")
        print(f"   Mean restlessness ratio (test): {test_df['pit_restlessness_ratio'].mean():.2f}")
        
        # Feature 2: flight_risk_score
        print("\n2. Creating 'flight_risk_score'...")
        # flight_risk = pit_moves_3yr * (firm_net_change_12mo * -1)
        # Negative net change means firm is losing advisors (bleeding)
        # Clip firm_net_change to reasonable range to avoid extreme values
        train_df['flight_risk_score'] = (
            train_df['pit_moves_3yr'] * (train_df['firm_net_change_12mo'].clip(-100, 100) * -1)
        ).fillna(0).clip(-1000, 1000)  # Cap extreme values
        
        test_df['flight_risk_score'] = (
            test_df['pit_moves_3yr'] * (test_df['firm_net_change_12mo'].clip(-100, 100) * -1)
        ).fillna(0).clip(-1000, 1000)  # Cap extreme values
        
        print(f"   Mean flight risk (train): {train_df['flight_risk_score'].mean():.2f}")
        print(f"   Mean flight risk (test): {test_df['flight_risk_score'].mean():.2f}")
        
        # Feature 3: is_fresh_start
        print("\n3. Creating 'is_fresh_start'...")
        train_df['is_fresh_start'] = (train_df['current_firm_tenure_months'] < 12).astype(int)
        test_df['is_fresh_start'] = (test_df['current_firm_tenure_months'] < 12).astype(int)
        
        fresh_start_pct_train = train_df['is_fresh_start'].mean() * 100
        fresh_start_pct_test = test_df['is_fresh_start'].mean() * 100
        print(f"   Fresh start rate (train): {fresh_start_pct_train:.1f}%")
        print(f"   Fresh start rate (test): {fresh_start_pct_test:.1f}%")
        
        # Compile final feature set
        self.feature_names = features_base + [
            'pit_restlessness_ratio',
            'flight_risk_score',
            'is_fresh_start'
        ]
        
        train_df = train_df[self.feature_names]
        test_df = test_df[self.feature_names]
        
        self.X_train = train_df.values
        self.y_train = target_train_df['target'].values
        
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
        print(f"Features: {len(self.feature_names)} (base: {len(features_base)}, new: 3)")
        print(f"{'='*60}\n")
        
        # Results storage
        self.cv_results = []
        self.model = None
        self.test_metrics = {}
        
    def train_with_tscv(self, n_splits: int = 5):
        """Train with Time-Series Cross-Validation"""
        
        print(f"Running {n_splits}-Fold Time-Series Cross-Validation...")
        print(f"{'='*60}")
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        cv_scores_auc_pr = []
        cv_scores_auc_roc = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(self.X_train)):
            X_train_fold = self.X_train[train_idx]
            y_train_fold = self.y_train[train_idx]
            X_val_fold = self.X_train[val_idx]
            y_val_fold = self.y_train[val_idx]
            
            model = xgb.XGBClassifier(
                objective='binary:logistic',
                eval_metric='aucpr',
                scale_pos_weight=self.scale_pos_weight,
                use_label_encoder=False,
                n_estimators=100,
                learning_rate=0.1,
                max_depth=3,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )
            
            model.fit(X_train_fold, y_train_fold, verbose=False)
            
            y_train_pred = model.predict_proba(X_train_fold)[:, 1]
            y_val_pred = model.predict_proba(X_val_fold)[:, 1]
            
            train_auc_pr = average_precision_score(y_train_fold, y_train_pred)
            train_auc_roc = roc_auc_score(y_train_fold, y_train_pred)
            val_auc_pr = average_precision_score(y_val_fold, y_val_pred)
            val_auc_roc = roc_auc_score(y_val_fold, y_val_pred)
            
            print(f"Fold {fold+1}/{n_splits}:")
            print(f"  Train AUC-PR: {train_auc_pr:.4f}, Train AUC-ROC: {train_auc_roc:.4f}")
            print(f"  Val   AUC-PR: {val_auc_pr:.4f}, Val   AUC-ROC: {val_auc_roc:.4f}")
            
            cv_scores_auc_pr.append(val_auc_pr)
            cv_scores_auc_roc.append(val_auc_roc)
            
            self.cv_results.append({
                'fold': fold + 1,
                'train_auc_pr': train_auc_pr,
                'val_auc_pr': val_auc_pr,
                'train_auc_roc': train_auc_roc,
                'val_auc_roc': val_auc_roc
            })
        
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
        
    def train_final_model(self):
        """Train final model on full training set"""
        
        print("Training final model on full training set...")
        print(f"{'='*60}")
        
        self.model = xgb.XGBClassifier(
            objective='binary:logistic',
            eval_metric='aucpr',
            scale_pos_weight=self.scale_pos_weight,
            use_label_encoder=False,
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        self.model.fit(self.X_train, self.y_train, verbose=False)
        
        y_train_pred = self.model.predict_proba(self.X_train)[:, 1]
        train_auc_pr = average_precision_score(self.y_train, y_train_pred)
        train_auc_roc = roc_auc_score(self.y_train, y_train_pred)
        
        print(f"Training AUC-PR:  {train_auc_pr:.4f}")
        print(f"Training AUC-ROC: {train_auc_roc:.4f}")
        print(f"{'='*60}\n")
        
    def evaluate_test_set(self):
        """Evaluate on held-out test set"""
        
        print("Evaluating on test set...")
        print(f"{'='*60}")
        
        y_test_pred = self.model.predict_proba(self.X_test)[:, 1]
        
        test_auc_pr = average_precision_score(self.y_test, y_test_pred)
        test_auc_roc = roc_auc_score(self.y_test, y_test_pred)
        
        # Calculate lift chart
        test_results = pd.DataFrame({
            'y_true': self.y_test,
            'y_pred_proba': y_test_pred
        })
        test_results = test_results.sort_values(by='y_pred_proba', ascending=False).reset_index(drop=True)
        
        n_samples = len(test_results)
        decile_size = n_samples // 10
        
        baseline_rate = self.y_test.mean()
        
        lift_data = []
        print("\nLift Chart:")
        print(f"  Baseline conversion rate: {baseline_rate:.2%}")
        
        for i in range(10):
            start_idx = i * decile_size
            end_idx = (i + 1) * decile_size if i < 9 else n_samples
            
            decile_df = test_results.iloc[start_idx:end_idx]
            decile_conversion_rate = decile_df['y_true'].mean()
            
            lift_data.append({
                'decile': i + 1,
                'conversion_rate': decile_conversion_rate,
                'n_samples': len(decile_df)
            })
            
            if i == 0:  # Top decile
                top_decile_rate = decile_conversion_rate
                top_decile_lift = top_decile_rate / baseline_rate if baseline_rate > 0 else np.inf
                print(f"  Top decile conversion rate: {top_decile_rate:.2%}")
                print(f"  Top decile lift: {top_decile_lift:.2f}x")
        
        print(f"{'='*60}\n")
        
        self.test_metrics = {
            'test_auc_pr': float(test_auc_pr),
            'test_auc_roc': float(test_auc_roc),
            'baseline_rate': float(baseline_rate),
            'top_decile_rate': float(top_decile_rate),
            'top_decile_lift': float(top_decile_lift),
            'lift_chart': lift_data
        }
        
        return self.test_metrics
    
    def compare_with_baseline(self):
        """Compare with honest baseline model"""
        
        # Load baseline metrics
        baseline_path = Path("models/baseline/baseline_metrics.json")
        if baseline_path.exists():
            with open(baseline_path, 'r') as f:
                baseline_metrics = json.load(f)
            
            baseline_lift = baseline_metrics['test_metrics']['top_decile_lift']
            baseline_auc_pr = baseline_metrics['test_metrics']['test_auc_pr']
            baseline_auc_roc = baseline_metrics['test_metrics']['test_auc_roc']
            
            print("\n" + "="*60)
            print("BOOSTED vs BASELINE COMPARISON")
            print("="*60)
            
            print(f"\nTest AUC-PR:")
            print(f"  Baseline (honest): {baseline_auc_pr:.4f}")
            print(f"  Boosted:           {self.test_metrics['test_auc_pr']:.4f}")
            change_auc_pr = self.test_metrics['test_auc_pr'] - baseline_auc_pr
            pct_change_auc_pr = (change_auc_pr / baseline_auc_pr * 100) if baseline_auc_pr > 0 else 0
            print(f"  Change:            {change_auc_pr:+.4f} ({pct_change_auc_pr:+.1f}%)")
            
            print(f"\nTest AUC-ROC:")
            print(f"  Baseline (honest): {baseline_auc_roc:.4f}")
            print(f"  Boosted:           {self.test_metrics['test_auc_roc']:.4f}")
            change_auc_roc = self.test_metrics['test_auc_roc'] - baseline_auc_roc
            pct_change_auc_roc = (change_auc_roc / baseline_auc_roc * 100) if baseline_auc_roc > 0 else 0
            print(f"  Change:            {change_auc_roc:+.4f} ({pct_change_auc_roc:+.1f}%)")
            
            print(f"\nTop Decile Lift:")
            print(f"  Baseline (honest): {baseline_lift:.2f}x")
            print(f"  Boosted:           {self.test_metrics['top_decile_lift']:.2f}x")
            change_lift = self.test_metrics['top_decile_lift'] - baseline_lift
            pct_change_lift = (change_lift / baseline_lift * 100) if baseline_lift > 0 else 0
            print(f"  Change:            {change_lift:+.2f}x ({pct_change_lift:+.1f}%)")
            
            # Target achievement
            target_lift = 1.9
            achieved_target = self.test_metrics['top_decile_lift'] >= target_lift
            
            print(f"\n{'='*60}")
            print("TARGET ACHIEVEMENT")
            print(f"{'='*60}")
            print(f"Target Lift: 1.9x")
            print(f"Achieved:    {self.test_metrics['top_decile_lift']:.2f}x")
            print(f"Status:      {'[SUCCESS] Target Met!' if achieved_target else '[PARTIAL] Below target but improved'}")
            print(f"{'='*60}\n")
            
            return {
                'baseline_lift': baseline_lift,
                'boosted_lift': self.test_metrics['top_decile_lift'],
                'improvement': change_lift,
                'achieved_target': achieved_target
            }
        else:
            print("Warning: Baseline metrics not found for comparison")
            return None
    
    def save_model(self):
        """Save model if lift > 1.85x"""
        
        if self.test_metrics['top_decile_lift'] > 1.85:
            print(f"Saving boosted model (Lift: {self.test_metrics['top_decile_lift']:.2f}x > 1.85x)...")
            
            # Save model
            model_path = self.output_dir / "model_v2_boosted.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            print(f"[OK] Model saved to: {model_path}")
            
            # Save feature names
            feature_path = self.output_dir / "feature_names_v2_boosted.json"
            with open(feature_path, 'w') as f:
                json.dump(self.feature_names, f, indent=2)
            print(f"[OK] Feature names saved to: {feature_path}")
            
            # Save metrics
            metrics = {
                'cv_results': self.cv_results,
                'test_metrics': self.test_metrics,
                'scale_pos_weight': float(self.scale_pos_weight),
                'n_features': len(self.feature_names),
                'n_train': len(self.y_train),
                'n_test': len(self.y_test),
                'new_features': ['pit_restlessness_ratio', 'flight_risk_score', 'is_fresh_start']
            }
            
            metrics_path = self.output_dir / "boosted_metrics.json"
            with open(metrics_path, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            print(f"[OK] Metrics saved to: {metrics_path}")
            
            # Plot lift chart
            plt.figure(figsize=(10, 6))
            deciles = [d['decile'] for d in self.test_metrics['lift_chart']]
            conversion_rates = [d['conversion_rate'] for d in self.test_metrics['lift_chart']]
            
            plt.bar(deciles, conversion_rates, color='steelblue')
            plt.axhline(y=self.test_metrics['baseline_rate'], color='r', linestyle='--', 
                       label=f'Baseline Rate ({self.test_metrics["baseline_rate"]:.2%})')
            plt.xlabel('Decile')
            plt.ylabel('Conversion Rate')
            plt.title(f'Boosted Model Lift Chart (Lift: {self.test_metrics["top_decile_lift"]:.2f}x)')
            plt.xticks(deciles)
            plt.legend()
            plt.grid(axis='y', linestyle='--')
            plt.savefig(self.output_dir / "lift_chart_boosted.png")
            plt.close()
            
            print(f"[OK] Lift chart saved to: {self.output_dir / 'lift_chart_boosted.png'}")
            
            return {
                'model_path': str(model_path),
                'feature_path': str(feature_path),
                'metrics_path': str(metrics_path)
            }
        else:
            print(f"Model not saved (Lift: {self.test_metrics['top_decile_lift']:.2f}x <= 1.85x threshold)")
            return None
    
    def run_full_pipeline(self):
        """Execute complete feature boost pipeline"""
        
        print("\n" + "="*60)
        print("FEATURE BOOST TRAINING PIPELINE")
        print("="*60 + "\n")
        
        # Step 1: Train with CV
        self.train_with_tscv(n_splits=5)
        
        # Step 2: Train final model
        self.train_final_model()
        
        # Step 3: Evaluate on test set
        test_metrics = self.evaluate_test_set()
        
        # Step 4: Compare with baseline
        comparison = self.compare_with_baseline()
        
        # Step 5: Save if threshold met
        saved_paths = self.save_model()
        
        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        print(f"Test AUC-PR:  {test_metrics['test_auc_pr']:.4f}")
        print(f"Test AUC-ROC: {test_metrics['test_auc_roc']:.4f}")
        print(f"Top Decile Lift: {test_metrics['top_decile_lift']:.2f}x")
        print(f"  Baseline: {test_metrics['baseline_rate']:.2%}")
        print(f"  Top Decile: {test_metrics['top_decile_rate']:.2%}")
        if comparison:
            print(f"\nImprovement over baseline: {comparison['improvement']:+.2f}x")
        print("="*60 + "\n")
        
        return {
            'test_metrics': test_metrics,
            'comparison': comparison,
            'saved_paths': saved_paths
        }


if __name__ == "__main__":
    trainer = FeatureBoostTrainer()
    results = trainer.run_full_pipeline()
    
    print("[OK] Feature boost training complete!")

