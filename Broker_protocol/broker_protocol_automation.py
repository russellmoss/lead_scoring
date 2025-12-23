"""
Broker Protocol Full Automation Script
Downloads, parses, matches, and merges broker protocol data.
This script is called by n8n workflow for automated runs.
"""

import sys
import os
from datetime import datetime
import argparse
import traceback
from pathlib import Path
import config


def run_full_automation(excel_path: str, verbose: bool = False, dry_run: bool = False):
    """
    Run complete automation pipeline.
    
    Args:
        excel_path: Path to downloaded Excel file
        verbose: Print detailed output
        dry_run: If True, don't actually update BigQuery
        
    Returns:
        dict with results
    """
    
    start_time = datetime.now()
    scrape_run_id = f"auto_{start_time.strftime('%Y%m%d_%H%M%S')}"
    
    results = {
        'scrape_run_id': scrape_run_id,
        'status': 'FAILED',
        'error': None,
        'steps_completed': [],
        'duration_seconds': 0
    }
    
    try:
        # Step 1: Parse Excel
        print("=" * 60)
        print("STEP 1: Parsing Excel file")
        print("=" * 60)
        
        if not Path(excel_path).exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        import broker_protocol_parser as parser
        
        parsed_df = parser.parse_broker_protocol_excel(excel_path, verbose=verbose)
        parsed_path = config.get_parsed_csv_path()
        parsed_path.parent.mkdir(parents=True, exist_ok=True)
        parsed_df.to_csv(parsed_path, index=False)
        
        results['steps_completed'].append('PARSE')
        results['firms_parsed'] = len(parsed_df)
        
        print(f"\n[SUCCESS] Parsed {len(parsed_df)} firms")
        print(f"  Saved to: {parsed_path}")
        
        # Step 2: Get FINTRX firms
        print("\n" + "=" * 60)
        print("STEP 2: Loading FINTRX firms")
        print("=" * 60)
        
        from google.cloud import bigquery
        
        client = bigquery.Client(project=config.GCP_PROJECT_ID)
        
        query = f"""
        SELECT CRD_ID, NAME
        FROM `{config.TABLE_FINTRX_FIRMS}`
        WHERE NAME IS NOT NULL
        """
        
        if verbose:
            print(f"Querying BigQuery: {config.TABLE_FINTRX_FIRMS}")
        
        fintrx_df = client.query(query).to_dataframe()
        fintrx_path = config.get_fintrx_export_path()
        fintrx_path.parent.mkdir(parents=True, exist_ok=True)
        fintrx_df.to_csv(fintrx_path, index=False)
        
        print(f"\n[SUCCESS] Loaded {len(fintrx_df)} FINTRX firms")
        print(f"  Saved to: {fintrx_path}")
        
        # Step 3: Match firms
        print("\n" + "=" * 60)
        print("STEP 3: Matching firms to FINTRX")
        print("=" * 60)
        
        import firm_matcher as matcher
        
        matched_df = matcher.batch_match_firms(
            parsed_df,
            fintrx_df,
            confidence_threshold=config.DEFAULT_CONFIDENCE_THRESHOLD,
            verbose=verbose,
            use_token_fuzzy=True,
            use_variants=True,
            protect_known_good=True
        )
        
        matched_path = config.get_matched_csv_path()
        matched_path.parent.mkdir(parents=True, exist_ok=True)
        matched_df.to_csv(matched_path, index=False)
        
        results['steps_completed'].append('MATCH')
        matched_count = (matched_df['firm_crd_id'].notna()).sum()
        results['firms_matched'] = matched_count
        results['match_rate'] = matched_count / len(matched_df) * 100 if len(matched_df) > 0 else 0
        results['needs_review'] = matched_df['needs_manual_review'].sum()
        
        print(f"\n[SUCCESS] Matched {matched_count}/{len(matched_df)} firms ({results['match_rate']:.1f}%)")
        print(f"  Needs review: {results['needs_review']}")
        print(f"  Saved to: {matched_path}")
        
        # Step 4: Merge with existing data
        print("\n" + "=" * 60)
        print("STEP 4: Merging with existing data")
        print("=" * 60)
        
        if dry_run:
            print("[DRY RUN] Skipping BigQuery merge")
            results['steps_completed'].append('MERGE_DRY_RUN')
        else:
            import broker_protocol_updater as updater
            
            merge_results = updater.merge_broker_protocol_data(
                str(matched_path),
                scrape_run_id,
                dry_run=False
            )
            
            results['steps_completed'].append('MERGE')
            if merge_results:
                results['new_firms'] = merge_results.get('new_firms', 0)
                results['withdrawn_firms'] = merge_results.get('withdrawn_firms', 0)
                results['updated_firms'] = merge_results.get('updated_firms', 0)
                results['changes_logged'] = merge_results.get('changes', 0)
            
            print(f"\n[SUCCESS] Merged data successfully")
            if merge_results:
                print(f"  New firms: {results.get('new_firms', 0)}")
                print(f"  Withdrawn firms: {results.get('withdrawn_firms', 0)}")
                print(f"  Updated firms: {results.get('updated_firms', 0)}")
                print(f"  Changes logged: {results.get('changes_logged', 0)}")
        
        # Success
        results['status'] = 'SUCCESS'
        
        duration = (datetime.now() - start_time).total_seconds()
        results['duration_seconds'] = duration
        
        print("\n" + "=" * 60)
        print("AUTOMATION COMPLETE")
        print("=" * 60)
        print(f"Status: {results['status']}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Scrape Run ID: {scrape_run_id}")
        print(f"\nSteps completed: {', '.join(results['steps_completed'])}")
        
        return results
        
    except Exception as e:
        results['status'] = 'FAILED'
        results['error'] = str(e)
        
        duration = (datetime.now() - start_time).total_seconds()
        results['duration_seconds'] = duration
        
        print(f"\n[ERROR] {str(e)}", file=sys.stderr)
        
        if verbose:
            traceback.print_exc()
        
        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run broker protocol automation')
    parser.add_argument('excel_file', help='Path to Excel file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (skip BigQuery merge)')
    
    args = parser.parse_args()
    
    if not Path(args.excel_file).exists():
        print(f"ERROR: File not found: {args.excel_file}", file=sys.stderr)
        sys.exit(1)
    
    results = run_full_automation(args.excel_file, verbose=args.verbose, dry_run=args.dry_run)
    
    if results['status'] == 'FAILED':
        print(f"\n[FAILED] Automation failed: {results.get('error', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n[SUCCESS] Automation completed successfully")
    sys.exit(0)

