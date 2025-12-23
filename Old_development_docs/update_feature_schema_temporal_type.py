#!/usr/bin/env python3
"""
Update feature schema to use temporal_type classification instead of is_mutable.
This script reclassifies features into: stable, calculable, mutable
"""

import json

# Read the current schema
with open('config/v1_feature_schema.json', 'r') as f:
    schema = json.load(f)

# Define tenure/calculable features - these can be recalculated point-in-time
calculable_features = {
    'DateBecameRep_NumberOfYears',
    'DateOfHireAtCurrentFirm_NumberOfYears',
    'Total_Prior_Firm_Years',
    'Number_YearsPriorFirm1',
    'Number_YearsPriorFirm2',
    'Number_YearsPriorFirm3',
    'Number_YearsPriorFirm4',
    'Number_Of_Prior_Firms'  # Historical count, can be recalculated
}

# Define stable features - these never change over time
stable_features = {
    # Demographics (never change)
    'FirstName', 'LastName', 'Gender', 'Education',
    
    # Geographic (stable)
    'Branch_State', 'Branch_City', 'Branch_County', 'Branch_ZipCode',
    'Branch_Latitude', 'Branch_Longitude',
    'Home_State', 'Home_City', 'Home_County', 'Home_ZipCode',
    'Home_Latitude', 'Home_Longitude',
    'Home_MetropolitanArea',
    'Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ',
    'Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA',
    'Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN',
    'Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX',
    'Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL',
    'MilesToWork',  # Geographic distance is stable
    
    # Professional identifiers (stable)
    'Title', 'SocialMedia_LinkedIn', 'PersonalWebpage', 'FirmWebsite',
    'Email_BusinessType', 'Email_PersonalType',
    'Brochure_Keywords', 'CustomKeywords', 'Notes',
    
    # Licenses/Credentials (stable - these don't change)
    'Has_Series_7', 'Has_Series_65', 'Has_Series_66', 'Has_Series_24',
    'Has_CFP', 'Has_CFA', 'Has_CIMA', 'Has_AIF',
    'Licenses', 'RegulatoryDisclosures',
    
    # Firm relationships (stable - these are historical facts)
    'RIAFirmCRD', 'RIAFirmName', 'RIAFirmCRD',
    'Custodian1', 'Custodian2', 'Custodian3', 'Custodian4', 'Custodian5',
    'IsPrimaryRIAFirm', 'DuallyRegisteredBDRIARep', 'BreakawayRep',
    'KnownNonAdvisor', 'Is_Known_Non_Advisor',
    
    # Multi-relationship flags (stable - historical fact)
    'Multi_RIA_Relationships',  # ⭐ m5's top feature - this is stable!
    'Multi_Firm_Associations',  # Historical count is stable
    
    # Number of associations (stable - historical fact)
    'NumberFirmAssociations',  # Historical count
    'NumberRIAFirmAssociations',  # Historical count
}

# Update each feature
stable_count = 0
calculable_count = 0
mutable_count = 0

for feature in schema['features']:
    feature_name = feature['name']
    
    # Remove old is_mutable key
    if 'is_mutable' in feature:
        del feature['is_mutable']
    
    # Classify feature
    if feature_name in calculable_features:
        feature['temporal_type'] = 'calculable'
        calculable_count += 1
    elif feature_name in stable_features:
        feature['temporal_type'] = 'stable'
        stable_count += 1
    else:
        # Default to mutable for everything else
        feature['temporal_type'] = 'mutable'
        mutable_count += 1

# Write updated schema
with open('config/v1_feature_schema.json', 'w') as f:
    json.dump(schema, f, indent=2)

print("Feature schema updated successfully!")
print(f"   - Stable features: {stable_count}")
print(f"   - Calculable features: {calculable_count}")
print(f"   - Mutable features: {mutable_count}")
print(f"   - Total features: {len(schema['features'])}")

