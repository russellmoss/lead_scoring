# Lead Scoring Model Overview

The lead scoring process is a two-step model that involves data loading and preparation, followed by a data science pipeline for model creation and execution.

## Data Loading and Preparation (data_load.ipynb)

This initial phase focuses on aggregating and reconciling data from two primary sources: Salesforce and Discovery Data (MarketPro).

### Data Sources:

- **Salesforce**: Our internal CRM containing existing lead and client information.
- **Discovery Data (MarketPro)**: An external source for RIA (Registered Investment Advisor) data.

### Data Export Process:

- A known limitation in MarketPro prevents a bulk download of all RIA rep data at once.
- To work around this, the US is segmented into three geographic territories: T1 (Eastern US), T2 (Central US), and T3 (Western US). Data must be exported from each territory individually.
- To ensure a complete dataset, we match the downloaded MarketPro data against our Salesforce records using CRD

### Data Reconciliation:

- We identify any CRDs (Central Registration Depository numbers) that exist in Salesforce but are missing from our initial MarketPro export.
- We then perform a targeted search within MarketPro for these specific missing CRDs using the "Rep CRD" field under the "Titles and Licenses" section to complete our dataset.

## Data Science Pipeline (DataSciencePipeline.ipynb)

This is the core component where the predictive model is built and tested.

### Data Integration and Cleaning:

- The raw data is loaded, merging the datasets for RIA firms and RIA reps into a single dataframe.
- The merged data is cleaned extensively. This includes correcting data types (e.g., converting text objects to numerical types), checking for collinearity between variables, and standardizing column names.

### Feature Selection and Model Creation:

- After cleaning, relevant columns (features) are selected to build the model data.
- Several machine learning models are run to find the best performer.

### Models Tested:

- Logistic Regression
- Random Forest with Gradient Boosting
- XGBoost (eXtreme Gradient Boosting)

### Addressing Class Imbalance:

- The primary challenge is the highly biased target class. Only 2-3% of leads are in the "positive" class (i.e., a successful contact), as most people do not answer the phone.
- The SMOTE (Synthetic Minority Over-sampling TEchnique) method was used successfully with the Logistic Regression model to correct for this imbalance by creating synthetic examples of the minority class.