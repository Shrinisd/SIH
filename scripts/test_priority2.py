import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.decision import DecisionEngine, WAKE_WORD_THRESHOLD

def run_tests():
    print("=" * 60)
    print("PRIORITY 2: TEMPORAL CONFIRMATION + COOLDOWN VERIFICATION SUITE")
    print(f"Target Wake Threshold: {WAKE_WORD_THRESHOLD * 100:.1f}%")
    print("Required Consecutive Hits: 3")
    print("Cooldown Duration: 1500 ms")
    print("=" * 60)

    engine = DecisionEngine(threshold=WAKE_WORD_THRESHOLD)
    results = {}

    # TEST A — Single spike
    # 1 high confidence frame followed by low confidence frame
    engine.reset()
    res1 = engine.process_prediction(pred_class=0, target_conf=0.85, current_time_ms=1000)
    res2 = engine.process_prediction(pred_class=0, target_conf=0.42, current_time_ms=1050)
    
    test_a_pass = (not res1["triggered"]) and (res1["consecutive_hits"] == 1) and \
                 (not res2["triggered"]) and (res2["consecutive_hits"] == 0) and \
                 (engine.trigger_count == 0)
    results["Single spike"] = "PASS" if test_a_pass else "FAIL"
    print(f"\nTEST A [Single spike]: {'PASS' if test_a_pass else 'FAIL'}")
    print(f"  Frame 1 (85%): status='{res1['status']}', triggered={res1['triggered']}")
    print(f"  Frame 2 (42%): status='{res2['status']}', triggered={res2['triggered']}")

    # TEST B — Two consecutive detections
    # 2 high confidence frames
    engine.reset()
    res1 = engine.process_prediction(pred_class=0, target_conf=0.85, current_time_ms=1000)
    res2 = engine.process_prediction(pred_class=0, target_conf=0.88, current_time_ms=1050)
    
    test_b_pass = (not res1["triggered"]) and (res1["consecutive_hits"] == 1) and \
                 (not res2["triggered"]) and (res2["consecutive_hits"] == 2) and \
                 (engine.trigger_count == 0)
    results["Two detections"] = "PASS" if test_b_pass else "FAIL"
    print(f"\nTEST B [Two consecutive detections]: {'PASS' if test_b_pass else 'FAIL'}")
    print(f"  Frame 1 (85%): status='{res1['status']}', hits={res1['consecutive_hits']}")
    print(f"  Frame 2 (88%): status='{res2['status']}', hits={res2['consecutive_hits']}")

    # TEST C — Three consecutive detections
    # 3 high confidence frames
    engine.reset()
    res1 = engine.process_prediction(pred_class=0, target_conf=0.85, current_time_ms=1000)
    res2 = engine.process_prediction(pred_class=0, target_conf=0.88, current_time_ms=1050)
    res3 = engine.process_prediction(pred_class=0, target_conf=0.91, current_time_ms=1100)
    
    test_c_pass = (not res1["triggered"]) and (not res2["triggered"]) and \
                 res3["triggered"] and (res3["status"] == "Wake confirmed") and \
                 (engine.trigger_count == 1)
    results["Three detections"] = "PASS" if test_c_pass else "FAIL"
    print(f"\nTEST C [Three consecutive detections]: {'PASS' if test_c_pass else 'FAIL'}")
    print(f"  Frame 1 (85%): hits={res1['consecutive_hits']}")
    print(f"  Frame 2 (88%): hits={res2['consecutive_hits']}")
    print(f"  Frame 3 (91%): status='{res3['status']}', triggered={res3['triggered']}")

    # TEST D — Confidence interruption
    # high, high, low, high, high
    engine.reset()
    f1 = engine.process_prediction(pred_class=0, target_conf=0.85, current_time_ms=1000) # hit 1
    f2 = engine.process_prediction(pred_class=0, target_conf=0.88, current_time_ms=1050) # hit 2
    f3 = engine.process_prediction(pred_class=0, target_conf=0.42, current_time_ms=1100) # reset
    f4 = engine.process_prediction(pred_class=0, target_conf=0.90, current_time_ms=1150) # hit 1
    f5 = engine.process_prediction(pred_class=0, target_conf=0.87, current_time_ms=1200) # hit 2
    
    test_d_no_trigger = not (f1["triggered"] or f2["triggered"] or f3["triggered"] or f4["triggered"] or f5["triggered"])
    test_d_pass = test_d_no_trigger and (f3["consecutive_hits"] == 0) and (f5["consecutive_hits"] == 2) and (engine.trigger_count == 0)
    
    # 6th frame to verify third hit triggers
    f6 = engine.process_prediction(pred_class=0, target_conf=0.92, current_time_ms=1250) # hit 3 -> trigger
    test_d_pass = test_d_pass and f6["triggered"] and (engine.trigger_count == 1)
    
    results["Interrupted sequence"] = "PASS" if test_d_pass else "FAIL"
    print(f"\nTEST D [Confidence interruption]: {'PASS' if test_d_pass else 'FAIL'}")
    print(f"  F1 (85%): hits={f1['consecutive_hits']} | F2 (88%): hits={f2['consecutive_hits']}")
    print(f"  F3 (42% DROP): hits={f3['consecutive_hits']} (RESET)")
    print(f"  F4 (90%): hits={f4['consecutive_hits']} | F5 (87%): hits={f5['consecutive_hits']} | Triggered: {f5['triggered']}")
    print(f"  F6 (92%): hits={f6['consecutive_hits']} | Triggered: {f6['triggered']}")

    # TEST E — Cooldown
    # Trigger at t=1100ms. Cooldown active until 1100 + 1500 = 2600ms.
    # Provide 3 valid frames at t=1150, 1200, 1250ms (during cooldown).
    engine.reset()
    # Initial trigger
    engine.process_prediction(0, 0.85, 1000)
    engine.process_prediction(0, 0.88, 1050)
    trig1 = engine.process_prediction(0, 0.91, 1100) # Trigger 1 at t=1100ms
    
    # Valid frames during cooldown (t=1150..1250)
    cd1 = engine.process_prediction(0, 0.95, 1150)
    cd2 = engine.process_prediction(0, 0.95, 1200)
    cd3 = engine.process_prediction(0, 0.95, 1250)
    
    test_e_pass = trig1["triggered"] and (engine.trigger_count == 1) and \
                 (not cd1["triggered"]) and (not cd2["triggered"]) and (not cd3["triggered"]) and \
                 cd1["in_cooldown"] and cd3["in_cooldown"] and (engine.trigger_count == 1)
    results["Cooldown"] = "PASS" if test_e_pass else "FAIL"
    print(f"\nTEST E [Cooldown enforcement]: {'PASS' if test_e_pass else 'FAIL'}")
    print(f"  Trigger 1 fired at t=1100ms (trigger_count={trig1['trigger_count']})")
    print(f"  t=1150ms during cooldown: status='{cd1['status']}', triggered={cd1['triggered']}")
    print(f"  t=1250ms during cooldown: status='{cd3['status']}', triggered={cd3['triggered']}")
    print(f"  Total Triggers Fired: {engine.trigger_count} (Expected: 1)")

    # TEST F — After cooldown
    # Cooldown expires at t=2600ms.
    # Provide 3 valid frames at t=2700, 2750, 2800ms.
    p1 = engine.process_prediction(0, 0.85, 2700)
    p2 = engine.process_prediction(0, 0.88, 2750)
    trig2 = engine.process_prediction(0, 0.92, 2800)
    
    test_f_pass = (not p1["in_cooldown"]) and (not p1["triggered"]) and (p1["consecutive_hits"] == 1) and \
                 (not p2["triggered"]) and (p2["consecutive_hits"] == 2) and \
                 trig2["triggered"] and (engine.trigger_count == 2)
    results["Post-cooldown"] = "PASS" if test_f_pass else "FAIL"
    print(f"\nTEST F [Post-cooldown recovery]: {'PASS' if test_f_pass else 'FAIL'}")
    print(f"  t=2700ms (cooldown expired): hits={p1['consecutive_hits']}, in_cooldown={p1['in_cooldown']}")
    print(f"  t=2750ms: hits={p2['consecutive_hits']}")
    print(f"  t=2800ms: status='{trig2['status']}', triggered={trig2['triggered']}")
    print(f"  Total Triggers Fired: {engine.trigger_count} (Expected: 2)")

    # Summary
    all_pass = all(v == "PASS" for v in results.values())
    print("\n" + "=" * 60)
    print(f"ALL TESTS PASSED: {'YES' if all_pass else 'NO'}")
    for test_name, status in results.items():
        print(f"  - {test_name}: {status}")
    print("=" * 60)

    return all_pass, results

if __name__ == "__main__":
    success, _ = run_tests()
    sys.exit(0 if success else 1)
