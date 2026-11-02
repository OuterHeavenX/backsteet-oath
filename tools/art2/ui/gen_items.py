#!/usr/bin/env python3
"""v2 held weapons + world pickups at density 2 -> game/assets/{weapons2,pickups2}/.

Weapons point RIGHT with the grip near the left end (same convention as v1); `grip`/`tip`
are in texels of the 2x image. Pickups mirror the v1 frame layout at 2x. Inked (2 tx outer
contour, 1 tx inner part contours) and cel-shaded with the key light from the top-left.

Usage: python3 tools/art2/ui/gen_items.py
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vec import Layer, hx, mix, tones, strip, save, bez, ell_pts, star_pts, F_COND_B, INK, ASSETS  # noqa: E402

WHITE = (255, 255, 255)
W_OUT = os.path.join(ASSETS, 'weapons2')
P_OUT = os.path.join(ASSETS, 'pickups2')


class Item:
    """Part-based inked drawing on one layer."""

    def __init__(self, w, h, ss=6):
        self.L = Layer(w, h, ss)

    def part(self, m, base, contour=True, light=(-0.6, -1), sh_off=1.6, li_off=1.0, ink=None, li=None, sh=None):
        L = self.L
        t = tones(base)
        if contour:
            L.fill(np.clip(L.dil(m, 1.0) - m, 0, 1), ink or t[3])
        L.cel(m, base, light=light, sh_off=sh_off, li_off=li_off, li=li, sh=sh)
        return m

    def line(self, pts, w, col, clip=None, a=1.0):
        m = self.L.stroke(pts, w)
        if clip is not None:
            m = m * clip
        self.L.fill(m, col, a)
        return m

    def spec(self, x, y, rx, ry, a=0.9, rot=0):
        self.L.fill(self.L.ellipse(x, y, rx, ry, rot), (255, 252, 240), a)

    def done(self, ink=INK, w=2.0):
        self.L.outline(w, ink)
        return self.L.image()


# ================================================================ weapons
def w_bat():
    it = Item(60, 12)
    L = it.L
    wood = hx('#cf9a5e')
    body = L.poly([(9, 4.6), (30, 3.6), (50, 2.2), (55, 2.4), (57.5, 4), (58, 6), (57.5, 8), (55, 9.6), (50, 9.8),
                   (30, 8.4), (9, 7.4)])
    it.part(body, wood)
    for y0, x0, x1 in ((4.6, 30, 52), (7.2, 34, 54)):
        it.line(bez((x0, y0), ((x0 + x1) / 2, y0 + 0.4), (x1, y0 - 0.3)), 0.5, mix(wood, hx('#7a4a2a'), 0.6), body, 0.6)
    tape = L.rect(9, 4.2, 22, 7.8)
    it.part(tape, hx('#3b3348'))
    for x in range(11, 22, 3):
        it.line([(x, 4.2), (x + 1.6, 7.8)], 0.6, hx('#5c5470'), tape)
    knob = L.ellipse(6.5, 6, 3.2, 3.6)
    it.part(knob, wood)
    it.spec(48, 4.2, 4.5, 0.8, 0.55)
    return it.done(), (14, 6), (57, 6)


def w_baton():
    it = Item(36, 10)
    L = it.L
    shaft = L.rect(4, 3, 34, 7, r=2)
    it.part(shaft, hx('#3a3a46'))
    grip = L.rect(4, 2.6, 15, 7.4, r=1.5)
    it.part(grip, hx('#24222c'))
    for x in range(6, 15, 2):
        it.line([(x, 2.8), (x, 7.2)], 0.5, hx('#4a4858'), grip)
    cap = L.ellipse(3.6, 5, 2.2, 2.6)
    it.part(cap, hx('#2a2832'))
    it.spec(26, 4.0, 6, 0.6, 0.6)
    return it.done(), (9, 5), (34, 5)


def w_belt():
    it = Item(56, 10)
    L = it.L
    pts_top, pts_bot = [], []
    for i in range(41):
        x = 5 + 43 * i / 40
        y = 5 + 1.6 * math.sin(i / 40 * math.pi * 2.2)
        pts_top.append((x, y - 2.0))
        pts_bot.append((x, y + 2.0))
    strap = L.poly(pts_top + pts_bot[::-1])
    it.part(strap, hx('#6a3e2a'))
    for i in range(4, 40, 5):
        x = 5 + 43 * i / 40
        y = 5 + 1.6 * math.sin(i / 40 * math.pi * 2.2)
        st = L.circle(x, y, 1.15)
        it.part(st, hx('#c8ccd8'), sh_off=0.6, li_off=0.5)
    buckle_o = L.rect(46, 1.2, 54.5, 8.8, r=1.2)
    buckle_i = L.rect(48, 3.0, 52.5, 7.0, r=0.6)
    it.part(np.clip(buckle_o - buckle_i, 0, 1), hx('#d8b858'))
    it.line([(47, 5), (52, 5)], 0.9, hx('#a88838'))
    wrap = L.rect(2, 2.6, 8, 7.4, r=1)
    it.part(wrap, hx('#4a2c20'))
    return it.done(), (5, 5), (54, 5)


def w_bottle():
    it = Item(24, 12)
    L = it.L
    glass = hx('#3f8f5a')
    body = L.poly(bez((10, 2.4), (13, 1.6), (21, 2.2)) + [(22.5, 3.5), (22.5, 8.5)] + bez((21, 9.8), (13, 10.4), (10, 9.6))
                  + [(7, 7.2), (2.2, 7), (2.2, 5), (7, 4.8)])
    it.part(body, glass, li=hx('#9ee0b0'))
    lab = L.rect(13, 3, 19, 9) * body
    it.part(lab, hx('#e8dcb8'))
    it.line([(14, 5), (18, 5)], 0.6, hx('#b04030'), lab)
    it.line([(14, 7), (17.5, 7)], 0.5, hx('#7a6a50'), lab)
    cap = L.rect(1.2, 4.6, 3.2, 7.4, r=0.5)
    it.part(cap, hx('#c8b048'))
    it.spec(20.5, 4.4, 1.2, 0.6, 0.85)
    it.spec(9, 4.6, 1.5, 0.45, 0.7)
    return it.done(), (5, 6), (22, 6)


def w_brick():
    it = Item(20, 14)
    L = it.L
    face = L.poly([(2.5, 3.5), (15, 2.5), (17.5, 4.5), (17.5, 11.5), (5, 12), (2.5, 10.5)])
    it.part(face, hx('#b5523a'))
    top = L.poly([(2.5, 3.5), (15, 2.5), (17.5, 4.5), (5, 5.5)])
    it.part(top, hx('#d47658'), contour=True)
    for x, y in ((7, 8), (12, 9.5), (14, 7)):
        L.fill(L.circle(x, y, 0.8) * face, hx('#7a3020'), 0.8)
    L.fill(L.circle(9.5, 10.5, 0.5) * face, hx('#e8c8a0'), 0.8)
    return it.done(), (9, 7), (18, 7)


def w_broom():
    it = Item(80, 16)
    L = it.L
    stick = L.rect(3, 6.6, 66, 9.4, r=1.4)
    it.part(stick, hx('#c99860'))
    for x0 in (14, 34, 50):
        it.line([(x0, 7.6), (x0 + 9, 7.3)], 0.45, hx('#8a5a32'), stick, 0.6)
    brace = L.poly([(58, 7.2), (66, 3.4), (67.5, 4.6), (61, 8.4)])
    it.part(brace, hx('#9aa2b2'))
    block = L.rect(64, 1.5, 72, 14.5, r=1)
    it.part(block, hx('#7a3c26'))
    bristle = L.poly([(71, 1.8), (78.5, 0.8), (79, 15.2), (71, 14.2)])
    it.part(bristle, hx('#d8c070'))
    for y in np.linspace(2.5, 13.5, 8):
        it.line([(72, y), (78.4, y + (y - 8) * 0.12)], 0.45, hx('#9a8040'), bristle, 0.8)
    cap = L.ellipse(3.4, 8, 1.8, 2)
    it.part(cap, hx('#d84a3a'))
    return it.done(), (10, 8), (76, 8)


def w_chain():
    it = Item(80, 12)
    L = it.L
    steel = hx('#a8b0c0')
    for i in range(12):
        x = 9 + i * 5.9
        y = 6 + 0.9 * math.sin(i * 0.9)
        if i % 2 == 0:
            o = L.ellipse(x, y, 4.0, 2.7)
            inn = L.ellipse(x, y, 2.1, 0.9)
        else:
            o = L.ellipse(x, y, 4.0, 1.5)
            inn = L.ellipse(x, y, 2.6, 0.35)
        it.part(np.clip(o - inn, 0, 1), steel, sh_off=0.9, li_off=0.7, ink=hx('#1c2030'))
    wrap = L.rect(1.5, 2.8, 8.5, 9.2, r=1.2)
    it.part(wrap, hx('#3a3442'))
    for x in (3.5, 5.5, 7.5):
        it.line([(x, 3), (x - 0.8, 9)], 0.5, hx('#5a5468'), wrap)
    return it.done(hx('#141824')), (5, 6), (77, 6)


def w_fish():
    it = Item(32, 16)
    L = it.L
    body = L.poly(bez((7, 8), (12, 2.5), (22, 3.2)) + bez((22, 3.2), (29, 4.5), (30.5, 8))
                  + bez((30.5, 8), (29, 11.5), (22, 12.6)) + bez((22, 12.6), (12, 13.4), (7, 8)))
    it.part(body, hx('#7fa8b8'), li=hx('#d8eef2'))
    back = L.poly(bez((8, 7.5), (13, 3), (22, 3.4)) + bez((22, 3.4), (28, 4.5), (30, 7.4)) + [(24, 6.2), (12, 7.2)]) * body
    L.fill(back, hx('#2e5a6a'))
    for x in (13, 16.5, 20, 23.5):
        it.line(bez((x, 4.2), (x + 1.2, 5.2), (x, 6.2)), 0.6, hx('#183842'), back)
    belly = L.poly(bez((10, 9.4), (18, 12.8), (27, 10.2)) + [(27, 11.8), (18, 13.2)]) * body
    L.fill(belly, hx('#eef4f2'), 0.8)
    tail = L.poly([(8, 8), (2, 2.8), (3.8, 8), (2, 13.2)])
    it.part(tail, hx('#5a8a9c'))
    gill = it.line(bez((25, 5), (23.6, 8), (25, 11)), 0.6, hx('#2a4a58'), body)
    eye = L.circle(27.3, 7.0, 1.4)
    L.fill(eye, (250, 250, 240))
    L.fill(L.circle(27.6, 7.0, 0.7), INK)
    it.spec(18, 5.2, 3, 0.5, 0.6)
    return it.done(hx('#16303a')), (6, 8), (30, 8)


def w_newspaper():
    it = Item(36, 12)
    L = it.L
    roll = L.rect(3, 2.8, 33, 9.2, r=2.4)
    it.part(roll, hx('#e8e0cc'), li=hx('#fffaf0'))
    for x0, x1, y in ((8, 20, 4.8), (10, 27, 6.4), (22, 30, 4.8), (7, 15, 7.6)):
        it.line([(x0, y), (x1, y)], 0.5, hx('#8a8478'), roll, 0.7)
    head = L.rect(18, 3.4, 24, 5.6) * roll
    L.fill(head, hx('#3a3440'), 0.85)
    spiral = L.ellipse(33, 6, 1.8, 3.2)
    it.part(spiral, hx('#d8d0bc'))
    it.line(ell_pts(33, 6, 1.0, 1.9, a0=-90, a1=200, n=20), 0.45, hx('#7a7468'), spiral)
    band = L.rect(11, 2.6, 13.2, 9.4)
    it.part(band, hx('#c84a3a'))
    return it.done(), (7, 6), (34, 6)


def w_pipe():
    it = Item(64, 10)
    L = it.L
    lead = hx('#8e96a6')
    shaft = L.rect(3, 3, 58, 7)
    it.part(shaft, lead)
    for x0 in (2, 54):
        col = L.rect(x0, 1.6, x0 + 7, 8.4, r=0.8)
        it.part(col, mix(lead, hx('#c8a060'), 0.25))
        for x in np.arange(x0 + 1.2, x0 + 7, 1.4):
            it.line([(x, 1.8), (x, 8.2)], 0.35, hx('#4a4e5a'), col, 0.7)
    L.fill(L.rect(14, 4, 46, 5) * shaft, hx('#e0e6f0'), 0.6)
    L.fill(L.circle(30, 6, 0.8), hx('#7a4a30'), 0.6)
    return it.done(hx('#161a24')), (9, 5), (61, 5)


def w_road_sign():
    it = Item(88, 28)
    L = it.L
    pole = L.rect(3, 12.2, 66, 15.8, r=1)
    it.part(pole, hx('#9aa2ae'))
    for x in range(8, 64, 6):
        L.fill(L.circle(x, 14, 0.55) * pole, hx('#4a4e58'), 0.8)
    plate = L.rect(56, 2, 86, 26, r=2)
    it.part(plate, hx('#f08a1e'))
    inner = L.rect(58.5, 4.5, 83.5, 23.5, r=1.2)
    L.fill(np.clip(inner - L.ero(inner, 0.9), 0, 1), hx('#2a1a14'))
    txt = L.text('DETOUR', F_COND_B, 8.6, 71, 12.2, anchor='mm')
    L.fill(txt * inner, hx('#2a1a14'))
    arr = L.poly([(63, 18.6), (76, 18.6), (76, 16.8), (80.5, 19.6), (76, 22.4), (76, 20.6), (63, 20.6)])
    L.fill(arr, hx('#2a1a14'))
    for x, y in ((58, 14), (84, 14)):
        L.fill(L.circle(x, y, 0.9), hx('#c8ccd4'))
    L.fill(L.poly([(60, 3), (70, 3), (60, 8)]) * plate, (255, 255, 255), 0.25)
    return it.done(), (10, 14), (86, 14)


def w_spatula():
    it = Item(36, 14)
    L = it.L
    handle = L.rect(2, 5, 17, 9, r=2)
    it.part(handle, hx('#7a4628'))
    L.fill(L.circle(5, 7, 0.9), INK)
    neck = L.rect(16, 6, 23, 8)
    it.part(neck, hx('#b8c0cc'))
    blade = L.poly([(22, 3.2), (34, 1.6), (34.5, 12.4), (22, 10.8)])
    it.part(blade, hx('#c8d0dc'))
    for y in (5.0, 7.0, 9.0):
        slot = L.rect(25, y - 0.45, 32, y + 0.45, r=0.4)
        L.fill(slot, hx('#3a4050'))
    it.spec(28, 3.2, 3, 0.5, 0.7)
    return it.done(), (8, 7), (34, 7)


def w_tire():
    it = Item(36, 36)
    L = it.L
    o = L.circle(18, 18, 16.5)
    i = L.circle(18, 18, 7.5)
    rub = np.clip(o - i, 0, 1)
    it.part(rub, hx('#34303a'), sh_off=2.4, li_off=1.2, li=hx('#6a6676'))
    for k in range(18):
        a = k / 18 * math.tau
        x0, y0 = 18 + math.cos(a) * 13.5, 18 + math.sin(a) * 13.5
        x1, y1 = 18 + math.cos(a + 0.12) * 16.4, 18 + math.sin(a + 0.12) * 16.4
        it.line([(x0, y0), (x1, y1)], 0.8, hx('#18161e'), rub, 0.9)
    rim = np.clip(L.circle(18, 18, 9.2) - L.circle(18, 18, 4.5), 0, 1)
    it.part(rim, hx('#a8b0bc'))
    for k in range(5):
        a = k / 5 * math.tau
        L.fill(L.circle(18 + math.cos(a) * 6.8, 18 + math.sin(a) * 6.8, 0.8), hx('#4a5060'))
    it.spec(11, 8, 4, 1.2, 0.35, rot=-40)
    return it.done(hx('#121016')), (18, 18), (33, 18)


def w_wrench():
    it = Item(32, 14)
    L = it.L
    steel = hx('#aab2c0')
    handle = L.poly([(2.5, 5.4), (20, 5.6), (20, 8.4), (2.5, 8.6)])
    it.part(handle, steel)
    L.fill(L.rect(5, 6.2, 16, 7.8, r=0.8) * handle, hx('#7a8292'), 0.9)
    head = L.poly([(19, 3.6), (25, 1.2), (30.5, 2.2), (30.5, 5.2), (26.5, 5.2), (26.5, 8.8), (30.5, 8.8), (30.5, 11.8),
                   (25, 12.8), (19, 10.4)])
    it.part(head, steel)
    knurl = L.ellipse(23, 7, 1.6, 2.6)
    it.part(knurl, hx('#7a8292'))
    for y in (5.6, 7, 8.4):
        it.line([(21.6, y), (24.4, y)], 0.4, hx('#3a4050'), knurl)
    hole = L.circle(4.6, 7, 1.0)
    L.fill(hole, hx('#2a2e3a'))
    it.spec(12, 5.9, 5, 0.4, 0.75)
    return it.done(hx('#161a24')), (9, 7), (30, 7)


def w_shovel():
    """Long-handled round-point steel shovel (content 1.2, the Moles' tool)."""
    it = Item(84, 24)
    L = it.L
    handle = L.rect(3, 10.4, 60, 13.6, r=1.5)
    it.part(handle, hx('#c08a52'))
    for x0 in (12, 30, 46):
        it.line([(x0, 11.4), (x0 + 10, 11.1)], 0.45, hx('#7a4a2a'), handle, 0.6)
    cap = L.rect(2, 9.8, 7, 14.2, r=1.2)
    it.part(cap, hx('#3a3442'))
    ferrule = L.poly([(58, 9.6), (66, 8.4), (66, 15.6), (58, 14.4)])
    it.part(ferrule, hx('#7a8292'))
    for x in (60.5, 63):
        L.fill(L.rect(x, 9.4, x + 0.6, 14.6) * ferrule, hx('#3a4050'), 0.8)
    blade = L.poly(bez((64, 3), (74, 1.4), (78, 5)) + bez((78, 5), (83.4, 12), (78, 19)) + bez((78, 19), (74, 22.6), (64, 21))
                   + [(66.5, 14.5), (66.5, 9.5)])
    it.part(blade, hx('#a8b2c2'), li=hx('#e8f0f8'))
    L.fill(L.stroke(bez((68, 6), (75.5, 12), (68, 18)), 0.7) * blade, hx('#5a6474'), 0.8)
    L.fill(L.poly([(78, 9), (82.6, 12), (78, 15)]) * blade, hx('#8a5a3a'), 0.45)
    it.spec(72, 5.4, 3.2, 0.7, 0.8, rot=-15)
    return it.done(hx('#161a24')), (12, 12), (80, 12)


WEAPONS = {
    'bat': w_bat, 'baton': w_baton, 'belt': w_belt, 'bottle': w_bottle, 'brick': w_brick, 'broom': w_broom,
    'chain': w_chain, 'fish': w_fish, 'newspaper': w_newspaper, 'pipe': w_pipe, 'road_sign': w_road_sign,
    'spatula': w_spatula, 'tire': w_tire, 'wrench': w_wrench, 'shovel': w_shovel,
}


# ================================================================ pickups
def p_bill():
    it = Item(24, 16)
    L = it.L
    paper = L.poly([(2.5, 5), (20, 2.5), (21.5, 10.5), (4, 13.5)])
    it.part(paper, hx('#7cb86a'), li=hx('#c8ecb0'))
    inner = L.poly([(4.6, 6.2), (18.6, 4.2), (19.6, 9.6), (5.6, 12)])
    L.fill(np.clip(inner - L.ero(inner, 0.6), 0, 1), hx('#3a6a34'), 0.9)
    oval = L.ellipse(12, 8, 2.8, 2.2, rot=-9)
    it.part(oval, hx('#a8d890'), contour=False)
    L.fill(L.text('$', F_COND_B, 5, 12.1, 8.2, anchor='mm'), hx('#2a5228'))
    for x, y in ((6.6, 7), (17.5, 9.4)):
        L.fill(L.circle(x, y, 0.8), hx('#3a6a34'))
    return it.done(hx('#16301a')), 1


def p_cash_stack():
    it = Item(28, 20)
    L = it.L
    for k in range(3, -1, -1):
        y = 6 + k * 2.2
        sheet = L.poly([(3, y), (22.5, y - 2.5), (25, y + 4), (5.5, y + 6.5)])
        it.part(sheet, hx('#78b466') if k else hx('#86c274'), li=hx('#c8ecb0'))
    band = L.poly([(11, 3.6), (15, 3.1), (17.5, 15.6), (13.5, 16.2)])
    it.part(band, hx('#e8dcb0'))
    L.fill(L.text('$', F_COND_B, 5, 18.8, 7.6, anchor='mm'), hx('#2a5228'))
    return it.done(hx('#16301a')), 1


def p_coin():
    frames = []
    for f, sx in enumerate((1.0, 0.6, 0.18, 0.6)):
        it = Item(16, 16)
        L = it.L
        gold = hx('#f2c040')
        rim = L.ellipse(8, 8, 6.4 * sx + 0.4, 6.4)
        it.part(rim, hx('#d89a28'), light=(-1, -1) if f != 3 else (1, -1))
        if sx > 0.3:
            face = L.ellipse(8, 8, 4.6 * sx, 4.7)
            it.part(face, gold, light=(-1, -1) if f != 3 else (1, -1))
            star = L.text('$', F_COND_B, 7, 8, 8.4, anchor='mm')
            if sx < 0.9:
                X, Y = L.coords()
                star = star * 0
                L.fill(L.rect(8 - 0.6 * sx * 2, 5.2, 8 + 0.6 * sx * 2, 10.8), hx('#a86a18'), 0.8)
            else:
                L.fill(star, hx('#a86a18'))
            it.spec(8 - 2.4 * sx, 5.2, 1.4 * sx + 0.2, 0.9, 0.85)
        else:
            L.fill(L.rect(7.2, 2.2, 8.8, 13.8), hx('#ffe080'), 0.7)
        frames.append(it.done(hx('#3a2208'), 1.6))
    return strip(frames), 4


def p_heal_bun():
    it = Item(24, 20)
    L = it.L
    bun = L.poly(bez((2.5, 16.5), (1.0, 8.5), (12, 5.5)) + bez((12, 5.5), (23.0, 8.5), (21.5, 16.5))
                 + bez((21.5, 16.5), (12, 18.2), (2.5, 16.5)))
    it.part(bun, hx('#f4ecdc'), li=(255, 255, 250), sh=hx('#cfbfae'))
    for k in range(5):
        x0 = 12 + (k - 2) * 2.4
        it.line(bez((12, 6.2), (x0 + (k - 2) * 1.2, 8.5), (x0 + (k - 2) * 2.0, 11.5)), 0.5, hx('#c8b49c'), bun, 0.9)
    L.fill(L.circle(12, 6.6, 1.5), hx('#d8402e'))
    L.outline(2.0, INK)
    for x in (7, 17):
        steam = L.stroke(bez((x, 4.4), (x - 1.6, 2.8), (x, 1.0)), 0.8)
        L.fill(steam, (255, 255, 255), 0.75)
    return L.image(), 1


def p_key():
    it = Item(20, 12)
    L = it.L
    brass = hx('#e0b448')
    bow = np.clip(L.circle(5, 6, 4.2) - L.circle(5, 6, 1.6), 0, 1)
    it.part(bow, brass)
    shaft = L.rect(8.5, 4.9, 18, 7.1)
    it.part(shaft, brass)
    bits = L.poly([(13, 7), (14.4, 7), (14.4, 9.6), (13, 9.6)]) + L.poly([(16, 7), (17.8, 7), (17.8, 10.2), (16, 10.2)])
    it.part(np.clip(bits, 0, 1), brass)
    it.spec(4, 3.4, 1.4, 0.6, 0.8, rot=-30)
    return it.done(hx('#3a2408')), 1


def p_ledger():
    it = Item(24, 20)
    L = it.L
    pages = L.poly([(4, 4.5), (20.5, 3), (21.5, 16.5), (5, 18)])
    it.part(pages, hx('#efe6cc'))
    cover = L.poly([(3, 3.5), (19.5, 2), (20.5, 15.5), (4, 17)])
    it.part(cover, hx('#8a2e2a'))
    spine = L.poly([(3, 3.5), (6, 3.2), (7, 16.7), (4, 17)])
    it.part(spine, hx('#5a1c1a'))
    lab = L.poly([(10, 6), (17, 5.4), (17.4, 9), (10.4, 9.6)])
    it.part(lab, hx('#e8dcb0'))
    for y in (7.2, 8.3):
        it.line([(11, y), (16.4, y - 0.5)], 0.4, hx('#6a5a50'), lab)
    return it.done(), 1


def p_parcel():
    it = Item(24, 24)
    L = it.L
    paper = hx('#c8955e')
    top = L.poly([(3, 8), (12, 3.5), (21, 8), (12, 12.5)])
    left = L.poly([(3, 8), (12, 12.5), (12, 21.5), (3, 17)])
    right = L.poly([(12, 12.5), (21, 8), (21, 17), (12, 21.5)])
    it.part(left, mix(paper, hx('#7a4a30'), 0.25), sh_off=0.8)
    it.part(right, mix(paper, hx('#5a3a3a'), 0.4), sh_off=0.8)
    it.part(top, mix(paper, hx('#ffe8c0'), 0.15), sh_off=0.8)
    string = hx('#f0e8d8')
    for seg in ([(7.5, 5.8), (16.5, 10.2)], [(16.5, 5.8), (7.5, 10.2)], [(7.5, 10.2), (7.5, 19.2)], [(16.5, 10.2), (16.5, 19.2)]):
        it.line(seg, 0.9, string)
    L.fill(L.ellipse(12, 8, 2.2, 1.2), string)
    lab = L.poly([(13.5, 13.4), (18.6, 10.9), (18.6, 13.6), (13.5, 16.1)])
    it.part(lab, hx('#f4eedc'), contour=False)
    return it.done(), 1


def p_satchel():
    it = Item(28, 24)
    L = it.L
    leather = hx('#8a5232')
    strap = np.clip(L.stroke(bez((6, 9), (14, -6), (22, 9)), 2.2) - L.rect(0, 9, 28, 24), 0, 1)
    it.part(strap, mix(leather, INK, 0.25))
    bag = L.rect(3, 8, 25, 21.5, r=2.5)
    it.part(bag, leather)
    flap = L.poly([(3, 8)] + bez((3, 8), (14, 7), (25, 8)) + [(25, 14)] + bez((25, 14), (14, 16.5), (3, 14)))
    it.part(flap, mix(leather, hx('#c88a5a'), 0.25))
    buckle = L.rect(12, 13, 16, 17, r=0.6)
    it.part(np.clip(buckle - L.rect(13.2, 14.2, 14.8, 15.8), 0, 1), hx('#d8b858'))
    for x in np.arange(5, 24, 1.6):
        L.fill(L.circle(x, 20.2, 0.3) * bag, hx('#d8b088'), 0.8)
    return it.done(), 1


def p_toolbox():
    it = Item(32, 20)
    L = it.L
    red = hx('#c83a2e')
    handle = np.clip(L.rect(10, 1.5, 22, 7, r=2) - L.rect(12.2, 3.6, 19.8, 8), 0, 1)
    it.part(handle, hx('#3a3a44'))
    box = L.rect(2.5, 6.5, 29.5, 18.5, r=1.6)
    it.part(box, red)
    lid = L.rect(2.5, 6.5, 29.5, 10, r=1.2)
    it.part(lid, mix(red, hx('#ff8a6a'), 0.2))
    for x in (6, 26):
        L.fill(L.rect(x - 1.4, 9.2, x + 1.4, 12), hx('#c8ccd4'))
    it.spec(16, 12.5, 9, 0.5, 0.5)
    return it.done(), 1


def p_radio():
    """Chunky 1980s two-way radio from the ambulance (content 1.2)."""
    it = Item(20, 30)
    L = it.L
    ant = L.rect(13.5, 0.8, 16, 10, r=1.1)
    it.part(ant, hx('#2a2830'))
    knob = L.rect(5, 3.8, 9, 7.5, r=1)
    it.part(knob, hx('#4a4652'))
    body = L.rect(2.5, 6.5, 17.5, 28.5, r=2.2)
    it.part(body, hx('#34323e'), li=hx('#6a6878'))
    stripe = L.rect(2.5, 9.5, 17.5, 12.5) * body
    L.fill(stripe, hx('#e8402e'))
    L.fill(L.rect(8.6, 9.8, 11.4, 12.2), WHITE)
    L.fill(L.rect(9.3, 9.2, 10.7, 12.8), WHITE)
    grille = L.rect(5, 14.5, 15, 21.5, r=1.2)
    L.fill(grille, hx('#1c1a22'))
    for y in np.arange(15.5, 21, 1.5):
        L.fill(L.rect(5.8, y, 14.2, y + 0.6) * grille, hx('#5a5866'))
    L.fill(L.rect(5, 23.5, 15, 26.5, r=0.8), hx('#8ad05a'), 0.85)
    L.fill(L.rect(5.6, 24.1, 9, 25.9), hx('#e8ffd0'), 0.8)
    it.spec(4.4, 9, 0.5, 2.0, 0.6)
    return it.done(), 1


def p_conductor_punch():
    """Brass conductor's ticket punch (content 1.2)."""
    it = Item(26, 20)
    L = it.L
    brass = hx('#d8a838')
    h1 = L.poly(bez((2, 13), (8, 15.5), (14, 11)) + [(14, 9)] + bez((14, 9), (8, 13), (2.5, 10.5)))
    h2 = L.poly(bez((3, 18), (9, 19), (15, 13.5)) + [(14.5, 11.5)] + bez((14.5, 11.5), (9, 16.5), (3, 15.5)))
    it.part(h2, mix(brass, hx('#5a3a1a'), 0.3))
    it.part(h1, brass, li=hx('#ffe48a'))
    head = L.poly([(13, 7.5), (21, 4), (24.5, 7), (24.5, 12.5), (21, 15.5), (13.5, 13.5)])
    it.part(head, brass, li=hx('#ffe48a'))
    jaw = L.rect(19, 9, 24.5, 11.4) * head
    L.fill(jaw, hx('#3a2a14'))
    die = L.poly(star_pts(21.5, 6.6, 1.8, 0.8, 5))
    L.fill(die, hx('#5a3a14'))
    pivot = L.circle(14.5, 11.2, 1.4)
    it.part(pivot, hx('#a8b0c0'))
    for k in range(3):
        L.fill(L.circle(23 + (k % 2) * 1.6 - 4, 17.5 + k * 0.6, 0.7), hx('#f2e6c8'))
    return it.done(hx('#3a2408')), 1


def p_scale_weight():
    """Rigged lead market weight: '1 LB' stamped, but a filed-down plug in the base gives it away (content 1.2)."""
    it = Item(24, 24)
    L = it.L
    lead = hx('#7a7e8a')
    ring = np.clip(L.ellipse(12, 5, 4.6, 3.6) - L.ellipse(12, 5, 2.6, 1.8), 0, 1)
    it.part(ring, hx('#5a5e6a'))
    body = L.poly([(7.5, 7.5), (16.5, 7.5), (20.5, 20), (3.5, 20)])
    body = np.clip(body + L.ellipse(12, 20, 8.5, 2.6), 0, 1)
    it.part(body, lead, li=hx('#c8ccd8'), sh_off=1.8)
    top = L.ellipse(12, 7.6, 4.6, 1.4)
    it.part(top, mix(lead, WHITE, 0.25))
    L.fill(L.text('1LB', F_COND_B, 6.2, 12, 14.4, anchor='mm'), hx('#3a3e4a'))
    plug = L.ellipse(12, 20.4, 3.2, 1.2)
    L.fill(plug, hx('#c89a48'))
    L.fill(L.stroke([(10, 20.3), (14, 20.5)], 0.45), hx('#6a4a14'))
    L.fill(L.stroke([(4.5, 17), (7, 16.4)], 0.5), hx('#c8ccd8'), 0.7)
    return it.done(hx('#16181e')), 1


PICKUPS = {
    'bill': p_bill, 'cash_stack': p_cash_stack, 'coin': p_coin, 'heal_bun': p_heal_bun, 'key': p_key,
    'ledger': p_ledger, 'parcel': p_parcel, 'satchel': p_satchel, 'toolbox': p_toolbox,
    'radio': p_radio, 'conductor_punch': p_conductor_punch, 'scale_weight': p_scale_weight,
}


def main():
    wmeta = {}
    for k, fn in WEAPONS.items():
        im, grip, tip = fn()
        save(im, os.path.join(W_OUT, k + '.png'))
        wmeta[k] = {'file': 'res://assets/weapons2/%s.png' % k, 'grip': list(grip), 'tip': list(tip), 'density': 2}
    with open(os.path.join(W_OUT, 'weapons.json'), 'w') as fh:
        json.dump(wmeta, fh, indent=1)
    pmeta = {}
    for k, fn in PICKUPS.items():
        im, n = fn()
        save(im, os.path.join(P_OUT, k + '.png'))
        pmeta[k] = {'file': 'res://assets/pickups2/%s.png' % k, 'frame': [im.size[0] // n, im.size[1]], 'frames': n,
                    'density': 2}
    with open(os.path.join(P_OUT, 'pickups.json'), 'w') as fh:
        json.dump(pmeta, fh, indent=1)
    print('weapons2:', len(wmeta), 'pickups2:', len(pmeta))


if __name__ == '__main__':
    main()
