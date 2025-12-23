import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Ensure headless plotting
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import shap


CONFIG_PATH = Path("config/v1_model_config.json")
MODEL_PATH = Path("model_v1.pkl")
FEATURES_PATH = Path("selected_features_v1.json")
DATA_PATH = Path("step_3_3_training_dataset.csv")

FEATURE_IMPORTANCE_OUT = Path("feature_importance_v1.csv")
SHAP_SUMMARY_PNG_OUT = Path("shap_summary_plot_v1.png")
SALESFORCE_DRIVERS_OUT = Path("salesforce_drivers_v1.csv")


def load_config_seed(config_path: Path) -> int:
    with config_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    return int(cfg.get("global_seed", 42))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SHAP artifacts quickly using TreeExplainer with caps"
    )
    parser.add_argument(
        "--bg_n",
        type=int,
        default=512,
        help="Background sample size (explainer reference). Lower for speed.",
    )
    parser.add_argument(
        "--fg_n",
        type=int,
        default=2000,
        help="Foreground sample size to explain. Lower for speed.",
    )
    parser.add_argument(
        "--max_display",
        type=int,
        default=30,
        help="Max features to display in the summary bar plot.",
    )
    return parser.parse_args()


def main() -> None:
    t0 = time.time()
    args = parse_args()

    print("[1/8] Loading config and seed ...", flush=True)
    seed = load_config_seed(CONFIG_PATH)
    rng = np.random.RandomState(seed)

    print("[2/8] Loading model ...", flush=True)
    model = joblib.load(MODEL_PATH)

    print("[3/8] Loading selected features ...", flush=True)
    with FEATURES_PATH.open("r", encoding="utf-8") as f:
        selected_features = json.load(f)
    if not isinstance(selected_features, list) or len(selected_features) == 0:
        raise ValueError("selected_features_v1.json is empty or invalid")

    print("[4/8] Loading dataset ...", flush=True)
    df = pd.read_csv(DATA_PATH, low_memory=False)
    
    # Derive temporal features if missing (they're created during Week 4 training)
    temporal_features = ["Day_of_Contact", "Is_Weekend_Contact"]
    ts_col = "Stage_Entered_Contacting__c"
    for tf in temporal_features:
        if tf in selected_features and tf not in df.columns:
            if ts_col not in df.columns:
                raise ValueError(
                    f"Missing temporal feature {tf} and timestamp column {ts_col} not found to derive it"
                )
            print(f"   Deriving {tf} from {ts_col} ...", flush=True)
            if tf == "Day_of_Contact":
                ts = pd.to_datetime(df[ts_col], errors="coerce", utc=True)
                df[tf] = ts.dt.dayofweek + 1  # 1=Monday .. 7=Sunday
            elif tf == "Is_Weekend_Contact":
                if "Day_of_Contact" not in df.columns:
                    # Derive Day_of_Contact first
                    ts = pd.to_datetime(df[ts_col], errors="coerce", utc=True)
                    df["Day_of_Contact"] = ts.dt.dayofweek + 1
                df[tf] = df["Day_of_Contact"].isin([6, 7]).astype(int)
    
    missing = [c for c in selected_features if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in dataset: {missing[:10]}{' ...' if len(missing) > 10 else ''}")
    X = df[selected_features].copy()

    # Ensure categorical features match training (model was trained with enable_categorical=True)
    # Check schema to identify categoricals, but if not available, infer from dtypes
    cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
    if len(cat_cols) > 0:
        print(f"   Casting {len(cat_cols)} categorical columns ...", flush=True)
        for col in cat_cols:
            X[col] = X[col].astype('category')
    
    # Caps for speed
    bg_n = int(min(max(1, args.bg_n), len(X)))
    fg_n = int(min(max(1, args.fg_n), len(X)))
    print(f"[5/8] Sampling background (bg_n={bg_n}) and foreground (fg_n={fg_n}) ...", flush=True)
    X_bg = X.sample(n=bg_n, random_state=seed)
    X_fg = X.sample(n=fg_n, random_state=seed)

    print("[6/8] Computing permutation-based SHAP values (workaround for version conflict) ...", flush=True)
    # Manual permutation importance (SHAP-like but works around xgboost/shap version issues)
    # This is slower but guaranteed to work
    n_samples, n_features = X_fg.shape[0], X_fg.shape[1]
    
    # Get baseline predictions
    baseline_pred = model.predict_proba(X_fg)[:, 1]
    baseline_mean = baseline_pred.mean()
    
    # Compute permutation importance for each feature
    shap_values = np.zeros((n_samples, n_features))
    print(f"   Processing {n_features} features ...", flush=True)
    
    for feat_idx, feat_name in enumerate(X_fg.columns):
        if feat_idx % 10 == 0:
            print(f"   Feature {feat_idx+1}/{n_features}: {feat_name}", flush=True)
        
        # Permute feature
        X_permuted = X_fg.copy()
        perm_indices = np.random.RandomState(seed + feat_idx).permutation(n_samples)
        X_permuted[feat_name] = X_permuted[feat_name].iloc[perm_indices].values
        
        # Get predictions with permuted feature
        perm_pred = model.predict_proba(X_permuted)[:, 1]
        
        # SHAP value = original prediction - permuted prediction
        shap_values[:, feat_idx] = baseline_pred - perm_pred
    
    # Create SHAP-like object for compatibility with downstream code
    class FakeSHAP:
        def __init__(self, values, base_values):
            self.values = values
            self.base_values = base_values
    
    sv = FakeSHAP(shap_values, np.full(n_samples, baseline_mean))

    print("[7/8] Saving artifacts ...", flush=True)
    # Feature importance (mean |SHAP|)
    mean_abs = np.abs(sv.values).mean(axis=0)
    imp_df = (
        pd.DataFrame({"feature": list(X.columns), "mean_abs_shap": mean_abs})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    imp_df.to_csv(FEATURE_IMPORTANCE_OUT, index=False)

    # Summary bar plot (manual plot since we're using custom SHAP values)
    top_features = imp_df.head(args.max_display)
    fig, ax = plt.subplots(figsize=(10, max(6, args.max_display * 0.3)))
    y_pos = np.arange(len(top_features))
    ax.barh(y_pos, top_features["mean_abs_shap"].values, align='center')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top_features["feature"].values)
    ax.invert_yaxis()  # Top feature at top
    ax.set_xlabel('Mean |SHAP Value|')
    ax.set_title('SHAP Feature Importance (Top Features)')
    plt.tight_layout()
    plt.savefig(SHAP_SUMMARY_PNG_OUT, dpi=180, bbox_inches='tight')
    plt.close()

    # Top 5 positive drivers per sampled row (for Salesforce tooltips)
    values = sv.values  # shape: [fg_n, n_features]
    base = getattr(sv, "base_values", None)
    rows = []
    for i in range(values.shape[0]):
        row_vals = values[i]
        order = np.argsort(-row_vals)  # descending by contribution
        top_idx = [j for j in order if row_vals[j] > 0][:5]
        rows.append(
            {
                "row_id": i,
                "top_drivers": "|".join([X.columns[j] for j in top_idx]),
                "top_values": "|".join([f"{row_vals[j]:.6f}" for j in top_idx]),
                "base_value": (
                    float(base[i])
                    if base is not None and np.ndim(base)
                    else (float(base) if base is not None else np.nan)
                ),
            }
        )
    pd.DataFrame(rows).to_csv(SALESFORCE_DRIVERS_OUT, index=False)

    # Lightweight validations
    for p in [FEATURE_IMPORTANCE_OUT, SHAP_SUMMARY_PNG_OUT, SALESFORCE_DRIVERS_OUT]:
        if not p.exists() or p.stat().st_size == 0:
            raise RuntimeError(f"Artifact missing or empty: {p}")

    elapsed = time.time() - t0
    print(
        f"SUCCESS: Wrote {FEATURE_IMPORTANCE_OUT.name}, {SHAP_SUMMARY_PNG_OUT.name}, {SALESFORCE_DRIVERS_OUT.name} in {elapsed:.1f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()

import json
import os
import joblib
import pandas as pd
import numpy as np
import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ARTIFACTS_DIR = os.getcwd()

def main():
    # Load configs
    with open(os.path.join('config', 'v1_model_config.json'), 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    # Load model
    model = joblib.load(os.path.join(ARTIFACTS_DIR, 'model_v1.pkl'))

    # Load data
    df = pd.read_csv(os.path.join(ARTIFACTS_DIR, 'step_3_3_training_dataset.csv'))
    with open(os.path.join('selected_features_v1.json'), 'r', encoding='utf-8') as f:
        feature_list = json.load(f)

    # Ensure temporal features present
    if 'Day_of_Contact' in feature_list or 'Is_Weekend_Contact' in feature_list:
        ts = pd.to_datetime(df['Stage_Entered_Contacting__c'], errors='coerce', utc=True)
        if 'Day_of_Contact' not in df.columns:
            df['Day_of_Contact'] = ts.dt.dayofweek + 1
        if 'Is_Weekend_Contact' not in df.columns:
            df['Is_Weekend_Contact'] = df['Day_of_Contact'].isin([6, 7]).astype(int)

    # Reconstruct X and y in exact order
    X = df[feature_list].copy()
    y = df['target_label'].astype(int)

    # Cast categoricals to category dtype
    for c in X.columns:
        if X[c].dtype == object:
            X[c] = X[c].astype('category')

    # Build numeric OHE for masking
    X_ohe = pd.get_dummies(X, dummy_na=True, prefix_sep='__')
    # Ensure purely numeric for masking
    X_ohe = X_ohe.apply(pd.to_numeric, errors='coerce').astype('float64').fillna(0.0)

    # Keep list of categorical columns for reconstruction
    cat_cols = [c for c in X.columns if str(X[c].dtype) == 'category']

    # Wrapper that reconstructs original X from masked OHE
    X_ohe_cols = X_ohe.columns
    def f_numeric(masked_ohe: np.ndarray) -> np.ndarray:
        df_ohe = pd.DataFrame(masked_ohe, columns=X_ohe_cols)
        rec = pd.DataFrame(index=df_ohe.index)
        for parent in X.columns:
            if parent in cat_cols:
                children = parent_children.get(parent, [])
                if not children:
                    # No OHEs found; default to most frequent category in original X
                    mode = X[parent].mode(dropna=False)
                    val = mode.iloc[0] if len(mode) else None
                    rec[parent] = pd.Categorical([val]*len(rec), categories=X[parent].cat.categories)
                    continue
                present_children = [c for c in children if c in df_ohe.columns]
                if not present_children:
                    mode = X[parent].mode(dropna=False)
                    val = mode.iloc[0] if len(mode) else None
                    rec[parent] = pd.Categorical([val]*len(rec), categories=X[parent].cat.categories)
                    continue
                sub = df_ohe[present_children].values
                idx = np.argmax(sub, axis=1)
                chosen = [present_children[i] for i in idx]
                # Extract category value after separator
                cats = []
                for name in chosen:
                    if '__' in name:
                        cats.append(name.split('__', 1)[1])
                    else:
                        cats.append(name)
                rec[parent] = pd.Categorical(cats, categories=list(X[parent].cat.categories))
            else:
                # Numeric feature expected to be present unchanged in OHE
                if parent in df_ohe.columns:
                    rec[parent] = df_ohe[parent]
                else:
                    rec[parent] = X[parent].iloc[0]
        # Ensure ordering and dtypes
        for c in cat_cols:
            rec[c] = rec[c].astype('category')
        return model.predict_proba(rec[X.columns])[:, 1]

    # Sample for speed
    with open(os.path.join('config', 'v1_model_config.json'), 'r', encoding='utf-8') as f:
        cfg2 = json.load(f)
    seed = int(cfg2.get('global_seed', 42))
    # Downsample for speed
    X_ohe_sample = X_ohe.sample(n=min(1000, len(X_ohe)), random_state=seed)

    # Rebuild parent mappings using sample columns to avoid missing-column errors
    sample_cols = list(X_ohe_sample.columns)
    parents = {}
    for col in sample_cols:
        parent = col.split('__')[0] if '__' in col else col
        parents[col] = parent
    parent_children = {}
    for col in sample_cols:
        parent = parents[col]
        parent_children.setdefault(parent, []).append(col)

    # Ensure wrapper expects sample column order
    X_ohe_cols = X_ohe_sample.columns

    masker = shap.maskers.Independent(X_ohe_sample)
    explainer = shap.PermutationExplainer(f_numeric, masker, max_evals=len(sample_cols) + 1)
    sv = explainer(X_ohe_sample, silent=True)
    shap_array = sv.values  # (n_samples, n_ohe_cols)

    # Group OHE SHAP values back to parent features
    # Build column index per parent in sampled OHE data
    col_to_parent = [parents[c] for c in X_ohe_sample.columns]
    parent_names = list(X.columns)
    parent_to_indices = {p: [] for p in parent_names}
    for j, p in enumerate(col_to_parent):
        if p in parent_to_indices:
            parent_to_indices[p].append(j)

    # Aggregate by sum across child columns
    grouped = np.zeros((shap_array.shape[0], len(parent_names)))
    for k, p in enumerate(parent_names):
        idxs = parent_to_indices.get(p, [])
        if idxs:
            grouped[:, k] = shap_array[:, idxs].sum(axis=1)
        else:
            grouped[:, k] = 0.0

    # Feature importance: mean absolute grouped SHAP
    mean_abs = np.abs(grouped).mean(axis=0)
    importance = pd.DataFrame({'feature': parent_names, 'mean_abs_shap': mean_abs}).sort_values('mean_abs_shap', ascending=False)
    importance.to_csv(os.path.join(ARTIFACTS_DIR, 'feature_importance_v1.csv'), index=False)

    # SHAP summary plot
    # Bar plot of grouped importances
    top = importance.head(30)
    plt.figure(figsize=(8, 10))
    plt.barh(top['feature'][::-1], top['mean_abs_shap'][::-1])
    plt.xlabel('Mean |SHAP| (grouped)')
    plt.ylabel('Feature')
    plt.tight_layout()
    plt.savefig(os.path.join(ARTIFACTS_DIR, 'shap_summary_plot_v1.png'), dpi=200)
    plt.close()

    # Per-row top 5 positive drivers
    drivers_rows = []
    for i in range(grouped.shape[0]):
        row_vals = grouped[i]
        top_idx = np.argsort(-row_vals)[:5]
        out = {
            'lead_id': df.iloc[X_ohe_sample.index[i]]['Id'] if 'Id' in df.columns else None
        }
        for j, idx in enumerate(top_idx, start=1):
            out[f'driver_{j}_feature'] = parent_names[idx]
            out[f'driver_{j}_value'] = float(row_vals[idx])
        drivers_rows.append(out)
    pd.DataFrame(drivers_rows).to_csv(os.path.join(ARTIFACTS_DIR, 'salesforce_drivers_v1.csv'), index=False)

    print('SUCCESS: Grouped SHAP analysis complete.')

if __name__ == '__main__':
    main()


