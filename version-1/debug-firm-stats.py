"""
debug_firm_stats.py
-------------------
Deep dive into the 'Bleeding Firm' numbers to check for double-counting.
"""

from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("🕵️  Investigating the 'Impossible' Bleeding Numbers...")

debug_sql = """
WITH 
-- 1. Get the Raw Counts per Firm
firm_stats AS (
    SELECT 
        SAFE_CAST(PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) as firm_crd,
        
        -- A. Total Rows (Just to see volume)
        COUNT(*) as total_history_rows,
        
        -- B. Arrivals (Starts in last 12mo)
        COUNT(DISTINCT CASE WHEN PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) 
              THEN RIA_CONTACT_CRD_ID END) as arrivals_12mo,
              
        -- C. Departures (Ends in last 12mo)
        COUNT(DISTINCT CASE WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) 
              THEN RIA_CONTACT_CRD_ID END) as departures_12mo,
              
        -- D. Current Active Reps (No End Date)
        COUNT(DISTINCT CASE WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
              THEN RIA_CONTACT_CRD_ID END) as current_reps

    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_CRD_ID IS NOT NULL
    GROUP BY 1
),

-- 2. Get Firm Names (Using the CORRECT Column: PRIMARY_FIRM_NAME)
firm_names AS (
    SELECT DISTINCT 
        SAFE_CAST(RIA_INVESTOR_CRD_ID AS INT64) as firm_crd,
        PRIMARY_FIRM_NAME as firm_name
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current`
    WHERE RIA_INVESTOR_CRD_ID IS NOT NULL
)

-- 3. Combine and Filter for the "Bleeders"
SELECT 
    fs.firm_crd,
    -- Get name (handle duplicates by taking MAX)
    (SELECT MAX(firm_name) FROM firm_names fn WHERE fn.firm_crd = fs.firm_crd) as firm_name,
    fs.current_reps,
    fs.arrivals_12mo,
    fs.departures_12mo,
    (fs.arrivals_12mo - fs.departures_12mo) as net_change,
    
    -- The "Sanity Ratio": Net Change / Current Reps
    CASE WHEN fs.current_reps > 0 
         THEN ROUND((fs.arrivals_12mo - fs.departures_12mo) / fs.current_reps, 2) 
         ELSE 0 
    END as churn_ratio_pct

FROM firm_stats fs
ORDER BY net_change ASC -- Show the biggest bleeders first
LIMIT 10
"""

print("⏳ Running deep diagnostic...")
try:
    df = client.query(debug_sql).to_dataframe()
    print("\n🚨 TOP 10 BLEEDING FIRMS REPORT 🚨")
    print(df.to_string(index=False))
    
    print("\n--- DIAGNOSIS GUIDE ---")
    print("1. REAL BLEED: Large firms (Wells Fargo, Merrill) with net change ~10% of Current Reps.")
    print("2. BUG: Small firms with huge net change (e.g. 50 reps, -2000 change).")
    
except Exception as e:
    print(f"❌ Error: {e}")