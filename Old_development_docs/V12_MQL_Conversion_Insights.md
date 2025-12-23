# V12 Model: What Makes Someone Most Likely to Become an MQL?

**Generated:** November 5, 2025  
**Model:** V12 with Binned Features + Fixed Gender Encoding  
**Performance:** 6.00% AUC-PR, 1.27x lift over baseline

---

## 🎯 Top 5 Most Important Factors for MQL Conversion

Based on feature importance and conversion rates:

### 1. **Low Firm Stability** (11.18% importance) 🏆

**What it means:** Advisors who move between firms frequently (spend < 30% of their career at current firm)

**MQL Rate:** **7.07%** (vs 2.53% for very stable advisors)

**Why it matters:**
- **2.8x higher** conversion than very stable advisors
- Indicates active job exploration
- These advisors are "in the market" and open to opportunities

**Actionable Insight:** Prioritize advisors who have changed firms 3+ times or have short tenure at current firm relative to their total career.

---

### 2. **Missing Gender Data** (8.03% importance) 🎯

**What it means:** Gender information is not available in Discovery data

**MQL Rate:** **9.27%** (vs 4.22% for Male, 3.03% for Female)

**Why it matters:**
- **2.2x higher** conversion than advisors with known gender
- Likely indicates newer advisors or incomplete data profiles
- May correlate with advisors who are newer to the industry or have less established profiles

**Actionable Insight:** Missing gender data is a strong signal - these leads should be prioritized.

---

### 3. **Long Tenure at Prior Firm 1** (7.41% importance) ⚠️

**What it means:** Spent 7+ years at their most recent prior firm

**MQL Rate:** **2.54%** (lower than average)

**Why it matters:**
- This is a **negative signal** - advisors with very long tenure at prior firm are less likely to convert
- Indicates they may be risk-averse or satisfied with their current situation
- Model uses this to identify less likely converters

**Actionable Insight:** Advisors who spent 7+ years at prior firm are lower priority (stable, less likely to move).

---

### 4. **Very High Firm Stability** (5.75% importance) ⚠️

**What it means:** Advisors who spend 90%+ of their career at current firm

**MQL Rate:** **2.53%** (lowest conversion rate)

**Why it matters:**
- **2.8x lower** conversion than low stability advisors
- Indicates advisors who are very satisfied and unlikely to move
- Model uses this as a strong negative signal

**Actionable Insight:** Very stable advisors are lowest priority - they're satisfied and unlikely to engage.

---

### 5. **Long Average Tenure at Prior Firms** (4.39% importance) ⚠️

**What it means:** Averaged 5-10 years at prior firms

**MQL Rate:** **2.77%** (lower than average)

**Why it matters:**
- Another **negative signal** - advisors with long average tenure are less likely to convert
- Indicates stability and risk aversion

**Actionable Insight:** Long average tenure = lower priority.

---

## 📊 Detailed Conversion Rates by Factor

### Firm Stability (Most Important Signal)

| Stability Level | MQL Rate | Total Leads | Lift vs Baseline |
|----------------|----------|-------------|------------------|
| **Low Stability (< 30%)** | **7.07%** | 1,145 | **2.8x** 🎯 |
| Moderate Stability (30-60%) | 5.42% | 2,416 | 2.1x |
| High Stability (60-90%) | 3.89% | 3,800 | 1.5x |
| **Very High Stability (90%+)** | **2.53%** | 29,293 | **1.0x** (baseline) |
| Missing/Zero | 6.10% | 5,249 | 2.4x |

**Key Insight:** Lower stability = higher conversion. Advisors who move frequently are actively exploring.

---

### Average Tenure at Prior Firms

| Average Tenure | MQL Rate | Total Leads | Interpretation |
|----------------|----------|-------------|---------------|
| **< 2 years avg** | **4.30%** | 5,610 | **Job hoppers - highest conversion** |
| 2-5 years avg | 3.89% | 15,652 | Moderate tenure |
| 5-10 years avg | 2.77% | 8,673 | Longer tenure |
| **10+ years avg** | **1.99%** | 2,458 | **Very stable - lowest conversion** |
| No Prior Firms | 1.15% | 523 | Career starters |

**Key Insight:** Short average tenure (< 2 years) = **2.2x higher** conversion than very long tenure (10+ years).

---

### Years at Prior Firm 1 (Most Recent Prior Firm)

| Prior Firm 1 Tenure | MQL Rate | Total Leads | Interpretation |
|---------------------|----------|-------------|----------------|
| **< 3 years** | **3.96%** | 12,800 | **Recent job hoppers - highest conversion** |
| 3-7 years | 3.62% | 11,810 | Moderate tenure |
| No Prior Firm 1 | 3.08% | 8,987 | First firm (career starters) |
| **7+ years** | **2.54%** | 8,306 | **Stable at prior firm - lowest conversion** |

**Key Insight:** Short tenure at prior firm (< 3 years) = **1.56x higher** conversion than long tenure (7+ years).

---

### Career Stage (Years Active as Rep)

| Career Stage | MQL Rate | Total Leads | Interpretation |
|--------------|----------|-------------|----------------|
| Early Career (< 3 years) | Need to query | - | Newer advisors |
| Mid Career (3-10 years) | Need to query | - | Established advisors |
| Senior (10-20 years) | Need to query | - | Experienced advisors |
| Veteran (20+ years) | Need to query | - | Very experienced advisors |

**Key Insight:** (Data to be queried - check if newer advisors convert at higher rates)

---

### Current Firm Tenure

| Current Firm Tenure | MQL Rate | Total Leads | Interpretation |
|---------------------|----------|-------------|----------------|
| New to Firm (< 1 year) | Need to query | - | Just joined current firm |
| Early (1-3 years) | Need to query | - | Early tenure |
| Established (3-7 years) | Need to query | - | Established tenure |
| Long Tenure (7+ years) | Need to query | - | Long tenure |

**Key Insight:** (Data to be queried - check if newer to current firm = higher conversion)

---

### Regulatory Disclosures

| Disclosure Status | MQL Rate | Total Leads | Interpretation |
|-------------------|----------|-------------|----------------|
| **Unknown/Missing** | **9.84%** | 945 | **Highest conversion - missing data is signal** |
| Has Disclosures | 3.24% | 40,958 | Lower conversion |
| No Disclosures | Need to query | - | No disclosures |

**Key Insight:** Missing disclosure data = **3x higher** conversion rate. This is a data quality signal (newer advisors or incomplete profiles).

---

## 🎯 Summary: The Perfect MQL Profile

Based on the model, the **ideal MQL candidate** has:

1. ✅ **Low Firm Stability** (< 30% of career at current firm)
   - MQL Rate: **7.07%** (2.8x higher than stable advisors)

2. ✅ **Short Average Tenure at Prior Firms** (< 2 years average)
   - MQL Rate: **4.30%** (2.2x higher than long tenure)

3. ✅ **Short Tenure at Prior Firm 1** (< 3 years)
   - MQL Rate: **3.96%** (1.56x higher than long tenure)

4. ✅ **Missing Gender Data**
   - MQL Rate: **9.27%** (2.2x higher than known gender)

5. ✅ **Missing/Unknown Regulatory Disclosures**
   - MQL Rate: **9.84%** (3x higher than known disclosures)

---

## 🚫 What Makes Someone LESS Likely to Become an MQL

### Negative Signals (Lower Priority):

1. ❌ **Very High Firm Stability** (90%+ of career at current firm)
   - MQL Rate: **2.53%** (lowest)

2. ❌ **Long Average Tenure at Prior Firms** (10+ years average)
   - MQL Rate: **1.99%** (lowest)

3. ❌ **Long Tenure at Prior Firm 1** (7+ years)
   - MQL Rate: **2.54%** (low)

4. ❌ **Has Regulatory Disclosures**
   - MQL Rate: **3.24%** (vs 9.84% for unknown)

---

## 💡 Business Interpretation

### Why Do These Patterns Exist?

1. **Firm Stability = Job Satisfaction**
   - Low stability = actively exploring options
   - High stability = satisfied and unlikely to move

2. **Tenure Patterns = Risk Tolerance**
   - Short tenure = comfortable with change
   - Long tenure = risk-averse, less likely to explore

3. **Missing Data = Newer Advisors**
   - Missing gender/disclosures = newer to industry or incomplete profiles
   - Newer advisors may be more open to opportunities

4. **Regulatory Disclosures = Established Advisors**
   - Has disclosures = more established, may be more cautious
   - Unknown disclosures = newer advisors, more open

---

## 📈 Actionable Recommendations

### High Priority Leads (Target These First):

1. **Advisors with Low Firm Stability** (< 30%)
   - Focus on: Frequent firm movers
   - Expected conversion: **7.07%**

2. **Advisors with Missing Gender Data**
   - Focus on: Newer profiles or incomplete data
   - Expected conversion: **9.27%**

3. **Advisors with Unknown Regulatory Disclosures**
   - Focus on: Newer advisors or incomplete profiles
   - Expected conversion: **9.84%**

4. **Advisors with Short Average Tenure** (< 2 years)
   - Focus on: Job hoppers
   - Expected conversion: **4.30%**

### Lower Priority Leads (Deprioritize):

1. **Very High Stability Advisors** (90%+)
   - Expected conversion: **2.53%** (lowest)

2. **Long Average Tenure** (10+ years)
   - Expected conversion: **1.99%** (lowest)

3. **Long Tenure at Prior Firm 1** (7+ years)
   - Expected conversion: **2.54%** (low)

---

## 🎯 Model Performance Summary

- **Test AUC-PR:** 6.00%
- **Baseline MQL Rate:** 4.74%
- **Model Lift:** 1.27x
- **Top 1% Conversion:** 6.9% (1.4x lift)
- **Top 10% Conversion:** 6.3% (1.3x lift)

**The model successfully identifies:**
- Low stability advisors (7.07% conversion)
- Missing data advisors (9.27% conversion)
- Short tenure advisors (4.30% conversion)

**The model successfully deprioritizes:**
- Very stable advisors (2.53% conversion)
- Long tenure advisors (1.99% conversion)

---

**Report Generated:** November 5, 2025  
**Model:** V12 with Binned Features (20251105_1646)  
**Key Insight:** **Low firm stability and missing data are the strongest positive signals for MQL conversion.**

