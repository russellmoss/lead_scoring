#!/usr/bin/env python3
"""Create unit_4_train_model_v2.py from week_4_train_model_v1.py with m5 feature engineering"""

# Read V1 script
with open('week_4_train_model_v1.py', 'r', encoding='utf-8') as f:
    v1_content = f.read()

# Read the m5 feature engineering function we created
with open('unit_4_train_model_v2.py', 'r', encoding='utf-8') as f:
    v2_partial = f.read()

# Extract the m5 feature engineering function
m5_fe_func_start = v2_partial.find('def create_m5_engineered_features')
m5_fe_func_end = v2_partial.find('def validate_against_schema', m5_fe_func_start)
m5_fe_func = v2_partial[m5_fe_func_start:m5_fe_func_end]

# Now build the complete V2 script
# Replace all _v1 with _v2
v2_content = v1_content.replace('_v1', '_v2')
v2_content = v2_content.replace('Week 4', 'Unit 4 V2')
v2_content = v2_content.replace('week_4_train_model_v1', 'unit_4_train_model_v2')
v2_content = v2_content.replace('BQ_TABLE = "savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset"', 'BQ_TABLE = "savvy-gtm-analytics.LeadScoring.step_3_3_training_dataset_v2"')

# Update step numbers
v2_content = v2_content.replace('[1/12]', '[1/13]')
v2_content = v2_content.replace('[2/12]', '[2/13]')
v2_content = v2_content.replace('[3/12]', '[4/13]')
v2_content = v2_content.replace('[4/12]', '[5/13]')
v2_content = v2_content.replace('[5/12]', '[6/13]')
v2_content = v2_content.replace('[6/12]', '[7/13]')
v2_content = v2_content.replace('[7/12]', '[8/13]')
v2_content = v2_content.replace('[8/12]', '[9/13]')
v2_content = v2_content.replace('[9/12]', '[10/13]')
v2_content = v2_content.replace('[10/12]', '[11/13]')
v2_content = v2_content.replace('[11/12]', '[12/13]')
v2_content = v2_content.replace('[12/12]', '[13/13]')

# Insert m5 feature engineering function after load_data_from_bigquery
insert_pos = v2_content.find('def validate_against_schema')
v2_content = v2_content[:insert_pos] + '\n' + m5_fe_func + '\n\n' + v2_content[insert_pos:]

# Update get_feature_columns to include m5 features (we already did this in the partial)
# Find the get_feature_columns function and replace it
get_feature_cols_start = v2_content.find('def get_feature_columns')
get_feature_cols_end = v2_content.find('def cast_categoricals_inplace', get_feature_cols_start)

# Get the updated version from v2_partial
updated_get_feature_cols_start = v2_partial.find('def get_feature_columns')
updated_get_feature_cols_end = v2_partial.find('def cast_categoricals_inplace', updated_get_feature_cols_start)
updated_get_feature_cols = v2_partial[updated_get_feature_cols_start:updated_get_feature_cols_end]

v2_content = v2_content[:get_feature_cols_start] + updated_get_feature_cols + v2_content[get_feature_cols_end:]

# Update main() to call create_m5_engineered_features after loading data
# Find where df is loaded and add feature engineering call
load_data_pos = v2_content.find('    # Load data from BigQuery\n    df = load_data_from_bigquery()')
if load_data_pos != -1:
    insert_pos = v2_content.find('\n    # Verify temporal features', load_data_pos)
    v2_content = v2_content[:insert_pos] + '\n    \n    # Create m5 engineered features\n    df = create_m5_engineered_features(df)' + v2_content[insert_pos:]

# Update SMOTE to use m5's sampling_strategy=0.1
v2_content = v2_content.replace(
    'sampler = SMOTE(random_state=seed, k_neighbors=min(5, (y_train == 1).sum() - 1))',
    'sampler = SMOTE(sampling_strategy=0.1, random_state=seed, k_neighbors=min(5, (y_train == 1).sum() - 1))'
)
v2_content = v2_content.replace(
    'sampler = SMOTE(random_state=seed, k_neighbors=min(5, (y_all == 1).sum() - 1))',
    'sampler = SMOTE(sampling_strategy=0.1, random_state=seed, k_neighbors=min(5, (y_all == 1).sum() - 1))'
)

# Write the complete V2 script
with open('unit_4_train_model_v2.py', 'w', encoding='utf-8') as f:
    f.write(v2_content)

print("Created unit_4_train_model_v2.py successfully!")

