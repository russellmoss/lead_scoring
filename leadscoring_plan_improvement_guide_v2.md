# Lead Scoring Plan v3.1 - Grade & Improvement Guide (v2)

## For Cursor.ai Agent Execution

**Document:** `C:\Users\russe\Documents\Lead Scoring\Version-3\leadscoring_plan.md`  
**Graded:** December 21, 2024  
**Revision:** v2 - Incorporates ChatGPT feedback + NUM_OF_EMPLOYEES exploration

---

## Overall Grade: **C+ (73/100)** → Target: **A (92/100)**

### Score Breakdown

| Category | Weight | Current | Target | Key Issue |
|----------|--------|---------|--------|-----------|
| **Accuracy** | 25% | 60/100 | 95/100 | Conflicting tier definitions |
| **Completeness** | 20% | 85/100 | 95/100 | Missing SQL, validation code bugs |
| **Consistency** | 25% | 55/100 | 95/100 | Old vs new tiers, contact_date naming |
| **Actionability** | 15% | 80/100 | 90/100 | BigQuery execution gaps |
| **Maintainability** | 15% | 85/100 | 90/100 | Good logging system |

---

## Part 1: Critical Issues (Must Fix Before Agent Execution)

### 🔴 Issue 1.1: Conflicting Tier Definitions

**Locations:** Lines 77-83 vs Lines 10509-10515

The document has TWO completely different tier systems:

| Section | Tier 1 Definition | Lift |
|---------|-------------------|------|
| Executive Summary (correct) | 1-4yr tenure + 5-15yr exp + not wirehouse | 3.40x |
| Quick Reference (WRONG) | Small (≤10) + 4-10yr tenure | 2.55x |

**Agent Impact:** An agent implementing from Quick Reference would get **50% worse results**.

**Fix:** See Step 1 below.

---

### 🔴 Issue 1.2: BigQuery `OPTIONS(location=...)` on Tables (Invalid SQL)

**Location:** Multiple SQL snippets throughout

**Problem:** The plan correctly states that location is a DATASET property, but then includes SQL like:
```sql
CREATE OR REPLACE TABLE ... OPTIONS(location='northamerica-northeast2') AS ...
```

This is **invalid BigQuery syntax** and will cause agent failures.

**Fix:** Remove ALL table-level `OPTIONS(location=...)` clauses. Ensure agents are instructed to:
1. Verify `ml_features` dataset exists in Toronto
2. Create it if needed: `CREATE SCHEMA IF NOT EXISTS ml_features OPTIONS(location='northamerica-northeast2')`
3. Never use location options on individual tables

---

### 🔴 Issue 1.3: `contact_date` vs `contacted_date` Inconsistency

**Locations:** Throughout document

The plan mandates `contacted_date` but uses `contact_date` in several places:
- Some PIT feature SQL uses `contact_date`
- Batch scoring schema references both

**Agent Impact:** Agents will create mismatched schemas, leading to JOIN failures.

**Fix:** Global search & replace:
```
Find: contact_date
Replace: contacted_date
```
Then manually verify each change makes sense in context.

---

### 🔴 Issue 1.4: Snapshot Validation Code Bug

**Location:** `validate_snapshot_integrity()` function

**Problems:**
1. References `FROM snapshot_validation` but CTE is named `virtual_snapshot_validation`
2. Checks `validation['valid_snapshot_pct']` but field is `valid_virtual_snapshot_pct`

**Fix:** Use this corrected version:
```python
def validate_snapshot_integrity(client):
    """Validate virtual snapshot methodology integrity."""
    query = """
    WITH virtual_snapshot_validation AS (
        SELECT
            lead_id,
            contacted_date,
            pit_month,
            CASE 
                WHEN pit_month <= contacted_date THEN 1 
                ELSE 0 
            END as valid_snapshot
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
        WHERE pit_month IS NOT NULL
    )
    SELECT
        COUNT(*) as total_rows,
        SUM(valid_snapshot) as valid_rows,
        ROUND(SUM(valid_snapshot) / COUNT(*) * 100, 2) as valid_virtual_snapshot_pct
    FROM virtual_snapshot_validation
    """
    result = client.query(query).to_dataframe().iloc[0]
    
    if result['valid_virtual_snapshot_pct'] < 100:
        raise ValueError(f"PIT leakage detected: {100 - result['valid_virtual_snapshot_pct']:.2f}% of rows have future data")
    
    return result
```

---

### 🔴 Issue 1.5: V3 Rules vs ML Scoring Confusion

**Problem:** The plan describes V3 as **rules-based SQL tiers** but also includes:
- Python/XGBoost batch scoring code
- Cloud Function with ML feature vectors
- BQML model training

**Agent Impact:** Agents may start wiring ML infrastructure when you want rules-only.

**Fix:** Add a clear decision block at the top:

```markdown
## 🎯 Production Decision: Rules-Only (V3.1)

**CONFIRMED:** Production uses rules-based tier assignment, NOT XGBoost ML.

| Approach | Status | Use Case |
|----------|--------|----------|
| **V3.1 Rules** | ✅ PRODUCTION | Daily scoring, Salesforce sync |
| XGBoost ML | 📦 ARCHIVED | Benchmarking only |
| BQML | 📦 ARCHIVED | Quick validation only |

Agents should SKIP any ML-related code sections unless explicitly requested.
```

---

### 🔴 Issue 1.6: Bogus Percentile Calculation

**Location:** Cloud Function scoring example

**Problem:**
```python
pd.Series([score]).rank(pct=True)  # Single value = always ~100%
```

This is mathematically meaningless for a single score.

**Fix:** Either:
1. Remove percentile from real-time scoring, OR
2. Use a stored calibration table:
```python
# Load daily score distribution
calibration = load_calibration_table()  # Pre-computed quantiles
percentile = np.searchsorted(calibration['quantiles'], score) / 100
```

---

### 🟡 Issue 1.7: BigQuery Job Location in Python

**Problem:** Even with datasets in Toronto, Python jobs can fail without explicit location.

**Fix:** Add to all BigQuery client instantiation:

---

### 🟡 Issue 1.8: Firm_historicals Lag Behavior - No Canonical Rule

**Location:** Multiple PIT feature sections

**Problem:** The plan notes Firm_historicals has ~1 month lag, but doesn't specify a single rule:
- Is snapshot cutoff `contacted_date - 1 month` always?
- Or `<= contacted_date` with fallback to most recent?

**Agent Impact:** Different phases may use different logic, causing feature inconsistency.

**Fix:** Add this canonical rule to Phase 1:
```markdown
### Firm_historicals Snapshot Rule (CANONICAL)

**Rule:** Always use the most recent snapshot BEFORE or ON contacted_date:

```sql
-- Get firm metrics as of contacted_date
SELECT f.*
FROM `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals` f
WHERE DATE(YEAR, MONTH, 1) <= DATE_TRUNC(contacted_date, MONTH)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY RIA_INVESTOR_CRD_ID 
    ORDER BY YEAR DESC, MONTH DESC
) = 1
```

**Rationale:** This handles the 1-month lag by using whatever was most recently published.
**All phases MUST use this pattern** - no variations allowed.
```

---

### 🟡 Issue 1.9: Pre-Execution Permission Check Missing

**Problem:** The plan assumes the agent has all necessary permissions. If it doesn't, the agent will spiral trying "fixes."

**Fix:** Add this checklist to Phase 0.0:

```markdown
### Pre-Execution Permission Verification

Before ANY BigQuery execution, verify the executing identity has:

| Permission | Required For | Check Query |
|------------|--------------|-------------|
| `bigquery.datasets.get` | Read source datasets | `SELECT schema_name FROM INFORMATION_SCHEMA.SCHEMATA` |
| `bigquery.tables.create` | Create feature tables | Try creating a test table |
| `bigquery.jobs.create` | Run queries | Any query will test this |
| `bigquery.datasets.create` | Create ml_features if missing | `CREATE SCHEMA IF NOT EXISTS ml_features` |

**If using service account:** Verify the service account email has BigQuery Data Editor role on `ml_features` dataset.

**Agent instruction:** If ANY permission check fails, STOP and report. Do not attempt workarounds.
```

---

### 🟡 Issue 1.10: Scheduled Query Location Not Specified

**Problem:** If using BigQuery Scheduled Queries, the job location must be Toronto.

**Fix:** Add to Phase 7 (Production Deployment):

```markdown
### Scheduled Query Configuration

When creating scheduled queries:

```sql
-- In BigQuery Console or via API, ensure:
-- Location: northamerica-northeast2 (Toronto)
-- Dataset: ml_features
-- Schedule: Daily at 6 AM EST

-- Example API call includes location:
{
  "location": "northamerica-northeast2",
  "scheduleTime": "06:00",
  "query": "CALL ml_features.score_leads_daily()"
}
```

**CRITICAL:** Scheduled queries created in the wrong region will fail with cross-region errors.
```
```python
from google.cloud import bigquery

# ALWAYS specify location for Toronto region
client = bigquery.Client(
    project='savvy-gtm-analytics',
    location='northamerica-northeast2'  # <-- REQUIRED
)
```

Add this note to the BigQuery Contract section:
```markdown
### Python Client Configuration

**CRITICAL:** Every BigQuery job must specify `location='northamerica-northeast2'`:

```python
client = bigquery.Client(
    project='savvy-gtm-analytics',
    location='northamerica-northeast2'
)
```

Without this, cross-region errors will occur even if datasets are in Toronto.
```

---

## Part 2: Consistency Issues (High Priority)

### 🟡 Issue 2.1: Old Tier Names Throughout Document

**Problem:** ~300+ references to deprecated tier names:
- "Platinum" (149 occurrences)
- "Gold" (23 occurrences)
- "Danger Zone" (67 occurrences)
- "Small firm ≤10" (34 occurrences)

**Fix:** See Step 10 for global search & replace instructions.

---

### 🟡 Issue 2.2: Salesforce Fields Use Old Tier Codes

**Location:** Lines 10500-10505

**Current (Wrong):**
```markdown
| `Lead_Score_Tier__c` | Picklist | Tier code (1_PLATINUM, 2_DANGER_ZONE, etc.) |
```

**Fix:** Update to match validated tiers (see Step 2).

---

### 🟡 Issue 2.3: Narrative Example Uses Invalidated Criteria

**Location:** Lines 10534-10538

The example promotes "small firm (8 advisors)" as a positive factor, but small firms convert **below baseline (0.96x)**.

**Fix:** Update narrative example (see Step 3).

---

## Part 3: Firm Size Signal - Analysis Complete ✅

### Background

We explored whether `NUM_OF_EMPLOYEES` from `ria_firms_current` could replace our calculated `firm_rep_count` (which has only 8.5% coverage).

### ACTUAL Results (December 2024)

#### Coverage: WORSE Than Expected

| Metric | Expected | Actual | Verdict |
|--------|----------|--------|---------|
| NUM_OF_EMPLOYEES coverage | ~75% | **5.85%** | ❌ Nearly useless |
| Leads with data | ~30,000 | **2,307** | ❌ Too sparse |

#### Signal: Exists But Too Weak For Tiers

| Firm Size | Leads | Conv % | Lift | Verdict |
|-----------|-------|--------|------|---------|
| Small (1-10) | 175 | 12.0% | **1.27x** | ✓ Above baseline |
| **Medium (11-50)** | 200 | **15.5%** | **1.64x** | 🎯 Best segment |
| Large (51-200) | 222 | 10.36% | 1.10x | ○ Neutral |
| Very Large (201-1000) | 443 | 5.42% | **0.57x** | ❌ **AVOID** |
| Enterprise (1000+) | 1,267 | 9.39% | 0.99x | ○ Baseline |

#### Quartile Analysis (Confirms Pattern)

| Quartile | Employee Range | Leads | Conv % | Lift |
|----------|----------------|-------|--------|------|
| Q1 (Smallest) | 0-177 | 577 | 12.13% | 1.28x |
| Q2 | 177-2,375 | 577 | 10.05% | 1.06x |
| Q3 | 2,375-8,717 | 577 | 7.28% | 0.77x |
| Q4 (Largest) | 8,717-37,893 | 576 | 8.33% | 0.88x |

#### Correlation Analysis

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Leads with both measures | 2,304 | Small sample |
| Employee-to-rep ratio | 21.2:1 | Includes all staff |
| Correlation | 0.57 | Moderate - related but different signals |

### 🔴 CRITICAL DISCOVERY: Original "Small Firm = Bad" Was WRONG

| Measure | Small Firm Definition | Lift | What We Thought |
|---------|----------------------|------|-----------------|
| Calculated rep_count | ≤10 reps | **0.96x** | "Small firms convert poorly" |
| NUM_OF_EMPLOYEES | 1-10 employees | **1.27x** | "Small firms convert WELL" |

**Root Cause:** When `firm_rep_count = 0`, it means **"unknown"** not **"small"**. 

We were penalizing firms we couldn't track in FINTRX employment history, NOT actually small firms. The 91.5% with firm_rep_count=0 were unknown-size firms, and they converted at baseline (not below).

### Decision: DO NOT Add to V3.2 Tiers

| Criterion | Required | Actual | Pass? |
|-----------|----------|--------|-------|
| Coverage ≥ 50% | Yes | 5.85% | ❌ FAIL |
| Lift ≥ 2.0x | Yes | 1.64x max | ❌ FAIL |
| Volume ≥ 500 | Yes | 200 (best bucket) | ❌ FAIL |

### Update Required: Decision Log Addition

**Add this entry to the leadscoring_plan.md Decision Log:**

```markdown
### Firm Size Signal - Explored & Rejected (December 2024)

**Hypothesis:** NUM_OF_EMPLOYEES could replace low-coverage rep_count calculation

**Analysis:** Ran exploration on 39,448 leads

**Findings:**
1. Coverage only 5.85% (expected ~75%) - data too sparse
2. Best segment (Medium 11-50) = 1.64x lift - below 2.0x tier threshold
3. Very Large firms (201-1000) = 0.57x - strong NEGATIVE signal
4. Original "small firm = bad" finding was a DATA ARTIFACT, not a real signal

**Decision:** Do NOT add to V3.2 tiers

**Rationale:** Coverage too low, lift too weak, volume too small

**Insight Gained:** The original "small firm ≤10" rule was WRONG because:
- 91.5% of leads had firm_rep_count = 0 (unknown, not small)
- Actual small firms (1-10 employees) convert at 1.27x (ABOVE baseline)
- We were penalizing "firms we can't track" not "small firms"
```

### Update Required: Deprecation Notice Clarification

Update the "small firm" deprecation entry to:

```markdown
| "Small firm ≤10" | ❌ INVALIDATED | Rule DROPPED - was measuring "unknown firms" not "small firms" |
```

### Potential V3.3 Consideration: Very Large Firm Exclusion

The data suggests firms with 201-1000 employees convert at only **0.57x** (worst segment):

| Firm Size | Lift | Possible Action |
|-----------|------|-----------------|
| Very Large (201-1000 emp) | **0.57x** | Consider EXCLUDING |

This may overlap with regional broker-dealers or large RIAs with "golden handcuffs" dynamics similar to wirehouses.

**Future exploration:** Check if Very Large firms overlap with wirehouse exclusion list.

---

## Part 4: Step-by-Step Improvement Instructions

### Pre-Execution Checklist

Before making changes:

1. [ ] Run dataset location verification query
2. [ ] Confirm `ml_features` dataset exists in Toronto
3. [ ] Read Decision Log (lines 97-176) - this is the TRUTH
4. [ ] Identify all Quick Reference occurrences (they're WRONG)

---

### Step 1: Fix Quick Reference Tier Table (CRITICAL)

**Location:** Lines 10507-10515

**Replace entire section with:**

```markdown
### Tier Quick Reference (V3.1 Validated)

| Priority | Tier | Criteria | Lift | Volume |
|----------|------|----------|------|--------|
| 🥇 **1** | **Prime Movers** | 1-4yr tenure + 5-15yr exp + firm instability + Not Wirehouse | **3.40x** | ~194 |
| 🥈 **2** | **Moderate Bleeders** | Net change -10 to -1 + exp ≥5yr | **2.77x** | ~124 |
| 🥉 **3** | **Experienced Movers** | 1-4yr tenure + exp ≥20yr | **2.65x** | ~199 |
| **4** | **Heavy Bleeders** | Net change <-10 + exp ≥5yr | **2.28x** | ~1,388 |
| ⚪ | Standard | Everything else | 0.92x | ~37,151 |

**Combined Priority (T1-T4):** 1,905 leads at **2.29x lift**

⚠️ **IMPORTANT:** The old "Platinum/Gold/Silver/Bronze" tier names have been retired.
See Decision Log for validation details.
```

---

### Step 2: Fix Salesforce Field Mapping

**Location:** Lines 10498-10505

**Replace with:**

```markdown
### Salesforce Fields

| Field | Type | Purpose |
|-------|------|---------|
| `Lead_Score_Tier__c` | Number | Tier rank (1, 2, 3, 4, 99) |
| `Lead_Tier_Name__c` | Picklist | TIER_1_PRIME_MOVER, TIER_2_MODERATE_BLEEDER, etc. |
| `Lead_Tier_Display__c` | Text | 🥇 Prime Mover, 🥈 Moderate Bleeder, etc. |
| `Lead_Score_Expected_Lift__c` | Number | Expected lift (3.40, 2.77, 2.65, 2.28, 1.00) |
| `Lead_Score_Model_Version__c` | Text | v3.1-final-20241221 |
| `Lead_Score_Narrative__c` | Long Text (500) | LLM-generated explanation |
```

---

### Step 3: Fix Narrative Example

**Location:** Lines 10525-10538

**Replace with:**

```markdown
### Narrative Example

**In Salesforce, SDRs will see:**

> **Score:** 🥇 Prime Mover (Expected Lift: 3.40x)
> 
> **Why This Lead:**  
> "This advisor recently joined their current firm (2 years ago) after 12 years in the industry. They're at the perfect career stage - established enough to have a book, mobile enough to consider a change. Their firm has seen 5 advisors leave in the past year, suggesting some internal instability."
>
> **Key Factors:**
> - ✅ Recent hire (2yr tenure) - still evaluating fit
> - ✅ Mid-career (12yr experience) - peak mobility window
> - ✅ Firm instability (net change: -5) - opportunity signal
> - ✅ Not wirehouse - no golden handcuffs

⚠️ **Note:** The old "small firm" criterion was DROPPED after validation showed small firms convert BELOW baseline (0.96x lift).
```

---

### Step 4: Add Production Decision Block

**Location:** After line 95 (after the Critical Corrections section)

**Add:**

```markdown
---

## 🎯 Production Decision: Rules-Only (V3.1)

**CONFIRMED:** Production uses rules-based tier assignment, NOT XGBoost ML.

| Approach | Status | Use Case |
|----------|--------|----------|
| **V3.1 Rules** | ✅ PRODUCTION | Daily scoring, Salesforce sync |
| XGBoost ML | 📦 ARCHIVED | Benchmarking only (see Phase -2) |
| BQML | 📦 ARCHIVED | Quick validation only |

**Why Rules Beat ML:**
- Top decile lift: 1.74x (rules) vs 1.63x (XGBoost)
- 100% interpretable (SDRs understand "1-4yr tenure + unstable firm")
- No model drift concerns
- Simpler infrastructure

Agents should **SKIP** any ML-related code sections unless explicitly requested.
```

---

### Step 5: Fix BigQuery Python Client Instructions

**Location:** BigQuery Contract section (around line 490)

**Add new subsection:**

```markdown
### Python Client Configuration

**CRITICAL:** Every BigQuery operation must specify Toronto region:

```python
from google.cloud import bigquery

# ALWAYS include location for Toronto
client = bigquery.Client(
    project='savvy-gtm-analytics',
    location='northamerica-northeast2'  # <-- REQUIRED
)

# For queries
query_job = client.query(sql, location='northamerica-northeast2')

# For table operations
table_ref = client.dataset('ml_features', location='northamerica-northeast2').table('lead_scores')
```

**Without explicit location:** Cross-region errors will occur even if datasets are correctly located in Toronto.
```

---

### Step 6: Remove Invalid Table-Level OPTIONS

**Global search for:**
```
OPTIONS(location='northamerica-northeast2')
```

**In CREATE TABLE statements, remove this clause entirely.**

**Keep it ONLY in CREATE SCHEMA/CREATE DATASET statements.**

---

### Step 7: Fix contact_date vs contacted_date

**Global search & replace:**
```
Find: contact_date
Replace: contacted_date
```

Then manually verify each change (some may be in column aliases where it's intentional).

---

### Step 8: Fix Snapshot Validation Function

**Location:** Find `validate_snapshot_integrity()` function

**Replace with corrected version from Issue 1.4 above.**

---

### Step 9: Add Deprecation Notice

**Location:** After Executive Summary (around line 95)

**Add:**

```markdown
---

## ⚠️ DEPRECATION NOTICE: Retired Tier Names & Criteria

The following are **DEPRECATED** and should NOT be used:

| Deprecated | Replacement | Reason |
|------------|-------------|--------|
| 💎 Platinum | 🥇 Prime Mover | Name change for clarity |
| 🥇 Gold | 🥈 Moderate Bleeder | Criteria changed |
| "Danger Zone" (1-2yr) | "Prime Movers" | Was our BEST segment (4.08x), not danger! |
| "Small firm ≤10" | DROPPED | Was measuring "UNKNOWN firms" not small firms (see analysis) |
| "Sweet Spot 4-10yr" | "1-4yr tenure" | Inverted - 1-4yr = 4.08x, 4-10yr = 1.5x |
| "Bleeding <-5" | Split: <-10 and -10 to -1 | Better segmentation |

**Why:** December 2024 validation discovered original thresholds were inverted or incorrect.

**Note on "Small Firm" rule:** Analysis of NUM_OF_EMPLOYEES (5.85% coverage) revealed actual small firms (1-10 employees) convert at **1.27x** (above baseline). The original 0.96x finding was because 91.5% of leads with `firm_rep_count = 0` were "unknown" not "small."
```

---

### Step 10: Global Search & Replace

Execute in order:

```
1. Find: "1_PLATINUM" → Replace: "TIER_1_PRIME_MOVER"
2. Find: "2_DANGER_ZONE" → Replace: "TIER_2_MODERATE_BLEEDER"
3. Find: "💎 Platinum" → Replace: "🥇 Prime Mover"
4. Find: "🥇 Gold" → Replace: "🥈 Moderate Bleeder"
5. Find: "🥈 Silver" → Replace: "🥉 Experienced Mover"
6. Find: "🥉 Bronze" → Replace: "4️⃣ Heavy Bleeder"
7. Find: "v3-hybrid" → Replace: "v3.1-final"
8. Find: "v3.0" → Replace: "v3.1"
```

---

### Step 11: Update Document Footer

**Location:** Lines 10467-10470

**Replace with:**

```markdown
*Document Version: 3.1*  
*Last Updated: December 21, 2024*  
*Model Version: v3.1-final-20241221*  
*Model Type: Four-Tier Rules-Based (Validated)*
*Validation: Rules outperform XGBoost ML (1.74x vs 1.63x)*
```

---

### Step 12: Update Deprecation Notice with "Unknown Firm" Insight

**Location:** In the deprecation notice added by Step 9

**Update this line:**
```markdown
| "Small firm ≤10" | DROPPED | Converts BELOW baseline (0.96x) |
```

**To:**
```markdown
| "Small firm ≤10" | DROPPED | Was measuring "UNKNOWN firms" not "small firms" - see Decision Log |
```

---

### Step 16: Add Firm Size Exploration Findings to Decision Log

**Location:** Decision Log section (after line ~176)

**Add this entry:**

```markdown
### Firm Size Signal - Explored & Rejected (December 2024)

**Hypothesis:** NUM_OF_EMPLOYEES could replace low-coverage rep_count calculation

**Analysis:** Ran exploration on 39,448 leads

**Results:**

| Metric | Expected | Actual |
|--------|----------|--------|
| Coverage | ~75% | **5.85%** |
| Best lift | >2.0x | **1.64x** (Medium 11-50) |
| Volume in best bucket | >500 | **200** |

| Firm Size | Leads | Conv % | Lift |
|-----------|-------|--------|------|
| Small (1-10) | 175 | 12.0% | 1.27x |
| **Medium (11-50)** | 200 | **15.5%** | **1.64x** |
| Large (51-200) | 222 | 10.36% | 1.10x |
| Very Large (201-1000) | 443 | 5.42% | **0.57x** |
| Enterprise (1000+) | 1,267 | 9.39% | 0.99x |

**Decision:** Do NOT add to V3.2 tiers

**Rationale:** Coverage too low (5.85%), lift too weak (1.64x max), volume too small (200)

**🔴 CRITICAL INSIGHT - Original "Small Firm" Finding Was WRONG:**

The original V3 rule said "small firm (≤10 reps) = 0.96x lift (avoid)."

This was a **DATA ARTIFACT**, not a real signal:
- 91.5% of leads had `firm_rep_count = 0` (unknown, not small)
- Actual small firms (1-10 employees) convert at **1.27x** (ABOVE baseline)
- We were penalizing "firms we can't track" not "small firms"

**Future consideration:** Very Large firms (201-1000 emp) show 0.57x lift - may warrant exclusion if pattern holds.
```

---

## Summary: Execution Checklist for Cursor.ai

### Pre-Flight (Before ANY BigQuery Execution)

- [ ] **P1:** Verify dataset locations are all `northamerica-northeast2`
- [ ] **P2:** Verify permissions (BigQuery Data Editor on ml_features)
- [ ] **P3:** Confirm ml_features dataset exists (or create it)

### Critical (Must Fix First)

- [ ] Step 1: Fix Quick Reference tier table
- [ ] Step 4: Add Production Decision block (rules vs ML)
- [ ] Step 5: Fix BigQuery Python client instructions (add location param)
- [ ] Step 6: Remove invalid table-level OPTIONS(location=...)
- [ ] Step 7: Fix contact_date → contacted_date naming
- [ ] Step 8: Fix snapshot validation function (CTE name + field name)
- [ ] Step 13: Add Firm_historicals lag canonical rule
- [ ] Step 14: Add scheduled query location requirement

### High Priority

- [ ] Step 2: Fix Salesforce field mapping
- [ ] Step 3: Fix narrative example
- [ ] Step 9: Add deprecation notice (updated with "small firm = unknown firm" insight)
- [ ] Step 10: Global search & replace
- [ ] Step 15: Add pre-execution permission checklist
- [ ] Step 16: Add firm size exploration findings to Decision Log

### Medium Priority

- [ ] Step 11: Update document footer
- [ ] Step 12: Update deprecation notice with "unknown firm" insight

### ✅ Data Exploration (COMPLETED)

- [x] ~~Run `explore_num_employees.sql` to evaluate firm size signal~~
- [x] **Result:** Coverage only 5.85%, best lift only 1.64x
- [x] **Decision:** DO NOT add to V3.2 tiers
- [x] **Insight:** Original "small firm = bad" was measuring "unknown firms"

### Post-Update Validation

After all changes:

1. Search for "Platinum" - should only find deprecation notice
2. Search for "Small (≤10)" - should be marked as DROPPED
3. Search for "OPTIONS(location=" - should only be in CREATE SCHEMA
4. Search for "contact_date" (without "ed") - should be zero or intentional aliases only
5. Verify tier definitions are consistent across all sections

---

## Expected Final Grade: **A (92/100)**
