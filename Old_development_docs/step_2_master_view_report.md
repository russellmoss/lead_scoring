# Step 2: Master Snapshot Views Creation Report

**Date:** 2025-11-04  
**Step:** 2  
**Status:** SUCCESS

---

## Views Created

### 1. v_discovery_reps_all_vintages

- **Status:** Created successfully
- **Row Count:** 3,845,530
- **Distinct Reps:** 522,181
- **Distinct Snapshot Dates:** 8
- **Date Range:** 2024-01-07 to 2025-10-05

**Source Tables:**
- snapshot_reps_20240107
- snapshot_reps_20240331
- snapshot_reps_20240707
- snapshot_reps_20241006
- snapshot_reps_20250105
- snapshot_reps_20250406
- snapshot_reps_20250706
- snapshot_reps_20251005

### 2. v_discovery_firms_all_vintages

- **Status:** Created successfully
- **Row Count:** 328,184
- **Distinct Firms:** 46,376
- **Distinct Snapshot Dates:** 8
- **Date Range:** 2024-01-07 to 2025-10-05

**Source Tables:**
- snapshot_firms_20240107
- snapshot_firms_20240331
- snapshot_firms_20240707
- snapshot_firms_20241006
- snapshot_firms_20250105
- snapshot_firms_20250406
- snapshot_firms_20250706
- snapshot_firms_20251005

---

## Validation

- ✅ All 8 rep snapshots successfully combined into single view
- ✅ All 8 firm snapshots successfully combined into single view
- ✅ `snapshot_at` column exists in both views
- ✅ Row counts match sum of individual snapshot tables
- ✅ All 8 snapshot dates present (2024-01-07, 2024-03-31, 2024-07-07, 2024-10-06, 2025-01-05, 2025-04-06, 2025-07-06, 2025-10-05)
- ✅ Views are queryable and ready for Step 3 point-in-time joins

---

## View Details

### Rep View Statistics
- **Total Rows:** 3,845,530 (across all 8 snapshots)
- **Unique Reps:** 522,181 (some reps appear in multiple snapshots)
- **Average Rows per Snapshot:** ~480,691
- **Date Span:** 21 months (2024-01-07 to 2025-10-05)

### Firm View Statistics
- **Total Rows:** 328,184 (across all 8 snapshots)
- **Unique Firms:** 46,376 (some firms appear in multiple snapshots)
- **Average Rows per Snapshot:** ~41,023
- **Date Span:** 21 months (2024-01-07 to 2025-10-05)

---

## SQL Validation Queries

### Rep View Validation
```sql
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT snapshot_at) as distinct_snapshot_dates,
    COUNT(DISTINCT RepCRD) as distinct_reps,
    MIN(snapshot_at) as earliest_snapshot,
    MAX(snapshot_at) as latest_snapshot
FROM `savvy-gtm-analytics.LeadScoring.v_discovery_reps_all_vintages`
```

**Result:**
- total_rows: 3,845,530
- distinct_snapshot_dates: 8
- distinct_reps: 522,181
- earliest_snapshot: 2024-01-07
- latest_snapshot: 2025-10-05

### Firm View Validation
```sql
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT snapshot_at) as distinct_snapshot_dates,
    COUNT(DISTINCT RIAFirmCRD) as distinct_firms,
    MIN(snapshot_at) as earliest_snapshot,
    MAX(snapshot_at) as latest_snapshot
FROM `savvy-gtm-analytics.LeadScoring.v_discovery_firms_all_vintages`
```

**Result:**
- total_rows: 328,184
- distinct_snapshot_dates: 8
- distinct_firms: 46,376
- earliest_snapshot: 2024-01-07
- latest_snapshot: 2025-10-05

---

## Next Steps

✅ **Gate Passed:** Both views created and validated successfully.

**Ready for Step 3:** Point-in-Time Joins with Salesforce Leads

The views are now ready to be used in Step 3.1 for point-in-time joins, where:
- Each lead's `Stage_Entered_Contacting__c` date will be matched to the most recent `snapshot_at` that is ≤ the contact date
- This ensures temporal correctness and prevents data leakage

---

**Report Generated:** 2025-11-04  
**Created By:** `step_2_create_master_views.py`  
**View Creation Method:** UNION ALL of all 8 snapshot tables

