"""Single source of truth for the stage-1 (Nano 328P + MCP23S17) connections.

The schematic sheets, the wiring tables in docs/STAGE1-NANO.md and (next) the
firmware pin map all read from here, so they cannot disagree.
"""

# ---- chip under test: top-justified in a 40-pin ZIF --------------------------
# Signal positions: left column 1-12, right column 29-40 (40 = top right).
LEFT = list(range(1, 13))
RIGHT = list(range(40, 28, -1))          # 40, 39, ... 29  (top to bottom)

# Expander pin -> ZIF contact. U2 owns the left column, U3 the right.
# GPx7 are output-only on newer datasheet revisions, so they drive VCC switches.
EXP = {
    "U2": {**{f"GPA{i}": f"Z{z}" for i, z in enumerate(range(1, 8))},        # GPA0-6 -> Z1-Z7
           **{f"GPB{i}": f"Z{z}" for i, z in enumerate(range(8, 13))},       # GPB0-4 -> Z8-Z12
           "GPB5": None, "GPB6": None, "GPA7": "VCC_EN_1", "GPB7": "VCC_EN_4"},
    "U3": {**{f"GPA{i}": f"Z{z}" for i, z in enumerate(range(40, 33, -1))},  # GPA0-6 -> Z40-Z34
           **{f"GPB{i}": f"Z{z}" for i, z in enumerate(range(33, 28, -1))},  # GPB0-4 -> Z33-Z29
           "GPB5": None, "GPB6": None, "GPA7": "VCC_EN_40", "GPB7": "VCC_EN_5"},
}
EXP_ADDR = {"U2": 0, "U3": 1}            # A2..A0 strapping (U3: A0 high)

# ---- power switches ---------------------------------------------------------
# (designator, ZIF contact, enable net, driven by)
HIGH_SIDE = [("Q1", 40, "VCC_EN_40", "U3 GPA7"), ("Q2", 1, "VCC_EN_1", "U2 GPA7"),
             ("Q3", 4, "VCC_EN_4", "U2 GPB7"), ("Q4", 5, "VCC_EN_5", "U3 GPB7")]
LOW_SIDE = [("Q5", 7, "GND_EN_7", "D2"), ("Q6", 8, "GND_EN_8", "D3"), ("Q7", 10, "GND_EN_10", "D4"),
            ("Q8", 12, "GND_EN_12", "D5"), ("Q9", 36, "GND_EN_36", "D6"), ("Q10", 37, "GND_EN_37", "D7")]

# ---- Nano (ATmega328P) ------------------------------------------------------
# Physical order: left column pin 1 (TX1) at top ... pin 15 (D12);
# right column pin 30 (VIN) at top ... pin 16 (D13).
NANO_LEFT = [(1, "TX1"), (2, "RX0"), (3, "RST"), (4, "GND"), (5, "D2"), (6, "D3"), (7, "D4"), (8, "D5"),
             (9, "D6"), (10, "D7"), (11, "D8"), (12, "D9"), (13, "D10"), (14, "D11"), (15, "D12")]
NANO_RIGHT = [(30, "VIN"), (29, "GND "), (28, "RST "), (27, "5V"), (26, "A7"), (25, "A6"), (24, "A5"),
              (23, "A4"), (22, "A3"), (21, "A2"), (20, "A1"), (19, "A0"), (18, "AREF"), (17, "3V3"), (16, "D13")]
NANO_NET = {
    "TX1": "USB serial (on-board CH340)", "RX0": "USB serial (on-board CH340)", "RST": "nc",
    "GND": "GND", "GND ": "GND", "RST ": "nc", "VIN": "nc (do not feed 12 V here)", "5V": "+5V",
    **{lo[3]: lo[2] for lo in LOW_SIDE},
    "D8": "BTN", "D9": "LED_STAT", "D10": "EXP_CS", "D11": "MOSI", "D12": "MISO", "D13": "SCK",
    "A0": "EXP_RST", "A1": "spare", "A2": "spare", "A3": "spare", "A4": "SDA", "A5": "SCL",
    "A6": "VIN_SENSE", "A7": "spare", "AREF": "nc", "3V3": "nc",
}

# ---- MCP23S17 SPDIP-28 (DS21952B) -------------------------------------------
MCP_LEFT = [(i + 1, f"GPB{i}") for i in range(8)] + [(9, "VDD"), (10, "VSS"), (11, "CS"), (12, "SCK"), (13, "SI"), (14, "SO")]
MCP_RIGHT = [(28 - i, f"GPA{7-i}") for i in range(8)] + [(20, "INTA"), (19, "INTB"), (18, "RESET"), (17, "A2"), (16, "A1"), (15, "A0")]


def firmware_zmap():
    """ZIF contact -> (expander index, port 0=A/1=B, bit)."""
    m = {}
    for u, pins in EXP.items():
        for pin, net in pins.items():
            if net and net.startswith("Z"):
                m[int(net[1:])] = (0 if u == "U2" else 1, 0 if pin[2] == "A" else 1, int(pin[3]))
    return m


def check():
    zs = sorted(firmware_zmap())
    assert zs == LEFT + sorted(RIGHT), zs
    for q, z, net, drv in HIGH_SIDE:
        u, pin = drv.split()
        assert EXP[u][pin] == net, (q, drv)
    assert {z for _, z, _, _ in HIGH_SIDE} == {40, 1, 4, 5}
    assert {z for _, z, _, _ in LOW_SIDE} == {7, 8, 10, 12, 36, 37}
    return True


if __name__ == "__main__":
    check(); print("design ok")
