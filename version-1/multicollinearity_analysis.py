"""
Phase 3.1: Multicollinearity Analysis
Identifies and removes highly correlated features to improve model stability
"""

import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.stats.outliers_influence import variance_inflation_factor
import json
import warnings
warnings.filterwarnings('ignore')

class MulticollinearityAnalyzer:
    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path("reports/feature_selection")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load training data from parquet (more reliable than numpy for mixed types)
        train_df = pd.read_parquet(self.data_dir / "X_train.parquet")
        with open(self.data_dir / "feature_names.json", 'r') as f:
            feature_data = json.load(f)
            self.feature_names = feature_data['feature_names']
        
        # Ensure columns match
        self.df = train_df.copy()
        if list(self.df.columns) != self.feature_names:
            self.df.columns = self.feature_names
        
        # Results storage
        self.vif_results = None
        self.correlation_matrix = None
        self.high_correlation_pairs = []
        self.features_to_remove = []
        
    def calculate_vif(self) -> pd.DataFrame:
        """Calculate VIF for all numeric features"""
        
        # Get numeric columns only (exclude one-hot encoded categoricals if needed)
        # For our case, all features are numeric (mobility tier is already one-hot encoded)
        numeric_cols = [c for c in self.df.columns 
                       if self.df[c].dtype in ['float64', 'int64', 'float32', 'int32']]
        
        # Filter to columns with variance > 0
        valid_cols = [c for c in numeric_cols if self.df[c].var() > 1e-10]
        
        if len(valid_cols) == 0:
            print("WARNING: No valid numeric columns found for VIF calculation")
            return pd.DataFrame()
        
        # Add constant for VIF calculation
        X_numeric = self.df[valid_cols].copy()
        X_numeric = X_numeric.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # Calculate VIF
        vif_data = []
        for i, col in enumerate(valid_cols):
            try:
                vif = variance_inflation_factor(X_numeric.values, i)
                if np.isinf(vif) or np.isnan(vif):
                    vif = np.nan
                vif_data.append({
                    'feature': col,
                    'vif': float(vif) if not np.isnan(vif) else np.nan,
                    'vif_category': self._categorize_vif(vif)
                })
            except Exception as e:
                vif_data.append({
                    'feature': col,
                    'vif': np.nan,
                    'vif_category': 'ERROR'
                })
        
        self.vif_results = pd.DataFrame(vif_data).sort_values('vif', ascending=False, na_position='last')
        return self.vif_results
    
    def _categorize_vif(self, vif: float) -> str:
        """Categorize VIF value"""
        if np.isnan(vif) or np.isinf(vif):
            return 'ERROR'
        elif vif > 10:
            return 'HIGH'
        elif vif > 5:
            return 'MODERATE'
        else:
            return 'LOW'
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calculate pairwise correlation matrix"""
        
        # Get numeric columns
        numeric_cols = [c for c in self.df.columns 
                       if self.df[c].dtype in ['float64', 'int64', 'float32', 'int32']]
        
        self.correlation_matrix = self.df[numeric_cols].corr()
        return self.correlation_matrix
    
    def identify_high_correlations(self, threshold: float = 0.90) -> list:
        """Identify feature pairs with correlation above threshold"""
        
        if self.correlation_matrix is None:
            self.calculate_correlation_matrix()
        
        self.high_correlation_pairs = []
        
        for i in range(len(self.correlation_matrix.columns)):
            for j in range(i + 1, len(self.correlation_matrix.columns)):
                corr = self.correlation_matrix.iloc[i, j]
                if abs(corr) > threshold:
                    self.high_correlation_pairs.append({
                        'feature_1': self.correlation_matrix.columns[i],
                        'feature_2': self.correlation_matrix.columns[j],
                        'correlation': float(corr)
                    })
        
        return self.high_correlation_pairs
    
    def recommend_removals(self) -> list:
        """
        Recommend features to remove based on VIF and business importance.
        
        CRITICAL: Protected features (primary business hypotheses) are NEVER removed,
        even if they have high VIF or correlation. If they correlate with other features,
        the other features are removed instead.
        """
        
        # PROTECTED FEATURES: Primary business hypotheses - MUST NOT be removed
        protected_features = {
            'pit_moves_3yr',  # Validated 3.8x lift - primary mobility hypothesis
            'firm_net_change_12mo'  # Primary firm stability hypothesis
        }
        
        # Business importance ranking (lower = more important)
        importance_ranking = {
            'firm_net_change_12mo': 1,  # Most important stability metric
            'pit_moves_3yr': 2,  # HIGH PRIORITY: Validated 3.8x lift
            'firm_stability_score': 3,  # Derived from net_change
            'pit_mobility_tier_Highly Mobile': 4,  # Categorical version of moves_3yr
            'pit_mobility_tier_Mobile': 5,
            'pit_mobility_tier_Average': 6,
            'pit_mobility_tier_Stable': 7,
            'industry_tenure_months': 8,
            'current_firm_tenure_months': 9,
            'firm_aum_pit': 10,
            'firm_rep_count_at_contact': 11,
            'aum_growth_since_jan2024_pct': 12,
            'num_prior_firms': 13,
            'days_in_gap': 14,
        }
        
        removals = []
        
        # Remove high VIF features (keep more important ones)
        # CRITICAL: Never remove protected features
        if self.vif_results is not None:
            high_vif = self.vif_results[self.vif_results['vif'] > 10].copy()
            for _, row in high_vif.iterrows():
                feature = row['feature']
                
                # NEVER remove protected features
                if feature in protected_features:
                    continue
                
                # Don't remove if it's highly important (rank <= 5)
                if importance_ranking.get(feature, 100) <= 5:
                    continue
                
                removals.append({
                    'feature': feature,
                    'reason': f"VIF = {row['vif']:.2f} > 10",
                    'type': 'multicollinearity'
                })
        
        # Handle high correlation pairs (remove less important one)
        # CRITICAL: If a protected feature correlates with another, always remove the other
        for pair in self.high_correlation_pairs:
            f1, f2 = pair['feature_1'], pair['feature_2']
            
            # If one feature is protected, always remove the other
            if f1 in protected_features:
                to_remove = f2
                reason = f"High correlation ({pair['correlation']:.3f}) with protected feature {f1}"
            elif f2 in protected_features:
                to_remove = f1
                reason = f"High correlation ({pair['correlation']:.3f}) with protected feature {f2}"
            else:
                # Neither is protected - use importance ranking
                imp1 = importance_ranking.get(f1, 100)
                imp2 = importance_ranking.get(f2, 100)
                to_remove = f1 if imp1 > imp2 else f2
                reason = f"High correlation ({pair['correlation']:.3f}) with {f1 if to_remove == f2 else f2}"
            
            # Only add to removals if not already there and not protected
            if to_remove not in protected_features and to_remove not in [r['feature'] for r in removals]:
                removals.append({
                    'feature': to_remove,
                    'reason': reason,
                    'type': 'high_correlation'
                })
        
        self.features_to_remove = removals
        return removals
    
    def generate_report(self) -> dict:
        """Generate comprehensive multicollinearity report"""
        
        # Run all analyses
        print("Calculating VIF...")
        self.calculate_vif()
        
        print("Calculating correlation matrix...")
        self.calculate_correlation_matrix()
        
        print("Identifying high correlations...")
        self.identify_high_correlations()
        
        print("Generating removal recommendations...")
        recommendations = self.recommend_removals()
        
        report = {
            'summary': {
                'total_features': len(self.feature_names),
                'high_vif_count': len(self.vif_results[self.vif_results['vif'] > 10]) if self.vif_results is not None else 0,
                'moderate_vif_count': len(self.vif_results[(self.vif_results['vif'] > 5) & (self.vif_results['vif'] <= 10)]) if self.vif_results is not None else 0,
                'high_correlation_pairs': len(self.high_correlation_pairs),
                'recommended_removals': len(recommendations)
            },
            'vif_results': self.vif_results.to_dict('records') if self.vif_results is not None else [],
            'high_correlations': self.high_correlation_pairs,
            'recommendations': recommendations,
            'protected_features': ['pit_moves_3yr', 'firm_net_change_12mo']
        }
        
        # Save report
        with open(self.output_dir / "multicollinearity_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save VIF table
        if self.vif_results is not None:
            self.vif_results.to_csv(self.output_dir / "vif_analysis.csv", index=False)
        
        # Save correlation matrix
        if self.correlation_matrix is not None:
            self.correlation_matrix.to_csv(self.output_dir / "correlation_matrix.csv")
        
        return report


if __name__ == "__main__":
    analyzer = MulticollinearityAnalyzer()
    report = analyzer.generate_report()
    
    print("\n" + "="*60)
    print("MULTICOLLINEARITY ANALYSIS RESULTS")
    print("="*60)
    print(f"Total features: {report['summary']['total_features']}")
    print(f"High VIF (>10): {report['summary']['high_vif_count']}")
    print(f"Moderate VIF (5-10): {report['summary']['moderate_vif_count']}")
    print(f"High correlation pairs (>0.90): {report['summary']['high_correlation_pairs']}")
    print(f"\nRecommended removals: {report['summary']['recommended_removals']}")
    
    if report['recommendations']:
        print("\nFeatures recommended for removal:")
        for rec in report['recommendations']:
            print(f"  - {rec['feature']}: {rec['reason']}")
    else:
        print("\nNo features recommended for removal.")
    
    print(f"\nProtected features (never removed):")
    for feat in report['protected_features']:
        print(f"  - {feat}")
    
    print(f"\n[OK] Report saved to: {analyzer.output_dir / 'multicollinearity_report.json'}")

