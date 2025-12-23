"""
linkedin_success_analysis.py
----------------------------
What makes LinkedIn self-sourced leads convert at 6x the rate?

Key questions:
1. Who are these people? (Firm size, tenure, mobility)
2. What firms do winners come from?
3. What signals predict success within LinkedIn leads?
4. Can we create a "target profile" for SGAs?
"""
from google.cloud import bigquery
import pandas as pd
import numpy as np

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("LINKEDIN SELF-SOURCED SUCCESS ANALYSIS")
print("What makes these leads convert at 6x the rate?")
print("=" * 70)

# ============================================================================
# PART 1: Basic Comparison - LinkedIn vs Provided Lead List
# ============================================================================

print("\n⏳ Loading lead data with features...")

query_compare = """
WITH lead_data AS (
    SELECT 
        l.Id as lead_id,
        l.LeadSource as lead_source,
        l.IsConverted as converted,
        l.Company as company,
        l.CreatedDate,
        EXTRACT(YEAR FROM l.CreatedDate) as year,
        
        -- Features from scoring table
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.num_prior_firms,
        f.pit_moves_3yr,
        f.firm_net_change_12mo,
        f.firm_rep_count_at_contact,
        f.firm_aum_pit,
        
        -- Derived signals
        CASE WHEN f.current_firm_tenure_months BETWEEN 12 AND 24 THEN 1 ELSE 0 END as in_danger_zone,
        CASE WHEN f.firm_net_change_12mo < -5 THEN 1 ELSE 0 END as at_bleeding_firm,
        CASE WHEN f.industry_tenure_months >= 120 THEN 1 ELSE 0 END as is_veteran,
        CASE WHEN f.firm_rep_count_at_contact < 50 THEN 'Small (<50)'
             WHEN f.firm_rep_count_at_contact < 200 THEN 'Medium (50-200)'
             ELSE 'Large (200+)' END as firm_size_bucket
        
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features` f
        ON l.Id = f.lead_id
    WHERE l.LeadSource IN ('Provided Lead List', 'LinkedIn (Self Sourced)')
      AND l.CreatedDate >= '2024-01-01'
)
SELECT * FROM lead_data
"""

df = client.query(query_compare).to_dataframe()

print(f"\n📊 Loaded {len(df):,} leads")

# Basic stats
print("\n" + "=" * 70)
print("PART 1: BASIC COMPARISON")
print("=" * 70)

for source in ['Provided Lead List', 'LinkedIn (Self Sourced)']:
    subset = df[df['lead_source'] == source]
    conv = subset['converted'].mean()
    print(f"\n{source}:")
    print(f"   Total Leads: {len(subset):,}")
    print(f"   Conversions: {subset['converted'].sum():,}")
    print(f"   Conversion Rate: {conv:.2%}")

# ============================================================================
# PART 2: Feature Comparison - What's Different?
# ============================================================================

print("\n" + "=" * 70)
print("PART 2: FEATURE COMPARISON - What's Different?")
print("=" * 70)

features_to_compare = [
    'current_firm_tenure_months',
    'industry_tenure_months', 
    'num_prior_firms',
    'pit_moves_3yr',
    'firm_net_change_12mo',
    'firm_rep_count_at_contact'
]

print(f"\n{'Feature':<30} | {'Provided List':<15} | {'LinkedIn':<15} | {'Difference':<15}")
print("-" * 80)

provided = df[df['lead_source'] == 'Provided Lead List']
linkedin = df[df['lead_source'] == 'LinkedIn (Self Sourced)']

for feat in features_to_compare:
    prov_mean = provided[feat].mean()
    link_mean = linkedin[feat].mean()
    diff_pct = (link_mean - prov_mean) / prov_mean * 100 if prov_mean != 0 else 0
    
    print(f"{feat:<30} | {prov_mean:<15.1f} | {link_mean:<15.1f} | {diff_pct:+.1f}%")

# Signal prevalence
print(f"\n{'Signal':<30} | {'Provided List':<15} | {'LinkedIn':<15}")
print("-" * 65)

for signal in ['in_danger_zone', 'at_bleeding_firm', 'is_veteran']:
    prov_pct = provided[signal].mean() * 100
    link_pct = linkedin[signal].mean() * 100
    print(f"{signal:<30} | {prov_pct:<14.1f}% | {link_pct:<14.1f}%")

# ============================================================================
# PART 3: What Signals Work for LinkedIn Leads?
# ============================================================================

print("\n" + "=" * 70)
print("PART 3: WHAT SIGNALS WORK FOR LINKEDIN LEADS?")
print("=" * 70)

linkedin_only = df[df['lead_source'] == 'LinkedIn (Self Sourced)'].copy()
baseline = linkedin_only['converted'].mean()

print(f"\nLinkedIn Baseline Conversion: {baseline:.2%}")
print(f"\n{'Signal':<35} | {'Without':<12} | {'With':<12} | {'Lift':<10}")
print("-" * 75)

signals_to_test = [
    ('in_danger_zone', 'In Danger Zone (12-24mo tenure)'),
    ('at_bleeding_firm', 'At Bleeding Firm (net chg < -5)'),
    ('is_veteran', 'Is Veteran (10+ yr industry)'),
]

for col, label in signals_to_test:
    without = linkedin_only[linkedin_only[col] == 0]['converted'].mean()
    with_signal = linkedin_only[linkedin_only[col] == 1]['converted'].mean()
    n_with = len(linkedin_only[linkedin_only[col] == 1])
    
    if n_with >= 10 and without > 0:
        lift = with_signal / without
        lift_icon = "🔥" if lift >= 2.0 else ("✅" if lift >= 1.5 else "⚠️")
        print(f"{label:<35} | {without:.1%} ({len(linkedin_only[linkedin_only[col]==0]):,}) | {with_signal:.1%} ({n_with:,}) | {lift:.2f}x {lift_icon}")

# Combo signals
print(f"\n{'Combo Signal':<40} | {'Conv':<10} | {'N':<8} | {'Lift':<10}")
print("-" * 75)

combos = [
    ('DZ + Bleeding', (linkedin_only['in_danger_zone'] == 1) & (linkedin_only['at_bleeding_firm'] == 1)),
    ('DZ + Veteran', (linkedin_only['in_danger_zone'] == 1) & (linkedin_only['is_veteran'] == 1)),
    ('Bleeding + Veteran', (linkedin_only['at_bleeding_firm'] == 1) & (linkedin_only['is_veteran'] == 1)),
    ('DZ + Bleeding + Veteran', (linkedin_only['in_danger_zone'] == 1) & (linkedin_only['at_bleeding_firm'] == 1) & (linkedin_only['is_veteran'] == 1)),
]

for name, mask in combos:
    subset = linkedin_only[mask]
    if len(subset) >= 5:
        conv = subset['converted'].mean()
        lift = conv / baseline if baseline > 0 else 0
        lift_icon = "🔥" if lift >= 2.0 else ("✅" if lift >= 1.5 else "⚠️")
        print(f"{name:<40} | {conv:.1%} | {len(subset):<8,} | {lift:.2f}x {lift_icon}")

# ============================================================================
# PART 4: Firm Size Analysis
# ============================================================================

print("\n" + "=" * 70)
print("PART 4: FIRM SIZE - Does It Matter?")
print("=" * 70)

print(f"\n{'Source':<25} | {'Firm Size':<20} | {'Conv':<10} | {'N':<10}")
print("-" * 70)

for source in ['Provided Lead List', 'LinkedIn (Self Sourced)']:
    subset = df[df['lead_source'] == source]
    for size in ['Small (<50)', 'Medium (50-200)', 'Large (200+)']:
        size_subset = subset[subset['firm_size_bucket'] == size]
        if len(size_subset) >= 20:
            conv = size_subset['converted'].mean()
            print(f"{source:<25} | {size:<20} | {conv:.2%} | {len(size_subset):,}")

# ============================================================================
# PART 5: Top Converting Firms for LinkedIn Leads
# ============================================================================

print("\n" + "=" * 70)
print("PART 5: TOP FIRMS FOR LINKEDIN LEADS")
print("(Firms with 5+ LinkedIn leads and highest conversion)")
print("=" * 70)

linkedin_firms = linkedin_only.groupby('company').agg({
    'converted': ['sum', 'count', 'mean']
}).reset_index()
linkedin_firms.columns = ['company', 'wins', 'total', 'conv_rate']
linkedin_firms = linkedin_firms[linkedin_firms['total'] >= 5]
linkedin_firms = linkedin_firms.sort_values('conv_rate', ascending=False)

print(f"\n{'Firm':<40} | {'Wins':<6} | {'Total':<6} | {'Conv':<8}")
print("-" * 65)

for _, row in linkedin_firms.head(15).iterrows():
    print(f"{str(row['company'])[:40]:<40} | {int(row['wins']):<6} | {int(row['total']):<6} | {row['conv_rate']:.1%}")

# ============================================================================
# PART 6: Profile of LinkedIn WINNERS
# ============================================================================

print("\n" + "=" * 70)
print("PART 6: PROFILE OF LINKEDIN WINNERS")
print("What do converted LinkedIn leads look like?")
print("=" * 70)

linkedin_winners = linkedin_only[linkedin_only['converted'] == True]
linkedin_losers = linkedin_only[linkedin_only['converted'] == False]

print(f"\nLinkedIn Winners: {len(linkedin_winners)}")
print(f"LinkedIn Non-Converts: {len(linkedin_losers)}")

print(f"\n{'Feature':<30} | {'Winners':<15} | {'Non-Converts':<15} | {'Diff':<15}")
print("-" * 80)

for feat in features_to_compare:
    win_mean = linkedin_winners[feat].mean()
    lose_mean = linkedin_losers[feat].mean()
    diff = win_mean - lose_mean
    diff_pct = (win_mean - lose_mean) / lose_mean * 100 if lose_mean != 0 else 0
    
    indicator = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➡️"
    print(f"{feat:<30} | {win_mean:<15.1f} | {lose_mean:<15.1f} | {diff_pct:+.1f}% {indicator}")

# Signal prevalence in winners
print(f"\n{'Signal':<30} | {'Winners':<15} | {'Non-Converts':<15} | {'Index':<10}")
print("-" * 75)

for signal in ['in_danger_zone', 'at_bleeding_firm', 'is_veteran']:
    win_pct = linkedin_winners[signal].mean()
    lose_pct = linkedin_losers[signal].mean()
    index = win_pct / lose_pct if lose_pct > 0 else 0
    
    indicator = "🔥" if index >= 2.0 else ("✅" if index >= 1.3 else "⚠️")
    print(f"{signal:<30} | {win_pct:.1%} | {lose_pct:.1%} | {index:.2f}x {indicator}")

# ============================================================================
# PART 7: ACTIONABLE TARGET PROFILE
# ============================================================================

print("\n" + "=" * 70)
print("PART 7: ACTIONABLE TARGET PROFILE FOR SGAs")
print("=" * 70)

print("""
Based on the analysis, here's what to tell your SGAs:

🎯 IDEAL LINKEDIN TARGET PROFILE:
""")

# Calculate the ideal profile
win_tenure = linkedin_winners['current_firm_tenure_months'].median()
win_industry = linkedin_winners['industry_tenure_months'].median()
win_moves = linkedin_winners['pit_moves_3yr'].median()
win_firm_size = linkedin_winners['firm_rep_count_at_contact'].median()

print(f"   1. TENURE: Look for advisors {win_tenure:.0f} months at current firm")
print(f"      (Sweet spot: 12-24 months = 'Danger Zone')")
print(f"")
print(f"   2. EXPERIENCE: Target advisors with ~{win_industry:.0f} months in industry")
print(f"      ({win_industry/12:.0f}+ years experience)")
print(f"")
print(f"   3. MOBILITY: Advisors with {win_moves:.0f}+ moves in last 3 years")
print(f"")
print(f"   4. FIRM SIZE: ~{win_firm_size:.0f} reps at firm")

# Best combo
print(f"""
💎 THE GOLDEN COMBO (if you can find it):
   - In Danger Zone (1-2 years at firm)
   - At a Bleeding Firm (losing advisors)
   - Is a Veteran (10+ years in industry)
""")

# Top firms to target
print("🏢 TOP FIRMS TO HUNT ON LINKEDIN:")
for _, row in linkedin_firms.head(5).iterrows():
    if row['conv_rate'] >= 0.10:
        print(f"   - {row['company']} ({row['conv_rate']:.0%} conversion)")

print("\n" + "=" * 70)
print("SUMMARY: WHY LINKEDIN WORKS BETTER")
print("=" * 70)

prov_baseline = provided['converted'].mean()
link_baseline = linkedin_only['converted'].mean()

print(f"""
📊 THE DATA:
   Provided Lead List: {prov_baseline:.2%} conversion
   LinkedIn Self-Sourced: {link_baseline:.2%} conversion
   LinkedIn is {link_baseline/prov_baseline:.1f}x better

🤔 POSSIBLE REASONS:
   1. SGAs pick better leads intuitively (human judgment > algorithm)
   2. LinkedIn = warmer outreach (they see your profile, feel connection)
   3. Self-sourced leads come from SGAs' existing network/referrals
   4. Provided lists are "cold" - no context, no relationship

💡 RECOMMENDATION:
   Instead of scoring Provided Lead Lists...
   Give SGAs FINTRX data to HELP them pick who to target on LinkedIn.
   
   "Here are 500 advisors at bleeding firms in danger zone. 
    Find them on LinkedIn and reach out."
""")
