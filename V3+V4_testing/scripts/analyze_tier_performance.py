"""
Analyze V3 Tier Performance: Actual vs Expected Conversion Rates

Working Directory: C:/Users/russe/Documents/Lead Scoring/V3+V4_testing
Output: data/tier_performance.csv, reports/tier_analysis.md
"""

import pandas as pd
import numpy as np
from scipy import stats
from google.cloud import bigquery
from pathlib import Path
from datetime import datetime

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
WORKING_DIR = Path("C:/Users/russe/Documents/Lead Scoring/V3+V4_testing")
DATA_DIR = WORKING_DIR / "data"
REPORTS_DIR = WORKING_DIR / "reports"
LOGS_DIR = WORKING_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "savvy-gtm-analytics"

# V3 Expected Conversion Rates (from SQL query - these are what's actually in the data)
V3_EXPECTED_RATES = {
    'TIER_1A_PRIME_MOVER_CFP': 0.1644,
    'TIER_1B_PRIME_MOVER_SERIES65': 0.1648,
    'TIER_1_PRIME_MOVER': 0.1321,
    'TIER_1F_HV_WEALTH_BLEEDER': 0.065,  # Not in data but keeping for reference
    'TIER_2_PROVEN_MOVER': 0.0859,
    'TIER_3_MODERATE_BLEEDER': 0.0952,
    'TIER_4_EXPERIENCED_MOVER': 0.1154,
    'TIER_5_HEAVY_BLEEDER': 0.0727,
    'STANDARD': 0.0382
}

def load_historical_data():
    """Load historical leads with outcomes from BigQuery."""
    client = bigquery.Client(project=PROJECT_ID)
    query = """
    SELECT *
    FROM `savvy-gtm-analytics.ml_features.historical_leads_with_outcomes`
    """
    df = client.query(query).to_dataframe()
    print(f"[INFO] Loaded {len(df):,} historical leads")
    return df

def calculate_tier_performance(df):
    """Calculate actual conversion rates by tier."""
    
    # Overall baseline
    baseline_rate = df['converted_to_mql'].mean()
    print(f"\n[INFO] Overall conversion rate: {baseline_rate*100:.2f}%")
    
    # By tier
    tier_stats = df.groupby('score_tier').agg({
        'lead_id': 'count',
        'converted_to_mql': ['sum', 'mean']
    }).round(4)
    
    tier_stats.columns = ['total_leads', 'conversions', 'actual_rate']
    tier_stats['expected_rate'] = tier_stats.index.map(V3_EXPECTED_RATES)
    tier_stats['actual_lift'] = tier_stats['actual_rate'] / baseline_rate if baseline_rate > 0 else 0
    tier_stats['expected_lift'] = tier_stats['expected_rate'] / baseline_rate if baseline_rate > 0 else 0
    tier_stats['rate_vs_expected'] = tier_stats['actual_rate'] / tier_stats['expected_rate'] if tier_stats['expected_rate'].gt(0).any() else 0
    
    # Sort by tier priority
    tier_order = ['TIER_1A_PRIME_MOVER_CFP', 'TIER_1B_PRIME_MOVER_SERIES65', 
                  'TIER_1_PRIME_MOVER', 'TIER_1F_HV_WEALTH_BLEEDER',
                  'TIER_2_PROVEN_MOVER', 'TIER_3_MODERATE_BLEEDER',
                  'TIER_4_EXPERIENCED_MOVER', 'TIER_5_HEAVY_BLEEDER', 'STANDARD']
    tier_stats = tier_stats.reindex([t for t in tier_order if t in tier_stats.index])
    
    return tier_stats, baseline_rate

def statistical_significance(df, tier1, tier2):
    """Test if two tiers have significantly different conversion rates."""
    t1_data = df[df['score_tier'] == tier1]
    t2_data = df[df['score_tier'] == tier2]
    
    if len(t1_data) == 0 or len(t2_data) == 0:
        return {
            'tier1': tier1,
            'tier2': tier2,
            'tier1_rate': 0 if len(t1_data) == 0 else t1_data['converted_to_mql'].mean(),
            'tier2_rate': 0 if len(t2_data) == 0 else t2_data['converted_to_mql'].mean(),
            'odds_ratio': None,
            'p_value': None,
            'significant': False,
            'note': 'Insufficient data for comparison'
        }
    
    # Create contingency table
    table = [
        [t1_data['converted_to_mql'].sum(), len(t1_data) - t1_data['converted_to_mql'].sum()],
        [t2_data['converted_to_mql'].sum(), len(t2_data) - t2_data['converted_to_mql'].sum()]
    ]
    
    # Fisher's exact test (better for small samples)
    try:
        odds_ratio, p_value = stats.fisher_exact(table)
    except:
        odds_ratio, p_value = None, None
    
    return {
        'tier1': tier1,
        'tier2': tier2,
        'tier1_rate': t1_data['converted_to_mql'].mean(),
        'tier2_rate': t2_data['converted_to_mql'].mean(),
        'odds_ratio': odds_ratio,
        'p_value': p_value,
        'significant': p_value < 0.05 if p_value is not None else False
    }

def generate_report(tier_stats, baseline_rate, comparisons):
    """Generate markdown report."""
    report = f"""# V3 Tier Performance Analysis

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data Period**: Q1-Q3 2025
**Baseline Conversion Rate**: {baseline_rate*100:.2f}%

---

## Tier Performance Summary

| Tier | Leads | Conversions | Actual Rate | Expected Rate | Actual Lift | Rate vs Expected |
|------|-------|-------------|-------------|---------------|-------------|------------------|
"""
    
    for tier, row in tier_stats.iterrows():
        report += f"| {tier} | {int(row['total_leads']):,} | {int(row['conversions'])} | {row['actual_rate']*100:.2f}% | {row['expected_rate']*100:.2f}% | {row['actual_lift']:.2f}x | {row['rate_vs_expected']:.2f}x |\n"
    
    report += f"""

---

## Key Findings

### T1A vs T2 Comparison (The Critical Question)

"""
    
    # Find T1A vs T2 comparison
    t1a_t2_found = False
    for comp in comparisons:
        if comp['tier1'] == 'TIER_1A_PRIME_MOVER_CFP' and comp['tier2'] == 'TIER_2_PROVEN_MOVER':
            t1a_t2_found = True
            odds_str = f"{comp['odds_ratio']:.2f}" if comp['odds_ratio'] is not None else 'N/A'
            pval_str = f"{comp['p_value']:.4f}" if comp['p_value'] is not None else 'N/A'
            report += f"""
| Metric | T1A (CFP) | T2 (Proven Mover) |
|--------|-----------|-------------------|
| Conversion Rate | {comp['tier1_rate']*100:.2f}% | {comp['tier2_rate']*100:.2f}% |
| Odds Ratio | {odds_str} | - |
| P-Value | {pval_str} | - |
| Statistically Significant | {'Yes' if comp.get('significant', False) else 'No'} | - |

**Interpretation**: 
"""
            if comp.get('note'):
                report += f"{comp['note']}\n"
            elif comp['tier1_rate'] > comp['tier2_rate'] and comp['tier2_rate'] > 0:
                report += f"T1A converts **{comp['tier1_rate']/comp['tier2_rate']:.2f}x better** than T2. V3 tier ordering is correct.\n"
            elif comp['tier2_rate'] > comp['tier1_rate'] and comp['tier1_rate'] > 0:
                report += f"T2 converts **{comp['tier2_rate']/comp['tier1_rate']:.2f}x better** than T1A. V3 tier ordering may be wrong!\n"
            else:
                report += f"T1A rate: {comp['tier1_rate']*100:.2f}%, T2 rate: {comp['tier2_rate']*100:.2f}%. Cannot calculate ratio due to zero rates.\n"
    
    if not t1a_t2_found:
        report += "**Note**: T1A sample size too small (4 leads) for reliable comparison with T2.\n"
    
    # Also compare T1 vs T2 (larger samples)
    report += f"""

### T1 vs T2 Comparison (Larger Samples)

"""
    t1_t2_found = False
    for comp in comparisons:
        if comp['tier1'] == 'TIER_1_PRIME_MOVER' and comp['tier2'] == 'TIER_2_PROVEN_MOVER':
            t1_t2_found = True
            odds_str = f"{comp['odds_ratio']:.2f}" if comp['odds_ratio'] is not None else 'N/A'
            pval_str = f"{comp['p_value']:.4f}" if comp['p_value'] is not None else 'N/A'
            report += f"""
| Metric | T1 (Prime Mover) | T2 (Proven Mover) |
|--------|------------------|-------------------|
| Conversion Rate | {comp['tier1_rate']*100:.2f}% | {comp['tier2_rate']*100:.2f}% |
| Odds Ratio | {odds_str} | - |
| P-Value | {pval_str} | - |
| Statistically Significant | {'Yes' if comp.get('significant', False) else 'No'} | - |

**Interpretation**: 
"""
            if comp['tier1_rate'] > comp['tier2_rate'] and comp['tier2_rate'] > 0:
                report += f"T1 converts **{comp['tier1_rate']/comp['tier2_rate']:.2f}x better** than T2.\n"
            elif comp['tier2_rate'] > comp['tier1_rate'] and comp['tier1_rate'] > 0:
                report += f"T2 converts **{comp['tier2_rate']/comp['tier1_rate']:.2f}x better** than T1.\n"
            else:
                report += f"T1 rate: {comp['tier1_rate']*100:.2f}%, T2 rate: {comp['tier2_rate']*100:.2f}%.\n"
    
    report += """

---

## Conclusions

"""
    
    # Determine if V3 ordering is correct
    if 'TIER_1A_PRIME_MOVER_CFP' in tier_stats.index and 'TIER_2_PROVEN_MOVER' in tier_stats.index:
        t1a_rate = tier_stats.loc['TIER_1A_PRIME_MOVER_CFP', 'actual_rate']
        t2_rate = tier_stats.loc['TIER_2_PROVEN_MOVER', 'actual_rate']
        t1a_n = tier_stats.loc['TIER_1A_PRIME_MOVER_CFP', 'total_leads']
        
        if t1a_n < 10:
            report += "⚠️ **T1A Sample Too Small**: Only 4 leads in T1A - cannot reliably compare to T2.\n"
            report += "   - Recommendation: Need more T1A data or compare T1 vs T2 instead.\n"
        elif t1a_rate > t2_rate:
            report += "✅ **V3 Tier Ordering is Correct**: T1A (CFP) leads convert better than T2 (Proven Mover) leads.\n"
            report += "   - Recommendation: Trust V3 tiers, V4 disagreement may be noise.\n"
        else:
            report += "⚠️ **V3 Tier Ordering May Be Wrong**: T2 leads convert better than T1A leads.\n"
            report += "   - Recommendation: Investigate V4's signal more closely.\n"
    
    # Check T1 vs T2
    if 'TIER_1_PRIME_MOVER' in tier_stats.index and 'TIER_2_PROVEN_MOVER' in tier_stats.index:
        t1_rate = tier_stats.loc['TIER_1_PRIME_MOVER', 'actual_rate']
        t2_rate = tier_stats.loc['TIER_2_PROVEN_MOVER', 'actual_rate']
        
        if t1_rate > t2_rate:
            report += f"\n✅ **T1 Outperforms T2**: T1 converts at {t1_rate*100:.2f}% vs T2's {t2_rate*100:.2f}%.\n"
            report += "   - This suggests V3's prioritization of prime movers is correct.\n"
        else:
            report += f"\n⚠️ **T2 Outperforms T1**: T2 converts at {t2_rate*100:.2f}% vs T1's {t1_rate*100:.2f}%.\n"
            report += "   - This contradicts V3's tier ordering.\n"
    
    return report

def main():
    print("=" * 70)
    print("V3 TIER PERFORMANCE ANALYSIS")
    print("=" * 70)
    
    # Load data
    df = load_historical_data()
    
    # Calculate tier performance
    tier_stats, baseline_rate = calculate_tier_performance(df)
    
    print("\n" + "=" * 70)
    print("TIER PERFORMANCE SUMMARY")
    print("=" * 70)
    print(tier_stats.to_string())
    
    # Statistical comparisons
    comparisons = []
    
    # T1A vs T2 (if both exist)
    if 'TIER_1A_PRIME_MOVER_CFP' in df['score_tier'].values and 'TIER_2_PROVEN_MOVER' in df['score_tier'].values:
        comp = statistical_significance(df, 'TIER_1A_PRIME_MOVER_CFP', 'TIER_2_PROVEN_MOVER')
        comparisons.append(comp)
        if comp.get('p_value') is not None:
            print(f"\n[INFO] T1A vs T2: p-value = {comp['p_value']:.4f}")
        else:
            print(f"\n[INFO] T1A vs T2: {comp.get('note', 'Cannot calculate')}")
    
    # T1 vs T2 (larger samples)
    if 'TIER_1_PRIME_MOVER' in df['score_tier'].values and 'TIER_2_PROVEN_MOVER' in df['score_tier'].values:
        comp = statistical_significance(df, 'TIER_1_PRIME_MOVER', 'TIER_2_PROVEN_MOVER')
        comparisons.append(comp)
        if comp.get('p_value') is not None:
            print(f"[INFO] T1 vs T2: p-value = {comp['p_value']:.4f}")
    
    # Save results
    tier_stats.to_csv(DATA_DIR / "tier_performance.csv")
    print(f"\n[INFO] Saved tier performance to {DATA_DIR / 'tier_performance.csv'}")
    
    # Generate report
    report = generate_report(tier_stats, baseline_rate, comparisons)
    report_path = REPORTS_DIR / "tier_analysis.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"[INFO] Saved report to {report_path}")
    
    # Log to investigation log
    log_path = LOGS_DIR / "INVESTIGATION_LOG.md"
    with open(log_path, 'a') as f:
        f.write(f"\n\n## Step 3: Tier Performance Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- Baseline conversion rate: {baseline_rate*100:.2f}%\n")
        f.write(f"- Total leads analyzed: {len(df):,}\n")
        f.write(f"- Total conversions: {df['converted_to_mql'].sum():,}\n")
        for tier, row in tier_stats.iterrows():
            f.write(f"- {tier}: {row['actual_rate']*100:.2f}% actual (vs {row['expected_rate']*100:.2f}% expected)\n")
    
    return tier_stats

if __name__ == "__main__":
    main()

