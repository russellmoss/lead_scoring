"""
linkedin_dna_analysis.py
------------------------
Reverse-engineers the success of the SGA's self-sourced leads.
"""
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project='savvy-gtm-analytics', location='northamerica-northeast2')

print("🧬 Sequencing the DNA of LinkedIn Success...")

query = """
SELECT 
    l.LeadSource,
    l.IsConverted,
    f.industry_tenure_months,
    f.num_prior_firms,
    f.current_firm_tenure_months,
    f.firm_net_change_12mo,
    
    -- Derived Signals
    CASE WHEN f.current_firm_tenure_months BETWEEN 12 AND 24 THEN 1 ELSE 0 END as in_danger_zone,
    CASE WHEN f.firm_net_change_12mo < -5 THEN 1 ELSE 0 END as is_bleeding_firm,
    CASE WHEN f.industry_tenure_months >= 120 THEN 1 ELSE 0 END as is_veteran

FROM `savvy-gtm-analytics.ml_features.lead_scoring_features` f
JOIN `savvy-gtm-analytics.SavvyGTMData.Lead` l ON f.lead_id = l.Id
WHERE l.LeadSource IN ('LinkedIn (Self Sourced)', 'Provided Lead List')
  AND l.CreatedDate >= '2024-01-01'
"""

df = client.query(query).to_dataframe()

# Split into two groups
linkedin = df[df['LeadSource'] == 'LinkedIn (Self Sourced)']
provided = df[df['LeadSource'] == 'Provided Lead List']

print(f"\n📊 DATASET SIZE:")
print(f"   - LinkedIn Leads: {len(linkedin):,} (Avg Conv: {linkedin['IsConverted'].mean():.2%})")
print(f"   - Provided Leads: {len(provided):,} (Avg Conv: {provided['IsConverted'].mean():.2%})")

print("\n🧐 PROFILE COMPARISON (Who are they targeting?):")
print(f"{'Feature':<25} | {'LinkedIn (SGA)':<15} | {'Provided List':<15} | {'Diff'}")
print("-" * 70)

metrics = {
    'Avg Industry Tenure (Mo)': 'industry_tenure_months',
    'Avg Prior Firms': 'num_prior_firms',
    'Avg Current Tenure (Mo)': 'current_firm_tenure_months',
    'Avg Firm Net Change': 'firm_net_change_12mo',
    '% Veterans (>10yr)': 'is_veteran',
    '% In Danger Zone': 'in_danger_zone',
    '% At Bleeding Firm': 'is_bleeding_firm'
}

for label, col in metrics.items():
    val_li = linkedin[col].mean()
    val_prov = provided[col].mean()
    
    # Format properly
    if '%' in label:
        v_li_str = f"{val_li:.1%}"
        v_prov_str = f"{val_prov:.1%}"
    else:
        v_li_str = f"{val_li:.1f}"
        v_prov_str = f"{val_prov:.1f}"
        
    print(f"{label:<25} | {v_li_str:<15} | {v_prov_str:<15} | {val_li - val_prov:+.1f}")

print("\n🏆 THE 'LINKEDIN WINNER' PROFILE (Converted vs. Not):")
winners = linkedin[linkedin['IsConverted'] == True]
losers = linkedin[linkedin['IsConverted'] == False]

print(f"   - Winners are usually VETERANS: {winners['is_veteran'].mean():.1%} vs {losers['is_veteran'].mean():.1%}")
print(f"   - Winners are in DANGER ZONE:   {winners['in_danger_zone'].mean():.1%} vs {losers['in_danger_zone'].mean():.1%}")
print(f"   - Winners are at BLEEDING FIRMS: {winners['is_bleeding_firm'].mean():.1%} vs {losers['is_bleeding_firm'].mean():.1%}")