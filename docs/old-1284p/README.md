# docs/old-1284p

The earlier ATmega1284P design: 24 socket pins on direct GPIO, an MCP23008 for power switching, and an
INA219. **Superseded by [stage1](../stage1/).**

## Rules

- **Frozen.** Don't update these files to match later designs. They record what the 1284P board was.
- The firmware's `hal_avr.c` still targets this board until the Nano HAL replaces it. After that, this
  folder is reference only.

## Index

| File | Contents |
|---|---|
| [HARDWARE.md](HARDWARE.md) | Breadboard build notes, including the top-justify rule for placing chips in the ZIF |
| [schematic-power.png](schematic-power.png) | Sheet 1: DUT power, current sense, grounds, I²C |
| [schematic-mcu.png](schematic-mcu.png) | Sheet 2: ATmega1284P and the ZIF-40 |

Drawn by the scripts in `tools/old-1284p/`. Each sheet also exists as `.svg`.
