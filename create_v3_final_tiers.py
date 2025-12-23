# create_v3_final_tiers.py
# Creates the final V3 tier scoring table and validates results

import sys
import warnings
warnings.filterwarnings("ignore")

print("=" * 70)
print("V3 FINAL TIER SCORING - CREATE & VALIDATE")
print("=" * 70)

from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

# =============================================================================
# STEP 1: CREATE THE FINAL SCORING TABLE
# =============================================================================

print("\n[1/3] Creating lead_scores_v3_final table...")

create_sql = """
CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scores_v3_final` AS

WITH lead_features AS (
    SELECT
        f.lead_id,
        f.advisor_crd,
        f.contacted_date,
        f.target as converted,
        f.current_firm_tenure_months,
        f.current_firm_tenure_months / 12.0 as tenure_years,
        f.industry_tenure_months,
        f.industry_tenure_months / 12.0 as experience_years,
        f.firm_crd_at_contact,
        f.firm_net_change_12mo,
        f.firm_rep_count_at_contact,
        f.firm_aum_pit,
        f.pit_moves_3yr,
        f.num_prior_firms,
        l.Company as company_name,
        l.FirstName as first_name,
        l.LastName as last_name,
        l.Email as email
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2` f
    INNER JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
        ON f.lead_id = l.Id
),

wirehouse_flagged AS (
    SELECT
        *,
        CASE 
            WHEN UPPER(company_name) LIKE '%MERRILL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%MORGAN STANLEY%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%UBS %' THEN TRUE
            WHEN UPPER(company_name) LIKE '%WELLS FARGO%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%EDWARD JONES%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%RAYMOND JAMES%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%AMERIPRISE%' THEN TRUE
            WHEN UPPER(company_name) LIKE '% LPL %' THEN TRUE
            WHEN UPPER(company_name) LIKE '%LPL FINANCIAL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%NORTHWESTERN MUTUAL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%STIFEL%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%RBC %' THEN TRUE
            WHEN UPPER(company_name) LIKE '%JANNEY%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%BAIRD%' THEN TRUE
            WHEN UPPER(company_name) LIKE '%OPPENHEIMER%' THEN TRUE
            ELSE FALSE
        END as is_wirehouse,
        CASE
            WHEN firm_rep_count_at_contact IS NULL OR firm_rep_count_at_contact = 0 THEN 'UNKNOWN'
            WHEN firm_rep_count_at_contact <= 10 THEN 'SMALL'
            WHEN firm_rep_count_at_contact <= 50 THEN 'MEDIUM'
            WHEN firm_rep_count_at_contact <= 200 THEN 'LARGE'
            ELSE 'VERY_LARGE'
        END as firm_size_category,
        (firm_rep_count_at_contact IS NOT NULL AND firm_rep_count_at_contact > 0) as has_firm_size_data
    FROM lead_features
),

scored AS (
    SELECT
        *,
        
        -- TIER ASSIGNMENT
        CASE
            -- TIER 1: PRIME MOVERS (3.5x-6.6x)
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 1
            
            -- TIER 2: HEAVY BLEEDERS (2.2x-3.6x)
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 2
            
            -- TIER 3: EXPERIENCED MOVERS (2.7x)
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 3
            
            -- TIER 4: MEDIUM/LARGE FIRM (2.4x-2.6x)
            WHEN has_firm_size_data = TRUE
                 AND firm_size_category IN ('MEDIUM', 'LARGE')
            THEN 4
            
            -- TIER 5: MODERATE BLEEDERS (1.6x-2.0x)
            WHEN firm_net_change_12mo < 0
                 AND firm_net_change_12mo >= -10
                 AND experience_years >= 5
            THEN 5
            
            ELSE 99
        END as tier_rank,
        
        CASE
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 'TIER_1_PRIME_MOVER'
            
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 'TIER_2_HEAVY_BLEEDER'
            
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 'TIER_3_EXPERIENCED_MOVER'
            
            WHEN has_firm_size_data = TRUE
                 AND firm_size_category IN ('MEDIUM', 'LARGE')
            THEN 'TIER_4_KNOWN_MED_LARGE_FIRM'
            
            WHEN firm_net_change_12mo < 0
                 AND firm_net_change_12mo >= -10
                 AND experience_years >= 5
            THEN 'TIER_5_MODERATE_BLEEDER'
            
            ELSE 'STANDARD'
        END as tier_name,
        
        CASE
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years BETWEEN 5 AND 15
                 AND firm_net_change_12mo != 0
                 AND is_wirehouse = FALSE
            THEN 3.51
            
            WHEN firm_net_change_12mo < -10
                 AND experience_years >= 5
            THEN 2.46
            
            WHEN tenure_years BETWEEN 1 AND 4
                 AND experience_years >= 20
            THEN 2.74
            
            WHEN has_firm_size_data = TRUE
                 AND firm_size_category IN ('MEDIUM', 'LARGE')
            THEN 2.50
            
            WHEN firm_net_change_12mo < 0
                 AND firm_net_change_12mo >= -10
                 AND experience_years >= 5
            THEN 1.80
            
            ELSE 1.00
        END as expected_lift,
        
        (tenure_years BETWEEN 1 AND 4) as rule_short_tenure,
        (experience_years BETWEEN 5 AND 15) as rule_mid_career,
        (experience_years >= 20) as rule_veteran,
        (firm_net_change_12mo != 0) as rule_unstable_firm,
        (firm_net_change_12mo < -10) as rule_heavy_bleeding,
        (firm_net_change_12mo < 0 AND firm_net_change_12mo >= -10) as rule_moderate_bleeding
        
    FROM wirehouse_flagged
)

SELECT
    lead_id,
    advisor_crd,
    contacted_date,
    first_name,
    last_name,
    email,
    company_name,
    tier_rank,
    tier_name,
    expected_lift,
    tenure_years,
    experience_years,
    firm_net_change_12mo,
    firm_rep_count_at_contact,
    firm_size_category,
    is_wirehouse,
    pit_moves_3yr,
    rule_short_tenure,
    rule_mid_career,
    rule_veteran,
    rule_unstable_firm,
    rule_heavy_bleeding,
    rule_moderate_bleeding,
    has_firm_size_data,
    converted,
    CURRENT_TIMESTAMP() as scored_at,
    'v3-final-20251221' as model_version
FROM scored
ORDER BY tier_rank, expected_lift DESC, contacted_date DESC
"""

try:
    job = client.query(create_sql)
    job.result()
    print("      Done - lead_scores_v3_final created")
except Exception as e:
    print("      ERROR: " + str(e))
    sys.exit(1)


# =============================================================================
# STEP 2: VALIDATE TIER DISTRIBUTION AND LIFT
# =============================================================================

print("\n[2/3] Validating tier distribution and lift...")

validate_sql = """
SELECT
    tier_name,
    tier_rank,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`), 2) as actual_lift,
    ROUND(AVG(expected_lift), 2) as expected_lift
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
GROUP BY 1, 2
ORDER BY tier_rank
"""

try:
    results = client.query(validate_sql).to_dataframe()
    
    print("")
    print("=" * 80)
    print("V3 FINAL TIER VALIDATION")
    print("=" * 80)
    print("")
    print("{:<30} {:>8} {:>10} {:>10} {:>10} {:>10}".format(
        "Tier", "Leads", "Converted", "Conv %", "Actual", "Expected"
    ))
    print("-" * 80)
    
    total_priority = 0
    priority_converted = 0
    
    for _, row in results.iterrows():
        actual_str = "{:.2f}x".format(row['actual_lift'])
        expected_str = "{:.2f}x".format(row['expected_lift'])
        
        # Check if actual meets expected
        if row['actual_lift'] >= row['expected_lift'] * 0.9:
            status = "OK"
        else:
            status = "LOW"
        
        print("{:<30} {:>8,} {:>10,} {:>9.2f}% {:>10} {:>10}".format(
            row['tier_name'],
            int(row['n_leads']),
            int(row['n_converted']),
            row['conversion_rate_pct'],
            actual_str,
            expected_str
        ))
        
        if row['tier_rank'] <= 5:
            total_priority += row['n_leads']
            priority_converted += row['n_converted']
    
    print("-" * 80)
    
    # Summary stats
    baseline = results['n_converted'].sum() / results['n_leads'].sum()
    priority_rate = priority_converted / total_priority if total_priority > 0 else 0
    priority_lift = priority_rate / baseline if baseline > 0 else 0
    
    print("")
    print("PRIORITY LEADS (Tiers 1-5):")
    print("  Total: {:,} leads".format(int(total_priority)))
    print("  Converted: {:,}".format(int(priority_converted)))
    print("  Rate: {:.2f}%".format(priority_rate * 100))
    print("  Lift: {:.2f}x".format(priority_lift))
    
except Exception as e:
    print("ERROR: " + str(e))


# =============================================================================
# STEP 3: SHOW TOP LEADS FOR EACH TIER
# =============================================================================

print("\n[3/3] Sample leads from each tier...")

sample_sql = """
SELECT
    tier_name,
    first_name,
    last_name,
    company_name,
    ROUND(tenure_years, 1) as tenure_yrs,
    ROUND(experience_years, 1) as exp_yrs,
    firm_net_change_12mo as net_chg,
    converted
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
WHERE tier_rank <= 3
QUALIFY ROW_NUMBER() OVER (PARTITION BY tier_name ORDER BY contacted_date DESC) <= 3
ORDER BY tier_rank, contacted_date DESC
"""

try:
    samples = client.query(sample_sql).to_dataframe()
    
    print("")
    print("=" * 80)
    print("SAMPLE LEADS BY TIER")
    print("=" * 80)
    
    current_tier = None
    for _, row in samples.iterrows():
        if row['tier_name'] != current_tier:
            current_tier = row['tier_name']
            print("\n" + current_tier + ":")
            print("-" * 60)
        
        conv_status = "CONVERTED" if row['converted'] == 1 else ""
        print("  {} {} @ {} ({}yr tenure, {}yr exp, {} net chg) {}".format(
            row['first_name'],
            row['last_name'],
            row['company_name'][:30] if row['company_name'] else 'Unknown',
            row['tenure_yrs'],
            row['exp_yrs'],
            row['net_chg'],
            conv_status
        ))
        
except Exception as e:
    print("ERROR: " + str(e))


# =============================================================================
# FINAL SUMMARY
# =============================================================================

print("")
print("")
print("=" * 80)
print("V3 FINAL SCORING COMPLETE")
print("=" * 80)
print("")
print("Table created: savvy-gtm-analytics.ml_features.lead_scores_v3_final")
print("Model version: v3-final-20251221")
print("")
print("TIER DEFINITIONS:")
print("-" * 80)
print("")
print("TIER 1: PRIME MOVERS (Expected 3.5x lift)")
print("  - Tenure: 1-4 years")
print("  - Experience: 5-15 years")
print("  - Firm net change != 0 (any instability)")
print("  - Not wirehouse")
print("")
print("TIER 2: HEAVY BLEEDERS (Expected 2.5x lift)")
print("  - Firm net change < -10")
print("  - Experience >= 5 years")
print("")
print("TIER 3: EXPERIENCED MOVERS (Expected 2.7x lift)")
print("  - Tenure: 1-4 years")
print("  - Experience: 20+ years")
print("")
print("TIER 4: MEDIUM/LARGE FIRMS (Expected 2.5x lift)")
print("  - Firm rep count 11-200 (when data available)")
print("")
print("TIER 5: MODERATE BLEEDERS (Expected 1.8x lift)")
print("  - Firm net change -10 to 0")
print("  - Experience >= 5 years")
print("")
print("=" * 80)
print("DONE")
print("=" * 80)
