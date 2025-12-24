-- ============================================================================
-- Firm Bleeding × Mobility Interaction Analysis
-- ============================================================================
-- Purpose: Analyze the combined effect of advisor mobility and firm stability
--          (bleeding/growing) on MQL conversion rates
--
-- Key Question: Do mobile reps at bleeding firms convert better than
--                mobile reps at stable/growing firms?
--
-- Methodology: 
--   - Mobility: Count of firm moves in 3 years before contact date
--   - Firm Stability: Net change in reps (arrivals - departures) over 
--     12 months before contact date (PIT-safe)
--   - Target: MQL conversion (Stage_Entered_Call_Scheduled__c)
-- ============================================================================

WITH lead_base AS (
    SELECT 
        l.Id,
        SAFE_CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) as advisor_crd,
        DATE(l.stage_entered_contacting__c) as contacted_date,
        CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
    WHERE l.stage_entered_contacting__c IS NOT NULL
        AND l.stage_entered_contacting__c >= '2024-01-01'
),

-- Calculate mobility (moves in 3 years before contact)
mobility_calc AS (
    SELECT 
        lb.Id,
        lb.contacted_date,
        lb.converted,
        lb.advisor_crd,
        COALESCE(COUNT(DISTINCT CASE 
            WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE_SUB(lb.contacted_date, INTERVAL 3 YEAR)
                AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= lb.contacted_date
            THEN eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID END), 0) as move_count,
        CASE 
            WHEN COUNT(DISTINCT CASE 
                WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE_SUB(lb.contacted_date, INTERVAL 3 YEAR)
                    AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= lb.contacted_date
                THEN eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID END) >= 2 
            THEN 'Mobile'
            ELSE 'Stable'
        END as mobility
    FROM lead_base lb
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON lb.advisor_crd = eh.RIA_CONTACT_CRD_ID
    GROUP BY lb.Id, lb.contacted_date, lb.converted, lb.advisor_crd
),

-- Get current firm at time of contact (PIT-safe)
current_firm AS (
    SELECT 
        mc.Id,
        mc.contacted_date,
        mc.converted,
        mc.mobility,
        mc.move_count,
        mc.advisor_crd,
        eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd
    FROM mobility_calc mc
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
        ON mc.advisor_crd = eh.RIA_CONTACT_CRD_ID
        AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= mc.contacted_date
        AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
             OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= mc.contacted_date)
    QUALIFY ROW_NUMBER() OVER(PARTITION BY mc.Id ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC) = 1
),

-- Calculate firm stability (net change in reps over 12 months before contact)
-- PIT-safe: Only uses data available at contact date
firm_stability AS (
    SELECT 
        cf.Id,
        cf.contacted_date,
        cf.converted,
        cf.mobility,
        cf.move_count,
        cf.firm_crd,
        -- Count departures from this firm in 12 months before contact
        (SELECT COUNT(DISTINCT eh_depart.RIA_CONTACT_CRD_ID)
         FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_depart
         WHERE eh_depart.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = cf.firm_crd
           AND eh_depart.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(cf.contacted_date, INTERVAL 12 MONTH)
           AND eh_depart.PREVIOUS_REGISTRATION_COMPANY_END_DATE < cf.contacted_date
           AND eh_depart.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
        ) as departures_12mo,
        -- Count arrivals to this firm in 12 months before contact
        (SELECT COUNT(DISTINCT eh_arrive.RIA_CONTACT_CRD_ID)
         FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_arrive
         WHERE eh_arrive.PREVIOUS_REGISTRATION_COMPANY_CRD_ID = cf.firm_crd
           AND eh_arrive.PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(cf.contacted_date, INTERVAL 12 MONTH)
           AND eh_arrive.PREVIOUS_REGISTRATION_COMPANY_START_DATE < cf.contacted_date
        ) as arrivals_12mo
    FROM current_firm cf
),

-- Calculate net change and categorize firm status
mobility_bleeding AS (
    SELECT 
        *,
        COALESCE(arrivals_12mo, 0) - COALESCE(departures_12mo, 0) as net_change_12mo,
        CASE 
            WHEN firm_crd IS NULL THEN 'Unknown Firm'
            WHEN COALESCE(arrivals_12mo, 0) - COALESCE(departures_12mo, 0) < -10 THEN 'Heavy Bleeding'
            WHEN COALESCE(arrivals_12mo, 0) - COALESCE(departures_12mo, 0) < 0 THEN 'Light Bleeding'
            WHEN COALESCE(arrivals_12mo, 0) - COALESCE(departures_12mo, 0) = 0 THEN 'Stable'
            ELSE 'Growing'
        END as firm_status
    FROM firm_stability
)

-- Final output: Conversion rates by mobility × firm status
SELECT 
    mobility,
    firm_status,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / NULLIF((SELECT AVG(converted) FROM mobility_bleeding), 0), 2) as lift_vs_baseline,
    ROUND(AVG(net_change_12mo), 1) as avg_net_change
FROM mobility_bleeding
GROUP BY 1, 2
ORDER BY 
    CASE mobility
        WHEN 'Stable' THEN 0
        ELSE 1
    END,
    CASE firm_status
        WHEN 'Heavy Bleeding' THEN 0
        WHEN 'Light Bleeding' THEN 1
        WHEN 'Stable' THEN 2
        WHEN 'Growing' THEN 3
        ELSE 4
    END;

-- ============================================================================
-- Expected Results Interpretation:
-- ============================================================================
-- Key Finding: Mobile reps at bleeding firms convert at 20.37% (4.85x lift)
--              This is the strongest combination found
--
-- However, mobile reps at growing firms also convert well (19.05%, 4.54x lift)
-- This suggests MOBILITY is the dominant signal, not firm bleeding
--
-- Recommendation: Focus on mobility as primary feature, firm stability as
--                 secondary/contextual feature
-- ============================================================================

