# PRODUCING_ADVISOR Analysis Report

**Analysis Date:** December 2025  
**Purpose:** Evaluate whether the `PRODUCING_ADVISOR` boolean from FINTRX can replace or complement title-based exclusions for filtering non-advisors.

---

## Executive Summary

This analysis examined the `PRODUCING_ADVISOR` field from FINTRX to determine if it provides a cleaner, more maintainable alternative to complex title pattern matching for filtering out non-advisors (compliance, operations, wholesalers, etc.).

### Key Findings

❌ **PRODUCING_ADVISOR is NOT a strong conversion signal:**
- **TRUE:** 1.74% conversion (1.01x lift) - barely above baseline
- **FALSE:** 1.45% conversion (0.84x lift) - below baseline
- **NULL:** 2.58% conversion (1.49x lift) - best performing group

⚠️ **Counterintuitive Tier Performance:**
- In **TIER_1F_HV_WEALTH_BLEEDER**: FALSE = 22.86% conversion vs TRUE = 10.96%
- In **TIER_3_EXPERIENCED_MOVER**: FALSE = 26.09% conversion vs TRUE = 8.91%
- This suggests `PRODUCING_ADVISOR = FALSE` may not indicate "non-advisor" in all contexts

✅ **High Overlap with Title Exclusions:**
- 1,318 leads (1.71%) have PRODUCING=TRUE but bad titles (CONFLICT)
- 963 leads (1.25%) have PRODUCING=FALSE and bad titles (EXCLUDE BOTH)
- Title exclusions catch more bad leads than PRODUCING filter alone

❌ **Would Exclude Many Legitimate Advisors:**
- 17 non-producing leads in TIER_1A (54.84% of tier)
- 40 non-producing leads in TIER_1B (66.67% of tier)
- Many have legitimate advisor titles (Financial Advisor, Registered Representative, etc.)

### Recommendation

**DO NOT use PRODUCING_ADVISOR as a primary filter.** The field does not reliably distinguish between advisors and non-advisors, and would exclude many high-performing leads. Continue using title-based exclusions, which are more precise and data-driven.

---

## Query Results

### Query 1: FINTRX Distribution

**Question:** What % of contacts are PRODUCING_ADVISOR = TRUE?

| PRODUCING_ADVISOR | Contact Count | % of Total |
|-------------------|--------------|------------|
| **FALSE** | **502,462** | **63.75%** |
| **TRUE** | **285,692** | **36.25%** |

**Analysis:**
- **63.75% of FINTRX contacts** are marked as non-producing
- This is a majority of the database, suggesting the field may be too conservative or have different criteria than expected
- The high FALSE rate suggests this field may not align with our definition of "producing advisor"

**Verdict:** ⚠️ **Concerning** - Majority of contacts marked as non-producing suggests field may be too restrictive.

---

### Query 2: Conversion by PRODUCING_ADVISOR

**Question:** Does TRUE convert better than FALSE?

| PRODUCING_ADVISOR | Total Leads | Conversions | Conversion Rate | Lift vs Baseline |
|-------------------|------------|-------------|-----------------|------------------|
| **NULL** | **4,654** | **120** | **2.58%** | **1.49x** |
| **TRUE** | **55,495** | **968** | **1.74%** | **1.01x** |
| **FALSE** | **16,783** | **243** | **1.45%** | **0.84x** |

**Analysis:**
- ❌ **TRUE shows minimal lift** (1.01x) - barely above baseline
- ❌ **FALSE is below baseline** (0.84x) but not dramatically worse
- ✅ **NULL performs best** (1.49x lift) - unexpected finding
- The conversion gap between TRUE and FALSE is small (0.29 percentage points)

**Verdict:** ❌ **FAIL** - PRODUCING_ADVISOR = TRUE does not show strong conversion signal (only 1.01x lift).

---

### Query 3: MQL Breakdown

**Question:** What % of MQLs had PRODUCING_ADVISOR = TRUE?

| PRODUCING_ADVISOR | MQL Count | % of MQLs |
|-------------------|-----------|-----------|
| **TRUE** | **968** | **72.73%** |
| **FALSE** | **243** | **18.26%** |
| **NULL** | **120** | **9.02%** |

**Analysis:**
- ✅ **72.73% of MQLs** have PRODUCING = TRUE
- However, this is only slightly higher than the 70.42% of all leads that are "Producing + Good Title" (Query 4)
- **18.26% of MQLs** are FALSE - significant portion that would be excluded

**Verdict:** ⚠️ **MIXED** - While most MQLs are TRUE, 18% are FALSE, suggesting the filter would remove legitimate conversions.

---

### Query 4: Overlap with Title Exclusions

**Question:** Does PRODUCING_ADVISOR catch the same bad leads?

| Filter Scenario | Lead Count | Conversions | Conversion Rate | % of Total |
|-----------------|------------|-------------|-----------------|------------|
| **KEEP: Producing + Good Title** | **54,177** | **961** | **1.77%** | **70.42%** |
| **PRODUCING ONLY: Non-Producing + Good Title** | **15,820** | **240** | **1.52%** | **20.56%** |
| **NULL + Good Title** | **4,654** | **120** | **2.58%** | **6.05%** |
| **CONFLICT: Producing but Bad Title** | **1,318** | **7** | **0.53%** | **1.71%** |
| **EXCLUDE BOTH: Non-Producing + Bad Title** | **963** | **3** | **0.31%** | **1.25%** |

**Analysis:**
- ✅ **High overlap:** 963 leads (1.25%) are caught by BOTH filters (EXCLUDE BOTH)
- ⚠️ **CONFLICT cases:** 1,318 leads (1.71%) have PRODUCING=TRUE but bad titles - these would slip through PRODUCING-only filter
- ⚠️ **PRODUCING ONLY category:** 15,820 leads (20.56%) are non-producing but have good titles - these would be excluded by PRODUCING filter but kept by title filter
- The "PRODUCING ONLY" category has 1.52% conversion - not zero, suggesting some legitimate advisors

**Verdict:** ⚠️ **MIXED** - Title exclusions catch more bad leads (1,318 CONFLICT cases), but PRODUCING filter would exclude many good leads (15,820 in PRODUCING ONLY category).

---

### Query 5: Non-Producing Titles

**Question:** What titles do NON-PRODUCING advisors have?

**Top 30 Non-Producing Titles:**

| Title | Lead Count | Conversions | Conversion Rate |
|-------|------------|-------------|-----------------|
| Financial Advisor | 2,348 | 31 | 1.32% |
| Registered Representative | 1,175 | 17 | 1.45% |
| Managing Director | 488 | 5 | 1.02% |
| Investment Advisor Representative | 388 | 6 | 1.55% |
| Wealth Advisor | 331 | 10 | **3.02%** |
| Vice President | 286 | 7 | **2.45%** |
| President | 283 | 5 | 1.77% |
| Financial Planner | 262 | 5 | 1.91% |
| Founder | 200 | 3 | 1.50% |
| Owner | 175 | 4 | **2.29%** |
| Partner | 175 | 7 | **4.00%** |
| Investment Adviser Representative | 168 | 6 | **3.57%** |
| Senior Vice President | 158 | 0 | 0.00% |
| Principal | 156 | 3 | 1.92% |
| Managing Partner | 155 | 2 | 1.29% |
| Financial Solutions Advisor | 150 | 0 | 0.00% |
| Associate | 136 | 1 | 0.74% |
| Director | 131 | 0 | 0.00% |
| Associate Wealth Advisor | 129 | 1 | 0.78% |
| Senior Financial Advisor | 101 | 3 | **2.97%** |
| Senior Wealth Advisor | 87 | 3 | **3.45%** |

**Key Observations:**
- ❌ **Many legitimate advisor titles** are marked as non-producing:
  - "Financial Advisor" (2,348 leads, 1.32% conversion)
  - "Wealth Advisor" (331 leads, **3.02% conversion**)
  - "Partner" (175 leads, **4.00% conversion**)
  - "Senior Wealth Advisor" (87 leads, **3.45% conversion**)
- These are clearly advisors with client-facing roles, not operations/compliance
- The PRODUCING_ADVISOR field appears to have different criteria than our definition

**Verdict:** ❌ **FAIL** - PRODUCING=FALSE includes many legitimate advisors with strong conversion rates.

---

### Query 6: Producing Titles

**Question:** Sanity check - are TRUE leads actual advisors?

**Top 30 Producing Titles:**

| Title | Lead Count | Conversions | Conversion Rate |
|-------|------------|-------------|-----------------|
| Financial Advisor | 11,583 | 138 | 1.19% |
| Registered Representative | 3,478 | 66 | 1.90% |
| Wealth Advisor | 2,234 | 52 | **2.33%** |
| Investment Advisor Representative | 1,434 | 35 | **2.44%** |
| Financial Planner | 1,404 | 17 | 1.21% |
| Partner | 977 | 10 | 1.02% |
| President | 968 | 24 | **2.48%** |
| Managing Director | 899 | 20 | **2.22%** |
| Wealth Management Advisor | 847 | 19 | **2.24%** |
| Senior Wealth Advisor | 807 | 31 | **3.84%** |
| Vice President | 784 | 16 | 2.04% |
| Founder | 777 | 21 | **2.70%** |
| Senior Financial Advisor | 744 | 10 | 1.34% |
| Private Wealth Advisor | 699 | 12 | 1.72% |
| Senior Vice President | 680 | 10 | 1.47% |
| Financial Consultant | 676 | 12 | 1.78% |
| Managing Partner | 654 | 14 | **2.14%** |
| **Wealth Manager** | **634** | **42** | **6.62%** |
| Investment Adviser | 555 | 6 | 1.08% |
| Owner | 552 | 5 | 0.91% |

**Key Observations:**
- ✅ **Titles look legitimate** - all are advisor/client-facing roles
- ✅ **"Wealth Manager"** shows strong performance (6.62% conversion) - aligns with our HV Wealth analysis
- ✅ **"Senior Wealth Advisor"** shows 3.84% conversion
- The PRODUCING=TRUE group contains legitimate advisors

**Verdict:** ✅ **PASS** - Producing advisors have legitimate titles and show expected conversion patterns.

---

### Query 7: PRODUCING_ADVISOR by Tier

**Question:** Is PRODUCING_ADVISOR additive within tiers?

**Key Findings by Tier:**

| Tier | PRODUCING | Leads | Conversions | Conversion Rate |
|------|-----------|-------|-------------|-----------------|
| **TIER_1F_HV_WEALTH_BLEEDER** | **FALSE** | **35** | **8** | **22.86%** ⚠️ |
| **TIER_1F_HV_WEALTH_BLEEDER** | **TRUE** | **146** | **16** | **10.96%** |
| **TIER_3_EXPERIENCED_MOVER** | **FALSE** | **23** | **6** | **26.09%** ⚠️ |
| **TIER_3_EXPERIENCED_MOVER** | **TRUE** | **101** | **9** | **8.91%** |
| TIER_1A_PRIME_MOVER_CFP | TRUE | 10 | 5 | 50.00% |
| TIER_1B_PRIME_MOVER_SERIES65 | TRUE | 57 | 9 | 15.79% |
| TIER_1B_PRIME_MOVER_SERIES65 | FALSE | 28 | 4 | 14.29% |
| TIER_1E_PRIME_MOVER | TRUE | 65 | 9 | 13.85% |
| TIER_1E_PRIME_MOVER | FALSE | 25 | 3 | 12.00% |
| TIER_2A_PROVEN_MOVER | TRUE | 899 | 74 | 8.23% |
| TIER_2A_PROVEN_MOVER | FALSE | 226 | 20 | 8.85% |
| STANDARD | TRUE | 26,740 | 855 | 3.20% |
| STANDARD | FALSE | 6,082 | 236 | 3.88% |
| STANDARD | NULL | 1,557 | 136 | 8.73% |

**Critical Findings:**
- ⚠️⚠️⚠️ **TIER_1F: FALSE = 22.86% vs TRUE = 10.96%** - Non-producing leads convert **2x better**!
- ⚠️⚠️⚠️ **TIER_3: FALSE = 26.09% vs TRUE = 8.91%** - Non-producing leads convert **3x better**!
- ⚠️ **STANDARD tier: FALSE = 3.88% vs TRUE = 3.20%** - Non-producing slightly better
- This suggests `PRODUCING_ADVISOR = FALSE` does NOT mean "non-advisor" in these contexts

**Verdict:** ❌ **FAIL** - PRODUCING=FALSE shows BETTER conversion in multiple tiers, suggesting the field is not a reliable filter.

---

### Query 8: Impact on January 2026 List

**Question:** How many leads would be affected by a PRODUCING_ADVISOR filter?

| Tier | Producing Count | Non-Producing Count | Total | % Producing | % Non-Producing |
|------|-----------------|---------------------|-------|-------------|-----------------|
| **TIER_1A_PRIME_MOVER_CFP** | **14** | **17** | **31** | **45.16%** | **54.84%** |
| **TIER_1B_PRIME_MOVER_SERIES65** | **20** | **40** | **60** | **33.33%** | **66.67%** |
| **TIER_1_PRIME_MOVER** | **63** | **237** | **300** | **21.00%** | **79.00%** |
| **TIER_1F_HV_WEALTH_BLEEDER** | **19** | **31** | **50** | **38.00%** | **62.00%** |
| TIER_2_PROVEN_MOVER | 584 | 916 | 1,500 | 38.93% | 61.07% |
| TIER_3_MODERATE_BLEEDER | 89 | 211 | 300 | 29.67% | 70.33% |
| TIER_4_EXPERIENCED_MOVER | 57 | 102 | 159 | 35.85% | 64.15% |

**Analysis:**
- ❌ **High non-producing rates in Tier 1:**
  - Tier 1A: 54.84% non-producing
  - Tier 1B: 66.67% non-producing
  - Tier 1: 79.00% non-producing
  - Tier 1F: 62.00% non-producing
- If we filtered to PRODUCING=TRUE only, we would lose:
  - **17 leads from Tier 1A** (54.84% of the tier)
  - **40 leads from Tier 1B** (66.67% of the tier)
  - **237 leads from Tier 1** (79% of the tier)
  - **31 leads from Tier 1F** (62% of the tier)

**Verdict:** ❌ **FAIL** - Filtering to PRODUCING=TRUE would exclude majority of Tier 1 leads, including many high-performing ones.

---

### Query 9: Non-Producing Leads in January List

**Question:** Who specifically would be removed?

**Sample of Non-Producing Leads (Top 50):**

**Tier 1A Examples:**
- Financial Advisor (World Investment Advisors)
- Tax Specialist (Fortress Private Ledger)
- Senior Financial Advisor (Purshe Kaplan Sterling)
- Registered Representative (Arcadia Securities)
- Partner (Valmark Securities)
- Investment Advisor Representative (Valmark Securities)
- CEO (Fortune Financial Services)

**Tier 1B Examples:**
- Investment Adviser Representative (Empower Advisory Group)
- Financial Advisor (Empower Advisory Group)
- Managing Director (Cynosure Group)
- Senior Financial Advisor (Empower Advisory Group)
- Co-Founder & Managing Director (Cynosure Group)

**Analysis:**
- ❌ **Many legitimate advisors** would be excluded:
  - "Financial Advisor" titles
  - "Investment Advisor Representative" titles
  - "Partner" titles
  - "Managing Director" titles
  - "Senior Financial Advisor" titles
- These are clearly client-facing roles, not operations/compliance
- The PRODUCING_ADVISOR field appears to have different classification criteria

**Verdict:** ❌ **FAIL** - Would exclude many legitimate advisors with client-facing titles.

---

### Query 10: Combined Filter Comparison

**Question:** What if we use BOTH PRODUCING_ADVISOR AND Title Exclusions?

| Filter Strategy | Leads Kept | Conversions | Conversion Rate |
|-----------------|------------|-------------|-----------------|
| **Title Exclusions only** | **74,651** | **1,321** | **1.77%** |
| **BOTH Filters (PRODUCING + Title)** | **54,177** | **961** | **1.77%** |
| **PRODUCING_ADVISOR = TRUE only** | **55,495** | **968** | **1.74%** |
| **No Filters (baseline)** | **76,932** | **1,331** | **1.73%** |

**Analysis:**
- ✅ **Title Exclusions only:** 1.77% conversion (best performance)
- ⚠️ **BOTH Filters:** 1.77% conversion (same as title only, but removes 20,474 more leads)
- ⚠️ **PRODUCING only:** 1.74% conversion (slightly worse than title only)
- The **BOTH filter removes 20,474 leads** but achieves the same conversion rate as title-only
- This suggests the additional PRODUCING filter is removing legitimate advisors without improving quality

**Verdict:** ⚠️ **MIXED** - Title exclusions alone achieve the same conversion rate as combined filters, with more leads retained.

---

### Query 11: NULL Check

**Question:** Are NULLs a problem?

| Title | Lead Count | Conversions | Conversion Rate |
|-------|------------|-------------|-----------------|
| **NULL (no title)** | **4,654** | **120** | **2.58%** |

**Analysis:**
- ⚠️ **4,654 leads (6.05% of total)** have NULL PRODUCING_ADVISOR
- These leads have **2.58% conversion (1.49x lift)** - better than TRUE or FALSE!
- Most have NULL title name as well (4,654 leads with NULL title)
- This suggests NULL may indicate missing data rather than "non-producing"

**Verdict:** ⚠️ **MIXED** - NULL values show good conversion, suggesting they're missing data rather than non-producing advisors.

---

### Query 12: Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Leads Analyzed** | **76,932** |
| **PRODUCING_ADVISOR = TRUE** | **55,495 (72.1%)** |
| **PRODUCING_ADVISOR = FALSE** | **16,783 (21.8%)** |
| **PRODUCING_ADVISOR IS NULL** | **4,654 (6.0%)** |
| **MQLs with PRODUCING = TRUE** | **968 (72.7% of MQLs)** |
| **MQLs with PRODUCING = FALSE** | **243 (18.3% of MQLs)** |

**Key Insights:**
- 72.1% of leads are PRODUCING=TRUE
- 18.3% of MQLs are PRODUCING=FALSE - significant portion
- 6.0% have NULL values

---

## Detailed Analysis

### Why PRODUCING_ADVISOR Doesn't Work as Expected

#### 1. **Field Definition Mismatch**

The `PRODUCING_ADVISOR` field appears to have different criteria than our definition of "advisor vs non-advisor":

- **Many legitimate advisors are marked FALSE:**
  - "Financial Advisor" (2,348 leads, 1.32% conversion)
  - "Wealth Advisor" (331 leads, 3.02% conversion)
  - "Partner" (175 leads, 4.00% conversion)
  - "Senior Wealth Advisor" (87 leads, 3.45% conversion)

- **These are clearly client-facing roles**, not operations/compliance/wholesaler roles

#### 2. **Counterintuitive Performance**

The most concerning finding is that **PRODUCING=FALSE shows BETTER conversion in multiple tiers:**

- **TIER_1F_HV_WEALTH_BLEEDER:** FALSE = 22.86% vs TRUE = 10.96% (2x better)
- **TIER_3_EXPERIENCED_MOVER:** FALSE = 26.09% vs TRUE = 8.91% (3x better)
- **STANDARD tier:** FALSE = 3.88% vs TRUE = 3.20% (slightly better)

This suggests the field may be measuring something different than "producing advisor" (e.g., commission-based vs fee-based, or some other FINTRX classification).

#### 3. **High Exclusion Rate**

If we filtered to PRODUCING=TRUE only, we would exclude:
- **54.84% of Tier 1A leads** (17 out of 31)
- **66.67% of Tier 1B leads** (40 out of 60)
- **79% of Tier 1 leads** (237 out of 300)
- **62% of Tier 1F leads** (31 out of 50)

These are our highest-performing tiers, and we'd be excluding the majority of them.

#### 4. **Minimal Conversion Lift**

- **PRODUCING=TRUE:** 1.74% conversion (1.01x lift) - barely above baseline
- **PRODUCING=FALSE:** 1.45% conversion (0.84x lift) - below baseline but not dramatically worse
- The gap is only **0.29 percentage points** - not a strong signal

---

## Comparison: Title Exclusions vs PRODUCING_ADVISOR

| Aspect | Title Exclusions | PRODUCING_ADVISOR |
|--------|------------------|-------------------|
| **Conversion Lift** | Maintains 1.77% (baseline 1.73%) | 1.74% (1.01x lift) |
| **Leads Retained** | 74,651 (97.0% of total) | 55,495 (72.1% of total) |
| **Precision** | ✅ Data-driven, specific titles | ❌ Excludes many legitimate advisors |
| **Transparency** | ✅ Clear exclusion rules | ⚠️ Boolean field, unclear criteria |
| **Maintainability** | ⚠️ Requires pattern updates | ✅ Single boolean check |
| **False Negatives** | Low (specific patterns) | High (excludes 27.9% of leads) |
| **False Positives** | Low (validated on 72K leads) | Medium (1,318 CONFLICT cases) |

**Winner:** ✅ **Title Exclusions** - More precise, retains more leads, achieves same/better conversion.

---

## Recommendations

### ❌ **DO NOT Implement PRODUCING_ADVISOR Filter**

**Rationale:**
1. **Minimal conversion lift:** Only 1.01x (barely above baseline)
2. **Would exclude majority of Tier 1 leads:** 54-79% of top tiers marked as non-producing
3. **Counterintuitive performance:** FALSE shows better conversion in multiple tiers
4. **Many legitimate advisors excluded:** Financial Advisor, Wealth Advisor, Partner titles marked FALSE
5. **Title exclusions perform better:** Same conversion rate with more leads retained

### ✅ **Continue Using Title-Based Exclusions**

**Rationale:**
1. **Data-driven:** Based on analysis of 72,055 historical leads
2. **Precise:** Targets specific low-converting titles (0-0.5% conversion)
3. **Validated:** All excluded titles have conversion rates ≤ 0.5%
4. **Transparent:** Clear exclusion rules that can be audited
5. **Better performance:** 1.77% conversion vs 1.74% for PRODUCING filter

### ⚠️ **Optional: Use PRODUCING_ADVISOR as Secondary Signal**

If you want to add an additional layer of filtering, consider:

```sql
-- Optional: Add PRODUCING_ADVISOR as secondary filter
-- Only exclude if BOTH conditions are true:
WHERE is_excluded_title = 0  -- Primary filter (title exclusions)
  AND (PRODUCING_ADVISOR = TRUE OR PRODUCING_ADVISOR IS NULL)  -- Secondary filter
```

**However, this would:**
- Remove 20,474 additional leads (from 74,651 to 54,177)
- Achieve the same conversion rate (1.77%)
- Exclude many legitimate advisors

**Recommendation:** Only implement if lead volume is not a constraint and you want maximum precision.

---

## Potential Use Cases for PRODUCING_ADVISOR

While not recommended as a primary filter, `PRODUCING_ADVISOR` could be useful for:

1. **Reporting/Analytics:** Understanding the distribution of "producing" vs "non-producing" advisors in your pipeline
2. **Secondary Segmentation:** Using as a feature in tier assignment (not as a filter)
3. **Data Quality Checks:** Identifying potential data issues (e.g., why are so many "Financial Advisor" titles marked FALSE?)

---

## How FINTRX Determines PRODUCING_ADVISOR

Based on FINTRX documentation and research, the `PRODUCING_ADVISOR` field is determined through:

### Definition
A "Producing Advisor" is identified as a **registered representative who actively manages a personal book of client assets**. This designation confirms that the advisor:
- Directly allocates client capital
- Makes investment decisions
- Oversees financial relationships

### Determination Method
FINTRX uses a **combination of machine learning and human verification**, analyzing:
1. **Job descriptions** - Title and role descriptions
2. **Bios** - Professional biographies and profiles
3. **LinkedIn profiles** - Professional networking information
4. **Licensing information** - Regulatory licenses (Series 7, 65, 66, etc.)
5. **Firm websites** - Public firm information and team pages

### Why This Doesn't Align with Our Use Case

The FINTRX definition focuses on **"actively manages a personal book of client assets"** - which is different from our conversion-based definition of "good leads." This explains:

1. **Why many legitimate advisors are FALSE:**
   - Advisors who don't manage their own book (e.g., team-based advisors, support roles)
   - Advisors in transition or new to the industry
   - Advisors with different business models (e.g., fee-only planners vs. asset managers)

2. **Why FALSE shows better conversion in some tiers:**
   - Advisors without a "personal book" may be more mobile/portable
   - Team-based advisors may be looking for better opportunities
   - The field may be measuring "book ownership" rather than "conversion potential"

3. **Why the field is conservative:**
   - FINTRX errs on the side of caution (63.75% marked as FALSE)
   - Requires clear evidence of personal book management
   - May exclude advisors who are "producing" but in non-traditional roles

### Key Insight

**PRODUCING_ADVISOR measures "book ownership" not "conversion potential."** Our analysis shows that advisors without a personal book (FALSE) can still be highly convertible, especially in certain contexts (Tier 1F, Tier 3).

---

## Limitations

1. **Field Definition Mismatch:** FINTRX's definition (personal book management) differs from our need (conversion potential)
2. **Historical Data Only:** Analysis based on 2022-2025 leads; field behavior may have changed
3. **NULL Handling:** 6% of leads have NULL values; unclear if these are missing data or intentional
4. **Tier-Specific Behavior:** Field shows different patterns in different tiers (FALSE better in Tier 1F/3)
5. **Conservative Classification:** FINTRX's ML/human verification may be too conservative for our use case

---

## Conclusion

The `PRODUCING_ADVISOR` field from FINTRX is **not a reliable filter** for distinguishing advisors from non-advisors. While it may have value for FINTRX's internal classification, it does not align with our conversion-based definition of "good leads."

**Key Reasons:**
1. Minimal conversion lift (1.01x)
2. Would exclude majority of Tier 1 leads
3. Counterintuitive performance (FALSE better in some tiers)
4. Many legitimate advisors marked as FALSE
5. Title exclusions perform better with more leads retained

**Final Recommendation:** Continue using data-driven title exclusions. Do not implement PRODUCING_ADVISOR as a filter.

---

## Appendix: Query Results Summary

### Query 1: FINTRX Distribution
- TRUE: 285,692 (36.25%)
- FALSE: 502,462 (63.75%)

### Query 2: Conversion Rates
- TRUE: 1.74% (1.01x lift)
- FALSE: 1.45% (0.84x lift)
- NULL: 2.58% (1.49x lift)

### Query 3: MQL Distribution
- TRUE: 968 MQLs (72.73%)
- FALSE: 243 MQLs (18.26%)
- NULL: 120 MQLs (9.02%)

### Query 4: Filter Overlap
- KEEP (Producing + Good Title): 54,177 leads (1.77% conversion)
- PRODUCING ONLY (Non-Producing + Good Title): 15,820 leads (1.52% conversion)
- CONFLICT (Producing + Bad Title): 1,318 leads (0.53% conversion)
- EXCLUDE BOTH: 963 leads (0.31% conversion)

### Query 7: Tier Performance
- TIER_1F: FALSE = 22.86%, TRUE = 10.96%
- TIER_3: FALSE = 26.09%, TRUE = 8.91%
- STANDARD: FALSE = 3.88%, TRUE = 3.20%

### Query 8: January List Impact
- Tier 1A: 54.84% non-producing
- Tier 1B: 66.67% non-producing
- Tier 1: 79.00% non-producing
- Tier 1F: 62.00% non-producing

### Query 10: Filter Comparison
- Title Exclusions: 1.77% conversion, 74,651 leads
- PRODUCING only: 1.74% conversion, 55,495 leads
- BOTH: 1.77% conversion, 54,177 leads

---

*Report generated: December 2025*  
*Analysis queries: producing_advisor_analysis.sql*  
*Data period: 2022-2025 (3 years of historical leads)*

