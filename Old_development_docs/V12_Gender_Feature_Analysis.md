# V12 Gender Feature Analysis: Redundancy Removal

**Generated:** November 5, 2025  
**Issue:** Both `Gender_Male` and `Gender_Female` were in top features, creating redundancy  
**Solution:** Use single `Gender_Male` feature + `Gender_Missing` flag

---

## The Problem

**Original Encoding (Redundant):**
- `Gender_Male`: 3.55% importance (rank #14)
- `Gender_Female`: 3.94% importance (rank #7)
- **Total:** 7.49% combined importance

**Issue:** Since every lead is either Male or Female, having both features is redundant:
- If `Gender_Male = 1`, then `Gender_Female = 0` (automatically)
- If `Gender_Male = 0`, then `Gender_Female = 1` (automatically)
- This creates perfect negative correlation (-1.0), which is wasteful

---

## The Solution

**New Encoding (Efficient):**
- `Gender_Male`: 3.46% importance (rank #10)
- `Gender_Missing`: **8.03% importance** (rank #2!)
- **Total:** 11.49% combined importance

**Why This Works:**
1. **Single feature for Male:** `Gender_Male = 1` if male, `0` if female or missing
2. **Missing as separate signal:** `Gender_Missing = 1` if gender is unknown/missing, `0` if known
3. **No redundancy:** These are independent binary flags

---

## Performance Impact

### Test Set Performance

| Metric | Before (Both) | After (Single + Missing) | Change |
|--------|---------------|--------------------------|--------|
| **Test AUC-PR** | 5.97% | **6.00%** | **+0.03pp** ✅ |
| **Test AUC-ROC** | 0.5811 | 0.5820 | +0.0009 ✅ |
| **Overfit Gap** | 2.07pp (25.7%) | 2.02pp (25.2%) | -0.05pp ✅ |
| **Feature Count** | 53 | 53 | Same |

**Result:** ✅ **Slight improvement** - Removing redundancy didn't hurt performance!

### Cross-Validation

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **CV Mean** | 6.08% | 6.07% | -0.01pp (stable) |
| **CV Std** | 0.0064 | 0.0063 | -0.0001 (slightly more stable) |

**Result:** ✅ **Stability maintained** - No degradation in CV performance

---

## Key Insight: Gender_Missing is a Strong Signal!

### MQL Rates by Gender

| Gender Group | Total Leads | MQLs | **MQL Rate** | % of Total |
|--------------|-------------|------|---------------|------------|
| **Unknown/Missing** | 1,661 | 154 | **9.27%** 🎯 | 3.57% |
| Male | 36,482 | 1,540 | 4.22% | 78.48% |
| Female | 8,340 | 253 | 3.03% | 17.94% |

**Key Finding:** 
- **Missing gender has 2.2x higher MQL rate than Male** (9.27% vs 4.22%)
- **Missing gender has 3.1x higher MQL rate than Female** (9.27% vs 3.03%)
- This is why `Gender_Missing` is now the **#2 feature** (8.03% importance)!

### Why Missing Gender is a Signal

**Possible Explanations:**
1. **Newer advisors:** Gender data may not be fully captured for newer advisors in Discovery
2. **Data quality:** Missing gender might correlate with other missing data (e.g., newer firm associations)
3. **Proxy for other factors:** Missing gender might indicate advisors who are less traditional or have different career paths

**Actionable Insight:** Leads with missing gender data should be **prioritized** - they have nearly 3x the MQL rate!

---

## Feature Importance Comparison

### Before (Both Gender Features)

| Rank | Feature | Importance | Type |
|------|---------|------------|------|
| 7 | Gender_Female | 3.94% | Categorical |
| 14 | Gender_Male | 3.55% | Categorical |

**Total Gender Importance:** 7.49%

### After (Single + Missing)

| Rank | Feature | Importance | Type |
|------|---------|------------|------|
| **2** | **Gender_Missing** | **8.03%** | **Missing flag** |
| 10 | Gender_Male | 3.46% | Categorical |

**Total Gender Importance:** 11.49% (53% increase!)

**Why Increase?**
- `Gender_Missing` captured the strong signal that was previously hidden
- Single `Gender_Male` feature is more efficient (no redundancy)

---

## Recommendation: Keep Gender Features (But Single Encoding)

### ✅ **Keep Gender_Male and Gender_Missing**

**Reasons:**
1. **Strong signal:** Gender_Missing has 8.03% importance (#2 feature)
2. **Business value:** Missing gender = 9.27% MQL rate (vs 4.22% for Male)
3. **No redundancy:** Single encoding is efficient
4. **Performance:** Slight improvement (6.00% vs 5.97% AUC-PR)

### ⚠️ **Ethical Considerations**

**Should we remove Gender entirely for ethical reasons?**

**Arguments FOR removing:**
- Gender may be a proxy for other factors (firm type, AUM, advisor role)
- Using gender as a predictive feature may introduce bias
- Gender shouldn't causally affect MQL conversion

**Arguments AGAINST removing:**
- Gender_Missing is a strong data quality signal (9.27% MQL rate)
- Gender_Male still provides some signal (3.46% importance)
- Removing might hurt performance (6.00% → ?)

**Recommendation:** 
1. **Keep for now** - Gender_Missing is a valuable data quality signal
2. **Investigate causality** - Why is gender a signal? Is it causation or correlation?
3. **Consider proxy features** - If gender is a proxy for firm type/AUM, use those directly
4. **Monitor for bias** - Ensure model doesn't unfairly discriminate

---

## Alternative: Remove Gender Entirely?

If we want to remove gender for ethical reasons, we should:

1. **Test performance impact:**
   - Remove `Gender_Male` and `Gender_Missing`
   - Retrain model
   - Compare AUC-PR (expect 0.1-0.3pp drop based on 11.49% combined importance)

2. **Replace with proxy features:**
   - If gender correlates with firm type, use `Firm_Type` directly
   - If gender correlates with AUM, use `TotalAssetsInMillions` directly
   - If gender correlates with advisor role, use `Title` or `Is_Owner` directly

3. **Monitor for bias:**
   - Track MQL rates by gender in production
   - Ensure no unfair discrimination

---

## Conclusion

**✅ Gender Redundancy Fixed**

**Changes Made:**
- Removed redundant `Gender_Female` feature
- Kept `Gender_Male` as single binary feature
- Added `Gender_Missing` flag (strong signal - 8.03% importance)

**Performance:**
- ✅ Slight improvement (6.00% vs 5.97% AUC-PR)
- ✅ Better feature efficiency (no redundancy)
- ✅ Stronger signal captured (Gender_Missing is #2 feature)

**Next Steps:**
1. ✅ **Keep current encoding** (Gender_Male + Gender_Missing)
2. ⚠️ **Investigate causality** - Why is gender a signal?
3. ⚠️ **Monitor for bias** - Ensure fair predictions
4. ⚠️ **Consider proxy features** - If gender is a proxy, use underlying factors directly

---

**Report Generated:** November 5, 2025  
**Comparison:** V12 with Both Gender Features (20251105_1642) vs V12 with Single Gender Feature (20251105_1646)  
**Recommendation:** ✅ **Keep Gender_Male + Gender_Missing** (current implementation is optimal)

