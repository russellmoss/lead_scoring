-- ===================================================================
-- STEP 3.1: CLASS DISTRIBUTION ANALYSIS
-- Lead Scoring Model Development - Phase 0, Week 3
-- ===================================================================
-- 
-- This script analyzes the class distribution for our lead scoring model
-- to understand Contacted → MQL conversion rates and prepare for class 
-- imbalance handling.
--
-- Analysis Components:
-- 1. Overall conversion rates (Contacted leads that became MQLs)
-- 2. Conversion rates by AUM tiers (<$100M, $100-500M, >$500M)
-- 3. Conversion rates by metropolitan areas
-- 4. 30-day outcome window conversion rates
-- 5. Temporal patterns in conversion rates
--
-- ===================================================================

-- ===================================================================
-- 1. OVERALL CONVERSION RATES ANALYSIS
-- ===================================================================

-- Overall conversion rates for contacted leads
SELECT 
    'Overall Conversion Analysis' as analysis_type,
    'Contacted Leads (All Time)' as stage,
    COUNT(*) as total_contacted_leads,
    COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) as mql_conversions,
    ROUND(COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(*) * 100, 2) as conversion_rate_percent,
    ROUND(COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NULL THEN 1 END), 4) as positive_to_negative_ratio
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE Stage_Entered_Contacting__c IS NOT NULL

UNION ALL

-- 30-day window conversion rates
SELECT 
    'Overall Conversion Analysis' as analysis_type,
    'Contacted Leads (30-day window)' as stage,
    COUNT(*) as total_contacted_leads,
    COUNT(CASE 
        WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
        AND DATE(Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
        THEN 1 
    END) as mql_conversions,
    ROUND(COUNT(CASE 
        WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
        AND DATE(Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
        THEN 1 
    END) / COUNT(*) * 100, 2) as conversion_rate_percent,
    ROUND(COUNT(CASE 
        WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
        AND DATE(Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
        THEN 1 
    END) / COUNT(CASE 
        WHEN Stage_Entered_Call_Scheduled__c IS NULL 
        OR DATE(Stage_Entered_Call_Scheduled__c) > DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
        THEN 1 
    END), 4) as positive_to_negative_ratio
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE Stage_Entered_Contacting__c IS NOT NULL

UNION ALL

-- Leads with discovery data coverage
SELECT 
    'Overall Conversion Analysis' as analysis_type,
    'Leads with Discovery Data' as stage,
    COUNT(*) as total_contacted_leads,
    COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) as mql_conversions,
    ROUND(COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(*) * 100, 2) as conversion_rate_percent,
    ROUND(COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NULL THEN 1 END), 4) as positive_to_negative_ratio
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
INNER JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;

-- ===================================================================
-- 2. CONVERSION RATES BY AUM TIERS
-- ===================================================================

-- AUM tier analysis with discovery data
SELECT 
    'AUM Tier Analysis' as analysis_type,
    CASE 
        WHEN dd.AUM < 100000000 THEN '<$100M'
        WHEN dd.AUM BETWEEN 100000000 AND 500000000 THEN '$100M-$500M'
        WHEN dd.AUM > 500000000 THEN '>$500M'
        ELSE 'Unknown AUM'
    END as aum_tier,
    COUNT(*) as total_leads,
    COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) as mql_conversions,
    ROUND(COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(*) * 100, 2) as conversion_rate_percent,
    ROUND(AVG(dd.AUM), 0) as avg_aum,
    ROUND(PERCENTILE_CONT(dd.AUM, 0.5) OVER(), 0) as median_aum
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
INNER JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
GROUP BY 
    CASE 
        WHEN dd.AUM < 100000000 THEN '<$100M'
        WHEN dd.AUM BETWEEN 100000000 AND 500000000 THEN '$100M-$500M'
        WHEN dd.AUM > 500000000 THEN '>$500M'
        ELSE 'Unknown AUM'
    END
ORDER BY 
    CASE 
        WHEN CASE 
            WHEN dd.AUM < 100000000 THEN '<$100M'
            WHEN dd.AUM BETWEEN 100000000 AND 500000000 THEN '$100M-$500M'
            WHEN dd.AUM > 500000000 THEN '>$500M'
            ELSE 'Unknown AUM'
        END = '<$100M' THEN 1
        WHEN CASE 
            WHEN dd.AUM < 100000000 THEN '<$100M'
            WHEN dd.AUM BETWEEN 100000000 AND 500000000 THEN '$100M-$500M'
            WHEN dd.AUM > 500000000 THEN '>$500M'
            ELSE 'Unknown AUM'
        END = '$100M-$500M' THEN 2
        WHEN CASE 
            WHEN dd.AUM < 100000000 THEN '<$100M'
            WHEN dd.AUM BETWEEN 100000000 AND 500000000 THEN '$100M-$500M'
            WHEN dd.AUM > 500000000 THEN '>$500M'
            ELSE 'Unknown AUM'
        END = '>$500M' THEN 3
        ELSE 4
    END;

-- ===================================================================
-- 3. CONVERSION RATES BY METROPOLITAN AREAS
-- ===================================================================

-- Metropolitan area analysis
SELECT 
    'Metro Area Analysis' as analysis_type,
    CASE 
        WHEN dd.Metro_Area_NYC = 1 THEN 'New York City'
        WHEN dd.Metro_Area_LA = 1 THEN 'Los Angeles'
        WHEN dd.Metro_Area_Chicago = 1 THEN 'Chicago'
        WHEN dd.Metro_Area_Dallas = 1 THEN 'Dallas'
        WHEN dd.Metro_Area_Miami = 1 THEN 'Miami'
        ELSE 'Other/Unknown'
    END as metro_area,
    COUNT(*) as total_leads,
    COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) as mql_conversions,
    ROUND(COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(*) * 100, 2) as conversion_rate_percent,
    ROUND(AVG(dd.AUM), 0) as avg_aum
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
INNER JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
GROUP BY 
    CASE 
        WHEN dd.Metro_Area_NYC = 1 THEN 'New York City'
        WHEN dd.Metro_Area_LA = 1 THEN 'Los Angeles'
        WHEN dd.Metro_Area_Chicago = 1 THEN 'Chicago'
        WHEN dd.Metro_Area_Dallas = 1 THEN 'Dallas'
        WHEN dd.Metro_Area_Miami = 1 THEN 'Miami'
        ELSE 'Other/Unknown'
    END
ORDER BY conversion_rate_percent DESC;

-- ===================================================================
-- 4. 30-DAY OUTCOME WINDOW ANALYSIS
-- ===================================================================

-- Detailed 30-day window analysis
SELECT 
    '30-Day Window Analysis' as analysis_type,
    'Overall 30-Day Conversion' as metric,
    COUNT(*) as total_contacted_leads,
    COUNT(CASE 
        WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
        AND DATE(Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
        THEN 1 
    END) as conversions_within_30_days,
    COUNT(CASE 
        WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
        AND DATE(Stage_Entered_Call_Scheduled__c) > DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
        THEN 1 
    END) as conversions_after_30_days,
    ROUND(COUNT(CASE 
        WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
        AND DATE(Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
        THEN 1 
    END) / COUNT(*) * 100, 2) as conversion_rate_30_day_percent,
    ROUND(AVG(CASE 
        WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL 
        AND DATE(Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(Stage_Entered_Contacting__c), INTERVAL 30 DAY)
        THEN DATE_DIFF(DATE(Stage_Entered_Call_Scheduled__c), DATE(Stage_Entered_Contacting__c), DAY)
    END), 1) as avg_days_to_conversion
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE Stage_Entered_Contacting__c IS NOT NULL;

-- ===================================================================
-- 5. TEMPORAL PATTERNS IN CONVERSION RATES
-- ===================================================================

-- Monthly conversion trends
SELECT 
    'Temporal Analysis' as analysis_type,
    'Monthly Conversion Trends' as metric,
    EXTRACT(YEAR FROM Stage_Entered_Contacting__c) as year,
    EXTRACT(MONTH FROM Stage_Entered_Contacting__c) as month,
    COUNT(*) as total_contacted_leads,
    COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) as mql_conversions,
    ROUND(COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(*) * 100, 2) as conversion_rate_percent
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE Stage_Entered_Contacting__c IS NOT NULL
    AND Stage_Entered_Contacting__c >= DATE_SUB(CURRENT_DATE(), INTERVAL 24 MONTH)
GROUP BY 
    EXTRACT(YEAR FROM Stage_Entered_Contacting__c),
    EXTRACT(MONTH FROM Stage_Entered_Contacting__c)
ORDER BY year DESC, month DESC;

-- Day of week conversion patterns
SELECT 
    'Temporal Analysis' as analysis_type,
    'Day of Week Patterns' as metric,
    EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c) as day_of_week,
    CASE EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c)
        WHEN 1 THEN 'Sunday'
        WHEN 2 THEN 'Monday'
        WHEN 3 THEN 'Tuesday'
        WHEN 4 THEN 'Wednesday'
        WHEN 5 THEN 'Thursday'
        WHEN 6 THEN 'Friday'
        WHEN 7 THEN 'Saturday'
    END as day_name,
    COUNT(*) as total_contacted_leads,
    COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) as mql_conversions,
    ROUND(COUNT(CASE WHEN Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(*) * 100, 2) as conversion_rate_percent
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE Stage_Entered_Contacting__c IS NOT NULL
GROUP BY 
    EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c)
ORDER BY day_of_week;

-- ===================================================================
-- 6. CLASS IMBALANCE SUMMARY FOR MODELING
-- ===================================================================

-- Final class imbalance summary for modeling preparation
SELECT 
    'Class Imbalance Summary' as analysis_type,
    'Modeling Dataset' as dataset_type,
    COUNT(*) as total_samples,
    COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) as positive_samples,
    COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NULL THEN 1 END) as negative_samples,
    ROUND(COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(*) * 100, 2) as positive_class_percent,
    ROUND(COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NULL THEN 1 END) / COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END), 2) as imbalance_ratio,
    ROUND(COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 END) / COUNT(CASE WHEN sf.Stage_Entered_Call_Scheduled__c IS NULL THEN 1 END), 4) as positive_to_negative_ratio
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
INNER JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
    AND DATE(sf.Stage_Entered_Contacting__c) <= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);

-- ===================================================================
-- 7. DATA QUALITY VALIDATION
-- ===================================================================

-- Data quality checks for class distribution analysis
SELECT 
    'Data Quality Validation' as analysis_type,
    'CRD Matching Rate' as metric,
    COUNT(DISTINCT sf.Id) as total_salesforce_leads,
    COUNT(DISTINCT sf.FA_CRD__c) as unique_crds_in_salesforce,
    COUNT(DISTINCT dd.RepCRD) as unique_crds_in_discovery,
    COUNT(DISTINCT CASE WHEN dd.RepCRD IS NOT NULL THEN sf.FA_CRD__c END) as matched_crds,
    ROUND(COUNT(DISTINCT CASE WHEN dd.RepCRD IS NOT NULL THEN sf.FA_CRD__c END) / COUNT(DISTINCT sf.FA_CRD__c) * 100, 2) as crd_matching_rate_percent
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_with_features` dd 
    ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;

-- ===================================================================
-- END OF STEP 3.1 CLASS DISTRIBUTION ANALYSIS
-- ===================================================================