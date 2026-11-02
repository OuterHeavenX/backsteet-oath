# Third-Party Notices & Asset Ledger

## Engine
**Godot Engine 4.7.2-stable**: MIT License. Copyright (c) 2014-present Godot Engine contributors; (c) 2007-2014
Juan Linietsky, Ariel Manzur. The exported game includes the Godot runtime and its bundled third-party libraries
(e.g. FreeType, HarfBuzz, ICU data, Mbed TLS, libogg/libvorbis, zlib, Emscripten runtime on web), each under
its own permissive license. The complete list ships with Godot: https://godotengine.org/license
(also `COPYRIGHT.txt` in the Godot source).

## Third-party fonts (v1.1 visual upgrade)
| Font | Files | Copyright | License | Source |
|---|---|---|---|---|
| **Bungee** (display: logo, headings, boss cards) | `game/assets/fonts/ofl/Bungee-Regular.ttf` | Copyright 2023 The Bungee Project Authors (https://github.com/djrrb/Bungee) | SIL Open Font License 1.1, full text in `game/assets/fonts/ofl/OFL-Bungee.txt` | Google Fonts via the npm package `@fontsource/bungee` 5.3.0 (latin subset WOFF, converted to TTF with fontTools, glyphs unmodified) |
| **Barlow** Medium/SemiBold/Bold and **Barlow Condensed** SemiBold/Bold (body text, HUD numbers) | `game/assets/fonts/ofl/Barlow*.ttf` | Copyright 2017 The Barlow Project Authors (https://github.com/jpt/barlow) | SIL Open Font License 1.1, full text in `game/assets/fonts/ofl/OFL-Barlow.txt` | Google Fonts via `@fontsource/barlow` 5.3.0 and `@fontsource/barlow-condensed` 5.3.0 (same conversion) |

The fonts are bundled, not sold on their own, and keep their original names. Bungee and Barlow Condensed glyphs are
also rendered into some project images (logo, app icon, sign lettering), which the OFL permits.

## Project assets: all original, generated for this project
| Asset group | Origin | License |
|---|---|---|
| v2 character atlases and portraits (density 2) | `tools/art2/chars/` | Project-owned |
| v2 rooms, district parallax layers, props, lightmaps | `tools/art2/env/` | Project-owned |
| v2 effects, weapons, pickups, icons, UI, map, logo, title art | `tools/art2/ui/` | Project-owned (logo and labels use the OFL fonts above) |
| rc3 character sheets, portraits, dog sprite (kept as fallback) | `tools/art/gen_characters.py` | Project-owned |
| rc3 rooms, parallax, props, title backdrop, map | `tools/art/gen_environments.py` | Project-owned |
| rc3 weapons, icons, effects, pickups, UI, logo, app icon | `tools/art/gen_items_ui.py` (+ helper modules) | Project-owned |
| Fonts "Oath Pixel" and "Oath Big" (rc3 UI, no longer used by default) | `tools/art/gen_font.py` from original glyph bitmaps | Project-owned; may be released under SIL OFL 1.1 |
| Music (12 loops, 2 jingles) and 63 sound effects | Synthesized by `tools/audio/gen_audio.py` (numpy + ffmpeg encoding) | Project-owned |
| Cover / key art | `tools/make_cover.py`, composed from the assets above | Project-owned |
| Story, dialogue, names, maps, data | Written for this project | Project-owned |

No ROM-extracted, purchased or AI-generated art or audio is used. No paid generation service was used. The only
downloaded third-party assets are the OFL fonts above. Detailed per-file ledgers:
- v2 art: `docs/assets/CHARACTERS_V2.md`, `docs/assets/ENVIRONMENTS_V2.md` and `docs/assets/UI_FX_V2.md`;
- rc3 art: `docs/assets/CHARACTER_ASSETS.md`, `docs/assets/ENVIRONMENT_ASSETS.md` and `docs/assets/ITEMS_UI_ASSETS.md`;
- audio: `docs/assets/AUDIO_ASSETS.md`.

## Tools used to build (not distributed)
Python 3, Pillow, numpy, fontTools, ffmpeg (Vorbis encoding, footage), npm (font download), Playwright + Chromium (testing), Xvfb.

## Affiliation
Backstreet Oath is an original game inspired by the classic belt-scrolling action RPG genre. It is not affiliated
with, endorsed by, or derived from any other game or franchise.
