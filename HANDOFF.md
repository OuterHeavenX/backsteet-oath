# HANDOFF — continuation notes

**Version:** 1.0.0-rc2 · **Branch:** `claude/backstreet-oath-build` · **Release binaries:** branch `release-builds`
(orphan branch holding the four zips + itch assets, because build outputs are git-ignored on the main branch).
**Engine:** Godot 4.7.2-stable. Fresh container: download `Godot_v4.7.2-stable_linux.x86_64.zip` and
`Godot_v4.7.2-stable_export_templates.tpz` from github.com/godotengine/godot-builds releases; put templates in
`~/.local/share/godot/export_templates/4.7.2.stable/`.

## Status
Complete and verified by automation:
- Engine, campaign, side quests, ending/credits/postgame, UI, saves, settings, touch.
- All assets are original and procedurally generated (see `tools/`).
- Tests pass: unit 574/574, features 65/65, quests 23/23, and the autoplay bot completes the campaign.
- Web, Linux and Windows exports and versioned zips are built. The web and Linux zips were checked after extraction.

## Open items (release gates)
1. **Human timed playtest:** needed to confirm the 60-minute active-play target. The bot measured 47.4 in-game
   minutes; see PLAYTHROUGH_REPORT.md.
2. **Real-device checks:** Steam Deck, a phone browser, physical gamepads, and the Windows exe.
3. **itch.io upload:** blocked here by network policy. Follow the steps in ITCH_PAGE.md.
4. Optional polish: night-palette props, animated drawbridge, more facade variety (see KNOWN_ISSUES.md).

## Commands
```bash
cd game
godot --headless --import
godot --headless res://tests/unit_tests.tscn
godot --headless --fixed-fps 60 res://tests/feature_tests.tscn
godot --headless --fixed-fps 60 res://tests/quest_tests.tscn
godot --headless --fixed-fps 60 res://tests/autoplay.tscn        # report: user://autoplay_report.json
cd .. && python3 tools/package.py 1.0.0-rc2                      # exports + zips into release/
SHOT_ROOM=oq_kettle SHOT_STEPS="wait:2;shot:x" tools/shots.sh /tmp/shots   # screenshots via Xvfb
node tools/webtest/game_test.js http://127.0.0.1:8765/web/index.html?bo_debug=1 /tmp/out
```
Debug builds only: F1 overlay, F2 +XP, F3 next room, F4 spawn enemies, F5 heal, F6 delete slot 3 (`scripts/ui/debug_overlay.gd`).

## Where things live
- Content: `game/data/*.json`. Story beats: `game/scripts/autoload/story.gd`. Combat: `game/scripts/core/actor.gd`, `player.gd`, `enemy.gd`, `boss.gd`.
- Rooms: layout in `data/rooms.json`; gameplay (waves, events, NPCs, pickups) in `data/encounters.json`.
- To add a room, add it to both files, then regenerate art with `tools/art/gen_environments.py --rooms <id>`.
