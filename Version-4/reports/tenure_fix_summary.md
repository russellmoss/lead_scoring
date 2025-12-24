# Tenure Calculation Bug Fix - Summary

**Date**: 2025-12-24  
**Status**: ✅ FIXED AND VERIFIED

---

## Problem

- **97.2% of test leads** had `tenure_bucket = "Unknown"` (5,836 of 6,004)
- **90.28% of training leads** had `tenure_bucket = "Unknown"` (22,330 of 24,734)
- Root cause: Feature engineering SQL only queried `contact_registered_employment_history` (past employment), missing current employment data in `ria_contacts_current`

---

## Solution

Modified `sql/phase_2_feature_engineering.sql` to add fallback logic:

1. **First try**: `contact_registered_employment_history` (existing PIT-compliant logic)
2. **Fallback**: `ria_contacts_current` using `LATEST_REGISTERED_EMPLOYMENT_START_DATE`
3. **PIT Compliance**: Only use records where `LATEST_REGISTERED_EMPLOYMENT_START_DATE <= contacted_date`

---

## Results

### Before Fix
| Period | Has Tenure | Unknown | Coverage |
|--------|-----------|---------|----------|
| Test | 168 (2.8%) | 5,836 (97.2%) | 2.8% |
| Training | 2,404 (9.72%) | 22,330 (90.28%) | 9.72% |
| **Overall** | **2,572 (8.4%)** | **28,166 (91.6%)** | **8.4%** |

### After Fix
| Period | Has Tenure | Unknown | Coverage | Improvement |
|--------|-----------|---------|----------|-------------|
| Test | 4,692 (78.15%) | 1,312 (21.85%) | 78.15% | **27.9x** |
| Training | 19,469 (78.71%) | 5,265 (21.29%) | 78.71% | **8.1x** |
| **Overall** | **24,161 (78.6%)** | **6,577 (21.4%)** | **78.6%** | **7.9x** |

### Tenure Distribution (After Fix)
| Tenure Bucket | Leads | Percentage |
|--------------|-------|------------|
| 120+ months | 12,041 | 39.17% |
| 48-120 months | 9,089 | 29.57% |
| 24-48 months | 2,093 | 6.81% |
| 12-24 months | 552 | 1.80% |
| 0-12 months | 386 | 1.26% |
| Unknown | 6,577 | 21.40% |

---

## Impact

### Model Quality
- **Before**: Model missing critical tenure feature for 91.6% of leads
- **After**: Model has tenure data for 78.6% of leads
- **Expected**: Significant improvement in model performance (tenure is a key feature with 4.05x lift for short tenure)

### Feature Engineering
- Phase 2: ✅ Re-run complete (tenure coverage fixed)
- All gates passed: 5/5

---

## Next Steps

1. ✅ **Phase 2**: Re-run complete
2. ⏭️ **Phase 3**: Re-run leakage audit (verify no new leakage introduced)
3. ⏭️ **Phase 4**: Re-run multicollinearity analysis (feature set may change)
4. ⏭️ **Phase 5**: Re-run train/test split
5. ⏭️ **Phase 6**: Re-run model training (expect improved performance)
6. ⏭️ **Phase 7**: Re-run overfitting detection

---

## Files Modified

- `sql/phase_2_feature_engineering.sql` - Added `history_firm`, `current_snapshot`, and updated `current_firm` CTEs
- `reports/tenure_investigation.md` - Investigation report
- `reports/tenure_fix_summary.md` - This summary

---

## Validation

- ✅ PIT compliance check passed (99% of start dates older than 1 year)
- ✅ Phase 2 re-run successful (all gates passed)
- ✅ Tenure coverage increased from 8.4% to 78.6%
- ✅ No duplicate lead_ids introduced
- ✅ Row count preserved (30,738 leads)

