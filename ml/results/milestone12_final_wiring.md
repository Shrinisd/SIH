# MILESTONE 12 — FINAL PICO 2 W HARDWARE WIRING DIAGRAM

**Target Microcontroller:** Raspberry Pi Pico 2 W (RP2350)  
**Document Date:** August 28, 2026  

---

## 1. Physical Pin Connection Table

```
                  Raspberry Pi Pico 2 W Pinout
                         +------------+
           (OLED SDA) GP4 | 1       40 | VBUS (+5V USB)
           (OLED SCL) GP5 | 2       39 | VSYS
                      GND | 3       38 | GND (System Ground)
                      ... | ...    ... | ...
           (Green LED) GP14| 19      36 | 3V3 OUT (+3.3V Power)
             (Red LED) GP15| 20      34 | GP28 (INMP441 SD / Data)
              (Buzzer) GP16| 21      33 | GND (INMP441 L/R Ground)
                      ... | ...     32 | GP27 (INMP441 WS / LRCLK)
                      GND | 23      31 | GP26 (INMP441 SCK / BCLK)
                         +------------+
```

---

## 2. Complete Interconnect Details

### A. INMP441 I2S Digital MEMS Microphone
- **VDD** $\rightarrow$ **Pico 2 W Pin 36 (3V3 OUT)**
- **GND** $\rightarrow$ **Pico 2 W Pin 38 (GND)**
- **L/R** $\rightarrow$ **Pico 2 W Pin 33 (GND)** (Configures Left Channel / Mono mode)
- **SCK** (Bit Clock) $\rightarrow$ **Pico 2 W Pin 31 (GP26)**
- **WS** (Word Select / LRCLK) $\rightarrow$ **Pico 2 W Pin 32 (GP27)**
- **SD** (Serial Data) $\rightarrow$ **Pico 2 W Pin 34 (GP28)**

### B. SSD1306 OLED Display ($128 \times 64$, I2C)
- **VCC** $\rightarrow$ **Pico 2 W Pin 36 (3V3 OUT)**
- **GND** $\rightarrow$ **Pico 2 W Pin 3 (GND)**
- **SDA** $\rightarrow$ **Pico 2 W Pin 6 (GP4, I2C0 SDA)**
- **SCL** $\rightarrow$ **Pico 2 W Pin 7 (GP5, I2C0 SCL)**

### C. Actuators (LEDs & Piezo Buzzer)
- **Green LED Anode (+)** $\rightarrow$ $220\ \Omega$ Resistor $\rightarrow$ **Pico 2 W Pin 19 (GP14)**
- **Green LED Cathode (-)** $\rightarrow$ **Pico 2 W Pin 18 (GND)**
- **Red LED Anode (+)** $\rightarrow$ $220\ \Omega$ Resistor $\rightarrow$ **Pico 2 W Pin 20 (GP15)**
- **Red LED Cathode (-)** $\rightarrow$ **Pico 2 W Pin 18 (GND)**
- **Buzzer Positive (+)** $\rightarrow$ **Pico 2 W Pin 21 (GP16)**
- **Buzzer Negative (-)** $\rightarrow$ **Pico 2 W Pin 23 (GND)**

---

## 3. Pin Isolation & Conflict Audit

- **Dedicated Peripherals**:
  - I2C0 Bus: GP4 / GP5
  - GPIO Actuators: GP14 / GP15 / GP16
  - I2S Bus: GP26 / GP27 / GP28
- **Conflict Verdict**: **ZERO CONFLICTS**. Every pin assignment is physically and logically isolated.
