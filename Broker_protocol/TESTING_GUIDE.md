# Broker Protocol Automation - Testing Guide

This guide shows you how to test the automation locally before deploying to n8n.

---

## 🧪 Testing Philosophy

**Test locally first, then deploy to automation.**

### Testing Levels
1. **Unit Tests** - Test individual Python functions
2. **Integration Tests** - Test parser + matcher together
3. **End-to-End Tests** - Test full automation pipeline
4. **Production Validation** - Test in n8n workflow

---

## ⚙️ Setup for Testing

### 1. Install Test Dependencies

```bash
pip install pytest pytest-cov --break-system-packages
```

### 2. Create Test Data Directory

```bash
cd "C:\Users\russe\Documents\Lead Scoring\Broker_protocol"
mkdir test_data
```

### 3. Copy Sample Excel File

```bash
# Copy your sample file to test_data folder
copy TheBrokerProtocolMemberFirms122225.xlsx test_data\
```

---

## 🧪 Test 1: Parser (Excel → CSV)

### Test the parser on sample data

```bash
# Test mode (shows samples only)
python broker_protocol_parser.py test_data\TheBrokerProtocolMemberFirms122225.xlsx --test

# Full parse with verbose output
python broker_protocol_parser.py test_data\TheBrokerProtocolMemberFirms122225.xlsx -v -o test_data\parsed_output.csv
```

### Expected Output:
```
Reading Excel file: test_data\TheBrokerProtocolMemberFirms122225.xlsx
Raw rows: 2587
After cleaning: 2587 rows

Parsing firm names...
Extracting dates...

Parsing complete!
Total firms: 2587
Current members: 2345
Withdrawn members: 242
Firms with name changes: 127
Firms with join dates: 2511 (97.1%)
Firms with withdrawal dates: 242 (9.4%)
```

### Validation Checks:
- [ ] Total firms: 2,500-3,000
- [ ] Join dates: >90%
- [ ] No parsing errors
- [ ] CSV file created

---

## 🧪 Test 2: FINTRX Export

### Export FINTRX firms for matching

```python
# test_fintrx_export.py
from google.cloud import bigquery
import pandas as pd
from config import TABLE_FINTRX_FIRMS

client = bigquery.Client(project='savvy-gtm-analytics')

print("Exporting FINTRX firms...")
query = f"SELECT CRD_ID, NAME FROM `{TABLE_FINTRX_FIRMS}` WHERE NAME IS NOT NULL"
df = client.query(query).to_dataframe()

df.to_csv('test_data/fintrx_firms.csv', index=False)
print(f"Exported {len(df)} firms")
```

```bash
python test_fintrx_export.py
```

### Expected Output:
```
Exporting FINTRX firms...
Exported 45233 firms
```

### Validation Checks:
- [ ] 40K-50K firms exported
- [ ] CRD_ID and NAME columns present
- [ ] No nulls in NAME
- [ ] CSV file created

---

## 🧪 Test 3: Matcher (Single Firm)

### Test matching on specific firms

```bash
# Test well-known firm
python firm_matcher.py test_data\parsed_output.csv test_data\fintrx_firms.csv --firm "Morgan Stanley Wealth Management"

# Test firm with name change
python firm_matcher.py test_data\parsed_output.csv test_data\fintrx_firms.csv --firm "UBS Financial Services Inc."

# Test smaller firm
python firm_matcher.py test_data\parsed_output.csv test_data\fintrx_firms.csv --firm "Cetera Advisor Networks LLC"
```

### Expected Output (example):
```
Matching: Morgan Stanley Wealth Management

  ✓ EXACT MATCH: Morgan Stanley Wealth Management

Result:
  CRD ID: 149777
  FINTRX Name: Morgan Stanley Wealth Management
  Confidence: 1.000
  Method: exact
```

### Validation Checks:
- [ ] Large firms match exactly
- [ ] Confidence scores reasonable
- [ ] Match method makes sense
- [ ] CRD IDs look valid

---

## 🧪 Test 4: Matcher (Full Batch)

### Test full matching on all firms

```bash
# Run with verbose output
python firm_matcher.py test_data\parsed_output.csv test_data\fintrx_firms.csv -v -o test_data\matched_output.csv
```

### Expected Output:
```
Matching 2587 broker protocol firms...
FINTRX database: 45233 firms
Confidence threshold: 0.60

  Processed 100/2587 firms...
  Processed 200/2587 firms...
  ...
  Processed 2587/2587 firms...

=== MATCHING SUMMARY ===
Total firms: 2587

By match method:
exact              745
normalized_exact   389
base_name          234
fuzzy              612
unmatched          607

Match rate: 1980 / 2587 (76.5%)
Average confidence (matched): 0.876
Needs manual review: 412 (15.9%)
```

### Validation Checks:
- [ ] Match rate: >70%
- [ ] Exact matches: 20-30%
- [ ] Fuzzy matches: 30-50%
- [ ] Needs review: <20%
- [ ] CSV files created

---

## 🧪 Test 5: Match Quality Analysis

### Analyze matching results

```python
# test_match_quality.py
import pandas as pd

df = pd.read_csv('test_data/matched_output.csv')

print("=== MATCH QUALITY ANALYSIS ===\n")

# Overall stats
print(f"Total firms: {len(df)}")
print(f"Matched: {df['firm_crd_id'].notna().sum()} ({df['firm_crd_id'].notna().sum()/len(df)*100:.1f}%)")
print(f"Needs review: {df['needs_manual_review'].sum()} ({df['needs_manual_review'].sum()/len(df)*100:.1f}%)")

# By method
print("\n=== BY METHOD ===")
print(df['match_method'].value_counts())

# Confidence distribution
print("\n=== CONFIDENCE DISTRIBUTION ===")
matched = df[df['firm_crd_id'].notna()]
print(matched['match_confidence'].describe())

# Sample high-confidence fuzzy matches
print("\n=== SAMPLE FUZZY MATCHES (HIGH CONFIDENCE) ===")
fuzzy = df[(df['match_method'] == 'fuzzy') & (df['match_confidence'] >= 0.80)]
print(fuzzy[['firm_name', 'fintrx_firm_name', 'match_confidence']].head(10))

# Sample low-confidence matches
print("\n=== SAMPLE FUZZY MATCHES (LOW CONFIDENCE - REVIEW) ===")
low = df[(df['match_method'] == 'fuzzy') & (df['match_confidence'] < 0.70)]
print(low[['firm_name', 'fintrx_firm_name', 'match_confidence']].head(10))

# Unmatched firms
print("\n=== SAMPLE UNMATCHED FIRMS ===")
unmatched = df[df['firm_crd_id'].isna()]
print(unmatched[['firm_name', 'former_names']].head(10))
```

```bash
python test_match_quality.py
```

### Validation Checks:
- [ ] Results look reasonable
- [ ] High-confidence matches are correct
- [ ] Low-confidence matches need review
- [ ] Unmatched firms are truly not in FINTRX

---

## 🧪 Test 6: BigQuery Write (Dry Run)

### Test BigQuery operations without writing

```python
# test_bigquery_dry_run.py
from google.cloud import bigquery
import pandas as pd
from config import GCP_PROJECT_ID, OUTPUT_DATASET

client = bigquery.Client(project=GCP_PROJECT_ID)

# Load test data
df = pd.read_csv('test_data/matched_output.csv')

# Check if tables exist
tables = [
    'broker_protocol_members',
    'broker_protocol_history',
    'broker_protocol_scrape_log'
]

print("=== BIGQUERY CONNECTIVITY TEST ===\n")

for table_name in tables:
    table_id = f"{GCP_PROJECT_ID}.{OUTPUT_DATASET}.{table_name}"
    try:
        table = client.get_table(table_id)
        print(f"✓ Table exists: {table_name}")
        print(f"  Rows: {table.num_rows}")
        print(f"  Size: {table.num_bytes / 1024 / 1024:.1f} MB")
    except Exception as e:
        print(f"✗ Table missing or error: {table_name}")
        print(f"  Error: {str(e)}")

print("\n=== TEST DATA ===")
print(f"Rows to insert: {len(df)}")
print(f"Columns: {list(df.columns)}")

print("\n✓ Dry run complete - no data written")
```

```bash
python test_bigquery_dry_run.py
```

### Expected Output:
```
=== BIGQUERY CONNECTIVITY TEST ===

✓ Table exists: broker_protocol_members
  Rows: 2587
  Size: 1.2 MB
✓ Table exists: broker_protocol_history
  Rows: 42
  Size: 0.1 MB
✓ Table exists: broker_protocol_scrape_log
  Rows: 3
  Size: 0.01 MB

=== TEST DATA ===
Rows to insert: 2587
Columns: ['firm_name', 'firm_crd_id', ...]

✓ Dry run complete - no data written
```

### Validation Checks:
- [ ] All tables exist
- [ ] BigQuery connection works
- [ ] Service account has permissions
- [ ] Data structure looks correct

---

## 🧪 Test 7: Update Logic (Dry Run)

### Test the updater without writing

```bash
python broker_protocol_updater.py test_data\matched_output.csv --dry-run
```

### Expected Output:
```
=== BROKER PROTOCOL DATA MERGE ===
Scrape Run ID: scrape_20241222_143022
Dry Run: True

Loading new data...
  New data: 2587 firms
Loading existing data...
  Existing data: 2587 firms

Analyzing changes...
  Newly joined firms: 0
  Newly withdrawn firms: 0
  Existing firms (checking for updates): 2587

=== SUMMARY ===
New firms to add: 0
Existing firms to update: 0
Changes to log: 0

⚠️ DRY RUN - No changes will be made to database
```

### Validation Checks:
- [ ] Change detection works
- [ ] No errors in logic
- [ ] Summary makes sense

---

## 🧪 Test 8: Full Automation (Test Mode)

### Test end-to-end automation

Edit `config.py` temporarily:
```python
TEST_MODE = True
TEST_LIMIT = 100
ENABLE_BIGQUERY_WRITE = False  # Dry run
```

```bash
python broker_protocol_automation.py test_data\TheBrokerProtocolMemberFirms122225.xlsx -v
```

### Expected Output:
```
============================================================
STEP 1: Parsing Excel file
============================================================
✓ Parsed 100 firms (TEST MODE)

============================================================
STEP 2: Loading FINTRX firms
============================================================
✓ Loaded 45233 FINTRX firms

============================================================
STEP 3: Matching firms to FINTRX
============================================================
✓ Matched 82 firms (82.0%)
  Needs review: 15

============================================================
STEP 4: Merging with existing data
============================================================
⚠️ DRY RUN - No changes made

============================================================
AUTOMATION COMPLETE
============================================================
Status: SUCCESS
Duration: 45.2 seconds
```

### Validation Checks:
- [ ] All steps complete
- [ ] No errors
- [ ] Performance reasonable (<2 minutes)
- [ ] Results look correct

---

## 🧪 Test 9: Error Handling

### Test what happens when things fail

**Test 1: Invalid Excel file**
```bash
python broker_protocol_automation.py nonexistent.xlsx
```
Expected: Clear error message, graceful exit

**Test 2: BigQuery connection failure**
```bash
# Temporarily break credentials
set GOOGLE_APPLICATION_CREDENTIALS=invalid.json
python broker_protocol_automation.py test_data\TheBrokerProtocolMemberFirms122225.xlsx
```
Expected: Authentication error, no data corruption

**Test 3: Malformed Excel data**
Create a test file with missing columns and test parser

### Validation Checks:
- [ ] Errors are caught gracefully
- [ ] Error messages are clear
- [ ] No data corruption
- [ ] Logs contain useful info

---

## 🧪 Test 10: Performance Benchmarking

### Measure performance

```python
# test_performance.py
import time
import pandas as pd
from firm_matcher import batch_match_firms

# Load data
broker_df = pd.read_csv('test_data/parsed_output.csv')
fintrx_df = pd.read_csv('test_data/fintrx_firms.csv')

# Test different sizes
test_sizes = [100, 500, 1000, 2587]

print("=== PERFORMANCE BENCHMARK ===\n")

for size in test_sizes:
    if size > len(broker_df):
        continue
    
    test_df = broker_df.head(size)
    
    start = time.time()
    result = batch_match_firms(test_df, fintrx_df, verbose=False)
    duration = time.time() - start
    
    print(f"Firms: {size:4d} | Time: {duration:6.2f}s | Per firm: {duration/size*1000:.1f}ms")

print("\n✓ Benchmark complete")
```

```bash
python test_performance.py
```

### Expected Output:
```
=== PERFORMANCE BENCHMARK ===

Firms:  100 | Time:   3.45s | Per firm: 34.5ms
Firms:  500 | Time:  18.23s | Per firm: 36.5ms
Firms: 1000 | Time:  37.12s | Per firm: 37.1ms
Firms: 2587 | Time:  95.67s | Per firm: 37.0ms

✓ Benchmark complete
```

### Performance Targets:
- [ ] <40ms per firm average
- [ ] Full run <3 minutes for 2,500 firms
- [ ] Linear scaling (not exponential)

---

## ✅ Final Pre-Deployment Checklist

Before deploying to n8n:

### Code Quality
- [ ] All tests pass
- [ ] No hardcoded credentials
- [ ] Config file updated
- [ ] Error handling tested

### Data Quality
- [ ] Match rate >70%
- [ ] Sample matches reviewed manually
- [ ] Unmatched firms reviewed
- [ ] No data corruption

### Documentation
- [ ] All guides updated
- [ ] SQL templates tested
- [ ] Configuration documented
- [ ] Known issues documented

### BigQuery
- [ ] All tables created
- [ ] Views working
- [ ] Permissions correct
- [ ] Initial data loaded

### Integration
- [ ] Python scripts in correct location
- [ ] Dependencies installed
- [ ] Environment variables set
- [ ] Paths correct for n8n

---

## 🐛 Troubleshooting Test Failures

### Parser Test Fails
- Check Excel file format hasn't changed
- Verify pandas and openpyxl installed
- Check for special characters in firm names

### Matcher Test Fails
- Verify FINTRX export is complete
- Check confidence threshold setting
- Review normalization logic

### BigQuery Test Fails
- Check service account credentials
- Verify project ID is correct
- Check dataset permissions
- Ensure tables exist

### Performance Test Fails
- Check system resources
- Close other applications
- Try smaller batch sizes
- Check network latency

---

## 📊 Test Results Template

Document your test results:

```
=== TEST RESULTS - [Date] ===

Environment:
- OS: Windows 11
- Python: 3.11.x
- Dataset: FinTrx_data_CA

Test 1: Parser
✓ PASS - 2587 firms parsed in 8.2s

Test 2: FINTRX Export  
✓ PASS - 45233 firms exported

Test 3: Single Firm Match
✓ PASS - All test firms matched correctly

Test 4: Batch Match
✓ PASS - 76.5% match rate, 15.9% need review

Test 5: Match Quality
✓ PASS - Results look reasonable

Test 6: BigQuery Dry Run
✓ PASS - All tables exist, connectivity OK

Test 7: Update Logic
✓ PASS - Change detection working

Test 8: Full Automation
✓ PASS - All steps completed successfully

Test 9: Error Handling
✓ PASS - Errors handled gracefully

Test 10: Performance
✓ PASS - 37ms per firm, 95s total

Overall: ✅ READY FOR DEPLOYMENT

Notes:
- Match rate slightly better than expected (76.5% vs 70% target)
- Performance good (<2 minutes)
- No errors encountered
- Ready to deploy to n8n
```

---

**Last Updated**: December 22, 2024  
**Next Step**: Deploy to n8n workflow (see N8N_SETUP_GUIDE.md)
