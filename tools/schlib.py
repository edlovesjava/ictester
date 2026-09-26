"""Tiny explicit-coordinate SVG schematic library (no auto-layout, nothing clever).

Every drawing call appends to a Sheet; Sheet.save() writes .svg and .png.
Symbols follow common hobby conventions: zig-zag resistors, triangle ground,
bar-with-label supply, pentagon net flags. A net flag with the same text on
two sheets is the same wire.
"""
import math
import cairosvg

RED, BLU, GRN, GRY = "#b03a2e", "#1f5fa8", "#2e7d32", "#666"


class Sheet:
    def __init__(self, w, h, title, block, colour):
        self.w, self.h, self.o = w, h, []
        self.text(30, 42, title, 22, weight="bold")
        # block tag, matching the block diagram
        self.o.append(f'<rect x="{w-330}" y="18" width="300" height="36" rx="5" fill="{colour}" stroke="#000"/>')
        self.text(w - 180, 42, f"block: {block}", 15, "middle", "bold")

    # ---- primitives
    def raw(self, s): self.o.append(s)

    def wire(self, *pts, col="#000"):
        self.o.append('<polyline fill="none" stroke="%s" points="%s"/>' % (col, " ".join(f"{x},{y}" for x, y in pts)))

    def dot(self, x, y): self.o.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#000"/>')

    def text(self, x, y, s, size=13, anchor="start", weight="normal", col="#000"):
        for i, line in enumerate(str(s).split("\n")):
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            self.o.append(f'<text x="{x}" y="{y + i * (size + 3)}" font-size="{size}" text-anchor="{anchor}" '
                          f'font-weight="{weight}" fill="{col}">{line}</text>')

    def arrowhead(self, x1, y1, x2, y2, fill="#000"):
        a = math.atan2(y2 - y1, x2 - x1); l = 10
        p1 = (x2 - l * math.cos(a - 0.4), y2 - l * math.sin(a - 0.4))
        p2 = (x2 - l * math.cos(a + 0.4), y2 - l * math.sin(a + 0.4))
        self.o.append(f'<polygon fill="{fill}" stroke="{fill}" points="{x2},{y2} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"/>')

    # ---- two-terminal parts
    def res(self, x1, y1, x2, y2, label="", side=1, size=12):
        """Resistor between two points on a horizontal or vertical line."""
        n, amp = 6, 6
        L = math.hypot(x2 - x1, y2 - y1); ux, uy = (x2 - x1) / L, (y2 - y1) / L
        px, py = -uy, ux
        body = min(40, L - 12); lead = (L - body) / 2
        pts = [(x1, y1), (x1 + ux * lead, y1 + uy * lead)]
        for i in range(n):
            t = lead + body * (i + 0.5) / n; s = amp if i % 2 == 0 else -amp
            pts.append((x1 + ux * t + px * s, y1 + uy * t + py * s))
        pts += [(x2 - ux * lead, y2 - uy * lead), (x2, y2)]
        self.wire(*pts)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            if abs(uy) > 0.5:   # vertical
                self.text(mx + 12 * side, my + 4, label, size, "start" if side > 0 else "end")
            else:
                self.text(mx, my - 12 if side > 0 else my + 22, label, size, "middle")

    def cap(self, x, y1, y2, label="", polar=False, side=1):
        m = (y1 + y2) / 2
        self.wire((x, y1), (x, m - 5)); self.wire((x, m + 5), (x, y2))
        self.wire((x - 14, m - 5), (x + 14, m - 5))
        if polar:
            self.raw(f'<path d="M{x-14},{m+9} Q{x},{m+2} {x+14},{m+9}" fill="none" stroke="#000"/>')
            self.text(x - 20, m - 8, "+", 13, "middle")
        else:
            self.wire((x - 14, m + 5), (x + 14, m + 5))
        if label: self.text(x + 20 * side, m + 5, label, 12, "start" if side > 0 else "end")

    def diode(self, x1, y, x2, label="", led=False, vertical=False):
        """Anode at (x1,y) -> cathode at (x2,y); vertical=True uses x1 as x and y..x2 as y-range."""
        if vertical:
            x, ya, yk = x1, y, x2
            m = (ya + yk) / 2; d = 1 if yk > ya else -1
            self.wire((x, ya), (x, m - 8 * d)); self.wire((x, m + 8 * d), (x, yk))
            self.raw(f'<polygon fill="none" stroke="#000" points="{x-9},{m-8*d} {x+9},{m-8*d} {x},{m+8*d}"/>')
            self.wire((x - 9, m + 8 * d), (x + 9, m + 8 * d))
            if led:
                for k in (0, 7):
                    self.wire((x + 11, m - 2 + k), (x + 20, m - 9 + k)); self.arrowhead(x + 11, m - 2 + k, x + 20, m - 9 + k)
            if label: self.text(x + 24, m + 4, label, 12)
            return
        m = (x1 + x2) / 2; d = 1 if x2 > x1 else -1
        self.wire((x1, y), (m - 8 * d, y)); self.wire((m + 8 * d, y), (x2, y))
        self.raw(f'<polygon fill="none" stroke="#000" points="{m-8*d},{y-9} {m-8*d},{y+9} {m+8*d},{y}"/>')
        self.wire((m + 8 * d, y - 9), (m + 8 * d, y + 9))
        if label: self.text(m, y - 14, label, 12, "middle")

    def button(self, x, y1, y2, label=""):
        m = (y1 + y2) / 2
        self.wire((x, y1), (x, m - 8)); self.wire((x, m + 8), (x, y2))
        self.dot(x, m - 8); self.dot(x, m + 8)
        self.wire((x - 12, m - 14), (x - 12, m + 14)); self.wire((x - 12, m), (x - 22, m))
        if label: self.text(x + 12, m + 4, label, 12)

    # ---- supplies and flags
    def gnd(self, x, y):
        self.wire((x, y), (x, y + 8))
        for i, w in enumerate((12, 8, 4)):
            self.wire((x - w, y + 8 + i * 4), (x + w, y + 8 + i * 4))

    def rail(self, x, y, label, col=RED):
        self.wire((x - 12, y), (x + 12, y)); self.text(x, y - 7, label, 12, "middle", "bold", col)

    def flag(self, x, y, label, direction="right", col=BLU, size=12):
        w = 18 + 7.6 * len(label)
        if direction == "right":
            pts = f"{x},{y} {x+9},{y-10} {x+w},{y-10} {x+w},{y+10} {x+9},{y+10}"; tx = x + 12
        else:
            pts = f"{x},{y} {x-9},{y-10} {x-w},{y-10} {x-w},{y+10} {x-9},{y+10}"; tx = x - w + 4
        self.raw(f'<polygon fill="#fff" stroke="{col}" points="{pts}"/>')
        self.text(tx, y + 4, label, size, col=col)

    # ---- three-terminal parts
    def pnp(self, bx, by, label=""):
        """Base at (bx,by). Returns (emitter_top, collector_bottom)."""
        self.raw(f'<circle cx="{bx+40}" cy="{by}" r="28" fill="none" stroke="#000"/>')
        self.wire((bx, by), (bx + 28, by)); self.wire((bx + 28, by - 18), (bx + 28, by + 18))
        self.wire((bx + 28, by - 9), (bx + 55, by - 32), (bx + 55, by - 52))
        self.arrowhead(bx + 55, by - 32, bx + 31, by - 11)
        self.wire((bx + 28, by + 9), (bx + 55, by + 32), (bx + 55, by + 52))
        if label: self.text(bx + 74, by + 4, label, 12)
        return (bx + 55, by - 52), (bx + 55, by + 52)

    def nmos(self, dx, dy, label=""):
        """Drain at (dx,dy) top, source at (dx,dy+90). Returns gate (left)."""
        self.wire((dx, dy), (dx, dy + 28), (dx - 15, dy + 28))
        self.wire((dx - 15, dy + 62), (dx, dy + 62), (dx, dy + 90))
        self.wire((dx, dy + 45), (dx - 15, dy + 45)); self.arrowhead(dx, dy + 45, dx - 15, dy + 45)
        self.wire((dx, dy + 45), (dx, dy + 62))
        for y0 in (dy + 22, dy + 39, dy + 56):
            self.wire((dx - 15, y0), (dx - 15, y0 + 11))
        self.wire((dx - 24, dy + 24), (dx - 24, dy + 66)); self.wire((dx - 24, dy + 45), (dx - 55, dy + 45))
        if label: self.text(dx + 8, dy + 50, label, 12)
        return (dx - 55, dy + 45)

    # ---- boxes with pins
    def ic(self, x, y, w, left, right, title, pitch=24, pinnum=True, lead=26, size=11):
        """left/right: lists of (pin_number, pin_name). Returns dict name->(x,y) pin end."""
        n = max(len(left), len(right)); h = 20 + pitch * n
        self.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" stroke="#000" stroke-width="2"/>')
        self.text(x + w / 2, y + h / 2 - 6 * title.count("\n"), title, 13, "middle", "bold")
        ends = {}
        for side, pins in (("L", left), ("R", right)):
            for i, (num, name) in enumerate(pins):
                if name is None: continue
                yy = y + 22 + pitch * i
                if side == "L":
                    self.wire((x - lead, yy), (x, yy)); self.text(x + 5, yy + 4, name, size)
                    if pinnum: self.text(x - 4, yy - 3, num, 9, "end", col=GRY)
                    ends[name] = (x - lead, yy)
                else:
                    self.wire((x + w, yy), (x + w + lead, yy)); self.text(x + w - 5, yy + 4, name, size, "end")
                    if pinnum: self.text(x + w + 4, yy - 3, num, 9, col=GRY)
                    ends[name] = (x + w + lead, yy)
        return ends

    def note(self, x, y, lines, size=13):
        for i, l in enumerate(lines): self.text(x, y + i * (size + 7), l, size)

    def save(self, path):
        body = "\n".join(self.o)
        doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" font-family="DejaVu Sans, Arial, sans-serif">'
               f'<rect width="100%" height="100%" fill="white"/>'
               f'<g stroke-width="1.8" stroke-linecap="round">{body}</g></svg>')
        open(path + ".svg", "w").write(doc)
        cairosvg.svg2png(bytestring=doc.encode(), write_to=path + ".png")
