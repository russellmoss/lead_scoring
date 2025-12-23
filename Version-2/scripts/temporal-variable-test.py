# File: C:\Users\russe\Documents\Lead Scoring\Version-2\scripts\temporal_velocity_diagnostic.py

import sys
from pathlib import Path
VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

import pandas as pd
import numpy as np
from google.cloud import bigquery
from sklearn.metrics import roc_auc_score
import warnings
warnings.filterwarnings('ignore')

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("=" * 70)
print("TEMPORAL VELOCITY FEATURE EXPLORATION")
print("=" * 70)

# =============================================================================
# STEP 1: Understand the Employment History Data
# =============================================================================
print("\n" + "=" * 60)
print("STEP 1: EMPLOYMENT HISTORY DATA EXPLORATION")
print("=" * 60)

# Check the structure of employment history
query_structure = """
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT RIA_CONTACT_CRD_ID) as unique_advisors,
    ROUND(COUNT(*) / COUNT(DISTINCT RIA_CONTACT_CRD_ID), 2) as avg_jobs_per_advisor,
    
    -- Date coverage
    MIN(PREVIOUS_REGISTRATION_COMPANY_START_DATE) as earliest_start,
    MAX(PREVIOUS_REGISTRATION_COMPANY_START_DATE) as latest_start,
    
    -- NULL analysis
    ROUND(COUNTIF(PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL) * 100.0 / COUNT(*), 1) as pct_current_jobs
    
FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
"""

result = client.query(query_structure).result().to_dataframe()
print(f"\nEmployment History Overview:")
print(f"  Total records: {result['total_records'].iloc[0]:,}")
print(f"  Unique advisors: {result['unique_advisors'].iloc[0]:,}")
print(f"  Avg jobs per advisor: {result['avg_jobs_per_advisor'].iloc[0]}")
print(f"  Date range: {result['earliest_start'].iloc[0]} to {result['latest_start'].iloc[0]}")
print(f"  Current jobs (end_date NULL): {result['pct_current_jobs'].iloc[0]}%")

# =============================================================================
# STEP 2: Calculate Velocity Features for a Sample
# =============================================================================
print("\n" + "=" * 60)
print("STEP 2: CALCULATE VELOCITY FEATURES")
print("=" * 60)

# Get leads with their employment history
velocity_query = """
WITH leads AS (
    -- Get 2024 leads from our splits table
    SELECT DISTINCT
        lead_id,
        advisor_crd,
        contacted_date,
        target
    FROM `savvy-gtm-analytics.ml_features.lead_scoring_splits_v2`
    WHERE EXTRACT(YEAR FROM contacted_date) = 2024
      AND advisor_crd IS NOT NULL
),

employment_history AS (
    -- Get employment history ordered by start date
    SELECT 
        RIA_CONTACT_CRD_ID as advisor_crd,
        PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd,
        PREVIOUS_REGISTRATION_COMPANY_START_DATE as start_date,
        PREVIOUS_REGISTRATION_COMPANY_END_DATE as end_date,
        -- Calculate tenure at this job
        DATE_DIFF(
            COALESCE(PREVIOUS_REGISTRATION_COMPANY_END_DATE, CURRENT_DATE()),
            PREVIOUS_REGISTRATION_COMPANY_START_DATE,
            DAY
        ) as tenure_days
    FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history`
    WHERE PREVIOUS_REGISTRATION_COMPANY_START_DATE IS NOT NULL
),

-- For each lead, get their job history as of contact date
lead_job_history AS (
    SELECT 
        l.lead_id,
        l.advisor_crd,
        l.contacted_date,
        l.target,
        eh.firm_crd,
        eh.start_date,
        eh.end_date,
        eh.tenure_days,
        -- Is this job current as of contact date?
        CASE 
            WHEN eh.end_date IS NULL OR eh.end_date >= l.contacted_date 
            THEN TRUE ELSE FALSE 
        END as is_current,
        -- Job sequence number (most recent = 1)
        ROW_NUMBER() OVER (
            PARTITION BY l.lead_id 
            ORDER BY eh.start_date DESC
        ) as job_seq
    FROM leads l
    INNER JOIN employment_history eh ON l.advisor_crd = eh.advisor_crd
    WHERE eh.start_date <= l.contacted_date  -- Only jobs started before contact
),

-- Calculate velocity features per lead
velocity_features AS (
    SELECT 
        lead_id,
        advisor_crd,
        contacted_date,
        target,
        
        -- Total jobs as of contact date
        COUNT(*) as total_jobs,
        
        -- Days since last move (if they have multiple jobs)
        MAX(CASE 
            WHEN job_seq = 2 AND end_date IS NOT NULL 
            THEN DATE_DIFF(contacted_date, end_date, DAY)
            ELSE NULL 
        END) as days_since_last_move,
        
        -- Current job tenure (days)
        MAX(CASE WHEN is_current THEN tenure_days ELSE NULL END) as current_tenure_days,
        
        -- Average prior job tenure (excluding current)
        AVG(CASE WHEN NOT is_current THEN tenure_days ELSE NULL END) as avg_prior_tenure_days,
        
        -- Most recent prior job tenure
        MAX(CASE WHEN job_seq = 2 THEN tenure_days ELSE NULL END) as prior_job_tenure_days,
        
        -- Second most recent prior job tenure (for acceleration calc)
        MAX(CASE WHEN job_seq = 3 THEN tenure_days ELSE NULL END) as second_prior_job_tenure_days,
        
        -- Number of moves in last 3 years (we already have this, but recalc for verification)
        COUNTIF(
            end_date >= DATE_SUB(contacted_date, INTERVAL 3 YEAR)
            AND end_date < contacted_date
        ) as moves_3yr_verified
        
    FROM lead_job_history
    GROUP BY lead_id, advisor_crd, contacted_date, target
)

SELECT 
    *,
    
    -- Tenure Decay Ratio: current / avg prior (>1 means staying longer than usual)
    CASE 
        WHEN avg_prior_tenure_days > 30 
        THEN ROUND(current_tenure_days / avg_prior_tenure_days, 2)
        ELSE NULL 
    END as tenure_decay_ratio,
    
    -- Move Acceleration: are they moving faster? (prior_tenure / second_prior_tenure)
    -- <1 means accelerating (staying shorter at each job)
    CASE 
        WHEN second_prior_job_tenure_days > 30 
        THEN ROUND(prior_job_tenure_days / second_prior_job_tenure_days, 2)
        ELSE NULL 
    END as move_acceleration_ratio,
    
    -- Recency Tier
    CASE 
        WHEN days_since_last_move IS NULL THEN 'No Prior Moves'
        WHEN days_since_last_move < 180 THEN 'Very Recent (< 6mo)'
        WHEN days_since_last_move < 365 THEN 'Recent (6-12mo)'
        WHEN days_since_last_move < 730 THEN 'Moderate (1-2yr)'
        ELSE 'Distant (> 2yr)'
    END as recency_tier

FROM velocity_features
"""

print("\nCalculating velocity features for 2024 leads...")
df = client.query(velocity_query).result().to_dataframe()
print(f"✅ Calculated for {len(df):,} leads")

# =============================================================================
# STEP 3: Analyze Feature Distributions
# =============================================================================
print("\n" + "=" * 60)
print("STEP 3: FEATURE DISTRIBUTIONS")
print("=" * 60)

print(f"\ndays_since_last_move:")
print(f"  Non-null: {df['days_since_last_move'].notna().sum():,} ({df['days_since_last_move'].notna().mean()*100:.1f}%)")
print(f"  Mean: {df['days_since_last_move'].mean():.0f} days")
print(f"  Median: {df['days_since_last_move'].median():.0f} days")

print(f"\ntenure_decay_ratio:")
print(f"  Non-null: {df['tenure_decay_ratio'].notna().sum():,} ({df['tenure_decay_ratio'].notna().mean()*100:.1f}%)")
print(f"  Mean: {df['tenure_decay_ratio'].mean():.2f}")
print(f"  < 1.0 (staying shorter): {(df['tenure_decay_ratio'] < 1.0).sum():,}")
print(f"  > 1.0 (staying longer): {(df['tenure_decay_ratio'] > 1.0).sum():,}")

print(f"\nRecency Tier Distribution:")
print(df['recency_tier'].value_counts())

# =============================================================================
# STEP 4: Signal Strength Analysis
# =============================================================================
print("\n" + "=" * 60)
print("STEP 4: SIGNAL STRENGTH BY TARGET")
print("=" * 60)

# days_since_last_move by target
print("\ndays_since_last_move by Target:")
for target in [0, 1]:
    subset = df[df['target'] == target]['days_since_last_move'].dropna()
    print(f"  Target={target}: Mean={subset.mean():.0f}, Median={subset.median():.0f}")

# Recency tier by target
print("\nConversion Rate by Recency Tier:")
tier_analysis = df.groupby('recency_tier').agg({
    'target': ['count', 'sum', 'mean']
}).round(4)
tier_analysis.columns = ['count', 'conversions', 'conv_rate']
tier_analysis = tier_analysis.sort_values('conv_rate', ascending=False)
print(tier_analysis.to_string())

# tenure_decay_ratio by target
print("\ntenure_decay_ratio by Target:")
for target in [0, 1]:
    subset = df[df['target'] == target]['tenure_decay_ratio'].dropna()
    print(f"  Target={target}: Mean={subset.mean():.2f}, < 1.0 (accelerating): {(subset < 1.0).mean()*100:.1f}%")

# =============================================================================
# STEP 5: Univariate Predictive Power
# =============================================================================
print("\n" + "=" * 60)
print("STEP 5: UNIVARIATE PREDICTIVE POWER")
print("=" * 60)

velocity_features = [
    'days_since_last_move',
    'tenure_decay_ratio',
    'current_tenure_days',
    'avg_prior_tenure_days',
    'total_jobs',
    'moves_3yr_verified'
]

print("\nFeature AUC-ROC (higher = more predictive):")
for feat in velocity_features:
    if feat in df.columns:
        # Handle direction (some features should be negated)
        valid = df[['target', feat]].dropna()
        if len(valid) > 100:
            feat_vals = valid[feat]
            # For days_since_last_move, LOWER is better (more recent = hotter)
            if feat == 'days_since_last_move':
                feat_vals = -feat_vals
            # For tenure_decay_ratio, LOWER is better (accelerating)
            if feat == 'tenure_decay_ratio':
                feat_vals = -feat_vals
            try:
                auc = roc_auc_score(valid['target'], feat_vals)
                signal = "🔥" if auc > 0.55 else "✅" if auc > 0.52 else "⚠️"
                print(f"  {signal} {feat}: {auc:.4f} (n={len(valid):,})")
            except:
                print(f"  ❌ {feat}: Could not calculate")

# =============================================================================
# STEP 6: Create Bins and Test Lift
# =============================================================================
print("\n" + "=" * 60)
print("STEP 6: LIFT BY RECENCY (days_since_last_move)")
print("=" * 60)

# Only for leads with prior moves
has_moves = df[df['days_since_last_move'].notna()].copy()

if len(has_moves) > 100:
    # Create deciles based on recency
    has_moves['recency_decile'] = pd.qcut(
        has_moves['days_since_last_move'].rank(method='first'), 
        10, 
        labels=False,
        duplicates='drop'
    )
    
    # Calculate conversion by decile (0 = most recent, 9 = least recent)
    decile_analysis = has_moves.groupby('recency_decile').agg({
        'target': ['count', 'mean'],
        'days_since_last_move': ['min', 'max']
    }).round(4)
    decile_analysis.columns = ['count', 'conv_rate', 'min_days', 'max_days']
    
    base_rate = has_moves['target'].mean()
    decile_analysis['lift'] = (decile_analysis['conv_rate'] / base_rate).round(2)
    
    print(f"\nBase rate for advisors with prior moves: {base_rate*100:.2f}%")
    print("\nConversion by Recency Decile (0=Most Recent Move):")
    print(decile_analysis.to_string())
    
    # Most vs least recent comparison
    most_recent = has_moves[has_moves['recency_decile'] == 0]
    least_recent = has_moves[has_moves['recency_decile'] == has_moves['recency_decile'].max()]
    
    if len(most_recent) > 0 and len(least_recent) > 0:
        lift_diff = most_recent['target'].mean() / max(least_recent['target'].mean(), 0.001)
        print(f"\n🔥 Most Recent vs Least Recent Lift: {lift_diff:.2f}x")

# =============================================================================
# STEP 7: Recommendations
# =============================================================================
print("\n" + "=" * 60)
print("RECOMMENDATIONS")
print("=" * 60)

print("""
Based on this analysis, consider adding these features:

1. RECENCY FEATURES (if days_since_last_move has signal):
   - days_since_last_move (continuous, log-transform)
   - recency_tier (categorical: Very Recent, Recent, Moderate, Distant, No Prior)
   - is_recent_mover (binary: moved in last 12 months)

2. VELOCITY FEATURES (if tenure_decay_ratio has signal):
   - tenure_decay_ratio (current_tenure / avg_prior_tenure)
   - is_accelerating (binary: tenure_decay_ratio < 1.0)
   - move_acceleration_ratio (are moves speeding up?)

3. TRAJECTORY FEATURES (requires firm type data):
   - firm_prestige_trajectory (moving up or down market)
   - aum_trajectory (moving to smaller or larger firm)

To implement:
1. Add these features to the BigQuery feature table
2. Retrain model with velocity features
3. Expect 0.1-0.3x lift improvement from recency alone

⚠️ LEAKAGE WARNING:
   - days_since_last_move uses END_DATE which may be backfilled
   - Only use for leads where the advisor had COMPLETED a move before contact
   - Do NOT use if the "move" completed AFTER contact date
""")

# =============================================================================
# STEP 8: Save Results
# =============================================================================
output_path = VERSION_2_DIR / 'reports' / 'temporal_velocity_analysis.csv'
df.to_csv(output_path, index=False)
print(f"\n✅ Results saved to: {output_path}")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)