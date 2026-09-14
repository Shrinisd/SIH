import os
import sys
import numpy as np

# Add project root to sys.path
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import PROCESSED_DATA_DIR, CLASS_MAP

def check_training_ready():
    print("=" * 50)
    print("DATASET TRAINING READINESS SANITY CHECK")
    print("=" * 50)
    
    files = {
        "train": (PROCESSED_DATA_DIR / "x_train.npy", PROCESSED_DATA_DIR / "y_train.npy"),
        "val": (PROCESSED_DATA_DIR / "x_val.npy", PROCESSED_DATA_DIR / "y_val.npy"),
        "test": (PROCESSED_DATA_DIR / "x_test.npy", PROCESSED_DATA_DIR / "y_test.npy")
    }
    
    # 1. File existence check
    for split_name, (x_p, y_p) in files.items():
        if not x_p.exists() or not y_p.exists():
            print(f"FAIL: Missing feature file for {split_name}: {x_p.name} or {y_p.name}")
            return False

    # Load data
    try:
        x_train, y_train = np.load(files["train"][0]), np.load(files["train"][1])
        x_val, y_val = np.load(files["val"][0]), np.load(files["val"][1])
        x_test, y_test = np.load(files["test"][0]), np.load(files["test"][1])
    except Exception as e:
        print(f"FAIL: Error loading numpy arrays: {str(e)}")
        return False

    splits_data = {
        "TRAIN": (x_train, y_train),
        "VALIDATION": (x_val, y_val),
        "TEST": (x_test, y_test)
    }

    # 2. Check shapes, NaNs, Infs
    for split_name, (x, y) in splits_data.items():
        print(f"\nChecking {split_name} Set:")
        print(f"  Feature Tensor Shape: {x.shape}")
        print(f"  Labels Array Shape:   {y.shape}")
        
        if len(x.shape) != 3 or x.shape[1:] != (49, 40):
            print(f"  FAIL: Feature shape mismatch for {split_name}. Expected (*, 49, 40), got {x.shape}")
            return False
            
        if np.isnan(x).any():
            print(f"  FAIL: NaN values detected in {split_name} features!")
            return False
            
        if np.isinf(x).any():
            print(f"  FAIL: Infinite values detected in {split_name} features!")
            return False

    # 3. Class representation check across all splits
    class_ids = set(CLASS_MAP.keys())
    readiness_pass = True
    
    print("\n" + "=" * 50)
    print("CLASS DISTRIBUTION PER SPLIT")
    print("=" * 50)
    
    for split_name, (x, y) in splits_data.items():
        unique_labels, counts = np.unique(y, return_counts=True)
        label_count_dict = dict(zip(unique_labels, counts))
        
        print(f"\n{split_name}:")
        for cid, cname in CLASS_MAP.items():
            count = label_count_dict.get(cid, 0)
            print(f"  Class {cid} ({cname}): {count} samples")
            if count == 0:
                print(f"  CRITICAL ISSUE: Class {cid} ({cname}) HAS ZERO SAMPLES in {split_name} split!")
                readiness_pass = False

    # 4. Check labels range
    all_y = np.concatenate([y_train, y_val, y_test])
    if not set(np.unique(all_y)).issubset(class_ids):
        print(f"FAIL: Unexpected label values detected: {np.unique(all_y)}")
        return False

    print("\n" + "=" * 50)
    if readiness_pass:
        print("TRAINING READINESS CHECK: PASS")
        print("=" * 50)
        return True
    else:
        print("TRAINING READINESS CHECK: FAIL")
        print("Reason: One or more classes are missing from VALIDATION or TEST split.")
        print("=" * 50)
        return False

if __name__ == "__main__":
    success = check_training_ready()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
