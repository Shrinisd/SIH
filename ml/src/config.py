import os
from pathlib import Path

# Project Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Dataset Paths
DATASET_DIR = BASE_DIR / "dataset"
RAW_DATA_DIR = DATASET_DIR / "raw"
PROCESSED_DATA_DIR = DATASET_DIR / "processed"

# Results Directory
RESULTS_DIR = BASE_DIR / "ml" / "results"

# Models Directory
MODELS_DIR = BASE_DIR / "ml" / "models"

# Audio Pipeline Configuration
SAMPLE_RATE = 16000          # Target audio sample rate (Hz)
CHANNELS = 1                # Mono audio
BIT_DEPTH = 16              # 16-bit PCM
WINDOW_DURATION_SEC = 1.0   # Standard audio window duration (seconds)
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_DURATION_SEC)  # 16000 samples

# Classes Definition
TARGET_WAKE_WORD = "Hero Arise"
CLASS_MAP = {
    0: "target_word",
    1: "unknown_words",
    2: "background_noise"
}
CLASS_NAME_TO_ID = {v: k for k, v in CLASS_MAP.items()}

# Dataset Splitting Configuration
SPLIT_RATIOS = {
    "train": 0.70,
    "val": 0.15,
    "test": 0.15
}
RANDOM_SEED = 42

# MFE Feature Extraction Configuration (TinyML ESP32-S3 Efficient)
N_FFT = 512                 # FFT length
WIN_LENGTH = 480            # Frame duration (30 ms = 480 samples @ 16kHz)
HOP_LENGTH = 320            # Frame stride (20 ms = 320 samples @ 16kHz)
N_MELS = 40                 # Number of Mel Filterbank channels
F_MIN = 20.0                # Lower frequency limit (Hz)
F_MAX = 8000.0              # Upper frequency limit (Hz)
LOG_OFFSET = 1e-6           # Offset for log calculation to prevent log(0)

