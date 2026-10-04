# Screen Insect: handoff notes for the next Claude

Read this first. It records everything done so far, how the code works, and how the user likes to work.
(`summary.md` is the user's original v1 summary and is older than this file.)

## What this project is
Windows-only desktop "bug prank": Python/tkinter scripts (`.pyw`, double-click to run) that draw bugs on a
transparent full-screen overlay on top of the real desktop. Clicks fall through the empty areas to other apps.
Owner: Dr. Sedat Kacar (sedatkacar56@gmail.com). Repo: https://github.com/sedatkacar56/Screen_insect
Quit key in every version: **Ctrl + Shift + Q**.

## Files (each is a standalone version; they are NOT imports of each other)
| File | Version |
|---|---|
| `desktop_bug_beetle_spider_v1.pyw` | v1: one beetle + one spider (originally `desktop_bug.pyw`) |
| `desktop_bug_beetle_spider_v2.pyw` | v2: identical to v1; the user's stable "working" version |
| `desktop_bug_centipede_v3.pyw` | v3: + house centipede (creeps slowly far away, rushes when close) |
| `desktop_bug_manybeetles_v4.pyw` | v4: dict -> list of bugs; 6 beetles, 1 spider, 1 centipede |
| `desktop_bug_multi_v5.pyw` | v5: 12 kinds, eggs, footprints, perching on title bars, crossings, F8 swarm, double-click slam |
| `desktop_bug_fight_man_v6.pyw` | v6: arena with real fights + the little man (sword/hammer/fists) |
| `desktop_bug_gun_v7.pyw` | v7 (**latest**): v6 + gun with limited ammo, fewer/slower spawns |
| `README.md`, `docs/index.html` | public README and GitHub Pages site (play guide + version history) |
| `VERSIONS.md` | short table of what each file includes |

Naming rule the user chose: `desktop_bug_<short description>_v<N>.pyw` (description BEFORE the version number).
Keep `VERSIONS.md`, `README.md` and `docs/index.html` in sync when adding a version.

## How the user likes to work (important)
- **Never edit a working version in place.** When they said "it already works, don't change", they meant it.
  New features go into a NEW file with the next version number (copy the latest, then patch).
  (Exception: the small "gun stands still, double-click to walk" tweak was applied to v7 in place at their request.)
- They write short, informal, often misspelled messages. Read the intent, don't ask many questions.
- "DO ALL" means implement every idea listed. They want lots of features but a *less cluttered* screen in v6+.
- They test by double-clicking on their real desktop; Claude can only test headless (see Testing).
- Outward actions (git push, publishing) only with their go-ahead.

## Design of the latest code (v6/v7)
Single file, sections in this order: settings block, win32 helpers (ctypes: `GetCursorPos`, `GetAsyncKeyState`),
`SPECS` dict, `WEAPONS` list, `Insect`, `Man`, `World`, overlay setup, `main()`.

- **Overlay:** `Tk` window, `overrideredirect`, `-topmost`, `-transparentcolor "#010101"`; extra window styles
  (layered/toolwindow/no-activate) set via `SetWindowLongW`. Everything is redrawn each ~16 ms: canvas items tagged
  `"bug"` are deleted and recreated (splats use their own tags so they persist).
- **Input is polled**, not bound: mouse button = `GetAsyncKeyState(0x01)` edge detection; F9 = `0x78`.
  Because the window is click-through, clicks ALSO reach the app under the cursor (known limitation).
- **`SPECS[kind]`:** `scale` (drawing size; frog 2.2, scorpion 1.8, mantis 1.3, spider 1.1, beetle/cockroach 1.0,
  centipede 0.8, ...), `r` body radius, `hp`, `atk` (damage to other bugs), `mdmg` (damage to the man; 0 = never
  attacks him and flees from him), `aggr`, `sight`, `rate`, `strike/rush/creep` (rush when closer than `strike`;
  `creep` 0 = ambusher that sits still), `eats`, `weight` (spawn weight), optional `chain`/`gap` (segmented
  bodies: centipede, caterpillar), `tongue` (frog). `power = hp*atk` decides who attacks/flees.
- **Fights (`World.pick_fight`, `think`, `strike`, `damage`, `disengage`):** an aggressor picks the nearest bug whose
  power is below `0.4 + 1.4*bold` times its own (bold = aggr * random 0.8-1.2, fixed per bug). On contact both get
  `foe` set and are locked: they face each other, trade blows every `rate` seconds (75% hit chance, damage
  x random 0.6-1.4, ambushers open with x1.8). Weak loser may disengage and flee; winner who `eats` carries the
  loser (`feast`). Lunge/shake offsets (`ox`,`oy`), spark effects (`fx`) and HP bars make fights visible.
  Weaker bugs flee stronger non-ambusher hunters; ambushers also start stalking if the target doesn't come for 3 s.
  Frog tongue one-shots bugs with maxhp <= 15 from 200 px.
- **Man:** follows the cursor (stays ~60 px away) and faces it; click -> `try_swing()`. Hit test (`World.man_hit`) at
  50% of the swing: bug must be within weapon range AND within the arc in front of him, so behind/side = no damage.
  Weapons tuple: `(name, range, arc, dmg, swing time, cooldown, knockback, stun)`. Energy bar; 0 -> KO 6 s, wakes at 50%;
  regen after 3 s without being hit.
- **v7 additions:** `GUN` weapon (8 bullets, `AMMO_REGEN` 4 s per bullet, bullets are fast straight tracers that
  hit the first bug point in their path). With the gun the man does NOT follow the cursor; he only turns to aim.
  Double-click (two clicks < 0.4 s) sets `Man.goto`; he walks, or runs if > 250 px, then stops; can't shoot while moving.
  Spawn rules: `MAX_BUGS` 5, `MAX_BIG` 3, `SPAWN_SMALL=False` (bugs with hp < 20 never spawn), and every
  `NO_DEATH_SECONDS` (20) without any death allows +1 bug (up to `MAX_EXTRA` 4; resets on any death).
  The user's phrase "small ones not visible / keep coming if nobody dies" was interpreted this way; they were
  told and can correct it.

## Testing approach (Claude has no real screen)
Import the `.pyw` with `importlib`, create `tk.Tk()` + `Canvas`, build `World`, monkeypatch `m.cursor_pos`, set
`w.next_spawn=1e18`, place `Insect`s manually (set `entered=True`), and call `w.tick(0.016)` in a loop.
Past checks: duels (e.g. mantis vs centipede split winners), front/behind weapon hits, ammo/empty clip, spawn caps,
drawing every kind. Python `-m py_compile` for syntax. NOTE: in Git Bash, long heredocs sometimes broke; write the
patch script to a file with the Write tool and run it. Test runs go faster than real time (respawn timers use
`time.perf_counter()`).

## Git / GitHub state
- Local repo in this folder, branch `main`, remote `origin` = https://github.com/sedatkacar56/Screen_insect.git
- Pushed: all versions, README, docs page, VERSIONS.md, summary.md (+ GitHub's initial LICENSE, rebased on top).
- `.gitignore` excludes `__pycache__/`. This `CLAUDE.md` may be newer than the last push: check `git status`.
- **GitHub Pages is not enabled yet** (needs the user: Settings -> Pages -> Deploy from branch -> `main` / `/docs`).
  Expected URL: https://sedatkacar56.github.io/Screen_insect/
- `gh` CLI is not installed; plain `git` works. Commit author/email: Sedat Kacar / sedatkacar56@gmail.com.
- Commit messages end with the `Co-Authored-By: Claude ...` trailer given by the harness.

## Known issues / ideas not done
- First click of a gun double-click still fires one bullet (can't know it's a double-click yet).
- Clicks pass through to apps under the cursor (fighting over icons can open things).
- Only the main monitor; not over exclusive-fullscreen games.
- Bugs vs. bugs balance is only lightly tuned (see duel tests); tweak `hp/atk/aggr` in `SPECS` if the user complains.
- Not implemented (offered earlier, user said "do all" then moved on): sounds beyond hit beeps, per-monitor support.
- Ideas the user might like next: man picks up health, more weapons, bullet limit pickups, score counter.
