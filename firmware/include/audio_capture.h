#ifndef AUDIO_CAPTURE_H
#define AUDIO_CAPTURE_H

#include <cmath>
#include <cstddef>
#include <cstdint>

// Static-allocation 1.0s circular PCM ring buffer, fed by raw I2S samples
// and read out as the linear window mfe::compute_log_mfe() expects.
//
// No Arduino/I2S dependency -- pure buffer logic, so it's unit-testable on
// desktop the same way firmware/src/mfe.cpp is (see firmware/test/).

namespace audio_capture {

constexpr int kWindowSamples = 16000;  // 1.0s @ 16kHz, matches mfe::kSampleWindow
constexpr int kHopSamples = 320;       // 20ms hop, matches mfe internal framing

class RingBuffer {
 public:
  RingBuffer() { reset(); }

  void reset() {
    for (int i = 0; i < kWindowSamples; i++) buf_[i] = 0;
    write_pos_ = 0;
    total_written_ = 0;
    hop_accum_ = 0;
  }

  // Converts raw I2S samples (INMP441: 24-bit data left-justified in a
  // 32-bit word) to 16-bit PCM and pushes them into the ring buffer.
  // `shift` is the right-shift applied to the raw 32-bit word; 14 is a
  // common starting point for INMP441 but may need field calibration
  // against your specific wiring/gain -- see config.h I2S_SAMPLE_SHIFT.
  //
  // Returns true once a new hop's worth of samples (kHopSamples) has
  // landed AND the buffer has been filled at least once, i.e. a fresh
  // full 1.0s window is ready to be read with get_window().
  bool push_raw_i2s(const int32_t* raw_samples, size_t count, int shift) {
    bool hop_ready = false;
    for (size_t i = 0; i < count; i++) {
      int32_t v = raw_samples[i] >> shift;
      if (v > 32767) v = 32767;
      if (v < -32768) v = -32768;
      buf_[write_pos_] = (int16_t)v;
      write_pos_ = (write_pos_ + 1) % kWindowSamples;
      if (total_written_ < kWindowSamples) total_written_++;
      hop_accum_++;
      if (hop_accum_ >= kHopSamples) {
        hop_accum_ = 0;
        if (total_written_ >= kWindowSamples) hop_ready = true;
      }
    }
    return hop_ready;
  }

  bool is_full() const { return total_written_ >= kWindowSamples; }

  // Copies the last 1.0s of audio out in chronological order (oldest
  // first) into a contiguous buffer suitable for mfe::compute_log_mfe().
  void get_window(int16_t* out_1s) const {
    for (int i = 0; i < kWindowSamples; i++) {
      out_1s[i] = buf_[(write_pos_ + i) % kWindowSamples];
    }
  }

 private:
  int16_t buf_[kWindowSamples];
  int write_pos_;
  int total_written_;
  int hop_accum_;
};

// Cheap energy-based voice activity gate. Computes RMS over the most
// recent `hop_samples` of a chronologically-ordered window (as returned
// by RingBuffer::get_window) and compares it to a fixed threshold.
//
// Two things use this: (1) gating whether the CNN is invoked at all this
// hop -- the previous firmware ran inference on every single audio
// buffer nonstop, which is the opposite of what the "efficient" /
// low-idle-CPU part of the problem statement asks for; (2) the
// vad_speech input to decision::DecisionEngine::process(), matching how
// ml/src/decision.py's engine was designed to be gated.
//
// `rms_threshold` has no universal correct value -- it depends on your
// mic gain and ambient noise floor. Calibrate it against your own
// INMP441 + enclosure (log raw RMS over a few seconds of silence vs. a
// few seconds of speech and pick a value between them) rather than
// trusting this default blind.
inline int16_t compute_hop_rms(const int16_t* window_1s, int hop_samples = kHopSamples) {
  const int16_t* recent = window_1s + (kWindowSamples - hop_samples);
  int64_t sum_sq = 0;
  for (int i = 0; i < hop_samples; i++) {
    int32_t s = recent[i];
    sum_sq += (int64_t)s * s;
  }
  double mean_sq = (double)sum_sq / (double)hop_samples;
  double rms = mean_sq > 0.0 ? sqrt(mean_sq) : 0.0;
  if (rms > 32767.0) rms = 32767.0;
  return (int16_t)rms;
}

inline bool is_speech(const int16_t* window_1s, int16_t rms_threshold, int hop_samples = kHopSamples) {
  return compute_hop_rms(window_1s, hop_samples) >= rms_threshold;
}

}  // namespace audio_capture

#endif  // AUDIO_CAPTURE_H
