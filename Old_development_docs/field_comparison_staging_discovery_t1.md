# Field Comparison: discovery_firms_current vs staging_discovery_t1

## Summary
The `staging_discovery_t1` table contains firm-level data, but the field names are **different** from `discovery_firms_current`. Some fields exist with different names, while others do not exist and would need to be calculated.

## Field Mapping

### ✅ Fields That Exist (with different names)

| Requested Field (discovery_firms_current) | Equivalent Field (staging_discovery_t1) | Notes |
|-------------------------------------------|-----------------------------------------|-------|
| `total_firm_aum_millions` | `TotalAssetsInMillions` | ⚠️ Type: STRING (formatted like "$1,295.31") vs FLOAT |
| `total_schwab_aum` | `CustodianAUM_Schwab` | ✅ Type: FLOAT |
| `total_fidelity_aum` | `CustodianAUM_Fidelity_NationalFinancial` | ✅ Type: FLOAT |
| `total_pershing_aum` | `CustodianAUM_Pershing` | ✅ Type: FLOAT |
| `total_tdameritrade_aum` | `CustodianAUM_TDAmeritrade` | ✅ Type: FLOAT |
| `total_mutual_fund_aum` | `AssetsInMillions_MutualFunds` | ✅ Type: FLOAT |
| `total_private_fund_aum` | `AssetsInMillions_PrivateFunds` | ✅ Type: FLOAT |
| `total_etf_aum` | `AssetsInMillions_Equity_ExchangeTraded` | ✅ Type: FLOAT |
| `total_sma_aum` | `TotalAssets_SeparatelyManagedAccounts` | ✅ Type: FLOAT |
| `total_pooled_aum` | `TotalAssets_PooledVehicles` | ✅ Type: FLOAT |
| `avg_firm_growth_1y` | `AUMGrowthRate_1Year` | ✅ Type: FLOAT (but might need aggregation) |
| `avg_firm_growth_5y` | `AUMGrowthRate_5Year` | ✅ Type: FLOAT (but might need aggregation) |

### ❌ Fields That Do NOT Exist (would need calculation/aggregation)

| Requested Field | Status | Notes |
|----------------|--------|-------|
| `avg_rep_aum_millions` | ❌ NOT FOUND | Would need to calculate AVG(TotalAssetsInMillions) per firm |
| `max_rep_aum_millions` | ❌ NOT FOUND | Would need to calculate MAX(TotalAssetsInMillions) per firm |
| `min_rep_aum_millions` | ❌ NOT FOUND | Would need to calculate MIN(TotalAssetsInMillions) per firm |
| `aum_std_deviation` | ❌ NOT FOUND | Would need to calculate STDDEV(TotalAssetsInMillions) per firm |
| `aum_per_rep` | ❌ NOT FOUND | Would need to calculate TotalAssetsInMillions / Number_IAReps |
| `max_firm_growth_1y` | ❌ NOT FOUND | Would need to calculate MAX(AUMGrowthRate_1Year) per firm |
| `max_firm_growth_5y` | ❌ NOT FOUND | Would need to calculate MAX(AUMGrowthRate_5Year) per firm |
| `firm_growth_momentum` | ❌ NOT FOUND | Calculated field, doesn't exist |
| `accelerating_growth` | ❌ NOT FOUND | Calculated field, doesn't exist |
| `positive_growth_trajectory` | ❌ NOT FOUND | Calculated field, doesn't exist |
| `total_reps` | ❌ NOT FOUND | Could use COUNT(*) or MAX(Number_IAReps) per firm |
| `avg_clients_per_rep` | ❌ NOT FOUND | Would need AVG(NumberClients_Individuals) per firm |
| `avg_hnw_clients_per_rep` | ❌ NOT FOUND | Would need AVG(NumberClients_HNWIndividuals) per firm |
| `clients_per_rep` | ❌ NOT FOUND | Similar to avg_clients_per_rep |
| `hnw_clients_per_rep` | ❌ NOT FOUND | Similar to avg_hnw_clients_per_rep |
| `pct_reps_with_series_7` | ❌ NOT FOUND | Would need to check Licenses field and calculate percentage |
| `pct_reps_with_cfp` | ❌ NOT FOUND | Would need to check Licenses field and calculate percentage |
| `pct_veteran_reps` | ❌ NOT FOUND | Would need to check MilitaryBranch field and calculate percentage |
| `pct_reps_with_disclosure` | ❌ NOT FOUND | Would need to check RegulatoryDisclosures field and calculate percentage |
| `states_represented` | ❌ NOT FOUND | Would need COUNT(DISTINCT Branch_State) per firm |
| `metro_areas_represented` | ❌ NOT FOUND | Would need COUNT(DISTINCT Branch_MetropolitanArea) per firm |
| `avg_ia_reps_per_record` | ❌ NOT FOUND | Would need AVG(Number_IAReps) per firm |
| `pct_breakaway_reps` | ❌ NOT FOUND | Would need COUNT WHERE BreakawayRep = 'Yes' / COUNT(*) per firm |
| `large_rep_firm` | ❌ NOT FOUND | Calculated field, doesn't exist |

## Conclusion

**Answer: NO, `staging_discovery_t1` does NOT have the same fields.**

However, it has **similar fields with different names** for:
- AUM totals (with different naming convention)
- Custodian AUM (with different naming convention)
- Product AUM (with different naming convention)
- Growth rates (with different naming convention)

Many of the requested fields are **aggregated/calculated metrics** that don't exist directly in `staging_discovery_t1` and would need to be computed using GROUP BY and aggregate functions.

## Note on Data Structure

Based on the query results, `staging_discovery_t1` appears to have multiple rows per firm (we saw 3 rows for Savvy and 2 rows for Farther). This suggests the data might be at a different granularity (perhaps rep-level or record-level) that would need aggregation to match the firm-level view in `discovery_firms_current`.
