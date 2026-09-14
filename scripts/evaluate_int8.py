import os
import sys
import json
import numpy as np
import tensorflow as tf
from pathlib import Path
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import PROCESSED_DATA_DIR, MODELS_DIR, RESULTS_DIR, CLASS_MAP

def evaluate_int8():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    keras_path = MODELS_DIR / "hero_arise_best.keras"
    int8_tflite_path = MODELS_DIR / "hero_arise_int8.tflite"
    x_test_path = PROCESSED_DATA_DIR / "x_test.npy"
    y_test_path = PROCESSED_DATA_DIR / "y_test.npy"
    
    if not (keras_path.exists() and int8_tflite_path.exists() and x_test_path.exists() and y_test_path.exists()):
        print("ERROR: Missing required model or dataset test files!")
        return False

    x_test = np.load(x_test_path)
    y_test = np.load(y_test_path)

    # 1. Float32 Keras Inference
    model_float = tf.keras.models.load_model(str(keras_path))
    float_probs = model_float.predict(x_test, verbose=0)
    float_preds = np.argmax(float_probs, axis=1)
    float_acc = float(np.mean(float_preds == y_test))

    # 2. INT8 TFLite Inference
    interpreter = tf.lite.Interpreter(model_path=str(int8_tflite_path))
    interpreter.allocate_tensors()
    
    in_details = interpreter.get_input_details()[0]
    out_details = interpreter.get_output_details()[0]
    
    in_scale, in_zero_point = in_details.get("quantization", (1.0, 0))
    out_scale, out_zero_point = out_details.get("quantization", (1.0, 0))
    
    if in_scale == 0: in_scale = 1.0
    if out_scale == 0: out_scale = 1.0

    int8_preds = []
    int8_probs = []

    for i in range(len(x_test)):
        sample_float = x_test[i]
        
        if in_details["dtype"] == np.int8:
            sample_quant = np.round(sample_float / in_scale + in_zero_point).clip(-128, 127).astype(np.int8)
            sample_quant = np.expand_dims(sample_quant, axis=0)
        else:
            sample_quant = np.expand_dims(sample_float, axis=0).astype(np.float32)
            
        interpreter.set_tensor(in_details["index"], sample_quant)
        interpreter.invoke()
        
        raw_out = interpreter.get_tensor(out_details["index"])[0]
        
        if out_details["dtype"] == np.int8:
            dequant_out = (raw_out.astype(np.float32) - out_zero_point) * out_scale
        else:
            dequant_out = raw_out.astype(np.float32)
            
        pred_cls = np.argmax(dequant_out)
        int8_preds.append(pred_cls)
        int8_probs.append(dequant_out)

    int8_preds = np.array(int8_preds)
    int8_probs = np.array(int8_probs)
    int8_acc = float(np.mean(int8_preds == y_test))

    # 3. Prediction Agreement
    agreement = float(np.mean(float_preds == int8_preds))
    acc_diff = float(float_acc - int8_acc)

    # 4. Metrics & Target Word Analysis
    int8_cm = confusion_matrix(y_test, int8_preds, labels=[0, 1, 2])
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, int8_preds, labels=[0, 1, 2], zero_division=0)

    tp = int(int8_cm[0, 0])
    fp = int(int8_cm[1, 0] + int8_cm[2, 0])
    fn = int(int8_cm[0, 1] + int8_cm[0, 2])
    tn = int(int8_cm[1, 1] + int8_cm[1, 2] + int8_cm[2, 1] + int8_cm[2, 2])

    target_prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    target_rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    target_f1 = float(2 * target_prec * target_rec / (target_prec + target_rec)) if (target_prec + target_rec) > 0 else 0.0

    print("=" * 50)
    print("FLOAT32 VS INT8 QUANTIZATION EVALUATION")
    print("=" * 50)
    print(f"Float32 Test Accuracy:  {float_acc * 100:.2f}%")
    print(f"INT8 Test Accuracy:     {int8_acc * 100:.2f}%")
    print(f"Accuracy Difference:    {acc_diff * 100:.2f}%")
    print(f"Prediction Agreement:   {agreement * 100:.2f}%")
    
    print("\nINT8 TARGET WORD ('Hero Arise') METRICS:")
    print(f"  Precision:            {target_prec * 100:.2f}%")
    print(f"  Recall:               {target_rec * 100:.2f}%")
    print(f"  F1 Score:             {target_f1:.4f}")
    print(f"  False Positives:      {fp}")

    print("\nINT8 CONFUSION MATRIX:")
    print(int8_cm)
    print("=" * 50)

    # Save JSON Evaluation
    int8_eval_data = {
        "float32_test_accuracy": float_acc,
        "int8_test_accuracy": int8_acc,
        "accuracy_difference": acc_diff,
        "prediction_agreement": agreement,
        "target_word_metrics": {
            "precision": target_prec,
            "recall": target_rec,
            "f1_score": target_f1,
            "false_positives": fp
        },
        "per_class_int8": {
            CLASS_MAP[i]: {
                "precision": float(prec[i]),
                "recall": float(rec[i]),
                "f1_score": float(f1[i])
            } for i in range(3)
        }
    }

    with open(RESULTS_DIR / "int8_evaluation.json", "w", encoding="utf-8") as f:
        json.dump(int8_eval_data, f, indent=2)

    return True

if __name__ == "__main__":
    success = evaluate_int8()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
