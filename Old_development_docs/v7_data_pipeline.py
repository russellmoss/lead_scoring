"""
V7 Data Pipeline: Hybrid Financial Data Approach
Builds V7 training dataset combining:
1. Historical snapshot data for non-financial features (8 quarters)
2. Current financial data applied to all historical leads (like m5)
3. Temporal dynamics calculated from snapshot changes
4. m5's engineered features

This addresses the training-production mismatch by using current financial
data across all historical leads, matching production methodology.
"""

from google.cloud import bigquery
from datetime import datetime
import sys
import json

# Generate version string
VERSION = datetime.now().strftime("%Y%m%d_%H%M")

# Output table name
OUTPUT_TABLE = f"savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v7_{VERSION}"

SQL = f"""
CREATE OR REPLACE TABLE `{OUTPUT_TABLE}` AS
WITH
-- Step 1: Get leads with contact dates
LeadsWithContactDate AS (
    SELECT 
        Id,
        FA_CRD__c,
        Stage_Entered_Contacting__c,
        Stage_Entered_Call_Scheduled__c,
        DATE(Stage_Entered_Contacting__c) as contact_date
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE Stage_Entered_Contacting__c IS NOT NULL
      AND FA_CRD__c IS NOT NULL
      -- Exclude right-censored data (last 30 days)
      AND DATE(Stage_Entered_Contacting__c) <= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

-- Step 2: Point-in-time join for NON-FINANCIAL features from historical snapshots
RepPointInTimeJoin AS (
    SELECT 
        l.FA_CRD__c,
        l.contact_date,
        l.Id,
        l.Stage_Entered_Contacting__c,
        l.Stage_Entered_Call_Scheduled__c,
        -- Non-financial features from historical snapshots
        reps.RepCRD,
        reps.RIAFirmCRD,
        reps.DateBecameRep_NumberOfYears,
        reps.DateOfHireAtCurrentFirm_NumberOfYears,
        reps.Number_YearsPriorFirm1,
        reps.Number_YearsPriorFirm2,
        reps.Number_YearsPriorFirm3,
        reps.Number_YearsPriorFirm4,
        reps.AverageTenureAtPriorFirms,
        reps.NumberOfPriorFirms,
        reps.IsPrimaryRIAFirm,
        reps.DuallyRegisteredBDRIARep,
        reps.Has_Series_7,
        reps.Has_Series_65,
        reps.Has_Series_66,
        reps.Has_Series_24,
        reps.Has_CFP,
        reps.Has_CFA,
        reps.Has_CIMA,
        reps.Has_AIF,
        reps.Has_Disclosure,
        reps.Is_BreakawayRep,
        reps.Has_Insurance_License,
        reps.Is_NonProducer,
        reps.Is_IndependentContractor,
        reps.Is_Owner,
        reps.Office_USPS_Certified,
        reps.Home_USPS_Certified,
        reps.Has_LinkedIn,
        reps.Home_MetropolitanArea,
        reps.Branch_State,
        reps.Home_State,
        reps.Home_ZipCode,
        reps.Branch_ZipCode,
        reps.MilesToWork,
        reps.SocialMedia_LinkedIn,
        reps.NumberFirmAssociations,
        reps.NumberRIAFirmAssociations,
        reps.Number_IAReps,
        reps.Number_BranchAdvisors,
        reps.Number_RegisteredStates,
        reps.snapshot_at as rep_snapshot_at,
        -- Financial features will be NULL here (we'll join current snapshot next)
        reps.TotalAssetsInMillions as historical_TotalAssetsInMillions,
        reps.AUMGrowthRate_1Year as historical_AUMGrowthRate_1Year,
        reps.AUMGrowthRate_5Year as historical_AUMGrowthRate_5Year
    FROM LeadsWithContactDate l
    LEFT JOIN `savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages` reps
        ON reps.RepCRD = l.FA_CRD__c
        AND reps.snapshot_at <= l.contact_date
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY l.FA_CRD__c, l.contact_date 
        ORDER BY reps.snapshot_at DESC
    ) = 1
),

-- Step 3: Join CURRENT financial data for ALL leads (like m5)
RepWithCurrentFinancials AS (
    SELECT 
        r.*,
        -- Financial features from CURRENT snapshot (no temporal constraint)
        fin.TotalAssetsInMillions,
        fin.TotalAssets_PooledVehicles,
        fin.TotalAssets_SeparatelyManagedAccounts,
        fin.NumberClients_Individuals,
        fin.NumberClients_HNWIndividuals,
        fin.NumberClients_RetirementPlans,
        fin.PercentClients_Individuals,
        fin.PercentClients_HNWIndividuals,
        fin.AssetsInMillions_Individuals,
        fin.AssetsInMillions_HNWIndividuals,
        fin.AssetsInMillions_MutualFunds,
        fin.AssetsInMillions_PrivateFunds,
        fin.AssetsInMillions_Equity_ExchangeTraded,
        fin.PercentAssets_MutualFunds,
        fin.PercentAssets_PrivateFunds,
        fin.PercentAssets_Equity_ExchangeTraded,
        fin.PercentAssets_HNWIndividuals,
        fin.PercentAssets_Individuals,
        fin.AUMGrowthRate_1Year,
        fin.AUMGrowthRate_5Year,
        fin.CustodianAUM_Schwab,
        fin.CustodianAUM_Fidelity_NationalFinancial,
        fin.CustodianAUM_Pershing,
        fin.CustodianAUM_TDAmeritrade,
        fin.Has_Schwab_Relationship,
        fin.Has_Fidelity_Relationship,
        fin.Has_Pershing_Relationship,
        fin.Has_TDAmeritrade_Relationship
    FROM RepPointInTimeJoin r
    LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` fin
        ON fin.RepCRD = r.RepCRD
        -- No temporal constraint - use current financial data for all leads
),

-- Step 4: Join firm data (point-in-time for non-financial, current for financial)
FirmPointInTimeJoin AS (
    SELECT 
        r.*,
        firms.total_firm_aum_millions,
        firms.total_reps,
        firms.total_firm_clients,
        firms.total_firm_hnw_clients,
        firms.avg_clients_per_rep,
        firms.aum_per_rep,
        firms.avg_firm_growth_1y,
        firms.avg_firm_growth_5y,
        firms.pct_reps_with_cfp,
        firms.pct_reps_with_disclosure,
        firms.firm_size_tier,
        firms.multi_state_firm,
        firms.national_firm,
        firms.snapshot_at as firm_snapshot_at
    FROM RepWithCurrentFinancials r
    LEFT JOIN `savvy-gtm-analytics.LeadScoring.v_discovery_firms_all_vintages` firms
        ON firms.RIAFirmCRD = r.RIAFirmCRD
        AND firms.snapshot_at <= r.contact_date
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY r.FA_CRD__c, r.contact_date 
        ORDER BY firms.snapshot_at DESC
    ) = 1
),

-- Step 5: Create temporal dynamics features by comparing snapshots
TemporalDynamics AS (
    SELECT 
        p.*,
        -- Calculate temporal features from snapshot history
        -- (These will be calculated in Python feature engineering for now)
        -- Placeholder for temporal features
        CAST(NULL AS INT64) as firm_change_flag_placeholder,
        CAST(NULL AS INT64) as license_growth_placeholder,
        CAST(NULL AS INT64) as branch_stability_placeholder,
        CAST(NULL AS INT64) as tenure_momentum_placeholder,
        
        -- Create target label
        CASE 
            WHEN p.Stage_Entered_Call_Scheduled__c IS NOT NULL 
             AND DATE(p.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(p.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
            THEN 1 ELSE 0 
        END as target_label,
        
        -- Calculate days to conversion
        DATE_DIFF(
            DATE(p.Stage_Entered_Call_Scheduled__c), 
            DATE(p.Stage_Entered_Contacting__c), 
            DAY
        ) as days_to_conversion
    FROM FirmPointInTimeJoin p
)

SELECT 
    Id,
    FA_CRD__c,
    RepCRD,
    RIAFirmCRD,
    Stage_Entered_Contacting__c,
    Stage_Entered_Call_Scheduled__c,
    contact_date,
    target_label,
    days_to_conversion,
    
    -- Non-financial features (from historical snapshots)
    DateBecameRep_NumberOfYears,
    DateOfHireAtCurrentFirm_NumberOfYears,
    Number_YearsPriorFirm1,
    Number_YearsPriorFirm2,
    Number_YearsPriorFirm3,
    Number_YearsPriorFirm4,
    AverageTenureAtPriorFirms,
    NumberOfPriorFirms,
    IsPrimaryRIAFirm,
    DuallyRegisteredBDRIARep,
    Has_Series_7,
    Has_Series_65,
    Has_Series_66,
    Has_Series_24,
    Has_CFP,
    Has_CFA,
    Has_CIMA,
    Has_AIF,
    Has_Disclosure,
    Is_BreakawayRep,
    Has_Insurance_License,
    Is_NonProducer,
    Is_IndependentContractor,
    Is_Owner,
    Office_USPS_Certified,
    Home_USPS_Certified,
    Has_LinkedIn,
    Home_MetropolitanArea,
    Branch_State,
    Home_State,
    Home_ZipCode,
    Branch_ZipCode,
    MilesToWork,
    SocialMedia_LinkedIn,
    NumberFirmAssociations,
    NumberRIAFirmAssociations,
    Number_IAReps,
    Number_BranchAdvisors,
    Number_RegisteredStates,
    rep_snapshot_at,
    firm_snapshot_at,
    
    -- Financial features (from current snapshot)
    TotalAssetsInMillions,
    TotalAssets_PooledVehicles,
    TotalAssets_SeparatelyManagedAccounts,
    NumberClients_Individuals,
    NumberClients_HNWIndividuals,
    NumberClients_RetirementPlans,
    PercentClients_Individuals,
    PercentClients_HNWIndividuals,
    AssetsInMillions_Individuals,
    AssetsInMillions_HNWIndividuals,
    AssetsInMillions_MutualFunds,
    AssetsInMillions_PrivateFunds,
    AssetsInMillions_Equity_ExchangeTraded,
    PercentAssets_MutualFunds,
    PercentAssets_PrivateFunds,
    PercentAssets_Equity_ExchangeTraded,
    PercentAssets_HNWIndividuals,
    PercentAssets_Individuals,
    AUMGrowthRate_1Year,
    AUMGrowthRate_5Year,
    CustodianAUM_Schwab,
    CustodianAUM_Fidelity_NationalFinancial,
    CustodianAUM_Pershing,
    CustodianAUM_TDAmeritrade,
    Has_Schwab_Relationship,
    Has_Fidelity_Relationship,
    Has_Pershing_Relationship,
    Has_TDAmeritrade_Relationship,
    
    -- Firm features
    total_firm_aum_millions,
    total_reps,
    total_firm_clients,
    total_firm_hnw_clients,
    avg_clients_per_rep,
    aum_per_rep,
    avg_firm_growth_1y,
    avg_firm_growth_5y,
    pct_reps_with_cfp,
    pct_reps_with_disclosure,
    firm_size_tier,
    multi_state_firm,
    national_firm
    
FROM TemporalDynamics
WHERE days_to_conversion >= 0 OR days_to_conversion IS NULL;
"""


def verify_dataset(client, table_name):
    """Verify the created dataset"""
    print("\n" + "="*70)
    print("Verifying V7 Dataset")
    print("="*70)
    
    # Row count
    count_query = f"SELECT COUNT(*) as cnt FROM `{table_name}`"
    count_result = client.query(count_query).result()
    row_count = list(count_result)[0].cnt
    print(f"\nRow count: {row_count:,}")
    
    # Class distribution
    class_query = f"""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN target_label = 1 THEN 1 END) as positive,
        COUNT(CASE WHEN target_label = 0 THEN 1 END) as negative,
        ROUND(COUNT(CASE WHEN target_label = 1 THEN 1 END) / COUNT(*) * 100, 2) as positive_pct
    FROM `{table_name}`
    """
    class_result = client.query(class_query).result()
    class_row = list(class_result)[0]
    print(f"\nClass Distribution:")
    print(f"  Total samples: {class_row.total:,}")
    print(f"  Positive (target_label=1): {class_row.positive:,} ({class_row.positive_pct}%)")
    print(f"  Negative (target_label=0): {class_row.negative:,} ({100-class_row.positive_pct}%)")
    
    # Financial feature coverage
    financial_query = f"""
    SELECT 
        COUNT(*) as total,
        COUNT(TotalAssetsInMillions) as has_aum,
        COUNT(NumberClients_Individuals) as has_clients,
        COUNT(AUMGrowthRate_1Year) as has_growth,
        ROUND(COUNT(TotalAssetsInMillions) / COUNT(*) * 100, 2) as aum_coverage_pct
    FROM `{table_name}`
    """
    financial_result = client.query(financial_query).result()
    financial_row = list(financial_result)[0]
    print(f"\nFinancial Feature Coverage:")
    print(f"  TotalAssetsInMillions: {financial_row.has_aum:,} ({financial_row.aum_coverage_pct}%)")
    print(f"  NumberClients_Individuals: {financial_row.has_clients:,}")
    print(f"  AUMGrowthRate_1Year: {financial_row.has_growth:,}")
    
    # Join statistics
    join_query = f"""
    SELECT 
        COUNT(*) as total,
        COUNT(RepCRD) as has_rep_data,
        COUNT(RIAFirmCRD) as has_firm_data,
        COUNT(TotalAssetsInMillions) as has_financial_data
    FROM `{table_name}`
    """
    join_result = client.query(join_query).result()
    join_row = list(join_result)[0]
    print(f"\nJoin Statistics:")
    print(f"  Has rep data: {join_row.has_rep_data:,} ({100*join_row.has_rep_data/join_row.total:.1f}%)")
    print(f"  Has firm data: {join_row.has_firm_data:,} ({100*join_row.has_firm_data/join_row.total:.1f}%)")
    print(f"  Has financial data: {join_row.has_financial_data:,} ({100*join_row.has_financial_data/join_row.total:.1f}%)")
    
    # Column count
    col_query = f"""
    SELECT COUNT(*) as col_count
    FROM `savvy-gtm-analytics.LeadScoring.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = '{table_name.split('.')[-1]}'
    """
    col_result = client.query(col_query).result()
    col_count = list(col_result)[0].col_count
    print(f"\nTotal columns: {col_count}")
    
    return {
        'row_count': row_count,
        'positive_samples': class_row.positive,
        'positive_pct': class_row.positive_pct,
        'financial_coverage': financial_row.aum_coverage_pct
    }


def main():
    client = bigquery.Client(project='savvy-gtm-analytics')
    
    print("="*70)
    print("V7 Data Pipeline: Hybrid Financial Data Approach")
    print("="*70)
    print(f"\nVersion: {VERSION}")
    print(f"Output Table: {OUTPUT_TABLE}")
    print("\nStrategy:")
    print("  - Non-financial features: Point-in-time from historical snapshots")
    print("  - Financial features: Current snapshot for ALL leads (like m5)")
    print("  - Temporal dynamics: To be calculated in feature engineering")
    print("\nExecuting query...")
    print("This may take 5-10 minutes...")
    
    try:
        query_job = client.query(SQL)
        query_job.result()  # Wait for completion
        print(f"\n[SUCCESS] V7 dataset created: {OUTPUT_TABLE}")
        
        # Verify dataset
        stats = verify_dataset(client, OUTPUT_TABLE)
        
        # Save metadata
        metadata = {
            'version': VERSION,
            'table_name': OUTPUT_TABLE,
            'created_at': datetime.now().isoformat(),
            'row_count': stats['row_count'],
            'positive_samples': stats['positive_samples'],
            'positive_pct': stats['positive_pct'],
            'financial_coverage_pct': stats['financial_coverage'],
            'strategy': 'hybrid_financial',
            'description': 'Non-financial from historical snapshots, financial from current snapshot'
        }
        
        metadata_file = f"v7_dataset_metadata_{VERSION}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"\n[SUCCESS] Metadata saved to: {metadata_file}")
        
        print(f"\n[SUCCESS] V7 dataset ready for feature engineering")
        print(f"\nNext steps:")
        print(f"  1. Run: python v7_feature_engineering.py --input-table {OUTPUT_TABLE}")
        print(f"  2. Then: python train_model_v7.py --input-table <feature_engineered_table>")
        
        return OUTPUT_TABLE
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create V7 dataset: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='V7 Data Pipeline')
    parser.add_argument('--verify-only', action='store_true', 
                       help='Only verify existing table (do not create)')
    parser.add_argument('--table-name', type=str, 
                       help='Table name to verify (if verify-only)')
    args = parser.parse_args()
    
    if args.verify_only:
        if not args.table_name:
            print("[ERROR] --table-name required with --verify-only")
            sys.exit(1)
        client = bigquery.Client(project='savvy-gtm-analytics')
        verify_dataset(client, args.table_name)
    else:
        main()

