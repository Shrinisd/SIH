# ESP32-S3 Wiring — Hero Arise

**Board:** ESP32-S3 DevKitC-1 (N16R8) — matches `platformio.ini`'s `esp32-s3-devkitc-1` environment.
**Pin source of truth:** `firmware/include/config.h` — if these ever disagree, trust the header, not this doc, and fix this doc.

Do **not** use `ml/results/milestone12_final_wiring.md` — that diagram is for a Raspberry Pi Pico 2 W, a different board with a different pinout, from an earlier detour. See `ml/results/README.md`.

## Connections

### INMP441 I2S digital MEMS microphone
| INMP441 pin | ESP32-S3 pin | Notes |
|---|---|---|
| VDD | 3V3 | |
| GND | GND | |
| L/R | GND | selects left channel / mono, matches `I2S_CHANNEL_FMT_ONLY_LEFT` in `main.cpp` |
| SCK (BCLK) | GPIO 12 | `PIN_I2S_SCK` |
| WS (LRCLK) | GPIO 11 | `PIN_I2S_WS` |
| SD (data out) | GPIO 10 | `PIN_I2S_SD` |

### SSD1306 OLED (128×64, I2C)
| OLED pin | ESP32-S3 pin | Notes |
|---|---|---|
| VCC | 3V3 | |
| GND | GND | |
| SDA | GPIO 8 | `PIN_OLED_SDA` |
| SCL | GPIO 9 | `PIN_OLED_SCL` |

I2C address `0x3C` (`OLED_I2C_ADDRESS` in `config.h`) — if your module is silkscreened `0x3D`, change it there.

### Actuators
| Component | ESP32-S3 pin | Notes |
|---|---|---|
| Green LED (+, via ~220Ω resistor) | GPIO 4 | `PIN_LED_GREEN` — on during a confirmed wake |
| Red LED (+, via ~220Ω resistor) | GPIO 5 | `PIN_LED_RED` — on while idle/listening, off during a wake (added; the original firmware declared this pin but never drove it) |
| Piezo buzzer (+) | GPIO 6 | `PIN_BUZZER` |
| LED/buzzer (−) | GND | common ground |

## Pin conflict check

- I2C0 (OLED): GPIO 8/9
- I2S (mic): GPIO 10/11/12
- GPIO actuators: GPIO 4/5/6

No overlaps. GPIO 4–6 are safe general-purpose pins on the S3 DevKitC-1 (not strapping pins); GPIO 8/9 and 10/12 are likewise unused by the board's own peripherals (unlike the original ESP32/ESP32-S2, the S3 doesn't reserve these for flash/PSRAM). Double-check against your specific module's silkscreen/schematic if you're on a variant board, since some S3 modules with octal PSRAM do use a handful of high GPIO numbers internally — none of the pins above are in that range.

## Power

Both the INMP441 and SSD1306 run off the DevKitC-1's onboard 3V3 regulator, fed from USB. That's fine for bring-up and demos; if you see brownouts when the buzzer and OLED are both active, add a bulk capacitor (100–220µF) across 3V3/GND near the peripherals rather than assuming the MCU is at fault.
