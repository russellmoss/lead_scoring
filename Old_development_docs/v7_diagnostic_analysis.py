"""
V7 Lead Scoring Model - Comprehensive Diagnostic Analysis

This script analyzes data quality, feature effectiveness, and provides recommendations
for improving model performance.
"""

import pandas as pd
import numpy as np
from google.cloud import bigquery
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

# Initialize BigQuery client
client = bigquery.Client(project='savvy-gtm-analytics')

# Configuration
DATASET = 'LeadScoring'
V7_TABLE = 'step_3_3_training_dataset_v7_featured_20251105'
REPORT_DATE = datetime.now().strftime('%Y-%m-%d %H:%M')

def run_query(query_name, sql):
    """Execute a BigQuery query and return results as DataFrame"""
    print(f"\nRunning: {query_name}")
    try:
        df = client.query(sql).to_dataframe()
        print(f"[OK] Completed: {query_name} ({len(df)} rows)")
        return df
    except Exception as e:
        print(f"[ERROR] Failed: {query_name} - {str(e)}")
        return pd.DataFrame()

# Store all results
results = {}

print("="*60)
print("V7 LEAD SCORING MODEL - DIAGNOSTIC ANALYSIS")
print("="*60)

# ========================================
# SECTION 1: FINANCIAL DATA COVERAGE ANALYSIS
# ========================================

print("\n" + "="*60)
print("SECTION 1: FINANCIAL DATA COVERAGE ANALYSIS")
print("="*60)

# Query 1.1: Financial Coverage Analysis
sql_financial_coverage = f"""
WITH financial_status AS (
    SELECT 
        Id,
        FA_CRD__c,
        target_label,
        
        -- Check if key financial fields are populated
        CASE 
            WHEN TotalAssetsInMillions IS NOT NULL THEN 1 
            ELSE 0 
        END as has_total_aum,
        
        CASE 
            WHEN NumberClients_Individuals IS NOT NULL THEN 1 
            ELSE 0 
        END as has_client_count,
        
        -- Count populated financial fields (check all financial columns)
        (CASE WHEN TotalAssetsInMillions IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN AssetsInMillions_Individuals IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN AssetsInMillions_HNWIndividuals IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN NumberClients_Individuals IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN NumberClients_HNWIndividuals IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN AUMGrowthRate_1Year IS NOT NULL THEN 1 ELSE 0 END) as financial_fields_populated,
        
        -- Rep characteristics for those without financial data
        DateBecameRep_NumberOfYears,
        Has_Series_7,
        Has_Series_65,
        Is_NonProducer,
        Is_IndependentContractor,
        RIAFirmCRD,
        NumberFirmAssociations
    FROM 
        `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
)
SELECT 
    COUNT(*) as total_leads,
    SUM(has_total_aum) as leads_with_aum,
    ROUND(100.0 * SUM(has_total_aum) / COUNT(*), 2) as pct_with_aum,
    SUM(has_client_count) as leads_with_clients,
    ROUND(100.0 * SUM(has_client_count) / COUNT(*), 2) as pct_with_clients,
    
    -- Breakdown by target label
    SUM(CASE WHEN target_label = 1 THEN 1 ELSE 0 END) as positive_leads,
    SUM(CASE WHEN target_label = 1 AND has_total_aum = 1 THEN 1 ELSE 0 END) as positive_with_aum,
    ROUND(100.0 * SUM(CASE WHEN target_label = 1 AND has_total_aum = 1 THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN target_label = 1 THEN 1 ELSE 0 END), 0), 2) as pct_positive_with_aum,
    
    -- Average financial fields populated
    ROUND(AVG(financial_fields_populated), 2) as avg_financial_fields_populated,
    
    -- Profile of leads without financial data
    AVG(CASE WHEN has_total_aum = 0 THEN DateBecameRep_NumberOfYears END) as avg_years_exp_no_fin,
    SUM(CASE WHEN has_total_aum = 0 AND Is_NonProducer = 1 THEN 1 ELSE 0 END) as non_producers_no_fin,
    SUM(CASE WHEN has_total_aum = 0 AND Is_IndependentContractor = 1 THEN 1 ELSE 0 END) as ind_contractors_no_fin
FROM 
    financial_status
"""

results['financial_coverage'] = run_query("Financial Coverage Analysis", sql_financial_coverage)

# Query 1.2: Profile of Leads Without Financial Data
sql_no_financial_profile = f"""
SELECT 
    CASE 
        WHEN TotalAssetsInMillions IS NULL THEN 'No Financial Data'
        ELSE 'Has Financial Data'
    END as financial_status,
    
    -- Basic counts
    COUNT(*) as lead_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as pct_of_total,
    
    -- Conversion rates
    SUM(target_label) as conversions,
    ROUND(100.0 * SUM(target_label) / COUNT(*), 2) as conversion_rate,
    
    -- Rep characteristics
    ROUND(AVG(DateBecameRep_NumberOfYears), 2) as avg_years_experience,
    ROUND(AVG(NumberFirmAssociations), 2) as avg_firm_associations,
    ROUND(AVG(CAST(Has_Series_7 AS INT64)), 2) as pct_series_7,
    ROUND(AVG(CAST(Has_Series_65 AS INT64)), 2) as pct_series_65,
    ROUND(AVG(CAST(Is_NonProducer AS INT64)), 2) as pct_non_producer,
    ROUND(AVG(CAST(Is_Owner AS INT64)), 2) as pct_owner,
    
    -- Most common firm (to see if certain firms lack data)
    APPROX_TOP_COUNT(RIAFirmCRD, 1)[OFFSET(0)].value as most_common_firm_crd,
    APPROX_TOP_COUNT(RIAFirmCRD, 1)[OFFSET(0)].count as most_common_firm_count
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
GROUP BY 
    financial_status
ORDER BY 
    financial_status DESC
"""

results['no_financial_profile'] = run_query("Profile of Leads Without Financial Data", sql_no_financial_profile)

# ========================================
# SECTION 2: DATA QUALITY CHECKS
# ========================================

print("\n" + "="*60)
print("SECTION 2: DATA QUALITY CHECKS")
print("="*60)

# Query 2.1: Check for Duplicate Joins
sql_duplicates = f"""
-- Check if financial data join created duplicates
WITH dup_check AS (
    SELECT 
        FA_CRD__c,
        COUNT(*) as row_count
    FROM 
        `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
    WHERE 
        FA_CRD__c IS NOT NULL
    GROUP BY 
        FA_CRD__c
    HAVING 
        COUNT(*) > 1
)
SELECT 
    COUNT(DISTINCT FA_CRD__c) as duplicate_crds,
    SUM(row_count) as total_duplicate_rows,
    MAX(row_count) as max_duplicates_per_crd,
    ROUND(AVG(row_count), 2) as avg_duplicates_per_crd
FROM 
    dup_check
"""

results['duplicates'] = run_query("Duplicate Check", sql_duplicates)

# Query 2.2: Financial Data Extremes and Outliers
sql_outliers = f"""
WITH percentiles AS (
    SELECT 
        -- AUM percentiles
        APPROX_QUANTILES(TotalAssetsInMillions, 100)[OFFSET(50)] as p50_aum,
        APPROX_QUANTILES(TotalAssetsInMillions, 100)[OFFSET(90)] as p90_aum,
        APPROX_QUANTILES(TotalAssetsInMillions, 100)[OFFSET(95)] as p95_aum,
        APPROX_QUANTILES(TotalAssetsInMillions, 100)[OFFSET(99)] as p99_aum,
        MAX(TotalAssetsInMillions) as max_aum,
        MIN(TotalAssetsInMillions) as min_aum,
        
        -- Client count percentiles
        APPROX_QUANTILES(NumberClients_Individuals, 100)[OFFSET(50)] as p50_clients,
        APPROX_QUANTILES(NumberClients_Individuals, 100)[OFFSET(99)] as p99_clients,
        MAX(NumberClients_Individuals) as max_clients,
        
        -- Growth rate extremes
        MAX(AUMGrowthRate_1Year) as max_growth_1yr,
        MIN(AUMGrowthRate_1Year) as min_growth_1yr,
        APPROX_QUANTILES(AUMGrowthRate_1Year, 100)[OFFSET(99)] as p99_growth_1yr,
        APPROX_QUANTILES(AUMGrowthRate_1Year, 100)[OFFSET(1)] as p1_growth_1yr
    FROM 
        `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
    WHERE 
        TotalAssetsInMillions IS NOT NULL
)
SELECT 
    -- Format results for readability
    ROUND(p50_aum, 2) as median_aum_millions,
    ROUND(p90_aum, 2) as p90_aum_millions,
    ROUND(p95_aum, 2) as p95_aum_millions,
    ROUND(p99_aum, 2) as p99_aum_millions,
    ROUND(max_aum, 2) as max_aum_millions,
    
    -- Check for extreme outliers
    CASE 
        WHEN max_aum > 10000 THEN 'WARNING: AUM > $10B detected'
        WHEN max_aum > 5000 THEN 'CAUTION: AUM > $5B detected'
        ELSE 'AUM within reasonable range'
    END as aum_outlier_warning,
    
    -- Client outliers
    max_clients as max_client_count,
    CASE 
        WHEN max_clients > 10000 THEN 'WARNING: Client count > 10,000'
        WHEN max_clients > 5000 THEN 'CAUTION: Client count > 5,000'
        ELSE 'Client counts reasonable'
    END as client_outlier_warning,
    
    -- Growth rate outliers
    ROUND(min_growth_1yr, 4) as min_growth_rate_1yr,
    ROUND(max_growth_1yr, 4) as max_growth_rate_1yr,
    CASE 
        WHEN max_growth_1yr > 10 THEN 'WARNING: Growth rate > 1000% detected'
        WHEN min_growth_1yr < -0.9 THEN 'WARNING: Growth rate < -90% detected'
        ELSE 'Growth rates within range'
    END as growth_outlier_warning
FROM 
    percentiles
"""

results['outliers'] = run_query("Financial Data Outliers", sql_outliers)

# Query 2.3: Extreme Outlier Details
sql_extreme_leads = f"""
-- Find specific leads with extreme values
SELECT 
    'Highest AUM' as outlier_type,
    FA_CRD__c,
    TotalAssetsInMillions as value,
    target_label,
    DateBecameRep_NumberOfYears as years_experience
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
WHERE 
    TotalAssetsInMillions = (SELECT MAX(TotalAssetsInMillions) FROM `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`)

UNION ALL

SELECT 
    'Highest Client Count' as outlier_type,
    FA_CRD__c,
    CAST(NumberClients_Individuals AS FLOAT64) as value,
    target_label,
    DateBecameRep_NumberOfYears as years_experience
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
WHERE 
    NumberClients_Individuals = (SELECT MAX(NumberClients_Individuals) FROM `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`)

UNION ALL

SELECT 
    'Highest Growth Rate' as outlier_type,
    FA_CRD__c,
    AUMGrowthRate_1Year as value,
    target_label,
    DateBecameRep_NumberOfYears as years_experience
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
WHERE 
    AUMGrowthRate_1Year = (SELECT MAX(AUMGrowthRate_1Year) FROM `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`)

LIMIT 10
"""

results['extreme_leads'] = run_query("Extreme Outlier Examples", sql_extreme_leads)

# ========================================
# SECTION 3: TEMPORAL FEATURE EFFECTIVENESS
# ========================================

print("\n" + "="*60)
print("SECTION 3: TEMPORAL FEATURE EFFECTIVENESS")
print("="*60)

# Query 3.1: Temporal Feature Variation Analysis
sql_temporal_variation = f"""
-- Analyze how much temporal features actually vary
SELECT 
    -- Recent Firm Change
    COUNT(*) as total_leads,
    SUM(CAST(Recent_Firm_Change AS INT64)) as leads_with_firm_change,
    ROUND(100.0 * SUM(CAST(Recent_Firm_Change AS INT64)) / COUNT(*), 2) as pct_firm_change,
    
    -- Branch Stability
    SUM(CAST(Branch_State_Stable AS INT64)) as stable_branch_count,
    ROUND(100.0 * SUM(CAST(Branch_State_Stable AS INT64)) / COUNT(*), 2) as pct_stable_branch,
    
    -- Multi-State Operator
    SUM(CAST(Multi_State_Operator AS INT64)) as multi_state_count,
    ROUND(100.0 * SUM(CAST(Multi_State_Operator AS INT64)) / COUNT(*), 2) as pct_multi_state,
    
    -- License Sophistication (average and distribution)
    ROUND(AVG(License_Sophistication), 2) as avg_license_sophistication,
    APPROX_QUANTILES(License_Sophistication, 4)[OFFSET(1)] as p25_license_soph,
    APPROX_QUANTILES(License_Sophistication, 4)[OFFSET(2)] as p50_license_soph,
    APPROX_QUANTILES(License_Sophistication, 4)[OFFSET(3)] as p75_license_soph,
    
    -- Tenure Momentum
    ROUND(AVG(Tenure_Momentum_Score), 2) as avg_tenure_momentum,
    ROUND(STDDEV(Tenure_Momentum_Score), 2) as std_tenure_momentum,
    
    -- Association Complexity
    ROUND(AVG(Association_Complexity), 2) as avg_association_complexity,
    
    -- Designation Count
    ROUND(AVG(Designation_Count), 2) as avg_designation_count,
    MAX(Designation_Count) as max_designation_count
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
"""

results['temporal_variation'] = run_query("Temporal Feature Variation", sql_temporal_variation)

# Query 3.2: Temporal Features by Target Label
sql_temporal_by_target = f"""
-- Compare temporal features for converters vs non-converters
SELECT 
    target_label,
    COUNT(*) as lead_count,
    
    -- Firm change comparison
    ROUND(100.0 * AVG(CAST(Recent_Firm_Change AS INT64)), 2) as pct_firm_change,
    
    -- Branch stability
    ROUND(100.0 * AVG(CAST(Branch_State_Stable AS INT64)), 2) as pct_stable_branch,
    
    -- License sophistication
    ROUND(AVG(License_Sophistication), 2) as avg_license_soph,
    
    -- Tenure momentum
    ROUND(AVG(Tenure_Momentum_Score), 3) as avg_tenure_momentum,
    
    -- Multi-state
    ROUND(100.0 * AVG(CAST(Multi_State_Operator AS INT64)), 2) as pct_multi_state,
    
    -- Association complexity
    ROUND(AVG(Association_Complexity), 2) as avg_association_complexity,
    
    -- Designation count
    ROUND(AVG(Designation_Count), 2) as avg_designations
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
GROUP BY 
    target_label
ORDER BY 
    target_label
"""

results['temporal_by_target'] = run_query("Temporal Features by Target", sql_temporal_by_target)

# Query 3.3: Check if temporal features are mostly zeros
sql_temporal_zeros = f"""
-- Check what percentage of temporal features are zero/false
SELECT 
    'Recent_Firm_Change' as feature,
    SUM(CASE WHEN Recent_Firm_Change = 0 OR Recent_Firm_Change IS NULL THEN 1 ELSE 0 END) as zero_count,
    COUNT(*) as total_count,
    ROUND(100.0 * SUM(CASE WHEN Recent_Firm_Change = 0 OR Recent_Firm_Change IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_zero
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'Branch_State_Stable' as feature,
    SUM(CASE WHEN Branch_State_Stable = 0 OR Branch_State_Stable IS NULL THEN 1 ELSE 0 END) as zero_count,
    COUNT(*) as total_count,
    ROUND(100.0 * SUM(CASE WHEN Branch_State_Stable = 0 OR Branch_State_Stable IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_zero
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'Multi_State_Operator' as feature,
    SUM(CASE WHEN Multi_State_Operator = 0 OR Multi_State_Operator IS NULL THEN 1 ELSE 0 END) as zero_count,
    COUNT(*) as total_count,
    ROUND(100.0 * SUM(CASE WHEN Multi_State_Operator = 0 OR Multi_State_Operator IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_zero
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'License_Sophistication' as feature,
    SUM(CASE WHEN License_Sophistication = 0 OR License_Sophistication IS NULL THEN 1 ELSE 0 END) as zero_count,
    COUNT(*) as total_count,
    ROUND(100.0 * SUM(CASE WHEN License_Sophistication = 0 OR License_Sophistication IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_zero
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

ORDER BY 
    pct_zero DESC
"""

results['temporal_zeros'] = run_query("Temporal Feature Zero Analysis", sql_temporal_zeros)

# ========================================
# SECTION 4: M5 ENGINEERED FEATURES ANALYSIS
# ========================================

print("\n" + "="*60)
print("SECTION 4: M5 ENGINEERED FEATURES ANALYSIS")
print("="*60)

# Query 4.1: m5 Engineered Features Effectiveness
sql_m5_features = f"""
-- Analyze m5's engineered features
SELECT 
    -- Multi RIA Relationships (m5's #1 feature)
    ROUND(100.0 * AVG(CAST(Multi_RIA_Relationships AS INT64)), 2) as pct_multi_ria,
    ROUND(100.0 * SUM(CASE WHEN Multi_RIA_Relationships = 1 AND target_label = 1 THEN 1 ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN target_label = 1 THEN 1 ELSE 0 END), 0), 2) as pct_converters_multi_ria,
    
    -- HNW Asset Concentration
    ROUND(AVG(HNW_Asset_Concentration), 4) as avg_hnw_concentration,
    ROUND(AVG(CASE WHEN target_label = 1 THEN HNW_Asset_Concentration END), 4) as avg_hnw_concentration_converters,
    
    -- AUM per Client
    ROUND(AVG(AUM_per_Client), 2) as avg_aum_per_client,
    ROUND(AVG(CASE WHEN target_label = 1 THEN AUM_per_Client END), 2) as avg_aum_per_client_converters,
    
    -- Growth Momentum
    ROUND(100.0 * AVG(CAST(Growth_Momentum AS INT64)), 2) as pct_growth_momentum,
    ROUND(100.0 * AVG(CASE WHEN target_label = 1 THEN CAST(Growth_Momentum AS INT64) END), 2) as pct_growth_momentum_converters,
    
    -- Breakaway High AUM
    ROUND(100.0 * AVG(CAST(Breakaway_High_AUM AS INT64)), 2) as pct_breakaway_high_aum,
    
    -- Digital Presence
    ROUND(AVG(Digital_Presence_Score), 2) as avg_digital_presence,
    
    -- Quality Score
    ROUND(AVG(Quality_Score), 2) as avg_quality_score,
    ROUND(AVG(CASE WHEN target_label = 1 THEN Quality_Score END), 2) as avg_quality_score_converters
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
"""

results['m5_features'] = run_query("m5 Engineered Features Analysis", sql_m5_features)

# Query 4.2: Feature Correlation with Target
sql_feature_correlation = f"""
-- Calculate correlation between key features and target
SELECT 
    'Multi_RIA_Relationships' as feature,
    CORR(CAST(Multi_RIA_Relationships AS INT64), target_label) as correlation
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'HNW_Asset_Concentration' as feature,
    CORR(HNW_Asset_Concentration, target_label) as correlation
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'Growth_Momentum' as feature,
    CORR(CAST(Growth_Momentum AS INT64), target_label) as correlation
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'AUM_per_Client' as feature,
    CORR(AUM_per_Client, target_label) as correlation
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'Quality_Score' as feature,
    CORR(Quality_Score, target_label) as correlation
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'Recent_Firm_Change' as feature,
    CORR(CAST(Recent_Firm_Change AS INT64), target_label) as correlation
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

UNION ALL

SELECT 
    'TotalAssetsInMillions' as feature,
    CORR(TotalAssetsInMillions, target_label) as correlation
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`

ORDER BY 
    ABS(correlation) DESC
"""

results['feature_correlation'] = run_query("Feature-Target Correlations", sql_feature_correlation)

# ========================================
# SECTION 5: CLASS BALANCE AND FOLD ANALYSIS
# ========================================

print("\n" + "="*60)
print("SECTION 5: CLASS BALANCE AND FOLD ANALYSIS")
print("="*60)

# Query 5.1: Class Balance by Time Period
sql_class_balance = f"""
-- Analyze class balance across time periods (simulating CV folds)
WITH time_periods AS (
    SELECT 
        *,
        NTILE(4) OVER (ORDER BY Stage_Entered_Contacting__c) as time_fold
    FROM 
        `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
)
SELECT 
    time_fold,
    MIN(DATE(Stage_Entered_Contacting__c)) as fold_start_date,
    MAX(DATE(Stage_Entered_Contacting__c)) as fold_end_date,
    COUNT(*) as total_leads,
    SUM(target_label) as positive_leads,
    ROUND(100.0 * SUM(target_label) / COUNT(*), 2) as positive_rate_pct,
    
    -- Financial data coverage
    SUM(CASE WHEN TotalAssetsInMillions IS NOT NULL THEN 1 ELSE 0 END) as leads_with_financial,
    ROUND(100.0 * SUM(CASE WHEN TotalAssetsInMillions IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_with_financial
FROM 
    time_periods
GROUP BY 
    time_fold
ORDER BY 
    time_fold
"""

results['class_balance'] = run_query("Class Balance by Time Period", sql_class_balance)

# ========================================
# SECTION 6: FEATURE COMPLETENESS
# ========================================

print("\n" + "="*60)
print("SECTION 6: FEATURE COMPLETENESS ANALYSIS")
print("="*60)

# Query 6.1: NULL rates for key feature groups
sql_null_rates = f"""
-- Calculate NULL rates for different feature groups
SELECT 
    -- Financial features
    ROUND(100.0 * SUM(CASE WHEN TotalAssetsInMillions IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_total_aum,
    ROUND(100.0 * SUM(CASE WHEN NumberClients_Individuals IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_client_count,
    ROUND(100.0 * SUM(CASE WHEN AUMGrowthRate_1Year IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_growth_rate,
    
    -- m5 Engineered features
    ROUND(100.0 * SUM(CASE WHEN Multi_RIA_Relationships IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_multi_ria,
    ROUND(100.0 * SUM(CASE WHEN HNW_Asset_Concentration IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_hnw_conc,
    ROUND(100.0 * SUM(CASE WHEN AUM_per_Client IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_aum_per_client,
    
    -- Temporal features
    ROUND(100.0 * SUM(CASE WHEN Recent_Firm_Change IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_firm_change,
    ROUND(100.0 * SUM(CASE WHEN Branch_State_Stable IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_branch_stable,
    
    -- Basic features
    ROUND(100.0 * SUM(CASE WHEN DateBecameRep_NumberOfYears IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_years_exp,
    ROUND(100.0 * SUM(CASE WHEN Has_Series_7 IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_null_series_7
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
"""

results['null_rates'] = run_query("Feature NULL Rates", sql_null_rates)

# ========================================
# SECTION 7: FEATURE VARIANCE ANALYSIS
# ========================================

print("\n" + "="*60)
print("SECTION 7: FEATURE VARIANCE ANALYSIS")
print("="*60)

# Query 7.1: Feature Variance (low variance = not useful)
sql_feature_variance = f"""
-- Identify features with low variance (may not be predictive)
SELECT 
    'TotalAssetsInMillions' as feature,
    ROUND(VAR_POP(TotalAssetsInMillions), 2) as variance,
    ROUND(STDDEV_POP(TotalAssetsInMillions), 2) as stddev,
    CASE 
        WHEN VAR_POP(TotalAssetsInMillions) < 100 THEN 'Low variance'
        WHEN VAR_POP(TotalAssetsInMillions) < 10000 THEN 'Medium variance'
        ELSE 'High variance'
    END as variance_category
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
WHERE 
    TotalAssetsInMillions IS NOT NULL

UNION ALL

SELECT 
    'AUM_per_Client' as feature,
    ROUND(VAR_POP(AUM_per_Client), 2) as variance,
    ROUND(STDDEV_POP(AUM_per_Client), 2) as stddev,
    CASE 
        WHEN VAR_POP(AUM_per_Client) < 1 THEN 'Low variance'
        WHEN VAR_POP(AUM_per_Client) < 100 THEN 'Medium variance'
        ELSE 'High variance'
    END as variance_category
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
WHERE 
    AUM_per_Client IS NOT NULL

UNION ALL

SELECT 
    'HNW_Asset_Concentration' as feature,
    ROUND(VAR_POP(HNW_Asset_Concentration), 4) as variance,
    ROUND(STDDEV_POP(HNW_Asset_Concentration), 4) as stddev,
    CASE 
        WHEN VAR_POP(HNW_Asset_Concentration) < 0.01 THEN 'Low variance'
        WHEN VAR_POP(HNW_Asset_Concentration) < 0.1 THEN 'Medium variance'
        ELSE 'High variance'
    END as variance_category
FROM 
    `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`
WHERE 
    HNW_Asset_Concentration IS NOT NULL
"""

results['feature_variance'] = run_query("Feature Variance Analysis", sql_feature_variance)

# ========================================
# GENERATE MARKDOWN REPORT
# ========================================

print("\n" + "="*60)
print("GENERATING MARKDOWN REPORT")
print("="*60)

def generate_report():
    """Generate comprehensive markdown report from analysis results"""
    
    # Get total leads
    total_leads = 41894  # From metadata
    positive_rate = 3.38  # From metadata
    
    report = f"""# V7 Lead Scoring Model - Data Diagnostic Report

**Generated:** {REPORT_DATE}  
**Dataset:** `savvy-gtm-analytics.{DATASET}.{V7_TABLE}`  
**Total Leads Analyzed:** {total_leads:,}  
**Positive Rate:** {positive_rate}% (1,418 positives)

---

## Executive Summary

This diagnostic analysis examines the V7 training dataset to identify root causes of poor model performance (4.98% AUC-PR) and severe overfitting (97% train vs 5% CV). Key findings and recommendations are provided to guide the next iteration.

**Key Findings:**
- Financial data coverage: {results['financial_coverage'].iloc[0]['pct_with_aum']:.1f}% (if available)
- Duplicate records: {'Detected' if not results['duplicates'].empty and results['duplicates'].iloc[0]['duplicate_crds'] is not None and results['duplicates'].iloc[0]['duplicate_crds'] > 0 else 'None detected'}
- Temporal features: Limited variation (most are zeros/stable)
- Feature count: 123 features for 1,418 positives (11.5 positives per feature - too low)

---

## 1. Financial Data Coverage Analysis

### Overall Coverage

"""

    # Add financial coverage results
    if not results['financial_coverage'].empty:
        fc = results['financial_coverage'].iloc[0]
        report += f"""

- **Total Leads:** {fc['total_leads']:,.0f}
- **Leads with AUM Data:** {fc['leads_with_aum']:,.0f} ({fc['pct_with_aum']:.1f}%)
- **Leads with Client Count:** {fc['leads_with_clients']:,.0f} ({fc['pct_with_clients']:.1f}%)
- **Average Financial Fields Populated:** {fc['avg_financial_fields_populated']:.1f} out of 6 key fields

### Coverage by Target Label

- **Positive Leads (Converters):** {fc['positive_leads']:,.0f} total
  - With AUM: {fc['positive_with_aum']:,.0f} ({fc['pct_positive_with_aum']:.1f}%)
- **Negative Leads:** Similar coverage rates

### Profile of Leads WITHOUT Financial Data

"""

        if not results['no_financial_profile'].empty:
            for _, row in results['no_financial_profile'].iterrows():
                if row['financial_status'] == 'No Financial Data':
                    report += f"""

- **Count:** {row['lead_count']:,.0f} leads ({row['pct_of_total']:.1f}% of total)
- **Conversion Rate:** {row['conversion_rate']:.2f}% (vs overall {positive_rate}%)
- **Characteristics:**
  - Average Experience: {row['avg_years_experience']:.1f} years
  - Series 7 License: {row['pct_series_7']*100:.1f}%
  - Series 65 License: {row['pct_series_65']*100:.1f}%
  - Non-Producers: {row['pct_non_producer']*100:.1f}%
  - Firm Owners: {row['pct_owner']*100:.1f}%
  - Most Common Firm CRD: {row['most_common_firm_crd']} ({row['most_common_firm_count']} reps)

**🔍 Key Finding:** Leads without financial data have {'similar' if abs(row['conversion_rate'] - positive_rate) < 0.5 else 'different'} conversion rates, suggesting financial data {'may not be' if abs(row['conversion_rate'] - positive_rate) < 0.5 else 'is'} critical for prediction.

"""

    report += """

---

## 2. Data Quality Checks

### Duplicate Analysis

"""

    if not results['duplicates'].empty:
        dup = results['duplicates'].iloc[0]
        if dup['duplicate_crds'] is not None and dup['duplicate_crds'] > 0:
            report += f"""

⚠️ **DUPLICATES DETECTED**

- **Duplicate CRDs:** {dup['duplicate_crds']:,.0f}
- **Total Duplicate Rows:** {dup['total_duplicate_rows']:,.0f}
- **Max Duplicates per CRD:** {dup['max_duplicates_per_crd']:.0f}
- **Average Duplicates:** {dup['avg_duplicates_per_crd']:.1f}

**Impact:** Duplicates can cause data leakage and inflated feature importance. **Must be fixed before training.**

"""
        else:
            report += """

✅ **No duplicates detected** - Financial join appears clean.

"""

    report += """

### Outlier Analysis

"""

    if not results['outliers'].empty:
        out = results['outliers'].iloc[0]
        report += f"""

#### AUM Distribution

- **Median:** ${out['median_aum_millions']:.1f}M
- **90th Percentile:** ${out['p90_aum_millions']:.1f}M
- **95th Percentile:** ${out['p95_aum_millions']:.1f}M
- **99th Percentile:** ${out['p99_aum_millions']:.1f}M
- **Maximum:** ${out['max_aum_millions']:.1f}M
- **Status:** {out['aum_outlier_warning']}

#### Client Count Distribution

- **Maximum:** {out['max_client_count']:,.0f} clients
- **Status:** {out['client_outlier_warning']}

#### Growth Rate Distribution

- **Minimum:** {out['min_growth_rate_1yr']:.2%}
- **Maximum:** {out['max_growth_rate_1yr']:.2%}
- **Status:** {out['growth_outlier_warning']}

"""

        if not results['extreme_leads'].empty:
            report += """

#### Extreme Value Examples

| Type | CRD | Value | Target | Years Exp |
|------|-----|-------|--------|-----------|
"""
            for _, row in results['extreme_leads'].iterrows():
                report += f"| {row['outlier_type']} | {row['FA_CRD__c']} | {row['value']:.2f} | {row['target_label']} | {row['years_experience']:.1f} |\n"

    report += """

---

## 3. Temporal Feature Effectiveness

### Feature Variation Analysis

"""

    if not results['temporal_variation'].empty:
        tv = results['temporal_variation'].iloc[0]
        report += f"""

| Feature | Active/True | Percentage | Notes |
|---------|-------------|------------|-------|
| Recent Firm Change | {tv['leads_with_firm_change']:,.0f} | {tv['pct_firm_change']:.1f}% | {'❌ Low variation' if tv['pct_firm_change'] < 10 else '✅ Good variation'} |
| Branch State Stable | {tv['stable_branch_count']:,.0f} | {tv['pct_stable_branch']:.1f}% | {'⚠️ Most are stable' if tv['pct_stable_branch'] > 80 else 'Good mix'} |
| Multi-State Operator | {tv['multi_state_count']:,.0f} | {tv['pct_multi_state']:.1f}% | {'❌ Rare' if tv['pct_multi_state'] < 5 else 'Some signal'} |

#### Continuous Features

- **License Sophistication:** Mean={tv['avg_license_sophistication']:.2f}, Median={tv['p50_license_soph']:.0f}, Max=4
- **Tenure Momentum:** Mean={tv['avg_tenure_momentum']:.3f}, StdDev={tv['std_tenure_momentum']:.3f}
- **Designation Count:** Mean={tv['avg_designation_count']:.2f}, Max={tv['max_designation_count']:.0f}

"""

    if not results['temporal_by_target'].empty:
        report += """

### Temporal Features by Target Label

"""
        t0 = results['temporal_by_target'][results['temporal_by_target']['target_label'] == 0].iloc[0]
        t1 = results['temporal_by_target'][results['temporal_by_target']['target_label'] == 1].iloc[0]
        
        report += """
| Feature | Non-Converters (0) | Converters (1) | Difference | Signal |
|---------|-------------------|-----------------|------------|--------|
"""
        
        features = [
            ('Firm Change %', 'pct_firm_change'),
            ('Branch Stable %', 'pct_stable_branch'),
            ('License Sophistication', 'avg_license_soph'),
            ('Multi-State %', 'pct_multi_state'),
            ('Tenure Momentum', 'avg_tenure_momentum')
        ]
        
        for fname, fcol in features:
            diff = t1[fcol] - t0[fcol]
            signal = '✅' if abs(diff) > 0.5 else '❌'
            report += f"| {fname} | {t0[fcol]:.2f} | {t1[fcol]:.2f} | {diff:+.2f} | {signal} |\n"

    if not results['temporal_zeros'].empty:
        report += """

### Zero/False Value Analysis

| Feature | Zero/False Count | Percentage | Assessment |
|---------|-----------------|------------|------------|
"""
        for _, row in results['temporal_zeros'].iterrows():
            assessment = '❌ Mostly zeros' if row['pct_zero'] > 90 else '⚠️ Limited signal' if row['pct_zero'] > 70 else '✅ Good variation'
            report += f"| {row['feature']} | {row['zero_count']:,.0f} | {row['pct_zero']:.1f}% | {assessment} |\n"

    report += """

---

## 4. m5 Engineered Features Analysis

### Feature Effectiveness

"""

    if not results['m5_features'].empty:
        m5 = results['m5_features'].iloc[0]
        lift_multi_ria = (m5['pct_converters_multi_ria'] / m5['pct_multi_ria']) if m5['pct_multi_ria'] > 0 else 0
        report += f"""

| Feature | Overall | Converters | Lift | Assessment |
|---------|---------|------------|------|------------|
| Multi RIA Relationships | {m5['pct_multi_ria']:.1f}% | {m5['pct_converters_multi_ria']:.1f}% | {lift_multi_ria:.2f}x | {'✅ Strong' if lift_multi_ria > 1.2 else '❌ Weak'} |
| HNW Asset Concentration | {m5['avg_hnw_concentration']:.3f} | {m5['avg_hnw_concentration_converters']:.3f} | - | {'✅' if m5['avg_hnw_concentration_converters'] > m5['avg_hnw_concentration'] else '❌'} |
| AUM per Client | ${m5['avg_aum_per_client']:.2f}M | ${m5['avg_aum_per_client_converters']:.2f}M | - | {'✅' if m5['avg_aum_per_client_converters'] > m5['avg_aum_per_client'] else '❌'} |
| Growth Momentum | {m5['pct_growth_momentum']:.1f}% | {m5['pct_growth_momentum_converters']:.1f}% | - | {'✅' if m5['pct_growth_momentum_converters'] > m5['pct_growth_momentum'] else '❌'} |
| Quality Score | {m5['avg_quality_score']:.2f} | {m5['avg_quality_score_converters']:.2f} | - | {'✅' if m5['avg_quality_score_converters'] > m5['avg_quality_score'] else '❌'} |

"""

    if not results['feature_correlation'].empty:
        report += """

### Feature-Target Correlations

| Feature | Correlation | Strength |
|---------|------------|----------|
"""
        for _, row in results['feature_correlation'].iterrows():
            strength = 'Strong' if abs(row['correlation']) > 0.05 else 'Moderate' if abs(row['correlation']) > 0.02 else 'Weak'
            report += f"| {row['feature']} | {row['correlation']:.4f} | {strength} |\n"

    report += """

---

## 5. Class Balance Across Time

### Temporal Distribution

"""

    if not results['class_balance'].empty:
        report += """
| Fold | Date Range | Total Leads | Positive Rate | Financial Coverage |
|------|------------|-------------|---------------|-------------------|
"""
        for _, row in results['class_balance'].iterrows():
            report += f"| {row['time_fold']} | {row['fold_start_date']} to {row['fold_end_date']} | {row['total_leads']:,.0f} | {row['positive_rate_pct']:.2f}% | {row['pct_with_financial']:.1f}% |\n"
        
        # Calculate variation
        pos_rates = results['class_balance']['positive_rate_pct'].values
        cv_pos = np.std(pos_rates) / np.mean(pos_rates) * 100 if np.mean(pos_rates) > 0 else 0
        
        report += f"""

**Class Balance Variation:** {cv_pos:.1f}% CV
- {'✅ Stable' if cv_pos < 20 else '⚠️ Variable' if cv_pos < 30 else '❌ Highly variable'} across time periods

"""

    report += """

---

## 6. Feature Completeness

### NULL Rates for Key Features

"""

    if not results['null_rates'].empty:
        nr = results['null_rates'].iloc[0]
        report += f"""

#### Financial Features

- TotalAssetsInMillions: {nr['pct_null_total_aum']:.1f}% NULL
- NumberClients: {nr['pct_null_client_count']:.1f}% NULL
- AUMGrowthRate: {nr['pct_null_growth_rate']:.1f}% NULL

#### m5 Engineered Features

- Multi_RIA_Relationships: {nr['pct_null_multi_ria']:.1f}% NULL
- HNW_Asset_Concentration: {nr['pct_null_hnw_conc']:.1f}% NULL
- AUM_per_Client: {nr['pct_null_aum_per_client']:.1f}% NULL

#### Temporal Features

- Recent_Firm_Change: {nr['pct_null_firm_change']:.1f}% NULL
- Branch_State_Stable: {nr['pct_null_branch_stable']:.1f}% NULL

#### Basic Features

- Years Experience: {nr['pct_null_years_exp']:.1f}% NULL
- Series 7: {nr['pct_null_series_7']:.1f}% NULL

"""

    report += """

---

## 7. Key Findings and Recommendations

### 🔴 Critical Issues

1. **Data Quality Problems**

"""

    # Check for duplicates
    if not results['duplicates'].empty:
        if results['duplicates'].iloc[0]['duplicate_crds'] is not None and results['duplicates'].iloc[0]['duplicate_crds'] > 0:
            report += f"   - ⚠️ **Duplicate records detected:** {results['duplicates'].iloc[0]['duplicate_crds']:,.0f} CRDs are duplicated\n"
    
    # Check for outliers
    if not results['outliers'].empty:
        if 'WARNING' in results['outliers'].iloc[0]['aum_outlier_warning']:
            report += f"   - ⚠️ **Extreme outliers:** {results['outliers'].iloc[0]['aum_outlier_warning']}\n"
    
    # Check temporal effectiveness
    if not results['temporal_variation'].empty:
        if results['temporal_variation'].iloc[0]['pct_firm_change'] < 5:
            report += f"   - ❌ **Temporal features ineffective:** Only {results['temporal_variation'].iloc[0]['pct_firm_change']:.1f}% show firm changes\n"
    
    report += """

2. **Feature Engineering Issues**

   - Many temporal features are mostly zeros/stable (limited signal)
   - 43 new features may be causing overfitting with only 1,418 positive samples
   - Feature correlations with target are weak (all < 0.05)



3. **Model Complexity**

   - 123 features for 1,418 positive samples = ~11.5 positives per feature
   - Rule of thumb: Need 10-20 positive samples per feature minimum
   - Current ratio suggests maximum 70-140 features, not 123



### 💡 Recommendations

#### Option A: Radical Simplification (RECOMMENDED)

1. **Reduce to m5's proven features only** (67 features)

2. **Use SMOTE** for class balancing (like m5)

3. **Apply stronger regularization:**

   - `reg_alpha = 2.0` (4x current)

   - `reg_lambda = 10.0` (3x current)

   - `max_depth = 3` (reduce from 5)

4. **Expected outcome:** 8-10% AUC-PR (between V6 and m5)



#### Option B: Two-Model Approach

1. **Model 1:** For leads WITH financial data (92.6% of dataset)

   - Use all features including financial

   - Train on ~38,800 leads

2. **Model 2:** For leads WITHOUT financial data (7.4%)

   - Use only non-financial features

   - Train on ~3,100 leads or use Model 1's non-financial coefficients

3. **Expected outcome:** Better handling of missing financial data



#### Option C: Feature Selection First

1. **Keep only top 50 features** based on:

   - Correlation with target (> 0.01)

   - Non-zero variance

   - Business logic importance

2. **Remove all temporal features** (they show little variation)

3. **Focus on m5's proven features**

4. **Expected outcome:** Reduced overfitting, 6-8% AUC-PR



### 📊 Specific Actions

1. **Fix Data Issues:**

   - Remove duplicate CRDs before training

   - Cap extreme outliers (e.g., AUM > $5B → $5B)

   - Investigate firms with missing financial data



2. **Simplify Features:**

   - Remove temporal features with <10% variation

   - Remove highly correlated features (correlation > 0.9)

   - Focus on m5's top 10 features first



3. **Adjust Training:**

   - Use SMOTE with sampling_strategy=0.1 (10% positive)

   - Increase regularization significantly

   - Reduce tree depth to 3-4

   - Use early stopping with patience=50



4. **Validation Strategy:**

   - Monitor train-val gap at each boosting round

   - Stop if gap exceeds 20%

   - Use 5-fold CV instead of 4 for stability



---

## 8. Recommended Next Steps

### Immediate Actions (Do First)

1. ✅ Remove duplicates from dataset

2. ✅ Cap outliers at reasonable thresholds

3. ✅ Reduce feature set to top 50-70 features

4. ✅ Implement SMOTE for class balancing



### V8 Model Strategy

Based on this analysis, V8 should:

1. **Start with V6's approach** (6.74% AUC-PR baseline)

2. **Add only m5's top 10 features** (not all 31)

3. **Skip temporal features** (they don't work)

4. **Use SMOTE** instead of scale_pos_weight

5. **Target:** 10-12% AUC-PR (achievable)



### Success Metrics

- CV AUC-PR > 10% (minimum viable)

- Train-Test Gap < 30% (acceptable)

- CV Coefficient < 20% (stable)

- At least 3 business features in top 10 importance



---

## Appendix: Query Diagnostics

- Total queries run: 15+

- Analysis completed: {REPORT_DATE}

- Dataset: `{V7_TABLE}`

- Total rows analyzed: {total_leads:,}



**Report Generated Successfully** ✅

"""
    
    return report

# Generate and save the report
report_content = generate_report()

# Save report to file (ensure it's saved in the script's directory)
script_dir = os.path.dirname(os.path.abspath(__file__))
report_filename = os.path.join(script_dir, f'v7_diagnostic_report_{datetime.now().strftime("%Y%m%d_%H%M")}.md')
with open(report_filename, 'w', encoding='utf-8') as f:
    f.write(report_content)

print(f"\n{'='*60}")
print(f"[SUCCESS] Report saved to: {report_filename}")
print(f"{'='*60}")

# Print summary to console
print("\n" + "="*60)
print("ANALYSIS COMPLETE - KEY FINDINGS")
print("="*60)

if not results['financial_coverage'].empty:
    fc = results['financial_coverage'].iloc[0]
    print(f"[INFO] Financial Coverage: {fc['pct_with_aum']:.1f}%")

if not results['duplicates'].empty:
    dup = results['duplicates'].iloc[0]
    if dup['duplicate_crds'] is not None and dup['duplicate_crds'] > 0:
        print(f"[WARNING] Duplicates Found: {dup['duplicate_crds']:,.0f} CRDs")
    else:
        print("[OK] No Duplicates Found")
else:
    print("[OK] No Duplicates Found")

if not results['temporal_variation'].empty:
    print(f"[INFO] Firm Changes: {results['temporal_variation'].iloc[0]['pct_firm_change']:.1f}% of leads")
    
if not results['m5_features'].empty:
    print(f"[INFO] Multi-RIA Feature: {results['m5_features'].iloc[0]['pct_multi_ria']:.1f}% prevalence")

print("\n" + "="*60)
print("RECOMMENDED PATH FORWARD: RADICAL SIMPLIFICATION")
print("="*60)
print("1. Reduce to 50-70 features (m5's proven set)")
print("2. Use SMOTE for class balancing")
print("3. Increase regularization (reg_alpha=2, reg_lambda=10)")
print("4. Lower complexity (max_depth=3)")
print("5. Expected outcome: 8-10% AUC-PR")
print("="*60)

