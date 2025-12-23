# Feature Selection Report V1

**Generated:** 2025-11-03 16:35:26

## Pre-Filter Summary

- **Initial Features:** 132
- **Final Features:** 91
- **Removed:** 41

## Features Removed by Filter

### Removed by IV Filter (< 0.02)

- Branch_Latitude
- Branch_Longitude
- Complex_Registration
- CustodianAUM_Fidelity_NationalFinancial
- CustodianAUM_Pershing
- CustodianAUM_Schwab
- CustodianAUM_TDAmeritrade
- CustomKeywords
- DateBecameRep_NumberOfYears
- Day_of_Contact
- Growth_Acceleration
- Has_AIF
- Has_CFA
- Has_CFP
- Has_CIMA
- Has_Series_24
- Has_Series_65
- Has_Series_66
- Has_TDAmeritrade_Relationship
- Home_Latitude
- Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN
- Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX
- Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA
- Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL
- Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ
- Is_Known_Non_Advisor
- Is_Weekend_Contact
- Multi_Firm_Associations
- Multi_RIA_Relationships
- Notes
- NumberFirmAssociations
- NumberRIAFirmAssociations
- Number_YearsPriorFirm2
- Quality_Score

### Removed by VIF Filter (> 10.0)

- AUMGrowthRate_1Year
- AUM_Per_Client
- AUM_Per_IARep
- AUM_per_Client
- AUM_per_IARep
- AssetsInMillions_HNWIndividuals
- AssetsInMillions_Individuals
- AssetsInMillions_PrivateFunds
- Branch_Longitude
- Branch_ZipCode
- Complex_Registration
- Growth_Momentum
- HNW_Asset_Concentration
- Individual_Asset_Ratio
- Multi_RIA_Relationships
- NumberClients_HNWIndividuals
- NumberClients_Individuals
- NumberClients_RetirementPlans
- Number_IAReps
- PercentAssets_Individuals
- PercentAssets_PrivateFunds
- TotalAssetsInMillions
- TotalAssets_SeparatelyManagedAccounts

## Feature Importance (Top 20)

| feature                               |   mean_abs_shap |
|:--------------------------------------|----------------:|
| FirstName                             |     0.00839807  |
| Branch_City                           |     0.00716041  |
| SocialMedia_LinkedIn                  |     0.00693819  |
| LastName                              |     0.00576292  |
| Education                             |     0.00485559  |
| Licenses                              |     0.00454602  |
| Brochure_Keywords                     |     0.00272609  |
| Branch_County                         |     0.00271292  |
| RIAFirmCRD                            |     0.00241217  |
| DateOfHireAtCurrentFirm_NumberOfYears |     0.00230268  |
| Home_State                            |     0.00175993  |
| Title                                 |     0.00153704  |
| Home_City                             |     0.00125373  |
| Custodian1                            |     0.00114736  |
| Branch_State                          |     0.00114018  |
| Home_County                           |     0.00113683  |
| FirmWebsite                           |     0.000976486 |
| PersonalWebpage                       |     0.000551572 |
| Number_YearsPriorFirm2                |     0.000532121 |
| Home_MetropolitanArea                 |     0.000519763 |