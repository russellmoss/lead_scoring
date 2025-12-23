# C:\Users\russe\Documents\Lead Scoring\Version-2\utils\paths.py
"""
Centralized path constants for Version-2 model development.

Usage:
    from utils.paths import PATHS
    
    features_path = PATHS['FEATURES_DIR'] / 'features_train.parquet'
"""

from pathlib import Path

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")

PATHS = {
    # Base
    'BASE': BASE_DIR,
    'EXECUTION_LOG': BASE_DIR / 'EXECUTION_LOG.md',
    'DATE_CONFIG': BASE_DIR / 'date_config.json',
    
    # Utils
    'UTILS_DIR': BASE_DIR / 'utils',
    
    # Data
    'DATA_DIR': BASE_DIR / 'data',
    'RAW_DATA_DIR': BASE_DIR / 'data' / 'raw',
    'FEATURES_DIR': BASE_DIR / 'data' / 'features',
    'SCORED_DIR': BASE_DIR / 'data' / 'scored',
    
    # Models
    'MODELS_DIR': BASE_DIR / 'models',
    'REGISTRY': BASE_DIR / 'models' / 'registry.json',
    
    # Reports
    'REPORTS_DIR': BASE_DIR / 'reports',
    'SHAP_DIR': BASE_DIR / 'reports' / 'shap',
    
    # SQL
    'SQL_DIR': BASE_DIR / 'sql',
    
    # Inference
    'INFERENCE_DIR': BASE_DIR / 'inference',
}

def get_model_dir(version_id: str) -> Path:
    """Get the directory for a specific model version."""
    return PATHS['MODELS_DIR'] / version_id

def get_report_path(phase: str) -> Path:
    """Get the report path for a specific phase."""
    return PATHS['REPORTS_DIR'] / f"phase_{phase}_report.md"

