# Follow-ups: hypotheses that need player evidence

Ordered by how much the answer would change the game. Each item names what to watch for, and where to change it.
None of these was tested with people. The bot numbers quoted are from single runs and vary run to run (two
no-shopping runs of this branch differed by about 4 minutes and 2 knockouts), so treat them as rough.

## 1. Does the opening teach without help?
- **Hypothesis:** a first-time player lands a combo, blocks, throws and eats before Duke without being told.
- **Evidence needed:** playtest kit sections A and B; the playtest log's "tips done by doing" versus "skipped".
- **If not:** tip wording and order are in `game/scripts/core/tutor.gd` (`TIPS`, `ORDER`); how long the Dogs
  wait and how many attack at once are in `Story._intro`.
- **Watch especially:** whether people read the tip panel at all, and whether "line up level" makes sense.

## 2. Is the fight camera the right distance?
- **Hypothesis:** 1.16x in fights makes fighters easier to follow without hiding approaching enemies.
- **Evidence needed:** kit section C ("what got you there?"), any hit from an enemy the player did not see coming,
  and whether anyone notices or dislikes the zoom changing.
- **Change:** `game/data/tuning.json` > `camera` (`combat_zoom`, `hold_seconds`, `threat_bias`). Players can also
  pick Settings > Combat camera: Wide.
- **Open question:** whether exploring should also be slightly closer (currently 1.0) so the change is smaller.

## 3. Do people shop, and is the economy too generous?
- **Measured:** a bot that never shops finishes with about $850 to $940 unspent and is knocked out 15 to 18 times,
  mostly from the Neon Mile on. A bot that spends half its cash on food at each story stage spends $254 in total,
  reaches **every** permanent food cap, and is knocked out 4 times.
- **Hypothesis A:** the late-game spike only bites players who do not eat, so the fix is discovery (Dot's free
  plate, the food tip), not weaker enemies. No enemy numbers were changed.
- **Hypothesis B:** permanent food bonuses are too cheap to be a real choice: $254 buys all of them while income
  is over $1,100.
- **Evidence needed:** kit section G (what people bought and why), question 8.
- **Change:** prices and caps in `game/data/items.json` (`food_caps`); see `ECONOMY_REVIEW.md` for options.
  Do not retune without that evidence.

## 4. Are the three attack cues audible and distinct?
- **State:** the sounds were generated and are numerically different (a low double thump under 300 Hz, a mid
  whoosh, a bright rising ring), but **nobody has listened to them**, or to any of the game's audio, in this
  environment.
- **Evidence needed:** a person with speakers: do the cues cut through music, are they annoying, is the mix
  balanced across fights, shops, hubs, bosses and room changes? Kit question 7.
- **Change:** `tools/audio/gen_audio.py` (`sfx_tell_*`) and the volumes in `Enemy._launch_attack`.

## 5. Do the readability aids help or clutter?
- **Hypothesis:** the keyline, lane rings and object highlights reduce "why didn't that hit?" moments.
- **Evidence needed:** kit sections A (wrong-lane attempts) and E; whether anyone turns Combat guides off.
- **Change:** alphas and ranges in `tuning.json` > `readability`.

## 6. Do players notice the town changing, and connect it to what they did?
- **Hypothesis:** the neighbours after Duke and the "what changed" card make cause and effect clear.
- **Evidence needed:** kit section F and question 5, asked without prompting.
- **Change:** `Story._duke_aftermath`, the `districts` block in `story.json`.
- **Open question:** thinner patrols after a boss shorten backtracking (the bot fought about 40 fewer enemies with
  the same final level). Does a human miss the fights, or the XP?

## 7. Kowal's lights: decision or chore?
- **Hypothesis:** choosing between relighting and pressing the attack is interesting, and saving a light by
  hitting her feels good.
- **Evidence needed:** a late-game playtest round; the playtest log counts lights switched on.
- **Change:** timings in `Boss` (`snuff_cd`, the 480-tick dark timer, the wave cap) and light positions in
  `Story.start_boss`.

## 8. Storage Floor: is the shutter run fair?
- **Hypothesis:** 24 seconds (32 on Relaxed) is reachable by a player who runs and dodges, and failing feels like
  a consequence rather than a punishment.
- **Measured:** the bot never makes it (it fights everything), so it cannot judge this.
- **Change:** `Story.SHUTTER_SECONDS` and the bonus constants; the crane in `encounters.json` (`rw_storage`).

## 9. Hit-stop, impact effects and input feel
- **State:** reviewed against the attack data and left unchanged. Buffering (8 ticks) and hit-stop values were
  not felt by anyone here.
- **Evidence needed:** players describing hits as mushy, sticky or delayed; dropped inputs.
- **Change:** `hitstop` per attack in `attacks.json`; `Player.BUFFER_TICKS`.

## 10. New Game+ pace
- **State:** composition and boss variations are tested for correctness only. Nobody, human or bot, has played it.
- **Change:** `tuning.json` > `ngplus`.

## 11. Performance on real hardware
See `PERF_REPORT.md`. Every number in this pass comes from a software renderer in a container. Nothing here says
how the game runs on a GPU, a Steam Deck or a phone. The steps for a person to measure are in that report and in
`VALIDATION_REPORT.md`.

## Smaller items
- Possible older issue, **not confirmed by running it**: from reading the code, the postgame welcome line in the
  diner may be replaced by the ending's own diner dialogue, so players might never see it.
- Regenerating the Market Gate art re-applies the mural layers automatically (`gen_env2.py` calls `mural.py`).
- The heavy's grab still has no wind-up animation frames (a held pose plus the lean and the purple tell).
- Sparring partners use Chain Dog sprites and are written as ex-Dogs who train with Benny; a dedicated look would
  need art.
- A full-campaign human duration is still unknown. The bot's 47 to 52 in-game minutes is not a human time, and
  this pass removed some repeated fights on purpose rather than add length.
