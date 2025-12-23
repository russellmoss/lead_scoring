# diagnose_v3_features.py
# Check what's actually in the V3 feature table

import sys
import warnings
warnings.filterwarnings("ignore")

print("=" * 70)
print("V3 FEATURE TABLE DIAGNOSTIC")
print("=" * 70)

from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

# 1. Get column names
print("\n[1] Checking table schema...")
query1 = """
SELECT column_name, data_type
FROM `savvy-gtm-analytics.ml_features.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'lead_scoring_features_pit'
ORDER BY ordinal_position
"""
try:
    cols = client.query(query1).to_dataframe()
    print("\nAvailable columns:")
    for _, row in cols.iterrows():
        print("  - {} ({})".format(row['column_name'], row['data_type']))
except Exception as e:
    print("Error: " + str(e))

# 2. Check feature distributions
print("\n" + "=" * 70)
print("[2] Checking feature distributions...")
query2 = """
SELECT
    COUNT(*) as total_leads,
    
    -- Tenure distributions
    AVG(current_firm_tenure_months) as avg_tenure_months,
    AVG(current_firm_tenure_months / 12.0) as avg_tenure_years,
    COUNTIF(current_firm_tenure_months / 12.0 BETWEEN 4 AND 10) as sweet_tenure_count,
    
    -- Experience distributions  
    AVG(industry_tenure_months) as avg_experience_months,
    AVG(industry_tenure_months / 12.0) as avg_experience_years,
    COUNTIF(industry_tenure_months / 12.0 BETWEEN 8 AND 30) as experienced_count,
    
    -- Firm metrics
    AVG(firm_net_change_12mo) as avg_net_change,
    COUNTIF(firm_net_change_12mo < -5) as bleeding_firm_count,
    
    -- Check if firm_rep_count exists
    AVG(CASE WHEN firm_rep_count_at_contact IS NOT NULL THEN firm_rep_count_at_contact ELSE NULL END) as avg_rep_count,
    COUNTIF(firm_rep_count_at_contact IS NOT NULL) as has_rep_count,
    COUNTIF(firm_rep_count_at_contact <= 10) as small_firm_count,
    
    -- Danger zone tenure
    COUNTIF(current_firm_tenure_months / 12.0 BETWEEN 1 AND 2) as danger_zone_tenure_count,
    
    -- Target
    AVG(CAST(target AS INT64)) as conversion_rate

FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
WHERE contacted_date >= '2024-02-01'
"""

try:
    stats = client.query(query2).to_dataframe()
    print("")
    for col in stats.columns:
        val = stats[col].iloc[0]
        if pd.isna(val):
            print("{}: NULL".format(col))
        elif isinstance(val, float):
            print("{}: {:.2f}".format(col, val))
        else:
            print("{}: {:,}".format(col, val))
except Exception as e:
    print("Error: " + str(e))

# 3. Check tier overlap
print("\n" + "=" * 70)
print("[3] Checking Platinum tier components separately...")
query3 = """
SELECT
    COUNT(*) as total_leads,
    
    -- Individual rule components (using actual thresholds from plan)
    COUNTIF(current_firm_tenure_months / 12.0 BETWEEN 4 AND 10) as rule_sweet_tenure,
    COUNTIF(industry_tenure_months / 12.0 BETWEEN 8 AND 30) as rule_experienced,
    COUNTIF(firm_rep_count_at_contact <= 10) as rule_small_firm,
    COUNTIF(firm_rep_count_at_contact IS NULL) as rule_small_firm_null,
    
    -- How many pass tenure + experience (without firm size)?
    COUNTIF(
        current_firm_tenure_months / 12.0 BETWEEN 4 AND 10
        AND industry_tenure_months / 12.0 BETWEEN 8 AND 30
    ) as tenure_and_experience,
    
    -- Full Platinum (if firm_rep_count worked)
    COUNTIF(
        current_firm_tenure_months / 12.0 BETWEEN 4 AND 10
        AND industry_tenure_months / 12.0 BETWEEN 8 AND 30
        AND firm_rep_count_at_contact <= 10
    ) as full_platinum

FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
WHERE contacted_date >= '2024-02-01'
"""

try:
    tiers = client.query(query3).to_dataframe()
    print("")
    for col in tiers.columns:
        val = tiers[col].iloc[0]
        if pd.isna(val):
            print("{}: NULL".format(col))
        else:
            print("{}: {:,}".format(col, int(val)))
except Exception as e:
    print("Error: " + str(e))

# 4. What ARE the top converting segments?
print("\n" + "=" * 70)
print("[4] Finding ACTUAL high-converting segments...")
query4 = """
WITH lead_data AS (
    SELECT
        current_firm_tenure_months / 12.0 as tenure_years,
        industry_tenure_months / 12.0 as experience_years,
        firm_net_change_12mo,
        pit_moves_3yr,
        firm_aum_pit,
        COALESCE(target, 0) as converted
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
    WHERE contacted_date >= '2024-02-01'
)

SELECT
    -- Tenure buckets
    CASE 
        WHEN tenure_years < 1 THEN '0-1yr'
        WHEN tenure_years < 2 THEN '1-2yr'
        WHEN tenure_years < 4 THEN '2-4yr'
        WHEN tenure_years < 7 THEN '4-7yr'
        WHEN tenure_years < 10 THEN '7-10yr'
        ELSE '10+yr'
    END as tenure_bucket,
    
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / 0.0369, 2) as lift_vs_baseline

FROM lead_data
GROUP BY 1
ORDER BY conversion_rate_pct DESC
"""

try:
    segments = client.query(query4).to_dataframe()
    print("")
    print(segments.to_string(index=False))
except Exception as e:
    print("Error: " + str(e))

# 5. Experience buckets
print("\n" + "=" * 70)
print("[5] Experience bucket analysis...")
query5 = """
WITH lead_data AS (
    SELECT
        industry_tenure_months / 12.0 as experience_years,
        COALESCE(target, 0) as converted
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
    WHERE contacted_date >= '2024-02-01'
)

SELECT
    CASE 
        WHEN experience_years < 5 THEN '0-5yr'
        WHEN experience_years < 10 THEN '5-10yr'
        WHEN experience_years < 15 THEN '10-15yr'
        WHEN experience_years < 20 THEN '15-20yr'
        WHEN experience_years < 30 THEN '20-30yr'
        ELSE '30+yr'
    END as experience_bucket,
    
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / 0.0369, 2) as lift_vs_baseline

FROM lead_data
GROUP BY 1
ORDER BY conversion_rate_pct DESC
"""

try:
    exp = client.query(query5).to_dataframe()
    print("")
    print(exp.to_string(index=False))
except Exception as e:
    print("Error: " + str(e))

# 6. Bleeding firm analysis
print("\n" + "=" * 70)
print("[6] Firm net change analysis...")
query6 = """
WITH lead_data AS (
    SELECT
        firm_net_change_12mo,
        COALESCE(target, 0) as converted
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
    WHERE contacted_date >= '2024-02-01'
)

SELECT
    CASE 
        WHEN firm_net_change_12mo < -10 THEN 'Heavy bleeding (<-10)'
        WHEN firm_net_change_12mo < -5 THEN 'Bleeding (-10 to -5)'
        WHEN firm_net_change_12mo < 0 THEN 'Slight loss (-5 to 0)'
        WHEN firm_net_change_12mo = 0 THEN 'Stable (0)'
        WHEN firm_net_change_12mo <= 5 THEN 'Growing (0 to 5)'
        ELSE 'Fast growing (>5)'
    END as net_change_bucket,
    
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / 0.0369, 2) as lift_vs_baseline

FROM lead_data
GROUP BY 1
ORDER BY conversion_rate_pct DESC
"""

try:
    nc = client.query(query6).to_dataframe()
    print("")
    print(nc.to_string(index=False))
except Exception as e:
    print("Error: " + str(e))

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
