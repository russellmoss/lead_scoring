# Phase 4: Multicollinearity Analysis Report

**Generated**: 2025-12-24 14:37:51

---

## Summary

- **Total Features Analyzed**: 27
- **Final Feature Count**: 15
- **Features Removed**: 12
- **High Correlation Pairs**: 10
- **High VIF Features**: 6
- **Max VIF (Final Set)**: 1.67

## High Correlation Pairs (|r| > 0.7)

| Feature 1 | Feature 2 | Correlation |
|-----------|-----------|------------|
| has_firm_data | has_employment_history | 1.000 |
| is_tenure_missing | has_firm_data | -1.000 |
| is_tenure_missing | has_employment_history | -1.000 |
| firm_departures_12mo | firm_net_change_12mo | -0.972 |
| industry_tenure_months | experience_years | 0.963 |
| mobility_3yr | tenure_bucket_x_mobility | 0.937 |
| firm_rep_count_12mo_ago | firm_arrivals_12mo | 0.837 |
| firm_rep_count_at_contact | firm_arrivals_12mo | 0.820 |
| firm_rep_count_at_contact | firm_rep_count_12mo_ago | 0.773 |
| firm_rep_count_12mo_ago | firm_departures_12mo | 0.760 |

## High VIF Features (VIF > 5.0)

| Feature | VIF |
|---------|-----|
| industry_tenure_months | 999.00 |
| experience_years | 999.00 |
| firm_departures_12mo | 17.47 |
| firm_net_change_12mo | 17.47 |
| mobility_3yr | 8.09 |
| tenure_bucket_x_mobility | 8.09 |

## Removed Features

| Feature | Reason |
|---------|--------|
| experience_years | High VIF (999.00) and correlated with other features (max r=0.963) |
| firm_arrivals_12mo | Correlated with firm_rep_count_at_contact (r=0.820). Keeping firm_rep_count_at_contact due to high IV (0.7991). |
| firm_departures_12mo | Correlated with firm_net_change_12mo (r=-0.972). Keeping firm_net_change_12mo as it captures the delta signal (derived feature). |
| firm_rep_count_12mo_ago | Highly correlated with firm_rep_count_at_contact (r=0.837). Keeping _at_contact as it's more directly relevant to contact timing and has higher IV. |
| has_employment_history | Correlated with has_firm_data (r=1.000), keeping shorter/more intuitive name |
| has_fintrx_match | Zero variance (all values identical) |
| industry_tenure_months | Correlated with experience_years (r=0.963), keeping shorter/more intuitive name |
| is_linkedin_sourced | Zero variance (all values identical) |
| is_provided_list | Zero variance (all values identical) |
| is_tenure_missing | Correlated with has_firm_data (r=-1.000), keeping shorter/more intuitive name |
| mobility_3yr | High VIF (8.09) and correlated with other features (max r=0.937) |
| tenure_bucket_x_mobility | Correlated with mobility_3yr (r=0.937), keeping shorter/more intuitive name |

## Final Feature Set

**Count**: 15

| Feature | VIF |
|---------|-----|
| experience_bucket | 0.00 |
| firm_net_change_12mo | 1.10 |
| firm_rep_count_at_contact | 1.06 |
| firm_stability_tier | 0.00 |
| has_email | 1.00 |
| has_firm_data | 0.00 |
| has_linkedin | 1.00 |
| is_broker_protocol | 1.08 |
| is_experience_missing | 0.00 |
| is_wirehouse | 1.10 |
| mobility_tier | 0.00 |
| mobility_x_heavy_bleeding | 1.67 |
| short_tenure_x_high_mobility | 1.67 |
| tenure_bucket | 0.00 |
| tenure_months | 1.04 |

## Recommendations

✅ **Multicollinearity addressed**
- Removed 12 redundant features
- Final set has 15 features
- Max VIF: 1.67 (acceptable)

**Proceed to Phase 5: Train/Test Split**

