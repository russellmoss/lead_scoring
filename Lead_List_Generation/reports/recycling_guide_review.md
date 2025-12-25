# Monthly Recyclable Lead List Generation Guide V2 - Review

**Review Date**: December 24, 2025  
**Status**: ⚠️ **NEEDS CORRECTIONS BEFORE AGENTIC EXECUTION**

---

## Executive Summary

The guide has **sound prioritization logic** but contains **critical SQL errors** that must be fixed before agentic execution. The corrected firm change logic (excluding recent movers < 2 years) is conceptually correct, but the implementation has date type mismatches and logic issues.

---

## ✅ What's Good

### 1. Prioritization Logic Makes Sense

The corrected priority tiers are well-reasoned:

| Priority | Logic | Rationale | Status |
|----------|-------|------------|--------|
| **P1: Timing** | "Timing" disposition + 180-365 days | They said timing was bad - try again | ✅ Sound |
| **P2: High V4 + No Change + Long Tenure** | V4≥80 + No firm change + ≥3 years tenure | Model predicts move, hasn't moved yet | ✅ Sound |
| **P3: No Response + High V4** | No response + V4≥70 | Good prospect who didn't engage | ✅ Sound |
| **P4: Changed 2-3 Years Ago** | Changed firms 2-3 years ago | Proven mover, may be restless | ✅ Sound |
| **P5: Changed 3+ Years Ago** | Changed 3+ years + V4≥60 | Overdue for another change | ✅ Sound |

**Key Insight**: Excluding people who changed firms < 2 years ago is correct - they just settled in and won't move again soon.

### 2. Exclusion Logic is Correct

- ✅ Excludes no-go dispositions (permanent DQs)
- ✅ Excludes DoNotCall = true
- ✅ Excludes recently contacted (< 90 days)
- ✅ Excludes recent firm changers (< 2 years)

### 3. Structure is Clear

- ✅ Well-organized phases
- ✅ Clear Cursor prompts
- ✅ Complete SQL and Python code
- ✅ Expected outputs documented

---

## ❌ Critical Issues to Fix

### Issue 1: Date Type Mismatch in Firm Change Detection

**Problem**: Comparing `PRIMARY_FIRM_START_DATE` (DATE) with `CloseDate` (DATE) and `Stage_Entered_Closed__c` (TIMESTAMP) without proper casting.

**Location**: Lines 251, 303, 352, 406

**Current Code**:
```sql
-- Line 251 (Opportunities)
WHEN c.PRIMARY_FIRM_START_DATE > o.CloseDate THEN TRUE

-- Line 352 (Leads)  
WHEN c.PRIMARY_FIRM_START_DATE > l.Stage_Entered_Closed__c THEN TRUE
```

**Issue**: `Stage_Entered_Closed__c` is TIMESTAMP, `PRIMARY_FIRM_START_DATE` is DATE. Need to cast.

**Fix Required**:
```sql
-- For Opportunities (CloseDate is already DATE, so OK)
WHEN c.PRIMARY_FIRM_START_DATE > DATE(o.CloseDate) THEN TRUE

-- For Leads (Stage_Entered_Closed__c is TIMESTAMP)
WHEN c.PRIMARY_FIRM_START_DATE > DATE(l.Stage_Entered_Closed__c) THEN TRUE
```

---

### Issue 2: Logic Error in `years_at_firm_total` Calculation

**Problem**: The calculation for `years_at_firm_total` (tenure at firm when we closed them) is incorrect.

**Location**: Lines 263-267 (Opportunities), 364-368 (Leads)

**Current Code**:
```sql
-- Line 264-266 (Opportunities)
CASE 
    WHEN c.PRIMARY_FIRM_START_DATE IS NOT NULL AND c.PRIMARY_FIRM_START_DATE <= o.CloseDate
    THEN DATE_DIFF(CURRENT_DATE(), DATE(c.PRIMARY_FIRM_START_DATE), DAY) / 365.0
    ELSE NULL
END as years_at_firm_total,
```

**Issue**: This calculates tenure from `PRIMARY_FIRM_START_DATE` (current firm start) to `CURRENT_DATE()`, not to `CloseDate`. If they changed firms after we closed them, this gives wrong tenure.

**Correct Logic**: We need to find the firm they were at WHEN we closed them, not their current firm.

**Fix Required**: Use employment history to find firm at time of close:

```sql
-- For Opportunities
CASE 
    WHEN eh_close.PREVIOUS_REGISTRATION_COMPANY_START_DATE IS NOT NULL 
         AND eh_close.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(o.CloseDate)
         AND (eh_close.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
              OR eh_close.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(o.CloseDate))
    THEN DATE_DIFF(DATE(o.CloseDate), DATE(eh_close.PREVIOUS_REGISTRATION_COMPANY_START_DATE), DAY) / 365.0
    ELSE NULL
END as years_at_firm_when_closed,
```

---

### Issue 3: Missing Employment History Join for "Firm at Close"

**Problem**: The query doesn't join to employment history to find what firm they were at when we closed them. It only uses `PRIMARY_FIRM_START_DATE` which is their CURRENT firm.

**Impact**: 
- If they changed firms after we closed them, we can't correctly calculate tenure at the firm they were at when we closed
- The `years_at_firm_total` field will be wrong for people who changed firms

**Fix Required**: Add employment history join to find firm at time of close:

```sql
-- Add to recyclable_opportunities CTE
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_close
    ON SAFE_CAST(REGEXP_REPLACE(CAST(o.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh_close.RIA_CONTACT_CRD_ID
    AND eh_close.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= DATE(o.CloseDate)
    AND (eh_close.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
         OR eh_close.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE(o.CloseDate))
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY o.Id 
    ORDER BY eh_close.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
) = 1
```

---

### Issue 4: Potential Issue with Firm Change Detection

**Current Logic**:
```sql
CASE 
    WHEN c.PRIMARY_FIRM_START_DATE > o.CloseDate THEN TRUE
    ELSE FALSE
END as changed_firms_since_close,
```

**Problem**: This only detects if they started at their CURRENT firm after we closed them. But what if:
- They were at Firm A when we closed them
- They moved to Firm B (started 1 year ago)
- They moved to Firm C (current firm, started 6 months ago)

The query would only see Firm C's start date, missing the intermediate move.

**However**: For recycling purposes, we mainly care about "did they change firms after we closed them?" - which this captures. The intermediate moves are less relevant.

**Status**: ⚠️ **Acceptable but not perfect** - may miss some edge cases.

---

### Issue 5: Missing Field Validation

**Potential Issues**:
- `LinkedIn_URL__c` field may not exist on Lead object (should check)
- `SGA_Owner__c` and `SGM_Owner__c` fields may not exist
- `Advisor_First_Name__c`, `Advisor_Last_Name__c` etc. on Opportunity may not exist

**Fix Required**: Verify all custom fields exist or add NULL handling.

---

## 🔧 Required Fixes

### Fix 1: Date Type Casting

**File**: `sql/recycling/recyclable_pool_master_v2.sql`

**Changes Needed**:
1. Cast `Stage_Entered_Closed__c` to DATE in all comparisons
2. Cast `CloseDate` to DATE for consistency
3. Ensure all date comparisons use same types

### Fix 2: Add Employment History Join

**Changes Needed**:
1. Add employment history join to find firm at time of close
2. Calculate `years_at_firm_when_closed` correctly
3. Use this for P2 priority logic (long tenure at firm when closed)

### Fix 3: Field Validation

**Changes Needed**:
1. Verify all custom fields exist
2. Add NULL handling for optional fields
3. Use COALESCE for fallback values

---

## 📋 Readiness Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| **Prioritization Logic** | ✅ **SOUND** | Corrected firm change logic is well-reasoned |
| **SQL Syntax** | ❌ **NEEDS FIXES** | Date type mismatches, missing joins |
| **Field Names** | ⚠️ **NEEDS VERIFICATION** | Some custom fields may not exist |
| **Structure** | ✅ **READY** | Clear phases, good organization |
| **Documentation** | ✅ **GOOD** | Well-documented logic and rationale |

**Overall Status**: ⚠️ **NOT READY FOR AGENTIC EXECUTION** - Fix SQL issues first.

---

## 🎯 Recommended Action Plan

### Step 1: Fix SQL Issues (Critical)
1. Fix date type casting
2. Add employment history join for firm at close
3. Correct `years_at_firm_total` calculation
4. Validate all field names

### Step 2: Test Query
1. Run query with LIMIT 100 to validate
2. Check for NULL values in key fields
3. Verify firm change detection works correctly
4. Validate priority assignment

### Step 3: Update Guide
1. Add field validation section
2. Document any field name changes
3. Add troubleshooting section

### Step 4: Mark as Ready
1. Add "✅ READY FOR AGENTIC EXECUTION" header
2. Document any assumptions or limitations
3. Add validation checklist

---

## 💡 Logic Validation

### The "Exclude Recent Movers" Logic is Correct

**Why it makes sense**:
- People who just changed firms (< 2 years) are:
  - Still building relationships at new firm
  - Dealing with transition stress
  - Unlikely to move again soon (settling in period)
  
- People who changed firms 2-3 years ago:
  - Have had time to settle
  - May be evaluating options again
  - Proven track record of being willing to move

- People who haven't moved but have long tenure + high V4:
  - Model predicts they're about to move
  - Haven't moved yet = still at same firm = good timing

**This aligns with behavioral research**: Most advisors have a "settling period" of 1-2 years after a move before they consider moving again.

---

## 🔍 Specific SQL Issues Found

### Issue A: Line 251 (Opportunities)
```sql
-- CURRENT (may have type mismatch)
WHEN c.PRIMARY_FIRM_START_DATE > o.CloseDate THEN TRUE

-- SHOULD BE
WHEN c.PRIMARY_FIRM_START_DATE IS NOT NULL 
     AND DATE(c.PRIMARY_FIRM_START_DATE) > DATE(o.CloseDate) THEN TRUE
```

### Issue B: Line 352 (Leads)
```sql
-- CURRENT (type mismatch - Stage_Entered_Closed__c is TIMESTAMP)
WHEN c.PRIMARY_FIRM_START_DATE > l.Stage_Entered_Closed__c THEN TRUE

-- SHOULD BE
WHEN c.PRIMARY_FIRM_START_DATE IS NOT NULL 
     AND DATE(c.PRIMARY_FIRM_START_DATE) > DATE(l.Stage_Entered_Closed__c) THEN TRUE
```

### Issue C: Lines 264-266, 365-367 (Tenure Calculation)
```sql
-- CURRENT (calculates to CURRENT_DATE, not CloseDate)
WHEN c.PRIMARY_FIRM_START_DATE IS NOT NULL AND c.PRIMARY_FIRM_START_DATE <= o.CloseDate
THEN DATE_DIFF(CURRENT_DATE(), DATE(c.PRIMARY_FIRM_START_DATE), DAY) / 365.0

-- SHOULD BE (need employment history join first)
-- Use employment history to find firm at time of close, then calculate tenure to close date
```

### Issue D: Lines 303, 406 (Exclusion Logic)
```sql
-- CURRENT
OR c.PRIMARY_FIRM_START_DATE <= o.CloseDate

-- SHOULD BE (with proper casting)
OR (c.PRIMARY_FIRM_START_DATE IS NOT NULL 
    AND DATE(c.PRIMARY_FIRM_START_DATE) <= DATE(o.CloseDate))
```

---

## ✅ What to Keep

1. **Priority Logic**: The P1-P6 prioritization is sound
2. **Exclusion Lists**: No-go dispositions and reasons are correct
3. **Time Windows**: 90-730 days for recycling is reasonable
4. **2-Year Exclusion**: Excluding recent movers is correct
5. **Structure**: Phase organization is good

---

## 📝 Summary

**Prioritization Logic**: ✅ **SOUND** - The corrected firm change logic makes behavioral sense.

**SQL Implementation**: ❌ **NEEDS FIXES** - Date type mismatches and missing employment history join.

**Readiness**: ⚠️ **NOT READY** - Fix SQL issues before agentic execution.

**Recommendation**: Fix the 4 critical SQL issues listed above, then mark as ready for agentic execution.

