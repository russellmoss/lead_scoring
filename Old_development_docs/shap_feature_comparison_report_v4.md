# SHAP Feature Comparison Report V4

**Generated:** 2025-11-03 19:37:27

## Executive Summary

* **Top V4 Feature:** `SocialMedia_LinkedIn`
* **Multi_RIA_Relationships V4 Rank:** #17
* **Multi_RIA_Relationships m5 Rank:** #1

## Did V4 Discover the Same 'Truth' as m5?

**Partially** - V4 model has a different top feature than m5.

**V4 Top Feature:** `SocialMedia_LinkedIn`

**Business Rationale:**

* V4 model was trained on temporally-correct data (Hybrid V2 strategy)
* V4 model removed PII features (FirstName, LastName, etc.) which were dominating V3
* The top features in V4 (`SocialMedia_LinkedIn`, `Education`, `Licenses`) represent real business signals
* `Multi_RIA_Relationships` may have lower importance in V4 due to:
  - Different data distribution in temporally-correct dataset
  - Feature interactions with other strong signals
  - Model learning different patterns without PII noise

## Top 25 Feature Comparison

| Rank | Feature | V4 Importance | V4 Rank | m5 Importance | m5 Rank | Difference |
|------|---------|---------------|---------|---------------|---------|------------|
| 1 | `SocialMedia_LinkedIn` | 0.019572 | 1 | 0.0000 | N/A | N/A |
| 2 | `Education` | 0.010010 | 2 | 0.0000 | N/A | N/A |
| 3 | `Licenses` | 0.007628 | 3 | 0.0000 | N/A | N/A |
| 4 | `Brochure_Keywords` | 0.006545 | 4 | 0.0000 | N/A | N/A |
| 5 | `Home_MetropolitanArea` | 0.004066 | 5 | 0.0000 | N/A | N/A |
| 6 | `Email_BusinessType` | 0.003704 | 6 | 0.0000 | N/A | N/A |
| 7 | `Email_PersonalType` | 0.003018 | 7 | 0.0000 | N/A | N/A |
| 8 | `Title` | 0.002975 | 8 | 0.0000 | N/A | N/A |
| 9 | `FirmWebsite` | 0.002732 | 9 | 0.0000 | N/A | N/A |
| 10 | `DateOfHireAtCurrentFirm_NumberOfYears` | 0.002711 | 10 | 0.0000 | N/A | N/A |
| 11 | `Branch_State` | 0.002374 | 11 | 0.0000 | N/A | N/A |
| 12 | `Custodian1` | 0.001418 | 12 | 0.0000 | N/A | N/A |
| 13 | `Complex_Registration` | 0.001028 | 13 | 0.0152 | 18.0 | -5 |
| 14 | `Home_State` | 0.000812 | 14 | 0.0000 | N/A | N/A |
| 15 | `Number_YearsPriorFirm2` | 0.000748 | 15 | 0.0000 | N/A | N/A |
| 16 | `Number_YearsPriorFirm1` | 0.000517 | 16 | 0.0000 | N/A | N/A |
| 17 | `Multi_RIA_Relationships` | 0.000468 | 17 | 0.0816 | 1.0 | 16 |
| 18 | `Number_YearsPriorFirm3` | 0.000465 | 18 | 0.0000 | N/A | N/A |
| 19 | `Gender` | 0.000444 | 19 | 0.0000 | N/A | N/A |
| 20 | `Branch_Latitude` | 0.000394 | 20 | 0.0000 | N/A | N/A |
| 21 | `Custodian2` | 0.000368 | 21 | 0.0000 | N/A | N/A |
| 22 | `Branch_Longitude` | 0.000358 | 22 | 0.0000 | N/A | N/A |
| 23 | `Number_YearsPriorFirm4` | 0.000263 | 23 | 0.0000 | N/A | N/A |
| 24 | `Total_Prior_Firm_Years` | 0.000229 | 24 | 0.0000 | N/A | N/A |
| 25 | `MilesToWork` | 0.000209 | 25 | 0.0000 | N/A | N/A |

## Calibration Metrics

* **Global ECE:** 0.0017

## Validation

✅ **Global ECE ≤ 0.05** - Calibration passed

✅ **All segment ECE ≤ 0.05** - Calibration passed

