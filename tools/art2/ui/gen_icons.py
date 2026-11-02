#!/usr/bin/env python3
"""v2 item / UI icons: 32x32 at density 2 (shown at 16 u) -> game/assets/icons2/<id>.png.

There is one icon per id in game/assets/icons/. Every icon is redrawn as vectors in the
inked, cel-shaded style: a 2 tx silhouette contour, 1 tx inner part contours, and the key
light from the top-left. Weapon icons come from the new 2x weapon art (weapons2), rotated
and fitted (a downscale), and then re-inked.

Usage: python3 tools/art2/ui/gen_icons.py [id ...]
"""
import glob
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vec import (Layer, hx, mix, tones, save, bez, ell_pts, star_pts, rot_pts, F_BUNGEE, F_COND_B, INK,  # noqa: E402
                 ASSETS, dilate)
import gen_items  # noqa: E402
from gen_items import Item  # noqa: E402

OUT = os.path.join(ASSETS, 'icons2')
S = 32
WHITE = (255, 255, 255)
CREAM = hx('#f2e8d2')
REG = {}


def icon(name):
    def deco(fn):
        REG[name] = fn
        return fn
    return deco


def new():
    return Item(S, S, ss=6)


def fin(it, post=None):
    it.L.outline(2.0, INK)
    if post:
        post(it.L)
    return it.L.image()


def steam(L, xs, y0=9, h=7, a=0.85):
    for i, x in enumerate(xs):
        p = bez((x, y0), (x - 2.2, y0 - h * 0.5), (x + 0.6 * (1 if i % 2 else -1), y0 - h))
        L.fill(L.stroke(p, 1.1), WHITE, a)


def plate(it, cx=16, cy=25, rx=13, ry=3.6, col=hx('#e8eef2')):
    m = it.L.ellipse(cx, cy, rx, ry)
    it.part(m, col, sh_off=1.0)
    it.L.fill(it.L.ellipse(cx, cy - 0.6, rx * 0.7, ry * 0.55), mix(col, hx('#a8b4c0'), 0.35), 0.7)
    return m


def bowl(it, food, bowl_col=hx('#e8e2d4'), rim_y=15, x0=4, x1=28, depth=11, food_hi=None):
    L = it.L
    cx = (x0 + x1) / 2
    rx = (x1 - x0) / 2
    body = L.poly(ell_pts(cx, rim_y, rx, 3.4, a0=0, a1=180, n=30) + [(cx - rx * 0.55, rim_y + depth), (cx + rx * 0.55, rim_y + depth)][::-1])
    body = np.clip(body + L.ellipse(cx, rim_y + depth - 0.6, rx * 0.5, 1.6), 0, 1)
    it.part(body, bowl_col)
    L.fill(L.rect(x0, rim_y + 3.2, x1, rim_y + 4.8) * body, hx('#c8402e'), 0.9)
    top = L.ellipse(cx, rim_y, rx, 3.4)
    it.part(top, food)
    if food_hi:
        L.fill(L.ellipse(cx - rx * 0.25, rim_y - 0.8, rx * 0.45, 1.3), food_hi, 0.8)
    return top


def cup(it, x0, x1, y0, y1, col, liquid=None, handle=True):
    L = it.L
    cx = (x0 + x1) / 2
    if handle:
        h = np.clip(L.ellipse(x1 + 0.5, (y0 + y1) / 2, 4, 4.6) - L.ellipse(x1 + 0.5, (y0 + y1) / 2, 2, 2.6), 0, 1)
        it.part(h, col)
    body = np.clip(L.rect(x0, y0, x1, y1 - 2, r=0.5) + L.ellipse(cx, y1 - 2, (x1 - x0) / 2, 2.2), 0, 1)
    it.part(body, col)
    top = L.ellipse(cx, y0, (x1 - x0) / 2, 2.2)
    it.part(top, mix(col, hx('#8a8a9a'), 0.3))
    if liquid:
        L.fill(L.ellipse(cx, y0 + 0.4, (x1 - x0) / 2 - 1.2, 1.4), liquid)
    return body


def book(it, col, x0=6, y0=4, x1=26, y1=28, pages=CREAM):
    L = it.L
    pg = L.rect(x0 + 2, y0 + 1.5, x1 + 1, y1 + 1, r=1)
    it.part(pg, pages)
    for y in np.arange(y0 + 3, y1, 2.2):
        L.fill(L.rect(x1 - 0.5, y, x1 + 1, y + 0.5) * pg, hx('#b8a890'))
    cov = L.rect(x0, y0, x1 - 1, y1, r=1.5)
    it.part(cov, col)
    sp = L.rect(x0, y0, x0 + 3.5, y1, r=1)
    it.part(sp, mix(col, INK, 0.35))
    for y in (y0 + 3, y1 - 4):
        L.fill(L.rect(x0 + 0.5, y, x0 + 3, y + 1), hx('#e8c860'), 0.9)
    return cov


def paper(it, x0, y0, x1, y1, col=CREAM, rot=0, lines=True):
    L = it.L
    pts = rot_pts([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], rot, (x0 + x1) / 2, (y0 + y1) / 2)
    m = L.poly(pts)
    it.part(m, col, sh_off=0.8)
    if lines:
        for y in np.arange(y0 + 4, y1 - 2, 2.6):
            seg = rot_pts([(x0 + 2.5, y), (x1 - 2.5 - (2 if int(y) % 3 == 0 else 0), y)], rot, (x0 + x1) / 2, (y0 + y1) / 2)
            L.fill(L.stroke(seg, 0.55) * m, hx('#8a8070'), 0.8)
    return m


def scroll(it, mark):
    L = it.L
    body = L.rect(7, 6, 25, 26)
    it.part(body, CREAM)
    for y in (6, 26):
        roll = L.rect(5, y - 2.2, 27, y + 2.2, r=2.2)
        it.part(roll, hx('#d8c49a'))
    for y in np.arange(10, 23, 2.6):
        L.fill(L.rect(9.5, y, 22.5, y + 0.6) * body, hx('#a89a80'), 0.7)
    return mark


def badge(L, x, y, r, col):
    m = L.circle(x, y, r)
    L.fill(L.dil(m, 1.2), INK)
    sh, b, li, ink = tones(col)
    L.fill(m, b)
    L.fill(np.clip(m - L.shift(m, -0.8, -0.8), 0, 1), sh)
    L.fill(L.circle(x - r * 0.3, y - r * 0.3, r * 0.4) * m, li)
    return m


def arrow_shape(L, d):
    pts = [(16, 4), (27, 15), (20.5, 15), (20.5, 27), (11.5, 27), (11.5, 15), (5, 15)]
    ang = {'up': 0, 'right': 90, 'down': 180, 'left': 270}[d]
    return L.poly(rot_pts(pts, ang, 16, 16))


# ============================================================ foods
@icon('coffee')
def _():
    it = new()
    cup(it, 7, 21, 12, 27, hx('#efe6d6'), liquid=hx('#5a3420'))
    it.L.fill(it.L.rect(7, 18, 21, 20.5), hx('#c8402e'))
    return fin(it, lambda L: steam(L, (11, 15.5), 9, 6))


@icon('pancakes')
def _():
    it = new()
    L = it.L
    plate(it)
    for k in range(3):
        y = 22 - k * 4
        cake = np.clip(L.ellipse(16, y, 11, 3.6) + L.rect(5, y - 1.2, 27, y + 0.8) + L.ellipse(16, y + 1, 11, 3.2), 0, 1)
        it.part(cake, hx('#e0a258'), sh_off=1.2)
        L.fill(L.ellipse(16, y - 0.8, 10, 2.8), hx('#f0c47a'))
    syr = L.poly([(9, 12.5), (23, 12.5), (22, 15), (21, 19), (19.5, 15.5), (13, 15), (11, 18), (10, 15)])
    it.part(syr, hx('#a8521e'))
    butter = L.rect(13.5, 9, 18.5, 12.5, r=0.8)
    it.part(butter, hx('#ffe48a'))
    return fin(it)


@icon('meatloaf')
def _():
    it = new()
    L = it.L
    plate(it)
    side = L.poly([(5, 14), (21, 11), (27, 14), (27, 22), (11, 25), (5, 22)])
    it.part(side, hx('#8a4a30'))
    top = L.poly([(5, 14), (21, 11), (27, 14), (11, 17)])
    it.part(top, hx('#c03a26'))
    face = L.poly([(5, 14), (11, 17), (11, 25), (5, 22)])
    it.part(face, hx('#a86a48'))
    for x, y in ((7, 19), (9, 21.5), (7.5, 22.5)):
        L.fill(L.circle(x, y, 0.6), hx('#5a2a1a'))
    L.fill(L.circle(14, 15, 1), hx('#5aa83a'))
    return fin(it)


@icon('cherry_pie')
def _():
    it = new()
    L = it.L
    plate(it, cy=25.5)
    wedge_top = L.poly([(4, 17), (25, 10), (28, 15), (9, 21)])
    side = L.poly([(4, 17), (9, 21), (28, 15), (28, 19), (9, 25), (4, 21)])
    it.part(side, hx('#e0aa66'))
    L.fill(L.poly([(4.5, 19), (9, 22.5), (27.5, 16.5), (27.5, 17.6), (9, 23.6), (4.5, 20)]), hx('#a8202e'))
    it.part(wedge_top, hx('#b8202e'))
    for k in range(4):
        a = (7 + k * 5, 18.5 - k * 1.8)
        L.fill(L.stroke([a, (a[0] + 3, a[1] - 6.5)], 1.6) * wedge_top, hx('#f0c47a'))
    crust = L.stroke([(25, 10), (28, 15)], 2.6)
    it.part(crust, hx('#e8b46a'))
    badge(L, 22, 8.5, 2.2, hx('#d8202e'))
    L.fill(L.stroke(bez((22, 6.5), (23, 3.5), (25.5, 3)), 0.8), hx('#4a7a2a'))
    return fin(it)


@icon('club_sandwich')
def _():
    it = new()
    L = it.L
    layers = [('#e8c07a', 0), ('#5aa83a', 1), ('#d8402e', 2), ('#f0d8a0', 3), ('#c86a48', 4), ('#e8c07a', 5)]
    for col, k in layers:
        y = 25 - k * 3.2
        th = 3.6 if k in (0, 3, 5) else 2.4
        m = L.poly([(4, y), (26, y), (26 - 1.2, y - th), (5.5, y - th)])
        it.part(m, hx(col), sh_off=0.8)
    pick = L.stroke([(16, 10), (16, 2.5)], 1.0)
    L.fill(pick, hx('#d8b07a'))
    L.fill(L.poly([(16, 2), (21, 3.5), (16, 5)]), hx('#e03a2c'))
    badge(L, 16, 7.5, 2.2, hx('#5a8a2a'))
    return fin(it)


@icon('milkshake')
def _():
    it = new()
    L = it.L
    straw = L.stroke([(19, 9), (24, 1.5)], 1.8)
    it.part(straw, hx('#e8484a'))
    glass = L.poly([(9, 11), (23, 11), (20.5, 27), (11.5, 27)])
    it.part(glass, hx('#f8a8c0'), li=hx('#ffe0ea'))
    L.fill(L.rect(9, 18, 23, 19.4) * glass, hx('#e87898'))
    cream = np.clip(L.ellipse(12, 10, 4, 3) + L.ellipse(16, 8, 5, 3.6) + L.ellipse(20, 10, 4, 3), 0, 1)
    it.part(cream, hx('#fffaf0'))
    badge(L, 16, 4.6, 2.3, hx('#d8202e'))
    base = L.rect(10, 26.5, 22, 28.5, r=1)
    it.part(base, hx('#d8e2ea'))
    return fin(it)


def bun(it, cx=16, cy=17, rx=11, ry=8):
    L = it.L
    b = L.poly(bez((cx - rx, cy + ry * 0.9), (cx - rx * 1.2, cy - ry * 0.4), (cx, cy - ry)) +
               bez((cx, cy - ry), (cx + rx * 1.2, cy - ry * 0.4), (cx + rx, cy + ry * 0.9)) +
               bez((cx + rx, cy + ry * 0.9), (cx, cy + ry * 1.3), (cx - rx, cy + ry * 0.9)))
    it.part(b, hx('#f6eedf'), li=WHITE, sh=hx('#cdbca8'))
    for k in range(5):
        x0 = cx + (k - 2) * rx * 0.28
        L.fill(L.stroke(bez((cx, cy - ry + 1.5), (x0, cy - ry * 0.3), (x0 + (k - 2) * 1.2, cy + ry * 0.2)), 0.6) * b,
               hx('#c8b49c'))
    L.fill(L.circle(cx, cy - ry + 1.8, 1.4), hx('#d8402e'))
    return b


@icon('pork_bun')
def _():
    it = new()
    plate(it, cy=26, rx=12, ry=3)
    bun(it)
    return fin(it, lambda L: steam(L, (9, 23), 9, 6, 0.7))


@icon('ramen')
def _():
    it = new()
    L = it.L
    top = bowl(it, hx('#e8b868'), bowl_col=hx('#2a2a3a'), rim_y=14)
    for k in range(4):
        L.fill(L.stroke(bez((7 + k * 3, 14), (9 + k * 3, 12), (11 + k * 3, 14.5)), 0.7) * top, hx('#fff0b8'))
    egg = L.ellipse(21, 13.6, 3, 1.8)
    it.part(egg, WHITE)
    L.fill(L.ellipse(21, 13.6, 1.4, 1), hx('#ffb030'))
    nar = L.ellipse(11, 13, 2.2, 1.4)
    it.part(nar, WHITE)
    L.fill(L.stroke(ell_pts(11, 13, 1.1, 0.7, a0=0, a1=300, n=12), 0.45), hx('#e86a8a'))
    for dx in (0, 2.4):
        L.fill(L.stroke([(6 + dx, 3), (19 + dx, 13)], 1.3), hx('#c8945a'))
    return fin(it)


@icon('dumplings')
def _():
    it = new()
    L = it.L
    st = L.rect(3, 19, 29, 27, r=2)
    it.part(st, hx('#c8a060'))
    for x in (6, 11, 16, 21, 26):
        L.fill(L.rect(x, 19.5, x + 0.6, 26.5) * st, hx('#8a6a3a'))
    for (x, y) in ((9.5, 16), (22.5, 16), (16, 13)):
        d = L.poly(bez((x - 6, y + 3), (x - 5, y - 4), (x, y - 5)) + bez((x, y - 5), (x + 5, y - 4), (x + 6, y + 3)) + [(x - 6, y + 3)])
        it.part(d, hx('#f2e8d4'), li=WHITE, sh=hx('#c8b49c'))
        for k in (-2, 0, 2):
            L.fill(L.stroke([(x + k, y - 4.5), (x + k * 1.5, y - 1)], 0.5) * d, hx('#c0ac90'))
    return fin(it)


@icon('green_tea')
def _():
    it = new()
    L = it.L
    body = L.poly(bez((7, 13), (7, 26), (16, 27)) + bez((16, 27), (25, 26), (25, 13)))
    it.part(body, hx('#e0e8d8'))
    L.fill(L.rect(7, 17, 25, 18.5) * body, hx('#5a8a5a'))
    top = L.ellipse(16, 13, 9, 2.4)
    it.part(top, hx('#c8d4c0'))
    L.fill(L.ellipse(16, 13.3, 7.6, 1.6), hx('#8ab84a'))
    return fin(it, lambda L: steam(L, (12, 16.5, 20.5), 10, 7, 0.7))


@icon('spicy_udon')
def _():
    it = new()
    L = it.L
    top = bowl(it, hx('#c83a1e'), bowl_col=hx('#f2ece0'), rim_y=14)
    for k in range(3):
        L.fill(L.stroke(bez((8 + k * 4, 14.5), (10 + k * 4, 12), (13 + k * 4, 14.6)), 1.4) * top, hx('#fff2c8'))
    for (x, y) in ((20, 12.6), (23, 14)):
        ch = L.ellipse(x, y, 1.8, 0.9, rot=-30)
        it.part(ch, hx('#e8201e'), contour=False)
    L.fill(L.ellipse(10, 12.8, 1.4, 0.7), hx('#5aa83a'))
    return fin(it, lambda L: steam(L, (11, 20), 9, 6, 0.6))


@icon('bean_chili')
def _():
    it = new()
    L = it.L
    top = bowl(it, hx('#a83a1e'), bowl_col=hx('#d8c0a0'), rim_y=15)
    for (x, y) in ((10, 14.5), (14, 15.6), (18, 14.2), (21, 15.4), (12, 13.6)):
        L.fill(L.ellipse(x, y, 1.3, 0.8) * top, hx('#5a1a14'))
        L.fill(L.ellipse(x - 0.4, y - 0.3, 0.5, 0.3) * top, hx('#d87a5a'))
    sp = L.stroke([(19, 14), (26, 3)], 1.6)
    it.part(np.clip(sp + L.ellipse(26.5, 3, 2, 1.4, rot=-55), 0, 1), hx('#c8ccd8'))
    return fin(it)


@icon('grilled_cheese')
def _():
    it = new()
    L = it.L
    plate(it)
    for (pts, k) in (([(4, 22), (14, 6), (18, 22)], 0), ([(13, 23), (25, 8), (28, 23)], 1)):
        crust = L.poly(pts)
        it.part(crust, hx('#c8823a'))
        inner = L.ero(crust, 1.6)
        L.fill(inner, hx('#f0c070'))
        for (x, y) in ((pts[0][0] + 5, 18), (pts[1][0], 14)):
            L.fill(L.rect(x - 1.5, y, x + 1.5, y + 0.6) * inner, hx('#b86a2a'), 0.8)
    ooze = L.poly([(15, 20), (19, 18), (20, 23), (18.5, 25.5), (17.5, 22.5), (15.5, 23)])
    it.part(ooze, hx('#ffd23a'))
    return fin(it)


@icon('iron_stew')
def _():
    it = new()
    L = it.L
    for x in (3.5, 28.5):
        h = np.clip(L.ellipse(x, 15.5, 2.6, 2.2) - L.ellipse(x, 15.5, 1, 0.8), 0, 1)
        it.part(h, hx('#3a3a46'))
    pot = L.poly(ell_pts(16, 14, 12, 3.6, a0=0, a1=180, n=30)[::-1] + [(28, 14), (26, 25), (6, 25), (4, 14)])
    pot = np.clip(pot + L.ellipse(16, 24.5, 10, 2.5), 0, 1)
    it.part(pot, hx('#4a4a58'), li=hx('#8a8a9e'))
    top = L.ellipse(16, 14, 12, 3.6)
    it.part(top, hx('#8a4a24'))
    for (x, y, c) in ((11, 13.5, '#e8862e'), (16, 14.6, '#f0c47a'), (20.5, 13.2, '#5aa83a'), (14, 12.6, '#a85a3a')):
        L.fill(L.ellipse(x, y, 1.6, 1) * top, hx(c))
    return fin(it, lambda L: steam(L, (11, 20), 9, 6, 0.6))


@icon('hard_eggs')
def _():
    it = new()
    L = it.L
    e1 = L.ellipse(11, 16, 6.5, 8.5, rot=-12)
    it.part(e1, hx('#f6efe2'), li=WHITE)
    e2 = L.ellipse(21.5, 21, 7.5, 5.5)
    it.part(e2, hx('#fbf6ec'))
    L.fill(L.ellipse(21.5, 21, 3.4, 2.6), hx('#ffb424'))
    L.fill(L.ellipse(20.6, 20.2, 1.2, 0.8), hx('#ffe08a'))
    return fin(it)


@icon('hot_dog')
def _():
    it = new()
    L = it.L
    b2 = L.poly(bez((3, 18), (16, 30), (29, 15)) + [(29, 13)] + bez((29, 13), (16, 24), (3, 16)))
    sau = L.poly(bez((2, 15), (16, 25), (30, 11)) + bez((30, 11), (31, 9), (29, 9)) + bez((29, 9), (16, 20), (3, 12)) + bez((3, 12), (1, 13), (2, 15)))
    b1 = L.poly(bez((3, 13), (16, 22), (29, 10)) + [(28, 7.5)] + bez((28, 7.5), (16, 15), (4, 9)))
    it.part(b1, hx('#e8b060'))
    it.part(sau, hx('#c8482e'))
    zig = [(6, 13), (8, 15.5), (10, 14), (12, 17), (14, 16), (16, 18.5), (18, 16.5), (20, 18), (22, 15), (24, 16), (26, 12.5)]
    L.fill(L.stroke(zig, 1.1), hx('#ffd23a'))
    it.part(b2, hx('#d89a4a'))
    return fin(it)


@icon('nachos')
def _():
    it = new()
    L = it.L
    tray = L.poly([(3, 19), (29, 19), (26, 27), (6, 27)])
    it.part(tray, hx('#d8402e'))
    L.fill(L.rect(3, 21, 29, 22.5) * tray, hx('#f0e0c8'), 0.8)
    for (cx, cy, rot) in ((9, 15, -20), (16, 12, 10), (23, 15, 30), (13, 18, 50), (20, 18, -40)):
        ch = L.poly(rot_pts([(cx, cy - 5), (cx + 5, cy + 4), (cx - 5, cy + 4)], rot, cx, cy))
        it.part(ch, hx('#f0c050'))
    cheese = L.poly(bez((7, 15), (16, 10), (25, 15)) + [(24, 18), (21, 17), (19, 20), (16, 17.5), (13, 19.5), (10, 17), (8, 18)])
    it.part(cheese, hx('#ffb424'))
    L.fill(L.circle(17, 13, 1), hx('#4a8a2a'))
    L.fill(L.circle(12, 15, 0.9), hx('#4a8a2a'))
    return fin(it)


@icon('soda')
def _():
    it = new()
    L = it.L
    can = np.clip(L.rect(9, 6, 23, 27, r=1) + L.ellipse(16, 27, 7, 2), 0, 1)
    it.part(can, hx('#d8302e'), li=hx('#ff8a7a'))
    L.fill(L.poly([(9, 15), (23, 12), (23, 15.5), (9, 18.5)]) * can, WHITE)
    L.fill(L.rect(11, 8, 12.5, 25) * can, WHITE, 0.35)
    top = L.ellipse(16, 6, 7, 2)
    it.part(top, hx('#c8ccd8'))
    L.fill(L.ellipse(17.5, 5.8, 2, 0.8), hx('#6a7080'))
    return fin(it)


@icon('popcorn')
def _():
    it = new()
    L = it.L
    box = L.poly([(7, 12), (25, 12), (22.5, 28), (9.5, 28)])
    it.part(box, WHITE)
    X, Y = L.coords()
    stripes = ((((X - 7) // 3) % 2) == 0).astype(np.float32) * box
    L.fill(stripes, hx('#d8302e'))
    corn = np.zeros_like(box)
    for (x, y) in ((9, 11), (12.5, 9), (16, 10), (19.5, 8.5), (23, 11), (11, 6.5), (15, 5.5), (18.5, 5.5), (21.5, 7.5)):
        corn = np.maximum(corn, L.circle(x, y, 2.6))
    it.part(corn, hx('#fff2c8'))
    for (x, y) in ((12.5, 9), (18.5, 5.5)):
        L.fill(L.circle(x + 0.5, y + 0.6, 0.9), hx('#ffcc3a'))
    return fin(it)


@icon('fish_taco')
def _():
    it = new()
    L = it.L
    shell = L.poly(bez((3, 22), (3, 6), (16, 6)) + bez((16, 6), (29, 6), (29, 22)) + bez((29, 22), (16, 15), (3, 22)))
    fill = L.poly(bez((5, 17), (16, 7), (27, 17)) + bez((27, 17), (16, 13), (5, 17)))
    it.part(fill, hx('#e8a050'))
    cab = L.poly([(6, 16), (9, 11), (13, 12), (16, 9), (20, 11), (24, 10), (26, 15), (16, 13.5)])
    it.part(cab, hx('#8ad05a'))
    L.fill(L.stroke([(8, 14), (12, 12.5), (16, 12), (20, 12.5), (24, 13.6)], 0.9), hx('#fff2e0'))
    it.part(np.clip(shell - L.dil(fill, 0.5) * (L.coords()[1] < 16), 0, 1), hx('#f0c45a'))
    return fin(it)


@icon('thermos_soup')
def _():
    it = new()
    L = it.L
    body = L.rect(8, 8, 18, 28, r=2)
    it.part(body, hx('#3a7a5a'), li=hx('#8ad0a8'))
    L.fill(L.rect(8, 15, 18, 19) * body, hx('#e8dcc0'))
    cap = L.rect(7.5, 3, 18.5, 8.5, r=1.5)
    it.part(cap, hx('#c8ccd8'))
    cupm = cup(it, 18, 27, 18, 27, hx('#c8ccd8'), liquid=hx('#e08a3a'), handle=False)
    return fin(it, lambda L: steam(L, (22.5,), 15, 6, 0.7))


@icon('jerky')
def _():
    it = new()
    L = it.L
    pk = L.poly([(6, 7), (24, 4), (27, 25), (9, 28)])
    it.part(pk, hx('#c8a46a'))
    win = L.poly([(9, 12), (23, 10), (24.5, 22), (10.5, 24)])
    L.fill(win, hx('#3a2018'))
    for k, (x0, y0) in enumerate(((11, 13), (13, 15.5), (11.5, 18.5))):
        st = L.poly(rot_pts([(x0, y0), (x0 + 12, y0 - 1.6), (x0 + 12.3, y0 + 1), (x0 + 0.3, y0 + 2.6)], 5 * k, x0 + 6, y0))
        it.part(st * win, hx('#8a3a24'), contour=False)
    L.fill(L.rect(7, 5.8, 25, 8) * pk, hx('#d8402e'))
    return fin(it)


@icon('clam_chowder')
def _():
    it = new()
    L = it.L
    top = bowl(it, hx('#f2e6c8'), bowl_col=hx('#c88a4a'), rim_y=15)
    for (x, y) in ((10, 14.5), (18, 15.5), (14, 13.5)):
        L.fill(L.rect(x - 1, y - 0.8, x + 1, y + 0.8, r=0.3) * top, hx('#e0b880'))
    L.fill(L.circle(21, 13.8, 0.8) * top, hx('#5aa83a'))
    shell = L.poly(bez((20, 9), (23, 4), (27, 6)) + bez((27, 6), (28, 10), (24, 12)) + [(21, 11)])
    it.part(shell, hx('#e8d8c0'))
    for k in range(3):
        L.fill(L.stroke([(21.5, 10.5), (23 + k * 1.5, 5.5 + k * 0.6)], 0.5) * shell, hx('#a89078'))
    return fin(it)


@icon('empanada')
def _():
    it = new()
    L = it.L
    plate(it)
    e = L.poly(bez((3, 20), (5, 6), (16, 6)) + bez((16, 6), (27, 6), (29, 20)) + [(3, 20)])
    it.part(e, hx('#e8a450'), li=hx('#ffd890'))
    for k in range(9):
        x = 4.5 + k * 2.9
        L.fill(L.ellipse(x, 20, 1.6, 1.4), hx('#c8823a'))
        L.fill(L.stroke([(x - 0.6, 19), (x + 0.6, 21)], 0.4), hx('#8a4a1a'))
    L.fill(L.stroke([(11, 12), (13, 10.5)], 0.6), hx('#a8622a'))
    L.fill(L.stroke([(18, 10.5), (20, 12)], 0.6), hx('#a8622a'))
    return fin(it)


# ============================================================ medicine
@icon('bandage')
def _():
    it = new()
    L = it.L
    roll = np.clip(L.ellipse(13, 14, 8, 9) + L.rect(13, 5, 20, 23), 0, 1)
    it.part(roll, hx('#f4efe6'))
    end = L.ellipse(20, 14, 4, 9)
    it.part(end, hx('#e0d8cc'))
    L.fill(L.stroke(ell_pts(20, 14, 2, 5.5, a0=-100, a1=200, n=20), 0.6), hx('#b8ac9c'))
    strip = L.poly(rot_pts([(9, 22), (29, 22), (29, 27), (9, 27)], -25, 19, 24.5))
    it.part(strip, hx('#e8b08a'))
    pad = L.poly(rot_pts([(16, 22.5), (22, 22.5), (22, 26.5), (16, 26.5)], -25, 19, 24.5))
    L.fill(pad, hx('#f8e8d8'))
    L.fill(L.poly(rot_pts([(18.5, 23), (19.5, 23), (19.5, 26), (18.5, 26)], -25, 19, 24.5)), hx('#d8402e'))
    return fin(it)


@icon('tonic')
def _():
    it = new()
    L = it.L
    body = L.poly(bez((10, 14), (8, 28), (16, 28)) + bez((16, 28), (24, 28), (22, 14)) + [(19, 11), (19, 6), (13, 6), (13, 11)])
    it.part(body, hx('#c87a2a'), li=hx('#ffc87a'))
    lab = L.rect(10.5, 17, 21.5, 23.5) * body
    it.part(lab, hx('#f2e8d2'), contour=False)
    L.fill(L.poly([(16, 18), (17, 20), (19.5, 20), (17.5, 21.3), (18.3, 23.3), (16, 22), (13.7, 23.3), (14.5, 21.3),
                   (12.5, 20), (15, 20)]) * lab, hx('#d8402e'))
    cork = L.rect(12.5, 2.5, 19.5, 7, r=1)
    it.part(cork, hx('#b8864a'))
    it.spec(11.8, 16, 0.8, 2.2, 0.8)
    return fin(it)


@icon('vitamin_pack')
def _():
    it = new()
    L = it.L
    card = L.rect(5, 5, 27, 27, r=2)
    it.part(card, hx('#c8d8ea'))
    for i in range(3):
        for j in range(2):
            x, y = 10.5 + i * 5.5, 11.5 + j * 9
            bl = L.ellipse(x, y, 2.4, 3.6)
            it.part(bl, hx('#e8f0f8'), sh_off=0.6)
            L.fill(L.ellipse(x, y, 1.5, 2.6), hx('#ffb424') if (i + j) % 2 else hx('#e85a3a'))
            L.fill(L.ellipse(x - 0.5, y - 1, 0.5, 0.8), WHITE, 0.8)
    return fin(it)


@icon('energy_drink')
def _():
    it = new()
    L = it.L
    can = np.clip(L.rect(10, 4, 22, 27, r=1) + L.ellipse(16, 27, 6, 1.8), 0, 1)
    it.part(can, hx('#2a2a3a'), li=hx('#6a6a8a'))
    bolt = L.poly([(17.5, 7), (12, 17), (16, 17), (14, 25), (20.5, 13.5), (16.5, 13.5), (19, 7)])
    it.part(bolt, hx('#b8f03a'))
    top = L.ellipse(16, 4, 6, 1.8)
    it.part(top, hx('#c8ccd8'))
    return fin(it)


@icon('smelling_salts')
def _():
    it = new()
    L = it.L
    vial = np.clip(L.rect(10, 12, 22, 27, r=3), 0, 1)
    it.part(vial, hx('#8ac8d8'), li=hx('#e0f8ff'))
    L.fill(L.rect(11.5, 19, 20.5, 26) * vial, WHITE, 0.8)
    for (x, y) in ((13.5, 22), (17, 23.5), (15.5, 20.5), (19, 21.5)):
        L.fill(L.rect(x - 0.8, y - 0.8, x + 0.8, y + 0.8) * vial, hx('#c8d8e0'))
    cap = L.rect(11, 8.5, 21, 12.5, r=1)
    it.part(cap, hx('#5a4a6a'))

    def post(L):
        for k, x in enumerate((12, 16, 20)):
            p = bez((x, 7.5), (x + 2.5, 5), (x - 1, 1.5))
            L.fill(L.stroke(p, 1.0), hx('#d8f0a8'), 0.85)
    return fin(it, post)


# ============================================================ key items
def from_pickup(name, scale=1.0):
    im, n = gen_items.PICKUPS[name]()
    if n > 1:
        im = im.crop((0, 0, im.size[0] // n, im.size[1]))
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    out.alpha_composite(im, ((S - im.size[0]) // 2, (S - im.size[1]) // 2 + 1))
    return out


@icon('satchel')
def _():
    return from_pickup('satchel')


@icon('toolbox')
def _():
    return from_pickup('toolbox')


@icon('parcel')
def _():
    return from_pickup('parcel')


@icon('ledger')
def _():
    return from_pickup('ledger')


@icon('postcard')
def _():
    it = new()
    L = it.L
    card = L.poly(rot_pts([(3, 8), (29, 8), (29, 25), (3, 25)], -8, 16, 16.5))
    it.part(card, hx('#f2e6c8'))
    stamp = L.poly(rot_pts([(21, 10.5), (27, 10.5), (27, 17), (21, 17)], -8, 16, 16.5))
    it.part(stamp, hx('#e86a3a'))
    L.fill(L.poly(rot_pts([(22.5, 12), (25.5, 12), (25.5, 15.5), (22.5, 15.5)], -8, 16, 16.5)), hx('#5ab8d8'))
    for k in range(3):
        seg = rot_pts([(16, 17 + k * 2.6), (27, 17 + k * 2.6)], -8, 16, 16.5)
        L.fill(L.stroke(seg, 0.6), hx('#8a7a68'))
    L.fill(L.stroke(rot_pts([(15, 10), (15, 24)], -8, 16, 16.5), 0.6), hx('#8a7a68'))
    sc = rot_pts([(5, 12), (8, 10.5), (11, 13), (13, 11.5)], -8, 16, 16.5)
    L.fill(L.stroke(sc, 0.9), hx('#3a5a8a'))
    return fin(it)


@icon('manifest')
def _():
    it = new()
    L = it.L
    board = L.rect(6, 5, 26, 29, r=1.5)
    it.part(board, hx('#a8784a'))
    paper(it, 8, 8, 24, 27)
    clip = L.rect(11.5, 3, 20.5, 8.5, r=1.5)
    it.part(clip, hx('#c8ccd8'))
    for y in (12, 16.5, 21):
        L.fill(L.rect(9.5, y - 0.8, 11.5, y + 0.8), hx('#3a8a3a'))
    return fin(it)


@icon('count_book')
def _():
    it = new()
    L = it.L
    book(it, hx('#2e5a3e'))
    L.fill(L.text('#', F_COND_B, 13, 17.5, 16.5, anchor='mm'), hx('#e8c860'))
    return fin(it)


@icon('payroll_pages')
def _():
    it = new()
    L = it.L
    paper(it, 5, 6, 22, 27, rot=-10, lines=False)
    paper(it, 9, 5, 26, 27, rot=4)
    L.fill(L.text('$', F_COND_B, 10, 20.5, 9.5, anchor='mm'), hx('#2e7a3e'))
    clip = L.stroke([(12, 3), (12, 10), (14.5, 10), (14.5, 4.5)], 1.0)
    L.fill(clip, hx('#8a92a6'))
    return fin(it)


@icon('cassette')
def _():
    it = new()
    L = it.L
    body = L.rect(3, 8, 29, 25, r=1.5)
    it.part(body, hx('#3a3442'))
    lab = L.rect(5.5, 10, 26.5, 18.5, r=0.8)
    it.part(lab, hx('#f0c45a'), contour=False)
    L.fill(L.rect(5.5, 13, 26.5, 14.4), hx('#d8402e'))
    win = L.rect(10, 14.5, 22, 18, r=1)
    L.fill(win, hx('#1a1620'))
    for x in (12.5, 19.5):
        L.fill(L.circle(x, 16.2, 1.6), hx('#e8e4dc'))
        L.fill(L.circle(x, 16.2, 0.6), hx('#1a1620'))
    btm = L.poly([(8, 25), (10, 21), (22, 21), (24, 25)])
    it.part(btm, hx('#4a4452'))
    return fin(it)


@icon('gate_key')
def _():
    it = new()
    L = it.L
    iron = hx('#7a8292')
    ring = np.clip(L.circle(9, 9, 6) - L.circle(9, 9, 3.6), 0, 1)
    it.part(ring, hx('#c8a050'))
    bow = np.clip(L.circle(12.5, 12.5, 4.6) - L.circle(12.5, 12.5, 2.0), 0, 1)
    it.part(bow, iron)
    shaft = L.poly(rot_pts([(15, 11.2), (29, 11.2), (29, 13.8), (15, 13.8)], 45, 15, 12.5))
    it.part(shaft, iron)
    bits = L.poly(rot_pts([(23, 13.6), (25.5, 13.6), (25.5, 17.5), (23, 17.5)], 45, 15, 12.5))
    bits2 = L.poly(rot_pts([(26.5, 13.6), (28.6, 13.6), (28.6, 16.2), (26.5, 16.2)], 45, 15, 12.5))
    it.part(np.clip(bits + bits2, 0, 1), iron)
    tag = L.poly(rot_pts([(3, 18), (11, 18), (13, 21), (11, 24), (3, 24)], -70, 8, 21))
    it.part(tag, hx('#e8c46a'))
    return fin(it)


@icon('photo')
def _():
    it = new()
    L = it.L
    fr = L.poly(rot_pts([(5, 4), (27, 4), (27, 28), (5, 28)], 6, 16, 16))
    it.part(fr, hx('#f6f0e2'))
    pic = L.poly(rot_pts([(7.5, 6.5), (24.5, 6.5), (24.5, 22), (7.5, 22)], 6, 16, 16))
    L.lin(pic, hx('#f0a070'), hx('#7a4a6a'), (0, 6), (0, 22))
    for (x, h, col) in ((12.5, 9, '#3a2a4a'), (19.5, 10.5, '#4a2a3a')):
        p = rot_pts([(x - 2.5, 22), (x - 2.2, 22 - h + 3), (x + 2.2, 22 - h + 3), (x + 2.5, 22)], 6, 16, 16)
        L.fill(L.poly(p) * pic, hx(col))
        hc = rot_pts([(x, 22 - h + 1.5)], 6, 16, 16)[0]
        L.fill(L.circle(hc[0], hc[1], 2) * pic, hx(col))
    return fin(it)


@icon('eviction_notice')
def _():
    it = new()
    L = it.L
    p = paper(it, 6, 5, 26, 29, rot=-4)
    hd = L.poly(rot_pts([(7.5, 7.5), (24.5, 7.5), (24.5, 12.5), (7.5, 12.5)], -4, 16, 17))
    L.fill(hd, hx('#d8302e'))
    L.fill(L.text('NOTICE', F_COND_B, 5.2, 16, 10.2, anchor='mm') * hd, WHITE)
    nail = L.circle(16, 4.8, 1.5)
    it.part(nail, hx('#9aa2b2'))
    return fin(it)


@icon('leash')
def _():
    it = new()
    L = it.L
    loop = np.clip(L.ellipse(11, 11, 7, 6.5) - L.ellipse(11, 11, 4.8, 4.3), 0, 1)
    it.part(loop, hx('#d8302e'))
    strap = L.stroke(bez((15, 16), (22, 20), (19, 25)), 2.6)
    it.part(strap, hx('#d8302e'))
    clipm = np.clip(L.rect(17, 24, 23, 28, r=1) + L.circle(20, 29, 1.6) - L.circle(20, 29, 0.6), 0, 1)
    it.part(clipm, hx('#c8ccd8'))
    return fin(it)


@icon('arcade_log')
def _():
    it = new()
    L = it.L
    book(it, hx('#5a2a7a'))
    base = L.rect(11, 17, 22, 21, r=1)
    L.fill(base, hx('#1a1620'))
    L.fill(L.stroke([(16.5, 17), (16.5, 11)], 1.4), hx('#c8ccd8'))
    L.fill(L.circle(16.5, 10.5, 2.2), hx('#ff3a6a'))
    L.fill(L.circle(15.8, 9.8, 0.7), WHITE)
    return fin(it)


@icon('courier_sneakers')
def _():
    it = new()
    L = it.L
    sole = L.poly([(4, 22), (27, 22), (29, 24.5), (28, 26.5), (5, 26.5), (3.5, 24.5)])
    upper = L.poly(bez((5, 22), (5, 13), (11, 12)) + [(15, 16), (21, 17)] + bez((21, 17), (28, 18), (28, 22)))
    it.part(upper, hx('#3a7ad8'), li=hx('#9ac8ff'))
    it.part(sole, WHITE)
    L.fill(L.stroke(bez((8, 20), (14, 16), (22, 20)), 1.2), WHITE)
    for k in range(3):
        L.fill(L.stroke([(12 + k * 2.4, 14 + k * 0.8), (14.5 + k * 2.4, 16.5 + k * 0.4)], 0.6), WHITE)
    wing = L.poly([(5, 15), (1, 9), (4, 10), (3, 6.5), (7, 9), (7.5, 6), (10, 11)])
    it.part(wing, hx('#ffd23a'))
    return fin(it)


@icon('champion_wraps')
def _():
    it = new()
    L = it.L
    roll = np.clip(L.ellipse(12, 15, 8, 9) + L.rect(12, 6, 18, 24), 0, 1)
    it.part(roll, hx('#e83a2e'))
    end = L.ellipse(18, 15, 4, 9)
    it.part(end, hx('#c82a22'))
    L.fill(L.stroke(ell_pts(18, 15, 2, 5.5, a0=-100, a1=200, n=20), 0.6), hx('#8a1a14'))
    tail = L.poly([(5, 21), (14, 22), (26, 27), (24, 29.5), (12, 25), (4, 24)])
    it.part(tail, hx('#e83a2e'))
    st = L.poly(star_pts(24, 8, 5, 2.2, 5))
    it.part(st, hx('#ffd23a'))
    return fin(it)


def jacket(it, base, trim, emblem=None):
    L = it.L
    body = L.poly([(9, 6), (23, 6), (27, 10), (27, 27), (5, 27), (5, 10)])
    it.part(body, base)
    for s in (-1, 1):
        sl = L.poly([(16 + s * 10.5, 9), (16 + s * 14, 12), (16 + s * 14.5, 25), (16 + s * 11, 25)])
        it.part(sl, mix(base, INK, 0.12))
        L.fill(L.rect(min(16 + s * 14.5, 16 + s * 11), 23, max(16 + s * 14.5, 16 + s * 11), 25.5), trim)
    L.fill(L.rect(5, 24.5, 27, 27) * body, trim)
    col = L.poly([(11, 6), (16, 12), (21, 6), (19, 5), (16, 8.5), (13, 5)])
    it.part(col, trim)
    L.fill(L.stroke([(16, 12), (16, 25)], 0.7), mix(base, INK, 0.5))
    if emblem:
        emblem(L)


@icon('token_jacket')
def _():
    it = new()

    def em(L):
        m = L.poly(star_pts(11.5, 17, 3.4, 1.5, 5))
        L.fill(L.dil(m, 0.6), INK)
        L.fill(m, hx('#ffd23a'))
    jacket(it, hx('#5a2a7a'), hx('#f0c45a'), em)
    return fin(it)


@icon('lucky_bandana')
def _():
    it = new()
    L = it.L
    tri = L.poly([(3, 9), (29, 9), (16, 27)])
    it.part(tri, hx('#d8302e'))
    for (x, y) in ((9, 12), (16, 12.5), (23, 12), (12.5, 17), (19.5, 17), (16, 22)):
        L.fill(L.ellipse(x, y, 1.6, 1.1, rot=30) * tri, WHITE)
        L.fill(L.circle(x + 0.4, y + 0.2, 0.5) * tri, hx('#d8302e'))
    band = L.rect(3, 7, 29, 10, r=1)
    it.part(band, hx('#b8221e'))
    for s in (-1, 1):
        t = L.poly([(16 + s * 13, 8), (16 + s * 15.5, 4), (16 + s * 15, 10)])
        it.part(t, hx('#d8302e'))
    return fin(it)


# ============================================================ manuals
MAN_COL = {'shoulder': '#3a6ad8', 'rising': '#3a9a4a', 'heel': '#e8862e', 'rapid': '#d8302e', 'sweep': '#2a9a9a',
           'counter': '#7a3ab8', 'giant': '#8a5a34', 'retrieve': '#d85a9a', 'slam': '#6a6a78', 'oath': '#22202c'}


def man_symbol(L, kind, col):
    cx, cy = 16.5, 15.5
    if kind == 'shoulder':
        m = L.poly([(10, 13.5), (18, 13.5), (18, 10.5), (23, 15.5), (18, 20.5), (18, 17.5), (10, 17.5)])
    elif kind == 'rising':
        m = L.poly([(16.5, 8.5), (21.5, 14), (18.5, 14), (18.5, 22), (14.5, 22), (14.5, 14), (11.5, 14)])
    elif kind == 'heel':
        m = L.poly([(16.5, 22.5), (21.5, 17), (18.5, 17), (18.5, 9), (14.5, 9), (14.5, 17), (11.5, 17)])
    elif kind == 'rapid':
        m = np.zeros((L.H, L.W), np.float32)
        for k in range(3):
            x = 10 + k * 4.2
            m = np.maximum(m, L.poly([(x, 10), (x + 4, 15.5), (x, 21), (x + 2, 21), (x + 6, 15.5), (x + 2, 10)]))
    elif kind == 'sweep':
        m = np.clip(L.stroke(bez((10, 12), (12, 21), (21, 19)), 2.2) + L.poly([(19.5, 15.5), (24.5, 19), (19, 22.5)]), 0, 1)
    elif kind == 'counter':
        a = L.poly([(9.5, 12.5), (13, 9.5), (13, 11.5), (22, 11.5), (22, 13.5), (13, 13.5), (13, 15.5)])
        b = L.poly([(23.5, 18.5), (20, 15.5), (20, 17.5), (11, 17.5), (11, 19.5), (20, 19.5), (20, 21.5)])
        m = np.clip(a + b, 0, 1)
    elif kind == 'giant':
        m = np.clip(L.stroke(bez((10, 20), (11, 8), (22, 12)), 2.0) + L.poly([(20, 8.5), (25, 13), (19.5, 15)]) + L.circle(10, 21, 2.4), 0, 1)
    elif kind == 'retrieve':
        m = np.clip(L.stroke(bez((21, 9), (23, 20), (13, 20)), 2.0) + L.poly([(14.5, 16.5), (10, 20), (14.5, 23.5)]) + L.circle(21, 9, 2.2), 0, 1)
    elif kind == 'slam':
        m = L.poly(star_pts(cx, cy, 7.5, 3.4, 8))
    else:  # oath
        m = L.poly(star_pts(cx, cy, 7.5, 3.2, 5))
    L.fill(L.dil(m, 1.0), INK)
    L.fill(m, col)
    L.fill(np.clip(m - L.shift(m, 0, -0.9), 0, 1), mix(col, INK, 0.35))


def make_manual(kind):
    def fn():
        it = new()
        L = it.L
        col = hx(MAN_COL[kind])
        cov = book(it, col)
        plate_m = L.rect(10, 8.5, 23, 22.5, r=1.5)
        sym = hx('#ffe08a') if kind in ('oath', 'slam', 'giant', 'counter') else WHITE
        L.fill(plate_m, mix(col, INK, 0.45))
        man_symbol(L, kind, sym)
        L.fill(L.rect(10, 24, 23, 25.2), hx('#e8c860'), 0.85)
        return fin(it)
    return fn


for _k in MAN_COL:
    REG['manual_' + _k] = make_manual(_k)


# ============================================================ weapons (from weapons2 art)
def weapon_icon(wid):
    def fn():
        im = Image.open(os.path.join(ASSETS, 'weapons2', wid + '.png')).convert('RGBA')
        ang = 0 if wid in ('tire', 'brick') else 38
        r = im.rotate(ang, resample=Image.BICUBIC, expand=True)
        bb = r.getbbox()
        r = r.crop(bb)
        sc = min(27.0 / r.size[0], 27.0 / r.size[1], 1.0)
        nw, nh = max(1, round(r.size[0] * sc)), max(1, round(r.size[1] * sc))
        r = r.resize((nw, nh), Image.LANCZOS)
        out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        out.alpha_composite(r, ((S - nw) // 2, (S - nh) // 2))
        # re-ink silhouette so the line weight matches the other icons
        a = np.asarray(out, np.float32)[..., 3] / 255.0
        big = np.kron(a, np.ones((4, 4), np.float32))
        ring = dilate(big, 1.4 * 4)
        ring = ring.reshape(S, 4, S, 4).mean(axis=(1, 3))
        arr = np.asarray(out, np.float32) / 255.0
        ink = np.array(INK, np.float32) / 255.0
        k = np.clip(ring - arr[..., 3], 0, 1)
        rgb = arr[..., :3] * arr[..., 3:4] + ink * k[..., None]
        al = np.clip(arr[..., 3] + k, 0, 1)
        rgb = np.where(al[..., None] > 0, rgb / np.maximum(al[..., None], 1e-4), 0)
        return Image.fromarray(np.dstack([rgb * 255, al * 255]).round().astype(np.uint8), 'RGBA')
    return fn


for _w in ('wrench', 'baton', 'bat', 'pipe', 'broom', 'chain', 'belt', 'newspaper', 'spatula', 'bottle', 'brick',
           'fish', 'tire', 'road_sign'):
    REG['w_' + _w] = weapon_icon(_w)


@icon('w_crate')
def _():
    it = new()
    L = it.L
    wood = hx('#c8925a')
    front = L.rect(5, 10, 23, 28)
    side = L.poly([(23, 10), (28, 6), (28, 24), (23, 28)])
    top = L.poly([(5, 10), (10, 6), (28, 6), (23, 10)])
    it.part(front, wood)
    it.part(side, mix(wood, hx('#5a3a3a'), 0.35))
    it.part(top, mix(wood, hx('#ffe0b0'), 0.25))
    for y in (15.5, 21.5):
        L.fill(L.rect(5, y, 23, y + 0.6), hx('#7a4a2a'))
    L.fill(L.stroke([(6, 27), (22, 11)], 2.0), hx('#a8723a'))
    L.fill(L.stroke([(6, 27), (22, 11)], 0.5), hx('#7a4a2a'))
    return fin(it)


@icon('w_trash_can')
def _():
    it = new()
    L = it.L
    steel = hx('#8a96a6')
    body = L.poly([(7, 10), (25, 10), (23.5, 28), (8.5, 28)])
    it.part(body, steel)
    for x in (11, 16, 21):
        L.fill(L.stroke([(x, 11.5), (x - (x - 16) * 0.12, 26.5)], 1.0) * body, mix(steel, INK, 0.35))
    lid = L.ellipse(16, 9, 11, 3)
    it.part(lid, mix(steel, hx('#e0e8f0'), 0.25))
    hnd = np.clip(L.rect(13, 4, 19, 7.5, r=1.5) - L.rect(14.5, 5.5, 17.5, 8), 0, 1)
    it.part(hnd, steel)
    return fin(it)


# ============================================================ stats
@icon('stat_hp')
def _():
    return REG['heart']()


@icon('stat_atk')
def _():
    it = new()
    L = it.L
    skin = hx('#e0a070')
    palm = L.rect(7, 10, 25, 26, r=4)
    it.part(palm, skin)
    for k in range(4):
        f = L.rect(7.5 + k * 4.4, 7, 11.5 + k * 4.4, 14, r=2)
        it.part(f, skin)
    th = L.poly([(7, 18), (16, 16), (17, 19.5), (8, 22)])
    it.part(th, skin)
    wrap = L.rect(7, 22, 25, 28, r=1)
    it.part(wrap, hx('#f2ece0'))
    L.fill(L.stroke([(7, 24.5), (25, 25.5)], 0.6), hx('#b8ac9c'))
    return fin(it)


@icon('stat_def')
def _():
    it = new()
    L = it.L
    sh = L.poly(bez((5, 6), (16, 3), (27, 6)) + bez((27, 6), (28, 21), (16, 29)) + bez((16, 29), (4, 21), (5, 6)))
    it.part(sh, hx('#c8a050'))
    inner = L.poly(bez((8, 8), (16, 6), (24, 8)) + bez((24, 8), (25, 20), (16, 25.5)) + bez((16, 25.5), (7, 20), (8, 8)))
    it.part(inner, hx('#3a6ad8'))
    L.fill(L.poly([(16, 6.5), (16, 25.5), (7.8, 19), (8, 8)]) * inner, hx('#2a52b0'))
    st = L.poly(star_pts(16, 15, 4.5, 2, 5))
    L.fill(L.dil(st, 0.6), INK)
    L.fill(st, hx('#f6e6b0'))
    return fin(it)


@icon('stat_agi')
def _():
    it = new()
    L = it.L
    bolt = L.poly([(19, 2.5), (8, 17), (14.5, 17), (11, 29.5), (24, 13), (17.5, 13), (21.5, 2.5)])
    it.part(bolt, hx('#5ad83a'), li=hx('#d8ffa8'))
    for k, y in enumerate((9, 14, 19)):
        L.fill(L.stroke([(2.5, y), (7 - k * 0.5, y)], 1.4), hx('#5ad83a'))
    return fin(it)


@icon('stat_tec')
def _():
    it = new()
    L = it.L
    g = np.zeros((L.H, L.W), np.float32)
    for k in range(8):
        a = k / 8 * math.tau
        g = np.maximum(g, L.poly(rot_pts([(14.5, 2.5), (17.5, 2.5), (18, 7), (14, 7)], math.degrees(a), 16, 16)))
    g = np.clip(g + L.circle(16, 16, 10.5) - L.circle(16, 16, 4.6), 0, 1)
    it.part(g, hx('#9a5ad8'))
    st = L.poly(star_pts(16, 16.3, 4.2, 1.8, 5))
    L.fill(L.dil(st, 0.6), INK)
    L.fill(st, hx('#ffe08a'))
    return fin(it)


# ============================================================ UI glyphs
@icon('heart')
def _():
    it = new()
    L = it.L
    h = L.poly(bez((16, 28), (3, 19), (3, 11)) + bez((3, 11), (3, 4), (10, 4)) + bez((10, 4), (14, 4), (16, 8))
               + bez((16, 8), (18, 4), (22, 4)) + bez((22, 4), (29, 4), (29, 11)) + bez((29, 11), (29, 19), (16, 28)))
    it.part(h, hx('#e8303a'), li=hx('#ff9a9a'), sh_off=2.2)
    L.fill(L.ellipse(9.5, 9.5, 2.4, 1.6, rot=-30), WHITE, 0.9)
    return fin(it)


@icon('star')
def _():
    it = new()
    s = it.L.poly(star_pts(16, 17, 14, 6, 5))
    it.part(s, hx('#ffc83a'), li=hx('#fff0a8'), sh_off=2.0)
    return fin(it)


@icon('check')
def _():
    it = new()
    m = it.L.poly([(3.5, 16), (8, 11.5), (13, 16.5), (24.5, 4.5), (29, 9), (13, 25.5)])
    it.part(m, hx('#4ac84a'), li=hx('#b8ff9a'), sh_off=1.8)
    return fin(it)


@icon('cross')
def _():
    it = new()
    L = it.L
    a = L.poly(rot_pts([(13, 3), (19, 3), (19, 29), (13, 29)], 45, 16, 16))
    b = L.poly(rot_pts([(13, 3), (19, 3), (19, 29), (13, 29)], -45, 16, 16))
    it.part(np.clip(a + b, 0, 1), hx('#e8303a'), li=hx('#ff9a9a'), sh_off=1.8)
    return fin(it)


for _d in ('up', 'down', 'left', 'right'):
    def _mk(d):
        def fn():
            it = new()
            m = arrow_shape(it.L, d)
            it.part(m, hx('#f2e6c8'), sh_off=1.6)
            return fin(it)
        return fn
    REG['arrow_' + _d] = _mk(_d)


@icon('lock')
def _():
    it = new()
    L = it.L
    sh = np.clip(L.rect(9, 3, 23, 18, r=6) - L.rect(12, 6, 20, 18, r=3.5), 0, 1)
    it.part(sh, hx('#a8b0c0'))
    body = L.rect(6, 13, 26, 29, r=2.5)
    it.part(body, hx('#d8a838'), li=hx('#ffe48a'))
    kh = np.clip(L.circle(16, 19.5, 2.3) + L.poly([(14.8, 20), (17.2, 20), (18, 25), (14, 25)]), 0, 1)
    L.fill(kh, hx('#3a2a14'))
    return fin(it)


def gear_mask(L, cx, cy, ro, ri, hole, teeth=8, tw=3.2):
    g = np.zeros((L.H, L.W), np.float32)
    for k in range(teeth):
        a = k * 360 / teeth
        g = np.maximum(g, L.poly(rot_pts([(cx - tw / 2, cy - ro), (cx + tw / 2, cy - ro), (cx + tw / 2 + 0.6, cy - ri + 1),
                                          (cx - tw / 2 - 0.6, cy - ri + 1)], a, cx, cy)))
    return np.clip(g + L.circle(cx, cy, ri) - L.circle(cx, cy, hole), 0, 1)


@icon('gear')
def _():
    it = new()
    it.part(gear_mask(it.L, 16, 16, 14, 10.5, 4), hx('#a8b0c0'), sh_off=1.8)
    return fin(it)


@icon('settings')
def _():
    it = new()
    L = it.L
    it.part(gear_mask(L, 13, 13, 11, 8, 3), hx('#a8b0c0'))
    it.part(gear_mask(L, 23.5, 23.5, 7.5, 5.2, 2, teeth=6, tw=2.6), hx('#f0c45a'))
    return fin(it)


@icon('save')
def _():
    it = new()
    L = it.L
    body = L.poly([(4, 4), (24, 4), (28, 8), (28, 28), (4, 28)])
    it.part(body, hx('#3a6ad8'))
    shutter = L.rect(9, 4, 22, 12)
    it.part(shutter, hx('#c8ccd8'))
    L.fill(L.rect(17.5, 5.5, 20, 10.5), hx('#3a4050'))
    lab = L.rect(8, 16, 24, 28)
    it.part(lab, hx('#f2ece0'))
    for y in (19, 22, 25):
        L.fill(L.rect(10, y, 22, y + 0.6), hx('#8a8a9a'))
    return fin(it)


@icon('journal')
def _():
    it = new()
    L = it.L
    book(it, hx('#8a4a2a'), x0=5, x1=24)
    L.fill(L.rect(8.5, 9, 22, 13), hx('#f2e6c8'))
    L.fill(L.stroke([(10, 11), (20, 11)], 0.6), hx('#6a5a50'))
    pen = L.poly(rot_pts([(14, 26), (30, 26), (30, 28.5), (14, 28.5)], -50, 22, 20))
    it.part(pen, hx('#f0c45a'))
    tip = L.poly(rot_pts([(11.5, 27.25), (14.2, 26), (14.2, 28.5)], -50, 22, 20))
    it.part(tip, hx('#e8d0b0'))
    return fin(it)


@icon('map_pin')
def _():
    it = new()
    L = it.L
    sh = L.ellipse(16, 28, 6, 1.6)
    L.fill(sh, (0, 0, 0), 0.35)
    pin = L.poly(bez((16, 28), (6, 17), (6, 11)) + bez((6, 11), (6, 3), (16, 3)) + bez((16, 3), (26, 3), (26, 11))
                 + bez((26, 11), (26, 17), (16, 28)))
    it.part(pin, hx('#e8303a'), li=hx('#ff9a9a'), sh_off=2.0)
    L.fill(L.circle(16, 11, 3.6), WHITE)
    return fin(it)


@icon('bus')
def _():
    it = new()
    L = it.L
    body = L.rect(5, 4, 27, 26, r=3)
    it.part(body, hx('#f0a830'), li=hx('#ffe08a'))
    win = L.rect(7.5, 7, 24.5, 15, r=1)
    L.lin(win, hx('#a8d8f0'), hx('#5a8ab8'), (0, 7), (0, 15))
    L.fill(L.rect(15.5, 7, 16.5, 15), hx('#3a4050'))
    L.fill(L.rect(10, 4.6, 22, 6.4, r=0.6), hx('#3a3442'))
    for x in (9, 23):
        L.fill(L.circle(x, 20, 1.7), hx('#fff2c8'))
    L.fill(L.rect(12, 19, 20, 21.5, r=0.6), hx('#3a3442'))
    for x in (8, 24):
        w = L.rect(x - 2.5, 25, x + 2.5, 29, r=1)
        it.part(w, hx('#2a2830'))
    return fin(it)


@icon('cash')
def _():
    it = new()
    L = it.L
    for k in (1, 0):
        y = 9 + k * 6
        b = L.poly(rot_pts([(4, y), (26, y), (26, y + 12), (4, y + 12)], -10 + k * 8, 15, y + 6))
        it.part(b, hx('#6aac5a'), li=hx('#c8ecb0'))
        inner = L.ero(b, 1.8)
        L.fill(np.clip(inner - L.ero(inner, 0.6), 0, 1), hx('#2e6a2e'))
    L.fill(L.text('$', F_BUNGEE, 9, 15.5, 15.5, anchor='mm'), hx('#2a5228'))
    c = badge(L, 25, 24, 4.5, hx('#f2c040'))
    return fin(it)


@icon('xp')
def _():
    it = new()
    L = it.L
    st = L.poly(star_pts(16, 16, 14.5, 7, 8, rot=22.5))
    it.part(st, hx('#5ad8e8'), li=hx('#d8fbff'))
    t = L.text('XP', F_BUNGEE, 9.5, 16.3, 16.6, anchor='mm')
    L.fill(L.dil(t, 0.9), INK)
    L.fill(t, WHITE)
    return fin(it)


@icon('level')
def _():
    it = new()
    L = it.L
    sh = L.poly([(4, 4), (28, 4), (28, 21), (16, 29), (4, 21)])
    it.part(sh, hx('#d8a838'), li=hx('#ffe48a'))
    for k in range(2):
        y = 9 + k * 6
        ch = L.poly([(9, y + 5), (16, y), (23, y + 5), (23, y + 8.5), (16, y + 3.5), (9, y + 8.5)])
        L.fill(L.dil(ch, 0.6), INK)
        L.fill(ch, WHITE)
    return fin(it)


def quest_icon(mark):
    def fn():
        it = new()
        L = it.L
        scroll(it, mark)
        if mark == 'new':
            m = np.clip(L.rect(19.5, 13, 23.5, 25, r=1.2) + L.circle(21.5, 28.5, 2.2), 0, 1)
            col = hx('#ffb424')
        elif mark == 'active':
            m = L.poly([(17, 15), (24, 21), (17, 27)])
            col = hx('#3ab8e8')
        else:
            m = L.poly([(15.5, 22), (18, 19.5), (20, 21.5), (25.5, 15), (28, 17.5), (20, 26.5)])
            col = hx('#4ac84a')
        L.fill(L.dil(m, 1.4), INK)
        sh, b, li, _ = tones(col)
        L.fill(m, b)
        L.fill(np.clip(m - L.shift(m, -0.8, -0.8), 0, 1), sh)
        return fin(it)
    return fn


REG['quest_new'] = quest_icon('new')
REG['quest_active'] = quest_icon('active')
REG['quest_done'] = quest_icon('done')


@icon('food')
def _():
    it = new()
    L = it.L
    plate(it, cy=20, rx=13, ry=8)
    fk = np.clip(L.poly(rot_pts([(15, 4), (17, 4), (17, 28), (15, 28)], -35, 16, 16)), 0, 1)
    kn = np.clip(L.poly(rot_pts([(15, 4), (18, 4), (17.5, 28), (15, 28)], 35, 16, 16)), 0, 1)
    it.part(fk, hx('#c8ccd8'))
    it.part(kn, hx('#c8ccd8'))
    return fin(it)


@icon('skill')
def _():
    it = new()
    L = it.L
    book(it, hx('#d8302e'))
    st = L.poly(star_pts(17, 16, 6, 2.6, 5))
    L.fill(L.dil(st, 0.8), INK)
    L.fill(st, hx('#ffd23a'))
    return fin(it)


@icon('key_item')
def _():
    it = new()
    L = it.L
    ring = np.clip(L.circle(11, 11, 7) - L.circle(11, 11, 4.6), 0, 1)
    it.part(ring, hx('#c8ccd8'))
    brass = hx('#e0b448')
    bow = np.clip(L.circle(16, 16, 4) - L.circle(16, 16, 1.7), 0, 1)
    it.part(bow, brass)
    shaft = L.poly(rot_pts([(19, 14.9), (29, 14.9), (29, 17.1), (19, 17.1)], 40, 19, 16))
    it.part(shaft, brass)
    bit = L.poly(rot_pts([(25, 17), (27.5, 17), (27.5, 20), (25, 20)], 40, 19, 16))
    it.part(bit, brass)
    return fin(it)


def main(ids=None):
    os.makedirs(OUT, exist_ok=True)
    want = [os.path.basename(p)[:-4] for p in sorted(glob.glob(os.path.join(ASSETS, 'icons', '*.png')))]
    missing = [i for i in want if i not in REG]
    if missing:
        print('MISSING icon drawers:', missing)
    for i in (ids or want):
        if i in REG:
            im = REG[i]()
            assert im.size == (S, S), (i, im.size)
            save(im, os.path.join(OUT, i + '.png'))
    print('icons2:', len([i for i in want if i in REG]), '/', len(want))


if __name__ == '__main__':
    main(sys.argv[1:] or None)
