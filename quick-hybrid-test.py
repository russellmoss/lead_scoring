# quick_hybrid_test.py
# Compare: Raw XGBoost vs Rules vs Hybrid
# Usage: python quick_hybrid_test.py

import sys
import warnings
warnings.filterwarnings("ignore")

print("=" * 70)
print("HYBRID MODEL COMPARISON TEST")
print("=" * 70)
print("")
print("[1/6] Loading libraries...")

try:
    import pandas as pd
    import numpy as np
    from google.cloud import bigquery
    from xgboost import XGBClassifier
    from sklearn.metrics import average_precision_score, roc_auc_score
    print("      Done - All libraries loaded")
except ImportError as e:
    print("      ERROR - Missing library: " + str(e))
    print("")
    print("      Run: pip install pandas numpy google-cloud-bigquery xgboost scikit-learn")
    sys.exit(1)

PROJECT_ID = "savvy-gtm-analytics"
LOCATION = "northamerica-northeast2"

WIREHOUSE_PATTERNS = [
    "MERRILL", "MORGAN STANLEY", "UBS", "WELLS FARGO", "EDWARD JONES",
    "RAYMOND JAMES", "AMERIPRISE", "LPL", "NORTHWESTERN MUTUAL",
    "STIFEL", "RBC", "JANNEY", "BAIRD", "OPPENHEIMER"
]


def fetch_training_data(client):
    query = """
    WITH lead_features AS (
        SELECT 
            f.lead_id,
            f.advisor_crd,
            f.contacted_date,
            -- firm_rep_count_at_contact is not available in Version-3 (always NULL)
            -- Using firm_aum_pit as a proxy: if AUM < 100M, likely small firm
            CASE 
                WHEN f.firm_aum_pit IS NULL OR f.firm_aum_pit = 0 THEN 0
                WHEN f.firm_aum_pit < 100000000 THEN 5  -- Proxy: small firm (< 100M AUM)
                ELSE 50  -- Proxy: larger firm
            END as firm_rep_count,
            COALESCE(f.current_firm_tenure_months, 0) as current_firm_tenure_months,
            COALESCE(f.industry_tenure_months, 0) as industry_tenure_months,
            COALESCE(f.firm_net_change_12mo, 0) as firm_net_change_12mo,
            COALESCE(f.pit_moves_3yr, 0) as pit_moves_3yr,
            COALESCE(f.num_prior_firms, 0) as num_prior_firms,
            COALESCE(f.firm_aum_pit, 0) as firm_aum_pit,
            -- aum_growth_12mo_pct not available in table, setting to 0
            0 as aum_growth_pct,
            l.Company as company_name,
            -- Use the target column that's already calculated in the table
            COALESCE(f.target, 0) as converted
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
        INNER JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l
            ON f.lead_id = l.Id
        WHERE f.contacted_date >= '2024-02-01'
          AND f.contacted_date <= '2025-09-01'
    )
    SELECT * FROM lead_features
    WHERE lead_id IS NOT NULL
    """
    
    print("")
    print("[2/6] Fetching data from BigQuery...")
    print("      Project: " + PROJECT_ID)
    
    df = client.query(query).to_dataframe()
    n_leads = len(df)
    n_conv = int(df["converted"].sum())
    conv_rate = df["converted"].mean() * 100
    print("      Done - Fetched {:,} leads".format(n_leads))
    print("      Done - Conversions: {:,} ({:.2f}%)".format(n_conv, conv_rate))
    return df


def is_wirehouse(company_name):
    if pd.isna(company_name):
        return False
    company_upper = str(company_name).upper()
    for pattern in WIREHOUSE_PATTERNS:
        if pattern in company_upper:
            return True
    return False


def engineer_hybrid_features(df):
    print("")
    print("[3/6] Engineering hybrid features...")
    
    result = df.copy()
    
    result["tenure_years"] = result["current_firm_tenure_months"] / 12.0
    result["experience_years"] = result["industry_tenure_months"] / 12.0
    result["is_wirehouse"] = result["company_name"].apply(is_wirehouse).astype(int)
    
    # Tier 1: SGA Platinum components
    result["rule_small_firm"] = (result["firm_rep_count"] <= 10).astype(int)
    result["rule_sweet_tenure"] = ((result["tenure_years"] >= 4) & (result["tenure_years"] <= 10)).astype(int)
    result["rule_experienced"] = ((result["experience_years"] >= 8) & (result["experience_years"] <= 30)).astype(int)
    result["rule_not_wirehouse"] = (1 - result["is_wirehouse"]).astype(int)
    
    # Tier 2: Danger Zone components
    result["rule_danger_zone_tenure"] = ((result["tenure_years"] >= 1) & (result["tenure_years"] <= 2)).astype(int)
    result["rule_bleeding_firm"] = (result["firm_net_change_12mo"] < -5).astype(int)
    result["rule_veteran"] = (result["experience_years"] >= 10).astype(int)
    
    # Composite rules
    result["rule_platinum_all"] = (
        (result["rule_small_firm"] == 1) & 
        (result["rule_sweet_tenure"] == 1) & 
        (result["rule_experienced"] == 1) & 
        (result["rule_not_wirehouse"] == 1)
    ).astype(int)
    
    result["rule_dz_all"] = (
        (result["rule_danger_zone_tenure"] == 1) & 
        (result["rule_bleeding_firm"] == 1) & 
        (result["rule_veteran"] == 1)
    ).astype(int)
    
    # Tier assignment
    def assign_tier(row):
        if row["rule_platinum_all"] == 1:
            return 1
        elif row["rule_dz_all"] == 1:
            return 2
        elif row["rule_danger_zone_tenure"] == 1 and row["rule_not_wirehouse"] == 1:
            return 3
        elif row["rule_danger_zone_tenure"] == 1:
            return 4
        else:
            return 5
    
    result["rule_tier"] = result.apply(assign_tier, axis=1)
    
    # Interaction features
    result["interaction_mobile_bleeding"] = result["pit_moves_3yr"] * np.maximum(-result["firm_net_change_12mo"], 0)
    result["interaction_platinum_bleeding"] = result["rule_platinum_all"] * result["rule_bleeding_firm"]
    
    n_platinum = int(result["rule_platinum_all"].sum())
    n_dz = int(result["rule_dz_all"].sum())
    
    print("      Done - Platinum leads: {:,}".format(n_platinum))
    print("      Done - Danger Zone leads: {:,}".format(n_dz))
    
    return result


def calculate_top_decile_lift(y_true, y_scores):
    df = pd.DataFrame({"true": y_true, "score": y_scores})
    df = df.sort_values("score", ascending=False)
    
    n_decile = len(df) // 10
    if n_decile == 0:
        return 0.0
    
    top_decile = df.head(n_decile)
    top_decile_rate = top_decile["true"].mean()
    baseline_rate = df["true"].mean()
    
    if baseline_rate == 0:
        return 0.0
    
    return top_decile_rate / baseline_rate


def run_comparison(df):
    print("")
    print("[4/6] Training models...")
    
    df_sorted = df.sort_values("contacted_date")
    split_idx = int(len(df_sorted) * 0.7)
    
    train = df_sorted.iloc[:split_idx]
    test = df_sorted.iloc[split_idx:]
    
    train_conv = int(train["converted"].sum())
    test_conv = int(test["converted"].sum())
    
    print("      Train: {:,} leads ({:,} conversions)".format(len(train), train_conv))
    print("      Test:  {:,} leads ({:,} conversions)".format(len(test), test_conv))
    
    y_train = train["converted"].values
    y_test = test["converted"].values
    
    pos_count = y_train.sum()
    neg_count = len(y_train) - pos_count
    scale_pos_weight = neg_count / max(pos_count, 1)
    
    results = {}
    
    # Model 1: Raw Features Only
    print("")
    print("      Training Model 1: Raw Features Only...")
    
    raw_features = [
        "firm_rep_count", "current_firm_tenure_months", "industry_tenure_months",
        "firm_net_change_12mo", "pit_moves_3yr", "num_prior_firms",
        "firm_aum_pit"
        # Note: aum_growth_pct removed - not available in Version-3 table
    ]
    
    X_train_raw = train[raw_features].fillna(0)
    X_test_raw = test[raw_features].fillna(0)
    
    model_raw = XGBClassifier(
        n_estimators=100, 
        max_depth=4, 
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        verbosity=0
    )
    model_raw.fit(X_train_raw, y_train)
    
    preds_raw = model_raw.predict_proba(X_test_raw)[:, 1]
    
    results["raw_only"] = {
        "name": "Raw Features Only (V2)",
        "auc_pr": average_precision_score(y_test, preds_raw),
        "auc_roc": roc_auc_score(y_test, preds_raw),
        "top_decile_lift": calculate_top_decile_lift(y_test, preds_raw)
    }
    print("      Done - Raw Only Lift: {:.2f}x".format(results["raw_only"]["top_decile_lift"]))
    
    # Model 2: Rules Only
    print("      Evaluating Model 2: Rules Only...")
    
    test_tier_scores = 6 - test["rule_tier"].values
    
    results["rules_only"] = {
        "name": "Rules Only (V3)",
        "auc_pr": None,
        "auc_roc": None,
        "top_decile_lift": calculate_top_decile_lift(y_test, test_tier_scores)
    }
    print("      Done - Rules Only Lift: {:.2f}x".format(results["rules_only"]["top_decile_lift"]))
    
    # Model 3: Hybrid
    print("      Training Model 3: Hybrid (Raw + Rules)...")
    
    hybrid_features = raw_features + [
        "rule_small_firm", "rule_sweet_tenure", "rule_experienced", 
        "rule_not_wirehouse", "rule_danger_zone_tenure", "rule_bleeding_firm",
        "rule_veteran", "rule_platinum_all", "rule_dz_all", "rule_tier",
        "interaction_mobile_bleeding", "interaction_platinum_bleeding"
    ]
    
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
    
    results["hybrid"] = {
        "name": "Hybrid (Raw + Rules)",
        "auc_pr": average_precision_score(y_test, preds_hybrid),
        "auc_roc": roc_auc_score(y_test, preds_hybrid),
        "top_decile_lift": calculate_top_decile_lift(y_test, preds_hybrid)
    }
    print("      Done - Hybrid Lift: {:.2f}x".format(results["hybrid"]["top_decile_lift"]))
    
    # Feature Importance
    print("")
    print("[5/6] Analyzing feature importance...")
    
    importance = pd.DataFrame({
        "feature": hybrid_features,
        "importance": model_hybrid.feature_importances_
    }).sort_values("importance", ascending=False)
    
    rule_mask = importance["feature"].str.startswith("rule_") | importance["feature"].str.startswith("interaction_")
    rule_features = importance[rule_mask]
    raw_features_imp = importance[~rule_mask]
    
    total_imp = importance["importance"].sum()
    rule_pct = rule_features["importance"].sum() / total_imp * 100
    raw_pct = raw_features_imp["importance"].sum() / total_imp * 100
    
    results["feature_analysis"] = {
        "rule_importance_pct": rule_pct,
        "raw_importance_pct": raw_pct,
        "top_5_features": importance.head(5)["feature"].tolist(),
        "importance_df": importance
    }
    
    return results


def print_results(results):
    print("")
    print("[6/6] Results Summary")
    print("")
    print("=" * 70)
    print("MODEL COMPARISON RESULTS")
    print("=" * 70)
    
    print("")
    print("{:<30} {:<18} {:<12} {:<12}".format("Model", "Top Decile Lift", "AUC-PR", "AUC-ROC"))
    print("-" * 70)
    
    for key in ["raw_only", "rules_only", "hybrid"]:
        r = results[key]
        auc_pr = "{:.4f}".format(r["auc_pr"]) if r["auc_pr"] else "N/A"
        auc_roc = "{:.4f}".format(r["auc_roc"]) if r["auc_roc"] else "N/A"
        lift_str = "{:.2f}x".format(r["top_decile_lift"])
        print("{:<30} {:<18} {:<12} {:<12}".format(r["name"], lift_str, auc_pr, auc_roc))
    
    fa = results["feature_analysis"]
    print("")
    print("-" * 70)
    print("FEATURE IMPORTANCE BREAKDOWN (Hybrid Model)")
    print("-" * 70)
    print("Rule Features:  {:.1f}% of total importance".format(fa["rule_importance_pct"]))
    print("Raw Features:   {:.1f}% of total importance".format(fa["raw_importance_pct"]))
    print("")
    print("Top 5 Features: " + ", ".join(fa["top_5_features"]))
    
    print("")
    print("=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    
    hybrid_lift = results["hybrid"]["top_decile_lift"]
    rules_lift = results["rules_only"]["top_decile_lift"]
    raw_lift = results["raw_only"]["top_decile_lift"]
    
    lifts = {"Hybrid": hybrid_lift, "Rules Only": rules_lift, "Raw Only": raw_lift}
    winner = max(lifts, key=lifts.get)
    
    print("")
    print("** WINNER: {} ({:.2f}x lift) **".format(winner, lifts[winner]))
    
    if winner == "Hybrid":
        improvement = hybrid_lift - rules_lift
        if improvement > 0.3:
            print("")
            print("[OK] Hybrid adds {:.2f}x lift over rules alone.".format(improvement))
            print("   RECOMMENDATION: Use hybrid model - ML is finding additional signal.")
        else:
            print("")
            print("[NOTE] Hybrid only adds {:.2f}x over rules.".format(improvement))
            print("   RECOMMENDATION: Probably not worth the complexity. Stick with rules-only V3.")
    elif winner == "Rules Only":
        diff = rules_lift - hybrid_lift
        print("")
        print("[OK] Rules outperform ML by {:.2f}x".format(diff))
        print("   RECOMMENDATION: Stick with rules-only V3. SGA intuition is best.")
    else:
        diff = raw_lift - rules_lift
        print("")
        print("[WARNING] Raw features outperform rules by {:.2f}x".format(diff))
        print("   RECOMMENDATION: Investigate - rules may not capture the right patterns.")
    
    if fa["rule_importance_pct"] > 70:
        print("")
        print("[INSIGHT] Rules account for {:.0f}% of hybrid model importance.".format(fa["rule_importance_pct"]))
        print("   The ML is mostly learning to weight the rules you gave it.")
    
    print("")
    print("=" * 70)


def main():
    try:
        print("")
        print("Connecting to BigQuery...")
        client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
        
        df = fetch_training_data(client)
        
        if len(df) < 1000:
            print("")
            print("[WARNING] Only {} leads found. Need more data.".format(len(df)))
            return
        
        df = engineer_hybrid_features(df)
        results = run_comparison(df)
        print_results(results)
        
        import os
        output_dir = "Version-3/reports"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_path = os.path.join(output_dir, "hybrid_comparison_results.csv")
        results["feature_analysis"]["importance_df"].to_csv(output_path, index=False)
        print("")
        print("[SAVED] Feature importance saved to: " + output_path)
        print("")
        print("Done!")
        
    except Exception as e:
        print("")
        print("[ERROR] " + str(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()