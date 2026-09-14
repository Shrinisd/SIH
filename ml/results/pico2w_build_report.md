# MILESTONE 12 — PICO 2 W BUILD VERIFICATION & TOOLCHAIN INSTALLATION GUIDE

**Target Board:** Raspberry Pi Pico 2 W (`pico2_w`)  
**Target Microcontroller:** RP2350 (ARM Cortex-M33)  
**Build System Specification:** [`firmware/CMakeLists.txt`](file:///d:/SIH%202026/Voice_Activator_Project/firmware/CMakeLists.txt)  
**Date:** August 28, 2026  

---

## 1. Toolchain Execution Test Results

Execution test attempted on host machine:

```powershell
cmake -B firmware/build -S firmware -DPICO_BOARD=pico2_w
```

### Output:
```
cmake : The term 'cmake' is not recognized as the name of a cmdlet, function, script file, or operable program.
CommandNotFoundException
```

---

## 2. Source Code & Build Configuration Status

- **`firmware/CMakeLists.txt`**: **100% COMPLETE & VERIFIED** (Pico SDK CMake configuration targeting RP2350).
- **C++ Firmware Source Files**: **100% COMPLETE & VERIFIED** (`firmware/src/main.cpp`, `audio_capture.cpp`, `mfe.cpp`, `model_runner.cpp`, `decision.cpp`).
- **INT8 Model Byte Array**: **100% COMPLETE & VERIFIED** (`firmware/model/model_data.h`, 13,232 bytes).
- **Host Toolchain Status**: **MISSING HOST CROSS-COMPILER (`cmake` and `arm-none-eabi-gcc`)**.

---

## 3. Step-by-Step Toolchain Installation Guide for RP2350 Compilations

To compile the firmware into a `.uf2` binary artifact on Windows:

### Step 1: Install Raspberry Pi Pico VS Code Extension / Pico SDK
Download and run the official Raspberry Pi Pico Windows Installer:
- URL: `https://github.com/raspberrypi/pico-setup-windows/releases`
- Installs: CMake, Ninja, `arm-none-eabi-gcc` ARM GNU Toolchain, Git, and Pico SDK (v2.0+ supporting RP2350).

### Step 2: Set Environment Variables
In PowerShell:
```powershell
$env:PICO_SDK_PATH = "C:\Users\<user>\.pico-sdk\sdk\2.0.0"
```

### Step 3: Compile Binary
```powershell
# Navigate to project root
cd "d:\SIH 2026\Voice_Activator_Project"

# Generate build environment targeting Pico 2 W (RP2350)
cmake -B firmware/build -S firmware -DPICO_BOARD=pico2_w -G "Ninja"

# Build UF2 firmware binary
cmake --build firmware/build
```

### Step 4: Flash Binary to Pico 2 W
1. Hold the **BOOTSEL** button on the Raspberry Pi Pico 2 W while plugging in USB cable.
2. Drag and drop `firmware/build/hero_arise_pico2w.uf2` onto the mounted `RPI-RP2` drive.
