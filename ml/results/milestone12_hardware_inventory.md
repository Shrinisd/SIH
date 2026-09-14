# MILESTONE 12 — PHYSICAL HARDWARE INVENTORY AUDIT REPORT

**Project:** SIH2672 — Low Latency and Efficient Voice Activator for Edge Devices  
**Target Microcontroller:** Raspberry Pi Pico 2 W (RP2350 / ARM Cortex-M33)  
**Date:** August 28, 2026  

---

## 1. Physical Hardware Component Inventory

| Component Description | Model / Spec | Quantity | Interface / Signal Type | Functional Role | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Microcontroller Unit** | Raspberry Pi Pico 2 W (RP2350) | 1 | Dual ARM Cortex-M33 @ 150MHz | Main Edge Processing Unit & TFLM Model Host | **REQUIRED** |
| **Digital Microphone** | INMP441 MEMS Microphone | 1 | I2S Digital Audio (BCLK, WS, SD) | 16 kHz 16-bit Mono PCM Live Audio Capture | **REQUIRED** |
| **Visual Display** | SSD1306 0.96" OLED ($128 \times 64$) | 1 | I2C Bus (`0x3C`, GP4 SDA, GP5 SCL) | Real-time status display & activation confidence | **REQUIRED** |
| **Status Indicator LED** | 5mm Green LED | 1 | GPIO Output (GP14) | Wake-Word Detection ("Hero Arise") Alert | **REQUIRED** |
| **Status Indicator LED** | 5mm Red LED | 1 | GPIO Output (GP15) | Listening / Idle Indicator | **REQUIRED** |
| **Audible Actuator** | 5V Active/Passive Piezo Buzzer | 1 | GPIO / PWM Output (GP16) | 2000 Hz 150ms activation tone alert | **REQUIRED** |
| **Current Limiting Resistors**| $220\ \Omega$ $\frac{1}{4}\text{W}$ Resistors | 2 | Inline LED Anode Protection | Limits LED forward current ($I_f \approx 6\text{mA}$) | **REQUIRED** |
| **Prototyping Board** | Solderless 830-Point Breadboard | 1 | Mechanical Interconnect | Circuit prototyping bed | **REQUIRED** |
| **Jumper Wires** | Premium Male-to-Male / Male-to-Female | 15 | Discrete Wiring | Electrical connection of peripherals to Pico 2 W | **REQUIRED** |
| **Host / Power Interface** | Micro-USB / USB-C Data Cable | 1 | USB 2.0 CDC Serial / 5V VBUS | Power delivery & firmware flashing / Serial log output | **REQUIRED** |

---

## 2. Power Arrangement & Electrical Budget

- **Input Supply**: 5.0V VBUS via USB cable.
- **On-Board Voltage Regulation**: Pico 2 W on-board RT6154 buck-boost regulator delivering +3.3V DC.
- **Power Consumption Breakdown**:
  - Pico 2 W RP2350 @ 150 MHz: $\sim 20 - 30\text{ mA}$
  - INMP441 Microphone: $1.4\text{ mA}$
  - SSD1306 OLED Display: $\sim 15.0\text{ mA}$
  - Green LED ($220\ \Omega$): $\sim 6.0\text{ mA}$
  - Red LED ($220\ \Omega$): $\sim 6.0\text{ mA}$
  - Piezo Buzzer: $\sim 10.0\text{ mA}$ (pulse only)
  - **Total System Current**: $\approx 40 - 65\text{ mA}$ @ 3.3V (Well within Pico 2 W 300mA 3.3V regulator capacity).

---

## 3. Physical Inventory Summary

**HARDWARE INVENTORY AUDIT: VERIFIED & COMPLETE**  
All required physical components, pinouts, current-limiting resistors, and power budgets are fully specified for real physical demonstration.
