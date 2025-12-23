-- Create Hybrid Training Dataset with all 122 features

CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` AS

WITH

AllLeadsWithSnapshot AS (
    SELECT 
        sf.Id,
        sf.Stage_Entered_Contacting__c,
        sf.Stage_Entered_Call_Scheduled__c,
        drc.snapshot_as_of,
        CASE 
            WHEN DATE(sf.Stage_Entered_Contacting__c) >= drc.snapshot_as_of
            THEN 1 ELSE 0 
        END as is_eligible_for_mutable_features,
        
        -- Stable Features (always OK to use):
        drc.Branch_City,
        drc.Branch_County,
        drc.Branch_Latitude,
        drc.Branch_Longitude,
        drc.Branch_State,
        drc.Branch_ZipCode,
        drc.BreakawayRep,
        drc.Brochure_Keywords,
        drc.Custodian1,
        drc.Custodian2,
        drc.Custodian3,
        drc.Custodian4,
        drc.Custodian5,
        drc.CustomKeywords,
        drc.DateBecameRep_NumberOfYears,
        drc.DateOfHireAtCurrentFirm_NumberOfYears,
        drc.DuallyRegisteredBDRIARep,
        drc.Education,
        drc.Email_BusinessType,
        drc.Email_PersonalType,
        drc.FirmWebsite,
        drc.FirstName,
        drc.Gender,
        drc.Has_AIF,
        drc.Has_CFA,
        drc.Has_CFP,
        drc.Has_CIMA,
        drc.Has_Series_24,
        drc.Has_Series_65,
        drc.Has_Series_66,
        drc.Has_Series_7,
        drc.Home_City,
        drc.Home_County,
        drc.Home_Latitude,
        drc.Home_Longitude,
        drc.Home_MetropolitanArea,
        drc.Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN,
        drc.Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX,
        drc.Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA,
        drc.Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL,
        drc.Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ,
        drc.Home_State,
        drc.Home_ZipCode,
        drc.IsPrimaryRIAFirm,
        drc.KnownNonAdvisor,
        drc.LastName,
        drc.Licenses,
        drc.MilesToWork,
        drc.Notes,
        drc.Number_Of_Prior_Firms,
        drc.Number_YearsPriorFirm1,
        drc.Number_YearsPriorFirm2,
        drc.Number_YearsPriorFirm3,
        drc.Number_YearsPriorFirm4,
        drc.PersonalWebpage,
        drc.RIAFirmCRD,
        drc.RIAFirmName,
        drc.RegulatoryDisclosures,
        drc.SocialMedia_LinkedIn,
        drc.Title,
        drc.Total_Prior_Firm_Years,
        
        -- Mutable Features (will be NULLed for historical leads):
        drc.AUMGrowthRate_1Year,
        drc.AUMGrowthRate_5Year,
        drc.AUM_Per_BranchAdvisor,
        drc.AUM_Per_Client,
        drc.AUM_Per_IARep,
        drc.Accelerating_Growth,
        drc.AssetsInMillions_Equity_ExchangeTraded,
        drc.AssetsInMillions_HNWIndividuals,
        drc.AssetsInMillions_Individuals,
        drc.AssetsInMillions_MutualFunds,
        drc.AssetsInMillions_PrivateFunds,
        drc.Clients_per_BranchAdvisor,
        drc.Clients_per_IARep,
        drc.CustodianAUM_Fidelity_NationalFinancial,
        drc.CustodianAUM_Pershing,
        drc.CustodianAUM_Schwab,
        drc.CustodianAUM_TDAmeritrade,
        drc.Firm_Stability_Score,
        drc.Growth_Momentum,
        drc.HNW_Asset_Concentration,
        drc.HNW_Client_Ratio,
        drc.Has_Disclosure,
        drc.Has_ETF_Focus,
        drc.Has_Fidelity_Relationship,
        drc.Has_Mutual_Fund_Focus,
        drc.Has_Pershing_Relationship,
        drc.Has_Private_Funds,
        drc.Has_Scale,
        drc.Has_Schwab_Relationship,
        drc.Has_TDAmeritrade_Relationship,
        drc.Individual_Asset_Ratio,
        drc.Is_Boutique_Firm,
        drc.Is_Breakaway_Rep,
        drc.Is_Dually_Registered,
        drc.Is_Known_Non_Advisor,
        drc.Is_Large_Firm,
        drc.Is_New_To_Firm,
        drc.Is_Primary_RIA,
        drc.Is_Veteran_Advisor,
        drc.Local_Advisor,
        drc.Multi_Firm_Associations,
        drc.Multi_RIA_Relationships,
        drc.NumberClients_HNWIndividuals,
        drc.NumberClients_Individuals,
        drc.NumberClients_RetirementPlans,
        drc.NumberFirmAssociations,
        drc.NumberRIAFirmAssociations,
        drc.Number_BranchAdvisors,
        drc.Number_IAReps,
        drc.PercentAssets_Equity_ExchangeTraded,
        drc.PercentAssets_HNWIndividuals,
        drc.PercentAssets_Individuals,
        drc.PercentAssets_MutualFunds,
        drc.PercentAssets_PrivateFunds,
        drc.PercentClients_HNWIndividuals,
        drc.PercentClients_Individuals,
        drc.Positive_Growth_Trajectory,
        drc.Remote_Work_Indicator,
        drc.TotalAssetsInMillions,
        drc.TotalAssets_PooledVehicles,
        drc.TotalAssets_SeparatelyManagedAccounts
        
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
    LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc
        ON sf.FA_CRD__c = drc.RepCRD
    WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
),

LabelData AS (
    SELECT 
        s.*,
        CASE 
            WHEN s.Stage_Entered_Call_Scheduled__c IS NOT NULL 
            AND DATE(s.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(s.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
            THEN 1 
            ELSE 0 
        END as target_label,
        CASE 
            WHEN DATE(s.Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            THEN 1
            ELSE 0
        END as is_in_right_censored_window,
        DATE_DIFF(DATE(s.Stage_Entered_Call_Scheduled__c), DATE(s.Stage_Entered_Contacting__c), DAY) as days_to_conversion
    FROM AllLeadsWithSnapshot s
),

FinalDatasetCreation AS (
    SELECT 
        Id,
        Stage_Entered_Contacting__c,
        target_label,
        is_eligible_for_mutable_features,
        
        -- Temporal features (derived):
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c) = 1 THEN 7
            ELSE EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c) - 1
        END as Day_of_Contact,
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c) IN (1, 7) THEN 1
            ELSE 0 
        END as Is_Weekend_Contact,
        
        -- Stable Features (pass-through):
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
        DateBecameRep_NumberOfYears,
        DateOfHireAtCurrentFirm_NumberOfYears,
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
        KnownNonAdvisor,
        LastName,
        Licenses,
        MilesToWork,
        Notes,
        Number_Of_Prior_Firms,
        Number_YearsPriorFirm1,
        Number_YearsPriorFirm2,
        Number_YearsPriorFirm3,
        Number_YearsPriorFirm4,
        PersonalWebpage,
        RIAFirmCRD,
        RIAFirmName,
        RegulatoryDisclosures,
        SocialMedia_LinkedIn,
        Title,
        Total_Prior_Firm_Years,
        
        -- Mutable Features (with CASE WHEN):
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AUMGrowthRate_1Year 
            ELSE NULL 
        END as AUMGrowthRate_1Year,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AUMGrowthRate_5Year 
            ELSE NULL 
        END as AUMGrowthRate_5Year,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AUM_Per_BranchAdvisor 
            ELSE NULL 
        END as AUM_Per_BranchAdvisor,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AUM_Per_Client 
            ELSE NULL 
        END as AUM_Per_Client,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AUM_Per_IARep 
            ELSE NULL 
        END as AUM_Per_IARep,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Accelerating_Growth 
            ELSE NULL 
        END as Accelerating_Growth,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AssetsInMillions_Equity_ExchangeTraded 
            ELSE NULL 
        END as AssetsInMillions_Equity_ExchangeTraded,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AssetsInMillions_HNWIndividuals 
            ELSE NULL 
        END as AssetsInMillions_HNWIndividuals,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AssetsInMillions_Individuals 
            ELSE NULL 
        END as AssetsInMillions_Individuals,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AssetsInMillions_MutualFunds 
            ELSE NULL 
        END as AssetsInMillions_MutualFunds,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN AssetsInMillions_PrivateFunds 
            ELSE NULL 
        END as AssetsInMillions_PrivateFunds,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Clients_per_BranchAdvisor 
            ELSE NULL 
        END as Clients_per_BranchAdvisor,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Clients_per_IARep 
            ELSE NULL 
        END as Clients_per_IARep,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN CustodianAUM_Fidelity_NationalFinancial 
            ELSE NULL 
        END as CustodianAUM_Fidelity_NationalFinancial,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN CustodianAUM_Pershing 
            ELSE NULL 
        END as CustodianAUM_Pershing,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN CustodianAUM_Schwab 
            ELSE NULL 
        END as CustodianAUM_Schwab,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN CustodianAUM_TDAmeritrade 
            ELSE NULL 
        END as CustodianAUM_TDAmeritrade,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Firm_Stability_Score 
            ELSE NULL 
        END as Firm_Stability_Score,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Growth_Momentum 
            ELSE NULL 
        END as Growth_Momentum,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN HNW_Asset_Concentration 
            ELSE NULL 
        END as HNW_Asset_Concentration,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN HNW_Client_Ratio 
            ELSE NULL 
        END as HNW_Client_Ratio,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_Disclosure 
            ELSE NULL 
        END as Has_Disclosure,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_ETF_Focus 
            ELSE NULL 
        END as Has_ETF_Focus,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_Fidelity_Relationship 
            ELSE NULL 
        END as Has_Fidelity_Relationship,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_Mutual_Fund_Focus 
            ELSE NULL 
        END as Has_Mutual_Fund_Focus,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_Pershing_Relationship 
            ELSE NULL 
        END as Has_Pershing_Relationship,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_Private_Funds 
            ELSE NULL 
        END as Has_Private_Funds,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_Scale 
            ELSE NULL 
        END as Has_Scale,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_Schwab_Relationship 
            ELSE NULL 
        END as Has_Schwab_Relationship,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Has_TDAmeritrade_Relationship 
            ELSE NULL 
        END as Has_TDAmeritrade_Relationship,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Individual_Asset_Ratio 
            ELSE NULL 
        END as Individual_Asset_Ratio,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Is_Boutique_Firm 
            ELSE NULL 
        END as Is_Boutique_Firm,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Is_Breakaway_Rep 
            ELSE NULL 
        END as Is_Breakaway_Rep,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Is_Dually_Registered 
            ELSE NULL 
        END as Is_Dually_Registered,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Is_Known_Non_Advisor 
            ELSE NULL 
        END as Is_Known_Non_Advisor,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Is_Large_Firm 
            ELSE NULL 
        END as Is_Large_Firm,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Is_New_To_Firm 
            ELSE NULL 
        END as Is_New_To_Firm,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Is_Primary_RIA 
            ELSE NULL 
        END as Is_Primary_RIA,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Is_Veteran_Advisor 
            ELSE NULL 
        END as Is_Veteran_Advisor,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Local_Advisor 
            ELSE NULL 
        END as Local_Advisor,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Multi_Firm_Associations 
            ELSE NULL 
        END as Multi_Firm_Associations,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Multi_RIA_Relationships 
            ELSE NULL 
        END as Multi_RIA_Relationships,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN NumberClients_HNWIndividuals 
            ELSE NULL 
        END as NumberClients_HNWIndividuals,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN NumberClients_Individuals 
            ELSE NULL 
        END as NumberClients_Individuals,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN NumberClients_RetirementPlans 
            ELSE NULL 
        END as NumberClients_RetirementPlans,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN NumberFirmAssociations 
            ELSE NULL 
        END as NumberFirmAssociations,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN NumberRIAFirmAssociations 
            ELSE NULL 
        END as NumberRIAFirmAssociations,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Number_BranchAdvisors 
            ELSE NULL 
        END as Number_BranchAdvisors,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Number_IAReps 
            ELSE NULL 
        END as Number_IAReps,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN PercentAssets_Equity_ExchangeTraded 
            ELSE NULL 
        END as PercentAssets_Equity_ExchangeTraded,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN PercentAssets_HNWIndividuals 
            ELSE NULL 
        END as PercentAssets_HNWIndividuals,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN PercentAssets_Individuals 
            ELSE NULL 
        END as PercentAssets_Individuals,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN PercentAssets_MutualFunds 
            ELSE NULL 
        END as PercentAssets_MutualFunds,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN PercentAssets_PrivateFunds 
            ELSE NULL 
        END as PercentAssets_PrivateFunds,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN PercentClients_HNWIndividuals 
            ELSE NULL 
        END as PercentClients_HNWIndividuals,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN PercentClients_Individuals 
            ELSE NULL 
        END as PercentClients_Individuals,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Positive_Growth_Trajectory 
            ELSE NULL 
        END as Positive_Growth_Trajectory,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN Remote_Work_Indicator 
            ELSE NULL 
        END as Remote_Work_Indicator,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN TotalAssetsInMillions 
            ELSE NULL 
        END as TotalAssetsInMillions,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN TotalAssets_PooledVehicles 
            ELSE NULL 
        END as TotalAssets_PooledVehicles,
        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN TotalAssets_SeparatelyManagedAccounts 
            ELSE NULL 
        END as TotalAssets_SeparatelyManagedAccounts
        
    FROM LabelData
    WHERE is_in_right_censored_window = 0
      AND (days_to_conversion >= 0 OR days_to_conversion IS NULL)
)

SELECT * FROM FinalDatasetCreation;