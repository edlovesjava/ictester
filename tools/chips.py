#!/usr/bin/env python3
"""
Chip database for the IC tester.

Each chip = pinout (names in pin order) + a behavioural model + a list of
stimulus steps.  The generator replays the steps through the model *exactly the
way the firmware engine applies them* (pins changed one at a time in chip-pin
order 1..N, then clock pins pulsed 0->1->0 `rep` times) and records the
expected outputs.  That produces the vector strings the firmware stores.

Vector alphabet (one char per chip pin):
  0 1  drive low/high             C  pulse 0->1->0 (rests low)
  L H  expect low/high            X  don't care (MCU input + pull-up)
  G    ground (low-side switch)   V  VCC (switched rail, always top-right)

Outputs that are high-Z (tri-state off, open switch) read as H because the MCU
enables its internal pull-up on every pin it reads.

Run:  python3 tools/chips.py    -> writes firmware/src/chips_db.c, docs/chips.txt
"""
import os, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ----------------------------------------------------------------- framework
class Chip:
    def __init__(self, name, desc, pinout, aliases="", bidir=False,
                 allow_const=()):
        self.name, self.desc, self.aliases = name, desc, aliases
        self.names = pinout.split()
        self.pins = len(self.names)
        assert self.pins in (14, 16, 20, 24), (name, self.pins)
        self.pin = {n: i + 1 for i, n in enumerate(self.names) if n != "NC"}
        assert len(self.pin) == len([n for n in self.names if n != "NC"]), f"dup pin name in {name}"
        g, v = self.names[self.pins // 2 - 1], self.names[-1]
        assert g in ("GND", "VSS") and v in ("VCC", "VDD"), f"{name}: non-standard power pins"
        self.bidir = bidir              # pins may switch between driven and read
        self.allow_const = set(allow_const)  # outputs allowed to never toggle
        self.steps = []                 # (changes dict, clocks list, rep)
        self.outputs = []               # pin names we read
        self.inputs = []                # pin names we drive
        self.model = None               # fn(prev, cur, st) -> None ; out(cur, st) -> dict

    # step helpers -----------------------------------------------------------
    def s(self, clocks=(), rep=1, **chg):
        self.steps.append((dict(chg), list(clocks), rep))
        return self

    def generate(self):
        st = {}
        self.init_state(st)
        level = {}                       # current level on every chip input pin
        first = True
        vecs = []
        for chg, clocks, rep in self.steps:
            want = dict(level)
            want.update(chg)
            for c in clocks:
                want[c] = 0
            driven = set(want)            # names being driven this vector
            # apply in pin order, one pin at a time (mirrors firmware)
            cur = Lv(level)
            if first:
                # pins were Hi-Z before this; their transient is unknowable, so
                # just settle every pin at once (no edges) and let async inputs act
                cur.update(want); self.update(Lv(cur), cur, st); first = False
            for pnum in range(1, self.pins + 1):
                n = self.names[pnum - 1]
                if n in want and cur.get(n) != want[n]:
                    prev = Lv(cur); cur[n] = want[n]
                    self.update(prev, cur, st)
            for _ in range(rep if clocks else 0):
                for edge in (1, 0):
                    for c in clocks:
                        prev = Lv(cur); cur[c] = edge
                        self.update(prev, cur, st)
            level = cur
            out = self.out(cur, st)
            vec = []
            for pnum in range(1, self.pins + 1):
                n = self.names[pnum - 1]
                if pnum == self.pins // 2: vec.append("G")
                elif pnum == self.pins: vec.append("V")
                elif n in clocks: vec.append("C")
                elif n in driven and n in chg or (n in driven and n not in out):
                    vec.append(str(cur[n]))
                elif n in out and out[n] is not None:
                    vec.append("H" if out[n] else "L")
                else:
                    vec.append("X")
            vecs.append((rep if clocks else 1, "".join(vec)))
            # a pin that was an output in this vector must not stay "driven"
            for n in list(level):
                if n in out and n not in chg and n not in clocks and self.bidir:
                    del level[n]
        self.vectors = vecs
        return vecs

    # overridables
    def init_state(self, st): pass
    def update(self, prev, cur, st): pass
    def out(self, cur, st): return {}


class Lv(dict):
    """Pin levels; an input not yet driven reads 0 (only during the very first vector)."""
    def __missing__(self, k): return 0


# None = unknown state (flip-flops power up random) -> rendered as X
def nq(q): return None if q is None else 1 - q
def bit(q, k): return None if q is None else (q >> k) & 1
def inc(q, m, d=1): return None if q is None else (q + d) % m


def rise(prev, cur, n): return prev.get(n, 0) == 0 and cur.get(n, 0) == 1
def fall(prev, cur, n): return prev.get(n, 0) == 1 and cur.get(n, 0) == 0


class Comb(Chip):
    """Combinational: out = fn(cur)."""
    def __init__(self, *a, fn=None, **k):
        super().__init__(*a, **k); self.fn = fn
    def out(self, cur, st): return self.fn(cur)


# ------------------------------------------------------------ gate helpers
PIN_7400 = "1A 1B 1Y 2A 2B 2Y GND 3Y 3A 3B 4Y 4A 4B VCC"
PIN_7402 = "1Y 1A 1B 2Y 2A 2B GND 3A 3B 3Y 4A 4B 4Y VCC"
PIN_7404 = "1A 1Y 2A 2Y 3A 3Y GND 4Y 4A 5Y 5A 6Y 6A VCC"
PIN_7410 = "1A 1B 2A 2B 2C 2Y GND 3Y 3A 3B 3C 1Y 1C VCC"
PIN_7420 = "1A 1B NC 1C 1D 1Y GND 2Y 2A 2B NC 2C 2D VCC"
PIN_4011 = "1A 1B 1Y 2Y 2A 2B VSS 3A 3B 3Y 4Y 4A 4B VDD"

NAND = lambda xs: 0 if all(xs) else 1
AND  = lambda xs: 1 if all(xs) else 0
NOR  = lambda xs: 0 if any(xs) else 1
OR   = lambda xs: 1 if any(xs) else 0
XOR  = lambda xs: sum(xs) & 1
XNOR = lambda xs: 1 - (sum(xs) & 1)
INV  = lambda xs: 1 - xs[0]


def gate_chip(name, desc, pinout, fn, aliases="", ins="AB", gates=4):
    ids = [str(i + 1) for i in range(gates)]
    def f(cur):
        return {g + "Y": fn([cur[g + x] for x in ins]) for g in ids}
    c = Comb(name, desc, pinout, aliases, fn=f)
    k = len(ins)
    if k <= 4:
        combos = []
        for v in range(2 ** k):   # gate g gets combo (v+g) -> neighbours differ
            combos.append({g + ins[b]: ((v + gi) >> b) & 1
                           for gi, g in enumerate(ids) for b in range(k)})
    else:                          # wide gate: all-1, walking 0, all-0
        combos = [{g + x: 1 for g in ids for x in ins}]
        for w in ins:
            combos.append({g + x: 0 if x == w else 1 for g in ids for x in ins})
        combos.append({g + x: 0 for g in ids for x in ins})
    for cmb in combos:
        c.s(**cmb)
    return c


# --------------------------------------------------------------- the chips
CHIPS = []
def add(c): CHIPS.append(c); return c

# ---- TTL gates
add(gate_chip("7400", "Quad 2-in NAND", PIN_7400, NAND, "7400 7403 7426 7437 7438 74132"))
add(gate_chip("7402", "Quad 2-in NOR", PIN_7402, NOR, "7402 7428 7433"))
add(gate_chip("7404", "Hex inverter", PIN_7404, INV, "7404 7405 7406 7414 7416 7419 4069 40106", ins="A", gates=6))
add(gate_chip("7407", "Hex buffer", PIN_7404, lambda x: x[0], "7407 7417 74365?", ins="A", gates=6))
CHIPS[-1].aliases = "7407 7417"
add(gate_chip("7408", "Quad 2-in AND", PIN_7400, AND, "7408 7409"))
add(gate_chip("7410", "Triple 3-in NAND", PIN_7410, NAND, "7410 7412", ins="ABC", gates=3))
add(gate_chip("7411", "Triple 3-in AND", PIN_7410, AND, "7411 7415", ins="ABC", gates=3))
add(gate_chip("7420", "Dual 4-in NAND", PIN_7420, NAND, "7420 7422 7440", ins="ABCD", gates=2))
add(gate_chip("7421", "Dual 4-in AND", PIN_7420, AND, "7421", ins="ABCD", gates=2))
add(gate_chip("7432", "Quad 2-in OR", PIN_7400, OR, "7432"))
add(gate_chip("7486", "Quad 2-in XOR", PIN_7400, XOR, "7486 74136"))

c = add(Comb("7430", "8-in NAND", "A B C D E F GND Y NC NC G H NC VCC", "7430",
             fn=lambda cur: {"Y": NAND([cur[x] for x in "ABCDEFGH"])}))
c.s(**{x: 1 for x in "ABCDEFGH"})
for w in "ABCDEFGH":
    c.s(**{x: (0 if x == w else 1) for x in "ABCDEFGH"})
c.s(**{x: 1 for x in "ABCDEFGH"})

# ---- tri-state buffers
def tri(name, desc, active):
    def f(cur):
        return {f"{g}Y": (cur[f"{g}A"] if cur[f"{g}OE"] == active else 1) for g in "1234"}
    c = add(Comb(name, desc, "1OE 1A 1Y 2OE 2A 2Y GND 3Y 3A 3OE 4Y 4A 4OE VCC", name, fn=f))
    for v in range(8):
        chg = {}
        for gi, g in enumerate("1234"):
            combo = (v + gi) % 4
            chg[f"{g}A"] = combo & 1
            chg[f"{g}OE"] = active if not (combo & 2) else 1 - active
        c.s(**chg)
        chg2 = {f"{g}A": 1 - chg[f"{g}A"] for g in "1234"}
        c.s(**chg2)
    return c
tri("74125", "Quad tri-state buffer, OE low", 0)
tri("74126", "Quad tri-state buffer, OE high", 1)

# ---- 7474 dual D flip-flop
class FF7474(Chip):
    def init_state(self, st): st.update(q1=None, q2=None)
    def update(self, p, c, st):
        for i in "12":
            if not c[i + "CLR"]: st["q" + i] = 0
            elif not c[i + "PRE"]: st["q" + i] = 1
            elif rise(p, c, i + "CLK"): st["q" + i] = c[i + "D"]
    def out(self, c, st):
        return {"1Q": st["q1"], "1QN": nq(st["q1"]), "2Q": st["q2"], "2QN": nq(st["q2"])}
c = add(FF7474("7474", "Dual D flip-flop, PRE/CLR", "1CLR 1D 1CLK 1PRE 1Q 1QN GND 2QN 2Q 2PRE 2CLK 2D 2CLR VCC", "7474"))
base = {"1CLR": 1, "1PRE": 1, "2CLR": 1, "2PRE": 1, "1D": 0, "2D": 0, "1CLK": 0, "2CLK": 0}
c.s(**base)
c.s(**{"1CLR": 0, "2PRE": 0}); c.s(**{"1CLR": 1, "2PRE": 1})
c.s(**{"1PRE": 0, "2CLR": 0}); c.s(**{"1PRE": 1, "2CLR": 1})
for d1, d2 in ((0, 1), (1, 0), (1, 1), (0, 0), (1, 0)):
    c.s(**{"1D": d1, "2D": d2})                              # no clock: must hold
    c.s(clocks=["1CLK", "2CLK"])
c.s(**{"1D": 0, "2D": 1}, clocks=["1CLK"])                   # clock only FF1
c.s(clocks=["2CLK"])

# ---- JK flip-flops (negative edge)
def jk(q, j, k): return q if (j, k) == (0, 0) else 0 if (j, k) == (0, 1) else 1 if (j, k) == (1, 0) else nq(q)

class JKNeg(Chip):
    has_pre = False
    def init_state(self, st): st.update(q1=None, q2=None)
    def update(self, p, c, st):
        for i in "12":
            if not c[i + "CLR"]: st["q" + i] = 0
            elif self.has_pre and not c[i + "PRE"]: st["q" + i] = 1
            elif fall(p, c, i + "CLK"): st["q" + i] = jk(st["q" + i], c[i + "J"], c[i + "K"])
    def out(self, c, st):
        return {"1Q": st["q1"], "1QN": nq(st["q1"]), "2Q": st["q2"], "2QN": nq(st["q2"])}

def jk_steps(c, pre):
    b = {"1CLR": 1, "2CLR": 1, "1J": 0, "1K": 0, "2J": 0, "2K": 0, "1CLK": 0, "2CLK": 0}
    if pre: b.update({"1PRE": 1, "2PRE": 1})
    c.s(**b)
    c.s(**{"1CLR": 0, "2CLR": 0}); c.s(**{"1CLR": 1, "2CLR": 1})
    if pre:
        c.s(**{"1PRE": 0}); c.s(**{"1PRE": 1})
        c.s(**{"1CLR": 0, "2PRE": 0}); c.s(**{"1CLR": 1, "2PRE": 1})
    seq = [(1, 0, 0, 1), (0, 0, 0, 0), (0, 1, 1, 0), (1, 1, 1, 1), (1, 1, 1, 1), (1, 0, 0, 1), (0, 1, 1, 1)]
    for j1, k1, j2, k2 in seq:
        c.s(**{"1J": j1, "1K": k1, "2J": j2, "2K": k2}, clocks=["1CLK", "2CLK"])
    c.s(**{"1J": 1, "1K": 1}, clocks=["1CLK"])

c = add(JKNeg("74107", "Dual JK flip-flop, CLR, neg edge", "1J 1QN 1Q 1K 2Q 2QN GND 2J 2CLK 2CLR 2K 1CLK 1CLR VCC", "74107"))
jk_steps(c, False)
c = add(JKNeg("74112", "Dual JK flip-flop, PRE/CLR, neg edge", "1CLK 1K 1J 1PRE 1Q 1QN 2QN GND 2Q 2PRE 2J 2K 2CLK 2CLR 1CLR VCC", "74112"))
c.has_pre = True
jk_steps(c, True)

# ---- decoders / muxes
def f138(c):
    en = c["G1"] == 1 and c["G2A"] == 0 and c["G2B"] == 0
    idx = c["A"] | c["B"] << 1 | c["C"] << 2
    return {f"Y{i}": (0 if en and i == idx else 1) for i in range(8)}
c = add(Comb("74138", "3-to-8 decoder", "A B C G2A G2B G1 Y7 GND Y6 Y5 Y4 Y3 Y2 Y1 Y0 VCC", "74138", fn=f138))
for i in range(8): c.s(A=i & 1, B=i >> 1 & 1, C=i >> 2 & 1, G1=1, G2A=0, G2B=0)
c.s(G1=0); c.s(G1=1, G2A=1); c.s(G2A=0, G2B=1); c.s(G2B=0)

def f139(c):
    o = {}
    for h in "12":
        idx = c[h + "A"] | c[h + "B"] << 1
        for i in range(4): o[f"{h}Y{i}"] = 0 if (c[h + "G"] == 0 and i == idx) else 1
    return o
c = add(Comb("74139", "Dual 2-to-4 decoder", "1G 1A 1B 1Y0 1Y1 1Y2 1Y3 GND 2Y3 2Y2 2Y1 2Y0 2B 2A 2G VCC", "74139", fn=f139))
for i in range(4):
    j = 3 - i
    c.s(**{"1G": 0, "2G": 0, "1A": i & 1, "1B": i >> 1, "2A": j & 1, "2B": j >> 1})
c.s(**{"1G": 1}); c.s(**{"1G": 0, "2G": 1})

def f151(c):
    sel = c["A"] | c["B"] << 1 | c["C"] << 2
    y = 0 if c["G"] else c[f"D{sel}"]
    return {"Y": y, "W": 1 - y}
c = add(Comb("74151", "8-to-1 mux", "D3 D2 D1 D0 Y W G GND C B A D7 D6 D5 D4 VCC", "74151", fn=f151))
for s in range(8):
    for v in (1, 0):
        d = {f"D{i}": (v if i == s else 1 - v) for i in range(8)}
        c.s(A=s & 1, B=s >> 1 & 1, C=s >> 2, G=0, **d)
c.s(G=1)

def f153(c):
    sel = c["A"] | c["B"] << 1
    return {f"{h}Y": 0 if c[h + "G"] else c[f"{h}C{sel}"] for h in "12"}
c = add(Comb("74153", "Dual 4-to-1 mux", "1G B 1C3 1C2 1C1 1C0 1Y GND 2Y 2C0 2C1 2C2 2C3 A 2G VCC", "74153", fn=f153))
for s in range(4):
    for v in (1, 0):
        d = {}
        for i in range(4):
            d[f"1C{i}"] = v if i == s else 1 - v
            d[f"2C{i}"] = 1 - d[f"1C{i}"]
        c.s(**{"1G": 0, "2G": 0, "A": s & 1, "B": s >> 1}, **d)
c.s(**{"1G": 1}); c.s(**{"1G": 0, "2G": 1})

def f157(c):
    return {f"{i}Y": 0 if c["G"] else (c[f"{i}B"] if c["S"] else c[f"{i}A"]) for i in "1234"}
c = add(Comb("74157", "Quad 2-to-1 mux", "S 1A 1B 1Y 2A 2B 2Y GND 3Y 3B 3A 4Y 4B 4A G VCC", "74157", fn=f157))
for s in (0, 1):
    for pat in (0b0101, 0b1010):
        d = {}
        for k, i in enumerate("1234"):
            d[i + "A"] = pat >> k & 1
            d[i + "B"] = 1 - d[i + "A"]
        c.s(S=s, G=0, **d)
c.s(G=1)

def f154(c):
    idx = c["A"] | c["B"] << 1 | c["C"] << 2 | c["D"] << 3
    en = c["G1"] == 0 and c["G2"] == 0
    return {f"Y{i}": 0 if en and i == idx else 1 for i in range(16)}
c = add(Comb("74154", "4-to-16 decoder (24-pin, 0.6in)",
             "Y0 Y1 Y2 Y3 Y4 Y5 Y6 Y7 Y8 Y9 Y10 GND Y11 Y12 Y13 Y14 Y15 G1 G2 D C B A VCC", "74154", fn=f154))
for i in range(16): c.s(A=i & 1, B=i >> 1 & 1, C=i >> 2 & 1, D=i >> 3, G1=0, G2=0)
c.s(G1=1); c.s(G1=0, G2=1); c.s(G2=0)

# ---- arithmetic
def f283(c):
    a = sum(c[f"A{i}"] << (i - 1) for i in range(1, 5))
    b = sum(c[f"B{i}"] << (i - 1) for i in range(1, 5))
    s = a + b + c["C0"]
    o = {f"S{i}": s >> (i - 1) & 1 for i in range(1, 5)}
    o["C4"] = s >> 4 & 1
    return o
c = add(Comb("74283", "4-bit binary full adder", "S2 B2 A2 S1 A1 B1 C0 GND C4 S4 B4 A4 S3 A3 B3 VCC", "74283", fn=f283))
rng = random.Random(283)
pairs = [(0, 0, 0), (15, 15, 1), (15, 0, 1), (0, 15, 0), (5, 10, 0), (10, 5, 1), (8, 8, 0), (7, 1, 0)]
pairs += [(rng.randrange(16), rng.randrange(16), rng.randrange(2)) for _ in range(24)]
for a, b, ci in pairs:
    c.s(C0=ci, **{f"A{i}": a >> (i - 1) & 1 for i in range(1, 5)}, **{f"B{i}": b >> (i - 1) & 1 for i in range(1, 5)})

def f85(c):
    a = sum(c[f"A{i}"] << i for i in range(4)); b = sum(c[f"B{i}"] << i for i in range(4))
    if a > b: r = (1, 0, 0)
    elif a < b: r = (0, 1, 0)
    else: r = (c["IAGTB"], c["IALTB"], c["IAEQB"])
    return {"OAGTB": r[0], "OALTB": r[1], "OAEQB": r[2]}
c = add(Comb("7485", "4-bit magnitude comparator",
             "B3 IALTB IAEQB IAGTB OAGTB OAEQB OALTB GND B0 A0 B1 A1 A2 B2 A3 VCC", "7485", fn=f85))
rng = random.Random(85)
pairs = [(0, 0), (15, 15), (15, 0), (0, 15), (8, 7), (7, 8), (1, 2), (2, 1), (4, 4), (10, 10)]
pairs += [(rng.randrange(16), rng.randrange(16)) for _ in range(20)]
for a, b in pairs:
    c.s(IAGTB=0, IALTB=0, IAEQB=1, **{f"A{i}": a >> i & 1 for i in range(4)}, **{f"B{i}": b >> i & 1 for i in range(4)})
for a, b in ((6, 6), (9, 9), (9, 3)):            # cascade inputs only matter when A == B
    for casc in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        c.s(IAGTB=casc[0], IALTB=casc[1], IAEQB=casc[2],
            **{f"A{i}": a >> i & 1 for i in range(4)}, **{f"B{i}": b >> i & 1 for i in range(4)})

# ---- 7-segment decoders
SEG = {0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg",
       6: "cdefg", 7: "abc", 8: "abcdefg", 9: "abcfg"}
TAIL = {6: "a", 9: "d"}        # tail segments vary by vendor -> don't care

def seg_out(n, active_low, lamp=False, blank=False):
    o = {}
    for s in "abcdefg":
        on = True if lamp else False if blank else (s in SEG[n])
        v = (0 if on else 1) if active_low else (1 if on else 0)
        if not lamp and not blank and s in TAIL.get(n, ""): v = None
        o[s] = v
    return o

def f47(c):
    n = c["A"] | c["B"] << 1 | c["C"] << 2 | c["D"] << 3
    if c["LT"] == 1 and c["RBI"] == 0 and n == 0: return seg_out(8, True, blank=True)
    return seg_out(n, True, lamp=(c["LT"] == 0))
c = add(Comb("7447", "BCD to 7-seg decoder/driver, OC active low",
             "B C LT BIRBO RBI D A GND e d c b a g f VCC", "7447 7446", fn=f47))
for n in range(10): c.s(A=n & 1, B=n >> 1 & 1, C=n >> 2 & 1, D=n >> 3, LT=1, RBI=1)
c.s(LT=0); c.s(LT=1)
c.s(A=0, B=0, C=0, D=0, RBI=0)       # ripple blanking: a zero is blanked
c.s(A=1)                              # a non-zero is not
c.s(RBI=1)

class F4511(Chip):
    def init_state(self, st): st["latch"] = None
    def update(self, p, c, st):
        if c.get("LE", 0) == 0:
            st["latch"] = c.get("A", 0) | c.get("B", 0) << 1 | c.get("C", 0) << 2 | c.get("D", 0) << 3
    def out(self, c, st):
        if c["LT"] == 0: return seg_out(8, False, lamp=True)
        if c["BL"] == 0: return seg_out(8, False, blank=True)
        if st["latch"] is None: return {s: None for s in "abcdefg"}
        return seg_out(st["latch"], False)
c = add(F4511("4511", "BCD to 7-seg latch/decoder, active high",
              "B C LT BL LE D A VSS e d c b a g f VDD", "4511"))
for n in range(10): c.s(A=n & 1, B=n >> 1 & 1, C=n >> 2 & 1, D=n >> 3, LT=1, BL=1, LE=0)
c.s(LT=0); c.s(LT=1, BL=0); c.s(BL=1)
c.s(A=1, B=1, C=0, D=0)          # 3
c.s(LE=1); c.s(A=0, B=0, C=0, D=1)   # latched: still 3
c.s(LE=0)                         # now 8

# ---- counters / registers
class C161(Chip):
    def init_state(self, st): st["q"] = None
    def update(self, p, c, st):
        if c["CLR"] == 0: st["q"] = 0; return
        if rise(p, c, "CLK"):
            if c["LOAD"] == 0: st["q"] = c["A"] | c["B"] << 1 | c["C"] << 2 | c["D"] << 3
            elif c["ENP"] and c["ENT"]: st["q"] = inc(st["q"], 16)
    def out(self, c, st):
        q = st["q"]
        return {"QA": bit(q, 0), "QB": bit(q, 1), "QC": bit(q, 2), "QD": bit(q, 3),
                "RCO": 0 if not c["ENT"] else None if q is None else int(q == 15)}
c = add(C161("74161", "Sync 4-bit binary counter", "CLR CLK A B C D ENP GND LOAD ENT QD QC QB QA RCO VCC", "74161 74163"))
c.s(CLR=0, LOAD=1, ENP=0, ENT=0, A=0, B=0, C=0, D=0, clocks=["CLK"])
c.s(CLR=1, ENP=1, ENT=1)
for _ in range(17): c.s(clocks=["CLK"])
c.s(LOAD=0, A=0, B=1, C=0, D=1, clocks=["CLK"])       # load 10
c.s(LOAD=1, A=1, B=0, C=1, D=0, ENP=0, clocks=["CLK"])  # hold (ENP=0)
c.s(ENP=1, ENT=0, clocks=["CLK"])                      # hold (ENT=0)
c.s(LOAD=0, A=1, B=1, C=1, D=1, ENT=1, clocks=["CLK"])  # load 15 -> RCO
c.s(ENT=0)
c.s(LOAD=1, ENT=1, clocks=["CLK"])                      # wrap to 0

class C193(Chip):
    def init_state(self, st): st["q"] = None
    def update(self, p, c, st):
        if c["CLR"]: st["q"] = 0; return
        if c["LOAD"] == 0: st["q"] = c["A"] | c["B"] << 1 | c["C"] << 2 | c["D"] << 3; return
        if rise(p, c, "UP") and c["DOWN"]: st["q"] = inc(st["q"], 16)
        if rise(p, c, "DOWN") and c["UP"]: st["q"] = inc(st["q"], 16, -1)
    def out(self, c, st):
        q = st["q"]
        if q is None: return {k: None for k in ("QA", "QB", "QC", "QD", "CO", "BO")}
        return {"QA": bit(q, 0), "QB": bit(q, 1), "QC": bit(q, 2), "QD": bit(q, 3),
                "CO": 0 if (q == 15 and c["UP"] == 0) else 1,
                "BO": 0 if (q == 0 and c["DOWN"] == 0) else 1}
c = add(C193("74193", "Sync up/down 4-bit counter", "B QB QA DOWN UP QC QD GND D C LOAD CO BO CLR A VCC", "74193"))
c.s(CLR=1, LOAD=1, UP=0, DOWN=1, A=0, B=0, C=0, D=0)
c.s(CLR=0)
for _ in range(17): c.s(clocks=["UP"])
c.s(DOWN=0)                                  # DOWN low first (no count)...
c.s(UP=1)                                    # ...then UP high (no count)
for _ in range(17): c.s(clocks=["DOWN"])
c.s(LOAD=0, A=0, B=1, C=1, D=0)              # async load 6
c.s(LOAD=1)
c.s(clocks=["DOWN"])
c.s(LOAD=0, A=1, B=0, C=0, D=1)              # async load 9
c.s(LOAD=1)
c.s(CLR=1); c.s(CLR=0)

class C175(Chip):
    def init_state(self, st): st["q"] = [None] * 4
    def update(self, p, c, st):
        if c["CLR"] == 0: st["q"] = [0] * 4
        elif rise(p, c, "CLK"): st["q"] = [c[f"{i}D"] for i in "1234"]
    def out(self, c, st):
        o = {}
        for k, i in enumerate("1234"):
            o[i + "Q"] = st["q"][k]; o[i + "QN"] = nq(st["q"][k])
        return o
c = add(C175("74175", "Quad D flip-flop, CLR", "CLR 1Q 1QN 1D 2D 2QN 2Q GND CLK 3Q 3QN 3D 4D 4QN 4Q VCC", "74175"))
c.s(CLR=0, CLK=0, **{f"{i}D": 1 for i in "1234"}); c.s(CLR=1)
for pat in (0b0101, 0b1010, 0b1111, 0b0000, 0b0011):
    d = {f"{i}D": pat >> k & 1 for k, i in enumerate("1234")}
    c.s(**d); c.s(clocks=["CLK"])

class C164(Chip):
    def init_state(self, st): st["r"] = [None] * 8
    def update(self, p, c, st):
        if c["CLR"] == 0: st["r"] = [0] * 8
        elif rise(p, c, "CLK"): st["r"] = [c["A"] & c["B"]] + st["r"][:7]
    def out(self, c, st): return {f"Q{'ABCDEFGH'[i]}": st["r"][i] for i in range(8)}
c = add(C164("74164", "8-bit SIPO shift register", "A B QA QB QC QD GND CLK CLR QE QF QG QH VCC", "74164"))
c.s(CLR=0, A=1, B=1, CLK=0); c.s(CLR=1)
for b_ in (1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0):
    c.s(A=b_, B=1, clocks=["CLK"])
c.s(A=1, B=0, clocks=["CLK"]); c.s(A=0, B=1, clocks=["CLK"])
c.s(CLR=0); c.s(CLR=1)

class C595(Chip):
    def init_state(self, st): st.update(r=[None] * 8, l=[None] * 8)
    def update(self, p, c, st):
        if c["SRCLR"] == 0: st["r"] = [0] * 8
        elif rise(p, c, "SRCLK"): st["r"] = [c["SER"]] + st["r"][:7]
        if rise(p, c, "RCLK"): st["l"] = list(st["r"])
    def out(self, c, st):
        o = {f"Q{'ABCDEFGH'[i]}": (st["l"][i] if c["OE"] == 0 else 1) for i in range(8)}
        o["QHS"] = st["r"][7]
        return o
c = add(C595("74595", "8-bit shift register + output latch", "QB QC QD QE QF QG QH GND QHS SRCLR SRCLK RCLK OE SER QA VCC", "74595"))
c.s(SRCLR=0, OE=0, SER=0, SRCLK=0, clocks=["RCLK"]); c.s(SRCLR=1)
for b_ in (1, 0, 1, 1, 0, 0, 1, 0):
    c.s(SER=b_, clocks=["SRCLK"])
c.s(clocks=["RCLK"])
c.s(OE=1); c.s(OE=0)
for b_ in (0, 1, 0, 0, 1, 1, 0, 1):
    c.s(SER=b_, clocks=["SRCLK"])
c.s(clocks=["RCLK"])

class Oct(Chip):
    """74273 / 74374 / 74373 share a pinout (pin1 = CLR or OE, pin11 = CLK or LE)."""
    kind = "273"
    def init_state(self, st): st["q"] = [None] * 8
    def update(self, p, c, st):
        d = [c[f"D{i}"] for i in range(1, 9)]
        if self.kind == "273":
            if c["CLR"] == 0: st["q"] = [0] * 8
            elif rise(p, c, "CLK"): st["q"] = d
        elif self.kind == "374":
            if rise(p, c, "CLK"): st["q"] = d
        else:
            if c["LE"]: st["q"] = d
    def out(self, c, st):
        z = self.kind != "273" and c["OE"] == 1
        return {f"Q{i}": (1 if z else st["q"][i - 1]) for i in range(1, 9)}
OCT = "{p1} Q1 D1 D2 Q2 Q3 D3 D4 Q4 GND {p11} Q5 D5 D6 Q6 Q7 D7 D8 Q8 VCC"
def dat(v): return {f"D{i}": v >> (i - 1) & 1 for i in range(1, 9)}
c = add(Oct("74273", "Octal D flip-flop, CLR", OCT.format(p1="CLR", p11="CLK"), "74273"))
c.s(CLR=0, CLK=0, **dat(0xFF)); c.s(CLR=1)
for v in (0x55, 0xAA, 0xFF, 0x0F, 0x00):
    c.s(**dat(v)); c.s(clocks=["CLK"])
c.s(CLR=0); c.s(CLR=1)
c = add(Oct("74374", "Octal D flip-flop, tri-state", OCT.format(p1="OE", p11="CLK"), "74374 74574?"))
c.kind = "374"; c.aliases = "74374"
c.s(OE=0, **dat(0x00), clocks=["CLK"])
for v in (0x55, 0xAA, 0xFF, 0x3C):
    c.s(**dat(v)); c.s(clocks=["CLK"])
c.s(OE=1); c.s(OE=0, **dat(0x00), clocks=["CLK"])
c = add(Oct("74373", "Octal transparent latch, tri-state", OCT.format(p1="OE", p11="LE"), "74373"))
c.kind = "373"
c.s(OE=0, LE=1, **dat(0x00))
for v in (0x55, 0xAA, 0xFF):
    c.s(**dat(v))
c.s(LE=0); c.s(**dat(0x00)); c.s(**dat(0x55))    # latched: holds 0xFF
c.s(LE=1)
c.s(OE=1); c.s(OE=0)

# ---- bus buffers / transceivers
def f244(c):
    o = {}
    for h in "12":
        for i in range(1, 5):
            o[f"{h}Y{i}"] = c[f"{h}A{i}"] if c[f"{h}OE"] == 0 else 1
    return o
c = add(Comb("74244", "Octal tri-state buffer",
             "1OE 1A1 2Y4 1A2 2Y3 1A3 2Y2 1A4 2Y1 GND 2A1 1Y4 2A2 1Y3 2A3 1Y2 2A4 1Y1 2OE VCC", "74244 74541?", fn=f244))
c.aliases = "74244"
def a244(v): return {f"{h}A{i}": v >> ((0 if h == "1" else 4) + i - 1) & 1 for h in "12" for i in range(1, 5)}
for v in (0x00, 0xFF, 0x55, 0xAA, 0x0F, 0xF0):
    c.s(**{"1OE": 0, "2OE": 0}, **a244(v))
c.s(**{"1OE": 1}, **a244(0)); c.s(**{"1OE": 0, "2OE": 1}); c.s(**{"2OE": 0})

class T245(Chip):
    def out(self, c, st):
        o = {}
        for i in range(1, 9):
            if c["OE"] == 1:
                o[f"A{i}"] = o[f"B{i}"] = 1
            elif c["DIR"] == 1: o[f"B{i}"] = c[f"A{i}"]
            else: o[f"A{i}"] = c[f"B{i}"]
        return o
c = add(T245("74245", "Octal bus transceiver", "DIR A1 A2 A3 A4 A5 A6 A7 A8 GND B8 B7 B6 B5 B4 B3 B2 B1 OE VCC", "74245", bidir=True))
A = lambda v: {f"A{i}": v >> (i - 1) & 1 for i in range(1, 9)}
B = lambda v: {f"B{i}": v >> (i - 1) & 1 for i in range(1, 9)}
c.s(OE=1, DIR=1, **A(0))
for v in (0x00, 0xFF, 0x55, 0xAA): c.s(OE=0, **A(v))
c.s(OE=1)                                   # isolate before turning around
c.s(DIR=0, **B(0))                          # now drive B side (A pins released)
for v in (0x00, 0xFF, 0x55, 0xAA): c.s(OE=0, **B(v))
c.s(OE=1)

# ---- CMOS 4000 gates (4011 pinout)
add(gate_chip("4001", "Quad 2-in NOR (CMOS)", PIN_4011, NOR, "4001 4025?"))
CHIPS[-1].aliases = "4001"
add(gate_chip("4011", "Quad 2-in NAND (CMOS)", PIN_4011, NAND, "4011 4093"))
add(gate_chip("4070", "Quad 2-in XOR (CMOS)", PIN_4011, XOR, "4070 4030"))
add(gate_chip("4071", "Quad 2-in OR (CMOS)", PIN_4011, OR, "4071"))
add(gate_chip("4077", "Quad 2-in XNOR (CMOS)", PIN_4011, XNOR, "4077"))
add(gate_chip("4081", "Quad 2-in AND (CMOS)", PIN_4011, AND, "4081"))

class D4013(Chip):
    def init_state(self, st): st.update(q1=None, q2=None)
    def update(self, p, c, st):
        for i in "12":
            if c["R" + i]: st["q" + i] = 0
            elif c["S" + i]: st["q" + i] = 1
            elif rise(p, c, "CLK" + i): st["q" + i] = c["D" + i]
    def out(self, c, st):
        return {"Q1": st["q1"], "QN1": nq(st["q1"]), "Q2": st["q2"], "QN2": nq(st["q2"])}
c = add(D4013("4013", "Dual D flip-flop, set/reset (CMOS)", "Q1 QN1 CLK1 R1 D1 S1 VSS S2 D2 R2 CLK2 QN2 Q2 VDD", "4013"))
c.s(R1=1, S1=0, R2=0, S2=1, D1=0, D2=0, CLK1=0, CLK2=0)
c.s(R1=0, S2=0); c.s(S1=1, R2=1); c.s(S1=0, R2=0)
for d1, d2 in ((0, 1), (1, 0), (1, 1), (0, 0), (1, 0)):
    c.s(D1=d1, D2=d2); c.s(clocks=["CLK1", "CLK2"])
c.s(D1=0, D2=1, clocks=["CLK1"]); c.s(clocks=["CLK2"])

class JK4027(Chip):
    def init_state(self, st): st.update(q1=None, q2=None)
    def update(self, p, c, st):
        for i in "12":
            if c["R" + i]: st["q" + i] = 0
            elif c["S" + i]: st["q" + i] = 1
            elif rise(p, c, "CLK" + i): st["q" + i] = jk(st["q" + i], c["J" + i], c["K" + i])
    def out(self, c, st):
        return {"Q1": st["q1"], "QN1": nq(st["q1"]), "Q2": st["q2"], "QN2": nq(st["q2"])}
c = add(JK4027("4027", "Dual JK flip-flop, set/reset (CMOS)", "Q2 QN2 CLK2 R2 K2 J2 S2 VSS S1 J1 K1 R1 CLK1 QN1 Q1 VDD", "4027"))
c.s(R1=1, R2=1, S1=0, S2=0, J1=0, K1=0, J2=0, K2=0, CLK1=0, CLK2=0)
c.s(R1=0, R2=0); c.s(S1=1); c.s(S1=0, S2=1); c.s(S2=0)
for j1, k1, j2, k2 in [(1, 0, 0, 1), (0, 0, 0, 0), (0, 1, 1, 0), (1, 1, 1, 1), (1, 1, 1, 1), (1, 0, 0, 1)]:
    c.s(J1=j1, K1=k1, J2=j2, K2=k2, clocks=["CLK1", "CLK2"])

class C4017(Chip):
    def init_state(self, st): st["q"] = None
    def update(self, p, c, st):
        if c["RST"]: st["q"] = 0
        elif rise(p, c, "CLK") and c["INH"] == 0: st["q"] = inc(st["q"], 10)
    def out(self, c, st):
        if st["q"] is None: return {k: None for k in [f"Q{i}" for i in range(10)] + ["CO"]}
        o = {f"Q{i}": 1 if st["q"] == i else 0 for i in range(10)}
        o["CO"] = 1 if st["q"] < 5 else 0
        return o
c = add(C4017("4017", "Decade counter/divider (CMOS)", "Q5 Q1 Q0 Q2 Q6 Q7 Q3 VSS Q8 Q4 Q9 CO INH CLK RST VDD", "4017"))
c.s(RST=1, INH=0, CLK=0); c.s(RST=0)
for _ in range(12): c.s(clocks=["CLK"])
c.s(INH=1, clocks=["CLK"])          # inhibited: no count
c.s(INH=0); c.s(RST=1); c.s(RST=0)

class Ripple(Chip):
    bits = 12
    taps = {}
    def init_state(self, st): st["q"] = None
    def update(self, p, c, st):
        if c["RST"]: st["q"] = 0
        elif fall(p, c, "CLK"): st["q"] = inc(st["q"], 1 << self.bits)
    def out(self, c, st): return {n: bit(st["q"], k - 1) for n, k in self.taps.items()}

def ripple_steps(c, total):
    c.s(RST=1, CLK=0); c.s(RST=0)
    for _ in range(9): c.s(clocks=["CLK"])
    n = 9
    rng = random.Random(total)
    while n < total + 20:
        r = rng.choice((255, 255, 200, 131, 77))
        c.s(clocks=["CLK"], rep=r); n += r
    c.s(RST=1); c.s(RST=0)

c = add(Ripple("4040", "12-stage ripple counter (CMOS)", "Q12 Q6 Q5 Q7 Q4 Q3 Q2 VSS Q1 CLK RST Q9 Q8 Q10 Q11 VDD", "4040"))
c.bits = 12; c.taps = {f"Q{i}": i for i in range(1, 13)}
ripple_steps(c, 4096)
c = add(Ripple("4020", "14-stage ripple counter (CMOS)", "Q12 Q13 Q14 Q6 Q5 Q7 Q4 VSS Q1 CLK RST Q9 Q8 Q10 Q11 VDD", "4020"))
c.bits = 14; c.taps = {f"Q{i}": i for i in [1] + list(range(4, 15))}
ripple_steps(c, 16384)

# ---- analog switches (read through the MCU pull-up)
def f4051(c):
    sel = c["A"] | c["B"] << 1 | c["C"] << 2
    return {f"CH{i}": (c["COM"] if (c["INH"] == 0 and i == sel) else 1) for i in range(8)}
c = add(Comb("4051", "8-ch analog mux (VEE tied low by tester)",
             "CH4 CH6 COM CH7 CH5 INH VEE VSS C B A CH3 CH0 CH1 CH2 VDD", "4051", fn=f4051))
for s in range(8): c.s(VEE=0, INH=0, COM=0, A=s & 1, B=s >> 1 & 1, C=s >> 2)
c.s(COM=1); c.s(COM=0, INH=1); c.s(INH=0)

class Sw4066(Chip):
    def out(self, c, st):
        o = {}
        for i in "1234":
            a, b = c.get(f"A{i}"), c.get(f"B{i}")
            closed = c[f"C{i}"] == 1
            if a is not None and f"B{i}" not in self.drv: o[f"B{i}"] = a if closed else 1
            if b is not None and f"A{i}" not in self.drv: o[f"A{i}"] = b if closed else 1
        return o
c = add(Sw4066("4066", "Quad bilateral switch (CMOS)", "A1 B1 B2 A2 C2 C3 VSS A3 B3 B4 A4 C4 C1 VDD", "4066 4016", bidir=True))
c.drv = {f"A{i}" for i in "1234"}
for pat in (0b0101, 0b1010):
    ctl = {f"C{i}": pat >> k & 1 for k, i in enumerate("1234")}
    c.s(**ctl, **{f"A{i}": 0 for i in "1234"})
    c.s(**{f"A{i}": 1 for i in "1234"})
    c.s(**{f"A{i}": 0 for i in "1234"})


# ---------------------------------------------------------- 4066 bidir fixup
# Generic bidir handling in Chip.generate() deletes read pins from `level`; the
# 4066 model only ever drives A pins, so nothing else to do.


# --------------------------------------------------------------- verification
def verify(c):
    errs = []
    n = c.pins
    seen_drive, seen_out = {}, {}
    for idx, (rep, v) in enumerate(c.vectors):
        if len(v) != n: errs.append(f"vec {idx} len {len(v)}")
        if v[n // 2 - 1] != "G" or v[n - 1] != "V": errs.append(f"vec {idx} power pos")
        if not 1 <= rep <= 255: errs.append(f"vec {idx} rep {rep}")
        for p, ch in enumerate(v, 1):
            if ch not in "01CLHXGV": errs.append(f"vec {idx} bad char {ch}")
            name = c.names[p - 1]
            if ch in "01C": seen_drive.setdefault(name, set()).add(ch)
            if ch in "LH": seen_out.setdefault(name, set()).add(ch)
    for name in c.names:
        if name in ("NC", "GND", "VSS", "VCC", "VDD"): continue
        d, o = seen_drive.get(name), seen_out.get(name)
        if d and o and not c.bidir:
            errs.append(f"pin {name} both driven and read")
        if not d and not o:
            # pins that are always X are OK only for pass-through status pins
            if name not in ("BIRBO",): errs.append(f"pin {name} never used")
        if d and not ({"0", "1"} <= d or "C" in d) and name not in ("VEE",):
            errs.append(f"input {name} never toggled: {sorted(d)}")
        if o and o != {"L", "H"} and name not in c.allow_const:
            errs.append(f"output {name} only seen {sorted(o)}")
    # a CMOS input must never float: every non-output, non-NC pin must be driven every vector
    inputs = [nm for nm in seen_drive if nm not in seen_out]
    for idx, (rep, v) in enumerate(c.vectors):
        for nm in inputs:
            if v[c.pin[nm] - 1] not in "01C":
                errs.append(f"vec {idx}: input {nm} not driven"); break
    return errs


def emit(chips):
    total = 0
    lines = ['/* GENERATED by tools/chips.py -- do not edit. */',
             '#include "chips_db.h"', '']
    for i, c in enumerate(chips):
        data = []
        for rep, v in c.vectors:
            data.append(f"{rep}," + ",".join(f"'{ch}'" for ch in v))
        total += len(c.vectors) * (c.pins + 1)
        lines.append(f"static const char n{i}[] PROGMEM = \"{c.name}\";")
        lines.append(f"static const char a{i}[] PROGMEM = \"{c.aliases}\";")
        lines.append(f"static const char d{i}[] PROGMEM = \"{c.desc}\";")
        lines.append(f"static const uint8_t v{i}[] PROGMEM = {{")
        for d in data: lines.append("  " + d + ",")
        lines.append("};")
    lines.append("")
    lines.append("const chip_t chip_db[] PROGMEM = {")
    for i, c in enumerate(chips):
        lines.append(f"  {{n{i}, a{i}, d{i}, v{i}, {len(c.vectors)}, {c.pins}}},")
    lines.append("};")
    lines.append(f"const uint8_t chip_db_count = {len(chips)};")
    return "\n".join(lines) + "\n", total


def main():
    bad = 0
    for c in CHIPS:
        c.generate()
        e = verify(c)
        if e:
            bad += 1
            print(f"[FAIL] {c.name}: " + "; ".join(e[:6]))
    names = [c.name for c in CHIPS]
    assert len(names) == len(set(names)), "duplicate chip names"
    src, total = emit(CHIPS)
    with open(os.path.join(ROOT, "firmware/src/chips_db.c"), "w") as f: f.write(src)
    with open(os.path.join(ROOT, "docs/chips.txt"), "w") as f:
        f.write("# Generated by tools/chips.py. Format: rep:vector  (pin 1 first)\n")
        f.write("# 0/1 drive  C clock pulse  L/H expect  X don't care  G gnd  V vcc\n\n")
        for c in CHIPS:
            f.write(f"== {c.name}  ({c.pins}-pin)  {c.desc}\n   aliases: {c.aliases}\n")
            f.write("   pins: " + " ".join(f"{i+1}:{n}" for i, n in enumerate(c.names)) + "\n")
            for rep, v in c.vectors: f.write(f"   {rep:3d}:{v}\n")
            f.write("\n")
    print(f"{len(CHIPS)} chips, {sum(len(c.vectors) for c in CHIPS)} vectors, {total} bytes of vector data, {bad} failing checks")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
