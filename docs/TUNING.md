# Tuning Sheet

All values come from `game/data/*.json`. Ticks are 1/60 s.

## Player growth
- XP to next level: `round(40·L^1.5 + 20)` → L1→2 60, L5→6 467, L10→11 1285, L13→14 1895.
- Per level: +7 HP, +1 ATK, +1 DEF, +0.5 AGI, +0.5 TEC, +1 stat point (+6 HP when spent on HP). Balanced
  auto-spend cycles ATK→DEF→TEC→AGI→HP (on by default).
- Base L1: HP 60, ATK 5, DEF 4, AGI 5, TEC 5. Food caps: HP +30, other stats +8 each.
- Damage: physical `power × (1 + ATK·0.06)`; techniques `power × (1 + ATK·0.03 + TEC·0.05)`; weapons
  `(weapon + upgrade + move) × (1 + ATK·0.04 + TEC·0.03) × (1 + 0.06·mastery)`. Defense: `× 60 / (60 + DEF·2.5)`,
  minimum 1. Relaxed difficulty: incoming × 0.6, one attacker at a time, perfect-guard window +4 ticks.
- AGI: walk speed +1.5%/pt (cap +30%), −1 recovery tick per 6 AGI (cap −4), get-up protection +1 tick/pt.
- TEC: perfect-guard window 8 + TEC/4 ticks (cap +6), dizzy build-up +3%/pt.

## Expected progression (measured by the autoplay bot, Normal)
| District (tier) | Level entering → leaving | Bot deaths | Notes |
|---|---|---|---|
| Old Quarter (1) | 1 → 3 | 1 | Duke 210 HP |
| Canal Market (2) | 3 → 6 | 1 | Pikes 190 + 160 HP, Jett duel retreats at 50% |
| Ironworks (3) | 6 → 7 | 1 | Otto 520 HP, armored wind-ups |
| Neon Mile (4) | 7 → 9 | 2 | Jett 470 HP, dodges |
| Setback + Floodgate (5) | 9 → 12 | 4 | Holt 600 HP + 2 summons |
| Warehouse (6) | 12 → 14 | 4 | Rook 900 HP, phase 2 at 50% |

## Enemy scaling (multipliers by tier 1–6)
| | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| HP | 1.0 | 1.35 | 1.75 | 2.15 | 2.6 | 3.0 |
| Power | 1.0 | 1.25 | 1.5 | 1.75 | 2.0 | 2.25 |
| DEF | 2 | 4 | 6 | 8 | 10 | 12 |
| XP | 1.0 | 1.6 | 2.3 | 3.0 | 3.8 | 4.6 |
| Cash | 1.0 | 1.5 | 2.0 | 2.6 | 3.2 | 3.8 |

Archetype base HP / XP: brawler 40/9, flanker 32/9, blocker 52/12, heavy 95/18, weapon 46/12, thrower 30/10.
At most 2 enemies hold attack tokens at once (1 on Relaxed or during boss fights). Room population cap: 6 (5 on Relaxed).

## Economy
- Earnings: the bot banked **$1,101** over the main story without spending. Side jobs add about $260 more, plus
  Cup rematches at $25 each.
- Food: $2–$15 (heal 12–110). Medicine: bandage $10, tonic $25 (full), vitamin pack $30 (+3 max HP),
  smelling salts $15 (auto-revive).
- Manuals: $40–$150, total **$655** for all ten (one is also an escort reward).
- Workbench: four lines × three tiers, about $1,045 for everything. Tiers 2 and 3 unlock in Acts II and III.
- Respec $25 (after Act I). Bus fare $2. Defeat penalty: 20% of carried cash, max $40.
- Result: essentials and most manuals are affordable from normal play. No farming is required.

## Healing per district (shop that is closest to the action)
Old Quarter: Lucky Spoon. Canal Market: Fong's. Ironworks: Yard Canteen. Neon Mile: Starlight snack bar + Rosa's
Pharmacy. Floodgate/Warehouse: Bait & Tackle (Gus). Each is also a safe hub with saving.
