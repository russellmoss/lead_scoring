# Step 1.2: Quick Start Guide

## ✅ Prerequisites Checklist

Before running the upload script, verify:

1. **Python packages installed:**
   ```bash
   python -c "import pandas; import google.cloud.bigquery; print('✅ Packages OK')"
   ```
   If missing, install: `pip install pandas google-cloud-bigquery`

2. **BigQuery authentication set up:**
   - Option A: Application Default Credentials (recommended)
     ```bash
     gcloud auth application-default login
     ```
   - Option B: Service account key file
     - Set environment variable: `GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json`

3. **Good internet connection** (stable, won't timeout)
   - Uploads can take 5-30 minutes per file
   - Total time: ~40 minutes to 4 hours for all 8 files

4. **Files in correct location:**
   - Verify: `discovery_data/RIARepDataFeed*.csv` (8 files exist)

---

## 🚀 Run the Upload

**Simple command:**
```bash
cd "C:\Users\russe\Documents\Lead Scoring"
python step_1_2_upload_ria_reps_raw.py
```

**What it does:**
1. Finds all 8 RIARepDataFeed CSV files
2. Maps each to its quarter (handles duplicates by using latest date)
3. Uploads each to BigQuery staging tables:
   - `snapshot_reps_2024_q1_raw`
   - `snapshot_reps_2024_q3_raw`
   - `snapshot_reps_2024_q4_raw`
   - `snapshot_reps_2025_q1_raw`
   - `snapshot_reps_2025_q2_raw`
   - `snapshot_reps_2025_q3_raw`
   - `snapshot_reps_2025_q4_raw`

---

## 📊 What to Expect

**Progress output:**
```
[START] Uploading RIARepDataFeed_20240331.csv to snapshot_reps_2024_q1_raw
[INFO] File date: 20240331 → Quarter: 2024 Q1
[READ] Reading CSV file...
[SUCCESS] Successfully read 45,234 records with 124 columns
[UPLOAD] Uploading to BigQuery...
[WAIT] Waiting for upload to complete...
[SUCCESS] Successfully uploaded 45,234 rows to snapshot_reps_2024_q1_raw
```

**Time estimates:**
- Small files (<100MB): ~5-10 minutes each
- Medium files (100-200MB): ~10-20 minutes each
- Large files (>200MB): ~20-30 minutes each
- **Total: 40 minutes to 4 hours** (depending on file sizes)

---

## ⚠️ Troubleshooting

**If upload fails:**
1. **Authentication error:**
   ```
   DefaultCredentialsError: Could not automatically determine credentials
   ```
   → Run: `gcloud auth application-default login`

2. **Network timeout:**
   - Check internet connection
   - Files are large - may need to retry
   - Script will show which file failed

3. **File not found:**
   ```
   [ERROR] File discovery_data/RIARepDataFeed_XXXXXX.csv not found!
   ```
   → Verify files exist in `discovery_data/` folder

4. **Memory error:**
   - Large CSV files may need more RAM
   - Consider uploading one file at a time (modify script)

---

## ✅ After Completion

The script will print:
```
[COMPLETE] ✅ All 8 RIARepDataFeed files uploaded successfully!
```

**Next steps:**
1. Verify uploads in BigQuery Console
2. Run Step 1.3 validation checklist
3. Proceed to Step 1.5 (Transform Raw CSV to Standardized Schema)

---

## 🔍 Verify in BigQuery

After upload, verify in BigQuery Console:
```sql
SELECT 
  table_name,
  row_count,
  size_bytes
FROM `savvy-gtm-analytics.LeadScoring.INFORMATION_SCHEMA.TABLES`
WHERE table_name LIKE 'snapshot_reps_%_raw'
ORDER BY table_name;
```

Expected: 7 tables (or 8 if Q2 2024 exists) with row counts matching CSV files.

