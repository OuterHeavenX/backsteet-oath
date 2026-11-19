#!/usr/bin/env python3
"""Markdown table from one or more harness outputs made with PERF_PAIRED (game/tests/perf.gd).

Each cell is the average frame time saved when the system is switched off, measured inside one run by alternating
on/off windows (mean of the pairs +/- standard error of the mean), in ms. A negative value means the frame got
slower with the system off (true for `fast_bloom`, where "off" is the 1.3.0-rc1 reference pass). With several
input files the cell lists each run.

Usage: python3 tools/perf/paired_table.py out1.json [out2.json ...]
"""
import json, sys

runs = [json.load(open(p)) for p in sys.argv[1:]]
scen, systems = [], []
for j in runs:
    for s in j["scenarios"]:
        if s["scenario"] not in scen:
            scen.append(s["scenario"])
        for k in s.get("paired", {}):
            if k not in systems:
                systems.append(k)
m = runs[0]["meta"]
print("Renderer `%s` (%s), window %sx%s, %s pairs of %ss windows per system.%s" % (
    m["adapter"], m["rendering_method"], m["window_px"][0], m["window_px"][1],
    next(iter(runs[0]["scenarios"][0].get("paired", {"x": {"pairs": "?"}}).values()))["pairs"],
    __import__("os").environ.get("PERF_PAIR_WINDOW", "0.6"),
    " **Software renderer: not GPU numbers.**" if m.get("software_renderer") else ""))
print()
print("| switched off | " + " | ".join(scen) + " |")
print("|---|" + "---|" * len(scen))


def cell(sys_name, sc):
    out = []
    for j in runs:
        for s in j["scenarios"]:
            if s["scenario"] == sc and sys_name in s.get("paired", {}):
                p = s["paired"][sys_name]
                out.append("%.1f ±%.1f" % (p["saved_ms"], p["sem_ms"]))
    return " / ".join(out) if out else "n/a"


def score(sys_name):
    best = -1e9
    for j in runs:
        for s in j["scenarios"]:
            if sys_name in s.get("paired", {}):
                best = max(best, s["paired"][sys_name]["saved_ms"])
    return best


for k in sorted(systems, key=lambda x: -score(x)):
    print("| `%s` | %s |" % (k, " | ".join(cell(k, sc) for sc in scen)))
