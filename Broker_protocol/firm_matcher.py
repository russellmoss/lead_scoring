"""
Firm Matcher
Matches Broker Protocol firms to FINTRX CRD IDs using multiple matching strategies.
"""

import pandas as pd
import re
import sys
import argparse
from difflib import SequenceMatcher
from pathlib import Path
import config

# Try to use RapidFuzz for faster fuzzy matching, fallback to difflib
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


def normalize_firm_name(name):
    """
    Normalize firm name for matching:
    - Convert to lowercase
    - Remove punctuation
    - Standardize whitespace
    - Remove common suffixes variations
    """
    if pd.isna(name):
        return None
    
    name_str = str(name).strip()
    
    # Convert to lowercase
    name_str = name_str.lower()
    
    # Remove common punctuation
    name_str = re.sub(r'[.,;:!?\'"()\[\]{}]', '', name_str)
    
    # Standardize whitespace
    name_str = ' '.join(name_str.split())
    
    return name_str


def get_base_name(name):
    """
    Extract base name by removing entity suffixes (LLC, Inc, Corp, etc.)
    """
    if pd.isna(name):
        return None
    
    name_str = normalize_firm_name(name)
    
    # Common entity suffixes
    suffixes = [
        r'\s+llc\s*$',
        r'\s+l\.l\.c\.\s*$',
        r'\s+inc\s*$',
        r'\s+inc\.\s*$',
        r'\s+incorporated\s*$',
        r'\s+corp\s*$',
        r'\s+corp\.\s*$',
        r'\s+corporation\s*$',
        r'\s+ltd\s*$',
        r'\s+ltd\.\s*$',
        r'\s+limited\s*$',
        r'\s+lp\s*$',
        r'\s+l\.p\.\s*$',
        r'\s+llp\s*$',
        r'\s+l\.l\.p\.\s*$',
        r'\s+pc\s*$',
        r'\s+p\.c\.\s*$',
        r'\s+pa\s*$',
        r'\s+p\.a\.\s*$',
        r'\s+plc\s*$',
        r'\s+p\.l\.c\.\s*$',
    ]
    
    for suffix in suffixes:
        name_str = re.sub(suffix, '', name_str, flags=re.IGNORECASE)
    
    return name_str.strip()


def parse_name_variants(broker_row):
    """
    Parse name variants from broker protocol row (firm_name, former_names, dbas).
    
    Args:
        broker_row: Dict or Series with broker protocol firm data
        
    Returns:
        List of (variant_name, variant_type) tuples where variant_type is 
        'firm_name', 'former_name', or 'dba'
    """
    variants = []
    
    # Main firm name
    if pd.notna(broker_row.get('firm_name')):
        variants.append((str(broker_row['firm_name']), 'firm_name'))
    
    # Former names (comma-separated)
    if pd.notna(broker_row.get('former_names')):
        former_names = str(broker_row['former_names']).split(',')
        for name in former_names:
            name = name.strip()
            if name:
                variants.append((name, 'former_name'))
    
    # DBAs (comma-separated)
    if pd.notna(broker_row.get('dbas')):
        dbas = str(broker_row['dbas']).split(',')
        for name in dbas:
            name = name.strip()
            if name:
                variants.append((name, 'dba'))
    
    return variants


def is_known_good_match(existing_match):
    """
    Check if an existing match should be protected (known-good).
    
    Args:
        existing_match: Dict with match_confidence and match_method, or None
        
    Returns:
        True if match should be protected (locked), False otherwise
    """
    if existing_match is None:
        return False
    
    confidence = existing_match.get('match_confidence')
    method = existing_match.get('match_method')
    
    # Protect if confidence >= 0.95 OR method is exact/normalized_exact/manual
    if confidence is not None and confidence >= 0.95:
        return True
    
    if method in ('exact', 'normalized_exact', 'manual'):
        return True
    
    return False


def fuzzy_similarity(str1, str2, use_token_aware=False):
    """
    Calculate similarity ratio between two strings (0.0 to 1.0).
    Uses RapidFuzz if available (much faster), otherwise falls back to SequenceMatcher.
    
    Args:
        str1: First string
        str2: Second string
        use_token_aware: If True, use token-aware matching (max of token_set_ratio, 
                        token_sort_ratio, partial_ratio). Default False for backward compatibility.
    """
    if pd.isna(str1) or pd.isna(str2):
        return 0.0
    
    str1_str = str(str1)
    str2_str = str(str2)
    
    if RAPIDFUZZ_AVAILABLE:
        if use_token_aware:
            # Use token-aware matching: max of multiple methods
            scores = [
                fuzz.ratio(str1_str, str2_str),
                fuzz.token_set_ratio(str1_str, str2_str),
                fuzz.token_sort_ratio(str1_str, str2_str),
                fuzz.partial_ratio(str1_str, str2_str)
            ]
            # RapidFuzz returns 0-100, convert to 0-1
            return max(scores) / 100.0
        else:
            # RapidFuzz returns 0-100, convert to 0-1
            return fuzz.ratio(str1_str, str2_str) / 100.0
    else:
        return SequenceMatcher(None, str1_str, str2_str).ratio()


def match_single_firm(broker_name, fintrx_df, confidence_threshold=0.60, bucket_map=None,
                     use_token_fuzzy=False, use_variants=False, broker_row=None,
                     existing_match=None):
    """
    Match a single broker protocol firm to FINTRX.
    
    Args:
        broker_name: Name of broker protocol firm (primary name)
        fintrx_df: DataFrame with FINTRX firms (must have NAME_normalized and NAME_base columns)
        confidence_threshold: Minimum confidence for fuzzy matches
        bucket_map: Optional dict mapping first character to filtered DataFrame for faster fuzzy matching
        use_token_fuzzy: If True, use token-aware fuzzy matching (default: False for backward compatibility)
        use_variants: If True, also try matching against former_names and dbas (default: False)
        broker_row: Optional dict/Series with full broker row (needed for variant matching)
        existing_match: Optional dict with existing match result (for known-good protection)
    
    Returns:
        dict with match results including:
        - firm_crd_id: CRD ID of matched firm (or None)
        - fintrx_firm_name: Name of matched FINTRX firm (or None)
        - match_confidence: Confidence score (0.0-1.0, or None)
        - match_method: 'exact', 'normalized_exact', 'base_name', 'fuzzy', 'unmatched', or 'manual'
        - needs_manual_review: Boolean
        - matched_on_variant: 'firm_name', 'former_name', 'dba', or None (if use_variants enabled)
    """
    # Check for known-good protection
    if existing_match is not None and is_known_good_match(existing_match):
        # Return existing match unchanged (locked)
        result = existing_match.copy()
        # Ensure all expected fields are present
        if 'matched_on_variant' not in result:
            result['matched_on_variant'] = None
        return result
    
    if pd.isna(broker_name):
        return {
            'firm_crd_id': None,
            'fintrx_firm_name': None,
            'match_confidence': None,
            'match_method': 'unmatched',
            'needs_manual_review': True,
            'matched_on_variant': None
        }
    
    # Get variants to try
    if use_variants and broker_row is not None:
        variants = parse_name_variants(broker_row)
    else:
        # Just use the primary firm name
        variants = [(str(broker_name).strip(), 'firm_name')]
    
    best_match = None
    best_confidence = 0.0
    best_method = 'unmatched'
    best_variant_type = None
    
    # Try each variant
    for variant_name, variant_type in variants:
        if pd.isna(variant_name) or not variant_name.strip():
            continue
        
        variant_normalized = normalize_firm_name(variant_name)
        variant_base = get_base_name(variant_name)
        
        # Tier 1: Exact match (case-insensitive)
        exact_matches = fintrx_df[
            fintrx_df['NAME_normalized'].str.lower() == variant_normalized.lower()
        ]
        if len(exact_matches) > 0:
            if 1.0 > best_confidence:
                best_match = exact_matches.iloc[0]
                best_confidence = 1.0
                best_method = 'exact'
                best_variant_type = variant_type
            continue  # Found exact, no need for lower tiers
        
        # Tier 2: Normalized exact match
        if 0.95 > best_confidence:
            normalized_matches = fintrx_df[
                fintrx_df['NAME_normalized'] == variant_normalized
            ]
            if len(normalized_matches) > 0:
                if 0.95 > best_confidence:
                    best_match = normalized_matches.iloc[0]
                    best_confidence = 0.95
                    best_method = 'normalized_exact'
                    best_variant_type = variant_type
                continue
        
        # Tier 3: Base name match
        if 0.85 > best_confidence and variant_base:
            base_matches = fintrx_df[
                fintrx_df['NAME_base'] == variant_base
            ]
            if len(base_matches) > 0:
                if 0.85 > best_confidence:
                    best_match = base_matches.iloc[0]
                    best_confidence = 0.85
                    best_method = 'base_name'
                    best_variant_type = variant_type
                continue
        
        # Tier 4: Fuzzy match
        if confidence_threshold > best_confidence:
            # Use bucket map to only compare against firms with same first character
            if bucket_map is not None and variant_normalized:
                first_char = variant_normalized[:1] if variant_normalized else ''
                candidates = bucket_map.get(first_char, fintrx_df)
            else:
                candidates = fintrx_df
            
            # Calculate similarity for candidate firms only
            candidates = candidates.copy()
            candidates['similarity'] = candidates['NAME_normalized'].apply(
                lambda x: fuzzy_similarity(variant_normalized, x, use_token_aware=use_token_fuzzy) 
                if pd.notna(x) else 0.0
            )
            
            # Find best match above threshold
            fuzzy_matches = candidates[candidates['similarity'] >= confidence_threshold]
            if len(fuzzy_matches) > 0:
                top_match = fuzzy_matches.loc[fuzzy_matches['similarity'].idxmax()]
                top_score = top_match['similarity']
                if top_score > best_confidence:
                    best_match = top_match
                    best_confidence = top_score
                    best_method = 'fuzzy'
                    best_variant_type = variant_type
    
    # Determine if manual review needed
    needs_review = False
    if best_match is not None:
        if best_method == 'fuzzy' and best_confidence < 0.85:
            needs_review = True
        # Quality check: if confidence < 0.90, force review
        if best_method == 'fuzzy' and best_confidence < 0.90:
            needs_review = True
    else:
        needs_review = True  # Unmatched firms need review
    
    if best_match is not None:
        return {
            'firm_crd_id': int(best_match['CRD_ID']),
            'fintrx_firm_name': str(best_match['NAME']),
            'match_confidence': best_confidence,
            'match_method': best_method,
            'needs_manual_review': needs_review,
            'matched_on_variant': best_variant_type if use_variants else None
        }
    else:
        return {
            'firm_crd_id': None,
            'fintrx_firm_name': None,
            'match_confidence': None,
            'match_method': 'unmatched',
            'needs_manual_review': True,
            'matched_on_variant': None
        }


def batch_match_firms(broker_df, fintrx_df, confidence_threshold=0.60, verbose=False,
                     use_token_fuzzy=False, use_variants=False, protect_known_good=True):
    """
    Match all broker protocol firms to FINTRX.
    
    Args:
        broker_df: DataFrame with broker protocol firms
        fintrx_df: DataFrame with FINTRX firms
        confidence_threshold: Minimum confidence for fuzzy matches
        verbose: Print progress
        use_token_fuzzy: If True, use token-aware fuzzy matching (default: False)
        use_variants: If True, also try matching against former_names and dbas (default: False)
        protect_known_good: If True, lock existing high-confidence matches (default: True)
        
    Returns:
        DataFrame with matched results
    """
    if verbose:
        print(f"Matching {len(broker_df)} broker protocol firms to {len(fintrx_df)} FINTRX firms...")
        if use_token_fuzzy:
            print("  Using token-aware fuzzy matching")
        if use_variants:
            print("  Using variant matching (former_names, dbas)")
        if protect_known_good:
            print("  Protecting known-good matches")
    
    # Pre-process FINTRX names for efficiency
    if verbose:
        print("Pre-processing FINTRX firm names...")
    
    fintrx_df = fintrx_df.copy()
    fintrx_df['NAME_normalized'] = fintrx_df['NAME'].apply(normalize_firm_name)
    fintrx_df['NAME_base'] = fintrx_df['NAME'].apply(get_base_name)
    
    # Create bucket map for faster fuzzy matching (group by first character)
    # This reduces fuzzy comparisons from ~45k to ~1-2k per firm on average
    if verbose:
        print("Creating fuzzy matching buckets...")
    fintrx_df['bucket1'] = fintrx_df['NAME_normalized'].str[:1].fillna('')
    bucket_map = {k: g for k, g in fintrx_df.groupby('bucket1')}
    
    # Check for existing matches in broker_df (for known-good protection)
    existing_matches = {}
    if protect_known_good:
        for idx, row in broker_df.iterrows():
            if 'firm_crd_id' in row and pd.notna(row.get('firm_crd_id')):
                existing_match = {
                    'firm_crd_id': row.get('firm_crd_id'),
                    'fintrx_firm_name': row.get('fintrx_firm_name'),
                    'match_confidence': row.get('match_confidence'),
                    'match_method': row.get('match_method')
                }
                # Only protect if it's actually a known-good match
                if is_known_good_match(existing_match):
                    existing_matches[idx] = existing_match
    
    if verbose and protect_known_good:
        print(f"  Found {len(existing_matches)} known-good matches to protect")
    
    # Match each firm
    matches = []
    for idx, row in broker_df.iterrows():
        if verbose and (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(broker_df)} firms...")
        
        # Get existing match if protected
        existing_match = existing_matches.get(idx) if protect_known_good else None
        
        match_result = match_single_firm(
            row.get('firm_name'),
            fintrx_df,
            confidence_threshold=confidence_threshold,
            bucket_map=bucket_map,
            use_token_fuzzy=use_token_fuzzy,
            use_variants=use_variants,
            broker_row=row.to_dict() if use_variants else None,
            existing_match=existing_match
        )
        
        # Combine with original row data
        matched_row = row.to_dict()
        matched_row.update(match_result)
        matches.append(matched_row)
    
    result_df = pd.DataFrame(matches)
    
    if verbose:
        matched_count = result_df['firm_crd_id'].notna().sum()
        match_rate = matched_count / len(result_df) * 100
        print(f"\n[SUCCESS] Matched {matched_count}/{len(result_df)} firms ({match_rate:.1f}%)")
        print(f"  Match methods: {result_df['match_method'].value_counts().to_dict()}")
        print(f"  Needs review: {result_df['needs_manual_review'].sum()}")
        if use_variants and 'matched_on_variant' in result_df.columns:
            variant_counts = result_df['matched_on_variant'].value_counts()
            print(f"  Matched on variants: {variant_counts.to_dict()}")
    
    return result_df


def main():
    parser = argparse.ArgumentParser(description='Match Broker Protocol firms to FINTRX')
    parser.add_argument('broker_csv', help='Path to parsed broker protocol CSV')
    parser.add_argument('fintrx_csv', help='Path to FINTRX firms CSV')
    parser.add_argument('-o', '--output', help='Output CSV path',
                       default=str(config.get_matched_csv_path()))
    parser.add_argument('-t', '--threshold', type=float, default=0.60,
                       help='Confidence threshold for fuzzy matching (default: 0.60)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--firm', help='Test matching for a single firm name')
    
    args = parser.parse_args()
    
    # Load data
    if not Path(args.broker_csv).exists():
        print(f"ERROR: File not found: {args.broker_csv}", file=sys.stderr)
        sys.exit(1)
    
    if not Path(args.fintrx_csv).exists():
        print(f"ERROR: File not found: {args.fintrx_csv}", file=sys.stderr)
        sys.exit(1)
    
    broker_df = pd.read_csv(args.broker_csv)
    fintrx_df = pd.read_csv(args.fintrx_csv)
    
    if args.firm:
        # Test single firm
        print(f"Testing match for: {args.firm}")
        fintrx_df['NAME_normalized'] = fintrx_df['NAME'].apply(normalize_firm_name)
        fintrx_df['NAME_base'] = fintrx_df['NAME'].apply(get_base_name)
        
        # Create bucket map for fuzzy matching
        fintrx_df['bucket1'] = fintrx_df['NAME_normalized'].str[:1].fillna('')
        bucket_map = {k: g for k, g in fintrx_df.groupby('bucket1')}
        
        result = match_single_firm(args.firm, fintrx_df, confidence_threshold=args.threshold, bucket_map=bucket_map)
        print(f"\nMatch Result:")
        print(f"  CRD ID: {result['firm_crd_id']}")
        print(f"  FINTRX Name: {result['fintrx_firm_name']}")
        print(f"  Confidence: {result['match_confidence']}")
        print(f"  Method: {result['match_method']}")
        print(f"  Needs Review: {result['needs_manual_review']}")
    else:
        # Batch match
        result_df = batch_match_firms(
            broker_df,
            fintrx_df,
            confidence_threshold=args.threshold,
            verbose=args.verbose
        )
        
        # Save results
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result_df.to_csv(output_path, index=False)
        print(f"\n[SUCCESS] Saved matched results to {output_path}")


if __name__ == '__main__':
    main()

