# Building and launching 1.4.0-rc1

Nothing was published or uploaded. The packaged files below exist only in the `release/` folder of the working
copy where they were built (that folder is ignored by git), and can be rebuilt from the branch at any time.

## Run from source (any machine with Godot 4.7.2)
```bash
git checkout claude/gameplay-polish
cd game
godot --headless --import      # first time only; about 7 minutes (textures are re-encoded)
godot                           # opens the editor; press F5. Or: godot --path . to run directly
```
Debug builds only: F1 overlay, F2 +XP, F3 next room, F4 spawn enemies, F5 heal.

## Build the packages
```bash
python3 tools/package.py 1.4.0-rc1 --reimport-textures
```
Needs Godot 4.7.2 with its export templates installed. `--reimport-textures` matters the first time after pulling
this branch: an import cache made by an older checkout keeps the larger textures until they are re-imported.
Output goes to `release/`.

## What was built here
From a clean checkout of commit `d212c56` (fresh import, then export):

| File | Size | 1.3.0-rc1 | SHA-256 |
|---|---|---|---|
| `backstreet-oath-v1.4.0-rc1-web.zip` | 62.8 MB | 74.5 MB | `65b5f73e5c10c78244f47f3f910a0506634cb56a99e981a467b8148f4a8c2f13` |
| `backstreet-oath-v1.4.0-rc1-linux-x86_64.zip` | 81.0 MB | 92.7 MB | `5cb5f5b2fd8853e08f29d69e0e5a6c176334bb19abbd1f48310a392df2bd4679` |
| `backstreet-oath-v1.4.0-rc1-windows-x86_64.zip` | 90.5 MB | 102.3 MB | `05852a04beb689d90559168cf86d524a27cfb7037059a4518a36731e1fa20f38` |
| `backstreet-oath-v1.4.0-rc1-source.zip` | 110.4 MB | 79.1 MB | `e6c2066d761232a4cd9fd2095d332eb562831f915e4cdd00be045b50c4b3e452` |

- The game data pack is 54.5 MB (66.2 MB in 1.3) because textures are stored with a stronger lossless setting;
  the pixels are identical.
- The Windows zip is now under GitHub's 100 MB file limit, so it no longer needs splitting.
- The source zip grew because it now carries the before/after captures, the 1.3 save fixtures and the
  performance evidence under `docs/polish/`.

## Launch
**Linux / Steam Deck**
```bash
unzip backstreet-oath-v1.4.0-rc1-linux-x86_64.zip
cd BackstreetOath
./start.sh
```
Works from a folder with spaces in its name. Saves: `~/.local/share/godot/app_userdata/Backstreet Oath/`.
Steam Deck steps are in `STEAM_DECK.md` (not tested on a Deck).

**Windows:** unzip and run `BackstreetOath\BackstreetOath.exe` (exported, never launched here).

**Browser:** unzip the web zip and serve the folder over HTTP, then open `index.html`:
```bash
unzip backstreet-oath-v1.4.0-rc1-web.zip -d web
python3 tools/webtest/serve.py web 8765      # or: python3 -m http.server --directory web 8765
# open http://127.0.0.1:8765/index.html
```
Opening `index.html` straight from disk does not work; browsers block it. On itch.io the same zip is uploaded as
an HTML game (steps in `ITCH_PAGE.md`; not done as part of this work).

## Smoke tests run on these packaged files
| Check | Result |
|---|---|
| Web, desktop Chromium (headless, software WebGL): `node tools/webtest/game_test.js <url>?bo_debug=1 <out>` | Boots in 4.5 s, title shows v1.4.0-rc1, new game starts, the opening tips appear and advance, status menu opens, reload returns to the menu. No page errors. |
| Web audio: `node tools/webtest/audio_test.js <url> <out>` | Web Audio is running and produces signal after input (RMS 0.056 to 0.091). This shows sound is being output, not that it sounds right. |
| Web, emulated iPad touch: `node tools/webtest/touch_test.js <url>?bo_debug=1 <out>` | Title, New Game by tap, docked control deck, intro dialogue advancing by tap. The script's later taps (skip, fight, bag) are aimed at an older layout and did not land, so touch fighting in the browser was **not** exercised by this run. One stale tap position in the script was fixed. |
| Linux package, extracted to a folder with a space in its name, under Xvfb with real X key events (`tools/nativetest/xkeys.py`) | Launches, title shows v1.4.0-rc1, new game, intro skipped with Escape, walking and punching work, tips advance. No script errors; the only error in the log is the missing audio device. |
| Windows package | Not launched (no Windows machine). |

All rendering in these checks was software. They show that the packages start and respond to input, nothing
about speed.
