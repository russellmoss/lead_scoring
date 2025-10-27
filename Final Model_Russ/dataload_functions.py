import simple_salesforce
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def create_sf_client():
    """Create a new Salesforce client"""
    base = os.getenv('INSTANCE_URL')
    username = os.getenv('USERNAME')
    password = os.getenv('PASSWORD')
    security_token = os.getenv('SECURITY_TOKEN')
    
    return simple_salesforce.Salesforce(
        username=username,
        password=password,
        security_token=security_token,
        instance_url=base
    )

# Initialize once, but through a function call
sf_client = create_sf_client()

def query_salesforce(query, sf_client=sf_client):
    """
    Connects to Salesforce using simple_salesforce and executes the provided query.
    
    Args:
        query: The SOQL query string.
        sf_client: Salesforce client (defaults to module-level client)
    
    Returns:
        A pandas DataFrame containing the query results.
    """
    results = sf_client.query_all(query)
    df = pd.DataFrame(results['records'])
    return df

## Merge Data with analysis
def analyze_merge_operations(sf, dd_rep, dd_firm, verbosity='high'):
    """
    Perform merge operations and generate a detailed analysis report
    
    Parameters:
    -----------
    sf : DataFrame - Salesforce data
    dd_rep : DataFrame - Representative data
    dd_firm : DataFrame - Firm data
    verbosity : str - 'none', 'low', or 'high' (default: 'high')
        - 'none': No output, just return results
        - 'low': Essential statistics only
        - 'high': Full detailed report
    
    Returns:
    --------
    tuple : (data_sf_rep, data_sf_rep_firm, data_rep_firm, report_dict)
    """
    
    # Helper function for conditional printing
    def vprint(message, level='high'):
        """Print based on verbosity level"""
        if verbosity == 'none':
            return
        elif verbosity == 'low' and level == 'high':
            return
        else:
            print(message)
    
    vprint("="*80, 'low')
    vprint("MERGE OPERATIONS ANALYSIS REPORT", 'low')
    vprint("="*80, 'low')
    
    # Store initial row counts
    initial_counts = {
        'sf': len(sf),
        'dd_rep': len(dd_rep),
        'dd_firm': len(dd_firm)
    }
    
    vprint("\n1. INITIAL DATASET SIZES:", 'low')
    vprint("-"*40, 'low')
    vprint(f"   Salesforce (sf):         {initial_counts['sf']:,} rows", 'low')
    vprint(f"   Representatives (dd_rep): {initial_counts['dd_rep']:,} rows", 'high')
    vprint(f"   Firms (dd_firm):         {initial_counts['dd_firm']:,} rows", 'high')
    
    # ============ MERGE 1: SF + REP ============
    vprint("\n2. MERGE 1: Salesforce + Representatives", 'high')
    vprint("-"*40, 'high')
    vprint(f"   Join Keys: sf['FA_CRD__c'] <-> dd_rep['RepCRD']", 'high')
    vprint(f"   Join Type: OUTER", 'high')
    
    data_sf_rep = pd.merge(
        sf, 
        dd_rep, 
        left_on="FA_CRD__c", 
        right_on="RepCRD", 
        how="outer", 
        indicator='_merge_sf_rep', 
        suffixes=('_sf', '_rep')
    )
    
    merge1_stats = data_sf_rep['_merge_sf_rep'].value_counts()
    
    vprint(f"\n   Result: {len(data_sf_rep):,} total rows", 'high')
    vprint("\n   Merge Breakdown:", 'high')
    for category in ['both', 'left_only', 'right_only']:
        count = merge1_stats.get(category, 0)
        pct = (count / len(data_sf_rep)) * 100
        
        if category == 'both':
            vprint(f"     • Matched records:           {count:,} ({pct:.1f}%)", 'high')
        elif category == 'left_only':
            vprint(f"     • SF records without Rep:    {count:,} ({pct:.1f}%)", 'high')
        else:
            vprint(f"     • Rep records without SF:    {count:,} ({pct:.1f}%)", 'high')
    
    # Salesforce-based success rate
    sf_matched_count = merge1_stats.get('both', 0)
    sf_unmatched_count = merge1_stats.get('left_only', 0)
    sf_total_in_merge = sf_matched_count + sf_unmatched_count
    sf_match_rate = (sf_matched_count / initial_counts['sf']) * 100 if initial_counts['sf'] > 0 else 0
    
    vprint(f"\n   📊 Salesforce Match Rate:", 'low')
    vprint(f"     • {sf_matched_count:,} of {initial_counts['sf']:,} SF records matched", 'low')
    vprint(f"     • Success Rate: {sf_match_rate:.1f}%", 'low')
    vprint(f"     • Unmatched SF records: {sf_unmatched_count:,} ({(sf_unmatched_count/initial_counts['sf']*100):.1f}%)", 'high')
    
    # Check for duplicate join keys
    if 'FA_CRD__c' in sf.columns:
        sf_duplicates = sf['FA_CRD__c'].duplicated().sum()
        if sf_duplicates > 0:
            vprint(f"\n   ⚠️  Warning: {sf_duplicates} duplicate FA_CRD__c values in SF data", 'high')
    
    if 'RepCRD' in dd_rep.columns:
        rep_duplicates = dd_rep['RepCRD'].duplicated().sum()
        if rep_duplicates > 0:
            vprint(f"   ⚠️  Warning: {rep_duplicates} duplicate RepCRD values in Rep data", 'high')
    
    # ============ MERGE 2: (SF+REP) + FIRM ============
    vprint("\n3. MERGE 2: (Salesforce + Representatives) + Firms", 'high')
    vprint("-"*40, 'high')
    vprint(f"   Join Keys: RIAFirmCRD (from both datasets)", 'high')
    vprint(f"   Join Type: OUTER", 'high')
    
    data_sf_rep_firm = pd.merge(
        data_sf_rep, 
        dd_firm, 
        on="RIAFirmCRD", 
        how="outer", 
        indicator='_merge_sf_rep_firm', 
        suffixes=('_merge1', '_firm')
    )
    
    merge2_stats = data_sf_rep_firm['_merge_sf_rep_firm'].value_counts()
    
    vprint(f"\n   Result: {len(data_sf_rep_firm):,} total rows", 'high')
    vprint("\n   Merge Breakdown:", 'high')
    for category in ['both', 'left_only', 'right_only']:
        count = merge2_stats.get(category, 0)
        pct = (count / len(data_sf_rep_firm)) * 100
        
        if category == 'both':
            vprint(f"     • Matched records:              {count:,} ({pct:.1f}%)", 'high')
        elif category == 'left_only':
            vprint(f"     • SF+Rep records without Firm:  {count:,} ({pct:.1f}%)", 'high')
        else:
            vprint(f"     • Firm records without SF+Rep:  {count:,} ({pct:.1f}%)", 'high')
    
    # Calculate Salesforce-based firm match rate
    # Count SF records that have both Rep AND Firm matches
    sf_with_rep_and_firm = len(data_sf_rep_firm[
        (data_sf_rep_firm['_merge_sf_rep'] == 'both') & 
        (data_sf_rep_firm['_merge_sf_rep_firm'] == 'both')
    ])
    sf_with_rep_only = len(data_sf_rep_firm[
        (data_sf_rep_firm['_merge_sf_rep'] == 'both') & 
        (data_sf_rep_firm['_merge_sf_rep_firm'] == 'left_only')
    ])
    sf_no_matches = len(data_sf_rep_firm[
        data_sf_rep_firm['_merge_sf_rep'] == 'left_only'
    ])
    
    vprint(f"\n   📊 Salesforce-based Firm Match Analysis:", 'low')
    vprint(f"     • SF records with Rep AND Firm: {sf_with_rep_and_firm:,} ({(sf_with_rep_and_firm/initial_counts['sf']*100):.1f}%)", 'low')
    vprint(f"     • SF records with Rep only:     {sf_with_rep_only:,} ({(sf_with_rep_only/initial_counts['sf']*100):.1f}%)", 'high')
    vprint(f"     • SF records with no matches:   {sf_no_matches:,} ({(sf_no_matches/initial_counts['sf']*100):.1f}%)", 'low')
    
    # ============ MERGE 3: REP + FIRM ============
    vprint("\n4. MERGE 3: Representatives + Firms", 'high')
    vprint("-"*40, 'high')
    vprint(f"   Join Keys: RIAFirmCRD (from both datasets)", 'high')
    vprint(f"   Join Type: OUTER", 'high')
    
    data_rep_firm = pd.merge(
        dd_rep, 
        dd_firm, 
        on="RIAFirmCRD", 
        how="outer", 
        indicator='_merge_rep_firm', 
        suffixes=('_merge1', '_firm')
    )
    
    merge3_stats = data_rep_firm['_merge_rep_firm'].value_counts()
    
    vprint(f"\n   Result: {len(data_rep_firm):,} total rows", 'high')
    vprint("\n   Merge Breakdown:", 'high')
    for category in ['both', 'left_only', 'right_only']:
        count = merge3_stats.get(category, 0)
        pct = (count / len(data_rep_firm)) * 100
        
        if category == 'both':
            vprint(f"     • Matched records:           {count:,} ({pct:.1f}%)", 'high')
        elif category == 'left_only':
            vprint(f"     • Rep records without Firm:  {count:,} ({pct:.1f}%)", 'high')
        else:
            vprint(f"     • Firm records without Rep:  {count:,} ({pct:.1f}%)", 'high')
    
    # ============ SUMMARY STATISTICS ============
    vprint("\n5. SUMMARY STATISTICS", 'high')
    vprint("="*80, 'high')
    
    vprint("\n   Row Count Progression:", 'high')
    vprint(f"     • Initial total rows:     {sum(initial_counts.values()):,}", 'high')
    vprint(f"     • After Merge 1 (SF+Rep): {len(data_sf_rep):,}", 'high')
    vprint(f"     • After Merge 2 (All):    {len(data_sf_rep_firm):,}", 'high')
    vprint(f"     • Rep+Firm merge:         {len(data_rep_firm):,}", 'high')
    
    # Calculate success rates (original method)
    vprint("\n   Match Success Rates (% of merge result):", 'high')
    if len(data_sf_rep) > 0:
        merge1_success = (merge1_stats.get('both', 0) / len(data_sf_rep)) * 100
        vprint(f"     • Merge 1 (SF+Rep):       {merge1_success:.1f}% matched", 'high')
    
    if len(data_sf_rep_firm) > 0:
        merge2_success = (merge2_stats.get('both', 0) / len(data_sf_rep_firm)) * 100
        vprint(f"     • Merge 2 (SF+Rep+Firm):  {merge2_success:.1f}% matched", 'high')
    
    if len(data_rep_firm) > 0:
        merge3_success = (merge3_stats.get('both', 0) / len(data_rep_firm)) * 100
        vprint(f"     • Merge 3 (Rep+Firm):     {merge3_success:.1f}% matched", 'high')
    
    # NEW: Salesforce-centric success summary
    vprint("\n   📊 SALESFORCE-CENTRIC SUCCESS SUMMARY:", 'low')
    vprint("   " + "-"*40, 'low')
    vprint(f"     Total Salesforce Records: {initial_counts['sf']:,}", 'low')
    vprint(f"     ├─ Matched with Rep:      {sf_matched_count:,} ({sf_match_rate:.1f}%)", 'low')
    vprint(f"     ├─ Matched with Rep+Firm: {sf_with_rep_and_firm:,} ({(sf_with_rep_and_firm/initial_counts['sf']*100):.1f}%)", 'low')
    vprint(f"     └─ No matches at all:     {sf_no_matches:,} ({(sf_no_matches/initial_counts['sf']*100):.1f}%)", 'low')
    
    # ============ DATA QUALITY CHECKS ============
    vprint("\n6. DATA QUALITY ANALYSIS", 'high')
    vprint("-"*40, 'high')
    
    # Check for null key values
    null_checks = []
    if 'FA_CRD__c' in sf.columns:
        null_count = sf['FA_CRD__c'].isna().sum()
        if null_count > 0:
            null_checks.append(f"   • SF: {null_count:,} null FA_CRD__c values ({(null_count/len(sf)*100):.1f}% of SF)")
    
    if 'RepCRD' in dd_rep.columns:
        null_count = dd_rep['RepCRD'].isna().sum()
        if null_count > 0:
            null_checks.append(f"   • Rep: {null_count:,} null RepCRD values")
    
    if 'RIAFirmCRD' in dd_rep.columns:
        null_count = dd_rep['RIAFirmCRD'].isna().sum()
        if null_count > 0:
            null_checks.append(f"   • Rep: {null_count:,} null RIAFirmCRD values")
    
    if 'RIAFirmCRD' in dd_firm.columns:
        null_count = dd_firm['RIAFirmCRD'].isna().sum()
        if null_count > 0:
            null_checks.append(f"   • Firm: {null_count:,} null RIAFirmCRD values")
    
    if null_checks:
        vprint("   Null Values in Join Keys:", 'high')
        for check in null_checks:
            vprint(check, 'high')
    else:
        vprint("   ✓ No null values found in join keys", 'high')
    
    # ============ CREATE DETAILED REPORT DICTIONARY ============
    report = {
        'initial_counts': initial_counts,
        'merge1_stats': {
            'total_rows': len(data_sf_rep),
            'matched': merge1_stats.get('both', 0),
            'sf_only': merge1_stats.get('left_only', 0),
            'rep_only': merge1_stats.get('right_only', 0),
            'match_rate': (merge1_stats.get('both', 0) / len(data_sf_rep) * 100) if len(data_sf_rep) > 0 else 0,
            'sf_based_match_rate': sf_match_rate,
            'sf_matched_count': sf_matched_count,
            'sf_unmatched_count': sf_unmatched_count
        },
        'merge2_stats': {
            'total_rows': len(data_sf_rep_firm),
            'matched': merge2_stats.get('both', 0),
            'sf_rep_only': merge2_stats.get('left_only', 0),
            'firm_only': merge2_stats.get('right_only', 0),
            'match_rate': (merge2_stats.get('both', 0) / len(data_sf_rep_firm) * 100) if len(data_sf_rep_firm) > 0 else 0,
            'sf_with_rep_and_firm': sf_with_rep_and_firm,
            'sf_with_rep_only': sf_with_rep_only,
            'sf_no_matches': sf_no_matches,
            'sf_based_complete_match_rate': (sf_with_rep_and_firm/initial_counts['sf']*100) if initial_counts['sf'] > 0 else 0
        },
        'merge3_stats': {
            'total_rows': len(data_rep_firm),
            'matched': merge3_stats.get('both', 0),
            'rep_only': merge3_stats.get('left_only', 0),
            'firm_only': merge3_stats.get('right_only', 0),
            'match_rate': (merge3_stats.get('both', 0) / len(data_rep_firm) * 100) if len(data_rep_firm) > 0 else 0
        },
        'salesforce_summary': {
            'total_records': initial_counts['sf'],
            'matched_with_rep': sf_matched_count,
            'matched_with_rep_pct': sf_match_rate,
            'matched_with_both': sf_with_rep_and_firm,
            'matched_with_both_pct': (sf_with_rep_and_firm/initial_counts['sf']*100) if initial_counts['sf'] > 0 else 0,
            'no_matches': sf_no_matches,
            'no_matches_pct': (sf_no_matches/initial_counts['sf']*100) if initial_counts['sf'] > 0 else 0
        }
    }
    
    vprint("\n" + "="*80, 'low')
    vprint("ANALYSIS COMPLETE", 'low')
    vprint("="*80, 'low')
    
    return data_sf_rep, data_sf_rep_firm, data_rep_firm, report

def create_discovery_data_pkl(debug=True):
    """
    Reads all CSV files from raw_discovery_data directory,
    concatenates them with proper type handling, and saves as pickle.
    
    Parameters:
    -----------
    debug : bool, default=True
        If True, prints detailed logging information.
        If False, suppresses all log outputs.
    
    Returns:
    --------
    pd.DataFrame : The concatenated discovery data
    """
    
    def log(message, force=False):
        """Helper function to conditionally print messages"""
        if debug or force:
            print(message)
    
    # Get list of all CSV files in raw_discovery_data directory
    csv_files = [f for f in os.listdir('data/raw_discovery_data') if f.endswith('.csv')]
    
    log(f"Found {len(csv_files)} CSV files to process")
    
    # Initialize empty list to store dataframes
    dfs = []
    
    # Read and append each CSV file with type inference
    for i, file in enumerate(csv_files, 1):
        log(f"Reading file {i}/{len(csv_files)}: {file}")
        
        # Read CSV with low_memory=False to allow pandas to infer types properly
        df = pd.read_csv(
            os.path.join('data/raw_discovery_data', file),
            low_memory=False,  # This allows pandas to scan entire columns for type inference
            na_values=['', 'NA', 'N/A', 'null', 'NULL', 'None'],  # Standardize NA values
            keep_default_na=True
        )
        
        # Store the dataframe
        dfs.append(df)
        log(f"  - Shape: {df.shape}")
    
    # Before concatenating, let's check and align data types
    log("\nAligning data types across dataframes...")
    
    # Get all unique columns across all dataframes
    all_columns = set()
    for df in dfs:
        all_columns.update(df.columns)
    
    log(f"Total unique columns across all files: {len(all_columns)}")
    
    # Identify common columns and their types
    column_types = {}
    for col in all_columns:
        types_for_col = []
        for df in dfs:
            if col in df.columns:
                # Get the inferred type for this column in this dataframe
                dtype = df[col].dtype
                types_for_col.append(str(dtype))
        
        # Determine the most appropriate type for this column
        unique_types = set(types_for_col)
        
        if len(unique_types) > 1:
            log(f"  Column '{col}' has mixed types: {unique_types}")
            
            # Decide on the best common type
            if 'object' in unique_types or any('str' in t for t in unique_types):
                # If any df has it as object/string, use object
                column_types[col] = 'object'
            elif any('float' in t for t in unique_types):
                # If any has float, use float (to handle NaN values)
                column_types[col] = 'float64'
            elif any('int' in t for t in unique_types):
                # If all are integers, use Int64 (nullable integer)
                column_types[col] = 'Int64'
            else:
                # Default to object for safety
                column_types[col] = 'object'
        else:
            # All dataframes have the same type for this column
            column_types[col] = unique_types.pop() if unique_types else 'object'
    
    # Apply consistent types to all dataframes before concatenation
    log("\nApplying consistent data types...")
    for i, df in enumerate(dfs):
        for col in df.columns:
            target_type = column_types.get(col, 'object')
            
            try:
                if target_type == 'float64':
                    # Convert to numeric, coercing errors to NaN
                    dfs[i][col] = pd.to_numeric(df[col], errors='coerce')
                elif target_type == 'Int64':
                    # Convert to nullable integer
                    dfs[i][col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                elif target_type == 'object':
                    # Keep as object/string
                    dfs[i][col] = df[col].astype('object')
                else:
                    # Keep original type
                    pass
            except Exception as e:
                log(f"    Warning: Could not convert column '{col}' to {target_type}: {e}")
                # Keep as object type if conversion fails
                dfs[i][col] = df[col].astype('object')
    
    # Concatenate all dataframes
    log("\nConcatenating all dataframes...")
    discovery_data = pd.concat(dfs, ignore_index=True, sort=False)
    discovery_data = discovery_data.drop_duplicates()
    
    log(f"\nFinal concatenated shape: {discovery_data.shape}")
    
    # Display data type summary
    if debug:
        log("\nData types summary:")
        type_counts = discovery_data.dtypes.value_counts()
        for dtype, count in type_counts.items():
            log(f"  {dtype}: {count} columns")
    
    # Check for any remaining issues
    if debug:
        log("\nChecking for potential issues...")
        
        # Check for columns with high percentage of NaN values
        nan_percentages = (discovery_data.isna().sum() / len(discovery_data)) * 100
        high_nan_cols = nan_percentages[nan_percentages > 90].sort_values(ascending=False)
        
        if not high_nan_cols.empty:
            log(f"\nColumns with >90% missing values ({len(high_nan_cols)} columns):")
            for col, pct in high_nan_cols.head(10).items():
                log(f"  - {col}: {pct:.1f}% missing")
    
    # Save concatenated data
    output_path = 'data/discovery_data.pkl'
    discovery_data.to_pickle(output_path)
    log(f"\nData successfully saved to {output_path}", force=True)  # Always show save confirmation
    
    # Also save a CSV backup with proper encoding
    csv_backup_path = 'data/discovery_data_backup.csv'
    discovery_data.to_csv(csv_backup_path, index=False, encoding='utf-8')
    log(f"CSV backup saved to {csv_backup_path}")
    
    return discovery_data