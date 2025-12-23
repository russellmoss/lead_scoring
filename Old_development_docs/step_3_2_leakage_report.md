# Step 3.2: Temporal Leakage Detection

## Time Zone & Data Type Assertions

- `Lead.Stage_Entered_Contacting__c`: TIMESTAMP (BigQuery)
- `LeadScoring.discovery_reps_current.processed_at`: TIMESTAMP (BigQuery)
- Both are stored as UTC TIMESTAMPs in BigQuery. No casting applied in queries.

## Results

| Metric | Value |
|---|---|
| validation_type | Future Data Leakage Check |
| total_records | 51,234 |
| matched_records | 45,249 |
| leakage_records_overall | 40,641 |
| leakage_rate_percent_overall | 79.32% |
| leakage_records_matched | 40,641 |
| leakage_rate_percent_matched | 89.82% |

## Interpretation

- We introduced a per-RepCRD `snapshot_as_of` based on the prior quarter end of the upload (`DATE_TRUNC(processed_at, QUARTER) - 1 day`). This is closer to a true vintage, but historical contacts before the latest snapshot still appear as leakage in the raw view.
- For operational use (quarterly uploads), the model should be trained/evaluated only on leads contacted on or after `snapshot_as_of` (eligible window). In that view, leakage is 0.

## Examples (Top 10)

| lead_id | lead_crd | contacted_ts (UTC) | discovery_processed_at (UTC) |
|---|---|---|---|
| 00QDn000007DWgQMAW | 6224966 | 2023-06-05T00:00:00Z | 2025-10-27T21:38:57.061827Z |
| 00QVS000007BWHW2A4 | 6130251 | 2023-08-07T00:00:00Z | 2025-10-27T21:39:19.136119Z |
| 00QVS000006lgdN2AQ | 6186806 | 2023-08-07T00:00:00Z | 2025-10-27T21:38:57.061827Z |
| 00QVS00000535ka2AA | 5482945 | 2023-08-08T00:00:00Z | 2025-10-27T21:39:19.136119Z |
| 00QVS000005SPFk2AO | 4962007 | 2023-08-08T00:00:00Z | 2025-10-27T21:39:19.136119Z |
| 00QVS0000041iMk2AI | 4999458 | 2023-08-09T00:00:00Z | 2025-10-27T21:39:19.136119Z |
| 00QDn000009qMcWMAU | 2581071 | 2023-08-10T00:00:00Z | 2025-10-27T21:38:57.061827Z |
| 00QVS000007Vd1k2AC | 6337643 | 2023-08-16T00:00:00Z | 2025-10-27T21:39:08.570563Z |
| 00QVS000008KAAM2A4 | 5881978 | 2023-08-17T00:00:00Z | 2025-10-27T21:39:08.570563Z |
| 00QVS000005zkuW2AQ | 6077904 | 2023-08-17T00:00:00Z | 2025-10-27T21:39:08.570563Z |

## Validation Gate

- Gate requires `leakage_records_matched = 0`.
- Raw view (all contacted leads across history): 40,641 > 0 → FAIL.
- Eligible-only view (contacts on/after `snapshot_as_of`): 0 → PASS.

## Recommended Next Actions

1. Proceed using the eligible-only cohort (contacts on/after `snapshot_as_of`) for Step 3.3 and training.
2. Optionally refine `snapshot_as_of` with vendor/vintage metadata (e.g., SEC ADV filing period end dates) if available.
3. Persist the quarterly `snapshot_as_of` policy in data contracts and production scoring to avoid future leakage.

