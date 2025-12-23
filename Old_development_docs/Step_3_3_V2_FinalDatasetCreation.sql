-- FinalDatasetCreation CTE for V2 (3-part temporal logic)

FinalDatasetCreation AS (
    SELECT 
        ld.Id,
        ld.target_label,
        ld.is_in_right_censored_window,
        ld.days_to_conversion,
        
        -- Temporal features (derived):
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) = 1 THEN 7
            ELSE EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) - 1
        END as Day_of_Contact,
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) IN (1, 7) THEN 1
            ELSE 0 
        END as Is_Weekend_Contact,
        
        -- 1. Stable Features (Pass-through - never change)
        Branch_City,
        Branch_County,
        Branch_Latitude,
        Branch_Longitude,
        Branch_State,
        Branch_ZipCode,
        BreakawayRep,
        Brochure_Keywords,
        Custodian1,
        Custodian2,
        Custodian3,
        Custodian4,
        Custodian5,
        CustomKeywords,
        DuallyRegisteredBDRIARep,
        Education,
        Email_BusinessType,
        Email_PersonalType,
        FirmWebsite,
        FirstName,
        Gender,
        Has_AIF,
        Has_CFA,
        Has_CFP,
        Has_CIMA,
        Has_Series_24,
        Has_Series_65,
        Has_Series_66,
        Has_Series_7,
        Home_City,
        Home_County,
        Home_Latitude,
        Home_Longitude,
        Home_MetropolitanArea,
        Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN,
        Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX,
        Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA,
        Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL,
        Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ,
        Home_State,
        Home_ZipCode,
        IsPrimaryRIAFirm,
        Is_Known_Non_Advisor,
        KnownNonAdvisor,
        LastName,
        Licenses,
        MilesToWork,
        Multi_Firm_Associations,
        Multi_RIA_Relationships,
        Notes,
        NumberFirmAssociations,
        NumberRIAFirmAssociations,
        PersonalWebpage,
        RIAFirmCRD,
        RIAFirmName,
        RegulatoryDisclosures,
        SocialMedia_LinkedIn,
        Title,

        -- 2. Calculable Features (Re-calculate point-in-time value)
        -- Calculate years at contact time by subtracting years elapsed since snapshot
        drc.DateBecameRep_NumberOfYears - DATE_DIFF(CURRENT_DATE(), DATE(sf.Stage_Entered_Contacting__c), YEAR) as DateBecameRep_NumberOfYears,
        drc.DateOfHireAtCurrentFirm_NumberOfYears - DATE_DIFF(CURRENT_DATE(), DATE(sf.Stage_Entered_Contacting__c), YEAR) as DateOfHireAtCurrentFirm_NumberOfYears,
        drc.Number_Of_Prior_Firms,
        drc.Number_YearsPriorFirm1,
        drc.Number_YearsPriorFirm2,
        drc.Number_YearsPriorFirm3,
        drc.Number_YearsPriorFirm4,
        drc.Total_Prior_Firm_Years,

        -- 3. Mutable Features (NULLed for historical leads)
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AUMGrowthRate_1Year
            ELSE NULL
        END as AUMGrowthRate_1Year,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AUMGrowthRate_5Year
            ELSE NULL
        END as AUMGrowthRate_5Year,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AUM_Per_BranchAdvisor
            ELSE NULL
        END as AUM_Per_BranchAdvisor,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AUM_Per_Client
            ELSE NULL
        END as AUM_Per_Client,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AUM_Per_IARep
            ELSE NULL
        END as AUM_Per_IARep,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Accelerating_Growth
            ELSE NULL
        END as Accelerating_Growth,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AssetsInMillions_Equity_ExchangeTraded
            ELSE NULL
        END as AssetsInMillions_Equity_ExchangeTraded,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AssetsInMillions_HNWIndividuals
            ELSE NULL
        END as AssetsInMillions_HNWIndividuals,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AssetsInMillions_Individuals
            ELSE NULL
        END as AssetsInMillions_Individuals,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AssetsInMillions_MutualFunds
            ELSE NULL
        END as AssetsInMillions_MutualFunds,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.AssetsInMillions_PrivateFunds
            ELSE NULL
        END as AssetsInMillions_PrivateFunds,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Clients_per_BranchAdvisor
            ELSE NULL
        END as Clients_per_BranchAdvisor,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Clients_per_IARep
            ELSE NULL
        END as Clients_per_IARep,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.CustodianAUM_Fidelity_NationalFinancial
            ELSE NULL
        END as CustodianAUM_Fidelity_NationalFinancial,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.CustodianAUM_Pershing
            ELSE NULL
        END as CustodianAUM_Pershing,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.CustodianAUM_Schwab
            ELSE NULL
        END as CustodianAUM_Schwab,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.CustodianAUM_TDAmeritrade
            ELSE NULL
        END as CustodianAUM_TDAmeritrade,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Firm_Stability_Score
            ELSE NULL
        END as Firm_Stability_Score,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Growth_Momentum
            ELSE NULL
        END as Growth_Momentum,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.HNW_Asset_Concentration
            ELSE NULL
        END as HNW_Asset_Concentration,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.HNW_Client_Ratio
            ELSE NULL
        END as HNW_Client_Ratio,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_Disclosure
            ELSE NULL
        END as Has_Disclosure,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_ETF_Focus
            ELSE NULL
        END as Has_ETF_Focus,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_Fidelity_Relationship
            ELSE NULL
        END as Has_Fidelity_Relationship,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_Mutual_Fund_Focus
            ELSE NULL
        END as Has_Mutual_Fund_Focus,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_Pershing_Relationship
            ELSE NULL
        END as Has_Pershing_Relationship,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_Private_Funds
            ELSE NULL
        END as Has_Private_Funds,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_Scale
            ELSE NULL
        END as Has_Scale,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_Schwab_Relationship
            ELSE NULL
        END as Has_Schwab_Relationship,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Has_TDAmeritrade_Relationship
            ELSE NULL
        END as Has_TDAmeritrade_Relationship,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Individual_Asset_Ratio
            ELSE NULL
        END as Individual_Asset_Ratio,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Is_Boutique_Firm
            ELSE NULL
        END as Is_Boutique_Firm,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Is_Breakaway_Rep
            ELSE NULL
        END as Is_Breakaway_Rep,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Is_Dually_Registered
            ELSE NULL
        END as Is_Dually_Registered,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Is_Large_Firm
            ELSE NULL
        END as Is_Large_Firm,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Is_New_To_Firm
            ELSE NULL
        END as Is_New_To_Firm,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Is_Primary_RIA
            ELSE NULL
        END as Is_Primary_RIA,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Is_Veteran_Advisor
            ELSE NULL
        END as Is_Veteran_Advisor,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Local_Advisor
            ELSE NULL
        END as Local_Advisor,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.NumberClients_HNWIndividuals
            ELSE NULL
        END as NumberClients_HNWIndividuals,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.NumberClients_Individuals
            ELSE NULL
        END as NumberClients_Individuals,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.NumberClients_RetirementPlans
            ELSE NULL
        END as NumberClients_RetirementPlans,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Number_BranchAdvisors
            ELSE NULL
        END as Number_BranchAdvisors,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Number_IAReps
            ELSE NULL
        END as Number_IAReps,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.PercentAssets_Equity_ExchangeTraded
            ELSE NULL
        END as PercentAssets_Equity_ExchangeTraded,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.PercentAssets_HNWIndividuals
            ELSE NULL
        END as PercentAssets_HNWIndividuals,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.PercentAssets_Individuals
            ELSE NULL
        END as PercentAssets_Individuals,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.PercentAssets_MutualFunds
            ELSE NULL
        END as PercentAssets_MutualFunds,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.PercentAssets_PrivateFunds
            ELSE NULL
        END as PercentAssets_PrivateFunds,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.PercentClients_HNWIndividuals
            ELSE NULL
        END as PercentClients_HNWIndividuals,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.PercentClients_Individuals
            ELSE NULL
        END as PercentClients_Individuals,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Positive_Growth_Trajectory
            ELSE NULL
        END as Positive_Growth_Trajectory,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.Remote_Work_Indicator
            ELSE NULL
        END as Remote_Work_Indicator,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.TotalAssetsInMillions
            ELSE NULL
        END as TotalAssetsInMillions,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.TotalAssets_PooledVehicles
            ELSE NULL
        END as TotalAssets_PooledVehicles,
        CASE
            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.TotalAssets_SeparatelyManagedAccounts
            ELSE NULL
        END as TotalAssets_SeparatelyManagedAccounts,
        
    FROM LabelData ld
    JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc ON ld.FA_CRD__c = drc.RepCRD
    JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` sf ON ld.Id = sf.Id
        -- Note: is_eligible_for_mutable_features comes from ld (LabelData)
    WHERE ld.is_in_right_censored_window = 0
      AND (ld.days_to_conversion >= 0 OR ld.days_to_conversion IS NULL)
)
