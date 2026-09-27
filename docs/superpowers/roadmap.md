# Roadmap: breadboard → perfboard → PCB

Outline only. Each stage gets its own spec and plan when we reach it (see [README](README.md)), and every
stage is built in small steps, each checked on the bench before the next. Details here will change as
the bench teaches us things. Update this file when they do.

A **reference chip set** carries through all phases: the physical chips we trust (starting with a 74LS00
and a 74HC00), each tested at every stage. From stage 1c onwards it is run by one command
(`ictester.py batch` or a small regression script), so each new board is judged by the same checks.

## Phase A: breadboard MVP

**MVP means:** a chip in the ZIF is tested or identified for any package in the database (14/16/20/24
pins), standalone from the button and OLED or over USB. Supply current is measured and over-current cuts
power. It runs from 12 V.

| Stage | Adds | Proven by | Open decisions |
|---|---|---|---|
| **0** | Nano wired straight to a 7400 ([spec](specs/2026-09-26-stage0-nano-breadboard-design.md), [plan](plans/2026-09-26-stage0-nano-breadboard.md)) | `TEST` / `ID` of LS00 and HC00, pulled-wire fault | – |
| **1a** | Two MCP23S17s on SPI replace direct GPIO. New `hal_nano1.c` with shadow registers. Pin map generated from `tools/design.py` so firmware, schematic and wiring can't disagree. VCC stays on a direct Nano pin; GND is a jumper moved per package. | Stage 0 checks through one expander, then both. A 16-pin chip (4040: exercises long clock runs) with the GND jumper on ZIF 8. | Generate a C header from `design.py`, or hand-copy the table and test it? |
| **1b** | Power path: 12 V jack, 7805, BC327 VCC switch on ZIF 40, 2N7000 GND switches on 7/8/10/12, INA219 current sense and trip. | `INFO` shows sensible `icc_mA`/`vbus_mV`. A resistor load trips the limit. A reversed chip is caught by current, not heat. 20- and 24-pin chips. | Support non-standard power pins (VCC on ZIF 1/4/5, GND on 36/37, e.g. 7490)? `hal.h` has no API for it yet. |
| **1c** | Front panel and socket: OLED, button, 40-pin ZIF. `HAVE_PANEL` build. | Button ID with no PC attached. Reference chip set passes from the ZIF. | – |

## Phase B: perfboard

Goal: the MVP circuit, soldered, reliable enough to use day to day.

- **Freeze first.** `design.py` and the stage 1 sheets are the source of truth. Any change the perfboard
  forces goes back into them before it's soldered.
- **Layout on paper (or generated) before soldering.** Place the ZIF, Nano (socketed) and expanders first,
  and keep the 220 Ω resistors next to the ZIF.
- **Build and test in the same order as the stages:**
  1. Power section alone, no ICs (measure 5 V, check polarity protection).
  2. Nano + expanders (the stage 1a checks).
  3. Power switches + INA219 (the 1b checks).
  4. Panel (the 1c checks).
  Socket every IC.
- **Done when:** the reference chip set passes, and it survives a soak run (a few hundred `ID`s) and a
  week of real use.

## Phase C: PCB

Goal: a board that can be ordered and rebuilt.

- **Capture in KiCad** from `design.py`, either as a generated netlist or a checked hand capture.
  Firmware gets its own `BOARD=` if anything moves.
- **Decisions to make at that spec:**
  - Keep the Nano module, or use a bare 328P + CH340?
  - Enclosure and ZIF mounting.
  - Test points for the power rails and SPI.
  - Through-hole or SMD.
- **Review before ordering:** ERC/DRC, a footprint check against the real parts, and a second-pair-of-eyes
  review of the schematic against `WIRING.md`.
- **Bring-up section by section**, as on the perfboard, with a written checklist.
- **Done when:** the PCB passes the same reference-set and soak checks as the perfboard.
