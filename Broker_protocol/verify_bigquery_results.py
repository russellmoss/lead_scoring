"""Verify BigQuery results after automation run."""
from google.cloud import bigquery
import config

def verify_results():
    """Run verification queries."""
    client = bigquery.Client(project=config.GCP_PROJECT_ID)
    
    print("=" * 80)
    print("BIGQUERY VERIFICATION")
    print("=" * 80)
    
    # A) Match quality view
    print("\n1. Match Quality View:")
    print("-" * 80)
    query_a = f"""
    SELECT * 
    FROM `{config.TABLE_SCRAPE_LOG.replace('broker_protocol_scrape_log', 'broker_protocol_match_quality')}`
    ORDER BY scrape_timestamp DESC
    LIMIT 1
    """
    try:
        result_a = client.query(query_a).to_dataframe()
        if len(result_a) > 0:
            print(result_a.to_string(index=False))
        else:
            print("  No match quality data found")
    except Exception as e:
        print(f"  Error: {e}")
        print("  (Match quality view may not exist yet)")
    
    # B) Unmatched count
    print("\n2. Unmatched Firms Count:")
    print("-" * 80)
    query_b = f"""
    SELECT COUNT(*) AS unmatched
    FROM `{config.TABLE_MEMBERS}`
    WHERE firm_crd_id IS NULL
    """
    result_b = client.query(query_b).to_dataframe()
    unmatched = result_b['unmatched'].iloc[0]
    total_query = f"SELECT COUNT(*) AS total FROM `{config.TABLE_MEMBERS}`"
    total_result = client.query(total_query).to_dataframe()
    total = total_result['total'].iloc[0]
    match_rate = ((total - unmatched) / total * 100) if total > 0 else 0
    
    print(f"  Unmatched: {unmatched}")
    print(f"  Total: {total}")
    print(f"  Match Rate: {match_rate:.2f}%")
    
    if unmatched == 0:
        print("  [SUCCESS] 100% match rate!")
    elif unmatched / total <= 0.01:
        print(f"  [SUCCESS] Match rate >= 99% (only {unmatched} unmatched)")
    else:
        print(f"  [WARNING] Match rate below 99% ({unmatched} unmatched)")
    
    # C) Latest scrape log
    print("\n3. Latest Scrape Log:")
    print("-" * 80)
    query_c = f"""
    SELECT scrape_timestamp, firms_parsed, firms_matched, firms_needing_review
    FROM `{config.TABLE_SCRAPE_LOG}`
    ORDER BY scrape_timestamp DESC
    LIMIT 1
    """
    result_c = client.query(query_c).to_dataframe()
    if len(result_c) > 0:
        print(result_c.to_string(index=False))
    else:
        print("  No scrape log entries found")
    
    # D) Sample of unmatched firms (if any)
    if unmatched > 0:
        print(f"\n4. Sample of Unmatched Firms (showing up to 10):")
        print("-" * 80)
        query_d = f"""
        SELECT broker_protocol_firm_name, match_method, match_confidence, needs_manual_review
        FROM `{config.TABLE_MEMBERS}`
        WHERE firm_crd_id IS NULL
        ORDER BY last_updated DESC
        LIMIT 10
        """
        result_d = client.query(query_d).to_dataframe()
        print(result_d.to_string(index=False))
    
    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    verify_results()

