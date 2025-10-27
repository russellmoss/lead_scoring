import pandas as pd
from typing import List, Dict, Tuple, Optional, Union
import logging
from enum import IntEnum
from dataclasses import dataclass, field

# Create a dedicated logger for this module
logger = logging.getLogger(__name__)


class VerbosityLevel(IntEnum):
    """Verbosity levels for logging output."""
    SILENT = 0  # No output
    MINIMAL = 1  # Only summary statistics
    NORMAL = 2  # Summary + major operations
    DETAILED = 3  # All operations
    DEBUG = 4  # Everything including debug info


@dataclass
class CleaningReport:
    """Container for cleaning operation results."""
    columns_dropped: List[str] = field(default_factory=list)
    columns_renamed: Dict[str, str] = field(default_factory=dict)
    columns_converted: List[str] = field(default_factory=list)
    correlations_found: List[Tuple[str, str, float]] = field(default_factory=list)
    identical_pairs: List[Tuple[str, str]] = field(default_factory=list)
    total_columns_before: int = 0
    total_columns_after: int = 0
    
    def summary(self) -> str:
        """Generate a summary of the cleaning operations."""
        lines = [
            f"Column Cleaning Summary:",
            f"  • Columns: {self.total_columns_before} → {self.total_columns_after} "
            f"({self.total_columns_before - self.total_columns_after} removed)",
            f"  • Dropped: {len(self.columns_dropped)} columns",
            f"  • Renamed: {len(self.columns_renamed)} columns",
            f"  • Converted to numeric: {len(self.columns_converted)} columns",
            f"  • Identical pairs found: {len(self.identical_pairs)}",
            f"  • High correlations found: {len(self.correlations_found)}"
        ]
        return "\n".join(lines)


class ColumnCleaner:
    """Enhanced column cleaner with verbosity control."""
    
    def __init__(self, 
                 verbosity: Union[int, VerbosityLevel] = VerbosityLevel.NORMAL,
                 logger_instance: Optional[logging.Logger] = None):
        """
        Initialize the ColumnCleaner.
        
        Parameters:
        -----------
        verbosity : int or VerbosityLevel
            Control the amount of output (0=silent, 4=debug)
        logger_instance : logging.Logger, optional
            Custom logger instance to use
        """
        self.verbosity = VerbosityLevel(verbosity)
        self.logger = logger_instance or logger
        self.report = CleaningReport()
        
        # Configure logger level based on verbosity
        self._configure_logging()
    
    def _configure_logging(self):
        """Configure logging based on verbosity level."""
        if self.verbosity == VerbosityLevel.SILENT:
            self.logger.setLevel(logging.CRITICAL + 1)
        elif self.verbosity == VerbosityLevel.MINIMAL:
            self.logger.setLevel(logging.WARNING)
        elif self.verbosity == VerbosityLevel.NORMAL:
            self.logger.setLevel(logging.INFO)
        elif self.verbosity == VerbosityLevel.DETAILED:
            self.logger.setLevel(logging.INFO)
        else:  # DEBUG
            self.logger.setLevel(logging.DEBUG)
    
    def _log(self, level: int, message: str, force: bool = False):
        """Log a message if verbosity allows it."""
        if force or self.verbosity > VerbosityLevel.SILENT:
            self.logger.log(level, message)
    
    def clean_merged_columns(self,
                            df: pd.DataFrame, 
                            suffixes: List[str] = None,
                            correlation_threshold: float = 0.98,
                            perfect_correlation_threshold: float = 0.9999,
                            inplace: bool = False,
                            return_report: bool = False) -> Union[pd.DataFrame, Tuple[pd.DataFrame, CleaningReport]]:
        """
        Clean merged columns by removing duplicates and highly correlated columns.
        
        Parameters:
        -----------
        df : pd.DataFrame
            Input dataframe with merged columns
        suffixes : List[str], optional
            List of suffixes to identify merged columns
        correlation_threshold : float, default=0.98
            Threshold for considering columns as highly correlated
        perfect_correlation_threshold : float, default=0.9999
            Threshold for considering columns as perfectly correlated
        inplace : bool, default=False
            Whether to modify the dataframe in place
        return_report : bool, default=False
            Whether to return the cleaning report along with the dataframe
        
        Returns:
        --------
        pd.DataFrame or Tuple[pd.DataFrame, CleaningReport]
            Cleaned dataframe (and optionally the cleaning report)
        """
        # Reset report
        self.report = CleaningReport()
        self.report.total_columns_before = len(df.columns)
        
        # Work with a copy if not inplace
        if not inplace:
            df = df.copy()
        
        # Default suffixes
        if suffixes is None:
            suffixes = ['_sf', '_rep', '_firm', '_merge1', '_ddrep', '_ddfirm']
        
        if self.verbosity >= VerbosityLevel.NORMAL:
            self._log(logging.INFO, f"Starting column cleaning with {len(df.columns)} columns")
            self._log(logging.INFO, f"Looking for suffixes: {suffixes}")
        
        # Step 1: Identify and group columns by base name
        base_column_groups = self._group_columns_by_base(df.columns, suffixes)
        
        if self.verbosity >= VerbosityLevel.DETAILED:
            self._log(logging.INFO, f"Found {len(base_column_groups)} column groups to process")
        
        # Step 2: Process each group of related columns
        for base_name, cols in base_column_groups.items():
            if len(cols) <= 1:
                continue
            
            if self.verbosity >= VerbosityLevel.DETAILED:
                self._log(logging.INFO, f"Processing group '{base_name}' with {len(cols)} columns")
            
            # Step 3: Handle identical columns
            cols_to_keep = self._handle_identical_columns(df, base_name, cols)
            
            if len(cols_to_keep) <= 1:
                continue
            
            # Step 4: Convert to numeric where possible
            self._convert_to_numeric(df, cols_to_keep)
            
            # Step 5: Handle correlated numeric columns
            self._handle_correlated_columns(df, base_name, cols_to_keep, 
                                          correlation_threshold, 
                                          perfect_correlation_threshold)
        
        # Step 6: Clean up column names
        self._clean_column_names(df, suffixes)
        
        # Update final column count
        self.report.total_columns_after = len(df.columns)
        
        # Log summary based on verbosity
        if self.verbosity >= VerbosityLevel.MINIMAL:
            self._log(logging.INFO, "\n" + self.report.summary())
        
        if return_report:
            return df, self.report
        return df
    
    def _group_columns_by_base(self, columns: pd.Index, suffixes: List[str]) -> Dict[str, List[str]]:
        """Group columns by their base name (before suffix)."""
        base_column_groups = {}
        
        for col in columns:
            has_suffix = False
            base_name = col
            
            for suffix in suffixes:
                if col.endswith(suffix):
                    base_name = col[:-len(suffix)]
                    has_suffix = True
                    break
            
            if has_suffix:
                if base_name not in base_column_groups:
                    base_column_groups[base_name] = []
                base_column_groups[base_name].append(col)
        
        if self.verbosity == VerbosityLevel.DEBUG:
            for base, cols in base_column_groups.items():
                self._log(logging.DEBUG, f"  Group '{base}': {cols}")
        
        return base_column_groups
    
    def _handle_identical_columns(self, df: pd.DataFrame, base_name: str, 
                                 cols: List[str]) -> List[str]:
        """Remove columns that are identical to others in the group."""
        cols_to_keep = cols.copy()
        
        for i in range(len(cols)):
            if cols[i] not in cols_to_keep:
                continue
                
            for j in range(i + 1, len(cols)):
                if cols[j] not in cols_to_keep:
                    continue
                    
                try:
                    if df[cols[i]].equals(df[cols[j]]):
                        df.drop(columns=[cols[j]], inplace=True)
                        cols_to_keep.remove(cols[j])
                        
                        self.report.columns_dropped.append(cols[j])
                        self.report.identical_pairs.append((cols[i], cols[j]))
                        
                        if self.verbosity >= VerbosityLevel.DETAILED:
                            self._log(logging.INFO, f"    Dropped {cols[j]} (identical to {cols[i]})")
                            
                except Exception as e:
                    if self.verbosity == VerbosityLevel.DEBUG:
                        self._log(logging.WARNING, f"    Error comparing {cols[i]} and {cols[j]}: {e}")
        
        # Rename single remaining column to base name if possible
        if len(cols_to_keep) == 1 and base_name not in df.columns:
            old_name = cols_to_keep[0]
            df.rename(columns={old_name: base_name}, inplace=True)
            self.report.columns_renamed[old_name] = base_name
            
            if self.verbosity >= VerbosityLevel.DETAILED:
                self._log(logging.INFO, f"    Renamed {old_name} to {base_name}")
            
            cols_to_keep = [base_name]
        
        return cols_to_keep
    
    def _convert_to_numeric(self, df: pd.DataFrame, cols: List[str]) -> None:
        """Convert columns to numeric where possible."""
        for col in cols:
            if col not in df.columns or pd.api.types.is_numeric_dtype(df[col]):
                continue
                
            try:
                test_series = df[col].copy()
                
                if df[col].dtype == 'object':
                    # Clean formatting
                    test_series = test_series.str.replace('$', '', regex=False)
                    test_series = test_series.str.replace(',', '', regex=False)
                    test_series = test_series.str.replace('%', '', regex=False)
                    test_series = test_series.str.strip()
                    
                    converted = pd.to_numeric(test_series, errors='coerce')
                    
                    # Check conversion quality
                    non_null_before = df[col].notna().sum()
                    non_null_after = converted.notna().sum()
                    
                    if non_null_before > 0 and non_null_after / non_null_before > 0.5:
                        df[col] = converted
                        self.report.columns_converted.append(col)
                        
                        if self.verbosity >= VerbosityLevel.DETAILED:
                            self._log(logging.INFO, f"    Converted {col} to numeric")
                            
            except Exception as e:
                if self.verbosity == VerbosityLevel.DEBUG:
                    self._log(logging.DEBUG, f"    Could not convert {col} to numeric: {e}")
    
    def _handle_correlated_columns(self, df: pd.DataFrame, base_name: str, cols: List[str],
                                  correlation_threshold: float, 
                                  perfect_correlation_threshold: float) -> None:
        """Handle highly correlated numeric columns."""
        numeric_cols = [col for col in cols 
                       if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        
        if len(numeric_cols) <= 1:
            return
        
        try:
            corr_matrix = df[numeric_cols].corr().abs()
            cols_to_drop = set()
            
            # Check all pairs
            for i in range(len(numeric_cols)):
                if numeric_cols[i] in cols_to_drop:
                    continue
                    
                for j in range(i + 1, len(numeric_cols)):
                    if numeric_cols[j] in cols_to_drop:
                        continue
                        
                    correlation = corr_matrix.iloc[i, j]
                    
                    if correlation >= correlation_threshold:
                        keep_col, drop_col = self._choose_column_to_keep(
                            df, numeric_cols[i], numeric_cols[j]
                        )
                        cols_to_drop.add(drop_col)
                        
                        self.report.correlations_found.append((keep_col, drop_col, correlation))
                        
                        if self.verbosity >= VerbosityLevel.DETAILED:
                            self._log(logging.INFO, 
                                    f"    Dropped {drop_col} (corr={correlation:.3f} with {keep_col})")
            
            # Drop the selected columns
            if cols_to_drop:
                df.drop(columns=list(cols_to_drop), inplace=True)
                self.report.columns_dropped.extend(list(cols_to_drop))
                
        except Exception as e:
            if self.verbosity >= VerbosityLevel.NORMAL:
                self._log(logging.WARNING, f"Error handling correlated columns for {base_name}: {e}")
    
    def _choose_column_to_keep(self, df: pd.DataFrame, col1: str, col2: str) -> Tuple[str, str]:
        """Decide which column to keep based on data quality metrics."""
        na_count1 = df[col1].isna().sum()
        na_count2 = df[col2].isna().sum()
        
        # Check missing values
        total_rows = len(df)
        if abs(na_count1 - na_count2) / total_rows > 0.1:
            return (col1, col2) if na_count1 < na_count2 else (col2, col1)
        
        # Check variance
        var1 = df[col1].var()
        var2 = df[col2].var()
        
        if var1 > 0 or var2 > 0:
            max_var = max(var1, var2)
            if max_var > 0 and abs(var1 - var2) / max_var > 0.2:
                return (col1, col2) if var1 > var2 else (col2, col1)
        
        # Default to shorter name
        return (col1, col2) if len(col1) <= len(col2) else (col2, col1)
    
    def _clean_column_names(self, df: pd.DataFrame, suffixes: List[str]) -> None:
        """Remove suffixes from column names where possible."""
        columns_to_rename = {}
        
        for col in df.columns:
            for suffix in suffixes:
                if col.endswith(suffix):
                    base_name = col[:-len(suffix)]
                    
                    if base_name not in df.columns and base_name not in columns_to_rename.values():
                        columns_to_rename[col] = base_name
                        
                        if self.verbosity >= VerbosityLevel.DETAILED:
                            self._log(logging.INFO, f"  Renamed {col} to {base_name}")
                        break
        
        if columns_to_rename:
            df.rename(columns=columns_to_rename, inplace=True)
            self.report.columns_renamed.update(columns_to_rename)


# Convenience function for backward compatibility
def clean_merged_columns(df: pd.DataFrame, 
                        suffixes: List[str] = None,
                        correlation_threshold: float = 0.98,
                        perfect_correlation_threshold: float = 0.9999,
                        inplace: bool = False,
                        verbosity: int = VerbosityLevel.NORMAL) -> pd.DataFrame:
    """
    Clean merged columns with configurable verbosity.
    
    This is a convenience function that maintains backward compatibility
    while adding verbosity control.
    
    Parameters:
    -----------
    verbosity : int, default=2
        Verbosity level (0=silent, 1=minimal, 2=normal, 3=detailed, 4=debug)
    
    Other parameters same as ColumnCleaner.clean_merged_columns()
    """
    cleaner = ColumnCleaner(verbosity=verbosity)
    return cleaner.clean_merged_columns(df, suffixes, correlation_threshold, 
                                       perfect_correlation_threshold, inplace)


# Example usage
if __name__ == "__main__":
    # Example with different verbosity levels
    import numpy as np
    
    # Create sample data
    df = pd.DataFrame({
        'feature1_sf': np.random.randn(100),
        'feature1_rep': np.random.randn(100),
        'feature2_merge1': np.random.randn(100),
        'feature2_firm': np.random.randn(100),
        'feature3': np.random.randn(100)
    })
    
    # Make some columns identical
    df['feature1_ddrep'] = df['feature1_sf']
    
    print("Example 1: Silent mode")
    cleaner = ColumnCleaner(verbosity=VerbosityLevel.SILENT)
    df_clean = cleaner.clean_merged_columns(df.copy())
    
    print("\nExample 2: Minimal output")
    cleaner = ColumnCleaner(verbosity=VerbosityLevel.MINIMAL)
    df_clean = cleaner.clean_merged_columns(df.copy())
    
    print("\nExample 3: Normal output")
    cleaner = ColumnCleaner(verbosity=VerbosityLevel.NORMAL)
    df_clean = cleaner.clean_merged_columns(df.copy())
    
    print("\nExample 4: Detailed output with report")
    cleaner = ColumnCleaner(verbosity=VerbosityLevel.DETAILED)
    df_clean, report = cleaner.clean_merged_columns(df.copy(), return_report=True)
    
    print("\nExample 5: Using convenience function")
    df_clean = clean_merged_columns(df.copy(), verbosity=1)