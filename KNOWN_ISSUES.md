# Known Issues & Limitations (1.4.0-rc1)

No known blocker or major bugs remain in the main campaign or on the tested platforms. The automated campaign
run and every test suite pass on this build (see `docs/polish/VALIDATION_REPORT.md`).

## Release gates still open
- **Human playtest not performed.** Nobody has played 1.4.0-rc1, or any version, start to finish. A five-person
  first-time test is prepared in `docs/polish/PLAYTEST_KIT.md`. Campaign length for a person is unknown: the bot
  takes 47 to 52 in-game minutes without shopping (it was 56 in 1.3; this pass removed some repeated street
  fights on purpose). This is the reason for the `-rc` label.
- **The 1.4 design changes are hypotheses.** The closer fight camera, the tips, the attack tells, Kowal's lights
  and the Storage Floor run are tested for correctness, not for whether people understand or enjoy them. See
  `docs/polish/FOLLOW_UPS.md`.
- **No GPU performance measurement yet.** Every number so far comes from a GPU-less machine using software
  rendering (see `docs/polish/PERF_REPORT.md`). Players can report real numbers with Settings → Show FPS or from
  the run summary card. *Effects: Reduced* and *Colour grade & bloom: Off* are the fallbacks for slow devices.
- **Audio has not been listened to.** This includes the three new attack cues, which are only known to be
  numerically different from each other.
- **Not tested on physical devices:** Steam Deck hardware, iPhone/Safari, Android phones and real gamepads. Desktop
  Chromium (software WebGL) and touch emulation were tested; real devices may behave differently.
- **Windows build** is exported but was not launched (no Windows machine available).
- **Not published.** 1.4.0-rc1 exists only on the `claude/gameplay-polish` branch; the itch.io page and the
  `release-builds` branch still hold 1.3.0-rc1.

## Visual limitations (honest ceiling)
- All art is procedural vector illustration from this project's generators, not hand-painted.
  - Hands, anatomy and cloth are simplified.
  - All fighters share one rig, and archetypes share attack animations.
  - Distant skylines are flat silhouettes, and some floors are mild patterns.
- `jump_punch` and the from-behind hit read weaker than the other animations.
- Old Quarter skies are a cooler dusk (violet above an amber horizon) than the art-direction target's amber.
- The web download is 74.5 MB in 1.3 (56.7 MB in 1.1, about half that in rc3) because of the 2× art and the 1.3
  background layers. The Windows zip (102.3 MB) is split into two parts on the release-builds branch because of
  GitHub's 100 MB file limit.

## Minor issues
- Difficulty rises from the Neon Mile on for players who never buy food or manuals: a bot that never shops is
  knocked out 15 to 17 times, one that spends half its cash on food 4 times, and one on Relaxed 4 times. Food,
  Dot's free plate and Relaxed difficulty are the intended relief; enemy numbers were not changed.
- Permanent food bonuses are cheap relative to income (about $250 buys all of them). Whether that is a problem
  needs player evidence; see `docs/polish/ECONOMY_REVIEW.md`.
- The heavy's grab has no wind-up animation frames; it relies on a held pose, a lean and the purple tell.
- The audio mix has not been listened to by a human, and this container has no audio device. Since rc4, browser
  output is verified numerically by measuring Web Audio RMS. The new material sound layers on impacts are mixed
  quietly for that reason.
- Steam Cloud does not sync saves (the game is added as a non-Steam shortcut).
- Browser saves depend on the browser keeping site storage. Private windows do not persist. Use Export.
