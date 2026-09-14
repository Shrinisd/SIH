import os
import sys
import json
import numpy as np
import tensorflow as tf

# Add project root to sys.path
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.model import build_model
from ml.src.config import RESULTS_DIR, CLASS_MAP

def analyze_model():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 50)
    print("TINY 1D-CNN ARCHITECTURE ANALYSIS")
    print("=" * 50)
    
    model = build_model(input_shape=(49, 40), num_classes=3)
    
    # Print Keras Summary
    model.summary()
    
    # Calculate parameter counts
    total_params = int(model.count_params())
    trainable_params = int(sum([tf.keras.backend.count_params(w) for w in model.trainable_weights]))
    non_trainable_params = int(sum([tf.keras.backend.count_params(w) for w in model.non_trainable_weights]))
    
    # Memory estimates
    float32_size_bytes = total_params * 4
    float32_size_kb = float32_size_bytes / 1024.0
    
    int8_size_bytes = total_params * 1
    int8_size_kb = int8_size_bytes / 1024.0
    
    # Dummy forward pass verification
    dummy_input = np.zeros((1, 49, 40), dtype=np.float32)
    dummy_output = model(dummy_input, training=False).numpy()
    
    print("\n" + "=" * 50)
    print("MODEL ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Model Name:                  {model.name}")
    print(f"Input Shape:                 {model.input_shape}")
    print(f"Output Shape:                {model.output_shape}")
    print(f"Total Parameters:            {total_params:,}")
    print(f"Trainable Parameters:        {trainable_params:,}")
    print(f"Non-Trainable Parameters:    {non_trainable_params:,}")
    print(f"Est. Float32 Model Weights: {float32_size_kb:.2f} KB ({float32_size_bytes:,} bytes)")
    print(f"Est. INT8 Quantized Weights: {int8_size_kb:.2f} KB ({int8_size_bytes:,} bytes)")
    
    print("\n" + "=" * 50)
    print("DUMMY FORWARD PASS TEST")
    print("=" * 50)
    print(f"Dummy Input Shape:  {dummy_input.shape}")
    print(f"Dummy Output Shape: {dummy_output.shape}")
    print(f"Dummy Predictions:  {dummy_output[0]}")
    for cid, cname in CLASS_MAP.items():
        print(f"  Class {cid} ({cname}): {dummy_output[0][cid]:.4f}")

    forward_pass_pass = (dummy_output.shape == (1, 3)) and (np.isclose(np.sum(dummy_output[0]), 1.0))
    print(f"\nDummy Forward Pass Verification: {'PASS' if forward_pass_pass else 'FAIL'}")
    print("=" * 50)

    # Save Analysis Report JSON
    analysis_data = {
        "model_name": model.name,
        "input_shape": list(model.input_shape[1:]),
        "output_shape": list(model.output_shape[1:]),
        "total_parameters": total_params,
        "trainable_parameters": trainable_params,
        "non_trainable_parameters": non_trainable_params,
        "estimated_float32_weight_size_kb": round(float32_size_kb, 2),
        "estimated_int8_weight_size_kb": round(int8_size_kb, 2),
        "dummy_forward_pass_status": "PASS" if forward_pass_pass else "FAIL",
        "class_mapping": CLASS_MAP
    }
    
    analysis_json_path = RESULTS_DIR / "model_analysis.json"
    with open(analysis_json_path, "w", encoding="utf-8") as f:
        json.dump(analysis_data, f, indent=2)

    return forward_pass_pass

if __name__ == "__main__":
    success = analyze_model()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
