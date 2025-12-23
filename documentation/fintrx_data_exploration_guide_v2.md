# FINTRX BigQuery Data Exploration Guide v2.0

## Purpose
This document provides step-by-step prompts for Cursor.ai to systematically explore all 25 tables in `savvy-gtm-analytics.FinTrx_data` and generate comprehensive, **accurate** data architecture documentation.

## CRITICAL: Validated Findings (Do NOT Re-Discover)

Before exploring, Cursor.ai must understand these **confirmed facts**:

### ✅ Confirmed Data Types
| Field | Table | Actual Type | Query Syntax |
|-------|-------|-------------|--------------|
| `REP_LICENSES` | ria_contacts_current | **STRING** (not ARRAY) | Use `LIKE '%Series 7%'` or `JSON_EXTRACT_ARRAY()` |
| Other "array" fields | various | Likely STRING | Verify each, do NOT assume ARRAY |

### ✅ Confirmed Table Structure
| What We Expected | What Actually Exists |
|------------------|---------------------|
| Monthly contact snapshots | ❌ **NO contact-level historical snapshots exist** |
| `Firm_historicals` for firms | ✅ Yes, monthly firm snapshots |
| Contact history tables | ✅ Only: employment, accolades, registrations, BD states |

### ✅ Confirmed Coverage Issues
| Table | Field | Coverage |
|-------|-------|----------|
| `private_wealth_teams_ps` | `AUM` | **Only 20.1%** have AUM data (5,304 of 26,368 teams) |
| `ria_contacts_current` | `REP_AUM` | ~99% NULL |
| `contact_accolades_historicals` | all | Only 4.8% of contacts have accolades |

### ⚠️ Point-in-Time (PIT) Limitations
For lead scoring, you wanted to get a rep's snapshot BEFORE contact date. Here's what's actually possible:

| Data Type | PIT Possible? | How |
|-----------|---------------|-----|
| **Firm AUM** | ✅ Yes | Use `Firm_historicals` with YEAR/MONTH filter |
| **Rep's Employer** | ✅ Yes | Use `contact_registered_employment_history` date filter |
| **Rep's Accolades** | ✅ Yes | Use `contact_accolades_historicals` YEAR filter |
| **Rep's State Registrations** | ✅ Yes | Use `contact_state_registrations_historicals` |
| **Rep's Licenses** | ❌ No | Only current state in `ria_contacts_current` |
| **Rep's AUM** | ❌ No | Only current state (and 99% NULL anyway) |
| **Rep's Tenure** | ⚠️ Partial | Calculate from employment history, not stored field |
| **Team AUM** | ❌ No | Only current state in `private_wealth_teams_ps` |

---

## Output Location
All documentation should be saved to: `C:\Users\russe\Big_Query\documentation\`

**Files to Generate:**
1. `FINTRX_Data_Dictionary.md` - Complete field-level documentation
2. `FINTRX_Architecture_Overview.md` - Executive summary with ERD
3. `FINTRX_Lead_Scoring_Features.md` - Curated list of scoring features
4. `FINTRX_PIT_Query_Templates.sql` - Point-in-time SQL templates
5. `FINTRX_Data_Quality_Report.md` - Quality check findings

---

# PHASE 1: Verify Table Inventory & Row Counts

## Prompt 1.1: Get Complete Table Inventory
**Prompt for Cursor.ai:**
> "Query BigQuery to get a complete inventory of all tables in `savvy-gtm-analytics.FinTrx_data`. For each table, get the table name, row count, and size in MB. Save results for documentation."

```sql
SELECT
  table_id as table_name,
  row_count,
  ROUND(size_bytes / 1024 / 1024, 2) AS size_mb
FROM `savvy-gtm-analytics.FinTrx_data.__TABLES__`
ORDER BY row_count DESC;
```

---

# PHASE 2: Core Tables - Full Schema Discovery

## Prompt 2.1: Get COMPLETE Schema for ria_contacts_current
**Prompt for Cursor.ai:**
> "Get the COMPLETE schema for `ria_contacts_current` - every single column, its exact data type, and nullability. This is critical because we need to know which fields are STRING vs ARRAY. Do NOT assume any field is an array unless the data_type explicitly says ARRAY."

```sql
SELECT 
  ordinal_position,
  column_name,
  data_type,
  is_nullable
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'ria_contacts_current'
ORDER BY ordinal_position;
```

## Prompt 2.2: Sample ria_contacts_current Data
**Prompt for Cursor.ai:**
> "Get 5 sample rows from `ria_contacts_current` to see actual data formats. Pay special attention to fields that look like they might contain arrays or JSON (REP_LICENSES, RIA_REGISTERED_LOCATIONS, ACCOLADES, PASSIONS_AND_INTERESTS, etc.). Document whether they are stored as JSON strings, comma-separated strings, or actual arrays."

```sql
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
LIMIT 5;
```

## Prompt 2.3: Check String-Array Fields Format
**Prompt for Cursor.ai:**
> "For each field that appears to contain multiple values, check the actual format. We confirmed REP_LICENSES is STRING. Check if it's JSON array format, comma-separated, or something else."

```sql
-- Check format of multi-value string fields
SELECT 
  RIA_CONTACT_CRD_ID,
  REP_LICENSES,
  RIA_REGISTERED_LOCATIONS,
  BD_REGISTERED_LOCATIONS,
  ACCOLADES,
  PASSIONS_AND_INTERESTS
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
WHERE REP_LICENSES IS NOT NULL
LIMIT 10;
```

## Prompt 2.4: Get COMPLETE Schema for ria_firms_current
**Prompt for Cursor.ai:**
> "Get the COMPLETE schema for `ria_firms_current`. Same approach - document every column and exact data type."

```sql
SELECT 
  ordinal_position,
  column_name,
  data_type,
  is_nullable
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'ria_firms_current'
ORDER BY ordinal_position;
```

## Prompt 2.5: Sample ria_firms_current Data
**Prompt for Cursor.ai:**
> "Get 5 sample rows from `ria_firms_current`. Check format of ENTITY_CLASSIFICATION, FEE_STRUCTURE, INVESTMENTS_UTILIZED, ALTERNATIVES, and other multi-value fields."

```sql
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current`
LIMIT 5;
```

---

# PHASE 3: Historical Tables - Understanding the Snapshot System

## Prompt 3.1: Firm_historicals Complete Schema
**Prompt for Cursor.ai:**
> "Get the complete schema for `Firm_historicals`. This is the ONLY table with monthly snapshots. Identify the snapshot date fields (YEAR, MONTH) and all metric fields."

```sql
SELECT 
  ordinal_position,
  column_name,
  data_type
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'Firm_historicals'
ORDER BY ordinal_position;
```

## Prompt 3.2: Firm_historicals Snapshot Distribution
**Prompt for Cursor.ai:**
> "Analyze the snapshot coverage in Firm_historicals. How many months? What's the date range? How many firms per month?"

```sql
SELECT 
  YEAR,
  MONTH,
  COUNT(*) as records,
  COUNT(DISTINCT RIA_INVESTOR_CRD_ID) as unique_firms,
  COUNTIF(TOTAL_AUM IS NOT NULL) as firms_with_aum,
  ROUND(COUNTIF(TOTAL_AUM IS NOT NULL) / COUNT(*) * 100, 1) as aum_coverage_pct
FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
GROUP BY YEAR, MONTH
ORDER BY YEAR, MONTH;
```

## Prompt 3.3: Employment History Schema and Sample
**Prompt for Cursor.ai:**
> "Get schema and sample data for `contact_registered_employment_history`. This is how we determine where a rep worked at a specific point in time."

```sql
-- Schema
SELECT column_name, data_type
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'contact_registered_employment_history'
ORDER BY ordinal_position;
```

```sql
-- Sample one rep's full employment history
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
WHERE RIA_CONTACT_CRD_ID = (
  SELECT RIA_CONTACT_CRD_ID
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
  LIMIT 1
)
ORDER BY PREVIOUS_REGISTRATION_COMPANY_START_DATE;
```

## Prompt 3.4: State Registrations Historical Schema
**Prompt for Cursor.ai:**
> "Get schema for `contact_state_registrations_historicals`. This is large (19M+ rows) so just get schema and a small sample."

```sql
SELECT column_name, data_type
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'contact_state_registrations_historicals'
ORDER BY ordinal_position;
```

```sql
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data.contact_state_registrations_historicals`
LIMIT 10;
```

---

# PHASE 4: Team Data (Critical - Low Coverage)

## Prompt 4.1: private_wealth_teams_ps Complete Analysis
**Prompt for Cursor.ai:**
> "We confirmed only 20.1% of teams have AUM data. Get the complete schema, then analyze what data IS available and what's missing."

```sql
-- Schema
SELECT column_name, data_type
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'private_wealth_teams_ps'
ORDER BY ordinal_position;
```

```sql
-- Coverage analysis for all fields
SELECT 
  COUNT(*) as total_teams,
  COUNTIF(AUM IS NOT NULL) as has_aum,
  COUNTIF(TEAM_NAME IS NOT NULL) as has_name,
  COUNTIF(CRD_ID IS NOT NULL) as has_firm_crd,
  COUNTIF(MINIMUM_ACCOUNT_SIZE IS NOT NULL) as has_min_account,
  ROUND(COUNTIF(AUM IS NOT NULL) / COUNT(*) * 100, 1) as aum_pct,
  ROUND(COUNTIF(CRD_ID IS NOT NULL) / COUNT(*) * 100, 1) as firm_crd_pct
FROM `savvy-gtm-analytics.FinTrx_data.private_wealth_teams_ps`;
```

```sql
-- Sample teams WITH AUM data
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data.private_wealth_teams_ps`
WHERE AUM IS NOT NULL
ORDER BY AUM DESC
LIMIT 10;
```

## Prompt 4.2: Verify Contact-to-Team Join
**Prompt for Cursor.ai:**
> "Test the join from contacts to teams via WEALTH_TEAM_ID fields. How many contacts are actually on teams with AUM data?"

```sql
-- Check WEALTH_TEAM_ID fields exist
SELECT column_name
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'ria_contacts_current'
  AND column_name LIKE '%TEAM%';
```

```sql
-- Count contacts with team associations and AUM
SELECT 
  COUNT(*) as total_contacts,
  COUNTIF(WEALTH_TEAM_ID_1 IS NOT NULL) as has_team_1,
  COUNTIF(WEALTH_TEAM_ID_2 IS NOT NULL) as has_team_2,
  COUNTIF(WEALTH_TEAM_ID_3 IS NOT NULL) as has_team_3
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`;
```

```sql
-- How many contacts can actually get team AUM?
SELECT 
  COUNT(DISTINCT c.RIA_CONTACT_CRD_ID) as contacts_with_team_aum
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current` c
INNER JOIN `savvy-gtm-analytics.FinTrx_data.private_wealth_teams_ps` t
  ON c.WEALTH_TEAM_ID_1 = t.ID
WHERE t.AUM IS NOT NULL;
```

---

# PHASE 5: Enrichment Tables

## Prompt 5.1: Accolades Schema and Distribution
**Prompt for Cursor.ai:**
> "Get complete schema for `contact_accolades_historicals` and analyze the distribution by outlet and year."

```sql
SELECT column_name, data_type
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'contact_accolades_historicals'
ORDER BY ordinal_position;
```

```sql
-- Distribution by outlet
SELECT 
  OUTLET,
  COUNT(*) as accolade_count,
  COUNT(DISTINCT RIA_CONTACT_CRD_ID) as unique_contacts,
  MIN(YEAR) as min_year,
  MAX(YEAR) as max_year
FROM `savvy-gtm-analytics.FinTrx_data.contact_accolades_historicals`
GROUP BY OUTLET
ORDER BY accolade_count DESC;
```

## Prompt 5.2: Passions and Interests Structure
**Prompt for Cursor.ai:**
> "Get the EXACT schema for `passions_and_interests`. We need to know if interests are stored as individual boolean columns, an array, or JSON string."

```sql
SELECT column_name, data_type
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'passions_and_interests'
ORDER BY ordinal_position;
```

```sql
-- Sample to see actual structure
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data.passions_and_interests`
LIMIT 5;
```

---

# PHASE 6: Compliance & Disclosure Tables

## Prompt 6.1: Historical_Disclosure_data Schema and Types
**Prompt for Cursor.ai:**
> "Get schema for `Historical_Disclosure_data` and analyze disclosure type distribution."

```sql
SELECT column_name, data_type
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'Historical_Disclosure_data'
ORDER BY ordinal_position;
```

```sql
-- What types of disclosures exist?
SELECT 
  DISCLOSURE_TYPE,  -- Adjust field name based on schema
  COUNT(*) as count,
  COUNT(DISTINCT RIA_CONTACT_CRD_ID) as unique_contacts
FROM `savvy-gtm-analytics.FinTrx_data.Historical_Disclosure_data`
GROUP BY 1
ORDER BY count DESC;
```

---

# PHASE 7: Relationship Tables

## Prompt 7.1: Contact-Firm Relationship Verification
**Prompt for Cursor.ai:**
> "Verify the contact-to-firm join keys. Test that PRIMARY_FIRM joins to ria_firms_current.CRD_ID correctly."

```sql
-- Check join key names
SELECT column_name
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'ria_contacts_current'
  AND (column_name LIKE '%FIRM%' OR column_name LIKE '%CRD%' OR column_name LIKE '%RIA%' OR column_name LIKE '%BD%');
```

```sql
-- Test the join and count orphans
SELECT 
  COUNT(*) as total_contacts,
  COUNTIF(c.PRIMARY_FIRM IS NOT NULL) as has_primary_firm,
  COUNTIF(c.PRIMARY_FIRM IS NOT NULL AND f.CRD_ID IS NULL) as orphaned_contacts
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current` c
LEFT JOIN `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f
  ON c.PRIMARY_FIRM = f.CRD_ID;
```

## Prompt 7.2: All Other Table Schemas (Quick Pass)
**Prompt for Cursor.ai:**
> "Get schemas for remaining tables. These are lower priority but document them for completeness."

```sql
-- Get all remaining table schemas in one query
SELECT 
  table_name,
  column_name,
  data_type,
  ordinal_position
FROM `savvy-gtm-analytics.FinTrx_data.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name IN (
  'custodians_historicals',
  'affiliates_historicals',
  'news_ps',
  'ria_contact_news',
  'ria_investors_news',
  'industry_exam_bd_historicals',
  'industry_exams_ia_historicals',
  'schedule_d_section_A_historicals',
  'schedule_d_section_B_historicals',
  'ria_contact_firm_relationships',
  'wealth_team_members',
  'contact_branch_data',
  'private_fund_data',
  'ria_investors_private_fund_relationships',
  'firm_accolades_historicals',
  'contact_broker_dealer_state_historicals'
)
ORDER BY table_name, ordinal_position;
```

---

# PHASE 8: Data Quality Checks

## Prompt 8.1: NULL Rate Analysis for Key Fields
**Prompt for Cursor.ai:**
> "Calculate NULL rates for all key lead scoring fields in ria_contacts_current."

```sql
SELECT 
  COUNT(*) as total,
  -- Identifiers
  ROUND(COUNTIF(RIA_CONTACT_CRD_ID IS NULL) / COUNT(*) * 100, 2) as crd_null_pct,
  -- AUM fields
  ROUND(COUNTIF(REP_AUM IS NULL) / COUNT(*) * 100, 2) as rep_aum_null_pct,
  ROUND(COUNTIF(PRIMARY_FIRM_TOTAL_AUM IS NULL) / COUNT(*) * 100, 2) as firm_aum_null_pct,
  -- Experience
  ROUND(COUNTIF(INDUSTRY_TENURE_MONTHS IS NULL) / COUNT(*) * 100, 2) as tenure_null_pct,
  ROUND(COUNTIF(REP_LICENSES IS NULL) / COUNT(*) * 100, 2) as licenses_null_pct,
  -- Contact info
  ROUND(COUNTIF(EMAIL IS NULL) / COUNT(*) * 100, 2) as email_null_pct,
  ROUND(COUNTIF(MOBILE_PHONE_NUMBER IS NULL) / COUNT(*) * 100, 2) as mobile_null_pct,
  -- Firm relationship
  ROUND(COUNTIF(PRIMARY_FIRM IS NULL) / COUNT(*) * 100, 2) as primary_firm_null_pct,
  -- Team
  ROUND(COUNTIF(WEALTH_TEAM_ID_1 IS NULL) / COUNT(*) * 100, 2) as team_id_null_pct
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`;
```

## Prompt 8.2: Firm_historicals AUM Coverage by Month
**Prompt for Cursor.ai:**
> "Check AUM data quality in historical snapshots."

```sql
SELECT 
  YEAR,
  MONTH,
  COUNT(*) as total_records,
  COUNTIF(TOTAL_AUM IS NOT NULL) as has_aum,
  ROUND(AVG(TOTAL_AUM), 0) as avg_aum,
  ROUND(COUNTIF(TOTAL_AUM IS NOT NULL) / COUNT(*) * 100, 1) as coverage_pct
FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
GROUP BY YEAR, MONTH
ORDER BY YEAR, MONTH;
```

---

# PHASE 9: Build Documentation Files

## Prompt 9.1: Generate Data Dictionary
**Prompt for Cursor.ai:**
> "Using all the schema and sample data collected, create a comprehensive Data Dictionary markdown file. 
>
> IMPORTANT CORRECTIONS to include:
> - REP_LICENSES is STRING type (not ARRAY) - document the actual format (JSON string, comma-separated, etc.)
> - There is NO contact-level historical snapshot table
> - TEAM_AUM coverage is only 20.1%
> - Document actual NULL rates for each field
>
> For each table include: purpose, row count, all columns with EXACT data types, primary key, foreign keys, and data quality notes.
>
> Save to: `C:\Users\russe\Big_Query\documentation\FINTRX_Data_Dictionary.md`"

## Prompt 9.2: Generate Architecture Overview
**Prompt for Cursor.ai:**
> "Create an Architecture Overview document that accurately reflects the data structure.
>
> CRITICAL: Include a clear section on PIT (Point-in-Time) LIMITATIONS:
> - Firm-level data: ✅ Monthly snapshots available via Firm_historicals
> - Contact-level data: ❌ NO snapshots - ria_contacts_current is current state ONLY
> - Employment: ✅ Historical via contact_registered_employment_history
> - Accolades: ✅ Historical with YEAR field
> - Licenses, Tenure, Rep AUM: ❌ Current state only
>
> Include Mermaid ERD and all join paths.
>
> Save to: `C:\Users\russe\Big_Query\documentation\FINTRX_Architecture_Overview.md`"

## Prompt 9.3: Generate Lead Scoring Features Document
**Prompt for Cursor.ai:**
> "Create a Lead Scoring Features document with HONEST coverage assessments:
>
> Include for each feature:
> - Table and field name
> - EXACT data type
> - NULL rate / coverage percentage
> - Whether PIT query is possible
> - Query syntax notes (especially for STRING fields that contain JSON)
>
> Key corrections:
> - TEAM_AUM: Only 20.1% coverage (5,304 of 26,368 teams)
> - REP_AUM: ~99% NULL - essentially unusable
> - REP_LICENSES: STRING type, need JSON_EXTRACT_ARRAY() or LIKE queries
> - No contact-level historical snapshots
>
> Save to: `C:\Users\russe\Big_Query\documentation\FINTRX_Lead_Scoring_Features.md`"

## Prompt 9.4: Generate PIT Query Templates
**Prompt for Cursor.ai:**
> "Create Point-in-Time Query Templates that ONLY include queries that are actually possible:
>
> ✅ INCLUDE templates for:
> - Firm AUM as of date (via Firm_historicals YEAR/MONTH)
> - Employment at date (via contact_registered_employment_history date range)
> - Accolades as of date (via YEAR filter)
> - State registrations as of date
> - Disclosure check as of date
>
> ⚠️ CLEARLY DOCUMENT that these are NOT possible:
> - Rep-level AUM as of date (no historical data)
> - Licenses as of date (current state only)
> - Team AUM as of date (current state only)
>
> For STRING fields containing JSON (like REP_LICENSES), show correct parsing syntax.
>
> Save to: `C:\Users\russe\Big_Query\documentation\FINTRX_PIT_Query_Templates.sql`"

## Prompt 9.5: Generate Data Quality Report
**Prompt for Cursor.ai:**
> "Create a Data Quality Report with ACTUAL findings from queries:
>
> Key findings to document:
> - REP_LICENSES is STRING, not ARRAY
> - No contact-level historical snapshots exist
> - TEAM_AUM only 20.1% coverage
> - REP_AUM ~99% NULL
> - Actual NULL rates for all key fields
>
> Include referential integrity checks and recommendations.
>
> Save to: `C:\Users\russe\Big_Query\documentation\FINTRX_Data_Quality_Report.md`"

---

# PHASE 10: Final Validation

## Prompt 10.1: Cross-Check All Join Keys
**Prompt for Cursor.ai:**
> "Run final validation to ensure all documented joins work correctly. Test each primary join path and document any issues."

```sql
-- Test all major joins
WITH join_tests AS (
  SELECT 'contact_to_firm' as join_name,
    COUNT(*) as total,
    COUNTIF(f.CRD_ID IS NOT NULL) as matched
  FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current` c
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f ON c.PRIMARY_FIRM = f.CRD_ID
  WHERE c.PRIMARY_FIRM IS NOT NULL
  
  UNION ALL
  
  SELECT 'contact_to_team',
    COUNT(*),
    COUNTIF(t.ID IS NOT NULL)
  FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current` c
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.private_wealth_teams_ps` t ON c.WEALTH_TEAM_ID_1 = t.ID
  WHERE c.WEALTH_TEAM_ID_1 IS NOT NULL
  
  UNION ALL
  
  SELECT 'firm_to_historicals',
    COUNT(*),
    COUNTIF(h.RIA_INVESTOR_CRD_ID IS NOT NULL)
  FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current` f
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h ON f.CRD_ID = h.RIA_INVESTOR_CRD_ID
)
SELECT 
  join_name,
  total,
  matched,
  ROUND(matched / total * 100, 1) as match_rate_pct
FROM join_tests;
```

---

# Summary: What Makes This Guide Different

| Issue | Previous Guide | This Guide |
|-------|----------------|------------|
| **Data Types** | Assumed ARRAY for licenses | Confirmed STRING - shows correct query syntax |
| **Contact Snapshots** | Implied they exist | Clearly states NO contact-level snapshots |
| **Team AUM Coverage** | Implied good coverage | Documents actual 20.1% coverage |
| **PIT Queries** | Templates for impossible queries | Only includes possible PIT queries |
| **NULL Rates** | Estimated | Will use actual measured values |

---

# Checklist: Files to Generate

After completing all phases, these files should exist in `C:\Users\russe\Big_Query\documentation\`:

- [ ] `FINTRX_Data_Dictionary.md` - Complete, accurate field documentation
- [ ] `FINTRX_Architecture_Overview.md` - With correct PIT limitations
- [ ] `FINTRX_Lead_Scoring_Features.md` - With honest coverage stats
- [ ] `FINTRX_PIT_Query_Templates.sql` - Only possible queries
- [ ] `FINTRX_Data_Quality_Report.md` - With actual NULL rates

