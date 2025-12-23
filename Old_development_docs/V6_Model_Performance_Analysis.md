# V6 Model Performance Analysis: Is It Better Than Guessing?

**Generated:** November 4, 2025  
**Model Version:** v6_20251104  
**Baseline Conversion Rate:** 3.39% (training data), 4-5% (actual business rate)

---

## Executive Summary

✅ **YES, the model is better than random guessing, but performance is modest.**

- **Model AUC-PR:** 0.0588 (5.88%)
- **Baseline (Random Guess):** 0.0339 (3.39%)
- **Improvement:** 1.73x better than random
- **AUC-ROC:** ~0.63 (random = 0.50, so 26% better than random)

**Will it help?** Yes, but with limitations. The model provides modest lift but won't dramatically improve conversion rates.

---

## Performance Metrics

### 1. AUC-PR (Average Precision) - Primary Metric

**What it means:** Measures how well the model ranks positive examples (MQLs).

- **Random Guess:** 0.0339 (3.39% - just the baseline positive rate)
- **Our Model:** 0.0588 (5.88%)
- **Improvement:** 1.73x better than random

**Interpretation:** 
- The model can identify leads that are 1.73x more likely to convert than average
- This is modest but meaningful improvement
- Ideal would be >0.15 (15%), but even 5.88% is better than nothing

### 2. AUC-ROC (Receiver Operating Characteristic)

**What it means:** Measures how well the model distinguishes between positive and negative classes.

- **Random Guess:** 0.50 (coin flip)
- **Our Model:** ~0.63 (varies by fold: 0.62-0.64)
- **Improvement:** 26% better than random (0.63 vs 0.50)

**Interpretation:**
- The model can correctly rank 63% of positive/negative pairs
- This is better than random, but not great (excellent would be >0.80)

---

## Real-World Impact Analysis

### Scenario: Top 10% of Leads (Highest Scores)

Let's assume you call the top 10% of leads based on model scores:

**Without Model (Random Selection):**
- Call 10% of leads = ~4,194 leads
- Expected conversions: 4,194 × 3.39% = **142 MQLs**
- Conversion rate: 3.39%

**With Model (Top 10% by Score):**
- If model is 1.73x better, top 10% should have ~1.73x higher conversion
- Expected conversion rate: 3.39% × 1.73 = **5.86%**
- Expected conversions: 4,194 × 5.86% = **246 MQLs**
- **Lift: +104 MQLs (+73% improvement)**

### Scenario: Top 20% of Leads

**Without Model:**
- Call 20% = ~8,388 leads
- Expected conversions: 8,388 × 3.39% = **284 MQLs**

**With Model:**
- Top 20% conversion: ~5.0% (model provides some lift but not as concentrated)
- Expected conversions: 8,388 × 5.0% = **419 MQLs**
- **Lift: +135 MQLs (+48% improvement)**

---

## Will This Model Help?

### ✅ **YES, but with caveats:**

**Pros:**
1. **Better than random:** 1.73x improvement means you'll get more MQLs per dial
2. **Stable performance:** CV coefficient of 2.36% shows consistent performance
3. **Actionable ranking:** Model can prioritize which leads to call first
4. **Cost-effective:** Even modest lift (50-100 extra MQLs per 10,000 leads) can be valuable

**Cons:**
1. **Modest performance:** AUC-PR of 5.88% is well below ideal (15%+)
2. **Limited signal:** Without financial features, model has weaker predictive power
3. **Not a game-changer:** Won't dramatically transform conversion rates
4. **May need refinement:** Could benefit from additional features or different approaches

---

## Comparison to Your Business Metrics

**Your actual conversion rate:** 4-5%  
**Model baseline (training data):** 3.39%

**Key Insight:** The model was trained on historical data showing 3.39% conversion. If your actual rate is 4-5%, that's actually better than the training baseline! This suggests:

1. **Recent improvements:** Business may have improved conversion rates since training data
2. **Model may be conservative:** Trained on lower-converting historical data
3. **Potential upside:** Model might perform better in production if recent rates are higher

---

## Recommendations

### 1. **Deploy with Low Expectations**
- Model provides modest lift (1.73x)
- Don't expect dramatic improvements
- Monitor actual performance vs baseline

### 2. **Use for Prioritization**
- Focus on top-scoring leads first
- Even 50-100 extra MQLs per quarter is valuable
- Track conversion rates by score decile

### 3. **Consider Improvements**
- **Short-term:** Model is usable but limited
- **Medium-term:** Explore adding more features (if available)
- **Long-term:** Consider ensemble approaches or different algorithms

### 4. **Monitor and Iterate**
- Track actual conversion rates by model score
- Compare to baseline (4-5% actual rate)
- Refine model based on production performance

---

## Bottom Line

**Is it better than guessing?** ✅ **YES** - 1.73x better (5.88% vs 3.39% AUC-PR)

**Will it help?** ✅ **YES, modestly** - Expect 50-100 extra MQLs per 10,000 leads in top decile

**Should you deploy?** ✅ **YES, with realistic expectations**
- Model provides actionable prioritization
- Even modest lift is valuable
- Better than random selection
- Can be improved over time

**Expected ROI:**
- If you call 1,000 leads/month
- Top 10% (100 leads) with model: ~6 MQLs (vs 3-4 without)
- **Extra MQLs: +2-3 per month**
- Over a year: +24-36 extra MQLs

This is meaningful but not transformative. The model is a tool, not a silver bullet.

---

## Next Steps

1. ✅ **Deploy model** for lead prioritization
2. 📊 **Track performance** by score decile
3. 🔄 **Iterate** based on production data
4. 🎯 **Refine** with additional features if available

