# Hardware: breadboard build

Schematics: `schematic-power.png` (sheet 1: DUT power, current sense, grounds, I²C) and
`schematic-mcu.png` (sheet 2: ATmega1284P and the ZIF-40).

## The one rule: top-justify the chip

Put pin 1 in ZIF position 1, with the notch toward the lever end you choose as "top", every time.
For a standard DIP-N pinout that puts:

| Package | GND (chip pin N/2) | VCC (chip pin N) | Signal ZIF positions |
|---|---|---|---|
| 14-pin | ZIF 7  | ZIF 40 | 1–6, 34–39 |
| 16-pin | ZIF 8  | ZIF 40 | 1–7, 33–39 |
| 20-pin | ZIF 10 | ZIF 40 | 1–9, 31–39 |
| 24-pin | ZIF 12 | ZIF 40 | 1–11, 29–39 |

Chip pin p maps to ZIF p for p ≤ N/2, and to ZIF 40 − (N − p) for the rest.

The tester doesn't support chips with power pins in odd places: 7490/92/93 and 7476 (VCC on pin 5), and
4049/4050 (VDD on pin 1). Plugging one in won't break anything, because the over-current trip opens Q1,
but it can't be tested.

## Pin map: ZIF → ATmega1284P

Each line goes MCU pin → **220 Ω** → ZIF contact. That's 23 resistors.

| ZIF | Port | DIP-40 pin | | ZIF | Port | DIP-40 pin |
|---|---|---|---|---|---|---|
| 1 | PA0 | 40 | | 29 | PB0 | 1 |
| 2 | PA1 | 39 | | 30 | PB1 | 2 |
| 3 | PA2 | 38 | | 31 | PB2 | 3 |
| 4 | PA3 | 37 | | 32 | PC6 | 28 |
| 5 | PA4 | 36 | | 33 | PC7 | 29 |
| 6 | PA5 | 35 | | 34 | PD2 | 16 |
| 7 | PA6 | 34 | | 35 | PD3 | 17 |
| 8 | PA7 | 33 | | 36 | PD4 | 18 |
| 9 | PC2 | 24 | | 37 | PD5 | 19 |
| 10 | PC3 | 25 | | 38 | PD6 | 20 |
| 11 | PC4 | 26 | | 39 | PD7 | 21 |
| 12 | PC5 | 27 | | 40 | V_DUT rail (no GPIO) | – |

ZIF 7, 8, 10 and 12 also connect to the drain of their 2N7000 (Q2–Q5). The FET goes on the **ZIF side**
of the 220 Ω resistor. ZIF 13–28 aren't used.

## Other MCU pins

| Pin | Use |
|---|---|
| PD0 / PD1 (14, 15) | UART0 RX/TX → USB-serial adapter (CH340/FT232), cross TX↔RX |
| PC0 / PC1 (22, 23) | I²C SCL / SDA, 4.7 kΩ to +5 V (leave these off if your modules already have pull-ups) |
| PB3 (4) | push-button to GND (uses the internal pull-up) |
| PB4 (5) | 1 kΩ → LED → GND (on while testing) |
| PB5–7 (6–8), RESET (9) | ISP header (USBasp). **Take the DUT out of the ZIF before flashing.** |
| RESET (9) | 10 kΩ to +5 V. Optionally 100 nF from the adapter's DTR for auto-reset |
| XTAL1/2 (13, 12) | 16 MHz crystal, 22 pF from each leg to GND |
| VCC 10, AVCC 30 | +5 V, 100 nF at each pin, plus 10 µF on the rail |
| GND 11, 31 | GND |
| AREF 32 | 100 nF to GND |
| PB5, PB6, PB7 | spare after programming |

## I²C bus

| Device | Address | Notes |
|---|---|---|
| MCP23008 (DIP-18) | 0x20 | A0–A2 to GND, /RESET to +5 V. GP0 → Q1, GP1–GP4 → Q2–Q5 |
| INA219 module | 0x40 | Default address. Its 0.1 Ω shunt (R100) sits between Q1's collector and ZIF 40 |
| SSD1306 128×64 | 0x3C | Some modules ship at 0x3D. If yours is one, change `I2C_OLED` in `config.h` |

## Bill of materials

| Qty | Part | Notes |
|---|---|---|
| 1 | ATmega1284P-PU (DIP-40) | 128 KB flash, 16 KB SRAM, 32 I/O |
| 1 | 40-pin universal ZIF | Accepts 0.3″ and 0.6″ DIPs |
| 1 | MCP23008-E/P (DIP-18) | Drives the power switches |
| 1 | INA219 breakout | Current sense with 0.1 Ω shunt |
| 1 | SSD1306 0.96″ I²C OLED | 128×64 |
| 1 | USB-serial adapter, 5 V logic | CH340G or FT232 |
| 1 | USBasp (or other ISP) | Flashing and fuses |
| 1 | BC327 PNP (TO-92) | Q1, high-side switch. A 2N3906 works for chips under ~100 mA |
| 4 | 2N7000 (TO-92) | Q2–Q5, low-side switches (BS170 also fine) |
| 23 | 220 Ω ¼ W | DUT series resistors |
| 1 | 1 kΩ | Q1 base |
| 1 | 1 kΩ | LED |
| 3 | 10 kΩ | Q1 B-E, RESET pull-up, spare |
| 4 | 100 kΩ | 2N7000 gate pull-downs |
| 2 | 4.7 kΩ | I²C pull-ups, if the modules lack them |
| 1 | 16 MHz crystal + 2 × 22 pF | |
| 5 | 100 nF | Decoupling ×3, AREF, C1 on V_DUT |
| 1 | 10 µF | Bulk on +5 V |
| 1 | LED + tactile switch | Front panel |

## Fuses and first flash

```
make fuses          # lfuse 0xF7  hfuse 0xD9  efuse 0xFD   (PROG=usbasp by default)
make flash
```

- **hfuse 0xD9 turns JTAG off.** From the factory, JTAG owns PC2–PC5, which are ZIF 9–12. The firmware also
  sets MCUCR.JTD at boot, belt-and-braces.
- **lfuse 0xF7** selects a full-swing crystal oscillator. That drive mode is more forgiving of breadboard
  capacitance than the low-power one.
- A factory-fresh chip runs at 1 MHz (internal RC ÷ 8), so run `make fuses` with `-B 32` if your USBasp
  can't talk to it (`avrdude … -B 32`).

## Bring-up order

1. **MCU alone** (crystal, decoupling, UART). You should see `{"ready":true,...}` at 115200 baud.
   `INFO` shows `mcp23008:false,ina219:false`.
2. **Add the I²C devices.** `INFO` should now show both `true`. The OLED shows READY.
3. **Add Q1 and the INA219 with an empty socket.** `VEC 000000G000000V` powers the socket. Measure ZIF 40:
   expect about 4.8 V. `INFO` reports `vbus_mV` ≈ 4800 and `icc_mA` ≈ 0. `OFF` should drop ZIF 40 to 0.
4. **Add Q2–Q5.** With a 14-pin setup powered, ZIF 7 should measure a few ohms to GND. The other three should be open.
5. **Add the 23 resistors, then insert a known-good 74LS00** and run `TEST 7400`.

## Why the numbers are what they are

- **220 Ω series resistors.** A standard-TTL input sources up to 1.6 mA when held low (SN7400, VI = 0.4 V).
  That makes 0.352 V across the resistor, plus an estimated 0.05 V of AVR V_OL, so the pin sees about
  0.40 V. V_IL(max) is 0.8 V, which leaves about 0.4 V of margin. At 470 Ω it would be gone. The same resistor limits contention to 5 V / 220 Ω = 22.7 mA, under the
  AVR's 40 mA absolute maximum. Contention happens during auto-ID, when the tester drives a pin that is
  really an output.
- **Reading outputs with pull-ups.** Every pin being read has the AVR's internal pull-up on (20–50 kΩ).
  That's how open-collector parts (7401/03/05/06/07/09/…, 7447) and tri-stated outputs read H.
  The pull-up is weak enough that even a CMOS 4000B output (I_OH about 0.5 mA at 5 V) overrides it easily.
- **CMOS latch-up.** The rule is never to drive a pin of an unpowered chip. Without power,
  5 V / 220 Ω = 23 mA would flow into the input protection diode, which is rated for ±10 mA. The firmware
  sets everything Hi-Z, turns on the ground, then VCC, and only then drives the pins. Power-down runs in
  reverse.
- **The chip's ground sits up to 0.13 V above board ground.** 2N7000 R_DS(on) is 6.0 Ω max at V_GS 4.5 V,
  I_D 75 mA (onsemi), and a standard 7400 draws up to 22 mA with all outputs low. That helps inputs and
  costs outputs 0.13 V, which is nothing against the AVR's 1.5 V input-low threshold.
- **V_DUT should sit roughly 0.1 V below +5 V** (Q1 saturation plus shunt). That figure is an estimate: the
  BC327 sheet only guarantees V_CE(sat) ≤ 0.7 V at 500 mA / 50 mA, so measure it at bring-up. A '1' from the AVR is therefore slightly
  above the chip's VCC. That's well under the ~0.5 V it takes for a protection diode to conduct, and the
  220 Ω resistor limits the current if it ever does.
