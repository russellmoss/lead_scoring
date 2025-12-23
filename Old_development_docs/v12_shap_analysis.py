"""
SHAP Analysis for V12 Model
===========================

Generates local and global SHAP explanations for the V12 XGBoost model using the
Impact Attendees dataset (or any dataset matching the V12 feature schema).

Outputs:
  - CSV of mean |SHAP| values per feature
  - CSV of per-row SHAP contributions for the sampled leads
  - Optional SHAP summary bar plot (if matplotlib support is available)
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import shap
from google.cloud import bigquery

from v12_score_impact_list import (
    DEFAULT_DISCOVERY_VIEW,
    DEFAULT_IMPACT_TABLE,
    DEFAULT_OUTPUT_DIR,
    add_engineered_features,
    apply_feature_drops,
    bin_tenure_features,
    encode_categoricals_from_metadata,
    encode_gender,
    load_artifacts,
    prepare_feature_matrix,
    resolve_discovery_source,
    fetch_impact_dataframe,
)


PROJECT = "savvy-gtm-analytics"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute SHAP values for the V12 model.")
    parser.add_argument("--project", default=PROJECT, help="BigQuery project ID.")
    parser.add_argument("--impact-table", default=DEFAULT_IMPACT_TABLE, help="Source table to score.")
    parser.add_argument("--discovery-view", default=DEFAULT_DISCOVERY_VIEW, help="Discovery snapshot source.")
    parser.add_argument("--as-of-date", required=True, help="As-of date (YYYY-MM-DD) for point-in-time join.")
    parser.add_argument("--sample-size", type=int, default=300, help="Number of rows to sample for SHAP.")
    parser.add_argument("--model-path", default=None, help="Optional override for the V12 model pickle path.")
    parser.add_argument("--metadata-path", default=None, help="Optional override for the V12 metadata json path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to store SHAP outputs.")
    parser.add_argument("--discovery-tier", choices=["t1", "t2", "t3", "view", "latest"], default="view",
                        help="Discovery snapshot source tier (t1/t2/t3), combined latest snapshot, or the point-in-time view.")
    return parser.parse_args()


def build_feature_matrix(
    client: bigquery.Client,
    impact_table: str,
    discovery_config: Dict[str, str],
    as_of_date: str,
    feature_names: List[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    df_raw = fetch_impact_dataframe(client, impact_table, discovery_config, pd.to_datetime(as_of_date).date())

    df_features = add_engineered_features(df_raw)
    df_features = apply_feature_drops(df_features)
    df_features = bin_tenure_features(df_features)
    df_features = encode_gender(df_features)

    categorical_columns = ["Home_State", "Branch_State", "Office_State"]
    for col in categorical_columns:
        df_features = encode_categoricals_from_metadata(df_features, feature_names, col)

    feature_matrix, missing_features = prepare_feature_matrix(df_features, feature_names)
    if missing_features:
        print(f"[WARNING] {len(missing_features)} features missing from dataset, filled with zeros:")
        for feat in missing_features[:20]:
            print(f"  - {feat}")

    return df_raw, feature_matrix


def compute_shap_values(
    model,
    feature_matrix: pd.DataFrame,
    sample_size: int,
) -> Tuple[pd.DataFrame, np.ndarray, pd.Index]:
    if len(feature_matrix) > sample_size:
        explain_df = feature_matrix.sample(sample_size, random_state=42)
    else:
        explain_df = feature_matrix

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(explain_df)
        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    except Exception as exc:
        print(f"[INFO] TreeExplainer failed ({exc}). Falling back to permutation SHAP (slower).")
        background = shap.sample(feature_matrix, min(len(feature_matrix), 1000), random_state=42)

        def predict_fn(data: np.ndarray) -> np.ndarray:
            return model.predict_proba(data)[:, 1]

        perm_explainer = shap.Explainer(
            predict_fn,
            background,
            algorithm="permutation",
            output_names=["probability"],
        )
        shap_values = perm_explainer(explain_df).values

    return explain_df, shap_values, explain_df.index


def save_outputs(
    output_dir: Path,
    explain_df: pd.DataFrame,
    shap_values: np.ndarray,
    feature_names: Iterable[str],
    df_raw: pd.DataFrame,
    explain_index: pd.Index,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    shap_abs = np.abs(shap_values)
    mean_abs = shap_abs.mean(axis=0)
    importance_df = pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs})
    importance_df = importance_df.sort_values("mean_abs_shap", ascending=False)
    importance_path = output_dir / "v12_shap_importance.csv"
    importance_df.to_csv(importance_path, index=False)
    print(f"[OK] SHAP feature importance saved: {importance_path}")

    shap_detail_df = explain_df.copy()
    raw_subset = df_raw.loc[explain_index]
    join_cols = [col for col in raw_subset.columns if col not in shap_detail_df.columns]
    shap_detail_df = pd.concat([raw_subset[join_cols].reset_index(drop=True), shap_detail_df.reset_index(drop=True)], axis=1)
    for idx, feat in enumerate(feature_names):
        shap_detail_df[f"shap_{feat}"] = shap_values[:, idx]
    detail_path = output_dir / "v12_shap_detail.csv"
    shap_detail_df.to_csv(detail_path, index=False)
    print(f"[OK] SHAP detail saved: {detail_path}")

    try:
        shap.summary_plot(shap_values, explain_df, show=False, plot_type="bar")
        import matplotlib.pyplot as plt

        plot_path = output_dir / "v12_shap_summary_bar.png"
        plt.tight_layout()
        plt.savefig(plot_path, dpi=200)
        plt.close()
        print(f"[OK] SHAP summary plot saved: {plot_path}")
    except Exception as exc:
        print(f"[INFO] Skipped SHAP summary plot (matplotlib/shap limitation): {exc}")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    artifacts = load_artifacts(
        Path(args.model_path) if args.model_path else None,
        Path(args.metadata_path) if args.metadata_path else None,
    )
    feature_names = artifacts.metadata["features"]

    with open(artifacts.model_path, "rb") as f:
        model = pickle.load(f)

    client = bigquery.Client(project=args.project)
    discovery_config = resolve_discovery_source(args.discovery_view, args.discovery_tier)

    print(f"[INFO] Using discovery source: {discovery_config}")
    df_raw, feature_matrix = build_feature_matrix(
        client,
        args.impact_table,
        discovery_config,
        args.as_of_date,
        feature_names,
    )
    print(f"[INFO] Assembled feature matrix with {len(feature_matrix)} rows and {feature_matrix.shape[1]} features")

    explain_df, shap_values, explain_index = compute_shap_values(model, feature_matrix, args.sample_size)
    print(f"[INFO] Computed SHAP values for {len(explain_df)} samples")

    save_outputs(
        output_dir,
        explain_df,
        shap_values,
        feature_names,
        df_raw,
        explain_index,
    )


if __name__ == "__main__":
    main()


