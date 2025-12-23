# Enterprise Targets Query - Validation & Results Summary

**Query File:** `enterprise-targets.sql`  
**Date:** December 23, 2025  
**Purpose:** Identify "Colorado Wealth Group Look-Alike" independent RIAs for Enterprise & ECI opportunities

---

## Query Overview

This query implements the "Look-Alike" strategy to identify independent RIAs that match the Colorado Wealth Group profile:
- **AUM Range:** $200M - $600M
- **Structure:** Independent RIA (must file their own ADV)
- **Custodian:** Fidelity or Charles Schwab
- **Team Size:** 5-25 employees (prioritizing ≤10 reps)
- **HNW Focus:** >50% of AUM from high net worth individuals
- **Ownership:** Founder-led with verified ownership (>5%)
- **Active Allocation:** Uses Exchange-Traded Equity Securities

---

## Validation Results

### Phase 1: Firm Identification

**Total Qualified Firms:** 1,054 independent RIAs matching basic criteria

| Metric | Value |
|--------|-------|
| **Fidelity Firms** | 249 |
| **Schwab Firms** | 905 |
| **Average AUM** | $371.5M |
| **Average Employees** | 8.17 |
| **Average HNW %** | 75.56% |

**Criteria Applied:**
- ✅ AUM: $200M - $600M
- ✅ Entity Classification: Contains "Independent RIA"
- ✅ Custodian: Fidelity or Charles Schwab
- ✅ Employee Count: 5-25 employees
- ✅ HNW AUM: >50% of total AUM
- ✅ Active Allocation: Uses Exchange-Traded Equity Securities

### Phase 2: Owner Identification

**Sample Results (Top 20):**

| Firm Name | AUM | Employees | Owner | Title | Ownership % | Match Score | Custodian |
|-----------|-----|-----------|-------|-------|-------------|-------------|-----------|
| Buckley Wealth Management | $583M | 5 | Brian Buckley | Managing Partner | 25-50% | High | Fidelity |
| Family Office Research | $581M | 5 | Scott Freund | Founder & President | 75%+ | High | Fidelity |
| Morangie Management | $578M | 7 | Geraldine Mcmanus | Co-Founder | 25-50% | High | Fidelity |
| Presilium Private Wealth | $554M | 7 | Jerry Davidse | CEO | 75%+ | High | Fidelity |
| Waterway Wealth Management | $553M | 10 | Daniel Michalk | Founder & Owner | 75%+ | High | Fidelity |

---

## Query Logic Breakdown

### 1. Firm Filters (Phase 1)

```sql
WHERE f.TOTAL_AUM BETWEEN 200000000 AND 600000000
  AND f.ACTIVE = TRUE
  AND f.ENTITY_CLASSIFICATION LIKE '%Independent RIA%'
  AND (
      f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%FIDELITY%'
      OR f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%SCHWAB%'
      OR f.CUSTODIAN_PRIMARY_BUSINESS_NAME LIKE '%CHARLES SCHWAB%'
  )
  AND f.NUM_OF_EMPLOYEES BETWEEN 5 AND 25
  AND SAFE_DIVIDE(f.AMT_OF_AUM_HIGH_NET_WORTH_INDIVIDUALS, f.TOTAL_AUM) > 0.50
  AND f.INVESTMENTS_UTILIZED LIKE '%Exchange-Traded Equities Securities%'
```

### 2. Owner Title Patterns (Phase 2)

**Included Titles:**
- Founder (all variants)
- CEO
- President
- Principal
- Partner (excluding "Associate Partner")
- Managing Director
- Director + Wealth

**Excluded Titles:**
- COO (unless also Partner)
- CCO (unless also Partner)
- Operations
- Compliance (unless also Partner)
- Associate
- Assistant
- Paraplanner

### 3. Ownership Verification

**Included:**
- Ownership percentage >5% (excludes "No Ownership" and "less than 5%")
- Founders/CEOs/Presidents even if ownership data is missing

**Ownership Percentage Mapping:**
- "75% or more" → 75
- "50% but less than 75%" → 62.5
- "25% but less than 50%" → 37.5
- "10% but less than 25%" → 17.5
- "5% but less than 10%" → 7.5

### 4. Smart Producing Advisor Filter

**Included:**
- `PRODUCING_ADVISOR = TRUE`
- `PRODUCING_ADVISOR = FALSE` BUT title is Founder/CEO/President/Principal/Managing Partner

This ensures we don't miss founders who may be mislabeled in FINTRX data.

### 5. CWG Match Score Calculation

**High Match:**
- Employees ≤10
- HNW AUM % ≥70%
- Active Producing Reps ≤10
- Ownership % ≥25%

**Med Match:**
- Employees ≤15
- HNW AUM % ≥50%
- Ownership % ≥10%

**Low Match:** Excluded from final results

### 6. Sorting Logic

1. **Custodian Priority:** Fidelity → Both → Schwab → Other
2. **AUM:** Descending
3. **Ownership %:** Descending

---

## Output Columns

### Firm Information
- `firm_name` - Legal name of the RIA
- `firm_crd` - CRD number
- `firm_aum` - Total assets under management
- `discretionary_aum` - Discretionary AUM
- `non_discretionary_aum` - Non-discretionary AUM
- `firm_aum_yoy_pct` - Year-over-year AUM growth
- `firm_aum_3yoy_pct` - 3-year AUM growth
- `firm_aum_5yoy_pct` - 5-year AUM growth

### Headcount
- `total_employees` - Total employee count
- `advisory_employees` - Employees performing investment advisory functions
- `active_producing_reps` - Count of active producing advisors

### Custodian
- `primary_custodian` - Fidelity, Schwab, Both, or Other
- `custodian_details` - Full custodian name(s)

### Owner/Founder Information
- `owner_first_name` - First name
- `owner_last_name` - Last name
- `owner_full_name` - Full name (concatenated)
- `owner_title` - Job title
- `ownership_percentage` - Ownership percentage (text)
- `ownership_pct_numeric` - Ownership percentage (numeric for sorting)
- `owner_crd` - Contact CRD number

### Contact Information
- `owner_email` - Primary email
- `additional_email` - Secondary email
- `mobile_phone_number` - Mobile phone
- `office_phone_number` - Office phone
- `linkedin_profile_url` - LinkedIn profile
- `owner_fintrx_url` - FINTRX profile URL

### Professional Details
- `producing_advisor` - Boolean flag
- `industry_tenure_months` - Months in industry
- `owner_firm_start_date` - Start date at firm
- `rep_licenses` - Licenses held
- `contact_bio` - Professional bio
- `has_certification` - CFP/CFA flag
- `investment_committee_member` - Boolean
- `contact_roles` - Roles array
- `university_names` - Education
- `accolades` - Awards/recognition

### Location
- `owner_city` - Owner's city
- `owner_state` - Owner's state
- `firm_city` - Firm's main office city
- `firm_state` - Firm's main office state
- `main_office_address_1` - Street address
- `main_office_address_2` - Suite/unit
- `zip_code` - ZIP code
- `firm_phone` - Firm phone number

### Firm Characteristics
- `hnw_aum_pct` - HNW AUM percentage
- `entity_classification` - Entity type
- `client_base` - Client types
- `fee_structure` - Fee types
- `total_accounts` - Total account count
- `total_discretionary_accounts` - Discretionary account count
- `average_account_size` - Average account size
- `investments_utilized` - Investment types
- `capital_allocator` - Capital allocator flag
- `active_esg_investor` - ESG investor flag
- `tamp_and_tech_used` - Technology platforms
- `team_page` - Team page URL

### Match Score
- `cwg_match_score` - High, Med, or Low

---

## Key Insights

1. **Market Size:** 1,054 qualified firms in the $200M-$600M range
2. **Custodian Distribution:** 76% use Schwab, 24% use Fidelity
3. **Average Profile:** $371M AUM, 8 employees, 75.6% HNW focus
4. **High Match Potential:** Many firms match the CWG profile closely

---

## Usage Instructions

1. **Run the Query:** Execute `enterprise-targets.sql` in BigQuery
2. **Review Results:** Results are pre-sorted by custodian (Fidelity first) and AUM
3. **Filter by Match Score:** Use `cwg_match_score` to prioritize High matches
4. **Export:** Export results to CSV/Excel for outreach

---

## Next Steps

1. **Validate Sample:** Review top 20-50 results manually
2. **Enrich Data:** Add LinkedIn/Salesforce enrichment
3. **Prioritize Outreach:** Focus on "High" match scores first
4. **Track Results:** Monitor conversion rates by match score

---

**Query Status:** ✅ Validated and Ready for Production Use

