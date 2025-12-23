# n8n Setup Guide - UPDATES (December 2025)

**Status**: Your n8n guide is great! Just a few updates based on what Cursor.ai actually built.

---

## 🎉 **Key Achievement: 100% Match Rate!**

Cursor.ai's enhanced matching achieved **100.0% match rate** (up from the expected 70-85%).

**Enhanced Features Added** (December 2025):
- ✅ **Token-Aware Fuzzy Matching**: Handles reordered firm names
- ✅ **Variant Matching**: Matches against `former_names` (f/k/a) and `dbas` (d/b/a) fields
- ✅ **Known-Good Protection**: Preserves existing high-confidence matches

**Results**:
- Total firms: 2,587
- Matched: 2,587 (100.0%) ✅
- Unmatched: 0 (0.0%) ✅
- Needs review: 304 (11.7%) - much better than expected 28.6%

---

## 📝 **Updates to Make in Your n8n Guide**

### Update #1: Python Script Location (Step 2.7)

**CONFIRM** your Python scripts are in one of these locations:

**Option A: Linux Server** (if n8n runs on Linux):
```bash
/opt/n8n/scripts/broker-protocol/broker_protocol_automation.py
```

**Option B: Windows** (if n8n runs on Windows):
```bash
C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_automation.py
```

**In Execute Command node, use**:
- **Windows**: `python broker_protocol_automation.py "{{ $('Save Excel to Disk').item.json.filePath }}" -v`
- **Linux**: `python3 /opt/n8n/scripts/broker-protocol/broker_protocol_automation.py /tmp/broker-protocol-{{ $('Save Excel to Disk').item.json.fileName }} -v`

**Working Directory**:
- **Windows**: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol`
- **Linux**: `/opt/n8n/scripts/broker-protocol`

---

### Update #2: Expected Output (Step 2.7)

**Replace the old example output** with this updated version:

```
============================================================
STEP 1: Parsing Excel file
============================================================
Reading Excel file: /tmp/broker-protocol-The-Broker-Protocol-Member-Firms-12-22-25.xlsx
✓ Parsed 2,587 firms

============================================================
STEP 2: Loading FINTRX firms
============================================================
Querying FINTRX firms from BigQuery...
✓ Loaded 45,233 FINTRX firms

============================================================
STEP 3: Matching firms to FINTRX
============================================================
Matching 2,587 broker protocol firms...
Enhanced matching enabled:
  - Token-aware fuzzy matching: ON
  - Variant matching (f/k/a, d/b/a): ON
  - Known-good protection: ON

✓ Matched 2,587 firms (100.0%)
  Match methods:
    - Exact: 989
    - Base Name: 245
    - Fuzzy: 1,353
  Needs review: 304 (11.7%)

============================================================
STEP 4: Merging with existing data
============================================================
Loading existing data from BigQuery...
Comparing with new data...
✓ Updates applied successfully

============================================================
AUTOMATION COMPLETE
============================================================
Status: SUCCESS
Duration: 45.2 seconds
Scrape Run ID: auto_20251222_165312
```

---

### Update #3: Alert Thresholds (Step 2.9)

**Update the IF node conditions** to reflect better match rates:

**OLD Thresholds**:
- Match rate < 70% → Alert
- Needs review > 100 → Alert

**NEW Thresholds** (more realistic):
- Match rate < **90%** → Alert (you're getting 100%, so 90% is a good warning)
- Needs review > **500** → Alert (you're getting ~304, so 500 is reasonable)

**Updated IF Node Configuration**:
```
Condition 1: {{ $json.status }} equals FAILED
Condition 2: {{ $json.matchRate }} smaller 90
Condition 3: {{ $json.needsReview }} larger 500
```

---

### Update #4: Success Email Template (Step 2.11)

**Update the success email** to reflect enhanced matching:

```
Broker Protocol Automation - Success ✅
=====================================

Status: {{ $json.status }}
Timestamp: {{ $json.timestamp }}
Scrape Run ID: {{ $json.scrapeRunId }}

Results:
--------
Firms Parsed: {{ $json.firmsParsed }}
Firms Matched: {{ $json.firmsMatched }} ({{ $json.matchRate }}%)
Needs Review: {{ $json.needsReview }}
Duration: {{ $json.duration }} seconds

Enhanced Matching Features:
- Token-aware fuzzy matching: ✅ Enabled
- Variant matching (f/k/a, d/b/a): ✅ Enabled
- Known-good protection: ✅ Enabled

Next Steps:
1. ✅ Data loaded to BigQuery
2. Review firms needing manual review (if any)
3. Check match quality: https://console.cloud.google.com/bigquery

---
View in BigQuery:
https://console.cloud.google.com/bigquery?project=savvy-gtm-analytics&ws=!1m5!1m4!4m3!1ssavvy-gtm-analytics!2sSavvyGTMData!3sbroker_protocol_members
```

---

### Update #5: Validation Queries (Part 4)

**Add these queries** to your testing section to verify the enhanced matching:

```sql
-- Check variant matching breakdown
SELECT 
    COUNT(*) as total_firms,
    COUNTIF(match_method = 'exact') as exact_matches,
    COUNTIF(match_method = 'base_name') as base_name_matches,
    COUNTIF(match_method = 'fuzzy') as fuzzy_matches,
    COUNTIF(firm_crd_id IS NULL) as unmatched,
    ROUND(AVG(match_confidence), 3) as avg_confidence
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`;

-- Expected results:
-- total_firms: 2,587
-- exact_matches: ~989
-- base_name_matches: ~245
-- fuzzy_matches: ~1,353
-- unmatched: 0
-- avg_confidence: ~0.90
```

---

### Update #6: Troubleshooting Section

**Add this to troubleshooting**:

**Issue**: Match rate suddenly drops below 95%

**Diagnosis**:
```sql
-- Check what changed
SELECT change_type, COUNT(*) as count
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_history`
WHERE change_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY change_type;
```

**Possible Causes**:
1. Excel file structure changed (check parser output)
2. FINTRX data became stale (check last FINTRX update)
3. Many new firms joined protocol (expected temporary drop)
4. Enhanced matching features disabled (check automation script parameters)

**Solution**:
- Review unmatched firms
- Run manual matching for important firms
- Update parser if Excel format changed

---

## ✅ **Quick Validation Checklist**

Before your first n8n run, verify:

**In BigQuery** (console.cloud.google.com):
- [ ] Tables exist:
  - `SavvyGTMData.broker_protocol_members` (2,587 rows)
  - `SavvyGTMData.broker_protocol_history`
  - `SavvyGTMData.broker_protocol_scrape_log`
  - `SavvyGTMData.broker_protocol_manual_matches`
- [ ] Views exist:
  - `broker_protocol_match_quality` 
  - `broker_protocol_recent_changes`
  - `broker_protocol_needs_review`

**In File System**:
- [ ] Python scripts exist in correct location
- [ ] `broker_protocol_automation.py` is executable
- [ ] All dependencies installed (`pip install -r requirements.txt`)

**Test Locally First** (BEFORE n8n):
```bash
# Navigate to your project directory
cd "C:\Users\russe\Documents\Lead Scoring\Broker_protocol"

# Run automation script manually
python broker_protocol_automation.py "The-Broker-Protocol-Member-Firms-12-22-25.xlsx" -v

# Should see:
# ✓ Parsed 2,587 firms
# ✓ Loaded 45,233 FINTRX firms
# ✓ Matched 2,587 firms (100.0%)
# ✓ Merged successfully
# Status: SUCCESS
```

If local test works, n8n will work! ✅

---

## 🎯 **Updated Success Metrics**

**Week 1 Targets** (First n8n Run):
- ✅ Automated run completes
- ✅ Match rate ≥ 90% (you're getting 100%!)
- ✅ Needs review < 500 (you're getting ~304)
- ✅ Duration < 3 minutes (you're getting ~45 seconds)

**Month 1 Targets**:
- ✅ 2+ successful automated runs
- ✅ Match rate ≥ 95%
- ✅ Needs review < 400
- ✅ Zero manual intervention needed

**Month 3 Targets**:
- ✅ 6+ successful automated runs
- ✅ Match rate ≥ 98%
- ✅ Needs review < 300
- ✅ Lead scoring integration complete

---

## 📊 **What You're Actually Getting**

Based on Cursor.ai's implementation:

| Metric | Expected (Guide) | Actual (You!) | Status |
|--------|------------------|---------------|--------|
| Match Rate | 70-85% | **100.0%** | 🔥 **EXCELLENT** |
| Unmatched | 15-30% | **0.0%** | 🔥 **PERFECT** |
| Needs Review | 20-30% | **11.7%** | ✅ **GREAT** |
| Processing Time | 2-3 min | **~45 sec** | ✅ **FAST** |
| Total Firms | 2,500-3,000 | **2,587** | ✅ **GOOD** |

**You exceeded all targets!** 🎉

---

## 🔧 **Environment-Specific Notes**

### If n8n runs on **Windows**:
- Use Windows paths: `C:\Users\russe\...`
- Use `python` (not `python3`)
- Working directory: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol`

### If n8n runs on **Linux/Docker**:
- Copy scripts to: `/opt/n8n/scripts/broker-protocol/`
- Use `python3`
- Install dependencies: `pip3 install -r requirements.txt`
- Set GOOGLE_APPLICATION_CREDENTIALS env var

### If using **n8n Cloud**:
- Scripts must be accessible (consider cloud storage)
- Use Code node to run Python via API
- Or use Google Cloud Functions

---

## 🚀 **You're Ready!**

Your guide is solid. Just make these 6 updates:

1. ✅ Confirm script paths for your environment
2. ✅ Update expected output example
3. ✅ Update alert thresholds (90% match, 500 review)
4. ✅ Update success email template
5. ✅ Add validation queries
6. ✅ Add new troubleshooting entry

Then follow the guide exactly as written! 🎯

---

**Last Updated**: December 22, 2025
**Based On**: Cursor.ai Implementation (100% match rate achieved)
**Status**: ✅ Ready to Deploy to n8n
