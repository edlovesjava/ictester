# firmware/test

PC-only test code. It links the real `tester.c`, `cmd.c` and `chips_db.c` against a simulated socket
instead of hardware. How and when to run it: top-level [README](../../README.md#tests-no-hardware-needed).

| File | Purpose |
|---|---|
| `sim_hal.c`, `sim.h` | Simulated socket implementing `hal.h`: pin modes, power, stuck-pin faults, supply current |
| `test_main.c` | `make test`: fake 7400, 7474, 4040 and 74193 models (written independently of `tools/chips.py`), fault, lookup and API checks |
| `fake_board.c` | `make sim`: the real command handler on stdin/stdout with a fake 7400, for trying the serial API without hardware |
