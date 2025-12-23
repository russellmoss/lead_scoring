# Broker Protocol Automation - Cursor.ai Development Guide

## 🎯 Project Overview

**Objective**: Build an automated system that downloads, parses, and matches Broker Protocol member firms to FINTRX CRD IDs every 2 weeks for lead enrichment and scoring.

**Key Components**:
1. BigQuery tables for storing Broker Protocol data
2. Python parser to extract firm names and dates from Excel
3. Python matcher to link firms to FINTRX CRD IDs using fuzzy matching
4. Integration with n8n workflow (manual setup by user)

**Data Flow**:
```
JSHeld Website → Download Excel → Parse → Match to FINTRX → Load to BigQuery → Track Changes
```

**Project Context**: 
- You have access to FINTRX dataset (`savvy-gtm-analytics.FinTrx_data_CA`) with 788K contacts and 45K firms
- Broker Protocol list has ~2,500-3,000 firms that change periodically
- Need point-in-time tracking for lead scoring (join dates, withdrawal dates)
- Match rate target: >80%

**Local Development Environment**:
- **Project Root**: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol`
- All Python scripts and files should be created in this directory
- Paths in examples use Windows format for local development
- For n8n deployment, scripts will be copied to Linux paths (see N8N_SETUP_GUIDE.md)

---

## 📋 Reference Materials Available

You have access to these documents in the project:
- `broker_protocol_parser.py` - Excel parser (already written, needs testing/refinement)
- `firm_matcher.py` - Firm matching logic (already written, needs testing/refinement)
- `broker_protocol_scrape.js` - JavaScript for downloading Excel (for n8n use)
- `TheBrokerProtocolMemberFirms122225.xlsx` - Sample data file
- `FINTRX_Architecture_Overview.md` - FINTRX database structure
- `FINTRX_Data_Dictionary.md` - Field-level documentation
- `FINTRX_Data_Quality_Report.md` - Data quality analysis

---

## 🚀 Development Phases

### PHASE 1: BigQuery Infrastructure Setup

#### Task 1.1: Create Main Data Table

Create the primary table to store Broker Protocol member data.

**Table**: `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members` (
    -- Identifiers
    broker_protocol_firm_name STRING NOT NULL,
    firm_crd_id INT64,  -- Matched FINTRX CRD ID
    fintrx_firm_name STRING,  -- Matched FINTRX firm name
    
    -- Name variations
    former_names STRING,  -- f/k/a names (comma-separated)
    dbas STRING,  -- d/b/a names (comma-separated)
    has_name_change BOOLEAN DEFAULT FALSE,
    
    -- Dates
    date_joined DATE,  -- Date joined Broker Protocol
    date_withdrawn DATE,  -- Date withdrawn from Protocol (NULL if current member)
    is_current_member BOOLEAN DEFAULT TRUE,
    
    -- Metadata from Broker Protocol
    joinder_qualifications STRING,  -- Original qualifications text
    date_notes_cleaned STRING,  -- Cleaned notes from Excel
    firm_name_raw STRING,  -- Original raw name from Excel
    date_notes_raw STRING,  -- Original raw date notes from Excel
    
    -- Matching metadata
    match_confidence FLOAT64,  -- 0.0 to 1.0
    match_method STRING,  -- 'exact', 'normalized_exact', 'base_name', 'fuzzy', 'manual', 'unmatched'
    needs_manual_review BOOLEAN DEFAULT FALSE,
    manual_review_notes STRING,
    manual_review_date TIMESTAMP,
    manual_review_by STRING,
    
    -- Tracking metadata
    scrape_timestamp TIMESTAMP NOT NULL,
    scrape_run_id STRING,  -- Unique ID for each scrape run
    first_seen_date DATE,  -- First date this firm appeared in data
    last_seen_date DATE,  -- Last date this firm was in data
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_firm_crd_id 
ON `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`(firm_crd_id);

CREATE INDEX IF NOT EXISTS idx_current_member 
ON `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`(is_current_member);

CREATE INDEX IF NOT EXISTS idx_needs_review 
ON `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`(needs_manual_review);
```

**Validation**:
```sql
-- Check table exists
SELECT table_name, row_count, size_mb 
FROM `savvy-gtm-analytics.SavvyGTMData.__TABLES__`
WHERE table_name = 'broker_protocol_members';
```

---

#### Task 1.2: Create History Tracking Table

Track all changes over time (firms joining, withdrawing, info updates).

**Table**: `savvy-gtm-analytics.SavvyGTMData.broker_protocol_history`

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS `savvy-gtm-analytics.SavvyGTMData.broker_protocol_history` (
    history_id STRING NOT NULL,  -- UUID for each history record
    broker_protocol_firm_name STRING NOT NULL,
    firm_crd_id INT64,
    
    change_type STRING NOT NULL,  -- 'JOINED', 'WITHDREW', 'INFO_UPDATED', 'NAME_CHANGED', 'MATCHED'
    change_date DATE NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    
    -- Before/After snapshots (JSON)
    previous_values STRING,  -- JSON object of old values
    new_values STRING,  -- JSON object of new values
    
    scrape_run_id STRING,
    notes STRING
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_firm_history 
ON `savvy-gtm-analytics.SavvyGTMData.broker_protocol_history`(broker_protocol_firm_name, change_date);

CREATE INDEX IF NOT EXISTS idx_change_type 
ON `savvy-gtm-analytics.SavvyGTMData.broker_protocol_history`(change_type);
```

**Validation**:
```sql
SELECT table_name FROM `savvy-gtm-analytics.SavvyGTMData.__TABLES__`
WHERE table_name = 'broker_protocol_history';
```

---

#### Task 1.3: Create Scrape Log Table

Track each scrape run for monitoring and debugging.

**Table**: `savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log`

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS `savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log` (
    scrape_run_id STRING NOT NULL,
    scrape_timestamp TIMESTAMP NOT NULL,
    scrape_status STRING NOT NULL,  -- 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED'
    
    -- Scrape details
    source_url STRING,
    excel_file_name STRING,
    excel_file_size_bytes INT64,
    excel_download_timestamp TIMESTAMP,
    
    -- Processing results
    firms_downloaded INT64,
    firms_parsed INT64,
    firms_matched INT64,
    firms_needing_review INT64,
    avg_match_confidence FLOAT64,
    
    -- Performance
    execution_duration_seconds FLOAT64,
    
    -- Errors
    error_message STRING,
    error_details STRING,
    
    -- Changes detected
    new_firms INT64,
    withdrawn_firms INT64,
    info_updates INT64
);

CREATE INDEX IF NOT EXISTS idx_scrape_timestamp 
ON `savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log`(scrape_timestamp DESC);
```

**Validation**:
```sql
SELECT table_name FROM `savvy-gtm-analytics.SavvyGTMData.__TABLES__`
WHERE table_name = 'broker_protocol_scrape_log';
```

---

#### Task 1.4: Create Manual Matches Table

Store manual match overrides.

**Table**: `savvy-gtm-analytics.SavvyGTMData.broker_protocol_manual_matches`

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS `savvy-gtm-analytics.SavvyGTMData.broker_protocol_manual_matches` (
    broker_protocol_firm_name STRING NOT NULL,
    firm_crd_id INT64 NOT NULL,
    fintrx_firm_name STRING,
    
    match_reason STRING,  -- Why this match was made
    reviewed_by STRING,
    reviewed_at TIMESTAMP NOT NULL,
    
    is_active BOOLEAN DEFAULT TRUE,
    
    PRIMARY KEY (broker_protocol_firm_name, firm_crd_id)
);
```

**Validation**:
```sql
SELECT table_name FROM `savvy-gtm-analytics.SavvyGTMData.__TABLES__`
WHERE table_name = 'broker_protocol_manual_matches';
```

---

#### Task 1.5: Create Monitoring Views

Create views for easy monitoring and reporting.

**View 1: Match Quality Summary**
```sql
CREATE OR REPLACE VIEW `savvy-gtm-analytics.SavvyGTMData.broker_protocol_match_quality` AS
SELECT 
    COUNT(*) as total_firms,
    COUNTIF(firm_crd_id IS NOT NULL) as matched_firms,
    COUNTIF(firm_crd_id IS NULL) as unmatched_firms,
    ROUND(COUNTIF(firm_crd_id IS NOT NULL) / COUNT(*) * 100, 1) as match_rate_pct,
    
    -- By match method
    COUNTIF(match_method = 'exact') as exact_matches,
    COUNTIF(match_method = 'normalized_exact') as normalized_matches,
    COUNTIF(match_method = 'base_name') as base_name_matches,
    COUNTIF(match_method = 'fuzzy') as fuzzy_matches,
    COUNTIF(match_method = 'manual') as manual_matches,
    COUNTIF(match_method = 'unmatched') as unmatched,
    
    -- Quality metrics
    ROUND(AVG(CASE WHEN firm_crd_id IS NOT NULL THEN match_confidence END), 3) as avg_match_confidence,
    COUNTIF(needs_manual_review) as needs_review_count,
    ROUND(COUNTIF(needs_manual_review) / COUNT(*) * 100, 1) as needs_review_pct,
    
    -- Current vs withdrawn
    COUNTIF(is_current_member) as current_members,
    COUNTIF(NOT is_current_member) as withdrawn_members,
    
    MAX(last_updated) as last_updated
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`;
```

**View 2: Recent Changes**
```sql
CREATE OR REPLACE VIEW `savvy-gtm-analytics.SavvyGTMData.broker_protocol_recent_changes` AS
SELECT 
    h.broker_protocol_firm_name,
    h.change_type,
    h.change_date,
    h.detected_at,
    m.firm_crd_id,
    m.fintrx_firm_name,
    f.TOTAL_AUM,
    h.notes
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_history` h
LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members` m
    ON h.broker_protocol_firm_name = m.broker_protocol_firm_name
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON m.firm_crd_id = f.CRD_ID
WHERE h.change_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
ORDER BY h.detected_at DESC;
```

**View 3: Top Firms Needing Review**
```sql
CREATE OR REPLACE VIEW `savvy-gtm-analytics.SavvyGTMData.broker_protocol_needs_review` AS
SELECT 
    m.broker_protocol_firm_name,
    m.fintrx_firm_name,
    m.match_confidence,
    m.match_method,
    m.date_joined,
    m.is_current_member,
    f.TOTAL_AUM,
    f.NUM_OF_EMPLOYEES
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members` m
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON m.firm_crd_id = f.CRD_ID
WHERE m.needs_manual_review = TRUE
ORDER BY 
    CASE 
        WHEN m.match_confidence > 0 THEN 1  -- Fuzzy matches first (likely correct)
        ELSE 2  -- Unmatched last
    END,
    COALESCE(f.TOTAL_AUM, 0) DESC,  -- Prioritize large firms
    m.match_confidence DESC;
```

**Validation**:
```sql
-- Test all views
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_match_quality`;
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_recent_changes` LIMIT 5;
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_needs_review` LIMIT 5;
```

---

### PHASE 2: Test and Refine Python Scripts

#### Task 2.1: Test the Excel Parser

The parser (`broker_protocol_parser.py`) is already written but needs testing and potential refinement.

**Steps**:

1. **Read the parser code** to understand its logic:
   - Reads Excel with header at row 3
   - Parses firm names (handles f/k/a, d/b/a)
   - Extracts join and withdrawal dates
   - Creates clean output CSV

2. **Test on sample data**:
```bash
# Windows (local development)
python broker_protocol_parser.py "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\TheBrokerProtocolMemberFirms122225.xlsx" --test
```

3. **Run full parse**:
```bash
python broker_protocol_parser.py "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\TheBrokerProtocolMemberFirms122225.xlsx" -v -o "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_parsed.csv"
```

4. **Validate output**:
```python
import pandas as pd

df = pd.read_csv(r'C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_parsed.csv')

print("=== PARSER OUTPUT VALIDATION ===")
print(f"Total rows: {len(df)}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nSample rows:")
print(df.head(10))

print(f"\n=== DATA QUALITY ===")
print(f"Firms with join dates: {df['date_joined'].notna().sum()} ({df['date_joined'].notna().sum()/len(df)*100:.1f}%)")
print(f"Current members: {df['is_current_member'].sum()} ({df['is_current_member'].sum()/len(df)*100:.1f}%)")
print(f"Withdrawn members: {(~df['is_current_member']).sum()}")
print(f"Firms with name changes: {df['has_name_change'].sum()}")

print(f"\n=== SAMPLE WITHDRAWN FIRMS ===")
withdrawn = df[df['date_withdrawn'].notna()]
if len(withdrawn) > 0:
    print(withdrawn[['firm_name', 'date_joined', 'date_withdrawn']].head(5))

print(f"\n=== SAMPLE NAME CHANGES ===")
name_changes = df[df['has_name_change']]
if len(name_changes) > 0:
    print(name_changes[['firm_name', 'former_names', 'dbas']].head(5))
```

5. **Issues to watch for**:
   - Date parsing failures (check `date_notes_cleaned` for unparsed dates)
   - Firm name parsing issues (check `firm_name_raw` vs `firm_name`)
   - Missing data (unexpected NULLs)

6. **If issues found**, refine the parser:
   - Update date regex patterns in `extract_dates()`
   - Update name parsing in `parse_firm_name()`
   - Re-test until output is clean

**Expected Results**:
- ~2,500-3,000 firms parsed
- >90% have join dates
- ~10-20% have withdrawal dates
- ~5-10% have name changes

---

#### Task 2.2: Export FINTRX Firms for Matching

Get the FINTRX firm list to use for matching.

```python
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project='savvy-gtm-analytics')

print("Exporting FINTRX firms...")

query = """
SELECT 
    CRD_ID,
    NAME,
    TOTAL_AUM,
    NUM_OF_EMPLOYEES
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current`
WHERE NAME IS NOT NULL
ORDER BY CRD_ID
"""

fintrx_df = client.query(query).to_dataframe()
fintrx_df.to_csv(r'C:\Users\russe\Documents\Lead Scoring\Broker_protocol\fintrx_firms.csv', index=False)

print(f"Exported {len(fintrx_df)} FINTRX firms")
print(f"With AUM: {fintrx_df['TOTAL_AUM'].notna().sum()}")
print(f"With employee count: {fintrx_df['NUM_OF_EMPLOYEES'].notna().sum()}")
```

---

#### Task 2.3: Test the Firm Matcher

The matcher (`firm_matcher.py`) is already written but needs testing.

**Steps**:

1. **Read the matcher code** to understand its logic:
   - Tier 1: Exact match (case-insensitive)
   - Tier 2: Normalized exact match (remove punctuation, standardize suffixes)
   - Tier 3: Base name match (remove entity suffixes)
   - Tier 4: Fuzzy match (similarity scoring)

2. **Test on single firms** (especially problematic ones):
```bash
# Test large well-known firms
python firm_matcher.py "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_parsed.csv" "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\fintrx_firms.csv" --firm "Morgan Stanley Wealth Management"

python firm_matcher.py "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_parsed.csv" "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\fintrx_firms.csv" --firm "Merrill Lynch, Pierce, Fenner & Smith Incorporated"

python firm_matcher.py "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_parsed.csv" "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\fintrx_firms.csv" --firm "Wells Fargo Advisors, LLC"

# Test firms with name changes
python firm_matcher.py "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_parsed.csv" "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\fintrx_firms.csv" --firm "UBS Financial Services Inc. f/k/a UBS Wealth Management USA"
```

3. **Run full batch matching**:
```bash
python firm_matcher.py "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_parsed.csv" "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\fintrx_firms.csv" -v -o "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_matched.csv"
```

4. **Validate matching results**:
```python
import pandas as pd

matched_df = pd.read_csv(r'C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_matched.csv')

print("=== MATCHING RESULTS ===")
print(f"Total firms: {len(matched_df)}")
print(f"\nMatch rate: {(matched_df['firm_crd_id'].notna()).sum()} / {len(matched_df)} ({(matched_df['firm_crd_id'].notna()).sum()/len(matched_df)*100:.1f}%)")

print(f"\n=== BY MATCH METHOD ===")
print(matched_df['match_method'].value_counts())

print(f"\n=== CONFIDENCE DISTRIBUTION ===")
print(matched_df[matched_df['firm_crd_id'].notna()]['match_confidence'].describe())

print(f"\n=== NEEDS REVIEW ===")
print(f"Needs manual review: {matched_df['needs_manual_review'].sum()} ({matched_df['needs_manual_review'].sum()/len(matched_df)*100:.1f}%)")

print(f"\n=== SAMPLE EXACT MATCHES ===")
exact = matched_df[matched_df['match_method'] == 'exact']
if len(exact) > 0:
    print(exact[['firm_name', 'fintrx_firm_name', 'match_confidence']].head(5))

print(f"\n=== SAMPLE FUZZY MATCHES (GOOD) ===")
fuzzy_good = matched_df[(matched_df['match_method'] == 'fuzzy') & (matched_df['match_confidence'] >= 0.80)]
if len(fuzzy_good) > 0:
    print(fuzzy_good[['firm_name', 'fintrx_firm_name', 'match_confidence']].head(5))

print(f"\n=== SAMPLE FUZZY MATCHES (NEEDS REVIEW) ===")
fuzzy_review = matched_df[(matched_df['match_method'] == 'fuzzy') & (matched_df['match_confidence'] < 0.80)]
if len(fuzzy_review) > 0:
    print(fuzzy_review[['firm_name', 'fintrx_firm_name', 'match_confidence']].head(5))

print(f"\n=== UNMATCHED FIRMS ===")
unmatched = matched_df[matched_df['firm_crd_id'].isna()]
if len(unmatched) > 0:
    print(f"Total unmatched: {len(unmatched)}")
    print(unmatched[['firm_name', 'date_joined', 'is_current_member']].head(10))
```

5. **Check for systematic issues**:
```python
# Check if certain name patterns are failing
import re

unmatched = matched_df[matched_df['firm_crd_id'].isna()]

# Check for LLC vs Inc inconsistencies
llc_firms = unmatched[unmatched['firm_name'].str.contains('LLC', case=False, na=False)]
print(f"\nUnmatched LLC firms: {len(llc_firms)}")
if len(llc_firms) > 0:
    print(llc_firms[['firm_name']].head(10))

# Check for name change issues
name_change_unmatched = unmatched[unmatched['has_name_change']]
print(f"\nUnmatched firms with name changes: {len(name_change_unmatched)}")
if len(name_change_unmatched) > 0:
    print(name_change_unmatched[['firm_name', 'former_names']].head(5))
```

6. **If matching issues found**, refine the matcher:
   - Update name normalization logic
   - Adjust confidence threshold
   - Add special case handling
   - Re-test until match rate >70%

**Expected Results**:
- Match rate: 70-85%
- Exact + normalized matches: 30-50%
- Fuzzy matches: 20-40%
- Needs review: 10-20%
- Unmatched: 5-15%

---

#### Task 2.4: Improve Match Rate (If Needed)

If match rate is <70%, try these improvements:

**Option 1: Lower confidence threshold**
```bash
python3 firm_matcher.py broker_protocol_parsed.csv fintrx_firms.csv -t 0.50
```

**Option 2: Add firm-specific overrides**

Create manual matches for large important firms:
```python
# Add to manual matches table
manual_matches = [
    ('Firm Name in Broker Protocol', 12345, 'Firm Name in FINTRX'),
    # Add more...
]

# Insert into BigQuery
# (will do in Phase 3)
```

**Option 3: Improve name normalization**

Edit `firm_matcher.py` `normalize_firm_name()` function to handle edge cases:
```python
# Add more suffix variations
suffixes = {
    'llc': [..., 'l.l.c', 'll.c'],  # Add more variations
    # ...
}
```

---

### PHASE 3: Initial Data Load

#### Task 3.1: Load Matched Data to BigQuery

Now that we have clean, matched data, load it into BigQuery.

```python
from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import uuid

client = bigquery.Client(project='savvy-gtm-analytics')

# Load matched data
print("Loading matched data...")
matched_df = pd.read_csv(r'C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_matched.csv')

# Add tracking metadata
scrape_run_id = f"initial_load_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
matched_df['scrape_run_id'] = scrape_run_id
matched_df['first_seen_date'] = pd.Timestamp.now().date()
matched_df['last_seen_date'] = pd.Timestamp.now().date()
matched_df['last_updated'] = pd.Timestamp.now()

print(f"Scrape Run ID: {scrape_run_id}")
print(f"Loading {len(matched_df)} rows...")

# Load to BigQuery
table_id = 'savvy-gtm-analytics.SavvyGTMData.broker_protocol_members'

job_config = bigquery.LoadJobConfig(
    write_disposition='WRITE_APPEND',  # Append data
    schema_update_options=[
        bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION
    ]
)

job = client.load_table_from_dataframe(
    matched_df,
    table_id,
    job_config=job_config
)

job.result()  # Wait for completion

print(f"✓ Loaded {len(matched_df)} rows to {table_id}")

# Verify
query = "SELECT COUNT(*) as count FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`"
result = client.query(query).to_dataframe()
print(f"✓ Table now has {result['count'].iloc[0]} total rows")
```

---

#### Task 3.2: Create Initial Scrape Log Entry

Log this initial load for tracking.

```python
# Create log entry
log_entry = pd.DataFrame([{
    'scrape_run_id': scrape_run_id,
    'scrape_timestamp': pd.Timestamp.now(),
    'scrape_status': 'SUCCESS',
    'source_url': 'https://www.jsheld.com/markets-served/financial-services/broker-recruiting/the-broker-protocol',
    'excel_file_name': 'TheBrokerProtocolMemberFirms122225.xlsx',
    'firms_downloaded': len(matched_df),
    'firms_parsed': len(matched_df),
    'firms_matched': (matched_df['firm_crd_id'].notna()).sum(),
    'firms_needing_review': matched_df['needs_manual_review'].sum(),
    'avg_match_confidence': matched_df[matched_df['firm_crd_id'].notna()]['match_confidence'].mean(),
    'new_firms': len(matched_df),
    'withdrawn_firms': 0,
    'info_updates': 0
}])

table_id = 'savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log'
job = client.load_table_from_dataframe(log_entry, table_id)
job.result()

print(f"✓ Created scrape log entry")
```

---

#### Task 3.3: Validate Data Quality

Run comprehensive validation checks.

```python
from google.cloud import bigquery

client = bigquery.Client(project='savvy-gtm-analytics')

print("=== DATA QUALITY VALIDATION ===\n")

# Check 1: Total records
query = """
SELECT COUNT(*) as total_firms
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
"""
result = client.query(query).to_dataframe()
total = result['total_firms'].iloc[0]
print(f"✓ Total firms loaded: {total}")
assert total > 2000, f"Expected >2000 firms, got {total}"

# Check 2: Match quality
query = """
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_match_quality`
"""
quality = client.query(query).to_dataframe()
print(f"\n✓ Match Quality:")
print(quality.to_string())

match_rate = quality['match_rate_pct'].iloc[0]
assert match_rate > 70, f"Match rate {match_rate}% is below 70% threshold"
print(f"\n✓ Match rate {match_rate}% exceeds 70% threshold")

# Check 3: Date coverage
query = """
SELECT 
    COUNTIF(date_joined IS NOT NULL) as with_join_date,
    COUNTIF(date_withdrawn IS NOT NULL) as with_withdrawal_date,
    COUNTIF(is_current_member) as current_members,
    COUNTIF(NOT is_current_member) as withdrawn_members
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
"""
dates = client.query(query).to_dataframe()
print(f"\n✓ Date Coverage:")
print(dates.to_string())

# Check 4: No duplicates
query = """
SELECT 
    broker_protocol_firm_name,
    COUNT(*) as count
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
GROUP BY broker_protocol_firm_name
HAVING COUNT(*) > 1
"""
dupes = client.query(query).to_dataframe()
assert len(dupes) == 0, f"Found {len(dupes)} duplicate firm names"
print(f"\n✓ No duplicate firm names")

# Check 5: Views work
query = "SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_needs_review` LIMIT 5"
needs_review = client.query(query).to_dataframe()
print(f"\n✓ Needs review view working: {len(needs_review)} firms")

print("\n=== ALL VALIDATION CHECKS PASSED ===")
```

---

### PHASE 4: Create Update/Merge Logic

#### Task 4.1: Create Update Function

This function will be used by the automated workflow to merge new data.

```python
# File: C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_updater.py

"""
Broker Protocol Data Updater
Merges new scrape data with existing data, tracking changes.
"""

from google.cloud import bigquery
import pandas as pd
from datetime import datetime
import uuid
import sys
import json


def compare_records(old_row: dict, new_row: dict) -> dict:
    """
    Compare two records and identify changes.
    
    Returns:
        dict with 'has_changes' (bool) and 'changes' (list of change descriptions)
    """
    changes = []
    
    # Check for withdrawal
    if pd.isna(old_row.get('date_withdrawn')) and pd.notna(new_row.get('date_withdrawn')):
        changes.append({
            'type': 'WITHDREW',
            'field': 'date_withdrawn',
            'old_value': None,
            'new_value': str(new_row['date_withdrawn'])
        })
    
    # Check for name change
    if old_row.get('firm_name') != new_row.get('firm_name'):
        changes.append({
            'type': 'NAME_CHANGED',
            'field': 'firm_name',
            'old_value': old_row.get('firm_name'),
            'new_value': new_row.get('firm_name')
        })
    
    # Check for matching update
    if old_row.get('firm_crd_id') != new_row.get('firm_crd_id'):
        changes.append({
            'type': 'MATCHED',
            'field': 'firm_crd_id',
            'old_value': old_row.get('firm_crd_id'),
            'new_value': new_row.get('firm_crd_id')
        })
    
    # Check for info updates (other fields)
    check_fields = ['former_names', 'dbas', 'joinder_qualifications']
    for field in check_fields:
        if old_row.get(field) != new_row.get(field):
            changes.append({
                'type': 'INFO_UPDATED',
                'field': field,
                'old_value': old_row.get(field),
                'new_value': new_row.get(field)
            })
    
    return {
        'has_changes': len(changes) > 0,
        'changes': changes
    }


def merge_broker_protocol_data(new_data_path: str, scrape_run_id: str, dry_run: bool = False):
    """
    Merge new broker protocol data with existing data.
    
    Args:
        new_data_path: Path to CSV with new data
        scrape_run_id: Unique ID for this scrape run
        dry_run: If True, don't actually update database
    """
    
    client = bigquery.Client(project='savvy-gtm-analytics')
    
    print(f"=== BROKER PROTOCOL DATA MERGE ===")
    print(f"Scrape Run ID: {scrape_run_id}")
    print(f"Dry Run: {dry_run}\n")
    
    # Load new data
    print("Loading new data...")
    new_df = pd.read_csv(new_data_path)
    print(f"  New data: {len(new_df)} firms")
    
    # Load existing data
    print("Loading existing data...")
    query = """
    SELECT 
        broker_protocol_firm_name,
        firm_crd_id,
        fintrx_firm_name,
        former_names,
        dbas,
        date_joined,
        date_withdrawn,
        is_current_member,
        joinder_qualifications,
        match_confidence,
        match_method,
        first_seen_date,
        last_seen_date
    FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
    """
    existing_df = client.query(query).to_dataframe()
    print(f"  Existing data: {len(existing_df)} firms")
    
    # Compare and categorize
    print("\nAnalyzing changes...")
    
    existing_names = set(existing_df['broker_protocol_firm_name'].values)
    new_names = set(new_df['firm_name'].values)
    
    newly_joined = new_names - existing_names
    newly_withdrawn = existing_names - new_names
    potentially_updated = existing_names & new_names
    
    print(f"  Newly joined firms: {len(newly_joined)}")
    print(f"  Newly withdrawn firms: {len(newly_withdrawn)}")
    print(f"  Existing firms (checking for updates): {len(potentially_updated)}")
    
    # Track changes
    changes_to_log = []
    
    # Process newly joined firms
    new_firms = []
    for firm_name in newly_joined:
        row = new_df[new_df['firm_name'] == firm_name].iloc[0]
        
        new_firm = {
            'broker_protocol_firm_name': row['firm_name'],
            'firm_crd_id': row.get('firm_crd_id'),
            'fintrx_firm_name': row.get('fintrx_firm_name'),
            'former_names': row.get('former_names'),
            'dbas': row.get('dbas'),
            'has_name_change': row.get('has_name_change'),
            'date_joined': row.get('date_joined'),
            'date_withdrawn': row.get('date_withdrawn'),
            'is_current_member': row.get('is_current_member'),
            'joinder_qualifications': row.get('joinder_qualifications'),
            'date_notes_cleaned': row.get('date_notes_cleaned'),
            'firm_name_raw': row.get('firm_name_raw'),
            'date_notes_raw': row.get('date_notes_raw'),
            'match_confidence': row.get('match_confidence'),
            'match_method': row.get('match_method'),
            'needs_manual_review': row.get('needs_manual_review'),
            'scrape_timestamp': row.get('scrape_timestamp', pd.Timestamp.now()),
            'scrape_run_id': scrape_run_id,
            'first_seen_date': pd.Timestamp.now().date(),
            'last_seen_date': pd.Timestamp.now().date(),
            'last_updated': pd.Timestamp.now()
        }
        
        new_firms.append(new_firm)
        
        # Log change
        changes_to_log.append({
            'history_id': str(uuid.uuid4()),
            'broker_protocol_firm_name': firm_name,
            'firm_crd_id': row.get('firm_crd_id'),
            'change_type': 'JOINED',
            'change_date': row.get('date_joined', pd.Timestamp.now().date()),
            'detected_at': pd.Timestamp.now(),
            'previous_values': None,
            'new_values': json.dumps(new_firm, default=str),
            'scrape_run_id': scrape_run_id,
            'notes': 'Newly joined firm detected'
        })
    
    # Process existing firms - check for updates
    updated_firms = []
    for firm_name in potentially_updated:
        old_row = existing_df[existing_df['broker_protocol_firm_name'] == firm_name].iloc[0].to_dict()
        new_row = new_df[new_df['firm_name'] == firm_name].iloc[0].to_dict()
        
        comparison = compare_records(old_row, new_row)
        
        if comparison['has_changes']:
            # Update record
            updated_firm = {
                'broker_protocol_firm_name': firm_name,
                'last_seen_date': pd.Timestamp.now().date(),
                'last_updated': pd.Timestamp.now(),
                'scrape_run_id': scrape_run_id
            }
            
            # Apply changes
            for change in comparison['changes']:
                updated_firm[change['field']] = new_row.get(change['field'])
                
                if change['type'] == 'WITHDREW':
                    updated_firm['is_current_member'] = False
            
            updated_firms.append(updated_firm)
            
            # Log each change
            for change in comparison['changes']:
                changes_to_log.append({
                    'history_id': str(uuid.uuid4()),
                    'broker_protocol_firm_name': firm_name,
                    'firm_crd_id': old_row.get('firm_crd_id'),
                    'change_type': change['type'],
                    'change_date': pd.Timestamp.now().date(),
                    'detected_at': pd.Timestamp.now(),
                    'previous_values': json.dumps({'field': change['field'], 'value': change['old_value']}),
                    'new_values': json.dumps({'field': change['field'], 'value': change['new_value']}),
                    'scrape_run_id': scrape_run_id,
                    'notes': f"Field '{change['field']}' changed"
                })
        else:
            # No changes, just update last_seen_date
            updated_firms.append({
                'broker_protocol_firm_name': firm_name,
                'last_seen_date': pd.Timestamp.now().date(),
                'scrape_run_id': scrape_run_id
            })
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"New firms to add: {len(new_firms)}")
    print(f"Existing firms to update: {len(updated_firms)}")
    print(f"Changes to log: {len(changes_to_log)}")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No changes will be made to database")
        
        if len(new_firms) > 0:
            print("\nSample new firms:")
            for firm in new_firms[:5]:
                print(f"  - {firm['broker_protocol_firm_name']}")
        
        if len(changes_to_log) > 0:
            print("\nSample changes:")
            for change in changes_to_log[:5]:
                print(f"  - {change['change_type']}: {change['broker_protocol_firm_name']}")
        
        return
    
    # Execute updates
    print("\n=== EXECUTING UPDATES ===")
    
    # Insert new firms
    if len(new_firms) > 0:
        print(f"Inserting {len(new_firms)} new firms...")
        new_df_to_insert = pd.DataFrame(new_firms)
        
        table_id = 'savvy-gtm-analytics.SavvyGTMData.broker_protocol_members'
        job = client.load_table_from_dataframe(new_df_to_insert, table_id)
        job.result()
        print(f"  ✓ Inserted {len(new_firms)} new firms")
    
    # Update existing firms
    if len(updated_firms) > 0:
        print(f"Updating {len(updated_firms)} existing firms...")
        
        # Use MERGE statement for updates
        for firm in updated_firms:
            update_query = f"""
            UPDATE `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
            SET 
                last_seen_date = DATE('{firm['last_seen_date']}'),
                last_updated = TIMESTAMP('{firm['last_updated']}'),
                scrape_run_id = '{firm['scrape_run_id']}'
            """
            
            # Add field updates if present
            for key, value in firm.items():
                if key not in ['broker_protocol_firm_name', 'last_seen_date', 'last_updated', 'scrape_run_id']:
                    if pd.notna(value):
                        if isinstance(value, (int, float, bool)):
                            update_query += f", {key} = {value}"
                        elif isinstance(value, str):
                            update_query += f", {key} = '{value}'"
                        elif isinstance(value, pd.Timestamp):
                            update_query += f", {key} = TIMESTAMP('{value}')"
            
            update_query += f" WHERE broker_protocol_firm_name = '{firm['broker_protocol_firm_name']}'"
            
            client.query(update_query).result()
        
        print(f"  ✓ Updated {len(updated_firms)} firms")
    
    # Log changes to history table
    if len(changes_to_log) > 0:
        print(f"Logging {len(changes_to_log)} changes...")
        changes_df = pd.DataFrame(changes_to_log)
        
        table_id = 'savvy-gtm-analytics.SavvyGTMData.broker_protocol_history'
        job = client.load_table_from_dataframe(changes_df, table_id)
        job.result()
        print(f"  ✓ Logged {len(changes_to_log)} changes")
    
    # Update scrape log
    print("Updating scrape log...")
    log_entry = pd.DataFrame([{
        'scrape_run_id': scrape_run_id,
        'scrape_timestamp': pd.Timestamp.now(),
        'scrape_status': 'SUCCESS',
        'firms_downloaded': len(new_df),
        'firms_parsed': len(new_df),
        'firms_matched': (new_df['firm_crd_id'].notna()).sum(),
        'firms_needing_review': new_df['needs_manual_review'].sum(),
        'avg_match_confidence': new_df[new_df['firm_crd_id'].notna()]['match_confidence'].mean(),
        'new_firms': len(new_firms),
        'withdrawn_firms': len(newly_withdrawn),
        'info_updates': len([c for c in changes_to_log if c['change_type'] == 'INFO_UPDATED'])
    }])
    
    table_id = 'savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log'
    job = client.load_table_from_dataframe(log_entry, table_id)
    job.result()
    print(f"  ✓ Updated scrape log")
    
    print("\n=== MERGE COMPLETE ===")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Merge broker protocol data')
    parser.add_argument('data_file', help='Path to matched CSV file')
    parser.add_argument('--scrape-id', help='Scrape run ID', default=f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no changes)')
    
    args = parser.parse_args()
    
    try:
        merge_broker_protocol_data(args.data_file, args.scrape_id, args.dry_run)
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

---

#### Task 4.2: Test Update Logic

Test the updater with a dry run.

```bash
# First, test with dry run
python "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_updater.py" "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_matched.csv" --dry-run

# If looks good, run for real
python "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_updater.py" "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_matched.csv"
```

---

### PHASE 5: Create Complete Automation Script

#### Task 5.1: Create End-to-End Automation Script

This script will be called by n8n to do the full process.

```python
# File: C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_automation.py

"""
Broker Protocol Full Automation Script
Downloads, parses, matches, and merges broker protocol data.
"""

import sys
import os
from datetime import datetime
import argparse
import traceback


def run_full_automation(excel_path: str, verbose: bool = False):
    """
    Run complete automation pipeline.
    
    Args:
        excel_path: Path to downloaded Excel file
        verbose: Print detailed output
        
    Returns:
        dict with results
    """
    
    start_time = datetime.now()
    scrape_run_id = f"auto_{start_time.strftime('%Y%m%d_%H%M%S')}"
    
    results = {
        'scrape_run_id': scrape_run_id,
        'status': 'FAILED',
        'error': None,
        'steps_completed': []
    }
    
    try:
        # Step 1: Parse Excel
        print("=" * 60)
        print("STEP 1: Parsing Excel file")
        print("=" * 60)
        
        import broker_protocol_parser as parser
        
        parsed_df = parser.parse_broker_protocol_excel(excel_path, verbose=verbose)
        parsed_path = r'C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_parsed_latest.csv'
        parsed_df.to_csv(parsed_path, index=False)
        
        results['steps_completed'].append('PARSE')
        results['firms_parsed'] = len(parsed_df)
        
        print(f"\n✓ Parsed {len(parsed_df)} firms")
        
        # Step 2: Get FINTRX firms
        print("\n" + "=" * 60)
        print("STEP 2: Loading FINTRX firms")
        print("=" * 60)
        
        from google.cloud import bigquery
        
        client = bigquery.Client(project='savvy-gtm-analytics')
        
        query = """
        SELECT CRD_ID, NAME
        FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current`
        WHERE NAME IS NOT NULL
        """
        
        fintrx_df = client.query(query).to_dataframe()
        fintrx_path = r'C:\Users\russe\Documents\Lead Scoring\Broker_protocol\fintrx_firms_latest.csv'
        fintrx_df.to_csv(fintrx_path, index=False)
        
        print(f"\n✓ Loaded {len(fintrx_df)} FINTRX firms")
        
        # Step 3: Match firms
        print("\n" + "=" * 60)
        print("STEP 3: Matching firms to FINTRX")
        print("=" * 60)
        
        import firm_matcher as matcher
        
        matched_df = matcher.batch_match_firms(
            parsed_df,
            fintrx_df,
            confidence_threshold=0.60,
            verbose=verbose
        )
        
        matched_path = r'C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_matched_latest.csv'
        matched_df.to_csv(matched_path, index=False)
        
        results['steps_completed'].append('MATCH')
        results['firms_matched'] = (matched_df['firm_crd_id'].notna()).sum()
        results['match_rate'] = (matched_df['firm_crd_id'].notna()).sum() / len(matched_df) * 100
        results['needs_review'] = matched_df['needs_manual_review'].sum()
        
        print(f"\n✓ Matched {results['firms_matched']} firms ({results['match_rate']:.1f}%)")
        print(f"  Needs review: {results['needs_review']}")
        
        # Step 4: Merge with existing data
        print("\n" + "=" * 60)
        print("STEP 4: Merging with existing data")
        print("=" * 60)
        
        import broker_protocol_updater as updater
        
        updater.merge_broker_protocol_data(
            matched_path,
            scrape_run_id,
            dry_run=False
        )
        
        results['steps_completed'].append('MERGE')
        
        print(f"\n✓ Merged data successfully")
        
        # Success
        results['status'] = 'SUCCESS'
        
        duration = (datetime.now() - start_time).total_seconds()
        results['duration_seconds'] = duration
        
        print("\n" + "=" * 60)
        print("AUTOMATION COMPLETE")
        print("=" * 60)
        print(f"Status: {results['status']}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Scrape Run ID: {scrape_run_id}")
        
        return results
        
    except Exception as e:
        results['status'] = 'FAILED'
        results['error'] = str(e)
        
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        
        if verbose:
            traceback.print_exc()
        
        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run broker protocol automation')
    parser.add_argument('excel_file', help='Path to Excel file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.excel_file):
        print(f"ERROR: File not found: {args.excel_file}", file=sys.stderr)
        sys.exit(1)
    
    results = run_full_automation(args.excel_file, verbose=args.verbose)
    
    if results['status'] == 'FAILED':
        sys.exit(1)
    
    sys.exit(0)
```

---

#### Task 5.2: Test Complete Automation

Test the full automation end-to-end.

```bash
# Test with existing file
python "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_automation.py" "C:\Users\russe\Documents\Lead Scoring\Broker_protocol\TheBrokerProtocolMemberFirms122225.xlsx" -v
```

Verify results:
```python
from google.cloud import bigquery

client = bigquery.Client(project='savvy-gtm-analytics')

# Check match quality
query = "SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_match_quality`"
print(client.query(query).to_dataframe().to_string())

# Check recent scrape log
query = """
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log`
ORDER BY scrape_timestamp DESC LIMIT 3
"""
print(client.query(query).to_dataframe().to_string())

# Check recent changes
query = """
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_recent_changes`
LIMIT 10
"""
print(client.query(query).to_dataframe().to_string())
```

---

### PHASE 6: Documentation and Handoff

#### Task 6.1: Create Python Package Documentation

Create a README for the Python scripts.

```markdown
# File: C:\Users\russe\Documents\Lead Scoring\Broker_protocol\PYTHON_SCRIPTS_README.md

# Broker Protocol Python Scripts

## Scripts

### 1. broker_protocol_parser.py
Parses Excel file from JSHeld website.

**Usage**:
```bash
python3 broker_protocol_parser.py input.xlsx -o output.csv
```

**Output**: CSV with columns:
- firm_name
- former_names (f/k/a)
- dbas (d/b/a)
- date_joined
- date_withdrawn
- is_current_member
- ...

### 2. firm_matcher.py
Matches broker protocol firms to FINTRX CRD IDs.

**Usage**:
```bash
python3 firm_matcher.py broker_parsed.csv fintrx_firms.csv -o matched.csv
```

**Match Methods**:
- exact (1.0 confidence)
- normalized_exact (0.95)
- base_name (0.85)
- fuzzy (0.60-0.84)

### 3. broker_protocol_updater.py
Merges new data with existing BigQuery data.

**Usage**:
```bash
# Dry run first
python3 broker_protocol_updater.py matched.csv --dry-run

# Then run for real
python3 broker_protocol_updater.py matched.csv
```

### 4. broker_protocol_automation.py
End-to-end automation script.

**Usage**:
```bash
python3 broker_protocol_automation.py downloaded.xlsx -v
```

This script:
1. Parses Excel
2. Loads FINTRX firms
3. Matches firms
4. Merges with BigQuery

**Called by n8n workflow**.

## Testing

Test each component:
```bash
# 1. Test parser
python3 broker_protocol_parser.py test.xlsx --test

# 2. Test matcher on single firm
python3 firm_matcher.py parsed.csv fintrx.csv --firm "Morgan Stanley"

# 3. Test full automation
python3 broker_protocol_automation.py test.xlsx -v
```

## Monitoring

Check data quality:
```sql
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_match_quality`;
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_recent_changes` LIMIT 10;
```
```

Save this file:
```bash
# Create PYTHON_SCRIPTS_README.md in project root
# File: C:\Users\russe\Documents\Lead Scoring\Broker_protocol\PYTHON_SCRIPTS_README.md
[paste content above]
EOF
```

---

#### Task 6.2: Create SQL Query Reference

Create useful SQL queries for monitoring.

```sql
-- File: C:\Users\russe\Documents\Lead Scoring\Broker_protocol\monitoring_queries.sql

-- === DATA QUALITY CHECKS ===

-- Check overall match quality
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_match_quality`;

-- Check firms needing review (prioritized by AUM)
SELECT 
    broker_protocol_firm_name,
    fintrx_firm_name,
    match_confidence,
    match_method,
    TOTAL_AUM
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_needs_review`
LIMIT 50;

-- Check recent changes
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_recent_changes`
ORDER BY detected_at DESC LIMIT 20;

-- Check last scrape status
SELECT 
    scrape_timestamp,
    scrape_status,
    firms_matched,
    avg_match_confidence,
    new_firms,
    withdrawn_firms
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log`
ORDER BY scrape_timestamp DESC LIMIT 5;


-- === LEAD ENRICHMENT QUERIES ===

-- Add broker protocol status to contacts
SELECT 
    c.RIA_CONTACT_CRD_ID,
    c.RIA_CONTACT_PREFERRED_NAME,
    f.NAME as firm_name,
    bp.is_current_member as is_broker_protocol_firm,
    bp.date_joined as broker_protocol_join_date,
    DATE_DIFF(CURRENT_DATE(), bp.date_joined, YEAR) as broker_protocol_tenure_years
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON c.PRIMARY_FIRM = f.CRD_ID
LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members` bp
    ON f.CRD_ID = bp.firm_crd_id
WHERE c.RIA_CONTACT_CRD_ID = 12345;  -- Replace with actual CRD


-- Top broker protocol firms by AUM
SELECT 
    bpm.broker_protocol_firm_name,
    bpm.fintrx_firm_name,
    f.TOTAL_AUM,
    f.NUM_OF_EMPLOYEES,
    bpm.date_joined,
    DATE_DIFF(CURRENT_DATE(), bpm.date_joined, YEAR) as years_in_protocol
FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members` bpm
INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON bpm.firm_crd_id = f.CRD_ID
WHERE bpm.is_current_member = TRUE
    AND f.TOTAL_AUM IS NOT NULL
ORDER BY f.TOTAL_AUM DESC
LIMIT 100;


-- === MANUAL REVIEW HELPERS ===

-- Search FINTRX for potential match
SELECT 
    CRD_ID,
    NAME,
    TOTAL_AUM,
    NUM_OF_EMPLOYEES,
    MAIN_OFFICE_CITY_NAME,
    MAIN_OFFICE_STATE
FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current`
WHERE LOWER(NAME) LIKE '%search term%'
ORDER BY TOTAL_AUM DESC NULLS LAST
LIMIT 20;

-- Update manual match
UPDATE `savvy-gtm-analytics.SavvyGTMData.broker_protocol_members`
SET 
    firm_crd_id = 12345,
    fintrx_firm_name = 'Matched Firm Name',
    match_confidence = 1.0,
    match_method = 'manual',
    needs_manual_review = FALSE,
    manual_review_notes = 'Manually verified match',
    manual_review_date = CURRENT_TIMESTAMP(),
    manual_review_by = 'russell.moss@savvywealth.com'
WHERE broker_protocol_firm_name = 'Firm Name from Broker Protocol';
```

---

#### Task 6.3: Create Summary Report

Generate a final summary of what was built.

```markdown
# File: C:\Users\russe\Documents\Lead Scoring\Broker_protocol\IMPLEMENTATION_SUMMARY.md

# Broker Protocol Automation - Implementation Summary

**Date**: [Date]
**Status**: ✅ COMPLETE

## What Was Built

### BigQuery Infrastructure
- ✅ `broker_protocol_members` - Main data table
- ✅ `broker_protocol_history` - Change tracking
- ✅ `broker_protocol_scrape_log` - Monitoring
- ✅ `broker_protocol_manual_matches` - Override table
- ✅ 3 monitoring views (match_quality, recent_changes, needs_review)

### Python Scripts
- ✅ `broker_protocol_parser.py` - Parse Excel
- ✅ `firm_matcher.py` - Match to FINTRX
- ✅ `broker_protocol_updater.py` - Merge data
- ✅ `broker_protocol_automation.py` - End-to-end automation

### Documentation
- ✅ Python scripts README
- ✅ SQL monitoring queries
- ✅ This summary

## Initial Data Load Results

**Total Firms**: [Number]
**Match Rate**: [Percentage]%
**Needs Review**: [Number] ([Percentage]%)

**Match Methods**:
- Exact: [Number]
- Normalized: [Number]
- Base Name: [Number]
- Fuzzy: [Number]
- Manual: [Number]
- Unmatched: [Number]

## Next Steps (Manual)

### Immediate (User Actions)
1. ⏳ Set up n8n workflow (see N8N_SETUP_GUIDE.md)
2. ⏳ Review unmatched firms
3. ⏳ Configure monitoring alerts

### Week 2
- Manual review of low-confidence matches
- Refine matching rules if needed
- Test automated runs

### Month 1
- Integrate with lead scoring model
- Add broker protocol features to ML pipeline
- Train sales team

## File Locations

**BigQuery**:
- Project: `savvy-gtm-analytics`
- Dataset: `SavvyGTMData`

**Python Scripts**:
- Location: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\`
- Ready to deploy to Cloud Functions or run locally
- For n8n deployment, scripts will be copied to `/opt/n8n/scripts/broker-protocol/` (see N8N_SETUP_GUIDE.md)

**JavaScript Scraper**:
- Location: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_scrape.js`
- For use in n8n workflow

## Monitoring

**Daily**: Check scrape log for failures
**Weekly**: Review firms needing manual match
**Monthly**: Validate match quality metrics

**Key Queries**:
```sql
-- Check last run
SELECT * FROM broker_protocol_scrape_log ORDER BY scrape_timestamp DESC LIMIT 1;

-- Check match quality
SELECT * FROM broker_protocol_match_quality;
```

## Support

- **Technical Issues**: Check troubleshooting section in Python scripts README
- **Data Questions**: See SQL monitoring queries
- **Enhancement Requests**: Document in backlog

---

**System Status**: ✅ PRODUCTION READY
**Next Manual Step**: n8n workflow setup
```

---

## ✅ Final Validation Checklist

Before declaring complete, verify:

### BigQuery
- [ ] All 4 tables created
- [ ] All 3 views created
- [ ] Data loaded successfully
- [ ] No errors in table structures

### Data Quality
- [ ] Total firms > 2,000
- [ ] Match rate > 70%
- [ ] Needs review < 20%
- [ ] No duplicate firm names
- [ ] Join dates >90% populated

### Scripts
- [ ] Parser runs without errors
- [ ] Matcher runs without errors
- [ ] Updater runs without errors
- [ ] Automation script runs end-to-end

### Documentation
- [ ] Python README created
- [ ] SQL queries documented
- [ ] Implementation summary created
- [ ] All files in `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\`

### Files to Present
- [ ] `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_automation.py` (main script)
- [ ] `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\broker_protocol_updater.py` (merge logic)
- [ ] `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\PYTHON_SCRIPTS_README.md` (documentation)
- [ ] `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\monitoring_queries.sql` (SQL reference)
- [ ] `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\IMPLEMENTATION_SUMMARY.md` (summary report)

---

## 🎯 Success Criteria

You have successfully completed development when:

1. ✅ All BigQuery tables exist and are populated
2. ✅ Match rate is >70%
3. ✅ Python automation script runs successfully end-to-end
4. ✅ Data quality validation passes
5. ✅ Documentation is complete

**Current Status**: 🟡 IN PROGRESS

Update this status to ✅ COMPLETE when all criteria are met.

---

## 📞 Questions or Issues?

If you encounter any issues:

1. Check error messages carefully
2. Verify BigQuery permissions
3. Check data file format hasn't changed
4. Review validation queries
5. Check Python dependencies

**Most Common Issues**:
- BigQuery permission errors → Check IAM roles
- Low match rate → Review unmatched firms, adjust threshold
- Date parsing failures → Check for new date formats in Excel
- Duplicate firm names → Data quality issue in source

---

## 🎉 Next Steps After Completion

Once Cursor.ai completes development:

1. User sets up n8n workflow (see N8N_SETUP_GUIDE.md)
2. User tests first automated run
3. User performs manual review of unmatched firms
4. User integrates with lead scoring model

**Expected Timeline**:
- Cursor development: Done automatically
- n8n setup: 2-3 hours (manual)
- First review cycle: 1 hour (manual)
- Lead scoring integration: 1-2 weeks (depends on ML pipeline)

---

**Last Updated**: [Date]
**Version**: 1.0
**Status**: Ready for Autonomous Development
