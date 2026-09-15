#ifndef CONFIG_H
#define CONFIG_H

// ─── Microcontroller & Hardware Pins (ESP32-S3) ─────────────────────────────

// OLED Display (SSD1306, I2C)
#define PIN_OLED_SDA       8
#define PIN_OLED_SCL       9
#define OLED_I2C_ADDRESS   0x3C
#define OLED_ADDR          OLED_I2C_ADDRESS   // Alias used by main.cpp
#define OLED_SCREEN_WIDTH  128
#define OLED_SCREEN_HEIGHT 64
#define SCREEN_WIDTH       OLED_SCREEN_WIDTH  // Alias used by main.cpp
#define SCREEN_HEIGHT      OLED_SCREEN_HEIGHT // Alias used by main.cpp

// Status LEDs
#define PIN_LED_GREEN      4
#define PIN_LED_RED        5

// Piezo Buzzer
#define PIN_BUZZER         6

// INMP441 I2S Digital Microphone
#define PIN_I2S_SCK        12  // I2S Bit Clock (BCLK)
#define PIN_I2S_WS         11  // I2S Word Select / LR Clock
#define PIN_I2S_SD         10  // I2S Serial Data In

// ─── Model Input & Output Parameters ────────────────────────────────────────
#define MODEL_INPUT_FRAMES 49
#define MODEL_INPUT_MELS   40
#define MODEL_INPUT_SIZE   (MODEL_INPUT_FRAMES * MODEL_INPUT_MELS) // 1960
#define MODEL_NUM_CLASSES  3

// ─── Wake-Word Detection Thresholds ─────────────────────────────────────────
#define WAKE_WORD_THRESHOLD  0.75f  // Python/test threshold
#define DETECTION_THRESHOLD  0.75f  // Firmware inference threshold

// ─── Class ID Definitions ───────────────────────────────────────────────────
#define CLASS_ID_TARGET    0  // "Hero Arise"
#define CLASS_ID_UNKNOWN   1  // "unknown_words"
#define CLASS_ID_NOISE     2  // "background_noise"

// ─── INT8 Model Quantization Parameters ─────────────────────────────────────
// (Verified from tflite_model_spec.json)
#define INPUT_SCALE        0.06526922f
#define INPUT_ZERO_POINT   84
#define OUTPUT_SCALE       0.00390625f
#define OUTPUT_ZERO_POINT  -128

// ─── Tensor Arena Allocation ─────────────────────────────────────────────────
#define TENSOR_ARENA_SIZE  (20 * 1024)

// ─── I2S / Audio Capture ─────────────────────────────────────────────────────
// INMP441 outputs 24-bit samples left-justified in a 32-bit I2S word. This
// shift brings that down to a usable int16 range. 14 is a reasonable
// starting point but depends on your specific board/gain -- calibrate by
// logging compute_hop_rms() over known silence vs. known speech and
// adjusting until the two are clearly separated (see also
// AUDIO_VAD_RMS_THRESHOLD below, which depends on this same calibration).
#define I2S_SAMPLE_SHIFT    14

// Energy-gate threshold for audio_capture::is_speech(). Raw int16 RMS.
// Uncalibrated default -- see I2S_SAMPLE_SHIFT comment above.
#define AUDIO_VAD_RMS_THRESHOLD  600

// ─── Wi-Fi / ASR Streaming ───────────────────────────────────────────────────
// Fill these in for your network and ASR receiver before flashing.
// scripts/asr_stream_server.py is a minimal reference receiver you can run
// on a laptop on the same network for an end-to-end demo.
#define WIFI_SSID            "ACT-ai_103819226960"
#define WIFI_PASSWORD         "58702087"
#define WIFI_CONNECT_TIMEOUT_MS  15000

#define ASR_SERVER_HOST       "192.168.0.6"  // your ASR receiver's LAN IP
#define ASR_SERVER_PORT       8000
#define ASR_STREAM_PATH       "/stream"

// How much post-wake audio to stream to the ASR server once triggered.
#define ASR_STREAM_SECONDS    3.0f

#endif // CONFIG_H
