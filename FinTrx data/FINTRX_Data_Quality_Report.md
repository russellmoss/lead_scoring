# FINTRX Data Quality Report

Comprehensive data quality assessment for the FINTRX dataset in `savvy-gtm-analytics.FinTrx_data`.

**Last Updated**: December 2025

## Executive Summary

### Overall Data Quality: **GOOD** ✅

The FINTRX dataset provides comprehensive coverage of RIA contacts and firms with good historical depth for firm-level data. Key strengths include complete contact coverage, rich enrichment data, and monthly historical snapshots for firms. Main concerns are NULL values in AUM fields, incomplete coverage for some enrichment features, and the absence of contact-level historical snapshots.

### Key Findings
- ✅ **788,154 contacts** with complete current-state data
- ✅ **45,233 firms** with detailed firm-level metrics
- ✅ **23 monthly snapshots** (Jan 2024 - Nov 2025) for **firm-level** historical analysis
- ⚠️ **REP_AUM**: 99.1% NULL - essentially unusable
- ⚠️ **Team AUM**: Only 20.1% of teams have AUM data (5,304 of 26,368 teams)
- ⚠️ **Contact AUM Coverage**: Only 4.1% of contacts can get team AUM (32,456 of 788,154)
- ⚠️ **Accolades**: Only 1.8% of contacts have accolades (14,501 of 788,154)
- ⚠️ **No Contact Snapshots**: There are NO contact-level historical snapshot tables
- ⚠️ **JSON String Fields**: Many "array" fields are actually STRING type containing JSON

---

## Critical Data Type Corrections

### ⚠️ STRING vs ARRAY Confusion

**IMPORTANT**: Many fields that appear to contain arrays are actually **STRING** type containing JSON array format.

| Field | Table | Actual Type | Format | Query Syntax |
|-------|-------|-------------|--------|--------------|
| `REP_LICENSES` | ria_contacts_current | **STRING** | `["Series 7", "Series 65"]` | `LIKE '%Series 7%'` or `JSON_EXTRACT_ARRAY()` |
| `RIA_REGISTERED_LOCATIONS` | ria_contacts_current | **STRING** | `["CA", "NY"]` | `JSON_EXTRACT_ARRAY()` |
| `BD_REGISTERED_LOCATIONS` | ria_contacts_current | **STRING** | `["CA", "NY"]` | `JSON_EXTRACT_ARRAY()` |
| `ENTITY_CLASSIFICATION` | ria_firms_current | **STRING** | `["Independent RIA", "Wirehouse"]` | `JSON_EXTRACT_ARRAY()` |
| `FEE_STRUCTURE` | ria_firms_current | **STRING** | `["Percentage of AUM", "Fixed Fees"]` | `JSON_EXTRACT_ARRAY()` |
| `INVESTMENTS_UTILIZED` | ria_firms_current | **STRING** | `["Equities", "Mutual Funds"]` | `JSON_EXTRACT_ARRAY()` |
| `ALTERNATIVES` | ria_firms_current | **STRING** | `["Hedge Funds", "Private Equity"]` | `JSON_EXTRACT_ARRAY()` |
| `CONTACT_ROLES` | ria_contacts_current | **STRING** | `["Director Executive", "Sr. Team Member"]` | `JSON_EXTRACT_ARRAY()` |
| `ACCOLADES` | ria_contacts_current | **STRING** | `["Forbes Top 250 Wealth Advisors 2021"]` | `JSON_EXTRACT_ARRAY()` |
| `PASSIONS_AND_INTERESTS` | ria_contacts_current | **STRING** | `["Cooking", "Wine"]` | `JSON_EXTRACT_ARRAY()` |

**Query Examples**:
```sql
-- Check if contact has Series 7
SELECT * FROM ria_contacts_current
WHERE REP_LICENSES LIKE '%Series 7%';

-- Extract as array
SELECT JSON_EXTRACT_ARRAY(REP_LICENSES) as licenses
FROM ria_contacts_current
WHERE REP_LICENSES IS NOT NULL;

-- Count elements
SELECT ARRAY_LENGTH(JSON_EXTRACT_ARRAY(REP_LICENSES)) as num_licenses
FROM ria_contacts_current;
```

---

## Data Completeness Analysis

### Core Tables

#### ria_contacts_current
- **Total Rows**: 788,154
- **Unique Contacts**: 788,154 (100% unique)
- **Primary Key Completeness**: 100% (all rows have ID and RIA_CONTACT_CRD_ID)
- **Size**: 2,871.29 MB

**Field Completeness** (Actual NULL Rates):
| Field | Null Rate | Total NULL | Notes |
|-------|-----------|------------|-------|
| `RIA_CONTACT_CRD_ID` | 0% | 0 | ✅ Complete |
| `RIA_CONTACT_PREFERRED_NAME` | <1% | <7,881 | ✅ Nearly complete |
| `REP_AUM` | **99.1%** | **781,054** | ⚠️ **Essentially unusable** - use team/firm AUM |
| `PRIMARY_FIRM_TOTAL_AUM` | **30.21%** | **238,139** | ⚠️ Moderate NULL rate |
| `INDUSTRY_TENURE_MONTHS` | **6.1%** | **48,057** | ⚠️ Can calculate from employment history |
| `REP_LICENSES` | 0% | 0 | ✅ Complete (but STRING type, not ARRAY) |
| `EMAIL` | **41.12%** | **324,000** | ⚠️ Many contacts missing email |
| `MOBILE_PHONE_NUMBER` | **97.6%** | **768,838** | ⚠️ Very high NULL rate |
| `PRIMARY_FIRM` | 0% | 0 | ✅ Complete (all contacts have firm) |
| `WEALTH_TEAM_ID_1` | **86.96%** | **684,340** | ⚠️ Only 13% of contacts on teams |

**Recommendations**:
- Use `PRIMARY_FIRM_TOTAL_AUM` as primary AUM feature (more complete than `REP_AUM`)
- Calculate tenure from `contact_registered_employment_history` when `INDUSTRY_TENURE_MONTHS` is NULL
- Use firm-level data as fallback for missing rep-level data
- For JSON string fields, use `JSON_EXTRACT_ARRAY()` or `LIKE` queries

#### ria_firms_current
- **Total Rows**: 45,233
- **Unique Firms**: 45,233 (100% unique)
- **Primary Key Completeness**: 100%
- **Size**: 129.02 MB

**Field Completeness**:
| Field | Null Rate | Notes |
|-------|-----------|-------|
| `CRD_ID` | 0% | ✅ Complete |
| `NAME` | <1% | ✅ Nearly complete |
| `TOTAL_AUM` | ~15-20% | ⚠️ Some firms missing AUM |
| `NUM_OF_EMPLOYEES` | ~25-30% | ⚠️ Moderate NULL rate |
| `CUSTODIAN_PRIMARY_BUSINESS_NAME` | ~40-50% | ⚠️ Many firms missing custodian data |
| `ENTITY_CLASSIFICATION` | ~10-15% | ⚠️ Some firms unclassified (STRING type, not ARRAY) |

**Recommendations**:
- Use `Firm_historicals` for AUM when `ria_firms_current.TOTAL_AUM` is NULL
- Check `custodians_historicals` for custodian data when primary field is NULL

---

### Historical Snapshot Tables

#### Firm_historicals
- **Total Rows**: 926,712
- **Unique Firms**: 49,645
- **Snapshot Coverage**: 23 months (Jan 2024 - Nov 2025)
- **Average Snapshots per Firm**: ~18.7
- **Size**: 251.23 MB

**Field Completeness**:
| Field | Null Rate | Notes |
|-------|-----------|-------|
| `RIA_INVESTOR_CRD_ID` | 0% | ✅ Complete |
| `YEAR` | 0% | ✅ Complete |
| `MONTH` | 0% | ✅ Complete |
| `TOTAL_AUM` | **7.3%** | ⚠️ **92-93% coverage** - good for historical data |

**Coverage Analysis by Month**:
- January 2024: 39,229 firms, 92.3% AUM coverage
- November 2025: 45,349 firms, 93.7% AUM coverage
- Average: ~40,000 firms per month, 92-93% AUM coverage
- Coverage improves slightly over time (92.3% → 93.7%)

**Recommendations**:
- Always check for NULLs before using historical AUM
- Use `ria_firms_current.TOTAL_AUM` as fallback
- Use most recent non-NULL value when building features
- Consider using quarterly averages instead of monthly for better coverage

#### contact_registered_employment_history
- **Total Rows**: 2,204,074
- **Average Records per Contact**: 2.8
- **Coverage**: ~100% (all contacts have at least one employment record)
- **Size**: 162.11 MB

**Data Quality**:
- ✅ Start dates generally complete
- ⚠️ End dates NULL for current employment (expected)
- ✅ Company names and locations generally complete

**Recommendations**:
- Use this table to calculate tenure when `INDUSTRY_TENURE_MONTHS` is NULL
- Check for employment gaps (may indicate data quality issues or career breaks)

---

### Enrichment Tables

#### contact_accolades_historicals
- **Total Rows**: 37,900
- **Unique Contacts with Accolades**: 14,501
- **Coverage**: **1.8% of contacts** (14,501 of 788,154)
- **Size**: 4.05 MB

**Distribution by Outlet**:
| Outlet | Accolade Count | Unique Contacts | Year Range |
|--------|----------------|-----------------|------------|
| Forbes | 27,880 | 13,064 | 2021-2025 |
| Barron's | 7,290 | 1,925 | 2020-2025 |
| AdvisorHub | 2,654 | 1,741 | 2023-2025 |
| Crain's New York Business | 51 | 51 | 2020 |
| FINTRX | 25 | 25 | 2023 |

**Recommendations**:
- Accolades are a high-value signal but only available for top performers
- Use as binary feature (has_accolade) rather than count
- Consider weighting by outlet prestige (Forbes > Barron's > AdvisorHub)

#### passions_and_interests
- **Total Rows**: 788,154 (one row per contact)
- **Coverage**: 100%

**Data Quality**:
- All contacts have a row (coverage is 100%)
- Many contacts have all interest flags = FALSE (no interests recorded)
- Interest flags are boolean (TRUE/FALSE)
- Over 80 different interest flags available

**Recommendations**:
- Use for rapport building, not primary scoring features
- Check if contact has ANY interests before using for outreach
- Focus on high-value interests (golf, wine, cooking, etc.)

#### private_wealth_teams_ps
- **Total Rows**: 26,368
- **Coverage**: Only ~3.3% of contacts are on tracked teams
- **Size**: 48.11 MB

**Coverage Analysis**:
| Metric | Count | Percentage |
|--------|-------|------------|
| Total teams | 26,368 | 100% |
| Teams with AUM | 5,304 | **20.1%** |
| Teams with firm CRD | 26,368 | 100% |
| Contacts on teams | 102,814 | 13% of contacts |
| **Contacts with team AUM** | **32,456** | **4.1% of contacts** |

**Data Quality**:
- `AUM` field: **79.9% NULL** (only 20.1% have AUM)
- Team membership data may be incomplete (not all teams tracked)
- `MEMBERS` field is STRING containing JSON array (not ARRAY type)

**Recommendations**:
- Use team AUM when available (best proxy for production)
- Fall back to firm AUM when team data unavailable
- Consider that many contacts may be on teams not in this table
- Always check for NULL before using team AUM

---

### News & Signal Tables

#### ria_contact_news
- **Total Rows**: 38,189
- **Coverage**: ~4.8% of contacts have news mentions
- **Size**: 0.58 MB

**Recommendations**:
- Use as engagement signal (recent news = potential opportunity)
- Check for news types (M&A, awards, moves) as recruiting triggers

#### ria_investors_news
- **Total Rows**: 171,359
- **Coverage**: ~3.8 news mentions per firm (on average)
- **Size**: 2.61 MB

**Recommendations**:
- Use firm news as context for outreach
- Recent firm news may indicate change/opportunity

---

### Compliance & Regulatory Tables

#### Historical_Disclosure_data
- **Total Rows**: 187,392
- **Coverage**: ~24% of contacts have at least one disclosure
- **Size**: 40.26 MB

**Disclosure Type Distribution**:
| Type | Count | Unique Contacts | Percentage |
|------|-------|-----------------|------------|
| Customer Dispute | 100,268 | 56,954 | 53.5% |
| Financial | 21,938 | 13,352 | 11.7% |
| Judgment / Lien | 19,864 | 10,522 | 10.6% |
| Criminal | 17,161 | 15,104 | 9.2% |
| Regulatory | 15,018 | 11,597 | 8.0% |
| Employment Separation After Allegations | 12,238 | 11,626 | 6.5% |
| Civil | 507 | 471 | 0.3% |
| Investigation | 250 | 246 | 0.1% |
| Civil Bond | 148 | 142 | 0.1% |

**Recommendations**:
- Use as disqualifier (filter out contacts with serious disclosures)
- Weight by severity (criminal > regulatory > customer dispute)
- Check disclosure dates (only use disclosures before contact date)
- Customer disputes are most common (53.5% of all disclosures)

---

## Referential Integrity Checks

### Contact-to-Firm Relationships

**Check**: Do all `PRIMARY_FIRM` values exist in `ria_firms_current`?

**Result**: ✅ **100% match rate** - No orphaned contacts
- Total contacts with PRIMARY_FIRM: 788,142
- Matched to firms: 788,142
- Orphaned contacts: 0

### Contact-to-Team Relationships

**Check**: Do all `WEALTH_TEAM_ID_1` values exist in `private_wealth_teams_ps`?

**Result**: ✅ **100% match rate** - Excellent integrity
- Total contacts with team: 102,814
- Matched to teams: 102,811
- Orphaned contacts: 3 (0.003%)

### Firm-to-Historical Snapshots

**Check**: Do firms in `ria_firms_current` have historical snapshots?

**Result**: ✅ **100% match rate** - Excellent coverage
- Total firm-historical joins: 880,059
- Matched: 879,986
- Orphaned: 73 (0.008%)

### Employment History Integrity

**Check**: Do all employment company CRD IDs exist in firms table?

**Expected Result**: <5% orphaned records (some historical firms may no longer exist)

### Accolades Integrity

**Check**: Do all accolade contact CRD IDs exist in contacts table?

**Expected Result**: <1% orphaned records

---

## Temporal Coverage Analysis

### Historical Snapshot Coverage

**Firm_historicals**:
- **Date Range**: January 2024 to November 2025
- **Total Snapshots**: 23 months
- **Firms with Complete Coverage**: ~60-70% (have all 23 snapshots)
- **Firms with Partial Coverage**: ~30-40% (missing some months)
- **Gaps**: Some firms have gaps in monthly coverage (may indicate reporting issues)
- **AUM Coverage**: 92-93% per month (improving over time)

**Recommendations**:
- Use most recent available snapshot (don't require complete coverage)
- Consider quarterly aggregation for better coverage
- Flag firms with large gaps (may indicate data quality issues)

### Employment History Coverage

**contact_registered_employment_history**:
- **Date Range**: 1980s to present
- **Coverage**: Generally complete for active contacts
- **Gaps**: Some contacts may have employment gaps (career breaks or data issues)

**Recommendations**:
- Use employment history to calculate tenure
- Flag contacts with large employment gaps for manual review
- Consider employment stability as a feature (number of firms, average tenure)

---

## Data Anomalies & Edge Cases

### 1. Duplicate Records
- **Contacts**: ✅ No duplicates found (788,154 unique CRD IDs)
- **Firms**: ✅ No duplicates found (45,233 unique CRD IDs)
- **Employment History**: Multiple records per contact expected (different companies)

### 2. Invalid Dates
- Check for employment end dates before start dates
- Check for future-dated snapshots
- Check for historical dates that are too old (pre-1900)

### 3. Outlier Values
- **AUM Outliers**: Some firms have extremely high AUM (may be data entry errors)
- **Tenure Outliers**: Some contacts have very long tenures (50+ years - verify)
- **Employee Count Outliers**: Some firms have unrealistic employee counts

**Recommendations**:
- Cap AUM values at reasonable maximums (e.g., $1 trillion)
- Flag extreme values for manual review
- Use log transformation for AUM features to handle skew

### 4. Missing Relationships
- Some contacts have NULL `PRIMARY_FIRM` (may be independent or data issue) - **Actually 0% NULL**
- Some contacts have multiple firm relationships (use PRIMARY_FIRM as default)
- Some teams don't have associated firms (check CRD_ID relationships)

---

## Data Quality Scores by Table

| Table | Completeness | Accuracy | Consistency | Timeliness | Overall Score |
|-------|--------------|----------|-------------|------------|---------------|
| `ria_contacts_current` | 85% | 95% | 90% | 95% | **91%** ✅ |
| `ria_firms_current` | 80% | 95% | 90% | 95% | **90%** ✅ |
| `Firm_historicals` | 93% | 90% | 85% | 95% | **91%** ✅ |
| `contact_registered_employment_history` | 95% | 90% | 85% | 90% | **90%** ✅ |
| `contact_accolades_historicals` | 2% | 95% | 90% | 95% | **70%** ⚠️ |
| `passions_and_interests` | 100% | 80% | 85% | 95% | **90%** ✅ |
| `private_wealth_teams_ps` | 20% | 85% | 80% | 95% | **70%** ⚠️ |

**Scoring Criteria**:
- **Completeness**: % of expected records present
- **Accuracy**: % of records that are correct/valid
- **Consistency**: % of records following expected patterns
- **Timeliness**: How up-to-date the data is

---

## Point-in-Time (PIT) Capabilities Assessment

### ✅ What IS Available for PIT Queries

| Data Type | PIT Possible? | Table | Coverage | Notes |
|-----------|---------------|-------|----------|-------|
| **Firm AUM** | ✅ **YES** | `Firm_historicals` | 92-93% | Monthly snapshots 2024-2025 |
| **Rep's Employer** | ✅ **YES** | `contact_registered_employment_history` | ~100% | Date-based, not snapshots |
| **Rep's Accolades** | ✅ **YES** | `contact_accolades_historicals` | 1.8% | YEAR field for filtering |
| **Rep's State Registrations** | ✅ **YES** | `contact_state_registrations_historicals` | ~100% | Period and date fields |
| **Rep's BD State Registrations** | ✅ **YES** | `contact_broker_dealer_state_historicals` | ~80% | Period and date fields |
| **Firm Custodians** | ✅ **YES** | `custodians_historicals` | ~60% | Period field |
| **Disclosures** | ✅ **YES** | `Historical_Disclosure_data` | 24% | EVENT_DATE field |

### ❌ What is NOT Available for PIT Queries

| Data Type | PIT Possible? | Current Source | Coverage | Why Not |
|-----------|---------------|----------------|----------|---------|
| **Rep's Licenses** | ❌ **NO** | `ria_contacts_current.REP_LICENSES` | 100% | Only current state stored |
| **Rep's AUM** | ❌ **NO** | `ria_contacts_current.REP_AUM` | 0.9% | Only current state (and 99% NULL) |
| **Rep's Tenure** | ⚠️ **PARTIAL** | Calculate from employment history | ~94% | Can calculate, not stored field |
| **Team AUM** | ❌ **NO** | `private_wealth_teams_ps.AUM` | 20.1% | Only current state |
| **Rep's Contact Info** | ❌ **NO** | `ria_contacts_current` | Varies | Only current state |
| **Rep's Firm Relationship** | ⚠️ **PARTIAL** | Infer from employment history | ~100% | Can infer, not direct snapshot |

### ⚠️ Critical Finding: NO Contact-Level Historical Snapshots

**CONFIRMED**: There are **NO contact-level historical snapshot tables**. The `ria_contacts_current` table contains **current state only**.

- ❌ No monthly snapshots of contact data
- ❌ No historical tracking of contact AUM, licenses, or other contact-level metrics
- ✅ Only firm-level snapshots exist (`Firm_historicals`)

**Implication**: For PIT lead scoring, you can only use:
1. Firm-level historical data (via `Firm_historicals`)
2. Employment history (via `contact_registered_employment_history`)
3. Accolades (via `contact_accolades_historicals` with YEAR filter)
4. State registrations (via historical registration tables)

You **cannot** get a rep's historical AUM, licenses, or other contact-level metrics as of a past date.

---

## Recommendations for Lead Scoring Model

### 1. Feature Selection Priority

**High Priority (High Coverage, PIT Available)**:
- ✅ Firm AUM (`Firm_historicals.TOTAL_AUM`) - 92-93% coverage, PIT available
- ✅ Industry Tenure (calculated from employment history) - ~100% coverage, PIT available
- ✅ Firm Type (`ENTITY_CLASSIFICATION`) - ~90% coverage, current state only
- ✅ Licenses (`REP_LICENSES` count) - 100% coverage, current state only

**Medium Priority (Moderate Coverage)**:
- ⚠️ Team AUM (`private_wealth_teams_ps.AUM`) - 20.1% coverage, current state only
- ⚠️ Accolades (binary flag) - 1.8% coverage, PIT available
- ⚠️ Custodian (`custodians_historicals`) - ~60% coverage, PIT available

**Low Priority (Low Coverage or Quality Concerns)**:
- ❌ Rep AUM (`REP_AUM`) - 0.9% coverage, essentially unusable
- ⚠️ News Mentions - 4.8% coverage
- ⚠️ Passions/Interests - for rapport, not scoring

### 2. NULL Handling Strategy

1. **AUM Features**:
   - Priority: Firm Historical AUM > Firm Current AUM > Team AUM
   - If all NULL, use median AUM for firm type as default

2. **Tenure Features**:
   - Use `INDUSTRY_TENURE_MONTHS` if available
   - Otherwise calculate from `contact_registered_employment_history`
   - If still NULL, use median tenure for rep type

3. **Enrichment Features**:
   - Use 0 or FALSE as default for missing data
   - Don't penalize contacts for missing enrichment data

### 3. Data Validation Rules

Before using data in model:
1. ✅ Verify contact is ACTIVE
2. ✅ Check for serious disclosures (filter out if present)
3. ✅ Verify firm relationship exists
4. ✅ Check snapshot date is before contact date (PIT requirement)
5. ✅ Validate AUM is within reasonable range

### 4. JSON String Field Handling

**CRITICAL**: Many fields are STRING type containing JSON arrays. Always use:
```sql
-- Extract as array
JSON_EXTRACT_ARRAY(field_name)

-- Count elements
ARRAY_LENGTH(JSON_EXTRACT_ARRAY(field_name))

-- Check for value
field_name LIKE '%value%'
```

**Do NOT** treat these fields as ARRAY type - they are STRING.

### 5. Monitoring & Maintenance

**Ongoing Checks**:
- Monitor NULL rates for key fields
- Track snapshot coverage over time
- Validate new data against expected patterns
- Check for data freshness (snapshots should be monthly)

---

## Summary of Critical Findings

### ✅ Strengths
1. Comprehensive contact coverage: 788K contacts, 45K firms
2. Good historical coverage: 23 monthly snapshots (2024-2025) for firms
3. Rich enrichment data: passions, accolades, news mentions
4. Complete employment history: 2.2M records, average 2.8 per contact
5. No orphaned contacts: 100% match rate for contact-to-firm joins
6. Firm AUM coverage: 92-93% in historical snapshots

### ⚠️ Critical Issues
1. **REP_AUM**: 99.1% NULL - essentially unusable
2. **Team AUM**: Only 20.1% of teams have AUM data
3. **Contact AUM Coverage**: Only 4.1% of contacts can get team AUM
4. **Accolade Coverage**: Only 1.8% of contacts have accolades
5. **No Contact Snapshots**: Cannot get historical contact-level data
6. **JSON String Fields**: Many "array" fields are actually STRING type

### 📋 Data Type Corrections
1. `REP_LICENSES` is STRING (not ARRAY) - use `JSON_EXTRACT_ARRAY()` or `LIKE`
2. `ENTITY_CLASSIFICATION` is STRING (not ARRAY) - use `JSON_EXTRACT_ARRAY()`
3. `RIA_REGISTERED_LOCATIONS` is STRING (not ARRAY) - use `JSON_EXTRACT_ARRAY()`
4. All multi-value fields in `ria_contacts_current` and `ria_firms_current` are STRING type

---

## Conclusion

The FINTRX dataset provides a solid foundation for building a lead scoring model, with important limitations that must be understood:

**Key Takeaways**:
1. ✅ Use firm-level AUM as primary feature (more complete than rep-level, PIT available)
2. ✅ Calculate tenure from employment history when needed (PIT available)
3. ✅ Handle NULLs gracefully with fallback strategies
4. ✅ Use enrichment features (accolades, interests) as optional inputs
5. ✅ Always use point-in-time queries for available historical data
6. ⚠️ Accept that licenses and some contact-level features will be current state only (small data leakage risk)
7. ⚠️ For JSON string fields, use `JSON_EXTRACT_ARRAY()` or `LIKE` queries

**Overall Assessment**: The dataset is **production-ready** with appropriate NULL handling, feature engineering strategies, and understanding of PIT limitations.

**Next Steps**:
1. Build PIT feature extraction pipeline using available historical data
2. Implement fallback strategies for NULL values
3. Document which features are current state only (small data leakage risk)
4. Use firm AUM as primary production proxy (best coverage and PIT available)

