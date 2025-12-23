# m5 Feature Selection and Dimensionality Reduction Analysis

**Date:** November 5, 2025  
**Purpose:** Understand m5's approach to feature selection and dimensionality reduction

---

## Executive Summary

**m5 does NOT use explicit feature selection or dimensionality reduction techniques.**

Instead, m5 uses:
1. **All 67 features** (31 base + 5 metro dummies + 31 engineered)
2. **XGBoost's built-in feature importance** for understanding which features matter
3. **Regularization (L1/L2)** to naturally prune unimportant features during training

This is a key difference from V1/V7, which used aggressive pre-filtering that removed important features.

---

## m5's Feature Selection Strategy

### No Explicit Feature Selection

From `m5_vs_V1_Model_Comparison_Analysis.md` (Section 5.1):

> **No Explicit Feature Selection:**
> - Uses all 67 features
> - Relies on XGBoost's built-in feature importance
> - Regularization (L1/L2) naturally prunes unimportant features
> - Feature importance shows `Multi_RIA_Relationships` is #1 (0.0816)

### Feature Set Composition

**Total Features: 67**

1. **Base Features (31):**
   - Rep characteristics (tenure, licenses, designations)
   - Firm characteristics (employees, AUM, clients)
   - Asset and client metrics
   - Growth metrics
   - Geographic information

2. **Metropolitan Area Dummies (5):**
   - Chicago-Naperville-Elgin IL-IN
   - Dallas-Fort Worth-Arlington TX
   - Los Angeles-Long Beach-Anaheim CA
   - Miami-Fort Lauderdale-West Palm Beach FL
   - New York-Newark-Jersey City NY-NJ

3. **Engineered Features (31):**
   - Efficiency metrics (AUM_per_Client, AUM_per_Employee, AUM_per_IARep)
   - Growth indicators (Growth_Momentum, Growth_Acceleration)
   - Stability scores (Firm_Stability_Score, Experience_Efficiency)
   - Client composition (HNW_Asset_Concentration, Individual_Asset_Ratio)
   - Scale indicators (Has_Scale, Is_Large_Firm, Is_Boutique_Firm)
   - Advisor tenure patterns (Is_New_To_Firm, Is_Veteran_Advisor)
   - Market positioning (Premium_Positioning, Mass_Market_Focus)
   - Operational efficiency (Clients_per_Employee, Branch_Advisor_Density)
   - Geographic factors (Remote_Work_Indicator, Local_Advisor)
   - Firm relationships (**Multi_RIA_Relationships** - #1 feature)
   - Composite scores (Quality_Score, Positive_Growth_Trajectory)

---

## How m5 Handles Feature Selection

### 1. Regularization-Based Pruning

**L1 Regularization (reg_alpha=0.5):**
- Encourages sparsity
- Drives coefficients of unimportant features to zero
- Acts as automatic feature selection during training

**L2 Regularization (reg_lambda=2.0):**
- Prevents overfitting
- Reduces feature weights
- Helps generalize better

**Additional Regularization:**
- `gamma=2`: Minimum split loss (further regularization)
- `min_child_weight=2`: Minimum samples in leaf nodes
- `colsample_bytree=0.7`: Random feature subsampling
- `colsample_bylevel=0.7`: Additional feature subsampling per level

**Result:** Features that don't contribute to predictions are effectively pruned by regularization, without explicit feature selection.

### 2. XGBoost's Built-in Feature Importance

**How it works:**
- XGBoost tracks feature usage in splits
- Features used in more splits with higher information gain are ranked higher
- `Multi_RIA_Relationships` emerged as #1 feature (0.0816 importance)

**Benefits:**
- No pre-filtering needed
- Model learns which features matter
- Important features naturally rise to the top

### 3. Feature Scaling Strategy

**Conditional Scaling:**
- **Scaled (43 features):** All numeric features via StandardScaler
- **Passthrough (24 features):** All dummy/boolean features remain unscaled

**Why this matters:**
- Prevents unimportant numeric features from being over-weighted
- Allows model to learn appropriate feature importance
- Doesn't artificially suppress features

---

## Comparison with V1/V7 Approach

### V1 Approach (Aggressive Pre-Filtering)

**Issues:**
- ❌ **IV Filter:** Removed 18 features with IV < 0.02 (too strict for 3.5% positive class)
- ❌ **VIF Filter:** Removed features with VIF > 10
- ❌ **Removed important features:** `Multi_RIA_Relationships` (m5's #1 feature) was filtered out!
- ❌ **Removed other key features:** `AUMGrowthRate_5Year`, `AUM_Per_Client`, etc.

**Result:** V1 lost critical signal by removing important features before training.

### V7 Approach (No Pre-Filtering, But Too Many Features)

**Current State:**
- ✅ **No pre-filtering:** All 123 features used
- ⚠️ **Too many features:** 123 vs m5's 67 (84% more features)
- ⚠️ **Insufficient regularization:** reg_alpha=0.5, reg_lambda=3.0 (same as m5, but more features)
- ❌ **Overfitting:** 94.87% train-test gap

**Problem:** V7 has nearly 2x the features of m5 but uses similar regularization, leading to overfitting.

### m5 Approach (Optimal Balance)

**Strengths:**
- ✅ **All features included:** 67 features (curated set)
- ✅ **Strong regularization:** L1=0.5, L2=2.0, gamma=2
- ✅ **Feature subsampling:** colsample_bytree=0.7, colsample_bylevel=0.7
- ✅ **No overfitting:** Stable performance

**Result:** m5 achieves optimal balance between feature richness and model complexity.

---

## Why m5's Approach Works

### 1. Feature Quality over Quantity

**m5's 67 features:**
- Carefully curated base features
- Sophisticated engineered features (31)
- All features have business logic behind them
- No redundant or noisy features

**V7's 123 features:**
- Includes all base features
- Adds 43 new engineered features
- May include redundant or noisy features
- Some features may not have strong signal

### 2. Regularization Effectiveness

**m5's Regularization:**
- L1=0.5, L2=2.0 (moderate but effective)
- Works well with 67 features
- Prunes unimportant features automatically

**V7's Regularization:**
- L1=0.5, L2=3.0 (slightly higher L2, but more features)
- May be insufficient for 123 features
- Needs stronger regularization or fewer features

### 3. Feature Engineering Focus

**m5's Engineered Features:**
- 31 carefully crafted features
- Each has clear business rationale
- Proven to contribute to predictions
- Top feature (`Multi_RIA_Relationships`) is engineered

**V7's Engineered Features:**
- 43 new features (23 m5 + 8 temporal + 4 career + 2 market + 6 business)
- Some may be redundant or noisy
- Temporal features may not be capturing useful patterns
- Need to verify which features actually help

---

## Dimensionality Reduction Techniques Used

### None Explicitly

**m5 does NOT use:**
- ❌ PCA (Principal Component Analysis)
- ❌ ICA (Independent Component Analysis)
- ❌ Feature selection algorithms (RFE, SelectKBest, etc.)
- ❌ Correlation-based filtering
- ❌ Variance thresholding

**Instead, m5 uses:**
- ✅ **Regularization** (implicit feature selection)
- ✅ **Feature subsampling** (colsample_bytree, colsample_bylevel)
- ✅ **XGBoost's internal feature importance** (for understanding, not selection)

---

## Key Insights for V7

### 1. Feature Count Matters

**Comparison:**
- **m5:** 67 features → 14.92% AUC-PR
- **V7:** 123 features → 4.98% AUC-PR (worse!)

**Insight:** More features don't always mean better performance. Quality and regularization matter more.

### 2. Regularization Must Match Feature Count

**m5's Ratio:**
- 67 features / 2.0 L2 regularization = 33.5 features per L2 unit

**V7's Ratio:**
- 123 features / 3.0 L2 regularization = 41 features per L2 unit

**Problem:** V7 has higher feature-to-regularization ratio, leading to overfitting.

**Solution:** 
- Either reduce features to ~67 (like m5)
- Or increase regularization significantly (L2 to 5.0+)

### 3. Feature Engineering Should Be Selective

**m5's Approach:**
- 31 engineered features, all proven useful
- Top features are engineered (`Multi_RIA_Relationships`)

**V7's Approach:**
- 43 engineered features, some may be redundant
- Need to verify which features actually contribute

**Recommendation:**
- Review feature importance rankings
- Remove features with very low importance
- Focus on m5's proven features first

---

## Recommendations for V7 Improvement

### Option 1: Reduce Feature Count (Recommended)

**Strategy:**
1. Start with m5's proven 67 features
2. Add V7's temporal features incrementally
3. Test performance after each addition
4. Stop when performance plateaus or degrades

**Benefits:**
- Matches m5's proven approach
- Easier to regularize
- Less risk of overfitting

### Option 2: Increase Regularization

**Strategy:**
1. Keep all 123 features
2. Increase L2 regularization: 3.0 → 5.0 or higher
3. Increase L1 regularization: 0.5 → 1.0
4. Increase gamma: 2 → 3
5. Reduce max_depth: 5 → 4

**Benefits:**
- Keeps all engineered features
- Stronger regularization should prevent overfitting
- May still achieve good performance

### Option 3: Feature Selection Post-Training

**Strategy:**
1. Train model with all features
2. Review feature importance rankings
3. Remove bottom 20-30% of features
4. Re-train with selected features
5. Compare performance

**Benefits:**
- Data-driven feature selection
- Removes truly unimportant features
- Can improve performance and reduce overfitting

---

## Conclusion

**m5's Success Formula:**
1. **No explicit feature selection** - uses all 67 features
2. **Strong regularization** - L1=0.5, L2=2.0, gamma=2
3. **Feature subsampling** - colsample_bytree=0.7, colsample_bylevel=0.7
4. **Quality feature engineering** - 31 proven engineered features
5. **XGBoost's built-in importance** - learns which features matter

**V7's Issues:**
1. **Too many features** - 123 vs 67 (84% more)
2. **Insufficient regularization** - Same as m5 but 2x features
3. **Overfitting** - 94.87% train-test gap
4. **Feature quality unknown** - Need to verify which features help

**Recommendation:**
- **Option 1 (Reduce Features)** is most likely to succeed
- Start with m5's 67 features and add V7 features incrementally
- This matches m5's proven approach
- Easier to debug and understand

---

**Analysis Date:** November 5, 2025  
**Status:** Complete  
**Key Finding:** m5 does NOT use explicit feature selection - relies on regularization and feature quality

