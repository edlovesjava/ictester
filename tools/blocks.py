"""Sheet 0: block diagram / index for the stage-1 schematic."""
import cairosvg
W,H=1300,1180
o=[]
def box(x,y,w,h,title,lines=(),fill="#fff",bold=True):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="#000" stroke-width="2"/>')
    o.append(f'<text x="{x+w/2}" y="{y+30}" font-size="20" text-anchor="middle" font-weight="bold">{title}</text>')
    for i,l in enumerate(lines):
        o.append(f'<text x="{x+w/2}" y="{y+56+i*20}" font-size="14" text-anchor="middle">{l}</text>')
def arrow(pts,label="",col="#000",lx=None,ly=None,dash=False):
    d=' stroke-dasharray="7,5"' if dash else ''
    o.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{col}" stroke-width="3"{d} marker-end="url(#a{col[1:]})"/>')
    if label:
        x,y=(lx,ly) if lx else pts[0]
        o.append(f'<text x="{x}" y="{y}" font-size="13" fill="{col}" font-weight="bold">{label}</text>')
RED,BLU,GRN="#c0392b","#1f5fa8","#2e7d32"
box(40,40,300,150,"12 V DC in  (sheet 1)",["barrel jack","D1 1N5819 reverse-polarity","V_IN → A6 via 22k/10k"])
box(480,40,320,150,"main power  (sheet 1)",["12 V → 5 V (L7805 or buck)","1N4007 OUT→IN protection","ONE 5 V rail for everything"],"#fdecea")
box(940,40,320,150,"uart / com  (on the Nano)",["the Nano's own USB","(CH340 serial + bootloader)","ISP header (later: UPDI)"])
box(40,300,240,170,"mcu power (1)",["Nano 5V pin","fed from main 5 V","+ 10 µF, 100 nF"],"#fdecea")
box(360,300,900,170,"mcu  (sheet 2)",["Arduino Nano (328P), in female headers","SPI D10–D13 → expanders   I²C A4/A5 → OLED, INA219","D2–D7 → 6 low-side GND switches   D8, D9 → button, LED"])
box(360,540,900,130,"pin drivers  (sheet 3)",["2× MCP23S17 on SPI, one shared chip-select","24 lines → 24 × 220 Ω → ZIF 1–12, 29–40","GPA7/GPB7 (output-only) → 4 high-side VCC switches"],"#eaf2fb")
box(40,540,240,370,"chip power (4)",["INA219 + 0.1 Ω shunt","on the shared VCC feed","","4 high-side switches","ZIF 40, 1, 4, 5","","6 low-side switches","ZIF 7, 8, 10, 12, 36, 37","","decoupling on VCC_SW,","never on a ZIF contact"],"#fdecea")
box(360,740,900,170,"zif  (sheet 5)",["40-pin universal, chip top-justified (pin 1 → ZIF 1)","VCC/GND switch nodes on the ZIF side of the 220 Ω","ZIF 13–28 unused"])
box(40,990,1220,150,"control  (sheet 2)",["SSD1306 OLED (I²C)   ·   ID button (short = identify, long = pin count)","status LED   ·   power LED   ·   V_IN sense on A6"])
# power (red)
arrow([(340,115),(476,115)],"12 V",RED,380,105)
arrow([(640,190),(640,245),(160,245),(160,296)],"5 V",RED,420,238)
arrow([(640,245),(1290,245),(1290,1000),(1264,1000)],"",RED)
arrow([(20,245),(20,720),(36,720)],"",RED)
o.append(f'<line x1="160" y1="245" x2="20" y2="245" stroke="{RED}" stroke-width="3"/>')
arrow([(280,760),(356,760)],"Z nodes",RED,286,750)
# signals (blue)
arrow([(810,470),(810,536)],"SPI",BLU,820,510)
arrow([(810,670),(810,736)],"24 × 220 Ω",BLU,820,710)
arrow([(356,640),(284,640)],"",BLU)
o.append(f'<text x="290" y="632" font-size="12" fill="{BLU}" font-weight="bold">4 VCC</text>')
arrow([(420,470),(420,500),(160,500),(160,536)],"6 GND gates, I²C",BLU,190,493)
arrow([(1180,470),(1180,520),(1275,520),(1275,985)],"",BLU)
o.append(f'<text x="1150" y="980" font-size="13" fill="{BLU}" font-weight="bold">I²C, D8/D9</text>')
arrow([(1100,190),(1100,296)],"USB",GRN,1110,275)
o.append('<text x="40" y="1170" font-size="14">Red = power, blue = signals, green = USB. One ground, star-joined at the main-power block.</text>')
marks="".join(f'<marker id="a{c[1:]}" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in ("#000",RED,BLU,GRN))
svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="DejaVu Sans, Arial"><defs>{marks}</defs><rect width="100%" height="100%" fill="white"/>{"".join(o)}</svg>'
import os
out=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"docs","stage1","sch-0-blocks")
open(out+".svg","w").write(svg); cairosvg.svg2png(bytestring=svg.encode(),write_to=out+".png")
