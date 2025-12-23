import json
import os
import csv
import math
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import average_precision_score, roc_auc_score, precision_recall_curve
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import VarianceThreshold
from sklearn.utils import compute_sample_weight

from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

import shap
import json

ARTIFACTS_DIR = os.path.join(os.getcwd())
CONFIG_PATH = os.path.join(os.getcwd(), "config", "v1_model_config.json")
FEATURE_SCHEMA_PATH = os.path.join(os.getcwd(), "config", "v1_feature_schema.json")
DATASET_PATH = os.path.join(os.getcwd(), "step_3_3_training_dataset.csv")


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_feature_schema() -> Dict[str, Any]:
    with open(FEATURE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def read_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATASET_PATH)
    return df


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    ts_col = "Stage_Entered_Contacting__c"
    ts = pd.to_datetime(df[ts_col], errors="coerce", utc=True)
    df["Day_of_Contact"] = ts.dt.dayofweek + 1  # 1=Monday .. 7=Sunday
    df["Is_Weekend_Contact"] = df["Day_of_Contact"].isin([6, 7]).astype(int)
    return df


def validate_against_schema(df: pd.DataFrame, schema: Dict[str, Any]) -> List[str]:
    issues = []
    exclusions = set(schema.get("exclusions", []))
    feature_names = [f["name"] for f in schema.get("features", [])]

    missing = [c for c in feature_names if c not in df.columns]
    if missing:
        issues.append(f"Missing features: {missing}")

    # Type checks are soft due to CSV loading; we focus on presence.
    return issues


def get_feature_columns(df: pd.DataFrame, schema: Dict[str, Any]) -> List[str]:
    exclusions = set(schema.get("exclusions", []))
    base_features = [f["name"] for f in schema.get("features", []) if f["name"] in df.columns]
    # Add temporal features
    base_features += ["Day_of_Contact", "Is_Weekend_Contact"]

    # Remove ID/label/time columns if present
    drop_cols = {"Id", "FA_CRD__c", "Stage_Entered_Contacting__c", "Stage_Entered_Call_Scheduled__c", "target_label"}
    features = [c for c in base_features if c not in drop_cols]
    return sorted(list(dict.fromkeys(features)))


def cast_categoricals_inplace(df: pd.DataFrame, columns: List[str]) -> None:
    for c in columns:
        if c in df.columns and df[c].dtype == object:
            df[c] = df[c].astype("category")


def compute_vif_filter(df: pd.DataFrame, continuous_cols: List[str], vif_threshold: float = 10.0) -> List[str]:
    # Simple VIF approximation via correlation; robust VIF requires statsmodels and invertibility handling.
    # We apply a greedy correlation-based removal to avoid multicollinearity.
    if not continuous_cols:
        return continuous_cols
    corr = df[continuous_cols].corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    to_drop = set()
    for col in upper.columns:
        if any(upper[col] > 0.95):
            to_drop.add(col)
    kept = [c for c in continuous_cols if c not in to_drop]
    return kept


def compute_information_value(x: pd.Series, y: pd.Series, bins: int = 10) -> float:
    try:
        s = pd.qcut(x.rank(method="first"), q=min(bins, x.notna().sum()), duplicates="drop")
    except Exception:
        return 0.0
    iv = 0.0
    for b in s.unique():
        mask = s == b
        event = ((y == 1) & mask).sum()
        non_event = ((y == 0) & mask).sum()
        total_event = (y == 1).sum()
        total_non_event = (y == 0).sum()
        if total_event == 0 or total_non_event == 0:
            return 0.0
        pe = event / total_event
        pne = non_event / total_non_event
        if pe > 0 and pne > 0:
            iv += (pe - pne) * math.log(pe / pne)
    return iv


def apply_prefilters(train_df: pd.DataFrame, feature_cols: List[str], y_col: str = "target_label") -> List[str]:
    # IV filter
    iv_scores = {}
    for c in feature_cols:
        if pd.api.types.is_numeric_dtype(train_df[c]):
            iv_scores[c] = compute_information_value(train_df[c], train_df[y_col])
        else:
            # For non-numeric, keep for tree models (XGBoost with categorical support)
            iv_scores[c] = 0.02
    kept_iv = [c for c, v in iv_scores.items() if v >= 0.02]

    # VIF-like filter on numeric subset
    numeric_kept = [c for c in kept_iv if pd.api.types.is_numeric_dtype(train_df[c])]
    numeric_after_vif = compute_vif_filter(train_df, numeric_kept, vif_threshold=10.0)

    # Merge back non-numeric kept
    non_numeric_kept = [c for c in kept_iv if c not in numeric_kept]
    final_kept = sorted(list(dict.fromkeys(numeric_after_vif + non_numeric_kept)))
    return final_kept


def blocked_time_series_folds(df: pd.DataFrame, n_folds: int, gap_days: int, time_col: str, seed: int) -> List[Tuple[np.ndarray, np.ndarray]]:
    # Sort by time and split into contiguous folds; apply gap by trimming overlap
    d = df.sort_values(time_col).reset_index(drop=True)
    n = len(d)
    fold_sizes = [n // n_folds + (1 if i < n % n_folds else 0) for i in range(n_folds)]
    indices = np.arange(n)
    folds = []
    start = 0
    for size in fold_sizes:
        end = start + size
        test_idx = indices[start:end]
        # Gap: exclude records within gap_days before test start from training
        test_start_time = pd.to_datetime(d.loc[start, time_col]) if size > 0 else None
        if test_start_time is not None:
            gap_mask = pd.to_datetime(d[time_col]) <= (test_start_time - pd.Timedelta(days=gap_days))
            train_idx = indices[gap_mask.values]
        else:
            train_idx = indices[:start]
        folds.append((train_idx, test_idx))
        start = end
    return folds


def evaluate_strategy(X_train: pd.DataFrame, y_train: pd.Series, X_valid: pd.DataFrame, y_valid: pd.Series, strategy: str, seed: int) -> Dict[str, Any]:
    if strategy == "smote":
        if len(X_train) == 0 or y_train.nunique() < 2:
            return {"model": None, "aucpr": float("-inf"), "aucroc": float("nan")}
        sampler = SMOTE(random_state=seed)
        X_res, y_res = sampler.fit_resample(X_train, y_train)
        model = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic",
            base_score=0.5
        )
        model.fit(X_res, y_res)
    else:
        # scale_pos_weight
        pos = (y_train == 1).sum()
        neg = (y_train == 0).sum()
        spw = max((neg / max(pos, 1)), 1.0)
        model = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            scale_pos_weight=spw,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic",
            base_score=0.5
        )
        model.fit(X_train, y_train)

    preds = model.predict_proba(X_valid)[:, 1]
    aucpr = average_precision_score(y_valid, preds)
    aucroc = roc_auc_score(y_valid, preds)
    return {"model": model, "aucpr": aucpr, "aucroc": aucroc}


def main():
    cfg = load_config()
    schema = load_feature_schema()
    seed = int(cfg.get("global_seed", 42))
    gap_days = int(cfg.get("cv_gap_days", 30))
    cv_folds = int(cfg.get("cv_folds", 5))

    df = read_dataset()
    df = add_temporal_features(df)
    # Ensure binary labels only
    if "target_label" in df.columns:
        df = df[df["target_label"].isin([0, 1])].copy()

    issues = validate_against_schema(df, schema)
    if issues:
        raise RuntimeError("Schema validation failed: " + "; ".join(issues))

    feature_cols = get_feature_columns(df, schema)
    # Cast categoricals for XGBoost
    cast_categoricals_inplace(df, feature_cols)

    y_col = "target_label"
    time_col = "Stage_Entered_Contacting__c"

    # Build folds and persist indices
    folds = blocked_time_series_folds(df, n_folds=cv_folds, gap_days=gap_days, time_col=time_col, seed=seed)
    cv_indices = []

    metrics = []
    all_removed_features = []

    for fold_id, (train_idx, test_idx) in enumerate(folds):
        train_df = df.iloc[train_idx].reset_index(drop=True)
        test_df = df.iloc[test_idx].reset_index(drop=True)

        if len(train_df) == 0 or len(test_df) == 0:
            continue

        kept_features = apply_prefilters(train_df, feature_cols, y_col)
        removed = [c for c in feature_cols if c not in kept_features]
        all_removed_features.append({"fold": fold_id, "removed": removed})

        X_train = train_df[kept_features].copy()
        y_train = train_df[y_col].astype(int)
        X_valid = test_df[kept_features].copy()
        y_valid = test_df[y_col].astype(int)

        if y_train.nunique() < 2:
            # Can't train binary classifier with single-class training fold; skip fold
            continue

        # Ensure categorical dtypes propagate
        cast_categoricals_inplace(X_train, kept_features)
        cast_categoricals_inplace(X_valid, kept_features)

        # Evaluate both strategies
        res_spw = evaluate_strategy(X_train, y_train, X_valid, y_valid, strategy="spw", seed=seed)
        res_smote = evaluate_strategy(X_train, y_train, X_valid, y_valid, strategy="smote", seed=seed)

        best = "smote" if res_smote["aucpr"] > res_spw["aucpr"] else "spw"
        metrics.append({
            "fold": fold_id,
            "kept_features": len(kept_features),
            "strategy_smote_aucpr": res_smote["aucpr"],
            "strategy_spw_aucpr": res_spw["aucpr"],
            "best_strategy": best
        })

        cv_indices.append({
            "fold": fold_id,
            "train_indices": train_df.index.tolist(),
            "test_indices": test_df.index.tolist()
        })

    # Determine winning strategy overall
    best_votes = sum(1 for m in metrics if m["best_strategy"] == "spw")
    winning_strategy = "spw" if best_votes >= (len(metrics) - best_votes) else "smote"

    # Train final models on all data using winning strategy
    final_kept = apply_prefilters(df, feature_cols, y_col)
    X_all = df[final_kept].copy()
    y_all = df[y_col].astype(int)
    cast_categoricals_inplace(X_all, final_kept)

    if winning_strategy == "smote":
        sampler = SMOTE(random_state=seed)
        X_res, y_res = sampler.fit_resample(X_all, y_all)
        final_model = XGBClassifier(
            n_estimators=400,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic",
            base_score=0.5
        )
        final_model.fit(X_res, y_res)
    else:
        pos = (y_all == 1).sum()
        neg = (y_all == 0).sum()
        spw = max((neg / max(pos, 1)), 1.0)
        final_model = XGBClassifier(
            n_estimators=400,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            scale_pos_weight=spw,
            eval_metric="logloss",
            tree_method="hist",
            enable_categorical=True,
            objective="binary:logistic",
            base_score=0.5
        )
        final_model.fit(X_all, y_all)

    # Baseline Logistic Regression (one-hot encode categoricals)
    X_all_ohe = pd.get_dummies(X_all, dummy_na=True)
    baseline = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
    baseline.fit(X_all_ohe.fillna(0), y_all)

    # Save artifacts
    import joblib
    joblib.dump(final_model, os.path.join(ARTIFACTS_DIR, "model_v1.pkl"))
    joblib.dump(baseline, os.path.join(ARTIFACTS_DIR, "model_v1_baseline_logit.pkl"))

    with open(os.path.join(ARTIFACTS_DIR, "cv_fold_indices_v1.json"), "w", encoding="utf-8") as f:
        json.dump(cv_indices, f, indent=2)

    # Importance
    importance_path = os.path.join(ARTIFACTS_DIR, "feature_importance_v1.csv")
    try:
        explainer = shap.TreeExplainer(final_model)
        shap_vals = explainer.shap_values(X_all)
        mean_abs = np.mean(np.abs(shap_vals), axis=0)
        importance = pd.DataFrame({"feature": final_kept, "mean_abs_shap": mean_abs}).sort_values("mean_abs_shap", ascending=False)
        importance.to_csv(importance_path, index=False)
    except Exception:
        # Fallback to gain-based importance from booster
        booster = final_model.get_booster()
        score = booster.get_score(importance_type='gain')
        rows = []
        for i, f in enumerate(final_kept):
            val = score.get(f, 0.0)
            rows.append({"feature": f, "gain_importance": val})
        pd.DataFrame(rows).sort_values("gain_importance", ascending=False).to_csv(importance_path, index=False)

    with open(os.path.join(ARTIFACTS_DIR, "selected_features_v1.json"), "w", encoding="utf-8") as f:
        json.dump(final_kept, f, indent=2)

    # Reports
    report_lines = [
        f"Winning strategy: {winning_strategy}",
        "Fold metrics:",
    ]
    for m in metrics:
        report_lines.append(json.dumps(m))

    with open(os.path.join(ARTIFACTS_DIR, "feature_selection_report_v1.md"), "w", encoding="utf-8") as f:
        f.write("# Feature Selection Report V1\n\n")
        f.write("Removed features by fold (IV/VIF):\n\n")
        for entry in all_removed_features:
            f.write(f"- Fold {entry['fold']}: removed {len(entry['removed'])} features\n")

    with open(os.path.join(ARTIFACTS_DIR, "model_training_report_v1.md"), "w", encoding="utf-8") as f:
        f.write("# Model Training Report V1\n\n")
        f.write("Winning strategy and CV metrics\n\n")
        f.write("\n".join(report_lines))


if __name__ == "__main__":
    main()
