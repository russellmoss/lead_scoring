# Deep Diagnostic Summary: Root Cause Analysis

**Date:** December 21, 2025  
**Issue:** v3 model achieves 1.50x lift vs v2's 2.62x target

---

## 🔴 CRITICAL FINDING #1: flight_risk_score is 98.7% Sparse

### The Problem
**Only 1.3% of leads have a non-zero `flight_risk_score`!**

```
Zero values: 38,953 (98.7%)
Non-zero values: 495 (1.3%)
```

### Why It's Zero
- **79.7%** of leads have `pit_moves_3yr = 0` (no moves in 3 years)
- **94.6%** of leads have `firm_net_change_12mo >= 0` (firms are NOT bleeding)

**The multiplicative feature `pit_moves_3yr × max(-firm_net_change_12mo, 0)` is zero when:**
- Advisor has no moves (79.7% of cases), OR
- Firm is not bleeding (94.6% of cases)

### Impact on Model
- **Single-feature performance:** AUC-ROC = 0.5037, Lift = **0.76x** (worse than random!)
- **Model importance rank:** #19 (correctly ignored by model)
- **The +657% univariate signal is misleading** - it only applies to 1.3% of leads

### Conversion Rates by Bucket
| Bucket | Count | Conversion Rate | % of Total |
|--------|-------|-----------------|------------|
| Zero | 38,953 | 3.67% | 98.7% |
| 1-10 | 88 | 11.36% | 0.2% |
| 11-50 | 96 | 12.50% | 0.2% |
| 51-100 | 52 | 7.69% | 0.1% |
| >100 | 259 | 15.44% | 0.7% |

**Key Insight:** The non-zero buckets DO show higher conversion (11-15% vs 3.67%), but they're too rare to help the model.

---

## 🔴 CRITICAL FINDING #2: Missing V2 Features

### Missing Base Features
❌ **`aum_growth_since_jan2024_pct`** - Firm growth metric  
❌ **`firm_rep_count_at_contact`** - Firm size at contact  
❌ **`pit_mobility_tier_Highly Mobile`** - Mobility tier (one-hot)  
❌ **`pit_mobility_tier_Mobile`** - Mobility tier (one-hot)  
❌ **`pit_mobility_tier_Stable`** - Mobility tier (one-hot)  

### Impact
V2 used **mobility tiers** (categorical bins) instead of raw `pit_moves_3yr`. This may have been more predictive because:
- Tiers handle sparsity better (fewer zero values)
- Categorical features can be more stable in tree models
- V2 achieved 2.62x lift with these features

---

## ⚠️ FINDING #3: Signal Strength Decreased in 2025

### Year Comparison
| Year | Leads | Positive Rate | flight_risk_score Signal | pit_moves_3yr Signal | firm_net_change Signal |
|------|-------|---------------|-------------------------|---------------------|------------------------|
| **2024** | 17,683 | 3.10% | **+63.08** | +0.48 | -42.04 |
| **2025** | 21,765 | 4.35% | **+37.71** | +0.21 | -9.45 |

**Key Observations:**
- Signal strength **decreased by 40%** in 2025
- Positive rate **increased** in 2025 (4.35% vs 3.10%)
- Firm bleeding signal **weakened** significantly (-9.45 vs -42.04)

**Hypothesis:** 2025 data has different characteristics - fewer bleeding firms, more stable advisors.

---

## 📊 FINDING #4: Single Feature Performance

### Test Results (Test Set Only)
| Feature | AUC-ROC | Notes |
|---------|---------|-------|
| `pit_moves_3yr` | **0.5487** | Best single feature |
| `flight_risk_score` | 0.5037 | Near random (sparsity issue) |
| `firm_net_change_12mo` | 0.5035 | Near random |
| `num_prior_firms` | 0.5026 | Near random |
| `current_firm_tenure_months` | 0.5014 | Near random |

**Key Insight:** Even the best single feature (`pit_moves_3yr`) only achieves AUC-ROC = 0.5487, which is barely better than random (0.50). This suggests:
- Individual features are weak predictors
- Model needs feature interactions to work
- V2's mobility tiers may have been more predictive than raw `pit_moves_3yr`

---

## 🎯 ROOT CAUSE ANALYSIS

### Why v3 Underperforms v2

1. **Sparsity Killed flight_risk_score**
   - 98.7% zero values make it useless
   - Model correctly ignores it (rank #19)
   - V2 may have used a different formulation or binned version

2. **Missing Mobility Tiers**
   - V2 used categorical `pit_mobility_tier` features
   - V3 uses raw `pit_moves_3yr` (sparse)
   - Categorical features often perform better in tree models

3. **Missing Growth Metrics**
   - `aum_growth_since_jan2024_pct` was in v2 but not v3
   - `firm_rep_count_at_contact` was in v2 but not v3
   - These may have been key predictors

4. **Data Shift (2024 → 2025)**
   - Signal strength decreased in 2025
   - Fewer bleeding firms, more stable advisors
   - Model trained on 2024+2025 may be diluted

---

## 💡 RECOMMENDATIONS

### Immediate Actions

1. **Add Missing V2 Features**
   - Re-engineer `pit_mobility_tier` (categorical bins of `pit_moves_3yr`)
   - Add `aum_growth_since_jan2024_pct` if possible
   - Add `firm_rep_count_at_contact` if available

2. **Fix flight_risk_score Sparsity**
   - **Option A:** Bin into tiers (Zero, Low, Medium, High)
   - **Option B:** Use separate features (`has_moves`, `is_bleeding_firm`)
   - **Option C:** Remove it and rely on component features

3. **Test with Mobility Tiers**
   - Create `pit_mobility_tier` from `pit_moves_3yr`:
     - Stable: 0 moves
     - Mobile: 1-2 moves
     - Highly Mobile: 3+ moves
   - Train model with tiers instead of raw `pit_moves_3yr`

4. **Investigate Target Variable**
   - Could not compare v2 vs v3 target definition (v2 table missing)
   - Verify target calculation matches v2 exactly

### Expected Impact

If we add mobility tiers and fix sparsity:
- **Expected lift:** 1.8-2.2x (closer to v2's 2.62x)
- **Rationale:** V2 achieved 2.62x with these features, so adding them back should help

---

## 📝 Next Steps

1. ✅ **Diagnostic complete** - Root causes identified
2. ⏭️ **Add mobility tiers** to feature engineering
3. ⏭️ **Re-engineer flight_risk_score** to handle sparsity
4. ⏭️ **Add missing v2 features** if available
5. ⏭️ **Retrain model** with complete feature set
6. ⏭️ **Target:** Achieve >2.0x lift

---

## Files Created

- `deep_diagnostic_findings.json` - Raw diagnostic data
- `deep_diagnostic_summary.md` - This summary document

