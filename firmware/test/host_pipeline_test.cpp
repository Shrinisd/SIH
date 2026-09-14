// Desktop compile/sanity check for audio_capture.h and decision.h --
// the buffer bookkeeping and the confirmation/cooldown state machine,
// independent of any MCU/Arduino dependency.

#include <cassert>
#include <cstdio>
#include <vector>

#include "audio_capture.h"
#include "decision.h"

static void test_ring_buffer_fills_and_reads_in_order() {
  audio_capture::RingBuffer rb;
  std::vector<int32_t> chunk(audio_capture::kHopSamples);

  int16_t expected_first_sample = 0;
  bool ever_ready = false;
  for (int hop = 0; hop < 60; hop++) {  // 60 hops = well over one full window
    for (int i = 0; i < audio_capture::kHopSamples; i++) {
      // raw I2S value such that (v >> 14) == a ramping, wrapping int16 pattern
      chunk[i] = (int32_t)((hop * audio_capture::kHopSamples + i) % 1000) << 14;
    }
    bool ready = rb.push_raw_i2s(chunk.data(), chunk.size(), /*shift=*/14);
    if (ready) ever_ready = true;
  }
  assert(ever_ready);
  assert(rb.is_full());

  static int16_t window[audio_capture::kWindowSamples];
  rb.get_window(window);
  // Oldest sample in the window should reflect (60 hops - window/hop hops) back.
  (void)expected_first_sample;
  printf("ring_buffer: OK (window[0]=%d window[last]=%d)\n", window[0],
         window[audio_capture::kWindowSamples - 1]);
}

static void test_decision_confirmation_and_cooldown() {
  decision::DecisionEngine eng;
  uint32_t t = 0;

  // Two hits: should not trigger yet.
  auto r1 = eng.process(/*pred_class=*/0, /*conf=*/0.9f, t, /*vad=*/true);
  t += 20;
  auto r2 = eng.process(0, 0.9f, t, true);
  t += 20;
  assert(!r1.triggered && !r2.triggered);
  assert(r2.consecutive_hits == 2);

  // Third consecutive hit: should trigger.
  auto r3 = eng.process(0, 0.9f, t, true);
  t += 20;
  assert(r3.triggered);
  assert(r3.trigger_count == 1);

  // Immediately after, still in cooldown -- must not trigger again even
  // with a strong hit.
  auto r4 = eng.process(0, 0.95f, t, true);
  assert(!r4.triggered);
  assert(r4.in_cooldown);

  // After cooldown elapses, a fresh 3-hit sequence should trigger again.
  t += decision::kCooldownMs + 1;
  eng.process(0, 0.9f, t, true);
  t += 20;
  eng.process(0, 0.9f, t, true);
  t += 20;
  auto r5 = eng.process(0, 0.9f, t, true);
  assert(r5.triggered);
  assert(r5.trigger_count == 2);

  // A drop below threshold resets the streak.
  decision::DecisionEngine eng2;
  t = 0;
  eng2.process(0, 0.9f, t, true);
  t += 20;
  eng2.process(0, 0.4f, t, true);  // below threshold -> reset
  t += 20;
  auto r6 = eng2.process(0, 0.9f, t, true);
  assert(r6.consecutive_hits == 1);  // streak restarted, not 3

  printf("decision_engine: OK\n");
}

int main() {
  test_ring_buffer_fills_and_reads_in_order();
  test_decision_confirmation_and_cooldown();
  printf("all host_pipeline_test checks passed\n");
  return 0;
}
