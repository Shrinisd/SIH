# MILESTONE 10 FINAL REPORT — ESP32-S3 TO RASPBERRY PI PICO 2 W (RP2350) MIGRATION & DEPLOYMENT PIPELINE UNIFICATION

**Project:** SIH2672 — Low Latency and Efficient Voice Activator for Edge Devices  
**Target Wake Word:** "Hero Arise"  
**New Target Microcontroller:** Raspberry Pi Pico 2 W (RP2350 / ARM Cortex-M33)  
**Date:** August 28, 2026  

---

## 1. Summary of Work Executed

### Task 1 — Full Project Audit
- Complete project tree audited and documented in [`ml/results/milestone10_platform_audit.md`](file:///d:/SIH%202026/Voice_Activator_Project/ml/results/milestone10_platform_audit.md).
- Identified all ESP32-S3 pinouts, EloquentTinyML library dependencies, TFLM scripts, MFE configuration, Wokwi diagram files, actuator logic, test-vector files, and latency benchmarking scripts.

### Task 2 — Architecture Definition
- Defined unified end-to-end architecture:
  $$\text{Dataset} \rightarrow \text{Python MFE} \rightarrow \text{Training} \rightarrow \text{INT8 TFLite} \rightarrow \text{model\_data.h} \rightarrow \text{Pico 2 W Firmware} \rightarrow \text{I2S Microphone (INMP441)} \rightarrow \text{16kHz PCM} \rightarrow \text{MFE Preprocessing} \rightarrow \text{49}\times\text{40 INT8 Tensor} \rightarrow \text{TFLM C++ Engine} \rightarrow \text{Decision Logic} \rightarrow \text{Actuators (LED/Buzzer/OLED)}$$

### Task 3 — EloquentTinyML Removal Plan
- Audited EloquentTinyML compatibility with RP2350. EloquentTinyML is an ESP32/Arduino-centric wrapper containing hardcoded precompiled headers for older MCUs.
- Removed EloquentTinyML from the Pico 2 W deployment path.
- Standardized on direct C++ TensorFlow Lite Micro (`tflite::MicroInterpreter`) using native C++ headers.

### Task 4 — Model Compatibility Verification
- Parsed FlatBuffer metadata from `ml/models/hero_arise_int8.tflite` and saved verified report in [`ml/results/pico2w_model_compatibility.md`](file:///d:/SIH%202026/Voice_Activator_Project/ml/results/pico2w_model_compatibility.md).
- Verified parameters:
  - Input: `[1, 49, 40]`, dtype `INT8`, Scale = `0.06907098`, Zero Point = `72`
  - Output: `[1, 3]`, dtype `INT8`, Scale = `0.00390625`, Zero Point = `-128`
  - Model Size: `13,232 bytes` (12.92 KB), matching `hero_arise_model` byte-for-byte in `model_data.h`.
  - Required Operators: `CONV_2D`, `MAX_POOL_2D`, `MEAN`, `FULLY_CONNECTED`, `SOFTMAX`, `QUANTIZE`, `DEQUANTIZE`.

### Task 5 — MFE Preprocessing Specification
- Recorded exact signal processing parameters in [`ml/results/mfe_deployment_spec.md`](file:///d:/SIH%202026/Voice_Activator_Project/ml/results/mfe_deployment_spec.md):
  - Sample rate: `16,000 Hz` (16-bit mono PCM)
  - Frame length: `480 samples` (30 ms), Frame stride: `320 samples` (20 ms), FFT size: `512`
  - Mel Filterbank: `40 bands`, Freq range: `20.0 Hz` to `8000.0 Hz`
  - Log offset: `1e-6`, feature matrix shape: `(49, 40)`
  - Quantization formula: $\text{int8} = \text{clamp}(\text{round}(\frac{\text{log\_mfe}}{0.06907098} + 72), -128, 127)$

### Task 6 — Firmware Structure Refactoring
- Created modular directory structure without deleting working legacy files:
  - `firmware/include/config.h`: Pico 2 W hardware GPIO pinout & quantization parameters.
  - `firmware/model/model_data.h`: Alignment-preserved INT8 model byte array.
  - `firmware/src/audio_capture.h` / `.cpp`: Hardware abstraction layer for 16kHz PCM audio capture.
  - `firmware/src/mfe.h` / `.cpp`: Log-Mel Filterbank Energy feature extraction module.
  - `firmware/src/model_runner.h` / `.cpp`: Direct C++ TFLite Micro inference runner.
  - `firmware/src/decision.h` / `.cpp`: Thresholding engine & peripheral actuator manager.
  - `firmware/src/main.cpp`: Modular application entry point.

### Task 7 — Audio Hardware Abstraction
- Implemented `AudioCapture` class (`firmware/src/audio_capture.h`) exposing clean APIs (`begin()`, `read_samples()`, `available()`, `isLiveMicActive()`) delivering 16 kHz mono 16-bit PCM.

### Task 8 — Deterministic Test Mode Verification
- Retained embedded test-vector execution path using precomputed test vectors (`firmware/test_vectors.h`).
- Executed empirical verification script (`scripts/verify_python_cpp.py`), confirming 100% agreement between Python TFLite and C++ embedded output:
  - Target Word sample #31 -> Predicted Class 0 ("Hero Arise"), Confidence = 92.19% (PASS)
  - Unknown Words sample #56 -> Predicted Class 1 ("unknown_words") (PASS)
  - Background Noise sample #15 -> Predicted Class 2 ("background_noise") (PASS)

### Task 9 — Wokwi Simulation Limits Documented
- Documented in [`ml/results/wokwi_platform_status.md`](file:///d:/SIH%202026/Voice_Activator_Project/ml/results/wokwi_platform_status.md) that Wokwi currently simulates RP2040 / ESP32, but lacks native RP2350 hardware simulation. Wokwi is preserved strictly as an RP2040 test-vector/firmware simulator.

### Task 10 — Production Build Strategy
- Formulated Pico 2 W production build strategy using official Raspberry Pi Pico SDK and CMake (`firmware/CMakeLists.txt`), compiling native C++ source files against RP2350 target.

### Task 11 — Live Audio Capture Deferred
- Physical INMP441 live I2S microphone capture was stubbed and deferred until post-Milestone 10, prioritizing model, TFLM runtime, and build system verification.

---

## 2. Status of Identified Artifacts

| Component | Status | Details |
| :--- | :--- | :--- |
| **Existing ML Model** | **Unchanged** | `hero_arise_int8.tflite` (13,232 bytes, 4,083 parameters) retained |
| **Wake Word** | **Unchanged** | "Hero Arise" (Class ID 0) |
| **Dataset & Splitting** | **Unchanged** | 16kHz mono audio samples retained |
| **EloquentTinyML** | **Removed** | Replaced with direct C++ TensorFlow Lite Micro API |
| **Pico 2 W Firmware** | **Refactored** | Modular architecture built under `firmware/src/`, `include/`, `model/` |
| **Test Vector Verification** | **PASS** | 100% agreement across all classes |

---

## 3. Outstanding Items & Next Steps (Milestone 11 Readiness)

1. Physical INMP441 I2S digital microphone hardware integration on GP26/GP27/GP28.
2. Hardware latency profiling on physical RP2350 Cortex-M33 silicon.

---

## 4. Final Milestone Declaration

MILESTONE 10 STATUS:
PASS
