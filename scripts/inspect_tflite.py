import os
import sys
import json
import numpy as np
import tensorflow as tf
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import MODELS_DIR, RESULTS_DIR, CLASS_MAP

def inspect_tflite_model():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    int8_model_path = MODELS_DIR / "hero_arise_int8.tflite"
    if not int8_model_path.exists():
        print(f"ERROR: TFLite model not found at {int8_model_path}")
        return False
        
    interpreter = tf.lite.Interpreter(model_path=str(int8_model_path))
    interpreter.allocate_tensors()
    
    in_details = interpreter.get_input_details()[0]
    out_details = interpreter.get_output_details()[0]
    
    in_scale, in_zero_point = in_details.get("quantization", (1.0, 0))
    out_scale, out_zero_point = out_details.get("quantization", (1.0, 0))
    
    model_size_bytes = int8_model_path.stat().st_size
    
    spec_data = {
        "model_file": int8_model_path.name,
        "model_size_bytes": model_size_bytes,
        "model_size_kb": round(model_size_bytes / 1024.0, 2),
        "input_name": in_details["name"],
        "input_shape": [int(x) for x in in_details["shape"]],
        "input_dtype": str(in_details["dtype"].__name__),
        "input_quantization": {
            "scale": float(in_scale),
            "zero_point": int(in_zero_point)
        },
        "output_name": out_details["name"],
        "output_shape": [int(x) for x in out_details["shape"]],
        "output_dtype": str(out_details["dtype"].__name__),
        "output_quantization": {
            "scale": float(out_scale),
            "zero_point": int(out_zero_point)
        },
        "class_mapping": CLASS_MAP,
        "required_ops": [
            "CONV_1D / CONV_2D",
            "MAX_POOLING_1D / MAX_POOL_2D",
            "GLOBAL_AVERAGE_POOLING",
            "FULLY_CONNECTED (Dense)",
            "SOFTMAX",
            "QUANTIZE",
            "DEQUANTIZE"
        ]
    }
    
    spec_json_path = RESULTS_DIR / "tflite_model_spec.json"
    with open(spec_json_path, "w", encoding="utf-8") as f:
        json.dump(spec_data, f, indent=2)

    print("=" * 50)
    print("VERIFIED TFLITE MODEL SPECIFICATION")
    print("=" * 50)
    print(f"Model Path:         {int8_model_path}")
    print(f"Model Size:         {spec_data['model_size_kb']} KB ({model_size_bytes:,} bytes)")
    print(f"Input Shape:        {spec_data['input_shape']}")
    print(f"Input Dtype:        {spec_data['input_dtype']}")
    print(f"Input Quantization: Scale={in_scale}, ZeroPoint={in_zero_point}")
    print(f"Output Shape:       {spec_data['output_shape']}")
    print(f"Output Dtype:       {spec_data['output_dtype']}")
    print(f"Output Quant:       Scale={out_scale}, ZeroPoint={out_zero_point}")
    print(f"Spec saved to:      {spec_json_path}")
    print("=" * 50)

    return True

if __name__ == "__main__":
    success = inspect_tflite_model()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
