# V6 Temporal Matching Logic Clarification

## 🎯 **Key Question: How do we match Salesforce leads to discovery snapshots?**

### **Answer: Use Quarter Start Dates for Both**

**The Matching Logic:**
1. **Lead `contact_quarter`**: `DATE_TRUNC(DATE(Stage_Entered_Contacting__c), QUARTER)`
   - Always returns the **start of the quarter** (Jan 1, Apr 1, Jul 1, Oct 1)
   - Example: Lead contacted on **March 31, 2024** → `contact_quarter = 2024-01-01` (Q1 start)

2. **Snapshot `snapshot_quarter`**: Set to **start of the quarter** in Step 1.5
   - Example: `RIARepDataFeed_20240331.csv` → `snapshot_quarter = DATE('2024-01-01')` (Q1 start)
   - **Important**: Even though CSV is dated March 31 (end of Q1), it represents Q1 data

3. **Join Condition**: `l.contact_quarter = reps.snapshot_quarter`
   - Both are quarter start dates, so they match correctly ✅

---

## 📅 **Quarter Mapping Reference**

| CSV File Date | Quarter | `snapshot_quarter` | Example Lead Contact Date | `contact_quarter` | Match? |
|---------------|---------|-------------------|---------------------------|-------------------|--------|
| 2024-01-07 | Q1 2024 | 2024-01-01 | 2024-01-15 | 2024-01-01 | ✅ Yes |
| 2024-03-31 | Q1 2024 | 2024-01-01 | 2024-03-31 | 2024-01-01 | ✅ Yes |
| 2024-04-01 | Q2 2024 | 2024-04-01 | 2024-04-15 | 2024-04-01 | ✅ Yes |
| 2024-07-07 | Q3 2024 | 2024-07-01 | 2024-07-31 | 2024-07-01 | ✅ Yes |
| 2024-10-06 | Q4 2024 | 2024-10-01 | 2024-12-31 | 2024-10-01 | ✅ Yes |

**Key Insight**: The CSV file date (e.g., March 31) doesn't determine the quarter - the quarter itself does. Both March 31 and January 7 are in Q1, so both get `snapshot_quarter = 2024-01-01`.

---

## 🔍 **Edge Case: March 31 CSV (End of Q1)**

**Question**: `RIARepDataFeed_20240331.csv` is dated March 31 (technically Q1, but almost Q2). Should it match to Q1 or Q2?

**Answer**: **Q1** (snapshot_quarter = 2024-01-01)

**Why:**
1. March 31 is still in Q1 (Q1 = Jan 1 - Mar 31)
2. A lead contacted on March 31 would have `contact_quarter = 2024-01-01` (Q1 start)
3. The CSV represents data as of March 31, which is the end of Q1
4. For temporal correctness, we want: **"Lead contacted in Q1 → Use Q1 snapshot data"**
5. Therefore, the March 31 CSV should be assigned to Q1 snapshot

**Alternative (Wrong) Approach**: If we assigned March 31 CSV to Q2, then:
- Lead contacted on March 31 → `contact_quarter = 2024-01-01` (Q1)
- Snapshot → `snapshot_quarter = 2024-04-01` (Q2)
- **No match!** ❌ This would be incorrect.

---

## ✅ **Correct Implementation**

### **Step 1.2: Upload Raw CSV (No snapshot_quarter yet)**
- Upload `RIARepDataFeed_20240331.csv` → `snapshot_reps_2024_q1_raw`
- Map to Q1 based on date (March 31 is in Q1)

### **Step 1.5: Transform & Add snapshot_quarter**
```sql
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.snapshot_reps_2024_q1` AS
SELECT 
  -- ... all transformed columns ...
  DATE('2024-01-01') as snapshot_quarter  -- ⭐ Q1 START, regardless of CSV date
FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_2024_q1_raw`
```

### **Step 3.2: Point-in-Time Join**
```sql
WITH LeadsWithQuarter AS (
    SELECT 
        *,
        DATE_TRUNC(DATE(Stage_Entered_Contacting__c), QUARTER) as contact_quarter
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE Stage_Entered_Contacting__c IS NOT NULL
),
PointInTimeJoin AS (
    SELECT l.*, reps.*
    FROM LeadsWithQuarter l
    JOIN `LeadScoring.v_discovery_reps_all_vintages` reps
        ON l.FA_CRD__c = reps.RepCRD
       AND l.contact_quarter = reps.snapshot_quarter  -- ⭐ Both are quarter starts
)
```

---

## 📊 **Summary**

**Field Used for Matching:**
- **Lead side**: `contact_quarter = DATE_TRUNC(DATE(Stage_Entered_Contacting__c), QUARTER)`
- **Snapshot side**: `snapshot_quarter` (set to quarter start date in Step 1.5)
- **Join**: `contact_quarter = snapshot_quarter`

**Why This Works:**
- `DATE_TRUNC(..., QUARTER)` always returns quarter start (Jan 1, Apr 1, Jul 1, Oct 1)
- CSV files dated anywhere in a quarter (Jan 7, Mar 31, etc.) all represent that quarter's data
- Setting `snapshot_quarter` to quarter start ensures correct matching with `contact_quarter`

**No Data Leakage:**
- Lead contacted in Q1 → Only uses Q1 snapshot data ✅
- Lead contacted in Q2 → Only uses Q2 snapshot data ✅
- No future data is used ✅

