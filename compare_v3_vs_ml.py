# compare_v3_vs_ml.py
# Compare the final V3 tier rules vs XGBoost ML

import sys
import warnings
warnings.filterwarnings("ignore")

print("=" * 70)
print("V3 FINAL TIERS vs XGBOOST ML - HEAD TO HEAD")
print("=" * 70)

from google.cloud import bigquery
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"

client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

# =============================================================================
# FETCH DATA
# =============================================================================

print("\n[1/4] Fetching scored data...")

query = """
SELECT
    lead_id,
    contacted_date,
    tier_rank,
    tier_name,
    expected_lift,
    
    -- Features for ML
    tenure_years,
    experience_years,
    firm_net_change_12mo,
    COALESCE(firm_rep_count_at_contact, 0) as firm_rep_count,
    pit_moves_3yr,
    CAST(is_wirehouse AS INT64) as is_wirehouse,
    CAST(has_firm_size_data AS INT64) as has_firm_size_data,
    
    -- Outcome
    converted

FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_final`
WHERE contacted_date >= '2024-02-01'
  AND contacted_date <= '2025-09-01'
"""

df = client.query(query).to_dataframe()
print("      Done - Loaded {:,} leads".format(len(df)))

# =============================================================================
# TEMPORAL SPLIT
# =============================================================================

print("\n[2/4] Setting up temporal split...")

df_sorted = df.sort_values("contacted_date")
split_idx = int(len(df_sorted) * 0.7)

train = df_sorted.iloc[:split_idx]
test = df_sorted.iloc[split_idx:]

print("      Train: {:,} leads ({:,} conversions)".format(
    len(train), int(train['converted'].sum())
))
print("      Test:  {:,} leads ({:,} conversions)".format(
    len(test), int(test['converted'].sum())
))

# =============================================================================
# CALCULATE LIFT FUNCTION
# =============================================================================

def calculate_top_decile_lift(y_true, y_scores):
    df_temp = pd.DataFrame({"true": y_true, "score": y_scores})
    df_temp = df_temp.sort_values("score", ascending=False)
    
    n_decile = len(df_temp) // 10
    if n_decile == 0:
        return 0.0
    
    top_decile = df_temp.head(n_decile)
    top_decile_rate = top_decile["true"].mean()
    baseline_rate = df_temp["true"].mean()
    
    if baseline_rate == 0:
        return 0.0
    
    return top_decile_rate / baseline_rate


# =============================================================================
# METHOD 1: V3 TIER RULES
# =============================================================================

print("\n[3/4] Evaluating methods...")

# For V3, score = inverse of tier_rank (lower tier = higher priority)
test_v3_scores = 100 - test["tier_rank"].values

v3_lift = calculate_top_decile_lift(test["converted"].values, test_v3_scores)
print("      V3 Rules Lift: {:.2f}x".format(v3_lift))

# =============================================================================
# METHOD 2: RAW XGBOOST
# =============================================================================

raw_features = [
    "tenure_years", "experience_years", "firm_net_change_12mo",
    "firm_rep_count", "pit_moves_3yr", "is_wirehouse"
]

X_train = train[raw_features].fillna(0)
X_test = test[raw_features].fillna(0)
y_train = train["converted"].values
y_test = test["converted"].values

pos_count = y_train.sum()
neg_count = len(y_train) - pos_count
scale_pos_weight = neg_count / max(pos_count, 1)

model_raw = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    verbosity=0
)
model_raw.fit(X_train, y_train)

preds_raw = model_raw.predict_proba(X_test)[:, 1]
raw_lift = calculate_top_decile_lift(y_test, preds_raw)
print("      Raw XGBoost Lift: {:.2f}x".format(raw_lift))

# =============================================================================
# METHOD 3: HYBRID (ML + RULES)
# =============================================================================

# Add tier as a feature
hybrid_features = raw_features + ["tier_rank", "expected_lift"]

X_train_hybrid = train[hybrid_features].fillna(0)
X_test_hybrid = test[hybrid_features].fillna(0)

model_hybrid = XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    verbosity=0
)
model_hybrid.fit(X_train_hybrid, y_train)

preds_hybrid = model_hybrid.predict_proba(X_test_hybrid)[:, 1]
hybrid_lift = calculate_top_decile_lift(y_test, preds_hybrid)
print("      Hybrid Lift: {:.2f}x".format(hybrid_lift))

# =============================================================================
# RESULTS
# =============================================================================

print("\n[4/4] Final Results...")
print("")
print("=" * 70)
print("HEAD-TO-HEAD COMPARISON")
print("=" * 70)
print("")
print("{:<30} {:>15}".format("Method", "Top Decile Lift"))
print("-" * 45)
print("{:<30} {:>14.2f}x".format("V3 Final Tier Rules", v3_lift))
print("{:<30} {:>14.2f}x".format("Raw XGBoost", raw_lift))
print("{:<30} {:>14.2f}x".format("Hybrid (ML + Rules)", hybrid_lift))
print("-" * 45)

# Determine winner
lifts = {
    "V3 Rules": v3_lift,
    "Raw XGBoost": raw_lift,
    "Hybrid": hybrid_lift
}
winner = max(lifts, key=lifts.get)

print("")
print("** WINNER: {} ({:.2f}x) **".format(winner, lifts[winner]))

if winner == "V3 Rules":
    print("")
    print("[SUCCESS] V3 tier rules outperform ML!")
    print("   Stick with rules-based approach for simplicity and interpretability.")
elif winner == "Hybrid":
    improvement = hybrid_lift - v3_lift
    print("")
    if improvement > 0.3:
        print("[OK] Hybrid improves by {:.2f}x over rules alone.".format(improvement))
        print("   Consider using hybrid approach for additional lift.")
    else:
        print("[NOTE] Hybrid only improves by {:.2f}x.".format(improvement))
        print("   Marginal gain - rules-only is simpler and nearly as good.")
else:
    print("")
    print("[INVESTIGATE] Raw XGBoost beats rules by {:.2f}x".format(raw_lift - v3_lift))
    print("   ML may be finding patterns not captured in tier rules.")

# Feature importance from hybrid
print("")
print("-" * 45)
print("HYBRID MODEL FEATURE IMPORTANCE:")
print("-" * 45)

importance = pd.DataFrame({
    "feature": hybrid_features,
    "importance": model_hybrid.feature_importances_
}).sort_values("importance", ascending=False)

for _, row in importance.iterrows():
    bar = "*" * int(row['importance'] * 50)
    print("{:<20} {:.3f} {}".format(row['feature'], row['importance'], bar))

print("")
print("=" * 70)
print("DONE")
print("=" * 70)
