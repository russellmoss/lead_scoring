# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\signal_decay_diagnostic.py
# Investigates WHY the danger zone signal decayed from 4.43x (2024) to 1.70x (2025)

import sys
from pathlib import Path
VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

import pandas as pd
import numpy as np
from google.cloud import bigquery
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 80)
print("SIGNAL DECAY INVESTIGATION")
print("Why did Danger Zone lift drop from 4.43x (2024) to 1.70x (Aug-Oct 2025)?")
print("=" * 80)

# =============================================================================
# LOAD COMPREHENSIVE DATA
# =============================================================================
print("\n[1/8] Loading comprehensive data...")

query = """
SELECT 
    s.lead_id,
    s.contacted_date,
    s.target,
    s.split,
    s.advisor_crd,
    
    -- Lead metadata from Salesforce
    l.LeadSource as lead_source,
    l.Company as company_name,
    l.CreatedDate as sf_created_date,
    
    -- Base features
    s.industry_tenure_months,
    s.num_prior_firms,
    s.current_firm_tenure_months,
    s.pit_moves_3yr,
    s.firm_aum_pit,
    s.firm_net_change_12mo,
    s.is_bleeding_firm,
    
    -- Velocity features
    v.days_at_current_firm,
    v.in_danger_zone,
    v.tenure_bucket,
    v.moves_3yr_from_starts,
    v.total_jobs_pit as total_jobs
    
FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2` s
LEFT JOIN `savvy-gtm-analytics.ml_features.lead_velocity_features` v
    ON s.lead_id = v.lead_id
LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
    ON s.lead_id = l.Id
WHERE s.split IN ('TRAIN', 'TEST')
ORDER BY s.contacted_date
"""

df = client.query(query).result().to_dataframe()
df['contacted_date'] = pd.to_datetime(df['contacted_date'])
df['year_month'] = df['contacted_date'].dt.to_period('M')
df['quarter'] = df['contacted_date'].dt.to_period('Q')
df['year'] = df['contacted_date'].dt.year

print(f"   Loaded {len(df):,} leads")

# =============================================================================
# HYPOTHESIS 1: GRADUAL DECAY VS SUDDEN SHIFT
# =============================================================================
print("\n" + "=" * 80)
print("[2/8] HYPOTHESIS 1: Is this a gradual decay or sudden shift?")
print("=" * 80)

# Monthly danger zone conversion rates
monthly_dz = df[df['in_danger_zone'] == 1].groupby('year_month').agg({
    'target': ['count', 'sum', 'mean']
}).round(4)
monthly_dz.columns = ['dz_count', 'dz_conversions', 'dz_conv_rate']

monthly_baseline = df.groupby('year_month').agg({
    'target': ['count', 'sum', 'mean']
}).round(4)
monthly_baseline.columns = ['total_count', 'total_conversions', 'baseline_rate']

monthly = monthly_dz.join(monthly_baseline)
monthly['dz_lift'] = monthly['dz_conv_rate'] / monthly['baseline_rate']

print("\nMonthly Danger Zone Performance:")
print("-" * 80)
print(f"{'Month':<10} | {'DZ Leads':<10} | {'DZ Conv%':<10} | {'Baseline%':<10} | {'Lift':<8}")
print("-" * 80)

for month in monthly.index:
    row = monthly.loc[month]
    if row['dz_count'] >= 10:  # Only show months with enough data
        lift_marker = "🔥" if row['dz_lift'] >= 3.0 else ("✅" if row['dz_lift'] >= 2.0 else "⚠️")
        print(f"{str(month):<10} | {int(row['dz_count']):<10} | {row['dz_conv_rate']*100:<10.1f} | {row['baseline_rate']*100:<10.1f} | {row['dz_lift']:<6.2f}x {lift_marker}")

# Quarterly summary
print("\nQuarterly Summary:")
quarterly = df.groupby(['quarter', 'in_danger_zone'])['target'].agg(['count', 'mean']).unstack()
print(quarterly.round(3))

# =============================================================================
# HYPOTHESIS 2: CREAM SKIMMING - Were DZ leads contacted first?
# =============================================================================
print("\n" + "=" * 80)
print("[3/8] HYPOTHESIS 2: Cream Skimming - Were danger zone leads contacted earlier?")
print("=" * 80)

# Check if DZ leads were contacted earlier in each quarter
print("\nMedian Contact Date by Danger Zone Status (per quarter):")
for q in df['quarter'].unique():
    q_df = df[df['quarter'] == q]
    if len(q_df) > 100:
        dz_median = q_df[q_df['in_danger_zone'] == 1]['contacted_date'].median()
        non_dz_median = q_df[q_df['in_danger_zone'] == 0]['contacted_date'].median()
        if pd.notna(dz_median) and pd.notna(non_dz_median):
            diff_days = (non_dz_median - dz_median).days
            direction = "EARLIER" if diff_days > 0 else "LATER"
            print(f"  {q}: DZ leads contacted {abs(diff_days)} days {direction} than non-DZ")

# Check contact order within each month
print("\nPercentile of DZ leads in contact order (0=first contacted, 100=last):")
df['month_contact_rank'] = df.groupby('year_month')['contacted_date'].rank(pct=True) * 100
for period_name, period_filter in [("2024", df['year'] == 2024), ("2025", df['year'] == 2025)]:
    period_df = df[period_filter]
    dz_percentile = period_df[period_df['in_danger_zone'] == 1]['month_contact_rank'].mean()
    non_dz_percentile = period_df[period_df['in_danger_zone'] == 0]['month_contact_rank'].mean()
    print(f"  {period_name}: DZ leads at {dz_percentile:.1f}th percentile, Non-DZ at {non_dz_percentile:.1f}th percentile")

# =============================================================================
# HYPOTHESIS 3: LEAD SOURCE CHANGED
# =============================================================================
print("\n" + "=" * 80)
print("[4/8] HYPOTHESIS 3: Did lead sources change between 2024 and 2025?")
print("=" * 80)

df_2024 = df[df['year'] == 2024]
df_2025 = df[df['year'] == 2025]

print("\nLead Source Distribution:")
print("-" * 60)
print(f"{'Lead Source':<30} | {'2024 %':<10} | {'2025 %':<10} | {'Change':<10}")
print("-" * 60)

sources_2024 = df_2024['lead_source'].value_counts(normalize=True) * 100
sources_2025 = df_2025['lead_source'].value_counts(normalize=True) * 100

all_sources = set(sources_2024.index) | set(sources_2025.index)
for source in sorted(all_sources, key=lambda x: sources_2024.get(x, 0) + sources_2025.get(x, 0), reverse=True)[:10]:
    pct_2024 = sources_2024.get(source, 0)
    pct_2025 = sources_2025.get(source, 0)
    change = pct_2025 - pct_2024
    change_str = f"+{change:.1f}" if change > 0 else f"{change:.1f}"
    print(f"{str(source)[:30]:<30} | {pct_2024:<10.1f} | {pct_2025:<10.1f} | {change_str:<10}")

# Lead source conversion rates
print("\nDanger Zone Conversion by Lead Source (2024 vs 2025):")
for source in df['lead_source'].value_counts().head(5).index:
    source_2024 = df_2024[(df_2024['lead_source'] == source) & (df_2024['in_danger_zone'] == 1)]
    source_2025 = df_2025[(df_2025['lead_source'] == source) & (df_2025['in_danger_zone'] == 1)]
    
    if len(source_2024) >= 10 and len(source_2025) >= 10:
        conv_2024 = source_2024['target'].mean() * 100
        conv_2025 = source_2025['target'].mean() * 100
        print(f"  {str(source)[:25]}: 2024={conv_2024:.1f}%, 2025={conv_2025:.1f}%")

# =============================================================================
# HYPOTHESIS 4: FEATURE DISTRIBUTION SHIFT
# =============================================================================
print("\n" + "=" * 80)
print("[5/8] HYPOTHESIS 4: Did the characteristics of DZ leads change?")
print("=" * 80)

# Compare DZ leads between 2024 and 2025
features_to_compare = [
    'industry_tenure_months',
    'num_prior_firms', 
    'pit_moves_3yr',
    'firm_aum_pit',
    'firm_net_change_12mo',
    'days_at_current_firm',
    'total_jobs'
]

print("\nMean Feature Values for DANGER ZONE Leads:")
print("-" * 70)
print(f"{'Feature':<30} | {'2024 DZ':<12} | {'2025 DZ':<12} | {'Change %':<10}")
print("-" * 70)

dz_2024 = df_2024[df_2024['in_danger_zone'] == 1]
dz_2025 = df_2025[df_2025['in_danger_zone'] == 1]

for feat in features_to_compare:
    if feat in df.columns:
        mean_2024 = dz_2024[feat].mean()
        mean_2025 = dz_2025[feat].mean()
        if pd.notna(mean_2024) and pd.notna(mean_2025) and mean_2024 != 0:
            pct_change = ((mean_2025 - mean_2024) / abs(mean_2024)) * 100
            change_str = f"+{pct_change:.0f}%" if pct_change > 0 else f"{pct_change:.0f}%"
            print(f"{feat:<30} | {mean_2024:<12.1f} | {mean_2025:<12.1f} | {change_str:<10}")

# =============================================================================
# HYPOTHESIS 5: FIRM SATURATION - Same firms being contacted repeatedly?
# =============================================================================
print("\n" + "=" * 80)
print("[6/8] HYPOTHESIS 5: Firm Saturation - Are we depleting certain firms?")
print("=" * 80)

# Top firms by lead volume in 2024 - how do they perform in 2025?
firm_2024 = df_2024.groupby('company_name').agg({
    'lead_id': 'count',
    'target': 'mean'
}).rename(columns={'lead_id': 'leads_2024', 'target': 'conv_2024'})

firm_2025 = df_2025.groupby('company_name').agg({
    'lead_id': 'count',
    'target': 'mean'
}).rename(columns={'lead_id': 'leads_2025', 'target': 'conv_2025'})

firm_comparison = firm_2024.join(firm_2025, how='inner')
firm_comparison = firm_comparison[(firm_comparison['leads_2024'] >= 20) & (firm_comparison['leads_2025'] >= 20)]
firm_comparison['conv_change'] = firm_comparison['conv_2025'] - firm_comparison['conv_2024']

if len(firm_comparison) > 0:
    print(f"\nFirms with 20+ leads in both years: {len(firm_comparison)}")
    
    improved = (firm_comparison['conv_change'] > 0).sum()
    declined = (firm_comparison['conv_change'] < 0).sum()
    print(f"  Conversion improved: {improved} firms")
    print(f"  Conversion declined: {declined} firms")
    
    print("\nTop 5 Declining Firms (by conversion drop):")
    worst = firm_comparison.nsmallest(5, 'conv_change')
    for firm, row in worst.iterrows():
        print(f"  {str(firm)[:40]}: {row['conv_2024']*100:.1f}% → {row['conv_2025']*100:.1f}% ({row['conv_change']*100:+.1f}pp)")

# =============================================================================
# HYPOTHESIS 6: REPEAT ADVISORS - Same people being contacted again?
# =============================================================================
print("\n" + "=" * 80)
print("[7/8] HYPOTHESIS 6: Repeat Contacts - Same advisors contacted multiple times?")
print("=" * 80)

# Check if advisors were contacted in both 2024 and 2025
advisors_2024 = set(df_2024['advisor_crd'].dropna().unique())
advisors_2025 = set(df_2025['advisor_crd'].dropna().unique())
repeat_advisors = advisors_2024 & advisors_2025

print(f"\nUnique advisors in 2024: {len(advisors_2024):,}")
print(f"Unique advisors in 2025: {len(advisors_2025):,}")
print(f"Advisors contacted in BOTH years: {len(repeat_advisors):,} ({len(repeat_advisors)/len(advisors_2025)*100:.1f}% of 2025)")

# Conversion rates for repeat vs new advisors in 2025
df_2025['is_repeat'] = df_2025['advisor_crd'].isin(repeat_advisors)
repeat_conv = df_2025[df_2025['is_repeat']]['target'].mean()
new_conv = df_2025[~df_2025['is_repeat']]['target'].mean()

print(f"\n2025 Conversion Rates:")
print(f"  Repeat advisors (also contacted in 2024): {repeat_conv*100:.2f}%")
print(f"  New advisors (first contact in 2025): {new_conv*100:.2f}%")

# DZ signal for repeat vs new
print("\nDanger Zone Signal for Repeat vs New Advisors in 2025:")
for is_repeat, label in [(True, "Repeat"), (False, "New")]:
    subset = df_2025[df_2025['is_repeat'] == is_repeat]
    dz_subset = subset[subset['in_danger_zone'] == 1]
    non_dz_subset = subset[subset['in_danger_zone'] == 0]
    
    if len(dz_subset) >= 10:
        dz_conv = dz_subset['target'].mean()
        non_dz_conv = non_dz_subset['target'].mean()
        lift = dz_conv / non_dz_conv if non_dz_conv > 0 else 0
        print(f"  {label}: DZ={dz_conv*100:.1f}%, Non-DZ={non_dz_conv*100:.1f}%, Lift={lift:.2f}x")

# =============================================================================
# HYPOTHESIS 7: BLEEDING FIRM INTERACTION
# =============================================================================
print("\n" + "=" * 80)
print("[8/8] HYPOTHESIS 7: Does DZ + Bleeding Firm combo still work?")
print("=" * 80)

# DZ + Bleeding Firm interaction
for year in [2024, 2025]:
    year_df = df[df['year'] == year]
    print(f"\n{year}:")
    
    combos = year_df.groupby(['in_danger_zone', 'is_bleeding_firm'])['target'].agg(['count', 'mean'])
    baseline = year_df['target'].mean()
    
    for (dz, bf), row in combos.iterrows():
        if row['count'] >= 20:
            label = f"DZ={int(dz)}, Bleeding={int(bf)}"
            lift = row['mean'] / baseline if baseline > 0 else 0
            print(f"  {label}: {int(row['count']):5,} leads, {row['mean']*100:.1f}% conv, {lift:.2f}x lift")

# =============================================================================
# SUMMARY & CONCLUSIONS
# =============================================================================
print("\n" + "=" * 80)
print("SUMMARY & CONCLUSIONS")
print("=" * 80)

# Calculate key metrics for summary
dz_lift_2024 = df_2024[df_2024['in_danger_zone'] == 1]['target'].mean() / df_2024['target'].mean()
dz_lift_2025 = df_2025[df_2025['in_danger_zone'] == 1]['target'].mean() / df_2025['target'].mean()

print(f"""
KEY FINDINGS:

1. DANGER ZONE LIFT DECAY:
   - 2024: {dz_lift_2024:.2f}x
   - 2025: {dz_lift_2025:.2f}x
   - Drop: {((dz_lift_2024 - dz_lift_2025) / dz_lift_2024 * 100):.0f}%

2. REPEAT ADVISOR EFFECT:
   - {len(repeat_advisors):,} advisors contacted in both years
   - This is {len(repeat_advisors)/len(advisors_2025)*100:.1f}% of 2025 contacts
   - Repeat advisors convert at: {repeat_conv*100:.2f}%
   - New advisors convert at: {new_conv*100:.2f}%

3. LIKELY CAUSES OF SIGNAL DECAY:
""")

# Determine most likely causes
causes = []

# Check if repeat advisors are the problem
if repeat_conv < new_conv:
    causes.append(f"   ❌ REPEAT CONTACTS: Re-contacting same advisors ({repeat_conv*100:.1f}% < {new_conv*100:.1f}%)")
else:
    causes.append(f"   ✅ Repeat contacts not the issue ({repeat_conv*100:.1f}% ≥ {new_conv*100:.1f}%)")

# Check if DZ lead characteristics changed
dz_moves_2024 = dz_2024['pit_moves_3yr'].mean()
dz_moves_2025 = dz_2025['pit_moves_3yr'].mean()
if abs(dz_moves_2025 - dz_moves_2024) / dz_moves_2024 > 0.2:
    causes.append(f"   ❌ DZ LEADS CHANGED: Avg moves went from {dz_moves_2024:.1f} to {dz_moves_2025:.1f}")
else:
    causes.append(f"   ✅ DZ lead characteristics stable")

# Print causes
for cause in causes:
    print(cause)

print("""
4. RECOMMENDATIONS:
   - The signal decay appears to be [see analysis above]
   - Expected realistic lift going forward: 1.5-2.0x
   - Model should be retrained quarterly as patterns evolve
   - Monitor monthly DZ lift as a leading indicator
""")

# Save detailed report
output_dir = VERSION_2_DIR / 'reports'
output_dir.mkdir(exist_ok=True)
report_file = output_dir / f'signal_decay_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

# Create monthly summary for export
monthly_export = monthly.reset_index()
monthly_export.to_csv(report_file, index=False)
print(f"\n📊 Monthly data saved to: {report_file}")
