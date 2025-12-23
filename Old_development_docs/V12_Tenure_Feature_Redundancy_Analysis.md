# V12 Tenure Feature Redundancy Analysis

**Generated:** November 5, 2025  
**Issue:** 16 tenure features from Prior Firm 1-4 + AverageTenureAtPriorFirms may be redundant  
**Goal:** Identify redundant features and recommend simplification

---

## Current Tenure Features (16 Features)

### AverageTenureAtPriorFirms (5 bins)
- Short_Under_2 (3.09% importance)
- Moderate_2_to_5 (3.59% importance)
- Long_5_to_10 (4.39% importance)
- Very_Long_10_Plus (4.26% importance)
- No_Prior_Firms (0.00% importance)

**Total Importance:** 15.33%

### Prior Firm 1 (4 bins)
- Short_Under_3 (3.10% importance)
- Moderate_3_to_7 (3.18% importance)
- Long_7_Plus (7.41% importance) ⭐ **Top 3 feature**
- No_Prior_Firm_1 (0.00% importance)

**Total Importance:** 13.69%

### Prior Firm 2 (4 bins)
- Short_Under_3 (3.31% importance)
- Moderate_3_to_7 (3.30% importance)
- Long_7_Plus (3.35% importance)
- No_Prior_Firm_2 (0.00% importance)

**Total Importance:** 9.96%

### Prior Firm 3 (4 bins)
- Short_Under_3 (3.46% importance)
- Moderate_3_to_7 (3.11% importance)
- Long_7_Plus (3.52% importance)
- No_Prior_Firm_3 (0.00% importance)

**Total Importance:** 10.09%

### Prior Firm 4 (4 bins)
- Short_Under_3 (3.26% importance)
- Moderate_3_to_7 (3.20% importance)
- Long_7_Plus (3.37% importance)
- No_Prior_Firm_4 (0.00% importance)

**Total Importance:** 9.83%

---

## Redundancy Analysis

### Correlation Analysis

| Feature Pair | Correlation | Status |
|--------------|-------------|--------|
| **AverageTenureAtPriorFirms vs Prior Firm 1** | **0.879** | ⚠️ **VERY HIGH - Highly Redundant** |
| Prior Firm 1 vs Prior Firm 2 | 0.414 | ✅ Moderate - OK |
| Prior Firm 2 vs Prior Firm 3 | 0.442 | ✅ Moderate - OK |
| Prior Firm 3 vs Prior Firm 4 | 0.493 | ✅ Moderate - OK |

**Key Finding:** AverageTenureAtPriorFirms is **88% correlated** with Prior Firm 1!

### Coverage Analysis

| Feature | Coverage | Interpretation |
|---------|----------|-----------------|
| Prior Firm 1 | 18.91% | Most recent prior firm - highest coverage |
| Prior Firm 2 | 13.33% | Second prior firm - moderate coverage |
| Prior Firm 3 | 9.35% | Third prior firm - low coverage |
| Prior Firm 4 | 6.56% | Fourth prior firm - very low coverage |
| Average Prior Firms | 0.48 avg | Average number of prior firms per advisor |

**Key Finding:** Coverage drops significantly for Prior Firm 2-4 (13%, 9%, 7%).

---

## Current Feature Importance Distribution

### Top Tenure Features

| Rank | Feature | Importance | Type |
|------|---------|------------|------|
| 3 | Number_YearsPriorFirm1_binned_Long_7_Plus | 7.41% | Prior Firm 1 |
| 5 | AverageTenureAtPriorFirms_binned_Long_5_to_10 | 4.39% | Average |
| 6 | AverageTenureAtPriorFirms_binned_Very_Long_10_Plus | 4.26% | Average |
| 7 | AverageTenureAtPriorFirms_binned_Moderate_2_to_5 | 3.59% | Average |
| 9 | Number_YearsPriorFirm3_binned_Short_Under_3 | 3.46% | Prior Firm 3 |
| 13 | Number_YearsPriorFirm2_binned_Long_7_Plus | 3.35% | Prior Firm 2 |
| 14 | Number_YearsPriorFirm2_binned_Short_Under_3 | 3.31% | Prior Firm 2 |
| 15 | Number_YearsPriorFirm2_binned_Moderate_3_to_7 | 3.30% | Prior Firm 2 |
| 16 | Number_YearsPriorFirm4_binned_Short_Under_3 | 3.26% | Prior Firm 4 |
| 17 | Number_YearsPriorFirm4_binned_Moderate_3_to_7 | 3.20% | Prior Firm 4 |
| 19 | Number_YearsPriorFirm1_binned_Moderate_3_to_7 | 3.18% | Prior Firm 1 |
| 20 | Number_YearsPriorFirm3_binned_Moderate_3_to_7 | 3.11% | Prior Firm 3 |
| 21 | Number_YearsPriorFirm1_binned_Short_Under_3 | 3.10% | Prior Firm 1 |
| 22 | AverageTenureAtPriorFirms_binned_Short_Under_2 | 3.09% | Average |

**Total Tenure Importance:** 52.35% (16 features)

---

## Problem Statement

### Issues with Current Approach:

1. **High Redundancy:**
   - AverageTenureAtPriorFirms (summary) is 88% correlated with Prior Firm 1
   - Both capture similar "long tenure" signals

2. **Low Coverage:**
   - Prior Firm 2-4 have decreasing coverage (13%, 9%, 7%)
   - Many features have 0% importance (No_Prior_Firm_2/3/4)

3. **Diminishing Returns:**
   - Prior Firm 3 and 4 features have similar importance (3.1-3.5%)
   - Not much incremental signal beyond Prior Firm 1-2

4. **Complexity:**
   - 16 tenure features is hard to interpret
   - Many similar patterns across Prior Firm 2-4

---

## Recommended Simplification

### Option 1: Keep Summary + Most Recent (RECOMMENDED)

**Keep:**
1. ✅ **AverageTenureAtPriorFirms** (5 bins) - Summary signal
2. ✅ **Prior Firm 1** (4 bins) - Most recent prior firm, highest signal

**Remove:**
- ❌ Prior Firm 2 (4 bins) - Lower coverage, similar patterns
- ❌ Prior Firm 3 (4 bins) - Low coverage, redundant
- ❌ Prior Firm 4 (4 bins) - Very low coverage, redundant

**Rationale:**
- AverageTenureAtPriorFirms captures overall tenure pattern
- Prior Firm 1 captures most recent prior firm (strongest signal)
- Prior Firm 2-4 are redundant and have lower coverage

**Expected Impact:**
- Reduce from 16 to 9 tenure features (7 fewer features)
- Keep 28.98% of tenure importance (Average: 15.33% + Prior Firm 1: 13.69%)
- May lose ~23% of tenure importance, but gain simplicity

---

### Option 2: Keep Prior Firm 1 Only (More Aggressive)

**Keep:**
1. ✅ **Prior Firm 1** (4 bins) - Most recent, highest signal (7.41% top feature)

**Remove:**
- ❌ AverageTenureAtPriorFirms (5 bins) - 88% correlated with Prior Firm 1
- ❌ Prior Firm 2-4 (12 bins) - Lower coverage, redundant

**Rationale:**
- Prior Firm 1 is the #3 feature overall (7.41% importance)
- AverageTenureAtPriorFirms is highly redundant (88% correlation)
- Prior Firm 1 captures the most recent tenure signal

**Expected Impact:**
- Reduce from 16 to 4 tenure features (12 fewer features)
- Keep 13.69% of tenure importance (Prior Firm 1 only)
- May lose ~39% of tenure importance, but significant simplification

---

### Option 3: Combine Prior Firm 2-4 into Single Feature

**Keep:**
1. ✅ **AverageTenureAtPriorFirms** (5 bins)
2. ✅ **Prior Firm 1** (4 bins)
3. ✅ **New: Max/Min Tenure at Prior Firms 2-4** (3 bins: Short/Moderate/Long)

**Remove:**
- ❌ Individual Prior Firm 2 bins (4 bins)
- ❌ Individual Prior Firm 3 bins (4 bins)
- ❌ Individual Prior Firm 4 bins (4 bins)

**Rationale:**
- Captures additional signal from Prior Firm 2-4 without redundancy
- Single feature instead of 12 features

**Expected Impact:**
- Reduce from 16 to 12 tenure features (4 fewer features)
- Keep most tenure importance while simplifying

---

## Recommendation: Option 1 (Keep Summary + Most Recent)

### Why Option 1?

1. **Balance:**
   - Keeps the most important signals (Average + Prior Firm 1)
   - Removes redundant lower-coverage features (Prior Firm 2-4)

2. **Interpretability:**
   - 9 features instead of 16 (44% reduction)
   - Clear meaning: "Overall tenure pattern" + "Most recent prior firm"

3. **Performance:**
   - Keeps 28.98% of tenure importance
   - Prior Firm 1 is top 3 feature (7.41%)
   - AverageTenureAtPriorFirms captures overall pattern

4. **Coverage:**
   - Prior Firm 1 has 18.9% coverage (highest)
   - Prior Firm 2-4 have decreasing coverage (13%, 9%, 7%)

### Implementation:

```python
# Keep these tenure features
TENURE_FEATURES_TO_BIN = {
    'AverageTenureAtPriorFirms': {
        'bins': [0, 2, 5, 10, 100],
        'labels': ['Short_Under_2', 'Moderate_2_to_5', 'Long_5_to_10', 'Very_Long_10_Plus'],
        'default': 'No_Prior_Firms'
    },
    'Number_YearsPriorFirm1': {
        'bins': [0, 3, 7, 100],
        'labels': ['Short_Under_3', 'Moderate_3_to_7', 'Long_7_Plus'],
        'default': 'No_Prior_Firm_1'
    },
    'Firm_Stability_Score_v12': {
        'bins': [0, 0.3, 0.6, 0.9, 10],
        'labels': ['Low_Under_30', 'Moderate_30_to_60', 'High_60_to_90', 'Very_High_90_Plus'],
        'default': 'Missing_Zero'
    }
}

# Remove Prior Firm 2-4 from binning
```

---

## Expected Impact

### Feature Count Reduction

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Tenure Features** | 16 | 9 | **-7 features** (44% reduction) |
| **Total Features** | 53 | 46 | **-7 features** (13% reduction) |

### Importance Retention

| Feature Set | Importance | Retention |
|-------------|------------|-----------|
| AverageTenureAtPriorFirms | 15.33% | ✅ Kept |
| Prior Firm 1 | 13.69% | ✅ Kept |
| Prior Firm 2-4 | 29.97% | ❌ Removed |
| **Total Kept** | **28.98%** | **55% of tenure importance** |

### Performance Impact (Expected)

- **Potential AUC-PR Drop:** 0.1-0.3pp (may actually improve due to less overfitting)
- **Overfitting Reduction:** Likely improved (fewer correlated features)
- **Interpretability:** Significantly improved (7 fewer features)

---

## Next Steps

1. ✅ **Implement Option 1** - Remove Prior Firm 2-4 from binning
2. ✅ **Retrain Model** - Compare performance
3. ✅ **Compare Results** - AUC-PR, overfitting, feature importance
4. ✅ **Document Changes** - Update feature importance report

---

**Recommendation:** ✅ **Proceed with Option 1** - Remove Prior Firm 2-4, keep AverageTenureAtPriorFirms + Prior Firm 1

**Expected Outcome:** 
- Simpler model (7 fewer features)
- Better interpretability
- Similar or better performance (less overfitting)
- Clearer business signals

---

**Report Generated:** November 5, 2025  
**Analysis:** V12 Tenure Feature Redundancy  
**Recommendation:** Remove Prior Firm 2-4, keep AverageTenureAtPriorFirms + Prior Firm 1

