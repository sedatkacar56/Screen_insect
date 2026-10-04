"""
Desktop Bug Prank (Windows)

A small bug walks around on top of everything on your real screen.
Mouse clicks pass straight through it, so nothing else is blocked.

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
BUG = "beetle"          # "beetle" or "spider"
SIZE = 1.0              # 1.0 = normal, 1.5 = bigger, 0.7 = smaller
SPEED = 90              # walking speed in pixels per second
START_DELAY = 10        # seconds to wait before the bug appears
RUN_MINUTES = 0         # auto-quit after this many minutes (0 = never)
FLEE_FROM_MOUSE = True  # bug scurries away when the mouse gets close
# ---------------------------------------------------------------------------

KEY = "#010101"         # this color is made see-through
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


# Leg layouts, in the bug's own coordinates (it faces +x).
# Each leg: (attach_x, knee_dx, foot_dx), plus spread distances.
BEETLE = {
    "legs": [(11, 5, 9), (5, 0, 0), (-1, -5, -9)],
    "attach_y": 6, "knee_y": 14, "foot_y": 21, "width": 2, "swing": 5,
}
SPIDER = {
    "legs": [(8, 10, 19), (3, 6, 10), (-2, -5, -10), (-7, -11, -20)],
    "attach_y": 5, "knee_y": 15, "foot_y": 29, "width": 2, "swing": 6,
}


class Bug:
    def __init__(self, canvas, w, h):
        self.c = canvas
        self.w, self.h = w, h
        self.x = random.choice([-40, w + 40])
        self.y = random.uniform(120, h - 120)
        self.a = math.pi if self.x > 0 else 0.0
        self.target = self.new_target()
        self.state = "walk"
        self.timer = random.uniform(3, 8)
        self.scurry = 0.0
        self.phase = 0.0
        self.t = 0.0

    def new_target(self):
        m = 80
        return (random.uniform(m, self.w - m), random.uniform(m, self.h - m))

    def update(self, dt):
        self.t += dt

        if FLEE_FROM_MOUSE:
            mx, my = cursor_pos()
            if math.hypot(mx - self.x, my - self.y) < 90 * SIZE + 40:
                away = math.atan2(self.y - my, self.x - mx)
                tx = min(max(self.x + math.cos(away) * 500, 60), self.w - 60)
                ty = min(max(self.y + math.sin(away) * 500, 60), self.h - 60)
                self.target = (tx, ty)
                self.scurry = 1.2
                self.state = "walk"
                self.timer = 4

        if self.scurry > 0:
            self.scurry -= dt

        if self.state == "walk":
            speed = SPEED * (3.2 if self.scurry > 0 else 1.0)
            tx, ty = self.target
            desired = math.atan2(ty - self.y, tx - self.x)
            diff = (desired - self.a + math.pi) % (2 * math.pi) - math.pi
            max_turn = (5.0 if self.scurry > 0 else 2.3) * dt
            self.a += max(-max_turn, min(max_turn, diff))
            if abs(diff) > 1.0:
                speed *= 0.4
            self.x += math.cos(self.a) * speed * dt
            self.y += math.sin(self.a) * speed * dt
            self.phase += speed * dt / (9.0 * SIZE)
            if math.hypot(tx - self.x, ty - self.y) < 25:
                self.target = self.new_target()
            self.timer -= dt
            if self.timer <= 0 and self.scurry <= 0:
                self.state = "pause"
                self.timer = random.uniform(0.6, 3.0)
        else:
            self.timer -= dt
            if self.timer <= 0:
                self.state = "walk"
                self.timer = random.uniform(3, 8)
                self.target = self.new_target()

    def draw(self):
        c = self.c
        c.delete("bug")
        ca, sa = math.cos(self.a), math.sin(self.a)
        s = SIZE

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

        spec = SPIDER if BUG == "spider" else BEETLE
        walking = self.state == "walk"

        # Legs first so the body sits on top of them.
        for i, (ax, kdx, fdx) in enumerate(spec["legs"]):
            for side in (1, -1):
                if walking:
                    off = 0.0 if (i + (side > 0)) % 2 == 0 else math.pi
                    swing = spec["swing"] * math.sin(self.phase + off)
                else:
                    # tiny twitch while resting
                    swing = 1.2 * math.sin(self.t * 7 + i * 1.7 + side)
                line([(ax, side * spec["attach_y"]),
                      (ax + kdx, side * spec["knee_y"]),
                      (ax + fdx + swing, side * spec["foot_y"])],
                     spec["width"], LEG)

        if BUG == "spider":
            poly(ellipse(-13, 0, 12, 9), BODY)
            poly(ellipse(4, 0, 8, 6.5), SHELL)
            poly(ellipse(-13, 0, 5, 4), SHELL)
            fang = 1.2 * math.sin(self.t * 9)
            line([(11, -2), (14, -2 + fang)], 2, LEG)
            line([(11, 2), (14, 2 - fang)], 2, LEG)
        else:
            poly(ellipse(-6, 0, 14, 10), BODY)
            poly(ellipse(9, 0, 8, 7), BODY)
            poly(ellipse(19, 0, 5, 5), BODY)
            line([(-19, 0), (7, 0)], 1, SHELL)  # wing seam
            wig = 3 * math.sin(self.t * 9)
            for side in (1, -1):
                line([(21, side * 2), (28, side * 6 + wig), (34, side * 5 - wig)],
                     1, LEG)


def make_click_through(root):
    hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
    GWL_EXSTYLE = -20
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    # layered + click-through + tool window (hidden from taskbar)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x80000 | 0x20 | 0x80)


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
    state = {"bug": None, "last": 0.0}

    def check_quit():
        ctrl, shift, q = key_down(0x11), key_down(0x10), key_down(0x51)
        timed_out = (RUN_MINUTES > 0 and
                     time.perf_counter() - started > RUN_MINUTES * 60 + START_DELAY)
        if (ctrl and shift and q) or timed_out:
            root.destroy()
            return
        root.after(100, check_quit)

    def keep_on_top():
        if state["bug"] is not None:
            root.attributes("-topmost", True)
            root.lift()
        root.after(2000, keep_on_top)

    def tick():
        now = time.perf_counter()
        dt = min(now - state["last"], 0.05)
        state["last"] = now
        state["bug"].update(dt)
        state["bug"].draw()
        root.after(16, tick)

    def begin():
        root.deiconify()
        root.update()
        make_click_through(root)
        state["bug"] = Bug(canvas, w, h)
        state["last"] = time.perf_counter()
        tick()

    root.after(int(START_DELAY * 1000), begin)
    check_quit()
    keep_on_top()
    root.mainloop()


if __name__ == "__main__":
    main()
