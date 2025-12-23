"""
Export FINTRX Firms for Matching
Exports FINTRX firm list to CSV for use in firm matching.
"""

import pandas as pd
from google.cloud import bigquery
from pathlib import Path
import sys
import config

def export_fintrx_firms(output_path=None):
    """
    Export FINTRX firms to CSV for matching.
    
    Args:
        output_path: Path to output CSV file (defaults to config path)
        
    Returns:
        DataFrame with FINTRX firms
    """
    if output_path is None:
        output_path = config.get_fintrx_export_path()
    
    print("Exporting FINTRX firms...")
    
    try:
        client = bigquery.Client(project=config.GCP_PROJECT_ID)
        
        query = f"""
        SELECT 
            CRD_ID,
            NAME,
            TOTAL_AUM,
            NUM_OF_EMPLOYEES
        FROM `{config.TABLE_FINTRX_FIRMS}`
        WHERE NAME IS NOT NULL
        ORDER BY CRD_ID
        """
        
        print(f"Querying BigQuery: {config.TABLE_FINTRX_FIRMS}")
        fintrx_df = client.query(query).to_dataframe()
        
        print(f"Exported {len(fintrx_df)} FINTRX firms")
        print(f"  With AUM: {fintrx_df['TOTAL_AUM'].notna().sum()}")
        print(f"  With employee count: {fintrx_df['NUM_OF_EMPLOYEES'].notna().sum()}")
        
        # Save to CSV
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fintrx_df.to_csv(output_path, index=False)
        
        print(f"\n[SUCCESS] Saved to {output_path}")
        
        return fintrx_df
        
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Export FINTRX firms for matching')
    parser.add_argument('-o', '--output', help='Output CSV path', 
                       default=str(config.get_fintrx_export_path()))
    
    args = parser.parse_args()
    
    export_fintrx_firms(args.output)

