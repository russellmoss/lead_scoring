# V6 Training Dataset Report

**Table:** `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v6_20251104_2217`  
**Created:** November 4, 2025, 22:22:15  
**Total Rows:** 41,942  
**Total Columns:** 162  
**Table Size:** 27.16 MB

---

## Executive Summary

The V6 training dataset is a **point-in-time (PIT) correct** dataset designed for predicting 30-day MQL (Marketing Qualified Lead) conversion. It combines:

- **Rep-level features** from Discovery Data snapshots (historical point-in-time data)
- **Firm-level aggregations** from Discovery Data
- **Lead metadata** from Salesforce
- **Engineered features** optimized for 30-day conversion prediction
- **Target variable:** Binary indicator if Call Scheduled occurred ≤ 30 days after Stage Entered Contacting

**Key Innovation:** All features are **temporally correct** - each lead is matched to rep/firm data that existed at or before the contact date, preventing data leakage.

---

## Dataset Creation Process (How V6 Was Built)

### Step 1: Historical Snapshot Ingestion
1. **8 Historical Snapshots** were ingested from Discovery Data:
   - 2024-01-07, 2024-03-31, 2024-07-07, 2024-10-06
   - 2025-01-05, 2025-04-06, 2025-07-06, 2025-10-05
2. Each snapshot contains rep-level data (licenses, tenure, location, firm associations)
3. Firm-level aggregations were computed from rep snapshots

### Step 2: Point-in-Time Join
- Each lead's `Stage_Entered_Contacting__c` date was matched to the **nearest earlier snapshot**
- Ensures no future information leaks into features
- Rep and firm data reflect state **at or before** contact date

### Step 3: Feature Engineering
- **Rep & Firm Maturity Proxies:** Veteran status, tenure, stability scores
- **License/Designation Counts:** Aggregated professional credentials
- **Geographic & Logistics:** Remote work, local advisor, state mismatches
- **Contactability:** LinkedIn presence, email flags
- **Missingness Indicators:** Flags for missing data (never silently imputed)
- **Simple Interactions:** Cross-feature combinations

### Step 4: Target Label Creation
```sql
target_label = 1 IF Call_Scheduled occurred ≤ 30 days after Stage_Entered_Contacting__c
target_label = 0 OTHERWISE
```

### Step 5: Data Quality Filters
- Excluded right-censored leads (within last 30 days)
- Removed leads with negative days_to_conversion
- Final dataset: 41,942 valid training samples

---

## Complete Schema: Column Names, Types, and Descriptions

### Identifiers (Not Features)
| Column Name | Type | Description |
|-------------|------|-------------|
| `Id` | STRING | Salesforce Lead ID (for linking only, not a feature) |
| `FA_CRD__c` | STRING | Financial Advisor CRD number (identifier, not a feature) |
| `RIAFirmCRD` | STRING | RIA Firm CRD number (identifier, not a feature) |
| `target_label` | INTEGER | Binary target: 1 = converted within 30 days, 0 = did not convert |

### Financial Metrics (Rep-Level)
| Column Name | Type | Description |
|-------------|------|-------------|
| `TotalAssetsInMillions` | FLOAT | Total assets under management (millions) |
| `TotalAssets_PooledVehicles` | FLOAT | Assets in pooled vehicles (millions) |
| `TotalAssets_SeparatelyManagedAccounts` | FLOAT | Assets in separately managed accounts (millions) |
| `NumberClients_Individuals` | INTEGER | Count of individual clients |
| `NumberClients_HNWIndividuals` | INTEGER | Count of high net worth individual clients |
| `NumberClients_RetirementPlans` | INTEGER | Count of retirement plan clients |
| `PercentClients_Individuals` | FLOAT | Percentage of clients that are individuals |
| `PercentClients_HNWIndividuals` | FLOAT | Percentage of clients that are HNW individuals |
| `AssetsInMillions_MutualFunds` | FLOAT | Assets in mutual funds (millions) |
| `AssetsInMillions_PrivateFunds` | FLOAT | Assets in private funds (millions) |
| `AssetsInMillions_Equity_ExchangeTraded` | FLOAT | Assets in exchange-traded equity (millions) |
| `PercentAssets_MutualFunds` | FLOAT | Percentage of assets in mutual funds |
| `PercentAssets_PrivateFunds` | FLOAT | Percentage of assets in private funds |
| `PercentAssets_Equity_ExchangeTraded` | FLOAT | Percentage of assets in exchange-traded equity |

### Professional Metrics (Rep-Level)
| Column Name | Type | Description |
|-------------|------|-------------|
| `Number_IAReps` | INTEGER | Number of IA (Investment Advisor) representatives |
| `Number_BranchAdvisors` | INTEGER | Number of branch advisors |
| `NumberFirmAssociations` | INTEGER | Total number of firm associations |
| `NumberRIAFirmAssociations` | INTEGER | Number of RIA firm associations |
| `AUMGrowthRate_1Year` | FLOAT | AUM growth rate over 1 year |
| `AUMGrowthRate_5Year` | FLOAT | AUM growth rate over 5 years |

### Tenure & Experience (Rep-Level)
| Column Name | Type | Description |
|-------------|------|-------------|
| `DateBecameRep_NumberOfYears` | FLOAT | Years since becoming a rep |
| `DateOfHireAtCurrentFirm_NumberOfYears` | FLOAT | Years at current firm |
| `Number_YearsPriorFirm1` | FLOAT | Years at prior firm 1 |
| `Number_YearsPriorFirm2` | FLOAT | Years at prior firm 2 |
| `Number_YearsPriorFirm3` | FLOAT | Years at prior firm 3 |
| `Number_YearsPriorFirm4` | FLOAT | Years at prior firm 4 |
| `AverageTenureAtPriorFirms` | FLOAT | Average tenure at prior firms |
| `NumberOfPriorFirms` | INTEGER | Total number of prior firms |

### Professional Flags (Binary - INTEGER 0/1)
| Column Name | Type | Description |
|-------------|------|-------------|
| `IsPrimaryRIAFirm` | INTEGER | 1 if primary RIA firm, 0 otherwise |
| `DuallyRegisteredBDRIARep` | INTEGER | 1 if dually registered BD/RIA rep, 0 otherwise |
| `Has_Series_7` | INTEGER | 1 if has Series 7 license, 0 otherwise |
| `Has_Series_65` | INTEGER | 1 if has Series 65 license, 0 otherwise |
| `Has_Series_66` | INTEGER | 1 if has Series 66 license, 0 otherwise |
| `Has_Series_24` | INTEGER | 1 if has Series 24 license, 0 otherwise |
| `Has_CFP` | INTEGER | 1 if has CFP designation, 0 otherwise |
| `Has_CFA` | INTEGER | 1 if has CFA designation, 0 otherwise |
| `Has_CIMA` | INTEGER | 1 if has CIMA designation, 0 otherwise |
| `Has_AIF` | INTEGER | 1 if has AIF designation, 0 otherwise |
| `Has_Disclosure` | INTEGER | 1 if has regulatory disclosure, 0 otherwise |
| `Is_BreakawayRep` | INTEGER | 1 if breakaway rep, 0 otherwise |
| `Has_Insurance_License` | INTEGER | 1 if has insurance license, 0 otherwise |
| `Is_NonProducer` | INTEGER | 1 if non-producer, 0 otherwise |
| `Is_IndependentContractor` | INTEGER | 1 if independent contractor, 0 otherwise |
| `Is_Owner` | INTEGER | 1 if firm owner, 0 otherwise |
| `Office_USPS_Certified` | INTEGER | 1 if office address is USPS certified, 0 otherwise |
| `Home_USPS_Certified` | INTEGER | 1 if home address is USPS certified, 0 otherwise |

### Geographic & Location
| Column Name | Type | Description |
|-------------|------|-------------|
| `Home_MetropolitanArea` | STRING | Home metropolitan area name |
| `Branch_State` | STRING | Branch/office state |
| `Home_State` | STRING | Home state |
| `MilesToWork` | FLOAT | Distance from home to work (miles) |

### Contact & Social Media
| Column Name | Type | Description |
|-------------|------|-------------|
| `SocialMedia_LinkedIn` | STRING | LinkedIn profile URL (if available) |

### Custodian Relationships (AUM & Flags)
| Column Name | Type | Description |
|-------------|------|-------------|
| `CustodianAUM_Schwab` | FLOAT | AUM with Schwab custodian (millions) |
| `CustodianAUM_Fidelity_NationalFinancial` | FLOAT | AUM with Fidelity custodian (millions) |
| `CustodianAUM_Pershing` | FLOAT | AUM with Pershing custodian (millions) |
| `CustodianAUM_TDAmeritrade` | FLOAT | AUM with TD Ameritrade custodian (millions) |
| `Has_Schwab_Relationship` | INTEGER | 1 if has Schwab relationship, 0 otherwise |
| `Has_Fidelity_Relationship` | INTEGER | 1 if has Fidelity relationship, 0 otherwise |
| `Has_Pershing_Relationship` | INTEGER | 1 if has Pershing relationship, 0 otherwise |
| `Has_TDAmeritrade_Relationship` | INTEGER | 1 if has TD Ameritrade relationship, 0 otherwise |
| `Number_RegisteredStates` | INTEGER | Number of states where rep is registered |

### Firm-Level Aggregations
| Column Name | Type | Description |
|-------------|------|-------------|
| `total_firm_aum_millions` | FLOAT | Total firm AUM (millions) |
| `total_reps` | INTEGER | Total number of reps at firm |
| `total_firm_clients` | INTEGER | Total number of firm clients |
| `total_firm_hnw_clients` | INTEGER | Total number of HNW clients at firm |
| `avg_clients_per_rep` | FLOAT | Average clients per rep at firm |
| `aum_per_rep` | FLOAT | Average AUM per rep at firm |
| `avg_firm_growth_1y` | FLOAT | Average 1-year growth rate at firm |
| `avg_firm_growth_5y` | FLOAT | Average 5-year growth rate at firm |
| `pct_reps_with_cfp` | FLOAT | Percentage of reps at firm with CFP |
| `pct_reps_with_disclosure` | FLOAT | Percentage of reps at firm with disclosure |
| `firm_size_tier` | STRING | Firm size category (e.g., "Small", "Medium", "Large") |
| `multi_state_firm` | INTEGER | 1 if firm operates in multiple states, 0 otherwise |
| `national_firm` | INTEGER | 1 if national firm, 0 otherwise |

### Engineered Features - Rep & Firm Maturity Proxies
| Column Name | Type | Description |
|-------------|------|-------------|
| `is_veteran_advisor` | INTEGER | 1 if DateBecameRep_NumberOfYears >= 10, 0 otherwise |
| `is_new_to_firm` | INTEGER | 1 if DateOfHireAtCurrentFirm_NumberOfYears < 2, 0 otherwise |
| `avg_prior_firm_tenure_lt3` | INTEGER | 1 if AverageTenureAtPriorFirms < 3, 0 otherwise |
| `high_turnover_flag` | INTEGER | 1 if NumberOfPriorFirms > 3 AND AverageTenureAtPriorFirms < 3, 0 otherwise |
| `multi_ria_relationships` | INTEGER | 1 if NumberRIAFirmAssociations > 1, 0 otherwise |
| `complex_registration` | INTEGER | 1 if NumberFirmAssociations > 2 OR NumberRIAFirmAssociations > 1, 0 otherwise |
| `multi_state_registered` | INTEGER | 1 if Number_RegisteredStates > 10, 0 otherwise |
| `Firm_Stability_Score` | FLOAT | DateOfHireAtCurrentFirm_NumberOfYears / (NumberOfPriorFirms + 1) |

### Engineered Features - License/Designation Counts
| Column Name | Type | Description |
|-------------|------|-------------|
| `license_count` | INTEGER | Sum of Has_Series_7, Has_Series_65, Has_Series_66, Has_Series_24 |
| `designation_count` | INTEGER | Sum of Has_CFP, Has_CFA, Has_CIMA, Has_AIF |

### Engineered Features - Geography & Logistics
| Column Name | Type | Description |
|-------------|------|-------------|
| `branch_vs_home_mismatch` | INTEGER | 1 if Branch_State != Home_State, 0 otherwise |
| `Home_Zip_3Digit` | STRING | First 3 digits of home zip code (if metro area missing) |
| `remote_work_indicator` | INTEGER | 1 if MilesToWork > 50, 0 otherwise |
| `local_advisor` | INTEGER | 1 if MilesToWork <= 10, 0 otherwise |

### Engineered Features - Firm Context
| Column Name | Type | Description |
|-------------|------|-------------|
| `firm_rep_count_bin` | STRING | Binned firm size: '1', '2_5', '6_20', '21_plus' |

### Engineered Features - Contactability & Presence
| Column Name | Type | Description |
|-------------|------|-------------|
| `has_linkedin` | INTEGER | 1 if LinkedIn profile exists, 0 otherwise |
| `email_business_type_flag` | INTEGER | 1 if business email available, 0 otherwise (proxy from LinkedIn) |
| `email_personal_type_flag` | INTEGER | 1 if personal email available, 0 otherwise (proxy from LinkedIn) |

### Engineered Features - Missingness Indicators (Never Silently Imputed)
| Column Name | Type | Description |
|-------------|------|-------------|
| `doh_current_years_is_missing` | INTEGER | 1 if DateOfHireAtCurrentFirm_NumberOfYears IS NULL, 0 otherwise |
| `became_rep_years_is_missing` | INTEGER | 1 if DateBecameRep_NumberOfYears IS NULL, 0 otherwise |
| `avg_prior_firm_tenure_is_missing` | INTEGER | 1 if AverageTenureAtPriorFirms IS NULL, 0 otherwise |
| `num_prior_firms_is_missing` | INTEGER | 1 if NumberOfPriorFirms IS NULL, 0 otherwise |
| `num_registered_states_is_missing` | INTEGER | 1 if Number_RegisteredStates IS NULL, 0 otherwise |
| `firm_total_reps_is_missing` | INTEGER | 1 if total_reps IS NULL, 0 otherwise |
| `missing_feature_count` | INTEGER | Sum of all missingness flags (0-6) |

### Engineered Features - Simple Interactions
| Column Name | Type | Description |
|-------------|------|-------------|
| `is_new_to_firm_x_has_series65` | INTEGER | is_new_to_firm × Has_Series_65 |
| `veteran_x_cfp` | INTEGER | is_veteran_advisor × Has_CFP |

### Engineered Features - Additional Derived
| Column Name | Type | Description |
|-------------|------|-------------|
| `Branch_Advisors_per_Firm_Association` | FLOAT | Number_BranchAdvisors / NumberFirmAssociations |

### Financial-Derived Features (NULL - Not Available in V6)
| Column Name | Type | Description |
|-------------|------|-------------|
| `AUM_per_Client` | FLOAT | NULL - Not available in V6 data |
| `AUM_per_IARep` | FLOAT | NULL - Not available in V6 data |
| `Clients_per_IARep` | FLOAT | NULL - Not available in V6 data |
| `Clients_per_BranchAdvisor` | FLOAT | NULL - Not available in V6 data |
| `Branch_Advisor_Density` | FLOAT | NULL - Not available in V6 data |
| `HNW_Client_Ratio` | FLOAT | NULL - Not available in V6 data |
| `HNW_Asset_Concentration` | FLOAT | NULL - Not available in V6 data |
| `Individual_Asset_Ratio` | FLOAT | NULL - Not available in V6 data |
| `Alternative_Investment_Focus` | FLOAT | NULL - Not available in V6 data |
| `Positive_Growth_Trajectory` | INTEGER | NULL - Not available in V6 data |
| `Accelerating_Growth` | INTEGER | NULL - Not available in V6 data |

**Note:** These fields were included in the schema for future compatibility but are set to NULL in V6 because financial metrics were not available in the Discovery Data snapshots.

### Metadata & Temporal Fields
| Column Name | Type | Description |
|-------------|------|-------------|
| `days_to_conversion` | INTEGER | Days between Stage_Entered_Contacting__c and Stage_Entered_Call_Scheduled__c (NULL if not converted) |
| `rep_snapshot_at` | DATE | Date of rep snapshot used (one of 8 historical dates) |
| `firm_snapshot_at` | DATE | Date of firm snapshot used (one of 8 historical dates) |
| `Stage_Entered_Contacting__c` | TIMESTAMP | Salesforce timestamp when lead entered "Contacting" stage |
| `Stage_Entered_Call_Scheduled__c` | TIMESTAMP | Salesforce timestamp when lead entered "Call Scheduled" stage (NULL if never scheduled) |

---

## Feature Categories Summary

### **Total Features: ~158 (excluding identifiers and metadata)**

1. **Financial Metrics:** 15 columns (AUM, client counts, asset breakdowns)
2. **Professional Metrics:** 6 columns (growth rates, associations)
3. **Tenure & Experience:** 8 columns (years at firm, prior firms)
4. **Professional Flags:** 17 binary columns (licenses, designations, status flags)
5. **Geographic & Location:** 4 columns (states, metro area, distance)
6. **Contact & Social:** 1 column (LinkedIn URL)
7. **Custodian Relationships:** 8 columns (AUM and flags for 4 major custodians)
8. **Registration:** 1 column (number of registered states)
9. **Firm-Level Aggregations:** 13 columns (firm size, growth, client metrics)
10. **Engineered - Maturity Proxies:** 8 columns (veteran, tenure, stability)
11. **Engineered - License Counts:** 2 columns (license_count, designation_count)
12. **Engineered - Geography:** 4 columns (remote work, local, mismatches)
13. **Engineered - Firm Context:** 1 column (firm size bin)
14. **Engineered - Contactability:** 3 columns (LinkedIn, email flags)
15. **Engineered - Missingness:** 7 columns (missing data indicators)
16. **Engineered - Interactions:** 2 columns (cross-feature combinations)
17. **Engineered - Additional:** 1 column (branch advisors per association)
18. **Financial-Derived (NULL):** 11 columns (placeholders for future data)

---

## Target Variable Definition

**`target_label`** (INTEGER, 0 or 1)

```sql
target_label = 1 IF (
    Stage_Entered_Call_Scheduled__c IS NOT NULL
    AND DATE(Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
)
ELSE 0
```

**Business Meaning:**
- **1 (Positive):** Lead scheduled a call within 30 days of entering "Contacting" stage
- **0 (Negative):** Lead did not schedule a call within 30 days (or never scheduled)

**Class Distribution:**
- Total samples: 41,942
- Positive samples: ~1,400-1,500 (estimated 3-4%)
- Negative samples: ~40,400-40,500 (estimated 96-97%)
- **Imbalance Ratio:** ~28:1 (highly imbalanced)

---

## Key Design Principles

### 1. **Point-in-Time (PIT) Correctness**
- Every feature reflects data that existed **at or before** the contact date
- Prevents data leakage from future information
- Each lead is matched to the nearest earlier snapshot

### 2. **No Silent Imputation**
- Missing data is flagged with explicit missingness indicators
- Never silently fill with zeros or means
- Model learns from missingness patterns

### 3. **Temporal Validity**
- Right-censored leads excluded (within last 30 days)
- Only complete conversion windows included
- Negative conversion times filtered out

### 4. **Feature Engineering Philosophy**
- **Maturity signals:** Veteran status, tenure, stability
- **Operational friction:** Geographic mismatches, remote work
- **Contactability:** LinkedIn, email presence
- **Professional sophistication:** License/designation counts
- **Firm context:** Size, growth, characteristics

---

## How V6 Was Used in Model Training

### Training Script: `unit_4_train_model_v6.py`

1. **Data Loading:**
   - Loaded from BigQuery table: `step_3_3_training_dataset_v6_20251104_2217`
   - Excluded PII columns (from `config/v6_pii_droplist.json`)
   - Excluded identifiers: `Id`, `FA_CRD__c`, `RIAFirmCRD`
   - Excluded metadata: `Stage_Entered_Contacting__c`, `rep_snapshot_at`, `firm_snapshot_at`, `days_to_conversion`

2. **Feature Selection:**
   - ~124-129 features used (after excluding metadata and PII)
   - All numeric and categorical features included
   - Categorical features one-hot encoded

3. **Time-Series Cross-Validation:**
   - Blocked time-series CV with 5 folds
   - 30-day gap between train and test sets
   - Prevents temporal leakage

4. **Class Balancing:**
   - Used `scale_pos_weight` parameter in XGBoost
   - Weight = (negative samples) / (positive samples) ≈ 27-28

5. **Model Training:**
   - XGBoost classifier with optimized hyperparameters
   - Baseline logistic regression for comparison
   - Feature importance analysis

### Model Performance (V6)
- **Test AUC-PR:** ~6.74% (baseline)
- **CV Mean:** ~6.74%
- **CV Stability:** 19.79% coefficient of variation

---

## Data Quality Checks

### Validation Assertions (All Passed)
1. ✅ No negative days_to_conversion
2. ✅ Rep match rate: ≥ 85% (97.4% achieved)
3. ✅ Firm match rate: ≥ 75% (97.4% achieved)
4. ✅ Snapshot date integrity: All dates valid
5. ✅ Point-in-time integrity: No post-contact features
6. ✅ Boolean domain validation: All flags are 0/1
7. ✅ Enum domain validation: firm_rep_count_bin valid
8. ✅ Missingness indicator validation: All flags are 0/1

---

## Limitations & Known Issues

1. **Financial Metrics Missing:**
   - AUM per client, efficiency ratios not available
   - Set to NULL in schema (included for future compatibility)

2. **High Class Imbalance:**
   - 28:1 negative to positive ratio
   - Requires careful class balancing techniques

3. **Email Fields:**
   - Email data not directly available
   - Using LinkedIn presence as proxy for contactability

4. **Geographic Granularity:**
   - Limited to state and metro area level
   - No city/county features (dropped as PII)

---

## Next Steps & Future Enhancements

1. **V7:** Added financial metrics from separate data source
2. **V8:** Cleaned and simplified feature set
3. **V9:** Attempted m5 replication with additional features
4. **V10:** Added Discovery data enrichment (with leakage issues fixed in V10_Fixed)

---

## References

- **Creation Script:** `step_3_2_create_training_dataset.py`
- **Training Script:** `unit_4_train_model_v6.py`
- **Documentation:** `V6_Historical_Data_Processing_Guide.md`
- **Feature Engineering:** `V6_Feature_Engineering_Review.md`

---

**Report Generated:** 2025-11-05  
**Table Version:** v6_20251104_2217  
**Total Columns:** 162  
**Total Rows:** 41,942

