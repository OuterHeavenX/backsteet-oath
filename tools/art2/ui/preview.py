#!/usr/bin/env python3
"""Contact sheets for self-review of the v2 UI/FX/item art (not shipped).

Usage: python3 tools/art2/ui/preview.py <fx|items|ui|icons|all> [outdir]
"""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vec import ASSETS  # noqa: E402

OUT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/ui_preview'
BGS = [(200, 120, 80), (28, 24, 48), (110, 118, 130)]


def sheet(items, name, zoom=2, width=1800, label=True):
    """items: list of (label, PIL image). Each drawn on the 3 backgrounds side by side."""
    rows = []
    x, y, rowh = 0, 0, 0
    placed = []
    for lab, im in items:
        w, h = im.size[0] * zoom, im.size[1] * zoom
        cw = w * 3 + 16
        if x + cw > width:
            x = 0
            y += rowh + 18
            rowh = 0
        placed.append((x, y, lab, im))
        x += cw + 12
        rowh = max(rowh, h)
    H = y + rowh + 20
    out = Image.new('RGB', (width, H), (60, 60, 66))
    d = ImageDraw.Draw(out)
    for x, y, lab, im in placed:
        big = im.resize((im.size[0] * zoom, im.size[1] * zoom), Image.NEAREST)
        for i, bg in enumerate(BGS):
            tile = Image.new('RGBA', big.size, bg + (255,))
            tile.alpha_composite(big)
            out.paste(tile.convert('RGB'), (x + i * (big.size[0] + 4), y + 12))
        if label:
            d.text((x, y), lab, fill=(240, 240, 240))
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + '.png')
    out.save(p)
    print(p, out.size)


def fx():
    meta = json.load(open(os.path.join(ASSETS, 'fx2', 'fx.json')))
    items = []
    for k, v in meta.items():
        if k.startswith('_'):
            continue
        items.append((f"{k} {v['count']}f", Image.open(os.path.join(ASSETS, 'fx2', v['file'])).convert('RGBA')))
    big = [it for it in items if it[1].size[0] > 400]
    small = [it for it in items if it[1].size[0] <= 400]
    sheet(small, 'fx_small', zoom=2)
    sheet(big, 'fx_big', zoom=1, width=2200)


def items():
    its = []
    for d in ('weapons2', 'pickups2'):
        for f in sorted(glob.glob(os.path.join(ASSETS, d, '*.png'))):
            its.append((os.path.basename(f)[:-4], Image.open(f).convert('RGBA')))
    sheet(its, 'items', zoom=3, width=1800)


def ui():
    its = []
    for f in sorted(glob.glob(os.path.join(ASSETS, 'ui2', '*.png'))):
        im = Image.open(f).convert('RGBA')
        if im.size[0] > 700 or im.size[1] > 400:
            continue
        its.append((os.path.basename(f)[:-4], im))
    sheet(its, 'ui', zoom=1, width=2000)


def icons():
    its = []
    for f in sorted(glob.glob(os.path.join(ASSETS, 'icons2', '*.png'))):
        its.append((os.path.basename(f)[:-4][:14], Image.open(f).convert('RGBA')))
    for i in range(0, len(its), 60):
        sheet(its[i:i + 60], f'icons_{i // 60}', zoom=2, width=1900)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for fn in (fx, items, ui, icons):
        if what in ('all', fn.__name__):
            fn()
