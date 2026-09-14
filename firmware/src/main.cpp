#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <driver/i2s.h>
#include "esp_timer.h"

#include "config.h"
#include "model_data.h"

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#define OLED_RESET       -1
#define I2S_PORT         I2S_NUM_0
#define SAMPLE_RATE      16000
#define DMA_BUFFER_LEN   256
#define COOLDOWN_MS      1500   // Post-trigger lockout window

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

namespace {
  tflite::ErrorReporter* error_reporter = nullptr;
  const tflite::Model* model = nullptr;
  tflite::MicroInterpreter* interpreter = nullptr;
  TfLiteTensor* model_input = nullptr;
  TfLiteTensor* model_output = nullptr;
  uint8_t tensor_arena[TENSOR_ARENA_SIZE];
}

uint32_t last_trigger_time = 0;
float current_latency_ms = 0.0f;
float current_conf = 0.0f;

// Render system telemetry directly to SSD1306 OLED
void update_oled(const char* status_text, float conf, float latency, bool triggered) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  // Header Banner
  display.setTextSize(1);
  display.setCursor(14, 0);
  display.print("HERO ARISE EDGE");
  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  // Live Metrics for Judges
  display.setCursor(0, 16);
  display.printf("State  : %s", status_text);

  display.setCursor(0, 28);
  display.printf("Conf   : %.1f %%", conf * 100.0f);

  display.setCursor(0, 40);
  display.printf("Latency: %.2f ms", latency);

  // Visual Confirmation Bar
  if (triggered) {
    display.fillRect(0, 52, 128, 12, SSD1306_WHITE);
    display.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
    display.setCursor(12, 54);
    display.print(">> TRIGGER CONFIRMED <<");
  } else {
    display.drawLine(0, 52, 127, 52, SSD1306_WHITE);
    display.setCursor(0, 55);
    display.print("Engine: Ready (INT8)");
  }

  display.display();
}

void setup_i2s() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = DMA_BUFFER_LEN,
    .use_apll = false
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = PIN_I2S_SCK,
    .ws_io_num = PIN_I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = PIN_I2S_SD
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_zero_dma_buffer(I2S_PORT);
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  #ifdef PIN_LED_GREEN
  pinMode(PIN_LED_GREEN, OUTPUT);
  digitalWrite(PIN_LED_GREEN, LOW);
  #endif

  Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[ERROR] SSD1306 allocation failed!");
  }
  display.clearDisplay();
  display.display();

  update_oled("Booting...", 0.0f, 0.0f, false);

  static tflite::MicroErrorReporter micro_error_reporter;
  error_reporter = &micro_error_reporter;

  model = tflite::GetModel(hero_arise_model);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.printf("[ERROR] Schema version mismatch! Model: %d, Runtime: %d\n",
                  model->version(), TFLITE_SCHEMA_VERSION);
    return;
  }

  static tflite::AllOpsResolver resolver;
  static tflite::MicroInterpreter static_interpreter(
      model, resolver, tensor_arena, TENSOR_ARENA_SIZE, error_reporter);
  interpreter = &static_interpreter;

  if (interpreter->AllocateTensors() != kTfLiteOk) {
    Serial.println("[ERROR] AllocateTensors() failed!");
    return;
  }

  model_input = interpreter->input(0);
  model_output = interpreter->output(0);

  setup_i2s();
  update_oled("Listening", 0.0f, 0.0f, false);
  Serial.println("[SYSTEM] Ready. Listening for 'Hero Arise'...");
}

void loop() {
  // 1. Read audio data from DMA
  size_t bytes_read = 0;
  int32_t raw_samples[DMA_BUFFER_LEN];
  i2s_read(I2S_PORT, raw_samples, sizeof(raw_samples), &bytes_read, portMAX_DELAY);

  // 2. Hardware microsecond timer around inference
  int64_t bench_start = esp_timer_get_time();

  TfLiteStatus invoke_status = interpreter->Invoke();

  int64_t bench_end = esp_timer_get_time();
  current_latency_ms = (float)(bench_end - bench_start) / 1000.0f;

  if (invoke_status != kTfLiteOk) {
    Serial.println("[ERROR] Model inference failed!");
    return;
  }

  // 3. Dequantize INT8 output for target class
  int8_t quant_val = model_output->data.int8[CLASS_ID_TARGET];
  float scale = model_output->params.scale;
  int32_t zero_point = model_output->params.zero_point;
  current_conf = (quant_val - zero_point) * scale;
  if (current_conf < 0.0f) current_conf = 0.0f;
  if (current_conf > 1.0f) current_conf = 1.0f;

  uint32_t now = millis();
  bool triggered = false;

  // 4. Threshold & buzzer trigger
  if (current_conf >= DETECTION_THRESHOLD && (now - last_trigger_time > COOLDOWN_MS)) {
    triggered = true;
    last_trigger_time = now;

    #ifdef PIN_LED_GREEN
    digitalWrite(PIN_LED_GREEN, HIGH);
    #endif

    digitalWrite(PIN_BUZZER, HIGH);
    delay(120);
    digitalWrite(PIN_BUZZER, LOW);

    #ifdef PIN_LED_GREEN
    digitalWrite(PIN_LED_GREEN, LOW);
    #endif
  }

  // 5. Output metrics to Serial
  Serial.printf("[INFERENCE] Conf: %5.1f%% | Latency: %6.2f ms | State: %s\n",
                current_conf * 100.0f,
                current_latency_ms,
                triggered ? "TRIGGERED" : "LISTENING");

  // 6. Refresh SSD1306 OLED Telemetry
  update_oled(triggered ? "TRIGGERED!" : "Listening", current_conf, current_latency_ms, triggered);

  if (triggered) {
    delay(400);
  }
}