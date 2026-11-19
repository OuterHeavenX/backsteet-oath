#!/usr/bin/env python3
"""Compares the frozen-frame captures written by game/tests/grade_ab.gd.

For every room it diffs each variant against the first one (the 1.3.0-rc1 reference pass) and reports, on the
0..255 scale: mean absolute difference, the 99th and 99.9th percentile and the maximum per-pixel difference
(largest channel), and the share of pixels that differ by more than 2 and by more than 8 levels. It also reports
how strong the bloom itself is in the reference (reference minus the no-grade frame is not meaningful because the
grade changes every pixel, so bloom strength is measured as |reference - variant| where the variant has no bloom).

Usage: python3 tools/perf/grade_diff.py <dir> [--amplify 8]   (writes <room>__diff_<variant>.png, amplified)
"""
import glob, os, re, sys
import numpy as np
from PIL import Image

d = sys.argv[1]
amp = float(sys.argv[sys.argv.index("--amplify") + 1]) if "--amplify" in sys.argv else 8.0
rooms = {}
for p in sorted(glob.glob(os.path.join(d, "*__*_*.png"))):
    m = re.match(r"(.+)__(\d+)_([a-z]+)\.png$", os.path.basename(p))
    if m:
        rooms.setdefault(m.group(1), []).append((int(m.group(2)), m.group(3), p))
print("%-22s %-10s %8s %6s %6s %5s %8s %8s" % ("frame", "variant", "mean|d|", "p99", "p99.9", "max", ">2 lvl", ">8 lvl"))
for room, vs in rooms.items():
    vs.sort()
    ref = np.asarray(Image.open(vs[0][2]).convert("RGB")).astype(np.int16)
    for i, name, p in vs[1:]:
        a = np.asarray(Image.open(p).convert("RGB")).astype(np.int16)
        diff = np.abs(a - ref).max(axis=2)
        print("%-22s %-10s %8.3f %6.0f %6.0f %5d %7.2f%% %7.2f%%" % (room, "%d_%s" % (i, name), np.abs(a - ref).mean(),
              np.percentile(diff, 99), np.percentile(diff, 99.9), diff.max(), 100.0 * (diff > 2).mean(), 100.0 * (diff > 8).mean()))
        out = np.clip(np.abs(a - ref) * amp, 0, 255).astype(np.uint8)
        Image.fromarray(out, "RGB").save(os.path.join(d, "%s__diff_%d_%s.png" % (room, i, name)))
