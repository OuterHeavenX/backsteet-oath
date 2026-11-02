# itch.io page draft: BACKSTREET OATH

## Page settings
| Field | Value |
|---|---|
| Title | Backstreet Oath |
| Project URL | `https://<your-account>.itch.io/backstreet-oath` |
| Short description / tagline | A neighborhood brawler RPG. Punch, eat, learn, level up, and take back Bellwether, 1988. |
| Classification | Game |
| Kind of project | **HTML** (playable in browser) + downloadable Linux/Windows builds |
| Release status | Released (or "In development" while it is a release candidate) |
| Pricing | Free / pay-what-you-want (your choice) |
| Genre | Action |
| Tags | beat-em-up, brawler, action-rpg, pixel-art, retro, belt-scroller, story-rich, singleplayer, controller-support, steam-deck |
| Input | Keyboard, Gamepad (any), Touchscreen |
| Accessibility | Configurable controls, adjustable difficulty, subtitles (all dialogue is text), high-contrast UI, large text option, reduced screen shake/flashes |
| Average session | About an hour |
| Languages | English |
| Cover image | `release/itch/cover_630x500.png` (630×500) |
| Screenshots | `release/itch/screenshot_1.png` … `screenshot_7.png` (1280×720, real gameplay, 2× nearest upscale) |
| Content note | Cartoon fistfights and improvised-weapon violence (no blood, no guns). Mild peril, arson mentioned in the story. |

### Embed options (HTML upload)
- Upload `backstreet-oath-v1.0.0-rc1-web.zip` and tick **"This file will be played in the browser"**.
- Viewport: **1280 × 720**. Tick **Mobile friendly** (orientation: **Landscape**), **Fullscreen button**.
  Leave **"Automatically start on page load"** off; the game waits for a click or key press to start audio anyway.
- **SharedArrayBuffer support: leave OFF.** The build is single-threaded and needs no special headers.
- Downloadable files: `...-linux-x86_64.zip` (platform: Linux), `...-windows-x86_64.zip` (platform: Windows).

## Short description
Nico Vale comes home to Bellwether after two years away and finds his best friend missing, his neighborhood
under siege, and the man who taught him to fight standing on the wrong side. Brawl through six districts,
spend your street cash on diner food and fighting manuals, grow stronger, and keep the oath: **nobody fights alone.**

## Long description
**Backstreet Oath** is an original belt-scrolling action RPG in the classic tradition: streets with real depth,
punch-kick-jump combat, enemies that drop cash, weapons lying in the gutter, food shops that make you stronger,
and gang bosses with something to say.

**Fight like it's 1988**
- Combos, finishers, running attacks, jump kicks, a guard with a forgiving *perfect guard* reward.
- Grab dizzy thugs and throw them into their friends. Lift crates and trash cans. Roll a tire down the street.
- 16 weapons in 6 families: wrenches and batons, bats and pipes, chains and belts, bottles and bricks, road signs...
- Ten fighting manuals to buy and master, from the Rising Kick to the secret Oath Breaker.

**Grow like an RPG**
- Levels 1–20 with clear stat gains and a stat point each level (or let it auto-balance).
- 29 foods and medicines. Diner pancakes, Fong's ramen, Gus's clam chowder. Some give small permanent boosts.
- Weapon mastery and Mara's workbench upgrades.

**A neighborhood worth saving**
- Six districts: Old Quarter, Canal Market, Ironworks Yard, Neon Mile, Floodgate Road and Rook's Warehouse.
- Six boss fights with readable patterns, including a two-phase finale.
- A complete story with funny, heartfelt dialogue, a real ending, credits and postgame free roam.
- Six side jobs: find a runaway terrier, escort a nervous bookseller, settle an arcade feud, win the Alley Cat Cup...

**Play your way**
- Keyboard, any controller (Steam Deck native Linux build) or touch controls in mobile browsers (landscape).
- Rebindable controls, Normal/Relaxed difficulty, large text, text speed, shake and flash settings.
- Three save slots with automatic backups, plus save export/import.

*Backstreet Oath is an original game made with Godot 4.7. All art, music, sound and writing were created for this
project. It is a love letter to a genre, not affiliated with any existing franchise.*

## Controls (summary)
Move WASD / arrows · Punch J · Kick K · Jump Space · Guard L · Grab/Talk E · Run Shift (or double-tap) · Status Tab · Pause Esc.
Controller: A jump · X punch · Y kick · B grab · LB guard · RB run. Full list in the game's Controls screen.

## Install notes
- **Browser:** click Run. Saves stay in your browser; export a backup from *Manage Saves* if you clear site data.
- **Linux / Steam Deck:** unzip, run `start.sh`. Steam Deck: add `start.sh` as a non-Steam game (no Proton needed).
- **Windows:** unzip, run `BackstreetOath.exe` (SmartScreen may warn about an unsigned build).

---

## Upload instructions (blocked in the build environment)
This build was produced in an environment whose network policy **blocks itch.io and the butler download host**
(`itch.io`, `broth.itch.zone` returned HTTP 403 from the egress proxy). So nothing has been uploaded. To publish:

1. Create the project page (draft/restricted first) with the settings above and upload the cover and screenshots.
2. Install butler (https://itch.io/docs/butler/) and log in once: `butler login`.
3. Push the three channels from the `release/` folder:
   ```bash
   butler push backstreet-oath-v1.0.0-rc1-web.zip            <your-account>/backstreet-oath:html5 --userversion 1.0.0-rc1
   butler push backstreet-oath-v1.0.0-rc1-linux-x86_64.zip   <your-account>/backstreet-oath:linux --userversion 1.0.0-rc1
   butler push backstreet-oath-v1.0.0-rc1-windows-x86_64.zip <your-account>/backstreet-oath:windows --userversion 1.0.0-rc1
   butler status <your-account>/backstreet-oath
   ```
4. On the page's Edit screen: mark the `html5` upload "played in the browser", set the viewport to 1280×720, and
   tick Fullscreen button and Mobile friendly (Landscape). Make sure the Linux and Windows uploads carry the right
   platform tags.
5. Open the page while it is still restricted and check:
   - The browser build boots, starts on a click, plays audio, and saves across a reload.
   - The fullscreen button works.
   - The Linux zip downloads and launches.

   Then switch the page to Public.
