#!/usr/bin/env python3
"""Sheet 1 (power path) drawn as explicit SVG -> docs/schematic-power.svg/.png"""
import os
import cairosvg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1500, 930
out = []


def svg(s): out.append(s)
def wire(*pts): svg('<polyline fill="none" points="%s"/>' % " ".join(f"{x},{y}" for x, y in pts))
def dot(x, y): svg(f'<circle cx="{x}" cy="{y}" r="4" class="f"/>')
def text(x, y, s, size=14, anchor="start", weight="normal"):
    for i, line in enumerate(s.split("\n")):
        svg(f'<text x="{x}" y="{y + i * (size + 3)}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{line}</text>')


def res_v(x, y1, y2, label="", side="right"):
    n, amp = 6, 7
    seg = (y2 - y1 - 20) / n
    pts = [(x, y1), (x, y1 + 10)]
    for i in range(n):
        pts.append((x + (amp if i % 2 == 0 else -amp), y1 + 10 + seg * (i + 0.5)))
    pts += [(x, y2 - 10), (x, y2)]
    wire(*pts)
    if label:
        text(x + 14 if side == "right" else x - 14, (y1 + y2) / 2 - 2, label, 13, "start" if side == "right" else "end")


def res_h(x1, x2, y, label=""):
    n, amp = 6, 7
    seg = (x2 - x1 - 20) / n if x2 > x1 else (x2 - x1 + 20) / n
    d = 1 if x2 > x1 else -1
    pts = [(x1, y), (x1 + 10 * d, y)]
    for i in range(n):
        pts.append((x1 + 10 * d + seg * (i + 0.5), y + (amp if i % 2 == 0 else -amp)))
    pts += [(x2 - 10 * d, y), (x2, y)]
    wire(*pts)
    if label: text((x1 + x2) / 2, y - 14, label, 13, "middle")


def cap_v(x, y1, y2, label=""):
    m = (y1 + y2) / 2
    wire((x, y1), (x, m - 5)); wire((x, m + 5), (x, y2))
    wire((x - 16, m - 5), (x + 16, m - 5)); wire((x - 16, m + 5), (x + 16, m + 5))
    if label: text(x + 22, m + 4, label, 13)


def gnd(x, y):
    wire((x, y), (x, y + 8))
    for i, w in enumerate((14, 9, 4)):
        wire((x - w, y + 8 + i * 5), (x + w, y + 8 + i * 5))


def vcc(x, y, label):
    wire((x - 14, y), (x + 14, y)); text(x, y - 8, label, 14, "middle", "bold")


def flag(x, y, label, direction="right"):
    w = 14 + 8 * len(label)
    if direction == "right":
        svg(f'<polygon fill="none" points="{x},{y} {x+10},{y-11} {x+w},{y-11} {x+w},{y+11} {x+10},{y+11}"/>')
        text(x + 12, y + 5, label, 13)
    else:
        svg(f'<polygon fill="none" points="{x},{y} {x-10},{y-11} {x-w},{y-11} {x-w},{y+11} {x-10},{y+11}"/>')
        text(x - w + 3, y + 5, label, 13)


def arrow(x1, y1, x2, y2):
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    l = 10
    p1 = (x2 - l * math.cos(a - 0.4), y2 - l * math.sin(a - 0.4))
    p2 = (x2 - l * math.cos(a + 0.4), y2 - l * math.sin(a + 0.4))
    svg(f'<polygon class="f" points="{x2},{y2} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"/>')


def pnp(bx, by):
    """base at (bx,by); returns emitter (top) and collector (bottom) terminals."""
    svg(f'<circle cx="{bx+42}" cy="{by}" r="32" fill="none"/>')
    wire((bx, by), (bx + 30, by))
    wire((bx + 30, by - 20), (bx + 30, by + 20))
    wire((bx + 30, by - 10), (bx + 60, by - 36), (bx + 60, by - 60))
    arrow(bx + 60, by - 36, bx + 33, by - 12)            # PNP: arrow points in, toward base
    wire((bx + 30, by + 10), (bx + 60, by + 36), (bx + 60, by + 60))
    return (bx + 60, by - 60), (bx + 60, by + 60)


def nmos(dx, dy):
    """drain terminal (dx,dy) top, source (dx,dy+100) bottom; returns gate terminal."""
    wire((dx, dy), (dx, dy + 32), (dx - 16, dy + 32))
    wire((dx - 16, dy + 68), (dx, dy + 68), (dx, dy + 100))
    wire((dx, dy + 50), (dx - 16, dy + 50)); arrow(dx, dy + 50, dx - 16, dy + 50)
    wire((dx, dy + 50), (dx, dy + 68))
    for y0 in (dy + 26, dy + 44, dy + 62):
        wire((dx - 16, y0), (dx - 16, y0 + 12))
    wire((dx - 26, dy + 28), (dx - 26, dy + 72))
    wire((dx - 26, dy + 50), (dx - 60, dy + 50))
    return (dx - 60, dy + 50)


def box(x, y, w, left, right, title):
    h = 30 + 26 * max(len(left), len(right))
    svg(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none"/>')
    text(x + w / 2, y + h / 2 - 10, title, 14, "middle", "bold")
    for i, (pin, net) in enumerate(left):
        yy = y + 28 + 26 * i
        wire((x - 30, yy), (x, yy)); text(x + 6, yy + 5, pin, 12); text(x - 34, yy + 5, net, 12, "end")
    for i, (pin, net) in enumerate(right):
        yy = y + 28 + 26 * i
        wire((x + w, yy), (x + w + 30, yy)); text(x + w - 6, yy + 5, pin, 12, "end"); text(x + w + 34, yy + 5, net, 12)


# ---------------------------------------------------------------- drawing
text(30, 40, "Sheet 1 - DUT power switch, current sense, low-side grounds, I2C", 20, weight="bold")

# high-side switch
vcc(420, 80, "+5V")
E, C = pnp(360, 180)
wire((420, 80), E)
dot(420, 105)
wire((420, 105), (300, 105))
res_v(300, 105, 180, "R1 10k", "right")
dot(300, 180)
wire((300, 180), (360, 180))
res_h(300, 180, 170, "R2 1k")
text(160, 176, "U2 GP0", 13, "end"); text(160, 193, "(/VCC_EN, active low)", 11, "end")
text(470, 172, "Q1 BC327", 14, weight="bold"); text(470, 190, "PNP, I_C 800 mA", 12)

# shunt + rail
wire(C, (420, 270)); dot(420, 270); text(408, 275, "VIN+", 12, "end")
res_v(420, 270, 360, "R_shunt 0.1 Ω\n(on the INA219 module)")
dot(420, 360); text(408, 365, "VIN-", 12, "end")
wire((420, 360), (420, 400), (760, 400))
dot(600, 400); text(600, 390, "V_DUT", 14, "middle", "bold")
cap_v(600, 400, 470, "C1 100 nF")
gnd(600, 470)
flag(760, 400, "ZIF 40 (chip pin N)")

# low-side switches
text(30, 560, "Low-side ground switches (one per package size)", 15, weight="bold")
for i, (z, gp, pkg) in enumerate(((7, 1, 14), (8, 2, 16), (10, 3, 20), (12, 4, 24))):
    dx = 180 + i * 240
    text(dx, 598, f"ZIF {z}", 14, "middle", "bold"); text(dx, 614, f"({pkg}-pin GND)", 11, "middle")
    wire((dx, 620), (dx, 640))
    g = nmos(dx, 640)
    gnd(dx, 740)
    text(dx + 10, 700, f"Q{i+2}", 13, weight="bold"); text(dx + 10, 716, "2N7000", 11)
    dot(*g)
    res_v(g[0], g[1], g[1] + 80, "100k", "left")
    gnd(g[0], g[1] + 80)
    wire(g, (g[0], g[1] - 25), (g[0] - 30, g[1] - 25))
    text(g[0] - 34, g[1] - 20, f"U2 GP{gp}", 12, "end")

# I2C side
text(1060, 80, "I2C (U1 PC0 = SCL, PC1 = SDA, 4.7k pull-ups to +5V)", 13, weight="bold")
box(1100, 100, 200, [("SCL", "SCL"), ("SDA", "SDA"), ("A0", "GND"), ("A1", "GND"), ("A2", "GND"),
                     ("/RESET", "+5V"), ("VDD", "+5V"), ("VSS", "GND")],
    [("GP0", "Q1 via R2"), ("GP1", "Q2 gate"), ("GP2", "Q3 gate"), ("GP3", "Q4 gate"),
     ("GP4", "Q5 gate"), ("GP5", "-"), ("GP6", "-"), ("GP7", "-")], "U2\nMCP23008\n@ 0x20")
box(1100, 370, 200, [("SCL", "SCL"), ("SDA", "SDA"), ("VCC", "+5V"), ("GND", "GND")],
    [("VIN+", "Q1 collector"), ("VIN-", "V_DUT")], "U3 INA219\n@ 0x40")
box(1100, 540, 200, [("SCL", "SCL"), ("SDA", "SDA"), ("VCC", "+5V"), ("GND", "GND")], [],
    "U4 SSD1306\n128x64 @ 0x3C")

# notes
notes = [
    "Q1 base drive: I_B = (5 V - V_EB 0.7 V - V_OL ~0.1 V) / 1 kΩ - 0.7 V / 10 kΩ ≈ 4.1 mA: forced gain 5.3 at 22 mA, deeper than the BC327 sheet's V_CE(sat) ≤ 0.7 V point (500 mA / 50 mA).",
    "R1 holds Q1 OFF while U2 is in reset (all MCP23008 pins power up as inputs). The 100k gate resistors do the same for Q2-Q5.",
    "INA219 PGA /1: ±40 mV full scale / 0.1 Ω = ±400 mA; 10 µV LSB / 0.1 Ω = 0.1 mA per count. Firmware trips at 120 mA (LIMIT command).",
    "2N7000: R_DS(on) ≤ 6.0 Ω at V_GS 4.5 V, I_D 75 mA → at a standard 7400's I_CCL(max) 22 mA the chip's ground sits ≤ 0.13 V up. (A ULN2003 would lift it ~0.9 V: too much.)",
]
for i, n in enumerate(notes):
    text(30, 830 + i * 22, n, 13)

body = "\n".join(out)
doc = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">
<rect width="100%" height="100%" fill="white"/>
<style>polyline,line,circle,rect,polygon{{stroke:#000;stroke-width:1.8}} .f{{fill:#000}} text{{fill:#000}}</style>
{body}
</svg>'''
open(os.path.join(ROOT, "docs/schematic-power.svg"), "w").write(doc)
cairosvg.svg2png(bytestring=doc.encode(), write_to=os.path.join(ROOT, "docs/schematic-power.png"))
print("ok")
