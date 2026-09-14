#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <driver/i2s.h>
#include "esp_timer.h"
#include <cstring>

#include "config.h"
#include "model_data.h"
#include "mfe.h"
#include "audio_capture.h"
#include "decision.h"
#include "asr_client.h"

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

#define OLED_RESET       -1
#define I2S_PORT         I2S_NUM_0
#define SAMPLE_RATE      16000
#define DMA_BUFFER_LEN   256

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

namespace {
  tflite::ErrorReporter* error_reporter = nullptr;
  const tflite::Model* model = nullptr;
  tflite::MicroInterpreter* interpreter = nullptr;
  TfLiteTensor* model_input = nullptr;
  TfLiteTensor* model_output = nullptr;
  uint8_t tensor_arena[TENSOR_ARENA_SIZE];

  audio_capture::RingBuffer g_ring;
  decision::DecisionEngine g_decision;
  bool g_wifi_ready = false;

  float g_last_conf = 0.0f;
  float g_last_latency_ms = 0.0f;
  bool g_last_vad = false;
}

// Render system telemetry directly to SSD1306 OLED
void update_oled(const char* status_text, float conf, float latency, bool triggered, bool vad) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(1);
  display.setCursor(14, 0);
  display.print("HERO ARISE EDGE");
  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  display.setCursor(0, 16);
  display.printf("State  : %s", status_text);

  display.setCursor(0, 26);
  display.printf("Conf   : %.1f %%  VAD:%s", conf * 100.0f, vad ? "Y" : "N");

  display.setCursor(0, 36);
  display.printf("Latency: %.2f ms  WiFi:%s", latency, g_wifi_ready ? "Y" : "N");

  if (triggered) {
    display.fillRect(0, 52, 128, 12, SSD1306_WHITE);
    display.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
    display.setCursor(4, 54);
    display.print(">> TRIGGER -> STREAMING <<");
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

// Reads DMA_BUFFER_LEN raw I2S samples straight from the mic (bypassing
// the ring buffer) and streams them to the ASR server as they arrive.
// Runs for ASR_STREAM_SECONDS. This intentionally blocks the main loop
// (wake-word detection is paused for this window, same as the existing
// post-trigger cooldown already implied) -- true concurrent
// listen+stream would need a second FreeRTOS task/queue, noted as a
// follow-up in STATUS.md rather than built here.
void stream_post_trigger_audio() {
  if (!g_wifi_ready || !asr::wifi_is_connected()) {
    Serial.println("[ASR] WiFi not connected, skipping stream");
    return;
  }

  asr::StreamSession session;
  if (!session.begin(ASR_SERVER_HOST, ASR_SERVER_PORT, ASR_STREAM_PATH)) {
    return;
  }

  const uint32_t total_samples = (uint32_t)(ASR_STREAM_SECONDS * SAMPLE_RATE);
  uint32_t sent = 0;
  int32_t raw_samples[DMA_BUFFER_LEN];
  int16_t pcm_samples[DMA_BUFFER_LEN];

  Serial.printf("[ASR] streaming %.1fs to %s:%d%s\n", ASR_STREAM_SECONDS, ASR_SERVER_HOST,
                ASR_SERVER_PORT, ASR_STREAM_PATH);

  while (sent < total_samples) {
    size_t bytes_read = 0;
    i2s_read(I2S_PORT, raw_samples, sizeof(raw_samples), &bytes_read, portMAX_DELAY);
    size_t n = bytes_read / sizeof(int32_t);

    for (size_t i = 0; i < n; i++) {
      int32_t v = raw_samples[i] >> I2S_SAMPLE_SHIFT;
      if (v > 32767) v = 32767;
      if (v < -32768) v = -32768;
      pcm_samples[i] = (int16_t)v;
    }

    if (!session.send_pcm_chunk(pcm_samples, n)) {
      Serial.println("[ASR] stream dropped mid-transfer");
      break;
    }
    sent += n;
  }

  session.end();
  Serial.printf("[ASR] stream complete (%u samples)\n", (unsigned)sent);
}

void setup() {
  Serial.begin(115200);

  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

  #ifdef PIN_LED_GREEN
  pinMode(PIN_LED_GREEN, OUTPUT);
  digitalWrite(PIN_LED_GREEN, LOW);
  #endif
  #ifdef PIN_LED_RED
  pinMode(PIN_LED_RED, OUTPUT);
  digitalWrite(PIN_LED_RED, HIGH);  // idle: red on, green off (swapped on wake)
  #endif

  Wire.begin(PIN_OLED_SDA, PIN_OLED_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("[ERROR] SSD1306 allocation failed!");
  }
  display.clearDisplay();
  display.display();

  update_oled("Booting...", 0.0f, 0.0f, false, false);

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

  mfe::init();
  setup_i2s();

  Serial.println("[WIFI] connecting...");
  g_wifi_ready = asr::connect_wifi(WIFI_SSID, WIFI_PASSWORD, WIFI_CONNECT_TIMEOUT_MS);
  if (!g_wifi_ready) {
    Serial.println("[WIFI] not connected -- wake-word detection still works, "
                    "ASR streaming will be skipped until WiFi is available.");
  }

  update_oled("Listening", 0.0f, 0.0f, false, false);
  Serial.println("[SYSTEM] Ready. Listening for 'Hero Arise'...");
}

void loop() {
  size_t bytes_read = 0;
  int32_t raw_samples[DMA_BUFFER_LEN];
  i2s_read(I2S_PORT, raw_samples, sizeof(raw_samples), &bytes_read, portMAX_DELAY);
  size_t n = bytes_read / sizeof(int32_t);

  bool hop_ready = g_ring.push_raw_i2s(raw_samples, n, I2S_SAMPLE_SHIFT);
  if (!hop_ready) {
    return;  // still filling the buffer, or mid-hop -- nothing to infer yet
  }

  static int16_t window_1s[audio_capture::kWindowSamples];
  g_ring.get_window(window_1s);

  const bool vad = audio_capture::is_speech(window_1s, AUDIO_VAD_RMS_THRESHOLD);
  g_last_vad = vad;

  int pred_class = -1;
  float target_conf = 0.0f;

  if (vad) {
    // Only pay for feature extraction + CNN inference when there's
    // plausibly speech in the window -- on silence/steady noise we skip
    // straight to a "no hit" decision update below. This is the low-idle-
    // CPU behavior the problem statement asks for; the previous firmware
    // ran full inference nonstop regardless of audio content.
    static int8_t features[mfe::kFeatureSize];
    mfe::extract(window_1s, features, INPUT_SCALE, INPUT_ZERO_POINT);
    memcpy(model_input->data.int8, features, mfe::kFeatureSize);

    int64_t bench_start = esp_timer_get_time();
    TfLiteStatus invoke_status = interpreter->Invoke();
    int64_t bench_end = esp_timer_get_time();
    g_last_latency_ms = (float)(bench_end - bench_start) / 1000.0f;

    if (invoke_status != kTfLiteOk) {
      Serial.println("[ERROR] Model inference failed!");
      return;
    }

    float scale = model_output->params.scale;
    int32_t zero_point = model_output->params.zero_point;
    float best_prob = -1.0f;
    for (int c = 0; c < MODEL_NUM_CLASSES; c++) {
      float prob = (model_output->data.int8[c] - zero_point) * scale;
      if (prob > best_prob) {
        best_prob = prob;
        pred_class = c;
      }
      if (c == CLASS_ID_TARGET) target_conf = prob;
    }
    if (target_conf < 0.0f) target_conf = 0.0f;
    if (target_conf > 1.0f) target_conf = 1.0f;
  } else {
    g_last_latency_ms = 0.0f;
  }
  g_last_conf = target_conf;

  uint32_t now = millis();
  decision::Result result = g_decision.process(pred_class, target_conf, now, vad);

  const char* status_text = result.triggered ? "TRIGGERED!"
                            : result.in_cooldown ? "Cooldown"
                            : vad ? "Speech..."
                            : "Listening";

  Serial.printf("[INFERENCE] Class:%d Conf:%5.1f%% VAD:%d Hits:%d Latency:%6.2fms State:%s\n",
                pred_class, target_conf * 100.0f, vad, result.consecutive_hits,
                g_last_latency_ms, status_text);

  update_oled(status_text, target_conf, g_last_latency_ms, result.triggered, vad);

  if (result.triggered) {
    #ifdef PIN_LED_GREEN
    digitalWrite(PIN_LED_GREEN, HIGH);
    #endif
    #ifdef PIN_LED_RED
    digitalWrite(PIN_LED_RED, LOW);
    #endif
    digitalWrite(PIN_BUZZER, HIGH);
    delay(120);
    digitalWrite(PIN_BUZZER, LOW);

    stream_post_trigger_audio();

    #ifdef PIN_LED_GREEN
    digitalWrite(PIN_LED_GREEN, LOW);
    #endif
    #ifdef PIN_LED_RED
    digitalWrite(PIN_LED_RED, HIGH);
    #endif
  }
}
