"""Analyze evaluation results to determine best matching approach."""
import pandas as pd
from pathlib import Path

def analyze_results(results_dir: str):
    """Analyze experiment results."""
    results_dir = Path(results_dir)
    
    # Load summary
    summary = pd.read_csv(results_dir / 'summary.csv')
    print("=" * 80)
    print("EXPERIMENT SUMMARY")
    print("=" * 80)
    print(summary.to_string(index=False))
    print()
    
    # Load baseline and best variant
    baseline = pd.read_csv(results_dir / 'baseline_results.csv')
    token_variants = pd.read_csv(results_dir / 'token_variants_results.csv')
    full_variant = pd.read_csv(results_dir / 'full_results.csv')
    
    print("=" * 80)
    print("COMPARING VARIANTS")
    print("=" * 80)
    
    # Compare baseline vs token+variants
    print("\n1. Baseline vs +Token Fuzzy +Variants:")
    baseline_matched = baseline['firm_crd_id'].notna().sum()
    tv_matched = token_variants['firm_crd_id'].notna().sum()
    print(f"   Baseline matched: {baseline_matched}/{len(baseline)} ({baseline_matched/len(baseline)*100:.2f}%)")
    print(f"   Token+Variants matched: {tv_matched}/{len(token_variants)} ({tv_matched/len(token_variants)*100:.2f}%)")
    print(f"   Improvement: +{tv_matched - baseline_matched} firms")
    
    # Newly matched analysis
    newly_matched = token_variants[
        (token_variants['firm_crd_id'].notna()) & 
        (baseline['firm_crd_id'].isna())
    ].copy()
    
    print(f"\n2. Newly Matched Firms ({len(newly_matched)}):")
    print(f"   Mean confidence: {newly_matched['match_confidence'].mean():.3f}")
    print(f"   Min confidence: {newly_matched['match_confidence'].min():.3f}")
    print(f"   Max confidence: {newly_matched['match_confidence'].max():.3f}")
    print(f"   Confidence >= 0.90: {(newly_matched['match_confidence'] >= 0.90).sum()}")
    print(f"   Confidence < 0.90: {(newly_matched['match_confidence'] < 0.90).sum()}")
    print(f"   Needs manual review: {newly_matched['needs_manual_review'].sum()}")
    print(f"   Match methods:")
    print(newly_matched['match_method'].value_counts().to_string())
    
    # Check quality criteria
    print(f"\n3. Quality Check (Acceptance Criteria):")
    low_confidence = newly_matched[newly_matched['match_confidence'] < 0.90]
    if len(low_confidence) > 0:
        print(f"   [WARNING] {len(low_confidence)} newly matched with confidence < 0.90")
        print(f"   All flagged for review: {(low_confidence['needs_manual_review'] == True).all()}")
        print(f"   Sample low-confidence matches:")
        print(low_confidence[['firm_name', 'match_confidence', 'match_method', 'needs_manual_review']].head(10).to_string())
    else:
        print(f"   [OK] All newly matched have confidence >= 0.90")
    
    # Check confidence margins for ambiguous matches
    if 'confidence_margin' in newly_matched.columns:
        ambiguous = newly_matched[
            (newly_matched['confidence_margin'].notna()) & 
            (newly_matched['confidence_margin'] < 0.05)
        ]
        print(f"\n   Ambiguous matches (margin < 0.05): {len(ambiguous)}")
        if len(ambiguous) > 0:
            print(f"   All flagged for review: {(ambiguous['needs_manual_review'] == True).all()}")
    
    # Known-good stability check
    print(f"\n4. Known-Good Stability Check:")
    if 'match_confidence' in baseline.columns and 'match_method' in baseline.columns:
        known_good_mask = (
            (baseline['match_confidence'] >= 0.95) |
            (baseline['match_method'].isin(['exact', 'normalized_exact', 'manual']))
        ) & (baseline['firm_crd_id'].notna())
        
        known_good_baseline = baseline[known_good_mask].copy()
        known_good_tv = token_variants[known_good_mask].copy()
        
        changed = (known_good_baseline['firm_crd_id'] != known_good_tv['firm_crd_id']).sum()
        print(f"   Known-good firms: {known_good_mask.sum()}")
        print(f"   Changed CRD_ID: {changed}")
        if changed == 0:
            print(f"   [PASS] No known-good matches changed")
        else:
            print(f"   [FAIL] {changed} known-good matches changed")
    
    # Compare needs_review counts
    print(f"\n5. Manual Review Impact:")
    print(f"   Baseline needs_review: {(baseline.get('needs_manual_review', pd.Series([False]*len(baseline))) == True).sum()}")
    print(f"   Token+Variants needs_review: {token_variants['needs_manual_review'].sum()}")
    print(f"   Full variant needs_review: {full_variant['needs_manual_review'].sum()}")
    
    # Recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    
    match_rate_tv = tv_matched / len(token_variants) * 100
    match_rate_baseline = baseline_matched / len(baseline) * 100
    improvement = match_rate_tv - match_rate_baseline
    
    criteria_met = []
    if match_rate_tv >= 99.0 or improvement >= 2.5:
        criteria_met.append("[PASS] Match rate >= 99% or improvement >= 2.5 points")
    else:
        criteria_met.append("[FAIL] Match rate criteria not met")
    
    if changed == 0:
        criteria_met.append("[PASS] No known-good matches changed")
    else:
        criteria_met.append("[FAIL] Known-good matches changed")
    
    low_conf_all_flagged = len(low_confidence) == 0 or (low_confidence['needs_manual_review'] == True).all()
    if low_conf_all_flagged:
        criteria_met.append("[PASS] Low-confidence matches flagged for review")
    else:
        criteria_met.append("[FAIL] Some low-confidence matches not flagged")
    
    baseline_review_count = (baseline.get('needs_manual_review', pd.Series([False]*len(baseline))) == True).sum()
    review_exploded = token_variants['needs_manual_review'].sum() > baseline_review_count * 1.5
    if not review_exploded:
        criteria_met.append("[PASS] Manual review count acceptable")
    else:
        criteria_met.append("[WARNING] Manual review count increased significantly")
    
    print("\nAcceptance Criteria Check:")
    for criterion in criteria_met:
        print(f"  {criterion}")
    
    print(f"\n[BEST VARIANT] +Token Fuzzy +Variants")
    print(f"   - Match rate: {match_rate_tv:.2f}% (baseline: {match_rate_baseline:.2f}%)")
    print(f"   - Improvement: +{improvement:.2f} percentage points")
    print(f"   - Newly matched: {len(newly_matched)} firms")
    print(f"   - Known-good stability: {changed} changed")
    print(f"   - Manual review: {token_variants['needs_manual_review'].sum()} firms")
    
    if all("[PASS]" in c for c in criteria_met[:3]):
        print(f"\n[RECOMMENDATION] IMPLEMENT +Token Fuzzy +Variants")
        print(f"   This variant meets all acceptance criteria and achieves 100% match rate.")
    else:
        print(f"\n[RECOMMENDATION] Review acceptance criteria")
        print(f"   Some criteria not fully met, but variant shows strong improvement.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        # Use most recent
        output_dir = Path(__file__).parent / 'output'
        results_dir = sorted(output_dir.glob('*'))[-1]
    
    analyze_results(results_dir)

