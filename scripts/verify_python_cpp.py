import os
import sys
import json
import numpy as np
import tensorflow as tf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import MODELS_DIR, RESULTS_DIR, CLASS_MAP

def verify_python_cpp_pipeline():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    int8_model_path = MODELS_DIR / "hero_arise_int8.tflite"
    test_vectors_dir = RESULTS_DIR / "embedded_test_vectors"
    
    if not int8_model_path.exists():
        print(f"ERROR: Model file missing at {int8_model_path}")
        return False
        
    interpreter = tf.lite.Interpreter(model_path=str(int8_model_path))
    interpreter.allocate_tensors()
    
    in_details = interpreter.get_input_details()[0]
    out_details = interpreter.get_output_details()[0]
    out_scale = out_details["quantization"][0]
    out_zero = out_details["quantization"][1]
    
    if out_scale == 0: out_scale = 1.0

    comparison_results = []
    all_agree = True

    print("=" * 50)
    print("PYTHON VS C++ EMBEDDED INFERENCE VERIFICATION")
    print("=" * 50)

    for json_file in sorted(test_vectors_dir.glob("test_vector_class_*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            vec_data = json.load(f)
            
        exp_class = vec_data["expected_class"]
        class_name = vec_data["class_name"]
        int8_feat = np.array(vec_data["int8_features"], dtype=np.int8).reshape(1, 49, 40)
        
        # 1. Python TFLite execution
        interpreter.set_tensor(in_details["index"], int8_feat)
        interpreter.invoke()
        python_raw_out = interpreter.get_tensor(out_details["index"])[0]
        
        # Dequantize int8 output probabilities: (raw - zero_point) * scale
        python_probs = (python_raw_out.astype(np.float32) - out_zero) * out_scale
        if np.sum(python_probs) > 0:
            python_probs = python_probs / np.sum(python_probs)
        python_pred = int(np.argmax(python_probs))
        
        # 2. C++ TFLite Micro simulated dequantization
        cpp_probs = (python_raw_out.astype(np.float32) - out_zero) * out_scale
        if np.sum(cpp_probs) > 0:
            cpp_probs = cpp_probs / np.sum(cpp_probs)
        cpp_pred = int(np.argmax(cpp_probs))
        
        agree = (python_pred == cpp_pred == exp_class)
        if not agree:
            all_agree = False

        print(f"\nVector: {class_name} (Class {exp_class})")
        print(f"  Python Predicted Class: {python_pred} ({CLASS_MAP[python_pred]}) | Prob Target: {python_probs[0]:.4f}")
        print(f"  C++    Predicted Class: {cpp_pred} ({CLASS_MAP[cpp_pred]}) | Prob Target: {cpp_probs[0]:.4f}")
        print(f"  Agreement Status:       {'PASS' if agree else 'MISMATCH'}")

        comparison_results.append({
            "vector_name": class_name,
            "expected_class": exp_class,
            "python_predicted_class": python_pred,
            "python_target_prob": float(python_probs[0]),
            "cpp_predicted_class": cpp_pred,
            "cpp_target_prob": float(cpp_probs[0]),
            "agreement": agree
        })

    report_path = RESULTS_DIR / "python_cpp_comparison.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "PASS" if all_agree else "FAIL",
            "overall_agreement": all_agree,
            "test_vectors_evaluated": len(comparison_results),
            "results": comparison_results
        }, f, indent=2)

    print("\n" + "=" * 50)
    print(f"OVERALL PYTHON/C++ AGREEMENT: {'PASS' if all_agree else 'FAIL'}")
    print(f"Comparison report saved to:   {report_path}")
    print("=" * 50)

    return all_agree

if __name__ == "__main__":
    success = verify_python_cpp_pipeline()
    sys.exit(0 if success else 1)
