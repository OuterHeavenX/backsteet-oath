#!/bin/bash
# Usage: SHOT_ROOM=... SHOT_STEPS="wait:1;shot:x" tools/shots.sh <outdir>
OUT=${1:-/tmp/claude-0/shots}
mkdir -p "$OUT"
cd "$(dirname "$0")/../game"
SHOTS_DIR="$OUT" timeout ${SHOT_TIMEOUT:-90} xvfb-run -a -s "-screen 0 1280x720x24" godot --resolution 1280x720 res://tests/shots.tscn 2>&1 | grep -E "SCRIPT ERROR|ERROR:|shot " | grep -v "ALSA\|audio" | head -30
