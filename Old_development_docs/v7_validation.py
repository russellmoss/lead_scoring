"""
V7 Model Validation Script
Comprehensive validation checks for V7 model including:
1. CV AUC-PR > 0.12 (approaching m5's 14.92%)
2. Train-Test Gap < 20%
3. CV Coefficient of Variation < 15%
4. Top 5 features include at least 2 business signals (not geographic)
5. Feature importance correlation with m5 > 0.5
6. Calibration ECE < 0.05 across all segments
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import LabelEncoder
from google.cloud import bigquery

# Paths
BASE_DIR = Path(__file__).parent

# V7 Artifacts (will be versioned)
# Try to find the latest version, or use today's date
import glob
import re
today_str = datetime.now().strftime("%Y%m%d")
# Try to find latest model file with today's date
today_models = list(Path(BASE_DIR).glob(f"model_v7_{today_str}_*_ensemble.pkl"))
if today_models:
    # Use the latest one (sorted by name, which includes timestamp)
    latest_model = str(sorted(today_models)[-1])
    # Extract version from filename
    match = re.search(r'model_v7_(\d{8}_\d{4})_ensemble\.pkl', latest_model)
    if match:
        VERSION = match.group(1)
    else:
        VERSION = "20251105_0936"  # Fallback to latest training version
else:
    VERSION = "20251105_0936"  # Fallback to latest training version
MODEL_V7_ENSEMBLE_PATH = BASE_DIR / f"model_v7_{VERSION}_ensemble.pkl"
MODEL_V7_BASELINE_PATH = BASE_DIR / f"model_v7_{VERSION}_baseline_logit.pkl"
CV_INDICES_V7_PATH = BASE_DIR / f"cv_fold_indices_v7_{VERSION}.json"
FEATURE_IMPORTANCE_V7_PATH = BASE_DIR / f"feature_importance_v7_{VERSION}.csv"
FEATURE_ORDER_V7_PATH = BASE_DIR / f"feature_order_v7_{VERSION}.json"
MODEL_TRAINING_REPORT_V7_PATH = BASE_DIR / f"model_training_report_v7_{VERSION}.md"

# Output paths
VALIDATION_REPORT_V7_PATH = BASE_DIR / f"v7_validation_report_{VERSION}.md"

# BigQuery config
PROJECT_ID = "savvy-gtm-analytics"
# Extract date part for table name
DATE_PART = VERSION.split('_')[0] if '_' in VERSION else VERSION
BQ_TABLE = f"savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v7_featured_{DATE_PART}"

# Validation thresholds
THRESHOLDS = {
    'cv_aucpr_min': 0.12,  # Target: >12% (approaching m5's 14.92%)
    'train_test_gap_max': 20.0,  # Max 20% gap
    'cv_coefficient_variation_max': 15.0,  # Max 15% CV
    'ece_max': 0.05,  # Max ECE
    'business_signals_min': 2,  # At least 2 business signals in top 5
    'm5_correlation_min': 0.5  # Min correlation with m5 features
}

# PII features to drop (same as training)
PII_TO_DROP = [
    'FirstName', 'LastName', 
    'Branch_City', 'Branch_County', 'Branch_ZipCode',
    'Home_City', 'Home_County', 'Home_ZipCode',
    'RIAFirmCRD', 'RIAFirmName',
    'PersonalWebpage', 'Notes'
]

# Geographic features (not business signals)
GEOGRAPHIC_FEATURES = [
    'Home_State', 'Branch_State', 'Home_MetropolitanArea',
    'Branch_Latitude', 'Branch_Longitude', 'Home_Latitude', 'Home_Longitude',
    'Home_County', 'Branch_County', 'Home_ZipCode', 'Branch_ZipCode'
]

# m5 top features (from m5_vs_V1_Model_Comparison_Analysis.md)
M5_TOP_FEATURES = [
    'Multi_RIA_Relationships',
    'HNW_Asset_Concentration',
    'Client_Efficiency_Score',
    'Growth_Momentum_Indicator',
    'Institutional_Focus',
    'Breakaway_High_AUM',
    'Digital_Presence_Score',
    'License_Sophistication',
    'Designation_Count',
    'Tenure_Stability_Score'
]


def load_data_from_bigquery() -> pd.DataFrame:
    """Load V7 training dataset from BigQuery"""
    print(f"[1/8] Loading data from BigQuery...", flush=True)
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
    SELECT *
    FROM `{BQ_TABLE}`
    """
    
    df = client.query(query).to_dataframe()
    print(f"   Loaded {len(df):,} rows with {len(df.columns)} columns", flush=True)
    return df


def load_model_artifacts() -> Tuple[Dict[str, Any], Dict[str, List[int]], List[str], pd.DataFrame]:
    """Load model, CV indices, feature order, and feature importance"""
    print(f"[2/8] Loading model artifacts...", flush=True)
    
    # Load ensemble model
    if not MODEL_V7_ENSEMBLE_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_V7_ENSEMBLE_PATH}")
    
    ensemble = joblib.load(MODEL_V7_ENSEMBLE_PATH)
    print(f"   Loaded ensemble model", flush=True)
    
    # Load CV indices
    if not CV_INDICES_V7_PATH.exists():
        raise FileNotFoundError(f"CV indices not found: {CV_INDICES_V7_PATH}")
    
    with open(CV_INDICES_V7_PATH, 'r') as f:
        cv_indices = json.load(f)
    print(f"   Loaded CV indices for {len(cv_indices)} folds", flush=True)
    
    # Load feature order
    if not FEATURE_ORDER_V7_PATH.exists():
        raise FileNotFoundError(f"Feature order not found: {FEATURE_ORDER_V7_PATH}")
    
    with open(FEATURE_ORDER_V7_PATH, 'r') as f:
        feature_order = json.load(f)
    print(f"   Loaded {len(feature_order)} features", flush=True)
    
    # Load feature importance
    if not FEATURE_IMPORTANCE_V7_PATH.exists():
        raise FileNotFoundError(f"Feature importance not found: {FEATURE_IMPORTANCE_V7_PATH}")
    
    feature_importance_df = pd.read_csv(FEATURE_IMPORTANCE_V7_PATH)
    print(f"   Loaded feature importance", flush=True)
    
    return ensemble, cv_indices, feature_order, feature_importance_df


def prepare_features(df: pd.DataFrame, feature_order: List[str]) -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
    """Prepare features for model prediction"""
    # Drop PII
    pii_found = [col for col in PII_TO_DROP if col in df.columns]
    if pii_found:
        df = df.drop(columns=pii_found)
        print(f"   Dropped {len(pii_found)} PII features", flush=True)
    
    # Get target
    if 'target_label' not in df.columns:
        raise ValueError("target_label column not found")
    
    y = df['target_label'].values
    df = df.drop(columns=['target_label'])
    
    # Ensure feature order matches
    missing_features = [f for f in feature_order if f not in df.columns]
    if missing_features:
        print(f"   Warning: {len(missing_features)} features missing. Adding as zeros.", flush=True)
        for feat in missing_features:
            df[feat] = 0
    
    # Select features in order
    X = df[feature_order].copy()
    
    # Handle categoricals (convert to codes if needed)
    for col in X.columns:
        if X[col].dtype == 'object':
            # Try to convert to category codes
            try:
                X[col] = pd.Categorical(X[col]).codes
            except:
                # If conversion fails, use label encoding
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str).fillna(''))
    
    # Fill NaN
    X = X.fillna(0)
    
    return X, y, feature_order


def calculate_ece(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> float:
    """Calculate Expected Calibration Error (ECE)"""
    try:
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]
        
        ece = 0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            # Find samples in this bin
            in_bin = (y_pred > bin_lower) & (y_pred <= bin_upper)
            prop_in_bin = in_bin.mean()
            
            if prop_in_bin > 0:
                # Calculate accuracy in this bin
                accuracy_in_bin = y_true[in_bin].mean()
                # Calculate average confidence in this bin
                avg_confidence_in_bin = y_pred[in_bin].mean()
                # Add to ECE
                ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
        
        return float(ece)
    except Exception as e:
        print(f"   Warning: ECE calculation failed: {e}", flush=True)
        return float('inf')


def validate_cv_performance(
    ensemble: Dict[str, Any],
    cv_indices: Dict[str, List[int]],
    X: pd.DataFrame,
    y: np.ndarray,
    feature_order: List[str]
) -> Dict[str, Any]:
    """Validate CV performance metrics"""
    print(f"[3/8] Validating CV performance...", flush=True)
    
    cv_scores = []
    fold_results = []
    
    for fold_idx, (train_idx, test_idx) in enumerate(zip(
        cv_indices['train_indices'], 
        cv_indices['test_indices']
    )):
        X_train_fold = X.iloc[train_idx]
        X_test_fold = X.iloc[test_idx]
        y_train_fold = y[train_idx]
        y_test_fold = y[test_idx]
        
        # Get predictions from ensemble
        y_pred_test = ensemble['predict_proba'](X_test_fold)
        
        # Calculate metrics
        aucpr = average_precision_score(y_test_fold, y_pred_test)
        aucroc = roc_auc_score(y_test_fold, y_pred_test)
        
        cv_scores.append(aucpr)
        fold_results.append({
            'fold': fold_idx,
            'aucpr': aucpr,
            'aucroc': aucroc,
            'n_train': len(train_idx),
            'n_test': len(test_idx)
        })
    
    # Calculate statistics
    mean_aucpr = np.mean(cv_scores)
    std_aucpr = np.std(cv_scores)
    cv_coefficient = (std_aucpr / mean_aucpr * 100) if mean_aucpr > 0 else float('inf')
    
    results = {
        'cv_scores': cv_scores,
        'mean_aucpr': mean_aucpr,
        'std_aucpr': std_aucpr,
        'cv_coefficient_variation': cv_coefficient,
        'fold_results': fold_results,
        'passes_threshold': mean_aucpr >= THRESHOLDS['cv_aucpr_min'],
        'passes_stability': cv_coefficient <= THRESHOLDS['cv_coefficient_variation_max']
    }
    
    print(f"   CV AUC-PR: {mean_aucpr:.4f} (std: {std_aucpr:.4f}, CV: {cv_coefficient:.2f}%)", flush=True)
    print(f"   Passes threshold (>={THRESHOLDS['cv_aucpr_min']}): {results['passes_threshold']}", flush=True)
    print(f"   Passes stability (<={THRESHOLDS['cv_coefficient_variation_max']}%): {results['passes_stability']}", flush=True)
    
    return results


def validate_train_test_gap(
    ensemble: Dict[str, Any],
    cv_indices: Dict[str, List[int]],
    X: pd.DataFrame,
    y: np.ndarray
) -> Dict[str, Any]:
    """Validate train-test performance gap"""
    print(f"[4/8] Validating train-test gap...", flush=True)
    
    # Use first fold for train-test comparison
    train_idx = cv_indices['train_indices'][0]
    test_idx = cv_indices['test_indices'][0]
    
    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]
    y_train = y[train_idx]
    y_test = y[test_idx]
    
    # Get predictions
    y_pred_train = ensemble['predict_proba'](X_train)
    y_pred_test = ensemble['predict_proba'](X_test)
    
    # Calculate metrics
    train_aucpr = average_precision_score(y_train, y_pred_train)
    test_aucpr = average_precision_score(y_test, y_pred_test)
    
    # Calculate gap
    if train_aucpr > 0:
        gap_pct = ((train_aucpr - test_aucpr) / train_aucpr) * 100
    else:
        gap_pct = 0.0
    
    results = {
        'train_aucpr': train_aucpr,
        'test_aucpr': test_aucpr,
        'gap_pct': gap_pct,
        'passes_threshold': gap_pct <= THRESHOLDS['train_test_gap_max']
    }
    
    print(f"   Train AUC-PR: {train_aucpr:.4f}", flush=True)
    print(f"   Test AUC-PR: {test_aucpr:.4f}", flush=True)
    print(f"   Gap: {gap_pct:.2f}%", flush=True)
    print(f"   Passes threshold (<={THRESHOLDS['train_test_gap_max']}%): {results['passes_threshold']}", flush=True)
    
    return results


def validate_business_signals(feature_importance_df: pd.DataFrame) -> Dict[str, Any]:
    """Validate that top 5 features include business signals"""
    print(f"[5/8] Validating business signals in top features...", flush=True)
    
    # Get top 5 features
    top_5 = feature_importance_df.head(5)['feature'].tolist()
    
    # Count business signals (non-geographic)
    business_signals = [f for f in top_5 if f not in GEOGRAPHIC_FEATURES]
    num_business_signals = len(business_signals)
    
    results = {
        'top_5_features': top_5,
        'business_signals': business_signals,
        'num_business_signals': num_business_signals,
        'passes_threshold': num_business_signals >= THRESHOLDS['business_signals_min']
    }
    
    print(f"   Top 5 features: {top_5}", flush=True)
    print(f"   Business signals: {business_signals}", flush=True)
    print(f"   Passes threshold (>={THRESHOLDS['business_signals_min']}): {results['passes_threshold']}", flush=True)
    
    return results


def validate_m5_correlation(feature_importance_df: pd.DataFrame) -> Dict[str, Any]:
    """Validate feature importance correlation with m5"""
    print(f"[6/8] Validating m5 feature correlation...", flush=True)
    
    # Create feature ranking for V7
    v7_ranking = {row['feature']: idx for idx, row in feature_importance_df.iterrows()}
    
    # Create feature ranking for m5 (top features ranked higher)
    m5_ranking = {feat: idx for idx, feat in enumerate(M5_TOP_FEATURES)}
    
    # Find common features
    common_features = set(v7_ranking.keys()) & set(m5_ranking.keys())
    
    if len(common_features) < 3:
        print(f"   Warning: Only {len(common_features)} common features found", flush=True)
        return {
            'correlation': 0.0,
            'common_features': list(common_features),
            'passes_threshold': False
        }
    
    # Get rankings for common features
    v7_ranks = [v7_ranking[f] for f in common_features]
    m5_ranks = [m5_ranking[f] for f in common_features]
    
    # Calculate Spearman correlation
    correlation, p_value = stats.spearmanr(v7_ranks, m5_ranks)
    
    results = {
        'correlation': correlation if not np.isnan(correlation) else 0.0,
        'p_value': p_value if not np.isnan(p_value) else 1.0,
        'common_features': list(common_features),
        'passes_threshold': correlation >= THRESHOLDS['m5_correlation_min']
    }
    
    print(f"   Correlation with m5: {correlation:.4f} (p={p_value:.4f})", flush=True)
    print(f"   Common features: {len(common_features)}", flush=True)
    print(f"   Passes threshold (>={THRESHOLDS['m5_correlation_min']}): {results['passes_threshold']}", flush=True)
    
    return results


def validate_calibration(
    ensemble: Dict[str, Any],
    cv_indices: Dict[str, List[int]],
    X: pd.DataFrame,
    y: np.ndarray
) -> Dict[str, Any]:
    """Validate calibration across segments"""
    print(f"[7/8] Validating calibration...", flush=True)
    
    # Use first fold
    train_idx = cv_indices['train_indices'][0]
    test_idx = cv_indices['test_indices'][0]
    
    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]
    y_train = y[train_idx]
    y_test = y[test_idx]
    
    # Get AUM tier (if available)
    if 'TotalAssetsInMillions' in X_test.columns:
        aum = X_test['TotalAssetsInMillions'].fillna(0)
        aum_tier = pd.cut(
            aum,
            bins=[-np.inf, 100, 500, np.inf],
            labels=['<$100M', '$100-500M', '>$500M']
        )
    else:
        aum_tier = pd.Series(['Unknown'] * len(X_test), index=X_test.index)
    
    # Get predictions
    y_pred_test = ensemble['predict_proba'](X_test)
    
    # Overall ECE
    overall_ece = calculate_ece(y_test, y_pred_test)
    
    # ECE by segment
    segment_ece = {}
    for tier in aum_tier.unique():
        tier_mask = aum_tier == tier
        if tier_mask.sum() > 100:  # Need sufficient samples
            tier_ece = calculate_ece(y_test[tier_mask], y_pred_test[tier_mask])
            segment_ece[str(tier)] = tier_ece
    
    # Check if all pass
    all_pass = overall_ece <= THRESHOLDS['ece_max']
    for ece in segment_ece.values():
        if ece > THRESHOLDS['ece_max']:
            all_pass = False
    
    results = {
        'overall_ece': overall_ece,
        'segment_ece': segment_ece,
        'passes_threshold': all_pass
    }
    
    print(f"   Overall ECE: {overall_ece:.4f}", flush=True)
    for tier, ece in segment_ece.items():
        print(f"   ECE {tier}: {ece:.4f}", flush=True)
    print(f"   Passes threshold (<={THRESHOLDS['ece_max']}): {results['passes_threshold']}", flush=True)
    
    return results


def generate_validation_report(
    cv_results: Dict[str, Any],
    gap_results: Dict[str, Any],
    business_results: Dict[str, Any],
    m5_results: Dict[str, Any],
    calibration_results: Dict[str, Any]
) -> None:
    """Generate comprehensive validation report"""
    print(f"[8/8] Generating validation report...", flush=True)
    
    # Determine overall pass/fail
    all_passed = (
        cv_results['passes_threshold'] and
        cv_results['passes_stability'] and
        gap_results['passes_threshold'] and
        business_results['passes_threshold'] and
        m5_results['passes_threshold'] and
        calibration_results['passes_threshold']
    )
    
    with open(VALIDATION_REPORT_V7_PATH, 'w', encoding='utf-8') as f:
        f.write("# V7 Model Validation Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Version:** {VERSION}\n\n")
        
        f.write("## Overall Status\n\n")
        if all_passed:
            f.write("✅ **ALL VALIDATION GATES PASSED**\n\n")
        else:
            f.write("❌ **VALIDATION GATES FAILED**\n\n")
        
        f.write("## Validation Gates\n\n")
        f.write("| Gate | Status | Value | Threshold |\n")
        f.write("|------|--------|-------|-----------|\n")
        
        # CV Performance
        f.write(f"| CV AUC-PR | {'✅ PASS' if cv_results['passes_threshold'] else '❌ FAIL'} | "
                f"{cv_results['mean_aucpr']:.4f} | >={THRESHOLDS['cv_aucpr_min']} |\n")
        f.write(f"| CV Stability | {'✅ PASS' if cv_results['passes_stability'] else '❌ FAIL'} | "
                f"{cv_results['cv_coefficient_variation']:.2f}% | <={THRESHOLDS['cv_coefficient_variation_max']}% |\n")
        
        # Train-Test Gap
        f.write(f"| Train-Test Gap | {'✅ PASS' if gap_results['passes_threshold'] else '❌ FAIL'} | "
                f"{gap_results['gap_pct']:.2f}% | <={THRESHOLDS['train_test_gap_max']}% |\n")
        
        # Business Signals
        f.write(f"| Business Signals | {'✅ PASS' if business_results['passes_threshold'] else '❌ FAIL'} | "
                f"{business_results['num_business_signals']}/5 | >={THRESHOLDS['business_signals_min']} |\n")
        
        # m5 Correlation
        f.write(f"| m5 Correlation | {'✅ PASS' if m5_results['passes_threshold'] else '❌ FAIL'} | "
                f"{m5_results['correlation']:.4f} | >={THRESHOLDS['m5_correlation_min']} |\n")
        
        # Calibration
        f.write(f"| Calibration ECE | {'✅ PASS' if calibration_results['passes_threshold'] else '❌ FAIL'} | "
                f"{calibration_results['overall_ece']:.4f} | <={THRESHOLDS['ece_max']} |\n")
        
        f.write("\n## Detailed Results\n\n")
        
        # CV Results
        f.write("### Cross-Validation Performance\n\n")
        f.write(f"- **Mean AUC-PR:** {cv_results['mean_aucpr']:.4f}\n")
        f.write(f"- **Std Dev:** {cv_results['std_aucpr']:.4f}\n")
        f.write(f"- **Coefficient of Variation:** {cv_results['cv_coefficient_variation']:.2f}%\n\n")
        f.write("| Fold | AUC-PR | AUC-ROC | Train Size | Test Size |\n")
        f.write("|------|--------|---------|------------|-----------|\n")
        for fold_result in cv_results['fold_results']:
            f.write(f"| {fold_result['fold']} | {fold_result['aucpr']:.4f} | "
                    f"{fold_result['aucroc']:.4f} | {fold_result['n_train']:,} | {fold_result['n_test']:,} |\n")
        
        # Train-Test Gap
        f.write("\n### Train-Test Performance Gap\n\n")
        f.write(f"- **Train AUC-PR:** {gap_results['train_aucpr']:.4f}\n")
        f.write(f"- **Test AUC-PR:** {gap_results['test_aucpr']:.4f}\n")
        f.write(f"- **Gap:** {gap_results['gap_pct']:.2f}%\n")
        if gap_results['gap_pct'] > THRESHOLDS['train_test_gap_max']:
            f.write("\n⚠️ **Warning:** Train-test gap exceeds threshold. Model may be overfitting.\n")
        
        # Business Signals
        f.write("\n### Top 5 Features Analysis\n\n")
        f.write("**Top 5 Features:**\n")
        for i, feat in enumerate(business_results['top_5_features'], 1):
            is_business = feat not in GEOGRAPHIC_FEATURES
            marker = "✅" if is_business else "📍"
            f.write(f"{i}. {marker} {feat}\n")
        f.write(f"\n**Business Signals:** {business_results['num_business_signals']}/5\n")
        
        # m5 Correlation
        f.write("\n### m5 Feature Importance Correlation\n\n")
        f.write(f"- **Spearman Correlation:** {m5_results['correlation']:.4f}\n")
        f.write(f"- **P-Value:** {m5_results['p_value']:.4f}\n")
        f.write(f"- **Common Features:** {len(m5_results['common_features'])}\n")
        if len(m5_results['common_features']) <= 10:
            f.write(f"  - {', '.join(m5_results['common_features'])}\n")
        
        # Calibration
        f.write("\n### Calibration Metrics\n\n")
        f.write(f"- **Overall ECE:** {calibration_results['overall_ece']:.4f}\n")
        f.write("\n**ECE by AUM Tier:**\n")
        for tier, ece in calibration_results['segment_ece'].items():
            status = "✅" if ece <= THRESHOLDS['ece_max'] else "❌"
            f.write(f"- {status} {tier}: {ece:.4f}\n")
        
        f.write("\n## Recommendations\n\n")
        if not all_passed:
            f.write("### Issues to Address:\n\n")
            if not cv_results['passes_threshold']:
                f.write("- **CV AUC-PR below threshold:** Consider feature engineering or model tuning\n")
            if not cv_results['passes_stability']:
                f.write("- **High CV variation:** Model may be unstable. Consider regularization or simpler model\n")
            if not gap_results['passes_threshold']:
                f.write("- **Large train-test gap:** Model may be overfitting. Increase regularization\n")
            if not business_results['passes_threshold']:
                f.write("- **Geographic features dominating:** Review feature engineering to emphasize business signals\n")
            if not m5_results['passes_threshold']:
                f.write("- **Low m5 correlation:** Review feature importance alignment with m5's proven features\n")
            if not calibration_results['passes_threshold']:
                f.write("- **Calibration issues:** Apply calibration or adjust model parameters\n")
        else:
            f.write("✅ **All validation gates passed. Model is ready for production consideration.**\n")
    
    print(f"   Report saved to {VALIDATION_REPORT_V7_PATH}", flush=True)


def main():
    """Main validation pipeline"""
    print("=" * 80)
    print("V7 Model Validation")
    print("=" * 80)
    print()
    
    # Load data
    df = load_data_from_bigquery()
    
    # Load model artifacts
    ensemble, cv_indices, feature_order, feature_importance_df = load_model_artifacts()
    
    # Prepare features
    X, y, feature_order = prepare_features(df, feature_order)
    
    # Run validations
    cv_results = validate_cv_performance(ensemble, cv_indices, X, y, feature_order)
    gap_results = validate_train_test_gap(ensemble, cv_indices, X, y)
    business_results = validate_business_signals(feature_importance_df)
    m5_results = validate_m5_correlation(feature_importance_df)
    calibration_results = validate_calibration(ensemble, cv_indices, X, y)
    
    # Generate report
    generate_validation_report(cv_results, gap_results, business_results, m5_results, calibration_results)
    
    print()
    print("=" * 80)
    print("Validation Complete")
    print("=" * 80)
    print(f"Report: {VALIDATION_REPORT_V7_PATH}")


if __name__ == "__main__":
    main()

