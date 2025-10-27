-- Complete BigQuery SQL Pipeline for discovery_reps_current Table
-- This creates the unified MarketPro data table with feature engineering
-- Part of Phase 0, Week 1: Data Foundation

-- Step 1: Create empty table structure
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.discovery_reps_current` (
  RepCRD STRING,
  RIAFirmCRD STRING,
  TotalAssetsInMillions FLOAT64,
  Number_IAReps INT64,
  AUMGrowthRate_1Year FLOAT64,
  AUMGrowthRate_5Year FLOAT64,
  DateBecameRep_NumberOfYears FLOAT64,
  DateOfHireAtCurrentFirm_NumberOfYears FLOAT64,
  NumberClients_Individuals INT64,
  NumberClients_HNWIndividuals INT64,
  AssetsInMillions_Individuals FLOAT64,
  Home_MetropolitanArea STRING,
  NumberFirmAssociations INT64,
  NumberRIAFirmAssociations INT64,
  Number_BranchAdvisors INT64,
  NumberClients_RetirementPlans INT64,
  PercentClients_HNWIndividuals FLOAT64,
  PercentClients_Individuals FLOAT64,
  AssetsInMillions_HNWIndividuals FLOAT64,
  PercentAssets_HNWIndividuals FLOAT64,
  PercentAssets_Individuals FLOAT64,
  TotalAssets_SeparatelyManagedAccounts FLOAT64,
  TotalAssets_PooledVehicles FLOAT64,
  AssetsInMillions_MutualFunds FLOAT64,
  AssetsInMillions_PrivateFunds FLOAT64,
  AssetsInMillions_Equity_ExchangeTraded FLOAT64,
  PercentAssets_MutualFunds FLOAT64,
  PercentAssets_PrivateFunds FLOAT64,
  PercentAssets_Equity_ExchangeTraded FLOAT64,
  CustodianAUM_Fidelity_NationalFinancial FLOAT64,
  CustodianAUM_Pershing FLOAT64,
  CustodianAUM_Schwab FLOAT64,
  CustodianAUM_TDAmeritrade FLOAT64,
  Number_YearsPriorFirm1 FLOAT64,
  Number_YearsPriorFirm2 FLOAT64,
  Number_YearsPriorFirm3 FLOAT64,
  Number_YearsPriorFirm4 FLOAT64,
  Licenses STRING,
  RegulatoryDisclosures STRING,
  Education STRING,
  Gender STRING,
  KnownNonAdvisor STRING,
  DuallyRegisteredBDRIARep STRING,
  IsPrimaryRIAFirm STRING,
  BreakawayRep STRING,
  Custodian1 STRING,
  Custodian2 STRING,
  Custodian3 STRING,
  Custodian4 STRING,
  Custodian5 STRING,
  Branch_State STRING,
  Home_State STRING,
  Branch_City STRING,
  Home_City STRING,
  Branch_County STRING,
  Home_County STRING,
  Branch_ZipCode FLOAT64,
  Home_ZipCode FLOAT64,
  Branch_Longitude FLOAT64,
  Branch_Latitude FLOAT64,
  Home_Longitude FLOAT64,
  Home_Latitude FLOAT64,
  MilesToWork FLOAT64,
  FirstName STRING,
  LastName STRING,
  Title STRING,
  RIAFirmName STRING,
  Email_BusinessType STRING,
  Email_PersonalType STRING,
  SocialMedia_LinkedIn STRING,
  PersonalWebpage STRING,
  FirmWebsite STRING,
  Brochure_Keywords STRING,
  Notes STRING,
  CustomKeywords STRING,
  territory_source STRING,
  processed_at TIMESTAMP
);

-- Step 2: Insert T1 data (with SAFE_CAST and explicit string casting)
INSERT INTO `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
SELECT 
  CAST(RepCRD AS STRING) as RepCRD,
  CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
  SAFE_CAST(REGEXP_REPLACE(TotalAssetsInMillions, r'[$,]', '') AS FLOAT64) as TotalAssetsInMillions,
  SAFE_CAST(Number_IAReps AS INT64) as Number_IAReps,
  SAFE_CAST(AUMGrowthRate_1Year AS FLOAT64) as AUMGrowthRate_1Year,
  SAFE_CAST(AUMGrowthRate_5Year AS FLOAT64) as AUMGrowthRate_5Year,
  SAFE_CAST(DateBecameRep_NumberOfYears AS FLOAT64) as DateBecameRep_NumberOfYears,
  SAFE_CAST(DateOfHireAtCurrentFirm_NumberOfYears AS FLOAT64) as DateOfHireAtCurrentFirm_NumberOfYears,
  CASE 
    WHEN NumberClients_Individuals = '< 5' THEN 2
    WHEN NumberClients_Individuals = '' OR NumberClients_Individuals IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_Individuals AS INT64)
  END as NumberClients_Individuals,
  CASE 
    WHEN NumberClients_HNWIndividuals = '< 5' THEN 2
    WHEN NumberClients_HNWIndividuals = '' OR NumberClients_HNWIndividuals IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_HNWIndividuals AS INT64)
  END as NumberClients_HNWIndividuals,
  SAFE_CAST(AssetsInMillions_Individuals AS FLOAT64) as AssetsInMillions_Individuals,
  CAST(Home_MetropolitanArea AS STRING) as Home_MetropolitanArea,
  SAFE_CAST(NumberFirmAssociations AS INT64) as NumberFirmAssociations,
  SAFE_CAST(NumberRIAFirmAssociations AS INT64) as NumberRIAFirmAssociations,
  SAFE_CAST(Number_BranchAdvisors AS INT64) as Number_BranchAdvisors,
  CASE 
    WHEN NumberClients_RetirementPlans = '< 5' THEN 2
    WHEN NumberClients_RetirementPlans = '' OR NumberClients_RetirementPlans IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_RetirementPlans AS INT64)
  END as NumberClients_RetirementPlans,
  SAFE_CAST(PercentClients_HNWIndividuals AS FLOAT64) as PercentClients_HNWIndividuals,
  SAFE_CAST(PercentClients_Individuals AS FLOAT64) as PercentClients_Individuals,
  SAFE_CAST(AssetsInMillions_HNWIndividuals AS FLOAT64) as AssetsInMillions_HNWIndividuals,
  SAFE_CAST(PercentAssets_HNWIndividuals AS FLOAT64) as PercentAssets_HNWIndividuals,
  SAFE_CAST(PercentAssets_Individuals AS FLOAT64) as PercentAssets_Individuals,
  SAFE_CAST(TotalAssets_SeparatelyManagedAccounts AS FLOAT64) as TotalAssets_SeparatelyManagedAccounts,
  SAFE_CAST(TotalAssets_PooledVehicles AS FLOAT64) as TotalAssets_PooledVehicles,
  SAFE_CAST(AssetsInMillions_MutualFunds AS FLOAT64) as AssetsInMillions_MutualFunds,
  SAFE_CAST(AssetsInMillions_PrivateFunds AS FLOAT64) as AssetsInMillions_PrivateFunds,
  SAFE_CAST(AssetsInMillions_Equity_ExchangeTraded AS FLOAT64) as AssetsInMillions_Equity_ExchangeTraded,
  SAFE_CAST(PercentAssets_MutualFunds AS FLOAT64) as PercentAssets_MutualFunds,
  SAFE_CAST(PercentAssets_PrivateFunds AS FLOAT64) as PercentAssets_PrivateFunds,
  SAFE_CAST(PercentAssets_Equity_ExchangeTraded AS FLOAT64) as PercentAssets_Equity_ExchangeTraded,
  SAFE_CAST(CustodianAUM_Fidelity_NationalFinancial AS FLOAT64) as CustodianAUM_Fidelity_NationalFinancial,
  SAFE_CAST(CustodianAUM_Pershing AS FLOAT64) as CustodianAUM_Pershing,
  SAFE_CAST(CustodianAUM_Schwab AS FLOAT64) as CustodianAUM_Schwab,
  SAFE_CAST(CustodianAUM_TDAmeritrade AS FLOAT64) as CustodianAUM_TDAmeritrade,
  SAFE_CAST(Number_YearsPriorFirm1 AS FLOAT64) as Number_YearsPriorFirm1,
  SAFE_CAST(Number_YearsPriorFirm2 AS FLOAT64) as Number_YearsPriorFirm2,
  SAFE_CAST(Number_YearsPriorFirm3 AS FLOAT64) as Number_YearsPriorFirm3,
  SAFE_CAST(Number_YearsPriorFirm4 AS FLOAT64) as Number_YearsPriorFirm4,
  CAST(Licenses AS STRING) as Licenses,
  CAST(RegulatoryDisclosures AS STRING) as RegulatoryDisclosures,
  CAST(Education AS STRING) as Education,
  CAST(Gender AS STRING) as Gender,
  CAST(KnownNonAdvisor AS STRING) as KnownNonAdvisor,
  CAST(DuallyRegisteredBDRIARep AS STRING) as DuallyRegisteredBDRIARep,
  CAST(IsPrimaryRIAFirm AS STRING) as IsPrimaryRIAFirm,
  CAST(BreakawayRep AS STRING) as BreakawayRep,
  CAST(Custodian1 AS STRING) as Custodian1,
  CAST(Custodian2 AS STRING) as Custodian2,
  CAST(Custodian3 AS STRING) as Custodian3,
  CAST(Custodian4 AS STRING) as Custodian4,
  CAST(Custodian5 AS STRING) as Custodian5,
  CAST(Branch_State AS STRING) as Branch_State,
  CAST(Home_State AS STRING) as Home_State,
  CAST(Branch_City AS STRING) as Branch_City,
  CAST(Home_City AS STRING) as Home_City,
  CAST(Branch_County AS STRING) as Branch_County,
  CAST(Home_County AS STRING) as Home_County,
  SAFE_CAST(Branch_ZipCode AS FLOAT64) as Branch_ZipCode,
  SAFE_CAST(Home_ZipCode AS FLOAT64) as Home_ZipCode,
  SAFE_CAST(Branch_Longitude AS FLOAT64) as Branch_Longitude,
  SAFE_CAST(Branch_Latitude AS FLOAT64) as Branch_Latitude,
  SAFE_CAST(Home_Longitude AS FLOAT64) as Home_Longitude,
  SAFE_CAST(Home_Latitude AS FLOAT64) as Home_Latitude,
  SAFE_CAST(MilesToWork AS FLOAT64) as MilesToWork,
  CAST(FirstName AS STRING) as FirstName,
  CAST(LastName AS STRING) as LastName,
  CAST(Title AS STRING) as Title,
  CAST(RIAFirmName AS STRING) as RIAFirmName,
  CAST(Email_BusinessType AS STRING) as Email_BusinessType,
  CAST(Email_PersonalType AS STRING) as Email_PersonalType,
  CAST(SocialMedia_LinkedIn AS STRING) as SocialMedia_LinkedIn,
  CAST(PersonalWebpage AS STRING) as PersonalWebpage,
  CAST(FirmWebsite AS STRING) as FirmWebsite,
  CAST(Brochure_Keywords AS STRING) as Brochure_Keywords,
  CAST(Notes AS STRING) as Notes,
  CAST(CustomKeywords AS STRING) as CustomKeywords,
  'T1' as territory_source,
  CURRENT_TIMESTAMP() as processed_at
FROM `savvy-gtm-analytics.LeadScoring.staging_discovery_t1`;

-- Step 3: Insert T2 data (with SAFE_CAST and explicit string casting)
INSERT INTO `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
SELECT 
  CAST(RepCRD AS STRING) as RepCRD,
  CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
  SAFE_CAST(REGEXP_REPLACE(TotalAssetsInMillions, r'[$,]', '') AS FLOAT64) as TotalAssetsInMillions,
  SAFE_CAST(Number_IAReps AS INT64) as Number_IAReps,
  SAFE_CAST(AUMGrowthRate_1Year AS FLOAT64) as AUMGrowthRate_1Year,
  SAFE_CAST(AUMGrowthRate_5Year AS FLOAT64) as AUMGrowthRate_5Year,
  SAFE_CAST(DateBecameRep_NumberOfYears AS FLOAT64) as DateBecameRep_NumberOfYears,
  SAFE_CAST(DateOfHireAtCurrentFirm_NumberOfYears AS FLOAT64) as DateOfHireAtCurrentFirm_NumberOfYears,
  CASE 
    WHEN NumberClients_Individuals = '< 5' THEN 2
    WHEN NumberClients_Individuals = '' OR NumberClients_Individuals IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_Individuals AS INT64)
  END as NumberClients_Individuals,
  CASE 
    WHEN NumberClients_HNWIndividuals = '< 5' THEN 2
    WHEN NumberClients_HNWIndividuals = '' OR NumberClients_HNWIndividuals IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_HNWIndividuals AS INT64)
  END as NumberClients_HNWIndividuals,
  SAFE_CAST(AssetsInMillions_Individuals AS FLOAT64) as AssetsInMillions_Individuals,
  CAST(Home_MetropolitanArea AS STRING) as Home_MetropolitanArea,
  SAFE_CAST(NumberFirmAssociations AS INT64) as NumberFirmAssociations,
  SAFE_CAST(NumberRIAFirmAssociations AS INT64) as NumberRIAFirmAssociations,
  SAFE_CAST(Number_BranchAdvisors AS INT64) as Number_BranchAdvisors,
  CASE 
    WHEN NumberClients_RetirementPlans = '< 5' THEN 2
    WHEN NumberClients_RetirementPlans = '' OR NumberClients_RetirementPlans IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_RetirementPlans AS INT64)
  END as NumberClients_RetirementPlans,
  SAFE_CAST(PercentClients_HNWIndividuals AS FLOAT64) as PercentClients_HNWIndividuals,
  SAFE_CAST(PercentClients_Individuals AS FLOAT64) as PercentClients_Individuals,
  SAFE_CAST(AssetsInMillions_HNWIndividuals AS FLOAT64) as AssetsInMillions_HNWIndividuals,
  SAFE_CAST(PercentAssets_HNWIndividuals AS FLOAT64) as PercentAssets_HNWIndividuals,
  SAFE_CAST(PercentAssets_Individuals AS FLOAT64) as PercentAssets_Individuals,
  SAFE_CAST(TotalAssets_SeparatelyManagedAccounts AS FLOAT64) as TotalAssets_SeparatelyManagedAccounts,
  SAFE_CAST(TotalAssets_PooledVehicles AS FLOAT64) as TotalAssets_PooledVehicles,
  SAFE_CAST(AssetsInMillions_MutualFunds AS FLOAT64) as AssetsInMillions_MutualFunds,
  SAFE_CAST(AssetsInMillions_PrivateFunds AS FLOAT64) as AssetsInMillions_PrivateFunds,
  SAFE_CAST(AssetsInMillions_Equity_ExchangeTraded AS FLOAT64) as AssetsInMillions_Equity_ExchangeTraded,
  SAFE_CAST(PercentAssets_MutualFunds AS FLOAT64) as PercentAssets_MutualFunds,
  SAFE_CAST(PercentAssets_PrivateFunds AS FLOAT64) as PercentAssets_PrivateFunds,
  SAFE_CAST(PercentAssets_Equity_ExchangeTraded AS FLOAT64) as PercentAssets_Equity_ExchangeTraded,
  SAFE_CAST(CustodianAUM_Fidelity_NationalFinancial AS FLOAT64) as CustodianAUM_Fidelity_NationalFinancial,
  SAFE_CAST(CustodianAUM_Pershing AS FLOAT64) as CustodianAUM_Pershing,
  SAFE_CAST(CustodianAUM_Schwab AS FLOAT64) as CustodianAUM_Schwab,
  SAFE_CAST(CustodianAUM_TDAmeritrade AS FLOAT64) as CustodianAUM_TDAmeritrade,
  SAFE_CAST(Number_YearsPriorFirm1 AS FLOAT64) as Number_YearsPriorFirm1,
  SAFE_CAST(Number_YearsPriorFirm2 AS FLOAT64) as Number_YearsPriorFirm2,
  SAFE_CAST(Number_YearsPriorFirm3 AS FLOAT64) as Number_YearsPriorFirm3,
  SAFE_CAST(Number_YearsPriorFirm4 AS FLOAT64) as Number_YearsPriorFirm4,
  CAST(Licenses AS STRING) as Licenses,
  CAST(RegulatoryDisclosures AS STRING) as RegulatoryDisclosures,
  CAST(Education AS STRING) as Education,
  CAST(Gender AS STRING) as Gender,
  CAST(KnownNonAdvisor AS STRING) as KnownNonAdvisor,
  CAST(DuallyRegisteredBDRIARep AS STRING) as DuallyRegisteredBDRIARep,
  CAST(IsPrimaryRIAFirm AS STRING) as IsPrimaryRIAFirm,
  CAST(BreakawayRep AS STRING) as BreakawayRep,
  CAST(Custodian1 AS STRING) as Custodian1,
  CAST(Custodian2 AS STRING) as Custodian2,
  CAST(Custodian3 AS STRING) as Custodian3,
  CAST(Custodian4 AS STRING) as Custodian4,
  CAST(Custodian5 AS STRING) as Custodian5,
  CAST(Branch_State AS STRING) as Branch_State,
  CAST(Home_State AS STRING) as Home_State,
  CAST(Branch_City AS STRING) as Branch_City,
  CAST(Home_City AS STRING) as Home_City,
  CAST(Branch_County AS STRING) as Branch_County,
  CAST(Home_County AS STRING) as Home_County,
  SAFE_CAST(Branch_ZipCode AS FLOAT64) as Branch_ZipCode,
  SAFE_CAST(Home_ZipCode AS FLOAT64) as Home_ZipCode,
  SAFE_CAST(Branch_Longitude AS FLOAT64) as Branch_Longitude,
  SAFE_CAST(Branch_Latitude AS FLOAT64) as Branch_Latitude,
  SAFE_CAST(Home_Longitude AS FLOAT64) as Home_Longitude,
  SAFE_CAST(Home_Latitude AS FLOAT64) as Home_Latitude,
  SAFE_CAST(MilesToWork AS FLOAT64) as MilesToWork,
  CAST(FirstName AS STRING) as FirstName,
  CAST(LastName AS STRING) as LastName,
  CAST(Title AS STRING) as Title,
  CAST(RIAFirmName AS STRING) as RIAFirmName,
  CAST(Email_BusinessType AS STRING) as Email_BusinessType,
  CAST(Email_PersonalType AS STRING) as Email_PersonalType,
  CAST(SocialMedia_LinkedIn AS STRING) as SocialMedia_LinkedIn,
  CAST(PersonalWebpage AS STRING) as PersonalWebpage,
  CAST(FirmWebsite AS STRING) as FirmWebsite,
  CAST(Brochure_Keywords AS STRING) as Brochure_Keywords,
  CAST(Notes AS STRING) as Notes,
  CAST(CustomKeywords AS STRING) as CustomKeywords,
  'T2' as territory_source,
  CURRENT_TIMESTAMP() as processed_at
FROM `savvy-gtm-analytics.LeadScoring.staging_discovery_t2`;

-- Step 4: Insert T3 data (with SAFE_CAST and explicit string casting)
INSERT INTO `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
SELECT 
  CAST(RepCRD AS STRING) as RepCRD,
  CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
  SAFE_CAST(REGEXP_REPLACE(TotalAssetsInMillions, r'[$,]', '') AS FLOAT64) as TotalAssetsInMillions,
  SAFE_CAST(Number_IAReps AS INT64) as Number_IAReps,
  SAFE_CAST(AUMGrowthRate_1Year AS FLOAT64) as AUMGrowthRate_1Year,
  SAFE_CAST(AUMGrowthRate_5Year AS FLOAT64) as AUMGrowthRate_5Year,
  SAFE_CAST(DateBecameRep_NumberOfYears AS FLOAT64) as DateBecameRep_NumberOfYears,
  SAFE_CAST(DateOfHireAtCurrentFirm_NumberOfYears AS FLOAT64) as DateOfHireAtCurrentFirm_NumberOfYears,
  CASE 
    WHEN NumberClients_Individuals = '< 5' THEN 2
    WHEN NumberClients_Individuals = '' OR NumberClients_Individuals IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_Individuals AS INT64)
  END as NumberClients_Individuals,
  CASE 
    WHEN NumberClients_HNWIndividuals = '< 5' THEN 2
    WHEN NumberClients_HNWIndividuals = '' OR NumberClients_HNWIndividuals IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_HNWIndividuals AS INT64)
  END as NumberClients_HNWIndividuals,
  SAFE_CAST(AssetsInMillions_Individuals AS FLOAT64) as AssetsInMillions_Individuals,
  CAST(Home_MetropolitanArea AS STRING) as Home_MetropolitanArea,
  SAFE_CAST(NumberFirmAssociations AS INT64) as NumberFirmAssociations,
  SAFE_CAST(NumberRIAFirmAssociations AS INT64) as NumberRIAFirmAssociations,
  SAFE_CAST(Number_BranchAdvisors AS INT64) as Number_BranchAdvisors,
  CASE 
    WHEN NumberClients_RetirementPlans = '< 5' THEN 2
    WHEN NumberClients_RetirementPlans = '' OR NumberClients_RetirementPlans IS NULL THEN NULL
    ELSE SAFE_CAST(NumberClients_RetirementPlans AS INT64)
  END as NumberClients_RetirementPlans,
  SAFE_CAST(PercentClients_HNWIndividuals AS FLOAT64) as PercentClients_HNWIndividuals,
  SAFE_CAST(PercentClients_Individuals AS FLOAT64) as PercentClients_Individuals,
  SAFE_CAST(AssetsInMillions_HNWIndividuals AS FLOAT64) as AssetsInMillions_HNWIndividuals,
  SAFE_CAST(PercentAssets_HNWIndividuals AS FLOAT64) as PercentAssets_HNWIndividuals,
  SAFE_CAST(PercentAssets_Individuals AS FLOAT64) as PercentAssets_Individuals,
  SAFE_CAST(TotalAssets_SeparatelyManagedAccounts AS FLOAT64) as TotalAssets_SeparatelyManagedAccounts,
  SAFE_CAST(TotalAssets_PooledVehicles AS FLOAT64) as TotalAssets_PooledVehicles,
  SAFE_CAST(AssetsInMillions_MutualFunds AS FLOAT64) as AssetsInMillions_MutualFunds,
  SAFE_CAST(AssetsInMillions_PrivateFunds AS FLOAT64) as AssetsInMillions_PrivateFunds,
  SAFE_CAST(AssetsInMillions_Equity_ExchangeTraded AS FLOAT64) as AssetsInMillions_Equity_ExchangeTraded,
  SAFE_CAST(PercentAssets_MutualFunds AS FLOAT64) as PercentAssets_MutualFunds,
  SAFE_CAST(PercentAssets_PrivateFunds AS FLOAT64) as PercentAssets_PrivateFunds,
  SAFE_CAST(PercentAssets_Equity_ExchangeTraded AS FLOAT64) as PercentAssets_Equity_ExchangeTraded,
  SAFE_CAST(CustodianAUM_Fidelity_NationalFinancial AS FLOAT64) as CustodianAUM_Fidelity_NationalFinancial,
  SAFE_CAST(CustodianAUM_Pershing AS FLOAT64) as CustodianAUM_Pershing,
  SAFE_CAST(CustodianAUM_Schwab AS FLOAT64) as CustodianAUM_Schwab,
  SAFE_CAST(CustodianAUM_TDAmeritrade AS FLOAT64) as CustodianAUM_TDAmeritrade,
  SAFE_CAST(Number_YearsPriorFirm1 AS FLOAT64) as Number_YearsPriorFirm1,
  SAFE_CAST(Number_YearsPriorFirm2 AS FLOAT64) as Number_YearsPriorFirm2,
  SAFE_CAST(Number_YearsPriorFirm3 AS FLOAT64) as Number_YearsPriorFirm3,
  SAFE_CAST(Number_YearsPriorFirm4 AS FLOAT64) as Number_YearsPriorFirm4,
  CAST(Licenses AS STRING) as Licenses,
  CAST(RegulatoryDisclosures AS STRING) as RegulatoryDisclosures,
  CAST(Education AS STRING) as Education,
  CAST(Gender AS STRING) as Gender,
  CAST(KnownNonAdvisor AS STRING) as KnownNonAdvisor,
  CAST(DuallyRegisteredBDRIARep AS STRING) as DuallyRegisteredBDRIARep,
  CAST(IsPrimaryRIAFirm AS STRING) as IsPrimaryRIAFirm,
  CAST(BreakawayRep AS STRING) as BreakawayRep,
  CAST(Custodian1 AS STRING) as Custodian1,
  CAST(Custodian2 AS STRING) as Custodian2,
  CAST(Custodian3 AS STRING) as Custodian3,
  CAST(Custodian4 AS STRING) as Custodian4,
  CAST(Custodian5 AS STRING) as Custodian5,
  CAST(Branch_State AS STRING) as Branch_State,
  CAST(Home_State AS STRING) as Home_State,
  CAST(Branch_City AS STRING) as Branch_City,
  CAST(Home_City AS STRING) as Home_City,
  CAST(Branch_County AS STRING) as Branch_County,
  CAST(Home_County AS STRING) as Home_County,
  SAFE_CAST(Branch_ZipCode AS FLOAT64) as Branch_ZipCode,
  SAFE_CAST(Home_ZipCode AS FLOAT64) as Home_ZipCode,
  SAFE_CAST(Branch_Longitude AS FLOAT64) as Branch_Longitude,
  SAFE_CAST(Branch_Latitude AS FLOAT64) as Branch_Latitude,
  SAFE_CAST(Home_Longitude AS FLOAT64) as Home_Longitude,
  SAFE_CAST(Home_Latitude AS FLOAT64) as Home_Latitude,
  SAFE_CAST(MilesToWork AS FLOAT64) as MilesToWork,
  CAST(FirstName AS STRING) as FirstName,
  CAST(LastName AS STRING) as LastName,
  CAST(Title AS STRING) as Title,
  CAST(RIAFirmName AS STRING) as RIAFirmName,
  CAST(Email_BusinessType AS STRING) as Email_BusinessType,
  CAST(Email_PersonalType AS STRING) as Email_PersonalType,
  CAST(SocialMedia_LinkedIn AS STRING) as SocialMedia_LinkedIn,
  CAST(PersonalWebpage AS STRING) as PersonalWebpage,
  CAST(FirmWebsite AS STRING) as FirmWebsite,
  CAST(Brochure_Keywords AS STRING) as Brochure_Keywords,
  CAST(Notes AS STRING) as Notes,
  CAST(CustomKeywords AS STRING) as CustomKeywords,
  'T3' as territory_source,
  CURRENT_TIMESTAMP() as processed_at
FROM `savvy-gtm-analytics.LeadScoring.staging_discovery_t3`;

-- Step 5: Apply deduplication and feature engineering
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.discovery_reps_current` AS
WITH deduplicated_data AS (
  SELECT 
    *,
    ROW_NUMBER() OVER (
      PARTITION BY RepCRD, RIAFirmCRD 
      ORDER BY processed_at DESC, territory_source
    ) as dedup_rank
  FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
),
base_data AS (
  SELECT * FROM deduplicated_data WHERE dedup_rank = 1
),
engineered_features AS (
  SELECT 
    *,
    -- Efficiency metrics
    SAFE_DIVIDE(TotalAssetsInMillions * 1000000, NULLIF(NumberClients_Individuals, 0)) as AUM_Per_Client,
    SAFE_DIVIDE(TotalAssetsInMillions * 1000000, NULLIF(Number_IAReps, 0)) as AUM_Per_IARep,
    SAFE_DIVIDE(TotalAssetsInMillions * 1000000, NULLIF(Number_BranchAdvisors, 0)) as AUM_Per_BranchAdvisor,
    
    -- Growth indicators
    AUMGrowthRate_1Year * AUMGrowthRate_5Year as Growth_Momentum,
    CASE WHEN AUMGrowthRate_1Year > AUMGrowthRate_5Year THEN 1 ELSE 0 END as Accelerating_Growth,
    CASE WHEN AUMGrowthRate_1Year > 0 AND AUMGrowthRate_5Year > 0 THEN 1 ELSE 0 END as Positive_Growth_Trajectory,
    
    -- Firm stability
    DateBecameRep_NumberOfYears + DateOfHireAtCurrentFirm_NumberOfYears as Firm_Stability_Score,
    CASE WHEN DateBecameRep_NumberOfYears > 10 THEN 1 ELSE 0 END as Is_Veteran_Advisor,
    CASE WHEN DateOfHireAtCurrentFirm_NumberOfYears < 2 THEN 1 ELSE 0 END as Is_New_To_Firm,
    
    -- Client focus
    SAFE_DIVIDE(NumberClients_HNWIndividuals, NULLIF(NumberClients_Individuals, 0)) as HNW_Client_Ratio,
    SAFE_DIVIDE(AssetsInMillions_Individuals, NULLIF(TotalAssetsInMillions, 0)) as Individual_Asset_Ratio,
    SAFE_DIVIDE(AssetsInMillions_HNWIndividuals, NULLIF(TotalAssetsInMillions, 0)) as HNW_Asset_Concentration,
    
    -- Operational metrics
    SAFE_DIVIDE(NumberClients_Individuals, NULLIF(Number_IAReps, 0)) as Clients_per_IARep,
    SAFE_DIVIDE(NumberClients_Individuals, NULLIF(Number_BranchAdvisors, 0)) as Clients_per_BranchAdvisor,
    CASE WHEN NumberFirmAssociations > 1 THEN 1 ELSE 0 END as Multi_Firm_Associations,
    CASE WHEN NumberRIAFirmAssociations > 1 THEN 1 ELSE 0 END as Multi_RIA_Relationships,
    
    -- Geographic factors
    CASE WHEN MilesToWork > 50 THEN 1 ELSE 0 END as Remote_Work_Indicator,
    CASE WHEN MilesToWork < 10 THEN 1 ELSE 0 END as Local_Advisor,
    
    -- Quality & Performance indicators
    CASE WHEN TotalAssetsInMillions > 100 THEN 1 ELSE 0 END as Is_Large_Firm,
    CASE WHEN TotalAssetsInMillions < 50 AND NumberClients_Individuals < 100 THEN 1 ELSE 0 END as Is_Boutique_Firm,
    CASE WHEN TotalAssetsInMillions > 50 OR NumberClients_Individuals > 100 THEN 1 ELSE 0 END as Has_Scale,
    CASE WHEN DuallyRegisteredBDRIARep = 'Yes' THEN 1 ELSE 0 END as Is_Dually_Registered,
    CASE WHEN IsPrimaryRIAFirm = 'Yes' THEN 1 ELSE 0 END as Is_Primary_RIA,
    CASE WHEN BreakawayRep = 'Yes' THEN 1 ELSE 0 END as Is_Breakaway_Rep,
    
    -- Investment sophistication
    CASE WHEN AssetsInMillions_PrivateFunds > 0 THEN 1 ELSE 0 END as Has_Private_Funds,
    CASE WHEN AssetsInMillions_Equity_ExchangeTraded > 0 THEN 1 ELSE 0 END as Has_ETF_Focus,
    CASE WHEN AssetsInMillions_MutualFunds > 0 THEN 1 ELSE 0 END as Has_Mutual_Fund_Focus,
    
    -- Custodian relationships
    CASE WHEN CustodianAUM_Schwab > 0 THEN 1 ELSE 0 END as Has_Schwab_Relationship,
    CASE WHEN CustodianAUM_Fidelity_NationalFinancial > 0 THEN 1 ELSE 0 END as Has_Fidelity_Relationship,
    CASE WHEN CustodianAUM_Pershing > 0 THEN 1 ELSE 0 END as Has_Pershing_Relationship,
    CASE WHEN CustodianAUM_TDAmeritrade > 0 THEN 1 ELSE 0 END as Has_TDAmeritrade_Relationship,
    
    -- Career mobility
    COALESCE(Number_YearsPriorFirm1, 0) + COALESCE(Number_YearsPriorFirm2, 0) + 
    COALESCE(Number_YearsPriorFirm3, 0) + COALESCE(Number_YearsPriorFirm4, 0) as Total_Prior_Firm_Years,
    CASE WHEN Number_YearsPriorFirm1 IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN Number_YearsPriorFirm2 IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN Number_YearsPriorFirm3 IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN Number_YearsPriorFirm4 IS NOT NULL THEN 1 ELSE 0 END as Number_Of_Prior_Firms,
    
    -- Professional credentials
    CASE WHEN Licenses LIKE '%7%' THEN 1 ELSE 0 END as Has_Series_7,
    CASE WHEN Licenses LIKE '%65%' THEN 1 ELSE 0 END as Has_Series_65,
    CASE WHEN Licenses LIKE '%66%' THEN 1 ELSE 0 END as Has_Series_66,
    CASE WHEN Licenses LIKE '%24%' THEN 1 ELSE 0 END as Has_Series_24,
    CASE WHEN Licenses LIKE '%CFP%' THEN 1 ELSE 0 END as Has_CFP,
    CASE WHEN Licenses LIKE '%CFA%' THEN 1 ELSE 0 END as Has_CFA,
    CASE WHEN Licenses LIKE '%CIMA%' THEN 1 ELSE 0 END as Has_CIMA,
    CASE WHEN Licenses LIKE '%AIF%' THEN 1 ELSE 0 END as Has_AIF,
    
    -- Regulatory status
    CASE WHEN RegulatoryDisclosures = 'No' THEN 0 ELSE 1 END as Has_Disclosure,
    CASE WHEN KnownNonAdvisor = 'Yes' THEN 1 ELSE 0 END as Is_Known_Non_Advisor,
    
    -- Metropolitan area dummy variables (Top 5 metro areas)
    CASE WHEN Home_MetropolitanArea LIKE '%New York%' OR Home_MetropolitanArea LIKE '%Newark%' OR Home_MetropolitanArea LIKE '%Jersey City%' THEN 1 ELSE 0 END as Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ,
    CASE WHEN Home_MetropolitanArea LIKE '%Los Angeles%' OR Home_MetropolitanArea LIKE '%Long Beach%' OR Home_MetropolitanArea LIKE '%Anaheim%' THEN 1 ELSE 0 END as Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA,
    CASE WHEN Home_MetropolitanArea LIKE '%Chicago%' OR Home_MetropolitanArea LIKE '%Naperville%' OR Home_MetropolitanArea LIKE '%Elgin%' THEN 1 ELSE 0 END as Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN,
    CASE WHEN Home_MetropolitanArea LIKE '%Dallas%' OR Home_MetropolitanArea LIKE '%Fort Worth%' OR Home_MetropolitanArea LIKE '%Arlington%' THEN 1 ELSE 0 END as Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX,
    CASE WHEN Home_MetropolitanArea LIKE '%Miami%' OR Home_MetropolitanArea LIKE '%Fort Lauderdale%' OR Home_MetropolitanArea LIKE '%West Palm Beach%' THEN 1 ELSE 0 END as Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL
    
  FROM base_data
)
SELECT * FROM engineered_features;

-- Final validation query
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT RepCRD) as unique_reps,
  COUNT(DISTINCT RIAFirmCRD) as unique_firms,
  COUNT(DISTINCT territory_source) as territories,
  COUNT(*) - COUNT(DISTINCT RepCRD) as duplicates_removed
FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current`;
