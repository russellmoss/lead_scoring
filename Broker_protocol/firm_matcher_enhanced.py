"""
Enhanced Firm Matcher
Improved matching strategies with optional features for evaluation.
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

# Import base functions
import firm_matcher

# Try to use RapidFuzz for faster fuzzy matching
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


def normalize_firm_name_enhanced(name: str, cleanup_mode: bool = False) -> Optional[str]:
    """
    Enhanced normalization with optional cleanup.
    
    Args:
        name: Firm name to normalize
        cleanup_mode: If True, apply additional cleanup (strip footnotes, etc.)
    """
    if pd.isna(name):
        return None
    
    name_str = str(name).strip()
    
    if cleanup_mode:
        # Strip leading footnote markers
        name_str = re.sub(r'^[\*\†\‡\§]+', '', name_str)
        
        # Remove obvious "note" parentheticals (but preserve brand parentheses)
        # Pattern: (*See...), (See...), etc.
        name_str = re.sub(r'\s*\([^)]*[Ss]ee[^)]*\)', '', name_str, flags=re.IGNORECASE)
        name_str = re.sub(r'\s*\([^)]*[Ss]pecific[^)]*qualification[^)]*\)', '', name_str, flags=re.IGNORECASE)
        
        # Normalize &/and
        name_str = re.sub(r'\s*&\s*', ' and ', name_str)
    
    # Apply base normalization
    name_str = firm_matcher.normalize_firm_name(name_str)
    
    return name_str


def parse_name_variants(row: Dict) -> List[Tuple[str, str]]:
    """
    Parse name variants from broker protocol row.
    
    Returns:
        List of (variant_name, variant_type) tuples
    """
    variants = []
    
    # Main firm name
    if pd.notna(row.get('firm_name')):
        variants.append((str(row['firm_name']), 'firm_name'))
    
    # Former names (f/k/a)
    if pd.notna(row.get('former_names')):
        former_names = str(row['former_names']).split(',')
        for name in former_names:
            name = name.strip()
            if name:
                variants.append((name, 'former_name'))
    
    # DBAs (d/b/a)
    if pd.notna(row.get('dbas')):
        dbas = str(row['dbas']).split(',')
        for name in dbas:
            name = name.strip()
            if name:
                variants.append((name, 'dba'))
    
    return variants


def fuzzy_similarity_token_aware(str1: str, str2: str) -> float:
    """
    Token-aware fuzzy similarity using multiple RapidFuzz methods.
    
    Returns:
        Maximum of token_set_ratio, token_sort_ratio, partial_ratio, ratio
    """
    if pd.isna(str1) or pd.isna(str2):
        return 0.0
    
    str1_str = str(str1)
    str2_str = str(str2)
    
    if RAPIDFUZZ_AVAILABLE:
        scores = [
            fuzz.ratio(str1_str, str2_str),
            fuzz.partial_ratio(str1_str, str2_str),
            fuzz.token_sort_ratio(str1_str, str2_str),
            fuzz.token_set_ratio(str1_str, str2_str)
        ]
        return max(scores) / 100.0
    else:
        # Fallback to basic ratio
        return SequenceMatcher(None, str1_str, str2_str).ratio()


def get_candidate_bucket(fintrx_df: pd.DataFrame, broker_normalized: str,
                        bucket_strategy: str = 'first_char') -> pd.DataFrame:
    """
    Get candidate bucket based on strategy.
    
    Args:
        fintrx_df: FINTRX DataFrame with bucket columns
        broker_normalized: Normalized broker name
        bucket_strategy: 'first_char', 'first2', 'first_token', 'hybrid'
    
    Returns:
        Filtered DataFrame of candidates
    """
    if not broker_normalized:
        return fintrx_df
    
    fintrx_df = fintrx_df.copy()  # Work on copy to avoid modifying original
    
    if bucket_strategy == 'first_char':
        first_char = broker_normalized[:1] if broker_normalized else ''
        if 'bucket1' in fintrx_df.columns:
            candidates = fintrx_df[fintrx_df['bucket1'] == first_char]
            return candidates if len(candidates) > 0 else fintrx_df
        else:
            return fintrx_df
    
    elif bucket_strategy == 'first2':
        first2 = broker_normalized[:2] if len(broker_normalized) >= 2 else broker_normalized
        bucket_col = 'bucket2'
        if bucket_col not in fintrx_df.columns and 'NAME_normalized' in fintrx_df.columns:
            fintrx_df[bucket_col] = fintrx_df['NAME_normalized'].str[:2].fillna('')
        if bucket_col in fintrx_df.columns:
            candidates = fintrx_df[fintrx_df[bucket_col] == first2]
            return candidates if len(candidates) > 0 else fintrx_df
        else:
            return fintrx_df
    
    elif bucket_strategy == 'first_token':
        first_token = broker_normalized.split()[0] if broker_normalized.split() else ''
        bucket_col = 'bucket_token'
        if bucket_col not in fintrx_df.columns and 'NAME_normalized' in fintrx_df.columns:
            fintrx_df[bucket_col] = fintrx_df['NAME_normalized'].str.split().str[0].fillna('')
        if bucket_col in fintrx_df.columns:
            candidates = fintrx_df[fintrx_df[bucket_col] == first_token]
            return candidates if len(candidates) > 0 else fintrx_df
        else:
            return fintrx_df
    
    elif bucket_strategy == 'hybrid':
        # Try first_char, then first_token, then all
        first_char = broker_normalized[:1] if broker_normalized else ''
        if 'bucket1' in fintrx_df.columns:
            candidates = fintrx_df[fintrx_df['bucket1'] == first_char]
            if len(candidates) > 0:
                return candidates
        
        # Fallback to first token
        first_token = broker_normalized.split()[0] if broker_normalized.split() else ''
        bucket_col = 'bucket_token'
        if bucket_col not in fintrx_df.columns and 'NAME_normalized' in fintrx_df.columns:
            fintrx_df[bucket_col] = fintrx_df['NAME_normalized'].str.split().str[0].fillna('')
        if bucket_col in fintrx_df.columns:
            candidates = fintrx_df[fintrx_df[bucket_col] == first_token]
            if len(candidates) > 0:
                return candidates
        
        # Final fallback to all
        return fintrx_df
    
    else:
        return fintrx_df


def match_single_firm_enhanced(
    broker_row: Dict,
    fintrx_df: pd.DataFrame,
    confidence_threshold: float = 0.60,
    use_variants: bool = False,
    fuzzy_mode: str = 'ratio',
    enable_ambiguity_check: bool = False,
    ambiguity_margin: float = 0.05,
    cleanup_mode: bool = False,
    bucket_strategy: str = 'first_char',
    overrides_map: Optional[Dict] = None
) -> Dict:
    """
    Enhanced single firm matcher with optional improvements.
    
    Args:
        broker_row: Dict with broker firm data (firm_name, former_names, dbas, etc.)
        fintrx_df: DataFrame with FINTRX firms (must have NAME_normalized, NAME_base)
        confidence_threshold: Minimum confidence for fuzzy matches
        use_variants: If True, try former_names and dbas
        fuzzy_mode: 'ratio' or 'token_max'
        enable_ambiguity_check: If True, check for ambiguous matches
        ambiguity_margin: Minimum margin between top1 and top2
        cleanup_mode: If True, apply enhanced normalization cleanup
        bucket_strategy: Bucket strategy for candidate generation
        overrides_map: Dict mapping normalized names to {crd_id, fintrx_name}
    
    Returns:
        dict with match results (includes matched_on_variant, top2_confidence, confidence_margin if applicable)
    """
    broker_name = broker_row.get('firm_name')
    if pd.isna(broker_name):
        return {
            'firm_crd_id': None,
            'fintrx_firm_name': None,
            'match_confidence': None,
            'match_method': 'unmatched',
            'needs_manual_review': True,
            'matched_on_variant': None,
            'top2_confidence': None,
            'confidence_margin': None
        }
    
    # Tier 0: Manual overrides
    if overrides_map:
        broker_normalized = normalize_firm_name_enhanced(broker_name, cleanup_mode)
        if broker_normalized and broker_normalized in overrides_map:
            override = overrides_map[broker_normalized]
            return {
                'firm_crd_id': override['crd_id'],
                'fintrx_firm_name': override.get('fintrx_name', ''),
                'match_confidence': 1.0,
                'match_method': 'manual',
                'needs_manual_review': False,
                'matched_on_variant': 'override',
                'top2_confidence': None,
                'confidence_margin': None
            }
    
    # Get name variants to try
    if use_variants:
        variants = parse_name_variants(broker_row)
    else:
        variants = [(broker_name, 'firm_name')]
    
    best_match = None
    best_confidence = 0.0
    best_method = 'unmatched'
    best_variant = None
    top2_confidence = None
    best_top2_confidence = None  # Track top2 across all variants
    
    # Try each variant
    for variant_name, variant_type in variants:
        variant_normalized = normalize_firm_name_enhanced(variant_name, cleanup_mode)
        if not variant_normalized:
            continue
        
        variant_base = firm_matcher.get_base_name(variant_name)
        
        # Tier 1: Exact match
        exact_matches = fintrx_df[
            fintrx_df['NAME_normalized'].str.lower() == variant_normalized.lower()
        ]
        if len(exact_matches) > 0:
            candidate = exact_matches.iloc[0]
            if 1.0 > best_confidence:
                best_match = candidate
                best_confidence = 1.0
                best_method = 'exact'
                best_variant = variant_type
            continue
        
        # Tier 2: Normalized exact match
        normalized_matches = fintrx_df[
            fintrx_df['NAME_normalized'] == variant_normalized
        ]
        if len(normalized_matches) > 0:
            candidate = normalized_matches.iloc[0]
            if 0.95 > best_confidence:
                best_match = candidate
                best_confidence = 0.95
                best_method = 'normalized_exact'
                best_variant = variant_type
            continue
        
        # Tier 3: Base name match
        if variant_base:
            base_matches = fintrx_df[
                fintrx_df['NAME_base'] == variant_base
            ]
            if len(base_matches) > 0:
                candidate = base_matches.iloc[0]
                if 0.85 > best_confidence:
                    best_match = candidate
                    best_confidence = 0.85
                    best_method = 'base_name'
                    best_variant = variant_type
                continue
        
        # Tier 4: Fuzzy match
        candidates = get_candidate_bucket(fintrx_df, variant_normalized, bucket_strategy)
        if len(candidates) == 0:
            candidates = fintrx_df
        
        candidates = candidates.copy()
        
        # Calculate similarity
        if fuzzy_mode == 'token_max':
            candidates['similarity'] = candidates['NAME_normalized'].apply(
                lambda x: fuzzy_similarity_token_aware(variant_normalized, x) if pd.notna(x) else 0.0
            )
        else:
            candidates['similarity'] = candidates['NAME_normalized'].apply(
                lambda x: firm_matcher.fuzzy_similarity(variant_normalized, x) if pd.notna(x) else 0.0
            )
        
        # Get top matches
        fuzzy_matches = candidates[candidates['similarity'] >= confidence_threshold]
        if len(fuzzy_matches) > 0:
            sorted_matches = fuzzy_matches.sort_values('similarity', ascending=False)
            top_match = sorted_matches.iloc[0]
            top_score = top_match['similarity']
            
            # Get top2 for ambiguity check (always track for quality checks)
            if len(sorted_matches) > 1:
                variant_top2 = sorted_matches.iloc[1]['similarity']
            else:
                variant_top2 = 0.0
            
            if top_score > best_confidence:
                best_match = top_match
                best_confidence = top_score
                best_method = 'fuzzy'
                best_variant = variant_type
                if enable_ambiguity_check or True:  # Always track top2 for quality checks
                    best_top2_confidence = variant_top2
    
    # Ambiguity check
    confidence_margin = None
    has_match = best_match is not None
    top2_confidence = best_top2_confidence  # Use the tracked value
    
    if enable_ambiguity_check and has_match and top2_confidence is not None:
        confidence_margin = best_confidence - top2_confidence
        if confidence_margin < ambiguity_margin:
            # Ambiguous match - force review
            needs_review = True
        else:
            needs_review = (best_method == 'fuzzy' and best_confidence < 0.85)
    else:
        needs_review = (best_method == 'fuzzy' and best_confidence < 0.85) if has_match else True
    
    has_match = best_match is not None
    if has_match:
        result = {
            'firm_crd_id': int(best_match['CRD_ID']),
            'fintrx_firm_name': str(best_match['NAME']),
            'match_confidence': best_confidence,
            'match_method': best_method,
            'needs_manual_review': needs_review,
            'matched_on_variant': best_variant,
            'top2_confidence': top2_confidence,
            'confidence_margin': confidence_margin
        }
        
        # Quality check for newly matched: if confidence < 0.90 or margin < 0.05, force review
        if best_method == 'fuzzy' and (best_confidence < 0.90 or (confidence_margin is not None and confidence_margin < 0.05)):
            result['needs_manual_review'] = True
        
        return result
    else:
        return {
            'firm_crd_id': None,
            'fintrx_firm_name': None,
            'match_confidence': None,
            'match_method': 'unmatched',
            'needs_manual_review': True,
            'matched_on_variant': None,
            'top2_confidence': None,
            'confidence_margin': None
        }


def batch_match_firms_enhanced(
    broker_df: pd.DataFrame,
    fintrx_df: pd.DataFrame,
    confidence_threshold: float = 0.60,
    use_variants: bool = False,
    fuzzy_mode: str = 'ratio',
    enable_ambiguity_check: bool = False,
    ambiguity_margin: float = 0.05,
    cleanup_mode: bool = False,
    bucket_strategy: str = 'first_char',
    overrides_map: Optional[Dict] = None,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Enhanced batch matcher with optional improvements.
    
    Args:
        broker_df: DataFrame with broker protocol firms
        fintrx_df: DataFrame with FINTRX firms
        confidence_threshold: Minimum confidence for fuzzy matches
        use_variants: If True, try former_names and dbas
        fuzzy_mode: 'ratio' or 'token_max'
        enable_ambiguity_check: If True, check for ambiguous matches
        ambiguity_margin: Minimum margin between top1 and top2
        cleanup_mode: If True, apply enhanced normalization cleanup
        bucket_strategy: Bucket strategy for candidate generation
        overrides_map: Dict mapping normalized names to overrides
        verbose: Print progress
    
    Returns:
        DataFrame with matched results
    """
    if verbose:
        print(f"Matching {len(broker_df)} broker protocol firms to {len(fintrx_df)} FINTRX firms...")
    
    # Pre-process FINTRX names
    if verbose:
        print("Pre-processing FINTRX firm names...")
    
    fintrx_df = fintrx_df.copy()
    fintrx_df['NAME_normalized'] = fintrx_df['NAME'].apply(firm_matcher.normalize_firm_name)
    fintrx_df['NAME_base'] = fintrx_df['NAME'].apply(firm_matcher.get_base_name)
    
    # Create buckets based on strategy
    if verbose:
        print(f"Creating buckets (strategy: {bucket_strategy})...")
    
    fintrx_df['bucket1'] = fintrx_df['NAME_normalized'].str[:1].fillna('')
    
    if bucket_strategy in ['first2', 'hybrid']:
        fintrx_df['bucket2'] = fintrx_df['NAME_normalized'].str[:2].fillna('')
    
    if bucket_strategy in ['first_token', 'hybrid']:
        fintrx_df['bucket_token'] = fintrx_df['NAME_normalized'].str.split().str[0].fillna('')
    
    # Match each firm
    matches = []
    for idx, row in broker_df.iterrows():
        if verbose and (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(broker_df)} firms...")
        
        match_result = match_single_firm_enhanced(
            row.to_dict(),
            fintrx_df,
            confidence_threshold=confidence_threshold,
            use_variants=use_variants,
            fuzzy_mode=fuzzy_mode,
            enable_ambiguity_check=enable_ambiguity_check,
            ambiguity_margin=ambiguity_margin,
            cleanup_mode=cleanup_mode,
            bucket_strategy=bucket_strategy,
            overrides_map=overrides_map
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
    
    return result_df

