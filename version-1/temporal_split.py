"""
Phase 2.1: Temporal Train/Validation/Test Split
Ensures no future information leakage in model training
"""

import pandas as pd
from google.cloud import bigquery

class TemporalSplitter:
    def __init__(self, project_id: str = "savvy-gtm-analytics"):
        self.client = bigquery.Client(project=project_id, location="northamerica-northeast2")
        self.split_boundaries = {}
        
    def create_temporal_split(
        self,
        train_pct: float = 0.70,
        val_pct: float = 0.15,
        test_pct: float = 0.15,
        gap_days: int = 30
    ) -> str:
        """
        Create temporal split with gaps to prevent leakage
        """
        
        sql = f"""
        CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_splits` AS
        
        WITH ordered_leads AS (
            SELECT
                lead_id,
                contacted_date,
                target,
                ROW_NUMBER() OVER (ORDER BY contacted_date) as row_num,
                COUNT(*) OVER () as total_rows
            FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit`
            WHERE target IS NOT NULL
              AND contacted_date >= '2024-02-01'  -- Apply date floor constraint
        ),
        
        split_boundaries AS (
            SELECT
                MAX(total_rows) as total_count,
                CAST(MAX(total_rows) * {train_pct} AS INT64) as train_end_idx,
                CAST(MAX(total_rows) * (1 - {test_pct}) AS INT64) as test_start_idx
            FROM ordered_leads
        ),
        
        train_end_date AS (
            SELECT contacted_date as train_end_date
            FROM ordered_leads ol
            CROSS JOIN split_boundaries sb
            WHERE ol.row_num = sb.train_end_idx
            LIMIT 1
        ),
        
        test_start_date AS (
            SELECT contacted_date as test_start_date
            FROM ordered_leads ol
            CROSS JOIN split_boundaries sb
            WHERE ol.row_num = sb.test_start_idx
            LIMIT 1
        ),
        
        val_start_date AS (
            SELECT DATE_ADD(t.train_end_date, INTERVAL {gap_days} DAY) as val_start_date
            FROM train_end_date t
        ),
        
        val_end_date AS (
            SELECT DATE_SUB(ts.test_start_date, INTERVAL {gap_days} DAY) as val_end_date
            FROM test_start_date ts
        ),
        
        split_dates AS (
            SELECT
                t.train_end_date,
                vs.val_start_date,
                v.val_end_date,
                ts.test_start_date
            FROM train_end_date t
            CROSS JOIN val_start_date vs
            CROSS JOIN val_end_date v
            CROSS JOIN test_start_date ts
        )
        
        SELECT
            f.lead_id,
            f.contacted_date,
            f.target,
            CASE
                WHEN f.contacted_date <= sd.train_end_date THEN 'TRAIN'
                WHEN f.contacted_date >= sd.val_start_date AND f.contacted_date <= sd.val_end_date THEN 'VALIDATION'
                WHEN f.contacted_date >= sd.test_start_date THEN 'TEST'
                ELSE 'GAP'  -- Leads in gap periods are excluded
            END as split,
            sd.train_end_date,
            sd.val_start_date,
            sd.val_end_date,
            sd.test_start_date
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
        CROSS JOIN split_dates sd
        WHERE f.target IS NOT NULL
          AND f.contacted_date >= '2024-02-01';  -- Apply date floor constraint
        """
        
        print("Creating temporal splits...")
        job = self.client.query(sql)
        job.result()
        print("[OK] Split table created!")
        return sql
    
    def validate_split_distribution(self) -> pd.DataFrame:
        """Validate class balance and sample sizes across splits"""
        query = """
        SELECT
            split,
            COUNT(*) as n_samples,
            SUM(target) as n_positive,
            ROUND(SUM(target) * 100.0 / COUNT(*), 2) as positive_rate_pct,
            MIN(contacted_date) as earliest_date,
            MAX(contacted_date) as latest_date
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
        WHERE split != 'GAP'
        GROUP BY split
        ORDER BY 
            CASE split 
                WHEN 'TRAIN' THEN 1 
                WHEN 'VALIDATION' THEN 2 
                WHEN 'TEST' THEN 3 
            END
        """
        return self.client.query(query).to_dataframe()
    
    def validate_temporal_integrity(self) -> pd.DataFrame:
        """Ensure no temporal overlap between splits"""
        query = """
        WITH split_ranges AS (
            SELECT
                split,
                MIN(contacted_date) as min_date,
                MAX(contacted_date) as max_date
            FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
            WHERE split != 'GAP'
            GROUP BY split
        ),
        train_range AS (
            SELECT * FROM split_ranges WHERE split = 'TRAIN'
        ),
        val_range AS (
            SELECT * FROM split_ranges WHERE split = 'VALIDATION'
        ),
        test_range AS (
            SELECT * FROM split_ranges WHERE split = 'TEST'
        )
        SELECT
            t.max_date as train_max,
            v.min_date as val_min,
            DATE_DIFF(v.min_date, t.max_date, DAY) as train_val_gap_days,
            ts.min_date as test_min,
            DATE_DIFF(ts.min_date, COALESCE(v.max_date, t.max_date), DAY) as val_test_gap_days
        FROM train_range t
        LEFT JOIN val_range v ON TRUE
        CROSS JOIN test_range ts
        """
        return self.client.query(query).to_dataframe()
    
    def get_split_date_ranges(self) -> dict:
        """Get date ranges for each split"""
        query = """
        SELECT
            split,
            MIN(contacted_date) as start_date,
            MAX(contacted_date) as end_date,
            COUNT(*) as count
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits`
        WHERE split != 'GAP'
        GROUP BY split
        ORDER BY 
            CASE split 
                WHEN 'TRAIN' THEN 1 
                WHEN 'VALIDATION' THEN 2 
                WHEN 'TEST' THEN 3 
            END
        """
        df = self.client.query(query).to_dataframe()
        return df.to_dict('records')
    
    def run_split_pipeline(self) -> dict:
        """Execute complete split pipeline with validation"""
        # Create splits
        self.create_temporal_split()
        
        # Validate distribution
        print("Validating distribution...")
        distribution = self.validate_split_distribution()
        
        # Validate temporal integrity
        print("Validating temporal integrity...")
        integrity = self.validate_temporal_integrity()
        
        # Get date ranges
        print("Getting split date ranges...")
        date_ranges = self.get_split_date_ranges()
        
        return {
            'distribution': distribution.to_dict('records'),
            'integrity': integrity.to_dict('records'),
            'date_ranges': date_ranges
        }


if __name__ == "__main__":
    splitter = TemporalSplitter()
    results = splitter.run_split_pipeline()
    
    print("\n" + "="*60)
    print("SPLIT DISTRIBUTION")
    print("="*60)
    dist_df = pd.DataFrame(results['distribution'])
    print(dist_df.to_string(index=False))
    
    print("\n" + "="*60)
    print("TEMPORAL INTEGRITY (Gap Validation)")
    print("="*60)
    integrity_df = pd.DataFrame(results['integrity'])
    print(integrity_df.to_string(index=False))
    
    print("\n" + "="*60)
    print("SPLIT DATE RANGES")
    print("="*60)
    for split_info in results['date_ranges']:
        print(f"{split_info['split']:12} | {split_info['start_date']} to {split_info['end_date']} | {split_info['count']:,} rows")
    
    print("\n[OK] Temporal Split Complete!")

