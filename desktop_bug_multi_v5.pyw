"""
Desktop Bug Prank v5 (Windows)

Lots of small prey, a few rare predators, all walking on top of your real screen.

PREY       beetle, ant (colony stream), fly (buzzes, lands), moth (circles your
           cursor), caterpillar (slow), ladybug (follows your cursor if you stay
           still), cockroach (runs along the screen edges)
PREDATORS  spider (chases, sometimes drops from the top on a web thread),
           house centipede (creeps slowly, then rushes), praying mantis (waits,
           then strikes), scorpion, frog (flicks its tongue)

THINGS YOU CAN DO
  - Left-click a bug to squash it (with a squash sound).
  - Double-click anywhere: big SLAM splat that kills everything close by.
  - Hold F8: all the prey swarm to your cursor.
  - Click an egg to crush it.
  - Bugs run from the mouse (sometimes they freeze, so you can hit them).

THINGS BUGS DO
  - Walk along the title bar of your active window and along the taskbar.
  - Leave tiny footprints. Beetles lay eggs that hatch.
  - Every few minutes a bug crosses the whole screen and leaves.

HOW TO RUN   Double-click this file (needs Python from python.org).
HOW TO STOP  Ctrl + Shift + Q at any time.
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
# How many of each. Prey are many, predators are rare. Set 0 to remove a kind.
COUNTS = {
    "beetle": 6, "ant": 8, "fly": 4, "moth": 1, "caterpillar": 2,
    "ladybug": 2, "cockroach": 2,
    "spider": 1, "centipede": 1, "mantis": 1, "scorpion": 1, "frog": 1,
}
SIZE = 1.0                  # 1.0 = normal, 1.5 = bigger, 0.7 = smaller
SPEED = 90                  # base walking speed in pixels per second
START_DELAY = 10            # seconds to wait before the bugs appear
RUN_MINUTES = 0             # auto-quit after this many minutes (0 = never)

HUNTING = True              # predators chase and eat other bugs
FLEE_FROM_MOUSE = True      # bugs run away when the mouse gets close
FREEZE_CHANCE = 0.35        # chance a bug freezes (easy to hit) instead of running
CLICK_TO_SQUASH = True      # left-click on a bug to squash it
SOUND = True                # squash sounds
RESPAWN_SECONDS = 25        # a squashed or eaten bug returns after this long
SPLAT_SECONDS = 8           # how long a splat stays on screen
PERCH = True                # walk on the active window's title bar / the taskbar
FOOTPRINTS = True           # tiny footprints that fade
EGGS = True                 # beetles lay eggs that hatch
CROSS_MINUTES = 2           # a bug crosses the screen this often (0 = never)
SWARM_KEY = 0x77            # hold this key (F8) to make the prey swarm the cursor
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
user32.GetForegroundWindow.restype = ctypes.c_void_p

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]


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


def play(f1, f2):
    if not SOUND or winsound is None:
        return

    def run():
        try:
            winsound.Beep(f1, 45)
            winsound.Beep(f2, 55)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def perch_lines(w, h):
    """Lines bugs like to walk on: the taskbar and the active window's title bar."""
    lines = [(60, h - 22, w - 60, h - 22)]
    try:
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            r = RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(r)):
                if r.right - r.left > 200 and r.bottom - r.top > 100:
                    y = clamp(r.top + 14, 20, h - 60)
                    x1, x2 = max(r.left + 140, 30), min(r.right - 170, w - 30)
                    if x2 > x1 + 50:
                        lines.append((x1, y, x2, y))
    except Exception:
        pass
    return lines


PERCHES = []

# Per kind: legs (attach_x, knee_dx, foot_dx), base speed, click size, and for
# predators: prey, sight (see prey), strike (rush inside this), rush and creep
# speed multipliers (creep 0 = sit still and wait), catch (grab distance),
# scare (prey run away inside this; 0 = prey can't see it coming).
SPECS = {
    "beetle": {
        "legs": [(11, 5, 9), (5, 0, 0), (-1, -5, -9)],
        "attach_y": 6, "knee_y": 14, "foot_y": 21, "width": 2, "swing": 5,
        "base": 1.0, "hit": 30,
    },
    "ant": {
        "legs": [(3, 3, 5), (0, 0, 0), (-3, -3, -5)],
        "attach_y": 1.5, "knee_y": 5, "foot_y": 8, "width": 1, "swing": 3,
        "base": 1.3, "hit": 14,
    },
    "fly": {
        "legs": [], "base": 2.2, "hit": 16,
        "walk_t": (0.4, 1.2), "pause_t": (0.6, 2.5),
    },
    "moth": {"legs": [], "base": 1.0, "hit": 22},
    "caterpillar": {"legs": [], "base": 0.35, "hit": 20, "chain": 9, "gap": 7},
    "ladybug": {
        "legs": [(5, 3, 5), (0, 0, 0), (-5, -3, -5)],
        "attach_y": 5, "knee_y": 9, "foot_y": 13, "width": 1, "swing": 3,
        "base": 0.9, "hit": 18,
    },
    "cockroach": {
        "legs": [(8, 3, 6), (2, 0, -2), (-4, -4, -10)],
        "attach_y": 5, "knee_y": 12, "foot_y": 18, "width": 1, "swing": 6,
        "base": 1.8, "hit": 28, "walk_t": (1, 3), "edges": True,
    },
    "spider": {
        "legs": [(8, 10, 19), (3, 6, 10), (-2, -5, -10), (-7, -11, -20)],
        "attach_y": 5, "knee_y": 15, "foot_y": 29, "width": 2, "swing": 6,
        "base": 0.8, "hit": 38,
        "prey": {"beetle", "ant", "fly"}, "sight": 380, "strike": 380,
        "rush": 2.2, "creep": 1.0, "catch": 32, "scare": 200,
    },
    "centipede": {
        "legs": [], "base": 0.9, "hit": 34, "chain": 14, "gap": 11,
        "prey": {"spider", "beetle", "cockroach", "caterpillar", "ant"},
        "sight": 650, "strike": 230, "rush": 5.5, "creep": 0.25,
        "catch": 38, "scare": 230,
    },
    "mantis": {
        "legs": [(0, 6, 12), (-8, -4, -12)],
        "attach_y": 3, "knee_y": 11, "foot_y": 17, "width": 1, "swing": 3,
        "base": 0.5, "hit": 30,
        "prey": {"fly", "moth", "ladybug", "ant", "beetle"}, "sight": 300,
        "strike": 140, "rush": 6.0, "creep": 0, "catch": 36, "scare": 0,
    },
    "scorpion": {
        "legs": [(8, 6, 9), (3, 2, 4), (-2, -3, -4), (-7, -7, -9)],
        "attach_y": 6, "knee_y": 13, "foot_y": 19, "width": 2, "swing": 5,
        "base": 0.7, "hit": 34,
        "prey": {"beetle", "cockroach", "caterpillar", "ant", "ladybug"},
        "sight": 350, "strike": 130, "rush": 4.0, "creep": 0.4,
        "catch": 36, "scare": 130,
    },
    "frog": {
        "legs": [], "base": 0.6, "hit": 36,
        "walk_t": (1, 2), "pause_t": (2, 6),
        "prey": {"fly", "moth", "ant", "ladybug"}, "sight": 200, "strike": 0,
        "rush": 1.0, "creep": 0, "catch": 190, "scare": 0,
        "tongue": True, "feast": 1.8,
    },
}
for _s in SPECS.values():
    _s.setdefault("prey", set())
    _s.setdefault("scare", 0)
    _s.setdefault("creep", 1.0)

PRINT_KINDS = {"beetle", "cockroach", "scorpion", "spider", "ladybug"}


class Insect:
    def __init__(self, kind, w, h, pos=None):
        self.kind = kind
        self.spec = SPECS[kind]
        self.w, self.h = w, h
        side = random.choice("lrtb")
        if side == "l":
            self.x, self.y = -40, random.uniform(100, h - 100)
        elif side == "r":
            self.x, self.y = w + 40, random.uniform(100, h - 100)
        elif side == "t":
            self.x, self.y = random.uniform(100, w - 100), -40
        else:
            self.x, self.y = random.uniform(100, w - 100), h + 40
        if pos is not None:
            self.x, self.y = pos
        self.target = self.new_target()
        self.a = math.atan2(self.target[1] - self.y, self.target[0] - self.x)
        self.state = "walk"
        self.timer = random.uniform(*self.spec.get("walk_t", (3, 8)))
        self.phase = random.uniform(0, 6)
        self.t = 0.0
        self.alive = True
        self.moving = False
        self.entered = pos is not None
        self.freeze = 0.0
        self.feast = 0.0
        self.mouse_near = False
        self.run_t = 0.0
        self.run_boost = 1.0
        self.striking = False
        self.tongue = None
        self.transient = False
        self.seen = False
        self.cross = None
        self.drop_y = 0.0
        self.last_print = (self.x, self.y)
        self.off = (random.uniform(-45, 45), random.uniform(-45, 45))
        self.segs = [(self.x, self.y)] * self.spec.get("chain", 0)

    def new_target(self):
        m = 80
        if PERCH and PERCHES and self.kind not in ("fly", "moth") and random.random() < 0.18:
            x1, y1, x2, y2 = random.choice(PERCHES)
            f = random.random()
            return (x1 + (x2 - x1) * f, y1 + (y2 - y1) * f)
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
        if self.state == "drop":  # spider rappelling down its thread
            self.a = math.pi / 2
            self.y += 70 * dt
            self.moving = True
            self.phase += 70 * dt / (9.0 * SIZE)
            if self.y >= self.drop_y:
                self.state = "walk"
                self.entered = True
            return
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
            diff = (desired - self.a + math.pi) % (2 * math.pi) - math.pi
            turn = (2.3 if boost <= 1 else 2.3 + (boost - 1) * 1.4) * dt
            if self.kind == "fly":
                turn *= 3
            self.a += max(-turn, min(turn, diff))
            if abs(diff) > 1.0:
                speed *= 0.4 if boost <= 1 else 0.55
            self.x += math.cos(self.a) * speed * dt
            self.y += math.sin(self.a) * speed * dt
            self.moving = True
            self.phase += speed * dt / (9.0 * SIZE)
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

        # Once on screen, stay on screen.
        if 20 < self.x < self.w - 20 and 20 < self.y < self.h - 20:
            self.entered = True
        if self.entered and not self.transient:
            self.x = clamp(self.x, 15, self.w - 15)
            self.y = clamp(self.y, 15, self.h - 15)
        if self.segs:
            self.follow()

    def follow(self):
        gap = self.spec["gap"] * SIZE
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
            return
        if self.kind == "caterpillar":
            self.draw_caterpillar(c)
            return
        ca, sa = math.cos(self.a), math.sin(self.a)
        s = SIZE
        spec = self.spec

        def T(px, py):
            px, py = px * s, py * s
            return (self.x + px * ca - py * sa, self.y + px * sa + py * ca)

        def poly(pts, fill):
            flat = [v for p in pts for v in T(*p)]
            c.create_polygon(flat, fill=fill, outline="", tags="bug")

        def line(pts, width, fill):
            flat = [v for p in pts for v in T(*p)]
            c.create_line(flat, width=max(1, int(width * s)), fill=fill,
                          capstyle="round", joinstyle="round", tags="bug")

        if self.kind == "spider" and self.state == "drop":
            c.create_line(self.x, 0, self.x, self.y, fill="#3a3a3a", width=1, tags="bug")

        # Legs first so the body sits on top of them.
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

    def body_spider(self, poly, line, T, c):
        poly(ellipse(-13, 0, 12, 9), BODY)
        poly(ellipse(4, 0, 8, 6.5), SHELL)
        poly(ellipse(-13, 0, 5, 4), SHELL)
        fang = 1.2 * math.sin(self.t * 9)
        line([(11, -2), (14, -2 + fang)], 2, LEG)
        line([(11, 2), (14, 2 - fang)], 2, LEG)
        if self.feast > 0:  # holding its wrapped-up catch
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
            if self.striking:
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
        line([(-12, 0), (-24, sway), (-31, -6 + sway), (-27, -15), (-17, -17)],
             3, "#4a3318")
        poly([(-17, -20), (-10, -17), (-17, -14)], "#2a1c0a")
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
        if self.tongue:
            tx, ty, _ = self.tongue
            hx = self.x + math.cos(self.a) * 18 * SIZE
            hy = self.y + math.sin(self.a) * 18 * SIZE
            c.create_line(hx, hy, tx, ty, width=3, fill="#d04060",
                          capstyle="round", tags="bug")
            c.create_oval(tx - 5, ty - 5, tx + 5, ty + 5, fill="#d04060",
                          outline="", tags="bug")

    def draw_centipede(self, c):
        s = SIZE
        n = len(self.segs)
        for i in range(n - 1, -1, -1):
            x, y = self.segs[i]
            if i > 0:
                px, py = self.segs[i - 1]
                ang = math.atan2(py - y, px - x) if (px, py) != (x, y) else self.a
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
        hx, hy = self.segs[0]
        ca, sa = math.cos(self.a), math.sin(self.a)
        for side in (1, -1):
            wig = 4 * s * math.sin(self.t * 8 + side)
            c.create_line(hx + ca * 6 * s, hy + sa * 6 * s,
                          hx + ca * 22 * s - sa * side * (8 * s + wig),
                          hy + sa * 22 * s + ca * side * (8 * s + wig),
                          hx + ca * 38 * s - sa * side * (14 * s - wig),
                          hy + sa * 38 * s + ca * side * (14 * s - wig),
                          width=1, fill=LEG, smooth=True, tags="bug")
        if self.feast > 0:  # carrying its catch
            gx, gy = hx + ca * 14 * s, hy + sa * 14 * s
            c.create_oval(gx - 8 * s, gy - 6 * s, gx + 8 * s, gy + 6 * s,
                          fill="#c4c4c4", outline="", tags="bug")

    def draw_caterpillar(self, c):
        s = SIZE
        n = len(self.segs)
        for i in range(n - 1, -1, -1):
            x, y = self.segs[i]
            r = (4.6 if i else 5.4) * s
            bump = 1.2 * s * math.sin(self.phase * 1.2 - i * 0.8) if self.moving else 0
            col = "#2a4d1c" if i == 0 else ("#4f8f33" if i % 2 else "#3d7a28")
            c.create_oval(x - r, y - r - bump, x + r, y + r - bump, fill=col,
                          outline="", tags="bug")
        hx, hy = self.segs[0]
        ca, sa = math.cos(self.a), math.sin(self.a)
        for side in (1, -1):
            c.create_line(hx + ca * 4 * s, hy + sa * 4 * s,
                          hx + ca * 10 * s - sa * side * 4 * s,
                          hy + sa * 10 * s + ca * side * 4 * s,
                          width=1, fill=LEG, tags="bug")


class World:
    def __init__(self, canvas, w, h):
        self.c = canvas
        self.w, self.h = w, h
        self.bugs = []
        self.respawns = []        # (when, kind)
        self.splats = []          # (expires_at, tag)
        self.prints = []          # (expires_at, canvas id)
        self.eggs = []            # dicts: id, x, y, hatch
        self.splat_n = 0
        self.prev_down = False
        self.last_click = (0.0, 0, 0)
        self.last_mouse = (0, 0)
        self.mouse_moved = time.perf_counter()
        self.next_perch = 0.0
        self.next_cross = (time.perf_counter() + CROSS_MINUTES * 60
                           if CROSS_MINUTES > 0 else 1e18)
        self.leader = [w / 2, h / 2]
        self.leader_dest = (w / 2, h / 2)
        for kind, n in COUNTS.items():
            for _ in range(n):
                self.bugs.append(Insect(kind, w, h))

    # ------------------------------ helpers ------------------------------
    @staticmethod
    def nearest(ins, group, limit):
        best, best_d = None, limit
        for g in group:
            d = math.hypot(g.x - ins.x, g.y - ins.y)
            if d < best_d:
                best, best_d = g, d
        return best, best_d

    def mouse_check(self, ins, mx, my):
        """Track the mouse entering a bug's personal space. Returns True if it should flee."""
        near = math.hypot(mx - ins.x, my - ins.y) < 70 * SIZE + 30
        if near and not ins.mouse_near:
            ins.mouse_near = True
            if random.random() < FREEZE_CHANCE:
                ins.freeze = random.uniform(0.7, 1.5)
        elif not near:
            ins.mouse_near = False
        return near and ins.freeze <= 0

    def kill(self, ins, now):
        ins.alive = False
        if not ins.transient:
            self.respawns.append((now + RESPAWN_SECONDS, ins.kind))

    def splat(self, x, y, col, scale, now):
        self.splat_n += 1
        tag = "splat%d" % self.splat_n
        c, s = self.c, SIZE * scale
        pts = []
        for i in range(14):
            ang = 2 * math.pi * i / 14
            r = random.uniform(8, 16) * s
            pts += [x + r * math.cos(ang), y + r * math.sin(ang)]
        c.create_polygon(pts, fill=col, outline="", tags=tag)
        for _ in range(random.randint(6, 10) * int(max(1, scale))):
            ang = random.uniform(0, 2 * math.pi)
            d = random.uniform(15, 40) * s
            r = random.uniform(1.5, 4) * s
            cx, cy = x + d * math.cos(ang), y + d * math.sin(ang)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="", tags=tag)
        for _ in range(random.randint(3, 5)):  # leftover leg bits
            ang = random.uniform(0, 2 * math.pi)
            ln = random.uniform(10, 22) * s
            c.create_line(x + 8 * s * math.cos(ang), y + 8 * s * math.sin(ang),
                          x + ln * math.cos(ang + 0.4), y + ln * math.sin(ang + 0.4),
                          width=2, fill=col, capstyle="round", tags=tag)
        self.splats.append((now + SPLAT_SECONDS * (1.5 if scale > 1 else 1), tag))

    def squash(self, ins, now):
        self.kill(ins, now)
        col = {"ladybug": "#3a1210", "frog": "#1b2b14", "mantis": "#1b2b14",
               "caterpillar": "#1b2b14"}.get(ins.kind, "#1b1b12")
        self.splat(ins.x, ins.y, col, 1.0, now)
        play(260, 140)

    def slam(self, x, y, now):
        """Double-click: a big splat that wipes out everything close by."""
        for b in self.bugs:
            if b.alive and math.hypot(b.x - x, b.y - y) < 70 * SIZE:
                self.kill(b, now)
        for e in list(self.eggs):
            if math.hypot(e["x"] - x, e["y"] - y) < 70 * SIZE:
                self.c.delete(e["id"])
                self.eggs.remove(e)
        self.splat(x, y, "#141414", 2.4, now)
        play(150, 80)

    def spawn_crosser(self, now):
        kind = random.choice(["beetle", "ant", "cockroach", "ladybug",
                              "caterpillar", "spider", "scorpion"])
        w, h = self.w, self.h
        if random.random() < 0.5:
            sx, ex = (-40, w + 80) if random.random() < 0.5 else (w + 40, -80)
            sy, ey = random.uniform(100, h - 100), random.uniform(100, h - 100)
        else:
            sy, ey = (-40, h + 80) if random.random() < 0.5 else (h + 40, -80)
            sx, ex = random.uniform(100, w - 100), random.uniform(100, w - 100)
        ins = Insect(kind, w, h, (sx, sy))
        ins.entered = False
        ins.transient = True
        ins.cross = (ex, ey)
        ins.a = math.atan2(ey - sy, ex - sx)
        self.bugs.append(ins)

    # -------------------------------- tick --------------------------------
    def tick(self, dt):
        now = time.perf_counter()
        mx, my = cursor_pos()
        global PERCHES
        if PERCH and now >= self.next_perch:
            PERCHES = perch_lines(self.w, self.h)
            self.next_perch = now + 2.0
        if (mx, my) != self.last_mouse:
            self.last_mouse = (mx, my)
            self.mouse_moved = now
        mouse_still = now - self.mouse_moved > 3.0
        swarm = key_down(SWARM_KEY)

        # Ant colony leader wanders; ants stream after it.
        lx, ly = self.leader
        dx, dy = self.leader_dest[0] - lx, self.leader_dest[1] - ly
        dist = math.hypot(dx, dy)
        if dist < 20:
            self.leader_dest = (random.uniform(100, self.w - 100),
                                random.uniform(100, self.h - 100))
        else:
            self.leader = [lx + dx / dist * 70 * dt, ly + dy / dist * 70 * dt]

        live = [b for b in self.bugs if b.alive]

        # Predators grab prey that is within reach.
        if HUNTING:
            for h in live:
                spec = h.spec
                if not spec["prey"] or h.feast > 0 or not h.alive:
                    continue
                cands = [p for p in live if p.alive and p.kind in spec["prey"]]
                prey, d = self.nearest(h, cands, spec["catch"] * SIZE)
                if prey:
                    self.kill(prey, now)
                    h.feast = spec.get("feast", 4.0)
                    if spec.get("tongue"):
                        h.tongue = [prey.x, prey.y, 0.3]
                        h.a = math.atan2(prey.y - h.y, prey.x - h.x)

        # Mouse clicks.
        down = key_down(0x01)
        if CLICK_TO_SQUASH and down and not self.prev_down:
            t0, x0, y0 = self.last_click
            double = now - t0 < 0.4 and math.hypot(mx - x0, my - y0) < 40
            self.last_click = (0.0, 0, 0) if double else (now, mx, my)
            if double:
                self.slam(mx, my, now)
            else:
                egg = next((e for e in self.eggs
                            if math.hypot(mx - e["x"], my - e["y"]) < 14), None)
                best, best_d = None, 1e9
                for ins in self.bugs:
                    if not ins.alive:
                        continue
                    d = math.hypot(mx - ins.x, my - ins.y)
                    if d < (ins.spec["hit"] + 8) * SIZE and d < best_d:
                        best, best_d = ins, d
                if best is not None:
                    self.squash(best, now)
                elif egg is not None:
                    self.c.delete(egg["id"])
                    self.eggs.remove(egg)
                    self.splat(egg["x"], egg["y"], "#2a2a22", 0.5, now)
                    play(320, 200)
        self.prev_down = down

        live = [b for b in self.bugs if b.alive]
        hunters = [b for b in live if b.spec["scare"] and b.feast <= 0]

        # Decide what each bug does this frame.
        for ins in live:
            kind, spec = ins.kind, ins.spec
            if ins.transient:
                ins.update(dt, ins.cross, 1.0)
                inside = -50 < ins.x < self.w + 50 and -50 < ins.y < self.h + 50
                if inside:
                    ins.seen = True
                elif ins.seen:
                    ins.alive = False
                continue
            goal, boost = None, 1.0
            hunting = False
            ins.striking = False
            flee_mouse = (FLEE_FROM_MOUSE and kind != "moth"
                          and self.mouse_check(ins, mx, my))

            if HUNTING and spec["prey"] and ins.feast <= 0 and ins.state != "drop":
                cands = [p for p in live if p.kind in spec["prey"]]
                prey, d = self.nearest(ins, cands, spec["sight"] * SIZE)
                if prey:
                    hunting = True
                    if d < spec["strike"] * SIZE:
                        goal, boost = (prey.x, prey.y), spec["rush"]
                        ins.striking = True
                    elif spec["creep"] == 0:  # sit still, watch it come
                        ins.freeze = 0.1
                        diff = (math.atan2(prey.y - ins.y, prey.x - ins.x)
                                - ins.a + math.pi) % (2 * math.pi) - math.pi
                        ins.a += clamp(diff, -3 * dt, 3 * dt)
                    else:
                        goal, boost = (prey.x, prey.y), spec["creep"]

            threat = None
            if HUNTING:
                best_d = 1e9
                for h in hunters:
                    if h is not ins and kind in h.spec["prey"]:
                        d = math.hypot(h.x - ins.x, h.y - ins.y)
                        if d < h.spec["scare"] * SIZE and d < best_d:
                            threat, best_d = h, d

            if threat:
                goal, boost = ins.away_goal(threat.x, threat.y), 3.0
            elif swarm and not spec["prey"]:
                goal = (mx + ins.off[0], my + ins.off[1])
                boost = 2.0
            elif hunting:
                pass
            elif flee_mouse:
                goal = ins.away_goal(mx, my)
                boost = 3.0 if kind in ("beetle", "fly", "cockroach") else 2.4
            elif kind == "moth":
                ang = now * 1.2 + ins.phase
                goal = (mx + 110 * math.cos(ang), my + 110 * math.sin(ang))
                boost = 1.6
            elif kind == "ladybug" and mouse_still:
                d = math.hypot(ins.x - mx, ins.y - my)
                if d > 150:
                    goal = (mx + (ins.x - mx) / d * 150, my + (ins.y - my) / d * 150)
                    boost = 1.0
            elif kind == "ant":
                goal = (self.leader[0] + ins.off[0], self.leader[1] + ins.off[1])
            ins.update(dt, goal, boost)

            if ins.alive and ins.state != "drop":
                # Footprints.
                if (FOOTPRINTS and ins.moving and kind in PRINT_KINDS
                        and math.hypot(ins.x - ins.last_print[0],
                                       ins.y - ins.last_print[1]) > 38):
                    ins.last_print = (ins.x, ins.y)
                    i = self.c.create_oval(ins.x - 1.5, ins.y - 1.5, ins.x + 1.5,
                                           ins.y + 1.5, fill="#262626", outline="")
                    self.prints.append((now + 4.0, i))
                # Eggs.
                if (EGGS and kind == "beetle" and random.random() < dt / 150
                        and len(self.eggs) + sum(b.kind == "beetle" for b in live)
                        < COUNTS.get("beetle", 0) * 2):
                    i = self.c.create_oval(ins.x - 3, ins.y - 4, ins.x + 3, ins.y + 4,
                                           fill="#d8d4c0", outline="#8a8670")
                    self.eggs.append({"id": i, "x": ins.x, "y": ins.y,
                                      "hatch": now + random.uniform(15, 22)})
                # Spider drops in on a thread from the top of the screen.
                if (kind == "spider" and ins.feast <= 0 and ins.entered
                        and random.random() < dt / 90):
                    ins.x = random.uniform(100, self.w - 100)
                    ins.y = -10
                    ins.state = "drop"
                    ins.drop_y = random.uniform(150, self.h * 0.55)
                    ins.target = ins.new_target()

        # Eggs hatch, respawns, expired splats and footprints.
        for e in list(self.eggs):
            if now >= e["hatch"]:
                self.c.delete(e["id"])
                self.eggs.remove(e)
                self.bugs.append(Insect("beetle", self.w, self.h, (e["x"], e["y"])))
        for item in list(self.respawns):
            if now >= item[0]:
                self.respawns.remove(item)
                self.bugs.append(Insect(item[1], self.w, self.h))
        for item in list(self.splats):
            if now >= item[0]:
                self.c.delete(item[1])
                self.splats.remove(item)
        for item in list(self.prints):
            if now >= item[0]:
                self.c.delete(item[1])
                self.prints.remove(item)
        if now >= self.next_cross:
            self.spawn_crosser(now)
            self.next_cross = now + CROSS_MINUTES * 60

        self.bugs = [b for b in self.bugs if b.alive]
        self.c.delete("bug")
        for ins in self.bugs:
            ins.draw(self.c)


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
