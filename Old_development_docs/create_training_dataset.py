"""
Create the full training dataset by executing the FinalDatasetCreation CTE
This reads the schema and generates complete SQL with all 124 features
"""
import json
from pathlib import Path

def build_complete_sql():
    """Build the complete SQL query with all features"""
    schema_path = Path("config/v1_feature_schema.json")
    
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    
    stable_features = [f["name"] for f in schema["features"] if not f.get("is_mutable", True)]
    mutable_features = [f["name"] for f in schema["features"] if f.get("is_mutable", True)]
    
    # Build SQL
    sql = f"""-- Create Hybrid Training Dataset with all {len(stable_features) + len(mutable_features)} features

CREATE OR REPLACE TABLE `savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_hybrid` AS

WITH

AllLeadsWithSnapshot AS (
    SELECT 
        sf.Id,
        sf.Stage_Entered_Contacting__c,
        sf.Stage_Entered_Call_Scheduled__c,
        drc.snapshot_as_of,
        CASE 
            WHEN DATE(sf.Stage_Entered_Contacting__c) >= drc.snapshot_as_of
            THEN 1 ELSE 0 
        END as is_eligible_for_mutable_features,
        
        -- Stable Features (always OK to use):"""
    
    for feat in sorted(stable_features):
        sql += f"\n        drc.{feat},"
    
    sql += "\n        \n        -- Mutable Features (will be NULLed for historical leads):"
    
    for feat in sorted(mutable_features):
        sql += f"\n        drc.{feat},"
    
    sql = sql.rstrip(",")  # Remove last comma
    
    sql += """
        
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
        Id,
        Stage_Entered_Contacting__c,
        target_label,
        is_eligible_for_mutable_features,
        
        -- Temporal features (derived):
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c) = 1 THEN 7
            ELSE EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c) - 1
        END as Day_of_Contact,
        CASE 
            WHEN EXTRACT(DAYOFWEEK FROM Stage_Entered_Contacting__c) IN (1, 7) THEN 1
            ELSE 0 
        END as Is_Weekend_Contact,
        
        -- Stable Features (pass-through):"""
    
    for i, feat in enumerate(sorted(stable_features)):
        comma = "," if i < len(stable_features) - 1 or len(mutable_features) > 0 else ""
        sql += f"\n        {feat}{comma}"
    
    sql += "\n        \n        -- Mutable Features (with CASE WHEN):"
    
    for i, feat in enumerate(sorted(mutable_features)):
        comma = "," if i < len(mutable_features) - 1 else ""
        sql += f"""\n        CASE 
            WHEN is_eligible_for_mutable_features = 1 THEN {feat} 
            ELSE NULL 
        END as {feat}{comma}"""
    
    sql += """
        
    FROM LabelData
    WHERE is_in_right_censored_window = 0
      AND (days_to_conversion >= 0 OR days_to_conversion IS NULL)
)

SELECT * FROM FinalDatasetCreation;"""
    
    return sql

if __name__ == "__main__":
    sql = build_complete_sql()
    
    # Save to file
    output_path = Path("create_training_dataset_full.sql")
    with output_path.open("w", encoding="utf-8") as f:
        f.write(sql)
    
    print(f"Complete SQL generated: {output_path}")
    print(f"   Ready to execute via BigQuery MCP or BigQuery console")
    print(f"   Will create table: savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_hybrid")

