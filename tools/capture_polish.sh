#!/bin/bash
# Fixed before/after capture set for the gameplay-polish pass (same inputs every run, 1280x720, software GL here).
# Usage: tools/capture_polish.sh <outdir> [stills|clips|all]
OUT=${1:?outdir}; WHAT=${2:-all}
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
mkdir -p "$OUT"
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="intro_done,intro_seen,met_mara"
shot() {  # name room stage flags steps
  local name=$1 room=$2 stage=$3 flags=$4 steps=$5 tmp
  tmp=$(mktemp -d)
  SHOT_ROOM=$room SHOT_STAGE=$stage SHOT_FLAGS=$flags SHOT_SPAWN=west SHOT_STEPS="$steps" "$HERE/shots.sh" "$tmp" > "$tmp/log.txt" 2>&1
  grep "SCRIPT ERROR" "$tmp/log.txt" | head -3
  for f in "$tmp"/s_*.png; do [ -f "$f" ] && mv "$f" "$OUT/${name}_$(basename "$f" | sed 's/^s_//')"; done
  rm -rf "$tmp"
}
if [ "$WHAT" != "clips" ]; then
  # 1. the opening fight outside the diner (cutscene already seen, so the fight starts straight away)
  shot intro oq_kettle intro "intro_seen" "wait:2.0;shot:s_a;hold:move_right;wait:1.6;release:move_right;wait:0.4;shot:s_b;press:punch;wait:0.15;press:punch;wait:0.15;press:punch;wait:0.25;shot:s_c"
  # 2. a street fight on Kettle Street
  shot kettle oq_kettle chain_dogs "$BASE" "wait:0.5;tp:420:290;spawn:dogs_brawler:90:-10;spawn:dogs_flanker:-70:14;spawn:dogs_weapon:130:20;wait:1.6;shot:s_a;press:punch;wait:0.15;press:punch;wait:0.15;press:punch;wait:0.2;shot:s_b"
  # 3. Duke's lieutenants in the Chain Lot (thrower + blocker + brawler)
  shot chainlot oq_chainlot chain_dogs "$BASE" "wait:0.5;tp:760:290;spawn:dogs_blocker:90:0;spawn:dogs_thrower:170:-20;spawn:dogs_brawler:120:30;wait:1.8;shot:s_a;wait:1.0;shot:s_b"
  # 4. Duke
  shot duke oq_chainlot chain_dogs "$BASE,duke_intro_seen" "wait:0.5;tp:700:290;boss:duke:110;wait:2.2;shot:s_a;wait:1.2;shot:s_b"
  # 5. the Kettle Street after Duke (quiet street)
  shot kettle_after oq_kettle market "$BASE,boss_duke" "wait:0.5;tp:520:290;wait:2.5;shot:s_a;tp:1100:290;wait:2.0;shot:s_b"
  # 6. a dark scene: Kowal's vault at half health
  shot kowal ul_vault underline "$BASE,kowal_intro_seen" "wait:0.5;tp:560:290;boss:kowal:110;wait:1.0;bosshp:0.45;wait:3.0;shot:s_a"
fi
if [ "$WHAT" != "stills" ]; then
  "$HERE/capture_footage.sh" "$OUT/clip_kettle.mp4" kettle
  "$HERE/capture_footage.sh" "$OUT/clip_duke.mp4" duke
fi
ls "$OUT"
