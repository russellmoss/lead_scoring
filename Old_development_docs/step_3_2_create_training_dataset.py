"""
Step 3.2: Apply Feature Engineering & Create Final Training Set (V6)
Creates the final training dataset with engineered features for 30-day MQL target
"""

from google.cloud import bigquery
from datetime import datetime
import sys

# Use the version from Step 3.1
STAGING_VERSION = "20251104_2217"
version = STAGING_VERSION  # Use same version for output

SQL = f"""
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}` AS
WITH
StagingData AS (
    SELECT * FROM `savvy-gtm-analytics.LeadScoring.step_3_1_staging_join_v6_{STAGING_VERSION}`
),
EngineeredData AS (
    SELECT
        p.*,
        
        -- ===== FINANCIAL-DERIVED FEATURES (NULL - Not Available) =====
        CAST(NULL AS FLOAT64) as AUM_per_Client,
        CAST(NULL AS FLOAT64) as AUM_per_IARep,
        CAST(NULL AS FLOAT64) as Clients_per_IARep,
        CAST(NULL AS FLOAT64) as Clients_per_BranchAdvisor,
        CAST(NULL AS FLOAT64) as Branch_Advisor_Density,
        CAST(NULL AS FLOAT64) as HNW_Client_Ratio,
        CAST(NULL AS FLOAT64) as HNW_Asset_Concentration,
        CAST(NULL AS FLOAT64) as Individual_Asset_Ratio,
        CAST(NULL AS FLOAT64) as Alternative_Investment_Focus,
        CAST(NULL AS INT64) as Positive_Growth_Trajectory,
        CAST(NULL AS INT64) as Accelerating_Growth,
        
        -- ===== A) REP & FIRM MATURITY PROXIES (PIT-Safe) =====
        CASE WHEN p.DateBecameRep_NumberOfYears >= 10 THEN 1 ELSE 0 END as is_veteran_advisor,
        CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears < 2 THEN 1 ELSE 0 END as is_new_to_firm,
        CASE WHEN p.AverageTenureAtPriorFirms < 3 THEN 1 ELSE 0 END as avg_prior_firm_tenure_lt3,
        CASE WHEN p.NumberOfPriorFirms > 3 AND p.AverageTenureAtPriorFirms < 3 THEN 1 ELSE 0 END as high_turnover_flag,
        CASE WHEN p.NumberRIAFirmAssociations > 1 THEN 1 ELSE 0 END as multi_ria_relationships,
        CASE WHEN (p.NumberFirmAssociations > 2 OR p.NumberRIAFirmAssociations > 1) THEN 1 ELSE 0 END as complex_registration,
        CASE WHEN p.Number_RegisteredStates > 10 THEN 1 ELSE 0 END as multi_state_registered,
        SAFE_DIVIDE(p.DateOfHireAtCurrentFirm_NumberOfYears, NULLIF((p.NumberOfPriorFirms + 1), 0)) as Firm_Stability_Score,
        
        -- ===== B) LICENSES/DESIGNATIONS FOOTPRINT (Boolean Rollups) =====
        (COALESCE(p.Has_Series_7, 0) + COALESCE(p.Has_Series_65, 0) + COALESCE(p.Has_Series_66, 0) + COALESCE(p.Has_Series_24, 0)) AS license_count,
        (COALESCE(p.Has_CFP, 0) + COALESCE(p.Has_CFA, 0) + COALESCE(p.Has_CIMA, 0) + COALESCE(p.Has_AIF, 0)) AS designation_count,
        
        -- ===== C) GEOGRAPHY & LOGISTICS (Operational Friction) =====
        CASE 
            WHEN p.Branch_State IS NOT NULL AND p.Home_State IS NOT NULL AND p.Branch_State != p.Home_State THEN 1 
            ELSE 0 
        END AS branch_vs_home_mismatch,
        CASE 
            WHEN p.Home_MetropolitanArea IS NULL AND p.Home_ZipCode IS NOT NULL THEN SUBSTR(CAST(CAST(p.Home_ZipCode AS INT64) AS STRING), 1, 3)
            ELSE NULL
        END as Home_Zip_3Digit,
        CASE WHEN p.MilesToWork > 50 THEN 1 ELSE 0 END as remote_work_indicator,
        CASE WHEN p.MilesToWork <= 10 THEN 1 ELSE 0 END as local_advisor,
        
        -- ===== D) FIRM CONTEXT (Rep-Level Aggregates from Firm Snapshot) =====
        CASE
            WHEN p.total_reps IS NULL THEN NULL
            WHEN p.total_reps = 1 THEN '1'
            WHEN p.total_reps BETWEEN 2 AND 5 THEN '2_5'
            WHEN p.total_reps BETWEEN 6 AND 20 THEN '6_20'
            ELSE '21_plus'
        END AS firm_rep_count_bin,
        
        -- ===== E) CONTACTABILITY & PRESENCE =====
        CASE WHEN COALESCE(p.Has_LinkedIn, 0) = 1 THEN 1 ELSE 0 END AS has_linkedin_engineered,
        -- Note: Email fields not available in staging table, using SocialMedia_LinkedIn as proxy
        CASE WHEN p.SocialMedia_LinkedIn IS NOT NULL THEN 1 ELSE 0 END AS email_business_type_flag,
        CASE WHEN p.SocialMedia_LinkedIn IS NOT NULL THEN 1 ELSE 0 END AS email_personal_type_flag,
        
        -- ===== F) MISSINGNESS AS SIGNAL (Never Silently Impute) =====
        CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears IS NULL THEN 1 ELSE 0 END AS doh_current_years_is_missing,
        CASE WHEN p.DateBecameRep_NumberOfYears IS NULL THEN 1 ELSE 0 END AS became_rep_years_is_missing,
        CASE WHEN p.AverageTenureAtPriorFirms IS NULL THEN 1 ELSE 0 END AS avg_prior_firm_tenure_is_missing,
        CASE WHEN p.NumberOfPriorFirms IS NULL THEN 1 ELSE 0 END AS num_prior_firms_is_missing,
        CASE WHEN p.Number_RegisteredStates IS NULL THEN 1 ELSE 0 END AS num_registered_states_is_missing,
        CASE WHEN p.total_reps IS NULL THEN 1 ELSE 0 END AS firm_total_reps_is_missing,
        (
            (CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.DateBecameRep_NumberOfYears IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.AverageTenureAtPriorFirms IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.NumberOfPriorFirms IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.Number_RegisteredStates IS NULL THEN 1 ELSE 0 END) +
            (CASE WHEN p.total_reps IS NULL THEN 1 ELSE 0 END)
        ) AS missing_feature_count,
        
        -- ===== G) SIMPLE INTERACTIONS (Bounded; Avoid Blow-ups) =====
        (CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears < 2 THEN 1 ELSE 0 END) * COALESCE(p.Has_Series_65, 0) AS is_new_to_firm_x_has_series65,
        (CASE WHEN p.DateBecameRep_NumberOfYears >= 10 THEN 1 ELSE 0 END) * COALESCE(p.Has_CFP, 0) AS veteran_x_cfp,
        
        -- Additional derived features
        SAFE_DIVIDE(p.Number_BranchAdvisors, NULLIF(p.NumberFirmAssociations, 0)) as Branch_Advisors_per_Firm_Association,
        
        -- Labels
        CASE 
            WHEN p.Stage_Entered_Call_Scheduled__c IS NOT NULL 
             AND DATE(p.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(p.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
            THEN 1 ELSE 0 
        END as target_label,
        
        -- Filters
        (DATE(p.Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as is_in_right_censored_window,
        DATE_DIFF(DATE(p.Stage_Entered_Call_Scheduled__c), DATE(p.Stage_Entered_Contacting__c), DAY) as days_to_conversion
    FROM StagingData p
)
SELECT 
    e.Id,
    e.FA_CRD__c,
    e.RIAFirmCRD,
    e.target_label,
    -- Reps Keep
    e.TotalAssetsInMillions, e.TotalAssets_PooledVehicles, e.TotalAssets_SeparatelyManagedAccounts,
    e.NumberClients_Individuals, e.NumberClients_HNWIndividuals, e.NumberClients_RetirementPlans,
    e.PercentClients_Individuals, e.PercentClients_HNWIndividuals, e.AssetsInMillions_MutualFunds,
    e.AssetsInMillions_PrivateFunds, e.AssetsInMillions_Equity_ExchangeTraded, e.PercentAssets_MutualFunds,
    e.PercentAssets_PrivateFunds, e.PercentAssets_Equity_ExchangeTraded, e.Number_IAReps,
    e.Number_BranchAdvisors, e.NumberFirmAssociations, e.NumberRIAFirmAssociations, e.AUMGrowthRate_1Year,
    e.AUMGrowthRate_5Year, e.DateBecameRep_NumberOfYears, e.DateOfHireAtCurrentFirm_NumberOfYears,
    e.Number_YearsPriorFirm1, e.Number_YearsPriorFirm2, e.Number_YearsPriorFirm3, e.Number_YearsPriorFirm4,
    e.AverageTenureAtPriorFirms, e.NumberOfPriorFirms, e.IsPrimaryRIAFirm, e.DuallyRegisteredBDRIARep,
    e.Has_Series_7, e.Has_Series_65, e.Has_Series_66, e.Has_Series_24, e.Has_CFP, e.Has_CFA, e.Has_CIMA,
    e.Has_AIF, e.Has_Disclosure, e.Is_BreakawayRep, e.Has_Insurance_License, e.Is_NonProducer,
    e.Is_IndependentContractor, e.Is_Owner, e.Office_USPS_Certified, e.Home_USPS_Certified,
    e.Home_MetropolitanArea, e.Branch_State, e.Home_State,
    e.MilesToWork, e.SocialMedia_LinkedIn, e.CustodianAUM_Schwab, e.CustodianAUM_Fidelity_NationalFinancial,
    e.CustodianAUM_Pershing, e.CustodianAUM_TDAmeritrade, e.Has_Schwab_Relationship,
    e.Has_Fidelity_Relationship, e.Has_Pershing_Relationship, e.Has_TDAmeritrade_Relationship,
    e.Number_RegisteredStates,
    -- Firms Keep
    e.total_firm_aum_millions, e.total_reps, e.total_firm_clients, e.total_firm_hnw_clients,
    e.avg_clients_per_rep, e.aum_per_rep, e.avg_firm_growth_1y, e.avg_firm_growth_5y,
    e.pct_reps_with_cfp, e.pct_reps_with_disclosure, e.firm_size_tier, e.multi_state_firm, e.national_firm,
    -- Engineered Features (No-Financials, 30-Day MQL Target)
    -- A) Rep & Firm Maturity Proxies
    e.is_veteran_advisor, e.is_new_to_firm, e.avg_prior_firm_tenure_lt3, e.high_turnover_flag,
    e.multi_ria_relationships, e.complex_registration, e.multi_state_registered, e.Firm_Stability_Score,
    -- B) Licenses/Designations Footprint
    e.license_count, e.designation_count,
    -- C) Geography & Logistics
    e.branch_vs_home_mismatch, e.Home_Zip_3Digit, e.remote_work_indicator, e.local_advisor,
    -- D) Firm Context
    e.firm_rep_count_bin,
    -- E) Contactability & Presence
    e.has_linkedin_engineered as has_linkedin, e.email_business_type_flag, e.email_personal_type_flag,
    -- F) Missingness as Signal
    e.doh_current_years_is_missing, e.became_rep_years_is_missing, e.avg_prior_firm_tenure_is_missing,
    e.num_prior_firms_is_missing, e.num_registered_states_is_missing, e.firm_total_reps_is_missing, e.missing_feature_count,
    -- G) Simple Interactions
    e.is_new_to_firm_x_has_series65, e.veteran_x_cfp,
    e.Branch_Advisors_per_Firm_Association,
    -- Financial-derived (NULL - not available)
    e.AUM_per_Client, e.AUM_per_IARep, e.Clients_per_IARep, e.Clients_per_BranchAdvisor,
    e.Branch_Advisor_Density, e.HNW_Client_Ratio, e.HNW_Asset_Concentration, e.Individual_Asset_Ratio,
    e.Alternative_Investment_Focus, e.Positive_Growth_Trajectory, e.Accelerating_Growth,
    -- Metadata
    e.days_to_conversion,
    e.rep_snapshot_at,
    e.firm_snapshot_at,
    e.Stage_Entered_Contacting__c,
    e.Stage_Entered_Call_Scheduled__c
FROM EngineeredData e
WHERE e.is_in_right_censored_window = false
  AND (e.days_to_conversion >= 0 OR e.days_to_conversion IS NULL);
"""

# Validation queries
VALIDATION_QUERIES = {
    "1_negative_days": f"""
        SELECT COUNT(*) AS negative_days_count
        FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`
        WHERE days_to_conversion < 0;
    """,
    "2_rep_match_rate": f"""
        WITH 
        LeadsWithQuarter AS (
            SELECT DISTINCT FA_CRD__c
            FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
            WHERE Stage_Entered_Contacting__c IS NOT NULL AND FA_CRD__c IS NOT NULL
        ),
        MatchedReps AS (
            SELECT DISTINCT FA_CRD__c
            FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`
        )
        SELECT 
            (SELECT COUNT(*) FROM MatchedReps) / (SELECT COUNT(*) FROM LeadsWithQuarter) AS rep_match_rate;
    """,
    "3_firm_match_rate": f"""
        SELECT 
            COUNT(DISTINCT CASE WHEN RIAFirmCRD IS NOT NULL THEN FA_CRD__c END) / COUNT(DISTINCT FA_CRD__c) AS firm_match_rate
        FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`;
    """,
    "4_snapshot_date_integrity": f"""
        SELECT COUNTIF(rep_snapshot_at NOT IN (
            DATE('2024-01-07'), DATE('2024-03-31'), DATE('2024-07-07'), DATE('2024-10-06'),
            DATE('2025-01-05'), DATE('2025-04-06'), DATE('2025-07-06'), DATE('2025-10-05')
        )) AS invalid_snapshot_count
        FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`
        WHERE rep_snapshot_at IS NOT NULL;
    """,
    "5_pit_integrity": f"""
        SELECT COUNT(*) AS post_contact_features
        FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`
        WHERE rep_snapshot_at > DATE(Stage_Entered_Contacting__c)
           OR firm_snapshot_at > DATE(Stage_Entered_Contacting__c);
    """,
    "6_boolean_domain": f"""
        SELECT 
          COUNTIF(is_veteran_advisor NOT IN (0, 1)) AS invalid_veteran,
          COUNTIF(is_new_to_firm NOT IN (0, 1)) AS invalid_new_to_firm,
          COUNTIF(high_turnover_flag NOT IN (0, 1)) AS invalid_turnover,
          COUNTIF(multi_ria_relationships NOT IN (0, 1)) AS invalid_multi_ria,
          COUNTIF(complex_registration NOT IN (0, 1)) AS invalid_complex_reg,
          COUNTIF(remote_work_indicator NOT IN (0, 1)) AS invalid_remote,
          COUNTIF(local_advisor NOT IN (0, 1)) AS invalid_local,
          COUNTIF(has_linkedin NOT IN (0, 1)) AS invalid_linkedin,
          COUNTIF(email_business_type_flag NOT IN (0, 1)) AS invalid_email_business,
          COUNTIF(email_personal_type_flag NOT IN (0, 1)) AS invalid_email_personal
        FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`;
    """,
    "7_enum_domain": f"""
        SELECT COUNTIF(firm_rep_count_bin NOT IN ('1', '2_5', '6_20', '21_plus') AND firm_rep_count_bin IS NOT NULL) AS invalid_bin
        FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`;
    """,
    "8_null_safety": f"""
        SELECT 
          COUNTIF(doh_current_years_is_missing NOT IN (0, 1)) AS invalid_doh_missing,
          COUNTIF(became_rep_years_is_missing NOT IN (0, 1)) AS invalid_became_missing,
          COUNTIF(missing_feature_count < 0 OR missing_feature_count > 6) AS invalid_missing_count
        FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`;
    """,
    "class_imbalance": f"""
        SELECT 
          'Class Imbalance Metrics (V6 - True Vintage)' AS metric_type,
          COUNT(*) AS total_samples,
          COUNT(CASE WHEN target_label = 1 THEN 1 END) AS positive_samples,
          COUNT(CASE WHEN target_label = 0 THEN 1 END) AS negative_samples,
          ROUND(COUNT(CASE WHEN target_label = 1 THEN 1 END) / COUNT(*) * 100, 2) AS positive_class_percent,
          ROUND(COUNT(CASE WHEN target_label = 0 THEN 1 END) / COUNT(CASE WHEN target_label = 1 THEN 1 END), 2) AS imbalance_ratio
        FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{version}`;
    """
}

def run_validation(client, query_name, query_sql, expected_result=None):
    """Run a validation query and check results"""
    print(f"\n  Running {query_name}...")
    try:
        result = client.query(query_sql).result()
        row = list(result)[0]
        
        if query_name == "class_imbalance":
            return row
        
        # Check if it's a single value query
        if hasattr(row, 'negative_days_count'):
            value = row.negative_days_count
            expected = 0
            status = "PASS" if value == expected else "FAIL"
            print(f"    Result: {value} (Expected: {expected}) [{status}]")
            return {"value": value, "expected": expected, "status": status}
        elif hasattr(row, 'rep_match_rate'):
            value = row.rep_match_rate
            expected_min = 0.85
            status = "PASS" if value >= expected_min else "FAIL"
            print(f"    Result: {value:.3f} (Expected: >= {expected_min}) [{status}]")
            return {"value": value, "expected_min": expected_min, "status": status}
        elif hasattr(row, 'firm_match_rate'):
            value = row.firm_match_rate
            expected_min = 0.75
            status = "PASS" if value >= expected_min else "FAIL"
            print(f"    Result: {value:.3f} (Expected: >= {expected_min}) [{status}]")
            return {"value": value, "expected_min": expected_min, "status": status}
        elif hasattr(row, 'invalid_snapshot_count'):
            value = row.invalid_snapshot_count
            expected = 0
            status = "PASS" if value == expected else "FAIL"
            print(f"    Result: {value} (Expected: {expected}) [{status}]")
            return {"value": value, "expected": expected, "status": status}
        elif hasattr(row, 'post_contact_features'):
            value = row.post_contact_features
            expected = 0
            status = "PASS" if value == expected else "FAIL"
            print(f"    Result: {value} (Expected: {expected}) [{'HARD FAIL' if value > 0 else 'PASS'}]")
            return {"value": value, "expected": expected, "status": status}
        elif hasattr(row, 'invalid_bin'):
            value = row.invalid_bin
            expected = 0
            status = "PASS" if value == expected else "FAIL"
            print(f"    Result: {value} (Expected: {expected}) [{status}]")
            return {"value": value, "expected": expected, "status": status}
        else:
            # Boolean domain or null safety checks
            all_zeros = all(getattr(row, attr) == 0 for attr in dir(row) if attr.startswith('invalid_'))
            status = "PASS" if all_zeros else "FAIL"
            print(f"    Result: All invalid counts = 0 [{status}]")
            return {"status": status, "details": row}
    except Exception as e:
        print(f"    ERROR: {str(e)}")
        return {"status": "ERROR", "error": str(e)}

def main():
    client = bigquery.Client(project='savvy-gtm-analytics')
    
    print("="*70)
    print("Step 3.2: Apply Feature Engineering & Create Final Training Set (V6)")
    print("="*70)
    print(f"\nVersion: {version}")
    print(f"Staging Table: step_3_1_staging_join_v6_{STAGING_VERSION}")
    print(f"Output Table: step_3_3_training_dataset_v6_{version}")
    print("\nExecuting feature engineering and creating training dataset...")
    print("This may take several minutes...")
    
    try:
        query_job = client.query(SQL)
        query_job.result()  # Wait for completion
        print(f"\n[SUCCESS] Training dataset created: step_3_3_training_dataset_v6_{version}")
        
        # Validate
        print("\n" + "="*70)
        print("Running Validation Assertions")
        print("="*70)
        
        validation_results = {}
        for query_name, query_sql in VALIDATION_QUERIES.items():
            if query_name == "class_imbalance":
                imbalance_result = run_validation(client, query_name, query_sql)
                validation_results[query_name] = imbalance_result
            else:
                validation_results[query_name] = run_validation(client, query_name, query_sql)
        
        # Summary
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        
        all_passed = True
        for query_name, result in validation_results.items():
            if query_name == "class_imbalance":
                continue
            if isinstance(result, dict) and result.get("status") != "PASS":
                all_passed = False
        
        if all_passed:
            print("\n[SUCCESS] All validation assertions passed!")
        else:
            print("\n[WARNING] Some validation assertions failed. Please review above.")
        
        # Class imbalance report
        if "class_imbalance" in validation_results:
            imb = validation_results["class_imbalance"]
            print(f"\nClass Imbalance Metrics:")
            print(f"  Total samples: {imb.total_samples:,}")
            print(f"  Positive samples: {imb.positive_samples:,}")
            print(f"  Negative samples: {imb.negative_samples:,}")
            print(f"  Positive class %: {imb.positive_class_percent}%")
            print(f"  Imbalance ratio: {imb.imbalance_ratio:.2f}:1")
            
            # Write class imbalance report
            report_lines = [
                "# Class Imbalance Analysis (V6)",
                "",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Version:** {version}",
                "",
                "## Metrics",
                "",
                f"- **Total Samples:** {imb.total_samples:,}",
                f"- **Positive Samples (target_label=1):** {imb.positive_samples:,}",
                f"- **Negative Samples (target_label=0):** {imb.negative_samples:,}",
                f"- **Positive Class Percentage:** {imb.positive_class_percent}%",
                f"- **Imbalance Ratio:** {imb.imbalance_ratio:.2f}:1 (negative:positive)",
                "",
                "## Target Definition",
                "",
                "`target_label = 1` if `Call_Scheduled` occurred **≤ 30 days** after `Stage_Entered_Contacting__c`; else 0.",
                "",
                "## Recommendations",
                "",
                "Consider class balancing techniques for XGBoost training:",
                "- Scale positive weight: Use `scale_pos_weight` parameter",
                "- Undersampling majority class",
                "- Oversampling minority class (SMOTE)",
                "- Focal loss or other cost-sensitive learning approaches",
                ""
            ]
            
            with open(f'step_3_3_class_imbalance_analysis_v6_{version}.md', 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            print(f"\nClass imbalance report written to: step_3_3_class_imbalance_analysis_v6_{version}.md")
        
        print(f"\n[SUCCESS] Step 3.2 complete!")
        print(f"\nTraining dataset ready for model training:")
        print(f"  Table: step_3_3_training_dataset_v6_{version}")
        
        return version
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create training dataset: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

