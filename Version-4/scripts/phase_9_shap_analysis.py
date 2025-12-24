"""
Phase 9: SHAP Analysis

This script performs SHAP (SHapley Additive exPlanations) analysis to understand
feature contributions and model interpretability.
"""

import sys
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import shap
import xgboost as xgb

# Add project root to path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

# Import utilities and constants
from utils.execution_logger import ExecutionLogger
from config.constants import BASE_DIR

def prepare_features(df, feature_list):
    """Prepare features for XGBoost (handle categoricals)."""
    X = df[feature_list].copy()
    
    # Identify categorical features
    categorical_features = []
    for feat in feature_list:
        if df[feat].dtype == 'object' or df[feat].dtype.name == 'category':
            categorical_features.append(feat)
    
    # Convert categoricals to codes
    for feat in categorical_features:
        if feat in X.columns:
            X[feat] = X[feat].astype('category').cat.codes
    
    # Fill NaN
    X = X.fillna(0)
    
    return X

def run_phase_9() -> bool:
    """Execute Phase 9: SHAP Analysis."""
    
    logger = ExecutionLogger(BASE_DIR)
    logger.start_phase("9", "SHAP Analysis")
    
    # =========================================================================
    # STEP 9.1: Load Model and Sample
    # =========================================================================
    logger.log_action("Loading model and sampling test data")
    
    try:
        # Load test data
        test_df = pd.read_csv(BASE_DIR / "data" / "splits" / "test.csv")
        logger.log_metric("Test Data", f"{len(test_df):,} leads")
        
        # Sample for SHAP (memory constraint - use 1000-2000 records)
        sample_size = min(2000, len(test_df))
        test_sample = test_df.sample(n=sample_size, random_state=42)
        logger.log_metric("SHAP Sample Size", f"{sample_size:,} leads")
        
        # Load model from pickle (more reliable for SHAP with XGBoost)
        model_path = BASE_DIR / "models" / "v4.0.0" / "model.pkl"
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.log_metric("Model Type", "XGBoost Booster (from pickle)")
        except Exception as e:
            logger.log_warning(f"Failed to load from pickle: {str(e)}", action_taken="Trying JSON")
            # Fallback to JSON
            model_json_path = BASE_DIR / "models" / "v4.0.0" / "model.json"
            model = xgb.Booster()
            model.load_model(str(model_json_path))
            logger.log_metric("Model Type", "XGBoost Booster (from JSON)")
        
        # Load final features
        import json
        with open(BASE_DIR / "data" / "processed" / "final_features.json", 'r') as f:
            final_features_data = json.load(f)
            final_features = final_features_data['final_features']
        
        logger.log_metric("Model Loaded", "Success")
        logger.log_metric("Features", f"{len(final_features)} features")
        
    except Exception as e:
        logger.log_error(f"Failed to load data/model: {str(e)}", exception=e)
        status = logger.end_phase()
        return False
    
    # Prepare features - ensure all are numeric
    X_sample = prepare_features(test_sample, final_features)
    
    # Ensure all columns are numeric (convert any remaining object types)
    for col in X_sample.columns:
        if X_sample[col].dtype == 'object':
            try:
                X_sample[col] = pd.to_numeric(X_sample[col], errors='coerce').fillna(0)
            except:
                X_sample[col] = 0
    
    # Check for any non-numeric values
    logger.log_action("Verifying feature data types")
    for col in X_sample.columns:
        if not pd.api.types.is_numeric_dtype(X_sample[col]):
            logger.log_warning(f"Non-numeric column {col} detected, converting to numeric")
            X_sample[col] = pd.to_numeric(X_sample[col], errors='coerce').fillna(0)
    
    logger.log_metric("Feature Data Types", "All numeric")
    
    # =========================================================================
    # STEP 9.2: Calculate SHAP Values
    # =========================================================================
    logger.log_action("Calculating SHAP values")
    
    shap_values = None
    shap_calculated = False
    
    try:
        # Ensure X_sample is a numpy array with proper dtype
        X_sample_array = X_sample.values.astype(np.float32)
        
        # Create TreeExplainer for XGBoost
        logger.log_action("Creating SHAP TreeExplainer...")
        try:
            explainer = shap.TreeExplainer(model)
            shap_calculated = True
        except Exception as e_shap:
            # If SHAP fails, document and use XGBoost importance instead
            logger.log_warning(
                f"SHAP TreeExplainer creation failed: {str(e_shap)}",
                action_taken="Using XGBoost native feature importance instead of SHAP"
            )
            shap_calculated = False
        
        if shap_calculated:
            # Calculate SHAP values - use a smaller sample for faster computation
            logger.log_action("Computing SHAP values (this may take a minute)...")
            # Use smaller sample (500) for faster computation
            smaller_sample = X_sample_array[:500]
            shap_values = explainer.shap_values(smaller_sample)
            logger.log_metric("SHAP Sample Size", "500 leads (for faster computation)")
            
            logger.log_metric("SHAP Values Calculated", f"Shape: {shap_values.shape}")
            
            # Save SHAP values
            shap_values_path = BASE_DIR / "models" / "v4.0.0" / "shap_values.pkl"
            with open(shap_values_path, 'wb') as f:
                pickle.dump(shap_values, f)
            
            logger.log_file_created("shap_values.pkl", str(shap_values_path))
        else:
            logger.log_warning(
                "SHAP analysis skipped due to model compatibility issue",
                action_taken="Using XGBoost feature importance for interpretability"
            )
        
    except Exception as e:
        logger.log_error(f"Failed to calculate SHAP values: {str(e)}", exception=e)
        shap_calculated = False
    
    # =========================================================================
    # STEP 9.3: Generate Summary Plots
    # =========================================================================
    logger.log_action("Generating SHAP summary plots")
    
    if shap_calculated and shap_values is not None:
        try:
            # SHAP Summary Plot (beeswarm)
            plt.figure(figsize=(10, 8))
            shap.summary_plot(shap_values, X_sample.iloc[:500], show=False, max_display=15)
            plt.tight_layout()
            
            summary_path = BASE_DIR / "reports" / "shap_summary.png"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(summary_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.log_file_created("shap_summary.png", str(summary_path))
            
            # SHAP Bar Plot (mean absolute SHAP values)
            plt.figure(figsize=(10, 8))
            shap.summary_plot(shap_values, X_sample.iloc[:500], plot_type="bar", show=False, max_display=15)
            plt.tight_layout()
            
            bar_path = BASE_DIR / "reports" / "shap_bar.png"
            plt.savefig(bar_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.log_file_created("shap_bar.png", str(bar_path))
            
        except Exception as e:
            logger.log_error(f"Failed to generate summary plots: {str(e)}", exception=e)
    else:
        logger.log_warning("Skipping SHAP plots - using XGBoost importance instead")
    
    # =========================================================================
    # STEP 9.4: Feature Importance Comparison
    # =========================================================================
    logger.log_action("Comparing XGBoost importance vs SHAP importance")
    
    try:
        # Get XGBoost native importance
        xgb_importance = pd.read_csv(BASE_DIR / "models" / "v4.0.0" / "feature_importance.csv")
        # Check column name (might be 'importance' or 'gain' or 'weight')
        importance_col = 'importance' if 'importance' in xgb_importance.columns else xgb_importance.columns[1]
        xgb_importance = xgb_importance.sort_values(importance_col, ascending=False)
        
        # Calculate SHAP importance (mean absolute SHAP value) or use XGBoost importance
        if shap_calculated and shap_values is not None:
            shap_importance = pd.DataFrame({
                'feature': final_features,
                'shap_importance': np.abs(shap_values).mean(axis=0)
            }).sort_values('shap_importance', ascending=False)
        else:
            # Use XGBoost importance as proxy for SHAP
            importance_col = xgb_importance.columns[1] if len(xgb_importance.columns) > 1 else 'importance'
            shap_importance = xgb_importance.copy()
            shap_importance['shap_importance'] = shap_importance[importance_col] / shap_importance[importance_col].max()
            logger.log_warning("Using XGBoost importance as proxy for SHAP (SHAP calculation failed)")
        
        # Merge for comparison
        try:
            comparison = xgb_importance.merge(
                shap_importance, 
                left_on='feature', 
                right_on='feature', 
                how='outer'
            )
            if importance_col in comparison.columns:
                comparison = comparison.sort_values(importance_col, ascending=False)
            else:
                comparison = comparison.sort_values(comparison.columns[1], ascending=False)
            
            logger.log_action("Top 10 Features by XGBoost Importance:")
            for i, row in comparison.head(10).iterrows():
                xgb_val = row.get(importance_col, row.get(comparison.columns[1], 0)) if len(comparison.columns) > 1 else 0
                shap_val = row.get('shap_importance', 0)
                logger.log_metric(
                    f"{row['feature']}",
                    f"XGB: {xgb_val:.2f}, SHAP: {shap_val:.4f}"
                )
        except Exception as e:
            logger.log_error(f"Failed to merge importance data: {str(e)}", exception=e)
            comparison = xgb_importance.copy()
        
        # Save comparison
        comparison_path = BASE_DIR / "reports" / "feature_importance_comparison.csv"
        comparison.to_csv(comparison_path, index=False)
        logger.log_file_created("feature_importance_comparison.csv", str(comparison_path))
        
    except Exception as e:
        logger.log_error(f"Failed to compare importance: {str(e)}", exception=e)
    
    # =========================================================================
    # STEP 9.5: Dependence Plots (Top Features)
    # =========================================================================
    logger.log_action("Generating SHAP dependence plots for top features")
    
    try:
        # Get top 5 features by SHAP importance
        top_features = shap_importance.head(5)['feature'].tolist()
        
        if shap_calculated and shap_values is not None:
            for feat in top_features:
                if feat in X_sample.columns:
                    try:
                        plt.figure(figsize=(8, 6))
                        shap.dependence_plot(
                            feat, 
                            shap_values, 
                            X_sample.iloc[:500], 
                            show=False,
                            interaction_index=None
                        )
                        plt.tight_layout()
                        
                        dep_path = BASE_DIR / "reports" / f"shap_dependence_{feat}.png"
                        plt.savefig(dep_path, dpi=150, bbox_inches='tight')
                        plt.close()
                        
                        logger.log_file_created(f"shap_dependence_{feat}.png", str(dep_path))
                    except Exception as e:
                        logger.log_warning(f"Failed to create dependence plot for {feat}: {str(e)}")
        else:
            logger.log_warning("Skipping SHAP dependence plots - SHAP values not available")
        
    except Exception as e:
        logger.log_error(f"Failed to generate dependence plots: {str(e)}", exception=e)
    
    # =========================================================================
    # STEP 9.6: Generate SHAP Report
    # =========================================================================
    logger.log_action("Generating SHAP analysis report")
    
    try:
        report_path = BASE_DIR / "reports" / "shap_analysis_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Phase 9: SHAP Analysis Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"- **Sample Size**: {sample_size:,} leads\n")
            f.write(f"- **Features Analyzed**: {len(final_features)}\n")
            if shap_calculated and shap_values is not None:
                f.write(f"- **SHAP Values Calculated**: {shap_values.shape[0]:,} predictions × {shap_values.shape[1]} features\n\n")
            else:
                f.write(f"- **SHAP Values**: ⚠️ **Not calculated** - Using XGBoost feature importance instead\n")
                f.write(f"- **Reason**: Model compatibility issue with SHAP TreeExplainer\n\n")
            
            # Feature Importance Comparison
            importance_col = 'importance' if 'importance' in xgb_importance.columns else (xgb_importance.columns[1] if len(xgb_importance.columns) > 1 else 'importance')
            f.write("## Feature Importance Comparison\n\n")
            f.write("| Rank | Feature | XGBoost Importance | SHAP Importance |\n")
            f.write("|------|---------|-------------------|-----------------|\n")
            for i, (_, row) in enumerate(comparison.head(15).iterrows(), 1):
                xgb_val = row.get(importance_col, row.get(comparison.columns[1] if len(comparison.columns) > 1 else 'importance', 0))
                shap_val = row.get('shap_importance', 0)
                f.write(f"| {i} | {row['feature']} | {xgb_val:.2f} | {shap_val:.4f} |\n")
            f.write("\n")
            
            # Top Features Analysis
            f.write("## Top 5 Features by SHAP Importance\n\n")
            for i, (_, row) in enumerate(shap_importance.head(5).iterrows(), 1):
                f.write(f"### {i}. {row['feature']}\n")
                f.write(f"- **SHAP Importance**: {row['shap_importance']:.4f}\n")
                comp_row = comparison[comparison['feature'] == row['feature']]
                if len(comp_row) > 0:
                    xgb_val = comp_row.get(importance_col, comp_row.iloc[0, 1] if len(comp_row.columns) > 1 else 0)
                    if isinstance(xgb_val, pd.Series):
                        xgb_val = xgb_val.values[0] if len(xgb_val) > 0 else 0
                    f.write(f"- **XGBoost Importance**: {xgb_val:.2f}\n")
                if shap_calculated and shap_values is not None:
                    f.write(f"- **Dependence Plot**: ![Dependence Plot](shap_dependence_{row['feature']}.png)\n\n")
                else:
                    f.write("\n")
            
            # Visualizations
            if shap_calculated and shap_values is not None:
                f.write("## Visualizations\n\n")
                f.write("### SHAP Summary Plot (Beeswarm)\n\n")
                f.write("![SHAP Summary](shap_summary.png)\n\n")
                f.write("This plot shows the distribution of SHAP values for each feature. Features are ranked by importance.\n\n")
                
                f.write("### SHAP Bar Plot (Mean Absolute)\n\n")
                f.write("![SHAP Bar](shap_bar.png)\n\n")
                f.write("This plot shows the mean absolute SHAP value for each feature.\n\n")
            else:
                f.write("## Visualizations\n\n")
                f.write("⚠️ **SHAP plots not available** - See XGBoost feature importance in `feature_importance.csv`\n\n")
            
            # Key Insights
            f.write("## Key Insights\n\n")
            f.write("### Feature Contributions\n\n")
            f.write("The SHAP values reveal:\n")
            f.write("- **Positive SHAP values** increase the prediction (higher conversion probability)\n")
            f.write("- **Negative SHAP values** decrease the prediction (lower conversion probability)\n")
            f.write("- **Feature interactions** can be seen in the dependence plots\n\n")
            
            f.write("### Model Interpretability\n\n")
            f.write("For any individual lead, SHAP values explain:\n")
            f.write("- Which features pushed the prediction up or down\n")
            f.write("- How much each feature contributed to the final score\n")
            f.write("- Whether feature interactions are important\n\n")
        
        logger.log_file_created("shap_analysis_report.md", str(report_path))
        
    except Exception as e:
        logger.log_error(f"Failed to generate report: {str(e)}", exception=e)
    
    # =========================================================================
    # PHASE SUMMARY
    # =========================================================================
    status = logger.end_phase(next_steps=["Phase 10: Deployment"])
    
    return status in ["PASSED", "PASSED WITH WARNINGS"]


if __name__ == "__main__":
    success = run_phase_9()
    sys.exit(0 if success else 1)

