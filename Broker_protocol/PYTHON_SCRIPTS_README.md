# Broker Protocol Python Scripts

Complete documentation for all Python scripts in the Broker Protocol automation system.

## Overview

This package contains scripts to download, parse, match, and merge Broker Protocol member firm data with FINTRX CRD IDs for lead enrichment and scoring.

## Scripts

### 1. broker_protocol_parser.py
Parses Excel file from JSHeld website and extracts firm information.

**Usage**:
```bash
python broker_protocol_parser.py input.xlsx -o output.csv -v
```

**Arguments**:
- `input.xlsx` - Path to Excel file (required)
- `-o, --output` - Output CSV path (default: from config)
- `-v, --verbose` - Verbose output
- `--test` - Test mode (print sample output)

**Output**: CSV with columns:
- `firm_name` - Cleaned firm name
- `former_names` - f/k/a names (comma-separated)
- `dbas` - d/b/a names (comma-separated)
- `has_name_change` - Boolean flag
- `firm_name_raw` - Original raw name from Excel
- `date_joined` - Date joined Broker Protocol
- `date_withdrawn` - Date withdrawn (NULL if current member)
- `is_current_member` - Boolean flag
- `date_notes_cleaned` - Cleaned date notes
- `date_notes_raw` - Original raw date notes
- `joinder_qualifications` - Qualifications text
- `scrape_timestamp` - Timestamp of parsing

**Example**:
```bash
python broker_protocol_parser.py "The-Broker-Protocol-Member-Firms-12-22-25.xlsx" -v -o "output/parsed.csv"
```

---

### 2. firm_matcher.py
Matches broker protocol firms to FINTRX CRD IDs using multiple matching strategies.

**Usage**:
```bash
python firm_matcher.py broker_parsed.csv fintrx_firms.csv -o matched.csv -t 0.60 -v
```

**Arguments**:
- `broker_parsed.csv` - Path to parsed broker protocol CSV (required)
- `fintrx_firms.csv` - Path to FINTRX firms CSV (required)
- `-o, --output` - Output CSV path (default: from config)
- `-t, --threshold` - Confidence threshold for fuzzy matching (default: 0.60)
- `-v, --verbose` - Verbose output
- `--firm` - Test matching for a single firm name

**Match Methods** (in order of priority):
- `exact` - Exact match (case-insensitive), confidence: 1.0
- `normalized_exact` - Normalized exact match (remove punctuation), confidence: 0.95
- `base_name` - Base name match (remove entity suffixes), confidence: 0.85
- `fuzzy` - Fuzzy match (similarity scoring), confidence: 0.60-0.84
- `unmatched` - No match found

**Output**: CSV with all original columns plus:
- `firm_crd_id` - Matched FINTRX CRD ID
- `fintrx_firm_name` - Matched FINTRX firm name
- `match_confidence` - Confidence score (0.0 to 1.0)
- `match_method` - Match method used
- `needs_manual_review` - Boolean flag (True if confidence < 0.85 or unmatched)

**Example**:
```bash
# Test single firm
python firm_matcher.py parsed.csv fintrx.csv --firm "Morgan Stanley Wealth Management"

# Batch match
python firm_matcher.py parsed.csv fintrx.csv -o matched.csv -v
```

**Performance Optimizations**:
- Uses RapidFuzz for 10-100x faster fuzzy matching
- Bucket-based matching (only compares firms with same first character)
- Estimated 50-500x speedup over naive approach

---

### 3. broker_protocol_updater.py
Merges new matched data with existing BigQuery data, tracking changes.

**Usage**:
```bash
# Dry run first (recommended)
python broker_protocol_updater.py matched.csv --dry-run

# Then run for real
python broker_protocol_updater.py matched.csv --scrape-id "scrape_20251222"
```

**Arguments**:
- `matched.csv` - Path to matched CSV file (required)
- `--scrape-id` - Scrape run ID (auto-generated if not provided)
- `--dry-run` - Dry run mode (no database changes)

**What it does**:
1. Loads new matched data from CSV
2. Loads existing data from BigQuery
3. Compares and identifies:
   - Newly joined firms
   - Newly withdrawn firms
   - Updated firms (matches, info changes)
4. Updates BigQuery tables:
   - Inserts new firms
   - Updates existing firms
   - Marks withdrawn firms
   - Logs all changes to history table
   - Updates scrape log

**Change Types Tracked**:
- `JOINED` - New firm joined protocol
- `WITHDREW` - Firm withdrew from protocol
- `MATCHED` - Firm got matched (or match changed)
- `INFO_UPDATED` - Firm info updated (names, dates, etc.)
- `NAME_CHANGED` - Firm name changed

**Example**:
```bash
python broker_protocol_updater.py "output/broker_protocol_matched.csv" --dry-run
```

---

### 4. broker_protocol_automation.py
End-to-end automation script that runs the complete pipeline.

**Usage**:
```bash
python broker_protocol_automation.py excel_file.xlsx -v
```

**Arguments**:
- `excel_file.xlsx` - Path to Excel file (required)
- `-v, --verbose` - Verbose output
- `--dry-run` - Dry run (skip BigQuery merge)

**Pipeline Steps**:
1. **Parse Excel** - Extracts firm data from Excel file
2. **Load FINTRX Firms** - Queries BigQuery for FINTRX firm list
3. **Match Firms** - Matches broker protocol firms to FINTRX CRD IDs
4. **Merge with BigQuery** - Updates BigQuery with new/updated data

**Output**:
- Exit code 0 on success, 1 on failure
- Status messages printed to stdout
- Error messages printed to stderr
- Results dictionary with metrics

**Example**:
```bash
# Full automation
python broker_protocol_automation.py "The-Broker-Protocol-Member-Firms-12-22-25.xlsx" -v

# Dry run (testing)
python broker_protocol_automation.py "The-Broker-Protocol-Member-Firms-12-22-25.xlsx" --dry-run
```

**Called by n8n workflow** for automated biweekly runs.

---

### 5. export_fintrx_firms.py
Exports FINTRX firms from BigQuery to CSV for matching.

**Usage**:
```bash
python export_fintrx_firms.py -o output/fintrx_firms.csv
```

**Arguments**:
- `-o, --output` - Output CSV path (default: from config)

**Output**: CSV with columns:
- `CRD_ID` - FINTRX CRD ID
- `NAME` - Firm name
- `TOTAL_AUM` - Total assets under management
- `NUM_OF_EMPLOYEES` - Number of employees

---

### 6. load_to_bigquery.py
Loads matched data to BigQuery (initial load).

**Usage**:
```bash
python load_to_bigquery.py matched.csv --excel-file "file.xlsx" --dry-run
```

**Arguments**:
- `matched.csv` - Path to matched CSV file (required)
- `--excel-file` - Name of source Excel file (for logging)
- `--source-url` - Source URL (for logging)
- `--dry-run` - Dry run mode
- `--skip-validation` - Skip data quality validation

**Note**: This script is typically only used for initial data load. Subsequent updates use `broker_protocol_updater.py`.

---

## Testing

Test each component individually:

```bash
# 1. Test parser
python broker_protocol_parser.py test.xlsx --test

# 2. Test matcher on single firm
python firm_matcher.py parsed.csv fintrx.csv --firm "Morgan Stanley"

# 3. Test matcher batch
python test_firm_matcher.py --test all

# 4. Test updater (dry run)
python broker_protocol_updater.py matched.csv --dry-run

# 5. Test full automation (dry run)
python broker_protocol_automation.py test.xlsx --dry-run -v
```

---

## Validation Scripts

### validate_parser_output.py
Validates parser output quality.

```bash
python validate_parser_output.py output/broker_protocol_parsed.csv
```

### validate_matching_results.py
Validates matching results.

```bash
python validate_matching_results.py output/broker_protocol_matched.csv
```

### test_automation.py
Validates automation results in BigQuery.

```bash
python test_automation.py
```

---

## Configuration

All scripts use `config.py` for centralized configuration:

- **Paths**: Project directories, file paths
- **BigQuery**: Project ID, dataset names, table names
- **Matching**: Confidence thresholds, review thresholds
- **Settings**: Feature flags, debug modes

Edit `config.py` to customize settings.

---

## Dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

Required packages:
- `pandas>=2.0.0`
- `openpyxl>=3.1.0`
- `python-dateutil>=2.8.0`
- `google-cloud-bigquery>=3.11.0`
- `rapidfuzz>=3.0.0` (for fast fuzzy matching)

---

## Monitoring

Check data quality in BigQuery:

```sql
-- Match quality summary
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_match_quality`;

-- Recent changes
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_recent_changes` LIMIT 10;

-- Scrape log
SELECT * FROM `savvy-gtm-analytics.SavvyGTMData.broker_protocol_scrape_log`
ORDER BY scrape_timestamp DESC LIMIT 5;
```

See `monitoring_queries.sql` for more queries.

---

## Troubleshooting

### Common Issues

**Parser Issues**:
- Excel file format changed → Update header row detection in parser
- Date parsing failures → Check `date_notes_raw` column for unparsed dates
- Missing columns → Verify Excel file structure

**Matcher Issues**:
- Low match rate → Lower confidence threshold (`-t 0.50`)
- Slow performance → Ensure RapidFuzz is installed
- False positives → Review fuzzy matches, adjust threshold

**Updater Issues**:
- SQL syntax errors → Check for special characters in firm names
- Type errors → Ensure firm_crd_id is integer
- Duplicate errors → Check for duplicate firm names in source data

**BigQuery Issues**:
- Permission errors → Check IAM roles for service account
- Table not found → Verify table names in config.py
- Query timeout → Optimize queries or increase timeout

### Getting Help

1. Check error messages carefully
2. Review validation scripts output
3. Check BigQuery logs
4. Review `config.py` settings
5. See `IMPLEMENTATION_SUMMARY.md` for system overview

---

## File Locations

**Scripts**: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\`
**Output**: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\output\`
**Logs**: `C:\Users\russe\Documents\Lead Scoring\Broker_protocol\logs\`

---

**Last Updated**: December 22, 2025
**Version**: 1.0

