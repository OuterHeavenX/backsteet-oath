# Steam Deck guide

Backstreet Oath ships a **native Linux x86_64** build. It does not need Proton.

## Install (Desktop Mode)
1. Copy `backstreet-oath-v1.2.0-rc1-linux-x86_64.zip` to the Deck and extract it (e.g. to `~/Games/BackstreetOath`).
2. Make sure the launcher is executable: right-click `start.sh` → Properties → Permissions → *Is executable*
   (or in Konsole: `chmod +x start.sh BackstreetOath.x86_64`).
3. Steam → *Games* → *Add a Non-Steam Game to My Library* → *Browse* → pick `start.sh` (or `BackstreetOath.x86_64`).
4. Optional: in the shortcut's Properties, rename it to "Backstreet Oath". Leave *Compatibility* **off** (it's native).
5. Return to Gaming Mode and launch it from your library.

## Controls
The Deck's built-in controller uses the standard layout: **A** jump, **X** punch, **Y** kick, **B** grab/talk,
**L1/L2** guard, **R1/R2** run, **View** status, **Menu** pause. Everything (menus, shops, dialogue, saves) works
without the touchscreen or a keyboard. Rebind in *Controls*; adjust stick deadzone in *Settings*.

## Display
The game's 640×360 layout fills the Deck's 1280×800 screen at exactly 2×. The 2× art is drawn 1:1 and the view
extends slightly taller (no bars). Settings → *Large text* enlarges all text, and *Effects: Reduced* lowers the
GPU load. Performance on Deck hardware has **not** been measured (no device was available).

## Saves
`~/.local/share/godot/app_userdata/Backstreet Oath/` (3 slots + automatic backups). Not synced by Steam Cloud
(non-Steam shortcut). Use *Manage Saves → Export* to copy a save elsewhere.

## Notes / honesty
- The game is **not** Valve-certified or Deck-verified. It has not been run on physical Steam Deck hardware by the
  developer. What was verified: the Linux build launches from its own folder (including paths with spaces) under X11
  with Mesa OpenGL at 1280×800, renders the title and menus correctly, and saves to the user data folder.
  Controller input uses Godot's standard SDL gamepad mapping, which supports the Deck. On-device testing is still pending.
- If the game starts on an external monitor in a window, press **F11** (or Settings → Fullscreen).
