CREATE OR REPLACE TABLE `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` AS
        
        WITH 
        -- ========================================================================
        -- BASE: Target variable with right-censoring protection
        -- ========================================================================
        lead_base AS (
            SELECT
                l.Id as lead_id,
                SAFE_CAST(REGEXP_REPLACE(l.FA_CRD__c, r'[^0-9]', '') AS INT64) as advisor_crd,
                DATE(l.stage_entered_contacting__c) as contacted_date,
                
                -- PIT month for firm lookups (month BEFORE contact to ensure data availability)
                DATE_TRUNC(DATE_SUB(DATE(l.stage_entered_contacting__c), INTERVAL 1 MONTH), MONTH) as pit_month,
                
                -- Target variable with fixed analysis_date for training set stability
                -- CRITICAL: Use fixed analysis_date instead of CURRENT_DATE() to prevent training set drift
                -- Updated to 2025-12-31 to include 2025 data
                CASE
                    WHEN DATE_DIFF(DATE('2025-12-31'), DATE(l.stage_entered_contacting__c), DAY) < 30
                    THEN NULL  -- Right-censored (too young as of analysis_date)
                    WHEN l.Stage_Entered_Call_Scheduled__c IS NOT NULL
                         AND DATE_DIFF(DATE(l.Stage_Entered_Call_Scheduled__c), 
                                       DATE(l.stage_entered_contacting__c), DAY) <= 30
                    THEN 1  -- Positive: converted within window
                    ELSE 0  -- Negative: mature lead, never converted
                END as target,
                
                -- Lead metadata
                l.Company as company_name,
                l.LeadSource as lead_source
                
            FROM `savvy-gtm-analytics.SavvyGTMData.Lead` l
            WHERE l.stage_entered_contacting__c IS NOT NULL
                AND l.FA_CRD__c IS NOT NULL
                AND l.Company NOT LIKE '%Savvy%'
        ),
        
        -- ========================================================================
        -- VIRTUAL SNAPSHOT: Rep State at contacted_date (from employment_history)
        -- GAP-TOLERANT LOGIC: Use "Latest Record" instead of "Strict Interval"
        -- This recovers "Gap Victims" by using the most recent employment record
        -- that started on or before contacted_date, regardless of end date
        -- ========================================================================
        rep_state_pit AS (
            SELECT
                lb.lead_id,
                lb.advisor_crd,
                lb.contacted_date,
                
                -- Find the most recent employment record that started on or before contacted_date
                -- GAP-TOLERANT: We ignore end_date to recover leads in employment gaps
                eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID as firm_crd_at_contact,
                eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE as current_job_start_date,
                COALESCE(eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE, DATE('2025-12-31')) as current_job_end_date,
                
                -- Gap Indicator (for audit purposes)
                -- Positive value = advisor is in a gap (left firm before contact date)
                CASE 
                    WHEN eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL 
                         AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE < lb.contacted_date
                    THEN DATE_DIFF(lb.contacted_date, eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE, DAY)
                    ELSE 0 
                END as days_in_gap,
                
                -- Calculate current firm tenure as of contacted_date
                -- Note: For gap cases, this represents tenure at the last known firm
                DATE_DIFF(
                    lb.contacted_date,
                    eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE,
                    MONTH
                ) as current_firm_tenure_months,
                
                -- Calculate total industry tenure from all prior jobs
                -- Sum of all completed tenures before current job
                (SELECT 
                    COALESCE(SUM(
                        DATE_DIFF(
                            COALESCE(eh2.PREVIOUS_REGISTRATION_COMPANY_END_DATE, DATE('2025-12-31')),
                            eh2.PREVIOUS_REGISTRATION_COMPANY_START_DATE,
                            MONTH
                        )
                    ), 0)
                 FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh2
                 WHERE eh2.RIA_CONTACT_CRD_ID = lb.advisor_crd
                   AND eh2.PREVIOUS_REGISTRATION_COMPANY_START_DATE < eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE
                ) as industry_tenure_months,
                
                -- Count prior firms (all jobs before current)
                (SELECT COUNT(DISTINCT eh3.PREVIOUS_REGISTRATION_COMPANY_CRD_ID)
                 FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh3
                 WHERE eh3.RIA_CONTACT_CRD_ID = lb.advisor_crd
                   AND eh3.PREVIOUS_REGISTRATION_COMPANY_START_DATE < eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE
                ) as num_prior_firms
                
            FROM lead_base lb
            INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
                ON lb.advisor_crd = eh.RIA_CONTACT_CRD_ID
            WHERE 
                -- ONLY constraint: Job must have started on or before contact date
                -- We NO LONGER require end_date >= contacted_date (this recovers Gap Victims)
                eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= lb.contacted_date
            
            -- "Last Known Value" Logic: Take the most recent start date
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY lb.lead_id 
                ORDER BY eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
            ) = 1
        ),
        
        -- ========================================================================
        -- VIRTUAL SNAPSHOT: Firm State at contacted_date (from Firm_historicals)
        -- CRITICAL: Use pit_month (month BEFORE contacted_date) to ensure data availability
        -- Join on Firm_CRD AND Year/Month corresponding to pit_month
        -- If exact month match doesn't exist, use most recent prior month (fallback)
        -- ========================================================================
        -- Calculate rep count from employment history (PIT-safe)
        firm_rep_count_pit AS (
            SELECT
                rsp.firm_crd_at_contact,
                rsp.contacted_date,
                COUNT(DISTINCT eh.RIA_CONTACT_CRD_ID) as firm_rep_count_at_contact
            FROM rep_state_pit rsp
            INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
                ON rsp.firm_crd_at_contact = eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID
            WHERE eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= rsp.contacted_date
                AND (eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
                     OR eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= rsp.contacted_date)
            GROUP BY rsp.firm_crd_at_contact, rsp.contacted_date
        ),
        
        firm_state_pit AS (
            SELECT
                rsp.lead_id,
                rsp.firm_crd_at_contact,
                rsp.contacted_date,
                lb.pit_month,
                
                -- Join to Firm_historicals using pit_month (month before contacted_date)
                -- Use most recent Firm_historicals row with month <= pit_month
                fh.TOTAL_AUM as firm_aum_pit,
                -- Rep count calculated from employment history (PIT-safe)
                COALESCE(frc.firm_rep_count_at_contact, 0) as firm_rep_count_at_contact,
                -- Client wealth segmentation fields (if available in Firm_historicals)
                fh.AMT_OF_AUM_HIGH_NET_WORTH_INDIVIDUALS as firm_hnw_aum_pit,
                fh.TOTAL_ACCOUNTS as firm_total_accounts_pit,
                
                -- Calculate AUM growth (12 months prior from Firm_historicals)
                -- Get AUM from 12 months before pit_month
                fh_12mo.TOTAL_AUM as firm_aum_12mo_ago,
                
                -- AUM growth rate (12-month)
                CASE 
                    WHEN fh_12mo.TOTAL_AUM > 0
                    THEN (fh.TOTAL_AUM - fh_12mo.TOTAL_AUM) * 100.0 / fh_12mo.TOTAL_AUM
                    ELSE NULL
                END as aum_growth_12mo_pct
                
            FROM rep_state_pit rsp
            INNER JOIN lead_base lb ON rsp.lead_id = lb.lead_id
            -- Join to Firm_historicals for pit_month
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals` fh
                ON rsp.firm_crd_at_contact = fh.RIA_INVESTOR_CRD_ID
                AND EXTRACT(YEAR FROM lb.pit_month) = fh.YEAR
                AND EXTRACT(MONTH FROM lb.pit_month) = fh.MONTH
            -- Join to Firm_historicals for 12 months prior (for growth calculation)
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.Firm_historicals` fh_12mo
                ON rsp.firm_crd_at_contact = fh_12mo.RIA_INVESTOR_CRD_ID
                AND fh_12mo.YEAR = EXTRACT(YEAR FROM DATE_SUB(lb.pit_month, INTERVAL 12 MONTH))
                AND fh_12mo.MONTH = EXTRACT(MONTH FROM DATE_SUB(lb.pit_month, INTERVAL 12 MONTH))
            -- Join to rep count CTE
            LEFT JOIN firm_rep_count_pit frc
                ON rsp.firm_crd_at_contact = frc.firm_crd_at_contact
                AND rsp.contacted_date = frc.contacted_date
        ),
        
        -- ========================================================================
        -- ADVISOR: Features derived from employment history (Virtual Snapshot)
        -- ========================================================================
        advisor_features_virtual AS (
            SELECT
                rsp.lead_id,
                rsp.advisor_crd,
                rsp.contacted_date,
                rsp.industry_tenure_months,
                rsp.num_prior_firms,
                rsp.current_firm_tenure_months,
                rsp.firm_crd_at_contact,
                
                -- Calculate average tenure at prior firms (excluding current)
                (SELECT 
                    AVG(DATE_DIFF(
                        COALESCE(eh_prior.PREVIOUS_REGISTRATION_COMPANY_END_DATE, DATE('2025-12-31')),
                        eh_prior.PREVIOUS_REGISTRATION_COMPANY_START_DATE,
                        MONTH
                    ))
                 FROM `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh_prior
                 WHERE eh_prior.RIA_CONTACT_CRD_ID = rsp.advisor_crd
                   AND eh_prior.PREVIOUS_REGISTRATION_COMPANY_START_DATE < rsp.current_job_start_date
                   AND eh_prior.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
                   AND eh_prior.PREVIOUS_REGISTRATION_COMPANY_END_DATE < rsp.contacted_date
                ) as avg_prior_firm_tenure_months
                
            FROM rep_state_pit rsp
        ),
        
        -- ========================================================================
        -- ADVISOR: Additional employment history features (Virtual Snapshot)
        -- VALIDATED MOBILITY FEATURES: 3-year lookback and Restlessness logic
        -- Note: Primary advisor features come from rep_state_pit and advisor_features_virtual above
        -- This CTE adds calculated mobility features from employment history
        -- ========================================================================
        employment_features_supplement AS (
            SELECT
                lb.lead_id,
                lb.advisor_crd,
                lb.contacted_date,
                
                -- VALIDATED MOBILITY FEATURES (From Rep Mobility Doc)
                -- Key Predictor: 3-4x Lift for high mobility advisors
                
                -- 1. Recent Velocity (3-year lookback) - Count moves in last 36 months
                COUNTIF(
                    eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= DATE_SUB(lb.contacted_date, INTERVAL 36 MONTH)
                    AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE < lb.contacted_date
                ) as pit_moves_3yr,
                
                -- 2. Historical Pattern - Average tenure at all prior firms (excluding current)
                -- Only count completed tenures (those with end dates)
                AVG(
                    CASE 
                        WHEN eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
                             AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE < lb.contacted_date
                        THEN DATE_DIFF(
                            eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE,
                            eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE, 
                            MONTH
                        )
                        ELSE NULL
                    END
                ) as pit_avg_prior_tenure_months,
                
                -- Legacy: Job hopper indicator (3+ firms in 5 years) - kept for backward compatibility
                COUNTIF(
                    eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE >= DATE_SUB(lb.contacted_date, INTERVAL 5 YEAR)
                ) as firms_in_last_5_years
                
            FROM lead_base lb
            INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
                ON lb.advisor_crd = eh.RIA_CONTACT_CRD_ID
            WHERE eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE < lb.contacted_date
            GROUP BY lb.lead_id, lb.advisor_crd, lb.contacted_date
        ),
        
        -- ========================================================================
        -- MOBILITY DERIVED: Restlessness ratio calculation
        -- Logic: If current tenure > avg prior tenure, advisor might be "due" for a move
        -- ========================================================================
        mobility_derived AS (
            SELECT
                efs.lead_id,
                efs.pit_moves_3yr,
                efs.pit_avg_prior_tenure_months,
                avf.current_firm_tenure_months,
                
                -- 3. Restlessness Score (Ratio)
                -- High ratio (>1.0) = staying longer than usual = might be ready to move
                -- Low ratio (<1.0) = staying shorter than usual = might be settling in
                CASE 
                    WHEN efs.pit_avg_prior_tenure_months > 0 
                    THEN SAFE_DIVIDE(avf.current_firm_tenure_months, efs.pit_avg_prior_tenure_months)
                    ELSE 1.0  -- Default to 1.0 if no prior tenure data
                END as pit_restlessness_ratio,
                
                -- 4. Mobility Tier (Categorical - High Priority Signal)
                -- Validated: Advisors with 3+ moves in 3 years have 11% conversion vs 3% baseline
                CASE
                    WHEN efs.pit_moves_3yr >= 3 THEN 'Highly Mobile'  -- 11% conversion rate
                    WHEN efs.pit_moves_3yr = 2 THEN 'Mobile'
                    WHEN efs.pit_moves_3yr = 1 THEN 'Average'
                    WHEN efs.pit_moves_3yr = 0 AND avf.current_firm_tenure_months < 60 THEN 'Stable'
                    WHEN efs.pit_moves_3yr = 0 AND avf.current_firm_tenure_months >= 60 THEN 'Lifer'
                    ELSE 'Unknown'
                END as pit_mobility_tier
            FROM employment_features_supplement efs
            LEFT JOIN advisor_features_virtual avf
                ON efs.lead_id = avf.lead_id
        ),
        
        -- NOTE: firm_state_pit is defined above in Virtual Snapshot section
        -- It contains firm features from Firm_historicals using Year/Month matching
        
        -- ========================================================================
        -- SAFE LOCATION PROXIES: Replace raw geography with aggregated signals
        -- CRITICAL: No raw Metro, City, State, or Zip codes to prevent overfitting
        -- ========================================================================
        -- ========================================================================
        -- SAFE LOCATION PROXIES: Replace raw geography with aggregated signals
        -- CRITICAL: No raw Metro, City, State, or Zip codes to prevent overfitting
        -- NOTE: For Virtual Snapshot, we may need to derive from current data or skip
        -- ========================================================================
        safe_location_features AS (
            -- Create safe location proxies without exposing raw geography
            -- For Virtual Snapshot, we use simplified logic (can be enhanced later)
            SELECT
                rsp.lead_id,
                rsp.contacted_date,
                -- Metro advisor density tier - simplified for Virtual Snapshot
                -- TODO: Can be enhanced with aggregation from employment_history if metro data available
                'Unknown' as metro_advisor_density_tier,
                -- Core market flag - simplified (can be enhanced if state data available)
                0 as is_core_market
            FROM rep_state_pit rsp
        ),
        
        -- ========================================================================
        -- DATA QUALITY SIGNALS: Null/Unknown indicators (highly predictive in V12)
        -- ========================================================================
        -- NULL-SIGNAL FEATURES: Boolean indicators only—do not use for feature values
        -- NOTE: These join to ria_contacts_current ONLY for data quality flags (boolean indicators),
        -- not for feature calculation. This is an exception to the PIT-only rule.
        -- CRITICAL: These are boolean presence/absence indicators, NOT attribute values.
        -- ========================================================================
        data_quality_signals AS (
            -- Capture predictive power of missing data
            -- "No Gender Provided" often signals stale/low-quality profile
            -- BOOLEAN INDICATORS ONLY - Do NOT pull attribute values from ria_contacts_current
            SELECT
                rsp.lead_id,
                rsp.advisor_crd,
                -- Gender missing (2.15% missing in current data) - BOOLEAN INDICATOR ONLY
                CASE WHEN c.GENDER IS NULL OR c.GENDER = '' THEN 1 ELSE 0 END as is_gender_missing,
                -- LinkedIn missing (22.77% missing - highly predictive) - BOOLEAN INDICATOR ONLY
                CASE WHEN c.LINKEDIN_PROFILE_URL IS NULL OR c.LINKEDIN_PROFILE_URL = '' THEN 1 ELSE 0 END as is_linkedin_missing,
                -- Personal email missing (87.63% missing - very predictive) - BOOLEAN INDICATOR ONLY
                CASE WHEN c.PERSONAL_EMAIL_ADDRESS IS NULL OR c.PERSONAL_EMAIL_ADDRESS = '' THEN 1 ELSE 0 END as is_personal_email_missing,
                -- License data missing (0% missing, but check for completeness) - BOOLEAN INDICATOR ONLY
                CASE WHEN c.REP_LICENSES IS NULL OR c.REP_LICENSES = '' THEN 1 ELSE 0 END as is_license_data_missing,
                -- Industry tenure missing (6.1% missing) - BOOLEAN INDICATOR ONLY
                CASE WHEN c.INDUSTRY_TENURE_MONTHS IS NULL THEN 1 ELSE 0 END as is_industry_tenure_missing
            FROM rep_state_pit rsp
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` c
                ON rsp.advisor_crd = c.RIA_CONTACT_CRD_ID
        ),
        
        -- ========================================================================
        -- FIRM STABILITY: Rep movement metrics (PIT - calculated from employment history)
        -- Note: Still uses employment_history for movement calculation (this is PIT-safe)
        -- ========================================================================
        firm_stability_pit AS (
            SELECT
                rsp.lead_id,
                rsp.firm_crd_at_contact,
                rsp.contacted_date,
                
                -- Departures in 12 months before contact
                COUNT(DISTINCT CASE 
                    WHEN eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NOT NULL
                         AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE <= rsp.contacted_date
                         AND eh.PREVIOUS_REGISTRATION_COMPANY_END_DATE > DATE_SUB(rsp.contacted_date, INTERVAL 12 MONTH)
                    THEN eh.RIA_CONTACT_CRD_ID 
                END) as departures_12mo,
                
                -- Arrivals in 12 months before contact
                COUNT(DISTINCT CASE 
                    WHEN eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= rsp.contacted_date
                         AND eh.PREVIOUS_REGISTRATION_COMPANY_START_DATE > DATE_SUB(rsp.contacted_date, INTERVAL 12 MONTH)
                    THEN eh.RIA_CONTACT_CRD_ID 
                END) as arrivals_12mo
                
            FROM rep_state_pit rsp
            INNER JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_registered_employment_history` eh
                ON rsp.firm_crd_at_contact = eh.PREVIOUS_REGISTRATION_COMPANY_CRD_ID
            GROUP BY rsp.lead_id, rsp.firm_crd_at_contact, rsp.contacted_date
        ),
        
        -- ========================================================================
        -- FIRM STABILITY: Add derived metrics
        -- ========================================================================
        firm_stability_derived AS (
            SELECT
                fs.*,
                
                -- Net change (empirically: most predictive feature)
                arrivals_12mo - departures_12mo as net_change_12mo,
                
                -- Total movement (velocity indicator)
                departures_12mo + arrivals_12mo as total_movement_12mo
                
            FROM firm_stability_pit fs
        ),
        
        
        -- ========================================================================
        -- ACCOLADES: Count before contact date (PIT)
        -- ========================================================================
        accolades_pit AS (
            SELECT
                lb.lead_id,
                lb.advisor_crd,
                COUNT(*) as accolade_count,
                COUNTIF(a.OUTLET = 'Forbes') as forbes_accolades,
                COUNTIF(a.OUTLET = "Barron's") as barrons_accolades,
                MAX(a.YEAR) as most_recent_accolade_year
            FROM lead_base lb
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_accolades_historicals` a
                ON lb.advisor_crd = a.RIA_CONTACT_CRD_ID
                AND a.YEAR <= EXTRACT(YEAR FROM lb.contacted_date)
            GROUP BY lb.lead_id, lb.advisor_crd
        ),
        
        -- ========================================================================
        -- DISCLOSURES: Count before contact date (PIT)
        -- ========================================================================
        disclosures_pit AS (
            SELECT
                lb.lead_id,
                lb.advisor_crd,
                COUNT(*) as disclosure_count,
                COUNTIF(d.TYPE = 'Criminal') as criminal_disclosures,
                COUNTIF(d.TYPE = 'Regulatory') as regulatory_disclosures,
                COUNTIF(d.TYPE = 'Customer Dispute') as customer_dispute_disclosures
            FROM lead_base lb
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.Historical_Disclosure_data` d
                ON lb.advisor_crd = d.CONTACT_CRD_ID
                AND DATE(d.EVENT_DATE) < lb.contacted_date
            GROUP BY lb.lead_id, lb.advisor_crd
        ),
        
        -- ========================================================================
        -- PERCENTILE CALCULATIONS: Firm stability percentiles (calculated globally)
        -- This is a cross-sectional percentile for context
        -- ========================================================================
        stability_percentiles AS (
            SELECT
                lead_id,
                arrivals_12mo - departures_12mo as net_change_12mo,
                PERCENT_RANK() OVER (ORDER BY arrivals_12mo - departures_12mo) * 100 as net_change_percentile
            FROM firm_stability_pit
        ),
        
        -- ========================================================================
        -- GROUP A: QUALITY & PRODUCTION SIGNALS
        -- ========================================================================
        
        -- 1. Production Proxy (The "Hidden Whale" Signal)
        -- Source: private_wealth_teams_ps (Team AUM) + Firm_historicals (fallback)
        production_proxy AS (
            SELECT
                rsp.lead_id,
                rsp.advisor_crd,
                rsp.firm_crd_at_contact,
                rsp.contacted_date,
                -- Waterfall logic: Team AUM (4% coverage, high signal) -> Firm AUM per rep -> Firm AUM PIT
                COALESCE(
                    pt.AUM,  -- Gold standard (rare but high signal)
                    SAFE_DIVIDE(fsp.firm_aum_pit, fsp.firm_rep_count_at_contact),  -- Firm AUM per rep
                    fsp.firm_aum_pit  -- Fallback to firm AUM
                ) as production_proxy_aum
            FROM rep_state_pit rsp
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` rc
                ON rsp.advisor_crd = rc.RIA_CONTACT_CRD_ID
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.private_wealth_teams_ps` pt
                ON rc.WEALTH_TEAM_ID_1 = pt.ID
            LEFT JOIN firm_state_pit fsp
                ON rsp.lead_id = fsp.lead_id
        ),
        
        -- 2. Accolades (PIT-Safe Prestige) - Enhanced version
        accolades_enhanced AS (
            SELECT
                ap.lead_id,
                ap.advisor_crd,
                ap.accolade_count as accolade_count_lifetime,
                CASE 
                    WHEN ap.most_recent_accolade_year IS NOT NULL
                         AND ap.most_recent_accolade_year >= EXTRACT(YEAR FROM lb.contacted_date) - 3 
                    THEN 1 
                    ELSE 0 
                END as has_recent_accolade,
                CASE 
                    WHEN COALESCE(ap.forbes_accolades, 0) > 0 
                    THEN 1 
                    ELSE 0 
                END as is_forbes_ranked
            FROM accolades_pit ap
            INNER JOIN lead_base lb ON ap.lead_id = lb.lead_id
        ),
        
        -- 3. Licenses & Accreditations (JSON Parsing Required)
        licenses_features AS (
            SELECT
                rsp.lead_id,
                rsp.advisor_crd,
                -- License count from JSON array
                ARRAY_LENGTH(JSON_EXTRACT_ARRAY(COALESCE(rc.REP_LICENSES, '[]'))) as license_count,
                -- Series 7 check (NULL-safe)
                CASE WHEN COALESCE(rc.REP_LICENSES, '') LIKE '%Series 7%' THEN 1 ELSE 0 END as has_series_7,
                -- Series 65/66 check (NULL-safe)
                CASE 
                    WHEN COALESCE(rc.REP_LICENSES, '') LIKE '%Series 65%' 
                      OR COALESCE(rc.REP_LICENSES, '') LIKE '%Series 66%' 
                    THEN 1 
                    ELSE 0 
                END as has_series_65_66,
                -- CFP check (from ACCOLADES)
                CASE 
                    WHEN COALESCE(rc.ACCOLADES, '') LIKE '%CFP%' 
                      OR COALESCE(rc.ACCOLADES, '') LIKE '%Certified Financial Planner%'
                    THEN 1 
                    ELSE 0 
                END as is_cfp
            FROM rep_state_pit rsp
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_contacts_current` rc
                ON rsp.advisor_crd = rc.RIA_CONTACT_CRD_ID
        ),
        
        -- ========================================================================
        -- GROUP B: BUSINESS CONTEXT & TECH STACK
        -- ========================================================================
        
        -- 4. Custodian & Tech Stack (PIT-Safe)
        custodians_pit AS (
            SELECT
                rsp.lead_id,
                rsp.firm_crd_at_contact,
                rsp.contacted_date,
                -- Primary custodian (most recent as of contacted_date month)
                ARRAY_AGG(c.PRIMARY_BUSINESS_NAME ORDER BY c.period DESC LIMIT 1)[OFFSET(0)] as custodian_primary,
                -- Multi-custodial flag
                CASE WHEN COUNT(DISTINCT c.PRIMARY_BUSINESS_NAME) > 1 THEN 1 ELSE 0 END as is_multicustodial
            FROM rep_state_pit rsp
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.custodians_historicals` c
                ON rsp.firm_crd_at_contact = c.RIA_INVESTOR_CRD_ID
                AND PARSE_DATE('%Y-%m', c.period) <= DATE_TRUNC(rsp.contacted_date, MONTH)
            GROUP BY rsp.lead_id, rsp.firm_crd_at_contact, rsp.contacted_date
        ),
        
        -- 5. Client Wealth Segmentation (PIT-Safe)
        client_wealth_pit AS (
            SELECT
                fsp.lead_id,
                -- HNW AUM ratio (if HNW AUM available)
                SAFE_DIVIDE(
                    COALESCE(fsp.firm_hnw_aum_pit, 0),
                    NULLIF(fsp.firm_aum_pit, 0)
                ) as firm_hnw_aum_ratio,
                -- Average client size (if total accounts available)
                SAFE_DIVIDE(
                    fsp.firm_aum_pit,
                    NULLIF(COALESCE(fsp.firm_total_accounts_pit, 0), 0)
                ) as avg_client_size
            FROM firm_state_pit fsp
        ),
        
        -- ========================================================================
        -- GROUP C: SCALE & STRUCTURE
        -- ========================================================================
        
        -- 6. Geographic Scale (PIT-Safe)
        geographic_scale_pit AS (
            SELECT
                rsp.lead_id,
                rsp.advisor_crd,
                rsp.contacted_date,
                COUNT(DISTINCT sr.registerations_regulator) as num_states_registered
            FROM rep_state_pit rsp
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.contact_state_registrations_historicals` sr
                ON rsp.advisor_crd = sr.contact_crd_id
                AND sr.active = TRUE
                AND PARSE_DATE('%Y-%m', sr.period) <= DATE_TRUNC(rsp.contacted_date, MONTH)
            GROUP BY rsp.lead_id, rsp.advisor_crd, rsp.contacted_date
        ),
        
        -- 7. Firm Complexity (Support Ratio)
        firm_complexity AS (
            SELECT
                rsp.lead_id,
                rsp.firm_crd_at_contact,
                -- Support ratio: (Total Employees - Reps) / Reps
                -- High ratio = "Fat" firm (hard to leave), Low ratio = "Lean" firm (easier to leave)
                SAFE_DIVIDE(
                    COALESCE(rfc.NUM_OF_EMPLOYEES, 0) - COALESCE(fsp.firm_rep_count_at_contact, 0),
                    NULLIF(fsp.firm_rep_count_at_contact, 0)
                ) as support_ratio
            FROM rep_state_pit rsp
            LEFT JOIN firm_state_pit fsp
                ON rsp.lead_id = fsp.lead_id
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` rfc
                ON rsp.firm_crd_at_contact = rfc.CRD_ID
        ),
        
        -- 8. Firm Entity Structure (Static Proxy)
        firm_entity_structure AS (
            SELECT
                rsp.lead_id,
                rsp.firm_crd_at_contact,
                -- Extract entity type from JSON array (first element)
                COALESCE(
                    (SELECT JSON_EXTRACT_SCALAR(entity_val, '$')
                     FROM UNNEST(JSON_EXTRACT_ARRAY(COALESCE(rfc.ENTITY_CLASSIFICATION, '[]'))) as entity_val
                     LIMIT 1),
                    'Unknown'
                ) as firm_entity_type,
                -- ESG investor flag
                CASE WHEN COALESCE(rfc.ACTIVE_ESG_INVESTOR, FALSE) = TRUE THEN 1 ELSE 0 END as is_esg_investor,
                -- Fee structure type (extract first from JSON array)
                COALESCE(
                    (SELECT JSON_EXTRACT_SCALAR(fee_val, '$')
                     FROM UNNEST(JSON_EXTRACT_ARRAY(COALESCE(rfc.FEE_STRUCTURE, '[]'))) as fee_val
                     LIMIT 1),
                    'Unknown'
                ) as fee_structure_type
            FROM rep_state_pit rsp
            LEFT JOIN `savvy-gtm-analytics.FinTrx_data_CA.ria_firms_current` rfc
                ON rsp.firm_crd_at_contact = rfc.CRD_ID
        )
        
        -- ========================================================================
        -- FINAL: Combine all features
        -- ========================================================================
        SELECT
            -- Identifiers & Target
            lb.lead_id,
            lb.advisor_crd,
            lb.contacted_date,
            lb.target,
            lb.lead_source,
            
            -- Firm identifiers (for analysis, not features)
            rsp.firm_crd_at_contact,
            -- Note: firm_name not available in Virtual Snapshot (would need additional source)
            -- rsp.firm_name_at_contact,
            rsp.contacted_date as vintage_contacted_date,  -- Track contact date (for validation)
            lb.pit_month,  -- PIT month used for firm features (for leakage audit)
            rsp.days_in_gap,  -- Gap indicator: days between job end and contact (0 = no gap)
            
            -- =====================
            -- ADVISOR FEATURES (from Virtual Snapshot - rep_state_pit)
            -- =====================
            COALESCE(rsp.industry_tenure_months, 0) as industry_tenure_months,
            COALESCE(rsp.num_prior_firms, 0) as num_prior_firms,
            COALESCE(rsp.current_firm_tenure_months, 0) as current_firm_tenure_months,
            COALESCE(avf.avg_prior_firm_tenure_months, 0) as avg_prior_firm_tenure_months,
            COALESCE(efs.firms_in_last_5_years, 0) as firms_in_last_5_years,
            
            -- VALIDATED MOBILITY FEATURES (3-year lookback and Restlessness) - HIGH PRIORITY SIGNALS
            COALESCE(md.pit_moves_3yr, 0) as pit_moves_3yr,
            COALESCE(md.pit_avg_prior_tenure_months, 0) as pit_avg_prior_tenure_months,
            COALESCE(md.pit_restlessness_ratio, 1.0) as pit_restlessness_ratio,
            COALESCE(md.pit_mobility_tier, 'Unknown') as pit_mobility_tier,
            
            -- Note: advisor_total_assets_millions not available in Virtual Snapshot
            -- COALESCE(afs.advisor_total_assets_millions, 0) as advisor_total_assets_millions,
            
            -- Note: License features not available in Virtual Snapshot (would need additional source)
            -- COALESCE(afs.Has_Series_7, 0) as has_series_7,
            -- COALESCE(afs.Has_Series_65, 0) as has_series_65,
            -- COALESCE(afs.Has_Series_66, 0) as has_series_66,
            -- COALESCE(afs.Has_CFP, 0) as has_cfp,
            -- Note: LinkedIn and disclosure flags from data_quality_signals instead
            -- COALESCE(afs.has_disclosure_from_snapshot, 0) as has_disclosure_from_snapshot,
            
            -- =====================
            -- FIRM AUM FEATURES (from Virtual Snapshot - firm_state_pit)
            -- =====================
            fsp.firm_aum_pit,
            LOG(GREATEST(1, COALESCE(fsp.firm_aum_pit, 1))) as log_firm_aum,
            -- Note: firm_total_accounts_pit, firm_hnw_clients_pit not available in Firm_historicals
            -- ffs.firm_total_accounts_pit,
            -- ffs.firm_hnw_clients_pit,
            fsp.aum_growth_12mo_pct,
            fsp.firm_rep_count_at_contact,
            -- Note: avg_rep_aum_millions, avg_rep_experience_years, avg_tenure_at_firm_years not available in Firm_historicals
            -- ffs.avg_rep_aum_millions,
            -- ffs.avg_rep_experience_years,
            -- ffs.avg_tenure_at_firm_years,
            
            -- AUM tier (calculated from firm_aum_pit)
            CASE
                WHEN fsp.firm_aum_pit >= 1000000000 THEN 'Billion+'
                WHEN fsp.firm_aum_pit >= 100000000 THEN '100M-1B'
                WHEN fsp.firm_aum_pit >= 10000000 THEN '10M-100M'
                WHEN fsp.firm_aum_pit >= 1000000 THEN '1M-10M'
                WHEN fsp.firm_aum_pit IS NOT NULL THEN 'Under_1M'
                ELSE 'Unknown'
            END as firm_aum_tier,
            
            -- =====================
            -- SAFE LOCATION PROXIES (NO RAW GEOGRAPHY)
            -- =====================
            COALESCE(slf.metro_advisor_density_tier, 'Unknown') as metro_advisor_density_tier,
            COALESCE(slf.is_core_market, 0) as is_core_market,
            
            -- =====================
            -- FIRM STABILITY FEATURES (PIT - KEY PREDICTORS)
            -- =====================
            COALESCE(fst.departures_12mo, 0) as firm_departures_12mo,
            COALESCE(fst.arrivals_12mo, 0) as firm_arrivals_12mo,
            COALESCE(fst.arrivals_12mo - fst.departures_12mo, 0) as firm_net_change_12mo,
            COALESCE(fst.arrivals_12mo + fst.departures_12mo, 0) as firm_total_movement_12mo,
            
            -- Net change score (empirically validated: 50 + net_change * 3.5)
            ROUND(GREATEST(0, LEAST(100, 50 + COALESCE(fst.arrivals_12mo - fst.departures_12mo, 0) * 3.5)), 1) as firm_stability_score,
            
            -- Stability percentile
            COALESCE(sp.net_change_percentile, 50) as firm_stability_percentile,
            
            -- Priority classification (empirically validated thresholds)
            CASE
                WHEN COALESCE(sp.net_change_percentile, 50) <= 10 THEN 'HIGH_PRIORITY'
                WHEN COALESCE(sp.net_change_percentile, 50) <= 25 THEN 'MEDIUM_PRIORITY'
                WHEN COALESCE(fst.arrivals_12mo - fst.departures_12mo, 0) < 0 THEN 'MONITOR'
                ELSE 'STABLE'
            END as firm_recruiting_priority,
            
            -- Stability tier (binned)
            CASE
                WHEN COALESCE(fst.arrivals_12mo - fst.departures_12mo, 0) <= -14 THEN 'Severe_Bleeding'
                WHEN COALESCE(fst.arrivals_12mo - fst.departures_12mo, 0) <= -3 THEN 'Moderate_Bleeding'
                WHEN COALESCE(fst.arrivals_12mo - fst.departures_12mo, 0) < 0 THEN 'Slight_Bleeding'
                WHEN COALESCE(fst.arrivals_12mo - fst.departures_12mo, 0) = 0 THEN 'Stable'
                ELSE 'Growing'
            END as firm_stability_tier,
            
            -- =====================
            -- ACCOLADES & QUALITY FEATURES
            -- =====================
            COALESCE(ap.accolade_count, 0) as accolade_count,
            CASE WHEN COALESCE(ap.accolade_count, 0) > 0 THEN 1 ELSE 0 END as has_accolades,
            COALESCE(ap.forbes_accolades, 0) as forbes_accolades,
            
            -- =====================
            -- DISCLOSURE FEATURES (PIT)
            -- =====================
            COALESCE(dp.disclosure_count, 0) as disclosure_count,
            CASE WHEN COALESCE(dp.disclosure_count, 0) > 0 THEN 1 ELSE 0 END as has_disclosures,
            COALESCE(dp.criminal_disclosures, 0) as criminal_disclosures,
            COALESCE(dp.regulatory_disclosures, 0) as regulatory_disclosures,
            
            -- =====================
            -- DATA QUALITY INDICATORS & NULL SIGNALS
            -- =====================
            -- Note: has_linkedin from data_quality_signals (inverse of is_linkedin_missing)
            CASE WHEN COALESCE(dqs.is_linkedin_missing, 1) = 0 THEN 1 ELSE 0 END as has_linkedin,
            CASE WHEN fsp.firm_aum_pit IS NOT NULL THEN 1 ELSE 0 END as has_firm_aum,
            CASE WHEN rsp.firm_crd_at_contact IS NOT NULL THEN 1 ELSE 0 END as has_valid_virtual_snapshot,
            
            -- NULL SIGNAL FEATURES (Highly predictive in V12 - capture missing data patterns)
            -- These prevent the model from imputing "Average" for bad data
            -- Instead, the model learns that "Bad Data = Low Conversion"
            COALESCE(dqs.is_gender_missing, 0) as is_gender_missing,
            COALESCE(dqs.is_linkedin_missing, 0) as is_linkedin_missing,
            COALESCE(dqs.is_personal_email_missing, 0) as is_personal_email_missing,
            COALESCE(dqs.is_license_data_missing, 0) as is_license_data_missing,
            COALESCE(dqs.is_industry_tenure_missing, 0) as is_industry_tenure_missing,
            
            -- =====================
            -- GROUP A: QUALITY & PRODUCTION SIGNALS
            -- =====================
            -- 1. Production Proxy (The "Hidden Whale" Signal)
            COALESCE(pp.production_proxy_aum, 0) as production_proxy_aum,
            
            -- 2. Accolades Enhanced (PIT-Safe Prestige)
            COALESCE(ae.accolade_count_lifetime, 0) as accolade_count_lifetime,
            COALESCE(ae.has_recent_accolade, 0) as has_recent_accolade,
            COALESCE(ae.is_forbes_ranked, 0) as is_forbes_ranked,
            
            -- 3. Licenses & Accreditations (JSON Parsing Required)
            COALESCE(lf.license_count, 0) as license_count,
            COALESCE(lf.has_series_7, 0) as has_series_7,
            COALESCE(lf.has_series_65_66, 0) as has_series_65_66,
            COALESCE(lf.is_cfp, 0) as is_cfp,
            
            -- =====================
            -- GROUP B: BUSINESS CONTEXT & TECH STACK
            -- =====================
            -- 4. Custodian & Tech Stack (PIT-Safe)
            cp.custodian_primary,
            COALESCE(cp.is_multicustodial, 0) as is_multicustodial,
            
            -- 5. Client Wealth Segmentation (PIT-Safe)
            COALESCE(cw.firm_hnw_aum_ratio, 0) as firm_hnw_aum_ratio,
            COALESCE(cw.avg_client_size, 0) as avg_client_size,
            
            -- =====================
            -- GROUP C: SCALE & STRUCTURE
            -- =====================
            -- 6. Geographic Scale (PIT-Safe)
            COALESCE(gs.num_states_registered, 0) as num_states_registered,
            
            -- 7. Firm Complexity (Support Ratio)
            COALESCE(fc.support_ratio, 0) as support_ratio,
            
            -- 8. Firm Entity Structure (Static Proxy)
            COALESCE(fes.firm_entity_type, 'Unknown') as firm_entity_type,
            COALESCE(fes.is_esg_investor, 0) as is_esg_investor,
            COALESCE(fes.fee_structure_type, 'Unknown') as fee_structure_type,
            
            -- Metadata
            CURRENT_TIMESTAMP() as feature_extraction_ts
            
        FROM lead_base lb
        LEFT JOIN rep_state_pit rsp ON lb.lead_id = rsp.lead_id
        LEFT JOIN advisor_features_virtual avf ON lb.lead_id = avf.lead_id
        LEFT JOIN firm_state_pit fsp ON lb.lead_id = fsp.lead_id
        LEFT JOIN safe_location_features slf ON lb.lead_id = slf.lead_id
        LEFT JOIN data_quality_signals dqs ON lb.lead_id = dqs.lead_id
        LEFT JOIN employment_features_supplement efs ON lb.lead_id = efs.lead_id
        LEFT JOIN mobility_derived md ON lb.lead_id = md.lead_id
        LEFT JOIN firm_stability_pit fst ON lb.lead_id = fst.lead_id
        LEFT JOIN accolades_pit ap ON lb.lead_id = ap.lead_id
        LEFT JOIN disclosures_pit dp ON lb.lead_id = dp.lead_id
        LEFT JOIN stability_percentiles sp ON lb.lead_id = sp.lead_id
        LEFT JOIN production_proxy pp ON lb.lead_id = pp.lead_id
        LEFT JOIN accolades_enhanced ae ON lb.lead_id = ae.lead_id
        LEFT JOIN licenses_features lf ON lb.lead_id = lf.lead_id
        LEFT JOIN custodians_pit cp ON lb.lead_id = cp.lead_id
        LEFT JOIN client_wealth_pit cw ON lb.lead_id = cw.lead_id
        LEFT JOIN geographic_scale_pit gs ON lb.lead_id = gs.lead_id
        LEFT JOIN firm_complexity fc ON lb.lead_id = fc.lead_id
        LEFT JOIN firm_entity_structure fes ON lb.lead_id = fes.lead_id
        
        WHERE lb.target IS NOT NULL  -- Exclude right-censored leads
          AND rsp.firm_crd_at_contact IS NOT NULL;  -- CRITICAL: Only include leads with valid Virtual Snapshot (rep state found)
        