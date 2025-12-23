# Email to Jamie - Financial Columns Request

**Subject:** Request for Financial Metrics in RIARepDataFeed Historical Snapshots

**To:** Jamie  
**From:** [Your Name]  
**Date:** November 4, 2025

---

Hi Jamie,

Thank you again for providing the historical RIARepDataFeed CSV files - they've been very helpful for our lead scoring model development.

We're reaching out because we've identified that the RIARepDataFeed files don't include financial metrics that are critical for our model's performance. These financial metrics are available in the current MarketPro data downloads (we can see them in the discovery_t1, discovery_t2, and discovery_t3 files we download from the site), but they're missing from the historical RIARepDataFeed snapshots.

**Question:** Is it possible to include these financial columns in the historical RIARepDataFeed snapshots you provide? If not, is there an alternative way to get historical financial data for these snapshots?

We know these columns exist in the current downloads (discovery_t1/t2/t3), so we're hoping they might be available historically as well.

## Financial Columns We Need (Rep-Level)

### Core Financial Metrics:
- `TotalAssetsInMillions` - Total assets under management
- `NumberClients_Individuals` - Number of individual clients
- `NumberClients_HNWIndividuals` - Number of high-net-worth individual clients
- `NumberClients_RetirementPlans` - Number of retirement plan clients
- `Number_IAReps` - Number of investment advisor reps

### Asset Breakdowns:
- `AssetsInMillions_Individuals` - AUM from individual clients
- `AssetsInMillions_HNWIndividuals` - AUM from HNW individual clients
- `AssetsInMillions_MutualFunds` - AUM in mutual funds
- `AssetsInMillions_PrivateFunds` - AUM in private funds
- `AssetsInMillions_Equity_ExchangeTraded` - AUM in ETFs
- `TotalAssets_SeparatelyManagedAccounts` - AUM in SMAs
- `TotalAssets_PooledVehicles` - AUM in pooled vehicles

### Growth Metrics:
- `AUMGrowthRate_1Year` - 1-year AUM growth rate
- `AUMGrowthRate_5Year` - 5-year AUM growth rate

### Percentage Metrics:
- `PercentClients_HNWIndividuals` - % of clients that are HNW
- `PercentClients_Individuals` - % of clients that are individuals
- `PercentAssets_HNWIndividuals` - % of AUM from HNW clients
- `PercentAssets_Individuals` - % of AUM from individual clients
- `PercentAssets_MutualFunds` - % of AUM in mutual funds
- `PercentAssets_PrivateFunds` - % of AUM in private funds
- `PercentAssets_Equity_ExchangeTraded` - % of AUM in ETFs

### Custodian Relationships:
- `CustodianAUM_Schwab` - AUM custodied at Schwab
- `CustodianAUM_Fidelity_NationalFinancial` - AUM custodied at Fidelity
- `CustodianAUM_Pershing` - AUM custodied at Pershing
- `CustodianAUM_TDAmeritrade` - AUM custodied at TD Ameritrade
- `Custodian1` through `Custodian5` - Custodian names (if available)

## Why This Matters

These financial metrics are among the most predictive features in our lead scoring model - 8 of our top 20 features are financial. Without historical financial data in the snapshots, we're forced to use current financial data for historical leads, which creates a temporal mismatch in our model training.

Having historical financial snapshots would allow us to:
1. Train a more accurate model with point-in-time correct data
2. Better understand how financial metrics change over time
3. Improve our model's predictive performance

## Current Workaround

Right now, we're joining financial data from the current MarketPro snapshot to all historical leads, but this assumes financial metrics are relatively stable over time. Having actual historical financial snapshots would be much more accurate.

## Alternative Solutions

If these columns aren't available in the RIARepDataFeed snapshots, we'd appreciate any guidance on:
1. **Alternative data sources** - Are there other files or exports that contain historical financial data?
2. **Data availability** - Is historical financial data available from MarketPro, even if not in the RIARepDataFeed format?
3. **Timeline** - If these columns can be added, what would be the timeline?

## What We Currently Have

The RIARepDataFeed files we received contain excellent rep-level metadata (licenses, designations, tenure, firm associations, locations), but we're missing the financial metrics that are critical for model performance.

We understand if these columns aren't available in the historical snapshots - we just want to confirm so we can plan accordingly. Any guidance you can provide would be greatly appreciated.

Thank you for your help!

Best regards,  
[Your Name]  
[Your Title]  
[Your Contact Information]

---

**P.S.** The files we currently download from the MarketPro site (discovery_t1, discovery_t2, discovery_t3) do contain these financial columns, so we know the data exists. We're just wondering if it's possible to get this same data in the historical RIARepDataFeed snapshots.

