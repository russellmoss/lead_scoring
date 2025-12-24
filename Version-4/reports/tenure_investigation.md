# Tenure "Unknown" Investigation Report

**Generated**: 2025-12-24  
**Issue**: 97.2% of test leads (5,836 of 6,004) have `tenure_bucket = "Unknown"` despite Phase 1 showing 78.64% employment history coverage.

---

## Executive Summary

**ROOT CAUSE IDENTIFIED**: The feature engineering SQL (`phase_2_feature_engineering.sql`) only queries `contact_registered_employment_history` for current employment, but this table primarily contains **past employment records**. Current employment information is stored in `ria_contacts_current` table, which is not being used.

**Impact**: This is a **BUG** that significantly reduces feature quality. Fixing it could dramatically improve model performance.

---

## Query Results

### Query 1: Employment History Coverage in Test Period

| Employment Status | Leads | Percentage |
|-------------------|-------|------------|
| No History | 5,836 | 97.2% |
| Has History | 168 | 2.8% |

**Finding**: Only 2.8% of test leads have employment history, vs 9.72% in training period.

### Query 2: Tenure Bucket Distribution

| has_employment_history | tenure_bucket | is_tenure_missing | Leads |
|----------------------|---------------|-------------------|-------|
| 0 | Unknown | 1 | 5,836 |
| 1 | 48-120 | 0 | 66 |
| 1 | 24-48 | 0 | 32 |
| 1 | 120+ | 0 | 28 |
| 1 | 0-12 | 0 | 24 |
| 1 | 12-24 | 0 | 18 |

**Finding**: All "Unknown" tenure leads have `has_employment_history = 0`. The logic is consistent - if no employment history is found, tenure is Unknown.

### Query 3: Sample Leads with Employment History but Unknown Tenure

**Result**: 0 rows found.

**Finding**: No leads have `has_employment_history = 1` AND `tenure_bucket = 'Unknown'`. This confirms the logic is working correctly - the issue is that `has_employment_history = 0` for 97% of leads.

### Query 4: Raw Employment History Check

**Sample Lead**: `00QVS000006lgcY2AT` (advisor_crd: 5386963, contacted_date: 2025-08-07)

**Employment History Records Found**: 4 records, ALL with `END_DATE` BEFORE `contacted_date`:
- 2012-11-06 to 2019-05-23 (END_TOO_EARLY)
- 2008-08-21 to 2012-11-06 (END_TOO_EARLY)
- 2008-06-20 to 2012-11-06 (END_TOO_EARLY)
- 2004-09-30 to 2007-04-02 (END_TOO_EARLY)

**Finding**: The `contact_registered_employment_history` table only contains PAST employment. There are NO records with `END_DATE IS NULL` or `END_DATE >= contacted_date` for this lead.

**However**, `ria_contacts_current` shows:
- `LATEST_REGISTERED_EMPLOYMENT_COMPANY_CRD_ID`: 6413
- `LATEST_REGISTERED_EMPLOYMENT_START_DATE`: 2012-11-06
- `PRIMARY_FIRM`: 297287
- `PRIMARY_FIRM_NAME`: "IFP Securities, LLC"

**This advisor IS currently employed**, but the current employment is NOT in `contact_registered_employment_history` - it's only in `ria_contacts_current`.

### Query 5: Comparison Across Periods

| Period | Total Leads | Leads with History | Percentage |
|--------|-------------|-------------------|------------|
| Training Period | 24,734 | 2,404 | 9.72% |
| Test Period | 6,004 | 168 | 2.8% |

**Finding**: Test period has significantly lower coverage (2.8% vs 9.72%), suggesting either:
1. Data quality degraded over time, OR
2. Test period leads are more likely to have current employment that's not yet in history table

---

## Root Cause Analysis

### The Bug

The `current_firm` CTE in `sql/phase_2_feature_engineering.sql` (lines 44-69) only queries `contact_registered_employment_history`:

```sql
current_firm AS (
    SELECT 
        b.lead_id,
        b.contacted_date,
        b.advisor_crd,
        eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
        eh.PREVIOUS_REGISTRATION_COMPANY_NAME as firm_name,
        eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE as firm_start_date,
        DATE_DIFF(b.contacted_date, eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE, MONTH) as tenure_months
    FROM base b
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON b.advisor_crd = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= b.contacted_date
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= b.contacted_date)
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY b.lead_id 
        ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
    ) = 1
)
```

**Problem**: The `contact_registered_employment_history` table appears to primarily contain **completed/past employment periods**. Current employment is tracked in `ria_contacts_current` table with fields:
- `LATEST_REGISTERED_EMPLOYMENT_COMPANY_CRD_ID`
- `LATEST_REGISTERED_EMPLOYMENT_START_DATE`
- `PRIMARY_FIRM`
- `PRIMARY_FIRM_NAME`

### Why This Happens

1. **Data Model**: FINTRX appears to use `contact_registered_employment_history` for historical tracking, while `ria_contacts_current` contains the current snapshot.

2. **PIT Compliance**: The current approach is trying to be PIT-compliant by only using historical data, but it's missing the current employment snapshot.

3. **Temporal Drift**: The test period (Aug-Oct 2025) has even lower coverage (2.8%) than training (9.72%), suggesting that more recent leads have current employment that hasn't been backfilled into the history table yet.

---

## Recommended Fix

### Option 1: Use `ria_contacts_current` as Primary Source (RECOMMENDED)

Modify `current_firm` CTE to:
1. First try `contact_registered_employment_history` for PIT-compliant historical data
2. **Fallback to `ria_contacts_current`** if no current employment found in history table
3. Calculate tenure from `LATEST_REGISTERED_EMPLOYMENT_START_DATE` to `contacted_date`

**SQL Fix**:
```sql
current_firm AS (
    -- Try employment history first (PIT-compliant)
    WITH history_firm AS (
        SELECT 
            b.lead_id,
            b.contacted_date,
            b.advisor_crd,
            eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
            eh.PREVIOUS_REGISTRATION_COMPANY_NAME as firm_name,
            eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE as firm_start_date,
            DATE_DIFF(b.contacted_date, eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE, MONTH) as tenure_months
        FROM base b
        LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
            ON b.advisor_crd = eh.RIA_CONTACT_CRD_ID
            AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= b.contacted_date
            AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
                 OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= b.contacted_date)
        QUALIFY ROW_NUMBER() OVER(
            PARTITION BY b.lead_id 
            ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
        ) = 1
    ),
    -- Fallback to current snapshot if no history found
    current_snapshot AS (
        SELECT 
            b.lead_id,
            b.contacted_date,
            b.advisor_crd,
            c.LATEST_REGISTERED_EMPLOYMENT_COMPANY_CRD_ID as firm_crd,
            c.LATEST_REGISTERED_EMPLOYMENT_COMPANY as firm_name,
            c.LATEST_REGISTERED_EMPLOYMENT_START_DATE as firm_start_date,
            DATE_DIFF(b.contacted_date, c.LATEST_REGISTERED_EMPLOYMENT_START_DATE, MONTH) as tenure_months
        FROM base b
        LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
            ON b.advisor_crd = c.RIA_CONTACT_CRD_ID
        WHERE c.LATEST_REGISTERED_EMPLOYMENT_START_DATE IS NOT NULL
          AND c.LATEST_REGISTERED_EMPLOYMENT_START_DATE <= b.contacted_date
    )
    SELECT 
        COALESCE(hf.lead_id, cs.lead_id) as lead_id,
        COALESCE(hf.contacted_date, cs.contacted_date) as contacted_date,
        COALESCE(hf.advisor_crd, cs.advisor_crd) as advisor_crd,
        COALESCE(hf.firm_crd, cs.firm_crd) as firm_crd,
        COALESCE(hf.firm_name, cs.firm_name) as firm_name,
        COALESCE(hf.firm_start_date, cs.firm_start_date) as firm_start_date,
        COALESCE(hf.tenure_months, cs.tenure_months) as tenure_months
    FROM history_firm hf
    FULL OUTER JOIN current_snapshot cs
        ON hf.lead_id = cs.lead_id
    WHERE COALESCE(hf.lead_id, cs.lead_id) IS NOT NULL
)
```

### Option 2: Use `PRIMARY_FIRM` from `ria_contacts_current`

If `LATEST_REGISTERED_EMPLOYMENT_*` fields are not reliable, use `PRIMARY_FIRM` and `PRIMARY_FIRM_START_DATE` instead.

---

## Impact Assessment

### Current State
- **Training Period**: 9.72% have tenure (2,404 of 24,734)
- **Test Period**: 2.8% have tenure (168 of 6,004)
- **Overall**: ~10% coverage

### Expected After Fix
- **Training Period**: Should increase to ~70-80% (based on Phase 1 coverage metric)
- **Test Period**: Should increase to ~70-80%
- **Overall**: ~75% coverage (7.5x improvement)

### Model Impact
1. **Feature Quality**: Tenure is a critical feature (short tenure = 4.05x lift in exploration)
2. **Model Performance**: With 7.5x more tenure data, model should see significant improvement
3. **Segment Analysis**: Currently 97% "Unknown" makes tenure_bucket segmentation unreliable

### Risk Assessment
- **PIT Compliance**: Using `ria_contacts_current` is a snapshot, but if `LATEST_REGISTERED_EMPLOYMENT_START_DATE` is accurate, it should be PIT-compliant
- **Data Quality**: Need to validate that `LATEST_REGISTERED_EMPLOYMENT_START_DATE` is not updated retroactively

---

## Next Steps

1. **Immediate**: Implement Option 1 fix in `sql/phase_2_feature_engineering.sql`
2. **Validation**: Re-run Phase 2 and verify tenure coverage increases to ~75%
3. **Re-run Phases**: If fix is successful, re-run Phases 2-7:
   - Phase 2: Feature Engineering (with fix)
   - Phase 3: Leakage Audit
   - Phase 4: Multicollinearity Analysis
   - Phase 5: Train/Test Split
   - Phase 6: Model Training
   - Phase 7: Overfitting Detection
4. **Comparison**: Compare model performance before/after fix

---

## Conclusion

This is a **critical bug** that significantly reduces feature quality. The fix is straightforward (add fallback to `ria_contacts_current`) and should dramatically improve model performance by providing tenure data for ~75% of leads instead of ~10%.

**Recommendation**: **FIX IMMEDIATELY** before proceeding to Phase 8.

