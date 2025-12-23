# Broker Protocol Members Table - Data Structure Report

**Table**: `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`  
**Report Date**: December 22, 2025  
**Data Source**: Broker Protocol Member Firms Excel File (scraped from JSHeld.com)

---

## 📊 Executive Summary

- **Total Rows**: 2,587 firms
- **Unique Firm Names**: 2,551
- **Unique CRD IDs**: 2,327
- **Firms with CRD ID**: 2,483 (95.98%)
- **Firms without CRD ID**: 104 (4.02%)
- **Date Joined**: 2,581 firms have join dates (99.8%)
- **Date Withdrawn**: 0 firms have withdrawal dates in structured field
- **Current Members**: 2,587 (100% marked as current)
- **Scrape Runs**: 8 total runs, latest on 2025-12-22

---

## 🗂️ Table Schema

### Complete Column List (24 columns)

| Column Name | Data Type | Required | Nullable | Description |
|------------|-----------|----------|----------|-------------|
| `broker_protocol_firm_name` | STRING | ✅ Yes | No | Cleaned firm name from Broker Protocol |
| `firm_crd_id` | INTEGER | ❌ No | Yes | FINTRX CRD ID (matched firm identifier) |
| `fintrx_firm_name` | STRING | ❌ No | Yes | Matched FINTRX firm name |
| `former_names` | STRING | ❌ No | Yes | Former names (f/k/a) from FINTRX |
| `dbas` | STRING | ❌ No | Yes | Doing business as names from FINTRX |
| `has_name_change` | BOOLEAN | ❌ No | Yes | Default: FALSE |
| `date_joined` | DATE | ❌ No | Yes | **Parsed join date (YYYY-MM-DD format)** |
| `date_withdrawn` | DATE | ❌ No | Yes | **Parsed withdrawal date (YYYY-MM-DD format)** |
| `is_current_member` | BOOLEAN | ❌ No | Yes | Default: TRUE |
| `joinder_qualifications` | STRING | ❌ No | Yes | Full joinder notes text |
| `date_notes_cleaned` | STRING | ❌ No | Yes | Cleaned date notes (parsed text) |
| `date_notes_raw` | STRING | ❌ No | Yes | Raw date notes from Excel |
| `firm_name_raw` | STRING | ❌ No | Yes | Raw firm name from Excel |
| `match_confidence` | FLOAT | ❌ No | Yes | Matching confidence score (0-1) |
| `match_method` | STRING | ❌ No | Yes | Matching method: exact, base_name, fuzzy, unmatched |
| `needs_manual_review` | BOOLEAN | ❌ No | Yes | Default: FALSE |
| `manual_review_notes` | STRING | ❌ No | Yes | Manual review notes |
| `manual_review_date` | TIMESTAMP | ❌ No | Yes | When manual review was done |
| `manual_review_by` | STRING | ❌ No | Yes | Who did manual review |
| `scrape_timestamp` | TIMESTAMP | ✅ Yes | No | When data was scraped |
| `scrape_run_id` | STRING | ❌ No | Yes | Unique scrape run identifier |
| `first_seen_date` | DATE | ❌ No | Yes | First time firm appeared in scrapes |
| `last_seen_date` | DATE | ❌ No | Yes | Last time firm appeared in scrapes |
| `last_updated` | TIMESTAMP | ❌ No | Yes | Default: CURRENT_TIMESTAMP() |

---

## 🆔 Firm CRD ID Analysis

### Overview

**CRD IDs** (Central Registration Depository) are unique identifiers for financial firms registered with FINRA. They are used to match Broker Protocol firms to FINTRX database records.

### Statistics

- **Total Firms with CRD ID**: 2,483 (95.98%)
- **Total Firms without CRD ID**: 104 (4.02%)
- **Unique CRD IDs**: 2,327
- **Duplicate CRD IDs**: 156 firms share CRD IDs (some firms have multiple entries)

### CRD ID Distribution

**Most Common CRD IDs** (firms appearing multiple times):
- CRD **170655**: 4 firms
- CRD **135788**: 3 firms
- CRD **291925**: 3 firms
- CRD **151495**: 3 firms
- CRD **133802**: 3 firms
- CRD **27913**: 3 firms
- CRD **6694**: 3 firms (2 unique names)
- CRD **168452**: 3 firms
- CRD **124004**: 3 firms
- CRD **335596**: 3 firms

**Note**: Multiple firms sharing the same CRD ID typically indicates:
- Parent/subsidiary relationships
- Name changes (same firm, different names)
- Data quality issues requiring manual review

### Matching Methods by CRD Status

| Match Method | Total Firms | With CRD ID | Without CRD ID |
|-------------|-------------|-------------|----------------|
| **Exact** | 960 | 960 (100%) | 0 (0%) |
| **Base Name** | 247 | 247 (100%) | 0 (0%) |
| **Fuzzy** | 1,239 | 1,239 (100%) | 0 (0%) |
| **Unmatched** | 141 | 37 (26.2%) | 104 (73.8%) |

**Key Insight**: All matched firms (exact, base_name, fuzzy) have CRD IDs. Only unmatched firms lack CRD IDs, which is expected.

---

## 📅 Date Joined Analysis

### Overview

The `date_joined` field contains the **parsed join date** when a firm joined the Broker Protocol. Dates are stored in **DATE format (YYYY-MM-DD)** in BigQuery.

### Statistics

- **Firms with Join Date**: 2,581 (99.8%)
- **Firms Missing Join Date**: 6 (0.2%)
- **Earliest Join Date**: 2001-01-19
- **Latest Join Date**: 2031-12-14 ⚠️ (Future date - data quality issue)

### Date Range Analysis

**Join Dates by Year** (Top Years):

| Year | Firm Count | Notes |
|------|------------|-------|
| 2017 | 150 | Peak year |
| 2016 | 151 | Peak year |
| 2009 | 128 | High activity |
| 2022 | 133 | Recent high |
| 2023 | 103 | Recent activity |
| 2024 | 79 | Recent activity |
| 2025 | 59 | Current year |
| 2031 | 32 | ⚠️ **Future dates** |
| 2030 | 72 | ⚠️ **Future dates** |
| 2029 | 49 | ⚠️ **Future dates** |
| 2028 | 62 | ⚠️ **Future dates** |
| 2027 | 62 | ⚠️ **Future dates** |
| 2026 | 62 | ⚠️ **Future dates** |

**⚠️ Data Quality Issue**: There are **409 firms** with join dates in the future (2026-2031). This appears to be a parsing error where dates were misinterpreted. For example:
- Date notes say "2019-01-01" but parsed date is "2001-01-19" (year/month swapped)
- Date notes say "2024-02-01" but parsed date is "2001-02-24" (year/month swapped)

### Most Common Join Dates

| Date Joined | Firm Count | Notes |
|-------------|------------|-------|
| 2009-06-11 | 10 | Multiple firms joined same day |
| 2016-01-11 | 9 | Multiple firms joined same day |
| 2025-09-09 | 6 | Recent join date |
| 2001-10-04 | 6 | Early join date |
| 2017-09-09 | 6 | Peak period |

### Date Structure Details

**Date Format in BigQuery**:
- **Type**: `DATE`
- **Format**: `YYYY-MM-DD` (ISO 8601)
- **Example**: `2009-06-11` (June 11, 2009)
- **Storage**: Dates are stored as integers (days since epoch)

**Date Parsing Sources**:
1. **Primary**: Parsed from `date_notes_raw` field (Excel source)
2. **Fallback**: Extracted from `joinder_qualifications` text
3. **Cleaned**: Stored in `date_notes_cleaned` for reference

**Date Parsing Examples**:

| Raw Text | Parsed Date | Notes |
|----------|-------------|-------|
| "June 11, 2009" | 2009-06-11 | ✅ Correct |
| "2019-01-01 00:00:00" | 2001-01-19 | ❌ **Parsing error** (year/month swapped) |
| "2024-02-01 00:00:00" | 2001-02-24 | ❌ **Parsing error** (year/month swapped) |
| "November 7, 2013\nWithdrew as Member\n(Effective March 16, 2015)" | 2013-11-07 | ✅ Correct (join date) |

**⚠️ Known Parsing Issues**:
- **Year/Month Swapping**: Dates in format "YYYY-MM-DD" are sometimes parsed as "YYYY-DD-MM" or "MM-DD-YYYY"
- **Future Dates**: 409 firms have join dates in 2026-2031, likely due to parsing errors
- **Very Old Dates**: Some firms have join dates in 2001, but `date_notes_cleaned` shows later dates (e.g., "2019-01-01")

### Example: Date Joined with Issues

```sql
-- Example of date parsing issues
SELECT 
  broker_protocol_firm_name,
  date_joined,
  date_notes_cleaned,
  date_notes_raw
FROM broker_protocol_members
WHERE date_joined < '2004-01-01' OR date_joined > CURRENT_DATE()
LIMIT 5;
```

**Results**:
- **Compass Securities Corporation**: `date_joined` = 2001-01-19, but `date_notes_cleaned` = "2019-01-01 00:00:00"
- **Promethium Advisors, LLC**: `date_joined` = 2001-02-24, but `date_notes_cleaned` = "2024-02-01 00:00:00"
- **Skyline Advisors**: `date_joined` = 2001-03-17, but `date_notes_cleaned` = "2017-03-01 00:00:00"

**Recommendation**: Review and fix date parsing logic for dates in "YYYY-MM-DD" format.

---

## 🚪 Date Withdrawn Analysis

### Overview

The `date_withdrawn` field contains the **parsed withdrawal date** when a firm withdrew from the Broker Protocol. Dates are stored in **DATE format (YYYY-MM-DD)** in BigQuery.

### Statistics

- **Firms with Withdrawal Date**: **0** (0%)
- **Firms without Withdrawal Date**: 2,587 (100%)
- **Firms Mentioning Withdrawal in Notes**: ~20 firms (found in `date_notes_cleaned`)

### Key Finding: Withdrawal Dates Not Parsed

**⚠️ Critical Issue**: Despite **20+ firms** mentioning withdrawals in their `date_notes_cleaned` field, **NONE** have withdrawal dates parsed into the `date_withdrawn` field.

### Examples of Withdrawal Mentions

Firms that mention withdrawal in notes but have `date_withdrawn = NULL`:

| Firm Name | Date Joined | Withdrawal Mentioned | `date_withdrawn` |
|-----------|-------------|---------------------|------------------|
| Fusion Family Wealth, LLC | 2013-11-07 | "Withdrew as Member (Effective March 16, 2015)" | ❌ NULL |
| Planning Solutions Group, LLC | 2012-08-07 | "Withdrew as Member (effective June 21, 2013)" | ❌ NULL |
| Capital Strategies Investment Group, LLC | 2009-06-01 | "Withdrew as Member (Effective August 14, 2025)" | ❌ NULL |
| Grove Point Advisors, LLC. | 2023-02-24 | "Withdrew as Member (effective August 16, 2025)" | ❌ NULL |
| Palisade Capital Management, LLC | 2019-09-03 | "Withdrew as a member Effective November 10, 2025" | ❌ NULL |
| SVB Wealth LLC | 2019-10-10 | "Withdrew as Member (effective April 23, 2023)" | ❌ NULL |
| AFA Financial Group, LLC | 2009-03-09 | "Withdrew as Member (Notice Provided June 24, 2010)" | ❌ NULL |
| CONCERT Capital Management, Inc. | 2012-01-13 | "Withdrew as Member (Notice Provided July 20, 2015)" | ❌ NULL |
| Mt. Eden Investment Advisors, LLC | 2010-03-08 | "Withdrew as Member (Notice Provided May 24, 2011)" | ❌ NULL |
| Barlow Wealth Partners, LLC | 2023-04-21 | "Withdrew as a Member June 15, 2023" | ❌ NULL |

### Withdrawal Date Patterns in Notes

**Common Patterns Found**:
1. **"Withdrew as Member (Effective [DATE])"** - Most common
2. **"Withdrew as Member (Notice Provided [DATE])"** - Notice date (not effective date)
3. **"Withdrew as a member Effective [DATE]"** - Alternative format
4. **"Withdrew as Member\n(effective [DATE])"** - Multi-line format

**Example Text**:
```
November 7, 2013
Withdrew as Member 
(Effective March 16, 2015)
```

**Recommendation**: 
1. **Enhance date parser** to extract withdrawal dates from `date_notes_cleaned`
2. **Update `date_withdrawn` field** for firms with withdrawal mentions
3. **Set `is_current_member = FALSE`** for firms with withdrawal dates
4. **Create validation query** to identify firms with withdrawal mentions but NULL `date_withdrawn`

### Withdrawal Date Extraction Logic Needed

```python
# Pseudo-code for withdrawal date extraction
patterns = [
    r"Withdrew.*?\(Effective\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\)",
    r"Withdrew.*?\(effective\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\)",
    r"Withdrew.*?Effective\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
    r"Withdrew.*?\(Notice Provided\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\)",
    # Add more patterns...
]
```

---

## 📋 Data Quality Issues Summary

### 1. Date Parsing Errors

**Issue**: Year/month swapping in date parsing
- **Affected**: ~409 firms with future dates (2026-2031)
- **Root Cause**: Dates in "YYYY-MM-DD" format parsed incorrectly
- **Impact**: Historical analysis will be inaccurate
- **Priority**: 🔴 **HIGH** - Affects data integrity

### 2. Missing Withdrawal Dates

**Issue**: Withdrawal dates not parsed from notes
- **Affected**: ~20 firms with withdrawal mentions
- **Root Cause**: Parser doesn't extract withdrawal dates
- **Impact**: Cannot identify former members accurately
- **Priority**: 🟡 **MEDIUM** - Affects membership status

### 3. Duplicate CRD IDs

**Issue**: Multiple firms share same CRD ID
- **Affected**: 156 firms (6% of total)
- **Root Cause**: Parent/subsidiary relationships or name changes
- **Impact**: May need manual review to determine relationships
- **Priority**: 🟢 **LOW** - Expected behavior, but needs documentation

### 4. Missing CRD IDs

**Issue**: 104 firms (4%) don't have CRD IDs
- **Affected**: All unmatched firms + 37 matched firms
- **Root Cause**: Firms not in FINTRX database or matching failed
- **Impact**: Cannot link to FINTRX data
- **Priority**: 🟡 **MEDIUM** - Limits data enrichment

### 5. All Firms Marked as Current

**Issue**: All 2,587 firms have `is_current_member = TRUE`
- **Affected**: 100% of firms
- **Root Cause**: Withdrawal dates not parsed, so status not updated
- **Impact**: Cannot distinguish current vs. former members
- **Priority**: 🔴 **HIGH** - Critical for membership tracking

---

## 🔍 Sample Data Examples

### Example 1: Well-Parsed Firm

```json
{
  "broker_protocol_firm_name": "Brighton Wealth Management, Inc.",
  "firm_crd_id": 148457,
  "fintrx_firm_name": "Brighton Wealth Management, Inc.",
  "date_joined": "2009-01-23",
  "date_withdrawn": null,
  "is_current_member": true,
  "match_method": "exact",
  "match_confidence": 1.0,
  "date_notes_cleaned": "January 23, 2009\nresubmitted joinder September 17, 2024"
}
```

**Analysis**: ✅ Perfect match, correct date parsing, high confidence.

### Example 2: Date Parsing Error

```json
{
  "broker_protocol_firm_name": "Compass Securities Corporation",
  "firm_crd_id": 16168,
  "date_joined": "2001-01-19",
  "date_notes_cleaned": "2019-01-01 00:00:00",
  "date_notes_raw": "2019-01-01 00:00:00"
}
```

**Analysis**: ❌ Date parsing error - `date_joined` (2001-01-19) doesn't match `date_notes_cleaned` (2019-01-01). Year/month likely swapped.

### Example 3: Withdrawal Mentioned but Not Parsed

```json
{
  "broker_protocol_firm_name": "Fusion Family Wealth, LLC",
  "firm_crd_id": 168254,
  "date_joined": "2013-11-07",
  "date_withdrawn": null,
  "is_current_member": true,
  "date_notes_cleaned": "November 7, 2013\nWithdrew as Member \n(Effective March 16, 2015)"
}
```

**Analysis**: ❌ Withdrawal mentioned in notes but `date_withdrawn` is NULL. Should be `2015-03-16` and `is_current_member` should be `FALSE`.

### Example 4: Unmatched Firm

```json
{
  "broker_protocol_firm_name": "Ameriprise Financial Services, LLC* *See specific qualifications...",
  "firm_crd_id": null,
  "fintrx_firm_name": null,
  "match_method": "unmatched",
  "match_confidence": null,
  "needs_manual_review": true
}
```

**Analysis**: ⚠️ Firm not matched to FINTRX. Requires manual review.

---

## 📊 Data Distribution Summary

### Match Method Distribution

| Match Method | Count | Percentage | Avg Confidence |
|-------------|-------|------------|----------------|
| **Fuzzy** | 1,239 | 47.9% | 0.835 |
| **Exact** | 960 | 37.1% | 1.000 |
| **Base Name** | 247 | 9.5% | 0.850 |
| **Unmatched** | 141 | 5.5% | null |

### Membership Status

- **Current Members**: 2,587 (100%) ⚠️ *All marked as current, but ~20 have withdrawal mentions*
- **Former Members**: 0 (0%) ⚠️ *Should be ~20 based on withdrawal mentions*

### Date Joined Distribution

- **2001-2004**: 230 firms (8.9%) - Early adopters
- **2005-2009**: 421 firms (16.3%) - Growth period
- **2010-2014**: 458 firms (17.7%) - Peak growth
- **2015-2019**: 586 firms (22.6%) - Peak period
- **2020-2024**: 385 firms (14.9%) - Recent activity
- **2025+**: 501 firms (19.4%) ⚠️ *Includes future dates (parsing errors)*

---

## 🎯 Recommendations

### Immediate Actions (High Priority)

1. **Fix Date Parsing Logic**
   - Review and correct year/month swapping issue
   - Re-parse all dates with corrected logic
   - Validate dates are within reasonable range (2001-2025)

2. **Extract Withdrawal Dates**
   - Implement withdrawal date extraction from `date_notes_cleaned`
   - Update `date_withdrawn` field for ~20 firms
   - Set `is_current_member = FALSE` for withdrawn firms

3. **Data Validation Query**
   ```sql
   -- Find firms with withdrawal mentions but NULL date_withdrawn
   SELECT 
     broker_protocol_firm_name,
     date_joined,
     date_notes_cleaned
   FROM broker_protocol_members
   WHERE date_notes_cleaned LIKE '%Withdrew%'
     AND date_withdrawn IS NULL;
   ```

### Medium Priority

4. **Review Future Dates**
   - Identify all firms with `date_joined > CURRENT_DATE()`
   - Cross-reference with `date_notes_cleaned` to find correct dates
   - Update dates manually or fix parser

5. **Document CRD ID Relationships**
   - Review firms sharing CRD IDs
   - Document parent/subsidiary relationships
   - Add notes to `manual_review_notes` field

### Low Priority

6. **Improve Matching for Unmatched Firms**
   - Review 141 unmatched firms
   - Add manual matches for important firms
   - Update matching algorithm if needed

---

## 📝 SQL Queries for Analysis

### Find Firms with Future Join Dates

```sql
SELECT 
  broker_protocol_firm_name,
  date_joined,
  date_notes_cleaned,
  date_notes_raw
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
WHERE date_joined > CURRENT_DATE()
ORDER BY date_joined
LIMIT 50;
```

### Find Firms with Withdrawal Mentions

```sql
SELECT 
  broker_protocol_firm_name,
  firm_crd_id,
  date_joined,
  date_withdrawn,
  is_current_member,
  date_notes_cleaned
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
WHERE date_notes_cleaned LIKE '%Withdrew%' 
   OR date_notes_cleaned LIKE '%withdrawn%'
ORDER BY date_joined;
```

### CRD ID Statistics

```sql
SELECT 
  COUNT(*) as total_firms,
  COUNT(firm_crd_id) as with_crd,
  COUNT(*) - COUNT(firm_crd_id) as without_crd,
  COUNT(DISTINCT firm_crd_id) as unique_crds,
  ROUND(COUNT(firm_crd_id) * 100.0 / COUNT(*), 2) as pct_with_crd
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`;
```

### Join Dates by Year

```sql
SELECT 
  EXTRACT(YEAR FROM date_joined) as join_year,
  COUNT(*) as firm_count
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
WHERE date_joined IS NOT NULL
GROUP BY join_year
ORDER BY join_year DESC;
```

---

## 📌 Key Takeaways

1. **CRD IDs**: 96% of firms have CRD IDs, enabling FINTRX matching
2. **Date Joined**: 99.8% have join dates, but ~409 have parsing errors (future dates)
3. **Date Withdrawn**: **0% parsed** - critical gap, ~20 firms mention withdrawals in notes
4. **Data Quality**: Overall good, but date parsing needs improvement
5. **Matching**: 94.5% match rate (exact + base_name + fuzzy)
6. **Membership Status**: All marked as current, but should reflect withdrawals

---

**Report Generated**: December 22, 2025  
**Data Source**: `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`  
**Total Rows Analyzed**: 2,587

