# Build Plan — BACKSTREET OATH

Engine: **Godot 4.7.2-stable** (official build), GDScript, Compatibility renderer. Virtual canvas 640×360, `viewport` stretch, `keep_height`.

| # | Stage | Status |
|---|---|---|
| 1 | Environment audit, scope lock, art bible, room data | done |
| 2 | Platform proof (web over HTTP + persistence, Linux under X11/GL) | done |
| 3 | Core engine: ground-plane actors, combat, AI tokens, rooms, weapons, props | done |
| 4 | Systems: save slots/backup/import-export, settings, rebinding, touch, audio, UI menus | done |
| 5 | Campaign: 6 districts, 20 exterior + 10 interior rooms, bosses, quests, ending | done (tuning ongoing) |
| 6 | Assets: procedural characters, environments, props, items/UI/fonts, music/SFX | done |
| 7 | Verification: autoplay bot, unit tests, web + Linux runs, screenshots | in progress |
| 8 | Release: versioned zips, docs, itch page, upload | pending (itch.io blocked by network policy) |

Key decisions
- Custom belt-scroller physics (no physics engine): ground (x, depth y) + height z; y-sort by feet.
- All content data-driven in `game/data/*.json`, validated by `Content.validate()` and tests.
- Story beats are coroutines in `scripts/autoload/story.gd`; NPC dialogue chosen by condition strings.
- The campaign is verified by `tests/autoplay.tscn`, a bot that plays through InputMap actions only.
