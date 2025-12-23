"""
Broker Protocol Automation Configuration
Update these values for your environment
"""

import os
from pathlib import Path

# ===== PROJECT PATHS =====
# Base directory for the project
PROJECT_ROOT = Path(r"C:\Users\russe\Documents\Lead Scoring\Broker_protocol")

# Input/output directories
DATA_DIR = PROJECT_ROOT / "data"
TEMP_DIR = PROJECT_ROOT / "temp"
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
for dir_path in [DATA_DIR, TEMP_DIR, OUTPUT_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ===== BIGQUERY SETTINGS =====
GCP_PROJECT_ID = "savvy-gtm-analytics"
FINTRX_DATASET = "FinTrx_data_CA"
OUTPUT_DATASET = "SavvyGTMData"

# Table names
TABLE_MEMBERS = f"{GCP_PROJECT_ID}.{OUTPUT_DATASET}.broker_protocol_members"
TABLE_HISTORY = f"{GCP_PROJECT_ID}.{OUTPUT_DATASET}.broker_protocol_history"
TABLE_SCRAPE_LOG = f"{GCP_PROJECT_ID}.{OUTPUT_DATASET}.broker_protocol_scrape_log"
TABLE_MANUAL_MATCHES = f"{GCP_PROJECT_ID}.{OUTPUT_DATASET}.broker_protocol_manual_matches"

# FINTRX source tables
TABLE_FINTRX_FIRMS = f"{GCP_PROJECT_ID}.{FINTRX_DATASET}.ria_firms_current"
TABLE_FINTRX_CONTACTS = f"{GCP_PROJECT_ID}.{FINTRX_DATASET}.ria_contacts_current"

# ===== BROKER PROTOCOL SOURCE =====
BROKER_PROTOCOL_URL = "https://www.jsheld.com/markets-served/financial-services/broker-recruiting/the-broker-protocol"

# ===== MATCHING SETTINGS =====
# Confidence threshold for fuzzy matching (0.0 to 1.0)
DEFAULT_CONFIDENCE_THRESHOLD = 0.60

# Flag for manual review thresholds
MANUAL_REVIEW_THRESHOLD = 0.85  # Below this confidence, flag for review
HIGH_REVIEW_COUNT_ALERT = 100   # Alert if more than this many need review

# ===== MATCHING QUALITY TARGETS =====
TARGET_MATCH_RATE = 70.0  # Alert if match rate falls below this percentage

# ===== ALERT SETTINGS =====
# Email settings (for n8n)
ALERT_ENABLED = True
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "alerts@yourcompany.com")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "team@yourcompany.com")

# Slack settings (optional)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# ===== LOGGING =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True
LOG_FILE = LOGS_DIR / "broker_protocol_automation.log"

# ===== SCHEDULE =====
# For reference - actual schedule set in n8n
SCHEDULE_CRON = "0 9 1,15 * *"  # 9 AM ET on 1st and 15th of each month
SCHEDULE_DESCRIPTION = "Biweekly on 1st and 15th at 9 AM ET"

# ===== FILE NAMING =====
def get_scrape_run_id():
    """Generate unique scrape run ID"""
    from datetime import datetime
    return f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def get_temp_excel_path(filename="broker_protocol.xlsx"):
    """Get path for temporary Excel file"""
    return TEMP_DIR / filename

def get_parsed_csv_path():
    """Get path for parsed CSV output"""
    return OUTPUT_DIR / "broker_protocol_parsed_latest.csv"

def get_matched_csv_path():
    """Get path for matched CSV output"""
    return OUTPUT_DIR / "broker_protocol_matched_latest.csv"

def get_fintrx_export_path():
    """Get path for FINTRX firms export"""
    return OUTPUT_DIR / "fintrx_firms_latest.csv"

# ===== GOOGLE CLOUD AUTHENTICATION =====
# Path to service account key (for local development)
# In production (n8n), this is handled via service account credentials
GCP_SERVICE_ACCOUNT_KEY = os.getenv(
    "GCP_SERVICE_ACCOUNT_KEY", 
    str(PROJECT_ROOT / "service-account-key.json")
)

# Set environment variable for BigQuery client
if os.path.exists(GCP_SERVICE_ACCOUNT_KEY):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GCP_SERVICE_ACCOUNT_KEY

# ===== VALIDATION SETTINGS =====
# Minimum expected number of firms
MIN_EXPECTED_FIRMS = 2000
MAX_EXPECTED_FIRMS = 5000

# Date validation
MIN_JOIN_DATE_YEAR = 2000  # Earliest reasonable join date

# ===== FEATURE FLAGS =====
# Enable/disable features during development
ENABLE_BIGQUERY_WRITE = True  # Set to False for dry-run testing
ENABLE_CHANGE_TRACKING = True  # Track changes in history table
ENABLE_EMAIL_ALERTS = True     # Send email notifications
ENABLE_BACKUP = False          # Backup Excel files to Cloud Storage (optional)

# ===== DEVELOPMENT/DEBUG SETTINGS =====
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
VERBOSE = os.getenv("VERBOSE", "False").lower() == "true"

# Test mode - processes only first N firms
TEST_MODE = False
TEST_LIMIT = 100  # Number of firms to process in test mode

# ===== USAGE EXAMPLES =====
if __name__ == "__main__":
    print("=== Broker Protocol Automation Configuration ===")
    print(f"\nProject Root: {PROJECT_ROOT}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Temp Directory: {TEMP_DIR}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Logs Directory: {LOGS_DIR}")
    
    print(f"\n=== BigQuery Settings ===")
    print(f"Project: {GCP_PROJECT_ID}")
    print(f"FINTRX Dataset: {FINTRX_DATASET}")
    print(f"Output Dataset: {OUTPUT_DATASET}")
    print(f"Members Table: {TABLE_MEMBERS}")
    
    print(f"\n=== Matching Settings ===")
    print(f"Confidence Threshold: {DEFAULT_CONFIDENCE_THRESHOLD}")
    print(f"Manual Review Threshold: {MANUAL_REVIEW_THRESHOLD}")
    print(f"Target Match Rate: {TARGET_MATCH_RATE}%")
    
    print(f"\n=== Schedule ===")
    print(f"Cron: {SCHEDULE_CRON}")
    print(f"Description: {SCHEDULE_DESCRIPTION}")
    
    print(f"\n=== File Paths ===")
    print(f"Temp Excel: {get_temp_excel_path()}")
    print(f"Parsed CSV: {get_parsed_csv_path()}")
    print(f"Matched CSV: {get_matched_csv_path()}")
    print(f"FINTRX Export: {get_fintrx_export_path()}")
    
    print(f"\n=== Feature Flags ===")
    print(f"BigQuery Write: {ENABLE_BIGQUERY_WRITE}")
    print(f"Change Tracking: {ENABLE_CHANGE_TRACKING}")
    print(f"Email Alerts: {ENABLE_EMAIL_ALERTS}")
    print(f"Debug Mode: {DEBUG_MODE}")
    print(f"Test Mode: {TEST_MODE}")
