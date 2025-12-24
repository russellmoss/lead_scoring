"""
Execution Logger Utility for Version 4 Lead Scoring Model

This module provides comprehensive logging for agentic model development.
Logs to:
1. EXECUTION_LOG.md (human-readable markdown)
2. Console (real-time feedback)
3. JSON files (machine-readable metrics)
"""

from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import pandas as pd


class ExecutionLogger:
    """
    Comprehensive logger for agentic model development.
    
    Logs to:
    1. EXECUTION_LOG.md (human-readable markdown)
    2. Console (real-time feedback)
    3. JSON files (machine-readable metrics)
    """
    
    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            base_dir = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")
        
        self.base_dir = base_dir
        self.log_file = base_dir / "EXECUTION_LOG.md"
        self.metrics_dir = base_dir / "data" / "exploration"
        self.current_phase = None
        self.phase_start_time = None
        self.gate_results = []
        self.decisions = []
        self.warnings = []
        self.errors = []
        
        # Initialize log file if not exists
        if not self.log_file.exists():
            self._initialize_log_file()
    
    def _initialize_log_file(self):
        """Initialize the execution log file."""
        header = f"""# Version 4 Lead Scoring Model - Execution Log

**Model Version**: 4.0.0  
**Started**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Status**: In Progress

---

## Execution Timeline

"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(header)
    
    def _append_to_log(self, content: str):
        """Append content to log file."""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(content)
    
    def start_phase(self, phase_id: str, phase_name: str):
        """Start a new phase and log it."""
        self.current_phase = phase_id
        self.phase_start_time = datetime.now()
        self.gate_results = []
        self.decisions = []
        self.warnings = []
        
        log_entry = f"""
---

## Phase {phase_id}: {phase_name}

**Started**: {self.phase_start_time.strftime("%Y-%m-%d %H:%M:%S")}  
**Status**: In Progress

### Actions

"""
        self._append_to_log(log_entry)
        print(f"\n{'='*70}")
        print(f"PHASE {phase_id}: {phase_name}")
        print(f"{'='*70}")
    
    def log_action(self, action: str, details: str = None):
        """Log an action taken."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        log_entry = f"- [{timestamp}] {action}\n"
        if details:
            log_entry += f"  - Details: {details}\n"
        
        self._append_to_log(log_entry)
        print(f"  -> {action}")
        if details:
            print(f"    {details}")
    
    def log_gate(self, gate_id: str, gate_name: str, passed: bool, 
                 expected: Any, actual: Any, notes: str = None):
        """Log a validation gate result."""
        status = "[PASSED]" if passed else "[FAILED]"
        
        gate_result = {
            "gate_id": gate_id,
            "gate_name": gate_name,
            "passed": passed,
            "expected": str(expected),
            "actual": str(actual),
            "notes": notes
        }
        self.gate_results.append(gate_result)
        
        log_entry = f"""
#### Gate {gate_id}: {gate_name}
- **Status**: {status}
- **Expected**: {expected}
- **Actual**: {actual}
"""
        if notes:
            log_entry += f"- **Notes**: {notes}\n"
        
        self._append_to_log(log_entry)
        print(f"  Gate {gate_id}: {status}")
        print(f"    Expected: {expected}, Actual: {actual}")
        
        if not passed:
            self.warnings.append(f"Gate {gate_id} failed: {gate_name}")
    
    def log_metric(self, metric_name: str, value: Any, context: str = None):
        """Log a metric value."""
        log_entry = f"- **{metric_name}**: {value}\n"
        if context:
            log_entry += f"  - Context: {context}\n"
        
        self._append_to_log(log_entry)
        print(f"  [METRIC] {metric_name}: {value}")
    
    def log_decision(self, decision: str, rationale: str, alternatives: List[str] = None):
        """Log a decision made during execution."""
        self.decisions.append({
            "decision": decision,
            "rationale": rationale,
            "alternatives": alternatives,
            "timestamp": datetime.now().isoformat()
        })
        
        log_entry = f"""
#### Decision Made
- **Decision**: {decision}
- **Rationale**: {rationale}
"""
        if alternatives:
            log_entry += f"- **Alternatives Considered**: {', '.join(alternatives)}\n"
        
        self._append_to_log(log_entry)
        print(f"  [DECISION] {decision}")
        print(f"     Rationale: {rationale}")
    
    def log_warning(self, warning: str, action_taken: str = None):
        """Log a warning."""
        self.warnings.append(warning)
        
        log_entry = f"""
**Warning**: {warning}
"""
        if action_taken:
            log_entry += f"- **Action Taken**: {action_taken}\n"
        log_entry += "\n"
        
        self._append_to_log(log_entry)
        print(f"  [WARNING] {warning}")
        if action_taken:
            print(f"     Action: {action_taken}")
    
    def log_error(self, error: str, exception: Exception = None):
        """Log an error."""
        self.errors.append({
            "error": error,
            "exception": str(exception) if exception else None,
            "timestamp": datetime.now().isoformat()
        })
        
        log_entry = f"""
**Error**: {error}
"""
        if exception:
            log_entry += f"- **Exception**: {str(exception)}\n"
        log_entry += "\n"
        
        self._append_to_log(log_entry)
        print(f"  [ERROR] {error}")
        if exception:
            print(f"     Exception: {str(exception)}")
    
    def log_dataframe_summary(self, df: pd.DataFrame, name: str):
        """Log summary statistics of a DataFrame."""
        log_entry = f"""
#### DataFrame: {name}
- **Shape**: {df.shape[0]:,} rows × {df.shape[1]} columns
- **Memory**: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB
- **Columns**: {', '.join(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}
"""
        if hasattr(df, 'target') or 'converted' in df.columns or 'target' in df.columns:
            target_col = 'converted' if 'converted' in df.columns else 'target'
            if target_col in df.columns:
                pos_rate = df[target_col].mean() * 100
                log_entry += f"- **Positive Class Rate**: {pos_rate:.2f}%\n"
        
        self._append_to_log(log_entry)
        print(f"  [DATA] {name}: {df.shape[0]:,} rows × {df.shape[1]} columns")
    
    def log_file_created(self, filename: str, filepath: str, description: str = None):
        """Log file creation."""
        log_entry = f"- **File Created**: `{filename}` at `{filepath}`\n"
        if description:
            log_entry += f"  - {description}\n"
        
        self._append_to_log(log_entry)
        print(f"  [FILE] Created: {filename}")
    
    def end_phase(self, next_steps: List[str] = None) -> str:
        """End the current phase and summarize."""
        duration = datetime.now() - self.phase_start_time
        duration_str = str(duration).split('.')[0]
        
        # Determine overall status
        if self.errors:
            status = "FAILED"
            status_emoji = "[FAILED]"
        elif self.warnings:
            status = "PASSED WITH WARNINGS"
            status_emoji = "[WARNING]"
        else:
            status = "PASSED"
            status_emoji = "[PASSED]"
        
        # Count gate results
        gates_passed = sum(1 for g in self.gate_results if g['passed'])
        gates_failed = len(self.gate_results) - gates_passed
        
        log_entry = f"""
### Phase Summary

- **Status**: {status}
- **Duration**: {duration_str}
- **Gates**: {gates_passed} passed, {gates_failed} failed
- **Warnings**: {len(self.warnings)}
- **Errors**: {len(self.errors)}
"""
        
        if self.decisions:
            log_entry += f"- **Decisions Made**: {len(self.decisions)}\n"
        
        if next_steps:
            log_entry += "\n**Next Steps**:\n"
            for step in next_steps:
                log_entry += f"- [ ] {step}\n"
        
        self._append_to_log(log_entry)
        
        print(f"\n{'-'*70}")
        print(f"Phase {self.current_phase} Complete: {status_emoji} {status}")
        print(f"Duration: {duration_str}")
        print(f"Gates: {gates_passed}/{len(self.gate_results)} passed")
        print(f"{'-'*70}\n")
        
        # Reset for next phase
        self.current_phase = None
        self.phase_start_time = None
        
        return status
    
    def save_phase_metrics(self, metrics: Dict[str, Any], filename: str):
        """Save phase metrics to JSON file."""
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.metrics_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        self.log_file_created(filename, str(filepath), "Phase metrics saved")
    
    def get_gate_summary(self) -> Dict[str, Any]:
        """Get summary of all gates from current phase."""
        return {
            "total": len(self.gate_results),
            "passed": sum(1 for g in self.gate_results if g['passed']),
            "failed": sum(1 for g in self.gate_results if not g['passed']),
            "results": self.gate_results
        }
    
    def finalize_log(self, final_status: str, model_version: str = None):
        """Finalize the execution log with summary."""
        log_entry = f"""
---

## Final Summary

**Completed**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Final Status**: {final_status}  
"""
        if model_version:
            log_entry += f"**Model Version**: {model_version}\n"
        
        self._append_to_log(log_entry)
        print(f"\n{'='*70}")
        print(f"EXECUTION COMPLETE: {final_status}")
        print(f"{'='*70}\n")


# Convenience function for quick logging
_logger = None

def get_logger() -> ExecutionLogger:
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = ExecutionLogger()
    return _logger

