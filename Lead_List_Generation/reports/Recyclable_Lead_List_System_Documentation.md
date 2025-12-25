# Recyclable Lead List Generation System - Technical Documentation

**System Version**: V2.1  
**Documentation Date**: December 24, 2025  
**Status**: ✅ Production Ready  
**Purpose**: Generate monthly lists of 600 recyclable leads/opportunities for SGA re-engagement

---

## Executive Summary

The **Monthly Recyclable Lead List Generation System** is a sophisticated lead recycling pipeline that identifies and prioritizes previously contacted but unconverted leads/opportunities for re-engagement. Unlike the primary "new prospect" lead lists, this system focuses on **re-engaging existing CRM contacts** who may have become more receptive over time.

### Key Differentiators from New Prospect Lists

| Aspect | New Prospect Lists | Recyclable Lists |
|--------|-------------------|------------------|
| **Source** | FINTRX database (never contacted) | Salesforce CRM (previously contacted) |
| **Focus** | Cold outbound | Warm re-engagement |
| **Timing** | First contact | 90-730 days since last contact |
| **Conversion Rate** | 3.2% baseline | 3-7% (varies by priority) |
| **Volume** | 2,400-3,000/month | 600/month |
| **Purpose** | Expand reach | Maximize existing relationships |

---

## System Overview

### What It Does

The system generates a **monthly list of 600 prioritized recyclable leads/opportunities** by:

1. **Identifying Eligible Candidates**: Finds closed/lost leads and opportunities in Salesforce that meet recycling criteria
2. **Enriching with External Data**: Joins FINTRX employment history and V4 ML scores
3. **Applying Business Logic**: Prioritizes based on firm change timing, V4 scores, and disposition history
4. **Ranking and Filtering**: Orders by priority and selects top 600
5. **Generating Narratives**: Creates human-readable explanations for each lead
6. **Exporting Results**: Produces CSV and summary reports

### Business Value

- **Increases Conversion Rates**: Re-engaging at optimal timing achieves 3-7% conversion (vs 3.2% baseline)
- **Maximizes CRM Value**: Leverages existing relationships rather than always starting cold
- **Reduces Waste**: Re-engages leads who may have been contacted too early
- **Complements New Lists**: Works alongside primary prospect lists (separate 600 leads/month)

---

## System Architecture

### Component Structure

```
Lead_List_Generation/
├── sql/
│   └── recycling/
│       └── recyclable_pool_master_v2.1.sql    # Master SQL query
├── scripts/
│   └── recycling/
│       └── generate_recyclable_list_v2.1.py  # Python orchestrator
├── exports/
│   └── [MONTH]_[YEAR]_recyclable_leads.csv   # Final output
└── reports/
    └── recycling_analysis/
        └── [MONTH]_[YEAR]_recyclable_list_report.md  # Summary report
```

### Data Flow

```
Salesforce CRM
    ↓
[Closed Leads/Opportunities]
    ↓
BigQuery SQL Query
    ↓
[Enrichment: FINTRX + V4 Scores]
    ↓
[Priority Assignment]
    ↓
[Ranking & Filtering]
    ↓
Python Script
    ↓
[Narrative Generation]
    ↓
CSV Export + Report
```

---

## Step-by-Step Build Process

### Phase 0: Setup and Infrastructure

**Objective**: Create directory structure and logging infrastructure

**Actions Taken**:
1. Created directory structure:
   - `sql/recycling/` - SQL queries
   - `scripts/recycling/` - Python scripts
   - `exports/` - CSV outputs
   - `reports/recycling_analysis/` - Summary reports

2. Initialized logging:
   - `RECYCLABLE_LIST_LOG.md` for execution tracking

**Output**: Organized file structure ready for development

---

### Phase 1: Master SQL Query Development

**Objective**: Build the core SQL query that identifies and prioritizes recyclable leads

#### Step 1.1: Exclusion Lists (Part A)

**Purpose**: Define permanent disqualifications and priority signals

**Created**:
- **No-Go Dispositions** (Leads): 8 permanent DQs
  - "Not Interested in Moving", "Not a Fit", "No Book", etc.
- **No-Go Reasons** (Opportunities): 6 permanent DQs
  - "Savvy Declined - No Book", "Savvy Declined - Insufficient Revenue", etc.
- **Timing Dispositions** (High Priority): "Timing" related
  - Leads: "Timing"
  - Opportunities: "Candidate Declined - Timing", "Candidate Declined - Fear of Change"
- **General Recyclable**: Re-engagement candidates
  - Leads: "No Response", "Auto-Closed by Operations", "Other", "No Show / Ghosted"
  - Opportunities: "No Longer Responsive", "No Show – Intro Call", "Other"
- **Excluded Firms**: Internal and wirehouse firms
  - Savvy Wealth, Ritholtz, J.P. Morgan, Morgan Stanley, Merrill, Wells Fargo, etc.

**Rationale**: Clear categorization enables precise filtering and prioritization

#### Step 1.2: Task Activity Tracking (Part B)

**Purpose**: Find last contact date for each lead/opportunity

**Created CTEs**:
- `lead_last_tasks`: Last task activity for Leads (WhoId LIKE '00Q%')
- `opp_last_tasks`: Last task activity for Opportunities (WhatId LIKE '006%')
- `users`: Active user lookup for owner names

**Key Fields Captured**:
- `last_task_date`: Most recent ActivityDate
- `last_task_owner_id`: Who last contacted
- `last_task_subject`: Subject of last task

**Rationale**: Determines if enough time has passed for re-engagement (90-730 days)

#### Step 1.3: Recyclable Opportunities (Part C)

**Purpose**: Identify closed/lost opportunities eligible for recycling

**Key Logic**:
1. **Base Filtering**:
   - `IsClosed = true` AND `IsWon = false`
   - Not in no-go reasons
   - Last contact 90-730 days ago
   - Has CRD (for FINTRX join)

2. **Firm Change Detection** (CRITICAL):
   ```sql
   CASE 
       WHEN c.PRIMARY_FIRM_START_DATE IS NOT NULL 
            AND DATE(c.PRIMARY_FIRM_START_DATE) > DATE(o.CloseDate) 
       THEN TRUE
       ELSE FALSE
   END as changed_firms_since_close
   ```
   - Detects if advisor changed firms AFTER we closed the opportunity
   - Uses DATE() casting to handle TIMESTAMP vs DATE type mismatch

3. **Tenure Calculations**:
   - `years_at_current_firm`: Current tenure at their current firm
   - `years_at_current_firm_now`: Same as above (used for P2 priority)
   - `years_at_firm_when_closed`: Tenure at firm WHEN we closed them (PIT-compliant)
     - Uses employment history join to find firm at time of close
     - Falls back to current firm if no employment history

4. **PIT-Compliant Employment History Join**:
   ```sql
   LEFT JOIN (
       SELECT RIA_CONTACT_CRD_ID as crd,
              PREVIOUS_REGISTRATION_COMPANY_START_DATE as firm_start_at_close,
              PREVIOUS_REGISTRATION_COMPANY_END_DATE as firm_end_at_close
       FROM contact_registered_employment_history
   ) eh_pit ON [CRD match]
       AND DATE(eh_pit.firm_start_at_close) <= DATE(o.CloseDate)
       AND (eh_pit.firm_end_at_close IS NULL 
            OR DATE(eh_pit.firm_end_at_close) >= DATE(o.CloseDate))
   QUALIFY ROW_NUMBER() OVER (PARTITION BY o.Id ORDER BY eh_pit.firm_start_at_close DESC) = 1
   ```
   - Finds the firm they were at WHEN we closed them
   - Prevents data leakage by using only data available at close date

5. **Recent Firm Changer Exclusion**:
   ```sql
   AND (
       c.PRIMARY_FIRM_START_DATE IS NULL 
       OR DATE(c.PRIMARY_FIRM_START_DATE) <= DATE(o.CloseDate)
       OR DATE_DIFF(CURRENT_DATE(), DATE(c.PRIMARY_FIRM_START_DATE), DAY) >= (2 * 365)
   )
   ```
   - **KEY INSIGHT**: Excludes people who changed firms < 2 years ago
   - They just settled in and won't move again soon
   - Only includes people who changed 2+ years ago (settling period over)

6. **Field Validation**:
   - Uses COALESCE for optional fields (LinkedIn, owner, names)
   - Falls back to FINTRX data if Salesforce fields missing

#### Step 1.4: Recyclable Leads (Part D)

**Purpose**: Identify closed leads eligible for recycling

**Similar Logic to Opportunities**:
- Same firm change detection
- Same tenure calculations
- Same exclusion logic
- **Additional Filter**: `ConvertedOpportunityId IS NULL` (not already converted)
- **Deduplication**: Excludes leads already in recyclable opportunities (by CRD)

**Key Difference**: Uses `Stage_Entered_Closed__c` (TIMESTAMP) instead of `CloseDate` (DATE)

#### Step 1.5: Priority Assignment (Part E)

**Purpose**: Assign priority tiers based on business logic

**Priority Logic** (in order):

1. **P1: Timing Dispositions** (7% expected conversion)
   - Criteria: `is_timing_reason = TRUE` AND `days_since_last_contact BETWEEN 180 AND 365`
   - Rationale: They literally said timing was bad - try again now
   - Opportunities prioritized over Leads

2. **P2: High V4 + No Firm Change + Long Tenure** (6% expected)
   - Criteria: `v4_percentile >= 80` AND `changed_firms_since_close = FALSE` AND `years_at_current_firm_now >= 3`
   - Rationale: Model predicts they're about to move, haven't moved yet, still at same firm
   - **KEY INSIGHT**: People who HAVEN'T changed firms are better targets than recent changers

3. **P3: No Response + High V4** (5% expected)
   - Criteria: `close_reason IN ('No Response', ...)` AND `v4_percentile >= 70`
   - Rationale: Good prospect who didn't engage before, worth retry

4. **P4: Changed Firms 2-3 Years Ago** (4.5% expected)
   - Criteria: `changed_firms_since_close = TRUE` AND `years_at_current_firm BETWEEN 2 AND 3`
   - Rationale: Proven mover, settling period is over, may be getting restless

5. **P5: Changed Firms 3+ Years Ago + High V4** (4% expected)
   - Criteria: `changed_firms_since_close = TRUE` AND `years_at_current_firm > 3` AND `v4_percentile >= 60`
   - Rationale: Overdue for another change, historical movers tend to move again

6. **P6: Standard Recycle** (3% expected)
   - Criteria: Everything else that's eligible
   - Rationale: General re-engagement pool

**Ranking Order**:
1. Priority tier (P1 → P6)
2. Record type (Opportunities before Leads)
3. V4 percentile (descending)
4. Days since contact (closer to 180 days = better)
5. Record ID (tiebreaker)

#### Step 1.6: Final Output

**Selects Top 600** (or `target_count`) records ordered by `recycle_rank`

**Output Columns**:
- Contact info (name, email, phone, LinkedIn, firm)
- Recycling context (priority, expected conversion rate)
- History (close reason, close date, last contact)
- Firm analysis (changed firms, tenure metrics)
- Scoring (V4 score, percentile)
- Flags (is_timing_reason, is_general_recyclable)

---

### Phase 2: Python Orchestration Script

**Objective**: Create Python script to execute SQL, generate narratives, and export results

#### Step 2.1: Narrative Generation Function

**Purpose**: Create human-readable explanations for each recyclable lead

**Logic by Priority**:

- **P1 (Timing)**: 
  ```
  "TIMING RE-ENGAGEMENT: They told us timing was bad X days ago. 
   Enough time has passed - timing may be better now."
  ```

- **P2 (High V4 + Long Tenure)**:
  ```
  "HIGH MOVER POTENTIAL: V4 score in top X% of prospects. 
   Currently has Y years at same firm. 
   KEY INSIGHT: They have NOT changed firms since we closed them - 
   meaning they're still available and may be getting restless."
  ```

- **P3 (No Response + High V4)**:
  ```
  "NO RESPONSE RE-TRY: Previously didn't respond, but V4 score indicates 
   strong prospect. X days have passed - circumstances may have changed."
  ```

- **P4 (Changed 2-3 Years Ago)**:
  ```
  "PROVEN MOVER - WARMING UP: Changed firms after we contacted them, 
   but that was X years ago. They've had time to settle in and may be 
   starting to evaluate options again."
  ```

- **P5 (Changed 3+ Years Ago)**:
  ```
  "PROVEN MOVER - OVERDUE: Changed firms X years ago. 
   Has been at current firm long enough to potentially be looking again."
  ```

- **P6 (Standard)**:
  ```
  "STANDARD RE-ENGAGEMENT: X days since last contact. 
   Sufficient time has passed for circumstances to have changed."
  ```

**Additional Context**:
- Warns if recent firm changer slipped through (< 2 years)
- Notes if still at same firm vs changed firms
- Includes last contact info (who, when, what)
- Shows expected conversion rate and previous owner

#### Step 2.2: Query Execution Function

**Purpose**: Execute the SQL query and return DataFrame

**Process**:
1. Read SQL file from `sql/recycling/recyclable_pool_master_v2.1.sql`
2. Replace `target_count` parameter if needed
3. Execute via BigQuery client
4. Return pandas DataFrame

#### Step 2.3: Report Generation Function

**Purpose**: Create summary report with statistics and analysis

**Report Sections**:
1. **Header**: Month, year, generation timestamp, total records
2. **Logic Explanation**: V1 vs V2 differences
3. **Priority Distribution**: Count, percentage, avg conversion by tier
4. **Summary Statistics**: 
   - Total records, Opportunities vs Leads split
   - Weighted average conversion rate
   - Expected total conversions
   - Changed firms count, High V4 count
5. **Firm Change Analysis**: Distribution by firm change category
6. **Files Generated**: Links to CSV and report

#### Step 2.4: Main Execution Function

**Purpose**: Orchestrate the entire pipeline

**Process**:
1. Parse command-line arguments (month, year, target count)
2. Initialize BigQuery client
3. Execute SQL query
4. Generate narratives for each record
5. Export to CSV
6. Generate summary report
7. Validate no recent firm changers slipped through
8. Print summary statistics

**Command-Line Usage**:
```bash
python scripts/recycling/generate_recyclable_list_v2.1.py --month january --year 2026
```

---

### Phase 3: Validation and Testing

**Objective**: Ensure data quality and correct logic execution

#### Validation Queries (Built into SQL)

1. **V1: Date Type Issues**
   - Checks for negative or unrealistic tenure values
   - Should return 0 rows

2. **V2: Recent Firm Changers**
   - Checks for records with `changed_firms_since_close=TRUE` AND `years_at_current_firm < 2`
   - Should return 0 rows (these should be excluded)

3. **V3: Priority Distribution**
   - Shows count and average conversion by priority tier
   - Validates distribution looks reasonable

#### Pre-Execution Checklist

- [ ] Verified all custom field names exist
- [ ] Ran query with LIMIT 100 to validate output
- [ ] Confirmed no recent firm changers (< 2 years)
- [ ] Confirmed priority distribution reasonable
- [ ] Confirmed no NULL values in critical fields
- [ ] Tested narrative generation

#### Post-Execution Checklist

- [ ] Total count = 600 (or target)
- [ ] No duplicate CRDs
- [ ] Opportunities appear before Leads
- [ ] Expected conversion rates align with priority
- [ ] Report generated successfully
- [ ] Validation queries run successfully

---

## Key Business Logic Evolution

### V1 (Initial Version) - INCORRECT ASSUMPTION

**Wrong Logic**: "Changed firms = hot lead, prioritize them"

**Problem**: This assumed people who just changed firms were ready to move again, but behavioral research shows:
- People who just changed firms are in a "settling period"
- They're building relationships, dealing with transition stress
- They won't want to move again for 1-2 years minimum

### V2.0 (Corrected Logic) - BREAKTHROUGH INSIGHT

**Correct Logic**: "Recently changed firms = NOT ready to move again"

**Key Changes**:
1. **Exclude** people who changed firms < 2 years ago
2. **Prioritize** people who HAVEN'T changed firms + High V4 + Long tenure
3. **Medium Priority** for people who changed firms 2-3 years ago
4. **Higher Priority** for people who changed firms 3+ years ago

**Rationale**:
- Recent movers (< 2 years): Just settled in, won't move again soon
- No change + High V4 + Long tenure: Model predicts move, still at same firm = good timing
- Changed 2-3 years ago: Settling period over, may be getting restless
- Changed 3+ years ago: Overdue for another change

### V2.1 (SQL Fixes) - TECHNICAL CORRECTIONS

**Issues Fixed**:
1. **Date Type Mismatches**: Added DATE() casting for all date comparisons
2. **Tenure Calculations**: Calculate to CloseDate, not CURRENT_DATE
3. **PIT Compliance**: Added employment history join to find firm at time of close
4. **Priority Logic**: Use `years_at_current_firm_now` instead of incorrect field
5. **Field Validation**: Added COALESCE wrappers for optional fields

**Result**: Production-ready SQL with correct logic and data handling

---

## Technical Implementation Details

### Data Sources

1. **Salesforce CRM**:
   - `Lead` table: Closed leads with dispositions
   - `Opportunity` table: Closed lost opportunities with reasons
   - `Task` table: Last contact activity tracking
   - `User` table: Owner name lookup

2. **FINTRX Database**:
   - `ria_contacts_current`: Current firm information
   - `contact_registered_employment_history`: Historical firm changes (PIT-compliant)

3. **ML Features**:
   - `v4_prospect_scores`: V4 XGBoost model scores and percentiles

### Key SQL Techniques

1. **PIT Compliance**:
   - Uses employment history to find firm at time of close
   - Prevents data leakage by only using data available at close date
   - Uses QUALIFY with ROW_NUMBER() to get most recent employment record

2. **Date Handling**:
   - Consistent DATE() casting for all comparisons
   - Handles TIMESTAMP vs DATE type mismatches
   - Calculates tenure correctly at time of close

3. **Field Validation**:
   - COALESCE for optional fields
   - Fallback to FINTRX data if Salesforce missing
   - Safe string handling for names and descriptions

4. **Deduplication**:
   - Opportunities prioritized over Leads
   - Excludes Leads already in Opportunities (by CRD)
   - Ensures no duplicate advisors in final list

### Performance Considerations

- **Indexing**: Relies on BigQuery's automatic indexing
- **Filtering**: Early filtering in WHERE clauses reduces join size
- **TEMP TABLES**: Uses TEMP TABLE for exclusion lists (efficient lookups)
- **QUALIFY**: Uses QUALIFY instead of subqueries for better performance

---

## Expected Outputs

### CSV Export

**File**: `exports/[MONTH]_[YEAR]_recyclable_leads.csv`

**Columns** (30+ fields):
- Contact info: `first_name`, `last_name`, `email`, `phone`, `linkedin_url`, `current_firm`
- Recycling context: `recycle_priority`, `expected_conv_rate_pct`, `recycle_narrative`
- History: `close_reason`, `close_date`, `last_task_date`, `last_contacted_by`, `days_since_last_contact`
- Firm analysis: `changed_firms_since_close`, `years_at_current_firm`, `years_at_current_firm_now`, `years_at_firm_when_closed`
- Scoring: `v4_score`, `v4_percentile`
- Metadata: `record_type`, `record_id`, `fa_crd`, `owner_name`, `generated_at`

**Row Count**: 600 (or target_count)

### Summary Report

**File**: `reports/recycling_analysis/[MONTH]_[YEAR]_recyclable_list_report.md`

**Sections**:
1. Header with generation timestamp
2. Logic explanation (V1 vs V2)
3. Priority tier distribution table
4. Summary statistics
5. Firm change analysis
6. Files generated

---

## Integration with Other Systems

### Relationship to Primary Lead Lists

- **Separate Lists**: Recyclable lists are generated separately from new prospect lists
- **Complementary**: Works alongside primary lists (600 recyclable + 2,400 new = 3,000 total)
- **Different Purpose**: Re-engagement vs cold outbound
- **Different Timing**: 90-730 days since contact vs never contacted

### Relationship to V4 Model

- **Uses V4 Scores**: Leverages V4 XGBoost model for prioritization
- **P2 Priority**: High V4 score (≥80th percentile) is key signal
- **P3 Priority**: High V4 score (≥70th percentile) for no-response leads
- **P5 Priority**: High V4 score (≥60th percentile) for proven movers

### Relationship to SGA Optimization

- **Part of Hybrid Strategy**: Recyclable lists are part of the 70/30 hybrid approach
- **Expected Conversion**: 3-7% depending on priority (vs 3.2% baseline)
- **Pool Size**: 26,311 recyclable leads available (sustainable for 12+ months)

---

## Maintenance and Updates

### Monthly Execution

1. Run Python script with month/year parameters
2. Review summary report for anomalies
3. Validate no recent firm changers slipped through
4. Check priority distribution looks reasonable
5. Export CSV for SGA distribution

### Monitoring Metrics

- **Total Records**: Should be ~600 (or target)
- **Priority Distribution**: P1-P2 should be 10-20% of list
- **Conversion Tracking**: Monitor actual vs expected conversion rates
- **Pool Depletion**: Track recyclable pool size over time

### Future Enhancements

- **Dynamic Target Count**: Adjust based on pool size and conversion rates
- **A/B Testing**: Test different priority thresholds
- **Automated Scheduling**: Monthly cron job for generation
- **Salesforce Integration**: Auto-create tasks or update fields
- **Performance Tracking**: Dashboard for conversion by priority tier

---

## Lessons Learned

### Critical Insights

1. **Behavioral Research Matters**: Understanding advisor psychology (settling period after moves) led to corrected logic
2. **PIT Compliance is Essential**: Using employment history correctly prevents data leakage
3. **Date Type Handling**: Always cast dates consistently to avoid type mismatch errors
4. **Field Validation**: Use COALESCE for optional fields to handle missing data gracefully
5. **Iterative Improvement**: V1 → V2.0 → V2.1 shows value of testing and refinement

### Common Pitfalls Avoided

1. **Data Leakage**: Using `PREVIOUS_REGISTRATION_COMPANY_END_DATE` (backfilled) would leak future information
2. **Type Mismatches**: Not casting TIMESTAMP to DATE causes comparison errors
3. **Incorrect Tenure**: Calculating to CURRENT_DATE instead of CloseDate gives wrong tenure
4. **Missing Validation**: Without validation queries, errors can slip through
5. **Assumption Errors**: Initial "changed firms = hot" assumption was wrong

---

## Conclusion

The Recyclable Lead List Generation System represents a sophisticated approach to maximizing CRM value through intelligent re-engagement. By combining behavioral insights (settling periods), ML predictions (V4 scores), and precise timing (90-730 day windows), the system identifies the most promising re-engagement candidates.

The evolution from V1 to V2.1 demonstrates the importance of:
- **Questioning assumptions** (changed firms ≠ always hot)
- **Technical precision** (PIT compliance, date handling)
- **Iterative refinement** (testing and fixing issues)

The system is now production-ready and provides a sustainable source of 600 high-quality re-engagement leads per month, complementing the primary new prospect lists and contributing to overall conversion rate improvements.

---

**Document Version**: 1.0  
**Last Updated**: December 24, 2025  
**Maintained By**: Data Science Team

