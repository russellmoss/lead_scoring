"""
Phase 6.2: Package Boosted Model (v2) for Production
Creates the "Golden Artifact" for the boosted model
"""

import json
import pickle
from pathlib import Path
from datetime import datetime
import hashlib
import shutil
import pandas as pd

class BoostedModelPackager:
    def __init__(self, calibrated_model_dir: str = "models/production", 
                 boosted_model_dir: str = "models/boosted"):
        self.calibrated_model_dir = Path(calibrated_model_dir)
        self.boosted_model_dir = Path(boosted_model_dir)
        self.output_dir = Path("models/production")
        self.registry_dir = Path("models/registry")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*60}")
        print("BOOSTED MODEL PACKAGING SETUP")
        print(f"{'='*60}\n")
        
    def generate_version_hash(self) -> str:
        """Generate unique version hash"""
        
        with open(self.calibrated_model_dir / "calibrated_model_v2_boosted.pkl", 'rb') as f:
            model_bytes = f.read()
        
        timestamp = datetime.now().strftime("%Y%m%d")
        hash_input = model_bytes + timestamp.encode()
        version_hash = hashlib.md5(hash_input).hexdigest()[:8]
        
        version_id = f"v2-boosted-{timestamp}-{version_hash}"
        
        print(f"Generated Version ID: {version_id}")
        return version_id
    
    def create_model_card(self, version_id: str) -> Path:
        """Create Model Card documentation for boosted model"""
        
        # Load performance metrics
        with open(self.boosted_model_dir / "boosted_metrics.json", 'r') as f:
            metrics = json.load(f)
        
        with open(self.calibrated_model_dir / "calibration_metadata_v2_boosted.json", 'r') as f:
            calibration_meta = json.load(f)
        
        model_card = f"""# Lead Scoring Model Card - Boosted Model (v2)

**Version:** {version_id}  
**Date:** {datetime.now().strftime("%Y-%m-%d")}  
**Status:** Production Ready  
**Model Type:** Boosted XGBoost with Engineered Features

---

## Model Overview

This model predicts the probability that a lead will convert to a "Call Scheduled" stage within 30 days of initial contact. The model uses XGBoost with **3 engineered features** to recover performance after removing data leakage, achieving **2.62x lift** on the test set.

### Model Type
- **Algorithm:** XGBoost (Gradient Boosting)
- **Calibration Method:** {calibration_meta['calibration_method'].title()}
- **Features:** {calibration_meta['n_features']} features (11 base + 3 engineered)
- **Model Version:** v2-boosted (replaces v1 after data leakage remediation)

---

## Performance Metrics

### Test Set Performance (1,739 leads)

| Metric | Value |
|--------|-------|
| **AUC-ROC** | {metrics['test_metrics']['test_auc_roc']:.4f} |
| **AUC-PR** | {metrics['test_metrics']['test_auc_pr']:.4f} |
| **Baseline Conversion Rate** | {metrics['test_metrics']['baseline_rate']:.2%} |
| **Top Decile Conversion Rate** | {metrics['test_metrics']['top_decile_rate']:.2%} |
| **Top Decile Lift** | **{metrics['test_metrics']['top_decile_lift']:.2f}x** |

### Calibration Quality

| Metric | Value |
|--------|-------|
| **Calibration Method** | {calibration_meta['calibration_method'].title()} |
| **Brier Score** | {calibration_meta['brier_score']:.6f} |

---

## Key Features

### Top Predictive Features

1. **`current_firm_tenure_months`** - Primary signal (short tenure = higher conversion)
2. **`pit_restlessness_ratio`** ⭐ - **NEW**: Captures advisors staying longer than historical pattern
3. **`flight_risk_score`** ⭐ - **NEW**: Combines mobility + firm bleeding (multiplicative signal)
4. **`firm_net_change_12mo`** - Firm stability signal (bleeding firms = opportunity)
5. **`is_fresh_start`** ⭐ - **NEW**: Binary flag for new hires (< 12 months)

### Engineered Features (v2 Boost)

**1. `pit_restlessness_ratio`**
- **Formula:** `current_firm_tenure_months / (avg_prior_firm_tenure_months + 1)`
- **Purpose:** Identifies advisors who have stayed longer than their historical "itch" cycle
- **Business Logic:** High ratio = stable, low ratio = may be ready to move

**2. `flight_risk_score`**
- **Formula:** `pit_moves_3yr * (firm_net_change_12mo * -1)`
- **Purpose:** Multiplicative combination of "Mobile Person" + "Bleeding Firm"
- **Business Logic:** High mobility × Bleeding firm = High flight risk

**3. `is_fresh_start`**
- **Formula:** `1 if current_firm_tenure_months < 12 else 0`
- **Purpose:** Binary flag to isolate "New Hires" from "Veterans"
- **Business Logic:** New hires may be more open to opportunities

### Business Hypotheses Validated

- ✅ **Mobility Hypothesis:** Advisors with frequent firm changes are more likely to convert
- ✅ **Employment Gap Hypothesis:** Removed due to data leakage (retrospective backfilling)
- ✅ **Bleeding Firm Hypothesis:** Advisors at unstable firms are more likely to convert
- ✅ **Restlessness Hypothesis:** Advisors staying longer than usual may be more stable
- ✅ **Flight Risk Hypothesis:** Mobile advisors at bleeding firms = highest conversion risk

---

## Training Data

- **Training Period:** February 2024 - October 2024
- **Training Samples:** {metrics['n_train']:,} leads
- **Test Period:** November 2024
- **Test Samples:** {metrics['n_test']:,} leads
- **Temporal Split:** 70% train, 15% validation, 15% test (with 30-day gap)

---

## Model Architecture

### Feature Set

**Base Features (11):**
{', '.join([f for f in calibration_meta['feature_names'] if f not in ['pit_restlessness_ratio', 'flight_risk_score', 'is_fresh_start']][:5])}
... and 6 more base features

**Engineered Features (3):**
- `pit_restlessness_ratio` ⭐
- `flight_risk_score` ⭐
- `is_fresh_start` ⭐

**Total:** {calibration_meta['n_features']} features

### Data Leakage Remediation

**Removed Features:**
- ❌ `days_in_gap` - **DATA LEAKAGE** (retrospective backfilling, not available at inference)
- ❌ `firm_stability_score` - Weak IV (0.004)
- ❌ `pit_mobility_tier_Average` - Weak IV (0.004)

**Performance Impact:**
- Original (with leakage): 3.03x lift
- Honest baseline (no leakage): 1.65x lift
- Boosted (with engineered features): **2.62x lift** ✅

---

## Usage

### Score Interpretation

- **0.0 - 0.3:** Low probability (Cold)
- **0.3 - 0.5:** Medium probability (Warm)
- **0.5 - 0.7:** High probability (Hot)
- **0.7 - 1.0:** Very high probability (Very Hot)

### Recommended Actions

- **Very Hot (0.7+):** Call immediately
- **Hot (0.5-0.7):** Prioritize in next outreach cycle
- **Warm (0.3-0.5):** Include in standard outreach
- **Cold (<0.3):** Low priority

---

## Limitations

1. **Class Imbalance:** 4.2% positive rate requires careful threshold tuning
2. **Temporal Validation:** Model trained on Feb-Oct 2024, tested on Nov 2024
3. **Feature Dependencies:** Some features depend on FINTRX data availability
4. **Derived Features:** 3 features must be calculated at inference time (not in BigQuery table)

---

## Maintenance

- **Retrain Frequency:** Quarterly
- **Monitoring:** Track conversion rates monthly
- **Alert Threshold:** If top decile lift drops below 2.0x

---

## Version History

- **{version_id}:** Boosted model (v2) - Initial production release
  - 2.62x lift on test set
  - {calibration_meta['calibration_method'].title()} calibration
  - 3 engineered features (restlessness, flight risk, fresh start)
  - Data leakage removed (`days_in_gap`)
  - Validated on 1,739 test leads

- **v1-20251221-b374197e:** Original model (deprecated due to data leakage)

---

## Contact

For questions or issues, contact the Data Science team.
"""
        
        output_path = self.output_dir / f"model_card_{version_id}.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(model_card)
        
        print(f"[OK] Model card saved to: {output_path}")
        return output_path
    
    def register_model(self, version_id: str):
        """Register model in registry"""
        
        registry_path = self.registry_dir / "registry.json"
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                registry = json.load(f)
        else:
            registry = {
                'models': [],
                'latest_version': None
            }
        
        with open(self.boosted_model_dir / "boosted_metrics.json", 'r') as f:
            metrics = json.load(f)
        
        with open(self.calibrated_model_dir / "calibration_metadata_v2_boosted.json", 'r') as f:
            calibration_meta = json.load(f)
        
        model_entry = {
            'version_id': version_id,
            'created_date': datetime.now().isoformat(),
            'status': 'production',
            'model_type': 'boosted_v2',
            'performance': {
                'test_auc_roc': float(metrics['test_metrics']['test_auc_roc']),
                'test_auc_pr': float(metrics['test_metrics']['test_auc_pr']),
                'top_decile_lift': float(metrics['test_metrics']['top_decile_lift']),
                'baseline_rate': float(metrics['test_metrics']['baseline_rate']),
                'top_decile_rate': float(metrics['test_metrics']['top_decile_rate'])
            },
            'calibration': {
                'method': calibration_meta['calibration_method'],
                'brier_score': float(calibration_meta['brier_score'])
            },
            'model_path': str(self.output_dir / f"model_{version_id}.pkl"),
            'model_card_path': str(self.output_dir / f"model_card_{version_id}.md"),
            'n_features': calibration_meta['n_features'],
            'n_train': metrics['n_train'],
            'n_test': metrics['n_test'],
            'engineered_features': ['pit_restlessness_ratio', 'flight_risk_score', 'is_fresh_start']
        }
        
        registry['models'].append(model_entry)
        registry['latest_version'] = version_id
        
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        
        print(f"[OK] Model registered in: {registry_path}")
        return registry
    
    def package_model(self, version_id: str):
        """Package model files for production"""
        
        print("Packaging boosted model files...")
        
        # Copy calibrated model
        source_model = self.calibrated_model_dir / "calibrated_model_v2_boosted.pkl"
        dest_model = self.output_dir / f"model_{version_id}.pkl"
        shutil.copy2(source_model, dest_model)
        print(f"  Copied model to: {dest_model}")
        
        # Copy feature names
        source_features = self.boosted_model_dir / "feature_names_v2_boosted.json"
        dest_features = self.output_dir / f"feature_names_{version_id}.json"
        shutil.copy2(source_features, dest_features)
        print(f"  Copied feature names to: {dest_features}")
        
        # Copy calibration lookup table
        source_lookup = self.calibrated_model_dir / "calibration_lookup_v2_boosted.csv"
        if source_lookup.exists():
            dest_lookup = self.output_dir / f"calibration_lookup_{version_id}.csv"
            shutil.copy2(source_lookup, dest_lookup)
            print(f"  Copied lookup table to: {dest_lookup}")
        
        return {
            'model_path': str(dest_model),
            'feature_names_path': str(dest_features),
            'lookup_table_path': str(dest_lookup) if source_lookup.exists() else None
        }
    
    def run_full_packaging(self):
        """Execute complete packaging pipeline"""
        
        print("\n" + "="*60)
        print("BOOSTED MODEL PACKAGING PIPELINE")
        print("="*60 + "\n")
        
        version_id = self.generate_version_hash()
        model_card_path = self.create_model_card(version_id)
        packaged_files = self.package_model(version_id)
        registry = self.register_model(version_id)
        
        print("\n" + "="*60)
        print("PACKAGING COMPLETE")
        print("="*60)
        print(f"Version ID: {version_id}")
        print(f"Model Card: {model_card_path}")
        print(f"Model File: {packaged_files['model_path']}")
        print(f"Registry: models/registry/registry.json")
        print("="*60 + "\n")
        
        return {
            'version_id': version_id,
            'model_card_path': model_card_path,
            'packaged_files': packaged_files,
            'registry': registry
        }


if __name__ == "__main__":
    packager = BoostedModelPackager()
    results = packager.run_full_packaging()
    
    print(f"[OK] Boosted model packaging complete!")
    print(f"Final Model Version ID: {results['version_id']}")

