# V6 Feature Engineering Review - Boolean Conversion & Signal Detection

**Date:** 2025-11-04  
**Purpose:** Identify fields that should be converted to boolean flags and fields that should be dropped (non-signals)

---

## 🚨 **CRITICAL ISSUES FOUND**

### **1. Yes/No Fields Kept as Strings (Should be Boolean)**

The following fields are currently kept as STRING but contain "Yes"/"No"/"Unknown" values. These should be converted to boolean flags (0/1) for better signal:

#### **High Priority - Convert to Boolean:**
1. **`BreakawayRep`** (Line 298)
   - **Current:** `CAST(BreakawayRep AS STRING) as BreakawayRep`
   - **Should be:** `CASE WHEN BreakawayRep = 'Yes' THEN 1 ELSE 0 END as Is_BreakawayRep`
   - **Values:** "Yes", "No", null
   - **Rationale:** Presence matters more than the exact value

2. **`InsuranceLicensed`** (NOT in current plan - should be added)
   - **Current:** Not included
   - **Should be:** `CASE WHEN InsuranceLicensed = 'Yes' THEN 1 ELSE 0 END as Has_Insurance_License`
   - **Values:** "Yes", null
   - **Rationale:** Binary signal - either licensed or not

3. **`NonProducer`** (NOT in current plan - should be added)
   - **Current:** Not included
   - **Should be:** `CASE WHEN NonProducer = 'Yes' THEN 1 ELSE 0 END as Is_NonProducer`
   - **Values:** "Yes", "No", "Unknown"
   - **Rationale:** Important signal - non-producers are less likely to convert

4. **`IndependentContractor`** (NOT in current plan - should be added)
   - **Current:** Not included
   - **Should be:** `CASE WHEN IndependentContractor = 'Yes' THEN 1 ELSE 0 END as Is_IndependentContractor`
   - **Values:** "Yes", "No", "Unknown"
   - **Rationale:** Employment type is a strong signal

5. **`Owner`** (NOT in current plan - should be added)
   - **Current:** Not included
   - **Should be:** `CASE WHEN Owner = 'Yes' THEN 1 ELSE 0 END as Is_Owner`
   - **Values:** "Yes", null
   - **Rationale:** Firm ownership is a strong signal

6. **`Office_USPSCertified`** (NOT in current plan - should be added)
   - **Current:** Not included
   - **Should be:** `CASE WHEN Office_USPSCertified = 'Yes' THEN 1 ELSE 0 END as Office_USPS_Certified`
   - **Values:** "Yes", "No", null
   - **Rationale:** Address quality signal

7. **`Home_USPSCertified`** (NOT in current plan - should be added)
   - **Current:** Not included
   - **Should be:** `CASE WHEN Home_USPSCertified = 'Yes' THEN 1 ELSE 0 END as Home_USPS_Certified`
   - **Values:** "Yes", "No", null
   - **Rationale:** Address quality signal

#### **Medium Priority - Consider Boolean:**
8. **`SocialMedia_LinkedIn`** (Line 335)
   - **Current:** `CAST(SocialMedia_LinkedIn AS STRING) as SocialMedia_LinkedIn`
   - **Should be:** Keep URL for linking, but ALSO add: `CASE WHEN SocialMedia_LinkedIn IS NOT NULL THEN 1 ELSE 0 END as Has_LinkedIn`
   - **Rationale:** Presence of LinkedIn profile might be more predictive than the URL itself

---

## ❌ **Fields That Should Be Dropped (Non-Signals)**

### **1. PII Fields (Already in PII Drop List - Good)**
- ✅ `FirstName`, `LastName` - Already in Step 4.2 PII drop list
- ✅ `Branch_City`, `Branch_County`, `Branch_ZipCode` - Already in PII drop list
- ✅ `Home_City`, `Home_County`, `Home_ZipCode` - Already in PII drop list
- ✅ `RIAFirmName` - Already in PII drop list
- ✅ `PersonalWebpage`, `Notes` - Already in PII drop list

### **2. Identifiers (Should NOT be Features - Keep for Linking Only)**
- ⚠️ **`RepCRD`** - Keep for linking, but should NOT be a feature (Step 4.2 mentions this)
- ⚠️ **`RIAFirmCRD`** - Keep for linking, but should NOT be a feature (Step 4.2 mentions this)
- ⚠️ **`Id`** (from Lead table) - Keep for linking, but should NOT be a feature

### **3. String Fields with Low Predictive Value (Consider Dropping)**

These are currently kept as strings but might not provide strong signals:

1. **`Title`** (Line 329)
   - **Current:** `CAST(Title AS STRING) as Title`
   - **Issue:** Many unique values, might not be predictive
   - **Recommendation:** 
     - Option A: Drop entirely (if not in model)
     - Option B: Create boolean flags for common titles (e.g., `Is_PortfolioManager`, `Is_BranchManager`)
     - Option C: Keep but treat as high-cardinality categorical (will be one-hot encoded)

2. **`Education1`** (Line 293)
   - **Current:** `CAST(Education1 AS STRING) as Education`
   - **Issue:** Many unique values, might not be predictive
   - **Recommendation:** 
     - Option A: Drop entirely
     - Option B: Create boolean flags for common degrees (e.g., `Has_MBA`, `Has_Bachelors`)
     - Option C: Keep but treat as categorical

3. **`Gender`** (Line 294)
   - **Current:** `CAST(Gender AS STRING) as Gender`
   - **Issue:** Low cardinality (M/F), but might not be predictive and could raise ethical concerns
   - **Recommendation:** 
     - Option A: Drop entirely (recommended - may not be predictive and raises ethical concerns)
     - Option B: Keep as categorical (if determined to be predictive)

4. **`BreakawayRep`** (Line 298)
   - **Current:** `CAST(BreakawayRep AS STRING) as BreakawayRep`
   - **Issue:** Should be boolean (see above)
   - **Recommendation:** Convert to boolean flag

5. **`Licenses`** (Line 291)
   - **Current:** `CAST(LicensesDesignations AS STRING) as Licenses`
   - **Issue:** This is a concatenated string, but we already have boolean flags for each license
   - **Recommendation:** 
     - Keep for reference, but it's redundant with `Has_Series_7`, `Has_Series_65`, etc.
     - Consider dropping if all important licenses are covered by boolean flags

6. **`RegulatoryDisclosures`** (Line 292)
   - **Current:** `CAST(RegulatoryDisclosures AS STRING) as RegulatoryDisclosures`
   - **Issue:** We already have `Has_Disclosure` boolean flag
   - **Recommendation:** 
     - Keep for reference, but redundant with `Has_Disclosure`
     - Consider dropping if `Has_Disclosure` covers the signal

---

## ✅ **Fields That Are Correctly Handled**

### **Boolean Conversions (Already Correct):**
- ✅ `DuallyRegisteredBDRIARep` → Boolean (Line 296)
- ✅ `IsPrimaryRIAFirm` → Boolean (Line 297)
- ✅ `Has_Series_7`, `Has_Series_65`, `Has_Series_66`, `Has_Series_24` → Boolean (Lines 343-346)
- ✅ `Has_CFP`, `Has_CFA`, `Has_CIMA`, `Has_AIF` → Boolean (Lines 347-350)
- ✅ `Has_Disclosure` → Boolean (Line 351)

### **Numeric Fields (Correctly Kept as Numeric):**
- ✅ All tenure fields (`DateBecameRep_NumberOfYears`, etc.)
- ✅ All count fields (`NumberFirmAssociations`, `NumberRIAFirmAssociations`, etc.)
- ✅ `MilesToWork` - Keep as numeric (we create boolean flags from it in Step 3.2)

---

## 📋 **Recommended Changes to Step 1.5**

### **Add These Boolean Conversions:**
```sql
-- Breakaway rep (convert to boolean)
CASE WHEN BreakawayRep = 'Yes' THEN 1 ELSE 0 END as Is_BreakawayRep,

-- Insurance license
CASE WHEN InsuranceLicensed = 'Yes' THEN 1 ELSE 0 END as Has_Insurance_License,

-- Non-producer flag
CASE WHEN NonProducer = 'Yes' THEN 1 ELSE 0 END as Is_NonProducer,

-- Independent contractor
CASE WHEN IndependentContractor = 'Yes' THEN 1 ELSE 0 END as Is_IndependentContractor,

-- Owner status
CASE WHEN Owner = 'Yes' THEN 1 ELSE 0 END as Is_Owner,

-- USPS certified addresses
CASE WHEN Office_USPSCertified = 'Yes' THEN 1 ELSE 0 END as Office_USPS_Certified,
CASE WHEN Home_USPSCertified = 'Yes' THEN 1 ELSE 0 END as Home_USPS_Certified,

-- LinkedIn presence (in addition to URL)
CASE WHEN SocialMedia_LinkedIn IS NOT NULL THEN 1 ELSE 0 END as Has_LinkedIn,
```

### **Remove or Update These String Fields:**
```sql
-- Remove: BreakawayRep (replaced by Is_BreakawayRep boolean)
-- Keep: Title (but consider creating boolean flags for common titles)
-- Keep: Education1 (but consider creating boolean flags for common degrees)
-- Consider: Gender (drop if not predictive and/or raises ethical concerns)
-- Keep: Licenses (for reference, but redundant with boolean flags)
-- Keep: RegulatoryDisclosures (for reference, but redundant with Has_Disclosure)
```

---

## 📋 **Recommended Changes to Step 4.2 (PII Drop List)**

### **Add to PII Drop List:**
- `Branch_City` ✅ (already in list)
- `Branch_County` ✅ (already in list)
- `Branch_ZipCode` ✅ (already in list)
- `Home_City` ✅ (already in list)
- `Home_County` ✅ (already in list)
- `Home_ZipCode` ✅ (already in list)
- `FirstName` ✅ (already in list)
- `LastName` ✅ (already in list)
- `RIAFirmName` ✅ (already in list)
- `PersonalWebpage` ✅ (already in list)
- `Notes` ✅ (already in list)

### **Add to Feature Drop List (Non-PII but Non-Signals):**
- `RepCRD` - Identifier, not a feature
- `RIAFirmCRD` - Identifier, not a feature (keep for linking but drop as feature)
- `Id` - Identifier, not a feature
- `Licenses` - Redundant with boolean flags
- `RegulatoryDisclosures` - Redundant with `Has_Disclosure`
- `BreakawayRep` - Replaced by `Is_BreakawayRep` boolean
- `Gender` - Consider dropping (low cardinality, may not be predictive, ethical concerns)
- `Title` - Consider dropping (high cardinality, may not be predictive)
- `Education1` - Consider dropping (high cardinality, may not be predictive)

---

## 🎯 **Summary**

### **Immediate Actions Needed:**
1. ✅ Convert `BreakawayRep` to boolean `Is_BreakawayRep`
2. ✅ Add `InsuranceLicensed` → `Has_Insurance_License` boolean
3. ✅ Add `NonProducer` → `Is_NonProducer` boolean
4. ✅ Add `IndependentContractor` → `Is_IndependentContractor` boolean
5. ✅ Add `Owner` → `Is_Owner` boolean
6. ✅ Add `Office_USPSCertified` → `Office_USPS_Certified` boolean
7. ✅ Add `Home_USPSCertified` → `Home_USPS_Certified` boolean
8. ✅ Add `Has_LinkedIn` boolean flag (in addition to `SocialMedia_LinkedIn` URL)

### **Fields to Drop (Non-Signals):**
1. ✅ `RepCRD`, `RIAFirmCRD`, `Id` - Identifiers (keep for linking, drop as features)
2. ⚠️ `Licenses` - Redundant with boolean flags
3. ⚠️ `RegulatoryDisclosures` - Redundant with `Has_Disclosure`
4. ⚠️ `BreakawayRep` - Replaced by `Is_BreakawayRep`
5. ⚠️ `Gender` - Consider dropping (ethical concerns, may not be predictive)
6. ⚠️ `Title` - Consider dropping or creating boolean flags
7. ⚠️ `Education1` - Consider dropping or creating boolean flags

---

## ✅ **Next Steps**

1. Update Step 1.5 SQL to include new boolean conversions
2. Update Step 4.2 PII drop list to include identifier fields as non-features
3. Document decision on `Gender`, `Title`, `Education1` (drop vs. keep vs. transform)

