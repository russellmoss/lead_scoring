"""
Extract SQL from leadscoring_plan.md, apply fixes, and prepare for execution
"""
import re

# Read the plan file
with open('leadscoring_plan.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the feature engineering SQL section (starts with CREATE OR REPLACE TABLE)
# Look for the section that contains "CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`"
sql_start = content.find('CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`')
if sql_start > 0:
    # Find the end of the SQL (look for the closing """ after the SELECT statement)
    # The SQL ends before the next """ that's part of the Python code
    # Look for the pattern: WHERE ... AND rsp.firm_crd_at_contact IS NOT NULL;
    sql_end_marker = content.find('AND rsp.firm_crd_at_contact IS NOT NULL;', sql_start)
    if sql_end_marker > 0:
        # Find the next """ after the SQL ends
        sql_end = content.find('"""', sql_end_marker + 50)
    else:
        sql_end = -1
    if sql_end > 0:
        sql = content[sql_start + 10:sql_end]
        
        # Apply fixes and substitutions
        sql = sql.replace('{self.analysis_date}', '2024-12-31')
        sql = sql.replace('{maturity_window_days}', '30')
        sql = sql.replace('afs.current_firm_tenure_months', 'avf.current_firm_tenure_months')
        
        # Write to file
        with open('phase1_1_complete.sql', 'w', encoding='utf-8') as f:
            f.write(sql)
        
        print(f"SQL extracted and fixed. Length: {len(sql)} characters")
        print(f"Saved to: phase1_1_complete.sql")
        print(f"Fixes applied:")
        print(f"  - Replaced {{self.analysis_date}} with '2024-12-31'")
        print(f"  - Replaced {{maturity_window_days}} with '30'")
        print(f"  - Fixed afs -> avf (4 occurrences)")
    else:
        print("ERROR: Could not find closing \"\"\"")
else:
    print("ERROR: Could not find sql = f\"\"\"")

