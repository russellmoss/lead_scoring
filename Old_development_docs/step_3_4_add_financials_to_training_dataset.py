"""
Step 3.4: Add Financial Features from discovery_reps_current to V6 Training Dataset
Assumes financial metrics are relatively stable over 2-year period and joins current snapshot
"""

from google.cloud import bigquery
from datetime import datetime
import sys

# Use the version from Step 3.3
TRAINING_VERSION = "20251104_2217"
version = datetime.now().strftime("%Y%m%d_%H%M")
OUTPUT_VERSION = version  # New version for output table

SQL = f"""
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_4_training_dataset_v6_with_financials_{OUTPUT_VERSION}` AS
WITH
BaseData AS (
    SELECT * FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_{TRAINING_VERSION}`
),
FinancialData AS (
    SELECT 
        RepCRD,
        -- Core financial metrics
        TotalAssetsInMillions,
        NumberClients_Individuals,
        NumberClients_HNWIndividuals,
        NumberClients_RetirementPlans,
        AssetsInMillions_Individuals,
        AssetsInMillions_HNWIndividuals,
        AssetsInMillions_MutualFunds,
        AssetsInMillions_PrivateFunds,
        AssetsInMillions_Equity_ExchangeTraded,
        TotalAssets_SeparatelyManagedAccounts,
        TotalAssets_PooledVehicles,
        
        -- Growth metrics
        AUMGrowthRate_1Year,
        AUMGrowthRate_5Year,
        
        -- Percentage metrics
        PercentClients_HNWIndividuals,
        PercentClients_Individuals,
        PercentAssets_HNWIndividuals,
        PercentAssets_Individuals,
        PercentAssets_MutualFunds,
        PercentAssets_PrivateFunds,
        PercentAssets_Equity_ExchangeTraded,
        
        -- Custodian AUM
        CustodianAUM_Schwab,
        CustodianAUM_Fidelity_NationalFinancial,
        CustodianAUM_Pershing,
        CustodianAUM_TDAmeritrade,
        
        -- Pre-engineered efficiency metrics (from discovery_reps_current)
        AUM_Per_Client,
        AUM_Per_IARep,
        AUM_Per_BranchAdvisor,
        
        -- Pre-engineered growth indicators
        Growth_Momentum,
        Accelerating_Growth,
        Positive_Growth_Trajectory,
        
        -- Pre-engineered client focus metrics
        HNW_Client_Ratio,
        Individual_Asset_Ratio,
        HNW_Asset_Concentration,
        
        -- Pre-engineered operational metrics
        Clients_per_IARep,
        Clients_per_BranchAdvisor
        
    FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
)
SELECT 
    -- All base columns from V6, but replace financial columns with actual values
    -- Note: Only exclude columns that actually exist in V6 dataset
    b.* EXCEPT(
        TotalAssetsInMillions,
        NumberClients_Individuals,
        NumberClients_HNWIndividuals,
        NumberClients_RetirementPlans,
        AssetsInMillions_MutualFunds,
        AssetsInMillions_PrivateFunds,
        AssetsInMillions_Equity_ExchangeTraded,
        TotalAssets_SeparatelyManagedAccounts,
        TotalAssets_PooledVehicles,
        AUMGrowthRate_1Year,
        AUMGrowthRate_5Year,
        PercentClients_HNWIndividuals,
        PercentClients_Individuals,
        PercentAssets_MutualFunds,
        PercentAssets_PrivateFunds,
        PercentAssets_Equity_ExchangeTraded,
        CustodianAUM_Schwab,
        CustodianAUM_Fidelity_NationalFinancial,
        CustodianAUM_Pershing,
        CustodianAUM_TDAmeritrade,
        AUM_per_Client,
        AUM_per_IARep,
        Clients_per_IARep,
        Clients_per_BranchAdvisor,
        HNW_Client_Ratio,
        HNW_Asset_Concentration,
        Individual_Asset_Ratio,
        Positive_Growth_Trajectory,
        Accelerating_Growth,
        Alternative_Investment_Focus
    ),
    
    -- Core financial metrics (replace NULLs from V6 with actual values)
    COALESCE(f.TotalAssetsInMillions, b.TotalAssetsInMillions) as TotalAssetsInMillions,
    COALESCE(f.NumberClients_Individuals, b.NumberClients_Individuals) as NumberClients_Individuals,
    COALESCE(f.NumberClients_HNWIndividuals, b.NumberClients_HNWIndividuals) as NumberClients_HNWIndividuals,
    COALESCE(f.NumberClients_RetirementPlans, b.NumberClients_RetirementPlans) as NumberClients_RetirementPlans,
    -- Add new asset columns that don't exist in V6
    f.AssetsInMillions_Individuals,
    f.AssetsInMillions_HNWIndividuals,
    COALESCE(f.AssetsInMillions_MutualFunds, b.AssetsInMillions_MutualFunds) as AssetsInMillions_MutualFunds,
    COALESCE(f.AssetsInMillions_PrivateFunds, b.AssetsInMillions_PrivateFunds) as AssetsInMillions_PrivateFunds,
    COALESCE(f.AssetsInMillions_Equity_ExchangeTraded, b.AssetsInMillions_Equity_ExchangeTraded) as AssetsInMillions_Equity_ExchangeTraded,
    COALESCE(f.TotalAssets_SeparatelyManagedAccounts, b.TotalAssets_SeparatelyManagedAccounts) as TotalAssets_SeparatelyManagedAccounts,
    COALESCE(f.TotalAssets_PooledVehicles, b.TotalAssets_PooledVehicles) as TotalAssets_PooledVehicles,
    
    -- Growth metrics
    COALESCE(f.AUMGrowthRate_1Year, b.AUMGrowthRate_1Year) as AUMGrowthRate_1Year,
    COALESCE(f.AUMGrowthRate_5Year, b.AUMGrowthRate_5Year) as AUMGrowthRate_5Year,
    
    -- Percentage metrics (add new ones that don't exist in V6)
    COALESCE(f.PercentClients_HNWIndividuals, b.PercentClients_HNWIndividuals) as PercentClients_HNWIndividuals,
    COALESCE(f.PercentClients_Individuals, b.PercentClients_Individuals) as PercentClients_Individuals,
    f.PercentAssets_HNWIndividuals,
    f.PercentAssets_Individuals,
    COALESCE(f.PercentAssets_MutualFunds, b.PercentAssets_MutualFunds) as PercentAssets_MutualFunds,
    COALESCE(f.PercentAssets_PrivateFunds, b.PercentAssets_PrivateFunds) as PercentAssets_PrivateFunds,
    COALESCE(f.PercentAssets_Equity_ExchangeTraded, b.PercentAssets_Equity_ExchangeTraded) as PercentAssets_Equity_ExchangeTraded,
    
    -- Custodian AUM
    COALESCE(f.CustodianAUM_Schwab, b.CustodianAUM_Schwab) as CustodianAUM_Schwab,
    COALESCE(f.CustodianAUM_Fidelity_NationalFinancial, b.CustodianAUM_Fidelity_NationalFinancial) as CustodianAUM_Fidelity_NationalFinancial,
    COALESCE(f.CustodianAUM_Pershing, b.CustodianAUM_Pershing) as CustodianAUM_Pershing,
    COALESCE(f.CustodianAUM_TDAmeritrade, b.CustodianAUM_TDAmeritrade) as CustodianAUM_TDAmeritrade,
    
    -- Replace NULL engineered financial features with actual values
    COALESCE(f.AUM_Per_Client, b.AUM_per_Client) as AUM_per_Client,
    COALESCE(f.AUM_Per_IARep, b.AUM_per_IARep) as AUM_per_IARep,
    COALESCE(f.Clients_per_IARep, b.Clients_per_IARep) as Clients_per_IARep,
    COALESCE(f.Clients_per_BranchAdvisor, b.Clients_per_BranchAdvisor) as Clients_per_BranchAdvisor,
    COALESCE(f.HNW_Client_Ratio, b.HNW_Client_Ratio) as HNW_Client_Ratio,
    COALESCE(f.HNW_Asset_Concentration, b.HNW_Asset_Concentration) as HNW_Asset_Concentration,
    COALESCE(f.Individual_Asset_Ratio, b.Individual_Asset_Ratio) as Individual_Asset_Ratio,
    COALESCE(f.Positive_Growth_Trajectory, b.Positive_Growth_Trajectory) as Positive_Growth_Trajectory,
    COALESCE(f.Accelerating_Growth, b.Accelerating_Growth) as Accelerating_Growth,
    
    -- Additional engineered features using financial data
    COALESCE(
        SAFE_DIVIDE((f.AssetsInMillions_PrivateFunds + f.AssetsInMillions_Equity_ExchangeTraded), 
                    NULLIF(f.TotalAssetsInMillions, 0)),
        b.Alternative_Investment_Focus
    ) as Alternative_Investment_Focus,
    
    -- Flag indicating if financial data was joined (for monitoring)
    CASE WHEN f.RepCRD IS NOT NULL THEN 1 ELSE 0 END as has_financial_data_flag
    
FROM BaseData b
LEFT JOIN FinancialData f
    ON CAST(b.FA_CRD__c AS STRING) = CAST(f.RepCRD AS STRING)
"""

def main():
    client = bigquery.Client(project='savvy-gtm-analytics')
    
    print("=" * 80)
    print(f"Step 3.4: Add Financial Features to V6 Training Dataset")
    print("=" * 80)
    print(f"Input: step_3_3_training_dataset_v6_{TRAINING_VERSION}")
    print(f"Output: step_3_4_training_dataset_v6_with_financials_{OUTPUT_VERSION}")
    print(f"Financial Source: discovery_reps_current")
    print()
    
    # Execute query
    print("[INFO] Executing SQL query...")
    query_job = client.query(SQL)
    query_job.result()  # Wait for completion
    
    print("[SUCCESS] Table created successfully!")
    print()
    
    # Validation queries
    print("[INFO] Running validation checks...")
    
    # 1. Check row count
    validation_sql = f"""
    SELECT 
        COUNT(*) as total_rows,
        COUNT(DISTINCT FA_CRD__c) as distinct_leads,
        SUM(has_financial_data_flag) as leads_with_financials,
        ROUND(SUM(has_financial_data_flag) / COUNT(*) * 100, 1) as pct_with_financials,
        SUM(CASE WHEN TotalAssetsInMillions IS NOT NULL THEN 1 ELSE 0 END) as leads_with_aum,
        SUM(CASE WHEN NumberClients_Individuals IS NOT NULL THEN 1 ELSE 0 END) as leads_with_clients,
        SUM(CASE WHEN AUMGrowthRate_1Year IS NOT NULL THEN 1 ELSE 0 END) as leads_with_growth_1y,
        SUM(CASE WHEN AUMGrowthRate_5Year IS NOT NULL THEN 1 ELSE 0 END) as leads_with_growth_5y
    FROM `savvy-gtm-analytics.LeadScoring.step_3_4_training_dataset_v6_with_financials_{OUTPUT_VERSION}`
    """
    
    val_job = client.query(validation_sql)
    results = val_job.result()
    
    for row in results:
        print(f"  Total rows: {row.total_rows:,}")
        print(f"  Distinct leads: {row.distinct_leads:,}")
        print(f"  Leads with financial data: {row.leads_with_financials:,} ({row.pct_with_financials}%)")
        print(f"  Leads with AUM: {row.leads_with_aum:,}")
        print(f"  Leads with client counts: {row.leads_with_clients:,}")
        print(f"  Leads with 1Y growth rate: {row.leads_with_growth_1y:,}")
        print(f"  Leads with 5Y growth rate: {row.leads_with_growth_5y:,}")
    
    print()
    print("[SUCCESS] Validation complete!")
    print()
    print(f"Output table: savvy-gtm-analytics.LeadScoring.step_3_4_training_dataset_v6_with_financials_{OUTPUT_VERSION}")
    print()
    print("Next steps:")
    print("  1. Review financial data coverage")
    print("  2. Retrain model with financial features")
    print("  3. Compare performance to V6 without financials")

if __name__ == "__main__":
    main()

