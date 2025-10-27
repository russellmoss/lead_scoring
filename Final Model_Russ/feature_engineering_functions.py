import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """Configuration for feature engineering pipeline."""
    top_metro_areas: int = 5
    prior_firm_prefix: str = "Number_YearsPriorFirm"
    metro_area_prefix: str = "Home_MetropolitanArea_"


class FeatureEngineer:
    """Modern feature engineering pipeline for model data."""
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self.feature_columns = []
        
    def clean_numeric_column(self, series: pd.Series) -> pd.Series:
        """Remove currency and formatting characters from numeric columns."""
        replacements = {'<': '', '$': '', ',': '', ' ': ''}
        return series.replace(replacements, regex=True)
    
    def to_numeric(self, series: pd.Series, dtype: type = float) -> pd.Series:
        """Convert series to numeric type with error handling."""
        cleaned = self.clean_numeric_column(series)
        return pd.to_numeric(cleaned, errors='coerce').astype(dtype)
    
    def to_boolean(self, series: pd.Series, true_values: List[str] = ["Yes"]) -> pd.Series:
        """Convert series to boolean based on specified true values."""
        return series.isin(true_values).astype('boolean')
    
    def to_datetime(self, series: pd.Series) -> pd.Series:
        """Convert series to timezone-naive datetime."""
        return pd.to_datetime(series, errors='coerce').dt.tz_localize(None)
    
    def create_dummy_features(self, df: pd.DataFrame, column: str, 
                            top_n: Optional[int] = None, 
                            other_label: str = "Other") -> pd.DataFrame:
        """Create dummy variables for categorical column with optional top-N filtering."""
        if top_n:
            top_values = df[column].value_counts().head(top_n).index
            df[column] = df[column].apply(lambda x: x if x in top_values else other_label)
        
        df = pd.get_dummies(df, columns=[column], drop_first=False)
        
        # Drop the "Other" category if it exists
        other_col = f"{column}_{other_label}"
        if other_col in df.columns:
            df = df.drop(columns=[other_col])
            
        return df
    
    def engineer_features(self, df: pd.DataFrame, feature_columns: List[str]) -> tuple[pd.DataFrame, List[str]]:
        """
        Main feature engineering pipeline.
        
        Args:
            df: Input dataframe with raw features
            feature_columns: List of feature column names
            
        Returns:
            Tuple of (transformed dataframe, updated feature columns list)
        """
        # Create a copy to avoid modifying the original
        model_data = df.copy()
        self.feature_columns = feature_columns.copy()
        
        # Define transformations in a clean, declarative way
        transformations = {
            # Boolean conversions
            'boolean_mappings': [
                ('DuallyRegisteredBDRIARep', 'IsDuallyRegistered', lambda x: x == "Yes"),
                ('OwnershipType', 'IsIndependent', lambda x: x == "Independent"),
            ],
            
            # Direct boolean conversions with Yes/No mapping
            'yes_no_booleans': ['IsPrimaryRIAFirm', 'KnownNonAdvisor'],
            
            # Type conversions
            'to_boolean': ['IsConverted'],
            
            # Numeric conversions with renaming
            'numeric_renames': [
                ('NumberClients_HNWIndividuals_merge1', 'NumberClients_HNWIndividuals'),
                ('NumberClients_Individuals_merge1', 'NumberClients_Individuals'),
            ],
            
            # Direct numeric conversions
            'to_numeric': [
                'Number_InvestmentAdvisoryClients',
                'Number_Employees', 
                'Percent_ClientsUS'
            ],
            
            # Datetime conversions
            'to_datetime': [
                'ConvertedDate',
                'CreatedDate',
                'Stage_Entered_Call_Scheduled__c'
            ]
        }
        
        # Apply boolean mappings
        for old_col, new_col, transform_func in transformations['boolean_mappings']:
            if old_col in model_data.columns:
                model_data[new_col] = model_data[old_col].apply(transform_func).astype('boolean')
                model_data = model_data.drop(columns=[old_col])
                self._update_feature_columns(old_col, new_col)
                logger.info(f"Transformed {old_col} -> {new_col}")
        
        # Apply Yes/No boolean conversions
        for col in transformations['yes_no_booleans']:
            if col in model_data.columns:
                model_data[col] = model_data[col].map({"Yes": True, "No": False}).fillna(False).astype('boolean')
                logger.info(f"Converted {col} to boolean")
        
        # Apply direct boolean conversions
        for col in transformations['to_boolean']:
            if col in model_data.columns:
                model_data[col] = model_data[col].astype('boolean')
                logger.info(f"Converted {col} to boolean type")
        
        # Apply numeric conversions with renaming
        for old_col, new_col in transformations['numeric_renames']:
            if old_col in model_data.columns:
                model_data[new_col] = self.to_numeric(model_data[old_col])
                model_data = model_data.drop(columns=[old_col])
                self._update_feature_columns(old_col, new_col)
                logger.info(f"Converted {old_col} -> {new_col} (numeric)")
        
        # Apply direct numeric conversions
        for col in transformations['to_numeric']:
            if col in model_data.columns:
                model_data[col] = self.to_numeric(model_data[col])
                logger.info(f"Converted {col} to numeric")
        
        # Apply datetime conversions
        for col in transformations['to_datetime']:
            if col in model_data.columns:
                model_data[col] = self.to_datetime(model_data[col])
                logger.info(f"Converted {col} to datetime")
        
        # Handle metropolitan area encoding
        if 'Home_MetropolitanArea' in model_data.columns:
            model_data = self.create_dummy_features(
                model_data, 
                'Home_MetropolitanArea',
                top_n=self.config.top_metro_areas
            )
            self._update_feature_columns('Home_MetropolitanArea')
            
            # Add new dummy columns to feature list
            new_dummy_cols = [col for col in model_data.columns 
                            if col.startswith(self.config.metro_area_prefix)]
            self.feature_columns.extend(new_dummy_cols)
            logger.info(f"Created {len(new_dummy_cols)} metropolitan area dummy variables")
        
        # Engineer tenure-related features
        model_data = self._engineer_tenure_features(model_data)
        
        # Create target variable
        if 'Stage_Entered_Call_Scheduled__c' in model_data.columns:
            model_data['EverCalled'] = model_data['Stage_Entered_Call_Scheduled__c'].notna().astype(bool)
            logger.info("Created target variable: EverCalled")
        
        return model_data, self.feature_columns
    
    def _engineer_tenure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create tenure-related engineered features."""
        prior_firm_cols = [col for col in df.columns 
                          if col.startswith(self.config.prior_firm_prefix)]
        
        if prior_firm_cols:
            # Average tenure at prior firms
            df['AverageTenureAtPriorFirms'] = df[prior_firm_cols].mean(axis=1)
            self.feature_columns.append('AverageTenureAtPriorFirms')
            
            # Number of prior firms
            df['NumberOfPriorFirms'] = df[prior_firm_cols].count(axis=1)
            self.feature_columns.append('NumberOfPriorFirms')
            
            logger.info(f"Created tenure features from {len(prior_firm_cols)} prior firm columns")
        
        return df
    
    def _update_feature_columns(self, old_col: str, new_col: Optional[str] = None):
        """Update feature columns list when renaming or removing columns."""
        if old_col in self.feature_columns:
            self.feature_columns.remove(old_col)
            if new_col:
                self.feature_columns.append(new_col)