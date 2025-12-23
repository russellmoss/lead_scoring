"""
Broker Protocol Excel Parser
Parses Excel file from JSHeld website and extracts firm information.
"""

import pandas as pd
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from dateutil import parser as date_parser
import config


def normalize_firm_name(name):
    """Normalize firm name by removing extra whitespace"""
    if pd.isna(name):
        return None
    return ' '.join(str(name).split())


def parse_firm_name(raw_name):
    """
    Parse firm name, extracting f/k/a (formerly known as) and d/b/a (doing business as) names.
    
    Returns:
        dict with keys: firm_name, former_names, dbas, has_name_change
    """
    if pd.isna(raw_name):
        return {
            'firm_name': None,
            'former_names': None,
            'dbas': None,
            'has_name_change': False
        }
    
    name_str = str(raw_name).strip()
    original_name = name_str
    
    # Extract f/k/a (formerly known as)
    former_names = []
    fka_patterns = [
        r'\s+f/k/a\s+(.+?)(?:\s+\(|$)',
        r'\s+formerly\s+known\s+as\s+(.+?)(?:\s+\(|$)',
        r'\s+f\.k\.a\.\s+(.+?)(?:\s+\(|$)',
        r'\s+\(f/k/a\s+(.+?)\)',
    ]
    
    for pattern in fka_patterns:
        matches = re.findall(pattern, name_str, re.IGNORECASE)
        if matches:
            former_names.extend([m.strip() for m in matches])
            # Remove f/k/a from main name
            name_str = re.sub(pattern, '', name_str, flags=re.IGNORECASE)
    
    # Extract d/b/a (doing business as)
    dbas = []
    dba_patterns = [
        r'\s+d/b/a\s+(.+?)(?:\s+\(|$)',
        r'\s+doing\s+business\s+as\s+(.+?)(?:\s+\(|$)',
        r'\s+d\.b\.a\.\s+(.+?)(?:\s+\(|$)',
        r'\s+\(d/b/a\s+(.+?)\)',
    ]
    
    for pattern in dba_patterns:
        matches = re.findall(pattern, name_str, re.IGNORECASE)
        if matches:
            dbas.extend([m.strip() for m in matches])
            # Remove d/b/a from main name
            name_str = re.sub(pattern, '', name_str, flags=re.IGNORECASE)
    
    # Clean up main name
    firm_name = normalize_firm_name(name_str)
    
    # Remove trailing punctuation and clean
    firm_name = re.sub(r'[,\s]+$', '', firm_name)
    
    return {
        'firm_name': firm_name,
        'former_names': ', '.join(former_names) if former_names else None,
        'dbas': ', '.join(dbas) if dbas else None,
        'has_name_change': len(former_names) > 0 or len(dbas) > 0,
        'firm_name_raw': original_name
    }


def extract_dates(date_notes):
    """
    Extract join and withdrawal dates from date notes field.
    
    Returns:
        dict with keys: date_joined, date_withdrawn, is_current_member, date_notes_cleaned
    """
    if pd.isna(date_notes):
        return {
            'date_joined': None,
            'date_withdrawn': None,
            'is_current_member': True,
            'date_notes_cleaned': None,
            'date_notes_raw': None
        }
    
    date_str = str(date_notes).strip()
    original_notes = date_str
    
    date_joined = None
    date_withdrawn = None
    is_current_member = True
    
    # Common date patterns
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # MM/DD/YYYY or MM-DD-YYYY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',   # YYYY/MM/DD or YYYY-MM-DD
        r'(\w+\s+\d{1,2},?\s+\d{4})',       # Month DD, YYYY
        r'(\d{1,2}\s+\w+\s+\d{4})',         # DD Month YYYY
    ]
    
    # Look for "joined" or "effective" dates
    joined_patterns = [
        r'joined[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'effective[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'since[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    # Look for "withdrawn" or "withdrawal" dates
    withdrawn_patterns = [
        r'withdrawn[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'withdrawal[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'withdrew[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    # Try to extract join date
    for pattern in joined_patterns:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                date_joined = date_parser.parse(match.group(1), fuzzy=True).date()
                break
            except:
                pass
    
    # Try to extract withdrawal date
    for pattern in withdrawn_patterns:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                date_withdrawn = date_parser.parse(match.group(1), fuzzy=True).date()
                is_current_member = False
                break
            except:
                pass
    
    # If no specific patterns found, try to parse first date as join date
    if date_joined is None:
        for pattern in date_patterns:
            matches = re.findall(pattern, date_str)
            if matches:
                try:
                    date_joined = date_parser.parse(matches[0], fuzzy=True).date()
                    break
                except:
                    pass
    
    # Clean up notes (remove parsed dates)
    date_notes_cleaned = date_str
    
    return {
        'date_joined': date_joined,
        'date_withdrawn': date_withdrawn,
        'is_current_member': is_current_member,
        'date_notes_cleaned': date_notes_cleaned,
        'date_notes_raw': original_notes
    }


def parse_broker_protocol_excel(excel_path, verbose=False):
    """
    Parse Broker Protocol Excel file.
    
    Args:
        excel_path: Path to Excel file
        verbose: Print detailed output
        
    Returns:
        DataFrame with parsed firm data
    """
    if verbose:
        print(f"Reading Excel file: {excel_path}")
    
    # Read Excel - header is typically at row 4 (0-indexed: row 4)
    # Try header=4 first, fall back to header=2 if that doesn't work
    try:
        df = pd.read_excel(excel_path, header=4)
        # If we get unnamed columns, try header=2
        if any('Unnamed' in str(col) for col in df.columns):
            df = pd.read_excel(excel_path, header=2)
    except Exception as e:
        # Fallback to header=2
        try:
            df = pd.read_excel(excel_path, header=2)
        except Exception as e2:
            print(f"Error reading Excel file: {e2}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error reading Excel file: {e}", file=sys.stderr)
        sys.exit(1)
    
    if verbose:
        print(f"Found {len(df)} rows")
        print(f"Columns: {df.columns.tolist()}")
    
    # Expected column names (may vary)
    # Common variations: "Firm Name", "Member Firm", "Company Name", etc.
    firm_name_col = None
    date_col = None
    qualifications_col = None
    
    # Find firm name column
    for col in df.columns:
        col_lower = str(col).lower()
        if 'firm' in col_lower or 'company' in col_lower or 'name' in col_lower:
            if firm_name_col is None:
                firm_name_col = col
                break
    
    # Find date column
    for col in df.columns:
        col_lower = str(col).lower()
        if 'date' in col_lower or 'joined' in col_lower or 'effective' in col_lower:
            if date_col is None:
                date_col = col
                break
    
    # Find qualifications column
    for col in df.columns:
        col_lower = str(col).lower()
        if 'qualification' in col_lower or 'note' in col_lower or 'comment' in col_lower:
            if qualifications_col is None:
                qualifications_col = col
                break
    
    if firm_name_col is None:
        print("ERROR: Could not find firm name column", file=sys.stderr)
        print(f"Available columns: {df.columns.tolist()}", file=sys.stderr)
        sys.exit(1)
    
    if verbose:
        print(f"Using columns:")
        print(f"  Firm Name: {firm_name_col}")
        print(f"  Date: {date_col}")
        print(f"  Qualifications: {qualifications_col}")
    
    # Parse each row
    parsed_rows = []
    
    for idx, row in df.iterrows():
        if pd.isna(row.get(firm_name_col)):
            continue  # Skip rows with no firm name
        
        # Parse firm name
        name_info = parse_firm_name(row.get(firm_name_col))
        
        # Parse dates
        date_info = extract_dates(row.get(date_col) if date_col else None)
        
        # Combine into single row
        parsed_row = {
            'firm_name': name_info['firm_name'],
            'former_names': name_info['former_names'],
            'dbas': name_info['dbas'],
            'has_name_change': name_info['has_name_change'],
            'firm_name_raw': name_info['firm_name_raw'],
            'date_joined': date_info['date_joined'],
            'date_withdrawn': date_info['date_withdrawn'],
            'is_current_member': date_info['is_current_member'],
            'date_notes_cleaned': date_info['date_notes_cleaned'],
            'date_notes_raw': date_info['date_notes_raw'],
            'joinder_qualifications': str(row.get(qualifications_col)) if qualifications_col and pd.notna(row.get(qualifications_col)) else None,
            'scrape_timestamp': datetime.now()
        }
        
        parsed_rows.append(parsed_row)
    
    result_df = pd.DataFrame(parsed_rows)
    
    if verbose:
        print(f"\nParsed {len(result_df)} firms")
        print(f"Firms with join dates: {result_df['date_joined'].notna().sum()}")
        print(f"Current members: {result_df['is_current_member'].sum()}")
        print(f"Withdrawn members: {(~result_df['is_current_member']).sum()}")
    
    return result_df


def main():
    parser = argparse.ArgumentParser(description='Parse Broker Protocol Excel file')
    parser.add_argument('excel_file', help='Path to Excel file')
    parser.add_argument('-o', '--output', help='Output CSV path', 
                       default=str(config.get_parsed_csv_path()))
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--test', action='store_true', help='Test mode (print sample)')
    
    args = parser.parse_args()
    
    if not Path(args.excel_file).exists():
        print(f"ERROR: File not found: {args.excel_file}", file=sys.stderr)
        sys.exit(1)
    
    # Parse Excel
    df = parse_broker_protocol_excel(args.excel_file, verbose=args.verbose)
    
    if args.test:
        print("\n=== TEST MODE - Sample Output ===")
        print(df.head(10).to_string())
        print(f"\nTotal rows: {len(df)}")
    else:
        # Save to CSV
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"\n[SUCCESS] Saved {len(df)} firms to {output_path}")


if __name__ == '__main__':
    main()

