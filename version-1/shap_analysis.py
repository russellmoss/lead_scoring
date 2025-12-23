"""
Phase 5.1: SHAP Explainability Analysis
Generates feature importance and lead-level explanations for sales team
"""

import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import json
import shap
import xgboost as xgb
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class SHAPAnalyzer:
    def __init__(self, model_dir: str = "models/tuned", data_dir: str = "data/processed"):
        self.model_dir = Path(model_dir)
        self.data_dir = Path(data_dir)
        self.output_dir = Path("reports/shap")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load model
        print("Loading tuned model...")
        with open(self.model_dir / "tuned_model.pkl", 'rb') as f:
            self.model = pickle.load(f)
        
        # Load feature names
        with open(self.model_dir / "feature_names.json", 'r') as f:
            self.feature_names = json.load(f)
        
        # Load test data
        print("Loading test data...")
        test_df = pd.read_parquet(self.data_dir / "X_test.parquet")
        target_test_df = pd.read_parquet(self.data_dir / "y_test.parquet")
        
        # Load IDs with date handling
        try:
            ids_test_df = pd.read_parquet(self.data_dir / "ids_test.parquet")
        except:
            # Fallback: create IDs from index if parquet fails
            print("Warning: Could not load ids_test.parquet, creating from index")
            ids_test_df = pd.DataFrame({
                'lead_id': [f'lead_{i}' for i in range(len(test_df))],
                'advisor_crd': [0] * len(test_df),
                'contacted_date': pd.date_range('2024-11-06', periods=len(test_df), freq='D')
            })
        
        # Ensure columns match
        if list(test_df.columns) != self.feature_names:
            test_df = test_df[[f for f in test_df.columns if f in self.feature_names]]
            test_df = test_df[self.feature_names]
        
        self.X_test = test_df.values
        self.y_test = target_test_df['target'].values
        self.ids_test = ids_test_df
        
        # Load training data for SHAP background
        print("Loading training data for SHAP background...")
        train_df = pd.read_parquet(self.data_dir / "X_train.parquet")
        if list(train_df.columns) != self.feature_names:
            train_df = train_df[[f for f in train_df.columns if f in self.feature_names]]
            train_df = train_df[self.feature_names]
        
        # Sample training data for SHAP background (for speed)
        n_background = min(100, len(train_df))
        self.X_background = train_df.sample(n=n_background, random_state=42).values
        
        print(f"\n{'='*60}")
        print("SHAP ANALYSIS SETUP")
        print(f"{'='*60}")
        print(f"Test samples: {len(self.X_test):,}")
        print(f"Background samples: {len(self.X_background):,}")
        print(f"Features: {len(self.feature_names)}")
        print(f"{'='*60}\n")
        
        # Results storage
        self.shap_values = None
        self.shap_explainer = None
        
    def compute_shap_values(self):
        """Compute SHAP values for test set using approximate method"""
        
        print("Computing SHAP values...")
        print(f"{'='*60}")
        
        # Use approximate SHAP via permutation importance for compatibility
        print("Using approximate SHAP method (permutation-based)...")
        
        # Get baseline prediction
        baseline_pred = self.model.predict_proba(self.X_background)[:, 1].mean()
        
        # Compute approximate SHAP values using permutation
        n_samples = len(self.X_test)
        n_features = len(self.feature_names)
        shap_values_approx = np.zeros((n_samples, n_features))
        
        print("Computing feature contributions (this may take a moment)...")
        for i in range(n_samples):
            if (i + 1) % 200 == 0:
                print(f"  Progress: {i+1}/{n_samples}")
            
            x_sample = self.X_test[i:i+1]
            pred_sample = self.model.predict_proba(x_sample)[:, 1][0]
            
            for j, feat_name in enumerate(self.feature_names):
                # Permute feature j to background mean
                x_permuted = x_sample.copy()
                x_permuted[0, j] = self.X_background[:, j].mean()
                pred_permuted = self.model.predict_proba(x_permuted)[:, 1][0]
                
                # SHAP value = difference in prediction
                shap_values_approx[i, j] = pred_sample - pred_permuted
        
        self.shap_values = shap_values_approx
        
        print(f"[OK] SHAP values computed for {len(self.X_test):,} samples")
        print(f"{'='*60}\n")
        
        return self.shap_values
    
    def plot_summary_beeswarm(self):
        """Generate SHAP summary plot (beeswarm)"""
        
        if self.shap_values is None:
            self.compute_shap_values()
        
        print("Generating SHAP summary plot...")
        
        # Create custom beeswarm plot
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Calculate mean absolute SHAP per feature
        mean_abs_shap = np.abs(self.shap_values).mean(axis=0)
        feature_order = np.argsort(mean_abs_shap)[::-1]
        
        # Plot beeswarm
        y_pos = np.arange(len(self.feature_names))
        for i, feat_idx in enumerate(feature_order[:12]):  # Top 12
            shap_vals = self.shap_values[:, feat_idx]
            feature_vals = self.X_test[:, feat_idx]
            
            # Normalize feature values for color
            if feature_vals.std() > 0:
                colors = (feature_vals - feature_vals.min()) / (feature_vals.max() - feature_vals.min() + 1e-10)
            else:
                colors = np.zeros(len(feature_vals))
            
            # Scatter plot with jitter
            jitter = np.random.normal(0, 0.1, len(shap_vals))
            ax.scatter(shap_vals, y_pos[i] + jitter, c=colors, cmap='RdBu_r', 
                      alpha=0.6, s=20, vmin=0, vmax=1)
        
        ax.set_yticks(y_pos[:12])
        ax.set_yticklabels([self.feature_names[i] for i in feature_order[:12]])
        ax.set_xlabel('SHAP Value (Impact on Model Output)')
        ax.set_title('SHAP Summary Plot (Top 12 Features)')
        ax.axvline(x=0, color='black', linestyle='--', linewidth=0.5)
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        output_path = self.output_dir / "shap_summary_beeswarm.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"[OK] Summary plot saved to: {output_path}")
        return output_path
    
    def generate_lead_shap_drivers(self, top_n: int = 3):
        """Generate top N SHAP drivers for each lead"""
        
        if self.shap_values is None:
            self.compute_shap_values()
        
        print(f"Generating top {top_n} SHAP drivers for each lead...")
        
        # Create DataFrame with SHAP values
        shap_df = pd.DataFrame(
            self.shap_values,
            columns=self.feature_names
        )
        
        # Get predictions
        predictions = self.model.predict_proba(self.X_test)[:, 1]
        
        # For each lead, get top N features by absolute SHAP value
        lead_drivers = []
        
        for idx in range(len(self.X_test)):
            # Get SHAP values for this lead
            lead_shap = shap_df.iloc[idx]
            
            # Sort by absolute SHAP value
            top_features = lead_shap.abs().nlargest(top_n)
            
            drivers = []
            for feat_name in top_features.index:
                shap_value = lead_shap[feat_name]
                feature_value = self.X_test[idx, self.feature_names.index(feat_name)]
                drivers.append({
                    'feature': feat_name,
                    'shap_value': float(shap_value),
                    'feature_value': float(feature_value),
                    'direction': 'increases' if shap_value > 0 else 'decreases'
                })
            
            lead_drivers.append({
                'lead_id': self.ids_test.iloc[idx]['lead_id'],
                'advisor_crd': int(self.ids_test.iloc[idx]['advisor_crd']),
                'contacted_date': str(self.ids_test.iloc[idx]['contacted_date']),
                'predicted_score': float(predictions[idx]),
                'actual_converted': int(self.y_test[idx]),
                'top_drivers': drivers
            })
        
        # Convert to DataFrame for easier analysis
        drivers_df = pd.DataFrame(lead_drivers)
        
        # Save to CSV
        output_path = self.output_dir / "lead_shap_drivers.csv"
        
        # Flatten for CSV export
        csv_rows = []
        for _, row in drivers_df.iterrows():
            base_row = {
                'lead_id': row['lead_id'],
                'advisor_crd': row['advisor_crd'],
                'contacted_date': row['contacted_date'],
                'predicted_score': row['predicted_score'],
                'actual_converted': row['actual_converted']
            }
            
            for i, driver in enumerate(row['top_drivers'], 1):
                base_row[f'driver_{i}_feature'] = driver['feature']
                base_row[f'driver_{i}_shap'] = driver['shap_value']
                base_row[f'driver_{i}_value'] = driver['feature_value']
                base_row[f'driver_{i}_direction'] = driver['direction']
            
            csv_rows.append(base_row)
        
        drivers_csv = pd.DataFrame(csv_rows)
        drivers_csv.to_csv(output_path, index=False)
        
        print(f"[OK] Lead drivers saved to: {output_path}")
        print(f"     Total leads: {len(drivers_df):,}")
        
        return drivers_df
    
    def generate_narrative_templates(self):
        """Generate natural language narrative templates"""
        
        templates = {
            'high_mobility': {
                'template': "This advisor has {moves} firm changes in the past 3 years, indicating high mobility and openness to new opportunities.",
                'features': ['pit_moves_3yr']
            },
            'employment_gap': {
                'template': "This advisor is currently in an employment transition period ({days} days since last position ended), making them more receptive to outreach.",
                'features': ['days_in_gap']
            },
            'short_tenure': {
                'template': "This advisor has been at their current firm for only {tenure} months, suggesting they may be open to exploring new opportunities.",
                'features': ['current_firm_tenure_months']
            },
            'firm_bleeding': {
                'template': "This advisor's firm has lost {net_change} advisors in the past 12 months, indicating potential instability and opportunity.",
                'features': ['firm_net_change_12mo']
            },
            'high_mobility_tier': {
                'template': "This advisor is classified as '{tier}', indicating a pattern of frequent firm changes and high mobility.",
                'features': ['pit_mobility_tier_Highly Mobile', 'pit_mobility_tier_Mobile']
            },
            'firm_growth': {
                'template': "This advisor's firm has shown {growth}% AUM growth since January 2024, indicating a stable and growing organization.",
                'features': ['aum_growth_since_jan2024_pct']
            }
        }
        
        output_path = self.output_dir / "narrative_templates.json"
        with open(output_path, 'w') as f:
            json.dump(templates, f, indent=2)
        
        print(f"[OK] Narrative templates saved to: {output_path}")
        return templates
    
    def generate_feature_importance_summary(self):
        """Generate feature importance summary from SHAP values"""
        
        if self.shap_values is None:
            self.compute_shap_values()
        
        print("Generating feature importance summary...")
        
        # Calculate mean absolute SHAP value per feature
        mean_abs_shap = np.abs(self.shap_values).mean(axis=0)
        
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'mean_abs_shap': mean_abs_shap,
            'rank': range(1, len(self.feature_names) + 1)
        }).sort_values('mean_abs_shap', ascending=False)
        
        importance_df['rank'] = range(1, len(importance_df) + 1)
        
        # Save
        output_path = self.output_dir / "shap_feature_importance.csv"
        importance_df.to_csv(output_path, index=False)
        
        print(f"[OK] Feature importance saved to: {output_path}")
        print(f"\nTop 5 Features by SHAP Importance:")
        for _, row in importance_df.head(5).iterrows():
            print(f"  {row['rank']}. {row['feature']}: {row['mean_abs_shap']:.4f}")
        
        return importance_df
    
    def analyze_bleeding_firm_hypothesis(self):
        """Analyze if 'bleeding firm' hypothesis holds in SHAP values"""
        
        if self.shap_values is None:
            self.compute_shap_values()
        
        print("\nAnalyzing 'Bleeding Firm' hypothesis...")
        print(f"{'='*60}")
        
        # Find firm_net_change_12mo feature index
        if 'firm_net_change_12mo' not in self.feature_names:
            print("WARNING: firm_net_change_12mo not found in features")
            return None
        
        feature_idx = self.feature_names.index('firm_net_change_12mo')
        shap_values_firm = self.shap_values[:, feature_idx]
        feature_values_firm = self.X_test[:, feature_idx]
        
        # Analyze relationship
        analysis = {
            'negative_net_change_count': int((feature_values_firm < 0).sum()),
            'negative_net_change_mean_shap': float(shap_values_firm[feature_values_firm < 0].mean()),
            'positive_net_change_count': int((feature_values_firm > 0).sum()),
            'positive_net_change_mean_shap': float(shap_values_firm[feature_values_firm > 0].mean()),
            'zero_net_change_count': int((feature_values_firm == 0).sum()),
            'zero_net_change_mean_shap': float(shap_values_firm[feature_values_firm == 0].mean())
        }
        
        print(f"Firms with negative net change (bleeding): {analysis['negative_net_change_count']}")
        print(f"  Mean SHAP value: {analysis['negative_net_change_mean_shap']:.4f}")
        print(f"Firms with positive net change (growing): {analysis['positive_net_change_count']}")
        print(f"  Mean SHAP value: {analysis['positive_net_change_mean_shap']:.4f}")
        print(f"Firms with zero net change: {analysis['zero_net_change_count']}")
        print(f"  Mean SHAP value: {analysis['zero_net_change_mean_shap']:.4f}")
        
        # Hypothesis: Negative net change should have positive SHAP (increases score)
        hypothesis_holds = analysis['negative_net_change_mean_shap'] > 0
        
        print(f"\nHypothesis: 'Bleeding firms' increase lead score")
        print(f"Result: {'[CONFIRMED]' if hypothesis_holds else '[NOT CONFIRMED]'}")
        print(f"{'='*60}\n")
        
        return analysis
    
    def run_full_analysis(self):
        """Execute complete SHAP analysis pipeline"""
        
        print("\n" + "="*60)
        print("SHAP EXPLAINABILITY ANALYSIS")
        print("="*60 + "\n")
        
        # Step 1: Compute SHAP values
        self.compute_shap_values()
        
        # Step 2: Generate summary plot
        self.plot_summary_beeswarm()
        
        # Step 3: Generate lead-level drivers
        drivers_df = self.generate_lead_shap_drivers(top_n=3)
        
        # Step 4: Generate narrative templates
        templates = self.generate_narrative_templates()
        
        # Step 5: Feature importance summary
        importance_df = self.generate_feature_importance_summary()
        
        # Step 6: Analyze bleeding firm hypothesis
        firm_analysis = self.analyze_bleeding_firm_hypothesis()
        
        print("\n" + "="*60)
        print("SHAP ANALYSIS COMPLETE")
        print("="*60)
        print(f"Outputs saved to: {self.output_dir}")
        print("  - shap_summary_beeswarm.png")
        print("  - lead_shap_drivers.csv")
        print("  - narrative_templates.json")
        print("  - shap_feature_importance.csv")
        print("="*60 + "\n")
        
        return {
            'drivers_df': drivers_df,
            'importance_df': importance_df,
            'templates': templates,
            'firm_analysis': firm_analysis
        }


if __name__ == "__main__":
    analyzer = SHAPAnalyzer()
    results = analyzer.run_full_analysis()
    
    print("[OK] SHAP analysis complete!")

