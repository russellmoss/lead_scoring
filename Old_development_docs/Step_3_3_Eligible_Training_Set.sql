-- Step 3.3: Build Eligible-Only Training Dataset & Validate

-- Materialize training dataset (eligible-only) using discovery_reps_current as feature source
CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset` AS
WITH
EligibleCohort AS (
  SELECT 
    sf.*,
    dd.snapshot_as_of
  FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
  JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` dd 
    ON sf.FA_CRD__c = dd.RepCRD
  WHERE DATE(sf.Stage_Entered_Contacting__c) >= dd.snapshot_as_of
),
LabelData AS (
  SELECT 
    ec.Id,
    ec.FA_CRD__c,
    ec.Stage_Entered_Contacting__c,
    ec.Stage_Entered_Call_Scheduled__c,
    CASE 
      WHEN ec.Stage_Entered_Call_Scheduled__c IS NOT NULL 
       AND DATE(ec.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(ec.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
      THEN 1 ELSE 0 
    END AS target_label,
    CASE WHEN DATE(ec.Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END AS is_in_right_censored_window
  FROM EligibleCohort ec
),
FinalDatasetCreation AS (
  SELECT *
  FROM LabelData
  WHERE is_in_right_censored_window = 0
)
SELECT 
  fdc.Id,
  fdc.FA_CRD__c,
  fdc.Stage_Entered_Contacting__c,
  fdc.Stage_Entered_Call_Scheduled__c,
  fdc.target_label,
  dd_cur.* EXCEPT(RepCRD, processed_at, snapshot_as_of)
FROM FinalDatasetCreation fdc
LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` dd_cur
  ON fdc.FA_CRD__c = dd_cur.RepCRD;

-- Assertions & Metrics
WITH 
LabelData AS (
  SELECT 
    Id,
    Stage_Entered_Contacting__c,
    Stage_Entered_Call_Scheduled__c,
    target_label,
    DATE_DIFF(DATE(Stage_Entered_Call_Scheduled__c), DATE(Stage_Entered_Contacting__c), DAY) AS days_to_conversion,
    CASE WHEN DATE(Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN 1 ELSE 0 END AS is_in_right_censored_window
  FROM `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset`
)
SELECT 
  (SELECT COUNT(*) FROM LabelData) AS total_samples,
  (SELECT COUNT(*) FROM LabelData WHERE target_label = 1) AS positive_samples,
  (SELECT COUNT(*) FROM LabelData WHERE target_label = 0) AS negative_samples,
  (SELECT COUNT(*) FROM LabelData WHERE days_to_conversion < 0) AS negative_days_to_conversion,
  (SELECT COUNT(*) FROM LabelData WHERE is_in_right_censored_window = 1 AND target_label = 1) AS labels_in_right_censored_window;
