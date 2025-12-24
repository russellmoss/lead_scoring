"""
Phase 0: Environment Setup and Preflight Validation

This phase validates:
1. Python dependencies
2. BigQuery connectivity
3. Dataset access permissions
4. Directory structure
5. Data volume validation
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")))

# Import ExecutionLogger and constants
from utils.execution_logger import ExecutionLogger
from config.constants import (
    BASE_DIR,
    PROJECT_ID,
    LOCATION,
    DATASET_FINTRX,
    DATASET_SALESFORCE
)


def run_phase_0() -> bool:
    """Execute Phase 0: Environment Setup & Preflight."""
    
    logger = ExecutionLogger(BASE_DIR)
    logger.start_phase("0", "Environment Setup & Preflight")
    
    # Track all gates
    all_gates_passed = True
    
    # =========================================================================
    # STEP 0.1: Check Python Dependencies
    # =========================================================================
    logger.log_action("Checking Python dependencies")
    
    required_packages = [
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("xgboost", "xgboost"),
        ("sklearn", "sklearn"),
        ("google.cloud.bigquery", "google.cloud.bigquery"),
        ("shap", "shap"),
        ("matplotlib", "matplotlib"),
        ("seaborn", "seaborn"),
        ("scipy", "scipy"),
        ("yaml", "yaml"),
    ]
    
    missing = []
    for package, import_name in required_packages:
        try:
            __import__(import_name)
            logger.log_metric(f"{package}", "Installed")
        except ImportError:
            logger.log_warning(f"{package} - MISSING")
            missing.append(package)
    
    gate_0_1 = len(missing) == 0
    logger.log_gate(
        "G0.1", "Python Dependencies",
        passed=gate_0_1,
        expected="All packages installed",
        actual=f"{len(required_packages) - len(missing)}/{len(required_packages)} installed"
    )
    
    if missing:
        logger.log_warning(
            f"Missing packages: {', '.join(missing)}",
            action_taken="Install with: pip install " + " ".join(missing)
        )
        all_gates_passed = False
    
    # =========================================================================
    # STEP 0.2: Test BigQuery Connectivity
    # =========================================================================
    logger.log_action("Testing BigQuery connectivity")
    
    client = None
    try:
        from google.cloud import bigquery
        
        client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
        
        # Test query
        test_query = "SELECT 1 as test"
        result = list(client.query(test_query).result())
        
        if result and result[0].test == 1:
            logger.log_metric("BigQuery Connection", "Successful")
            logger.log_metric("Project", PROJECT_ID)
            logger.log_metric("Location", LOCATION)
            gate_0_2 = True
        else:
            logger.log_error("BigQuery query returned unexpected result")
            gate_0_2 = False
            all_gates_passed = False
            
    except Exception as e:
        logger.log_error(f"BigQuery connection failed: {str(e)}", exception=e)
        gate_0_2 = False
        all_gates_passed = False
    
    logger.log_gate(
        "G0.2", "BigQuery Connectivity",
        passed=gate_0_2,
        expected="Connection successful",
        actual="Connected" if gate_0_2 else "Failed"
    )
    
    # =========================================================================
    # STEP 0.3: Validate Dataset Access
    # =========================================================================
    logger.log_action("Validating dataset access")
    
    datasets_to_check = [
        (DATASET_FINTRX, "contact_registered_employment_history"),
        (DATASET_FINTRX, "Firm_historicals"),
        (DATASET_FINTRX, "ria_contacts_current"),
        (DATASET_SALESFORCE, "Lead"),
        (DATASET_SALESFORCE, "broker_protocol_members"),
    ]
    
    accessible = 0
    if client:
        for dataset, table in datasets_to_check:
            try:
                query = f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.{dataset}.{table}` LIMIT 1"
                result = list(client.query(query).result())
                logger.log_metric(f"{dataset}.{table}", "Accessible")
                accessible += 1
            except Exception as e:
                logger.log_error(f"{dataset}.{table} - {str(e)[:100]}")
    
    gate_0_3 = accessible == len(datasets_to_check) if client else False
    logger.log_gate(
        "G0.3", "Dataset Access",
        passed=gate_0_3,
        expected=f"{len(datasets_to_check)}/{len(datasets_to_check)} datasets accessible",
        actual=f"{accessible}/{len(datasets_to_check)} accessible"
    )
    
    if not gate_0_3:
        all_gates_passed = False
    
    # =========================================================================
    # STEP 0.4: Verify Directory Structure
    # =========================================================================
    logger.log_action("Verifying directory structure")
    
    directories = [
        "config",
        "data/raw",
        "data/processed",
        "data/splits",
        "data/exploration",
        "sql",
        "scripts",
        "utils",
        "models/v4.0.0",
        "reports",
        "tests"
    ]
    
    created = 0
    for dir_path in directories:
        full_path = BASE_DIR / dir_path
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            created += 1
        except Exception as e:
            logger.log_error(f"Failed to create {dir_path}: {str(e)}")
    
    logger.log_metric("Directories Created", f"{created}/{len(directories)}")
    
    gate_0_4 = created == len(directories)
    logger.log_gate(
        "G0.4", "Directory Structure",
        passed=gate_0_4,
        expected=f"{len(directories)} directories",
        actual=f"{created} created"
    )
    
    if not gate_0_4:
        all_gates_passed = False
    
    # =========================================================================
    # STEP 0.5: Check Data Volume
    # =========================================================================
    logger.log_action("Checking data volume")
    
    contacted_leads = 0
    if client:
        try:
            # Check lead volume with FA_CRD__c
            lead_query = """
            SELECT 
                COUNT(*) as contacted_leads
            FROM `savvy-gtm-analytics.SavvyGTMData.Lead`
            WHERE stage_entered_contacting__c IS NOT NULL
              AND FA_CRD__c IS NOT NULL
              AND stage_entered_contacting__c >= '2024-02-01'
            """
            result = list(client.query(lead_query).result())[0]
            contacted_leads = result.contacted_leads
            
            logger.log_metric("Contacted Leads (with FA_CRD__c)", f"{contacted_leads:,}")
            
        except Exception as e:
            logger.log_error(f"Data volume check failed: {str(e)}", exception=e)
            contacted_leads = 0
    
    gate_0_5 = contacted_leads >= 10000
    logger.log_gate(
        "G0.5", "Data Volume",
        passed=gate_0_5,
        expected=">= 10,000 contacted leads",
        actual=f"{contacted_leads:,} leads"
    )
    
    if not gate_0_5:
        all_gates_passed = False
    
    # =========================================================================
    # PHASE SUMMARY
    # =========================================================================
    status = logger.end_phase(next_steps=["Phase 1: Data Extraction & Target Definition"])
    
    return all_gates_passed and status in ["PASSED", "PASSED WITH WARNINGS"]


if __name__ == "__main__":
    success = run_phase_0()
    sys.exit(0 if success else 1)

