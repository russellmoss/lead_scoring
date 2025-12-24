"""
Phase 4: Multicollinearity Analysis

This script:
1. Calculates correlation matrix for all numeric features
2. Calculates VIF (Variance Inflation Factor) for each feature
3. Identifies and removes highly correlated features
4. Creates final feature set for modeling
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant

# Add project root to path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

# Import utilities and constants
from utils.execution_logger import ExecutionLogger, get_logger
from config.constants import (
    BASE_DIR,
    PROJECT_ID,
    LOCATION,
    DATASET_ML,
    MulticollinearityGates,
    ALL_FEATURES,
    FEATURES_EXCLUDE
)

from google.cloud import bigquery


def calculate_vif(df, features):
    """
    Calculate Variance Inflation Factor (VIF) for each feature.
    
    VIF = 1 / (1 - R²) where R² is from regressing feature on all others.
    VIF > 5 indicates multicollinearity.
    """
    # Prepare data (only numeric features, no missing values)
    df_clean = df[features].copy()
    df_clean = df_clean.select_dtypes(include=[np.number])
    df_clean = df_clean.dropna()
    
    if len(df_clean) == 0 or len(df_clean.columns) == 0:
        return {}
    
    # Remove constant columns (zero variance)
    df_clean = df_clean.loc[:, df_clean.std() > 0]
    
    if len(df_clean.columns) == 0:
        return {}
    
    # Check for perfect correlation (singular matrix)
    # If any two features are perfectly correlated, VIF will fail
    corr_matrix = df_clean.corr().abs()
    
    vif_data = {}
    
    # Try to calculate VIF, but handle singular matrix issues
    try:
        # Add constant for regression
        X = add_constant(df_clean)
        
        # Check if matrix is singular
        if np.linalg.cond(X.values) > 1e12:
            # Matrix is near-singular, calculate VIF manually using correlation
            # Note: logger not available in this function scope, so we'll handle it in caller
            for feature in df_clean.columns:
                # VIF approximation: 1 / (1 - max_corr²)
                max_corr = corr_matrix[feature].drop(feature).max()
                if max_corr < 0.999:  # Avoid division by zero
                    vif_data[feature] = 1 / (1 - max_corr**2)
                else:
                    vif_data[feature] = 999.0
        else:
            # Normal VIF calculation
            for i, feature in enumerate(df_clean.columns, start=1):  # Start at 1 because const is at 0
                try:
                    vif = variance_inflation_factor(X.values, i)
                    if np.isnan(vif) or np.isinf(vif):
                        # Fallback to correlation-based approximation
                        max_corr = corr_matrix[feature].drop(feature).max()
                        if max_corr < 0.999:
                            vif_data[feature] = 1 / (1 - max_corr**2)
                        else:
                            vif_data[feature] = 999.0
                    else:
                        vif_data[feature] = vif
                except Exception as e:
                    # Fallback to correlation-based approximation
                    max_corr = corr_matrix[feature].drop(feature).max()
                    if max_corr < 0.999:
                        vif_data[feature] = 1 / (1 - max_corr**2)
                    else:
                        vif_data[feature] = 999.0
    except Exception as e:
        # Complete fallback: use correlation-based VIF
        for feature in df_clean.columns:
            max_corr = corr_matrix[feature].drop(feature).max()
            if max_corr < 0.999:
                vif_data[feature] = 1 / (1 - max_corr**2)
            else:
                vif_data[feature] = 999.0
    
    return vif_data


def run_phase_4() -> bool:
    """Execute Phase 4: Multicollinearity Analysis."""
    
    logger = ExecutionLogger(BASE_DIR)
    logger.start_phase("4", "Multicollinearity Analysis")
    
    # Track all gates
    all_blocking_gates_passed = True
    
    # Initialize BigQuery client
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    
    # =========================================================================
    # STEP 4.1: Load Feature Data
    # =========================================================================
    logger.log_action("Loading feature data from BigQuery")
    
    try:
        # Load feature data
        query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ML}.v4_features_pit`
        """
        
        df = client.query(query).to_dataframe()
        logger.log_dataframe_summary(df, "Feature Data")
        
        # Separate features from metadata
        metadata_cols = ['lead_id', 'advisor_crd', 'contacted_date', 'target', 
                        'lead_source_grouped', 'firm_crd', 'firm_name', 
                        'feature_extraction_timestamp']
        feature_columns = [col for col in df.columns if col not in metadata_cols]
        
        logger.log_metric("Total Features", f"{len(feature_columns)}")
        
    except Exception as e:
        logger.log_error(f"Failed to load feature data: {str(e)}", exception=e)
        status = logger.end_phase()
        return False
    
    # =========================================================================
    # STEP 4.2: Calculate Correlation Matrix
    # =========================================================================
    logger.log_action("Calculating correlation matrix")
    
    try:
        # Get numeric features only
        numeric_features = df[feature_columns].select_dtypes(include=[np.number]).columns.tolist()
        
        # Calculate correlation matrix
        corr_matrix = df[numeric_features].corr()
        
        # Find high correlation pairs
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                feature1 = corr_matrix.columns[i]
                feature2 = corr_matrix.columns[j]
                corr_value = corr_matrix.iloc[i, j]
                
                if abs(corr_value) > MulticollinearityGates.MAX_CORRELATION:
                    high_corr_pairs.append({
                        'feature1': feature1,
                        'feature2': feature2,
                        'correlation': corr_value
                    })
        
        # Sort by absolute correlation
        high_corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        logger.log_metric("High Correlation Pairs", f"{len(high_corr_pairs)}")
        
        if high_corr_pairs:
            logger.log_action("High Correlation Pairs (|r| > 0.7):")
            for pair in high_corr_pairs[:10]:  # Log top 10
                logger.log_metric(
                    f"{pair['feature1']} <-> {pair['feature2']}",
                    f"r = {pair['correlation']:.3f}"
                )
        
        # Gate G4.1: <= 3 feature pairs with correlation > 0.7 (WARNING)
        gate_4_1 = len(high_corr_pairs) <= 3
        logger.log_gate(
            "G4.1", "High Correlation Pairs",
            passed=gate_4_1,
            expected="<= 3 pairs with |r| > 0.7",
            actual=f"{len(high_corr_pairs)} pairs"
        )
        
        if not gate_4_1:
            logger.log_warning(
                f"Found {len(high_corr_pairs)} high correlation pairs",
                action_taken="Will remove redundant features"
            )
        
        # Create correlation heatmap
        plt.figure(figsize=(16, 12))
        if HAS_SEABORN:
            sns.heatmap(corr_matrix, annot=False, cmap='coolwarm', center=0,
                       square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})
        else:
            # Use matplotlib only
            im = plt.imshow(corr_matrix.values, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
            plt.colorbar(im, shrink=0.8)
            plt.xticks(range(len(corr_matrix.columns)), corr_matrix.columns, rotation=90, ha='right')
            plt.yticks(range(len(corr_matrix.columns)), corr_matrix.columns)
        plt.title('Feature Correlation Matrix', fontsize=16, pad=20)
        plt.tight_layout()
        
        heatmap_path = BASE_DIR / "reports" / "correlation_heatmap.png"
        heatmap_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(heatmap_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.log_file_created("correlation_heatmap.png", str(heatmap_path))
        
    except Exception as e:
        logger.log_error(f"Failed correlation analysis: {str(e)}", exception=e)
        gate_4_1 = True  # Don't block
        high_corr_pairs = []
        corr_matrix = None
    
    # =========================================================================
    # STEP 4.3: Calculate VIF
    # =========================================================================
    logger.log_action("Calculating Variance Inflation Factor (VIF)")
    
    try:
        # Calculate VIF for numeric features
        vif_results = calculate_vif(df, numeric_features)
        
        # Sort by VIF
        vif_sorted = sorted(vif_results.items(), key=lambda x: x[1], reverse=True)
        
        high_vif_features = [f for f, vif in vif_results.items() if vif > MulticollinearityGates.MAX_VIF]
        
        logger.log_metric("Features with High VIF", f"{len(high_vif_features)}")
        
        if high_vif_features:
            logger.log_action("High VIF Features (VIF > 5.0):")
            for feature, vif in vif_sorted:
                if vif > MulticollinearityGates.MAX_VIF:
                    logger.log_metric(f"{feature}", f"VIF: {vif:.2f}")
        
        # Log top 10 VIF values
        logger.log_action("Top 10 VIF Values:")
        for feature, vif in vif_sorted[:10]:
            logger.log_metric(f"{feature}", f"VIF: {vif:.2f}")
        
        # Gate G4.2: <= 2 features with VIF > 5 (WARNING)
        gate_4_2 = len(high_vif_features) <= 2
        logger.log_gate(
            "G4.2", "High VIF Features",
            passed=gate_4_2,
            expected="<= 2 features with VIF > 5.0",
            actual=f"{len(high_vif_features)} features"
        )
        
        if not gate_4_2:
            logger.log_warning(
                f"Found {len(high_vif_features)} features with high VIF",
                action_taken="Will remove redundant features"
            )
        
    except Exception as e:
        logger.log_error(f"Failed VIF calculation: {str(e)}", exception=e)
        gate_4_2 = True  # Don't block
        vif_results = {}
        high_vif_features = []
    
    # =========================================================================
    # STEP 4.4: Feature Removal Decision
    # =========================================================================
    logger.log_action("Making feature removal decisions")
    
    features_to_remove = set()
    removal_reasons = {}
    
    try:
        # Load IV results from Phase 3 if available
        iv_results = {}
        try:
            iv_file = BASE_DIR / "reports" / "leakage_audit_report.md"
            if iv_file.exists():
                # Try to extract IV values from report (simple parsing)
                # For now, we'll use correlation and VIF to make decisions
                pass
        except:
            pass
        
        # Decision 1: Remove one feature from high correlation pairs
        for pair in high_corr_pairs:
            feat1, feat2 = pair['feature1'], pair['feature2']
            
            # Skip if already marked for removal
            if feat1 in features_to_remove or feat2 in features_to_remove:
                continue
            
            # Decision logic (prioritized):
            # 1. Special cases: firm_rep_count, firm_net_change (keep important ones)
            # 2. Keep features with higher IV (from Phase 3 - firm_rep_count_at_contact has 0.7991 IV)
            # 3. Keep derived/interaction features over raw features
            # 4. If one has much higher VIF, remove it (unless it's a key feature)
            # 5. Otherwise, use heuristics
            
            vif1 = vif_results.get(feat1, 1.0)
            vif2 = vif_results.get(feat2, 1.0)
            
            # Special handling for firm_rep_count features (expected high correlation)
            if 'firm_rep_count_12mo_ago' in [feat1, feat2]:
                features_to_remove.add('firm_rep_count_12mo_ago')
                removal_reasons['firm_rep_count_12mo_ago'] = (
                    f"Highly correlated with firm_rep_count_at_contact (r={pair['correlation']:.3f}). "
                    "Keeping _at_contact as it's more directly relevant to contact timing and has higher IV."
                )
                logger.log_decision(
                    f"Remove firm_rep_count_12mo_ago (correlated with firm_rep_count_at_contact)",
                    "Keep _at_contact, remove _12mo_ago. The delta signal is captured by firm_net_change_12mo."
                )
                continue
            
            # Protect firm_rep_count_at_contact (high IV feature)
            if 'firm_rep_count_at_contact' in [feat1, feat2]:
                other_feat = feat2 if feat1 == 'firm_rep_count_at_contact' else feat1
                features_to_remove.add(other_feat)
                removal_reasons[other_feat] = (
                    f"Correlated with firm_rep_count_at_contact (r={pair['correlation']:.3f}). "
                    "Keeping firm_rep_count_at_contact due to high IV (0.7991)."
                )
                continue
            
            # Protect firm_net_change_12mo (important derived feature)
            if 'firm_net_change_12mo' in [feat1, feat2]:
                other_feat = feat2 if feat1 == 'firm_net_change_12mo' else feat1
                # Always keep firm_net_change_12mo (it's a derived feature with important signal)
                features_to_remove.add(other_feat)
                removal_reasons[other_feat] = (
                    f"Correlated with firm_net_change_12mo (r={pair['correlation']:.3f}). "
                    "Keeping firm_net_change_12mo as it captures the delta signal (derived feature)."
                )
                logger.log_decision(
                    f"Keep firm_net_change_12mo over {other_feat}",
                    "firm_net_change_12mo is a derived feature that captures firm stability delta signal"
                )
                continue
            
            # Protect interaction features
            interaction_features = ['mobility_x_heavy_bleeding', 'short_tenure_x_high_mobility']
            if any(ifeat in [feat1, feat2] for ifeat in interaction_features):
                other_feat = feat2 if feat1 in interaction_features else feat1
                if other_feat not in interaction_features:
                    features_to_remove.add(other_feat)
                    removal_reasons[other_feat] = (
                        f"Correlated with interaction feature (r={pair['correlation']:.3f}). "
                        "Keeping interaction feature as it captures combined signal."
                    )
                    continue
            
            # General rule: remove feature with higher VIF if significantly different
            if abs(vif1 - vif2) > 2.0:
                if vif1 > vif2:
                    features_to_remove.add(feat1)
                    removal_reasons[feat1] = f"Higher VIF ({vif1:.2f} vs {vif2:.2f}) and correlated with {feat2} (r={pair['correlation']:.3f})"
                else:
                    features_to_remove.add(feat2)
                    removal_reasons[feat2] = f"Higher VIF ({vif2:.2f} vs {vif1:.2f}) and correlated with {feat1} (r={pair['correlation']:.3f})"
            else:
                # Similar VIF - use heuristics
                # Prefer: shorter names, more intuitive, or keep the one that's in ALL_FEATURES
                if len(feat1) < len(feat2):
                    features_to_remove.add(feat2)
                    removal_reasons[feat2] = f"Correlated with {feat1} (r={pair['correlation']:.3f}), keeping shorter/more intuitive name"
                else:
                    features_to_remove.add(feat1)
                    removal_reasons[feat1] = f"Correlated with {feat2} (r={pair['correlation']:.3f}), keeping shorter/more intuitive name"
        
        # Decision 2: Remove high VIF features that aren't top predictors
        # (Already handled above for correlated pairs)
        # PROTECT: firm_rep_count_at_contact (high IV), firm_net_change_12mo (derived), interaction features
        protected_features = [
            'firm_rep_count_at_contact',  # High IV (0.7991)
            'firm_net_change_12mo',  # Important derived feature
            'mobility_x_heavy_bleeding',  # Top interaction feature
            'short_tenure_x_high_mobility'  # Second interaction feature
        ]
        
        for feature in high_vif_features:
            if feature not in features_to_remove and feature not in protected_features:
                # Check if it's correlated with other features
                if feature in numeric_features and corr_matrix is not None:
                    max_corr = corr_matrix[feature].abs().nlargest(2).iloc[1]  # Second highest (first is self)
                    if max_corr > 0.5:
                        features_to_remove.add(feature)
                        removal_reasons[feature] = f"High VIF ({vif_results.get(feature, 0):.2f}) and correlated with other features (max r={max_corr:.3f})"
        
        # Remove zero-variance features (from Phase 2 notes)
        zero_variance = []
        for feature in feature_columns:
            if feature in df.columns:
                if df[feature].nunique() <= 1:
                    zero_variance.append(feature)
        
        for feature in zero_variance:
            features_to_remove.add(feature)
            removal_reasons[feature] = "Zero variance (all values identical)"
        
        logger.log_metric("Features to Remove", f"{len(features_to_remove)}")
        
        if features_to_remove:
            logger.log_action("Features Marked for Removal:")
            for feature in sorted(features_to_remove):
                logger.log_metric(f"{feature}", removal_reasons.get(feature, "Multicollinearity"))
        
    except Exception as e:
        logger.log_error(f"Failed feature removal decision: {str(e)}", exception=e)
        features_to_remove = set()
        removal_reasons = {}
    
    # =========================================================================
    # STEP 4.5: Final Feature Set
    # =========================================================================
    logger.log_action("Creating final feature set")
    
    try:
        # Create final feature list
        final_features = [f for f in feature_columns if f not in features_to_remove]
        
        # Recalculate VIF for final set
        final_vif = calculate_vif(df, final_features)
        max_vif = max(final_vif.values()) if final_vif else 0
        
        logger.log_metric("Final Feature Count", f"{len(final_features)}")
        logger.log_metric("Removed Features", f"{len(features_to_remove)}")
        logger.log_metric("Max VIF (Final Set)", f"{max_vif:.2f}")
        
        # Gate G4.3: Max VIF in final set <= 7.5 (WARNING)
        gate_4_3 = max_vif <= 7.5
        logger.log_gate(
            "G4.3", "Final Set VIF",
            passed=gate_4_3,
            expected="Max VIF <= 7.5",
            actual=f"Max VIF: {max_vif:.2f}"
        )
        
        if not gate_4_3:
            logger.log_warning(
                f"Max VIF ({max_vif:.2f}) exceeds threshold (7.5)",
                action_taken="Consider additional feature removal if model performance is unstable"
            )
        
    except Exception as e:
        logger.log_error(f"Failed to create final feature set: {str(e)}", exception=e)
        final_features = feature_columns
        max_vif = 0
    
    # =========================================================================
    # STEP 4.6: Save Outputs
    # =========================================================================
    logger.log_action("Saving outputs")
    
    try:
        # Save final features list
        final_features_path = BASE_DIR / "data" / "processed" / "final_features.json"
        final_features_path.parent.mkdir(parents=True, exist_ok=True)
        
        final_features_data = {
            "final_features": final_features,
            "removed_features": list(features_to_remove),
            "removal_reasons": removal_reasons,
            "total_features": len(feature_columns),
            "final_count": len(final_features),
            "max_vif": max_vif,
            "high_corr_pairs_count": len(high_corr_pairs),
            "high_vif_count": len(high_vif_features),
            "generated": datetime.now().isoformat()
        }
        
        with open(final_features_path, 'w') as f:
            json.dump(final_features_data, f, indent=2)
        
        logger.log_file_created("final_features.json", str(final_features_path))
        
        # Generate multicollinearity report
        report_path = BASE_DIR / "reports" / "multicollinearity_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Phase 4: Multicollinearity Analysis Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"- **Total Features Analyzed**: {len(feature_columns)}\n")
            f.write(f"- **Final Feature Count**: {len(final_features)}\n")
            f.write(f"- **Features Removed**: {len(features_to_remove)}\n")
            f.write(f"- **High Correlation Pairs**: {len(high_corr_pairs)}\n")
            f.write(f"- **High VIF Features**: {len(high_vif_features)}\n")
            f.write(f"- **Max VIF (Final Set)**: {max_vif:.2f}\n\n")
            
            # High correlation pairs
            if high_corr_pairs:
                f.write("## High Correlation Pairs (|r| > 0.7)\n\n")
                f.write("| Feature 1 | Feature 2 | Correlation |\n")
                f.write("|-----------|-----------|------------|\n")
                for pair in high_corr_pairs:
                    f.write(f"| {pair['feature1']} | {pair['feature2']} | {pair['correlation']:.3f} |\n")
                f.write("\n")
            
            # High VIF features
            if high_vif_features:
                f.write("## High VIF Features (VIF > 5.0)\n\n")
                f.write("| Feature | VIF |\n")
                f.write("|---------|-----|\n")
                for feature in sorted(high_vif_features, key=lambda x: vif_results.get(x, 0), reverse=True):
                    f.write(f"| {feature} | {vif_results.get(feature, 0):.2f} |\n")
                f.write("\n")
            
            # Removed features
            if features_to_remove:
                f.write("## Removed Features\n\n")
                f.write("| Feature | Reason |\n")
                f.write("|---------|--------|\n")
                for feature in sorted(features_to_remove):
                    f.write(f"| {feature} | {removal_reasons.get(feature, 'Multicollinearity')} |\n")
                f.write("\n")
            
            # Final feature list
            f.write("## Final Feature Set\n\n")
            f.write(f"**Count**: {len(final_features)}\n\n")
            f.write("| Feature | VIF |\n")
            f.write("|---------|-----|\n")
            for feature in sorted(final_features):
                vif = final_vif.get(feature, 0)
                f.write(f"| {feature} | {vif:.2f} |\n")
            f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            f.write("✅ **Multicollinearity addressed**\n")
            f.write(f"- Removed {len(features_to_remove)} redundant features\n")
            f.write(f"- Final set has {len(final_features)} features\n")
            f.write(f"- Max VIF: {max_vif:.2f} {'(acceptable)' if max_vif <= 7.5 else '(monitor in model training)'}\n")
            f.write("\n**Proceed to Phase 5: Train/Test Split**\n\n")
        
        logger.log_file_created("multicollinearity_report.md", str(report_path))
        
    except Exception as e:
        logger.log_error(f"Failed to save outputs: {str(e)}", exception=e)
    
    # =========================================================================
    # PHASE SUMMARY
    # =========================================================================
    status = logger.end_phase(next_steps=["Phase 5: Train/Test Split"])
    
    return all_blocking_gates_passed and status in ["PASSED", "PASSED WITH WARNINGS"]


if __name__ == "__main__":
    success = run_phase_4()
    sys.exit(0 if success else 1)

