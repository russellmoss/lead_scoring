"""
Create Directory Structure for Version 4 Lead Scoring Project

This script creates all required directories and placeholder files for the V4 project.
"""

import os
from pathlib import Path

BASE_DIR = Path(r"C:\Users\russe\Documents\Lead Scoring\Version-4")

# Required directories
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

# Required placeholder files
placeholder_files = [
    "README.md",
    "VERSION_4_MODEL_REPORT.md",
    "EXECUTION_LOG.md",
    "config/constants.py",
    "config/feature_config.yaml",
    "config/model_config.yaml",
    "models/registry.json"
]

def create_directory_structure():
    """Create all directories and placeholder files."""
    
    print("=" * 70)
    print("CREATING VERSION-4 DIRECTORY STRUCTURE")
    print("=" * 70)
    print()
    
    # Create directories
    print("Creating directories...")
    created_dirs = 0
    for dir_path in directories:
        full_path = BASE_DIR / dir_path
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  [OK] {dir_path}/")
            created_dirs += 1
        except Exception as e:
            print(f"  [ERROR] Failed to create {dir_path}: {str(e)}")
    
    print(f"\nCreated {created_dirs}/{len(directories)} directories")
    print()
    
    # Create placeholder files
    print("Creating placeholder files...")
    created_files = 0
    for file_path in placeholder_files:
        full_path = BASE_DIR / file_path
        try:
            # Create parent directory if it doesn't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file if it doesn't exist
            if not full_path.exists():
                full_path.touch()
                print(f"  [OK] {file_path}")
                created_files += 1
            else:
                print(f"  [SKIP] {file_path} (already exists)")
        except Exception as e:
            print(f"  [ERROR] Failed to create {file_path}: {str(e)}")
    
    print(f"\nCreated {created_files}/{len(placeholder_files)} new files")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Directories: {created_dirs}/{len(directories)}")
    print(f"Files: {created_files}/{len(placeholder_files)}")
    print()
    
    if created_dirs == len(directories):
        print("[SUCCESS] Directory structure created successfully!")
    else:
        print("[WARNING] Some directories failed to create. Check errors above.")
    
    if created_files == len(placeholder_files):
        print("[SUCCESS] All placeholder files created successfully!")
    else:
        print("[INFO] Some files already existed or failed to create.")
    
    return created_dirs == len(directories)


if __name__ == "__main__":
    success = create_directory_structure()
    exit(0 if success else 1)

