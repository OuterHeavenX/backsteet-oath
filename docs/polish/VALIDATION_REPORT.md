# Validation report: 1.4.0-rc1 (gameplay, presentation and performance polish)

Branch `claude/gameplay-polish`. Nothing here was checked by a person playing the game, nothing was listened to,
and every frame was drawn by a software renderer. Those limits are listed in full at the end.

## Environment
| | |
|---|---|
| Engine | Godot 4.7.2-stable (official build `ed1daf0bf`), Compatibility renderer |
| Machine | Linux container, 4 virtual CPUs, no GPU, no audio device |
| Rendering | Mesa llvmpipe under Xvfb at 1280x720 (native); headless Chromium with SwiftShader (web) |
| Base | `origin/main` 4b22770 (the 1.3.0-rc1 tree) |

## Automated suites
Run from `game/`, on the merged tree (commit `d212c56`):

```
godot --headless res://tests/unit_tests.tscn
godot --headless --fixed-fps 60 res://tests/<suite>.tscn
```

| Suite | 1.3.0-rc1 | This build | What it covers |
|---|---|---|---|
| `unit_tests` | 8,568 | 8,573 passed | data validity, combat maths, save round-trips |
| `feature_tests` | 67 | 67 passed | every technique, weapon family and boss AI |
| `quest_tests` | 23 | 23 passed | side jobs |
| `expansion_tests` | 37 | 37 passed (see note) | Underline, ladder, later side jobs, New Game+ |
| `opening_tests` | new | 163 passed | tips, Dot's plate, Benny's lesson and sparring, camera, guides, tells, lieutenants, Duke and the street afterwards, playtest log |
| `campaign_tests` | new | 64 passed | Kowal's lights, Storage Floor crane and shutter run, New Game+ |
| `consequence_tests` | new | 139 passed | mural, radio discount, residents, ending guests, with and without each side job |
| `progression_tests` | new | 418 passed | every preview against the real result, prices, manual preview |
| `oldsave_tests` | new | 120 passed | 13 real 1.3.0-rc1 saves |

**Note on `expansion_tests`:** three linked checks in the "Heavy Thumb" weights job failed in 2 of about 30 runs
and passed in the rest. See "Open item" below.

## Campaign bot
`tests/autoplay.tscn` plays the whole campaign with a simple fighting routine. It proves a completion path and
gives rough pacing; it is not a person, does not use techniques well, and by default never shops.

```
AUTOPLAY_REPORT=out.json script -q -c "godot --headless --fixed-fps 60 res://tests/autoplay.tscn" /dev/null
# optional: AUTOPLAY_SHOP=some|all   AUTOPLAY_DIFF=relaxed
```

| Run | Result | In-game min | Knockouts | Enemies | Level | Script errors |
|---|---|---|---|---|---|---|
| 1.3.0-rc1 baseline | complete | 55.9 | 18 | 298 | 14 | 0 |
| after the opening milestone | complete | 47.3 | 15 | 254 | 14 | 0 |
| campaign changes, run 1 | complete | 51.5 | 17 | 269 | 14 | 0 |
| campaign changes, run 2 | complete | 49.6 | 15 | 261 | 14 | 0 |
| final merged tree | complete | 54.5 | 19 | 250 | 13 | 0 |
| spends half its cash on food each stage | complete | 38.5 | 4 | 241 | 13 | 0 |
| Relaxed difficulty, no shopping | complete | 43.7 | 4 | 237 | 13 | 0 |

- Runs differ by several minutes and a few knockouts from random AI alone, so single-run differences of that size
  mean nothing. The reports are in `docs/polish/baseline/`.
- What the numbers do support: the non-shopping bot is no worse off than in 1.3 (15 to 19 knockouts against 18);
  it fights about 30 to 50 fewer enemies because beaten gangs patrol less; and a little food changes the late
  game completely (4 knockouts for $254).
- What they do not support: any claim about human difficulty, enjoyment or playing time.

## Regressions found during the work and fixed
| Problem | Cause | Fix |
|---|---|---|
| Two Dukes on screen after beating him | Older bug: the boss flag is saved after the defeat scene, so the room could start the fight again in the pause before it if the player stood past the trigger line | `Room.boss_done`, plus a test that stands past the line |
| `expansion_tests` "Kowal fight starts" failed after that fix | The test helper floored bosses while walking and only passed because of the second boss start | Helper now leaves bosses to boss tests |
| Kowal's Moles arrived much later than designed | Her darkness clock only advanced while she was idle | Clocks run every tick |
| Kowal walked on the spot when the player stood between her and a light | Body-blocking | She steps down a lane and goes round |
| Enemy bottles destroyed the crate meant for the player | Any projectile broke crates | Only the player's throws do |
| A fighter told to wait kept its attack token, so nobody else could attack | Token never released | Released when held |
| Pause menu ran off the screen with Large text | Two new entries | One "Help & tips" entry |
| Objective text collided with the LIGHTS / SHUTTER counter on phones; boss bar ran under the touch buttons | Layout | Counter replaces the objective line; narrower boss bar on phones |
| Timed hints stayed up over conversations | No scene check | Dropped when a scene starts |
| Two new test checks failed about one run in ten | A second enemy could interrupt the scripted combo; a crane cycle could be missed | Retry the combo; allow two cycles |

## Checks driven by scripted input (not by a person)
Done with the screenshot harness (`tools/shots.sh`, real input events into the real game) and looked at:
- New game opening: tips appear one at a time, the Dogs wait, tips clear on the action, with keyboard labels,
  touch labels and Large text.
- Tells: all three badges, body tint and ground zone (`docs/polish/after/new/n02` to `n05`).
- Lieutenants fight, Duke's defeat scene and the street afterwards.
- Kowal: lit vault, lights contest, switching a light on, on desktop and touch layouts.
- Storage Floor crane and the shutter countdown.
- Shop previews, manual preview, Status previews, Build ideas, pharmacy discount; mural before and after;
  ending with guests.
- Fixed before/after set: `docs/polish/compare/` (12 side-by-side sheets) and `docs/polish/after/clip_*.mp4`
  against `docs/polish/before/clip_*.mp4`.

Covered by tests rather than by looking: skipping tips, defeat and retry mid-tutorial, save/load at each step,
sparring knockout, device switching, older saves at every story stage, completed and New Game+ saves.

## Packaged builds
See `docs/polish/BUILD_AND_LAUNCH.md` for sizes, checksums, launch steps and the smoke tests run on the packaged
files.

## Open item
**Intermittent `expansion_tests` failure (weights job).** In 2 of about 30 runs the step "inspector drops weights
in cm_pier" failed and the two checks that depend on it followed. Both failures happened while other heavy jobs
were running on the same machine; 22 consecutive runs since then passed. The test is frame-stepped, so machine
load should not matter, which means the cause is not understood. Diagnostics were added to that step so the next
failure prints the room state. It is listed here rather than hidden: treat a failure of that step as "re-run and
read the DIAG line", not as proof of a new bug or of none.

## Not verified
| Area | State | What a person needs to do |
|---|---|---|
| Human play | Nobody has played this build. | Run `PLAYTEST_KIT.md` with five first-time players. |
| Audio | No audio device here. Nothing was heard: not the mix, not the music, not the three new attack cues. | Play with speakers; kit question 7; listen in fights, shops, hubs, a boss and a room change. |
| Real GPU performance | Software rendering only. | Settings > Show FPS on Kettle Street in a fight, on Marquee Strip, and in Kowal's dark phase; note the device. The end-of-run card shows session averages. Details in `PERF_REPORT.md`. |
| The new bloom pass on real GPU drivers | Seen on two software renderers only (llvmpipe, SwiftShader). | Compare a street with Settings > Colour grade & bloom on and off; if the picture looks wrong with it on, report the device and leave it off. |
| Steam Deck, phones, tablets, real gamepads | Not available. Touch was emulated. | Launch steps in `BUILD_AND_LAUNCH.md` and `STEAM_DECK.md`. |
| Windows | Exported, never launched. | Run `BackstreetOath.exe`. |
| Browsers other than headless Chromium | Not tested. | Open the web build in Safari and Firefox. |
| New Game+ in play | Tested for correctness only. | Start New Game+ from a completed save. |
