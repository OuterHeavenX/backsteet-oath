# BACKSTREET OATH — Art Bible

All art is original and generated procedurally by the Python scripts in `tools/art/`.
No third-party or ROM-derived imagery is used. Re-run the generators to rebuild assets.

## 1. Canvas & rendering

| Item | Rule |
|---|---|
| Virtual canvas | 640×360, `viewport` stretch, `keep_height` aspect (wider screens see more street; 16:10 Steam Deck letterboxes 40px top/bottom at 2×) |
| Filtering | Nearest everywhere. No mipmaps. No sub-pixel sprite positions for UI |
| Pixel density | 1 art pixel = 1 canvas pixel. Never mix resolutions (no 2× upscaled art next to 1× art) |
| Outline | 1px outline color `#1a1220` around every character, prop and object silhouette. Backgrounds: no outline, but use darker edge pixels |
| Shading | Two tones per material (base + shadow) + optional 1px highlight. Light comes from upper-left |
| Ground shadow | Drawn by the engine: soft-edged dark ellipse `#000000` at 35% alpha, 22×6 px for normal characters |

## 2. Master palette (hex)

Use these colors. Small deviations are fine for gradients and neon glow.

- Outline / ink: `#1a1220`
- Skin: light `#f5c9a0` / shade `#d9a07a`; tan `#d9a07a` / `#b07850`; medium `#c68858` / `#9a6440`; deep `#8a5a3a` / `#5e3a26`
- Hair: black `#2a1e24`, brown `#6a4028`, auburn `#9a4a2a`, blonde `#e8c060`, platinum `#e8e4dc`, gray `#a8a0a0`, red `#c03a2a`, pink streak `#e06090`
- Cloth: red `#c03a3a`/`#7a2030`, orange `#e07a30`/`#a0501e`, mustard `#e0b040`/`#a87a20`, yellow `#f0c040`, green `#4a9a4a`/`#2a5a3a`, teal `#3a9a9a`/`#22605e`, blue `#3a6ac0`/`#22408a`, navy `#22305a`/`#141c38`, purple `#7a4aa0`/`#4a2a6a`, gray `#8a8a96`/`#5a5a66`, charcoal `#3a3a46`/`#24242e`, white `#e8e4dc`/`#b8b0a8`, denim `#4a6a9a`/`#30476e`, brown `#7a5030`/`#50341e`, tan `#c8a070`/`#987048`, black `#2a2a32`/`#18181e`, neon green `#7af04a`
- Environment: brick `#a04a3a`/`#7a3428`/`#c8664a`, mortar `#5a3a34`, asphalt `#3a3a48`/`#4a4a5a`, sidewalk `#8a8478`/`#a8a090`, curb `#6a6660`, wood `#8a5a34`/`#5e3a1e`, rust `#9a5a30`, steel `#6a7280`/`#9aa2b0`, water `#2a5a7a`/`#3a7a9a`/`#6ab0c8`
- Skies: Old Quarter sunset `#f0b070`→`#e08a5a`→`#7a4a6a`; Market day `#8ac8e8`→`#c8e8f0`; Ironworks dusk `#e07a3a`→`#7a3a4a`; Neon night `#1c1a3a`→`#2c2a5a`; Floodgate storm `#2a3040`→`#4a5466`; Warehouse interior dark `#1e1c26`
- Neon: pink `#ff4aa0`, cyan `#4af0f0`, yellow `#fff06a`, green `#7af04a`

## 3. Characters

Chibi-proportioned brawlers in the classic console tradition, but original designs:
oversized heads (≈ 40% of height), big readable eyes, mouths that change with emotion,
chunky 3×3 fists, stubby legs, clear silhouettes, bold gang palettes.

### Sprite sheet contract (all humanoids)

- Cell **64×64**, sheet **8 columns × 8 rows = 512×512** PNG, transparent background.
- **Foot anchor at (32, 60)**: the bottom of the feet sits on row 59; horizontal center of the stance is column 32.
- Drawn **facing right**. The engine flips for left.
- Frames are laid out sequentially left→right, top→bottom in this exact order (58 frames, cells 58–63 empty):

| # | anim | frames | pose notes |
|---|---|---|---|
| 0 | idle | 2 | fists up loosely, slight breathing bob (1px) |
| 2 | walk | 4 | contact/pass/contact/pass |
| 6 | run | 4 | leaning forward, longer stride, arms pumping |
| 10 | punch_a | 2 | jab: windup, front arm fully extended at shoulder height (fist reaches x≈50) |
| 12 | punch_b | 2 | cross with rear arm: windup, extended |
| 14 | punch_c | 3 | hook/uppercut finisher: windup low, impact (fist high, x≈50), follow-through |
| 17 | kick | 3 | chamber knee, leg extended horizontally at hip (foot reaches x≈54), retract |
| 20 | kick_c | 3 | roundhouse finisher: spin windup (back turned), high kick extended, recover |
| 23 | jump | 2 | rising (knees tucked), falling (legs down) |
| 25 | jump_kick | 1 | flying kick, leading leg extended forward-down |
| 26 | jump_punch | 1 | downward heel/punch, body angled down |
| 27 | run_punch | 1 | dash shoulder/punch, body leaning hard forward |
| 28 | dropkick | 1 | body horizontal, both feet forward |
| 29 | guard | 1 | forearms crossed in front of face, crouched slightly |
| 30 | hurt | 2 | high recoil (head back), low recoil (doubled over) |
| 32 | knockdown | 3 | flung back airborne, hitting ground, lying flat on back (lying pose spans ~44px wide, centered on x=32, resting on row 59) |
| 35 | getup | 2 | sitting up, crouched rising |
| 37 | dizzy | 2 | slumped, swaying left/right (engine draws stars) |
| 39 | pickup | 1 | crouching, hands down near feet |
| 40 | carry | 2 | both hands overhead (hands at y≈12), legs mid-walk A/B |
| 42 | throw | 2 | windup (arms back overhead), release (arms forward) |
| 44 | swing | 3 | weapon swing: raised back, mid swing, follow-through low-forward |
| 47 | sweep | 2 | low crouch spin, leg extended forward / leg extended back |
| 49 | rising_kick | 2 | deep crouch, leg straight up rising |
| 51 | slam | 1 | dropping body slam, knees down, fists together overhead |
| 52 | victory | 2 | fist pump down / up |
| 54 | talk | 2 | relaxed stance, mouth closed / open with a hand gesture |
| 56 | cower | 2 | crouched, arms over head, trembling offset |

- Weapons are **not** drawn on characters. Each sheet has a JSON sidecar giving the front-hand grip point and weapon angle for every frame, so the engine can attach any weapon sprite:

```json
{
  "id": "nico", "cell": [64, 64], "anchor": [32, 60], "columns": 8,
  "anims": {"idle": [0, 2], "walk": [2, 4], "...": [0, 0]},
  "hand": [[44, 38, 0], [44, 37, 0], "... one [x, y, angle_degrees] per frame (58 entries)"]
}
```

Angle 0 = weapon points right (horizontal), -90 = straight up, 90 = straight down.
For `carry` frames the hand point is the top-center point between the hands (where a
carried object's bottom sits).

### Body types

| type | height (px, feet→top of hair) | notes |
|---|---|---|
| normal | ≈ 46 | default |
| slim | ≈ 46 | narrower torso/limbs |
| heavy | ≈ 48 | wide belly/torso (≈ 26px wide) |
| big | ≈ 54 | boss bruiser (Otto); broad shoulders, huge fists |
| tall | ≈ 50 | Rook, Rhea Pike |
| kid | ≈ 36 | Pip, Teddy |
| elder | ≈ 42 | slight stoop (Mrs. Alvarez, Mr. Hollis, Dot) |

### Portraits

- **64×64 bust**, transparent background, 5 expressions in one strip **320×64**: `neutral, happy, angry, surprised, sad` (columns 0–4).
- Face 3/4 view facing right, shoulders visible at the bottom, 1px outline, 3-tone shading. Large expressive eyes; eyebrows carry emotion.
- File: `game/assets/portraits/<id>.png`.

### Cast (sprite id → description)

Story cast:
- `nico` — **Nico Vale**, player, ~20, delivery worker. Tan skin, messy spiky black hair, red headband. Mustard-yellow windbreaker with a red chest stripe over a white tee, blue jeans, red sneakers. Determined eyebrows. Body: normal.
- `mara` — **Mara Quinn**, mechanic, ~21. Deep skin, big curly hair in a high puff tied with a green bandana. Teal coverall with sleeves tied at waist, white tank top, brown work boots, grease smudge on cheek. Body: normal.
- `eli` — **Eli Mercer**, Nico's missing best friend, ~20. Light skin with freckles, wavy auburn hair, round glasses, green varsity jacket over a gray hoodie, khaki pants. Body: slim.
- `rook` — **Victor Rook**, antagonist, ~38. Slicked-back black hair with gray temples, scar through left eyebrow, charcoal long coat over a burgundy turtleneck, dark slacks, black gloves. Calm, heavy-lidded eyes. Body: tall.
- `rook_p2` — Rook phase 2: coat off, sleeves rolled, turtleneck torn at the shoulder, hair loose. Body: tall.
- `dot` — **Dot Kessler**, diner owner, 60s. Plump, gray beehive hair, pink waitress dress with white apron, cat-eye glasses. Body: elder (wide).
- `jett` — **Jett Vance**, acrobatic rival, ~19. Bleached-blond flat-top with shaved sides, sleeveless purple jacket, neon-green tank, black bike shorts over gray leggings, white high-tops, wristbands. Body: slim.
- `gus` — **Gus Pereira**, rail switchman/witness, 50s. Bushy gray mustache, flat cap, orange safety vest over a denim shirt, brown trousers. Body: heavy.
- `duke` — **Duke Brannigan**, Chain Dogs leader, ~25. Red mohawk, black leather vest over a red tee, chain draped across shoulders, ripped jeans, black boots. Body: heavy.
- `rhea` — **Rhea Pike**, market crew twin (pole fighter), ~24. Long dark braid, yellow rain slicker, rubber fishmonger apron, green rubber boots. Body: tall.
- `lou` — **Lou Pike**, the other twin (thrower), ~24. Dark bob haircut, orange slicker, apron, green rubber boots, satchel of throwables. Body: normal (short).
- `otto` — **Otto Kragg**, heavy foreman, 40s. Huge. Bald with a thick brown beard, yellow hard hat, gray work shirt with rolled sleeves, suspenders, giant tan work gloves. Body: big.
- `sabine` — **Captain Sabine Holt**, Gray Jacket enforcer captain, 30s. Short platinum hair, gray security jacket with red armband, black cap, black gloves, black boots. Sharp stern eyes. Body: normal.
- `price` — **Officer Dana Price**, honest cop, 30s. Navy police uniform, cap, dark ponytail. Body: normal.
- `hollis` — **Mr. Hollis**, bookshop owner, 70s. Bald with white fringe, thick glasses, brown cardigan, red bow tie. Body: elder.
- `benny` — **Coach Benny**, rec-center boxing coach, 50s. Stocky, deep skin, bald, gray goatee, red tracksuit, whistle. Body: heavy.
- `lacey` — **Lacey Tran**, arcade champion, ~17. Black bob with a pink streak, oversized denim jacket with pins, black tee, checkered sneakers. Body: slim.
- `pip` — **Pip**, arcade kid, ~12. Backwards blue baseball cap, striped red/white shirt, shorts. Body: kid.
- `alvarez` — **Mrs. Alvarez**, dog owner, 70s. Gray bun, purple shawl, floral dress, cane (drawn in hand). Body: elder.
- `fong` — **Mr. Fong**, noodle bar cook, 40s. White chef coat, red headband, cheerful. Body: normal.
- `rosa` — **Rosa Delgado**, pharmacist, 30s. Curly dark hair, white coat over teal blouse. Body: normal.
- `bigmo` — **Big Mo**, alley challenge host, 40s. Heavy, fedora, loud orange Hawaiian shirt, gold chain, sunglasses. Body: heavy.
- `teddy` — **Teddy**, newsie kid, ~13. Flat cap, brown vest, newspaper bag. Body: kid.
- `hank` — **Hank**, canteen cook, 50s. Paper hat, stained apron over white tee, thick forearms. Body: heavy.
- `marv` — **Marv**, arcade attendant, 40s. Comb-over, red arcade vest with name tag, glasses. Body: normal.
- `towna`, `townb`, `townc`, `townd` — ambient neighbors (varied: a jogger in a tracksuit; a man in a suit with briefcase; a teen in a hoodie; a woman with grocery bag).

Gang members — 5 gangs × 6 archetypes = 30 sheets, id `<gang>_<archetype>`:
- Archetypes and body: `brawler` (normal), `flanker` (slim, light on feet), `blocker` (normal, arm pads/forearm guards), `heavy` (heavy), `weapon` (normal, tougher look), `thrower` (slim, shoulder bag).
- `dogs` — **Chain Dogs** (Old Quarter): black leather + red; spiky hair, mohawks, studded wristbands, ripped jeans.
- `rats` — **Wharf Rats** (Canal Market): yellow/olive rain gear, knit beanies, rubber boots, rolled-up sleeves.
- `yard` — **Yard Boys** (Ironworks): orange safety vests, hard hats or welding caps, denim overalls, soot smudges.
- `saints` — **Neon Saints** (Neon Mile): purple and cyan satin jackets, shades, pompadours/side-shaves, white sneakers.
- `grays` — **Gray Jackets** (Rook's private security): gray jackets, red armbands, black caps, black pants, stern faces. Heavies wear padded vests.
- Gang portraits: one 320×64 strip per gang (`game/assets/portraits/<gang>.png`) showing a representative member.

Animal:
- `biscuit` — scruffy tan terrier mix with a red collar. Cell 32×32, anchor (16, 30), 4 columns × 2 rows: `idle` 2, `walk` 4, `sit` 1, `bark` 1.

## 4. Environments

- Each room background is one PNG `game/assets/bg/<room_id>.png` sized `width × 360` from `game/data/rooms.json`.
- Vertical bands: **back wall/facades y 0–214**, **ground y 214–360**. Walkable ground is y 218–344; the strip below 344 is a darker foreground curb/edge.
- Doors sit on the facade with their bottom edge at y=214, about 30×50 px, clearly readable (lit doorway or contrasting frame, a small sign or awning above).
- Interiors (`int_*`): back wall y 0–196, floor 196–360, walkable 232–344.
- Each district has a parallax far layer `game/assets/bg/parallax_<district>.png` (960×220, horizontally tileable) seen above or between buildings.
- Props are separate y-sorted sprites (`game/assets/props/<type>.png`) with bottom-center anchor and a ground footprint for collision (see `game/assets/props/props.json`).
- Keep decorative clutter out of the walkable band unless it is a solid prop with a footprint.

| District | Look | Ground |
|---|---|---|
| Old Quarter | warm red brick, sunset light, laundry lines, stoops, warm windows | gray sidewalk strip + asphalt street with faded lane line |
| Canal Market | striped canvas awnings, timber stalls, bunting, bright day | cobblestones; wooden boardwalk planks near the canal |
| Ironworks Yard | rusted sheds, smokestacks, cranes, orange dusk | gravel + embedded rail tracks (horizontal) |
| Neon Mile | night, glowing signs, theater marquee, wet asphalt reflections | dark asphalt with colored reflection streaks |
| Floodgate Road | storm night, river railing, floodgates, sodium lamps | wet road, puddles |
| Rook's Warehouse | dim interior, steel shelving, crates, hazard stripes, conveyor | concrete with yellow safety lines |

## 5. UI

- Font: original pixel font `game/assets/fonts/oath_pixel.ttf` (5×7 caps, 8px em). Rendered at 8px (normal) or 16px (large text option). Title lettering is hand-made art.
- Panels: dark plum `#1a1220` at 92% with a 2px warm cream border `#e8d8b0` and a 1px inner shadow; corners notched.
- Highlight color: mustard `#f0c040`. Danger: `#e04a4a`. XP: `#4af0f0`. Cash: `#7af04a`.
- Never use color alone for information: HP bars carry numbers, quest status carries text tags, prompts carry glyph letters.
- Icons 16×16 with 1px outline.

## 6. Animation timing (engine, at 60 ticks/s)

| anim | ticks/frame |
|---|---|
| idle | 30 |
| walk | 8 |
| run | 5 |
| attacks | from attack data (startup → windup frame, active → impact frame, recovery → follow frame) |
| knockdown | 6 / held / held |
| getup | 10 |
| dizzy | 12 |
| talk | 14 |
