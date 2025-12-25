# Lead Recycling Optimization Analysis Guide

**Purpose**: Analyze CRM leads to determine optimal re-engagement timing and boost conversion rates to 5-6%  
**Working Directory**: `C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation`  
**Report Output**: `C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation\reports\SGA_Optimization_Version2.md`  
**Prerequisites**: Cursor.ai with MCP BigQuery access, Python environment  
**Status**: ✅ **READY FOR AGENTIC ANALYSIS** (Updated December 24, 2025)

## Important References

Before starting, review these documents:
- **`reports/recycling_infrastructure.md`**: Complete field reference for Lead/Opportunity/Task objects
  - How to identify closed leads (`Status = 'Closed'`, `Disposition__c`)
  - Do Not Call fields (`DoNotCall`, `HasOptedOutOfEmail`)
  - Last task date calculation (using `Task` object)
  - Close lost details (`Closed_Lost_Reason__c`, `Closed_Lost_Details__c`)

## Key Updates Made

1. **Fixed field names**: Changed `Advisor_CRD__c` → `FA_CRD__c` (correct field name)
2. **Fixed conversion detection**: Using `Stage_Entered_Call_Scheduled__c` (not `MQL_Date__c`)
3. **Fixed closed status**: Using `Status = 'Closed'` and `Disposition__c` (per recycling_infrastructure.md)
4. **PIT compliance**: Employment history queries now use `PREVIOUS_REGISTRATION_COMPANY_START_DATE` (not `END_DATE`) for timing
5. **Task date calculation**: Using `Task` object `ActivityDate` for last contact date
6. **Added filters**: `IsDeleted = false`, `DoNotCall = false` for recyclable leads

---

## Executive Summary: The Recycling Hypothesis

### Current Problem
- **New prospect pool**: 97,280 leads → 3.2% conversion rate → ~109 conversions/month
- **Target**: 5-6% conversion rate → 150-180 conversions/month
- **Gap**: Need +40-70 additional conversions/month

### The Recycling Opportunity
- **Hypothesis**: Leads we contacted but didn't close may have moved firms AFTER we contacted them
- **If true**: We can re-engage them at the optimal time (right before or after they move)
- **Data available**: FINTRX employment history shows when advisors changed firms
- **Expected outcome**: Recyclable leads at optimal timing should convert at 5-8% (vs 3.2% cold)

### Key Questions to Answer
1. How many closed/lost leads later moved firms?
2. What's the time gap between our contact and their firm change?
3. What's the optimal re-engagement window?
4. How many leads are currently in the "re-engagement window"?
5. What conversion rate can we expect from recycled leads?

---

## Phase 0: Setup and Prerequisites

### Cursor Prompt 0.1: Create Analysis Directory Structure

```
@workspace Create the analysis directory structure for lead recycling optimization.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create the following directory structure (if not exists):
   Lead_List_Generation/
   ├── reports/
   │   └── recycling_analysis/
   │       ├── data/           # Intermediate analysis data
   │       ├── figures/        # Charts and visualizations
   │       └── final/          # Final reports
   ├── scripts/
   │   └── recycling/          # Analysis scripts for this investigation
   └── sql/
       └── recycling/          # SQL queries for this investigation

2. Create a log file: reports/recycling_analysis/RECYCLING_ANALYSIS_LOG.md with header:
   ```markdown
   # Lead Recycling Optimization Analysis
   **Started**: [timestamp]
   **Objective**: Determine optimal re-engagement timing to boost conversion to 5-6%
   
   ## Key Hypothesis
   Leads we contacted but didn't close may have moved firms AFTER we contacted them.
   By re-engaging at the optimal time, we can significantly boost conversion rates.
   ```

3. Confirm structure created.
```

---

## Phase 1: Identify Closed/Lost Leads with Employment History

### Objective
Find all leads/opportunities we contacted but didn't close, and match them to FINTRX employment history to see if they later changed firms.

### Cursor Prompt 1.1: Extract Closed/Lost Leads with Firm Change Data

```
@workspace Query closed/lost leads and match to employment history to find firm changes.

MCP BIGQUERY ACCESS REQUIRED

Task:
1. Create sql/recycling/closed_lost_with_firm_changes.sql:

```sql
-- ============================================================================
-- CLOSED/LOST LEADS WITH SUBSEQUENT FIRM CHANGES
-- Identifies leads we contacted but didn't close, who later changed firms
-- ============================================================================

WITH 
-- Step 1: Get all leads we've contacted (Provided Lead List)
contacted_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd_clean,
        l.FirstName,
        l.LastName,
        l.Company as company_at_contact,
        l.LeadSource,
        l.Status,
        l.stage_entered_contacting__c as contacted_date,
        l.Stage_Entered_Call_Scheduled__c as call_scheduled_date,
        l.Stage_Entered_Closed__c as closed_date,
        l.Disposition__c,
        l.DoNotCall,
        l.CreatedDate,
        -- Determine outcome (using correct fields from recycling_infrastructure.md)
        CASE 
            WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 'CONVERTED_MQL'
            WHEN l.Status = 'Closed' THEN 'CLOSED_LOST'
            WHEN l.Status IN ('Contacting', 'New', 'Nurture', 'Qualified', 'Replied') THEN 'ACTIVE'
            ELSE 'OTHER'
        END as outcome,
        -- Days since contact
        DATE_DIFF(CURRENT_DATE(), DATE(l.stage_entered_contacting__c), DAY) as days_since_contact
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.LeadSource LIKE '%Provided Lead List%'
      AND l.stage_entered_contacting__c IS NOT NULL
      AND DATE(l.stage_entered_contacting__c) >= '2022-01-01'  -- 3 years of history
      AND l.IsDeleted = false
),

-- Step 2: Get employment history for these advisors (PIT-compliant)
-- Find NEXT firm change AFTER we contacted them
next_firm_changes AS (
    SELECT 
        cl.lead_id,
        cl.crd_clean,
        cl.contacted_date,
        cl.outcome,
        -- Find the NEXT firm they joined after contact date
        MIN(CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > cl.contacted_date 
            THEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE 
        END) as next_firm_start_date,
        -- Find the firm they left (if they left before joining new one)
        MIN(CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE > cl.contacted_date
                 AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
            THEN eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE 
        END) as next_firm_end_date,
        -- Get firm name from current snapshot
        c.PRIMARY_FIRM_NAME as current_firm_name,
        c.PRIMARY_FIRM_START_DATE as current_firm_start_date,
        -- Get previous firm name (at time of contact)
        eh_contact.PREVIOUS_REGISTRATION_COMPANY_NAME as firm_at_contact
    FROM contacted_leads cl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON cl.crd_clean = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > cl.contacted_date  -- Started AFTER contact
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c 
        ON cl.crd_clean = c.RIA_CONTACT_CRD_ID
    -- Get firm at time of contact (PIT-compliant)
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_contact
        ON cl.crd_clean = eh_contact.RIA_CONTACT_CRD_ID
        AND eh_contact.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= cl.contacted_date
        AND (eh_contact.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh_contact.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= cl.contacted_date)
    WHERE cl.crd_clean IS NOT NULL
    GROUP BY cl.lead_id, cl.crd_clean, cl.contacted_date, cl.outcome, 
             c.PRIMARY_FIRM_NAME, c.PRIMARY_FIRM_START_DATE, eh_contact.PREVIOUS_REGISTRATION_COMPANY_NAME
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY cl.lead_id 
        ORDER BY eh_contact.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
    ) = 1
),

-- Step 3: Find firm changes AFTER we contacted them
leads_with_firm_changes AS (
    SELECT 
        cl.*,
        nfc.firm_at_contact,
        nfc.current_firm_name,
        nfc.next_firm_start_date as joined_new_firm_date,
        nfc.next_firm_end_date as left_old_firm_date,
        nfc.current_firm_start_date,
        -- Calculate timing (days from contact to new firm start)
        DATE_DIFF(DATE(COALESCE(nfc.next_firm_start_date, nfc.current_firm_start_date)), 
                  DATE(cl.contacted_date), DAY) as days_contact_to_move,
        -- Flag if they moved AFTER we contacted them
        CASE 
            WHEN nfc.next_firm_start_date IS NOT NULL 
                 AND DATE(nfc.next_firm_start_date) > DATE(cl.contacted_date) THEN TRUE
            WHEN nfc.current_firm_start_date IS NOT NULL 
                 AND DATE(nfc.current_firm_start_date) > DATE(cl.contacted_date) THEN TRUE
            ELSE FALSE
        END as moved_after_contact,
        -- Flag if they changed firms (firm name different)
        CASE 
            WHEN nfc.current_firm_name IS NOT NULL 
                 AND nfc.firm_at_contact IS NOT NULL
                 AND UPPER(nfc.firm_at_contact) != UPPER(nfc.current_firm_name)
                 AND DATE(COALESCE(nfc.next_firm_start_date, nfc.current_firm_start_date)) > DATE(cl.contacted_date)
            THEN TRUE
            ELSE FALSE
        END as changed_firms_since_contact
    FROM contacted_leads cl
    LEFT JOIN next_firm_changes nfc 
        ON cl.lead_id = nfc.lead_id
)

-- Final output: All leads with firm change analysis
SELECT 
    lead_id,
    crd_clean as advisor_crd,
    FirstName,
    LastName,
    company_at_contact,
    outcome,
    contacted_date,
    days_since_contact,
    firm_at_contact,
    current_firm_name,
    left_old_firm_date,
    joined_new_firm_date,
    days_contact_to_move,
    changed_firms_since_contact,
    moved_after_contact,
    -- Categorize the timing
    CASE 
        WHEN NOT moved_after_contact THEN 'MOVED_BEFORE_CONTACT'
        WHEN days_contact_to_move IS NULL THEN 'NO_MOVE_DETECTED'
        WHEN days_contact_to_move <= 30 THEN 'MOVED_WITHIN_30_DAYS'
        WHEN days_contact_to_move <= 60 THEN 'MOVED_31-60_DAYS'
        WHEN days_contact_to_move <= 90 THEN 'MOVED_61-90_DAYS'
        WHEN days_contact_to_move <= 180 THEN 'MOVED_91-180_DAYS'
        WHEN days_contact_to_move <= 365 THEN 'MOVED_181-365_DAYS'
        ELSE 'MOVED_AFTER_1_YEAR'
    END as move_timing_category
FROM leads_with_firm_changes
WHERE moved_after_contact = TRUE  -- Focus on those who moved AFTER we contacted
  AND days_contact_to_move IS NOT NULL
ORDER BY days_contact_to_move ASC;
```

2. Execute via MCP BigQuery
3. Save results to: reports/recycling_analysis/data/closed_lost_with_firm_changes.csv
4. Log summary statistics to RECYCLING_ANALYSIS_LOG.md:
   - Total leads contacted
   - Total who moved after contact
   - Distribution by move_timing_category
   - Average days_contact_to_move
```

### Cursor Prompt 1.2: Analyze Conversion Outcomes by Move Timing

```
@workspace Analyze whether leads who moved firms after we contacted them had different outcomes.

MCP BIGQUERY ACCESS REQUIRED

Task:
1. Create sql/recycling/outcome_by_move_timing.sql:

```sql
-- ============================================================================
-- CONVERSION OUTCOMES BY MOVE TIMING
-- Did we convert more leads who were about to move?
-- ============================================================================

WITH 
contacted_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd_clean,
        l.stage_entered_contacting__c as contacted_date,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted,
        l.Status,
        l.Disposition__c
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.LeadSource LIKE '%Provided Lead List%'
      AND l.stage_entered_contacting__c IS NOT NULL
      AND DATE(l.stage_entered_contacting__c) >= '2022-01-01'
      AND l.IsDeleted = false
),

-- Get their next firm change after contact (PIT-compliant)
next_firm_change AS (
    SELECT 
        cl.lead_id,
        cl.crd_clean,
        cl.contacted_date,
        cl.converted,
        cl.Status,
        cl.Disposition__c,
        -- Find next firm start date AFTER contact (PIT-safe: use start_date)
        MIN(CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > cl.contacted_date 
            THEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE 
        END) as next_firm_join_date,
        -- Get current firm info
        c.PRIMARY_FIRM_NAME as current_firm_name,
        c.PRIMARY_FIRM_START_DATE as current_firm_start_date,
        -- Get firm at time of contact (PIT-compliant)
        eh_contact.PREVIOUS_REGISTRATION_COMPANY_NAME as firm_at_contact
    FROM contacted_leads cl
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh 
        ON cl.crd_clean = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > cl.contacted_date  -- Started AFTER contact
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c 
        ON cl.crd_clean = c.RIA_CONTACT_CRD_ID
    -- Get firm at time of contact (PIT-compliant)
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_contact
        ON cl.crd_clean = eh_contact.RIA_CONTACT_CRD_ID
        AND eh_contact.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= cl.contacted_date
        AND (eh_contact.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh_contact.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= cl.contacted_date)
    WHERE cl.crd_clean IS NOT NULL
    GROUP BY cl.lead_id, cl.crd_clean, cl.contacted_date, cl.converted, cl.Status, cl.Disposition__c,
             c.PRIMARY_FIRM_NAME, c.PRIMARY_FIRM_START_DATE, eh_contact.PREVIOUS_REGISTRATION_COMPANY_NAME
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY cl.lead_id 
        ORDER BY eh_contact.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
    ) = 1
),

-- Calculate timing and categorize
timing_analysis AS (
    SELECT 
        lead_id,
        crd_clean,
        contacted_date,
        converted,
        next_firm_leave_date,
        next_firm_join_date,
        DATE_DIFF(DATE(COALESCE(next_firm_join_date, next_firm_leave_date)), DATE(contacted_date), DAY) as days_to_move,
        CASE 
            WHEN next_firm_join_date IS NULL AND next_firm_leave_date IS NULL THEN 'NO_MOVE_DETECTED'
            WHEN DATE_DIFF(DATE(COALESCE(next_firm_join_date, next_firm_leave_date)), DATE(contacted_date), DAY) <= 0 THEN 'MOVED_BEFORE_OR_AT_CONTACT'
            WHEN DATE_DIFF(DATE(COALESCE(next_firm_join_date, next_firm_leave_date)), DATE(contacted_date), DAY) <= 30 THEN 'MOVED_0-30_DAYS'
            WHEN DATE_DIFF(DATE(COALESCE(next_firm_join_date, next_firm_leave_date)), DATE(contacted_date), DAY) <= 60 THEN 'MOVED_31-60_DAYS'
            WHEN DATE_DIFF(DATE(COALESCE(next_firm_join_date, next_firm_leave_date)), DATE(contacted_date), DAY) <= 90 THEN 'MOVED_61-90_DAYS'
            WHEN DATE_DIFF(DATE(COALESCE(next_firm_join_date, next_firm_leave_date)), DATE(contacted_date), DAY) <= 180 THEN 'MOVED_91-180_DAYS'
            WHEN DATE_DIFF(DATE(COALESCE(next_firm_join_date, next_firm_leave_date)), DATE(contacted_date), DAY) <= 365 THEN 'MOVED_181-365_DAYS'
            ELSE 'MOVED_AFTER_1_YEAR'
        END as move_timing_bucket
    FROM next_firm_change
)

-- Aggregate by timing bucket
SELECT 
    move_timing_bucket,
    COUNT(*) as leads,
    SUM(converted) as conversions,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / 0.0324, 2) as lift_vs_baseline,
    MIN(days_to_move) as min_days,
    MAX(days_to_move) as max_days,
    ROUND(AVG(days_to_move), 0) as avg_days
FROM timing_analysis
GROUP BY move_timing_bucket
ORDER BY 
    CASE move_timing_bucket
        WHEN 'NO_MOVE_DETECTED' THEN 0
        WHEN 'MOVED_BEFORE_OR_AT_CONTACT' THEN 1
        WHEN 'MOVED_0-30_DAYS' THEN 2
        WHEN 'MOVED_31-60_DAYS' THEN 3
        WHEN 'MOVED_61-90_DAYS' THEN 4
        WHEN 'MOVED_91-180_DAYS' THEN 5
        WHEN 'MOVED_181-365_DAYS' THEN 6
        ELSE 7
    END;
```

2. Execute via MCP BigQuery
3. Save to: reports/recycling_analysis/data/outcome_by_move_timing.csv
4. **KEY INSIGHT**: Look for timing buckets with highest conversion rates
   - If "MOVED_0-30_DAYS" has highest conversion → we should contact just before they move
   - If "MOVED_31-60_DAYS" has highest → re-engage 30 days after initial contact
```

---

## Phase 2: Determine Optimal Re-engagement Window

### Objective
Find the optimal time window to re-engage leads based on when they actually moved firms.

### Cursor Prompt 2.1: Analyze Optimal Re-engagement Timing

```
@workspace Create a detailed analysis of optimal re-engagement timing.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create scripts/recycling/optimal_reengagement_timing.py:

```python
"""
Optimal Re-engagement Timing Analysis
Determines the best time to re-engage leads based on when they actually moved firms.
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
from datetime import datetime
from google.cloud import bigquery
import matplotlib.pyplot as plt

# Configuration
PROJECT_ID = "savvy-gtm-analytics"
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation")
REPORTS_DIR = WORKING_DIR / "reports" / "recycling_analysis"
DATA_DIR = REPORTS_DIR / "data"
FIGURES_DIR = REPORTS_DIR / "figures"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def analyze_reengagement_timing(client):
    """Analyze the distribution of time between contact and firm move."""
    
    query = """
    WITH 
    contacted_leads AS (
        SELECT 
            l.Id as lead_id,
            SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd_clean,
            l.stage_entered_contacting__c as contacted_date,
            l.Status,
            l.Disposition__c,
            CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
        FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
        WHERE l.LeadSource LIKE '%Provided Lead List%'
          AND l.stage_entered_contacting__c IS NOT NULL
          AND DATE(l.stage_entered_contacting__c) >= '2022-01-01'
          AND l.IsDeleted = false
    ),
    
    -- Find advisors who changed firms (PIT-compliant: use start_date of NEXT firm)
    firm_changes AS (
        SELECT 
            cl.lead_id,
            cl.crd_clean,
            cl.contacted_date,
            cl.converted,
            cl.Status,
            cl.Disposition__c,
            -- Find next firm start date AFTER contact (PIT-safe)
            MIN(CASE 
                WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > cl.contacted_date 
                THEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE 
            END) as next_firm_start_date,
            -- Get current firm info
            c.PRIMARY_FIRM_NAME as current_firm_name,
            c.PRIMARY_FIRM_START_DATE as current_firm_start_date
        FROM contacted_leads cl
        LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh 
            ON cl.crd_clean = eh.RIA_CONTACT_CRD_ID
            AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > cl.contacted_date  -- Started AFTER contact
        LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c 
            ON cl.crd_clean = c.RIA_CONTACT_CRD_ID
        WHERE cl.crd_clean IS NOT NULL
        GROUP BY cl.lead_id, cl.crd_clean, cl.contacted_date, cl.converted, cl.Status, cl.Disposition__c,
                 c.PRIMARY_FIRM_NAME, c.PRIMARY_FIRM_START_DATE
    ),
    
    -- Join to find moves after contact
    leads_with_moves AS (
        SELECT 
            fc.lead_id,
            fc.crd_clean,
            fc.contacted_date,
            fc.converted,
            fc.Status,
            fc.Disposition__c,
            COALESCE(fc.next_firm_start_date, fc.current_firm_start_date) as move_date,
            DATE_DIFF(DATE(COALESCE(fc.next_firm_start_date, fc.current_firm_start_date)), 
                      DATE(fc.contacted_date), DAY) as days_contact_to_move
        FROM firm_changes fc
        WHERE (fc.next_firm_start_date IS NOT NULL 
               AND DATE(fc.next_firm_start_date) > DATE(fc.contacted_date))
           OR (fc.current_firm_start_date IS NOT NULL 
               AND DATE(fc.current_firm_start_date) > DATE(fc.contacted_date))
    )
    
    SELECT 
        lead_id,
        crd_clean,
        contacted_date,
        converted,
        Status,
        left_date as move_date,
        days_contact_to_move,
        -- 30-day buckets for granular analysis
        CAST(FLOOR(days_contact_to_move / 30) * 30 AS INT64) as days_bucket_30,
        -- 7-day buckets for fine-grained analysis
        CAST(FLOOR(days_contact_to_move / 7) * 7 AS INT64) as days_bucket_7
    FROM leads_with_moves
    WHERE days_contact_to_move > 0  -- Moved after contact
      AND days_contact_to_move <= 730  -- Within 2 years
    ORDER BY days_contact_to_move
    """
    
    print("[INFO] Querying leads with firm moves after contact...")
    df = client.query(query).to_dataframe()
    print(f"[INFO] Found {len(df):,} leads who moved after we contacted them")
    
    return df


def find_optimal_window(df):
    """Find the optimal re-engagement window based on conversion rates."""
    
    # Analyze by 30-day buckets
    bucket_analysis = df.groupby('days_bucket_30').agg({
        'lead_id': 'count',
        'converted': ['sum', 'mean']
    }).round(4)
    bucket_analysis.columns = ['leads', 'conversions', 'conversion_rate']
    bucket_analysis['lift_vs_baseline'] = bucket_analysis['conversion_rate'] / 0.0324
    
    # Find the window with highest conversion rate (minimum 50 leads)
    significant_buckets = bucket_analysis[bucket_analysis['leads'] >= 50]
    
    if len(significant_buckets) > 0:
        best_bucket = significant_buckets['conversion_rate'].idxmax()
        best_rate = significant_buckets.loc[best_bucket, 'conversion_rate']
        best_lift = significant_buckets.loc[best_bucket, 'lift_vs_baseline']
    else:
        best_bucket = None
        best_rate = None
        best_lift = None
    
    return bucket_analysis, best_bucket, best_rate, best_lift


def analyze_missed_opportunities(df):
    """Analyze leads who moved but we didn't convert - potential recycling targets."""
    
    # Leads who moved after contact but we didn't convert
    missed = df[df['converted'] == 0].copy()
    
    # Group by timing
    missed_by_timing = missed.groupby('days_bucket_30').agg({
        'lead_id': 'count'
    }).rename(columns={'lead_id': 'missed_leads'})
    
    # These are people we COULD have converted if we'd re-engaged at the right time
    print(f"\n[INSIGHT] Missed Opportunities:")
    print(f"  - Total leads who moved after contact: {len(df):,}")
    print(f"  - Leads we converted: {df['converted'].sum():,}")
    print(f"  - Leads we MISSED (moved but didn't convert): {len(missed):,}")
    print(f"  - Potential uplift if we re-engaged: ~{len(missed) * 0.05:.0f} additional conversions (at 5% rate)")
    
    return missed, missed_by_timing


def calculate_reengagement_cadence(df):
    """Determine optimal re-engagement cadence based on move timing distribution."""
    
    # Distribution of days between contact and move
    days_stats = {
        'mean': df['days_contact_to_move'].mean(),
        'median': df['days_contact_to_move'].median(),
        'std': df['days_contact_to_move'].std(),
        'p25': df['days_contact_to_move'].quantile(0.25),
        'p50': df['days_contact_to_move'].quantile(0.50),
        'p75': df['days_contact_to_move'].quantile(0.75),
        'p90': df['days_contact_to_move'].quantile(0.90)
    }
    
    print(f"\n[TIMING DISTRIBUTION]")
    print(f"  - Mean days to move: {days_stats['mean']:.0f}")
    print(f"  - Median days to move: {days_stats['median']:.0f}")
    print(f"  - 25th percentile: {days_stats['p25']:.0f} days")
    print(f"  - 75th percentile: {days_stats['p75']:.0f} days")
    print(f"  - 90th percentile: {days_stats['p90']:.0f} days")
    
    # Recommended re-engagement windows
    recommendations = {
        'first_reengagement': int(days_stats['p25']),  # 25th percentile
        'second_reengagement': int(days_stats['p50']),  # Median
        'third_reengagement': int(days_stats['p75']),  # 75th percentile
    }
    
    print(f"\n[RECOMMENDED RE-ENGAGEMENT CADENCE]")
    print(f"  - First re-engagement: {recommendations['first_reengagement']} days after initial contact")
    print(f"  - Second re-engagement: {recommendations['second_reengagement']} days after initial contact")
    print(f"  - Third re-engagement: {recommendations['third_reengagement']} days after initial contact")
    
    return days_stats, recommendations


def plot_timing_distribution(df, bucket_analysis):
    """Create visualization of timing distribution and conversion rates."""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Histogram of days to move
    ax1 = axes[0, 0]
    df['days_contact_to_move'].hist(bins=50, ax=ax1, color='steelblue', edgecolor='white')
    ax1.set_xlabel('Days from Contact to Firm Move')
    ax1.set_ylabel('Number of Leads')
    ax1.set_title('Distribution: When Leads Move After Contact')
    ax1.axvline(df['days_contact_to_move'].median(), color='red', linestyle='--', 
                label=f'Median: {df["days_contact_to_move"].median():.0f} days')
    ax1.legend()
    
    # Plot 2: Conversion rate by timing bucket
    ax2 = axes[0, 1]
    significant = bucket_analysis[bucket_analysis['leads'] >= 30]
    ax2.bar(significant.index, significant['conversion_rate'] * 100, color='green', alpha=0.7)
    ax2.axhline(3.24, color='red', linestyle='--', label='Baseline (3.24%)')
    ax2.set_xlabel('Days from Contact to Firm Move (30-day buckets)')
    ax2.set_ylabel('Conversion Rate (%)')
    ax2.set_title('Conversion Rate by Timing')
    ax2.legend()
    
    # Plot 3: Lead volume by timing bucket
    ax3 = axes[1, 0]
    ax3.bar(bucket_analysis.index, bucket_analysis['leads'], color='orange', alpha=0.7)
    ax3.set_xlabel('Days from Contact to Firm Move (30-day buckets)')
    ax3.set_ylabel('Number of Leads')
    ax3.set_title('Volume of Leads by Timing')
    
    # Plot 4: Lift vs baseline by timing
    ax4 = axes[1, 1]
    significant = bucket_analysis[bucket_analysis['leads'] >= 30]
    colors = ['green' if x > 1.0 else 'red' for x in significant['lift_vs_baseline']]
    ax4.bar(significant.index, significant['lift_vs_baseline'], color=colors, alpha=0.7)
    ax4.axhline(1.0, color='black', linestyle='-', label='Baseline (1.0x)')
    ax4.set_xlabel('Days from Contact to Firm Move (30-day buckets)')
    ax4.set_ylabel('Lift vs Baseline')
    ax4.set_title('Lift by Timing (Green = Above Baseline)')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / 'timing_distribution_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[INFO] Saved timing distribution chart to {FIGURES_DIR / 'timing_distribution_analysis.png'}")


def main():
    print("=" * 70)
    print("OPTIMAL RE-ENGAGEMENT TIMING ANALYSIS")
    print("=" * 70)
    
    client = bigquery.Client(project=PROJECT_ID)
    
    # Step 1: Get leads with firm moves
    df = analyze_reengagement_timing(client)
    
    # Step 2: Find optimal window
    bucket_analysis, best_bucket, best_rate, best_lift = find_optimal_window(df)
    
    print(f"\n[CONVERSION BY TIMING BUCKET]")
    print(bucket_analysis.to_string())
    
    if best_bucket is not None:
        print(f"\n[BEST TIMING BUCKET]: {best_bucket}-{best_bucket+30} days")
        print(f"  - Conversion rate: {best_rate*100:.2f}%")
        print(f"  - Lift vs baseline: {best_lift:.2f}x")
    
    # Step 3: Analyze missed opportunities
    missed, missed_by_timing = analyze_missed_opportunities(df)
    
    # Step 4: Calculate re-engagement cadence
    days_stats, recommendations = calculate_reengagement_cadence(df)
    
    # Step 5: Create visualizations
    plot_timing_distribution(df, bucket_analysis)
    
    # Save results
    df.to_csv(DATA_DIR / 'leads_with_firm_moves.csv', index=False)
    bucket_analysis.to_csv(DATA_DIR / 'conversion_by_timing_bucket.csv')
    missed.to_csv(DATA_DIR / 'missed_opportunities.csv', index=False)
    
    # Save recommendations
    results = {
        'total_leads_analyzed': len(df),
        'leads_converted': int(df['converted'].sum()),
        'missed_opportunities': len(missed),
        'best_timing_bucket': int(best_bucket) if best_bucket else None,
        'best_conversion_rate': float(best_rate) if best_rate else None,
        'best_lift': float(best_lift) if best_lift else None,
        'timing_stats': days_stats,
        'recommendations': recommendations
    }
    
    import json
    with open(DATA_DIR / 'reengagement_recommendations.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[INFO] Results saved to {DATA_DIR}")
    
    return df, bucket_analysis, recommendations


if __name__ == "__main__":
    main()
```

2. Run the script
3. Review the generated charts in figures/
4. Log key findings to RECYCLING_ANALYSIS_LOG.md
```

---

## Phase 3: Identify Current Recyclable Lead Pool

### Objective
Find all leads in CRM that are currently in the optimal re-engagement window.

### Cursor Prompt 3.1: Query Current Recyclable Leads

```
@workspace Identify all current leads that are in the optimal re-engagement window.

MCP BIGQUERY ACCESS REQUIRED

Task:
1. Create sql/recycling/current_recyclable_leads.sql:

```sql
-- ============================================================================
-- CURRENT RECYCLABLE LEADS
-- Finds leads currently in the optimal re-engagement window
-- 
-- PARAMETERS (adjust based on Phase 2 findings):
--   @min_days_since_contact: Minimum days since initial contact (e.g., 90)
--   @max_days_since_contact: Maximum days since initial contact (e.g., 365)
--   @exclude_recent_contact: Exclude if contacted within last N days (e.g., 60)
-- ============================================================================

DECLARE min_days_since_contact INT64 DEFAULT 90;
DECLARE max_days_since_contact INT64 DEFAULT 365;
DECLARE exclude_recent_contact INT64 DEFAULT 60;

WITH 
-- All leads we've contacted
all_contacted AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd_clean,
        l.FirstName,
        l.LastName,
        l.Email,
        l.Phone,
        l.Company as company_at_contact,
        l.Status,
        l.LeadSource,
        l.stage_entered_contacting__c as first_contacted_date,
        l.LastActivityDate as last_activity_date,
        -- Find most recent contact (use LastActivityDate from Task object if available)
        COALESCE(
            (SELECT MAX(t.ActivityDate) 
             FROM `savvy-gtm-analytics.SavvyGTMData.Task` t 
             WHERE t.WhoId = l.Id AND t.IsDeleted = false),
            l.stage_entered_contacting__c
        ) as last_contact_date,
        l.Stage_Entered_Call_Scheduled__c,
        -- Outcome
        CASE 
            WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 'CONVERTED'
            ELSE 'NOT_CONVERTED'
        END as outcome
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.LeadSource LIKE '%Provided Lead List%'
      AND l.stage_entered_contacting__c IS NOT NULL
),

-- Filter to recyclable candidates
recyclable_candidates AS (
    SELECT 
        ac.*,
        DATE_DIFF(CURRENT_DATE(), DATE(ac.first_contacted_date), DAY) as days_since_first_contact,
        DATE_DIFF(CURRENT_DATE(), DATE(ac.last_contact_date), DAY) as days_since_last_contact
    FROM all_contacted ac
    WHERE 
        -- Not converted
        ac.outcome = 'NOT_CONVERTED'
        -- In the time window
        AND DATE_DIFF(CURRENT_DATE(), DATE(ac.first_contacted_date), DAY) >= min_days_since_contact
        AND DATE_DIFF(CURRENT_DATE(), DATE(ac.first_contacted_date), DAY) <= max_days_since_contact
        -- Not recently contacted
        AND DATE_DIFF(CURRENT_DATE(), DATE(ac.last_contact_date), DAY) >= exclude_recent_contact
),

-- Enrich with current FINTRX data
enriched_recyclable AS (
    SELECT 
        rc.*,
        c.PRIMARY_FIRM_NAME as current_firm_name,
        c.PRIMARY_FIRM as current_firm_crd,
        c.PRIMARY_FIRM_START_DATE as current_firm_start_date,
        c.EMAIL as current_email,
        c.LINKEDIN_PROFILE_URL as linkedin_url,
        -- Check if they changed firms since we contacted them
        CASE 
            WHEN UPPER(rc.company_at_contact) != UPPER(c.PRIMARY_FIRM_NAME) 
                 AND c.PRIMARY_FIRM_START_DATE > rc.first_contacted_date
            THEN TRUE
            ELSE FALSE
        END as changed_firms_since_contact,
        -- Days at current firm
        DATE_DIFF(CURRENT_DATE(), DATE(c.PRIMARY_FIRM_START_DATE), DAY) as days_at_current_firm
    FROM recyclable_candidates rc
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c 
        ON rc.crd_clean = c.RIA_CONTACT_CRD_ID
),

-- Apply V4 scoring for prioritization
with_v4_scores AS (
    SELECT 
        er.*,
        vs.v4_score,
        vs.v4_percentile
    FROM enriched_recyclable er
    LEFT JOIN `savvy-gtm-analytics.ml_features.v4_prospect_scores` vs 
        ON er.crd_clean = vs.crd
)

SELECT 
    lead_id,
    crd_clean as advisor_crd,
    FirstName,
    LastName,
    Email,
    Phone,
    company_at_contact,
    current_firm_name,
    Status,
    first_contacted_date,
    last_contact_date,
    days_since_first_contact,
    days_since_last_contact,
    changed_firms_since_contact,
    days_at_current_firm,
    linkedin_url,
    v4_score,
    v4_percentile,
    -- Priority scoring
    CASE 
        -- Highest priority: Changed firms recently, high V4 score
        WHEN changed_firms_since_contact = TRUE AND v4_percentile >= 80 THEN 'P1_CHANGED_FIRM_HIGH_V4'
        WHEN changed_firms_since_contact = TRUE THEN 'P2_CHANGED_FIRM'
        WHEN v4_percentile >= 80 THEN 'P3_HIGH_V4_SCORE'
        WHEN days_since_first_contact BETWEEN 90 AND 180 THEN 'P4_OPTIMAL_WINDOW'
        ELSE 'P5_STANDARD_RECYCLE'
    END as recycle_priority,
    -- Expected conversion rate based on priority
    CASE 
        WHEN changed_firms_since_contact = TRUE AND v4_percentile >= 80 THEN 0.08
        WHEN changed_firms_since_contact = TRUE THEN 0.06
        WHEN v4_percentile >= 80 THEN 0.05
        WHEN days_since_first_contact BETWEEN 90 AND 180 THEN 0.04
        ELSE 0.03
    END as expected_conversion_rate
FROM with_v4_scores
WHERE crd_clean IS NOT NULL
ORDER BY 
    CASE recycle_priority
        WHEN 'P1_CHANGED_FIRM_HIGH_V4' THEN 1
        WHEN 'P2_CHANGED_FIRM' THEN 2
        WHEN 'P3_HIGH_V4_SCORE' THEN 3
        WHEN 'P4_OPTIMAL_WINDOW' THEN 4
        ELSE 5
    END,
    v4_percentile DESC;
```

2. Execute via MCP BigQuery
3. Save results to: reports/recycling_analysis/data/current_recyclable_leads.csv
4. Generate summary by recycle_priority
5. Calculate expected conversions if we re-engage these leads
```

### Cursor Prompt 3.2: Calculate Recyclable Pool Size and Expected Conversions

```
@workspace Calculate the recyclable pool size and expected conversion impact.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create scripts/recycling/recyclable_pool_analysis.py:

```python
"""
Recyclable Pool Analysis
Calculates pool size and expected conversion impact from recycling leads.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from google.cloud import bigquery
import json

PROJECT_ID = "savvy-gtm-analytics"
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation")
REPORTS_DIR = WORKING_DIR / "reports" / "recycling_analysis"
DATA_DIR = REPORTS_DIR / "data"

# Expected conversion rates by recycle priority (from Phase 2 findings)
EXPECTED_RATES = {
    'P1_CHANGED_FIRM_HIGH_V4': 0.08,  # Changed firms + high V4 → 8%
    'P2_CHANGED_FIRM': 0.06,           # Changed firms → 6%
    'P3_HIGH_V4_SCORE': 0.05,          # High V4 score → 5%
    'P4_OPTIMAL_WINDOW': 0.04,         # Optimal timing window → 4%
    'P5_STANDARD_RECYCLE': 0.03        # Standard recycle → 3%
}


def query_recyclable_pool(client):
    """Query the current recyclable lead pool."""
    
    query = """
    -- Recyclable leads summary by priority
    WITH recyclable AS (
        SELECT 
            l.Id as lead_id,
            COALESCE(CAST(l.Advisor_CRD__c AS INT64), 
                     CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64)) as crd_clean,
            l.stage_entered_contacting__c as first_contacted_date,
            GREATEST(
                COALESCE(l.stage_entered_contacting__c, '1900-01-01'),
                COALESCE(l.Last_SMS_Received__c, '1900-01-01'),
                COALESCE(l.Last_Call_Date__c, '1900-01-01')
            ) as last_contact_date,
            l.Status,
            l.Company as company_at_contact
        FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
        WHERE         l.LeadSource LIKE '%Provided Lead List%'
      AND l.stage_entered_contacting__c IS NOT NULL
      AND l.Stage_Entered_Call_Scheduled__c IS NULL  -- Not converted
      AND l.IsDeleted = false
      AND l.DoNotCall = false  -- Exclude do not call
      AND l.Status = 'Closed'  -- Only closed leads (per recycling_infrastructure.md)
    ),
    
    enriched AS (
        SELECT 
            r.*,
            DATE_DIFF(CURRENT_DATE(), DATE(r.first_contacted_date), DAY) as days_since_first_contact,
            DATE_DIFF(CURRENT_DATE(), DATE(r.last_contact_date), DAY) as days_since_last_contact,
            c.PRIMARY_FIRM_NAME as current_firm_name,
            c.PRIMARY_FIRM_START_DATE as current_firm_start_date,
            CASE 
                WHEN c.PRIMARY_FIRM_START_DATE IS NOT NULL
                     AND DATE(c.PRIMARY_FIRM_START_DATE) > DATE(r.first_contacted_date) 
                     AND UPPER(r.company_at_contact) != UPPER(c.PRIMARY_FIRM_NAME)
                THEN TRUE
                ELSE FALSE
            END as changed_firms,
            vs.v4_percentile
        FROM recyclable r
        LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c 
            ON r.crd_clean = c.RIA_CONTACT_CRD_ID
        LEFT JOIN `savvy-gtm-analytics.ml_features.v4_prospect_scores` vs 
            ON r.crd_clean = vs.crd
        WHERE DATE_DIFF(CURRENT_DATE(), DATE(r.last_contact_date), DAY) >= 60  -- Not contacted in 60 days
          AND r.crd_clean IS NOT NULL
    )
    
    SELECT 
        CASE 
            WHEN changed_firms = TRUE AND v4_percentile >= 80 THEN 'P1_CHANGED_FIRM_HIGH_V4'
            WHEN changed_firms = TRUE THEN 'P2_CHANGED_FIRM'
            WHEN v4_percentile >= 80 THEN 'P3_HIGH_V4_SCORE'
            WHEN days_since_first_contact BETWEEN 90 AND 180 THEN 'P4_OPTIMAL_WINDOW'
            ELSE 'P5_STANDARD_RECYCLE'
        END as recycle_priority,
        COUNT(*) as leads,
        ROUND(AVG(v4_percentile), 1) as avg_v4_percentile,
        ROUND(AVG(days_since_first_contact), 0) as avg_days_since_first_contact,
        SUM(CASE WHEN changed_firms THEN 1 ELSE 0 END) as changed_firms_count
    FROM enriched
    WHERE crd_clean IS NOT NULL
    GROUP BY 1
    ORDER BY 1
    """
    
    print("[INFO] Querying recyclable pool...")
    df = client.query(query).to_dataframe()
    return df


def calculate_expected_impact(df):
    """Calculate expected conversion impact from recycling."""
    
    # Add expected conversion rates
    df['expected_rate'] = df['recycle_priority'].map(EXPECTED_RATES)
    
    # Calculate expected conversions
    df['expected_conversions'] = df['leads'] * df['expected_rate']
    
    # Calculate total impact
    total_leads = df['leads'].sum()
    total_expected_conversions = df['expected_conversions'].sum()
    weighted_rate = total_expected_conversions / total_leads if total_leads > 0 else 0
    
    print(f"\n[RECYCLABLE POOL SUMMARY]")
    print("-" * 70)
    print(f"{'Priority':<30} {'Leads':>10} {'Exp Rate':>10} {'Exp Conv':>10}")
    print("-" * 70)
    for _, row in df.iterrows():
        print(f"{row['recycle_priority']:<30} {row['leads']:>10,} {row['expected_rate']*100:>9.1f}% {row['expected_conversions']:>10.1f}")
    print("-" * 70)
    print(f"{'TOTAL':<30} {total_leads:>10,} {weighted_rate*100:>9.1f}% {total_expected_conversions:>10.1f}")
    
    return {
        'total_recyclable_leads': int(total_leads),
        'total_expected_conversions': round(total_expected_conversions, 1),
        'weighted_conversion_rate': round(weighted_rate * 100, 2),
        'by_priority': df.to_dict('records')
    }


def recommend_monthly_allocation(impact):
    """Recommend monthly allocation of recyclable leads."""
    
    # Target: Include recyclable leads in monthly list to boost conversion
    # Current: 3,000 new leads/month at 3.2% → 96 conversions
    # Target: 5-6% conversion rate → 150-180 conversions
    
    print(f"\n[MONTHLY ALLOCATION RECOMMENDATION]")
    print("-" * 70)
    
    # Scenario 1: Replace 20% of new prospects with recyclable leads
    scenario1_recycle = 600  # 20% of 3,000
    scenario1_new = 2400
    scenario1_recycle_conv = scenario1_recycle * (impact['weighted_conversion_rate'] / 100)
    scenario1_new_conv = scenario1_new * 0.032
    scenario1_total_conv = scenario1_recycle_conv + scenario1_new_conv
    scenario1_rate = scenario1_total_conv / 3000
    
    print(f"\nScenario 1: 20% Recyclable (600) + 80% New (2,400)")
    print(f"  - Recyclable conversions: {scenario1_recycle_conv:.1f} (at {impact['weighted_conversion_rate']:.1f}%)")
    print(f"  - New prospect conversions: {scenario1_new_conv:.1f} (at 3.2%)")
    print(f"  - Total conversions: {scenario1_total_conv:.1f}")
    print(f"  - Blended rate: {scenario1_rate*100:.2f}%")
    
    # Scenario 2: Replace 30% of new prospects with recyclable leads
    scenario2_recycle = 900  # 30% of 3,000
    scenario2_new = 2100
    scenario2_recycle_conv = scenario2_recycle * (impact['weighted_conversion_rate'] / 100)
    scenario2_new_conv = scenario2_new * 0.032
    scenario2_total_conv = scenario2_recycle_conv + scenario2_new_conv
    scenario2_rate = scenario2_total_conv / 3000
    
    print(f"\nScenario 2: 30% Recyclable (900) + 70% New (2,100)")
    print(f"  - Recyclable conversions: {scenario2_recycle_conv:.1f} (at {impact['weighted_conversion_rate']:.1f}%)")
    print(f"  - New prospect conversions: {scenario2_new_conv:.1f} (at 3.2%)")
    print(f"  - Total conversions: {scenario2_total_conv:.1f}")
    print(f"  - Blended rate: {scenario2_rate*100:.2f}%")
    
    # Scenario 3: Focus on P1-P3 recyclable only (highest quality)
    p1_p3 = [p for p in impact['by_priority'] if p['recycle_priority'] in ['P1_CHANGED_FIRM_HIGH_V4', 'P2_CHANGED_FIRM', 'P3_HIGH_V4_SCORE']]
    p1_p3_leads = sum(p['leads'] for p in p1_p3)
    p1_p3_conv = sum(p['expected_conversions'] for p in p1_p3)
    p1_p3_rate = p1_p3_conv / p1_p3_leads if p1_p3_leads > 0 else 0
    
    print(f"\nScenario 3: P1-P3 Only (Highest Quality Recyclable)")
    print(f"  - Available P1-P3 leads: {p1_p3_leads:,}")
    print(f"  - Expected conversions: {p1_p3_conv:.1f}")
    print(f"  - Expected rate: {p1_p3_rate*100:.2f}%")
    print(f"  - Monthly sustainable (12 months): {p1_p3_leads // 12:,} leads/month")
    
    return {
        'scenario1': {'recycle': 600, 'new': 2400, 'total_conv': scenario1_total_conv, 'rate': scenario1_rate},
        'scenario2': {'recycle': 900, 'new': 2100, 'total_conv': scenario2_total_conv, 'rate': scenario2_rate},
        'p1_p3_only': {'leads': p1_p3_leads, 'conversions': p1_p3_conv, 'rate': p1_p3_rate}
    }


def main():
    print("=" * 70)
    print("RECYCLABLE POOL ANALYSIS")
    print("=" * 70)
    
    client = bigquery.Client(project=PROJECT_ID)
    
    # Query recyclable pool
    df = query_recyclable_pool(client)
    
    # Save raw data
    df.to_csv(DATA_DIR / 'recyclable_pool_by_priority.csv', index=False)
    
    # Calculate impact
    impact = calculate_expected_impact(df)
    
    # Generate recommendations
    scenarios = recommend_monthly_allocation(impact)
    
    # Save results
    results = {
        'impact': impact,
        'scenarios': scenarios
    }
    
    with open(DATA_DIR / 'recyclable_pool_impact.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[INFO] Results saved to {DATA_DIR}")
    
    return df, impact, scenarios


if __name__ == "__main__":
    main()
```

2. Run the script
3. Log findings to RECYCLING_ANALYSIS_LOG.md
```

---

## Phase 4: Build Hybrid New + Recyclable Lead List Strategy

### Objective
Create an optimized strategy that combines new prospects with recyclable leads to achieve 5-6% conversion.

### Cursor Prompt 4.1: Create Hybrid Lead List Optimization Model

```
@workspace Create an optimization model for hybrid new + recyclable lead lists.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create scripts/recycling/hybrid_list_optimizer.py:

```python
"""
Hybrid Lead List Optimizer
Optimizes the mix of new prospects and recyclable leads to maximize conversions.

TARGET: Achieve 5-6% conversion rate (150-180 conversions per 3,000 leads)
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
from pathlib import Path
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple

WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation")
REPORTS_DIR = WORKING_DIR / "reports" / "recycling_analysis"
DATA_DIR = REPORTS_DIR / "data"

# ============================================================================
# LEAD POOL CONFIGURATION
# Update these values from Phase 1-3 findings
# ============================================================================

@dataclass
class LeadPool:
    """Configuration for a lead pool."""
    name: str
    pool_size: int
    conversion_rate: float
    conversion_rate_ci_lower: float
    conversion_rate_ci_upper: float
    monthly_replenishment: float  # % of pool that replenishes monthly
    priority: int  # Lower = higher priority

# New Prospect Pools (from SGA Optimization V1)
NEW_PROSPECT_POOLS = {
    'TIER_1_PRIME_MOVER': LeadPool('TIER_1_PRIME_MOVER', 85, 0.0741, 0.045, 0.112, 0.02, 1),
    'TIER_2_PROVEN_MOVER': LeadPool('TIER_2_PROVEN_MOVER', 42735, 0.032, 0.028, 0.036, 0.02, 2),
    'V4_UPGRADE': LeadPool('V4_UPGRADE', 15000, 0.046, 0.034, 0.060, 0.02, 3),
    'STANDARD': LeadPool('STANDARD', 53108, 0.032, 0.028, 0.036, 0.02, 4),
}

# Recyclable Pools (from Phase 3 findings - UPDATE WITH ACTUAL VALUES)
RECYCLABLE_POOLS = {
    'P1_CHANGED_FIRM_HIGH_V4': LeadPool('P1_CHANGED_FIRM_HIGH_V4', 500, 0.08, 0.05, 0.12, 0.10, 1),
    'P2_CHANGED_FIRM': LeadPool('P2_CHANGED_FIRM', 2000, 0.06, 0.04, 0.08, 0.08, 2),
    'P3_HIGH_V4_SCORE': LeadPool('P3_HIGH_V4_SCORE', 5000, 0.05, 0.035, 0.065, 0.05, 3),
    'P4_OPTIMAL_WINDOW': LeadPool('P4_OPTIMAL_WINDOW', 10000, 0.04, 0.03, 0.05, 0.08, 4),
    'P5_STANDARD_RECYCLE': LeadPool('P5_STANDARD_RECYCLE', 20000, 0.03, 0.025, 0.035, 0.10, 5),
}

TOTAL_MONTHLY_LEADS = 3000
TARGET_CONVERSION_RATE = 0.05  # 5% target
MIN_CONVERSION_RATE = 0.045   # Minimum acceptable
SUSTAINABILITY_MONTHS = 12     # Plan for 12 months


def calculate_expected_conversions(allocations: Dict[str, int], pools: Dict[str, LeadPool]) -> float:
    """Calculate total expected conversions for a given allocation."""
    total = 0
    for pool_name, count in allocations.items():
        if pool_name in pools:
            total += count * pools[pool_name].conversion_rate
    return total


def calculate_sustainability(allocations: Dict[str, int], pools: Dict[str, LeadPool]) -> Dict[str, float]:
    """Calculate months until depletion for each pool."""
    sustainability = {}
    for pool_name, count in allocations.items():
        if pool_name in pools and count > 0:
            pool = pools[pool_name]
            # Account for monthly replenishment
            net_usage = count - (pool.pool_size * pool.monthly_replenishment)
            if net_usage > 0:
                sustainability[pool_name] = pool.pool_size / net_usage
            else:
                sustainability[pool_name] = float('inf')  # Pool replenishes faster than usage
        else:
            sustainability[pool_name] = float('inf')
    return sustainability


def optimize_hybrid_allocation(
    target_conversion_rate: float = TARGET_CONVERSION_RATE,
    total_leads: int = TOTAL_MONTHLY_LEADS,
    min_sustainability_months: int = SUSTAINABILITY_MONTHS,
    max_recyclable_pct: float = 0.40  # Max 40% recyclable
) -> Tuple[Dict[str, int], Dict[str, int], float]:
    """
    Optimize allocation between new prospects and recyclable leads.
    
    Returns:
        new_allocation: Dict of new prospect allocations
        recycle_allocation: Dict of recyclable allocations
        expected_rate: Expected conversion rate
    """
    
    all_pools = {**NEW_PROSPECT_POOLS, **RECYCLABLE_POOLS}
    pool_names = list(all_pools.keys())
    n_pools = len(pool_names)
    
    # Get pool parameters
    rates = np.array([all_pools[p].conversion_rate for p in pool_names])
    pools_sizes = np.array([all_pools[p].pool_size for p in pool_names])
    replenishment = np.array([all_pools[p].monthly_replenishment for p in pool_names])
    
    # Identify which are recyclable
    is_recyclable = np.array([p in RECYCLABLE_POOLS for p in pool_names])
    
    def objective(x):
        """Minimize negative expected conversion rate (maximize conversions)."""
        total_conv = np.sum(x * rates)
        return -total_conv  # Negative because we minimize
    
    def constraint_total_leads(x):
        """Total leads must equal target."""
        return np.sum(x) - total_leads
    
    def constraint_recyclable_limit(x):
        """Recyclable leads <= max_recyclable_pct of total."""
        recyclable_total = np.sum(x[is_recyclable])
        return max_recyclable_pct * total_leads - recyclable_total
    
    def constraint_sustainability(x):
        """Each pool must be sustainable for min_sustainability_months."""
        violations = []
        for i, pool_name in enumerate(pool_names):
            if x[i] > 0:
                pool = all_pools[pool_name]
                net_usage = x[i] - (pool.pool_size * pool.monthly_replenishment)
                if net_usage > 0:
                    months = pool.pool_size / net_usage
                    if months < min_sustainability_months:
                        violations.append(min_sustainability_months - months)
        return -sum(violations) if violations else 1
    
    # Bounds: 0 <= allocation <= pool_size / min_sustainability_months
    max_sustainable = pools_sizes / min_sustainability_months
    bounds = [(0, min(max_s, total_leads)) for max_s in max_sustainable]
    
    # Initial guess: proportional to pool size and conversion rate
    x0 = rates * pools_sizes
    x0 = x0 / x0.sum() * total_leads
    x0 = np.minimum(x0, max_sustainable)
    
    constraints = [
        {'type': 'eq', 'fun': constraint_total_leads},
        {'type': 'ineq', 'fun': constraint_recyclable_limit},
        {'type': 'ineq', 'fun': constraint_sustainability}
    ]
    
    result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
    
    # Extract allocations
    allocations = {pool_names[i]: int(round(result.x[i])) for i in range(n_pools)}
    
    # Adjust to exactly hit total_leads
    total = sum(allocations.values())
    if total != total_leads:
        # Add/remove from largest pool
        largest_pool = max(pool_names, key=lambda p: all_pools[p].pool_size)
        allocations[largest_pool] += total_leads - total
    
    # Split into new and recyclable
    new_allocation = {k: v for k, v in allocations.items() if k in NEW_PROSPECT_POOLS}
    recycle_allocation = {k: v for k, v in allocations.items() if k in RECYCLABLE_POOLS}
    
    # Calculate expected rate
    total_conversions = calculate_expected_conversions(allocations, all_pools)
    expected_rate = total_conversions / total_leads
    
    return new_allocation, recycle_allocation, expected_rate


def generate_scenarios() -> List[Dict]:
    """Generate multiple optimization scenarios for comparison."""
    
    scenarios = []
    
    for max_recycle in [0.20, 0.30, 0.40, 0.50]:
        for target_rate in [0.045, 0.050, 0.055, 0.060]:
            try:
                new_alloc, recycle_alloc, expected_rate = optimize_hybrid_allocation(
                    target_conversion_rate=target_rate,
                    max_recyclable_pct=max_recycle
                )
                
                new_total = sum(new_alloc.values())
                recycle_total = sum(recycle_alloc.values())
                
                new_conv = calculate_expected_conversions(new_alloc, NEW_PROSPECT_POOLS)
                recycle_conv = calculate_expected_conversions(recycle_alloc, RECYCLABLE_POOLS)
                
                scenarios.append({
                    'max_recyclable_pct': max_recycle,
                    'target_rate': target_rate,
                    'new_leads': new_total,
                    'recyclable_leads': recycle_total,
                    'new_conversions': round(new_conv, 1),
                    'recycle_conversions': round(recycle_conv, 1),
                    'total_conversions': round(new_conv + recycle_conv, 1),
                    'expected_rate': round(expected_rate * 100, 2),
                    'new_allocation': new_alloc,
                    'recycle_allocation': recycle_alloc
                })
            except Exception as e:
                print(f"[WARN] Scenario failed: max_recycle={max_recycle}, target={target_rate}: {e}")
    
    return scenarios


def main():
    print("=" * 70)
    print("HYBRID LEAD LIST OPTIMIZATION")
    print("=" * 70)
    print(f"Target: {TARGET_CONVERSION_RATE*100:.0f}% conversion rate")
    print(f"Total leads/month: {TOTAL_MONTHLY_LEADS:,}")
    print(f"Sustainability: {SUSTAINABILITY_MONTHS} months")
    
    # Generate scenarios
    scenarios = generate_scenarios()
    
    # Find best scenario
    viable_scenarios = [s for s in scenarios if s['expected_rate'] >= MIN_CONVERSION_RATE * 100]
    if viable_scenarios:
        best = max(viable_scenarios, key=lambda s: s['expected_rate'])
    else:
        best = max(scenarios, key=lambda s: s['expected_rate'])
    
    print(f"\n{'='*70}")
    print("SCENARIO COMPARISON")
    print("="*70)
    
    df = pd.DataFrame([{
        'Max Recycle %': s['max_recyclable_pct']*100,
        'New Leads': s['new_leads'],
        'Recycle Leads': s['recyclable_leads'],
        'New Conv': s['new_conversions'],
        'Recycle Conv': s['recycle_conversions'],
        'Total Conv': s['total_conversions'],
        'Rate %': s['expected_rate']
    } for s in scenarios])
    
    print(df.to_string(index=False))
    
    print(f"\n{'='*70}")
    print("RECOMMENDED ALLOCATION")
    print("="*70)
    print(f"Max Recyclable: {best['max_recyclable_pct']*100:.0f}%")
    print(f"Expected Conversion Rate: {best['expected_rate']:.2f}%")
    print(f"Expected Conversions: {best['total_conversions']:.0f}")
    
    print(f"\nNew Prospect Allocation ({best['new_leads']:,} leads):")
    for pool, count in sorted(best['new_allocation'].items(), key=lambda x: -x[1]):
        if count > 0:
            rate = NEW_PROSPECT_POOLS[pool].conversion_rate * 100
            print(f"  {pool}: {count:,} leads ({rate:.1f}% expected)")
    
    print(f"\nRecyclable Allocation ({best['recyclable_leads']:,} leads):")
    for pool, count in sorted(best['recycle_allocation'].items(), key=lambda x: -x[1]):
        if count > 0:
            rate = RECYCLABLE_POOLS[pool].conversion_rate * 100
            print(f"  {pool}: {count:,} leads ({rate:.1f}% expected)")
    
    # Save results
    results = {
        'scenarios': scenarios,
        'recommended': best,
        'target_rate': TARGET_CONVERSION_RATE,
        'total_leads': TOTAL_MONTHLY_LEADS
    }
    
    with open(DATA_DIR / 'hybrid_optimization_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    df.to_csv(DATA_DIR / 'hybrid_scenarios_comparison.csv', index=False)
    
    print(f"\n[INFO] Results saved to {DATA_DIR}")
    
    return scenarios, best


if __name__ == "__main__":
    main()
```

2. Run the script
3. Analyze which scenario achieves 5-6% conversion
4. Log findings to RECYCLING_ANALYSIS_LOG.md
```

---

## Phase 5: Generate Final Report

### Cursor Prompt 5.1: Generate SGA Optimization Version 2 Report

```
@workspace Generate the final SGA Optimization Version 2 report with recycling strategy.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create reports/SGA_Optimization_Version2.md with the following structure:

```markdown
# SGA Lead Distribution Optimization Report V2
## Incorporating Lead Recycling for 5-6% Conversion Rates

**Analysis Date**: [CURRENT_DATE]
**Prepared By**: Data Science Team
**Report Version**: 2.0

---

## Executive Summary

### The Challenge
- **V1 Finding**: New prospect pool achieves ~3.2% conversion rate (109 conversions/3,000 leads)
- **Target**: 5-6% conversion rate (150-180 conversions/3,000 leads)
- **Gap**: Need +40-70 additional conversions/month

### The Solution: Hybrid New + Recyclable Strategy
- **Key Insight**: Leads we contacted but didn't convert often moved firms AFTER we contacted them
- **Recycling Opportunity**: Re-engage these leads at optimal timing → 5-8% conversion expected
- **Recommended Mix**: [X]% new prospects + [X]% recyclable leads

### Key Findings

| Metric | V1 (New Only) | V2 (Hybrid) | Improvement |
|--------|---------------|-------------|-------------|
| Expected Conversion Rate | 3.2% | [X]% | +[X] pts |
| Expected Conversions/Month | 109 | [X] | +[X] |
| Leads Who Moved After Contact | N/A | [X] | New insight |
| Optimal Re-engagement Window | N/A | [X]-[X] days | New strategy |

---

## 1. Recycling Opportunity Analysis

### 1.1 Leads Who Moved After We Contacted Them
[INSERT FINDINGS FROM PHASE 1]

### 1.2 Conversion Rate by Move Timing
[INSERT FINDINGS FROM PHASE 2]
- Best timing window: [X]-[X] days after initial contact
- Conversion rate at optimal timing: [X]%
- Lift vs baseline: [X]x

---

## 2. Optimal Re-engagement Strategy

### 2.1 Re-engagement Cadence
Based on analysis of when leads actually moved firms:
- **First re-engagement**: [X] days after initial contact
- **Second re-engagement**: [X] days after initial contact
- **Third re-engagement**: [X] days after initial contact

### 2.2 Recyclable Lead Prioritization
[INSERT PRIORITY TIERS FROM PHASE 3]

---

## 3. Hybrid Lead List Strategy

### 3.1 Recommended Monthly Allocation
[INSERT OPTIMIZED ALLOCATION FROM PHASE 4]

### 3.2 Expected Performance
[INSERT CONVERSION PROJECTIONS]

---

## 4. Implementation Recommendations

### 4.1 Immediate Actions
1. Update lead list generation to include recyclable leads
2. Implement re-engagement cadence in Salesforce
3. Create recycling priority dashboards

### 4.2 SQL Updates Required
[INSERT SQL CHANGES]

### 4.3 Monitoring Plan
[INSERT MONITORING RECOMMENDATIONS]

---

## 5. Risk Mitigation

### 5.1 Pool Sustainability
[INSERT SUSTAINABILITY ANALYSIS]

### 5.2 Conversion Rate Validation
[INSERT VALIDATION PLAN]

---

## Appendix

### A. Methodology Notes
### B. Data Sources
### C. SQL Queries Used
```

2. Populate all sections with actual data from Phase 1-4
3. Include key charts from figures/
4. Save to: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation\reports\SGA_Optimization_Version2.md
5. Log completion to RECYCLING_ANALYSIS_LOG.md
```

---

## Phase 6: Create Implementation SQL

### Cursor Prompt 6.1: Create Hybrid Lead List SQL

```
@workspace Create the SQL for generating hybrid new + recyclable lead lists.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create sql/recycling/hybrid_lead_list_generator.sql:

```sql
-- ============================================================================
-- HYBRID LEAD LIST GENERATOR (V3.2.5 + V4 + RECYCLING)
-- Combines new prospects with optimally-timed recyclable leads
-- 
-- PARAMETERS:
--   total_leads: Total leads to generate (default: 3000)
--   recyclable_pct: Percentage of list from recycling (default: 30%)
--   min_days_for_recycle: Minimum days since last contact (default: 90)
--   max_days_for_recycle: Maximum days since last contact (default: 365)
-- ============================================================================

DECLARE total_leads INT64 DEFAULT 3000;
DECLARE recyclable_pct FLOAT64 DEFAULT 0.30;
DECLARE new_leads INT64;
DECLARE recycle_leads INT64;
DECLARE min_days_for_recycle INT64 DEFAULT 90;
DECLARE max_days_for_recycle INT64 DEFAULT 365;

SET new_leads = CAST(total_leads * (1 - recyclable_pct) AS INT64);
SET recycle_leads = total_leads - new_leads;

-- ============================================================================
-- PART A: NEW PROSPECTS (from existing V3.2.5 + V4 logic)
-- ============================================================================
WITH new_prospects AS (
    -- [INSERT EXISTING V3.2.5 + V4 LEAD LIST LOGIC HERE]
    -- Reference: Lead_List_Generation/January_2026_Lead_List_V3_V4_Hybrid.sql
    SELECT 
        advisor_crd,
        first_name,
        last_name,
        email,
        phone,
        linkedin_url,
        firm_name,
        score_tier,
        v4_score,
        v4_percentile,
        expected_conversion_rate,
        'NEW_PROSPECT' as lead_source,
        NULL as days_since_last_contact,
        NULL as recycle_priority
    FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list_v4`
    WHERE is_v4_upgrade = 0  -- Exclude V4 upgrades (they come from STANDARD pool)
    LIMIT new_leads
),

-- ============================================================================
-- PART B: RECYCLABLE LEADS
-- ============================================================================
recyclable_leads AS (
    SELECT 
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd,
        l.FirstName as first_name,
        l.LastName as last_name,
        COALESCE(c.EMAIL, l.Email) as email,
        l.Phone as phone,
        c.LINKEDIN_PROFILE_URL as linkedin_url,
        c.PRIMARY_FIRM_NAME as firm_name,
        l.stage_entered_contacting__c as first_contacted_date,
        COALESCE(
            (SELECT MAX(t.ActivityDate) 
             FROM `savvy-gtm-analytics.SavvyGTMData.Task` t 
             WHERE t.WhoId = l.Id AND t.IsDeleted = false),
            l.stage_entered_contacting__c
        ) as last_contact_date,
        DATE_DIFF(CURRENT_DATE(), DATE(l.stage_entered_contacting__c), DAY) as days_since_first_contact,
        DATE_DIFF(CURRENT_DATE(), DATE(
            GREATEST(
                COALESCE(l.stage_entered_contacting__c, '1900-01-01'),
                COALESCE(l.Last_SMS_Received__c, '1900-01-01'),
                COALESCE(l.Last_Call_Date__c, '1900-01-01')
            )
        ), DAY) as days_since_last_contact,
        -- Check if they changed firms
        CASE 
            WHEN c.PRIMARY_FIRM_START_DATE > l.stage_entered_contacting__c 
                 AND UPPER(l.Company) != UPPER(c.PRIMARY_FIRM_NAME)
            THEN TRUE
            ELSE FALSE
        END as changed_firms,
        vs.v4_score,
        vs.v4_percentile,
        -- Recycle priority
        CASE 
            WHEN c.PRIMARY_FIRM_START_DATE > l.stage_entered_contacting__c 
                 AND vs.v4_percentile >= 80 THEN 'P1_CHANGED_FIRM_HIGH_V4'
            WHEN c.PRIMARY_FIRM_START_DATE > l.stage_entered_contacting__c THEN 'P2_CHANGED_FIRM'
            WHEN vs.v4_percentile >= 80 THEN 'P3_HIGH_V4_SCORE'
            WHEN DATE_DIFF(CURRENT_DATE(), DATE(l.stage_entered_contacting__c), DAY) BETWEEN 90 AND 180 
                 THEN 'P4_OPTIMAL_WINDOW'
            ELSE 'P5_STANDARD_RECYCLE'
        END as recycle_priority,
        -- Expected conversion rate
        CASE 
            WHEN c.PRIMARY_FIRM_START_DATE > l.stage_entered_contacting__c 
                 AND vs.v4_percentile >= 80 THEN 0.08
            WHEN c.PRIMARY_FIRM_START_DATE > l.stage_entered_contacting__c THEN 0.06
            WHEN vs.v4_percentile >= 80 THEN 0.05
            WHEN DATE_DIFF(CURRENT_DATE(), DATE(l.stage_entered_contacting__c), DAY) BETWEEN 90 AND 180 THEN 0.04
            ELSE 0.03
        END as expected_conversion_rate,
        'RECYCLABLE' as lead_source
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c 
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = c.RIA_CONTACT_CRD_ID
    LEFT JOIN `savvy-gtm-analytics.ml_features.v4_prospect_scores` vs 
        ON SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = vs.crd
    WHERE l.LeadSource LIKE '%Provided Lead List%'
      AND l.stage_entered_contacting__c IS NOT NULL
      AND l.Stage_Entered_Call_Scheduled__c IS NULL  -- Not converted
      AND l.IsDeleted = false
      AND l.DoNotCall = false  -- Exclude do not call
      AND l.Status = 'Closed'  -- Only closed leads (per recycling_infrastructure.md)
      -- In re-engagement window
      AND DATE_DIFF(CURRENT_DATE(), DATE(COALESCE(
          (SELECT MAX(t.ActivityDate) 
           FROM `savvy-gtm-analytics.SavvyGTMData.Task` t 
           WHERE t.WhoId = l.Id AND t.IsDeleted = false),
          l.stage_entered_contacting__c
      )), DAY) >= min_days_for_recycle
      AND DATE_DIFF(CURRENT_DATE(), DATE(l.stage_entered_contacting__c), DAY) <= max_days_for_recycle
),

-- Rank recyclable leads by priority
ranked_recyclable AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            ORDER BY 
                CASE recycle_priority
                    WHEN 'P1_CHANGED_FIRM_HIGH_V4' THEN 1
                    WHEN 'P2_CHANGED_FIRM' THEN 2
                    WHEN 'P3_HIGH_V4_SCORE' THEN 3
                    WHEN 'P4_OPTIMAL_WINDOW' THEN 4
                    ELSE 5
                END,
                v4_percentile DESC,
                days_since_first_contact ASC
        ) as recycle_rank
    FROM recyclable_leads
),

-- Select top recyclable leads
selected_recyclable AS (
    SELECT 
        advisor_crd,
        first_name,
        last_name,
        email,
        phone,
        linkedin_url,
        firm_name,
        recycle_priority as score_tier,
        v4_score,
        v4_percentile,
        expected_conversion_rate,
        lead_source,
        days_since_last_contact,
        recycle_priority
    FROM ranked_recyclable
    WHERE recycle_rank <= recycle_leads
)

-- ============================================================================
-- FINAL OUTPUT: Combined hybrid list
-- ============================================================================
SELECT * FROM new_prospects
UNION ALL
SELECT * FROM selected_recyclable
ORDER BY 
    lead_source DESC,  -- New prospects first
    CASE score_tier
        WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1
        WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2
        WHEN 'TIER_1_PRIME_MOVER' THEN 3
        WHEN 'P1_CHANGED_FIRM_HIGH_V4' THEN 4
        WHEN 'P2_CHANGED_FIRM' THEN 5
        WHEN 'TIER_2_PROVEN_MOVER' THEN 6
        WHEN 'P3_HIGH_V4_SCORE' THEN 7
        ELSE 10
    END,
    v4_percentile DESC;
```

2. Document the expected output columns
3. Add validation queries
4. Log to RECYCLING_ANALYSIS_LOG.md
```

---

## Execution Checklist

```markdown
## Lead Recycling Optimization Analysis - Execution Checklist

**Started**: ___________
**Analyst**: ___________

### Phase 0: Setup
- [ ] Created directory structure
- [ ] Initialized RECYCLING_ANALYSIS_LOG.md

### Phase 1: Identify Closed/Lost with Firm Changes
- [ ] Queried leads with subsequent firm changes
- [ ] Saved closed_lost_with_firm_changes.csv
- [ ] Analyzed outcome by move timing
- [ ] Key finding: [X] leads moved after we contacted them

### Phase 2: Optimal Re-engagement Timing
- [ ] Ran timing analysis script
- [ ] Identified optimal window: [X]-[X] days
- [ ] Created timing distribution charts
- [ ] Key finding: [X]% conversion at optimal timing

### Phase 3: Current Recyclable Pool
- [ ] Queried current recyclable leads
- [ ] Calculated pool by priority tier
- [ ] Key finding: [X] recyclable leads available

### Phase 4: Hybrid Optimization
- [ ] Ran hybrid optimizer
- [ ] Compared scenarios
- [ ] Recommended mix: [X]% new + [X]% recyclable
- [ ] Expected rate: [X]%

### Phase 5: Final Report
- [ ] Generated SGA_Optimization_Version2.md
- [ ] All data populated
- [ ] Charts included

### Phase 6: Implementation SQL
- [ ] Created hybrid_lead_list_generator.sql
- [ ] Validated output

**Completed**: ___________
**Final Report**: reports/SGA_Optimization_Version2.md
```

---

## Quick Reference: Expected Metrics

| Metric | V1 (New Only) | V2 (Hybrid) Target |
|--------|---------------|-------------------|
| Monthly Leads | 3,000 | 3,000 |
| New Prospects | 3,000 (100%) | 2,100 (70%) |
| Recyclable | 0 | 900 (30%) |
| Expected Conv Rate | 3.2% | 5.0-6.0% |
| Expected Conversions | 96-109 | 150-180 |
| Per-SGA Conversions | 6-7 | 10-12 |

---

**Document Version**: 1.0  
**Created**: December 24, 2025  
**Purpose**: Cursor.ai agentic analysis guide for lead recycling optimization
