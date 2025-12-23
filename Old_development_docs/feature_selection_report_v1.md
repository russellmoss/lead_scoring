# Feature Selection Report V1

**Generated:** 2025-11-03 13:54:39

## Pre-Filter Summary

- **Initial Features:** 124
- **Final Features:** 106
- **Removed:** 18

## Features Removed by Filter

### Removed by IV Filter (< 0.02)

- AUMGrowthRate_1Year
- AUMGrowthRate_5Year
- AUM_Per_BranchAdvisor
- AUM_Per_Client
- AUM_Per_IARep
- Accelerating_Growth
- AssetsInMillions_Equity_ExchangeTraded
- AssetsInMillions_HNWIndividuals
- AssetsInMillions_Individuals
- AssetsInMillions_MutualFunds
- AssetsInMillions_PrivateFunds
- Branch_Latitude
- Branch_Longitude
- Branch_ZipCode
- Clients_per_BranchAdvisor
- Clients_per_IARep
- CustodianAUM_Fidelity_NationalFinancial
- CustodianAUM_Pershing
- CustodianAUM_Schwab
- CustodianAUM_TDAmeritrade
- CustomKeywords
- DateBecameRep_NumberOfYears
- Day_of_Contact
- Firm_Stability_Score
- Growth_Momentum
- HNW_Asset_Concentration
- HNW_Client_Ratio
- Has_Disclosure
- Has_ETF_Focus
- Has_Fidelity_Relationship
- Has_Mutual_Fund_Focus
- Has_Pershing_Relationship
- Has_Private_Funds
- Has_Scale
- Has_Schwab_Relationship
- Has_Series_24
- Has_Series_66
- Has_TDAmeritrade_Relationship
- Home_MetropolitanArea
- Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN
- Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX
- Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA
- Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL
- Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ
- Individual_Asset_Ratio
- Is_Boutique_Firm
- Is_Breakaway_Rep
- Is_Dually_Registered
- Is_Known_Non_Advisor
- Is_Large_Firm
- Is_New_To_Firm
- Is_Primary_RIA
- Is_Veteran_Advisor
- Local_Advisor
- Multi_Firm_Associations
- Multi_RIA_Relationships
- Notes
- NumberClients_HNWIndividuals
- NumberClients_Individuals
- NumberClients_RetirementPlans
- NumberFirmAssociations
- NumberRIAFirmAssociations
- Number_BranchAdvisors
- Number_IAReps
- PercentAssets_Equity_ExchangeTraded
- PercentAssets_HNWIndividuals
- PercentAssets_Individuals
- PercentAssets_MutualFunds
- PercentAssets_PrivateFunds
- PercentClients_HNWIndividuals
- PercentClients_Individuals
- Positive_Growth_Trajectory
- Remote_Work_Indicator
- TotalAssetsInMillions
- TotalAssets_PooledVehicles
- TotalAssets_SeparatelyManagedAccounts

### Removed by VIF Filter (> 10.0)

- AUMGrowthRate_1Year
- AUM_Per_BranchAdvisor
- AssetsInMillions_Equity_ExchangeTraded
- AssetsInMillions_HNWIndividuals
- AssetsInMillions_Individuals
- AssetsInMillions_MutualFunds
- AssetsInMillions_PrivateFunds
- Clients_per_BranchAdvisor
- Clients_per_IARep
- CustodianAUM_Fidelity_NationalFinancial
- Growth_Momentum
- Has_Scale
- Individual_Asset_Ratio
- Is_Boutique_Firm
- Is_Large_Firm
- Is_Primary_RIA
- Multi_Firm_Associations
- Multi_RIA_Relationships
- NumberClients_HNWIndividuals
- NumberClients_Individuals
- NumberClients_RetirementPlans
- NumberFirmAssociations
- NumberRIAFirmAssociations
- Number_BranchAdvisors
- Number_IAReps
- PercentAssets_Individuals
- PercentAssets_PrivateFunds
- TotalAssetsInMillions
- TotalAssets_PooledVehicles
- TotalAssets_SeparatelyManagedAccounts

## Feature Importance (Top 20)

| feature                               |   mean_abs_shap |
|:--------------------------------------|----------------:|
| Branch_State                          |      0.0534497  |
| DateOfHireAtCurrentFirm_NumberOfYears |      0.0332651  |
| Custodian1                            |      0.0181909  |
| Branch_County                         |      0.0145804  |
| FirstName                             |      0.013039   |
| Branch_City                           |      0.0113411  |
| Education                             |      0.0097677  |
| Licenses                              |      0.00732452 |
| KnownNonAdvisor                       |      0.00688991 |
| LastName                              |      0.00567787 |
| SocialMedia_LinkedIn                  |      0.00541858 |
| Home_County                           |      0.00471715 |
| Brochure_Keywords                     |      0.00465156 |
| FirmWebsite                           |      0.00338281 |
| DateBecameRep_NumberOfYears           |      0.00321813 |
| RIAFirmCRD                            |      0.00276488 |
| Title                                 |      0.00271041 |
| Home_State                            |      0.00248586 |
| DuallyRegisteredBDRIARep              |      0.00217468 |
| Number_Of_Prior_Firms                 |      0.00192917 |