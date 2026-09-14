# MILESTONE 10 — FULL PROJECT PLATFORM AUDIT REPORT

**Project:** SIH2672 — Low Latency and Efficient Voice Activator for Edge Devices  
**Target Wake Word:** "Hero Arise"  
**Migration Scope:** ESP32-S3 DevKitC-1 → Raspberry Pi Pico 2 W (RP2350 / ARM Cortex-M33)  
**Date:** August 28, 2026  

---

## 1. Complete Project Directory Tree

```
Voice_Activator_Project/
├── .venv/                         # Local Python Virtual Environment
├── dataset/                       # Dataset Directory
│   ├── processed/                 # Extracted MFE features (.npy) and split metadata
│   └── raw/                       # Audio WAV samples (target_word, unknown_words, background_noise)
├── firmware/                      # Edge Device Firmware
│   ├── config.h                   # Pinout definitions & TFLite Micro quantization constants
│   ├── model_data.h               # INT8 TFLite model C array byte array (13,232 bytes)
│   ├── model_runner.cpp           # TFLite Micro engine wrapper (currently using EloquentTinyML)
│   ├── model_runner.h             # ModelRunner class header
│   ├── sketch.ino                 # Arduino main sketch with actuator control & test vector loop
│   └── test_vectors.h             # Precomputed INT8 test vector header (3 samples: target, unknown, noise)
├── ml/                            # Machine Learning Workflows & Artifacts
│   ├── models/                    # Trained model files
│   │   ├── hero_arise_best.keras   # Full Keras model (4,083 parameters)
│   │   ├── hero_arise_float32.tflite # Unquantized Float32 TFLite model (22.9 KB)
│   │   └── hero_arise_int8.tflite  # Full INT8 Quantized TFLite model (12.92 KB / 13,232 bytes)
│   ├── results/                   # Benchmark & evaluation metrics
│   │   ├── embedded_test_vectors/ # JSON test vector files per class
│   │   ├── dataset_summary.json   # Audio counts and class breakdown
│   │   ├── int8_evaluation.json   # INT8 model accuracy and confusion matrix
│   │   ├── mfe_config.json        # Signal processing configuration parameters
│   │   ├── tflite_model_spec.json # Verified FlatBuffer quantization parameters
│   │   └── latency_report.json    # PC-based end-to-end latency benchmarks
│   └── src/                       # ML source code modules
│       ├── config.py              # Central ML pipeline configuration
│       └── model.py               # HeroArise_Tiny1DCNN model architecture
├── scripts/                       # Python Pipeline Tooling
│   ├── analyze_model.py           # Model parameter counter & layer inspector
│   ├── benchmark_end_to_end.py    # PC pipeline latency benchmark script
│   ├── convert_int8.py            # Representative dataset INT8 converter
│   ├── evaluate_int8.py           # Test set INT8 evaluation script
│   ├── extract_mfe.py             # Log Mel Filterbank Energy feature extractor
│   ├── generate_test_vectors.py   # High-confidence test vector generator
│   ├── inspect_tflite.py          # TFLite FlatBuffer metadata & tensor inspector
│   ├── prepare_dataset.py         # Audio dataset loader & split generator
│   ├── tflite_to_c_array.py       # Binary to C header array converter
│   ├── train_model.py             # Model training script
│   └── validate_dataset.py        # Dataset audio validation script
├── wokwi/                         # Wokwi Web Simulator Assets
│   ├── diagram.json               # ESP32-S3 circuit diagram
│   └── libraries.txt              # Arduino library list (EloquentTinyML, Adafruit SSD1306, GFX)
└── requirements.txt               # Python package dependencies
```

---

## 2. Identified ESP32-Specific Code

1. **`firmware/config.h`**:
   - GPIO Pin mappings hardcoded for ESP32-S3 DevKitC-1 (`PIN_OLED_SDA 8`, `PIN_OLED_SCL 9`, `PIN_LED_GREEN 4`, `PIN_LED_RED 5`, `PIN_BUZZER 6`).
   - Header comments explicitly referencing `(ESP32-S3 Wokwi Circuit)`.
2. **`firmware/sketch.ino`**:
   - `Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL)` using ESP32 pin definitions.
   - Serial banner output referencing `Target MCU: ESP32-S3`.
   - ESP32 microsecond timing `micros()` usage in loop timing.
3. **`firmware/model_runner.cpp`**:
   - Inclusion of `<EloquentTinyML.h>` which uses ESP32-specific header abstractions and Arduino wrapper constructs.
4. **`wokwi/diagram.json`**:
   - Component declaration `"type": "board-esp32-s3-devkitc-1"`.
   - Wiring pin connections tied to ESP32 pin names (`esp:8`, `esp:9`, `esp:4`, `esp:5`, `esp:6`).

---

## 3. Identified EloquentTinyML Dependencies

- **`wokwi/libraries.txt`**: Line 4 lists `EloquentTinyML`.
- **`firmware/model_runner.cpp`**: Line 6 contains `#include <EloquentTinyML.h>` and instantiates static interpreter object `static Eloquent::TF::Sequential<MODEL_INPUT_SIZE, MODEL_NUM_CLASSES, TENSOR_ARENA_SIZE> tf;`.
- **`firmware/sketch.ino`**: Wraps model inference through `ModelRunner::predict()` which delegates directly to EloquentTinyML's `tf.predict()`.

---

## 4. Identified TensorFlow Lite Micro Dependencies

- **Python Ecosystem**: `tensorflow` (v2.18+), using `tf.lite.Interpreter`, `tf.lite.TFLiteConverter`, `tf.lite.OpsSet.TFLITE_BUILTINS_INT8`.
- **C++ Microcontroller Runtime**: Native C++ TFLM library headers (`tensorflow/lite/micro/micro_interpreter.h`, `tensorflow/lite/micro/all_ops_resolver.h`, `tensorflow/lite/schema/schema_generated.h`).

---

## 5. Identified Model Conversion Scripts

- **`scripts/convert_int8.py`**: Converts Keras model (`hero_arise_best.keras`) to Float32 TFLite and full INT8 quantized TFLite (`hero_arise_int8.tflite`) using representative dataset calibration.
- **`scripts/tflite_to_c_array.py`**: Reads `hero_arise_int8.tflite` binary file and writes C array `hero_arise_model[]` to `firmware/model_data.h`.
- **`scripts/inspect_tflite.py`**: Parses FlatBuffer details and generates `ml/results/tflite_model_spec.json`.

---

## 6. Identified Exact Current MFE Implementation

- **Configuration File**: `ml/src/config.py`
  - Audio Sample Rate: `16,000 Hz`
  - Channels: `1` (Mono)
  - Bit Depth: `16-bit PCM`
  - Audio Window: `1.0 sec` (`16,000 samples`)
  - FFT Window Length (`N_FFT`): `512`
  - Frame Duration (`WIN_LENGTH`): `480 samples` (`30 ms @ 16kHz`)
  - Frame Stride (`HOP_LENGTH`): `320 samples` (`20 ms @ 16kHz`)
  - Mel Filterbank Bands (`N_MELS`): `40`
  - Frequency Range: `20.0 Hz` – `8000.0 Hz`
  - Log Offset: `1e-6`
- **Extraction Function**: `compute_mfe()` in `scripts/extract_mfe.py`
  - Normalizes int16 audio array to float32 `[-1.0, 1.0]` by dividing by `32768.0`.
  - Calls `librosa.feature.melspectrogram(y=audio_float, sr=16000, n_fft=512, win_length=480, hop_length=320, n_mels=40, fmin=20.0, fmax=8000.0, center=False)`.
  - Converts power to log MFE: `log_mfe = np.log(mel_spec + 1e-6)`.
  - Transposes matrix shape to `(49, 40)` (Time Steps × Mel Bands).

---

## 7. Identified Wokwi-Specific Files

- **`wokwi/diagram.json`**: Board layout for ESP32-S3 DevKitC-1 with SSD1306 OLED, Green LED, Red LED, and Buzzer.
- **`wokwi/libraries.txt`**: Library dependencies (`Adafruit SSD1306`, `Adafruit GFX Library`, `EloquentTinyML`).

---

## 8. Identified Actuator Code

- **OLED Display**: `Adafruit_SSD1306 display` on I2C address `0x3C` (`firmware/sketch.ino`).
- **Green LED**: `PIN_LED_GREEN` (GPIO 4 on ESP32-S3) turned HIGH on wake-word detection.
- **Red LED**: `PIN_LED_RED` (GPIO 5 on ESP32-S3) turned HIGH when idle / no wake-word.
- **Piezo Buzzer**: `PIN_BUZZER` (GPIO 6 on ESP32-S3) pulsed using `tone(PIN_BUZZER, 2000, 150)` on detection.

---

## 9. Identified Test-Vector Code

- **`scripts/generate_test_vectors.py`**: Identifies highest-confidence correctly classified sample for each class, quantizes features using `int8_feat = clamp(round(feat / in_scale + in_zero), -128, 127)`, exports JSON files under `ml/results/embedded_test_vectors/` and C++ header `firmware/test_vectors.h`.
- **`firmware/test_vectors.h`**: Header file containing `struct TestVector` and static `TEST_VECTORS[]` array with 3 samples (Class 0: "Hero Arise", Class 1: "unknown_words", Class 2: "background_noise").
- **`firmware/sketch.ino`**: `loop()` iterates deterministically over `TEST_VECTORS`, evaluates inference, prints latencies and probabilities to Serial.

---

## 10. Identified Latency Benchmarking Code

- **`scripts/benchmark_end_to_end.py`**: Benchmarks MFE extraction, Float32 inference, INT8 inference, and decision logic across 1,000 runs on PC; outputs `ml/results/latency_report.json`, `ml/results/latency_comparison.csv`, and `ml/results/performance_summary.md`.
- **`scripts/benchmark_inference.py` / `scripts/profile_pipeline.py`**: Runner scripts for pipeline timing.

---

## Audit Conclusion

All project components have been audited. The repository contains a complete, working ML training and verification pipeline. The firmware and simulator components currently contain hardcoded ESP32-S3 and EloquentTinyML dependencies that will be systematically refactored for RP2350 / Pico 2 W deployment without altering trained model weights or dataset files.
