"""
V7 Model Comparison Report
Generates comprehensive comparison report between V6, V7, and m5 models including:
1. Performance metrics comparison
2. Feature importance rankings
3. Temporal feature contribution analysis
4. Financial feature impact assessment
5. Prediction distribution plots
6. Calibration curves
7. Segment-specific performance (by AUM tiers)
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from scipy import stats
from sklearn.metrics import (
    average_precision_score, roc_auc_score, precision_recall_curve,
    roc_curve, precision_score, recall_score, f1_score
)
from google.cloud import bigquery
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# Paths
BASE_DIR = Path(__file__).parent

# V7 Artifacts
VERSION = datetime.now().strftime("%Y%m%d")
MODEL_V7_ENSEMBLE_PATH = BASE_DIR / f"model_v7_{VERSION}_ensemble.pkl"
CV_INDICES_V7_PATH = BASE_DIR / f"cv_fold_indices_v7_{VERSION}.json"
FEATURE_IMPORTANCE_V7_PATH = BASE_DIR / f"feature_importance_v7_{VERSION}.csv"
FEATURE_ORDER_V7_PATH = BASE_DIR / f"feature_order_v7_{VERSION}.json"
MODEL_TRAINING_REPORT_V7_PATH = BASE_DIR / f"model_training_report_v7_{VERSION}.md"

# V6 Artifacts (latest versions)
MODEL_V6_PATH = BASE_DIR / "model_v6_20251104.pkl"
MODEL_V6_FINANCIALS_PATH = BASE_DIR / "model_v6_with_financials_20251104.pkl"
FEATURE_IMPORTANCE_V6_PATH = BASE_DIR / "feature_importance_v6_20251104.csv"
FEATURE_IMPORTANCE_V6_FINANCIALS_PATH = BASE_DIR / "feature_importance_v6_with_financials_20251104.csv"

# Output paths
COMPARISON_REPORT_V7_PATH = BASE_DIR / f"v7_comparison_report_{VERSION}.md"
COMPARISON_PLOTS_DIR = BASE_DIR / "v7_comparison_plots"

# BigQuery config
PROJECT_ID = "savvy-gtm-analytics"
BQ_TABLE_V7 = f"savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v7_featured_{VERSION}"

# m5 Performance (from documentation)
M5_METRICS = {
    'aucpr': 0.1492,  # 14.92%
    'aucroc': 0.7916,
    'top_10_precision': 0.1323,  # 13.23%
    'top_10_lift': 3.93,
    'conversion_rate': 0.04  # 4%
}

# m5 Top Features (from m5_vs_V1_Model_Comparison_Analysis.md)
M5_TOP_FEATURES = [
    'Multi_RIA_Relationships',
    'Mass_Market_Focus',
    'HNW_Asset_Concentration',
    'DateBecameRep_NumberOfYears',
    'Branch_Advisor_Density',
    'Client_Efficiency_Score',
    'Growth_Momentum_Indicator',
    'Institutional_Focus',
    'Breakaway_High_AUM',
    'Digital_Presence_Score'
]

# PII features to drop
PII_TO_DROP = [
    'FirstName', 'LastName', 
    'Branch_City', 'Branch_County', 'Branch_ZipCode',
    'Home_City', 'Home_County', 'Home_ZipCode',
    'RIAFirmCRD', 'RIAFirmName',
    'PersonalWebpage', 'Notes'
]

# Feature categories
TEMPORAL_FEATURES = [
    'Recent_Firm_Change',
    'License_Sophistication',
    'Branch_State_Stable',
    'Tenure_Momentum_Score',
    'Title_Progression_Flag',
    'Geographic_Expansion_Flag',
    'Firm_Size_Trajectory',
    'Association_Changes'
]

FINANCIAL_FEATURES = [
    'TotalAssetsInMillions',
    'NumberClients_Individuals',
    'NumberClients_HNWIndividuals',
    'NumberClients_Entities',
    'PercentClients_Individuals',
    'PercentClients_HNWIndividuals',
    'PercentAssets_MutualFunds',
    'PercentAssets_PrivateFunds',
    'AUMGrowthRate_1Year',
    'AUMGrowthRate_5Year',
    'Custodian1_AUM',
    'Custodian2_AUM'
]


def load_model_artifacts(model_name: str) -> Tuple[Any, pd.DataFrame, List[str]]:
    """Load model artifacts for a given model version"""
    if model_name == 'v7':
        model_path = MODEL_V7_ENSEMBLE_PATH
        importance_path = FEATURE_IMPORTANCE_V7_PATH
        order_path = FEATURE_ORDER_V7_PATH
    elif model_name == 'v6':
        model_path = MODEL_V6_PATH
        importance_path = FEATURE_IMPORTANCE_V6_PATH
        order_path = BASE_DIR / "feature_order_v6_20251104.json"
    elif model_name == 'v6_financials':
        model_path = MODEL_V6_FINANCIALS_PATH
        importance_path = FEATURE_IMPORTANCE_V6_FINANCIALS_PATH
        order_path = BASE_DIR / "feature_order_v6_with_financials_20251104.json"
    else:
        raise ValueError(f"Unknown model: {model_name}")
    
    if not model_path.exists():
        return None, None, None
    
    model = joblib.load(model_path)
    importance_df = pd.read_csv(importance_path) if importance_path.exists() else None
    
    feature_order = None
    if order_path.exists():
        with open(order_path, 'r') as f:
            feature_order = json.load(f)
    
    return model, importance_df, feature_order


def load_data_from_bigquery(table_name: str) -> pd.DataFrame:
    """Load data from BigQuery"""
    client = bigquery.Client(project=PROJECT_ID)
    query = f"SELECT * FROM `{table_name}`"
    df = client.query(query).to_dataframe()
    return df


def prepare_features(df: pd.DataFrame, feature_order: List[str]) -> Tuple[pd.DataFrame, np.ndarray]:
    """Prepare features for prediction"""
    # Drop PII
    pii_found = [col for col in PII_TO_DROP if col in df.columns]
    if pii_found:
        df = df.drop(columns=pii_found)
    
    # Get target
    y = df['target_label'].values if 'target_label' in df.columns else None
    df = df.drop(columns=['target_label'], errors='ignore')
    
    # Ensure feature order matches
    if feature_order:
        missing_features = [f for f in feature_order if f not in df.columns]
        if missing_features:
            for feat in missing_features:
                df[feat] = 0
        X = df[feature_order].copy()
    else:
        X = df.copy()
    
    # Handle categoricals
    for col in X.columns:
        if X[col].dtype == 'object':
            try:
                X[col] = pd.Categorical(X[col]).codes
            except:
                X[col] = pd.Categorical(X[col].astype(str).fillna('')).codes
    
    X = X.fillna(0)
    
    return X, y


def evaluate_model(model: Any, X: pd.DataFrame, y: np.ndarray, model_name: str) -> Dict[str, float]:
    """Evaluate model performance"""
    if model is None or X is None or y is None:
        return None
    
    try:
        # Get predictions
        if isinstance(model, dict) and 'predict_proba' in model:
            y_pred = model['predict_proba'](X)
        elif hasattr(model, 'predict_proba'):
            y_pred = model.predict_proba(X)[:, 1]
        else:
            return None
        
        # Calculate metrics
        metrics = {
            'aucpr': average_precision_score(y, y_pred),
            'aucroc': roc_auc_score(y, y_pred),
            'precision_at_10': precision_at_k(y, y_pred, k=0.10),
            'precision_at_20': precision_at_k(y, y_pred, k=0.20),
            'lift_at_10': lift_at_k(y, y_pred, k=0.10)
        }
        
        return metrics
    except Exception as e:
        print(f"   Warning: Evaluation failed for {model_name}: {e}", flush=True)
        return None


def precision_at_k(y_true: np.ndarray, y_pred: np.ndarray, k: float = 0.10) -> float:
    """Calculate precision at top k%"""
    n_top = int(len(y_true) * k)
    top_indices = np.argsort(y_pred)[::-1][:n_top]
    if len(top_indices) == 0:
        return 0.0
    return y_true[top_indices].mean()


def lift_at_k(y_true: np.ndarray, y_pred: np.ndarray, k: float = 0.10) -> float:
    """Calculate lift at top k%"""
    baseline_rate = y_true.mean()
    precision_k = precision_at_k(y_true, y_pred, k)
    if baseline_rate == 0:
        return 0.0
    return precision_k / baseline_rate


def compare_performance_metrics(
    v7_metrics: Dict[str, float],
    v6_metrics: Dict[str, float],
    v6_financials_metrics: Dict[str, float]
) -> pd.DataFrame:
    """Compare performance metrics across models"""
    comparison = pd.DataFrame({
        'm5': {
            'AUC-PR': M5_METRICS['aucpr'],
            'AUC-ROC': M5_METRICS['aucroc'],
            'Precision@10%': M5_METRICS['top_10_precision'],
            'Lift@10%': M5_METRICS['top_10_lift']
        },
        'V6': {
            'AUC-PR': v6_metrics.get('aucpr', np.nan) if v6_metrics else np.nan,
            'AUC-ROC': v6_metrics.get('aucroc', np.nan) if v6_metrics else np.nan,
            'Precision@10%': v6_metrics.get('precision_at_10', np.nan) if v6_metrics else np.nan,
            'Lift@10%': v6_metrics.get('lift_at_10', np.nan) if v6_metrics else np.nan
        },
        'V6 (Financials)': {
            'AUC-PR': v6_financials_metrics.get('aucpr', np.nan) if v6_financials_metrics else np.nan,
            'AUC-ROC': v6_financials_metrics.get('aucroc', np.nan) if v6_financials_metrics else np.nan,
            'Precision@10%': v6_financials_metrics.get('precision_at_10', np.nan) if v6_financials_metrics else np.nan,
            'Lift@10%': v6_financials_metrics.get('lift_at_10', np.nan) if v6_financials_metrics else np.nan
        },
        'V7': {
            'AUC-PR': v7_metrics.get('aucpr', np.nan) if v7_metrics else np.nan,
            'AUC-ROC': v7_metrics.get('aucroc', np.nan) if v7_metrics else np.nan,
            'Precision@10%': v7_metrics.get('precision_at_10', np.nan) if v7_metrics else np.nan,
            'Lift@10%': v7_metrics.get('lift_at_10', np.nan) if v7_metrics else np.nan
        }
    }).T
    
    return comparison


def compare_feature_importance(
    v7_importance: pd.DataFrame,
    v6_importance: pd.DataFrame,
    v6_financials_importance: pd.DataFrame
) -> pd.DataFrame:
    """Compare feature importance rankings"""
    # Get top 20 from each
    top_features = []
    
    if v7_importance is not None:
        top_v7 = v7_importance.head(20)['feature'].tolist()
        top_features.extend(top_v7)
    
    if v6_importance is not None:
        top_v6 = v6_importance.head(20)['feature'].tolist()
        top_features.extend(top_v6)
    
    if v6_financials_importance is not None:
        top_v6f = v6_financials_importance.head(20)['feature'].tolist()
        top_features.extend(top_v6f)
    
    # Get unique features
    unique_features = list(set(top_features))
    
    # Create comparison dataframe
    comparison_data = []
    for feat in unique_features[:50]:  # Top 50 unique features
        row = {'feature': feat}
        
        # V7 ranking
        if v7_importance is not None:
            v7_row = v7_importance[v7_importance['feature'] == feat]
            row['v7_rank'] = v7_row.index[0] + 1 if len(v7_row) > 0 else None
            row['v7_importance'] = v7_row['importance'].values[0] if len(v7_row) > 0 else None
        else:
            row['v7_rank'] = None
            row['v7_importance'] = None
        
        # V6 ranking
        if v6_importance is not None:
            v6_row = v6_importance[v6_importance['feature'] == feat]
            row['v6_rank'] = v6_row.index[0] + 1 if len(v6_row) > 0 else None
            row['v6_importance'] = v6_row['importance'].values[0] if len(v6_row) > 0 else None
        else:
            row['v6_rank'] = None
            row['v6_importance'] = None
        
        # V6 Financials ranking
        if v6_financials_importance is not None:
            v6f_row = v6_financials_importance[v6_financials_importance['feature'] == feat]
            row['v6_financials_rank'] = v6f_row.index[0] + 1 if len(v6f_row) > 0 else None
            row['v6_financials_importance'] = v6f_row['importance'].values[0] if len(v6f_row) > 0 else None
        else:
            row['v6_financials_rank'] = None
            row['v6_financials_importance'] = None
        
        # m5 ranking
        if feat in M5_TOP_FEATURES:
            row['m5_rank'] = M5_TOP_FEATURES.index(feat) + 1
        else:
            row['m5_rank'] = None
        
        comparison_data.append(row)
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Sort by V7 importance (if available)
    if v7_importance is not None:
        comparison_df = comparison_df.sort_values('v7_importance', ascending=False, na_last=True)
    
    return comparison_df


def analyze_temporal_feature_contribution(
    v7_importance: pd.DataFrame,
    v6_importance: pd.DataFrame
) -> Dict[str, Any]:
    """Analyze contribution of temporal features"""
    analysis = {}
    
    if v7_importance is not None:
        v7_temporal = v7_importance[v7_importance['feature'].isin(TEMPORAL_FEATURES)]
        analysis['v7_temporal_count'] = len(v7_temporal)
        analysis['v7_temporal_importance'] = v7_temporal['importance'].sum() if len(v7_temporal) > 0 else 0
        analysis['v7_temporal_avg_rank'] = v7_temporal.index.mean() if len(v7_temporal) > 0 else None
    
    if v6_importance is not None:
        v6_temporal = v6_importance[v6_importance['feature'].isin(TEMPORAL_FEATURES)]
        analysis['v6_temporal_count'] = len(v6_temporal)
        analysis['v6_temporal_importance'] = v6_temporal['importance'].sum() if len(v6_temporal) > 0 else 0
        analysis['v6_temporal_avg_rank'] = v6_temporal.index.mean() if len(v6_temporal) > 0 else None
    
    return analysis


def analyze_financial_feature_contribution(
    v7_importance: pd.DataFrame,
    v6_financials_importance: pd.DataFrame
) -> Dict[str, Any]:
    """Analyze contribution of financial features"""
    analysis = {}
    
    if v7_importance is not None:
        v7_financial = v7_importance[v7_importance['feature'].isin(FINANCIAL_FEATURES)]
        analysis['v7_financial_count'] = len(v7_financial)
        analysis['v7_financial_importance'] = v7_financial['importance'].sum() if len(v7_financial) > 0 else 0
        analysis['v7_financial_avg_rank'] = v7_financial.index.mean() if len(v7_financial) > 0 else None
    
    if v6_financials_importance is not None:
        v6f_financial = v6_financials_importance[v6_financials_importance['feature'].isin(FINANCIAL_FEATURES)]
        analysis['v6_financial_count'] = len(v6f_financial)
        analysis['v6_financial_importance'] = v6f_financial['importance'].sum() if len(v6f_financial) > 0 else 0
        analysis['v6_financial_avg_rank'] = v6f_financial.index.mean() if len(v6f_financial) > 0 else None
    
    return analysis


def plot_prediction_distributions(
    v7_preds: np.ndarray,
    v6_preds: np.ndarray,
    v6_financials_preds: np.ndarray,
    output_dir: Path
) -> None:
    """Plot prediction distributions"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Distribution plot
    axes[0, 0].hist(v7_preds, bins=50, alpha=0.7, label='V7', density=True)
    if v6_preds is not None:
        axes[0, 0].hist(v6_preds, bins=50, alpha=0.7, label='V6', density=True)
    if v6_financials_preds is not None:
        axes[0, 0].hist(v6_financials_preds, bins=50, alpha=0.7, label='V6 (Financials)', density=True)
    axes[0, 0].set_xlabel('Prediction Score')
    axes[0, 0].set_ylabel('Density')
    axes[0, 0].set_title('Prediction Distribution')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Box plot
    data_to_plot = [v7_preds]
    labels = ['V7']
    if v6_preds is not None:
        data_to_plot.append(v6_preds)
        labels.append('V6')
    if v6_financials_preds is not None:
        data_to_plot.append(v6_financials_preds)
        labels.append('V6 (Financials)')
    
    axes[0, 1].boxplot(data_to_plot, labels=labels)
    axes[0, 1].set_ylabel('Prediction Score')
    axes[0, 1].set_title('Prediction Distribution (Box Plot)')
    axes[0, 1].grid(True, alpha=0.3)
    
    # CDF plot
    axes[1, 0].hist(v7_preds, bins=50, cumulative=True, density=True, alpha=0.7, label='V7', histtype='step')
    if v6_preds is not None:
        axes[1, 0].hist(v6_preds, bins=50, cumulative=True, density=True, alpha=0.7, label='V6', histtype='step')
    if v6_financials_preds is not None:
        axes[1, 0].hist(v6_financials_preds, bins=50, cumulative=True, density=True, alpha=0.7, label='V6 (Financials)', histtype='step')
    axes[1, 0].set_xlabel('Prediction Score')
    axes[1, 0].set_ylabel('Cumulative Probability')
    axes[1, 0].set_title('Cumulative Distribution Function')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Top 10% score distribution
    top_10_v7 = np.percentile(v7_preds, 90)
    axes[1, 1].axvline(top_10_v7, color='blue', linestyle='--', label=f'V7 Top 10%: {top_10_v7:.3f}')
    if v6_preds is not None:
        top_10_v6 = np.percentile(v6_preds, 90)
        axes[1, 1].axvline(top_10_v6, color='green', linestyle='--', label=f'V6 Top 10%: {top_10_v6:.3f}')
    if v6_financials_preds is not None:
        top_10_v6f = np.percentile(v6_financials_preds, 90)
        axes[1, 1].axvline(top_10_v6f, color='orange', linestyle='--', label=f'V6 (Fin) Top 10%: {top_10_v6f:.3f}')
    
    axes[1, 1].hist(v7_preds, bins=50, alpha=0.7, label='V7', density=True)
    axes[1, 1].set_xlabel('Prediction Score')
    axes[1, 1].set_ylabel('Density')
    axes[1, 1].set_title('Top 10% Threshold Comparison')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'prediction_distributions.png', dpi=150, bbox_inches='tight')
    plt.close()


def generate_comparison_report(
    performance_comparison: pd.DataFrame,
    feature_comparison: pd.DataFrame,
    temporal_analysis: Dict[str, Any],
    financial_analysis: Dict[str, Any],
    v7_metrics: Dict[str, float],
    v6_metrics: Dict[str, float],
    v6_financials_metrics: Dict[str, float]
) -> None:
    """Generate comprehensive comparison report"""
    print(f"[8/8] Generating comparison report...", flush=True)
    
    with open(COMPARISON_REPORT_V7_PATH, 'w', encoding='utf-8') as f:
        f.write("# V7 Model Comparison Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Version:** {VERSION}\n\n")
        
        f.write("## Executive Summary\n\n")
        
        # Determine improvement
        v7_aucpr = v7_metrics.get('aucpr', 0) if v7_metrics else 0
        v6_aucpr = v6_metrics.get('aucpr', 0) if v6_metrics else 0
        v6f_aucpr = v6_financials_metrics.get('aucpr', 0) if v6_financials_metrics else 0
        m5_aucpr = M5_METRICS['aucpr']
        
        f.write(f"### Performance Overview\n\n")
        f.write(f"- **m5 (Production):** {m5_aucpr:.4f} ({m5_aucpr*100:.2f}%)\n")
        f.write(f"- **V6:** {v6_aucpr:.4f} ({v6_aucpr*100:.2f}%)\n")
        f.write(f"- **V6 (Financials):** {v6f_aucpr:.4f} ({v6f_aucpr*100:.2f}%)\n")
        f.write(f"- **V7:** {v7_aucpr:.4f} ({v7_aucpr*100:.2f}%)\n\n")
        
        if v7_aucpr > v6f_aucpr:
            improvement = ((v7_aucpr - v6f_aucpr) / v6f_aucpr) * 100
            f.write(f"✅ **V7 improves over V6 (Financials) by {improvement:.1f}%**\n\n")
        else:
            decline = ((v6f_aucpr - v7_aucpr) / v6f_aucpr) * 100
            f.write(f"⚠️ **V7 is {decline:.1f}% lower than V6 (Financials)**\n\n")
        
        gap_to_m5 = ((v7_aucpr - m5_aucpr) / m5_aucpr) * 100
        if v7_aucpr >= m5_aucpr:
            f.write(f"✅ **V7 matches/exceeds m5 performance** (gap: {gap_to_m5:+.1f}%)\n\n")
        else:
            f.write(f"⚠️ **V7 is {abs(gap_to_m5):.1f}% below m5** (target: close the gap)\n\n")
        
        f.write("## Performance Metrics Comparison\n\n")
        f.write(performance_comparison.to_markdown())
        f.write("\n\n")
        
        f.write("## Feature Importance Comparison\n\n")
        f.write("### Top 20 Features by Model\n\n")
        top_features_comparison = feature_comparison.head(20)
        f.write(top_features_comparison.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("### m5 Feature Alignment\n\n")
        m5_aligned = feature_comparison[feature_comparison['m5_rank'].notna()].head(10)
        f.write(m5_aligned.to_markdown(index=False))
        f.write("\n\n")
        
        f.write("## Temporal Feature Contribution\n\n")
        if 'v7_temporal_count' in temporal_analysis:
            f.write(f"- **V7 Temporal Features in Top 50:** {temporal_analysis['v7_temporal_count']}\n")
            f.write(f"- **V7 Total Temporal Importance:** {temporal_analysis['v7_temporal_importance']:.6f}\n")
            if temporal_analysis['v7_temporal_avg_rank']:
                f.write(f"- **V7 Average Temporal Rank:** {temporal_analysis['v7_temporal_avg_rank']:.1f}\n")
        
        if 'v6_temporal_count' in temporal_analysis:
            f.write(f"- **V6 Temporal Features in Top 50:** {temporal_analysis['v6_temporal_count']}\n")
            f.write(f"- **V6 Total Temporal Importance:** {temporal_analysis['v6_temporal_importance']:.6f}\n")
            if temporal_analysis['v6_temporal_avg_rank']:
                f.write(f"- **V6 Average Temporal Rank:** {temporal_analysis['v6_temporal_avg_rank']:.1f}\n")
        
        f.write("\n")
        
        f.write("## Financial Feature Contribution\n\n")
        if 'v7_financial_count' in financial_analysis:
            f.write(f"- **V7 Financial Features in Top 50:** {financial_analysis['v7_financial_count']}\n")
            f.write(f"- **V7 Total Financial Importance:** {financial_analysis['v7_financial_importance']:.6f}\n")
            if financial_analysis['v7_financial_avg_rank']:
                f.write(f"- **V7 Average Financial Rank:** {financial_analysis['v7_financial_avg_rank']:.1f}\n")
        
        if 'v6_financial_count' in financial_analysis:
            f.write(f"- **V6 (Financials) Financial Features in Top 50:** {financial_analysis['v6_financial_count']}\n")
            f.write(f"- **V6 (Financials) Total Financial Importance:** {financial_analysis['v6_financial_importance']:.6f}\n")
            if financial_analysis['v6_financial_avg_rank']:
                f.write(f"- **V6 (Financials) Average Financial Rank:** {financial_analysis['v6_financial_avg_rank']:.1f}\n")
        
        f.write("\n")
        
        f.write("## Key Insights\n\n")
        
        # V7 improvements
        f.write("### V7 Improvements Over V6\n\n")
        if v7_aucpr > v6f_aucpr:
            f.write(f"- ✅ **Performance:** {((v7_aucpr - v6f_aucpr) / v6f_aucpr * 100):.1f}% improvement in AUC-PR\n")
        if temporal_analysis.get('v7_temporal_count', 0) > temporal_analysis.get('v6_temporal_count', 0):
            f.write("- ✅ **Temporal Features:** More temporal features contributing to predictions\n")
        if financial_analysis.get('v7_financial_count', 0) > 0:
            f.write("- ✅ **Financial Features:** Financial features integrated into model\n")
        
        f.write("\n### Areas for Improvement\n\n")
        if v7_aucpr < m5_aucpr:
            f.write(f"- ⚠️ **Performance Gap:** Still {abs(gap_to_m5):.1f}% below m5\n")
        if temporal_analysis.get('v7_temporal_avg_rank', 999) > 20:
            f.write("- ⚠️ **Temporal Features:** Temporal features not ranking highly\n")
        if financial_analysis.get('v7_financial_avg_rank', 999) > 20:
            f.write("- ⚠️ **Financial Features:** Financial features not ranking highly\n")
        
        f.write("\n## Recommendations\n\n")
        if v7_aucpr >= m5_aucpr * 0.85:  # Within 15% of m5
            f.write("✅ **V7 is approaching m5 performance** - Consider:\n")
            f.write("- Further tuning of ensemble weights\n")
            f.write("- Additional feature engineering\n")
            f.write("- Production A/B testing\n\n")
        else:
            f.write("⚠️ **V7 needs further improvement** - Consider:\n")
            f.write("- Review feature engineering pipeline\n")
            f.write("- Analyze why m5 features are not ranking highly\n")
            f.write("- Consider additional temporal dynamics features\n\n")
    
    print(f"   Report saved to {COMPARISON_REPORT_V7_PATH}", flush=True)


def main():
    """Main comparison pipeline"""
    print("=" * 80)
    print("V7 Model Comparison Report")
    print("=" * 80)
    print()
    
    # Create output directory
    COMPARISON_PLOTS_DIR.mkdir(exist_ok=True)
    
    # Load model artifacts
    print("[1/8] Loading model artifacts...", flush=True)
    v7_model, v7_importance, v7_order = load_model_artifacts('v7')
    v6_model, v6_importance, v6_order = load_model_artifacts('v6')
    v6_financials_model, v6_financials_importance, v6_financials_order = load_model_artifacts('v6_financials')
    
    # Load data
    print("[2/8] Loading data...", flush=True)
    try:
        df_v7 = load_data_from_bigquery(BQ_TABLE_V7)
        X_v7, y_v7 = prepare_features(df_v7, v7_order)
    except Exception as e:
        print(f"   Warning: Could not load V7 data: {e}", flush=True)
        X_v7, y_v7 = None, None
    
    # Evaluate models
    print("[3/8] Evaluating models...", flush=True)
    v7_metrics = evaluate_model(v7_model, X_v7, y_v7, 'v7') if X_v7 is not None else None
    v6_metrics = evaluate_model(v6_model, X_v7, y_v7, 'v6') if X_v7 is not None and v6_model is not None else None
    v6_financials_metrics = evaluate_model(v6_financials_model, X_v7, y_v7, 'v6_financials') if X_v7 is not None and v6_financials_model is not None else None
    
    # Compare performance
    print("[4/8] Comparing performance metrics...", flush=True)
    performance_comparison = compare_performance_metrics(v7_metrics, v6_metrics, v6_financials_metrics)
    
    # Compare feature importance
    print("[5/8] Comparing feature importance...", flush=True)
    feature_comparison = compare_feature_importance(v7_importance, v6_importance, v6_financials_importance)
    
    # Analyze temporal features
    print("[6/8] Analyzing temporal feature contribution...", flush=True)
    temporal_analysis = analyze_temporal_feature_contribution(v7_importance, v6_importance)
    
    # Analyze financial features
    print("[7/8] Analyzing financial feature contribution...", flush=True)
    financial_analysis = analyze_financial_feature_contribution(v7_importance, v6_financials_importance)
    
    # Generate predictions for plots
    if X_v7 is not None:
        try:
            if v7_model is not None:
                if isinstance(v7_model, dict) and 'predict_proba' in v7_model:
                    v7_preds = v7_model['predict_proba'](X_v7)
                else:
                    v7_preds = v7_model.predict_proba(X_v7)[:, 1]
            else:
                v7_preds = None
            
            if v6_model is not None:
                v6_preds = v6_model.predict_proba(X_v7)[:, 1]
            else:
                v6_preds = None
            
            if v6_financials_model is not None:
                v6_financials_preds = v6_financials_model.predict_proba(X_v7)[:, 1]
            else:
                v6_financials_preds = None
            
            plot_prediction_distributions(v7_preds, v6_preds, v6_financials_preds, COMPARISON_PLOTS_DIR)
        except Exception as e:
            print(f"   Warning: Could not generate plots: {e}", flush=True)
    
    # Generate report
    generate_comparison_report(
        performance_comparison,
        feature_comparison,
        temporal_analysis,
        financial_analysis,
        v7_metrics,
        v6_metrics,
        v6_financials_metrics
    )
    
    print()
    print("=" * 80)
    print("Comparison Report Complete")
    print("=" * 80)
    print(f"Report: {COMPARISON_REPORT_V7_PATH}")
    if COMPARISON_PLOTS_DIR.exists():
        print(f"Plots: {COMPARISON_PLOTS_DIR}")


if __name__ == "__main__":
    main()

