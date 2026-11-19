# Performance, load size and export report (1.3 polish)

Every frame-time number in this report was measured with **software rendering**. Nothing here is a GPU, Steam
Deck, phone or console measurement, and nothing here certifies performance on real hardware. The numbers are
only good for comparing one build with another on the same machine. What a person has to run on real hardware
is in [Not verified](#not-verified-and-how-to-verify-it).

## Summary

| | 1.3.0-rc1 | this branch | how measured |
|---|---|---|---|
| Kettle Street, quiet (avg frame) | 46.8 ms | 39.7 ms | llvmpipe, 1280×720, best of 2 runs each |
| Kettle Street, 8 enemies | 53.4 ms | 41.0 ms | same |
| Pump Station Road, rain | 45.3 ms | 35.5 ms | same |
| Kowal, lights-out phase | 44.5 ms | 29.4 ms | same |
| Web `index.pck` | 66.2 MB | 54.3 MB | file size |
| Web release zip | 74.5 MB | 62.7 MB | deflate -9, as `tools/package.py` builds it |
| Web transfer, uncompressed host | 101.1 MiB | 89.8 MiB | headless Chromium, CDP byte counts |
| Web cold load to title at 50 Mbit/s | 19.2 s | 16.9 s | headless Chromium, one run each |

Two changes produced these:

1. **Bloom without the engine's blur chain** (`game/scripts/core/room_life.gd`). The colour grade + bloom pass
   was 40–50% of the software-rendered frame, and 70–80% of that was the bloom's blurred screen copy. The new
   pass costs 7–15 ms less per frame here and matches the old picture to within 0.12 of 255 levels on average.
2. **Lossless WebP at method 6** (`game/project.godot`). Same pixels (all 1025 imported textures verified),
   11.9 MB less in every platform's pack.

## Environment

| | |
|---|---|
| Renderer | Mesa **llvmpipe** (LLVM 20.1.2, 256 bits), OpenGL 4.5 core, Godot Compatibility renderer (`gl_compatibility`) |
| Display | Xvfb, 1280×720×24, window 1280×720 (stretch `canvas_items`/`expand`, 640×360 logical units) |
| Machine | Firecracker VM, 4 vCPU Intel Xeon (2.10 GHz for the baseline/profile runs, 2.30 GHz for the before/after and web runs: the VM changed host between sessions), 15 GB RAM, Ubuntu 24.04.5 |
| Engine | Godot 4.7.2-stable (official), editor binary running the project (debug build) |
| Game | 1.3.0-rc1 tree (`config/version` untouched) |
| Web | Playwright Chromium 153 headless, WebGL through SwiftShader (software), 1280×720 viewport |

The harness writes all of this into every result file (`meta` in the JSON, first line of the tables), with
`software_renderer: true` when the adapter is llvmpipe/SwiftShader.

### Run-to-run noise on this machine

The machine is shared and has slow phases that last tens of seconds. The same configuration measured minutes
apart:

- Kettle quiet, 1.3.0-rc1, three runs: **49.0 / 52.7 / 62.7 ms**.
- Diner interior, six back-to-back runs: 39.9, 40.7, 50.2, 53.4, 52.4, 41.3 ms.
- One run of the rc1 pass during the before/after measurement came out at 95 ms instead of 47 ms.

So a difference of less than about 5 ms between two separate runs means nothing here. The report therefore uses
two methods and labels each number with the one that produced it:

- **Between runs, best of N** (`tools/perf/perf_matrix.py`): each configuration is its own process, repeats are
  interleaved, the best (least disturbed) run is reported and every run's average is listed next to it.
- **Paired, inside one run** (`PERF_PAIRED` in the harness): one system is switched off and on in alternating
  0.6 s windows (on-off, off-on, …) and the mean difference of the pairs is reported with its standard error.
  Slow drift cancels, so this resolves about 1 ms.

## Commands

All from the repository root unless noted. `godot` is 4.7.2; a fresh checkout needs `cd game && godot
--headless --import` once (about 7–8 minutes on 4 cores with the WebP setting of this branch).

```sh
# one harness run, table + JSON (scenarios, switches and environment variables are documented in the file header)
cd game && PERF_SECONDS=8 PERF_OUT=/tmp/perf.json xvfb-run -a -s "-screen 0 1280x720x24" \
    godot --resolution 1280x720 res://tests/perf.tscn

# baseline + player-facing presets + one-system-off profile, 3 interleaved runs (docs/polish/perf/profile_rc1/)
python3 tools/perf/perf_matrix.py --out /tmp/perf/profile --profile --repeats 3 --seconds 5 \
    --scenarios kettle_quiet,kettle_combat8,pumpstation_rain,marquee_neon,vault_kowal_dark

# bloom before/after between runs (docs/polish/perf/bloom_ab/): no_fast_bloom = the 1.3.0-rc1 pass
python3 tools/perf/perf_matrix.py --out docs/polish/perf/bloom_ab --configs no_fast_bloom,base --all-tables \
    --repeats 2 --seconds 6 --scenarios kettle_quiet,kettle_combat8,pumpstation_rain,vault_kowal_dark

# paired in-run profile (docs/polish/perf/paired_*.json), then the table
cd game && PERF_PAIRED=all PERF_PAIRS=5 PERF_SECONDS=2 PERF_OUT=/tmp/paired.json \
    PERF_ONLY=kettle_quiet,kettle_combat8,pumpstation_rain,vault_kowal_dark \
    xvfb-run -a -s "-screen 0 1280x720x24" godot --resolution 1280x720 res://tests/perf.tscn
python3 tools/perf/paired_table.py /tmp/paired.json

# frozen-frame picture comparison of the grade/bloom pass (docs/polish/perf/grade_ab.txt)
cd game && AB_OUT=/tmp/ab xvfb-run -a -s "-screen 0 1280x720x24" godot --resolution 1280x720 res://tests/grade_ab.tscn
python3 tools/perf/grade_diff.py /tmp/ab

# export audit, pack contents, sizes, pixel check of two import caches
python3 tools/perf/audit_assets.py
python3 tools/perf/pck_list.py build/web/index.pck
python3 tools/perf/web_sizes.py build/web
python3 tools/perf/verify_ctex_pixels.py <old game/.godot/imported> game/.godot/imported

# web export and load test
cd game && godot --headless --export-release Web ../build/web/index.html
python3 tools/webtest/serve.py build/web 8765 &        # add --gzip to serve gzip-encoded bodies
node tools/webtest/load_test.js http://127.0.0.1:8765/index.html unthrottled out.json
node tools/webtest/load_test.js http://127.0.0.1:8765/index.html cable-50mbit out.json
node tools/webtest/game_test.js "http://127.0.0.1:8765/index.html?bo_debug=1" /tmp/websmoke
node tools/webtest/audio_test.js http://127.0.0.1:8765/index.html
```

## The harness (`game/tests/perf.gd`)

Scenarios (scripted input is driven from the physics tick, RNG seeded per scenario, nobody is allowed to die so
the load stays constant; the room's own waves, story events and boss triggers are disabled so only the
scenario's actors exist):

| name | what |
|---|---|
| `kettle_quiet` | `oq_kettle`, no enemies, the player walks back and forth so the camera scrolls |
| `kettle_combat8` | `oq_kettle`, 8 Dogs, the player attacks continuously (jab, jab, jab, kick) |
| `pumpstation_rain` | `fr_pumpstation` (night, rain, wet-ground reflections), 3 Grays, fighting |
| `marquee_neon` | `nm_marquee` (neon night, 9 animated signs), walking |
| `vault_kowal_dark` | `ul_vault`, Kowal forced to half health: darkness 0.45, lantern follow light and two summoned Moles are active before sampling starts (the result records `darkness` and `follow_lights`) |
| `interior_diner`, `boss_rook` | the two older scenarios, kept |

Per scenario it records: renderer and environment, effects preset and `post_fx`, switched-off systems, sample
duration, frames, average, p50/p90/p95/p99/max, count and share of frames over 16.7 / 20 / 33.4 ms, spikes (frames
longer than twice the scenario's own median), **load time** (room build + first drawn frame, kept apart from the
frame statistics), **reload time** (the same room loaded again inside the running world, i.e. a door transition
without its fade), script time split (simulation `_physics_process` per rendered frame, `_process`, and
everything else = engine + rendering + present), draw calls, node counts, texture memory, and CPU accounting
from `/proc` (own CPU, other processes, steal) so a disturbed sample can be recognised.

Note for comparisons with older reports: the previous harness pressed an action called `right`, which does not
exist, so its "explore" scenario measured a standing player. The scenario now really walks.

## Baseline: 1.3.0-rc1

Between runs, best of 3, 5 s samples, llvmpipe 1280×720. Times in ms. `sim`/`proc`/`other` are per rendered
frame. Full file: `docs/polish/perf/profile_rc1/summary.md`.

| scenario | frames | avg | p50 | p90 | p95 | p99 | max | >16.7 | >20 | >33.4 | spikes | sim | proc | other | draw calls | nodes room/total | load | reload | every run's avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kettle_quiet | 103 | 49.0 | 47.5 | 54.6 | 58.4 | 67.6 | 70.7 | 100% | 100% | 100% | 0 | 0.72 | 0.54 | 47.8 | 69 | 173/262 | 471 | 58 | 49.0 / 52.7 / 62.7 |
| kettle_combat8 | 94 | 53.4 | 51.9 | 60.5 | 62.5 | 81.2 | 81.2 | 100% | 100% | 100% | 0 | 2.14 | 0.53 | 50.7 | 88 | 236/325 | 129 | 48 | 53.4 / 54.9 / 68.8 |
| pumpstation_rain | 111 | 45.4 | 45.2 | 50.2 | 52.2 | 56.9 | 61.3 | 100% | 100% | 100% | 0 | 0.91 | 0.41 | 44.0 | 67 | 141/230 | 105 | 50 | 45.4 / 47.6 / 58.0 |
| marquee_neon | 98 | 51.2 | 50.1 | 57.1 | 59.1 | 70.0 | 70.0 | 100% | 100% | 100% | 0 | 0.74 | 0.43 | 50.0 | 61 | 146/235 | 148 | 58 | 51.2 / 51.2 / 64.8 |
| vault_kowal_dark | 130 | 38.5 | 38.2 | 42.8 | 43.7 | 47.9 | 51.1 | 100% | 100% | 99% | 0 | 0.80 | 0.28 | 37.4 | 74 | 95/184 | 105 | 38 | 38.5 / 40.3 / 50.2 |

What the table says:

- **Script time is small**: simulation 0.7–2.1 ms and per-frame script about 0.5 ms out of 38–53 ms. On this
  renderer the frame is almost entirely rendering (fill rate), not GDScript. (At 20 FPS about 2.5 physics ticks
  run per rendered frame, so the per-frame simulation share is, if anything, overstated.)
- Load: the first room of a process takes about 0.47 s (shader compilation and first texture uploads); later
  rooms 0.1–0.15 s; a reload 40–60 ms. No frame in these samples was a spike.
- The first, 4 s run of all seven scenarios also gave `interior_diner` 41.5 ms and `boss_rook` 40.4 ms.

Player-facing presets on 1.3.0-rc1, same method (avg ms; every run's avg in brackets):

| scenario | Full + grade | Colour grade & bloom: Off | Effects: Reduced | Reduced + grade off |
|---|---|---|---|---|
| kettle_quiet | 49.0 | 29.2 (29.2 / 34.3 / 36.4) | 25.8 (25.8 / 31.2 / 32.1) | 28.6 (28.6 / 32.1 / 32.5) |
| kettle_combat8 | 53.4 | 32.5 (32.5 / 39.6 / 41.0) | 28.1 (28.1 / 35.5 / 37.0) | 34.9 (34.9 / 36.6 / 38.0) |
| pumpstation_rain | 45.4 | 25.9 (25.9 / 32.4 / 33.9) | 25.1 (25.1 / 30.2 / 30.6) | 25.8 (25.8 / 30.1 / 30.5) |
| marquee_neon | 51.2 | 34.1 (34.1 / 39.2 / 41.3) | 30.8 (30.8 / 35.2 / 35.4) | 29.7 (29.7 / 33.7 / 36.9) |
| vault_kowal_dark | 38.5 | 21.0 (21.0 / 24.4 / 25.1) | 20.8 (20.8 / 23.6 / 24.0) | 20.7 (20.7 / 24.0 / 24.1) |

(Effects: Reduced already drops the grade, so its last two columns differ only by noise.)

## Where the frame goes

### Between runs (1.3.0-rc1, one system switched off per process)

Only the grade pass and its bloom rise clearly above the run-to-run noise with this method:

| switched off | kettle_quiet | kettle_combat8 | pumpstation_rain | marquee_neon | vault_kowal_dark |
|---|---|---|---|---|---|
| whole grade + bloom pass | 21.6 (44%) | 22.8 (43%) | 20.1 (44%) | 20.6 (40%) | 19.2 (50%) |
| bloom only (grade kept) | 16.6 (34%) | 17.2 (32%) | 14.8 (33%) | 14.3 (28%) | 14.0 (36%) |

ms saved (share of the frame), best of 3. Every other system (haze, parallax layers, foreground, glows,
lightmap, rim, cast shadows, reflections, ambient particles, each background-life type, rain, actor shader,
combat FX, HUD) came out between −15 and +9 ms with this method, i.e. inside the noise; the full table with
those cells is in `docs/polish/perf/profile_rc1/summary.md` and should be read as "not resolved", not as costs.

The reason the bloom was so expensive: the pass declared a mipmapped screen texture. For that the Compatibility
renderer copies the screen and then rebuilds a blur chain of the whole screen with a 13-tap filter per level,
every frame, before the pass itself takes 16 texel reads per pixel.

### Paired, inside one run (this branch)

Average frame ms saved when one system is switched off, mean of 5 on/off pairs of 0.6 s windows ± standard
error, llvmpipe 1280×720 (`docs/polish/perf/paired_all.json`, `paired_all_2.json`; made with the bloom change in
place, so `grade` and `bloom` are the new pass and `fast_bloom` is the difference to the rc1 pass). Systems are
switched by hiding their nodes or swapping their data, so a cell is the rendering cost plus whatever script
stops with it. `n/a`: the room has no such system.

| switched off | kettle_quiet | kettle_combat8 | pumpstation_rain | vault_kowal_dark |
|---|---|---|---|---|
| `grade` | 12.5 ±0.5 | 9.9 ±0.7 | 11.4 ±0.7 | 10.9 ±0.6 |
| `parallax` | 8.8 ±1.5 | 8.8 ±0.1 | 8.0 ±1.2 | n/a |
| `hud` | 6.8 ±1.0 | 7.6 ±2.0 | 5.8 ±1.1 | 5.4 ±1.1 |
| `base_layer` | 3.9 ±1.3 | 2.5 ±0.8 | 4.0 ±1.1 | 5.8 ±1.7 |
| `bloom` | 3.8 ±1.3 | 4.5 ±1.1 | 3.5 ±0.9 | 4.4 ±0.5 |
| `glows` | 2.9 ±0.8 | 3.3 ±1.8 | 2.3 ±1.4 | 0.7 ±1.0 |
| `life` | 3.0 ±0.9 | 1.1 ±0.5 | -0.1 ±0.5 | -0.1 ±0.3 |
| `signs` | 2.8 ±0.5 | 3.0 ±1.6 | n/a | n/a |
| `reflect` | -0.5 ±1.4 | -0.2 ±0.9 | 2.5 ±2.2 | -2.0 ±2.6 |
| `actor_shader` | 2.4 ±1.6 | 2.1 ±0.6 | -1.5 ±1.1 | 0.8 ±1.7 |
| `rain` | n/a | n/a | 2.1 ±0.7 | n/a |
| `lanes` | 1.9 ±1.2 | 1.6 ±1.4 | 0.5 ±1.7 | n/a |
| `lightmap` | 1.8 ±1.2 | -1.7 ±0.8 | 0.3 ±0.9 | -1.2 ±0.9 |
| `clouds` | 1.7 ±1.6 | 1.0 ±1.2 | -0.6 ±0.4 | n/a |
| `haze` | 0.6 ±1.4 | 1.5 ±0.5 | -0.0 ±1.2 | n/a |
| `sway` | -0.9 ±0.7 | 0.2 ±1.1 | 1.5 ±0.8 | n/a |
| `actors_props` | 1.1 ±0.5 | 1.2 ±1.1 | -0.8 ±1.9 | -0.1 ±0.7 |
| `rim` | 0.1 ±0.7 | 0.2 ±1.3 | 0.8 ±0.9 | 1.2 ±1.2 |
| `water` | 1.1 ±1.1 | -0.3 ±2.8 | -0.8 ±1.1 | -0.5 ±0.8 |
| `fg` | 0.4 ±2.0 | -3.7 ±0.9 | -0.2 ±1.1 | 1.1 ±0.2 |
| `combat_fx` | n/a | 0.0 ±0.9 | -0.8 ±0.8 | 0.0 ±0.8 |
| `cast` | -3.9 ±1.3 | -0.8 ±1.2 | -0.1 ±0.5 | -1.6 ±1.2 |
| `ambient` | -0.8 ±1.1 | -0.4 ±1.4 | -1.0 ±0.8 | -0.2 ±0.5 |
| `shafts` | n/a | n/a | n/a | -0.3 ±0.2 |
| `pigeons` | -2.4 ±0.9 | -0.5 ±0.6 | -0.4 ±0.9 | n/a |
| `windows` | -1.1 ±0.9 | -2.4 ±1.2 | -0.4 ±0.7 | n/a |
| `fast_bloom` | -9.6 ±1.6 | -9.9 ±1.1 | -12.0 ±0.3 | -14.4 ±1.6 |

How to read it:

- Cells within about ±3 ms of zero are **not resolved**. Several come out negative (`cast`, `windows`, `fg`,
  `pigeons`), which cannot be real: the standard error understates the noise when the machine changes pace
  between the two windows of a pair.
- What does stand out, in order: the **grade pass** (10–12.5 ms, of which the new bloom is 3.5–4.5 ms), the
  **sky/far/mid parallax layers** (8–9 ms: three nearly full-screen blended layers behind a base layer that
  hides most of them), the **HUD** (5.4–7.6 ms for about 24 draw calls), the **base layer** (2.5–5.8 ms), the
  **glows** (2.3–3.3 ms outdoors), the **neon signs** (about 3 ms in Kettle, which is the whole-viewport copy
  they make) and the **rain** (2.1 ms).
- Rim light, cast shadows, reflections, the lightmap, ambient particles, windows, pigeons, clouds, sway, water,
  haze, light shafts and combat FX are each below what this method can see here. `actors_props` (hiding every
  actor and prop, 9 fighters in the combat scenario) is about 1 ms: on this renderer the cost is screen-sized
  layers and passes, not sprites.
- `fast_bloom` is a third, independent confirmation of Change 1: the rc1 pass costs 9.6–14.4 ms more.

## Change 1: bloom without the blur chain

File: `game/scripts/core/room_life.gd` (`GRADE_SHADER`, `BLOOM_DOWN_SHADER`, `BLOOM_ADD_SHADER`, `_make_grade`).

What it does now, in the same canvas layer as before:

1. The grade is drawn from a plain copy of the screen (no mipmaps, one exact texel read per pixel).
2. A `CanvasGroup` with one small child. The Compatibility renderer draws a group's children into the back
   buffer, so the child (160×90 pixels, 29 taps each) writes a small soft copy of the frame into the back
   buffer's corner without touching the screen. It reads the frame from the viewport texture and undoes the
   grade (the grade is affine), so the bloom threshold still sees the ungraded picture, as in rc1.
3. The group's own quad covers the screen, stretches that small image with bilinear filtering and adds the
   bloom, carried through the linear part of the grade. Adding "linear part of the grade × bloom" after the
   grade equals grading "picture + bloom", which is what rc1 computed.

Settings are untouched: the pass still exists only for Effects: Full with "Colour grade & bloom" on, still
halves with flash reduction, still reads the same `grade` block of `room.json`. The rc1 shader is kept in the
file as a reference (`PerfDebug` switch `fast_bloom` off selects it; nothing in the shipped game does), so the
comparison below can be repeated by anyone.

### Frame time, before/after (llvmpipe, 1280×720)

Between runs, 6 s samples, 2 interleaved runs each, best run shown (`docs/polish/perf/bloom_ab/`):

| scenario | rc1 pass: avg / p95 / >33.4 ms | new pass: avg / p95 / >33.4 ms | change in avg | every run's avg, rc1 | every run's avg, new |
|---|---|---|---|---|---|
| kettle_quiet | 46.8 / 53.7 / 100% | 39.7 / 51.5 / 97% | −7.1 ms (−15%) | 46.8 / 95.3 | 39.7 / 46.7 |
| kettle_combat8 | 53.4 / 66.5 / 100% | 41.0 / 51.2 / 100% | −12.4 ms (−23%) | 53.4 / 97.2 | 41.0 / 41.9 |
| pumpstation_rain | 45.3 / 51.6 / 100% | 35.5 / 41.4 / 73% | −9.8 ms (−22%) | 45.3 / 46.4 | 35.5 / 35.8 |
| vault_kowal_dark | 44.5 / 76.2 / 96% | 29.4 / 35.5 / 9% | −15.1 ms (−34%) | 44.5 / 54.6 | 29.4 / 29.4 |

Paired inside one run, 6 pairs of 0.6 s windows, two runs (`docs/polish/perf/paired_bloom.r0.json`, `.r1.json`).
"Extra cost of the rc1 pass" is the mean of (rc1 window − new window) ± standard error:

| scenario | run 1 | run 2 |
|---|---|---|
| kettle_quiet | 10.2 ±0.9 ms | 8.2 ±5.5 ms |
| kettle_combat8 | 14.5 ±5.2 ms | 9.7 ±7.8 ms |
| pumpstation_rain | 6.7 ±1.4 ms | 8.6 ±0.5 ms |
| vault_kowal_dark | 14.1 ±2.1 ms | 9.8 ±1.1 ms |

(The large errors in run 2 of the two Kettle scenarios are a disturbed phase of the machine: frames were
60–100 ms throughout those windows. The sign is the same in every case, and the `fast_bloom` row of the profile
table above is a third run: 9.6 ±1.6, 9.9 ±1.1, 12.0 ±0.3 and 14.4 ±1.6 ms.) Draw calls go up by 1–3 per frame.
After the change the whole grade + bloom pass costs 10–12.5 ms in the paired profile (it was about 20 ms
between runs), of which the bloom is 3.5–4.5 ms (it was about 15 ms).

### Picture, before/after

`game/tests/grade_ab.gd` runs a room, pauses the tree, and draws the same frozen frame with the rc1 pass, the
new pass and with no bloom, so the captures differ only by the pass. Differences against the rc1 pass on the
0–255 scale (`docs/polish/perf/grade_ab.txt`):

| frame | new pass: mean / p99 / p99.9 / max | pixels off by more than 8 levels | for scale, no bloom at all: mean / p99 / more than 8 levels |
|---|---|---|---|
| Kettle Street x=640 (diner, laundromat) | 0.114 / 4 / 7 / 14 | 0.02% | 0.867 / 26 / 9.99% |
| Kettle Street x=1150 | 0.009 / 1 / 4 / 11 | 0.01% | 0.022 / 3 / 0.10% |
| Marquee Strip x=700 | 0.066 / 3 / 7 / 12 | 0.03% | 0.462 / 19 / 7.27% |
| Marquee Strip x=1300 | 0.025 / 2 / 7 / 12 | 0.02% | 0.085 / 9 / 1.10% |
| Pump Station Road x=760 | 0.002 / 0 / 2 / 10 | 0.00% | 0.004 / 0 / 0.05% |
| Greyline Cargo Vault x=450 | 0.005 / 0 / 4 / 11 | 0.00% | 0.030 / 0 / 0.44% |
| Lucky Spoon Diner | 0.051 / 3 / 6 / 12 | 0.01% | 0.341 / 17 / 4.86% |

For reference the film grain in the same pass is ±1.5 levels. I looked at the captures side by side and could
not tell them apart; three pairs and their ×8 amplified differences are in `docs/polish/perf/grade_ab/`
(`*_rc1.jpg`, `*_new.jpg`, `*_diff_x8.jpg`; JPEG copies, the numbers above come from the lossless captures).
The web export draws the same pass correctly under WebGL2 (SwiftShader): checked in the packaged smoke test's
screenshots.

Limits of this evidence: the comparison is at 1280×720 on two software rasterisers. The new pass relies on how
the Compatibility renderer handles `CanvasGroup` (children drawn into the back buffer) and on reading the
viewport texture there; that is the renderer the project is pinned to, but it has not been looked at on a real
GPU driver, at other window sizes or on a phone. If it ever misbehaves on some driver, "Colour grade & bloom:
Off" removes the whole pass, and the rc1 shader is still in the file.

Two engine behaviours found on the way (Godot 4.7.2 Compatibility), both avoided in the final code:

- A canvas shader cannot read `hint_screen_texture` in `vertex()`: the Godot shader compiles, the GLSL does not
  (`color_buffer undeclared`). This ruled out computing the bloom per vertex of a grid.
- After a `render_mode blend_disabled` item is drawn into the back buffer as a `CanvasGroup` child, the group's
  own quad is drawn without blending. The downsample shader therefore uses normal blending with alpha 1.

## Change 2: export size

### Audit

`tools/perf/audit_assets.py` checks every id the data and scripts can ask for against the v2 folders, and the
export presets' exclude filter:

- All three presets already exclude the v1 PNGs (`assets/{sprites/characters,bg,props,portraits,fx,icons,
  weapons,pickups,ui}/*.png`, 6.07 MB of source) and the old pixel font. **There was nothing left to remove.**
- Nothing that is excluded is needed: 33/33 rooms have `bg2/<id>/room.json` and every file it names; 72/72
  character sheets (player, 6 gangs × 6 archetypes, bosses, `rook_p2`, encounter and story NPCs, background
  walkers and passers-by), 102/102 icons, 57/57 prop types, 17/17 weapons, 9/9 pickups, 36/36 speaker portraits,
  the effect ids and the literal UI ids all resolve to v2 art.
- The v1 folders still ship their small JSON files, and must: `Content` loads `assets/props/props.json`,
  `weapons/weapons.json`, `fx/fx.json`, `pickups/pickups.json` and `ui/map.json` (14 KB together).
- 60 v1 character JSON files (87 KB, 0.1% of the pack) are in the pack and unreachable, because
  `SpriteLib._char_v1` only reads them when the v1 PNG exists. Left alone: not worth a filter change.

Pack contents by group (`tools/perf/pck_list.py`, `docs/polish/perf/web/pck_before.json`, `pck_after.json`):

| group | 1.3.0-rc1 | this branch |
|---|---|---|
| character sheets (`sprites/chars`) | 24.11 MB | 18.08 MB |
| room art (`bg2`) | 18.01 MB | 12.65 MB |
| music (15 tracks, Ogg Vorbis) | 16.29 MB | 16.29 MB |
| portraits2 | 3.57 MB | 3.20 MB |
| ui2 | 1.21 MB | 1.14 MB |
| sound effects | 1.03 MB | 1.03 MB |
| scripts, data, fonts, fx2, icons2, props2, rest | 1.8 MB | 1.8 MB |
| **`index.pck`** | **66.19 MB** | **54.32 MB** |

Oversized textures: none found that are drawn smaller than authored; the large ones are the 2048×720 room
layers and the character atlases, both drawn 1:1 at 720p. Audio: music is 30% of the new pack. Re-encoding it at
a lower bitrate would be a lossy step that nobody here can check by ear, so it was not done.

### The change

`game/project.godot`: `rendering/textures/webp_compression/compression_method` 4 → 6.

Why it matters so much: the art is palette-quantised, but the importer's "fix alpha border" writes neighbour
colours into the transparent pixels around every sprite edge. That pushes an atlas from ≤256 colours to a few
hundred, and libwebp only finds the compact encoding for such an image in its exhaustive mode, which it enters at
method 6 with factor 100 (the factor was already 100). Example: `sprites/chars/duke.png` is 338 KB as a PNG,
928 KB imported at method 4 and 359 KB at method 6. Turning the alpha-border fix off would be smaller still but
changes edge filtering, so it was left on.

- **Pixels**: `tools/perf/verify_ctex_pixels.py` decoded all 1025 imported textures, every mip level, from the
  method-4 cache and the method-6 cache: 1025 identical, 0 different. Imported texture bytes 51.08 → 38.40 MB.
- **Cost**: importing the textures took 7 min 18 s on 4 cores here (the whole first import was about 4–5 min
  before). It is paid once per fresh `game/.godot`.
- **Existing caches**: Godot does not re-import a texture because a project setting changed. A `game/.godot`
  made before this change keeps the larger files until the textures are re-imported:
  `python3 tools/package.py <version> --reimport-textures` (new flag) or delete `game/.godot` and import.
- The pack is the same for every platform, so the Linux and Windows zips shrink by the same 11.9 MB. I only
  built and measured the web export; the Windows zip (102.3 MB in 1.3) should land near 90 MB, under GitHub's
  100 MB limit, but that is arithmetic, not a measurement.

### Web size by file

Raw bytes and gzip -6 of each file (`tools/perf/web_sizes.py`), and bytes on the wire measured by Chromium from
the plain test server, which sends files as they are (`tools/webtest/load_test.js`):

| file | 1.3.0-rc1 raw | this branch raw | 1.3.0-rc1 gzip -6 | this branch gzip -6 |
|---|---|---|---|---|
| `index.pck` | 66,185,812 | 54,317,828 | 64,374,550 | 52,502,465 |
| `index.wasm` | 39,514,754 | 39,514,754 | 10,114,291 | 10,114,291 |
| `index.js` | 279,815 | 279,815 | 68,740 | 68,740 |
| `index.html`, icons, worklets | 67,666 | 67,666 | 52,722 | 52,722 |
| **total** | **106,048,047** | **94,180,063** | **74,610,303** | **62,738,218** |
| release zip (deflate -9) | 74,540,469 | 62,669,102 | | |
| measured on the wire, uncompressed host | 101.10 MiB | 89.78 MiB | | |

The "1.3.0-rc1" column is this branch exported from the method-4 import cache; its pack is 7 KB larger than the
released 1.3 build in the main checkout's `build/web` (66,178,844 bytes; identical wasm) because of the scripts
added here. Whether itch.io compresses `.pck`/`.wasm` in transit was not checked; the zip is what a player
downloads from the page's download button, the uncompressed and gzip totals bracket what the embedded player
transfers.

### Web load time

Headless Chromium, software WebGL, local server, fresh browser context per run. `title` is from the start of
navigation to the title screen's first frames; `control` is from the key press that confirms save slot 1 to the
moment the player can act, with the intro dialogue skipped as soon as it opens (±0.6 s). The timing marks come
from `game/scripts/core/load_marks.gd`, which exists only when the URL has `?bo_debug` (or `-- --bo-debug` on
desktop).

| profile | build | transfer | engine start | title | new game → control |
|---|---|---|---|---|---|
| unthrottled (3 runs each) | 1.3.0-rc1 | 101.10 MiB | 0.61 / 0.86 / 0.87 s | 2.17 / 2.83 / 3.09 s | 8.4 / 12.6 / 13.4 s |
| unthrottled (3 runs each) | this branch | 89.78 MiB | 0.75 / 0.68 / 1.57 s | 3.16 / 2.94 / 3.40 s | 12.8 / 14.2 / 12.4 s |
| `cable-50mbit`: 50 Mbit/s down, 10 up, 20 ms latency (1 run each) | 1.3.0-rc1 | 101.10 MiB | 17.9 s | 19.2 s | 8.2 s |
| `cable-50mbit` (1 run each) | this branch | 89.78 MiB | 15.7 s | 16.9 s | 13.0 s |

Reading it honestly:

- With a real connection the download dominates and the smaller pack is 2.3 s faster to the title at 50 Mbit/s
  (11.3 MiB less at 6.25 MB/s is 1.9 s). At 10 Mbit/s the same arithmetic gives about 9.5 s less; that profile
  exists in the script (`dsl-10mbit`) but was not run.
- Unthrottled start-up is CPU-bound (wasm compilation, software WebGL) and the three runs per build overlap:
  there is no measurable change in either direction. The `control` time is dominated by the fixed intro walk and
  by this machine's speed (the game runs at 4–8 FPS in SwiftShader); the spread between runs (8.4–13.4 s for
  the same build) is larger than any difference between the builds.
- Cache: on reload in the same browser context the small files revalidate (304) but `index.wasm` and
  `index.pck` are fetched again with 200, before and after alike, with this plain Python server and headless
  Chromium. File names and the server are unchanged by this work, so cache behaviour is the same as in 1.3; why
  the two large files are not served from the HTTP cache was not investigated.
- Smoke tests on the packaged web build of this branch: `game_test.js` plays from the title through the intro
  fight, the status screen and a reload with the save persisting; `audio_test.js` reports a running audio
  context with non-zero output after the first key press. Both passed.

## Tests

From `game/`: `godot --headless res://tests/unit_tests.tscn` 8568 passed; `--fixed-fps 60` `feature_tests` 67,
`quest_tests` 23, `expansion_tests` 37; 0 failed, run after each change.

## Not done, and why

- **Parallax overdraw (8–9 ms here).** The sky, far and mid layers are drawn in full although the base layer
  covers most of them. Drawing the sky without blending (it is the bottom layer) and clipping each layer to
  the rows the base layer leaves open would cut this; the second needs a per-room "base is opaque below row N"
  number from the art pipeline. Found only at the end, by the paired profile; not attempted.
- **HUD (5–8 ms here).** `hud.gd` was off limits. Worth checking there for full-screen or large controls that
  are drawn while fully transparent (flash and fade rectangles, cards), which cost fill rate for nothing.
- **Per-sign back-buffer copies.** Rooms with neon signs (`oq_kettle`, `nm_marquee`, …) copy the whole viewport
  once per frame for a few small sign rectangles (`_make_sign`, `BackBufferCopy.COPY_MODE_VIEWPORT`). A copy
  per sign in rect mode, or sampling the base texture instead of the screen, would avoid it. Not done: no time
  left to measure and compare pictures.
- **Invisible cast shadows.** `fr_pumpstation` and `ul_vault` set `cast_shadow.alpha` to 0, which still makes
  `Actor` draw a fully transparent shadow sprite per actor. Skipping the block in `RoomVisuals.build` when
  alpha is 0 would remove those draws. Not done for the same reason.
- **Window overlays.** Each `window` life entry keeps a clipped `Control`, a `ColorRect` that is fully
  transparent most of the time and a parked silhouette sprite. Hiding them while they show nothing would save
  draw calls (which matter more in a browser than here). Not measured.
- **Files I was asked not to edit.** `Actor._update_visual()` and `_update_lighting()` run on every physics
  tick for every actor (several times per rendered frame when the frame rate is low), set five shader
  parameters and build a dictionary in `rim_at`. Moving the lighting half to once per rendered frame is the
  obvious change in `actor.gd`. The measured simulation cost is at most 2.1 ms per frame with 9 actors, so it
  is not a bottleneck on this renderer; in a browser, where script is slower, it may matter more.
- **Music bitrate, a custom web export template, turning off the alpha-border fix**: each would cut the
  download further, each changes what the player gets or cannot be verified here.
- **Other systems' costs between runs**: not resolved by the between-run method (see above); the paired table is
  the one to use.

## Things that looked wrong but were out of scope

- The old perf harness's walking scenario did not walk (action name `right`).
- `index.wasm`/`index.pck` are re-downloaded on reload in headless Chromium against the plain test server.
- 60 unreachable v1 character JSON files ship in every pack (87 KB).
- A new `class_name` script is not usable until `godot --headless --import` has run once; a checkout that adds
  one fails every test with "Identifier not declared" until then (this bit one of my own measurement runs).
- The harness and the screenshot tool write an autosave into `user://` like the game does (pre-existing).

## Not verified, and how to verify it

Nothing below has been measured. Each needs a person and the device.

| not verified | what to do |
|---|---|
| Any real GPU (integrated or discrete), Windows or Linux | Run the packaged build. **Settings → Show FPS: On** puts the frame rate and the slowest recent frame in the corner. Walk Kettle Street, fight the first wave, visit Marquee Strip and Pump Station Road, and note the two numbers in each with Effects: Full and "Colour grade & bloom" On, then with it Off. A finished playthrough ends on the **run summary card** (after the ending, before the credits): it shows the session's average FPS, the share of frames under 30 FPS, the slowest frame, the effects preset, the window size and the GPU/driver line. Screenshot it. |
| The new bloom pass on real drivers | In the same rooms compare "Colour grade & bloom" On against Off: lit windows, lamps and neon should have the same soft glow as in 1.3, with no black or white flashes, no blocky corner at the top left and no change when the window is resized or made fullscreen. |
| Steam Deck | Same as above in Gaming Mode at 1280×800, plus the Deck's own performance overlay (level 2 or higher shows frame time and GPU load). `STEAM_DECK.md` has the launch steps. |
| Phones and tablets (touch browsers) | Open the web build. "Colour grade & bloom" starts Off there; note FPS with Show FPS, then turn it On in Settings, enter a new room and note it again. |
| Browsers other than headless Chromium (Firefox, Safari, desktop Chrome with a GPU) | Load the web build, check the title appears, start a new game, check sound after the first key press, and repeat the FPS notes. For load time: DevTools → Network, "Disable cache", reload, read the transferred total and the finish time; with a throttling preset if wanted. |
| Windows and Linux zips after the size change | `python3 tools/package.py <version> --reimport-textures`, read the sizes it prints, run each build once. |
| itch.io transfer encoding and caching | Upload is a separate, manual step; in the browser's Network tab check the `content-encoding` of `index.pck`/`index.wasm` and whether a second visit is served from cache. |

The main branch has since added an opt-in **Settings → Playtest log**; I did not have it in this worktree and
have not used it. If it records the same counters, it is the easiest way to send the numbers back.

## Files

- Game: `game/scripts/core/room_life.gd` (bloom), `room_visuals.gd` and `combat_fx.gd` (profiling switches
  only), `perf_debug.gd` (new, switches), `load_marks.gd` (new, debug-only timing marks),
  `scripts/autoload/scene_flow.gd` (2 lines to create the marks node), `project.godot` (WebP method).
- Tests: `game/tests/perf.gd` (rewritten), `grade_ab.gd` + `.tscn` (new).
- Tools: `tools/perf/` (`perf_matrix.py`, `paired_table.py`, `grade_diff.py`, `audit_assets.py`, `pck_list.py`,
  `web_sizes.py`, `verify_ctex_pixels.py`), `tools/webtest/load_test.js` (new), `tools/webtest/serve.py`
  (`--gzip` option), `tools/package.py` (`--reimport-textures`).
- Evidence: `docs/polish/perf/` (`profile_rc1/`, `bloom_ab/`, `paired_*.json`, `grade_ab.txt`, `grade_ab/`, `web/`).
