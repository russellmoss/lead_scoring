"""
Validate matching results from firm_matcher.py
"""

import pandas as pd
import sys
from pathlib import Path

def validate_matching_results(csv_path):
    """
    Validate the matching results.
    
    Args:
        csv_path: Path to matched CSV file
    """
    if not Path(csv_path).exists():
        print(f"ERROR: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    df = pd.read_csv(csv_path)
    
    print("=== MATCHING RESULTS VALIDATION ===")
    print(f"Total firms: {len(df)}")
    
    matched_count = df['firm_crd_id'].notna().sum()
    match_rate = matched_count / len(df) * 100
    print(f"Match rate: {matched_count}/{len(df)} ({match_rate:.1f}%)")
    
    print(f"\n=== BY MATCH METHOD ===")
    print(df['match_method'].value_counts().to_string())
    
    print(f"\n=== CONFIDENCE DISTRIBUTION (MATCHED FIRMS) ===")
    matched = df[df['firm_crd_id'].notna()]
    if len(matched) > 0:
        print(matched['match_confidence'].describe().to_string())
    
    print(f"\n=== NEEDS REVIEW ===")
    needs_review = df['needs_manual_review'].sum()
    print(f"Needs manual review: {needs_review} ({needs_review/len(df)*100:.1f}%)")
    
    print(f"\n=== SAMPLE EXACT MATCHES ===")
    exact = df[df['match_method'] == 'exact']
    if len(exact) > 0:
        print(exact[['firm_name', 'fintrx_firm_name', 'match_confidence']].head(5).to_string())
    
    print(f"\n=== SAMPLE FUZZY MATCHES (GOOD) ===")
    fuzzy_good = df[(df['match_method'] == 'fuzzy') & (df['match_confidence'] >= 0.80)]
    if len(fuzzy_good) > 0:
        print(fuzzy_good[['firm_name', 'fintrx_firm_name', 'match_confidence']].head(5).to_string())
    
    print(f"\n=== SAMPLE FUZZY MATCHES (NEEDS REVIEW) ===")
    fuzzy_review = df[(df['match_method'] == 'fuzzy') & (df['match_confidence'] < 0.80)]
    if len(fuzzy_review) > 0:
        print(fuzzy_review[['firm_name', 'fintrx_firm_name', 'match_confidence']].head(5).to_string())
    
    print(f"\n=== UNMATCHED FIRMS ===")
    unmatched = df[df['firm_crd_id'].isna()]
    if len(unmatched) > 0:
        print(f"Total unmatched: {len(unmatched)}")
        print(unmatched[['firm_name', 'date_joined', 'is_current_member']].head(10).to_string())
    
    print(f"\n=== VALIDATION SUMMARY ===")
    if match_rate >= 70:
        print(f"[SUCCESS] Match rate {match_rate:.1f}% exceeds 70% threshold")
    else:
        print(f"[WARNING] Match rate {match_rate:.1f}% is below 70% threshold")
    
    if match_rate >= 90:
        print(f"[EXCELLENT] Match rate {match_rate:.1f}% exceeds 90% threshold")
    
    return df


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate matching results')
    parser.add_argument('csv_file', help='Path to matched CSV file')
    
    args = parser.parse_args()
    
    validate_matching_results(args.csv_file)

