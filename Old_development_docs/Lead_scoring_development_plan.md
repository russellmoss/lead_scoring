# Lead Scoring Model Development Plan (V12-Aligned)

**Project:** Savvy Wealth Lead Scoring Engine (Contacted → MQL)  
**Current Status:** Phase 0, Unit 0 In Progress – True-Vintage Data Intake Orchestrated  
**Last Updated:** November 10, 2025  
**Next Phase:** Phase 0, Unit 1 – Historical Snapshot Normalization  

---

## 🎯 Core Objectives

We will rebuild the lead scoring system using the **V12 direct-lead architecture**: a temporally correct pipeline that links Salesforce leads to historical Discovery snapshots, trains on point-in-time features, removes PII, and includes SHAP explainability plus calibration. The model must:

- Achieve **≥0.07 AUC-PR** (target lift over the 4% baseline conversion rate) on temporally held-out data.
- Deliver **≥30% lift** in MQLs per 100 dials within top deciles (target ≥6.5% conversion in top 10% bucket vs 4% baseline).
- Provide per-lead narratives powered by SHAP attributions.
- Respect privacy (no raw geographic PII) and survive stability audits (collinearity, multicollinearity, leakage, overfitting).

---

## 🧭 Phase Overview

| Phase | Purpose | Primary Deliverables |
|-------|---------|----------------------|
| **Phase 0** | Data Foundation & Integrity | Historical snapshots, leakage-free training table |
| **Phase 1** | Model Development (V12 Direct) | Feature selection, XGBoost training, SHAP artifacts |
| **Phase 2** | Pre-Production Hardening | Calibration, shadow scoring, stress testing |
| **Phase 3** | Experimentation | Randomized A/B test with blocking and monitoring |
| **Phase 4** | Production & Scale | Continuous monitoring, quarterly refresh |

Each phase contains **Agentic Units** with validation gates. Progress halts if any gate fails.

---

## Phase 0 – Data Foundation & Integrity

### Unit 0: Vendor Snapshot Intake (Human + Agent)
- **Task 0.1 (Human):** Retrieve the 8 quarterly advisor and firm snapshots (True Vintages) from MarketPro for the past two years. Upload each CSV to BigQuery as `LeadScoring.snapshot_reps_YYYY_qX` and `LeadScoring.snapshot_firms_YYYY_qX`; log row counts and schemas.
- **Task 0.2 (Agent):** Validate table schemas, enforce UTC timestamps, and record the manifest in `data_ingest_manifest.md`.

**Gate 0:** All 16 snapshot tables exist, schema matches spec, and ingestion log is complete.

### Unit 1: Historical Snapshot Normalization
- **Task 1.1:** Create master union-all views `v_discovery_reps_all_vintages` and `v_discovery_firms_all_vintages`, adding `snapshot_quarter` date columns.
- **Task 1.2:** Run completeness checks: CRD matching rate, null coverage, and outlier detection per snapshot.
- **Artifact:** `step_1_snapshot_normalization_report.md`

**Gate 1:** CRD match rate ≥ 95%; no missing quarterly slices; outliers documented; views queryable.

### Unit 2: Salesforce Lead Alignment & Temporal Integrity
- **Task 2.1:** Build `LeadScoring.leads_contacted_v12` view with core lead fields, enforcing UTC and ISO formatting.
- **Task 2.2:** Assign `contact_quarter = DATE_TRUNC(Stage_Entered_Contacting__c, QUARTER)`.
- **Task 2.3:** Run temporal leakage checks ensuring `snapshot_quarter <= contact_quarter`.
- **Artifact:** `step_2_temporal_integrity_report.md`

**Gate 2:** Leakage rate for matched leads = 0%; timestamp types confirmed; fail-hard if mismatched.

### Unit 3: Point-in-Time Feature Engineering (True Vintage)
- **Task 3.1:** Recreate V12 engineered features (tenure, stability, data-quality flags) directly in SQL referencing historical snapshots; drop raw PII.
- **Task 3.2:** Label target via 30-day window on `Stage_Entered_Call_Scheduled__c` with right-censoring.
- **Task 3.3:** Produce final training table `LeadScoring.step_3_3_training_dataset_v12` sorted by `FilterDate_v12`.
- **Artifact:** `step_3_3_class_imbalance_analysis_v12.md`

**Gate 3:** Negative conversion counts = 0; positive class share between 3–6%; 0 duplicated leads (ROW_NUMBER audit).

### Unit 4: Statistical Validation Pre-Training
- **Task 4.1:** VIF and correlation analysis on continuous features (flag >0.90 correlations, VIF>10).
- **Task 4.2:** PSI drift checks across quarters to flag unstable features.
- **Task 4.3:** Confirm temporal split viability (80/20 quantile or blocked folds).
- **Artifact:** `statistical_validation_report_pre_training_v12.md`

**Gate 4:** All high-VIF or highly collinear features resolved; PSI<0.25; train/test split documented.

---

## Phase 1 – Model Development (Direct V12)

### Unit 5: Feature Contract & Configs
- **Task 5.1:** Generate `config/v12_model_config.json` (global seed, CV folds, imbalance strategy placeholders, calibration thresholds).
- **Task 5.2:** Produce `config/v12_feature_schema.json` with dtype, nullability, expected ranges, `is_mutable`, and `is_temporal` flags.
- **Task 5.3:** Create `feature_contract_validation.py` to assert schema compliance before training.

**Gate 5:** Config and schema load without error; validation script passes on training table.

### Unit 6: Feature Selection & Pre-Filtering
- **Task 6.1:** Inside blocked time-series CV, apply IV<0.02 filter, VIF>10 pruning, and correlation culling (all using train-fold data only).
- **Task 6.2:** Log removed features and rationale in `feature_selection_report_v12.md`.
- **Task 6.3:** Persist final feature order to `feature_order_v12.json`.

**Gate 6:** CV folds reproducible (indices saved); feature order consistent; no leakage of test data during filtering.

### Unit 7: Model Training (XGBoost Direct Lead)
- **Task 7.1:** Train imbalance strategies (scale_pos_weight vs SMOTE-on-fold) using blocked CV with ≥30-day gaps.
- **Task 7.2:** Select best strategy via mean AUC-PR + stability metrics; document in `model_training_report_v12.md`.
- **Task 7.3:** Train final model (`model_v12.pkl`) on full train window; record artifacts (importance CSV, metrics JSON).
- **Task 7.4:** Train baseline logistic regression (`model_v12_baseline_logit.pkl`) with simple imputers for audit.

**Gate 7:** AUC-PR (CV mean) ≥ 0.07; coefficient of variation < 20%; train-test AUC-PR gap < 15%.

### Unit 8: Model Diagnostics & SHAP Explainability
- **Task 8.1:** Generate SHAP values (TreeExplainer with fallback permutation) using temporally valid sample; save `feature_importance_v12.csv`, `shap_summary_plot_v12.png`, `salesforce_drivers_v12.csv`.
- **Task 8.2:** Create cohort explanations (AUM tier, tenure bands, metro) in `cohort_analysis_report_v12.md`.
- **Task 8.3:** Produce `shap_feature_comparison_report_v12.md` comparing against prior m5 importances.

**Gate 8:** SHAP artifacts non-empty; top features align with business logic (stability/tenure); driver file ready for narratives.

### Unit 9: Calibration & Probability Integrity
- **Task 9.1:** Fit Platt scaling or isotonic calibrators segmented by AUM tiers (<$100M, $100–500M, >$500M).
- **Task 9.2:** Validate Expected Calibration Error (ECE) per segment ≤ 0.05.
- **Task 9.3:** Save calibrated model (`model_v12_calibrated.pkl`) and calibration report.

**Gate 9:** Global and per-segment ECE ≤ 0.05; calibration report complete.

---

## Phase 2 – Pre-Production Hardening

### Unit 10: Pipeline Integration & Shadow Mode Prep
- **Task 10.1:** Package feature order, schema validator, and model weights into deployable bundle.
- **Task 10.2:** Build shadow scoring DAG (e.g., Composer/Airflow) scoring direct leads nightly.
- **Task 10.3:** Write `shadow_mode_runbook_v12.md`.

**Gate 10:** Dry-run executes successfully; feature validator passes; pipeline latency < 30 minutes per batch.

### Unit 11: Shadow Scoring & Stress Testing
- **Task 11.1:** Run 7-day shadow mode, logging success rate, latency, feature completeness.
- **Task 11.2:** Execute stress tests (2× volume, missing features, skewed class scenario) and document responses.
- **Artifact:** `shadow_scoring_metrics_v12.csv`, `pipeline_stress_test_report_v12.md`

**Gate 11:** >95% scoring success; no unhandled failures; stress tests meet SLOs; PSI drift < 0.05 day-over-day.

### Unit 12: Production Readiness & Governance
- **Task 12.1:** Compile `production_readiness_checklist_v12.md` including monitoring, rollback, on-call.
- **Task 12.2:** Configure alerting (`alerting_config_v12.json`) for failure rate, PSI drift, performance drop.
- **Task 12.3:** Validate privacy compliance (PII removed, only aggregated features exposed).

**Gate 12:** Checklist complete; alerts tested; compliance sign-off obtained.

---

## Phase 3 – Experimentation

### Unit 13: A/B Test Design & Power Analysis
- **Task 13.1:** Use baseline MQL rate to compute sample size for 50% lift at α=0.05, power=0.8; simulate 60% adoption scenario.
- **Task 13.2:** Draft `ab_test_power_analysis_v12.md` and `sga_adoption_tracking_plan_v12.md`.

**Gate 13:** Both normal and under-adoption power ≥ 0.8; adoption instrumentation defined.

### Unit 14: Randomization & Monitoring
- **Task 14.1:** Implement blocked randomization by AUM tier; produce `ab_test_assignments_v12.csv`.
- **Task 14.2:** Daily metric ingest (`ab_test_daily_metrics_v12.csv`) with lead-level outputs.
- **Task 14.3:** Interim analysis at week 4 (or 10-day equivalent) with safety checks (`ab_test_interim_analysis_v12.md`).

**Gate 14:** Treatment vs control balanced on key covariates; no safety flags; monitoring dashboards live.

### Unit 15: Final Analysis & Decision
- **Task 15.1:** Compute final lift, p-values, confidence intervals; document in `ab_test_final_analysis_v12.md`.
- **Task 15.2:** Recommend rollout decision with business impact summary.

**Gate 15:** Primary KPI significant (p<0.05) and lift ≥ 30%; if not, escalate for remediation.

---

## Phase 4 – Production & Scale

### Unit 16: Full Rollout & Monitoring
- **Task 16.1:** Deploy calibrated model to production scoring service.
- **Task 16.2:** Run daily health checks (success rate, latency, error rate), weekly class imbalance audits, monthly PSI drift reports.
- **Artifacts:** `production_health_dashboard_v12.json`, `monitoring_schedule_v12.yaml`, `feature_drift_detection_report_v12.md`

**Gate 16:** 30 consecutive days with no SLA breaches; weekly class balance within ±5%; PSI < 0.25.

### Unit 17: Quarterly Refresh & Snapshot Maintenance
- **Task 17.1:** Ingest new quarterly snapshots (repeat Phase 0 Unit 0 process).
- **Task 17.2:** Update master views via `ALTER VIEW`, regenerate training table, and retrain (yielding `model_v{N}.pkl`).
- **Task 17.3:** Document refresh in `model_refresh_protocol_v12.md`.

**Gate 17:** New model passes Phase 1 gates; change management approval recorded.

### Unit 18: Explainability & Salesforce Enablement
- **Task 18.1:** Update narratives pipeline with new SHAP drivers; ensure Gemini prompts align with suppressed score logic.
- **Task 18.2:** Maintain Salesforce field mappings (`salesforce_field_mapping_v12.csv`), UI specs, and SGA training guides.

**Gate 18:** Salesforce validation confirms narrative coverage = 100%; training materials refreshed; adoption ≥ 75%.

---

## 🔍 Continuous QA/QC Checkpoints

| Checkpoint | Scope | Pass Criteria |
|------------|-------|---------------|
| **Data Quality (between phases)** | CRD alignment, completeness, PSI | CRD ≥ 95%, completeness ≥ 95%, PSI < 0.25 |
| **Leakage Audit (pre-model & quarterly)** | Ensure `snapshot_quarter <= contact_quarter` | Leakage count = 0 |
| **Multicollinearity** | VIF, correlation matrices | All VIF < 10 (post-filter) |
| **Overfitting Monitoring** | Train vs test metrics, CV stability | Gap < 15%, CV CoV < 20% |
| **Explainability Stability** | SHAP rank drift vs prior release | Top-10 features stable within ±3 rank positions unless justified |
| **Calibration Audit** | Global + segmented ECE | All ≤ 0.05 |

Failure of any checkpoint halts downstream execution until remediated.

---

## 📈 Success Metrics

- **Technical:** AUC-PR ≥ 0.07, precision@10% ≥ 0.065 (vs 0.04 baseline), SHAP alignment with business intuition.
- **Business:** ≥30% lift in MQLs per 100 dials, ≥$2M incremental pipeline, ≥75% SGA adherence.
- **Operational:** <2% monthly pipeline failure, <4h recovery, ≥95% daily scoring success.

---

## 🔗 Key Resources

- `v12_production_model.py`, `v12_production_model_direct_lead.py`
- `LeadScoring.v_discovery_reps_all_vintages` & `LeadScoring.v_discovery_firms_all_vintages`
- `v12_shap_analysis.py`, `v12_generate_narratives.py`
- `TRAINING_ANALYSIS_Data_Leakage_Report.md` (legacy anti-patterns)
- `V12_Final_Model_Report.md`, `V12_PII_Compliant_Report_*.md`

---

## 🧰 Immediate Next Steps

1. Complete Phase 0 Unit 0 ingestion manifest and schema checks.  
2. Build master snapshot views and run leakage audits (Units 1–2).  
3. Recreate engineered features and training table using point-in-time joins (Unit 3).  
4. Execute statistical validation (Unit 4) before triggering model training automation.

Keep this document updated as each gate is cleared and as lessons emerge from subsequent iterations.

