"""
Validation script for broker_protocol_parser.py output
Run this after parsing an Excel file to validate the output quality.
"""

import pandas as pd
import sys
from pathlib import Path

def validate_parser_output(csv_path):
    """
    Validate the output from broker_protocol_parser.py
    
    Args:
        csv_path: Path to parsed CSV file
    """
    if not Path(csv_path).exists():
        print(f"ERROR: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    df = pd.read_csv(csv_path)
    
    print("=== PARSER OUTPUT VALIDATION ===")
    print(f"Total rows: {len(df)}")
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"\nSample rows:")
    print(df.head(10).to_string())
    
    print(f"\n=== DATA QUALITY ===")
    print(f"Firms with join dates: {df['date_joined'].notna().sum()} ({df['date_joined'].notna().sum()/len(df)*100:.1f}%)")
    print(f"Current members: {df['is_current_member'].sum()} ({df['is_current_member'].sum()/len(df)*100:.1f}%)")
    print(f"Withdrawn members: {(~df['is_current_member']).sum()}")
    print(f"Firms with name changes: {df['has_name_change'].sum()}")
    
    print(f"\n=== SAMPLE WITHDRAWN FIRMS ===")
    withdrawn = df[df['date_withdrawn'].notna()]
    if len(withdrawn) > 0:
        print(withdrawn[['firm_name', 'date_joined', 'date_withdrawn']].head(5).to_string())
    else:
        print("No withdrawn firms found")
    
    print(f"\n=== SAMPLE NAME CHANGES ===")
    name_changes = df[df['has_name_change']]
    if len(name_changes) > 0:
        print(name_changes[['firm_name', 'former_names', 'dbas']].head(5).to_string())
    else:
        print("No name changes found")
    
    print(f"\n=== DATE PARSING QUALITY ===")
    # Check for unparsed dates
    if 'date_notes_cleaned' in df.columns:
        unparsed = df[df['date_notes_cleaned'].notna() & df['date_joined'].isna()]
        print(f"Firms with date notes but no parsed join date: {len(unparsed)}")
        if len(unparsed) > 0:
            print("Sample unparsed dates:")
            print(unparsed[['firm_name', 'date_notes_raw', 'date_notes_cleaned']].head(5).to_string())
    
    print(f"\n=== VALIDATION SUMMARY ===")
    issues = []
    
    if len(df) < 2000:
        issues.append(f"WARNING: Only {len(df)} firms parsed (expected 2,500-3,000)")
    
    join_date_rate = df['date_joined'].notna().sum() / len(df) * 100
    if join_date_rate < 90:
        issues.append(f"WARNING: Only {join_date_rate:.1f}% have join dates (expected >90%)")
    
    if len(issues) > 0:
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("All validation checks passed!")
    
    return df


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate parser output')
    parser.add_argument('csv_file', help='Path to parsed CSV file')
    
    args = parser.parse_args()
    
    validate_parser_output(args.csv_file)

