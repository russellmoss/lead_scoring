-- Step 3.2 helper: Add and backfill snapshot_as_of for discovery reps

-- 1) Add column (idempotent)
ALTER TABLE `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
ADD COLUMN IF NOT EXISTS snapshot_as_of DATE;

-- 2) Backfill with best available proxy
-- NOTE: Using DATE(processed_at) as a placeholder until vendor/vintage dates are available
UPDATE `savvy-gtm-analytics.LeadScoring.discovery_reps_current`
SET snapshot_as_of = DATE(processed_at)
WHERE snapshot_as_of IS NULL;

-- 3) (Optional) Replace with true feature vintage when available
-- UPDATE `savvy-gtm-analytics.LeadScoring.discovery_reps_current` d
-- SET snapshot_as_of = src.true_vintage_date
-- FROM `savvy-gtm-analytics.LeadScoring.discovery_feature_vintages` src
-- WHERE d.RepCRD = src.RepCRD;

