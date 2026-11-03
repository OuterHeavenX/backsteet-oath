# Changelog

## 1.3.0-rc1 (2026-11-03): living, more real backgrounds
- **Streets that move:**
  - **Sky:** clouds drift.
  - **Windows:** lights switch on and off, silhouettes cross behind curtains, and TVs flicker.
  - **Passersby:** townsfolk stroll along the sidewalk when the street is quiet, and hurry off when a fight starts.
  - **Pigeons and birds:** pigeons scatter as you walk up, and birds cross the sky.
  - **Cloth and signs:** laundry, bunting, flags and hanging signs sway. Neon signs chase, blink and buzz.
  - **Traffic:** distant cars with headlights, and trains on the rail and elevated lines.
  - **Water and light:** canal water and puddles ripple, and light shafts with drifting dust come through
    windows, skylights and grates.
- **More real-looking art** in all 33 rooms (the inked style is kept):
  - **Lighting:** facades get light gradients and light pools, with soft shadows in corners, under ledges and in
    doorways.
  - **Surfaces:** brick, concrete, wood and metal texture, plus grime, water stains, soot, peeling paint and torn
    posters.
  - **Glass:** varied window interiors (blinds, curtains, plants, lamps) behind glass with reflections.
  - **Wet streets:** coloured light streaks on wet roads in the rain and night districts.
  - **Distance:** far layers are softly blurred and hazed for depth.
- **Camera finish:** a subtle per-room colour grade and vignette, plus a restrained glow on the brightest lights.
  This can be turned off in **Settings → Colour grade & bloom**, and is off by default in browsers on phones and
  tablets.
- **Effects: Reduced** turns off the expensive parts: the grade, traffic, distant pedestrians, trains, birds,
  light shafts and sign animation.

## 1.2.0-rc1 (2026-11-02): a longer game
- **New story chapter, "The Underline"** (Act III opener, on the main path):
  - Mara works out that Greyline moves its cargo under the river. The Neon Mile rooftops' fire escape drops into
    the abandoned 1971 subway.
  - Three new rooms, fought through in order: Kessler St. Station, Service Tunnel 3 and the Greyline Cargo Vault.
  - A new gang, **the Moles**, Greyline's tunnel crew in hard hats and hi-vis.
  - A new boss, **Ruth "Lantern" Kowal**. She wields a shovel, and at half health she kills the lights: the vault
    goes dark except for her lantern, and two Moles join in.
  - Beating her opens the service ladder to Floodgate Bridge and a new journal entry about the stolen deeds.
  - New music track for the Underline.
- **Benny's ladder** (Rec Center, after Duke): nine bouts against every gang, scaled to your level, ending with
  champion **Mae "Iron" Okafor**.
  - Rewards: cash and XP per bout, the **Ladder Belt** at bout five, and the **Iron Wraps** for beating Mae.
  - A knockout ends the night: no defeat screen and no penalty.
  - Replayable, and your best bout is recorded.
- **Four new side jobs:**
  - **Static on the Line** (Ines, Neon Mile pharmacy): win back the ambulance radio from the Saint called Flicker.
  - **Last Train Home** (Otis, Kessler St. Station): find a conductor's brass punch in the tunnel crates.
  - **Wet Paint** (Kiki, Canal Market gate): run two tagger crews off her mural.
  - **Heavy Thumb** (Sal, Canal Walk): take rigged weights from three Greyline inspectors in three districts.
- **New Game+:** finished saves can restart the story from the title screen.
  - You keep your level, stats, techniques, gear, bag and cash.
  - Each cycle, enemies gain +35% HP and +25% power plus one tier, every wave brings an extra fighter, and bosses
    gain +40% HP. XP and cash grow +25% per cycle.
  - An NG+ badge shows on the HUD.
- **New items:** a new weapon (the shovel) and two gear pieces. The map shows the Underline.
- The save format is unchanged, and older saves load. Saves already past the garage scene can walk the Underline
  but skip its boss.

## 1.1.0-rc2 (2026-11-02): playtest reporting
- **Show FPS** (Settings): a small corner readout with the current frame rate and the slowest recent frame, coloured
  green at 55 FPS and above, amber at 30 FPS and above, red below that.
- **Run summary card** after the ending, before the credits. It shows the run (play time, difficulty, level,
  enemies, knockouts, meals, cash, side jobs) and how the game ran on this device:
  - average FPS, share of frames under 30 FPS, slowest frame;
  - effects setting, window and view size, version;
  - OS and GPU/driver.

  Frames are counted only during gameplay: not paused, not during room transitions, and not in the first second
  after a room loads. Screenshot the card to report a playtest.

## 1.1.0-rc1 (2026-11-02): visual upgrade
The same game, redrawn. Story, quests, combat timing, controls and saves are unchanged; rc1–rc4 saves load.
- **One art direction:** inked, cel-shaded 2D illustration at 2× density, rendered at window resolution
  (`docs/ART_DIRECTION.md`). Before/after comparisons and footage: `docs/visual/`.
- **Characters (all 60):** full animation sets built on a vector rig.
  - Every attack has anticipation, contact, follow-through and recovery frames.
  - Walk and run cycles advance with distance travelled, so feet don't slide.
  - Spring-driven hair and cloth, and faces drawn per frame.
  - Distinct high, low and from-behind hit reactions, and a five-phase knockdown.
  - Per-archetype stances, plus signature boss idle and victory poses.
  - 29 new 192 px portraits.
- **Rooms (all 30):** each has its own district identity and a fixed collision layout.
  - Parallax skies and skylines, and foreground framing that fades when a fighter is behind it.
  - Authored light that tints fighters by where they stand, glows with neon, flame and fluorescent flicker, and a
    rim light from nearby lights.
  - Contact and cast shadows, wet-ground reflections, and ambient steam, sparks, embers and drips.
  - The Pier Square drawbridge is shown lowered after it opens.
- **Combat presentation:** impact effects for fists, kicks, metal, wood, glass, stone and soft objects, with
  debris thrown in the hit's direction. Swing arcs, dust, and directional camera kicks.
- **Story scenes:** letterbox bars and a slow push-in, location and boss name cards, and a phase-change beat.
  The opening, rescue and revelation have new framing, the ending gets a new backdrop, and scenes change with a
  patterned wipe. All scenes can still be skipped.
- **UI:** new typefaces (Bungee and Barlow, SIL OFL) at larger sizes, and brass-framed panels. The HUD has a portrait
  that reacts to HP and combat, and HP/boss bars that show damage as a trailing bar. Dialogue shows 96 px
  portraits, and the title screen is parallax.
- **New settings:** Effects (Full/Reduced) and Cinematic bars.
- **Web:** canvas pixel ratio capped at 1.5 for phones; textures are palette-optimised, so the download is 56.7 MB.
- Includes the 1.0.0-rc4 fix for silent audio in browsers.

## 1.0.0-rc4 (2026-11-02): audio fix for the browser build (tester feedback)
- **Music and sound effects now play in the web build.** Godot's web audio plays sounds as Web Audio samples routed
  by bus. The Music/SFX buses were created after startup, so every sound was routed nowhere and browsers stayed
  silent. They are now defined in `default_bus_layout.tres`.
- **iPhone/iPad:** the first tap starts a silent audio element, so the ring/silent switch no longer mutes the game.

## 1.0.0-rc3 (2026-11-02): tablet dialogue fix (tester feedback)
- Conversation boxes with choices (shopkeepers' Shop / Chat / Leave, quest questions) now grow upward from the
  bottom of the street, so every option stays visible above the touch control deck.
- The touch control deck always draws underneath the HUD and dialogue.
- Shop counters block the space behind them, so Nico can no longer walk behind or "onto" a counter.

## 1.0.0-rc2 (2026-11-02): touch & device identity pass (tester feedback)
- **Tablets:** the street sits on top and the touch controls get their own deck underneath (no overlap).
  The screen now fills taller displays instead of letterboxing.
- **Phones:** the controls disappear while a conversation or cutscene is on screen.
- **Context ACTION button:** replaces GRAB and relabels itself TALK / ENTER / PICK UP / LIFT / GRAB / THROW / BUS,
  glowing when there's something to do.
- **Buttons:** clear word labels (PUNCH, KICK, JUMP, GUARD, RUN, ACTION). On wide decks the labels sit under
  the buttons. BAG and PAUSE moved into the deck.
- **Dialogue:** tap anywhere on the street to continue, a visible **SKIP** button, and device-aware hints
  ("Tap to continue", "(A) Next (B) Skip", "[J] or [Enter] Next [Esc] Skip").
- **Menus:** every menu has a visible **< Back** button. Keyboard-only hints are hidden on touch, and touch
  buttons are taller.
- **Device detection:** browsers on phones and tablets start in touch mode ("TAP TO START", touch prompts
  everywhere). Touch controls show only while touch is in use, so keyboard and controller players never see them.
- Controls screen explains the touch layout.

## 1.0.0-rc1 (2026-11-02)
First complete build (release candidate pending a human playtest).
- Full campaign: prologue, three acts, ending, credits, postgame free roam.
- Six districts, 20 combat rooms, 10 interiors, River Line bus, rail-tunnel shortcut.
- Six bosses, story duel and mini-boss; 6 enemy archetypes × 5 gangs; attack-token AI with lane spacing.
- Combat: combos, finishers, guard/perfect guard, running/jump attacks, carry & throw, 16 weapons in 6 families.
- RPG: levels 1–20, five stats, stat points with balanced auto-spend, capped food boosts, 10 techniques,
  weapon mastery, workbench upgrades, respec.
- Six side jobs; journal with objective recap; district map.
- 3 save slots with backup/corruption recovery, versioned saves with migration, JSON export/import.
- Settings: audio buses, difficulty, shake/flash, text speed, large text, touch controls, deadzone, fullscreen.
- Rebindable keyboard/controller bindings; mobile touch controls with multi-touch; portrait-rotation notice.
- Original procedurally generated art, fonts, music and sound effects.
- Automated tests: unit (574), features (65), side quests (23), full-campaign autoplay bot.
