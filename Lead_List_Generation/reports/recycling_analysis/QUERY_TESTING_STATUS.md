# Recyclable Pool Query Testing Status

**Date**: December 24, 2025  
**Status**: ⚠️ SQL File Creation Required Before Testing

---

## Current Status

### ✅ Completed
1. **Test Script Created**: `scripts/recycling/test_recyclable_query.py`
   - Script ready to test query with LIMIT 100
   - Includes validation queries (V1, V2, V3)
   - Includes additional validations (NULLs, duplicates, ranking)

2. **Documentation Created**: `reports/Recyclable_Lead_List_System_Documentation.md`
   - Comprehensive technical documentation
   - Step-by-step build process
   - Business logic evolution

### ⚠️ Pending
1. **SQL File Creation**: `sql/recycling/recyclable_pool_master_v2.1.sql`
   - SQL query exists in guide but needs to be extracted to file
   - File path: `Lead_List_Generation/sql/recycling/recyclable_pool_master_v2.1.sql`

---

## Next Steps

### Step 1: Create SQL File
Extract the SQL query from `Monthly_Recyclable_Lead_List_Generation_Guide_V2.md` (lines 91-715) and save to:
```
Lead_List_Generation/sql/recycling/recyclable_pool_master_v2.1.sql
```

### Step 2: Test Query with LIMIT 100
Run the test script:
```bash
cd Lead_List_Generation
python scripts/recycling/test_recyclable_query.py
```

**Expected Output**:
- Query executes successfully
- Returns 100 records (or fewer if pool is smaller)
- Shows summary statistics
- Runs validation queries

### Step 3: Validation Queries

The test script will automatically run:

#### V1: Date Type Issues
- **Check**: `years_at_current_firm < 0 OR years_at_current_firm > 50`
- **Expected**: 0 rows (no invalid tenure values)

#### V2: Recent Firm Changers
- **Check**: `changed_firms_since_close = TRUE AND years_at_current_firm < 2`
- **Expected**: 0 rows (no recent movers should slip through)

#### V3: Priority Distribution
- **Check**: Count and average conversion by priority tier
- **Expected**: Reasonable distribution (P1-P2 should be 10-20% of list)

#### V4: Additional Validations
- **NULL Values**: Check critical fields (record_id, fa_crd, recycle_priority)
- **Duplicates**: Check for duplicate CRDs
- **Ranking**: Verify Opportunities appear before Leads

---

## Validation Criteria

### ✅ Pass Criteria
1. Query executes without errors
2. Returns 100 records (or available pool size)
3. V1 validation: 0 rows with date issues
4. V2 validation: 0 rows with recent firm changers
5. V3 validation: Priority distribution looks reasonable
6. V4 validation: No NULLs in critical fields, no duplicates, correct ranking

### ❌ Fail Criteria
- Any syntax errors in query
- Date type issues found (V1)
- Recent firm changers found (V2)
- NULL values in critical fields
- Duplicate CRDs
- Incorrect ranking (Leads before Opportunities)

---

## SQL Query Structure

The query consists of:

1. **Part A**: Exclusion Lists (TEMP TABLES)
   - No-go dispositions/reasons
   - Timing dispositions/reasons
   - General recyclable dispositions/reasons
   - Excluded firms

2. **Part B**: Last Task Activity (CTEs)
   - Lead last tasks
   - Opportunity last tasks
   - Users lookup

3. **Part C**: Recyclable Opportunities
   - Closed lost opportunities
   - FINTRX enrichment
   - PIT-compliant employment history join
   - V4 scoring
   - Firm change analysis

4. **Part D**: Recyclable Leads
   - Closed leads
   - Similar enrichment as opportunities
   - Deduplication (exclude if already in opportunities)

5. **Part E**: Priority Logic
   - Combine opportunities and leads
   - Apply priority tiers (P1-P6)
   - Rank by priority, record type, V4 score, days since contact
   - Select top N (target_count)

---

## Notes

- The query uses `DECLARE` statements for parameters (target_count, min_days, etc.)
- For testing, `target_count` should be set to 100
- The query includes PIT-compliant employment history joins to avoid data leakage
- Date casting (`DATE()`) is used throughout to handle TIMESTAMP vs DATE mismatches
- Field validation uses `COALESCE` for optional fields

---

## Once SQL File is Created

After creating the SQL file, the test script will:
1. Read the SQL file
2. Modify `target_count` to 100
3. Execute the query
4. Display results summary
5. Run all validation queries
6. Report pass/fail status

---

**Next Action**: Extract SQL from guide and create `sql/recycling/recyclable_pool_master_v2.1.sql`



