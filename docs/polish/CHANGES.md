# Gameplay, presentation and performance polish: what changed and why

Branch `claude/gameplay-polish`, built on the 1.3.0-rc1 tree (`origin/main` 4b22770). Version in this branch:
1.4.0-rc1. Nothing was published, merged into `main`, or uploaded.

Each entry says what a player now experiences, why it was chosen, and where it lives. Items marked
**needs players** are design hypotheses that only a playtest can settle (see `FOLLOW_UPS.md`).

## 1. The opening teaches by doing (Kettle Street to Duke)

| What the player gets | Why | Where |
|---|---|---|
| One tip on screen at a time. It stays until the action is really done (a landed combo, a blocked hit, a thrown object, a door entered) or is skipped from the pause menu. A green "GOT IT!" confirms the action that cleared it. | The 1.3 opening showed three timed hints that vanished whether or not anything was learned, and progress followed enemy defeats only. | `game/scripts/core/tutor.gd`, `hud.gd` |
| The two Chain Dogs keep leaning on Dot until Nico walks up, swings, or skips: a safe moment to learn to move and line up. One attacker at a time in this first fight. | "Teach through safe situations" without adding a separate tutorial room. Tips never gate anything: the fight still ends when the Dogs are down, with tips on, off or skipped. | `story.gd` `_intro` |
| The first Dog drops a bottle; the third Dog shows off for two seconds when he arrives. | The old hint pointed at a trash can 350 px away. Now the thing to throw is at Nico's feet at the moment the tip appears. | `story.gd` |
| Dot serves one plate on the house: it heals and adds a permanent +2 max HP, and the message says so (with a different line at full health or at the food cap). | Shows the game's core loop (eat, get stronger for good) before any money is spent. Saved at once, so it can never be served twice. | `story.gd` `_dot_meal` |
| Coach Benny teaches Shoulder Charge for free, then two optional sparring rounds: a patient partner to run at, then a blocker with a tire to throw. Sparring partners tap out instead of being knocked out, give no XP or cash, and a knockout costs nothing. "Spar a round" stays in his menu before Duke. | The cheapest manual teaches running, which nothing else taught, without making his other manuals pointless. The blocker round introduces guard-breaking in a place where failure is free. | `story.gd` `_benny_lesson`, `_spar` |
| Pause > Help & tips > Fighting tips lists everything the opening teaches plus the inputs of learned techniques, in the current device's labels. | "Keep a way to revisit instructions." | `tips_menu.gd`, `help_menu.gd` |
| A newly learned technique gets a short reminder at the start of later fights until it is used once; it retires by itself. | So a manual bought in a shop is not forgotten by the next street. | `Tutor.arm_skill` |
| Saves from before this change are not sent back through any of it; the favours are offered only while such a save is still in the Old Quarter chapter. New Game+ skips the opening tips. | Requirement: existing saves are not forced into the new opening. | `tutor.gd`, `story.gd` |

## 2. Fighters and fights are easier to read

| What the player gets | Why | Where |
|---|---|---|
| The camera moves in to 1.16x during fights, eases back out 2.5 s after the last enemy, and leans toward the enemies instead of swinging with every turn. The bottom of the street stays fixed on screen. **Settings > Combat camera: Close / Wide.** | Screenshots showed fighters at about 13% of screen height with bright shop fronts competing for the eye. Enemy "on screen" tests use the framed width, so nothing can attack from outside the closer view (tested). **needs players**: the zoom amount. | `room.gd` `_update_camera`, `data/tuning.json` |
| A thin cream keyline and a small ground ring on Nico. | Separates him from enemies and dark backgrounds (most visible in Kowal's vault). | `combat_marks.gd`, `actor.gd` |
| A ring under any enemy standing in Nico's lane; it turns to the danger colour while that enemy winds up. | The commonest belt-scroller confusion is "why didn't that hit?". The ring answers it without text. | `room.gd` `_update_guides` |
| A ring on things that can be lifted or picked up when Nico is near with free hands, and a pulsing outline on the one the Action button would take. | Distinguishes usable objects from scenery. **Settings > Combat guides: On / Off** switches all three aids. | `prop.gd`, `pickup.gd` |
| Three kinds of attack tell, each with its own badge shape, body tint and sound: a red warning triangle (heavy, can be guarded), a purple crossed shield (cannot be guarded: step away or jump), an orange cracked shield (breaks a guard). Attacks that hit all around mark the ground they will cover. | 1.3 used one red flash and one "!" for everything. Shape and sound still read with flashes turned down or off (tested with flash 0). | `combat_marks.gd`, `enemy.gd`, `tools/audio/gen_audio.py` |
| Telegraphed attacks lean back, lunge and settle, driven by the attack's own start-up/active/recovery ticks. Very fast wind-ups hold one pose instead of flickering two frames. | Result of `tools/anim_audit.py` (`ANIM_AUDIT.md`): the basic combo and every telegraphed attack already agreed with hit timing; these were the two real defects. | `actor.gd` |
| Camera kicks are the same size on screen at any zoom; timed hints no longer sit over conversations; the action prompt sits above the boss bar. | Small defects found while capturing. | `room.gd`, `hud.gd` |

Hit-stop, impact effects and input buffering were reviewed against the attack data and left as they were:
there was no measurement here that justified changing them, and no way to feel them. They are in the follow-ups.

## 3. Decisions and consequences in the opening

| What the player gets | Why | Where |
|---|---|---|
| "Duke's lieutenants" (Chain Lot): a blocker stands between Nico and a bottle-thrower. A crate and a trash can are in reach. A full combo, a heavy throw, getting behind him, or going round to the thrower all work. | The 1.3 wave was three fighters arriving from random sides. Heavy objects thrown by the player now break a raised guard, and enemy bottles no longer smash crates left for the player. | `encounters.json` c3, `enemy.gd` `protect`, `projectile.gd` |
| When Duke falls, neighbours walk into the Chain Lot, Duke leaves, and a card reads "Old Quarter: the Chain Dogs are off the street. People are coming back out." From then on there are no Chain Dog patrols in the Old Quarter, residents stand on Kettle Street, Brickrow and in the diner, a regular waits for the bus that runs again, and passers-by walk the streets (before Duke there are none). | The player goes east after Duke, so the change has to start where they are standing. It is derived from the boss flag alone, so it survives save/load, works for older saves, and resets in New Game+. | `story.gd` `_duke_aftermath`, `GameState.district_calm`, `story.json` districts |

## 4. Across the campaign

| What the player gets | Why | Where |
|---|---|---|
| Every district calms down once its gang boss is beaten: patrols lose one fighter and return half as often, passers-by come back, and a one-time card says so. | Backtracking through streets whose boss was already beaten was the largest block of repeated fighting in the bot's run (298 enemies before, 254 after the opening milestone, same final level). | `room.gd` `_is_patrol`, `room_life.gd` |
| Kowal's vault has three work lights. At half health she leaves one on and fights by her lantern. She walks over to put lit ones out with a slow telegraphed swing: hit her in the wind-up and the light is saved; afterwards she is winded. Nico can switch a light back on with Action. Her Moles only climb out while every light is dark (two waves at most, one on Relaxed). A "LIGHTS 2/3" counter, toasts and sounds carry the state. | Turns the existing one-off blackout into a decision: spend a moment on a light, or keep hitting her in the dark while Moles arrive. The floor never goes below the 1.3 darkness level, tells and rings are unaffected by darkness, and the fight can always be finished with every light out (tested). | `work_light.gd`, `boss.gd`, `room.gd` |
| Storage Floor: the big lock fight runs under a crane that drops crates on two marked spots in turn (it hurts whoever stands there, and leaves a crate to throw), with one fighter fewer. The two waves after it are replaced by a 24-second run to the office door: make it and the door crew is skipped for a bonus (300 XP, $40) that stands in for the fight; miss it and the shutter is forced by beating that crew. | Storage Floor was the longest single room before a boss (17 fighters in four waves). The run changes the rhythm from "another wave" to pressure and payoff, and failing it only means the old kind of fight. | `encounters.json` rw_storage, `room.gd` crane, `story.gd` `_storage_run` |
| New Game+: enemy scaling stops growing after cycle 3; each wave gains the kind of fighter it lacks (a thrower, then a blocker that covers it) instead of a copy of someone already there; from cycle 2 one brawler comes armed; bosses keep their attacks and tells but change thresholds and tempo (Duke whistles three times, Kowal starts the lights earlier, Rook's crates fall faster). | 1.3 scaled health without limit (4x by cycle 9) while the player's damage is capped by level 20 and food caps. The attacker cap is unchanged (tested). | `room.gd` `ngplus_wave`, `boss.gd`, `tuning.json` |
| A fix: a second boss fight could start in the pause before a boss's defeat scene if the player stood past the trigger line. | Found while capturing the new Duke scene; it predates this work. | `room.gd` `boss_done` |

## 5. A neighbourhood that remembers

Everything here is derived from saved quest states and boss records, so it works on older saves and in the
postgame, is silent when a side job was skipped, and resets in New Game+ (`game/tests/consequence_tests.tscn`).

| What the player gets | Why | Where |
|---|---|---|
| **Wet Paint:** the low wall under the Canal Market arch shows Kiki's old mural, primed over and tagged, until the job is done. On completion there is a short unveiling: the wall changes in front of the player to her finished mural (the canal, the bridge, the diner, everybody, and Nico with a cape), and Kiki stands beside it from then on. | The quest ended on a line of dialogue with nothing to see. The art is original and generated by the project's own tools. | `tools/art2/env/mural.py`, `cm_gate/room.json` (story-gated layers), `Story._mural_unveil` |
| **Static on the Line:** Ines and Rosa acknowledge the recovered ambulance radio, and the pharmacy gives 15% off from then on. The shop shows the list price, the reduced price and the reason. | "A modest service benefit where suitable." | `shops.json` discount, `GameState.price_for` |
| **People you helped stay helped:** Miss Hollis is at Pier Square after the escort; Lacey, Pip and Marv stop repeating their pre-job lines (they used to); Mara, Otis and Sal have a line for their finished jobs. | An audit of all ten side jobs: each giver is now found somewhere identifiable and says something that fits. | `encounters.json`, `dialogue.json` |
| **One returning resident per district** once its boss falls, each with a line that names what changed, alongside the thinner patrols and the passers-by. | Extends the Old Quarter pattern to the Canal Market, Ironworks, Neon Mile, Underline and Floodgate. | `encounters.json` |
| **The ending:** up to three people whose side jobs were finished sit in the diner for the final scene and say one line each, chosen by a fixed priority. With no side jobs done the scene is the original, line for line. If the radio was returned, Mara mentions it and a bandage is waiting before Rook. | Favours show up when it matters, without making a main-story-only ending feel incomplete. | `Story._rook_ending`, `ENDING_FAVOURS` |

## 5b. Understandable progression

Previews are computed by running the game's own code on throwaway fighters and then restoring the save state
exactly, so there are no duplicated formulas to drift (`game/scripts/core/preview.gd`; 418 checks in
`game/tests/progression_tests.tscn` compare every preview with what really happens).

| What the player gets | Why | Where |
|---|---|---|
| Food rows say what eating **now** would do: "HP 38/60 -> 62/62; Max HP +2 for good: 60 -> 62 (food bonus 0 -> 2 of 30)". Capped and partly capped bonuses are called out; the existing "(maxed)" labels stay. A meal that would change nothing is refused without a charge. | The shop showed list effects only; whether a dish would be wasted at full health or at the cap was left to the player. | `shop_menu.gd`, `preview_text.gd` |
| Mara's workbench shows damage and durability before and after for a named reference weapon and fighter. Status shows what the next stat point, mastery level or workbench tier changes, in concrete numbers with the reference case named ("against a Chain Dogs brawler"). | Damage depends on the move, the weapon and the target, so every number names its case instead of implying a universal value. The reference fighter follows the toughest district reached. | `status_menu.gd` |
| Pressing a manual opens a free preview: Nico performs the move with its real start-up, active and recovery timing, with the input for the current device, what it is for, and its damage against the reference fighter. Buy is only on that page. Learned techniques can be re-watched. | "Let players preview a manual's input and purpose" without charging or changing state. | `manual_preview.gd`, `move_demo.gd` |
| Buying a manual arms its reminder for the next fights. | See section 1. | `Tutor.arm_skill` |
| Status > Build ideas: brawler, weapon specialist, counter fighter. Each names the stat to favour (with its live next-point numbers), the cheapest dishes that raise it and where they are sold, and each manual's shop and whether it is learned, on the shelf or not yet. Advice only; nothing is locked or applied. The level-up banner points at it. | Lightweight guidance from existing systems, not classes. | `build_guide_menu.gd` |
| All prices go through one function, so the price shown is the price charged; a standing discount shows the list price and its reason. Shoulder Charge is not sold while Benny's free lesson is still on offer. | Needed for the pharmacy's thanks (section 5) and to stop a wasted purchase. | `GameState.price_for`, `shop_menu.gd` |

The economy was reviewed, not retuned: see `ECONOMY_REVIEW.md`. In short, income is back-loaded, permanent food
is by far the strongest purchase (about $250 reaches every cap), and nothing needs farming.

## 5c. Performance and load

Full detail, commands and evidence: `PERF_REPORT.md`. **Every number is from a software renderer in a container.**
They compare builds on one machine; they say nothing about real GPUs, a Steam Deck or phones.

| What changed | Measured here | Why | Where |
|---|---|---|---|
| The colour grade and bloom pass no longer asks the engine for a blurred copy of the whole screen every frame; it blurs a small copy itself. | 7 to 15 ms less per frame on the software renderer in four scenes (for example Kettle Street with eight enemies: 53.4 to 41.0 ms). The picture differs from the old pass by 0.11 of 255 levels on average. | Profiling showed this pass was 40 to 50% of the frame, most of it the blur. | `room_life.gd` |
| Imported textures use lossless WebP at its strongest setting. Pixels are identical (all 1,025 textures compared). | Web package 66.2 to 54.3 MB; every platform's pack is 11.9 MB smaller. Cold load to the title on a simulated 50 Mbit/s line: 19.2 to 16.9 s (one run each). | A free size cut with no visual change. Import takes about 7 minutes instead of 4 to 5. | `project.godot` |
| A profiling harness that records frame-time distribution, load time and the renderer in use, with a switch for each visual system and an on/off alternation mode for small differences; web size and load scripts. | Run-to-run noise on this machine is about 5 ms, which the alternation mode gets under. | So the next optimisation starts from measurements. | `game/tests/perf.gd`, `tools/perf/`, `tools/webtest/load_test.js` |

Found but not changed (listed in the report): overdraw from the sky and far background layers (8 to 9 ms here)
and the HUD (5 to 8 ms). The new bloom pass has only been seen on two software renderers; Settings > Colour
grade & bloom: Off turns the whole pass off if a real GPU driver disagrees.

## 6. For playtesting
- **Settings > Playtest log** (off by default) keeps first-time timestamps, tips done or skipped, stage times,
  knockouts per room and purchases inside the save. It is read under Pause > Help & tips > Playtest notes and
  nothing leaves the device.
- `PLAYTEST_KIT.md`: a five-person first-time test with a facilitator script and observation sheet.
- `tools/capture_polish.sh`: the fixed before/after capture set. `tools/anim_audit.py`: timing audit.
- The campaign bot can model a shopper: `AUTOPLAY_SHOP=some|all`.
