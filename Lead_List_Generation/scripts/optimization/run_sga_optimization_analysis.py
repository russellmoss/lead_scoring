"""
SGA Lead Distribution Optimization Analysis - Master Script
Executes all phases of the optimization analysis as outlined in the guide.

Usage: python scripts/optimization/run_sga_optimization_analysis.py
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from google.cloud import bigquery

# Add parent directory to path for imports
WORKING_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKING_DIR))

# Configuration
PROJECT_ID = "savvy-gtm-analytics"
DATASET_SALESFORCE = "SavvyGTMData"
DATASET_ML = "ml_features"

REPORTS_DIR = WORKING_DIR / "reports" / "sga_optimization"
DATA_DIR = REPORTS_DIR / "data"
FIGURES_DIR = REPORTS_DIR / "figures"
FINAL_DIR = REPORTS_DIR / "final"
SQL_DIR = WORKING_DIR / "sql" / "optimization"

# Ensure directories exist
for d in [DATA_DIR, FIGURES_DIR, FINAL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def log_to_analysis_log(message: str):
    """Append message to analysis log."""
    log_file = REPORTS_DIR / "ANALYSIS_LOG.md"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n### {timestamp} - {message}\n")
    print(f"[LOG] {message}")

def phase1_prospect_pool(client):
    """Phase 1: Prospect Pool Inventory Analysis"""
    print("\n" + "=" * 70)
    print("PHASE 1: PROSPECT POOL INVENTORY ANALYSIS")
    print("=" * 70)
    
    log_to_analysis_log("Starting Phase 1: Prospect Pool Inventory")
    
    # Read SQL query
    sql_file = SQL_DIR / "prospect_pool_inventory.sql"
    if not sql_file.exists():
        print(f"[ERROR] SQL file not found: {sql_file}")
        return None
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        query = f.read()
    
    # Execute query
    print("[INFO] Querying prospect pool inventory...")
    df = client.query(query).to_dataframe()
    
    # Save results
    output_file = DATA_DIR / "prospect_pool_inventory.csv"
    df.to_csv(output_file, index=False)
    print(f"[INFO] Saved to {output_file}")
    
    # Calculate sustainability metrics
    total_pool = df['prospect_count'].sum()
    monthly_usage = 3000  # 3,000 leads/month
    
    print(f"\nProspect Pool Summary:")
    print("-" * 70)
    print(f"{'Tier':<30} {'Count':>12} {'% of Total':>12} {'LinkedIn %':>12}")
    print("-" * 70)
    for _, row in df.iterrows():
        print(f"{row['estimated_tier']:<30} {row['prospect_count']:>12,} {row['pct_of_total']:>11.2f}% {row['linkedin_pct']:>11.1f}%")
    print("-" * 70)
    print(f"{'TOTAL':<30} {total_pool:>12,}")
    
    # Calculate months until depletion
    print(f"\nSustainability Analysis (at {monthly_usage:,} leads/month):")
    print("-" * 70)
    for _, row in df.iterrows():
        months = row['prospect_count'] / monthly_usage if monthly_usage > 0 else float('inf')
        status = "[OK]" if months >= 12 else "[WARN]" if months >= 6 else "[CRITICAL]"
        print(f"{row['estimated_tier']:<30} {months:>11.1f} months {status}")
    
    log_to_analysis_log(f"Phase 1 complete. Total pool: {total_pool:,} prospects")
    
    return df

def phase2_conversion_rates(client):
    """Phase 2: Historical Conversion Rate Analysis"""
    print("\n" + "=" * 70)
    print("PHASE 2: HISTORICAL CONVERSION RATE ANALYSIS")
    print("=" * 70)
    
    log_to_analysis_log("Starting Phase 2: Conversion Rate Analysis")
    
    # Query conversion rates with confidence intervals
    query = f"""
    WITH historical_leads AS (
        SELECT 
            l.Id as lead_id,
            l.stage_entered_contacting__c as contacted_date,
            l.MQL_Date__c,
            CASE WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL THEN 1 ELSE 0 END as converted,
            -- Get tier from January 2026 list (most recent)
            COALESCE(ll.score_tier, 'UNKNOWN') as score_tier
        FROM `{PROJECT_ID}.{DATASET_SALESFORCE}.Lead` l
        LEFT JOIN `{PROJECT_ID}.{DATASET_ML}.january_2026_lead_list_v4` ll
            ON CAST(REGEXP_REPLACE(CAST(l.FA_CRD__c AS STRING), r'[^0-9]', '') AS INT64) = ll.advisor_crd
        WHERE l.LeadSource LIKE '%Provided Lead List%'
          AND DATE(l.stage_entered_contacting__c) >= '2024-01-01'
          AND DATE(l.stage_entered_contacting__c) <= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
          AND l.FA_CRD__c IS NOT NULL
    ),
    
    tier_stats AS (
        SELECT 
            score_tier,
            COUNT(*) as n,
            SUM(converted) as successes,
            AVG(converted) as conversion_rate
        FROM historical_leads
        WHERE score_tier != 'UNKNOWN'
        GROUP BY score_tier
        HAVING COUNT(*) >= 50  -- Minimum sample size
    )
    
    SELECT 
        score_tier,
        n,
        successes,
        ROUND(conversion_rate * 100, 2) as conversion_rate_pct,
        
        -- Wilson score 95% confidence interval (lower)
        ROUND((
            (conversion_rate + 1.96*1.96/(2*n) - 1.96 * SQRT((conversion_rate*(1-conversion_rate) + 1.96*1.96/(4*n))/n))
            / (1 + 1.96*1.96/n)
        ) * 100, 2) as ci_lower_pct,
        
        -- Wilson score 95% confidence interval (upper)
        ROUND((
            (conversion_rate + 1.96*1.96/(2*n) + 1.96 * SQRT((conversion_rate*(1-conversion_rate) + 1.96*1.96/(4*n))/n))
            / (1 + 1.96*1.96/n)
        ) * 100, 2) as ci_upper_pct,
        
        -- Lift vs baseline (3.24% from historical)
        ROUND(conversion_rate / 0.0324, 2) as lift_vs_baseline
        
    FROM tier_stats
    ORDER BY conversion_rate DESC
    """
    
    print("[INFO] Querying historical conversion rates...")
    df = client.query(query).to_dataframe()
    
    # Save results
    output_file = DATA_DIR / "tier_conversion_rates.csv"
    df.to_csv(output_file, index=False)
    print(f"[INFO] Saved to {output_file}")
    
    print(f"\nConversion Rates by Tier:")
    print("-" * 70)
    print(f"{'Tier':<30} {'Leads':>10} {'Conv':>8} {'Rate':>8} {'CI (95%)':>20} {'Lift':>8}")
    print("-" * 70)
    for _, row in df.iterrows():
        print(f"{row['score_tier']:<30} {row['n']:>10,} {row['successes']:>8,} {row['conversion_rate_pct']:>7.2f}% "
              f"[{row['ci_lower_pct']:.2f}-{row['ci_upper_pct']:.2f}%] {row['lift_vs_baseline']:>7.2f}x")
    
    log_to_analysis_log(f"Phase 2 complete. Analyzed {len(df)} tiers")
    
    return df

def main():
    """Main execution function"""
    print("=" * 70)
    print("SGA LEAD DISTRIBUTION OPTIMIZATION ANALYSIS")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    client = bigquery.Client(project=PROJECT_ID)
    
    # Phase 1: Prospect Pool
    pool_df = phase1_prospect_pool(client)
    
    # Phase 2: Conversion Rates
    conversion_df = phase2_conversion_rates(client)
    
    print("\n" + "=" * 70)
    print("ANALYSIS IN PROGRESS")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Review Phase 1 & 2 results in reports/sga_optimization/data/")
    print("2. Continue with Phase 3-7 using the guide")
    print("3. See ANALYSIS_LOG.md for detailed progress")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

