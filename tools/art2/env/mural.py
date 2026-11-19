#!/usr/bin/env python3
"""BACKSTREET OATH -- Kiki's mural at the Market Gate (side job "Wet Paint"). Deterministic; Pillow + numpy only.

Draws two story-gated overlay layers for game/assets/bg2/cm_gate, on the low brick wall under the market arch:
  mural_tagged.png  until the side job is done: Kiki's first mural, faded and tagged over by the Chain Dogs
  mural_done.png    once quest:mural=done: the finished wall (the canal, the bridge, Dot's diner, everybody,
                    and Nico. Big. With a cape.)
and registers them in cm_gate/room.json as layers after "base" (docs/visual/ASSET_CONTRACT_V2.md section 2,
"requires" / "unless"). The paint is modulated by the brick already in base_0.png, so the courses and the baked
dusk shading show through and the wall still reads as a wall.

Run it again after regenerating cm_gate with gen_env2.py (that rewrites room.json and clears the room's PNGs),
then let Godot import the PNGs and run tools/art2/optimize_textures.py as usual.

Usage: python3 tools/art2/env/mural.py [--preview DIR]
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from raster import Canvas, C, mix, blur, value_noise   # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ROOM_DIR = os.path.join(ROOT, 'game', 'assets', 'bg2', 'cm_gate')
LEDGER = os.path.join(ROOT, 'docs', 'assets', 'MURAL.md')
D = 2

# The wall as painted in base_0.png (texels): brick from x 488..991 and y 353..426, one course every 7 tx.
WALL_X, WALL_Y, WALL_W, WALL_H = 488, 353, 504, 74
W_U, H_U = WALL_W / D, WALL_H / D      # 252 x 37 world units

INK = C('#2a1c30')
SKY = [C('#f7c66c'), C('#f4a56a'), C('#e57f72')]
SUN = C('#fdeeb4')
HOUSE = [C('#7b5282'), C('#93608a'), C('#6a4a78')]
WIN = C('#ffd971')
WATER, WATER_L, WATER_D = C('#2c8a8c'), C('#6cc9ba'), C('#1f6a74')
BANK, BANK_D = C('#d2b07e'), C('#b08e62')
STONE, STONE_D = C('#e0d0aa'), C('#b9a684')
CREAM, RED, TEAL = C('#f4e8cc'), C('#cf4b3d'), C('#2f9a94')
SKIN = [C('#e6a878'), C('#c98a5c'), C('#f0c090'), C('#a86e48')]

# "Everybody": body colour, hair or hat colour, skin index, height in u. Left to right along the bridge.
FOLK = [
    ('#f08ca8', '#cfcad6', 2, 6.6),   # Dot, pink apron
    ('#8e99a8', '#d8392f', 1, 7.2),   # Coach Benny, red cap
    ('#3f7fc0', '#a8452e', 0, 6.8),   # Mara, overalls
    ('#5fae6a', '#6a4630', 2, 6.9),   # Eli
    ('#f08a3c', '#8a93a0', 0, 4.6),   # Teddy, small
    ('#8a5a3c', '#eadfca', 2, 6.7),   # Mr. Hollis
    ('#f2f2e8', '#2c2630', 0, 6.5),   # Mr. Fong, white apron
    ('#6e78d8', '#f070b0', 1, 6.4),   # Kiki, pink hat
    ('#9a64b8', '#cfcad6', 3, 6.2),   # Mrs. Alvarez (Biscuit is next to her)
]


def top_of_bridge(x):
    return 25.0 - 10.5 * math.sin(math.pi * (x - 60.0) / 92.0)


def under_bridge(x):
    return 37.0 - 17.0 * math.sin(math.pi * (x - 70.0) / 72.0)


def wavy(y, amp, n, phase):
    return [(x, y + amp * math.sin(x * n + phase)) for x in np.linspace(0, W_U, 43)]


def scene(cv, rng):
    """The mural Kiki always meant to paint: sky, sun, water, both banks, the diner, the bridge and everybody."""
    cv.rect(0, 0, W_U, 23, SKY[0])
    cv.fill_poly(wavy(8.2, 0.7, 0.09, 0.4) + [(W_U, 23), (0, 23)], SKY[1])
    cv.fill_poly(wavy(15.4, 0.6, 0.12, 2.0) + [(W_U, 23), (0, 23)], SKY[2])
    # the sun going down behind the bridge
    cv.ellipse(106, 18, 15.0, 15.0, SUN, a=0.4)
    cv.ellipse(106, 18, 11.5, 11.5, C('#fff6cf'), ink=C('#ee8a4a'), iw=1.0)
    for k in range(11):
        a = math.pi * (k + 0.5) / 11
        cv.line([(106 - math.cos(a) * 14.2, 18 - math.sin(a) * 14.2), (106 - math.cos(a) * 17.2, 18 - math.sin(a) * 17.2)],
                0.8, C('#fff6cf'), a=0.9)
    # rowhouses on the far bank
    x = 150.0
    k = 0
    while x < W_U:
        w = 7.0 + rng.random() * 5.0
        h = 4.5 + rng.random() * 4.5
        col = HOUSE[k % 3]
        cv.fill_poly([(x, 23), (x, 23 - h), (x + w * 0.5, 23 - h - 2.4), (x + w, 23 - h), (x + w, 23)], col, ink=INK, iw=0.8)
        for wx in (x + w * 0.28, x + w * 0.66):
            if rng.random() < 0.8:
                cv.rect(wx - 0.6, 23 - h + 1.0, 1.3, 1.6, WIN)
        x += w
        k += 1
    # the canal
    cv.rect(0, 22.6, W_U, H_U - 22.6, WATER)
    cv.rect(0, 31.5, W_U, H_U - 31.5, WATER_D, a=0.55)
    for _ in range(46):
        rx = rng.random() * W_U
        ry = 24.0 + rng.random() * 12.0
        ln = 3.0 + rng.random() * 6.0
        cv.line([(rx, ry), (rx + ln, ry)], 0.6, WATER_L, a=0.9)
    for k in range(7):
        ry = 25.0 + k * 1.7
        half = 7.0 - k * 0.7
        cv.line([(106 - half, ry), (106 + half, ry)], 0.8, SUN, a=0.75)
    # banks
    cv.fill_poly([(0, 24.5), (64, 24.5), (72, H_U), (0, H_U)], BANK, ink=INK, iw=1.0)
    cv.fill_poly([(148, 24.5), (W_U, 24.5), (W_U, H_U), (140, H_U)], BANK, ink=INK, iw=1.0)
    for _ in range(60):
        bx = rng.random() * W_U
        by = 26.5 + rng.random() * 9.5
        if bx < 62 - (by - 24.5) * 0.1 or bx > 152:
            cv.ellipse(bx, by, 1.1, 0.5, BANK_D, a=0.8)
    # the bridge
    xs = list(np.linspace(60, 152, 40))
    ins = list(np.linspace(142, 70, 32))
    poly = [(x, top_of_bridge(x)) for x in xs] + [(152, H_U)] + [(x, under_bridge(x)) for x in ins] + [(60, H_U)]
    cv.fill_poly(poly, STONE, ink=INK, iw=1.0)
    cv.line([(x, under_bridge(x) - 2.2) for x in np.linspace(140, 72, 30)], 0.6, STONE_D)
    for k in range(13):
        x0 = 73.0 + k * 5.5
        cv.line([(x0, under_bridge(x0) - 0.4), (x0, under_bridge(x0) - 2.2)], 0.5, STONE_D)
    cv.line([(x, top_of_bridge(x) + 1.3) for x in np.linspace(62, 150, 36)], 0.5, STONE_D)
    diner(cv)
    stalls(cv)
    everybody(cv)


def diner(cv):
    cv.rect(7, 11, 50, 14, CREAM, ink=INK, iw=1.0)
    cv.rect(5, 7.4, 54, 4.2, RED, ink=INK, iw=1.0)
    cv.text('DINER', 'sign', 3.4, 30, 9.6, CREAM, anchor='mm')
    cv.rect(11, 15, 25, 7, WIN, ink=INK, iw=0.8)
    for mx in (19.3, 27.6):
        cv.rect(mx, 15, 0.6, 7, INK)
    cv.rect(42, 14, 8, 11, TEAL, ink=INK, iw=0.8)
    cv.rect(44, 15.6, 4, 3.4, WIN)
    for k in range(10):            # striped awning over the window
        col = RED if k % 2 == 0 else CREAM
        cv.fill_poly([(9.5 + k * 2.8, 12.6), (12.3 + k * 2.8, 12.6), (12.5 + k * 2.8, 15.4), (9.3 + k * 2.8, 15.4)], col)
    cv.line([(9.4, 15.4), (37.6, 15.4)], 0.5, INK)
    cv.line([(9.4, 12.6), (37.6, 12.6)], 0.5, INK)
    cv.rect(51.6, 2.4, 0.9, 5.2, INK)                     # the Lucky Spoon sign
    cv.ellipse(52, 3.3, 3.1, 2.9, TEAL, ink=INK, iw=0.8)
    cv.ellipse(51.3, 2.6, 1.0, 1.3, CREAM)
    cv.line([(51.7, 3.4), (53.3, 5.0)], 0.7, CREAM)


def stalls(cv):
    for i, (x0, a, b) in enumerate(((203.0, TEAL, CREAM), (228.0, C('#f0b62c'), CREAM))):
        cv.rect(x0 + 1.0, 14.5, 0.8, 10, INK)
        cv.rect(x0 + 19.4, 14.5, 0.8, 10, INK)
        cv.rect(x0 + 0.6, 19.6, 20, 5, C('#a8703f'), ink=INK, iw=0.8)
        for k in range(7):
            col = a if k % 2 == 0 else b
            cv.fill_poly([(x0 + k * 3.0, 11.2), (x0 + 3.0 + k * 3.0, 11.2), (x0 + 3.4 + k * 3.0, 15), (x0 - 0.4 + k * 3.0, 15)], col)
        cv.line([(x0 - 0.4, 15), (x0 + 21.4, 15)], 0.5, INK)
        cv.line([(x0, 11.2), (x0 + 21, 11.2)], 0.5, INK)
        for k in range(5):
            gx = x0 + 3.0 + k * 3.7
            if i == 0:
                cv.ellipse(gx, 18.7, 1.25, 1.2, [C('#f08a3c'), C('#d8392f'), C('#7ac05a')][k % 3], ink=INK, iw=0.5)
            else:
                cv.ellipse(gx, 18.9, 1.7, 0.85, C('#b9d3de'), ink=INK, iw=0.5)


def everybody(cv):
    spots = []
    for i, (body, top, sk, h) in enumerate(FOLK):
        x = 70.0 + i * 9.2
        feet = top_of_bridge(x) + 0.4
        sh = feet - h * 0.62
        spots.append((x, sh))
    for i in range(len(spots) - 1):            # hand in hand
        (xa, sa), (xb, sb) = spots[i], spots[i + 1]
        cv.line([(xa + 1.0, sa + 1.0), ((xa + xb) / 2, max(sa, sb) + 2.4), (xb - 1.0, sb + 1.0)], 0.6, INK)
    cv.line([(spots[0][0] - 1.0, spots[0][1] + 1.0), (spots[0][0] - 3.4, spots[0][1] - 2.0)], 0.6, INK)
    for i, (body, top, sk, h) in enumerate(FOLK):
        x, sh = spots[i]
        feet = sh + h * 0.62
        cv.fill_poly([(x - 1.7, feet), (x + 1.7, feet), (x + 1.25, sh), (x - 1.25, sh)], C(body), ink=INK, iw=0.8)
        cv.ellipse(x, sh - 1.25, 1.45, 1.4, SKIN[sk], ink=INK, iw=0.8)
        cv.fill_poly([(x - 1.6, sh - 1.5), (x - 1.1, sh - 2.9), (x + 1.1, sh - 2.9), (x + 1.6, sh - 1.5)], C(top))
    # Biscuit, at the end of the line
    bx, by = 151.0, 23.9
    tan = C('#d9a25e')
    cv.ellipse(bx, by, 2.1, 1.1, tan, ink=INK, iw=0.7)
    cv.ellipse(bx + 2.1, by - 1.0, 1.1, 1.0, tan, ink=INK, iw=0.7)
    cv.line([(bx - 2.0, by - 0.4), (bx - 3.0, by - 1.8)], 0.6, INK)
    cv.fill_poly([(bx + 1.5, by - 1.7), (bx + 1.9, by - 2.9), (bx + 2.5, by - 1.8)], tan, ink=INK, iw=0.5)


def nico(cv):
    """Painted in once the wall is safe. Big. With a cape."""
    jacket, jeans, skin = C('#f0b62c'), C('#3d5fa6'), C('#e6a878')
    hair, band, cape, cape_d = C('#3a1d24'), C('#e0392f'), C('#de3a36'), C('#a92b3c')
    cx = 178.0
    cape_pts = [(cx - 4.6, 14.8), (cx + 5.0, 14.4), (cx + 18, 11.2), (cx + 29, 13.2), (cx + 35.5, 18.2), (cx + 31, 21.6),
                (cx + 36.5, 26.4), (cx + 28, 28.8), (cx + 20.5, 26.4), (cx + 14.5, 30.6), (cx + 8, 27.2), (cx + 3, 25)]
    cv.fill_poly(cape_pts, cape, ink=INK, iw=1.2)
    cv.fill_poly([(cx + 5, 20.5), (cx + 16, 17.2), (cx + 27, 18.8), (cx + 31, 21.6), (cx + 36.5, 26.4), (cx + 28, 28.8),
                  (cx + 20.5, 26.4), (cx + 14.5, 30.6), (cx + 8, 27.2), (cx + 3, 25)], cape_d)
    cv.line([(cx + 6, 15.6), (cx + 17, 19.5), (cx + 20.5, 26.2)], 0.6, INK)
    cv.line([(cx + 12, 14), (cx + 25, 16.5), (cx + 31, 21.4)], 0.6, INK)
    # legs and shoes
    cv.fill_poly([(cx - 3.9, 24.2), (cx - 0.3, 24.2), (cx - 1.0, 33.6), (cx - 5.0, 33.6)], jeans, ink=INK, iw=1.0)
    cv.fill_poly([(cx + 0.3, 24.2), (cx + 3.9, 24.2), (cx + 5.0, 33.6), (cx + 1.0, 33.6)], jeans, ink=INK, iw=1.0)
    cv.ellipse(cx - 3.4, 34.5, 2.6, 1.2, band, ink=INK, iw=0.9)
    cv.ellipse(cx + 3.4, 34.5, 2.6, 1.2, band, ink=INK, iw=0.9)
    # arms akimbo (behind the torso), then the jacket
    for s in (-1, 1):
        cv.line([(cx + s * 4.6, 16.6), (cx + s * 9.0, 20.4), (cx + s * 4.8, 23.4)], 2.7, jacket, ink=INK, iw=1.0)
    cv.fill_poly([(cx - 5.4, 15.2), (cx + 5.4, 15.2), (cx + 4.6, 25), (cx - 4.6, 25)], jacket, ink=INK, iw=1.0)
    cv.fill_poly([(cx - 1.9, 15.2), (cx + 1.9, 15.2), (cx, 19.6)], C('#f6efe0'))
    cv.line([(cx, 19.6), (cx, 25)], 0.6, INK)
    for s in (-1, 1):
        cv.ellipse(cx + s * 4.9, 23.4, 1.5, 1.5, skin, ink=INK, iw=0.8)
    cv.ellipse(cx, 15.6, 2.0, 1.1, cape, ink=INK, iw=0.8)          # the knot
    # head, hair, headband
    cv.ellipse(cx, 10.4, 4.7, 4.5, skin, ink=INK, iw=1.0)
    cv.fill_poly([(cx - 4.9, 9.6), (cx - 5.8, 6.0), (cx - 3.4, 7.0), (cx - 3.0, 3.6), (cx - 0.8, 6.0), (cx + 0.8, 2.8),
                  (cx + 2.4, 5.8), (cx + 5.0, 3.8), (cx + 4.8, 6.8), (cx + 6.6, 6.4), (cx + 4.9, 9.6), (cx, 8.0)],
                 hair, ink=INK, iw=0.8)
    cv.line([(cx - 4.6, 9.0), (cx + 4.6, 9.0)], 1.4, band, ink=INK, iw=0.5)
    cv.line([(cx + 4.6, 9.0), (cx + 9.0, 7.4)], 1.0, band, ink=INK, iw=0.5)
    cv.line([(cx + 4.6, 9.2), (cx + 8.6, 10.2)], 1.0, band, ink=INK, iw=0.5)
    for s in (-1, 1):
        cv.ellipse(cx + s * 1.8, 11.4, 0.6, 0.95, INK)
    cv.line([(cx - 1.5, 13.0), (cx, 13.7), (cx + 1.5, 13.0)], 0.55, INK)
    cv.text("KIKI '88", 'cond', 3.4, W_U - 3.0, H_U - 2.2, INK, anchor='rs')


def ring(cv, cx, cy, rx, ry, w, col, a=1.0, rot=0.0):
    pts = []
    for k in range(25):
        t = 2 * math.pi * k / 24
        px, py = math.cos(t) * rx, math.sin(t) * ry
        pts.append((cx + px * math.cos(rot) - py * math.sin(rot), cy + px * math.sin(rot) + py * math.cos(rot)))
    cv.line(pts, w, col, a=a)


def tags(cv, rng):
    """What the Chain Dogs left on it."""
    acid, dark, silver, pink = C('#c6ee3e'), C('#17111d'), C('#ecebf2'), C('#e83a8c')
    cv.fill_poly([(158, 4), (203, 3), (205, 32), (160, 33)], C('#ddd2bc'), a=0.62)      # primer Kiki rolled on, twice
    cv.text('DOGS', 'sign', 25, 64, 16.5, dark, anchor='mm', ink=acid, iw=1.6, tracking=0.6)
    for dx, ln in ((30.5, 6.0), (52, 9.5), (70, 4.5), (93, 8.0)):
        cv.line([(dx, 25.0), (dx, 25.0 + ln)], 1.3, acid, a=0.95)
        cv.line([(dx + 1.2, 25.0), (dx + 1.2, 23.5 + ln * 0.6)], 0.9, dark)
    cv.text('RULE', 'sign', 9.5, 64, 31.2, acid, anchor='mm', ink=dark, iw=0.9, tracking=0.5)
    for k in range(9):                               # a length of chain along the water
        cx_ = 112.0 + k * 9.6
        cy_ = 28.5 + 2.2 * math.sin(k * 0.9)
        ring(cv, cx_, cy_, 5.6, 2.3, 1.1, silver, a=0.92, rot=0.25 if k % 2 == 0 else -0.25)
    hx, hy = 222.0, 17.0                              # a dog's head, more or less
    ring(cv, hx, hy, 9.5, 8.5, 1.3, pink, a=0.95)
    cv.line([(hx - 8.5, hy - 4), (hx - 9.5, hy - 14), (hx - 3, hy - 8.0)], 1.3, pink, a=0.95)
    cv.line([(hx + 8.5, hy - 4), (hx + 9.5, hy - 14), (hx + 3, hy - 8.0)], 1.3, pink, a=0.95)
    for s in (-1, 1):
        cv.line([(hx + s * 3.6 - 1.6, hy - 3.6), (hx + s * 3.6 + 1.6, hy - 0.4)], 1.0, pink)
        cv.line([(hx + s * 3.6 + 1.6, hy - 3.6), (hx + s * 3.6 - 1.6, hy - 0.4)], 1.0, pink)
    cv.line([(hx - 5, hy + 3.4), (hx - 2.5, hy + 5.6), (hx, hy + 3.4), (hx + 2.5, hy + 5.6), (hx + 5, hy + 3.4)], 1.0, pink)
    cv.line([(hx - 11, hy + 11), (hx - 7, hy + 13.5), (hx - 3.5, hy + 11), (hx, hy + 13.5), (hx + 3.5, hy + 11),
             (hx + 7, hy + 13.5), (hx + 11, hy + 11)], 1.2, silver, a=0.92)
    cv.line([(170, 9), (194, 28)], 1.6, dark, a=0.9)
    cv.line([(194, 9), (170, 28)], 1.6, dark, a=0.9)
    for _ in range(140):                             # overspray
        ox = rng.random() * W_U
        oy = rng.random() * H_U
        cv.ellipse(ox, oy, 0.35, 0.35, [acid, dark, silver, pink][int(rng.random() * 4)], a=0.5)


def fade(cv, keep, grey):
    """An old coat of paint: thinner and washed out."""
    a = cv.px[..., 3:4]
    with np.errstate(invalid='ignore', divide='ignore'):
        rgb = np.where(a > 1e-5, cv.px[..., :3] / np.maximum(a, 1e-5), 0)
    lum = (rgb * np.array([0.299, 0.587, 0.114], np.float32)).sum(axis=2, keepdims=True)
    rgb = rgb * (1 - grey) + (lum * 0.9 + 0.08) * grey
    cv.px[..., :3] = rgb * a * keep
    cv.px[..., 3:4] = a * keep


def on_brick(paint, brick, seed):
    """Lets the wall show through the paint: brick courses, the baked dusk falloff, and a rough painted edge."""
    p = np.asarray(paint, np.float32) / 255.0
    b = np.asarray(brick.convert('RGB'), np.float32) / 255.0
    lum = (b * np.array([0.299, 0.587, 0.114], np.float32)).sum(axis=2)
    soft = blur(lum, 6)
    course = np.clip(lum / np.maximum(soft, 1e-4), 0.74, 1.14)          # mortar lines and brick-to-brick variation
    fall = np.clip(soft / max(1e-4, float(soft[:10].mean())), 0.0, 1.1) ** 0.75   # darker toward the ground
    k = (0.12 + 0.88 * course) * fall
    rgb = p[..., :3] * k[..., None] * np.array([0.95, 0.91, 0.93], np.float32)
    h, w = lum.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    rough = value_noise(w, h, 5, seed, octaves=2) * 3.2
    mask = np.clip((edge - rough) / 1.2, 0, 1)
    wear = 0.86 + 0.14 * value_noise(w, h, 9, seed + 1, octaves=2)        # thin patches in the paint
    alpha = p[..., 3] * mask * wear
    out = np.concatenate([np.clip(rgb, 0, 1), alpha[..., None]], axis=2)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')


def render(state):
    rng = np.random.default_rng(1988)
    cv = Canvas(W_U, H_U, D)
    scene(cv, rng)
    if state == 'done':
        nico(cv)
    else:
        fade(cv, 0.6, 0.45)
        tags(cv, np.random.default_rng(7))
    return cv.to_image()


def register(files):
    """Adds (or refreshes) the two gated layers in cm_gate/room.json, right after the base layer."""
    path = os.path.join(ROOM_DIR, 'room.json')
    js = json.load(open(path))
    layers = [L for L in js['layers'] if not str(L.get('name', '')).startswith('mural_')]
    at = [i for i, L in enumerate(layers) if L.get('name') == 'base'][0] + 1
    spacer = f'spacer_{WALL_X}.png'
    new = []
    for name, fn, gate in files:
        e = {"name": name, "files": [spacer, fn], "parallax": 1.0, "y": WALL_Y / D, "repeat": False}
        e.update(gate)
        new.append(e)
    js['layers'] = layers[:at] + new + layers[at:]
    with open(path, 'w') as f:
        json.dump(js, f, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default='')
    a = ap.parse_args()
    base = Image.open(os.path.join(ROOM_DIR, 'base_0.png')).convert('RGBA')
    brick = base.crop((WALL_X, WALL_Y, WALL_X + WALL_W, WALL_Y + WALL_H))
    Image.new('RGBA', (WALL_X, 1), (0, 0, 0, 0)).save(os.path.join(ROOM_DIR, f'spacer_{WALL_X}.png'))
    files = []
    for state, gate in (('tagged', {"unless": "quest:mural=done"}), ('done', {"requires": "quest:mural=done"})):
        im = on_brick(render(state), brick, 11 if state == 'done' else 23)
        fn = f'mural_{state}.png'
        im.save(os.path.join(ROOM_DIR, fn), optimize=True)
        files.append((f'mural_{state}', fn, gate))
        if a.preview:
            os.makedirs(a.preview, exist_ok=True)
            shot = base.crop((WALL_X - 80, WALL_Y - 130, WALL_X + WALL_W + 80, WALL_Y + WALL_H + 60)).copy()
            shot.alpha_composite(im, (80, 130))
            bg = Image.new('RGBA', shot.size, (150, 120, 110, 255))
            bg.alpha_composite(shot)
            bg.resize((bg.width * 3, bg.height * 3), Image.NEAREST).save(os.path.join(a.preview, f'mural_{state}_x3.png'))
    register(files)
    with open(LEDGER, 'w') as f:
        f.write("# Kiki's mural (Market Gate)\n\n"
                "Generated by `tools/art2/env/mural.py` (deterministic, Pillow + numpy, the project's own raster kit).\n"
                "Project-original art; the only outside material is the OFL sign typeface already shipped with the game.\n\n"
                "| File | Size | Shown when | What it is |\n|---|---|---|---|\n"
                f"| `game/assets/bg2/cm_gate/mural_tagged.png` | {WALL_W}x{WALL_H} tx | `unless quest:mural=done` | "
                "Kiki's first mural, faded, primed over and tagged by the Chain Dogs |\n"
                f"| `game/assets/bg2/cm_gate/mural_done.png` | {WALL_W}x{WALL_H} tx | `requires quest:mural=done` | "
                "the finished wall: the canal, the bridge, Dot's diner, everybody, and Nico with a cape |\n"
                f"| `game/assets/bg2/cm_gate/spacer_{WALL_X}.png` | {WALL_X}x1 tx | - | transparent tile that positions the layer |\n\n"
                f"Both are layers after `base` in `cm_gate/room.json`, placed on the low brick wall under the market arch "
                f"(world x {WALL_X // D}-{(WALL_X + WALL_W) // D}, y {WALL_Y / D}-{(WALL_Y + WALL_H) / D}). The paint is multiplied by the brick "
                "in `base_0.png`, so re-run this script after regenerating `cm_gate` with `gen_env2.py`.\n")
    print('mural: wrote', ', '.join(fn for _, fn, _ in files))


if __name__ == '__main__':
    main()
