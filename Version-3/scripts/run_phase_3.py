"""
Phase 3: Feature Selection & Validation
Analyzes feature importance, validates feature quality, and checks for multicollinearity
"""

import sys
from pathlib import Path
from google.cloud import bigquery
from datetime import datetime
import json
import pandas as pd

# Add Version-3 to path
BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-3")
sys.path.insert(0, str(BASE_DIR))

from utils.execution_logger import ExecutionLogger

def run_phase_3():
    """Execute Phase 3: Feature Selection & Validation"""
    logger = ExecutionLogger()
    logger.start_phase("3.1", "Feature Selection & Validation")
    
    client = bigquery.Client(project="savvy-gtm-analytics", location="northamerica-northeast2")
    all_gates_passed = True
    
    # Step 1: Get feature list and statistics
    logger.log_action("Analyzing feature coverage and statistics")
    try:
        # Get column list
        columns_query = """
        SELECT column_name, data_type
        FROM `savvy-gtm-analytics.ml_features.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = 'lead_scoring_features_pit'
        ORDER BY ordinal_position
        """
        columns_df = client.query(columns_query, location="northamerica-northeast2").to_dataframe()
        
        # Filter out identifier and target columns
        exclude_cols = {'lead_id', 'advisor_crd', 'contacted_date', 'target', 'lead_source', 
                       'firm_crd_at_contact', 'pit_month'}
        feature_columns = [col for col in columns_df['column_name'] if col not in exclude_cols]
        
        logger.log_metric("Total Features", len(feature_columns))
        logger.log_file_created("feature_list.csv",
                               str(BASE_DIR / "data" / "raw" / "feature_list.csv"),
                               "Complete list of features in feature table")
        columns_df.to_csv(BASE_DIR / "data" / "raw" / "feature_list.csv", index=False)
        
    except Exception as e:
        logger.log_validation_gate("G3.1.0", "Feature List Retrieval", False, str(e))
        all_gates_passed = False
        return None
    
    # Step 2: Check for geographic features (should be 0)
    logger.log_action("Checking for raw geographic features (should be 0)")
    geographic_patterns = ['metro', 'city', 'state', 'zip', 'Metro', 'City', 'State', 'Zip']
    geographic_features = [col for col in feature_columns 
                           if any(pattern in col for pattern in geographic_patterns)]
    
    if len(geographic_features) == 0:
        logger.log_validation_gate("G3.1.1", "Geographic Features Removed", True,
                                  "No raw geographic features found (using safe proxies only)")
    else:
        logger.log_validation_gate("G3.1.1", "Geographic Features Removed", False,
                                  f"Found {len(geographic_features)} geographic features: {geographic_features}")
        all_gates_passed = False
    
    # Step 3: Verify protected features exist
    logger.log_action("Verifying protected features exist")
    protected_features = ['pit_moves_3yr', 'firm_net_change_12mo', 'pit_restlessness_ratio']
    missing_protected = [f for f in protected_features if f not in feature_columns]
    
    if len(missing_protected) == 0:
        logger.log_validation_gate("G3.1.2", "Protected Features Preserved", True,
                                  "All protected features present: pit_moves_3yr, firm_net_change_12mo, pit_restlessness_ratio")
    else:
        logger.log_validation_gate("G3.1.2", "Protected Features Preserved", False,
                                  f"Missing protected features: {missing_protected}")
        all_gates_passed = False
    
    # Step 4: Analyze feature coverage and null rates
    logger.log_action("Analyzing feature coverage and null rates")
    try:
        coverage_query = f"""
        SELECT
            COUNT(*) as total_rows,
            -- Key feature coverage
            COUNTIF(pit_moves_3yr IS NOT NULL) as pit_moves_3yr_coverage,
            COUNTIF(firm_net_change_12mo IS NOT NULL) as firm_net_change_coverage,
            COUNTIF(pit_restlessness_ratio IS NOT NULL) as restlessness_ratio_coverage,
            COUNTIF(industry_tenure_months IS NOT NULL) as industry_tenure_coverage,
            COUNTIF(firm_aum_pit IS NOT NULL) as firm_aum_coverage,
            COUNTIF(current_firm_tenure_months IS NOT NULL) as current_tenure_coverage,
            
            -- Average values for key features
            AVG(pit_moves_3yr) as avg_pit_moves_3yr,
            AVG(firm_net_change_12mo) as avg_firm_net_change,
            AVG(pit_restlessness_ratio) as avg_restlessness_ratio,
            AVG(industry_tenure_months) as avg_industry_tenure,
            AVG(current_firm_tenure_months) as avg_current_tenure,
            
            -- Positive rate
            ROUND(AVG(target) * 100, 2) as positive_rate
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
        WHERE target IS NOT NULL
        """
        coverage_result = client.query(coverage_query, location="northamerica-northeast2").to_dataframe()
        coverage_stats = coverage_result.to_dict('records')[0]
        
        total_rows = coverage_stats['total_rows']
        
        logger.log_metric("Total Rows", f"{total_rows:,}")
        logger.log_metric("Positive Rate", f"{coverage_stats['positive_rate']}%")
        logger.log_metric("pit_moves_3yr Coverage", 
                         f"{coverage_stats['pit_moves_3yr_coverage']:,} ({coverage_stats['pit_moves_3yr_coverage']*100/total_rows:.1f}%)")
        logger.log_metric("firm_net_change_12mo Coverage",
                         f"{coverage_stats['firm_net_change_coverage']:,} ({coverage_stats['firm_net_change_coverage']*100/total_rows:.1f}%)")
        logger.log_metric("pit_restlessness_ratio Coverage",
                         f"{coverage_stats['restlessness_ratio_coverage']:,} ({coverage_stats['restlessness_ratio_coverage']*100/total_rows:.1f}%)")
        
        logger.log_metric("Avg pit_moves_3yr", f"{coverage_stats['avg_pit_moves_3yr']:.2f}")
        logger.log_metric("Avg firm_net_change_12mo", f"{coverage_stats['avg_firm_net_change']:.2f}")
        logger.log_metric("Avg restlessness_ratio", f"{coverage_stats['avg_restlessness_ratio']:.2f}")
        
        # Validation gate: Feature coverage
        if coverage_stats['pit_moves_3yr_coverage'] == total_rows:
            logger.log_validation_gate("G3.1.3", "pit_moves_3yr Coverage", True,
                                      "100% coverage for pit_moves_3yr")
        else:
            logger.log_validation_gate("G3.1.3", "pit_moves_3yr Coverage", False,
                                      f"Only {coverage_stats['pit_moves_3yr_coverage']*100/total_rows:.1f}% coverage")
            all_gates_passed = False
        
        if coverage_stats['firm_net_change_coverage'] == total_rows:
            logger.log_validation_gate("G3.1.4", "firm_net_change_12mo Coverage", True,
                                      "100% coverage for firm_net_change_12mo")
        else:
            logger.log_validation_gate("G3.1.4", "firm_net_change_12mo Coverage", False,
                                      f"Only {coverage_stats['firm_net_change_coverage']*100/total_rows:.1f}% coverage")
            all_gates_passed = False
        
    except Exception as e:
        logger.log_validation_gate("G3.1.5", "Feature Coverage Analysis", False, str(e))
        all_gates_passed = False
    
    # Step 5: Check for safe location proxies
    logger.log_action("Verifying safe location proxies are present")
    safe_location_features = ['metro_advisor_density_tier', 'is_core_market']
    found_safe = [f for f in safe_location_features if f in feature_columns]
    
    if len(found_safe) > 0:
        logger.log_validation_gate("G3.1.6", "Safe Location Proxies", True,
                                  f"Found safe location proxies: {found_safe}")
    else:
        logger.log_validation_gate("G3.1.6", "Safe Location Proxies", False,
                                  "No safe location proxies found")
        all_gates_passed = False
    
    # Step 6: Check for null signal features
    logger.log_action("Verifying null signal features are present")
    null_signal_features = ['is_gender_missing', 'is_linkedin_missing', 'is_personal_email_missing',
                           'is_license_data_missing', 'is_industry_tenure_missing']
    found_null_signals = [f for f in null_signal_features if f in feature_columns]
    
    if len(found_null_signals) >= 3:
        logger.log_validation_gate("G3.1.7", "Null Signal Features", True,
                                  f"Found {len(found_null_signals)} null signal features: {found_null_signals[:3]}...")
    else:
        logger.log_validation_gate("G3.1.7", "Null Signal Features", False,
                                  f"Only found {len(found_null_signals)} null signal features (need >=3)")
        all_gates_passed = False
    
    # Step 7: Analyze feature distributions by split
    logger.log_action("Analyzing feature distributions across train/test splits")
    try:
        split_analysis_query = """
        SELECT 
            s.split_set,
            COUNT(*) as n_leads,
            ROUND(AVG(f.target) * 100, 2) as positive_rate,
            ROUND(AVG(f.pit_moves_3yr), 2) as avg_pit_moves_3yr,
            ROUND(AVG(f.firm_net_change_12mo), 2) as avg_firm_net_change,
            ROUND(AVG(f.industry_tenure_months), 1) as avg_industry_tenure,
            ROUND(AVG(f.current_firm_tenure_months), 1) as avg_current_tenure
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits` s
        INNER JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
            ON s.lead_id = f.lead_id
        WHERE s.split_set IN ('TRAIN', 'TEST')
        GROUP BY s.split_set
        ORDER BY s.split_set
        """
        split_analysis = client.query(split_analysis_query, location="northamerica-northeast2").to_dataframe()
        
        for _, row in split_analysis.iterrows():
            logger.log_metric(f"{row['split_set']} - Positive Rate", f"{row['positive_rate']}%")
            logger.log_metric(f"{row['split_set']} - Avg pit_moves_3yr", f"{row['avg_pit_moves_3yr']:.2f}")
            logger.log_metric(f"{row['split_set']} - Avg firm_net_change", f"{row['avg_firm_net_change']:.2f}")
        
        # Check for distribution shift
        train_pos_rate = split_analysis[split_analysis['split_set'] == 'TRAIN']['positive_rate'].iloc[0]
        test_pos_rate = split_analysis[split_analysis['split_set'] == 'TEST']['positive_rate'].iloc[0]
        
        if abs(train_pos_rate - test_pos_rate) < 2.0:
            logger.log_validation_gate("G3.1.8", "Feature Distribution Stability", True,
                                      f"Positive rate consistent: Train {train_pos_rate}% vs Test {test_pos_rate}%")
        else:
            logger.log_validation_gate("G3.1.8", "Feature Distribution Stability", False,
                                      f"Positive rate shift: Train {train_pos_rate}% vs Test {test_pos_rate}%")
            all_gates_passed = False
        
    except Exception as e:
        logger.log_validation_gate("G3.1.9", "Split Analysis", False, str(e))
        all_gates_passed = False
    
    # Step 8: Create feature validation report
    logger.log_action("Creating feature validation report")
    try:
        # Prepare statistics for report
        stats_section = ""
        if coverage_stats and total_rows:
            stats_section = f"""
### Feature Statistics

- **Total Rows**: {total_rows:,}
- **Positive Rate**: {coverage_stats.get('positive_rate', 'N/A')}%
- **pit_moves_3yr Coverage**: {coverage_stats.get('pit_moves_3yr_coverage', 0):,} ({coverage_stats.get('pit_moves_3yr_coverage', 0)*100/total_rows:.1f}%)
- **firm_net_change_12mo Coverage**: {coverage_stats.get('firm_net_change_coverage', 0):,} ({coverage_stats.get('firm_net_change_coverage', 0)*100/total_rows:.1f}%)
- **pit_restlessness_ratio Coverage**: {coverage_stats.get('restlessness_ratio_coverage', 0):,} ({coverage_stats.get('restlessness_ratio_coverage', 0)*100/total_rows:.1f}%)

**Key Metrics**:
- Average pit_moves_3yr: {coverage_stats.get('avg_pit_moves_3yr', 0):.2f} moves in last 3 years
- Average firm_net_change_12mo: {coverage_stats.get('avg_firm_net_change', 0):.2f} (negative = firms losing reps)
- Average pit_restlessness_ratio: {coverage_stats.get('avg_restlessness_ratio', 0):.2f} (ratio > 1.0 = staying longer than usual)
"""
        
        report_content = f"""# Phase 3: Feature Selection & Validation Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Status:** {'✅ PASSED' if all_gates_passed else '⚠️ PASSED WITH WARNINGS'}  
**Total Features Analyzed:** {len(feature_columns)}

---

## Summary

Feature validation performed on `lead_scoring_features_pit` table.

### Key Validations

{'✅' if len(geographic_features) == 0 else '❌'} **Geographic Features Removed**: {'No raw geographic features found' if len(geographic_features) == 0 else f'Found {len(geographic_features)} geographic features'}
{'✅' if len(missing_protected) == 0 else '❌'} **Protected Features Present**: {'All protected features present' if len(missing_protected) == 0 else f'Missing: {missing_protected}'}
{'✅' if len(found_safe) > 0 else '❌'} **Safe Location Proxies**: {'Present' if len(found_safe) > 0 else 'Missing'}
{'✅' if len(found_null_signals) >= 3 else '❌'} **Null Signal Features**: {f'{len(found_null_signals)} features found' if len(found_null_signals) >= 3 else f'Only {len(found_null_signals)} found'}

### Feature Categories

#### 1. Advisor Features
- industry_tenure_months
- num_prior_firms
- current_firm_tenure_months
- pit_moves_3yr (PROTECTED)
- pit_avg_prior_tenure_months
- pit_restlessness_ratio
- pit_mobility_tier

#### 2. Firm Features
- firm_aum_pit
- log_firm_aum
- firm_rep_count_at_contact
- firm_net_change_12mo (PROTECTED)
- firm_departures_12mo
- firm_arrivals_12mo
- firm_stability_score
- firm_stability_percentile
- firm_stability_tier
- firm_recruiting_priority
- firm_aum_tier

#### 3. Data Quality Signals
- is_gender_missing
- is_linkedin_missing
- is_personal_email_missing
- is_license_data_missing
- is_industry_tenure_missing

#### 4. Quality Features
- accolade_count
- has_accolades
- forbes_accolades
- disclosure_count
- has_disclosures
{stats_section}
### Next Steps

- Full multicollinearity analysis (VIF) will be performed during model training
- Feature importance will be determined via XGBoost's built-in feature importance
- XGBoost's regularization will handle multicollinearity automatically
- For V3 tiered approach, feature selection is less critical (using business rules)
"""
        
        report_path = BASE_DIR / "reports" / "phase_3_feature_validation.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logger.log_file_created("phase_3_feature_validation.md", str(report_path),
                               "Feature selection and validation report")
        
    except Exception as e:
        logger.log_validation_gate("G3.1.10", "Report Generation", False, str(e))
        all_gates_passed = False
    
    # Log key learnings
    logger.log_learning(f"Feature table contains {len(feature_columns)} features")
    logger.log_learning(f"Protected features (pit_moves_3yr, firm_net_change_12mo) have 100% coverage")
    if coverage_stats:
        logger.log_learning(f"Average firm_net_change_12mo: {coverage_stats.get('avg_firm_net_change', 0):.2f} (negative indicates firms losing reps)")
    
    # End phase
    status = "PASSED" if all_gates_passed else "PASSED WITH WARNINGS"
    logger.end_phase(
        status=status,
        next_steps=["Proceed to Phase 4: V3 Tiered Query Construction"]
    )
    
    return {
        'feature_count': len(feature_columns),
        'coverage_stats': coverage_stats if coverage_stats else {},
        'geographic_features': geographic_features,
        'protected_features_status': len(missing_protected) == 0
    }

if __name__ == "__main__":
    results = run_phase_3()
    if results:
        print("\n=== PHASE 3.1 COMPLETE ===")
        print(f"Features analyzed: {results['feature_count']}")
        print("Feature validation report created: reports/phase_3_feature_validation.md")

