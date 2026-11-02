# Changelog

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
