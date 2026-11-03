# BACKSTREET OATH

An original 2D belt-scrolling action RPG set in Bellwether, a fictional late-1980s industrial river town.
Walk the streets with depth, punch, kick and jump, grab whatever's lying around, buy food and fighting
manuals, level up, and take your neighborhood back from the man in the gray coat.

**Version:** 1.3.0-rc1 (visual upgrade of 1.0.0-rc3/rc4; feature-complete and tested by automated play; no human playtest yet)
**Engine:** Godot **4.7.2-stable** (official build), GDScript, Compatibility renderer (WebGL 2 / OpenGL 3.3)
**Platforms:** Web (HTML5, itch.io), Linux x86_64 (Steam Deck native), Windows x86_64 (built, not run-tested)

> Original game. All characters, story, art, music and sound were made for this project (generated procedurally by
> the scripts in `tools/`); the only third-party assets are the SIL OFL fonts Bungee and Barlow.
> Not affiliated with any other franchise.

## What's in the box
- Inked, cel-shaded 2D art at 2× density: fully animated cast of 60, 30 layered and lit rooms, material-specific
  combat effects and staged story scenes. See [docs/visual/UPGRADE_REPORT.md](docs/visual/UPGRADE_REPORT.md).
- Six connected districts plus the Underline subway: 23 street/arena rooms and 10 interiors, story-gated shortcuts and a River Line bus.
- Belt-scroller combat: ground plane + jump height, lane-aware hitboxes, combos, finishers, guard + perfect
  guard, running attacks, jump attacks, carry/throw dizzy enemies, 16 weapons in 6 behavior families.
- RPG layer: levels 1–20, five stats with a stat point per level (balanced auto-spend by default), 29 food and
  medicine items with capped permanent boosts, 10 purchasable techniques, weapon mastery, workbench upgrades.
- Seven bosses (Duke, the Pike sisters, Otto, Jett, Ruth Kowal, Captain Holt, Victor Rook with two phases) plus a story
  duel and a mini-boss; ten side jobs; Benny's nine-bout ladder; New Game+; finished dialogue, ending, credits and
  postgame free roam.
- 3 save slots with backup and corruption recovery, JSON export/import, keyboard/controller rebinding,
  touch controls, accessibility options (text size and speed, shake/flash, Relaxed difficulty).

## Play
- **Web:** open `index.html` from the web zip on any static web server (itch.io: upload the zip as an HTML game).
- **Phones and tablets (browser):** landscape, touch controls appear automatically. Tablets get a control deck under the street.
- **Linux / Steam Deck:** unzip, run `./start.sh` (or `BackstreetOath.x86_64`). See [STEAM_DECK.md](STEAM_DECK.md).
- **Windows:** unzip, run `BackstreetOath.exe`.
- Controls: [CONTROLS.md](CONTROLS.md).

## Save locations
| Platform | Location |
|---|---|
| Linux | `~/.local/share/godot/app_userdata/Backstreet Oath/` |
| Windows | `%APPDATA%\Godot\app_userdata\Backstreet Oath\` |
| Web | Browser storage (IndexedDB) for the page's origin. Cleared by private mode or "clear site data". Use **Manage Saves → Export** to keep a backup file. |

Files: `save_1..3.json` (+ `.bak` previous save), `settings.cfg`. Desktop import: put a file at `user://import/save.json` and choose Import.

## Build from source
Requires Godot 4.7.2-stable and its export templates (`~/.local/share/godot/export_templates/4.7.2.stable/`).
```bash
cd game
godot --headless --import
godot --headless --export-release "Web" ../build/web/index.html
godot --headless --export-release "Linux" ../build/linux/BackstreetOath.x86_64
godot --headless --export-release "Windows" ../build/windows/BackstreetOath.exe
python3 ../tools/package.py 1.3.0-rc1   # versioned zips in release/
```
Regenerate the v2 art (Python 3 + Pillow + numpy; `pip install imagequant` for the final optimisation step):
```bash
python3 tools/art2/chars/gen_chars2.py --all --portraits     # characters + portraits (~35 min)
python3 tools/art2/env/gen_env2.py --all                     # rooms, district layers, props
python3 tools/art2/ui/gen_fx.py && python3 tools/art2/ui/gen_items.py && python3 tools/art2/ui/gen_ui.py \
  && python3 tools/art2/ui/gen_ui_extra.py && python3 tools/art2/ui/gen_title.py && python3 tools/art2/ui/gen_icons.py
python3 tools/art2/optimize_textures.py                      # lossless palette quantisation for the web download
python3 tools/audio/gen_audio.py                             # music + sound effects
```
The asset contract the engine reads is `docs/visual/ASSET_CONTRACT_V2.md`. The rc3 generators in `tools/art/` and
their output are kept as fallbacks (excluded from exports).

## Tests
```bash
cd game
godot --headless res://tests/unit_tests.tscn                        # 7,775 checks: data, assets (incl. v2 contract), stats, saves, combat
godot --headless --fixed-fps 60 res://tests/feature_tests.tscn      # techniques, weapons, boss AI
godot --headless --fixed-fps 60 res://tests/quest_tests.tscn        # the original six side jobs end-to-end
godot --headless --fixed-fps 60 res://tests/expansion_tests.tscn    # 1.2: Underline boss path, 4 new side jobs, ladder, NG+
godot --headless --fixed-fps 60 res://tests/autoplay.tscn           # bot plays the whole campaign via input actions
```
Browser tests (Playwright + Chromium): `node tools/webtest/game_test.js <url> <outdir>`, `tools/webtest/touch_test.js` and
`tools/webtest/audio_test.js` (measures real Web Audio output). Visual checks: `tools/capture_set.sh <dir>` (fixed
before/after shots), `tools/capture_footage.sh <out.mp4> kettle|duke|diner`, `game/tests/perf.tscn` (frame times),
`game/tests/title_shot.tscn`. Native build input: `tools/nativetest/xkeys.py`.

## Project layout
```
game/                 Godot project (project.godot, scenes/, scripts/, data/, assets/, tests/)
  data/*.json         rooms, encounters, dialogue, story, quests, items, weapons, skills, enemies, shops
  scripts/autoload/   Content, Settings, GameState, SaveService, Audio, InputPrompts, SceneFlow, Quests, Story
  scripts/core/       Actor, Player, Enemy, Boss, NPC, Room, Projectile, Pickup, Prop, FX
  scripts/ui/         HUD, dialogue, menus, touch controls
tools/                asset generators, packaging, browser tests
docs/                 art direction, asset contract, upgrade report, before/after (docs/visual/), ledgers
```

Docs: [CONTROLS](CONTROLS.md) · [STEAM_DECK](STEAM_DECK.md) · [CHANGELOG](CHANGELOG.md) · [KNOWN_ISSUES](KNOWN_ISSUES.md) ·
[THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md) · [QA_REPORT](QA_REPORT.md) · [PLAYTHROUGH_REPORT](PLAYTHROUGH_REPORT.md) · [ITCH_PAGE](ITCH_PAGE.md) · [Tuning](docs/TUNING.md) ·
[ART_DIRECTION](docs/ART_DIRECTION.md) · [UPGRADE_REPORT](docs/visual/UPGRADE_REPORT.md)
