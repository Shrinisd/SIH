import time
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Existing threshold from config
WAKE_WORD_THRESHOLD = 0.75
CONFIRMATION_COUNT = 3
COOLDOWN_MS = 1500

class DecisionEngine:
    """
    Temporal Wake-Word Confirmation + Post-Trigger Cooldown Engine.
    
    Rules:
    1. Temporal Confirmation: Requires 3 consecutive inference frames with target confidence >= WAKE_WORD_THRESHOLD.
    2. Reset: Any frame dropping below threshold or non-speech VAD resets consecutive counter to 0 immediately.
    3. Cooldown: After successful trigger, ignore new wake-word detections for 1500 ms.
    """
    def __init__(self, threshold=WAKE_WORD_THRESHOLD, confirmation_count=CONFIRMATION_COUNT, cooldown_ms=COOLDOWN_MS):
        self.threshold = threshold
        self.confirmation_count = confirmation_count
        self.cooldown_ms = cooldown_ms
        
        self.consecutive_hits = 0
        self.cooldown_until_ms = 0
        self.last_status = "Listening"
        self.trigger_count = 0

    def reset(self):
        self.consecutive_hits = 0
        self.cooldown_until_ms = 0
        self.last_status = "Listening"
        self.trigger_count = 0

    def process_prediction(self, pred_class, target_conf, current_time_ms=None, vad_speech=True):
        """
        Processes a single prediction frame.
        
        Parameters:
        - pred_class: 0 (Hero Arise / target_word), 1 (unknown_words), 2 (background_noise)
        - target_conf: float confidence [0.0 - 1.0] for target class
        - current_time_ms: int timestamp in ms (if None, uses current system time)
        - vad_speech: bool (True if VAD energy gate detects speech)
        
        Returns:
        dict containing:
        - triggered (bool): True on the frame wake trigger occurs
        - status (str): UI status string
        - consecutive_hits (int): current consecutive confirmation count
        - in_cooldown (bool): True if currently within post-trigger cooldown window
        - trigger_count (int): total triggers fired
        """
        if current_time_ms is None:
            current_time_ms = int(time.time() * 1000)

        # 1. Check if currently in cooldown
        if current_time_ms < self.cooldown_until_ms:
            self.consecutive_hits = 0
            self.last_status = "Cooldown"
            return {
                "triggered": False,
                "status": "Cooldown",
                "consecutive_hits": 0,
                "in_cooldown": True,
                "trigger_count": self.trigger_count
            }

        # 2. Check if valid target wake-word detection frame
        valid_hit = vad_speech and (pred_class == 0) and (target_conf >= self.threshold)

        if valid_hit:
            self.consecutive_hits += 1
            if self.consecutive_hits >= self.confirmation_count:
                # WAKE CONFIRMED -> Fire trigger action and set 1500 ms cooldown
                self.trigger_count += 1
                self.cooldown_until_ms = current_time_ms + self.cooldown_ms
                self.consecutive_hits = 0
                self.last_status = "Wake confirmed"
                return {
                    "triggered": True,
                    "status": "Wake confirmed",
                    "consecutive_hits": self.confirmation_count,
                    "in_cooldown": True,
                    "trigger_count": self.trigger_count
                }
            else:
                self.last_status = f"Wake confirmation: {self.consecutive_hits}/{self.confirmation_count}"
                return {
                    "triggered": False,
                    "status": self.last_status,
                    "consecutive_hits": self.consecutive_hits,
                    "in_cooldown": False,
                    "trigger_count": self.trigger_count
                }
        else:
            # Interruption: Confidence dropped below threshold or non-speech -> Reset counter
            self.consecutive_hits = 0
            self.last_status = "Listening"
            return {
                "triggered": False,
                "status": "Listening",
                "consecutive_hits": 0,
                "in_cooldown": False,
                "trigger_count": self.trigger_count
            }

    def get_live_metrics(self, res, target_conf, vad_speech, latency_ms=0.0):
        """
        Extracts structured live telemetry metrics from decision engine state.
        """
        if res["status"] == "Wake confirmed":
            macro_state = "Wake confirmed"
            conf_display = f"{self.confirmation_count} / {self.confirmation_count}"
        elif res["in_cooldown"]:
            macro_state = "Cooldown"
            conf_display = f"0 / {self.confirmation_count}"
        elif res["consecutive_hits"] > 0:
            macro_state = "Speech detected"
            conf_display = f"{res['consecutive_hits']} / {self.confirmation_count}"
        elif vad_speech:
            macro_state = "Speech detected"
            conf_display = f"0 / {self.confirmation_count}"
        else:
            macro_state = "Listening"
            conf_display = f"0 / {self.confirmation_count}"

        vad_status = "Speech detected" if vad_speech else "Silence"

        return {
            "state": macro_state,
            "status": res["status"],
            "confidence": float(target_conf),
            "confidence_pct": float(target_conf * 100.0),
            "latency_ms": float(latency_ms),
            "confirmation": conf_display,
            "consecutive_hits": res["consecutive_hits"],
            "confirmation_count": self.confirmation_count,
            "vad_speech": bool(vad_speech),
            "vad_status": vad_status,
            "in_cooldown": bool(res["in_cooldown"]),
            "triggered": bool(res["triggered"]),
            "input_source": "Software/Test Audio",
            "runtime_environment": "PC"
        }

    def format_live_monitor(self, res, target_conf, vad_speech, latency_ms=0.0):
        """
        Formats a clean, lightweight terminal performance monitor panel string.
        """
        metrics = self.get_live_metrics(res, target_conf, vad_speech, latency_ms)
        cooldown_str = "YES (active)" if metrics["in_cooldown"] else "NO"
        
        lines = [
            "--------------------------------------------------",
            "             HERO ARISE — LIVE MONITOR            ",
            "--------------------------------------------------",
            f"STATE          : {metrics['state']}",
            f"CONFIDENCE     : {metrics['confidence_pct']:.1f} %",
            f"LATENCY        : {metrics['latency_ms']:.2f} ms (PC software)",
            f"CONFIRMATION   : {metrics['confirmation']}",
            f"VAD            : {metrics['vad_status']}",
            f"COOLDOWN       : {cooldown_str}",
            f"INPUT          : {metrics['input_source']}",
            f"RUNTIME        : {metrics['runtime_environment']}",
            "--------------------------------------------------"
        ]
        return "\n".join(lines)
