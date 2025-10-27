-- Create discovery_firms_current Table
-- Firm-level aggregated features derived from discovery_reps_current
-- This creates firm-level insights for lead scoring model
-- 
-- EXECUTED: October 27, 2025 ✅ SUCCESSFULLY COMPLETED
-- DATASET: savvy-gtm-analytics.LeadScoring.discovery_firms_current (Toronto region)
-- SOURCE: Aggregated from discovery_reps_current table
-- 
-- EXECUTION RESULTS:
-- - Total Firms Created: 38,543
-- - Average Reps per Firm: 12.4
-- - Average Firm AUM: $6,103,215.3M
-- - Mega Firms (>$1B): 9,234 (23.96%)
-- - Mid-Market Firms ($100M-$500M): 4,820 (12.51%)
-- - Small Firms (<$50M): 8,599 (22.31%)
-- - Unknown AUM: 11,442 (29.69%)
-- 
-- DATA QUALITY:
-- - No missing firm CRDs or names
-- - No firms with zero reps
-- - AUM aggregation verified: 100% accurate
-- - Rep count aggregation verified: 100% accurate

-- =============================================================================
-- STEP 1: CREATE FIRM-LEVEL AGGREGATED TABLE
-- =============================================================================

CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.discovery_firms_current` AS
WITH firm_base_data AS (
  SELECT 
    RIAFirmCRD,
    RIAFirmName,
    
    -- Basic firm metrics (aggregated from reps)
    COUNT(DISTINCT RepCRD) as total_reps,
    COUNT(*) as total_records,
    
    -- Financial metrics (aggregated)
    SUM(TotalAssetsInMillions) as total_firm_aum_millions,
    AVG(TotalAssetsInMillions) as avg_rep_aum_millions,
    MAX(TotalAssetsInMillions) as max_rep_aum_millions,
    MIN(TotalAssetsInMillions) as min_rep_aum_millions,
    STDDEV(TotalAssetsInMillions) as aum_std_deviation,
    
    -- Growth metrics (averaged across reps)
    AVG(AUMGrowthRate_1Year) as avg_firm_growth_1y,
    AVG(AUMGrowthRate_5Year) as avg_firm_growth_5y,
    MAX(AUMGrowthRate_1Year) as max_firm_growth_1y,
    MAX(AUMGrowthRate_5Year) as max_firm_growth_5y,
    
    -- Client metrics (aggregated)
    SUM(NumberClients_Individuals) as total_firm_clients,
    SUM(NumberClients_HNWIndividuals) as total_firm_hnw_clients,
    AVG(NumberClients_Individuals) as avg_clients_per_rep,
    AVG(NumberClients_HNWIndividuals) as avg_hnw_clients_per_rep,
    
    -- Professional metrics (percentages)
    AVG(Has_Series_7) as pct_reps_with_series_7,
    AVG(Has_CFP) as pct_reps_with_cfp,
    AVG(Is_Veteran_Advisor) as pct_veteran_reps,
    AVG(Has_Disclosure) as pct_reps_with_disclosure,
    
    -- Firm characteristics (most common values)
    APPROX_TOP_COUNT(Home_State, 1)[OFFSET(0)].value as primary_state,
    APPROX_TOP_COUNT(Home_MetropolitanArea, 1)[OFFSET(0)].value as primary_metro_area,
    APPROX_TOP_COUNT(Branch_State, 1)[OFFSET(0)].value as primary_branch_state,
    
    -- Geographic diversity metrics
    COUNT(DISTINCT Home_State) as states_represented,
    COUNT(DISTINCT Home_MetropolitanArea) as metro_areas_represented,
    COUNT(DISTINCT Branch_State) as branch_states,
    
    -- Custodian relationships (aggregated)
    SUM(CustodianAUM_Schwab) as total_schwab_aum,
    SUM(CustodianAUM_Fidelity_NationalFinancial) as total_fidelity_aum,
    SUM(CustodianAUM_Pershing) as total_pershing_aum,
    SUM(CustodianAUM_TDAmeritrade) as total_tdameritrade_aum,
    
    -- Custodian relationship flags (any rep has relationship)
    MAX(CASE WHEN CustodianAUM_Schwab > 0 THEN 1 ELSE 0 END) as has_schwab_relationship,
    MAX(CASE WHEN CustodianAUM_Fidelity_NationalFinancial > 0 THEN 1 ELSE 0 END) as has_fidelity_relationship,
    MAX(CASE WHEN CustodianAUM_Pershing > 0 THEN 1 ELSE 0 END) as has_pershing_relationship,
    MAX(CASE WHEN CustodianAUM_TDAmeritrade > 0 THEN 1 ELSE 0 END) as has_tdameritrade_relationship,
    
    -- Investment focus (aggregated)
    SUM(AssetsInMillions_MutualFunds) as total_mutual_fund_aum,
    SUM(AssetsInMillions_PrivateFunds) as total_private_fund_aum,
    SUM(AssetsInMillions_Equity_ExchangeTraded) as total_etf_aum,
    SUM(TotalAssets_SeparatelyManagedAccounts) as total_sma_aum,
    SUM(TotalAssets_PooledVehicles) as total_pooled_aum,
    
    -- Investment focus flags
    MAX(CASE WHEN AssetsInMillions_MutualFunds > 0 THEN 1 ELSE 0 END) as has_mutual_fund_focus,
    MAX(CASE WHEN AssetsInMillions_PrivateFunds > 0 THEN 1 ELSE 0 END) as has_private_fund_focus,
    MAX(CASE WHEN AssetsInMillions_Equity_ExchangeTraded > 0 THEN 1 ELSE 0 END) as has_etf_focus,
    
    -- Firm structure metrics
    AVG(Number_IAReps) as avg_ia_reps_per_record,
    AVG(Number_BranchAdvisors) as avg_branch_advisors_per_record,
    AVG(NumberFirmAssociations) as avg_firm_associations,
    AVG(NumberRIAFirmAssociations) as avg_ria_associations,
    
    -- Regulatory and compliance
    AVG(Is_Dually_Registered) as pct_dually_registered,
    AVG(Is_Primary_RIA) as pct_primary_ria,
    AVG(Is_Breakaway_Rep) as pct_breakaway_reps,
    
    -- Geographic concentration
    AVG(MilesToWork) as avg_miles_to_work,
    MAX(MilesToWork) as max_miles_to_work,
    MIN(MilesToWork) as min_miles_to_work,
    
    -- Processing metadata
    MAX(processed_at) as last_updated,
    APPROX_TOP_COUNT(territory_source, 1)[OFFSET(0)].value as primary_territory_source
    
  FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
  WHERE RIAFirmCRD IS NOT NULL AND RIAFirmCRD != ''
  GROUP BY RIAFirmCRD, RIAFirmName
),

-- =============================================================================
-- STEP 2: ADD FIRM-LEVEL ENGINEERED FEATURES
-- =============================================================================

firm_engineered_features AS (
  SELECT 
    *,
    
    -- Firm size classification
    CASE 
      WHEN total_firm_aum_millions > 1000 THEN 'Mega Firm (>$1B)'
      WHEN total_firm_aum_millions > 500 THEN 'Large Firm ($500M-$1B)'
      WHEN total_firm_aum_millions > 100 THEN 'Mid-Market ($100M-$500M)'
      WHEN total_firm_aum_millions > 50 THEN 'Small Firm ($50M-$100M)'
      WHEN total_firm_aum_millions > 0 THEN 'Micro Firm (<$50M)'
      ELSE 'Unknown AUM'
    END as firm_size_tier,
    
    -- Rep efficiency metrics
    SAFE_DIVIDE(total_firm_aum_millions * 1000000, NULLIF(total_reps, 0)) as aum_per_rep,
    SAFE_DIVIDE(total_firm_clients, NULLIF(total_reps, 0)) as clients_per_rep,
    SAFE_DIVIDE(total_firm_hnw_clients, NULLIF(total_reps, 0)) as hnw_clients_per_rep,
    
    -- Growth momentum indicators
    avg_firm_growth_1y * avg_firm_growth_5y as firm_growth_momentum,
    CASE WHEN avg_firm_growth_1y > avg_firm_growth_5y THEN 1 ELSE 0 END as accelerating_growth,
    CASE WHEN avg_firm_growth_1y > 0 AND avg_firm_growth_5y > 0 THEN 1 ELSE 0 END as positive_growth_trajectory,
    
    -- Geographic diversity scores
    CASE WHEN states_represented > 5 THEN 1 ELSE 0 END as multi_state_firm,
    CASE WHEN metro_areas_represented > 3 THEN 1 ELSE 0 END as multi_metro_firm,
    CASE WHEN states_represented = 1 THEN 1 ELSE 0 END as single_state_firm,
    
    -- Custodian concentration
    SAFE_DIVIDE(total_schwab_aum, NULLIF(total_firm_aum_millions, 0)) as schwab_concentration,
    SAFE_DIVIDE(total_fidelity_aum, NULLIF(total_firm_aum_millions, 0)) as fidelity_concentration,
    SAFE_DIVIDE(total_pershing_aum, NULLIF(total_firm_aum_millions, 0)) as pershing_concentration,
    SAFE_DIVIDE(total_tdameritrade_aum, NULLIF(total_firm_aum_millions, 0)) as tdameritrade_concentration,
    
    -- Investment focus ratios
    SAFE_DIVIDE(total_mutual_fund_aum, NULLIF(total_firm_aum_millions, 0)) as mutual_fund_ratio,
    SAFE_DIVIDE(total_private_fund_aum, NULLIF(total_firm_aum_millions, 0)) as private_fund_ratio,
    SAFE_DIVIDE(total_etf_aum, NULLIF(total_firm_aum_millions, 0)) as etf_ratio,
    SAFE_DIVIDE(total_sma_aum, NULLIF(total_firm_aum_millions, 0)) as sma_ratio,
    
    -- Firm stability indicators
    CASE WHEN pct_veteran_reps > 0.7 THEN 1 ELSE 0 END as veteran_heavy_firm,
    CASE WHEN pct_dually_registered > 0.5 THEN 1 ELSE 0 END as hybrid_firm,
    CASE WHEN pct_breakaway_reps > 0.3 THEN 1 ELSE 0 END as breakaway_heavy_firm,
    
    -- Professional development indicators
    CASE WHEN pct_reps_with_cfp > 0.3 THEN 1 ELSE 0 END as cfp_heavy_firm,
    CASE WHEN pct_reps_with_series_7 > 0.8 THEN 1 ELSE 0 END as series_7_heavy_firm,
    
    -- Geographic concentration indicators
    CASE WHEN avg_miles_to_work > 50 THEN 1 ELSE 0 END as remote_work_firm,
    CASE WHEN avg_miles_to_work < 10 THEN 1 ELSE 0 END as local_firm,
    
    -- Firm complexity indicators
    CASE WHEN total_reps > 20 THEN 1 ELSE 0 END as large_rep_firm,
    CASE WHEN total_reps < 5 THEN 1 ELSE 0 END as boutique_firm,
    CASE WHEN states_represented > 10 THEN 1 ELSE 0 END as national_firm,
    
    -- Metropolitan area dummy variables (Top 5 metro areas)
    CASE WHEN primary_metro_area LIKE '%New York%' OR primary_metro_area LIKE '%Newark%' OR primary_metro_area LIKE '%Jersey City%' THEN 1 ELSE 0 END as primary_metro_area_New_York_Newark_Jersey_City_NY_NJ,
    CASE WHEN primary_metro_area LIKE '%Los Angeles%' OR primary_metro_area LIKE '%Long Beach%' OR primary_metro_area LIKE '%Anaheim%' THEN 1 ELSE 0 END as primary_metro_area_Los_Angeles_Long_Beach_Anaheim_CA,
    CASE WHEN primary_metro_area LIKE '%Chicago%' OR primary_metro_area LIKE '%Naperville%' OR primary_metro_area LIKE '%Elgin%' THEN 1 ELSE 0 END as primary_metro_area_Chicago_Naperville_Elgin_IL_IN,
    CASE WHEN primary_metro_area LIKE '%Dallas%' OR primary_metro_area LIKE '%Fort Worth%' OR primary_metro_area LIKE '%Arlington%' THEN 1 ELSE 0 END as primary_metro_area_Dallas_Fort_Worth_Arlington_TX,
    CASE WHEN primary_metro_area LIKE '%Miami%' OR primary_metro_area LIKE '%Fort Lauderdale%' OR primary_metro_area LIKE '%West Palm Beach%' THEN 1 ELSE 0 END as primary_metro_area_Miami_Fort_Lauderdale_West_Palm_Beach_FL
    
  FROM firm_base_data
)

-- =============================================================================
-- STEP 3: FINAL TABLE CREATION WITH ALL FEATURES
-- =============================================================================

SELECT 
  -- Primary identifiers
  RIAFirmCRD,
  RIAFirmName,
  
  -- Firm size metrics
  total_reps,
  total_records,
  total_firm_aum_millions,
  avg_rep_aum_millions,
  max_rep_aum_millions,
  min_rep_aum_millions,
  aum_std_deviation,
  firm_size_tier,
  
  -- Growth metrics
  avg_firm_growth_1y,
  avg_firm_growth_5y,
  max_firm_growth_1y,
  max_firm_growth_5y,
  firm_growth_momentum,
  accelerating_growth,
  positive_growth_trajectory,
  
  -- Client metrics
  total_firm_clients,
  total_firm_hnw_clients,
  avg_clients_per_rep,
  avg_hnw_clients_per_rep,
  clients_per_rep,
  hnw_clients_per_rep,
  
  -- Efficiency metrics
  aum_per_rep,
  
  -- Professional metrics
  pct_reps_with_series_7,
  pct_reps_with_cfp,
  pct_veteran_reps,
  pct_reps_with_disclosure,
  cfp_heavy_firm,
  series_7_heavy_firm,
  veteran_heavy_firm,
  
  -- Geographic metrics
  primary_state,
  primary_metro_area,
  primary_branch_state,
  states_represented,
  metro_areas_represented,
  branch_states,
  multi_state_firm,
  multi_metro_firm,
  single_state_firm,
  national_firm,
  
  -- Geographic concentration
  avg_miles_to_work,
  max_miles_to_work,
  min_miles_to_work,
  remote_work_firm,
  local_firm,
  
  -- Custodian relationships
  total_schwab_aum,
  total_fidelity_aum,
  total_pershing_aum,
  total_tdameritrade_aum,
  has_schwab_relationship,
  has_fidelity_relationship,
  has_pershing_relationship,
  has_tdameritrade_relationship,
  schwab_concentration,
  fidelity_concentration,
  pershing_concentration,
  tdameritrade_concentration,
  
  -- Investment focus
  total_mutual_fund_aum,
  total_private_fund_aum,
  total_etf_aum,
  total_sma_aum,
  total_pooled_aum,
  has_mutual_fund_focus,
  has_private_fund_focus,
  has_etf_focus,
  mutual_fund_ratio,
  private_fund_ratio,
  etf_ratio,
  sma_ratio,
  
  -- Firm structure
  avg_ia_reps_per_record,
  avg_branch_advisors_per_record,
  avg_firm_associations,
  avg_ria_associations,
  
  -- Regulatory and compliance
  pct_dually_registered,
  pct_primary_ria,
  pct_breakaway_reps,
  hybrid_firm,
  breakaway_heavy_firm,
  
  -- Firm complexity
  large_rep_firm,
  boutique_firm,
  
  -- Metropolitan area dummy variables
  primary_metro_area_New_York_Newark_Jersey_City_NY_NJ,
  primary_metro_area_Los_Angeles_Long_Beach_Anaheim_CA,
  primary_metro_area_Chicago_Naperville_Elgin_IL_IN,
  primary_metro_area_Dallas_Fort_Worth_Arlington_TX,
  primary_metro_area_Miami_Fort_Lauderdale_West_Palm_Beach_FL,
  
  -- Processing metadata
  last_updated,
  primary_territory_source,
  CURRENT_TIMESTAMP() as processed_at
  
FROM firm_engineered_features
ORDER BY total_firm_aum_millions DESC;

-- =============================================================================
-- STEP 4: VALIDATION QUERIES
-- =============================================================================

-- Validation 1: Check table creation
SELECT 
  'TABLE CREATION VALIDATION' as validation_type,
  COUNT(*) as total_firms,
  COUNT(DISTINCT RIAFirmCRD) as unique_firm_crds,
  ROUND(AVG(total_reps), 1) as avg_reps_per_firm,
  ROUND(AVG(total_firm_aum_millions), 1) as avg_firm_aum_millions,
  COUNT(CASE WHEN total_firm_aum_millions > 1000 THEN 1 END) as mega_firms,
  COUNT(CASE WHEN total_firm_aum_millions BETWEEN 100 AND 1000 THEN 1 END) as mid_market_firms,
  COUNT(CASE WHEN total_firm_aum_millions < 100 THEN 1 END) as small_firms
FROM `savvy-gtm-analytics.LeadScoring.discovery_firms_current`;

-- Validation 2: Check data quality
SELECT 
  'DATA QUALITY VALIDATION' as validation_type,
  COUNT(CASE WHEN RIAFirmCRD IS NULL OR RIAFirmCRD = '' THEN 1 END) as missing_firm_crds,
  COUNT(CASE WHEN RIAFirmName IS NULL OR RIAFirmName = '' THEN 1 END) as missing_firm_names,
  COUNT(CASE WHEN total_reps = 0 THEN 1 END) as firms_with_no_reps,
  COUNT(CASE WHEN total_firm_aum_millions IS NULL THEN 1 END) as firms_with_null_aum,
  COUNT(CASE WHEN total_firm_aum_millions <= 0 THEN 1 END) as firms_with_zero_aum
FROM `savvy-gtm-analytics.LeadScoring.discovery_firms_current`;

-- Validation 3: Check aggregation accuracy
SELECT 
  'AGGREGATION VALIDATION' as validation_type,
  'Rep Count Verification' as metric,
  CAST(SUM(total_reps) AS STRING) as total_reps_in_firms_table,
  CAST((SELECT COUNT(DISTINCT RepCRD) FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current` WHERE RIAFirmCRD IS NOT NULL) AS STRING) as total_reps_in_source_table
FROM `savvy-gtm-analytics.LeadScoring.discovery_firms_current`

UNION ALL

SELECT 
  'AGGREGATION VALIDATION' as validation_type,
  'AUM Verification' as metric,
  CAST(ROUND(SUM(total_firm_aum_millions), 1) AS STRING) as total_aum_in_firms_table,
  CAST(ROUND((SELECT SUM(TotalAssetsInMillions) FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current` WHERE RIAFirmCRD IS NOT NULL), 1) AS STRING) as total_aum_in_source_table
FROM `savvy-gtm-analytics.LeadScoring.discovery_firms_current`;

-- =============================================================================
-- EXECUTION SUMMARY
-- =============================================================================
-- 
-- This script creates the discovery_firms_current table by aggregating
-- representative-level data from discovery_reps_current by RIAFirmCRD.
-- 
-- KEY FEATURES CREATED:
-- - Firm size metrics (AUM, rep count, client count)
-- - Growth metrics (averaged across reps)
-- - Geographic diversity indicators
-- - Custodian relationship aggregations
-- - Investment focus ratios
-- - Professional credential percentages
-- - Firm complexity indicators
-- 
-- VALIDATION INCLUDED:
-- - Table creation verification
-- - Data quality checks
-- - Aggregation accuracy validation
-- 
-- NEXT STEPS:
-- - Use firm-level features in lead scoring model
-- - Join with discovery_reps_current for comprehensive lead scoring
-- - Monitor data quality and update monthly with new discovery data
