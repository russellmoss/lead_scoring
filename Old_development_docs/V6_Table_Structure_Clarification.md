# V6 Table Structure Clarification

## 📊 **Key Distinction: `_current` vs `snapshot_*` Tables**

### **Existing Tables (Already Created):**
- `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
  - **Purpose:** Current/latest snapshot of all reps
  - **Temporal Dimension:** ❌ NO quarters (just "current" state)
  - **Used For:** Production scoring of NEW leads
  - **Structure:** Same schema as snapshot tables, but no `snapshot_quarter` column

- `savvy-gtm-analytics.LeadScoring.discovery_firms_current`
  - **Purpose:** Current/latest snapshot of all firms (aggregated from `discovery_reps_current`)
  - **Temporal Dimension:** ❌ NO quarters
  - **Used For:** Production scoring of NEW leads
  - **Structure:** Same schema as firm snapshot tables, but no `snapshot_quarter` column

### **New Tables We're Creating (V6 Plan):**
- `savvy-gtm-analytics.LeadScoring.snapshot_reps_2024_q1` through `snapshot_reps_2025_q4`
  - **Purpose:** Historical snapshots of reps at specific quarters
  - **Temporal Dimension:** ✅ YES - Each table represents data as it existed in that quarter
  - **Used For:** Training the XGBoost model with point-in-time joins (preventing temporal leakage)
  - **Structure:** Same schema as `discovery_reps_current` PLUS `snapshot_quarter` column

- `savvy-gtm-analytics.LeadScoring.snapshot_firms_2024_q1` through `snapshot_firms_2025_q4`
  - **Purpose:** Historical snapshots of firms at specific quarters (aggregated from rep snapshots)
  - **Temporal Dimension:** ✅ YES - Each table represents firm data as it existed in that quarter
  - **Used For:** Training the XGBoost model with point-in-time joins
  - **Structure:** Same schema as `discovery_firms_current` PLUS `snapshot_quarter` column

---

## 🎯 **Why We Need Quarter-Specific Tables for XGBoost Training**

### **The Temporal Leakage Problem:**

When training a model, we must ensure that:
- **For a lead that entered the funnel in Q1 2024**, we only use discovery data that existed **as of Q1 2024**
- **NOT** use data from Q2 2024 or later (which would be "looking into the future")

### **How Point-in-Time Joins Work:**

```sql
-- Step 3.1 in V6 Plan
WITH LeadsWithQuarter AS (
    SELECT 
        Id,
        FA_CRD__c,
        Stage_Entered_Contacting__c,
        DATE_TRUNC(DATE(Stage_Entered_Contacting__c), QUARTER) as contact_quarter
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE Stage_Entered_Contacting__c IS NOT NULL
      AND FA_CRD__c IS NOT NULL
),
PointInTimeJoin AS (
    SELECT
        l.*,
        reps.*  -- Rep features from the CORRECT quarter
    FROM LeadsWithQuarter l
    JOIN `LeadScoring.v_discovery_reps_all_vintages` reps
        ON l.FA_CRD__c = reps.RepCRD
       AND l.contact_quarter = reps.snapshot_quarter  -- ⭐ KEY: Match quarters!
    LEFT JOIN `LeadScoring.v_discovery_firms_all_vintages` firms
        ON reps.RIAFirmCRD = firms.RIAFirmCRD
       AND reps.snapshot_quarter = firms.snapshot_quarter  -- ⭐ KEY: Match quarters!
)
```

**The join condition `l.contact_quarter = reps.snapshot_quarter` ensures:**
- Lead from Q1 2024 → Uses rep data from Q1 2024 snapshot
- Lead from Q2 2024 → Uses rep data from Q2 2024 snapshot
- **No future data leakage!**

---

## 📋 **Summary Table**

| Table Type | Table Name Pattern | Quarters? | Purpose | Used For |
|------------|-------------------|-----------|---------|----------|
| **Current** | `discovery_reps_current` | ❌ No | Latest snapshot | Production scoring |
| **Current** | `discovery_firms_current` | ❌ No | Latest snapshot | Production scoring |
| **Snapshot** | `snapshot_reps_YYYY_Q` | ✅ Yes | Historical snapshots | Model training |
| **Snapshot** | `snapshot_firms_YYYY_Q` | ✅ Yes | Historical snapshots | Model training |
| **View** | `v_discovery_reps_all_vintages` | ✅ Yes | Union of all snapshots | Model training |
| **View** | `v_discovery_firms_all_vintages` | ✅ Yes | Union of all snapshots | Model training |

---

## ✅ **Answer to Your Question:**

**Q: Are we creating `discovery_reps_current` and `discovery_firms_current`?**

**A: NO** - These tables already exist. We're creating NEW quarter-specific snapshot tables:
- `snapshot_reps_2024_q1`, `snapshot_reps_2024_q2`, etc. (8 tables)
- `snapshot_firms_2024_q1`, `snapshot_firms_2024_q2`, etc. (8 tables)

**Q: Why do we need quarters for the XGBoost model?**

**A: YES** - We need quarters to prevent temporal leakage:
- When a lead enters the funnel in Q1 2024, we must use discovery data from Q1 2024 (not Q2, Q3, or Q4)
- The `snapshot_quarter` column allows us to join leads to the correct historical snapshot
- This ensures the model sees data as it would have been available at the time (no future information)

---

## 🔄 **Data Flow:**

```
8 RIARepDataFeed CSV Files (2024-2025)
    ↓
Step 1.2: Upload to raw staging tables (_raw)
    ↓
Step 1.5: Transform to standardized schema
    ↓
8 snapshot_reps_YYYY_Q tables (with snapshot_quarter column)
    ↓
Step 1.6: Aggregate to firm level
    ↓
8 snapshot_firms_YYYY_Q tables (with snapshot_quarter column)
    ↓
Step 2: Union into views
    ↓
v_discovery_reps_all_vintages (all quarters)
v_discovery_firms_all_vintages (all quarters)
    ↓
Step 3: Point-in-time joins with leads (by quarter)
    ↓
Training dataset for XGBoost model (no temporal leakage!)
```

---

## 📝 **Note:**

The `discovery_reps_current` and `discovery_firms_current` tables are:
- **Still used** for production scoring of new leads
- **NOT used** for model training (we need historical snapshots with quarters)
- **Reference schema** for our snapshot tables (same column structure, just add `snapshot_quarter`)

