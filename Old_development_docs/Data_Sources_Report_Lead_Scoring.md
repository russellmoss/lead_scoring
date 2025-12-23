# Data Sources Report: Lead Scoring Model Training

**Generated:** November 5, 2025  
**Purpose:** Comprehensive documentation of all data sources available for lead scoring model training  
**Audience:** Data scientists, ML engineers, and LLMs building new lead scoring models

---

## Table of Contents

1. [Overview](#overview)
2. [Raw Discovery Data Snapshots](#raw-discovery-data-snapshots)
3. [Lead Object (Salesforce)](#lead-object-salesforce)
4. [V6 Training Dataset](#v6-training-dataset)
5. [Data Joining Strategy](#data-joining-strategy)
6. [Binary Data Transformations](#binary-data-transformations)
7. [Engineered Features](#engineered-features)
8. [Usage Examples](#usage-examples)

---

## Overview

The lead scoring system uses three primary data sources:

1. **Discovery Data Snapshots** (`savvy-gtm-analytics.LeadScoring.snapshot_reps_*_raw`): Historical snapshots of financial advisor profiles from Discovery Data, captured at 8 different time points
2. **Salesforce Lead Object** (`savvy-gtm-analytics.SavvyGTMData.Lead`): Real-time lead data from Salesforce CRM
3. **V6 Training Dataset** (`savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_20251104_2217`): Processed, point-in-time correct training dataset with engineered features

### Key Connection Point

The **CRD Number** (Central Registration Depository) is the primary key that connects all data sources:
- In Discovery Data: `RepCRD` (INTEGER)
- In Salesforce Lead: `FA_CRD__c` (STRING)
- Join: `CAST(RepCRD AS STRING) = FA_CRD__c`

---

## Raw Discovery Data Snapshots

### Available Tables

We maintain 8 historical snapshots of Discovery Data to support point-in-time feature engineering:

| Table Name | Snapshot Date | Rows | Size | Purpose |
|------------|---------------|------|------|---------|
| `snapshot_reps_20251005_raw` | October 5, 2025 | 494,396 | 906 MB | Most recent snapshot |
| `snapshot_reps_20250706_raw` | July 6, 2025 | 488,834 | 900 MB | Q3 2025 baseline |
| `snapshot_reps_20250406_raw` | April 6, 2025 | ~480K | ~890 MB | Q2 2025 baseline |
| `snapshot_reps_20250105_raw` | January 5, 2025 | ~470K | ~870 MB | Q1 2025 baseline |
| `snapshot_reps_20241006_raw` | October 6, 2024 | ~470K | ~860 MB | Q4 2024 baseline |
| `snapshot_reps_20240707_raw` | July 7, 2024 | ~470K | ~850 MB | Q3 2024 baseline |
| `snapshot_reps_20240331_raw` | March 31, 2024 | ~470K | ~840 MB | Q1 2024 baseline |
| `snapshot_reps_20240107_raw` | January 7, 2024 | 469,920 | 831 MB | Earliest snapshot |

### Schema Overview

Each snapshot table contains **~500 columns** representing comprehensive financial advisor profiles. The schema is consistent across all snapshots.

#### Core Identifiers

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `DiscoveryRepID` | INTEGER | Unique Discovery Data identifier | 12345678 |
| `RepCRD` | INTEGER | **CRD Number (join key)** | 123456 |
| `FullName` | STRING | Advisor full name | "John A. Smith" |
| `FirstName` | STRING | First name | "John" |
| `LastName` | STRING | Last name | "Smith" |
| `Title` | STRING | Professional title | "Financial Advisor" |
| `TitleCategories` | STRING | Categorized title types | "Advisor;PortfolioManager" |

#### Firm Information

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `RIAFirmCRD` | INTEGER | RIA Firm CRD number | 987654 |
| `RIAFirmName` | STRING | Firm name | "ABC Wealth Management" |
| `PrimaryRIAFirmCRD` | INTEGER | Primary RIA firm association | 987654 |
| `NumberRIAFirmAssociations` | INTEGER | Count of RIA firm associations | 2 |
| `PrimaryFirmCRD` | INTEGER | Primary firm CRD | 987654 |
| `NumberFirmAssociations` | INTEGER | Total firm associations | 3 |
| `FirmRegistrationType` | STRING | Type of firm registration | "RIA" |
| `RepRegistrationType` | STRING | Rep registration type | "IAR" |

#### Office Address (Branch Location)

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `Office_DiscoveryAddressID` | INTEGER | Discovery address ID | 123456 |
| `Office_BranchCRD` | FLOAT | Branch CRD number | 987654.0 |
| `Office_Address1` | STRING | Street address | "123 Main St" |
| `Office_City` | STRING | City | "New York" |
| `Office_State` | STRING | State (2-letter) | "NY" |
| `Office_ZipCode` | FLOAT | Zip code (5-digit) | 10001.0 |
| `Office_MetropolitanArea` | STRING | Metro area name | "New York-Newark-Jersey City" |
| `Office_County` | STRING | County name | "New York" |
| `Office_Longitude` | FLOAT | GPS longitude | -73.935242 |
| `Office_Latitude` | FLOAT | GPS latitude | 40.730610 |
| `Office_Phone` | STRING | Office phone | "(212) 555-1234" |
| `Office_USPSCertified` | STRING | USPS certification status | "Yes" |

#### Home Address

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `Home_DiscoveryAddressID` | FLOAT | Discovery address ID | 123456.0 |
| `Home_Address1` | STRING | Home street address | "456 Oak Ave" |
| `Home_City` | STRING | Home city | "Brooklyn" |
| `Home_State` | STRING | Home state (2-letter) | "NY" |
| `Home_ZipCode` | FLOAT | Home zip code | 11201.0 |
| `Home_MetropolitanArea` | STRING | Home metro area | "New York-Newark-Jersey City" |
| `Home_Longitude` | FLOAT | Home GPS longitude | -73.9442 |
| `Home_Latitude` | FLOAT | Home GPS latitude | 40.6782 |
| `MilesToWork` | FLOAT | Distance from home to office | 12.5 |
| `Home_Phone` | STRING | Home phone number | "(718) 555-5678" |

#### Contact Information

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `Email_BusinessType` | STRING | Business email address | "john.smith@firm.com" |
| `Email_BusinessTypeValidationSupported` | STRING | Email validation status | "Yes" |
| `Email_PersonalType` | STRING | Personal email | "john.smith.personal@gmail.com" |
| `PersonalWebsite` | STRING | Personal website URL | "https://johnsmith.com" |
| `FirmWebsite` | STRING | Firm website URL | "https://firm.com" |
| `SocialMedia_LinkedIn` | STRING | LinkedIn profile URL | "https://linkedin.com/in/johnsmith" |
| `SocialMedia_Facebook` | STRING | Facebook profile URL | "https://facebook.com/johnsmith" |
| `SocialMedia_Twitter` | STRING | Twitter handle | "@johnsmith" |

#### Professional Experience

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `DateBecameRep_YYYY_MM_DD` | STRING | Date became rep (YYYY-MM-DD) | "2010-05-15" |
| `DateBecameRep_YYYY_MM` | STRING | Date became rep (YYYY-MM) | "2010-05" |
| `DateBecameRep_Year` | FLOAT | Year became rep | 2010.0 |
| `DateBecameRep_NumberOfYears` | FLOAT | **Years of experience as rep** | 15.5 |
| `DateOfHireAtCurrentFirm_MM_DD_YYYY` | STRING | Hire date (MM/DD/YYYY) | "2015-03-20" |
| `DateOfHireAtCurrentFirm_YYYY_MM` | STRING | Hire date (YYYY-MM) | "2015-03" |
| `DateOfHireAtCurrentFirm_Year` | FLOAT | Year hired | 2015.0 |
| `DateOfHireAtCurrentFirm_NumberOfYears` | FLOAT | **Years at current firm** | 10.5 |

#### Prior Firm History

Each advisor can have up to 5 prior firm associations:

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `PriorFirm1_FirmCRD` | FLOAT | Prior firm 1 CRD | 111111.0 |
| `PriorFirm1_Name` | STRING | Prior firm 1 name | "Previous Firm Inc" |
| `PriorFirm1_StartDate` | STRING | Start date at prior firm 1 | "2005-01-15" |
| `PriorFirm1_EndDate` | STRING | End date at prior firm 1 | "2015-03-19" |
| `PriorFirm1_NumberOfYears` | FLOAT | Years at prior firm 1 | 10.2 |
| `PriorFirm2_FirmCRD` | FLOAT | Prior firm 2 CRD | 222222.0 |
| `PriorFirm2_Name` | STRING | Prior firm 2 name | "Another Firm LLC" |
| `PriorFirm2_NumberOfYears` | FLOAT | Years at prior firm 2 | 3.5 |
| ... (PriorFirm3, PriorFirm4, PriorFirm5 follow same pattern) |

#### Professional Characteristics (Binary Flags - String Format)

These fields are stored as **STRING** with values "Yes" or "No" in raw data, but converted to **INTEGER** (0/1) in V6:

| Field Name | Raw Type | Raw Values | V6 Type | V6 Values | Description |
|------------|----------|------------|---------|-----------|-------------|
| `BreakawayRep` | STRING | "Yes", "No" | INTEGER | 0, 1 | Advisor who left a broker-dealer to go independent |
| `DuallyRegisteredBDRIARep` | STRING | "Yes", "No" | INTEGER | 0, 1 | Registered with both BD and RIA |
| `DuallyLicensedBDRIARep` | STRING | "Yes", "No" | INTEGER | 0, 1 | Licensed with both BD and RIA |
| `InsuranceLicensed` | STRING | "Yes", "No" | INTEGER | 0, 1 | Has insurance license |
| `NonProducer` | STRING | "Yes", "No" | INTEGER | 0, 1 | Non-producing advisor (back office) |
| `IndependentContractor` | STRING | "Yes", "No" | INTEGER | 0, 1 | Independent contractor status |
| `Owner` | STRING | "Yes", "No" | INTEGER | 0, 1 | Firm owner |
| `InternationalAdvisor` | STRING | "Yes", "No" | INTEGER | 0, 1 | International advisor |

**Sample Distribution:**
- `BreakawayRep`: ~76% "Yes", ~24% "No"
- `DuallyRegisteredBDRIARep`: ~69% "Yes", ~31% "No"

#### Licenses and Designations (String Format)

Each license/designation has its own field stored as **STRING** (typically "Yes"/"No" or date):

| Category | Field Names | Raw Type | Description |
|----------|-------------|----------|-------------|
| **Series Licenses** | `Series3_NationalCommodityFutures`, `Series6_MutualFundsAndVariableAnnuities`, `Series7_GeneralSecuritiesRepresentative`, `Series24_GeneralSecuritiesPrincipal`, `Series63_UniformStateLaw`, `Series65_InvestmentAdviserRepresentative`, `Series66_CombinedUniformStateLawAndIARepresentative`, `Series79_InvestmentBankingRepresentative`, `Series82_PrivateSecuritiesRepresentative`, etc. | STRING | FINRA Series licenses (typically "Yes"/"No") |
| **Designations** | `Designations_CFA`, `Designations_CFP`, `Designations_CPA`, `Designations_ChFC`, `Designations_CLU`, `Designations_CIMA`, `Designations_CPWA`, etc. | STRING | Professional designations (typically "Yes"/"No") |
| **License Dates** | `Series7_GeneralSecuritiesRepresentative_Date`, `Series65_InvestmentAdviserRepresentative_Date`, etc. | STRING | Date license was obtained |

#### Title Categories (String Format)

Multiple binary fields indicating title categories:

| Field Name | Type | Values | Description |
|------------|------|--------|-------------|
| `Advisor` | STRING | "Yes", "No" | Standard advisor title |
| `PortfolioManager` | STRING | "Yes", "No" | Portfolio manager |
| `BranchManager` | STRING | "Yes", "No" | Branch manager |
| `Executive` | STRING | "Yes", "No" | Executive role |
| `ComplianceLegal` | STRING | "Yes", "No" | Compliance/legal role |
| `OperationsTechnology` | STRING | "Yes", "No" | Operations/tech role |
| ... (and 15+ more title categories) | | | |

#### Geographic and Registration

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `Number_RegisteredStates` | FLOAT | Count of states where registered | 5.0 |
| `RegisteredStates` | STRING | Comma-separated list of state codes | "NY,CA,FL,TX,NJ" |
| `Number_OfficeReps` | INTEGER | Number of reps in office | 15 |
| `Number_RegisteredStates_YE2015` through `Number_RegisteredStates_YE2019` | FLOAT | Historical state registration counts | 4.0, 5.0, etc. |
| `Number_RegisteredStates_Change1Year` | FLOAT | Change in registrations (1 year) | 1.0 |

#### Historical Change Metrics

Many fields have year-end snapshots and change calculations:

| Field Pattern | Example | Description |
|---------------|---------|-------------|
| `{Field}_YE{Year}` | `Number_RegisteredStates_YE2018` | Year-end value for specific year |
| `{Field}_ChangeYTD` | `Number_RegisteredStates_ChangeYTD` | Year-to-date change |
| `{Field}_Change1Year` | `Number_RegisteredStates_Change1Year` | 1-year change |
| `{Field}_Change3Years` | `Number_RegisteredStates_Change3Years` | 3-year change |
| `{Field}_%ChangeYTD` | `Number_RegisteredStates_%ChangeYTD` | Percentage change YTD |

#### Financial Metrics (Note: Most are NULL in current data)

**Important:** Financial metrics like AUM, client counts, and growth rates are **typically NULL** in the raw snapshots. These are populated through separate data enrichment processes.

| Field Name | Data Type | Description | Typical Value |
|------------|-----------|-------------|---------------|
| `TotalAssetsInMillions` | NULL | Total AUM (millions) | NULL |
| `NumberClients_Individuals` | NULL | Individual client count | NULL |
| `AUMGrowthRate_1Year` | NULL | 1-year AUM growth rate | NULL |

---

## Lead Object (Salesforce)

**Table:** `savvy-gtm-analytics.SavvyGTMData.Lead`  
**Rows:** ~81,637  
**Size:** ~60 MB  
**Type:** Salesforce CRM object

### Core Identifiers

| Field Name | Data Type | Description | Join Key |
|------------|-----------|-------------|----------|
| `Id` | STRING | Salesforce Lead ID (18-char) | Primary key |
| `FA_CRD__c` | STRING | **CRD Number (join key to Discovery)** | `CAST(RepCRD AS STRING) = FA_CRD__c` |
| `Name` | STRING | Full name (concatenated) | "John Smith" |
| `FirstName` | STRING | First name | "John" |
| `LastName` | STRING | Last name | "Smith" |
| `Email` | STRING | Primary email | "john@example.com" |
| `Phone` | STRING | Primary phone | "(212) 555-1234" |
| `MobilePhone` | STRING | Mobile phone | "(917) 555-5678" |

### Lead Status and Conversion Tracking

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `Status` | STRING | Lead status | "Open - Not Contacted" |
| `IsConverted` | BOOLEAN | Has lead been converted? | true |
| `ConvertedDate` | DATE | Date of conversion | 2025-10-15 |
| `ConvertedAccountId` | STRING | Converted account ID | "001xx000003DGbQAAW" |
| `ConvertedContactId` | STRING | Converted contact ID | "003xx000004DGbQAAW" |
| `ConvertedOpportunityId` | STRING | Converted opportunity ID | "006xx000003DGbQAAW" |

### Stage Tracking (Timestamps)

**Critical for Target Definition:**

| Field Name | Data Type | Description | Usage |
|------------|-----------|-------------|-------|
| `Stage_Entered_New__c` | TIMESTAMP | When lead entered "New" stage | Initial contact |
| `Stage_Entered_Contacting__c` | TIMESTAMP | **When lead entered "Contacting" (MQL qualification)** | **Used for temporal split** |
| `Stage_Entered_Call_Scheduled__c` | TIMESTAMP | When call was scheduled | Conversion milestone |
| `Stage_Entered_Closed__c` | TIMESTAMP | When lead was closed | Final stage |
| `Stage_Before_Closed_or_Conversion__c` | STRING | Last stage before closure | "Call Scheduled" |

**Target Definition:**
- Lead is considered "converted" if `Stage_Entered_Call_Scheduled__c` is not NULL within 30 days of `Stage_Entered_Contacting__c`
- `target_label = 1` if converted, `0` otherwise

### Custom Fields for Lead Scoring

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `Savvy_Lead_Score__c` | FLOAT | Current lead score (0-100) | 75.5 |
| `Years_as_a_Rep__c` | FLOAT | Years of experience | 15.5 |
| `Years_at_Firm__c` | FLOAT | Years at current firm | 10.5 |
| `Personal_AUM__c` | FLOAT | Personal AUM (millions) | 125.0 |
| `Estimated_Transferable_AUM__c` | FLOAT | Estimated transferable AUM | 50.0 |
| `Transferability_Probability__c` | STRING | Probability category | "High" |
| `Disposition__c` | STRING | Lead disposition | "Qualified" |
| `Last_Prospecting_Step__c` | STRING | Last prospecting action | "Email Sent" |

### Geographic Information

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `Street` | STRING | Street address | "123 Main St" |
| `City` | STRING | City | "New York" |
| `State` | STRING | State (2-letter) | "NY" |
| `PostalCode` | STRING | Zip code | "10001" |
| `Country` | STRING | Country | "United States" |
| `Latitude` | FLOAT | GPS latitude | 40.730610 |
| `Longitude` | FLOAT | GPS longitude | -73.935242 |

### Lead Source and Marketing

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `LeadSource` | STRING | Source of lead | "Website" |
| `CampaignId` | STRING | Campaign ID | "701xx000000DGbQAAW" |
| `utm_source__c` | STRING | UTM source parameter | "google" |
| `utm_medium__c` | STRING | UTM medium | "cpc" |
| `utm_campaign__c` | STRING | UTM campaign | "summer_promo" |
| `Marketing_Cohort_Name__c` | STRING | Marketing cohort | "Q4_2025_Website" |

### Timestamps

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `CreatedDate` | TIMESTAMP | When lead was created |
| `LastModifiedDate` | TIMESTAMP | Last modification time |
| `LastActivityDate` | DATE | Last activity date |
| `Stage_Entered_Replied__c` | TIMESTAMP | When lead replied |

---

## V6 Training Dataset

**Table:** `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_20251104_2217`  
**Rows:** 41,942  
**Columns:** 162  
**Size:** ~27 MB  
**Created:** November 4, 2025, 10:17 PM

### Purpose

The V6 dataset is a **point-in-time correct** training dataset that:
1. Uses 8 historical Discovery Data snapshots to ensure no data leakage
2. Joins leads with Discovery Data at the time of contact
3. Includes engineered features
4. Converts string Yes/No fields to binary 0/1
5. Includes firm-level aggregations
6. Contains target labels for conversion prediction

### Key Identifiers

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `Id` | STRING | Salesforce Lead ID |
| `FA_CRD__c` | STRING | CRD Number (join key) |
| `RIAFirmCRD` | STRING | RIA Firm CRD |
| `target_label` | INTEGER | **Target: 1 = converted, 0 = not converted** |
| `Stage_Entered_Contacting__c` | TIMESTAMP | When lead entered contacting stage |
| `Stage_Entered_Call_Scheduled__c` | TIMESTAMP | When call was scheduled (conversion) |
| `rep_snapshot_at` | DATE | Which snapshot date was used |
| `firm_snapshot_at` | DATE | Which firm snapshot date was used |

### Financial Metrics (Point-in-Time)

| Field Name | Data Type | Description | Note |
|------------|-----------|-------------|------|
| `TotalAssetsInMillions` | FLOAT | Total AUM (millions) | NULL if not available |
| `NumberClients_Individuals` | INTEGER | Individual client count | NULL if not available |
| `NumberClients_HNWIndividuals` | INTEGER | HNW client count | NULL if not available |
| `AUMGrowthRate_1Year` | FLOAT | 1-year AUM growth rate | NULL if not available |
| `AUMGrowthRate_5Year` | FLOAT | 5-year AUM growth rate | NULL if not available |

### Professional Characteristics (Binary - INTEGER)

All Yes/No fields from Discovery Data are converted to **INTEGER (0/1)**:

| Field Name | V6 Type | Values | Description |
|------------|---------|--------|-------------|
| `DuallyRegisteredBDRIARep` | INTEGER | 0, 1 | Dually registered BD/RIA |
| `Has_Series_7` | INTEGER | 0, 1 | Has Series 7 license |
| `Has_Series_65` | INTEGER | 0, 1 | Has Series 65 license |
| `Has_Series_66` | INTEGER | 0, 1 | Has Series 66 license |
| `Has_Series_24` | INTEGER | 0, 1 | Has Series 24 license |
| `Has_CFP` | INTEGER | 0, 1 | Has CFP designation |
| `Has_CFA` | INTEGER | 0, 1 | Has CFA designation |
| `Has_CIMA` | INTEGER | 0, 1 | Has CIMA designation |
| `Has_AIF` | INTEGER | 0, 1 | Has AIF designation |
| `Has_Disclosure` | INTEGER | 0, 1 | Has regulatory disclosure |
| `Is_BreakawayRep` | INTEGER | 0, 1 | Is breakaway rep |
| `Has_Insurance_License` | INTEGER | 0, 1 | Has insurance license |
| `Is_NonProducer` | INTEGER | 0, 1 | Is non-producer |
| `Is_IndependentContractor` | INTEGER | 0, 1 | Is independent contractor |
| `Is_Owner` | INTEGER | 0, 1 | Is firm owner |
| `Office_USPS_Certified` | INTEGER | 0, 1 | Office address USPS certified |
| `Home_USPS_Certified` | INTEGER | 0, 1 | Home address USPS certified |

### Custodian Relationships (Binary - INTEGER)

| Field Name | V6 Type | Values | Description |
|------------|---------|--------|-------------|
| `Has_Schwab_Relationship` | INTEGER | 0, 1 | Has Schwab custodian relationship |
| `Has_Fidelity_Relationship` | INTEGER | 0, 1 | Has Fidelity custodian relationship |
| `Has_Pershing_Relationship` | INTEGER | 0, 1 | Has Pershing custodian relationship |
| `Has_TDAmeritrade_Relationship` | INTEGER | 0, 1 | Has TD Ameritrade relationship |
| `CustodianAUM_Schwab` | FLOAT | Numeric | Schwab AUM (millions) |
| `CustodianAUM_Fidelity_NationalFinancial` | FLOAT | Numeric | Fidelity AUM (millions) |
| `CustodianAUM_Pershing` | FLOAT | Numeric | Pershing AUM (millions) |

### Experience Metrics (Numeric)

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `DateBecameRep_NumberOfYears` | FLOAT | Years of experience as rep |
| `DateOfHireAtCurrentFirm_NumberOfYears` | FLOAT | Years at current firm |
| `Number_YearsPriorFirm1` | FLOAT | Years at prior firm 1 |
| `Number_YearsPriorFirm2` | FLOAT | Years at prior firm 2 |
| `Number_YearsPriorFirm3` | FLOAT | Years at prior firm 3 |
| `Number_YearsPriorFirm4` | FLOAT | Years at prior firm 4 |
| `AverageTenureAtPriorFirms` | FLOAT | Average tenure at prior firms |
| `NumberOfPriorFirms` | INTEGER | Count of prior firms |

### Firm Associations

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `NumberFirmAssociations` | INTEGER | Total firm associations |
| `NumberRIAFirmAssociations` | INTEGER | RIA firm associations |
| `IsPrimaryRIAFirm` | INTEGER | Is primary RIA firm (0/1) |

### Geographic Features

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `Home_State` | STRING | Home state (2-letter code) |
| `Branch_State` | STRING | Branch/office state (2-letter code) |
| `Home_MetropolitanArea` | STRING | Home metro area name |
| `Number_RegisteredStates` | INTEGER | Count of registered states |
| `MilesToWork` | FLOAT | Distance from home to office |

### Firm-Level Aggregations

These features aggregate data across all reps in the firm:

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `total_reps` | INTEGER | Total reps in firm |
| `total_firm_aum_millions` | FLOAT | Total firm AUM (millions) |
| `total_firm_clients` | INTEGER | Total firm clients |
| `total_firm_hnw_clients` | INTEGER | Total firm HNW clients |
| `avg_clients_per_rep` | FLOAT | Average clients per rep |
| `aum_per_rep` | FLOAT | Average AUM per rep |
| `avg_firm_growth_1y` | FLOAT | Average firm 1-year growth |
| `avg_firm_growth_5y` | FLOAT | Average firm 5-year growth |
| `pct_reps_with_cfp` | FLOAT | Percentage of reps with CFP |
| `pct_reps_with_disclosure` | FLOAT | Percentage of reps with disclosure |
| `firm_size_tier` | STRING | Firm size category ("Small", "Medium", "Large") |
| `multi_state_firm` | INTEGER | Firm operates in multiple states (0/1) |
| `national_firm` | INTEGER | National firm (0/1) |

---

## Data Joining Strategy

### Primary Join: Discovery Data → Lead Object

The connection between Discovery Data and Salesforce Lead is made via the **CRD Number**:

```sql
-- Join Discovery Data to Lead
SELECT 
    l.Id,
    l.FA_CRD__c,
    l.Stage_Entered_Contacting__c,
    d.RepCRD,
    d.FullName,
    d.RIAFirmName,
    -- ... other Discovery fields
FROM 
    `savvy-gtm-analytics.SavvyGTMData.Lead` l
INNER JOIN 
    `savvy-gtm-analytics.LeadScoring.snapshot_reps_20251005_raw` d
ON 
    CAST(d.RepCRD AS STRING) = l.FA_CRD__c
WHERE 
    l.FA_CRD__c IS NOT NULL
    AND l.Stage_Entered_Contacting__c IS NOT NULL
```

### Point-in-Time Join (V6 Approach)

The V6 dataset uses **point-in-time** joins to prevent data leakage:

1. **Identify contact date**: Use `Stage_Entered_Contacting__c` from Lead
2. **Select appropriate snapshot**: Choose the snapshot that was current at the time of contact
3. **Join logic**: 
   ```sql
   CASE 
       WHEN contact_date >= '2025-10-05' THEN 'snapshot_reps_20251005_raw'
       WHEN contact_date >= '2025-07-06' THEN 'snapshot_reps_20250706_raw'
       WHEN contact_date >= '2025-04-06' THEN 'snapshot_reps_20250406_raw'
       -- ... etc
       ELSE 'snapshot_reps_20240107_raw'
   END
   ```

4. **Join on CRD**: `CAST(snapshot.RepCRD AS STRING) = Lead.FA_CRD__c`

### Example: Building Training Dataset

```sql
WITH lead_contacts AS (
    SELECT 
        Id,
        FA_CRD__c,
        Stage_Entered_Contacting__c,
        Stage_Entered_Call_Scheduled__c,
        -- Target: converted within 30 days?
        CASE 
            WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
                AND DATE_DIFF(DATE(Stage_Entered_Call_Scheduled__c), DATE(Stage_Entered_Contacting__c), DAY) <= 30
            THEN 1 
            ELSE 0 
        END as target_label
    FROM 
        `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE 
        FA_CRD__c IS NOT NULL
        AND Stage_Entered_Contacting__c IS NOT NULL
),
point_in_time_snapshots AS (
    SELECT 
        lc.*,
        -- Select snapshot based on contact date
        CASE 
            WHEN DATE(lc.Stage_Entered_Contacting__c) >= '2025-10-05' THEN s1.RepCRD
            WHEN DATE(lc.Stage_Entered_Contacting__c) >= '2025-07-06' THEN s2.RepCRD
            -- ... etc
        END as RepCRD_at_contact
    FROM 
        lead_contacts lc
    LEFT JOIN 
        `savvy-gtm-analytics.LeadScoring.snapshot_reps_20251005_raw` s1
    ON 
        CAST(s1.RepCRD AS STRING) = lc.FA_CRD__c
        AND DATE(lc.Stage_Entered_Contacting__c) >= '2025-10-05'
    -- ... additional snapshot joins
)
SELECT * FROM point_in_time_snapshots
```

---

## Binary Data Transformations

### Transformation Logic

In the raw Discovery Data snapshots, many fields are stored as **STRING** with values "Yes" or "No". For model training, these are converted to **INTEGER** binary flags (0/1).

### Transformation Pattern

```sql
-- Example: Converting BreakawayRep from STRING to INTEGER
CASE 
    WHEN BreakawayRep = 'Yes' THEN 1
    WHEN BreakawayRep = 'No' THEN 0
    ELSE 0  -- NULL or other values default to 0
END as Is_BreakawayRep
```

### Fields Converted in V6

| Raw Field Name | Raw Type | Raw Values | V6 Field Name | V6 Type | V6 Values |
|----------------|----------|------------|---------------|---------|-----------|
| `BreakawayRep` | STRING | "Yes", "No" | `Is_BreakawayRep` | INTEGER | 0, 1 |
| `DuallyRegisteredBDRIARep` | STRING | "Yes", "No" | `DuallyRegisteredBDRIARep` | INTEGER | 0, 1 |
| `NonProducer` | STRING | "Yes", "No" | `Is_NonProducer` | INTEGER | 0, 1 |
| `IndependentContractor` | STRING | "Yes", "No" | `Is_IndependentContractor` | INTEGER | 0, 1 |
| `Owner` | STRING | "Yes", "No" | `Is_Owner` | INTEGER | 0, 1 |
| `Series7_GeneralSecuritiesRepresentative` | STRING | "Yes", "No" | `Has_Series_7` | INTEGER | 0, 1 |
| `Series65_InvestmentAdviserRepresentative` | STRING | "Yes", "No" | `Has_Series_65` | INTEGER | 0, 1 |
| `Series66_CombinedUniformStateLawAndIARepresentative` | STRING | "Yes", "No" | `Has_Series_66` | INTEGER | 0, 1 |
| `Series24_GeneralSecuritiesPrincipal` | STRING | "Yes", "No" | `Has_Series_24` | INTEGER | 0, 1 |
| `Designations_CFP` | STRING | "Yes", "No" | `Has_CFP` | INTEGER | 0, 1 |
| `Designations_CFA` | STRING | "Yes", "No" | `Has_CFA` | INTEGER | 0, 1 |
| `Designations_CIMA` | STRING | "Yes", "No" | `Has_CIMA` | INTEGER | 0, 1 |
| `Designations_AIF` | STRING | "Yes", "No" | `Has_AIF` | INTEGER | 0, 1 |
| `RegulatoryDisclosures` | STRING | "Yes", "No" | `Has_Disclosure` | INTEGER | 0, 1 |
| `InsuranceLicensed` | STRING | "Yes", "No" | `Has_Insurance_License` | INTEGER | 0, 1 |
| `Office_USPSCertified` | STRING | "Yes", "No" | `Office_USPS_Certified` | INTEGER | 0, 1 |
| `Home_USPSCertified` | STRING | "Yes", "No" | `Home_USPS_Certified` | INTEGER | 0, 1 |

### License/Designation Conversion Pattern

For licenses and designations, the conversion checks if the field is not NULL and not empty:

```sql
-- Example: Series 7 license
CASE 
    WHEN Series7_GeneralSecuritiesRepresentative = 'Yes' THEN 1
    WHEN Series7_GeneralSecuritiesRepresentative IS NOT NULL 
        AND Series7_GeneralSecuritiesRepresentative != '' 
        AND Series7_GeneralSecuritiesRepresentative != 'No' 
    THEN 1
    ELSE 0
END as Has_Series_7
```

### Custodian Relationship Conversion

Custodian relationships are derived from AUM fields:

```sql
-- Example: Schwab relationship
CASE 
    WHEN CustodianAUM_Schwab IS NOT NULL 
        AND CustodianAUM_Schwab > 0 
    THEN 1 
    ELSE 0 
END as Has_Schwab_Relationship
```

---

## Engineered Features

The V6 dataset includes numerous engineered features created from raw Discovery Data fields. These are organized into several categories:

### 1. Career Stage Features

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `is_veteran_advisor` | INTEGER | Veteran advisor (20+ years) | `DateBecameRep_NumberOfYears >= 20 ? 1 : 0` |
| `is_new_to_firm` | INTEGER | New to current firm (< 1 year) | `DateOfHireAtCurrentFirm_NumberOfYears < 1 ? 1 : 0` |
| `high_turnover_flag` | INTEGER | High job turnover indicator | `AverageTenureAtPriorFirms < 3 AND NumberOfPriorFirms >= 2 ? 1 : 0` |
| `avg_prior_firm_tenure_lt3` | INTEGER | Average prior tenure < 3 years | `AverageTenureAtPriorFirms < 3 ? 1 : 0` |

### 2. Firm Relationship Features

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `multi_ria_relationships` | INTEGER | Multiple RIA relationships | `NumberRIAFirmAssociations > 1 ? 1 : 0` |
| `complex_registration` | INTEGER | Complex registration (multiple states) | `Number_RegisteredStates > 3 ? 1 : 0` |
| `multi_state_registered` | INTEGER | Registered in multiple states | `Number_RegisteredStates > 1 ? 1 : 0` |

### 3. Firm Stability Features

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `Firm_Stability_Score` | FLOAT | Firm stability ratio | `DateOfHireAtCurrentFirm_NumberOfYears / DateBecameRep_NumberOfYears` |
| `remote_work_indicator` | INTEGER | Works remotely (home != office state) | `Home_State != Branch_State ? 1 : 0` |
| `local_advisor` | INTEGER | Local advisor (home == office state) | `Home_State = Branch_State ? 1 : 0` |
| `branch_vs_home_mismatch` | INTEGER | Home/office mismatch | `Home_State != Branch_State ? 1 : 0` |

### 4. License and Designation Aggregates

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `license_count` | INTEGER | Total number of licenses | `Has_Series_7 + Has_Series_65 + Has_Series_66 + Has_Series_24 + ...` |
| `designation_count` | INTEGER | Total number of designations | `Has_CFP + Has_CFA + Has_CIMA + Has_AIF + ...` |

### 5. Financial Efficiency Metrics

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `AUM_per_Client` | FLOAT | AUM per client (millions) | `TotalAssetsInMillions / NumberClients_Individuals` |
| `AUM_per_IARep` | FLOAT | AUM per IAR rep | `TotalAssetsInMillions / Number_IAReps` |
| `Clients_per_IARep` | FLOAT | Clients per IAR rep | `NumberClients_Individuals / Number_IAReps` |
| `HNW_Client_Ratio` | FLOAT | HNW client concentration | `NumberClients_HNWIndividuals / NumberClients_Individuals` |
| `HNW_Asset_Concentration` | FLOAT | HNW asset concentration | Calculated from HNW assets / total assets |

### 6. Growth Indicators

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `Positive_Growth_Trajectory` | INTEGER | Positive 1-year growth | `AUMGrowthRate_1Year > 0 ? 1 : 0` |
| `Accelerating_Growth` | INTEGER | Accelerating growth (5yr > 1yr) | `AUMGrowthRate_5Year > AUMGrowthRate_1Year ? 1 : 0` |

### 7. Interaction Features

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `is_new_to_firm_x_has_series65` | INTEGER | New to firm AND has Series 65 | `is_new_to_firm * Has_Series_65` |
| `veteran_x_cfp` | INTEGER | Veteran advisor AND has CFP | `is_veteran_advisor * Has_CFP` |

### 8. Data Quality Flags

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `doh_current_years_is_missing` | INTEGER | Missing date of hire | `DateOfHireAtCurrentFirm_NumberOfYears IS NULL ? 1 : 0` |
| `became_rep_years_is_missing` | INTEGER | Missing became rep date | `DateBecameRep_NumberOfYears IS NULL ? 1 : 0` |
| `missing_feature_count` | INTEGER | Count of missing features | Sum of all missing flags |
| `email_business_type_flag` | INTEGER | Has business email | `Email_BusinessType IS NOT NULL ? 1 : 0` |
| `email_personal_type_flag` | INTEGER | Has personal email | `Email_PersonalType IS NOT NULL ? 1 : 0` |
| `has_linkedin` | INTEGER | Has LinkedIn profile | `SocialMedia_LinkedIn IS NOT NULL ? 1 : 0` |

### 9. Geographic Features

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `Home_Zip_3Digit` | STRING | 3-digit zip code prefix | First 3 digits of `Home_ZipCode` |
| `firm_rep_count_bin` | STRING | Firm size bin | `CASE WHEN total_reps < 10 THEN 'Small' WHEN total_reps < 50 THEN 'Medium' ELSE 'Large' END` |

### 10. Firm-Level Features

| Feature Name | Type | Description | Logic |
|--------------|------|-------------|-------|
| `multi_state_firm` | INTEGER | Firm operates in multiple states | Aggregated from all reps |
| `national_firm` | INTEGER | National firm (many states) | `Number_RegisteredStates > 10 ? 1 : 0` (aggregated) |

---

## Usage Examples

### Example 1: Load V6 Training Dataset

```python
from google.cloud import bigquery

client = bigquery.Client(project='savvy-gtm-analytics')

query = """
SELECT 
    * EXCEPT(days_to_conversion)  -- Exclude leakage feature
FROM 
    `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_20251104_2217`
WHERE 
    FA_CRD__c IS NOT NULL
    AND target_label IS NOT NULL
ORDER BY 
    Stage_Entered_Contacting__c
"""

df = client.query(query).to_dataframe()
```

### Example 2: Join Raw Discovery Data to Lead

```python
query = """
SELECT 
    l.Id,
    l.FA_CRD__c,
    l.Stage_Entered_Contacting__c,
    d.RepCRD,
    d.FullName,
    d.RIAFirmName,
    d.DateBecameRep_NumberOfYears,
    d.DateOfHireAtCurrentFirm_NumberOfYears,
    d.BreakawayRep,  -- String: "Yes" or "No"
    d.DuallyRegisteredBDRIARep,  -- String: "Yes" or "No"
    d.Series7_GeneralSecuritiesRepresentative,  -- String: "Yes" or "No"
    d.NumberRIAFirmAssociations,
    d.Number_RegisteredStates
FROM 
    `savvy-gtm-analytics.SavvyGTMData.Lead` l
INNER JOIN 
    `savvy-gtm-analytics.LeadScoring.snapshot_reps_20251005_raw` d
ON 
    CAST(d.RepCRD AS STRING) = l.FA_CRD__c
WHERE 
    l.FA_CRD__c IS NOT NULL
    AND l.Stage_Entered_Contacting__c >= '2025-10-05'
"""

df = client.query(query).to_dataframe()
```

### Example 3: Convert String Yes/No to Binary

```python
# After loading raw Discovery Data
binary_fields = [
    'BreakawayRep',
    'DuallyRegisteredBDRIARep',
    'Series7_GeneralSecuritiesRepresentative',
    'Series65_InvestmentAdviserRepresentative',
    # ... etc
]

for field in binary_fields:
    df[f'Has_{field}'] = (df[field] == 'Yes').astype(int)
    df = df.drop(columns=[field])  # Remove original string field
```

### Example 4: Point-in-Time Join (V6 Logic)

```python
# Determine which snapshot to use based on contact date
def get_snapshot_table(contact_date):
    snapshots = [
        ('2025-10-05', 'snapshot_reps_20251005_raw'),
        ('2025-07-06', 'snapshot_reps_20250706_raw'),
        ('2025-04-06', 'snapshot_reps_20250406_raw'),
        ('2025-01-05', 'snapshot_reps_20250105_raw'),
        ('2024-10-06', 'snapshot_reps_20241006_raw'),
        ('2024-07-07', 'snapshot_reps_20240707_raw'),
        ('2024-03-31', 'snapshot_reps_20240331_raw'),
        ('2024-01-07', 'snapshot_reps_20240107_raw'),
    ]
    
    for snapshot_date, table_name in snapshots:
        if contact_date >= snapshot_date:
            return table_name
    
    return 'snapshot_reps_20240107_raw'  # Default to earliest

# Use in query
query = f"""
SELECT 
    l.Id,
    l.FA_CRD__c,
    CASE 
        WHEN DATE(l.Stage_Entered_Contacting__c) >= '2025-10-05' 
            THEN (SELECT RepCRD FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20251005_raw` WHERE CAST(RepCRD AS STRING) = l.FA_CRD__c)
        WHEN DATE(l.Stage_Entered_Contacting__c) >= '2025-07-06' 
            THEN (SELECT RepCRD FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_20250706_raw` WHERE CAST(RepCRD AS STRING) = l.FA_CRD__c)
        -- ... etc
    END as RepCRD_at_contact
FROM 
    `savvy-gtm-analytics.SavvyGTMData.Lead` l
"""
```

### Example 5: Create Engineered Features

```python
# After joining Discovery Data to Lead
df['is_veteran_advisor'] = (df['DateBecameRep_NumberOfYears'] >= 20).astype(int)
df['is_new_to_firm'] = (df['DateOfHireAtCurrentFirm_NumberOfYears'] < 1).astype(int)
df['multi_ria_relationships'] = (df['NumberRIAFirmAssociations'] > 1).astype(int)
df['license_count'] = (
    df['Has_Series_7'] + 
    df['Has_Series_65'] + 
    df['Has_Series_66'] + 
    df['Has_Series_24']
).fillna(0).astype(int)

# Firm stability score
df['Firm_Stability_Score'] = (
    df['DateOfHireAtCurrentFirm_NumberOfYears'] / 
    df['DateBecameRep_NumberOfYears']
).fillna(0)

# AUM per client (if available)
df['AUM_per_Client'] = (
    df['TotalAssetsInMillions'] / 
    df['NumberClients_Individuals']
).fillna(0)
```

---

## Key Takeaways for Model Builders

1. **Always use point-in-time joins** - Don't use the latest snapshot for historical leads
2. **Convert Yes/No strings to 0/1** - All binary flags should be INTEGER type
3. **Handle NULL financial metrics** - Most AUM/client data is NULL; use 0 or flag missingness
4. **Use V6 as reference** - The V6 dataset shows the correct transformations and feature engineering
5. **Avoid data leakage** - Never use `days_to_conversion` or post-conversion fields as features
6. **Join on CRD** - `CAST(RepCRD AS STRING) = FA_CRD__c` is the primary join key
7. **Temporal split** - Always split train/test by `Stage_Entered_Contacting__c` date, not randomly

---

## Appendix: Complete Field List

### Discovery Data Snapshots: ~500 Fields

**Core Fields (50+):**
- Identifiers: DiscoveryRepID, RepCRD, FullName, FirstName, LastName, Title
- Firm: RIAFirmCRD, RIAFirmName, PrimaryRIAFirmCRD, NumberRIAFirmAssociations
- Office Address: Office_Address1, Office_City, Office_State, Office_ZipCode, Office_MetropolitanArea
- Home Address: Home_Address1, Home_City, Home_State, Home_ZipCode, Home_MetropolitanArea
- Experience: DateBecameRep_*, DateOfHireAtCurrentFirm_*
- Prior Firms: PriorFirm1_* through PriorFirm5_* (5 sets × 5 fields = 25 fields)

**Licenses (30+ Series licenses):**
- Series3, Series4, Series5, Series6, Series7, Series8_9_10, Series11, Series14A, Series17, Series21, Series22, Series24, Series25, Series26, Series27, Series28, Series30, Series31, Series39, Series42, Series51, Series52, Series53, Series55, Series56, Series62, Series63, Series64, Series65, Series66, Series72, Series73, Series79, Series82, Series86_87, Series99
- Each has a corresponding _Date field

**Designations (20+):**
- Designations_CFA, Designations_CFP, Designations_CPA, Designations_ChFC, Designations_CLU, Designations_AAMS, Designations_AEP, Designations_AIF, Designations_AWMA, Designations_CASL, Designations_CDFA, Designations_CIMA, Designations_CLTC, Designations_CMFC, Designations_CPWA, Designations_CRPC, Designations_CRPS, Designations_FIC, Designations_LUTCF, Designations_PFS, Designations_RICP, Designations_Other

**Title Categories (20+):**
- Advisor, BankAdvisor, CallCenterAdvisor, Administration, AdvisorAssistant, BranchManager, BranchAdminOps, ComplianceLegal, Executive, FinanceAccounting, InvestmentBanking, OperationsTechnology, PlanningSpecialist, PortfolioManager, Research, ResearchDirector, RetirementPlanSpecialist, SalesMarketing, TradingDesk, TrustOfficer, Wholesaler, Other, Unknown

**Historical Metrics (100+ fields):**
- Number_RegisteredStates_YE2015 through YE2019
- Number_RegisteredStates_ChangeYTD, Change1Year, Change3Years
- NumberRIAFirmAssociations_YE2015 through YE2019
- NumberRIAFirmAssociations_ChangeYTD, Change1Year, Change3Years
- NumberFirmAssociations_YE2015 through YE2019
- NumberFirmAssociations_ChangeYTD, Change1Year, Change3Years
- Number_OfficeReps_YE2018, YE2019, ChangeYTD, Change1Year

### Lead Object: ~150 Fields

**Core Salesforce Fields (50+):**
- Id, Name, FirstName, LastName, Email, Phone, MobilePhone
- Street, City, State, PostalCode, Country, Latitude, Longitude
- Status, LeadSource, IsConverted, ConvertedDate
- CreatedDate, LastModifiedDate, LastActivityDate

**Custom Fields (100+):**
- FA_CRD__c (join key)
- Stage_Entered_New__c, Stage_Entered_Contacting__c, Stage_Entered_Call_Scheduled__c, Stage_Entered_Closed__c
- Savvy_Lead_Score__c, Years_as_a_Rep__c, Years_at_Firm__c
- Personal_AUM__c, Estimated_Transferable_AUM__c
- UTM fields: utm_source__c, utm_medium__c, utm_campaign__c
- Marketing fields: Marketing_Cohort_Name__c, Cohort_Apollo__c

### V6 Training Dataset: 162 Fields

**Identifiers (4):** Id, FA_CRD__c, RIAFirmCRD, target_label

**Financial Metrics (15):** TotalAssetsInMillions, NumberClients_Individuals, NumberClients_HNWIndividuals, AUMGrowthRate_1Year, etc.

**Professional Binary Flags (20):** DuallyRegisteredBDRIARep, Has_Series_7, Has_Series_65, Has_Series_66, Has_CFP, Has_CFA, Is_BreakawayRep, Is_Owner, etc.

**Experience Metrics (10):** DateBecameRep_NumberOfYears, DateOfHireAtCurrentFirm_NumberOfYears, NumberOfPriorFirms, AverageTenureAtPriorFirms, etc.

**Geographic (5):** Home_State, Branch_State, Home_MetropolitanArea, Number_RegisteredStates, MilesToWork

**Firm Aggregations (15):** total_reps, total_firm_aum_millions, avg_clients_per_rep, aum_per_rep, etc.

**Engineered Features (30+):** is_veteran_advisor, is_new_to_firm, multi_ria_relationships, Firm_Stability_Score, license_count, etc.

**Ratios/Efficiency (10+):** AUM_per_Client, AUM_per_IARep, HNW_Client_Ratio, etc.

**Custodian Relationships (8):** Has_Schwab_Relationship, CustodianAUM_Schwab, etc.

**Data Quality Flags (10+):** Missing value indicators, data completeness scores

**Timestamps (4):** Stage_Entered_Contacting__c, Stage_Entered_Call_Scheduled__c, rep_snapshot_at, firm_snapshot_at

---

**Report End**

This report provides a comprehensive foundation for understanding the data sources, structures, transformations, and joining strategies used in the lead scoring model training pipeline. When building new models, always reference the V6 dataset as the canonical example of correct data preparation.

