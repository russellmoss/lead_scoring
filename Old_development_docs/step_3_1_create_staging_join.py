"""
Step 3.1: Create Staging Join Table (V6)
Point-in-time join between Salesforce Leads and discovery snapshots
"""

from google.cloud import bigquery
from datetime import datetime
import sys

# Generate version string
version = datetime.now().strftime("%Y%m%d_%H%M")

SQL = f"""
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_1_staging_join_v6_{version}` AS
WITH
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
),
RepPointInTimeJoin AS (
    SELECT 
        l2.FA_CRD__c,
        l2.contact_date,
        l2.Id,
        l2.Stage_Entered_Contacting__c,
        l2.Stage_Entered_Call_Scheduled__c,
        reps.*
    FROM LeadsWithContactDate l2
    LEFT JOIN `savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages` reps
        ON reps.RepCRD = l2.FA_CRD__c
        AND reps.snapshot_at <= l2.contact_date
    QUALIFY ROW_NUMBER() OVER (PARTITION BY l2.FA_CRD__c, l2.contact_date ORDER BY reps.snapshot_at DESC) = 1
),
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
    FROM RepPointInTimeJoin r
    LEFT JOIN `savvy-gtm-analytics.LeadScoring.v_discovery_firms_all_vintages` firms
        ON firms.RIAFirmCRD = r.RIAFirmCRD
        AND firms.snapshot_at <= r.contact_date
    QUALIFY ROW_NUMBER() OVER (PARTITION BY r.FA_CRD__c, r.contact_date ORDER BY firms.snapshot_at DESC) = 1
),
PointInTimeJoin AS (
    SELECT
        Id,
        FA_CRD__c,
        Stage_Entered_Contacting__c,
        Stage_Entered_Call_Scheduled__c,
        contact_date,
        -- Reps Keep Features (Note: Financial metrics are NULL from RIARepDataFeed)
        RepCRD,
        RIAFirmCRD,
        TotalAssetsInMillions,
        TotalAssets_PooledVehicles,
        TotalAssets_SeparatelyManagedAccounts,
        NumberClients_Individuals,
        NumberClients_HNWIndividuals,
        NumberClients_RetirementPlans,
        PercentClients_Individuals,
        PercentClients_HNWIndividuals,
        AssetsInMillions_MutualFunds,
        AssetsInMillions_PrivateFunds,
        AssetsInMillions_Equity_ExchangeTraded,
        PercentAssets_MutualFunds,
        PercentAssets_PrivateFunds,
        PercentAssets_Equity_ExchangeTraded,
        Number_IAReps,
        Number_BranchAdvisors,
        NumberFirmAssociations,
        NumberRIAFirmAssociations,
        AUMGrowthRate_1Year,
        AUMGrowthRate_5Year,
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
        CustodianAUM_Schwab,
        CustodianAUM_Fidelity_NationalFinancial,
        CustodianAUM_Pershing,
        CustodianAUM_TDAmeritrade,
        Has_Schwab_Relationship,
        Has_Fidelity_Relationship,
        Has_Pershing_Relationship,
        Has_TDAmeritrade_Relationship,
        Number_RegisteredStates,
        snapshot_at as rep_snapshot_at,
        -- Firms Keep Features
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
        national_firm,
        firm_snapshot_at
    FROM FirmPointInTimeJoin
)
SELECT * FROM PointInTimeJoin;
"""

def main():
    client = bigquery.Client(project='savvy-gtm-analytics')
    
    print("="*70)
    print("Step 3.1: Create Staging Join Table (V6)")
    print("="*70)
    print(f"\nVersion: {version}")
    print(f"Table: step_3_1_staging_join_v6_{version}")
    print("\nExecuting point-in-time join...")
    print("This may take several minutes...")
    
    try:
        query_job = client.query(SQL)
        query_job.result()  # Wait for completion
        print(f"\n[SUCCESS] Staging table created: step_3_1_staging_join_v6_{version}")
        
        # Validate
        print("\nValidating table...")
        count_query = f"SELECT COUNT(*) as cnt FROM `savvy-gtm-analytics.LeadScoring.step_3_1_staging_join_v6_{version}`"
        count_result = client.query(count_query).result()
        row_count = list(count_result)[0].cnt
        print(f"  Row count: {row_count:,}")
        
        # Check join rates
        join_query = f"""
        SELECT 
            COUNT(*) as total_leads,
            COUNT(RepCRD) as leads_with_rep_data,
            COUNT(RIAFirmCRD) as leads_with_firm_data,
            COUNT(*) - COUNT(RepCRD) as leads_without_rep_data
        FROM `savvy-gtm-analytics.LeadScoring.step_3_1_staging_join_v6_{version}`
        """
        join_result = client.query(join_query).result()
        join_row = list(join_result)[0]
        print(f"\nJoin Statistics:")
        print(f"  Total leads: {join_row.total_leads:,}")
        print(f"  Leads with rep data: {join_row.leads_with_rep_data:,} ({100*join_row.leads_with_rep_data/join_row.total_leads:.1f}%)")
        print(f"  Leads with firm data: {join_row.leads_with_firm_data:,} ({100*join_row.leads_with_firm_data/join_row.total_leads:.1f}%)")
        print(f"  Leads without rep data: {join_row.leads_without_rep_data:,} ({100*join_row.leads_without_rep_data/join_row.total_leads:.1f}%)")
        
        # Check snapshot date ranges
        snapshot_query = f"""
        SELECT 
            COUNT(DISTINCT rep_snapshot_at) as distinct_rep_snapshots,
            COUNT(DISTINCT firm_snapshot_at) as distinct_firm_snapshots,
            MIN(rep_snapshot_at) as earliest_rep_snapshot,
            MAX(rep_snapshot_at) as latest_rep_snapshot,
            MIN(firm_snapshot_at) as earliest_firm_snapshot,
            MAX(firm_snapshot_at) as latest_firm_snapshot
        FROM `savvy-gtm-analytics.LeadScoring.step_3_1_staging_join_v6_{version}`
        WHERE RepCRD IS NOT NULL
        """
        snapshot_result = client.query(snapshot_query).result()
        snapshot_row = list(snapshot_result)[0]
        print(f"\nSnapshot Statistics:")
        print(f"  Distinct rep snapshots used: {snapshot_row.distinct_rep_snapshots}")
        print(f"  Distinct firm snapshots used: {snapshot_row.distinct_firm_snapshots}")
        print(f"  Rep snapshot range: {snapshot_row.earliest_rep_snapshot} to {snapshot_row.latest_rep_snapshot}")
        print(f"  Firm snapshot range: {snapshot_row.earliest_firm_snapshot} to {snapshot_row.latest_firm_snapshot}")
        
        print(f"\n[SUCCESS] Staging table validated and ready for Step 3.2")
        print(f"\nNext: Use version '{version}' in Step 3.2")
        
        return version
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create staging table: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

