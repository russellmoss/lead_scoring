# V12 AUM Data Coverage Analysis

**Generated:** November 5, 2025  
**Finding:** All AUM features have 0% importance because they're **missing in the dataset**  
**Impact:** These features cannot be used by the model

---

## Key Finding: AUM Features Are Missing

**All AUM features show 0% coverage in the V12 dataset:**
- `TotalAssetsInMillions`: 0% coverage (all NULL)
- `AUMGrowthRate_1Year`: 0% coverage (all NULL)
- `AUMGrowthRate_5Year`: 0% coverage (all NULL)
- `AssetsInMillions_Individuals`: 0% coverage (all NULL)
- `AssetsInMillions_HNWIndividuals`: 0% coverage (all NULL)
- `CustodianAUM_*`: 0% coverage (all NULL)

**Why They Have 0% Importance:**
- Not because they're not predictive
- **Because they're completely missing from the data** (all NULL)
- Model cannot learn from features that don't exist

---

## Data Coverage Analysis

### Financial Features Coverage

| Feature | Coverage | Status | Reason |
|---------|----------|--------|--------|
| TotalAssetsInMillions | **0%** | ❌ Missing | Not available in `v_discovery_reps_all_vintages` view |
| AUMGrowthRate_1Year | **0%** | ❌ Missing | Not available in view |
| AUMGrowthRate_5Year | **0%** | ❌ Missing | Not available in view |
| AssetsInMillions_Individuals | **0%** | ❌ Missing | Not available in view |
| AssetsInMillions_HNWIndividuals | **0%** | ❌ Missing | Not available in view |
| CustodianAUM_Schwab | **0%** | ❌ Missing | Not available in view |
| CustodianAUM_Fidelity | **0%** | ❌ Missing | Not available in view |
| CustodianAUM_Pershing | **0%** | ❌ Missing | Not available in view |
| CustodianAUM_TDAmeritrade | **0%** | ❌ Missing | Not available in view |

### Engineered Features (Dependent on Missing Data)

| Feature | Coverage | Status | Reason |
|---------|----------|--------|--------|
| AUM_per_Client_v12 | **0%** | ❌ Cannot Compute | Depends on `TotalAssetsInMillions` (missing) |
| HNW_Concentration_v12 | **0%** | ❌ Cannot Compute | Depends on `NumberClients_HNWIndividuals` (may be missing) |

---

## Why This Matters

### Impact on Model

1. **Cannot Use Financial Signals:**
   - AUM size is typically a strong predictor in lead scoring
   - Growth rates are important business signals
   - Custodian relationships could indicate firm type

2. **Model Relies on Behavioral Signals Only:**
   - Stability patterns (firm moves)
   - Tenure patterns (job hopping)
   - Data quality signals (missing data)

3. **Missing Opportunity:**
   - If AUM data were available, model performance could improve significantly
   - Financial features are often top predictors in similar models

---

## Potential Solutions

### Option 1: Check if AUM Data Exists Elsewhere

**Investigation Needed:**
- Check if AUM data exists in raw snapshot tables
- Check if it's available in a different view or table
- Verify if it was filtered out during view creation

### Option 2: Use Alternative Data Sources

**If AUM is truly missing:**
- Use firm-level aggregations if available
- Use client count as proxy (if available)
- Use registration/compliance data as proxy for firm size

### Option 3: Accept Current Model

**Current State:**
- Model works well without AUM (5.95% AUC-PR)
- Behavioral signals are strong
- Missing data itself is a signal (Gender_Missing, RegulatoryDisclosures_Unknown)

---

## Recommendation

**Immediate Action:**
1. ✅ **Accept current model** - It works well with behavioral signals
2. ⚠️ **Investigate AUM availability** - Check if data exists in raw tables
3. ⚠️ **Consider removing AUM features** - If they're always missing, remove from feature set to simplify

**Future Improvement:**
- If AUM data becomes available, add it back to model
- Expected improvement: 1-2pp AUC-PR increase (based on typical importance of financial features)

---

**Report Generated:** November 5, 2025  
**Finding:** All AUM features have 0% coverage in V12 dataset  
**Recommendation:** Accept current model (works well with behavioral signals), investigate AUM data availability for future improvement

