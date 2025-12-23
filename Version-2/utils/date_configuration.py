# =============================================================================
# PHASE 0.0: DYNAMIC DATE CONFIGURATION (MANDATORY FIRST STEP)
# =============================================================================
"""
This module MUST execute first. All downstream phases import dates from here.
NEVER hardcode dates in other phases - always reference these variables.

Based on data assessment from December 21, 2025:
- Firm_historicals: Jan 2024 - Nov 2025 (23 months)
- Salesforce Leads: 56,982 total (18,337 in 2024, 38,645 in 2025)
- CRD Match Rate: 95.72%
"""

from datetime import datetime, timedelta

class DateConfiguration:
    """
    Central date configuration for the entire pipeline.
    All dates are calculated relative to execution date.
    
    Key Constraints (from data assessment):
    - Firm_historicals starts Jan 2024, so training floor is Feb 2024
    - Firm_historicals has ~1 month lag (Dec data not available in Dec)
    - 30-day maturity window required for conversion observation
    """
    
    def __init__(self, execution_date: datetime = None):
        """
        Initialize date configuration.
        
        Args:
            execution_date: Override for testing. Defaults to today.
        """
        self.execution_date = execution_date or datetime.now()
        self._calculate_all_dates()
    
    def _calculate_all_dates(self):
        """Calculate all pipeline dates from execution date."""
        
        # FIRM_HISTORICALS_LAG: Firm data is typically 1 month behind
        # If we're in Dec 2025, latest firm data is Nov 2025
        self.firm_data_lag_months = 1
        
        # TRAINING_SNAPSHOT_DATE: End of last month with firm data
        first_of_current_month = self.execution_date.replace(day=1)
        last_month_end = first_of_current_month - timedelta(days=1)
        # Go back one more month for firm data lag
        self.training_snapshot_date = (last_month_end.replace(day=1) - timedelta(days=1))
        
        # MATURITY_WINDOW: Days to wait for conversion outcome
        self.maturity_window_days = 30
        
        # TRAINING_END_DATE: Latest contacted_date we can use
        # Must be maturity_window before snapshot to observe outcomes
        self.training_end_date = self.training_snapshot_date - timedelta(days=self.maturity_window_days)
        
        # TRAINING_START_DATE: Earliest contacted_date we can use
        # Firm_historicals starts Jan 2024, need Feb 2024 for prior month comparison
        self.training_start_date = datetime(2024, 2, 1).date()
        
        # Ensure training_end_date is a date object
        if hasattr(self.training_end_date, 'date'):
            self.training_end_date = self.training_end_date.date()
        if hasattr(self.training_snapshot_date, 'date'):
            self.training_snapshot_date = self.training_snapshot_date.date()
        
        # TEST_SPLIT_DATE: Where to split train vs test
        # Use approximately 80/20 split, with test being most recent 60 days
        total_days = (self.training_end_date - self.training_start_date).days
        test_days = min(60, int(total_days * 0.15))  # 15% or 60 days, whichever is smaller
        self.test_split_date = self.training_end_date - timedelta(days=test_days)
        
        # GAP_DAYS: Minimum gap between train and test to prevent leakage
        self.gap_days = 30
        
        # Adjusted train end (with gap before test)
        self.train_end_date = self.test_split_date - timedelta(days=self.gap_days)
        
        # TEST dates
        self.test_start_date = self.test_split_date
        self.test_end_date = self.training_end_date
        
        # LATEST_FIRM_SNAPSHOT: For scoring new leads without current month data
        self.latest_firm_snapshot_date = self.training_snapshot_date.replace(day=1)
    
    def validate(self):
        """Validate date configuration is sensible."""
        errors = []
        
        # Check we have enough training data
        train_days = (self.train_end_date - self.training_start_date).days
        if train_days < 180:
            errors.append(f"Insufficient training data: only {train_days} days (need 180+)")
        
        # Check we have enough test data
        test_days = (self.test_end_date - self.test_start_date).days
        if test_days < 30:
            errors.append(f"Insufficient test data: only {test_days} days (need 30+)")
        
        # Check dates are in correct order
        if self.training_start_date >= self.train_end_date:
            errors.append("training_start_date must be before train_end_date")
        
        if self.test_start_date >= self.test_end_date:
            errors.append("test_start_date must be before test_end_date")
        
        # Check snapshot isn't in the future
        if self.training_snapshot_date > datetime.now().date():
            errors.append("training_snapshot_date cannot be in the future")
        
        # Check training start is after Firm_historicals start
        firm_data_start = datetime(2024, 1, 1).date()
        if self.training_start_date < firm_data_start:
            errors.append(f"training_start_date ({self.training_start_date}) is before Firm_historicals start ({firm_data_start})")
        
        if errors:
            raise ValueError("Date configuration validation failed:\n" + "\n".join(errors))
        
        return True
    
    def print_summary(self):
        """Print date configuration summary."""
        train_days = (self.train_end_date - self.training_start_date).days
        test_days = (self.test_end_date - self.test_start_date).days
        
        print(f"""
╔══════════════════════════════════════════════════════════════════╗
║           DYNAMIC DATE CONFIGURATION (v2)                        ║
║           Based on Data Assessment: Dec 21, 2025                 ║
╠══════════════════════════════════════════════════════════════════╣
║  Execution Date:           {self.execution_date.strftime('%Y-%m-%d'):>20}              ║
║  Training Snapshot:        {self.training_snapshot_date.strftime('%Y-%m-%d'):>20}              ║
║  Latest Firm Data:         {self.latest_firm_snapshot_date.strftime('%Y-%m-%d'):>20}              ║
║  Maturity Window:          {self.maturity_window_days:>20} days            ║
╠══════════════════════════════════════════════════════════════════╣
║  DATA CONSTRAINTS (from assessment)                              ║
║    Firm_historicals:       Jan 2024 - Nov 2025 (23 months)       ║
║    Firm data lag:          ~1 month                              ║
║    Total leads available:  56,982                                ║
║    Total MQLs available:   2,413                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  TRAINING DATA                                                   ║
║    Start:                  {self.training_start_date.strftime('%Y-%m-%d'):>20}              ║
║    End:                    {self.train_end_date.strftime('%Y-%m-%d'):>20}              ║
║    Days:                   {train_days:>20}              ║
╠══════════════════════════════════════════════════════════════════╣
║  GAP (Leakage Prevention): {self.gap_days:>10} days                          ║
╠══════════════════════════════════════════════════════════════════╣
║  TEST DATA                                                       ║
║    Start:                  {self.test_start_date.strftime('%Y-%m-%d'):>20}              ║
║    End:                    {self.test_end_date.strftime('%Y-%m-%d'):>20}              ║
║    Days:                   {test_days:>20}              ║
╚══════════════════════════════════════════════════════════════════╝
        """)
    
    def to_dict(self):
        """Export configuration as dictionary for SQL templating."""
        return {
            'execution_date': self.execution_date.strftime('%Y-%m-%d'),
            'training_snapshot_date': self.training_snapshot_date.strftime('%Y-%m-%d'),
            'latest_firm_snapshot_date': self.latest_firm_snapshot_date.strftime('%Y-%m-%d'),
            'maturity_window_days': self.maturity_window_days,
            'training_start_date': self.training_start_date.strftime('%Y-%m-%d'),
            'training_end_date': self.training_end_date.strftime('%Y-%m-%d'),
            'train_end_date': self.train_end_date.strftime('%Y-%m-%d'),
            'test_split_date': self.test_split_date.strftime('%Y-%m-%d'),
            'test_start_date': self.test_start_date.strftime('%Y-%m-%d'),
            'test_end_date': self.test_end_date.strftime('%Y-%m-%d'),
            'gap_days': self.gap_days,
            'firm_data_lag_months': self.firm_data_lag_months
        }
    
    def get_sql_parameters(self):
        """Get parameters formatted for SQL queries."""
        d = self.to_dict()
        return {
            'TRAINING_START': d['training_start_date'],
            'TRAINING_END': d['training_end_date'],
            'TRAIN_END': d['train_end_date'],
            'TEST_START': d['test_start_date'],
            'TEST_END': d['test_end_date'],
            'SNAPSHOT_DATE': d['training_snapshot_date'],
            'MATURITY_DAYS': d['maturity_window_days']
        }

