"""
Generate the complete Hybrid (Stable/Mutable) SQL query for Step 3.3
Uses discovery_reps_current (which has all features + snapshot_as_of) 
and optionally discovery_firms_current for firm-level features
"""
import json
from pathlib import Path

def get_columns_from_table(table_name):
    """Helper to get column list - we'll use schema file instead"""
    pass

def generate_sql():
    schema_path = Path("config/v1_feature_schema.json")
    
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    
    # Separate features by mutable status
    stable_features = [f["name"] for f in schema["features"] if not f.get("is_mutable", True)]
    mutable_features = [f["name"] for f in schema["features"] if f.get("is_mutable", True)]
    
    # Add temporal features (stable) that will be derived during Week 4
    temporal_stable = ["Day_of_Contact", "Is_Weekend_Contact"]
    all_stable = stable_features + temporal_stable
    
    print(f"Stable features: {len(all_stable)}")
    print(f"Mutable features: {len(mutable_features)}")
    print(f"Total: {len(all_stable) + len(mutable_features)}")
    
    # Generate SQL
    sql_parts = []
    
    # CTE 1: AllLeadsWithSnapshot
    sql_parts.append("-- Week 3 Validation Checkpoint 3.3: Build \"Hybrid (Stable/Mutable)\" Training Set & Validate\n")
    sql_parts.append("-- Uses discovery_reps_current (has all features + snapshot_as_of)\n")
    sql_parts.append("-- Optionally includes discovery_firms_current for firm-level features\n\n")
    sql_parts.append("WITH\n\n-- CTE 1: Join all leads to the (current) snapshot\nAllLeadsWithSnapshot AS (\n    SELECT \n        sf.*,\n        drc.snapshot_as_of,\n        -- This is the core policy flag\n        CASE \n            WHEN DATE(sf.Stage_Entered_Contacting__c) >= drc.snapshot_as_of\n            THEN 1 ELSE 0 \n        END as is_eligible_for_mutable_features,")
    
    # Add all stable features (direct selection from discovery_reps_current)
    sql_parts.append("        \n        -- Stable Features (always OK to use):")
    for feat in sorted(all_stable):
        sql_parts.append(f"        drc.{feat},")
    
    # Add all mutable features (will be NULLed later)
    sql_parts.append("        \n        -- Mutable Features (will be NULLed for historical leads):")
    for feat in sorted(mutable_features):
        sql_parts.append(f"        drc.{feat},")
    
    # Optional: Add firm-level features (all would be mutable since they're aggregated firm metrics)
    # For now, we'll skip firm features to keep it simple, but can add later
    sql_parts.append("        \n        -- Firm-level features (optional - uncomment if needed):\n")
    sql_parts.append("        -- dfc.total_firm_aum_millions as Firm_TotalAUM,\n")
    sql_parts.append("        -- dfc.avg_rep_aum_millions as Firm_AvgRepAUM,\n")
    sql_parts.append("        -- ... (add firm features as needed)\n")
    
    # Complete CTE 1
    sql_parts[-4] = sql_parts[-4].rstrip(",")  # Remove trailing comma from last feature
    sql_parts.append("        \n    FROM `savvy-gtm-analytics.SavvyGTMData.Lead` sf\n    LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc\n        ON sf.FA_CRD__c = drc.RepCRD\n    -- Optional: Join firm-level features\n    -- LEFT JOIN `savvy-gtm-analytics.LeadScoring.discovery_firms_current` dfc\n    --     ON drc.RIAFirmCRD = dfc.RIAFirmCRD\n    WHERE sf.Stage_Entered_Contacting__c IS NOT NULL\n),")
    
    # CTE 2: LabelData
    sql_parts.append("\n-- CTE 2: Apply Labels and Integrity Checks\nLabelData AS (\n    SELECT \n        s.*,\n        CASE \n            WHEN s.Stage_Entered_Call_Scheduled__c IS NOT NULL \n            AND DATE(s.Stage_Entered_Call_Scheduled__c) <= DATE_ADD(DATE(s.Stage_Entered_Contacting__c), INTERVAL 30 DAY)\n            THEN 1 \n            ELSE 0 \n        END as target_label,\n        -- Check for right-censored window (last 30 days)\n        CASE \n            WHEN DATE(s.Stage_Entered_Contacting__c) > DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)\n            THEN 1\n            ELSE 0\n        END as is_in_right_censored_window,\n        -- Check for negative conversion times\n        DATE_DIFF(DATE(s.Stage_Entered_Call_Scheduled__c), DATE(s.Stage_Entered_Contacting__c), DAY) as days_to_conversion\n    FROM AllLeadsWithSnapshot s\n),")
    
    # CTE 3: IntegrityAssertions
    sql_parts.append("\n-- CTE 3: Run Label Integrity Assertions\nIntegrityAssertions AS (\n    SELECT\n        COUNT(CASE WHEN days_to_conversion < 0 THEN 1 END) as negative_days_to_conversion,\n        COUNT(CASE WHEN is_in_right_censored_window = 1 AND target_label = 1 THEN 1 END) as labels_in_right_censored_window\n    FROM LabelData\n),")
    
    # CTE 4: FinalDatasetCreation (this is the complex one)
    sql_parts.append("\n-- CTE 4: Define the Final, Filtered, Hybrid Dataset\n-- This is where we NULL-out future data to prevent leakage\nFinalDatasetCreation AS (\n    SELECT \n        Id,\n        Stage_Entered_Contacting__c,\n        target_label,\n        is_in_right_censored_window,\n        days_to_conversion,\n        is_eligible_for_mutable_features,")
    
    # Add stable features (direct pass-through)
    sql_parts.append("        \n        -- Stable Features (Always OK to use for all leads):")
    for feat in sorted(all_stable):
        sql_parts.append(f"        {feat},")
    
    # Add mutable features (with CASE WHEN)
    sql_parts.append("        \n        -- Mutable Features (NULLed for historical leads to prevent leakage):")
    for feat in sorted(mutable_features):
        sql_parts.append(f"        CASE \n            WHEN is_eligible_for_mutable_features = 1 THEN {feat} \n            ELSE NULL \n        END as {feat},")
    
    sql_parts[-1] = sql_parts[-1].rstrip(",")  # Remove trailing comma
    
    sql_parts.append("        \n    FROM LabelData\n    WHERE is_in_right_censored_window = 0\n      AND (days_to_conversion >= 0 OR days_to_conversion IS NULL)\n),")
    
    # CTE 5: ImbalanceMetrics
    sql_parts.append("\n-- CTE 5: Calculate Final Imbalance Metrics\nImbalanceMetrics AS (\n    SELECT \n        'Class Imbalance Metrics (Hybrid)' as metric_type,\n        COUNT(*) as total_samples, -- This will now be ~40k+\n        COUNT(CASE WHEN target_label = 1 THEN 1 END) as positive_samples,\n        COUNT(CASE WHEN target_label = 0 THEN 1 END) as negative_samples,\n        ROUND(COUNT(CASE WHEN target_label = 1 THEN 1 END) / COUNT(*) * 100, 2) as positive_class_percent,\n        ROUND(COUNT(CASE WHEN target_label = 0 THEN 1 END) / COUNT(CASE WHEN target_label = 1 THEN 1 END), 2) as imbalance_ratio\n    FROM FinalDatasetCreation\n)\n\n-- Run all queries. The AGENTIC TASK will use these CTEs.\n-- First, check assertions:\nSELECT * FROM IntegrityAssertions;\n-- Then, get metrics for the report:\nSELECT * FROM ImbalanceMetrics;\n-- Finally, create the dataset (the agent will run this query separately):\n-- SELECT * FROM FinalDatasetCreation;")
    
    sql = "\n".join(sql_parts)
    
    # Write to file
    output_path = Path("Step_3_3_Hybrid_Training_Set.sql")
    with output_path.open("w", encoding="utf-8") as f:
        f.write(sql)
    
    print(f"\nSQL query generated: {output_path}")
    print(f"Total features handled: {len(all_stable) + len(mutable_features)}")
    print(f"  - Stable: {len(all_stable)}")
    print(f"  - Mutable: {len(mutable_features)}")
    print(f"\nNOTE: Uses discovery_reps_current directly (has snapshot_as_of + all features)")
    print(f"      Firm-level features from discovery_firms_current are commented out (can add if needed)")
    
    return sql

if __name__ == "__main__":
    generate_sql()

