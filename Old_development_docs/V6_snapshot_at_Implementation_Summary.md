# V6 Implementation: Using `snapshot_at` Instead of `snapshot_quarter`

## 🎯 **Key Change**

We've updated the V6 plan to use **actual snapshot dates from CSV filenames** (`snapshot_at`) instead of quarter start dates (`snapshot_quarter`). This provides more accurate temporal matching and handles edge cases naturally.

---

## ✅ **What Changed**

### **1. Snapshot Date Field**
- **Old**: `snapshot_quarter` (quarter start date, e.g., `2024-01-01`)
- **New**: `snapshot_at` (actual CSV file date, e.g., `2024-03-31`)

### **2. Temporal Matching Logic**
- **Old**: Match leads to snapshots using quarter boundaries
  ```sql
  WHERE contact_quarter = snapshot_quarter
  ```
- **New**: Match leads to the **most recent snapshot that is still before or equal to the contact date**
  ```sql
  WHERE snapshot_at <= contact_date
  ORDER BY snapshot_at DESC
  LIMIT 1
  ```

### **3. Files Updated**
- ✅ `step_1_2_upload_ria_reps_raw.py` - Tracks actual snapshot dates
- ✅ `V6_Historical_Data_Processing_Guide.md` - Updated all steps
- ✅ `config/v6_feature_contract.json` - Changed field name
- ✅ `config/v6_firm_feature_contract.json` - Changed field name
- ✅ `config/v6_snapshot_date_mapping.json` - New mapping file

---

## 📅 **Snapshot Date Mapping**

| Quarter | CSV File | `snapshot_at` Date | Notes |
|---------|----------|-------------------|-------|
| 2024 Q1 | `RIARepDataFeed_20240331.csv` | `2024-03-31` | Uses latest Q1 file (20240331 > 20240107) |
| 2024 Q2 | (None) | N/A | No file available |
| 2024 Q3 | `RIARepDataFeed_20240707.csv` | `2024-07-07` | Single file |
| 2024 Q4 | `RIARepDataFeed_20241006.csv` | `2024-10-06` | Single file |
| 2025 Q1 | `RIARepDataFeed_20250105.csv` | `2025-01-05` | Single file |
| 2025 Q2 | `RIARepDataFeed_20250406.csv` | `2025-04-06` | Single file |
| 2025 Q3 | `RIARepDataFeed_20250706.csv` | `2025-07-06` | Single file |
| 2025 Q4 | `RIARepDataFeed_20251005.csv` | `2025-10-05` | Single file |

**Reference**: See `config/v6_snapshot_date_mapping.json` for complete details.

---

## 🔍 **How It Works Now**

### **Example: Lead Contacted on March 31, 2024**

**Old Approach (Quarter-based):**
- Lead `contact_quarter` = `2024-01-01` (Q1 start)
- Snapshot `snapshot_quarter` = `2024-01-01` (Q1 start)
- Match: ✅ (but loses precision - March 31 snapshot might be more accurate)

**New Approach (Date-based):**
- Lead `contact_date` = `2024-03-31`
- Available snapshots: `2024-01-07`, `2024-03-31`
- Match: `snapshot_at = 2024-03-31` ✅ (most recent snapshot ≤ contact date)
- **Result**: Uses the exact snapshot from March 31, which is more accurate!

### **Example: Lead Contacted on April 1, 2024**

**Old Approach:**
- Lead `contact_quarter` = `2024-04-01` (Q2 start)
- Snapshot `snapshot_quarter` = `2024-01-01` (Q1) - **No match!** ❌

**New Approach:**
- Lead `contact_date` = `2024-04-01`
- Available snapshots: `2024-01-07`, `2024-03-31`, `2024-07-07`
- Match: `snapshot_at = 2024-03-31` ✅ (most recent snapshot ≤ contact date)
- **Result**: Uses the March 31 snapshot (most recent data available at that time)

---

## 🎯 **Benefits**

1. **More Accurate**: Uses actual snapshot dates, not quarter approximations
2. **Handles Edge Cases**: Naturally handles dates near quarter boundaries
3. **No Data Leakage**: Only uses snapshots that existed at or before contact date
4. **Flexible**: Can handle irregular snapshot schedules (e.g., missing Q2 2024)

---

## 📝 **Implementation Steps**

### **Step 1.5: Transform Raw CSV**
- Extract actual date from CSV filename (e.g., `20240331` → `DATE('2024-03-31')`)
- Set `snapshot_at = [SNAPSHOT_DATE]` in transformed tables
- Reference: `config/v6_snapshot_date_mapping.json` for correct dates

### **Step 1.6: Create Firm Snapshots**
- Use `MAX(snapshot_at)` from rep snapshots (all reps in same snapshot have same date)

### **Step 2: Create Master Views**
- Simply `SELECT *` from snapshot tables (no need to override `snapshot_at`)

### **Step 3.1: Point-in-Time Join**
- Use `QUALIFY` with `ROW_NUMBER()` to get most recent `snapshot_at <= contact_date`
- Join logic:
  ```sql
  WHERE reps.snapshot_at <= l.contact_date
  QUALIFY ROW_NUMBER() OVER (PARTITION BY RepCRD, contact_date ORDER BY snapshot_at DESC) = 1
  ```

---

## ✅ **Validation**

After implementing, verify:
- [ ] `snapshot_at` column exists in all snapshot tables
- [ ] `snapshot_at` dates match CSV filenames (see mapping file)
- [ ] No leads matched to future snapshots (leakage check)
- [ ] Leads use most recent snapshot ≤ contact date

---

## 📚 **Related Documents**

- `V6_Historical_Data_Processing_Guide.md` - Complete implementation guide
- `config/v6_snapshot_date_mapping.json` - Snapshot date mapping
- `config/v6_feature_contract.json` - Rep feature schema
- `config/v6_firm_feature_contract.json` - Firm feature schema

