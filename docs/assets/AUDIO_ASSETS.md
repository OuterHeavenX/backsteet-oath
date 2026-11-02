# BACKSTREET OATH - Audio Assets

All music and sound effects are **procedurally synthesized by tools/audio/gen_audio.py, original, project-owned**. No samples, recordings or third-party material are used; every melody is an original composition written for this game.

Rebuild everything with `python3 tools/audio/gen_audio.py` (Python 3 + numpy + ffmpeg/libvorbis). Output is deterministic. Use `--only id1,id2` to rebuild single assets and `--verify` to re-run the checks and regenerate this file.

## Format

- Music: `game/assets/audio/music/<id>.ogg`, Ogg Vorbis q5, 44.1 kHz **stereo**.
- SFX: `game/assets/audio/sfx/<id>.ogg`, Ogg Vorbis q5, 44.1 kHz **mono**.
- Looping music is an exact whole number of bars; the file length *is* the loop. In Godot import the looping files with **Loop = on, Loop Offset = 0** (AudioStreamOggVorbis `loop = true`). `victory` and `defeat` are one-shots. The four `*_loop` SFX also loop with offset 0.
- Seamless loops: the arrangement is rendered past the loop end and the tail is wrapped onto the start; echo, room reverb, EQ and limiting are applied circularly, so the last sample flows into the first.
- Levels: music is normalised to about -16 LUFS integrated (BS.1770 K-weighting; `safe_hub` -17, `setback`/`defeat` -18 for their quieter mood) with a soft limiter, peaks below -1 dBFS after encoding. One-shot SFX are normalised by momentary loudness per category (impacts loudest, UI and footsteps soft); ambient loops sit at -25..-28 LUFS so they can play under music.

Total size of all OGG files: **16.06 MB** (78 files).

## Music

| id | file | duration | loop | bars | BPM | key | description | origin |
|---|---|---|---|---|---|---|---|---|
| `title` | `music/title.ogg` | 48.76 s | yes | 24 | 118.12 | D major | Anthemic, hopeful title theme; pulse lead over driving octave bass, harmony lift in the reprise | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `old_quarter` | `music/old_quarter.ogg` | 68.67 s | yes | 32 | 111.83 | G mixolydian | Home-district street funk; swung 16ths, clav stabs, organ answers, slap-style bass | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `canal_market` | `music/canal_market.ogg` | 61.81 s | yes | 32 | 124.25 | F major | Sunny calypso/ska bounce; steel-pan lead, offbeat skank, clave and timbales | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `ironworks` | `music/ironworks.ogg` | 67.20 s | yes | 28 | 100.00 | E minor | Heavy industrial half-time groove; anvil, pipe and chain percussion, saw lead | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `neon_mile` | `music/neon_mile.ogg` | 61.81 s | yes | 32 | 124.25 | A minor | Night-time synth-pop; 16th arpeggios, gated snare, PWM lead with echo | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `floodgate` | `music/floodgate.ogg` | 65.31 s | yes | 36 | 132.30 | D harmonic minor | Tense storm chase; galloping bass, tremolo pulses, timpani and thunder | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `warehouse` | `music/warehouse.ogg` | 69.66 s | yes | 32 | 110.25 | C harmonic minor | Dark pulsing infiltration; heartbeat kick, eerie vibrato lead, metallic hits | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `underline` | `music/underline.ogg` | 79.82 s | yes | 32 | 96.22 | D minor | Subterranean tunnel groove; dripping bell echoes, sub bass, pipe and chain percussion | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `safe_hub` | `music/safe_hub.ogg` | 62.69 s | yes | 24 | 91.88 | F major | Relaxed swung diner/shop jazz; vibes lead, e-piano comping, walking bass, brushes | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `boss` | `music/boss.ogg` | 57.60 s | yes | 36 | 150.00 | F harmonic minor | Intense gang-boss fight; chromatic unison riff, 16th bass, brass alarm stabs | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `rook` | `music/rook.ogg` | 75.43 s | yes | 44 | 140.00 | B harmonic minor | Dramatic final boss; bell toll intro, choir, timpani, Neapolitan riff break, layered climax | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `setback` | `music/setback.ogg` | 37.93 s | yes | 12 | 75.93 | G harmonic minor | Somber, tense workshop-attacked cue; heartbeat, ticking clock, flute over e-piano | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `ending` | `music/ending.ogg` | 79.82 s | yes | 32 | 96.22 | D major | Credits: triumphant title reprise, new warm credits melody, jazzy interlude, title bridge | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `victory` | `music/victory.ogg` | 3.95 s | no | - | 150.00 | C major | Short brass/pulse fanfare after a boss win | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `defeat` | `music/defeat.ogg` | 3.99 s | no | - | 120.27 | A minor | Short sad descending jingle | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |

BPM values are exact: the 16th-note is a whole number of samples (nominal tempo nudged by < 0.3 %).

## Sound effects

| id | file | duration | loop | description | origin |
|---|---|---|---|---|---|
| `punch_light` | `sfx/punch_light.ogg` | 0.250 s | no | Light jab impact: low thump, noise crack, pitch drop | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `punch_heavy` | `sfx/punch_heavy.ogg` | 0.450 s | no | Heavy punch: deeper thump, sub boom, crunchy crack | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `kick_light` | `sfx/kick_light.ogg` | 0.280 s | no | Light kick impact with short air slap | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `kick_heavy` | `sfx/kick_heavy.ogg` | 0.500 s | no | Heavy kick: long low thump and crunch | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `whiff` | `sfx/whiff.ogg` | 0.220 s | no | Missed attack: band-passed noise sweep | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `block` | `sfx/block.ogg` | 0.160 s | no | Blocked hit: short leathery/metallic click | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `perfect_guard` | `sfx/perfect_guard.ogg` | 0.900 s | no | Perfect guard: bright ringing ping | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `hurt_player` | `sfx/hurt_player.ogg` | 0.340 s | no | Player hurt: gritty downward pitch blip (abstract, no voice) | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `hurt_enemy` | `sfx/hurt_enemy.ogg` | 0.280 s | no | Enemy hurt: lower, grittier downward blip | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `fall` | `sfx/fall.ogg` | 0.600 s | no | Body hits the ground with a small bounce | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `land` | `sfx/land.ogg` | 0.200 s | no | Landing from a jump: short thud with grit | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `footstep_a` | `sfx/footstep_a.ogg` | 0.090 s | no | Soft footstep scuff (variant A) | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `footstep_b` | `sfx/footstep_b.ogg` | 0.090 s | no | Soft footstep scuff (variant B) | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `jump` | `sfx/jump.ogg` | 0.240 s | no | Jump: rising chip blip with air | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `pickup` | `sfx/pickup.ogg` | 0.240 s | no | Item pickup: two quick rising chip notes | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `drop` | `sfx/drop.ogg` | 0.320 s | no | Item dropped: small thud and bounce | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `cash` | `sfx/cash.ogg` | 0.470 s | no | Money pickup: bright two-note coin chime | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `cash_big` | `sfx/cash_big.ogg` | 1.000 s | no | Big money pickup: coin cascade and final chime | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `purchase` | `sfx/purchase.ogg` | 0.600 s | no | Shop purchase: register click and chime | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `deny` | `sfx/deny.ogg` | 0.300 s | no | Not allowed / cannot afford: low two-note buzz | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `eat` | `sfx/eat.ogg` | 0.480 s | no | Eating: three crunchy bites | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `drink` | `sfx/drink.ogg` | 0.600 s | no | Drinking: three gulps | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `heal` | `sfx/heal.ogg` | 0.900 s | no | Health restored: rising sparkle arpeggio | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `level_up` | `sfx/level_up.ogg` | 1.200 s | no | Level up: rising pulse arpeggio with bell chord | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `weapon_hit_blunt` | `sfx/weapon_hit_blunt.ogg` | 0.400 s | no | Bat/pipe-wood blunt hit: thock and thump | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `weapon_hit_metal` | `sfx/weapon_hit_metal.ogg` | 0.600 s | no | Metal weapon hit: clang over impact | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `weapon_hit_chain` | `sfx/weapon_hit_chain.ogg` | 0.500 s | no | Chain hit: rattling links and impact | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `weapon_swing` | `sfx/weapon_swing.ogg` | 0.300 s | no | Heavy weapon swing whoosh | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `throw` | `sfx/throw.ogg` | 0.250 s | no | Throw release whoosh | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `bottle_break` | `sfx/bottle_break.ogg` | 0.750 s | no | Glass bottle shatter | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `crate_break` | `sfx/crate_break.ogg` | 0.750 s | no | Wooden crate smashed to splinters | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `metal_clang` | `sfx/metal_clang.ogg` | 0.850 s | no | Big ringing metal clang (barrels, poles) | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `tire_bounce` | `sfx/tire_bounce.ogg` | 0.420 s | no | Rubber tire bounce | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `ui_move` | `sfx/ui_move.ogg` | 0.045 s | no | Menu cursor move tick | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `ui_confirm` | `sfx/ui_confirm.ogg` | 0.110 s | no | Menu confirm: rising two-note blip | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `ui_cancel` | `sfx/ui_cancel.ogg` | 0.100 s | no | Menu cancel: falling two-note blip | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `ui_open` | `sfx/ui_open.ogg` | 0.100 s | no | Menu open: upward blip sweep | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `ui_close` | `sfx/ui_close.ogg` | 0.090 s | no | Menu close: downward blip sweep | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `door` | `sfx/door.ogg` | 0.850 s | no | Door: latch click, creak, close thump | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `dialogue_blip` | `sfx/dialogue_blip.ogg` | 0.035 s | no | Dialogue text blip (per character) | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `quest_update` | `sfx/quest_update.ogg` | 0.650 s | no | Quest updated: two-note chime | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `quest_complete` | `sfx/quest_complete.ogg` | 1.300 s | no | Quest complete: chime triad with warm swell | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `boss_intro` | `sfx/boss_intro.ogg` | 2.700 s | no | Boss intro: riser into low boom, brass cluster and gong | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `ko` | `sfx/ko.ogg` | 1.250 s | no | Knockout: heavy hit, boom, echoes and bell ring | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `dizzy` | `sfx/dizzy.ogg` | 1.200 s | no | Dizzy/stunned: warbling circling tones | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `grab` | `sfx/grab.ogg` | 0.250 s | no | Grab: cloth swish and soft thud | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `slam` | `sfx/slam.ogg` | 0.650 s | no | Body slam: very heavy thump and rumble | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `shockwave` | `sfx/shockwave.ogg` | 1.000 s | no | Shockwave: low boom with expanding whoosh | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `whistle` | `sfx/whistle.ogg` | 0.800 s | no | Trilling whistle (police/referee style) | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `crate_fall` | `sfx/crate_fall.ogg` | 0.850 s | no | Crate falls and lands with a bounce | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `alarm` | `sfx/alarm.ogg` | 2.400 s | no | Two-tone alarm siren | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `dog_bark` | `sfx/dog_bark.ogg` | 0.550 s | no | Stylized synth dog bark (two woofs) | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `splash` | `sfx/splash.ogg` | 0.850 s | no | Water splash with bubbles | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `crowd_cheer` | `sfx/crowd_cheer.ogg` | 2.800 s | no | Abstract crowd cheer swell with claps | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `countdown_tick` | `sfx/countdown_tick.ogg` | 0.120 s | no | Countdown tick beep | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `bus_horn` | `sfx/bus_horn.ogg` | 0.900 s | no | City bus horn honk | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `save` | `sfx/save.ogg` | 0.900 s | no | Game saved: soft rising chime | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `guard_break` | `sfx/guard_break.ogg` | 0.750 s | no | Guard broken: shatter, thump, falling tone | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `charge` | `sfx/charge.ogg` | 1.000 s | no | Charging power: rising tremolo sweep | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `rain_loop` | `sfx/rain_loop.ogg` | 10.000 s | yes | Seamless rain ambience loop with drips | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `street_loop` | `sfx/street_loop.ogg` | 10.000 s | yes | Seamless city ambience: distant traffic, murmur, passing cars | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `industrial_loop` | `sfx/industrial_loop.ogg` | 10.000 s | yes | Seamless factory ambience: hum, press thumps, steam, clinks | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |
| `neon_buzz_loop` | `sfx/neon_buzz_loop.ogg` | 6.000 s | yes | Seamless neon-sign hum with flicker crackles | procedurally synthesized by tools/audio/gen_audio.py, original, project-owned |

## Level report (measured from the decoded OGG files)

Peak = sample peak dBFS, RMS = whole-file RMS dBFS, LUFS = integrated loudness for loops / max momentary (300 ms) loudness for one-shots, Seam = |last-first sample| jump divided by the 99th-percentile sample-to-sample step (values around 1 or below mean the loop point is inaudible).

| id | type | peak dBFS | RMS dBFS | LUFS | seam | size KB |
|---|---|---|---|---|---|---|
| `title` | music | -3.07 | -18.84 | -16.0 | 0.33 | 952 |
| `old_quarter` | music | -4.05 | -18.17 | -16.0 | 0.42 | 1270 |
| `canal_market` | music | -3.28 | -17.83 | -16.0 | 0.07 | 1101 |
| `ironworks` | music | -2.76 | -18.64 | -16.1 | 0.14 | 1267 |
| `neon_mile` | music | -2.69 | -18.20 | -16.0 | 0.13 | 1233 |
| `floodgate` | music | -2.75 | -18.12 | -16.0 | 0.47 | 1196 |
| `warehouse` | music | -2.37 | -18.06 | -16.0 | 0.13 | 1330 |
| `underline` | music | -1.71 | -18.07 | -16.0 | 0.04 | 1425 |
| `safe_hub` | music | -3.30 | -18.73 | -16.9 | 0.15 | 1091 |
| `boss` | music | -3.85 | -17.75 | -16.0 | 0.64 | 1062 |
| `rook` | music | -2.19 | -17.88 | -16.0 | 0.51 | 1377 |
| `setback` | music | -6.07 | -19.28 | -18.0 | 0.10 | 601 |
| `ending` | music | -3.40 | -18.23 | -16.0 | 0.80 | 1469 |
| `victory` | music | -4.33 | -19.80 | -14.0 | - | 71 |
| `defeat` | music | -7.00 | -20.29 | -16.2 | - | 81 |
| `punch_light` | sfx | -1.26 | -11.44 | -13.9 | - | 5 |
| `punch_heavy` | sfx | -1.19 | -9.18 | -11.2 | - | 7 |
| `kick_light` | sfx | -1.12 | -11.11 | -13.4 | - | 6 |
| `kick_heavy` | sfx | -1.37 | -8.53 | -11.0 | - | 7 |
| `whiff` | sfx | -4.86 | -19.59 | -18.3 | - | 6 |
| `block` | sfx | -1.19 | -13.66 | -16.8 | - | 5 |
| `perfect_guard` | sfx | -5.25 | -20.57 | -14.0 | - | 8 |
| `hurt_player` | sfx | -3.10 | -14.85 | -14.1 | - | 8 |
| `hurt_enemy` | sfx | -6.49 | -14.43 | -15.0 | - | 7 |
| `fall` | sfx | -2.15 | -11.95 | -12.9 | - | 9 |
| `land` | sfx | -2.47 | -12.88 | -17.0 | - | 6 |
| `footstep_a` | sfx | -3.68 | -17.79 | -24.0 | - | 5 |
| `footstep_b` | sfx | -3.12 | -17.64 | -24.0 | - | 5 |
| `jump` | sfx | -5.06 | -17.01 | -18.0 | - | 7 |
| `pickup` | sfx | -6.78 | -18.55 | -17.1 | - | 6 |
| `drop` | sfx | -1.65 | -18.12 | -19.0 | - | 6 |
| `cash` | sfx | -8.53 | -20.46 | -16.0 | - | 6 |
| `cash_big` | sfx | -8.12 | -20.40 | -15.1 | - | 12 |
| `purchase` | sfx | -6.92 | -19.79 | -15.0 | - | 7 |
| `deny` | sfx | -11.86 | -16.23 | -17.0 | - | 8 |
| `eat` | sfx | -1.21 | -18.81 | -16.3 | - | 8 |
| `drink` | sfx | -7.72 | -17.56 | -17.0 | - | 8 |
| `heal` | sfx | -7.23 | -20.16 | -16.0 | - | 14 |
| `level_up` | sfx | -4.36 | -18.94 | -14.0 | - | 14 |
| `weapon_hit_blunt` | sfx | -1.64 | -11.17 | -12.0 | - | 6 |
| `weapon_hit_metal` | sfx | -4.23 | -13.85 | -12.0 | - | 8 |
| `weapon_hit_chain` | sfx | -1.44 | -14.07 | -12.1 | - | 9 |
| `weapon_swing` | sfx | -4.10 | -18.10 | -17.3 | - | 7 |
| `throw` | sfx | -4.86 | -19.74 | -18.3 | - | 7 |
| `bottle_break` | sfx | -3.32 | -20.13 | -13.1 | - | 9 |
| `crate_break` | sfx | -2.36 | -15.31 | -12.1 | - | 9 |
| `metal_clang` | sfx | -8.18 | -14.84 | -13.0 | - | 9 |
| `tire_bounce` | sfx | -4.45 | -14.10 | -14.0 | - | 6 |
| `ui_move` | sfx | -2.84 | -16.43 | -22.1 | - | 4 |
| `ui_confirm` | sfx | -6.12 | -17.49 | -20.1 | - | 5 |
| `ui_cancel` | sfx | -9.43 | -16.00 | -21.0 | - | 5 |
| `ui_open` | sfx | -5.53 | -16.98 | -21.2 | - | 5 |
| `ui_close` | sfx | -6.07 | -17.21 | -21.2 | - | 5 |
| `door` | sfx | -1.67 | -17.83 | -15.9 | - | 11 |
| `dialogue_blip` | sfx | -7.16 | -14.82 | -24.0 | - | 5 |
| `quest_update` | sfx | -7.95 | -19.45 | -17.0 | - | 6 |
| `quest_complete` | sfx | -3.74 | -20.02 | -15.0 | - | 15 |
| `boss_intro` | sfx | -1.45 | -17.18 | -12.6 | - | 27 |
| `ko` | sfx | -1.28 | -15.12 | -12.5 | - | 11 |
| `dizzy` | sfx | -14.31 | -23.11 | -19.2 | - | 16 |
| `grab` | sfx | -1.27 | -16.91 | -17.4 | - | 6 |
| `slam` | sfx | -1.40 | -9.85 | -11.0 | - | 9 |
| `shockwave` | sfx | -3.72 | -13.50 | -12.0 | - | 13 |
| `whistle` | sfx | -13.19 | -20.87 | -17.2 | - | 12 |
| `crate_fall` | sfx | -2.29 | -15.98 | -14.0 | - | 10 |
| `alarm` | sfx | -13.83 | -17.80 | -17.0 | - | 26 |
| `dog_bark` | sfx | -8.39 | -17.26 | -15.0 | - | 8 |
| `splash` | sfx | -2.36 | -21.42 | -15.3 | - | 12 |
| `crowd_cheer` | sfx | -4.65 | -20.00 | -16.2 | - | 32 |
| `countdown_tick` | sfx | -1.45 | -17.03 | -20.6 | - | 5 |
| `bus_horn` | sfx | -11.39 | -16.95 | -16.1 | - | 13 |
| `save` | sfx | -9.02 | -20.39 | -17.0 | - | 10 |
| `guard_break` | sfx | -1.45 | -15.24 | -12.1 | - | 10 |
| `charge` | sfx | -5.60 | -18.71 | -16.1 | - | 15 |
| `rain_loop` | sfx | -15.28 | -29.26 | -26.2 | 0.27 | 105 |
| `street_loop` | sfx | -12.60 | -27.44 | -27.2 | 0.03 | 102 |
| `industrial_loop` | sfx | -9.07 | -24.15 | -25.1 | 0.20 | 102 |
| `neon_buzz_loop` | sfx | -16.08 | -27.98 | -28.0 | 1.94 | 68 |

Verification: all checks passed (format, channels, sample rate, whole-bar loop lengths, loop seams, peaks <= -1 dBFS, SFX length limits).
