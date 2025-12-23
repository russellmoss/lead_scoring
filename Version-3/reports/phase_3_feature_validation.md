# Phase 3: Feature Selection & Validation Report

**Date:** 2025-12-21 19:09  
**Status:** ⚠️ PASSED WITH WARNINGS  
**Total Features Analyzed:** 37

---

## Summary

Feature validation performed on `lead_scoring_features_pit` table.

### Key Validations

✅ **Geographic Features Removed**: No raw geographic features found
✅ **Protected Features Present**: All protected features present
❌ **Safe Location Proxies**: Missing
✅ **Null Signal Features**: 5 features found

### Feature Categories

#### 1. Advisor Features
- industry_tenure_months
- num_prior_firms
- current_firm_tenure_months
- pit_moves_3yr (PROTECTED)
- pit_avg_prior_tenure_months
- pit_restlessness_ratio
- pit_mobility_tier

#### 2. Firm Features
- firm_aum_pit
- log_firm_aum
- firm_rep_count_at_contact
- firm_net_change_12mo (PROTECTED)
- firm_departures_12mo
- firm_arrivals_12mo
- firm_stability_score
- firm_stability_percentile
- firm_stability_tier
- firm_recruiting_priority
- firm_aum_tier

#### 3. Data Quality Signals
- is_gender_missing
- is_linkedin_missing
- is_personal_email_missing
- is_license_data_missing
- is_industry_tenure_missing

#### 4. Quality Features
- accolade_count
- has_accolades
- forbes_accolades
- disclosure_count
- has_disclosures

### Feature Statistics

- **Total Rows**: 39,448
- **Positive Rate**: 3.79%
- **pit_moves_3yr Coverage**: 39,448 (100.0%)
- **firm_net_change_12mo Coverage**: 39,448 (100.0%)
- **pit_restlessness_ratio Coverage**: 39,448 (100.0%)

**Key Metrics**:
- Average pit_moves_3yr: 0.54 moves in last 3 years
- Average firm_net_change_12mo: -13.83 (negative = firms losing reps)
- Average pit_restlessness_ratio: 1.18 (ratio > 1.0 = staying longer than usual)

### Next Steps

- Full multicollinearity analysis (VIF) will be performed during model training
- Feature importance will be determined via XGBoost's built-in feature importance
- XGBoost's regularization will handle multicollinearity automatically
- For V3 tiered approach, feature selection is less critical (using business rules)
