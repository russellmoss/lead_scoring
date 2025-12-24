"""
Compare V3 Tiers vs V4 Scores on Historical Conversion Data

Working Directory: C:/Users/russe/Documents/Lead Scoring/V3+V4_testing
"""

import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score
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

for d in [DATA_DIR, REPORTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PROJECT_ID = "savvy-gtm-analytics"

# V3 tier priority (1 = highest)
TIER_PRIORITY = {
    'TIER_1A_PRIME_MOVER_CFP': 1,
    'TIER_1B_PRIME_MOVER_SERIES65': 2,
    'TIER_1_PRIME_MOVER': 3,
    'TIER_1F_HV_WEALTH_BLEEDER': 4,
    'TIER_2_PROVEN_MOVER': 5,
    'TIER_3_MODERATE_BLEEDER': 6,
    'TIER_4_EXPERIENCED_MOVER': 7,
    'TIER_5_HEAVY_BLEEDER': 8,
    'STANDARD': 9
}

def load_combined_data():
    """Load historical leads with outcomes and V4 scores."""
    client = bigquery.Client(project=PROJECT_ID)
    
    query = """
    SELECT 
        o.*,
        s.v4_score,
        s.v4_percentile,
        s.v4_deprioritize
    FROM `savvy-gtm-analytics.ml_features.historical_leads_with_outcomes` o
    LEFT JOIN `savvy-gtm-analytics.ml_features.historical_leads_v4_scores` s
        ON o.lead_id = s.lead_id
    WHERE s.v4_score IS NOT NULL
    """
    
    df = client.query(query).to_dataframe()
    print(f"[INFO] Loaded {len(df):,} leads with outcomes and V4 scores")
    return df

def calculate_auc_scores(df):
    """Calculate AUC-ROC for V3 tier priority and V4 score."""
    
    # V3: Convert tier to numeric (inverted so higher = better)
    df['v3_score'] = df['score_tier'].map(TIER_PRIORITY)
    df['v3_score_inverted'] = 10 - df['v3_score']  # Higher = better priority
    
    # V4: Already a score (higher = better)
    
    # Calculate AUC-ROC
    v3_auc = roc_auc_score(df['converted_to_mql'], df['v3_score_inverted'])
    v4_auc = roc_auc_score(df['converted_to_mql'], df['v4_score'])
    
    print(f"\n[INFO] V3 Tier AUC-ROC: {v3_auc:.4f}")
    print(f"[INFO] V4 Score AUC-ROC: {v4_auc:.4f}")
    
    return v3_auc, v4_auc

def analyze_disagreement(df):
    """Analyze cases where V3 and V4 disagree."""
    
    # High V3 tier but low V4 score
    high_v3_low_v4 = df[
        (df['score_tier'].isin(['TIER_1A_PRIME_MOVER_CFP', 'TIER_1B_PRIME_MOVER_SERIES65', 'TIER_1_PRIME_MOVER'])) &
        (df['v4_percentile'] < 50)
    ]
    
    # Low V3 tier but high V4 score
    low_v3_high_v4 = df[
        (df['score_tier'].isin(['TIER_3_MODERATE_BLEEDER', 'TIER_4_EXPERIENCED_MOVER', 'TIER_5_HEAVY_BLEEDER', 'STANDARD'])) &
        (df['v4_percentile'] >= 80)
    ]
    
    results = {
        'high_v3_low_v4': {
            'count': len(high_v3_low_v4),
            'conversion_rate': high_v3_low_v4['converted_to_mql'].mean() if len(high_v3_low_v4) > 0 else 0
        },
        'low_v3_high_v4': {
            'count': len(low_v3_high_v4),
            'conversion_rate': low_v3_high_v4['converted_to_mql'].mean() if len(low_v3_high_v4) > 0 else 0
        }
    }
    
    return results

def generate_comparison_report(df, v3_auc, v4_auc, disagreement):
    """Generate final comparison report."""
    
    baseline = df['converted_to_mql'].mean()
    
    # T1A vs T2 head-to-head
    t1a = df[df['score_tier'] == 'TIER_1A_PRIME_MOVER_CFP']
    t2 = df[df['score_tier'] == 'TIER_2_PROVEN_MOVER']
    t1 = df[df['score_tier'] == 'TIER_1_PRIME_MOVER']
    
    report = f"""# V3 vs V4 Model Comparison Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Leads Analyzed**: {len(df):,}
**Total Conversions**: {df['converted_to_mql'].sum():,}
**Baseline Conversion Rate**: {baseline*100:.2f}%

---

## 1. Model Performance Summary

| Metric | V3 (Tier Rules) | V4 (XGBoost) | Winner |
|--------|-----------------|--------------|--------|
| AUC-ROC | {v3_auc:.4f} | {v4_auc:.4f} | {'V3' if v3_auc > v4_auc else 'V4'} |

**Interpretation**: 
- AUC-ROC measures how well the model ranks leads (higher score → higher conversion probability)
- {'V3 rules better predict conversions' if v3_auc > v4_auc else 'V4 XGBoost better predicts conversions'}
- Difference: {abs(v3_auc - v4_auc):.4f} ({'significant' if abs(v3_auc - v4_auc) > 0.02 else 'marginal'})

---

## 2. The Critical Question: T1A vs T2

| Metric | T1A (CFP) | T2 (Proven Mover) |
|--------|-----------|-------------------|
| Lead Count | {len(t1a):,} | {len(t2):,} |
| Conversions | {t1a['converted_to_mql'].sum() if len(t1a) > 0 else 0} | {t2['converted_to_mql'].sum()} |
| Conversion Rate | {(t1a['converted_to_mql'].mean()*100 if len(t1a) > 0 else 0):.2f}% | {t2['converted_to_mql'].mean()*100:.2f}% |
| Lift vs Baseline | {(t1a['converted_to_mql'].mean()/baseline if len(t1a) > 0 and baseline > 0 else 0):.2f}x | {(t2['converted_to_mql'].mean()/baseline if baseline > 0 else 0):.2f}x |
| Avg V4 Score | {(t1a['v4_score'].mean() if len(t1a) > 0 else 0):.4f} | {t2['v4_score'].mean():.4f} |
| Avg V4 Percentile | {(t1a['v4_percentile'].mean() if len(t1a) > 0 else 0):.1f} | {t2['v4_percentile'].mean():.1f} |

"""
    
    # Also compare T1 vs T2 (larger samples)
    if len(t1) > 0 and len(t2) > 0:
        t1_rate = t1['converted_to_mql'].mean()
        t2_rate = t2['converted_to_mql'].mean()
        report += f"""
### T1 vs T2 Comparison (Larger Samples)

| Metric | T1 (Prime Mover) | T2 (Proven Mover) |
|--------|------------------|-------------------|
| Lead Count | {len(t1):,} | {len(t2):,} |
| Conversions | {t1['converted_to_mql'].sum()} | {t2['converted_to_mql'].sum()} |
| Conversion Rate | {t1_rate*100:.2f}% | {t2_rate*100:.2f}% |
| Lift vs Baseline | {(t1_rate/baseline if baseline > 0 else 0):.2f}x | {(t2_rate/baseline if baseline > 0 else 0):.2f}x |
| Avg V4 Score | {t1['v4_score'].mean():.4f} | {t2['v4_score'].mean():.4f} |
| Avg V4 Percentile | {t1['v4_percentile'].mean():.1f} | {t2['v4_percentile'].mean():.1f} |

"""
    
    if len(t1a) > 0 and len(t2) > 0:
        t1a_rate = t1a['converted_to_mql'].mean()
        t2_rate = t2['converted_to_mql'].mean()
        
        if t1a_rate > t2_rate and t2_rate > 0:
            report += f"""
### ✅ CONCLUSION: V3 Tier Ordering is CORRECT (T1A > T2)

T1A leads convert at **{(t1a_rate/t2_rate):.2f}x** the rate of T2 leads.

Despite V4 giving T1A leads lower scores (avg {t1a['v4_score'].mean():.4f} vs T2's {t2['v4_score'].mean():.4f}), 
the actual conversion data shows V3's prioritization of CFPs at bleeding firms is correct.

**Note**: T1A sample size is very small (4 leads), so this conclusion should be validated with more data.

"""
        elif t2_rate > t1a_rate and t1a_rate > 0:
            report += f"""
### ⚠️ CONCLUSION: V3 Tier Ordering May Be WRONG (T2 > T1A)

T2 leads convert at **{(t2_rate/t1a_rate):.2f}x** the rate of T1A leads.

V4's lower scores for T1A leads appear to be correct - these leads don't convert as well as V3 predicts.

**Note**: T1A sample size is very small (4 leads), so this conclusion should be validated with more data.

"""
    elif len(t1) > 0 and len(t2) > 0:
        t1_rate = t1['converted_to_mql'].mean()
        t2_rate = t2['converted_to_mql'].mean()
        
        if t1_rate > t2_rate and t2_rate > 0:
            report += f"""
### ✅ CONCLUSION: V3 Tier Ordering is CORRECT (T1 > T2)

T1 leads convert at **{(t1_rate/t2_rate):.2f}x** the rate of T2 leads.

This validates V3's prioritization of prime movers over proven movers.

"""
        elif t2_rate > t1_rate and t1_rate > 0:
            report += f"""
### ⚠️ CONCLUSION: V3 Tier Ordering May Be WRONG (T2 > T1)

T2 leads convert at **{(t2_rate/t1_rate):.2f}x** the rate of T1 leads.

This contradicts V3's tier ordering.

"""
    
    report += f"""

---

## 3. Disagreement Analysis

### When V3 Says High Priority but V4 Says Low

Leads with V3 Tier 1 but V4 Percentile < 50:
- Count: {disagreement['high_v3_low_v4']['count']:,}
- Conversion Rate: {disagreement['high_v3_low_v4']['conversion_rate']*100:.2f}%
- vs Baseline: {(disagreement['high_v3_low_v4']['conversion_rate']/baseline if baseline > 0 else 0):.2f}x

### When V3 Says Low Priority but V4 Says High

Leads with V3 Tier 3+ but V4 Percentile >= 80:
- Count: {disagreement['low_v3_high_v4']['count']:,}
- Conversion Rate: {disagreement['low_v3_high_v4']['conversion_rate']*100:.2f}%
- vs Baseline: {(disagreement['low_v3_high_v4']['conversion_rate']/baseline if baseline > 0 else 0):.2f}x

"""
    
    # Determine which disagreement group performs better
    if disagreement['high_v3_low_v4']['count'] > 0 and disagreement['low_v3_high_v4']['count'] > 0:
        if disagreement['high_v3_low_v4']['conversion_rate'] > disagreement['low_v3_high_v4']['conversion_rate']:
            report += "**Finding**: V3 is right when they disagree - high V3/low V4 leads convert better.\n"
        else:
            report += "**Finding**: V4 is right when they disagree - low V3/high V4 leads convert better.\n"
    
    report += f"""

---

## 4. Final Recommendations

Based on this analysis:

"""
    
    if v3_auc > v4_auc:
        report += """
1. **V3 has better predictive power** - Higher AUC-ROC indicates better ranking
2. **Trust V3 tier ordering** - Historical data validates tier prioritization
3. **Use V4 for deprioritization only** - V4 can identify bottom 20% but shouldn't override V3 tiers
4. **Monitor T1A performance** - Sample size too small to draw firm conclusions
"""
    else:
        report += """
1. **V4 has better predictive power** - Higher AUC-ROC indicates better ranking
2. **Consider V4 for cross-tier ranking** - V4 may capture signals V3 misses
3. **Re-evaluate V3 tier logic** - Some tier assignments may not align with actual performance
4. **A/B test both approaches** - Test V4 prioritization vs V3 in production
"""
    
    return report

def main():
    print("=" * 70)
    print("V3 vs V4 MODEL COMPARISON")
    print("=" * 70)
    
    # Load data
    df = load_combined_data()
    
    # Calculate AUC
    v3_auc, v4_auc = calculate_auc_scores(df)
    
    # Analyze disagreement
    disagreement = analyze_disagreement(df)
    
    # Generate report
    report = generate_comparison_report(df, v3_auc, v4_auc, disagreement)
    
    # Save report
    report_path = REPORTS_DIR / "v3_vs_v4_testing.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n[INFO] Report saved to {report_path}")
    
    # Save comparison data
    df.to_csv(DATA_DIR / "v3_v4_comparison.csv", index=False)
    
    # Log summary
    log_path = LOGS_DIR / "INVESTIGATION_LOG.md"
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"\n\n## Step 5: V3 vs V4 Comparison - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- V3 AUC-ROC: {v3_auc:.4f}\n")
        f.write(f"- V4 AUC-ROC: {v4_auc:.4f}\n")
        f.write(f"- Winner: {'V3' if v3_auc > v4_auc else 'V4'}\n")
    
    print("\n[INFO] Comparison complete!")
    return df

if __name__ == "__main__":
    main()

