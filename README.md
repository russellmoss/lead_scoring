# Lead Scoring Model Development Repository

**Purpose:** Iteratively develop and deploy lead scoring algorithms and lead list generation systems for financial advisor recruitment.

**Current Production Model:** [Version 3.2.5](./Version-3/VERSION_3_MODEL_REPORT.md) - Rules-based tiered classification system with LinkedIn prioritization

**Status:** ✅ Production Ready - Generating lead lists for sales outreach campaigns

---

## Repository Overview

This repository contains the complete development history of lead scoring models for identifying high-conversion financial advisor prospects. The project has evolved through multiple iterations, from machine learning approaches (Version 1 & 2) to a rules-based tier system (Version 3) that achieves superior performance with full explainability.

### Key Objectives

1. **Lead Scoring:** Identify which financial advisor leads are most likely to convert from "Contacted" to "MQL" (Marketing Qualified Lead) within 30 days
2. **Lead List Generation:** Generate prioritized, actionable lead lists for sales team outreach campaigns
3. **Iterative Improvement:** Continuously refine models based on performance data and business feedback

---

## Current Production System

### Version 3.2.5 (Deployed)

**Model Type:** Rules-based tiered classification system  
**Performance:** 2.0x to 4.3x lift over baseline conversion rates  
**Status:** ✅ Production Ready

**Key Features:**
- **Tier-based prioritization:** 8 priority tiers (1A, 1B, 1, 1F, 2, 3, 4, 5) plus STANDARD baseline
- **Certification boost:** CFP holders and Series 65-only advisors get highest priority (Tier 1A/1B)
- **LinkedIn prioritization:** ≥90% of leads have LinkedIn URLs (V3.2.5)
- **Producing advisor filter:** Only includes advisors who actively manage client assets
- **Title exclusions:** Data-driven exclusions remove non-advisor roles (operations, compliance, etc.)
- **Insurance exclusions:** Filters out insurance agents and insurance-focused firms

**Lead List Generation:**
- **Query:** [`Version-3/January_2026_Lead_List_Query_V3.2.sql`](./Version-3/January_2026_Lead_List_Query_V3.2.sql)
- **Output:** 2,400 prioritized leads with tier assignments, expected conversion rates, and detailed narratives
- **Source:** New prospects (not in Salesforce) + Recyclable leads (180+ days no contact)
- **Diversity:** Maximum 50 leads per firm to ensure broad market coverage

**Comprehensive Documentation:**
- **Full Technical Report:** [`Version-3/VERSION_3_MODEL_REPORT.md`](./Version-3/VERSION_3_MODEL_REPORT.md)
- **Model Guide:** [`Version-3/V3_Lead_Scoring_Model_Complete_Guide.md`](./Version-3/V3_Lead_Scoring_Model_Complete_Guide.md)

---

## Repository Structure

```
Lead Scoring/
├── Version-3/              # ✅ CURRENT PRODUCTION MODEL
│   ├── VERSION_3_MODEL_REPORT.md          # Comprehensive technical documentation
│   ├── January_2026_Lead_List_Query_V3.2.sql  # Production lead list generator
│   ├── sql/                 # SQL feature engineering and tier logic
│   ├── scripts/             # Phase execution scripts
│   ├── reports/             # Validation and analysis reports
│   └── models/              # Model registry and metadata
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

### Version 3: Rules-Based Tier System (Current Production)
- **Approach:** SQL-based business rules (not ML)
- **Performance:** 2.0x to 4.3x lift across priority tiers
- **Key Innovation:** Point-in-Time (PIT) feature engineering eliminates data leakage
- **Explainability:** Every tier assignment is transparent and auditable
- **Status:** ✅ Production Ready

**Version 3 Evolution:**
- **V3.1:** Initial rules-based tier system (3.69x lift for Tier 1)
- **V3.2:** Added firm size signals and proven mover segment (7.29x lift for Tier 1A)
- **V3.2.1:** Added certification-based tiers (CFP, Series 65) - 4.3x+ lift
- **V3.2.2:** Added High-Value Wealth tier (3.35x lift)
- **V3.2.3:** Added producing advisor filter
- **V3.2.4:** Added insurance exclusions
- **V3.2.5:** Added LinkedIn prioritization (≥90% coverage)

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
- `lead_scoring_features_pit` - Feature engineering table (37 features)
- `lead_scores_v3_2_12212025` - Production scoring table
- `january_2026_lead_list` - Generated lead lists

---

## Getting Started

### For Model Users (Sales Team)
1. **Query Lead Lists:** Use `Version-3/January_2026_Lead_List_Query_V3.2.sql` to generate prioritized lead lists
2. **Review Tier Assignments:** Each lead includes tier, expected conversion rate, and explanation narrative
3. **Prioritize Outreach:** Focus on Tier 1A/1B/1 leads first (highest conversion rates)

### For Developers
1. **Read Documentation:** Start with [`Version-3/VERSION_3_MODEL_REPORT.md`](./Version-3/VERSION_3_MODEL_REPORT.md)
2. **Understand Architecture:** Review the tier logic in `Version-3/sql/phase_4_v3_tiered_scoring.sql`
3. **Run Validation:** Execute phase scripts in `Version-3/scripts/` to validate model performance

---

## Key Files

### Production Files
- **Lead List Generator:** [`Version-3/January_2026_Lead_List_Query_V3.2.sql`](./Version-3/January_2026_Lead_List_Query_V3.2.sql)
- **Tier Logic:** [`Version-3/sql/phase_4_v3_tiered_scoring.sql`](./Version-3/sql/phase_4_v3_tiered_scoring.sql)
- **Feature Engineering:** [`Version-3/sql/lead_scoring_features_pit.sql`](./Version-3/sql/lead_scoring_features_pit.sql)

### Documentation
- **Technical Report:** [`Version-3/VERSION_3_MODEL_REPORT.md`](./Version-3/VERSION_3_MODEL_REPORT.md) ⭐ **START HERE**
- **User Guide:** [`Version-3/V3_Lead_Scoring_Model_Complete_Guide.md`](./Version-3/V3_Lead_Scoring_Model_Complete_Guide.md)
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
**Current Model Version:** V3.2.5_12232025_LINKEDIN_PRIORITIZATION  
**Status:** ✅ Production Ready

