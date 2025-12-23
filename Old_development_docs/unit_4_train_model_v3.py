"""
Unit 4 V3: Model Training (No Pre-Filtering) (with m5 Feature Engineering)
Reads from BigQuery, applies m5 feature engineering, tests imbalance strategies, trains final models.
V3: Removes IV/VIF pre-filtering to allow all features for XGBoost's built-in feature selection.
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
BQ_TABLE = "savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2"  # V3 uses same dataset as V2
PROJECT_ID = "savvy-gtm-analytics"

print(f"[1/13] Loading configuration and feature schema...", flush=True)


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
    print(f"[2/13] Loading data from BigQuery table: {BQ_TABLE}...", flush=True)
    
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{BQ_TABLE}`'
    
    df = client.query(query).to_dataframe()
    print(f"   Loaded {len(df):,} rows, {len(df.columns)} columns", flush=True)
    
    return df



def create_m5_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create m5's 31 engineered features.
    This function replicates the feature engineering from FinalLeadScorePipeline.ipynb
    """
    print(f"[3/13] Creating m5 engineered features...", flush=True)
    
    df = df.copy()
    features_created = []
    
    # Helper function for safe division
    def safe_divide(numerator, denominator, default=np.nan):
        """Safely divide, handling zeros and NaNs"""
        if isinstance(denominator, pd.Series):
            # Replace 0 with NaN, then divide
            denominator_clean = denominator.replace(0, np.nan)
            result = numerator / denominator_clean
            return result.fillna(default)
        else:
            # Scalar case
            if pd.isna(denominator) or denominator == 0:
                return default
            return numerator / denominator
    
    # 1. Client efficiency metrics
    if "TotalAssetsInMillions" in df.columns:
        # Note: Some features may already exist from BigQuery (e.g., AUM_per_Client, AUM_Per_IARep)
        # We'll create them if they don't exist, or recompute if needed
        
        if "NumberClients_Individuals" in df.columns:
            if "AUM_per_Client" not in df.columns:
                df["AUM_per_Client"] = safe_divide(
                    df["TotalAssetsInMillions"], 
                    df["NumberClients_Individuals"].replace(0, np.nan)
                )
                features_created.append("AUM_per_Client")
        
        if "Number_Employees" in df.columns:
            if "AUM_per_Employee" not in df.columns:
                df["AUM_per_Employee"] = safe_divide(
                    df["TotalAssetsInMillions"],
                    df["Number_Employees"].replace(0, np.nan)
                )
                features_created.append("AUM_per_Employee")
        
        if "Number_IAReps" in df.columns:
            if "AUM_per_IARep" not in df.columns:
                df["AUM_per_IARep"] = safe_divide(
                    df["TotalAssetsInMillions"],
                    df["Number_IAReps"].replace(0, np.nan)
                )
                features_created.append("AUM_per_IARep")
    
    # 2. Growth momentum indicators
    if "AUMGrowthRate_1Year" in df.columns and "AUMGrowthRate_5Year" in df.columns:
        if "Growth_Momentum" not in df.columns:
            df["Growth_Momentum"] = (
                df["AUMGrowthRate_1Year"].fillna(0) * 
                df["AUMGrowthRate_5Year"].fillna(0)
            )
            features_created.append("Growth_Momentum")
        
        if "Growth_Acceleration" not in df.columns:
            df["Growth_Acceleration"] = (
                df["AUMGrowthRate_1Year"].fillna(0) - 
                (df["AUMGrowthRate_5Year"].fillna(0) / 5)
            )
            features_created.append("Growth_Acceleration")
    
    # 3. Firm stability and experience scores
    if "DateOfHireAtCurrentFirm_NumberOfYears" in df.columns:
        # Use Number_Of_Prior_Firms if available, otherwise compute from Number_YearsPriorFirm columns
        if "Number_Of_Prior_Firms" in df.columns:
            num_prior_firms = df["Number_Of_Prior_Firms"]
        else:
            # Count non-null prior firm years
            prior_firm_cols = [col for col in df.columns if col.startswith("Number_YearsPriorFirm")]
            if prior_firm_cols:
                num_prior_firms = df[prior_firm_cols].notna().sum(axis=1)
            else:
                num_prior_firms = pd.Series(0, index=df.index)
        
        if "Firm_Stability_Score" not in df.columns:
            df["Firm_Stability_Score"] = safe_divide(
                df["DateOfHireAtCurrentFirm_NumberOfYears"],
                (num_prior_firms + 1)
            )
            features_created.append("Firm_Stability_Score")
    
    if "DateBecameRep_NumberOfYears" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "Experience_Efficiency" not in df.columns:
            df["Experience_Efficiency"] = safe_divide(
                df["TotalAssetsInMillions"],
                (df["DateBecameRep_NumberOfYears"].replace(0, np.nan) + 1)
            )
            features_created.append("Experience_Efficiency")
    
    # 4. Client composition metrics
    if "NumberClients_HNWIndividuals" in df.columns and "NumberClients_Individuals" in df.columns:
        if "HNW_Client_Ratio" not in df.columns:
            df["HNW_Client_Ratio"] = safe_divide(
                df["NumberClients_HNWIndividuals"],
                df["NumberClients_Individuals"].replace(0, np.nan)
            )
            features_created.append("HNW_Client_Ratio")
    
    if "AssetsInMillions_HNWIndividuals" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "HNW_Asset_Concentration" not in df.columns:
            df["HNW_Asset_Concentration"] = safe_divide(
                df["AssetsInMillions_HNWIndividuals"],
                df["TotalAssetsInMillions"].replace(0, np.nan)
            )
            features_created.append("HNW_Asset_Concentration")
    
    # 5. Client focus metrics
    if "AssetsInMillions_Individuals" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "Individual_Asset_Ratio" not in df.columns:
            df["Individual_Asset_Ratio"] = safe_divide(
                df["AssetsInMillions_Individuals"],
                df["TotalAssetsInMillions"].replace(0, np.nan)
            )
            features_created.append("Individual_Asset_Ratio")
    
    if "AssetsInMillions_MutualFunds" in df.columns and "AssetsInMillions_PrivateFunds" in df.columns:
        if "Alternative_Investment_Focus" not in df.columns:
            df["Alternative_Investment_Focus"] = safe_divide(
                (df["AssetsInMillions_MutualFunds"].fillna(0) + 
                 df["AssetsInMillions_PrivateFunds"].fillna(0)),
                df["TotalAssetsInMillions"].replace(0, np.nan) if "TotalAssetsInMillions" in df.columns 
                else pd.Series(1, index=df.index)
            )
            features_created.append("Alternative_Investment_Focus")
    
    # 6. Scale and reach indicators
    if "Number_Employees" in df.columns:
        if "Is_Large_Firm" not in df.columns:
            df["Is_Large_Firm"] = (df["Number_Employees"] > 100).astype(int)
            features_created.append("Is_Large_Firm")
    
    # Is_Boutique_Firm requires AverageAccountSize which may not be in our dataset
    # Skip if not available
    if "Number_Employees" in df.columns and "AverageAccountSize" in df.columns:
        if "Is_Boutique_Firm" not in df.columns:
            q75 = df["AverageAccountSize"].quantile(0.75)
            df["Is_Boutique_Firm"] = (
                (df["Number_Employees"] <= 20) & 
                (df["AverageAccountSize"] > q75)
            ).astype(int)
            features_created.append("Is_Boutique_Firm")
    
    if "TotalAssetsInMillions" in df.columns:
        if "Has_Scale" not in df.columns:
            # Check if NumberClients_Individuals or Number_InvestmentAdvisoryClients exists
            if "NumberClients_Individuals" in df.columns:
                df["Has_Scale"] = (
                    (df["TotalAssetsInMillions"] > 500) | 
                    (df["NumberClients_Individuals"] > 100)
                ).astype(int)
            elif "Number_InvestmentAdvisoryClients" in df.columns:
                df["Has_Scale"] = (
                    (df["TotalAssetsInMillions"] > 500) | 
                    (df["Number_InvestmentAdvisoryClients"] > 100)
                ).astype(int)
            else:
                df["Has_Scale"] = (df["TotalAssetsInMillions"] > 500).astype(int)
            features_created.append("Has_Scale")
    
    # 7. Advisor tenure patterns
    if "DateOfHireAtCurrentFirm_NumberOfYears" in df.columns:
        if "Is_New_To_Firm" not in df.columns:
            df["Is_New_To_Firm"] = (df["DateOfHireAtCurrentFirm_NumberOfYears"] < 2).astype(int)
            features_created.append("Is_New_To_Firm")
    
    if "DateBecameRep_NumberOfYears" in df.columns:
        if "Is_Veteran_Advisor" not in df.columns:
            df["Is_Veteran_Advisor"] = (df["DateBecameRep_NumberOfYears"] > 10).astype(int)
            features_created.append("Is_Veteran_Advisor")
    
    # High_Turnover_Flag requires AverageTenureAtPriorFirms
    if "Number_Of_Prior_Firms" in df.columns:
        # Calculate average tenure if we have prior firm years
        prior_firm_cols = [col for col in df.columns if col.startswith("Number_YearsPriorFirm")]
        if prior_firm_cols:
            avg_tenure = df[prior_firm_cols].mean(axis=1)
            if "High_Turnover_Flag" not in df.columns:
                df["High_Turnover_Flag"] = (
                    (df["Number_Of_Prior_Firms"] > 3) & 
                    (avg_tenure < 3)
                ).astype(int)
                features_created.append("High_Turnover_Flag")
    
    # 8. Market positioning (requires AverageAccountSize and PercentClients_Individuals)
    if "AverageAccountSize" in df.columns and "PercentClients_Individuals" in df.columns:
        q75 = df["AverageAccountSize"].quantile(0.75)
        if "Premium_Positioning" not in df.columns:
            df["Premium_Positioning"] = (
                (df["AverageAccountSize"] > q75) &
                (df["PercentClients_Individuals"] < 50)
            ).astype(int)
            features_created.append("Premium_Positioning")
        
        median = df["AverageAccountSize"].median()
        if "Mass_Market_Focus" not in df.columns:
            df["Mass_Market_Focus"] = (
                (df["PercentClients_Individuals"] > 80) &
                (df["AverageAccountSize"] < median)
            ).astype(int)
            features_created.append("Mass_Market_Focus")
    
    # 9. Operational efficiency
    if "Number_InvestmentAdvisoryClients" in df.columns:
        if "Number_Employees" in df.columns:
            if "Clients_per_Employee" not in df.columns:
                df["Clients_per_Employee"] = safe_divide(
                    df["Number_InvestmentAdvisoryClients"],
                    df["Number_Employees"].replace(0, np.nan)
                )
                features_created.append("Clients_per_Employee")
        
        if "Number_IAReps" in df.columns:
            if "Clients_per_IARep" not in df.columns:
                df["Clients_per_IARep"] = safe_divide(
                    df["Number_InvestmentAdvisoryClients"],
                    df["Number_IAReps"].replace(0, np.nan)
                )
                features_created.append("Clients_per_IARep")
    
    if "Number_BranchAdvisors" in df.columns and "Number_Employees" in df.columns:
        if "Branch_Advisor_Density" not in df.columns:
            df["Branch_Advisor_Density"] = safe_divide(
                df["Number_BranchAdvisors"],
                df["Number_Employees"].replace(0, np.nan)
            )
            features_created.append("Branch_Advisor_Density")
    
    # 10. Geographic factors
    if "MilesToWork" in df.columns:
        if "Remote_Work_Indicator" not in df.columns:
            df["Remote_Work_Indicator"] = (df["MilesToWork"] > 50).astype(int)
            features_created.append("Remote_Work_Indicator")
        
        if "Local_Advisor" not in df.columns:
            df["Local_Advisor"] = (df["MilesToWork"] <= 10).astype(int)
            features_created.append("Local_Advisor")
    
    # 11. Firm relationship indicators
    if "NumberRIAFirmAssociations" in df.columns:
        if "Multi_RIA_Relationships" not in df.columns:
            df["Multi_RIA_Relationships"] = (df["NumberRIAFirmAssociations"] > 1).astype(int)
            features_created.append("Multi_RIA_Relationships")
    
    if "NumberFirmAssociations" in df.columns and "NumberRIAFirmAssociations" in df.columns:
        if "Complex_Registration" not in df.columns:
            df["Complex_Registration"] = (
                (df["NumberFirmAssociations"] > 2) | 
                (df["NumberRIAFirmAssociations"] > 1)
            ).astype(int)
            features_created.append("Complex_Registration")
    
    # 12. US focus (requires Percent_ClientsUS)
    if "Percent_ClientsUS" in df.columns:
        if "Primarily_US_Clients" not in df.columns:
            df["Primarily_US_Clients"] = (df["Percent_ClientsUS"] > 90).astype(int)
            features_created.append("Primarily_US_Clients")
        
        if "International_Presence" not in df.columns:
            df["International_Presence"] = (df["Percent_ClientsUS"] < 80).astype(int)
            features_created.append("International_Presence")
    
    # 13. Composite quality score (requires several features)
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
    
    if len(quality_score_components) >= 3:  # Need at least 3 components
        if "Quality_Score" not in df.columns:
            quality_score = pd.Series(0.0, index=df.index)
            for component in quality_score_components:
                if len(component) == 2:
                    feat_name, weight = component
                    if feat_name in df.columns:
                        # Convert to numeric if string/object type
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
    
    # 14. Growth trajectory indicator
    if "AUMGrowthRate_1Year" in df.columns and "AUMGrowthRate_5Year" in df.columns:
        if "Positive_Growth_Trajectory" not in df.columns:
            df["Positive_Growth_Trajectory"] = (
                (df["AUMGrowthRate_1Year"] > 0) & 
                (df["AUMGrowthRate_5Year"] > 0)
            ).astype(int)
            features_created.append("Positive_Growth_Trajectory")
    
    # Accelerating_Growth (may already exist from discovery_reps_current)
    if "AUMGrowthRate_1Year" in df.columns and "AUMGrowthRate_5Year" in df.columns:
        if "Accelerating_Growth" not in df.columns:
            df["Accelerating_Growth"] = (
                df["AUMGrowthRate_1Year"] > (df["AUMGrowthRate_5Year"] / 5)
            ).astype(int)
            features_created.append("Accelerating_Growth")
    
    print(f"   Created {len(features_created)} m5 engineered features: {', '.join(features_created[:10])}{'...' if len(features_created) > 10 else ''}", flush=True)
    
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
    """Get list of feature columns from schema, including m5 engineered features"""
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
    
    # Add m5 engineered features (if they exist in df but not in schema)
    m5_features = [
        "AUM_per_Client", "AUM_per_Employee", "AUM_per_IARep",
        "Growth_Momentum", "Growth_Acceleration",
        "Firm_Stability_Score", "Experience_Efficiency",
        "HNW_Client_Ratio", "HNW_Asset_Concentration",
        "Individual_Asset_Ratio", "Alternative_Investment_Focus",
        "Is_Large_Firm", "Is_Boutique_Firm", "Has_Scale",
        "Is_New_To_Firm", "Is_Veteran_Advisor", "High_Turnover_Flag",
        "Premium_Positioning", "Mass_Market_Focus",
        "Clients_per_Employee", "Branch_Advisor_Density", "Clients_per_IARep",
        "Remote_Work_Indicator", "Local_Advisor",
        "Multi_RIA_Relationships", "Complex_Registration",
        "Primarily_US_Clients", "International_Presence",
        "Quality_Score", "Positive_Growth_Trajectory", "Accelerating_Growth"
    ]
    
    for m5_feat in m5_features:
        if m5_feat in df.columns and m5_feat not in base_features:
            base_features.append(m5_feat)
    
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
    """Cast object dtype columns to category for XGBoost, handling edge cases
    
    When enable_categorical=True, XGBoost requires ALL non-numeric columns to be category dtype.
    This function converts ALL object columns to category, handling edge cases.
    """
    for c in columns:
        if c in df.columns and df[c].dtype == "object":
            try:
                # First, handle NaN values - fill with placeholder before conversion
                # This ensures we always have at least one category
                has_nan = df[c].isna().any()
                if has_nan:
                    # Fill NaN with placeholder, convert, then add placeholder as valid category
                    df[c] = df[c].fillna("__MISSING__").astype("category")
                    # Ensure __MISSING__ is in categories
                    if "__MISSING__" not in df[c].cat.categories:
                        df[c] = df[c].cat.add_categories(["__MISSING__"])
                else:
                    # No NaN, convert directly
                    df[c] = df[c].astype("category")
                
                # Verify the conversion created valid categories
                cat_categories = df[c].cat.categories
                if len(cat_categories) == 0:
                    # Empty categories - this shouldn't happen but handle it
                    # Add a placeholder category
                    df[c] = df[c].cat.add_categories(["__MISSING__"])
                    df[c] = df[c].fillna("__MISSING__")
            except Exception as e:
                # If conversion fails, try filling all values first
                try:
                    # Fill any NaN with placeholder, then convert
                    df[c] = df[c].fillna("__MISSING__").astype("category")
                    if "__MISSING__" not in df[c].cat.categories:
                        df[c] = df[c].cat.add_categories(["__MISSING__"])
                except Exception:
                    # Last resort: convert to string first, then category
                    df[c] = df[c].astype(str).fillna("__MISSING__").astype("category")


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
    V3: NO PRE-FILTERING - Return all features and let XGBoost handle feature selection.
    Returns: (kept_features, filter_report)
    """
    # V3: Skip IV and VIF filtering - trust XGBoost to handle all features
    filter_report = {
        "iv_scores": {},
        "vif_scores": {},
        "removed_iv": [],
        "removed_vif": [],
        "note": "V3: No pre-filtering applied - using all features"
    }
    
    # Return all features that exist in the dataframe
    kept_features = [c for c in feature_cols if c in train_df.columns]
    
    return sorted(kept_features), filter_report


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
        
        # V3: Check if we have categorical/string features - SMOTE can't handle them
        import pandas.api.types as pd_types
        has_categorical = any(
            X_train[col].dtype == 'object' or 
            pd_types.is_categorical_dtype(X_train[col])
            for col in X_train.columns
        )
        
        if has_categorical:
            # Skip SMOTE for V3 (has categorical features), fall back to scale_pos_weight
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
            try:
                model.fit(X_train, y_train)
            except (ValueError, TypeError) as e:
                # If categorical conversion fails, convert problematic columns back to object
                if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
                    # Find and fix problematic categorical columns
                    for col in X_train.columns:
                        if pd.api.types.is_categorical_dtype(X_train[col]):
                            if len(X_train[col].cat.categories) == 0:
                                X_train[col] = X_train[col].astype("object")
                                X_valid[col] = X_valid[col].astype("object")
                    # Retry fitting
                    model.fit(X_train, y_train)
                else:
                    raise
            
            preds = model.predict_proba(X_valid)[:, 1]
            return {
                "strategy": "smote_skipped_categorical",
                "aucpr": float(average_precision_score(y_valid, preds)),
                "aucroc": float(roc_auc_score(y_valid, preds)),
                "model": model
            }
        
        try:
            sampler = SMOTE(sampling_strategy=0.1, random_state=seed, k_neighbors=min(5, (y_train == 1).sum() - 1))
            X_res, y_res = sampler.fit_resample(X_train, y_train)
        except Exception as e:
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
            try:
                model.fit(X_train, y_train)
            except (ValueError, TypeError) as e:
                # If categorical conversion fails, convert problematic columns back to object
                if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
                    # Find and fix problematic categorical columns
                    for col in X_train.columns:
                        if pd.api.types.is_categorical_dtype(X_train[col]):
                            if len(X_train[col].cat.categories) == 0:
                                X_train[col] = X_train[col].astype("object")
                                X_valid[col] = X_valid[col].astype("object")
                    # Retry fitting
                    model.fit(X_train, y_train)
                else:
                    raise
            
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
        try:
            model.fit(X_res, y_res)
        except (ValueError, TypeError) as e:
            # If categorical conversion fails, convert problematic columns back to object
            if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
                # Find and fix problematic categorical columns
                for col in X_res.columns:
                    if pd.api.types.is_categorical_dtype(X_res[col]):
                        if len(X_res[col].cat.categories) == 0:
                            X_res[col] = X_res[col].astype("object")
                # Retry fitting
                model.fit(X_res, y_res)
            else:
                raise
        
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
        try:
            model.fit(X_train, y_train)
        except (ValueError, TypeError) as e:
            # If categorical conversion fails, convert problematic columns back to object
            if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
                # Find and fix problematic categorical columns
                for col in X_train.columns:
                    if pd.api.types.is_categorical_dtype(X_train[col]):
                        if len(X_train[col].cat.categories) == 0:
                            X_train[col] = X_train[col].astype("object")
                            X_valid[col] = X_valid[col].astype("object")
                # Retry fitting
                model.fit(X_train, y_train)
            else:
                raise
    
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
        print(f"[11/13] Computing SHAP values using TreeExplainer...", flush=True)
        
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
    print("Unit 4 V3: Model Training (No Pre-Filtering)")
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
    
    
    # Create m5 engineered features
    df = create_m5_engineered_features(df)
    # Verify temporal features exist
    if "Day_of_Contact" not in df.columns or "Is_Weekend_Contact" not in df.columns:
        print("WARNING: Temporal features missing, deriving from Stage_Entered_Contacting__c...", flush=True)
        ts = pd.to_datetime(df["Stage_Entered_Contacting__c"], errors="coerce", utc=True)
        df["Day_of_Contact"] = ts.dt.dayofweek + 1  # 1=Monday, 7=Sunday
        df["Is_Weekend_Contact"] = df["Day_of_Contact"].isin([6, 7]).astype(int)
    
    # Validate schema
    print(f"[4/13] Validating data against feature schema...", flush=True)
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
    print(f"[5/13] Preparing data types...", flush=True)
    cast_categoricals_inplace(df, feature_cols)
    
    # Set up time column and target
    time_col = "Stage_Entered_Contacting__c"
    y_col = "target_label"
    
    # Create CV folds
    print(f"[6/13] Creating blocked time-series CV folds (n_folds={cv_folds}, gap={gap_days} days)...", flush=True)
    folds = blocked_time_series_folds(df, n_folds=cv_folds, gap_days=gap_days, time_col=time_col, seed=seed)
    print(f"   Created {len(folds)} folds", flush=True)
    
    # Store CV fold indices
    cv_indices = []
    all_filter_reports = []
    cv_metrics = []
    
    # Cross-validation loop (V3: No pre-filtering, using all features)
    print(f"[7/13] Running cross-validation with strategy testing (V3: All features, no pre-filtering)...", flush=True)
    
    for fold_id, (train_idx, test_idx) in enumerate(folds):
        print(f"   Fold {fold_id + 1}/{len(folds)}: train={len(train_idx):,}, test={len(test_idx):,}", flush=True)
        
        train_df = df.iloc[train_idx].reset_index(drop=True).copy()
        test_df = df.iloc[test_idx].reset_index(drop=True).copy()
        
        if len(train_df) == 0 or len(test_df) == 0:
            print(f"      Skipping fold (empty train/test)", flush=True)
            continue
        
        # V3: No pre-filtering - use all features
        kept_features, filter_report = apply_prefilters(train_df, feature_cols, y_col="target_label")
        filter_report["fold"] = fold_id
        filter_report["kept_count"] = len(kept_features)
        all_filter_reports.append(filter_report)
        
        print(f"      V3 (No pre-filtering): using {len(kept_features)}/{len(feature_cols)} features", flush=True)
        
        # Prepare data
        X_train = train_df[kept_features].copy()
        y_train = train_df[y_col].astype(int)
        X_valid = test_df[kept_features].copy()
        y_valid = test_df[y_col].astype(int)
        
        # V3: Cast categoricals for XGBoost (before SMOTE check)
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
    print(f"[8/13] Winning strategy: {winning_strategy} (wins: spw={spw_wins}, smote={smote_wins})", flush=True)
    
    # V3: No pre-filtering - use all features
    print(f"[9/13] Preparing full dataset (V3: Using all features, no pre-filtering)...", flush=True)
    final_kept_features, final_filter_report = apply_prefilters(df, feature_cols, y_col="target_label")
    print(f"   Final features: {len(final_kept_features)}/{len(feature_cols)}", flush=True)
    
    # Prepare final training data
    X_all = df[final_kept_features].copy()
    y_all = df[y_col].astype(int)
    cast_categoricals_inplace(X_all, final_kept_features)
    
    # Train final XGBoost model
    print(f"[10/13] Training final XGBoost model with {winning_strategy}...", flush=True)
    
    if winning_strategy == "smote":
        try:
            sampler = SMOTE(sampling_strategy=0.1, random_state=seed, k_neighbors=min(5, (y_all == 1).sum() - 1))
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
            try:
                final_model.fit(X_res, y_res)
            except (ValueError, TypeError) as e2:
                # If categorical conversion fails, convert problematic columns back to object
                if "cannot call `vectorize`" in str(e2) or "size 0" in str(e2):
                    # Find and fix problematic categorical columns
                    for col in X_res.columns:
                        if pd.api.types.is_categorical_dtype(X_res[col]):
                            if len(X_res[col].cat.categories) == 0:
                                X_res[col] = X_res[col].astype("object")
                    # Retry fitting
                    final_model.fit(X_res, y_res)
                else:
                    raise
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
            try:
                final_model.fit(X_all, y_all)
            except (ValueError, TypeError) as e2:
                # If categorical conversion fails, convert problematic columns back to object
                if "cannot call `vectorize`" in str(e2) or "size 0" in str(e2):
                    # Find and fix problematic categorical columns
                    for col in X_all.columns:
                        if pd.api.types.is_categorical_dtype(X_all[col]):
                            if len(X_all[col].cat.categories) == 0:
                                X_all[col] = X_all[col].astype("object")
                    # Retry fitting
                    final_model.fit(X_all, y_all)
                else:
                    raise
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
        try:
            final_model.fit(X_all, y_all)
        except (ValueError, TypeError) as e:
            # If categorical conversion fails, convert problematic columns back to object
            if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
                # Find and fix problematic categorical columns
                for col in X_all.columns:
                    if pd.api.types.is_categorical_dtype(X_all[col]):
                        if len(X_all[col].cat.categories) == 0:
                            X_all[col] = X_all[col].astype("object")
                # Retry fitting
                final_model.fit(X_all, y_all)
            else:
                raise
    
    # Verify NULL handling
    print(f"   Verifying NULL value handling...", flush=True)
    preds_sample = final_model.predict_proba(X_all.head(100))[:, 1]
    print(f"   Predictions generated successfully (sample mean: {preds_sample.mean():.4f})", flush=True)
    
    # Train baseline Logistic Regression
    print(f"[11/13] Training baseline Logistic Regression model...", flush=True)
    baseline_model = train_baseline_logistic(X_all, y_all, seed)
    
    # Save models
    print(f"[12/13] Saving models and artifacts...", flush=True)
    joblib.dump(final_model, ARTIFACTS_DIR / "model_v3.pkl")
    joblib.dump(baseline_model, ARTIFACTS_DIR / "model_v3_baseline_logit.pkl")
    
    # Save CV fold indices
    with open(ARTIFACTS_DIR / "cv_fold_indices_v3.json", "w", encoding="utf-8") as f:
        json.dump(cv_indices, f, indent=2)
    
    # Save selected features
    with open(ARTIFACTS_DIR / "selected_features_v3.json", "w", encoding="utf-8") as f:
        json.dump(final_kept_features, f, indent=2)
    
    # Generate feature importance
    print(f"[13/13] Generating feature importance...", flush=True)
    importance_df = generate_shap_importance(final_model, X_all, final_kept_features)
    importance_df.to_csv(ARTIFACTS_DIR / "feature_importance_v3.csv", index=False)
    
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
    with open(ARTIFACTS_DIR / "feature_selection_report_v3.md", "w", encoding="utf-8") as f:
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
    with open(ARTIFACTS_DIR / "model_training_report_v3.md", "w", encoding="utf-8") as f:
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
    print("Unit 4 V3 Training Complete!")
    print("=" * 80)
    print()
    print("Artifacts created:")
    print(f"  - model_v3.pkl")
    print(f"  - model_v3_baseline_logit.pkl")
    print(f"  - cv_fold_indices_v3.json")
    print(f"  - feature_importance_v3.csv")
    print(f"  - feature_selection_report_v3.md")
    print(f"  - model_training_report_v3.md")
    print(f"  - selected_features_v3.json")
    print()
    print(f"Final Model Performance:")
    print(f"  XGBoost AUC-PR: {final_aucpr:.4f}")
    print(f"  Baseline AUC-PR: {baseline_aucpr:.4f}")
    print(f"  Improvement: {((final_aucpr - baseline_aucpr) / baseline_aucpr * 100):.1f}%")
    print()


if __name__ == "__main__":
    main()

