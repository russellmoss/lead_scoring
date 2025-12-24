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

**How They Work Together:**
```
Lead Scoring Pipeline:
1. V3 Rules → Assign Tier (T1A, T1B, T1, T2, T3, T4, T5, STANDARD)
2. V4 Score → Assign Percentile (1-100) and deprioritize flag
3. Final Lead List:
   - V3 T1-T2 leads → HIGHEST PRIORITY (regardless of V4 score)
   - V3 T3-T5 leads → HIGH PRIORITY (if V4 percentile > 20%)
   - V3 STANDARD leads → SKIP if V4 deprioritize = TRUE (bottom 20%)
   - All other leads → Standard priority
```

**Expected Impact:**
- **V3 Prioritization**: 1.74x lift on top decile (best leads)
- **V4 Deprioritization**: 11.7% efficiency gain (skip 20% of leads, lose only 8.3% of conversions)
- **Combined**: Best of both worlds - identify top leads AND filter out bottom leads

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

### Version 4.0.0 (Deprioritization Filter)

**Model Type:** XGBoost machine learning model  
**Performance:** Identifies bottom 20% with 1.33% conversion (58% below baseline)  
**Status:** ✅ Production Ready (Deprioritization Filter)

**What is V4?**
V4 is an XGBoost machine learning model trained on historical lead conversion data to identify leads that should be **deprioritized or skipped**. Unlike V3, which focuses on finding the best leads, V4 excels at finding the worst leads.

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
- **Bottom 20%**: Converts at 1.33% (0.42x lift, 58% below baseline)
- **Top 80%**: Converts at 3.66% (1.15x lift, 14% above baseline)
- **Efficiency Gain**: Skip 20% of leads, lose only 8.3% of conversions = **11.7% efficiency gain**

**Why V4 Doesn't Replace V3:**
- **V3 Top Decile Lift**: 1.74x (better than V4's 1.51x)
- **V4 Deprioritization**: 0.42x on bottom 20% (V3 doesn't do this)
- **Use Case**: V3 for prioritization, V4 for deprioritization = **complementary, not competitive**

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
   - Calculate percentiles (1-100) and deprioritize flags (bottom 20%)
   - Output: `ml_features.v4_prospect_scores`

3. **Generate Hybrid Lead List** (`sql/January_2026_Lead_List_V3_V4_Hybrid.sql`)
   - Apply V3 tier logic to all prospects
   - Join V4 scores and filter out `v4_deprioritize = TRUE` leads
   - Apply tier quotas and LinkedIn prioritization
   - Output: `ml_features.january_2026_lead_list_v4` (2,400 leads)

4. **Export to CSV** (`scripts/export_lead_list.py`)
   - Export lead list with all V3 and V4 columns
   - Validate data quality (no duplicates, required fields present)
   - Output: `exports/january_2026_lead_list_YYYYMMDD.csv`

**Result:**
- **2,400 prioritized leads** with V3 tier assignments
- **Zero bottom 20% leads** (all filtered out by V4)
- **Average V4 percentile: 95.6** (top 5% of prospects)
- **99.9% LinkedIn coverage** for SDR outreach

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
│   ├── sql/
│   │   ├── v4_prospect_features.sql      # V4 features for all prospects
│   │   └── January_2026_Lead_List_V3_V4_Hybrid.sql  # Hybrid query
│   ├── scripts/
│   │   ├── score_prospects_monthly.py    # V4 scoring script
│   │   └── export_lead_list.py           # CSV export script
│   ├── exports/             # Generated CSV lead lists (gitignored)
│   └── logs/                # Execution logs
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
- **Deployment:** Integrated into monthly lead list generation as deprioritization filter
- **Hybrid Integration:** Works alongside V3 to filter bottom 20% while V3 prioritizes top tiers

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
- `v4_prospect_scores` - V4 scoring table (percentiles and deprioritize flags)
- `january_2026_lead_list_v4` - Generated hybrid lead lists (V3 + V4)

---

## Getting Started

### For Model Users (Sales Team)
1. **Use Hybrid Lead Lists:** Monthly lead lists are generated using both V3 and V4 (see `Lead_List_Generation/`)
2. **Review Tier Assignments:** Each lead includes V3 tier, expected conversion rate, and V4 percentile
3. **Prioritize Outreach:** 
   - **Highest Priority**: V3 Tier 1A/1B/1 leads (regardless of V4 score)
   - **High Priority**: V3 Tier 2-5 leads with V4 percentile > 20%
   - **Skip**: Leads with V4 deprioritize flag = TRUE (bottom 20%, unless V3 Tier 1-2)
4. **Export Format:** CSV files in `Lead_List_Generation/exports/` with all scoring columns

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
- **Export Script:** [`Lead_List_Generation/scripts/export_lead_list.py`](./Lead_List_Generation/scripts/export_lead_list.py)
- **Process Documentation:** [`Lead_List_Generation/Monthly_Lead_List_Generation_V3_V4_Hybrid.md`](./Lead_List_Generation/Monthly_Lead_List_Generation_V3_V4_Hybrid.md)

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

**Last Updated:** December 2025  
**Current Model Versions:** 
- **V3.2.5** (Primary Prioritization) - Rules-based tier system
- **V4.0.0** (Deprioritization Filter) - XGBoost ML model  
**Status:** ✅ Production Ready (Hybrid Deployment)

