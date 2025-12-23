"""
Phase 1.2: Feature Catalog Documentation
Comprehensive documentation of all features for audit and governance
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Optional
from enum import Enum
from pathlib import Path

class PITStatus(Enum):
    FULL_PIT = "FULL_PIT"  # Can calculate exactly as of contacted_date
    PARTIAL_PIT = "PARTIAL_PIT"  # Can approximate but not exact
    CURRENT_ONLY = "CURRENT_ONLY"  # Only current state available

class LeakageRisk(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

@dataclass
class FeatureDefinition:
    name: str
    data_type: str
    source_tables: List[str]
    pit_status: PITStatus
    expected_direction: str  # "positive", "negative", "nonlinear"
    business_logic: str
    null_handling: str
    leakage_risk: LeakageRisk
    category: str
    is_model_feature: bool = True
    notes: Optional[str] = None

# Define complete feature catalog based on actual table structure
FEATURE_CATALOG = [
    # ==================== IDENTIFIERS (Not Model Features) ====================
    FeatureDefinition(
        name="lead_id",
        data_type="STRING",
        source_tables=["SavvyGTMData.Lead"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="none",
        business_logic="Salesforce Lead ID - primary identifier",
        null_handling="Required - no nulls",
        leakage_risk=LeakageRisk.LOW,
        category="identifier",
        is_model_feature=False
    ),
    FeatureDefinition(
        name="advisor_crd",
        data_type="INT64",
        source_tables=["SavvyGTMData.Lead"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="none",
        business_logic="Advisor CRD number - identifier",
        null_handling="Required - no nulls",
        leakage_risk=LeakageRisk.LOW,
        category="identifier",
        is_model_feature=False
    ),
    FeatureDefinition(
        name="contacted_date",
        data_type="DATE",
        source_tables=["SavvyGTMData.Lead"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="none",
        business_logic="Date lead entered 'Contacting' stage - temporal anchor",
        null_handling="Required - no nulls",
        leakage_risk=LeakageRisk.LOW,
        category="identifier",
        is_model_feature=False
    ),
    FeatureDefinition(
        name="firm_crd_at_contact",
        data_type="INT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="none",
        business_logic="Firm CRD at contacted_date (Gap Tolerant - Last Known Value)",
        null_handling="Required - no nulls",
        leakage_risk=LeakageRisk.LOW,
        category="identifier",
        is_model_feature=False
    ),
    
    # ==================== GAP TOLERANT FEATURES ====================
    FeatureDefinition(
        name="days_in_gap",
        data_type="INT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="positive",
        business_logic="Days between job end date and contacted_date. 0 = no gap (active employment). Positive = advisor in employment gap. Higher values may indicate transition period = opportunity.",
        null_handling="Default to 0",
        leakage_risk=LeakageRisk.LOW,
        category="gap_tolerant",
        notes="NEW: Gap-tolerant logic recovers ~63% of leads. This feature captures employment transition periods."
    ),
    
    # ==================== ADVISOR FEATURES ====================
    FeatureDefinition(
        name="industry_tenure_months",
        data_type="INT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="nonlinear",
        business_logic="Total months in industry calculated from employment history end dates. Very long tenure may indicate less mobility.",
        null_handling="Impute with median, create indicator for missing",
        leakage_risk=LeakageRisk.LOW,
        category="advisor_experience"
    ),
    FeatureDefinition(
        name="num_prior_firms",
        data_type="INT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="positive",
        business_logic="Count of firms worked at before current. Higher mobility may indicate openness to change.",
        null_handling="Default to 0",
        leakage_risk=LeakageRisk.LOW,
        category="advisor_mobility"
    ),
    FeatureDefinition(
        name="current_firm_tenure_months",
        data_type="INT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="negative",
        business_logic="Months at current firm as of contact. Very long tenure may indicate low mobility. For gap cases, represents tenure at last known firm.",
        null_handling="Impute with 0, flag as missing",
        leakage_risk=LeakageRisk.LOW,
        category="advisor_stability"
    ),
    
    # ==================== MOBILITY FEATURES (VALIDATED) ====================
    FeatureDefinition(
        name="pit_moves_3yr",
        data_type="INT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="positive",
        business_logic="Count of firm changes in 36 months prior to contact. VALIDATED: Advisors with 3+ moves have 11% conversion vs 3% baseline (3.8x lift). Top predictor alongside Firm Net Change.",
        null_handling="Default to 0",
        leakage_risk=LeakageRisk.LOW,
        category="advisor_mobility",
        notes="HIGH PRIORITY SIGNAL - Validated in Rep Mobility analysis"
    ),
    FeatureDefinition(
        name="pit_mobility_tier",
        data_type="STRING",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="nonlinear",
        business_logic="Categorical mobility classification: 'Highly Mobile' (3+ moves in 3yr, 11% conversion), 'Mobile' (2 moves), 'Average' (1 move), 'Stable' (0 moves). VALIDATED: Highly Mobile tier has 3.8x lift over baseline.",
        null_handling="Assign 'Unknown' category",
        leakage_risk=LeakageRisk.LOW,
        category="advisor_mobility",
        notes="HIGH PRIORITY SIGNAL - Categorical version of pit_moves_3yr. One-hot encode for model."
    ),
    
    # ==================== FIRM FEATURES ====================
    FeatureDefinition(
        name="firm_aum_pit",
        data_type="INT64",
        source_tables=["Firm_historicals"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="nonlinear",
        business_logic="Firm AUM as of pit_month (month before contacted_date). Large firms may be harder to recruit from, but also have more resources.",
        null_handling="Impute with median, create indicator",
        leakage_risk=LeakageRisk.LOW,
        category="firm_size"
    ),
    FeatureDefinition(
        name="firm_rep_count_at_contact",
        data_type="INT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="nonlinear",
        business_logic="Number of advisors at firm as of contacted_date, calculated from employment history. Larger firms may have more turnover opportunities.",
        null_handling="Impute with median",
        leakage_risk=LeakageRisk.LOW,
        category="firm_size"
    ),
    FeatureDefinition(
        name="aum_growth_since_jan2024_pct",
        data_type="FLOAT64",
        source_tables=["Firm_historicals"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="negative",
        business_logic="AUM growth from Jan 2024 baseline to pit_month. Declining AUM may indicate distress = opportunity. **Note:** Due to limited history (Jan 2024+), this replaces the 12-month growth metric.",
        null_handling="Impute with 0 (no growth)",
        leakage_risk=LeakageRisk.LOW,
        category="firm_growth",
        notes="Replaces aum_growth_12mo_pct due to limited historical data"
    ),
    
    # ==================== FIRM STABILITY FEATURES (KEY PREDICTORS) ====================
    FeatureDefinition(
        name="firm_net_change_12mo",
        data_type="INT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="negative",
        business_logic="Net change in advisors at firm (arrivals - departures) in 12 months before contact. Negative = bleeding talent = opportunity. VALIDATED: Most predictive feature alongside pit_moves_3yr.",
        null_handling="Impute with 0",
        leakage_risk=LeakageRisk.LOW,
        category="firm_stability",
        notes="HIGH PRIORITY SIGNAL - Empirically validated as top predictor"
    ),
    FeatureDefinition(
        name="firm_stability_score",
        data_type="FLOAT64",
        source_tables=["contact_registered_employment_history"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="negative",
        business_logic="Derived stability score: 50 + (net_change_12mo * 3.5), clamped to 0-100. Lower scores indicate more instability = higher opportunity. Empirically validated formula.",
        null_handling="Impute with 50 (neutral)",
        leakage_risk=LeakageRisk.LOW,
        category="firm_stability",
        notes="Derived from firm_net_change_12mo using validated formula"
    ),
    
    # ==================== TARGET VARIABLE ====================
    FeatureDefinition(
        name="target",
        data_type="INT64",
        source_tables=["SavvyGTMData.Lead"],
        pit_status=PITStatus.FULL_PIT,
        expected_direction="none",
        business_logic="Binary target: 1 = converted to MQL within 30 days, 0 = mature lead never converted. NULL = right-censored (excluded from training).",
        null_handling="Exclude NULLs from training",
        leakage_risk=LeakageRisk.LOW,
        category="target",
        is_model_feature=False
    ),
]

def generate_feature_catalog_json(output_path: str = "feature_catalog.json"):
    """Generate JSON feature catalog"""
    # Convert features to dicts, handling enums
    features_list = []
    for f in FEATURE_CATALOG:
        feature_dict = asdict(f)
        # Convert enums to their values
        feature_dict['pit_status'] = f.pit_status.value
        feature_dict['leakage_risk'] = f.leakage_risk.value
        features_list.append(feature_dict)
    
    catalog_dict = {
        'features': features_list,
        'metadata': {
            'total_features': len([f for f in FEATURE_CATALOG if f.is_model_feature]),
            'gap_tolerant_features': len([f for f in FEATURE_CATALOG if 'gap' in f.category]),
            'high_priority_signals': len([f for f in FEATURE_CATALOG if 'HIGH PRIORITY' in (f.notes or '')]),
            'version': '1.1',
            'date_created': '2024-12-19'
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(catalog_dict, f, indent=2)
    
    print(f"[OK] Feature catalog JSON saved to: {output_path}")
    return catalog_dict

def generate_feature_catalog_markdown(output_path: str = "FEATURE_CATALOG.md"):
    """Generate Markdown feature catalog documentation"""
    
    md_content = """# Lead Scoring Feature Catalog

## Overview

This catalog documents all features engineered for the lead scoring model using Point-in-Time (PIT) methodology with Gap-Tolerant logic.

**Key Updates:**
- **Gap-Tolerant Logic:** Recovers ~63% of leads by using "Last Known Value" for employment records
- **Date Floor:** Training data filtered to `contacted_date >= '2024-02-01'` to ensure valid firm historicals
- **Limited History:** AUM growth uses Jan 2024 baseline instead of 12-month lookback

## Feature Categories

"""
    
    # Group by category
    categories = {}
    for feature in FEATURE_CATALOG:
        cat = feature.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(feature)
    
    for category, features in categories.items():
        md_content += f"\n### {category.replace('_', ' ').title()}\n\n"
        
        for feature in features:
            if feature.is_model_feature:
                md_content += f"#### `{feature.name}`\n\n"
                md_content += f"- **Type:** {feature.data_type}\n"
                md_content += f"- **Source:** {', '.join(feature.source_tables)}\n"
                md_content += f"- **PIT Status:** {feature.pit_status.value}\n"
                md_content += f"- **Expected Direction:** {feature.expected_direction}\n"
                md_content += f"- **Leakage Risk:** {feature.leakage_risk.value}\n"
                md_content += f"- **Business Logic:** {feature.business_logic}\n"
                md_content += f"- **Null Handling:** {feature.null_handling}\n"
                if feature.notes:
                    md_content += f"- **Notes:** {feature.notes}\n"
                md_content += "\n"
    
    md_content += """
## High Priority Signals

The following features have been empirically validated as top predictors:

1. **pit_moves_3yr** - 3.8x lift for advisors with 3+ moves in 3 years
2. **firm_net_change_12mo** - Most predictive feature alongside mobility
3. **pit_mobility_tier** - Categorical version with validated thresholds

## Gap-Tolerant Features

The following features leverage the new "Last Known Value" logic:

- **days_in_gap** - Captures employment transition periods
- **firm_crd_at_contact** - Uses most recent employment record
- **current_firm_tenure_months** - For gap cases, represents tenure at last known firm

## Null Signal Features

Note: The simplified remediation table does not include all null signal features from the full pipeline. These would be added in the complete implementation:
- is_gender_missing
- is_linkedin_missing
- is_personal_email_missing
- is_license_data_missing
- is_industry_tenure_missing

"""
    
    with open(output_path, 'w') as f:
        f.write(md_content)
    
    print(f"[OK] Feature catalog Markdown saved to: {output_path}")

if __name__ == "__main__":
    print("Generating Feature Catalog...")
    print(f"Total features defined: {len(FEATURE_CATALOG)}")
    print(f"Model features: {len([f for f in FEATURE_CATALOG if f.is_model_feature])}")
    
    # Generate JSON
    catalog_json = generate_feature_catalog_json()
    
    # Generate Markdown
    generate_feature_catalog_markdown()
    
    print("\n[OK] Feature Catalog Generation Complete!")
    print(f"   - JSON: feature_catalog.json")
    print(f"   - Markdown: FEATURE_CATALOG.md")

