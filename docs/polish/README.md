# Gameplay, presentation and performance polish (1.4.0-rc1)

Branch `claude/gameplay-polish`, built on the 1.3.0-rc1 tree. Not merged, not published.

| Read this | For |
|---|---|
| [CHANGES.md](CHANGES.md) | What changed for the player and why each change was chosen |
| [VALIDATION_REPORT.md](VALIDATION_REPORT.md) | Exact commands, results, regressions fixed, and everything that was not verified |
| [BUILD_AND_LAUNCH.md](BUILD_AND_LAUNCH.md) | How to run, build and launch; package sizes and checksums; smoke tests on the packages |
| [PERF_REPORT.md](PERF_REPORT.md) | Frame-time profile, the two optimisations, web size and load (software rendering only) |
| [SAVE_AND_NGPLUS_NOTES.md](SAVE_AND_NGPLUS_NOTES.md) | Save compatibility with 1.3 and New Game+ behaviour |
| [PLAYTEST_KIT.md](PLAYTEST_KIT.md) | Five-person first-time playtest: facilitator script and observation sheet (not yet run) |
| [FOLLOW_UPS.md](FOLLOW_UPS.md) | Hypotheses that need player evidence, in priority order |
| [ECONOMY_REVIEW.md](ECONOMY_REVIEW.md) | Income against prices; recommendations, no retuning |
| [ANIM_AUDIT.md](ANIM_AUDIT.md) | Attack animation frames against hit timing |
| [CHECKLIST.md](CHECKLIST.md) | Done / pending list for resuming the work |

Evidence:
- `before/` and `after/`: the same fixed capture set on 1.3.0-rc1 and on this build (stills and two clips each);
  `compare/` has them side by side; `after/new/` has one still per new feature.
- `baseline/`: campaign bot reports for every run quoted in the validation report, and the attack-cue sound analysis.
- `perf/`: profiling data and the bloom A/B images.
- Tools: `tools/capture_polish.sh`, `tools/anim_audit.py`, `tools/perf/`, `tools/webtest/`.
