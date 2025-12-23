-- ============================================================================
-- EXPLORATION: Does NUM_OF_EMPLOYEES correlate with conversion?
-- ============================================================================

-- Step 1: Check coverage
SELECT
    COUNT(*) as total_leads,
    COUNTIF(f.NUM_OF_EMPLOYEES IS NOT NULL) as has_employee_count,
    ROUND(COUNTIF(f.NUM_OF_EMPLOYEES IS NOT NULL) / COUNT(*) * 100, 2) as coverage_pct,
    AVG(CASE WHEN f.NUM_OF_EMPLOYEES IS NOT NULL THEN f.NUM_OF_EMPLOYEES END) as avg_employees
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` lsf
LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
    ON lsf.firm_crd_at_contact = f.CRD_ID;


-- Step 2: Segment by employee quartiles and check conversion
WITH employee_data AS (
    SELECT
        lsf.lead_id,
        lsf.target as converted,
        f.NUM_OF_EMPLOYEES as num_employees,
        NTILE(4) OVER (ORDER BY f.NUM_OF_EMPLOYEES) as employee_quartile
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` lsf
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
        ON lsf.firm_crd_at_contact = f.CRD_ID
    WHERE f.NUM_OF_EMPLOYEES IS NOT NULL
)

SELECT
    employee_quartile,
    MIN(num_employees) as min_employees,
    MAX(num_employees) as max_employees,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM employee_data), 2) as lift
FROM employee_data
GROUP BY 1
ORDER BY 1;


-- Step 3: Custom buckets (more intuitive than quartiles)
WITH employee_data AS (
    SELECT
        lsf.lead_id,
        lsf.target as converted,
        f.NUM_OF_EMPLOYEES as num_employees,
        CASE
            WHEN f.NUM_OF_EMPLOYEES <= 10 THEN '1_Small (1-10)'
            WHEN f.NUM_OF_EMPLOYEES <= 50 THEN '2_Medium (11-50)'
            WHEN f.NUM_OF_EMPLOYEES <= 200 THEN '3_Large (51-200)'
            WHEN f.NUM_OF_EMPLOYEES <= 1000 THEN '4_Very Large (201-1000)'
            ELSE '5_Enterprise (1000+)'
        END as firm_size_bucket
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` lsf
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
        ON lsf.firm_crd_at_contact = f.CRD_ID
    WHERE f.NUM_OF_EMPLOYEES IS NOT NULL
)

SELECT
    firm_size_bucket,
    COUNT(*) as n_leads,
    SUM(converted) as n_converted,
    ROUND(AVG(converted) * 100, 2) as conversion_rate_pct,
    ROUND(AVG(converted) / (SELECT AVG(converted) FROM employee_data), 2) as lift
FROM employee_data
GROUP BY 1
ORDER BY 1;


-- Step 4: Compare NUM_OF_EMPLOYEES vs calculated rep_count
-- (for the 8.5% that have both)
WITH comparison AS (
    SELECT
        lsf.lead_id,
        lsf.target as converted,
        lsf.firm_rep_count_at_contact as calculated_rep_count,
        f.NUM_OF_EMPLOYEES as reported_employees,
        ROUND(f.NUM_OF_EMPLOYEES / NULLIF(lsf.firm_rep_count_at_contact, 0), 1) as employee_to_rep_ratio
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit_v2` lsf
    LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` f
        ON lsf.firm_crd_at_contact = f.CRD_ID
    WHERE lsf.firm_rep_count_at_contact > 0
      AND f.NUM_OF_EMPLOYEES IS NOT NULL
)

SELECT
    'Coverage comparison' as metric,
    COUNT(*) as n_leads_with_both,
    ROUND(AVG(employee_to_rep_ratio), 1) as avg_employee_to_rep_ratio,
    ROUND(CORR(calculated_rep_count, reported_employees), 3) as correlation
FROM comparison;

