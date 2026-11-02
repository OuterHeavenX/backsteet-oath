#!/usr/bin/env python3
"""Verify every item/UI/font asset exists with the contracted size and the JSON sidecars parse.

    python3 tools/art/verify_items_ui.py      (exit code 1 on any failure)
"""
import json
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
A = os.path.join(ROOT, 'game', 'assets')

from PIL import Image  # noqa: E402
import items_icons as I  # noqa: E402
import items_fx as F  # noqa: E402
import items_ui as U  # noqa: E402
import items_logo as LG  # noqa: E402

WEAPON_SIZES = {
    'wrench': (16, 7), 'baton': (18, 5), 'bat': (30, 6), 'pipe': (32, 5), 'broom': (40, 8),
    'chain': (40, 6), 'belt': (28, 5), 'newspaper': (18, 6), 'spatula': (18, 7), 'bottle': (12, 6),
    'brick': (10, 7), 'fish': (16, 8), 'tire': (18, 18), 'road_sign': (44, 14),
}

errors = []
count = 0


def check_png(path, size):
    global count
    count += 1
    if not os.path.exists(path):
        errors.append('missing ' + os.path.relpath(path, ROOT))
        return None
    im = Image.open(path)
    if im.mode != 'RGBA':
        errors.append('%s mode %s (want RGBA)' % (path, im.mode))
    if im.size != tuple(size):
        errors.append('%s size %s (want %s)' % (os.path.relpath(path, ROOT), im.size, tuple(size)))
    return im.convert('RGBA')


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        errors.append('json %s: %s' % (path, e))
        return {}


# fonts
for fn in ('oath_pixel.ttf', 'oath_big.ttf'):
    p = os.path.join(A, 'fonts', fn)
    count += 1
    if not os.path.exists(p):
        errors.append('missing font ' + fn)
    else:
        from fontTools.ttLib import TTFont
        f = TTFont(p)
        cmap = f.getBestCmap()
        need = [chr(c) for c in range(32, 127)]
        if fn == 'oath_pixel.ttf':
            need += list('éáóñü‘’“”–—…'
                         '×•©←↑→↓★♥')
        else:
            need += list('★♥’—…')
        miss = [ch for ch in need if ord(ch) not in cmap]
        if miss:
            errors.append('%s missing glyphs %r' % (fn, miss))

# weapons
wj = load_json(os.path.join(A, 'weapons', 'weapons.json'))
for wid, size in WEAPON_SIZES.items():
    im = check_png(os.path.join(A, 'weapons', wid + '.png'), size)
    e = wj.get(wid)
    if not e:
        errors.append('weapons.json missing ' + wid)
        continue
    if e.get('file') != 'res://assets/weapons/%s.png' % wid:
        errors.append('weapons.json bad file for ' + wid)
    for key in ('grip', 'tip'):
        x, y = e[key]
        if not (0 <= x < size[0] and 0 <= y < size[1]):
            errors.append('%s %s out of bounds' % (wid, key))
        elif im is not None and im.getpixel((x, y))[3] == 0:
            errors.append('%s %s on transparent pixel' % (wid, key))

# icons
for grp, ids in I.GROUPS:
    for iid in ids:
        check_png(os.path.join(A, 'icons', iid + '.png'), (16, 16))

# fx / pickups
for jname, spec, sub in [('fx', F.FX_SPEC, 'fx'), ('pickups', F.PICKUP_SPEC, 'pickups')]:
    data = load_json(os.path.join(A, sub, jname + '.json'))
    for k, (n, w, h) in spec.items():
        check_png(os.path.join(A, sub, k + '.png'), (w * n, h))
        e = data.get(k)
        if not e or e.get('frame') != [w, h] or e.get('frames') != n or \
                e.get('file') != 'res://assets/%s/%s.png' % (sub, k):
            errors.append('%s.json entry wrong for %s: %r' % (jname, k, e))

# ui
for uid, size in U.UI_SIZES.items():
    check_png(os.path.join(A, 'ui', uid + '.png'), size)
for uid, size in LG.LOGO_SIZES.items():
    check_png(os.path.join(A, 'ui', uid + '.png'), size)
pf = Image.open(os.path.join(A, 'ui', 'portrait_frame.png')).convert('RGBA')
import numpy as np  # noqa: E402
pa = np.array(pf)[..., 3]
if pa[3:67, 3:67].max() != 0:
    errors.append('portrait_frame window not fully transparent')
if pa[0:3, 3:-3].min() == 0 or pa[3:-3, 0:3].min() == 0:
    errors.append('portrait_frame border has holes')

print('checked %d assets' % count)
if errors:
    print('FAILURES:')
    for e in errors:
        print('  ' + e)
    sys.exit(1)
print('all OK')
