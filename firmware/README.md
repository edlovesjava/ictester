# firmware

AVR firmware for the tester (plain avr-gcc, no Arduino core), plus a PC build of the test engine for
simulated tests.

| Path | What it is |
|---|---|
| [src/](src/) | Firmware sources |
| [test/](test/) | Simulated socket and chips for `make test` / `make sim` |
| [Makefile](Makefile) | `make` (build; `BOARD=nano0` is the default and only board so far), `make flash PORT=COMx [UPLOAD_BAUD=57600]`, `make db` (regenerate the chip DB), `make test`, `make sim`, `make clean` |
| `build/` | Build output, not tracked |

Build and test instructions are in the top-level [README](../README.md#tests-no-hardware-needed).
