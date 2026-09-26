#!/usr/bin/env python3
"""Draws docs/schematic-mcu.svg/png (schemdraw). Sheet 1 is tools/power_sheet.py."""
import os
import schemdraw
import schemdraw.elements as elm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs")
schemdraw.config(fontsize=11, lw=1.3)


def save(d, name):
    d.save(os.path.join(OUT, name + ".svg"))
    d.save(os.path.join(OUT, name + ".png"), dpi=130)


# -------------------------------------------------------------- sheet 2: MCU
DIP40 = ["PB0", "PB1", "PB2", "PB3", "PB4", "PB5", "PB6", "PB7", "/RESET", "VCC",
         "GND", "XTAL2", "XTAL1", "PD0", "PD1", "PD2", "PD3", "PD4", "PD5", "PD6",
         "PD7", "PC0", "PC1", "PC2", "PC3", "PC4", "PC5", "PC6", "PC7", "AVCC",
         "GND", "AREF", "PA7", "PA6", "PA5", "PA4", "PA3", "PA2", "PA1", "PA0"]
NET = {
    "PA0": "ZIF1", "PA1": "ZIF2", "PA2": "ZIF3", "PA3": "ZIF4", "PA4": "ZIF5", "PA5": "ZIF6",
    "PA6": "ZIF7", "PA7": "ZIF8", "PC2": "ZIF9", "PC3": "ZIF10", "PC4": "ZIF11", "PC5": "ZIF12",
    "PB0": "ZIF29", "PB1": "ZIF30", "PB2": "ZIF31", "PC6": "ZIF32", "PC7": "ZIF33",
    "PD2": "ZIF34", "PD3": "ZIF35", "PD4": "ZIF36", "PD5": "ZIF37", "PD6": "ZIF38", "PD7": "ZIF39",
    "PB3": "BUTTON → GND", "PB4": "1k → LED → GND", "PB5": "ISP MOSI", "PB6": "ISP MISO", "PB7": "ISP SCK",
    "/RESET": "10k → +5V, ISP RST, (100nF ← DTR)", "VCC": "+5V (100nF)", "GND": "GND", "AVCC": "+5V (100nF)",
    "AREF": "100nF → GND", "XTAL1": "16 MHz + 22pF", "XTAL2": "16 MHz + 22pF",
    "PD0": "RXD0 ← USB-serial TX", "PD1": "TXD0 → USB-serial RX", "PC0": "SCL", "PC1": "SDA",
}


def sheet_mcu():
    d = schemdraw.Drawing()
    d += elm.Label().at((-7, 18.0)).label("Sheet 2 - ATmega1284P (DIP-40) and the ZIF-40", fontsize=14, halign="left")
    # schemdraw stacks each side's pins bottom-up in list order: left side must be
    # listed 20..1 so pin 1 ends up top-left like the real DIP
    order = list(range(19, -1, -1)) + list(range(20, 40))
    pins = [elm.IcPin(name=DIP40[i], pin=str(i + 1), side="left" if i < 20 else "right",
                      anchorname=f"p{i+1}") for i in order]
    ic = elm.Ic(pins=pins, pinspacing=0.8, edgepadH=0.4, edgepadW=1.6, leadlen=0.5,
                label="U1\nATmega1284P\n16 MHz")
    d += ic.at((0, 0))
    for i, n in enumerate(DIP40):
        a = getattr(ic, f"p{i+1}")
        net = NET[n]
        dut = net.startswith("ZIF")
        if i < 20:
            if dut:
                d += elm.Resistor().left(1.6).at(a).label("220Ω", fontsize=7, ofst=0.02)
                d += elm.Tag().left().label(net, fontsize=9)
            else:
                d += elm.Line().left(0.4).at(a); d += elm.Label().label(net, loc="left", fontsize=9)
        else:
            if dut:
                d += elm.Resistor().right(1.6).at(a).label("220Ω", fontsize=7, ofst=0.02)
                d += elm.Tag().right().label(net, fontsize=9)
            else:
                d += elm.Line().right(0.4).at(a); d += elm.Label().label(net, loc="right", fontsize=9)

    # ZIF-40
    zpins = [elm.IcPin(name="", pin=str(i + 1), side="left" if i < 20 else "right", anchorname=f"z{i+1}")
             for i in order]
    zif = elm.Ic(pins=zpins, pinspacing=0.8, edgepadH=0.4, edgepadW=1.4, leadlen=0.5,
                 label="J1\nZIF-40\n(universal)\n\nchip pin 1\n→ ZIF 1\n(top-justified)")
    d += zif.at((14.5, 0))
    for z in range(1, 41):
        a = getattr(zif, f"z{z}")
        if 13 <= z <= 28:
            d += elm.Line().at(a).length(0.3).left() if z <= 20 else elm.Line().at(a).length(0.3).right()
            d += elm.Label().label("nc", loc="left" if z <= 20 else "right", fontsize=8)
            continue
        if z == 40:
            d += elm.Line().right(0.4).at(a); d += elm.Label().label("V_DUT (sheet 1)", loc="right", fontsize=9)
            continue
        extra = {7: " + Q2", 8: " + Q3", 10: " + Q4", 12: " + Q5"}.get(z, "")
        if z <= 20:
            d += elm.Line().left(0.4).at(a); d += elm.Label().label(f"ZIF{z}{extra}", loc="left", fontsize=9)
        else:
            d += elm.Line().right(0.4).at(a); d += elm.Label().label(f"ZIF{z}", loc="right", fontsize=9)
    d += elm.Label().at((-7, -1.3)).label(
        "Every DUT line: MCU pin → 220 Ω → ZIF contact.  Driving a TTL input low: 1.6 mA × 220 Ω = 0.35 V (+~0.1 V V_OL) < V_IL 0.8 V.  "
        "Worst contention: 5 V / 220 Ω = 22.7 mA < 40 mA abs-max.",
        fontsize=10, halign="left")
    d += elm.Label().at((-7, -1.9)).label(
        "Fuses: lfuse 0xF7 (16 MHz full-swing xtal), hfuse 0xD9 (JTAG OFF - it owns PC2..PC5), efuse 0xFD.  "
        "PB5..7 are kept free for ISP.", fontsize=10, halign="left")
    return d


if __name__ == "__main__":
    save(sheet_mcu(), "schematic-mcu")
    print("ok")
