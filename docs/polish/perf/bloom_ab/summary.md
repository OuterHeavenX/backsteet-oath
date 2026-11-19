Renderer: `llvmpipe (LLVM 20.1.2, 256 bits)` (gl_compatibility, OpenGL 4.5 (Core Profile) Mesa 25.2.8-0ubuntu0.24.04.4), Ubuntu 24.04.5 LTS, CPU `Intel(R) Xeon(R) Processor @ 2.30GHz` x4, window 1280x720 px, Godot 4.7.2-stable (official), game 1.3.0-rc1, debug build: true. **Software renderer: not GPU numbers.**

Sample 6.0s per scenario after 1.0s warm-up, up to 2 runs per configuration (interleaved). Rows show the best run (lowest average); `runs avg` lists every run's average so the run-to-run noise is visible. Times in ms.

### Configuration `no_fast_bloom`

| scenario | frames | avg | p50 | p90 | p95 | p99 | max | >16.7 ms | >20 ms | >33.4 ms | spikes | sim | proc | other | draw calls | nodes room/total | load | reload | runs avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kettle_quiet | 129 | 46.8 | 45.3 | 52.4 | 53.7 | 63.3 | 91.7 | 129 (100%) | 129 (100%) | 129 (100%) | 1 | 0.65 | 0.43 | 45.7 | 68 | 173/262 | 402 | 54 | 46.8 / 95.3 |
| kettle_combat8 | 113 | 53.4 | 52.1 | 59.5 | 66.5 | 72.4 | 88.8 | 113 (100%) | 113 (100%) | 113 (100%) | 0 | 1.95 | 0.57 | 50.9 | 88 | 234/323 | 121 | 55 | 53.4 / 97.2 |
| pumpstation_rain | 133 | 45.3 | 44.7 | 49.5 | 51.6 | 55.0 | 61.3 | 133 (100%) | 133 (100%) | 133 (100%) | 0 | 0.93 | 0.47 | 43.9 | 68 | 141/230 | 124 | 52 | 45.3 / 46.4 |
| vault_kowal_dark | 136 | 44.5 | 38.5 | 67.1 | 76.2 | 92.1 | 98.0 | 136 (100%) | 136 (100%) | 131 (96%) | 6 | 0.89 | 0.33 | 43.3 | 74 | 93/182 | 87 | 84 | 44.5 / 54.6 |

### Configuration `base`

| scenario | frames | avg | p50 | p90 | p95 | p99 | max | >16.7 ms | >20 ms | >33.4 ms | spikes | sim | proc | other | draw calls | nodes room/total | load | reload | runs avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kettle_quiet | 152 | 39.7 | 38.4 | 44.7 | 51.5 | 73.9 | 74.6 | 152 (100%) | 152 (100%) | 147 (97%) | 0 | 0.59 | 0.42 | 38.7 | 69 | 175/264 | 482 | 52 | 39.7 / 46.7 |
| kettle_combat8 | 147 | 41.0 | 40.0 | 47.4 | 51.2 | 62.5 | 64.7 | 147 (100%) | 147 (100%) | 147 (100%) | 0 | 1.58 | 0.47 | 39.0 | 89 | 236/325 | 118 | 44 | 41.0 / 41.9 |
| pumpstation_rain | 169 | 35.5 | 35.2 | 39.9 | 41.4 | 46.5 | 48.3 | 169 (100%) | 169 (100%) | 123 (73%) | 0 | 0.75 | 0.39 | 34.4 | 69 | 141/230 | 101 | 42 | 35.5 / 35.8 |
| vault_kowal_dark | 205 | 29.4 | 28.9 | 32.8 | 35.5 | 40.7 | 44.0 | 205 (100%) | 205 (100%) | 18 (9%) | 0 | 0.63 | 0.30 | 28.5 | 76 | 97/186 | 78 | 28 | 29.4 / 29.4 |

### Cost per system: average frame ms saved when it is switched off (best `base` run − best variant run)

`~` marks a difference no larger than the gap between the two best runs of either configuration (not distinguishable from noise). `n/a`: the room has no such system. In brackets: share of the base frame, and the change in draw calls.

| switched off | kettle_quiet | kettle_combat8 | pumpstation_rain | vault_kowal_dark |
|---|---|---|---|---|
| `no_fast_bloom` | ~-7.1 (-18%, -0 dc) | ~-12.4 (-30%, -1 dc) | -9.8 (-28%, -1 dc) | -15.1 (-51%, -1 dc) |
