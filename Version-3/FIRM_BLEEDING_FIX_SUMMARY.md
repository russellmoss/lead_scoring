# Firm Bleeding Calculation Fix - Summary

**Date:** 2025-01-XX  
**Issue:** Broken firm arrivals calculation in `lead_scoring_features_pit` table  
**Status:** ✅ Fixed in SQL file, needs regeneration

---

## Problem Identified

The `firm_net_change_12mo` feature in `lead_scoring_features_pit` was using a **broken calculation** for firm arrivals:

### ❌ OLD (BROKEN) Calculation:
- **Arrivals** were calculated from `contact_registered_employment_history` 
- This only captures people who **left** and then came back
- **Missing:** Current hires who are still at the firm (undercounts by 800+)
- **Impact:** Growing firms like Equitable Advisors were incorrectly marked as "bleeding"

### ✅ NEW (FIXED) Calculation:
- **Arrivals** now come from `ria_contacts_current` using `PRIMARY_FIRM_START_DATE`
- Captures all advisors currently at the firm who started within 12 months
- **PIT Verification:** Uses `employment_history` to verify advisor was at firm at `contacted_date`
- **Departures:** Still correctly calculated from `employment_history` (unchanged)

---

## Files Modified

### ✅ `sql/lead_scoring_features_pit.sql`
- **Lines 316-341:** Updated `firm_stability_pit` CTE
- **Arrivals calculation:** Changed from `employment_history` to `ria_contacts_current`
- **Added PIT verification:** Ensures advisors were at firm at `contacted_date`

---

## Next Steps (REQUIRED)

### 1. Regenerate Feature Table

**⚠️ CRITICAL:** The fix is in the SQL file, but the production table still has the broken data.

```sql
-- Drop existing table (or rename for backup)
DROP TABLE IF EXISTS `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_backup`;
CREATE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_backup` AS
SELECT * FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`;

-- Regenerate with corrected calculation
-- Execute: sql/lead_scoring_features_pit.sql
```

### 2. Validate the Fix

Run this diagnostic query to compare old vs new:

```sql
-- Compare firm_net_change values
SELECT 
    'Before fix (backup)' as source,
    AVG(firm_net_change_12mo) as avg_net_change,
    COUNT(*) as lead_count,
    COUNTIF(firm_net_change_12mo < 0) as bleeding_firms_count
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_backup`
WHERE firm_rep_count_at_contact >= 100

UNION ALL

SELECT 
    'After fix (new)' as source,
    AVG(firm_net_change_12mo) as avg_net_change,
    COUNT(*) as lead_count,
    COUNTIF(firm_net_change_12mo < 0) as bleeding_firms_count
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
WHERE firm_rep_count_at_contact >= 100;
```

**Expected Result:** 
- Average `firm_net_change_12mo` should be **higher** (less negative or more positive)
- Growing firms should now show positive values instead of negative

### 3. Re-Run Tier Scoring

After regenerating the feature table, re-run your production tier scoring:

```sql
-- Re-run: sql/phase_4_v3.2_12212025_consolidated.sql
-- This will use the CORRECTED firm_net_change_12mo values
```

### 4. Verify Tier Assignments

Check that growing firms are no longer incorrectly assigned to bleeding tiers:

```sql
-- Check Equitable Advisors (or other known growing firms)
SELECT 
    score_tier,
    COUNT(*) as lead_count,
    AVG(firm_net_change_12mo) as avg_net_change
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3`
WHERE Company LIKE '%Equitable%'
GROUP BY score_tier
ORDER BY lead_count DESC;
```

---

## Impact Assessment

### Before Fix:
- ❌ Growing firms incorrectly marked as "bleeding"
- ❌ Tier 1/2/3/4 logic incorrectly includes non-bleeding firms
- ❌ Missing leads from growing firms that might qualify for other tiers

### After Fix:
- ✅ Growing firms correctly identified (positive `firm_net_change_12mo`)
- ✅ Only truly bleeding firms qualify for bleeding tiers
- ✅ More accurate tier assignments overall

---

## Technical Details

### Arrivals Calculation (Fixed)

```sql
-- CORRECTED: Count from ria_contacts_current
(SELECT COUNT(DISTINCT c.RIA_CONTACT_CRD_ID)
 FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
 INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_verify
     ON c.RIA_CONTACT_CRD_ID = eh_verify.RIA_CONTACT_CRD_ID
 WHERE SAFE_CAST(c.PRIMARY_FIRM AS INT64) = rsp.firm_crd_at_contact
   AND c.PRIMARY_FIRM_START_DATE IS NOT NULL
   AND c.PRIMARY_FIRM_START_DATE <= rsp.contacted_date
   AND c.PRIMARY_FIRM_START_DATE > DATE_SUB(rsp.contacted_date, INTERVAL 12 MONTH)
   -- PIT verification: Advisor was at this firm at contacted_date
   AND eh_verify.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = rsp.firm_crd_at_contact
   AND eh_verify.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= rsp.contacted_date
   AND (eh_verify.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
        OR eh_verify.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= rsp.contacted_date)
) as arrivals_12mo
```

### Departures Calculation (Unchanged - Already Correct)

```sql
-- Departures from employment_history (correct)
COUNT(DISTINCT CASE 
    WHEN eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
         AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE <= rsp.contacted_date
         AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE > DATE_SUB(rsp.contacted_date, INTERVAL 12 MONTH)
    THEN eh.RIA_CONTACT_CRD_ID 
END) as departures_12mo
```

---

## References

- **Fixed File:** `Version-3/sql/lead_scoring_features_pit.sql`
- **Production Table:** `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
- **Tier Scoring:** `Version-3/sql/phase_4_v3.2_12212025_consolidated.sql`

