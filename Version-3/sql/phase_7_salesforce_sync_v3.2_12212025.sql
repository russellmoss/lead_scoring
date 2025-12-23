
-- ============================================================================
-- SALESFORCE SYNC QUERY - V3.2_12212025
-- ============================================================================
-- Export this data for Salesforce Lead custom field updates
-- Run this query and export results for Salesforce Bulk API or Data Loader

SELECT 
    lead_id as Id,
    score_tier as Lead_Score_Tier__c,
    tier_display as Lead_Tier_Display__c,
    CAST(ROUND(expected_conversion_rate * 100, 1) AS STRING) || '%' as Expected_Conversion_Rate__c,
    CAST(expected_lift AS STRING) || 'x' as Expected_Lift__c,
    priority_rank as Lead_Priority_Rank__c,
    action_recommended as Lead_Action_Recommended__c,
    tier_explanation as Lead_Tier_Explanation__c,
    model_version as Lead_Score_Model_Version__c,
    CAST(scored_at AS STRING) as Lead_Score_Updated__c
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_2_12212025`
WHERE score_tier != 'STANDARD'  -- Only sync priority tiers
ORDER BY priority_rank, lead_id;

