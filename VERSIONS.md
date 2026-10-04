# Desktop Bug Prank: what each version includes

Run any `.pyw` by double-clicking it. Quit with **Ctrl + Shift + Q**.

| File | What it includes |
|---|---|
| `desktop_bug_beetle_spider_v1.pyw` | v1. One beetle and one spider. The spider hunts the beetle. Click to squash, splats, respawn after 25 s. Bugs run from the mouse, sometimes freeze. |
| `desktop_bug_beetle_spider_v2.pyw` | Same as v1 (the working version). Nothing added. |
| `desktop_bug_centipede_v3.pyw` | v2 + **house centipede**. Creeps slowly while prey is far, rushes when close, grabs a spider or beetle. Beetle and spider flee it. |
| `desktop_bug_manybeetles_v4.pyw` | v3 with **many beetles, few predators** (6 beetles, 1 spider, 1 centipede). Supports several bugs of each kind. |
| `desktop_bug_multi_v5.pyw` | v4 + everything below. |
| `desktop_bug_fight_man_v6.pyw` | Arena: bugs fight each other (hit points, lunges, health bars, random winners), realistic sizes (frog and scorpion bigger than the centipede), few bugs that spawn slowly, and a little man you control with the mouse (sword / hammer / fists, F9 switches, energy bar). |
| `desktop_bug_gun_v7.pyw` | v6 + a **GUN** with limited ammo (8 bullets, 1 comes back every 4 s). Only mid/big bugs spawn (no tiny ones), max 5 at once, +1 allowed every 20 s while nobody dies (up to +4). F9 cycles sword / hammer / fists / gun. |

## v5 in detail

**Prey:** beetle, ant (colony stream), fly, moth (circles cursor), caterpillar, ladybug (follows cursor when you stay still), cockroach (runs along screen edges).

**Predators (1 each):** spider (also drops from the top on a web thread), house centipede, praying mantis (waits, then strikes), scorpion, frog (tongue flick).

**Behaviors:** walk on the active window's title bar and the taskbar, tiny footprints, beetles lay eggs that hatch, a bug crosses the screen every 2 minutes.

**Controls:** click = squash (with sound), double-click = big slam splat, hold **F8** = prey swarm the cursor, click an egg = crush it.

**Settings:** top of each file (`COUNTS`, `SOUND`, `PERCH`, `FOOTPRINTS`, `EGGS`, `CROSS_MINUTES`, `RESPAWN_SECONDS`, ...).

## v6 in detail

**Man:** follows the cursor and faces it. Left-click swings the weapon. **F9** switches SWORD -> HAMMER -> FISTS. Hits only land on bugs in front of him (the swing arc); bugs beside or behind are not hurt. Bigger bugs bite harder, small ones run away. Energy bar: at 0 he is knocked out for 6 s, then wakes with half energy.

**Fights:** big bugs pick fights with smaller or similar bugs and with the man. Hit points, random hit chance and damage, so the winner changes. Loser may flee when low. Winner carries off and eats the loser.

**Clutter removed:** eggs, footprints, window walking, crossings, swarm key. Max 7 bugs, a new one every 6-14 s.
