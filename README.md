# Lead Scoring Model Development Repository

**Purpose:** Iteratively develop and deploy lead scoring algorithms and lead list generation systems for financial advisor recruitment.

**Current Production System:** [Version 3.2.5](./Version-3/VERSION_3_MODEL_REPORT.md) + [Version 4.0.0](./Version-4/VERSION_4_MODEL_REPORT.md) - Hybrid approach combining V3 rules-based prioritization with V4 ML deprioritization

**Status:** ✅ Production Ready - Generating lead lists for sales outreach campaigns

---

## Repository Overview

This repository contains the complete development history of lead scoring models for identifying high-conversion financial advisor prospects. The project has evolved through multiple iterations:

- **Version 1 & 2**: Initial machine learning approaches (XGBoost)
- **Version 3**: Rules-based tier system with superior performance and full explainability (2.0x to 4.3x lift)
- **Version 4**: XGBoost ML model for deprioritization (identifies bottom 20% to skip)
- **Hybrid System**: V3 + V4 working together - V3 prioritizes best leads, V4 filters out worst leads

### Key Objectives

1. **Lead Scoring:** Identify which financial advisor leads are most likely to convert from "Contacted" to "MQL" (Marketing Qualified Lead) within 30 days
2. **Lead List Generation:** Generate prioritized, actionable lead lists for sales team outreach campaigns
3. **Iterative Improvement:** Continuously refine models based on performance data and business feedback

---

## Current Production System

### Hybrid Approach: V3 + V4

The production system uses a **hybrid approach** that combines the strengths of both models:

1. **V3 Rules-Based Model** (Primary): Prioritizes leads into tiers (2.0x to 4.3x lift)
2. **V4 XGBoost Model** (Deprioritization Filter): Identifies bottom 20% of leads to skip (1.33% conversion vs 3.20% baseline)

**How They Work Together (Updated December 2025):**
```
Lead Scoring Pipeline:
1. V3 Rules → Assign Tier (T1A, T1B, T1, T2, T3, T4, T5, STANDARD)
2. V4 Score → Assign Percentile (1-100) and identify upgrade candidates
3. Final Lead List:
   - V3 T1-T5 leads → INCLUDED (validated tier ordering: T1 > T2)
   - V3 STANDARD leads with V4 >= 80th percentile → UPGRADED to V4_UPGRADE tier
   - All other STANDARD leads → EXCLUDED
   - Result: High-quality mix of V3 tier leads + V4 upgraded leads
```

**Expected Impact:**
- **V3 Prioritization**: 1.74x lift on top decile (best leads)
- **V4 Upgrade Path**: +6-12% conversion rate improvement by including V4 upgraded leads
- **Combined**: Best of both worlds - V3 prioritizes top tiers, V4 finds hidden gems in STANDARD tier

---

### Version 3.2.5 (Primary Prioritization)

**Model Type:** Rules-based tiered classification system  
**Performance:** 2.0x to 4.3x lift over baseline conversion rates  
**Status:** ✅ Production Ready (Primary Model)

**Key Features:**
- **Tier-based prioritization:** 8 priority tiers (1A, 1B, 1, 1F, 2, 3, 4, 5) plus STANDARD baseline
- **Certification boost:** CFP holders and Series 65-only advisors get highest priority (Tier 1A/1B)
- **LinkedIn prioritization:** ≥90% of leads have LinkedIn URLs (V3.2.5)
- **Producing advisor filter:** Only includes advisors who actively manage client assets
- **Title exclusions:** Data-driven exclusions remove non-advisor roles (operations, compliance, etc.)
- **Insurance exclusions:** Filters out insurance agents and insurance-focused firms

**Comprehensive Documentation:**
- **Full Technical Report:** [`Version-3/VERSION_3_MODEL_REPORT.md`](./Version-3/VERSION_3_MODEL_REPORT.md)
- **Model Guide:** [`Version-3/V3_Lead_Scoring_Model_Complete_Guide.md`](./Version-3/V3_Lead_Scoring_Model_Complete_Guide.md)

---

### Version 4.0.0 (Upgrade Path Filter)

**Model Type:** XGBoost machine learning model  
**Performance:** Identifies STANDARD tier leads with 4.60% conversion (1.42x baseline)  
**Status:** ✅ Production Ready (Upgrade Path Filter)

**What is V4?**
V4 is an XGBoost machine learning model trained on historical lead conversion data to identify **high-quality leads that V3's rules miss**. V4 excels at finding "hidden gems" in the STANDARD tier - leads that don't meet V3's explicit criteria but have strong conversion signals.

**How V4 Was Created:**
1. **Data Extraction**: Trained on "Provided Lead List" leads only (cold outbound, not inbound)
2. **Feature Engineering**: 14 Point-in-Time (PIT) compliant features:
   - Tenure buckets, experience buckets, mobility tiers
   - Firm stability metrics (rep count, net change, stability tier)
   - Wirehouse flags, broker protocol membership
   - Data quality flags (has_email, has_linkedin)
   - Interaction features (mobility × heavy bleeding, short tenure × high mobility)
3. **Model Training**: XGBoost with strong regularization to prevent overfitting
4. **Validation**: Tested on Aug-Oct 2025 data (never seen during training)
5. **Deployment**: Integrated into monthly lead list generation pipeline

**Key Findings:**
- **STANDARD leads with V4 >= 80th percentile**: Convert at 4.60% (1.42x baseline, 44% better than T2)
- **V4 AUC-ROC**: 0.6141 vs V3 AUC-ROC: 0.5095 (V4 better at prediction overall)
- **Upgrade Path**: 486 leads upgraded in January 2026 list (20.25% of total)
- **Expected Impact**: +6-12% conversion rate improvement by including V4 upgraded leads

**Why V4 Complements V3:**
- **V3 Tier Ordering**: Validated (T1: 7.41% > T2: 3.20%, statistically significant)
- **V4 Upgrade Path**: Finds high-quality leads V3 rules miss (4.60% conversion)
- **Use Case**: V3 prioritizes explicit patterns, V4 finds implicit patterns = **complementary, not competitive**

**Comprehensive Documentation:**
- **Full Technical Report:** [`Version-4/VERSION_4_MODEL_REPORT.md`](./Version-4/VERSION_4_MODEL_REPORT.md)
- **Deprioritization Analysis:** [`Version-4/reports/deprioritization_analysis.md`](./Version-4/reports/deprioritization_analysis.md)

---

### Monthly Lead List Generation (Hybrid Process)

**Process:** [`Lead_List_Generation/Monthly_Lead_List_Generation_V3_V4_Hybrid.md`](./Lead_List_Generation/Monthly_Lead_List_Generation_V3_V4_Hybrid.md)

**Step-by-Step:**
1. **Calculate V4 Features** (`sql/v4_prospect_features.sql`)
   - Generate all 14 V4 features for all FINTRX prospects (~285K)
   - Uses `CURRENT_DATE()` for PIT compliance
   - Output: `ml_features.v4_prospect_features`

2. **Score with V4 Model** (`scripts/score_prospects_monthly.py`)
   - Load V4 XGBoost model and score all prospects
   - Calculate percentiles (1-100) and identify upgrade candidates (>= 80th percentile)
   - **Generate SHAP-based narratives** for V4 upgrade candidates
   - Extract top 3 SHAP features per prospect (feature importance-based)
   - Output: `ml_features.v4_prospect_scores` with columns:
     - `v4_score`, `v4_percentile`, `v4_upgrade_candidate`
     - `shap_top1_feature`, `shap_top1_value`, `shap_top2_feature`, `shap_top2_value`, `shap_top3_feature`, `shap_top3_value`
     - `v4_narrative` (human-readable explanation for upgrades)

3. **Generate Hybrid Lead List** (`sql/January_2026_Lead_List_V3_V4_Hybrid.sql`)
   - Apply V3 tier logic to all prospects with rich narratives
   - **Exclude specific firms**: Savvy Advisors (CRD 318493) and Ritholtz Wealth Management (CRD 168652)
   - Join V4 scores and upgrade STANDARD leads with V4 >= 80th percentile to V4_UPGRADE tier
   - **Generate final narratives**: V3 tier narratives OR V4 SHAP-based narratives for upgrades
   - Apply tier quotas and LinkedIn prioritization
   - Output: `ml_features.january_2026_lead_list_v4` (2,400 leads)

4. **Export to CSV** (`scripts/export_lead_list.py`)
   - Export lead list with all V3 and V4 columns
   - Validate data quality (no duplicates, required fields present, firm exclusions verified)
   - Output: `exports/january_2026_lead_list_YYYYMMDD.csv`

**Result:**
- **2,400 prioritized leads** with V3 tier assignments + V4 upgrades
- **486 V4_UPGRADE leads** (20.25% of list, expected 4.60% conversion)
- **Average V4 percentile: 98.2** (top 2% of prospects)
- **99.9% LinkedIn coverage** for SDR outreach
- **100% narrative coverage** - every lead has a human-readable explanation
- **100% job title coverage** - advisor job titles included for context

---

### Recyclable Lead List Generation (Unified Scoring System)

**Purpose:** Generate a monthly list of 600 previously-contacted leads/opportunities that are ready for re-engagement, using a unified scoring system that combines V3 tier signals, V4 ML predictions, and recycling-specific factors.

**Process:** [`Lead_List_Generation/scripts/recycling/generate_recyclable_list_v2.1.py`](./Lead_List_Generation/scripts/recycling/generate_recyclable_list_v2.1.py)

**How It Works:**

The recyclable lead list system identifies leads and opportunities that were previously contacted but didn't convert, and determines which ones are most likely to convert on re-engagement. The system uses a **unified scoring approach** that combines multiple signals into a single score for easy prioritization.

**Key Insight - Firm Change Logic:**
- **WRONG (V1)**: Prioritized people who recently changed firms as "hot leads"
- **CORRECT (V2)**: People who **just changed firms (< 2 years)** are **EXCLUDED** - they just settled in and won't move again soon
- **INCLUDE**: People who changed firms 2+ years ago (proven movers, may be getting restless)

**Unified Scoring System (V2.2):**

Each recyclable lead receives a single `recyclable_score` that combines:

1. **V4 ML Score** (0-100 pts) - Base score from machine learning prediction
2. **V3 Tier Boost** (0-35 pts) - Based on historical conversion rates:
   - TIER_1A_PRIME_MOVER_CFP: +35 pts
   - TIER_1B_PRIME_MOVER_SERIES65: +35 pts
   - TIER_1_PRIME_MOVER: +30 pts
   - TIER_1F_HV_WEALTH_BLEEDER: +28 pts
   - TIER_4_EXPERIENCED_MOVER: +22 pts
   - TIER_2_PROVEN_MOVER: +20 pts
   - TIER_3_MODERATE_BLEEDER: +18 pts
   - TIER_5_HEAVY_BLEEDER: +12 pts
   - STANDARD: +0 pts
3. **Timing Boost** (+15 pts) - Previously said "timing was bad" (high re-engagement potential)
4. **Opportunity Boost** (+10 pts) - Warmer than lead (previously engaged as opportunity)
5. **Optimal Window** (+10 pts) - 180-365 days since last contact (sweet spot for re-engagement)
6. **Bleeding Firm** (+8 pts) - Currently at unstable firm (high movement signal)

**Score Range:** Typically 129-165 points  
**Expected Conversions:** Score-to-conversion mapping:
- Score 50 (baseline) → 3.2% conversion
- Score 100 → 6.0% conversion
- Score 135+ → 10.0%+ conversion

**Step-by-Step Process:**

1. **Query Recyclable Pool** (`sql/recycling/recyclable_pool_master_v2.1.sql`)
   - Identifies closed/lost leads and opportunities from Salesforce
   - Excludes recent firm changers (< 2 years)
   - Excludes no-go dispositions and DoNotCall records
   - Excludes recently contacted (< 90 days)
   - Joins with FINTRX current data for V3 tier calculation
   - Joins with V4 scores for ML predictions
   - Calculates unified `recyclable_score` for each record
   - Ranks by score (highest first) and selects top 600

2. **Generate Narratives** (`generate_narrative()` function)
   - Creates clear, concise narratives explaining why each lead is being recycled
   - Includes: record type, key signals (V3 tier, V4 percentile, timing, bleeding firm), previous contact info, score and expected conversion

3. **Calculate Expected Conversions** (`estimate_conversion_rate()` function)
   - Converts unified score to expected conversion percentage
   - Uses calibrated mapping based on historical data

4. **Export to CSV** (`exports/[MONTH]_[YEAR]_recyclable_leads.csv`)
   - Includes all contact information, scoring data, narratives, and expected conversions

5. **Generate Report** (`reports/recycling_analysis/[MONTH]_[YEAR]_recyclable_list_report.md`)
   - Score distribution statistics
   - Breakdown by record type (Opportunity vs Lead)
   - V3 tier distribution with average scores
   - Score buckets analysis
   - Expected conversion summary

**Usage:**

```bash
cd "C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation"
python scripts/recycling/generate_recyclable_list_v2.1.py --month january --year 2026
```

**Output Files:**
- **CSV Export**: `exports/january_2026_recyclable_leads.csv` (600 leads)
- **Report**: `reports/recycling_analysis/january_2026_recyclable_list_report.md`

**What's in the Recyclable List:**

Each lead includes:
- **Contact Information**: `first_name`, `last_name`, `email`, `phone`, `linkedin_url`, `current_firm`
- **Unified Scoring**: `recyclable_score` (129-165 range), `expected_conv_pct` (calculated from score)
- **V3 Tier Data**: `v3_tier`, `v3_tier_rank`, `at_bleeding_firm`, `has_cfp`, `previous_firm_count`, `v3_tier_narrative`
- **V4 ML Data**: `v4_score`, `v4_percentile`, `v4_shap_narrative`, `shap_top1_feature`, `shap_top2_feature`, `shap_top3_feature`
- **Recycling Context**: `close_reason`, `close_date`, `days_since_last_contact`, `last_contacted_by`, `recycle_narrative`
- **Firm Change Analysis**: `changed_firms_since_close`, `years_at_current_firm`, `years_at_current_firm_now`

**Key Features:**

1. **Unified Scoring**: Single score combines all signals for easy prioritization (no complex P1-P6 tiers)
2. **V3 Integration**: Uses same V3 tier logic as Provided Lead List for consistency
3. **V4 Integration**: Leverages ML predictions to identify high-potential recyclable leads
4. **Smart Exclusions**: Automatically excludes recent firm changers and no-go dispositions
5. **Comprehensive Narratives**: Every lead includes explanation of why it's being recycled
6. **Expected Conversions**: Score-to-conversion mapping provides realistic expectations

**Performance:**

- **Score Range**: 129-165 (January 2026)
- **Average Score**: 135.6
- **Expected Conversions**: ~59.5 conversions (9.9% avg rate)
- **Top Performers**: Score 165+ leads have 11.5%+ expected conversion

**Documentation:**
- **Process Guide**: [`Lead_List_Generation/Monthly_Recyclable_Lead_List_Generation_Guide_V2.md`](./Lead_List_Generation/Monthly_Recyclable_Lead_List_Generation_Guide_V2.md)
- **SQL Query**: [`Lead_List_Generation/sql/recycling/recyclable_pool_master_v2.1.sql`](./Lead_List_Generation/sql/recycling/recyclable_pool_master_v2.1.sql)
- **Python Script**: [`Lead_List_Generation/scripts/recycling/generate_recyclable_list_v2.1.py`](./Lead_List_Generation/scripts/recycling/generate_recyclable_list_v2.1.py)

### What's in the Lead List?

**Every lead includes:**

1. **Contact Information:**
   - `first_name`, `last_name`, `email`, `phone`, `linkedin_url`
   - `job_title` - Advisor's role (e.g., "Wealth Manager", "Financial Advisor")

2. **Scoring & Prioritization:**
   - `score_tier` - Final tier assignment (T1A, T1B, T1, T2, T3, T4, T5, or V4_UPGRADE)
   - `original_v3_tier` - Original V3 tier before upgrade (shows "STANDARD" for V4 upgrades)
   - `expected_rate_pct` - Expected conversion rate (e.g., 7.10% for T1, 4.60% for V4_UPGRADE)
   - `list_rank` - Overall ranking in the list (1 = highest priority)

3. **Human-Readable Narratives:**
   - `score_narrative` - Explains why the lead was scored/upgraded:
     - **V3 Tier Leads**: "James is a CFP holder at ABC Wealth, which has lost 5 advisors (net) in the past year. CFP designation indicates book ownership and client relationships. With 2 years at the firm and 8 years of experience, this is an ULTRA-PRIORITY lead. Tier 1A: 8.7% expected conversion."
     - **V4 Upgrade Leads**: "V4 Model Upgrade: Sarah at XYZ Advisors identified as high-potential lead (V4 score: 0.70, 99th percentile). Key factors: This advisor is relatively new at their current firm AND has a history of changing firms - a strong signal they may move again. Historical conversion: 4.60% (1.42x baseline). Track as V4 Upgrade."

4. **V4 Machine Learning Data:**
   - `v4_score` - Raw XGBoost prediction score (0.0-1.0)
   - `v4_percentile` - Percentile rank (1-100, higher is better)
   - `is_v4_upgrade` - Flag (1 = upgraded from STANDARD, 0 = V3 tier qualified)
   - `v4_status` - Description ("V4 Upgrade (STANDARD with V4 >= 80%)" or "V3 Tier Qualified")
   - `shap_top1_feature`, `shap_top2_feature`, `shap_top3_feature` - Top 3 ML features driving the score (for V4 upgrades)

5. **Firm Information:**
   - `firm_name`, `firm_crd` - Firm identification
   - `firm_rep_count` - Number of advisors at firm
   - `firm_net_change_12mo` - Net advisor change (negative = losing advisors)
   - `tenure_months`, `tenure_years` - How long advisor has been at current firm
   - `industry_tenure_years` - Total years in the industry

6. **Certifications & Flags:**
   - `has_cfp`, `has_series_65_only`, `has_series_7`, `has_cfa` - Professional certifications
   - `is_hv_wealth_title` - High-value wealth title flag
   - `prospect_type` - "NEW_PROSPECT" or recyclable lead

**How Narratives Are Generated:**

- **V3 Tier Leads**: Narratives are generated from SQL business rules, explaining the specific criteria that qualified the lead for that tier (e.g., CFP certification, firm bleeding, tenure, etc.)

- **V4 Upgrade Leads**: Narratives are generated from SHAP (SHapley Additive exPlanations) feature importance analysis. The model identifies the top 3 features driving the score, and the narrative explains what those features mean in business terms (e.g., "relatively new at firm AND history of changing firms" for `short_tenure_x_high_mobility`).

**Firm Exclusions Applied:**
- **Savvy Advisors, Inc.** (CRD 318493) - Internal firm, excluded from all lead lists
- **Ritholtz Wealth Management** (CRD 168652) - Partner firm, excluded from all lead lists

---

## Repository Structure

```
Lead Scoring/
├── Version-3/              # ✅ PRIMARY PRODUCTION MODEL (Prioritization)
│   ├── VERSION_3_MODEL_REPORT.md          # Comprehensive technical documentation
│   ├── January_2026_Lead_List_Query_V3.2.sql  # V3-only lead list generator
│   ├── sql/                 # SQL feature engineering and tier logic
│   ├── scripts/             # Phase execution scripts
│   ├── reports/             # Validation and analysis reports
│   └── models/              # Model registry and metadata
│
├── Version-4/              # ✅ DEPRIORITIZATION FILTER (ML Model)
│   ├── VERSION_4_MODEL_REPORT.md         # Comprehensive technical documentation
│   ├── models/v4.0.0/      # Trained XGBoost model (model.pkl)
│   ├── sql/                 # V4 feature engineering SQL
│   ├── scripts/             # Training, validation, and scoring scripts
│   ├── reports/             # Performance and deprioritization analysis
│   ├── inference/           # Production scoring interface (LeadScorerV4)
│   └── EXECUTION_LOG.md    # Development execution log
│
├── Lead_List_Generation/   # ✅ HYBRID LEAD LIST GENERATION (V3 + V4)
│   ├── Monthly_Lead_List_Generation_V3_V4_Hybrid.md  # Process documentation
│   ├── Monthly_Recyclable_Lead_List_Generation_Guide_V2.md  # Recyclable list guide
│   ├── sql/
│   │   ├── v4_prospect_features.sql      # V4 features for all prospects
│   │   ├── January_2026_Lead_List_V3_V4_Hybrid.sql  # Hybrid query
│   │   └── recycling/
│   │       └── recyclable_pool_master_v2.1.sql  # Recyclable lead query (unified scoring)
│   ├── scripts/
│   │   ├── score_prospects_monthly.py    # V4 scoring script
│   │   ├── export_lead_list.py           # CSV export script
│   │   └── recycling/
│   │       ├── generate_recyclable_list_v2.1.py  # Recyclable list generator
│   │       └── test_recyclable_query.py  # Query testing script
│   ├── exports/             # Generated CSV lead lists (gitignored)
│   ├── reports/
│   │   └── recycling_analysis/  # Recyclable list reports
│   └── logs/                # Execution logs
│
├── V3+V4_testing/          # ✅ METHODOLOGY INVESTIGATION (December 2025)
│   ├── reports/
│   │   ├── FINAL_V3_VS_V4_INVESTIGATION_REPORT.md  # Full investigation report
│   │   └── tier_analysis.md              # Tier performance analysis
│   ├── logs/
│   │   └── INVESTIGATION_LOG.md          # Investigation execution log
│   └── scripts/             # Investigation analysis scripts
│
├── Version-2/              # Machine Learning Approach (XGBoost)
│   ├── VERSION_2_MODEL_REPORT.md
│   ├── models/             # Trained XGBoost models
│   ├── scripts/            # Training and validation scripts
│   └── reports/             # Performance analysis
│
├── version-1/              # Initial ML Model Development
│   ├── models/             # Baseline, tuned, and boosted models
│   ├── production/         # Production deployment code
│   └── reports/            # Feature selection and SHAP analysis
│
├── Broker_protocol/        # Broker Protocol automation and firm matching
│   ├── broker_protocol_automation.py
│   ├── firm_matcher.py     # FINTRX firm matching logic
│   └── experiments/        # Matching algorithm experiments
│
├── Old_development_docs/    # Historical development documentation
│   └── [174 files]         # Analysis reports, SQL queries, Python scripts
│
├── documentation/          # FINTRX data documentation
│   ├── FINTRX_Data_Dictionary.md
│   ├── FINTRX_Architecture_Overview.md
│   └── FINTRX_Lead_Scoring_Features.md
│
├── config/                 # Feature schemas and model configurations
├── discovery_data/         # Historical discovery data snapshots
└── .gitignore             # Excludes credentials and sensitive files
```

---

## Model Evolution

### Version 1: Initial ML Approach
- **Algorithm:** XGBoost classifier
- **Features:** 20 engineered features
- **Performance:** Baseline model development
- **Status:** Superseded by Version 2

### Version 2: Enhanced ML with Velocity Features
- **Algorithm:** XGBoost with temporal velocity features
- **Features:** 20+ features including firm stability signals
- **Performance:** 1.50x lift (below 2.5x target)
- **Issues:** Data leakage concerns, limited explainability
- **Status:** Superseded by Version 3

### Version 3: Rules-Based Tier System (Primary Production Model)
- **Approach:** SQL-based business rules (not ML)
- **Performance:** 2.0x to 4.3x lift across priority tiers
- **Key Innovation:** Point-in-Time (PIT) feature engineering eliminates data leakage
- **Explainability:** Every tier assignment is transparent and auditable
- **Status:** ✅ Production Ready (Primary Prioritization)

**Version 3 Evolution:**
- **V3.1:** Initial rules-based tier system (3.69x lift for Tier 1)
- **V3.2:** Added firm size signals and proven mover segment (7.29x lift for Tier 1A)
- **V3.2.1:** Added certification-based tiers (CFP, Series 65) - 4.3x+ lift
- **V3.2.2:** Added High-Value Wealth tier (3.35x lift)
- **V3.2.3:** Added producing advisor filter
- **V3.2.4:** Added insurance exclusions
- **V3.2.5:** Added LinkedIn prioritization (≥90% coverage)

### Version 4: XGBoost Deprioritization Filter (Complementary Model)
- **Approach:** XGBoost machine learning model
- **Performance:** Identifies bottom 20% with 1.33% conversion (58% below baseline)
- **Key Innovation:** ML model trained specifically for deprioritization (finding worst leads)
- **Use Case:** Filter out low-value leads that V3 doesn't explicitly exclude
- **Status:** ✅ Production Ready (Deprioritization Filter)

**Version 4 Development:**
- **V4.0.0:** Initial XGBoost model with 14 PIT-compliant features
- **Training Data:** "Provided Lead List" leads only (cold outbound, Feb 2024 - Jul 2025)
- **Test Data:** Aug-Oct 2025 (never seen during training)
- **Deployment:** Integrated into monthly lead list generation as upgrade path filter
- **Hybrid Integration:** Works alongside V3 to upgrade STANDARD tier leads while V3 prioritizes top tiers

**Methodology Evolution (December 2025):**
- **Initial Approach:** V4 used for deprioritization (filtering bottom 20%)
- **Updated Approach:** V4 used for upgrade path (promoting STANDARD leads with V4 >= 80%)
- **Rationale:** Investigation showed V4 deprioritization wasn't adding value (90% of V3 leads already in top 10%)
- **New Finding:** V4 identifies "hidden gems" - STANDARD leads that convert at 4.60% (better than T2's 3.20%)

---

## Lead Scoring Methodology Evolution

### Data-Driven Investigation (Q1-Q3 2025)

In December 2025, we conducted a rigorous investigation comparing V3 tier rules vs V4 XGBoost model performance on historical lead data to validate our methodology and identify improvement opportunities.

**Investigation Scope:**
- **Dataset:** 17,867 historical leads contacted in Q1-Q3 2025
- **Conversions:** 579 total conversions (3.24% baseline conversion rate)
- **Key Question:** Does V3 tier ordering correctly prioritize leads? Can V4 find leads V3 misses?

**Full Investigation Report:** [`V3+V4_testing/reports/FINAL_V3_VS_V4_INVESTIGATION_REPORT.md`](./V3+V4_testing/reports/FINAL_V3_VS_V4_INVESTIGATION_REPORT.md)

### Key Findings

#### V3 Tier Performance (Validated ✅)

**Tier Conversion Rates (Historical Data):**
- **T1 (Prime Mover):** 7.41% conversion - **2.31x better than T2** (statistically significant, p=0.0008)
- **T2 (Proven Mover):** 3.20% conversion
- **T1A (CFP):** Sample too small (4 leads) to validate statistically

**Conclusion:** V3 tier ordering is **validated** - T1 leads convert significantly better than T2 leads. The rules-based tier system correctly prioritizes leads.

#### V4 Model Performance (Superior Prediction ✅)

**Model Comparison:**
- **V4 AUC-ROC:** 0.6141
- **V3 AUC-ROC:** 0.5095
- **V4 is better at predicting conversions overall** (14% improvement in AUC)

**Hidden Gems Discovery:**
- **STANDARD leads with V4 >= 80th percentile:** Convert at **4.60%** (1.42x baseline)
- **This is 44% better than T2's 3.20% conversion rate**
- **V4 found high-quality leads that V3's rules missed**

#### Disagreement Analysis

**When V3 and V4 Disagree:**
- **High V3 / Low V4 leads:** 0.00% conversion (V4 was right to score low)
- **Low V3 / High V4 leads:** 4.60% conversion (V4 found leads V3 missed)

**Insight:** V4's ML model captures patterns that V3's explicit rules don't cover, particularly in the STANDARD tier.

### Methodology Changes

#### OLD Hybrid Approach (Deprecated - December 2025)

```
Lead Scoring Pipeline (OLD):
1. V3 Rules → Assign Tier (T1A, T1B, T1, T2, T3, T4, T5, STANDARD)
2. V4 Score → Assign Percentile and deprioritize flag (bottom 20%)
3. Final Lead List:
   - V3 T1-T2 leads → INCLUDED (regardless of V4 score)
   - V3 T3-T5 leads → INCLUDED (if V4 percentile > 20%)
   - V3 STANDARD leads → EXCLUDED if V4 deprioritize = TRUE
   - Result: V3 prioritization + V4 deprioritization
```

**Problem Identified:**
- V4 deprioritization wasn't adding value
- 90% of V3-qualified leads already scored in V4's top 10%
- Filtering bottom 20% didn't improve conversion rates within V3 tiers

#### NEW Hybrid Approach (Current - December 2025)

```
Lead Scoring Pipeline (NEW):
1. V3 Rules → Assign Tier (T1A, T1B, T1, T2, T3, T4, T5, STANDARD)
2. V4 Score → Assign Percentile and identify upgrade candidates
3. Final Lead List:
   - V3 T1-T5 leads → INCLUDED (validated tier ordering)
   - V3 STANDARD leads with V4 >= 80th percentile → UPGRADED to V4_UPGRADE tier
   - All other STANDARD leads → EXCLUDED
   - Result: V3 prioritization + V4 upgrade path
```

**Expected Improvement:**
- **+6-12% conversion rate** by including V4 upgraded leads
- **486 V4_UPGRADE leads** in January 2026 list (20.25% of total)
- **Expected conversion:** 4.60% for V4 upgrades (vs 3.20% for T2)

### New Features & Tracking

**New Columns in Lead Lists:**
- **`is_v4_upgrade`**: Flag (1 = V4 upgraded lead, 0 = V3 tier lead)
- **`V4_UPGRADE`**: New tier for STANDARD leads with V4 >= 80th percentile
- **`original_v3_tier`**: Preserves original V3 tier for analysis (shows "STANDARD" for upgraded leads)
- **`v4_status`**: Description of V4 status ("V4 Upgrade (STANDARD with V4 >= 80%)" or "V3 Tier Qualified")
- **`job_title`**: Advisor's job title from FINTRX (e.g., "Wealth Manager", "Financial Advisor")
- **`score_narrative`**: Human-readable explanation of why the lead was scored/upgraded:
  - **V3 Tier Leads**: Rich narratives explaining tier criteria (e.g., "James is a CFP holder at ABC Wealth, which has lost 5 advisors...")
  - **V4 Upgrade Leads**: SHAP-based narratives explaining ML factors (e.g., "Key factors: This advisor is relatively new at their current firm AND has a history of changing firms...")
- **`shap_top1_feature`**, **`shap_top2_feature`**, **`shap_top3_feature`**: Top 3 ML features driving the V4 score (for V4 upgrades)

**Performance Tracking:**
- Filter by `is_v4_upgrade = 1` to measure V4 upgrade performance
- Expected conversion rate: **4.60%** (based on historical data)
- Compare V4 upgrades vs V3 tier leads monthly to validate methodology

### Files Modified

**Updated Files (December 2025):**
- **`Lead_List_Generation/sql/January_2026_Lead_List_V3_V4_Hybrid.sql`**
  - Removed: V4 deprioritization filter (`v4_deprioritize = FALSE`)
  - Added: V4 upgrade path logic (STANDARD + V4 >= 80% → V4_UPGRADE tier)
  - Added: `is_v4_upgrade` flag and `original_v3_tier` column

- **`Lead_List_Generation/scripts/export_lead_list.py`**
  - Added: V4 upgrade tracking columns to export
  - Added: V4 upgrade analysis in validation output

### Investigation Documentation

**Full Investigation Reports:**
- **Final Report:** [`V3+V4_testing/reports/FINAL_V3_VS_V4_INVESTIGATION_REPORT.md`](./V3+V4_testing/reports/FINAL_V3_VS_V4_INVESTIGATION_REPORT.md)
- **Investigation Log:** [`V3+V4_testing/logs/INVESTIGATION_LOG.md`](./V3+V4_testing/logs/INVESTIGATION_LOG.md)
- **Tier Analysis:** [`V3+V4_testing/reports/tier_analysis.md`](./V3+V4_testing/reports/tier_analysis.md)

**Key Takeaways:**
1. **V3 tier ordering is validated** - T1 converts 2.31x better than T2 (statistically significant)
2. **V4 is better at prediction** - 0.6141 AUC-ROC vs 0.5095 for V3
3. **V4 finds hidden gems** - STANDARD leads with V4 >= 80% convert at 4.60% (better than T2)
4. **Hybrid approach optimized** - Upgrade path adds more value than deprioritization filter

---

## Key Technical Concepts

### Point-in-Time (PIT) Methodology
All features are calculated using only data available at the `contacted_date`, preventing data leakage that plagued earlier versions.

### Virtual Snapshot Approach
Instead of pre-computed snapshot tables, V3 constructs advisor/firm state dynamically from historical data, ensuring accurate point-in-time calculations.

### Tier System
Leads are assigned to priority tiers based on business rules:
- **Tier 1A/1B:** Certification boost (CFP or Series 65 only) + Prime Mover criteria (16.44-16.48% conversion)
- **Tier 1:** Prime Movers - mid-career advisors at small, bleeding firms (13.21% conversion)
- **Tier 1F:** High-Value Wealth titles at bleeding firms (12.78% conversion)
- **Tier 2:** Proven Movers - career changers with 3+ prior firms (8.59% conversion)
- **Tier 3:** Moderate Bleeders - firms losing 1-10 advisors (9.52% conversion)
- **Tier 4:** Experienced Movers - 20+ year veterans who recently moved (11.54% conversion)
- **Tier 5:** Heavy Bleeders - firms in crisis losing 10+ advisors (7.27% conversion)
- **STANDARD:** Baseline leads (3.82% conversion)

---

## Data Sources

### Primary Data Sources
1. **Salesforce Lead Table** (`SavvyGTMData.Lead`)
   - Lead lifecycle and conversion events
   - Contact timestamps

2. **FINTRX Contact Employment History** (`FinTrx_data_CA.contact_registered_employment_history`)
   - Historical advisor employment records
   - Used for tenure and mobility calculations

3. **FINTRX Firm Historicals** (`FinTrx_data_CA.Firm_historicals`)
   - Monthly snapshots of firm metrics
   - AUM, rep counts, firm stability

4. **FINTRX Current Contacts** (`FinTrx_data_CA.ria_contacts_current`)
   - Current advisor data
   - Contact information, certifications, licenses

### BigQuery Deployment
- **Project:** `savvy-gtm-analytics`
- **Dataset:** `ml_features`
- **Location:** `northamerica-northeast2`

**Key Tables:**
- `lead_scoring_features_pit` - V3 feature engineering table (37 features)
- `lead_scores_v3_2_12212025` - V3 production scoring table
- `v4_prospect_features` - V4 feature engineering table (14 features, all prospects)
- `v4_prospect_scores` - V4 scoring table with SHAP data:
  - Percentiles, upgrade candidates, deprioritize flags
  - SHAP top features (`shap_top1/2/3_feature`, `shap_top1/2/3_value`)
  - V4 narratives (`v4_narrative`) for upgrade candidates
- `january_2026_lead_list_v4` - Generated hybrid lead lists (V3 + V4) with:
  - V3 tier assignments and narratives
  - V4 upgrade path (STANDARD → V4_UPGRADE)
  - Job titles, SHAP features, and combined narratives
  - Firm exclusions applied (Savvy, Ritholtz)

---

## Getting Started

### For Model Users (Sales Team)
1. **Use Hybrid Lead Lists:** Monthly lead lists are generated using both V3 and V4 (see `Lead_List_Generation/`)
2. **Review Tier Assignments:** Each lead includes:
   - **V3 tier** (or V4_UPGRADE for upgraded leads)
   - **Expected conversion rate** (percentage)
   - **V4 percentile** (1-100, higher is better)
   - **Job title** (advisor's role for context)
   - **Score narrative** (human-readable explanation of why the lead was scored/upgraded)
   - **SHAP features** (top 3 ML factors for V4 upgrades)
3. **Prioritize Outreach:** 
   - **Highest Priority**: V3 Tier 1A/1B/1 leads (7.41%+ expected conversion)
   - **High Priority**: V3 Tier 2 leads (3.20% expected conversion)
   - **V4 Upgraded**: V4_UPGRADE tier leads (4.60% expected conversion, 44% better than T2)
     - Read the `score_narrative` to understand why they were upgraded (e.g., "relatively new at firm AND history of changing firms")
   - **Standard Priority**: V3 Tier 3-5 leads
4. **Understand Narratives:**
   - **V3 Tier Leads**: Narratives explain tier criteria (e.g., "CFP holder at firm losing advisors")
   - **V4 Upgrade Leads**: Narratives explain ML factors (e.g., "new at firm AND history of mobility")
5. **Track Performance:** Filter by `is_v4_upgrade = 1` to measure V4 upgrade performance (expected: 4.60% conversion)
6. **Export Format:** CSV files in `Lead_List_Generation/exports/` with all columns:
   - Contact info: `first_name`, `last_name`, `email`, `phone`, `linkedin_url`, `job_title`
   - Scoring: `score_tier`, `original_v3_tier`, `expected_rate_pct`, `score_narrative`
   - V4 data: `v4_score`, `v4_percentile`, `is_v4_upgrade`, `v4_status`, `shap_top1_feature`, `shap_top2_feature`, `shap_top3_feature`
   - Firm data: `firm_name`, `firm_crd`, `firm_rep_count`, `firm_net_change_12mo`

### For Developers
1. **Read Documentation:** Start with [`Version-3/VERSION_3_MODEL_REPORT.md`](./Version-3/VERSION_3_MODEL_REPORT.md)
2. **Understand Architecture:** Review the tier logic in `Version-3/sql/phase_4_v3_tiered_scoring.sql`
3. **Run Validation:** Execute phase scripts in `Version-3/scripts/` to validate model performance

---

## Key Files

### Production Files

**V3 (Primary Prioritization):**
- **Lead List Generator (V3 Only):** [`Version-3/January_2026_Lead_List_Query_V3.2.sql`](./Version-3/January_2026_Lead_List_Query_V3.2.sql)
- **Tier Logic:** [`Version-3/sql/phase_4_v3_tiered_scoring.sql`](./Version-3/sql/phase_4_v3_tiered_scoring.sql)
- **Feature Engineering:** [`Version-3/sql/lead_scoring_features_pit.sql`](./Version-3/sql/lead_scoring_features_pit.sql)

**V4 (Deprioritization Filter):**
- **V4 Feature Engineering:** [`Lead_List_Generation/sql/v4_prospect_features.sql`](./Lead_List_Generation/sql/v4_prospect_features.sql)
- **V4 Scoring Script:** [`Lead_List_Generation/scripts/score_prospects_monthly.py`](./Lead_List_Generation/scripts/score_prospects_monthly.py)
- **V4 Model:** [`Version-4/models/v4.0.0/model.pkl`](./Version-4/models/v4.0.0/model.pkl)

**Hybrid Lead List Generation:**
- **Hybrid Query:** [`Lead_List_Generation/sql/January_2026_Lead_List_V3_V4_Hybrid.sql`](./Lead_List_Generation/sql/January_2026_Lead_List_V3_V4_Hybrid.sql)
  - Includes: V3 tier logic, V4 upgrade path, SHAP narratives, job titles, firm exclusions
- **V4 Scoring Script:** [`Lead_List_Generation/scripts/score_prospects_monthly.py`](./Lead_List_Generation/scripts/score_prospects_monthly.py)
  - Generates SHAP-based narratives for V4 upgrade candidates
- **Export Script:** [`Lead_List_Generation/scripts/export_lead_list.py`](./Lead_List_Generation/scripts/export_lead_list.py)
  - Exports CSV with all columns including narratives and SHAP features
- **Process Documentation:** [`Lead_List_Generation/Monthly_Lead_List_Generation_V3_V4_Hybrid.md`](./Lead_List_Generation/Monthly_Lead_List_Generation_V3_V4_Hybrid.md)
- **Upgrades Guide:** [`Lead_List_Generation/January_2026_Lead_List_Final_Upgrades_Guide.md`](./Lead_List_Generation/January_2026_Lead_List_Final_Upgrades_Guide.md)

### Documentation

**V3 (Primary Model):**
- **Technical Report:** [`Version-3/VERSION_3_MODEL_REPORT.md`](./Version-3/VERSION_3_MODEL_REPORT.md) ⭐ **START HERE**
- **User Guide:** [`Version-3/V3_Lead_Scoring_Model_Complete_Guide.md`](./Version-3/V3_Lead_Scoring_Model_Complete_Guide.md)

**V4 (Deprioritization Filter):**
- **Technical Report:** [`Version-4/VERSION_4_MODEL_REPORT.md`](./Version-4/VERSION_4_MODEL_REPORT.md)
- **Deprioritization Analysis:** [`Version-4/reports/deprioritization_analysis.md`](./Version-4/reports/deprioritization_analysis.md)

**Hybrid Process:**
- **Monthly Generation Guide:** [`Lead_List_Generation/Monthly_Lead_List_Generation_V3_V4_Hybrid.md`](./Lead_List_Generation/Monthly_Lead_List_Generation_V3_V4_Hybrid.md)

**Data:**
- **Data Dictionary:** [`documentation/FINTRX_Data_Dictionary.md`](./documentation/FINTRX_Data_Dictionary.md)

---

## Performance Summary

### Version 3.2.5 Tier Performance

| Tier | Conversion Rate | Lift vs Baseline | Volume (Historical) |
|------|----------------|------------------|---------------------|
| **TIER_1A_PRIME_MOVER_CFP** | **16.44%** | **4.30x** | 73 leads |
| **TIER_1B_PRIME_MOVER_SERIES65** | **16.48%** | **4.31x** | 91 leads |
| **TIER_1_PRIME_MOVER** | **13.21%** | **3.46x** | ~245 leads |
| **TIER_1F_HV_WEALTH_BLEEDER** | **12.78%** | **3.35x** | 266 leads |
| **TIER_4_EXPERIENCED_MOVER** | **11.54%** | **3.35x** | 130 leads |
| **TIER_3_MODERATE_BLEEDER** | **9.52%** | **2.77x** | 84 leads |
| **TIER_2_PROVEN_MOVER** | **8.59%** | **2.50x** | 1,281 leads |
| **TIER_5_HEAVY_BLEEDER** | **7.27%** | **2.11x** | 674 leads |
| **STANDARD** | 3.82% | 1.0x | ~37,034 leads |

**Bottom Line:** By focusing on priority tier leads, sales teams can expect **2.0x to 4.3x improvement** in conversion efficiency compared to random selection.

---

## Development Philosophy

### Why Rules-Based Over ML?
1. **Explainability:** Every tier assignment can be explained in plain English
2. **Trust:** Sales team can audit and understand decisions
3. **Performance:** Achieved 4.3x lift (better than V2's 1.50x)
4. **Maintainability:** Rules are easier to update than retraining ML models
5. **No Black Box:** Transparent business logic vs mysterious algorithms

### Key Principles
- **Zero Data Leakage:** All features calculated using only data available at contact time
- **Statistical Validation:** Confidence intervals confirm tier significance
- **Temporal Validation:** Test on future data the model never saw
- **Iterative Improvement:** Continuous refinement based on performance data

---

## Security & Credentials

**Important:** This repository uses `.gitignore` to exclude sensitive files:
- Google Cloud credentials (`*-credentials.json`, `*-key.json`)
- N8N manifest files (`manifest.json`)
- Environment variables (`.env` files)
- Large data files (CSV, Excel, database files)

**Never commit credentials or sensitive data to this repository.**

---

## Contributing

When making changes to the model:
1. **Document Changes:** Update `VERSION_3_MODEL_REPORT.md` with version history
2. **Validate Performance:** Run validation scripts to ensure tier performance is maintained
3. **Update Lead List Query:** Ensure `January_2026_Lead_List_Query_V3.2.sql` reflects model changes
4. **Test Thoroughly:** Validate on historical data before deploying to production

---

## License & Usage

This repository contains proprietary lead scoring algorithms and data processing code for internal use only.

---

## Contact & Support

For questions about the model or lead list generation:
1. Review [`Version-3/VERSION_3_MODEL_REPORT.md`](./Version-3/VERSION_3_MODEL_REPORT.md) for technical details
2. Check [`Version-3/V3_Lead_Scoring_Model_Complete_Guide.md`](./Version-3/V3_Lead_Scoring_Model_Complete_Guide.md) for usage instructions
3. Review execution logs in `Version-3/EXECUTION_LOG.md` for deployment history

---

**Last Updated:** December 25, 2025  
**Current Model Versions:** 
- **V3.2.5** (Primary Prioritization) - Rules-based tier system with rich narratives
- **V4.0.0** (Upgrade Path Filter) - XGBoost ML model with SHAP narratives  
**Status:** ✅ Production Ready (Hybrid Deployment with V4 Upgrade Path, SHAP Narratives, Job Titles, Firm Exclusions, Recyclable Lead Lists)

**Version History:**
- **December 24, 2025:** Updated hybrid approach from V4 deprioritization to V4 upgrade path based on data-driven investigation findings. V3 tier ordering validated (T1 > T2, statistically significant). V4 upgrade path adds 486 high-quality leads (20.25% of list) with expected 4.60% conversion rate.
- **December 24, 2025 (Evening):** Enhanced lead list generation with SHAP narratives, job titles, and firm exclusions:
  - **SHAP Narratives**: V4 upgrade leads now include personalized explanations (e.g., "relatively new at firm AND history of changing firms")
  - **Job Titles**: Added `job_title` column from FINTRX for SDR context
  - **Firm Exclusions**: Excluded Savvy Advisors (CRD 318493) and Ritholtz Wealth Management (CRD 168652)
  - **Narrative Coverage**: 100% of leads have human-readable explanations (V3 tier narratives or V4 SHAP narratives)
  - **SHAP Features**: Top 3 ML features included for V4 upgrades (`shap_top1/2/3_feature`)
- **December 25, 2025:** Implemented Recyclable Lead List Generation system with unified scoring:
  - **Unified Scoring**: Replaced P1-P6 priority tiers with single `recyclable_score` (129-165 range) combining V3 tier signals, V4 ML predictions, timing indicators, and recycling-specific factors
  - **V3 Integration**: Recyclable list uses same V3 tier logic as Provided Lead List for consistency
  - **V4 Integration**: Leverages V4 ML scores and SHAP narratives for recyclable leads
  - **Smart Exclusions**: Automatically excludes recent firm changers (< 2 years) and no-go dispositions
  - **Comprehensive Narratives**: Every recyclable lead includes explanation of why it's being recycled
  - **Expected Conversions**: Score-to-conversion mapping (9.9% avg rate, 59.5 expected conversions per 600 leads)
  - **Files**: `sql/recycling/recyclable_pool_master_v2.1.sql` (unified scoring query), `scripts/recycling/generate_recyclable_list_v2.1.py` (generation script)

