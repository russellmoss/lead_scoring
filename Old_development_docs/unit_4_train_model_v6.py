"""
Unit 4 V6: Model Training (Streamlined - Features Already Engineered)
Reads from BigQuery v_latest_training_dataset_v6, drops PII, trains XGBoost model.
V6: Uses V5-style regularization, all features already engineered in SQL.
"""
import json
import os
from datetime import datetime
from typing import List, Tuple, Dict, Any
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
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

from google.cloud import bigquery
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
import joblib

# Paths
ARTIFACTS_DIR = Path(os.getcwd())
CONFIG_PATH = ARTIFACTS_DIR / "config" / "v1_model_config.json"
PII_DROPLIST_PATH = ARTIFACTS_DIR / "config" / "v6_pii_droplist.json"
BQ_VIEW = "savvy-gtm-analytics.LeadScoring.v_latest_training_dataset_v6"
PROJECT_ID = "savvy-gtm-analytics"

# Version string
VERSION = datetime.now().strftime("%Y%m%d")

print("=" * 80)
print("Unit 4 V6: Model Training (Streamlined - Features Already Engineered)")
print("=" * 80)
print()


def load_config() -> Dict[str, Any]:
    """Load model configuration"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_pii_droplist() -> List[str]:
    """Load PII drop list"""
    with open(PII_DROPLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data_from_bigquery() -> pd.DataFrame:
    """Load training data from BigQuery view"""
    print(f"[1/10] Loading data from BigQuery view: {BQ_VIEW}...", flush=True)
    
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{BQ_VIEW}`'
    
    df = client.query(query).to_dataframe()
    print(f"   Loaded {len(df):,} rows, {len(df.columns)} columns", flush=True)
    
    return df


def drop_pii_features(df: pd.DataFrame, pii_droplist: List[str]) -> pd.DataFrame:
    """Drop PII features from dataframe"""
    print(f"[2/10] Dropping PII features...", flush=True)
    
    pii_cols_to_drop = [col for col in pii_droplist if col in df.columns]
    if pii_cols_to_drop:
        df = df.drop(columns=pii_cols_to_drop)
        print(f"   Dropped {len(pii_cols_to_drop)} PII features: {', '.join(pii_cols_to_drop[:10])}{'...' if len(pii_cols_to_drop) > 10 else ''}", flush=True)
    else:
        print(f"   Warning: No PII features found to drop", flush=True)
    
    # Assert all PII features are dropped
    remaining_pii = [col for col in pii_droplist if col in df.columns]
    if remaining_pii:
        raise ValueError(f"PII features still present after drop: {remaining_pii}")
    
    print(f"   PII drop assertion passed", flush=True)
    return df


def cast_categoricals_inplace(df: pd.DataFrame, columns: List[str]) -> None:
    """Cast object dtype columns to category for XGBoost"""
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
                
                cat_categories = df[c].cat.categories
                if len(cat_categories) == 0:
                    df[c] = df[c].cat.add_categories(["__MISSING__"])
                    df[c] = df[c].fillna("__MISSING__")
            except Exception as e:
                try:
                    df[c] = df[c].fillna("__MISSING__").astype("category")
                    if "__MISSING__" not in df[c].cat.categories:
                        df[c] = df[c].cat.add_categories(["__MISSING__"])
                except Exception:
                    df[c] = df[c].astype(str).fillna("__MISSING__").astype("category")


def blocked_time_series_folds(
    df: pd.DataFrame, 
    n_folds: int, 
    gap_days: int, 
    time_col: str, 
    seed: int
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Create blocked time-series cross-validation folds with gap"""
    df_sorted = df.sort_values(time_col).reset_index(drop=True)
    df_sorted[time_col] = pd.to_datetime(df_sorted[time_col])
    
    n = len(df_sorted)
    fold_size = n // n_folds
    
    folds = []
    for fold_id in range(n_folds):
        test_start_idx = n - (n_folds - fold_id) * fold_size
        test_end_idx = n - (n_folds - fold_id - 1) * fold_size
        
        test_indices = np.arange(test_start_idx, min(test_end_idx, n))
        
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


def train_baseline_logistic(X: pd.DataFrame, y: pd.Series, seed: int) -> LogisticRegression:
    """Train baseline Logistic Regression"""
    print(f"   Preparing data for LogisticRegression...", flush=True)
    
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()
    
    X_encoded = X.copy()
    
    for col in categorical_cols:
        if col in X_encoded.columns:
            if pd.api.types.is_categorical_dtype(X_encoded[col]):
                X_encoded[col] = X_encoded[col].astype(str)
    
    for col in categorical_cols:
        if col in X_encoded.columns:
            le = LabelEncoder()
            X_encoded[col] = X_encoded[col].astype(str).replace('nan', 'MISSING').fillna('MISSING')
            try:
                X_encoded[col] = le.fit_transform(X_encoded[col])
            except Exception:
                X_encoded = X_encoded.drop(columns=[col])
    
    for col in numeric_cols:
        if col in X_encoded.columns and X_encoded[col].isna().any():
            median_val = X_encoded[col].median()
            X_encoded[col] = X_encoded[col].fillna(median_val if not pd.isna(median_val) else 0.0)
    
    X_imputed = X_encoded.values.astype(np.float32)
    
    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=seed,
        n_jobs=-1,
        solver="lbfgs"
    )
    model.fit(X_imputed, y)
    
    return model


def main():
    """Main training pipeline"""
    # Load configs
    cfg = load_config()
    pii_droplist = load_pii_droplist()
    seed = int(cfg.get("global_seed", 42))
    gap_days = int(cfg.get("cv_gap_days", 30))
    cv_folds = int(cfg.get("cv_folds", 5))
    
    print(f"Configuration:")
    print(f"  - Version: {VERSION}")
    print(f"  - Global seed: {seed}")
    print(f"  - CV folds: {cv_folds}")
    print(f"  - Gap days: {gap_days}")
    print()
    
    # Load data
    df = load_data_from_bigquery()
    
    # Drop PII
    df = drop_pii_features(df, pii_droplist)
    
    # Ensure binary labels
    if "target_label" not in df.columns:
        raise ValueError("target_label column not found in dataset")
    
    df = df[df["target_label"].isin([0, 1])].copy()
    print(f"[3/10] Dataset: {len(df):,} rows after filtering", flush=True)
    
    # Get feature columns (exclude metadata and target)
    metadata_cols = {
        "Id", "FA_CRD__c", "target_label", "Stage_Entered_Contacting__c",
        "Stage_Entered_Call_Scheduled__c", "rep_snapshot_at", "firm_snapshot_at",
        "days_to_conversion"
    }
    feature_cols = [c for c in df.columns if c not in metadata_cols]
    
    print(f"[4/10] Total features: {len(feature_cols)}", flush=True)
    
    # Cast categoricals
    print(f"[5/10] Preparing data types...", flush=True)
    cast_categoricals_inplace(df, feature_cols)
    
    # Set up time column and target
    time_col = "Stage_Entered_Contacting__c"
    y_col = "target_label"
    
    # Create CV folds
    print(f"[6/10] Creating CV folds...", flush=True)
    
    # Try blocked time-series split first
    try:
        if time_col in df.columns:
            folds = blocked_time_series_folds(df, n_folds=cv_folds, gap_days=gap_days, time_col=time_col, seed=seed)
            print(f"   Using BlockedTimeSeriesSplit: {len(folds)} folds", flush=True)
        else:
            raise ValueError("Time column not found, falling back to StratifiedKFold")
    except Exception as e:
        print(f"   BlockedTimeSeriesSplit failed ({e}), using StratifiedKFold", flush=True)
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
        folds = list(skf.split(df[feature_cols], df[y_col]))
    
    # Cross-validation loop
    print(f"[7/10] Running cross-validation...", flush=True)
    
    cv_metrics = []
    X_all = df[feature_cols].copy()
    y_all = df[y_col].astype(int)
    
    for fold_id, (train_idx, test_idx) in enumerate(folds):
        print(f"   Fold {fold_id + 1}/{len(folds)}: train={len(train_idx):,}, test={len(test_idx):,}", flush=True)
        
        X_train = X_all.iloc[train_idx].copy()
        y_train = y_all.iloc[train_idx]
        X_valid = X_all.iloc[test_idx].copy()
        y_valid = y_all.iloc[test_idx]
        
        if y_train.nunique() < 2:
            print(f"      Skipping fold (single class in training)", flush=True)
            continue
        
        # Test both strategies: SMOTE and scale_pos_weight
        pos = (y_train == 1).sum()
        neg = (y_train == 0).sum()
        spw = max(neg / max(pos, 1), 1.0)
        
        # Strategy 1: Try SMOTE (if feasible)
        smote_aucpr = 0.0
        smote_aucroc = 0.0
        smote_success = False
        
        # Check if we have categorical features (SMOTE can't handle them directly)
        has_categorical = any(
            pd.api.types.is_categorical_dtype(X_train[col]) or X_train[col].dtype == 'object'
            for col in X_train.columns
        )
        
        if not has_categorical and pos > 1:
            try:
                print(f"      Testing SMOTE...", flush=True)
                sampler = SMOTE(sampling_strategy=0.1, random_state=seed, k_neighbors=min(5, pos - 1))
                X_res, y_res = sampler.fit_resample(X_train, y_train)
                
                model_smote = XGBClassifier(
                    n_estimators=200,
                    max_depth=4,
                    learning_rate=0.02,
                    subsample=0.7,
                    colsample_bytree=0.7,
                    reg_alpha=1.0,
                    reg_lambda=5.0,
                    random_state=seed,
                    eval_metric="logloss",
                    tree_method="hist",
                    enable_categorical=True,
                    objective="binary:logistic"
                )
                model_smote.fit(X_res, y_res)
                preds_smote = model_smote.predict_proba(X_valid)[:, 1]
                smote_aucpr = float(average_precision_score(y_valid, preds_smote))
                smote_aucroc = float(roc_auc_score(y_valid, preds_smote))
                smote_success = True
                print(f"         SMOTE AUC-PR: {smote_aucpr:.4f}, AUC-ROC: {smote_aucroc:.4f}", flush=True)
            except Exception as e:
                print(f"         SMOTE failed: {e}, using scale_pos_weight", flush=True)
        
        # Strategy 2: scale_pos_weight
        print(f"      Testing scale_pos_weight...", flush=True)
        model_spw = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.02,
            subsample=0.7,
            colsample_bytree=0.7,
            reg_alpha=1.0,
            reg_lambda=5.0,
            random_state=seed,
            scale_pos_weight=spw,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic"
        )
        
        try:
            model_spw.fit(X_train, y_train)
        except (ValueError, TypeError) as e:
            if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
                for col in X_train.columns:
                    if pd.api.types.is_categorical_dtype(X_train[col]):
                        if len(X_train[col].cat.categories) == 0:
                            X_train[col] = X_train[col].astype("object")
                            X_valid[col] = X_valid[col].astype("object")
                model_spw.fit(X_train, y_train)
            else:
                raise
        
        preds_spw = model_spw.predict_proba(X_valid)[:, 1]
        spw_aucpr = float(average_precision_score(y_valid, preds_spw))
        spw_aucroc = float(roc_auc_score(y_valid, preds_spw))
        print(f"         SPW AUC-PR: {spw_aucpr:.4f}, AUC-ROC: {spw_aucroc:.4f}", flush=True)
        
        # Choose best strategy for this fold
        if smote_success and smote_aucpr > spw_aucpr:
            best_strategy = "smote"
            best_aucpr = smote_aucpr
            best_aucroc = smote_aucroc
        else:
            best_strategy = "scale_pos_weight"
            best_aucpr = spw_aucpr
            best_aucroc = spw_aucroc
        
        cv_metrics.append({
            "fold": fold_id,
            "strategy": best_strategy,
            "aucpr": best_aucpr,
            "aucroc": best_aucroc,
            "smote_aucpr": smote_aucpr if smote_success else None,
            "spw_aucpr": spw_aucpr
        })
        
        print(f"      Best: {best_strategy.upper()} - AUC-PR: {best_aucpr:.4f}, AUC-ROC: {best_aucroc:.4f}", flush=True)
    
    # Calculate CV statistics
    cv_aucpr_mean = np.mean([m["aucpr"] for m in cv_metrics])
    cv_aucpr_std = np.std([m["aucpr"] for m in cv_metrics])
    cv_aucpr_cv = (cv_aucpr_std / cv_aucpr_mean * 100) if cv_aucpr_mean > 0 else 0
    
    print(f"\n[8/10] CV Results:")
    print(f"   Mean AUC-PR: {cv_aucpr_mean:.4f} ± {cv_aucpr_std:.4f}")
    print(f"   CV Coefficient: {cv_aucpr_cv:.2f}%")
    
    # Strategy comparison
    smote_wins = sum(1 for m in cv_metrics if m.get("strategy") == "smote")
    spw_wins = sum(1 for m in cv_metrics if m.get("strategy") == "scale_pos_weight")
    print(f"   Strategy wins: SMOTE={smote_wins}, scale_pos_weight={spw_wins}")
    
    # Determine winning strategy from CV
    winning_strategy = "smote" if smote_wins > spw_wins else "scale_pos_weight"
    
    print(f"\n[9/10] Training final model on all data...", flush=True)
    print(f"   Winning strategy from CV: {winning_strategy} ({smote_wins} SMOTE wins, {spw_wins} SPW wins)", flush=True)
    
    pos = (y_all == 1).sum()
    neg = (y_all == 0).sum()
    spw = max(neg / max(pos, 1), 1.0)
    
    # Train final model with winning strategy
    if winning_strategy == "smote":
        # Check if SMOTE is feasible
        has_categorical = any(
            pd.api.types.is_categorical_dtype(X_all[col]) or X_all[col].dtype == 'object'
            for col in X_all.columns
        )
        
        if not has_categorical and pos > 1:
            try:
                print(f"   Using SMOTE for final model...", flush=True)
                sampler = SMOTE(sampling_strategy=0.1, random_state=seed, k_neighbors=min(5, pos - 1))
                X_res, y_res = sampler.fit_resample(X_all, y_all)
                print(f"   Resampled: {len(X_res):,} samples", flush=True)
                
                final_model = XGBClassifier(
                    n_estimators=200,
                    max_depth=4,
                    learning_rate=0.02,
                    subsample=0.7,
                    colsample_bytree=0.7,
                    reg_alpha=1.0,
                    reg_lambda=5.0,
                    random_state=seed,
                    eval_metric="logloss",
                    tree_method="hist",
                    enable_categorical=True,
                    objective="binary:logistic"
                )
                final_model.fit(X_res, y_res)
            except Exception as e:
                print(f"   SMOTE failed for final model ({e}), using scale_pos_weight", flush=True)
                winning_strategy = "scale_pos_weight"
                final_model = XGBClassifier(
                    n_estimators=200,
                    max_depth=4,
                    learning_rate=0.02,
                    subsample=0.7,
                    colsample_bytree=0.7,
                    reg_alpha=1.0,
                    reg_lambda=5.0,
                    random_state=seed,
                    scale_pos_weight=spw,
                    eval_metric="logloss",
                    tree_method="hist",
                    enable_categorical=True,
                    objective="binary:logistic"
                )
                final_model.fit(X_all, y_all)
        else:
            print(f"   SMOTE not feasible (categorical features or insufficient positives), using scale_pos_weight", flush=True)
            winning_strategy = "scale_pos_weight"
            final_model = XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.02,
                subsample=0.7,
                colsample_bytree=0.7,
                reg_alpha=1.0,
                reg_lambda=5.0,
                random_state=seed,
                scale_pos_weight=spw,
                eval_metric="logloss",
                tree_method="hist",
                enable_categorical=True,
                objective="binary:logistic"
            )
            final_model.fit(X_all, y_all)
    else:  # scale_pos_weight
        print(f"   Using scale_pos_weight: {spw:.2f}", flush=True)
        final_model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.02,
            subsample=0.7,
            colsample_bytree=0.7,
            reg_alpha=1.0,
            reg_lambda=5.0,
            random_state=seed,
            scale_pos_weight=spw,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic"
        )
        
        try:
            final_model.fit(X_all, y_all)
        except (ValueError, TypeError) as e:
            if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
                for col in X_all.columns:
                    if pd.api.types.is_categorical_dtype(X_all[col]):
                        if len(X_all[col].cat.categories) == 0:
                            X_all[col] = X_all[col].astype("object")
                final_model.fit(X_all, y_all)
            else:
                raise
    
    # Train baseline
    print(f"[10/10] Training baseline Logistic Regression...", flush=True)
    baseline_model = train_baseline_logistic(X_all, y_all, seed)
    
    # Save models
    print(f"\n[Saving] Models and artifacts...", flush=True)
    
    model_path = ARTIFACTS_DIR / f"model_v6_{VERSION}.pkl"
    baseline_path = ARTIFACTS_DIR / f"model_v6_{VERSION}_baseline_logit.pkl"
    feature_order_path = ARTIFACTS_DIR / f"feature_order_v6_{VERSION}.json"
    importance_path = ARTIFACTS_DIR / f"feature_importance_v6_{VERSION}.csv"
    report_path = ARTIFACTS_DIR / f"model_training_report_v6_{VERSION}.md"
    
    joblib.dump(final_model, model_path)
    joblib.dump(baseline_model, baseline_path)
    
    # Save feature order
    with open(feature_order_path, "w") as f:
        json.dump(feature_cols, f, indent=2)
    
    # Save feature importance
    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": final_model.feature_importances_
    }).sort_values("importance", ascending=False)
    importance_df.to_csv(importance_path, index=False)
    
    # Generate training report
    print(f"\n[Generating] Training report...", flush=True)
    
    report = f"""# V6 Model Training Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Version:** {VERSION}

## Dataset Summary

- **Total Samples:** {len(df):,}
- **Positive Class:** {(y_all == 1).sum():,} ({100*(y_all == 1).sum()/len(y_all):.2f}%)
- **Negative Class:** {(y_all == 0).sum():,} ({100*(y_all == 0).sum()/len(y_all):.2f}%)
- **Features:** {len(feature_cols)}
- **CV Folds:** {cv_folds}

## Cross-Validation Results

- **Mean AUC-PR:** {cv_aucpr_mean:.4f} ± {cv_aucpr_std:.4f}
- **CV Coefficient:** {cv_aucpr_cv:.2f}%
- **Winning Strategy:** {winning_strategy}
- **Strategy Wins:** SMOTE={smote_wins}, scale_pos_weight={spw_wins}
- **Fold Details:**
"""
    
    for m in cv_metrics:
        strategy_info = f" ({m.get('strategy', 'unknown')})"
        if m.get('smote_aucpr') is not None:
            strategy_info += f" [SMOTE={m.get('smote_aucpr', 0):.4f}, SPW={m.get('spw_aucpr', 0):.4f}]"
        report += f"  - Fold {m['fold']+1}{strategy_info}: AUC-PR={m['aucpr']:.4f}, AUC-ROC={m['aucroc']:.4f}\n"
    
    report += f"""
## Model Configuration

- **XGBoost Parameters:**
  - n_estimators: 200
  - max_depth: 4
  - learning_rate: 0.02
  - subsample: 0.7
  - colsample_bytree: 0.7
  - reg_alpha: 1.0
  - reg_lambda: 5.0
  - scale_pos_weight: {spw:.2f} (used if scale_pos_weight strategy)
  - **Imbalance Strategy:** {winning_strategy}

## Top 20 Features

"""
    
    for i, row in importance_df.head(20).iterrows():
        report += f"{row['feature']}: {row['importance']:.6f}\n"
    
    report += f"""
## Artifacts Saved

- Model: `model_v6_{VERSION}.pkl`
- Baseline: `model_v6_{VERSION}_baseline_logit.pkl`
- Feature Order: `feature_order_v6_{VERSION}.json`
- Feature Importance: `feature_importance_v6_{VERSION}.csv`

## Validation Gates

- **CV AUC-PR > 0.15:** {'PASS' if cv_aucpr_mean > 0.15 else 'FAIL'} ({cv_aucpr_mean:.4f})
- **CV Coefficient < 20%:** {'PASS' if cv_aucpr_cv < 20 else 'FAIL'} ({cv_aucpr_cv:.2f}%)
"""
    
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\n[SUCCESS] Training complete!")
    print(f"  - Model: {model_path}")
    print(f"  - Report: {report_path}")
    print(f"  - Feature Importance: {importance_path}")
    
    # Validation gates
    print(f"\n[VALIDATION] Gates:")
    print(f"  - CV AUC-PR > 0.15: {'PASS' if cv_aucpr_mean > 0.15 else 'FAIL'} ({cv_aucpr_mean:.4f})")
    print(f"  - CV Coefficient < 20%: {'PASS' if cv_aucpr_cv < 20 else 'FAIL'} ({cv_aucpr_cv:.2f}%)")
    
    if cv_aucpr_mean <= 0.15 or cv_aucpr_cv >= 20:
        print(f"\n[WARNING] Some validation gates failed. Review model performance.")
    else:
        print(f"\n[SUCCESS] All validation gates passed!")


if __name__ == "__main__":
    main()

