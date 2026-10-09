# firmware/src

The files split into a portable core and a hardware layer. The core talks to the hardware only through
`hal.h`, so it builds unchanged for the AVR and for the PC tests.

## Portable core (also built by `make test`)

| File | Purpose |
|---|---|
| `tester.c/.h` | Test engine: power sequencing, applying vectors, running a chip's tests, identify, part-number lookup |
| `cmd.c/.h` | Serial command parser; every command answers with one JSON line |
| `chips_db.c/.h` | Chip database: pinouts and vectors. **Generated** by `tools/chips.py`, do not edit |
| `compat.h` | Lets the core build on a PC (stands in for `avr/pgmspace.h`) |
| `hal.h` | Hardware interface the core calls: pin modes, reads, VCC/GND, supply current, delays |
| `ui.h` | Front-panel hooks the core calls; no-ops in the test build |

## Hardware layer (AVR only)

Built for `BOARD=nano0` (stage 0):

| File | Purpose |
|---|---|
| `hal_nano0.c` | `hal.h` for stage 0: Nano GPIO wired straight to a 14-pin chip, VCC from A0, LED on D13 |
| `ui_led.c` | `ui.h` for boards without an OLED: the LED is on while a test or identify runs |
| `main.c` | Start-up and main loop. OLED and button code only with `HAVE_PANEL` |
| `config.h` | Clock, baud, I²C addresses, current-trip default, test timing |
| `uart.c/.h` | Interrupt-driven serial, bound to `stdout` |

Not built for nano0; kept for stage 1:

| File | Purpose |
|---|---|
| `hal_avr.c` | `hal.h` for the old ATmega1284P board (direct GPIO, MCP23008, INA219). Reference only. |
| `twi.c/.h` | I²C master (INA219, OLED) |
| `ssd1306.c/.h`, `font5x7.h` | Text-only OLED driver and its font |
| `ui.c` | Front-panel screens on the OLED |
