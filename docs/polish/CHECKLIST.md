# Gameplay polish: working checklist

Branch `claude/gameplay-polish`, based on `origin/main` 4b22770 (1.3.0-rc1 tree). Update this file with every
checkpoint so a later session can resume without repeating work.

## Baseline (done)
- [x] Suites on 1.3.0-rc1: unit 8568, features 67, quests 23, expansion 37, all passing.
- [x] Bot campaign on 1.3.0-rc1: 55.9 in-game min, 298 enemies, 18 knockouts, level 14
      (`docs/polish/baseline/bot_report_1.3.0-rc1.json`).
- [x] Before stills and clips: `docs/polish/before/` (re-run with `tools/capture_polish.sh <dir>`).

## Milestone 1: Old Quarter through Duke
### A. Teach through play
- [x] `Tutor` (game/scripts/core/tutor.gd): one tip at a time, completes on the real action, skippable from Pause,
      state in save flags (`tip_<id>`), text follows the input device.
- [x] Opening fight rewritten around tips (move, combo, guard, throw); never gates progress.
- [x] Dot's plate on the house (once, saved immediately, full-health and capped cases handled).
- [x] Benny's free Shoulder Charge + two sparring rounds (runner, then a blocker); partners cannot be knocked out,
      no XP/cash, knockout has no penalty; "Spar a round" stays in his menu before Duke.
- [x] Fighting tips page in the pause menu; technique reminders for newly learned moves.
- [x] Tests: `game/tests/opening_tests.tscn`.
### B. Readability
- [x] Combat camera (tunable, Settings > Combat camera), Nico keyline, lane rings, usable-object cues
      (Settings > Combat guides), three attack tells with their own shape/tint/sound, ground zones.
- [x] Animation timing audit (`tools/anim_audit.py`, `docs/polish/ANIM_AUDIT.md`), wind-up flicker fix, lean.
### C. Decisions and consequences
- [x] "Duke's lieutenants" (Chain Lot c3): blocker covers the thrower; crate and trash can in reach.
- [x] Old Quarter after Duke: aftermath scene, residents, no patrols, passers-by, one-time card.
- [x] Fix: second boss start in the pause before a defeat scene.

## Campaign
- [x] District calm system (`GameState.district_calm`, `story.json` districts).
- [x] Kowal's work lights; Storage Floor crane + shutter run; `game/tests/campaign_tests.tscn`.
- [x] New Game+: capped scaling, composition changes, boss variations (`tuning.json` ngplus).
- [x] Late-game difficulty measured with shopping/non-shopping/Relaxed bots (no enemy numbers changed).
- [ ] Neighbourhood remembers (mural, radio, residents, finale): agent branch `worktree-agent-a534d54f8cc06208f`.
      Stopped once at a usage limit; resumed. Merge when it reports, or finish from its WIP commit.
- [ ] Progression previews, manual preview, build guidance, economy review: agent branch
      `worktree-agent-ac4bf485523b97fc1` (same situation).

## Performance / load / audio
- [ ] Perf agent branch `worktree-agent-addcc4dc8b9b7bbf7` (harness committed; optimisation and report pending).
- [x] Tell sounds (heavy / unblockable / guard-break): generated, numerically distinct, NOT heard by anyone.

## Validation and deliverables
- [x] Opt-in playtest log + `PLAYTEST_KIT.md`; `CHANGES.md`, `FOLLOW_UPS.md`, `SAVE_AND_NGPLUS_NOTES.md`.
- [x] Real 1.3.0-rc1 saves load (`game/tests/oldsave_tests.tscn`, 13 fixtures).
- [x] Version 1.4.0-rc1, changelog. Branch pushed to origin (no PR, no merge, no release).
- [ ] After merging the agent branches: all suites, bot, web/Linux export + browser checks, after captures,
      `VALIDATION_REPORT.md`, final pass over `CHANGES.md` sections 5 and README/KNOWN_ISSUES/HANDOFF.

## Suites (run from `game/`)
`godot --headless res://tests/unit_tests.tscn`, then with `--fixed-fps 60`: `feature_tests`, `quest_tests`,
`expansion_tests`, `opening_tests`, `campaign_tests`, `oldsave_tests` (`.tscn`). Bot: `tests/autoplay.tscn` run
under `script -q -c "..." /dev/null` (set `AUTOPLAY_REPORT`, optional `AUTOPLAY_SHOP=some|all`, `AUTOPLAY_DIFF=relaxed`).
