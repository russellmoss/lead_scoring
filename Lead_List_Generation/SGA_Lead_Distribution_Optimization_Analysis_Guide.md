# SGA Lead Distribution Optimization Analysis Guide

**Purpose**: Statistical analysis to optimize lead distribution across 15 SGAs (200 leads/SGA/month = 3,000 leads/month)  
**Working Directory**: `C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation`  
**Report Output**: `C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation\reports\`  
**Prerequisites**: Cursor.ai with MCP BigQuery access, Python environment  

---

## Executive Summary: What We're Solving

| Challenge | Question | Analysis Required |
|-----------|----------|-------------------|
| **Quality vs. Sustainability** | How do we maximize conversions without depleting best leads too fast? | Pool depletion modeling |
| **Fair Distribution** | Should each SGA get same tier mix, or specialize? | Stratification analysis |
| **Conversion Forecasting** | What conversions can we expect per list per month? | Historical validation + confidence intervals |
| **Optimal Tier Quotas** | What's the ideal tier mix for 3,000 leads/month? | Constraint optimization |

---

## Phase 0: Setup and Prerequisites

### Cursor Prompt 0.1: Create Analysis Directory Structure

```
@workspace Create the analysis directory structure for SGA lead distribution optimization.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create the following directory structure:
   Lead_List_Generation/
   ├── reports/
   │   └── sga_optimization/
   │       ├── data/           # Intermediate analysis data
   │       ├── figures/        # Charts and visualizations
   │       └── final/          # Final reports
   ├── scripts/
   │   └── optimization/       # Analysis scripts for this investigation
   └── sql/
       └── optimization/       # SQL queries for this investigation

2. Create a log file: reports/sga_optimization/ANALYSIS_LOG.md with header:
   # SGA Lead Distribution Optimization Analysis
   **Started**: [timestamp]
   **Objective**: Optimize 3,000 leads/month across 15 SGAs (200 each)
   
3. Confirm structure created.
```

---

## Phase 1: Prospect Pool Inventory Analysis

### Objective
Understand the total available prospect pool, tier distribution, and monthly depletion rates.

### Cursor Prompt 1.1: Calculate Total Prospect Pool by Tier

```
@workspace Query the total prospect pool available for lead list generation.

MCP BIGQUERY ACCESS REQUIRED

Task:
1. Run the following SQL via MCP BigQuery connection:

```sql
-- ============================================================================
-- PROSPECT POOL INVENTORY BY TIER (V3.2.5 Logic)
-- Shows total available prospects and tier distribution
-- ============================================================================

WITH 
-- Exclusions (wirehouses, insurance, internal firms)
excluded_firms AS (
    SELECT firm_pattern FROM UNNEST([
        '%J.P. MORGAN%', '%MORGAN STANLEY%', '%MERRILL%', '%WELLS FARGO%', 
        '%UBS %', '%EDWARD JONES%', '%AMERIPRISE%', '%NORTHWESTERN MUTUAL%',
        '%PRUDENTIAL%', '%RAYMOND JAMES%', '%FIDELITY%', '%SCHWAB%', 
        '%VANGUARD%', '%GOLDMAN SACHS%', '%LPL FINANCIAL%', '%COMMONWEALTH%',
        '%CETERA%', '%PRIMERICA%', '%STATE FARM%', '%ALLSTATE%', 
        '%NEW YORK LIFE%', '%TRANSAMERICA%', '%INSURANCE%'
    ]) as firm_pattern
),

-- All producing advisors from FINTRX
all_prospects AS (
    SELECT 
        c.RIA_CONTACT_CRD_ID as crd,
        c.PRIMARY_FIRM as firm_crd,
        c.PRIMARY_FIRM_NAME as firm_name,
        c.PRIMARY_FIRM_START_DATE as firm_start_date,
        c.LINKEDIN_PROFILE_URL,
        DATE_DIFF(CURRENT_DATE(), c.PRIMARY_FIRM_START_DATE, MONTH) as tenure_months,
        COALESCE(f.PERIOD_END_REP_CNT, 0) as firm_rep_count,
        COALESCE(f.NET_CHANGE_12MO, 0) as firm_net_change_12mo
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f 
        ON c.PRIMARY_FIRM = f.RIA_FIRM_CRD_ID
    WHERE c.RIA_CONTACT_CRD_ID IS NOT NULL
      AND c.PRODUCING_ADVISOR = TRUE
      -- Exclude wirehouses/insurance
      AND NOT EXISTS (
          SELECT 1 FROM excluded_firms ef 
          WHERE UPPER(c.PRIMARY_FIRM_NAME) LIKE ef.firm_pattern
      )
      -- Exclude internal firms
      AND c.PRIMARY_FIRM NOT IN (318493, 168652)  -- Savvy Wealth, Ritholtz
),

-- Prospects NOT already in Salesforce (new prospects)
new_prospects AS (
    SELECT ap.*
    FROM all_prospects ap
    LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l 
        ON CAST(ap.crd AS STRING) = l.Advisor_CRD__c
    WHERE l.Id IS NULL
),

-- Apply V3.2.5 tier logic (simplified for counting)
tiered_prospects AS (
    SELECT 
        np.*,
        CASE 
            -- Tier 1A: CFP at bleeding firm (would need bio data - estimate)
            WHEN tenure_months BETWEEN 12 AND 48 
                 AND firm_rep_count <= 50 
                 AND firm_net_change_12mo < -3
            THEN 'TIER_1_PRIME_MOVER'
            
            -- Tier 2: Career movers (would need employment history - estimate based on tenure)
            WHEN tenure_months BETWEEN 24 AND 120
            THEN 'TIER_2_PROVEN_MOVER'
            
            -- Tier 3: Moderate bleeders
            WHEN firm_net_change_12mo BETWEEN -10 AND -1
            THEN 'TIER_3_MODERATE_BLEEDER'
            
            -- Tier 5: Heavy bleeders
            WHEN firm_net_change_12mo < -10
            THEN 'TIER_5_HEAVY_BLEEDER'
            
            ELSE 'STANDARD'
        END as estimated_tier
    FROM new_prospects np
)

SELECT 
    estimated_tier,
    COUNT(*) as prospect_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct_of_total,
    COUNT(CASE WHEN LINKEDIN_PROFILE_URL IS NOT NULL THEN 1 END) as with_linkedin,
    ROUND(COUNT(CASE WHEN LINKEDIN_PROFILE_URL IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as linkedin_pct
FROM tiered_prospects
GROUP BY estimated_tier
ORDER BY 
    CASE estimated_tier
        WHEN 'TIER_1_PRIME_MOVER' THEN 1
        WHEN 'TIER_2_PROVEN_MOVER' THEN 2
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 3
        WHEN 'TIER_5_HEAVY_BLEEDER' THEN 4
        ELSE 99
    END;
```

2. Save results to: reports/sga_optimization/data/prospect_pool_inventory.csv
3. Log to ANALYSIS_LOG.md with timestamp and key findings
4. Calculate: At 3,000 leads/month, how many months until each tier is depleted?
```

### Cursor Prompt 1.2: Calculate Monthly Depletion Rate

```
@workspace Calculate prospect pool depletion rates based on current generation patterns.

MCP BIGQUERY ACCESS REQUIRED

Task:
1. Run SQL to analyze how many leads we've pulled from each tier historically:

```sql
-- ============================================================================
-- HISTORICAL LEAD GENERATION BY TIER (Last 6 Months)
-- Shows how fast we're depleting each tier
-- ============================================================================

WITH monthly_generation AS (
    SELECT 
        FORMAT_DATE('%Y-%m', DATE(generated_at)) as month,
        score_tier,
        COUNT(*) as leads_generated
    FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list_v4`
    -- Add UNION ALL for other monthly tables if they exist
    GROUP BY 1, 2
)

SELECT 
    score_tier,
    SUM(leads_generated) as total_generated,
    COUNT(DISTINCT month) as months_active,
    ROUND(SUM(leads_generated) / COUNT(DISTINCT month), 0) as avg_monthly_generation
FROM monthly_generation
GROUP BY score_tier
ORDER BY avg_monthly_generation DESC;
```

2. If historical data limited, use the January 2026 list as baseline:

```sql
-- January 2026 tier distribution (actual)
SELECT 
    score_tier,
    COUNT(*) as leads,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct
FROM `savvy-gtm-analytics.ml_features.january_2026_lead_list_v4`
GROUP BY score_tier
ORDER BY leads DESC;
```

3. Calculate sustainability metrics:
   - Months_Until_Depleted = Pool_Size / Monthly_Usage
   - Sustainable_Monthly_Rate = Pool_Size / 12 (for 1-year horizon)
   
4. Save to: reports/sga_optimization/data/depletion_analysis.csv
5. Log findings to ANALYSIS_LOG.md
```

---

## Phase 2: Historical Conversion Rate Analysis

### Objective
Establish statistically valid conversion rates by tier with confidence intervals.

### Cursor Prompt 2.1: Calculate Conversion Rates with Confidence Intervals

```
@workspace Calculate historical conversion rates by tier with statistical confidence intervals.

MCP BIGQUERY ACCESS REQUIRED

Task:
1. Run SQL to get conversion data for "Provided Lead List" leads:

```sql
-- ============================================================================
-- CONVERSION RATES BY TIER WITH CONFIDENCE INTERVALS
-- Uses Wilson score interval for binomial proportions
-- ============================================================================

WITH historical_leads AS (
    SELECT 
        l.Id as lead_id,
        l.stage_entered_contacting__c as contacted_date,
        l.MQL_Date__c,
        CASE WHEN l.MQL_Date__c IS NOT NULL THEN 1 ELSE 0 END as converted,
        -- Approximate tier based on available data
        COALESCE(ls.score_tier, 'UNKNOWN') as score_tier
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scores_v3_current` ls 
        ON l.Id = ls.lead_id
    WHERE l.Lead_Source__c = 'Provided Lead List'
      AND l.stage_entered_contacting__c >= '2024-01-01'
      AND l.stage_entered_contacting__c <= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

tier_stats AS (
    SELECT 
        score_tier,
        COUNT(*) as n,
        SUM(converted) as successes,
        AVG(converted) as conversion_rate
    FROM historical_leads
    WHERE score_tier != 'UNKNOWN'
    GROUP BY score_tier
)

SELECT 
    score_tier,
    n,
    successes,
    ROUND(conversion_rate * 100, 2) as conversion_rate_pct,
    
    -- Wilson score 95% confidence interval
    -- Lower bound
    ROUND((
        (conversion_rate + 1.96*1.96/(2*n) - 1.96 * SQRT((conversion_rate*(1-conversion_rate) + 1.96*1.96/(4*n))/n))
        / (1 + 1.96*1.96/n)
    ) * 100, 2) as ci_lower_pct,
    
    -- Upper bound  
    ROUND((
        (conversion_rate + 1.96*1.96/(2*n) + 1.96 * SQRT((conversion_rate*(1-conversion_rate) + 1.96*1.96/(4*n))/n))
        / (1 + 1.96*1.96/n)
    ) * 100, 2) as ci_upper_pct,
    
    -- Lift vs baseline (3.82%)
    ROUND(conversion_rate / 0.0382, 2) as lift_vs_baseline
    
FROM tier_stats
ORDER BY conversion_rate DESC;
```

2. Save to: reports/sga_optimization/data/tier_conversion_rates.csv
3. Create a summary table showing:
   - Expected conversions per 100 leads by tier
   - 95% CI for conversion rate
   - Statistical significance vs baseline (chi-square test)
4. Log to ANALYSIS_LOG.md
```

### Cursor Prompt 2.2: Validate Tier Performance (V3 vs V4 Hybrid)

```
@workspace Validate the V3+V4 hybrid methodology performance on historical data.

MCP BIGQUERY ACCESS REQUIRED

Reference: C:\Users\russe\Documents\Lead Scoring\V3+V4_testing\reports\FINAL_V3_VS_V4_INVESTIGATION_REPORT.md

Task:
1. Query the investigation results to confirm tier ordering:

```sql
-- ============================================================================
-- V3 TIER PERFORMANCE VALIDATION (from Q1-Q3 2025 investigation)
-- Confirms tier ordering is statistically valid
-- ============================================================================

-- Use data from V3+V4 investigation if available, otherwise replicate
WITH investigation_results AS (
    SELECT 
        'TIER_1_PRIME_MOVER' as tier, 270 as leads, 20 as conversions, 0.0741 as rate, 0.0008 as p_value_vs_t2
    UNION ALL SELECT 'TIER_2_PROVEN_MOVER', 7808, 250, 0.0320, NULL
    UNION ALL SELECT 'TIER_3_MODERATE_BLEEDER', 298, 9, 0.0302, NULL
    UNION ALL SELECT 'TIER_5_HEAVY_BLEEDER', 239, 5, 0.0209, NULL
    UNION ALL SELECT 'STANDARD', 9185, 294, 0.0320, NULL
)

SELECT 
    tier,
    leads,
    conversions,
    ROUND(rate * 100, 2) as conversion_rate_pct,
    ROUND(rate / 0.0324, 2) as lift_vs_baseline,
    p_value_vs_t2,
    CASE 
        WHEN p_value_vs_t2 < 0.05 THEN 'SIGNIFICANT'
        WHEN p_value_vs_t2 IS NULL THEN 'N/A'
        ELSE 'NOT SIGNIFICANT'
    END as significance
FROM investigation_results
ORDER BY rate DESC;
```

2. Confirm: T1 > T2 is statistically significant (p < 0.05)
3. Document V4 upgrade path value: STANDARD leads with V4 >= 80% convert at 4.60%
4. Log validation results to ANALYSIS_LOG.md
```

---

## Phase 3: Optimal Tier Distribution Analysis

### Objective
Determine the optimal tier mix for 3,000 leads/month that balances conversion rate vs. pool sustainability.

### Cursor Prompt 3.1: Build Optimization Model

```
@workspace Create a Python script to optimize tier distribution for 3,000 monthly leads.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create scripts/optimization/tier_distribution_optimizer.py with:

```python
"""
Tier Distribution Optimizer for SGA Lead Lists
Optimizes 3,000 leads/month across 15 SGAs (200 each)

Objective: Maximize expected conversions while maintaining pool sustainability
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize, LinearConstraint
from dataclasses import dataclass
from typing import Dict, List, Tuple
import json
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================
TOTAL_LEADS_PER_MONTH = 3000
NUM_SGAS = 15
LEADS_PER_SGA = 200
SUSTAINABILITY_HORIZON_MONTHS = 12  # Plan for 1-year sustainability

# Output paths
REPORTS_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation\reports\sga_optimization")
DATA_DIR = REPORTS_DIR / "data"
FIGURES_DIR = REPORTS_DIR / "figures"

@dataclass
class TierConfig:
    """Configuration for each tier"""
    name: str
    pool_size: int
    conversion_rate: float
    conversion_rate_ci_lower: float
    conversion_rate_ci_upper: float
    expected_conversion_rate: float  # From V3 model

# ============================================================================
# TIER DATA (Update with actual values from Phase 1 & 2)
# ============================================================================
TIER_CONFIGS = {
    'TIER_1A_PRIME_MOVER_CFP': TierConfig(
        name='TIER_1A_PRIME_MOVER_CFP',
        pool_size=500,  # UPDATE from Phase 1
        conversion_rate=0.1644,
        conversion_rate_ci_lower=0.075,
        conversion_rate_ci_upper=0.254,
        expected_conversion_rate=0.1644
    ),
    'TIER_1B_PRIME_MOVER_SERIES65': TierConfig(
        name='TIER_1B_PRIME_MOVER_SERIES65',
        pool_size=800,  # UPDATE from Phase 1
        conversion_rate=0.1648,
        conversion_rate_ci_lower=0.086,
        conversion_rate_ci_upper=0.244,
        expected_conversion_rate=0.1648
    ),
    'TIER_1_PRIME_MOVER': TierConfig(
        name='TIER_1_PRIME_MOVER',
        pool_size=3000,  # UPDATE from Phase 1
        conversion_rate=0.1321,
        conversion_rate_ci_lower=0.089,
        conversion_rate_ci_upper=0.175,
        expected_conversion_rate=0.1321
    ),
    'TIER_2_PROVEN_MOVER': TierConfig(
        name='TIER_2_PROVEN_MOVER',
        pool_size=50000,  # UPDATE from Phase 1
        conversion_rate=0.0859,
        conversion_rate_ci_lower=0.076,
        conversion_rate_ci_upper=0.097,
        expected_conversion_rate=0.0859
    ),
    'TIER_3_MODERATE_BLEEDER': TierConfig(
        name='TIER_3_MODERATE_BLEEDER',
        pool_size=5000,  # UPDATE from Phase 1
        conversion_rate=0.0952,
        conversion_rate_ci_lower=0.045,
        conversion_rate_ci_upper=0.170,
        expected_conversion_rate=0.0952
    ),
    'TIER_4_EXPERIENCED_MOVER': TierConfig(
        name='TIER_4_EXPERIENCED_MOVER',
        pool_size=2000,  # UPDATE from Phase 1
        conversion_rate=0.1154,
        conversion_rate_ci_lower=0.035,
        conversion_rate_ci_upper=0.270,
        expected_conversion_rate=0.1154
    ),
    'TIER_5_HEAVY_BLEEDER': TierConfig(
        name='TIER_5_HEAVY_BLEEDER',
        pool_size=4000,  # UPDATE from Phase 1
        conversion_rate=0.0727,
        conversion_rate_ci_lower=0.024,
        conversion_rate_ci_upper=0.160,
        expected_conversion_rate=0.0727
    ),
    'V4_UPGRADE': TierConfig(
        name='V4_UPGRADE',
        pool_size=15000,  # UPDATE from Phase 1 (STANDARD with V4 >= 80%)
        conversion_rate=0.0460,
        conversion_rate_ci_lower=0.034,
        conversion_rate_ci_upper=0.060,
        expected_conversion_rate=0.0460
    )
}


def calculate_expected_conversions(tier_allocations: Dict[str, int]) -> float:
    """Calculate expected conversions given tier allocations."""
    total = 0
    for tier_name, count in tier_allocations.items():
        if tier_name in TIER_CONFIGS:
            total += count * TIER_CONFIGS[tier_name].conversion_rate
    return total


def calculate_months_until_depletion(tier_allocations: Dict[str, int]) -> Dict[str, float]:
    """Calculate how many months until each tier is depleted."""
    depletion = {}
    for tier_name, count in tier_allocations.items():
        if tier_name in TIER_CONFIGS and count > 0:
            pool = TIER_CONFIGS[tier_name].pool_size
            depletion[tier_name] = pool / count
        else:
            depletion[tier_name] = float('inf')
    return depletion


def optimize_distribution(
    total_leads: int = TOTAL_LEADS_PER_MONTH,
    min_months_sustainability: int = SUSTAINABILITY_HORIZON_MONTHS,
    strategy: str = 'maximize_conversions'
) -> Dict[str, int]:
    """
    Optimize tier distribution.
    
    Strategies:
    - 'maximize_conversions': Max conversions subject to sustainability constraint
    - 'maximize_sustainability': Maximize min months until any tier depleted
    - 'balanced': Balance conversions and sustainability equally
    """
    
    tier_names = list(TIER_CONFIGS.keys())
    n_tiers = len(tier_names)
    
    # Get tier parameters
    rates = np.array([TIER_CONFIGS[t].conversion_rate for t in tier_names])
    pools = np.array([TIER_CONFIGS[t].pool_size for t in tier_names])
    
    # Sustainability constraint: monthly_allocation <= pool_size / min_months
    max_sustainable = pools / min_months_sustainability
    
    if strategy == 'maximize_conversions':
        # Maximize: sum(allocation[i] * rate[i])
        # Subject to: sum(allocation) = total_leads
        #            allocation[i] <= max_sustainable[i]
        #            allocation[i] >= 0
        
        def objective(x):
            return -np.sum(x * rates)  # Negative because we minimize
        
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - total_leads}
        ]
        
        bounds = [(0, min(max_s, total_leads)) for max_s in max_sustainable]
        
        x0 = np.ones(n_tiers) * (total_leads / n_tiers)
        x0 = np.minimum(x0, max_sustainable)
        x0 = x0 * (total_leads / x0.sum())  # Scale to meet constraint
        
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        allocations = {tier_names[i]: int(round(result.x[i])) for i in range(n_tiers)}
        
    elif strategy == 'balanced':
        # Multi-objective: maximize conversions AND sustainability
        
        def objective(x):
            conversions = np.sum(x * rates)
            min_months = np.min(np.where(x > 0, pools / x, float('inf')))
            # Normalize and combine (higher is better for both)
            conv_score = conversions / (total_leads * rates.max())
            sust_score = min(min_months / 24, 1)  # Cap at 24 months
            return -(0.5 * conv_score + 0.5 * sust_score)
        
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - total_leads}]
        bounds = [(0, total_leads) for _ in range(n_tiers)]
        x0 = np.ones(n_tiers) * (total_leads / n_tiers)
        
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        allocations = {tier_names[i]: int(round(result.x[i])) for i in range(n_tiers)}
    
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    # Adjust to exactly hit total_leads
    diff = total_leads - sum(allocations.values())
    if diff != 0:
        # Add/remove from largest pool tier
        largest_tier = max(tier_names, key=lambda t: TIER_CONFIGS[t].pool_size)
        allocations[largest_tier] += diff
    
    return allocations


def generate_scenarios() -> pd.DataFrame:
    """Generate multiple optimization scenarios for comparison."""
    
    scenarios = []
    
    for strategy in ['maximize_conversions', 'balanced']:
        for sustainability in [6, 12, 18, 24]:
            alloc = optimize_distribution(
                total_leads=TOTAL_LEADS_PER_MONTH,
                min_months_sustainability=sustainability,
                strategy=strategy
            )
            
            exp_conv = calculate_expected_conversions(alloc)
            depletion = calculate_months_until_depletion(alloc)
            min_depletion = min(v for v in depletion.values() if v < float('inf'))
            
            scenarios.append({
                'strategy': strategy,
                'sustainability_months': sustainability,
                'expected_conversions': round(exp_conv, 1),
                'expected_conversion_rate': round(exp_conv / TOTAL_LEADS_PER_MONTH * 100, 2),
                'min_months_until_depletion': round(min_depletion, 1),
                'tier_allocations': alloc
            })
    
    return pd.DataFrame(scenarios)


def main():
    print("=" * 70)
    print("SGA LEAD DISTRIBUTION OPTIMIZATION")
    print("=" * 70)
    print(f"Total leads/month: {TOTAL_LEADS_PER_MONTH:,}")
    print(f"SGAs: {NUM_SGAS}")
    print(f"Leads per SGA: {LEADS_PER_SGA}")
    print()
    
    # Generate scenarios
    scenarios_df = generate_scenarios()
    
    print("\n" + "=" * 70)
    print("SCENARIO COMPARISON")
    print("=" * 70)
    print(scenarios_df[['strategy', 'sustainability_months', 
                        'expected_conversions', 'expected_conversion_rate',
                        'min_months_until_depletion']].to_string(index=False))
    
    # Save results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    scenarios_df.to_csv(DATA_DIR / "optimization_scenarios.csv", index=False)
    
    # Detailed allocation for recommended scenario
    print("\n" + "=" * 70)
    print("RECOMMENDED ALLOCATION (Balanced, 12-month sustainability)")
    print("=" * 70)
    
    recommended = optimize_distribution(
        total_leads=TOTAL_LEADS_PER_MONTH,
        min_months_sustainability=12,
        strategy='balanced'
    )
    
    for tier, count in sorted(recommended.items(), key=lambda x: -x[1]):
        config = TIER_CONFIGS[tier]
        exp_conv = count * config.conversion_rate
        print(f"{tier}: {count:,} leads -> {exp_conv:.1f} expected conversions")
    
    # Save recommended allocation
    with open(DATA_DIR / "recommended_allocation.json", 'w') as f:
        json.dump({
            'allocation': recommended,
            'expected_conversions': calculate_expected_conversions(recommended),
            'months_until_depletion': calculate_months_until_depletion(recommended)
        }, f, indent=2)
    
    print(f"\n[INFO] Results saved to {DATA_DIR}")
    return scenarios_df


if __name__ == "__main__":
    main()
```

2. Run the script and capture output
3. Save results to reports/sga_optimization/data/
4. Log key findings to ANALYSIS_LOG.md
```

### Cursor Prompt 3.2: Simulate 12-Month Pool Depletion

```
@workspace Create a simulation showing pool depletion over 12 months for different strategies.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create scripts/optimization/depletion_simulation.py:

```python
"""
12-Month Pool Depletion Simulation
Shows how different allocation strategies affect pool sustainability
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json

REPORTS_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation\reports\sga_optimization")
FIGURES_DIR = REPORTS_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Load tier configs from previous step
# UPDATE these with actual values from Phase 1
TIER_POOLS = {
    'TIER_1A_PRIME_MOVER_CFP': 500,
    'TIER_1B_PRIME_MOVER_SERIES65': 800,
    'TIER_1_PRIME_MOVER': 3000,
    'TIER_2_PROVEN_MOVER': 50000,
    'TIER_3_MODERATE_BLEEDER': 5000,
    'TIER_4_EXPERIENCED_MOVER': 2000,
    'TIER_5_HEAVY_BLEEDER': 4000,
    'V4_UPGRADE': 15000
}

# Pool replenishment rate (new prospects entering each month)
# Estimate: ~2% of pool refreshes monthly from new registrations, firm changes
REPLENISHMENT_RATE = 0.02


def simulate_depletion(
    monthly_allocation: dict,
    months: int = 12,
    include_replenishment: bool = True
) -> pd.DataFrame:
    """
    Simulate pool depletion over time.
    
    Returns DataFrame with columns for each tier showing remaining pool.
    """
    
    results = []
    pools = TIER_POOLS.copy()
    
    for month in range(months + 1):
        row = {'month': month}
        for tier, pool in pools.items():
            row[f'{tier}_remaining'] = pool
            row[f'{tier}_pct_remaining'] = pool / TIER_POOLS[tier] * 100
        results.append(row)
        
        if month < months:
            for tier in pools:
                # Subtract monthly usage
                usage = monthly_allocation.get(tier, 0)
                pools[tier] = max(0, pools[tier] - usage)
                
                # Add replenishment (if enabled)
                if include_replenishment:
                    replenishment = int(TIER_POOLS[tier] * REPLENISHMENT_RATE)
                    pools[tier] = min(pools[tier] + replenishment, TIER_POOLS[tier] * 1.1)
    
    return pd.DataFrame(results)


def plot_depletion_curves(results: pd.DataFrame, title: str, filename: str):
    """Create visualization of pool depletion over time."""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    tier_colors = {
        'TIER_1A_PRIME_MOVER_CFP': '#FF6B6B',
        'TIER_1B_PRIME_MOVER_SERIES65': '#FF8E8E',
        'TIER_1_PRIME_MOVER': '#4ECDC4',
        'TIER_2_PROVEN_MOVER': '#45B7D1',
        'TIER_3_MODERATE_BLEEDER': '#96CEB4',
        'TIER_4_EXPERIENCED_MOVER': '#FFEAA7',
        'TIER_5_HEAVY_BLEEDER': '#DFE6E9',
        'V4_UPGRADE': '#A29BFE'
    }
    
    for tier in TIER_POOLS.keys():
        col = f'{tier}_pct_remaining'
        if col in results.columns:
            ax.plot(results['month'], results[col], 
                   label=tier.replace('_', ' ').title()[:20],
                   color=tier_colors.get(tier, 'gray'),
                   linewidth=2)
    
    ax.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='50% Threshold')
    ax.axhline(y=25, color='darkred', linestyle='--', alpha=0.5, label='25% Critical')
    
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Pool Remaining (%)', fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 110)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[INFO] Saved {filename}")


def main():
    print("=" * 70)
    print("POOL DEPLETION SIMULATION (12 Months)")
    print("=" * 70)
    
    # Scenario 1: Aggressive (maximize conversions)
    aggressive_allocation = {
        'TIER_1A_PRIME_MOVER_CFP': 50,
        'TIER_1B_PRIME_MOVER_SERIES65': 60,
        'TIER_1_PRIME_MOVER': 300,
        'TIER_2_PROVEN_MOVER': 1500,
        'TIER_3_MODERATE_BLEEDER': 300,
        'TIER_4_EXPERIENCED_MOVER': 200,
        'TIER_5_HEAVY_BLEEDER': 100,
        'V4_UPGRADE': 490
    }
    
    # Scenario 2: Conservative (maximize sustainability)
    conservative_allocation = {
        'TIER_1A_PRIME_MOVER_CFP': 30,
        'TIER_1B_PRIME_MOVER_SERIES65': 40,
        'TIER_1_PRIME_MOVER': 200,
        'TIER_2_PROVEN_MOVER': 1800,
        'TIER_3_MODERATE_BLEEDER': 200,
        'TIER_4_EXPERIENCED_MOVER': 100,
        'TIER_5_HEAVY_BLEEDER': 130,
        'V4_UPGRADE': 500
    }
    
    # Simulate both
    aggressive_results = simulate_depletion(aggressive_allocation, months=12)
    conservative_results = simulate_depletion(conservative_allocation, months=12)
    
    # Generate plots
    plot_depletion_curves(
        aggressive_results, 
        'Pool Depletion: Aggressive Strategy (3,000 leads/month)',
        'depletion_aggressive.png'
    )
    
    plot_depletion_curves(
        conservative_results,
        'Pool Depletion: Conservative Strategy (3,000 leads/month)',
        'depletion_conservative.png'
    )
    
    # Summary comparison
    print("\n" + "=" * 70)
    print("12-MONTH PROJECTION SUMMARY")
    print("=" * 70)
    
    for name, results in [('Aggressive', aggressive_results), ('Conservative', conservative_results)]:
        print(f"\n{name} Strategy at Month 12:")
        final = results[results['month'] == 12].iloc[0]
        for tier in ['TIER_1A_PRIME_MOVER_CFP', 'TIER_1_PRIME_MOVER', 'TIER_2_PROVEN_MOVER']:
            pct = final[f'{tier}_pct_remaining']
            status = '⚠️ LOW' if pct < 50 else '✅ OK'
            print(f"  {tier}: {pct:.1f}% remaining {status}")
    
    # Save data
    aggressive_results.to_csv(REPORTS_DIR / 'data' / 'depletion_aggressive.csv', index=False)
    conservative_results.to_csv(REPORTS_DIR / 'data' / 'depletion_conservative.csv', index=False)
    
    print(f"\n[INFO] Simulation complete. Figures saved to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
```

2. Run the simulation
3. Review the generated plots in figures/
4. Log findings to ANALYSIS_LOG.md
```

---

## Phase 4: SGA Distribution Strategy Analysis

### Objective
Determine whether SGAs should receive uniform tier mixes or specialize by tier.

### Cursor Prompt 4.1: Analyze Uniform vs. Specialized Distribution

```
@workspace Analyze whether SGAs should receive uniform or specialized lead distributions.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create scripts/optimization/sga_distribution_analysis.py:

```python
"""
SGA Distribution Strategy Analysis
Compare uniform vs. specialized distribution approaches
"""

import pandas as pd
import numpy as np
from scipy import stats
import json
from pathlib import Path

REPORTS_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation\reports\sga_optimization")

# SGA configuration
NUM_SGAS = 15
LEADS_PER_SGA = 200
TOTAL_LEADS = NUM_SGAS * LEADS_PER_SGA

# Tier conversion rates
TIER_RATES = {
    'TIER_1A_PRIME_MOVER_CFP': 0.1644,
    'TIER_1B_PRIME_MOVER_SERIES65': 0.1648,
    'TIER_1_PRIME_MOVER': 0.1321,
    'TIER_2_PROVEN_MOVER': 0.0859,
    'TIER_3_MODERATE_BLEEDER': 0.0952,
    'TIER_4_EXPERIENCED_MOVER': 0.1154,
    'TIER_5_HEAVY_BLEEDER': 0.0727,
    'V4_UPGRADE': 0.0460
}

# Optimal monthly allocation (from Phase 3)
OPTIMAL_ALLOCATION = {
    'TIER_1A_PRIME_MOVER_CFP': 40,
    'TIER_1B_PRIME_MOVER_SERIES65': 50,
    'TIER_1_PRIME_MOVER': 250,
    'TIER_2_PROVEN_MOVER': 1600,
    'TIER_3_MODERATE_BLEEDER': 250,
    'TIER_4_EXPERIENCED_MOVER': 150,
    'TIER_5_HEAVY_BLEEDER': 160,
    'V4_UPGRADE': 500
}


def strategy_uniform_distribution() -> pd.DataFrame:
    """
    Strategy 1: Each SGA gets proportional share of each tier.
    Everyone gets same tier mix.
    """
    
    sga_allocations = []
    
    for sga_id in range(1, NUM_SGAS + 1):
        allocation = {}
        remaining = LEADS_PER_SGA
        
        for tier, total in OPTIMAL_ALLOCATION.items():
            # Proportional share
            share = int(total / NUM_SGAS)
            allocation[tier] = min(share, remaining)
            remaining -= allocation[tier]
        
        # Distribute remainder to largest tier
        if remaining > 0:
            allocation['TIER_2_PROVEN_MOVER'] += remaining
        
        expected_conv = sum(allocation[t] * TIER_RATES[t] for t in allocation)
        
        sga_allocations.append({
            'sga_id': sga_id,
            'strategy': 'UNIFORM',
            'total_leads': sum(allocation.values()),
            'expected_conversions': expected_conv,
            'expected_rate': expected_conv / LEADS_PER_SGA,
            **allocation
        })
    
    return pd.DataFrame(sga_allocations)


def strategy_specialized_distribution() -> pd.DataFrame:
    """
    Strategy 2: Specialize SGAs by tier expertise.
    Some SGAs focus on high-tier leads, others on volume.
    """
    
    sga_allocations = []
    
    # Designate SGA roles:
    # 3 SGAs: "Elite" - focus on Tier 1A, 1B, 1 (lower volume, higher quality)
    # 5 SGAs: "Balanced" - mix of tiers
    # 7 SGAs: "Volume" - focus on Tier 2, V4 Upgrades (higher volume)
    
    elite_sgas = [1, 2, 3]
    balanced_sgas = [4, 5, 6, 7, 8]
    volume_sgas = [9, 10, 11, 12, 13, 14, 15]
    
    # Allocate elite SGAs
    for sga_id in elite_sgas:
        allocation = {
            'TIER_1A_PRIME_MOVER_CFP': 13,  # 40/3
            'TIER_1B_PRIME_MOVER_SERIES65': 17,  # 50/3
            'TIER_1_PRIME_MOVER': 83,  # 250/3
            'TIER_2_PROVEN_MOVER': 50,
            'TIER_3_MODERATE_BLEEDER': 20,
            'TIER_4_EXPERIENCED_MOVER': 10,
            'TIER_5_HEAVY_BLEEDER': 7,
            'V4_UPGRADE': 0
        }
        expected_conv = sum(allocation[t] * TIER_RATES[t] for t in allocation)
        sga_allocations.append({
            'sga_id': sga_id,
            'strategy': 'SPECIALIZED',
            'role': 'ELITE',
            'total_leads': sum(allocation.values()),
            'expected_conversions': expected_conv,
            'expected_rate': expected_conv / sum(allocation.values()),
            **allocation
        })
    
    # Allocate balanced SGAs
    for sga_id in balanced_sgas:
        allocation = {
            'TIER_1A_PRIME_MOVER_CFP': 0,
            'TIER_1B_PRIME_MOVER_SERIES65': 0,
            'TIER_1_PRIME_MOVER': 0,
            'TIER_2_PROVEN_MOVER': 120,
            'TIER_3_MODERATE_BLEEDER': 30,
            'TIER_4_EXPERIENCED_MOVER': 20,
            'TIER_5_HEAVY_BLEEDER': 10,
            'V4_UPGRADE': 20
        }
        expected_conv = sum(allocation[t] * TIER_RATES[t] for t in allocation)
        sga_allocations.append({
            'sga_id': sga_id,
            'strategy': 'SPECIALIZED',
            'role': 'BALANCED',
            'total_leads': sum(allocation.values()),
            'expected_conversions': expected_conv,
            'expected_rate': expected_conv / sum(allocation.values()),
            **allocation
        })
    
    # Allocate volume SGAs
    for sga_id in volume_sgas:
        allocation = {
            'TIER_1A_PRIME_MOVER_CFP': 0,
            'TIER_1B_PRIME_MOVER_SERIES65': 0,
            'TIER_1_PRIME_MOVER': 0,
            'TIER_2_PROVEN_MOVER': 130,
            'TIER_3_MODERATE_BLEEDER': 10,
            'TIER_4_EXPERIENCED_MOVER': 0,
            'TIER_5_HEAVY_BLEEDER': 10,
            'V4_UPGRADE': 50
        }
        expected_conv = sum(allocation[t] * TIER_RATES[t] for t in allocation)
        sga_allocations.append({
            'sga_id': sga_id,
            'strategy': 'SPECIALIZED',
            'role': 'VOLUME',
            'total_leads': sum(allocation.values()),
            'expected_conversions': expected_conv,
            'expected_rate': expected_conv / sum(allocation.values()),
            **allocation
        })
    
    return pd.DataFrame(sga_allocations)


def compare_strategies():
    """Compare uniform vs specialized strategies."""
    
    uniform = strategy_uniform_distribution()
    specialized = strategy_specialized_distribution()
    
    print("=" * 70)
    print("STRATEGY COMPARISON: UNIFORM vs SPECIALIZED")
    print("=" * 70)
    
    print("\n--- UNIFORM DISTRIBUTION ---")
    print(f"Total Expected Conversions: {uniform['expected_conversions'].sum():.1f}")
    print(f"Average Expected Rate: {uniform['expected_rate'].mean()*100:.2f}%")
    print(f"Variance in SGA Performance: {uniform['expected_conversions'].var():.2f}")
    
    print("\n--- SPECIALIZED DISTRIBUTION ---")
    print(f"Total Expected Conversions: {specialized['expected_conversions'].sum():.1f}")
    print(f"Average Expected Rate: {specialized['expected_rate'].mean()*100:.2f}%")
    print(f"Variance in SGA Performance: {specialized['expected_conversions'].var():.2f}")
    
    # Statistical test: Are the expected conversions significantly different?
    t_stat, p_value = stats.ttest_ind(
        uniform['expected_conversions'], 
        specialized['expected_conversions']
    )
    print(f"\nStatistical Comparison:")
    print(f"  T-statistic: {t_stat:.3f}")
    print(f"  P-value: {p_value:.4f}")
    print(f"  Significant at α=0.05: {'YES' if p_value < 0.05 else 'NO'}")
    
    # By role analysis for specialized
    print("\n--- SPECIALIZED BY ROLE ---")
    role_summary = specialized.groupby('role').agg({
        'expected_conversions': ['mean', 'sum'],
        'expected_rate': 'mean'
    }).round(3)
    print(role_summary)
    
    # Save results
    uniform.to_csv(REPORTS_DIR / 'data' / 'sga_uniform_strategy.csv', index=False)
    specialized.to_csv(REPORTS_DIR / 'data' / 'sga_specialized_strategy.csv', index=False)
    
    return uniform, specialized


def main():
    uniform, specialized = compare_strategies()
    
    # Generate recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    
    uniform_total = uniform['expected_conversions'].sum()
    specialized_total = specialized['expected_conversions'].sum()
    
    if specialized_total > uniform_total * 1.05:  # 5% threshold
        print("SPECIALIZED distribution recommended:")
        print("  - Designate 3 'Elite' SGAs for Tier 1 leads")
        print("  - Expected +{:.1f} additional conversions/month".format(specialized_total - uniform_total))
    else:
        print("UNIFORM distribution recommended:")
        print("  - Simpler to administer")
        print("  - More fair perception among SGAs")
        print("  - Minimal conversion difference")


if __name__ == "__main__":
    main()
```

2. Run the analysis
3. Document recommendation in ANALYSIS_LOG.md
```

---

## Phase 5: Conversion Forecasting Model

### Objective
Build a model to predict expected conversions for each monthly list with confidence intervals.

### Cursor Prompt 5.1: Build Monthly Conversion Forecast Model

```
@workspace Create a monthly conversion forecasting model with confidence intervals.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create scripts/optimization/conversion_forecast.py:

```python
"""
Monthly Conversion Forecasting Model
Predicts expected conversions with confidence intervals
"""

import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Tuple, Dict
import json
from pathlib import Path

REPORTS_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation\reports\sga_optimization")

@dataclass
class TierForecast:
    """Forecast for a single tier"""
    tier: str
    leads: int
    expected_conversions: float
    ci_lower: float
    ci_upper: float
    conversion_rate: float
    ci_lower_rate: float
    ci_upper_rate: float


def forecast_tier_conversions(
    tier: str,
    leads: int,
    conversion_rate: float,
    rate_ci_lower: float,
    rate_ci_upper: float
) -> TierForecast:
    """
    Forecast conversions for a tier using binomial distribution.
    """
    
    expected = leads * conversion_rate
    
    # Use normal approximation to binomial for CI
    # Var(X) = n * p * (1-p)
    variance = leads * conversion_rate * (1 - conversion_rate)
    std = np.sqrt(variance)
    
    # 95% CI using normal approximation
    ci_lower = max(0, expected - 1.96 * std)
    ci_upper = expected + 1.96 * std
    
    return TierForecast(
        tier=tier,
        leads=leads,
        expected_conversions=expected,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        conversion_rate=conversion_rate,
        ci_lower_rate=rate_ci_lower,
        ci_upper_rate=rate_ci_upper
    )


def forecast_monthly_list(allocation: Dict[str, int]) -> pd.DataFrame:
    """
    Forecast total conversions for a monthly lead list.
    """
    
    # Tier conversion rates with CIs (from Phase 2)
    TIER_PARAMS = {
        'TIER_1A_PRIME_MOVER_CFP': (0.1644, 0.075, 0.254),
        'TIER_1B_PRIME_MOVER_SERIES65': (0.1648, 0.086, 0.244),
        'TIER_1_PRIME_MOVER': (0.1321, 0.089, 0.175),
        'TIER_2_PROVEN_MOVER': (0.0859, 0.076, 0.097),
        'TIER_3_MODERATE_BLEEDER': (0.0952, 0.045, 0.170),
        'TIER_4_EXPERIENCED_MOVER': (0.1154, 0.035, 0.270),
        'TIER_5_HEAVY_BLEEDER': (0.0727, 0.024, 0.160),
        'V4_UPGRADE': (0.0460, 0.034, 0.060)
    }
    
    forecasts = []
    
    for tier, leads in allocation.items():
        if tier in TIER_PARAMS and leads > 0:
            rate, ci_low, ci_high = TIER_PARAMS[tier]
            forecast = forecast_tier_conversions(tier, leads, rate, ci_low, ci_high)
            forecasts.append(forecast)
    
    return pd.DataFrame([f.__dict__ for f in forecasts])


def aggregate_forecast(tier_forecasts: pd.DataFrame) -> Dict:
    """
    Aggregate tier forecasts into monthly total with combined CI.
    """
    
    total_leads = tier_forecasts['leads'].sum()
    total_expected = tier_forecasts['expected_conversions'].sum()
    
    # Combine variances (assuming independence)
    # Var(sum) = sum(Var_i)
    # For binomial: Var = n*p*(1-p)
    total_variance = sum(
        row['leads'] * row['conversion_rate'] * (1 - row['conversion_rate'])
        for _, row in tier_forecasts.iterrows()
    )
    total_std = np.sqrt(total_variance)
    
    ci_lower = max(0, total_expected - 1.96 * total_std)
    ci_upper = total_expected + 1.96 * total_std
    
    return {
        'total_leads': int(total_leads),
        'expected_conversions': round(total_expected, 1),
        'ci_lower': round(ci_lower, 1),
        'ci_upper': round(ci_upper, 1),
        'expected_rate_pct': round(total_expected / total_leads * 100, 2),
        'ci_lower_rate_pct': round(ci_lower / total_leads * 100, 2),
        'ci_upper_rate_pct': round(ci_upper / total_leads * 100, 2)
    }


def monte_carlo_simulation(
    allocation: Dict[str, int],
    n_simulations: int = 10000
) -> pd.DataFrame:
    """
    Monte Carlo simulation for conversion outcomes.
    More accurate than normal approximation for rare events.
    """
    
    TIER_PARAMS = {
        'TIER_1A_PRIME_MOVER_CFP': 0.1644,
        'TIER_1B_PRIME_MOVER_SERIES65': 0.1648,
        'TIER_1_PRIME_MOVER': 0.1321,
        'TIER_2_PROVEN_MOVER': 0.0859,
        'TIER_3_MODERATE_BLEEDER': 0.0952,
        'TIER_4_EXPERIENCED_MOVER': 0.1154,
        'TIER_5_HEAVY_BLEEDER': 0.0727,
        'V4_UPGRADE': 0.0460
    }
    
    simulations = []
    
    for _ in range(n_simulations):
        total_conversions = 0
        for tier, leads in allocation.items():
            if tier in TIER_PARAMS and leads > 0:
                # Simulate binomial outcome
                conversions = np.random.binomial(leads, TIER_PARAMS[tier])
                total_conversions += conversions
        simulations.append(total_conversions)
    
    simulations = np.array(simulations)
    
    return {
        'mean': np.mean(simulations),
        'median': np.median(simulations),
        'std': np.std(simulations),
        'ci_2.5': np.percentile(simulations, 2.5),
        'ci_97.5': np.percentile(simulations, 97.5),
        'ci_5': np.percentile(simulations, 5),
        'ci_95': np.percentile(simulations, 95),
        'min': np.min(simulations),
        'max': np.max(simulations),
        'simulations': simulations
    }


def main():
    print("=" * 70)
    print("MONTHLY CONVERSION FORECAST MODEL")
    print("=" * 70)
    
    # Example allocation (from Phase 3 optimization)
    allocation = {
        'TIER_1A_PRIME_MOVER_CFP': 40,
        'TIER_1B_PRIME_MOVER_SERIES65': 50,
        'TIER_1_PRIME_MOVER': 250,
        'TIER_2_PROVEN_MOVER': 1600,
        'TIER_3_MODERATE_BLEEDER': 250,
        'TIER_4_EXPERIENCED_MOVER': 150,
        'TIER_5_HEAVY_BLEEDER': 160,
        'V4_UPGRADE': 500
    }
    
    print(f"\nAllocation: {sum(allocation.values()):,} total leads")
    
    # Tier-level forecasts
    tier_forecasts = forecast_monthly_list(allocation)
    print("\n--- TIER-LEVEL FORECASTS ---")
    print(tier_forecasts[['tier', 'leads', 'expected_conversions', 'ci_lower', 'ci_upper']].to_string(index=False))
    
    # Aggregate forecast
    aggregate = aggregate_forecast(tier_forecasts)
    print("\n--- AGGREGATE MONTHLY FORECAST ---")
    print(f"Total Leads: {aggregate['total_leads']:,}")
    print(f"Expected Conversions: {aggregate['expected_conversions']}")
    print(f"95% Confidence Interval: [{aggregate['ci_lower']}, {aggregate['ci_upper']}]")
    print(f"Expected Conversion Rate: {aggregate['expected_rate_pct']}%")
    print(f"95% CI Rate: [{aggregate['ci_lower_rate_pct']}%, {aggregate['ci_upper_rate_pct']}%]")
    
    # Monte Carlo simulation
    print("\n--- MONTE CARLO SIMULATION (10,000 iterations) ---")
    mc_results = monte_carlo_simulation(allocation)
    print(f"Mean: {mc_results['mean']:.1f}")
    print(f"Median: {mc_results['median']:.0f}")
    print(f"95% CI: [{mc_results['ci_2.5']:.0f}, {mc_results['ci_97.5']:.0f}]")
    print(f"90% CI: [{mc_results['ci_5']:.0f}, {mc_results['ci_95']:.0f}]")
    print(f"Range: [{mc_results['min']}, {mc_results['max']}]")
    
    # Per-SGA forecast
    print("\n--- PER-SGA FORECAST (200 leads each) ---")
    sga_allocation = {tier: leads // 15 for tier, leads in allocation.items()}
    sga_forecast = aggregate_forecast(forecast_monthly_list(sga_allocation))
    print(f"Expected Conversions per SGA: {sga_forecast['expected_conversions']}")
    print(f"95% CI per SGA: [{sga_forecast['ci_lower']}, {sga_forecast['ci_upper']}]")
    
    # Save results
    results = {
        'allocation': allocation,
        'tier_forecasts': tier_forecasts.to_dict('records'),
        'aggregate_forecast': aggregate,
        'monte_carlo': {k: v for k, v in mc_results.items() if k != 'simulations'},
        'per_sga_forecast': sga_forecast
    }
    
    with open(REPORTS_DIR / 'data' / 'conversion_forecast.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    tier_forecasts.to_csv(REPORTS_DIR / 'data' / 'tier_forecasts.csv', index=False)
    
    print(f"\n[INFO] Forecast saved to {REPORTS_DIR / 'data'}")


if __name__ == "__main__":
    main()
```

2. Run the forecasting model
3. Document expected conversion ranges in ANALYSIS_LOG.md
```

---

## Phase 6: Generate Final Report

### Cursor Prompt 6.1: Generate Comprehensive Analysis Report

```
@workspace Generate the final comprehensive analysis report.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create reports/sga_optimization/final/SGA_Lead_Distribution_Optimization_Report.md with:

```markdown
# SGA Lead Distribution Optimization Report

**Analysis Date**: [CURRENT_DATE]
**Prepared By**: Data Science Team
**Report Version**: 1.0

---

## Executive Summary

This report presents the optimal strategy for distributing 3,000 leads per month across 15 SGAs (200 leads each) to maximize conversions while maintaining pool sustainability.

### Key Findings

| Metric | Value | Confidence Interval |
|--------|-------|---------------------|
| **Expected Monthly Conversions** | [X] | [CI_LOW - CI_HIGH] |
| **Expected Conversion Rate** | [X%] | [CI_LOW% - CI_HIGH%] |
| **Months Until Pool Stress** | [X] | Based on top-tier depletion |
| **Recommended Strategy** | [UNIFORM/SPECIALIZED] | See Section 4 |

### Recommendations

1. **Tier Allocation**: [Recommended allocation by tier]
2. **Distribution Strategy**: [Uniform vs. Specialized]
3. **Sustainability Actions**: [Pool replenishment recommendations]

---

## 1. Prospect Pool Analysis

### 1.1 Total Available Pool by Tier

[INSERT TABLE FROM PHASE 1]

### 1.2 Depletion Projections (12-Month)

[INSERT DEPLETION CHART]

**Key Insight**: [Which tiers are at risk of depletion]

---

## 2. Conversion Rate Validation

### 2.1 Historical Conversion Rates by Tier

[INSERT TABLE FROM PHASE 2]

### 2.2 Statistical Validation

- T1 vs T2: [p-value, significance]
- V4 Upgrade effectiveness: [conversion rate, lift]

---

## 3. Optimal Tier Distribution

### 3.1 Optimization Scenarios

[INSERT SCENARIO COMPARISON TABLE]

### 3.2 Recommended Monthly Allocation

| Tier | Leads | Expected Conv | Rate |
|------|-------|---------------|------|
[INSERT OPTIMIZED ALLOCATION]

---

## 4. SGA Distribution Strategy

### 4.1 Uniform vs. Specialized Comparison

[INSERT COMPARISON TABLE]

### 4.2 Recommendation

[RECOMMENDATION WITH RATIONALE]

---

## 5. Monthly Conversion Forecast

### 5.1 Expected Outcomes

| Scenario | Conversions | Rate |
|----------|-------------|------|
| Best Case (95th percentile) | [X] | [X%] |
| Expected | [X] | [X%] |
| Conservative (5th percentile) | [X] | [X%] |

### 5.2 Per-SGA Expectations

Each SGA (200 leads) can expect:
- **Expected**: [X] conversions/month
- **Range**: [X-Y] conversions/month (90% CI)

---

## 6. Implementation Recommendations

### 6.1 Immediate Actions

1. Update lead list generation SQL with optimized tier quotas
2. Implement [UNIFORM/SPECIALIZED] distribution
3. Set up monthly tier tracking dashboard

### 6.2 Ongoing Monitoring

- Track actual vs. expected conversions by tier weekly
- Monitor pool depletion rates monthly
- Recalibrate tier quotas quarterly

### 6.3 Risk Mitigation

- **Tier 1 Depletion Risk**: [Mitigation strategy]
- **Conversion Rate Drift**: [Monitoring approach]

---

## Appendix

### A. Methodology Notes
### B. Data Sources
### C. Statistical Tests Performed
### D. SQL Queries Used

---

*Report generated using Lead Scoring V3.2.5 + V4.0.0 Hybrid Model*
```

2. Populate all [PLACEHOLDERS] with actual data from Phase 1-5
3. Include all generated charts from figures/
4. Save to reports/sga_optimization/final/
5. Log completion to ANALYSIS_LOG.md
```

### Cursor Prompt 6.2: Create Implementation SQL

```
@workspace Create the optimized lead list generation SQL based on analysis findings.

WORKING DIRECTORY: C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation

Task:
1. Create sql/optimization/optimized_lead_list_v1.sql that implements the recommended tier quotas
2. Add parameters for:
   - Total leads (default 3000)
   - Number of SGAs (default 15)
   - Tier quotas (from optimization)
3. Include SGA assignment logic:
   - Round-robin by tier priority
   - Ensure each SGA gets their quota
4. Add tracking columns:
   - expected_conversions
   - sga_assignment
   - generated_at

Reference the existing: Lead_List_Generation/January_2026_Lead_List_V3_V4_Hybrid.sql
Update the tier quota section with optimized values.
```

---

## Phase 7: Validation and Testing

### Cursor Prompt 7.1: Validate Against Historical Data

```
@workspace Validate the optimized allocation against historical outcomes.

MCP BIGQUERY ACCESS REQUIRED

Task:
1. Query historical lead lists and their actual conversion outcomes:

```sql
-- ============================================================================
-- BACKTEST: Compare predicted vs actual conversions by tier
-- ============================================================================

WITH historical_lists AS (
    -- Get leads from previous months with known outcomes
    SELECT 
        l.Id as lead_id,
        l.stage_entered_contacting__c as contacted_date,
        FORMAT_DATE('%Y-%m', l.stage_entered_contacting__c) as contact_month,
        COALESCE(ls.score_tier, 'UNKNOWN') as score_tier,
        CASE WHEN l.MQL_Date__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scores_v3_current` ls ON l.Id = ls.lead_id
    WHERE l.Lead_Source__c = 'Provided Lead List'
      AND l.stage_entered_contacting__c >= '2024-06-01'
      AND l.stage_entered_contacting__c < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
),

monthly_performance AS (
    SELECT 
        contact_month,
        score_tier,
        COUNT(*) as leads,
        SUM(converted) as conversions,
        ROUND(AVG(converted) * 100, 2) as actual_rate_pct
    FROM historical_lists
    WHERE score_tier != 'UNKNOWN'
    GROUP BY contact_month, score_tier
)

SELECT 
    contact_month,
    score_tier,
    leads,
    conversions,
    actual_rate_pct,
    -- Expected rate (from V3 model)
    CASE score_tier
        WHEN 'TIER_1_PRIME_MOVER' THEN 13.21
        WHEN 'TIER_2_PROVEN_MOVER' THEN 8.59
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 9.52
        ELSE 3.82
    END as expected_rate_pct,
    -- Variance from expected
    actual_rate_pct - CASE score_tier
        WHEN 'TIER_1_PRIME_MOVER' THEN 13.21
        WHEN 'TIER_2_PROVEN_MOVER' THEN 8.59
        WHEN 'TIER_3_MODERATE_BLEEDER' THEN 9.52
        ELSE 3.82
    END as variance_pct
FROM monthly_performance
ORDER BY contact_month DESC, score_tier;
```

2. Calculate prediction accuracy metrics:
   - Mean Absolute Error (MAE)
   - Root Mean Square Error (RMSE)
   - Prediction interval coverage
   
3. Document any systematic biases
4. Update conversion rate estimates if needed
5. Log findings to ANALYSIS_LOG.md
```

---

## Execution Checklist

Use this checklist to track progress:

```markdown
## SGA Lead Distribution Optimization - Execution Checklist

**Started**: ___________
**Analyst**: ___________

### Phase 0: Setup
- [ ] Created directory structure
- [ ] Initialized ANALYSIS_LOG.md

### Phase 1: Prospect Pool Inventory
- [ ] Queried total prospect pool by tier
- [ ] Calculated monthly depletion rates
- [ ] Saved prospect_pool_inventory.csv
- [ ] Saved depletion_analysis.csv

### Phase 2: Conversion Rate Analysis
- [ ] Calculated conversion rates with CIs
- [ ] Validated V3+V4 methodology
- [ ] Saved tier_conversion_rates.csv

### Phase 3: Tier Distribution Optimization
- [ ] Ran optimization model
- [ ] Generated scenario comparison
- [ ] Created depletion simulation charts
- [ ] Saved optimization_scenarios.csv

### Phase 4: SGA Distribution Strategy
- [ ] Compared uniform vs. specialized
- [ ] Generated recommendation
- [ ] Saved strategy comparison data

### Phase 5: Conversion Forecasting
- [ ] Built forecast model
- [ ] Ran Monte Carlo simulation
- [ ] Documented expected ranges
- [ ] Saved conversion_forecast.json

### Phase 6: Final Report
- [ ] Generated comprehensive report
- [ ] Created implementation SQL
- [ ] All charts included

### Phase 7: Validation
- [ ] Backtested against historical data
- [ ] Documented prediction accuracy
- [ ] Updated estimates if needed

**Completed**: ___________
**Final Report Location**: reports/sga_optimization/final/
```

---

## Quick Reference: Key Metrics to Track

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Monthly Leads | 3,000 | | |
| Expected Conv Rate | 8-10% | | |
| Expected Conversions | 240-300 | | |
| Top-Tier Pool Sustainability | 12+ months | | |
| Per-SGA Expected Conv | 16-20 | | |

---

**Document Version**: 1.0  
**Created**: December 24, 2025  
**Purpose**: Cursor.ai agentic analysis guide for SGA lead distribution optimization
