"""
Unit tests for firm matcher improvements.
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import firm_matcher
from firm_matcher_enhanced import (
    normalize_firm_name_enhanced,
    parse_name_variants,
    fuzzy_similarity_token_aware,
    match_single_firm_enhanced,
    get_candidate_bucket
)


class TestNormalization:
    """Test normalization improvements."""
    
    def test_normalize_handles_punctuation(self):
        """Test that normalization handles punctuation correctly."""
        name = "Smith & Co., LLC"
        normalized = firm_matcher.normalize_firm_name(name)
        assert normalized == "smith & co llc"
    
    def test_normalize_enhanced_cleanup_footnotes(self):
        """Test enhanced normalization removes footnote markers."""
        name = "*See specific qualifications..."
        normalized = normalize_firm_name_enhanced(name, cleanup_mode=True)
        assert not normalized.startswith('*')
        assert 'see specific' in normalized.lower()
    
    def test_normalize_enhanced_removes_note_parentheticals(self):
        """Test enhanced normalization removes note parentheticals."""
        name = "Firm Name (*See qualifications in attached list)"
        normalized = normalize_firm_name_enhanced(name, cleanup_mode=True)
        assert 'see qualifications' not in normalized.lower()
        assert 'firm name' in normalized.lower()
    
    def test_normalize_enhanced_normalizes_ampersand(self):
        """Test enhanced normalization normalizes & to and."""
        name = "Smith & Jones LLC"
        normalized = normalize_firm_name_enhanced(name, cleanup_mode=True)
        assert ' and ' in normalized or 'and' in normalized


class TestTokenFuzzy:
    """Test token-aware fuzzy matching."""
    
    def test_token_fuzzy_handles_reordered_tokens(self):
        """Test that token-based fuzzy handles reordered tokens better."""
        str1 = "Morgan Stanley Wealth Management"
        str2 = "Wealth Management Morgan Stanley"
        
        token_score = fuzzy_similarity_token_aware(str1, str2)
        ratio_score = firm_matcher.fuzzy_similarity(str1, str2)
        
        # Token-based should score higher for reordered tokens
        assert token_score >= ratio_score
        assert token_score > 0.8  # Should be high similarity


class TestVariantMatching:
    """Test variant matching (former_names, dbas)."""
    
    def test_parse_name_variants(self):
        """Test parsing of name variants."""
        row = {
            'firm_name': 'Current Name LLC',
            'former_names': 'Old Name Inc, Previous Name Corp',
            'dbas': 'DBA Name'
        }
        
        variants = parse_name_variants(row)
        
        assert len(variants) == 4
        assert ('Current Name LLC', 'firm_name') in variants
        assert ('Old Name Inc', 'former_name') in variants
        assert ('Previous Name Corp', 'former_name') in variants
        assert ('DBA Name', 'dba') in variants
    
    def test_variant_matching_matches_on_dba(self):
        """Test that variant matching can match on DBA when firm_name fails."""
        broker_row = {
            'firm_name': 'Unknown Firm Name',
            'dbas': 'Known DBA Name'
        }
        
        fintrx_df = pd.DataFrame({
            'CRD_ID': [12345],
            'NAME': ['Known DBA Name LLC'],
            'NAME_normalized': ['known dba name llc'],
            'NAME_base': ['known dba name']
        })
        
        result = match_single_firm_enhanced(
            broker_row,
            fintrx_df,
            use_variants=True,
            fuzzy_mode='ratio'
        )
        
        assert result['firm_crd_id'] == 12345
        assert result['matched_on_variant'] == 'dba'


class TestManualOverrides:
    """Test manual override functionality."""
    
    def test_manual_override_short_circuits(self):
        """Test that manual override short-circuits matching."""
        broker_row = {'firm_name': 'Test Firm LLC'}
        
        fintrx_df = pd.DataFrame({
            'CRD_ID': [99999],
            'NAME': ['Wrong Match'],
            'NAME_normalized': ['wrong match'],
            'NAME_base': ['wrong match']
        })
        
        overrides_map = {
            'test firm llc': {
                'crd_id': 12345,
                'fintrx_name': 'Correct Match'
            }
        }
        
        result = match_single_firm_enhanced(
            broker_row,
            fintrx_df,
            overrides_map=overrides_map
        )
        
        assert result['firm_crd_id'] == 12345
        assert result['match_method'] == 'manual'
        assert result['match_confidence'] == 1.0
        assert result['needs_manual_review'] == False


class TestAmbiguityCheck:
    """Test ambiguity detection."""
    
    def test_ambiguity_check_forces_review(self):
        """Test that ambiguity check forces review when margin is small."""
        broker_name = "Ambiguous Firm Name"
        
        # Create FINTRX with two very similar names
        fintrx_df = pd.DataFrame({
            'CRD_ID': [111, 222],
            'NAME': ['Ambiguous Firm Name LLC', 'Ambiguous Firm Names Inc'],
            'NAME_normalized': ['ambiguous firm name llc', 'ambiguous firm names inc'],
            'NAME_base': ['ambiguous firm name', 'ambiguous firm names']
        })
        
        broker_row = {'firm_name': broker_name}
        
        # Without ambiguity check
        result_no_check = match_single_firm_enhanced(
            broker_row,
            fintrx_df,
            enable_ambiguity_check=False
        )
        
        # With ambiguity check
        result_with_check = match_single_firm_enhanced(
            broker_row,
            fintrx_df,
            enable_ambiguity_check=True,
            ambiguity_margin=0.10
        )
        
        # Both should match, but with_check should have needs_review=True if ambiguous
        assert result_with_check['firm_crd_id'] is not None
        margin = result_with_check.get('confidence_margin')
        if margin is not None and margin < 0.10:
            assert result_with_check['needs_manual_review'] == True


class TestBucketStrategy:
    """Test bucket strategy improvements."""
    
    def test_bucket_first_char(self):
        """Test first character bucket."""
        fintrx_df = pd.DataFrame({
            'NAME_normalized': ['apple inc', 'banana corp', 'apricot llc'],
            'bucket1': ['a', 'b', 'a']
        })
        
        candidates = get_candidate_bucket(fintrx_df, 'apple', 'first_char')
        assert len(candidates) == 2  # apple and apricot
        assert 'banana' not in candidates['NAME_normalized'].values
    
    def test_bucket_first_token(self):
        """Test first token bucket."""
        fintrx_df = pd.DataFrame({
            'NAME_normalized': ['apple inc', 'apple corp', 'banana llc'],
            'bucket_token': ['apple', 'apple', 'banana']
        })
        
        candidates = get_candidate_bucket(fintrx_df, 'apple pie', 'first_token')
        assert len(candidates) == 2  # both apple firms
        assert 'banana' not in candidates['NAME_normalized'].values


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

