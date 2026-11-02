# Content expansion (1.2): longer game

Goal: about +12–18 min on the main path, +30–45 min optional, and New Game+ for replay. Nothing here changes
existing combat timing or the save format; new fields default safely.

## 1. Story chapter: "The Underline" (new stage `underline`, Act III opener)
**Flow:**
1. Garage setback scene.
2. Mara works out that Greyline moves its cargo *under* Floodgate Road, through the Underline, an abandoned
   1970s subway under the river.
3. The stage becomes `underline`.
4. The Neon Mile rooftops fire escape (`act3_started`) leads down into **Kessler St. Station** (`ul_station`).
5. **Service Tunnel 3** (`ul_tunnel`).
6. **Greyline Cargo Vault** (`ul_vault`). Boss: **Ruth "Lantern" Kowal**, foreman of **the Moles**, Greyline's
   tunnel crew.
7. Her defeat sets the stage to `floodgate`.
8. The service ladder (east exit) climbs to Floodgate Bridge, where Jett's crew is waiting (the alliance scene is
   unchanged).

**Rooms** (geometry in `data/rooms.json`; district `underline`, tier 5, music `underline`):
| Room | Width | Look |
|---|---|---|
| `ul_station` | 1600 | Abandoned platform: grimy white tile, "KESSLER ST" mosaic, peeling 1970s ads, "CLOSED 1971", a few failing fluorescents, warm Mole work lights |
| `ul_tunnel` | 1920 | Arched service tunnel: track bed and rails behind the walkway, cable trays, cage lamps (sodium), puddles, steam pipes, a Mole camp with an oil-drum fire |
| `ul_vault` | 1120 | Vaulted old pump room turned Greyline depot: stencilled crates, a hanging work-lamp cluster, chained service ladder at the east end |

**Boss mechanic:**
- At 50% HP, Kowal kills the lights: the room's light drops to about 45%, and a lantern glow follows her. Fighters
  stay readable through the rim light.
- She calls two Moles.
- Moveset: long pole jab, low sweep, spin, charge.

## 2. The Moles (gang `moles`)
- Ids: `moles_brawler`, `moles_flanker`, `moles_blocker`, `moles_heavy`, `moles_weapon`, `moles_thrower`.
- Kit: hard hats with headlamps, orange hi-vis vests with reflective stripes over navy coveralls or hoodies, dust
  masks pulled down, work gloves, steel-toe boots.
- Palette: orange `#e8742a`, navy `#2b3a55`, dust tan `#b8a27a`.
- Weapons: shovel (new), pipe and wrench. They throw bricks.

## 3. Rec Center Ladder (Coach Benny, `int_rec`)
- **Bouts:** nine, against mixed-gang opponents scaled to the player's level. Bouts 3 and 6 are duos; bout 9 is the
  champion, **Mae "Iron" Okafor**.
- **Between bouts:** heal 30%.
- **Losing:** a KO ends the ladder without the defeat screen, at 50% HP, and keeps the rewards earned so far.
- **Rewards:**
  - cash per bout;
  - first clear of bout 5: the **Ladder Belt** (gear);
  - first champion win: the **Iron Wraps** (gear) and a title in the journal.
- **Replay:** always replayable, and the best bout is recorded.

## 4. Four side jobs
| Id | Name | Giver (new NPC) | Unlock | Steps |
|---|---|---|---|---|
| `radio` | Static on the Line | Ines Duarte, night pharmacist (`int_pharmacy`) | stage ≥ neon | Get the ambulance radio back from the Saint "Flicker" in Big Mo's Alley → return it |
| `punch` | Last Train Home | Otis Bell, retired Underline conductor (`ul_station`) | stage ≥ floodgate | Find his brass conductor's punch in the crates of Service Tunnel 3 → return it |
| `mural` | Wet Paint | Kiki Moreno, teen muralist (`cm_gate`) | boss_duke | Run off two waves of Chain Dog taggers in the Chain Lot → tell Kiki |
| `weights` | Heavy Thumb | Sal Bianchi, fishmonger (`cm_canalwalk`) | stage ≥ floodgate | Take rigged weights from Greyline "inspectors" at Pier Square, Ironworks Gate and the Marquee Strip (0/3) → return them |

## 5. New Game+
- **How to start:** completed saves offer **New Game+** from the title screen.
- **Kept:** level, XP, stat points, allocations, food boosts, techniques, cash, bag, weapon upgrades and mastery.
- **Reset:** story, flags, quests, keys and bosses. Run stats reset; total play time carries over.
- **Each cycle `n`:**
  - enemy HP ×(1 + 0.35n) and power ×(1 + 0.25n), tier +1 (capped at 6);
  - one extra enemy per wave;
  - boss HP ×(1 + 0.4n);
  - XP and cash ×(1 + 0.25n).
- **HUD:** an "NG+" badge.

## 6. New art (generators)
- **Characters:**
  - Fighters: 6 Moles, `kowal` (boss, tall, long grey braid, lamp hard hat, olive oilskin coat over hi-vis, goggles,
    shovel) and `mae` (champion, athletic, boxing wraps, "BENNY'S" tank top, track pants, hair tied up).
  - Civilians: `ines` (scrubs and cardigan, lanyard, readers), `otis` (conductor cap, cardigan, white moustache),
    `kiki` (paint-splattered overalls, bucket hat, spray can) and `sal` (rubber apron, rolled sleeves, flat cap).
  - Portraits: kowal, mae, ines, otis, kiki, sal, and the `moles` gang portrait.
- **Environment:** `underline` district kinds and the 3 rooms above.
- **UI:**
  - weapon `shovel` (weapons2 + icon `w_shovel`);
  - pickups and icons `radio`, `conductor_punch`, `scale_weight`;
  - gear icons `ladder_belt` and `iron_wraps`;
  - the map with an Underline marker.
