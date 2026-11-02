#!/bin/bash
# Runs the headless smoke scene and prints script errors (filters audio noise).
cd "$(dirname "$0")/../game"
timeout ${1:-40} godot --headless res://tests/smoke.tscn > /tmp/claude-0/smoke.log 2>&1
echo "exit=$?"
grep -v "ALSA\|alsa\|audio driver\|dummy driver\|^\s*$" /tmp/claude-0/smoke.log | grep -E -A1 "SCRIPT ERROR|ERROR|player pos|enemy state|SMOKE|world=|scripts checked" | grep -v "GDScript backtrace\|^--$" | head -${2:-40}
