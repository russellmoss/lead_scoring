"""
temporal_backtest.py
--------------------
Simulates a deployment in the past to verify model stability over time.
"""
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score, average_precision_score
from google.cloud import bigquery
import matplotlib.pyplot as plt
import numpy as np

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("Initiating Temporal Backtest (The 'Time Machine')...")

# 1. Fetch Historical Data AND Target Label (Joined with Salesforce)
# Also check what dates exist in the raw Leads table
print("   Checking date ranges in source tables...")
date_check_query = """
SELECT 
    MIN(DATE(CreatedDate)) as min_lead_date,
    MAX(DATE(CreatedDate)) as max_lead_date,
    COUNT(*) as total_leads
FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
WHERE CreatedDate >= '2024-01-01'
"""
date_info = client.query(date_check_query).to_dataframe()
print(f"   Salesforce Leads table: {date_info['min_lead_date'].iloc[0]} to {date_info['max_lead_date'].iloc[0]} ({date_info['total_leads'].iloc[0]:,} leads since 2024)")

query = """
SELECT 
    f.*,
    -- Get the Target Label from Salesforce
    CAST(l.IsConverted AS INT64) as is_converted
FROM `savvy-gtm-analytics.ml_features.lead_scoring_features` f
JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
    ON f.lead_id = l.Id
WHERE f.contacted_date IS NOT NULL
"""

print("   Fetching data with targets...")
df = client.query(query).to_dataframe()
df['contacted_date'] = pd.to_datetime(df['contacted_date'])

# Check available date range
min_date = df['contacted_date'].min()
max_date = df['contacted_date'].max()
total_leads = len(df)
print(f"   Total leads fetched: {total_leads:,}")
print(f"   Date range in data: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")

# Show distribution by year-month
df['year_month'] = df['contacted_date'].dt.to_period('M')
monthly_counts = df['year_month'].value_counts().sort_index()
print(f"\n   Leads by month (last 12 months):")
for period, count in list(monthly_counts.tail(12).items()):
    print(f"      {period}: {count:,} leads")

# 2. The Split: June 1st, 2025
# Train on all data before June 2025, test on June-December 2025
SPLIT_DATE = '2025-06-01'
SPLIT_DATE_DT = pd.to_datetime(SPLIT_DATE)

train = df[df['contacted_date'] < SPLIT_DATE_DT].copy()
test = df[df['contacted_date'] >= SPLIT_DATE_DT].copy()

print(f"\n[Training] Training on {len(train)} leads (Pre-{SPLIT_DATE})")
print(f"[Testing] Testing on {len(test)} leads (Post-{SPLIT_DATE})")

# Check if we have test data
if len(test) == 0:
    print(f"\n[ERROR] No test data available!")
    print(f"   Latest date in dataset: {max_date.strftime('%Y-%m-%d')}")
    print(f"   Split date requested: {SPLIT_DATE}")
    
    # Suggest a split date that gives ~6 months of test data
    suggested_split = max_date - pd.Timedelta(days=180)
    if suggested_split > min_date:
        print(f"\n💡 Suggestion: Use a split date like: {suggested_split.strftime('%Y-%m-%d')}")
        print(f"   This would give ~6 months of test data.")
        print(f"   Update SPLIT_DATE in the script to: '{suggested_split.strftime('%Y-%m-%d')}'")
    else:
        print(f"\n[WARNING] Dataset too small for temporal split (only {len(df)} total leads)")
    exit(1)

# 3. Engineer Features (Re-applying the 'Boost' logic)
def engineer_features(data):
    # Ensure columns are numeric, filling NaNs with 0
    data['pit_moves_3yr'] = pd.to_numeric(data['pit_moves_3yr'], errors='coerce').fillna(0)
    data['firm_net_change_12mo'] = pd.to_numeric(data['firm_net_change_12mo'], errors='coerce').fillna(0)
    data['current_firm_tenure_months'] = pd.to_numeric(data['current_firm_tenure_months'], errors='coerce').fillna(0)
    data['industry_tenure_months'] = pd.to_numeric(data['industry_tenure_months'], errors='coerce').fillna(1) # Avoid div/0
    data['num_prior_firms'] = pd.to_numeric(data['num_prior_firms'], errors='coerce').fillna(0)
    data['firm_aum_pit'] = pd.to_numeric(data['firm_aum_pit'], errors='coerce').fillna(0)

    # Calculate Boosters
    data['flight_risk_score'] = data['pit_moves_3yr'] * (data['firm_net_change_12mo'] * -1)
    
    # Restlessness (Avoid division by zero)
    # Calculate avg_prior_firm_tenure first
    avg_prior_tenure = (data['industry_tenure_months'] - data['current_firm_tenure_months']) / data['num_prior_firms'].replace(0, 1)
    avg_prior_tenure = avg_prior_tenure.clip(lower=0.1)  # Ensure minimum denominator
    
    # Calculate restlessness ratio (avoid division by zero)
    data['pit_restlessness_ratio'] = data['current_firm_tenure_months'] / avg_prior_tenure
    
    # Replace inf and NaN with reasonable defaults
    data['pit_restlessness_ratio'] = data['pit_restlessness_ratio'].replace([np.inf, -np.inf], 0).fillna(0)
    data['flight_risk_score'] = data['flight_risk_score'].replace([np.inf, -np.inf], 0).fillna(0)
    
    # Clip extreme values to prevent overflow
    data['pit_restlessness_ratio'] = data['pit_restlessness_ratio'].clip(upper=1000, lower=-1000)
    data['flight_risk_score'] = data['flight_risk_score'].clip(upper=1000, lower=-1000)
    data['firm_net_change_12mo'] = data['firm_net_change_12mo'].clip(upper=100, lower=-100)
    
    return data

train = engineer_features(train)
test = engineer_features(test)

# 4. Train the Model (Simulating the past)
features = [
    'flight_risk_score', 'pit_restlessness_ratio', 'current_firm_tenure_months',
    'firm_net_change_12mo', 'pit_moves_3yr', 'firm_aum_pit'
]
target = 'is_converted'

# Final data cleaning: Ensure no inf or NaN in features
print("   Cleaning data (removing inf/NaN)...")
for feature in features:
    # Replace inf with NaN, then fill with 0
    train[feature] = train[feature].replace([np.inf, -np.inf], np.nan).fillna(0)
    test[feature] = test[feature].replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Verify no remaining inf or NaN
    if train[feature].isin([np.inf, -np.inf]).any() or train[feature].isna().any():
        print(f"   Warning: {feature} still has inf/NaN in training set")
    if test[feature].isin([np.inf, -np.inf]).any() or test[feature].isna().any():
        print(f"   Warning: {feature} still has inf/NaN in test set")

# Check if we have enough training data
if len(train) < 100:
    print(f"\n[ERROR] Insufficient training data ({len(train)} leads)")
    print(f"   Need at least 100 leads for meaningful model training.")
    exit(1)

print("   Training 'Past' Model...")
model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss')
model.fit(train[features], train[target])

# 5. Predict the "Future" (The Test Set)
probs = model.predict_proba(test[features])[:, 1]
test['score'] = probs

# 6. Evaluate
roc = roc_auc_score(test[target], test['score'])
baseline_conv = test[target].mean()

# Calculate Lift (Top 10%)
top_decile_threshold = test['score'].quantile(0.9)
top_decile = test[test['score'] >= top_decile_threshold]
top_conv = top_decile[target].mean()
lift = top_conv / baseline_conv if baseline_conv > 0 else 0

print(f"\n[TEMPORAL RESULTS] If we launched on June 1st, 2025:")
print(f"   - Test AUC: {roc:.4f}")
print(f"   - Lift: {lift:.2f}x")
print(f"   - Baseline Conversion: {baseline_conv:.2%}")
print(f"   - Top Decile Conversion: {top_conv:.2%}")

if lift > 2.0:
    print("\n[VERDICT: PASSED] The model predicts the future successfully.")
else:
    print("\n[VERDICT: FAILED] The model relies on short-term correlations.")