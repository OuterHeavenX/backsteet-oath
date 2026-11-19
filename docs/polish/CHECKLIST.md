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
- [ ] Combat camera prototype (tunable), Nico keyline, lane/ground cues, usable-object cue, tells.
### C. Decisions and consequences
- [ ] Rework "Duke's lieutenants" (Chain Lot c3); Old Quarter changes after Duke.

## Campaign
- [ ] Encounter pacing from measurements; Kowal's work lights; late-game difficulty review.
- [ ] Neighbourhood remembers: mural, radio, residents, gang defeats, finale favours.
- [ ] Progression previews, manual preview, build guidance, economy review; NG+ composition.

## Performance / load / audio
- [ ] Perf agent (separate worktree) report in `docs/polish/PERF_REPORT.md`; merge its branch.
- [ ] Tell sounds (heavy / grab / guard-break). Not verifiable by ear in this container.

## Validation and deliverables
- [ ] All suites + bot + browser checks after the last change.
- [ ] Playable export + launch instructions, after captures, validation report, playtest kit, follow-ups.
