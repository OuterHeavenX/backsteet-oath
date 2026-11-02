# BACKSTREET OATH

An original 2D belt-scrolling action RPG set in Bellwether, a fictional late-1980s industrial river town.
Walk the streets with depth, punch, kick and jump, grab whatever's lying around, buy food and fighting
manuals, level up, and take your neighborhood back from the man in the gray coat.

**Version:** 1.0.0-rc3 (release candidate: feature-complete and tested by automated play; no human playtest yet)
**Engine:** Godot **4.7.2-stable** (official build), GDScript, Compatibility renderer (WebGL 2 / OpenGL 3.3)
**Platforms:** Web (HTML5, itch.io), Linux x86_64 (Steam Deck native), Windows x86_64 (built, not run-tested)

> Original game. All characters, story, art, music, sound and fonts were made for this project
> (generated procedurally by the scripts in `tools/`). Not affiliated with any other franchise.

## What's in the box
- Six connected districts, 20 street/arena rooms and 10 interiors; story-gated shortcuts and a River Line bus.
- Belt-scroller combat: ground plane + jump height, lane-aware hitboxes, combos, finishers, guard + perfect
  guard, running attacks, jump attacks, carry/throw dizzy enemies, 16 weapons in 6 behavior families.
- RPG layer: levels 1–20, five stats with a stat point per level (balanced auto-spend by default), 29 food and
  medicine items with capped permanent boosts, 10 purchasable techniques, weapon mastery, workbench upgrades.
- Six bosses (Duke, the Pike sisters, Otto, Jett, Captain Holt, Victor Rook with two phases) plus a story duel
  and a mini-boss; six side jobs; finished dialogue, ending, credits and postgame free roam.
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
../tools/package.sh 1.0.0-rc3        # versioned zips in release/
```
Regenerate assets (Python 3 + Pillow + numpy; fonttools for fonts; ffmpeg for audio):
```bash
python3 tools/art/gen_characters.py
python3 tools/art/gen_environments.py
python3 tools/art/gen_items_ui.py && python3 tools/art/gen_font.py
python3 tools/audio/gen_audio.py
```

## Tests
```bash
cd game
godot --headless res://tests/unit_tests.tscn                        # 574 checks: data, assets, stats, saves, combat geometry
godot --headless --fixed-fps 60 res://tests/feature_tests.tscn      # techniques, weapons, boss AI
godot --headless --fixed-fps 60 res://tests/quest_tests.tscn        # all six side jobs end-to-end
godot --headless --fixed-fps 60 res://tests/autoplay.tscn           # bot plays the whole campaign via input actions
```
Browser tests (Playwright + Chromium): `node tools/webtest/game_test.js <url> <outdir>` and `tools/webtest/touch_test.js`.

## Project layout
```
game/                 Godot project (project.godot, scenes/, scripts/, data/, assets/, tests/)
  data/*.json         rooms, encounters, dialogue, story, quests, items, weapons, skills, enemies, shops
  scripts/autoload/   Content, Settings, GameState, SaveService, Audio, InputPrompts, SceneFlow, Quests, Story
  scripts/core/       Actor, Player, Enemy, Boss, NPC, Room, Projectile, Pickup, Prop, FX
  scripts/ui/         HUD, dialogue, menus, touch controls
tools/                asset generators, packaging, browser tests
docs/                 art bible, tuning sheet, asset ledgers
```

Docs: [CONTROLS](CONTROLS.md) · [STEAM_DECK](STEAM_DECK.md) · [CHANGELOG](CHANGELOG.md) · [KNOWN_ISSUES](KNOWN_ISSUES.md) ·
[THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md) · [QA_REPORT](QA_REPORT.md) · [PLAYTHROUGH_REPORT](PLAYTHROUGH_REPORT.md) · [ITCH_PAGE](ITCH_PAGE.md) · [Tuning](docs/TUNING.md)
