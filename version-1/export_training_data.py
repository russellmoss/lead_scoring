"""
Phase 2.2: Export Training Data to Pandas/NumPy
Prepares datasets for XGBoost training with proper null handling
"""

import pandas as pd
import numpy as np
from google.cloud import bigquery
from pathlib import Path
import json

class TrainingDataExporter:
    def __init__(self, project_id: str = "savvy-gtm-analytics"):
        self.client = bigquery.Client(project=project_id, location="northamerica-northeast2")
        self.output_dir = Path("data/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define feature groups based on actual table structure
        self.numeric_features = [
            'days_in_gap',
            'industry_tenure_months',
            'num_prior_firms',
            'current_firm_tenure_months',
            'firm_aum_pit',
            'firm_rep_count_at_contact',
            'aum_growth_since_jan2024_pct',
            'pit_moves_3yr',
            'firm_net_change_12mo',
            'firm_stability_score',
        ]
        
        self.categorical_features = [
            'pit_mobility_tier',
        ]
        
        self.id_columns = ['lead_id', 'advisor_crd', 'contacted_date', 'firm_crd_at_contact']
        
    def export_split_data(self, split: str) -> pd.DataFrame:
        """Export data for a specific split"""
        
        query = f"""
        SELECT
            f.lead_id,
            f.advisor_crd,
            f.contacted_date,
            f.firm_crd_at_contact,
            f.target,
            
            -- Numeric features
            f.days_in_gap,
            f.industry_tenure_months,
            f.num_prior_firms,
            f.current_firm_tenure_months,
            f.firm_aum_pit,
            f.firm_rep_count_at_contact,
            f.aum_growth_since_jan2024_pct,
            f.pit_moves_3yr,
            f.firm_net_change_12mo,
            f.firm_stability_score,
            
            -- Categorical features
            f.pit_mobility_tier
            
        FROM `savvy-gtm-analytics.ml_features.lead_scoring_features_pit` f
        INNER JOIN `savvy-gtm-analytics.ml_features.lead_scoring_splits` s
            ON f.lead_id = s.lead_id
        WHERE s.split = '{split}'
        """
        
        print(f"Exporting {split} data...")
        df = self.client.query(query).to_dataframe()
        print(f"  Loaded {len(df):,} rows")
        return df
    
    def apply_null_handling(self, df: pd.DataFrame, train_medians: dict = None) -> pd.DataFrame:
        """Apply null handling according to feature catalog"""
        
        df = df.copy()
        
        # Numeric features: impute with median (from training set)
        for col in self.numeric_features:
            if col in df.columns:
                if train_medians and col in train_medians:
                    median_val = train_medians[col]
                else:
                    median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
        
        # Categorical features: default to 'Unknown'
        for col in self.categorical_features:
            if col in df.columns:
                df[col] = df[col].fillna('Unknown')
        
        return df
    
    def prepare_features_for_model(self, df: pd.DataFrame) -> tuple:
        """Prepare feature matrix X and target vector y"""
        
        # Separate identifiers, features, and target
        ids = df[self.id_columns].copy()
        y = df['target'].values
        
        # Get feature columns
        feature_cols = self.numeric_features + self.categorical_features
        X = df[feature_cols].copy()
        
        # One-hot encode categorical features
        for col in self.categorical_features:
            if col in X.columns:
                dummies = pd.get_dummies(X[col], prefix=col, drop_first=False)
                X = pd.concat([X.drop(columns=[col]), dummies], axis=1)
        
        return X, y, ids
    
    def export_all_splits(self):
        """Export all splits and save to files"""
        
        print("="*60)
        print("EXPORTING TRAINING DATA")
        print("="*60)
        
        # Export train set first to get medians
        print("\n1. Exporting TRAIN set...")
        train_df = self.export_split_data('TRAIN')
        train_medians = {col: train_df[col].median() for col in self.numeric_features if col in train_df.columns}
        
        # Apply null handling to train
        train_df = self.apply_null_handling(train_df, train_medians)
        X_train, y_train, ids_train = self.prepare_features_for_model(train_df)
        
        # Export validation
        print("\n2. Exporting VALIDATION set...")
        val_df = self.export_split_data('VALIDATION')
        val_df = self.apply_null_handling(val_df, train_medians)
        X_val, y_val, ids_val = self.prepare_features_for_model(val_df)
        
        # Export test
        print("\n3. Exporting TEST set...")
        test_df = self.export_split_data('TEST')
        test_df = self.apply_null_handling(test_df, train_medians)
        X_test, y_test, ids_test = self.prepare_features_for_model(test_df)
        
        # Ensure all feature sets have same columns
        all_cols = set(X_train.columns) | set(X_val.columns) | set(X_test.columns)
        for X in [X_train, X_val, X_test]:
            for col in all_cols:
                if col not in X.columns:
                    X[col] = 0
        
        # Reorder columns consistently
        all_cols_sorted = sorted(all_cols)
        X_train = X_train[all_cols_sorted]
        X_val = X_val[all_cols_sorted]
        X_test = X_test[all_cols_sorted]
        
        # Save to Parquet
        print("\n4. Saving to Parquet...")
        X_train.to_parquet(self.output_dir / "X_train.parquet", index=False)
        X_val.to_parquet(self.output_dir / "X_val.parquet", index=False)
        X_test.to_parquet(self.output_dir / "X_test.parquet", index=False)
        
        pd.DataFrame(y_train, columns=['target']).to_parquet(self.output_dir / "y_train.parquet", index=False)
        pd.DataFrame(y_val, columns=['target']).to_parquet(self.output_dir / "y_val.parquet", index=False)
        pd.DataFrame(y_test, columns=['target']).to_parquet(self.output_dir / "y_test.parquet", index=False)
        
        ids_train.to_parquet(self.output_dir / "ids_train.parquet", index=False)
        ids_val.to_parquet(self.output_dir / "ids_val.parquet", index=False)
        ids_test.to_parquet(self.output_dir / "ids_test.parquet", index=False)
        
        # Save to NumPy (for XGBoost)
        print("\n5. Saving to NumPy...")
        np.save(self.output_dir / "X_train.npy", X_train.values)
        np.save(self.output_dir / "X_val.npy", X_val.values)
        np.save(self.output_dir / "X_test.npy", X_test.values)
        np.save(self.output_dir / "y_train.npy", y_train)
        np.save(self.output_dir / "y_val.npy", y_val)
        np.save(self.output_dir / "y_test.npy", y_test)
        
        # Save feature names
        feature_names = {
            'feature_names': list(X_train.columns),
            'numeric_features': self.numeric_features,
            'categorical_features': self.categorical_features,
            'n_features': len(X_train.columns),
            'n_train': len(X_train),
            'n_val': len(X_val),
            'n_test': len(X_test)
        }
        
        with open(self.output_dir / "feature_names.json", 'w') as f:
            json.dump(feature_names, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("EXPORT SUMMARY")
        print("="*60)
        print(f"Train:   {len(X_train):,} rows × {X_train.shape[1]} features")
        print(f"Val:     {len(X_val):,} rows × {X_val.shape[1]} features")
        print(f"Test:    {len(X_test):,} rows × {X_test.shape[1]} features")
        print(f"\nFiles saved to: {self.output_dir}")
        print(f"  - X_train.npy, X_val.npy, X_test.npy")
        print(f"  - y_train.npy, y_val.npy, y_test.npy")
        print(f"  - *.parquet files (backup)")
        print(f"  - feature_names.json")
        
        return {
            'X_train': X_train,
            'X_val': X_val,
            'X_test': X_test,
            'y_train': y_train,
            'y_val': y_val,
            'y_test': y_test,
            'feature_names': list(X_train.columns)
        }


if __name__ == "__main__":
    exporter = TrainingDataExporter()
    results = exporter.export_all_splits()
    print("\n[OK] Data Export Complete!")

