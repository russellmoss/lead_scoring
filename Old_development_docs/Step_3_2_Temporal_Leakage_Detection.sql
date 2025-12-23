-- Step 3.2: Temporal Leakage Detection

-- Assert data types (manually verified via INFORMATION_SCHEMA):
-- Lead.Stage_Entered_Contacting__c: TIMESTAMP
-- LeadScoring.discovery_reps_current.processed_at: TIMESTAMP

-- Aggregate leakage metrics (using discovery_reps_current)
SELECT 
  'Future Data Leakage Check' as validation_type,
  COUNT(*) as total_records,
  COUNT(dd.RepCRD) as matched_records,
  COUNT(CASE WHEN COALESCE(TIMESTAMP(dd.snapshot_as_of), dd.processed_at) > sf.Stage_Entered_Contacting__c THEN 1 END) as leakage_records_overall,
  ROUND(COUNT(CASE WHEN COALESCE(TIMESTAMP(dd.snapshot_as_of), dd.processed_at) > sf.Stage_Entered_Contacting__c THEN 1 END) / COUNT(*) * 100, 2) as leakage_rate_percent_overall,
  COUNT(CASE WHEN dd.RepCRD IS NOT NULL AND COALESCE(TIMESTAMP(dd.snapshot_as_of), dd.processed_at) > sf.Stage_Entered_Contacting__c THEN 1 END) as leakage_records_matched,
  ROUND(COUNT(CASE WHEN dd.RepCRD IS NOT NULL AND COALESCE(TIMESTAMP(dd.snapshot_as_of), dd.processed_at) > sf.Stage_Entered_Contacting__c THEN 1 END) / NULLIF(COUNT(dd.RepCRD), 0) * 100, 2) as leakage_rate_percent_matched
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` dd 
  ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL;

-- Example leakage records
SELECT 
  sf.Id as lead_id,
  sf.FA_CRD__c as lead_crd,
  sf.Stage_Entered_Contacting__c as contacted_ts,
  COALESCE(TIMESTAMP(dd.snapshot_as_of), dd.processed_at) as discovery_as_of_ts,
  dd.RepCRD
FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` dd 
  ON sf.FA_CRD__c = dd.RepCRD
WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
  AND dd.RepCRD IS NOT NULL
  AND COALESCE(TIMESTAMP(dd.snapshot_as_of), dd.processed_at) > sf.Stage_Entered_Contacting__c
ORDER BY COALESCE(TIMESTAMP(dd.snapshot_as_of), dd.processed_at) - sf.Stage_Entered_Contacting__c DESC
LIMIT 25;

