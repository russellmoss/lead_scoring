# V6 Engineered Features - What We CAN Calculate

**Date:** 2025-11-04  
**Purpose:** List all m5 engineered features that CAN be calculated from V6 data (RIARepDataFeed)

---

## ✅ **Engineered Features We CAN Calculate (No Financial Data Needed)**

### **1. Firm_Stability_Score** ✅
**m5 Formula:**
```python
Firm_Stability_Score = DateOfHireAtCurrentFirm_NumberOfYears / (NumberOfPriorFirms + 1)
```

**V6 SQL:**
```sql
SAFE_DIVIDE(p.DateOfHireAtCurrentFirm_NumberOfYears, NULLIF((p.NumberOfPriorFirms + 1), 0)) as Firm_Stability_Score
```

**Available in V6:** ✅ Yes - All required fields exist
**m5 Importance:** #8 (0.0211)

---

### **2. Is_Veteran_Advisor** ✅
**m5 Formula:**
```python
Is_Veteran_Advisor = (DateBecameRep_NumberOfYears > 10).astype(int)
```

**V6 SQL:**
```sql
CASE WHEN p.DateBecameRep_NumberOfYears > 10 THEN 1 ELSE 0 END as Is_Veteran_Advisor
```

**Available in V6:** ✅ Yes
**m5 Importance:** #6 (0.0225)

---

### **3. Is_New_To_Firm** ✅
**m5 Formula:**
```python
Is_New_To_Firm = (DateOfHireAtCurrentFirm_NumberOfYears < 2).astype(int)
```

**V6 SQL:**
```sql
CASE WHEN p.DateOfHireAtCurrentFirm_NumberOfYears < 2 THEN 1 ELSE 0 END as Is_New_To_Firm
```

**Available in V6:** ✅ Yes
**m5 Importance:** #23 (0.0130)

---

### **4. High_Turnover_Flag** ✅
**m5 Formula:**
```python
High_Turnover_Flag = (
    (NumberOfPriorFirms > 3) & 
    (AverageTenureAtPriorFirms < 3)
).astype(int)
```

**V6 SQL:**
```sql
CASE WHEN p.NumberOfPriorFirms > 3 AND p.AverageTenureAtPriorFirms < 3 THEN 1 ELSE 0 END as High_Turnover_Flag
```

**Available in V6:** ✅ Yes - Both fields exist
**m5 Importance:** Not in top 25, but available

---

### **5. Multi_RIA_Relationships** ✅
**m5 Formula:**
```python
Multi_RIA_Relationships = (NumberRIAFirmAssociations > 1).astype(int)
```

**V6 SQL:**
```sql
CASE WHEN p.NumberRIAFirmAssociations > 1 THEN 1 ELSE 0 END as Multi_RIA_Relationships
```

**Available in V6:** ✅ Yes
**m5 Importance:** #1 (0.0816) - **MOST IMPORTANT FEATURE!**

---

### **6. Complex_Registration** ✅
**m5 Formula:**
```python
Complex_Registration = (
    (NumberFirmAssociations > 2) | 
    (NumberRIAFirmAssociations > 1)
).astype(int)
```

**V6 SQL:**
```sql
CASE WHEN p.NumberFirmAssociations > 2 OR p.NumberRIAFirmAssociations > 1 THEN 1 ELSE 0 END as Complex_Registration
```

**Available in V6:** ✅ Yes
**m5 Importance:** #18 (0.0152)

---

### **7. Remote_Work_Indicator** ✅
**m5 Formula:**
```python
Remote_Work_Indicator = (MilesToWork > 50).astype(int)
```

**V6 SQL:**
```sql
CASE WHEN p.MilesToWork > 50 THEN 1 ELSE 0 END as Remote_Work_Indicator
```

**Available in V6:** ✅ Yes
**m5 Importance:** #22 (0.0131)

---

### **8. Local_Advisor** ✅
**m5 Formula:**
```python
Local_Advisor = (MilesToWork <= 10).astype(int)
```

**V6 SQL:**
```sql
CASE WHEN p.MilesToWork <= 10 THEN 1 ELSE 0 END as Local_Advisor
```

**Available in V6:** ✅ Yes
**m5 Importance:** Not in top 25, but available

---

### **9. Home_Zip_3Digit** ✅
**m5 Formula:** Not in m5, but useful feature engineering
**V6 SQL:**
```sql
CASE 
    WHEN p.Home_MetropolitanArea IS NULL AND p.Home_ZipCode IS NOT NULL 
    THEN SUBSTR(CAST(CAST(p.Home_ZipCode AS INT64) AS STRING), 1, 3)
    ELSE NULL
END as Home_Zip_3Digit
```

**Available in V6:** ✅ Yes
**m5 Importance:** Not in m5, but good for imputation

---

### **10. Multi_State_Registered** ✅ (NEW - not in m5)
**V6 SQL:**
```sql
CASE WHEN p.Number_RegisteredStates > 10 THEN 1 ELSE 0 END as Multi_State_Registered
```

**Available in V6:** ✅ Yes - `Number_RegisteredStates` exists
**m5 Importance:** Not in m5, but could be useful

---

### **11. Branch_Advisors_per_Firm_Association** ✅ (NEW - not in m5)
**V6 SQL:**
```sql
SAFE_DIVIDE(p.Number_BranchAdvisors, NULLIF(p.NumberFirmAssociations, 0)) as Branch_Advisors_per_Firm_Association
```

**Available in V6:** ✅ Yes
**m5 Importance:** Not in m5, but could be useful

---

## ❌ **Engineered Features We CANNOT Calculate (Require Financial Data)**

### **1. AUM_per_Client**
**Requires:** `TotalAssetsInMillions`, `NumberClients_Individuals`
**Status:** ❌ Missing in V6

### **2. AUM_per_Employee**
**Requires:** `TotalAssetsInMillions`, `Number_Employees`
**Status:** ❌ Missing in V6

### **3. AUM_per_IARep**
**Requires:** `TotalAssetsInMillions`, `Number_IAReps`
**Status:** ❌ Missing in V6

### **4. Growth_Momentum**
**Requires:** `AUMGrowthRate_1Year`, `AUMGrowthRate_5Year`
**Status:** ❌ Missing in V6

### **5. Growth_Acceleration**
**Requires:** `AUMGrowthRate_1Year`, `AUMGrowthRate_5Year`
**Status:** ❌ Missing in V6

### **6. Experience_Efficiency**
**Requires:** `TotalAssetsInMillions`, `DateBecameRep_NumberOfYears`
**Status:** ❌ Missing in V6

### **7. HNW_Client_Ratio**
**Requires:** `NumberClients_HNWIndividuals`, `NumberClients_Individuals`
**Status:** ❌ Missing in V6

### **8. HNW_Asset_Concentration**
**Requires:** `AssetsInMillions_HNWIndividuals`, `TotalAssetsInMillions`
**Status:** ❌ Missing in V6
**m5 Importance:** #3 (0.0587) - High importance, but missing

### **9. Individual_Asset_Ratio**
**Requires:** `AssetsInMillions_Individuals`, `TotalAssetsInMillions`
**Status:** ❌ Missing in V6
**m5 Importance:** #10 (0.0197)

### **10. Alternative_Investment_Focus**
**Requires:** `AssetsInMillions_MutualFunds`, `AssetsInMillions_PrivateFunds`, `TotalAssetsInMillions`
**Status:** ❌ Missing in V6

### **11. Is_Large_Firm**
**Requires:** `Number_Employees > 100`
**Status:** ❌ Missing in V6 (`Number_Employees` not available)

### **12. Is_Boutique_Firm**
**Requires:** `Number_Employees <= 20` AND `AverageAccountSize > quantile(0.75)`
**Status:** ❌ Missing in V6

### **13. Has_Scale**
**Requires:** `TotalAssetsInMillions > 500` OR `Number_InvestmentAdvisoryClients > 100`
**Status:** ❌ Missing in V6

### **14. Premium_Positioning**
**Requires:** `AverageAccountSize > quantile(0.75)` AND `PercentClients_Individuals < 50`
**Status:** ❌ Missing in V6

### **15. Mass_Market_Focus**
**Requires:** `PercentClients_Individuals > 80` AND `AverageAccountSize < median()`
**Status:** ❌ Missing in V6
**m5 Importance:** #2 (0.0708) - Very high importance, but missing

### **16. Clients_per_Employee**
**Requires:** `Number_InvestmentAdvisoryClients`, `Number_Employees`
**Status:** ❌ Missing in V6

### **17. Branch_Advisor_Density**
**Requires:** `Number_BranchAdvisors`, `Number_IAReps`
**Status:** ❌ Missing in V6 (requires `Number_IAReps`)
**m5 Importance:** #5 (0.0240)

### **18. Clients_per_IARep**
**Requires:** `Number_InvestmentAdvisoryClients`, `Number_IAReps`
**Status:** ❌ Missing in V6

### **19. Primarily_US_Clients**
**Requires:** `Percent_ClientsUS > 90`
**Status:** ❌ Missing in V6 (`Percent_ClientsUS` not available)

### **20. International_Presence**
**Requires:** `Percent_ClientsUS < 80`
**Status:** ❌ Missing in V6

### **21. Quality_Score**
**Requires:** Multiple financial and tenure features
**Status:** ❌ Partially missing (can calculate some components, but not all)

### **22. Positive_Growth_Trajectory**
**Requires:** `AUMGrowthRate_1Year > 0` AND `AUMGrowthRate_5Year > 0`
**Status:** ❌ Missing in V6

### **23. Accelerating_Growth**
**Requires:** `AUMGrowthRate_1Year > (AUMGrowthRate_5Year / 5)`
**Status:** ❌ Missing in V6
**m5 Importance:** #25 (0.0128)

---

## 📊 **Summary**

### **Available in V6 (11 features):**
1. ✅ `Firm_Stability_Score` (#8 in m5)
2. ✅ `Is_Veteran_Advisor` (#6 in m5)
3. ✅ `Is_New_To_Firm` (#23 in m5)
4. ✅ `High_Turnover_Flag`
5. ✅ `Multi_RIA_Relationships` (#1 in m5 - **MOST IMPORTANT!**)
6. ✅ `Complex_Registration` (#18 in m5)
7. ✅ `Remote_Work_Indicator` (#22 in m5)
8. ✅ `Local_Advisor`
9. ✅ `Home_Zip_3Digit`
10. ✅ `Multi_State_Registered` (new)
11. ✅ `Branch_Advisors_per_Firm_Association` (new)

### **Missing in V6 (20 features):**
- All financial-based features (AUM, client counts, growth rates)
- All scale/firm size features (require `Number_Employees` or AUM)
- All client composition features (require client/asset breakdowns)

### **Impact:**
- **Good news:** We have m5's #1 feature (`Multi_RIA_Relationships`) and several other top features
- **Bad news:** Missing #2 (`Mass_Market_Focus`), #3 (`HNW_Asset_Concentration`), #5 (`Branch_Advisor_Density`), #10 (`Individual_Asset_Ratio`)

---

## ✅ **Updated Step 3.2 SQL**

The V6 plan already includes these calculations. The key ones are:
- `Firm_Stability_Score` (m5 formula)
- `Is_Veteran_Advisor`
- `Is_New_To_Firm`
- `High_Turnover_Flag`
- `Multi_RIA_Relationships`
- `Complex_Registration`
- `Remote_Work_Indicator`
- `Local_Advisor`

All financial-based features are set to NULL, which is correct.

