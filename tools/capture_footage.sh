#!/bin/bash
# Records the fixed gameplay clip used for before/after footage (Movie Maker, 30 fps, deterministic timing).
# Usage: tools/capture_footage.sh <out.mp4> [scenario]   scenario: kettle (default) | duke | diner | life_kettle | life_neon | life_canal
OUT=${1:-/tmp/footage.mp4}; SC=${2:-kettle}
TMP=$(mktemp -d)
FLAGS="intro_done,intro_seen,met_mara"
case "$SC" in
  kettle) ROOM=oq_kettle; STAGE=chain_dogs; SPAWN=west
    STEPS="wait:0.5;tp:420:290;spawn:dogs_brawler:90:-10;spawn:dogs_flanker:-70:14;hold:right;wait:0.5;release:right;press:punch;wait:0.15;press:punch;wait:0.15;press:punch;wait:0.5;press:kick;wait:0.2;press:kick;wait:0.6;hold:left;wait:0.4;release:left;press:punch;wait:0.15;press:punch;wait:0.15;press:kick;wait:0.8;press:jump;wait:0.2;press:kick;wait:0.8;weapon:pipe;press:punch;wait:0.3;press:punch;wait:0.6;hold:right;wait:1.2;release:right;press:punch;wait:0.2;press:punch;wait:1.5";;
  duke) ROOM=oq_chainlot; STAGE=chain_dogs; SPAWN=west; FLAGS="$FLAGS,duke_intro_seen"
    STEPS="wait:0.5;tp:700:290;boss:duke:110;wait:1.5;press:punch;wait:0.15;press:punch;wait:0.15;press:punch;wait:0.6;press:guard:0.6;press:kick;wait:0.3;press:kick;wait:0.8;press:jump;wait:0.2;press:kick;wait:1.0;press:punch;wait:0.15;press:punch;wait:0.15;press:kick;wait:2.0";;
  life_kettle) ROOM=oq_kettle; STAGE=chain_dogs; SPAWN=west
    STEPS="wait:1.0;tp:200:262;wait:3.0;hold:move_right;wait:7.5;release:move_right;wait:2.5";;
  life_neon) ROOM=nm_marquee; STAGE=neon; SPAWN=west; FLAGS="$FLAGS,boss_duke,boss_pikes,boss_otto"
    STEPS="wait:1.0;tp:260:300;wait:2.0;hold:move_right;wait:7.0;release:move_right;wait:2.0";;
  life_canal) ROOM=cm_canalwalk; STAGE=market; SPAWN=west; FLAGS="$FLAGS,boss_duke"
    STEPS="wait:1.0;tp:500:240;wait:2.0;hold:move_right;wait:6.0;release:move_right;wait:2.0";;
  diner) ROOM=int_diner; STAGE=chain_dogs; SPAWN=south
    STEPS="wait:0.5;hold:up;wait:0.6;release:up;hold:right;wait:1.0;release:right;wait:0.5;menu:shop:diner;wait:1.5;menu:close;wait:1.0";;
esac
cd "$(dirname "$0")/../game"
SHOTS_DIR=$TMP SHOT_ROOM=$ROOM SHOT_FLAGS=$FLAGS SHOT_STAGE=$STAGE SHOT_SPAWN=$SPAWN SHOT_STEPS="$STEPS" \
  timeout 400 xvfb-run -a -s "-screen 0 1280x720x24" godot --resolution 1280x720 --write-movie $TMP/clip.avi --fixed-fps 30 res://tests/shots.tscn > $TMP/log.txt 2>&1
ffmpeg -y -loglevel error -i $TMP/clip.avi -vf "scale=1280:720" -c:v libx264 -crf 24 -preset slow -pix_fmt yuv420p -an "$OUT"
grep "SCRIPT ERROR" $TMP/log.txt | head -5
rm -rf $TMP
ls -la "$OUT"
