Summary

What it is: desktop_bug.pyw is a Windows prank script that puts a beetle and a spider on top of your real screen. Clicks pass through the empty areas to your other apps.

What the bugs do:

Both wander around, pause to twitch their legs, and turn toward new spots.
The spider chases the beetle once it spots it, catches it, and holds the wrapped-up beetle for about 4 seconds.
Left-click a bug to squash it. A splat stays for 8 seconds, and the bug comes back after 25 seconds.
Bugs usually run from the mouse, but about a third of the time they freeze so you can hit them.

Running it: Install Python from python.org (tick "Add python.exe to PATH"). Save the code below as desktop_bug.pyw and double-click it. The bugs appear after 10 seconds. Press Ctrl + Shift + Q to quit.

Settings at the top of the file: SHOW_BEETLE, SHOW_SPIDER, SIZE, SPEED, START_DELAY, RUN_MINUTES, SPIDER_HUNTS_BEETLE, FREEZE_CHANCE, RESPAWN_SECONDS and a few more.

Limits: It only shows on the main monitor, and it doesn't appear over games in exclusive fullscreen.

Code (desktop_bug.pyw)
python
"""
Desktop Bug Prank (Windows)

A beetle and a spider walk around on top of everything on your real screen.
 - The spider hunts the beetle when it spots it, and catches it.
 - Left-click a bug to squash it. A splat is left behind for a few seconds.
 - Bugs run away from the mouse (sometimes they freeze instead, so you can hit them).
 - Squashed or eaten bugs come back after a while.

HOW TO RUN
  1. Install Python from python.org (tick "Add python.exe to PATH").
  2. Double-click this file (desktop_bug.pyw). No console window appears.

HOW TO STOP
  Press Ctrl + Shift + Q at any time.
  (Backup: Task Manager > end "Python" / "pythonw.exe".)
"""

import ctypes
import math
import random
import time
import tkinter as tk

# ------------------------- SETTINGS (change these) -------------------------
SHOW_BEETLE = True
SHOW_SPIDER = True
SIZE = 1.0                  # 1.0 = normal, 1.5 = bigger, 0.7 = smaller
SPEED = 90                  # beetle walking speed in pixels per second
START_DELAY = 10            # seconds to wait before the bugs appear
RUN_MINUTES = 0             # auto-quit after this many minutes (0 = never)

SPIDER_HUNTS_BEETLE = True  # spider chases and catches the beetle
SPIDER_SIGHT = 380          # how far (pixels) the spider can spot the beetle

FLEE_FROM_MOUSE = True      # bugs run away when the mouse gets close
FREEZE_CHANCE = 0.35        # chance a bug freezes (easy to hit) instead of running
CLICK_TO_SQUASH = True      # left-click on a bug to squash it
RESPAWN_SECONDS = 25        # a squashed or eaten bug returns after this long
SPLAT_SECONDS = 8           # how long a splat stays on screen
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


# Leg layouts in the bug's own coordinates (it faces +x).
# Each leg: (attach_x, knee_dx, foot_dx).
SPECS = {
    "beetle": {
        "legs": [(11, 5, 9), (5, 0, 0), (-1, -5, -9)],
        "attach_y": 6, "knee_y": 14, "foot_y": 21, "width": 2, "swing": 5,
        "base": 1.0, "hit": 30,
    },
    "spider": {
        "legs": [(8, 10, 19), (3, 6, 10), (-2, -5, -10), (-7, -11, -20)],
        "attach_y": 5, "knee_y": 15, "foot_y": 29, "width": 2, "swing": 6,
        "base": 0.8, "hit": 38,
    },
}


class Insect:
    def __init__(self, kind, w, h):
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
        self.target = self.new_target()
        self.a = math.atan2(self.target[1] - self.y, self.target[0] - self.x)
        self.state = "walk"
        self.timer = random.uniform(3, 8)
        self.phase = random.uniform(0, 6)
        self.t = 0.0
        self.alive = True
        self.moving = False
        self.entered = False
        self.freeze = 0.0
        self.feast = 0.0
        self.mouse_near = False
        self.run_t = 0.0
        self.run_boost = 1.0

    def new_target(self):
        m = 80
        return (random.uniform(m, self.w - m), random.uniform(m, self.h - m))

    def update(self, dt, goal=None, boost=1.0):
        self.t += dt
        self.moving = False
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
                self.timer = random.uniform(0.6, 3.0)
        else:
            self.timer -= dt
            if self.timer <= 0:
                self.state = "walk"
                self.timer = random.uniform(3, 8)
                self.target = self.new_target()

        # Once on screen, stay on screen.
        if 20 < self.x < self.w - 20 and 20 < self.y < self.h - 20:
            self.entered = True
        if self.entered:
            self.x = clamp(self.x, 15, self.w - 15)
            self.y = clamp(self.y, 15, self.h - 15)

    def away_goal(self, px, py):
        ang = math.atan2(self.y - py, self.x - px)
        tx, ty = self.x, self.y
        for da in (0, 0.9, -0.9, 1.8, -1.8):
            tx = clamp(self.x + math.cos(ang + da) * 500, 40, self.w - 40)
            ty = clamp(self.y + math.sin(ang + da) * 500, 40, self.h - 40)
            if math.hypot(tx - self.x, ty - self.y) > 150:
                break
        return (tx, ty)

    def draw(self, c):
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

        if self.kind == "spider":
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
        else:
            poly(ellipse(-6, 0, 14, 10), BODY)
            poly(ellipse(9, 0, 8, 7), BODY)
            poly(ellipse(19, 0, 5, 5), BODY)
            line([(-19, 0), (7, 0)], 1, SHELL)  # wing seam
            wig = 3 * math.sin(self.t * 9)
            for side in (1, -1):
                line([(21, side * 2), (28, side * 6 + wig), (34, side * 5 - wig)],
                     1, LEG)


class World:
    def __init__(self, canvas, w, h):
        self.c = canvas
        self.w, self.h = w, h
        self.insects = {}
        self.respawn_at = {}
        self.splats = []          # (expires_at, tag)
        self.splat_n = 0
        self.prev_down = False
        if SHOW_BEETLE:
            self.insects["beetle"] = Insect("beetle", w, h)
        if SHOW_SPIDER:
            self.insects["spider"] = Insect("spider", w, h)

    def alive(self, kind):
        ins = self.insects.get(kind)
        return ins if ins is not None and ins.alive else None

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

    def squash(self, ins, now):
        ins.alive = False
        self.respawn_at[ins.kind] = now + RESPAWN_SECONDS
        self.splat_n += 1
        tag = "splat%d" % self.splat_n
        c, s = self.c, SIZE
        col = "#1b1b12" if ins.kind == "beetle" else "#141414"
        pts = []
        for i in range(14):
            ang = 2 * math.pi * i / 14
            r = random.uniform(8, 16) * s
            pts += [ins.x + r * math.cos(ang), ins.y + r * math.sin(ang)]
        c.create_polygon(pts, fill=col, outline="", tags=tag)
        for _ in range(random.randint(6, 10)):
            ang = random.uniform(0, 2 * math.pi)
            d = random.uniform(15, 40) * s
            r = random.uniform(1.5, 4) * s
            cx, cy = ins.x + d * math.cos(ang), ins.y + d * math.sin(ang)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="", tags=tag)
        for _ in range(random.randint(3, 5)):  # leftover leg bits
            ang = random.uniform(0, 2 * math.pi)
            ln = random.uniform(10, 22) * s
            c.create_line(ins.x + 8 * s * math.cos(ang), ins.y + 8 * s * math.sin(ang),
                          ins.x + ln * math.cos(ang + 0.4), ins.y + ln * math.sin(ang + 0.4),
                          width=2, fill=col, capstyle="round", tags=tag)
        self.splats.append((now + SPLAT_SECONDS, tag))

    def tick(self, dt):
        now = time.perf_counter()
        mx, my = cursor_pos()
        beetle, spider = self.alive("beetle"), self.alive("spider")

        # Spider catches beetle.
        if (SPIDER_HUNTS_BEETLE and beetle and spider and spider.feast <= 0
                and math.hypot(spider.x - beetle.x, spider.y - beetle.y) < 32 * SIZE):
            beetle.alive = False
            self.respawn_at["beetle"] = now + RESPAWN_SECONDS
            spider.feast = 4.0
            beetle = None

        # Left-click squash (only on the moment the button goes down).
        down = key_down(0x01)
        if CLICK_TO_SQUASH and down and not self.prev_down:
            best, best_d = None, 1e9
            for ins in self.insects.values():
                if not ins.alive:
                    continue
                d = math.hypot(mx - ins.x, my - ins.y)
                if d < (ins.spec["hit"] + 8) * SIZE and d < best_d:
                    best, best_d = ins, d
            if best is not None:
                self.squash(best, now)
        self.prev_down = down
        beetle, spider = self.alive("beetle"), self.alive("spider")

        # Decide what each bug does this frame.
        for kind, ins in self.insects.items():
            if not ins.alive:
                continue
            goal, boost = None, 1.0
            hunting = False
            if kind == "spider" and SPIDER_HUNTS_BEETLE and beetle and ins.feast <= 0:
                if math.hypot(beetle.x - ins.x, beetle.y - ins.y) < SPIDER_SIGHT:
                    goal, boost, hunting = (beetle.x, beetle.y), 2.2, True
            flee_mouse = FLEE_FROM_MOUSE and self.mouse_check(ins, mx, my)
            if flee_mouse and not hunting:
                goal = ins.away_goal(mx, my)
                boost = 3.0 if kind == "beetle" else 2.4
            elif (kind == "beetle" and goal is None and spider and SPIDER_HUNTS_BEETLE
                  and spider.feast <= 0
                  and math.hypot(spider.x - ins.x, spider.y - ins.y) < 200):
                goal = ins.away_goal(spider.x, spider.y)
                boost = 1.6
            ins.update(dt, goal, boost)

        # Respawns and expired splats.
        for kind, when in list(self.respawn_at.items()):
            if now >= when:
                del self.respawn_at[kind]
                self.insects[kind] = Insect(kind, self.w, self.h)
        for item in list(self.splats):
            if now >= item[0]:
                self.c.delete(item[1])
                self.splats.remove(item)

        self.c.delete("bug")
        for ins in self.insects.values():
            if ins.alive:
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

That is the only file. The headless test script I used is not needed to run the prank. To run it from a terminal instead of double-clicking, use pythonw desktop_bug.pyw, or python desktop_bug.pyw if you want to see any errors.

---
NOTE FOR THE NEXT CLAUDE: this file is the old v1 summary. The full, current project notes (v1 to v7, how it works, how the user likes to work, git state) are in CLAUDE.md in this folder. Read that first.
