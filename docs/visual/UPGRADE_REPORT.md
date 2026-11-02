# Visual Upgrade Report — Backstreet Oath 1.1.0-rc1

Branch `claude/visual-upgrade`, built on 1.0.0-rc3 (plus the rc4 web-audio fix). Gameplay, story, quests, weapons,
skills, controls, the ending and the save format (v2) are unchanged. Saves from rc1–rc4 load in 1.1.0.

## What changed, in one paragraph
Every image in the game was redrawn at twice the old density with a single direction: **inked, cel-shaded 2D
illustration** (`docs/ART_DIRECTION.md`). The engine now renders 640×360 logical units at window resolution
(`canvas_items` stretch) instead of upscaling a 640×360 pixel image.
- **Characters:** full animation sets of 73–128 frames per character, where rc3 had 58 small frames.
- **Rooms:** layered parallax rooms with foreground framing and authored lighting.
- **Combat presentation:** reworked around real hit events.
- **UI:** rebuilt with OFL typefaces, brass-framed panels, a portrait HUD and 96 u dialogue busts.
- **Story scenes:** letterbox staging, location and boss name cards.

## Before / after (same camera positions, same game state)
Side-by-side stills are in `docs/visual/compare/*.jpg`; `before` is rc3 upscaled 2× nearest-neighbour to the same
size. A side-by-side clip of the same scripted fight is `docs/visual/compare/before_after_kettle.mp4`, and
`docs/visual/after/footage_{kettle,duke,diner}.mp4` are 30 fps Movie Maker captures.

| Shot | What to look at |
|---|---|
| `c01_kettle_fight` | Characters ~2× the detail with readable faces; layered street; lightmap tint and rim light |
| `c04_duke` | Boss card and bar; Duke's chain held at the hand point; contact shadows; chain-link mid layer |
| `c05_canal` | District identity (gold/teal); water drawn exactly over the blocker rects |
| `c06_foundry` | Furnace glow (flame flicker), steel-blue industry, embers |
| `c07_neon` / `c08_rain` | Night neon glows; rain district wet-ground reflections |
| `c10_status` / `c03_diner_shop` | Unified UI: Barlow/Bungee type, brass panels, 2× icons |
| `c11_dialogue` | Letterbox + push-in during scenes; 96 u bust breaking out of the dialogue panel |

## The five weaknesses of rc3, and what was done about each
1. **Tiny, stiff characters.** A new rigged generator (`tools/art2/chars/`) builds the cast:
   - **Rig and rendering:** a supersampled vector rig with ink and cel shading, spring-lagged hair and cloth, and a face drawn per frame.
   - **Hands and limbs:** real fists and open hands, tapered limbs and sleeves.
   - **Distinct movement:** per-archetype stances, walks and guards, plus signature boss idles and victory poses.
   - **Attack timing:** each attack has anticipation → contact → follow-through frames, mapped onto the existing tick phases, so **no damage timing changed**.
   - **No foot sliding:** walk and run cycles advance by distance travelled; measured planted-foot drift is ≤0.37 tx per frame.
   - **Hit reactions:** high, low and from-behind hits, and a 5-phase knockdown.
2. **Flat environments.**
   - **Layers and framing:** 30 rooms with sky, far and mid parallax, a 2× base and foreground framing that fades to 30% when a fighter is behind it.
   - **Ambient life:** steam, drips, sparks, embers, paper, dust and water shimmer.
   - **Storytelling:** eviction notices, MISSING: ELI flyers, gang tags and Greyline signage.
   - **Collision unchanged:** collision comes only from `rooms.json` and the rc3 prop footprints, which a unit check verifies.
3. **No lighting.**
   - **Lightmaps:** per-room authored lightmaps tint fighters and props by where their feet are.
   - **Glows:** additive glows with neon, flame and fluorescent flicker.
   - **Rim light:** edge-detected rim light from the nearest glow.
   - **Shadows and reflections:** soft contact shadows, a faint cast shadow outdoors, and reflections on wet or polished floors.
   - **Restraint:** no full-screen bloom, and fog ≤0.15.
4. **Weak combat feedback.**
   - **Material impacts:** fist, kick, metal, wood, glass, stone and soft each have their own burst and directional debris.
   - **Smear arcs:** drawn at the contact frame.
   - **Dust:** landing, footstep, slide and fall dust.
   - **Camera:** a directional spring impulse replaces random shake.
   - **Flash:** hits flash at 55% so hi-res bodies don't blow out.
   - **Settings:** Screen shake, Hit flashes and the new Effects (Full/Reduced) setting are all respected.
5. **Tiny UI and static story scenes.**
   - **Text:** 10–11 u body text (rc3 was 8 u).
   - **HUD:** a portrait medallion that changes expression with HP and combat.
   - **Story staging:** letterbox bars and a 6% push-in during scripted scenes, location and boss cards, a flash and slow-motion beat when the boss changes phase, and a patterned wipe between scenes.
   - **Title:** a parallax title screen.
   - **Key scenes:** the opening, rescue and revelation got camera framing; the ending cards now play over a drifting dusk backdrop. All scenes remain skippable, and skipping still applies flags and journal notes.

## Asset sources and licences
- **Art:** all of it is generated by this project's own deterministic Python generators in `tools/art2/{chars,env,ui}`. Each has a ledger in `docs/assets/*_V2.md`.
- **Generation services:** no paid generation services, image models or downloaded art were used.
- **Fonts:** the only third-party assets are the SIL OFL fonts Bungee and Barlow / Barlow Condensed, with licences in `game/assets/fonts/ofl/` and listed in `THIRD_PARTY_NOTICES.md`.
- **Build-time tool:** `tools/art2/optimize_textures.py` uses libimagequant through the BSD-licensed `imagequant` Python package at build time only. Nothing from it ships in the game.

## Performance (measured; read the caveats)
`game/tests/perf.tscn`: 6 s per scenario at a 1280×720 window. Machine: 4-vCPU Xeon @ 2.1 GHz, **no GPU**, Mesa
llvmpipe software OpenGL under Xvfb. Same machine and harness for both builds.

| Scenario | rc4 FPS (avg / p95 ms) | 1.1.0 FPS (avg / p95 ms) | 1.1.0 draw calls | 1.1.0 texture MB |
|---|---|---|---|---|
| Explore Kettle Street | 125.7 / 10.4 | 28.4 / 41.0 | 56 | 53 |
| Crowd (8 enemies) | 123.2 / 11.0 | 31.2 / 39.3 | 71 | 88 |
| Rain, Pump Station | 116.7 / 11.9 | 32.9 / 36.9 | 65 | 78 |
| Interior, diner | 140.2 / 9.7 | 44.7 / 27.3 | 43 | 29 |
| Boss, Rook | 121.5 / 11.0 | 47.0 / 26.9 | 47 | 37 |

- rc3/rc4 rendered 640×360 pixels and scaled the image up. 1.1.0 renders every window pixel (4× as many at 720p),
  with layered parallax and additive glows. Running the same crowd scenario in a 640×360 window gives **73 FPS**,
  so on this machine the cost is software pixel fill, not game logic.
- **No GPU, Steam Deck, phone or console hardware was available.** 60 FPS on real hardware is expected for this
  load (≤71 draw calls, ≤88 MB of textures) but is **not measured** here. In particular, no Steam Deck performance
  is claimed.
- Web (Chromium, SwiftShader software WebGL): 4–10 FPS at 1280×720, against 29–40 for rc3 in the same harness.
  This is not representative of GPU browsers.
- **Mitigations that are in place:**
  - The web canvas pixel ratio is capped at 1.5. A phone with a 3× screen renders 1266×585 instead of 2532×1170.
  - Effects: Reduced turns off cast shadows, reflections and ambient emitters, and halves debris.
  - Character atlases are packed and trimmed.
  - Only the current room's character and background textures stay loaded.
  - Ambient effects run on persistent CPU particle emitters.
  - Hit effects are short-lived sprite nodes, capped per hit (at most 7 debris pieces, 2 on Reduced). They are not
    pooled.
- **Download:** the web package is 56.7 MB. Before palette quantisation it was 106.5 MB. Quantisation is lossless
  256-colour, with the worst atlas at 38 dB PSNR.

## Verification summary
- **Test suites:**
  - Unit 7,775/7,775. These now include v2 contract checks: required anims, valid contact frames, strides, atlas ≤ 2048, prop footprints identical to rc3, and known ambient types.
  - Features 65/65 and quests 23/23.
  - The autoplay bot completed the whole campaign with the v2 roster in 49.0 game-minutes: 15 knockouts all recovered, level 14, 0 script errors.
- **Platforms:**
  - **Browser:** the web export was tested in Chromium (title → new game → intro → fight → status → reload).
  - **Native Linux:** the exported binary was driven with real X11 key events (`tools/nativetest/xkeys.py`).
  - **Windows:** exported only, not run.
- **Layouts:** checked at 1920×1080, 1280×800 (Deck size), 1688×780 (phone landscape, touch) and 1280×960 (tablet with the touch deck). Dialogue, shop, status and pause screens showed no overlaps.
- **Audio:** web audio was measured in Chromium by tapping the Web Audio graph: RMS 0.05–0.11 after the first input. **The mix itself has not been listened to;** this container has no audio device. The new material sound layers are kept quiet (−14/−15 dB) for that reason.

## Honest ceiling
This is clean, consistent **procedural vector illustration**, not hand-painted art.
- **Characters:**
  - Anatomy, cloth folds and hands are simplified.
  - All fighters share one rig.
  - Attack animations are shared within an archetype.
- **Environments:**
  - Distant skylines are flat silhouettes.
  - Some floors are mild patterns.
  - Foreground framing is placed automatically per district.
- **Upgrade path:** a human illustrator or animator pass on the hero, the bosses and the six district key rooms would
  be the highest-value next step. The asset contract (`docs/visual/ASSET_CONTRACT_V2.md`) lets hand-made art
  replace any generated sheet or room without code changes.
