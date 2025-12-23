# V3.2.1 Title Exclusion Update - Cursor Deployment Prompt

## Overview

We need to add **data-driven title exclusion logic** to the V3.2 lead scoring model. Analysis of 72,000+ historical leads revealed that certain job titles have near-zero conversion rates and should be excluded from lead list generation.

**Expected Impact:** Removes ~8.5% of leads (204 of 2,400 in January list) that historically convert at 0-0.5%.

---

## Data Analysis Findings (Summary)

### Keywords with Near-Zero Conversion
| Keyword | Historical Conversion | Lift vs Baseline | Action |
|---------|----------------------|------------------|--------|
| OPERATIONS | 0.0% | 0.00x | STRONGLY EXCLUDE |
| SOLUTIONS | 0.17% | 0.10x | STRONGLY EXCLUDE |
| FIRST (as in "First Vice President") | 0.39% | 0.23x | STRONGLY EXCLUDE |
| SALES | 0.57% | 0.34x | EXCLUDE |
| ASSOCIATE | 0.70% | 0.42x | EXCLUDE |
| SPECIALIST | 0.74% | 0.44x | EXCLUDE |

### Specific Zero-Converting Titles (n >= 30)
| Title | Leads | Conversion |
|-------|-------|------------|
| Financial Solutions Advisor | 476 | 0% |
| Senior Vice President, Wealth Management | 224 | 0% |
| First Vice President, Wealth Management Advisor | 142 | 0% |
| Associate Advisor | 140 | 0% |
| Paraplanner | 87 | 0% |
| Chief Operating Officer | 73 | 0% |

---

## Files to Update

Based on `PRODUCTION_MODEL_UPDATE_CHECKLIST.md`, update these files in order:

### 1. 🔴 CRITICAL: `sql/phase_4_v3_tiered_scoring.sql`
### 2. 🔴 CRITICAL: `sql/generate_lead_list_v3.2.1.sql`  
### 3. 🔴 CRITICAL: `models/model_registry_v3.json`
### 4. 🟡 IMPORTANT: `January_2026_Lead_List_Query_V3.2.sql` (if regenerating list)

---

## Implementation Instructions

### Step 1: Update `sql/phase_4_v3_tiered_scoring.sql`

Find the CTE where leads are joined to FINTRX contact data (likely `lead_base`, `contacted_leads`, or similar early CTE). Add the title exclusion logic to the WHERE clause.

**Add this exclusion block:**

```sql
-- =============================================================================
-- TITLE EXCLUSIONS (V3.2.1 Update - Data-Driven)
-- Based on analysis of 72,000+ historical leads
-- Removes ~8.5% of leads with near-zero historical conversion
-- =============================================================================
AND NOT (
    -- HARD EXCLUSIONS: 0% conversion titles with n >= 30
    
    -- "Financial Solutions Advisor" = Bank of America retail bankers (476 leads, 0% conv)
    UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTIONS ADVISOR%'
    OR UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTION ADVISOR%'
    
    -- Support/Junior roles (0% conversion)
    OR UPPER(c.TITLE_NAME) LIKE '%PARAPLANNER%'
    OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE ADVISOR%'
    OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE WEALTH ADVISOR%'
    
    -- Operations roles (0% conversion across 297 leads with "OPERATIONS" keyword)
    OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS MANAGER%'
    OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR OF OPERATIONS%'
    OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS SPECIALIST%'
    OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS ASSOCIATE%'
    OR UPPER(c.TITLE_NAME) LIKE '%CHIEF OPERATING OFFICER%'
    
    -- "First Vice President" variants (all 0% conversion - junior wirehouse titles)
    OR UPPER(c.TITLE_NAME) LIKE '%FIRST VICE PRESIDENT%'
    
    -- Wholesaler titles (sell to advisors, not clients)
    OR UPPER(c.TITLE_NAME) LIKE '%WHOLESALER%'
    OR UPPER(c.TITLE_NAME) LIKE '%INTERNAL WHOLESALER%'
    OR UPPER(c.TITLE_NAME) LIKE '%EXTERNAL WHOLESALER%'
    OR UPPER(c.TITLE_NAME) LIKE '%INTERNAL SALES%'
    OR UPPER(c.TITLE_NAME) LIKE '%EXTERNAL SALES%'
    
    -- Compliance/Regulatory roles (0.76% conversion, 0.44x lift)
    OR UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE OFFICER%'
    OR UPPER(c.TITLE_NAME) LIKE '%CHIEF COMPLIANCE%'
    OR UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE MANAGER%'
    OR UPPER(c.TITLE_NAME) LIKE '%SUPERVISION%'
    
    -- Administrative/Support roles
    OR UPPER(c.TITLE_NAME) LIKE '%REGISTERED ASSISTANT%'
    OR UPPER(c.TITLE_NAME) LIKE '%CLIENT SERVICE ASSOCIATE%'
    OR UPPER(c.TITLE_NAME) LIKE '%SALES ASSISTANT%'
    OR UPPER(c.TITLE_NAME) LIKE '%ADMINISTRATIVE ASSISTANT%'
    OR UPPER(c.TITLE_NAME) LIKE '%BRANCH OFFICE ADMINISTRATOR%'
    
    -- Analyst roles (0.93% conversion, 0.56x lift) - exclude non-investment analysts
    OR (UPPER(c.TITLE_NAME) LIKE '%ANALYST%' 
        AND UPPER(c.TITLE_NAME) NOT LIKE '%INVESTMENT ANALYST%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%FINANCIAL ANALYST%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%PORTFOLIO ANALYST%')
    
    -- "Senior Vice President, Financial Advisor" specifically (551 leads, 0.54% conv)
    -- These are wirehouse employees who cannot move their book
    OR UPPER(c.TITLE_NAME) = 'SENIOR VICE PRESIDENT, FINANCIAL ADVISOR'
    OR UPPER(c.TITLE_NAME) = 'SENIOR VICE PRESIDENT, WEALTH MANAGEMENT ADVISOR'
    OR UPPER(c.TITLE_NAME) = 'SENIOR VICE PRESIDENT, SENIOR FINANCIAL ADVISOR'
    OR UPPER(c.TITLE_NAME) = 'VICE PRESIDENT, SENIOR FINANCIAL ADVISOR'
)
```

**Important:** 
- The column `c.TITLE_NAME` should reference the FINTRX contacts table alias
- If the query uses a different alias (e.g., `contacts`, `fintrx`, `ria_contacts`), update accordingly
- This filter should be added in the earliest CTE where FINTRX data is joined

---

### Step 2: Update `sql/generate_lead_list_v3.2.1.sql`

Find the `base_contacts` or `base_prospects` CTE (around line 100-200 based on the uploaded query structure). Add the same exclusion logic.

The structure should look like:

```sql
base_contacts AS (
    SELECT 
        c.RIA_CONTACT_CRD_ID as crd,
        c.FIRST_NAME as first_name,
        c.LAST_NAME as last_name,
        -- ... other fields
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    WHERE 
        -- Existing filters...
        c.EMAIL IS NOT NULL
        AND c.PRIMARY_FIRM IS NOT NULL
        
        -- ADD TITLE EXCLUSIONS HERE (same block as above)
        AND NOT (
            UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTIONS ADVISOR%'
            OR UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTION ADVISOR%'
            -- ... (full exclusion block from Step 1)
        )
        
        -- Existing wirehouse exclusions...
        AND NOT EXISTS (
            SELECT 1 FROM excluded_firms ef 
            WHERE UPPER(c.PRIMARY_FIRM_NAME) LIKE ef.firm_pattern
        )
),
```

---

### Step 3: Update `models/model_registry_v3.json`

Add the following to the model registry:

1. Update `model_version` to `"V3.2.1"`
2. Update `updated_date` to current date
3. Add to `changes_from_v3.2` array:

```json
{
  "model_version": "V3.2.1",
  "updated_date": "2025-12-23",
  "changes_from_v3.2": [
    "Added data-driven title exclusion logic based on analysis of 72,000+ historical leads",
    "Excludes ~8.5% of leads with near-zero historical conversion rates",
    "Key exclusions: Financial Solutions Advisor (BofA retail), First Vice President variants (wirehouse junior), Operations roles, Paraplanner/Associate Advisor (support roles), Wholesaler titles, Compliance roles",
    "Expected impact: Improved lead quality by removing 0% conversion title categories"
  ],
  "title_exclusions": {
    "enabled": true,
    "exclusion_categories": [
      {
        "category": "RETAIL_BANK_ADVISOR",
        "patterns": ["FINANCIAL SOLUTIONS ADVISOR", "FINANCIAL SOLUTION ADVISOR"],
        "reason": "Bank of America retail bankers, 0% conversion (n=476)"
      },
      {
        "category": "WIREHOUSE_JUNIOR",
        "patterns": ["FIRST VICE PRESIDENT%"],
        "reason": "Junior wirehouse titles (MS/UBS/Merrill), 0% conversion"
      },
      {
        "category": "OPERATIONS",
        "patterns": ["OPERATIONS MANAGER", "CHIEF OPERATING OFFICER", "DIRECTOR OF OPERATIONS"],
        "reason": "Back office roles, 0% conversion"
      },
      {
        "category": "SUPPORT_ROLES",
        "patterns": ["PARAPLANNER", "ASSOCIATE ADVISOR", "REGISTERED ASSISTANT"],
        "reason": "Support roles without client books, 0% conversion"
      },
      {
        "category": "WHOLESALER",
        "patterns": ["WHOLESALER", "INTERNAL SALES", "EXTERNAL SALES"],
        "reason": "Sell to advisors not clients"
      },
      {
        "category": "COMPLIANCE",
        "patterns": ["COMPLIANCE OFFICER", "CHIEF COMPLIANCE"],
        "reason": "Regulatory roles, 0.76% conversion (0.44x lift)"
      },
      {
        "category": "WIREHOUSE_SVP",
        "patterns": ["SENIOR VICE PRESIDENT, FINANCIAL ADVISOR", "SENIOR VICE PRESIDENT, WEALTH MANAGEMENT ADVISOR"],
        "reason": "Wirehouse employees who cannot move book, 0.54% conversion (0.33x lift)"
      }
    ],
    "estimated_exclusion_rate": "8.5%",
    "validation_date": "2025-12-23",
    "validation_sample_size": 72055
  }
}
```

---

### Step 4: Update Version String in SQL Files

In both SQL files, update the model version string:

**Find:**
```sql
'V3.2.1_12212025' as model_version
```

**Replace with:**
```sql
'V3.2.1_12232025_TITLE_EXCLUSIONS' as model_version
```

Or similar version identifier that indicates the title exclusion update.

---

## Validation Steps

After making changes, run these validation queries:

### 1. Count excluded leads in existing January list
```sql
SELECT 
    COUNT(*) as total_leads,
    SUM(CASE WHEN 
        UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTIONS ADVISOR%'
        OR UPPER(c.TITLE_NAME) LIKE '%PARAPLANNER%'
        OR UPPER(c.TITLE_NAME) LIKE '%FIRST VICE PRESIDENT%'
        OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE ADVISOR%'
        OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS%'
        OR UPPER(c.TITLE_NAME) LIKE '%WHOLESALER%'
        OR UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE%'
        THEN 1 ELSE 0 END) as would_be_excluded,
    ROUND(SUM(CASE WHEN 
        UPPER(c.TITLE_NAME) LIKE '%FINANCIAL SOLUTIONS ADVISOR%'
        OR UPPER(c.TITLE_NAME) LIKE '%PARAPLANNER%'
        OR UPPER(c.TITLE_NAME) LIKE '%FIRST VICE PRESIDENT%'
        OR UPPER(c.TITLE_NAME) LIKE '%ASSOCIATE ADVISOR%'
        OR UPPER(c.TITLE_NAME) LIKE '%OPERATIONS%'
        OR UPPER(c.TITLE_NAME) LIKE '%WHOLESALER%'
        OR UPPER(c.TITLE_NAME) LIKE '%COMPLIANCE%'
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_excluded
FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON jl.advisor_crd = c.RIA_CONTACT_CRD_ID;
```

**Expected:** ~8.5% excluded (204 of 2,400)

### 2. Verify no high-converting titles are excluded
```sql
-- Check that we're not accidentally excluding good titles
SELECT 
    c.TITLE_NAME,
    COUNT(*) as count_in_list
FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list` jl
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    ON jl.advisor_crd = c.RIA_CONTACT_CRD_ID
WHERE 
    UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%'
    OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%'
    OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%'
GROUP BY c.TITLE_NAME
ORDER BY count_in_list DESC
LIMIT 20;
```

**Expected:** These high-converting titles should NOT be excluded

---

## Rollback Plan

If issues are discovered:

1. Revert to backup copies of SQL files
2. Re-run `phase_4_v3_tiered_scoring.sql` without title exclusions
3. Regenerate lead list from original query

---

## Notes

- The exclusion logic uses `UPPER()` for case-insensitive matching
- Pattern matching uses `LIKE '%PATTERN%'` for flexibility
- Some exclusions use exact match (`= 'TITLE'`) for precision
- The `AND NOT (...)` structure ensures all conditions are properly grouped
- Title data comes from `ria_contacts_current.TITLE_NAME` field

---

## Summary of Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `phase_4_v3_tiered_scoring.sql` | Add WHERE clause | Title exclusion filter in base CTE |
| `generate_lead_list_v3.2.1.sql` | Add WHERE clause | Title exclusion filter in base_contacts CTE |
| `model_registry_v3.json` | Add metadata | Document title exclusions and rationale |
| Version strings | Update | Change to V3.2.1_TITLE_EXCLUSIONS |

---

*Prompt Version: 1.0*  
*Created: 2025-12-23*  
*Based on: Title Analysis of 72,055 historical leads*
