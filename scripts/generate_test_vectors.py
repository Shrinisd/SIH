import os
import sys
import json
import numpy as np
import tensorflow as tf
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import PROCESSED_DATA_DIR, MODELS_DIR, RESULTS_DIR, CLASS_MAP

def generate_vectors():
    VECTORS_DIR = RESULTS_DIR / "embedded_test_vectors"
    VECTORS_DIR.mkdir(parents=True, exist_ok=True)
    
    spec_path = RESULTS_DIR / "tflite_model_spec.json"
    int8_model_path = MODELS_DIR / "hero_arise_int8.tflite"
    x_test_path = PROCESSED_DATA_DIR / "x_test.npy"
    y_test_path = PROCESSED_DATA_DIR / "y_test.npy"
    
    if not (spec_path.exists() and int8_model_path.exists() and x_test_path.exists() and y_test_path.exists()):
        print("ERROR: Missing required files for test vector generation!")
        return False

    interpreter = tf.lite.Interpreter(model_path=str(int8_model_path))
    interpreter.allocate_tensors()
    in_details = interpreter.get_input_details()[0]
    out_details = interpreter.get_output_details()[0]
    
    in_scale = in_details["quantization"][0]
    in_zero = in_details["quantization"][1]
    out_scale = out_details["quantization"][0]
    out_zero = out_details["quantization"][1]
    
    if in_scale == 0: in_scale = 1.0
    if out_scale == 0: out_scale = 1.0

    x_test = np.load(x_test_path)
    y_test = np.load(y_test_path)
    
    # Quantize to int8
    x_test_int8 = np.round(x_test / in_scale + in_zero).clip(-128, 127).astype(np.int8)

    # Find highest confidence correctly classified test sample for each class
    best_indices = {}
    for cid in range(3):
        idxs = np.where(y_test == cid)[0]
        best_idx = None
        best_conf = -1.0
        
        for idx in idxs:
            sample_quant = np.expand_dims(x_test_int8[idx], axis=0)
            interpreter.set_tensor(in_details["index"], sample_quant)
            interpreter.invoke()
            raw_out = interpreter.get_tensor(out_details["index"])[0]
            probs = (raw_out.astype(np.float32) - out_zero) * out_scale
            pred_cls = np.argmax(probs)
            
            if pred_cls == cid and probs[cid] > best_conf:
                best_conf = probs[cid]
                best_idx = idx
                
        if best_idx is not None:
            best_indices[cid] = best_idx
        else:
            best_indices[cid] = idxs[0]

    cpp_header_lines = [
        "// Auto-generated test vectors header",
        "#ifndef TEST_VECTORS_H",
        "#define TEST_VECTORS_H",
        "",
        "#include <cstdint>",
        "",
        "struct TestVector {",
        "  const char* name;",
        "  int expected_class;",
        "  int8_t features[49 * 40];",
        "};",
        ""
    ]

    vector_defs = []

    for cid, idx in best_indices.items():
        cname = CLASS_MAP[cid]
        feat_int8 = x_test_int8[idx]  # shape (49, 40)
        feat_flat = feat_int8.flatten()
        
        json_file = VECTORS_DIR / f"test_vector_class_{cid}_{cname}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                "sample_index": int(idx),
                "expected_class": int(cid),
                "class_name": cname,
                "input_scale": float(in_scale),
                "input_zero_point": int(in_zero),
                "int8_features": [int(b) for b in feat_flat]
            }, f, indent=2)

        feat_hex = ", ".join([str(int(b)) for b in feat_flat])
        vector_defs.append(f'  {{ "{cname}", {cid}, {{ {feat_hex} }} }}')

    cpp_header_lines.append("const int NUM_TEST_VECTORS = " + str(len(vector_defs)) + ";")
    cpp_header_lines.append("const TestVector TEST_VECTORS[] = {")
    cpp_header_lines.append(",\n".join(vector_defs))
    cpp_header_lines.append("};")
    cpp_header_lines.append("")
    cpp_header_lines.append("#endif // TEST_VECTORS_H")

    header_path = BASE_DIR / "firmware" / "test_vectors.h"
    with open(header_path, "w", encoding="utf-8") as f:
        f.write("\n".join(cpp_header_lines))

    print("=" * 50)
    print("HIGH-CONFIDENCE TEST VECTOR GENERATOR")
    print("=" * 50)
    for cid, idx in best_indices.items():
        print(f"  Class {cid} ({CLASS_MAP[cid]}): Test Sample #{idx}")
    print(f"Generated C++ test header: {header_path}")
    print("=" * 50)

    return True

if __name__ == "__main__":
    success = generate_vectors()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
