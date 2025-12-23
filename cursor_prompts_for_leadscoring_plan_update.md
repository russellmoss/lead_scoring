# Cursor.ai Prompts: Lead Scoring Plan v3 Update

## Overview

These prompts should be executed **in order**. Each prompt focuses on one major section of `leadscoring_plan.md` and incorporates specific learnings from the V2→V3 signal decay investigation.

**Context for Cursor:** We discovered that the V2 XGBoost model suffered signal decay (4.43x → 1.46x lift) due to lead source shifts and pool depletion. We're pivoting from a complex ML model to a transparent Two-Tier Query system that combines validated SGA intuition with data-driven signals.

---

# PROMPT 1: Add Executive Summary & Strategic Pivot Section

**Instructions for Cursor:**

In `@leadscoring_plan.md`, add a new section immediately after the title and before the Table of Contents. This section explains WHY we pivoted from V2 XGBoost to V3 Two-Tier Query.

**Add this new section:**

```markdown
---

## 🚨 CRITICAL: V2 → V3 Strategic Pivot

### Why We Changed Our Approach

The V2 XGBoost model achieved **4.43x lift** on 2024 test data but collapsed to **1.46x lift** on 2025 production data. This wasn't a model failure—it was a **market reality check**.

#### Root Cause Analysis Summary

| Finding | Impact | Action Taken |
|---------|--------|--------------|
| **Lead Source Shift** | "Provided Lists" dropped from 85.7% → 64.9% of volume | Model trained on one distribution, deployed on another |
| **Pool Depletion** | Top firms (Mariner, Corebridge, Corient) 100% fished out | "Best" leads already contacted in 2024 |
| **Quality Degradation** | 2025 DZ leads: -60% industry tenure, -53% prior firms | Remaining pool is "Junior Stayers" not "Senior Movers" |
| **Channel Performance Gap** | LinkedIn: 5.2% baseline vs Provided Lists: 0.67% | Same signal = 6x difference by channel |
| **Wirehouse Wall** | Model loved large firms; SGAs correctly avoided them | AI optimized for wrong objective (stability vs. portability) |

#### The Strategic Pivot

| Aspect | V2 Approach | V3 Approach | Why |
|--------|-------------|-------------|-----|
| **Model Type** | XGBoost black box | Transparent SQL tiers | Explainability + SGA buy-in |
| **Feature Strategy** | 14 ML features | 4-5 business rules | Simpler = more robust |
| **Targeting** | Score all leads equally | Tier 1 (SGA Profile) + Tier 2 (Danger Zone) | Different profiles need different approaches |
| **Channel Strategy** | Single list for all | LinkedIn-first for Tier 1 | 6x better baseline conversion |
| **Volume Goal** | Maximize scored leads | Optimize for ~1,900 high-quality leads | Quality over quantity |

#### Key Insight: Human Intuition Beat the Algorithm

We compared model-selected leads vs. SGA-selected leads:

| Selection Method | Conversion Rate | Lift vs Baseline |
|------------------|-----------------|------------------|
| **Model (V2)** | 0.67% | 0.79x (worse than random) |
| **SGA Intuition** | 1.83% | 2.17x |
| **SGA Platinum Criteria** | 2.15% | 2.55x |

The SGAs were right: **small firms + mid-tenure + experienced + not wirehouse** beats any ML signal.

### V3 Model Summary

**Model Version:** `v3-hybrid-20251221`

| Tier | Criteria | Expected Lift | Volume/Batch |
|------|----------|---------------|--------------|
| 💎 **Platinum** | Small firm (≤10) + 4-10yr tenure + 8-30yr exp + Not Wirehouse | **2.55x** | ~1,600 |
| 🥇 **Gold** | Danger Zone (1-2yr) + Bleeding Firm + Veteran (10yr+) | **2.33x** | ~350 |
| 🥈 **Silver** | DZ + Not Wirehouse OR Perry tenure + Experienced | ~2.2x | ~3,600 |
| 🥉 **Bronze** | Danger Zone only | ~2.0x | ~740 |
| ⚪ **Standard** | No strong signals | 0.84% baseline | Rest |

**Combined Top 2 Tiers:** ~1,950 leads at ~2.5x expected lift

---
```

**Also update the document title to reflect V3:**

Change:
```markdown
# Savvy Wealth Lead Scoring Model: Agentic Development Plan

## XGBoost Model for Contacted → MQL Conversion
```

To:
```markdown
# Savvy Wealth Lead Scoring Model: Agentic Development Plan

## V3 Two-Tier Hybrid Model for Contacted → MQL Conversion

**Model Evolution:** V1 (Baseline) → V2 (XGBoost + Engineered Features) → **V3 (Transparent Tiered Query)**
```

---

# PROMPT 2: Add Signal Decay Investigation Documentation

**Instructions for Cursor:**

In `@leadscoring_plan.md`, add a new Phase -2 section before Phase -1. This documents the signal decay investigation that led to the V3 pivot. This is critical context for anyone maintaining the model.

**Add this new section:**

```markdown
---

## Phase -2: Signal Decay Investigation (V2 → V3 Pivot)

> **Purpose:** Document the investigation that revealed why V2 failed in production and how we arrived at the V3 strategy.
> 
> **Status:** ✅ COMPLETE (December 2025)
> 
> **Key Output:** Decision to pivot from XGBoost to Tiered Query

### Unit -2.1: Symptom Identification

**The Problem:**
- V2 model achieved 4.43x lift on 2024 test data
- V2 model achieved only 1.46x lift on Aug-Oct 2025 production data
- 68% lift degradation in <12 months

**Initial Hypotheses Tested:**

| # | Hypothesis | Status | Finding |
|---|------------|--------|---------|
| 1 | Model overfitting | ❌ Rejected | Temporal backtest showed 1.90x lift (model generalized) |
| 2 | Feature drift | ⚠️ Partial | DZ leads in 2025 had different profile (less experienced) |
| 3 | Lead source shift | ✅ Confirmed | Major shift from Provided Lists to LinkedIn |
| 4 | Pool depletion | ✅ Confirmed | Top firms 100% contacted in 2024 |
| 5 | Seasonality | ❌ Rejected | No seasonal pattern in conversion rates |
| 6 | Cream skimming | ❌ Rejected | DZ and non-DZ leads contacted at similar times |
| 7 | Time-to-close lag | ❌ Rejected | Median close time = 10 days, 90th percentile = 231 days |

### Unit -2.2: Root Cause Analysis

**Diagnostic Query (Run this to reproduce findings):**

```sql
-- Signal Decay Diagnostic: Lead Source Shift
WITH lead_data AS (
    SELECT 
        l.Id as lead_id,
        l.LeadSource,
        l.stage_entered_contacting__c as contacted_date,
        CASE WHEN l.MQL_Date__c IS NOT NULL THEN 1 ELSE 0 END as converted,
        EXTRACT(YEAR FROM l.stage_entered_contacting__c) as contact_year,
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.pit_moves_3yr,
        f.firm_net_change_12mo,
        CASE WHEN f.current_firm_tenure_months BETWEEN 12 AND 24 THEN 1 ELSE 0 END as in_danger_zone
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features` f
        ON l.Id = f.lead_id
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
)

SELECT 
    contact_year,
    LeadSource,
    COUNT(*) as total_leads,
    SUM(converted) as conversions,
    ROUND(AVG(converted) * 100, 2) as conv_rate_pct,
    -- DZ performance within this segment
    SUM(CASE WHEN in_danger_zone = 1 THEN converted ELSE 0 END) as dz_conversions,
    SUM(in_danger_zone) as dz_leads,
    ROUND(SAFE_DIVIDE(SUM(CASE WHEN in_danger_zone = 1 THEN converted ELSE 0 END), 
                       SUM(in_danger_zone)) * 100, 2) as dz_conv_rate_pct
FROM lead_data
GROUP BY 1, 2
ORDER BY 1, 3 DESC
```

**Key Findings:**

1. **Lead Source Shift:**
   | Source | 2024 Share | 2025 Share | Change |
   |--------|------------|------------|--------|
   | Provided Lead List | 85.7% | 64.9% | -21pp |
   | LinkedIn Self-Sourced | 13.3% | 33.3% | +20pp |

2. **DZ Signal Performance by Channel:**
   | Channel | 2024 DZ Lift | 2025 DZ Lift | Stability |
   |---------|--------------|--------------|-----------|
   | Provided Lists | 5.35x | 1.44x | ❌ Collapsed |
   | LinkedIn | 2.07x | 2.10x | ✅ Stable |

3. **Pool Quality Degradation:**
   | Metric | 2024 DZ Leads | 2025 DZ Leads | Change |
   |--------|---------------|---------------|--------|
   | Industry Tenure | 191 months | 76 months | -60% |
   | Prior Firms | 1.8 | 0.8 | -53% |
   | Firm Bleeding | -97 | -32 | 67% less bleeding |

4. **Top Firm Depletion:**
   | Firm | 2024 DZ Share | 2025 DZ Share |
   |------|---------------|---------------|
   | Mariner Wealth | 16.1% | 0.0% |
   | Corebridge | 15.0% | 0.0% |
   | Corient | 12.5% | 0.0% |
   | TIAA | 9.5% | 1.4% |

### Unit -2.3: SGA Intuition Analysis

**Discovery:** SGAs were outperforming the model by targeting different profiles.

**SGA Targeting Criteria (from interviews):**
1. Small firms (1-10 reps) - "owners with portable books"
2. Exclude wirehouses/banks (Perry's 20+ firm list)
3. 4-10 years at current firm - "Under 4 is too new; after 10, clients are loyal"
4. 8-30 years total experience
5. Prior wirehouse experience (moved from big firm to RIA)

**Validation Query:**

```sql
-- SGA Platinum Criteria Validation
WITH lead_features AS (
    SELECT 
        l.Id,
        CASE WHEN l.MQL_Date__c IS NOT NULL THEN 1 ELSE 0 END as converted,
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.firm_rep_count_at_contact,
        f.firm_net_change_12mo,
        -- SGA Platinum criteria
        CASE WHEN f.firm_rep_count_at_contact <= 10 THEN 1 ELSE 0 END as is_small_firm,
        CASE WHEN f.current_firm_tenure_months BETWEEN 48 AND 120 THEN 1 ELSE 0 END as in_sweet_spot,
        CASE WHEN f.industry_tenure_months BETWEEN 96 AND 360 THEN 1 ELSE 0 END as is_experienced,
        CASE WHEN UPPER(l.Company) NOT LIKE '%MERRILL%'
              AND UPPER(l.Company) NOT LIKE '%MORGAN STANLEY%'
              AND UPPER(l.Company) NOT LIKE '%UBS%'
              AND UPPER(l.Company) NOT LIKE '%WELLS FARGO%'
              AND UPPER(l.Company) NOT LIKE '%EDWARD JONES%'
              -- Add other wirehouses...
             THEN 1 ELSE 0 END as not_wirehouse
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features` f
        ON l.Id = f.lead_id
    WHERE l.stage_entered_contacting__c >= '2024-01-01'
)

SELECT 
    'SGA Platinum' as model,
    COUNT(*) as volume,
    SUM(converted) as conversions,
    ROUND(AVG(converted) * 100, 2) as conv_rate_pct,
    ROUND(AVG(converted) / 0.0084, 2) as lift  -- 0.84% baseline
FROM lead_features
WHERE is_small_firm = 1 
  AND in_sweet_spot = 1 
  AND is_experienced = 1 
  AND not_wirehouse = 1

UNION ALL

SELECT 
    'Baseline' as model,
    COUNT(*) as volume,
    SUM(converted) as conversions,
    ROUND(AVG(converted) * 100, 2) as conv_rate_pct,
    1.0 as lift
FROM lead_features
```

**Results:**
| Model | Volume | Conv Rate | Lift |
|-------|--------|-----------|------|
| SGA Platinum | 1,631 | 2.15% | **2.55x** |
| DZ + Bleeding + Veteran | 356 | 1.97% | 2.33x |
| Baseline | 33,901 | 0.84% | 1.0x |

### Unit -2.4: Decision Point

**Options Evaluated:**

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| A. Retrain V2 on 2025 data | Maintains ML approach | Pool depleted; signal still weak | ❌ Rejected |
| B. Add velocity features | Captures recency | Complex; limited lift recovery | ❌ Rejected |
| C. Pivot to tiered query | Transparent; uses SGA intuition; robust | Simpler; less "ML" | ✅ Selected |

**Final Decision:** Pivot to V3 Two-Tier Hybrid Model

**Rationale:**
1. SGA Platinum criteria outperforms any ML signal (2.55x vs 2.33x)
2. Tiered query is transparent and explainable to sales team
3. Different tiers can use different outreach strategies
4. LinkedIn-first for Tier 1 exploits 6x channel advantage
5. Simpler = more robust to future market shifts

### Validation Gate

| Gate ID | Check | Result | Notes |
|---------|-------|--------|-------|
| G-2.1.1 | Root cause identified | ✅ PASSED | Lead source shift + pool depletion |
| G-2.2.1 | Alternative validated | ✅ PASSED | SGA Platinum achieves 2.55x lift |
| G-2.3.1 | Decision documented | ✅ PASSED | Pivot to V3 Two-Tier approved |

---
```

---

# PROMPT 3: Replace Phase 4 (Model Training) with Tiered Query Logic

**Instructions for Cursor:**

In `@leadscoring_plan.md`, **completely replace Phase 4** (Model Training & Hyperparameter Tuning) with the new V3 Tiered Query approach. The old XGBoost training is no longer applicable.

**Replace the entire Phase 4 section with:**

```markdown
---

## Phase 4: V3 Tiered Query Construction

> **Purpose:** Build the transparent tiered query that replaces the XGBoost model.
> 
> **Key Change from V2:** No ML training. Instead, we codify validated business rules into SQL tiers.
> 
> **Dependencies:** Phase 1 (feature engineering table must exist)

### Why Tiered Query Instead of XGBoost

| Factor | XGBoost (V2) | Tiered Query (V3) |
|--------|--------------|-------------------|
| **Explainability** | "Score is 0.73 because..." (SHAP needed) | "This is Tier 1 because small firm + mid-tenure" |
| **SGA Buy-in** | Low (black box) | High (matches their intuition) |
| **Maintenance** | Retrain quarterly | Adjust thresholds as needed |
| **Robustness** | Sensitive to distribution shift | Rules-based; more stable |
| **Performance** | 2.33x lift (best V2 config) | 2.55x lift (Tier 1) |

### Unit 4.1: Tier Definitions

**Tier 1: SGA Platinum (The "Hunter" Profile)**

```python
# Tier 1 Logic - Validated 2.55x lift
TIER_1_PLATINUM = {
    'name': 'SGA Platinum',
    'criteria': {
        'firm_rep_count': '≤ 10',           # Small firm (portable book)
        'current_tenure_months': '48-120',   # 4-10 years (sweet spot)
        'industry_tenure_months': '96-360',  # 8-30 years (experienced)
        'is_wirehouse': False                # Not a captive advisor
    },
    'expected_lift': 2.55,
    'expected_conversion': 0.0215,  # 2.15%
    'volume_per_batch': 1600,
    'recommended_channel': 'LinkedIn',
    'talk_track': 'Independent advisor with portable book, established but not entrenched'
}
```

**Tier 2: Danger Zone (The "Farmer" Profile)**

```python
# Tier 2 Logic - Validated 2.33x lift  
TIER_2_DANGER_ZONE = {
    'name': 'Danger Zone',
    'criteria': {
        'current_tenure_months': '12-24',    # 1-2 years (new at firm)
        'firm_net_change_12mo': '< -5',      # Bleeding firm
        'industry_tenure_months': '≥ 120'    # Veteran (10+ years)
    },
    'expected_lift': 2.33,
    'expected_conversion': 0.0197,  # 1.97%
    'volume_per_batch': 350,
    'recommended_channel': 'Cold Call',
    'talk_track': 'Flight risk at unstable firm, likely evaluating options'
}
```

### Unit 4.2: Wirehouse Exclusion List

**Why Exclude Wirehouses:**
- "Golden Handcuffs" - deferred compensation locks advisors in
- Clients belong to the firm, not the advisor
- V2 model incorrectly favored these (stability ≠ portability)

```python
# Perry's Wirehouse Exclusion List (validated with SGA team)
WIREHOUSE_PATTERNS = [
    # Major Wirehouses
    '%MERRILL LYNCH%', '%MERRILL%',
    '%MORGAN STANLEY%',
    '%UBS%',
    '%WELLS FARGO%',
    '%EDWARD JONES%',
    '%RAYMOND JAMES%',
    '%LPL FINANCIAL%',
    
    # Insurance-Affiliated
    '%NORTHWESTERN MUTUAL%',
    '%MASS MUTUAL%', '%MASSMUTUAL%',
    '%NEW YORK LIFE%', '%NYLIFE%',
    '%PRUDENTIAL%',
    '%PRINCIPAL%',
    '%LINCOLN FINANCIAL%',
    '%TRANSAMERICA%',
    '%ALLSTATE%',
    '%STATE FARM%',
    '%FARM BUREAU%',
    
    # Banks
    '%BANK OF AMERICA%',
    '%JP MORGAN%', '%JPMORGAN%',
    '%CHASE%',
    '%CITIBANK%', '%CITI %',
    
    # Large RIAs (>1000 reps - still captive)
    '%AMERIPRISE%',
    '%FIDELITY%',
    '%SCHWAB%', '%CHARLES SCHWAB%',
    '%VANGUARD%',
    '%FISHER INVESTMENTS%',
    '%CREATIVE PLANNING%',
    '%EDELMAN%',
    '%FIRST COMMAND%',
    '%T. ROWE PRICE%'
]
```

### Unit 4.3: Production Scoring Query

**Complete V3 Scoring Query:**

```sql
-- =============================================================================
-- LEAD SCORING V3: TWO-TIER HYBRID MODEL
-- =============================================================================
-- Version: v3-hybrid-20251221
-- Expected Lift: Tier 1 = 2.55x, Tier 2 = 2.33x
-- =============================================================================

WITH 
-- Wirehouse exclusion patterns
excluded_firms AS (
    SELECT pattern FROM UNNEST([
        '%MERRILL%', '%MORGAN STANLEY%', '%UBS%', '%WELLS FARGO%',
        '%EDWARD JONES%', '%RAYMOND JAMES%', '%LPL FINANCIAL%',
        '%NORTHWESTERN MUTUAL%', '%MASS MUTUAL%', '%MASSMUTUAL%',
        '%NEW YORK LIFE%', '%NYLIFE%', '%PRUDENTIAL%', '%PRINCIPAL%',
        '%LINCOLN FINANCIAL%', '%TRANSAMERICA%', '%ALLSTATE%',
        '%STATE FARM%', '%FARM BUREAU%', '%BANK OF AMERICA%',
        '%JP MORGAN%', '%JPMORGAN%', '%AMERIPRISE%', '%FIDELITY%',
        '%SCHWAB%', '%CHARLES SCHWAB%', '%VANGUARD%',
        '%FISHER INVESTMENTS%', '%CREATIVE PLANNING%', '%EDELMAN%',
        '%FIRST COMMAND%', '%T. ROWE PRICE%'
    ]) AS pattern
),

-- Base lead data with features
lead_features AS (
    SELECT 
        l.Id as lead_id,
        l.FirstName, l.LastName, l.Email, l.Phone,
        l.Company, l.Title, l.Status, l.LeadSource,
        l.FA_CRD__c as advisor_crd,
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.firm_rep_count_at_contact,
        f.firm_net_change_12mo,
        f.pit_moves_3yr,
        
        -- Derived flags
        CASE WHEN f.current_firm_tenure_months BETWEEN 12 AND 24 THEN 1 ELSE 0 END as in_danger_zone,
        CASE WHEN f.current_firm_tenure_months BETWEEN 48 AND 120 THEN 1 ELSE 0 END as in_sweet_spot,
        CASE WHEN f.industry_tenure_months BETWEEN 96 AND 360 THEN 1 ELSE 0 END as is_experienced,
        CASE WHEN f.industry_tenure_months >= 120 THEN 1 ELSE 0 END as is_veteran,
        CASE WHEN f.firm_rep_count_at_contact <= 10 THEN 1 ELSE 0 END as is_small_firm,
        CASE WHEN f.firm_net_change_12mo < -5 THEN 1 ELSE 0 END as at_bleeding_firm,
        UPPER(l.Company) as company_upper
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features` f
        ON l.Id = f.lead_id
    WHERE l.Status NOT IN ('Converted', 'Disqualified', 'Dead', 'Unqualified')
        AND f.lead_id IS NOT NULL
),

-- Add wirehouse flag
leads_with_flags AS (
    SELECT 
        lf.*,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM excluded_firms ef 
                WHERE lf.company_upper LIKE ef.pattern
            ) THEN 1 ELSE 0 
        END as is_wirehouse
    FROM lead_features lf
),

-- Assign tiers
tiered_leads AS (
    SELECT 
        *,
        CASE 
            -- 💎 TIER 1: SGA PLATINUM (2.55x lift)
            WHEN is_small_firm = 1 
                 AND in_sweet_spot = 1 
                 AND is_experienced = 1 
                 AND is_wirehouse = 0
            THEN '1_PLATINUM'
            
            -- 🥇 TIER 2: DANGER ZONE (2.33x lift)
            WHEN in_danger_zone = 1 
                 AND at_bleeding_firm = 1 
                 AND is_veteran = 1
            THEN '2_DANGER_ZONE'
            
            -- 🥈 TIER 3: SILVER
            WHEN in_danger_zone = 1 AND is_wirehouse = 0
            THEN '3_SILVER'
            
            -- 🥉 TIER 4: BRONZE  
            WHEN in_danger_zone = 1
            THEN '4_BRONZE'
            
            -- ⚪ TIER 5: STANDARD
            ELSE '5_STANDARD'
        END as score_tier,
        
        -- Numeric score for ranking within tiers
        (CASE 
            WHEN is_small_firm = 1 AND in_sweet_spot = 1 AND is_experienced = 1 AND is_wirehouse = 0 THEN 80
            WHEN in_danger_zone = 1 AND at_bleeding_firm = 1 AND is_veteran = 1 THEN 75
            WHEN in_danger_zone = 1 AND is_wirehouse = 0 THEN 60
            WHEN in_danger_zone = 1 THEN 50
            ELSE 20
        END
        + CASE WHEN at_bleeding_firm = 1 THEN 10 ELSE 0 END
        + CASE WHEN is_veteran = 1 THEN 5 ELSE 0 END
        + CASE WHEN pit_moves_3yr >= 2 THEN 5 ELSE 0 END
        ) as lead_score
    FROM leads_with_flags
)

-- Final output
SELECT 
    lead_id, advisor_crd,
    FirstName, LastName, Email, Phone, Company, Title,
    score_tier,
    lead_score,
    
    CASE score_tier
        WHEN '1_PLATINUM' THEN '💎 Platinum (SGA Profile)'
        WHEN '2_DANGER_ZONE' THEN '🥇 Gold (Danger Zone)'
        WHEN '3_SILVER' THEN '🥈 Silver'
        WHEN '4_BRONZE' THEN '🥉 Bronze'
        ELSE '⚪ Standard'
    END as tier_display,
    
    CASE score_tier
        WHEN '1_PLATINUM' THEN 'LinkedIn Hunt: Independent with portable book'
        WHEN '2_DANGER_ZONE' THEN 'Call: Flight risk at bleeding firm'
        WHEN '3_SILVER' THEN 'Standard outreach'
        WHEN '4_BRONZE' THEN 'Low priority'
        ELSE 'Deprioritize'
    END as action_recommended,
    
    -- Ranking
    ROW_NUMBER() OVER (ORDER BY score_tier, lead_score DESC) as global_rank,
    
    -- Metadata
    CURRENT_TIMESTAMP() as scored_at,
    'v3-hybrid-20251221' as model_version

FROM tiered_leads
ORDER BY score_tier, lead_score DESC
```

### Unit 4.4: Python Scoring Class

```python
"""
V3 Lead Scorer: Two-Tier Hybrid Model
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd

@dataclass
class TierResult:
    tier: str
    tier_display: str
    score: int
    expected_lift: float
    expected_conversion: float
    action: str
    signals: List[str]

class LeadScorerV3:
    """
    V3 Two-Tier Hybrid Lead Scorer
    
    Replaces XGBoost with transparent business rules validated
    against actual conversion data.
    """
    
    # Wirehouse patterns (leads at these firms are deprioritized)
    WIREHOUSE_PATTERNS = [
        'MERRILL', 'MORGAN STANLEY', 'UBS', 'WELLS FARGO',
        'EDWARD JONES', 'RAYMOND JAMES', 'LPL FINANCIAL',
        'NORTHWESTERN MUTUAL', 'MASS MUTUAL', 'MASSMUTUAL',
        'PRUDENTIAL', 'AMERIPRISE', 'FIDELITY', 'SCHWAB',
        'VANGUARD', 'FISHER INVESTMENTS', 'CREATIVE PLANNING'
    ]
    
    # Tier definitions with validated metrics
    TIERS = {
        '1_PLATINUM': {
            'display': '💎 Platinum',
            'lift': 2.55,
            'conversion': 0.0215,
            'action': 'LinkedIn Hunt: Independent advisor with portable book'
        },
        '2_DANGER_ZONE': {
            'display': '🥇 Gold',
            'lift': 2.33,
            'conversion': 0.0197,
            'action': 'Call: Flight risk at bleeding firm'
        },
        '3_SILVER': {
            'display': '🥈 Silver',
            'lift': 2.20,
            'conversion': 0.0185,
            'action': 'Standard outreach'
        },
        '4_BRONZE': {
            'display': '🥉 Bronze',
            'lift': 2.00,
            'conversion': 0.0168,
            'action': 'Low priority'
        },
        '5_STANDARD': {
            'display': '⚪ Standard',
            'lift': 1.00,
            'conversion': 0.0084,
            'action': 'Deprioritize'
        }
    }
    
    def __init__(self):
        self.model_version = 'v3-hybrid-20251221'
    
    def is_wirehouse(self, company: str) -> bool:
        """Check if company matches wirehouse patterns."""
        if not company:
            return False
        company_upper = company.upper()
        return any(pattern in company_upper for pattern in self.WIREHOUSE_PATTERNS)
    
    def score_lead(self, features: Dict) -> TierResult:
        """
        Score a single lead using tiered business rules.
        
        Args:
            features: Dict with keys:
                - current_firm_tenure_months
                - industry_tenure_months
                - firm_rep_count_at_contact
                - firm_net_change_12mo
                - pit_moves_3yr
                - company (firm name)
        
        Returns:
            TierResult with tier assignment and metadata
        """
        # Extract features
        tenure = features.get('current_firm_tenure_months', 0) or 0
        industry = features.get('industry_tenure_months', 0) or 0
        rep_count = features.get('firm_rep_count_at_contact', 100) or 100
        net_change = features.get('firm_net_change_12mo', 0) or 0
        moves_3yr = features.get('pit_moves_3yr', 0) or 0
        company = features.get('company', '')
        
        # Derived flags
        is_wirehouse = self.is_wirehouse(company)
        in_danger_zone = 12 <= tenure <= 24
        in_sweet_spot = 48 <= tenure <= 120
        is_experienced = 96 <= industry <= 360
        is_veteran = industry >= 120
        is_small_firm = rep_count <= 10
        at_bleeding_firm = net_change < -5
        
        # Collect signals
        signals = []
        
        # Tier assignment
        if is_small_firm and in_sweet_spot and is_experienced and not is_wirehouse:
            tier = '1_PLATINUM'
            score = 80
            signals = [
                f'Small firm ({rep_count} reps)',
                f'Sweet spot tenure ({tenure/12:.1f} yrs)',
                f'Experienced ({industry/12:.0f} yrs in industry)',
                'Not wirehouse'
            ]
        elif in_danger_zone and at_bleeding_firm and is_veteran:
            tier = '2_DANGER_ZONE'
            score = 75
            signals = [
                f'Danger zone ({tenure/12:.1f} yrs at firm)',
                f'Bleeding firm ({net_change:+d} advisors)',
                f'Veteran ({industry/12:.0f} yrs exp)'
            ]
        elif in_danger_zone and not is_wirehouse:
            tier = '3_SILVER'
            score = 60
            signals = [f'Danger zone ({tenure/12:.1f} yrs)', 'Not wirehouse']
        elif in_danger_zone:
            tier = '4_BRONZE'
            score = 50
            signals = [f'Danger zone ({tenure/12:.1f} yrs)']
        else:
            tier = '5_STANDARD'
            score = 20
            signals = ['No strong signals']
        
        # Bonus points
        if at_bleeding_firm and tier != '5_STANDARD':
            score += 10
        if is_veteran and tier != '5_STANDARD':
            score += 5
        if moves_3yr >= 2:
            score += 5
            signals.append(f'Mobile ({moves_3yr} moves in 3yr)')
        
        tier_config = self.TIERS[tier]
        
        return TierResult(
            tier=tier,
            tier_display=tier_config['display'],
            score=score,
            expected_lift=tier_config['lift'],
            expected_conversion=tier_config['conversion'],
            action=tier_config['action'],
            signals=signals
        )
    
    def score_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score a batch of leads."""
        results = []
        for _, row in df.iterrows():
            result = self.score_lead(row.to_dict())
            results.append({
                'tier': result.tier,
                'tier_display': result.tier_display,
                'lead_score': result.score,
                'expected_lift': result.expected_lift,
                'action': result.action,
                'signals': '; '.join(result.signals)
            })
        return pd.concat([df, pd.DataFrame(results)], axis=1)
```

### Validation Gates

| Gate ID | Check | Pass Criteria | Status |
|---------|-------|---------------|--------|
| G4.1.1 | Tier 1 criteria validated | Lift ≥ 2.5x on historical data | ✅ |
| G4.1.2 | Tier 2 criteria validated | Lift ≥ 2.0x on historical data | ✅ |
| G4.2.1 | Wirehouse list complete | Covers major brokerages | ✅ |
| G4.3.1 | Query executes | No syntax errors in BigQuery | ⏳ |
| G4.4.1 | Python scorer matches SQL | Same tier assignments | ⏳ |

---
```

---

# PROMPT 4: Update Phase 5 (Evaluation) for Tiered Model

**Instructions for Cursor:**

In `@leadscoring_plan.md`, update Phase 5 to evaluate the tiered query instead of XGBoost metrics. We're measuring tier performance, not AUC-ROC.

**Replace the Phase 5 content with:**

```markdown
---

## Phase 5: V3 Tier Validation & Performance Analysis

> **Purpose:** Validate that the tiered query achieves expected lift on historical data.
> 
> **Key Change from V2:** We measure **tier-level conversion rates**, not model-level AUC.

### Why Different Metrics

| V2 (XGBoost) | V3 (Tiered Query) |
|--------------|-------------------|
| AUC-ROC | ❌ Not applicable (no probabilities) |
| AUC-PR | ❌ Not applicable |
| **Top Decile Lift** | ✅ Still relevant (Tier 1 = top decile) |
| SHAP Values | ❌ Not needed (rules are transparent) |
| **Tier Conversion Rates** | ✅ Primary metric |
| **Lift by Tier** | ✅ Primary metric |
| **Volume by Tier** | ✅ Operational metric |

### Unit 5.1: Historical Tier Performance Validation

**Validation Query:**

```sql
-- V3 Tier Performance Validation
-- Run this on historical data to validate expected lift

WITH historical_leads AS (
    SELECT 
        l.Id as lead_id,
        CASE WHEN l.MQL_Date__c IS NOT NULL THEN 1 ELSE 0 END as converted,
        l.stage_entered_contacting__c as contacted_date,
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.firm_rep_count_at_contact,
        f.firm_net_change_12mo,
        UPPER(l.Company) as company_upper
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features` f
        ON l.Id = f.lead_id
    WHERE l.stage_entered_contacting__c >= '2024-01-01'
        AND l.stage_entered_contacting__c < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        AND f.lead_id IS NOT NULL
),

tiered_historical AS (
    SELECT 
        *,
        -- Tier assignment (must match production query exactly)
        CASE 
            WHEN firm_rep_count_at_contact <= 10 
                 AND current_firm_tenure_months BETWEEN 48 AND 120
                 AND industry_tenure_months BETWEEN 96 AND 360
                 AND NOT (company_upper LIKE '%MERRILL%' OR company_upper LIKE '%MORGAN STANLEY%'
                         OR company_upper LIKE '%UBS%' OR company_upper LIKE '%WELLS FARGO%'
                         -- ... other wirehouse patterns
                         )
            THEN '1_PLATINUM'
            WHEN current_firm_tenure_months BETWEEN 12 AND 24
                 AND firm_net_change_12mo < -5
                 AND industry_tenure_months >= 120
            THEN '2_DANGER_ZONE'
            WHEN current_firm_tenure_months BETWEEN 12 AND 24
            THEN '3_SILVER_BRONZE'
            ELSE '4_STANDARD'
        END as score_tier
    FROM historical_leads
)

SELECT 
    score_tier,
    COUNT(*) as volume,
    SUM(converted) as conversions,
    ROUND(AVG(converted) * 100, 3) as conversion_rate_pct,
    ROUND(AVG(converted) / 0.0084, 2) as lift_vs_baseline,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM tiered_historical), 2) as lift_vs_pool
FROM tiered_historical
GROUP BY 1
ORDER BY 1
```

**Expected Results:**

| Tier | Volume | Conv Rate | Lift | Status |
|------|--------|-----------|------|--------|
| 1_PLATINUM | ~1,600 | 2.15% | 2.55x | ✅ Target |
| 2_DANGER_ZONE | ~350 | 1.97% | 2.33x | ✅ Target |
| 3_SILVER_BRONZE | ~4,300 | 1.5-1.8% | 1.8-2.1x | ✅ Acceptable |
| 4_STANDARD | ~27,000 | 0.84% | 1.0x | Expected |

### Unit 5.2: Channel-Specific Performance

**Why This Matters:** Same tier performs differently by channel. Tier 1 especially benefits from LinkedIn.

```sql
-- Tier Performance by Channel
SELECT 
    score_tier,
    LeadSource,
    COUNT(*) as volume,
    SUM(converted) as conversions,
    ROUND(AVG(converted) * 100, 2) as conv_rate_pct,
    ROUND(AVG(converted) / 0.0084, 2) as lift
FROM tiered_historical th
JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l ON th.lead_id = l.Id
GROUP BY 1, 2
HAVING COUNT(*) >= 50  -- Minimum sample size
ORDER BY 1, 4 DESC
```

**Expected Pattern:**
- Tier 1 + LinkedIn → 4-5% conversion (highest)
- Tier 1 + Provided List → 2-3% conversion
- Tier 2 + LinkedIn → 3-4% conversion
- Tier 2 + Provided List → 1.5-2% conversion

### Unit 5.3: Temporal Stability Check

**Purpose:** Confirm tiers perform consistently across time periods.

```sql
-- Tier Performance by Quarter
SELECT 
    score_tier,
    DATE_TRUNC(contacted_date, QUARTER) as quarter,
    COUNT(*) as volume,
    ROUND(AVG(converted) * 100, 2) as conv_rate_pct,
    ROUND(AVG(converted) / 0.0084, 2) as lift
FROM tiered_historical
GROUP BY 1, 2
ORDER BY 1, 2
```

**Alert Condition:** If any tier's lift drops below 1.5x for 2 consecutive quarters, investigate.

### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G5.1.1 | Tier 1 Lift | ≥ 2.4x | ⏳ |
| G5.1.2 | Tier 2 Lift | ≥ 2.0x | ⏳ |
| G5.1.3 | Combined Top 2 Volume | ≥ 1,500 leads | ⏳ |
| G5.2.1 | LinkedIn Tier 1 Lift | ≥ 3.0x | ⏳ |
| G5.3.1 | Temporal Variance | < 0.5x between quarters | ⏳ |

---
```

---

# PROMPT 5: Update Phase 6 (Calibration) - Simplify for Tiered Model

**Instructions for Cursor:**

In `@leadscoring_plan.md`, update Phase 6. Since we're using tiers instead of probabilities, calibration is simpler - we just validate that expected conversion rates match reality.

**Replace Phase 6 content with:**

```markdown
---

## Phase 6: Tier Calibration & Production Packaging

> **Purpose:** Validate expected conversion rates and package for production.
> 
> **Key Change from V2:** No probability calibration needed. Instead, we calibrate expected conversion rates per tier.

### Why Tier Calibration is Simpler

| V2 (XGBoost) | V3 (Tiered) |
|--------------|-------------|
| Isotonic regression on probabilities | Empirical conversion rates per tier |
| Lookup table with 100 bins | 5 fixed tiers with expected rates |
| Recalibrate on distribution shift | Update rates quarterly |

### Unit 6.1: Tier Calibration Table

**Calculate actual conversion rates per tier:**

```python
"""
Tier Calibration: Calculate and store expected conversion rates.
"""

import pandas as pd
from google.cloud import bigquery

def calibrate_tiers(client: bigquery.Client) -> pd.DataFrame:
    """
    Calculate actual conversion rates per tier from historical data.
    These become the 'expected_conversion' values in production.
    """
    
    query = """
    WITH tiered_leads AS (
        -- (Same tier assignment query as Phase 4)
        ...
    )
    
    SELECT 
        score_tier,
        COUNT(*) as volume,
        SUM(converted) as conversions,
        AVG(converted) as conversion_rate,
        STDDEV(converted) / SQRT(COUNT(*)) as conversion_se,  -- Standard error
        AVG(converted) / 0.0084 as lift  -- vs 0.84% baseline
    FROM tiered_leads
    GROUP BY 1
    ORDER BY 1
    """
    
    calibration_df = client.query(query).to_dataframe()
    
    # Add confidence intervals
    calibration_df['conv_lower_95'] = calibration_df['conversion_rate'] - 1.96 * calibration_df['conversion_se']
    calibration_df['conv_upper_95'] = calibration_df['conversion_rate'] + 1.96 * calibration_df['conversion_se']
    
    return calibration_df


# Expected output:
# | Tier | Volume | Conv Rate | 95% CI | Lift |
# |------|--------|-----------|--------|------|
# | 1_PLATINUM | 1,631 | 2.15% | [1.4%, 2.9%] | 2.55x |
# | 2_DANGER_ZONE | 356 | 1.97% | [0.9%, 3.0%] | 2.33x |
# | 3_SILVER | 3,600 | 1.60% | [1.2%, 2.0%] | 1.90x |
# | 4_BRONZE | 740 | 1.50% | [0.9%, 2.1%] | 1.79x |
# | 5_STANDARD | 27,000 | 0.84% | [0.7%, 1.0%] | 1.00x |
```

### Unit 6.2: Production Artifacts

**Model Registry Entry:**

```json
{
    "version_id": "v3-hybrid-20251221",
    "model_type": "tiered_query",
    "status": "production",
    "created_date": "2025-12-21",
    "performance": {
        "tier_1_lift": 2.55,
        "tier_2_lift": 2.33,
        "combined_volume": 1987,
        "baseline_conversion": 0.0084
    },
    "calibration": {
        "method": "empirical",
        "last_calibrated": "2025-12-21",
        "tiers": {
            "1_PLATINUM": {"expected_conv": 0.0215, "volume": 1631},
            "2_DANGER_ZONE": {"expected_conv": 0.0197, "volume": 356},
            "3_SILVER": {"expected_conv": 0.0160, "volume": 3600},
            "4_BRONZE": {"expected_conv": 0.0150, "volume": 740},
            "5_STANDARD": {"expected_conv": 0.0084, "volume": 27000}
        }
    },
    "artifacts": {
        "sql_query": "sql/lead_scoring_v3.sql",
        "python_scorer": "inference/lead_scorer_v3.py",
        "calibration_table": "models/v3-hybrid-20251221/tier_calibration.json"
    }
}
```

### Unit 6.3: Calibration Monitoring

**Quarterly Recalibration Query:**

```sql
-- Run quarterly to check if tier conversion rates are drifting
WITH recent_tiers AS (
    -- Score recent leads (last 90 days, matured 30+ days)
    SELECT score_tier, converted
    FROM scored_leads_v3
    WHERE contacted_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
                             AND DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
)

SELECT 
    score_tier,
    COUNT(*) as volume,
    ROUND(AVG(converted) * 100, 2) as actual_conv_pct,
    -- Compare to expected (from calibration table)
    CASE score_tier
        WHEN '1_PLATINUM' THEN 2.15
        WHEN '2_DANGER_ZONE' THEN 1.97
        WHEN '3_SILVER' THEN 1.60
        WHEN '4_BRONZE' THEN 1.50
        ELSE 0.84
    END as expected_conv_pct,
    ABS(AVG(converted) * 100 - CASE score_tier WHEN '1_PLATINUM' THEN 2.15 ... END) as drift_pct
FROM recent_tiers
GROUP BY 1
ORDER BY 1
```

**Alert Thresholds:**
- **Warning:** Drift > 0.5% from expected
- **Critical:** Drift > 1.0% from expected OR Tier 1 lift < 2.0x

### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G6.1.1 | Tier 1 CI includes 2.15% | Yes | ⏳ |
| G6.1.2 | Tier 2 CI includes 1.97% | Yes | ⏳ |
| G6.2.1 | Registry entry valid | JSON schema passes | ⏳ |
| G6.3.1 | No current drift | All tiers within 0.5% | ⏳ |

---
```

---

# PROMPT 6: Add New Phase on Channel Strategy

**Instructions for Cursor:**

In `@leadscoring_plan.md`, add a NEW Phase 4.5 between Phase 4 and Phase 5. This phase documents the channel-specific strategy that emerged from our investigation.

**Add this new section:**

```markdown
---

## Phase 4.5: Channel Strategy Configuration

> **Purpose:** Configure different outreach strategies per tier based on channel performance data.
> 
> **Key Insight:** The same tier converts at wildly different rates depending on the outreach channel. LinkedIn converts 6x better than cold call lists.

### Why Channel Matters

**Discovery from V2→V3 Investigation:**

| Channel | Baseline Conv | Tier 1 Conv | Tier 2 Conv |
|---------|---------------|-------------|-------------|
| **LinkedIn Self-Sourced** | 1.83% | 4.5% | 3.7% |
| **Provided List (Cold)** | 0.67% | 2.0% | 1.5% |
| **Ratio** | **2.7x** | **2.3x** | **2.5x** |

**Implication:** Tier 1 leads are worth 2x more effort to find on LinkedIn vs. cold calling.

### Unit 4.5.1: Channel Recommendations by Tier

```python
# Channel Strategy Configuration
CHANNEL_STRATEGY = {
    '1_PLATINUM': {
        'primary_channel': 'LinkedIn',
        'secondary_channel': 'Warm Introduction',
        'cold_call': False,
        'expected_conv_linkedin': 0.045,  # 4.5%
        'expected_conv_cold': 0.020,      # 2.0%
        'rationale': 'LinkedIn allows targeting by firm size/role. 2.3x better than cold.'
    },
    '2_DANGER_ZONE': {
        'primary_channel': 'Cold Call',
        'secondary_channel': 'LinkedIn',
        'cold_call': True,
        'expected_conv_linkedin': 0.037,  # 3.7%
        'expected_conv_cold': 0.015,      # 1.5%
        'rationale': 'Time-sensitive signal; immediate outreach preferred.'
    },
    '3_SILVER': {
        'primary_channel': 'Cold Call',
        'secondary_channel': None,
        'cold_call': True,
        'expected_conv_cold': 0.012,
        'rationale': 'Standard outreach; not worth LinkedIn effort.'
    },
    '4_BRONZE': {
        'primary_channel': 'Email Only',
        'secondary_channel': None,
        'cold_call': False,
        'expected_conv_cold': 0.010,
        'rationale': 'Low priority; minimize SGA time.'
    },
    '5_STANDARD': {
        'primary_channel': 'Skip',
        'secondary_channel': None,
        'cold_call': False,
        'expected_conv_cold': 0.008,
        'rationale': 'Not worth outreach; essentially random.'
    }
}
```

### Unit 4.5.2: LinkedIn Hunt Playbook (Tier 1)

**Who to Target:**
- Small firm (≤10 advisors) - "Independent RIA"
- 4-10 years at current firm
- 8-30 years total experience
- Title contains: "Founder", "Partner", "Principal", "Owner"
- NOT at wirehouse/bank

**LinkedIn Search Filters:**
```
Title: "Financial Advisor" OR "Wealth Advisor" OR "Financial Planner"
Company Size: 1-10 employees
Industry: Financial Services
Experience: 8-30 years total
Current Company Tenure: 4-10 years
```

**Outreach Template (Tier 1):**
```
Subject: Fellow independent advisor

Hi [First Name],

I noticed you've built a practice at [Company] over the past [X] years - 
that's impressive staying power in an industry where most advisors 
change firms every 2-3 years.

I'm reaching out because Savvy is working with independent advisors 
who value control over their practice but want better technology 
and support infrastructure.

Would you be open to a brief call to share what we're seeing 
work for advisors like yourself?

Best,
[SGA Name]
```

### Unit 4.5.3: Cold Call Playbook (Tier 2)

**Talk Track (Tier 2 - Flight Risk):**
```
"Hi [First Name], this is [SGA] from Savvy Wealth.

I know this is a cold call, but I wanted to reach out because 
I noticed you joined [Current Firm] about [X] months ago - 
and I've seen several advisors leave there recently.

Without knowing your situation, I just wanted to make sure 
you're aware of the options available if things aren't working out.

Do you have 5 minutes to hear what we're offering advisors 
who are re-evaluating their fit?"
```

### Unit 4.5.4: Weekly List Generation

**Recommended Weekly Volumes:**

| Tier | LinkedIn List | Cold Call List | Total |
|------|---------------|----------------|-------|
| 💎 Tier 1 | 50 | 0 | 50 |
| 🥇 Tier 2 | 0 | 100 | 100 |
| 🥈 Tier 3 | 0 | 100 | 100 |
| **Total** | 50 | 200 | **250** |

**SQL to Generate Weekly Lists:**

```sql
-- Weekly LinkedIn Hunt List (Tier 1 only)
SELECT 
    advisor_crd,
    FirstName, LastName,
    Company,
    Email,
    current_firm_tenure_months / 12.0 as years_at_firm,
    industry_tenure_months / 12.0 as years_experience,
    firm_rep_count_at_contact as firm_size,
    'LinkedIn' as assigned_channel,
    'Small firm independent, sweet spot tenure' as targeting_notes
FROM scored_leads_v3
WHERE score_tier = '1_PLATINUM'
    AND scored_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY lead_score DESC
LIMIT 50;

-- Weekly Cold Call List (Tier 2 + 3)
SELECT 
    advisor_crd,
    FirstName, LastName,
    Company,
    Phone,
    current_firm_tenure_months / 12.0 as years_at_firm,
    firm_net_change_12mo as advisors_leaving,
    'Cold Call' as assigned_channel,
    CASE score_tier 
        WHEN '2_DANGER_ZONE' THEN 'Flight risk at bleeding firm - urgent'
        ELSE 'Standard DZ outreach'
    END as targeting_notes
FROM scored_leads_v3
WHERE score_tier IN ('2_DANGER_ZONE', '3_SILVER')
    AND scored_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY score_tier, lead_score DESC
LIMIT 200;
```

### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G4.5.1 | LinkedIn list generated | 50 Tier 1 leads/week | ⏳ |
| G4.5.2 | Cold call list generated | 200 Tier 2-3 leads/week | ⏳ |
| G4.5.3 | No Tier 1 in cold call list | 0 overlap | ⏳ |
| G4.5.4 | Playbooks documented | Sales team trained | ⏳ |

---
```

---

# PROMPT 7: Update Phase 7 (Deployment) for V3

**Instructions for Cursor:**

In `@leadscoring_plan.md`, update Phase 7 to reflect V3 deployment. Key changes:
- No XGBoost model deployment
- Simple SQL query scheduling
- Different output structure (tiers instead of scores)

**Replace relevant parts of Phase 7 with:**

```markdown
---

## Phase 7: V3 Production Deployment

> **Purpose:** Deploy the tiered query to production and integrate with Salesforce.
> 
> **Key Change from V2:** No model binary to deploy. Just schedule the SQL query.

### Unit 7.1: BigQuery Scheduled Query

**Create Scheduled Query:**

```sql
-- Create or replace the scoring view
CREATE OR REPLACE VIEW `savvy-gtm-analytics.ml_features.lead_scores_v3_current` AS

-- (Full V3 scoring query from Phase 4.3)
WITH excluded_firms AS (...),
     lead_features AS (...),
     ...
SELECT * FROM tiered_leads
ORDER BY score_tier, lead_score DESC;
```

**Schedule Configuration:**
- **Frequency:** Daily at 6:00 AM EST
- **Destination:** `ml_features.lead_scores_v3_daily` (partitioned by score_date)
- **Notification:** Email on failure

```python
# Schedule creation using BigQuery API
from google.cloud import bigquery_datatransfer

def create_scheduled_query(project_id: str = 'savvy-gtm-analytics'):
    client = bigquery_datatransfer.DataTransferServiceClient()
    
    parent = f"projects/{project_id}/locations/northamerica-northeast2"
    
    transfer_config = {
        "display_name": "Lead Scoring V3 Daily",
        "data_source_id": "scheduled_query",
        "params": {
            "query": open('sql/lead_scoring_v3.sql').read(),
            "destination_table_name_template": "ml_features.lead_scores_v3_{run_date}",
            "write_disposition": "WRITE_TRUNCATE"
        },
        "schedule": "every day 06:00",
        "notification_pubsub_topic": f"projects/{project_id}/topics/scoring-alerts"
    }
    
    response = client.create_transfer_config(parent=parent, transfer_config=transfer_config)
    print(f"Created scheduled query: {response.name}")
```

### Unit 7.2: Salesforce Integration

**Field Mappings (Updated for V3):**

| Salesforce Field | V3 Source | Description |
|------------------|-----------|-------------|
| `Lead_Score_Tier__c` | score_tier | 1_PLATINUM, 2_DANGER_ZONE, etc. |
| `Lead_Tier_Display__c` | tier_display | 💎 Platinum, 🥇 Gold, etc. |
| `Lead_Score__c` | lead_score | Numeric score (0-100) |
| `Lead_Action__c` | action_recommended | Channel-specific action |
| `Lead_Signals__c` | signals | List of why this tier |
| `Lead_Expected_Conv__c` | expected_conversion | Calibrated rate |
| `Lead_Model_Version__c` | model_version | v3-hybrid-20251221 |

**Sync Query:**

```sql
-- Generate Salesforce update payloads
SELECT 
    lead_id as Id,
    score_tier as Lead_Score_Tier__c,
    tier_display as Lead_Tier_Display__c,
    lead_score as Lead_Score__c,
    action_recommended as Lead_Action__c,
    CASE score_tier
        WHEN '1_PLATINUM' THEN 0.0215
        WHEN '2_DANGER_ZONE' THEN 0.0197
        WHEN '3_SILVER' THEN 0.016
        WHEN '4_BRONZE' THEN 0.015
        ELSE 0.0084
    END as Lead_Expected_Conv__c,
    'v3-hybrid-20251221' as Lead_Model_Version__c,
    CURRENT_TIMESTAMP() as Lead_Score_Timestamp__c
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_current`
WHERE score_tier IN ('1_PLATINUM', '2_DANGER_ZONE', '3_SILVER')  -- Only sync priority tiers
```

### Unit 7.3: SGA Dashboard Integration

**Looker/Data Studio View:**

```sql
-- Dashboard view with SGA-friendly columns
CREATE OR REPLACE VIEW `savvy-gtm-analytics.ml_features.sga_priority_list` AS

SELECT 
    -- Identity
    FirstName || ' ' || LastName as advisor_name,
    Company as firm_name,
    advisor_crd,
    Email, Phone,
    
    -- Scoring
    tier_display as priority_tier,
    action_recommended as next_action,
    
    -- Context for talk track
    CONCAT(
        CASE WHEN is_small_firm = 1 THEN 'Small firm (' || firm_rep_count || ' advisors). ' ELSE '' END,
        CASE WHEN in_sweet_spot = 1 THEN 'At firm ' || ROUND(tenure_months/12, 1) || ' years. ' ELSE '' END,
        CASE WHEN at_bleeding_firm = 1 THEN 'Firm lost ' || ABS(firm_net_change_12mo) || ' advisors this year. ' ELSE '' END,
        CASE WHEN is_veteran = 1 THEN ROUND(industry_months/12, 0) || ' years in industry.' ELSE '' END
    ) as context_notes,
    
    -- Ranking
    global_rank,
    
    -- Metadata
    scored_at,
    model_version

FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_current`
WHERE score_tier IN ('1_PLATINUM', '2_DANGER_ZONE')  -- Top 2 tiers only
ORDER BY global_rank
LIMIT 500;  -- Weekly list cap
```

### Unit 7.4: Weekly Report Generation

```python
"""
Weekly V3 Scoring Report
"""

def generate_weekly_report(client: bigquery.Client) -> str:
    """Generate weekly summary for sales leadership."""
    
    query = """
    SELECT 
        score_tier,
        COUNT(*) as new_leads,
        ROUND(AVG(lead_score), 1) as avg_score
    FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_current`
    WHERE scored_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    GROUP BY 1
    ORDER BY 1
    """
    
    df = client.query(query).to_dataframe()
    
    report = f"""
# Weekly Lead Scoring Report (V3)

**Week of:** {datetime.now().strftime('%Y-%m-%d')}
**Model Version:** v3-hybrid-20251221

## Tier Distribution (New This Week)

| Tier | New Leads | Avg Score |
|------|-----------|-----------|
"""
    
    for _, row in df.iterrows():
        tier_emoji = {'1_PLATINUM': '💎', '2_DANGER_ZONE': '🥇', '3_SILVER': '🥈', '4_BRONZE': '🥉'}.get(row['score_tier'], '⚪')
        report += f"| {tier_emoji} {row['score_tier']} | {row['new_leads']} | {row['avg_score']} |\n"
    
    report += """
## Recommended Actions

1. **Tier 1 (Platinum):** Generate LinkedIn hunt list
2. **Tier 2 (Danger Zone):** Assign to cold call queue
3. **Review:** Check if any Tier 1 leads have LinkedIn activity

---
*Generated by V3 Lead Scoring Pipeline*
"""
    
    return report
```

### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G7.1.1 | Scheduled query created | Running daily | ⏳ |
| G7.2.1 | Salesforce fields exist | All custom fields created | ⏳ |
| G7.2.2 | Sync working | Test payload accepted | ⏳ |
| G7.3.1 | Dashboard view created | SGA can access | ⏳ |
| G7.4.1 | Weekly report generated | Email sent Monday AM | ⏳ |

---
```

---

# PROMPT 8: Update Phase 8 (Temporal Backtest) for V3

**Instructions for Cursor:**

In `@leadscoring_plan.md`, update Phase 8 to validate the tiered query against historical data. Instead of ML metrics, we measure tier stability over time.

**Replace Phase 8 content with:**

```markdown
---

## Phase 8: V3 Temporal Stability Validation

> **Purpose:** Validate that tier performance is stable across different time periods.
> 
> **Key Change from V2:** We measure tier lift consistency, not model AUC.

### Why Temporal Validation Still Matters

Even though V3 uses rules instead of ML, we still need to confirm:
1. Tier definitions don't accidentally select for temporal artifacts
2. Lift is stable across quarters
3. Pool isn't depleting (volume by tier over time)

### Unit 8.1: Quarterly Tier Performance

```sql
-- Tier performance by quarter
WITH quarterly_tiers AS (
    SELECT 
        DATE_TRUNC(contacted_date, QUARTER) as quarter,
        score_tier,
        COUNT(*) as volume,
        SUM(converted) as conversions,
        AVG(converted) as conversion_rate
    FROM historical_scored_leads_v3
    WHERE contacted_date >= '2024-01-01'
    GROUP BY 1, 2
)

SELECT 
    quarter,
    score_tier,
    volume,
    ROUND(conversion_rate * 100, 2) as conv_rate_pct,
    ROUND(conversion_rate / 0.0084, 2) as lift,
    -- Quarter-over-quarter change
    ROUND((conversion_rate - LAG(conversion_rate) OVER (PARTITION BY score_tier ORDER BY quarter)) 
          / NULLIF(LAG(conversion_rate) OVER (PARTITION BY score_tier ORDER BY quarter), 0) * 100, 1) as qoq_change_pct
FROM quarterly_tiers
ORDER BY quarter, score_tier
```

**Expected Pattern:**
| Tier | Q1 2024 | Q2 2024 | Q3 2024 | Q4 2024 | Variance |
|------|---------|---------|---------|---------|----------|
| 1_PLATINUM | 2.3x | 2.6x | 2.5x | 2.4x | ±0.15x ✅ |
| 2_DANGER_ZONE | 2.5x | 2.4x | 2.2x | 2.1x | ±0.2x ✅ |

**Alert:** Variance > ±0.5x indicates potential issue.

### Unit 8.2: Pool Depletion Check

```sql
-- Volume by tier over time (check for depletion)
SELECT 
    DATE_TRUNC(contacted_date, MONTH) as month,
    score_tier,
    COUNT(*) as new_leads_in_tier,
    SUM(COUNT(*)) OVER (PARTITION BY score_tier ORDER BY DATE_TRUNC(contacted_date, MONTH)) as cumulative_contacted
FROM historical_scored_leads_v3
GROUP BY 1, 2
ORDER BY 1, 2
```

**Alert Conditions:**
- Tier 1 monthly volume drops > 30% from prior quarter → Pool may be depleting
- Tier 2 monthly volume drops > 50% → Market conditions changed

### Unit 8.3: Firm-Level Depletion

```sql
-- Top firms in each tier - are they getting fished out?
WITH firm_tier_counts AS (
    SELECT 
        Company,
        score_tier,
        DATE_TRUNC(contacted_date, QUARTER) as quarter,
        COUNT(DISTINCT advisor_crd) as advisors_contacted
    FROM historical_scored_leads_v3
    WHERE score_tier IN ('1_PLATINUM', '2_DANGER_ZONE')
    GROUP BY 1, 2, 3
)

SELECT 
    Company,
    score_tier,
    SUM(CASE WHEN quarter = '2024-01-01' THEN advisors_contacted END) as q1_2024,
    SUM(CASE WHEN quarter = '2024-04-01' THEN advisors_contacted END) as q2_2024,
    SUM(CASE WHEN quarter = '2024-07-01' THEN advisors_contacted END) as q3_2024,
    SUM(CASE WHEN quarter = '2024-10-01' THEN advisors_contacted END) as q4_2024,
    -- Depletion check
    CASE 
        WHEN SUM(CASE WHEN quarter = '2024-10-01' THEN advisors_contacted END) = 0
             AND SUM(CASE WHEN quarter = '2024-01-01' THEN advisors_contacted END) > 10
        THEN '🚨 DEPLETED'
        ELSE '✅ OK'
    END as status
FROM firm_tier_counts
GROUP BY 1, 2
HAVING SUM(advisors_contacted) > 20
ORDER BY SUM(advisors_contacted) DESC
LIMIT 50
```

### Unit 8.4: Holdout Validation

**Simulated Deployment Test:**
1. Train tier definitions on 2024 H1 data
2. Score 2024 H2 data
3. Compare predicted tier performance to actual

```python
def run_holdout_validation(client: bigquery.Client):
    """
    Simulate deploying V3 in July 2024 and measure performance through December.
    """
    
    query = """
    WITH holdout_leads AS (
        -- Leads from July-December 2024 (simulate "future")
        SELECT *
        FROM lead_features
        WHERE contacted_date BETWEEN '2024-07-01' AND '2024-12-31'
    ),
    
    scored_holdout AS (
        -- Apply V3 tier logic
        SELECT *,
            CASE 
                WHEN is_small_firm = 1 AND in_sweet_spot = 1 AND is_experienced = 1 AND is_wirehouse = 0
                THEN '1_PLATINUM'
                WHEN in_danger_zone = 1 AND at_bleeding_firm = 1 AND is_veteran = 1
                THEN '2_DANGER_ZONE'
                ...
            END as score_tier
        FROM holdout_leads
    )
    
    SELECT 
        score_tier,
        COUNT(*) as volume,
        SUM(converted) as conversions,
        ROUND(AVG(converted) * 100, 2) as conv_rate_pct,
        ROUND(AVG(converted) / 0.0084, 2) as lift
    FROM scored_holdout
    GROUP BY 1
    ORDER BY 1
    """
    
    results = client.query(query).to_dataframe()
    
    # Validate against expected lift
    tier_1_lift = results[results['score_tier'] == '1_PLATINUM']['lift'].values[0]
    tier_2_lift = results[results['score_tier'] == '2_DANGER_ZONE']['lift'].values[0]
    
    print(f"Holdout Validation Results:")
    print(f"  Tier 1 Lift: {tier_1_lift:.2f}x (expected ≥ 2.4x)")
    print(f"  Tier 2 Lift: {tier_2_lift:.2f}x (expected ≥ 2.0x)")
    
    if tier_1_lift >= 2.4 and tier_2_lift >= 2.0:
        print("✅ PASSED: Model generalizes to holdout period")
        return True
    else:
        print("❌ FAILED: Lift degradation detected")
        return False
```

### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G8.1.1 | Tier 1 quarterly variance | < ±0.5x | ⏳ |
| G8.1.2 | Tier 2 quarterly variance | < ±0.5x | ⏳ |
| G8.2.1 | No major pool depletion | Volume drop < 30%/quarter | ⏳ |
| G8.3.1 | Top 10 firms not depleted | At least 5 active | ⏳ |
| G8.4.1 | Holdout Tier 1 lift | ≥ 2.4x | ⏳ |
| G8.4.2 | Holdout Tier 2 lift | ≥ 2.0x | ⏳ |

---
```

---

# PROMPT 9: Update Monitoring & Alerts Section

**Instructions for Cursor:**

In `@leadscoring_plan.md`, update the Production Monitoring section at the end to reflect V3 specifics. Add explicit decay detection based on our learnings.

**Replace/update the Production Monitoring section with:**

```markdown
---

## Production Monitoring (V3)

### Key Metrics Dashboard

**Daily Monitoring:**
| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Tier 1 volume | Daily scoring | < 10 new/day |
| Tier 2 volume | Daily scoring | < 3 new/day |
| SF sync success | Salesforce API | < 95% |

**Weekly Monitoring:**
| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Tier 1 conversion rate | SF closed-won | < 1.5% (30-day trailing) |
| Tier 2 conversion rate | SF closed-won | < 1.2% (30-day trailing) |
| Combined lift | Calculated | < 2.0x |

**Monthly Monitoring:**
| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Pool depletion rate | Tier volume trend | > 20% MoM decline |
| Top firm concentration | Firm analysis | Any firm > 25% of tier |
| Channel performance gap | LinkedIn vs cold | < 2x (narrowing = issue) |

### Signal Decay Detection

**Based on V2→V3 Investigation Learnings:**

```python
def detect_signal_decay(client: bigquery.Client) -> Dict:
    """
    Weekly check for the same decay pattern that killed V2.
    """
    
    query = """
    WITH recent_performance AS (
        SELECT 
            DATE_TRUNC(contacted_date, WEEK) as week,
            score_tier,
            LeadSource,
            COUNT(*) as volume,
            SUM(converted) as conversions,
            AVG(converted) as conv_rate
        FROM lead_scores_v3_with_outcomes
        WHERE contacted_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        GROUP BY 1, 2, 3
    )
    
    SELECT 
        score_tier,
        LeadSource,
        -- Last 4 weeks vs prior 8 weeks
        AVG(CASE WHEN week >= DATE_SUB(CURRENT_DATE(), INTERVAL 28 DAY) 
            THEN conv_rate END) as recent_conv,
        AVG(CASE WHEN week < DATE_SUB(CURRENT_DATE(), INTERVAL 28 DAY) 
            THEN conv_rate END) as prior_conv,
        SAFE_DIVIDE(
            AVG(CASE WHEN week >= DATE_SUB(CURRENT_DATE(), INTERVAL 28 DAY) THEN conv_rate END),
            AVG(CASE WHEN week < DATE_SUB(CURRENT_DATE(), INTERVAL 28 DAY) THEN conv_rate END)
        ) as conv_ratio
    FROM recent_performance
    GROUP BY 1, 2
    HAVING COUNT(*) >= 4  -- Need at least 4 weeks of data
    """
    
    results = client.query(query).to_dataframe()
    
    alerts = []
    
    for _, row in results.iterrows():
        if row['conv_ratio'] and row['conv_ratio'] < 0.7:
            alerts.append({
                'tier': row['score_tier'],
                'channel': row['LeadSource'],
                'recent_conv': row['recent_conv'],
                'prior_conv': row['prior_conv'],
                'decay_pct': (1 - row['conv_ratio']) * 100,
                'severity': 'CRITICAL' if row['conv_ratio'] < 0.5 else 'WARNING'
            })
    
    return {
        'alerts': alerts,
        'status': 'ALERT' if alerts else 'OK',
        'checked_at': datetime.now().isoformat()
    }
```

### Root Cause Playbook

**When Decay is Detected:**

1. **Check Lead Source Shift**
   ```sql
   SELECT 
       DATE_TRUNC(contacted_date, MONTH) as month,
       LeadSource,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY DATE_TRUNC(contacted_date, MONTH)), 1) as pct
   FROM lead_scores_v3_with_outcomes
   WHERE contacted_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
   GROUP BY 1, 2
   ORDER BY 1, 3 DESC
   ```

2. **Check Pool Quality**
   ```sql
   SELECT 
       DATE_TRUNC(contacted_date, MONTH) as month,
       score_tier,
       AVG(industry_tenure_months) as avg_experience,
       AVG(pit_moves_3yr) as avg_mobility,
       AVG(ABS(firm_net_change_12mo)) as avg_firm_bleeding
   FROM lead_scores_v3_with_features
   WHERE score_tier IN ('1_PLATINUM', '2_DANGER_ZONE')
   GROUP BY 1, 2
   ORDER BY 1, 2
   ```

3. **Check Firm Depletion**
   ```sql
   SELECT 
       Company,
       MIN(contacted_date) as first_contact,
       MAX(contacted_date) as last_contact,
       COUNT(DISTINCT advisor_crd) as total_advisors_contacted,
       COUNTIF(contacted_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)) as last_30_days
   FROM lead_scores_v3_with_outcomes
   WHERE score_tier = '1_PLATINUM'
   GROUP BY 1
   HAVING COUNT(DISTINCT advisor_crd) > 20
   ORDER BY last_30_days ASC
   ```

### Recalibration Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| **Automatic** | Quarterly scheduled | Run holdout validation |
| **Warning** | Any tier lift drops 20% | Review root cause playbook |
| **Critical** | Tier 1 lift < 2.0x for 4 weeks | Pause Tier 1 lists, investigate |
| **Emergency** | Combined lift < 1.5x | Pause all scoring, full investigation |

### Retrain/Reconfigure Guidelines

1. **Threshold Adjustment** (Minor):
   - Tier 1 sweet spot: Try 3-12 years instead of 4-10 years
   - Firm size: Try ≤15 instead of ≤10
   - Document change and A/B test

2. **Wirehouse List Update** (Minor):
   - Add newly-identified captive firms
   - Remove firms that became independent
   - Quarterly review with SGA team

3. **Tier Redesign** (Major):
   - If both tiers drop below 1.5x for 3 months
   - Re-run full investigation (Phase -2)
   - Consider new feature sources

---
```

---

# PROMPT 10: Add Appendix with Key Learnings & Decisions Log

**Instructions for Cursor:**

In `@leadscoring_plan.md`, add a new Appendix section at the very end. This documents the key learnings from the V2→V3 investigation for future reference.

**Add this new section:**

```markdown
---

## Appendix A: V2→V3 Investigation Key Learnings

### Summary of What We Learned

This appendix documents the systematic investigation that led to pivoting from V2 XGBoost to V3 Tiered Query.

### Learning 1: Signal Decay Was Real, Not a Bug

**Observation:** V2 model lift dropped from 4.43x (2024) to 1.46x (2025)

**Root Cause:** Not model overfitting. Three real-world factors:
1. Lead source shift (Provided Lists → LinkedIn)
2. Pool quality degradation ("Senior Movers" fished out, left with "Junior Stayers")
3. Top firm depletion (Mariner, Corebridge, Corient 100% contacted)

**Implication:** Even perfect models decay if the underlying pool changes.

### Learning 2: Same Signal, Different Channels = Wildly Different Results

**Observation:**
| Channel | Baseline | DZ Lift |
|---------|----------|---------|
| LinkedIn | 1.83% | 2.10x |
| Provided List | 0.67% | 1.44x |

**Root Cause:** LinkedIn is "warm outreach" (you find them), lists are "cold outreach" (they're assigned).

**Implication:** Don't evaluate signals in aggregate. Always segment by channel.

### Learning 3: The Model Optimized for the Wrong Thing

**Observation:** V2 model loved large, stable firms (wirehouses). SGAs correctly avoided them.

**Root Cause:** 
- Model saw: Large firm = stable = good
- Reality: Large firm = "Golden Handcuffs" = can't move

**Implication:** Domain expertise (SGA intuition) > pure data patterns for some features.

### Learning 4: Velocity Features Work, But Can't Overcome Bad Lists

**Observation:** "Days since last move" had 7x predictive power in isolation, but only added ~0.2x lift to full model.

**Root Cause:** Velocity is correlated with other good signals (DZ tenure, prior moves). Incremental value is limited when base features are already strong.

**Implication:** Feature importance ≠ incremental value. Always test marginal contribution.

### Learning 5: Transparency Beats Accuracy for Adoption

**Observation:** SGAs didn't trust the V2 "black box" even when it was working.

**Insight:** "Score is 0.73" means nothing. "Small independent firm, 6 years tenure, not wirehouse" is actionable.

**Implication:** For sales tools, explainability > marginal accuracy improvement.

### Learning 6: Pool Depletion is Inevitable, Plan for It

**Observation:**
- 2024: Best firms heavily contacted
- 2025: Those firms depleted, forced to lower-quality leads

**Implication:** 
- Build pool replenishment into the process (new FINTRX data, new criteria)
- Monitor volume by tier monthly
- Diversify channels (LinkedIn hunting)

---

## Appendix B: Decision Log

| Date | Decision | Rationale | Outcome |
|------|----------|-----------|---------|
| 2025-12-01 | Investigate V2 decay | 4.43x → 1.46x lift suspicious | Identified 3 root causes |
| 2025-12-10 | Add velocity features | Hypothesis: recency matters | +0.2x lift, not sufficient |
| 2025-12-15 | Analyze SGA intuition | SGAs outperforming model | Discovered "SGA Platinum" profile |
| 2025-12-18 | Test tiered approach | Combine SGA + DZ signals | 2.55x + 2.33x validated |
| 2025-12-20 | Pivot to V3 Tiered | ML not adding value over rules | Approved for production |
| 2025-12-21 | Deploy V3 | Tiered query ready | In production |

---

## Appendix C: File References

### Investigation Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| `signal_decay_diagnostic.py` | 7-hypothesis investigation | `/outputs/` |
| `lead_source_signal_check.py` | Channel comparison | `/outputs/` |
| `sga_criteria_validation.py` | SGA profile testing | `/outputs/` |
| `hybrid_model_test.py` | Tier combination testing | `/outputs/` |

### Production Files

| File | Purpose | Location |
|------|---------|----------|
| `lead_scoring_v3_hybrid.py` | Python scorer | `/outputs/` |
| `lead_scoring_v3_query.sql` | BigQuery query | `/outputs/` |
| `tier_calibration.json` | Expected conversion rates | `/models/v3-hybrid/` |

---

*Document Version: 3.0*  
*Last Updated: December 21, 2025*  
*Model Version: v3-hybrid-20251221*
```

---

# Execution Checklist

After running all 10 prompts, verify:

- [ ] Executive summary reflects V3 pivot
- [ ] Phase -2 (Signal Decay Investigation) added
- [ ] Phase 4 replaced with Tiered Query logic
- [ ] Phase 4.5 (Channel Strategy) added
- [ ] Phase 5 updated for tier validation
- [ ] Phase 6 simplified for tier calibration
- [ ] Phase 7 updated for SQL-based deployment
- [ ] Phase 8 updated for temporal stability
- [ ] Monitoring section includes decay detection
- [ ] Appendices with learnings and decisions added

---

*Prompts generated: December 21, 2025*
*Based on V2→V3 signal decay investigation*
