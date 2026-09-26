#!/usr/bin/env python3
"""
Host client for the ATmega1284P logic IC tester.

Library:
    from ictester import ICTester
    with ICTester() as t:                 # auto-detects the USB-serial port
        print(t.identify(14))
        print(t.test("74LS00"))
        print(t.vec("00H00HGH00H00V"))

CLI:
    ictester.py info
    ictester.py list [--pins 16]
    ictester.py test 74LS00 SN7474N CD4011BE
    ictester.py id [--pins 16]
    ictester.py vec 00H00HGH00H00V [--rep 5]
    ictester.py batch                      # re-run ID on every button press/Enter
    ictester.py raw "TEST 7400"
    add --json for raw JSON, --port to choose the port.

The protocol is one command line in, one JSON line out (see firmware/src/cmd.c).
"""
import argparse
import json
import sys
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:  # pragma: no cover
    sys.exit("pip install pyserial")

USB_SERIAL_VIDS = {0x1A86, 0x0403, 0x10C4, 0x067B}   # CH340, FTDI, CP210x, PL2303


class TesterError(RuntimeError):
    pass


class ICTester:
    def __init__(self, port=None, baud=115200, timeout=10.0):
        self.port = port or self.find_port()
        self.ser = serial.Serial(self.port, baud, timeout=0.25)
        # Opening the port may reset the board (DTR -> 100 nF -> RESET). Wait briefly
        # for the boot banner; a board without auto-reset simply stays silent.
        deadline = time.time() + 2.5
        while time.time() < deadline:
            if b'"ready"' in self.ser.readline():
                break
        self.ser.reset_input_buffer()
        self.ser.timeout = timeout

    @staticmethod
    def find_port():
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if p.vid in USB_SERIAL_VIDS:
                return p.device
        if len(ports) == 1:
            return ports[0].device
        raise TesterError("could not auto-detect the tester; pass --port "
                          f"(seen: {', '.join(p.device for p in ports) or 'none'})")

    def close(self):
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---------------------------------------------------------------- core
    def cmd(self, line, timeout=None):
        """Send one command, return the decoded JSON reply. Raises on {"error":...}."""
        if timeout is not None:
            self.ser.timeout = timeout
        self.ser.write((line.strip() + "\n").encode())
        while True:
            raw = self.ser.readline()
            if not raw:
                raise TesterError(f"timeout waiting for reply to {line!r}")
            raw = raw.decode(errors="replace").strip()
            if not raw.startswith("{"):
                continue                         # ignore noise
            reply = json.loads(raw)
            if "ready" in reply:                 # board reset under us; skip banner
                continue
            if "error" in reply:
                raise TesterError(reply["error"])
            return reply

    # ----------------------------------------------------------- commands
    def info(self):              return self.cmd("INFO")
    def list(self, pins=None):   return self.cmd(f"LIST {pins or ''}")["chips"]
    def test(self, part):        return self.cmd(f"TEST {part}", timeout=10)
    def identify(self, pins=14): return self.cmd(f"ID {pins}", timeout=30)
    def set_pins(self, pins):    return self.cmd(f"PINS {pins}")
    def off(self):               return self.cmd("OFF")
    def limit(self, ma):         return self.cmd(f"LIMIT {int(ma)}")

    def vec(self, vector, rep=1):
        return self.cmd(f"VEC {vector} {rep}")

    def sequence(self, vectors):
        """Apply several raw vectors (chip stays powered), then power down."""
        try:
            return [self.vec(v) for v in vectors]
        finally:
            self.off()


# ------------------------------------------------------------------- CLI
def fmt_icc(v):
    return "n/a" if v is None else f"{v:.1f} mA"


def family_hint(icc, cmos_part):
    """Rough guess from supply current with the test's last vector applied."""
    if icc is None:
        return ""
    if icc < 0.3:
        return "  (µA-level: CMOS - 4000/HC/HCT/AC)"
    if cmos_part:
        return "  (unusually high for CMOS - suspect)"
    if icc < 5:
        return "  (LS/ALS-level current)"
    return "  (standard TTL / S / F-level current)"


def show_test(r):
    if r.get("tripped"):
        return f"{r['part']:>6}  TRIP   over-current - chip reversed or shorted?"
    if r["pass"]:
        cmos = r["part"].startswith("40") or r["part"].startswith("45")
        return f"{r['part']:>6}  PASS   {r['vectors']} vectors, Icc {fmt_icc(r['icc_mA'])}{family_hint(r['icc_mA'], cmos)}"
    f = r["fail"]
    return (f"{r['part']:>6}  FAIL   vector {f['vector']}, pin {f['pin']}: "
            f"expected {f['expected']} got {f['got']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="7400/4000 logic IC tester client")
    ap.add_argument("--port")
    ap.add_argument("--json", action="store_true", help="print raw JSON replies")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info")
    p = sub.add_parser("list"); p.add_argument("--pins", type=int)
    p = sub.add_parser("test"); p.add_argument("parts", nargs="+")
    p = sub.add_parser("id"); p.add_argument("--pins", type=int, default=14)
    p = sub.add_parser("vec"); p.add_argument("vector"); p.add_argument("--rep", type=int, default=1)
    p = sub.add_parser("batch", help="press Enter after each chip swap; runs ID")
    p.add_argument("--pins", type=int, default=14)
    p = sub.add_parser("raw"); p.add_argument("line")
    a = ap.parse_args(argv)

    try:
        with ICTester(a.port) as t:
            out = lambda obj, text: print(json.dumps(obj) if a.json else text)
            if a.cmd == "info":
                i = t.info()
                out(i, "\n".join(f"{k:>9}: {v}" for k, v in i.items()))
            elif a.cmd == "list":
                chips = t.list(a.pins)
                out(chips, "\n".join(f"{c['part']:>6} {c['pins']}p  {c['desc']:<42} [{c['aliases']}]" for c in chips))
            elif a.cmd == "test":
                for part in a.parts:
                    try:
                        r = t.test(part)
                        out(r, show_test(r))
                    except TesterError as e:
                        out({"part": part, "error": str(e)}, f"{part:>6}  ERROR  {e}")
            elif a.cmd in ("id", "batch"):
                while True:
                    r = t.identify(a.pins)
                    if not r["matches"]:
                        text = f"no match among {r['tried']} {a.pins}-pin definitions (dead, unknown, or wrong pin count?)"
                    else:
                        text = "\n".join(f"{m['part']:>6}  {m['desc']:<40} Icc {fmt_icc(m['icc_mA'])}  also: {m['aliases']}"
                                         for m in r["matches"])
                    out(r, text)
                    if a.cmd == "id":
                        break
                    try:
                        input("-- swap chip, Enter to test (Ctrl-C to stop) --")
                    except (KeyboardInterrupt, EOFError):
                        break
            elif a.cmd == "vec":
                try:
                    r = t.vec(a.vector, a.rep)
                    out(r, f"sent {r['sent']}\nread {r['read']}   {'match' if r['match'] else 'MISMATCH'}  Icc {fmt_icc(r.get('icc_mA'))}")
                finally:
                    t.off()
            elif a.cmd == "raw":
                print(json.dumps(t.cmd(a.line)))
    except TesterError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
