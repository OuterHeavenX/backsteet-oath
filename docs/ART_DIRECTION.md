# Backstreet Oath — Art Direction (visual upgrade, v1.1)

**One direction:** a *high-detail, inked and cel-shaded 2D street illustration*. Picture compact, expressive
fighters with clean dark outlines and two-step shading, standing in layered, lived-in streets painted at the same
density. Light tells the story:
- the warm neighbourhoods (Old Quarter, Canal Market) glow amber at dusk;
- the industry (Ironworks, Floodgate, Warehouse) is cold steel, sodium and fluorescent;
- Neon Mile is night colour.

Effects stay restrained. The fight must always read first.

Reference set (our own game, same camera positions before and after): `docs/visual/baseline/` (rc3) and
`docs/visual/after/` (this upgrade). The comparison set is captured by `tools/capture_set.sh`.

## The five biggest weaknesses of rc3, in priority order
1. **Characters are tiny, stiff and low-detail.** They are 46 px chibis with 2×2-pixel eyes. Punches are 2 frames
   with no anticipation or follow-through, there is no secondary motion, and one generic hurt pose covers every hit.
   Faces don't read (`baseline/c01_kettle_fight.png`).
2. **Environments are single flat layers.** Each is one 640×360-density painting with no foreground framing, no
   parallax depth beyond one skyline strip and no ambient life. The ground band is mostly empty asphalt
   (`baseline/c02_kettle_street.png`, `c05_canal.png`).
3. **There is no lighting.** One uniform tint per district, props tinted by the engine, no local light, no contact
   or cast shadows and no wet reflections in the rain districts (`c07_neon.png`, `c08_rain.png`).
4. **Combat feedback is weak and the same for everything.** One spark and one heavy burst for all impacts. No arcs,
   no difference between materials, and random screen shake.
5. **The UI is tiny pixel-font text and the cinematics are static.** HUD text is 8 px, dialogue portraits are 64 px
   and boss entrances have no staging (`c10_status.png`, `c11_dialogue.png`).

## Measurable decisions
| Area | Decision |
|---|---|
| Resolution | Logical 640×360 (unchanged, so gameplay and layout code are unchanged). Stretch `canvas_items` + `expand`. Art at **density 2** (1 world unit = 2 texels), drawn at scale 0.5. That is 1:1 at 1280×720 and the Deck's 1280×800, linear filtering with mipmaps for smaller windows. |
| Max texture | 2048 texels per edge (web-safe). Character atlases are packed and trimmed. |
| Character scale | Adults 92–100 tx (46–50 u, same world size as rc3, so hitboxes still match). Heavies 104–116 tx, kids 76–84 tx. About 3 heads tall: head 30–34 tx, eyes at least 4×5 tx with a highlight. |
| Line | 2 tx outer contour in a darkened, hue-shifted local colour (L* 8–20, never pure black). 1 tx inner contours where limbs overlap. Limbs are drawn as one merged shape per limb, so there are no visible joint seams. |
| Shading | Three tones (shadow / base / light) plus a rim. Shadows shift about 20° toward violet-blue, lights toward warm. The key light is upper-front, with an engine-driven rim light from the room. |
| Animation | Every attack has anticipation, contact, follow-through and recovery frames. Frames are mapped onto the existing tick phases (startup → anticipation, active → contact, recovery → follow-through), so **damage timing is unchanged**. Walk/run cycles advance by distance travelled (`stride`), so feet don't slide. Hair, jacket hems and loose cloth use spring-lagged secondary motion. Faces change per frame (effort, pain, blink). |
| Hit reactions | `hurt_high` (head snap), `hurt_low` (body fold), `hurt_back` (hit from behind), and knockdown for heavy hits. Direction comes from the attacker's side. |
| Environments | Stacked layers: sky 0.05 → far 0.25 → mid ≈0.55 → base 1.0 → foreground 1.2–1.35. Foreground fades to 30% when an actor is behind it. The walk band is a calm, low-contrast surface with a clear curb or wall edge at `walk_top`. |
| Lighting | An authored per-room lightmap (8 u cells) tints actors and props by where their feet are. Additive radial glows with neon/flame/fluorescent flicker. A rim light from the nearest glow. Soft contact shadows under everyone, plus a faint directional cast shadow outdoors. Wet-ground reflections in rain districts. No full-screen bloom, no crushed blacks, and fog alpha ≤ 0.15. |
| Effects | Material-specific impacts (fist, kick, metal, wood, glass, stone, soft) and white smear arcs tinted per attack. Directional dust and debris. Directional camera impulses (not random shake). At most 48 particles per hit, with pooled nodes. "Reduce flashes" and "screen shake" settings are respected, and a new "Effects: Full / Reduced" setting is added. |
| Palette | Old Quarter: amber dusk (#ffb070 light, #3a2a4a shadow). Canal: gold and teal. Ironworks: steel blue with furnace orange. Neon Mile: magenta and cyan at night. Floodgate: rain blue-green. Warehouse: fluorescent green-grey. Characters keep saturated mid-values, so they separate from the darker, more muted grounds. |
| Typography | **Bungee** (display: logo, titles, boss cards). **Barlow SemiBold/Bold** (body, dialogue). **Barlow Condensed Bold** (HUD numbers). All SIL OFL 1.1 from Google Fonts via Fontsource; licences are in `game/assets/fonts/ofl/`. Minimum body size is 11 u (22 px at 720p). |
| Portraits | 192×192 tx busts, 5 expressions, shown at 96 u in dialogue. |
| Cinematics | Letterbox bars (32 u), slow camera pushes, boss name cards, a hit-pause flash on phase changes. Every scene can be skipped, and skipping still applies its journal and quest results. |

## Honest ceiling
All art is still produced by **local procedural generators** (Python, deterministic) written for this project. No
paid generation services were used, and no third-party art other than the OFL fonts above. The generators draw at
2× density with supersampled anti-aliasing, inked outlines, cel shading, spring-driven secondary motion and
per-frame expressions. The result is a clean, consistent vector-illustration look. It is **not** hand-painted
illustration: anatomy, cloth folds and painterly texture stay simpler than a human artist's work. See
`docs/visual/UPGRADE_REPORT.md` for the before/after evidence.
