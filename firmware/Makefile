# ATmega1284P IC tester -- avr-gcc / avrdude
MCU      = atmega1284p
F_CPU    = 16000000UL
PROG    ?= usbasp
PORT    ?=
# PC compiler for make test / make sim. On Windows this is MSYS2 UCRT64 gcc; its
# bin directory is put on PATH for those two targets only (gcc needs its helpers).
HOSTCC  ?= gcc
ifeq ($(OS),Windows_NT)
HOSTBIN ?= /c/msys64/ucrt64/bin
endif
HOSTENV  = $(if $(HOSTBIN),PATH="$(HOSTBIN):$$PATH")
SRC      = src/main.c src/hal_avr.c src/twi.c src/uart.c src/ssd1306.c src/ui.c \
           src/cmd.c src/tester.c src/chips_db.c
CFLAGS   = -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Os -std=gnu11 -Wall -Wextra -Werror \
           -ffunction-sections -fdata-sections -Isrc
LDFLAGS  = -Wl,--gc-sections -Wl,-Map,build/ictester.map

# 16 MHz full-swing crystal, JTAG OFF (frees PC2-PC5), SPI on, BOD 2.7 V
LFUSE = 0xF7
HFUSE = 0xD9
EFUSE = 0xFD

all: build/ictester.hex size

build/ictester.elf: $(SRC) src/*.h | build
	avr-gcc $(CFLAGS) $(SRC) $(LDFLAGS) -o $@

build/ictester.hex: build/ictester.elf
	avr-objcopy -O ihex -R .eeprom $< $@

src/chips_db.c: ../tools/chips.py
	python3 ../tools/chips.py

build:
	mkdir -p build

size: build/ictester.elf
	avr-size --format=avr --mcu=$(MCU) $<

flash: build/ictester.hex
	avrdude -c $(PROG) $(if $(PORT),-P $(PORT)) -p m1284p -U flash:w:$<:i

fuses:
	avrdude -c $(PROG) $(if $(PORT),-P $(PORT)) -p m1284p -U lfuse:w:$(LFUSE):m -U hfuse:w:$(HFUSE):m -U efuse:w:$(EFUSE):m

# Host-side engine tests: real tester.c + cmd.c + chip DB against simulated chips
test:
	mkdir -p build
	$(HOSTENV) $(HOSTCC) -std=gnu11 -Wall -Wextra -Werror -Isrc -o build/host_test \
	   test/test_main.c test/sim_hal.c src/tester.c src/cmd.c src/chips_db.c
	$(HOSTENV) ./build/host_test

clean:
	rm -rf build

.PHONY: all size flash fuses test clean sim

# Simulated board on stdin/stdout (sim 7400) for exercising host/ictester.py over a pty
sim:
	mkdir -p build
	$(HOSTENV) $(HOSTCC) -std=gnu11 -Wall -Isrc -o build/fake_board test/fake_board.c test/sim_hal.c src/tester.c src/cmd.c src/chips_db.c
