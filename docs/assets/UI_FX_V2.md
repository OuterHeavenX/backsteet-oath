# UI / FX / Items v2: asset ledger

These assets are at **density 2** (1 world unit = 2 texels) per `docs/visual/ASSET_CONTRACT_V2.md` §4, and are drawn
at scale 0.5.

**Origin:** every image here is project-original. Deterministic Python generators in `tools/art2/ui/` (Pillow +
numpy only, fixed seeds, no network, no paid or AI generation services) drew them as vectors at 4–6× supersampling,
then box-filtered them down. No v1 image was upscaled. The weapon icons are the new 2× weapon art (`weapons2/`),
rotated, fitted down and re-inked. The key-item icons `satchel`, `toolbox`, `parcel` and `ledger` reuse the new 2×
pickup art.

**Licence:** project-owned, the same as the rest of the game's original art.

## Third-party fonts used inside images
| Font | Used for | Licence | Source |
|---|---|---|---|
| Bungee Regular | `ui2/logo*.png`, `ui2/icon*.png`, title signage, gamepad letters, `fx2/exclaim`, `fx2/question`, a few icon glyphs | SIL OFL 1.1, © 2023 The Bungee Project Authors | Google Fonts via Fontsource 5.3.0 (`game/assets/fonts/ofl/OFL-Bungee.txt`) |
| Barlow Condensed Bold | touch button labels, "DETOUR" sign, small icon text (`$`, `#`, NOTICE) | SIL OFL 1.1, © 2017 The Barlow Project Authors | Google Fonts via Fontsource 5.3.0 (`game/assets/fonts/ofl/OFL-Barlow.txt`) |

The OFL allows embedding rendered glyphs in artwork. The font files themselves ship under the OFL with their licence
texts.

## Rebuild (order matters: icons read `weapons2/` and pickup drawers)
```bash
python3 tools/art2/ui/gen_fx.py          # fx2/*.png + fx2/fx.json                  (~6 s)
python3 tools/art2/ui/gen_items.py       # weapons2/ + pickups2/ (+ json)          (~1 s)
python3 tools/art2/ui/gen_ui.py all      # ui2 core: panels, bars, frames, logo, app icons
python3 tools/art2/ui/gen_title.py       # ui2/title_* parallax layers             (~3 min)
python3 tools/art2/ui/gen_ui_extra.py    # touch buttons, gp/key glyphs, map (+map.json), rotate hint, wipe
python3 tools/art2/ui/gen_icons.py       # icons2/*.png (102 ids)
python3 tools/art2/ui/preview.py all <dir>   # contact sheets for review (not shipped)
```

## Contents
### fx2/ (46 strips + `fx.json`)
- `fx.json` follows the contract format. The extra `_meta` key holds density and notes; skip `_*` keys. Looping
  effects also have `"loop": true`.
- Impacts: `hit_light` (64², 4 frames), `hit_heavy` (96², 5), `hit_kick` (80², 5), `hit_metal` (sparks),
  `hit_wood` (splinters + dust), `hit_glass` (shards), `hit_stone` (chunks + dust), `hit_soft` (paper/poof), `block`,
  `perfect_block`.
- Arcs (white, alpha-tapered, for the engine to tint): `arc_punch`, `arc_kick`, `arc_swing`, `arc_sweep`,
  `arc_heavy`, `arc_rising`. **Their anchor is the attacker's feet** (the ground point) for a standard 96 tx adult
  facing right; scale by actor height / 96 if needed.
- Dust: `dust_land`, `dust_step`, `dust_slide`, `dust_fall`, `dust_jump`. These are neutral warm grey, so the lightmap
  can tint them.
- Status and specials: `ko_burst`, `stars_dizzy` (loop), `levelup_burst` (anchor at the feet), `charge_glow`
  (additive, loop), `coin_sparkle` (additive), `exclaim`, `question`, `shockwave`, `splash`.
- Atmosphere: `steam_puff`, `smoke_puff`, `rain_splash`, `drip`.
- Debris (4 variants each, 1 frame per variant): `chip_wood`, `shard_glass`, `spark_streak` (additive),
  `chunk_stone`, `scrap_paper`, `bit_metal`.
- Shared textures: `glow_soft` (256², additive), `glow_streak` (additive), `shadow_soft` (128×48, black; set alpha
  with modulate), `light_cone` (additive, anchored at the top centre), `sweat`, `target_shadow`.

### weapons2/ (14 + `weapons.json`)
These have the same keys as v1. Each PNG is exactly 2× the v1 size. `grip`/`tip` are in texels, and each entry has
`density: 2`. `crate` and `trash_can` remain `prop:` weapons.

### pickups2/ (9 + `pickups.json`)
These have the same keys as v1. `frame` is ×2, and `coin` has 4 spin frames.

### icons2/ (102)
- One icon per v1 id, 32×32.
- Style: a 2 tx silhouette contour, 1 tx inner contours, cel shading lit from the top-left, and a faint light
  keyline (32% alpha) so dark items stay legible on the dark panels.

### ui2/ (62 + `ui.json` + `map.json`)
- `ui.json` lists every file with its size; 9-slices also have `margins` [l, t, r, b] in texels.
- 9-slice panels: `panel`, `panel_light`, `dialog_box`, `tooltip`, `hud_frame`, `name_tag`, `button`,
  `button_focus`, `button_pressed`, `button_disabled`, `bar_frame`, `boss_bar_frame`, `portrait_frame` and `key_cap`.
- Bar fills: `bar_fill_hp`, `bar_fill_xp`, `bar_fill_boss`, `bar_fill_lag` and `bar_fill_guard`.
- `portrait_frame`: a 208² frame; the 192² portrait sits at (8, 8).
- `boss_card`: 720×160, with `text_rect` given in `ui.json`.
- `cursor`, with its hotspot at (21, 12). `hud_badge`.
- `logo` (1100×330) and `logo_small`. App icons: `icon` (256) and `icon_64`.
- Title layers:
  - `title_sky`: 1600×960, opaque.
  - `title_far`, `title_mid`, `title_street`: 1600×720, transparent tops, bottom-anchored.
  - `title_hero`: a backlit Nico seen from behind; `feet` is in `ui.json`.
  - Suggested parallax values are in `ui.json`.
- Touch: `touch_btn_{punch,kick,jump,guard,grab,run}` (labelled) and `_bare` variants (112²), `touch_btn_pause` and
  `touch_btn_status` (64²), `touch_stick_base` (192²) and `touch_stick_knob` (80²).
- Glyphs: `gp_a/b/x/y/dpad/lstick` (24²), `gp_lb/rb/lt/rt` (32×20) and `gp_select/start` (24×20).
- `map.png` is 960×520 (v1 ×2). `map.json` holds the district coordinates in texels, i.e. the v1 coordinates ×2.
- `rotate_device` (128²) and `wipe` (640×360 greyscale reveal-order mask for a threshold-shader transition).

## Known limits (honest ceiling)
- This is procedural vector art. The pictograms and food icons are clean and readable, but simpler than a skilled
  illustrator's work.
- The title hero is a stylised backlit silhouette. That was a deliberate choice, because a procedural front-facing
  face would read worse than a silhouette.

## Content 1.2 additions (CONTENT_EXPANSION.md §6)
- `weapons2/shovel.png`: 84×24, a long-handled round-point shovel. Grip (12, 12), tip (80, 12). The icon is
  `icons2/w_shovel`.
- `pickups2/` + icons: `radio` (an 80s two-way ambulance radio, 20×30), `conductor_punch` (a brass ticket punch,
  26×20), `scale_weight` (a rigged 1 LB lead weight with a filed plug in its base, 24×24).
- Gear icons: `ladder_belt` (Benny's Rec championship belt) and `iron_wraps` (steel-grey hand wraps).
- `ui2/map.png` now shows the **Underline**, a dashed maroon subway line that runs under the river (drawn faint
  across the water) from Neon Mile to Floodgate. A roundel and an "UNDERLINE" label sit on the south bank.
  `map.json` has `"underline": [658, 406]` (the roundel centre, in texels like the district entries).
