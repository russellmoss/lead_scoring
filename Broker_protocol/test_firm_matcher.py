"""
Test script for firm_matcher.py
Tests the firm matcher with sample data and validates matching logic.
"""

import pandas as pd
import sys
from pathlib import Path
import firm_matcher
import config

def test_single_firms():
    """
    Test matching for specific well-known firms.
    """
    print("=== TESTING SINGLE FIRM MATCHING ===\n")
    
    # Load FINTRX firms
    fintrx_path = config.get_fintrx_export_path()
    if not Path(fintrx_path).exists():
        print(f"ERROR: FINTRX firms file not found: {fintrx_path}")
        print("Run export_fintrx_firms.py first")
        sys.exit(1)
    
    fintrx_df = pd.read_csv(fintrx_path)
    fintrx_df['NAME_normalized'] = fintrx_df['NAME'].apply(firm_matcher.normalize_firm_name)
    fintrx_df['NAME_base'] = fintrx_df['NAME'].apply(firm_matcher.get_base_name)
    
    # Create bucket map for fuzzy matching
    fintrx_df['bucket1'] = fintrx_df['NAME_normalized'].str[:1].fillna('')
    bucket_map = {k: g for k, g in fintrx_df.groupby('bucket1')}
    
    # Test firms (well-known broker protocol members)
    test_firms = [
        "Morgan Stanley Wealth Management",
        "Merrill Lynch, Pierce, Fenner & Smith Incorporated",
        "Wells Fargo Advisors, LLC",
        "UBS Financial Services Inc. f/k/a UBS Wealth Management USA",
        "Raymond James & Associates, Inc.",
        "Edward Jones",
        "LPL Financial LLC"
    ]
    
    print("Testing matching for well-known firms:\n")
    
    for firm_name in test_firms:
        print(f"Testing: {firm_name}")
        result = firm_matcher.match_single_firm(firm_name, fintrx_df, confidence_threshold=0.60, bucket_map=bucket_map)
        
        print(f"  CRD ID: {result['firm_crd_id']}")
        print(f"  FINTRX Name: {result['fintrx_firm_name']}")
        print(f"  Confidence: {result['match_confidence']}")
        print(f"  Method: {result['match_method']}")
        print(f"  Needs Review: {result['needs_manual_review']}")
        print()
    
    print("=== SINGLE FIRM TESTING COMPLETE ===\n")


def test_batch_matching():
    """
    Test batch matching with sample broker protocol firms.
    """
    print("=== TESTING BATCH MATCHING ===\n")
    
    # Create sample broker protocol data
    sample_broker_firms = pd.DataFrame({
        'firm_name': [
            'Morgan Stanley Wealth Management',
            'Merrill Lynch, Pierce, Fenner & Smith Incorporated',
            'Wells Fargo Advisors, LLC',
            'Test Firm That Does Not Exist',
            'Raymond James & Associates, Inc.'
        ],
        'date_joined': pd.to_datetime(['2020-01-01', '2019-06-15', '2021-03-01', '2022-01-01', '2018-09-01']),
        'is_current_member': [True, True, True, True, True]
    })
    
    # Load FINTRX firms
    fintrx_path = config.get_fintrx_export_path()
    if not Path(fintrx_path).exists():
        print(f"ERROR: FINTRX firms file not found: {fintrx_path}")
        print("Run export_fintrx_firms.py first")
        sys.exit(1)
    
    fintrx_df = pd.read_csv(fintrx_path)
    
    print(f"Matching {len(sample_broker_firms)} sample firms to {len(fintrx_df)} FINTRX firms...\n")
    
    # Run batch matching
    matched_df = firm_matcher.batch_match_firms(
        sample_broker_firms,
        fintrx_df,
        confidence_threshold=0.60,
        verbose=True
    )
    
    print("\n=== BATCH MATCHING RESULTS ===")
    print(matched_df[['firm_name', 'firm_crd_id', 'fintrx_firm_name', 'match_method', 'match_confidence']].to_string())
    
    print("\n=== MATCHING STATISTICS ===")
    matched_count = matched_df['firm_crd_id'].notna().sum()
    match_rate = matched_count / len(matched_df) * 100
    print(f"Match rate: {matched_count}/{len(matched_df)} ({match_rate:.1f}%)")
    print(f"\nBy match method:")
    print(matched_df['match_method'].value_counts().to_string())
    
    print("\n=== BATCH MATCHING TEST COMPLETE ===\n")
    
    return matched_df


def test_name_normalization():
    """
    Test name normalization functions.
    """
    print("=== TESTING NAME NORMALIZATION ===\n")
    
    test_names = [
        "Morgan Stanley & Co. LLC",
        "Merrill Lynch, Pierce, Fenner & Smith Incorporated",
        "Wells Fargo Advisors, LLC",
        "Raymond James & Associates, Inc.",
        "Edward Jones"
    ]
    
    print("Testing normalize_firm_name():")
    for name in test_names:
        normalized = firm_matcher.normalize_firm_name(name)
        print(f"  '{name}' -> '{normalized}'")
    
    print("\nTesting get_base_name():")
    for name in test_names:
        base = firm_matcher.get_base_name(name)
        print(f"  '{name}' -> '{base}'")
    
    print("\n=== NAME NORMALIZATION TEST COMPLETE ===\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test firm matcher')
    parser.add_argument('--test', choices=['single', 'batch', 'normalization', 'all'], 
                       default='all', help='Which test to run')
    
    args = parser.parse_args()
    
    try:
        if args.test in ['single', 'all']:
            test_single_firms()
        
        if args.test in ['batch', 'all']:
            test_batch_matching()
        
        if args.test in ['normalization', 'all']:
            test_name_normalization()
        
        print("\n[SUCCESS] All tests completed")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

