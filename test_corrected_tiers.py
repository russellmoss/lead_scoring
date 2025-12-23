# test_corrected_tiers.py
# Test the NEW tier definitions based on actual data patterns

import sys
import warnings
warnings.filterwarnings("ignore")

print("=" * 70)
print("CORRECTED TIER VALIDATION")
print("=" * 70)

from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

# Test query with CORRECTED tiers
query = """
WITH lead_data AS (
    SELECT
        lead_id,
        contacted_date,
        current_firm_tenure_months / 12.0 as tenure_years,
        industry_tenure_months / 12.0 as experience_years,
        firm_net_change_12mo,
        pit_moves_3yr,
        num_prior_firms,
        COALESCE(target, 0) as converted,
        
        -- Wirehouse detection (using company name from Lead table)
        CASE 
            WHEN UPPER(l.Company) LIKE '%MERRILL%' THEN 1
            WHEN UPPER(l.Company) LIKE '%MORGAN STANLEY%' THEN 1
            WHEN UPPER(l.Company) LIKE '%UBS%' THEN 1
            WHEN UPPER(l.Company) LIKE '%WELLS FARGO%' THEN 1
            WHEN UPPER(l.Company) LIKE '%EDWARD JONES%' THEN 1
            WHEN UPPER(l.Company) LIKE '%RAYMOND JAMES%' THEN 1
            WHEN UPPER(l.Company) LIKE '%AMERIPRISE%' THEN 1
            WHEN UPPER(l.Company) LIKE '%LPL%' THEN 1
            WHEN UPPER(l.Company) LIKE '%NORTHWESTERN%' THEN 1
            ELSE 0
        END as is_wirehouse
        
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
    INNER JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
        ON f.lead_id = l.Id
    WHERE f.contacted_date >= '2024-02-01'
      AND f.contacted_date <= '2025-09-01'
),

tiered_leads AS (
    SELECT
        *,
        
        -- NEW TIER 1: Prime Movers (1-4yr tenure, 5-15yr exp, unstable firm, not wirehouse)
        CASE WHEN 
            tenure_years BETWEEN 1 AND 4
            AND experience_years BETWEEN 5 AND 15
            AND firm_net_change_12mo != 0
            AND is_wirehouse = 0
        THEN 1 ELSE 0 END as new_tier1_prime_movers,
        
        -- NEW TIER 2: Heavy Bleeders (<-10 net change, 5+ yr exp)
        CASE WHEN 
            firm_net_change_12mo < -10
            AND experience_years >= 5
        THEN 1 ELSE 0 END as new_tier2_heavy_bleeders,
        
        -- NEW TIER 3: Experienced Short-Tenure (1-4yr tenure, 20+ yr exp)
        CASE WHEN 
            tenure_years BETWEEN 1 AND 4
            AND experience_years >= 20
        THEN 1 ELSE 0 END as new_tier3_experienced_movers,
        
        -- OLD TIER 1: Platinum (4-10yr tenure, 8-30yr exp, not wirehouse)
        -- Note: Cannot include small firm rule - column missing
        CASE WHEN 
            tenure_years BETWEEN 4 AND 10
            AND experience_years BETWEEN 8 AND 30
            AND is_wirehouse = 0
        THEN 1 ELSE 0 END as old_tier1_platinum,
        
        -- OLD TIER 2: Danger Zone (1-2yr tenure, <-5 net change, 10+ exp)
        CASE WHEN 
            tenure_years BETWEEN 1 AND 2
            AND firm_net_change_12mo < -5
            AND experience_years >= 10
        THEN 1 ELSE 0 END as old_tier2_danger_zone
        
    FROM lead_data
)

SELECT
    'Baseline (all leads)' as tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    1.00 as lift
FROM tiered_leads

UNION ALL

SELECT
    'NEW Tier 1: Prime Movers' as tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM tiered_leads), 2) as lift
FROM tiered_leads
WHERE new_tier1_prime_movers = 1

UNION ALL

SELECT
    'NEW Tier 2: Heavy Bleeders' as tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM tiered_leads), 2) as lift
FROM tiered_leads
WHERE new_tier2_heavy_bleeders = 1

UNION ALL

SELECT
    'NEW Tier 3: Exp Movers' as tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM tiered_leads), 2) as lift
FROM tiered_leads
WHERE new_tier3_experienced_movers = 1

UNION ALL

SELECT
    'OLD Tier 1: Platinum' as tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM tiered_leads), 2) as lift
FROM tiered_leads
WHERE old_tier1_platinum = 1

UNION ALL

SELECT
    'OLD Tier 2: Danger Zone' as tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM tiered_leads), 2) as lift
FROM tiered_leads
WHERE old_tier2_danger_zone = 1

ORDER BY lift DESC
"""

print("\nRunning tier comparison...")
print("")

try:
    results = client.query(query).to_dataframe()
    
    print("=" * 70)
    print("TIER COMPARISON: NEW vs OLD")
    print("=" * 70)
    print("")
    print("{:<30} {:>10} {:>12} {:>12} {:>8}".format(
        "Tier", "Leads", "Converted", "Conv Rate", "Lift"
    ))
    print("-" * 70)
    
    for _, row in results.iterrows():
        print("{:<30} {:>10,} {:>12,} {:>11.2f}% {:>7.2f}x".format(
            row['tier'],
            int(row['n_leads']),
            int(row['n_converted']),
            row['conversion_rate_pct'],
            row['lift']
        ))
    
    print("-" * 70)
    
    # Summary
    new_tiers = results[results['tier'].str.startswith('NEW')]
    old_tiers = results[results['tier'].str.startswith('OLD')]
    
    if len(new_tiers) > 0 and len(old_tiers) > 0:
        best_new = new_tiers.loc[new_tiers['lift'].idxmax()]
        best_old = old_tiers.loc[old_tiers['lift'].idxmax()]
        
        print("")
        print("SUMMARY:")
        print("  Best NEW tier: {} ({:.2f}x lift, {:,} leads)".format(
            best_new['tier'], best_new['lift'], int(best_new['n_leads'])
        ))
        print("  Best OLD tier: {} ({:.2f}x lift, {:,} leads)".format(
            best_old['tier'], best_old['lift'], int(best_old['n_leads'])
        ))
        
        improvement = best_new['lift'] - best_old['lift']
        print("")
        if improvement > 0:
            print("  [OK] NEW tiers improve lift by {:.2f}x".format(improvement))
        else:
            print("  [NOTE] OLD tiers still better by {:.2f}x".format(-improvement))

except Exception as e:
    print("[ERROR] " + str(e))
    import traceback
    traceback.print_exc()

# Also test combined tiers
print("")
print("=" * 70)
print("COMBINED NEW TIERS (Any of Tier 1, 2, or 3)")
print("=" * 70)

query2 = """
WITH lead_data AS (
    SELECT
        lead_id,
        current_firm_tenure_months / 12.0 as tenure_years,
        industry_tenure_months / 12.0 as experience_years,
        firm_net_change_12mo,
        COALESCE(target, 0) as converted,
        CASE 
            WHEN UPPER(l.Company) LIKE '%MERRILL%' THEN 1
            WHEN UPPER(l.Company) LIKE '%MORGAN STANLEY%' THEN 1
            WHEN UPPER(l.Company) LIKE '%UBS%' THEN 1
            WHEN UPPER(l.Company) LIKE '%WELLS FARGO%' THEN 1
            WHEN UPPER(l.Company) LIKE '%EDWARD JONES%' THEN 1
            WHEN UPPER(l.Company) LIKE '%RAYMOND JAMES%' THEN 1
            WHEN UPPER(l.Company) LIKE '%AMERIPRISE%' THEN 1
            WHEN UPPER(l.Company) LIKE '%LPL%' THEN 1
            WHEN UPPER(l.Company) LIKE '%NORTHWESTERN%' THEN 1
            ELSE 0
        END as is_wirehouse
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
    INNER JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
        ON f.lead_id = l.Id
    WHERE f.contacted_date >= '2024-02-01'
      AND f.contacted_date <= '2025-09-01'
),

scored AS (
    SELECT
        *,
        CASE 
            -- Tier 1: Prime Movers
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = 0
            THEN 1
            -- Tier 2: Heavy Bleeders
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 2
            -- Tier 3: Experienced Movers
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 3
            -- Standard
            ELSE 5
        END as new_tier
    FROM lead_data
)

SELECT
    CASE 
        WHEN new_tier = 1 THEN 'Tier 1: Prime Movers'
        WHEN new_tier = 2 THEN 'Tier 2: Heavy Bleeders'
        WHEN new_tier = 3 THEN 'Tier 3: Exp Movers'
        ELSE 'Standard'
    END as tier_name,
    new_tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM scored), 2) as lift
FROM scored
GROUP BY 1, 2
ORDER BY new_tier
"""

try:
    results2 = client.query(query2).to_dataframe()
    print("")
    print("{:<25} {:>10} {:>12} {:>12} {:>8}".format(
        "Tier", "Leads", "Converted", "Conv Rate", "Lift"
    ))
    print("-" * 70)
    
    total_priority = 0
    priority_converted = 0
    
    for _, row in results2.iterrows():
        print("{:<25} {:>10,} {:>12,} {:>11.2f}% {:>7.2f}x".format(
            row['tier_name'],
            int(row['n_leads']),
            int(row['n_converted']),
            row['conversion_rate_pct'],
            row['lift']
        ))
        if row['new_tier'] <= 3:
            total_priority += row['n_leads']
            priority_converted += row['n_converted']
    
    print("-" * 70)
    
    baseline = results2['n_converted'].sum() / results2['n_leads'].sum()
    priority_rate = priority_converted / total_priority if total_priority > 0 else 0
    
    print("")
    print("PRIORITY LEADS (Tiers 1-3 combined):")
    print("  Total: {:,} leads".format(int(total_priority)))
    print("  Converted: {:,}".format(int(priority_converted)))
    print("  Rate: {:.2f}%".format(priority_rate * 100))
    print("  Lift: {:.2f}x".format(priority_rate / baseline if baseline > 0 else 0))

except Exception as e:
    print("[ERROR] " + str(e))

print("")
print("=" * 70)
print("DONE")
print("=" * 70)
