# Phase 7: V3 Production Deployment Guide

**Date:** 2025-12-21 19:30  
**Model Version:** v3.1-final-20241221  
**Status:** Ready for Deployment

---

## Deployment Checklist

### 1. BigQuery Production View

**File:** `sql/phase_7_production_view.sql`

**Action Required:**
- Execute SQL in BigQuery Console (location: `northamerica-northeast2`)
- Creates view: `ml_features.lead_scores_v3_current`
- This view provides real-time scoring for all leads

**Schedule (Optional):**
- Can be scheduled to refresh daily at 6:00 AM EST
- Or use as on-demand view (refreshes automatically)

### 2. Salesforce Integration

**File:** `sql/phase_7_salesforce_sync.sql`

**Field Mappings:**
| Salesforce Field | Source | Description |
|------------------|--------|-------------|
| `Lead_Score_Tier__c` | score_tier | TIER_1_PRIME_MOVER, TIER_2_MODERATE_BLEEDER, etc. |
| `Lead_Tier_Display__c` | tier_display | 🥇 Prime Mover, 🥈 Moderate Bleeder, etc. |
| `Lead_Expected_Lift__c` | expected_lift | Numeric lift value (e.g., 3.40) |
| `Lead_Expected_Conv__c` | expected_conversion | Calibrated conversion rate (e.g., 0.1350) |
| `Lead_Action__c` | action_recommended | Channel-specific action recommendation |
| `Lead_Model_Version__c` | model_version | v3.1-final-20241221 |
| `Lead_Score_Timestamp__c` | scored_at | Timestamp of scoring |

**Action Required:**
1. Create custom fields in Salesforce (if not already created)
2. Set up data sync pipeline (BigQuery → Salesforce)
3. Configure sync frequency (recommended: daily)

### 3. SGA Dashboard

**View:** `ml_features.sga_priority_list`

**Purpose:** Provides SGA-friendly view of priority leads (Tier 1 and Tier 2 only)

**Access:** Can be connected to Looker, Data Studio, or other BI tools

**Columns:**
- advisor_name, firm_name, advisor_crd
- priority_tier, tier_display, expected_lift
- next_action, context_notes
- contacted_date, scored_at

### 4. Weekly Report Generation

**Recommended:** Set up automated weekly report generation

**Query Template:**
```sql
SELECT 
    score_tier,
    COUNT(*) as new_leads,
    ROUND(AVG(expected_lift), 2) as avg_lift
FROM `savvy-gtm-analytics.ml_features.lead_scores_v3_current`
WHERE scored_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY score_tier
ORDER BY 
    CASE score_tier
        WHEN 'TIER_1_PRIME_MOVER' THEN 1
        WHEN 'TIER_2_MODERATE_BLEEDER' THEN 2
        WHEN 'TIER_3_EXPERIENCED_MOVER' THEN 3
        WHEN 'TIER_4_HEAVY_BLEEDER' THEN 4
        ELSE 99
    END
```

---

## Validation Steps

1. ✅ Production view SQL generated
2. ✅ Salesforce sync query generated
3. ✅ SGA dashboard view created
4. ⏳ Production view deployed (manual step)
5. ⏳ Salesforce fields created (manual step)
6. ⏳ Salesforce sync configured (manual step)

---

## Next Steps

1. **Deploy Production View:** Execute `phase_7_production_view.sql` in BigQuery
2. **Create Salesforce Fields:** Add custom fields to Lead object
3. **Configure Sync:** Set up BigQuery → Salesforce data pipeline
4. **Test Integration:** Verify tier assignments appear in Salesforce
5. **Train SGA Team:** Provide tier interpretation guide

---

## Support

For questions or issues, refer to:
- Model Registry: `models/model_registry_v3.json`
- Execution Log: `EXECUTION_LOG.md`
- Tier Calibration: `ml_features.tier_calibration_v3`
