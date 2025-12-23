#!/usr/bin/env python3
"""
Generate Step 3.3 V2 SQL with 3-part temporal logic: stable, calculable, mutable
"""

import json

# Load schema
with open('config/v1_feature_schema.json', 'r') as f:
    schema = json.load(f)

# Categorize features
stable_features = []
calculable_features = []
mutable_features = []

for feature in schema['features']:
    name = feature['name']
    temp_type = feature.get('temporal_type', 'mutable')
    
    if temp_type == 'stable':
        stable_features.append(name)
    elif temp_type == 'calculable':
        calculable_features.append(name)
    else:
        mutable_features.append(name)

# Generate SQL
sql_parts = []

# Stable features section
sql_parts.append("        -- 1. Stable Features (Pass-through - never change)")
for feat in sorted(stable_features):
    sql_parts.append(f"        {feat},")

sql_parts.append("")
sql_parts.append("        -- 2. Calculable Features (Re-calculate point-in-time value)")
sql_parts.append("        -- Calculate years at contact time by subtracting years elapsed since snapshot")
for feat in sorted(calculable_features):
    if 'Date' in feat and 'Years' in feat:
        # For date-based tenure features, subtract years elapsed
        sql_parts.append(f"        drc.{feat} - DATE_DIFF(CURRENT_DATE(), DATE(sf.Stage_Entered_Contacting__c), YEAR) as {feat},")
    else:
        # For other calculable features (like Total_Prior_Firm_Years), they're stable enough
        sql_parts.append(f"        drc.{feat},")

sql_parts.append("")
sql_parts.append("        -- 3. Mutable Features (NULLed for historical leads)")
for feat in sorted(mutable_features):
    sql_parts.append(f"        CASE")
    sql_parts.append(f"            WHEN is_eligible_for_mutable_features = 1 THEN drc.{feat}")
    sql_parts.append(f"            ELSE NULL")
    sql_parts.append(f"        END as {feat},")

# Join the SQL parts
final_sql = "\n".join(sql_parts)

# Write to file
with open('Step_3_3_V2_FinalDatasetCreation.sql', 'w') as f:
    f.write("-- FinalDatasetCreation CTE for V2 (3-part temporal logic)\n\n")
    f.write("FinalDatasetCreation AS (\n")
    f.write("    SELECT \n")
    f.write("        ld.Id,\n")
    f.write("        ld.target_label,\n")
    f.write("        ld.is_in_right_censored_window,\n")
    f.write("        ld.days_to_conversion,\n")
    f.write("        \n")
    f.write("        -- Temporal features (derived):\n")
    f.write("        CASE \n")
    f.write("            WHEN EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) = 1 THEN 7\n")
    f.write("            ELSE EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) - 1\n")
    f.write("        END as Day_of_Contact,\n")
    f.write("        CASE \n")
    f.write("            WHEN EXTRACT(DAYOFWEEK FROM ld.Stage_Entered_Contacting__c) IN (1, 7) THEN 1\n")
    f.write("            ELSE 0 \n")
    f.write("        END as Is_Weekend_Contact,\n")
    f.write("        \n")
    f.write(final_sql)
    f.write("\n")
    f.write("        \n")
    f.write("    FROM LabelData ld\n")
    f.write("    JOIN `savvy-gtm-analytics.LeadScoring.discovery_reps_current` drc ON ld.FA_CRD__c = drc.RepCRD\n")
    f.write("    JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` sf ON ld.Id = sf.Id\n")
    f.write("    WHERE ld.is_in_right_censored_window = 0\n")
    f.write("      AND (ld.days_to_conversion >= 0 OR ld.days_to_conversion IS NULL)\n")
    f.write(")\n")

print("SQL generated successfully!")
print(f"   - Stable features: {len(stable_features)}")
print(f"   - Calculable features: {len(calculable_features)}")
print(f"   - Mutable features: {len(mutable_features)}")
print("\nSQL written to: Step_3_3_V2_FinalDatasetCreation.sql")

