# Known Issues & Limitations (1.0.0-rc2)

No known blocker or major bugs remain in the main campaign or on the tested platforms. The automated campaign
run, feature tests, quest tests and unit tests all pass.

## Release gates still open
- **Human playtest not performed.** The campaign duration (target: 60+ minutes of active play) is an estimate
  based on an automated run of 47.4 in-game minutes; see PLAYTHROUGH_REPORT.md. This is the reason for the
  `-rc` (release candidate) label.
- **Not tested on physical devices:** Steam Deck hardware, iPhone/Safari, Android phones, real gamepads. Desktop
  Chromium (software WebGL) and mobile emulation were tested; real-device behavior may differ.
- **Windows build** is exported but was not launched (no Windows machine available).
- **itch.io upload not performed:** this environment's network policy blocks itch.io and the butler download
  host. See ITCH_PAGE.md for the exact upload steps.

## Minor issues
- Difficulty spikes in the warehouse for players who never buy food or manuals. The bot (which never shops) was
  knocked out 13 times across the campaign. Relaxed difficulty and food are the intended relief.
- Background art is static, so the Pier Square drawbridge still looks raised after it opens.
- Props in the night districts are tinted by the engine rather than drawn with night palettes. A few props still
  look slightly bright.
- Sprite faces are tiny at 1× (2×2 eyes), so expressions read mostly through portraits.
- Some icons are only moderately clear at 1× (leash, champion wraps, green tea).
- Web performance was measured only under software rendering on a shared 4-core VM: 29–40 FPS, worst frame 60–140 ms
  while another process ran. GPU-accelerated browsers should do much better, but this is unmeasured.
- Audio was synthesized and checked numerically (levels, seams, loudness) but not listened to by a human.
- Steam Cloud does not sync saves (the game is added as a non-Steam shortcut).
- Browser saves depend on the browser keeping site storage. Private windows do not persist. Use Export.
