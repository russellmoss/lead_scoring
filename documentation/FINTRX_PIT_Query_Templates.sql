-- FINTRX Point-in-Time (PIT) Query Templates
-- Use these templates to extract features for lead scoring without data leakage
-- Always filter historical data to dates BEFORE the contact date

-- ============================================================================
-- ⚠️ IMPORTANT: PIT Limitations
-- ============================================================================
-- 
-- ✅ PIT Queries ARE Possible For:
--   - Firm AUM (via Firm_historicals YEAR/MONTH)
--   - Employment history (via contact_registered_employment_history date ranges)
--   - Accolades (via contact_accolades_historicals YEAR filter)
--   - State registrations (via contact_state_registrations_historicals period/date)
--   - Disclosures (via Historical_Disclosure_data EVENT_DATE)
--   - Custodians (via custodians_historicals period)
--
-- ❌ PIT Queries are NOT Possible For:
--   - Rep-level AUM (no historical data, and 99% NULL anyway)
--   - Licenses (current state only in ria_contacts_current.REP_LICENSES)
--   - Team AUM (current state only in private_wealth_teams_ps.AUM)
--   - Contact info (email, phone, etc. - current state only)
--   - Contact roles/title (current state only)
--
-- ⚠️ Note: For fields that are STRING containing JSON arrays (like REP_LICENSES),
--   use JSON_EXTRACT_ARRAY() or LIKE queries. See examples below.

-- ============================================================================
-- TEMPLATE 1: Get Firm Snapshot as of a Specific Date
-- ============================================================================
-- Use case: Get firm metrics as of June 2024 (before July 1, 2024 contact)
-- ✅ PIT POSSIBLE - Firm_historicals has monthly snapshots

WITH contact_event AS (
  SELECT 
    12345 AS firm_crd,  -- Replace with actual CRD_ID
    DATE('2024-07-01') AS contact_date,
    2024 AS contact_year,
    7 AS contact_month
)
SELECT 
  h.*
FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h
CROSS JOIN contact_event ce
WHERE h.RIA_INVESTOR_CRD_ID = ce.firm_crd
  AND (
    h.YEAR < ce.contact_year 
    OR (h.YEAR = ce.contact_year AND h.MONTH < ce.contact_month)
  )
ORDER BY h.YEAR DESC, h.MONTH DESC
LIMIT 1;


-- ============================================================================
-- TEMPLATE 2: Get Most Recent Firm Snapshot Before Contact Date
-- ============================================================================
-- Use case: Get the most recent firm snapshot available before contact date
-- ✅ PIT POSSIBLE

WITH contact_event AS (
  SELECT 
    12345 AS firm_crd,
    DATE('2024-07-01') AS contact_date,
    2024 AS contact_year,
    7 AS contact_month
),
most_recent_snapshot AS (
  SELECT 
    h.*,
    ROW_NUMBER() OVER (
      PARTITION BY h.RIA_INVESTOR_CRD_ID
      ORDER BY h.YEAR DESC, h.MONTH DESC
    ) as rn
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h
  CROSS JOIN contact_event ce
  WHERE h.RIA_INVESTOR_CRD_ID = ce.firm_crd
    AND (
      h.YEAR < ce.contact_year 
      OR (h.YEAR = ce.contact_year AND h.MONTH < ce.contact_month)
    )
)
SELECT *
FROM most_recent_snapshot
WHERE rn = 1;


-- ============================================================================
-- TEMPLATE 3: Get Employment History as of a Specific Date
-- ============================================================================
-- Use case: Determine where a rep worked at the time of contact
-- ✅ PIT POSSIBLE - contact_registered_employment_history has date ranges

WITH contact_event AS (
  SELECT 
    12345 AS rep_crd,
    DATE('2024-07-01') AS contact_date
)
SELECT 
  e.*,
  CASE 
    WHEN e.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
      OR e.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= ce.contact_date
    THEN TRUE 
    ELSE FALSE 
  END as was_active_at_contact_date
FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history` e
CROSS JOIN contact_event ce
WHERE e.RIA_CONTACT_CRD_ID = ce.rep_crd
  AND e.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= ce.contact_date
  AND (
    e.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
    OR e.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= ce.contact_date
  )
ORDER BY e.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC;


-- ============================================================================
-- TEMPLATE 4: Calculate Tenure at Current Firm as of Contact Date
-- ============================================================================
-- Use case: Calculate how long rep has been at current firm as of contact date
-- ✅ PIT POSSIBLE - Calculate from employment history

WITH contact_event AS (
  SELECT 
    12345 AS rep_crd,
    DATE('2024-07-01') AS contact_date
),
current_employment AS (
  SELECT 
    e.*,
    DATE_DIFF(
      ce.contact_date,
      e.PREVIOUS_REGISTRATION_COMPANY_START_DATE,
      MONTH
    ) as tenure_months_at_contact
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history` e
  CROSS JOIN contact_event ce
  WHERE e.RIA_CONTACT_CRD_ID = ce.rep_crd
    AND e.PREVIOUS_REGISTRATION_COMPANY_START_DATE <= ce.contact_date
    AND (
      e.PREVIOUS_REGISTRATION_COMPANY_END_DATE IS NULL 
      OR e.PREVIOUS_REGISTRATION_COMPANY_END_DATE >= ce.contact_date
    )
  ORDER BY e.PREVIOUS_REGISTRATION_COMPANY_START_DATE DESC
  LIMIT 1
)
SELECT 
  *,
  tenure_months_at_contact
FROM current_employment;


-- ============================================================================
-- TEMPLATE 5: Get Accolades as of a Specific Date
-- ============================================================================
-- Use case: Get accolades that existed before contact date (recruiting trigger)
-- ✅ PIT POSSIBLE - contact_accolades_historicals has YEAR field

WITH contact_event AS (
  SELECT 
    12345 AS rep_crd,
    2024 AS contact_year
)
SELECT 
  a.*
FROM `savvy-gtm-analytics.FinTrx_data.contact_accolades_historicals` a
CROSS JOIN contact_event ce
WHERE a.RIA_CONTACT_CRD_ID = ce.rep_crd
  AND a.YEAR <= ce.contact_year
ORDER BY a.YEAR DESC, a.OUTLET;


-- ============================================================================
-- TEMPLATE 6: Get State Registrations as of a Specific Date
-- ============================================================================
-- Use case: Determine what states a rep was registered in at contact date
-- ✅ PIT POSSIBLE - contact_state_registrations_historicals has period and date fields

WITH contact_event AS (
  SELECT 
    12345 AS rep_crd,
    DATE('2024-07-01') AS contact_date,
    '2024-07' AS contact_period
)
SELECT DISTINCT
  csr.registerations_regulator as state,
  csr.registerations_registeration as registration_type,
  csr.registerations_registeration_status as status
FROM `savvy-gtm-analytics.FinTrx_data.contact_state_registrations_historicals` csr
CROSS JOIN contact_event ce
WHERE csr.contact_crd_id = ce.rep_crd
  AND csr.period <= ce.contact_period
  AND csr.registerations_registeration_date <= ce.contact_date
  AND csr.active = TRUE
ORDER BY csr.registerations_regulator;


-- ============================================================================
-- TEMPLATE 7: Get BD State Registrations as of a Specific Date
-- ============================================================================
-- Use case: Determine BD state registrations at contact date
-- ✅ PIT POSSIBLE

WITH contact_event AS (
  SELECT 
    12345 AS rep_crd,
    DATE('2024-07-01') AS contact_date,
    '2024-07' AS contact_period
)
SELECT DISTINCT
  bd.state,
  bd.registration_scope,
  bd.registration_date
FROM `savvy-gtm-analytics.FinTrx_data.contact_broker_dealer_state_historicals` bd
CROSS JOIN contact_event ce
WHERE bd.contact_crd_id = ce.rep_crd
  AND bd.period <= ce.contact_period
  AND bd.registration_date <= ce.contact_date
ORDER BY bd.state;


-- ============================================================================
-- TEMPLATE 8: Check for Disclosures Before Contact Date
-- ============================================================================
-- Use case: Check if rep had any disclosures before contact (disqualifier)
-- ✅ PIT POSSIBLE - Historical_Disclosure_data has EVENT_DATE

WITH contact_event AS (
  SELECT 
    12345 AS rep_crd,
    DATE('2024-07-01') AS contact_date
)
SELECT 
  d.*
FROM `savvy-gtm-analytics.FinTrx_data.Historical_Disclosure_data` d
CROSS JOIN contact_event ce
WHERE d.CONTACT_CRD_ID = ce.rep_crd
  AND d.EVENT_DATE < ce.contact_date
ORDER BY d.EVENT_DATE DESC;


-- ============================================================================
-- TEMPLATE 9: Get Custodian Information as of a Specific Date
-- ============================================================================
-- Use case: Determine which custodian a firm was using at contact date
-- ✅ PIT POSSIBLE - custodians_historicals has period field

WITH contact_event AS (
  SELECT 
    12345 AS firm_crd,
    DATE('2024-07-01') AS contact_date,
    '2024-07' AS contact_period
)
SELECT 
  c.*
FROM `savvy-gtm-analytics.FinTrx_data.custodians_historicals` c
CROSS JOIN contact_event ce
WHERE c.RIA_INVESTOR_CRD_ID = ce.firm_crd
  AND c.period <= ce.contact_period
  AND c.CURRENT_DATA = TRUE
ORDER BY c.period DESC
LIMIT 1;


-- ============================================================================
-- TEMPLATE 10: Complete Feature Vector for Lead Scoring (PIT)
-- ============================================================================
-- Use case: Extract all PIT-available features for a single contact at a specific date
-- ✅ Only includes features where PIT queries are possible

WITH contact_event AS (
  SELECT 
    12345 AS rep_crd,
    DATE('2024-07-01') AS contact_date,
    2024 AS contact_year,
    7 AS contact_month
),
-- Contact base data (current state only - some data leakage risk)
contact_base AS (
  SELECT *
  FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
  WHERE RIA_CONTACT_CRD_ID = (SELECT rep_crd FROM contact_event)
),
-- Firm snapshot as of date (PIT)
firm_snapshot AS (
  SELECT 
    h.*,
    ROW_NUMBER() OVER (ORDER BY h.YEAR DESC, h.MONTH DESC) as rn
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h
  CROSS JOIN contact_event ce
  CROSS JOIN contact_base c
  WHERE h.RIA_INVESTOR_CRD_ID = COALESCE(c.PRIMARY_FIRM, c.PRIMARY_RIA, c.PRIMARY_BD)
    AND (
      h.YEAR < ce.contact_year 
      OR (h.YEAR = ce.contact_year AND h.MONTH < ce.contact_month)
    )
),
-- Team data (current state only - small data leakage risk)
team_data AS (
  SELECT 
    t.AUM as team_aum,
    t.MINIMUM_ACCOUNT_SIZE
  FROM `savvy-gtm-analytics.FinTrx_data.private_wealth_teams_ps` t
  CROSS JOIN contact_base c
  WHERE t.ID IN (c.WEALTH_TEAM_ID_1, c.WEALTH_TEAM_ID_2, c.WEALTH_TEAM_ID_3)
  ORDER BY t.AUM DESC
  LIMIT 1
),
-- Accolades count (PIT)
accolades_summary AS (
  SELECT 
    COUNT(*) as num_accolades,
    COUNTIF(OUTLET = 'Forbes') as num_forbes_accolades,
    COUNTIF(OUTLET = "Barron's") as num_barrons_accolades,
    MAX(YEAR) as most_recent_accolade_year
  FROM `savvy-gtm-analytics.FinTrx_data.contact_accolades_historicals`
  CROSS JOIN contact_event ce
  WHERE RIA_CONTACT_CRD_ID = ce.rep_crd
    AND YEAR <= ce.contact_year
),
-- Employment tenure (PIT)
employment_tenure AS (
  SELECT 
    SUM(
      DATE_DIFF(
        COALESCE(PREVIOUS_REGISTRATION_COMPANY_END_DATE, CURRENT_DATE()),
        PREVIOUS_REGISTRATION_COMPANY_START_DATE,
        MONTH
      )
    ) as total_tenure_months,
    COUNT(*) as num_previous_firms,
    DATE_DIFF(
      (SELECT contact_date FROM contact_event),
      MAX(PREVIOUS_REGISTRATION_COMPANY_START_DATE),
      MONTH
    ) as tenure_at_current_firm_months
  FROM `savvy-gtm-analytics.FinTrx_data.contact_registered_employment_history`
  CROSS JOIN contact_event ce
  WHERE RIA_CONTACT_CRD_ID = ce.rep_crd
    AND PREVIOUS_REGISTRATION_COMPANY_START_DATE <= ce.contact_date
),
-- State registrations count (PIT)
state_registrations AS (
  SELECT 
    COUNT(DISTINCT registerations_regulator) as num_states_registered
  FROM `savvy-gtm-analytics.FinTrx_data.contact_state_registrations_historicals`
  CROSS JOIN contact_event ce
  WHERE contact_crd_id = ce.rep_crd
    AND period <= FORMAT_DATE('%Y-%m', ce.contact_date)
    AND registerations_registeration_date <= ce.contact_date
    AND active = TRUE
),
-- Disclosures check (PIT)
disclosures_check AS (
  SELECT 
    COUNT(*) as num_disclosures,
    COUNTIF(TYPE = 'Criminal') as num_criminal,
    COUNTIF(TYPE = 'Regulatory') as num_regulatory,
    COUNTIF(TYPE = 'Customer Dispute') as num_customer_dispute
  FROM `savvy-gtm-analytics.FinTrx_data.Historical_Disclosure_data`
  CROSS JOIN contact_event ce
  WHERE CONTACT_CRD_ID = ce.rep_crd
    AND EVENT_DATE < ce.contact_date
),
-- Firm current data (fallback if snapshot unavailable)
firm_current AS (
  SELECT *
  FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current`
  CROSS JOIN contact_base c
  WHERE CRD_ID = COALESCE(c.PRIMARY_FIRM, c.PRIMARY_RIA, c.PRIMARY_BD)
)
SELECT 
  -- Contact identifiers
  c.RIA_CONTACT_CRD_ID,
  c.RIA_CONTACT_PREFERRED_NAME,
  
  -- AUM Features (priority: firm snapshot > firm current > team)
  COALESCE(fs.TOTAL_AUM, fc.TOTAL_AUM, t.team_aum) as aum,
  COALESCE(fs.TOTAL_AUM, fc.TOTAL_AUM) as firm_aum,
  t.team_aum,
  
  -- Experience Features (PIT)
  COALESCE(et.total_tenure_months, c.INDUSTRY_TENURE_MONTHS) as industry_tenure_months,
  et.tenure_at_current_firm_months,
  et.num_previous_firms,
  
  -- Quality Signals (PIT)
  COALESCE(a.num_accolades, 0) as num_accolades,
  COALESCE(a.num_forbes_accolades, 0) as num_forbes_accolades,
  COALESCE(a.num_barrons_accolades, 0) as num_barrons_accolades,
  a.most_recent_accolade_year,
  
  -- Firm Characteristics (PIT for AUM, current state for others)
  fc.ENTITY_CLASSIFICATION,
  fc.NUM_OF_EMPLOYEES,
  fs.NUM_OF_CLIENTS_HIGH_NET_WORTH_INDIVIDUALS as hnw_clients_as_of_date,
  
  -- Licenses (current state only - small data leakage risk)
  ARRAY_LENGTH(JSON_EXTRACT_ARRAY(c.REP_LICENSES)) as num_licenses,
  
  -- State Registrations (PIT)
  COALESCE(sr.num_states_registered, 0) as num_states_registered,
  
  -- Disclosures (PIT - disqualifiers)
  COALESCE(dc.num_disclosures, 0) as num_disclosures,
  COALESCE(dc.num_criminal, 0) as num_criminal_disclosures,
  COALESCE(dc.num_regulatory, 0) as num_regulatory_disclosures,
  
  -- Metadata
  (SELECT contact_date FROM contact_event) as feature_extraction_date
  
FROM contact_base c
LEFT JOIN firm_snapshot fs ON fs.rn = 1
LEFT JOIN team_data t ON TRUE
LEFT JOIN accolades_summary a ON TRUE
LEFT JOIN employment_tenure et ON TRUE
LEFT JOIN state_registrations sr ON TRUE
LEFT JOIN disclosures_check dc ON TRUE
LEFT JOIN firm_current fc ON TRUE;


-- ============================================================================
-- TEMPLATE 11: Batch Processing Multiple Reps at Different Dates
-- ============================================================================
-- Use case: Extract features for multiple contacts contacted at different dates
-- Input: Table with rep_crd and contact_date

WITH contact_events AS (
  -- Replace this with your actual contact events table
  SELECT 
    RIA_CONTACT_CRD_ID as rep_crd,
    CONTACT_DATE as contact_date,
    EXTRACT(YEAR FROM CONTACT_DATE) as contact_year,
    EXTRACT(MONTH FROM CONTACT_DATE) as contact_month
  FROM `your_project.your_dataset.contact_events`  -- Replace with your table
  WHERE CONTACT_DATE >= '2024-01-01'
),
-- Get firm snapshots for all contacts
firm_snapshots AS (
  SELECT 
    ce.rep_crd,
    ce.contact_date,
    h.*,
    ROW_NUMBER() OVER (
      PARTITION BY ce.rep_crd, ce.contact_date
      ORDER BY h.YEAR DESC, h.MONTH DESC
    ) as rn
  FROM contact_events ce
  INNER JOIN `savvy-gtm-analytics.FinTrx_data.ria_contacts_current` c
    ON c.RIA_CONTACT_CRD_ID = ce.rep_crd
  LEFT JOIN `savvy-gtm-analytics.FinTrx_data.Firm_historicals` h
    ON h.RIA_INVESTOR_CRD_ID = COALESCE(c.PRIMARY_FIRM, c.PRIMARY_RIA, c.PRIMARY_BD)
    AND (
      h.YEAR < ce.contact_year 
      OR (h.YEAR = ce.contact_year AND h.MONTH < ce.contact_month)
    )
),
-- Get team data (current state only)
team_data AS (
  SELECT DISTINCT
    ce.rep_crd,
    ce.contact_date,
    FIRST_VALUE(t.AUM) OVER (
      PARTITION BY ce.rep_crd, ce.contact_date
      ORDER BY t.AUM DESC
    ) as team_aum
  FROM contact_events ce
  INNER JOIN `savvy-gtm-analytics.FinTrx_data.ria_contacts_current` c
    ON c.RIA_CONTACT_CRD_ID = ce.rep_crd
  INNER JOIN `savvy-gtm-analytics.FinTrx_data.private_wealth_teams_ps` t
    ON t.ID IN (c.WEALTH_TEAM_ID_1, c.WEALTH_TEAM_ID_2, c.WEALTH_TEAM_ID_3)
)
SELECT 
  ce.rep_crd,
  ce.contact_date,
  c.RIA_CONTACT_PREFERRED_NAME,
  COALESCE(td.team_aum, fs.TOTAL_AUM, c.PRIMARY_FIRM_TOTAL_AUM) as aum,
  c.INDUSTRY_TENURE_MONTHS,
  c.PRODUCING_ADVISOR,
  -- Add more features as needed
FROM contact_events ce
INNER JOIN `savvy-gtm-analytics.FinTrx_data.ria_contacts_current` c
  ON c.RIA_CONTACT_CRD_ID = ce.rep_crd
LEFT JOIN firm_snapshots fs 
  ON fs.rep_crd = ce.rep_crd 
  AND fs.contact_date = ce.contact_date
  AND fs.rn = 1
LEFT JOIN team_data td
  ON td.rep_crd = ce.rep_crd
  AND td.contact_date = ce.contact_date;


-- ============================================================================
-- TEMPLATE 12: Calculate AUM Growth Rate from Historical Snapshots
-- ============================================================================
-- Use case: Calculate year-over-year AUM growth for a firm
-- ✅ PIT POSSIBLE - Uses Firm_historicals

WITH firm_snapshots AS (
  SELECT 
    RIA_INVESTOR_CRD_ID,
    YEAR,
    MONTH,
    TOTAL_AUM,
    LAG(TOTAL_AUM) OVER (
      PARTITION BY RIA_INVESTOR_CRD_ID
      ORDER BY YEAR, MONTH
    ) as prev_aum,
    LAG(TOTAL_AUM, 12) OVER (
      PARTITION BY RIA_INVESTOR_CRD_ID
      ORDER BY YEAR, MONTH
    ) as aum_12_months_ago
  FROM `savvy-gtm-analytics.FinTrx_data.Firm_historicals`
  WHERE TOTAL_AUM IS NOT NULL
)
SELECT 
  RIA_INVESTOR_CRD_ID,
  YEAR,
  MONTH,
  TOTAL_AUM,
  prev_aum,
  aum_12_months_ago,
  CASE 
    WHEN prev_aum > 0 
    THEN (TOTAL_AUM - prev_aum) / prev_aum * 100
    ELSE NULL
  END as mom_growth_pct,
  CASE 
    WHEN aum_12_months_ago > 0 
    THEN (TOTAL_AUM - aum_12_months_ago) / aum_12_months_ago * 100
    ELSE NULL
  END as yoy_growth_pct
FROM firm_snapshots
ORDER BY RIA_INVESTOR_CRD_ID, YEAR DESC, MONTH DESC;


-- ============================================================================
-- TEMPLATE 13: Check for Recent News Mentions (PIT)
-- ============================================================================
-- Use case: Find contacts with news mentions in the 6 months before contact
-- ⚠️ PARTIAL PIT - news_ps may not have dates, check schema first

WITH contact_event AS (
  SELECT 
    12345 AS rep_crd,
    DATE('2024-07-01') AS contact_date,
    DATE_SUB(DATE('2024-07-01'), INTERVAL 6 MONTH) AS lookback_date
)
SELECT 
  cn.*,
  n.written_at,  -- Adjust field name based on actual schema
  n.type as news_type,
  n.title,
  DATE_DIFF(ce.contact_date, DATE(n.written_at), DAY) as days_before_contact
FROM `savvy-gtm-analytics.FinTrx_data.ria_contact_news` cn
INNER JOIN `savvy-gtm-analytics.FinTrx_data.news_ps` n
  ON cn.article_id = n.ID  -- Adjust field names as needed
CROSS JOIN contact_event ce
WHERE cn.RIA_CONTACT_CRD_ID = ce.rep_crd
  AND DATE(n.written_at) >= ce.lookback_date
  AND DATE(n.written_at) < ce.contact_date
ORDER BY n.written_at DESC;


-- ============================================================================
-- ⚠️ TEMPLATES FOR FIELDS WHERE PIT IS NOT POSSIBLE
-- ============================================================================
-- These queries use current state only (small data leakage risk)

-- Get Licenses (Current State Only)
-- ❌ PIT NOT POSSIBLE - Only current state in ria_contacts_current
SELECT 
  RIA_CONTACT_CRD_ID,
  REP_LICENSES,  -- STRING containing JSON array
  ARRAY_LENGTH(JSON_EXTRACT_ARRAY(REP_LICENSES)) as num_licenses,
  CASE WHEN REP_LICENSES LIKE '%Series 7%' THEN TRUE ELSE FALSE END as has_series_7,
  CASE WHEN REP_LICENSES LIKE '%Series 65%' THEN TRUE ELSE FALSE END as has_series_65
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
WHERE RIA_CONTACT_CRD_ID = 12345;

-- Get Team AUM (Current State Only)
-- ❌ PIT NOT POSSIBLE - Only current state in private_wealth_teams_ps
SELECT 
  c.RIA_CONTACT_CRD_ID,
  t.AUM as team_aum
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current` c
INNER JOIN `savvy-gtm-analytics.FinTrx_data.private_wealth_teams_ps` t
  ON c.WEALTH_TEAM_ID_1 = t.ID
WHERE c.RIA_CONTACT_CRD_ID = 12345
  AND t.AUM IS NOT NULL;

-- Get Rep AUM (Current State Only, but 99% NULL)
-- ❌ PIT NOT POSSIBLE - Only current state, and 99.1% NULL anyway
SELECT 
  RIA_CONTACT_CRD_ID,
  REP_AUM
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
WHERE RIA_CONTACT_CRD_ID = 12345
  AND REP_AUM IS NOT NULL;  -- Only 0.9% of contacts have this


-- ============================================================================
-- JSON String Field Parsing Examples
-- ============================================================================
-- Many fields are STRING type containing JSON arrays, not actual ARRAY type

-- Extract licenses as array
SELECT 
  RIA_CONTACT_CRD_ID,
  JSON_EXTRACT_ARRAY(REP_LICENSES) as licenses_array
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
WHERE REP_LICENSES IS NOT NULL;

-- Count licenses
SELECT 
  RIA_CONTACT_CRD_ID,
  ARRAY_LENGTH(JSON_EXTRACT_ARRAY(REP_LICENSES)) as num_licenses
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
WHERE REP_LICENSES IS NOT NULL;

-- Check for specific license
SELECT *
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
WHERE REP_LICENSES LIKE '%Series 7%';

-- Extract entity classifications
SELECT 
  CRD_ID,
  JSON_EXTRACT_ARRAY(ENTITY_CLASSIFICATION) as classifications
FROM `savvy-gtm-analytics.FinTrx_data.ria_firms_current`
WHERE ENTITY_CLASSIFICATION IS NOT NULL;

-- Extract registered locations
SELECT 
  RIA_CONTACT_CRD_ID,
  JSON_EXTRACT_ARRAY(RIA_REGISTERED_LOCATIONS) as states
FROM `savvy-gtm-analytics.FinTrx_data.ria_contacts_current`
WHERE RIA_REGISTERED_LOCATIONS IS NOT NULL;

