# HANDOFF — continuation notes

**Branch:** `claude/backstreet-oath-build` · **Engine:** Godot 4.7.2-stable at `/usr/local/bin/godot` (download from github.com/godotengine/godot-builds releases if the container is fresh; templates go in `~/.local/share/godot/export_templates/4.7.2.stable/`).

## State
- Engine, systems, UI, campaign content, and all procedural assets are in place.
- Autoplay bot (`game/tests/autoplay.tscn`) drives the campaign with real input actions to verify completability.

## Commands
```bash
cd game
godot --headless --import                                        # import assets
../tools/check.sh                                                # smoke test (script errors + basic sim)
godot --headless --fixed-fps 60 res://tests/autoplay.tscn        # full-campaign bot (writes user://autoplay_report.json)
SHOT_ROOM=oq_kettle SHOT_STEPS="wait:2;shot:x" ../tools/shots.sh /tmp/shots   # screenshots via Xvfb
godot --headless --export-release "Web" ../build/web/index.html
godot --headless --export-release "Linux" ../build/linux/BackstreetOath.x86_64
```
Regenerate assets: `python3 tools/art/gen_characters.py`, `tools/art/gen_environments.py`, `tools/art/gen_items_ui.py`, `tools/art/gen_font.py`, `tools/audio/gen_audio.py`.

## Next actions
1. Finish bot-verified campaign run; fix any blockers it reports.
2. Unit tests (`tests/unit_tests.gd`), web/Linux export verification, screenshots.
3. Release packaging + docs + itch page. itch.io/butler hosts are blocked by this environment's network policy.
