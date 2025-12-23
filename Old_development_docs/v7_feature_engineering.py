"""
V7 Feature Engineering Module
Creates comprehensive feature set including:
1. m5's 31 engineered features
2. Temporal dynamics features (from snapshot history)
3. Career stage indicators
4. Market position features
5. Business model indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from google.cloud import bigquery
import sys
import json
from datetime import datetime

# Top 10 metropolitan areas by population (approximate)
TOP_10_METROS = [
    'New York-Newark-Jersey City, NY-NJ-PA',
    'Los Angeles-Long Beach-Anaheim, CA',
    'Chicago-Naperville-Elgin, IL-IN-WI',
    'Dallas-Fort Worth-Arlington, TX',
    'Houston-The Woodlands-Sugar Land, TX',
    'Washington-Arlington-Alexandria, DC-VA-MD-WV',
    'Miami-Fort Lauderdale-West Palm Beach, FL',
    'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD',
    'Atlanta-Sandy Springs-Roswell, GA',
    'Phoenix-Mesa-Scottsdale, AZ'
]

TOP_25_METROS = TOP_10_METROS + [
    'Boston-Cambridge-Newton, MA-NH',
    'San Francisco-Oakland-Hayward, CA',
    'Detroit-Warren-Dearborn, MI',
    'Seattle-Tacoma-Bellevue, WA',
    'Minneapolis-St. Paul-Bloomington, MN-WI',
    'San Diego-Carlsbad, CA',
    'Tampa-St. Petersburg-Clearwater, FL',
    'Denver-Aurora-Lakewood, CO',
    'St. Louis, MO-IL',
    'Baltimore-Columbia-Towson, MD',
    'Charlotte-Concord-Gastonia, NC-SC',
    'Orlando-Kissimmee-Sanford, FL',
    'San Antonio-New Braunfels, TX',
    'Portland-Vancouver-Hillsboro, OR-WA',
    'Sacramento--Roseville--Arden-Arcade, CA',
    'Las Vegas-Henderson-Paradise, NV',
    'Pittsburgh, PA',
    'Austin-Round Rock, TX',
    'Cincinnati, OH-KY-IN',
    'Cleveland-Elyria, OH',
    'Kansas City, MO-KS',
    'Columbus, OH',
    'Indianapolis-Carmel-Anderson, IN',
    'Nashville-Davidson--Murfreesboro--Franklin, TN',
    'Virginia Beach-Norfolk-Newport News, VA-NC'
]


def safe_divide(numerator: pd.Series, denominator: pd.Series, default: float = np.nan) -> pd.Series:
    """Safely divide, handling zeros and NaNs"""
    if isinstance(denominator, pd.Series):
        denominator_clean = denominator.replace(0, np.nan)
        result = numerator / denominator_clean
        return result.fillna(default)
    else:
        if pd.isna(denominator) or denominator == 0:
            return default
        return numerator / denominator


def create_m5_engineered_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Create m5's 31 engineered features.
    Returns: (df with features added, list of feature names created)
    """
    print("[1/5] Creating m5's 31 engineered features...", flush=True)
    
    df = df.copy()
    features_created = []
    
    # 1. Client efficiency metrics
    if "TotalAssetsInMillions" in df.columns:
        if "NumberClients_Individuals" in df.columns:
            if "AUM_per_Client" not in df.columns:
                df["AUM_per_Client"] = safe_divide(
                    df["TotalAssetsInMillions"], 
                    df["NumberClients_Individuals"]
                )
                features_created.append("AUM_per_Client")
        
        if "Number_Employees" in df.columns:
            if "AUM_per_Employee" not in df.columns:
                df["AUM_per_Employee"] = safe_divide(
                    df["TotalAssetsInMillions"],
                    df["Number_Employees"]
                )
                features_created.append("AUM_per_Employee")
        
        if "Number_IAReps" in df.columns:
            if "AUM_per_IARep" not in df.columns:
                df["AUM_per_IARep"] = safe_divide(
                    df["TotalAssetsInMillions"],
                    df["Number_IAReps"]
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
        if "NumberOfPriorFirms" in df.columns:
            num_prior_firms = df["NumberOfPriorFirms"]
        else:
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
                df["NumberClients_Individuals"]
            )
            features_created.append("HNW_Client_Ratio")
    
    if "AssetsInMillions_HNWIndividuals" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "HNW_Asset_Concentration" not in df.columns:
            df["HNW_Asset_Concentration"] = safe_divide(
                df["AssetsInMillions_HNWIndividuals"],
                df["TotalAssetsInMillions"]
            )
            features_created.append("HNW_Asset_Concentration")
    
    # 5. Client focus metrics
    if "AssetsInMillions_Individuals" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "Individual_Asset_Ratio" not in df.columns:
            df["Individual_Asset_Ratio"] = safe_divide(
                df["AssetsInMillions_Individuals"],
                df["TotalAssetsInMillions"]
            )
            features_created.append("Individual_Asset_Ratio")
    
    if "AssetsInMillions_MutualFunds" in df.columns and "AssetsInMillions_PrivateFunds" in df.columns:
        if "Alternative_Investment_Focus" not in df.columns:
            df["Alternative_Investment_Focus"] = safe_divide(
                (df["AssetsInMillions_MutualFunds"].fillna(0) + 
                 df["AssetsInMillions_PrivateFunds"].fillna(0)),
                df["TotalAssetsInMillions"] if "TotalAssetsInMillions" in df.columns 
                else pd.Series(1, index=df.index)
            )
            features_created.append("Alternative_Investment_Focus")
    
    # 6. Scale and reach indicators
    if "Number_Employees" in df.columns:
        if "Is_Large_Firm" not in df.columns:
            df["Is_Large_Firm"] = (df["Number_Employees"] > 100).fillna(False).astype(int)
            features_created.append("Is_Large_Firm")
    
    if "TotalAssetsInMillions" in df.columns:
        if "Has_Scale" not in df.columns:
            if "NumberClients_Individuals" in df.columns:
                df["Has_Scale"] = (
                    (df["TotalAssetsInMillions"] > 500) | 
                    (df["NumberClients_Individuals"] > 100)
                ).fillna(False).astype(int)
            else:
                df["Has_Scale"] = (df["TotalAssetsInMillions"] > 500).fillna(False).astype(int)
            features_created.append("Has_Scale")
    
    # 7. Advisor tenure patterns
    if "DateOfHireAtCurrentFirm_NumberOfYears" in df.columns:
        if "Is_New_To_Firm" not in df.columns:
            df["Is_New_To_Firm"] = (df["DateOfHireAtCurrentFirm_NumberOfYears"] < 2).fillna(False).astype(int)
            features_created.append("Is_New_To_Firm")
    
    if "DateBecameRep_NumberOfYears" in df.columns:
        if "Is_Veteran_Advisor" not in df.columns:
            df["Is_Veteran_Advisor"] = (df["DateBecameRep_NumberOfYears"] > 10).fillna(False).astype(int)
            features_created.append("Is_Veteran_Advisor")
    
    if "NumberOfPriorFirms" in df.columns and "AverageTenureAtPriorFirms" in df.columns:
        if "High_Turnover_Flag" not in df.columns:
            df["High_Turnover_Flag"] = (
                (df["NumberOfPriorFirms"] > 3) & 
                (df["AverageTenureAtPriorFirms"] < 3)
            ).fillna(False).astype(int)
            features_created.append("High_Turnover_Flag")
    
    # 8. Market positioning (simplified - requires AverageAccountSize)
    if "PercentClients_Individuals" in df.columns:
        if "Mass_Market_Focus" not in df.columns:
            # Simplified: high individual client percentage
            df["Mass_Market_Focus"] = (df["PercentClients_Individuals"] > 80).fillna(False).astype(int)
            features_created.append("Mass_Market_Focus")
    
    # 9. Operational efficiency
    if "NumberClients_Individuals" in df.columns:
        if "Number_Employees" in df.columns:
            if "Clients_per_Employee" not in df.columns:
                df["Clients_per_Employee"] = safe_divide(
                    df["NumberClients_Individuals"],
                    df["Number_Employees"]
                )
                features_created.append("Clients_per_Employee")
        
        if "Number_IAReps" in df.columns:
            if "Clients_per_IARep" not in df.columns:
                df["Clients_per_IARep"] = safe_divide(
                    df["NumberClients_Individuals"],
                    df["Number_IAReps"]
                )
                features_created.append("Clients_per_IARep")
    
    if "Number_BranchAdvisors" in df.columns and "Number_Employees" in df.columns:
        if "Branch_Advisor_Density" not in df.columns:
            df["Branch_Advisor_Density"] = safe_divide(
                df["Number_BranchAdvisors"],
                df["Number_Employees"]
            )
            features_created.append("Branch_Advisor_Density")
    
    # 10. Geographic factors
    if "MilesToWork" in df.columns:
        if "Remote_Work_Indicator" not in df.columns:
            df["Remote_Work_Indicator"] = (df["MilesToWork"] > 50).fillna(False).astype(int)
            features_created.append("Remote_Work_Indicator")
        
        if "Local_Advisor" not in df.columns:
            df["Local_Advisor"] = (df["MilesToWork"] <= 10).fillna(False).astype(int)
            features_created.append("Local_Advisor")
    
    # 11. Firm relationship indicators (CRITICAL - m5's #1 feature)
    if "NumberRIAFirmAssociations" in df.columns:
        if "Multi_RIA_Relationships" not in df.columns:
            df["Multi_RIA_Relationships"] = (df["NumberRIAFirmAssociations"] > 1).fillna(False).astype(int)
            features_created.append("Multi_RIA_Relationships")
    
    if "NumberFirmAssociations" in df.columns and "NumberRIAFirmAssociations" in df.columns:
        if "Complex_Registration" not in df.columns:
            df["Complex_Registration"] = (
                (df["NumberFirmAssociations"] > 2) | 
                (df["NumberRIAFirmAssociations"] > 1)
            ).fillna(False).astype(int)
            features_created.append("Complex_Registration")
    
    # 12. US focus (if Percent_ClientsUS exists)
    if "Percent_ClientsUS" in df.columns:
        if "Primarily_US_Clients" not in df.columns:
            df["Primarily_US_Clients"] = (df["Percent_ClientsUS"] > 90).fillna(False).astype(int)
            features_created.append("Primarily_US_Clients")
        
        if "International_Presence" not in df.columns:
            df["International_Presence"] = (df["Percent_ClientsUS"] < 80).fillna(False).astype(int)
            features_created.append("International_Presence")
    
    # 13. Growth trajectory indicator
    if "AUMGrowthRate_1Year" in df.columns and "AUMGrowthRate_5Year" in df.columns:
        if "Positive_Growth_Trajectory" not in df.columns:
            df["Positive_Growth_Trajectory"] = (
                (df["AUMGrowthRate_1Year"] > 0) & 
                (df["AUMGrowthRate_5Year"] > 0)
            ).fillna(False).astype(int)
            features_created.append("Positive_Growth_Trajectory")
        
        if "Accelerating_Growth" not in df.columns:
            df["Accelerating_Growth"] = (
                df["AUMGrowthRate_1Year"] > (df["AUMGrowthRate_5Year"] / 5)
            ).fillna(False).astype(int)
            features_created.append("Accelerating_Growth")
    
    # 14. Quality Score (composite)
    if "Quality_Score" not in df.columns:
        quality_score = pd.Series(0.0, index=df.index)
        
        if "Is_Veteran_Advisor" in df.columns:
            quality_score += pd.to_numeric(df["Is_Veteran_Advisor"], errors='coerce').fillna(0) * 0.25
        
        if "Has_Scale" in df.columns:
            quality_score += pd.to_numeric(df["Has_Scale"], errors='coerce').fillna(0) * 0.25
        
        if "Firm_Stability_Score" in df.columns:
            median_stability = df["Firm_Stability_Score"].median()
            stability_above_median = (df["Firm_Stability_Score"] > median_stability).fillna(False).astype(int)
            quality_score += stability_above_median * 0.15
        
        if "IsPrimaryRIAFirm" in df.columns:
            is_primary = pd.to_numeric(df["IsPrimaryRIAFirm"], errors='coerce').fillna(0)
            quality_score += is_primary * 0.15
        
        if "AUM_per_Client" in df.columns:
            median_aum = df["AUM_per_Client"].median()
            aum_above_median = (df["AUM_per_Client"] > median_aum).fillna(False).astype(int)
            quality_score += aum_above_median * 0.10
        
        if "High_Turnover_Flag" in df.columns:
            low_turnover = (1 - pd.to_numeric(df["High_Turnover_Flag"], errors='coerce').fillna(0))
            quality_score += low_turnover * 0.10
        
        df["Quality_Score"] = quality_score
        features_created.append("Quality_Score")
    
    print(f"   Created {len(features_created)} m5 engineered features", flush=True)
    return df, features_created


def create_temporal_dynamics_features(df: pd.DataFrame, client: bigquery.Client) -> Tuple[pd.DataFrame, List[str]]:
    """
    Create temporal dynamics features from snapshot history.
    Note: This requires joining back to snapshot views to calculate changes over time.
    For now, creates simplified versions that work with available data.
    """
    print("[2/5] Creating temporal dynamics features...", flush=True)
    
    df = df.copy()
    features_created = []
    
    # Since we don't have full snapshot history in the dataset, we'll create
    # proxy features based on available data and snapshot dates
    
    # 1. Firm Change Flag (simplified - would need snapshot history)
    # For now, use tenure as proxy
    if "DateOfHireAtCurrentFirm_NumberOfYears" in df.columns:
        if "Recent_Firm_Change" not in df.columns:
            # Reps with < 1 year at current firm likely changed recently
            df["Recent_Firm_Change"] = (df["DateOfHireAtCurrentFirm_NumberOfYears"] < 1).fillna(False).astype(int)
            features_created.append("Recent_Firm_Change")
    
    # 2. License Growth (simplified - count total licenses)
    if all(col in df.columns for col in ["Has_Series_7", "Has_Series_65", "Has_Series_66", "Has_Series_24"]):
        if "License_Sophistication" not in df.columns:
            df["License_Sophistication"] = (
                pd.to_numeric(df["Has_Series_7"], errors='coerce').fillna(0) +
                pd.to_numeric(df["Has_Series_65"], errors='coerce').fillna(0) +
                pd.to_numeric(df["Has_Series_66"], errors='coerce').fillna(0) +
                pd.to_numeric(df["Has_Series_24"], errors='coerce').fillna(0)
            ).astype(int)
            features_created.append("License_Sophistication")
    
    # 3. Branch Stability (if Branch_State is consistent)
    if "Branch_State" in df.columns:
        if "Branch_State_Stable" not in df.columns:
            # Mark as stable if Branch_State is not null (simplified)
            df["Branch_State_Stable"] = df["Branch_State"].notna().fillna(False).astype(int)
            features_created.append("Branch_State_Stable")
    
    # 4. Tenure Momentum (simplified - use current tenure)
    if "DateOfHireAtCurrentFirm_NumberOfYears" in df.columns:
        if "Tenure_Momentum_Score" not in df.columns:
            # Higher tenure = more momentum
            df["Tenure_Momentum_Score"] = np.clip(df["DateOfHireAtCurrentFirm_NumberOfYears"] / 10, 0, 1)
            features_created.append("Tenure_Momentum_Score")
    
    # 5. Geographic Expansion (use Number_RegisteredStates as proxy)
    if "Number_RegisteredStates" in df.columns:
        if "Multi_State_Operator" not in df.columns:
            df["Multi_State_Operator"] = (df["Number_RegisteredStates"] >= 3).fillna(False).astype(int)
            features_created.append("Multi_State_Operator")
    
    # 6. Association Changes (use current associations as proxy)
    if "NumberFirmAssociations" in df.columns:
        if "Association_Complexity" not in df.columns:
            df["Association_Complexity"] = np.clip(df["NumberFirmAssociations"] / 5, 0, 1)
            features_created.append("Association_Complexity")
    
    # 7. Designation Growth (count total designations)
    if all(col in df.columns for col in ["Has_CFP", "Has_CFA", "Has_CIMA", "Has_AIF"]):
        if "Designation_Count" not in df.columns:
            df["Designation_Count"] = (
                pd.to_numeric(df["Has_CFP"], errors='coerce').fillna(0) +
                pd.to_numeric(df["Has_CFA"], errors='coerce').fillna(0) +
                pd.to_numeric(df["Has_CIMA"], errors='coerce').fillna(0) +
                pd.to_numeric(df["Has_AIF"], errors='coerce').fillna(0)
            ).astype(int)
            features_created.append("Designation_Count")
    
    # 8. Snapshot Age (how old is the snapshot data)
    if "rep_snapshot_at" in df.columns and "contact_date" in df.columns:
        if "Snapshot_Age_Days" not in df.columns:
            df["Snapshot_Age_Days"] = (
                pd.to_datetime(df["contact_date"]) - 
                pd.to_datetime(df["rep_snapshot_at"])
            ).dt.days
            # Fill negative values (shouldn't happen with point-in-time join) with 0
            df["Snapshot_Age_Days"] = df["Snapshot_Age_Days"].clip(lower=0)
            features_created.append("Snapshot_Age_Days")
    
    print(f"   Created {len(features_created)} temporal dynamics features", flush=True)
    return df, features_created


def create_career_stage_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Create features that identify rep's career stage.
    """
    print("[3/5] Creating career stage indicators...", flush=True)
    
    df = df.copy()
    features_created = []
    
    # 1. Early Career High Performer
    if "DateBecameRep_NumberOfYears" in df.columns:
        has_series_65 = pd.to_numeric(df.get("Has_Series_65", pd.Series(0, index=df.index)), errors='coerce').fillna(0)
        has_series_7 = pd.to_numeric(df.get("Has_Series_7", pd.Series(0, index=df.index)), errors='coerce').fillna(0)
        
        if "Early_Career_High_Performer" not in df.columns:
            df["Early_Career_High_Performer"] = (
                (df["DateBecameRep_NumberOfYears"] < 3) &
                ((has_series_65 > 0) | (has_series_7 > 0))
            ).fillna(False).astype(int)
            features_created.append("Early_Career_High_Performer")
    
    # 2. Established Independent
    if "DateBecameRep_NumberOfYears" in df.columns:
        is_owner = pd.to_numeric(df.get("Is_Owner", pd.Series(0, index=df.index)), errors='coerce').fillna(0)
        is_independent = pd.to_numeric(df.get("Is_IndependentContractor", pd.Series(0, index=df.index)), errors='coerce').fillna(0)
        
        if "Established_Independent" not in df.columns:
            df["Established_Independent"] = (
                (df["DateBecameRep_NumberOfYears"] > 10) &
                ((is_owner > 0) | (is_independent > 0))
            ).fillna(False).astype(int)
            features_created.append("Established_Independent")
    
    # 3. Growth Phase Rep
    if "DateBecameRep_NumberOfYears" in df.columns and "Recent_Firm_Change" in df.columns:
        if "Growth_Phase_Rep" not in df.columns:
            df["Growth_Phase_Rep"] = (
                (df["DateBecameRep_NumberOfYears"] >= 3) &
                (df["DateBecameRep_NumberOfYears"] <= 7) &
                (df["Recent_Firm_Change"] == 1)
            ).fillna(False).astype(int)
            features_created.append("Growth_Phase_Rep")
    
    # 4. Veteran Stable
    if "DateBecameRep_NumberOfYears" in df.columns and "Branch_State_Stable" in df.columns:
        if "Veteran_Stable" not in df.columns:
            df["Veteran_Stable"] = (
                (df["DateBecameRep_NumberOfYears"] > 15) &
                (df["Branch_State_Stable"] == 1)
            ).fillna(False).astype(int)
            features_created.append("Veteran_Stable")
    
    print(f"   Created {len(features_created)} career stage features", flush=True)
    return df, features_created


def create_market_position_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Create features for market positioning.
    """
    print("[4/5] Creating market position features...", flush=True)
    
    df = df.copy()
    features_created = []
    
    # 1. Premium Market Position
    if "Home_MetropolitanArea" in df.columns and "Education" in df.columns:
        if "Premium_Market_Position" not in df.columns:
            in_top_metro = df["Home_MetropolitanArea"].isin(TOP_10_METROS)
            has_graduate = df["Education"].str.contains("Graduate|Master|PhD|Doctor", case=False, na=False)
            df["Premium_Market_Position"] = (in_top_metro & has_graduate).fillna(False).astype(int)
            features_created.append("Premium_Market_Position")
    
    # 2. Emerging Market Pioneer
    if "Home_MetropolitanArea" in df.columns:
        is_owner = pd.to_numeric(df.get("Is_Owner", pd.Series(0, index=df.index)), errors='coerce').fillna(0)
        
        if "Emerging_Market_Pioneer" not in df.columns:
            not_top_metro = ~df["Home_MetropolitanArea"].isin(TOP_25_METROS)
            df["Emerging_Market_Pioneer"] = (not_top_metro & (is_owner > 0)).fillna(False).astype(int)
            features_created.append("Emerging_Market_Pioneer")
    
    # 3. Multi-State Operator (already created in temporal dynamics, but keep for consistency)
    if "Multi_State_Operator" not in df.columns and "Number_RegisteredStates" in df.columns:
        df["Multi_State_Operator"] = (df["Number_RegisteredStates"] >= 3).fillna(False).astype(int)
        if "Multi_State_Operator" not in [f for f in features_created]:
            features_created.append("Multi_State_Operator")
    
    # 4. High Touch Advisor
    if "NumberClients_Individuals" in df.columns and "TotalAssetsInMillions" in df.columns:
        if "High_Touch_Advisor" not in df.columns:
            df["High_Touch_Advisor"] = (
                (df["NumberClients_Individuals"] < 100) &
                (df["TotalAssetsInMillions"] > 50)
            ).fillna(False).astype(int)
            features_created.append("High_Touch_Advisor")
    
    print(f"   Created {len(features_created)} market position features", flush=True)
    return df, features_created


def create_business_model_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Identify business model characteristics.
    """
    print("[5/5] Creating business model indicators...", flush=True)
    
    df = df.copy()
    features_created = []
    
    # 1. Mass Affluent Focus
    if "PercentClients_Individuals" in df.columns and "AUM_per_Client" in df.columns:
        if "Mass_Affluent_Focus" not in df.columns:
            df["Mass_Affluent_Focus"] = (
                (df["PercentClients_Individuals"] > 0.8) &
                (df["AUM_per_Client"] < 1.0)  # Less than $1M average
            ).fillna(False).astype(int)
            features_created.append("Mass_Affluent_Focus")
    
    # 2. UHNW Specialist
    if "PercentClients_HNWIndividuals" in df.columns and "AUM_per_Client" in df.columns:
        if "UHNW_Specialist" not in df.columns:
            df["UHNW_Specialist"] = (
                (df["PercentClients_HNWIndividuals"] > 0.5) &
                (df["AUM_per_Client"] > 5.0)  # More than $5M average
            ).fillna(False).astype(int)
            features_created.append("UHNW_Specialist")
    
    # 3. Institutional Manager
    if "PercentAssets_MutualFunds" in df.columns:
        if "Institutional_Manager" not in df.columns:
            df["Institutional_Manager"] = (df["PercentAssets_MutualFunds"] > 0.3).fillna(False).astype(int)
            features_created.append("Institutional_Manager")
    
    # 4. Hybrid Model
    if "Has_Insurance_License" in df.columns and "Has_Series_65" in df.columns:
        has_insurance = pd.to_numeric(df["Has_Insurance_License"], errors='coerce').fillna(0)
        has_series_65 = pd.to_numeric(df["Has_Series_65"], errors='coerce').fillna(0)
        
        if "Hybrid_Model" not in df.columns:
            df["Hybrid_Model"] = ((has_insurance > 0) & (has_series_65 > 0)).fillna(False).astype(int)
            features_created.append("Hybrid_Model")
    
    # 5. Breakaway High AUM
    if "Is_BreakawayRep" in df.columns and "TotalAssetsInMillions" in df.columns:
        is_breakaway = pd.to_numeric(df["Is_BreakawayRep"], errors='coerce').fillna(0)
        if "Breakaway_High_AUM" not in df.columns:
            df["Breakaway_High_AUM"] = ((is_breakaway > 0) & (df["TotalAssetsInMillions"] > 100)).fillna(False).astype(int)
            features_created.append("Breakaway_High_AUM")
    
    # 6. Digital Presence Score
    has_linkedin = (df.get("SocialMedia_LinkedIn", pd.Series("", index=df.index)).notna() & 
                    (df.get("SocialMedia_LinkedIn", pd.Series("", index=df.index)) != ""))
    has_webpage = (df.get("PersonalWebpage", pd.Series("", index=df.index)).notna() & 
                   (df.get("PersonalWebpage", pd.Series("", index=df.index)) != ""))
    
    if "Digital_Presence_Score" not in df.columns:
        df["Digital_Presence_Score"] = (
            (has_linkedin.astype(int) * 2) + 
            (has_webpage.astype(int))
        )
        features_created.append("Digital_Presence_Score")
    
    print(f"   Created {len(features_created)} business model features", flush=True)
    return df, features_created


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add temporal contact features (Day_of_Contact, Is_Weekend_Contact).
    """
    if "Stage_Entered_Contacting__c" in df.columns:
        if "Day_of_Contact" not in df.columns:
            df["Day_of_Contact"] = pd.to_datetime(df["Stage_Entered_Contacting__c"]).dt.dayofweek + 1
            # 1=Monday, 7=Sunday
        
        if "Is_Weekend_Contact" not in df.columns:
            df["Is_Weekend_Contact"] = df["Day_of_Contact"].isin([6, 7]).fillna(False).astype(int)
    
    return df


def apply_feature_engineering(
    df: pd.DataFrame, 
    client: bigquery.Client = None,
    save_to_bigquery: bool = False,
    output_table: str = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Apply all V7 feature engineering steps.
    
    Returns:
        (df with all features, metadata dict with feature counts)
    """
    print("="*70)
    print("V7 Feature Engineering")
    print("="*70)
    print(f"\nInput shape: {df.shape}")
    
    all_features_created = []
    
    # Step 1: Add temporal features
    df = add_temporal_features(df)
    
    # Step 2: Create m5 engineered features
    df, m5_features = create_m5_engineered_features(df)
    all_features_created.extend(m5_features)
    
    # Step 3: Create temporal dynamics features
    df, temp_features = create_temporal_dynamics_features(df, client)
    all_features_created.extend(temp_features)
    
    # Step 4: Create career stage features
    df, career_features = create_career_stage_features(df)
    all_features_created.extend(career_features)
    
    # Step 5: Create market position features
    df, market_features = create_market_position_features(df)
    all_features_created.extend(market_features)
    
    # Step 6: Create business model features
    df, business_features = create_business_model_features(df)
    all_features_created.extend(business_features)
    
    print(f"\nOutput shape: {df.shape}")
    print(f"Total features created: {len(all_features_created)}")
    
    metadata = {
        'm5_features': len(m5_features),
        'temporal_features': len(temp_features),
        'career_features': len(career_features),
        'market_features': len(market_features),
        'business_features': len(business_features),
        'total_new_features': len(all_features_created),
        'features_created': all_features_created
    }
    
    # Save to BigQuery if requested
    if save_to_bigquery and output_table:
        print(f"\nSaving to BigQuery: {output_table}...")
        from google.cloud.bigquery import LoadJobConfig
        job_config = LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        job = client.load_table_from_dataframe(df, output_table, job_config=job_config)
        job.result()  # Wait for job to complete
        print(f"[SUCCESS] Saved to {output_table}")
    
    return df, metadata


def main():
    import argparse
    from google.cloud import bigquery
    
    parser = argparse.ArgumentParser(description='V7 Feature Engineering')
    parser.add_argument('--input-table', type=str, required=True,
                       help='Input BigQuery table name')
    parser.add_argument('--output-table', type=str,
                       help='Output BigQuery table name (optional)')
    parser.add_argument('--save-csv', type=str,
                       help='Save to CSV file (optional)')
    args = parser.parse_args()
    
    client = bigquery.Client(project='savvy-gtm-analytics')
    
    print(f"Loading data from: {args.input_table}")
    df = client.query(f"SELECT * FROM `{args.input_table}`").to_dataframe()
    print(f"Loaded {len(df):,} rows")
    
    # Apply feature engineering
    df_engineered, metadata = apply_feature_engineering(
        df, 
        client=client,
        save_to_bigquery=bool(args.output_table),
        output_table=args.output_table
    )
    
    # Save metadata
    metadata_file = f"v7_feature_engineering_metadata_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"\nMetadata saved to: {metadata_file}")
    
    # Save CSV if requested
    if args.save_csv:
        df_engineered.to_csv(args.save_csv, index=False)
        print(f"CSV saved to: {args.save_csv}")
    
    print("\n[SUCCESS] Feature engineering complete!")
    print(f"\nNext: python train_model_v7.py --input-table {args.output_table or args.input_table}")


if __name__ == "__main__":
    main()

