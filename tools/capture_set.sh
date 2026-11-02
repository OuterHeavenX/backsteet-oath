#!/bin/bash
# Captures the fixed before/after comparison set. Usage: tools/capture_set.sh <outdir> [WxH]
OUT=${1:-/tmp/capture}; RES=${2:-1280x720}
mkdir -p "$OUT"
ALL="intro_done,intro_seen,met_mara,boss_duke,boss_pikes,act1_done,act2_started,rescued_gus,boss_otto,arcade_backroom,boss_jett,setback_fought,act3_started,alliance,met_price,boss_sabine,found_eli"
shot() { # name room flags stage steps [spawn]
  ( cd "$(dirname "$0")/../game" && SHOTS_DIR="$OUT" SHOT_ROOM=$2 SHOT_FLAGS=$3 SHOT_STAGE=$4 SHOT_SPAWN=${6:-west} SHOT_STEPS="$5" \
    timeout 120 xvfb-run -a -s "-screen 0 ${RES}x24" godot --resolution $RES res://tests/shots.tscn 2>&1 | grep -E "^shot $1|SCRIPT ERROR" )
}
shot c01_kettle_fight oq_kettle "intro_done,intro_seen,met_mara" chain_dogs "wait:1.2;tp:520:290;spawn:dogs_brawler:70:-10;spawn:dogs_flanker:-60:14;wait:1.4;press:punch;wait:0.12;press:punch;wait:0.12;press:punch;wait:0.1;shot:c01_kettle_fight"
shot c02_kettle_street oq_kettle "intro_done,intro_seen,met_mara" chain_dogs "wait:1.2;tp:300:300;wait:0.6;shot:c02_kettle_street"
shot c03_diner_shop int_diner "intro_done,met_mara" chain_dogs "wait:1.2;tp:380:300;wait:0.4;shot:c03a_diner;menu:shop:diner;wait:0.8;shot:c03_diner_shop" south
shot c04_duke oq_chainlot "intro_done,intro_seen,met_mara,duke_intro_seen" chain_dogs "wait:1.2;tp:760:290;boss:duke:110;wait:2.2;press:punch;wait:0.15;shot:c04_duke"
shot c05_canal cm_canalwalk "$ALL" pikes "wait:1.2;tp:950:286;spawn:rats_brawler:60:0;spawn:rats_thrower:150:20;wait:1.3;press:kick;wait:0.2;shot:c05_canal"
shot c06_foundry iy_foundry "$ALL" neon "wait:1.2;tp:760:290;boss:otto:90;wait:2;press:punch;wait:0.3;shot:c06_foundry"
shot c07_neon nm_marquee "$ALL" neon "wait:1.2;tp:820:280;spawn:saints_flanker:80:0;spawn:saints_brawler:-70:16;wait:1.2;press:jump;wait:0.18;press:kick;wait:0.12;shot:c07_neon"
shot c08_rain fr_pumpstation "$ALL" dockgate "wait:1.2;tp:700:290;spawn:grays_blocker:60:0;spawn:grays_heavy:-70:12;wait:1.5;press:punch;wait:0.15;shot:c08_rain"
shot c09_rook rw_floor "$ALL,rook_intro_seen" rook "wait:1.2;tp:420:290;boss:rook:100;wait:2.5;press:punch;wait:0.15;shot:c09_rook"
shot c10_status oq_kettle "intro_done,intro_seen,met_mara" chain_dogs "wait:1.2;menu:status;wait:0.6;shot:c10_status"
shot c11_dialogue int_garage "intro_done,intro_seen" find_mara "wait:2.8;shot:c11_dialogue" south
shot c12_arcade int_arcade "$ALL" neon "wait:1.5;shot:c12_arcade" south
ls "$OUT"
