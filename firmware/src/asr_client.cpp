#include "asr_client.h"

namespace asr {

bool connect_wifi(const char* ssid, const char* password, uint32_t timeout_ms) {
  if (WiFi.status() == WL_CONNECTED) return true;

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > timeout_ms) {
      Serial.println("[WIFI] connect timed out");
      return false;
    }
    delay(200);
  }
  Serial.print("[WIFI] connected, IP=");
  Serial.println(WiFi.localIP());
  return true;
}

bool wifi_is_connected() { return WiFi.status() == WL_CONNECTED; }

bool StreamSession::begin(const char* host, uint16_t port, const char* path,
                           const char* content_type) {
  if (!client_.connect(host, port)) {
    Serial.printf("[ASR] connect to %s:%u failed\n", host, port);
    return false;
  }

  client_.printf("POST %s HTTP/1.1\r\n", path);
  client_.printf("Host: %s:%u\r\n", host, port);
  client_.println("User-Agent: HeroArise-ESP32S3/1.0");
  client_.printf("Content-Type: %s\r\n", content_type);
  client_.println("Transfer-Encoding: chunked");
  client_.println("Connection: close");
  client_.println();
  return true;
}

bool StreamSession::send_pcm_chunk(const int16_t* pcm, size_t num_samples) {
  if (!client_.connected()) return false;

  const size_t byte_len = num_samples * sizeof(int16_t);
  if (byte_len == 0) return true;

  // HTTP chunk framing: <hex size>\r\n<data>\r\n
  client_.printf("%x\r\n", (unsigned)byte_len);
  size_t written = client_.write(reinterpret_cast<const uint8_t*>(pcm), byte_len);
  client_.print("\r\n");

  if (written != byte_len) {
    Serial.println("[ASR] short write, dropping session");
    return false;
  }
  return true;
}

void StreamSession::end() {
  if (client_.connected()) {
    client_.print("0\r\n\r\n");  // terminating chunk

    uint32_t start = millis();
    while (client_.connected() && millis() - start < 2000) {
      if (client_.available()) {
        String line = client_.readStringUntil('\n');
        Serial.print("[ASR] << ");
        Serial.println(line);
        if (line.length() <= 1) break;
      }
    }
  }
  client_.stop();
}

}  // namespace asr
