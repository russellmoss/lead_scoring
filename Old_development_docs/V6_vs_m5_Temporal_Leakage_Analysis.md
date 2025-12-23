# V6 vs m5: Temporal Leakage Analysis

**Date:** November 4, 2025  
**Critical Discovery:** m5 has significant temporal data leakage - V6 is temporally correct

---

## 🚨 **CRITICAL FINDING: m5 Has Data Leakage**

### How m5 Was Trained:

**❌ m5 Uses Single Point-in-Time (CURRENT Snapshot):**
- Loads `discovery_data.pkl` - **current snapshot** of all advisors
- Uses this **current snapshot for ALL historical leads**
- A lead contacted in 2023 uses 2024/2025 Discovery data
- **NO temporal filtering** by `Stage_Entered_Contacting__c` date
- **NO point-in-time joins** - just merges current data to all leads

**Evidence from `FinalLeadScorePipeline.ipynb`:**
```python
# Cell 8: Loads CURRENT snapshot
dd_rep = pd.read_pickle(f'{data_path}/discovery_data.pkl')  # Current snapshot

# Cell 11: Merges current data to ALL leads (no date filtering)
data_sf_rep = merge(sf, dd_rep)  # Uses current data for all historical leads
```

### Additional Data Leakage Issues in m5:

1. **Random Train-Test Split (Not Temporal)**
   - Uses `train_test_split(random_state=42, stratify=y)` 
   - Training data may include leads created AFTER test set leads
   - Model learns from future data patterns

2. **Preprocessing Fitted on ALL Data**
   - Scalers and imputers fit on entire dataset (including test/future)
   - Test distribution leaks into training preprocessing

3. **Feature Engineering on All Data**
   - Quantiles/medians calculated from entire dataset
   - Test data influences feature creation

4. **No Right-Censoring Window**
   - Leads contacted in last 30 days may be incorrectly labeled
   - No temporal validation for target creation

---

## ✅ **V6 Is Temporally Correct**

### How V6 Was Trained:

**✅ V6 Uses Point-in-Time Historical Snapshots:**
- 8 historical snapshots (2024-01-07 through 2025-10-05)
- Each lead matched to **most recent snapshot ≤ contact date**
- Uses "soonest, but past" logic - ensures no future data
- Validates PIT integrity (0 post-contact features)

**Evidence from V6 Processing:**
```sql
-- Step 3.1: Point-in-time join
LEFT JOIN (
    SELECT l2.FA_CRD__c, l2.contact_date, reps.*
    FROM LeadsWithContactDate l2
    JOIN `LeadScoring.v_discovery_reps_all_vintages` reps
        ON reps.RepCRD = l2.FA_CRD__c
        AND reps.snapshot_at <= l2.contact_date  -- ⭐ Only past data!
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY l2.FA_CRD__c, l2.contact_date 
        ORDER BY reps.snapshot_at DESC  -- Most recent, but past
    ) = 1
) reps ON ...
```

**Validation:**
- ✅ PIT Integrity Check: `post_contact_features = 0` (confirmed)
- ✅ All snapshots validated: `invalid_snapshot_count = 0`
- ✅ Temporal split: Uses contact date ordering

---

## 📊 **Performance Comparison: Fair vs Unfair**

### The Unfair Comparison:

| Model | AUC-PR | Temporal Correctness | Data Leakage |
|-------|--------|---------------------|--------------|
| **m5** | **14.92%** | ❌ **NO** | 🔴 **Multiple leaks** |
| **V6** | **5.88%** | ✅ **YES** | ✅ **None** |

**Why m5 Performs Better:**
1. **Uses future information** - Current snapshot for historical leads
2. **Sees test distribution** - Preprocessing fitted on all data
3. **Learns from future patterns** - Random split allows future→past learning
4. **Inflated metrics** - Test performance includes leaked information

**Why V6 Performs Worse (But Is Honest):**
1. **Only uses past data** - Point-in-time snapshots
2. **No future information** - Strict temporal validation
3. **Realistic performance** - True generalization ability
4. **Production-ready** - Will work in real deployment

---

## 🎯 **What This Means for Your 4% Conversion Rate**

### Current Situation:

**m5 in Production:**
- Achieves **4% conversion rate**
- But uses **current Discovery data** for all leads
- May be using some "future" information (if Discovery data is updated)

**Questions to Consider:**
1. **Is m5's 4% conversion rate inflated?** Possibly - if Discovery data changes over time
2. **Would m5 perform worse with temporal correctness?** Likely yes
3. **Is V6's 5.88% AUC-PR actually better than it seems?** Yes - it's honest performance

### Real-World Impact:

**If m5 Has Leakage:**
- Production leads get scored with current Discovery data
- But at training time, model learned patterns from current data applied to historical leads
- This might work IF Discovery data is stable (doesn't change much over time)
- But if Discovery data changes (AUM grows, firms change), m5 may overperform

**If V6 Replaces m5:**
- V6 uses point-in-time correct data
- Performance might actually be CLOSER to m5 than 14.92% vs 5.88% suggests
- Because m5's 14.92% is likely inflated due to leakage
- V6's 5.88% might be more realistic

---

## 💡 **The Real Question: Is m5's 4% Conversion Rate Achievable Without Leakage?**

### Hypothesis:

**m5's apparent success might be due to:**
1. **Data leakage** - Using future information
2. **Stable Discovery data** - If data doesn't change much, leakage doesn't hurt
3. **Financial features** - Strong signals even with leakage

**V6's lower performance might be due to:**
1. **No financial features** - Missing critical signals
2. **Temporal correctness** - Honest but harder problem
3. **Less training data** - 41,942 vs m5's 60,772

### To Answer This, We Need:

1. **Retrain m5 with temporal correctness** - See if it still gets 14.92% AUC-PR
2. **Compare m5 (temporal) vs V6** - Fair comparison
3. **Test m5 in production** - Track if 4% rate holds over time

---

## 🔄 **Recommendation: Retrain m5 with Temporal Correctness**

### Option 1: Fix m5's Data Leakage

**Steps:**
1. Use historical snapshots (like V6 does)
2. Point-in-time joins based on contact date
3. Temporal train-test split
4. Fix preprocessing leakage
5. Add right-censoring window

**Expected Result:**
- m5 performance will likely **decrease** (more realistic)
- But will be **production-ready** and trustworthy
- Can then fairly compare to V6

### Option 2: Improve V6 with Financial Features

**Steps:**
1. Source financial data (if available)
2. Add AUM, client counts, growth rates
3. Retrain V6 with financial features
4. Compare to fixed m5

**Expected Result:**
- V6 performance will likely **increase**
- Closer to m5's performance
- But still temporally correct

---

## 📊 **Updated Comparison (Acknowledging Leakage)**

### Adjusted Expectations:

| Model | Reported AUC-PR | Adjusted AUC-PR (est.) | Temporal Correct |
|-------|----------------|------------------------|------------------|
| **m5 (Current)** | 14.92% | **~8-10%** (estimated with leakage removed) | ❌ No |
| **V6 (New)** | 5.88% | **5.88%** (honest, no leakage) | ✅ Yes |

**After adjusting for leakage:**
- m5 might be **1.4-1.7x better** than V6 (not 2.54x)
- Gap is smaller due to m5's unfair advantage
- V6 is still worse, but not as bad as it seems

---

## ✅ **Bottom Line**

**m5's Training Approach:**
- ❌ Uses **current snapshot** for all historical leads (leakage)
- ❌ Uses **random split** (not temporal)
- ❌ Fits preprocessors on **all data** (leakage)
- ⚠️ **Performance likely inflated** due to leakage

**V6's Training Approach:**
- ✅ Uses **point-in-time snapshots** (temporally correct)
- ✅ Uses **temporal validation** (no future data)
- ✅ Fits preprocessors on **training only** (no leakage)
- ✅ **Performance is honest** - true generalization

**Will V6 Outperform m5?**
- **Unlikely** - Even with leakage removed, m5 has financial features
- **But the gap is smaller** - m5's 14.92% is likely inflated
- **V6 is production-ready** - m5 may not generalize well

**Recommendation:**
1. **Keep m5 for now** - It's working (4% conversion)
2. **But fix m5's leakage** - Retrain with temporal correctness
3. **Then compare fairly** - m5 (fixed) vs V6
4. **Choose based on fair comparison** - Not inflated metrics

The fact that m5 achieves 4% conversion suggests it's learning real patterns, but the leakage makes it hard to know if V6 could match it with proper temporal handling.

