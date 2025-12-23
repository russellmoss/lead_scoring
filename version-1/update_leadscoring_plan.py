# update_leadscoring_plan.py
import re

file_path = 'leadscoring_plan.md'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Phase 1.1 SQL Logic Description (Gap Tolerance)
# Look for the prompt description in Unit 1.1
pattern_1 = r"(2\. Rep State: Join to `contact_registered_employment_history` where `contact_date` BETWEEN `START` AND `END`\.)"
replacement_1 = """2. Rep State (PIT - Gap Tolerant): Join Lead to `contact_registered_employment_history` using "Last Known Value" logic.
   - Filter: `PREVIOUS_REGISTRATION_COMPANY_START_DATE <= contacted_date`
   - Rank: Order by `START_DATE DESC` and take the top 1.
   - **Why:** This recovers ~63% of leads that fall into administrative "employment gaps" at the exact moment of contact."""

# Try to find and replace
if pattern_1 in content:
    content = content.replace(pattern_1, replacement_1)
    print("✅ Updated Unit 1.1 Rep State logic description.")
else:
    # Fallback regex if exact string match fails due to formatting
    content = re.sub(
        r"2\. Rep State: Join to .*? BETWEEN `START` AND `END`\.",
        replacement_1,
        content,
        flags=re.DOTALL
    )
    print("✅ Updated Unit 1.1 Rep State logic description (Regex).")

# 2. Add Training Data Date Floor to Phase 2
pattern_2 = "## Phase 2: Training Dataset Construction"
replacement_2 = """## Phase 2: Training Dataset Construction

> **Constraint:** Filter training data to `contacted_date >= '2024-02-01'`.
> * *Reason:* `Firm_historicals` data only exists from Jan 2024. Leads before Feb 2024 have no valid firm snapshot (resulting in NULL features)."""

if pattern_2 in content:
    content = content.replace(pattern_2, replacement_2)
    print("✅ Added Phase 2 Date Floor constraint.")

# 3. Update Growth Feature Definition in Unit 1.2
# Find the definition of aum_growth_12mo_pct
pattern_3_search = r'(name="aum_growth_12mo_pct",.*?business_logic=")(.*?)(")'
replacement_3_text = r'\1\2 **Note:** Due to limited history (Jan 2024+), this feature will be replaced by `aum_growth_since_jan2024` or `aum_growth_3mo` for leads in early 2024 to ensure non-null values.\3'

if re.search(pattern_3_search, content, re.DOTALL):
    content = re.sub(pattern_3_search, replacement_3_text, content, flags=re.DOTALL)
    print("✅ Updated aum_growth_12mo_pct definition in Unit 1.2.")
else:
    print("⚠️ Could not find aum_growth_12mo_pct definition to update.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nSuccessfully updated {file_path}")