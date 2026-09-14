#ifndef ASR_CLIENT_H
#define ASR_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <cstdint>

// Post-wake audio streaming to a remote ASR server -- this is the half of
// the SIH2672 problem statement ("upon detecting the wake word, the
// system must efficiently stream subsequent audio to a remote ASR
// server") that had no implementation at all before this.
//
// Design: once woken, the device streams raw 16kHz/16-bit mono PCM to
// an HTTP endpoint using chunked transfer encoding -- each ~20ms hop of
// audio is written to the socket as soon as it's captured, rather than
// buffering the whole post-wake clip in RAM and sending it after the
// fact. A minimal reference receiver that speaks this same wire format
// is in scripts/asr_stream_server.py.
//
// This intentionally does not depend on any particular ASR backend.
// Point ASR_SERVER_HOST/PORT/PATH (config.h) at whatever you're running
// -- the reference server, a self-hosted whisper.cpp/faster-whisper
// server, or a small proxy in front of a hosted ASR API.

namespace asr {

// Blocks until connected or timeout. Safe to call once from setup().
bool connect_wifi(const char* ssid, const char* password, uint32_t timeout_ms);

bool wifi_is_connected();

// Opens a TCP connection to host:port and writes HTTP request headers
// for a chunked POST to `path`. Returns false on connect failure.
class StreamSession {
 public:
  bool begin(const char* host, uint16_t port, const char* path,
             const char* content_type = "audio/L16;rate=16000;channels=1");

  // Writes one HTTP chunk containing `num_samples` int16 PCM samples
  // (little-endian, as captured). Returns false if the write failed
  // (e.g. connection dropped) -- caller should abort the session.
  bool send_pcm_chunk(const int16_t* pcm, size_t num_samples);

  // Writes the terminating zero-length chunk, waits briefly for and logs
  // the server's response line, then closes the connection.
  void end();

  bool connected() const { return client_.connected(); }

 private:
  WiFiClient client_;
};

}  // namespace asr

#endif  // ASR_CLIENT_H
