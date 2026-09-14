# Audio Dataset Guide for Wake-Word Activator ("Hero Arise")

## Target Wake-Word
**"Hero Arise"** (Class 0: `target_word`)

---

## Dataset Structure
The dataset directory structure must follow:

```text
dataset/
└── raw/
    ├── target_word/       # Class 0: Real speech recordings of "Hero Arise"
    ├── unknown_words/     # Class 1: Real speech recordings of non-target words/phrases
    └── background_noise/  # Class 2: Environmental background noise recordings
```

---

## Target Collection Guidelines

### 1. `target_word` (Class 0)
* **Quantity:** 50 – 100 real recordings of the exact wake phrase: **"Hero Arise"**.
* **Duration:** Approximately 1 second per recording (0.8s to 1.2s window).
* **Format:** WAV, 16,000 Hz, mono, 16-bit PCM.

### 2. `unknown_words` (Class 1)
* **Quantity:** 50 – 100 real speech recordings of other words, numbers, or conversational phrases (excluding "Hero Arise").
* **Duration:** Approximately 1 second per recording.
* **Format:** WAV, 16,000 Hz, mono, 16-bit PCM.

### 3. `background_noise` (Class 2)
* **Quantity:** 3 – 5 minutes total of environmental audio (room ambient, fan noise, typing, traffic, silence).
* **Duration:** Individual files can be longer continuous recordings (e.g., 30s – 60s files).
* **Format:** WAV, 16,000 Hz, mono, 16-bit PCM.

---

## Recommended Audio Variation
To ensure robust model generalization on edge hardware (ESP32-S3):
* **Speaking Volume:** Whispering, normal tone, shouting.
* **Distance:** Near-field (10-30 cm), mid-field (1 m), far-field (2-3 m).
* **Microphone Angles:** Direct axis, off-axis.
* **Acoustic Environment:** Quiet bedroom, office, hall with echo.
* **Background Noise Overlay:** Record samples with fan running, background chatter, TV noise.

---

## Critical Data Leakage Prevention Rule
> **IMPORTANT:**
> All recordings originated from the same continuous session or same speaker session **MUST NOT** be split across training, validation, and test sets. Keep entire session batches grouped together during train/val/test partitioning.
