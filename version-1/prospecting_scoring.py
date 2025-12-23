"""
prospecting_scoring.py
----------------------
DEBUG VERSION: Exports AUM and Tenure to verify data quality.
Finds active advisors in FINTRX who are NOT in Salesforce, scores them,
and exports a "High Priority" call list with debug information.
"""

from google.cloud import bigquery
from inference_pipeline_v2 import LeadScorerV2
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# 1. Initialize
client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')
scorer = LeadScorerV2()

print("🚀 Starting Prospecting Job (Debug Mode)...")

# 2. SQL: Optimized - Uses Direct Columns (No Joins needed for basic info)
prospecting_sql = """
WITH 
-- A. Identify Advisors NOT in Salesforce
salesforce_crds AS (
    SELECT DISTINCT 
        SAFE_CAST(REGEXP_REPLACE(CAST(FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as crd
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
    WHERE FA_CRD__c IS NOT NULL
),

-- B. Find Active Candidates (Using Direct Columns)
active_candidates AS (
    SELECT 
        c.RIA_CONTACT_CRD_ID as advisor_crd,
        c.CONTACT_FIRST_NAME as first_name,
        c.CONTACT_LAST_NAME as last_name,
        c.PRIMARY_FIRM_NAME as company_name,
        
        -- FIX: Use the column ALREADY in the table (Safe & Easy)
        SAFE_CAST(c.LATEST_REGISTERED_EMPLOYMENT_COMPANY_CRD_ID AS INT64) as firm_crd,
        
        -- FIX: Use the start date ALREADY in the table
        SAFE_CAST(c.LATEST_REGISTERED_EMPLOYMENT_START_DATE AS DATE) as current_start_date
        
    FROM `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
    LEFT JOIN salesforce_crds s ON c.RIA_CONTACT_CRD_ID = s.crd
    WHERE s.crd IS NULL 
      AND c.CONTACT_FIRST_NAME IS NOT NULL
      AND c.LATEST_REGISTERED_EMPLOYMENT_COMPANY_CRD_ID IS NOT NULL
),

-- C. Pre-Aggregate Advisor History
advisor_stats AS (
    SELECT 
        RIA_CONTACT_CRD_ID,
        MAX(CASE WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
            THEN PREVIOUS_REGISTRATION_COMPANY_START_DATE END) as current_start_date,
        COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 YEAR)) as moves_3yr,
        COUNT(DISTINCT CASE WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL 
              THEN PREVIOUS_REGISTRATION_COMPANY_CRD_ID END) as prior_firms_count,
        MIN(PREVIOUS_REGISTRATION_COMPANY_START_DATE) as first_start_date
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    GROUP BY RIA_CONTACT_CRD_ID
),

-- D. Pre-Aggregate Firm Metrics
target_firms AS (
    SELECT DISTINCT firm_crd FROM active_candidates
),
firm_stats AS (
    SELECT 
        SAFE_CAST(PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) as firm_crd,
        -- Arrivals (12mo)
        COUNT(DISTINCT CASE WHEN PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) 
              THEN RIA_CONTACT_CRD_ID END) as arrivals_12mo,
        -- Departures (12mo)
        COUNT(DISTINCT CASE WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH) 
              THEN RIA_CONTACT_CRD_ID END) as departures_12mo,
        -- Current Rep Count
        COUNT(DISTINCT CASE WHEN PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
              THEN RIA_CONTACT_CRD_ID END) as current_reps
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE SAFE_CAST(PREVIOUS_REGISTRATION_COMPANY_CRD_ID AS INT64) IN (SELECT firm_crd FROM target_firms)
    GROUP BY 1
),

-- E. Pre-Aggregate AUM
firm_aum AS (
    SELECT
        SAFE_CAST(RIA_INVESTOR_CRD_ID AS INT64) as firm_crd,
        -- Latest AUM
        ARRAY_AGG(TOTAL_AUM ORDER BY YEAR DESC, MONTH DESC LIMIT 1)[OFFSET(0)] as current_aum,
        -- Jan 2024 AUM
        MAX(CASE WHEN YEAR = 2024 AND MONTH = 1 THEN TOTAL_AUM END) as jan24_aum
    FROM `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals`
    WHERE SAFE_CAST(RIA_INVESTOR_CRD_ID AS INT64) IN (SELECT firm_crd FROM target_firms)
    GROUP BY 1
)

-- Final Selection
SELECT 
    ac.advisor_crd,
    ac.first_name,
    ac.last_name,
    ac.company_name,
    ac.firm_crd,
    CURRENT_DATE() as contacted_date,
    
    DATE_DIFF(CURRENT_DATE(), COALESCE(ads.current_start_date, DATE('2020-01-01')), MONTH) as current_firm_tenure_months,
    
    -- Feature 2: Moves 3yr
    COALESCE(ads.moves_3yr, 0) as pit_moves_3yr,
    
    -- Feature 3: Prior Firms
    COALESCE(ads.prior_firms_count, 0) as num_prior_firms,
    
    -- Feature 4: Industry Tenure
    DATE_DIFF(CURRENT_DATE(), COALESCE(ads.first_start_date, DATE('2015-01-01')), MONTH) as industry_tenure_months,
    
    -- Feature 5: Net Change
    COALESCE(fs.arrivals_12mo, 0) - COALESCE(fs.departures_12mo, 0) as firm_net_change_12mo,
    
    -- Feature 6: Rep Count
    COALESCE(fs.current_reps, 1) as firm_rep_count_at_contact,
    
    -- Feature 7: AUM
    COALESCE(fa.current_aum, 0) as firm_aum_pit,
    
    -- Feature 8: AUM Growth
    CASE 
        WHEN fa.jan24_aum > 0 THEN (fa.current_aum - fa.jan24_aum) * 100.0 / fa.jan24_aum
        ELSE 0 
    END as aum_growth_since_jan2024_pct,
    
    -- Feature 9-11: Mobility Tiers
    CASE WHEN COALESCE(ads.moves_3yr, 0) >= 3 THEN 1 ELSE 0 END as pit_mobility_tier_Highly_Mobile,
    CASE WHEN COALESCE(ads.moves_3yr, 0) = 2 THEN 1 ELSE 0 END as pit_mobility_tier_Mobile,
    CASE WHEN COALESCE(ads.moves_3yr, 0) < 2 THEN 1 ELSE 0 END as pit_mobility_tier_Stable

FROM active_candidates ac
LEFT JOIN advisor_stats ads ON ac.advisor_crd = ads.RIA_CONTACT_CRD_ID
LEFT JOIN firm_stats fs ON ac.firm_crd = fs.firm_crd
LEFT JOIN firm_aum fa ON ac.firm_crd = fa.firm_crd
WHERE ac.firm_crd IS NOT NULL 
LIMIT 5000
"""

print("⏳ Fetching candidates from BigQuery...")
# Use the BigQuery client to run the optimized query
try:
    df = client.query(prospecting_sql).result().to_dataframe()
    print(f"✅ Fetched {len(df)} candidates.")

    if not df.empty:
        print("🧠 Scoring candidates...")
        results = []
        
        for idx, row in df.iterrows():
            try:
                features = {
                    'aum_growth_since_jan2024_pct': float(row.get('aum_growth_since_jan2024_pct', 0)),
                    'current_firm_tenure_months': float(row.get('current_firm_tenure_months', 0)),
                    'firm_aum_pit': float(row.get('firm_aum_pit', 0)),
                    'firm_net_change_12mo': float(row.get('firm_net_change_12mo', 0)),
                    'firm_rep_count_at_contact': float(row.get('firm_rep_count_at_contact', 0)),
                    'industry_tenure_months': float(row.get('industry_tenure_months', 0)),
                    'num_prior_firms': float(row.get('num_prior_firms', 0)),
                    'pit_mobility_tier_Highly Mobile': float(row.get('pit_mobility_tier_Highly_Mobile', 0)),
                    'pit_mobility_tier_Mobile': float(row.get('pit_mobility_tier_Mobile', 0)),
                    'pit_mobility_tier_Stable': float(row.get('pit_mobility_tier_Stable', 0)),
                    'pit_moves_3yr': float(row.get('pit_moves_3yr', 0))
                }
                
                result = scorer.score_lead(features)
                
                results.append({
                    'advisor_crd': row['advisor_crd'],
                    'first_name': row.get('first_name', ''),
                    'last_name': row.get('last_name', ''),
                    'company_name': row.get('company_name', ''),
                    'firm_crd': row.get('firm_crd', ''),
                    'lead_score': result['lead_score'],
                    'score_bucket': result['score_bucket'],
                    # DEBUG COLUMNS:
                    'firm_aum_pit': features['firm_aum_pit'],
                    'firm_net_change_12mo': features['firm_net_change_12mo'],
                    'current_tenure': features['current_firm_tenure_months'],
                    'flight_risk_score': result['engineered_features']['flight_risk_score'],
                })
            except Exception as e:
                continue

        scored_df = pd.DataFrame(results)
        
        if not scored_df.empty:
            print(f"✅ Scored {len(scored_df)} candidates successfully")
            
            # Export
            output_dir = Path("reports/prospecting")
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"prospects_DEBUG_{timestamp}.csv"
            
            # Sort by Score
            ranked = scored_df.sort_values('lead_score', ascending=False)
            
            ranked.to_csv(output_file, index=False)
            print(f"📄 Saved list to: {output_file}")
            
            # Show Top 5
            print("\nTop 5 Prospects (Debug View):")
            print(ranked[['first_name', 'last_name', 'lead_score', 'firm_aum_pit', 'firm_net_change_12mo', 'flight_risk_score']].head(5).to_string(index=False))
            
            # Stats check
            print("\nData Quality Check:")
            print(f"Leads with >0 AUM: {len(ranked[ranked['firm_aum_pit'] > 0])} / {len(ranked)}")
            print(f"Leads with >0 Flight Risk: {len(ranked[ranked['flight_risk_score'] > 0])} / {len(ranked)}")
        else:
            print("❌ No leads scored.")
    else:
        print("⚠️ No candidates found.")

except Exception as e:
    print(f"❌ Query Failed: {e}")