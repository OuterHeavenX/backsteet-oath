# QA Report (1.0.0-rc3)

**Test environment (all results below):** Linux x86_64 VM, 4 vCPU, 15 GB RAM, no GPU; Godot 4.7.2-stable official
editor binary for tests and the official export templates. Rendering: Mesa llvmpipe (OpenGL 4.5, software)
under Xvfb, and headless Chromium 1243 (Playwright) with SwiftShader WebGL 2. No sound card, so audio ran on the
dummy driver. **No physical Steam Deck, phone, Windows PC or gamepad was available.**

Bug classification: **blocker** = prevents completion or crashes; **major** = significant broken feature;
**minor** = cosmetic or limited impact. **Open blockers: 0. Open majors: 0.**

## Automated suites
| Suite | What it covers | Result |
|---|---|---|
| `tests/unit_tests.tscn` | Data cross-references, assets present for every reference, condition language, stats/XP/level cap, food caps, inventory, save round-trip + repeated reload (no double-apply), file save/backup, corrupt-save recovery, v1→v2 migration, hostile value sanitizing, quest rewards/repeatability, progression graph (every stage reachable, a safe hub always reachable), combat geometry (lane depth, behind, airborne, single hit per instance, downed not hittable, XP once per enemy), drop positions never inside geometry, weapon pickup/throw without duplication | **574 / 574 pass** (also passes from the extracted source zip) |
| `tests/feature_tests.tscn` | Every technique triggered through its real input chord and dealing damage; perfect guard + Guard Counter; Giant Swing; all 16 weapons (swing or throw); crate lift/throw; Lou's lobbed crate; all 8 boss AIs use ≥3 distinct attacks; Rook phase 2 | **65 / 65 pass** |
| `tests/quest_tests.tscn` | All six side jobs completed through walking + Grab/Talk + dialogue choices; follower, escort, investigation choice, timed Cup, parcel hunt; rewards; save/load persistence | **23 / 23 pass** |
| `tests/autoplay.tscn` | Full main campaign played by a bot through InputMap actions only | **Completed** in 47.4 in-game min, 13 retries, 0 script errors (see PLAYTHROUGH_REPORT.md) |
| `tools/check.sh` | Script-load smoke + short simulation | pass |

## Platform checks
| Check | Method | Result |
|---|---|---|
| Web export boots over HTTP without special headers (itch-style) | Release web zip extracted to a fresh folder, served by a plain static server, Chromium | **Pass:** single-threaded build, WebGL 2, boot about 4.6 s locally |
| Browser persistence | New game → save → page reload → title shows **Continue** | **Pass** (IndexedDB) |
| Browser audio activation | Title waits for first key/click/tap before music (`Audio.unlocked`) | Implemented; no audio device to listen |
| Browser console errors | Captured during boot, menus, fight, status, reload | **None** (only engine banner lines) |
| Tablet landscape + touch (rc2) | iPad Pro 11 landscape emulation (1194×834): tap to start, menus, tap/skip dialogue, multi-touch fight, BAG → Back | **Pass:** street on top, control deck below with no overlap, controls dimmed during dialogue, Back button closes menus. *Emulation only* |
| Tablet 4:3 choice dialog (rc3) | 1024×768 render with touch controls forced on: Coach Benny's Shop/Chat/Leave choice | **Pass:** all options visible above the control deck; deck dimmed and drawn beneath |
| Mobile landscape + touch | Pixel 7 landscape emulation, CDP multi-touch: stick + PUNCH held together | **Pass:** controls auto-appear, simultaneous move/attack registered, page scroll offset 0. *Emulation only; not a real phone* |
| Portrait orientation | Rotate overlay pauses without losing state | Implemented; not tested on a real phone |
| Linux package | Release zip extracted to a path with spaces, launched via `start.sh` under X11/Mesa | **Pass:** exec bits preserved, clean exit, no absolute paths |
| Steam Deck resolution | Exported binary at 1280×800 | **Pass:** 2× integer scale + 40 px bars, legible UI (screenshot verified). *Not on Deck hardware* |
| Windows package | Exported PE32+ x86-64 GUI exe + pck | Built; **not launched** (no Windows host) |
| Fullscreen / resize | `viewport` stretch + `keep_height`; tested 1280×720, 1280×800, 863×360 (phone) | Layout verified by screenshots |
| Performance | `?bo_debug` perf log in Chromium (SwiftShader, shared CPU) | 29–40 FPS with 4–5 actors; worst frames 43–143 ms. **Not representative of GPU hardware; the 60 FPS target is unverified** on real devices |

## Controls & menus
- Every menu is navigable with keyboard and controller (`ui_*` actions mapped to arrows/WASD, D-pad/left stick,
  Enter/Space/J/E/A to confirm, Esc/Backspace/K/B to go back), with focus recovery if lost.
- Bindings: each of the 12 gameplay actions has two keyboard keys and a pad button (guard/run also on triggers);
  rebind UI with conflict swapping and reset to defaults. Run (Shift) and Guard (L) do not overlap by default.
- Simulated gamepad navigation was **not** run (no device); controller support relies on Godot's SDL mappings.

## Issues found and fixed during verification
| Severity | Issue | Fix |
|---|---|---|
| Blocker | Enemies could spawn inside the Canal Walk water and never move (stuck wave lock) | Spawns choose free ground; anything overlapping geometry can move out |
| Blocker | Boss never started if a straggler wandered off-screen | Off-screen stragglers leave when the arena triggers |
| Major | Story fight helper crashed on typed spawn specs (intro softlock) | Fixed type handling |
| Major | Freed-room reference in story coroutines after defeat | Validity checks accept freed objects safely |
| Major | UI theme not applied through CanvasLayers (wrong font) and title layout offset in browsers | Theme applied per UI root; anchor+offset placement helper |
| Major | Touch pause/bag buttons didn't open menus | Touch emits real `InputEventAction` events |
| Major | Bosses repeated a single attack when the player kept distance | Weighted movesets with cooldowns and repeat penalty |
| Minor | Fighters could overlap the player | Body separation |
| Minor | Hints overlapped signage; objective under touch buttons | Hint panel; HUD offset when touch is active |

Remaining minor issues and open gates: [KNOWN_ISSUES.md](KNOWN_ISSUES.md).
