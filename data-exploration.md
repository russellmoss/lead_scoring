# Data Exploration: Lead Scoring Model Data Sources

**Last Updated:** December 2025  
**Purpose:** Comprehensive documentation of data sources, structures, and definitions for building a machine learning lead scoring model.

---

## Table of Contents

1. [Overview](#overview)
2. [Salesforce Lead Data](#salesforce-lead-data)
3. [Funnel and Conversion Data](#funnel-and-conversion-data)
4. [FINTRX Data Sources](#fintrx-data-sources)
5. [Broker Protocol Data](#broker-protocol-data)
6. [Key Concepts and Definitions](#key-concepts-and-definitions)
7. [Data Relationships](#data-relationships)
8. [Feature Engineering Opportunities](#feature-engineering-opportunities)

---

## Overview

This document describes the data sources available for building a machine learning lead scoring model. The data ecosystem consists of:

- **Salesforce Lead Data**: Core lead records with contact information, status, and custom fields
- **Funnel Analytics**: Views tracking lead progression through stages (Contacted → MQL → SQL → SQO → Joined)
- **Conversion Rates**: Aggregated conversion metrics by cohort and dimension
- **FINTRX Data**: External data provider with firm and contact information, historical AUM, and relationships
- **Broker Protocol**: List of firms that are members of the Broker Protocol (enabling easier advisor transitions)

**Primary Goal**: Predict which leads will convert from "Contacted" to "MQL" (Marketing Qualified Lead) based on lead characteristics, firm data, and historical patterns.

---

## Salesforce Lead Data

### Table: `savvy-gtm-analytics.SavvyGTMData.Lead`

**Description**: Core Salesforce Lead object containing all lead records with contact information, status tracking, and custom fields.

**Row Count**: ~89,183 unique leads  
**Key Fields**:

#### Identity & Contact Information
- `Id` (STRING): Salesforce unique identifier
- `Full_prospect_id__c` (STRING): Composite key combining Salesforce ID and other identifiers
- `FirstName`, `LastName`, `Name`: Contact name fields
- `Email`, `MobilePhone`, `Phone`: Contact methods
- `Company`: Firm/company name
- `Title`: Job title

#### Dates & Timeline
- `CreatedDate` (TIMESTAMP): **When the lead was first created in Salesforce**
  - This is the original creation date, regardless of re-entry into the funnel
  - Use this for understanding when a lead was first discovered
  
- `Stage_Entered_New__c` (TIMESTAMP): When lead entered "New" stage
- `Stage_Entered_Contacting__c` (TIMESTAMP): **When lead entered "Contacting" stage (first contact attempt)**
  - This is the key date for measuring "Contacted" conversion
  - Used to calculate time-to-contact metrics
  
- `Stage_Entered_Call_Scheduled__c` (TIMESTAMP): When lead entered "Call Scheduled" stage (MQL)
- `Stage_Entered_Closed__c` (TIMESTAMP): When lead entered "Closed" stage
- `LastActivityDate` (DATE): Last activity on the lead record
- `LastModifiedDate` (TIMESTAMP): Last modification to any field

#### Status & Conversion
- `Status` (STRING): Current lead status (e.g., "New", "Contacting", "Call Scheduled", "Closed")
- `IsConverted` (BOOLEAN): Whether lead has been converted to Opportunity
- `ConvertedDate` (DATE): Date of conversion to Opportunity
- `ConvertedOpportunityId` (STRING): Linked Opportunity ID if converted
- `Disposition__c` (STRING): Final disposition/reason for closure

#### Firm & Professional Information
- `Firm_Website__c` (STRING): Firm website URL
- `Total_Firm_AUM__c` (FLOAT): Total assets under management at firm
- `Firm_Type__c` (STRING): Type of firm (e.g., "RIA", "BD", "Hybrid")
- `Custodian__c` (STRING): Primary custodian (e.g., "Fidelity", "Schwab")
- `FA_CRD__c` (STRING): Financial Advisor CRD number
- `Fintrx_Contact_CRD_ID__c` (STRING): FINTRX contact CRD ID (for joining to FINTRX data)
- `Fintrx_Url__c` (STRING): FINTRX profile URL

#### Professional Metrics
- `Years_as_a_Rep__c` (FLOAT): Years of experience as a representative
- `Years_at_Firm__c` (FLOAT): Years at current firm
- `Personal_AUM__c` (FLOAT): Personal assets under management
- `Estimated_Transferable_AUM__c` (FLOAT): Estimated AUM that could be transferred
- `Transferability_Probability__c` (STRING): Probability assessment of transferability
- `Average_AUM_at_Firm__c` (FLOAT): Average AUM per advisor at firm

#### Lead Source & Attribution
- `LeadSource` (STRING): Original lead source
- `Original_Source_Grouping__c` (STRING): Grouped source categories
- `Source_Channel_Mapping__c` (STRING): Channel mapping
- `Campaign__c` (STRING): Marketing campaign
- `UTM_Source_Last__c`, `UTM_Medium_Last__c`, `UTM_Campaign_Last__c`: UTM parameters
- `External_Agency__c` (STRING): External agency that generated the lead

#### Lead Scoring & Enrichment
- `Savvy_Lead_Score__c` (FLOAT): Current lead score (may be from previous model)
- `Lead_List_Name__c` (STRING): Which lead list this came from
- `Last_Enrichment_Date__c` (DATE): Last time lead data was enriched
- `Experimentation_Tag__c` (STRING): A/B testing tag

#### Other Custom Fields
- `Licenses__c` (STRING): Professional licenses held
- `LinkedIn_Profile_Apollo__c` (STRING): LinkedIn profile URL
- `Notes__c` (STRING): Internal notes
- `Next_Steps__c` (STRING): Next action items
- `Ready_for_Assignment__c` (BOOLEAN): Whether lead is ready for assignment

---

## Funnel and Conversion Data

### View: `savvy-gtm-analytics.savvy_analytics.vw_funnel_lead_to_joined_v2`

**Description**: Comprehensive funnel view that combines Lead and Opportunity data, tracking progression from initial contact through to "Joined" status.

**Row Count**: ~89,708 rows (includes both leads and opportunities)  
**Key Features**:
- Full outer join between Leads and Opportunities
- Calculated conversion flags for each stage
- FilterDate calculation for proper cohort attribution
- Unified view of lead lifecycle

#### Key Fields

##### Primary Keys
- `primary_key` (STRING): Composite key (uses `Full_prospect_id__c` or `Full_Opportunity_ID__c`)
- `sqo_primary_key` (STRING): Always uses Opportunity ID for SQO counting (ensures one SQO = one opportunity)
- `Full_prospect_id__c` (STRING): Lead ID
- `Full_Opportunity_ID__c` (STRING): Opportunity ID (if converted)

##### Funnel Stage Flags
- `is_contacted` (INTEGER): 1 if lead entered "Contacting" stage
- `is_mql` (INTEGER): 1 if lead entered "Call Scheduled" stage (MQL = Marketing Qualified Lead)
- `is_sql` (INTEGER): 1 if lead converted to Opportunity (SQL = Sales Qualified Lead)
- `is_sqo` (INTEGER): 1 if opportunity is marked as SQO (Sales Qualified Opportunity)
- `is_joined` (INTEGER): 1 if advisor joined (has `advisor_join_date__c`)

##### Stage Entry Timestamps
- `stage_entered_contacting__c` (TIMESTAMP): When lead entered "Contacting" stage
- `mql_stage_entered_ts` (TIMESTAMP): When lead entered "Call Scheduled" (MQL stage)
- `converted_date_raw` (DATE): When lead converted to Opportunity (SQL)
- `Date_Became_SQO__c` (TIMESTAMP): When opportunity became SQO

##### FilterDate - Critical for Cohort Analysis

**`FilterDate` (TIMESTAMP)**: **The most important date field for measuring conversions**

FilterDate is calculated as:
```sql
GREATEST(
  IFNULL(CreatedDate, TIMESTAMP('1900-01-01')),
  IFNULL(Stage_Entered_New__c, TIMESTAMP('1900-01-01')),
  IFNULL(Stage_Entered_Contacting__c, TIMESTAMP('1900-01-01'))
)
```

**What FilterDate Represents**:
- **For new leads**: FilterDate = CreatedDate (when first created)
- **For recycled leads**: FilterDate = most recent of CreatedDate, Stage_Entered_New__c, or Stage_Entered_Contacting__c
- **Purpose**: Captures when a lead **re-enters the funnel** after being recycled

**Why FilterDate Matters**:
- Handles lead recycling: If a lead is closed and then re-opened, FilterDate updates to the re-entry date
- Ensures accurate conversion attribution: Only count conversions that happened **after** FilterDate
- Prevents double-counting: A lead that converts after re-entry is attributed to the re-entry cohort, not the original creation date

**Example Scenario**:
1. Lead created on 2024-01-01 (CreatedDate = 2024-01-01, FilterDate = 2024-01-01)
2. Lead contacted, no response, closed on 2024-02-01
3. Lead recycled and re-entered "New" stage on 2024-06-01 (Stage_Entered_New__c = 2024-06-01)
4. FilterDate updates to 2024-06-01 (the re-entry date)
5. Lead contacted again on 2024-06-15 (Stage_Entered_Contacting__c = 2024-06-15)
6. FilterDate updates to 2024-06-15 (most recent)
7. If lead converts to MQL on 2024-06-20, it's attributed to the June 2024 cohort (FilterDate), not January 2024

##### Conversion Status Fields
- `TOF_Stage` (STRING): Top-of-funnel stage ("MQL", "SQL", "SQO", "Joined")
- `Conversion_Status` (STRING): Overall status ("Open", "Closed", "Joined")
- `MQL_conversion_status` (STRING): MQL-specific status ("Converted", "Closed", "Open", "Stage not entered")
- `SQL_conversion_status` (STRING): SQL-specific status ("Converted", "Closed Lost", "Open")

##### Owner & Attribution
- `SGA_Owner_Name__c` (STRING): Sales Growth Advisor owner name
- `sgm_name` (STRING): Sales Growth Manager name
- `Original_source` (STRING): Original lead source
- `Channel_Grouping_Name` (STRING): Grouped channel name

##### Opportunity Fields (if converted)
- `Opp_Name` (STRING): Opportunity name
- `Opportunity_AUM` (FLOAT): AUM value from opportunity
- `StageName` (STRING): Current opportunity stage
- `CloseDate` (DATE): Opportunity close date
- `advisor_join_date__c` (DATE): Date advisor joined (final conversion)

---

### View: `savvy-gtm-analytics.savvy_analytics.vw_conversion_rates`

**Description**: Aggregated conversion rate metrics by cohort month and various dimensions (SGA, SGM, Source, Channel, etc.)

**Purpose**: Provides pre-calculated conversion rates for analysis and reporting.

#### Key Fields

##### Cohort Dimensions
- `cohort_month` (DATE): Primary cohort month (uses FilterDate)
- `created_cohort_month` (DATE): Cohort based on CreatedDate
- `filter_date_cohort_month` (DATE): **Cohort based on FilterDate (handles recycled leads)**
- `contacted_cohort_month` (DATE): Cohort based on when contacted
- `mql_cohort_month` (DATE): Cohort based on when became MQL
- `sql_cohort_month` (DATE): Cohort based on when became SQL
- `sqo_cohort_month` (DATE): Cohort based on when became SQO

##### Conversion Rate Components

**Pre-SQO Conversion Rates** (Lead-based, use SUM):
- `created_volume` / `created_denominator`: Total leads created
- `contacted_volume` / `contacted_denominator`: Leads that were contacted
- `mql_volume` / `mql_denominator`: Leads that became MQL
- `sql_volume` / `sql_denominator`: Leads that converted to SQL

**Conversion Numerators**:
- `created_to_contacted_numerator`: Created → Contacted
- `contacted_to_mql_numerator`: **Contacted → MQL (key metric for lead scoring)**
- `mql_to_sql_numerator`: MQL → SQL
- `sql_to_sqo_numerator`: SQL → SQO

**Post-SQO Conversion Rates** (Opportunity-based, use COUNT DISTINCT):
- `sqo_volume` / `sqo_denominator`: Opportunities that became SQO
- `discovery_volume` / `discovery_denominator`: Entered Discovery stage
- `sales_process_volume` / `sales_process_denominator`: Entered Sales Process
- `negotiating_volume` / `negotiating_denominator`: Entered Negotiating
- `signed_volume` / `signed_denominator`: Entered Signed stage

**Key Insight**: The view uses different aggregation methods:
- **Pre-SQO stages** (Created, Contacted, MQL, SQL): Use `SUM()` because leads can be counted multiple times
- **Post-SQO stages** (SQO, Discovery, etc.): Use `COUNT(DISTINCT Full_Opportunity_ID__c)` because one opportunity = one SQO

---

## FINTRX Data Sources

FINTRX is an external data provider that enriches lead data with firm and contact information, historical AUM data, and relationship mappings.

### Table: `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`

**Description**: Current snapshot of all RIA contacts (advisors/reps) with comprehensive profile information.

**Row Count**: ~788,154 contacts  
**Key Fields**:

#### Identity
- `RIA_CONTACT_CRD_ID` (INTEGER): Unique CRD identifier for the contact
- `CONTACT_FIRST_NAME`, `CONTACT_LAST_NAME`: Name fields
- `EMAIL`, `MOBILE_PHONE_NUMBER`, `OFFICE_PHONE_NUMBER`: Contact information
- `LINKEDIN_PROFILE_URL` (STRING): LinkedIn profile URL
- `FINTRX_URL` (STRING): FINTRX profile URL

#### Professional Information
- `TITLE_NAME` (STRING): Job title
- `CONTACT_BIO` (STRING): Professional biography (useful for extracting certifications, experience)
- `REP_LICENSES` (STRING): Professional licenses (e.g., "Series 65", "Series 7", "CFP", "CFA")
- `INDUSTRY_EXAMS` (STRING): Industry certifications and exams
- `INDUSTRY_TENURE_MONTHS` (INTEGER): Months of industry experience
- `REP_AUM` (INTEGER): Representative's AUM

#### Firm Association
- `PRIMARY_FIRM` (INTEGER): Primary firm CRD ID
- `PRIMARY_FIRM_NAME` (STRING): Primary firm name
- `PRIMARY_RIA` (INTEGER): Primary RIA CRD ID
- `PRIMARY_BD` (INTEGER): Primary BD CRD ID
- `RIA_INVESTOR_CRD_ID` (STRING): RIA firm CRD ID (may differ from PRIMARY_RIA)
- `RIA_INVESTOR_NAME` (STRING): RIA firm name
- `PRIMARY_FIRM_START_DATE` (DATE): When contact started at primary firm
- `LATEST_REGISTERED_EMPLOYMENT_COMPANY_CRD_ID` (INTEGER): Latest employer CRD ID
- `LATEST_REGISTERED_EMPLOYMENT_START_DATE` (DATE): Latest employment start date

#### Ownership & Role
- `CONTACT_OWNERSHIP_PERCENTAGE` (STRING): Ownership percentage in firm (e.g., "25-50%", "50-75%")
- `CONTACT_ROLES` (STRING): Roles within the firm
- `INVESTMENT_COMMITTEE_MEMBER` (BOOLEAN): Whether on investment committee
- `PRODUCING_ADVISOR` (BOOLEAN): **Whether contact is a producing advisor (key filter for lead scoring)**

#### Firm Characteristics (Denormalized)
- `PRIMARY_FIRM_TOTAL_AUM` (INTEGER): Total AUM at primary firm
- `PRIMARY_FIRM_EMPLOYEE_COUNT` (INTEGER): Employee count at primary firm
- `PRIMARY_FIRM_CLASSIFICATION` (STRING): Firm classification (e.g., "Independent RIA")

#### Location
- `PRIMARY_LOCATION_CITY`, `PRIMARY_LOCATION_STATE`, `PRIMARY_LOCATION_POSTAL`: Primary location
- `BRANCH_CITIES`, `BRANCH_STATES`: Additional branch locations

#### Regulatory & Disclosures
- `CONTACT_HAS_DISCLOSED_BANKRUPT` (BOOLEAN): Bankruptcy disclosure
- `CONTACT_HAS_DISCLOSED_REGULATORY_EVENT` (BOOLEAN): Regulatory event disclosure
- `CONTACT_HAS_DISCLOSED_CUSTOMER_DISPUTE` (BOOLEAN): Customer dispute disclosure
- Various other disclosure flags

#### Status
- `ACTIVE` (BOOLEAN): Whether contact is currently active
- `LATEST_UPDATE` (TIMESTAMP): Last update timestamp

**Join Key**: Use `Fintrx_Contact_CRD_ID__c` from Lead table to join on `RIA_CONTACT_CRD_ID`

---

### Table: `savvy-gtm-analytics.FinTrx_data.ria_contact_firm_relationships`

**Description**: Many-to-many relationship table linking contacts to firms (a contact can be associated with multiple firms).

**Row Count**: ~914,394 relationships  
**Key Fields**:
- `RIA_CONTACT_CRD_ID` (INTEGER): Contact CRD ID
- `RIA_INVESTOR_CRD_ID` (INTEGER): Firm CRD ID

**Use Case**: Find all firms a contact has been associated with, or all contacts at a firm.

---

### Table: `savvy-gtm-analytics.FinTrx_data.Firm_historicals`

**Description**: Historical monthly snapshots of firm AUM and client composition data.

**Row Count**: ~926,712 rows (multiple months per firm)  
**Key Fields**:

#### Time Dimensions
- `RIA_INVESTOR_CRD_ID` (INTEGER): Firm CRD ID
- `MONTH` (INTEGER): Month (1-12)
- `YEAR` (INTEGER): Year
- `QUARTER` (INTEGER): Quarter (1-4)

#### AUM Metrics
- `TOTAL_AUM` (INTEGER): Total assets under management
- `DISCRETIONARY_AUM` (INTEGER): Discretionary AUM
- `NON_DISCRETIONARY_AUM` (INTEGER): Non-discretionary AUM

#### Client Counts
- `TOTAL_ACCOUNTS` (INTEGER): Total number of accounts
- `TOTAL_DISCRETIONARY_ACCOUNTS` (INTEGER): Discretionary accounts
- `TOTAL_NON_DISCRETIONARY_ACCOUNTS` (INTEGER): Non-discretionary accounts

#### Client Composition by Type
- `NUM_OF_CLIENTS_HIGH_NET_WORTH_INDIVIDUALS` (INTEGER): HNW client count
- `AMT_OF_AUM_HIGH_NET_WORTH_INDIVIDUALS` (INTEGER): HNW AUM amount
- `NUM_OF_CLIENTS_NON_HIGH_NET_WORTH_INDIVIDUALS` (INTEGER): Non-HNW client count
- `AMT_OF_AUM_NON_HIGH_NET_WORTH_INDIVIDUALS` (INTEGER): Non-HNW AUM amount
- Additional client type breakdowns (banks, investment companies, pension plans, etc.)

**Use Case**: 
- Calculate firm growth trends (AUM change over time)
- Identify firms with high HNW concentration
- Calculate firm stability metrics (AUM volatility, client retention)

**Point-in-Time Considerations**: When building features, use only data from months **before** the `FilterDate` to prevent data leakage.

---

## Broker Protocol Data

### Table: `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`

**Description**: List of firms that are members of the Broker Protocol, which enables advisors to transition more easily between firms.

**Row Count**: ~2,587 firms  
**Key Fields**:

- `broker_protocol_firm_name` (STRING): Firm name from Broker Protocol list
- `firm_crd_id` (INTEGER): Matched FINTRX firm CRD ID
- `fintrx_firm_name` (STRING): Matched FINTRX firm name
- `is_current_member` (BOOLEAN): Whether firm is currently a member
- `date_joined` (DATE): Date firm joined Broker Protocol
- `date_withdrawn` (DATE): Date firm withdrew (if applicable)
- `match_confidence` (FLOAT): Confidence score of the match between Broker Protocol and FINTRX
- `match_method` (STRING): Method used to match firms

**Use Case**: 
- Identify leads from Broker Protocol firms (may indicate higher transition probability)
- Feature: `is_broker_protocol_firm` (BOOLEAN)

---

## Key Concepts and Definitions

### Funnel Stages

1. **Created**: Lead record created in Salesforce
2. **Contacted**: Lead entered "Contacting" stage (first outreach attempt)
3. **MQL (Marketing Qualified Lead)**: Lead entered "Call Scheduled" stage (showed interest)
4. **SQL (Sales Qualified Lead)**: Lead converted to Opportunity
5. **SQO (Sales Qualified Opportunity)**: Opportunity marked as qualified
6. **Joined**: Advisor actually joined Savvy (final conversion)

### Key Dates

- **CreatedDate**: Original creation date in Salesforce (doesn't change)
- **FilterDate**: When lead re-entered the funnel (handles recycling)
  - For new leads: FilterDate = CreatedDate
  - For recycled leads: FilterDate = most recent of (CreatedDate, Stage_Entered_New__c, Stage_Entered_Contacting__c)
- **Stage_Entered_Contacting__c**: When lead entered "Contacting" stage (first contact)

### Conversion Metrics

- **Contacted → MQL Conversion Rate**: Primary metric for lead scoring model
  - Numerator: Leads that became MQL after being contacted
  - Denominator: Leads that were contacted (based on FilterDate cohort)
  - **Critical**: Only count MQLs that occurred **after** FilterDate to handle recycled leads correctly

### Data Quality Considerations

- **Point-in-Time (PIT) Methodology**: When building features, only use data that was available **at the time of contact** (FilterDate)
  - Example: Don't use firm AUM from December 2025 if the lead was contacted in January 2025
  - Use historical snapshots from Firm_historicals with appropriate date filters

- **Missing Data**: 
  - Not all leads have FINTRX matches (Fintrx_Contact_CRD_ID__c may be NULL)
  - Some leads may not have firm information
  - Handle NULLs appropriately in feature engineering

---

## Data Relationships

### Primary Join Paths

1. **Lead → FINTRX Contact**:
   ```
   Lead.Fintrx_Contact_CRD_ID__c = ria_contacts_current.RIA_CONTACT_CRD_ID
   ```

2. **FINTRX Contact → Firm Historicals**:
   ```
   ria_contacts_current.PRIMARY_FIRM = Firm_historicals.RIA_INVESTOR_CRD_ID
   ```
   (Also filter by YEAR/MONTH for point-in-time data)

3. **Lead → Broker Protocol**:
   ```
   Lead.Company = broker_protocol_members.broker_protocol_firm_name
   ```
   (May require fuzzy matching or use firm_crd_id if available)

4. **Contact → Firm Relationships**:
   ```
   ria_contacts_current.RIA_CONTACT_CRD_ID = ria_contact_firm_relationships.RIA_CONTACT_CRD_ID
   ```

### Data Availability

- **~89,183 leads** in Salesforce
- **~57,576 leads contacted** (64.6%)
- **~3,413 MQLs** (5.9% of contacted, 3.8% of all leads)
- **~1,414 SQLs** (41.4% of MQLs)
- **~815 SQOs** (57.6% of SQLs)
- **~106 Joined** (13.0% of SQOs)

**Overall Funnel Conversion**:
- Created → Contacted: 64.6%
- Contacted → MQL: 5.9% (target for lead scoring)
- MQL → SQL: 41.4%
- SQL → SQO: 57.6%
- SQO → Joined: 13.0%

---

## Feature Engineering Opportunities

### Lead-Level Features

1. **Temporal Features**:
   - Days between CreatedDate and FilterDate (recycled lead indicator)
   - Days between FilterDate and Stage_Entered_Contacting__c
   - Day of week, month, quarter of contact
   - Time of year (Q1, Q2, Q3, Q4)

2. **Source & Attribution**:
   - Lead source category (grouped)
   - Channel type (paid, organic, referral, etc.)
   - Campaign name
   - UTM parameters

3. **Professional Characteristics** (from Lead or FINTRX):
   - Years of experience
   - Years at current firm
   - Title category (owner, advisor, support, etc.)
   - Certifications (CFP, CFA, Series 65, Series 7)
   - Licenses count

4. **Firm Characteristics** (from FINTRX):
   - Firm AUM (at time of contact)
   - Firm employee count
   - Firm type (RIA, BD, Hybrid)
   - Custodian
   - Firm growth rate (AUM change over 12 months)
   - Firm stability (AUM volatility)
   - HNW client concentration
   - Broker Protocol membership

5. **Contact Quality Indicators**:
   - Has LinkedIn profile
   - Has email
   - Has mobile phone
   - Email verified
   - Data completeness score

6. **Historical Performance** (aggregated):
   - Average conversion rate for similar leads (by source, firm type, etc.)
   - SGA owner historical performance
   - Firm-level historical conversion rate

### Target Variable

**Primary Target**: `is_mql` (binary)
- 1 if lead became MQL after being contacted
- 0 if lead was contacted but did not become MQL
- **Exclude**: Leads that were not contacted (is_contacted = 0)

**Secondary Targets** (for multi-stage modeling):
- `is_sql`: Converted to SQL
- `is_sqo`: Converted to SQO
- `is_joined`: Final conversion

### Feature Engineering Best Practices

1. **Point-in-Time Enforcement**: 
   - Always filter historical data by date < FilterDate
   - Use Firm_historicals with appropriate YEAR/MONTH filters

2. **Handle Missing Data**:
   - Create "missing" indicators for important features
   - Impute with median/mode or create "unknown" categories

3. **Categorical Encoding**:
   - One-hot encode low-cardinality categories
   - Target encode high-cardinality categories (with proper cross-validation)

4. **Temporal Aggregations**:
   - Calculate rolling averages, trends, and volatility
   - Use appropriate lookback windows (3mo, 6mo, 12mo)

5. **Interaction Features**:
   - Firm AUM × Years at Firm
   - Title × Firm Type
   - Source × Channel

---

## Next Steps for Model Development

1. **Data Preparation**:
   - Create point-in-time feature extraction query
   - Join Lead → FINTRX Contact → Firm Historicals
   - Calculate temporal and aggregated features

2. **Target Definition**:
   - Filter to contacted leads (is_contacted = 1)
   - Define positive class: is_mql = 1 AND mql_stage_entered_ts >= FilterDate
   - Define negative class: is_contacted = 1 AND is_mql = 0

3. **Train/Test Split**:
   - Use FilterDate for temporal split (e.g., train on 2024, test on 2025)
   - Ensure no data leakage (all features must be from before FilterDate)

4. **Feature Selection**:
   - Start with high-signal features (firm AUM, title, source, certifications)
   - Add interaction features
   - Use feature importance to identify key predictors

5. **Model Evaluation**:
   - Focus on precision at top deciles (top 10% of leads)
   - Measure lift over baseline conversion rate
   - Track conversion rate by predicted score decile

---

## Appendix: Quick Reference

### Key Tables and Views

| Table/View | Purpose | Row Count | Key Join Field |
|------------|---------|-----------|----------------|
| `SavvyGTMData.Lead` | Core lead records | ~89K | `Full_prospect_id__c` |
| `savvy_analytics.vw_funnel_lead_to_joined_v2` | Funnel tracking | ~90K | `primary_key` |
| `savvy_analytics.vw_conversion_rates` | Aggregated rates | Varies | Cohort dimensions |
| `FinTrx_data.ria_contacts_current` | Contact profiles | ~788K | `RIA_CONTACT_CRD_ID` |
| `FinTrx_data.Firm_historicals` | Historical AUM | ~927K | `RIA_INVESTOR_CRD_ID` |
| `FinTrx_data.ria_contact_firm_relationships` | Contact-firm links | ~914K | `RIA_CONTACT_CRD_ID` |
| `SavvyGTMData.broker_protocol_members` | Protocol firms | ~2.6K | `firm_crd_id` |

### Critical Fields for Lead Scoring

- **FilterDate**: When lead re-entered funnel (for cohort attribution)
- **Stage_Entered_Contacting__c**: When first contacted
- **is_mql**: Target variable (1 = converted to MQL)
- **PRODUCING_ADVISOR**: Filter (only include producing advisors)
- **Fintrx_Contact_CRD_ID__c**: Join key to FINTRX data

---

**Document Version**: 1.0  
**Last Updated**: December 2025  
**Maintained By**: Data Science Team

