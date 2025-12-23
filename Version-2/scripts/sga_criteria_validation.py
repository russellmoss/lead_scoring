"""
sga_criteria_validation.py
--------------------------
Tests the SGA's self-sourcing criteria against actual conversion data.

Key SGA Criteria (from interviews):
1. Small firms (1-10 reps) - "owners with portable books"
2. Exclude wirehouses/banks (Perry's list)
3. 4-10 years at current firm (Eleni's "sweet spot")
4. 8-30 years total experience
5. Prior wirehouse experience (moved from big firm to RIA)
6. CFP accreditation (if available)
"""
from google.cloud import bigquery
import pandas as pd
import numpy as np

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("SGA CRITERIA VALIDATION")
print("Testing if we can model what makes SGAs successful")
print("=" * 70)

# Perry's exclusion list (wirehouses/banks)
EXCLUDED_FIRMS = [
    'Fidelity', 'State Farm', 'Edelman', 'NYLife', 'New York Life',
    'Allstate', 'Etrade', 'E-Trade', 'Schwab', 'Charles Schwab',
    'Prudential', 'Transamerica', 'Farm Bureau', 'Ameriprise',
    'T. Rowe Price', 'Edward Jones', 'Fisher Investments', 
    'Vanguard', 'First Command', 'Creative Planning',
    'Bank of America', 'Wells Fargo', 'JP Morgan', 'JPMorgan',
    'Morgan Stanley', 'UBS', 'Merrill Lynch', 'Merrill'
]

print("\n⏳ Loading comprehensive lead data...")

query = """
WITH lead_features AS (
    SELECT 
        l.Id as lead_id,
        l.LeadSource as lead_source,
        l.IsConverted as converted,
        l.Company as company,
        l.CreatedDate,
        
        -- Core features
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.num_prior_firms,
        f.pit_moves_3yr,
        f.firm_net_change_12mo,
        f.firm_rep_count_at_contact,
        f.firm_aum_pit
        
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features` f
        ON l.Id = f.lead_id
    WHERE l.LeadSource IN ('Provided Lead List', 'LinkedIn (Self Sourced)')
      AND l.CreatedDate >= '2024-01-01'
      AND f.lead_id IS NOT NULL
),

-- Get employment history for "prior wirehouse" signal
emp_history AS (
    SELECT 
        RIA_CONTACT_CRD_ID as advisor_crd,
        COUNT(DISTINCT PREVIOUS_REGISTRATION_COMPANY_CRD_ID) as total_firms,
        -- Check if any prior firm was a wirehouse
        MAX(CASE 
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%MERRILL%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%MORGAN STANLEY%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%UBS%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%WELLS FARGO%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%EDWARD JONES%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%AMERIPRISE%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%FIDELITY%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%SCHWAB%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%PRUDENTIAL%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%RAYMOND JAMES%' THEN 1
            WHEN UPPER(PREVIOUS_REGISTRATION_COMPANY_NAME) LIKE '%LPL%' THEN 1
            ELSE 0
        END) as had_wirehouse_experience
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL  -- Only prior jobs
    GROUP BY 1
)

SELECT 
    lf.*,
    COALESCE(eh.had_wirehouse_experience, 0) as prior_wirehouse
FROM lead_features lf
LEFT JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l2 ON lf.lead_id = l2.Id
LEFT JOIN emp_history eh ON SAFE_CAST(REGEXP_REPLACE(CAST(l2.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = eh.advisor_crd
"""

df = client.query(query).to_dataframe()
print(f"✅ Loaded {len(df):,} leads with features")

# ============================================================================
# Create SGA-style filters
# ============================================================================

# Filter 1: Small firm (1-10 reps) - "owners with portable books"
df['is_small_firm'] = (df['firm_rep_count_at_contact'] <= 10).astype(int)

# Filter 2: Exclude wirehouses (check company name)
def is_excluded_firm(company):
    if pd.isna(company):
        return 0
    company_upper = str(company).upper()
    for excl in EXCLUDED_FIRMS:
        if excl.upper() in company_upper:
            return 1
    return 0

df['is_wirehouse'] = df['company'].apply(is_excluded_firm)
df['not_wirehouse'] = 1 - df['is_wirehouse']

# Filter 3: Eleni's sweet spot (4-10 years = 48-120 months at current firm)
df['in_sweet_spot'] = ((df['current_firm_tenure_months'] >= 48) & 
                        (df['current_firm_tenure_months'] <= 120)).astype(int)

# Filter 4: Experienced (8-30 years = 96-360 months total)
df['is_experienced'] = ((df['industry_tenure_months'] >= 96) & 
                         (df['industry_tenure_months'] <= 360)).astype(int)

# Filter 5: Our old Danger Zone (1-2 years)
df['in_danger_zone'] = ((df['current_firm_tenure_months'] >= 12) & 
                         (df['current_firm_tenure_months'] <= 24)).astype(int)

# Filter 6: Perry's ideal (3-10 years at current = 36-120 months)
df['perry_tenure'] = ((df['current_firm_tenure_months'] >= 36) & 
                       (df['current_firm_tenure_months'] <= 120)).astype(int)

# Filter 7: Prior wirehouse experience
df['prior_wirehouse'] = df['prior_wirehouse'].fillna(0).astype(int)

# ============================================================================
# PART 1: Test individual SGA criteria
# ============================================================================

print("\n" + "=" * 70)
print("PART 1: INDIVIDUAL SGA CRITERIA VS OUR MODEL")
print("=" * 70)

def test_signal(df, signal_col, signal_name):
    """Test a signal across both lead sources"""
    results = []
    
    for source in ['Provided Lead List', 'LinkedIn (Self Sourced)']:
        subset = df[df['lead_source'] == source]
        baseline = subset['converted'].mean()
        
        with_signal = subset[subset[signal_col] == 1]
        without_signal = subset[subset[signal_col] == 0]
        
        if len(with_signal) >= 10:
            conv_with = with_signal['converted'].mean()
            lift = conv_with / baseline if baseline > 0 else 0
            results.append({
                'source': source,
                'signal': signal_name,
                'baseline': baseline,
                'with_signal_conv': conv_with,
                'with_signal_n': len(with_signal),
                'lift': lift
            })
    
    return results

signals_to_test = [
    ('in_danger_zone', 'Our Model: Danger Zone (1-2yr)'),
    ('in_sweet_spot', 'SGA: Sweet Spot (4-10yr)'),
    ('perry_tenure', 'SGA: Perry Tenure (3-10yr)'),
    ('is_small_firm', 'SGA: Small Firm (≤10 reps)'),
    ('not_wirehouse', 'SGA: Not a Wirehouse'),
    ('is_experienced', 'SGA: Experienced (8-30yr total)'),
    ('prior_wirehouse', 'SGA: Prior Wirehouse Experience'),
]

print(f"\n{'Signal':<40} | {'Source':<12} | {'Conv':<8} | {'N':<8} | {'Lift':<8}")
print("-" * 85)

all_results = []
for signal_col, signal_name in signals_to_test:
    results = test_signal(df, signal_col, signal_name)
    all_results.extend(results)
    
    for r in results:
        source_short = 'LinkedIn' if 'LinkedIn' in r['source'] else 'Provided'
        lift_icon = "🔥" if r['lift'] >= 2.0 else ("✅" if r['lift'] >= 1.5 else ("⚠️" if r['lift'] >= 1.2 else "❌"))
        print(f"{r['signal']:<40} | {source_short:<12} | {r['with_signal_conv']:.2%} | {r['with_signal_n']:<8,} | {r['lift']:.2f}x {lift_icon}")

# ============================================================================
# PART 2: Compare Danger Zone vs Sweet Spot
# ============================================================================

print("\n" + "=" * 70)
print("PART 2: DANGER ZONE (1-2yr) VS SWEET SPOT (4-10yr)")
print("=" * 70)

for source in ['Provided Lead List', 'LinkedIn (Self Sourced)']:
    subset = df[df['lead_source'] == source]
    baseline = subset['converted'].mean()
    
    dz = subset[subset['in_danger_zone'] == 1]
    ss = subset[subset['in_sweet_spot'] == 1]
    
    source_short = 'LinkedIn' if 'LinkedIn' in source else 'Provided'
    
    print(f"\n{source_short}:")
    print(f"  Baseline: {baseline:.2%}")
    print(f"  Danger Zone (1-2yr): {dz['converted'].mean():.2%} (n={len(dz):,}) - Lift: {dz['converted'].mean()/baseline:.2f}x")
    print(f"  Sweet Spot (4-10yr): {ss['converted'].mean():.2%} (n={len(ss):,}) - Lift: {ss['converted'].mean()/baseline:.2f}x")

# ============================================================================
# PART 3: Build the "SGA Model" - Combined Criteria
# ============================================================================

print("\n" + "=" * 70)
print("PART 3: THE 'SGA MODEL' - COMBINED CRITERIA")
print("=" * 70)

# SGA Platinum: Small firm + Sweet spot tenure + Experienced + Not wirehouse
df['sga_platinum'] = (
    (df['is_small_firm'] == 1) & 
    (df['in_sweet_spot'] == 1) & 
    (df['is_experienced'] == 1) & 
    (df['not_wirehouse'] == 1)
).astype(int)

# SGA Gold: Perry's profile (3-10yr tenure + experienced + not wirehouse)
df['sga_gold'] = (
    (df['perry_tenure'] == 1) & 
    (df['is_experienced'] == 1) & 
    (df['not_wirehouse'] == 1)
).astype(int)

# SGA Silver: Small firm + not wirehouse
df['sga_silver'] = (
    (df['is_small_firm'] == 1) & 
    (df['not_wirehouse'] == 1)
).astype(int)

# Our old model: DZ + Bleeding + Veteran
df['at_bleeding_firm'] = (df['firm_net_change_12mo'] < -5).astype(int)
df['is_veteran'] = (df['industry_tenure_months'] >= 120).astype(int)
df['our_platinum'] = (
    (df['in_danger_zone'] == 1) & 
    (df['at_bleeding_firm'] == 1) & 
    (df['is_veteran'] == 1)
).astype(int)

combos = [
    ('our_platinum', 'Our Model: DZ + Bleeding + Veteran'),
    ('sga_platinum', 'SGA Model: Small + Sweet Spot + Exp + Not WH'),
    ('sga_gold', 'SGA Gold: Perry Tenure + Exp + Not WH'),
    ('sga_silver', 'SGA Silver: Small Firm + Not WH'),
]

print(f"\n{'Model':<50} | {'Source':<10} | {'Conv':<8} | {'N':<8} | {'Lift':<8}")
print("-" * 95)

for combo_col, combo_name in combos:
    for source in ['Provided Lead List', 'LinkedIn (Self Sourced)']:
        subset = df[df['lead_source'] == source]
        baseline = subset['converted'].mean()
        
        with_combo = subset[subset[combo_col] == 1]
        
        if len(with_combo) >= 5:
            conv = with_combo['converted'].mean()
            lift = conv / baseline if baseline > 0 else 0
            source_short = 'LinkedIn' if 'LinkedIn' in source else 'Provided'
            lift_icon = "🔥" if lift >= 2.5 else ("✅" if lift >= 1.5 else "⚠️")
            print(f"{combo_name:<50} | {source_short:<10} | {conv:.2%} | {len(with_combo):<8,} | {lift:.2f}x {lift_icon}")

# ============================================================================
# PART 4: The Wirehouse Breakout Signal
# ============================================================================

print("\n" + "=" * 70)
print("PART 4: THE 'WIREHOUSE BREAKOUT' SIGNAL")
print("(Advisors who left a wirehouse for a smaller RIA)")
print("=" * 70)

# Wirehouse breakout: Currently at small firm + has wirehouse in history
df['wirehouse_breakout'] = (
    (df['is_small_firm'] == 1) & 
    (df['prior_wirehouse'] == 1)
).astype(int)

for source in ['Provided Lead List', 'LinkedIn (Self Sourced)']:
    subset = df[df['lead_source'] == source]
    baseline = subset['converted'].mean()
    
    breakout = subset[subset['wirehouse_breakout'] == 1]
    
    if len(breakout) >= 5:
        conv = breakout['converted'].mean()
        lift = conv / baseline if baseline > 0 else 0
        source_short = 'LinkedIn' if 'LinkedIn' in source else 'Provided'
        print(f"\n{source_short} - Wirehouse Breakout Signal:")
        print(f"  Volume: {len(breakout):,} leads")
        print(f"  Conversion: {conv:.2%}")
        print(f"  Lift: {lift:.2f}x {'🔥' if lift >= 2.0 else '✅' if lift >= 1.5 else '⚠️'}")

# ============================================================================
# PART 5: Volume Check - Can we fill 3,750 leads/month?
# ============================================================================

print("\n" + "=" * 70)
print("PART 5: VOLUME CHECK")
print("=" * 70)

# Only look at Provided Lead List (that's what we're scoring)
provided = df[df['lead_source'] == 'Provided Lead List']
total_provided = len(provided)

print(f"\nTotal Provided Lead List: {total_provided:,}")
print(f"\nFilter Volumes:")

filters = [
    ('our_platinum', 'Our Model: DZ + Bleeding + Veteran'),
    ('sga_platinum', 'SGA Platinum: Small + Sweet Spot + Exp'),
    ('sga_gold', 'SGA Gold: Perry Tenure + Exp'),
    ('sga_silver', 'SGA Silver: Small Firm'),
    ('is_small_firm', 'Just: Small Firm (≤10)'),
    ('not_wirehouse', 'Just: Not Wirehouse'),
    ('in_sweet_spot', 'Just: Sweet Spot (4-10yr)'),
]

print(f"\n{'Filter':<45} | {'Volume':<10} | {'% of Pool':<10} | {'Conv':<8}")
print("-" * 80)

for col, name in filters:
    subset = provided[provided[col] == 1]
    pct = len(subset) / total_provided * 100
    conv = subset['converted'].mean() if len(subset) > 0 else 0
    print(f"{name:<45} | {len(subset):<10,} | {pct:<10.1f}% | {conv:.2%}")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY: WHAT THE SGAs KNOW THAT WE DIDN'T")
print("=" * 70)

print("""
🔑 KEY FINDINGS:

1. TENURE WINDOW IS WRONG:
   - Our model: 1-2 years ("Danger Zone")
   - SGAs target: 4-10 years ("Sweet Spot")
   - Eleni: "Under 4 is too new; after 4, clients are loyal enough to move"

2. FIRM SIZE MATTERS:
   - SGAs target firms with ≤10 reps ("owners with portable books")
   - Our model doesn't filter on this

3. EXCLUDE WIREHOUSES:
   - SGAs actively avoid banks/wirehouses (Perry's exclusion list)
   - "Bank owns the relationship, not the advisor"

4. PRIOR WIREHOUSE = GOOD:
   - SGAs like advisors who LEFT a wirehouse for an RIA
   - "Shows they can move and want independence"

5. EXPERIENCE SWEET SPOT:
   - 8-30 years total experience
   - Not too junior (no book), not too senior (retiring)

📊 NEW FEATURES TO ADD:
   - is_small_firm (≤10 reps)
   - is_wirehouse (exclusion filter)
   - prior_wirehouse_experience (employment history)
   - sweet_spot_tenure (4-10 years)
   - perry_tenure (3-10 years)
""")
