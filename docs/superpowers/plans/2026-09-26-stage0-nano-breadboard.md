# Stage 0: Nano + 7400 on a breadboard. Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the existing test engine, chip database and serial API on an Arduino Nano wired straight to a
74LS00/74HC00, driven from `host/ictester.py` over USB.

**Architecture:** A new board-specific hardware layer (`hal_nano0.c`) maps the firmware's virtual ZIF-40
positions onto Nano GPIO. The Makefile selects it with `BOARD=nano0`. The portable core (`tester.c`,
`cmd.c`, `chips_db.c`) is unchanged except for one pin-count guard in `cmd.c`, added test-first in task 3.

**Tech Stack:** C (gnu11), avr-gcc 7.3 (PlatformIO toolchain), avrdude 8 with the Arduino bootloader,
MSYS2 UCRT64 gcc for `make test`, Python 3 + pyserial for the host.

**Spec:** [docs/superpowers/specs/2026-09-26-stage0-nano-breadboard-design.md](../specs/2026-09-26-stage0-nano-breadboard-design.md)

## Global Constraints

- Run every command from a **Git Bash** terminal, not PowerShell. Paths below are relative to the repo root unless a step `cd`s.
- Board: Arduino Nano, ATmega328P at 16 MHz, CH340 USB serial. Serial 115200 8N1.
- Chips: **74LS00 or 74HC00 only.** Not a standard-TTL 7400 or a 74S00 (too much supply current for A0).
- Every chip signal pin goes through its own **220 Ω** resistor. VCC (chip pin 14) goes straight to A0. GND (pin 7) is a wire. 100 nF across pins 14–7.
- D13 is never a chip pin; it is the status LED. D0/D1 stay on USB serial.
- `tester.c`, `chips_db.c`, the vector format and the serial API don't change. `cmd.c` changes only in task 3.
- `make test` must end with `ALL TESTS PASSED (0 failures)` before and after any task that touches `tester.c`, `cmd.c`, `test/` or the chip DB.
- One commit per task. Each commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- If a bench check fails, debug it in that task (superpowers:systematic-debugging). Don't start the next task with a known failure.

## Review Focus

1. **Nano with the old bootloader** (57600 baud): `make flash` fails with `not in sync`. Expected: rerun with `UPLOAD_BAUD=57600` works. Task 1 records which one this Nano needs.
2. **Port opened → Nano resets** (DTR). Expected: `ictester.py` skips the boot banner and the first command still gets its reply. Checked in task 1 (`info` is the first command after open).
3. **A 16/20/24-pin command on the 14-pin board** (`ID 16`, `TEST 4040`, a 16-char `VEC`, `PINS 16`). Expected: an error, and the socket is never powered. Pinned by the simulated test in task 3.
4. **Chip left powered after `VEC`**, then the host exits. Expected: `OFF` (or the next `TEST`) powers down cleanly, with pin 14 at 0 V afterwards. Checked with a meter in task 2.
5. **Wrong chip during `ID`:** other parts' vectors drive the 7400's outputs. Expected: the 220 Ω resistors hold each fight to about 20 mA, and nothing gets hot. Checked by touch and by a clean `TEST 7400` straight after `ID` in task 4.

---

### Task 1: Nano answers over USB

The firmware builds for the 328P and talks JSON over USB. No chip is wired yet. There is no PC test for this
task: the checks are a clean `-Werror` build, an unchanged `make test`, and the board answering at the bench.

**Files:**
- Modify: `firmware/Makefile` (full replacement below)
- Create: `firmware/src/hal_nano0.c`
- Create: `firmware/src/ui_led.c`
- Modify: `firmware/src/main.c` (full replacement below)
- Modify: `firmware/src/uart.c` (the `ISR(...)` line)
- Modify: `firmware/README.md`, `firmware/src/README.md`, `README.md` (Quick start)

**Interfaces:**
- Consumes: `hal.h` (unchanged in this task), `ui.h`, `cmd.h`, `uart.h`, `config.h`.
- Produces: `BOARD=nano0` build; `make flash PORT=... [UPLOAD_BAUD=...]`; `make db`. `hal_nano0.c` implements every function in `hal.h`, with a `zmap[41]` table that tasks 2 and 3 fill in. `ui_led.c` implements `ui.h` using `hal_led()`.

- [x] **Step 1: Baseline.** Run `cd firmware && make test | tail -1`. Expected: `ALL TESTS PASSED (0 failures)`.

- [x] **Step 2: Replace `firmware/Makefile`**

```make
# IC tester firmware -- avr-gcc / avrdude
#   make                        build for BOARD (default nano0)
#   make flash PORT=COM5        upload through the Nano's bootloader
#   make test / make sim        PC builds against the simulated socket
#   make db                     regenerate src/chips_db.c after editing tools/chips.py
BOARD   ?= nano0
F_CPU    = 16000000UL
PORT    ?=
# 115200 for current Nanos; 57600 for Nanos with the old bootloader
UPLOAD_BAUD ?= 115200
PYTHON  ?= python

ifeq ($(BOARD),nano0)
# Stage 0: Nano wired straight to a 14-pin chip on a breadboard
MCU      = atmega328p
PART     = m328p
BOARDSRC = src/hal_nano0.c src/ui_led.c
else
$(error Unknown BOARD '$(BOARD)'. Supported: nano0)
endif

SRC      = src/main.c src/uart.c src/cmd.c src/tester.c src/chips_db.c $(BOARDSRC)
CFLAGS   = -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Os -std=gnu11 -Wall -Wextra -Werror \
           -ffunction-sections -fdata-sections -Isrc
LDFLAGS  = -Wl,--gc-sections -Wl,-Map,build/ictester.map

# PC compiler for make test / make sim. On Windows this is MSYS2 UCRT64 gcc; its
# bin directory is put on PATH for those two targets only (gcc needs its helpers).
HOSTCC  ?= gcc
ifeq ($(OS),Windows_NT)
HOSTBIN ?= /c/msys64/ucrt64/bin
endif
HOSTENV  = $(if $(HOSTBIN),PATH="$(HOSTBIN):$$PATH")

all: build/ictester.hex size

build/ictester.elf: $(SRC) src/*.h | build
	avr-gcc $(CFLAGS) $(SRC) $(LDFLAGS) -o $@

build/ictester.hex: build/ictester.elf
	avr-objcopy -O ihex -R .eeprom $< $@

build:
	mkdir -p build

size: build/ictester.elf
	avr-size --format=avr --mcu=$(MCU) $<

flash: build/ictester.hex
	@test -n "$(PORT)" || { echo "Set PORT, e.g. make flash PORT=COM5"; exit 1; }
	avrdude -c arduino -p $(PART) -P $(PORT) -b $(UPLOAD_BAUD) -D -U flash:w:$<:i

db:
	cd .. && $(PYTHON) tools/chips.py

# Host-side engine tests: real tester.c + cmd.c + chip DB against simulated chips
test:
	mkdir -p build
	$(HOSTENV) $(HOSTCC) -std=gnu11 -Wall -Wextra -Werror -Isrc -o build/host_test \
	   test/test_main.c test/sim_hal.c src/tester.c src/cmd.c src/chips_db.c
	$(HOSTENV) ./build/host_test

# Simulated board on stdin/stdout (sim 7400) for exercising the serial API without hardware
sim:
	mkdir -p build
	$(HOSTENV) $(HOSTCC) -std=gnu11 -Wall -Isrc -o build/fake_board test/fake_board.c test/sim_hal.c src/tester.c src/cmd.c src/chips_db.c

clean:
	rm -rf build

.PHONY: all size flash db test sim clean
```

Two changes from the old Makefile. The 1284P build and `make fuses` are gone (the Nano's fuses are
never touched). The automatic `src/chips_db.c: ../tools/chips.py` rule becomes an explicit `make db`, so a
fresh clone's file timestamps can't trigger a regeneration.

- [x] **Step 3: Create `firmware/src/hal_nano0.c`**

```c
/* Stage 0 hardware layer: Arduino Nano (ATmega328P) wired straight to a
 * 14-pin chip on a breadboard.
 * Spec: docs/superpowers/specs/2026-09-26-stage0-nano-breadboard-design.md
 *
 * A 14-pin chip sits top-justified in the virtual ZIF-40 (tester.c zif_of):
 * pins 1-7 at ZIF 1-7, pins 8-14 at ZIF 34-40. Each signal pin reaches its
 * Nano pin through its own 220 ohm resistor.
 *
 *   ZIF 1..6   -> D2..D7  (PD2..PD7)     chip pins 1..6
 *   ZIF 7      -> GND wire, no GPIO       chip pin 7
 *   ZIF 34..38 -> D8..D12 (PB0..PB4)     chip pins 8..12
 *   ZIF 39     -> A1      (PC1)          chip pin 13
 *   ZIF 40     -> A0      (PC0) = VCC    chip pin 14, no resistor
 *
 * D13 (PB5) is the on-board LED, never a chip pin.
 * No INA219: supply current is unknown and the over-current trip is off.
 */
#include <avr/io.h>
#include <util/delay.h>
#include "hal.h"

#define P(port, bit) (uint8_t)(((port) << 3) | (bit))
enum { B_, C_, D_ };
#define NONE 0xFF

static const uint8_t zmap[41] = {
    NONE,
    NONE, NONE, NONE, NONE, NONE, NONE,          /* ZIF 1-6:  D2-D7 (tasks 2, 3) */
    NONE,                                         /* ZIF 7:    GND wire           */
    NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, /* ZIF 8-17  */
    NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, NONE, /* ZIF 18-27 */
    NONE, NONE, NONE, NONE, NONE, NONE,          /* ZIF 28-33: unused            */
    NONE, NONE, NONE, NONE, NONE,                /* ZIF 34-38: D8-D12 (task 3)   */
    NONE,                                         /* ZIF 39:   A1     (task 3)    */
    NONE                                          /* ZIF 40:   VCC, see hal_vcc   */
};

/* ATmega328P: PINx/DDRx/PORTx for B, C, D live at 0x23, 0x26, 0x29 (+1, +2) */
#define R_PIN(k)  (*(volatile uint8_t *)(0x23 + 3 * (k)))
#define R_DDR(k)  (*(volatile uint8_t *)(0x24 + 3 * (k)))
#define R_PORT(k) (*(volatile uint8_t *)(0x25 + 3 * (k)))

#define VCC_BIT PC0     /* A0 feeds chip pin 14 directly */
#define LED_BIT PB5     /* D13, on-board LED */

void hal_pin(uint8_t zif, uint8_t mode)
{
    uint8_t e = zmap[zif];
    if (e == NONE) return;
    uint8_t k = e >> 3, m = (uint8_t)(1 << (e & 7));
    switch (mode) {
    case PM_HIZ:    R_DDR(k) &= (uint8_t)~m; R_PORT(k) &= (uint8_t)~m; break;
    case PM_PULLUP: R_DDR(k) &= (uint8_t)~m; R_PORT(k) |= m; break;
    case PM_LOW:    R_PORT(k) &= (uint8_t)~m; R_DDR(k) |= m; break;
    case PM_HIGH:   R_PORT(k) |= m; R_DDR(k) |= m; break;
    }
}

uint8_t hal_read(uint8_t zif)
{
    uint8_t e = zmap[zif];
    if (e == NONE) return 0;
    return (R_PIN(e >> 3) >> (e & 7)) & 1;
}

void hal_all_hiz(void)
{
    for (uint8_t z = 1; z < 40; z++) hal_pin(z, PM_HIZ);
}

void hal_gnd(uint8_t zif) { (void)zif; }            /* GND is a wire */

void hal_vcc(uint8_t on)
{
    if (on) PORTC |= 1 << VCC_BIT; else PORTC &= (uint8_t)~(1 << VCC_BIT);
}

int16_t hal_icc(void) { return ICC_NONE; }
int16_t hal_vbus_mv(void) { return -1; }
void hal_delay_us(uint16_t us) { while (us--) _delay_us(1); }
void hal_delay_ms(uint16_t ms) { while (ms--) _delay_ms(1); }
void hal_led(uint8_t on) { if (on) PORTB |= 1 << LED_BIT; else PORTB &= (uint8_t)~(1 << LED_BIT); }

uint8_t hal_init(void)
{
    hal_all_hiz();
    PORTC &= (uint8_t)~(1 << VCC_BIT);                /* VCC off ...       */
    DDRC |= 1 << VCC_BIT;                             /* ... then drive it */
    DDRB |= 1 << LED_BIT;
    return 0;                                         /* no MCP23008, no INA219 */
}
```

VCC control on A0 lands now, although nothing is wired to it until task 2. Tasks 2 and 3 only add
`zmap` entries.

- [x] **Step 4: Create `firmware/src/ui_led.c`**

```c
/* Front panel for boards without an OLED: the status LED is on while a test
 * or identify runs and off when the result is in. */
#include "ui.h"
#include "hal.h"

void ui_ready(uint8_t pins) { (void)pins; hal_led(0); }
void ui_busy(const char *name_P, uint8_t pins) { (void)name_P; (void)pins; hal_led(1); }
void ui_test_result(uint8_t idx, const result_t *r) { (void)idx; (void)r; hal_led(0); }
void ui_id_result(uint8_t pins, uint8_t nmatch, const uint8_t *first) { (void)pins; (void)nmatch; (void)first; hal_led(0); }
```

- [x] **Step 5: Replace `firmware/src/main.c`**

The 1284P JTAG lines go. The OLED and button code stays, compiled only for boards that define
`HAVE_PANEL` (none yet; stage 1c brings it back).

```c
#include <avr/io.h>
#include <avr/interrupt.h>
#include "config.h"
#include "hal.h"
#include "uart.h"
#include "cmd.h"
#include "ui.h"

#ifdef HAVE_PANEL                                 /* OLED + button boards */
#include <util/delay.h>
#include "ssd1306.h"

static const uint8_t pin_opts[] = {14, 16, 20, 24};

static void button(void)
{
    if (PINB & (1 << BTN_BIT)) return;
    _delay_ms(30);
    if (PINB & (1 << BTN_BIT)) return;
    uint16_t t = 0;
    while (!(PINB & (1 << BTN_BIT)) && t < 2000) { _delay_ms(10); t += 10; }
    if (t >= 700) {                               /* long press: next package size */
        uint8_t i = 0;
        while (pin_opts[i] != default_pins) i++;
        default_pins = pin_opts[(i + 1) & 3];
        ui_ready(default_pins);
    } else {
        cmd_identify(default_pins);               /* also reports on serial */
    }
    while (!(PINB & (1 << BTN_BIT))) ;
    _delay_ms(30);
}
#endif

int main(void)
{
    hal_status = hal_init();
    uart_init();
    sei();
#ifdef HAVE_PANEL
    oled_init();
#endif
    ui_ready(default_pins);
    printf_P(PSTR("{\"ready\":true,\"fw\":\"" FW_VERSION "\",\"mcp23008\":%s,\"ina219\":%s}\n"),
             (hal_status & 1) ? "true" : "false", (hal_status & 2) ? "true" : "false");
    for (;;) {
        char *l = uart_getline();
        if (l) cmd_exec(l);
#ifdef HAVE_PANEL
        button();
#endif
    }
}
```

- [x] **Step 6: Fix the UART vector name in `firmware/src/uart.c`.** Replace the line `ISR(USART0_RX_vect)` with:

```c
#ifndef USART0_RX_vect                 /* ATmega328P names its only USART without the 0 */
#define USART0_RX_vect USART_RX_vect
#endif

ISR(USART0_RX_vect)
```

- [x] **Step 7: Build.** Run `cd firmware && make`. Expected: no warnings, and `avr-size` reports
`Device: atmega328p`, `Program: 22376 bytes (68.3% Full)` (±100 bytes is fine) and `Data: 509 bytes`.

- [x] **Step 8: PC tests unchanged.** Run `make test | tail -1`. Expected: `ALL TESTS PASSED (0 failures)`.

- [x] **Step 9: Update the READMEs.**
  - `firmware/README.md`: the Makefile row becomes `make` (build, `BOARD=nano0` default), `make flash PORT=COMx [UPLOAD_BAUD=57600]`, `make db`, `make test`, `make sim`, `make clean`.
  - `firmware/src/README.md`: add `hal_nano0.c` (stage 0 Nano, direct GPIO) and `ui_led.c` (LED-only panel) to the hardware-layer table. Mark `hal_avr.c`, `twi.c`, `ssd1306.c`, `font5x7.h` and `ui.c` as *not built for nano0; kept for stage 1*.
  - `README.md` Quick start: replace the USBasp/fuses lines with `cd firmware && make && make flash PORT=COM5`, and use `python` rather than `python3` (Windows).

- [x] **Step 10: Bench check (Ed).** Plug in the Nano alone, with nothing else wired.
  1. Find the port: Device Manager → Ports shows `USB-SERIAL CH340 (COMx)`. If there's no CH340 entry, install the CH340 driver first.
  2. `cd firmware && make flash PORT=COMx`. Expected: avrdude ends `... bytes of flash verified`. If it says `not in sync`, rerun with `UPLOAD_BAUD=57600` and note which one worked in the commit message.
  3. `python ../host/ictester.py --json info`. Expected: a JSON line with `"fw": "1.0"`, `"chips": 50`, `"pins": 14`, `"mcp23008": false`, `"ina219": false`, `"powered": 0`, `"icc_mA": null`. `ictester.py` prints JSON with a space after each colon.
  4. `python ../host/ictester.py raw BOGUS`. Expected: an `unknown command` error.
  5. `python ../host/ictester.py --json test 7400`. Expected: `"pass": false` (nothing is wired yet, so this only proves the command runs end to end).

- [x] **Step 11: Commit**

```bash
git add firmware/Makefile firmware/src/hal_nano0.c firmware/src/ui_led.c firmware/src/main.c firmware/src/uart.c firmware/README.md firmware/src/README.md README.md
git commit -m "Stage 0 step 1: build for the Nano (BOARD=nano0), answer over USB"
git push
```

---

### Task 2: One gate, by hand

**Files:** Modify `firmware/src/hal_nano0.c` (the ZIF 1–3 entries of `zmap`).

**Interfaces:** Consumes the `zmap` table and `P()` / `D_` from task 1. Produces nothing new.

- [x] **Step 1: Wire it.** On the breadboard: 74LS00 (or 74HC00) with pin 1 → 220 Ω → D2, pin 2 → 220 Ω → D3,
  pin 3 → 220 Ω → D4, pin 7 → Nano GND, pin 14 → A0, 100 nF from pin 14 to pin 7. Leave pins 4–6 and 8–13 unconnected.
- [x] **Step 2: Map ZIF 1–3.** In `zmap`, change the ZIF 1–6 line to:

```c
    P(D_,2), P(D_,3), P(D_,4), NONE, NONE, NONE, /* ZIF 1-6:  D2-D7 (task 3 adds 4-6) */
```

- [x] **Step 3: Build and flash.** `cd firmware && make && make flash PORT=COMx`
- [x] **Step 4: Bench check.**
  1. `python ../host/ictester.py --json vec 00HXXXGXXXXXXV`. Expected: `"match": true`.
  2. `python ../host/ictester.py --json vec 11LXXXGXXXXXXV`. Expected: `"match": true`.
  3. `python ../host/ictester.py --json vec 11HXXXGXXXXXXV`. Expected: `"match": false`, and `"read"` shows `L` in the third position. This proves a wrong expectation is caught.
  4. Straight after 2 (the chip stays powered after `VEC`): meter chip pin 14 to pin 7 ≈ 4.8 V, and pin 3 to pin 7 below 0.5 V.
  5. `python ../host/ictester.py raw OFF`, then meter pin 14 to pin 7 ≈ 0 V.
- [x] **Step 5: Commit** `hal_nano0.c` as "Stage 0 step 2: first 7400 gate on the breadboard".

---

### Task 3: Whole 7400, plus the 14-pin guard

**Files:**
- Modify: `firmware/src/hal.h` (add `hal_max_pins`)
- Modify: `firmware/src/cmd.c` (add `fits()` and use it in `TEST`, `VEC`, `ID`, `PINS`)
- Modify: `firmware/src/hal_nano0.c` (the rest of `zmap`, plus `hal_max_pins`)
- Modify: `firmware/test/sim.h`, `firmware/test/sim_hal.c`, `firmware/test/test_main.c`

**Interfaces:**
- Produces: `uint8_t hal_max_pins(void);` in `hal.h`: the largest package the board can take (14 for nano0, 24 in the simulation). Test hooks `extern uint8_t sim_max_pins;` (default 24) and `extern unsigned sim_power_ups;` (count of `hal_vcc(1)` calls) in `sim.h`.

- [x] **Step 1: Baseline.** `cd firmware && make test | tail -1` → `ALL TESTS PASSED (0 failures)`.
- [x] **Step 2: Add the interface and sim hooks.** In `src/hal.h`, after `void hal_led(uint8_t on);`:

```c
uint8_t hal_max_pins(void);        /* largest package the board can take: 14..24 */
```

In `test/sim.h`, after the `sim_stuck_pin` line:

```c
extern uint8_t sim_max_pins;          /* what hal_max_pins() reports (default 24) */
extern unsigned sim_power_ups;        /* hal_vcc(1) calls so far */
```

In `test/sim_hal.c`: after `int8_t  sim_stuck_pin = 0, sim_stuck_val = 0;` add
`uint8_t sim_max_pins = 24;` and `unsigned sim_power_ups;`. Change `hal_vcc` to start with
`if (on) sim_power_ups++;`, and add `uint8_t hal_max_pins(void) { return sim_max_pins; }`.

- [x] **Step 3: Write the failing test.** In `test/test_main.c`, just before `/* the serial API, as the host sees it */`:

```c
    /* a board that only takes 14-pin chips must refuse bigger packages
     * without ever powering the socket */
    sim_insert(&s7400); sim_max_pins = 14;
    {
        const char *refuse[] = {"ID 16", "TEST 4040", "VEC 0000000G0000000V", "PINS 16"};
        for (unsigned i = 0; i < sizeof refuse / sizeof *refuse; i++) {
            char line[64]; strcpy(line, refuse[i]);
            unsigned before = sim_power_ups;
            printf("> %s  (14-pin board)\n< ", refuse[i]); fflush(stdout);
            cmd_exec(line);
            CHECK(sim_power_ups == before, "'%s' powered the socket on a 14-pin board", refuse[i]);
        }
        CHECK(default_pins == 14, "PINS 16 accepted on a 14-pin board");
        char ok[] = "TEST 7400";
        unsigned before = sim_power_ups;
        printf("> %s  (14-pin board)\n< ", ok); fflush(stdout);
        cmd_exec(ok);
        CHECK(sim_power_ups > before, "TEST 7400 refused on a 14-pin board");
    }
    sim_max_pins = 24;
```

- [x] **Step 4: Run it and watch it fail.** `make test`. Expected: `TESTS FAILED (4 failures)`, for `ID 16`, `TEST 4040`, the `VEC` and `PINS 16`.
- [x] **Step 5: Implement the guard in `src/cmd.c`.** After `valid_pins()`:

```c
/* Refuse packages the board has no pins for; driving them would push the
 * vectors into whatever is wired to the higher positions. */
static uint8_t fits(uint8_t n)
{
    if (n <= hal_max_pins()) return 1;
    printf_P(PSTR("{\"error\":\"board supports up to %u pins\"}\n"), hal_max_pins());
    return 0;
}
```

Then use it in four places:
  - `cmd_test`: after `chip_t ch; tester_chip(idx, &ch);` add `if (!fits(ch.pins)) return;`
  - `cmd_vec`: after the `valid_pins(n)` check add `if (!fits(n)) return;`
  - `ID`: `if (!valid_pins(n)) err("pins must be 14/16/20/24"); else if (fits((uint8_t)n)) cmd_identify((uint8_t)n);`
  - `PINS`: `if (!valid_pins(n)) err("pins must be 14/16/20/24"); else if (fits((uint8_t)n)) { default_pins = (uint8_t)n; ui_ready(default_pins); printf_P(PSTR("{\"pins\":%u}\n"), n); }`

- [x] **Step 6: Run it and watch it pass.** `make test`. Expected: each refused command prints `{"error":"board supports up to 14 pins"}`, then `ALL TESTS PASSED (0 failures)`.
- [x] **Step 7: Map the rest of the chip.** In `hal_nano0.c`, make the `zmap` lines read:

```c
    P(D_,2), P(D_,3), P(D_,4), P(D_,5), P(D_,6), P(D_,7), /* ZIF 1-6:  D2-D7 */
```
```c
    P(B_,0), P(B_,1), P(B_,2), P(B_,3), P(B_,4), /* ZIF 34-38: D8-D12 */
    P(C_,1),                                      /* ZIF 39:   A1      */
```

and add at the end of the file:

```c
uint8_t hal_max_pins(void) { return 14; }
```

- [x] **Step 8: Wire the rest.** Chip pins 4, 5, 6 → 220 Ω → D5, D6, D7. Pins 8–12 → 220 Ω → D8–D12. Pin 13 → 220 Ω → A1.
- [x] **Step 9: Build and flash.** `make && make flash PORT=COMx`. Expected: clean build, about 22.2 KB.
- [x] **Step 10: Bench check.**
  1. `python ../host/ictester.py test 7400` with the 74LS00 → PASS. Then the same with the 74HC00 → PASS.
  2. Pull the wire at chip pin 11. `python ../host/ictester.py --json test 7400` → `"pass": false` with `"pin": 11`. Put it back → PASS.
  3. `python ../host/ictester.py id --pins 16` → an error: `board supports up to 14 pins`.
- [x] **Step 11: Commit** all the files above as "Stage 0 step 3: whole 7400 wired; refuse packages over 14 pins".

---

### Task 4: Identify

No code change is expected.

- [x] **Step 1:** `python ../host/ictester.py id` with the 74LS00 → one match, `7400` (with aliases 7403 7426 7437 7438 74132).
- [ ] **Step 2:** Feel the chip and the resistors: nothing warm. Then `test 7400` → still PASS (Review Focus 5).
- [x] **Step 3:** If a 7402, 7404 or 7408 is on hand, swap it in and run `id`. Expected: it names the new part.
      A 7402 or 7404 puts outputs on different pins, so expect it to fail every other part's vectors rather than match them.
- [x] **Step 4:** If anything fails, debug it in this task. If a fix is needed, commit it as "Stage 0 step 4: ...".
      Otherwise record the result in the spec's status and move on.

---

### Task 5: Host workflow

- [ ] **Step 1:** `python ../host/ictester.py test 74LS00 74HC00` (with either chip in) → both names resolve to 7400 and both runs PASS against the chip in the socket.
- [ ] **Step 2:** `python ../host/ictester.py batch`. Swap between the LS00 and the HC00 ten times, pressing Enter after each swap, with the USB left connected throughout. Expected: every run identifies 7400, with no timeouts or garbled lines.
      The chip is only powered while a command runs, so swapping between commands is safe.
- [ ] **Step 3:** Fix whatever the real board shows up, test-first in `test/` when the fix is in the portable core.
- [ ] **Step 4:** Mark the spec *Done* in `docs/superpowers/README.md`, update the README's hardware status line
      ("stage 0 works on a breadboard"), and commit as "Stage 0 done: Nano + 7400 breadboard verified".
