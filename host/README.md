# host

PC side of the serial API.

| File | Purpose |
|---|---|
| [ictester.py](ictester.py) | Python library and CLI. Finds the board by USB-serial chip (CH340, FTDI, CP210x, PL2303), waits out the reset on connect, and sends one command per line. |

CLI commands: `info`, `list [--pins N]`, `test PART...`, `id [--pins N]`, `vec VECTOR [--rep N]`,
`batch` (swap a chip, press Enter, repeat), `raw LINE`. Needs `pip install pyserial`. The serial API
itself is described in the top-level [README](../README.md#serial-api-115200-8n1-one-line-in-one-json-line-out).
