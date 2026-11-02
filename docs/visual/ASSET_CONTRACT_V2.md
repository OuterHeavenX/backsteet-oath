# Asset contract v2 (visual upgrade)

This is the interface between the procedural art generators (`tools/art2/`) and the engine. If it isn't in this file,
the engine doesn't read it. Units: **world units (u)** are the game's logical pixels at the 640×360 base resolution;
**texels (tx)** are image pixels. All v2 art is authored at **density 2 (1 u = 2 tx)** and drawn at scale 0.5.

General rules:
- Every image is RGBA PNG with straight (non-premultiplied) alpha.
- No image edge may exceed **2048 tx** (WebGL2 minimum guaranteed size; some mobile GPUs stop at 4096).
- Generators are deterministic: fixed seeds, no network access, Python 3 + Pillow + numpy only.
- Every generator writes a ledger in `docs/assets/` (what it made, how, and its licence: project-original).
- Never upscale a 1× image to fake detail. Each v2 image is re-rendered at 2× with features drawn at that density.
- Collision geometry is defined only by `game/data/rooms.json` and the prop **footprints**. Art must follow that
  geometry and must never change it.

## 1. Characters — `game/assets/sprites/chars/<id>.png` + `<id>.json`
The atlas is packed: frames are trimmed and placed in any arrangement, at most 2048×2048. Its JSON sidecar:
```json
{
  "id": "nico", "version": 2, "density": 2, "height": 96,
  "frames": [[x, y, w, h, ox, oy], ...],
  "hand":   [[hx, hy, deg, front], ...],
  "head":   [[cx, cy], ...],
  "anims": {
    "idle":  {"frames": [0,1,2,3,4,5], "fps": 8, "loop": true},
    "walk":  {"frames": [...], "loop": true, "stride": 36},
    "punch_a": {"frames": [...], "contact": 1},
    "...": {}
  }
}
```
- `frames[i]` gives the atlas rect `x, y, w, h` plus `ox, oy`. `ox, oy` is the rect's top-left corner relative to the
  **anchor** (the point on the ground between the feet), in tx. A standing frame typically has `oy ≈ -100`. All frames
  face **right**; the engine mirrors them for left.
- `hand[i]` is the front-hand grip point relative to the anchor (tx). `deg` is the weapon angle in screen degrees
  (0 = pointing right, positive = clockwise). `front` is 1 if the weapon draws over the body, 0 if under.
- `head[i]` is the head centre relative to the anchor (tx). It positions dizzy stars and emotes.
- `height` is the standing crown height in tx.
- `stride` (walk, run, carry_walk) is the number of **world units travelled per full cycle**. The engine advances
  these cycles by distance, so the planted foot must stay fixed relative to the ground at that rate.
- `contact` is the index *within the anim's frame list* of the first frame of impact. The engine maps attack
  startup ticks to the frames before `contact`, active ticks to `contact` (and `contact+1` if the attack is long), and
  recovery ticks to the remaining frames. Damage timing does not change.
- **Fighter anims (all required):**
  - Movement: `idle` (6, loop), `walk` (8, stride), `run` (8, stride), `jump` (3: takeoff, rise, fall), `land` (2).
  - Strikes: `punch_a` (4), `punch_b` (4), `punch_c` (6), `kick` (5), `kick_c` (6), `jump_kick` (2), `jump_punch` (2),
    `run_punch` (3), `dropkick` (3).
  - Defence and damage: `guard` (2), `hurt_high` (3), `hurt_low` (3), `hurt_back` (3), `knockdown` (5: launch,
    airborne, impact, bounce, lying), `getup` (4), `dizzy` (4, loop).
  - Objects and specials: `pickup` (3), `carry` (2, loop), `carry_walk` (6, stride), `throw` (4), `swing` (5),
    `sweep` (4), `rising_kick` (4), `slam` (3).
  - Social: `victory` (4), `talk` (4, loop), `cower` (3, loop).
  - Counts are minimums. Every attack has at least one anticipation frame before `contact`.
- **Non-fighters** (civilian NPCs) need `idle`, `walk`, `run`, `talk`, `cower` and `victory`, plus every anim key
  their v1 sheet had (aliasing frames is allowed).
- **Scale:** a normal adult is 92–100 tx tall (46–50 u), the same world size as v1. Heavies are 104–116 tx, kids
  76–84 tx, and Biscuit the dog about 44 tx. Proportion is about 3 heads tall (head 30–34 tx).

**Portraits:** `game/assets/portraits2/<id>.png` is a horizontal strip of 5 frames, 192×192 tx each, in the order
neutral, happy, angry, surprised, sad. The ids are the same as v1.

## 2. Environments — `game/assets/bg2/<room_id>/room.json` + PNGs in that folder
```json
{
  "room": "oq_kettle", "width": 1600, "density": 2,
  "layers": [
    {"name": "sky",  "files": ["../_district/old_quarter_sky.png"], "parallax": 0.05, "y": 0, "repeat": true},
    {"name": "far",  "files": ["../_district/old_quarter_far.png"], "parallax": 0.25, "y": 40, "repeat": true},
    {"name": "mid",  "files": ["mid_0.png"], "parallax": 0.55, "y": 60, "repeat": false},
    {"name": "base", "files": ["base_0.png", "base_1.png"], "parallax": 1.0, "y": 0, "repeat": false}
  ],
  "fg": [{"file": "fg_pillar.png", "x": 512, "y": 360, "parallax": 1.25, "fade": true}],
  "lightmap": {"file": "light.png", "cell": 8},
  "ambient_color": "#fff0e0",
  "rim": {"color": "#ffb070", "dir": [-1.0, -0.35], "strength": 0.45},
  "cast_shadow": {"dir": [0.55, 0.22], "alpha": 0.22},
  "glows": [{"x": 300, "y": 120, "r": 60, "color": "#ffcc70", "energy": 0.5, "flicker": "neon", "front": false}],
  "ambient": [{"type": "steam", "x": 820, "y": 210}],
  "reflect": [{"rect": [0, 250, 1600, 94], "alpha": 0.18}]
}
```
- `layers` are drawn back to front. A layer's tiles sit left to right, each tile at most 2048 tx wide. `y` is the
  top edge in u. `parallax` 1.0 moves with the world, and smaller values move slower.
- The `base` layer spans the room width (2·W tx) and is 720 tx tall. On exterior rooms its sky is transparent so the
  district `sky`/`far` layers show through. Interiors are opaque and have no parallax layers.
- District layers live in `game/assets/bg2/_district/` and are shared by every room in that district. A layer with
  `repeat: true` tiles horizontally.
- `fg` holds foreground framing sprites (posts, railings, hanging signs, cables, fence ends). `x` is the sprite's
  centre and `y` its bottom edge, both in u at parallax 1.0 (the engine offsets them for parallax). They must stay
  near the bottom or side edges and never cover more than 40% of the walk band's height. `fade: true` lets the engine
  fade the sprite to 30% when an actor is behind it.
- `lightmap` covers the room. Each texel is `cell`×`cell` u and the image is W/8 × 45 tx. Each texel's RGB is the
  light multiplier for an actor or prop whose *feet* are there, with **value/204 = multiplier** (204 means neutral
  1.0, and 255 means 1.25). Keep the playable band between 140 and 240, so faces never go below about 0.69 or blow
  out.
- `rim` is the room's default rim light (the direction points from the light toward the actor). The engine also
  takes rim colour from the strongest `glow` within 1.5·r of an actor.
- `glows` are additive radial lights drawn by the engine with a shared soft texture. `flicker` is one of `none`,
  `neon`, `flame` or `fluor`. `front: true` draws the glow over actors, for haze; keep its energy at or below 0.25.
- `ambient.type` is one of `steam`, `drip`, `smoke`, `sparks`, `paper`, `leaves`, `pigeons`, `water_shimmer`,
  `fan`, `dust_motes` and `embers`. These take an optional `w`, `h` and `rate`.
- `reflect` lists wet or polished ground rects (u) where the engine draws faint flipped actor reflections.
- Base art must line up with `rooms.json`:
  - the walk band top edge (curb or wall base) at `walk[0]`;
  - doors at their `x`;
  - blockers (water, rubble, machinery) drawn where the blocker rects are.
- Props are **not** painted into the base. The playable band must stay calm and readable: low-contrast ground
  texture, with no high-contrast patterns under the fighters.

## 3. Props — `game/assets/props2/<type>.png` + `props2/props.json`
`props.json` holds the **same keys and the same `anchor`/`footprint` numbers as v1 `props/props.json`**, in
**world units**. The new file adds `"density": 2` per entry. The PNG is drawn at 2× (anchor tx = anchor u × 2). Draw
props in neutral albedo, because the lightmap does the district tint. The visible height may grow by up to 25% if
that helps the design, but footprints are fixed.

## 4. Items, FX and UI — under `game/assets/`
- `icons2/<id>.png`: 32×32, one for every id in `icons/`.
- `weapons2/<id>.png` + `weapons2/weapons.json`: the same keys as v1, with grip and anchor in tx at density 2.
- `pickups2/` + `pickups.json`: the same keys as v1, at density 2.
- `fx2/<name>.png` (a horizontal strip of equal cells) + `fx2/fx.json`:
  `{"name": {"file": "x.png", "cell": [w, h], "count": n, "anchor": [ax, ay], "fps": 24, "additive": false}}`.
  - Impact sets: `hit_light`, `hit_heavy`, `hit_kick`, `hit_metal`, `hit_wood`, `hit_glass`, `hit_stone`,
    `hit_soft`, `block`, `perfect_block`.
  - Arcs (white, tinted by the engine): `arc_punch`, `arc_kick`, `arc_swing`, `arc_sweep`, `arc_heavy`, `arc_rising`.
  - Dust and motion: `dust_land`, `dust_step`, `dust_slide`, `dust_fall`, `dust_jump`.
  - Status and specials: `ko_burst`, `stars_dizzy`, `levelup_burst`, `charge_glow`, `coin_sparkle`, `exclaim`,
    `question`, `shockwave`, `splash`.
  - Weather and atmosphere: `steam_puff`, `smoke_puff`, `rain_splash`, `drip`.
  - Single-frame debris (`count` 4, one variant per frame): `chip_wood`, `shard_glass`, `spark_streak`,
    `chunk_stone`, `scrap_paper`, `bit_metal`.
  - Shared textures: `glow_soft` (256² white radial, smooth falloff), `glow_streak`, `shadow_soft` (128×48 soft
    ellipse) and `light_cone`.
- `ui2/`: 9-slice panels with a `ui2/ui.json` of margins, the HUD frame, bar frames and fills, the boss bar, the
  portrait frame, the cursor, the touch buttons (the same names as v1 at 2×), gamepad and key glyphs (2×), the map
  (2×), `logo.png` (about 1100×330), the title layers (`title_sky`, `title_far`, `title_mid`, `title_street`,
  `title_hero`), the boss card frame and the app icons (256 and 64).
