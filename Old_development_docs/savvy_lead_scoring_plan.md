# Project Documentation: Focused Lead Scoring Engine (Contacted → MQL)

**Version:** 2.1  
**Date:** October 26, 2025  
**Audience:** Sales Growth Advisors (SGAs), RevOps, Data/Analytics, Engineering  
**Authoring Note:** This document is intentionally prescriptive and "step-by-step friendly" so an analyst or RevOps partner can execute with an LLM as a copilot. Each phase includes **LLM QA/QC prompts** and **checklists** to reduce execution risk.

---

## 0) Terminology & Data Sources

**Standardized Naming Convention:**
- **Salesforce CRM** - Lead records, conversion tracking, contact history
- **MarketPro Raw Data** - Vendor CSV exports from MarketPro portal (T1/T2/T3 territories)
- **Discovery Features** - 69 engineered features derived from MarketPro Raw Data (67 discovery + 2 temporal)
- **Lead Scoring Model** - XGBoost classifier predicting Contacted → MQL conversion

**Data Flow:**
1. **MarketPro Raw Data** (monthly CSV uploads) → BigQuery staging tables
2. **Salesforce CRM** (daily sync) → BigQuery lead tables  
3. **Discovery Features** (engineered from MarketPro) → Model training/scoring
4. **Lead Scores** (model output) → Salesforce field updates

---

## 1) Executive Summary

We are implementing a **single, high-leverage lead scoring model** that predicts whether a **Contacted** lead will become an **MQL** (i.e., will schedule an initial discovery call).

- **Why:** The biggest funnel bottleneck is **Contacted → MQL (~6%)**. Improving prioritization here yields the largest near-term impact on MQL volume and SGA efficiency.
- **What:** A daily-refreshed **XGBoost classifier** (or BigQuery ML XGBoost equivalent) scoring all *open, contacted* leads, outputting a **probability** and a **Tier (A/B/C)** based on SGA capacity.
- **How:** A lean, governed workflow in **BigQuery + Vertex AI** with strong **drift monitoring**, **calibrated thresholds**, and a **lead-level randomized A/B test** to prove business impact.
- **Enhanced Data:** Leveraging **69 engineered features** from discovery data including firmographics, growth metrics, operational indicators, and temporal contact patterns to significantly improve prediction accuracy.

**Scope Trim:** This plan focuses **only** on Contacted → MQL. Downstream stages (MQL→SQL, SQL→SQO, SQO→Joined) are out of scope until this model delivers proven ROI.

---

## 2) Problem & Definitions

### Problem Statement
Given a lead that has been **Contacted** (one-way outreach initiated), predict whether that lead will become an **MQL** (call scheduled) within a defined outcome window.

### Key Definitions
- **Contacted:** `stage_entered_contacting__c IS NOT NULL` (SGA initiated outreach).  
- **MQL:** `Stage_Entered_Call_Scheduled__c IS NOT NULL` (call scheduled).  
- **Outcome Window:** Default **30 days** from Contacted timestamp (configurable). Positives must meet MQL within the window.
- **Positive Class Rate:** Historically ~6% of contacted leads become MQLs.

### Out of Scope
- Predicting Contacted itself (operational).  
- Post-MQL stages (SQL, SQO, Joined).  
- Re-engagement opportunities without a lead (different process dynamics).

---

## 3) North-Star Metrics & Targets

- **Primary Online Metric:** `AUC-PR` (area under precision-recall) on a **temporal holdout**.
- **Primary Business Metric:** **MQLs per 100 dials** (lead-level randomized test; normalized for lead mix) and **MQLs per SGA day**.
- **Adoption Metric:** % of SGA call attempts executed in **Tier order**.
- **Target (Hypothesis):** +50% lift in **MQLs/100 dials** for treatment vs control at p<0.05.

---

## 4) Architecture (Hybrid Data Strategy)

### 4.1 Data Architecture Overview
**Hybrid Approach:** Salesforce real-time + Discovery Data batch enrichment

1. **Salesforce Data:** Real-time sync to BigQuery (hourly/daily)
2. **Discovery Data:** Batch enrichment (weekly/monthly) stored in BigQuery
3. **Model Scoring:** Daily batch processing with cached Discovery Data
4. **Salesforce Updates:** Real-time score updates via API

**BigQuery Dataset Structure:**
```
savvy-gtm-analytics.LeadScoring          # Core CRM data (existing)
├── Account, Channel_group, Contact, Lead, Opportunity, etc.

savvy-gtm-analytics.LeadScoring            # Lead scoring processing
├── staging_discovery_t1                   # Monthly T1 CSV upload
├── staging_discovery_t2                   # Monthly T2 CSV upload  
├── staging_discovery_t3                   # Monthly T3 CSV upload
├── discovery_reps_current                 # Processed MarketPro Raw Data
├── discovery_firms_current                # Processed firm data
├── lead_scores_current                   # Daily model scores
├── model_performance_log                  # Model monitoring
└── model_artifacts                       # Trained models, feature importance, etc.
```

**Key Benefits:**
- **Clean Separation**: Core CRM data separate from ML processing
- **Organized Processing**: All lead scoring tables grouped together
- **Scalable**: Room for future ML models and analytics
- **Existing Permissions**: Leverages current BigQuery access controls

### 4.2 Data Flow Strategy

### 4.2 Data Flow Strategy (REVISED - Monthly Batch)

**Salesforce → BigQuery (Daily)**
- **Frequency:** Daily full refresh of Lead object
- **Tables:** `savvy_analytics.sfdc_leads_current`
- **Key Fields:** All Lead object fields + conversion tracking
- **Cost:** ~$30-50/month for 70K records
- **Process:** Automated daily sync via Salesforce API

**Discovery Data → BigQuery (Monthly Manual)**
- **Frequency:** Monthly manual upload (T1/T2/T3 territory exports)
- **Tables:** `savvy_analytics.discovery_reps_current`, `savvy_analytics.discovery_firms_current`
- **Key Fields:** All 69 discovery features + CRD mappings
- **Cost:** ~$10-20/month for discovery data storage
- **Process:** Manual CSV upload → BigQuery processing

**Model Scoring Pipeline (Daily)**
- **Input:** Latest Salesforce + Cached Discovery Data (monthly refresh)
- **Output:** `savvy_analytics.lead_scores` table
- **Salesforce Sync:** Daily score updates via Bulk API
- **Process:** BigQuery stitches Discovery Data to Salesforce entries via CRD matching

### 4.3 Why NOT Salesforce-Only Approach

**Discovery Data in Salesforce (NOT RECOMMENDED):**
❌ **Field Limits:** 69 discovery fields would consume significant custom field capacity
❌ **Data Freshness:** Monthly manual CSV uploads would still be required, but with Salesforce field limitations
❌ **Storage Costs:** Salesforce storage is expensive (~$125/GB/month)
❌ **API Limits:** Bulk updates would hit Salesforce API limits
❌ **Maintenance:** Manual field management and data quality issues
❌ **Processing Complexity:** Would still need BigQuery for complex feature engineering

**BigQuery Hybrid (RECOMMENDED):**
✅ **Cost Effective:** ~$100/month vs $500+/month in Salesforce
✅ **Data Freshness:** Monthly manual Discovery Data refresh (T1/T2/T3 CSV uploads)
✅ **Scalability:** No field limits, unlimited storage
✅ **Performance:** Fast queries and model scoring
✅ **Flexibility:** Easy to add new discovery features
✅ **Manual Control:** Monthly CSV uploads allow data quality review before processing

---

## 5) Data & Feature Engineering (Leakage-Aware)

### 5.0 Multi-Source Data Aggregation & Reconciliation Pipeline

#### 5.0.1 Data Source Integration Architecture
Our lead scoring model requires sophisticated data preparation from **three primary sources** with complex reconciliation and quality assurance processes:

**Primary Data Sources:**
1. **Salesforce CRM** - Lead records, conversion tracking, contact history
2. **MarketPro Raw Data** - RIA representative and firm data (vendor CSV exports)
3. **Discovery Features** - Engineered features derived from MarketPro data

#### 5.0.2 Salesforce Data Extraction Process
```sql
-- Comprehensive lead data extraction with all required fields
SELECT Address, City, Company, Conversion_Channel__c, ConvertedDate,
    ConvertedOpportunityId, CreatedDate, Disposition__c, Email, 
    Experimentation_Tag__c, External_Agency__c, FA_CRD__c, FirstName, 
    Full_Prospect_ID__c, IsConverted, LastActivityDate, LastModifiedDate, 
    LastName, LeadSource, Lead_List_Name__c, LinkedIn_Profile_Apollo__c, 
    MobilePhone, Mobile_Phone_2__c, Name, Savvy_Lead_Score__c, 
    Stage_Entered_Contacting__c, Stage_Entered_Call_Scheduled__c, State, 
    Status, Title, OwnerId, Owner.Name
FROM Lead
WHERE Stage_Entered_Contacting__c IS NOT NULL
```

**Key Requirements:**
- Handle Salesforce API rate limiting and pagination
- Extract ~70K lead records with comprehensive attributes
- Implement robust error handling for API failures
- Store raw data with timestamps for auditability

#### 5.0.3 MarketPro Raw Data Processing Pipeline
**Multi-Territory Data Handling:**
Due to MarketPro's bulk download limitations, data must be exported from three geographic territories:
- **T1 (Eastern US)** - New York, Florida, Northeast
- **T2 (Central US)** - Texas, Illinois, Midwest  
- **T3 (Western US)** - California, Washington, West Coast

**Data Processing Steps:**
1. **File Discovery & Validation:**
   - Scan `data/raw_discovery_data/` directory for CSV files
   - Validate file integrity and format consistency
   - Log processing statistics for each territory

2. **Type Inference & Alignment:**
   - Use `low_memory=False` for proper type inference
   - Standardize NA values: `['', 'NA', 'N/A', 'null', 'NULL', 'None']`
   - Align data types across all CSV files before concatenation
   - Handle mixed data types and format inconsistencies

3. **Concatenation & Deduplication:**
   - Concatenate all territory files with proper type handling
   - Remove duplicates based on RepCRD and RIAFirmCRD
   - Generate comprehensive data quality reports

#### 5.0.4 Advanced Data Reconciliation Process
**Three-Stage Merge Strategy:**

**Stage 1: Salesforce + Representatives Merge**
- Join Keys: `FA_CRD__c` (Salesforce) ↔ `RepCRD` (MarketPro Raw Data)
- Join Type: OUTER JOIN to capture all records
- Success Target: >70% Salesforce record match rate
- Quality Checks: Validate CRD number consistency

**Stage 2: Add Firm Data**
- Join Keys: `RIAFirmCRD` (from both datasets)
- Join Type: OUTER JOIN for comprehensive coverage
- Success Target: >80% representative records with firm data
- Quality Checks: Validate firm data completeness

**Stage 3: Missing CRD Reconciliation**
- Identify CRDs in Salesforce missing from initial MarketPro export
- Perform targeted MarketPro searches using "Rep CRD" field
- Complete dataset with additional representative records
- Generate reconciliation success reports

#### 5.0.5 Comprehensive Data Quality Assurance
**Multi-Level Validation Framework:**

**Data Completeness Checks:**
- CRD number coverage across all sources
- Required field population rates
- Cross-source data consistency validation
- Temporal data freshness verification

**Data Quality Metrics (DEVELOPMENT-BASELINE):**
- Join success rates by source and territory: **100% of MarketPro records matched, with 8.8% matching duplicate SFDC entries**
- Missing value analysis by feature category: **<5% null rate on key features in development**
- Outlier detection and handling strategies: **Implemented with correlation thresholds in development**
- Data type consistency validation: **Multi-CSV type alignment pipeline in development**
- **Record Processing:** 509,851 total records successfully processed in development
- **Duplicate Rate:** <0.1% CRD duplicates in Salesforce data (development model)
- **Territory Coverage:** T1/T2/T3 Discovery Data coverage variance monitoring (development)

**Reconciliation Reporting:**
- Salesforce-centric success rates
- Discovery data coverage analysis
- Missing record identification and resolution
- Data quality scorecards by territory

### 5.1 Advanced Data Cleaning & Preprocessing

#### 5.1.1 Column Deduplication & Merging (DEVELOPMENT-VALIDATED)
**Suffix-Based Column Grouping:**
- Identify columns with suffixes: `['_sf', '_rep', '_firm', '_merge1', '_ddrep', '_ddfirm']`
- Group related columns by base name for intelligent merging
- Remove identical columns (correlation = 0.9999) - **VALIDATED IN DEVELOPMENT MODEL**
- Handle highly correlated columns (threshold = 0.98) - **PROVEN EFFECTIVE IN DEVELOPMENT**
- **Advanced Correlation Detection:** Automatically detect and merge columns with >98% correlation
- **Intelligent Column Selection:** Choose best column based on missing values, variance, and column name length

**Column Selection Logic:**
- Choose best column based on: missing values, variance, column name length
- Rename single remaining columns to clean base names
- Generate detailed cleaning reports with transformation logs

#### 5.1.2 Data Type Standardization
**Numeric Conversion Pipeline:**
- Clean currency symbols ($), commas, percentage signs, spaces
- Convert text objects to numerical types with error handling
- Apply consistent data types across all merged datasets
- Handle edge cases: negative values, zero denominators, null inputs

**Boolean Conversion Framework:**
- Convert Yes/No fields to boolean with proper null handling
- Map categorical values to boolean indicators
- Create derived boolean features from continuous variables
- Ensure consistent boolean encoding across sources

**Datetime Processing:**
- Convert datetime fields with timezone normalization
- Handle multiple datetime formats and timezone conversions
- Create temporal features (days since, time differences)
- Ensure no future data leakage in temporal features

#### 5.1.3 Duplicate Handling Strategy (DEVELOPMENT-IMPLEMENTED)
**Multi-Level Duplicate Detection:**
- **CRD-Level Duplicates:** Remove duplicates based on `FA_CRD__c` after merge operations
- **Record-Level Duplicates:** Handle duplicates from feature engineering with `drop_duplicates(subset=['RepCRD', 'RIAFirmCRD', 'FA_CRD__c'])`
- **Column-Level Duplicates:** Remove identical columns (correlation > 0.9999) and highly correlated columns (>0.98)
- **Territory-Level Duplicates:** Handle overlapping records across T1/T2/T3 Discovery Data exports

**Duplicate Resolution Logic:**
- **Salesforce Duplicates:** Keep most recent record by `LastModifiedDate`
- **Discovery Data Duplicates:** Keep record with most complete data (fewest nulls)
- **Merge Duplicates:** Use intelligent column selection based on data quality metrics

#### 5.1.4 Missing Value Handling Strategy
**Sophisticated Imputation Pipeline:**
- Use IterativeImputer for advanced missing value imputation
- Apply StandardScaler for numerical features
- Implement feature-specific imputation strategies:
  - Firmographics: Impute with segment medians
  - Growth metrics: Flag as "Unknown" category
  - Efficiency metrics: Derive only when denominators > 0

**Class Imbalance Management:**
- Apply SMOTE (Synthetic Minority Over-sampling Technique)
- Use `scale_pos_weight` for XGBoost class balancing
- Implement stratified sampling for train/test splits
- Monitor class distribution across feature segments

### 5.2 New Salesforce Fields (MarketPro → Lead/Contact)
To strengthen prediction at **Contacted → MQL**, we are **adding and standardizing** the following MarketPro-derived fields on the **Lead/Contact** object. All fields must be stamped with a **source timestamp** (`MarketPro_Last_Updated__c`) and are **read-only** for SGAs.

| Group | API Field | Type (SFDC) | Example | Why It Matters (Signal) |
| :--- | :--- | :--- | :--- | :--- |
| Propensity/Agitation | `Years_at_Firm__c` | Number(2,0) | 5 | Non-linear churn risk windows (3–7 years sweet spot; 15+ years low-propensity). |
| Propensity/Agitation | `Firm_Moves_10yr__c` | Number(2,0) | 3 | Identifies "movers"; prior mobility ↔ higher move propensity. |
| Propensity/Agitation | `Has_Disclosure__c` | Checkbox | TRUE | Compliance friction → agitation; strong positive predictor. |
| Propensity/Agitation | `Disclosure_Type__c` | Picklist | Termination | Urgency stratification (e.g., Termination > Regulatory > Customer Dispute). |
| Fit/Business Model | `Licenses__c` | Text(255) | "Series 7; 65" | Infers operating model (broker vs advisor) and suitability. |
| Fit/Business Model | `Designations__c` | Text(255) | "CFP; CFA" | Quality/fit; CFP/CFA often correlate with engagement. |
| Fit/Business Model | `Business_Model__c` | Picklist | "Fee-Based (Hybrid)" | Hybrid/fee-based advisors are prime targets. |
| Fit/Business Model | `Specialties__c` | Text(255) | "HNW; Retirement" | Niche fit with Savvy's strengths/messaging. |
| Operational/Technical | `Current_Custodian__c` | Picklist | "Schwab" | Lower friction if custodian is Savvy-supported; informs playbook. |
| Operational/Technical | `Team_Size__c` | Number(3,0) | 4 | Complexity proxy; solos often faster to move. |
| Operational/Technical | `Is_Team_Lead__c` | Checkbox | TRUE | Decision authority; target principals first. |
| Operational/Technical | `CRM_Used__c` | Picklist | "Redtail" | Sophistication + integration friction; messaging personalization. |

### 5.3 Comprehensive Feature Engineering Pipeline (69 Features)

#### 5.3.1 Feature Engineering Architecture
Our model implements a sophisticated **3-stage feature engineering pipeline** that transforms raw data into 69 predictive features (67 discovery + 2 temporal):

**Stage 1: Base Feature Extraction (31 features)**
- Direct mapping from discovery data fields
- Data type standardization and validation
- Missing value handling and outlier detection

**Stage 2: Geographic Encoding (5 features)**
- Metropolitan area dummy variable creation
- Top-N selection and one-hot encoding
- Geographic pattern analysis

**Stage 3: Advanced Feature Engineering (31 features)**
- Complex derived metrics and ratios
- Business logic-based feature creation
- Interaction terms and composite scores

#### 5.3.2 Base Discovery Features (31 features)
These features are directly sourced from discovery data and standardized on the Lead/Contact object:

| Group | API Field | Type (SFDC) | Example | Why It Matters (Signal) |
| :--- | :--- | :--- | :--- | :--- |
| **Firmographics** | `Total_Assets_In_Millions__c` | Number(12,2) | 450.5 | Scale indicator; larger AUM correlates with complex transitions. |
| | `Number_Employees__c` | Number(5,0) | 12 | Operational complexity; impacts decision timeline. |
| | `Number_Investment_Advisory_Clients__c` | Number(7,0) | 325 | Client base size; influences migration complexity. |
| **Advisor Tenure** | `Date_Became_Rep_Number_Of_Years__c` | Number(3,1) | 12.5 | Experience level; sweet spot 5-15 years for moves. |
| | `Date_Of_Hire_At_Current_Firm_Years__c` | Number(3,1) | 3.2 | Firm loyalty/restlessness; 2-5 years highest propensity. |
| **Client Composition** | `Number_Clients_HNW_Individuals__c` | Number(5,0) | 85 | Quality of book; HNW focus aligns with Savvy. |
| | `Assets_In_Millions_Individuals__c` | Number(10,2) | 320.0 | Individual vs institutional split; retail focus preferred. |
| **Growth Metrics** | `AUM_Growth_Rate_1Year__c` | Number(5,2) | 12.5 | Recent momentum; stagnant = more receptive. |
| | `AUM_Growth_Rate_5Year__c` | Number(5,2) | 45.0 | Long-term trajectory; declining = pain point. |
| **Registration** | `Number_Firm_Associations__c` | Number(3,0) | 2 | Complexity indicator; multi-firm harder to move. |
| | `Number_RIA_Firm_Associations__c` | Number(3,0) | 1 | RIA experience; positive signal for independence. |

#### 5.3.3 Metropolitan Area Features (5 features)
**Geographic Pattern Recognition Pipeline:**

The **metropolitan area dummy variables** are a set of 5 binary (0/1) features that indicate which major metropolitan area a financial advisor is located in. These features help the model understand geographic patterns in lead conversion behavior.

**Feature List:**
1. `Home_MetropolitanArea_Chicago-Naperville-Elgin IL-IN`
2. `Home_MetropolitanArea_Dallas-Fort Worth-Arlington TX`
3. `Home_MetropolitanArea_Los Angeles-Long Beach-Anaheim CA`
4. `Home_MetropolitanArea_Miami-Fort Lauderdale-West Palm Beach FL`
5. `Home_MetropolitanArea_New York-Newark-Jersey City NY-NJ`

**Engineering Process:**
1. **Source Data:** Extract `Home_MetropolitanArea` field from Discovery Data
2. **Top-N Selection:** Identify 5 most frequent metropolitan areas
3. **One-Hot Encoding:** Create binary indicators for each area
4. **Dimensionality Reduction:** Drop "Other" category to avoid multicollinearity

**Business Value:**
- Captures regional market dynamics and competition patterns
- Identifies geographic conversion hotspots
- Enables location-specific targeting strategies

#### 5.3.4 Advanced Engineered Features (31 features)
**Sophisticated Feature Creation Pipeline:**

Our model creates 31 advanced features through complex business logic and mathematical transformations:

**Efficiency Metrics (3 features):**
- `AUM_per_Client` - Client quality indicator (>$2M = premium)
- `AUM_per_Employee` - Operational efficiency metric
- `AUM_per_IARep` - Workload and productivity indicator

**Growth Indicators (3 features):**
- `Growth_Momentum` - 1Y growth × 5Y growth interaction
- `Growth_Acceleration` - Recent vs historical growth comparison
- `Positive_Growth_Trajectory` - Consistent growth flag

**Firm Stability (3 features):**
- `Firm_Stability_Score` - Composite tenure and loyalty metric
- `Is_Veteran_Advisor` - Experience threshold (>10 years)
- `High_Turnover_Flag` - Recent move pattern indicator

**Client Focus (3 features):**
- `HNW_Client_Ratio` - High-net-worth client concentration
- `Premium_Positioning` - High-value practice indicator
- `Mass_Market_Focus` - Lower-tier practice flag

**Operational Metrics (3 features):**
- `Branch_Advisor_Density` - Centralization and support needs
- `Complex_Registration` - Regulatory complexity flag
- `Multi_RIA_Relationships` - Independence experience indicator

**Geographic Factors (2 features):**
- `Remote_Work_Indicator` - Distance-based work pattern
- `Local_Advisor` - Proximity-based engagement flag

**Quality & Performance (16 features):**
- `Quality_Score` - Composite quality assessment
- `Experience_Efficiency` - AUM per year of experience
- `Clients_per_Employee` - Operational efficiency
- `Clients_per_IARep` - Workload distribution
- `Individual_Asset_Ratio` - Retail vs institutional focus
- `Alternative_Investment_Focus` - Investment sophistication
- `Is_Large_Firm` - Scale indicator (>100 employees)
- `Is_Boutique_Firm` - Premium small practice flag
- `Has_Scale` - AUM or client count threshold
- `Is_New_To_Firm` - Recent hire indicator
- `Primarily_US_Clients` - Geographic focus flag
- `International_Presence` - Global client base
- `Accelerating_Growth` - Growth trajectory flag
- `HNW_Asset_Concentration` - Wealth concentration
- `AverageTenureAtPriorFirms` - Career stability metric
- `NumberOfPriorFirms` - Career mobility indicator

#### 5.3.5 Temporal Contact Features (2 features)
**Weekend Contact Premium Discovery:**

Based on Step 3.1 Class Distribution Analysis findings (which showed weekend contacts have a premium conversion rate of 8.72% vs weekday average of 4.3%), we added two temporal features to capture contact timing patterns:

**Feature List:**
1. **`Day_of_Contact`**: Day of week when lead was contacted (1=Monday, 2=Tuesday, ..., 7=Sunday)
   - Numeric feature representing the day of the week
   - Captures day-of-week conversion patterns
   - Derived from `Stage_Entered_Contacting__c` timestamp

2. **`Is_Weekend_Contact`**: Boolean flag indicating if contact occurred on Saturday or Sunday
   - Binary indicator (0/1) for weekend contacts
   - Captures the observed premium conversion rate for weekend contacts (8.72% vs 4.3% weekday average)
   - Derived from `Day_of_Contact` (value of 6 or 7)

**Business Value:**
- **Weekend Premium:** Saturday contacts show 8.72% conversion rate (2x weekday average)
- **Timing Optimization:** Enables SGAs to prioritize weekend contact windows
- **Model Accuracy:** Improves prediction by incorporating known temporal patterns

**Engineering Process:**
1. Extract `Day_of_Contact` from `Stage_Entered_Contacting__c` timestamp
2. Create `Is_Weekend_Contact` binary flag from `Day_of_Contact` (6 or 7)
3. Include both features in model training and scoring pipelines

### 5.4 Data Quality Assurance & Validation Framework

#### 5.4.1 Multi-Source Data Quality Monitoring
**Comprehensive Quality Metrics:**
- **Source Coverage:** Track data availability from each source (Salesforce, MarketPro, Discovery)
- **Join Success Rates:** Monitor merge performance across all data sources
- **Data Freshness:** Validate timestamps and update frequencies
- **Completeness Scores:** Feature-level null rate monitoring
- **Consistency Checks:** Cross-source data validation

**Quality Thresholds (DEVELOPMENT-BASELINE):**
- Salesforce data coverage: >95% ✅ **DEVELOPMENT MODEL: 100% (with duplicate CRD handling)**
- MarketPro Raw Data coverage: >70% ✅ **DEVELOPMENT MODEL: >80%**
- MarketPro enrichment: >80% ✅ **DEVELOPMENT MODEL: Achieved**
- Overall join success rate: >75% ✅ **DEVELOPMENT MODEL: 100% (with duplicate handling)**
- **CRITICAL:** Handle duplicate CRD numbers in Salesforce (development model shows ~0.1% duplicate rate)
- **CRITICAL:** Manage MarketPro Raw Data territory gaps (T1/T2/T3 coverage variance in development)

**Note on Duplicate CRD Matching:**
The 8.8% duplicate matching indicates duplicate CRDs in Salesforce data. This means:
- 100% of MarketPro records successfully matched to Salesforce
- 8.8% of MarketPro records matched to multiple Salesforce entries (duplicate CRDs)
- Each MarketPro record can match multiple Salesforce records due to SF duplicates
- Production pipeline must deduplicate Salesforce records before joining

#### 5.4.2 Feature Engineering Quality Controls
**Data Contract Requirements:**
- All discovery fields require **Discovery_Data_Last_Updated__c** timestamp
- Maintain **data quality scores** for each discovery field (completeness, recency)
- Store raw discovery payload in `Discovery_Raw__c` (JSON) for auditability
- Implement **null handling strategies** per feature category:
  - Firmographics: Impute with segment medians
  - Growth metrics: Flag as "Unknown" category
  - Efficiency metrics: Derive only when denominators > 0

**Feature Validation Rules:**
- **Continuous features:** Apply log transformation for AUM-related fields; standardize all continuous features
- **Growth rates:** Cap at [-50%, +200%] to handle outliers; create bucketed versions for non-linearity
- **Efficiency ratios:** Create percentile ranks within peer groups (by AUM tier)
- **Metropolitan areas:** Use as-is binary flags; consider interaction terms with AUM size
- **Composite scores:** Normalize to [0,1] range; version the scoring logic

#### 5.4.3 Advanced Data Cleaning Pipeline
**Column Deduplication Process:**
- Identify and merge duplicate columns from multiple sources
- Remove highly correlated features (threshold = 0.98)
- Handle missing value patterns across sources
- Generate comprehensive cleaning reports

**Data Type Standardization:**
- Convert all numeric fields with proper error handling
- Standardize boolean encodings across sources
- Handle datetime conversions with timezone normalization
- Apply consistent categorical encoding

**Outlier Detection & Handling:**
- Statistical outlier detection for continuous features
- Business rule-based outlier identification
- Cap extreme values at reasonable thresholds
- Flag suspicious data for manual review


**Data Source Integration:**
- *"Design a data quality monitoring system that tracks join success rates across Salesforce, MarketPro, and Discovery Data sources. Include automated alerts for coverage drops below 70%."*
- *"Generate SQL to validate CRD number consistency across all three data sources and identify any mismatches or missing records that require manual review."*
- *"Create a reconciliation report template that shows data coverage by territory (T1, T2, T3) and identifies any geographic gaps in Discovery Data coverage."*

**Advanced Data Cleaning:**
- *"Write unit tests for the column deduplication pipeline that verify identical columns are properly merged and highly correlated columns (>0.98) are handled correctly."*
- *"Generate SQL assertions to validate data type conversions (numeric, boolean, datetime) handle edge cases like currency symbols, null values, and timezone conversions."*
- *"Design a data quality scorecard that tracks null rates, outlier percentages, and data consistency metrics across all 69 engineered features."*

**Feature Engineering Validation:**
- *"Given these 69 discovery features, identify potential multicollinearity issues and propose a correlation matrix threshold strategy. Generate VIF calculations for the top 20 features."*
- *"Write SQL to compute feature coverage rates across the lead population. Flag any features with >50% missing values and propose imputation strategies."*
- *"Generate unit tests to verify engineered feature calculations (e.g., AUM_Per_Client) handle edge cases like zero denominators, negative growth rates, and null inputs."*
- *"Propose a feature importance analysis plan using SHAP to identify the top 20 most predictive discovery features for the Contacted→MQL transition."*

**Data Pipeline Monitoring:**
- *"Design a comprehensive monitoring dashboard that tracks data quality metrics, processing latency, and error rates across all 10 phases of the daily pipeline."*
- *"Generate SQL to compute data drift metrics (PSI) for all 69 features comparing current distributions to 30-day baselines."*
- *"Create an automated alerting system that triggers when data quality scores drop below thresholds or when feature engineering produces unexpected results."*

### 5.3 Feature Scope (Combined)
- **At/Before Contacted:** - Channel/source
  - MarketPro firmographics (12 fields from 5.0)
  - Discovery base features (31 fields)
  - Metropolitan indicators (5 fields)
  - Engineered discovery features (31 fields)
  - Contact quality flags
  - Geography
  - Lead age
  - Days since created
  - Prior engagement (only if timestamped before Contacted)
  - SGA owner ID
  - Historical SGA performance
- **Total feature count:** ~100 features (after encoding)
- **Strictly exclude** any fields populated *after* Contacted or derived from future knowledge (e.g., `days_to_mql`).

### 5.4 Outcome Label
- **Label = 1** if MQL timestamp occurs **within 30 days** of `stage_entered_contacting__c`. Else **0**.  
- Exclude right-censored records (contacted less than 30 days before snapshot cutoff).

#### 5.4.1 30-Day Outcome Window Rationale

The **30-day outcome window** is a critical modeling decision that defines when we consider a lead conversion to be "valid" for our model:

**Why 30 Days?**
- **Business Reality:** Most MQL conversions happen quickly after initial contact
- **Model Performance:** Including very late conversions can hurt model accuracy  
- **Actionable Insights:** We want to predict leads that will convert within a reasonable timeframe

**What It Means:**
- **Contacted Lead:** Someone enters "Contacting" stage on Day 0
- **30-Day Window:** We only count conversions that happen within 30 days of contact
- **Late Conversions:** Any conversions after 30 days are excluded from our positive class

**Empirical Evidence:**
- **All-time conversions:** 2,111 MQLs
- **30-day window conversions:** 1,902 MQLs (90.1% of all conversions)
- **Late conversions:** 209 MQLs (9.9% excluded)

This means **90.1% of conversions happen within 30 days**, so the 30-day window captures the vast majority while excluding outliers that might confuse the model.

**Real-World Application:**
When the model scores a **new lead** (contacted today), it will predict:
- **"Will this lead convert to MQL within 30 days?"**
- **Not:** "Will this lead ever convert?" (which could take 6+ months)

This makes the model more actionable for your sales team - they can focus on leads likely to convert quickly rather than waiting indefinitely.

### 5.5 Temporal Framing & Splits
- TimeSeriesSplit with entity isolation; older → train, newer → validation/test.
- Given expanded feature set, use 180-day training window minimum.

### 5.6 Imbalance Strategy (DEVELOPMENT-VALIDATED COMPARISON)

**Comprehensive SMOTE vs Pos_Weight Testing Framework:**

Given the extreme class imbalance (2-3% positive class), we will systematically test both approaches:

#### 5.6.1 SMOTE Implementation
```python
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

# SMOTE Configuration
smote_configs = {
    'smote_default': SMOTE(random_state=42),
    'smote_balanced': SMOTE(random_state=42, sampling_strategy=0.1),  # 10% positive class
    'smote_conservative': SMOTE(random_state=42, sampling_strategy=0.05),  # 5% positive class
    'smote_k_neighbors': SMOTE(random_state=42, k_neighbors=3),  # Fewer neighbors for sparse data
}

# SMOTE Pipeline
def create_smote_pipeline(model, smote_config):
    return ImbPipeline([
        ('smote', smote_config),
        ('scaler', StandardScaler()),
        ('model', model)
    ])
```

#### 5.6.2 Pos_Weight Implementation
```python
# Pos_Weight Configuration
def calculate_pos_weight(y_train):
    n_pos = sum(y_train)
    n_neg = len(y_train) - n_pos
    pos_weight = min(n_neg / n_pos, 10.0)  # Cap at 10x to prevent extreme weights
    return pos_weight

pos_weight_configs = {
    'pos_weight_calculated': calculate_pos_weight(y_train),
    'pos_weight_conservative': 3.0,  # Conservative 3:1 ratio
    'pos_weight_moderate': 5.0,      # Moderate 5:1 ratio
    'pos_weight_aggressive': 8.0,    # Aggressive 8:1 ratio
}

# XGBoost with Pos_Weight
def create_pos_weight_model(pos_weight_value):
    return XGBClassifier(
        scale_pos_weight=pos_weight_value,
        random_state=42,
        eval_metric='aucpr'
    )
```

#### 5.6.3 Comprehensive Comparison Framework
```python
def compare_imbalance_strategies(X_train, y_train, X_val, y_val):
    """
    Systematic comparison of SMOTE vs Pos_Weight approaches
    """
    results = {}
    
    # Test SMOTE variants
    for smote_name, smote_config in smote_configs.items():
        pipeline = create_smote_pipeline(XGBClassifier(random_state=42), smote_config)
        pipeline.fit(X_train, y_train)
        
        y_pred_proba = pipeline.predict_proba(X_val)[:, 1]
        
        results[smote_name] = {
            'method': 'SMOTE',
            'config': smote_name,
            'auc_pr': average_precision_score(y_val, y_pred_proba),
            'auc_roc': roc_auc_score(y_val, y_pred_proba),
            'precision_at_10': precision_at_k(y_val, y_pred_proba, k=0.1),
            'recall_at_10': recall_at_k(y_val, y_pred_proba, k=0.1),
            'calibration_error': calibration_error(y_val, y_pred_proba),
            'training_samples': len(pipeline.named_steps['smote'].fit_resample(X_train, y_train)[0])
        }
    
    # Test Pos_Weight variants
    for pos_weight_name, pos_weight_value in pos_weight_configs.items():
        model = create_pos_weight_model(pos_weight_value)
        model.fit(X_train, y_train)
        
        y_pred_proba = model.predict_proba(X_val)[:, 1]
        
        results[pos_weight_name] = {
            'method': 'Pos_Weight',
            'config': pos_weight_name,
            'auc_pr': average_precision_score(y_val, y_pred_proba),
            'auc_roc': roc_auc_score(y_val, y_pred_proba),
            'precision_at_10': precision_at_k(y_val, y_pred_proba, k=0.1),
            'recall_at_10': recall_at_k(y_val, y_pred_proba, k=0.1),
            'calibration_error': calibration_error(y_val, y_pred_proba),
            'training_samples': len(X_train)
        }
    
    return results
```

#### 5.6.4 Validation Metrics for Imbalance Strategy Selection
```sql
-- Checkpoint: SMOTE vs Pos_Weight Comparison Results
SELECT 
    method_type,
    config_name,
    auc_pr_score,
    auc_roc_score,
    precision_at_10_percent,
    recall_at_10_percent,
    calibration_error,
    training_sample_count,
    CASE 
        WHEN method_type = 'SMOTE' THEN training_sample_count - original_sample_count
        ELSE 0
    END as synthetic_samples_generated,
    CASE 
        WHEN auc_pr_score > 0.35 AND calibration_error < 0.05 THEN 'EXCELLENT'
        WHEN auc_pr_score > 0.30 AND calibration_error < 0.08 THEN 'GOOD'
        WHEN auc_pr_score > 0.25 AND calibration_error < 0.10 THEN 'ACCEPTABLE'
        ELSE 'POOR'
    END as overall_performance,
    CASE 
        WHEN method_type = 'SMOTE' AND synthetic_samples_generated > 10000 THEN 'OVER_SAMPLED'
        WHEN method_type = 'SMOTE' AND synthetic_samples_generated < 1000 THEN 'UNDER_SAMPLED'
        WHEN method_type = 'Pos_Weight' AND scale_pos_weight > 8.0 THEN 'EXTREME_WEIGHT'
        ELSE 'BALANCED'
    END as sampling_status
FROM `savvy-gtm-analytics.LeadScoring.imbalance_strategy_comparison`
ORDER BY auc_pr_score DESC, calibration_error ASC;
```

#### 5.6.5 Decision Criteria for Imbalance Strategy Selection

**Primary Metrics (Weighted):**
1. **AUC-PR (40%)** - Most important for imbalanced data
2. **Calibration Error (25%)** - Critical for business decisions
3. **Precision@10% (20%)** - Tier A lead quality
4. **Training Stability (15%)** - Cross-validation consistency

**Secondary Considerations:**
- **Computational Cost:** SMOTE increases training time significantly
- **Memory Usage:** SMOTE creates synthetic samples (2-10x dataset size)
- **Interpretability:** Pos_Weight maintains original data distribution
- **Overfitting Risk:** SMOTE may create overfitted synthetic samples

**Selection Thresholds:**
- **AUC-PR Difference > 0.02:** Choose higher performing method
- **Calibration Error Difference > 0.03:** Choose better calibrated method
- **Precision@10% Difference > 0.05:** Choose higher precision method
- **Training Time Difference > 2x:** Consider computational constraints

### 5.7 Calibration
- Platt or isotonic on validation; persist `calibration_version`.
- Test calibration stability across AUM segments given firmographic features.

### 5.8 Tiering by Capacity
- Capacity-based A/B/C with **dynamic reallocation** based on:
  - SGA availability
  - Feature-driven priority scores (e.g., upweight high AUM + high growth momentum)
  - Include capacity calc and hourly refresh for intraday optimization

- *"Given the 100+ feature list including discovery data, identify any fields that can be populated or influenced **after** Contacted. Pay special attention to growth rates and client counts that might be updated post-contact."* - *"Write assertions (SQL) that confirm discovery data timestamps are all ≤ contacted\_ts. Include checks for Discovery\_Data\_Last\_Updated\_\_c vs stage\_entered\_contacting\_\_c."* - *"Generate SQL to validate that efficiency metrics (AUM\_Per\_Client, etc.) are computed from snapshot data at contacted\_ts, not current values."* - *"Create a feature correlation heatmap focusing on the discovery features. Identify clusters of highly correlated features (>0.8) and propose dimensionality reduction."*

---

## 6) Modeling

### 6.1 Algorithm
- **Primary:** XGBoost (binary:logistic) with custom feature importance weighting
- **Evaluation metric:** `aucpr` with secondary focus on top-decile precision
- **Early stopping:** on temporal validation with patience=20 rounds

### 6.2 Feature Selection Strategy
Given 100+ features, implement systematic selection:
1. **Univariate screening:** Remove features with IV < 0.02
2. **Multicollinearity check:** VIF < 10 for continuous features
3. **Recursive feature elimination:** Top 50 features by SHAP importance
4. **Business logic override:** Always include key discovery metrics (AUM, Growth, HNW ratio)

### 6.3 Cross-Validation
- **Blocked time-series CV** (K=5 folds) with 30-day gaps between train/val
- **Stratification:** By AUM tier to ensure representation

### 6.4 Hyperparameters (expanded grid for complex features)
- `max_depth: [4, 6, 8, 10]` (deeper trees for feature interactions)
- `eta: [0.01, 0.03, 0.05]` (slower learning for 100+ features)
- `min_child_weight: [1, 5, 10]` 
- `subsample: [0.6, 0.7, 0.8]` 
- `colsample_bytree: [0.4, 0.6, 0.8]` (more aggressive for high dimensionality)
- `scale_pos_weight: as computed`
- `reg_alpha: [0, 0.1, 1.0]` (L1 regularization for feature selection)
- `reg_lambda: [1, 2, 5]` (L2 regularization)

### 6.5 Explainability
- **Global:** SHAP summary plots for top 30 features
- **Local:** Per-prediction SHAP with focus on discovery vs MarketPro contribution
- **Cohort analysis:** SHAP by AUM tier, growth trajectory, metro area
- Persist top 5 positive drivers per prediction for SFDC tooltip

### 6.6 Model Ensemble (Optional Enhancement)
Consider stacking with:
- LightGBM for categorical features (metro, custodian, CRM)
- Logistic regression on top 20 features for baseline
- Neural network for non-linear interactions

- *"Given 100+ features and class imbalance ~6%, design a feature selection pipeline that preserves business-critical discovery metrics while optimizing AUC-PR."*
- *"Generate code to compute feature importance variance across CV folds. Flag features with importance CV > 50% as unstable."*
- *"Propose hyperparameter adjustments specific to handling the discovery features (continuous AUM/growth vs categorical metro/custodian)."*
- *"Design SHAP interaction plots for: AUM × Growth\_Rate, Years\_at\_Firm × Firm\_Moves, HNW\_Ratio × Metro\_Area."*

---

## 7) Validation, Calibration & Thresholding

### 7.1 Validation Metrics (Enhanced)
Report per fold and overall:
- `aucpr` (primary)
- `precision@capacity` by AUM tier
- `recall@capacity` by growth trajectory
- **Calibration by segment:** Brier score for each AUM quartile
- **Fairness metrics:** Precision parity across metro areas
- **Feature stability:** SHAP importance correlation between folds

### 7.2 Calibration Procedure (Segment-Aware)
1. Fit model on train  
2. Fit **segment-specific calibrators** for:
   - AUM < $100M
   - AUM $100M - $500M  
   - AUM > $500M
3. Apply appropriate calibrator based on lead's segment
4. Version and store all calibration params with segment keys

### 7.3 Dynamic Tier Design
Capacity-based cuts with **feature-driven adjustments**:
- **Tier A:** Top scores up to daily capacity × 1.2 (overbook for no-shows)
- **Priority boost:** +0.1 probability for leads with:
  - AUM > $500M AND positive growth
  - HNW\_ratio > 0.5
  - Veteran advisor with recent firm change
- Validate tier stability across discovery data updates

- *"Generate SQL to compute calibration curves separately for leads with complete discovery data vs partial/missing discovery fields."*
- *"Design a backtest comparing model performance with all 100 features vs MarketPro-only baseline. Report lift in AUC-PR and Tier A precision."*
- *"Write validation to ensure discovery-based priority boosts don't violate capacity constraints while maintaining fairness."*

---

## 8) Experiment Design (Proving Impact)

### 8.1 Randomization Unit
- **Lead-level randomization** with **blocking by AUM tier**
- Ensure balanced discovery data coverage in treatment/control

### 8.2 Stratification Variables
- AUM tier (derived from `Total_Assets_In_Millions__c`)
- Data completeness score (% of discovery features populated)
- Metro area presence

### 8.3 Primary KPI
- **MQLs per 100 dials** within 30 days of Contacted
- **Sub-analysis:** By AUM tier and growth trajectory

### 8.4 Secondary KPIs
- MQL quality score (based on discovery profile)
- Time-to-MQL for different advisor segments
- SGA efficiency by lead tier and feature richness

### 8.5 Guardrails
- Discovery data coverage balance between groups
- No degradation in high-AUM lead coverage
- SGA workload balance across metros

### 8.6 Duration & Power
- Minimum **4 weeks** or **≥ 500 MQL outcomes**
- Power calculation adjusted for blocking design
- Interim analysis at 2 weeks for safety

### 8.7 Compliance & Measurement
- Track "feature visibility" - which discovery features SGAs reference
- Log when SGAs override model recommendations
- Measure information value of discovery features via click-through on tooltips

- *"Design an analysis plan to measure heterogeneous treatment effects by AUM tier and discovery data completeness. Include sample size per stratum."*
- *"Generate SQL to validate that randomization preserved balance on all 69 discovery features within 5% between treatment/control."*
- *"Propose a method to quantify the incremental value of discovery features vs MarketPro-only in the experiment."*

---

## 9) Monitoring, Drift, and Governance

### 9.1 Enhanced Dashboards
**Prediction Quality:**
- Tier A precision/recall by week, **segmented by AUM tier**
- Calibration curves by month for each segment
- **Discovery feature drift:** Heatmap of feature distributions over time
- **Feature importance evolution:** SHAP rankings week-over-week

**Business Impact:**
- MQLs/100 dials by group and **by advisor segment**
- Conversion rates by tier and **discovery data completeness**
- SGA adoption with **feature utilization metrics**

**Data Quality:**
- Discovery data coverage rates
- Feature null rates and imputation impact
- Join success rates between MarketPro and Discovery sources

### 9.2 Drift Detection (Multi-Source)
**Discovery Data Drift:**
- PSI for each discovery feature category (firmographics, growth, efficiency)
- **Source reliability score:** Track vendor data delays/gaps
- **Cross-source consistency:** Flag when MarketPro and Discovery conflict

**Feature Importance Drift:**
- Track SHAP value changes for top 20 features
- Alert if any feature importance changes >50% week-over-week

**Segment Drift:**
- Monitor MQL rates by AUM tier
- Detection of new geographic concentrations

### 9.3 Alerting & Escalation
**Tiered Alerts:**
- **WARN:** Single feature PSI ≥ 0.2 OR discovery coverage < 60%
- **ALERT:** Multiple features PSI ≥ 0.3 OR AUM-tier calibration off >40%
- **CRITICAL:** Discovery data pipeline failure OR Tier A precision < 50% of baseline

**Response Playbook:**
1. Check vendor data feed status
2. Validate feature engineering pipeline
3. Recompute calibration with last 30 days
4. If discovery features degraded: Fall back to MarketPro-only model
5. If sustained drift: Trigger emergency retrain

### 9.4 Model Refresh Strategy
**Scheduled Retraining:**
- Every **45 days** with 180-day window (increased frequency due to feature complexity)
- **Feature selection refresh:** Monthly to adapt to importance shifts

**Triggered Retraining:**
- Discovery vendor changes data schema
- New metropolitan markets added
- Base rate shifts >50% in any AUM segment

**A/B Testing New Models:**
- Shadow mode for 7 days
- Must beat incumbent on AUC-PR **and** Tier A precision by >5%
- Gradual rollout: 10% → 50% → 100% over 2 weeks

- *"Design a monitoring dashboard that tracks discovery feature quality (null rates, outliers, cross-source conflicts) with automated anomaly detection."*
- *"Generate SQL to compute feature importance stability score comparing SHAP values between the current model and 30-day rolling window."*
- *"Propose a fallback strategy when >30% of discovery features are unavailable, including performance degradation estimates."*

---

## 10) Deployment & Operations

### 10.1 Monthly Batch Data Pipeline Architecture

**Salesforce Daily Sync (Automated)**
```sql
-- Daily full refresh of Lead object
CREATE OR REPLACE TABLE savvy_analytics.sfdc_leads_current AS
SELECT * FROM EXTERNAL_QUERY(
  'salesforce_connection',
  'SELECT Id, FA_CRD__c, Stage_Entered_Contacting__c, 
          Stage_Entered_Call_Scheduled__c, LastModifiedDate,
          FirstName, LastName, Email, Company, Title, State, City
   FROM Lead'
);
```

**Discovery Data Monthly Upload (Manual Process)**

**Manual Upload Workflow (Monthly - Day 1):**
1. **Download MarketPro CSVs** - Manual download from vendor portal
2. **Upload to BigQuery** - Use Python helper scripts (one-time tools)
3. **Process & Merge** - Automated BigQuery SQL pipeline
4. **Quality Validation** - Automated data quality checks

**Production Pipeline (Daily - Days 2-30):**
- Automated BigQuery SQL processing
- No Python scripts in production
- Managed services for orchestration

**Step 1: Download T1/T2/T3 CSV Files from MarketPro**
```bash
# Manual process - follow MarketPro README.TXT instructions
# 1. Go to MarketPro portal
# 2. Navigate to Reports → T1, T2, T3 territories
# 3. For each territory:
#    - Click "View List" → "Open in RIA Reps"
#    - Click "Download" → "All Fields Available"
# 4. Save as: discovery_t1_YYYY_MM.csv, discovery_t2_YYYY_MM.csv, discovery_t3_YYYY_MM.csv
```

**Step 2: Manual Upload Tools (One-Time Setup)**

**Python Helper Scripts (Manual Upload Only):**
```python
# These are ONE-TIME helper scripts for manual CSV uploads
# NOT part of the production pipeline

from google.cloud import bigquery
import pandas as pd

def upload_discovery_territory(territory, csv_path, project_id="savvy-gtm-analytics"):
    """ONE-TIME helper: Upload MarketPro CSV to BigQuery staging table"""
    
    # Read CSV with proper type inference
    df = pd.read_csv(
        csv_path,
        low_memory=False,
        na_values=['', 'NA', 'N/A', 'null', 'NULL', 'None'],
        keep_default_na=True
    )
    
  # Upload to BigQuery staging table
  client = bigquery.Client(project=project_id)
  table_id = f"{project_id}.LeadScoring.staging_discovery_{territory}"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True
    )
    
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()
    
    print(f"✅ Uploaded {len(df)} rows to {table_id}")

# Manual execution (run once per month):
# upload_discovery_territory("t1", "discovery_t1_2025_01.csv")
# upload_discovery_territory("t2", "discovery_t2_2025_01.csv") 
# upload_discovery_territory("t3", "discovery_t3_2025_01.csv")
```

**Note:** These Python scripts are **manual upload tools only**. They are NOT part of the production pipeline. The production pipeline uses BigQuery SQL exclusively.

**Step 3: Production Data Processing Pipeline (BigQuery SQL)**
```sql
-- Production-grade data processing using BigQuery SQL
-- Replaces Python-based create_discovery_data_pkl() with scalable SQL

CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.discovery_reps_current` AS
WITH 
-- Data type standardization and alignment across territories
type_aligned_t1 AS (
  SELECT 
    CAST(RepCRD AS STRING) as RepCRD,
    CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
    CAST(TotalAssetsInMillions AS FLOAT64) as TotalAssetsInMillions,
    CAST(Number_Employees AS INT64) as Number_Employees,
    CAST(AUMGrowthRate_1Year AS FLOAT64) as AUMGrowthRate_1Year,
    CAST(AUMGrowthRate_5Year AS FLOAT64) as AUMGrowthRate_5Year,
    CAST(Date_Became_Rep_Number_Of_Years AS FLOAT64) as Date_Became_Rep_Number_Of_Years,
    CAST(Date_Of_Hire_At_Current_Firm_Years AS FLOAT64) as Date_Of_Hire_At_Current_Firm_Years,
    CAST(Number_Investment_Advisory_Clients AS INT64) as Number_Investment_Advisory_Clients,
    CAST(Number_Clients_HNW_Individuals AS INT64) as Number_Clients_HNW_Individuals,
    CAST(Assets_In_Millions_Individuals AS FLOAT64) as Assets_In_Millions_Individuals,
    CAST(Home_MetropolitanArea AS STRING) as Home_MetropolitanArea,
                -- ... all 69 discovery features with proper type casting
    'T1' as territory_source,
    CURRENT_TIMESTAMP() as processed_at
  FROM `savvy-gtm-analytics.LeadScoring.staging_discovery_t1`
),

type_aligned_t2 AS (
  SELECT 
    CAST(RepCRD AS STRING) as RepCRD,
    CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
    CAST(TotalAssetsInMillions AS FLOAT64) as TotalAssetsInMillions,
    CAST(Number_Employees AS INT64) as Number_Employees,
    CAST(AUMGrowthRate_1Year AS FLOAT64) as AUMGrowthRate_1Year,
    CAST(AUMGrowthRate_5Year AS FLOAT64) as AUMGrowthRate_5Year,
    CAST(Date_Became_Rep_Number_Of_Years AS FLOAT64) as Date_Became_Rep_Number_Of_Years,
    CAST(Date_Of_Hire_At_Current_Firm_Years AS FLOAT64) as Date_Of_Hire_At_Current_Firm_Years,
    CAST(Number_Investment_Advisory_Clients AS INT64) as Number_Investment_Advisory_Clients,
    CAST(Number_Clients_HNW_Individuals AS INT64) as Number_Clients_HNW_Individuals,
    CAST(Assets_In_Millions_Individuals AS FLOAT64) as Assets_In_Millions_Individuals,
    CAST(Home_MetropolitanArea AS STRING) as Home_MetropolitanArea,
                -- ... all 69 discovery features with proper type casting
    'T2' as territory_source,
    CURRENT_TIMESTAMP() as processed_at
  FROM `savvy-gtm-analytics.LeadScoring.staging_discovery_t2`
),

type_aligned_t3 AS (
  SELECT 
    CAST(RepCRD AS STRING) as RepCRD,
    CAST(RIAFirmCRD AS STRING) as RIAFirmCRD,
    CAST(TotalAssetsInMillions AS FLOAT64) as TotalAssetsInMillions,
    CAST(Number_Employees AS INT64) as Number_Employees,
    CAST(AUMGrowthRate_1Year AS FLOAT64) as AUMGrowthRate_1Year,
    CAST(AUMGrowthRate_5Year AS FLOAT64) as AUMGrowthRate_5Year,
    CAST(Date_Became_Rep_Number_Of_Years AS FLOAT64) as Date_Became_Rep_Number_Of_Years,
    CAST(Date_Of_Hire_At_Current_Firm_Years AS FLOAT64) as Date_Of_Hire_At_Current_Firm_Years,
    CAST(Number_Investment_Advisory_Clients AS INT64) as Number_Investment_Advisory_Clients,
    CAST(Number_Clients_HNW_Individuals AS INT64) as Number_Clients_HNW_Individuals,
    CAST(Assets_In_Millions_Individuals AS FLOAT64) as Assets_In_Millions_Individuals,
    CAST(Home_MetropolitanArea AS STRING) as Home_MetropolitanArea,
                -- ... all 69 discovery features with proper type casting
    'T3' as territory_source,
    CURRENT_TIMESTAMP() as processed_at
  FROM `savvy-gtm-analytics.LeadScoring.staging_discovery_t3`
),

-- Concatenate all territories
unified_data AS (
  SELECT * FROM type_aligned_t1
  UNION ALL
  SELECT * FROM type_aligned_t2
  UNION ALL
  SELECT * FROM type_aligned_t3
),

-- Advanced deduplication logic (replaces Python drop_duplicates)
deduplicated_data AS (
  SELECT 
    *,
    ROW_NUMBER() OVER (
      PARTITION BY RepCRD, RIAFirmCRD 
      ORDER BY processed_at DESC, territory_source
    ) as dedup_rank
  FROM unified_data
),

-- Feature engineering (replaces Python FeatureEngineer class)
engineered_features AS (
  SELECT 
    *,
    -- Efficiency metrics
    SAFE_DIVIDE(TotalAssetsInMillions * 1000000, NULLIF(Number_Investment_Advisory_Clients, 0)) as AUM_Per_Client,
    SAFE_DIVIDE(TotalAssetsInMillions * 1000000, NULLIF(Number_Employees, 0)) as AUM_Per_Employee,
    
    -- Growth indicators
    AUMGrowthRate_1Year * AUMGrowthRate_5Year as Growth_Momentum,
    CASE WHEN AUMGrowthRate_1Year > AUMGrowthRate_5Year THEN 1 ELSE 0 END as Accelerating_Growth,
    
    -- Firm stability
    Date_Became_Rep_Number_Of_Years + Date_Of_Hire_At_Current_Firm_Years as Firm_Stability_Score,
    CASE WHEN Date_Became_Rep_Number_Of_Years > 10 THEN 1 ELSE 0 END as Is_Veteran_Advisor,
    
    -- Client focus
    SAFE_DIVIDE(Number_Clients_HNW_Individuals, NULLIF(Number_Investment_Advisory_Clients, 0)) as HNW_Client_Ratio,
    SAFE_DIVIDE(Assets_In_Millions_Individuals, NULLIF(TotalAssetsInMillions, 0)) as Individual_Asset_Ratio,
    
    -- Metropolitan area dummy variables
    CASE WHEN Home_MetropolitanArea LIKE '%New York%' THEN 1 ELSE 0 END as Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ,
    CASE WHEN Home_MetropolitanArea LIKE '%Los Angeles%' THEN 1 ELSE 0 END as Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA,
    CASE WHEN Home_MetropolitanArea LIKE '%Chicago%' THEN 1 ELSE 0 END as Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN,
    CASE WHEN Home_MetropolitanArea LIKE '%Dallas%' THEN 1 ELSE 0 END as Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX,
    CASE WHEN Home_MetropolitanArea LIKE '%Miami%' THEN 1 ELSE 0 END as Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL
    
  FROM deduplicated_data
  WHERE dedup_rank = 1  -- Keep only the most recent record per CRD
)

SELECT * FROM engineered_features;
```

**Step 4: CRD Matching & Salesforce Integration**
```sql
-- Create the final lead scoring table with Discovery Data attached
CREATE OR REPLACE TABLE savvy_analytics.lead_scores_with_discovery AS
SELECT 
    sf.Id as lead_id,
    sf.FA_CRD__c,
    sf.full_prospect_id__c,
    sf.Stage_Entered_Contacting__c,
    sf.Stage_Entered_Call_Scheduled__c,
    
    -- Discovery Data fields (69 features)
    dd.TotalAssetsInMillions,
    dd.Number_Employees,
    dd.AUMGrowthRate_1Year,
    dd.AUMGrowthRate_5Year,
    dd.Home_MetropolitanArea,
                -- ... all 69 discovery features
    
    -- Model scoring
    CURRENT_TIMESTAMP() as scored_at,
    CASE 
        WHEN dd.TotalAssetsInMillions > 500 AND dd.AUMGrowthRate_1Year > 10 THEN 0.25
        WHEN dd.TotalAssetsInMillions > 100 AND dd.AUMGrowthRate_1Year > 5 THEN 0.15
        WHEN dd.TotalAssetsInMillions > 50 THEN 0.10
        ELSE 0.05
    END as prob_mql_30d,
    
    CASE 
        WHEN prob_mql_30d > 0.20 THEN 'A'
        WHEN prob_mql_30d > 0.10 THEN 'B' 
        ELSE 'C'
    END as tier,
    
    -- Data quality flags
    CASE WHEN dd.RepCRD IS NOT NULL THEN TRUE ELSE FALSE END as has_discovery_data,
    dd.territory_source

FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;
```

**Step 5: Data Quality Validation**
```sql
-- Validate the merge success rates (matching your analyze_merge_operations output)
SELECT 
    COUNT(*) as total_salesforce_leads,
    COUNT(dd.RepCRD) as matched_with_discovery,
    ROUND(COUNT(dd.RepCRD) / COUNT(*) * 100, 1) as match_rate_percent,
    COUNT(DISTINCT dd.territory_source) as territories_covered
FROM `savvy-gtm-analytics.LeadScoring.lead_scores_with_discovery`;
```

**Daily Model Scoring (Automated)**
```sql
-- Daily scoring with monthly Discovery Data cache
CREATE OR REPLACE TABLE savvy_analytics.lead_scores AS
SELECT 
    sf.Id as lead_id,
    sf.FA_CRD__c,
    sf.full_prospect_id__c,
    CURRENT_TIMESTAMP() as scored_at,
    -- Model scoring using cached Discovery Data
    CASE 
        WHEN dd.TotalAssetsInMillions > 500 AND dd.AUMGrowthRate_1Year > 10 THEN 0.25
        WHEN dd.TotalAssetsInMillions > 100 AND dd.AUMGrowthRate_1Year > 5 THEN 0.15
        WHEN dd.TotalAssetsInMillions > 50 THEN 0.10
        ELSE 0.05
    END as prob_mql_30d,
    CASE 
        WHEN prob_mql_30d > 0.20 THEN 'A'
        WHEN prob_mql_30d > 0.10 THEN 'B' 
        ELSE 'C'
    END as tier
FROM savvy_analytics.sfdc_leads_current sf
LEFT JOIN savvy_analytics.discovery_reps_current dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;
```

**Production Model Scoring Pipeline (BigQuery SQL)**
```sql
-- Production model scoring using BigQuery ML or Vertex AI
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.lead_scores_production` AS
SELECT 
    sf.Id as lead_id,
    sf.FA_CRD__c,
    sf.full_prospect_id__c,
    sf.Stage_Entered_Contacting__c,
    sf.Stage_Entered_Call_Scheduled__c,
    CURRENT_TIMESTAMP() as scored_at,
    
    -- Model scoring using production model artifacts
    ML.PREDICT(
        MODEL `savvy-gtm-analytics.LeadScoring.production_lead_scoring_model`,
        (
            SELECT 
                sf.Id,
                dd.TotalAssetsInMillions,
                dd.AUMGrowthRate_1Year,
                dd.AUMGrowthRate_5Year,
                dd.Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ,
                dd.Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA,
                dd.Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN,
                dd.Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX,
                dd.Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL,
                -- ... all 67 engineered features
                dd.AUM_Per_Client,
                dd.Growth_Momentum,
                dd.Firm_Stability_Score,
                dd.HNW_Client_Ratio
            FROM `savvy-gtm-analytics.LeadScoring.sfdc_leads_current` sf
            LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` dd 
                ON sf.FA_CRD__c = dd.RepCRD
            WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
        )
    ).predicted_probability as prob_mql_30d,
    
    -- Tier assignment based on calibrated probabilities
    CASE 
        WHEN ML.PREDICT(...).predicted_probability > 0.20 THEN 'A'
        WHEN ML.PREDICT(...).predicted_probability > 0.10 THEN 'B' 
        ELSE 'C'
    END as tier,
    
    -- Data quality flags
    CASE WHEN dd.RepCRD IS NOT NULL THEN TRUE ELSE FALSE END as has_discovery_data,
    dd.territory_source

FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;
```

**Daily Salesforce Score Updates (Managed Service)**
```sql
-- Automated Salesforce sync via Cloud Functions or Cloud Run
-- This would be implemented as a managed service, not Python scripts

-- Step 1: Extract scores for Salesforce update
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.salesforce_score_updates` AS
SELECT 
    lead_id,
    tier,
    prob_mql_30d,
    scored_at,
    has_discovery_data
FROM `savvy-gtm-analytics.LeadScoring.lead_scores_production`
WHERE scored_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY);

-- Step 2: Export to Cloud Storage for Salesforce Bulk API
EXPORT DATA OPTIONS(
  uri='gs://savvy-lead-scoring/salesforce_updates/lead_scores_*.csv',
  format='CSV',
  overwrite=true
) AS
SELECT * FROM `savvy-gtm-analytics.LeadScoring.salesforce_score_updates`;
```

### 10.2 Monthly Batch Processing Workflow

**Monthly Discovery Data Upload (Manual - Day 1)**
1. **Download Discovery Data:** Manual download of T1, T2, T3 CSV files
2. **Upload to BigQuery:** Upload CSVs to staging tables
3. **Process & Merge:** Run your `create_discovery_data_pkl()` logic in BigQuery
4. **Update Discovery Tables:** Refresh `discovery_reps_current` and `discovery_firms_current`
5. **Quality Check:** Validate CRD matching rates and data completeness

**Daily Automated Pipeline (Days 2-30)**
1. **Salesforce Sync:** Daily full refresh of Lead object (automated)
2. **Model Scoring:** Daily scoring using cached Discovery Data (automated)
3. **Salesforce Updates:** Daily score updates via Bulk API (automated)
4. **Monitoring:** Daily data quality and performance checks (automated)

**Monthly Cycle Reset (Day 30)**
- Repeat Discovery Data upload process
- Archive previous month's Discovery Data
- Update model if needed based on performance metrics

**Detailed Pipeline Phase Breakdown:**

1. **Data Reconciliation Phase:**
   - **Three-Stage Merging:** Salesforce + Representatives + Firm data
   - **CRD Validation:** Ensure consistent identifier matching across sources
   - **Missing Data Resolution:** Targeted searches for missing CRDs
   - **Quality Reporting:** Generate comprehensive merge success metrics

2. **Advanced Data Cleaning Phase (PRODUCTION-VALIDATED):**
   - **Column Deduplication:** Remove identical columns (correlation > 0.9999) and highly correlated columns (>0.98)
   - **Data Type Standardization:** Multi-CSV type alignment with `low_memory=False` for proper inference
   - **Missing Value Handling:** Standardize NA values: `['', 'NA', 'N/A', 'null', 'NULL', 'None']`
   - **Duplicate Record Handling:** Remove duplicates based on `FA_CRD__c`, `RepCRD`, `RIAFirmCRD` combinations
   - **Territory Data Reconciliation:** Handle overlapping records across T1/T2/T3 exports

3. **Feature Engineering Phase:**
   - **Base Feature Extraction:** Process 31 direct discovery features
   - **Geographic Encoding:** Create 5 metropolitan area dummy variables
   - **Advanced Engineering:** Generate 31 complex derived features
   - **Feature Validation:** Ensure all 69 features meet quality standards

4. **Data Quality Assurance Phase:**
   - **Multi-Source Validation:** Check data consistency across sources
   - **Feature Completeness:** Monitor null rates and coverage metrics
   - **Temporal Validation:** Ensure no future data leakage
   - **Business Rule Validation:** Verify feature calculations and logic

5. **Model Scoring Phase:**
   - **Feature Preparation:** Apply scaling and imputation to all features
   - **Model Inference:** Generate probability scores using XGBoost
   - **Calibration:** Apply segment-specific probability calibration
   - **SHAP Analysis:** Generate feature contribution explanations

6. **Tier Assignment Phase:**
   - **Capacity Calculation:** Determine daily SGA capacity
   - **Priority Scoring:** Apply discovery-based priority boosts
   - **Tier Assignment:** Generate A/B/C tier classifications
   - **Tie Breaking:** Handle ties with secondary sorting criteria

7. **Data Persistence Phase:**
   - **Score Storage:** Write to `savvy_analytics.lead_scores` table
   - **Feature Snapshots:** Store feature values for auditability
   - **SHAP Storage:** Persist top 10 feature contributions
   - **Quality Metrics:** Record data quality scores and coverage

8. **Salesforce Integration Phase:**
   - **Field Updates:** Update `Score_Tier__c` and related fields
   - **Signal Population:** Generate human-readable explanations
   - **Queue Refresh:** Update SGA list views and priorities
   - **UI Updates:** Refresh dashboard and reporting interfaces

9. **Monitoring & Alerting Phase:**
    - **Performance Metrics:** Track model accuracy and business impact
    - **Data Quality Alerts:** Monitor feature drift and coverage
    - **Pipeline Health:** Check processing success rates and latency
    - **Business Reporting:** Generate daily summary reports

### 10.2 Feature Store Architecture
savvy_analytics/
├── raw/
│   ├── sfdc_leads/
│   ├── marketpro_enrichment/
│   └── discovery_firmographics/
├── staging/
│   ├── lead_features_base/
│   ├── discovery_features_computed/
│   └── feature_quality_scores/
├── marts/
│   ├── vw_model_features_contacted_mql/
│   ├── lead_scores/
│   └── model_performance_metrics/
└── ml/
    ├── training_datasets/
    ├── model_artifacts/
    └── feature_importance/

### 10.3 Fail-Safe & Degradation
**Graceful degradation hierarchy:**
1. Full model with all features
2. Fallback to MarketPro-only if discovery >50% missing
3. Basic heuristic scoring if model service fails
4. Maintain yesterday's scores if complete pipeline failure

- *"Design a data quality check framework that validates all 100+ features before scoring, with feature-specific thresholds and fallback strategies."*
- *"Generate idempotent SQL to merge daily scores handling discovery data updates that arrive late (e.g., T+1 updates for T-0 scores)."*
- *"Write a runbook for handling discovery vendor API outages including cache strategies and quality degradation communications."*

---

## 11) Salesforce Enablement (Enhanced)

### 11.1 UI Components
**SGA Homepage:**
- **Smart Lists:** Tier A/B/C with discovery insights badges
- **Lead cards:** Show top 3 discovery signals (e.g., "↗ 25% AUM growth", "85 HNW clients", "3 years at firm")
- **Peer benchmarks:** "Similar advisors: 12% MQL rate"

### 11.2 Discovery Insights Tooltip
Format: *"Why this lead?"*
- **Growth Signal:** "Growing 15% annually vs 5% peer average"
- **Size Signal:** "$450M AUM, top 10% in market"
- **Timing Signal:** "3.5 years at firm (peak move window)"
- **Fit Signal:** "80% HNW clients matches Savvy sweet spot"

### 11.3 SGA Training Materials
- Discovery data interpretation guide
- Feature importance cheat sheet
- "What moves the needle" playbook by segment

---

## 12) Security & Privacy (Enhanced)

### 12.1 Data Governance
- **PII handling:** Hash all direct identifiers before modeling
- **Vendor data:** Separate access controls for MarketPro vs Discovery
- **Feature lineage:** Track data provenance for all 100+ features
- **Right to deletion:** Cascade deletes through feature store

### 12.2 Access Controls
- Read-only service accounts per data source
- Feature store access via views with column-level security
- Model artifacts encrypted at rest
- Audit logs for all score updates

---

## 13) Implementation Roadmap

## ✅ **COMPLETED WORK**

### **Phase 0: Data Foundation**

#### **Week 1: Discovery Data Pipeline Implementation** ✅ COMPLETE
- **✅ Created BigQuery dataset structure:**
  - `savvy-gtm-analytics.LeadScoring` (processing tables)
  - `savvy-gtm-analytics.SavvyGTMData` (core CRM data)
- **✅ Uploaded MarketPro data (T1, T2, T3 territories):**
  - T1: 198,024 records (41.4%)
  - T2: 173,631 records (36.3%) 
  - T3: 106,246 records (22.2%)
  - **Total: 477,901 records**
- **✅ Created `discovery_reps_current` table** with SAFE_CAST handling for data quality issues
- **✅ Resolved "Osseo" data issue** using SAFE_CAST for numeric conversions
- **✅ Implemented proper deduplication** (462,825 unique reps from 477,901 records)

#### **Week 2: Feature Engineering Pipeline** ✅ COMPLETE
- **✅ Implemented 3-stage feature engineering architecture:**
  - **Stage 1:** 31 base features (direct mapping from discovery data)
  - **Stage 2:** 5 geographic features (metropolitan area dummy variables)
  - **Stage 3:** 31 advanced features (complex derived metrics and ratios)
- **✅ Created `discovery_reps_with_features` table** with all 67 engineered features
- **✅ Passed Week 2 validation checkpoints:**
  - Multicollinearity: All correlations < 0.95 (ACCEPTABLE)
  - Feature Distribution: Proper data ranges and distributions
  - Feature Quality: All engineered features working correctly

### **Key Data Quality Metrics Achieved:**
- **Data Completeness:** RepCRD (100%), AUM (93.3%), Growth Rates (90.3%)
- **Feature Coverage:** All 67 engineered features successfully created (expanding to 69 in Phase 1 with temporal features)
- **Geographic Distribution:** NYC (3.8%), LA (1.5%), Chicago (1.6%), Dallas (2.0%), Miami (1.4%)
- **Professional Credentials:** Series 7 (69.1%), CFP (17.4%), Primary RIA (96.8%)

---

## 🚧 **REMAINING WORK**

### **Phase 0, Week 3: Validation & Baseline Metrics** (CURRENT PHASE)

#### **Step 3.1: Class Distribution Analysis** ✅ COMPLETE

**✅ COMPLETED:** Comprehensive class distribution analysis completed on October 27, 2025.

**Key Findings:**
- **Overall Conversion Rate:** 4.32% (all time) → 3.89% (30-day window)
- **Class Imbalance Ratio:** 24.18:1 (negative:positive) - SEVERE imbalance
- **Discovery Data Coverage:** 94.82% CRD matching rate - EXCELLENT
- **AUM Tier Performance:** Smaller firms convert higher (<$100M: 6.13% vs >$500M: 3.58%)
- **Metro Area Performance:** Major metros underperform (NYC: 2.72%, LA: 2.60%)
- **Temporal Patterns:** Weekend contacts show premium (Saturday: 8.72% vs weekday avg: 4.3%)

**Critical Insights:**
- **Severe class imbalance** requires sophisticated SMOTE vs. Pos_Weight testing
- **Segment variations** suggest need for AUM tier-specific modeling
- **Data quality issues** detected (negative days to conversion)
- **Modeling dataset:** 40,595 samples ready for Phase 1

**Files Created:**
- `Step_3_1_Class_Distribution_Analysis.sql` - Complete analysis queries
- `Step_3_1_Class_Distribution_Analysis_Results.md` - Comprehensive results summary

**Status:** ✅ **READY FOR STEP 3.2**

#### **Step 3.2: Temporal Leakage Detection**

**Input Artifacts:**
- `savvy-gtm-analytics.SavvyGTMData.Lead`
- `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features`
- `Step_3_1_Class_Distribution_Analysis_Results.md` (for context)

**Output Artifacts:**
- `step_3_2_leakage_report.md` (markdown file containing query results and analysis)

**AGENTIC TASK:**

You are a data validation agent. Your task is to check for temporal data leakage.

1. **Execute** the SQL query from the `🔑 REFERENCE IMPLEMENTATION:` block.

2. **Analyze** the results, specifically the `leakage_records` and `leakage_rate_percent` fields.

3. **Create** a new file named `step_3_2_leakage_report.md`.

4. **Write** the results of the query into this file in a clear, tabular format.

5. **Document** any instances where discovery data timestamps occur after the contacted timestamp, including specific examples.

6. **Validate** that all discovery features are based on historical data only.

**🔑 REFERENCE IMPLEMENTATION:**

```sql
-- Week 3 Validation Checkpoint 3.2: Temporal Leakage Detection
SELECT 
    'Future Data Leakage Check' as validation_type,
    COUNT(*) as total_records,
    COUNT(CASE 
        WHEN dd.processed_at > sf.Stage_Entered_Contacting__c 
        THEN 1 
    END) as leakage_records,
    ROUND(COUNT(CASE 
        WHEN dd.processed_at > sf.Stage_Entered_Contacting__c 
        THEN 1 
    END) / COUNT(*) * 100, 2) as leakage_rate_percent
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;
```

**✅ VALIDATION GATE:**

Proceed to Step 3.3 **only if** `leakage_records` is 0 in `step_3_2_leakage_report.md`. If `leakage_records` > 0, **STOP** and tag @HumanDeveloper for immediate review.

#### **Step 3.3: SMOTE/Class Balancing Validation**

**Input Artifacts:**
- `savvy-gtm-analytics.SavvyGTMData.Lead`
- `step_3_2_leakage_report.md` (validation that Step 3.2 passed)
- `Step_3_1_Class_Distribution_Analysis_Results.md` (for baseline metrics)

**Output Artifacts:**
- `step_3_3_class_imbalance_analysis.md` (analysis report with class distribution metrics)
- `step_3_3_training_dataset.csv` (prepared dataset ready for model training with target_label column)

**AGENTIC TASK:**

You are a data preparation agent. Your task is to validate class imbalance and prepare data for SMOTE/Pos_Weight testing.

1. **Execute** the SQL query from the `🔑 REFERENCE IMPLEMENTATION:` block to calculate class imbalance metrics.

2. **Verify** the imbalance ratio matches expected ranges (baseline: ~24:1 from Step 3.1).

3. **Create** `step_3_3_training_dataset.csv` containing all features plus the `target_label` column.

4. **Generate** `step_3_3_class_imbalance_analysis.md` with:
   - Total samples count
   - Positive/negative class counts and percentages
   - Imbalance ratio
   - Distribution analysis of positive vs negative samples

5. **Validate** dataset readiness for SMOTE and Pos_Weight testing approaches.

**🔑 REFERENCE IMPLEMENTATION:**

```sql
-- Week 3 Validation Checkpoint 3.3: SMOTE/Class Balancing Validation
SELECT 
    'Class Imbalance Metrics' as metric_type,
    COUNT(*) as total_samples,
    COUNT(CASE WHEN target_label = 1 THEN 1 END) as positive_samples,
    COUNT(CASE WHEN target_label = 0 THEN 1 END) as negative_samples,
    ROUND(COUNT(CASE WHEN target_label = 1 THEN 1 END) / COUNT(*) * 100, 2) as positive_class_percent,
    ROUND(COUNT(CASE WHEN target_label = 0 THEN 1 END) / COUNT(CASE WHEN target_label = 1 THEN 1 END), 2) as imbalance_ratio
FROM (
    SELECT 
        sf.Id,
        CASE 
            WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL 
            AND DATE(sf.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(sf.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
            THEN 1 
            ELSE 0 
        END as target_label
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
    WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
        AND DATE(sf.Stage_Entered_Contacting__c) <= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
);
```

**✅ VALIDATION GATE:**

Proceed to Week 4 **only if** both `step_3_3_class_imbalance_analysis.md` and `step_3_3_training_dataset.csv` are successfully created, and the imbalance ratio is within expected range (15:1 to 30:1). If files are missing or ratio is outside expected range, **STOP** and tag @HumanDeveloper for review.

---

### **Phase 1: Model Development** (3 weeks)

#### **Week 4: Feature Selection and Model Training**

**Note:** Based on Step 3.1 Class Distribution Analysis findings (which showed weekend contacts have a premium conversion rate of 8.72% vs weekday average of 4.3%), we are adding two new temporal features to our feature engineering pipeline:

- **`Day_of_Contact`**: Day of week when lead was contacted (1=Monday, 7=Sunday)
- **`Is_Weekend_Contact`**: Boolean flag indicating if contact occurred on Saturday or Sunday

These features expand our total feature count from **67 to 69 features**.

**Input Artifacts:**
- `step_3_3_training_dataset.csv` (training data with target_label)
- `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` (69 features)
- `savvy-gtm-analytics.SavvyGTMData.Lead` (for extracting Day_of_Contact and Is_Weekend_Contact)
- `step_3_3_class_imbalance_analysis.md` (for class imbalance context)

**Output Artifacts:**
- `model_v1.pkl` (trained XGBoost model file)
- `feature_importance_v1.csv` (feature importance rankings)
- `feature_selection_report_v1.md` (univariate screening and VIF pre-filter results)
- `model_training_report_v1.md` (hyperparameter tuning results, CV performance, SMOTE vs Pos_Weight comparison)
- `selected_features_v1.json` (list of final selected feature names)

**AGENTIC TASK:**

You are a machine learning engineer. Your task is to train the V1 model and identify the most predictive features.

1. **Load** `step_3_3_training_dataset.csv`.

2. **Add Temporal Features:** Create the `Day_of_Contact` and `Is_Weekend_Contact` features from the `Stage_Entered_Contacting__c` column. You now have **69 total features**.

3. **Set Reproducibility:** Ensure all model training, splits, and stochastic processes (like SMOTE) use a fixed `random_state=42`.

4. **Implement Pre-filters:**
   * **IV Filter:** Remove features with an Information Value (IV) < 0.02.
   * **VIF Filter:** Remove features with a Variance Inflation Factor (VIF) > 10.
   * **Document** all removed features in `feature_selection_report_v1.md`.

5. **Test Imbalance Strategies:**
   * Using **all remaining features** that passed the pre-filters, systematically test SMOTE vs. `scale_pos_weight`.
   * Use blocked time-series cross-validation (30-day gaps, `random_state=42`) to evaluate.
   * Document the winning strategy (e.g., `scale_pos_weight`) in `model_training_report_v1.md`.

6. **Train Final Model:**
   * Train the final XGBoost model (with `random_state=42`, the winning imbalance strategy, and tuned hyperparameters) on **all** pre-filtered features.
   * Save this model as `model_v1.pkl`.

7. **Generate Importance (Audit):**
   * Using **SHAP** on the *final* `model_v1.pkl`, generate the feature importance for all features used in the model.
   * Save this list as `feature_importance_v1.csv` and the list of feature names as `selected_features_v1.json`.

8. **Save Reports:** Create `model_training_report_v1.md` with all CV performance metrics and the SMOTE vs. Pos_Weight comparison.

**🔑 REFERENCE IMPLEMENTATION:**

```python
# Feature Selection Pipeline
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
import xgboost as xgb

def feature_selection_pipeline(X, y):
    # 1. Univariate screening
    selector = SelectKBest(f_classif, k=50)
    X_selected = selector.fit_transform(X, y)
    
    # 2. Multicollinearity check
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    vif_data = pd.DataFrame()
    vif_data["Feature"] = X.columns
    vif_data["VIF"] = [variance_inflation_factor(X.values, i) for i in range(len(X.columns))]
    
    # 3. Recursive feature elimination
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rfe = RFE(rf, n_features_to_select=50)
    X_rfe = rfe.fit_transform(X_selected, y)
    
    return X_rfe, rfe.support_
```

**✅ VALIDATION GATE:**

Proceed to Week 5 **only if** `model_v1.pkl` and `feature_importance_v1.csv` are successfully saved to disk, and `model_training_report_v1.md` shows AUC-PR > 0.20 (baseline). If files are missing or performance is below baseline, **STOP** and tag @HumanDeveloper for review.

#### **Week 5: Calibration and SHAP Analysis**

**Input Artifacts:**
- `model_v1.pkl` (trained model from Week 4)
- `feature_importance_v1.csv` (feature rankings)
- `step_3_3_training_dataset.csv` (training data for SHAP analysis)
- `Current_Lead_Scoring_Model.md` (section 6.2 for m5 baseline comparison)

**Output Artifacts:**
- `model_v1_calibrated.pkl` (calibrated model with segment-specific calibrators)
- `shap_summary_plot_v1.png` (SHAP summary plot for top 30 features)
- `shap_feature_comparison_report_v1.md` (comparison vs m5 model importance)
- `cohort_analysis_report_v1.md` (cohort analysis by AUM tier, growth trajectory, metro area)
- `salesforce_drivers_v1.csv` (top 5 positive drivers per prediction for Salesforce tooltips)

**AGENTIC TASK:**

You are a model validation and explainability agent. Your task is to calibrate the model and generate comprehensive SHAP analysis.

1. **Load** `model_v1.pkl` and training data.

2. **Fit** segment-specific calibrators for AUM tiers (<$100M, $100-500M, >$500M) using Platt scaling.

3. **Generate** SHAP summary plots for top 30 features and save as `shap_summary_plot_v1.png`.

4. **Create** per-prediction SHAP explanations for all test set samples.

5. **Implement** cohort analysis by AUM tier, growth trajectory, and metro area.

6. **Persist** top 5 positive drivers per prediction as `salesforce_drivers_v1.csv` for Salesforce tooltips.

7. **Compare** new model SHAP importance vs. m5 model importance:
   - Generate SHAP summary plot for the new model
   - Compare directly against documented "Top 25 Most Important Features" from m5 model (`Current_Lead_Scoring_Model.md`, section 6.2)
   - Answer: Did the new model discover the same "truth"?
   - Answer: Did `Multi_RIA_Relationships` remain the top feature?
   - If not, provide business rationale for differences
   - Document all findings in `shap_feature_comparison_report_v1.md`

8. **Save** calibrated model as `model_v1_calibrated.pkl`.

**✅ VALIDATION GATE:**

Proceed to Week 6 **only if** `model_v1_calibrated.pkl`, `shap_summary_plot_v1.png`, and `shap_feature_comparison_report_v1.md` are successfully created. The comparison report must address whether `Multi_RIA_Relationships` remained the top feature and provide business rationale for any significant ranking differences. If files are missing or comparison report is incomplete, **STOP** and tag @HumanDeveloper for review.

#### **Week 6: Backtesting and Performance Validation**

**Input Artifacts:**
- `model_v1_calibrated.pkl` (calibrated model from Week 5)
- `step_3_3_training_dataset.csv` (full training dataset)
- `feature_selection_report_v1.md` (feature selection details)
- `model_training_report_v1.md` (initial training metrics)

**Output Artifacts:**
- `backtesting_report_v1.md` (temporal performance stability analysis)
- `performance_validation_report_v1.md` (comprehensive validation metrics)
- `overfitting_analysis_v1.md` (train vs test performance gap analysis)
- `business_impact_metrics_v1.csv` (MQLs per 100 dials and other business KPIs)
- `cv_consistency_report_v1.md` (cross-validation performance consistency across folds)

**AGENTIC TASK:**

You are a model validation agent. Your task is to perform comprehensive backtesting and validate model performance.

1. **Load** `model_v1_calibrated.pkl` and historical data.

2. **Perform** temporal performance stability analysis across different time periods.

3. **Validate** business impact metrics:
   - Calculate MQLs per 100 dials at different score thresholds
   - Estimate pipeline value at each tier
   - Document lift metrics vs. baseline

4. **Detect** overfitting by comparing train vs test performance:
   - Calculate performance gap metrics
   - Identify features contributing to overfitting
   - Document findings in `overfitting_analysis_v1.md`

5. **Implement** cross-validation performance consistency checks:
   - Analyze CV performance across all folds
   - Calculate coefficient of variation for key metrics
   - Identify any unstable performance patterns

6. **Generate** comprehensive performance reports with all metrics and validations.

**✅ VALIDATION GATE:**

Proceed to Week 7 **only if** all output artifacts are created and `performance_validation_report_v1.md` shows:
- Train-test performance gap < 10% (AUC-PR difference)
- CV coefficient of variation < 15% for key metrics
- Business impact metrics showing > 30% lift potential

If validation fails or artifacts are missing, **STOP** and tag @HumanDeveloper for review.

---

### **Phase 2: Pre-Production** (2 weeks)

#### **Week 7: Shadow Scoring and Pipeline Stress Testing**

**Input Artifacts:**
- `model_v1_calibrated.pkl` (calibrated model)
- `salesforce_drivers_v1.csv` (SHAP drivers for tooltips)
- `selected_features_v1.json` (final feature list)
- Production data pipeline access (`savvy-gtm-analytics.SavvyGTMData.Lead`)

**Output Artifacts:**
- `shadow_scoring_results_7day.md` (7-day shadow mode scoring results)
- `pipeline_stress_test_report_v1.md` (stress test results for data volume and quality)
- `shadow_mode_performance_metrics_v1.csv` (daily performance metrics)
- `production_readiness_checklist_v1.md` (checklist confirming all validation gates passed)
- `alerting_config_v1.json` (automated alerting configuration for performance degradation)

**AGENTIC TASK:**

You are a production readiness agent. Your task is to run shadow scoring and stress test the pipeline.

1. **Deploy** `model_v1_calibrated.pkl` in shadow mode (scores generated but not used in production).

2. **Run** shadow mode scoring for 7 consecutive days, scoring all new leads as they enter "Contacting" stage.

3. **Monitor** daily performance metrics:
   - Scoring success rate
   - Score distribution
   - Feature availability rates
   - Processing latency

4. **Implement** pipeline stress tests:
   - Test with 2x expected data volume
   - Test with missing features (simulate data quality issues)
   - Test with class imbalance scenarios
   - Validate error handling and recovery

5. **Validate** class imbalance handling in production-like environment.

6. **Create** automated alerting configuration for:
   - Scoring failure rate > 5%
   - Feature drift > 5% (PSI)
   - Performance degradation > 10%
   - Data freshness issues

7. **Generate** production readiness checklist confirming all validation gates passed.

**✅ VALIDATION GATE:**

Proceed to Week 8 **only if**:
- Shadow mode scoring runs successfully for 7 days with > 95% success rate
- All stress tests pass without pipeline failures
- `production_readiness_checklist_v1.md` shows all items checked
- Alerting configuration is deployed and tested

If any validation fails, **STOP** and tag @HumanDeveloper for review.

#### **Week 8: SGA Training and Salesforce Integration**

**Input Artifacts:**
- `salesforce_drivers_v1.csv` (top 5 drivers per prediction)
- `shap_feature_comparison_report_v1.md` (feature importance insights)
- `cohort_analysis_report_v1.md` (segment-specific insights)
- `feature_importance_v1.csv` (feature rankings)
- `selected_features_v1.json` (final feature list)

**Output Artifacts:**
- `salesforce_field_mapping_v1.csv` (mapping of all 69 features to Salesforce fields)
- `sga_training_guide_v1.md` (comprehensive SGA training materials)
- `feature_importance_cheat_sheet_v1.pdf` (visual cheat sheet for SGA)
- `what_moves_needle_playbook_v1.md` (segment-specific playbook)
- `salesforce_ui_spec_v1.md` (specification for lead scoring UI updates)

**AGENTIC TASK:**

You are a sales enablement agent. Your task is to prepare Salesforce integration and SGA training materials.

1. **Create** Salesforce field mapping document for all 69 features (67 discovery + 2 temporal):
   - Map each feature to Salesforce field name
   - Include data types and update frequency
   - Document field visibility and permissions

2. **Develop** SGA training materials for discovery data interpretation:
   - Explain what each feature means
   - Show how to interpret feature values
   - Provide examples of high-value vs low-value patterns

3. **Generate** feature importance cheat sheet:
   - Visual representation of top 30 features
   - Color-coded by importance tier
   - Quick reference format

4. **Create** "What moves the needle" playbook by segment:
   - AUM tier-specific insights (<$100M, $100-500M, >$500M)
   - Metro area-specific patterns
   - Growth trajectory recommendations
   - Include actionable insights from cohort analysis

5. **Design** Salesforce UI updates for lead scoring display:
   - Score display component
   - Top 5 drivers tooltip (from `salesforce_drivers_v1.csv`)
   - Segment-specific recommendations
   - Visual score buckets (Cold, Cool, Warm, Hot, Very Hot)

**✅ VALIDATION GATE:**

Proceed to Weeks 9-12 **only if** all output artifacts are created and:
- Salesforce field mapping includes all 69 features
- SGA training guide is complete with examples
- Feature importance cheat sheet is visually clear
- Salesforce UI spec is approved by product team
- "What moves the needle" playbook is actionable for each segment

If any artifact is missing or incomplete, **STOP** and tag @HumanDeveloper for review.

---

### **Phase 3: Experiment** (4 weeks)

#### **Weeks 9-12: Randomized A/B Test**

**Input Artifacts:**
- `model_v1_calibrated.pkl` (production model)
- `salesforce_drivers_v1.csv` (SHAP drivers)
- `salesforce_field_mapping_v1.csv` (feature mappings)
- `production_readiness_checklist_v1.md` (confirming readiness)
- Production Salesforce Lead data access

**Output Artifacts:**
- `ab_test_assignments_v1.csv` (treatment/control assignments with blocking)
- `ab_test_interim_analysis_week10.md` (interim analysis results at week 10)
- `ab_test_final_analysis_v1.md` (final statistical analysis)
- `ab_test_daily_metrics_v1.csv` (daily monitoring metrics)
- `ab_test_statistical_report_v1.md` (statistical significance testing results)

**AGENTIC TASK:**

You are an experimentation agent. Your task is to implement and monitor the A/B test.

1. **Implement** lead-level randomization with blocking by AUM tier:
   - Randomly assign leads to treatment (model scoring) or control (no scoring)
   - Ensure balanced assignment within each AUM tier block
   - Document assignments in `ab_test_assignments_v1.csv`

2. **Ensure** balanced discovery data coverage in treatment/control:
   - Verify feature availability is similar across groups
   - Check CRD matching rates are balanced
   - Validate no systematic differences in data quality

3. **Monitor** primary KPI daily: MQLs per 100 dials within 30 days:
   - Track conversion rates for treatment vs control
   - Calculate lift metrics daily
   - Record in `ab_test_daily_metrics_v1.csv`

4. **Implement** interim analysis at week 10:
   - Perform statistical significance testing
   - Check for safety issues or unexpected effects
   - Document findings in `ab_test_interim_analysis_week10.md`
   - Decide: continue, stop early (if significant), or adjust

5. **Perform** final analysis with statistical significance testing:
   - Calculate final lift metrics
   - Perform hypothesis testing (treatment vs control)
   - Validate p-value < 0.05 for primary KPI
   - Generate comprehensive statistical report

**✅ VALIDATION GATE:**

Proceed to Week 13+ **only if**:
- Final analysis shows statistically significant lift (p < 0.05) in MQLs per 100 dials
- Treatment group shows > 50% lift vs control
- No safety issues or adverse effects detected
- `ab_test_final_analysis_v1.md` contains complete statistical validation

If statistical significance is not achieved or lift is < 50%, **STOP** and tag @HumanDeveloper for review and model iteration.

---

### **Phase 4: Production & Scale** (Ongoing)

#### **Week 13+: Full Rollout**

**Input Artifacts:**
- `model_v1_calibrated.pkl` (validated production model)
- `ab_test_final_analysis_v1.md` (successful A/B test results)
- `alerting_config_v1.json` (alerting configuration)
- `production_readiness_checklist_v1.md` (readiness confirmation)
- `salesforce_ui_spec_v1.md` (UI specifications)

**Output Artifacts:**
- `production_health_dashboard_v1.json` (dashboard configuration for daily health checks)
- `monitoring_schedule_v1.yaml` (automated monitoring schedule)
- `feature_drift_detection_report_monthly_v1.md` (monthly drift reports)
- `model_refresh_protocol_v1.md` (quarterly refresh procedures)
- `production_runbook_v1.md` (operational runbook for ongoing maintenance)

**AGENTIC TASK:**

You are a production operations agent. Your task is to implement full production rollout with continuous monitoring.

1. **Deploy** `model_v1_calibrated.pkl` to production scoring pipeline.

2. **Implement** daily production health checks:
   - Scoring success rate monitoring
   - Latency tracking
   - Error rate monitoring
   - Feature availability checks

3. **Set up** weekly class imbalance monitoring:
   - Track positive class rate in production
   - Compare to training distribution
   - Alert if drift > 5%

4. **Implement** monthly feature drift detection:
   - Calculate Population Stability Index (PSI) for all features
   - Identify features with PSI > 0.25
   - Generate drift reports

5. **Configure** automated alerting for performance degradation:
   - Use `alerting_config_v1.json` as baseline
   - Set up alerts for: scoring failures, feature drift, model performance drop
   - Configure escalation procedures

6. **Establish** quarterly model refresh cycles:
   - Document refresh procedures
   - Define retraining triggers
   - Create validation checklist for refreshed models

7. **Create** production runbook for ongoing operations.

**✅ VALIDATION GATE:**

Production rollout is considered successful **only if**:
- Daily health checks run successfully for 30 consecutive days
- Weekly monitoring shows class imbalance within acceptable range
- Monthly drift detection shows PSI < 0.25 for all critical features
- Alerting system triggers appropriately without false positives
- Model refresh protocol is documented and tested

If any monitoring fails or shows degradation, **STOP** and tag @HumanDeveloper for immediate investigation.

---

## 🔍 **CRITICAL QA/QC CHECKPOINTS**

### **Data Quality Validation (Between Each Phase)**

**Input Artifacts:**
- Current phase output artifacts
- `savvy-gtm-analytics.SavvyGTMData.Lead`
- `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features`

**Output Artifacts:**
- `data_quality_validation_report_[phase].md` (comprehensive data quality report)

**AGENTIC TASK:**

You are a data quality validation agent. Your task is to validate data quality between phases.

1. **Validate** CRD matching rates between Salesforce and Discovery data.
2. **Check** data completeness for all 69 features (67 discovery + 2 temporal).
3. **Monitor** feature drift using Population Stability Index (PSI).
4. **Validate** no data leakage in temporal features.
5. **Ensure** proper class distribution maintenance.
6. **Generate** comprehensive validation report.

**✅ VALIDATION GATE:**

Proceed to next phase **only if**:
- CRD matching rate > 90%
- Feature completeness > 95% for all critical features
- PSI < 0.25 for all features
- No temporal leakage detected
- Class distribution within expected range

If any validation fails, **STOP** and tag @HumanDeveloper for review.

### **Statistical Validation (Before Model Training)**

**Input Artifacts:**
- `step_3_3_training_dataset.csv` (prepared training data)
- `step_3_3_class_imbalance_analysis.md` (class distribution metrics)

**Output Artifacts:**
- `statistical_validation_report_pre_training.md` (comprehensive statistical validation)

**AGENTIC TASK:**

You are a statistical validation agent. Your task is to validate data before model training.

1. **Check** for multicollinearity using VIF analysis (VIF < 10 required).
2. **Validate** feature distributions and identify outliers.
3. **Ensure** proper train/test split methodology (temporal blocking).
4. **Validate** class imbalance handling approaches.
5. **Check** for data leakage using temporal validation.
6. **Generate** statistical validation report.

**✅ VALIDATION GATE:**

Proceed to model training **only if**:
- All continuous features have VIF < 10
- Outliers are identified and documented
- Train/test split follows temporal blocking
- Class imbalance metrics validated
- No data leakage detected

If validation fails, **STOP** and tag @HumanDeveloper for review.

### **Model Performance Validation (After Each Training)**

**Input Artifacts:**
- Trained model artifacts (`model_v1.pkl` or latest version)
- Training and validation datasets
- Previous model performance reports (if available)

**Output Artifacts:**
- `model_performance_validation_report_[version].md` (comprehensive performance validation)

**AGENTIC TASK:**

You are a model performance validation agent. Your task is to validate model performance after training.

1. **Calculate** key performance metrics: AUC-PR, AUC-ROC, precision@10%, recall@10%.
2. **Validate** calibration error across segments (AUM tiers).
3. **Check** for overfitting using train vs validation performance gap.
4. **Monitor** feature importance stability vs. previous versions.
5. **Validate** business impact metrics (MQLs per 100 dials, lift estimates).
6. **Generate** performance validation report.

**✅ VALIDATION GATE:**

Proceed to next phase **only if**:
- AUC-PR > 0.20 (baseline threshold)
- Calibration error < 0.05 across all segments
- Train-validation performance gap < 10%
- Feature importance ranking is stable
- Business impact metrics show positive lift potential

If validation fails, **STOP** and tag @HumanDeveloper for model review and iteration.

---

## 14) Success Criteria

### Technical Success
- AUC-PR > 0.35 (vs ~0.20 baseline)
- Tier A precision > 15% (vs 6% base rate)
- <5% feature drift week-over-week
- >80% discovery data coverage

### Business Success
- >50% lift in MQLs/100 dials (treatment vs control)
- >$2M incremental pipeline (attributed)
- >75% SGA adoption (calling in tier order)
- <10% increase in time-to-first-touch

### Operational Success
- <2% pipeline failures per month
- <4 hour recovery time for any failure
- >95% daily scoring success rate
- <1 day latency for new feature deployment

---

## 15) Risk Register

| Risk | Probability | Impact | Mitigation |
| :--- | :--- | :--- | :--- |
| Discovery vendor data delays | Medium | High | Cache last-known-good; fallback models |
| Feature importance instability | Medium | Medium | Ensemble methods; longer training windows |
| SGA non-compliance | Low | High | Incentive alignment; UI enforcement |
| Model bias by geography | Low | Medium | Fairness constraints; regular audits |
| Integration complexity | High | Medium | Phased rollout; feature flags |

---

## 16) Appendices

### A) SQL Patterns for Discovery Features

```sql
-- AUM per Client calculation with safety checks
SELECT 
    full_prospect_id__c,
    SAFE_DIVIDE(
        Total_Assets_In_Millions__c * 1000000,
        NULLIF(Number_Investment_Advisory_Clients__c, 0)
    ) AS AUM_Per_Client__c,
    CASE 
        WHEN Number_Investment_Advisory_Clients__c IS NULL 
            OR Number_Investment_Advisory_Clients__c = 0 
        THEN 'Unknown'
        WHEN SAFE_DIVIDE(Total_Assets_In_Millions__c * 1000000,
                         Number_Investment_Advisory_Clients__c) > 2000000 
        THEN 'Premium'
        WHEN SAFE_DIVIDE(Total_Assets_In_Millions__c * 1000000,
                         Number_Investment_Advisory_Clients__c) < 500000 
        THEN 'Mass Market'
        ELSE 'Core'
    END AS Client_Tier__c
FROM staging.lead_discovery_features
WHERE contacted_ts <= snapshot_cutoff - INTERVAL 30 DAY
```

### B) SHAP Explanation Mapping

```python
# Top discovery features to human-readable explanations
SHAP_FEATURE_LABELS = {
    'AUM_Per_Client__c': 'Client wealth level',
    'AUM_Growth_Rate_1Year__c': 'Recent growth trajectory',
    'Years_at_Firm__c': 'Firm tenure (move timing)',
    'HNW_Client_Ratio__c': 'High-net-worth focus',
    'Firm_Stability_Score__c': 'Practice stability',
    'Growth_Momentum__c': 'Growth acceleration',
    'Home_MetropolitanArea_New York-Newark-Jersey City NY-NJ': 'NYC market presence',
    'Has_Disclosure__c': 'Compliance concerns',
    'Number_Employees__c': 'Team size',
    'Multi_RIA_Relationships__c': 'RIA experience'
}

```

### C) Discovery Data Quality Monitoring

```sql

-- Daily data quality scorecard
WITH coverage AS (
    SELECT
        COUNT(*) as total_leads,
        SUM(CASE WHEN Total_Assets_In_Millions__c IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) as aum_coverage,
        SUM(CASE WHEN AUM_Growth_Rate_1Year__c IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) as growth_coverage,
        SUM(CASE WHEN Number_Employees__c IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) as employee_coverage
    FROM staging.lead_discovery_features
    WHERE contacted_ts >= CURRENT_DATE - INTERVAL 7 DAY
)
SELECT 
    *,
    (aum_coverage + growth_coverage + employee_coverage) / 3 as avg_coverage,
    CASE 
        WHEN (aum_coverage + growth_coverage + employee_coverage) / 3 < 0.6 THEN 'ALERT'
        WHEN (aum_coverage + growth_coverage + employee_coverage) / 3 < 0.8 THEN 'WARN'
        ELSE 'OK'
    END as data_quality_status
FROM coverage

```

## 17) RACI Matrix (Updated)

| Activity | Data Science | RevOps | Data Eng | Sales | Vendor Mgmt |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Discovery data pipeline | C | I | R | I | A |
| Feature engineering | R | C | A | I | I |
| Model training | R | C | I | I | I |
| Experiment design | R | A | I | C | I |
| SFDC integration | C | R | A | I | I |
| Monitoring dashboards | A | R | C | I | I |
| Vendor data quality | I | C | I | I | R |
| Model governance | R | A | I | C | I |

## 18) LLM Prompt Pack (Enhanced for Discovery Features)

### Discovery Feature Engineering
"Given these raw discovery data fields [list fields], generate SQL to compute the 31 engineered features including null handling, outlier capping, and validation rules. Include unit tests."

### Feature Importance Analysis
"Analyze SHAP values for these 69 discovery features. Identify: (1) Top 10 most important, (2) Surprising non-important features, (3) Interaction effects worth exploring, (4) Features to potentially drop."

### Segment Performance
"Generate analysis comparing model performance across AUM tiers: <$100M, $100-500M, >$500M. Include precision, recall, and calibration metrics per segment. Recommend segment-specific strategies."

### Data Quality Alerting
"Design a comprehensive data quality monitoring system for 100+ features from 3 data sources. Include PSI thresholds, null rate alerts, and cross-source consistency checks. Output as SQL + alerting rules."

### Discovery ROI Analysis
"Calculate the incremental lift from adding discovery features vs MarketPro-only baseline. Break down contribution by feature category (firmographics, growth, efficiency). Estimate the ROI of the discovery data vendor."