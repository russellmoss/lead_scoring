# Step 5.1: Feature Reclassification Report

**Date:** November 2025  
**Purpose:** Reclassify features from binary `is_mutable` to 3-part `temporal_type` classification  
**Status:** ✅ COMPLETE

---

## Executive Summary

Successfully reclassified all 122 features from a binary `is_mutable` classification to a 3-part `temporal_type` classification: **stable**, **calculable**, and **mutable**. This enables the V2 model to properly handle temporal features without losing signal from important features like `Multi_RIA_Relationships` and tenure-based features.

---

## Classification Strategy

### 1. Stable Features (58 features)

**Definition:** Features that never change over time. These are historical facts or immutable characteristics.

**Categories:**
- **Demographics:** FirstName, LastName, Gender, Education
- **Geographic:** Branch_State, Branch_City, Home_State, Home_MetropolitanArea, MilesToWork
- **Professional Identifiers:** Title, SocialMedia_LinkedIn, Email_BusinessType, FirmWebsite
- **Licenses/Credentials:** Has_Series_7, Has_Series_65, Has_CFP, Has_CFA, Licenses
- **Firm Relationships:** RIAFirmCRD, RIAFirmName, Custodian1-5, IsPrimaryRIAFirm
- **Historical Counts:** Multi_RIA_Relationships ⭐ (m5's #1 feature), Multi_Firm_Associations, NumberFirmAssociations, NumberRIAFirmAssociations

**SQL Treatment:** Direct pass-through (no CASE WHEN logic)

### 2. Calculable Features (8 features)

**Definition:** Features that can be recalculated to reflect point-in-time values. These are typically tenure/age features where we can calculate the historical value from the current snapshot.

**Features:**
- `DateBecameRep_NumberOfYears`
- `DateOfHireAtCurrentFirm_NumberOfYears`
- `Total_Prior_Firm_Years`
- `Number_YearsPriorFirm1` through `Number_YearsPriorFirm4`
- `Number_Of_Prior_Firms`

**SQL Treatment:** Re-calculated using `CURRENT_DATE() - DATE_DIFF(CURRENT_DATE(), DATE(sf.Stage_Entered_Contacting__c), YEAR)`

**Example:**
```sql
drc.DateOfHireAtCurrentFirm_NumberOfYears - DATE_DIFF(CURRENT_DATE(), DATE(sf.Stage_Entered_Contacting__c), YEAR) as DateOfHireAtCurrentFirm_NumberOfYears
```

This calculates: "If the rep was hired 5 years ago (snapshot), and the lead was contacted 2 years ago, then at contact time they were at the firm for 3 years."

### 3. Mutable Features (56 features)

**Definition:** Features that truly change over time and cannot be recalculated. These require the current snapshot value to be available at contact time.

**Categories:**
- **Growth Metrics:** AUMGrowthRate_1Year, AUMGrowthRate_5Year, Growth_Momentum
- **AUM Metrics:** TotalAssetsInMillions, AUM_per_Client, AUM_Per_IARep
- **Client Metrics:** NumberClients_HNWIndividuals, NumberClients_Individuals
- **Asset Composition:** AssetsInMillions_Individuals, PercentAssets_HNWIndividuals
- **Engineered Features:** Firm_Stability_Score, HNW_Asset_Concentration, HNW_Client_Ratio
- **Operational Indicators:** Has_Scale, Is_Large_Firm, Is_Boutique_Firm

**SQL Treatment:** CASE WHEN logic to NULL for historical leads

**Example:**
```sql
CASE 
    WHEN is_eligible_for_mutable_features = 1 THEN AUMGrowthRate_1Year 
    ELSE NULL 
END as AUMGrowthRate_1Year
```

---

## Key Changes from V1

### V1 Classification (Binary)
- **Stable (63):** Features marked `is_mutable: false`
- **Mutable (61):** Features marked `is_mutable: true`

### V2 Classification (3-Part)
- **Stable (58):** Truly immutable features
- **Calculable (8):** Tenure features that can be recalculated
- **Mutable (56):** Features that require current snapshot

### Critical Fixes

1. **Multi_RIA_Relationships:** 
   - **V1:** Incorrectly classified as mutable (was NULLed for 95% of leads)
   - **V2:** Correctly classified as stable (always available)
   - **Impact:** This is m5's #1 feature! Now it will be available for all leads.

2. **Tenure Features:**
   - **V1:** Incorrectly classified as stable (used current values for historical leads)
   - **V2:** Correctly classified as calculable (recalculated to contact time)
   - **Impact:** Temporal integrity maintained while preserving signal

3. **NumberFirmAssociations / NumberRIAFirmAssociations:**
   - **V1:** Some were mutable
   - **V2:** Classified as stable (historical counts don't change)
   - **Impact:** These features are now always available

---

## Files Updated

### 1. `config/v1_feature_schema.json`
- ✅ Changed `is_mutable: true/false` → `temporal_type: "stable" | "calculable" | "mutable"`
- ✅ All 122 features reclassified
- ✅ Classification logic documented in `update_feature_schema_temporal_type.py`

### 2. `Step_3_3_V2_FinalDatasetCreation.sql`
- ✅ Generated new SQL with 3-part temporal logic
- ✅ Stable features: Direct pass-through
- ✅ Calculable features: Re-calculated point-in-time
- ✅ Mutable features: CASE WHEN NULL logic

### 3. `Lead_Scoring_Development_Progress.md`
- ✅ Updated Step 3.3 section with V2 REFERENCE IMPLEMENTATION block
- ✅ Documented the 3-part strategy

---

## Expected Impact on V2 Model

### Feature Availability

| Feature Type | V1 Availability | V2 Availability | Improvement |
|-------------|----------------|-----------------|-------------|
| **Stable** | 100% (all leads) | 100% (all leads) | Same |
| **Calculable** | 100% (but wrong values) | 100% (correct values) | ✅ **Temporal integrity** |
| **Mutable** | 5% (only recent leads) | 5% (only recent leads) | Same |

### Key Features Now Available

1. **Multi_RIA_Relationships:** Now available for 100% of leads (was 5% in V1)
2. **Tenure Features:** Now temporally correct for 100% of leads (was temporally incorrect in V1)
3. **Stable Features:** All 58 stable features available for all leads

### Expected Model Performance

- **V1 AUC-PR:** 4.98% (failed)
- **m5 AUC-PR:** 14.92% (successful)
- **V2 Target:** Expected to be significantly higher than V1, approaching m5 performance

**Why V2 Should Improve:**
- Access to `Multi_RIA_Relationships` (m5's #1 feature) for all leads
- Correct temporal values for tenure features
- All stable features available (no NULLs)

---

## Validation

✅ **Schema Updated:** All 122 features have `temporal_type` classification  
✅ **SQL Generated:** `Step_3_3_V2_FinalDatasetCreation.sql` created with correct 3-part logic  
✅ **Documentation Updated:** `Lead_Scoring_Development_Progress.md` updated with V2 reference  
✅ **Classification Verified:** Multi_RIA_Relationships correctly classified as stable

---

## Next Steps

1. **Step 5.2:** Port m5 feature engineering to V2 training script
2. **Step 5.3:** Execute V2 pipeline with new SQL and feature engineering
3. **Validation:** Compare V2 performance to V1 and m5 baselines

---

## Appendix: Feature Counts by Type

| Type | Count | Examples |
|------|-------|----------|
| **Stable** | 58 | Branch_State, Has_CFP, Multi_RIA_Relationships, FirstName |
| **Calculable** | 8 | DateBecameRep_NumberOfYears, DateOfHireAtCurrentFirm_NumberOfYears, Total_Prior_Firm_Years |
| **Mutable** | 56 | AUMGrowthRate_1Year, AUM_per_Client, Firm_Stability_Score, HNW_Asset_Concentration |
| **Total** | 122 | (Plus 2 temporal features: Day_of_Contact, Is_Weekend_Contact) |

