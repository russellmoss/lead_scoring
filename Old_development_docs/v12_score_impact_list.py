"""
V12 Scoring Pipeline for Impact Attendees Recruitment Target List
=================================================================

This script loads the Impact attendee list from BigQuery, enriches it with
Discovery snapshots via point-in-time joins, rebuilds the V12 feature set, and
scores each record with a previously trained V12 model artifact.

Usage (example):
---------------
python v12_score_impact_list.py \
    --as-of-date 2025-11-08 \
    --impact-table savvy-gtm-analytics.LeadScoring.Impact_Attendees_Recruitment_Target_List \
    --discovery-view savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages \
    --output-bq-table savvy-gtm-analytics.LeadScoring.Impact_Attendees_V12_Scores \
    --output-csv C:/Users/russe/Documents/Lead Scoring/impact_attendees_v12_scores.csv
"""

from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from google.cloud import bigquery


PROJECT = "savvy-gtm-analytics"
DATASET = "LeadScoring"
DEFAULT_IMPACT_TABLE = f"{PROJECT}.{DATASET}.Impact_Attendees_Recruitment_Target_List"
DEFAULT_DISCOVERY_VIEW = f"{PROJECT}.{DATASET}.v_discovery_reps_all_vintages"
DEFAULT_OUTPUT_DIR = Path("C:/Users/russe/Documents/Lead Scoring")

COLUMNS_TO_REMOVE = {
    "total_schwab_aum",
    "total_fidelity_aum",
    "total_pershing_aum",
    "total_tdameritrade_aum",
    "firm_has_schwab_relationship",
    "firm_has_fidelity_relationship",
    "firm_has_pershing_relationship",
    "firm_has_tdameritrade_relationship",
    "primary_territory_source",
    "TotalAssetsInMillions_1",
    "Number_IAReps_1",
    "AUMGrowthRate_1Year_1",
    "AUMGrowthRate_5Year_1",
    "DateBecameRep_NumberOfYears",
    "DateOfHireAtCurrentFirm_NumberOfYears",
    "NumberClients_Individuals_1",
    "NumberClients_HNWIndividuals_1",
    "NumberClients_RetirementPlans",
    "AssetsInMillions_Individuals_1",
    "AssetsInMillions_HNWIndividuals_1",
    "TotalAssets_SeparatelyManagedAccounts_1",
    "TotalAssets_PooledVehicles_1",
    "AssetsInMillions_MutualFunds",
    "AssetsInMillions_PrivateFunds",
    "AssetsInMillions_Equity_ExchangeTraded",
    "PercentClients_HNWIndividuals_1",
    "PercentClients_Individuals_1",
    "PercentAssets_HNWIndividuals_1",
    "PercentAssets_Individuals_1",
    "PercentAssets_MutualFunds",
    "PercentAssets_PrivateFunds",
    "PercentAssets_Equity_ExchangeTraded",
    "NumberFirmAssociations_1",
    "NumberRIAFirmAssociations_1",
    "Number_BranchAdvisors_1",
    "CustodianAUM_Fidelity_NationalFinancial",
    "CustodianAUM_Pershing",
    "CustodianAUM_Schwab",
    "CustodianAUM_TDAmeritrade",
    "Number_YearsPriorFirm1",
    "Number_YearsPriorFirm2",
    "Number_YearsPriorFirm3",
    "Number_YearsPriorFirm4",
    "KnownNonAdvisor_1",
    "DuallyRegisteredBDRIARep_1",
    "IsPrimaryRIAFirm",
    "Is_BreakawayRep",
    "Has_Insurance_License",
    "Is_NonProducer",
    "Is_IndependentContractor",
    "Is_Owner",
    "Office_USPS_Certified",
    "Home_USPS_Certified",
    "Custodian1",
    "Custodian2",
    "Custodian3",
    "Custodian4",
    "Custodian5",
    "FirstName",
    "LastName",
    "Title_1",
    "RIAFirmName_1",
    "Email_BusinessType_1",
    "Email_PersonalType_1",
    "SocialMedia_LinkedIn_1",
    "Has_LinkedIn",
    "PersonalWebpage_1",
    "FirmWebsite_1",
    "Brochure_Keywords",
    "Notes",
    "CustomKeywords",
    "Has_Series_7_1",
    "Has_Series_65_1",
    "Has_Series_66_1",
    "Has_Series_24_1",
    "Has_CFP_1",
    "Has_CFA_1",
    "Has_CIMA_1",
    "Has_AIF_1",
    "Has_Disclosure_1",
    "Has_Schwab_Relationship_1",
    "Has_Fidelity_Relationship_1",
    "Has_Pershing_Relationship_1",
    "Has_TDAmeritrade_Relationship_1",
    "Number_RegisteredStates",
    "Multi_Firm_Associations",
    "Multi_RIA_Relationships",
    "NumberFirmAssociations",
    "NumberRIAFirmAssociations",
    "Total_Prior_Firm_Years",
    "Number_Of_Prior_Firms",
    "Has_Disclosure",
    "Is_Known_Non_Advisor",
    "Has_Series_7",
    "Has_Series_65",
    "Has_Series_66",
    "Has_Series_24",
    "Has_CFP",
    "Has_CFA",
    "Has_CIMA",
    "Has_AIF",
    "Has_ETF_Focus",
    "Has_Private_Funds",
    "Has_Mutual_Fund_Focus",
    "Has_Schwab_Relationship",
    "Has_Fidelity_Relationship",
    "Has_Pershing_Relationship",
    "Has_TDAmeritrade_Relationship",
    "Is_Primary_RIA",
    "Is_Breakaway_Rep",
    "Is_Dually_Registered",
    "Is_Veteran_Advisor",
    "Is_New_To_Firm",
    "Is_Large_Firm",
    "Is_Boutique_Firm",
    "Has_Scale",
    "Remote_Work_Indicator",
    "Local_Advisor",
    "tgt_Branch_ZipCode",
    "tgt_DateBecameRep_NumberOfYears",
    "tgt_DateOfHireAtCurrentFirm_NumberOfYears",
    "tgt_AUMGrowthRate_1Year",
    "tgt_PercentAssets_HNWIndividuals",
    "tgt_PercentClients_HNWIndividuals",
    "Number_BranchAdvisors",
    "Accelerating_Growth",
    "Positive_Growth_Trajectory",
    "rep_FirstName",
    "rep_LastName",
    "Title",
    "Email_BusinessType",
    "Email_PersonalType",
    "SocialMedia_LinkedIn",
    "PersonalWebpage",
    "FirmWebsite",
    "Branch_City",
    "Branch_State",
    "Home_City",
    "Home_State",
    "Branch_County",
    "Home_County",
    "Branch_Longitude",
    "Branch_Latitude",
    "Home_Longitude",
    "Home_Latitude",
    "rep_processed_at",
    "snapshot_as_of",
    "territory_source",
    "dedup_rank",
    "total_reps",
    "total_records",
    "avg_clients_per_rep",
    "avg_hnw_clients_per_rep",
    "clients_per_rep",
    "hnw_clients_per_rep",
    "firm_growth_momentum",
    "firm_accelerating_growth",
    "firm_positive_growth_trajectory",
    "avg_firm_growth_1y",
    "avg_firm_growth_5y",
    "primary_state",
    "primary_metro_area",
    "primary_branch_state",
    "states_represented",
    "metro_areas_represented",
    "branch_states",
    "multi_state_firm",
    "multi_metro_firm",
    "single_state_firm",
    "national_firm",
    "firm_size_tier",
    "firm_boutique_flag",
    "firm_large_rep_flag",
    "breakaway_heavy_firm",
    "hybrid_firm",
    "pct_reps_with_series_7",
    "pct_reps_with_cfp",
    "pct_veteran_reps",
    "pct_breakaway_reps",
    "pct_dually_registered",
    "pct_primary_ria",
    "total_firm_clients",
    "total_firm_hnw_clients",
    "firm_processed_at",
    "total_firm_aum_millions",
    "avg_rep_aum_millions",
    "Rep_AUM_Tier",
    "Firm_AUM_Tier",
    "Rep_IAReps_Band",
    "Firm_Total_Reps_Band",
    "Rep_Growth_Bucket",
    "Firm_Growth_Bucket",
    "Territory_State",
    "Territory_City_Metro",
    "impact_row_id",
    "FilterDate_v12",
    "RIAFirmCRD_1",
    "AverageTenureAtPriorFirms",
    "NumberOfPriorFirms",
    "Licenses",
    "RegulatoryDisclosures_1",
    "Education",
    "Gender",
    "Branch_State_1",
    "Home_State_1",
    "Branch_City_1",
    "Home_City_1",
    "Branch_County_1",
    "Home_County_1",
    "Branch_ZipCode",
    "Home_ZipCode",
    "Branch_Longitude_1",
    "Branch_Latitude_1",
    "Home_Longitude_1",
    "Home_Latitude_1",
    "Branch_MetropolitanArea",
    "Home_MetropolitanArea",
    "MilesToWork",
}


# ---------------------------------------------------------------------------
# Dataclasses and utilities
# ---------------------------------------------------------------------------


@dataclass
class Artifacts:
    model_path: Path
    metadata_path: Path
    metadata: Dict


def get_latest_artifact(pattern: str, base_dir: Path) -> Optional[Path]:
    matches = sorted(base_dir.glob(pattern))
    return matches[-1] if matches else None


def load_artifacts(
    model_path: Optional[Path],
    metadata_path: Optional[Path],
    base_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Artifacts:
    if model_path is None:
        model_path = get_latest_artifact("v12_direct_xgboost_*.pkl", base_dir)
        if model_path is None:
            raise FileNotFoundError("No V12 model pickle found in output directory")
    if metadata_path is None:
        metadata_path = get_latest_artifact("v12_direct_metadata_*.json", base_dir)
        if metadata_path is None:
            raise FileNotFoundError("No V12 metadata json found in output directory")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return Artifacts(model_path=model_path, metadata_path=metadata_path, metadata=metadata)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score Impact attendees with V12 model")
    parser.add_argument("--project", default=PROJECT, help="BigQuery project ID")
    parser.add_argument("--impact-table", default=DEFAULT_IMPACT_TABLE, help="Source Impact attendee table")
    parser.add_argument("--discovery-view", default=DEFAULT_DISCOVERY_VIEW, help="Discovery snapshot view for enrichment")
    parser.add_argument("--as-of-date", default=None, help="As-of date (YYYY-MM-DD) for point-in-time snapshot selection")
    parser.add_argument("--model-path", default=None, help="Path to trained V12 model pickle")
    parser.add_argument("--metadata-path", default=None, help="Path to V12 metadata json")
    parser.add_argument("--output-csv", default=None, help="Optional CSV path for scored output")
    parser.add_argument("--output-bq-table", default=None, help="Optional destination BigQuery table for scores")
    parser.add_argument("--bq-write-disposition", default="WRITE_TRUNCATE", help="BigQuery write disposition (WRITE_APPEND, WRITE_TRUNCATE, WRITE_EMPTY)")
    parser.add_argument("--discovery-tier", choices=["t1", "t2", "t3", "view", "latest"], default="view",
                        help="Discovery snapshot source: staging tier (t1/t2/t3), combined latest (latest), or point-in-time view")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# BigQuery data extraction
# ---------------------------------------------------------------------------


def resolve_discovery_source(
    discovery_view: str,
    discovery_tier: str,
) -> Dict[str, str]:
    if discovery_tier == "view":
        return {"mode": "view", "table": discovery_view}
    if discovery_tier == "latest":
        return {"mode": "latest"}
    return {"mode": "staging", "table": f"{PROJECT}.{DATASET}.staging_discovery_{discovery_tier}"}


def fetch_impact_dataframe(
    client: bigquery.Client,
    impact_table: str,
    discovery_config: Dict[str, str],
    as_of_date: date,
) -> pd.DataFrame:
    if discovery_config["mode"] == "latest":
        query = f"""
        WITH impact AS (
            SELECT
                * REPLACE (SAFE_CAST(RepCRD AS STRING) AS RepCRD),
                ROW_NUMBER() OVER () AS impact_row_id,
                CAST(@as_of_date AS TIMESTAMP) AS FilterDate_v12
            FROM `{impact_table}`
            WHERE RepCRD IS NOT NULL
        ),
        latest_reps AS (
            SELECT *
            FROM (
                SELECT
                    reps.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY reps.RepCRD
                        ORDER BY reps.snapshot_at DESC
                    ) AS rn
                FROM `{PROJECT}.{DATASET}.v_discovery_reps_all_vintages` reps
            )
            WHERE rn = 1
        ),
        impact_with_snapshot AS (
            SELECT
                i.*,
                reps.* EXCEPT(RepCRD, snapshot_at, rn)
            FROM impact i
            LEFT JOIN latest_reps reps
                ON CAST(reps.RepCRD AS STRING) = i.RepCRD
        )
        SELECT * FROM impact_with_snapshot
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("as_of_date", "DATE", as_of_date),
            ],
        )
        return client.query(query, job_config=job_config).to_dataframe()

    discovery_table = client.get_table(discovery_config["table"])
    discovery_columns = {field.name.lower() for field in discovery_table.schema}
    has_snapshot = "snapshot_at" in discovery_columns

    reps_select = "reps.* EXCEPT(RepCRD, snapshot_at)" if has_snapshot else "reps.* EXCEPT(RepCRD)"
    snapshot_filter = "AND DATE(reps.snapshot_at) <= @as_of_date" if has_snapshot else ""
    qualify_clause = (
        """
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY i.impact_row_id
            ORDER BY reps.snapshot_at DESC NULLS LAST
        ) = 1
        """
        if has_snapshot
        else ""
    )

    query = f"""
    WITH impact AS (
        SELECT
            * REPLACE (SAFE_CAST(RepCRD AS STRING) AS RepCRD),
            ROW_NUMBER() OVER () AS impact_row_id,
            CAST(@as_of_date AS TIMESTAMP) AS FilterDate_v12
        FROM `{impact_table}`
        WHERE RepCRD IS NOT NULL
    ),
    impact_with_snapshot AS (
        SELECT
            i.*,
            {reps_select}
        FROM impact i
        LEFT JOIN `{discovery_config["table"]}` reps
            ON CAST(reps.RepCRD AS STRING) = i.RepCRD
            {snapshot_filter}
        {qualify_clause}
    )
    SELECT * FROM impact_with_snapshot
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("as_of_date", "DATE", as_of_date),
        ],
    )
    return client.query(query, job_config=job_config).to_dataframe()


def get_impact_columns(client: bigquery.Client, impact_table: str) -> List[str]:
    table = client.get_table(impact_table)
    return [field.name for field in table.schema]


# ---------------------------------------------------------------------------
# Feature engineering helpers (mirrors v12 training pipeline)
# ---------------------------------------------------------------------------


PII_TO_DROP = [
    "Home_ZipCode",
    "Branch_ZipCode",
    "Home_Latitude",
    "Home_Longitude",
    "Branch_Latitude",
    "Branch_Longitude",
    "Branch_City",
    "Home_City",
    "Branch_County",
    "Home_County",
    "RIAFirmName",
    "PersonalWebpage",
    "Notes",
    "Home_Zip_3Digit",
    "MilesToWork",
]

HIGH_CARDINALITY_TO_DROP = ["Home_MetropolitanArea"]

REDUNDANT_TENURE_TO_DROP = [
    "Number_YearsPriorFirm2",
    "Number_YearsPriorFirm3",
    "Number_YearsPriorFirm4",
]

MISSING_DATA_TO_DROP = [
    "TotalAssetsInMillions",
    "AUMGrowthRate_1Year",
    "AUMGrowthRate_5Year",
    "AssetsInMillions_Individuals",
    "AssetsInMillions_HNWIndividuals",
    "TotalAssets_SeparatelyManagedAccounts",
    "TotalAssets_PooledVehicles",
    "AssetsInMillions_MutualFunds",
    "AssetsInMillions_PrivateFunds",
    "AssetsInMillions_Equity_ExchangeTraded",
    "PercentClients_HNWIndividuals",
    "PercentClients_Individuals",
    "PercentAssets_HNWIndividuals",
    "PercentAssets_Individuals",
    "PercentAssets_MutualFunds",
    "PercentAssets_PrivateFunds",
    "PercentAssets_Equity_ExchangeTraded",
    "CustodianAUM_Fidelity_NationalFinancial",
    "CustodianAUM_Pershing",
    "CustodianAUM_Schwab",
    "CustodianAUM_TDAmeritrade",
    "NumberClients_Individuals",
    "NumberClients_HNWIndividuals",
    "AUM_per_Client_v12",
    "HNW_Concentration_v12",
]


TENURE_FEATURE_CONFIG = {
    "AverageTenureAtPriorFirms": {
        "bins": [0, 2, 5, 10, 100],
        "labels": ["Short_Under_2", "Moderate_2_to_5", "Long_5_to_10", "Very_Long_10_Plus"],
        "default": "No_Prior_Firms",
    },
    "Number_YearsPriorFirm1": {
        "bins": [0, 3, 7, 100],
        "labels": ["Short_Under_3", "Moderate_3_to_7", "Long_7_Plus"],
        "default": "No_Prior_Firm_1",
    },
    "Firm_Stability_Score_v12": {
        "bins": [0, 0.3, 0.6, 0.9, 10],
        "labels": ["Low_Under_30", "Moderate_30_to_60", "High_60_to_90", "Very_High_90_Plus"],
        "default": "Missing_Zero",
    },
}


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def get_series(df: pd.DataFrame, column: str, default=0) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series(default, index=df.index)


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["FilterDate_v12"] = pd.to_datetime(df.get("FilterDate_v12", datetime.utcnow()), errors="coerce")

    df["Multi_RIA_Relationships_v12"] = np.where(_safe_numeric(get_series(df, "NumberRIAFirmAssociations")).fillna(0) > 1, 1, 0)

    total_assets = _safe_numeric(get_series(df, "TotalAssetsInMillions")).astype("float64")
    num_clients = _safe_numeric(get_series(df, "NumberClients_Individuals")).astype("float64")
    mask_clients = num_clients > 0
    df["AUM_per_Client_v12"] = (total_assets / num_clients.where(mask_clients, np.nan)).fillna(0.0)

    num_hnw = _safe_numeric(get_series(df, "NumberClients_HNWIndividuals")).astype("float64")
    df["HNW_Concentration_v12"] = (num_hnw / num_clients.where(mask_clients, np.nan)).fillna(0.0)

    license_cols = ["Has_Series_7", "Has_Series_65", "Has_Series_66", "Has_Series_24"]
    df["license_count_v12"] = sum(_safe_numeric(get_series(df, col)).fillna(0) for col in license_cols)

    designation_cols = ["Has_CFP", "Has_CFA", "Has_CIMA", "Has_AIF"]
    df["designation_count_v12"] = sum(_safe_numeric(get_series(df, col)).fillna(0) for col in designation_cols)

    tenure_years = _safe_numeric(get_series(df, "DateBecameRep_NumberOfYears")).fillna(0)
    firm_years = _safe_numeric(get_series(df, "DateOfHireAtCurrentFirm_NumberOfYears")).fillna(0)
    df["Firm_Stability_Score_v12"] = np.where(tenure_years > 0, firm_years / tenure_years, 0)

    growth_1y = _safe_numeric(get_series(df, "AUMGrowthRate_1Year")).fillna(0)
    df["Positive_Growth_v12"] = np.where(growth_1y > 0.15, 1, 0)
    df["High_Growth_v12"] = np.where(growth_1y > 0.30, 1, 0)

    df["contact_dow"] = df["FilterDate_v12"].dt.dayofweek.fillna(0).astype(int)
    df["contact_month"] = df["FilterDate_v12"].dt.month.fillna(0).astype(int)
    df["contact_quarter"] = df["FilterDate_v12"].dt.quarter.fillna(0).astype(int)

    df["has_linkedin_v12"] = np.where(_safe_numeric(get_series(df, "Has_LinkedIn")).fillna(0) > 0, 1, 0)

    df["is_veteran_advisor_v12"] = np.where(tenure_years >= 20, 1, 0)
    df["is_new_to_firm_v12"] = np.where(firm_years < 1, 1, 0)

    num_states = _safe_numeric(get_series(df, "Number_RegisteredStates")).fillna(0)
    df["complex_registration_v12"] = np.where(num_states > 3, 1, 0)
    df["multi_state_registered_v12"] = np.where(num_states > 1, 1, 0)

    home_state = get_series(df, "Home_State", default=np.nan)
    branch_state = get_series(df, "Branch_State", default=np.nan)
    df["remote_work_indicator_v12"] = np.where(
        home_state.notna() & branch_state.notna() & (home_state != branch_state),
        1,
        0,
    )

    return df


def apply_feature_drops(df: pd.DataFrame) -> pd.DataFrame:
    drop_lists = [
        PII_TO_DROP,
        HIGH_CARDINALITY_TO_DROP,
        REDUNDANT_TENURE_TO_DROP,
        MISSING_DATA_TO_DROP,
    ]
    for drop_list in drop_lists:
        existing = [col for col in drop_list if col in df.columns]
        if existing:
            df = df.drop(columns=existing)
    return df


def bin_tenure_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for feat_name, cfg in TENURE_FEATURE_CONFIG.items():
        if feat_name not in df.columns:
            continue
        data = _safe_numeric(df[feat_name]).fillna(0)
        try:
            binned = pd.cut(
                data,
                bins=cfg["bins"],
                labels=cfg["labels"],
                include_lowest=True,
                duplicates="drop",
                right=True,
            )
            categories = list(cfg["labels"])
            if cfg["default"] not in binned.cat.categories:
                binned = binned.cat.add_categories([cfg["default"]])
            binned = binned.fillna(cfg["default"])
            base_col = f"{feat_name}_binned"
            df[base_col] = binned
            for label in categories + [cfg["default"]]:
                onehot_col = f"{base_col}_{label}"
                df[onehot_col] = (df[base_col] == label).astype(int)
        except Exception:
            continue
    return df


def encode_gender(df: pd.DataFrame) -> pd.DataFrame:
    if "Gender" not in df.columns:
        df["Gender_Male"] = 0
        df["Gender_Missing"] = 1
        return df
    gender = df["Gender"]
    df["Gender_Male"] = (gender == "Male").astype(int)
    df["Gender_Missing"] = gender.isna() | (~gender.isin(["Male", "Female"]))
    df["Gender_Missing"] = df["Gender_Missing"].astype(int)
    return df


def transform_label(value: str) -> str:
    return str(value)[:20].replace(" ", "_").replace("-", "_")


def encode_categoricals_from_metadata(
    df: pd.DataFrame,
    feature_names: Iterable[str],
    column: str,
) -> pd.DataFrame:
    df = df.copy()
    relevant = [feat for feat in feature_names if feat.startswith(f"{column}_")]
    if not relevant or column not in df.columns:
        return df

    transformed_col = df[column].astype(str).where(df[column].notna(), "")
    transformed_col = transformed_col.str[:20].str.replace(" ", "_").str.replace("-", "_")

    for feat in relevant:
        suffix = feat[len(column) + 1 :]
        df[feat] = (transformed_col == suffix).astype(int)

    return df


def prepare_feature_matrix(
    df: pd.DataFrame,
    feature_names: List[str],
) -> Tuple[pd.DataFrame, List[str]]:
    df = df.copy()
    missing_features = []
    for feat in feature_names:
        if feat not in df.columns:
            df[feat] = 0.0
            missing_features.append(feat)
        df[feat] = pd.to_numeric(df[feat], errors="coerce").fillna(0).astype(float)
    return df[feature_names], missing_features


# ---------------------------------------------------------------------------
# BigQuery write helper
# ---------------------------------------------------------------------------


def write_to_bigquery(
    client: bigquery.Client,
    df: pd.DataFrame,
    destination: str,
    write_disposition: str = "WRITE_TRUNCATE",
) -> None:
    job_config = bigquery.LoadJobConfig(write_disposition=write_disposition, autodetect=True)
    job = client.load_table_from_dataframe(df, destination, job_config=job_config)
    job.result()


# ---------------------------------------------------------------------------
# Main scoring routine
# ---------------------------------------------------------------------------


def score_impact_list(args: argparse.Namespace) -> None:
    as_of_date = (
        datetime.strptime(args.as_of_date, "%Y-%m-%d").date()
        if args.as_of_date
        else datetime.utcnow().date()
    )

    artifacts = load_artifacts(
        Path(args.model_path) if args.model_path else None,
        Path(args.metadata_path) if args.metadata_path else None,
    )
    feature_names = artifacts.metadata["features"]

    client = bigquery.Client(project=args.project)
    discovery_source = resolve_discovery_source(args.discovery_view, args.discovery_tier)
    print(f"[INFO] Using discovery source: {discovery_source}")
    df_raw = fetch_impact_dataframe(client, args.impact_table, discovery_source, as_of_date)
    impact_columns = get_impact_columns(client, args.impact_table)
    if df_raw.empty:
        print("[WARNING] Impact dataset query returned zero rows. Nothing to score.")
        return
    print(f"[INFO] Loaded {len(df_raw):,} Impact attendees (as-of {as_of_date})")

    df_features = add_engineered_features(df_raw)
    df_features = apply_feature_drops(df_features)
    df_features = bin_tenure_features(df_features)
    df_features = encode_gender(df_features)

    categorical_columns = ["Home_State", "Branch_State", "Office_State"]
    for col in categorical_columns:
        df_features = encode_categoricals_from_metadata(df_features, feature_names, col)

    feature_matrix, missing_features = prepare_feature_matrix(df_features, feature_names)
    if missing_features:
        print(f"[WARNING] {len(missing_features)} features missing from source data. Filled with zeros:")
        for feat in missing_features[:20]:
            print(f"  - {feat}")
        if len(missing_features) > 20:
            print(f"  ... and {len(missing_features) - 20} more")

    with open(artifacts.model_path, "rb") as f:
        model = pickle.load(f)

    print("[INFO] Scoring Impact attendees...")
    scores = model.predict_proba(feature_matrix.values)[:, 1]

    base_output = df_raw[impact_columns].copy()
    output_df = base_output.copy()
    output_df["v12_score"] = scores
    output_df["v12_score_generated_at"] = datetime.utcnow().isoformat()
    output_df["v12_model_used"] = artifacts.model_path.name
    output_df["v12_metadata_used"] = artifacts.metadata_path.name
    output_df["snapshot_as_of_date"] = as_of_date.isoformat()

    if args.output_csv:
        csv_path = Path(args.output_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        output_df.to_csv(csv_path, index=False)
        print(f"[OK] Scores exported to CSV: {csv_path}")

    if args.output_bq_table:
        write_to_bigquery(client, output_df, args.output_bq_table, args.bq_write_disposition)
        print(f"[OK] Scores written to BigQuery: {args.output_bq_table}")

    preview_cols = [col for col in ["impact_row_id", "RepCRD", "v12_score"] if col in output_df.columns]
    if preview_cols:
        print("[INFO] Preview of scored data:")
        print(output_df[preview_cols].head())
    else:
        print("[INFO] Preview columns not available after drop; skipped preview.")


def main() -> None:
    args = parse_args()
    score_impact_list(args)


if __name__ == "__main__":
    main()


