"""
Phase 1.1 REMEDIATION: Fix Gap Victims & Enforce Date Floor
------------------------------------------------------------
This script drops the old feature table and rebuilds it using:
1. "Gap Tolerant" Logic (Recovers ~9,700 leads)
2. Feb 1, 2024 Date Floor (Ensures Firm History exists)
"""

from google.cloud import bigquery
import time

# Configuration
PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"
ANALYSIS_DATE = "2024-12-31"
MATURITY_DAYS = 30

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

# THE CORRECTED SQL (Gap Tolerant + Date Floor)
REMEDIATION_SQL = f"""
CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` AS

WITH 
-- 1. LEAD BASE (With Date Floor)
lead_base AS (
    SELECT
        l.Id as lead_id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd,
        DATE(l.stage_entered_contacting__c) as contacted_date,
        
        -- PIT month for firm lookups
        DATE_TRUNC(DATE_SUB(DATE(l.stage_entered_contacting__c), INTERVAL 1 MONTH), MONTH) as pit_month,
        
        -- Target variable
        CASE
            WHEN DATE_DIFF(DATE('{ANALYSIS_DATE}'), DATE(l.stage_entered_contacting__c), DAY) < {MATURITY_DAYS}
            THEN NULL  -- Right-censored
            WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL
                 AND DATE_DIFF(DATE(l.Stage_Entered_Call_Scheduled__c), 
                               DATE(l.stage_entered_contacting__c), DAY) <= {MATURITY_DAYS}
            THEN 1  -- Positive
            ELSE 0  -- Negative
        END as target,
        l.Company as company_name,
        l.LeadSource as lead_source
        
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.FA_CRD__c IS NOT NULL
        AND l.Company NOT LIKE '%Savvy%'
        -- CRITICAL DATE FLOOR: Firm_historicals starts Jan 2024
        AND l.stage_entered_contacting__c >= '2024-02-01'
),

-- 2. REP STATE (Gap Tolerant)
rep_state_pit AS (
    SELECT
        lb.lead_id,
        lb.advisor_crd,
        lb.contacted_date,
        
        -- Most recent employment record starting ON or BEFORE contact date
        eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd_at_contact,
        eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE as current_job_start_date,
        COALESCE(eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE, DATE('{ANALYSIS_DATE}')) as current_job_end_date,
        
        -- Gap metrics
        CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL 
                 AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE < lb.contacted_date
            THEN DATE_DIFF(lb.contacted_date, eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE, DAY)
            ELSE 0 
        END as days_in_gap,
        
        -- Tenure
        DATE_DIFF(lb.contacted_date, eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE, MONTH) as current_firm_tenure_months,
        
        -- Industry Tenure
        (SELECT COALESCE(SUM(DATE_DIFF(COALESCE(eh2.PREVIOUS_REGISTRATION_COMPANY_END_DATE, DATE('{ANALYSIS_DATE}')), eh2.PREVIOUS_REGISTRATION_COMPANY_START_DATE, MONTH)), 0)
         FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh2
         WHERE eh2.RIA_CONTACT_CRD_ID = lb.advisor_crd
           AND eh2.PREVIOUS_REGISTRATION_COMPANY_START_DATE < eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE
        ) as industry_tenure_months,
        
        -- Prior Firms
        (SELECT COUNT(DISTINCT eh3.PREVIOUS_REGISTRATION_COMPANY_CRD_ID)
         FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh3
         WHERE eh3.RIA_CONTACT_CRD_ID = lb.advisor_crd
           AND eh3.PREVIOUS_REGISTRATION_COMPANY_START_DATE < eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE
        ) as num_prior_firms
        
    FROM lead_base lb
    INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON lb.advisor_crd = eh.RIA_CONTACT_CRD_ID
    WHERE 
        -- GAP FIX: Only check start date
        eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= lb.contacted_date
    
    -- GAP FIX: Take the most recent one
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY lb.lead_id 
        ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
    ) = 1
),

-- 3. FIRM REP COUNT (Calculate from employment history - PIT-safe)
firm_rep_count_pit AS (
    SELECT
        rsp.firm_crd_at_contact,
        rsp.contacted_date,
        COUNT(DISTINCT eh.RIA_CONTACT_CRD_ID) as firm_rep_count_at_contact
    FROM rep_state_pit rsp
    INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON rsp.firm_crd_at_contact = eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID
    WHERE eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= rsp.contacted_date
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= rsp.contacted_date)
    GROUP BY rsp.firm_crd_at_contact, rsp.contacted_date
),

-- 4. FIRM STATE (Virtual Snapshot)
firm_state_pit AS (
    SELECT
        rsp.lead_id,
        rsp.firm_crd_at_contact,
        rsp.contacted_date,
        lb.pit_month,
        
        fh.TOTAL_AUM as firm_aum_pit,
        -- Rep count calculated from employment history (PIT-safe)
        COALESCE(frc.firm_rep_count_at_contact, 0) as firm_rep_count_at_contact,
        
        -- Growth from JAN 2024 Baseline (Since we have limited history)
        CASE 
            WHEN fh_jan24.TOTAL_AUM > 0
            THEN (fh.TOTAL_AUM - fh_jan24.TOTAL_AUM) * 100.0 / fh_jan24.TOTAL_AUM
            ELSE NULL
        END as aum_growth_since_jan2024_pct
        
    FROM rep_state_pit rsp
    INNER JOIN lead_base lb ON rsp.lead_id = lb.lead_id
    
    -- Join to Firm_historicals for pit_month
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals` fh
        ON rsp.firm_crd_at_contact = fh.RIA_INVESTOR_CRD_ID
        AND EXTRACT(YEAR FROM lb.pit_month) = fh.YEAR
        AND EXTRACT(MONTH FROM lb.pit_month) = fh.MONTH
        
    -- Join to Firm_historicals for Jan 2024 Baseline
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals` fh_jan24
        ON rsp.firm_crd_at_contact = fh_jan24.RIA_INVESTOR_CRD_ID
        AND fh_jan24.YEAR = 2024
        AND fh_jan24.MONTH = 1
        
    -- Join to rep count CTE
    LEFT JOIN firm_rep_count_pit frc
        ON rsp.firm_crd_at_contact = frc.firm_crd_at_contact
        AND rsp.contacted_date = frc.contacted_date
),

-- 5. MOBILITY & STABILITY (Derived)
mobility_derived AS (
    SELECT
        lb.lead_id,
        
        -- Moves in last 3 years
        (SELECT COUNT(*) 
         FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h 
         WHERE h.RIA_CONTACT_CRD_ID = lb.advisor_crd 
           AND h.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
           AND h.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(lb.contacted_date, INTERVAL 3 YEAR)
           AND h.PREVIOUS_REGISTRATION_COMPANY_END_DATE < lb.contacted_date
        ) as pit_moves_3yr,
        
        -- Firm Net Change (12mo) - Arrivals minus Departures
        (SELECT COUNT(DISTINCT h.RIA_CONTACT_CRD_ID)
         FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
         WHERE h.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = rsp.firm_crd_at_contact
           AND h.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= rsp.contacted_date
           AND h.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE_SUB(rsp.contacted_date, INTERVAL 12 MONTH)
        ) - 
        (SELECT COUNT(DISTINCT h.RIA_CONTACT_CRD_ID)
         FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` h
         WHERE h.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = rsp.firm_crd_at_contact
           AND h.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
           AND h.PREVIOUS_REGISTRATION_COMPANY_END_DATE <= rsp.contacted_date
           AND h.PREVIOUS_REGISTRATION_COMPANY_END_DATE > DATE_SUB(rsp.contacted_date, INTERVAL 12 MONTH)
        ) as firm_net_change_12mo
        
    FROM lead_base lb
    INNER JOIN rep_state_pit rsp ON lb.lead_id = rsp.lead_id
)

-- FINAL SELECT
SELECT
    lb.lead_id,
    lb.advisor_crd,
    lb.contacted_date,
    lb.target,
    rsp.firm_crd_at_contact,
    rsp.days_in_gap,
    rsp.industry_tenure_months,
    rsp.current_firm_tenure_months,
    rsp.num_prior_firms,
    
    fsp.firm_aum_pit,
    fsp.firm_rep_count_at_contact,
    fsp.aum_growth_since_jan2024_pct,
    
    md.pit_moves_3yr,
    md.firm_net_change_12mo,
    
    -- Derived Scores
    CASE
        WHEN md.pit_moves_3yr >= 3 THEN 'Highly Mobile'
        WHEN md.pit_moves_3yr = 2 THEN 'Mobile'
        WHEN md.pit_moves_3yr = 1 THEN 'Average'
        ELSE 'Stable'
    END as pit_mobility_tier,
    
    ROUND(GREATEST(0, LEAST(100, 50 + COALESCE(md.firm_net_change_12mo, 0) * 3.5)), 1) as firm_stability_score

FROM lead_base lb
JOIN rep_state_pit rsp ON lb.lead_id = rsp.lead_id
LEFT JOIN firm_state_pit fsp ON lb.lead_id = fsp.lead_id
LEFT JOIN mobility_derived md ON lb.lead_id = md.lead_id
WHERE lb.target IS NOT NULL
"""

def execute_remediation():
    print(f"Starting Phase 1.1 Remediation...")
    print(f"Target Table: {PROJECT_ID}.ml_features.lead_scoring_features_pit")
    print(f"Configuration: Date Floor >= 2024-02-01, Gap Tolerant Logic")
    
    try:
        job = client.query(REMEDIATION_SQL)
        print("Query running...")
        job.result()
        print("✅ Remediation Query Complete!")
        
        # Verify Results
        check_query = """
        SELECT 
            COUNT(*) as total_rows,
            COUNTIF(days_in_gap > 0) as recovered_gap_leads,
            ROUND(COUNTIF(firm_aum_pit IS NOT NULL) * 100.0 / COUNT(*), 2) as firm_data_coverage
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
        """
        rows = client.query(check_query).result()
        for row in rows:
            print(f"\n--- NEW TABLE STATS ---")
            print(f"Total Training Rows: {row.total_rows:,}")
            print(f"Recovered Gap Leads: {row.recovered_gap_leads:,}")
            print(f"Firm Data Coverage:  {row.firm_data_coverage}%")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    execute_remediation()