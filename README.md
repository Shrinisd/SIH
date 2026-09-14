# SIH2672 – Low Latency & Efficient Voice Activator for Edge Devices

**Team:** BUGGY-BOTS  
**Hardware:** Raspberry Pi Pico 2 W (RP2350)  
**Wake Word:** "Hero Arise"  
**Status (28 Aug 2026):** Test-vector mode working • Live microphone path prepared • Streaming to be completed

## Problem Statement
Ultra-lightweight keyword spotting (KWS) that runs on a low-power MCU (< 256 KB RAM, < 10 % idle CPU). Upon detecting the wake word, the system must efficiently stream subsequent audio to a remote ASR server.

## Current Architecture
- Custom 3-class INT8 TFLite Micro model (Target / Unknown / Noise)
- Feature extraction: Mel-Frequency Energy (MFE) 49 × 40
- Runtime: Raspberry Pi Pico SDK + TensorFlow Lite Micro
- Target board: Raspberry Pi Pico 2 W

## Repository Structure
- `dataset/` – Audio dataset and processing guidelines
- `ml/` – Training, quantization and evaluation scripts
- `firmware/` – Pico 2 W firmware (CMake + Pico SDK)
- `scripts/` – Helper scripts for model conversion and benchmarking
- `wokwi/` – Simulation assets (to be updated)

## How to Build & Flash (Pico 2 W)
1. Install Raspberry Pi Pico SDK
2. `cd firmware`
3. `mkdir build && cd build`
4. `cmake ..`
5. `make -j4`
6. Flash the generated `.uf2` file to the Pico 2 W

## Measured Status (Test-vector mode)
- Model runs successfully on Pico 2 W
- Inference latency: 
- Tensor arena: 20 KB (see config.h)

## Next Steps (post-SIH)
- Complete live I2S microphone path (INMP441)
- Add post-detection audio streaming
- Full multi-speaker dataset expansion and power measurements

## Team Members
- Aathira Venuraj
- Shrinivas Hari
- Jero A
- Reshma V
- Sujatha K
- Akzhara Baskar
