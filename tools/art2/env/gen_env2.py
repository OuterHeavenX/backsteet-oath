#!/usr/bin/env python3
"""BACKSTREET OATH -- environment generator v2 (density 2, layered, lit). Deterministic; Pillow + numpy only.

Outputs (see docs/visual/ASSET_CONTRACT_V2.md sections 2-3):
  game/assets/bg2/<room>/room.json, base_N.png, mid_N.png, fg_*.png, light.png
  game/assets/bg2/_district/<district>_{sky,far,mid}.png
  game/assets/props2/<type>.png + props.json

Usage:
  python3 tools/art2/env/gen_env2.py --rooms oq_kettle,int_diner,oq_chainlot [--preview DIR] [--no-props]
  python3 tools/art2/env/gen_env2.py --all
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from raster import Canvas, C, mix, shade, light, blur, rng_of, value_noise   # noqa: E402
import kit                                                                 # noqa: E402
from kit import M, MAJOR, DETAIL                                           # noqa: E402
import room as roommod                                                     # noqa: E402
from room import Room, H, FACADE_BOTTOM, CURB_Y                            # noqa: E402
import oq                                                                  # noqa: E402
import district                                                            # noqa: E402
import props2                                                              # noqa: E402
import common                                                              # noqa: E402
import grounds2                                                            # noqa: E402
import oq2, canal, interiors                                               # noqa: E402,F401
import fg2                                                                 # noqa: E402
for _mod in ('iron', 'neon', 'flood', 'ware', 'props3', 'under'):
    try:
        __import__(_mod)
    except ImportError:
        pass
FACADES = dict(oq.FACADES)
FACADES.update(common.FACADES)

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DATA = os.path.join(ROOT, 'game', 'data')
OUT_BG = os.path.join(ROOT, 'game', 'assets', 'bg2')
OUT_PROPS = os.path.join(ROOT, 'game', 'assets', 'props2')
V1_PROPS = os.path.join(ROOT, 'game', 'assets', 'props', 'props.json')
LEDGER = os.path.join(ROOT, 'docs', 'assets', 'ENVIRONMENTS_V2.md')
D = 2

GROUNDS = {
    **grounds2.GROUNDS2,
    'street': roommod.g_street,
    'lot': roommod.g_lot,
    'checker_floor': lambda R, x, w: roommod.g_checker(R, x, w, c1='#ded3c2', c2='#bdb0b0'),
}

# Static props get a baked long dusk shadow on the ground (movable/breakable ones do not).
STATIC_SHADOW = {'lamp_post': (3, 78), 'bus_stop': (50, 60), 'mailbox': (14, 26), 'bench': (38, 14),
                 'hydrant': (10, 20), 'newsbox': (12, 24), 'car_wreck': (90, 30), 'floodlight': (4, 84),
                 'market_stall_fish': (70, 50), 'market_stall_fruit': (70, 50), 'phone_booth': (22, 60),
                 'mooring_post': (8, 16), 'planter': (24, 20), 'guard_booth': (38, 56), 'pipe_stack': (56, 28)}

DISTRICT_LAYERS = {d: [('sky', 0.05, 0), ('far', 0.25, 0), ('mid', 0.5, 0)]
                   for d in ('old_quarter', 'canal_market', 'ironworks', 'neon_mile', 'floodgate', 'warehouse')}

# Exterior look per district: dusk/afternoon/night grade ramps, lightmap ambient, rim light, cast shadow.
DCONF = {
    'old_quarter': dict(grade={}, ambient=('#fff0e0', 0.86), rim={"color": "#ffb070", "dir": [1.0, 0.25], "strength": 0.45},
                        cast={"dir": [0.6, 0.22], "alpha": 0.22}),
    'canal_market': dict(grade=dict(top=(1.06, 1.0, 0.88), mid=(1.0, 0.97, 0.9), base=(0.86, 0.88, 0.92),
                                    ground_far=(1.0, 0.98, 0.94), ground_near=(0.92, 0.92, 0.95)),
                         ambient=('#fff6e4', 0.94), rim={"color": "#ffe0a0", "dir": [1.0, 0.3], "strength": 0.4},
                         cast={"dir": [0.5, 0.2], "alpha": 0.24}),
    'ironworks': dict(grade=dict(top=(0.9, 0.95, 1.04), mid=(0.86, 0.9, 1.0), base=(0.7, 0.75, 0.88),
                                 ground_far=(0.9, 0.9, 0.96), ground_near=(0.8, 0.82, 0.92)),
                      ambient=('#d8e0f0', 0.84), rim={"color": "#ff9a50", "dir": [-1.0, 0.2], "strength": 0.5},
                      cast={"dir": [-0.5, 0.2], "alpha": 0.12}),
    'neon_mile': dict(grade=dict(top=(0.6, 0.58, 0.82), mid=(0.56, 0.54, 0.78), base=(0.5, 0.48, 0.72),
                                 ground_far=(0.74, 0.7, 0.86), ground_near=(0.64, 0.6, 0.8)),
                      ambient=('#b8a8e8', 0.76), rim={"color": "#ff5ab0", "dir": [0.6, 0.6], "strength": 0.55},
                      cast={"dir": [0.0, 0.3], "alpha": 0.06}),
    'floodgate': dict(grade=dict(top=(0.74, 0.84, 0.88), mid=(0.7, 0.8, 0.84), base=(0.6, 0.7, 0.76),
                                 ground_far=(0.76, 0.84, 0.88), ground_near=(0.66, 0.74, 0.8)),
                      ambient=('#c8e0e4', 0.8), rim={"color": "#a8e8f0", "dir": [0.3, 1.0], "strength": 0.4},
                      cast={"dir": [0.0, 0.2], "alpha": 0.0}),
    'underline': dict(grade=dict(top=(0.74, 0.84, 0.8), mid=(0.72, 0.82, 0.78), base=(0.66, 0.76, 0.72),
                                 ground_far=(0.8, 0.88, 0.84), ground_near=(0.7, 0.78, 0.76)),
                      ambient=('#c8e0d4', 0.82), rim={"color": "#ffc070", "dir": [0.3, 0.9], "strength": 0.45},
                      cast={"dir": [0.0, 0.2], "alpha": 0.0}),
    'warehouse': dict(grade=dict(top=(0.78, 0.88, 0.84), mid=(0.74, 0.84, 0.8), base=(0.64, 0.74, 0.7),
                                 ground_far=(0.8, 0.88, 0.84), ground_near=(0.7, 0.78, 0.76)),
                      ambient=('#d0f0e0', 0.84), rim={"color": "#c8ffe0", "dir": [0.2, 1.0], "strength": 0.4},
                      cast={"dir": [0.0, 0.2], "alpha": 0.0}),
}
# Interior grade (top, bottom) + ambient per room.
ICONF = {
    'int_diner': ((1.02, 0.97, 0.92), (0.86, 0.82, 0.86), '#fff0e4', 0.9),
    'int_garage': ((1.0, 0.98, 0.94), (0.84, 0.82, 0.84), '#fff4e8', 0.88),
    'int_rec': ((1.02, 0.96, 0.9), (0.86, 0.82, 0.84), '#fff0e0', 0.9),
    'int_noodle': ((1.04, 0.96, 0.86), (0.86, 0.8, 0.8), '#ffe8d0', 0.9),
    'int_books': ((1.0, 0.96, 0.88), (0.82, 0.78, 0.78), '#fff0d8', 0.86),
    'int_canteen': ((0.96, 1.0, 0.98), (0.8, 0.84, 0.84), '#e8fff4', 0.9),
    'int_switch': ((0.92, 0.98, 1.04), (0.76, 0.8, 0.88), '#e0f0ff', 0.86),
    'int_arcade': ((0.9, 0.86, 1.0), (0.66, 0.6, 0.8), '#d0b8ff', 0.74),
    'int_pharmacy': ((1.0, 1.02, 1.02), (0.86, 0.9, 0.92), '#f0ffff', 0.94),
    'int_bait': ((0.9, 0.96, 0.96), (0.72, 0.78, 0.8), '#d8eef0', 0.82),
}


def load():
    rooms = json.load(open(os.path.join(DATA, 'rooms.json')))['rooms']
    if isinstance(rooms, list):
        rooms = {r['id']: r for r in rooms}
    enc = json.load(open(os.path.join(DATA, 'encounters.json')))
    enc = enc.get('rooms', enc)
    return rooms, enc


# ----------------------------------------------------------------------------- room extras
def prop_shadow(R, p, meta):
    t = p['type']
    if t not in STATIC_SHADOW or R.interior:
        return
    w, h = STATIC_SHADOW[t]
    dx, dy = R.cast_shadow['dir']
    x, y = p['x'], p['y']
    L = h * 0.75
    if R.cast_shadow.get('alpha', 0) <= 0.01:
        return
    lx0 = min(x - w, x - w + L * dx)
    lx1 = max(x + w, x + w + L * dx) + 20
    lay = R.cv.layer(lx0, y - 10, lx1 - lx0, 24 + abs(L * dy))
    tipw = w * (0.35 if t == 'lamp_post' else 0.8)
    lay.fill_poly([(x - w / 2, y), (x + w / 2, y), (x + tipw / 2 + L * dx, y + L * dy),
                   (x - tipw / 2 + L * dx, y + L * dy)], C('#000000'))
    if t == 'lamp_post':
        lay.ellipse(x + L * dx, y + L * dy, 4, 1.6, C('#000000'))
    m = blur(lay.px[..., 3], 1.2 * D, passes=2)
    R.cv.paint((lay.ox, lay.oy, m), C('#1a1030'), a=R.cast_shadow['alpha'] * 1.3, mode='atop')


def lamp_lights(R):
    for p in R.data.get('props', []):
        if p['type'] in LIGHT_PROPS:
            dx, hy_off, r, col, en, fl, pool = LIGHT_PROPS[p['type']]
            x, y = p['x'], p['y']
            hx, hy = x + dx, y - hy_off
            R.glow(hx, hy, r, col, en, fl)
            R.glow(hx, hy + 30, r * 1.35, col, 0.12, 'none', front=True)
            roommod.light_pool(R, x + 2, y + 8, 34, 11, pool, a=0.22)
            R.light(x, y + 14, 60, 42, pool, 0.2)


def extras_oq_kettle(R):
    rs = R.rng('kettle')
    roommod.crosswalk(R, 846, 64)
    roommod.road_text(R, 'BUS STOP', 170, 262, 10)
    roommod.painted_curb(R, 700, 40)
    roommod.manhole(R, 745, 300)
    roommod.manhole(R, 1330, 318)
    R.ambient.append({"type": "steam", "x": 745.0, "y": 298.0, "rate": 0.7})
    roommod.puddle(R, 560, 322, 22, 4.5)
    roommod.puddle(R, 1180, 288, 16, 3.2)
    roommod.puddle(R, 210, 334, 14, 3)
    R.ambient.append({"type": "paper", "x": 900.0, "y": 300.0, "w": 400})
    R.ambient.append({"type": "pigeons", "x": 120.0, "y": 50.0, "w": 80})


def extras_oq_chainlot(R):
    roommod.puddle(R, 470, 300, 26, 5)
    roommod.puddle(R, 1180, 330, 18, 3.5)
    roommod.puddle(R, 830, 262, 12, 2.6)
    R.ambient.append({"type": "paper", "x": 720.0, "y": 290.0, "w": 500})
    R.ambient.append({"type": "leaves", "x": 500.0, "y": 240.0, "w": 400})


def extras_int_diner(R):
    south = R.data.get('exits', {}).get('south')
    if south:
        oq.doormat(R, south['x0'], south['x1'])
    # polished floor: faint reflections of the wall lights
    for lx in (300, 380, 460):
        R.cv.radial(lx, 214, 9, 22, C('#fff0c0'), a=0.10, mode='add', falloff=1.5)
    R.reflect.append({"rect": [0, 200, 640, 160], "alpha": 0.12})


SELF_DOORS = {'diner', 'alley_gap'}

LIGHT_PROPS = {   # type: (dx, head offset from the ground y, glow r, colour, energy, flicker, pool colour)
    'lamp_post': (0, 71, 34, '#ffd27a', 0.6, 'none', '#ffc878'),
    'lamp_sodium': (10, 84, 38, '#ffb050', 0.65, 'none', '#ffa848'),
    'floodlight': (0, 84, 44, '#e8f4ff', 0.6, 'fluor', '#d8ecff'),
    'neon_post': (0, 70, 26, '#ff4ab0', 0.5, 'neon', '#ff70c0'),
}


def drawbridge_layers(R, d):
    """cm_pier: bascule leaf raised until boss_pikes, lowered after (spacer tiles position the leaf)."""
    px, py, x_end = R.drawbridge
    x0 = int(px - 20)
    out = []
    for state in ('up', 'down'):
        cv = Canvas(x_end - x0, FACADE_BOTTOM, D, x0, 0)
        leaf = M(C('#3e4a56'))
        L = x_end - px + 10
        ang = math.radians(64 if state == 'up' else 0)
        tip = (px + math.cos(ang) * L, py - math.sin(ang) * L)
        nrm = (-math.sin(ang), -math.cos(ang))
        th = 12
        poly = [(px, py), tip, (tip[0] + nrm[0] * th, tip[1] + nrm[1] * th), (px + nrm[0] * th, py + nrm[1] * th)]
        cv.fill_poly(poly, leaf.b, ink=leaf.i, iw=MAJOR)
        n = 14
        for k in range(n + 1):
            t = k / n
            a = (px + (tip[0] - px) * t, py + (tip[1] - py) * t)
            b = (a[0] + nrm[0] * th, a[1] + nrm[1] * th)
            cv.line([a, b], 0.8, leaf.l)
            if k < n:
                t2 = (k + 1) / n
                c2 = (px + (tip[0] - px) * t2 + nrm[0] * th, py + (tip[1] - py) * t2 + nrm[1] * th)
                cv.line([a, c2], 0.6, leaf.l)
        cv.line([(px, py), tip], 0.8, C('#ffe0a0'), a=0.6)
        cv.ellipse(px, py, 6, 6, C('#5a5c66'), ink=C('#1a1420'), iw=MAJOR)
        if state == 'down':
            sx = x_end - 29
            cv.ellipse(sx, 123, 2.4, 2.4, C('#3a2a2a'))
            cv.ellipse(sx, 132, 2.4, 2.4, C('#3aff6a'), em=1.0)
            cv.rect(px, py - 14, L, 1.2, leaf.b)
            for k in range(int(L / 10)):
                cv.rect(px + k * 10, py - 14, 0.8, 8, leaf.b)
        im = cv.to_image()
        fn = f'bridge_{state}.png'
        im.save(os.path.join(d, fn), optimize=True)
        files = []
        left = x0 * D
        while left > 0:
            sw = min(2048, left)
            sp = f'spacer_{sw}.png'
            if not os.path.exists(os.path.join(d, sp)):
                Image.new('RGBA', (sw, 1), (0, 0, 0, 0)).save(os.path.join(d, sp))
            files.append(sp)
            left -= sw
        files.append(fn)
        e = {"name": f'bridge_{state}', "files": files, "parallax": 1.0, "y": 0, "repeat": False}
        if state == 'up':
            e["unless"] = "boss_pikes"
        else:
            e["requires"] = "boss_pikes"
        out.append(e)
    return out


def exterior_south(R, x0, x1):
    """South exit on an exterior (e.g. the back alley): a gap in the near curb with light spilling in."""
    cv = R.cv
    cv.rect(x0, CURB_Y, x1 - x0, H - CURB_Y, C('#2a2430'))
    cv.radial((x0 + x1) / 2, H, (x1 - x0) * 0.7, 20, C('#ff8ad0'), a=0.25, mode='add')


EXTRAS = {'oq_kettle': extras_oq_kettle, 'oq_chainlot': extras_oq_chainlot, 'int_diner': extras_int_diner}


# ----------------------------------------------------------------------------- foreground sprites
def fg_car(seed=0, col='#3a2a44'):
    w, h = 168, 58
    cv = Canvas(w, h, D)
    m = M(C(col))
    lay = cv.layer()
    # rear three-quarter: trunk, rear window, roof (top 26 u visible in game)
    lay.fill_poly([(4, h), (6, 30), (24, 22), (46, 8), (118, 6), (140, 20), (162, 28), (166, h)], m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.vgrad(4, 6, 162, h - 6, [m.l, m.b, m.s, m.d], mode='atop')
    cv.fill_poly([(50, 11), (114, 9.5), (132, 22), (34, 24)], C('#2a2440'), ink=m.d, iw=DETAIL)
    cv.fill_poly([(60, 11), (78, 10.5), (64, 22), (46, 23)], C('#ffb890'), a=0.35, mode='atop')
    cv.rect(10, 30, 150, 1.2, m.h, a=0.6)
    cv.rect(10, 34, 14, 4, C('#c83a3a'), ink=m.d, iw=DETAIL)
    cv.rect(146, 34, 14, 4, C('#c83a3a'), ink=m.d, iw=DETAIL)
    # warm rim from the dusk sky on top edges
    cv.line([(46, 8), (118, 6)], 1.0, C('#ffb890'), a=0.7)
    cv.line([(6, 30), (24, 22), (46, 8)], 0.8, C('#ffb890'), a=0.5)
    return cv


def fg_meter():
    w, h = 12, 70
    cv = Canvas(w, h, D)
    m = M(C('#3a3a46'))
    lay = cv.layer()
    lay.rect(5, 18, 2.4, h - 18, m.b)
    lay.fill_poly([(1.5, 18), (10.5, 18), (11, 6), (9, 2), (3, 2), (1, 6)], m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.hgrad(1, 2, 10, 16, [m.l, m.b, m.s], mode='atop')
    cv.fill_poly([(3, 6), (9, 6), (8.6, 10), (3.4, 10)], C('#d8e0e8'), ink=m.d, iw=DETAIL)
    cv.rect(5.2, 7, 2.4, 2, C('#c83a3a'))
    cv.rect(1, 2, 10, 0.8, C('#ffb890'), a=0.6)
    cv.rect(5, 18, 0.8, h - 18, C('#ffb890'), a=0.35)
    return cv


def fg_signal_cables():
    w, h = 260, 72
    cv = Canvas(w, h, D)
    kit.cable(cv, -5, 6, w + 5, 10, sag=18, w=0.8, col='#140e18')
    kit.cable(cv, -5, 2, w + 5, 4, sag=10, w=0.6, col='#140e18')
    # hanging traffic signal
    sx = w * 0.52
    sy = 6 + 4 + 18 * 4 * 0.52 * 0.48
    cv.rect(sx - 0.5, sy - 2, 1, 6, C('#140e18'))
    m = M(C('#c8a030'))
    cv.rect(sx - 5, sy + 4, 10, 28, m.b, ink=m.i, iw=MAJOR)
    cv.hgrad(sx - 5, sy + 4, 10, 28, [m.l, m.b, m.s], mode='atop')
    for k, c in enumerate(('#5a1a1a', '#ffb43a', '#1a3a2a')):
        cv.ellipse(sx, sy + 9 + k * 9, 3.2, 3.2, C('#1a1420'))
        cv.ellipse(sx, sy + 9 + k * 9, 2.6, 2.6, C(c))
        cv.fill_poly([(sx - 4, sy + 6 + k * 9), (sx + 4, sy + 6 + k * 9), (sx + 4.5, sy + 8 + k * 9), (sx - 4.5, sy + 8 + k * 9)],
                     m.d)
    cv.radial(sx, sy + 18, 8, 8, C('#ffb43a'), a=0.5, mode='addfree')
    return cv


def fg_rubble():
    w, h = 96, 44
    cv = Canvas(w, h, D)
    m = M(C('#6e6860'))
    lay = cv.layer()
    lay.fill_poly([(2, h), (6, 18), (20, 12), (52, 10), (60, 4), (72, 8), (84, 20), (94, h)], m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.vgrad(2, 4, 92, h - 4, [m.l, m.b, m.s, m.d], mode='atop')
    for k in range(4):
        x = 30 + k * 12
        cv.line([(x, 12), (x + 4, -2 + k * 2)], 0.8, C('#5a3a2a'))
    cv.line([(6, 18), (20, 12), (52, 10)], 0.8, C('#ffb890'), a=0.5)
    for k in range(6):
        roommod.weeds(type('R', (), {'cv': cv})(), 8 + k * 14, h - 1, 4, seed=500 + k)
    return cv


def fg_fence_end():
    w, h = 64, 60
    cv = Canvas(w, h, D)
    post = M(C('#4a4a54'))
    lay = cv.layer()
    mk = lay.rect_mask(8, 6, 50, h - 6)
    x_0, y_0, mm = mk
    hh, ww = mm.shape
    X = (np.arange(ww) + x_0 + 0.5) / D
    Y = (np.arange(hh) + y_0 + 0.5) / D
    XX, YY = np.meshgrid(X, Y)
    p = 5.0
    d1 = np.abs(((XX + YY) % p) - p / 2)
    d2 = np.abs(((XX - YY) % p) - p / 2)
    a1 = np.clip((d1 - (p / 2 - 0.45)) / 0.45, 0, 1)
    a2 = np.clip((d2 - (p / 2 - 0.45)) / 0.45, 0, 1)
    lay.paint((x_0, y_0, np.maximum(a1, a2) * mm), C('#5a5a68'))
    lay.rect(6, 2, 3.5, h - 2, post.b)
    lay.rect(6, 6, 54, 1.6, post.b)
    cv.merge(lay, ink=C('#0e0a14'), iw=DETAIL)
    cv.rect(6, 2, 1, h - 2, C('#ffb890'), a=0.45)
    return cv


def fg_wires():
    w, h = 340, 60
    cv = Canvas(w, h, D)
    for k in range(4):
        kit.cable(cv, -5, 4 + k * 5, w + 5, 2 + k * 6, sag=16 + k * 5, w=0.6, col='#140e18')
    # shoe pair hanging on a wire
    sx = w * 0.4
    sy = 2 + 2 * 6 + (16 + 10) * 4 * 0.4 * 0.6
    cv.line([(sx, sy - 2), (sx - 2, sy + 6)], 0.4, C('#d8d0c0'))
    cv.line([(sx, sy - 2), (sx + 2, sy + 7)], 0.4, C('#d8d0c0'))
    for dx, dy in ((-2, 6), (2, 7)):
        cv.fill_poly([(sx + dx - 2, sy + dy), (sx + dx + 2.5, sy + dy), (sx + dx + 2.5, sy + dy + 4), (sx + dx - 1.5, sy + dy + 4.5)],
                     C('#e8e4dc'), ink=C('#1a1220'), iw=DETAIL)
    return cv


def fg_pendant():
    w, h = 44, 56
    cv = Canvas(w, h, D)
    cv.rect(w / 2 - 0.5, 0, 1, 34, C('#140e18'))
    m = M(C('#8a1e2a'))
    cv.fill_poly([(w / 2 - 18, 52), (w / 2 + 18, 52), (w / 2 + 7, 34), (w / 2 - 7, 34)], m.b, ink=m.i, iw=MAJOR)
    cv.vgrad(w / 2 - 18, 34, 36, 18, [m.l, m.b, m.d], mode='atop')
    cv.ellipse(w / 2, 52.5, 16, 2.5, C('#fff0c0'))
    cv.radial(w / 2, 54, 14, 3, C('#ffffff'), a=0.6, mode='addfree')
    return cv


def fg_plant():
    w, h = 54, 80
    cv = Canvas(w, h, D)
    pot = M(C('#c87a4a'))
    cv.fill_poly([(14, h), (40, h), (43, h - 18), (11, h - 18)], pot.b, ink=pot.i, iw=MAJOR)
    cv.hgrad(11, h - 18, 32, 18, [pot.l, pot.b, pot.s], mode='atop')
    rs = rng_of('plant')
    leaf = M(C('#3a7a4a'))
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.32 + rs.uniform(-0.1, 0.1)
        L = rs.uniform(38, 60)
        bx, by = 27, h - 18
        tx, ty = bx + math.cos(a) * L, by + math.sin(a) * L
        mx, my = bx + math.cos(a) * L * 0.5 + rs.uniform(-6, 6), by + math.sin(a) * L * 0.5
        cv.fill_poly([(bx, by), (mx - 5, my), (tx, ty), (mx + 5, my)], leaf.b if k % 2 else leaf.s,
                     ink=leaf.i, iw=DETAIL)
        cv.line([(bx, by), (mx, my), (tx, ty)], 0.4, leaf.l, a=0.8)
    return cv


FG = {
    'oq_kettle': [('fg_car', fg_car, [(390, 384), (1240, 384)], 1.25, True),
                  ('fg_meter', fg_meter, [(770, 380), (1530, 380)], 1.3, True),
                  ('fg_signal', fg_signal_cables, [(980, 70)], 1.12, False)],
    'oq_chainlot': [('fg_rubble', fg_rubble, [(560, 382)], 1.25, True),
                    ('fg_fence_end', fg_fence_end, [(40, 384), (1180, 384)], 1.3, True),
                    ('fg_wires', fg_wires, [(720, 58)], 1.1, False)],
    'ul_vault': [('fg_lamps', lambda: __import__('under').fg_lamp_cluster(), [(560, 110)], 1.12, False),
                 ('fg_pillar', lambda: __import__('under').fg_pillar_stub(), [(260, 384), (860, 384)], 1.28, True),
                 ('fg_cables', fg2.fg_cables, [(300, 56), (900, 56)], 1.1, False)],
    'int_diner': [('fg_pendant', fg_pendant, [(150, 52), (520, 52)], 1.15, False),
                  ('fg_plant', fg_plant, [(612, 384)], 1.2, True)],
}


# ----------------------------------------------------------------------------- room-specific mid layers
def mid_chainlot():
    """Distant vacant lot / rail embankment seen through the fence (parallax 0.6, y = 80 u)."""
    TU = 1024
    cv = Canvas(TU, 142, D)
    base = 142           # bottom = y 222 world
    rs = rng_of('mid_chainlot')
    P = district.DIST['old_quarter']
    # warehouses + gas holder silhouettes
    col = C('#6a4466')
    for i in range(10):
        x = i * 104 + rs.uniform(-10, 10)
        w = rs.uniform(60, 100)
        h = rs.uniform(30, 70)
        def one(xx, w=w, h=h, s=i):
            r2 = rng_of('mw', s)
            cv.fill_poly([(xx, base - 30), (xx, base - 30 - h), (xx + w * 0.5, base - 30 - h - 10), (xx + w, base - 30 - h),
                          (xx + w, base - 30)], col, ink=shade(col, 1.2), iw=0.5)
            cv.rect(xx, base - 30 - h, w, 0.8, C(P['rim']), a=0.5)
            for k in range(int(w / 9)):
                if r2.random() < 0.3:
                    cv.rect(xx + 3 + k * 9, base - 30 - h * 0.5, 3, 2.5, C('#ffcf80'), a=0.9)
        district._wrap_draw(one, x)
    # rail embankment with a freight car
    emb = C('#5a3e56')
    cv.fill_poly([(-5, base - 22), (TU + 5, base - 22), (TU + 5, base - 34), (-5, base - 34)], emb)
    cv.rect(-5, base - 35, TU + 10, 1.2, C('#3a2a3a'))
    cv.rect(-5, base - 36.5, TU + 10, 0.6, C('#c8a0a0'), a=0.6)

    def car(xx):
        cv.rect(xx, base - 52, 70, 16, C('#7a4a4a'), ink=C('#3a1e2a'), iw=0.5)
        for k in range(1, 7):
            cv.rect(xx + k * 10, base - 52, 0.6, 16, C('#5a3438'))
        cv.rect(xx, base - 52, 70, 0.8, C(P['rim']), a=0.6)
        cv.ellipse(xx + 10, base - 35.5, 3, 1.6, C('#2a1a2a'))
        cv.ellipse(xx + 60, base - 35.5, 3, 1.6, C('#2a1a2a'))
    district._wrap_draw(car, 380)
    # telephone poles + wires
    for i in range(5):
        px = 60 + i * 205

        def pole(xx):
            cv.rect(xx, base - 100, 2, 100, C('#3a2a34'))
            cv.rect(xx - 7, base - 94, 16, 1.4, C('#3a2a34'))
        district._wrap_draw(pole, px)
    for k in range(3):
        pts = []
        for j in range(129):
            u = j / 128 * TU
            seg = (u - 60) % 205 / 205
            pts.append((u, base - 93 + k * 1.8 + 7 * 4 * seg * (1 - seg)))
        cv.line(pts, 0.4, C('#2a1e2a'), a=0.8)
    # billboard (faded ad for luxury lofts -- the developer's pitch)

    def board(xx):
        cv.rect(xx + 12, base - 60, 2.5, 60, C('#3a2a34'))
        cv.rect(xx + 76, base - 60, 2.5, 60, C('#3a2a34'))
        cv.rect(xx, base - 104, 92, 44, C('#e8dcc4'), ink=C('#2a1e2a'), iw=0.8)
        cv.vgrad(xx + 2, base - 102, 88, 40, [C('#c8a0b0'), C('#e8c8a8')])
        cv.text('RIVERVIEW', 'sign', 7, xx + 46, base - 90, C('#4a3a6a'), 'mm')
        cv.text('LOFTS', 'sign', 9, xx + 46, base - 78, C('#c83a5a'), 'mm')
        cv.text('COMING SOON', 'cond', 4, xx + 46, base - 68, C('#4a3a6a'), 'mm')
        kit.weather(cv, xx, base - 104, 92, 44, 5, soot=0.2, blotch=0.3)
        cv.rect(xx, base - 104, 92, 1, C(P['rim']), a=0.6)
    district._wrap_draw(board, 560)
    # distant lot ground strip with a far fence line
    g = C('#7a6266')
    cv.vgrad(0, base - 22, TU, 22, [mix(g, C(P['haze']), 0.4), g])
    for k in range(60):
        x = k * TU / 60
        cv.rect(x, base - 30, 0.5, 8, C('#4a3a48'), a=0.7)
    cv.rect(0, base - 30, TU, 0.5, C('#4a3a48'), a=0.7)
    cv.vgrad(0, base - 60, TU, 60, [C(P['haze'], 0), C(P['haze'], 70)], mode='atop')
    return cv


ROOM_MID = {'oq_chainlot': [('mid', mid_chainlot, 0.6, 80)]}
ROOM_DISTRICT_LAYERS = {'oq_chainlot': ['sky', 'far'], 'cm_pier': ['sky', 'far'], 'iy_foundry': [],
                        'rw_storage': [], 'rw_office': [], 'rw_floor': [], 'nm_backalley': [],
                        'ul_station': [], 'ul_tunnel': [], 'ul_vault': []}


# ----------------------------------------------------------------------------- build
def build_room(rid, rooms, enc, props_meta):
    data = rooms[rid]
    R = Room(rid, data, enc.get(rid, {}), D)
    if R.interior:
        ic = ICONF.get(rid, ((1.0, 0.97, 0.92), (0.86, 0.82, 0.86), '#fff0e4', 0.9))
        R.rim = {"color": "#ffd8a8", "dir": [0.3, 1.0], "strength": 0.3}
        R.ambient_color = ic[2]
        R.ambient_level = ic[3]
    else:
        dc = DCONF.get(R.district, DCONF['old_quarter'])
        R.ambient_color, R.ambient_level = dc['ambient']
        R.rim = dict(dc['rim'])
        R.cast_shadow = dict(dc['cast'])
    t0 = time.time()
    for g in data.get('ground', []):
        fn = GROUNDS.get(g['style'])
        if fn is None:
            raise SystemExit(f'[{rid}] ground style {g["style"]} not implemented in v2 yet')
        fn(R, g['x'], g['w'])
    if not R.interior:
        for p in data.get('props', []):
            prop_shadow(R, p, props_meta.get(p['type'], {}))
    for f in data.get('facades', []):
        fn = FACADES.get(f['kind'])
        if fn is None:
            raise SystemExit(f'[{rid}] facade kind {f["kind"]} not implemented in v2 yet')
        R.cv.clipx = (int(f['x'] * D), int((f['x'] + f['w']) * D))
        fn(R, f['x'], f['w'], f)
        R.cv.clipx = None
    for d in data.get('doors', []):
        if d['id'] not in R.drawn_doors and not any(f['x'] <= d['x'] < f['x'] + f['w'] and f['kind'] in SELF_DOORS
                                                    for f in data.get('facades', [])):
            common.generic_entrance(R, d)
    if rid in EXTRAS:
        EXTRAS[rid](R)
    elif R.interior and data.get('exits', {}).get('south'):
        s = data['exits']['south']
        oq.doormat(R, s['x0'], s['x1'])
    elif data.get('exits', {}).get('south'):
        s = data['exits']['south']
        exterior_south(R, s['x0'], s['x1'])
    if R.interior:
        ic = ICONF.get(rid, ((1.0, 0.97, 0.92), (0.86, 0.82, 0.86)))
        roommod.grade_interior(R, ic[0], ic[1])
    else:
        roommod.grade_exterior(R, **DCONF.get(R.district, DCONF['old_quarter'])['grade'])
        lamp_lights(R)
    img = R.cv.to_image(opaque=R.interior)
    print(f'  {rid}: drawn in {time.time() - t0:.1f}s')
    return R, img


def write_room(R, img, out_root):
    d = os.path.join(out_root, R.id)
    os.makedirs(d, exist_ok=True)
    for fn in os.listdir(d):
        if fn.endswith('.png'):
            os.remove(os.path.join(d, fn))
    base_files = roommod.save_tiles(img, d, 'base')
    layers = []
    if not R.interior:
        only = ROOM_DISTRICT_LAYERS.get(R.id)
        for name, par, y in DISTRICT_LAYERS.get(R.district, []):
            if only is not None and name not in only:
                continue
            layers.append({"name": name, "files": [f'../_district/{R.district}_{name}.png'], "parallax": par,
                           "y": y, "repeat": True})
    for name, fn, par, y in ROOM_MID.get(R.id, []):
        cv = fn()
        files = roommod.save_tiles(cv.to_image(), d, name)
        layers.append({"name": f'room_{name}', "files": files, "parallax": par, "y": y, "repeat": True})
    layers.append({"name": "base", "files": base_files, "parallax": 1.0, "y": 0, "repeat": False})
    fg = []
    if R.id in FG:
        for name, fn, places, par, fade in FG[R.id]:
            cv = fn()
            cv.to_image().save(os.path.join(d, f'{name}.png'), optimize=True)
            for (x, y) in places:
                fg.append({"file": f'{name}.png', "x": x, "y": y, "parallax": par, "fade": fade})
    else:
        south = R.data.get('exits', {}).get('south')
        spec = None
        if R.id == 'rw_office':
            spec = [('fg_tube', fg2.fg_tube, 'top', 1.15, False)]
        elif R.district == 'old_quarter' and not R.interior:
            spec = [('fg_car', fg_car, 'bottom', 1.25, True), ('fg_meter', fg_meter, 'bottom', 1.3, True),
                    ('fg_signal', fg_signal_cables, 'top', 1.12, False)]
        made = set()
        for name, fn, x, y, par, fade in fg2.auto_fg(R.id, R.district, R.interior, R.W,
                                                     (south['x0'], south['x1']) if south else None, spec):
            if name not in made:
                fn().to_image().save(os.path.join(d, f'{name}.png'), optimize=True)
                made.add(name)
            if name == 'fg_signal':
                y = 70.0
            elif name == 'fg_meter':
                y = 380.0
            fg.append({"file": f'{name}.png', "x": round(x, 1), "y": y, "parallax": par, "fade": fade})
    if R.drawbridge:
        layers.extend(drawbridge_layers(R, d))
    lm = roommod.build_lightmap(R, 8)
    lm.save(os.path.join(d, 'light.png'))
    if R.interior:
        for rf in R.reflect:
            rf["alpha"] = min(0.12, rf["alpha"])
    js = {
        "room": R.id, "width": R.W, "density": D,
        "layers": layers,
        "fg": fg,
        "lightmap": {"file": "light.png", "cell": 8},
        "ambient_color": R.ambient_color,
        "rim": R.rim,
        "glows": R.glows,
        "ambient": R.ambient,
        "reflect": R.reflect,
    }
    if not R.interior:
        js["cast_shadow"] = R.cast_shadow

    with open(os.path.join(d, 'room.json'), 'w') as f:
        json.dump(js, f, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    return js


def write_district(dist, out_root):
    d = os.path.join(out_root, '_district')
    os.makedirs(d, exist_ok=True)
    for name, fn in (('sky', district.sky), ('far', district.far), ('mid', district.mid)):
        cv = fn(dist)
        im = cv.to_image(opaque=(name == 'sky'))
        im.save(os.path.join(d, f'{dist}_{name}.png'), optimize=True)
        print(f'  district {dist}_{name}: {im.size}')


def write_props(types, v1meta):
    os.makedirs(OUT_PROPS, exist_ok=True)
    pj_path = os.path.join(OUT_PROPS, 'props.json')
    out = json.load(open(pj_path)) if os.path.exists(pj_path) else {}
    from PIL import Image as _I
    for t in sorted(types):
        if t not in props2.PROPS:
            print(f'  ! prop {t} has no v2 drawing yet (v1 fallback)')
            continue
        meta = v1meta[t]
        w1, h1 = _I.open(os.path.join(ROOT, 'game', meta['file'].replace('res://', ''))).size
        cv = Canvas(w1, h1, D)
        props2.PROPS[t](cv, w1, h1)
        cv.to_image().save(os.path.join(OUT_PROPS, f'{t}.png'), optimize=True)
        out[t] = {"anchor": meta['anchor'], "footprint": meta['footprint'], "density": D,
                  "file": f'res://assets/props2/{t}.png'}
    with open(pj_path, 'w') as f:
        json.dump(dict(sorted(out.items())), f, indent=1)


# ----------------------------------------------------------------------------- preview
def _load(path):
    return Image.open(path).convert('RGBA')


def preview(rid, js, out_dir, positions=3, debug=True, figures=True):
    d = os.path.join(OUT_BG, rid)
    W = js['width']
    vw, vh = 640, 360
    rooms, _ = load()
    data = rooms[rid]
    v1 = json.load(open(V1_PROPS))
    p2 = json.load(open(os.path.join(OUT_PROPS, 'props.json')))
    lm = np.asarray(Image.open(os.path.join(d, js['lightmap']['file'])).convert('RGB'), np.float32) / 204.0
    cams = [0.0] if W <= vw else [0.0, (W - vw) / 2, W - vw][:positions]
    outs = []
    for ci, cl in enumerate(cams):
        frame = Image.new('RGBA', (vw * D, vh * D), (0, 0, 0, 255))
        for L in js['layers']:
            par = L['parallax']
            imgs = [_load(os.path.normpath(os.path.join(d, f))) for f in L['files']]
            total = sum(i.width for i in imgs)
            ox = -cl * par * D
            y = int(L['y'] * D)
            if L.get('repeat'):
                start = ox % total - total
                xx = start
                while xx < vw * D:
                    cx = xx
                    for im in imgs:
                        _paste(frame, im, int(round(cx)), y)
                        cx += im.width
                    xx += total
            else:
                cx = ox
                for im in imgs:
                    if -im.width < cx < vw * D:
                        _paste(frame, im, int(round(cx)), y)
                    cx += im.width
        # props + stand-in figures, y-sorted, lightmap-tinted
        items = []
        for p in data.get('props', []):
            t = p['type']
            if t in p2:
                im = _load(os.path.join(ROOT, 'game', p2[t]['file'].replace('res://', '')))
                ax, ay = p2[t]['anchor']
            else:
                im = _load(os.path.join(ROOT, 'game', v1[t]['file'].replace('res://', '')))
                im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
                ax, ay = v1[t]['anchor']
            items.append((p['y'], p['x'], im, ax, ay))
        if figures:
            fig = _figure()
            for fx, fy in ((cl + 200, data['walk'][0] + 30), (cl + 300, data['walk'][1] - 20),
                           (cl + 440, (data['walk'][0] + data['walk'][1]) / 2)):
                items.append((fy, fx, fig, 12, 48))
        for (py, px, im, ax, ay) in sorted(items, key=lambda t: t[0]):
            gx = int(min(lm.shape[1] - 1, max(0, px / 8)))
            gy = int(min(lm.shape[0] - 1, max(0, py / 8)))
            mul = lm[gy, gx]
            a = np.asarray(im, np.float32)
            a[..., :3] = np.clip(a[..., :3] * mul[None, None, :], 0, 255)
            tim = Image.fromarray(a.astype(np.uint8), 'RGBA')
            _paste(frame, tim, int(round((px - ax - cl) * D)), int(round((py - ay) * D)))
        # foreground sprites at parallax
        for g in js['fg']:
            im = _load(os.path.join(d, g['file']))
            cx = (g['x'] - (cl + vw / 2)) * g['parallax'] + vw / 2
            _paste(frame, im, int(round(cx * D - im.width / 2)), int(round(g['y'] * D - im.height)))
        if debug:
            dbg = frame.copy()
            dr = ImageDraw.Draw(dbg)
            for yy in data['walk']:
                dr.line([(0, yy * D), (vw * D, yy * D)], fill=(0, 255, 120, 255), width=2)
            for dd in data.get('doors', []):
                x = (dd['x'] - cl) * D
                dr.line([(x, 150 * D), (x, data['walk'][0] * D)], fill=(255, 220, 0, 255), width=2)
            for side, ex in data.get('exits', {}).items():
                if side == 'south':
                    dr.rectangle([((ex['x0'] - cl) * D, (vh - 6) * D), ((ex['x1'] - cl) * D, vh * D)],
                                 outline=(255, 80, 255, 255), width=2)
            for p in data.get('props', []):
                fp = (p2.get(p['type']) or v1[p['type']])['footprint']
                x0 = (p['x'] - fp[0] / 2 - cl) * D
                y0 = (p['y'] - fp[1]) * D
                dr.rectangle([x0, y0, x0 + fp[0] * D, p['y'] * D], outline=(255, 60, 60, 255), width=2)
            for b in data.get('blockers', []):
                bb = b if isinstance(b, list) else [b['x'], b['y'], b['w'], b['h']]
                dr.rectangle([(bb[0] - cl) * D, bb[1] * D, (bb[0] + bb[2] - cl) * D, (bb[1] + bb[3]) * D],
                             outline=(60, 160, 255, 255), width=3)
            dbg.convert('RGB').save(os.path.join(out_dir, f'{rid}_cam{ci}_debug.png'))
        fn = os.path.join(out_dir, f'{rid}_cam{ci}.png')
        frame.convert('RGB').save(fn)
        outs.append(fn)
    return outs


def _paste(frame, im, x, y):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(frame.width, x + im.width), min(frame.height, y + im.height)
    if x1 <= x0 or y1 <= y0:
        return
    frame.alpha_composite(im.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


_FIG = None


def _figure():
    """Scale stand-in: v1 Nico idle frame (64 px cell) at 2x nearest -- PREVIEW ONLY."""
    global _FIG
    if _FIG is None:
        sh = Image.open(os.path.join(ROOT, 'game', 'assets', 'sprites', 'characters', 'nico.png')).convert('RGBA')
        cell = sh.crop((0, 0, 64, 64)).resize((128, 128), Image.NEAREST)
        f = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        f.alpha_composite(cell)
        _FIG = f.crop((40, 24, 88, 120))   # anchor (32,60)*2 = (64,120) -> (24, 96) in crop
    return _FIG


# ----------------------------------------------------------------------------- main
def write_ledger(built):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    lines = [
        '# Environments v2 -- asset ledger',
        '',
        'Generated by `tools/art2/env/gen_env2.py` (deterministic; Python 3 + Pillow + numpy). No downloads, no paid',
        'services, no third-party imagery. Licence: **project-original** (same terms as the rest of the game).',
        'Sign lettering uses the OFL fonts shipped in `game/assets/fonts/ofl/` (Bungee, Barlow; SIL OFL 1.1), rendered',
        'into the images; see THIRD_PARTY_NOTICES.md.',
        '',
        '## Method',
        '- Shapes are rasterised with 4x4 supersampled anti-aliasing at density 2 (1 world unit = 2 texels), with',
        '  2 tx ink on major forms and 1 tx on details, three-tone cel shading (shadows hue-shifted toward violet,',
        '  lights toward warm) and low-frequency value noise for grime. Nothing is upscaled from v1.',
        '- Each exterior is graded with a dusk ramp (warm upper floors, cool street level). Emissive texels (lit',
        '  windows, neon, lamps) are tracked in an emission mask and skip the grade.',
        '- Lightmaps are built from the ambient colour plus authored light sources (lamps, storefront spill, fire,',
        '  dark alleys), encoded as value/204 = multiplier and clamped to 140..240 in the playable band.',
        '- Geometry comes from `game/data/rooms.json`: facade spans, doors, exits, props, walk band. The generator',
        '  never writes to it.',
        '',
        '## Built',
    ]
    prev = {}
    if os.path.exists(LEDGER):
        for ln in open(LEDGER).read().splitlines():
            if ln.startswith('- `') and '`: ' in ln:
                prev[ln[3:ln.index('`', 3)]] = ln
    for rid, info in built:
        prev[rid] = f'- `{rid}`: {info}'
    for rid in sorted(prev):
        lines.append(prev[rid])
    with open(LEDGER, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rooms', default='oq_kettle,int_diner,oq_chainlot')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--preview', default='')
    ap.add_argument('--no-props', action='store_true')
    ap.add_argument('--no-district', action='store_true')
    a = ap.parse_args()
    rooms, enc = load()
    v1meta = json.load(open(V1_PROPS))
    ids = list(rooms.keys()) if a.all else [r for r in a.rooms.split(',') if r]
    dists = sorted({rooms[r]['district'] for r in ids if rooms[r].get('kind') != 'interior'
                    and rooms[r]['district'] in district.DIST and ROOM_DISTRICT_LAYERS.get(r) != []})
    if not a.no_district:
        for dd in dists:
            write_district(dd, OUT_BG)
    if not a.no_props:
        types = {p['type'] for r in ids for p in rooms[r].get('props', [])}
        write_props(types, v1meta)
    built = []
    for rid in ids:
        R, img = build_room(rid, rooms, enc, v1meta)
        js = write_room(R, img, OUT_BG)
        built.append((rid, f'{img.width}x{img.height} tx base in {len(js["layers"][-1]["files"])} tile(s), '
                           f'{len(js["fg"])} fg, {len(js["glows"])} glows, {len(js["ambient"])} ambient'))
        if a.preview:
            os.makedirs(a.preview, exist_ok=True)
            preview(rid, js, a.preview)
    write_ledger(built)


if __name__ == '__main__':
    main()
