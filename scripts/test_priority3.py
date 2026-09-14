import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ml.src.decision import DecisionEngine, WAKE_WORD_THRESHOLD

def run_priority3_tests():
    print("=" * 60)
    print("PRIORITY 3: LIVE PERFORMANCE MONITOR VERIFICATION SUITE")
    print("=" * 60)

    engine = DecisionEngine(threshold=WAKE_WORD_THRESHOLD)
    results = {}

    # TEST A: Listening / silence state
    engine.reset()
    res_a = engine.process_prediction(pred_class=2, target_conf=0.10, current_time_ms=1000, vad_speech=False)
    metrics_a = engine.get_live_metrics(res_a, target_conf=0.10, vad_speech=False, latency_ms=4.25)
    fmt_a = engine.format_live_monitor(res_a, target_conf=0.10, vad_speech=False, latency_ms=4.25)

    test_a_pass = (metrics_a["state"] == "Listening") and \
                 (metrics_a["vad_status"] == "Silence") and \
                 (metrics_a["confirmation"] == "0 / 3") and \
                 ("STATE          : Listening" in fmt_a) and \
                 ("VAD            : Silence" in fmt_a)
    results["TEST A [Silence / Listening]"] = "PASS" if test_a_pass else "FAIL"
    print(f"\nTEST A [Silence / Listening]: {'PASS' if test_a_pass else 'FAIL'}")
    print(f"  State: '{metrics_a['state']}' | VAD: '{metrics_a['vad_status']}' | Conf: '{metrics_a['confirmation']}'")

    # TEST B: Speech detected state (VAD detects speech, but confidence below threshold)
    engine.reset()
    res_b = engine.process_prediction(pred_class=1, target_conf=0.45, current_time_ms=1050, vad_speech=True)
    metrics_b = engine.get_live_metrics(res_b, target_conf=0.45, vad_speech=True, latency_ms=5.12)
    fmt_b = engine.format_live_monitor(res_b, target_conf=0.45, vad_speech=True, latency_ms=5.12)

    test_b_pass = (metrics_b["state"] == "Speech detected") and \
                 (metrics_b["vad_status"] == "Speech detected") and \
                 (metrics_b["confirmation"] == "0 / 3") and \
                 ("STATE          : Speech detected" in fmt_b)
    results["TEST B [Speech detected]"] = "PASS" if test_b_pass else "FAIL"
    print(f"\nTEST B [Speech detected]: {'PASS' if test_b_pass else 'FAIL'}")
    print(f"  State: '{metrics_b['state']}' | VAD: '{metrics_b['vad_status']}' | Conf: '{metrics_b['confirmation']}'")

    # TEST C: Confidence value formatting and accuracy
    engine.reset()
    conf_val = 0.824
    res_c = engine.process_prediction(pred_class=0, target_conf=conf_val, current_time_ms=1100, vad_speech=True)
    metrics_c = engine.get_live_metrics(res_c, target_conf=conf_val, vad_speech=True, latency_ms=3.80)
    fmt_c = engine.format_live_monitor(res_c, target_conf=conf_val, vad_speech=True, latency_ms=3.80)

    test_c_pass = (abs(metrics_c["confidence"] - conf_val) < 1e-4) and \
                 (abs(metrics_c["confidence_pct"] - 82.4) < 1e-2) and \
                 ("CONFIDENCE     : 82.4 %" in fmt_c)
    results["TEST C [Actual Confidence]"] = "PASS" if test_c_pass else "FAIL"
    print(f"\nTEST C [Actual Confidence]: {'PASS' if test_c_pass else 'FAIL'}")
    print(f"  Target Conf: {metrics_c['confidence_pct']:.1f}% | Formatted output line present: {'CONFIDENCE     : 82.4 %' in fmt_c}")

    # TEST D: Latency measurement is numeric and labeled correctly
    latency_test_val = 6.4812
    metrics_d = engine.get_live_metrics(res_c, target_conf=conf_val, vad_speech=True, latency_ms=latency_test_val)
    fmt_d = engine.format_live_monitor(res_c, target_conf=conf_val, vad_speech=True, latency_ms=latency_test_val)

    test_d_pass = isinstance(metrics_d["latency_ms"], (int, float)) and \
                 (metrics_d["latency_ms"] > 0) and \
                 ("LATENCY        : 6.48 ms (PC software)" in fmt_d) and \
                 (metrics_d["runtime_environment"] == "PC")
    results["TEST D [Measured PC Latency]"] = "PASS" if test_d_pass else "FAIL"
    print(f"\nTEST D [Measured PC Latency]: {'PASS' if test_d_pass else 'FAIL'}")
    print(f"  Measured Latency: {metrics_d['latency_ms']:.2f} ms | Labeled as PC software: {'(PC software)' in fmt_d}")

    # TEST E: Confirmation counter sequence display (0/3, 1/3, 2/3, 3/3)
    engine.reset()
    res_e1 = engine.process_prediction(0, 0.85, 1200, True) # 1/3
    res_e2 = engine.process_prediction(0, 0.88, 1250, True) # 2/3
    res_e3 = engine.process_prediction(0, 0.92, 1300, True) # 3/3 (Wake confirmed)

    fmt_e1 = engine.format_live_monitor(res_e1, 0.85, True, 4.0)
    fmt_e2 = engine.format_live_monitor(res_e2, 0.88, True, 4.1)
    fmt_e3 = engine.format_live_monitor(res_e3, 0.92, True, 4.2)

    test_e_pass = ("CONFIRMATION   : 1 / 3" in fmt_e1) and \
                 ("CONFIRMATION   : 2 / 3" in fmt_e2) and \
                 ("CONFIRMATION   : 3 / 3" in fmt_e3)
    results["TEST E [Confirmation Displays]"] = "PASS" if test_e_pass else "FAIL"
    print(f"\nTEST E [Confirmation Displays]: {'PASS' if test_e_pass else 'FAIL'}")
    print(f"  Frame 1: 'CONFIRMATION   : 1 / 3' present: {'CONFIRMATION   : 1 / 3' in fmt_e1}")
    print(f"  Frame 2: 'CONFIRMATION   : 2 / 3' present: {'CONFIRMATION   : 2 / 3' in fmt_e2}")
    print(f"  Frame 3: 'CONFIRMATION   : 3 / 3' present: {'CONFIRMATION   : 3 / 3' in fmt_e3}")

    # TEST F: Cooldown state display
    # Following frame 3 trigger at t=1300ms, cooldown active until t=2800ms.
    res_f = engine.process_prediction(0, 0.95, 1400, True) # during cooldown at t=1400ms
    metrics_f = engine.get_live_metrics(res_f, 0.95, True, 4.0)
    fmt_f = engine.format_live_monitor(res_f, 0.95, True, 4.0)

    test_f_pass = (metrics_f["state"] == "Cooldown") and \
                 (metrics_f["in_cooldown"] == True) and \
                 ("STATE          : Cooldown" in fmt_f) and \
                 ("COOLDOWN       : YES (active)" in fmt_f)
    results["TEST F [Cooldown State]"] = "PASS" if test_f_pass else "FAIL"
    print(f"\nTEST F [Cooldown State]: {'PASS' if test_f_pass else 'FAIL'}")
    print(f"  State: '{metrics_f['state']}' | Cooldown Active: {metrics_f['in_cooldown']} | Formatted line present: {'COOLDOWN       : YES (active)' in fmt_f}")

    # TEST G: Wake confirmed state display
    metrics_g = engine.get_live_metrics(res_e3, 0.92, True, 4.2)
    fmt_g = engine.format_live_monitor(res_e3, 0.92, True, 4.2)

    test_g_pass = (metrics_g["state"] == "Wake confirmed") and \
                 (metrics_g["triggered"] == True) and \
                 ("STATE          : Wake confirmed" in fmt_g)
    results["TEST G [Wake Confirmed State]"] = "PASS" if test_g_pass else "FAIL"
    print(f"\nTEST G [Wake Confirmed State]: {'PASS' if test_g_pass else 'FAIL'}")
    print(f"  State: '{metrics_g['state']}' | Triggered: {metrics_g['triggered']} | Formatted line present: {'STATE          : Wake confirmed' in fmt_g}")

    # Summary
    all_pass = all(v == "PASS" for v in results.values())
    print("\n" + "=" * 60)
    print(f"ALL PRIORITY 3 TESTS PASSED: {'YES' if all_pass else 'NO'}")
    for test_name, status in results.items():
        print(f"  - {test_name}: {status}")
    print("=" * 60)

    return all_pass, results

if __name__ == "__main__":
    success, _ = run_priority3_tests()
    sys.exit(0 if success else 1)
