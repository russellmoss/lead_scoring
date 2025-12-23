# add_firm_rep_count.py
# Adds firm_rep_count_at_contact to the feature table and re-validates tiers

import sys
import warnings
warnings.filterwarnings("ignore")

print("=" * 70)
print("ADDING firm_rep_count_at_contact TO FEATURE TABLE")
print("=" * 70)

from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

# Step 1: Create firm rep counts table
print("\n[1/4] Creating firm_rep_counts_pit table...")
print("      (Counting active reps per firm per date)")

query1 = """
CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.firm_rep_counts_pit` AS

WITH lead_dates AS (
    SELECT DISTINCT
        firm_crd_at_contact as firm_crd,
        contacted_date
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
    WHERE firm_crd_at_contact IS NOT NULL
),

rep_counts AS (
    SELECT
        ld.firm_crd,
        ld.contacted_date,
        COUNT(DISTINCT eh.RIA_CONTACT_CRD_ID) as rep_count
    FROM lead_dates ld
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON SAFE_CAST(eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) = ld.firm_crd
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= ld.contacted_date
        AND (
            eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL
            OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE > ld.contacted_date
        )
    GROUP BY ld.firm_crd, ld.contacted_date
)

SELECT * FROM rep_counts
"""

try:
    job = client.query(query1)
    job.result()  # Wait for completion
    print("      Done - firm_rep_counts_pit created")
except Exception as e:
    print("      ERROR: " + str(e))
    sys.exit(1)


# Step 2: Add column to main feature table
print("\n[2/4] Adding firm_rep_count_at_contact to feature table...")

query2 = """
CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2` AS

SELECT
    f.*,
    COALESCE(rc.rep_count, 0) as firm_rep_count_at_contact
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
LEFT JOIN `savvy-gtm-analytics.ml_features.firm_rep_counts_pit` rc
    ON f.firm_crd_at_contact = rc.firm_crd
    AND f.contacted_date = rc.contacted_date
"""

try:
    job = client.query(query2)
    job.result()
    print("      Done - lead_scoring_features_pit_v2 created")
except Exception as e:
    print("      ERROR: " + str(e))
    sys.exit(1)


# Step 3: Verify the new column
print("\n[3/4] Verifying firm_rep_count distribution...")

query3 = """
SELECT
    COUNT(*) as total_leads,
    COUNTIF(firm_rep_count_at_contact > 0) as has_rep_count,
    COUNTIF(firm_rep_count_at_contact <= 10) as small_firm_count,
    COUNTIF(firm_rep_count_at_contact BETWEEN 11 AND 50) as medium_firm_count,
    COUNTIF(firm_rep_count_at_contact > 50) as large_firm_count,
    ROUND(AVG(firm_rep_count_at_contact), 1) as avg_rep_count,
    APPROX_QUANTILES(firm_rep_count_at_contact, 4)[OFFSET(2)] as median_rep_count
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2`
"""

try:
    stats = client.query(query3).to_dataframe()
    print("")
    print("      Distribution:")
    for col in stats.columns:
        val = stats[col].iloc[0]
        if pd.isna(val):
            print("        {}: NULL".format(col))
        elif isinstance(val, float):
            print("        {}: {:.1f}".format(col, val))
        else:
            print("        {}: {:,}".format(col, int(val)))
except Exception as e:
    print("      ERROR: " + str(e))


# Step 4: Re-run tier validation with small firm rule included
print("\n[4/4] Re-validating tiers WITH small firm rule...")

query4 = """
WITH lead_data AS (
    SELECT
        lead_id,
        contacted_date,
        current_firm_tenure_months / 12.0 as tenure_years,
        industry_tenure_months / 12.0 as experience_years,
        firm_net_change_12mo,
        firm_rep_count_at_contact,
        pit_moves_3yr,
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
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2` f
    INNER JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
        ON f.lead_id = l.Id
    WHERE f.contacted_date >= '2024-02-01'
      AND f.contacted_date <= '2025-09-01'
),

scored AS (
    SELECT
        *,
        CASE 
            -- NEW Tier 1: Prime Movers at Small Firms
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = 0
                 AND firm_rep_count_at_contact <= 10
            THEN 1
            
            -- NEW Tier 1b: Prime Movers (any firm size) - fallback
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = 0
            THEN 2
            
            -- NEW Tier 2: Heavy Bleeders at Small Firms
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
                 AND firm_rep_count_at_contact <= 20
            THEN 3
            
            -- NEW Tier 2b: Heavy Bleeders (any firm size)
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 4
            
            -- NEW Tier 3: Experienced Movers
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 5
            
            -- OLD Platinum (for comparison)
            WHEN tenure_years BETWEEN 4 AND 10
                 AND experience_years BETWEEN 8 AND 30
                 AND is_wirehouse = 0
                 AND firm_rep_count_at_contact <= 10
            THEN 10
            
            ELSE 99
        END as tier
    FROM lead_data
)

SELECT
    CASE tier
        WHEN 1 THEN 'T1: Prime Movers (Small Firm)'
        WHEN 2 THEN 'T1b: Prime Movers (Any Firm)'
        WHEN 3 THEN 'T2: Heavy Bleeders (Small)'
        WHEN 4 THEN 'T2b: Heavy Bleeders (Any)'
        WHEN 5 THEN 'T3: Experienced Movers'
        WHEN 10 THEN 'OLD: Platinum (4-10yr)'
        ELSE 'Standard'
    END as tier_name,
    tier,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM scored), 2) as lift
FROM scored
GROUP BY 1, 2
ORDER BY lift DESC
"""

try:
    results = client.query(query4).to_dataframe()
    
    print("")
    print("=" * 70)
    print("TIER COMPARISON WITH SMALL FIRM RULE")
    print("=" * 70)
    print("")
    print("{:<35} {:>8} {:>10} {:>10} {:>8}".format(
        "Tier", "Leads", "Converted", "Conv %", "Lift"
    ))
    print("-" * 70)
    
    for _, row in results.iterrows():
        print("{:<35} {:>8,} {:>10,} {:>9.2f}% {:>7.2f}x".format(
            row['tier_name'],
            int(row['n_leads']),
            int(row['n_converted']),
            row['conversion_rate_pct'],
            row['lift']
        ))
    
    print("-" * 70)
    
except Exception as e:
    print("ERROR: " + str(e))
    import traceback
    traceback.print_exc()


# Final summary
print("")
print("=" * 70)
print("SMALL FIRM ANALYSIS")
print("=" * 70)

query5 = """
SELECT
    CASE 
        WHEN firm_rep_count_at_contact <= 10 THEN 'Small (<=10)'
        WHEN firm_rep_count_at_contact <= 50 THEN 'Medium (11-50)'
        WHEN firm_rep_count_at_contact <= 200 THEN 'Large (51-200)'
        ELSE 'Very Large (>200)'
    END as firm_size,
    COUNT(*) as n_leads,
    SUM(COALESCE(target, 0)) as n_converted,
    ROUND(AVG(COALESCE(target, 0)) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(COALESCE(target, 0)) / 0.0369, 2) as lift
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2`
WHERE contacted_date >= '2024-02-01'
GROUP BY 1
ORDER BY lift DESC
"""

try:
    firm_analysis = client.query(query5).to_dataframe()
    print("")
    print("{:<25} {:>10} {:>10} {:>10} {:>8}".format(
        "Firm Size", "Leads", "Converted", "Conv %", "Lift"
    ))
    print("-" * 65)
    
    for _, row in firm_analysis.iterrows():
        print("{:<25} {:>10,} {:>10,} {:>9.2f}% {:>7.2f}x".format(
            row['firm_size'],
            int(row['n_leads']),
            int(row['n_converted']),
            row['conversion_rate_pct'],
            row['lift']
        ))
        
except Exception as e:
    print("ERROR: " + str(e))

print("")
print("=" * 70)
print("DONE - New table: ml_features.lead_scoring_features_pit_v2")
print("=" * 70)
