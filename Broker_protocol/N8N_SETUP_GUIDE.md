# Broker Protocol Automation - n8n Workflow Setup Guide

**Purpose**: This guide walks you through setting up the n8n workflow to automatically download, process, and load Broker Protocol data every 2 weeks.

**Prerequisites**:
- Cursor.ai has completed all BigQuery tables and Python scripts ✅
- n8n installed (cloud or self-hosted) ✅
- ~~Google Cloud credentials available~~ **NOT NEEDED** - Python script handles this ✅
- Email/SMTP credentials available ✅
- Python scripts accessible from n8n environment ✅

**Estimated Time**: 2-3 hours for first-time setup

---

## 📋 Overview

The n8n workflow will:
1. **Trigger** every 2 weeks (1st and 15th of month at 9 AM ET)
2. **Download** Excel file from JSHeld website
3. **Process** data using Python scripts with enhanced matching
4. **Load** to BigQuery
5. **Alert** if errors or high review count

**Enhanced Matching Features** (December 2025):
- ✅ **Token-Aware Fuzzy Matching**: Handles reordered firm names
- ✅ **Variant Matching**: Matches against `former_names` (f/k/a) and `dbas` (d/b/a) fields
- ✅ **Known-Good Protection**: Preserves existing high-confidence matches

**Expected Performance**:
- Match Rate: **100.0%** (all firms matched)
- Needs Review: **~11.7%** (firms requiring manual verification)
- Processing Time: **~45 seconds**

---

## 🔧 Part 1: n8n Environment Setup

### Step 1.1: Install Required Nodes

In your n8n instance, ensure these nodes are available:

**Core Nodes** (usually pre-installed):
- ✅ Schedule Trigger
- ✅ HTTP Request
- ✅ Execute Command
- ✅ IF
- ✅ Send Email
- ✅ Set

**Additional Nodes** (install if needed):
- Google BigQuery (optional, for manual queries - not needed for automation)
- Slack (optional, for alerts)

**To Install a Node**:
1. Click "Settings" (gear icon) in n8n
2. Go to "Community Nodes"
3. Search for node name
4. Click "Install"

---

### Step 1.2: Set Up Credentials

#### Skip Google Cloud Credentials ✅

**You do NOT need to configure Google Cloud credentials in n8n!**

**Why?** 
- Your Python automation script (`broker_protocol_automation.py`) already handles BigQuery authentication
- The script uses `gcloud-user-credentials.json` in your project folder
- When n8n runs the Python script, it will authenticate automatically
- No need for n8n to authenticate separately

**What you already have:**
- ✅ Credentials file: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\gcloud-user-credentials.json`
- ✅ Config file points to it: `config.py` → `GCP_SERVICE_ACCOUNT_KEY`
- ✅ Python script loads it automatically

**If authentication fails** when you test the workflow:
1. Check that `gcloud-user-credentials.json` exists in your project folder
2. Verify `config.py` has the correct path
3. Test locally: `python broker_protocol_automation.py test.xlsx -v`
4. Only if local test works but n8n fails, then configure Google credentials in n8n

**For now: Skip this and move to Email credentials.** ⬇️

#### Email Credentials (for alerts)

1. Click "Add Credential"
2. Search for "SMTP"
3. Fill in your email server details:
   - **Host**: smtp.gmail.com (or your SMTP server)
   - **Port**: 587
   - **User**: russell.moss@savvywealth.com
   - **Password**: your-app-password
   - **Encryption**: STARTTLS
4. Name it: "Company Email Alerts"
5. Click "Create"

---

### Step 1.3: Verify Python Authentication

Before building the workflow, verify that your Python script can authenticate to BigQuery:

```powershell
# Navigate to project folder
cd "C:\Users\russe\Documents\Lead Scoring\Broker_protocol"

# Check credentials file exists
if (Test-Path "gcloud-user-credentials.json") {
    Write-Host "✅ Credentials file exists" -ForegroundColor Green
} else {
    Write-Host "❌ Missing gcloud-user-credentials.json" -ForegroundColor Red
    Write-Host "Run: gcloud auth application-default login" -ForegroundColor Yellow
}

# Test BigQuery connection
python -c "from google.cloud import bigquery; client = bigquery.Client(project='savvy-gtm-analytics'); print('✅ BigQuery authentication successful!')"
```

**Expected output**: `✅ BigQuery authentication successful!`

**If it fails**:
- Run `gcloud auth application-default login`
- Copy the credentials to your project folder as `gcloud-user-credentials.json`
- Update `config.py` to point to it

**Once this works, proceed to building the n8n workflow.** ⬇️

---

### Step 1.4: Set Up Python Environment (if self-hosted n8n)

If running n8n on your own server, ensure Python scripts are accessible:

**Option A: Windows n8n Installation**
- Scripts location: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\`
- Python command: `python` (not `python3`)
- Working directory: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol`
- Install dependencies:
  ```powershell
  pip install pandas openpyxl python-dateutil google-cloud-bigquery
  ```

**Option B: Linux/Docker n8n Installation**
- Scripts location: `/opt/n8n/scripts/broker-protocol/`
- Python command: `python3`
- Working directory: `/opt/n8n/scripts/broker-protocol`
- Copy scripts from Windows to Linux:
  ```bash
  # Copy Python scripts from local Windows machine to n8n-accessible location
  # (Use SCP, SFTP, or file share to transfer from Windows to Linux server)
  mkdir -p /opt/n8n/scripts/broker-protocol
  cp broker_protocol_parser.py /opt/n8n/scripts/broker-protocol/
  cp firm_matcher.py /opt/n8n/scripts/broker-protocol/
  cp broker_protocol_updater.py /opt/n8n/scripts/broker-protocol/
  cp broker_protocol_automation.py /opt/n8n/scripts/broker-protocol/
  
  # Install dependencies
  pip3 install pandas openpyxl python-dateutil google-cloud-bigquery --break-system-packages
  ```

**For n8n Cloud**: You'll need to use Code node with Execute Command pointing to a cloud function (see Alternative Setup section).

**Local Development Path**: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\`

---

## 🔨 Part 2: Build the n8n Workflow

### Step 2.1: Create New Workflow

1. In n8n, click "**Workflows**" in left sidebar
2. Click "**Add Workflow**"
3. Name it: "**Broker Protocol Automation**"
4. Description: "Automated scraping and processing of Broker Protocol member list every 2 weeks"

---

### Step 2.2: Add Schedule Trigger

This triggers the workflow every 2 weeks.

1. **Add Node**:
   - Click "+" button
   - Search for "Schedule Trigger"
   - Click to add

2. **Configure**:
   - **Trigger Interval**: Cron
   - **Cron Expression**: `0 9 1,15 * *`
     - This means: "At 9:00 AM on the 1st and 15th of every month"
   - **Timezone**: America/New_York (ET)

3. **Test**:
   - Click "Execute Node"
   - Should see: "Node executed successfully"

**⚠️ Important**: The cron expression `0 9 1,15 * *` runs at 9:00 AM ET on the 1st and 15th of each month. Adjust if you want different timing.

---

### Step 2.3: Add HTTP Request (Get Page HTML)

This node fetches the Broker Protocol webpage.

1. **Add Node**:
   - Click "+" after Schedule Trigger
   - Search "HTTP Request"
   - Click to add

2. **Configure**:
   - **Node Name**: "Fetch Broker Protocol Page"
   - **Method**: GET
   - **URL**: `https://www.jsheld.com/markets-served/financial-services/broker-recruiting/the-broker-protocol`
   - **Authentication**: None
   - **Options** → Response:
     - **Response Format**: String
     - **Full Response**: OFF

3. **Test**:
   - Click "Execute Node"
   - Should see HTML content in output

---

### Step 2.4: Add Code Node (Extract XLSX URL)

This node parses the HTML to find the Excel download link.

1. **Add Node**:
   - Click "+" after HTTP Request
   - Search "Code"
   - Click to add

2. **Configure**:
   - **Node Name**: "Extract XLSX URL"
   - **Language**: JavaScript
   - **Mode**: Run Once for All Items

3. **Paste this code**:

```javascript
// Extract XLSX link from HTML
const html = $input.all()[0].json.data;

// Find XLSX links
const xlsxRegex = /href="([^"]*\.xlsx[^"]*)"/gi;
const matches = [...html.matchAll(xlsxRegex)];

if (matches.length === 0) {
  throw new Error('No XLSX file found on page. Website structure may have changed.');
}

// Find the specific Broker Protocol member firms file
let xlsxUrl = null;
let fileName = null;

for (const match of matches) {
  let url = match[1];
  
  // Check if it's the member firms file
  if (url.toLowerCase().includes('broker') && 
      url.toLowerCase().includes('protocol') && 
      url.toLowerCase().includes('member')) {
    
    // Handle relative URLs
    if (!url.startsWith('http')) {
      url = new URL(url, 'https://www.jsheld.com').href;
    }
    
    xlsxUrl = url;
    fileName = url.split('/').pop().split('?')[0];
    break;
  }
}

if (!xlsxUrl) {
  // Fallback: use first XLSX found
  let url = matches[0][1];
  if (!url.startsWith('http')) {
    url = new URL(url, 'https://www.jsheld.com').href;
  }
  xlsxUrl = url;
  fileName = url.split('/').pop().split('?')[0];
}

return [
  {
    json: {
      xlsxUrl: xlsxUrl,
      fileName: fileName,
      timestamp: new Date().toISOString()
    }
  }
];
```

4. **Test**:
   - Click "Execute Node"
   - Should see output with `xlsxUrl` and `fileName`
   - Example output:
     ```json
     {
       "xlsxUrl": "https://www.jsheld.com/uploads/...",
       "fileName": "TheBrokerProtocolMemberFirms122225.xlsx",
       "timestamp": "2025-12-22T14:00:00.000Z"
     }
     ```

---

### Step 2.5: Add HTTP Request (Download XLSX)

This node downloads the Excel file.

1. **Add Node**:
   - Click "+" after Code node
   - Search "HTTP Request"
   - Click to add

2. **Configure**:
   - **Node Name**: "Download Excel File"
   - **Method**: GET
   - **URL**: `={{ $json.xlsxUrl }}`
     - ⚠️ Click the small chain link icon to enable expressions
     - This uses the URL from previous node
   - **Authentication**: None
   - **Options** → Response:
     - **Response Format**: File
     - **Put Output in Field**: data
     - **Binary Property**: data

3. **Test**:
   - Click "Execute Node"
   - Should see binary data in output
   - Check "Binary Data" tab to confirm Excel file

---

### Step 2.6: Add Write Binary File Node (Save Excel)

This node saves the downloaded Excel to disk for Python processing.

1. **Add Node**:
   - Click "+" after Download Excel
   - Search "Write Binary File"
   - Click to add

2. **Configure**:
   - **Node Name**: "Save Excel to Disk"
   - **File Path**: `/tmp/broker-protocol-{{ $json.fileName }}`
     - ⚠️ Enable expressions (chain link icon)
     - This saves to `/tmp/` with the filename from earlier
   - **Binary Property**: data

3. **Test**:
   - Click "Execute Node"
   - Should see success message
   - File is now saved to `/tmp/`

---

### Step 2.7: Add Execute Command (Run Python Automation)

This node runs the complete Python automation script.

1. **Add Node**:
   - Click "+" after Write Binary File
   - Search "Execute Command"
   - Click to add

2. **Configure**:
   - **Node Name**: "Run Python Automation"
   
   **For Linux Server** (if n8n runs on Linux):
   - **Command**: `python3`
   - **Arguments**:
     ```
     /opt/n8n/scripts/broker-protocol/broker_protocol_automation.py
     /tmp/broker-protocol-{{ $('Save Excel to Disk').item.json.fileName }}
     -v
     ```
     - ⚠️ Enable expressions for the file path
   - **Advanced Options**:
     - **Timeout**: 600000 (10 minutes)
     - **Working Directory**: /opt/n8n/scripts/broker-protocol
   
   **For Windows** (if n8n runs on Windows):
   - **Command**: `python`
   - **Arguments**:
     ```
     broker_protocol_automation.py
     "{{ $('Save Excel to Disk').item.json.filePath }}"
     -v
     ```
     - ⚠️ Enable expressions for the file path
   - **Advanced Options**:
     - **Timeout**: 600000 (10 minutes)
     - **Working Directory**: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol`

**Note on Authentication**:
- This node does NOT need Google Cloud credentials configured in n8n
- The Python script handles BigQuery authentication automatically
- Make sure `gcloud-user-credentials.json` exists in your project folder
- The script will use that file for authentication
- If authentication fails, see troubleshooting section below

3. **Test**:
   - Click "Execute Node"
   - Should see Python output in stdout
   - Check for "AUTOMATION COMPLETE" message
   - If errors, check stderr output

**Expected Output**:
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

### Step 2.8: Add Code Node (Parse Python Output)

This node extracts key metrics from Python output.

1. **Add Node**:
   - Click "+" after Execute Command
   - Search "Code"
   - Click to add

2. **Configure**:
   - **Node Name**: "Parse Results"
   - **Language**: JavaScript
   - **Mode**: Run Once for All Items

3. **Paste this code**:

```javascript
// Extract results from Python stdout
const stdout = $input.all()[0].json.stdout || '';
const stderr = $input.all()[0].json.stderr || '';

// Parse metrics from output
const parseMetric = (text, pattern) => {
  const match = text.match(pattern);
  return match ? match[1] : null;
};

const results = {
  status: stdout.includes('AUTOMATION COMPLETE') && stdout.includes('SUCCESS') ? 'SUCCESS' : 'FAILED',
  firmsParsed: parseMetric(stdout, /Parsed (\d+) firms/),
  firmsMatched: parseMetric(stdout, /Matched (\d+) firms/),
  matchRate: parseMetric(stdout, /Matched \d+ firms \(([0-9.]+)%\)/),
  needsReview: parseMetric(stdout, /Needs review: (\d+)/),
  duration: parseMetric(stdout, /Duration: ([0-9.]+) seconds/),
  scrapeRunId: parseMetric(stdout, /Scrape Run ID: (.+)/),
  timestamp: new Date().toISOString(),
  hasErrors: stderr.length > 0,
  errorMessage: stderr.substring(0, 500)
};

// Convert to numbers
if (results.firmsParsed) results.firmsParsed = parseInt(results.firmsParsed);
if (results.firmsMatched) results.firmsMatched = parseInt(results.firmsMatched);
if (results.matchRate) results.matchRate = parseFloat(results.matchRate);
if (results.needsReview) results.needsReview = parseInt(results.needsReview);
if (results.duration) results.duration = parseFloat(results.duration);

return [{ json: results }];
```

4. **Test**:
   - Click "Execute Node"
   - Should see parsed metrics in output

---

### Step 2.9: Add IF Node (Check for Issues)

This node determines if we need to send an alert.

1. **Add Node**:
   - Click "+" after Parse Results
   - Search "IF"
   - Click to add

2. **Configure**:
   - **Node Name**: "Check for Issues"
   - **Conditions**:
     - **Condition 1**:
       - Value 1: `={{ $json.status }}`
       - Operation: equals
       - Value 2: FAILED
     - Click "Add Condition" (OR operator)
     - **Condition 2**:
       - Value 1: `={{ $json.matchRate }}`
       - Operation: smaller
       - Value 2: 90
     - Click "Add Condition" (OR)
     - **Condition 3**:
       - Value 1: `={{ $json.needsReview }}`
       - Operation: larger
       - Value 2: 500

3. **Logic**: Send alert if:
   - Status is FAILED, OR
   - Match rate is < 90%, OR
   - More than 500 firms need review

---

### Step 2.10: Add Send Email (Alert - TRUE Branch)

This sends an alert if issues were found.

1. **Connect to TRUE output** of IF node
2. **Add Node**:
   - Search "Send Email"
   - Click to add

3. **Configure**:
   - **Node Name**: "Send Alert Email"
   - **Credentials**: Select "Company Email Alerts"
   - **From Email**: russell.moss@savvywealth.com
   - **To Email**: russell.moss@savvywealth.com (comma-separated for multiple)
   - **Subject**: `⚠️ Broker Protocol Automation Alert - {{ $json.status }}`
     - ⚠️ Enable expressions
   - **Email Type**: Text
   - **Text**: Paste this template:

```
Broker Protocol Automation Alert
=================================

Status: {{ $json.status }}
Timestamp: {{ $json.timestamp }}
Scrape Run ID: {{ $json.scrapeRunId }}

Metrics:
--------
Firms Parsed: {{ $json.firmsParsed }}
Firms Matched: {{ $json.firmsMatched }}
Match Rate: {{ $json.matchRate }}%
Needs Review: {{ $json.needsReview }}
Duration: {{ $json.duration }} seconds

{% if $json.status == "FAILED" %}
❌ AUTOMATION FAILED

Error Message:
{{ $json.errorMessage }}

Action Required:
1. Check n8n workflow logs
2. Check Python script logs in BigQuery
3. Run manual process if needed
{% endif %}

{% if $json.matchRate < 90 %}
⚠️ LOW MATCH RATE (< 90%)

Action Required:
1. Review unmatched firms in BigQuery
2. Check for website structure changes
3. Adjust matching threshold if needed
{% endif %}

{% if $json.needsReview > 500 %}
⚠️ HIGH REVIEW COUNT (> 500 firms)

Action Required:
1. Schedule manual review session
2. Prioritize by firm AUM
3. Update manual matches table
{% endif %}

---
Check workflow: [n8n URL]
Check BigQuery: https://console.cloud.google.com/bigquery?project=savvy-gtm-analytics
```

4. **Test** (if you want to test alert):
   - Temporarily change IF condition to always TRUE
   - Execute node
   - Check email inbox
   - Revert IF condition

---

### Step 2.11: Add Send Email (Success - FALSE Branch)

This sends a success notification (optional, but recommended).

1. **Connect to FALSE output** of IF node
2. **Add Node**:
   - Search "Send Email"
   - Click to add

3. **Configure**:
   - **Node Name**: "Send Success Email"
   - **Credentials**: Select "Company Email Alerts"
   - **From Email**: russell.moss@savvywealth.com
   - **To Email**: russell.moss@savvywealth.com
   - **Subject**: `✅ Broker Protocol Automation Complete`
   - **Email Type**: Text
   - **Text**: Paste this template:

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

### Step 2.12: Save Workflow

1. Click "**Save**" button (top right)
2. Workflow is now saved
3. It will run automatically on schedule

---

## ✅ Part 2.13: Pre-Deployment Validation Checklist

Before your first n8n run, verify:

**In BigQuery** (console.cloud.google.com):
- [ ] Tables exist:
  - `SavvyGTMData.broker_protocol_members` (should have ~2,587 rows)
  - `SavvyGTMData.broker_protocol_history`
  - `SavvyGTMData.broker_protocol_scrape_log`
  - `SavvyGTMData.broker_protocol_manual_matches`
- [ ] Views exist:
  - `broker_protocol_match_quality` 
  - `broker_protocol_recent_changes`
  - `broker_protocol_needs_review`

**In File System**:
- [ ] Python scripts exist in correct location
  - **Windows**: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_automation.py`
  - **Linux**: `/opt/n8n/scripts/broker-protocol/broker_protocol_automation.py`
- [ ] `broker_protocol_automation.py` is executable
- [ ] All dependencies installed (`pip install pandas openpyxl python-dateutil google-cloud-bigquery`)

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

## 🧪 Part 3: Testing the Workflow

### Step 3.1: Test Full Workflow

1. **Disable Schedule Trigger** (temporarily):
   - Click on Schedule Trigger node
   - Click the toggle to disable it
   - This prevents accidental scheduled runs during testing

2. **Execute Workflow Manually**:
   - Click "**Execute Workflow**" button (top right)
   - Watch each node execute in sequence
   - Check output of each node

3. **Common Issues**:

   **Issue**: "File not found" error
   **Solution**: Check file path in Execute Command node

   **Issue**: Python script errors
   **Solution**: Check Python dependencies installed, check file permissions

   **Issue**: BigQuery permission errors
   **Solution**: Verify `gcloud-user-credentials.json` exists and has correct permissions (see troubleshooting section)

   **Issue**: Email not sending
   **Solution**: Check SMTP credentials, check firewall rules

---

### Step 3.2: Validate Results in BigQuery

After successful run, check data in BigQuery:

```sql
-- Check last scrape
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log`
ORDER BY scrape_timestamp DESC LIMIT 1;

-- Check match quality
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_match_quality`;

-- Check recent changes
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_recent_changes`
LIMIT 10;

-- Check variant matching breakdown
SELECT 
    COUNT(*) as total_firms,
    COUNTIF(match_method = 'exact') as exact_matches,
    COUNTIF(match_method = 'base_name') as base_name_matches,
    COUNTIF(match_method = 'fuzzy') as fuzzy_matches,
    COUNTIF(firm_crd_id IS NULL) as unmatched,
    ROUND(AVG(match_confidence), 3) as avg_confidence
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`;
```

**Expected Results**:
- Scrape log entry with status = SUCCESS
- Match quality showing ≥90% match rate (typically 100% with enhanced matching)
- Some changes detected (if re-running)
- Variant matching breakdown:
  - total_firms: ~2,587
  - exact_matches: ~989
  - base_name_matches: ~245
  - fuzzy_matches: ~1,353
  - unmatched: 0
  - avg_confidence: ~0.90

---

### Step 3.3: Test Error Handling

Test that alerts work correctly.

1. **Create a test failure**:
   - Temporarily modify Execute Command to run non-existent script
   - Execute workflow
   - Should trigger error alert email

2. **Verify**:
   - Check email for alert
   - Check IF node routed to TRUE branch
   - Check error details in email

3. **Revert changes**:
   - Fix Execute Command back to correct script
   - Test again - should go to FALSE branch (success)

---

### Step 3.4: Enable Schedule

Once testing is complete:

1. Click on Schedule Trigger node
2. Toggle it back ON
3. Click "Save"
4. Workflow will now run automatically every 2 weeks

---

## ðŸ"§ Part 4: Optional Enhancements

### Enhancement 1: Slack Notifications

Instead of email, send to Slack.

1. **Add Slack credential**:
   - Get Slack Webhook URL from Slack admin
   - Add as credential in n8n

2. **Replace Send Email nodes** with Slack nodes:
   - Same inputs (subject → message title, text → message body)
   - Format message as Slack markdown

---

### Enhancement 2: Manual Review Dashboard

Create a simple dashboard to review unmatched firms.

1. **Add HTTP Request node** (after Parse Results):
   - **URL**: Your dashboard URL
   - **Method**: POST
   - **Body**: `={{ $json }}`
   - This sends results to your dashboard

2. **Dashboard** (separate project):
   - Simple web app that displays unmatched firms
   - Allows quick approve/reject decisions
   - Updates BigQuery manual matches table

---

### Enhancement 3: Data Quality Checks

Add additional validation before merging.

1. **Add Code node** (after Parse Results, before IF):
   - Check for unexpected data patterns
   - Validate date ranges
   - Check for duplicate firm names

2. **Extend IF node**:
   - Add condition for data quality failures
   - Send different alert for data issues

---

### Enhancement 4: Backup Excel Files

Keep a backup of each Excel file downloaded.

1. **Add Google Drive node** (after Download Excel):
   - **Operation**: Upload
   - **File**: Binary data from download
   - **Folder**: Broker Protocol Backups
   - **Filename**: `BrokerProtocol_{{ $json.timestamp }}.xlsx`

---

## ðŸ" Part 5: Monitoring & Maintenance

### Daily Checks (Automated)

These should happen automatically:
- ✅ Workflow runs on schedule
- ✅ Email notifications sent
- ✅ Data loaded to BigQuery

### Weekly Checks (Manual - 10 minutes)

1. **Check Last Run**:
   ```sql
   SELECT * FROM broker_protocol_scrape_log 
   ORDER BY scrape_timestamp DESC LIMIT 3;
   ```
   - Verify recent runs succeeded
   - Check match rate stayed ≥90%

2. **Review Unmatched Firms**:
   ```sql
   SELECT * FROM broker_protocol_needs_review LIMIT 20;
   ```
   - Prioritize by AUM
   - Add manual matches for important firms

3. **Check for Changes**:
   ```sql
   SELECT * FROM broker_protocol_recent_changes 
   WHERE detected_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);
   ```
   - Note any large firms joining/withdrawing

### Monthly Checks (Manual - 30 minutes)

1. **Review Match Quality Trends**:
   - Check if match rate improving or declining
   - Identify systematic matching issues
   - Refine matching rules if needed

2. **Manual Review Session**:
   - Schedule 30-minute session
   - Review top 50 unmatched firms by AUM
   - Add manual matches
   - Update needs_manual_review flags

3. **Validate Data Usage**:
   - Check that broker protocol data is being used in lead scoring
   - Validate join to contacts works correctly
   - Measure impact on lead quality

---

## ❓ Troubleshooting

### Issue: Workflow Not Triggering

**Symptoms**: No email notifications on schedule day

**Diagnosis**:
1. Check Schedule Trigger is enabled (toggle ON)
2. Check cron expression is correct
3. Check n8n execution logs

**Solution**:
- Verify timezone is correct (America/New_York)
- Test with more frequent schedule (every 5 minutes) temporarily
- Check n8n service is running

---

### Issue: Excel Download Fails

**Symptoms**: "No XLSX file found" error

**Diagnosis**:
1. Website structure may have changed
2. URL pattern changed
3. File moved to different location

**Solution**:
1. Visit website manually: https://www.jsheld.com/markets-served/financial-services/broker-recruiting/the-broker-protocol
2. Check if Excel file is still there
3. Check URL pattern
4. Update "Extract XLSX URL" code node if needed
5. Contact JSHeld if file is no longer publicly available

---

### Issue: Python Script Fails

**Symptoms**: "ModuleNotFoundError" or other Python errors

**Diagnosis**:
1. Missing Python dependencies
2. Wrong file paths
3. Permission issues

**Solution**:
```bash
# Reinstall dependencies
pip3 install pandas openpyxl python-dateutil google-cloud-bigquery --break-system-packages

# Check file permissions
ls -la /opt/n8n/scripts/broker-protocol/

# Test script manually
python3 /opt/n8n/scripts/broker-protocol/broker_protocol_automation.py /tmp/test.xlsx -v
```

---

### Issue: Low Match Rate

**Symptoms**: Match rate suddenly drops below 95%

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
1. Check FINTRX export is complete:
   ```sql
   SELECT COUNT(*) FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` WHERE NAME IS NOT NULL;
   ```
   Should be ~45,000 firms

2. Check for systematic issues:
   - Review unmatched firms
   - Look for patterns (e.g., all LLC firms failing)

3. Verify enhanced matching is enabled:
   - Check Python script output for "Enhanced matching enabled"
   - Ensure token-aware fuzzy matching is ON
   - Ensure variant matching (f/k/a, d/b/a) is ON

4. Review unmatched firms and add manual matches for important firms

5. Update parser if Excel format changed

---

### Issue: BigQuery Authentication Errors

**Symptoms**:
- Python script fails with "Could not automatically determine credentials"
- Error mentions "GOOGLE_APPLICATION_CREDENTIALS"
- Authentication errors in n8n Execute Command output

**Diagnosis**:
```powershell
# Check if credentials file exists
Test-Path "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\gcloud-user-credentials.json"

# Check config.py points to it
Get-Content config.py | Select-String "GCP_SERVICE_ACCOUNT_KEY"

# Test authentication locally
cd "C:\Users\russe\Documents\Lead Scoring\Broker_protocol"
python -c "from google.cloud import bigquery; client = bigquery.Client(project='savvy-gtm-analytics'); print('Auth works!')"
```

**Solution**:
1. **Verify credentials file exists** in project folder:
   ```powershell
   Test-Path "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\gcloud-user-credentials.json"
   ```
   Should return `True`

2. **Update config.py** if needed:
   ```python
   GCP_SERVICE_ACCOUNT_KEY = str(PROJECT_ROOT / "gcloud-user-credentials.json")
   ```

3. **Test locally first** - if it works locally but fails in n8n, it's a path/environment issue

4. **Set environment variable** in n8n Execute Command node (if needed):
   - In "Environment" section, add:
   - Key: `GOOGLE_APPLICATION_CREDENTIALS`
   - Value: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\gcloud-user-credentials.json`
   - (Windows path) or `/opt/n8n/scripts/broker-protocol/gcloud-user-credentials.json` (Linux path)

5. **If credentials file is missing**:
   ```powershell
   # Generate new credentials
   gcloud auth application-default login
   # Then copy the credentials file to your project folder
   ```

---

### Issue: BigQuery Permission Errors

**Symptoms**: "Forbidden: 403" errors

**Diagnosis**:
The credentials in `gcloud-user-credentials.json` don't have required BigQuery permissions

**Solution**:
1. **Check which account is authenticated**:
   ```powershell
   gcloud auth list
   ```

2. **Ensure the authenticated account has BigQuery access**:
   - The account should have `BigQuery Data Editor` and `BigQuery Job User` roles
   - Contact your GCP administrator if you need permissions

3. **Re-authenticate with correct account**:
   ```powershell
   gcloud auth application-default login
   ```

4. **Verify permissions**:
   ```sql
   -- Test query in BigQuery console
   SELECT COUNT(*) FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`;
   ```

---

## 📊 Success Metrics

Track these metrics to measure automation health:

### Week 1 Targets (First n8n Run)
- ✅ Automated run completes
- ✅ Match rate ≥ 90% (typically 100% with enhanced matching)
- ✅ Needs review < 500 (typically ~300)
- ✅ Duration < 3 minutes (typically ~45 seconds)

### Month 1 Targets
- ✅ 2+ successful automated runs
- ✅ Match rate ≥ 95%
- ✅ Needs review < 400
- ✅ Zero manual intervention needed

### Month 3 Targets
- ✅ 6+ successful automated runs
- ✅ Match rate ≥ 98%
- ✅ Needs review < 300
- ✅ Lead scoring integration complete

**Actual Performance** (Based on Cursor.ai implementation):
- Match Rate: **100.0%** (exceeds all targets)
- Unmatched: **0.0%** (perfect)
- Needs Review: **~11.7%** (excellent)
- Processing Time: **~45 seconds** (very fast)

---

## ðŸ"ž Support

### For n8n Issues:
- n8n Documentation: https://docs.n8n.io/
- n8n Community: https://community.n8n.io/
- Check workflow execution logs in n8n

### For Python Script Issues:
- Check `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\PYTHON_SCRIPTS_README.md` (local development)
- Or `/opt/n8n/scripts/broker-protocol/PYTHON_SCRIPTS_README.md` (if copied to n8n server)
- Review error messages in n8n execution logs
- Test scripts manually outside n8n

### For Data Issues:
- Check BigQuery tables and views
- Run monitoring SQL queries
- Review data quality metrics

---

## ✅ Final Checklist

Before marking complete:

### n8n Setup
- [ ] All nodes added and connected
- [ ] Credentials configured
- [ ] Schedule trigger enabled
- [ ] Test run successful

### Integration
- [ ] Python scripts accessible from n8n
- [ ] `gcloud-user-credentials.json` exists in project folder
- [ ] Python authentication tested locally (Step 1.3)
- [ ] Email alerts configured
- [ ] File paths correct

### Validation
- [ ] Test run loaded data to BigQuery
- [ ] Match quality looks good
- [ ] Alerts work (tested)
- [ ] No errors in logs

### Documentation
- [ ] Team notified of new automation
- [ ] Monitoring queries shared
- [ ] Manual review process documented
- [ ] Troubleshooting guide reviewed

---

## 🎉 Congratulations!

You've successfully set up the Broker Protocol automation workflow!

**Next Steps**:
1. Monitor first few scheduled runs closely
2. Perform manual review of unmatched firms
3. Integrate with lead scoring model
4. Train sales team on new data

**Maintenance**:
- Weekly: Review unmatched firms (10 min)
- Monthly: Match quality check (30 min)
- Quarterly: Process review and optimization

---

**Last Updated**: December 22, 2025
**Version**: 2.0
**Status**: Ready for Implementation
**Based On**: Cursor.ai Implementation (100% match rate achieved)
