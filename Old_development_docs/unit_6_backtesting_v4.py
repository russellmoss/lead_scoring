"""
Unit 6: Backtesting and Performance Validation (V4)

This script performs comprehensive backtesting and performance validation:
1. Temporal performance stability analysis
2. Business impact metrics (MQLs per 100 dials)
3. Overfitting detection (train vs test gap)
4. Cross-validation consistency checks
5. Comprehensive performance reports
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
from scipy import stats
from sklearn.metrics import (
    average_precision_score, roc_auc_score, precision_recall_curve,
    roc_curve, precision_score, recall_score, f1_score
)
from google.cloud import bigquery

# Paths
BASE_DIR = Path(__file__).parent
MODEL_V4_CALIBRATED_PATH = BASE_DIR / "model_v4_calibrated.pkl"
CV_INDICES_V4_PATH = BASE_DIR / "cv_fold_indices_v4.json"
MODEL_TRAINING_REPORT_V4_PATH = BASE_DIR / "model_training_report_v4.md"
FEATURE_IMPORTANCE_V4_PATH = BASE_DIR / "feature_importance_v4.csv"

# Output paths
BACKTESTING_REPORT_V4_PATH = BASE_DIR / "backtesting_report_v4.md"
PERFORMANCE_VALIDATION_REPORT_V4_PATH = BASE_DIR / "performance_validation_report_v4.md"
OVERFITTING_ANALYSIS_V4_PATH = BASE_DIR / "overfitting_analysis_v4.md"
BUSINESS_IMPACT_METRICS_V4_PATH = BASE_DIR / "business_impact_metrics_v4.csv"
CV_CONSISTENCY_REPORT_V4_PATH = BASE_DIR / "cv_consistency_report_v4.md"

# BigQuery config
PROJECT_ID = "savvy-gtm-analytics"
BQ_TABLE = "savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2"

# PII features to drop (same as V4 training)
PII_TO_DROP = [
    'FirstName', 'LastName', 'Branch_City', 'Branch_County', 'Branch_ZipCode',
    'Home_City', 'Home_County', 'Home_ZipCode', 'RIAFirmCRD', 'RIAFirmName',
    'PersonalWebpage', 'Notes'
]


def create_m5_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create m5's 31 engineered features (same function as in unit_4_train_model_v4.py)
    This is critical - the model was trained with these features
    """
    df = df.copy()
    features_created = []
    
    def safe_divide(numerator, denominator, default=np.nan):
        """Safely divide, handling zeros and NaNs"""
        if isinstance(denominator, pd.Series):
            denominator_clean = denominator.replace(0, np.nan)
            result = numerator / denominator_clean
            return result.fillna(default)
        else:
            if pd.isna(denominator) or denominator == 0:
                return default
            return numerator / denominator
    
    # Only create features that don't exist (from m5 feature engineering)
    # Client efficiency metrics
    if "TotalAssetsInMillions" in df.columns and "NumberClients_Individuals" in df.columns:
        if "AUM_per_Client" not in df.columns:
            df["AUM_per_Client"] = safe_divide(
                df["TotalAssetsInMillions"], 
                df["NumberClients_Individuals"].replace(0, np.nan)
            )
            features_created.append("AUM_per_Client")
    
    if "TotalAssetsInMillions" in df.columns and "Number_IAReps" in df.columns:
        if "AUM_per_IARep" not in df.columns:
            df["AUM_per_IARep"] = safe_divide(
                df["TotalAssetsInMillions"],
                df["Number_IAReps"].replace(0, np.nan)
            )
            features_created.append("AUM_per_IARep")
    
    # Growth indicators
    if "AUMGrowthRate_1Year" in df.columns and "AUMGrowthRate_5Year" in df.columns:
        if "Growth_Acceleration" not in df.columns:
            df["Growth_Acceleration"] = (
                df["AUMGrowthRate_1Year"].fillna(0) - 
                (df["AUMGrowthRate_5Year"].fillna(0) / 5)
            )
            features_created.append("Growth_Acceleration")
        if "Growth_Momentum" not in df.columns:
            df["Growth_Momentum"] = (
                df["AUMGrowthRate_1Year"].fillna(0) * 
                df["AUMGrowthRate_5Year"].fillna(0)
            )
            features_created.append("Growth_Momentum")
    
    # Firm stability
    if "DateOfHireAtCurrentFirm_NumberOfYears" in df.columns:
        if "Number_Of_Prior_Firms" in df.columns:
            num_prior_firms = df["Number_Of_Prior_Firms"]
        else:
            prior_firm_cols = [col for col in df.columns if col.startswith("Number_YearsPriorFirm")]
            num_prior_firms = df[prior_firm_cols].notna().sum(axis=1) if prior_firm_cols else pd.Series(0, index=df.index)
        
        if "Firm_Stability_Score" not in df.columns:
            df["Firm_Stability_Score"] = safe_divide(
                df["DateOfHireAtCurrentFirm_NumberOfYears"],
                (num_prior_firms + 1)
            )
            features_created.append("Firm_Stability_Score")
    
    # Experience efficiency
    if "DateBecameRep_NumberOfYears" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "Experience_Efficiency" not in df.columns:
            df["Experience_Efficiency"] = safe_divide(
                df["TotalAssetsInMillions"],
                (df["DateBecameRep_NumberOfYears"].replace(0, np.nan) + 1)
            )
            features_created.append("Experience_Efficiency")
    
    # Alternative investment focus
    if "AssetsInMillions_MutualFunds" in df.columns and "AssetsInMillions_PrivateFunds" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "Alternative_Investment_Focus" not in df.columns:
            df["Alternative_Investment_Focus"] = safe_divide(
                (df["AssetsInMillions_MutualFunds"].fillna(0) + df["AssetsInMillions_PrivateFunds"].fillna(0)),
                df["TotalAssetsInMillions"].replace(0, np.nan)
            )
            features_created.append("Alternative_Investment_Focus")
    
    # Complex registration
    if "NumberFirmAssociations" in df.columns and "NumberRIAFirmAssociations" in df.columns:
        if "Complex_Registration" not in df.columns:
            df["Complex_Registration"] = (
                (df["NumberFirmAssociations"] > 2) | 
                (df["NumberRIAFirmAssociations"] > 1)
            ).astype(int)
            features_created.append("Complex_Registration")
    
    # High turnover flag
    if "Number_Of_Prior_Firms" in df.columns:
        prior_firm_cols = [col for col in df.columns if col.startswith("Number_YearsPriorFirm")]
        if prior_firm_cols:
            avg_tenure = df[prior_firm_cols].mean(axis=1)
            if "High_Turnover_Flag" not in df.columns:
                df["High_Turnover_Flag"] = (
                    (df["Number_Of_Prior_Firms"] > 3) & 
                    (avg_tenure < 3)
                ).astype(int)
                features_created.append("High_Turnover_Flag")
    
    # Quality score (simplified - needs multiple components)
    quality_score_components = []
    if "Is_Veteran_Advisor" in df.columns:
        quality_score_components.append(("Is_Veteran_Advisor", 0.25))
    if "Has_Scale" in df.columns:
        quality_score_components.append(("Has_Scale", 0.25))
    if "Firm_Stability_Score" in df.columns:
        median_stability = df["Firm_Stability_Score"].median()
        quality_score_components.append(("Firm_Stability_Score_above_median", 0.15, median_stability))
    if "IsPrimaryRIAFirm" in df.columns:
        quality_score_components.append(("IsPrimaryRIAFirm", 0.15))
    if "AUM_per_Client" in df.columns:
        median_aum = df["AUM_per_Client"].median()
        quality_score_components.append(("AUM_per_Client_above_median", 0.10, median_aum))
    if "High_Turnover_Flag" in df.columns:
        quality_score_components.append(("High_Turnover_Flag_inverse", 0.10))
    
    if len(quality_score_components) >= 3 and "Quality_Score" not in df.columns:
        quality_score = pd.Series(0.0, index=df.index)
        for component in quality_score_components:
            if len(component) == 2:
                feat_name, weight = component
                if feat_name in df.columns:
                    feat_series = pd.to_numeric(df[feat_name], errors='coerce').fillna(0)
                    quality_score += feat_series * weight
            elif len(component) == 3:
                feat_name, weight, threshold = component
                if feat_name == "Firm_Stability_Score_above_median":
                    feat_series = pd.to_numeric(df["Firm_Stability_Score"], errors='coerce').fillna(0)
                    quality_score += (feat_series > threshold).astype(int) * weight
                elif feat_name == "AUM_per_Client_above_median":
                    feat_series = pd.to_numeric(df["AUM_per_Client"], errors='coerce').fillna(0)
                    quality_score += (feat_series > threshold).astype(int) * weight
            elif len(component) == 2 and component[0] == "High_Turnover_Flag_inverse":
                quality_score += (1 - df["High_Turnover_Flag"]) * component[1]
        df["Quality_Score"] = quality_score
        features_created.append("Quality_Score")
    
    if features_created:
        print(f"   Created {len(features_created)} m5 features: {', '.join(features_created)}", flush=True)
    
    return df


def load_config() -> Dict[str, Any]:
    """Load model configuration"""
    config_path = BASE_DIR / "config" / "v1_model_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data_from_bigquery() -> pd.DataFrame:
    """Load training data from BigQuery"""
    print(f"[1/7] Loading data from BigQuery table: {BQ_TABLE}...", flush=True)
    
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{BQ_TABLE}`'
    
    df = client.query(query).to_dataframe()
    print(f"   Loaded {len(df):,} rows, {len(df.columns)} columns", flush=True)
    
    return df


def cast_categoricals_inplace(df: pd.DataFrame, columns: List[str]) -> None:
    """Cast object dtype columns to category for XGBoost compatibility"""
    for c in columns:
        if c in df.columns and df[c].dtype == "object":
            try:
                has_nan = df[c].isna().any()
                if has_nan:
                    df[c] = df[c].fillna("__MISSING__").astype("category")
                    if "__MISSING__" not in df[c].cat.categories:
                        df[c] = df[c].cat.add_categories(["__MISSING__"])
                else:
                    df[c] = df[c].astype("category")
                
                if len(df[c].cat.categories) == 0:
                    df[c] = df[c].cat.add_categories(["__MISSING__"])
                    df[c] = df[c].fillna("__MISSING__")
            except Exception:
                try:
                    df[c] = df[c].fillna("__MISSING__").astype("category")
                    if "__MISSING__" not in df[c].cat.categories:
                        df[c] = df[c].cat.add_categories(["__MISSING__"])
                except Exception:
                    df[c] = df[c].astype(str).fillna("__MISSING__").astype("category")


def calculate_ks_statistic(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Kolmogorov-Smirnov statistic for score distribution drift"""
    # Get scores for positive and negative classes
    pos_scores = y_pred[y_true == 1]
    neg_scores = y_pred[y_true == 0]
    
    if len(pos_scores) == 0 or len(neg_scores) == 0:
        return 0.0
    
    # Calculate KS statistic
    ks_stat, _ = stats.ks_2samp(pos_scores, neg_scores)
    return float(ks_stat)


def calculate_performance_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray) -> Dict[str, float]:
    """Calculate comprehensive performance metrics"""
    metrics = {
        "aucpr": float(average_precision_score(y_true, y_proba)),
        "aucroc": float(roc_auc_score(y_true, y_proba)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    
    # Precision at top 10% and 20%
    n_top_10 = max(1, int(len(y_proba) * 0.1))
    n_top_20 = max(1, int(len(y_proba) * 0.2))
    
    top_10_indices = np.argsort(y_proba)[-n_top_10:]
    top_20_indices = np.argsort(y_proba)[-n_top_20:]
    
    metrics["precision_at_10pct"] = float(y_true[top_10_indices].mean()) if len(top_10_indices) > 0 else 0.0
    metrics["precision_at_20pct"] = float(y_true[top_20_indices].mean()) if len(top_20_indices) > 0 else 0.0
    
    # Lift metrics
    baseline_positive_rate = float(y_true.mean())
    metrics["lift_at_10pct"] = metrics["precision_at_10pct"] / baseline_positive_rate if baseline_positive_rate > 0 else 0.0
    metrics["lift_at_20pct"] = metrics["precision_at_20pct"] / baseline_positive_rate if baseline_positive_rate > 0 else 0.0
    
    return metrics


def calculate_business_impact_metrics(
    df: pd.DataFrame,
    y_proba: np.ndarray,
    score_thresholds: List[float] = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
) -> pd.DataFrame:
    """Calculate MQLs per 100 dials at different score thresholds"""
    results = []
    
    for threshold in score_thresholds:
        # Get leads above threshold
        above_threshold = y_proba >= threshold
        n_above = above_threshold.sum()
        
        if n_above == 0:
            continue
        
        # Calculate conversions (MQLs) in this group
        conversions = df.loc[above_threshold, "target_label"].sum()
        
        # MQLs per 100 dials (assuming each lead = 1 dial)
        mqls_per_100 = (conversions / n_above) * 100 if n_above > 0 else 0.0
        
        # Conversion rate
        conversion_rate = conversions / n_above if n_above > 0 else 0.0
        
        results.append({
            "score_threshold": threshold,
            "leads_above_threshold": int(n_above),
            "mqls": int(conversions),
            "mqls_per_100_dials": round(mqls_per_100, 2),
            "conversion_rate": round(conversion_rate, 4),
            "pct_of_total_leads": round((n_above / len(df)) * 100, 2)
        })
    
    return pd.DataFrame(results)


def perform_temporal_analysis(
    df: pd.DataFrame,
    model: Any,
    feature_cols: List[str],
    segment_calibrators: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Perform temporal performance stability analysis"""
    print(f"[2/7] Performing temporal performance stability analysis...", flush=True)
    
    # Ensure we have a timestamp column
    if "Stage_Entered_Contacting__c" not in df.columns:
        raise ValueError("Stage_Entered_Contacting__c column not found")
    
    # Convert to datetime
    df["contact_date"] = pd.to_datetime(df["Stage_Entered_Contacting__c"], errors="coerce", utc=True)
    df = df[df["contact_date"].notna()].copy()
    
    # Define time periods (quarters)
    df["quarter"] = df["contact_date"].dt.to_period("Q")
    quarters = sorted(df["quarter"].unique())
    
    results = {}
    
    for quarter in quarters:
        quarter_df = df[df["quarter"] == quarter].copy()
        
        if len(quarter_df) < 100:  # Skip quarters with too few samples
            continue
        
        # Ensure all expected features exist (add missing as NaN)
        for feat in feature_cols:
            if feat not in quarter_df.columns:
                quarter_df[feat] = np.nan
        
        X_quarter = quarter_df[feature_cols].copy()
        y_quarter = quarter_df["target_label"].astype(int).values
        
        # CRITICAL: Cast categoricals to match training (XGBoost requires category dtype, not object)
        cast_categoricals_inplace(X_quarter, feature_cols)
        
        # Get predictions
        y_proba_quarter = model.predict_proba(X_quarter)[:, 1]
        y_pred_quarter = (y_proba_quarter >= 0.5).astype(int)
        
        # Calculate metrics
        metrics = calculate_performance_metrics(y_quarter, y_pred_quarter, y_proba_quarter)
        metrics["n_samples"] = len(quarter_df)
        metrics["positive_rate"] = float(y_quarter.mean())
        
        # KS statistic for score distribution
        metrics["ks_statistic"] = calculate_ks_statistic(y_quarter, y_proba_quarter)
        
        results[str(quarter)] = metrics
    
    print(f"   Analyzed {len(results)} time periods", flush=True)
    return results


def detect_overfitting(
    train_metrics: Dict[str, float],
    test_metrics: Dict[str, float]
) -> Dict[str, Any]:
    """Detect overfitting by comparing train vs test performance"""
    print(f"[3/7] Detecting overfitting...", flush=True)
    
    overfitting_metrics = {}
    
    for metric_name in ["aucpr", "aucroc", "precision", "recall", "f1"]:
        train_val = train_metrics.get(metric_name, 0.0)
        test_val = test_metrics.get(metric_name, 0.0)
        
        if train_val > 0:
            gap_pct = ((train_val - test_val) / train_val) * 100
        else:
            gap_pct = 0.0
        
        overfitting_metrics[f"{metric_name}_gap_pct"] = gap_pct
        overfitting_metrics[f"{metric_name}_train"] = train_val
        overfitting_metrics[f"{metric_name}_test"] = test_val
    
    # Overall assessment
    aucpr_gap = overfitting_metrics["aucpr_gap_pct"]
    
    if aucpr_gap < 5:
        assessment = "No overfitting detected"
    elif aucpr_gap < 10:
        assessment = "Minor overfitting (acceptable)"
    else:
        assessment = "Significant overfitting detected"
    
    overfitting_metrics["assessment"] = assessment
    overfitting_metrics["overfitting_detected"] = aucpr_gap >= 10
    
    print(f"   AUC-PR gap: {aucpr_gap:.2f}% - {assessment}", flush=True)
    return overfitting_metrics


def analyze_cv_consistency(
    cv_indices: Dict[str, List[int]],
    df: pd.DataFrame,
    model: Any,
    feature_cols: List[str],
    segment_calibrators: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Analyze cross-validation performance consistency across folds"""
    print(f"[4/7] Analyzing CV consistency...", flush=True)
    
    fold_metrics = []
    
    # CV indices is a list of dicts, not a dict
    if isinstance(cv_indices, list):
        fold_iter = cv_indices
    else:
        fold_iter = cv_indices.items()
    
    for fold_item in fold_iter:
        if isinstance(cv_indices, list):
            fold_name = f"fold_{fold_item.get('fold', len(fold_metrics))}"
            test_indices = fold_item["test_indices"]
        else:
            fold_name, test_indices = fold_item
        
        # Get train indices (all indices not in test)
        all_indices = set(range(len(df)))
        train_indices = sorted(list(all_indices - set(test_indices)))
        
        # Ensure all expected features exist (add missing as NaN)
        for feat in feature_cols:
            if feat not in df.columns:
                df[feat] = np.nan
        
        # Get data splits
        X_train = df.iloc[train_indices][feature_cols].copy()
        y_train = df.iloc[train_indices]["target_label"].astype(int).values
        X_test = df.iloc[test_indices][feature_cols].copy()
        y_test = df.iloc[test_indices]["target_label"].astype(int).values
        
        # CRITICAL: Cast categoricals to match training (XGBoost requires category dtype, not object)
        cast_categoricals_inplace(X_train, feature_cols)
        cast_categoricals_inplace(X_test, feature_cols)
        
        # Get predictions
        y_proba_train = model.predict_proba(X_train)[:, 1]
        y_proba_test = model.predict_proba(X_test)[:, 1]
        y_pred_train = (y_proba_train >= 0.5).astype(int)
        y_pred_test = (y_proba_test >= 0.5).astype(int)
        
        # Calculate metrics
        train_metrics = calculate_performance_metrics(y_train, y_pred_train, y_proba_train)
        test_metrics = calculate_performance_metrics(y_test, y_pred_test, y_proba_test)
        
        fold_metrics.append({
            "fold": fold_name,
            "train_aucpr": train_metrics["aucpr"],
            "test_aucpr": test_metrics["aucpr"],
            "train_aucroc": train_metrics["aucroc"],
            "test_aucroc": test_metrics["aucroc"],
            "n_train": len(train_indices),
            "n_test": len(test_indices),
            "train_positive_rate": float(y_train.mean()),
            "test_positive_rate": float(y_test.mean())
        })
    
    # Calculate consistency metrics
    test_aucprs = [m["test_aucpr"] for m in fold_metrics]
    test_aucrocs = [m["test_aucroc"] for m in fold_metrics]
    
    consistency = {
        "fold_metrics": fold_metrics,
        "mean_test_aucpr": float(np.mean(test_aucprs)),
        "std_test_aucpr": float(np.std(test_aucprs)),
        "cv_test_aucpr": float(np.std(test_aucprs) / np.mean(test_aucprs) * 100) if np.mean(test_aucprs) > 0 else 0.0,
        "mean_test_aucroc": float(np.mean(test_aucrocs)),
        "std_test_aucroc": float(np.std(test_aucrocs)),
        "cv_test_aucroc": float(np.std(test_aucrocs) / np.mean(test_aucrocs) * 100) if np.mean(test_aucrocs) > 0 else 0.0,
        "min_test_aucpr": float(np.min(test_aucprs)),
        "max_test_aucpr": float(np.max(test_aucprs)),
        "range_test_aucpr": float(np.max(test_aucprs) - np.min(test_aucprs))
    }
    
    print(f"   CV AUC-PR: {consistency['mean_test_aucpr']:.4f} ± {consistency['std_test_aucpr']:.4f} (CV: {consistency['cv_test_aucpr']:.2f}%)", flush=True)
    return consistency


def generate_reports(
    temporal_results: Dict[str, Any],
    overfitting_results: Dict[str, Any],
    cv_consistency: Dict[str, Any],
    business_impact_df: pd.DataFrame,
    df: pd.DataFrame,
    y_proba: np.ndarray,
    y_true: np.ndarray
) -> None:
    """Generate all required reports"""
    print(f"[5/7] Generating reports...", flush=True)
    
    # 1. Backtesting Report
    with open(BACKTESTING_REPORT_V4_PATH, "w", encoding="utf-8") as f:
        f.write("# Backtesting Report V4\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Temporal Performance Stability Analysis\n\n")
        f.write("### Performance by Quarter\n\n")
        f.write("| Quarter | Samples | Positive Rate | AUC-PR | AUC-ROC | KS Statistic |\n")
        f.write("|---------|---------|---------------|--------|---------|--------------|\n")
        
        for quarter, metrics in sorted(temporal_results.items()):
            f.write(f"| {quarter} | {metrics['n_samples']:,} | {metrics['positive_rate']:.4f} | "
                   f"{metrics['aucpr']:.4f} | {metrics['aucroc']:.4f} | {metrics['ks_statistic']:.4f} |\n")
        
        # Calculate drift metrics
        if len(temporal_results) > 1:
            aucprs = [m["aucpr"] for m in temporal_results.values()]
            ks_stats = [m["ks_statistic"] for m in temporal_results.values()]
            
            f.write("\n### Stability Metrics\n\n")
            f.write(f"- **AUC-PR Range:** {min(aucprs):.4f} to {max(aucprs):.4f}\n")
            f.write(f"- **AUC-PR Std Dev:** {np.std(aucprs):.4f}\n")
            f.write(f"- **Max KS Statistic:** {max(ks_stats):.4f}\n")
            f.write(f"- **Stability Assessment:** ")
            if max(ks_stats) <= 0.1:
                f.write("✅ Stable (KS ≤ 0.1)\n")
            else:
                f.write("⚠️ Drift detected (KS > 0.1)\n")
    
    # 2. Performance Validation Report
    overall_metrics = calculate_performance_metrics(y_true, (y_proba >= 0.5).astype(int), y_proba)
    
    with open(PERFORMANCE_VALIDATION_REPORT_V4_PATH, "w", encoding="utf-8") as f:
        f.write("# Performance Validation Report V4\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Overall Performance Metrics\n\n")
        f.write(f"- **AUC-PR:** {overall_metrics['aucpr']:.4f}\n")
        f.write(f"- **AUC-ROC:** {overall_metrics['aucroc']:.4f}\n")
        f.write(f"- **Precision:** {overall_metrics['precision']:.4f}\n")
        f.write(f"- **Recall:** {overall_metrics['recall']:.4f}\n")
        f.write(f"- **F1 Score:** {overall_metrics['f1']:.4f}\n")
        f.write(f"- **Precision @ 10%:** {overall_metrics['precision_at_10pct']:.4f}\n")
        f.write(f"- **Precision @ 20%:** {overall_metrics['precision_at_20pct']:.4f}\n")
        f.write(f"- **Lift @ 10%:** {overall_metrics['lift_at_10pct']:.2f}x\n")
        f.write(f"- **Lift @ 20%:** {overall_metrics['lift_at_20pct']:.2f}x\n\n")
        
        f.write("## Cross-Validation Consistency\n\n")
        f.write(f"- **Mean Test AUC-PR:** {cv_consistency['mean_test_aucpr']:.4f}\n")
        f.write(f"- **Std Dev Test AUC-PR:** {cv_consistency['std_test_aucpr']:.4f}\n")
        f.write(f"- **CV Coefficient:** {cv_consistency['cv_test_aucpr']:.2f}%\n")
        f.write(f"- **Range:** {cv_consistency['min_test_aucpr']:.4f} to {cv_consistency['max_test_aucpr']:.4f}\n\n")
        
        f.write("## Validation Gates\n\n")
        f.write(f"- **AUC-PR > 0.20:** {'✅ PASS' if overall_metrics['aucpr'] > 0.20 else '❌ FAIL'}\n")
        f.write(f"- **CV Coefficient < 15%:** {'✅ PASS' if cv_consistency['cv_test_aucpr'] < 15 else '❌ FAIL'}\n")
        f.write(f"- **Train-Test Gap < 10%:** {'✅ PASS' if overfitting_results['aucpr_gap_pct'] < 10 else '❌ FAIL'}\n")
    
    # 3. Overfitting Analysis
    with open(OVERFITTING_ANALYSIS_V4_PATH, "w", encoding="utf-8") as f:
        f.write("# Overfitting Analysis V4\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Train vs Test Performance Gap\n\n")
        f.write("| Metric | Train | Test | Gap (%) |\n")
        f.write("|--------|-------|------|----------|\n")
        for metric in ["aucpr", "aucroc", "precision", "recall", "f1"]:
            train_val = overfitting_results[f"{metric}_train"]
            test_val = overfitting_results[f"{metric}_test"]
            gap = overfitting_results[f"{metric}_gap_pct"]
            f.write(f"| {metric.upper()} | {train_val:.4f} | {test_val:.4f} | {gap:.2f}% |\n")
        
        f.write(f"\n## Assessment\n\n")
        f.write(f"**{overfitting_results['assessment']}**\n\n")
        f.write(f"- **AUC-PR Gap:** {overfitting_results['aucpr_gap_pct']:.2f}%\n")
        if overfitting_results['overfitting_detected']:
            f.write("⚠️ **Overfitting detected** - Consider regularization or simpler model\n")
        else:
            f.write("✅ **No significant overfitting** - Model generalizes well\n")
    
    # 4. Business Impact Metrics (CSV)
    business_impact_df.to_csv(BUSINESS_IMPACT_METRICS_V4_PATH, index=False)
    
    # 5. CV Consistency Report
    with open(CV_CONSISTENCY_REPORT_V4_PATH, "w", encoding="utf-8") as f:
        f.write("# CV Consistency Report V4\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Fold-by-Fold Performance\n\n")
        f.write("| Fold | Train AUC-PR | Test AUC-PR | Train AUC-ROC | Test AUC-ROC | Train N | Test N |\n")
        f.write("|------|--------------|-------------|----------------|--------------|---------|--------|\n")
        
        for fold_metric in cv_consistency["fold_metrics"]:
            f.write(f"| {fold_metric['fold']} | {fold_metric['train_aucpr']:.4f} | "
                   f"{fold_metric['test_aucpr']:.4f} | {fold_metric['train_aucroc']:.4f} | "
                   f"{fold_metric['test_aucroc']:.4f} | {fold_metric['n_train']:,} | {fold_metric['n_test']:,} |\n")
        
        f.write("\n## Consistency Summary\n\n")
        f.write(f"- **Mean Test AUC-PR:** {cv_consistency['mean_test_aucpr']:.4f}\n")
        f.write(f"- **Std Dev:** {cv_consistency['std_test_aucpr']:.4f}\n")
        f.write(f"- **Coefficient of Variation:** {cv_consistency['cv_test_aucpr']:.2f}%\n")
        f.write(f"- **Range:** {cv_consistency['min_test_aucpr']:.4f} to {cv_consistency['max_test_aucpr']:.4f}\n\n")
        
        f.write("## Validation\n\n")
        if cv_consistency['cv_test_aucpr'] < 15:
            f.write("✅ **CV consistency PASS** - Model performance is stable across folds\n")
        else:
            f.write("⚠️ **CV consistency WARNING** - High variation across folds\n")
    
    print(f"   All reports generated", flush=True)


def main():
    """Main backtesting and validation pipeline"""
    print("=" * 80)
    print("Unit 6: Backtesting and Performance Validation (V4)")
    print("=" * 80)
    print()
    
    # Load artifacts
    print(f"[1/7] Loading model and artifacts...", flush=True)
    if not MODEL_V4_CALIBRATED_PATH.exists():
        raise FileNotFoundError(f"Calibrated model not found: {MODEL_V4_CALIBRATED_PATH}")
    if not CV_INDICES_V4_PATH.exists():
        raise FileNotFoundError(f"CV indices not found: {CV_INDICES_V4_PATH}")
    
    # Load calibrated model (it's a dict with model, global_calibrator, segment_calibrators)
    calibrated_model_data = joblib.load(MODEL_V4_CALIBRATED_PATH)
    model_v4 = calibrated_model_data['global_calibrator']  # Use global calibrator for predictions
    segment_calibrators = calibrated_model_data.get('segment_calibrators', {})
    
    with open(CV_INDICES_V4_PATH, "r", encoding="utf-8") as f:
        cv_indices = json.load(f)
    
    print(f"   Loaded calibrated model and {len(cv_indices)} CV folds", flush=True)
    
    # Load the official feature order from the V4 training run
    print(f"[1.5/7] Loading official feature order from feature_order_v4.json...", flush=True)
    feature_order_path = BASE_DIR / "feature_order_v4.json"
    if not feature_order_path.exists():
        raise FileNotFoundError(f"Feature order file not found: {feature_order_path}. Please re-run unit_4_train_model_v4.py first.")
    with open(feature_order_path, 'r', encoding='utf-8') as f:
        OFFICIAL_FEATURE_ORDER = json.load(f)
    print(f"   Loaded {len(OFFICIAL_FEATURE_ORDER)} features from official training order", flush=True)
    
    # Load data
    df = load_data_from_bigquery()
    
    # CRITICAL: Drop PII features FIRST to match the V4 model's training data (120 features, not 132)
    # This must happen before any feature engineering or preparation
    print(f"[1.5/7] Removing PII features to match V4 model training data...", flush=True)
    df = df.drop(columns=PII_TO_DROP, errors='ignore')
    pii_dropped = [col for col in PII_TO_DROP if col not in df.columns]
    print(f"   Dropped {len(pii_dropped)} PII features: {', '.join(pii_dropped)}", flush=True)
    
    # Create m5 engineered features (same as training and calibration)
    print(f"   Creating m5 engineered features...", flush=True)
    df = create_m5_engineered_features(df)
    
    # Define metadata columns
    metadata_cols = {
        "Id", "FA_CRD__c", "Stage_Entered_Contacting__c",
        "Stage_Entered_Call_Scheduled__c", "target_label",
        "is_eligible_for_mutable_features", "is_in_right_censored_window",
        "days_to_conversion"
    }
    
    # CRITICAL: Get feature names directly from the booster inside the calibrated model
    # The booster has the EXACT feature names and order it was trained with
    base_model = calibrated_model_data['model']
    
    # Try to get feature names from the booster (most accurate source)
    actual_expected_features = None
    try:
        # Navigate through calibration wrapper to get to the booster
        if hasattr(model_v4, 'calibrated_classifiers_'):
            first_cal = model_v4.calibrated_classifiers_[0]
            if hasattr(first_cal, 'base_estimator'):
                base_est = first_cal.base_estimator
                # Get booster from XGBoost model
                if hasattr(base_est, 'get_booster'):
                    booster = base_est.get_booster()
                    if hasattr(booster, 'feature_names'):
                        # Booster has feature names in the EXACT order it expects
                        actual_expected_features = list(booster.feature_names)
                        print(f"   Got feature names from booster ({len(actual_expected_features)} features)", flush=True)
                        print(f"   First 5 booster features: {actual_expected_features[:5]}", flush=True)
    except Exception as e:
        print(f"   Warning: Could not get from booster: {e}", flush=True)
    
    # Fallback: try feature_names_in_ from calibrated base estimator
    if actual_expected_features is None:
        try:
            if hasattr(model_v4, 'calibrated_classifiers_'):
                first_cal = model_v4.calibrated_classifiers_[0]
                if hasattr(first_cal, 'base_estimator'):
                    base_est = first_cal.base_estimator
                    if hasattr(base_est, 'feature_names_in_'):
                        actual_expected_features = list(base_est.feature_names_in_)
                        print(f"   Got feature names from calibrated base estimator ({len(actual_expected_features)} features)", flush=True)
        except Exception as e:
            print(f"   Warning: Could not get from calibrated model: {e}", flush=True)
    
    # Fallback to base model
    if actual_expected_features is None:
        if hasattr(base_model, 'feature_names_in_'):
            actual_expected_features = list(base_model.feature_names_in_)
            print(f"   Got feature names from base model ({len(actual_expected_features)} features)", flush=True)
        else:
            # Last resort: use all non-metadata columns
            actual_expected_features = [c for c in df.columns if c not in metadata_cols]
            print(f"   Using all non-metadata columns ({len(actual_expected_features)} features)", flush=True)
    
    expected_features = actual_expected_features
    print(f"   Model expects {len(expected_features)} features in specific order", flush=True)
    
    # Handle feature name mismatches (e.g., AUM_Per_Client vs AUM_per_Client)
    feature_name_mapping = {}
    for model_feat in expected_features:
        if model_feat not in df.columns:
            # Try to find a case-insensitive match
            possible_matches = [c for c in df.columns if c.lower() == model_feat.lower()]
            if possible_matches:
                feature_name_mapping[model_feat] = possible_matches[0]
                print(f"   Mapping: '{model_feat}' <- '{possible_matches[0]}'", flush=True)
    
    # Apply feature name mappings (copy data from data column to model column name)
    for model_feat, data_feat in feature_name_mapping.items():
        if data_feat in df.columns:
            df[model_feat] = df[data_feat].copy()
    
    # Ensure we have all expected features (add missing ones as NaN)
    # This includes PII features that the model expects (even if they were dropped during training,
    # the model's feature_names_in_ still has them)
    missing_features = []
    for feat in expected_features:
        if feat not in df.columns:
            missing_features.append(feat)
            df[feat] = np.nan
    
    if missing_features:
        print(f"   Warning: {len(missing_features)} expected features missing, adding as NaN", flush=True)
        pii_missing = [f for f in missing_features if f in PII_TO_DROP]
        if pii_missing:
            print(f"     ({len(pii_missing)} are PII features that were removed during V4 training)", flush=True)
    
    # Prepare X with features in the EXACT order the model expects
    # Ensure all expected features exist (add missing as NaN)
    for feat in expected_features:
        if feat not in df.columns:
            df[feat] = np.nan
    
    # CRITICAL: Re-order the DataFrame to EXACTLY match the training order
    # Use the official feature order from training, not the model's expected order
    # This guarantees 100% match with the training data
    print(f"   Re-ordering X to match official 120-feature training order...", flush=True)
    
    # Ensure all official features exist (add missing as NaN)
    for feat in OFFICIAL_FEATURE_ORDER:
        if feat not in df.columns:
            df[feat] = np.nan
    
    # Create X with features in EXACT official training order
    X = df[OFFICIAL_FEATURE_ORDER].copy()
    
    print(f"   Prepared X with {len(X.columns)} features in official order", flush=True)
    print(f"   First 5 features: {list(X.columns[:5])}", flush=True)
    print(f"   Official order first 5: {OFFICIAL_FEATURE_ORDER[:5]}", flush=True)
    
    # Verify order matches
    if list(X.columns) != OFFICIAL_FEATURE_ORDER:
        print(f"   ERROR: Column order mismatch! Reordering...", flush=True)
        X = X[OFFICIAL_FEATURE_ORDER]  # Force reorder to official order
    
    y = df["target_label"].astype(int).values
    
    # Cast categoricals (using official feature order)
    cast_categoricals_inplace(X, OFFICIAL_FEATURE_ORDER)
    
    # Get predictions for entire dataset
    print(f"[6/7] Generating predictions for entire dataset...", flush=True)
    
    # CRITICAL: X is already in the official training order
    # No need to reorder - XGBoost will match based on feature names
    # The official order from training is the source of truth
    print(f"   Final X shape: {X.shape}, using official training order ({len(OFFICIAL_FEATURE_ORDER)} features)", flush=True)
    print(f"   First 5 features: {list(X.columns[:5])}", flush=True)
    
    # Generate predictions using the officially-ordered features
    y_proba = model_v4.predict_proba(X)[:, 1]
    
    y_pred = (y_proba >= 0.5).astype(int)
    
    print(f"   Positive rate: {y.mean():.4f}", flush=True)
    print(f"   Mean predicted score: {y_proba.mean():.4f}", flush=True)
    
    # Perform analyses (using official feature order)
    temporal_results = perform_temporal_analysis(df, model_v4, OFFICIAL_FEATURE_ORDER, segment_calibrators)
    
    # Overfitting detection (use final train/test split from CV)
    # CV indices is a list of dicts, not a dict
    # Use the last fold as representative
    if isinstance(cv_indices, list):
        last_fold = cv_indices[-1]
        test_indices = np.array(last_fold["test_indices"])
    else:
        last_fold_name = sorted(cv_indices.keys())[-1]
        test_indices = np.array(cv_indices[last_fold_name])
    all_indices = set(range(len(df)))
    train_indices = sorted(list(all_indices - set(test_indices)))
    
    train_metrics = calculate_performance_metrics(
        y[train_indices], y_pred[train_indices], y_proba[train_indices]
    )
    test_metrics = calculate_performance_metrics(
        y[test_indices], y_pred[test_indices], y_proba[test_indices]
    )
    overfitting_results = detect_overfitting(train_metrics, test_metrics)
    
    # CV consistency
    cv_consistency = analyze_cv_consistency(cv_indices, df, model_v4, OFFICIAL_FEATURE_ORDER, segment_calibrators)
    
    # Business impact metrics
    print(f"[7/7] Calculating business impact metrics...", flush=True)
    business_impact_df = calculate_business_impact_metrics(df, y_proba)
    print(f"   Calculated metrics for {len(business_impact_df)} thresholds", flush=True)
    
    # Generate all reports
    generate_reports(
        temporal_results, overfitting_results, cv_consistency,
        business_impact_df, df, y_proba, y
    )
    
    print()
    print("=" * 80)
    print("Unit 6: Backtesting and Performance Validation - COMPLETE")
    print("=" * 80)
    print()
    print("Generated Reports:")
    print(f"  - {BACKTESTING_REPORT_V4_PATH.name}")
    print(f"  - {PERFORMANCE_VALIDATION_REPORT_V4_PATH.name}")
    print(f"  - {OVERFITTING_ANALYSIS_V4_PATH.name}")
    print(f"  - {BUSINESS_IMPACT_METRICS_V4_PATH.name}")
    print(f"  - {CV_CONSISTENCY_REPORT_V4_PATH.name}")
    print()


if __name__ == "__main__":
    main()

