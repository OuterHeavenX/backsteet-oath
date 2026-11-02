# Playthrough Report

**Build:** 1.1.0-rc1 (branch `claude/visual-upgrade`), Godot 4.7.2-stable, Normal difficulty. The detailed timings below come
from the 1.0.0-rc3 run. The visual upgrade changed no gameplay code, and its bot re-run is summarised in the next section.

## 1.1.0-rc1 re-run (full v2 art, same bot)
| Metric | rc3 | 1.1.0-rc1 |
|---|---|---|
| Outcome | complete | complete |
| In-game time | 47.4 min | 49.0 min |
| Knockouts (all recovered) | 13 | 15 |
| Enemies defeated | 270 | 271 |
| Level at the end | 14 | 14 |
| Script errors | 0 | 0 |

The small differences come from randomness: enemy AI and guard rolls. Attack timing, hitboxes and collision are
unchanged.
**Tester method:** automated bot (`game/tests/autoplay.tscn`), run headless at a fixed 60 ticks/s, so all times below are
**in-game seconds**. The bot drives the game only through InputMap actions, the same path as a keyboard or
controller. It uses no debug shortcuts, teleports, stat edits or cheats. It follows the main story only (no side jobs,
no shopping, no food), runs between objectives, guards when it sees a wind-up, and taps through dialogue.

> **No human playtest has been performed.** The bot verifies that the campaign can be completed end to end without
> cheats or grinding, and gives a mechanical timing reference. It cannot substantiate a human first-play duration.
> **The 60-minute campaign claim is therefore UNVERIFIED and is an estimate (see below).**

## Result (final run on the release candidate)
| Metric | Value |
|---|---|
| Outcome | Campaign completed: prologue → ending → credits hand-off |
| Total in-game time | **47.4 min** (2,845 s) |
| Combat | 36.3 min |
| Walking / exploring | 8.9 min |
| Dialogue (bot taps through instantly) | 0.9 min |
| Cutscene movement | 0.8 min |
| Room transitions | 0.15 min |
| Knockouts (retries) | 13 (all recovered via "retry"; no softlocks) |
| Enemies defeated | 270 |
| Level at the end | 14 (target range 10–14) |
| Cash at the end (never spent) | $1,101 |
| Script errors | 0 |

### Timestamps by story stage (in-game minutes:seconds, level, cumulative knockouts)
| Stage reached | Time | Level | KOs |
|---|---|---|---|
| Prologue: shake-down at the Lucky Spoon | 0:00 | 1 | 0 |
| Act I: find Mara | 0:18 | 1 | 0 |
| Chain Dogs / Duke | 0:53 | 1 | 0 |
| Canal Market (Duke defeated) | 3:22 | 3 | 1 |
| Pike sisters (after Jett duel) | 6:18 | 5 | 1 |
| Act II: Ironworks (Pikes defeated) | 8:32 | 6 | 2 |
| Foundry (Gus rescued) | 12:02 | 6 | 3 |
| Neon Mile (Otto defeated) | 14:46 | 7 | 3 |
| Rooftops (arcade back room) | 17:22 | 8 | 4 |
| Setback: return home (Jett defeated) | 20:08 | 9 | 5 |
| Act III: Floodgate (garage scene) | 25:33 | 10 | 6 |
| Dockside gate (alliance battle) | 31:06 | 10 | 7 |
| Rook's Warehouse (Holt defeated) | 36:34 | 12 | 9 |
| Rook (Eli found) | 45:20 | 13 | 12 |
| Epilogue (Rook defeated) | 47:15 | 14 | 13 |

Longest rooms (in-game seconds): Storage Floor 310, Dockside Gate 204, Marquee Strip 204, Foundry Floor 201,
Arcade Alley 192, Rooftops 177, Rail Spur 172, Pump Station Road 168, Pier Square 147, Brickrow Lane 139.

## Estimate for a human first playthrough (UNVERIFIED)
- The bot's 47 minutes include about 5–9 minutes lost to its 13 retries. It also never reads dialogue, shops,
  eats, explores interiors, reads the journal or stops to learn a new enemy.
- The main story has 225 lines of dialogue (2,618 words, about 10–13 minutes of reading). Shops, the journal
  and first-time navigation add more. These are not "active gameplay" by the brief's definition.
- **Estimate for mandatory active play:** 45–60 minutes. Reading and menus push the total session to about
  60–75 minutes. **Side jobs add an estimated 15–25 minutes:** six quests, including the timed Alley Cat Cup and
  three districts of parcel hunting.
- Because the 60-minute active-play target relies on this estimate, it is marked **unverified**. A timed human
  playtest is the remaining release gate (see KNOWN_ISSUES.md).

## Side-job verification
`game/tests/quest_tests.tscn` completes all six side jobs through real interactions: walking up to NPCs, the
Grab/Talk action, dialogue choices, the follower, the escort, the timed challenge, and breaking props. It checks
each reward and save/load persistence (23/23 checks pass). Combat inside those quests is short-circuited in that
test because combat is already covered by the campaign bot.

## Reproduce
```bash
cd game && godot --headless --fixed-fps 60 res://tests/autoplay.tscn   # writes user://autoplay_report.json
```
