"""
quality_filter_test.py
----------------------
Can we restore 2.0x lift by filtering for 'Veteran Movers' only?
"""
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("🕵️  Testing 'Quality Filters' on 2025 Data...")

query = """
WITH data_2025 AS (
    -- Get only 2025 'Provided Lead List' leads
    SELECT 
        l.Id,
        l.IsConverted,
        f.current_firm_tenure_months,
        f.industry_tenure_months,
        f.num_prior_firms,
        
        -- Danger Zone Definition (1-2 years tenure)
        CASE WHEN f.current_firm_tenure_months BETWEEN 12 AND 24 THEN 1 ELSE 0 END as in_danger_zone
        
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features` f
    JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l ON f.lead_id = l.Id
    WHERE EXTRACT(YEAR FROM l.CreatedDate) = 2025
      AND l.LeadSource = 'Provided Lead List'
)

SELECT
    COUNT(*) as total_leads,
    AVG(CAST(IsConverted AS INT64)) as baseline_conv,
    
    -- Scenario 1: Danger Zone ONLY (Current State)
    COUNTIF(in_danger_zone = 1) as dz_count,
    COUNTIF(in_danger_zone = 1 AND IsConverted = TRUE) as dz_wins,
    
    -- Scenario 2: Danger Zone + VETERAN (10+ Years Experience)
    COUNTIF(in_danger_zone = 1 AND industry_tenure_months >= 120) as veteran_dz_count,
    COUNTIF(in_danger_zone = 1 AND industry_tenure_months >= 120 AND IsConverted = TRUE) as veteran_dz_wins,

    -- Scenario 3: Danger Zone + MOVER (2+ Prior Firms)
    COUNTIF(in_danger_zone = 1 AND num_prior_firms >= 2) as mover_dz_count,
    COUNTIF(in_danger_zone = 1 AND num_prior_firms >= 2 AND IsConverted = TRUE) as mover_dz_wins,

    -- Scenario 4: THE GOLD STANDARD (DZ + Veteran + Mover)
    COUNTIF(in_danger_zone = 1 AND industry_tenure_months >= 120 AND num_prior_firms >= 2) as gold_count,
    COUNTIF(in_danger_zone = 1 AND industry_tenure_months >= 120 AND num_prior_firms >= 2 AND IsConverted = TRUE) as gold_wins

FROM data_2025
"""

df = client.query(query).to_dataframe()

# Calculate Lifts
baseline = df['baseline_conv'][0]

print(f"\n📉 BASELINE (2025 Provided Lists): {baseline:.2%}")

print(f"\n1️⃣  Standard Danger Zone (No Filters):")
conv1 = df['dz_wins'][0] / df['dz_count'][0]
print(f"    - Conversion: {conv1:.2%}")
print(f"    - Lift: {conv1/baseline:.2f}x")
print(f"    - Volume: {df['dz_count'][0]} leads")

print(f"\n2️⃣  'Veteran' Danger Zone (10+ Yrs Exp):")
conv2 = df['veteran_dz_wins'][0] / df['veteran_dz_count'][0]
print(f"    - Conversion: {conv2:.2%}")
print(f"    - Lift: {conv2/baseline:.2f}x")
print(f"    - Volume: {df['veteran_dz_count'][0]} leads")

print(f"\n3️⃣  'Mover' Danger Zone (2+ Prior Firms):")
conv3 = df['mover_dz_wins'][0] / df['mover_dz_count'][0]
print(f"    - Conversion: {conv3:.2%}")
print(f"    - Lift: {conv3/baseline:.2f}x")
print(f"    - Volume: {df['mover_dz_count'][0]} leads")

print(f"\n🏆 'GOLD STANDARD' (DZ + Veteran + Mover):")
conv4 = df['gold_wins'][0] / df['gold_count'][0]
print(f"    - Conversion: {conv4:.2%}")
print(f"    - Lift: {conv4/baseline:.2f}x")
print(f"    - Volume: {df['gold_count'][0]} leads")