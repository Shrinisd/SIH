# MILESTONE 09 — INTEGRATION INVENTORY DOCUMENT

========================================
SIH2672 TINYML WOKWI INTEGRATION INVENTORY
========================================

## 1. REAL ML PROJECT ARCHITECTURE (PROJECT A)
* **Model File:** `ml/models/hero_arise_int8.tflite`
* **Model Architecture:** `HeroArise_Tiny1DCNN`
* **Total Parameters:** 4,083 parameters
* **INT8 Model Size:** 13,232 bytes (12.92 KB)
* **Input Tensor Shape:** `(1, 49, 40)` (49 time frames × 40 Mel bands)
* **Input Datatype:** `INT8` (Signed 8-bit Integer)
* **Input Quantization:** Scale = `0.0690709799528122`, Zero Point = `72`
* **Output Tensor Shape:** `(1, 3)`
* **Output Datatype:** `INT8`
* **Output Quantization:** Scale = `0.00390625`, Zero Point = `-128`
* **Class Mapping:**
  - `0`: `target_word` ("Hero Arise")
  - `1`: `unknown_words`
  - `2`: `background_noise`

## 2. MFE FEATURE EXTRACTION CONFIGURATION
* **Sample Rate:** 16,000 Hz (1.0s window = 16,000 samples)
* **FFT Length (`N_FFT`):** 512
* **Window Length:** 480 (30 ms)
* **Hop Length:** 320 (20 ms)
* **Mel Filterbank Channels (`N_MELS`):** 40
* **Frequency Range:** 20.0 Hz to 8000.0 Hz

## 3. WOKWI HARDWARE CIRCUIT & PIN MAPPING (PROJECT B)
* **Microcontroller:** ESP32-S3 (`board-esp32-s3-devkitc-1`)
* **OLED Display:** SSD1306 (128x64, I2C `0x3C`)
  - **SDA:** GPIO 8
  - **SCL:** GPIO 9
* **Green LED (Wake-Word Active):** GPIO 4
* **Red LED (Listening / Idle):** GPIO 5
* **Buzzer (Tone Alert):** GPIO 6

## 4. WOKWI LIBRARIES
* `Adafruit SSD1306`
* `Adafruit GFX Library`
* `EloquentTinyML` (TensorFlow Lite Micro C++ engine)

## 5. MOCK CLASSIFIER REMOVAL & INTEGRATION POINTS
* **Removed:** `random()` mock score generator.
* **Integrated:** `ModelRunner::predict()` calling `hero_arise_model` INT8 C-array.
* **Integration Interface:** `updateActuators(pred_class, target_confidence)` updates OLED, LEDs, and Buzzer using REAL TFLite output scores.
