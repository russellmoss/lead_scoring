"""
Week 4: Feature Selection and Model Training
Reads from BigQuery, applies pre-filters, tests imbalance strategies, trains final models
"""
import json
import os
import math
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, 
    roc_auc_score, 
    precision_recall_curve,
    precision_score,
    recall_score,
    f1_score
)
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

from google.cloud import bigquery
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
import joblib

# Paths
ARTIFACTS_DIR = Path(os.getcwd())
CONFIG_PATH = ARTIFACTS_DIR / "config" / "v1_model_config.json"
FEATURE_SCHEMA_PATH = ARTIFACTS_DIR / "config" / "v1_feature_schema.json"
BQ_TABLE = "savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset"
PROJECT_ID = "savvy-gtm-analytics"

print(f"[1/12] Loading configuration and feature schema...", flush=True)


def load_config() -> Dict[str, Any]:
    """Load model configuration"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_feature_schema() -> Dict[str, Any]:
    """Load feature schema"""
    with open(FEATURE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data_from_bigquery() -> pd.DataFrame:
    """Load training data from BigQuery"""
    print(f"[2/12] Loading data from BigQuery table: {BQ_TABLE}...", flush=True)
    
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{BQ_TABLE}`'
    
    df = client.query(query).to_dataframe()
    print(f"   Loaded {len(df):,} rows, {len(df.columns)} columns", flush=True)
    
    return df


def validate_against_schema(df: pd.DataFrame, schema: Dict[str, Any]) -> List[str]:
    """Validate dataframe against feature schema"""
    issues = []
    feature_names = {f["name"] for f in schema.get("features", [])}
    
    # Add temporal features
    feature_names.add("Day_of_Contact")
    feature_names.add("Is_Weekend_Contact")
    
    # Exclusions
    exclusions = set(schema.get("exclusions", []))
    
    # Check for missing features
    missing = [f for f in feature_names if f not in df.columns and f not in exclusions]
    if missing:
        issues.append(f"Missing features: {missing}")
    
    return issues


def get_feature_columns(df: pd.DataFrame, schema: Dict[str, Any]) -> List[str]:
    """Get list of feature columns from schema"""
    exclusions = set(schema.get("exclusions", []))
    base_features = [
        f["name"] for f in schema.get("features", []) 
        if f["name"] in df.columns and f["name"] not in exclusions
    ]
    
    # Add temporal features (should already be in table)
    temporal_features = ["Day_of_Contact", "Is_Weekend_Contact"]
    for tf in temporal_features:
        if tf in df.columns and tf not in base_features:
            base_features.append(tf)
    
    # Remove metadata columns
    drop_cols = {
        "Id", "FA_CRD__c", "Stage_Entered_Contacting__c", 
        "Stage_Entered_Call_Scheduled__c", "target_label",
        "is_eligible_for_mutable_features", "is_in_right_censored_window",
        "days_to_conversion"
    }
    
    features = [c for c in base_features if c not in drop_cols]
    return sorted(list(dict.fromkeys(features)))  # Preserve order, remove duplicates


def cast_categoricals_inplace(df: pd.DataFrame, columns: List[str]) -> None:
    """Cast object dtype columns to category for XGBoost"""
    for c in columns:
        if c in df.columns and df[c].dtype == "object":
            df[c] = df[c].astype("category")


def compute_information_value(x: pd.Series, y: pd.Series, bins: int = 10) -> float:
    """Calculate Information Value (IV) for a feature"""
    try:
        # Remove NaN values
        mask = x.notna() & y.notna()
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < bins or x_clean.nunique() < 2:
            return 0.0
        
        # Create bins
        try:
            s = pd.qcut(
                x_clean.rank(method="first"), 
                q=min(bins, len(x_clean)), 
                duplicates="drop"
            )
        except ValueError:
            # Fallback to uniform bins if quantile fails
            s = pd.cut(x_clean, bins=min(bins, x_clean.nunique()), duplicates="drop")
        
        iv = 0.0
        total_event = (y_clean == 1).sum()
        total_non_event = (y_clean == 0).sum()
        
        if total_event == 0 or total_non_event == 0:
            return 0.0
        
        for b in s.cat.categories if hasattr(s, 'cat') else s.unique():
            if pd.isna(b):
                continue
            mask_bin = (s == b) if hasattr(s, 'cat') else (s == b)
            event = ((y_clean == 1) & mask_bin).sum()
            non_event = ((y_clean == 0) & mask_bin).sum()
            
            pe = event / total_event if total_event > 0 else 0
            pne = non_event / total_non_event if total_non_event > 0 else 0
            
            if pe > 0 and pne > 0:
                iv += (pe - pne) * math.log(pe / pne)
        
        return iv
    except Exception as e:
        return 0.0


def compute_vif(df: pd.DataFrame, continuous_cols: List[str]) -> Dict[str, float]:
    """
    Calculate Variance Inflation Factor (VIF) for continuous features.
    Uses statsmodels if available, otherwise falls back to correlation-based approximation.
    """
    vif_scores = {}
    
    # Try to import statsmodels, fallback to correlation if not available
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        use_statsmodels = True
    except ImportError:
        use_statsmodels = False
    
    # Remove columns with constant values or too many NaN
    valid_cols = []
    for col in continuous_cols:
        if col not in df.columns:
            continue
        col_data = df[col].dropna()
        if len(col_data) < 10 or col_data.nunique() < 2:
            continue
        valid_cols.append(col)
    
    if len(valid_cols) < 2:
        return {col: 1.0 for col in continuous_cols}
    
    # Prepare data for VIF (remove NaN)
    # Convert to float to avoid dtype issues when filling NaN
    vif_data = df[valid_cols].copy()
    for col in valid_cols:
        if vif_data[col].dtype.name.startswith('Int') or vif_data[col].dtype.name.startswith('int'):
            vif_data[col] = vif_data[col].astype(float)
    
    # Fill NaN with median
    medians = vif_data.median()
    vif_data = vif_data.fillna(medians)
    
    if use_statsmodels:
        try:
            for i, col in enumerate(valid_cols):
                try:
                    vif_value = variance_inflation_factor(vif_data.values, i)
                    if not np.isnan(vif_value) and np.isfinite(vif_value):
                        vif_scores[col] = float(vif_value)
                    else:
                        vif_scores[col] = 1.0
                except Exception:
                    vif_scores[col] = 1.0
        except Exception:
            use_statsmodels = False  # Fall through to correlation method
    
    if not use_statsmodels:
        # Fallback: use correlation-based approximation
        corr = vif_data.corr().abs()
        for col in valid_cols:
            if col in corr.columns:
                max_corr = corr[col].drop(col).max()
                vif_scores[col] = 1.0 / (1.0 - max_corr**2) if max_corr < 0.99 else 100.0
            else:
                vif_scores[col] = 1.0
    
    # Set default for columns not calculated
    for col in continuous_cols:
        if col not in vif_scores:
            vif_scores[col] = 1.0
    
    return vif_scores


def apply_prefilters(
    train_df: pd.DataFrame, 
    feature_cols: List[str], 
    y_col: str = "target_label",
    iv_threshold: float = 0.02,
    vif_threshold: float = 10.0
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Apply IV and VIF pre-filters to features.
    Returns: (kept_features, filter_report)
    """
    filter_report = {
        "iv_scores": {},
        "vif_scores": {},
        "removed_iv": [],
        "removed_vif": []
    }
    
    # Step 1: IV Filter (for all features)
    iv_scores = {}
    for col in feature_cols:
        if col not in train_df.columns:
            continue
        
        # Skip if all NaN
        if train_df[col].isna().all():
            iv_scores[col] = 0.0
            continue
        
        if pd.api.types.is_numeric_dtype(train_df[col]):
            iv_scores[col] = compute_information_value(train_df[col], train_df[y_col])
        else:
            # For categorical features, assign default IV (will keep them for tree models)
            # Or calculate IV differently for categorical
            iv_scores[col] = 0.05  # Default for categorical (above threshold)
    
    filter_report["iv_scores"] = {k: float(v) for k, v in iv_scores.items()}
    kept_iv = [c for c, v in iv_scores.items() if v >= iv_threshold]
    removed_iv = [c for c in feature_cols if c not in kept_iv]
    filter_report["removed_iv"] = removed_iv
    
    # Step 2: VIF Filter (only on continuous features)
    continuous_cols = [
        c for c in kept_iv 
        if pd.api.types.is_numeric_dtype(train_df[c]) and train_df[c].notna().sum() > 10
    ]
    
    if len(continuous_cols) > 1:
        vif_scores = compute_vif(train_df, continuous_cols)
        filter_report["vif_scores"] = {k: float(v) for k, v in vif_scores.items()}
        
        removed_vif = [c for c, v in vif_scores.items() if v > vif_threshold]
        filter_report["removed_vif"] = removed_vif
        kept_after_vif = [c for c in kept_iv if c not in removed_vif]
    else:
        kept_after_vif = kept_iv
        filter_report["vif_scores"] = {}
    
    return sorted(kept_after_vif), filter_report


def blocked_time_series_folds(
    df: pd.DataFrame, 
    n_folds: int, 
    gap_days: int, 
    time_col: str, 
    seed: int
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Create blocked time-series cross-validation folds with gap.
    Returns: List of (train_indices, test_indices) tuples
    """
    # Sort by time
    df_sorted = df.sort_values(time_col).reset_index(drop=True)
    df_sorted[time_col] = pd.to_datetime(df_sorted[time_col])
    
    n = len(df_sorted)
    fold_size = n // n_folds
    
    folds = []
    for fold_id in range(n_folds):
        # Test set: last fold_size samples
        test_start_idx = n - (n_folds - fold_id) * fold_size
        test_end_idx = n - (n_folds - fold_id - 1) * fold_size
        
        test_indices = np.arange(test_start_idx, min(test_end_idx, n))
        
        # Train set: all samples before test_start - gap_days
        if len(test_indices) > 0:
            test_start_time = df_sorted.loc[test_indices[0], time_col]
            gap_cutoff = test_start_time - pd.Timedelta(days=gap_days)
            train_mask = df_sorted[time_col] < gap_cutoff
            train_indices = np.array(df_sorted[train_mask].index)
        else:
            train_indices = np.array([])
        
        if len(train_indices) > 0 and len(test_indices) > 0:
            folds.append((train_indices, test_indices))
    
    return folds


def evaluate_imbalance_strategy(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_valid: pd.DataFrame,
    y_valid: pd.Series,
    strategy: str,
    seed: int
) -> Dict[str, Any]:
    """
    Evaluate an imbalance handling strategy (SMOTE or scale_pos_weight)
    Returns: metrics dict
    """
    if strategy == "smote":
        if len(X_train) < 2 or y_train.nunique() < 2:
            return {
                "strategy": "smote",
                "aucpr": 0.0,
                "aucroc": 0.0,
                "model": None
            }
        
        try:
            sampler = SMOTE(random_state=seed, k_neighbors=min(5, (y_train == 1).sum() - 1))
            X_res, y_res = sampler.fit_resample(X_train, y_train)
        except Exception:
            # SMOTE failed, fall back to scale_pos_weight
            pos = (y_train == 1).sum()
            neg = (y_train == 0).sum()
            spw = max(neg / max(pos, 1), 1.0)
            
            model = XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=seed,
                scale_pos_weight=spw,
                eval_metric="logloss",
                tree_method="hist",
                enable_categorical=True,
                objective="binary:logistic"
            )
            model.fit(X_train, y_train)
            
            preds = model.predict_proba(X_valid)[:, 1]
            return {
                "strategy": "smote_fallback_spw",
                "aucpr": float(average_precision_score(y_valid, preds)),
                "aucroc": float(roc_auc_score(y_valid, preds)),
                "model": model
            }
        
        model = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic"
        )
        model.fit(X_res, y_res)
        
    else:  # scale_pos_weight
        pos = (y_train == 1).sum()
        neg = (y_train == 0).sum()
        spw = max(neg / max(pos, 1), 1.0)
        
        model = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            scale_pos_weight=spw,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic"
        )
        model.fit(X_train, y_train)
    
    preds = model.predict_proba(X_valid)[:, 1]
    
    return {
        "strategy": strategy,
        "aucpr": float(average_precision_score(y_valid, preds)),
        "aucroc": float(roc_auc_score(y_valid, preds)),
        "model": model
    }


def train_baseline_logistic(
    X: pd.DataFrame,
    y: pd.Series,
    seed: int
) -> LogisticRegression:
    """Train baseline Logistic Regression with imputation"""
    print(f"   Preparing data for LogisticRegression...", flush=True)
    
    # Separate numeric and categorical
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()
    
    print(f"   Numeric columns: {len(numeric_cols)}, Categorical: {len(categorical_cols)}", flush=True)
    
    # For categorical, use label encoding instead of one-hot to save memory
    X_encoded = X.copy()
    from sklearn.preprocessing import LabelEncoder
    
    # Convert categorical dtype back to object/string first (XGBoost may have converted them)
    for col in categorical_cols:
        if col in X_encoded.columns:
            if pd.api.types.is_categorical_dtype(X_encoded[col]):
                X_encoded[col] = X_encoded[col].astype(str)
    
    # Label encode categoricals (more memory efficient than one-hot)
    for col in categorical_cols:
        if col in X_encoded.columns:
            le = LabelEncoder()
            # Fill NaN and convert to string
            X_encoded[col] = X_encoded[col].astype(str).replace('nan', 'MISSING').fillna('MISSING')
            try:
                X_encoded[col] = le.fit_transform(X_encoded[col])
            except Exception:
                # If encoding fails, drop the column
                X_encoded = X_encoded.drop(columns=[col])
                print(f"   Warning: Dropped categorical column {col} (encoding failed)", flush=True)
    
    # Fill numeric NaN with median
    for col in numeric_cols:
        if col in X_encoded.columns and X_encoded[col].isna().any():
            median_val = X_encoded[col].median()
            X_encoded[col] = X_encoded[col].fillna(median_val if not pd.isna(median_val) else 0.0)
    
    # Convert to numpy array for sklearn
    X_imputed = X_encoded.values.astype(np.float32)  # Use float32 to save memory
    
    print(f"   Training LogisticRegression...", flush=True)
    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
        solver="lbfgs"  # More memory efficient solver
    )
    model.fit(X_imputed, y)
    
    print(f"   Baseline model trained successfully", flush=True)
    return model


def generate_shap_importance(
    model: XGBClassifier,
    X: pd.DataFrame,
    feature_names: List[str],
    n_samples: int = 500
) -> pd.DataFrame:
    """
    Generate SHAP-based feature importance.
    Uses permutation-based approach if TreeExplainer fails.
    """
    try:
        import shap
        print(f"[10/12] Computing SHAP values using TreeExplainer...", flush=True)
        
        # Sample for faster computation
        if len(X) > n_samples:
            sample_idx = np.random.RandomState(42).choice(len(X), n_samples, replace=False)
            X_sample = X.iloc[sample_idx]
        else:
            X_sample = X
        
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)
        
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # Binary classification returns list
        
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        
        importance_df = pd.DataFrame({
            "feature": feature_names,
            "mean_abs_shap": mean_abs_shap
        }).sort_values("mean_abs_shap", ascending=False)
        
        return importance_df
        
    except Exception as e:
        print(f"   TreeExplainer failed: {e}, using permutation-based SHAP...", flush=True)
        
        # Fallback: Permutation-based SHAP
        baseline_pred = model.predict_proba(X)[:, 1]
        baseline_mean = baseline_pred.mean()
        
        shap_values = np.zeros((len(X), len(feature_names)))
        
        for i, feat in enumerate(feature_names):
            if i % 20 == 0:
                print(f"   Feature {i+1}/{len(feature_names)}: {feat}", flush=True)
            
            X_permuted = X.copy()
            perm_indices = np.random.RandomState(42 + i).permutation(len(X))
            X_permuted[feat] = X_permuted[feat].iloc[perm_indices].values
            
            perm_pred = model.predict_proba(X_permuted)[:, 1]
            shap_values[:, i] = baseline_pred - perm_pred
        
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        
        importance_df = pd.DataFrame({
            "feature": feature_names,
            "mean_abs_shap": mean_abs_shap
        }).sort_values("mean_abs_shap", ascending=False)
        
        return importance_df


def main():
    """Main training pipeline"""
    print("=" * 80)
    print("Week 4: Feature Selection and Model Training")
    print("=" * 80)
    print()
    
    # Load configs
    cfg = load_config()
    schema = load_feature_schema()
    seed = int(cfg.get("global_seed", 42))
    gap_days = int(cfg.get("cv_gap_days", 30))
    cv_folds = int(cfg.get("cv_folds", 5))
    
    print(f"Configuration loaded:")
    print(f"  - Global seed: {seed}")
    print(f"  - CV folds: {cv_folds}")
    print(f"  - Gap days: {gap_days}")
    print()
    
    # Load data from BigQuery
    df = load_data_from_bigquery()
    
    # Verify temporal features exist
    if "Day_of_Contact" not in df.columns or "Is_Weekend_Contact" not in df.columns:
        print("WARNING: Temporal features missing, deriving from Stage_Entered_Contacting__c...", flush=True)
        ts = pd.to_datetime(df["Stage_Entered_Contacting__c"], errors="coerce", utc=True)
        df["Day_of_Contact"] = ts.dt.dayofweek + 1  # 1=Monday, 7=Sunday
        df["Is_Weekend_Contact"] = df["Day_of_Contact"].isin([6, 7]).astype(int)
    
    # Validate schema
    print(f"[3/12] Validating data against feature schema...", flush=True)
    issues = validate_against_schema(df, schema)
    if issues:
        print(f"WARNING: Schema validation issues: {issues}", flush=True)
        # Continue anyway, but log warnings
    
    # Ensure binary labels
    if "target_label" not in df.columns:
        raise ValueError("target_label column not found in dataset")
    
    df = df[df["target_label"].isin([0, 1])].copy()
    print(f"   Dataset: {len(df):,} rows after filtering", flush=True)
    
    # Get feature columns
    feature_cols = get_feature_columns(df, schema)
    print(f"   Total features available: {len(feature_cols)}", flush=True)
    
    # Cast categoricals
    print(f"[4/12] Preparing data types...", flush=True)
    cast_categoricals_inplace(df, feature_cols)
    
    # Set up time column and target
    time_col = "Stage_Entered_Contacting__c"
    y_col = "target_label"
    
    # Create CV folds
    print(f"[5/12] Creating blocked time-series CV folds (n_folds={cv_folds}, gap={gap_days} days)...", flush=True)
    folds = blocked_time_series_folds(df, n_folds=cv_folds, gap_days=gap_days, time_col=time_col, seed=seed)
    print(f"   Created {len(folds)} folds", flush=True)
    
    # Store CV fold indices
    cv_indices = []
    all_filter_reports = []
    cv_metrics = []
    
    # Cross-validation loop with pre-filtering and strategy testing
    print(f"[6/12] Running cross-validation with pre-filtering and strategy testing...", flush=True)
    
    for fold_id, (train_idx, test_idx) in enumerate(folds):
        print(f"   Fold {fold_id + 1}/{len(folds)}: train={len(train_idx):,}, test={len(test_idx):,}", flush=True)
        
        train_df = df.iloc[train_idx].reset_index(drop=True).copy()
        test_df = df.iloc[test_idx].reset_index(drop=True).copy()
        
        if len(train_df) == 0 or len(test_df) == 0:
            print(f"      Skipping fold (empty train/test)", flush=True)
            continue
        
        # Apply pre-filters on training data only
        kept_features, filter_report = apply_prefilters(train_df, feature_cols, y_col)
        filter_report["fold"] = fold_id
        filter_report["kept_count"] = len(kept_features)
        all_filter_reports.append(filter_report)
        
        print(f"      Pre-filters: kept {len(kept_features)}/{len(feature_cols)} features", flush=True)
        
        # Prepare data
        X_train = train_df[kept_features].copy()
        y_train = train_df[y_col].astype(int)
        X_valid = test_df[kept_features].copy()
        y_valid = test_df[y_col].astype(int)
        
        # Ensure categoricals
        cast_categoricals_inplace(X_train, kept_features)
        cast_categoricals_inplace(X_valid, kept_features)
        
        if y_train.nunique() < 2:
            print(f"      Skipping fold (single class in training)", flush=True)
            continue
        
        # Test both strategies
        print(f"      Testing SMOTE...", flush=True)
        res_smote = evaluate_imbalance_strategy(X_train, y_train, X_valid, y_valid, "smote", seed)
        
        print(f"      Testing scale_pos_weight...", flush=True)
        res_spw = evaluate_imbalance_strategy(X_train, y_train, X_valid, y_valid, "scale_pos_weight", seed)
        
        # Determine best strategy for this fold
        best_strategy = "smote" if res_smote["aucpr"] > res_spw["aucpr"] else "spw"
        best_aucpr = max(res_smote["aucpr"], res_spw["aucpr"])
        
        cv_metrics.append({
            "fold": fold_id,
            "train_size": len(train_idx),
            "test_size": len(test_idx),
            "features_kept": len(kept_features),
            "smote_aucpr": res_smote["aucpr"],
            "spw_aucpr": res_spw["aucpr"],
            "best_strategy": best_strategy,
            "best_aucpr": best_aucpr
        })
        
        print(f"      Best: {best_strategy} (AUC-PR: {best_aucpr:.4f})", flush=True)
        
        cv_indices.append({
            "fold": fold_id,
            "train_indices": train_idx.tolist(),
            "test_indices": test_idx.tolist()
        })
    
    # Determine winning strategy (majority vote across folds)
    spw_wins = sum(1 for m in cv_metrics if m["best_strategy"] == "spw")
    smote_wins = len(cv_metrics) - spw_wins
    winning_strategy = "spw" if spw_wins >= smote_wins else "smote"
    
    print()
    print(f"[7/12] Winning strategy: {winning_strategy} (wins: spw={spw_wins}, smote={smote_wins})", flush=True)
    
    # Apply pre-filters on full dataset
    print(f"[8/12] Applying pre-filters on full dataset...", flush=True)
    final_kept_features, final_filter_report = apply_prefilters(df, feature_cols, y_col)
    print(f"   Final features: {len(final_kept_features)}/{len(feature_cols)}", flush=True)
    
    # Prepare final training data
    X_all = df[final_kept_features].copy()
    y_all = df[y_col].astype(int)
    cast_categoricals_inplace(X_all, final_kept_features)
    
    # Train final XGBoost model
    print(f"[9/12] Training final XGBoost model with {winning_strategy}...", flush=True)
    
    if winning_strategy == "smote":
        try:
            sampler = SMOTE(random_state=seed, k_neighbors=min(5, (y_all == 1).sum() - 1))
            X_res, y_res = sampler.fit_resample(X_all, y_all)
            print(f"   SMOTE resampled: {len(X_res):,} samples", flush=True)
            
            final_model = XGBClassifier(
                n_estimators=400,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=seed,
                eval_metric="logloss",
                tree_method="hist",
                enable_categorical=True,
                objective="binary:logistic"
            )
            final_model.fit(X_res, y_res)
        except Exception as e:
            print(f"   SMOTE failed ({e}), using scale_pos_weight instead", flush=True)
            winning_strategy = "spw"
            pos = (y_all == 1).sum()
            neg = (y_all == 0).sum()
            spw = max(neg / max(pos, 1), 1.0)
            final_model = XGBClassifier(
                n_estimators=400,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=seed,
                scale_pos_weight=spw,
                eval_metric="logloss",
                tree_method="hist",
                enable_categorical=True,
                objective="binary:logistic"
            )
            final_model.fit(X_all, y_all)
    else:  # scale_pos_weight
        pos = (y_all == 1).sum()
        neg = (y_all == 0).sum()
        spw = max(neg / max(pos, 1), 1.0)
        print(f"   scale_pos_weight: {spw:.2f}", flush=True)
        
        final_model = XGBClassifier(
            n_estimators=400,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            scale_pos_weight=spw,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic"
        )
        final_model.fit(X_all, y_all)
    
    # Verify NULL handling
    print(f"   Verifying NULL value handling...", flush=True)
    preds_sample = final_model.predict_proba(X_all.head(100))[:, 1]
    print(f"   Predictions generated successfully (sample mean: {preds_sample.mean():.4f})", flush=True)
    
    # Train baseline Logistic Regression
    print(f"[10/12] Training baseline Logistic Regression model...", flush=True)
    baseline_model = train_baseline_logistic(X_all, y_all, seed)
    
    # Save models
    print(f"[11/12] Saving models and artifacts...", flush=True)
    joblib.dump(final_model, ARTIFACTS_DIR / "model_v1.pkl")
    joblib.dump(baseline_model, ARTIFACTS_DIR / "model_v1_baseline_logit.pkl")
    
    # Save CV fold indices
    with open(ARTIFACTS_DIR / "cv_fold_indices_v1.json", "w", encoding="utf-8") as f:
        json.dump(cv_indices, f, indent=2)
    
    # Save selected features
    with open(ARTIFACTS_DIR / "selected_features_v1.json", "w", encoding="utf-8") as f:
        json.dump(final_kept_features, f, indent=2)
    
    # Generate feature importance
    print(f"[12/12] Generating feature importance...", flush=True)
    importance_df = generate_shap_importance(final_model, X_all, final_kept_features)
    importance_df.to_csv(ARTIFACTS_DIR / "feature_importance_v1.csv", index=False)
    
    # Evaluate final model performance
    print(f"   Evaluating final model...", flush=True)
    final_preds = final_model.predict_proba(X_all)[:, 1]
    final_aucpr = average_precision_score(y_all, final_preds)
    final_aucroc = roc_auc_score(y_all, final_preds)
    
    # Prepare X_all for baseline prediction (same encoding as training)
    X_baseline = X_all.copy()
    numeric_cols = X_baseline.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X_baseline.select_dtypes(exclude=[np.number]).columns.tolist()
    
    from sklearn.preprocessing import LabelEncoder
    
    # Convert categorical dtype back to object/string first
    for col in categorical_cols:
        if col in X_baseline.columns:
            if pd.api.types.is_categorical_dtype(X_baseline[col]):
                X_baseline[col] = X_baseline[col].astype(str)
    
    # Label encode categoricals (matching training)
    for col in categorical_cols:
        if col in X_baseline.columns:
            le = LabelEncoder()
            X_baseline[col] = X_baseline[col].astype(str).replace('nan', 'MISSING').fillna('MISSING')
            try:
                X_baseline[col] = le.fit_transform(X_baseline[col])
            except Exception:
                X_baseline = X_baseline.drop(columns=[col])
    
    # Fill numeric NaN with median
    for col in numeric_cols:
        if col in X_baseline.columns and X_baseline[col].isna().any():
            median_val = X_baseline[col].median()
            X_baseline[col] = X_baseline[col].fillna(median_val if not pd.isna(median_val) else 0.0)
    
    X_baseline_imputed = X_baseline.values.astype(np.float32)
    baseline_preds = baseline_model.predict_proba(X_baseline_imputed)[:, 1]
    baseline_aucpr = average_precision_score(y_all, baseline_preds)
    baseline_aucroc = roc_auc_score(y_all, baseline_preds)
    
    # Generate reports
    print(f"   Generating reports...", flush=True)
    
    # Feature selection report
    with open(ARTIFACTS_DIR / "feature_selection_report_v1.md", "w", encoding="utf-8") as f:
        f.write("# Feature Selection Report V1\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Pre-Filter Summary\n\n")
        f.write(f"- **Initial Features:** {len(feature_cols)}\n")
        f.write(f"- **Final Features:** {len(final_kept_features)}\n")
        f.write(f"- **Removed:** {len(feature_cols) - len(final_kept_features)}\n\n")
        f.write("## Features Removed by Filter\n\n")
        
        # Aggregate removed features across folds
        all_removed_iv = set()
        all_removed_vif = set()
        for report in all_filter_reports:
            all_removed_iv.update(report.get("removed_iv", []))
            all_removed_vif.update(report.get("removed_vif", []))
        
        f.write("### Removed by IV Filter (< 0.02)\n\n")
        for feat in sorted(all_removed_iv):
            f.write(f"- {feat}\n")
        
        f.write("\n### Removed by VIF Filter (> 10.0)\n\n")
        for feat in sorted(all_removed_vif):
            f.write(f"- {feat}\n")
        
        f.write("\n## Feature Importance (Top 20)\n\n")
        f.write(importance_df.head(20).to_markdown(index=False))
    
    # Model training report
    with open(ARTIFACTS_DIR / "model_training_report_v1.md", "w", encoding="utf-8") as f:
        f.write("# Model Training Report V1\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Winning Imbalance Strategy:** {winning_strategy}\n")
        f.write(f"- **Final Features Used:** {len(final_kept_features)}\n")
        f.write(f"- **Training Samples:** {len(X_all):,}\n")
        f.write(f"- **Positive Samples:** {(y_all == 1).sum():,} ({(y_all == 1).mean()*100:.2f}%)\n")
        f.write(f"- **Negative Samples:** {(y_all == 0).sum():,} ({(y_all == 0).mean()*100:.2f}%)\n\n")
        
        f.write("## Final Model Performance\n\n")
        f.write("### XGBoost (Final Model)\n\n")
        f.write(f"- **AUC-PR:** {final_aucpr:.4f}\n")
        f.write(f"- **AUC-ROC:** {final_aucroc:.4f}\n\n")
        
        f.write("### Logistic Regression (Baseline)\n\n")
        f.write(f"- **AUC-PR:** {baseline_aucpr:.4f}\n")
        f.write(f"- **AUC-ROC:** {baseline_aucroc:.4f}\n\n")
        
        f.write("## Cross-Validation Results\n\n")
        f.write("### Strategy Comparison by Fold\n\n")
        cv_df = pd.DataFrame(cv_metrics)
        f.write(cv_df.to_markdown(index=False))
        
        f.write("\n\n## SMOTE vs Scale_Pos_Weight Analysis\n\n")
        avg_smote = cv_df["smote_aucpr"].mean()
        avg_spw = cv_df["spw_aucpr"].mean()
        f.write(f"- **Average SMOTE AUC-PR:** {avg_smote:.4f}\n")
        f.write(f"- **Average Scale_Pos_Weight AUC-PR:** {avg_spw:.4f}\n")
        f.write(f"- **Winning Strategy:** {winning_strategy} ({'SMOTE' if avg_smote > avg_spw else 'Scale_Pos_Weight'})\n")
    
    print()
    print("=" * 80)
    print("Week 4 Training Complete!")
    print("=" * 80)
    print()
    print("Artifacts created:")
    print(f"  ✓ model_v1.pkl")
    print(f"  ✓ model_v1_baseline_logit.pkl")
    print(f"  ✓ cv_fold_indices_v1.json")
    print(f"  ✓ feature_importance_v1.csv")
    print(f"  ✓ feature_selection_report_v1.md")
    print(f"  ✓ model_training_report_v1.md")
    print(f"  ✓ selected_features_v1.json")
    print()
    print(f"Final Model Performance:")
    print(f"  XGBoost AUC-PR: {final_aucpr:.4f}")
    print(f"  Baseline AUC-PR: {baseline_aucpr:.4f}")
    print(f"  Improvement: {((final_aucpr - baseline_aucpr) / baseline_aucpr * 100):.1f}%")
    print()


if __name__ == "__main__":
    main()

