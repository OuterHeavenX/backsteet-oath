# Save compatibility and New Game+ notes

## Save format
- **Unchanged.** `SAVE_VERSION` is still 2. No migration was needed and none was added.
- Everything new is stored in places the format already had:
  - story flags: `tutor_v2`, `tip_<id>` (1 armed, 2 learned, 3 skipped), `tipt_skill_<id>` (seconds a reminder has
    been shown), `dot_meal_done`, `benny_lesson_done`, `calm_seen_<district>`, `storage_run_done`;
  - stats: `pt` (only if the opt-in playtest log is on).
- Flags are free-form in the save, so a 1.4 save opened in 1.3 would simply ignore them. That direction was not
  tested and is not supported.

## Saves made before this change (1.3.0-rc1 and earlier)
Tested with 13 real 1.3.0-rc1 saves, produced by running the 1.3.0-rc1 bot in an isolated data folder, one per
story stage plus a completed game (`game/tests/fixtures/saves_1_3/`, `game/tests/oldsave_tests.tscn`, 120 checks).

| Area | What an older save gets |
|---|---|
| Loading | Accepted by the validator; level, cash, max HP and techniques are unchanged; the world loads in the saved room. |
| Opening tips | None are armed. The player is never sent back through the opening. |
| Dot's plate, Benny's lesson | Offered only if the save has not beaten Duke yet. Past Duke, Dot and Benny behave as in 1.3. If Shoulder Charge is already owned, Benny says so and nothing is granted. |
| Contextual one-time tips (blocker, unblockable attack, Kowal's lights) | Shown the first time the situation comes up, like on a new game. Control hints: Off hides them. |
| Calm districts | Follow the bosses already beaten: an older save past Duke finds the Old Quarter without patrols and with residents, and sees the "what changed" card once on its next street visit there. Same for other districts (thinner, rarer patrols). |
| Storage Floor | A save that has not yet rescued Eli gets the crane and the shutter run. A save past the rescue never sees the run. |
| Kowal | A save that has not beaten her gets the work-light fight. Nothing changes for saves past her. |
| Reworked waves | Wave ids were kept, so cleared-wave memory in older saves still applies. Storage Floor's `st4` no longer exists; a save that had cleared it just carries an unused entry. |
| Completed saves | Postgame works as before; New Game+ can be started (tested from the real completed 1.3 save). |

## Retries, save/load and room changes inside this build
Covered by `opening_tests` and `campaign_tests`:
- A tip that was learned or skipped stays that way through save/load, defeat-and-retry and re-entering a room;
  re-arming never brings it back.
- Dot's plate and Benny's technique are flagged and saved before anything is handed over, so quitting at any
  point cannot grant them twice.
- Sparring: partners cannot be knocked out; a sparring knockout shows no defeat screen, costs no cash and is not
  counted as a knockout; the room is left unlocked and empty afterwards.
- Dying or leaving during the shutter run clears the counter and leaves the run for the next visit; the bonus is
  paid once.
- A boss room starts its fight once only (the second-start bug is fixed and tested).
- No counter (cup, ladder, shutter, lights) survives a room change.

## New Game+
| Topic | Behaviour |
|---|---|
| Reset rules | `start_new_game_plus` clears flags, quests and bosses as before. That also resets the new flags: Dot's plate and Benny's offer come round again each cycle (Benny cannot duplicate an owned technique), districts are gang-run again and calm down again as bosses fall, the shutter run returns. |
| Opening tips | Not armed on cycle 1 and later; the Dogs do not wait. |
| Scaling | Enemy HP, power and rewards use `min(cycle, 3)`. Cycle 1: HP x1.35, power x1.25, boss HP x1.4, boss power x1.15, rewards x1.25. From cycle 3 on: HP x2.05, power x1.75, boss HP x2.2, boss power x1.45, rewards x1.75. In 1.3 these kept growing to cycle 9 (HP x4.15). |
| Composition | Each wave gains the archetype it lacks: a thrower, else a blocker (which covers a thrower if there is one), else a flanker, else a heavy. From cycle 2 one brawler becomes a weapon fighter. Named quest fighters are never changed. |
| Limits | Simultaneous attackers (2, or 1 on Relaxed and in boss fights) and the on-screen cap are unchanged; measured in a real New Game+ wave. |
| Bosses | Same attacks and tells. Duke and Sabine call help at 75/50/25% (Duke's help includes a thrower); Otto speeds up at 65%; Jett evades more often; Kowal starts the lights at 70% and returns to them sooner; Rook changes phase at 60% and his crates fall 25% more often. |
| Max-level players | XP is ignored at level 20 as before; the shutter bonus still pays cash. |
| Tunables | `game/data/tuning.json` > `ngplus`. |

**Not measured:** how New Game+ feels or how long it takes. The bot was not run in New Game+, and the cap at
cycle 3 is arithmetic (the player's damage stops growing at level 20 and the food caps), not a playtest result.
