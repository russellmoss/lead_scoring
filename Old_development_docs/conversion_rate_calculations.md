# Conversion Rate Calculation Guide for Milea Estate Vineyard Analytics

## Executive Summary

This document outlines our standardized approach to calculating conversion rates across the sales funnel analytics system. The methodology ensures accurate, consistent metrics that reflect actual business performance rather than artificially depressed rates from improper calculations.

---

## Core Mathematical Principle

### The Fundamental Formula

```
Conversion Rate = Successful Outcomes / Evaluated Opportunities
```

**NOT:**
```
Conversion Rate = Successful Outcomes / All Records
```

This distinction is **critical** - we only count records where a decision has been made, not those awaiting evaluation.

---

## The Three-State Logic Problem

### Understanding the Challenge

The most complex calculation in our funnel involves three possible states:

1. **Yes** - Qualified/Converted (value: 1)
2. **No** - Not qualified/Not converted (value: 0)  
3. **NULL** - Not yet evaluated (no value assigned)

### Real-World Impact Example

Consider 100 SQL opportunities:
- 40 evaluated as "yes" (became SQO)
- 20 evaluated as "no" (didn't qualify)
- 40 not yet evaluated (NULL)

**Incorrect calculation (including NULL as 0):**
- Rate: 40/100 = **40%**

**Correct calculation (excluding NULL):**
- Rate: 40/60 = **67%**

This represents a **27 percentage point error** - the difference between thinking you have a problem versus celebrating strong performance.

---

## Funnel Stage Definitions & Calculations

### Stage Progression Map

| Stage | Description | ID Field | Date Field | Calculation Notes |
|-------|------------|----------|------------|-------------------|
| **Contacted** | Initial outreach made | `Full_prospect_id__c` | `stage_entered_contacting__c` | Entry point for prospects |
| **MQL** | Call scheduled | `Full_prospect_id__c` | `mql_stage_entered_ts` | Marketing qualified lead |
| **SQL** | Lead → Opportunity | `Full_prospect_id__c` | `converted_date_raw` | Sales qualified lead |
| **SQO** | Opportunity qualified | `Full_Opportunity_ID__c` | `Date_Became_SQO__c` | **⚠️ ID switch + 3-state logic** |
| **Joined** | Advisor signed | `Full_Opportunity_ID__c` | `advisor_join_date__c` | Revenue recognition point |

---

## SQL Implementation Patterns

### Binary Flag Creation (For Simple States)

```sql
-- Standard pattern for binary outcomes
CASE 
  WHEN stage_entered_contacting__c IS NOT NULL THEN 1 
  ELSE 0 
END AS is_contacted
```

### Three-State Logic (For SQO)

```sql
-- CORRECT: Preserves evaluation state
CASE 
  WHEN LOWER(SQO_raw) = 'yes' THEN 1    -- Qualified
  WHEN LOWER(SQO_raw) = 'no' THEN 0     -- Not qualified
  ELSE NULL                              -- Not yet evaluated
END AS is_sqo
```

### Conversion Rate Calculations

#### Standard Binary Conversion (MQL → SQL)
```sql
SAFE_DIVIDE(
  COUNT(DISTINCT IF(is_sql = 1, Full_prospect_id__c, NULL)),
  COUNT(DISTINCT IF(is_mql = 1, Full_prospect_id__c, NULL))
) AS mql_to_sql_rate
```

#### Three-State Conversion (SQL → SQO)
```sql
SAFE_DIVIDE(
  COUNT(DISTINCT CASE WHEN is_sqo = 1 THEN Full_Opportunity_ID__c END),
  COUNT(DISTINCT CASE WHEN is_sqo IN (0,1) THEN Full_Opportunity_ID__c END)
) AS sql_to_sqo_rate
```

**Critical elements:**
- Switch from `Full_prospect_id__c` to `Full_Opportunity_ID__c`
- Denominator explicitly excludes NULL values
- Uses CASE for complex conditional logic

---

## The Cascade Model for Predictions

### Sequential Multiplication Pattern

When forecasting future conversions, we use a waterfall approach:

```sql
-- Each stage feeds the next
Future_MQLs = Open_Prospects × Prospect_to_MQL_Rate
Future_SQLs = (Open_MQLs + Future_MQLs) × MQL_to_SQL_Rate
Future_SQOs = (Open_SQLs + Future_SQLs) × SQL_to_SQO_Rate
Future_Joined = (Open_SQOs + Future_SQOs) × SQO_to_Joined_Rate
```

This creates a Markov chain where each state's future population depends on all previous states.

---

## Common Implementation Mistakes

### ❌ Mistake 1: Treating NULL as Zero
```sql
-- WRONG: Artificially lowers rates
CASE WHEN LOWER(SQO_raw) = 'yes' THEN 1 ELSE 0 END
```

### ❌ Mistake 2: Using Wrong ID Fields
```sql
-- WRONG: SQOs are opportunities, not leads
COUNT(DISTINCT IF(is_sqo = 1, Full_prospect_id__c, NULL))
```

### ❌ Mistake 3: Including All Records
```sql
-- WRONG: Includes unevaluated records
SUM(is_sqo) / COUNT(*)
```

### ❌ Mistake 4: Missing DISTINCT
```sql
-- WRONG: Can double-count duplicates
COUNT(IF(is_mql = 1, Full_prospect_id__c, NULL))
```

---

## Diagnostic Query Template

Use this to validate your conversion rate calculations:

```sql
WITH diagnostic AS (
  SELECT
    COUNT(DISTINCT CASE WHEN is_sqo = 1 THEN Full_Opportunity_ID__c END) as qualified,
    COUNT(DISTINCT CASE WHEN is_sqo = 0 THEN Full_Opportunity_ID__c END) as not_qualified,
    COUNT(DISTINCT CASE WHEN is_sqo IS NULL THEN Full_Opportunity_ID__c END) as pending
  FROM your_view
  WHERE is_sql = 1
)
SELECT
  qualified,
  not_qualified,
  pending,
  ROUND(SAFE_DIVIDE(qualified, qualified + not_qualified) * 100, 1) as correct_rate,
  ROUND(SAFE_DIVIDE(qualified, qualified + not_qualified + pending) * 100, 1) as wrong_rate,
  ROUND(SAFE_DIVIDE(qualified, qualified + not_qualified) * 100, 1) - 
  ROUND(SAFE_DIVIDE(qualified, qualified + not_qualified + pending) * 100, 1) as error_pct
FROM diagnostic;
```

---

## Statistical Confidence & Volatility

### Standard Error for Conversion Rates

```
Standard Error = √(p × (1-p) / n)
```

Where:
- p = conversion rate
- n = sample size

### Confidence Intervals

```
95% CI = Rate ± (1.96 × Standard Error)
```

### Time-Based Uncertainty Growth

For future projections, uncertainty compounds:

```sql
Uncertainty = Base_Volatility × SQRT(Days_Into_Future)
```

This follows random walk theory where variance grows linearly with time.

---

## Implementation Checklist

Before deploying any conversion rate calculation:

- [ ] **Three-state logic** implemented for SQO calculations
- [ ] **DISTINCT** used in all COUNT operations
- [ ] **Correct ID fields** for each funnel stage
- [ ] **SAFE_DIVIDE** for all division operations
- [ ] **NULL handling** explicit in denominators
- [ ] **FilterDate** logic for cohort consistency
- [ ] **Diagnostic query** confirms no rate depression
- [ ] **Documentation** updated with calculation method

---

## Key Takeaways

1. **Conversion rates must reflect actual decisions**, not include pending evaluations
2. **Three-state logic is critical** for SQO calculations to avoid 20-30% errors
3. **ID fields switch** from prospect to opportunity at the SQL stage
4. **Cascade models** multiply rates sequentially through the funnel
5. **Testing is essential** - always validate with diagnostic queries

---

## Quick Reference

### For Daily Operations
```sql
-- Template for any conversion rate
Numerator:   COUNT(DISTINCT CASE WHEN [next_stage] = 1 THEN [id_field] END)
Denominator: COUNT(DISTINCT CASE WHEN [current_stage] = 1 THEN [id_field] END)
Rate:        SAFE_DIVIDE(Numerator, Denominator)
```

### For SQO Special Handling
```sql
-- Remember: Denominator excludes NULL
Numerator:   COUNT(DISTINCT CASE WHEN is_sqo = 1 THEN Full_Opportunity_ID__c END)
Denominator: COUNT(DISTINCT CASE WHEN is_sqo IN (0,1) THEN Full_Opportunity_ID__c END)
```

---

*Remember: A properly calculated 77% conversion rate that appears as 57% due to calculation errors isn't just a math problem - it's a business intelligence failure that leads to incorrect strategic decisions.*