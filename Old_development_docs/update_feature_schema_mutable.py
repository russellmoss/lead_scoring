"""
Script to add is_mutable flags to config/v1_feature_schema.json
Based on Step 3.4 requirements: classify features as mutable (true) or stable (false)
"""
import json
from pathlib import Path

# Define stable features (is_mutable: false)
# These are features that don't change over time and are safe to use for all historical leads
STABLE_FEATURES = {
    # Personal identifiers and demographics
    "FirstName", "LastName", "Title", "Gender",
    
    # Geographic (stable)
    "Branch_State", "Branch_City", "Branch_ZipCode", "Branch_County",
    "Branch_Latitude", "Branch_Longitude",
    "Home_State", "Home_City", "Home_ZipCode", "Home_County",
    "Home_Latitude", "Home_Longitude",
    "Home_MetropolitanArea",
    "Home_MetropolitanArea_Chicago_Naperville_Elgin_IL_IN",
    "Home_MetropolitanArea_Dallas_Fort_Worth_Arlington_TX",
    "Home_MetropolitanArea_Los_Angeles_Long_Beach_Anaheim_CA",
    "Home_MetropolitanArea_Miami_Fort_Lauderdale_West_Palm_Beach_FL",
    "Home_MetropolitanArea_New_York_Newark_Jersey_City_NY_NJ",
    "MilesToWork",
    
    # Professional credentials (stable)
    "Has_CFP", "Has_CFA", "Has_CIMA", "Has_AIF",
    "Has_Series_7", "Has_Series_65", "Has_Series_66", "Has_Series_24",
    "Licenses", "Education",
    
    # Historical career data (stable - these are fixed historical facts)
    "DateBecameRep_NumberOfYears",
    "DateOfHireAtCurrentFirm_NumberOfYears",
    "Number_YearsPriorFirm1", "Number_YearsPriorFirm2",
    "Number_YearsPriorFirm3", "Number_YearsPriorFirm4",
    "Total_Prior_Firm_Years",
    "Number_Of_Prior_Firms",
    
    # Firm/Relationship identifiers (relatively stable)
    "Custodian1", "Custodian2", "Custodian3", "Custodian4", "Custodian5",
    "RIAFirmCRD", "RIAFirmName",
    "DuallyRegisteredBDRIARep", "IsPrimaryRIAFirm",
    "BreakawayRep", "KnownNonAdvisor",
    
    # Web presence (relatively stable)
    "SocialMedia_LinkedIn", "PersonalWebpage", "FirmWebsite",
    "Brochure_Keywords", "Notes", "CustomKeywords",
    "Email_BusinessType", "Email_PersonalType",
    
    # Regulatory (stable)
    "RegulatoryDisclosures",
    
    # Temporal features (will be added during Week 4 training)
    # Note: These aren't in the schema yet, but will be added
    # "Day_of_Contact", "Is_Weekend_Contact",
}

# Everything else is mutable (default to true)
# Mutable features include: AUM metrics, growth rates, client counts, asset allocations, etc.

def update_schema():
    schema_path = Path("config/v1_feature_schema.json")
    
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    
    updated_features = []
    for feature in schema["features"]:
        feature_name = feature["name"]
        is_mutable = feature_name not in STABLE_FEATURES
        feature["is_mutable"] = is_mutable
        updated_features.append(feature)
    
    schema["features"] = updated_features
    
    # Write back
    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    
    # Print summary
    mutable_count = sum(1 for f in updated_features if f["is_mutable"])
    stable_count = sum(1 for f in updated_features if not f["is_mutable"])
    
    print(f"Schema updated successfully!")
    print(f"Total features: {len(updated_features)}")
    print(f"Mutable (is_mutable: true): {mutable_count}")
    print(f"Stable (is_mutable: false): {stable_count}")
    print(f"\nStable features: {sorted([f['name'] for f in updated_features if not f['is_mutable']])}")
    
    return schema

if __name__ == "__main__":
    update_schema()

