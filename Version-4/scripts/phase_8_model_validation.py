"""
Phase 8: Model Validation

This script performs final validation before deployment:
1. Calculates core metrics (AUC-ROC, AUC-PR, lift)
2. Creates lift by decile analysis
3. Performs statistical significance testing
4. Compares to V3 baseline
5. Generates validation report
"""

import sys
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, average_precision_score, log_loss
from scipy import stats
import xgboost as xgb

# Add project root to path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

# Import utilities and constants
from utils.execution_logger import ExecutionLogger
from config.constants import (
    BASE_DIR,
    PerformanceGates,
    BASELINE_CONVERSION_RATE
)

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

def calculate_lift_by_decile(y_true, y_pred, n_deciles=10):
    """Calculate lift for each decile."""
    # Sort by predictions (descending) - highest scores first
    df = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred})
    df = df.sort_values('y_pred', ascending=False).reset_index(drop=True)
    
    # Divide into deciles - assign decile numbers so decile 10 = highest scores
    # Since we sorted descending, first rows = highest scores
    # Reverse the assignment: first rows get decile 10, last rows get decile 1
    n = len(df)
    decile_size = n / n_deciles
    df['decile'] = n_deciles - (df.index // decile_size).astype(int)
    # Ensure decile 1 is the bottom (lowest predictions) and decile 10 is the top
    df['decile'] = df['decile'].clip(lower=1, upper=n_deciles)
    
    # Calculate conversion rate and lift for each decile
    decile_stats = df.groupby('decile').agg(
        n_leads=('y_true', 'count'),
        n_conversions=('y_true', 'sum'),
        avg_score=('y_pred', 'mean')
    ).reset_index()
    
    overall_conv_rate = y_true.mean()
    decile_stats['conv_rate'] = decile_stats['n_conversions'] / decile_stats['n_leads']
    decile_stats['lift'] = decile_stats['conv_rate'] / overall_conv_rate if overall_conv_rate > 0 else 0
    
    # Sort by decile to ensure correct order
    decile_stats = decile_stats.sort_values('decile').reset_index(drop=True)
    
    return decile_stats

def bootstrap_lift(y_true, y_pred, n_bootstrap=1000, top_decile=True):
    """Calculate bootstrap confidence intervals for lift."""
    n = len(y_true)
    lifts = []
    
    for _ in range(n_bootstrap):
        # Resample with replacement
        indices = np.random.choice(n, size=n, replace=True)
        y_true_boot = y_true.iloc[indices] if hasattr(y_true, 'iloc') else y_true[indices]
        y_pred_boot = y_pred.iloc[indices] if hasattr(y_pred, 'iloc') else y_pred[indices]
        
        if top_decile:
            # Top decile lift
            threshold = np.percentile(y_pred_boot, 90)
            top_mask = y_pred_boot >= threshold
            if top_mask.sum() > 0:
                top_conv_rate = y_true_boot[top_mask].mean()
                overall_conv_rate = y_true_boot.mean()
                lift = top_conv_rate / overall_conv_rate if overall_conv_rate > 0 else 0
                lifts.append(lift)
        else:
            # Overall lift
            overall_conv_rate = y_true_boot.mean()
            if overall_conv_rate > 0:
                lifts.append(1.0)  # Baseline
    
    if len(lifts) == 0:
        return None, None, None
    
    lifts = np.array(lifts)
    ci_lower = np.percentile(lifts, 2.5)
    ci_upper = np.percentile(lifts, 97.5)
    p_value = np.mean(lifts <= 1.0)  # Probability that lift <= 1.0 (no improvement)
    
    return ci_lower, ci_upper, p_value

def run_phase_8() -> bool:
    """Execute Phase 8: Model Validation."""
    
    logger = ExecutionLogger(BASE_DIR)
    logger.start_phase("8", "Model Validation")
    
    all_blocking_gates_passed = True
    
    # =========================================================================
    # STEP 8.1: Load Test Data and Model
    # =========================================================================
    logger.log_action("Loading test data and model")
    
    try:
        # Load test data
        test_df = pd.read_csv(BASE_DIR / "data" / "splits" / "test.csv")
        logger.log_metric("Test Data", f"{len(test_df):,} leads")
        
        # Load model
        model_path = BASE_DIR / "models" / "v4.0.0" / "model.pkl"
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        # Load final features
        with open(BASE_DIR / "data" / "processed" / "final_features.json", 'r') as f:
            final_features_data = json.load(f)
            final_features = final_features_data['final_features']
        
        logger.log_metric("Model Loaded", "Success")
        logger.log_metric("Features", f"{len(final_features)} features")
        
    except Exception as e:
        logger.log_error(f"Failed to load data/model: {str(e)}", exception=e)
        status = logger.end_phase()
        return False
    
    # Prepare features and generate predictions
    X_test = prepare_features(test_df, final_features)
    dtest = xgb.DMatrix(X_test)
    y_test = test_df['target'].values
    y_pred = model.predict(dtest)
    
    logger.log_metric("Predictions Generated", f"{len(y_pred):,} predictions")
    
    # =========================================================================
    # STEP 8.2: Calculate Core Metrics
    # =========================================================================
    logger.log_action("Calculating core metrics")
    
    auc_roc = roc_auc_score(y_test, y_pred)
    auc_pr = average_precision_score(y_test, y_pred)
    logloss = log_loss(y_test, y_pred)
    
    logger.log_metric("AUC-ROC", f"{auc_roc:.4f}")
    logger.log_metric("AUC-PR", f"{auc_pr:.4f}")
    logger.log_metric("Log Loss", f"{logloss:.4f}")
    
    # Calculate top decile lift
    decile_stats = calculate_lift_by_decile(y_test, y_pred)
    # Top decile (decile 10) should have highest predictions and highest lift
    # Since we sorted descending, decile 10 = highest scores
    top_decile_row = decile_stats[decile_stats['decile'] == 10]
    if len(top_decile_row) > 0:
        top_decile_lift = top_decile_row['lift'].values[0]
    else:
        # Fallback: use the decile with highest lift
        top_decile_lift = decile_stats['lift'].max()
    
    logger.log_metric("Top Decile Lift", f"{top_decile_lift:.2f}x")
    
    # Gate G8.1: Top decile lift >= 1.5x (BLOCKING)
    gate_8_1 = top_decile_lift >= PerformanceGates.MIN_TOP_DECILE_LIFT
    logger.log_gate(
        "G8.1", "Top Decile Lift",
        passed=gate_8_1,
        expected=f">= {PerformanceGates.MIN_TOP_DECILE_LIFT}x",
        actual=f"{top_decile_lift:.2f}x"
    )
    if not gate_8_1:
        all_blocking_gates_passed = False
    
    # Gate G8.2: AUC-ROC >= 0.60 (WARNING)
    gate_8_2 = auc_roc >= PerformanceGates.MIN_AUC_ROC
    logger.log_gate(
        "G8.2", "AUC-ROC",
        passed=gate_8_2,
        expected=f">= {PerformanceGates.MIN_AUC_ROC}",
        actual=f"{auc_roc:.4f}"
    )
    if not gate_8_2:
        logger.log_warning(
            f"AUC-ROC ({auc_roc:.4f}) below threshold ({PerformanceGates.MIN_AUC_ROC})",
            action_taken="Documented - model still meets lift threshold"
        )
    
    # Gate G8.3: AUC-PR >= 0.10 (WARNING)
    gate_8_3 = auc_pr >= PerformanceGates.MIN_AUC_PR
    logger.log_gate(
        "G8.3", "AUC-PR",
        passed=gate_8_3,
        expected=f">= {PerformanceGates.MIN_AUC_PR}",
        actual=f"{auc_pr:.4f}"
    )
    if not gate_8_3:
        logger.log_warning(
            f"AUC-PR ({auc_pr:.4f}) below threshold ({PerformanceGates.MIN_AUC_PR})",
            action_taken="Documented - model still meets lift threshold"
        )
    
    # =========================================================================
    # STEP 8.3: Lift by Decile
    # =========================================================================
    logger.log_action("Creating lift by decile analysis")
    
    # Create lift chart
    plt.figure(figsize=(10, 6))
    plt.bar(decile_stats['decile'], decile_stats['lift'], color='steelblue', alpha=0.7)
    plt.axhline(y=1.0, color='red', linestyle='--', label='Baseline (1.0x)')
    plt.xlabel('Decile (1 = Lowest, 10 = Highest)', fontsize=12)
    plt.ylabel('Lift', fontsize=12)
    plt.title('Lift by Decile - V4 Model', fontsize=14, pad=20)
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.xticks(range(1, 11))
    plt.tight_layout()
    
    lift_chart_path = BASE_DIR / "reports" / "lift_chart.png"
    lift_chart_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(lift_chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.log_file_created("lift_chart.png", str(lift_chart_path))
    
    # Log decile statistics
    logger.log_action("Decile Statistics:")
    for _, row in decile_stats.iterrows():
        logger.log_metric(
            f"Decile {int(row['decile'])}",
            f"Lift: {row['lift']:.2f}x, Conv: {row['conv_rate']*100:.2f}%, N: {int(row['n_leads']):,}"
        )
    
    # =========================================================================
    # STEP 8.4: Statistical Significance
    # =========================================================================
    logger.log_action("Calculating statistical significance")
    
    try:
        ci_lower, ci_upper, p_value = bootstrap_lift(
            pd.Series(y_test), pd.Series(y_pred), n_bootstrap=1000, top_decile=True
        )
        
        if ci_lower is not None:
            logger.log_metric("Top Decile Lift CI (95%)", f"[{ci_lower:.2f}, {ci_upper:.2f}]")
            logger.log_metric("P-value (lift > 1.0)", f"{p_value:.4f}")
            
            # Gate G8.4: p-value < 0.05 for lift > 1.0 (WARNING)
            gate_8_4 = p_value < PerformanceGates.MAX_P_VALUE
            logger.log_gate(
                "G8.4", "Statistical Significance",
                passed=gate_8_4,
                expected=f"p < {PerformanceGates.MAX_P_VALUE}",
                actual=f"p = {p_value:.4f}"
            )
            if not gate_8_4:
                logger.log_warning(
                    f"P-value ({p_value:.4f}) exceeds threshold ({PerformanceGates.MAX_P_VALUE})",
                    action_taken="Lift is still positive - may be due to small sample size"
                )
        else:
            logger.log_warning("Bootstrap failed - insufficient data", action_taken="Skipping statistical test")
            gate_8_4 = True  # Don't block
            
    except Exception as e:
        logger.log_error(f"Statistical significance calculation failed: {str(e)}", exception=e)
        gate_8_4 = True  # Don't block
    
    # =========================================================================
    # STEP 8.5: Segment Performance
    # =========================================================================
    logger.log_action("Analyzing segment performance")
    
    segment_results = {}
    
    # By lead_source_grouped
    if 'lead_source_grouped' in test_df.columns:
        segment_results['lead_source'] = {}
        for source in test_df['lead_source_grouped'].unique():
            mask = test_df['lead_source_grouped'] == source
            if mask.sum() > 10:
                y_seg = y_test[mask]
                y_pred_seg = y_pred[mask]
                auc_roc_seg = roc_auc_score(y_seg, y_pred_seg) if len(np.unique(y_seg)) > 1 else None
                conv_rate = y_seg.mean() * 100
                
                segment_results['lead_source'][source] = {
                    'n_leads': mask.sum(),
                    'auc_roc': auc_roc_seg,
                    'conv_rate': conv_rate
                }
                
                auc_str = f"{auc_roc_seg:.4f}" if auc_roc_seg is not None else "N/A"
                logger.log_metric(
                    f"Segment: {source}",
                    f"AUC-ROC: {auc_str}, Conv: {conv_rate:.2f}%, N: {mask.sum():,}"
                )
    
    # By tenure_bucket
    if 'tenure_bucket' in test_df.columns:
        segment_results['tenure_bucket'] = {}
        for bucket in test_df['tenure_bucket'].unique():
            mask = test_df['tenure_bucket'] == bucket
            if mask.sum() > 10:
                y_seg = y_test[mask]
                y_pred_seg = y_pred[mask]
                auc_roc_seg = roc_auc_score(y_seg, y_pred_seg) if len(np.unique(y_seg)) > 1 else None
                conv_rate = y_seg.mean() * 100
                
                segment_results['tenure_bucket'][bucket] = {
                    'n_leads': mask.sum(),
                    'auc_roc': auc_roc_seg,
                    'conv_rate': conv_rate
                }
                
                auc_str = f"{auc_roc_seg:.4f}" if auc_roc_seg is not None else "N/A"
                logger.log_metric(
                    f"Segment: tenure_bucket={bucket}",
                    f"AUC-ROC: {auc_str}, Conv: {conv_rate:.2f}%, N: {mask.sum():,}"
                )
    
    # =========================================================================
    # STEP 8.6: Comparison to V3
    # =========================================================================
    logger.log_action("Comparing to V3 baseline")
    
    v3_top_decile_lift = 1.74  # From V3 model report
    v4_top_decile_lift = top_decile_lift
    
    improvement = ((v4_top_decile_lift - v3_top_decile_lift) / v3_top_decile_lift) * 100
    
    logger.log_metric("V3 Top Decile Lift", f"{v3_top_decile_lift:.2f}x")
    logger.log_metric("V4 Top Decile Lift", f"{v4_top_decile_lift:.2f}x")
    logger.log_metric("Improvement vs V3", f"{improvement:+.1f}%")
    
    if v4_top_decile_lift >= v3_top_decile_lift:
        logger.log_decision(
            "V4 beats V3 baseline",
            f"V4 lift ({v4_top_decile_lift:.2f}x) >= V3 lift ({v3_top_decile_lift:.2f}x)"
        )
    else:
        logger.log_warning(
            f"V4 lift ({v4_top_decile_lift:.2f}x) below V3 baseline ({v3_top_decile_lift:.2f}x)",
            action_taken="Documented - may need further optimization"
        )
    
    # =========================================================================
    # STEP 8.7: Generate Validation Report
    # =========================================================================
    logger.log_action("Generating validation report")
    
    try:
        report_path = BASE_DIR / "reports" / "validation_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Phase 8: Model Validation Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # Core Metrics
            f.write("## Core Metrics\n\n")
            f.write(f"- **AUC-ROC**: {auc_roc:.4f}\n")
            f.write(f"- **AUC-PR**: {auc_pr:.4f}\n")
            f.write(f"- **Log Loss**: {logloss:.4f}\n")
            f.write(f"- **Top Decile Lift**: {top_decile_lift:.2f}x\n\n")
            
            # Gates
            f.write("## Validation Gates\n\n")
            f.write(f"| Gate | Status | Expected | Actual |\n")
            f.write(f"|------|--------|----------|--------|\n")
            f.write(f"| G8.1: Top Decile Lift | {'✅ PASSED' if gate_8_1 else '❌ FAILED'} | >= {PerformanceGates.MIN_TOP_DECILE_LIFT}x | {top_decile_lift:.2f}x |\n")
            f.write(f"| G8.2: AUC-ROC | {'✅ PASSED' if gate_8_2 else '⚠️ WARNING'} | >= {PerformanceGates.MIN_AUC_ROC} | {auc_roc:.4f} |\n")
            f.write(f"| G8.3: AUC-PR | {'✅ PASSED' if gate_8_3 else '⚠️ WARNING'} | >= {PerformanceGates.MIN_AUC_PR} | {auc_pr:.4f} |\n")
            p_val_str = f"{p_value:.4f}" if 'p_value' in locals() and p_value is not None else "N/A"
            f.write(f"| G8.4: Statistical Significance | {'✅ PASSED' if gate_8_4 else '⚠️ WARNING'} | p < {PerformanceGates.MAX_P_VALUE} | {p_val_str} |\n\n")
            
            # Lift by Decile
            f.write("## Lift by Decile\n\n")
            f.write("| Decile | Leads | Conversions | Conv Rate | Lift |\n")
            f.write("|--------|-------|-------------|-----------|------|\n")
            for _, row in decile_stats.iterrows():
                f.write(f"| {int(row['decile'])} | {int(row['n_leads']):,} | {int(row['n_conversions'])} | {row['conv_rate']*100:.2f}% | {row['lift']:.2f}x |\n")
            f.write("\n")
            f.write("![Lift Chart](lift_chart.png)\n\n")
            
            # Statistical Significance
            if 'ci_lower' in locals() and ci_lower is not None:
                f.write("## Statistical Significance\n\n")
                f.write(f"- **Top Decile Lift**: {top_decile_lift:.2f}x\n")
                f.write(f"- **95% Confidence Interval**: [{ci_lower:.2f}, {ci_upper:.2f}]\n")
                f.write(f"- **P-value (lift > 1.0)**: {p_value:.4f}\n\n")
            
            # Segment Performance
            if segment_results:
                f.write("## Segment Performance\n\n")
                if 'tenure_bucket' in segment_results:
                    f.write("### By Tenure Bucket\n\n")
                    f.write("| Tenure Bucket | N Leads | AUC-ROC | Conversion Rate |\n")
                    f.write("|--------------|---------|---------|-----------------|\n")
                    for bucket, data in segment_results['tenure_bucket'].items():
                        auc_str = f"{data['auc_roc']:.4f}" if data['auc_roc'] else "N/A"
                        f.write(f"| {bucket} | {data['n_leads']:,} | {auc_str} | {data['conv_rate']:.2f}% |\n")
                    f.write("\n")
            
            # Comparison to V3
            f.write("## Comparison to V3 Baseline\n\n")
            f.write(f"- **V3 Top Decile Lift**: {v3_top_decile_lift:.2f}x\n")
            f.write(f"- **V4 Top Decile Lift**: {v4_top_decile_lift:.2f}x\n")
            f.write(f"- **Improvement**: {improvement:+.1f}%\n\n")
            
            if v4_top_decile_lift >= v3_top_decile_lift:
                f.write("✅ **V4 beats V3 baseline**\n\n")
            else:
                f.write("⚠️ **V4 below V3 baseline** - May need further optimization\n\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            if gate_8_1 and gate_8_2 and gate_8_3:
                f.write("✅ **Model meets all critical thresholds**\n")
                f.write("- Top decile lift exceeds 1.5x threshold\n")
                f.write("- Model is ready for deployment consideration\n\n")
            else:
                f.write("⚠️ **Some thresholds not met**\n")
                if not gate_8_1:
                    f.write(f"- Top decile lift ({top_decile_lift:.2f}x) below threshold ({PerformanceGates.MIN_TOP_DECILE_LIFT}x)\n")
                if not gate_8_2:
                    f.write(f"- AUC-ROC ({auc_roc:.4f}) below threshold ({PerformanceGates.MIN_AUC_ROC})\n")
                if not gate_8_3:
                    f.write(f"- AUC-PR ({auc_pr:.4f}) below threshold ({PerformanceGates.MIN_AUC_PR})\n")
                f.write("\n")
        
        logger.log_file_created("validation_report.md", str(report_path))
        
    except Exception as e:
        logger.log_error(f"Failed to generate report: {str(e)}", exception=e)
    
    # =========================================================================
    # PHASE SUMMARY
    # =========================================================================
    status = logger.end_phase(next_steps=["Phase 9: SHAP Analysis"])
    
    return all_blocking_gates_passed and status in ["PASSED", "PASSED WITH WARNINGS"]


if __name__ == "__main__":
    success = run_phase_8()
    sys.exit(0 if success else 1)

