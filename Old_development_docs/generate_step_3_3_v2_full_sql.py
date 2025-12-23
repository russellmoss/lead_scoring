#!/usr/bin/env python3
"""
Generate complete Step 3.3 V2 SQL with 3-part temporal logic: stable, calculable, mutable
Creates the full CREATE TABLE statement with all CTEs
"""

import json

# Load schema
with open('config/v1_feature_schema.json', 'r') as f:
    schema = json.load(f)

# Categorize features
stable_features = []
calculable_features = []
mutable_features = []

exclusions = set(schema.get('exclusions', []))

for feature in schema['features']:
    name = feature['name']
    if name in exclusions:
        continue
        
    temp_type = feature.get('temporal_type', 'mutable')
    
    if temp_type == 'stable':
        stable_features.append(name)
    elif temp_type == 'calculable':
        calculable_features.append(name)
    else:
        mutable_features.append(name)

print(f"Categorizing features:")
print(f"   - Stable: {len(stable_features)}")
print(f"   - Calculable: {len(calculable_features)}")
print(f"   - Mutable: {len(mutable_features)}")

# Generate SQL parts for FinalDatasetCreation
stable_sql = []
for feat in sorted(stable_features):
    stable_sql.append(f"        drc.{feat},")

calculable_sql = []
for feat in sorted(calculable_features):
    if 'Date' in feat and 'Years' in feat:
        calculable_sql.append(f"        drc.{feat} - DATE_DIFF(CURRENT_DATE(), DATE(sf.Stage_Entered_Contacting__c), YEAR) as {feat},")
    else:
        calculable_sql.append(f"        drc.{feat},")

mutable_sql = []
for feat in sorted(mutable_features):
    mutable_sql.append(f"        CASE")
    mutable_sql.append(f"            WHEN ld.is_eligible_for_mutable_features = 1 THEN drc.{feat}")
    mutable_sql.append(f"            ELSE NULL")
    mutable_sql.append(f"        END as {feat},")

# Generate AllLeadsWithSnapshot CTE - select all features explicitly
all_features_sql = []
for feat in sorted(stable_features + calculable_features + mutable_features):
    all_features_sql.append(f"        drc.{feat},")

# Write complete SQL
sql_content = f"""-- Create Hybrid V2 Training Dataset with 3-part temporal logic (Stable, Calculable, Mutable)
-- This implements the V2 strategy: stable features always available, calculable features recalculated, mutable features NULLed for historical leads

CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2` AS

WITH

AllLeadsWithSnapshot AS (
    SELECT 
        sf.Id,
        sf.FA_CRD__c,
        sf.Stage_Entered_Contacting__c,
        sf.Stage_Entered_Call_Scheduled__c,
        drc.snapshot_as_of,
        CASE 
            WHEN DATE(sf.Stage_Entered_Contacting__c) >= drc.snapshot_as_of
            THEN 1 ELSE 0 
        END as is_eligible_for_mutable_features,
        
{chr(10).join(all_features_sql).rstrip(',')}
        
    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf
    LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc
        ON sf.FA_CRD__c = drc.RepCRD
    WHERE sf.Stage_Entered_Contacting__c IS NOT NULL
),

LabelData AS (
    SELECT 
        s.*,
        CASE 
            WHEN s.Stage_Entered_Call_Scheduled__c IS NOT NULL 
            AND DATE(s.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(s.Stage_Entered_Contacting__c), INTERVAL 30 DAY)
            THEN 1 
            ELSE 0 
        END as target_label,
        CASE 
            WHEN DATE(s.Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            THEN 1
            ELSE 0
        END as is_in_right_censored_window,
        DATE_DIFF(DATE(s.Stage_Entered_Call_Scheduled__c), DATE(s.Stage_Entered_Contacting__c), DAY) as days_to_conversion
    FROM AllLeadsWithSnapshot s
),

FinalDatasetCreation AS (
    SELECT 
        ld.Id,
        ld.target_label,
        ld.is_in_right_censored_window,
        ld.days_to_conversion,
        ld.FA_CRD__c,
        ld.Stage_Entered_Contacting__c,
        ld.is_eligible_for_mutable_features,
        
        -- Temporal features (derived):
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) = 1 THEN 7
            ELSE EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) - 1
        END as Day_of_Contact,
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) IN (1, 7) THEN 1
            ELSE 0 
        END as Is_Weekend_Contact,
        
        -- 1. Stable Features (Pass-through - never change)
{chr(10).join(stable_sql).rstrip(',')}

        -- 2. Calculable Features (Re-calculate point-in-time value)
        -- Calculate years at contact time by subtracting years elapsed since snapshot
{chr(10).join(calculable_sql).rstrip(',')}

        -- 3. Mutable Features (NULLed for historical leads)
{chr(10).join(mutable_sql).rstrip(',')}
        
    FROM LabelData ld
    JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc ON ld.FA_CRD__c = drc.RepCRD
    JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` sf ON ld.Id = sf.Id
    WHERE ld.is_in_right_censored_window = 0
      AND (ld.days_to_conversion >= 0 OR ld.days_to_conversion IS NULL)
)

SELECT * FROM FinalDatasetCreation;
"""

# Write to file
with open('create_training_dataset_v2_full.sql', 'w', encoding='utf-8') as f:
    f.write(sql_content)

print("\nSQL generated successfully!")
print(f"   - Stable features: {len(stable_features)}")
print(f"   - Calculable features: {len(calculable_features)}")
print(f"   - Mutable features: {len(mutable_features)}")
print(f"\nComplete SQL written to: create_training_dataset_v2_full.sql")

