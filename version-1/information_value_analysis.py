"""
Phase 3.2: Information Value & Feature Importance Pre-Screening
Filters features with no predictive power before model training
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score
import json
import warnings
warnings.filterwarnings('ignore')

class InformationValueAnalyzer:
    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path("reports/feature_selection")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load training data from parquet (more reliable than numpy for mixed types)
        train_df = pd.read_parquet(self.data_dir / "X_train.parquet")
        target_df = pd.read_parquet(self.data_dir / "y_train.parquet")
        with open(self.data_dir / "feature_names.json", 'r') as f:
            feature_data = json.load(f)
            self.feature_names = feature_data['feature_names']
        
        # Ensure columns match
        self.df = train_df.copy()
        if list(self.df.columns) != self.feature_names:
            self.df.columns = self.feature_names
        self.df['target'] = target_df['target'].values
        
        # Results
        self.iv_results = None
        self.auc_results = None
    
    def calculate_iv(self, feature: str, n_bins: int = 10) -> float:
        """
        Calculate Information Value for a single feature
        IV < 0.02: No predictive power (Weak)
        IV 0.02-0.1: Weak
        IV 0.1-0.3: Medium
        IV 0.3-0.5: Strong
        IV > 0.5: Suspicious (possible overfit)
        """
        
        data = self.df[[feature, 'target']].copy()
        data = data.dropna()
        
        if len(data) == 0:
            return 0.0
        
        # For continuous features, bin them
        if data[feature].nunique() > n_bins:
            try:
                data['bin'] = pd.qcut(data[feature], q=n_bins, duplicates='drop')
            except:
                try:
                    data['bin'] = pd.cut(data[feature], bins=n_bins)
                except:
                    # If binning fails, use original values
                    data['bin'] = data[feature]
        else:
            data['bin'] = data[feature]
        
        # Calculate WOE and IV
        grouped = data.groupby('bin')['target'].agg(['count', 'sum'])
        grouped['non_events'] = grouped['count'] - grouped['sum']
        grouped['events'] = grouped['sum']
        
        total_events = grouped['events'].sum()
        total_non_events = grouped['non_events'].sum()
        
        if total_events == 0 or total_non_events == 0:
            return 0.0
        
        grouped['pct_events'] = grouped['events'] / total_events
        grouped['pct_non_events'] = grouped['non_events'] / total_non_events
        
        # Avoid division by zero and log(0)
        grouped['pct_events'] = grouped['pct_events'].clip(lower=0.0001)
        grouped['pct_non_events'] = grouped['pct_non_events'].clip(lower=0.0001)
        
        grouped['woe'] = np.log(grouped['pct_events'] / grouped['pct_non_events'])
        grouped['iv'] = (grouped['pct_events'] - grouped['pct_non_events']) * grouped['woe']
        
        iv_value = grouped['iv'].sum()
        return float(iv_value) if not np.isnan(iv_value) else 0.0
    
    def calculate_univariate_auc(self, feature: str) -> float:
        """Calculate univariate AUC-ROC for a single feature"""
        
        data = self.df[[feature, 'target']].dropna()
        
        if len(data) == 0 or data['target'].nunique() < 2:
            return 0.5
        
        try:
            auc = roc_auc_score(data['target'], data[feature])
            # Handle features where higher = lower probability (inverse relationship)
            if auc < 0.5:
                auc = 1 - auc
            return float(auc)
        except:
            return 0.5
    
    def categorize_iv(self, iv: float) -> str:
        """Categorize IV value"""
        if iv < 0.02:
            return 'Weak'
        elif iv < 0.1:
            return 'Low'
        elif iv < 0.3:
            return 'Medium'
        elif iv < 0.5:
            return 'Strong'
        else:
            return 'Suspicious'
    
    def analyze_all_features(self) -> pd.DataFrame:
        """Calculate IV and AUC for all features"""
        
        results = []
        
        print(f"Analyzing {len(self.feature_names)} features...")
        for i, feature in enumerate(self.feature_names):
            if (i + 1) % 5 == 0:
                print(f"  Progress: {i+1}/{len(self.feature_names)}")
            
            iv = self.calculate_iv(feature)
            auc = self.calculate_univariate_auc(feature)
            
            results.append({
                'feature': feature,
                'iv': iv,
                'iv_category': self.categorize_iv(iv),
                'univariate_auc': auc,
                'predictive_power': 'High' if iv >= 0.1 or auc >= 0.55 else ('Medium' if iv >= 0.02 or auc >= 0.52 else 'Weak')
            })
        
        self.iv_results = pd.DataFrame(results).sort_values('iv', ascending=False)
        return self.iv_results
    
    def identify_weak_features(self, iv_threshold: float = 0.02) -> list:
        """Identify features with IV below threshold"""
        
        if self.iv_results is None:
            self.analyze_all_features()
        
        weak_features = self.iv_results[
            (self.iv_results['iv'] < iv_threshold) & 
            (self.iv_results['univariate_auc'] < 0.52)
        ].copy()
        
        # PROTECTED FEATURES: Never remove even if weak
        protected_features = {'pit_moves_3yr', 'firm_net_change_12mo'}
        weak_features = weak_features[~weak_features['feature'].isin(protected_features)]
        
        return weak_features.to_dict('records')
    
    def generate_report(self) -> dict:
        """Generate comprehensive IV analysis report"""
        
        # Run analysis
        print("Calculating Information Value for all features...")
        self.analyze_all_features()
        
        print("Identifying weak features...")
        weak_features = self.identify_weak_features()
        
        # Calculate summary statistics
        summary = {
            'total_features': len(self.feature_names),
            'high_iv_count': len(self.iv_results[self.iv_results['iv'] >= 0.3]),
            'medium_iv_count': len(self.iv_results[(self.iv_results['iv'] >= 0.1) & (self.iv_results['iv'] < 0.3)]),
            'low_iv_count': len(self.iv_results[(self.iv_results['iv'] >= 0.02) & (self.iv_results['iv'] < 0.1)]),
            'weak_iv_count': len(self.iv_results[self.iv_results['iv'] < 0.02]),
            'weak_features_recommended_removal': len(weak_features),
            'top_5_features_by_iv': self.iv_results.head(5)[['feature', 'iv', 'univariate_auc']].to_dict('records'),
            'top_5_features_by_auc': self.iv_results.nlargest(5, 'univariate_auc')[['feature', 'iv', 'univariate_auc']].to_dict('records')
        }
        
        report = {
            'summary': summary,
            'iv_results': self.iv_results.to_dict('records'),
            'weak_features': weak_features,
            'protected_features': ['pit_moves_3yr', 'firm_net_change_12mo']
        }
        
        # Save report
        with open(self.output_dir / "iv_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save IV table
        self.iv_results.to_csv(self.output_dir / "iv_analysis.csv", index=False)
        
        return report


if __name__ == "__main__":
    analyzer = InformationValueAnalyzer()
    report = analyzer.generate_report()
    
    print("\n" + "="*60)
    print("INFORMATION VALUE ANALYSIS RESULTS")
    print("="*60)
    print(f"Total features: {report['summary']['total_features']}")
    print(f"Strong IV (>=0.3): {report['summary']['high_iv_count']}")
    print(f"Medium IV (0.1-0.3): {report['summary']['medium_iv_count']}")
    print(f"Low IV (0.02-0.1): {report['summary']['low_iv_count']}")
    print(f"Weak IV (<0.02): {report['summary']['weak_iv_count']}")
    print(f"\nWeak features recommended for removal: {report['summary']['weak_iv_count']}")
    
    print("\nTop 5 Features by IV:")
    for feat in report['summary']['top_5_features_by_iv']:
        print(f"  - {feat['feature']}: IV={feat['iv']:.4f}, AUC={feat['univariate_auc']:.4f}")
    
    print("\nTop 5 Features by Univariate AUC:")
    for feat in report['summary']['top_5_features_by_auc']:
        print(f"  - {feat['feature']}: IV={feat['iv']:.4f}, AUC={feat['univariate_auc']:.4f}")
    
    if report['weak_features']:
        print("\nWeak features (IV < 0.02) recommended for removal:")
        for feat in report['weak_features']:
            print(f"  - {feat['feature']}: IV={feat['iv']:.4f}, AUC={feat['univariate_auc']:.4f}")
    else:
        print("\nNo weak features recommended for removal.")
    
    print(f"\nProtected features (never removed):")
    for feat in report['protected_features']:
        print(f"  - {feat}")
    
    print(f"\n[OK] Report saved to: {analyzer.output_dir / 'iv_report.json'}")

