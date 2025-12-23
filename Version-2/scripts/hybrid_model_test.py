"""
hybrid_model_test.py
--------------------
Tests the hybrid model: DZ + Not Wirehouse + Experienced

Combines:
- Our signal: Danger Zone (1-2yr tenure) - highest lift
- SGA filter: Not Wirehouse - quality filter
- SGA filter: Experienced (8-30yr) - quality filter
"""
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("HYBRID MODEL TEST")
print("DZ + Not Wirehouse + Experienced")
print("=" * 70)

# Perry's exclusion list
EXCLUDED_FIRMS = [
    'Fidelity', 'State Farm', 'Edelman', 'NYLife', 'New York Life',
    'Allstate', 'Etrade', 'E-Trade', 'Schwab', 'Charles Schwab',
    'Prudential', 'Transamerica', 'Farm Bureau', 'Ameriprise',
    'T. Rowe Price', 'Edward Jones', 'Fisher Investments', 
    'Vanguard', 'First Command', 'Creative Planning',
    'Bank of America', 'Wells Fargo', 'JP Morgan', 'JPMorgan',
    'Morgan Stanley', 'UBS', 'Merrill Lynch', 'Merrill'
]

print("\n⏳ Loading data...")

query = """
SELECT 
    l.Id as lead_id,
    l.LeadSource as lead_source,
    l.IsConverted as converted,
    l.Company as company,
    
    f.current_firm_tenure_months,
    f.industry_tenure_months,
    f.firm_net_change_12mo,
    f.firm_rep_count_at_contact

FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
LEFT JOIN `savvy-gtm-analytics.ml_features.lead_scoring_features` f
    ON l.Id = f.lead_id
WHERE l.LeadSource IN ('Provided Lead List', 'LinkedIn (Self Sourced)')
  AND l.CreatedDate >= '2024-01-01'
  AND f.lead_id IS NOT NULL
"""

df = client.query(query).to_dataframe()
print(f"✅ Loaded {len(df):,} leads")

# Create filters
df['in_danger_zone'] = ((df['current_firm_tenure_months'] >= 12) & 
                         (df['current_firm_tenure_months'] <= 24)).astype(int)

df['is_experienced'] = ((df['industry_tenure_months'] >= 96) & 
                         (df['industry_tenure_months'] <= 360)).astype(int)

df['at_bleeding_firm'] = (df['firm_net_change_12mo'] < -5).astype(int)

df['is_veteran'] = (df['industry_tenure_months'] >= 120).astype(int)

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

# ============================================================================
# Test all combinations
# ============================================================================

print("\n" + "=" * 70)
print("ALL MODEL COMBINATIONS - Provided Lead List")
print("=" * 70)

provided = df[df['lead_source'] == 'Provided Lead List']
baseline = provided['converted'].mean()

combos = [
    # Original models
    ('DZ only', 
     (provided['in_danger_zone'] == 1)),
    
    ('DZ + Bleeding', 
     (provided['in_danger_zone'] == 1) & (provided['at_bleeding_firm'] == 1)),
    
    ('DZ + Veteran (old model)', 
     (provided['in_danger_zone'] == 1) & (provided['is_veteran'] == 1)),
    
    ('DZ + Bleeding + Veteran (our current best)', 
     (provided['in_danger_zone'] == 1) & (provided['at_bleeding_firm'] == 1) & (provided['is_veteran'] == 1)),
    
    # NEW HYBRIDS with SGA filters
    ('DZ + Not Wirehouse', 
     (provided['in_danger_zone'] == 1) & (provided['not_wirehouse'] == 1)),
    
    ('DZ + Experienced', 
     (provided['in_danger_zone'] == 1) & (provided['is_experienced'] == 1)),
    
    ('DZ + Not WH + Experienced (HYBRID)', 
     (provided['in_danger_zone'] == 1) & (provided['not_wirehouse'] == 1) & (provided['is_experienced'] == 1)),
    
    ('DZ + Not WH + Exp + Bleeding (HYBRID+)', 
     (provided['in_danger_zone'] == 1) & (provided['not_wirehouse'] == 1) & 
     (provided['is_experienced'] == 1) & (provided['at_bleeding_firm'] == 1)),
    
    # SGA model for comparison
    ('SGA Platinum (Small + Sweet Spot + Exp + Not WH)', 
     (provided['firm_rep_count_at_contact'] <= 10) & 
     (provided['current_firm_tenure_months'] >= 48) & 
     (provided['current_firm_tenure_months'] <= 120) &
     (provided['is_experienced'] == 1) & (provided['not_wirehouse'] == 1)),
]

print(f"\nBaseline Conversion: {baseline:.2%}")
print(f"\n{'Model':<50} | {'Conv':<8} | {'Lift':<8} | {'Volume':<8} | {'Wins':<6}")
print("-" * 95)

results = []
for name, mask in combos:
    subset = provided[mask]
    if len(subset) >= 5:
        conv = subset['converted'].mean()
        lift = conv / baseline if baseline > 0 else 0
        wins = subset['converted'].sum()
        
        lift_icon = "🔥" if lift >= 2.5 else ("✅" if lift >= 2.0 else ("⚠️" if lift >= 1.5 else "❌"))
        
        results.append({
            'name': name,
            'conv': conv,
            'lift': lift,
            'volume': len(subset),
            'wins': wins
        })
        
        print(f"{name:<50} | {conv:.2%} | {lift:.2f}x {lift_icon} | {len(subset):<8,} | {int(wins):<6}")

# ============================================================================
# LinkedIn comparison
# ============================================================================

print("\n" + "=" * 70)
print("SAME MODELS - LinkedIn (Self Sourced)")
print("=" * 70)

linkedin = df[df['lead_source'] == 'LinkedIn (Self Sourced)']
baseline_li = linkedin['converted'].mean()

print(f"\nBaseline Conversion: {baseline_li:.2%}")
print(f"\n{'Model':<50} | {'Conv':<8} | {'Lift':<8} | {'Volume':<8}")
print("-" * 85)

linkedin_combos = [
    ('DZ + Bleeding + Veteran (our current)', 
     (linkedin['in_danger_zone'] == 1) & (linkedin['at_bleeding_firm'] == 1) & (linkedin['is_veteran'] == 1)),
    
    ('DZ + Not WH + Experienced (HYBRID)', 
     (linkedin['in_danger_zone'] == 1) & (linkedin['not_wirehouse'] == 1) & (linkedin['is_experienced'] == 1)),
    
    ('DZ + Not WH + Exp + Bleeding (HYBRID+)', 
     (linkedin['in_danger_zone'] == 1) & (linkedin['not_wirehouse'] == 1) & 
     (linkedin['is_experienced'] == 1) & (linkedin['at_bleeding_firm'] == 1)),
]

for name, mask in linkedin_combos:
    subset = linkedin[mask]
    if len(subset) >= 5:
        conv = subset['converted'].mean()
        lift = conv / baseline_li if baseline_li > 0 else 0
        lift_icon = "🔥" if lift >= 2.5 else ("✅" if lift >= 2.0 else ("⚠️" if lift >= 1.5 else "❌"))
        print(f"{name:<50} | {conv:.2%} | {lift:.2f}x {lift_icon} | {len(subset):<8,}")

# ============================================================================
# Winner comparison
# ============================================================================

print("\n" + "=" * 70)
print("HEAD-TO-HEAD: BEST MODELS")
print("=" * 70)

print("""
COMPARING TOP MODELS FOR PROVIDED LEAD LISTS:
""")

# Find best models
sorted_results = sorted(results, key=lambda x: x['lift'], reverse=True)

print(f"{'Rank':<5} | {'Model':<50} | {'Conv':<8} | {'Lift':<8} | {'Volume':<8}")
print("-" * 90)

for i, r in enumerate(sorted_results[:5], 1):
    lift_icon = "🔥" if r['lift'] >= 2.5 else ("✅" if r['lift'] >= 2.0 else "⚠️")
    print(f"{i:<5} | {r['name']:<50} | {r['conv']:.2%} | {r['lift']:.2f}x {lift_icon} | {r['volume']:<8,}")

# ============================================================================
# Recommendation
# ============================================================================

print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)

# Find hybrid model result
hybrid = next((r for r in results if 'HYBRID' in r['name'] and 'HYBRID+' not in r['name']), None)
hybrid_plus = next((r for r in results if 'HYBRID+' in r['name']), None)
our_current = next((r for r in results if 'our current' in r['name']), None)
sga = next((r for r in results if 'SGA Platinum' in r['name']), None)

print(f"""
📊 COMPARISON:

| Model                          | Conv   | Lift  | Volume |
|--------------------------------|--------|-------|--------|
| Our Current (DZ+Bleed+Vet)     | {our_current['conv']:.2%} | {our_current['lift']:.2f}x | {our_current['volume']:,} |
| HYBRID (DZ+NotWH+Exp)          | {hybrid['conv']:.2%} | {hybrid['lift']:.2f}x | {hybrid['volume']:,} |
| HYBRID+ (DZ+NotWH+Exp+Bleed)   | {hybrid_plus['conv']:.2%} | {hybrid_plus['lift']:.2f}x | {hybrid_plus['volume']:,} |
| SGA Platinum                   | {sga['conv']:.2%} | {sga['lift']:.2f}x | {sga['volume']:,} |
""")

# Calculate expected wins per month
monthly_need = 3750
our_pct = our_current['volume'] / len(provided)
hybrid_pct = hybrid['volume'] / len(provided)
hybrid_plus_pct = hybrid_plus['volume'] / len(provided)

print(f"""
💰 EXPECTED MONTHLY YIELD (from 3,750 leads):

| Model                    | Leads in Tier | Expected Wins |
|--------------------------|---------------|---------------|
| Our Current              | ~{int(monthly_need * our_pct):,} | ~{int(monthly_need * our_pct * our_current['conv']):,} |
| HYBRID                   | ~{int(monthly_need * hybrid_pct):,} | ~{int(monthly_need * hybrid_pct * hybrid['conv']):,} |
| HYBRID+                  | ~{int(monthly_need * hybrid_plus_pct):,} | ~{int(monthly_need * hybrid_plus_pct * hybrid_plus['conv']):,} |

🎯 VERDICT:
""")

if hybrid['lift'] > our_current['lift'] and hybrid['volume'] > our_current['volume']:
    print("   ✅ HYBRID WINS! Higher lift AND more volume than current model.")
elif hybrid['volume'] > our_current['volume'] * 2:
    print("   ✅ HYBRID is better for VOLUME - more leads to work with.")
else:
    print("   ⚠️ Trade-off: Check which metric matters more for your use case.")
