# Dataset Documentation Report: Lead Scoring Model

**Report Date:** November 4, 2025  
**Project:** Savvy Wealth Lead Scoring Engine  
**Purpose:** Comprehensive documentation of datasets, schemas, matching keys, and temporal identifiers

---

## Executive Summary

This document provides complete documentation for the three primary datasets used in the lead scoring model:
1. **Training Dataset** (`savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`)
2. **Discovery Reps Current** (`savvy-gtm-analytics.LeadScoring.discovery_reps_current`)
3. **Discovery Firms Current** (`savvy-gtm-analytics.LeadScoring.discovery_firms_current`)

**Key Matching Keys:**
- **RepCRD** (Discovery) ↔ **FA_CRD__c** (Salesforce Lead)
- **RIAFirmCRD** (Reps) ↔ **RIAFirmCRD** (Firms)

**Snapshot Date Identifiers:**
- **Current Tables:** `snapshot_as_of` (DATE) and `processed_at` (TIMESTAMP)
- **V6 Historical Snapshots:** `snapshot_at` (DATE) for point-in-time joins

---

## Dataset 1: Training Dataset

### Table Name
`savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`

### Purpose
Final training dataset containing all features and target labels for model training. This table combines Salesforce Lead data with Discovery representative and firm data, including engineered features.

### Key Characteristics
- **Row Count:** ~41,942 - 45,923 (varies by version)
- **Positive Class:** ~1,422 (3.39%)
- **Negative Class:** ~40,520 (96.61%)
- **Primary Key:** `Id` (Salesforce Lead ID)
- **Target Variable:** `target_label` (1 = MQL within 30 days, 0 = no MQL)

### Schema Overview

#### **Primary Identifiers**
| Field Name | Data Type | Description | Nullable |
|------------|-----------|-------------|----------|
| `Id` | STRING | Salesforce Lead ID (primary key) | NO |
| `FA_CRD__c` | STRING | Financial Advisor CRD number (matches RepCRD) | YES |
| `RIAFirmCRD` | STRING | RIA Firm CRD number | YES |

#### **Temporal Fields**
| Field Name | Data Type | Description | Nullable |
|------------|-----------|-------------|----------|
| `Stage_Entered_Contacting__c` | TIMESTAMP | When lead entered "Contacting" stage | NO |
| `Stage_Entered_Call_Scheduled__c` | TIMESTAMP | When lead scheduled call (conversion event) | YES |
| `days_to_conversion` | INT64 | Days from contact to conversion (NULL if no conversion) | YES |
| `rep_snapshot_at` | DATE | Snapshot date for rep data (V6 only) | YES |
| `firm_snapshot_at` | DATE | Snapshot date for firm data (V6 only) | YES |

#### **Target Variable**
| Field Name | Data Type | Description | Nullable |
|------------|-----------|-------------|----------|
| `target_label` | INT64 | 1 = MQL within 30 days, 0 = no MQL | NO |

#### **Representative Features (from discovery_reps_current)**
**Financial Metrics:**
- `TotalAssetsInMillions` (FLOAT64) - Total assets under management
- `TotalAssets_PooledVehicles` (FLOAT64) - Pooled vehicle assets
- `TotalAssets_SeparatelyManagedAccounts` (FLOAT64) - SMA assets
- `AssetsInMillions_Individuals` (FLOAT64) - Individual client assets
- `AssetsInMillions_HNWIndividuals` (FLOAT64) - High-net-worth individual assets
- `AssetsInMillions_MutualFunds` (FLOAT64) - Mutual fund assets
- `AssetsInMillions_PrivateFunds` (FLOAT64) - Private fund assets
- `AssetsInMillions_Equity_ExchangeTraded` (FLOAT64) - ETF assets

**Growth Metrics:**
- `AUMGrowthRate_1Year` (FLOAT64) - 1-year AUM growth rate
- `AUMGrowthRate_5Year` (FLOAT64) - 5-year AUM growth rate

**Client Metrics:**
- `NumberClients_Individuals` (INT64) - Number of individual clients
- `NumberClients_HNWIndividuals` (INT64) - Number of HNW individual clients
- `NumberClients_RetirementPlans` (INT64) - Number of retirement plan clients
- `PercentClients_Individuals` (FLOAT64) - Percentage of individual clients
- `PercentClients_HNWIndividuals` (FLOAT64) - Percentage of HNW clients

**Asset Composition:**
- `PercentAssets_MutualFunds` (FLOAT64) - Percentage of assets in mutual funds
- `PercentAssets_PrivateFunds` (FLOAT64) - Percentage of assets in private funds
- `PercentAssets_Equity_ExchangeTraded` (FLOAT64) - Percentage of assets in ETFs
- `PercentAssets_HNWIndividuals` (FLOAT64) - Percentage of assets from HNW individuals
- `PercentAssets_Individuals` (FLOAT64) - Percentage of assets from individuals

**Tenure & Experience:**
- `DateBecameRep_NumberOfYears` (FLOAT64) - Years since becoming a rep
- `DateOfHireAtCurrentFirm_NumberOfYears` (FLOAT64) - Years at current firm
- `Number_YearsPriorFirm1` (FLOAT64) - Years at prior firm 1
- `Number_YearsPriorFirm2` (FLOAT64) - Years at prior firm 2
- `Number_YearsPriorFirm3` (FLOAT64) - Years at prior firm 3
- `Number_YearsPriorFirm4` (FLOAT64) - Years at prior firm 4
- `AverageTenureAtPriorFirms` (FLOAT64) - Average tenure at prior firms
- `NumberOfPriorFirms` (FLOAT64) - Total number of prior firms

**Firm Associations:**
- `NumberFirmAssociations` (INT64) - Number of firm associations
- `NumberRIAFirmAssociations` (INT64) - Number of RIA firm associations
- `Number_IAReps` (INT64) - Number of IA reps at firm
- `Number_BranchAdvisors` (INT64) - Number of branch advisors
- `IsPrimaryRIAFirm` (STRING/INT64) - Is primary RIA firm flag
- `DuallyRegisteredBDRIARep` (STRING/INT64) - Dually registered BD/RIA rep

**Licenses & Designations:**
- `Has_Series_7` (INT64/BOOLEAN) - Has Series 7 license
- `Has_Series_65` (INT64/BOOLEAN) - Has Series 65 license
- `Has_Series_66` (INT64/BOOLEAN) - Has Series 66 license
- `Has_Series_24` (INT64/BOOLEAN) - Has Series 24 license
- `Has_CFP` (INT64/BOOLEAN) - Has CFP designation
- `Has_CFA` (INT64/BOOLEAN) - Has CFA designation
- `Has_CIMA` (INT64/BOOLEAN) - Has CIMA designation
- `Has_AIF` (INT64/BOOLEAN) - Has AIF designation
- `Has_Disclosure` (INT64/BOOLEAN) - Has regulatory disclosure
- `Licenses` (STRING) - Concatenated licenses string

**Professional Characteristics:**
- `Is_BreakawayRep` (STRING/INT64) - Is breakaway rep
- `Has_Insurance_License` (INT64/BOOLEAN) - Has insurance license
- `Is_NonProducer` (INT64/BOOLEAN) - Is non-producer
- `Is_IndependentContractor` (INT64/BOOLEAN) - Is independent contractor
- `Is_Owner` (INT64/BOOLEAN) - Is firm owner
- `Education` (STRING) - Education level/background
- `Gender` (STRING) - Gender
- `Title` (STRING) - Professional title

**Geographic Features:**
- `Home_State` (STRING) - Home state
- `Home_City` (STRING) - Home city
- `Home_County` (STRING) - Home county
- `Home_ZipCode` (FLOAT64) - Home zip code
- `Home_Latitude` (FLOAT64) - Home latitude
- `Home_Longitude` (FLOAT64) - Home longitude
- `Home_MetropolitanArea` (STRING) - Home metropolitan area
- `Branch_State` (STRING) - Branch office state
- `Branch_City` (STRING) - Branch office city
- `Branch_County` (STRING) - Branch office county
- `Branch_ZipCode` (FLOAT64) - Branch zip code
- `Branch_Latitude` (FLOAT64) - Branch latitude
- `Branch_Longitude` (FLOAT64) - Branch longitude
- `MilesToWork` (FLOAT64) - Miles from home to work
- `Number_RegisteredStates` (INT64) - Number of states registered in

**Contact & Presence:**
- `SocialMedia_LinkedIn` (STRING) - LinkedIn profile URL
- `Email_BusinessType` (STRING) - Business email type
- `Email_PersonalType` (STRING) - Personal email type
- `FirmWebsite` (STRING) - Firm website URL
- `PersonalWebpage` (STRING) - Personal webpage URL
- `Brochure_Keywords` (STRING) - Brochure keywords
- `CustomKeywords` (STRING) - Custom keywords

**Custodian Relationships:**
- `CustodianAUM_Schwab` (FLOAT64) - AUM with Schwab
- `CustodianAUM_Fidelity_NationalFinancial` (FLOAT64) - AUM with Fidelity
- `CustodianAUM_Pershing` (FLOAT64) - AUM with Pershing
- `CustodianAUM_TDAmeritrade` (FLOAT64) - AUM with TD Ameritrade
- `Custodian1` (STRING) - Primary custodian
- `Custodian2` (STRING) - Secondary custodian
- `Custodian3` (STRING) - Tertiary custodian
- `Custodian4` (STRING) - Fourth custodian
- `Custodian5` (STRING) - Fifth custodian
- `Has_Schwab_Relationship` (INT64/BOOLEAN) - Has Schwab relationship
- `Has_Fidelity_Relationship` (INT64/BOOLEAN) - Has Fidelity relationship
- `Has_Pershing_Relationship` (INT64/BOOLEAN) - Has Pershing relationship
- `Has_TDAmeritrade_Relationship` (INT64/BOOLEAN) - Has TD Ameritrade relationship

**USPS Certification:**
- `Office_USPS_Certified` (INT64/BOOLEAN) - Office USPS certified
- `Home_USPS_Certified` (INT64/BOOLEAN) - Home USPS certified

**PII Fields (Typically Excluded from Model):**
- `FirstName` (STRING) - First name
- `LastName` (STRING) - Last name
- `RIAFirmName` (STRING) - RIA firm name
- `Notes` (STRING) - Notes field

#### **Firm Features (from discovery_firms_current)**
| Field Name | Data Type | Description | Nullable |
|------------|-----------|-------------|----------|
| `total_firm_aum_millions` | FLOAT64 | Total firm AUM in millions | YES |
| `total_reps` | INT64 | Total number of reps at firm | YES |
| `total_firm_clients` | INT64 | Total firm clients | YES |
| `total_firm_hnw_clients` | INT64 | Total firm HNW clients | YES |
| `avg_clients_per_rep` | FLOAT64 | Average clients per rep | YES |
| `aum_per_rep` | FLOAT64 | Average AUM per rep | YES |
| `avg_firm_growth_1y` | FLOAT64 | Average 1-year firm growth | YES |
| `avg_firm_growth_5y` | FLOAT64 | Average 5-year firm growth | YES |
| `pct_reps_with_cfp` | FLOAT64 | Percentage of reps with CFP | YES |
| `pct_reps_with_disclosure` | FLOAT64 | Percentage of reps with disclosure | YES |
| `firm_size_tier` | STRING | Firm size category | YES |
| `multi_state_firm` | INT64/BOOLEAN | Multi-state firm flag | YES |
| `national_firm` | INT64/BOOLEAN | National firm flag | YES |

#### **Engineered Features (V6)**
**Rep & Firm Maturity:**
- `is_veteran_advisor` (INT64) - Advisor with 10+ years experience
- `is_new_to_firm` (INT64) - Less than 2 years at current firm
- `avg_prior_firm_tenure_lt3` (INT64) - Average prior firm tenure < 3 years
- `high_turnover_flag` (INT64) - High turnover flag (>3 prior firms, avg tenure <3)
- `multi_ria_relationships` (INT64) - Multiple RIA relationships
- `complex_registration` (INT64) - Complex registration pattern
- `multi_state_registered` (INT64) - Registered in >10 states
- `Firm_Stability_Score` (FLOAT64) - Firm stability score (tenure / prior firms)

**Licenses & Designations:**
- `license_count` (INT64) - Total license count
- `designation_count` (INT64) - Total designation count

**Geography & Logistics:**
- `branch_vs_home_mismatch` (INT64) - Branch state ≠ home state
- `Home_Zip_3Digit` (STRING) - 3-digit home zip code
- `remote_work_indicator` (INT64) - Miles to work > 50
- `local_advisor` (INT64) - Miles to work ≤ 10

**Firm Context:**
- `firm_rep_count_bin` (STRING) - Firm rep count bin (1, 2_5, 6_20, 21_plus)

**Contactability:**
- `has_linkedin` (INT64) - Has LinkedIn profile
- `email_business_type_flag` (INT64) - Has business email
- `email_personal_type_flag` (INT64) - Has personal email

**Missingness Indicators:**
- `doh_current_years_is_missing` (INT64) - DOH current years missing
- `became_rep_years_is_missing` (INT64) - Became rep years missing
- `avg_prior_firm_tenure_is_missing` (INT64) - Avg prior firm tenure missing
- `num_prior_firms_is_missing` (INT64) - Num prior firms missing
- `num_registered_states_is_missing` (INT64) - Num registered states missing
- `firm_total_reps_is_missing` (INT64) - Firm total reps missing
- `missing_feature_count` (INT64) - Total missing feature count

**Interactions:**
- `is_new_to_firm_x_has_series65` (INT64) - New to firm × Series 65
- `veteran_x_cfp` (INT64) - Veteran advisor × CFP
- `Branch_Advisors_per_Firm_Association` (FLOAT64) - Branch advisors per association

---

## Dataset 2: Discovery Reps Current

### Table Name
`savvy-gtm-analytics.LeadScoring.discovery_reps_current`

### Purpose
Current snapshot of all representative data from MarketPro (RIARepDataFeed). Contains all representative-level features used for lead scoring.

### Key Characteristics
- **Row Count:** ~477,901 records (462,825 unique RepCRDs)
- **Source:** MarketPro RIARepDataFeed (T1, T2, T3 territories)
- **Primary Key:** `RepCRD` (not unique - may have duplicates)
- **Update Frequency:** Quarterly (current snapshot only)

### Schema Overview

#### **Primary Identifiers**
| Field Name | Data Type | Description | Nullable |
|------------|-----------|-------------|----------|
| `RepCRD` | STRING | Representative CRD number (matching key) | NO |
| `RIAFirmCRD` | STRING | RIA Firm CRD number (joins to firms table) | YES |

#### **Temporal Identifiers**
| Field Name | Data Type | Description | Nullable |
|------------|-----------|-------------|----------|
| `snapshot_as_of` | DATE | Snapshot date for this data (when data was current) | YES |
| `processed_at` | TIMESTAMP | When this record was processed/loaded | NO |
| `territory_source` | STRING | Source territory (T1, T2, T3) | YES |

#### **Complete Field List**
The schema matches the representative features listed in Dataset 1 above. See "Representative Features" section for complete field list.

**Note:** This table may contain duplicate RepCRDs (same rep appearing in multiple territories or snapshots). Use appropriate deduplication when joining.

---

## Dataset 3: Discovery Firms Current

### Table Name
`savvy-gtm-analytics.LeadScoring.discovery_firms_current`

### Purpose
Current snapshot of firm-level aggregated features derived from `discovery_reps_current`. Provides firm-level insights for lead scoring.

### Key Characteristics
- **Row Count:** ~38,543 unique firms
- **Source:** Aggregated from `discovery_reps_current`
- **Primary Key:** `RIAFirmCRD` (unique)
- **Update Frequency:** Quarterly (current snapshot only)

### Schema Overview

#### **Primary Identifiers**
| Field Name | Data Type | Description | Nullable |
|------------|-----------|-------------|----------|
| `RIAFirmCRD` | STRING | RIA Firm CRD number (primary key, unique) | NO |
| `RIAFirmName` | STRING | RIA Firm name | YES |

#### **Complete Field List**
The schema matches the firm features listed in Dataset 1 above. See "Firm Features" section for complete field list.

**Key Aggregated Metrics:**
- Firm size (total_reps, total_firm_aum_millions)
- Growth metrics (avg_firm_growth_1y, avg_firm_growth_5y)
- Client metrics (total_firm_clients, total_firm_hnw_clients)
- Efficiency metrics (aum_per_rep, avg_clients_per_rep)
- Professional composition (pct_reps_with_cfp, pct_reps_with_disclosure)
- Geographic distribution (multi_state_firm, national_firm)

---

## Matching Keys: RepCRD to Lead Object

### Primary Matching Relationship

**Discovery Reps → Salesforce Leads**

| Discovery Table | Lead Object | Join Condition |
|----------------|-------------|----------------|
| `discovery_reps_current.RepCRD` | `SavvyGTMData.Lead.FA_CRD__c` | `RepCRD = FA_CRD__c` |

**Example SQL:**
```sql
SELECT 
    l.Id,
    l.FA_CRD__c,
    drc.RepCRD,
    drc.*
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc
    ON l.FA_CRD__c = drc.RepCRD
WHERE l.Stage_Entered_Contacting__c IS NOT NULL
  AND l.FA_CRD__c IS NOT NULL;
```

### Matching Characteristics

**CRD Matching Rate:**
- **Expected Match Rate:** ~94.82% (based on Step 3.1 analysis)
- **Total Leads:** ~79,002 leads with `FA_CRD__c` populated
- **Matched Leads:** ~74,900 leads with matching RepCRD

**Data Quality Notes:**
- `FA_CRD__c` is required for matching (must be NOT NULL)
- `RepCRD` may have duplicates (same rep in multiple territories)
- Use deduplication when joining (e.g., `QUALIFY ROW_NUMBER() OVER (PARTITION BY RepCRD ORDER BY processed_at DESC) = 1`)

### Secondary Matching: Firms

**Discovery Reps → Discovery Firms**

| Rep Table | Firm Table | Join Condition |
|-----------|------------|----------------|
| `discovery_reps_current.RIAFirmCRD` | `discovery_firms_current.RIAFirmCRD` | `RIAFirmCRD = RIAFirmCRD` |

**Example SQL:**
```sql
SELECT 
    drc.RepCRD,
    drc.RIAFirmCRD,
    dfc.*
FROM `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_firms_current` dfc
    ON drc.RIAFirmCRD = dfc.RIAFirmCRD;
```

---

## Snapshot Date Identifiers

### Overview
Snapshot date identifiers are critical for temporal data integrity. They ensure we use the correct historical data when training models and avoid data leakage.

### Current Tables (discovery_reps_current, discovery_firms_current)

#### **snapshot_as_of** (DATE)
- **Purpose:** Identifies when the data snapshot was taken
- **Usage:** Used to determine if a lead is eligible for mutable features
- **Example:** `DATE('2024-10-06')` for Q4 2024 snapshot
- **Logic:** 
  - If `Stage_Entered_Contacting__c >= snapshot_as_of` → Lead is eligible for mutable features
  - If `Stage_Entered_Contacting__c < snapshot_as_of` → Lead is historical, mutable features should be NULL

**Example Usage:**
```sql
CASE 
    WHEN DATE(sf.Stage_Entered_Contacting__c) >= drc.snapshot_as_of
    THEN 1 ELSE 0 
END as is_eligible_for_mutable_features
```

#### **processed_at** (TIMESTAMP)
- **Purpose:** Records when the data was processed/loaded into BigQuery
- **Usage:** Metadata tracking, not used for temporal logic
- **Example:** `2025-11-04 12:35:20 UTC`

### V6 Historical Snapshots (v_discovery_reps_all_vintages, v_discovery_firms_all_vintages)

#### **snapshot_at** (DATE)
- **Purpose:** Point-in-time snapshot date for historical data
- **Usage:** Used for point-in-time joins to match leads to correct historical snapshot
- **Example:** `DATE('2024-03-31')` for March 31, 2024 snapshot
- **Source:** Extracted from CSV filename (e.g., `RIARepDataFeed_20240331.csv` → `DATE('2024-03-31')`)

**Point-in-Time Join Logic:**
```sql
LEFT JOIN `v_discovery_reps_all_vintages` reps
    ON reps.RepCRD = l2.FA_CRD__c
    AND reps.snapshot_at <= l2.contact_date
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY l2.FA_CRD__c, l2.contact_date 
    ORDER BY reps.snapshot_at DESC
) = 1
```

**This ensures:**
- Each lead is matched to the most recent snapshot that existed at or before the contact date
- No future data leakage (only uses snapshots ≤ contact date)
- Point-in-time accuracy for historical training data

### Snapshot Date Mapping

| CSV File | Snapshot Date | Quarter | Usage |
|----------|---------------|---------|-------|
| `RIARepDataFeed_20240107.csv` | `2024-01-07` | Q1 2024 | Historical snapshot |
| `RIARepDataFeed_20240331.csv` | `2024-03-31` | Q1 2024 | Historical snapshot |
| `RIARepDataFeed_20240707.csv` | `2024-07-07` | Q3 2024 | Historical snapshot |
| `RIARepDataFeed_20241006.csv` | `2024-10-06` | Q4 2024 | Historical snapshot |
| `RIARepDataFeed_20250105.csv` | `2025-01-05` | Q1 2025 | Historical snapshot |
| `RIARepDataFeed_20250406.csv` | `2025-04-06` | Q2 2025 | Historical snapshot |
| `RIARepDataFeed_20250706.csv` | `2025-07-06` | Q3 2025 | Historical snapshot |
| `RIARepDataFeed_20251005.csv` | `2025-10-05` | Q4 2025 | Current snapshot |

**Reference:** See `config/v6_snapshot_date_mapping.json` for complete mapping.

### Temporal Matching Examples

#### Example 1: Lead Contacted on March 31, 2024
- **Lead:** `Stage_Entered_Contacting__c = '2024-03-31'`
- **Available Snapshots:** `2024-01-07`, `2024-03-31`
- **Match:** `snapshot_at = 2024-03-31` ✅ (most recent snapshot ≤ contact date)

#### Example 2: Lead Contacted on April 1, 2024
- **Lead:** `Stage_Entered_Contacting__c = '2024-04-01'`
- **Available Snapshots:** `2024-01-07`, `2024-03-31`, `2024-07-07`
- **Match:** `snapshot_at = 2024-03-31` ✅ (most recent snapshot ≤ contact date)
- **Note:** Does NOT use `2024-07-07` (future data leakage prevention)

#### Example 3: Lead Contacted on March 15, 2024
- **Lead:** `Stage_Entered_Contacting__c = '2024-03-15'`
- **Available Snapshots:** `2024-01-07`, `2024-03-31`
- **Match:** `snapshot_at = 2024-01-07` ✅ (most recent snapshot ≤ contact date)
- **Note:** Does NOT use `2024-03-31` (future data leakage prevention)

---

## Data Quality Considerations

### Duplicate RepCRDs
- **Issue:** `discovery_reps_current` may contain duplicate RepCRDs
- **Cause:** Same rep appearing in multiple territories (T1, T2, T3) or multiple snapshots
- **Impact:** LEFT JOIN can multiply rows when joining to Leads
- **Solution:** Use deduplication when joining:
  ```sql
  QUALIFY ROW_NUMBER() OVER (
      PARTITION BY RepCRD 
      ORDER BY processed_at DESC
  ) = 1
  ```

### Missing Values
- **Financial Metrics:** Many financial metrics may be NULL (not available in RIARepDataFeed)
- **Historical Leads:** Mutable features NULLed for historical leads (temporal integrity)
- **Missing Data Rate:** ~5-10% for key features (varies by feature)

### Data Type Consistency
- **Boolean Fields:** May be stored as INT64 (0/1) or STRING ("Yes"/"No") depending on source
- **Date Fields:** Ensure consistent DATE/TIMESTAMP format
- **Numeric Fields:** Use SAFE_CAST for conversions to handle errors gracefully

---

## Usage Examples

### Example 1: Join Leads to Discovery Data
```sql
SELECT 
    l.Id,
    l.FA_CRD__c,
    l.Stage_Entered_Contacting__c,
    drc.RepCRD,
    drc.TotalAssetsInMillions,
    drc.AUMGrowthRate_1Year,
    dfc.total_firm_aum_millions,
    dfc.total_reps
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc
    ON l.FA_CRD__c = drc.RepCRD
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_firms_current` dfc
    ON drc.RIAFirmCRD = dfc.RIAFirmCRD
WHERE l.Stage_Entered_Contacting__c IS NOT NULL
  AND l.FA_CRD__c IS NOT NULL;
```

### Example 2: Point-in-Time Join (V6)
```sql
SELECT 
    l.Id,
    l.FA_CRD__c,
    l.Stage_Entered_Contacting__c,
    DATE(l.Stage_Entered_Contacting__c) as contact_date,
    reps.RepCRD,
    reps.TotalAssetsInMillions,
    reps.snapshot_at as rep_snapshot_at,
    firms.total_firm_aum_millions,
    firms.snapshot_at as firm_snapshot_at
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
LEFT JOIN `savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages` reps
    ON reps.RepCRD = l.FA_CRD__c
    AND reps.snapshot_at <= DATE(l.Stage_Entered_Contacting__c)
LEFT JOIN `savvy-gtm-analytics.LeadScoring.v_discovery_firms_all_vintages` firms
    ON firms.RIAFirmCRD = reps.RIAFirmCRD
    AND firms.snapshot_at <= DATE(l.Stage_Entered_Contacting__c)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY l.Id 
    ORDER BY reps.snapshot_at DESC, firms.snapshot_at DESC
) = 1
WHERE l.Stage_Entered_Contacting__c IS NOT NULL
  AND l.FA_CRD__c IS NOT NULL;
```

### Example 3: Query Training Dataset
```sql
SELECT 
    Id,
    FA_CRD__c,
    target_label,
    TotalAssetsInMillions,
    AUMGrowthRate_1Year,
    total_firm_aum_millions,
    total_reps
FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`
WHERE target_label = 1  -- Positive examples
LIMIT 100;
```

---

## References

- **V6 Historical Data Processing Guide:** `V6_Historical_Data_Processing_Guide.md`
- **Snapshot Date Mapping:** `config/v6_snapshot_date_mapping.json`
- **Feature Schema:** `config/v1_feature_schema.json`
- **Model Config:** `config/v1_model_config.json`
- **Table Structure Clarification:** `V6_Table_Structure_Clarification.md`

---

**Report Generated:** November 4, 2025  
**Last Updated:** November 4, 2025  
**Maintained By:** Data Engineering Team

