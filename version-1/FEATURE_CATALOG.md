# Lead Scoring Feature Catalog

## Overview

This catalog documents all features engineered for the lead scoring model using Point-in-Time (PIT) methodology with Gap-Tolerant logic.

**Key Updates:**
- **Gap-Tolerant Logic:** Recovers ~63% of leads by using "Last Known Value" for employment records
- **Date Floor:** Training data filtered to `contacted_date >= '2024-02-01'` to ensure valid firm historicals
- **Limited History:** AUM growth uses Jan 2024 baseline instead of 12-month lookback

## Feature Categories


### Identifier


### Gap Tolerant

#### `days_in_gap`

- **Type:** INT64
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** positive
- **Leakage Risk:** LOW
- **Business Logic:** Days between job end date and contacted_date. 0 = no gap (active employment). Positive = advisor in employment gap. Higher values may indicate transition period = opportunity.
- **Null Handling:** Default to 0
- **Notes:** NEW: Gap-tolerant logic recovers ~63% of leads. This feature captures employment transition periods.


### Advisor Experience

#### `industry_tenure_months`

- **Type:** INT64
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** nonlinear
- **Leakage Risk:** LOW
- **Business Logic:** Total months in industry calculated from employment history end dates. Very long tenure may indicate less mobility.
- **Null Handling:** Impute with median, create indicator for missing


### Advisor Mobility

#### `num_prior_firms`

- **Type:** INT64
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** positive
- **Leakage Risk:** LOW
- **Business Logic:** Count of firms worked at before current. Higher mobility may indicate openness to change.
- **Null Handling:** Default to 0

#### `pit_moves_3yr`

- **Type:** INT64
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** positive
- **Leakage Risk:** LOW
- **Business Logic:** Count of firm changes in 36 months prior to contact. VALIDATED: Advisors with 3+ moves have 11% conversion vs 3% baseline (3.8x lift). Top predictor alongside Firm Net Change.
- **Null Handling:** Default to 0
- **Notes:** HIGH PRIORITY SIGNAL - Validated in Rep Mobility analysis

#### `pit_mobility_tier`

- **Type:** STRING
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** nonlinear
- **Leakage Risk:** LOW
- **Business Logic:** Categorical mobility classification: 'Highly Mobile' (3+ moves in 3yr, 11% conversion), 'Mobile' (2 moves), 'Average' (1 move), 'Stable' (0 moves). VALIDATED: Highly Mobile tier has 3.8x lift over baseline.
- **Null Handling:** Assign 'Unknown' category
- **Notes:** HIGH PRIORITY SIGNAL - Categorical version of pit_moves_3yr. One-hot encode for model.


### Advisor Stability

#### `current_firm_tenure_months`

- **Type:** INT64
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** negative
- **Leakage Risk:** LOW
- **Business Logic:** Months at current firm as of contact. Very long tenure may indicate low mobility. For gap cases, represents tenure at last known firm.
- **Null Handling:** Impute with 0, flag as missing


### Firm Size

#### `firm_aum_pit`

- **Type:** INT64
- **Source:** Firm_historicals
- **PIT Status:** FULL_PIT
- **Expected Direction:** nonlinear
- **Leakage Risk:** LOW
- **Business Logic:** Firm AUM as of pit_month (month before contacted_date). Large firms may be harder to recruit from, but also have more resources.
- **Null Handling:** Impute with median, create indicator

#### `firm_rep_count_at_contact`

- **Type:** INT64
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** nonlinear
- **Leakage Risk:** LOW
- **Business Logic:** Number of advisors at firm as of contacted_date, calculated from employment history. Larger firms may have more turnover opportunities.
- **Null Handling:** Impute with median


### Firm Growth

#### `aum_growth_since_jan2024_pct`

- **Type:** FLOAT64
- **Source:** Firm_historicals
- **PIT Status:** FULL_PIT
- **Expected Direction:** negative
- **Leakage Risk:** LOW
- **Business Logic:** AUM growth from Jan 2024 baseline to pit_month. Declining AUM may indicate distress = opportunity. **Note:** Due to limited history (Jan 2024+), this replaces the 12-month growth metric.
- **Null Handling:** Impute with 0 (no growth)
- **Notes:** Replaces aum_growth_12mo_pct due to limited historical data


### Firm Stability

#### `firm_net_change_12mo`

- **Type:** INT64
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** negative
- **Leakage Risk:** LOW
- **Business Logic:** Net change in advisors at firm (arrivals - departures) in 12 months before contact. Negative = bleeding talent = opportunity. VALIDATED: Most predictive feature alongside pit_moves_3yr.
- **Null Handling:** Impute with 0
- **Notes:** HIGH PRIORITY SIGNAL - Empirically validated as top predictor

#### `firm_stability_score`

- **Type:** FLOAT64
- **Source:** contact_registered_employment_history
- **PIT Status:** FULL_PIT
- **Expected Direction:** negative
- **Leakage Risk:** LOW
- **Business Logic:** Derived stability score: 50 + (net_change_12mo * 3.5), clamped to 0-100. Lower scores indicate more instability = higher opportunity. Empirically validated formula.
- **Null Handling:** Impute with 50 (neutral)
- **Notes:** Derived from firm_net_change_12mo using validated formula


### Target


## High Priority Signals

The following features have been empirically validated as top predictors:

1. **pit_moves_3yr** - 3.8x lift for advisors with 3+ moves in 3 years
2. **firm_net_change_12mo** - Most predictive feature alongside mobility
3. **pit_mobility_tier** - Categorical version with validated thresholds

## Gap-Tolerant Features

The following features leverage the new "Last Known Value" logic:

- **days_in_gap** - Captures employment transition periods
- **firm_crd_at_contact** - Uses most recent employment record
- **current_firm_tenure_months** - For gap cases, represents tenure at last known firm

## Null Signal Features

Note: The simplified remediation table does not include all null signal features from the full pipeline. These would be added in the complete implementation:
- is_gender_missing
- is_linkedin_missing
- is_personal_email_missing
- is_license_data_missing
- is_industry_tenure_missing

