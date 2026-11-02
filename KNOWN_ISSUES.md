# Known Issues & Limitations (1.1.0-rc2)

No known blocker or major bugs remain in the main campaign or on the tested platforms. The automated campaign
run, feature tests, quest tests and unit tests all pass on the visual-upgrade build.

## Release gates still open
- **Human playtest not performed.** The campaign duration (target: 60+ minutes of active play) is an estimate
  based on automated runs of 47–49 in-game minutes; see PLAYTHROUGH_REPORT.md. This is the reason for the `-rc`
  label.
- **No GPU performance measurement yet.** Players can now report it from the run summary card or with Settings → Show FPS. Every measurement so far ran on a GPU-less VM using software rendering, at
  28–47 FPS for 1.1.0 against 117–140 FPS for rc4 (see docs/visual/UPGRADE_REPORT.md). The new art renders at
  window resolution, so it needs about 4× the pixel fill of rc3. Real GPUs are expected to hold 60 FPS, but nobody
  has measured that, including on a Steam Deck. *Effects: Reduced* is the fallback for slow devices.
- **Not tested on physical devices:** Steam Deck hardware, iPhone/Safari, Android phones and real gamepads. Desktop
  Chromium (software WebGL) and mobile emulation were tested; real devices may behave differently.
- **Windows build** is exported but was not launched (no Windows machine available).
- **itch.io upload not performed:** this environment's network policy blocks itch.io and the butler download
  host. See ITCH_PAGE.md for the exact upload steps.

## Visual limitations (honest ceiling)
- All art is procedural vector illustration from this project's generators, not hand-painted.
  - Hands, anatomy and cloth are simplified.
  - All fighters share one rig, and archetypes share attack animations.
  - Distant skylines are flat silhouettes, and some floors are mild patterns.
- `jump_punch` and the from-behind hit read weaker than the other animations.
- Old Quarter skies are a cooler dusk (violet above an amber horizon) than the art-direction target's amber.
- The web download is 56.7 MB, about twice rc3's, because of the 2× art.

## Minor issues
- Difficulty spikes in the warehouse for players who never buy food or manuals. The bot never shops, and it was
  knocked out 15 times across the campaign. Relaxed difficulty and food are the intended relief.
- The audio mix has not been listened to by a human, and this container has no audio device. Since rc4, browser
  output is verified numerically by measuring Web Audio RMS. The new material sound layers on impacts are mixed
  quietly for that reason.
- Steam Cloud does not sync saves (the game is added as a non-Steam shortcut).
- Browser saves depend on the browser keeping site storage. Private windows do not persist. Use Export.
