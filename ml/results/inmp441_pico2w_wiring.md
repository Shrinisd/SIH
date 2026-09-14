# MILESTONE 11 — INMP441 I2S MICROPHONE PICO 2 W WIRING SPECIFICATION

**Target Microcontroller:** Raspberry Pi Pico 2 W (RP2350)  
**Audio Hardware:** INMP441 Omnidirectional I2S Digital MEMS Microphone  
**Display:** SSD1306 0.96" OLED ($128 \times 64$, I2C)  
**Actuators:** Green LED (Activation), Red LED (Idle/Listening), Piezo Buzzer  
**Document Date:** August 28, 2026  

---

## 1. INMP441 I2S Digital Microphone Pinout

| INMP441 Microphone Pin | Pico 2 W Physical Pin | RP2350 GPIO Pin | Signal Description | Wiring Color Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **SCK** (Bit Clock) | Pin 31 | **GP26** | I2S Bit Clock Line | Yellow |
| **WS** (Word Select / LRCLK) | Pin 32 | **GP27** | I2S Word Select / Frame Clock | Blue |
| **SD** (Serial Data Out) | Pin 34 | **GP28** | I2S Data Stream Output | Green |
| **L/R** (Channel Select) | Pin 33 | **GND** | Tied to GND for Left Channel (Mono) | Black |
| **VDD** (Power) | Pin 36 | **3V3** | +3.3V Power Supply | Red |
| **GND** (Ground) | Pin 38 | **GND** | System Ground | Black |

---

## 2. Complete System Pin Allocation & Conflict Verification

To ensure zero GPIO pin conflicts across peripherals, the entire hardware allocation table is defined below:

| Peripheral Device | Signal / Function | Pico 2 W GPIO | Physical Pin Number | Pin Status & Isolation |
| :--- | :--- | :--- | :--- | :--- |
| **SSD1306 OLED** | I2C0 SDA | **GP4** | Pin 6 | Dedicated I2C0 Bus |
| **SSD1306 OLED** | I2C0 SCL | **GP5** | Pin 7 | Dedicated I2C0 Bus |
| **Green Status LED** | Anode (+) | **GP14** | Pin 19 | Dedicated GPIO Output |
| **Red Status LED** | Anode (+) | **GP15** | Pin 20 | Dedicated GPIO Output |
| **Piezo Buzzer** | Signal Line | **GP16** | Pin 21 | Dedicated PWM / GPIO Output |
| **INMP441 I2S Mic** | BCLK | **GP26** | Pin 31 | Dedicated I2S Clock Line |
| **INMP441 I2S Mic** | WS / LRCLK | **GP27** | Pin 32 | Dedicated I2S Frame Line |
| **INMP441 I2S Mic** | SD / Data | **GP28** | Pin 34 | Dedicated I2S Data Line |

---

## 3. Conflict Verification Matrix

- **OLED I2C Bus**: GP4 / GP5 $\rightarrow$ **Zero conflict with I2S** (GP26/GP27/GP28).
- **Actuator GPIOs**: GP14 / GP15 / GP16 $\rightarrow$ **Zero conflict with I2S or OLED**.
- **Power Budget**: INMP441 draws $< 1.5\text{ mA}$ @ $3.3\text{V}$, SSD1306 draws $< 15\text{ mA}$, LEDs draw $< 10\text{ mA}$. Pico 2 W on-board 3.3V regulator easily handles total system current ($< 30\text{ mA}$).

---

## 4. Hardware Wiring Verification Verdict

**WIRING SPECIFICATION: VERIFIED & ISOLATED**  
All INMP441 I2S microphone connections are cleanly mapped to contiguous GPIOs (GP26, GP27, GP28) without overlapping display, LED, or buzzer pins.
