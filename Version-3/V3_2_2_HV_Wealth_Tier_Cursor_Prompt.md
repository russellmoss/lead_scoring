# V3.2.2 Model Update - Add TIER_1F_HV_WEALTH_BLEEDER

## Overview

This update adds a new high-performing tier based on analysis of 266 historical leads showing **12.78% conversion (3.35x lift)**. The tier targets advisors with "High-Value Wealth" titles at firms experiencing advisor losses.

**Model Version:** V3.2.1 → V3.2.2
**Date:** December 23, 2025

---

## New Tier Definition

### TIER_1F_HV_WEALTH_BLEEDER

| Attribute | Value |
|-----------|-------|
| **Name** | TIER_1F_HV_WEALTH_BLEEDER |
| **Description** | High-Value Wealth title holder at bleeding firm |
| **Expected Conversion** | 12.78% |
| **Expected Lift** | 3.35x |
| **Historical Validation** | 266 leads, 34 conversions (2022-2025) |
| **Ranking** | #4 overall (after 1A, 1B, 1E) |

**Criteria:**
1. Has a "High-Value Wealth Title" (see definition below)
2. Firm is bleeding (`firm_net_change_12mo < 0`)
3. Not already assigned to Tier 1A (CFP) or 1B (Series 65 Only)

---

## High-Value Wealth Title Definition

```sql
-- HIGH-VALUE WEALTH TITLE FLAG
-- Combines ownership/seniority signals with "Wealth" focus
-- EXCLUDES "Wealth Management Advisor" (wirehouse title, 0.66x lift)

CASE WHEN (
    -- Wealth Manager variants (exclude wirehouse and junior titles)
    (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
     AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
     AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
     AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSISTANT%')
    -- Director + Wealth
    OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
    -- Senior VP + Wealth (exclude wirehouse)
    OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR (UPPER(c.TITLE_NAME) LIKE '%SVP%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    -- Senior Wealth Advisor
    OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
    -- Founder + Wealth
    OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%FOUNDER%'
    -- Principal + Wealth
    OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRINCIPAL%'
    -- Partner + Wealth (exclude wirehouse)
    OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    -- President + Wealth
    OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRESIDENT%'
    -- Managing Director + Wealth (exclude wirehouse)
    OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
) THEN TRUE ELSE FALSE END as is_hv_wealth_title
```

---

## Files to Update

### 1. 🔴 CRITICAL: `sql/phase_4_v3_tiered_scoring.sql`

**Location:** `C:\Users\russe\Documents\Lead Scoring\Version-3\sql\phase_4_v3_tiered_scoring.sql`

#### Step 1A: Add HV Wealth Title Flag to the `lead_certifications` CTE

Find the `lead_certifications` CTE (around line 69-98). Add the HV Wealth title flag after `has_cfa`:

```sql
-- In the lead_certifications CTE, add this AFTER the has_cfa CASE statement (around line 89-93):

        -- High-Value Wealth Title flag (ownership/seniority + wealth focus)
        -- Added V3.2.2: 266 leads, 12.78% conversion when combined with bleeding firm
        CASE WHEN (
    (UPPER(c.TITLE_NAME) LIKE '%WEALTH MANAGER%' 
     AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%'
     AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSOCIATE%'
     AND UPPER(c.TITLE_NAME) NOT LIKE '%ASSISTANT%')
    OR UPPER(c.TITLE_NAME) LIKE '%DIRECTOR%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%DIRECTOR%'
    OR (UPPER(c.TITLE_NAME) LIKE '%SENIOR VICE%WEALTH%' 
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR (UPPER(c.TITLE_NAME) LIKE '%SVP%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR UPPER(c.TITLE_NAME) LIKE '%SENIOR WEALTH ADVISOR%'
    OR UPPER(c.TITLE_NAME) LIKE '%FOUNDER%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%FOUNDER%'
    OR UPPER(c.TITLE_NAME) LIKE '%PRINCIPAL%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRINCIPAL%'
    OR (UPPER(c.TITLE_NAME) LIKE '%PARTNER%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
    OR UPPER(c.TITLE_NAME) LIKE '%PRESIDENT%WEALTH%'
    OR UPPER(c.TITLE_NAME) LIKE '%WEALTH%PRESIDENT%'
    OR (UPPER(c.TITLE_NAME) LIKE '%MANAGING DIRECTOR%WEALTH%'
        AND UPPER(c.TITLE_NAME) NOT LIKE '%WEALTH MANAGEMENT ADVISOR%')
) THEN TRUE ELSE FALSE END as is_hv_wealth_title,
```

#### Step 1B: Update `leads_with_certs` CTE to Include the New Flag

Find the `leads_with_certs` CTE (around line 101-111). Add the new flag:

```sql
-- In leads_with_certs CTE, add after has_cfa line:
        COALESCE(cert.is_hv_wealth_title, 0) as is_hv_wealth_title
```

#### Step 1C: Add TIER_1F to the Tier Assignment CASE Statement

Find the main tier assignment CASE WHEN block in the `tiered_leads` CTE (starts around line 117). Insert TIER_1F **after TIER_1E** (around line 187) but **before TIER_2A** (around line 189):

```sql
            -- ============================================================
            -- TIER 1F: HV WEALTH TITLE + BLEEDING FIRM (NEW - V3.2.2)
            -- High-Value Wealth title at a firm losing advisors
            -- Expected: 12.78% conversion, 3.35x lift
            -- Historical validation: 266 leads, 34 conversions
            -- ============================================================
            WHEN is_hv_wealth_title = 1
                 AND firm_net_change_12mo < 0      -- Bleeding firm
                 AND is_wirehouse = 0
            THEN 'TIER_1F_HV_WEALTH_BLEEDER'
            
            -- [TIER_2A follows here...]
```

#### Step 1D: Add Tier Display Name

Find the `tier_display` CASE block (around line 228-240). Add after TIER_1E:

```sql
            WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN '🏆 Tier 1F: HV Wealth (Bleeding)'
```

#### Step 1E: Add Expected Conversion Rate

Find the `expected_conversion_rate` CASE block (around line 242-254). Add after TIER_1E:

```sql
            WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 0.1278   -- NEW: 12.78% (n=266)
```

#### Step 1F: Add Expected Lift

Find the `expected_lift` CASE block (around line 256-268). Add after TIER_1E:

```sql
            WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 3.35     -- 12.78% / 3.82%
```

#### Step 1G: Add Priority Rank

Find the `priority_rank` CASE block (around line 270-282). Add after TIER_1E and update TIER_2A+ ranks:

```sql
            WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 6        -- NEW
            WHEN 'TIER_2A_PROVEN_MOVER' THEN 7             -- UPDATED from 6
            WHEN 'TIER_2B_MODERATE_BLEEDER' THEN 8         -- UPDATED from 7
            WHEN 'TIER_3_EXPERIENCED_MOVER' THEN 9         -- UPDATED from 8
            WHEN 'TIER_4_HEAVY_BLEEDER' THEN 10            -- UPDATED from 9
```

#### Step 1H: Add Action Recommended

Find the `action_recommended` CASE block (around line 284-296). Add after TIER_1E:

```sql
            WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN '🔥 High priority - wealth leader at unstable firm'
```

#### Step 1I: Add Tier Explanation

Find the `tier_explanation` CASE block (around line 298-310). Add after TIER_1E:

```sql
            WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 'High-Value Wealth title holder (Wealth Manager, Director, Senior Advisor, Founder/Principal/Partner) at firm losing advisors. This combination of ownership-level title and firm instability historically converts at 12.78% (3.35x baseline). Title indicates book ownership and client relationships.'
```

#### Step 1J: Add is_hv_wealth_title to Output Columns

Find the final SELECT statement (around line 314-350). Add after `has_cfa`:

```sql
    is_hv_wealth_title,
```

#### Step 1K: Update Model Version String

Find the model_version line (around line 348). Update to:

```sql
    'V3.2.2_12232025_HV_WEALTH_TIER' as model_version
```

---

### 2. 🔴 CRITICAL: `sql/phase_4_v3.2_12212025_consolidated.sql`

**Location:** `C:\Users\russe\Documents\Lead Scoring\Version-3\sql\phase_4_v3.2_12212025_consolidated.sql`

Apply the **exact same changes** as Step 1 above to this consolidated version:
- Step 1A: Add `is_hv_wealth_title` flag to `lead_certifications` CTE
- Step 1B: Add flag to `leads_with_certs` CTE
- Step 1C: Add `TIER_1F_HV_WEALTH_BLEEDER` tier assignment
- Step 1D: Add tier_display
- Step 1E: Add expected_conversion_rate
- Step 1F: Add expected_lift  
- Step 1G: Add priority_rank (and update ranks for tiers 2A+)
- Step 1H: Add action_recommended
- Step 1I: Add tier_explanation
- Step 1J: Add `is_hv_wealth_title` to output SELECT
- Step 1K: Update model_version to `'V3.2.2_12232025_HV_WEALTH_TIER'`

**Note:** The consolidated file may have different line numbers. Search for the same CTE/CASE names.

---

### 3. 🔴 CRITICAL: `models/model_registry_v3.json`

**Location:** `C:\Users\russe\Documents\Lead Scoring\Version-3\models\model_registry_v3.json`

Update the JSON file with:

```json
{
  "model_id": "lead-scoring-v3.2.2",
  "model_version": "V3.2.2_12232025_HV_WEALTH_TIER",
  "model_type": "rules-based-tiers",
  "status": "production",
  "created_date": "2025-12-21",
  "updated_date": "2025-12-23",
  "changes_from_v3.2.1": [
    "Added TIER_1F_HV_WEALTH_BLEEDER: High-Value Wealth title holders at bleeding firms",
    "New tier captures advisors with ownership/seniority titles (Founder, Principal, Partner, Director, etc.) combined with 'Wealth' focus",
    "Historical validation: 266 leads, 34 conversions, 12.78% conversion rate, 3.35x lift",
    "Tier ranks #4 overall in performance (after 1A, 1B, 1E)",
    "Added is_hv_wealth_title flag to output schema",
    "Added narrative generation for TIER_1F"
  ],
  "expected_performance": {
    "tier_1a_cfp_lift": "4.30x",
    "tier_1b_series65_lift": "4.31x",
    "tier_1c_small_lift": "3.46x",
    "tier_1d_small_firm_lift": "3.66x",
    "tier_1e_prime_mover_lift": "3.46x",
    "tier_1f_hv_wealth_lift": "3.35x",
    "tier_2_lift": "2.46x",
    "tier_3_lift": "2.55x",
    "tier_4_lift": "3.27x",
    "tier_5_lift": "2.02x"
  },
  "tier_definitions": {
    "TIER_1A_PRIME_MOVER_CFP": {
      "description": "CFP holder (book ownership signal) at bleeding firm - highest conversion potential",
      "expected_conversion_rate": 0.1644,
      "expected_lift": 4.30,
      "criteria": "1-4yr tenure, 5+yr experience, bleeding firm, CFP designation, not wirehouse"
    },
    "TIER_1B_PRIME_MOVER_SERIES65": {
      "description": "Fee-only RIA (Series 65 only) meeting Prime Mover criteria - no broker-dealer ties",
      "expected_conversion_rate": 0.1648,
      "expected_lift": 4.31,
      "criteria": "Standard Tier 1 criteria + Series 65 only (no Series 7)"
    },
    "TIER_1C_PRIME_MOVER_SMALL": {
      "description": "Mid-career advisor at small bleeding firm",
      "expected_conversion_rate": 0.1321,
      "expected_lift": 3.46,
      "criteria": "1-3yr tenure, 5-15yr exp, bleeding firm <=50 reps"
    },
    "TIER_1D_SMALL_FIRM": {
      "description": "Recent joiner at very small firm",
      "expected_conversion_rate": 0.14,
      "expected_lift": 3.66,
      "criteria": "Firm <=10 reps"
    },
    "TIER_1E_PRIME_MOVER": {
      "description": "Mid-career advisor at bleeding firm (base Prime Mover)",
      "expected_conversion_rate": 0.1321,
      "expected_lift": 3.46,
      "criteria": "1-4yr tenure, 5-15yr exp, bleeding firm"
    },
    "TIER_1F_HV_WEALTH_BLEEDER": {
      "description": "High-Value Wealth title holder at bleeding firm - NEW V3.2.2",
      "expected_conversion_rate": 0.1278,
      "expected_lift": 3.35,
      "historical_validation": {
        "leads": 266,
        "conversions": 34,
        "time_period": "2022-2025 (3 years)"
      },
      "criteria": "High-Value Wealth title (Wealth Manager, Director+Wealth, Senior Wealth Advisor, Founder/Principal/Partner+Wealth, etc.) + bleeding firm",
      "title_patterns": [
        "Wealth Manager (not Wealth Management Advisor)",
        "Director + Wealth",
        "Senior VP + Wealth Advisor",
        "Senior Wealth Advisor",
        "Founder + Wealth",
        "Principal + Wealth",
        "Partner + Wealth",
        "President + Wealth",
        "Managing Director + Wealth"
      ],
      "exclusions": [
        "Wealth Management Advisor (wirehouse)",
        "Associate/Assistant variants"
      ]
    },
    "TIER_2_PROVEN_MOVER": {
      "description": "Has changed firms 3+ times - demonstrated willingness to move",
      "expected_conversion_rate": 0.0900,
      "expected_lift": 2.46
    },
    "TIER_3_MODERATE_BLEEDER": {
      "description": "Experienced advisor at firm losing 1-10 reps",
      "expected_conversion_rate": 0.0933,
      "expected_lift": 2.55
    },
    "TIER_4_EXPERIENCED_MOVER": {
      "description": "Veteran (20+ yrs) who recently moved",
      "expected_conversion_rate": 0.1197,
      "expected_lift": 3.27
    },
    "TIER_5_HEAVY_BLEEDER": {
      "description": "Experienced advisor at firm in crisis (losing 10+ reps)",
      "expected_conversion_rate": 0.0738,
      "expected_lift": 2.02
    },
    "STANDARD": {
      "description": "All other leads",
      "expected_conversion_rate": 0.0382,
      "expected_lift": 1.0
    }
  }
}
```

---

### 4. 🔴 CRITICAL: `January_2026_Lead_List_Query_V3.2.sql`

**Location:** `C:\Users\russe\Documents\Lead Scoring\Version-3\January_2026_Lead_List_Query_V3.2.sql`

#### Step 4A: Add TIER_1F Quota Section

Find the tier quota sections (Section O or similar). Add a new section for TIER_1F:

```sql
-- =============================================================================
-- TIER 1F: HV WEALTH BLEEDER QUOTA
-- Target: 50 leads (or adjust based on availability)
-- Expected conversion: 12.78%
-- =============================================================================
tier_1f_quota AS (
    SELECT *
    FROM scored_leads
    WHERE score_tier = 'TIER_1F_HV_WEALTH_BLEEDER'
    ORDER BY 
        ABS(firm_net_change_12mo) DESC,  -- Prioritize more distressed firms
        industry_tenure_months DESC       -- Then by experience
    LIMIT 50
),
```

#### Step 4B: Add to Final UNION ALL

Add TIER_1F to the final UNION ALL that combines all tier quotas:

```sql
SELECT * FROM tier_1f_quota
UNION ALL
```

#### Step 4C: Update Tier Priority Ranking

If there's an ORDER BY for tier priority, ensure TIER_1F is ranked appropriately:

```sql
ORDER BY 
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2
        WHEN 'TIER_1C_PRIME_MOVER_SMALL' THEN 3
        WHEN 'TIER_1D_SMALL_FIRM' THEN 4
        WHEN 'TIER_1E_PRIME_MOVER' THEN 5
        WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 6  -- NEW
        WHEN 'TIER_2_PROVEN_MOVER' THEN 7
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 8
        WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 9
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 10
        ELSE 99
    END
```

---

### 5. 🟡 IMPORTANT: `VERSION_3_MODEL_REPORT.md`

**Location:** `C:\Users\russe\Documents\Lead Scoring\Version-3\VERSION_3_MODEL_REPORT.md`

Add a new section documenting TIER_1F:

```markdown
## V3.2.2 Update: TIER_1F_HV_WEALTH_BLEEDER (December 23, 2025)

### Overview

Added a new tier targeting advisors with "High-Value Wealth" titles at firms experiencing advisor losses. This tier was identified through analysis of 6,503 leads with wealth-related titles, finding that the combination of ownership-level titles and firm distress creates exceptional conversion rates.

### Tier Definition

**TIER_1F_HV_WEALTH_BLEEDER**
- **Description:** High-Value Wealth title holder at bleeding firm
- **Expected Conversion Rate:** 12.78%
- **Expected Lift:** 3.35x
- **Historical Validation:** 266 leads, 34 conversions (2022-2025)
- **Ranking:** #4 overall (after 1A, 1B, 1E)

### Criteria

1. **High-Value Wealth Title** (any of the following):
   - Wealth Manager (excluding "Wealth Management Advisor")
   - Director + Wealth combinations
   - Senior VP + Wealth Advisor
   - Senior Wealth Advisor
   - Founder + Wealth combinations
   - Principal + Wealth combinations
   - Partner + Wealth combinations (excluding wirehouse)
   - President + Wealth combinations
   - Managing Director + Wealth combinations

2. **Bleeding Firm:** `firm_net_change_12mo < 0`

3. **Not already assigned** to Tier 1A (CFP) or Tier 1B (Series 65 Only)

### Exclusions

- "Wealth Management Advisor" (wirehouse title, 0.66x lift)
- Associate/Assistant variants
- Any title containing "Wealth Management Advisor"

### Analysis Summary

| Metric | Value |
|--------|-------|
| Total HV Wealth leads analyzed | 6,503 |
| HV Wealth + Bleeding Firm leads | 266 |
| Conversions | 34 |
| Conversion Rate | 12.78% |
| Lift vs Baseline | 3.35x |

### Top Performing Title Combinations

| Title | Leads | Conversion Rate | Lift |
|-------|-------|-----------------|------|
| Founder & Senior Wealth Advisor | 10 | 20.00% | 5.24x |
| Partner, Senior Wealth Manager | 11 | 18.18% | 4.76x |
| Principal & Wealth Manager | 14 | 14.29% | 3.74x |
| Wealth Manager | 715 | 6.99% | 1.83x |

### Rationale

1. **Ownership signal:** Titles with "Founder", "Principal", "Partner", "Director" indicate book ownership
2. **Wealth focus:** "Wealth Manager" vs "Financial Advisor" suggests fee-based, not commission-based practice
3. **Firm distress multiplier:** Bleeding firm creates urgency/opportunity
4. **Excludes wirehouses:** "Wealth Management Advisor" is a wirehouse title with poor conversion
```

---

## Deployment to BigQuery via MCP

After making all code changes, use your BigQuery MCP connection to deploy the updated model.

### MCP Deployment Commands

#### Step 1: Connect to BigQuery
Ensure your BigQuery MCP server is connected. If not already configured, you may need to run:
```
Connect to your BigQuery MCP server for savvy-gtm-analytics project
```

#### Step 2: Execute the Updated Tier Scoring Query
Run the entire contents of the updated `sql/phase_4_v3_tiered_scoring.sql` file.

**The query should:**
- Create/replace table: `savvy-gtm-analytics.ml_features.lead_scores_v3`
- Include the new `is_hv_wealth_title` column
- Include the new `TIER_1F_HV_WEALTH_BLEEDER` tier assignments
- Update model_version to `V3.2.2_12232025_HV_WEALTH_TIER`

#### Step 3: Validate TIER_1F Assignment
After deployment, run this validation query via MCP:

```sql
SELECT 
    score_tier,
    COUNT(*) as lead_count,
    ROUND(AVG(expected_conversion_rate) * 100, 2) as expected_rate_pct,
    ROUND(AVG(expected_lift), 2) as expected_lift
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
WHERE score_tier LIKE 'TIER_1%'
GROUP BY score_tier
ORDER BY 
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2
        WHEN 'TIER_1C_PRIME_MOVER_SMALL' THEN 3
        WHEN 'TIER_1D_SMALL_FIRM' THEN 4
        WHEN 'TIER_1E_PRIME_MOVER' THEN 5
        WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 6
    END;
```

**Expected:** TIER_1F_HV_WEALTH_BLEEDER should appear with ~200-300 leads.

### Step 3: Verify Narrative Generation

```sql
SELECT 
    advisor_crd,
    first_name,
    last_name,
    score_tier,
    score_narrative
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
WHERE score_tier = 'TIER_1F_HV_WEALTH_BLEEDER'
LIMIT 10;
```

**Expected:** Each lead should have a narrative mentioning their title type and firm bleeding status.

### Step 4: Check HV Wealth Flag

```sql
SELECT 
    is_hv_wealth_title,
    COUNT(*) as lead_count
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
GROUP BY is_hv_wealth_title;
```

**Expected:** ~3,000-4,000 leads with `is_hv_wealth_title = TRUE`

---

## Validation Queries

### Query 1: Tier Distribution After Update

```sql
SELECT 
    score_tier,
    COUNT(*) as leads,
    ROUND(AVG(expected_conversion_rate) * 100, 2) as expected_rate,
    ROUND(AVG(expected_lift), 2) as lift
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
GROUP BY score_tier
ORDER BY expected_rate DESC;
```

### Query 2: TIER_1F Sample Leads

```sql
SELECT 
    advisor_crd,
    first_name,
    last_name,
    firm_name,
    firm_net_change_12mo,
    is_hv_wealth_title,
    score_tier,
    expected_conversion_rate,
    score_narrative
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
WHERE score_tier = 'TIER_1F_HV_WEALTH_BLEEDER'
ORDER BY ABS(firm_net_change_12mo) DESC
LIMIT 20;
```

### Query 3: Verify No Overlap with 1A/1B

```sql
-- Ensure TIER_1F doesn't capture leads that should be 1A or 1B
SELECT 
    score_tier,
    SUM(CASE WHEN has_cfp = TRUE THEN 1 ELSE 0 END) as cfp_count,
    SUM(CASE WHEN has_series_65_only = TRUE THEN 1 ELSE 0 END) as series65_count
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
WHERE score_tier = 'TIER_1F_HV_WEALTH_BLEEDER'
GROUP BY score_tier;
```

**Expected:** CFP and Series 65 counts should be 0 (those would go to 1A/1B instead)

---

## Rollback Plan

If issues are discovered:

1. Restore backup of `sql/phase_4_v3_tiered_scoring.sql`
2. Re-run the original query in BigQuery
3. Revert `model_registry_v3.json` to previous version
4. Verify TIER_1F is no longer being assigned

---

## Summary of Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `phase_4_v3_tiered_scoring.sql` | Add tier logic | TIER_1F criteria, conversion rate, lift, narrative |
| `phase_4_v3.2_12212025_consolidated.sql` | Add tier logic | Same as above |
| `model_registry_v3.json` | Add metadata | Document TIER_1F definition and performance |
| `January_2026_Lead_List_Query_V3.2.sql` | Add quota | Add TIER_1F quota section |
| `VERSION_3_MODEL_REPORT.md` | Add documentation | Document V3.2.2 update |
| BigQuery | Deploy | Execute updated scoring query |

---

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Tier 1 sub-tiers | 5 (1A-1E) | 6 (1A-1F) |
| New tier leads | - | ~266 |
| New tier expected conversions | - | ~34 (12.78%) |
| Model version | V3.2.1 | V3.2.2 |

---

*Prompt Version: 1.0*  
*Created: December 23, 2025*  
*Based on: High-Value Wealth Titles Analysis (266 leads, 12.78% conversion)*
