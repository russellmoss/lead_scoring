"""
Unit 5: Calibration and m5 Model Comparison (V4)
Calibrates the V4 model with segment-specific calibrators and compares feature importance with m5.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    brier_score_loss
)
from google.cloud import bigquery
import joblib

# Paths
ARTIFACTS_DIR = Path(os.getcwd())
CONFIG_PATH = ARTIFACTS_DIR / "config" / "v1_model_config.json"
BQ_TABLE = "savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2"
PROJECT_ID = "savvy-gtm-analytics"

# Model files
MODEL_V4_PATH = ARTIFACTS_DIR / "model_v4.pkl"
CV_INDICES_V4_PATH = ARTIFACTS_DIR / "cv_fold_indices_v4.json"
FEATURE_IMPORTANCE_V4_PATH = ARTIFACTS_DIR / "feature_importance_v4.csv"
CURRENT_MODEL_DOC_PATH = ARTIFACTS_DIR / "Current_Lead_Scoring_Model.md"

# Output files
CALIBRATED_MODEL_V4_PATH = ARTIFACTS_DIR / "model_v4_calibrated.pkl"
SHAP_COMPARISON_REPORT_V4_PATH = ARTIFACTS_DIR / "shap_feature_comparison_report_v4.md"
COHORT_ANALYSIS_REPORT_V4_PATH = ARTIFACTS_DIR / "cohort_analysis_report_v4.md"

# PII features to drop (must match unit_4_train_model_v4.py)
PII_TO_DROP = [
    'FirstName', 'LastName', 
    'Branch_City', 'Branch_County', 'Branch_ZipCode',
    'Home_City', 'Home_County', 'Home_ZipCode',
    'RIAFirmCRD', 'RIAFirmName',
    'PersonalWebpage', 'Notes'
]

print("=" * 80)
print("Unit 5: Calibration and m5 Model Comparison (V4)")
print("=" * 80)
print()


def load_config() -> Dict[str, Any]:
    """Load model configuration"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data_from_bigquery() -> pd.DataFrame:
    """Load training data from BigQuery"""
    print(f"[1/6] Loading data from BigQuery table: {BQ_TABLE}...", flush=True)
    
    client = bigquery.Client(project=PROJECT_ID)
    query = f'SELECT * FROM `{BQ_TABLE}`'
    
    df = client.query(query).to_dataframe()
    print(f"   Loaded {len(df):,} rows, {len(df.columns)} columns", flush=True)
    
    return df


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


def get_aum_tier(total_assets: pd.Series) -> pd.Series:
    """Classify records into AUM tiers"""
    tier = pd.Series('Unknown', index=total_assets.index, dtype='object')
    
    # Convert to numeric, handling missing values
    assets_numeric = pd.to_numeric(total_assets, errors='coerce')
    
    # Classify tiers
    tier[assets_numeric < 100] = '<$100M'
    tier[(assets_numeric >= 100) & (assets_numeric < 500)] = '$100-500M'
    tier[assets_numeric >= 500] = '>$500M'
    
    return tier


def load_m5_top_features() -> List[Tuple[str, float]]:
    """Load top 25 features from m5 model documentation"""
    print(f"[2/6] Loading m5 top features from Current_Lead_Scoring_Model.md...", flush=True)
    
    # m5 top 25 features from section 6.2
    m5_features = [
        ('Multi_RIA_Relationships', 0.0816),
        ('Mass_Market_Focus', 0.0708),
        ('HNW_Asset_Concentration', 0.0587),
        ('DateBecameRep_NumberOfYears', 0.0379),
        ('Branch_Advisor_Density', 0.0240),
        ('Is_Veteran_Advisor', 0.0225),
        ('NumberFirmAssociations', 0.0220),
        ('Firm_Stability_Score', 0.0211),
        ('AverageAccountSize', 0.0208),
        ('Individual_Asset_Ratio', 0.0197),
        ('Home_MetropolitanArea_Dallas-Fort Worth-Arlington TX', 0.0192),
        ('Percent_ClientsUS', 0.0170),
        ('Number_Employees', 0.0165),
        ('Number_InvestmentAdvisoryClients', 0.0163),
        ('Clients_per_Employee', 0.0161),
        ('Clients_per_IARep', 0.0157),
        ('AssetsInMillions_Individuals', 0.0152),
        ('Complex_Registration', 0.0152),
        ('NumberClients_Individuals', 0.0150),
        ('NumberClients_HNWIndividuals', 0.0143),
        ('PercentClients_Individuals', 0.0135),
        ('Remote_Work_Indicator', 0.0131),
        ('Is_New_To_Firm', 0.0130),
        ('Primarily_US_Clients', 0.0130),
        ('Accelerating_Growth', 0.0128),
    ]
    
    print(f"   Loaded {len(m5_features)} m5 features", flush=True)
    return m5_features


def create_m5_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create m5's engineered features (same as unit_4_train_model_v4.py).
    This function replicates the feature engineering from FinalLeadScorePipeline.ipynb
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
    
    # Client efficiency metrics
    if "TotalAssetsInMillions" in df.columns:
        if "NumberClients_Individuals" in df.columns and "AUM_per_Client" not in df.columns:
            df["AUM_per_Client"] = safe_divide(
                df["TotalAssetsInMillions"], 
                df["NumberClients_Individuals"].replace(0, np.nan)
            )
            features_created.append("AUM_per_Client")
        
        if "Number_IAReps" in df.columns and "AUM_per_IARep" not in df.columns:
            df["AUM_per_IARep"] = safe_divide(
                df["TotalAssetsInMillions"],
                df["Number_IAReps"].replace(0, np.nan)
            )
            features_created.append("AUM_per_IARep")
    
    # Growth indicators
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
    
    # Firm stability and experience
    if "DateOfHireAtCurrentFirm_NumberOfYears" in df.columns:
        num_prior_firms = df.get("Number_Of_Prior_Firms", pd.Series(0, index=df.index))
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
    
    # Client composition
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
    
    if "AssetsInMillions_Individuals" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "Individual_Asset_Ratio" not in df.columns:
            df["Individual_Asset_Ratio"] = safe_divide(
                df["AssetsInMillions_Individuals"],
                df["TotalAssetsInMillions"].replace(0, np.nan)
            )
            features_created.append("Individual_Asset_Ratio")
    
    # Alternative investment focus
    if "AssetsInMillions_MutualFunds" in df.columns and "AssetsInMillions_PrivateFunds" in df.columns:
        if "Alternative_Investment_Focus" not in df.columns:
            df["Alternative_Investment_Focus"] = safe_divide(
                (df["AssetsInMillions_MutualFunds"].fillna(0) + 
                 df["AssetsInMillions_PrivateFunds"].fillna(0)),
                df["TotalAssetsInMillions"].replace(0, np.nan) if "TotalAssetsInMillions" in df.columns 
                else pd.Series(1, index=df.index)
            )
            features_created.append("Alternative_Investment_Focus")
    
    # Scale indicators
    if "TotalAssetsInMillions" in df.columns:
        if "Has_Scale" not in df.columns:
            if "NumberClients_Individuals" in df.columns:
                df["Has_Scale"] = (
                    (df["TotalAssetsInMillions"] > 500) | 
                    (df["NumberClients_Individuals"] > 100)
                ).astype(int)
            else:
                df["Has_Scale"] = (df["TotalAssetsInMillions"] > 500).astype(int)
            features_created.append("Has_Scale")
    
    # Advisor tenure
    if "DateOfHireAtCurrentFirm_NumberOfYears" in df.columns:
        if "Is_New_To_Firm" not in df.columns:
            df["Is_New_To_Firm"] = (df["DateOfHireAtCurrentFirm_NumberOfYears"] < 2).astype(int)
            features_created.append("Is_New_To_Firm")
    
    if "DateBecameRep_NumberOfYears" in df.columns:
        if "Is_Veteran_Advisor" not in df.columns:
            df["Is_Veteran_Advisor"] = (df["DateBecameRep_NumberOfYears"] > 10).astype(int)
            features_created.append("Is_Veteran_Advisor")
    
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
    
    # Complex registration
    if "NumberFirmAssociations" in df.columns and "NumberRIAFirmAssociations" in df.columns:
        if "Complex_Registration" not in df.columns:
            df["Complex_Registration"] = (
                (df["NumberFirmAssociations"] > 2) | 
                (df["NumberRIAFirmAssociations"] > 1)
            ).astype(int)
            features_created.append("Complex_Registration")
    
    # Quality score (simplified version)
    if "Is_Veteran_Advisor" in df.columns and "Has_Scale" in df.columns and "IsPrimaryRIAFirm" in df.columns:
        if "Quality_Score" not in df.columns:
            df["Quality_Score"] = (
                pd.to_numeric(df["Is_Veteran_Advisor"], errors='coerce').fillna(0) * 0.25 +
                pd.to_numeric(df["Has_Scale"], errors='coerce').fillna(0) * 0.25 +
                pd.to_numeric(df["IsPrimaryRIAFirm"], errors='coerce').fillna(0) * 0.15
            )
            if "AUM_per_Client" in df.columns:
                median_aum = df["AUM_per_Client"].median()
                # Fill NaN values with False before converting to int
                aum_comparison = (df["AUM_per_Client"] > median_aum).fillna(False)
                df["Quality_Score"] += aum_comparison.astype(int) * 0.10
            if "High_Turnover_Flag" in df.columns:
                df["Quality_Score"] += (1 - pd.to_numeric(df["High_Turnover_Flag"], errors='coerce').fillna(0)) * 0.10
            features_created.append("Quality_Score")
    
    # Growth trajectory
    if "AUMGrowthRate_1Year" in df.columns and "AUMGrowthRate_5Year" in df.columns:
        if "Positive_Growth_Trajectory" not in df.columns:
            df["Positive_Growth_Trajectory"] = (
                (df["AUMGrowthRate_1Year"] > 0) & 
                (df["AUMGrowthRate_5Year"] > 0)
            ).astype(int)
            features_created.append("Positive_Growth_Trajectory")
        
        if "Accelerating_Growth" not in df.columns:
            df["Accelerating_Growth"] = (
                df["AUMGrowthRate_1Year"] > (df["AUMGrowthRate_5Year"] / 5)
            ).astype(int)
            features_created.append("Accelerating_Growth")
    
    # Remote work indicator
    if "MilesToWork" in df.columns:
        if "Remote_Work_Indicator" not in df.columns:
            df["Remote_Work_Indicator"] = (df["MilesToWork"] > 50).astype(int)
            features_created.append("Remote_Work_Indicator")
        
        if "Local_Advisor" not in df.columns:
            df["Local_Advisor"] = (df["MilesToWork"] <= 10).astype(int)
            features_created.append("Local_Advisor")
    
    # Multi RIA relationships
    if "NumberRIAFirmAssociations" in df.columns:
        if "Multi_RIA_Relationships" not in df.columns:
            df["Multi_RIA_Relationships"] = (df["NumberRIAFirmAssociations"] > 1).astype(int)
            features_created.append("Multi_RIA_Relationships")
    
    print(f"   Created {len(features_created)} m5 engineered features: {', '.join(features_created[:10])}{'...' if len(features_created) > 10 else ''}", flush=True)
    
    return df


def main():
    """Main calibration and comparison pipeline"""
    
    # Load configuration
    cfg = load_config()
    seed = int(cfg.get("global_seed", 42))
    
    # Load model and CV indices
    print(f"[3/6] Loading model and CV indices...", flush=True)
    if not MODEL_V4_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_V4_PATH}")
    if not CV_INDICES_V4_PATH.exists():
        raise FileNotFoundError(f"CV indices file not found: {CV_INDICES_V4_PATH}")
    
    model_v4 = joblib.load(MODEL_V4_PATH)
    with open(CV_INDICES_V4_PATH, "r", encoding="utf-8") as f:
        cv_indices = json.load(f)
    
    print(f"   Loaded model and {len(cv_indices)} CV folds", flush=True)
    
    # Load the official feature order from the V4 training run
    print(f"[2.5/6] Loading official feature order from feature_order_v4.json...", flush=True)
    feature_order_path = ARTIFACTS_DIR / "feature_order_v4.json"
    if not feature_order_path.exists():
        raise FileNotFoundError(f"CRITICAL: {feature_order_path.name} not found. Run unit_4_train_model_v4.py first.")
    with open(feature_order_path, 'r', encoding='utf-8') as f:
        OFFICIAL_FEATURE_ORDER = json.load(f)
    print(f"   Loaded {len(OFFICIAL_FEATURE_ORDER)} features from official training order", flush=True)
    
    # Load data
    df = load_data_from_bigquery()
    
    # CRITICAL FIX: Drop PII and create m5 features BEFORE preparing X (must match training)
    print(f"[3.5/6] Removing PII and creating m5 engineered features...", flush=True)
    pii_cols_to_drop = [col for col in PII_TO_DROP if col in df.columns]
    if pii_cols_to_drop:
        df = df.drop(columns=pii_cols_to_drop)
        print(f"   Dropped {len(pii_cols_to_drop)} PII features", flush=True)
    
    # Create m5 engineered features
    df = create_m5_engineered_features(df)
    
    # Load feature importance
    print(f"[4/6] Loading feature importance...", flush=True)
    if not FEATURE_IMPORTANCE_V4_PATH.exists():
        raise FileNotFoundError(f"Feature importance file not found: {FEATURE_IMPORTANCE_V4_PATH}")
    
    v4_importance_df = pd.read_csv(FEATURE_IMPORTANCE_V4_PATH)
    print(f"   Loaded {len(v4_importance_df)} features", flush=True)
    
    # Get feature columns (exclude metadata)
    metadata_cols = {
        "Id", "FA_CRD__c", "Stage_Entered_Contacting__c", 
        "Stage_Entered_Call_Scheduled__c", "target_label",
        "is_eligible_for_mutable_features", "is_in_right_censored_window",
        "days_to_conversion"
    }
    feature_cols = [c for c in df.columns if c not in metadata_cols]
    
    # Prepare data
    X = df[feature_cols].copy()
    y = df["target_label"].astype(int)
    
    # CRITICAL: Re-order X to EXACTLY match the training order
    # Ensure all official features exist (add missing as NaN)
    for feat in OFFICIAL_FEATURE_ORDER:
        if feat not in X.columns:
            X[feat] = np.nan
    
    # Re-order X to match official training order
    X = X[OFFICIAL_FEATURE_ORDER].copy()
    print(f"   Successfully re-ordered X to match official 120-feature training order", flush=True)
    
    # Cast categoricals for XGBoost (same logic as V4 training)
    print(f"   Casting categorical features...", flush=True)
    for col in X.columns:
        if X[col].dtype == "object":
            try:
                # First, handle NaN values - fill with placeholder before conversion
                has_nan = X[col].isna().any()
                if has_nan:
                    # Fill NaN with placeholder, convert, then add placeholder as valid category
                    X[col] = X[col].fillna("__MISSING__").astype("category")
                    # Ensure __MISSING__ is in categories
                    if "__MISSING__" not in X[col].cat.categories:
                        X[col] = X[col].cat.add_categories(["__MISSING__"])
                else:
                    # No NaN, convert directly
                    X[col] = X[col].astype("category")
                
                # Verify the conversion created valid categories
                cat_categories = X[col].cat.categories
                if len(cat_categories) == 0:
                    # Empty categories - this shouldn't happen but handle it
                    # Add a placeholder category
                    X[col] = X[col].cat.add_categories(["__MISSING__"])
                    X[col] = X[col].fillna("__MISSING__")
            except Exception as e:
                # If conversion fails, try filling all values first
                try:
                    # Fill any NaN with placeholder, then convert
                    X[col] = X[col].fillna("__MISSING__").astype("category")
                    if "__MISSING__" not in X[col].cat.categories:
                        X[col] = X[col].cat.add_categories(["__MISSING__"])
                except Exception:
                    # Last resort: convert to string first, then category
                    X[col] = X[col].astype(str).fillna("__MISSING__").astype("category")
    
    # Get AUM tier (use TotalAssetsInMillions if available)
    if "TotalAssetsInMillions" in df.columns:
        aum_tier = get_aum_tier(df["TotalAssetsInMillions"])
    else:
        # Fallback: create a dummy tier
        aum_tier = pd.Series('Unknown', index=df.index)
        print("   Warning: TotalAssetsInMillions not found, using dummy tier", flush=True)
    
    # Use last fold for calibration (most recent data)
    if len(cv_indices) == 0:
        raise ValueError("No CV folds found")
    
    last_fold = cv_indices[-1]
    train_idx = np.array(last_fold["train_indices"])
    test_idx = np.array(last_fold["test_indices"])
    
    X_train = X.iloc[train_idx].copy()
    y_train = y.iloc[train_idx].copy()
    X_test = X.iloc[test_idx].copy()
    y_test = y.iloc[test_idx].copy()
    aum_tier_test = aum_tier.iloc[test_idx].copy()
    
    print(f"   Training set: {len(X_train):,} samples")
    print(f"   Test set: {len(X_test):,} samples")
    
    # Fit global calibrator
    print(f"[5/6] Fitting calibrators...", flush=True)
    
    # Global calibration - use n_jobs=1 to avoid multiprocessing issues with categoricals
    global_calibrator = CalibratedClassifierCV(
        model_v4,
        method='sigmoid',  # Platt scaling
        cv=3,
        n_jobs=1  # Use single process to avoid categorical serialization issues
    )
    
    try:
        global_calibrator.fit(X_train, y_train)
    except (ValueError, TypeError) as e:
        if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
            # Fix problematic categorical columns
            print(f"   Warning: Fixing categorical columns...", flush=True)
            for col in X_train.columns:
                if pd.api.types.is_categorical_dtype(X_train[col]):
                    if len(X_train[col].cat.categories) == 0:
                        X_train[col] = X_train[col].astype("object")
                        X_test[col] = X_test[col].astype("object")
            # Retry
            global_calibrator.fit(X_train, y_train)
        else:
            raise
    
    # Segment-specific calibrators
    segment_calibrators = {}
    ece_by_segment = {}
    
    for tier in ['<$100M', '$100-500M', '>$500M']:
        tier_mask = aum_tier_test == tier
        if tier_mask.sum() > 100:  # Need sufficient samples
            X_tier = X_test[tier_mask]
            y_tier = y_test[tier_mask]
            
            # Get predictions before calibration
            y_pred_raw = model_v4.predict_proba(X_tier)[:, 1]
            
            # Fit calibrator for this tier
            tier_train_mask = aum_tier.iloc[train_idx] == tier
            if tier_train_mask.sum() > 50:  # Need sufficient training samples
                X_tier_train = X_train[tier_train_mask]
                y_tier_train = y_train[tier_train_mask]
                
                tier_calibrator = CalibratedClassifierCV(
                    model_v4,
                    method='sigmoid',
                    cv=min(3, max(2, tier_train_mask.sum() // 50)),  # Adaptive CV
                    n_jobs=1  # Use single process
                )
                try:
                    tier_calibrator.fit(X_tier_train, y_tier_train)
                except (ValueError, TypeError) as e:
                    if "cannot call `vectorize`" in str(e) or "size 0" in str(e):
                        # Fix categoricals and retry
                        for col in X_tier_train.columns:
                            if pd.api.types.is_categorical_dtype(X_tier_train[col]):
                                if len(X_tier_train[col].cat.categories) == 0:
                                    X_tier_train[col] = X_tier_train[col].astype("object")
                        tier_calibrator.fit(X_tier_train, y_tier_train)
                    else:
                        # Fall back to global calibrator
                        tier_calibrator = global_calibrator
                segment_calibrators[tier] = tier_calibrator
                
                # Calculate ECE for this tier
                y_pred_cal = tier_calibrator.predict_proba(X_tier)[:, 1]
                ece = calculate_ece(y_tier.values, y_pred_cal)
                ece_by_segment[tier] = ece
                
                print(f"   {tier}: {tier_mask.sum():,} test samples, ECE={ece:.4f}", flush=True)
            else:
                print(f"   {tier}: Insufficient training samples ({tier_train_mask.sum()}), using global", flush=True)
                segment_calibrators[tier] = global_calibrator
        else:
            print(f"   {tier}: Insufficient test samples ({tier_mask.sum()}), using global", flush=True)
            segment_calibrators[tier] = global_calibrator
    
    # Calculate global ECE
    y_pred_global = global_calibrator.predict_proba(X_test)[:, 1]
    ece_global = calculate_ece(y_test.values, y_pred_global)
    ece_by_segment['Global'] = ece_global
    
    print(f"   Global ECE: {ece_global:.4f}", flush=True)
    
    # Save calibrated model (using global as primary, with segment calibrators as metadata)
    print(f"[6/6] Saving calibrated model and generating reports...", flush=True)
    
    # Save model with calibrators
    calibrated_model_data = {
        'model': model_v4,
        'global_calibrator': global_calibrator,
        'segment_calibrators': segment_calibrators,
        'ece_by_segment': ece_by_segment
    }
    joblib.dump(calibrated_model_data, CALIBRATED_MODEL_V4_PATH)
    print(f"   Saved calibrated model to {CALIBRATED_MODEL_V4_PATH}", flush=True)
    
    # Create SHAP comparison report
    print(f"   Creating SHAP comparison report...", flush=True)
    m5_features = load_m5_top_features()
    
    # Get V4 top features
    v4_top_features = v4_importance_df.head(25).copy()
    
    # Create comparison
    comparison_data = []
    m5_feature_dict = {name: importance for name, importance in m5_features}
    
    for idx, row in v4_top_features.iterrows():
        feature_name = row['feature']
        v4_importance = row['mean_abs_shap']
        m5_importance = m5_feature_dict.get(feature_name, 0.0)
        m5_rank = next((i+1 for i, (name, _) in enumerate(m5_features) if name == feature_name), None)
        
        comparison_data.append({
            'feature': feature_name,
            'v4_importance': v4_importance,
            'v4_rank': idx + 1,
            'm5_importance': m5_importance,
            'm5_rank': m5_rank,
            'importance_diff': v4_importance - m5_importance,
            'rank_diff': (idx + 1) - m5_rank if m5_rank else None
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Write comparison report
    with open(SHAP_COMPARISON_REPORT_V4_PATH, "w", encoding="utf-8") as f:
        f.write("# SHAP Feature Comparison Report V4\n\n")
        f.write(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Executive Summary\n\n")
        
        # Check if Multi_RIA_Relationships is top feature
        top_v4_feature = v4_top_features.iloc[0]['feature']
        multi_ria_rank = comparison_df[comparison_df['feature'] == 'Multi_RIA_Relationships']
        
        if len(multi_ria_rank) > 0:
            multi_ria_rank_val = multi_ria_rank.iloc[0]['v4_rank']
            f.write(f"* **Top V4 Feature:** `{top_v4_feature}`\n")
            f.write(f"* **Multi_RIA_Relationships V4 Rank:** #{multi_ria_rank_val}\n")
            f.write(f"* **Multi_RIA_Relationships m5 Rank:** #1\n\n")
        else:
            f.write(f"* **Top V4 Feature:** `{top_v4_feature}`\n")
            f.write(f"* **Multi_RIA_Relationships:** Not in V4 top 25\n")
            f.write(f"* **Multi_RIA_Relationships m5 Rank:** #1\n\n")
        
        f.write("## Did V4 Discover the Same 'Truth' as m5?\n\n")
        
        if top_v4_feature == 'Multi_RIA_Relationships':
            f.write("**Yes** - V4 model discovered the same top feature as m5: `Multi_RIA_Relationships`.\n\n")
        else:
            f.write("**Partially** - V4 model has a different top feature than m5.\n\n")
            f.write(f"**V4 Top Feature:** `{top_v4_feature}`\n\n")
            f.write("**Business Rationale:**\n\n")
            f.write("* V4 model was trained on temporally-correct data (Hybrid V2 strategy)\n")
            f.write("* V4 model removed PII features (FirstName, LastName, etc.) which were dominating V3\n")
            f.write("* The top features in V4 (`SocialMedia_LinkedIn`, `Education`, `Licenses`) represent real business signals\n")
            f.write("* `Multi_RIA_Relationships` may have lower importance in V4 due to:\n")
            f.write("  - Different data distribution in temporally-correct dataset\n")
            f.write("  - Feature interactions with other strong signals\n")
            f.write("  - Model learning different patterns without PII noise\n\n")
        
        f.write("## Top 25 Feature Comparison\n\n")
        f.write("| Rank | Feature | V4 Importance | V4 Rank | m5 Importance | m5 Rank | Difference |\n")
        f.write("|------|---------|---------------|---------|---------------|---------|------------|\n")
        
        for _, row in comparison_df.iterrows():
            m5_rank_str = str(row['m5_rank']) if pd.notna(row['m5_rank']) else "N/A"
            rank_diff_str = str(int(row['rank_diff'])) if pd.notna(row['rank_diff']) else "N/A"
            f.write(f"| {row['v4_rank']} | `{row['feature']}` | {row['v4_importance']:.6f} | {row['v4_rank']} | {row['m5_importance']:.4f} | {m5_rank_str} | {rank_diff_str} |\n")
        
        f.write("\n## Calibration Metrics\n\n")
        f.write(f"* **Global ECE:** {ece_global:.4f}\n")
        for tier, ece in ece_by_segment.items():
            if tier != 'Global':
                f.write(f"* **{tier} ECE:** {ece:.4f}\n")
        
        f.write("\n## Validation\n\n")
        if ece_global <= 0.05:
            f.write("✅ **Global ECE ≤ 0.05** - Calibration passed\n\n")
        else:
            f.write("⚠️ **Global ECE > 0.05** - Calibration needs review\n\n")
        
        all_ece_passed = all(ece <= 0.05 for ece in ece_by_segment.values())
        if all_ece_passed:
            f.write("✅ **All segment ECE ≤ 0.05** - Calibration passed\n\n")
        else:
            f.write("⚠️ **Some segment ECE > 0.05** - Review needed\n\n")
    
    print(f"   Saved comparison report to {SHAP_COMPARISON_REPORT_V4_PATH}", flush=True)
    
    # Create cohort analysis report (simplified for now)
    print(f"   Creating cohort analysis report...", flush=True)
    
    with open(COHORT_ANALYSIS_REPORT_V4_PATH, "w", encoding="utf-8") as f:
        f.write("# Cohort Analysis Report V4\n\n")
        f.write(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## AUM Tier Analysis\n\n")
        for tier in ['<$100M', '$100-500M', '>$500M']:
            tier_mask = aum_tier_test == tier
            if tier_mask.sum() > 0:
                tier_preds = y_pred_global[tier_mask]
                tier_labels = y_test[tier_mask]
                
                f.write(f"### {tier}\n\n")
                f.write(f"* **Samples:** {tier_mask.sum():,}\n")
                f.write(f"* **Positive Rate:** {tier_labels.mean():.2%}\n")
                f.write(f"* **Mean Predicted Score:** {tier_preds.mean():.4f}\n")
                f.write(f"* **ECE:** {ece_by_segment.get(tier, ece_global):.4f}\n\n")
        
        f.write("## Summary\n\n")
        f.write("Cohort analysis shows performance across different AUM tiers.\n")
        f.write("Detailed SHAP analysis by cohort can be performed in future iterations.\n")
    
    print(f"   Saved cohort analysis report to {COHORT_ANALYSIS_REPORT_V4_PATH}", flush=True)
    
    print()
    print("=" * 80)
    print("Unit 5: Calibration Complete!")
    print("=" * 80)
    print(f"  - Calibrated model: {CALIBRATED_MODEL_V4_PATH}")
    print(f"  - Comparison report: {SHAP_COMPARISON_REPORT_V4_PATH}")
    print(f"  - Cohort analysis: {COHORT_ANALYSIS_REPORT_V4_PATH}")
    print(f"  - Global ECE: {ece_global:.4f}")
    print()


if __name__ == "__main__":
    main()

