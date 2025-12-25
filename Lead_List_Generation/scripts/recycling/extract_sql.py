"""Extract SQL from guide and save to file."""
from pathlib import Path

guide_file = Path(__file__).parent.parent.parent / "Monthly_Recyclable_Lead_List_Generation_Guide_V2.md"
sql_file = Path(__file__).parent.parent.parent / "sql" / "recycling" / "recyclable_pool_master_v2.1.sql"

# Ensure directory exists
sql_file.parent.mkdir(parents=True, exist_ok=True)

# Read guide
with open(guide_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract SQL (lines 92-714, removing markdown markers at 91 and 715)
sql_lines = []
in_sql_block = False
for i, line in enumerate(lines, start=1):
    if i == 91 and line.strip() == '```sql':
        in_sql_block = True
        continue
    elif i == 715 and line.strip() == '```':
        break
    elif in_sql_block:
        sql_lines.append(line)

# Write SQL file
with open(sql_file, 'w', encoding='utf-8') as f:
    f.writelines(sql_lines)

print(f"SQL extracted to: {sql_file}")
print(f"Lines written: {len(sql_lines)}")



