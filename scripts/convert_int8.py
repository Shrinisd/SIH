import os
import sys
import numpy as np
import tensorflow as tf
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import PROCESSED_DATA_DIR, MODELS_DIR, RESULTS_DIR

def convert_to_tflite():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    keras_model_path = MODELS_DIR / "hero_arise_best.keras"
    if not keras_model_path.exists():
        print(f"ERROR: Keras model not found at {keras_model_path}")
        return False
        
    x_train_path = PROCESSED_DATA_DIR / "x_train.npy"
    if not x_train_path.exists():
        print(f"ERROR: Training features not found at {x_train_path}")
        return False
        
    x_train = np.load(x_train_path)
    
    print("=" * 50)
    print("TFLITE INT8 QUANTIZATION & CONVERSION")
    print("=" * 50)
    print(f"Loading Keras Model: {keras_model_path}")
    model = tf.keras.models.load_model(str(keras_model_path))
    
    # 1. Convert to Float32 TFLite
    converter_float = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_float_model = converter_float.convert()
    
    float_model_path = MODELS_DIR / "hero_arise_float32.tflite"
    with open(float_model_path, "wb") as f:
        f.write(tflite_float_model)
    print(f"Saved Float32 TFLite model to: {float_model_path} ({len(tflite_float_model):,} bytes)")

    # 2. Convert to Full INT8 Quantized TFLite
    def representative_dataset_gen():
        # Use ONLY training set for calibration
        for i in range(min(100, len(x_train))):
            sample = np.expand_dims(x_train[i], axis=0).astype(np.float32)
            yield [sample]

    converter_int8 = tf.lite.TFLiteConverter.from_keras_model(model)
    converter_int8.optimizations = [tf.lite.Optimize.DEFAULT]
    converter_int8.representative_dataset = representative_dataset_gen
    converter_int8.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter_int8.inference_input_type = tf.int8
    converter_int8.inference_output_type = tf.int8

    try:
        tflite_int8_model = converter_int8.convert()
    except Exception as e:
        print(f"Warning: Full INT8 with int8 IO failed ({e}). Retrying with int8 weights and float IO fallback...")
        converter_int8_fallback = tf.lite.TFLiteConverter.from_keras_model(model)
        converter_int8_fallback.optimizations = [tf.lite.Optimize.DEFAULT]
        converter_int8_fallback.representative_dataset = representative_dataset_gen
        tflite_int8_model = converter_int8_fallback.convert()

    int8_model_path = MODELS_DIR / "hero_arise_int8.tflite"
    with open(int8_model_path, "wb") as f:
        f.write(tflite_int8_model)
    print(f"Saved INT8 TFLite model to:    {int8_model_path} ({len(tflite_int8_model):,} bytes)")

    # 3. Inspect Quantization Parameters
    interpreter = tf.lite.Interpreter(model_path=str(int8_model_path))
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()[0]
    output_details = interpreter.get_output_details()[0]

    input_scale, input_zero_point = input_details.get("quantization", (0.0, 0))
    output_scale, output_zero_point = output_details.get("quantization", (0.0, 0))

    print("\n" + "=" * 50)
    print("QUANTIZATION PARAMETERS & DETAILS")
    print("=" * 50)
    print(f"Input Dtype:         {input_details['dtype']}")
    print(f"Input Scale:         {input_scale}")
    print(f"Input Zero Point:    {input_zero_point}")
    print(f"Output Dtype:        {output_details['dtype']}")
    print(f"Output Scale:        {output_scale}")
    print(f"Output Zero Point:   {output_zero_point}")
    print(f"Float32 Model Size:  {len(tflite_float_model) / 1024.0:.2f} KB")
    print(f"INT8 Model Size:     {len(tflite_int8_model) / 1024.0:.2f} KB")
    print(f"Compression Ratio:   {len(tflite_float_model) / float(len(tflite_int8_model)):.2f}x smaller")
    print("=" * 50)

    return True

if __name__ == "__main__":
    success = convert_to_tflite()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
