# ictester: 7400 / 4000 logic IC tester (Arduino Nano + MCP23S17, breadboard)

This tester plugs a chip into a ZIF socket, switches its power on, drives its inputs, reads its outputs,
and reports the result on a 128×64 OLED and as JSON over USB-serial. It can **identify** an unmarked chip
by trying every definition that has the right pin count. It also measures **supply current**, which
catches a reversed chip and gives a rough guess at the logic family.

> **Hardware status (2026-09-26):** the current hardware is **stage 1**: an Arduino Nano (328P) driving the chip
> through two MCP23S17 SPI expanders, with switchable VCC (ZIF 40/1/4/5) and GND (ZIF 7/8/10/12/36/37).
> Schematic and wiring: `docs/stage1/` (start at `sch-0-blocks.png`). The firmware in `firmware/` still targets
> the earlier ATmega1284P design (`docs/old-1284p/`); its hardware layer is ported to the Nano next. The test
> engine, API, chip database and host client carry over unchanged.

```
firmware/   avr-gcc sources, Makefile (make / make flash / make fuses / make test)
host/       ictester.py: Python library + CLI for the serial API
tools/      chips.py (chip database generator), design.py (stage-1 connections), sheets.py / blocks.py / wiring.py
docs/       stage1/ (Nano schematic sheets + WIRING.md), old-1284p/, superpowers/ (specs, plans), chips.txt
```

Each folder has its own `README.md` indexing what is in it.

## Quick start

```
cd firmware
make fuses && make flash          # USBasp; override with PROG=... PORT=...
pip install pyserial
python3 ../host/ictester.py id                 # identify the 14-pin chip in the socket
python3 ../host/ictester.py test 74LS00 CD4013BE
python3 ../host/ictester.py batch --pins 16    # swap chip, press Enter, repeat
```

On the front panel, a **short press runs ID** and a **long press cycles 14 → 16 → 20 → 24 pins**.

## Serial API (115200 8N1, one line in, one JSON line out)

| Command | Reply (example) |
|---|---|
| `INFO` | `{"fw":"1.0","chips":50,"pins":14,"mcp23008":true,"ina219":true,"powered":0,"limit_mA":120.0,"icc_mA":0.0,"vbus_mV":4812}` |
| `LIST [pins]` | `{"chips":[{"part":"7400","pins":14,"vectors":4,"desc":"Quad 2-in NAND","aliases":"7400 7403 ..."},...]}` |
| `TEST <part>` | `{"part":"7400","pins":14,"pass":true,"vectors":4,"icc_mA":1.6}` |
| | `{"part":"7402","pins":14,"pass":false,"vectors":4,"fail":{"vector":0,"pin":4,"expected":"L","got":"H"},"icc_mA":null}` |
| `ID [pins]` | `{"pins":14,"matches":[{"part":"7400","aliases":"...","desc":"Quad 2-in NAND","icc_mA":1.6}],"tried":25}` |
| `VEC <vector> [rep]` | `{"sent":"11H11HGH11H11V","read":"11L11LGL11L11V","match":false,"icc_mA":1.2}` (stays powered) |
| `OFF` | `{"powered":0}` |
| `PINS <n>` / `LIMIT <mA>` | `{"pins":16}` / `{"limit_mA":80}` |

`<part>` is normalised, so `SN74LS00N`, `74HC00`, `CD4011BE`, `MC14013B` and `74HC4040` all resolve.
Errors come back as `{"error":"..."}`.

### Vector alphabet (one char per chip pin, pin 1 first)

| Char | Meaning |
|---|---|
| `0` `1` | drive low / high |
| `C` | clock: rests low, pulsed 0→1→0 (`rep` times) |
| `L` `H` | expect low / high (read with the pull-up on, so a tri-state or open output reads H) |
| `X` | don't care |
| `G` | ground: must be at pin N/2 |
| `V` | VCC: must be at pin N |

## The chip database

`tools/chips.py` holds a pinout and a small behavioural model for each part (50 entries, 76 part
numbers counting aliases). The script replays each chip's stimulus through its model **in exactly the
order the firmware applies it** (pins change one at a time, in pin order, then clock pulses) and emits
`firmware/src/chips_db.c`.

It also checks every chip:
- every input toggles and every output is seen both L and H;
- no CMOS input is ever left floating;
- G and V sit in the right places;
- flip-flop outputs whose power-up state is unknown are marked X.

To add a chip, write its pinout string, a model (or reuse `gate_chip` / `Comb`), and the steps, then
run `python3 tools/chips.py`.

> The pinouts come from the standard TI/NXP/onsemi datasheets. The generator is only as right as the
> pinout typed into it. If a chip you trust shows FAIL, check the entry against its datasheet first.
> `docs/chips.txt` lists every vector with pin names so you can compare by eye.

## Tests (no hardware needed)

### When to run them

Run `make test` **before and after** every change to `tester.c`, `cmd.c`, `tools/chips.py` or
`chips_db.c`. It must end with `ALL TESTS PASSED (0 failures)` and exit 0. If it fails before you have
changed anything, stop and fix that first.

The simulation replaces the hardware layer, so it says nothing about `hal_*.c`, pin maps, wiring or
timing. Those changes are checked on the bench.

### One-time setup (Windows)

The tests need a PC C compiler as well as `avr-gcc`. Use MSYS2's UCRT64 gcc:

```
winget install --id MSYS2.MSYS2 -e
C:\msys64\usr\bin\bash.exe -lc "pacman -S --noconfirm --needed mingw-w64-ucrt-x86_64-gcc make"
```

The Makefile finds it at `C:\msys64\ucrt64\bin` and puts that folder on PATH for `test` and `sim`
only. If MSYS2 lives somewhere else, pass `HOSTBIN=/d/msys64/ucrt64/bin`. On Linux or macOS the
system `gcc` is used and nothing needs setting up. Any compiler can be forced with `HOSTCC=clang`.

### Running

Use a **Git Bash** terminal (in VS Code: terminal dropdown → Git Bash) or an **MSYS2 UCRT64** shell.
PowerShell and cmd do not work, because make hands the recipes to `cmd.exe`, which has no `mkdir -p`.

```
cd firmware
make test                                   # engine + chip DB against simulated chips
make sim                                    # builds build/fake_board (simulated 7400)
printf 'INFO\nTEST 7400\nID 14\n' | ./build/fake_board
```

`make test` prints one line per simulated chip, then the API transcript, then the verdict:

```
sim 7400   own test PASS, ID -> [7400 ]
...
ALL TESTS PASSED (0 failures)
```

`fake_board` answers each command line with one JSON line, exactly as the real board does. Use it to
check the serial API without hardware.

### What they check

`make test` builds the **real** `tester.c`, `cmd.c` and chip DB for the PC. It links them against a
simulated socket whose 7400, 7474, 4040 and 74193 models were written separately from the Python ones.
It checks:
- each part passes its own test and identifies uniquely;
- a stuck-at fault fails, including Q12 on the 4040, which needs more than 2048 clocks to reach;
- an empty socket matches nothing and over-current trips;
- part numbers normalise correctly;
- the API transcript is printed for inspection.
