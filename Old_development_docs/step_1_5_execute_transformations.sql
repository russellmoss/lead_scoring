-- Step 1.5: Transform Raw CSV to Standardized Schema
-- This file contains all 8 transformation queries for Step 1.5
-- Execute each query separately or as a batch

-- ============================================================================
-- 1. 20240107 (Jan 7, 2024)
-- ============================================================================
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240107` AS
SELECT 
  -- Identifiers
  CAST(RepCRD AS STRING) as RepCRD,
  CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
  
  -- Financial metrics (NOT AVAILABLE - set to NULL)
  CAST(NULL AS FLOAT64) as TotalAssetsInMillions,
  CAST(NULL AS INT64) as Number_IAReps,
  CAST(NULL AS FLOAT64) as AUMGrowthRate_1Year,
  CAST(NULL AS FLOAT64) as AUMGrowthRate_5Year,
  
  -- Tenure metrics
  SAFE_CAST(DateBecameRep_NumberOfYears AS FLOAT64) as DateBecameRep_NumberOfYears,
  SAFE_CAST(DateOfHireAtCurrentFirm_NumberOfYears AS FLOAT64) as DateOfHireAtCurrentFirm_NumberOfYears,
  
  -- Client metrics (NOT AVAILABLE - set to NULL)
  CAST(NULL AS INT64) as NumberClients_Individuals,
  CAST(NULL AS INT64) as NumberClients_HNWIndividuals,
  CAST(NULL AS INT64) as NumberClients_RetirementPlans,
  
  -- Asset metrics (NOT AVAILABLE - set to NULL)
  CAST(NULL AS FLOAT64) as AssetsInMillions_Individuals,
  CAST(NULL AS FLOAT64) as AssetsInMillions_HNWIndividuals,
  CAST(NULL AS FLOAT64) as TotalAssets_SeparatelyManagedAccounts,
  CAST(NULL AS FLOAT64) as TotalAssets_PooledVehicles,
  CAST(NULL AS FLOAT64) as AssetsInMillions_MutualFunds,
  CAST(NULL AS FLOAT64) as AssetsInMillions_PrivateFunds,
  CAST(NULL AS FLOAT64) as AssetsInMillions_Equity_ExchangeTraded,
  
  -- Percent metrics (NOT AVAILABLE - set to NULL)
  CAST(NULL AS FLOAT64) as PercentClients_HNWIndividuals,
  CAST(NULL AS FLOAT64) as PercentClients_Individuals,
  CAST(NULL AS FLOAT64) as PercentAssets_HNWIndividuals,
  CAST(NULL AS FLOAT64) as PercentAssets_Individuals,
  CAST(NULL AS FLOAT64) as PercentAssets_MutualFunds,
  CAST(NULL AS FLOAT64) as PercentAssets_PrivateFunds,
  CAST(NULL AS FLOAT64) as PercentAssets_Equity_ExchangeTraded,
  
  -- Firm associations
  SAFE_CAST(NumberFirmAssociations AS INT64) as NumberFirmAssociations,
  SAFE_CAST(NumberRIAFirmAssociations AS INT64) as NumberRIAFirmAssociations,
  SAFE_CAST(Number_OfficeReps AS INT64) as Number_BranchAdvisors,
  
  -- Custodian AUM (NOT AVAILABLE - set to NULL)
  CAST(NULL AS FLOAT64) as CustodianAUM_Fidelity_NationalFinancial,
  CAST(NULL AS FLOAT64) as CustodianAUM_Pershing,
  CAST(NULL AS FLOAT64) as CustodianAUM_Schwab,
  CAST(NULL AS FLOAT64) as CustodianAUM_TDAmeritrade,
  
  -- Prior firm tenure (map PriorFirmN_NumberOfYears to Number_YearsPriorFirmN)
  SAFE_CAST(PriorFirm1_NumberOfYears AS FLOAT64) as Number_YearsPriorFirm1,
  SAFE_CAST(PriorFirm2_NumberOfYears AS FLOAT64) as Number_YearsPriorFirm2,
  SAFE_CAST(PriorFirm3_NumberOfYears AS FLOAT64) as Number_YearsPriorFirm3,
  SAFE_CAST(PriorFirm4_NumberOfYears AS FLOAT64) as Number_YearsPriorFirm4,
  
  -- Derived: Average tenure at prior firms
  SAFE_CAST(
    (COALESCE(PriorFirm1_NumberOfYears, 0) + 
     COALESCE(PriorFirm2_NumberOfYears, 0) + 
     COALESCE(PriorFirm3_NumberOfYears, 0) + 
     COALESCE(PriorFirm4_NumberOfYears, 0)) / 
    NULLIF(
      (CASE WHEN PriorFirm1_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN PriorFirm2_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN PriorFirm3_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN PriorFirm4_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END), 0
    ) AS FLOAT64
  ) as AverageTenureAtPriorFirms,
  
  -- Derived: Number of prior firms
  (CASE WHEN PriorFirm1_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
   CASE WHEN PriorFirm2_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
   CASE WHEN PriorFirm3_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END +
   CASE WHEN PriorFirm4_NumberOfYears IS NOT NULL THEN 1 ELSE 0 END) as NumberOfPriorFirms,
  
  -- String fields (keep for reference, but will be dropped as features)
  CAST(LicensesDesignations AS STRING) as Licenses,
  CAST(RegulatoryDisclosures AS STRING) as RegulatoryDisclosures,
  CAST(Education1 AS STRING) as Education,
  CAST(Gender AS STRING) as Gender,
  CAST(NULL AS STRING) as KnownNonAdvisor,
  CASE WHEN DuallyRegisteredBDRIARep = 'Yes' THEN 1 ELSE 0 END as DuallyRegisteredBDRIARep,
  CASE WHEN RIAFirmCRD = PrimaryRIAFirmCRD THEN 1 ELSE 0 END as IsPrimaryRIAFirm,
  
  -- Boolean flags from Yes/No fields (presence matters more than value)
  CASE WHEN BreakawayRep = 'Yes' THEN 1 ELSE 0 END as Is_BreakawayRep,
  CASE WHEN InsuranceLicensed = 'Yes' THEN 1 ELSE 0 END as Has_Insurance_License,
  CASE WHEN NonProducer = 'Yes' THEN 1 ELSE 0 END as Is_NonProducer,
  CASE WHEN IndependentContractor = 'Yes' THEN 1 ELSE 0 END as Is_IndependentContractor,
  CASE WHEN Owner = 'Yes' THEN 1 ELSE 0 END as Is_Owner,
  CASE WHEN Office_USPSCertified = 'Yes' THEN 1 ELSE 0 END as Office_USPS_Certified,
  CASE WHEN Home_USPSCertified = 'Yes' THEN 1 ELSE 0 END as Home_USPS_Certified,
  
  -- Custodian strings (NOT AVAILABLE - set to NULL)
  CAST(NULL AS STRING) as Custodian1,
  CAST(NULL AS STRING) as Custodian2,
  CAST(NULL AS STRING) as Custodian3,
  CAST(NULL AS STRING) as Custodian4,
  CAST(NULL AS STRING) as Custodian5,
  
  -- Location: Map Office_* to Branch_*
  CAST(Office_State AS STRING) as Branch_State,
  CAST(Home_State AS STRING) as Home_State,
  CAST(Office_City AS STRING) as Branch_City,
  CAST(Home_City AS STRING) as Home_City,
  CAST(Office_County AS STRING) as Branch_County,
  CAST(Home_County AS STRING) as Home_County,
  SAFE_CAST(Office_ZipCode AS FLOAT64) as Branch_ZipCode,
  SAFE_CAST(Home_ZipCode AS FLOAT64) as Home_ZipCode,
  SAFE_CAST(Office_Longitude AS FLOAT64) as Branch_Longitude,
  SAFE_CAST(Office_Latitude AS FLOAT64) as Branch_Latitude,
  SAFE_CAST(Home_Longitude AS FLOAT64) as Home_Longitude,
  SAFE_CAST(Home_Latitude AS FLOAT64) as Home_Latitude,
  CAST(Office_MetropolitanArea AS STRING) as Branch_MetropolitanArea,
  CAST(Home_MetropolitanArea AS STRING) as Home_MetropolitanArea,
  
  -- Distance
  SAFE_CAST(MilesToWork AS FLOAT64) as MilesToWork,
  
  -- Personal info (for later PII drop)
  CAST(FirstName AS STRING) as FirstName,
  CAST(LastName AS STRING) as LastName,
  CAST(Title AS STRING) as Title,
  CAST(RIAFirmName AS STRING) as RIAFirmName,
  
  -- Contact info
  CAST(Email_BusinessType AS STRING) as Email_BusinessType,
  CAST(Email_PersonalType AS STRING) as Email_PersonalType,
  CAST(SocialMedia_LinkedIn AS STRING) as SocialMedia_LinkedIn,
  CASE WHEN SocialMedia_LinkedIn IS NOT NULL THEN 1 ELSE 0 END as Has_LinkedIn,
  CAST(PersonalWebsite AS STRING) as PersonalWebpage,
  CAST(FirmWebsite AS STRING) as FirmWebsite,
  CAST(NULL AS STRING) as Brochure_Keywords,
  CAST(NULL AS STRING) as Notes,
  CAST(NULL AS STRING) as CustomKeywords,
  
  -- Derived: Boolean flags from Series columns
  CASE WHEN Series7_GeneralSecuritiesRepresentative = 'Yes' THEN 1 ELSE 0 END as Has_Series_7,
  CASE WHEN Series65_InvestmentAdviserRepresentative = 'Yes' THEN 1 ELSE 0 END as Has_Series_65,
  CASE WHEN Series66_CombinedUniformStateLawAndIARepresentative = 'Yes' THEN 1 ELSE 0 END as Has_Series_66,
  CASE WHEN Series24_GeneralSecuritiesPrincipal = 'Yes' THEN 1 ELSE 0 END as Has_Series_24,
  CASE WHEN Designations_CFP = 'Yes' THEN 1 ELSE 0 END as Has_CFP,
  CASE WHEN Designations_CFA = 'Yes' THEN 1 ELSE 0 END as Has_CFA,
  CASE WHEN Designations_CIMA = 'Yes' THEN 1 ELSE 0 END as Has_CIMA,
  CASE WHEN Designations_AIF = 'Yes' THEN 1 ELSE 0 END as Has_AIF,
  CASE WHEN RegulatoryDisclosures != 'No' THEN 1 ELSE 0 END as Has_Disclosure,
  
  -- Derived: Custodian relationship flags (NOT AVAILABLE - set to 0)
  CAST(0 AS INT64) as Has_Schwab_Relationship,
  CAST(0 AS INT64) as Has_Fidelity_Relationship,
  CAST(0 AS INT64) as Has_Pershing_Relationship,
  CAST(0 AS INT64) as Has_TDAmeritrade_Relationship,
  
  -- Additional metadata
  SAFE_CAST(Number_RegisteredStates AS INT64) as Number_RegisteredStates,
  
  -- Snapshot metadata: Use actual date from CSV filename
  DATE('2024-01-07') as snapshot_at
  
FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20240107_raw`;

