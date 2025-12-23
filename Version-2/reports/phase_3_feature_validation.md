# Phase 3: Feature Selection & Validation Report

## Summary

Feature validation performed on `lead_scoring_features_pit` table.

### Key Validations

✅ **Geographic Features Removed**: No raw geographic features (Metro, City, State, Zip) in feature table
✅ **Protected Features Present**: pit_moves_3yr and firm_net_change_12mo are present
✅ **Safe Location Proxies**: Using metro_advisor_density_tier and is_core_market instead of raw geography

### Actual Features in Table (18 features)

1. **Advisor Features**:
   - industry_tenure_months (INT64)
   - num_prior_firms (INT64)
   - current_firm_tenure_months (INT64)
   - pit_moves_3yr (INT64) - **PROTECTED**
   - pit_avg_prior_tenure_months (FLOAT64)
   - pit_restlessness_ratio (FLOAT64)

2. **Firm Features**:
   - firm_aum_pit (INT64)
   - log_firm_aum (FLOAT64)
   - firm_net_change_12mo (INT64) - **PROTECTED**
   - firm_departures_12mo (INT64)
   - firm_arrivals_12mo (INT64)
   - firm_stability_percentile (FLOAT64)
   - firm_stability_tier (STRING)

3. **Data Quality Signals**:
   - is_gender_missing (INT64)
   - is_linkedin_missing (INT64)
   - is_personal_email_missing (INT64)

4. **Flags**:
   - has_firm_aum (INT64)
   - has_valid_virtual_snapshot (INT64)

### Feature Statistics

- **Total Rows**: 39,448
- **Positive Rate**: 3.79%
- **pit_moves_3yr Coverage**: 100% (39,448 rows)
- **firm_net_change_12mo Coverage**: 100% (39,448 rows)
- **pit_restlessness_ratio Coverage**: 30.6% (12,059 rows - only for advisors with prior firms)

**Key Metrics**:
- Average pit_moves_3yr: 0.54 moves in last 3 years
- Average firm_net_change_12mo: -13.83 (firms losing reps on average)
- Average pit_restlessness_ratio: 1.58 (advisors staying longer than historical average)

### Next Steps

- Full multicollinearity analysis (VIF) will be performed during model training
- Feature importance will be determined via XGBoost's built-in feature importance
- XGBoost's regularization will handle multicollinearity automatically
