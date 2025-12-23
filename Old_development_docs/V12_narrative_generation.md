# SHAP + Gemini Narrative Pipeline

## Overview
We rebuilt the V12 lead-scoring explanation flow so every rep in `savvy-gtm-analytics.LeadScoring.Impact_Attendees_V12_Scores` now carries a narrative that explains their score. The pipeline combines model introspection (SHAP) with Gemini-generated summaries, and we added logic to highlight recent firm moves (which suppress scores).

## End-to-End Flow

- **Score + Snapshot Inputs**
  - `impact_attendees_v12_scores.csv`: latest model scores and metadata for 1,596 records (1,498 unique `RepCRD`).
  - `v12_shap_analysis.py`: regenerates per-rep SHAP contributions from the V12 model using the latest *as-of* date.

- **SHAP Generation**
  - Run `v12_shap_analysis.py --as-of-date 2025-11-08 --sample-size 2000`.
  - Produces `v12_shap_detail.csv` with full SHAP vectors for all reps and summary outputs for QA.
  - Uses permutation SHAP fallback for stability; merges in engineered features from discovery view to match scoring schema.

- **Narrative Enrichment**
  - `v12_generate_narratives.py` merges the SHAP detail with the scores, adds flags for reps who changed firms within the last 12 months, and batches JSON prompts to Gemini.
  - Prompt includes: percentile bucket, key positive/negative SHAP drivers, recency flag, and hire date.
  - Gemini responds with 2–3 sentence narratives tailored per bucket; if the recent-move flag is true, it explains the suppression explicitly.
  - Output saved locally (`impact_attendees_v12_scores_with_narratives.csv`) and written to BigQuery table `savvy-gtm-analytics.LeadScoring.Impact_Attendees_V12_Scores_Explained`.

- **Warehouse Sync**
  - We roll the explained table down to one row per `RepCRD` using a deterministic order (latest `snapshot_as_of_date`, recent-move indicator).
  - Update the production scores table with:
    ```sql
    UPDATE `savvy-gtm-analytics.LeadScoring.Impact_Attendees_V12_Scores` AS scores
    SET v12_narrative = explained.v12_narrative
    FROM (
      SELECT RepCRD,
             (ARRAY_AGG(v12_narrative ORDER BY snapshot_as_of_date DESC, recent_move_flag DESC))[OFFSET(0)] AS v12_narrative
      FROM `savvy-gtm-analytics.LeadScoring.Impact_Attendees_V12_Scores_Explained`
      GROUP BY RepCRD
    ) explained
    WHERE SAFE_CAST(scores.RepCRD AS INT64) = explained.RepCRD;
    ```
  - Post-sync validation:
    ```sql
    WITH latest_explained AS (
      SELECT RepCRD,
             (ARRAY_AGG(v12_narrative ORDER BY snapshot_as_of_date DESC, recent_move_flag DESC))[OFFSET(0)] AS v12_narrative
      FROM `savvy-gtm-analytics.LeadScoring.Impact_Attendees_V12_Scores_Explained`
      GROUP BY RepCRD
    )
    SELECT COUNT(*) AS mismatch_count
    FROM `savvy-gtm-analytics.LeadScoring.Impact_Attendees_V12_Scores` s
    JOIN latest_explained e ON SAFE_CAST(s.RepCRD AS INT64) = e.RepCRD
    WHERE s.v12_narrative != e.v12_narrative;
    ```
    Result: `mismatch_count = 0`.

## Suppression Logic
- Reps with a hire date within the past 12 months get `recent_move_flag = TRUE`.
- Scores for movers are capped at `0.33` (below median) before narrative generation.
- Gemini prompt directive: “If the recent move flag is true, explain that the score is suppressed because the rep just switched firms and is unlikely to move again soon.”

## Productionalization Suggestions

- **Automate Weekly Run**
  - Schedule the SHAP script and narrative generation job (e.g., Cloud Composer or GitHub Actions runner on Windows host).
  - Ensure `GEMINI_API_KEY` is available via secure secret manager.
  - Wrap the BigQuery update in a transaction with logging; emit row counts before/after updates.

- **Versioning & QA**
  - Store SHAP and narrative CSV outputs in a dated folder (`/Lead Scoring/exports/YYYYMMDD`).
  - Track model metadata (`v12_model_used`, `v12_metadata_used`) in BigQuery to tie narratives to specific scoring runs.
  - Compare percentile thresholds and random sample of narratives after each run.

- **Monitoring**
  - Alert if Gemini returns `[ERROR]` placeholders (e.g., missing API quota).
  - Validate that mover suppression count matches expected join with `October_snapshot`.
  - Keep the explained table append-only but dedupe on read; you can partition by `snapshot_as_of_date` for long-term storage.

## Manual Repro Steps

1. Activate environment in `C:\Users\russe\Documents\Lead Scoring`.
2. Run SHAP script:
   ```bash
   python v12_shap_analysis.py --as-of-date 2025-11-08 --sample-size 2000
   ```
3. Run narratives:
   ```bash
   python v12_generate_narratives.py \
       --shap-detail "C:/Users/russe/Documents/Lead Scoring/v12_shap_detail.csv" \
       --scores-csv "C:/Users/russe/Documents/Lead Scoring/impact_attendees_v12_scores.csv" \
       --output-csv "C:/Users/russe/Documents/Lead Scoring/impact_attendees_v12_scores_with_narratives.csv" \
       --project savvy-gtm-analytics \
       --output-bq-table savvy-gtm-analytics.LeadScoring.Impact_Attendees_V12_Scores_Explained
   ```
4. Sync narratives in BigQuery (SQL above).
5. Validate counts and inspect sample rows.

## Outcome
Every `RepCRD` now has:
- A SHAP-backed explanation,
- A Gemini-generated narrative describing the drivers and any recent-move suppression,
- A synchronized entry in both the explained table and production score table.

This pipeline can be rerun whenever the model or data refreshes, giving sales teams an interpretable, up-to-date view of lead prioritization.
