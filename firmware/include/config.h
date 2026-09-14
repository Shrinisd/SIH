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
#define INPUT_SCALE        0.06907098f
#define INPUT_ZERO_POINT   72
#define OUTPUT_SCALE       0.00390625f
#define OUTPUT_ZERO_POINT  -128

// ─── Tensor Arena Allocation ─────────────────────────────────────────────────
#define TENSOR_ARENA_SIZE  (20 * 1024)

#endif // CONFIG_H
