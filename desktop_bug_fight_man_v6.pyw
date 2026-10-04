"""
Desktop Bug Arena v6 (Windows)

Bugs wander onto your screen one at a time, slowly and at random. Big ones pick
fights with smaller ones (and with each other). Fights take time, have hit
points, and the winner is not always the same one.

A SMALL MAN lives on your screen. He walks after your mouse cursor and always
FACES it, so you aim by moving the cursor around him.

  Left-click ... swing the weapon you are holding (toward the cursor)
  F9 ........... switch weapon: SWORD -> HAMMER -> FISTS
  Ctrl+Shift+Q . quit

Rules
  - A hit only counts on a bug in FRONT of the man (inside the swing arc).
    Bugs beside or behind him are not touched.
  - Sword: fast, medium damage.  Hammer: slow, heavy, stuns.  Fists: weak but quick.
  - Small bugs run from the man. Big ones attack him: the bigger the bug, the
    harder it bites. The man has an ENERGY bar. At zero he is knocked out for a
    few seconds, then gets up with half energy. Energy comes back slowly.
  - Tip: your clicks still reach the window under the cursor, so fight over an
    empty part of the desktop.

Sizes (small to big): ant, fly, ladybug, moth, caterpillar, beetle, cockroach,
spider, centipede, mantis, scorpion, frog.
"""

import ctypes
import math
import random
import threading
import time
import tkinter as tk

try:
    import winsound
except Exception:
    winsound = None

# ------------------------- SETTINGS (change these) -------------------------
SIZE = 1.0                  # 1.0 = normal, 1.5 = bigger, 0.7 = smaller
SPEED = 90                  # base walking speed in pixels per second
START_DELAY = 10            # seconds to wait before the arena starts
RUN_MINUTES = 0             # auto-quit after this many minutes (0 = never)

MAX_BUGS = 7                # most bugs on screen at once
MAX_BIG = 3                 # most big fighters (spider and up) at once
SPAWN_MIN = 6               # a new bug shows up every SPAWN_MIN..SPAWN_MAX seconds
SPAWN_MAX = 14
FIGHTING = True             # bugs attack each other and the man
SOUND = True                # small hit sounds when the man swings
MAN_SCALE = 1.0             # size of the little man
MAN_ENERGY = 100            # his starting / maximum energy
WEAPON_KEY = 0x78           # F9 switches weapon
# ---------------------------------------------------------------------------

KEY = "#010101"             # this color is made see-through
BODY = "#101010"
SHELL = "#2b2b2b"
LEG = "#161616"

user32 = ctypes.windll.user32
user32.GetParent.restype = ctypes.c_void_p
user32.GetParent.argtypes = [ctypes.c_void_p]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def cursor_pos():
    p = POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def key_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def ellipse(cx, cy, rx, ry, n=22):
    return [(cx + rx * math.cos(2 * math.pi * i / n),
             cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def play(f1, f2):
    if not SOUND or winsound is None:
        return

    def run():
        try:
            winsound.Beep(f1, 35)
            winsound.Beep(f2, 40)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


# Per kind:
#  scale  drawing size       r      body radius (pixels at scale 1)
#  hp     toughness          atk    damage per hit on another bug
#  mdmg   damage to the man (0 = never attacks him, runs from him)
#  aggr   how fight-happy (0 = never starts fights)
#  sight  how far it notices targets       rate  seconds between its attacks
#  strike distance (base px) where it rushes; rush / creep = speed multipliers
#                                                (creep 0 = sits still and waits)
#  eats   the winner carries off and eats the loser
SPECS = {
    "ant": {
        "legs": [(3, 3, 5), (0, 0, 0), (-3, -3, -5)],
        "attach_y": 1.5, "knee_y": 5, "foot_y": 8, "width": 1, "swing": 3,
        "base": 1.3, "scale": 0.9, "r": 8, "hp": 6, "atk": 1, "mdmg": 0,
        "aggr": 0.2, "sight": 60, "rate": 0.5, "weight": 3,
    },
    "fly": {
        "legs": [], "base": 2.2, "scale": 0.8, "r": 8, "hp": 4, "atk": 0.5,
        "mdmg": 0, "aggr": 0, "sight": 0, "rate": 0.5, "weight": 3,
        "walk_t": (0.4, 1.2), "pause_t": (0.6, 2.5),
    },
    "ladybug": {
        "legs": [(5, 3, 5), (0, 0, 0), (-5, -3, -5)],
        "attach_y": 5, "knee_y": 9, "foot_y": 13, "width": 1, "swing": 3,
        "base": 0.9, "scale": 1.0, "r": 10, "hp": 12, "atk": 2, "mdmg": 0,
        "aggr": 0.2, "sight": 90, "rate": 0.7, "weight": 2,
    },
    "moth": {
        "legs": [], "base": 1.0, "scale": 0.9, "r": 14, "hp": 8, "atk": 0.5,
        "mdmg": 0, "aggr": 0, "sight": 0, "rate": 0.7, "weight": 2,
    },
    "caterpillar": {
        "legs": [], "base": 0.35, "scale": 1.0, "r": 12, "hp": 14, "atk": 1,
        "mdmg": 0, "aggr": 0, "sight": 0, "rate": 0.8, "weight": 2,
        "chain": 9, "gap": 7,
    },
    "beetle": {
        "legs": [(11, 5, 9), (5, 0, 0), (-1, -5, -9)],
        "attach_y": 6, "knee_y": 14, "foot_y": 21, "width": 2, "swing": 5,
        "base": 1.0, "scale": 1.0, "r": 22, "hp": 40, "atk": 7, "mdmg": 4,
        "aggr": 0.5, "sight": 160, "rate": 0.9, "weight": 3,
        "strike": 90, "rush": 1.6, "creep": 1.0,
    },
    "cockroach": {
        "legs": [(8, 3, 6), (2, 0, -2), (-4, -4, -10)],
        "attach_y": 5, "knee_y": 12, "foot_y": 18, "width": 1, "swing": 6,
        "base": 1.8, "scale": 1.0, "r": 20, "hp": 30, "atk": 5, "mdmg": 3,
        "aggr": 0.3, "sight": 160, "rate": 0.7, "weight": 2,
        "walk_t": (1, 3), "edges": True,
        "strike": 90, "rush": 1.4, "creep": 1.0,
    },
    "spider": {
        "legs": [(8, 10, 19), (3, 6, 10), (-2, -5, -10), (-7, -11, -20)],
        "attach_y": 5, "knee_y": 15, "foot_y": 29, "width": 2, "swing": 6,
        "base": 0.8, "scale": 1.1, "r": 20, "hp": 55, "atk": 9, "mdmg": 8,
        "aggr": 0.8, "sight": 280, "rate": 0.85, "weight": 1.2, "eats": True,
        "strike": 160, "rush": 2.4, "creep": 1.0,
    },
    "centipede": {
        "legs": [], "base": 0.9, "scale": 0.8, "r": 22, "hp": 75, "atk": 12,
        "mdmg": 9, "aggr": 0.9, "sight": 330, "rate": 0.8, "weight": 0.8,
        "eats": True, "chain": 14, "gap": 11,
        "strike": 220, "rush": 5.0, "creep": 0.25,
    },
    "mantis": {
        "legs": [(0, 6, 12), (-8, -4, -12)],
        "attach_y": 3, "knee_y": 11, "foot_y": 17, "width": 1, "swing": 3,
        "base": 0.5, "scale": 1.3, "r": 24, "hp": 80, "atk": 14, "mdmg": 10,
        "aggr": 0.9, "sight": 240, "rate": 0.9, "weight": 0.8, "eats": True,
        "strike": 110, "rush": 6.0, "creep": 0,
    },
    "scorpion": {
        "legs": [(8, 6, 9), (3, 2, 4), (-2, -3, -4), (-7, -7, -9)],
        "attach_y": 6, "knee_y": 13, "foot_y": 19, "width": 2, "swing": 5,
        "base": 0.7, "scale": 1.8, "r": 28, "hp": 110, "atk": 18, "mdmg": 14,
        "aggr": 0.9, "sight": 300, "rate": 1.0, "weight": 0.6, "eats": True,
        "strike": 90, "rush": 3.5, "creep": 0.4,
    },
    "frog": {
        "legs": [], "base": 0.6, "scale": 2.2, "r": 22, "hp": 140, "atk": 12,
        "mdmg": 12, "aggr": 0.7, "sight": 260, "rate": 1.2, "weight": 0.6,
        "eats": True, "walk_t": (1, 2), "pause_t": (2, 6), "tongue": 200,
        "strike": 70, "rush": 3.0, "creep": 0,
    },
}
for _k, _s in SPECS.items():
    _s.setdefault("strike", 0)
    _s.setdefault("rush", 1.5)
    _s.setdefault("creep", 1.0)
    _s.setdefault("eats", False)
    _s["power"] = _s["hp"] * _s["atk"]
    _s["big"] = _s["hp"] >= 55

# name, range, arc (radians each side of facing), damage, swing time,
# cooldown, knockback, stun seconds
WEAPONS = [
    ("SWORD", 52, 0.95, 22, 0.28, 0.45, 14, 0.0),
    ("HAMMER", 46, 0.70, 55, 0.50, 1.10, 30, 1.3),
    ("FISTS", 32, 0.60, 9, 0.16, 0.25, 8, 0.0),
]


class Insect:
    def __init__(self, kind, w, h):
        self.kind = kind
        self.spec = SPECS[kind]
        spec = self.spec
        self.sc = SIZE * spec["scale"]
        self.w, self.h = w, h
        side = random.choice("lrtb")
        if side == "l":
            self.x, self.y = -60, random.uniform(100, h - 100)
        elif side == "r":
            self.x, self.y = w + 60, random.uniform(100, h - 100)
        elif side == "t":
            self.x, self.y = random.uniform(100, w - 100), -60
        else:
            self.x, self.y = random.uniform(100, w - 100), h + 60
        self.target = self.new_target()
        self.a = math.atan2(self.target[1] - self.y, self.target[0] - self.x)
        self.state = "walk"
        self.timer = random.uniform(*spec.get("walk_t", (3, 8)))
        self.phase = random.uniform(0, 6)
        self.t = 0.0
        self.alive = True
        self.moving = False
        self.entered = False
        self.freeze = 0.0
        self.feast = 0.0
        self.run_t = 0.0
        self.run_boost = 1.0
        self.tongue = None
        self.tongue_cd = 0.0
        self.segs = [(self.x, self.y)] * spec.get("chain", 0)
        # fighting
        self.hp = self.maxhp = float(spec["hp"])
        self.power = spec["power"]
        self.bold = spec["aggr"] * random.uniform(0.8, 1.2)
        self.hates = random.random() < spec["aggr"]      # will go after the man
        self.foe = None
        self.fight_t = 0.0
        self.atk_t = random.uniform(0.3, 1.0)
        self.first = False
        self.lunge = 0.0
        self.shake = 0.0
        self.flee_t = 0.0
        self.flee_from = (self.x, self.y)
        self.wait_t = 0.0
        self.ox = self.oy = 0.0

    @property
    def radius(self):
        return self.spec["r"] * self.sc

    def points(self):
        pts = [(self.x, self.y, self.radius)]
        for sx, sy in self.segs[3::4]:
            pts.append((sx, sy, 7 * self.sc))
        return pts

    def new_target(self):
        m = 80
        if self.spec.get("edges") and random.random() < 0.7:
            e = random.choice("lrtb")
            if e in "lr":
                return (random.choice((45, self.w - 45)), random.uniform(m, self.h - m))
            return (random.uniform(m, self.w - m), random.choice((45, self.h - 45)))
        return (random.uniform(m, self.w - m), random.uniform(m, self.h - m))

    def update(self, dt, goal=None, boost=1.0):
        self.t += dt
        self.moving = False
        if self.tongue:
            self.tongue[2] -= dt
            if self.tongue[2] <= 0:
                self.tongue = None
        if self.feast > 0:
            self.feast -= dt
            return
        if self.freeze > 0:
            self.freeze -= dt
            return

        if goal is not None:
            self.target = goal
            self.state = "walk"
            self.timer = 3
            if boost > 1:
                self.run_t = 0.8
                self.run_boost = boost
        elif self.run_t > 0:
            self.run_t -= dt
            boost = self.run_boost

        if self.state == "walk":
            speed = SPEED * self.spec["base"] * boost
            tx, ty = self.target
            desired = math.atan2(ty - self.y, tx - self.x)
            diff = angdiff(desired, self.a)
            turn = (2.3 if boost <= 1 else 2.3 + (boost - 1) * 1.4) * dt
            if self.kind == "fly":
                turn *= 3
            self.a += max(-turn, min(turn, diff))
            if abs(diff) > 1.0:
                speed *= 0.4 if boost <= 1 else 0.55
            self.x += math.cos(self.a) * speed * dt
            self.y += math.sin(self.a) * speed * dt
            self.moving = True
            self.phase += speed * dt / (9.0 * self.sc)
            if math.hypot(tx - self.x, ty - self.y) < 25 and goal is None:
                self.target = self.new_target()
            self.timer -= dt
            if self.timer <= 0 and boost <= 1 and goal is None:
                self.state = "pause"
                self.timer = random.uniform(*self.spec.get("pause_t", (0.6, 3.0)))
        else:
            self.timer -= dt
            if self.timer <= 0:
                self.state = "walk"
                self.timer = random.uniform(*self.spec.get("walk_t", (3, 8)))
                self.target = self.new_target()

        self.keep_on_screen()

    def keep_on_screen(self):
        if 20 < self.x < self.w - 20 and 20 < self.y < self.h - 20:
            self.entered = True
        if self.entered:
            self.x = clamp(self.x, 15, self.w - 15)
            self.y = clamp(self.y, 15, self.h - 15)
        if self.segs:
            self.follow()

    def follow(self):
        gap = self.spec["gap"] * self.sc
        pts = [(self.x, self.y)]
        for qx, qy in self.segs[1:]:
            px, py = pts[-1]
            d = math.hypot(px - qx, py - qy)
            if d > gap:
                qx, qy = px + (qx - px) * gap / d, py + (qy - py) * gap / d
            pts.append((qx, qy))
        self.segs = pts

    def away_goal(self, px, py):
        ang = math.atan2(self.y - py, self.x - px)
        tx, ty = self.x, self.y
        for da in (0, 0.9, -0.9, 1.8, -1.8):
            tx = clamp(self.x + math.cos(ang + da) * 500, 40, self.w - 40)
            ty = clamp(self.y + math.sin(ang + da) * 500, 40, self.h - 40)
            if math.hypot(tx - self.x, ty - self.y) > 150:
                break
        return (tx, ty)

    # ------------------------------ drawing ------------------------------
    def draw(self, c):
        if self.kind == "centipede":
            self.draw_centipede(c)
        elif self.kind == "caterpillar":
            self.draw_caterpillar(c)
        else:
            self.draw_legged(c)
        self.draw_bar(c)

    def draw_bar(self, c):
        if self.hp >= self.maxhp - 0.5 and not self.foe:
            return
        frac = clamp(self.hp / self.maxhp, 0, 1)
        w = clamp(26 * self.sc, 18, 56)
        x, y = self.x + self.ox, self.y + self.oy - self.radius - 14
        c.create_rectangle(x - w / 2 - 1, y - 3, x + w / 2 + 1, y + 3,
                           fill="#202020", outline="", tags="bug")
        col = "#4caf50" if frac > 0.5 else ("#e6b800" if frac > 0.25 else "#d33a2c")
        c.create_rectangle(x - w / 2, y - 2, x - w / 2 + w * frac, y + 2,
                           fill=col, outline="", tags="bug")

    def draw_legged(self, c):
        ca, sa = math.cos(self.a), math.sin(self.a)
        s = self.sc
        spec = self.spec
        ox, oy = self.ox, self.oy

        def T(px, py):
            px, py = px * s, py * s
            return (self.x + ox + px * ca - py * sa, self.y + oy + px * sa + py * ca)

        def poly(pts, fill):
            flat = [v for p in pts for v in T(*p)]
            c.create_polygon(flat, fill=fill, outline="", tags="bug")

        def line(pts, width, fill):
            flat = [v for p in pts for v in T(*p)]
            c.create_line(flat, width=max(1, int(width * s)), fill=fill,
                          capstyle="round", joinstyle="round", tags="bug")

        for i, (ax, kdx, fdx) in enumerate(spec["legs"]):
            for side in (1, -1):
                if self.moving:
                    off = 0.0 if (i + (side > 0)) % 2 == 0 else math.pi
                    swing = spec["swing"] * math.sin(self.phase + off)
                else:
                    swing = 1.2 * math.sin(self.t * 7 + i * 1.7 + side)
                line([(ax, side * spec["attach_y"]),
                      (ax + kdx, side * spec["knee_y"]),
                      (ax + fdx + swing, side * spec["foot_y"])],
                     spec["width"], LEG)

        getattr(self, "body_" + self.kind)(poly, line, T, c)

    def body_beetle(self, poly, line, T, c):
        poly(ellipse(-6, 0, 14, 10), BODY)
        poly(ellipse(9, 0, 8, 7), BODY)
        poly(ellipse(19, 0, 5, 5), BODY)
        line([(-19, 0), (7, 0)], 1, SHELL)  # wing seam
        wig = 3 * math.sin(self.t * 9)
        for side in (1, -1):
            line([(21, side * 2), (28, side * 6 + wig), (34, side * 5 - wig)], 1, LEG)
        for side in (1, -1):  # horn-like mandibles, open when attacking
            op = 2 + 5 * self.lunge
            line([(24, side * 1), (31, side * op)], 2, LEG)

    def body_spider(self, poly, line, T, c):
        poly(ellipse(-13, 0, 12, 9), BODY)
        poly(ellipse(4, 0, 8, 6.5), SHELL)
        poly(ellipse(-13, 0, 5, 4), SHELL)
        fang = 1.2 * math.sin(self.t * 9) + 2.5 * self.lunge
        line([(11, -2), (14, -2 + fang)], 2, LEG)
        line([(11, 2), (14, 2 - fang)], 2, LEG)
        if self.feast > 0:
            poly(ellipse(19, 0, 9, 6), "#c4c4c4")
            for sx in (14, 18, 22):
                line([(sx, -5), (sx, 5)], 1, "#8a8a8a")

    def body_ant(self, poly, line, T, c):
        col = "#2a1408"
        poly(ellipse(7, 0, 2.6, 2.3, 10), col)
        poly(ellipse(2, 0, 3, 2.4, 10), col)
        poly(ellipse(-5, 0, 5, 3.4, 12), col)
        wig = 1.2 * math.sin(self.t * 10)
        for side in (1, -1):
            line([(9, side), (12, side * 3 + wig)], 1, col)

    def body_fly(self, poly, line, T, c):
        poly(ellipse(-3, 0, 6, 3.8, 12), "#262626")
        poly(ellipse(4, 0, 3.5, 3.3, 10), "#262626")
        for side in (1, -1):
            poly(ellipse(6, side * 2, 1.5, 1.5, 8), "#8a1010")
            j = random.uniform(-1.5, 1.5) if self.moving else 0
            wy = side * (7 + j) if self.moving else side * 3.5
            poly(ellipse(-2, wy, 7, 3, 12), "#a8a8a8")
        for sx in (2, -1, -4):
            for side in (1, -1):
                line([(sx, side * 2), (sx - 1, side * 5)], 1, LEG)

    def body_moth(self, poly, line, T, c):
        flap = 0.55 + 0.45 * math.sin(self.t * 16)
        for side in (1, -1):
            poly([(3, side * 2), (-6, side * 18 * flap), (-15, side * 11 * flap),
                  (-10, side * 2)], "#a89878")
            poly([(3, side * 2), (8, side * 10 * flap), (0, side * 12 * flap)], "#8d7d5e")
            line([(8, side * 1), (16, side * 7), (22, side * 8)], 1, "#6b5b3e")
        poly(ellipse(-3, 0, 10, 3, 12), "#6b5b3e")
        poly(ellipse(8, 0, 3.5, 3, 8), "#4e422d")

    def body_ladybug(self, poly, line, T, c):
        poly(ellipse(0, 0, 10, 9, 16), "#b3201a")
        line([(-9, 0), (8, 0)], 1, BODY)
        for dx, dy in ((-3, -4.5), (-3, 4.5), (3, -3), (3, 3)):
            poly(ellipse(dx, dy, 2, 2, 8), BODY)
        poly(ellipse(10, 0, 4, 4, 10), BODY)

    def body_cockroach(self, poly, line, T, c):
        poly(ellipse(-4, 0, 15, 9, 18), "#3b1f0e")
        poly(ellipse(9, 0, 6, 6, 12), "#2a150a")
        line([(-18, 0), (5, 0)], 1, "#5a3418")
        wig = 3 * math.sin(self.t * 10)
        for side in (1, -1):
            line([(13, side * 2), (24, side * 8 + wig), (38, side * 6 - wig)], 1, LEG)

    def body_mantis(self, poly, line, T, c):
        poly(ellipse(-12, 0, 14, 4.5, 14), "#4f7a2c")
        poly(ellipse(6, 0, 11, 3, 12), "#5a8a32")
        poly(ellipse(20, 0, 4.5, 4, 10), "#6b9c3a")
        for side in (1, -1):
            poly(ellipse(22, side * 3, 1.5, 1.5, 6), BODY)
            if self.lunge > 0.3:
                line([(12, side * 2), (28, side * 9), (42, side * 3)], 2, "#3f6624")
            else:  # folded, "praying"
                line([(12, side * 2), (21, side * 6), (17, side * 2)], 2, "#3f6624")
        if self.feast > 0:
            poly(ellipse(26, 0, 6, 4), "#c4c4c4")

    def body_scorpion(self, poly, line, T, c):
        poly(ellipse(0, 0, 13, 8, 16), "#5a4020")
        poly(ellipse(10, 0, 6, 6, 12), "#4a3318")
        sway = 2.5 * math.sin(self.t * 4)
        for side in (1, -1):
            line([(10, side * 3), (19, side * 9), (27, side * 6)], 2, "#4a3318")
            poly(ellipse(29, side * 6, 5, 3, 10), "#5a4020")
        reach = 16 * self.lunge   # tail whips forward when it stings
        line([(-12, 0), (-24 + reach, sway), (-31 + reach * 1.5, -6 + sway),
              (-27 + reach * 2, -15), (-17 + reach * 2.6, -17)], 3, "#4a3318")
        poly([(-17 + reach * 2.6, -20), (-10 + reach * 2.6, -17),
              (-17 + reach * 2.6, -14)], "#2a1c0a")
        if self.feast > 0:
            poly(ellipse(32, 0, 6, 4), "#c4c4c4")

    def body_frog(self, poly, line, T, c):
        g = "#2f6b2a"
        for side in (1, -1):
            line([(-6, side * 8), (-15, side * 17), (-4, side * 21)], 4, "#26561f")
            line([(8, side * 8), (15, side * 13)], 3, "#26561f")
        poly(ellipse(0, 0, 14, 10, 18), g)
        poly(ellipse(12, 0, 8, 8, 14), "#38792f")
        for side in (1, -1):
            poly(ellipse(15, side * 6, 3.2, 3.2, 8), "#d8d8a0")
            poly(ellipse(16, side * 6, 1.4, 1.4, 6), BODY)
        if self.lunge > 0.3 and not self.tongue:  # mouth open for a bite
            poly(ellipse(19, 0, 3.5, 3, 8), "#7a1f2a")
        if self.tongue:
            tx, ty, _ = self.tongue
            hx = self.x + self.ox + math.cos(self.a) * 18 * self.sc
            hy = self.y + self.oy + math.sin(self.a) * 18 * self.sc
            c.create_line(hx, hy, tx, ty, width=3, fill="#d04060",
                          capstyle="round", tags="bug")
            c.create_oval(tx - 5, ty - 5, tx + 5, ty + 5, fill="#d04060",
                          outline="", tags="bug")

    def draw_centipede(self, c):
        s = self.sc
        n = len(self.segs)
        ox, oy = self.ox, self.oy
        for i in range(n - 1, -1, -1):
            x, y = self.segs[i][0] + ox, self.segs[i][1] + oy
            if i > 0:
                px, py = self.segs[i - 1]
                ang = (math.atan2(py - self.segs[i][1], px - self.segs[i][0])
                       if (px, py) != self.segs[i] else self.a)
            else:
                ang = self.a
            ca, sa = math.cos(ang), math.sin(ang)
            nx, ny = -sa, ca
            ll = (14 + 10 * i / n) * s
            if self.moving:
                sw = 5 * s * math.sin(self.phase * 1.5 + i * 0.9)
            else:
                sw = 1.2 * s * math.sin(self.t * 6 + i)
            for side in (1, -1):
                bx, by = x + nx * 3 * s * side, y + ny * 3 * s * side
                kx = x + nx * ll * 0.6 * side + ca * sw
                ky = y + ny * ll * 0.6 * side + sa * sw
                fx = x + nx * ll * side + ca * sw * 1.6
                fy = y + ny * ll * side + sa * sw * 1.6
                c.create_line(bx, by, kx, ky, fx, fy, width=1, fill=LEG,
                              capstyle="round", joinstyle="round", tags="bug")
            r = (6.5 if i == 0 else 5.2 - 1.5 * i / n) * s
            c.create_oval(x - r, y - r, x + r, y + r, fill=BODY, outline="", tags="bug")
            if i % 2 == 0 and i > 0:
                r2 = r * 0.55
                c.create_oval(x - r2, y - r2, x + r2, y + r2, fill=SHELL,
                              outline="", tags="bug")
        hx, hy = self.segs[0][0] + ox, self.segs[0][1] + oy
        ca, sa = math.cos(self.a), math.sin(self.a)
        for side in (1, -1):
            wig = 4 * s * math.sin(self.t * 8 + side)
            c.create_line(hx + ca * 6 * s, hy + sa * 6 * s,
                          hx + ca * 22 * s - sa * side * (8 * s + wig),
                          hy + sa * 22 * s + ca * side * (8 * s + wig),
                          hx + ca * 38 * s - sa * side * (14 * s - wig),
                          hy + sa * 38 * s + ca * side * (14 * s - wig),
                          width=1, fill=LEG, smooth=True, tags="bug")
        if self.lunge > 0.3:  # forcipules (fangs) open
            for side in (1, -1):
                c.create_line(hx + ca * 7 * s, hy + sa * 7 * s,
                              hx + ca * 14 * s - sa * side * 5 * s,
                              hy + sa * 14 * s + ca * side * 5 * s,
                              width=2, fill="#5a1a1a", tags="bug")
        if self.feast > 0:
            gx, gy = hx + ca * 14 * s, hy + sa * 14 * s
            c.create_oval(gx - 8 * s, gy - 6 * s, gx + 8 * s, gy + 6 * s,
                          fill="#c4c4c4", outline="", tags="bug")

    def draw_caterpillar(self, c):
        s = self.sc
        n = len(self.segs)
        for i in range(n - 1, -1, -1):
            x, y = self.segs[i][0] + self.ox, self.segs[i][1] + self.oy
            r = (4.6 if i else 5.4) * s
            bump = 1.2 * s * math.sin(self.phase * 1.2 - i * 0.8) if self.moving else 0
            col = "#2a4d1c" if i == 0 else ("#4f8f33" if i % 2 else "#3d7a28")
            c.create_oval(x - r, y - r - bump, x + r, y + r - bump, fill=col,
                          outline="", tags="bug")
        hx, hy = self.segs[0][0] + self.ox, self.segs[0][1] + self.oy
        ca, sa = math.cos(self.a), math.sin(self.a)
        for side in (1, -1):
            c.create_line(hx + ca * 4 * s, hy + sa * 4 * s,
                          hx + ca * 10 * s - sa * side * 4 * s,
                          hy + sa * 10 * s + ca * side * 4 * s,
                          width=1, fill=LEG, tags="bug")


class Man:
    """The little man. Follows the cursor, faces it, swings when you click."""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.a = 0.0
        self.hp = float(MAN_ENERGY)
        self.maxhp = float(MAN_ENERGY)
        self.weapon = 0
        self.swing = 0.0          # time left in the current swing
        self.swing_cd = 0.0
        self.hit_done = True
        self.hurt = 0.0
        self.ko = 0.0
        self.calm = 0.0           # time since last hit (for energy regen)
        self.phase = 0.0
        self.walking = False
        self.label_t = 0.0
        self.t = 0.0

    @property
    def active(self):
        return self.ko <= 0

    def next_weapon(self):
        self.weapon = (self.weapon + 1) % len(WEAPONS)
        self.label_t = 1.6

    def try_swing(self):
        if self.ko > 0 or self.swing > 0 or self.swing_cd > 0:
            return
        w = WEAPONS[self.weapon]
        self.swing = w[4]
        self.swing_cd = w[5]
        self.hit_done = False

    def swing_progress(self):
        w = WEAPONS[self.weapon]
        return 1 - self.swing / w[4] if self.swing > 0 else 0

    def damage(self, amount, from_x, from_y):
        self.hp -= amount
        self.hurt = 0.3
        self.calm = 0.0
        d = math.hypot(self.x - from_x, self.y - from_y) or 1
        self.x += (self.x - from_x) / d * 10
        self.y += (self.y - from_y) / d * 10
        if self.hp <= 0:
            self.hp = 0
            self.ko = 6.0
            self.swing = 0

    def update(self, dt, mx, my, w, h):
        self.t += dt
        self.hurt = max(0.0, self.hurt - dt)
        self.swing = max(0.0, self.swing - dt)
        self.swing_cd = max(0.0, self.swing_cd - dt)
        self.label_t = max(0.0, self.label_t - dt)
        self.walking = False
        if self.ko > 0:
            self.ko -= dt
            if self.ko <= 0:
                self.hp = self.maxhp * 0.5
            return
        self.calm += dt
        if self.calm > 3 and self.hp < self.maxhp:
            self.hp = min(self.maxhp, self.hp + 2.0 * dt)
        d = math.hypot(mx - self.x, my - self.y)
        if d > 8 and self.swing <= 0:
            want = math.atan2(my - self.y, mx - self.x)
            self.a += clamp(angdiff(want, self.a), -9 * dt, 9 * dt)
        if d > 70:
            sp = min(260 * MAN_SCALE, (d - 60) * 6)
            self.x += math.cos(self.a) * sp * dt
            self.y += math.sin(self.a) * sp * dt
            self.walking = True
            self.phase += sp * dt / 7
        self.x = clamp(self.x, 15, w - 15)
        self.y = clamp(self.y, 15, h - 15)

    def draw(self, c):
        s = MAN_SCALE * SIZE
        ca, sa = math.cos(self.a), math.sin(self.a)

        def T(px, py):
            px, py = px * s, py * s
            return (self.x + px * ca - py * sa, self.y + px * sa + py * ca)

        def poly(pts, fill):
            c.create_polygon([v for p in pts for v in T(*p)], fill=fill,
                             outline="", tags="bug")

        def line(pts, width, fill):
            c.create_line([v for p in pts for v in T(*p)], width=max(1, int(width * s)),
                          fill=fill, capstyle="round", joinstyle="round", tags="bug")

        # energy bar
        frac = clamp(self.hp / self.maxhp, 0, 1)
        bx, by = self.x, self.y - 26 * s
        c.create_rectangle(bx - 21, by - 4, bx + 21, by + 4, fill="#202020",
                           outline="", tags="bug")
        col = "#3fa7ff" if frac > 0.5 else ("#e6b800" if frac > 0.25 else "#d33a2c")
        c.create_rectangle(bx - 20, by - 3, bx - 20 + 40 * frac, by + 3, fill=col,
                           outline="", tags="bug")
        if self.label_t > 0:
            c.create_text(self.x, self.y + 28 * s, text=WEAPONS[self.weapon][0],
                          fill="#ffffff", font=("Segoe UI", 8, "bold"), tags="bug")

        cloth = "#c03030" if self.hurt > 0 else "#2c4a8a"
        skin = "#e0b088"
        if self.ko > 0:  # knocked out: lying flat, stars spinning
            poly(ellipse(0, 0, 11, 6), cloth)
            poly(ellipse(10, 0, 5, 5), skin)
            for i in range(3):
                ang = self.t * 4 + i * 2.1
                sx, sy = self.x + 11 * math.cos(ang), self.y - 14 + 4 * math.sin(ang)
                c.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill="#ffe27a",
                              outline="", tags="bug")
            return

        # feet
        stride = 5 * math.sin(self.phase) if self.walking else 0
        for side in (1, -1):
            poly(ellipse(stride * side, side * 4.5, 3.5, 2.4, 8), "#1a1a1a")
        # shoulders + head
        poly(ellipse(0, 0, 5.5, 10, 14), cloth)
        w = WEAPONS[self.weapon]
        p = self.swing_progress()
        arc = w[2]
        hand = (6.0, 8.0)
        if self.swing > 0:
            phi = arc - 2 * arc * (p * p * (3 - 2 * p))      # sweep right -> left
        else:
            phi = -0.2
        # arms
        line([(0, 9), hand], 3, skin)
        line([(0, -9), (5, -8)], 3, skin)
        name = w[0]
        if name == "SWORD":
            tipx = hand[0] + 38 * math.cos(phi)
            tipy = hand[1] + 38 * math.sin(phi)
            line([hand, (tipx, tipy)], 3, "#d3d7de")
            gx, gy = hand[0] + 6 * math.cos(phi), hand[1] + 6 * math.sin(phi)
            line([(gx - 4 * math.sin(phi), gy + 4 * math.cos(phi)),
                  (gx + 4 * math.sin(phi), gy - 4 * math.cos(phi))], 2, "#7a5a2a")
        elif name == "HAMMER":
            ex = hand[0] + 28 * math.cos(phi)
            ey = hand[1] + 28 * math.sin(phi)
            line([hand, (ex, ey)], 3, "#6b4a22")
            nx, ny = -math.sin(phi), math.cos(phi)
            fx, fy = math.cos(phi), math.sin(phi)
            poly([(ex - fx * 4 + nx * 7, ey - fy * 4 + ny * 7),
                  (ex + fx * 9 + nx * 7, ey + fy * 9 + ny * 7),
                  (ex + fx * 9 - nx * 7, ey + fy * 9 - ny * 7),
                  (ex - fx * 4 - nx * 7, ey - fy * 4 - ny * 7)], "#6b6f76")
        else:  # fists
            reach = 6 + 22 * math.sin(p * math.pi) if self.swing > 0 else 6
            poly(ellipse(hand[0] + reach, hand[1] - 3 * (1 - reach / 28), 3.6, 3.6, 8), skin)
            poly(ellipse(7, -8, 3.2, 3.2, 8), skin)
        poly(ellipse(1, 0, 5.2, 5.2, 12), skin)
        poly([(-5, -5), (0, -6.5), (-1.5, 0), (0, 6.5), (-5, 5)], "#3a2a1a")  # hair


class World:
    def __init__(self, canvas, w, h):
        self.c = canvas
        self.w, self.h = w, h
        self.bugs = []
        self.man = Man(w / 2, h / 2)
        self.splats = []          # (expires_at, tag)
        self.fx = []              # (expires_at, x, y, size)
        self.splat_n = 0
        self.prev_down = False
        self.prev_key = False
        self.next_spawn = time.perf_counter() + 1.5
        self.first_spawns = 2

    # ------------------------------ helpers ------------------------------
    def spawn(self, now):
        live = [b for b in self.bugs if b.alive]
        if len(live) >= MAX_BUGS:
            return
        big = sum(1 for b in live if b.spec["big"])
        kinds, weights = [], []
        for k, sp in SPECS.items():
            if sp["big"] and big >= MAX_BIG:
                continue
            kinds.append(k)
            weights.append(sp["weight"])
        kind = random.choices(kinds, weights)[0]
        self.bugs.append(Insect(kind, self.w, self.h))

    def splat(self, x, y, col, scale, now):
        self.splat_n += 1
        tag = "splat%d" % self.splat_n
        c, s = self.c, SIZE * max(0.4, scale)
        pts = []
        for i in range(14):
            ang = 2 * math.pi * i / 14
            r = random.uniform(8, 16) * s
            pts += [x + r * math.cos(ang), y + r * math.sin(ang)]
        c.create_polygon(pts, fill=col, outline="", tags=tag)
        for _ in range(random.randint(5, 9)):
            ang = random.uniform(0, 2 * math.pi)
            d = random.uniform(15, 40) * s
            r = random.uniform(1.5, 4) * s
            cx, cy = x + d * math.cos(ang), y + d * math.sin(ang)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="", tags=tag)
        self.splats.append((now + 8, tag))

    def contact(self, a, b):
        return (a.radius + b.radius) * 0.85 + 4

    def damage(self, b, dmg, now, by=None):
        """Hurt a bug. `by` is the attacking bug, or None if the man did it."""
        b.hp -= dmg
        b.shake = 0.3
        self.fx.append((now + 0.2, b.x, b.y, 6 + min(14, dmg * 0.4)))
        if b.hp > 0:
            return
        b.alive = False
        b.hp = 0
        eaten = False
        if b.foe is not None:
            b.foe.foe = None
            b.foe = None
        if by is not None:
            by.foe = None
            if by.spec["eats"]:
                by.feast = 3.5
                eaten = True
        if not eaten:
            col = "#1b2b14" if b.kind in ("caterpillar", "mantis", "frog") else "#1b1b12"
            self.splat(b.x, b.y, col, b.spec["scale"] * 0.8, now)

    def strike(self, a, b, now):
        a.atk_t = a.spec["rate"] * random.uniform(0.8, 1.3)
        a.lunge = 1.0
        if random.random() < 0.75:
            dmg = a.spec["atk"] * random.uniform(0.6, 1.4)
            if a.first:
                a.first = False
                if a.spec["creep"] == 0:
                    dmg *= 1.8      # ambushers open with a big hit
            self.damage(b, dmg, now, by=a)

    def disengage(self, a, b):
        a.foe = b.foe = None
        loser, winner = (a, b) if a.hp / a.maxhp < b.hp / b.maxhp else (b, a)
        loser.flee_t = 5.0
        loser.flee_from = (winner.x, winner.y)
        winner.freeze = 1.2

    def man_hit(self, now):
        m = self.man
        w = WEAPONS[m.weapon]
        rng, arc, dmg, _, _, kb, stun = w[1], w[2], w[3], w[4], w[5], w[6], w[7]
        hits = 0
        for b in self.bugs:
            if not b.alive:
                continue
            for px, py, pr in b.points():
                d = math.hypot(px - m.x, py - m.y)
                if d - pr > rng * MAN_SCALE:
                    continue
                if abs(angdiff(math.atan2(py - m.y, px - m.x), m.a)) > arc and d > pr:
                    continue
                # in front and within reach: it lands
                hits += 1
                self.damage(b, dmg * random.uniform(0.9, 1.1), now)
                if b.alive:
                    ang = math.atan2(b.y - m.y, b.x - m.x)
                    b.x += math.cos(ang) * kb
                    b.y += math.sin(ang) * kb
                    if b.segs:
                        b.follow()
                    if stun:
                        b.freeze = max(b.freeze, stun)
                        b.atk_t = max(b.atk_t, stun)
                break
        play(300, 180) if hits else play(120, 100)

    # ----------------------------- bug thinking -----------------------------
    def think(self, ins, dt, now, live):
        spec, kind = ins.spec, ins.kind
        m = self.man
        ins.atk_t -= dt
        ins.tongue_cd -= dt
        ins.flee_t -= dt
        ins.lunge = max(0.0, ins.lunge - dt * 4)
        ins.shake = max(0.0, ins.shake - dt)
        # visual offset: lunge toward the opponent, shudder when hurt
        ins.ox = math.cos(ins.a) * ins.lunge * 12 * ins.sc
        ins.oy = math.sin(ins.a) * ins.lunge * 12 * ins.sc
        if ins.shake > 0:
            ins.ox += random.uniform(-4, 4) * ins.shake * 3
            ins.oy += random.uniform(-4, 4) * ins.shake * 3

        # ---- in a fight with another bug: stand and trade blows ----
        if ins.foe is not None:
            f = ins.foe
            if not f.alive or f.foe is not ins:
                ins.foe = None
            else:
                ins.fight_t += dt
                ang = math.atan2(f.y - ins.y, f.x - ins.x)
                ins.a += clamp(angdiff(ang, ins.a), -8 * dt, 8 * dt)
                d = math.hypot(f.x - ins.x, f.y - ins.y)
                want = self.contact(ins, f)
                if d > want * 1.05:
                    ins.x += math.cos(ang) * 70 * dt
                    ins.y += math.sin(ang) * 70 * dt
                elif d < want * 0.7:
                    ins.x -= math.cos(ang) * 40 * dt
                    ins.y -= math.sin(ang) * 40 * dt
                ins.moving = True
                ins.phase += dt * 8
                ins.t += dt
                if ins.freeze > 0:
                    ins.freeze -= dt
                elif ins.atk_t <= 0:
                    self.strike(ins, f, now)
                if ins.alive and ins.foe is not None:
                    weak = ins.hp < 0.25 * ins.maxhp
                    if (weak and random.random() < dt * 0.6) or ins.fight_t > 25:
                        self.disengage(ins, f)
                ins.keep_on_screen()
                return

        goal, boost = None, 1.0
        man_on = m.active
        dm = math.hypot(m.x - ins.x, m.y - ins.y)

        # ---- the frog's tongue snaps up small things from a distance ----
        if (FIGHTING and spec.get("tongue") and ins.tongue_cd <= 0 and ins.feast <= 0
                and ins.freeze <= 0):
            for o in live:
                if (o is not ins and o.alive and o.maxhp <= 15 and o.foe is None
                        and math.hypot(o.x - ins.x, o.y - ins.y) < spec["tongue"]):
                    ins.a = math.atan2(o.y - ins.y, o.x - ins.x)
                    ins.tongue = [o.x, o.y, 0.3]
                    ins.tongue_cd = 1.4
                    ins.feast = 1.2
                    ins.lunge = 1.0
                    self.damage(o, 999, now, by=ins)
                    break

        # ---- run from stronger fighters (and small bugs run from the man) ----
        threat = None
        if FIGHTING:
            best = 1e9
            for o in live:
                if (o is ins or o.kind == kind or o.spec["aggr"] <= 0 or o.feast > 0
                        or o.foe is not None or o.flee_t > 0 or o.spec["creep"] == 0):
                    continue
                if ins.power >= 0.8 * o.power:
                    continue
                d = math.hypot(o.x - ins.x, o.y - ins.y)
                if d < max(70.0, o.spec["sight"] * 0.6 * SIZE) and d < best:
                    threat, best = o, d
            if man_on and spec["mdmg"] == 0 and dm < 140 and dm < best:
                threat = m

        if ins.feast > 0:
            pass
        elif threat is not None:
            goal, boost = ins.away_goal(threat.x, threat.y), 1.7
        elif ins.flee_t > 0:
            goal, boost = ins.away_goal(*ins.flee_from), 1.7
        elif FIGHTING and spec["aggr"] > 0:
            goal, boost = self.pick_fight(ins, live, m, man_on, dm, dt, now)

        # slowly heal when calm
        if ins.hp < ins.maxhp and ins.foe is None:
            ins.hp = min(ins.maxhp, ins.hp + ins.maxhp * 0.01 * dt)
        ins.update(dt, goal, boost)

    def pick_fight(self, ins, live, m, man_on, dm, dt, now):
        spec = ins.spec
        target, tman = None, False
        if (ins.hates and spec["mdmg"] > 0 and man_on
                and dm < spec["sight"] * SIZE + 120):
            target, tman = m, True
        else:
            ratio_max = 0.4 + 1.4 * ins.bold
            best_d = spec["sight"] * SIZE
            for o in live:
                if (o is ins or o.kind == ins.kind or o.foe is not None
                        or o.power > ratio_max * ins.power):
                    continue
                d = math.hypot(o.x - ins.x, o.y - ins.y)
                if d < best_d:
                    target, best_d = o, d
        if target is None:
            ins.wait_t = 0.0
            return None, 1.0

        d = math.hypot(target.x - ins.x, target.y - ins.y)
        ang = math.atan2(target.y - ins.y, target.x - ins.x)
        if tman:
            reach = ins.radius + 16
            if d <= reach:
                ins.a += clamp(angdiff(ang, ins.a), -8 * dt, 8 * dt)
                ins.freeze = max(ins.freeze, 0.05)
                if ins.atk_t <= 0:
                    ins.atk_t = spec["rate"] * random.uniform(1.0, 1.5)
                    ins.lunge = 1.0
                    m.damage(spec["mdmg"] * random.uniform(0.7, 1.3), ins.x, ins.y)
                    self.fx.append((now + 0.2, m.x, m.y, 9))
                return None, 1.0
        elif d <= self.contact(ins, target):
            ins.foe, target.foe = target, ins
            ins.fight_t = target.fight_t = 0.0
            ins.first, target.first = True, False
            ins.atk_t = random.uniform(0.2, 0.5)
            target.atk_t = random.uniform(0.4, 0.9)
            return None, 1.0

        if d < spec["strike"] * ins.sc:
            return (target.x, target.y), spec["rush"]
        if spec["creep"] == 0:    # ambusher: sit still, watch it come
            ins.wait_t += dt
            if ins.wait_t > 3.0:  # it isn't coming, so stalk it slowly
                return (target.x, target.y), 0.35
            ins.freeze = 0.1
            ins.a += clamp(angdiff(ang, ins.a), -3 * dt, 3 * dt)
            return None, 1.0
        return (target.x, target.y), spec["creep"] if spec["strike"] else 1.0

    # -------------------------------- tick --------------------------------
    def tick(self, dt):
        now = time.perf_counter()
        mx, my = cursor_pos()
        m = self.man

        k = key_down(WEAPON_KEY)
        if k and not self.prev_key:
            m.next_weapon()
        self.prev_key = k
        down = key_down(0x01)
        if down and not self.prev_down:
            m.try_swing()
        self.prev_down = down

        was_swinging = m.swing > 0
        m.update(dt, mx, my, self.w, self.h)
        if was_swinging and not m.hit_done and m.swing_progress() >= 0.5:
            m.hit_done = True
            self.man_hit(now)

        if now >= self.next_spawn:
            self.spawn(now)
            if self.first_spawns > 0:
                self.first_spawns -= 1
                self.next_spawn = now + 2.5
            else:
                self.next_spawn = now + random.uniform(SPAWN_MIN, SPAWN_MAX)

        live = [b for b in self.bugs if b.alive]
        for ins in live:
            if ins.alive:
                self.think(ins, dt, now, live)

        for item in list(self.splats):
            if now >= item[0]:
                self.c.delete(item[1])
                self.splats.remove(item)
        self.fx = [f for f in self.fx if now < f[0]]

        self.bugs = [b for b in self.bugs if b.alive]
        self.c.delete("bug")
        for ins in self.bugs:
            ins.draw(self.c)
        m.draw(self.c)
        for _, x, y, size in self.fx:   # impact sparks
            for i in range(6):
                ang = i * math.pi / 3 + now * 5
                self.c.create_line(x + math.cos(ang) * size * 0.4,
                                   y + math.sin(ang) * size * 0.4,
                                   x + math.cos(ang) * size,
                                   y + math.sin(ang) * size,
                                   width=2, fill="#ffe27a", tags="bug")


def make_overlay_style(root):
    """Layered, hidden from taskbar, never steals keyboard focus.
    The see-through color already lets clicks fall through to other apps."""
    hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
    GWL_EXSTYLE = -20
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x80000 | 0x80 | 0x08000000)


def main():
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-transparentcolor", KEY)
    root.configure(bg=KEY)
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+0+0")
    canvas = tk.Canvas(root, width=w, height=h, bg=KEY, highlightthickness=0)
    canvas.pack()
    root.withdraw()

    started = time.perf_counter()
    state = {"world": None, "last": 0.0}

    def check_quit():
        ctrl, shift, q = key_down(0x11), key_down(0x10), key_down(0x51)
        timed_out = (RUN_MINUTES > 0 and
                     time.perf_counter() - started > RUN_MINUTES * 60 + START_DELAY)
        if (ctrl and shift and q) or timed_out:
            root.destroy()
            return
        root.after(100, check_quit)

    def keep_on_top():
        if state["world"] is not None:
            root.attributes("-topmost", True)
            root.lift()
        root.after(2000, keep_on_top)

    def tick():
        now = time.perf_counter()
        dt = min(now - state["last"], 0.05)
        state["last"] = now
        state["world"].tick(dt)
        root.after(16, tick)

    def begin():
        root.deiconify()
        root.update()
        make_overlay_style(root)
        state["world"] = World(canvas, w, h)
        state["last"] = time.perf_counter()
        tick()

    root.after(int(START_DELAY * 1000), begin)
    check_quit()
    keep_on_top()
    root.mainloop()


if __name__ == "__main__":
    main()
