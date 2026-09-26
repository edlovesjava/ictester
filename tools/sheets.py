#!/usr/bin/env python3
"""Stage-1 schematic: one sheet per block of the block diagram.

    python3 tools/sheets.py      -> docs/stage1/sch-*.svg/.png
"""
import os
from schlib import Sheet, RED, BLU, GRN
import design as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "stage1")
os.makedirs(OUT, exist_ok=True)

COL = {"main power": "#fdecea", "mcu power": "#fdecea", "chip power": "#fdecea", "mcu": "#fff7e0",
       "control": "#fff7e0", "pin drivers": "#eaf2fb", "zif": "#eaf2fb", "uart/com": "#e8f5e9"}


# =========================================================== 1 main + mcu power
def sheet_power():
    s = Sheet(1500, 820, "Sheet 1 - Main power and MCU power", "main power + mcu power", COL["main power"])
    y, yg = 200, 420                                        # rail and ground y
    # J1 barrel jack
    s.raw('<rect x="40" y="170" width="90" height="270" fill="#fff" stroke="#000" stroke-width="2"/>')
    s.text(85, 300, "J1\n12 V\nbarrel\n(centre +)", 12, "middle", "bold")
    s.wire((130, y), (160, y)); s.text(135, y - 6, "+", 12)
    s.wire((130, yg), (1400, yg))
    s.gnd(610, yg + 0) if False else s.gnd(1300, yg)
    # D1 reverse-polarity
    s.diode(160, y, 250, "D1 1N5819")
    s.wire((250, y), (330, y)); s.dot(290, y); s.text(290, y - 22, "V_IN", 12, "middle", "bold", RED)
    # V_IN sense divider -> A6
    s.wire((290, y), (290, 250)); s.res(290, 250, 290, 320, "R1 22k", -1)
    s.dot(290, 320); s.wire((290, 320), (230, 320)); s.flag(230, 320, "VIN_SENSE", "left")
    s.res(290, 320, 290, yg, "R2 10k", -1); s.dot(290, yg)
    # input caps
    s.dot(360, y); s.wire((330, y), (540, y)); s.cap(360, y, yg, "C1\n100 µF\n25 V", polar=True); s.dot(360, yg)
    s.dot(450, y); s.cap(450, y, yg, "C2\n100 nF"); s.dot(450, yg)
    # U1 L7805
    s.raw('<rect x="540" y="160" width="140" height="90" fill="#fff" stroke="#000" stroke-width="2"/>')
    s.text(610, 200, "U1\nL7805", 13, "middle", "bold")
    s.text(545, y + 4, "IN", 10); s.text(675, y + 4, "OUT", 10, "end"); s.text(610, 244, "GND", 10, "middle")
    s.wire((610, 250), (610, yg)); s.dot(610, yg)
    s.wire((680, y), (1180, y))
    # D2 protection OUT->IN
    s.wire((720, y), (720, 110)); s.dot(720, y)
    s.diode(720, 110, 520, "D2 1N4007  (OUT → IN)")
    s.wire((520, 110), (520, y)); s.dot(520, y)
    # output caps and power LED
    s.dot(780, y); s.cap(780, y, yg, "C3 10 µF", polar=True); s.dot(780, yg)
    s.dot(880, y); s.cap(880, y, yg, "C4\n100 nF"); s.dot(880, yg)
    s.dot(980, y); s.res(980, y, 980, 300, "R3 1k"); s.diode(980, 300, yg, "D3 power", led=True, vertical=True)
    s.dot(980, yg)
    s.text(1080, y - 10, "+5V", 16, "middle", "bold", RED)
    # to mcu power + chip power + control
    s.dot(1180, y); s.wire((1180, y), (1180, 130), (1260, 130)); s.flag(1260, 130, "+5V  → sheets 2, 3, 4", col=RED)
    s.wire((1180, y), (1260, y)); s.flag(1260, y, "+5V  → Nano 5V pin", col=RED)
    # mcu power block
    s.raw('<rect x="1080" y="250" width="400" height="140" rx="6" fill="#fdecea" stroke="#000" stroke-dasharray="6,4"/>')
    s.text(1100, 275, "mcu power", 14, weight="bold")
    s.note(1100, 300, ["Nano 5V pin ← +5V, plus C9 10 µF + C10 100 nF at the pin.",
                        "Nano VIN is NOT connected (no second regulator).",
                        "USB plugged in with 12 V off: USB back-feeds",
                        "+5V through the Nano's diode; D2 protects U1."], 12)
    s.note(40, 500, [
        "D1 1N5819 (Schottky): reverse-polarity protection. Drop ≈ 0.3-0.45 V at 150 mA (estimate), so V_IN ≈ 11.6 V from a 12 V adapter.",
        "U1 dissipation at 150 mA (estimate: Nano 25 + OLED 20 + expanders/INA 3 + LEDs 6 + worst chip 60 + one contention 23 ≈ 140 mA):",
        "      P = (V_IN − 5 V) × I + V_IN × Id = (11.6 − 5) V × 0.15 A + 11.6 V × 0.008 A = 0.99 W + 0.093 W = 1.083 W",
        "      rise = 1.083 W × 50 °C/W (bare TO-220) = 54.2 °C  →  79.2 °C at 25 °C ambient. Fit a clip-on heatsink, or use a 9 V adapter.",
        "R1/R2 divide V_IN by (22k + 10k) / 10k = 3.2 for A6: 11.6 V → 3.63 V; 15 V → 4.69 V (still under 5 V). Firmware refuses to test if V_IN is absent.",
        "C1/C2 at U1's IN pin, C3/C4 at its OUT pin: the datasheet asks for them close to the regulator.",
        "One ground, star-joined here at U1's GND pin; every other block's ground returns to this point.",
    ], 13)
    s.save(os.path.join(OUT, "sch-1-power"))


# =============================================================== 2 mcu + control
def sheet_mcu():
    s = Sheet(1500, 900, "Sheet 2 - MCU (Arduino Nano, ATmega328P) and control", "mcu + control", COL["mcu"])
    e = s.ic(560, 120, 200, D.NANO_LEFT, D.NANO_RIGHT, "A1\nArduino Nano\n(ATmega328P,\nCH340 USB)\n\nin female\nheaders", pitch=36, size=12)
    for name, (x, y) in e.items():
        net = D.NANO_NET[name]
        left = name in dict((n, 1) for _, n in D.NANO_LEFT)
        if net in ("nc", "spare") or net.startswith("nc ") or net.startswith("USB"):
            s.text(x - 6 if left else x + 6, y + 4, net, 11, "end" if left else "start", col="#666")
        elif net == "GND":
            if left: s.wire((x, y), (x - 20, y)); s.gnd(x - 20, y)
            else: s.wire((x, y), (x + 20, y)); s.gnd(x + 20, y)
        elif net == "+5V":
            s.flag(x, y, "+5V", "right", col=RED)
        else:
            s.flag(x, y, net, "left" if left else "right")
    # control block
    s.raw('<rect x="1040" y="100" width="430" height="700" rx="6" fill="#fff7e0" stroke="#000" stroke-dasharray="6,4"/>')
    s.text(1060, 126, "control", 15, weight="bold")
    oled = s.ic(1260, 160, 150, [(1, "GND"), (2, "VCC"), (3, "SCL"), (4, "SDA")], [], "U5\nSSD1306\n128x64\n@0x3C", pitch=28)
    s.flag(*oled["GND"], "GND", "left", col="#000")
    s.flag(*oled["VCC"], "+5V", "left", col=RED)
    s.flag(*oled["SCL"], "SCL", "left"); s.flag(*oled["SDA"], "SDA", "left")
    # I2C pull-ups
    s.rail(1110, 330, "+5V")
    s.res(1090, 330, 1090, 420, "R4\n4.7k", -1); s.res(1150, 330, 1150, 420, "R5\n4.7k", 1)
    s.wire((1090, 330), (1150, 330))
    s.flag(1090, 420, "SCL", "left"); s.flag(1150, 420, "SDA", "right")
    s.text(1060, 470, "R4/R5 only if the OLED/INA219 modules lack pull-ups", 11, col="#666")
    # button
    s.flag(1110, 540, "BTN", "left"); s.wire((1110, 540), (1160, 540)); s.button(1160, 540, 620, "SW1 ID\n(short: identify,\n long: pin count)")
    s.gnd(1160, 620)
    s.text(1060, 660, "D8 uses the internal pull-up; no resistor.", 11, col="#666")
    # status LED
    s.flag(1330, 540, "LED_STAT", "left"); s.wire((1330, 540), (1380, 540))
    s.res(1380, 540, 1380, 620, "R6 1k"); s.diode(1380, 620, 700, "D4\nstatus", led=True, vertical=True); s.gnd(1380, 700)
    # EXP_RST pull-down: keeps expanders in reset while A0 floats during boot
    s.flag(1110, 720, "EXP_RST", "left"); s.wire((1110, 720), (1250, 720)); s.dot(1250, 720)
    s.res(1250, 720, 1250, 780, "R21 10k", 1); s.gnd(1250, 780)
    s.note(40, 760, [
        "SPI (D10 CS, D11 MOSI, D12 MISO, D13 SCK) goes to both expanders on sheet 3; they share one chip-select and are told apart by address (HAEN).",
        "D13 also drives the Nano's on-board LED; it flickers during tests and does not disturb SPI.",
        "D2-D7 drive the six low-side ground switches directly (sheet 4). At reset these pins are inputs, so the 100k pull-downs hold every switch off.",
        "A0 (EXP_RST) holds both expanders in reset until the firmware is ready; R21 keeps them in reset while A0 floats during boot, so every expander pin starts as an input.",
    ], 12)
    s.save(os.path.join(OUT, "sch-2-mcu"))


# ================================================================ 3 pin drivers
def sheet_drivers():
    s = Sheet(1700, 880, "Sheet 3 - Pin drivers (2 × MCP23S17 + 24 × 220 Ω)", "pin drivers", COL["pin drivers"])
    for ux, u in ((340, "U2"), (1140, "U3")):
        e = s.ic(ux, 110, 170, D.MCP_LEFT, D.MCP_RIGHT,
                 f"{u}\nMCP23S17\nSPDIP-28\naddr {D.EXP_ADDR[u]}", pitch=32, size=12)
        for name, (x, y) in e.items():
            left = name in dict((n, 1) for _, n in D.MCP_LEFT)
            d = -1 if left else 1
            if name.startswith("GP"):
                net = D.EXP[u][name]
                if net is None:
                    s.text(x + 6 * d, y + 4, "spare", 11, "end" if left else "start", col="#666")
                elif net.startswith("Z"):
                    s.res(x, y, x + 90 * d, y, "220 Ω", 1, size=10)
                    s.flag(x + 90 * d, y, net, "left" if left else "right")
                else:
                    s.wire((x, y), (x + 20 * d, y)); s.flag(x + 20 * d, y, net, "left" if left else "right")
            elif name == "VDD": s.flag(x, y, "+5V", "left", col=RED)
            elif name == "VSS": s.wire((x, y), (x - 20, y)); s.gnd(x - 20, y)
            elif name in ("CS", "SCK", "SI", "SO"):
                s.flag(x, y, {"CS": "EXP_CS", "SCK": "SCK", "SI": "MOSI", "SO": "MISO"}[name], "left")
            elif name == "RESET": s.flag(x, y, "EXP_RST", "right")
            elif name in ("INTA", "INTB"): s.text(x + 6, y + 4, "nc", 11, col="#666")
            elif name in ("A0", "A1", "A2"):
                hi = (D.EXP_ADDR[u] >> int(name[1])) & 1
                if hi: s.flag(x, y, "+5V", "right", col=RED)
                else: s.wire((x, y), (x + 20, y)); s.gnd(x + 20, y)
    # decoupling
    for i, (u, x) in enumerate((("U2", 700), ("U3", 820))):
        s.rail(x, 620, "+5V"); s.cap(x, 620, 690, f"C{5+i} 100 nF\nat {u} pin 9/10"); s.gnd(x, 690)
    s.note(40, 760, [
        "Series resistor, one per ZIF contact (RS1-RS24, all 220 Ω). A standard-TTL input held low pushes out I_IL = 1.6 mA:",
        "     1.6 mA × 220 Ω = 0.352 V, plus the expander's own drop (V_OL ≤ 0.6 V at 8 mA → ≈ 0.12 V at 1.6 mA, estimate) ≈ 0.47 V < V_IL 0.8 V.",
        "Contention (auto-ID drives a pin that is really an output): 5 V / 220 Ω = 22.7 mA, under the MCP23S17's 25 mA per pin. Several at once can pass its",
        "125 mA VDD limit, so the firmware keeps each vector short and stops at the first mismatch. GPA7/GPB7 drive the VCC switches (output-only on newer revisions).",
    ], 13)
    s.save(os.path.join(OUT, "sch-3-pin-drivers"))


# ================================================================= 4 chip power
def sheet_chip_power():
    s = Sheet(1700, 920, "Sheet 4 - Chip power: current sense, 4 VCC switches, 6 GND switches", "chip power", COL["chip power"])
    # INA219
    ina = s.ic(120, 110, 150, [(1, "VCC"), (2, "GND"), (3, "SCL"), (4, "SDA")], [(5, "VIN+"), (6, "VIN-")],
               "U4\nINA219\nmodule\n@0x40", pitch=30, pinnum=False)
    s.flag(*ina["VCC"], "+5V", "left", col=RED)
    s.flag(*ina["GND"], "GND", "left", col="#000")
    s.flag(*ina["SCL"], "SCL", "left"); s.flag(*ina["SDA"], "SDA", "left")
    x, y = ina["VIN+"]; s.wire((x, y), (x + 30, y), (x + 30, y - 60)); s.rail(x + 30, y - 60, "+5V")
    x, y = ina["VIN-"]; ry = 200
    s.wire((x, y), (x + 60, y), (x + 60, ry), (1560, ry))
    s.text(1500, ry - 10, "VCC_SW", 14, "middle", "bold", RED)
    s.dot(420, ry); s.cap(420, ry, 300, "C7 10 µF", polar=True, side=-1); s.gnd(420, 300)
    s.dot(500, ry); s.cap(500, ry, 300, "C8 100 nF"); s.gnd(500, 300)
    # high-side switches
    for i, (q, z, net, drv) in enumerate(D.HIGH_SIDE):
        bx = 690 + i * 230; by = 300
        E, C = s.pnp(bx, by, f"{q} BC327")
        s.dot(E[0], ry); s.wire((E[0], ry), E)
        # R_BE from rail to base
        s.dot(bx - 40, by); s.wire((bx - 40, by), (bx, by))
        s.wire((E[0], ry + 20), (bx - 40, ry + 20)); s.dot(E[0], ry + 20)
        s.res(bx - 40, ry + 20, bx - 40, by, "10k", -1, size=10)
        s.res(bx - 40, by, bx - 40, by + 90, "1k", -1, size=10)
        s.flag(bx - 40, by + 90, net, "left")
        s.wire(C, (C[0], by + 110)); s.flag(C[0], by + 110, f"Z{z}", "right")
        s.text(C[0], by + 145, f"VCC at ZIF {z}", 11, "middle", "bold")
        s.text(C[0], by + 160, f"gate: {drv}", 10, "middle", col="#666")
    # low-side switches
    s.text(40, 560, "Low-side (ground) switches  -  Q5-Q10 are 2N7000", 15, weight="bold")
    for i, (q, z, net, drv) in enumerate(D.LOW_SIDE):
        dx = 250 + i * 265; dy = 610
        s.flag(dx, dy - 10, f"Z{z}", "right"); s.wire((dx, dy - 10), (dx, dy))
        g = s.nmos(dx, dy, q)
        s.gnd(dx, dy + 90)
        s.dot(g[0] - 20, g[1]); s.wire(g, (g[0] - 40, g[1]))
        s.flag(g[0] - 40, g[1], net, "left", size=11)
        s.res(g[0] - 20, g[1], g[0] - 20, g[1] + 80, "100k", -1, size=10); s.gnd(g[0] - 20, g[1] + 80)
        s.text(dx, dy + 128, f"GND at ZIF {z}  ({drv})", 11, "middle", "bold")
    s.note(40, 780, [
        "Firmware turns on exactly one VCC switch and one GND switch, chosen from the chip's database entry; everything else stays off.",
        "No capacitor on any Z node: ZIF 1, 4, 5 and 40 are also signal lines, and 100 nF × 220 Ω = 22 µs would slow every edge. Decoupling (C7, C8) sits on VCC_SW instead.",
        "An off switch cannot load its contact: Q1-Q4's collector-base junction would need the contact above 5.6 V, and Q5-Q10's body diode would need it below −0.6 V.",
        "U4 reads the chip's current (0.1 mA per count) and VCC_SW, which is before the PNP: the chip itself sees VCC_SW minus Q's V_CE(sat) (measure it once).",
    ], 13)
    s.save(os.path.join(OUT, "sch-4-chip-power"))


# ======================================================================== 5 zif
def sheet_zif():
    s = Sheet(1300, 1040, "Sheet 5 - ZIF-40 (chip inserted top-justified: pin 1 → ZIF 1)", "zif", COL["zif"])
    left = [(z, "") for z in range(1, 21)]
    right = [(z, "") for z in range(40, 20, -1)]
    zx = 520
    n = s.ic(zx, 110, 260, [(str(z), f"{z}") for z, _ in left], [(str(z), f"{z}") for z, _ in right],
             "J2\nZIF-40\nuniversal\n(0.3″ + 0.6″)", pitch=38, pinnum=False, lead=40, size=12)
    hs = {z: q for q, z, _, _ in D.HIGH_SIDE}; ls = {z: q for q, z, _, _ in D.LOW_SIDE}
    zm = D.firmware_zmap()
    for name, (x, y) in n.items():
        z = int(name); left_side = z <= 20
        if z not in zm:
            s.text(x - 6 if left_side else x + 6, y + 4, "nc", 11, "end" if left_side else "start", col="#666")
            continue
        s.flag(x, y, f"Z{z}", "left" if left_side else "right")
        u, port, bit = zm[z]
        extra = f"  ← {'U2' if u == 0 else 'U3'} GP{'AB'[port]}{bit} via 220 Ω"
        if z in hs: extra += f"   + VCC switch {hs[z]}"
        if z in ls: extra += f"   + GND switch {ls[z]}"
        if left_side: s.text(x - 70, y + 4, extra.strip(), 11, "end", col="#444")
        else: s.text(x + 70, y + 4, extra.strip(), 11, col="#444")
    s.note(40, 950, [
        "Standard 14/16/20/24-pin parts: VCC = chip pin N → ZIF 40, GND = chip pin N/2 → ZIF 7/8/10/12.",
        "Odd ones: 7490/92/93 VCC ZIF 5, GND ZIF 36 · 7473 VCC 4, GND 37 · 7476 VCC 5, GND 37 · 7483/75/96 VCC 5, GND 36 · 4049/50 VDD 1, VSS 8.",
        "Chip pin p → ZIF p for p ≤ N/2, else ZIF 40 − (N − p).",
    ], 13)
    s.save(os.path.join(OUT, "sch-5-zif"))


if __name__ == "__main__":
    D.check()
    sheet_power(); sheet_mcu(); sheet_drivers(); sheet_chip_power(); sheet_zif()
    print("ok")
