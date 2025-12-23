"""
Unit 4 V6 with Financials: Model Training
Reads from BigQuery step_3_4_training_dataset_v6_with_financials table, drops PII, trains XGBoost model.
V6 with Financials: Uses V5-style regularization, all features already engineered in SQL, plus financial features.
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
# Use the specific table with financials
BQ_TABLE = "savvy-gtm-analytics.LeadScoring.step_3_4_training_dataset_v6_with_financials_20251104_2256"
PROJECT_ID = "savvy-gtm-analytics"

# Version string
VERSION = datetime.now().strftime("%Y%m%d")

print("=" * 80)
print("Unit 4 V6 with Financials: Model Training")
print("=" * 80)
print(f"Data source: {BQ_TABLE}")
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
    """Load training data from BigQuery table"""
    print(f"[1/10] Loading data from BigQuery table: {BQ_TABLE}...", flush=True)
    
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{BQ_TABLE}`'
    
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
        "days_to_conversion", "has_financial_data_flag"
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
                    n_jobs=-1,
                    eval_metric="logloss",
                    enable_categorical=True
                )
                model_smote.fit(X_res, y_res)
                
                y_pred_proba_smote = model_smote.predict_proba(X_valid)[:, 1]
                smote_aucpr = average_precision_score(y_valid, y_pred_proba_smote)
                smote_aucroc = roc_auc_score(y_valid, y_pred_proba_smote)
                smote_success = True
                print(f"         SMOTE: AUC-PR={smote_aucpr:.4f}, AUC-ROC={smote_aucroc:.4f}", flush=True)
            except Exception as e:
                print(f"         SMOTE failed: {e}", flush=True)
        
        # Strategy 2: scale_pos_weight (always available)
        print(f"      Testing scale_pos_weight (spw={spw:.2f})...", flush=True)
        model_spw = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.02,
            subsample=0.7,
            colsample_bytree=0.7,
            reg_alpha=1.0,
            reg_lambda=5.0,
            scale_pos_weight=spw,
            random_state=seed,
            n_jobs=-1,
            eval_metric="logloss",
            enable_categorical=True
        )
        model_spw.fit(X_train, y_train)
        
        y_pred_proba_spw = model_spw.predict_proba(X_valid)[:, 1]
        spw_aucpr = average_precision_score(y_valid, y_pred_proba_spw)
        spw_aucroc = roc_auc_score(y_valid, y_pred_proba_spw)
        print(f"         scale_pos_weight: AUC-PR={spw_aucpr:.4f}, AUC-ROC={spw_aucroc:.4f}", flush=True)
        
        # Choose best strategy
        if smote_success and smote_aucpr > spw_aucpr:
            winning_strategy = "SMOTE"
            winning_aucpr = smote_aucpr
            winning_aucroc = smote_aucroc
        else:
            winning_strategy = "scale_pos_weight"
            winning_aucpr = spw_aucpr
            winning_aucroc = spw_aucroc
        
        cv_metrics.append({
            "fold": fold_id + 1,
            "strategy": winning_strategy,
            "aucpr": winning_aucpr,
            "aucroc": winning_aucroc,
            "train_size": len(train_idx),
            "test_size": len(test_idx),
            "pos_train": pos,
            "neg_train": neg
        })
        
        print(f"      Fold {fold_id + 1} winner: {winning_strategy} (AUC-PR={winning_aucpr:.4f})", flush=True)
    
    # Aggregate CV results
    print(f"[8/10] Cross-validation complete", flush=True)
    cv_df = pd.DataFrame(cv_metrics)
    mean_aucpr = cv_df["aucpr"].mean()
    std_aucpr = cv_df["aucpr"].std()
    mean_aucroc = cv_df["aucroc"].mean()
    std_aucroc = cv_df["aucroc"].std()
    
    print(f"   Mean AUC-PR: {mean_aucpr:.4f} ± {std_aucpr:.4f}")
    print(f"   Mean AUC-ROC: {mean_aucroc:.4f} ± {std_aucroc:.4f}")
    
    # Determine winning strategy overall
    strategy_wins = cv_df["strategy"].value_counts()
    winning_strategy = strategy_wins.index[0]
    print(f"   Winning strategy: {winning_strategy} ({strategy_wins[winning_strategy]} folds)")
    print()
    
    # Train final model on all data
    print(f"[9/10] Training final model on all data...", flush=True)
    
    pos_all = (y_all == 1).sum()
    neg_all = (y_all == 0).sum()
    spw_all = max(neg_all / max(pos_all, 1), 1.0)
    
    # Use winning strategy
    if winning_strategy == "SMOTE" and not has_categorical and pos_all > 1:
        try:
            sampler = SMOTE(sampling_strategy=0.1, random_state=seed, k_neighbors=min(5, pos_all - 1))
            X_res, y_res = sampler.fit_resample(X_all, y_all)
            final_model = XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.02,
                subsample=0.7,
                colsample_bytree=0.7,
                reg_alpha=1.0,
                reg_lambda=5.0,
                random_state=seed,
                n_jobs=-1,
                eval_metric="logloss",
                enable_categorical=True
            )
            final_model.fit(X_res, y_res)
            imbalance_strategy = "SMOTE"
        except Exception:
            final_model = XGBClassifier(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.02,
                subsample=0.7,
                colsample_bytree=0.7,
                reg_alpha=1.0,
                reg_lambda=5.0,
                scale_pos_weight=spw_all,
                random_state=seed,
                n_jobs=-1,
                eval_metric="logloss",
                enable_categorical=True
            )
            final_model.fit(X_all, y_all)
            imbalance_strategy = "scale_pos_weight"
    else:
        final_model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.02,
            subsample=0.7,
            colsample_bytree=0.7,
            reg_alpha=1.0,
            reg_lambda=5.0,
            scale_pos_weight=spw_all,
            random_state=seed,
            n_jobs=-1,
            eval_metric="logloss",
            enable_categorical=True
        )
        final_model.fit(X_all, y_all)
        imbalance_strategy = "scale_pos_weight"
    
    print(f"   Final model trained using {imbalance_strategy}", flush=True)
    
    # Feature importance
    feature_importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": final_model.feature_importances_
    }).sort_values("importance", ascending=False)
    
    print(f"   Top 5 features: {', '.join(feature_importance.head(5)['feature'].tolist())}", flush=True)
    print()
    
    # Save artifacts
    print(f"[10/10] Saving model artifacts...", flush=True)
    
    model_path = ARTIFACTS_DIR / f"model_v6_with_financials_{VERSION}.pkl"
    baseline_path = ARTIFACTS_DIR / f"model_v6_with_financials_{VERSION}_baseline_logit.pkl"
    feature_order_path = ARTIFACTS_DIR / f"feature_order_v6_with_financials_{VERSION}.json"
    feature_importance_path = ARTIFACTS_DIR / f"feature_importance_v6_with_financials_{VERSION}.csv"
    report_path = ARTIFACTS_DIR / f"model_training_report_v6_with_financials_{VERSION}.md"
    
    # Save model
    joblib.dump(final_model, model_path)
    print(f"   Model saved: {model_path}", flush=True)
    
    # Save baseline (logistic regression)
    # Encode categoricals and fill NaN for baseline
    print(f"   Preparing data for baseline model...", flush=True)
    X_baseline = X_all.copy()
    label_encoders = {}
    for col in X_baseline.columns:
        if pd.api.types.is_categorical_dtype(X_baseline[col]) or X_baseline[col].dtype == 'object':
            le = LabelEncoder()
            X_baseline[col] = le.fit_transform(X_baseline[col].astype(str).fillna("__MISSING__"))
            label_encoders[col] = le
        else:
            # Fill numeric NaN with median (or 0 if all NaN)
            median_val = X_baseline[col].median()
            if pd.isna(median_val):
                X_baseline[col] = X_baseline[col].fillna(0)
            else:
                X_baseline[col] = X_baseline[col].fillna(median_val)
    
    baseline = LogisticRegression(max_iter=1000, random_state=seed, class_weight="balanced")
    baseline.fit(X_baseline, y_all)
    joblib.dump(baseline, baseline_path)
    print(f"   Baseline saved: {baseline_path}", flush=True)
    
    # Save feature order
    with open(feature_order_path, "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"   Feature order saved: {feature_order_path}", flush=True)
    
    # Save feature importance
    feature_importance.to_csv(feature_importance_path, index=False)
    print(f"   Feature importance saved: {feature_importance_path}", flush=True)
    
    # Generate report
    report = f"""# V6 with Financials Model Training Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Version:** {VERSION}

## Dataset Summary

- **Total Samples:** {len(df):,}
- **Positive Class:** {pos_all:,} ({pos_all/len(df)*100:.2f}%)
- **Negative Class:** {neg_all:,} ({neg_all/len(df)*100:.2f}%)
- **Features:** {len(feature_cols)}
- **CV Folds:** {cv_folds}

## Cross-Validation Results

- **Mean AUC-PR:** {mean_aucpr:.4f} ± {std_aucpr:.4f}
- **CV Coefficient:** {std_aucpr/mean_aucpr*100:.2f}%
- **Winning Strategy:** {winning_strategy}
- **Strategy Wins:** SMOTE={strategy_wins.get('SMOTE', 0)}, scale_pos_weight={strategy_wins.get('scale_pos_weight', 0)}
- **Fold Details:**
"""
    
    for row in cv_df.itertuples():
        report += f"  - Fold {row.fold} ({row.strategy}): AUC-PR={row.aucpr:.4f}, AUC-ROC={row.aucroc:.4f}\n"
    
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
  - scale_pos_weight: {spw_all:.2f} (used if scale_pos_weight strategy)
  - **Imbalance Strategy:** {imbalance_strategy}

## Top 20 Features

"""
    
    for _, row in feature_importance.head(20).iterrows():
        report += f"{row['feature']}: {row['importance']:.6f}\n"
    
    report += f"""
## Artifacts Saved

- Model: `model_v6_with_financials_{VERSION}.pkl`
- Baseline: `model_v6_with_financials_{VERSION}_baseline_logit.pkl`
- Feature Order: `feature_order_v6_with_financials_{VERSION}.json`
- Feature Importance: `feature_importance_v6_with_financials_{VERSION}.csv`

## Validation Gates

- **CV AUC-PR > 0.15:** {'PASS' if mean_aucpr > 0.15 else 'FAIL'} ({mean_aucpr:.4f})
- **CV Coefficient < 20%:** {'PASS' if (std_aucpr/mean_aucpr*100) < 20 else 'FAIL'} ({std_aucpr/mean_aucpr*100:.2f}%)
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"   Report saved: {report_path}", flush=True)
    
    print()
    print("=" * 80)
    print("Training Complete!")
    print("=" * 80)
    print(f"CV AUC-PR: {mean_aucpr:.4f} ± {std_aucpr:.4f}")
    print(f"CV AUC-ROC: {mean_aucroc:.4f} ± {std_aucroc:.4f}")
    print(f"Winning Strategy: {winning_strategy}")
    print()
    
    # Validation gates
    if mean_aucpr > 0.15:
        print("[PASS] CV AUC-PR > 0.15")
    else:
        print("[FAIL] CV AUC-PR <= 0.15")
    
    if (std_aucpr/mean_aucpr*100) < 20:
        print("[PASS] CV Coefficient < 20%")
    else:
        print("[FAIL] CV Coefficient >= 20%")
    
    print()


if __name__ == "__main__":
    main()

