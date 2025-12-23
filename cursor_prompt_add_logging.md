# Cursor.ai Prompt: Add Execution Logging & Version-2 Directory Structure

## Target File
`C:\Users\russe\Documents\Lead Scoring\leadscoring_plan.md`

---

## Prompt for Cursor.ai

```
I need you to edit my lead scoring agentic plan at C:\Users\russe\Documents\Lead Scoring\leadscoring_plan.md to add two critical features:

1. **Comprehensive Execution Logging** - A running log document that gets updated as each phase executes
2. **Version-2 Directory Structure** - All new files should be created in a dedicated Version-2 folder

## REQUIREMENT 1: EXECUTION LOGGING SYSTEM

Add a new section called "## Execution Logging System" immediately after the Table of Contents. This section should define:

### 1.1 Log File Location and Format

```markdown
## Execution Logging System

### Log File

**Location:** `C:\Users\russe\Documents\Lead Scoring\Version-2\EXECUTION_LOG.md`

This log is a **living document** that gets appended to as each phase executes. It provides:
- Complete audit trail of model development
- What was done in each phase
- What we learned (insights, surprises, issues)
- All file paths created
- Validation gate results
- Decisions made and why

**CRITICAL:** Every phase MUST append to this log before moving to the next phase.

### Log Entry Template

Each phase should append an entry using this exact format:

```markdown
---

## Phase [X.X]: [Phase Name]

**Executed:** [YYYY-MM-DD HH:MM]
**Duration:** [X minutes]
**Status:** [✅ PASSED / ⚠️ PASSED WITH WARNINGS / ❌ FAILED]

### What We Did
[Bullet points of actions taken]

### Files Created
| File | Path | Purpose |
|------|------|---------|
| [name] | `Version-2/[path]` | [description] |

### Validation Gates
| Gate ID | Check | Result | Notes |
|---------|-------|--------|-------|
| [id] | [check] | [✅/⚠️/❌] | [notes] |

### Key Metrics
[Relevant numbers from this phase]

### What We Learned
[Insights, surprises, issues discovered]

### Decisions Made
[Any decisions and rationale]

### Next Steps
[What needs to happen in the next phase]

---
```
```

### 1.2 Logging Implementation

Add this Python module to be used by all phases:

```python
# =============================================================================
# EXECUTION LOGGER MODULE
# =============================================================================
# Location: C:\Users\russe\Documents\Lead Scoring\Version-2\utils\execution_logger.py
"""
Execution Logger for Lead Scoring Model Development

This module provides consistent logging across all phases of model development.
Each phase should use this logger to append entries to EXECUTION_LOG.md.

Usage:
    from utils.execution_logger import ExecutionLogger
    
    logger = ExecutionLogger()
    logger.start_phase("1.1", "Feature Engineering")
    
    # ... do work ...
    
    logger.log_file_created("features.csv", "Version-2/data/features.csv", "Training features")
    logger.log_validation_gate("G1.1.1", "PIT Integrity", True, "Zero leakage detected")
    logger.log_metric("Total Leads", 45000)
    logger.log_learning("Conversion rate is higher in 2025 (4.37%) vs 2024 (3.96%)")
    logger.log_decision("Using 60-day test window", "Provides sufficient test samples while maximizing training data")
    
    logger.end_phase(status="PASSED", next_steps=["Proceed to Phase 1.2"])
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class ExecutionLogger:
    def __init__(self, 
                 log_path: str = r"C:\Users\russe\Documents\Lead Scoring\Version-2\EXECUTION_LOG.md",
                 version: str = "v3"):
        """
        Initialize the execution logger.
        
        Args:
            log_path: Path to the execution log file
            version: Model version being developed
        """
        self.log_path = Path(log_path)
        self.version = version
        self.current_phase = None
        self.phase_start_time = None
        self.files_created = []
        self.validation_gates = []
        self.metrics = {}
        self.learnings = []
        self.decisions = []
        
        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize log file if it doesn't exist
        if not self.log_path.exists():
            self._initialize_log()
    
    def _initialize_log(self):
        """Create the initial log file with header."""
        header = f"""# Lead Scoring Model Execution Log

**Model Version:** {self.version}
**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Base Directory:** `C:\\Users\\russe\\Documents\\Lead Scoring\\Version-2`

---

## Execution Summary

| Phase | Status | Duration | Key Outcome |
|-------|--------|----------|-------------|

---

## Detailed Phase Logs

"""
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write(header)
        
        print(f"📝 Initialized execution log: {self.log_path}")
    
    def start_phase(self, phase_id: str, phase_name: str):
        """
        Start logging a new phase.
        
        Args:
            phase_id: Phase identifier (e.g., "1.1", "0.0")
            phase_name: Human-readable phase name
        """
        self.current_phase = f"{phase_id}: {phase_name}"
        self.phase_start_time = datetime.now()
        self.files_created = []
        self.validation_gates = []
        self.metrics = {}
        self.learnings = []
        self.decisions = []
        
        print(f"\n{'='*60}")
        print(f"📍 STARTING Phase {self.current_phase}")
        print(f"   Time: {self.phase_start_time.strftime('%Y-%m-%d %H:%M')}")
        print('='*60)
    
    def log_file_created(self, filename: str, filepath: str, purpose: str):
        """Log a file that was created during this phase."""
        self.files_created.append({
            'filename': filename,
            'filepath': filepath,
            'purpose': purpose
        })
        print(f"   📄 Created: {filepath}")
    
    def log_validation_gate(self, gate_id: str, check: str, passed: bool, notes: str = ""):
        """Log a validation gate result."""
        status = "✅ PASSED" if passed else "❌ FAILED"
        self.validation_gates.append({
            'gate_id': gate_id,
            'check': check,
            'passed': passed,
            'status': status,
            'notes': notes
        })
        print(f"   {'✅' if passed else '❌'} {gate_id}: {check} - {notes}")
    
    def log_metric(self, name: str, value: Any):
        """Log a key metric from this phase."""
        self.metrics[name] = value
        print(f"   📊 {name}: {value}")
    
    def log_learning(self, learning: str):
        """Log an insight or learning from this phase."""
        self.learnings.append(learning)
        print(f"   💡 Learning: {learning}")
    
    def log_decision(self, decision: str, rationale: str):
        """Log a decision made during this phase."""
        self.decisions.append({
            'decision': decision,
            'rationale': rationale
        })
        print(f"   🎯 Decision: {decision}")
    
    def log_action(self, action: str):
        """Log an action taken (for the 'What We Did' section)."""
        if not hasattr(self, 'actions'):
            self.actions = []
        self.actions.append(action)
        print(f"   ▶️ {action}")
    
    def end_phase(self, 
                  status: str = "PASSED",
                  next_steps: List[str] = None,
                  additional_notes: str = ""):
        """
        End the current phase and write to log.
        
        Args:
            status: "PASSED", "PASSED WITH WARNINGS", or "FAILED"
            next_steps: List of next steps for following phases
            additional_notes: Any additional notes to include
        """
        if not self.current_phase:
            raise ValueError("No phase started. Call start_phase() first.")
        
        end_time = datetime.now()
        duration_minutes = (end_time - self.phase_start_time).total_seconds() / 60
        
        # Determine status emoji
        status_emoji = "✅" if status == "PASSED" else ("⚠️" if "WARNING" in status else "❌")
        
        # Build the log entry
        entry = f"""
---

## Phase {self.current_phase}

**Executed:** {self.phase_start_time.strftime('%Y-%m-%d %H:%M')}
**Duration:** {duration_minutes:.1f} minutes
**Status:** {status_emoji} {status}

### What We Did
"""
        # Add actions
        if hasattr(self, 'actions') and self.actions:
            for action in self.actions:
                entry += f"- {action}\n"
        else:
            entry += "- [No actions logged]\n"
        
        # Add files created
        entry += "\n### Files Created\n"
        if self.files_created:
            entry += "| File | Path | Purpose |\n|------|------|---------|"
            for f in self.files_created:
                entry += f"\n| {f['filename']} | `{f['filepath']}` | {f['purpose']} |"
            entry += "\n"
        else:
            entry += "*No files created in this phase*\n"
        
        # Add validation gates
        entry += "\n### Validation Gates\n"
        if self.validation_gates:
            entry += "| Gate ID | Check | Result | Notes |\n|---------|-------|--------|-------|"
            for g in self.validation_gates:
                entry += f"\n| {g['gate_id']} | {g['check']} | {g['status']} | {g['notes']} |"
            entry += "\n"
        else:
            entry += "*No validation gates in this phase*\n"
        
        # Add metrics
        entry += "\n### Key Metrics\n"
        if self.metrics:
            for name, value in self.metrics.items():
                entry += f"- **{name}:** {value}\n"
        else:
            entry += "*No metrics logged*\n"
        
        # Add learnings
        entry += "\n### What We Learned\n"
        if self.learnings:
            for learning in self.learnings:
                entry += f"- {learning}\n"
        else:
            entry += "*No specific learnings logged*\n"
        
        # Add decisions
        entry += "\n### Decisions Made\n"
        if self.decisions:
            for d in self.decisions:
                entry += f"- **{d['decision']}** — {d['rationale']}\n"
        else:
            entry += "*No decisions logged*\n"
        
        # Add additional notes
        if additional_notes:
            entry += f"\n### Additional Notes\n{additional_notes}\n"
        
        # Add next steps
        entry += "\n### Next Steps\n"
        if next_steps:
            for step in next_steps:
                entry += f"- {step}\n"
        else:
            entry += "- Proceed to next phase\n"
        
        entry += "\n---\n"
        
        # Append to log file
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(entry)
        
        # Update summary table (read, find table, update)
        self._update_summary_table(status, duration_minutes)
        
        print(f"\n{'='*60}")
        print(f"✅ COMPLETED Phase {self.current_phase}")
        print(f"   Status: {status}")
        print(f"   Duration: {duration_minutes:.1f} minutes")
        print(f"   Log updated: {self.log_path}")
        print('='*60 + "\n")
        
        # Reset for next phase
        self.current_phase = None
        self.phase_start_time = None
        self.actions = []
    
    def _update_summary_table(self, status: str, duration: float):
        """Update the summary table at the top of the log."""
        # Read current log
        with open(self.log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the summary table and add a row
        table_marker = "| Phase | Status | Duration | Key Outcome |"
        if table_marker in content:
            # Determine key outcome from metrics or learnings
            if self.metrics:
                key_outcome = list(self.metrics.items())[0]
                outcome_str = f"{key_outcome[0]}: {key_outcome[1]}"
            elif self.learnings:
                outcome_str = self.learnings[0][:50] + "..."
            else:
                outcome_str = status
            
            status_emoji = "✅" if status == "PASSED" else ("⚠️" if "WARNING" in status else "❌")
            new_row = f"| {self.current_phase} | {status_emoji} {status} | {duration:.1f}m | {outcome_str} |"
            
            # Insert after the header row
            parts = content.split(table_marker)
            if len(parts) == 2:
                # Find the end of the table header row
                header_end = parts[1].find('\n')
                if header_end != -1:
                    # Insert the new row after the header separator row
                    rest = parts[1][header_end+1:]
                    separator_end = rest.find('\n')
                    if separator_end != -1:
                        new_content = parts[0] + table_marker + parts[1][:header_end+1] + rest[:separator_end+1] + new_row + "\n" + rest[separator_end+1:]
                        with open(self.log_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)


# Convenience function for quick logging
def log_phase_simple(phase_id: str, 
                     phase_name: str, 
                     actions: List[str],
                     files: List[Dict],
                     gates: List[Dict],
                     metrics: Dict,
                     learnings: List[str],
                     status: str = "PASSED"):
    """
    Simple one-call logging for a phase.
    
    Example:
        log_phase_simple(
            phase_id="1.1",
            phase_name="Feature Engineering",
            actions=["Created feature table", "Ran PIT audit"],
            files=[{"name": "features.csv", "path": "data/features.csv", "purpose": "Training data"}],
            gates=[{"id": "G1.1.1", "check": "PIT", "passed": True}],
            metrics={"Total Leads": 45000, "Positive Rate": "4.2%"},
            learnings=["2025 data has higher conversion rate"],
            status="PASSED"
        )
    """
    logger = ExecutionLogger()
    logger.start_phase(phase_id, phase_name)
    
    for action in actions:
        logger.log_action(action)
    
    for f in files:
        logger.log_file_created(f['name'], f['path'], f['purpose'])
    
    for g in gates:
        logger.log_validation_gate(g['id'], g['check'], g['passed'], g.get('notes', ''))
    
    for name, value in metrics.items():
        logger.log_metric(name, value)
    
    for learning in learnings:
        logger.log_learning(learning)
    
    logger.end_phase(status=status)


if __name__ == "__main__":
    # Test the logger
    logger = ExecutionLogger()
    logger.start_phase("TEST", "Logger Test")
    logger.log_action("Testing the logger")
    logger.log_file_created("test.txt", "Version-2/test.txt", "Test file")
    logger.log_validation_gate("G0.0.1", "Test Gate", True, "Test passed")
    logger.log_metric("Test Metric", 42)
    logger.log_learning("The logger works!")
    logger.end_phase(status="PASSED", next_steps=["Deploy logger to all phases"])
```

### 1.3 Phase Integration

Update EVERY phase in the plan to use the ExecutionLogger. Add this pattern at the start and end of each phase's code:

```python
# At the START of each phase:
from utils.execution_logger import ExecutionLogger
logger = ExecutionLogger()
logger.start_phase("[PHASE_ID]", "[PHASE_NAME]")

# Throughout the phase, log actions, files, gates, metrics, learnings:
logger.log_action("Queried BigQuery for lead data")
logger.log_file_created("features.csv", "Version-2/data/features.csv", "Feature matrix")
logger.log_validation_gate("G1.1.1", "PIT Integrity", passed=True, notes="Zero leakage")
logger.log_metric("Total Leads", 45000)
logger.log_learning("Conversion rate improved in 2025")

# At the END of each phase:
logger.end_phase(
    status="PASSED",  # or "PASSED WITH WARNINGS" or "FAILED"
    next_steps=["Proceed to Phase X.Y", "Review feature importance"]
)
```


## REQUIREMENT 2: VERSION-2 DIRECTORY STRUCTURE

Add a new section called "## Version-2 Directory Structure" after the Execution Logging section. Define the complete directory structure:

```markdown
## Version-2 Directory Structure

All files for this model version MUST be created in:
`C:\Users\russe\Documents\Lead Scoring\Version-2`

### Directory Layout

```
C:\Users\russe\Documents\Lead Scoring\Version-2\
│
├── EXECUTION_LOG.md                    # Living log of all phases (auto-generated)
├── date_config.json                    # Date configuration from Phase 0.0
│
├── utils\                              # Utility modules
│   ├── __init__.py
│   ├── execution_logger.py             # Logging module
│   ├── date_configuration.py           # DateConfiguration class
│   └── feature_engineering.py          # Engineered feature calculations
│
├── data\                               # Data artifacts
│   ├── raw\                            # Raw data exports from BigQuery
│   │   ├── leads_raw.csv
│   │   └── firm_historicals_sample.csv
│   ├── features\                       # Feature matrices
│   │   ├── features_train.parquet
│   │   ├── features_test.parquet
│   │   └── features_all.parquet
│   └── scored\                         # Scoring outputs
│       └── lead_scores_YYYYMMDD.csv
│
├── models\                             # Model artifacts
│   ├── v3-boosted-YYYYMMDD-HASH\       # Versioned model directory
│   │   ├── model.pkl                   # Trained model
│   │   ├── model_calibrated.pkl        # Calibrated model
│   │   ├── feature_names.json          # Feature list
│   │   ├── hyperparameters.json        # Tuned hyperparameters
│   │   ├── calibration_lookup.csv      # Score calibration table
│   │   └── model_card.md               # Model documentation
│   └── registry.json                   # Model registry
│
├── reports\                            # Analysis reports
│   ├── phase_0_data_assessment.md
│   ├── phase_1_feature_analysis.md
│   ├── phase_3_feature_selection.md
│   ├── phase_5_evaluation.md
│   ├── phase_8_temporal_backtest.md
│   └── shap\                           # SHAP analysis outputs
│       ├── shap_summary.png
│       └── shap_values.csv
│
├── notebooks\                          # Jupyter notebooks (optional)
│   └── exploratory_analysis.ipynb
│
├── sql\                                # SQL queries used
│   ├── feature_engineering.sql
│   ├── training_data.sql
│   └── scoring.sql
│
└── inference\                          # Production inference code
    ├── lead_scorer_v3.py               # Inference pipeline
    ├── batch_scoring.py                # Batch scoring script
    └── salesforce_sync.py              # Salesforce integration
```

### Directory Creation

Add this to Phase 0.0 to create the directory structure:

```python
# Create Version-2 directory structure
import os
from pathlib import Path

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")

DIRECTORIES = [
    BASE_DIR / "utils",
    BASE_DIR / "data" / "raw",
    BASE_DIR / "data" / "features",
    BASE_DIR / "data" / "scored",
    BASE_DIR / "models",
    BASE_DIR / "reports" / "shap",
    BASE_DIR / "notebooks",
    BASE_DIR / "sql",
    BASE_DIR / "inference",
]

def create_directory_structure():
    """Create the Version-2 directory structure."""
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    # Create __init__.py in utils
    init_file = BASE_DIR / "utils" / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# Lead Scoring v3 Utilities\n")
    
    print(f"\n📁 Directory structure created at: {BASE_DIR}")

if __name__ == "__main__":
    create_directory_structure()
```

### Path Constants

Add this constants module that all phases should import:

```python
# C:\Users\russe\Documents\Lead Scoring\Version-2\utils\paths.py
"""
Centralized path constants for Version-2 model development.

Usage:
    from utils.paths import PATHS
    
    features_path = PATHS['FEATURES_DIR'] / 'features_train.parquet'
"""

from pathlib import Path

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")

PATHS = {
    # Base
    'BASE': BASE_DIR,
    'EXECUTION_LOG': BASE_DIR / 'EXECUTION_LOG.md',
    'DATE_CONFIG': BASE_DIR / 'date_config.json',
    
    # Utils
    'UTILS_DIR': BASE_DIR / 'utils',
    
    # Data
    'DATA_DIR': BASE_DIR / 'data',
    'RAW_DATA_DIR': BASE_DIR / 'data' / 'raw',
    'FEATURES_DIR': BASE_DIR / 'data' / 'features',
    'SCORED_DIR': BASE_DIR / 'data' / 'scored',
    
    # Models
    'MODELS_DIR': BASE_DIR / 'models',
    'REGISTRY': BASE_DIR / 'models' / 'registry.json',
    
    # Reports
    'REPORTS_DIR': BASE_DIR / 'reports',
    'SHAP_DIR': BASE_DIR / 'reports' / 'shap',
    
    # SQL
    'SQL_DIR': BASE_DIR / 'sql',
    
    # Inference
    'INFERENCE_DIR': BASE_DIR / 'inference',
}

def get_model_dir(version_id: str) -> Path:
    """Get the directory for a specific model version."""
    return PATHS['MODELS_DIR'] / version_id

def get_report_path(phase: str) -> Path:
    """Get the report path for a specific phase."""
    return PATHS['REPORTS_DIR'] / f"phase_{phase}_report.md"
```
```


## REQUIREMENT 3: UPDATE PHASE 0.0 

Update Phase 0.0 to:
1. Create the directory structure first
2. Initialize the execution log
3. Save the date configuration to the Version-2 directory

```python
# Phase 0.0: Dynamic Date Configuration (UPDATED)

import sys
from pathlib import Path

# Add Version-2 to path for imports
VERSION_2_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")
sys.path.insert(0, str(VERSION_2_DIR))

from datetime import datetime, timedelta
import json

# Step 1: Create directory structure
def create_directory_structure():
    """Create Version-2 directory structure."""
    directories = [
        VERSION_2_DIR / "utils",
        VERSION_2_DIR / "data" / "raw",
        VERSION_2_DIR / "data" / "features",
        VERSION_2_DIR / "data" / "scored",
        VERSION_2_DIR / "models",
        VERSION_2_DIR / "reports" / "shap",
        VERSION_2_DIR / "notebooks",
        VERSION_2_DIR / "sql",
        VERSION_2_DIR / "inference",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py
    (VERSION_2_DIR / "utils" / "__init__.py").write_text("# Lead Scoring v3 Utilities\n")
    
    print(f"✅ Directory structure created: {VERSION_2_DIR}")

# Step 2: Initialize execution logger (copy the module to utils/)
# [The ExecutionLogger class defined above should be saved to utils/execution_logger.py]

# Step 3: Run DateConfiguration and save
class DateConfiguration:
    # ... [existing DateConfiguration class code] ...
    pass

def run_phase_0_0():
    """Execute Phase 0.0: Dynamic Date Configuration"""
    
    # Import logger after creating directories
    create_directory_structure()
    
    # Now we can import from utils
    from utils.execution_logger import ExecutionLogger
    
    logger = ExecutionLogger()
    logger.start_phase("0.0", "Dynamic Date Configuration")
    
    # Log directory creation
    logger.log_action("Created Version-2 directory structure")
    logger.log_file_created("Version-2/", str(VERSION_2_DIR), "Base directory for model v3")
    
    # Create and validate date configuration
    logger.log_action("Calculating dynamic dates based on execution date")
    config = DateConfiguration()
    
    try:
        config.validate()
        logger.log_validation_gate("G0.0.1", "Date Configuration Valid", True, "All dates in correct order")
    except ValueError as e:
        logger.log_validation_gate("G0.0.1", "Date Configuration Valid", False, str(e))
        logger.end_phase(status="FAILED")
        raise
    
    # Save configuration
    config_path = VERSION_2_DIR / "date_config.json"
    with open(config_path, 'w') as f:
        json.dump(config.to_dict(), f, indent=2)
    
    logger.log_file_created("date_config.json", str(config_path), "Date configuration for all phases")
    
    # Log key metrics
    logger.log_metric("Execution Date", config.execution_date.strftime('%Y-%m-%d'))
    logger.log_metric("Training Start", config.training_start_date.strftime('%Y-%m-%d'))
    logger.log_metric("Training End", config.train_end_date.strftime('%Y-%m-%d'))
    logger.log_metric("Test Start", config.test_start_date.strftime('%Y-%m-%d'))
    logger.log_metric("Test End", config.test_end_date.strftime('%Y-%m-%d'))
    
    train_days = (config.train_end_date - config.training_start_date).days
    test_days = (config.test_end_date - config.test_start_date).days
    logger.log_metric("Training Days", train_days)
    logger.log_metric("Test Days", test_days)
    
    # Log learnings
    logger.log_learning(f"Training window covers {train_days} days ({train_days/30:.1f} months)")
    logger.log_learning(f"Firm data lag of {config.firm_data_lag_months} month(s) accounted for")
    
    # End phase
    logger.end_phase(
        status="PASSED",
        next_steps=[
            "Run Phase -1 pre-flight queries to verify data availability",
            "Proceed to Phase 0.1 Data Landscape Assessment"
        ]
    )
    
    config.print_summary()
    return config


if __name__ == "__main__":
    config = run_phase_0_0()
```


## REQUIREMENT 4: UPDATE ALL PHASES TO USE LOGGING

For each existing phase in the plan, add the logging pattern. Here's the template to add at the start and end of each phase's main execution code:

```python
# At the START of each phase's code block, add:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"C:\Users\russe\Documents\Lead Scoring\Version-2")))

from utils.execution_logger import ExecutionLogger
from utils.paths import PATHS

logger = ExecutionLogger()
logger.start_phase("[PHASE_ID]", "[PHASE_NAME]")

# ... existing phase code, with logger calls added throughout ...

# At the END of each phase's code block, add:
logger.end_phase(
    status="PASSED",  # Update based on actual results
    next_steps=["[Next phase or action]"]
)
```


## REQUIREMENT 5: ADD LOG REVIEW CHECKPOINTS

Add checkpoint reminders after key phases. Insert these as callout boxes:

```markdown
> **📝 LOG CHECKPOINT**
> 
> Before proceeding to the next phase, review the execution log:
> `C:\Users\russe\Documents\Lead Scoring\Version-2\EXECUTION_LOG.md`
> 
> Verify:
> - [ ] All validation gates passed
> - [ ] Files created in correct locations
> - [ ] Metrics look reasonable
> - [ ] No unexpected learnings that require investigation
```

Add these checkpoints after:
- Phase 0.0 (Date Configuration)
- Phase 1 (Feature Engineering) 
- Phase 4 (Model Training)
- Phase 5 (Model Evaluation)
- Phase 8 (Temporal Backtest)


## SUMMARY OF CHANGES

1. Add "## Execution Logging System" section after Table of Contents
2. Add "## Version-2 Directory Structure" section
3. Add ExecutionLogger class code to Phase 0.0
4. Add paths.py constants module definition
5. Update Phase 0.0 to create directories and initialize logging
6. Add logging pattern template for all phases
7. Add LOG CHECKPOINT callouts after key phases
8. Update all phase code blocks to use ExecutionLogger
9. Ensure all file paths reference Version-2 directory

When complete, the execution will:
- Create all files in `C:\Users\russe\Documents\Lead Scoring\Version-2\`
- Maintain a comprehensive log at `Version-2\EXECUTION_LOG.md`
- Provide complete audit trail of model development
- Make the development process fully reproducible
```

---

## How to Use This Prompt

1. Open Cursor.ai
2. Open `C:\Users\russe\Documents\Lead Scoring\leadscoring_plan.md`
3. Open Cursor's AI chat (Cmd/Ctrl + L)
4. Paste everything between the outer ``` markers above
5. Let Cursor make the changes
6. Review the diff before accepting

After this update, your plan will:
- Create all artifacts in a dedicated Version-2 folder
- Maintain a living EXECUTION_LOG.md as phases execute
- Provide complete traceability of the model development process
