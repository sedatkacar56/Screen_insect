# Screen Insect

Bugs that walk around on top of your real Windows desktop. Started as a small prank (a beetle and a spider) and grew into a bug arena where bugs fight each other and a tiny man defends your screen.

Clicks pass through the empty areas, so your other apps keep working underneath.

## Play in your browser

**https://sedatkacar56.github.io/Screen_insect/**

The page has a playable browser version of v7 (code in `docs/game.js`): bugs fight, a little man follows your mouse, and you click to attack with a sword, hammer, fists or gun. It is the same game, but it runs inside the page. To get bugs walking on your real desktop, use the Python files below.

(Page not loading? In the repo go to Settings, then Pages, choose branch `main` and folder `/docs`.)

## How to play on your desktop

1. Install **Python 3** from [python.org](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"**). Windows only, nothing else to install.
2. Download the file you want from this repo.
3. Double-click it. No console window opens. The bugs appear after 10 seconds.
4. Press **Ctrl + Shift + Q** to quit at any time.

To see errors, run it from a terminal with `python desktop_bug_gun_v7.pyw` instead of double-clicking.

## Versions

| File | What it has |
|---|---|
| `desktop_bug_beetle_spider_v1.pyw` | One beetle and one spider. The spider hunts the beetle. Click to squash. |
| `desktop_bug_beetle_spider_v2.pyw` | Same as v1 (the stable one). |
| `desktop_bug_centipede_v3.pyw` | Adds a house centipede that creeps slowly, then rushes. |
| `desktop_bug_manybeetles_v4.pyw` | Many beetles, few predators. |
| `desktop_bug_multi_v5.pyw` | 12 kinds of bugs, eggs, footprints, swarm key (F8), double-click slam. |
| `desktop_bug_fight_man_v6.pyw` | Arena: bugs fight with hit points, realistic sizes, and a little man you control. |
| **`desktop_bug_gun_v7.pyw`** | **Latest.** v6 plus a limited-ammo gun and slower, fewer spawns. |

## Version history

**v1 and v2: beetle and spider.** The first prank. A beetle and a spider walk around on top of your screen, pause to twitch their legs and turn toward new spots. The spider chases the beetle when it spots it and holds the wrapped-up beetle for about 4 seconds. Left-click a bug to squash it: the splat stays 8 seconds and the bug comes back after 25. Bugs run from the mouse, but about a third of the time they freeze so you can hit them. v2 is the same file kept as the stable version.

**v3: house centipede.** A long, many-legged centipede that eats spiders and beetles. Far from prey it creeps slowly and waits; once the prey gets close it rushes in fast, grabs it and carries it off. The beetle and spider now run away from it.

**v4: many prey, few predators.** The code was reworked so there can be several bugs of each kind: 6 beetles, 1 spider, 1 centipede.

**v5: the big zoo.** Twelve kinds of bugs. Prey: beetle, ant (a colony that streams after a leader), fly, moth (circles your cursor), caterpillar, ladybug (follows your cursor when you hold still), cockroach (runs along the screen edges). Predators: spider (sometimes drops from the top on a web thread), centipede, praying mantis (waits, then strikes), scorpion, frog (tongue flick). Extras: bugs walk on the active window's title bar and the taskbar, leave tiny footprints, beetles lay eggs that hatch, a bug crosses the screen every 2 minutes, squash sounds, a double-click slam, and F8 makes the prey swarm your cursor.

**v6: the arena.** Too busy, so most of v5's clutter was removed. Bugs spawn slowly, one at a time, and fight each other for real: hit points, random hits, lunges, health bars, a winner that is not always the same. Sizes are realistic (the frog and scorpion are bigger than the centipede). A **little man** joins: he follows your cursor, faces it, and you click to attack with a sword, hammer or fists (F9 switches). Hits only land on bugs in front of him. Bugs bite back, and he has an energy bar.

**v7: the gun.** Adds a gun with limited ammo (8 bullets, one returns every 4 seconds). With the gun he stands still and only aims; double-click makes him walk or run to a spot. Only mid-size and big bugs spawn now, at most 5 at once, and one extra bug is allowed for every 20 seconds in which nobody dies.

## Controls (v6 and v7)

| Input | What it does |
|---|---|
| Move the mouse | The little man follows the cursor and faces it |
| Left-click | Swing the weapon (or shoot) toward the cursor |
| **F9** | Switch weapon: sword, hammer, fists, gun (v7) |
| Double-click (gun) | Make him walk, or run if far, to the cursor spot |
| **Ctrl + Shift + Q** | Quit |

- **Sword**: fast, medium damage, widest reach.
- **Hammer**: slow and heavy, knocks bugs back and stuns them.
- **Fists**: weak but quick.
- **Gun** (v7): bullets fly straight. Ammo is limited (8 bullets, one comes back every 4 seconds). With the gun he stands still and only aims.

A hit only lands on a bug **in front** of the man. Bugs beside or behind him are not hurt. Small bugs run away from him, big ones attack him and bite harder the bigger they are. He has an energy bar. At zero he is knocked out for 6 seconds, then wakes with half energy.

## The bugs (v6 and v7)

Small to big: ant, fly, ladybug, moth, caterpillar, beetle, cockroach, spider, centipede, mantis, scorpion, frog. Bigger bugs start fights with smaller ones and with each other. Fights take time, have a random outcome, and the winner carries off and eats the loser. In v7 only the mid and big bugs show up, at most 5 at once. If nobody dies for 20 seconds, one more is allowed.

## Settings

Every file has a settings block at the top. In v7 you can change, for example, `MAX_BUGS`, `SPAWN_SMALL`, `AMMO_MAX`, `AMMO_REGEN`, `SIZE`, `SPEED`, `START_DELAY` and `RUN_MINUTES`.

## Limits

- Windows only. It only shows on the main monitor and does not appear over games in exclusive fullscreen.
- Your clicks still reach the window under the cursor, so fight over an empty part of the desktop.
- Stop it with Ctrl + Shift + Q. Backup: end `pythonw.exe` in Task Manager.

## Files for the web page

`docs/index.html` is the page (guide plus the playable game) and `docs/game.js` is the browser version of v7.
