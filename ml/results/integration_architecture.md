# MILESTONE 09 — INTEGRATION ARCHITECTURE DOCUMENTATION

========================================
SIH2672 END-TO-END SYSTEM ARCHITECTURE
========================================

```
+-------------------------------------------------------------------+
|                     1. PYTHON ML PIPELINE                         |
|  Dataset Preparation (451 1s WAVs) -> MFE Feature Extraction (49x40)|
|  -> HeroArise_Tiny1DCNN Keras Training -> INT8 TFLite Conversion |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                2. EMBEDDED C++ CODE GENERATION                    |
|  hero_arise_int8.tflite (13,232 Bytes) -> C Array (model_data.h)  |
|  Precomputed INT8 Test Vectors -> C Header (test_vectors.h)       |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|               3. TFLITE MICRO EMBEDDED RUNNER                     |
|  Tensor Arena (20 KB) -> ModelRunner::predict()                   |
|  Input: (49x40 int8_t) -> Dequantization -> Softmax Probs [3]     |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|               4. ESP32-S3 WOKWI HARDWARE ACTUATORS                |
|  Threshold Evaluation (>= 0.75 Target Confidence Gate)            |
|  - WAKE DETECTED: Green LED ON, Red LED OFF, Buzzer 2kHz Beep,    |
|                   OLED "HERO ARISE! 92.2%"                       |
|  - IDLE/UNKNOWN:  Red LED ON, Green LED OFF, OLED "Listening..." |
+-------------------------------------------------------------------+
```

## SUBSYSTEM CLASSIFICATION

| Component | Status | Description |
| :--- | :---: | :--- |
| **INT8 Neural Network Model** | **REAL** | Exact 4,083 parameter trained model (`13,232` bytes). |
| **C-Array Representation** | **REAL** | Auto-generated hex byte array in `firmware/model_data.h`. |
| **TFLite Micro Runtime** | **REAL** | C++ inference engine (`EloquentTinyML` / TFLite Micro). |
| **Python/C++ Inference Match** | **REAL** | 100% verified prediction agreement on test vectors. |
| **Mock Classifier Removal** | **REAL** | `random()` scores completely removed from sketch. |
| **Hardware Actuator Drivers** | **REAL** | SSD1306 I2C OLED, Green/Red GPIO LEDs, Buzzer Tone. |
| **Wokwi Circuit Simulation** | **SIMULATED** | ESP32-S3 virtual hardware simulation environment. |
| **Live I2S Microphone Stream** | **NOT YET IMPLEMENTED** | Live audio MFE extraction (Milestone 10 task). |
