#ifndef DECISION_H
#define DECISION_H

#include <cstdint>

// Firmware port of ml/src/decision.py's DecisionEngine.
//
// The original firmware triggered on a single inference frame crossing
// the threshold -- on a noisy microphone that false-fires constantly.
// This requires CONFIRMATION_COUNT consecutive frames above threshold
// (with VAD gating) before declaring a wake, then holds a cooldown
// window, exactly like the Python reference implementation used during
// offline evaluation.

namespace decision {

constexpr float kWakeWordThreshold = 0.75f;
constexpr int kConfirmationCount = 3;
constexpr uint32_t kCooldownMs = 1500;
constexpr int kTargetClassId = 0;

struct Result {
  bool triggered = false;
  bool in_cooldown = false;
  int consecutive_hits = 0;
  uint32_t trigger_count = 0;
};

class DecisionEngine {
 public:
  DecisionEngine(float threshold = kWakeWordThreshold,
                 int confirmation_count = kConfirmationCount,
                 uint32_t cooldown_ms = kCooldownMs)
      : threshold_(threshold),
        confirmation_count_(confirmation_count),
        cooldown_ms_(cooldown_ms) {}

  void reset() {
    consecutive_hits_ = 0;
    cooldown_until_ms_ = 0;
    trigger_count_ = 0;
  }

  // pred_class: argmax class id for this frame.
  // target_conf: dequantized confidence [0,1] for the target class.
  // now_ms: monotonic timestamp (e.g. millis()).
  // vad_speech: true if a cheap energy gate thinks this frame is speech,
  //             not silence/steady noise -- see audio_capture VAD helper.
  Result process(int pred_class, float target_conf, uint32_t now_ms, bool vad_speech) {
    Result r;

    if (now_ms < cooldown_until_ms_) {
      consecutive_hits_ = 0;
      r.in_cooldown = true;
      r.trigger_count = trigger_count_;
      return r;
    }

    const bool valid_hit = vad_speech && (pred_class == kTargetClassId) && (target_conf >= threshold_);

    if (valid_hit) {
      consecutive_hits_++;
      if (consecutive_hits_ >= confirmation_count_) {
        trigger_count_++;
        cooldown_until_ms_ = now_ms + cooldown_ms_;
        consecutive_hits_ = 0;
        r.triggered = true;
        r.in_cooldown = true;
      }
    } else {
      consecutive_hits_ = 0;
    }

    r.consecutive_hits = consecutive_hits_;
    r.trigger_count = trigger_count_;
    return r;
  }

 private:
  float threshold_;
  int confirmation_count_;
  uint32_t cooldown_ms_;

  int consecutive_hits_ = 0;
  uint32_t cooldown_until_ms_ = 0;
  uint32_t trigger_count_ = 0;
};

}  // namespace decision

#endif  // DECISION_H
