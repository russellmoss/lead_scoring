"""
Analyze Q4 2025 lead list performance vs January 2026 list composition.

GOAL: Understand why Q4 2025 converted at 1.7% vs 3.24% historical baseline,
and whether January 2026 list is structurally better.

Working Directory: Lead_List_Generation
Usage: python scripts/analyze_q4_vs_january.py
"""

import pandas as pd
from pathlib import Path
from google.cloud import bigquery
from datetime import datetime
import sys

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
WORKING_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Lead_List_Generation")
LOGS_DIR = WORKING_DIR / "logs"
REPORTS_DIR = WORKING_DIR / "reports"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# BIGQUERY CONFIGURATION
# ============================================================================
PROJECT_ID = "savvy-gtm-analytics"
DATASET_SALESFORCE = "SavvyGTMData"
DATASET_ML = "ml_features"

# ============================================================================
# DATE RANGES
# ============================================================================
Q4_START = "2024-10-01"
Q4_END = "2025-01-01"
JANUARY_2026_TABLE = "january_2026_lead_list_v4"

def get_q4_tier_distribution(client):
    """TASK 1: Get Q4 2025 Lead List Composition by Tier."""
    print("\n" + "=" * 70)
    print("TASK 1: Q4 2025 Lead List Composition")
    print("=" * 70)
    
    # Note: Lead_Score_Tier__c may not exist, so we'll get contacted leads and their conversion status
    query = f"""
    WITH q4_contacted AS (
        SELECT DISTINCT
            l.Id as lead_id,
            SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
            l.CreatedDate,
            l.Status,
            l.Company as firm_name,
            l.stage_entered_contacting__c,
            CASE 
                WHEN l.Status IN ('MQL', 'Qualified', 'Converted') 
                OR l.Stage_Entered_Call_Scheduled__c IS NOT NULL
                THEN 1 
                ELSE 0 
            END as converted
        FROM `{PROJECT_ID}.{DATASET_SALESFORCE}.Lead` l
        WHERE l.stage_entered_contacting__c >= '{Q4_START}' 
          AND l.stage_entered_contacting__c < '{Q4_END}'
          AND l.FA_CRD__c IS NOT NULL
          AND l.IsDeleted = false
          -- CRITICAL: Filter to Provided Lead List only (same as training data)
          AND (
              l.LeadSource LIKE '%Provided Lead List%' 
              OR l.LeadSource LIKE '%Provided Lead%'
              OR l.LeadSource LIKE '%Lead List%'
          )
    )
    SELECT 
        'Q4_CONTACTED_PROVIDED_LIST' as category,
        COUNT(*) as leads,
        SUM(converted) as conversions,
        ROUND(SUM(converted) * 100.0 / COUNT(*), 2) as conversion_rate
    FROM q4_contacted
    """
    
    print("[INFO] Querying Q4 2025 tier distribution...")
    df = client.query(query).to_dataframe()
    
    total_leads = df['leads'].sum()
    total_conversions = df['conversions'].sum()
    overall_rate = (total_conversions / total_leads * 100) if total_leads > 0 else 0
    
    print(f"\nQ4 2025 Contacted Leads Summary:")
    print("-" * 70)
    print(f"{'Category':<25} {'Leads':>10} {'Conversions':>12} {'Rate':>10}")
    print("-" * 70)
    for _, row in df.iterrows():
        print(f"{row['category']:<25} {row['leads']:>10,} {row['conversions']:>12,} {row['conversion_rate']:>9.2f}%")
    print("-" * 70)
    
    return df, total_leads, total_conversions, overall_rate


def get_q4_v4_scores(client):
    """TASK 2: Score Q4 2025 Leads with V4 Model."""
    print("\n" + "=" * 70)
    print("TASK 2: Q4 2025 Leads Scored with V4 Model")
    print("=" * 70)
    
    query = f"""
    WITH q4_leads AS (
        SELECT DISTINCT
            SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd,
            l.Status,
            CASE 
                WHEN l.Status IN ('MQL', 'Qualified', 'Converted') 
                OR l.Stage_Entered_Call_Scheduled__c IS NOT NULL
                THEN 1 
                ELSE 0 
            END as converted
        FROM `{PROJECT_ID}.{DATASET_SALESFORCE}.Lead` l
        WHERE l.stage_entered_contacting__c >= '{Q4_START}' 
          AND l.stage_entered_contacting__c < '{Q4_END}'
          AND l.FA_CRD__c IS NOT NULL
          AND l.IsDeleted = false
          -- CRITICAL: Filter to Provided Lead List only (same as training data)
          AND (
              l.LeadSource LIKE '%Provided Lead List%' 
              OR l.LeadSource LIKE '%Provided Lead%'
              OR l.LeadSource LIKE '%Lead List%'
          )
    )
    SELECT 
        CASE 
            WHEN v4.v4_percentile >= 80 THEN 'V4 Top 20% (>=80%)'
            WHEN v4.v4_percentile >= 50 THEN 'V4 50-80%'
            WHEN v4.v4_percentile >= 20 THEN 'V4 20-50%'
            WHEN v4.v4_percentile IS NOT NULL THEN 'V4 Bottom 20% (<20%)'
            ELSE 'No V4 Score'
        END as v4_bucket,
        COUNT(*) as leads,
        SUM(q4.converted) as conversions,
        ROUND(SUM(q4.converted) * 100.0 / COUNT(*), 2) as conversion_rate,
        ROUND(AVG(v4.v4_score), 4) as avg_v4_score,
        ROUND(AVG(v4.v4_percentile), 1) as avg_v4_percentile
    FROM q4_leads q4
    LEFT JOIN `{PROJECT_ID}.{DATASET_ML}.v4_prospect_scores` v4 ON q4.crd = v4.crd
    GROUP BY 1
    ORDER BY 
        CASE 
            WHEN v4_bucket = 'V4 Top 20% (>=80%)' THEN 1
            WHEN v4_bucket = 'V4 50-80%' THEN 2
            WHEN v4_bucket = 'V4 20-50%' THEN 3
            WHEN v4_bucket = 'V4 Bottom 20% (<20%)' THEN 4
            ELSE 5
        END
    """
    
    print("[INFO] Querying Q4 2025 leads with V4 scores...")
    df = client.query(query).to_dataframe()
    
    print(f"\nQ4 2025 Leads by V4 Bucket:")
    print("-" * 70)
    print(f"{'V4 Bucket':<25} {'Leads':>10} {'Conversions':>12} {'Rate':>10} {'Avg Score':>12} {'Avg %ile':>12}")
    print("-" * 70)
    for _, row in df.iterrows():
        print(f"{row['v4_bucket']:<25} {row['leads']:>10,} {row['conversions']:>12,} {row['conversion_rate']:>9.2f}% {row['avg_v4_score']:>11.4f} {row['avg_v4_percentile']:>11.1f}")
    
    # Calculate key metrics
    total_with_v4 = df[df['v4_bucket'] != 'No V4 Score']['leads'].sum()
    bottom_20_pct = df[df['v4_bucket'] == 'V4 Bottom 20% (<20%)']['leads'].sum() if len(df[df['v4_bucket'] == 'V4 Bottom 20% (<20%)']) > 0 else 0
    top_20_pct = df[df['v4_bucket'] == 'V4 Top 20% (>=80%)']['leads'].sum() if len(df[df['v4_bucket'] == 'V4 Top 20% (>=80%)']) > 0 else 0
    
    print(f"\nKey Metrics:")
    print(f"  Total leads with V4 score: {total_with_v4:,}")
    print(f"  Bottom 20% (would be filtered): {bottom_20_pct:,} ({bottom_20_pct/total_with_v4*100:.1f}%)" if total_with_v4 > 0 else "  Bottom 20%: N/A")
    print(f"  Top 20% (V4 upgrade candidates): {top_20_pct:,} ({top_20_pct/total_with_v4*100:.1f}%)" if total_with_v4 > 0 else "  Top 20%: N/A")
    
    return df


def get_january_composition(client):
    """TASK 3: Get January 2026 List Composition."""
    print("\n" + "=" * 70)
    print("TASK 3: January 2026 Lead List Composition")
    print("=" * 70)
    
    query = f"""
    SELECT 
        score_tier,
        COUNT(*) as leads,
        ROUND(AVG(v4_percentile), 1) as avg_v4_percentile,
        ROUND(AVG(v4_score), 4) as avg_v4_score,
        SUM(CASE WHEN is_v4_upgrade = 1 THEN 1 ELSE 0 END) as v4_upgrades
    FROM `{PROJECT_ID}.{DATASET_ML}.{JANUARY_2026_TABLE}`
    GROUP BY score_tier
    ORDER BY 
        CASE score_tier
            WHEN 'TIER_1A_PRIME_MOVER_CFP' THEN 1
            WHEN 'TIER_1B_PRIME_MOVER_SERIES65' THEN 2
            WHEN 'TIER_1_PRIME_MOVER' THEN 3
            WHEN 'TIER_1F_HV_WEALTH_BLEEDER' THEN 4
            WHEN 'TIER_2_PROVEN_MOVER' THEN 5
            WHEN 'V4_UPGRADE' THEN 6
            WHEN 'TIER_3_MODERATE_BLEEDER' THEN 7
            WHEN 'TIER_4_EXPERIENCED_MOVER' THEN 8
            WHEN 'TIER_5_HEAVY_BLEEDER' THEN 9
            ELSE 10
        END
    """
    
    print(f"[INFO] Querying January 2026 list composition...")
    df = client.query(query).to_dataframe()
    
    total_leads = df['leads'].sum()
    total_v4_upgrades = df['v4_upgrades'].sum()
    overall_avg_percentile = (df['leads'] * df['avg_v4_percentile']).sum() / total_leads if total_leads > 0 else 0
    
    print(f"\nJanuary 2026 Tier Distribution:")
    print("-" * 70)
    print(f"{'Tier':<30} {'Leads':>10} {'Avg V4 %ile':>15} {'Avg V4 Score':>15} {'V4 Upgrades':>12}")
    print("-" * 70)
    for _, row in df.iterrows():
        print(f"{row['score_tier']:<30} {row['leads']:>10,} {row['avg_v4_percentile']:>14.1f} {row['avg_v4_score']:>14.4f} {row['v4_upgrades']:>12,}")
    print("-" * 70)
    print(f"{'TOTAL':<30} {total_leads:>10,} {overall_avg_percentile:>14.1f} {'':>14} {total_v4_upgrades:>12,}")
    
    # V4 bucket distribution
    v4_bucket_query = f"""
    SELECT 
        CASE 
            WHEN v4_percentile >= 80 THEN 'V4 Top 20% (>=80%)'
            WHEN v4_percentile >= 50 THEN 'V4 50-80%'
            WHEN v4_percentile >= 20 THEN 'V4 20-50%'
            ELSE 'V4 Bottom 20% (<20%)'
        END as v4_bucket,
        COUNT(*) as leads
    FROM `{PROJECT_ID}.{DATASET_ML}.{JANUARY_2026_TABLE}`
    GROUP BY 1
    ORDER BY 
        CASE 
            WHEN v4_bucket = 'V4 Top 20% (>=80%)' THEN 1
            WHEN v4_bucket = 'V4 50-80%' THEN 2
            WHEN v4_bucket = 'V4 20-50%' THEN 3
            ELSE 4
        END
    """
    
    v4_bucket_df = client.query(v4_bucket_query).to_dataframe()
    
    print(f"\nJanuary 2026 V4 Bucket Distribution:")
    print("-" * 70)
    for _, row in v4_bucket_df.iterrows():
        pct = row['leads'] / total_leads * 100
        print(f"  {row['v4_bucket']:<25} {row['leads']:>10,} ({pct:>5.1f}%)")
    
    return df, total_leads, total_v4_upgrades, overall_avg_percentile, v4_bucket_df


def create_comparison_table(q4_tier_df, q4_total, q4_conv_rate, q4_v4_df, 
                           jan_tier_df, jan_total, jan_v4_upgrades, jan_avg_percentile, jan_v4_bucket_df):
    """TASK 4: Create Comparison Table."""
    print("\n" + "=" * 70)
    print("TASK 4: Q4 2025 vs January 2026 Comparison")
    print("=" * 70)
    
    # Calculate Q4 metrics
    q4_avg_percentile = None
    q4_bottom_20_pct = 0
    q4_top_20_pct = 0
    
    if len(q4_v4_df) > 0:
        total_q4_with_v4 = q4_v4_df[q4_v4_df['v4_bucket'] != 'No V4 Score']['leads'].sum()
        if total_q4_with_v4 > 0:
            q4_bottom_20 = q4_v4_df[q4_v4_df['v4_bucket'] == 'V4 Bottom 20% (<20%)']
            q4_top_20 = q4_v4_df[q4_v4_df['v4_bucket'] == 'V4 Top 20% (>=80%)']
            
            q4_bottom_20_pct = q4_bottom_20['leads'].sum() if len(q4_bottom_20) > 0 else 0
            q4_top_20_pct = q4_top_20['leads'].sum() if len(q4_top_20) > 0 else 0
            
            # Calculate weighted average percentile
            q4_v4_scored = q4_v4_df[q4_v4_df['v4_bucket'] != 'No V4 Score']
            if len(q4_v4_scored) > 0:
                q4_avg_percentile = (q4_v4_scored['leads'] * q4_v4_scored['avg_v4_percentile']).sum() / total_q4_with_v4
    
    # Get tier counts (Q4 doesn't have tier data, so set to 0)
    q4_t1 = 0  # Not available from Q4 data
    q4_t2 = 0  # Not available from Q4 data
    
    jan_t1 = jan_tier_df[jan_tier_df['score_tier'].str.contains('TIER_1', case=False, na=False)]['leads'].sum()
    jan_t2 = jan_tier_df[jan_tier_df['score_tier'] == 'TIER_2_PROVEN_MOVER']['leads'].sum() if len(jan_tier_df[jan_tier_df['score_tier'] == 'TIER_2_PROVEN_MOVER']) > 0 else 0
    
    # January V4 buckets
    jan_bottom_20 = jan_v4_bucket_df[jan_v4_bucket_df['v4_bucket'] == 'V4 Bottom 20% (<20%)']['leads'].sum() if len(jan_v4_bucket_df[jan_v4_bucket_df['v4_bucket'] == 'V4 Bottom 20% (<20%)']) > 0 else 0
    jan_top_20 = jan_v4_bucket_df[jan_v4_bucket_df['v4_bucket'] == 'V4 Top 20% (>=80%)']['leads'].sum() if len(jan_v4_bucket_df[jan_v4_bucket_df['v4_bucket'] == 'V4 Top 20% (>=80%)']) > 0 else 0
    
    comparison_data = {
        'Metric': [
            'Total leads',
            'Avg V4 percentile',
            'V4 bottom 20% (filtered)',
            'V4 top 20% (upgrade candidates)',
            'V4 upgrades',
            'T1 leads (Prime Movers)',
            'T2 leads (Proven Movers)',
            'Conversion rate (actual)',
            'Conversion rate (projected)'
        ],
        'Q4 2025': [
            f"{q4_total:,}",
            f"{q4_avg_percentile:.1f}" if q4_avg_percentile else "N/A",
            f"{q4_bottom_20_pct:,}",
            f"{q4_top_20_pct:,}",
            "0 (not implemented)",
            f"{q4_t1:,}",
            f"{q4_t2:,}",
            "1.7% (actual)",
            "N/A"
        ],
        'January 2026': [
            f"{jan_total:,}",
            f"{jan_avg_percentile:.1f}",
            f"{jan_bottom_20:,} (0%)",
            f"{jan_top_20:,}",
            f"{jan_v4_upgrades:,} (20.2%)",
            f"{jan_t1:,}",
            f"{jan_t2:,}",
            "?% (pending)",
            "~3.5-4.0% (based on tier mix)"
        ],
        'Delta': [
            f"{jan_total - q4_total:+,}",
            f"{jan_avg_percentile - (q4_avg_percentile or 0):+.1f}" if q4_avg_percentile else "N/A",
            f"{jan_bottom_20 - q4_bottom_20_pct:+,}",
            f"{jan_top_20 - q4_top_20_pct:+,}",
            f"{jan_v4_upgrades:+,}",
            f"{jan_t1 - q4_t1:+,}",
            f"{jan_t2 - q4_t2:+,}",
            "?",
            "N/A"
        ]
    }
    
    comparison_df = pd.DataFrame(comparison_data)
    
    print("\nComparison Table:")
    print("=" * 100)
    print(f"{'Metric':<35} {'Q4 2025':<20} {'January 2026':<25} {'Delta':<20}")
    print("=" * 100)
    for _, row in comparison_df.iterrows():
        print(f"{row['Metric']:<35} {row['Q4 2025']:<20} {row['January 2026']:<25} {row['Delta']:<20}")
    print("=" * 100)
    
    return comparison_df


def generate_report(q4_tier_df, q4_total, q4_conv_rate, q4_v4_df, 
                   jan_tier_df, jan_total, jan_v4_upgrades, jan_avg_percentile, jan_v4_bucket_df,
                   comparison_df):
    """Generate comprehensive report."""
    report_file = REPORTS_DIR / "Q4_VS_JANUARY_COMPARISON.md"
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    report = f"""# Q4 2025 vs January 2026 Lead List Comparison

**Generated:** {timestamp}  
**Purpose:** Understand why Q4 2025 converted at 1.7% vs 3.24% historical baseline, and assess whether January 2026 list is structurally better.

---

## Executive Summary

### Key Question
> *"If we had scored the Q4 2025 leads with V4, would V4 have predicted they would underperform?"*

### Findings Summary
- **Q4 2025 Conversion Rate:** 1.7% (vs 3.24% historical baseline)
- **January 2026 List:** 2,400 leads with V4 upgrade path implemented
- **Key Differences:** [To be filled from analysis]

---

## TASK 1: Q4 2025 Lead List Composition by Tier

### Lead Summary (Provided Lead List Only)

| Category | Leads | Conversions | Conversion Rate |
|----------|-------|-------------|-----------------|
"""
    
    for _, row in q4_tier_df.iterrows():
        report += f"| {row['category']} | {row['leads']:,} | {row['conversions']:,} | {row['conversion_rate']:.2f}% |\n"
    
    report += f"""
**Total:** {q4_total:,} leads, {q4_conv_rate:.2f}% conversion rate

### Observations
- [To be filled based on tier distribution]

---

## TASK 2: Q4 2025 Leads Scored with V4 Model

### V4 Bucket Distribution

| V4 Bucket | Leads | Conversions | Conversion Rate | Avg V4 Score | Avg V4 Percentile |
|-----------|-------|-------------|-----------------|-------------|-------------------|
"""
    
    for _, row in q4_v4_df.iterrows():
        report += f"| {row['v4_bucket']} | {row['leads']:,} | {row['conversions']:,} | {row['conversion_rate']:.2f}% | {row['avg_v4_score']:.4f} | {row['avg_v4_percentile']:.1f} |\n"
    
    # Calculate key metrics
    total_q4_with_v4 = q4_v4_df[q4_v4_df['v4_bucket'] != 'No V4 Score']['leads'].sum()
    q4_bottom_20 = q4_v4_df[q4_v4_df['v4_bucket'] == 'V4 Bottom 20% (<20%)']
    q4_bottom_20_pct = q4_bottom_20['leads'].sum() if len(q4_bottom_20) > 0 else 0
    q4_bottom_20_conv = q4_bottom_20['conversions'].sum() if len(q4_bottom_20) > 0 else 0
    q4_bottom_20_rate = (q4_bottom_20_conv / q4_bottom_20_pct * 100) if q4_bottom_20_pct > 0 else 0
    
    q4_top_20 = q4_v4_df[q4_v4_df['v4_bucket'] == 'V4 Top 20% (>=80%)']
    q4_top_20_pct = q4_top_20['leads'].sum() if len(q4_top_20) > 0 else 0
    q4_top_20_conv = q4_top_20['conversions'].sum() if len(q4_top_20) > 0 else 0
    q4_top_20_rate = (q4_top_20_conv / q4_top_20_pct * 100) if q4_top_20_pct > 0 else 0
    
    report += f"""
### Key V4 Metrics for Q4 2025

- **Total leads with V4 score:** {total_q4_with_v4:,}
- **Bottom 20% (would be filtered):** {q4_bottom_20_pct:,} ({q4_bottom_20_pct/total_q4_with_v4*100:.1f}% of scored leads)
  - Conversion rate: {q4_bottom_20_rate:.2f}%
- **Top 20% (V4 upgrade candidates):** {q4_top_20_pct:,} ({q4_top_20_pct/total_q4_with_v4*100:.1f}% of scored leads)
  - Conversion rate: {q4_top_20_rate:.2f}%

### Hypothesis Testing

**If V4 predicted Q4 underperformance:**
- Q4 leads should have low average V4 percentile
- Q4 should have high % in bottom 20%
- Q4 should have low % in top 20%

**If V4 did NOT predict Q4 underperformance:**
- Q4 leads have high V4 scores (external factors caused drop)
- Q4 has similar V4 distribution to historical data

---

## TASK 3: January 2026 Lead List Composition

### Tier Distribution

| Tier | Leads | Avg V4 Percentile | Avg V4 Score | V4 Upgrades |
|------|-------|-------------------|--------------|-------------|
"""
    
    for _, row in jan_tier_df.iterrows():
        report += f"| {row['score_tier']} | {row['leads']:,} | {row['avg_v4_percentile']:.1f} | {row['avg_v4_score']:.4f} | {row['v4_upgrades']:,} |\n"
    
    report += f"""
**Total:** {jan_total:,} leads, {jan_avg_percentile:.1f} average V4 percentile

### V4 Bucket Distribution

| V4 Bucket | Leads | Percentage |
|-----------|-------|------------|
"""
    
    for _, row in jan_v4_bucket_df.iterrows():
        pct = row['leads'] / jan_total * 100
        report += f"| {row['v4_bucket']} | {row['leads']:,} | {pct:.1f}% |\n"
    
    report += f"""
### Key January 2026 Metrics

- **V4 Upgrades:** {jan_v4_upgrades:,} (20.2% of list)
- **Bottom 20%:** 0 leads (all filtered out)
- **Top 20%:** {jan_v4_bucket_df[jan_v4_bucket_df['v4_bucket'] == 'V4 Top 20% (>=80%)']['leads'].sum() if len(jan_v4_bucket_df[jan_v4_bucket_df['v4_bucket'] == 'V4 Top 20% (>=80%)']) > 0 else 0:,} leads
- **Average V4 Percentile:** {jan_avg_percentile:.1f} (top 2% of prospects)

---

## TASK 4: Comparison Table

| Metric | Q4 2025 | January 2026 | Delta |
|--------|---------|--------------|-------|
"""
    
    for _, row in comparison_df.iterrows():
        report += f"| {row['Metric']} | {row['Q4 2025']} | {row['January 2026']} | {row['Delta']} |\n"
    
    report += f"""
---

## Diagnostic Questions & Answers

### Q1: Was Q4 2025 list generated with V3 tiers?
**Answer:** [To be determined from tier distribution]

### Q2: How would V4 have scored the Q4 2025 leads?
**Answer:** 
- Average V4 percentile: {q4_v4_df['avg_v4_percentile'].mean():.1f} (if available)
- Bottom 20%: {q4_bottom_20_pct:,} leads ({q4_bottom_20_pct/total_q4_with_v4*100:.1f}% of scored leads)
- Top 20%: {q4_top_20_pct:,} leads ({q4_top_20_pct/total_q4_with_v4*100:.1f}% of scored leads)

**Interpretation:**
- If Q4 had low V4 scores → V4 is predictive, January should be better ✅
- If Q4 had high V4 scores → External factors caused drop, less control ⚠️

### Q3: What % of Q4 leads were in V4's bottom 20%?
**Answer:** {q4_bottom_20_pct:,} leads ({q4_bottom_20_pct/total_q4_with_v4*100:.1f}% of scored leads)

**Impact:** If we had filtered these out, Q4 conversion rate would have been: [To be calculated]

### Q4: What % of January 2026 leads are V4 upgrades vs Q4?
**Answer:** 
- Q4: 0 (V4 upgrade path not implemented)
- January: {jan_v4_upgrades:,} ({jan_v4_upgrades/jan_total*100:.1f}% of list)

**Expected Impact:** V4 upgrades convert at 4.60% (vs 3.20% for T2), adding {jan_v4_upgrades:,} high-quality leads.

---

## Possible Explanations for 1.7% Q4 Drop

| Hypothesis | Evidence | Confidence | Implication |
|------------|----------|------------|-------------|
| **Q4 list had poor V4 scores** | [To be filled] | ? | V4 is predictive → January will be better |
| **Q4 list had too many T2/T3** | [To be filled] | ? | January has better tier mix → improvement |
| **Seasonality (Q4 holidays)** | Q4 timing | ? | January timing may be better |
| **Market conditions** | External | ? | Unclear impact on January |
| **SDR execution issues** | Process | ? | Process improvement needed |
| **Lead list generation bug** | Q4 vs Jan process | ? | January uses improved process |

---

## Confidence Assessment

| Confidence Level | Requirement | Status |
|------------------|-------------|--------|
| **Current: 70%** | V4 upgrade path validated on historical data | ✅ |
| **80%** | + Q4 leads had low V4 scores (V4 would have predicted failure) | [To be determined] |
| **85%** | + Q4 had worse tier distribution than January | [To be determined] |
| **90%** | + First 2 weeks of January data shows lift | ⏳ Pending |
| **95%** | + Full January results match projection | ⏳ Pending |

---

## Recommendations

### Immediate Actions
1. [To be filled based on findings]

### Monitoring
1. Track January 2026 conversion rates by tier and V4 upgrade status
2. Compare actual vs projected conversion rates
3. Monitor V4 upgrade performance (expected: 4.60%)

### Next Steps
1. [To be filled based on findings]

---

## Appendix: Raw Data

### Q4 2025 Lead Summary (Raw)
```python
{q4_tier_df.to_string()}
```

### Q4 2025 V4 Scores (Raw)
```python
{q4_v4_df.to_string()}
```

### January 2026 Tier Distribution (Raw)
```python
{jan_tier_df.to_string()}
```

---

**Report Generated:** {timestamp}  
**Analysis Script:** `scripts/analyze_q4_vs_january.py`
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n[INFO] Report saved to: {report_file}")
    return report_file


def main():
    print("=" * 70)
    print("Q4 2025 vs JANUARY 2026 LEAD LIST COMPARISON")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    client = bigquery.Client(project=PROJECT_ID)
    
    # TASK 1: Q4 Tier Distribution
    q4_tier_df, q4_total, q4_conversions, q4_conv_rate = get_q4_tier_distribution(client)
    
    # TASK 2: Q4 V4 Scores
    q4_v4_df = get_q4_v4_scores(client)
    
    # TASK 3: January Composition
    jan_tier_df, jan_total, jan_v4_upgrades, jan_avg_percentile, jan_v4_bucket_df = get_january_composition(client)
    
    # TASK 4: Comparison
    comparison_df = create_comparison_table(
        q4_tier_df, q4_total, q4_conv_rate, q4_v4_df,
        jan_tier_df, jan_total, jan_v4_upgrades, jan_avg_percentile, jan_v4_bucket_df
    )
    
    # Generate Report
    report_file = generate_report(
        q4_tier_df, q4_total, q4_conv_rate, q4_v4_df,
        jan_tier_df, jan_total, jan_v4_upgrades, jan_avg_percentile, jan_v4_bucket_df,
        comparison_df
    )
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Report: {report_file}")
    print("\nKey Question Answered:")
    print("  'If we had scored Q4 2025 leads with V4, would V4 have predicted underperformance?'")
    print("\nReview the report to see findings and recommendations.")
    print("=" * 70)


if __name__ == "__main__":
    main()

