# Stage 0: Nano + 7400 on a breadboard

**Goal.** Prove the existing software (test engine, chip database, serial API, `host/ictester.py`) on a real
chip with the least hardware possible: an Arduino Nano (ATmega328P) wired straight to a 7400, no expanders,
no INA219, no OLED, no ZIF socket.

**Done when.** `TEST 7400` passes on a real 74LS00 and a real 74HC00. A pulled wire fails on the right pin.
`ID 14` names the 7400 family. All of it can be driven from `ictester.py` over USB.

**Not in stage 0.** Chips other than 14-pin, supply-current measurement and the over-current trip, the
front panel. `tester.c` and the chip database are not changed. `cmd.c` changes only for one guard, in step 3.

## Wiring

The firmware places a 14-pin chip in a virtual 40-pin ZIF: pins 1–7 at ZIF 1–7, pins 8–14 at ZIF 34–40
(`zif_of()`). The stage 0 HAL maps those ZIF positions to Nano pins.

| Chip pin | ZIF | Nano | AVR | Via |
|---|---|---|---|---|
| 1–6 | 1–6 | D2–D7 | PD2–PD7 | 220 Ω each |
| 7 (GND) | 7 | GND | – | wire |
| 8–12 | 34–38 | D8–D12 | PB0–PB4 | 220 Ω each |
| 13 | 39 | A1 | PC1 | 220 Ω |
| 14 (VCC) | 40 | A0 | PC0 | wire, 100 nF from chip pin 14 to pin 7 |

- **D13 is not used for the chip.** The Nano's on-board LED hangs on it and would load a pull-up read.
  `hal_led` drives it, though nothing calls `hal_led` yet.
- **D0/D1** stay on the USB serial. A2–A5 are left free for later stages.
- **The 220 Ω resistors** limit a drive fight (Nano output against chip output, which happens while `ID`
  tries other parts) to about 20 mA.
- **VCC from A0.** An AVR pin sources the few mA a 74LS00 draws (4.4 mA max) or a 74HC00 draws (µA) with a
  drop of about 0.2 V. A standard-TTL 7400 (up to 22 mA) or a 74S00 is out of range. Don't use them in stage 0.

## Firmware

- **Board selection.** The Makefile gains `BOARD ?= nano0`. That sets `MCU=atmega328p`, the source list
  (`hal_nano0.c`, `ui_null.c`, no `twi.c` / `ssd1306.c` / `ui.c`), and `-DBOARD_NANO0`. The 1284P build
  is dropped from the Makefile. Its `hal_avr.c` stays in the tree for reference, unbuilt.
- **Flashing.** Through the Nano's bootloader:
  `avrdude -c arduino -p m328p -P $(PORT) -b $(UPLOAD_BAUD)`, `UPLOAD_BAUD ?= 115200`
  (57600 for Nanos with the old bootloader). `make fuses` does not apply to the Nano.
- **`hal_nano0.c`** keeps the same shape as `hal_avr.c`: a `zmap[41]` table of port/bit per ZIF position,
  with the 328P register addresses (PINB/PINC/PIND at 0x23/0x26/0x29).
  - `hal_vcc(on)` drives A0 high or low.
  - `hal_gnd()` does nothing (GND is a wire).
  - `hal_icc()` returns `ICC_NONE`, so JSON shows `icc_mA:null` and the trip is off.
  - `hal_vbus_mv()` returns -1.
  - `hal_init()` returns 0, so `INFO` reports `mcp23008:false, ina219:false`.
  - The existing power sequence stays in force, so no chip pin is driven while A0 is low: pins go Hi-Z,
    then VCC comes up, and on the way down pins go Hi-Z before VCC drops.
- **`main.c`.** The 1284P JTAG lines are removed. OLED and button code is compiled only when the board has
  a panel (`HAVE_PANEL`, not set for nano0).
- **`uart.c`.** On the 328P the interrupt vector is named `USART_RX_vect`; pick the name by MCU.
- **Pin-count guard (step 3).** `HAL_MAX_PINS` (14 for nano0, 24 by default) makes `ID`, `PINS` and `VEC`
  reject larger packages with `{"error":"board supports up to 14 pins"}`. The simulated tests keep
  the default of 24, so they are unaffected.

## Steps

Each step is one commit and ends with a check at the bench. Run `make test` before and after any step that
touches `tester.c`, `cmd.c` or the chip database.

| # | Step | Change | Check |
|---|---|---|---|
| 1 | Nano answers over USB | Makefile `BOARD=nano0`, `hal_nano0.c` with an empty pin map, `main.c` / `uart.c` fixes | `make flash PORT=COMx` succeeds. `python host/ictester.py info` prints the INFO JSON with `"chips":50`. `ictester.py raw BOGUS` → `{"error":"unknown command"}`. |
| 2 | One gate | Map chip pins 1–3 and VCC (A0). Wire gate 1, GND and VCC only. | `ictester.py vec 00HXXXGXXXXXXV` → `match:true`. `vec 11LXXXGXXXXXXV` → `match:true`. With the chip left powered after `vec 11LXXXGXXXXXXV`, a meter reads chip pin 3 low and pin 14 about 4.8 V. `off` → pin 14 reads 0 V. |
| 3 | Whole 7400 | Map the remaining nine pins. Add `HAL_MAX_PINS`. | `ictester.py test 7400` passes on the 74LS00 and on the 74HC00. Remove the wire to chip pin 11 → fails with `pin:11`. `ictester.py id --pins 16` → error. |
| 4 | Identify | None expected | `ictester.py id` → 7400 family only. If a 7402/7404/7408 is on hand, swap it in and check `id` names it. |
| 5 | Host workflow | Fixes the real board turns up | `ictester.py test 74LS00 74HC00` and `ictester.py batch` over 10 chip swaps, no timeouts or garbled lines. |

If a step fails, debug it at that step. Don't move on with a known failure.

## Later stages (outline only, each gets its own spec and plan)

- **1a: expanders.** Two MCP23S17s on SPI (D10–D13) replace direct GPIO. New `hal_nano1.c` with shadow
  registers, the same stage 0 7400 checks, then 16- to 24-pin chips.
- **1b: power.** BC327 VCC and 2N7000 GND switches, INA219 current sense and trip, per `docs/stage1/`.
- **1c: panel.** OLED, button, ZIF socket, 12 V supply.
