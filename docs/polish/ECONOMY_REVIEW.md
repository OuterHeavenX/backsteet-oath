# Economy review (healing, food, manuals, workbench, defeat penalty)

Analysis and recommendations only. No number was retuned: tuning needs player evidence, and nothing found is
plainly broken (every purchase can be afforded; the no-op purchases found are listed in section 5).

Sources: `game/data/items.json`, `skills.json`, `weapons.json`, `shops.json`, `quests.json`, `enemies.json`,
`GameState.defeat_penalty`, and bot campaigns on this branch (normal difficulty, single runs, so noisy; a bot
is not a player and nobody has playtested these numbers).

## 1. Measured income

Non-shopping bot at f74a713 (47.8 in-game minutes, 256 enemies, 13 knockouts, level 14). "Cash on arrival" is
what the bot held when the stage began. "Gross" adds back the defeat penalties it had paid by then (estimated
from the cash it was carrying: about $30 for the first knockout, $40 for each later one).

| Stage begins | Cash on arrival | Knockouts so far | Gross income so far (est.) |
|---|---|---|---|
| find_mara | $4 | 0 | $4 |
| chain_dogs | $33 | 0 | $33 |
| market | $91 | 0 | $91 |
| pikes | $123 | 0 | $123 |
| ironworks (Act II) | $192 | 1 | $222 |
| foundry | $271 | 1 | $301 |
| neon | $279 | 2 | $349 |
| rooftops | $291 | 4 | $441 |
| return_home | $309 | 5 | $499 |
| underline (Act III) | $354 | 5 | $544 |
| floodgate | $625 | 8 | $935 |
| dockgate | $741 | 8 | $1,051 |
| warehouse | $846 | 10 | $1,236 |
| rook | $986 | 12 | $1,456 |
| epilogue | $946 | 13 | $1,456 |

Other runs agree: the 1.3.0-rc1 baseline bot ended with $851 after 298 enemies and 18 knockouts; later runs on
this branch end with $850 to $940 unspent and 15 to 18 knockouts. A bot that spends half its cash on food at
each story stage spent $254 in total, reached every permanent food cap, had 4 knockouts and still ended with
about $1,000.

Income is back-loaded: about 15% of main-path cash arrives in Act I, 22% in Act II and 63% in Act III
(tier 5 and 6 enemies pay 3.2x and 3.8x; Kowal alone pays $120).

Optional income, all of it without farming: side jobs pay $585 in total ($195 available in Act I, a further
$190 in Act II, $200 in Act III), and Benny's ladder pays $10 times the bout number for each bout cleared, plus $150 for the title.

## 2. What things cost

| Purchase | Cost | Notes |
|---|---|---|
| Healing | $0.13 to $0.20 per HP | Ramen $8 for 60, Ironworker Stew $14 for 100, Tonic $25 for a full bar |
| Every food cap (+30 HP, +8 ATK, DEF, AGI, TEC) | $242 at the cheapest dishes | $322 if bought only at the Lucky Spoon, which sells all five stats |
| All ten manuals | $705 | $615 in practice: Shoulder Charge is Benny's free lesson, Heel Drop is a side-job reward |
| All workbench tiers | $1,045 | $1,005 if "Tools of the Trade" supplies Grip Tape tier 1 |
| Stat refund | $25 | |
| Knockout | 20% of cash on hand, at most $40 | $40 from $200 upward |

## 3. Purchase paths against income

Cumulative spend at the end of each act, against cumulative gross main-path income from section 1.

| | End of Act I | End of Act II | End of game |
|---|---|---|---|
| Main-path income (gross) | $220 | $545 | $1,455 |
| ...plus every side job | $415 | $930 | $2,040 |
| Minimal shopper (healing only, estimated) | about $40 | about $110 | about $250 |
| Some upgrades (all food caps, four manuals, one workbench line) | $210 | $552 | $782 |
| Completionist, buying each item as it reaches the shelf | $552 | $1,252 | $1,952 |

- **Minimal shopper**: never short. Ends with $850 to $1,000 and nothing left worth buying.
- **Some upgrades**: fits, but Act II is tight. On main-path income alone it is about even ($552 against $545)
  before knockouts, and the bot had already paid about $190 in penalties by then. One or two side jobs close
  the gap. From Act III on there is a surplus of roughly $650.
- **Completionist**: cannot keep up with the shelves in Acts I and II ($552 against $220, then $1,252 against
  $545), and is still short with every side job done ($415 and $930). Buying everything the moment it appears
  would need farming of roughly $50 to $250 in the first two acts. By the end, main path plus side jobs
  ($2,040) covers everything ($1,952) with no farming; main path alone falls about $500 short, which is the
  ladder or about two workbench lines.

Farming is therefore needed nowhere for a sensible path, and only for a player who insists on owning
everything as soon as it is sold.

## 4. Findings

1. **Food is the strongest purchase by an order of magnitude.** $242 buys the equivalent of 37 stat points
   (the whole level curve grants 19), and in the bot runs it cut knockouts from 13 to 18 down to 4. A $3 Green
   Tea is +1 TEC for good; the cheapest manual is $45. Bonus dishes also heal, so plain healing food is only
   worth buying to carry.
2. **Caps arrive early.** $242 is about the gross income up to the start of Act II, and the first shop sells
   all five stats. A player who learns this is capped by mid Act II; after that food is healing only. The shop
   now marks capped dishes and refuses a meal that would do nothing.
3. **Act II is the trough.** It brings the least income per stage, the most new stock (five manuals and four
   tier 2 upgrades, $700), and the most bot knockouts. The $40 penalty is a manual's worth of progress there.
4. **The knockout penalty falls on the wrong players.** It is a fixed $40 from $200 upward, so it takes the
   largest share from someone saving for a manual in Act II and is noise ($40 of $1,000) in Act III. It also
   charges cash on hand, so spending before a hard fight avoids it; the game never says so.
5. **Act III has no sink.** Tier 3 upgrades and Oath Breaker total $700 against about $900 of new income, so
   every measured run ends with $850 to $1,000 unspent.
6. Manuals ($45 to $150) and workbench tiers ($35 to $150) are priced sensibly against each act's income.
   Nothing is unaffordable.

## 5. No-op and overlapping purchases found while building the previews

- Eating at full HP with nothing left to gain charged money for nothing. Fixed in the shop (refused, no charge).
- **Throwable Object mastery can never rise**: mastery is only added on swing hits, and that family cannot be
  swung. The Status menu now says so instead of promising levels. Fix belongs in `player.gd` / `projectile.gd`
  (count thrown hits) or in the mastery list (hide the family).
- **Shoulder Charge** sits on Benny's shelf at $40 although his first lesson gives it free.
- **Heel Drop** ($50) is also the reward of "The Long Way Round"; **Grip Tape tier 1** ($40) is also the reward
  of "Tools of the Trade". A player who bought first gets nothing from the reward (`quests.gd` grants only if
  missing).
- One mastery level or one stat point can round to no visible change on a weak hit (for example a Wrench swing
  11 to 11). The previews show this honestly; it is rounding, not a bug.

## 6. Proposed changes, for a human decision

None of these is made. Each needs playtest evidence (cash held at each knockout, when caps are reached, cash
left at the credits) before any number moves.

1. **Defeat penalty**: lower the cap in the mid game (for example 15% capped at $25), or keep it and add one
   line to the defeat screen: "You lose cash you are carrying. Spend it before a hard fight." The text change
   is free of balance risk and can ship first.
2. **Flatten the income curve**: move some Act III cash earlier (for example the tier 3 and 4 cash multipliers
   up from 2.0 and 2.6, tiers 5 and 6 down from 3.2 and 3.8) so that Act II is not the trough and the game
   does not end with $900 in the pocket. Total income should stay about the same.
3. **Food caps**: leave prices alone. If players prove to be capped before Act II, spread the stat dishes
   across districts (the Lucky Spoon would keep HP and one stat) before touching prices or caps.
4. **Overlapping rewards**: when a side job grants a manual or tier the player already owns, pay its shop
   price instead, and take Shoulder Charge off Benny's price list once his lesson exists for that save.
5. **Throwable mastery**: count thrown hits, or drop the family from the mastery list.
6. **Late sink**: only if evidence shows players care about the leftover cash. No new system is proposed.
