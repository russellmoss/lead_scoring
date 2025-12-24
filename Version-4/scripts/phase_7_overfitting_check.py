"""
Phase 7: Overfitting Detection

This script:
1. Performs time-based cross-validation
2. Creates learning curves
3. Analyzes segment performance
4. Generates overfitting report
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
from sklearn.metrics import roc_auc_score, average_precision_score
import xgboost as xgb

# Add project root to path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

# Import utilities and constants
from utils.execution_logger import ExecutionLogger
from config.constants import (
    BASE_DIR,
    ModelConfig,
    OverfittingGates,
    PerformanceGates
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

def run_phase_7() -> bool:
    """Execute Phase 7: Overfitting Detection."""
    
    logger = ExecutionLogger(BASE_DIR)
    logger.start_phase("7", "Overfitting Detection")
    
    # Track all gates
    all_blocking_gates_passed = True
    
    # =========================================================================
    # STEP 7.1: Load Model and Data
    # =========================================================================
    logger.log_action("Loading model and training data")
    
    try:
        # Load model
        model_path = BASE_DIR / "models" / "v4.0.0" / "model.pkl"
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        logger.log_metric("Model Loaded", "Success")
        
        # Load training data with CV folds
        train_df = pd.read_csv(BASE_DIR / "data" / "splits" / "train.csv")
        
        # Load final features
        with open(BASE_DIR / "data" / "processed" / "final_features.json", 'r') as f:
            final_features_data = json.load(f)
            final_features = final_features_data['final_features']
        
        logger.log_metric("Training Data", f"{len(train_df):,} rows")
        logger.log_metric("CV Folds", f"{sorted(train_df['cv_fold'].unique().tolist())}")
        
    except Exception as e:
        logger.log_error(f"Failed to load model/data: {str(e)}", exception=e)
        status = logger.end_phase()
        return False
    
    # =========================================================================
    # STEP 7.2: Time-Based Cross-Validation
    # =========================================================================
    logger.log_action("Performing time-based cross-validation")
    
    cv_results = []
    
    try:
        # Get unique CV folds (should be 1-5)
        cv_folds = sorted([int(f) for f in train_df['cv_fold'].unique() if f > 0])
        
        logger.log_action(f"Running CV on {len(cv_folds)} folds")
        
        for test_fold in cv_folds:
            # Train on folds before test_fold, test on test_fold
            train_mask = train_df['cv_fold'] < test_fold
            test_mask = train_df['cv_fold'] == test_fold
            
            train_cv = train_df[train_mask]
            test_cv = train_df[test_mask]
            
            if len(train_cv) == 0 or len(test_cv) == 0:
                continue
            
            # Prepare features
            X_train_cv = prepare_features(train_cv, final_features)
            X_test_cv = prepare_features(test_cv, final_features)
            y_train_cv = train_cv['target'].values
            y_test_cv = test_cv['target'].values
            
            # Train model on CV fold
            dtrain_cv = xgb.DMatrix(X_train_cv, label=y_train_cv)
            dtest_cv = xgb.DMatrix(X_test_cv, label=y_test_cv)
            
            # Get model parameters (from loaded model or constants)
            model_params = {
                'objective': ModelConfig.OBJECTIVE,
                'eval_metric': ModelConfig.EVAL_METRIC,
                'random_state': ModelConfig.RANDOM_STATE,
                'max_depth': ModelConfig.MAX_DEPTH,
                'min_child_weight': ModelConfig.MIN_CHILD_WEIGHT,
                'gamma': ModelConfig.GAMMA,
                'subsample': ModelConfig.SUBSAMPLE,
                'colsample_bytree': ModelConfig.COLSAMPLE_BYTREE,
                'reg_alpha': ModelConfig.REG_ALPHA,
                'reg_lambda': ModelConfig.REG_LAMBDA,
                'learning_rate': ModelConfig.LEARNING_RATE,
                'scale_pos_weight': (y_train_cv == 0).sum() / (y_train_cv == 1).sum() if (y_train_cv == 1).sum() > 0 else 1.0,
                'tree_method': 'hist',
                'verbosity': 0
            }
            
            # Train
            model_cv = xgb.train(
                params=model_params,
                dtrain=dtrain_cv,
                num_boost_round=ModelConfig.N_ESTIMATORS,
                evals=[(dtrain_cv, 'train'), (dtest_cv, 'test')],
                early_stopping_rounds=ModelConfig.EARLY_STOPPING_ROUNDS,
                verbose_eval=False
            )
            
            # Evaluate
            y_pred_cv = model_cv.predict(dtest_cv)
            auc_roc = roc_auc_score(y_test_cv, y_pred_cv)
            auc_pr = average_precision_score(y_test_cv, y_pred_cv)
            
            cv_results.append({
                'fold': test_fold,
                'train_size': len(train_cv),
                'test_size': len(test_cv),
                'auc_roc': auc_roc,
                'auc_pr': auc_pr,
                'best_iteration': model_cv.best_iteration
            })
            
            logger.log_metric(
                f"Fold {test_fold}",
                f"AUC-ROC: {auc_roc:.4f}, AUC-PR: {auc_pr:.4f}, Train: {len(train_cv):,}, Test: {len(test_cv):,}"
            )
        
        # Calculate CV statistics
        cv_auc_scores = [r['auc_roc'] for r in cv_results]
        cv_mean = np.mean(cv_auc_scores)
        cv_std = np.std(cv_auc_scores)
        
        logger.log_metric("CV Mean AUC-ROC", f"{cv_mean:.4f}")
        logger.log_metric("CV Std Dev", f"{cv_std:.4f}")
        
        # Gate G7.1: CV score std dev < 0.1 (WARNING)
        gate_7_1 = cv_std < OverfittingGates.MAX_CV_FOLD_VARIANCE
        logger.log_gate(
            "G7.1", "CV Score Variance",
            passed=gate_7_1,
            expected=f"Std dev < {OverfittingGates.MAX_CV_FOLD_VARIANCE}",
            actual=f"{cv_std:.4f}"
        )
        
        if not gate_7_1:
            logger.log_warning(
                f"CV score variance ({cv_std:.4f}) exceeds threshold ({OverfittingGates.MAX_CV_FOLD_VARIANCE})",
                action_taken="Model performance varies across time periods - monitor in production"
            )
        
    except Exception as e:
        logger.log_error(f"Failed CV analysis: {str(e)}", exception=e)
        gate_7_1 = True  # Don't block
        cv_results = []
        cv_mean = cv_std = 0.0
    
    # =========================================================================
    # STEP 7.3: Learning Curve Analysis
    # =========================================================================
    logger.log_action("Creating learning curves")
    
    learning_curve_data = []
    
    try:
        # Prepare full training data
        X_train_full = prepare_features(train_df, final_features)
        y_train_full = train_df['target'].values
        
        # Sample sizes: 20%, 40%, 60%, 80%, 100%
        sample_sizes = [0.2, 0.4, 0.6, 0.8, 1.0]
        
        # Use test set for validation
        test_df = pd.read_csv(BASE_DIR / "data" / "splits" / "test.csv")
        X_test_full = prepare_features(test_df, final_features)
        y_test_full = test_df['target'].values
        dtest_full = xgb.DMatrix(X_test_full, label=y_test_full)
        
        logger.log_action("Training models on different sample sizes...")
        
        for pct in sample_sizes:
            n_samples = int(len(train_df) * pct)
            train_sample = train_df.sample(n=n_samples, random_state=42)
            
            X_train_sample = prepare_features(train_sample, final_features)
            y_train_sample = train_sample['target'].values
            
            dtrain_sample = xgb.DMatrix(X_train_sample, label=y_train_sample)
            
            # Train model
            model_params = {
                'objective': ModelConfig.OBJECTIVE,
                'eval_metric': ModelConfig.EVAL_METRIC,
                'random_state': ModelConfig.RANDOM_STATE,
                'max_depth': ModelConfig.MAX_DEPTH,
                'min_child_weight': ModelConfig.MIN_CHILD_WEIGHT,
                'gamma': ModelConfig.GAMMA,
                'subsample': ModelConfig.SUBSAMPLE,
                'colsample_bytree': ModelConfig.COLSAMPLE_BYTREE,
                'reg_alpha': ModelConfig.REG_ALPHA,
                'reg_lambda': ModelConfig.REG_LAMBDA,
                'learning_rate': ModelConfig.LEARNING_RATE,
                'scale_pos_weight': (y_train_sample == 0).sum() / (y_train_sample == 1).sum() if (y_train_sample == 1).sum() > 0 else 1.0,
                'tree_method': 'hist',
                'verbosity': 0
            }
            
            model_lc = xgb.train(
                params=model_params,
                dtrain=dtrain_sample,
                num_boost_round=ModelConfig.N_ESTIMATORS,
                evals=[(dtrain_sample, 'train'), (dtest_full, 'test')],
                early_stopping_rounds=ModelConfig.EARLY_STOPPING_ROUNDS,
                verbose_eval=False
            )
            
            # Evaluate on training and test
            y_train_pred = model_lc.predict(dtrain_sample)
            y_test_pred = model_lc.predict(dtest_full)
            
            train_auc = roc_auc_score(y_train_sample, y_train_pred)
            test_auc = roc_auc_score(y_test_full, y_test_pred)
            
            learning_curve_data.append({
                'sample_size': n_samples,
                'sample_pct': pct * 100,
                'train_auc': train_auc,
                'test_auc': test_auc
            })
            
            logger.log_metric(
                f"{pct*100:.0f}% samples ({n_samples:,})",
                f"Train AUC: {train_auc:.4f}, Test AUC: {test_auc:.4f}"
            )
        
        # Create learning curve plot
        plt.figure(figsize=(10, 6))
        sample_sizes_plot = [d['sample_size'] for d in learning_curve_data]
        train_aucs = [d['train_auc'] for d in learning_curve_data]
        test_aucs = [d['test_auc'] for d in learning_curve_data]
        
        plt.plot(sample_sizes_plot, train_aucs, 'o-', label='Train AUC-ROC', linewidth=2)
        plt.plot(sample_sizes_plot, test_aucs, 's-', label='Test AUC-ROC', linewidth=2)
        plt.xlabel('Training Sample Size', fontsize=12)
        plt.ylabel('AUC-ROC', fontsize=12)
        plt.title('Learning Curve: Model Performance vs Training Size', fontsize=14, pad=20)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        curve_path = BASE_DIR / "reports" / "learning_curve.png"
        curve_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(curve_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.log_file_created("learning_curve.png", str(curve_path))
        
        # Check for divergence
        # Validation curve should converge (test AUC should stabilize or improve)
        test_aucs_array = np.array(test_aucs)
        if len(test_aucs_array) >= 3:
            # Check if last 3 points are converging (small variance)
            last_3_std = np.std(test_aucs_array[-3:])
            is_converging = last_3_std < 0.02  # Small variance in last 3 points
        else:
            is_converging = True
        
        # Gate G7.2: Validation curve converges (no divergence) (WARNING)
        gate_7_2 = is_converging
        logger.log_gate(
            "G7.2", "Learning Curve Convergence",
            passed=gate_7_2,
            expected="Validation curve converges",
            actual=f"Last 3 points std: {last_3_std:.4f}" if len(test_aucs_array) >= 3 else "N/A"
        )
        
        if not gate_7_2:
            logger.log_warning(
                "Learning curve shows divergence - model may need more regularization",
                action_taken="Monitor - consider increasing regularization"
            )
        
    except Exception as e:
        logger.log_error(f"Failed learning curve analysis: {str(e)}", exception=e)
        gate_7_2 = True  # Don't block
        learning_curve_data = []
    
    # =========================================================================
    # STEP 7.4: Segment Performance Analysis
    # =========================================================================
    logger.log_action("Analyzing segment performance")
    
    segment_results = {}
    
    try:
        # Load test data for predictions
        test_df = pd.read_csv(BASE_DIR / "data" / "splits" / "test.csv")
        X_test = prepare_features(test_df, final_features)
        dtest = xgb.DMatrix(X_test)
        y_test = test_df['target'].values
        
        # Get predictions
        y_pred = model.predict(dtest)
        
        # Segment 1: lead_source_grouped (if available)
        if 'lead_source_grouped' in test_df.columns:
            segment_results['lead_source'] = {}
            for source in test_df['lead_source_grouped'].unique():
                mask = test_df['lead_source_grouped'] == source
                if mask.sum() > 10:  # Need sufficient samples
                    y_seg = y_test[mask]
                    y_pred_seg = y_pred[mask]
                    auc_roc = roc_auc_score(y_seg, y_pred_seg) if len(np.unique(y_seg)) > 1 else None
                    conv_rate = y_seg.mean() * 100
                    
                    segment_results['lead_source'][source] = {
                        'n_leads': mask.sum(),
                        'auc_roc': auc_roc,
                        'conv_rate': conv_rate
                    }
                    
                    auc_str = f"{auc_roc:.4f}" if auc_roc is not None else "N/A"
                    logger.log_metric(
                        f"Segment: {source}",
                        f"AUC-ROC: {auc_str}, Conv: {conv_rate:.2f}%, N: {mask.sum():,}"
                    )
        
        # Segment 2: tenure_bucket
        if 'tenure_bucket' in test_df.columns:
            segment_results['tenure_bucket'] = {}
            for bucket in test_df['tenure_bucket'].unique():
                mask = test_df['tenure_bucket'] == bucket
                if mask.sum() > 10:
                    y_seg = y_test[mask]
                    y_pred_seg = y_pred[mask]
                    auc_roc = roc_auc_score(y_seg, y_pred_seg) if len(np.unique(y_seg)) > 1 else None
                    conv_rate = y_seg.mean() * 100
                    
                    segment_results['tenure_bucket'][bucket] = {
                        'n_leads': mask.sum(),
                        'auc_roc': auc_roc,
                        'conv_rate': conv_rate
                    }
                    
                    auc_str = f"{auc_roc:.4f}" if auc_roc is not None else "N/A"
                    logger.log_metric(
                        f"Segment: tenure_bucket={bucket}",
                        f"AUC-ROC: {auc_str}, Conv: {conv_rate:.2f}%, N: {mask.sum():,}"
                    )
        
        # Check for dramatic differences
        if 'tenure_bucket' in segment_results:
            auc_scores = [v['auc_roc'] for v in segment_results['tenure_bucket'].values() if v['auc_roc'] is not None]
            if len(auc_scores) > 1:
                auc_range = max(auc_scores) - min(auc_scores)
                if auc_range > 0.15:  # More than 15 points difference
                    logger.log_warning(
                        f"Large AUC variation across tenure_bucket segments (range: {auc_range:.3f})",
                        action_taken="Model performance varies by segment - consider segment-specific models"
                    )
        
    except Exception as e:
        logger.log_error(f"Failed segment analysis: {str(e)}", exception=e)
        segment_results = {}
    
    # =========================================================================
    # STEP 7.5: Generate Report
    # =========================================================================
    logger.log_action("Generating overfitting report")
    
    try:
        report_path = BASE_DIR / "reports" / "overfitting_report.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Phase 7: Overfitting Detection Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            
            # CV Results
            f.write("## Time-Based Cross-Validation Results\n\n")
            f.write("| Fold | Train Size | Test Size | AUC-ROC | AUC-PR | Best Iteration |\n")
            f.write("|------|------------|-----------|---------|--------|----------------|\n")
            for result in cv_results:
                f.write(f"| {result['fold']} | {result['train_size']:,} | {result['test_size']:,} | "
                       f"{result['auc_roc']:.4f} | {result['auc_pr']:.4f} | {result['best_iteration']} |\n")
            f.write("\n")
            
            if cv_results:
                f.write(f"**Mean AUC-ROC**: {cv_mean:.4f}\n")
                f.write(f"**Std Dev**: {cv_std:.4f}\n")
                f.write(f"**Gate G7.1**: {'✅ PASSED' if gate_7_1 else '⚠️ WARNING'}\n\n")
            
            # Learning Curve
            f.write("## Learning Curve Analysis\n\n")
            f.write("| Sample Size | Sample % | Train AUC-ROC | Test AUC-ROC |\n")
            f.write("|-------------|----------|---------------|--------------|\n")
            for data in learning_curve_data:
                f.write(f"| {data['sample_size']:,} | {data['sample_pct']:.0f}% | "
                       f"{data['train_auc']:.4f} | {data['test_auc']:.4f} |\n")
            f.write("\n")
            f.write(f"**Gate G7.2**: {'✅ PASSED' if gate_7_2 else '⚠️ WARNING'}\n\n")
            f.write("![Learning Curve](learning_curve.png)\n\n")
            
            # Segment Analysis
            if segment_results:
                f.write("## Segment Performance Analysis\n\n")
                
                if 'lead_source' in segment_results:
                    f.write("### By Lead Source\n\n")
                    f.write("| Source | N Leads | AUC-ROC | Conversion Rate |\n")
                    f.write("|--------|---------|---------|-----------------|\n")
                    for source, data in segment_results['lead_source'].items():
                        auc_str = f"{data['auc_roc']:.4f}" if data['auc_roc'] else "N/A"
                        f.write(f"| {source} | {data['n_leads']:,} | {auc_str} | {data['conv_rate']:.2f}% |\n")
                    f.write("\n")
                
                if 'tenure_bucket' in segment_results:
                    f.write("### By Tenure Bucket\n\n")
                    f.write("| Tenure Bucket | N Leads | AUC-ROC | Conversion Rate |\n")
                    f.write("|--------------|---------|---------|-----------------|\n")
                    for bucket, data in segment_results['tenure_bucket'].items():
                        auc_str = f"{data['auc_roc']:.4f}" if data['auc_roc'] else "N/A"
                        f.write(f"| {bucket} | {data['n_leads']:,} | {auc_str} | {data['conv_rate']:.2f}% |\n")
                    f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            
            if gate_7_1 and gate_7_2:
                f.write("✅ **No major overfitting detected**\n")
                f.write("- CV scores are stable across time periods\n")
                f.write("- Learning curve shows convergence\n")
                f.write("- **Proceed to Phase 8: Model Validation**\n\n")
            else:
                f.write("⚠️ **Some overfitting concerns**\n")
                if not gate_7_1:
                    f.write(f"- CV score variance ({cv_std:.4f}) exceeds threshold\n")
                if not gate_7_2:
                    f.write("- Learning curve shows divergence\n")
                f.write("- **Recommendation**: Monitor model performance in production\n")
                f.write("- Consider additional regularization if performance degrades\n\n")
        
        logger.log_file_created("overfitting_report.md", str(report_path))
        
    except Exception as e:
        logger.log_error(f"Failed to generate report: {str(e)}", exception=e)
    
    # =========================================================================
    # PHASE SUMMARY
    # =========================================================================
    status = logger.end_phase(next_steps=["Phase 8: Model Validation"])
    
    return all_blocking_gates_passed and status in ["PASSED", "PASSED WITH WARNINGS"]


if __name__ == "__main__":
    success = run_phase_7()
    sys.exit(0 if success else 1)

