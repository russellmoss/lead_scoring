# Savvy Wealth Lead Scoring Model

## Overview

This repository contains the Savvy Wealth lead scoring model, a machine learning system designed to predict the likelihood that a financial advisor will schedule an initial discovery call (become an MQL - Marketing Qualified Lead) after being contacted by our sales team. The model uses XGBoost and is trained on data from both Salesforce (our CRM) and Discovery Data (MarketPro), an external RIA (Registered Investment Advisor) data provider.

## Model Performance

The model achieves the following performance metrics:
- **Average Precision**: 0.1492 (14.92%)
- **ROC AUC**: 0.7916 (79.16%)
- **Top 20% Precision**: 10.27% (3.05x lift over baseline)
- **Top 10% Precision**: 13.23% (3.93x lift over baseline)

The baseline conversion rate is approximately 3.36%, meaning the model can identify high-potential leads with significantly better precision than random selection.

## Model Architecture

### Data Sources
1. **Salesforce**: Internal CRM containing lead information, contact history, and conversion data
2. **Discovery Data (MarketPro)**: External RIA data provider with comprehensive advisor and firm information

### Model Type
- **Algorithm**: XGBoost (eXtreme Gradient Boosting)
- **Target Variable**: `EverCalled` - Binary indicator of whether a lead scheduled a call
- **Class Imbalance Handling**: SMOTE (Synthetic Minority Over-sampling Technique)
- **Calibration**: Platt scaling for better probability estimates

### Feature Engineering
The model uses 67 engineered features across three categories:

#### Base Features (31 features)
- Firmographics: `TotalAssetsInMillions`, `Number_Employees`, `Number_InvestmentAdvisoryClients`
- Advisor tenure: `DateBecameRep_NumberOfYears`, `DateOfHireAtCurrentFirm_NumberOfYears`
- Client composition: `NumberClients_HNWIndividuals`, `AssetsInMillions_Individuals`
- Growth metrics: `AUMGrowthRate_1Year`, `AUMGrowthRate_5Year`
- Registration details: `NumberFirmAssociations`, `NumberRIAFirmAssociations`

#### Metropolitan Area Dummies (5 features)
- Top 5 metropolitan areas: Chicago, Dallas, Los Angeles, Miami, New York

#### Engineered Features (31 features)
- **Efficiency metrics**: `AUM_per_Client`, `AUM_per_Employee`, `Clients_per_IARep`
- **Growth indicators**: `Growth_Momentum`, `Growth_Acceleration`, `Positive_Growth_Trajectory`
- **Firm stability**: `Firm_Stability_Score`, `Is_Veteran_Advisor`, `High_Turnover_Flag`
- **Client focus**: `HNW_Client_Ratio`, `Premium_Positioning`, `Mass_Market_Focus`
- **Operational metrics**: `Branch_Advisor_Density`, `Complex_Registration`, `Multi_RIA_Relationships`

## File Structure

```
Final Model_Russ/
├── FinalLeadScorePipeline.ipynb    # Main Jupyter notebook with model training
├── dataload_functions.py           # Salesforce and Discovery Data integration
├── feature_engineering_functions.py # Feature engineering pipeline
├── column_cleaning_functions.py    # Data cleaning and preprocessing
├── model_visualizer.py             # Model evaluation and visualization tools
└── data/
    └── raw_discovery_data/         # Raw Discovery Data exports
        └── README.TXT              # Data source documentation
```

## Prerequisites

### Required Python Packages
```bash
pip install pandas numpy scikit-learn xgboost imbalanced-learn plotly python-dotenv simple-salesforce
```

### Environment Setup
Create a `.env` file in the project root with your Salesforce credentials:
```env
INSTANCE_URL=your_salesforce_instance_url
USERNAME=your_salesforce_username
PASSWORD=your_salesforce_password
SECURITY_TOKEN=your_security_token
```

### Data Requirements
1. **Salesforce Data**: Lead records with CRD numbers and conversion tracking
2. **Discovery Data**: RIA representative and firm data exports (CSV format)

## Jupyter Setup and Usage

### Installing JupyterLab
Install JupyterLab along with the required packages:
```bash
pip install pandas numpy scikit-learn xgboost imbalanced-learn plotly python-dotenv simple-salesforce jupyter jupyterlab
```

### Starting JupyterLab
Since the `jupyter` command may not be in your PATH, use the Python module syntax:
```bash
python -m jupyterlab
```

This will start JupyterLab and display output like:
```
[I 2025-10-27 12:35:32.808 ServerApp] Jupyter Server 2.17.0 is running at:
[I 2025-10-27 12:35:32.808 ServerApp] http://localhost:8888/lab?token=9b1efeaf9e6400a0802a47809b966e47a925c209ce080909
```

### Accessing JupyterLab
1. **Copy the URL** from the terminal output (e.g., `http://localhost:8888/lab?token=9b1efeaf9e6400a0802a47809b966e47a925c209ce080909`)
2. **Paste it into your browser** or click the link if it opens automatically
3. **If prompted for authentication**, use the token from the URL (the part after `token=`)

### Setting Up a Password (Optional but Recommended)
1. **On the login page**, enter the token in the "Token" field
2. **Enter a new password** in the "New Password" field
3. **Click "Setup a Password"**
4. **Next time**, you can just use your password instead of the token

### Navigating to Your Project
1. **In JupyterLab's file browser** (left panel), navigate to your project directory
2. **Open** `Final Model_Russ/FinalLeadScorePipeline.ipynb`
3. **The notebook will open** in the main workspace

### Running the Notebook
1. **Click on a cell** to select it
2. **Press Shift+Enter** to run the cell
3. **Continue running cells** in order from top to bottom
4. **Wait for each cell** to complete before running the next one

### Stopping JupyterLab
- **In the terminal** where JupyterLab is running, press **Ctrl+C** twice to stop the server
- **Close the browser tab** when done

### Troubleshooting JupyterLab
- **"jupyter command not found"**: Use `python -m jupyterlab` instead
- **Can't access localhost:8888**: Make sure JupyterLab is still running in the terminal
- **Token expired**: Restart JupyterLab to get a new token
- **Notebook not trusted**: Click "Trust" when prompted, or go to File → Trust Notebook

## How to Use the Model

### Step 1: Data Preparation

#### 1.1 Export Salesforce Data
Run the Salesforce query in the notebook to export lead data:
```python
query = """
SELECT Address, City, Company, Conversion_Channel__c, ConvertedDate,
    ConvertedOpportunityId, CreatedDate, Disposition__c, Email, 
    Experimentation_Tag__c, External_Agency__c, FA_CRD__c, FirstName, 
    Full_Prospect_ID__c, IsConverted, LastActivityDate, LastModifiedDate, 
    LastName, LeadSource, Lead_List_Name__c, LinkedIn_Profile_Apollo__c, 
    MobilePhone, Mobile_Phone_2__c, Name, Savvy_Lead_Score__c, 
    Stage_Entered_Contacting__c, Stage_Entered_Call_Scheduled__c, State, 
    Status, Title, OwnerId, Owner.Name
FROM Lead
"""
```

#### 1.2 Prepare Discovery Data
Place Discovery Data CSV files in the `data/raw_discovery_data/` directory. The system will automatically concatenate all CSV files.

### Step 2: Model Training

#### 2.1 Run the Complete Pipeline
Execute the `FinalLeadScorePipeline.ipynb` notebook in order:

1. **Data Loading**: Load and merge Salesforce and Discovery Data
2. **Data Cleaning**: Remove duplicates, handle missing values, clean column names
3. **Feature Engineering**: Create 67 engineered features
4. **Model Training**: Train XGBoost with SMOTE and calibration
5. **Model Evaluation**: Generate performance metrics and visualizations

#### 2.2 Key Configuration
```python
# Model parameters
XGBoost parameters:
- n_estimators: 600
- max_depth: 6
- learning_rate: 0.015
- scale_pos_weight: 28.7 (handles class imbalance)
- subsample: 0.8
- colsample_bytree: 0.7

# SMOTE parameters
- sampling_strategy: 0.1 (brings minority class to 10% of majority)
- k_neighbors: 5
```

### Step 3: Model Scoring

#### 3.1 Score New Leads
```python
# Load trained model
import pickle
with open('m5_calibrated_model.pkl', 'rb') as f:
    model = pickle.load(f)

# Score new data
scores = model.predict_proba(new_data[feature_columns])[:, 1]

# Create score buckets
score_buckets = pd.cut(scores, 
    bins=[0, 0.02, 0.05, 0.10, 0.20, 1.0],
    labels=["Cold", "Cool", "Warm", "Hot", "Very Hot"])
```

#### 3.2 Score Interpretation
- **Very Hot (0.20-1.00)**: Immediate outreach - high priority
- **Hot (0.10-0.20)**: Contact this week
- **Warm (0.05-0.10)**: Contact this month
- **Cool (0.02-0.05)**: Nurture campaign
- **Cold (0.00-0.02)**: Do not contact

### Step 4: Model Evaluation

#### 4.1 Performance Metrics
The model provides several evaluation metrics:
- **Average Precision**: Overall model performance on imbalanced data
- **ROC AUC**: Area under the receiver operating characteristic curve
- **Precision@Top20%**: Precision when selecting top 20% of leads
- **Lift**: Improvement over random selection

#### 4.2 Feature Importance
The model tracks feature importance to understand which factors drive predictions:
- **Top Features**: Multi_RIA_Relationships, Mass_Market_Focus, HNW_Asset_Concentration
- **Tenure Factors**: DateBecameRep_NumberOfYears, Firm_Stability_Score
- **Client Metrics**: AverageAccountSize, Individual_Asset_Ratio

## Model Comparison and Evaluation

### Comparing with New Models

To evaluate a new model against this baseline:

#### 1. Prepare Evaluation Data
```python
# Use the same test set for fair comparison
X_test, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Ensure same feature engineering pipeline
new_model_data = feature_engineer.engineer_features(new_data, feature_columns)
```

#### 2. Run Comparative Analysis
```python
# Evaluate both models on same test set
baseline_metrics = evaluate_model(m5_calibrated, X_test, y_test)
new_model_metrics = evaluate_model(new_model, X_test, y_test)

# Compare key metrics
comparison = {
    'Average Precision': [baseline_metrics['avg_precision'], new_model_metrics['avg_precision']],
    'ROC AUC': [baseline_metrics['roc_auc'], new_model_metrics['roc_auc']],
    'Top 20% Precision': [baseline_metrics['top20_precision'], new_model_metrics['top20_precision']]
}
```

#### 3. Statistical Significance Testing
```python
from scipy import stats

# Compare AUC scores
baseline_auc = baseline_metrics['roc_auc']
new_auc = new_model_metrics['roc_auc']

# Perform statistical test (example with bootstrap)
# This would require implementing bootstrap confidence intervals
```

### Key Evaluation Criteria

1. **Primary Metric**: Average Precision (AP) - most important for imbalanced data
2. **Business Metric**: Top 20% Precision - practical business impact
3. **Stability**: Performance across different time periods
4. **Feature Importance**: Interpretability and business logic

## Model Maintenance

### Retraining Schedule
- **Frequency**: Every 60 days or when performance degrades
- **Trigger**: 30% drop in Top 20% precision for 7 consecutive days
- **Data Window**: Rolling 180-day training window

### Monitoring
- **Data Drift**: Population Stability Index (PSI) for key features
- **Performance Drift**: Weekly precision/recall monitoring
- **Calibration Drift**: Expected vs observed conversion rates

### Model Versioning
- Store model artifacts with version numbers
- Maintain performance baselines for comparison
- Document feature changes and data updates

## Troubleshooting

### Common Issues

#### 1. Data Quality Problems
```python
# Check for missing CRD numbers
missing_crds = sf['FA_CRD__c'].isna().sum()
print(f"Missing CRDs: {missing_crds}")

# Check Discovery Data completeness
dd_coverage = len(merged_data[merged_data['RepCRD'].notna()]) / len(merged_data)
print(f"Discovery Data coverage: {dd_coverage:.2%}")
```

#### 2. Feature Engineering Errors
```python
# Verify feature columns exist
missing_features = set(feature_columns) - set(model_data.columns)
if missing_features:
    print(f"Missing features: {missing_features}")
```

#### 3. Model Performance Issues
```python
# Check class balance
print(f"Positive class rate: {y.mean():.2%}")

# Verify SMOTE application
print(f"Training set shape: {X_train.shape}")
print(f"Training positive rate: {y_train.mean():.2%}")
```

## Business Impact

### Expected Outcomes
- **3-4x improvement** in lead conversion rates for top-scored leads
- **Reduced wasted effort** on low-probability prospects
- **Improved SGA efficiency** through prioritized call queues
- **Better resource allocation** based on lead quality

### Implementation in Salesforce
1. **Score Field**: Add `Savvy_Lead_Score__c` to Lead object
2. **Tier Field**: Add `Score_Tier__c` picklist (A/B/C)
3. **List Views**: Create tiered views for SGA prioritization
4. **Automation**: Daily scoring job via Process Builder/Flow

## Support and Contact

For technical questions or model updates, contact the Data Science team or refer to the model documentation in the `savvy_lead_scoring_focused_model_plan_contacted_→_mql_v_1.md` file for the next iteration of the model.

## License

This model is proprietary to Savvy Wealth and intended for internal use only.
