import os
import sys
import time
import csv
import json
import numpy as np
import tensorflow as tf
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.config import PROCESSED_DATA_DIR, MODELS_DIR, RESULTS_DIR, CLASS_MAP
from ml.src.decision import DecisionEngine
from scripts.extract_mfe import compute_mfe

def run_benchmarks():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    keras_path = MODELS_DIR / "hero_arise_best.keras"
    int8_tflite_path = MODELS_DIR / "hero_arise_int8.tflite"
    
    if not keras_path.exists() or not int8_tflite_path.exists():
        print("ERROR: Required model files missing!")
        return False

    # Instantiate Priority 2 & 3 DecisionEngine
    decision_engine = DecisionEngine()

    # Load Float32 model and INT8 TFLite interpreter
    keras_model = tf.keras.models.load_model(str(keras_path))
    
    interpreter = tf.lite.Interpreter(model_path=str(int8_tflite_path))
    interpreter.allocate_tensors()
    in_details = interpreter.get_input_details()[0]
    out_details = interpreter.get_output_details()[0]
    
    in_scale, in_zero_point = in_details.get("quantization", (1.0, 0))
    out_scale, out_zero_point = out_details.get("quantization", (1.0, 0))
    if in_scale == 0: in_scale = 1.0
    if out_scale == 0: out_scale = 1.0

    # Create 1-second synthetic 16kHz audio sample (16000 int16 samples)
    t = np.linspace(0, 1.0, 16000, False)
    test_audio = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)

    # 1. Warm-up iterations (100 runs)
    print("=" * 50)
    print("WARMING UP PIPELINE (100 Iterations)")
    print("=" * 50)
    for _ in range(100):
        feat = compute_mfe(test_audio)
        feat_batch = np.expand_dims(feat, axis=0)
        _ = keras_model(feat_batch, training=False)
        
        sample_quant = np.round(feat / in_scale + in_zero_point).clip(-128, 127).astype(np.int8)
        sample_quant = np.expand_dims(sample_quant, axis=0)
        interpreter.set_tensor(in_details["index"], sample_quant)
        interpreter.invoke()
        _ = interpreter.get_tensor(out_details["index"])

    # 2. Main Benchmark Runs (1,000 Iterations)
    N_RUNS = 1000
    print(f"BENCHMARKING PIPELINE ({N_RUNS} Warm Iterations)")
    
    mfe_times = []
    float32_cnn_times = []
    int8_cnn_times = []
    decision_times = []
    end_to_end_times = []

    latest_monitor_str = ""

    for i in range(N_RUNS):
        # Stage B: MFE Feature Extraction
        t0 = time.perf_counter()
        mfe_feat = compute_mfe(test_audio)
        t1 = time.perf_counter()
        
        # Stage C: Float32 Inference
        mfe_batch = np.expand_dims(mfe_feat, axis=0)
        _ = keras_model(mfe_batch, training=False)
        t2 = time.perf_counter()
        
        # Stage D: INT8 Quantized Inference
        sample_quant = np.round(mfe_feat / in_scale + in_zero_point).clip(-128, 127).astype(np.int8)
        sample_quant = np.expand_dims(sample_quant, axis=0)
        interpreter.set_tensor(in_details["index"], sample_quant)
        interpreter.invoke()
        raw_out = interpreter.get_tensor(out_details["index"])[0]
        t3 = time.perf_counter()
        
        # Stage E: Decision Logic & Live Monitor Telemetry
        dequant_out = (raw_out.astype(np.float32) - out_zero_point) * out_scale
        target_prob = float(dequant_out[0])
        pred_class = int(np.argmax(dequant_out))
        
        # VAD Energy check (RMS of input audio)
        rms = np.sqrt(np.mean(test_audio.astype(np.float32)**2))
        vad_speech = bool(rms > 100.0)

        # Real software pipeline latency (PC)
        t_start_software = t0
        t4 = time.perf_counter()
        software_latency_ms = (t4 - t_start_software) * 1000.0

        current_sim_time_ms = 1000 + (i * 50)
        dec_res = decision_engine.process_prediction(
            pred_class=pred_class, 
            target_conf=target_prob, 
            current_time_ms=current_sim_time_ms, 
            vad_speech=vad_speech
        )
        
        latest_monitor_str = decision_engine.format_live_monitor(
            res=dec_res, 
            target_conf=target_prob, 
            vad_speech=vad_speech, 
            latency_ms=software_latency_ms
        )

        mfe_ms = (t1 - t0) * 1000.0
        float_ms = (t2 - t1) * 1000.0
        int8_ms = (t3 - t2) * 1000.0
        dec_ms = (t4 - t3) * 1000.0
        e2e_ms = mfe_ms + int8_ms + dec_ms

        mfe_times.append(mfe_ms)
        float32_cnn_times.append(float_ms)
        int8_cnn_times.append(int8_ms)
        decision_times.append(dec_ms)
        end_to_end_times.append(e2e_ms)

    print("\nLATEST LIVE MONITOR DISPLAY (Iteration 1000 Sample):")
    print(latest_monitor_str)

    def calc_stats(arr):
        return {
            "min": float(np.min(arr)),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "p95": float(np.percentile(arr, 95)),
            "max": float(np.max(arr))
        }

    mfe_stats = calc_stats(mfe_times)
    float32_stats = calc_stats(float32_cnn_times)
    int8_stats = calc_stats(int8_cnn_times)
    decision_stats = calc_stats(decision_times)
    e2e_stats = calc_stats(end_to_end_times)

    # 3. Acceptance Gate Evaluation
    p95_e2e = e2e_stats["p95"]
    median_e2e = e2e_stats["median"]

    if p95_e2e < 200.0:
        gate_status = "PASS"
        pc_latency_status = "PASS ON PC SOFTWARE PIPELINE"
    elif median_e2e < 200.0:
        gate_status = "WARNING"
        pc_latency_status = "WARNING (Median < 200ms, P95 >= 200ms)"
    else:
        gate_status = "FAIL"
        pc_latency_status = "FAIL (Median >= 200ms)"

    print("\n" + "=" * 50)
    print("LATENCY BENCHMARK RESULTS (PC Execution)")
    print("=" * 50)
    print(f"MFE Extraction Median:   {mfe_stats['median']:.3f} ms (P95: {mfe_stats['p95']:.3f} ms)")
    print(f"Float32 CNN Median:      {float32_stats['median']:.3f} ms (P95: {float32_stats['p95']:.3f} ms)")
    print(f"INT8 CNN Median:         {int8_stats['median']:.3f} ms (P95: {int8_stats['p95']:.3f} ms)")
    print(f"Decision Logic Median:   {decision_stats['median']:.3f} ms (P95: {decision_stats['p95']:.3f} ms)")
    print("-" * 50)
    print(f"END-TO-END MEDIAN:       {e2e_stats['median']:.3f} ms")
    print(f"END-TO-END P95:          {e2e_stats['p95']:.3f} ms")
    print(f"HARD TARGET:             < 200.0 ms")
    print(f"200 ms GATE STATUS:      {gate_status}")
    print("=" * 50)

    # 4. Save latency_report.json
    report_data = {
        "mfe_min_ms": round(mfe_stats["min"], 3),
        "mfe_mean_ms": round(mfe_stats["mean"], 3),
        "mfe_median_ms": round(mfe_stats["median"], 3),
        "mfe_p95_ms": round(mfe_stats["p95"], 3),
        "mfe_max_ms": round(mfe_stats["max"], 3),
        
        "float32_cnn_min_ms": round(float32_stats["min"], 3),
        "float32_cnn_mean_ms": round(float32_stats["mean"], 3),
        "float32_cnn_median_ms": round(float32_stats["median"], 3),
        "float32_cnn_p95_ms": round(float32_stats["p95"], 3),
        "float32_cnn_max_ms": round(float32_stats["max"], 3),

        "int8_cnn_min_ms": round(int8_stats["min"], 3),
        "int8_cnn_mean_ms": round(int8_stats["mean"], 3),
        "int8_cnn_median_ms": round(int8_stats["median"], 3),
        "int8_cnn_p95_ms": round(int8_stats["p95"], 3),
        "int8_cnn_max_ms": round(int8_stats["max"], 3),

        "end_to_end_median_ms": round(e2e_stats["median"], 3),
        "end_to_end_p95_ms": round(e2e_stats["p95"], 3),
        "target_latency_ms": 200,
        "latency_status": gate_status
    }

    with open(RESULTS_DIR / "latency_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # 5. Save latency_comparison.csv
    csv_path = RESULTS_DIR / "latency_comparison.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["stage", "min_ms", "mean_ms", "median_ms", "p95_ms", "max_ms"])
        writer.writerow(["mfe_feature_extraction", mfe_stats["min"], mfe_stats["mean"], mfe_stats["median"], mfe_stats["p95"], mfe_stats["max"]])
        writer.writerow(["float32_cnn_inference", float32_stats["min"], float32_stats["mean"], float32_stats["median"], float32_stats["p95"], float32_stats["max"]])
        writer.writerow(["int8_cnn_inference", int8_stats["min"], int8_stats["mean"], int8_stats["median"], int8_stats["p95"], int8_stats["max"]])
        writer.writerow(["decision_logic", decision_stats["min"], decision_stats["mean"], decision_stats["median"], decision_stats["p95"], decision_stats["max"]])
        writer.writerow(["end_to_end_total", e2e_stats["min"], e2e_stats["mean"], e2e_stats["median"], e2e_stats["p95"], e2e_stats["max"]])

    # 6. Generate performance_summary.md
    int8_bytes = (MODELS_DIR / "hero_arise_int8.tflite").stat().st_size
    float_bytes = (MODELS_DIR / "hero_arise_float32.tflite").stat().st_size
    
    summary_md = f"""# HERO ARISE TINYML PERFORMANCE SUMMARY

========================================
HERO ARISE TINYML PERFORMANCE
========================================

MODEL:
HeroArise_Tiny1DCNN

PARAMETERS:
4,083

FLOAT32 MODEL SIZE:
{float_bytes / 1024.0:.2f} KB ({float_bytes:,} bytes)

INT8 MODEL SIZE:
{int8_bytes / 1024.0:.2f} KB ({int8_bytes:,} bytes)

MFE MEDIAN:
{mfe_stats['median']:.3f} ms

CNN INT8 MEDIAN:
{int8_stats['median']:.3f} ms

END-TO-END MEDIAN:
{e2e_stats['median']:.3f} ms

END-TO-END P95:
{e2e_stats['p95']:.3f} ms

HARD TARGET:
< 200 ms

PC LATENCY STATUS:
{pc_latency_status}

WOKWI STATUS:
NOT YET TESTED — PENDING MILESTONE 11

PHYSICAL ESP32-S3 STATUS:
NOT MEASURED — HARDWARE UNAVAILABLE

========================================
"""
    with open(RESULTS_DIR / "performance_summary.md", "w", encoding="utf-8") as f:
        f.write(summary_md)

    return True

if __name__ == "__main__":
    success = run_benchmarks()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
