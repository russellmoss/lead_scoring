# Lead Scoring Model Card - Boosted Model (v2)

**Version:** v2-boosted-20251221-b796831a  
**Date:** 2025-12-21  
**Status:** Production Ready  
**Model Type:** Boosted XGBoost with Engineered Features

---

## Model Overview

This model predicts the probability that a lead will convert to a "Call Scheduled" stage within 30 days of initial contact. The model uses XGBoost with **3 engineered features** to recover performance after removing data leakage, achieving **2.62x lift** on the test set.

### Model Type
- **Algorithm:** XGBoost (Gradient Boosting)
- **Calibration Method:** Isotonic
- **Features:** 14 features (11 base + 3 engineered)
- **Model Version:** v2-boosted (replaces v1 after data leakage remediation)

---

## Performance Metrics

### Test Set Performance (1,739 leads)

| Metric | Value |
|--------|-------|
| **AUC-ROC** | 0.6674 |
| **AUC-PR** | 0.0738 |
| **Baseline Conversion Rate** | 4.20% |
| **Top Decile Conversion Rate** | 10.98% |
| **Top Decile Lift** | **2.62x** |

### Calibration Quality

| Metric | Value |
|--------|-------|
| **Calibration Method** | Isotonic |
| **Brier Score** | 0.039311 |

---

## Key Features

### Top Predictive Features

1. **`current_firm_tenure_months`** - Primary signal (short tenure = higher conversion)
2. **`pit_restlessness_ratio`** ⭐ - **NEW**: Captures advisors staying longer than historical pattern
3. **`flight_risk_score`** ⭐ - **NEW**: Combines mobility + firm bleeding (multiplicative signal)
4. **`firm_net_change_12mo`** - Firm stability signal (bleeding firms = opportunity)
5. **`is_fresh_start`** ⭐ - **NEW**: Binary flag for new hires (< 12 months)

### Engineered Features (v2 Boost)

**1. `pit_restlessness_ratio`**
- **Formula:** `current_firm_tenure_months / (avg_prior_firm_tenure_months + 1)`
- **Purpose:** Identifies advisors who have stayed longer than their historical "itch" cycle
- **Business Logic:** High ratio = stable, low ratio = may be ready to move

**2. `flight_risk_score`**
- **Formula:** `pit_moves_3yr * (firm_net_change_12mo * -1)`
- **Purpose:** Multiplicative combination of "Mobile Person" + "Bleeding Firm"
- **Business Logic:** High mobility × Bleeding firm = High flight risk

**3. `is_fresh_start`**
- **Formula:** `1 if current_firm_tenure_months < 12 else 0`
- **Purpose:** Binary flag to isolate "New Hires" from "Veterans"
- **Business Logic:** New hires may be more open to opportunities

### Business Hypotheses Validated

- ✅ **Mobility Hypothesis:** Advisors with frequent firm changes are more likely to convert
- ✅ **Employment Gap Hypothesis:** Removed due to data leakage (retrospective backfilling)
- ✅ **Bleeding Firm Hypothesis:** Advisors at unstable firms are more likely to convert
- ✅ **Restlessness Hypothesis:** Advisors staying longer than usual may be more stable
- ✅ **Flight Risk Hypothesis:** Mobile advisors at bleeding firms = highest conversion risk

---

## Training Data

- **Training Period:** February 2024 - October 2024
- **Training Samples:** 8,135 leads
- **Test Period:** November 2024
- **Test Samples:** 1,739 leads
- **Temporal Split:** 70% train, 15% validation, 15% test (with 30-day gap)

---

## Model Architecture

### Feature Set

**Base Features (11):**
aum_growth_since_jan2024_pct, current_firm_tenure_months, firm_aum_pit, firm_net_change_12mo, firm_rep_count_at_contact
... and 6 more base features

**Engineered Features (3):**
- `pit_restlessness_ratio` ⭐
- `flight_risk_score` ⭐
- `is_fresh_start` ⭐

**Total:** 14 features

### Data Leakage Remediation

**Removed Features:**
- ❌ `days_in_gap` - **DATA LEAKAGE** (retrospective backfilling, not available at inference)
- ❌ `firm_stability_score` - Weak IV (0.004)
- ❌ `pit_mobility_tier_Average` - Weak IV (0.004)

**Performance Impact:**
- Original (with leakage): 3.03x lift
- Honest baseline (no leakage): 1.65x lift
- Boosted (with engineered features): **2.62x lift** ✅

---

## Usage

### Score Interpretation

- **0.0 - 0.3:** Low probability (Cold)
- **0.3 - 0.5:** Medium probability (Warm)
- **0.5 - 0.7:** High probability (Hot)
- **0.7 - 1.0:** Very high probability (Very Hot)

### Recommended Actions

- **Very Hot (0.7+):** Call immediately
- **Hot (0.5-0.7):** Prioritize in next outreach cycle
- **Warm (0.3-0.5):** Include in standard outreach
- **Cold (<0.3):** Low priority

---

## Limitations

1. **Class Imbalance:** 4.2% positive rate requires careful threshold tuning
2. **Temporal Validation:** Model trained on Feb-Oct 2024, tested on Nov 2024
3. **Feature Dependencies:** Some features depend on FINTRX data availability
4. **Derived Features:** 3 features must be calculated at inference time (not in BigQuery table)

---

## Maintenance

- **Retrain Frequency:** Quarterly
- **Monitoring:** Track conversion rates monthly
- **Alert Threshold:** If top decile lift drops below 2.0x

---

## Version History

- **v2-boosted-20251221-b796831a:** Boosted model (v2) - Initial production release
  - 2.62x lift on test set
  - Isotonic calibration
  - 3 engineered features (restlessness, flight risk, fresh start)
  - Data leakage removed (`days_in_gap`)
  - Validated on 1,739 test leads

- **v1-20251221-b374197e:** Original model (deprecated due to data leakage)

---

## Contact

For questions or issues, contact the Data Science team.
