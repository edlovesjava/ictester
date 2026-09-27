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
