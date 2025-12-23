# Cursor.ai Cleanup Prompts: Finalize leadscoring_plan.md for V3

## Overview

These prompts clean up remaining V2 XGBoost remnants and update all paths to Version-3. Execute **in order**.

**Key Changes:**
1. Update ALL directory paths from `Version-2` → `Version-3`
2. Remove orphaned XGBoost training code sections
3. **KEEP narrative/explanation infrastructure** - adapt for rule-based contributions + LLM
4. Fix duplicate Phase headers
5. Consolidate monitoring sections
6. Update validation gates for V3 context

---

## 🎯 Narrative Generation Strategy for V3

**Can we still do SHAP with the two-tier methodology?**

**YES!** But we adapt it. Here's the approach:

| Aspect | V2 (XGBoost) | V3 (Tiered + LLM) |
|--------|--------------|-------------------|
| **Contribution Source** | SHAP TreeExplainer | Rule-based contribution scores |
| **Explanation Engine** | Template strings | LLM (Claude) narrative generation |
| **Output** | "feature X contributed 0.15" | "Small firm with 8 advisors - portable book likely" |
| **Salesforce Fields** | Lead_Score_SHAP__c | Lead_Score_Narrative__c + Lead_Score_Factors__c |

Each tier rule contributes a score. The LLM converts those contributions into natural language narratives that SGAs can read and act on.

---

# PROMPT 1: Update All Directory Paths to Version-3

**Instructions for Cursor:**

In `@leadscoring_plan.md`, perform a global search and replace to update all directory references from Version-2 to Version-3. This includes:

1. The execution log path
2. The base directory structure
3. All path constants
4. All LOG CHECKPOINT references

**Specific Changes:**

Find and replace ALL occurrences:
- `Version-2` → `Version-3`
- `Version-2\` → `Version-3\`
- `Version-2/` → `Version-3/`

**Update the Directory Structure section (around line 157-211) to:**

```markdown
## Version-3 Directory Structure

All files for this model version MUST be created in:
`C:\Users\russe\Documents\Lead Scoring\Version-3`

### Directory Layout

```
C:\Users\russe\Documents\Lead Scoring\Version-3\
│
├── EXECUTION_LOG.md                    # Living log of all phases (auto-generated)
├── tier_config.json                    # Tier definitions and thresholds
│
├── utils\                              # Utility modules
│   ├── __init__.py
│   ├── execution_logger.py             # Logging module
│   ├── paths.py                        # Path constants
│   ├── tier_definitions.py             # Tier assignment logic
│   └── narrative_generator.py          # LLM-powered narrative generation
│
├── data\                               # Data artifacts
│   ├── raw\                            # Raw data exports from BigQuery
│   │   ├── leads_raw.csv
│   │   └── firm_historicals_sample.csv
│   ├── validation\                     # Tier validation data
│   │   ├── tier_performance_historical.csv
│   │   └── channel_performance.csv
│   └── scored\                         # Scoring outputs
│       ├── sga_priority_list_YYYYMMDD.csv
│       └── tier_distribution_YYYYMMDD.csv
│
├── sql\                                # SQL queries
│   ├── lead_scoring_v3.sql             # Main tiered scoring query
│   ├── tier_validation.sql             # Historical validation queries
│   ├── weekly_lists.sql                # Weekly list generation
│   └── monitoring.sql                  # Decay detection queries
│
├── reports\                            # Analysis reports
│   ├── phase_-2_signal_decay.md        # V2→V3 investigation
│   ├── phase_5_tier_validation.md      # Tier performance report
│   ├── phase_8_temporal_stability.md   # Stability analysis
│   └── weekly\                         # Weekly performance reports
│       └── week_YYYYMMDD.md
│
├── inference\                          # Production inference code
│   ├── lead_scorer_v3.py               # Tiered scorer class
│   ├── contribution_calculator.py      # Rule-based "SHAP-like" contributions
│   ├── narrative_generator.py          # LLM narrative generation
│   ├── weekly_list_generator.py        # Weekly list generation
│   └── salesforce_sync.py              # Salesforce integration
│
└── config\                             # Configuration files
    ├── wirehouse_patterns.json         # Wirehouse exclusion list
    ├── tier_thresholds.json            # Tier boundary definitions
    ├── channel_strategy.json           # Channel recommendations per tier
    └── narrative_prompts.json          # LLM prompt templates
```

### Path Constants Module

All phases should import path constants from `utils/paths.py`:

```python
# C:\Users\russe\Documents\Lead Scoring\Version-3\utils\paths.py
"""
Centralized path constants for Version-3 model development.

Usage:
    from utils.paths import PATHS
    
    sql_path = PATHS['SQL_DIR'] / 'lead_scoring_v3.sql'
"""

from pathlib import Path

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-3")

PATHS = {
    # Base
    'BASE': BASE_DIR,
    'EXECUTION_LOG': BASE_DIR / 'EXECUTION_LOG.md',
    'TIER_CONFIG': BASE_DIR / 'tier_config.json',
    
    # Utils
    'UTILS_DIR': BASE_DIR / 'utils',
    
    # Data
    'DATA_DIR': BASE_DIR / 'data',
    'RAW_DATA_DIR': BASE_DIR / 'data' / 'raw',
    'VALIDATION_DIR': BASE_DIR / 'data' / 'validation',
    'SCORED_DIR': BASE_DIR / 'data' / 'scored',
    
    # SQL
    'SQL_DIR': BASE_DIR / 'sql',
    
    # Reports
    'REPORTS_DIR': BASE_DIR / 'reports',
    'WEEKLY_REPORTS_DIR': BASE_DIR / 'reports' / 'weekly',
    
    # Inference
    'INFERENCE_DIR': BASE_DIR / 'inference',
    
    # Config
    'CONFIG_DIR': BASE_DIR / 'config',
    'WIREHOUSE_PATTERNS': BASE_DIR / 'config' / 'wirehouse_patterns.json',
    'TIER_THRESHOLDS': BASE_DIR / 'config' / 'tier_thresholds.json',
    'NARRATIVE_PROMPTS': BASE_DIR / 'config' / 'narrative_prompts.json',
}
```
```

**Also update ALL LOG CHECKPOINT blocks to reference Version-3:**

Find all instances of:
```markdown
> `C:\Users\russe\Documents\Lead Scoring\Version-2\EXECUTION_LOG.md`
```

Replace with:
```markdown
> `C:\Users\russe\Documents\Lead Scoring\Version-3\EXECUTION_LOG.md`
```

---

# PROMPT 2: Remove Orphaned XGBoost Training Code (Phase 4 Old Content)

**Instructions for Cursor:**

In `@leadscoring_plan.md`, there is leftover XGBoost training code that appears AFTER the new V3 Phase 5 section. This orphaned content starts around line 5710 with `#### Code Snippet` and the `BaselineXGBoostTrainer` class.

**Delete the entire section from approximately line 5710 to line 6070** that contains:

1. The `BaselineXGBoostTrainer` class (lines ~5714-6047)
2. The old validation gates for G4.1.1-G4.1.4 (around line 6049-6056)
3. The duplicate LOG CHECKPOINT (around line 6059-6069)
4. The old "Implement hyperparameter tuning" Cursor Prompt (around line 6072-6094)
5. The `XGBoostOptimizer` class (lines ~6096-6200+)

**Look for these markers to identify the section to delete:**

```python
# baseline_xgboost.py
"""
Phase 4.1: Baseline XGBoost with Class Imbalance Handling
```

AND

```python
# hyperparameter_tuning.py
"""
Phase 4.2: Hyperparameter Tuning with Optuna
```

**Delete everything from the first `#### Code Snippet` after the V3 Phase 5 validation gates (line ~5710) until you reach the clean Phase 6 or Phase 7 header.**

The document should flow directly from:
```markdown
### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G5.1.1 | Tier 1 Lift | ≥ 2.4x | ⏳ |
...
| G5.3.1 | Temporal Variance | < 0.5x between quarters | ⏳ |

---
```

To:
```markdown
## Phase 6: Tier Calibration & Production Packaging
```

---

# PROMPT 3: Remove Orphaned Probability Calibration Code (Phase 6 Old Content)

**Instructions for Cursor:**

In `@leadscoring_plan.md`, after the V3 Phase 6 content (Tier Calibration), there is leftover XGBoost probability calibration code.

**Look for and DELETE the section starting with:**

```markdown
#### Cursor Prompt
```
Implement probability calibration to ensure predicted probabilities match actual conversion rates.
```

This section (approximately lines 7566-7720+) contains:
1. Old Cursor Prompt for probability calibration
2. `ProbabilityCalibrator` class
3. Old ECE/Brier score calculations for XGBoost

**Delete from the old "#### Cursor Prompt" (around line 7566) that mentions "isotonic regression and Platt scaling" until you reach a clean section break or Phase 7.**

The document should flow from the V3 Validation Gates:
```markdown
| G6.3.1 | No current drift | All tiers within 0.5% | ⏳ |

---
```

Directly to:
```markdown
## Phase 7: V3 Production Deployment
```

---

# PROMPT 4: Remove Orphaned Model Packaging Code (Phase 6 Old Content)

**Instructions for Cursor:**

In `@leadscoring_plan.md`, there is leftover XGBoost model packaging code with classes like `ModelPackager`.

**Look for and DELETE the section containing:**

1. `ModelPackager` class (with methods like `calculate_model_hash`, `export_pickle`, `export_onnx`)
2. Old ONNX export code
3. Old model card generation for XGBoost
4. Old registry update code

**This section appears around lines 7980-8200+ and contains code like:**

```python
def calculate_model_hash(self) -> str:
    """Calculate MD5 hash of model for versioning"""
```

AND

```python
def export_onnx(self, output_path: Path = None) -> Path:
    """Export model as ONNX (for cross-platform deployment)"""
```

**Delete this entire orphaned section.**

---

# PROMPT 5: Remove Orphaned LeadScorer/BatchScorer Classes (Phase 6/7 Old Content)

**Instructions for Cursor:**

In `@leadscoring_plan.md`, there are old `LeadScorer` and `BatchScorerJob` classes that were designed for XGBoost inference.

**Look for and DELETE sections containing:**

1. Old `LeadScorer` class (with `load_model`, `score_leads`, `score_single_lead` methods)
2. Old `BatchScorerJob` class
3. Old `ScoringAPI` class

**These appear around lines 8300-8620 and contain code like:**

```python
class LeadScorer:
    """
    Production lead scoring class
    Loads calibrated model and provides scoring interface
    """
```

AND

```python
class BatchScorerJob:
    """Batch scoring job for daily/weekly runs"""
```

**Delete these sections as V3 uses `LeadScorerV3` (defined in Phase 4) instead.**

---

# PROMPT 6: Add Rule-Based Contributions + LLM Narrative System (NEW PHASE 4.6)

**Instructions for Cursor:**

In `@leadscoring_plan.md`, **ADD a new section** after Phase 4.5 (Channel Strategy) called "Phase 4.6: Narrative Generation System".

This is the **V3 replacement for SHAP** - it uses rule-based contribution scores + LLM narratives.

**Add this new section:**

```markdown
---

## Phase 4.6: Narrative Generation System (V3 "SHAP")

> **Purpose:** Generate human-readable explanations for why each lead was prioritized.
> 
> **Key Change from V2:** Instead of XGBoost SHAP values, we use rule-based contributions + LLM narratives.
> 
> **Why This is Better:** Contributions map directly to business rules SGAs understand. LLM adds conversational context.

### Why V3 Narratives Are Better Than V2 SHAP

| Aspect | V2 (XGBoost SHAP) | V3 (Rule-Based + LLM) |
|--------|-------------------|----------------------|
| **Source** | TreeExplainer on black-box model | Explicit rule matching |
| **Interpretability** | "Feature X contributed 0.15" | "Small firm (8 advisors) - portable book likely" |
| **Auditability** | Requires SHAP expertise | Any business user can verify |
| **Narrative Quality** | Static templates | LLM-powered, contextual, conversational |
| **Computational Cost** | Expensive for large batches | Fast rule evaluation + targeted LLM calls |
| **SGA Adoption** | Low (confusing numbers) | High (reads like a brief) |

### The V3 Narrative Pipeline

```
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐    ┌──────────────────┐
│  Lead Features  │───▶│  Tier Assignment     │───▶│  Contribution   │───▶│  LLM Narrative   │
│  (from BigQuery)│    │  (Rule-based scorer) │    │  Calculator     │    │  Generator       │
└─────────────────┘    └──────────────────────┘    └─────────────────┘    └──────────────────┘
                                │                         │                       │
                                ▼                         ▼                       ▼
                          score_tier              contribution_scores        narrative_text
                          lead_score              top_factors_json           confidence_level
```

### Unit 4.6.1: Rule-Based Contribution Calculator

Each tier rule contributes a score. When a rule matches, it adds to the explanation.

```python
# C:\Users\russe\Documents\Lead Scoring\Version-3\inference\contribution_calculator.py
"""
Rule-Based Contribution Calculator

Calculates "SHAP-like" contributions based on which tier rules matched.
These contributions are then fed to an LLM for narrative generation.

This replaces XGBoost SHAP with transparent, auditable rule contributions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json

@dataclass
class FeatureContribution:
    """Represents a single feature's contribution to tier assignment."""
    feature_name: str
    feature_value: float
    contribution_score: float  # -1.0 to +1.0 (negative = hurts, positive = helps)
    direction: str  # "positive", "negative", "neutral"
    rule_matched: str  # Which rule this satisfies
    explanation: str  # Human-readable explanation
    
    def to_dict(self) -> dict:
        return {
            'feature': self.feature_name,
            'value': round(self.feature_value, 2),
            'impact': round(self.contribution_score, 3),
            'direction': self.direction,
            'explanation': self.explanation[:100]
        }


class ContributionCalculator:
    """
    Calculates rule-based contributions for V3 tiered scoring.
    
    Each contribution explains WHY a lead was assigned to a particular tier.
    This provides "SHAP-like" explainability without needing an ML model.
    """
    
    # Contribution weights for each rule (sum to ~1.0 for each tier)
    TIER_1_WEIGHTS = {
        'small_firm': 0.30,
        'sweet_spot_tenure': 0.25,
        'experienced': 0.25,
        'not_wirehouse': 0.20
    }
    
    TIER_2_WEIGHTS = {
        'danger_zone': 0.35,
        'bleeding_firm': 0.35,
        'veteran': 0.30
    }
    
    WIREHOUSE_PATTERNS = [
        'MERRILL', 'MORGAN STANLEY', 'UBS', 'WELLS FARGO',
        'EDWARD JONES', 'RAYMOND JAMES', 'LPL FINANCIAL',
        'NORTHWESTERN MUTUAL', 'MASS MUTUAL', 'MASSMUTUAL',
        'PRUDENTIAL', 'AMERIPRISE', 'FIDELITY', 'SCHWAB',
        'VANGUARD', 'FISHER INVESTMENTS', 'CREATIVE PLANNING',
        'EDELMAN', 'FIRST COMMAND', 'CETERA', 'COMMONWEALTH'
    ]
    
    def __init__(self, wirehouse_patterns: List[str] = None):
        self.wirehouse_patterns = wirehouse_patterns or self.WIREHOUSE_PATTERNS
    
    def is_wirehouse(self, company: str) -> bool:
        """Check if company matches wirehouse patterns."""
        if not company:
            return False
        company_upper = company.upper()
        return any(pattern in company_upper for pattern in self.wirehouse_patterns)
    
    def calculate_contributions(self, features: Dict) -> List[FeatureContribution]:
        """
        Calculate contributions for a single lead.
        
        Args:
            features: Dict with lead features including:
                - current_firm_tenure_months
                - industry_tenure_months
                - firm_rep_count_at_contact
                - firm_net_change_12mo
                - company (firm name)
            
        Returns:
            List of FeatureContribution objects, sorted by |contribution_score|
        """
        contributions = []
        
        # Extract features with defaults
        tenure_months = float(features.get('current_firm_tenure_months', 0) or 0)
        industry_months = float(features.get('industry_tenure_months', 0) or 0)
        rep_count = float(features.get('firm_rep_count_at_contact', 100) or 100)
        net_change = float(features.get('firm_net_change_12mo', 0) or 0)
        company = str(features.get('company', '') or features.get('Company', '') or '')
        
        # Derived values
        tenure_years = tenure_months / 12
        industry_years = industry_months / 12
        is_wirehouse = self.is_wirehouse(company)
        
        # =====================================================
        # FIRM SIZE CONTRIBUTION
        # =====================================================
        if rep_count <= 10:
            contributions.append(FeatureContribution(
                feature_name='firm_size',
                feature_value=rep_count,
                contribution_score=self.TIER_1_WEIGHTS['small_firm'],
                direction='positive',
                rule_matched='small_firm',
                explanation=f"Small independent firm ({int(rep_count)} advisors) - portable book likely"
            ))
        elif rep_count <= 50:
            contributions.append(FeatureContribution(
                feature_name='firm_size',
                feature_value=rep_count,
                contribution_score=0.05,
                direction='neutral',
                rule_matched='medium_firm',
                explanation=f"Mid-size firm ({int(rep_count)} advisors)"
            ))
        else:
            contributions.append(FeatureContribution(
                feature_name='firm_size',
                feature_value=rep_count,
                contribution_score=-0.15,
                direction='negative',
                rule_matched='large_firm',
                explanation=f"Large firm ({int(rep_count)} advisors) - more institutional ties"
            ))
        
        # =====================================================
        # TENURE CONTRIBUTION
        # =====================================================
        if 48 <= tenure_months <= 120:  # 4-10 years = Sweet Spot
            contributions.append(FeatureContribution(
                feature_name='current_tenure',
                feature_value=tenure_years,
                contribution_score=self.TIER_1_WEIGHTS['sweet_spot_tenure'],
                direction='positive',
                rule_matched='sweet_spot_tenure',
                explanation=f"Sweet spot tenure ({tenure_years:.1f} years) - established but not entrenched"
            ))
        elif 12 <= tenure_months < 48:  # 1-4 years = Danger Zone
            contributions.append(FeatureContribution(
                feature_name='current_tenure',
                feature_value=tenure_years,
                contribution_score=0.20,
                direction='positive',
                rule_matched='danger_zone_tenure',
                explanation=f"Danger Zone tenure ({tenure_years:.1f} years) - may be evaluating fit"
            ))
        elif tenure_months < 12:
            contributions.append(FeatureContribution(
                feature_name='current_tenure',
                feature_value=tenure_years,
                contribution_score=-0.10,
                direction='negative',
                rule_matched='too_new',
                explanation=f"Very recent hire ({tenure_years:.1f} years) - too early to consider moving"
            ))
        else:  # > 10 years
            contributions.append(FeatureContribution(
                feature_name='current_tenure',
                feature_value=tenure_years,
                contribution_score=-0.15,
                direction='negative',
                rule_matched='long_tenure',
                explanation=f"Long tenure ({tenure_years:.1f} years) - deeply rooted, harder to move"
            ))
        
        # =====================================================
        # EXPERIENCE CONTRIBUTION
        # =====================================================
        if 96 <= industry_months <= 360:  # 8-30 years
            contributions.append(FeatureContribution(
                feature_name='industry_experience',
                feature_value=industry_years,
                contribution_score=self.TIER_1_WEIGHTS['experienced'],
                direction='positive',
                rule_matched='experienced',
                explanation=f"Prime experience ({industry_years:.0f} years) - established book, not near retirement"
            ))
        elif industry_months >= 120:  # 10+ years = Veteran
            contributions.append(FeatureContribution(
                feature_name='industry_experience',
                feature_value=industry_years,
                contribution_score=0.20,
                direction='positive',
                rule_matched='veteran',
                explanation=f"Veteran advisor ({industry_years:.0f} years) - deep client relationships"
            ))
        elif industry_months >= 60:  # 5-8 years
            contributions.append(FeatureContribution(
                feature_name='industry_experience',
                feature_value=industry_years,
                contribution_score=0.10,
                direction='positive',
                rule_matched='mid_career',
                explanation=f"Mid-career advisor ({industry_years:.0f} years) - building book"
            ))
        else:
            contributions.append(FeatureContribution(
                feature_name='industry_experience',
                feature_value=industry_years,
                contribution_score=-0.05,
                direction='neutral',
                rule_matched='early_career',
                explanation=f"Early career ({industry_years:.0f} years) - still building"
            ))
        
        # =====================================================
        # WIREHOUSE STATUS CONTRIBUTION
        # =====================================================
        if not is_wirehouse:
            contributions.append(FeatureContribution(
                feature_name='firm_type',
                feature_value=0,
                contribution_score=self.TIER_1_WEIGHTS['not_wirehouse'],
                direction='positive',
                rule_matched='not_wirehouse',
                explanation="Independent/RIA firm - no golden handcuffs, easier transition"
            ))
        else:
            contributions.append(FeatureContribution(
                feature_name='firm_type',
                feature_value=1,
                contribution_score=-0.30,
                direction='negative',
                rule_matched='wirehouse',
                explanation=f"Wirehouse firm ({company.split()[0] if company else 'Unknown'}...) - deferred comp likely locks them in"
            ))
        
        # =====================================================
        # FIRM STABILITY CONTRIBUTION (Bleeding Firm Signal)
        # =====================================================
        if net_change < -10:
            contributions.append(FeatureContribution(
                feature_name='firm_stability',
                feature_value=net_change,
                contribution_score=self.TIER_2_WEIGHTS['bleeding_firm'],
                direction='positive',
                rule_matched='severely_bleeding',
                explanation=f"Firm is hemorrhaging ({abs(int(net_change))} advisors left this year) - high instability"
            ))
        elif net_change < -5:
            contributions.append(FeatureContribution(
                feature_name='firm_stability',
                feature_value=net_change,
                contribution_score=0.25,
                direction='positive',
                rule_matched='bleeding_firm',
                explanation=f"Firm is bleeding ({abs(int(net_change))} net departures) - instability creates opportunity"
            ))
        elif net_change < 0:
            contributions.append(FeatureContribution(
                feature_name='firm_stability',
                feature_value=net_change,
                contribution_score=0.10,
                direction='positive',
                rule_matched='slight_decline',
                explanation=f"Firm has some turnover ({abs(int(net_change))} net departures)"
            ))
        else:
            contributions.append(FeatureContribution(
                feature_name='firm_stability',
                feature_value=net_change,
                contribution_score=0.0,
                direction='neutral',
                rule_matched='stable_growing',
                explanation=f"Firm is stable/growing (+{int(net_change)} net advisors)"
            ))
        
        # Sort by absolute contribution score (most impactful first)
        contributions.sort(key=lambda x: abs(x.contribution_score), reverse=True)
        
        return contributions
    
    def get_top_factors(self, contributions: List[FeatureContribution], n: int = 3) -> List[FeatureContribution]:
        """Get top N most impactful factors."""
        return contributions[:n]
    
    def calculate_aggregate_score(self, contributions: List[FeatureContribution]) -> float:
        """Calculate aggregate contribution score (sum of all contributions)."""
        return sum(c.contribution_score for c in contributions)
    
    def determine_confidence(self, contributions: List[FeatureContribution]) -> str:
        """
        Determine confidence level based on contribution pattern.
        
        Returns: "high", "medium", or "low"
        """
        positive_count = sum(1 for c in contributions if c.direction == "positive" and c.contribution_score > 0.1)
        negative_count = sum(1 for c in contributions if c.direction == "negative" and c.contribution_score < -0.1)
        aggregate = self.calculate_aggregate_score(contributions)
        
        if positive_count >= 3 and negative_count == 0 and aggregate > 0.6:
            return "high"
        elif positive_count >= 2 or (positive_count >= 1 and negative_count <= 1):
            return "medium"
        else:
            return "low"
    
    def format_for_llm(self, contributions: List[FeatureContribution], tier: str) -> str:
        """Format contributions as context for LLM narrative generation."""
        top_factors = self.get_top_factors(contributions, n=4)
        
        lines = [
            f"Tier Assignment: {tier}",
            f"Aggregate Score: {self.calculate_aggregate_score(contributions):.2f}",
            "",
            "Key Factors (ranked by impact):"
        ]
        
        for i, c in enumerate(top_factors, 1):
            emoji = "✅" if c.direction == "positive" else "⚠️" if c.direction == "negative" else "➖"
            lines.append(f"{i}. {emoji} {c.explanation}")
        
        return "\n".join(lines)
    
    def to_salesforce_json(self, contributions: List[FeatureContribution]) -> str:
        """Convert contributions to JSON for Salesforce Lead_Score_Factors__c field."""
        top_factors = self.get_top_factors(contributions, n=3)
        return json.dumps([c.to_dict() for c in top_factors])


# Quick test
if __name__ == "__main__":
    calc = ContributionCalculator()
    
    # Example Tier 1 lead
    tier1_lead = {
        'company': 'Apex Wealth Advisors',
        'firm_rep_count_at_contact': 8,
        'current_firm_tenure_months': 72,  # 6 years
        'industry_tenure_months': 180,     # 15 years
        'firm_net_change_12mo': -3
    }
    
    contributions = calc.calculate_contributions(tier1_lead)
    
    print("=== TIER 1 EXAMPLE ===")
    print(calc.format_for_llm(contributions, "💎 Platinum"))
    print(f"\nConfidence: {calc.determine_confidence(contributions)}")
    print(f"Salesforce JSON: {calc.to_salesforce_json(contributions)}")
```

### Unit 4.6.2: LLM Narrative Generator

Uses Claude API to generate natural language narratives from contributions.

```python
# C:\Users\russe\Documents\Lead Scoring\Version-3\inference\narrative_generator.py
"""
LLM-Powered Narrative Generator

Converts rule-based contributions into natural language explanations
that SGAs can read and act on in Salesforce.

Uses Claude API for high-quality, contextual narratives.
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

from contribution_calculator import ContributionCalculator, FeatureContribution

@dataclass
class NarrativeResult:
    """Result of narrative generation for a single lead."""
    lead_id: str
    narrative: str                # Human-readable explanation (2-3 sentences)
    top_factors_json: str         # JSON for Salesforce storage
    tier: str                     # Tier code
    tier_display: str             # Display name with emoji
    confidence: str               # "high", "medium", "low"
    aggregate_score: float        # Sum of contribution scores


class NarrativeGenerator:
    """
    Generates natural language narratives explaining lead prioritization.
    
    Uses Claude API to create conversational explanations based on
    rule-based contributions. Falls back to templates if API unavailable.
    """
    
    SYSTEM_PROMPT = """You are a sales intelligence assistant for Savvy Wealth, a wealth management recruiting firm.

Your job is to write brief, actionable explanations for why a financial advisor is a good recruiting prospect.

Guidelines:
- Write 2-3 sentences maximum
- Be specific about what makes this person a good prospect
- Focus on actionable insights for the SGA (Sales Development Associate)
- Use natural, conversational language
- If there are concerns, acknowledge briefly but emphasize positives
- NEVER mention "tier", "score", or the scoring system
- NEVER use bullet points - write flowing prose
- Focus on the PERSON, not the data"""

    PROMPT_TEMPLATE = """Write a brief explanation for why this financial advisor is worth contacting:

**Advisor Profile:**
- Company: {company}
- Firm Size: {firm_size} advisors
- Time at Current Firm: {tenure_years:.1f} years
- Industry Experience: {experience_years:.0f} years
- Firm Trend: {firm_trend}

**Key Factors:**
{factors_formatted}

Write 2-3 sentences explaining why this is a good prospect and what angle to use in outreach:"""

    def __init__(self, 
                 api_key: str = None,
                 model: str = "claude-sonnet-4-20250514",
                 use_anthropic: bool = True):
        """
        Initialize the narrative generator.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            use_anthropic: If True, use API; if False, use template fallback
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        self.model = model
        self.use_anthropic = use_anthropic and self.api_key is not None
        
        self.contribution_calculator = ContributionCalculator()
        self.client = None
        
        if self.use_anthropic:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                print("[OK] Anthropic client initialized for narrative generation")
            except ImportError:
                print("[WARNING] anthropic package not installed. pip install anthropic")
                print("         Using template-based fallback.")
                self.use_anthropic = False
            except Exception as e:
                print(f"[WARNING] Anthropic init failed: {e}. Using fallback.")
                self.use_anthropic = False
    
    def _format_factors(self, contributions: List[FeatureContribution]) -> str:
        """Format top contributions for the LLM prompt."""
        lines = []
        for c in contributions[:4]:
            emoji = "✅" if c.direction == "positive" else "⚠️" if c.direction == "negative" else "➖"
            lines.append(f"{emoji} {c.explanation}")
        return "\n".join(lines)
    
    def _get_firm_trend(self, net_change: float) -> str:
        """Convert net change to human-readable trend."""
        if net_change < -10:
            return f"Significant outflow ({abs(int(net_change))} advisors left this year)"
        elif net_change < -5:
            return f"Notable turnover ({abs(int(net_change))} net departures)"
        elif net_change < 0:
            return f"Some turnover ({abs(int(net_change))} net departures)"
        elif net_change > 5:
            return f"Growing firm (+{int(net_change)} advisors)"
        else:
            return "Stable"
    
    def _call_llm(self, prompt: str) -> str:
        """Call Claude API for narrative generation."""
        if not self.use_anthropic or not self.client:
            return self._template_fallback(prompt)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"[WARNING] LLM call failed: {e}. Using template fallback.")
            return self._template_fallback(prompt)
    
    def _template_fallback(self, prompt: str = None) -> str:
        """Template-based fallback when LLM is unavailable."""
        return ("This advisor matches our target profile based on firm size, tenure, "
                "and career stage. Their current situation suggests openness to exploring "
                "new opportunities. Consider reaching out to discuss their practice goals.")
    
    def generate_narrative(self, 
                          features: Dict,
                          tier: str,
                          tier_display: str = None,
                          lead_id: str = None) -> NarrativeResult:
        """
        Generate a narrative for a single lead.
        
        Args:
            features: Lead features dict
            tier: Tier code (e.g., "1_PLATINUM")
            tier_display: Display name (e.g., "💎 Platinum")
            lead_id: Optional lead ID for tracking
            
        Returns:
            NarrativeResult with narrative and metadata
        """
        # Calculate contributions
        contributions = self.contribution_calculator.calculate_contributions(features)
        
        # Get feature values
        company = str(features.get('company', '') or features.get('Company', '') or 'Unknown')
        rep_count = float(features.get('firm_rep_count_at_contact', 0) or 0)
        tenure_months = float(features.get('current_firm_tenure_months', 0) or 0)
        industry_months = float(features.get('industry_tenure_months', 0) or 0)
        net_change = float(features.get('firm_net_change_12mo', 0) or 0)
        
        # Build prompt
        prompt = self.PROMPT_TEMPLATE.format(
            company=company,
            firm_size=int(rep_count) if rep_count > 0 else "Unknown",
            tenure_years=tenure_months / 12,
            experience_years=industry_months / 12,
            firm_trend=self._get_firm_trend(net_change),
            factors_formatted=self._format_factors(contributions)
        )
        
        # Generate narrative
        narrative = self._call_llm(prompt)
        
        # Calculate confidence
        confidence = self.contribution_calculator.determine_confidence(contributions)
        aggregate = self.contribution_calculator.calculate_aggregate_score(contributions)
        
        return NarrativeResult(
            lead_id=lead_id or features.get('lead_id', 'unknown'),
            narrative=narrative,
            top_factors_json=self.contribution_calculator.to_salesforce_json(contributions),
            tier=tier,
            tier_display=tier_display or tier,
            confidence=confidence,
            aggregate_score=aggregate
        )
    
    def generate_batch(self, 
                      leads_df,
                      tier_column: str = 'score_tier',
                      tier_display_column: str = 'tier_display',
                      batch_size: int = 50,
                      rate_limit_delay: float = 0.1) -> List[Dict]:
        """
        Generate narratives for a batch of leads.
        
        Args:
            leads_df: DataFrame with leads to narrate
            tier_column: Column name for tier
            tier_display_column: Column name for tier display
            batch_size: Max leads to process
            rate_limit_delay: Seconds between API calls
            
        Returns:
            List of dicts ready for Salesforce sync
        """
        import time
        
        results = []
        total = min(len(leads_df), batch_size)
        
        print(f"Generating narratives for {total} leads...")
        
        for idx, (_, row) in enumerate(leads_df.head(batch_size).iterrows()):
            try:
                result = self.generate_narrative(
                    features=row.to_dict(),
                    tier=row.get(tier_column, 'UNKNOWN'),
                    tier_display=row.get(tier_display_column, None),
                    lead_id=row.get('lead_id', str(idx))
                )
                
                results.append({
                    'lead_id': result.lead_id,
                    'Lead_Score_Narrative__c': result.narrative,
                    'Lead_Score_Factors__c': result.top_factors_json,
                    'Lead_Score_Confidence__c': result.confidence,
                    'Lead_Score_Tier__c': result.tier,
                    'Lead_Tier_Display__c': result.tier_display
                })
                
                # Progress indicator
                if (idx + 1) % 10 == 0:
                    print(f"  Processed {idx + 1}/{total} leads")
                
                # Rate limiting for API
                if self.use_anthropic and rate_limit_delay > 0:
                    time.sleep(rate_limit_delay)
                    
            except Exception as e:
                print(f"[WARNING] Failed to generate narrative for row {idx}: {e}")
                results.append({
                    'lead_id': row.get('lead_id', str(idx)),
                    'Lead_Score_Narrative__c': 'Narrative generation failed',
                    'Lead_Score_Factors__c': '[]',
                    'Lead_Score_Confidence__c': 'low',
                    'Lead_Score_Tier__c': row.get(tier_column, 'UNKNOWN'),
                    'Lead_Tier_Display__c': row.get(tier_display_column, 'Unknown')
                })
        
        print(f"[OK] Generated {len(results)} narratives")
        return results


# Example usage
if __name__ == "__main__":
    generator = NarrativeGenerator()
    
    example_lead = {
        'lead_id': 'LEAD-001',
        'company': 'Apex Wealth Advisors',
        'firm_rep_count_at_contact': 8,
        'current_firm_tenure_months': 72,   # 6 years
        'industry_tenure_months': 180,      # 15 years
        'firm_net_change_12mo': -7
    }
    
    result = generator.generate_narrative(
        features=example_lead,
        tier='1_PLATINUM',
        tier_display='💎 Platinum'
    )
    
    print("="*60)
    print("NARRATIVE RESULT")
    print("="*60)
    print(f"Tier: {result.tier_display}")
    print(f"Confidence: {result.confidence}")
    print(f"Aggregate Score: {result.aggregate_score:.2f}")
    print()
    print("NARRATIVE:")
    print(result.narrative)
    print()
    print("FACTORS JSON:")
    print(result.top_factors_json)
```

### Unit 4.6.3: Salesforce Integration for Narratives

**New Salesforce Fields Required:**

| API Name | Label | Type | Length | Description |
|----------|-------|------|--------|-------------|
| `Lead_Score_Narrative__c` | Score Narrative | Long Text | 500 | LLM-generated explanation |
| `Lead_Score_Factors__c` | Score Factors | Long Text | 1000 | JSON of top contributing factors |
| `Lead_Score_Confidence__c` | Score Confidence | Picklist | - | Values: high, medium, low |

**Updated Salesforce Sync Query:**

```sql
-- Generate Salesforce update payloads with narratives
SELECT 
    lead_id as Id,
    score_tier as Lead_Score_Tier__c,
    tier_display as Lead_Tier_Display__c,
    lead_score as Lead_Score__c,
    action_recommended as Lead_Action__c,
    
    -- Narrative fields (populated by Python narrative_generator.py)
    -- These are added in a second pass after scoring
    -- narrative as Lead_Score_Narrative__c,
    -- top_factors_json as Lead_Score_Factors__c,
    -- confidence as Lead_Score_Confidence__c,
    
    'v3-hybrid-20251221' as Lead_Model_Version__c,
    CURRENT_TIMESTAMP() as Lead_Score_Timestamp__c
FROM scored_leads_v3
WHERE score_tier IN ('1_PLATINUM', '2_DANGER_ZONE', '3_SILVER')
```

**Python Integration:**

```python
# In weekly_list_generator.py or salesforce_sync.py

from narrative_generator import NarrativeGenerator

def enrich_with_narratives(scored_df, top_n: int = 100):
    """
    Add LLM narratives to top N scored leads.
    
    Only generates narratives for top leads to manage API costs.
    """
    generator = NarrativeGenerator()
    
    # Get top leads by tier priority
    top_leads = scored_df[
        scored_df['score_tier'].isin(['1_PLATINUM', '2_DANGER_ZONE'])
    ].head(top_n)
    
    # Generate narratives
    narratives = generator.generate_batch(top_leads, batch_size=top_n)
    
    # Merge back
    narrative_df = pd.DataFrame(narratives)
    enriched = scored_df.merge(
        narrative_df[['lead_id', 'Lead_Score_Narrative__c', 'Lead_Score_Factors__c', 'Lead_Score_Confidence__c']],
        on='lead_id',
        how='left'
    )
    
    return enriched
```

### Unit 4.6.4: Example Narratives

**Tier 1 (Platinum) Example:**

> "This advisor at Apex Wealth (8-person firm) has built their practice over 15 years and spent the last 6 establishing their current book. As an independent without corporate ties, they have full portability. The firm's recent turnover suggests some internal instability that could make them receptive to discussing alternatives."

**Tier 2 (Danger Zone) Example:**

> "With only 18 months at their current firm and 12 colleagues departing this year, this veteran advisor (20+ years) may be questioning their recent move. The firm's instability creates an opening to discuss whether Savvy's platform better aligns with their practice goals."

### Validation Gates

| Gate ID | Check | Pass Criteria | Result |
|---------|-------|---------------|--------|
| G4.6.1 | ContributionCalculator tested | All rules produce expected contributions | ⏳ |
| G4.6.2 | LLM API connected | Anthropic API responds successfully | ⏳ |
| G4.6.3 | Narratives generated | 50 sample narratives are coherent | ⏳ |
| G4.6.4 | Salesforce fields created | All 3 narrative fields exist on Lead | ⏳ |
| G4.6.5 | Batch performance | 100 narratives in < 2 minutes | ⏳ |

---

> **📝 LOG CHECKPOINT**
> 
> Before proceeding to Phase 5, review the execution log:
> `C:\Users\russe\Documents\Lead Scoring\Version-3\EXECUTION_LOG.md`
> 
> Verify:
> - [ ] ContributionCalculator produces expected results
> - [ ] NarrativeGenerator connects to Claude API
> - [ ] Sample narratives are high-quality
> - [ ] Salesforce custom fields created
> - [ ] API costs estimated for production volume

---
```

---

# PROMPT 7: Update Log Entry Template for V3

**Instructions for Cursor:**

In `@leadscoring_plan.md`, update the Log Entry Template (around lines 103-140) to reflect V3 context.

**Replace the Log Entry Template with:**

```markdown
### Log Entry Template

Each phase should append an entry using this exact format:

```markdown
---

## Phase [X.X]: [Phase Name]

**Executed:** [YYYY-MM-DD HH:MM]
**Duration:** [X minutes]
**Status:** [✅ PASSED / ⚠️ PASSED WITH WARNINGS / ❌ FAILED]

### What We Did
[Bullet points of actions taken]

### Files Created
| File | Path | Purpose |
|------|------|---------|
| [name] | `Version-3/[path]` | [description] |

### Tier Performance (if applicable)
| Tier | Volume | Conv Rate | Lift | Status |
|------|--------|-----------|------|--------|
| 1_PLATINUM | [n] | [x.xx%] | [x.xx]x | [✅/⚠️/❌] |
| 2_DANGER_ZONE | [n] | [x.xx%] | [x.xx]x | [✅/⚠️/❌] |

### Validation Gates
| Gate ID | Check | Result | Notes |
|---------|-------|--------|-------|
| [id] | [check] | [✅/⚠️/❌] | [notes] |

### Key Metrics
[Relevant numbers from this phase]

### What We Learned
[Insights, surprises, issues discovered]

### Decisions Made
[Any decisions and rationale]

### Next Steps
[What needs to happen in the next phase]

---
```
```

---

# PROMPT 8: Clean Up Duplicate Monitoring Sections

**Instructions for Cursor:**

In `@leadscoring_plan.md`, there are duplicate monitoring sections at the end of the document. One is the V3 "Production Monitoring" section and there's also an older "Monthly Monitoring Checklist".

**Find the duplicate sections around lines 11095-11150 and consolidate into one clean V3 monitoring section.**

The final monitoring section should be titled:

```markdown
## Production Monitoring (V3)
```

And should include:
1. Daily/Weekly/Monthly metrics dashboard
2. Signal Decay Detection (from our investigation learnings)
3. Root Cause Playbook
4. Recalibration Triggers

**Remove the duplicate "Monthly Monitoring Checklist" that references "Top decile" and "Feature Drift Detection" (these are V2 XGBoost concepts).**

---

# PROMPT 9: Update Validation Gate Summary for V3

**Instructions for Cursor:**

In `@leadscoring_plan.md`, there's a "Comprehensive Validation Gate Summary" section that may still reference XGBoost gates.

**Update this section to reflect V3 gates including narrative generation:**

```markdown
---

## Comprehensive Validation Gate Summary (V3)

### 🔴 BLOCKING Gates (Must Pass to Continue)

| Phase | Gate ID | Check | Pass Criteria |
|-------|---------|-------|---------------|
| -2 | G-2.1.1 | Root Cause Identified | Signal decay explained |
| -2 | G-2.2.1 | Alternative Validated | SGA Platinum ≥ 2.5x lift |
| 4 | G4.1.1 | Tier 1 Criteria Validated | Historical lift ≥ 2.4x |
| 4 | G4.1.2 | Tier 2 Criteria Validated | Historical lift ≥ 2.0x |
| 4 | G4.2.1 | Wirehouse List Complete | Covers major brokerages |
| 4.6 | G4.6.1 | Contribution Calculator | Rules produce expected contributions |
| 4.6 | G4.6.2 | LLM API Connected | Claude API responds |
| 4.6 | G4.6.3 | Narratives Quality | Sample narratives are coherent |
| 5 | G5.1.1 | Tier 1 Lift | ≥ 2.4x on validation data |
| 5 | G5.1.2 | Tier 2 Lift | ≥ 2.0x on validation data |
| 8 | G8.4.1 | Holdout Tier 1 Lift | ≥ 2.4x on holdout period |

### 🟡 WARNING Gates (Review Required)

| Phase | Gate ID | Check | Pass Criteria |
|-------|---------|-------|---------------|
| 5 | G5.1.3 | Combined Top 2 Volume | ≥ 1,500 leads per batch |
| 5 | G5.2.1 | LinkedIn Tier 1 Lift | ≥ 3.0x (channel advantage) |
| 6 | G6.3.1 | Calibration Drift | All tiers within 0.5% of expected |
| 8 | G8.2.1 | Pool Depletion | Volume drop < 30%/quarter |

### 🟢 INFORMATIONAL Gates (Log and Continue)

| Phase | Gate ID | Check | Expected |
|-------|---------|-------|----------|
| 4.5 | G4.5.1 | LinkedIn List Generated | 50 Tier 1 leads/week |
| 4.5 | G4.5.2 | Cold Call List Generated | 200 Tier 2-3 leads/week |
| 4.6 | G4.6.4 | Salesforce Narrative Fields | 3 custom fields created |
| 4.6 | G4.6.5 | Batch Narrative Performance | 100 narratives in < 2 min |
| 7 | G7.1.1 | Scheduled Query Running | Daily at 6 AM |
| 7 | G7.2.1 | Salesforce Sync | ≥ 95% success rate |

---
```

---

# PROMPT 10: Update Document Footer and Version

**Instructions for Cursor:**

In `@leadscoring_plan.md`, update the footer section at the very end of the document:

**Replace the current footer with:**

```markdown
---

*Document Version: 3.0*  
*Last Updated: December 21, 2025*  
*Model Version: v3-hybrid-20251221*  
*Model Type: Two-Tier Hybrid Query + LLM Narratives*

---

## Quick Reference

### File Locations

| Component | Path |
|-----------|------|
| **Plan Document** | `C:\Users\russe\Documents\Lead Scoring\Version-3\leadscoring_plan.md` |
| **Execution Log** | `C:\Users\russe\Documents\Lead Scoring\Version-3\EXECUTION_LOG.md` |
| **Main SQL Query** | `C:\Users\russe\Documents\Lead Scoring\Version-3\sql\lead_scoring_v3.sql` |
| **Python Scorer** | `C:\Users\russe\Documents\Lead Scoring\Version-3\inference\lead_scorer_v3.py` |
| **Contribution Calculator** | `C:\Users\russe\Documents\Lead Scoring\Version-3\inference\contribution_calculator.py` |
| **Narrative Generator** | `C:\Users\russe\Documents\Lead Scoring\Version-3\inference\narrative_generator.py` |
| **Weekly Reports** | `C:\Users\russe\Documents\Lead Scoring\Version-3\reports\weekly\` |

### BigQuery Tables

| Table | Purpose |
|-------|---------|
| `ml_features.lead_scoring_features` | Base features (11 columns) |
| `ml_features.lead_scores_v3_current` | Current scored leads view |
| `ml_features.lead_scores_v3_daily` | Daily scored leads (partitioned) |

### Salesforce Fields

| Field | Type | Purpose |
|-------|------|---------|
| `Lead_Score_Tier__c` | Picklist | Tier code (1_PLATINUM, 2_DANGER_ZONE, etc.) |
| `Lead_Tier_Display__c` | Text | Display name (💎 Platinum, etc.) |
| `Lead_Score__c` | Number | Numeric score (0-100) |
| `Lead_Score_Narrative__c` | Long Text (500) | LLM-generated explanation for SGA |
| `Lead_Score_Factors__c` | Long Text (1000) | JSON of top contributing factors |
| `Lead_Score_Confidence__c` | Picklist | high/medium/low confidence level |

### Tier Quick Reference

| Tier | Criteria | Expected Lift | Volume |
|------|----------|---------------|--------|
| 💎 Platinum | Small (≤10) + Sweet Spot (4-10yr) + Exp (8-30yr) + Not WH | 2.55x | ~1,600 |
| 🥇 Gold | DZ (1-2yr) + Bleeding (<-5) + Veteran (10yr+) | 2.33x | ~350 |
| 🥈 Silver | DZ + Not Wirehouse | ~2.2x | ~3,600 |
| 🥉 Bronze | DZ only | ~2.0x | ~740 |
| ⚪ Standard | No signals | 1.0x | Rest |

### Weekly Operations

1. **Monday:** Run weekly scoring query, generate SGA priority lists
2. **Tuesday:** Run narrative generation for top 100 leads (Tier 1 + 2)
3. **Wednesday:** Push scores + narratives to Salesforce
4. **Thursday-Friday:** SGAs work lists, reference narratives in outreach
5. **Friday EOD:** Log weekly conversion outcomes for monitoring

### Narrative Example

**In Salesforce, SGAs will see:**

> **Score:** 💎 Platinum (Confidence: High)
> 
> **Why This Lead:**  
> "This advisor at Apex Wealth (8-person firm) has built their practice over 15 years and spent the last 6 establishing their current book. As an independent without corporate ties, they have full portability. The firm's recent turnover suggests some internal instability that could make them receptive to discussing alternatives."
>
> **Key Factors:**
> - ✅ Small firm (8 advisors) - portable book
> - ✅ Sweet spot tenure (6 years)
> - ✅ Prime experience (15 years)
> - ✅ Independent firm - no golden handcuffs

---
```

---

# Execution Checklist

After running all 10 prompts, verify:

- [ ] All paths reference `Version-3` (not `Version-2`)
- [ ] No `BaselineXGBoostTrainer` class remains
- [ ] No `XGBoostOptimizer` class remains
- [ ] No `ProbabilityCalibrator` class remains  
- [ ] No `ModelPackager` class remains
- [ ] No old `LeadScorer` or `BatchScorerJob` classes remain
- [ ] **NEW Phase 4.6 added** with ContributionCalculator and NarrativeGenerator
- [ ] No duplicate Phase 5 headers
- [ ] No duplicate monitoring sections
- [ ] Validation gates include narrative generation gates (G4.6.x)
- [ ] Log entry template references Version-3
- [ ] Footer includes narrative generator in file locations
- [ ] Salesforce fields include all 3 narrative fields
- [ ] Document flows cleanly from Phase to Phase

---

## Bonus: Create Version-3 Directory Structure

After updating the plan, run this script to create the actual directory structure:

```python
"""
create_v3_directory.py
Creates the Version-3 directory structure for lead scoring development.
Run this ONCE after updating the plan.
"""

from pathlib import Path
import json
from datetime import datetime

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-3")

# Create directories
directories = [
    BASE_DIR,
    BASE_DIR / "utils",
    BASE_DIR / "data" / "raw",
    BASE_DIR / "data" / "validation",
    BASE_DIR / "data" / "scored",
    BASE_DIR / "sql",
    BASE_DIR / "reports" / "weekly",
    BASE_DIR / "inference",
    BASE_DIR / "config",
]

for d in directories:
    d.mkdir(parents=True, exist_ok=True)
    print(f"Created: {d}")

# Create placeholder files
(BASE_DIR / "utils" / "__init__.py").write_text('"""V3 Lead Scoring Utilities"""\n')

(BASE_DIR / "EXECUTION_LOG.md").write_text(f"""# V3 Execution Log

**Started:** {datetime.now().isoformat()}
**Model Version:** v3-hybrid-20251221

---

## Log Entries

(Phases will append entries below)

---
""")

(BASE_DIR / "tier_config.json").write_text(json.dumps({
    "version": "v3-hybrid-20251221",
    "created_at": datetime.now().isoformat(),
    "tiers": {
        "1_PLATINUM": {
            "criteria": "Small firm (≤10) + Sweet Spot (4-10yr) + Exp (8-30yr) + Not WH",
            "expected_lift": 2.55,
            "expected_conversion": 0.0215
        },
        "2_DANGER_ZONE": {
            "criteria": "DZ (1-2yr) + Bleeding (<-5) + Veteran (10yr+)",
            "expected_lift": 2.33,
            "expected_conversion": 0.0197
        }
    },
    "narrative_config": {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 200,
        "batch_size": 100,
        "rate_limit_delay_seconds": 0.1
    }
}, indent=2))

(BASE_DIR / "config" / "wirehouse_patterns.json").write_text(json.dumps({
    "version": "1.0",
    "updated": datetime.now().isoformat(),
    "patterns": [
        "MERRILL", "MORGAN STANLEY", "UBS", "WELLS FARGO",
        "EDWARD JONES", "RAYMOND JAMES", "LPL FINANCIAL",
        "NORTHWESTERN MUTUAL", "MASS MUTUAL", "MASSMUTUAL",
        "PRUDENTIAL", "AMERIPRISE", "FIDELITY", "SCHWAB",
        "VANGUARD", "FISHER INVESTMENTS", "CREATIVE PLANNING",
        "EDELMAN", "FIRST COMMAND", "CETERA", "COMMONWEALTH",
        "CAMBRIDGE", "STIFEL", "JANNEY", "BAIRD", "PIPER SANDLER"
    ],
    "notes": "Firms with 'golden handcuffs' - deferred comp locks advisors in. Review quarterly with SGA team."
}, indent=2))

(BASE_DIR / "config" / "narrative_prompts.json").write_text(json.dumps({
    "version": "1.0",
    "system_prompt": "You are a sales intelligence assistant for Savvy Wealth...",
    "user_template": "Write a brief explanation for why this financial advisor is worth contacting...",
    "notes": "See narrative_generator.py for full prompts"
}, indent=2))

print("\n✅ Version-3 directory structure created!")
print(f"Base: {BASE_DIR}")
print("\nNext steps:")
print("1. Copy contribution_calculator.py to inference/")
print("2. Copy narrative_generator.py to inference/")
print("3. Set ANTHROPIC_API_KEY environment variable")
print("4. Test with: python inference/narrative_generator.py")
```

---

*Cleanup prompts generated: December 21, 2025*
*For finalizing leadscoring_plan.md transition to V3*
*Includes: Rule-based contributions + LLM narrative generation (Claude API)*
