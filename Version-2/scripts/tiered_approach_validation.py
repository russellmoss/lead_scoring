"""
tiered_approach_validation.py
-----------------------------
Validates the "Perfect Storm" tiered prospecting approach on 2025 data.

Tests if combining Danger Zone + Bleeding Firm + Veteran actually delivers >2.0x lift.
"""
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("TIERED PROSPECTING VALIDATION")
print("Testing the 'Perfect Storm' approach on 2025 Provided Lead Lists")
print("=" * 70)

query = """
WITH base_data AS (
    SELECT 
        l.Id,
        l.IsConverted,
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.num_prior_firms,
        f.firm_net_change_12mo,
        f.pit_moves_3yr,
        
        -- Core Signals
        CASE WHEN f.current_firm_tenure_months BETWEEN 12 AND 24 THEN 1 ELSE 0 END as in_danger_zone,
        CASE WHEN f.firm_net_change_12mo < -10 THEN 1 ELSE 0 END as is_bleeding_severe,
        CASE WHEN f.firm_net_change_12mo < -5 THEN 1 ELSE 0 END as is_bleeding_moderate,
        CASE WHEN f.firm_net_change_12mo < 0 THEN 1 ELSE 0 END as is_bleeding_any,
        CASE WHEN f.industry_tenure_months >= 120 THEN 1 ELSE 0 END as is_veteran,
        CASE WHEN f.industry_tenure_months >= 60 THEN 1 ELSE 0 END as is_experienced
        
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features` f
    JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l ON f.lead_id = l.Id
    WHERE EXTRACT(YEAR FROM l.CreatedDate) = 2025
      AND l.LeadSource = 'Provided Lead List'
)

SELECT
    -- Baseline
    COUNT(*) as total_leads,
    SUM(CAST(IsConverted AS INT64)) as total_wins,
    AVG(CAST(IsConverted AS INT64)) as baseline_conv,
    
    -- ===========================================
    -- TIER 1: PLATINUM - DZ + Bleeding Severe + Veteran
    -- ===========================================
    COUNTIF(in_danger_zone = 1 AND is_bleeding_severe = 1 AND is_veteran = 1) as t1_count,
    COUNTIF(in_danger_zone = 1 AND is_bleeding_severe = 1 AND is_veteran = 1 AND IsConverted = TRUE) as t1_wins,
    
    -- ===========================================
    -- TIER 1B: PLATINUM-LITE - DZ + Bleeding Moderate + Veteran  
    -- ===========================================
    COUNTIF(in_danger_zone = 1 AND is_bleeding_moderate = 1 AND is_veteran = 1) as t1b_count,
    COUNTIF(in_danger_zone = 1 AND is_bleeding_moderate = 1 AND is_veteran = 1 AND IsConverted = TRUE) as t1b_wins,
    
    -- ===========================================
    -- TIER 2: GOLD - DZ + Bleeding (any level)
    -- ===========================================
    COUNTIF(in_danger_zone = 1 AND is_bleeding_any = 1) as t2_count,
    COUNTIF(in_danger_zone = 1 AND is_bleeding_any = 1 AND IsConverted = TRUE) as t2_wins,
    
    -- ===========================================
    -- TIER 2B: GOLD-PLUS - DZ + Bleeding Moderate (net change < -5)
    -- ===========================================
    COUNTIF(in_danger_zone = 1 AND is_bleeding_moderate = 1) as t2b_count,
    COUNTIF(in_danger_zone = 1 AND is_bleeding_moderate = 1 AND IsConverted = TRUE) as t2b_wins,
    
    -- ===========================================
    -- TIER 3: SILVER - DZ + Veteran (no bleeding requirement)
    -- ===========================================
    COUNTIF(in_danger_zone = 1 AND is_veteran = 1) as t3_count,
    COUNTIF(in_danger_zone = 1 AND is_veteran = 1 AND IsConverted = TRUE) as t3_wins,
    
    -- ===========================================
    -- TIER 4: BRONZE - Just Danger Zone
    -- ===========================================
    COUNTIF(in_danger_zone = 1) as t4_count,
    COUNTIF(in_danger_zone = 1 AND IsConverted = TRUE) as t4_wins,
    
    -- ===========================================
    -- ALTERNATE: Bleeding Firm ONLY (no DZ requirement)
    -- ===========================================
    COUNTIF(is_bleeding_severe = 1) as bleed_only_count,
    COUNTIF(is_bleeding_severe = 1 AND IsConverted = TRUE) as bleed_only_wins,
    
    -- ===========================================
    -- ALTERNATE: Bleeding + Veteran (no DZ)
    -- ===========================================
    COUNTIF(is_bleeding_moderate = 1 AND is_veteran = 1) as bleed_vet_count,
    COUNTIF(is_bleeding_moderate = 1 AND is_veteran = 1 AND IsConverted = TRUE) as bleed_vet_wins,
    
    -- ===========================================
    -- SANITY CHECK: What % of leads have each signal?
    -- ===========================================
    AVG(CAST(in_danger_zone AS FLOAT64)) as pct_in_dz,
    AVG(CAST(is_bleeding_any AS FLOAT64)) as pct_bleeding_any,
    AVG(CAST(is_bleeding_moderate AS FLOAT64)) as pct_bleeding_mod,
    AVG(CAST(is_bleeding_severe AS FLOAT64)) as pct_bleeding_severe,
    AVG(CAST(is_veteran AS FLOAT64)) as pct_veteran

FROM base_data
"""

print("\n⏳ Querying 2025 Provided Lead List data...")
df = client.query(query).to_dataframe()

baseline = df['baseline_conv'][0]
total = df['total_leads'][0]

print(f"\n📊 2025 PROVIDED LEAD LIST BASELINE:")
print(f"   Total Leads: {total:,}")
print(f"   Total Wins: {df['total_wins'][0]:,}")
print(f"   Baseline Conversion: {baseline:.2%}")

print(f"\n📈 SIGNAL COVERAGE:")
print(f"   In Danger Zone: {df['pct_in_dz'][0]:.1%}")
print(f"   At Bleeding Firm (any): {df['pct_bleeding_any'][0]:.1%}")
print(f"   At Bleeding Firm (<-5): {df['pct_bleeding_mod'][0]:.1%}")
print(f"   At Bleeding Firm (<-10): {df['pct_bleeding_severe'][0]:.1%}")
print(f"   Is Veteran (10yr+): {df['pct_veteran'][0]:.1%}")

print("\n" + "=" * 70)
print("TIERED APPROACH RESULTS")
print("=" * 70)

def calc_and_print(name, count_col, wins_col, emoji=""):
    count = df[count_col][0]
    wins = df[wins_col][0]
    if count > 0:
        conv = wins / count
        lift = conv / baseline
        lift_icon = "🔥" if lift >= 2.5 else ("✅" if lift >= 1.8 else ("⚠️" if lift >= 1.3 else "❌"))
        print(f"\n{emoji} {name}:")
        print(f"   Volume: {count:,} leads ({count/total*100:.1f}% of pool)")
        print(f"   Wins: {wins}")
        print(f"   Conversion: {conv:.2%}")
        print(f"   Lift: {lift:.2f}x {lift_icon}")
        return lift
    else:
        print(f"\n{emoji} {name}: No leads match criteria")
        return 0

print("\n" + "-" * 70)
print("THE PROPOSED TIERS")
print("-" * 70)

t1_lift = calc_and_print("TIER 1 PLATINUM: DZ + Bleeding(<-10) + Veteran", "t1_count", "t1_wins", "💎")
t1b_lift = calc_and_print("TIER 1B PLATINUM-LITE: DZ + Bleeding(<-5) + Veteran", "t1b_count", "t1b_wins", "🥇")
t2b_lift = calc_and_print("TIER 2 GOLD: DZ + Bleeding(<-5)", "t2b_count", "t2b_wins", "🥈")
t2_lift = calc_and_print("TIER 2B GOLD-LITE: DZ + Bleeding(any)", "t2_count", "t2_wins", "🥉")
t3_lift = calc_and_print("TIER 3 SILVER: DZ + Veteran", "t3_count", "t3_wins", "⚪")
t4_lift = calc_and_print("TIER 4 BRONZE: Just Danger Zone", "t4_count", "t4_wins", "🟤")

print("\n" + "-" * 70)
print("ALTERNATIVE APPROACHES (Skip Danger Zone?)")
print("-" * 70)

bleed_lift = calc_and_print("ALT A: Bleeding Firm Only (<-10)", "bleed_only_count", "bleed_only_wins", "🩸")
bleed_vet_lift = calc_and_print("ALT B: Bleeding(<-5) + Veteran (no DZ)", "bleed_vet_count", "bleed_vet_wins", "🎯")

print("\n" + "=" * 70)
print("VERDICT")
print("=" * 70)

best_lift = max(t1_lift, t1b_lift, t2_lift, t2b_lift, t3_lift, bleed_lift, bleed_vet_lift)

if best_lift >= 2.0:
    print(f"\n✅ SUCCESS! Found a tier with {best_lift:.2f}x lift")
    print("   The tiered approach works. Deploy the winning tier(s).")
elif best_lift >= 1.5:
    print(f"\n⚠️ PARTIAL SUCCESS. Best lift is {best_lift:.2f}x")
    print("   Better than plain DZ, but not the 2.0x+ we hoped for.")
    print("   Still worth deploying - 50%+ improvement is real value.")
else:
    print(f"\n❌ SIGNAL WEAK. Best lift is only {best_lift:.2f}x")
    print("   The FINTRX pool may be too depleted for effective targeting.")

print("\n" + "-" * 70)
print("RECOMMENDED STRATEGY")
print("-" * 70)

# Find best combo
results = [
    ("DZ + Bleeding(<-10) + Veteran", t1_lift, df['t1_count'][0]),
    ("DZ + Bleeding(<-5) + Veteran", t1b_lift, df['t1b_count'][0]),
    ("DZ + Bleeding(<-5)", t2b_lift, df['t2b_count'][0]),
    ("DZ + Bleeding(any)", t2_lift, df['t2_count'][0]),
    ("DZ + Veteran", t3_lift, df['t3_count'][0]),
    ("Bleeding(<-5) + Veteran (no DZ)", bleed_vet_lift, df['bleed_vet_count'][0]),
]

# Sort by lift
results.sort(key=lambda x: x[1], reverse=True)

print("\nPRIORITY ORDER (by lift):")
for i, (name, lift, vol) in enumerate(results, 1):
    if vol > 0:
        icon = "🔥" if lift >= 2.0 else ("✅" if lift >= 1.5 else "⚠️")
        print(f"   {i}. {name}: {lift:.2f}x lift, {vol:,} leads {icon}")

print("\n💡 TIP: Work tiers in order. Start with highest lift until exhausted,")
print("   then move to next tier. Don't mix - call Platinum leads first!")
