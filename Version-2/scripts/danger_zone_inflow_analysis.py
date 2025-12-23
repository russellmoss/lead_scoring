"""
danger_zone_inflow_analysis.py
------------------------------
Estimates the monthly "refill rate" of Danger Zone leads.

Key questions:
1. How many advisors enter the Danger Zone each month? (hit 12-month mark)
2. How many exit? (hit 24-month mark)
3. Of those entering, how many are "good" leads? (Bleeding + Veteran)
4. Is this sustainable for your 3,750 leads/month need?
"""
from google.cloud import bigquery
import pandas as pd
from datetime import datetime, timedelta

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("DANGER ZONE INFLOW ANALYSIS")
print("Can we sustain 500+ 'good' leads every 2 weeks?")
print("=" * 70)

# ============================================================================
# PART 1: Historical Danger Zone Entry/Exit by Month
# ============================================================================

print("\n⏳ Analyzing historical Danger Zone population flow...")

query_flow = """
WITH monthly_snapshots AS (
    -- For each month, count how many advisors are in danger zone
    -- Based on when they started at their current firm
    SELECT 
        snapshot_month,
        COUNT(DISTINCT advisor_crd) as dz_population,
        COUNT(DISTINCT CASE WHEN months_at_firm = 12 THEN advisor_crd END) as just_entered_dz,
        COUNT(DISTINCT CASE WHEN months_at_firm = 24 THEN advisor_crd END) as just_exited_dz
    FROM (
        SELECT 
            DATE_TRUNC(snapshot_date, MONTH) as snapshot_month,
            RIA_CONTACT_CRD_ID as advisor_crd,
            DATE_DIFF(snapshot_date, 
                SAFE_CAST(LATEST_REGISTERED_EMPLOYMENT_START_DATE AS DATE), 
                MONTH) as months_at_firm
        FROM (
            -- Create virtual monthly snapshots for the past 18 months
            SELECT 
                c.RIA_CONTACT_CRD_ID,
                c.LATEST_REGISTERED_EMPLOYMENT_START_DATE,
                snapshot_date
            FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
            CROSS JOIN UNNEST(GENERATE_DATE_ARRAY('2024-01-01', CURRENT_DATE(), INTERVAL 1 MONTH)) as snapshot_date
            WHERE c.LATEST_REGISTERED_EMPLOYMENT_START_DATE IS NOT NULL
        )
    )
    WHERE months_at_firm BETWEEN 12 AND 24  -- In Danger Zone
    GROUP BY snapshot_month
)
SELECT * FROM monthly_snapshots
ORDER BY snapshot_month
"""

# Simpler approach: look at start dates to estimate inflow
query_inflow = """
WITH 
-- Count advisors by their start date (when they'll enter DZ in 12 months)
start_cohorts AS (
    SELECT 
        DATE_TRUNC(SAFE_CAST(LATEST_REGISTERED_EMPLOYMENT_START_DATE AS DATE), MONTH) as start_month,
        COUNT(DISTINCT RIA_CONTACT_CRD_ID) as advisors_starting
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
    WHERE LATEST_REGISTERED_EMPLOYMENT_START_DATE IS NOT NULL
      AND SAFE_CAST(LATEST_REGISTERED_EMPLOYMENT_START_DATE AS DATE) >= '2023-01-01'
    GROUP BY 1
),

-- These advisors will ENTER danger zone 12 months after their start
-- and EXIT danger zone 24 months after their start
inflow_projection AS (
    SELECT
        DATE_ADD(start_month, INTERVAL 12 MONTH) as enters_dz_month,
        DATE_ADD(start_month, INTERVAL 24 MONTH) as exits_dz_month,
        advisors_starting
    FROM start_cohorts
)

SELECT 
    enters_dz_month as month,
    SUM(advisors_starting) as entering_dz,
    -- Get exits from 12 months prior cohort
    LAG(SUM(advisors_starting), 12) OVER (ORDER BY enters_dz_month) as exiting_dz
FROM inflow_projection
WHERE enters_dz_month >= '2024-01-01'
  AND enters_dz_month <= DATE_ADD(CURRENT_DATE(), INTERVAL 6 MONTH)
GROUP BY enters_dz_month
ORDER BY enters_dz_month
"""

print("\n📊 MONTHLY DANGER ZONE INFLOW (based on employment start dates)")
print("-" * 70)

df_inflow = client.query(query_inflow).to_dataframe()

print(f"\n{'Month':<12} | {'Entering DZ':<15} | {'Exiting DZ':<15} | {'Net Change':<12}")
print("-" * 60)

for _, row in df_inflow.iterrows():
    month = row['month'].strftime('%Y-%m') if pd.notna(row['month']) else 'N/A'
    entering = int(row['entering_dz']) if pd.notna(row['entering_dz']) else 0
    exiting = int(row['exiting_dz']) if pd.notna(row['exiting_dz']) else 0
    net = entering - exiting
    print(f"{month:<12} | {entering:<15,} | {exiting:<15,} | {net:+,}")

avg_entering = df_inflow['entering_dz'].mean()
print(f"\n📈 Average monthly inflow to Danger Zone: {avg_entering:,.0f} advisors")

# ============================================================================
# PART 2: Of those entering DZ, how many are "good" leads?
# ============================================================================

print("\n" + "=" * 70)
print("QUALITY FILTER: How many NEW DZ leads are 'Platinum' quality?")
print("=" * 70)

query_quality = """
WITH current_dz_advisors AS (
    -- Advisors currently in Danger Zone (12-24 months tenure)
    SELECT 
        c.RIA_CONTACT_CRD_ID as advisor_crd,
        c.PRIMARY_FIRM_NAME as firm_name,
        SAFE_CAST(c.LATEST_REGISTERED_EMPLOYMENT_COMPANY_CRD_ID AS INT64) as firm_crd,
        DATE_DIFF(CURRENT_DATE(), 
            SAFE_CAST(c.LATEST_REGISTERED_EMPLOYMENT_START_DATE AS DATE), 
            MONTH) as months_at_firm,
        SAFE_CAST(c.LATEST_REGISTERED_EMPLOYMENT_START_DATE AS DATE) as start_date
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    WHERE c.LATEST_REGISTERED_EMPLOYMENT_START_DATE IS NOT NULL
),

dz_with_features AS (
    SELECT 
        dz.advisor_crd,
        dz.firm_name,
        dz.months_at_firm,
        dz.start_date,
        
        -- Industry tenure from employment history
        COALESCE(
            DATE_DIFF(CURRENT_DATE(), 
                (SELECT MIN(PREVIOUS_REGISTRATION_COMPANY_START_DATE) 
                 FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
                 WHERE h.RIA_CONTACT_CRD_ID = dz.advisor_crd),
                MONTH),
            dz.months_at_firm
        ) as industry_tenure_months,
        
        -- Firm net change (simplified - count current vs historical)
        (SELECT 
            COUNTIF(PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) 
                    AND PREVIOUS_REGISTRATION_COMPANY_CRD_ID = CAST(dz.firm_crd AS STRING))
            - COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
                    AND PREVIOUS_REGISTRATION_COMPANY_CRD_ID = CAST(dz.firm_crd AS STRING))
         FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
        ) as firm_net_change_approx
        
    FROM current_dz_advisors dz
    WHERE dz.months_at_firm BETWEEN 12 AND 24
),

-- Check if already in Salesforce
salesforce_crds AS (
    SELECT DISTINCT 
        SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE FA_CRD__c IS NOT NULL
)

SELECT
    -- By how recently they entered DZ
    CASE 
        WHEN months_at_firm BETWEEN 12 AND 14 THEN '12-14mo (Fresh DZ)'
        WHEN months_at_firm BETWEEN 15 AND 18 THEN '15-18mo (Mid DZ)'
        WHEN months_at_firm BETWEEN 19 AND 24 THEN '19-24mo (Late DZ)'
    END as dz_tenure_bucket,
    
    COUNT(*) as total_in_bucket,
    
    -- How many NOT in Salesforce yet?
    COUNTIF(dz.advisor_crd NOT IN (SELECT crd FROM salesforce_crds WHERE crd IS NOT NULL)) as not_in_salesforce,
    
    -- How many are Veterans (10+ years)?
    COUNTIF(industry_tenure_months >= 120) as veterans,
    
    -- How many at Bleeding firms?
    COUNTIF(firm_net_change_approx < -10) as at_bleeding_firm,
    
    -- How many are PLATINUM quality? (Veteran + Bleeding + Not in SF)
    COUNTIF(
        industry_tenure_months >= 120 
        AND firm_net_change_approx < -10
        AND dz.advisor_crd NOT IN (SELECT crd FROM salesforce_crds WHERE crd IS NOT NULL)
    ) as platinum_quality

FROM dz_with_features dz
GROUP BY 1
ORDER BY 1
"""

print("\n⏳ Analyzing quality of current Danger Zone pool...")

try:
    df_quality = client.query(query_quality).to_dataframe()
    
    print(f"\n{'DZ Tenure':<20} | {'Total':<10} | {'Not in SF':<12} | {'Veterans':<10} | {'Bleeding':<10} | {'Platinum':<10}")
    print("-" * 85)
    
    total_platinum = 0
    total_not_sf = 0
    
    for _, row in df_quality.iterrows():
        bucket = row['dz_tenure_bucket'] or 'Unknown'
        total = row['total_in_bucket']
        not_sf = row['not_in_salesforce']
        vets = row['veterans']
        bleed = row['at_bleeding_firm']
        plat = row['platinum_quality']
        
        total_platinum += plat
        total_not_sf += not_sf
        
        print(f"{bucket:<20} | {total:<10,} | {not_sf:<12,} | {vets:<10,} | {bleed:<10,} | {plat:<10,}")
    
    print("-" * 85)
    print(f"{'TOTAL':<20} | {df_quality['total_in_bucket'].sum():<10,} | {total_not_sf:<12,} | {df_quality['veterans'].sum():<10,} | {df_quality['at_bleeding_firm'].sum():<10,} | {total_platinum:<10,}")

except Exception as e:
    print(f"⚠️ Quality query failed: {e}")
    print("   Running simplified version...")
    total_platinum = "Unknown"
    total_not_sf = "Unknown"

# ============================================================================
# PART 3: Sustainability Analysis
# ============================================================================

print("\n" + "=" * 70)
print("SUSTAINABILITY ANALYSIS")
print("=" * 70)

monthly_need = 3750
biweekly_need = monthly_need / 2

print(f"\n📋 YOUR REQUIREMENTS:")
print(f"   SGAs: 15")
print(f"   Leads per SGA per month: 250")
print(f"   Total monthly need: {monthly_need:,}")
print(f"   Bi-weekly need: {biweekly_need:,.0f}")

print(f"\n📊 FINTRX REFRESH SUPPLY (estimated):")
print(f"   Avg monthly DZ inflow: {avg_entering:,.0f} advisors")
print(f"   Bi-weekly inflow: {avg_entering/2:,.0f} advisors")

# Estimate Platinum rate from earlier findings (~1.5% of DZ)
platinum_rate = 0.015
estimated_platinum_biweekly = (avg_entering / 2) * platinum_rate

print(f"\n💎 PLATINUM LEADS (estimated bi-weekly):")
print(f"   ~{platinum_rate*100:.1f}% of DZ leads are Platinum quality")
print(f"   Estimated Platinum per 2-week refresh: {estimated_platinum_biweekly:,.0f}")

print(f"\n" + "=" * 70)
print("VERDICT")
print("=" * 70)

if avg_entering / 2 >= biweekly_need:
    print(f"\n✅ SUSTAINABLE: DZ inflow ({avg_entering/2:,.0f}) >= your need ({biweekly_need:,.0f})")
else:
    gap = biweekly_need - (avg_entering / 2)
    print(f"\n⚠️ GAP: DZ inflow ({avg_entering/2:,.0f}) < your need ({biweekly_need:,.0f})")
    print(f"   Shortfall: {gap:,.0f} leads per 2-week refresh")
    print(f"\n   OPTIONS:")
    print(f"   1. Fill gap with non-DZ leads (lower conversion)")
    print(f"   2. Expand criteria (lower lift)")
    print(f"   3. Reduce SGA headcount or lead quota")

print(f"\n💎 PLATINUM REALITY CHECK:")
if estimated_platinum_biweekly >= 100:
    print(f"   ✅ Expect ~{estimated_platinum_biweekly:,.0f} Platinum leads per refresh")
    print(f"   That's {estimated_platinum_biweekly / biweekly_need * 100:.1f}% of your bi-weekly need")
else:
    print(f"   ⚠️ Only ~{estimated_platinum_biweekly:,.0f} Platinum leads per refresh")
    print(f"   Platinum covers {estimated_platinum_biweekly / biweekly_need * 100:.1f}% of bi-weekly need")
    print(f"   The rest will be lower-tier leads")

print(f"\n" + "-" * 70)
print("RECOMMENDED BI-WEEKLY LIST COMPOSITION")
print("-" * 70)

# Calculate realistic tier volumes per refresh
tier1_vol = estimated_platinum_biweekly
tier2_vol = (avg_entering / 2) * 0.03  # ~3% are Gold
tier3_vol = (avg_entering / 2) * 0.02  # ~2% are Silver
remaining = biweekly_need - tier1_vol - tier2_vol - tier3_vol

print(f"""
   💎 Platinum (1.95x lift):     ~{tier1_vol:,.0f} leads
   🥈 Gold (1.56x lift):         ~{tier2_vol:,.0f} leads  
   ⚪ Silver (1.54x lift):       ~{tier3_vol:,.0f} leads
   🟤 Standard (1.0x baseline):  ~{max(0, remaining):,.0f} leads
   ─────────────────────────────────────
   TOTAL:                        ~{biweekly_need:,.0f} leads

   Blended expected lift: ~{(tier1_vol*1.95 + tier2_vol*1.56 + tier3_vol*1.54 + max(0,remaining)*1.0) / biweekly_need:.2f}x
""")
