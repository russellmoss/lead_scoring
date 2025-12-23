# Monitor Step 1.2 Uploads in Real-Time

## 🖥️ **Option 1: BigQuery Console (Recommended)**

Open BigQuery Console in your browser and run these queries:

### **1. Check Which Tables Are Created (Refresh Every 30-60 seconds)**

```sql
SELECT 
  table_name,
  row_count,
  ROUND(size_bytes / 1024 / 1024, 2) as size_mb,
  creation_time,
  CASE 
    WHEN table_name LIKE '%2024_q1%' THEN 'Q1 2024'
    WHEN table_name LIKE '%2024_q3%' THEN 'Q3 2024'
    WHEN table_name LIKE '%2024_q4%' THEN 'Q4 2024'
    WHEN table_name LIKE '%2025_q1%' THEN 'Q1 2025'
    WHEN table_name LIKE '%2025_q2%' THEN 'Q2 2025'
    WHEN table_name LIKE '%2025_q3%' THEN 'Q3 2025'
    WHEN table_name LIKE '%2025_q4%' THEN 'Q4 2025'
    ELSE 'Unknown'
  END as quarter
FROM `savvy-gtm-analytics.LeadScoring.INFORMATION_SCHEMA.TABLES`
WHERE table_name LIKE 'snapshot_reps_%_raw'
ORDER BY creation_time DESC;
```

### **2. Check Row Counts for Each Table**

```sql
SELECT 
  'snapshot_reps_2024_q1_raw' as table_name,
  COUNT(*) as row_count
FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_2024_q1_raw`
UNION ALL
SELECT 'snapshot_reps_2024_q3_raw', COUNT(*) FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_2024_q3_raw`
UNION ALL
SELECT 'snapshot_reps_2024_q4_raw', COUNT(*) FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_2024_q4_raw`
UNION ALL
SELECT 'snapshot_reps_2025_q1_raw', COUNT(*) FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_2025_q1_raw`
UNION ALL
SELECT 'snapshot_reps_2025_q2_raw', COUNT(*) FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_2025_q2_raw`
UNION ALL
SELECT 'snapshot_reps_2025_q3_raw', COUNT(*) FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_2025_q3_raw`
UNION ALL
SELECT 'snapshot_reps_2025_q4_raw', COUNT(*) FROM `savvy-gtm-analytics.LeadScoring.snapshot_reps_2025_q4_raw`
ORDER BY table_name;
```

**Note:** This will only work once tables are created. If a table doesn't exist yet, remove that line.

### **3. Check Table Size and Status**

```sql
SELECT 
  table_name,
  row_count,
  ROUND(size_bytes / 1024 / 1024, 2) as size_mb,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), creation_time, SECOND) as seconds_ago,
  CASE 
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_modified_time, SECOND) < 60 THEN '🔄 Uploading...'
    ELSE '✅ Complete'
  END as status
FROM `savvy-gtm-analytics.LeadScoring.INFORMATION_SCHEMA.TABLES`
WHERE table_name LIKE 'snapshot_reps_%_raw'
ORDER BY last_modified_time DESC;
```

---

## 💻 **Option 2: Terminal (bq CLI)**

If you have `bq` command-line tool installed:

### **1. List All Uploaded Tables**

```bash
bq ls --dataset_id=LeadScoring --format=prettyjson | grep -A 5 "snapshot_reps.*_raw"
```

### **2. Check Row Count for Specific Table**

```bash
# Replace with actual table name
bq query --use_legacy_sql=false "SELECT COUNT(*) as row_count FROM \`savvy-gtm-analytics.LeadScoring.snapshot_reps_2024_q1_raw\`"
```

### **3. Monitor All Tables (Refresh Every 30 seconds)**

```bash
# Run this in a loop (Ctrl+C to stop)
while true; do
  echo "=== $(date) ==="
  bq query --use_legacy_sql=false --format=pretty "
    SELECT 
      table_name,
      row_count,
      ROUND(size_bytes / 1024 / 1024, 2) as size_mb
    FROM \`savvy-gtm-analytics.LeadScoring.INFORMATION_SCHEMA.TABLES\`
    WHERE table_name LIKE 'snapshot_reps_%_raw'
    ORDER BY table_name
  "
  echo ""
  sleep 30
done
```

---

## 📊 **Option 3: Python Monitoring Script**

Create a simple monitoring script:

```python
# monitor_uploads.py
from google.cloud import bigquery
import time
from datetime import datetime

client = bigquery.Client(project="savvy-gtm-analytics")

tables = [
    "snapshot_reps_2024_q1_raw",
    "snapshot_reps_2024_q3_raw",
    "snapshot_reps_2024_q4_raw",
    "snapshot_reps_2025_q1_raw",
    "snapshot_reps_2025_q2_raw",
    "snapshot_reps_2025_q3_raw",
    "snapshot_reps_2025_q4_raw",
]

print("Monitoring upload progress... (Press Ctrl+C to stop)\n")

while True:
    print(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    for table_name in tables:
        try:
            table = client.get_table(f"savvy-gtm-analytics.LeadScoring.{table_name}")
            size_mb = table.num_bytes / 1024 / 1024
            print(f"✅ {table_name:35} | {table.num_rows:>10,} rows | {size_mb:>8.2f} MB")
        except Exception as e:
            if "Not found" in str(e):
                print(f"⏳ {table_name:35} | Not created yet...")
            else:
                print(f"❌ {table_name:35} | Error: {e}")
    
    time.sleep(30)  # Refresh every 30 seconds
```

**Run in another terminal:**
```bash
python monitor_uploads.py
```

---

## 🎯 **What to Look For**

### **Normal Progress:**
- Tables appear one by one as uploads complete
- Row counts increase (if table is still uploading)
- Size increases gradually

### **Upload Complete:**
- All 7 tables (or 8 if Q2 2024 exists) are created
- Row counts match expected CSV row counts
- `last_modified_time` stops changing

### **Potential Issues:**
- **Table stuck at 0 rows**: Upload might have failed
- **Table missing after 30+ minutes**: Check Python script output for errors
- **Size much smaller than expected**: Check if upload was truncated

---

## 📝 **Expected Results**

After all uploads complete, you should see:

| Table Name | Expected Status |
|------------|----------------|
| `snapshot_reps_2024_q1_raw` | ✅ Created |
| `snapshot_reps_2024_q3_raw` | ✅ Created |
| `snapshot_reps_2024_q4_raw` | ✅ Created |
| `snapshot_reps_2025_q1_raw` | ✅ Created |
| `snapshot_reps_2025_q2_raw` | ✅ Created |
| `snapshot_reps_2025_q3_raw` | ✅ Created |
| `snapshot_reps_2025_q4_raw` | ✅ Created |

**Total: 7 tables** (assuming no Q2 2024 file)

---

## 🔍 **Quick Check Script**

Run this once to see current status:

```bash
bq query --use_legacy_sql=false --format=table "
SELECT 
  table_name,
  row_count,
  ROUND(size_bytes / 1024 / 1024, 2) as size_mb,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), creation_time, MINUTE) as minutes_ago
FROM \`savvy-gtm-analytics.LeadScoring.INFORMATION_SCHEMA.TABLES\`
WHERE table_name LIKE 'snapshot_reps_%_raw'
ORDER BY table_name
"
```

