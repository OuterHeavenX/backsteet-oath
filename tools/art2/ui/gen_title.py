#!/usr/bin/env python3
"""Parallax title-screen layers (density 2) -> game/assets/ui2/title_*.png.

The scene is Old Quarter at dusk. Brick rows frame a low sun over the far ironworks, and
the wet street reflects the sky. Layers are 1600 tx wide (wider than 1280 so expanded aspect
ratios and parallax drift never show an edge) and are BOTTOM-anchored to the 720 tx frame.
title_sky is 960 tall so taller screens (4:3) can see more sky.

Usage: python3 tools/art2/ui/gen_title.py
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vec import Layer, hx, mix, tones, bez, ell_pts, rot_pts, F_BUNGEE, F_COND_B, INK  # noqa: E402
import gen_ui  # noqa: E402

W = 1600
HZ = 470          # horizon line in the 720 frame
SUN = (1010, 452)
INKT = hx('#1a1020')


def rng(s):
    return np.random.default_rng(s)


# ------------------------------------------------------------------ sky
def sky():
    H = 960
    off = H - 720            # frame offset (sky extends above the 720 frame)
    L = Layer(W, H, ss=1)
    X, Y = L.coords()
    yf = Y - off             # y in frame space
    stops = [(-240, '#140c2a'), (60, '#2c1a4c'), (230, '#7a3a6a'), (360, '#d8607a'), (430, '#ff9a6a'),
             (470, '#ffc888'), (560, '#ffd8a0')]
    col = np.zeros((H, W, 3), np.float32)
    for (y0, c0), (y1, c1) in zip(stops, stops[1:]):
        a = np.array(hx(c0), np.float32) / 255
        b = np.array(hx(c1), np.float32) / 255
        t = np.clip((yf - y0) / (y1 - y0), 0, 1)[..., None]
        m = ((yf >= y0) & (yf < y1))[..., None]
        col = np.where(m, a + (b - a) * t, col)
    col = np.where((yf >= stops[-1][0])[..., None], np.array(hx(stops[-1][1]), np.float32) / 255, col)
    col = np.where((yf < stops[0][0])[..., None], np.array(hx(stops[0][1]), np.float32) / 255, col)
    # sun glow
    d = np.sqrt((X - SUN[0]) ** 2 + ((yf - SUN[1]) * 1.3) ** 2)
    glow = np.clip(1 - d / 520, 0, 1) ** 2.2
    col = col + (np.array([1.0, 0.78, 0.5]) - col) * glow[..., None] * 0.55
    L.fill_rgb(L.full(), col.astype(np.float32))
    L2 = Layer(W, H, ss=2)
    # sun disc with cel bands
    sun = L2.circle(SUN[0], SUN[1] + off, 70)
    L2.fill(sun, hx('#ffe6b0'))
    for k, (dy, c) in enumerate(((22, '#ffd08a'), (40, '#ffb878'), (54, '#ff9c6a'))):
        band = L2.rect(SUN[0] - 80, SUN[1] + off + dy, SUN[0] + 80, SUN[1] + off + dy + 5 + k * 2) * sun
        L2.erase(band, 0.85)
    # cloud bands: flat cel-shaded streaks lit from below
    r = rng(5)
    for i in range(14):
        cy = off + 120 + i * 24 + r.random() * 16
        cx = r.random() * W
        ln = 220 + r.random() * 380
        th = 7 + r.random() * 12
        pts = bez((cx - ln / 2, cy), (cx - ln / 4, cy - th * 1.6), (cx + ln / 3, cy - th)) + \
            bez((cx + ln / 3, cy - th), (cx + ln / 2 + 30, cy - th * 0.2), (cx + ln / 2, cy)) + [(cx - ln / 2, cy)]
        m = L2.poly(pts)
        t = (cy - off) / 470
        base = mix(hx('#4a2a5e'), hx('#e07a7a'), min(max(t, 0), 1) ** 1.2)
        lit = mix(base, hx('#ffd0a0'), 0.55)
        L2.fill(m, base, 0.92)
        L2.fill(np.clip(m - L2.shift(m, 0, -3.5), 0, 1), lit, 0.95)
    # stars high up
    for i in range(70):
        x, y = r.random() * W, r.random() * (off + 160)
        a = 0.35 + 0.6 * r.random() * (1 - y / (off + 160))
        L2.fill(L2.circle(x, y, 0.9 + r.random() * 0.8), (255, 246, 230), a)
    L.over_from = None
    base = L.image().convert('RGBA')
    top = L2.image()
    base.alpha_composite(top)
    gen_ui.reg('title_sky', base, note='Opaque. 1600x960 tx; the 720 frame is the BOTTOM 720 rows (horizon y=470 in '
               'frame). Suggested parallax 0.02 + slow cloud drift.', anchor='bottom', parallax=0.02)


# ------------------------------------------------------------------ far industry silhouette
def far():
    H = 720
    L = Layer(W, H, ss=2)
    base_y = 548
    shapes = []
    r = rng(11)
    sil = np.zeros((L.H, L.W), np.float32)
    def add(pts):
        nonlocal sil
        sil = np.maximum(sil, L.poly(pts))
    # rolling low factory blocks
    x = 0
    while x < W:
        w = 60 + r.random() * 120
        h = 40 + r.random() * 70
        roof = r.integers(0, 3)
        if roof == 0:
            add([(x, base_y), (x, base_y - h), (x + w, base_y - h), (x + w, base_y)])
        elif roof == 1:   # saw-tooth roof
            pts = [(x, base_y), (x, base_y - h)]
            n = int(w // 26) + 1
            for k in range(n):
                x0 = x + k * w / n
                pts += [(x0 + w / n * 0.75, base_y - h - 18), (x0 + w / n, base_y - h)]
            pts += [(x + w, base_y)]
            add(pts)
        else:
            add([(x, base_y), (x, base_y - h), (x + w * 0.5, base_y - h - 22), (x + w, base_y - h), (x + w, base_y)])
        x += w - 4
    # smokestacks
    stacks = [(180, 250), (232, 220), (610, 280), (1290, 240), (1340, 300), (1460, 210)]
    for sx, h in stacks:
        add([(sx - 9, base_y - 60), (sx - 7, base_y - h), (sx + 7, base_y - h), (sx + 9, base_y - 60)])
        add([(sx - 10, base_y - h - 6), (sx + 10, base_y - h - 6), (sx + 10, base_y - h + 4), (sx - 10, base_y - h + 4)])
    # gas holder
    gh = L.ellipse(420, base_y - 70, 70, 74)
    sil = np.maximum(sil, gh * (L.coords()[1] < base_y))
    # water tower
    add([(820, base_y - 120), (826, base_y - 210), (832, base_y - 210), (838, base_y - 120)])
    add([(860, base_y - 120), (854, base_y - 210), (860, base_y - 210), (866, base_y - 120)])
    sil = np.maximum(sil, L.rect(810, base_y - 268, 880, base_y - 208, r=6))
    add([(806, base_y - 268), (845, base_y - 300), (884, base_y - 268)])
    # crane
    add([(1140, base_y), (1146, base_y - 260), (1156, base_y - 260), (1162, base_y)])
    add([(1060, base_y - 262), (1260, base_y - 268), (1260, base_y - 256), (1060, base_y - 252)])
    cable = L.stroke([(1230, base_y - 258), (1230, base_y - 170)], 2)
    sil = np.maximum(sil, cable)
    # truss bridge (low arch)
    arch = []
    for k in range(41):
        t = k / 40
        arch.append((540 + 560 * t, base_y - 30 - 70 * math.sin(t * math.pi)))
    sil = np.maximum(sil, L.stroke(arch, 7))
    for k in range(0, 41, 3):
        t = k / 40
        x0 = 540 + 560 * t
        y0 = base_y - 30 - 70 * math.sin(t * math.pi)
        sil = np.maximum(sil, L.stroke([(x0, y0), (x0 + 14, base_y - 24)], 2.2))
    sil = np.maximum(sil, L.rect(520, base_y - 30, 1120, base_y - 22))
    sil = np.maximum(sil, L.rect(0, base_y - 4, W, H))
    # atmospheric colour: lighter + warmer toward the sun and the horizon
    X, Y = L.coords()
    d = np.clip(1 - np.sqrt((X - SUN[0]) ** 2 + ((Y - SUN[1]) * 2) ** 2) / 700, 0, 1)
    t = np.clip((Y - 250) / 300, 0, 1)
    c_hi = np.array(hx('#8a5a7e'), np.float32) / 255
    c_lo = np.array(hx('#5e3a62'), np.float32) / 255
    c_sun = np.array(hx('#d88a7a'), np.float32) / 255
    rgb = c_hi + (c_lo - c_hi) * t[..., None]
    rgb = rgb + (c_sun - rgb) * (d ** 1.5)[..., None] * 0.7
    L.fill_rgb(sil, rgb.astype(np.float32))
    # tops catch the sunset (rim on edges facing the sun)
    rim = np.clip(sil - L.shift(sil, (X.mean() * 0) - 1.5, 2.5), 0, 1)
    L.fill(rim * (d[...] > 0.05), hx('#ffb890'), 0.55)
    # smoke plumes (soft, drifting left)
    for sx, h in stacks:
        for k in range(7):
            cx = sx - k * 26 - r.random() * 8
            cy = base_y - h - 14 - k * 12
            m = L.blur(L.circle(cx, cy, 10 + k * 4), 4)
            L.fill(m, mix(hx('#b88a9a'), hx('#e8b8a8'), k / 7), 0.35 * (1 - k / 8))
    # window specks
    for i in range(90):
        x, y = r.random() * W, base_y - 10 - r.random() * 90
        if sil[int(y * 2), int(x * 2)] > 0.5:
            L.fill(L.rect(x, y, x + 3, y + 3), hx('#ffd27a'), 0.55 + 0.4 * r.random())
    gen_ui.reg('title_far', L.image(), note='Transparent top; bottom-anchored. Suggested parallax 0.12.',
               anchor='bottom', parallax=0.12)


# ------------------------------------------------------------------ mid: Old Quarter brick rows (backlit)
BRICK_SH = hx('#4a2430')
BRICK = hx('#6a3034')
RIM = hx('#ffb27a')


def building(L, x0, x1, top, base, seed, kind='brick', sign=None):
    r = rng(seed)
    body = L.rect(x0, top, x1, base)
    sh, b, li, ink = tones(BRICK if kind == 'brick' else hx('#4a3a4e'))
    col_t = mix(b, hx('#2a1830'), 0.25)
    L.fill(L.dil(body, 2), INKT)
    L.lin(body, col_t, mix(sh, hx('#1a1020'), 0.35), (0, top), (0, base))
    # brick courses: faint horizontal lines
    for y in np.arange(top + 10, base, 7):
        L.fill(L.rect(x0 + 2, y, x1 - 2, y + 0.9) * body, hx('#1a1020'), 0.18)
    # cornice
    corn = L.rect(x0 - 6, top - 4, x1 + 6, top + 12)
    L.fill(L.dil(corn, 2), INKT)
    L.fill(corn, mix(b, hx('#2a1830'), 0.15))
    L.fill(np.clip(corn - L.shift(corn, 0, 3), 0, 1), RIM, 0.9)
    for x in np.arange(x0, x1, 18):
        L.fill(L.rect(x, top + 12, x + 8, top + 17), INKT, 0.7)
    # right-edge rim toward the sun (if the sun is to the right)
    if x1 < SUN[0] + 200:
        L.fill(L.rect(x1 - 3, top, x1, base) * body, RIM, 0.65)
    # windows
    cols = max(2, int((x1 - x0 - 30) // 52))
    rows = max(2, int((base - top - 90) // 74))
    ww, wh = 28, 44
    gapx = (x1 - x0 - cols * ww) / (cols + 1)
    for cx in range(cols):
        for ry in range(rows):
            wx = x0 + gapx + cx * (ww + gapx)
            wy = top + 40 + ry * 74
            if wy + wh > base - 70:
                continue
            frame = L.rect(wx - 3, wy - 3, wx + ww + 3, wy + wh + 3)
            L.fill(frame, INKT)
            pane = L.rect(wx, wy, wx + ww, wy + wh)
            lit = r.random() < 0.42
            if lit:
                L.lin(pane, hx('#ffe6a0'), hx('#ffb45a'), (0, wy), (0, wy + wh))
                L.fill(L.rect(wx, wy + wh * 0.55, wx + ww, wy + wh) * pane, hx('#d8803a'), 0.6)
                if r.random() < 0.5:   # blind
                    L.fill(L.rect(wx, wy, wx + ww, wy + wh * (0.2 + 0.4 * r.random())), hx('#c87a3a'), 0.9)
            else:
                L.lin(pane, hx('#5a3a5e'), hx('#2a1a30'), (0, wy), (0, wy + wh))
                L.fill(L.poly([(wx + 4, wy + wh), (wx + ww * 0.7, wy), (wx + ww, wy), (wx + 10, wy + wh)]) * pane,
                       hx('#c87a8a'), 0.35)
            L.fill(L.rect(wx, wy + wh / 2 - 1, wx + ww, wy + wh / 2 + 1), INKT)
            sill = L.rect(wx - 5, wy + wh + 3, wx + ww + 5, wy + wh + 8)
            L.fill(sill, mix(b, RIM, 0.25))
    # fire escape
    if kind == 'brick' and r.random() < 0.8:
        fx0 = x0 + gapx - 12
        fx1 = min(x1 - 10, fx0 + ww * 2 + gapx + 24)
        for ry in range(rows):
            y = top + 40 + ry * 74 + wh + 6
            if y > base - 80:
                continue
            L.fill(L.rect(fx0, y, fx1, y + 4), INKT)
            for x in np.arange(fx0, fx1, 7):
                L.fill(L.rect(x, y - 18, x + 1.6, y), INKT, 0.9)
            L.fill(L.rect(fx0, y - 18, fx1, y - 16), INKT)
            L.fill(L.stroke([(fx1 - 6, y), (fx1 - 36, y + 70)], 2.4), INKT)
    # water tank on roof
    if r.random() < 0.6:
        tx = x0 + (x1 - x0) * (0.3 + 0.4 * r.random())
        legs = L.rect(tx - 22, top - 34, tx - 18, top) + L.rect(tx + 18, top - 34, tx + 22, top)
        L.fill(np.clip(legs, 0, 1), INKT)
        tank = L.rect(tx - 28, top - 86, tx + 28, top - 32, r=4)
        L.fill(L.dil(tank, 2), INKT)
        L.lin(tank, hx('#5a3a3a'), hx('#2a1a24'), (0, top - 86), (0, top - 32))
        cap = L.poly([(tx - 32, top - 86), (tx, top - 108), (tx + 32, top - 86)])
        L.fill(L.dil(cap, 2), INKT)
        L.fill(cap, hx('#3a2430'))
        L.fill(np.clip(cap - L.shift(cap, -2, 2), 0, 1), RIM, 0.8)
        for k in range(3):
            L.fill(L.rect(tx - 28, top - 76 + k * 16, tx + 28, top - 75 + k * 16), INKT, 0.6)
    # storefront at the base
    sf_top = base - 64
    L.fill(L.rect(x0, sf_top, x1, base), hx('#2a1828'))
    awn = L.poly([(x0 + 6, sf_top - 6), (x1 - 6, sf_top - 6), (x1 + 2, sf_top + 16), (x0 - 2, sf_top + 16)])
    L.fill(L.dil(awn, 2), INKT)
    stripes = np.zeros_like(awn)
    X, Y = L.coords()
    stripes = ((((X - x0) // 14) % 2) == 0).astype(np.float32) * awn
    acol = hx('#b8382e') if r.random() < 0.5 else hx('#2e6a7a')
    L.fill(awn, mix(acol, hx('#1a1020'), 0.2))
    L.fill(stripes, mix(hx('#f0e0c8'), hx('#1a1020'), 0.35))
    shop = L.rect(x0 + 12, sf_top + 20, x1 - 12, base - 4)
    L.lin(shop, hx('#ffd890'), hx('#e08a40'), (0, sf_top + 20), (0, base))
    for x in np.arange(x0 + 12, x1 - 12, 40):
        L.fill(L.rect(x, sf_top + 20, x + 3, base - 4), INKT)
    if sign:
        txt, sc = sign
        sx = (x0 + x1) / 2
        plate = L.rect(sx - len(txt) * 11 - 16, top + 6 - 46, sx + len(txt) * 11 + 16, top - 8, r=4)
        L.fill(L.dil(plate, 2), INKT)
        L.fill(plate, hx('#2a1a2a'))
        t = L.text(txt, F_BUNGEE, 26, sx, top - 27, anchor='mm', spacing=1)
        glow = L.blur(L.dil(t, 2), 5)
        L.fill(glow, sc, 0.6)
        L.fill(t, mix(sc, (255, 255, 255), 0.55))


def mid():
    H = 720
    L = Layer(W, H, ss=2)
    base = 604
    building(L, -10, 200, 160, base, 1, sign=None)
    building(L, 196, 410, 236, base, 2, sign=('LUCKY SPOON', hx('#5ad8ff')))
    building(L, 406, 560, 300, base, 3, kind='brick')
    building(L, 1050, 1230, 280, base, 4, sign=('ARCADE', hx('#ff5ab8')))
    building(L, 1226, 1420, 200, base, 5)
    building(L, 1416, 1610, 140, base, 6)
    # vertical neon blade sign on the right building
    blade = L.rect(1232, 300, 1262, 470, r=4)
    L.fill(L.dil(blade, 2), INKT)
    L.fill(blade, hx('#1e1426'))
    for i, ch in enumerate('HOTEL'):
        t = L.text(ch, F_BUNGEE, 24, 1247, 322 + i * 33, anchor='mm')
        L.fill(L.blur(L.dil(t, 2), 4), hx('#ff6a9a'), 0.6)
        L.fill(t, hx('#ffd0e0'))
    # utility poles + cables across the gap (frame the sun)
    for px in (600, 1000):
        pole = L.rect(px - 5, 210, px + 5, base)
        L.fill(L.dil(pole, 2), INKT)
        L.fill(pole, hx('#2a1a24'))
        arm = L.rect(px - 40, 236, px + 40, 244)
        L.fill(L.dil(arm, 1.5), INKT)
        L.fill(arm, hx('#2a1a24'))
    for k, (y0, sag) in enumerate(((240, 40), (240, 52), (250, 30))):
        pts = bez((560 - 40 * k, y0 + 20), (800, y0 + sag + 40), (1040 + 30 * k, y0 + 5))
        L.fill(L.stroke(pts, 1.6), INKT, 0.9)
    pts = bez((0, 330), (300, 420), (600, 240))
    L.fill(L.stroke(pts, 1.6), INKT, 0.9)
    pts = bez((1000, 240), (1300, 400), (1600, 300))
    L.fill(L.stroke(pts, 1.6), INKT, 0.9)
    # sidewalk strip behind the street layer edge (continuity)
    L.fill(L.rect(0, base, W, H), hx('#3a2a36'))
    gen_ui.reg('title_mid', L.image(), note='Transparent top; bottom-anchored. Suggested parallax 0.35.',
               anchor='bottom', parallax=0.35)


# ------------------------------------------------------------------ street (foreground)
def street():
    H = 720
    L = Layer(W, H, ss=2)
    X, Y = L.coords()
    side_top, curb, road = 600, 636, 648
    sw = L.rect(0, side_top, W, curb)
    L.lin(sw, hx('#8a6a6e'), hx('#5a4250'), (0, side_top), (0, curb))
    for x in np.arange(0, W, 64):
        L.fill(L.rect(x, side_top, x + 1.5, curb), hx('#3a2a36'), 0.6)
    L.fill(L.rect(0, side_top, W, side_top + 2), hx('#ffcf9a'), 0.6)
    cb = L.rect(0, curb, W, road)
    L.fill(cb, hx('#a88a86'))
    L.fill(L.rect(0, curb, W, curb + 2.5), hx('#ffe0b8'), 0.9)
    L.fill(L.rect(0, road - 3, W, road), hx('#3a2832'))
    rd = L.rect(0, road, W, H)
    # wet asphalt: reflection of the sky (warm band under the sun), streaks
    t = np.clip((Y - road) / (H - road), 0, 1)
    base = np.array(hx('#3a2a3c'), np.float32) / 255
    deep = np.array(hx('#1c1424'), np.float32) / 255
    warm = np.array(hx('#ff9a6a'), np.float32) / 255
    rgb = base + (deep - base) * t[..., None]
    refl = np.clip(1 - np.abs(X - SUN[0]) / 260, 0, 1) ** 1.5 * (0.55 - 0.35 * t)
    streaks = (np.sin(Y * 1.7 + np.sin(X * 0.05) * 2) > 0.55).astype(np.float32)
    rgb = rgb + (warm - rgb) * (refl * (0.55 + 0.45 * streaks))[..., None]
    L.fill_rgb(rd, rgb.astype(np.float32))
    # neon reflections (cyan + magenta) as vertical broken streaks
    for (cx, col) in ((300, '#5ad8ff'), (1140, '#ff5ab8'), (1247, '#ff6a9a')):
        m = np.clip(1 - np.abs(X - cx) / 26, 0, 1) * (streaks * 0.6 + 0.4) * rd * np.clip(1 - t * 1.3, 0, 1)
        L.fill(m.astype(np.float32), hx(col), 0.45)
    # lane dash
    for x in np.arange(-40, W, 200):
        d = L.poly([(x, 688), (x + 110, 688), (x + 104, 696), (x - 6, 696)])
        L.fill(d, hx('#d8c8a0'), 0.55)
    # puddles
    for (cx, cy, rx) in ((520, 676, 70), (900, 700, 110), (1450, 668, 60)):
        p = L.ellipse(cx, cy, rx, rx * 0.12)
        L.fill(p, hx('#ffb088'), 0.35)
        L.fill(np.clip(p - L.shift(p, 0, 2), 0, 1), hx('#fff0d0'), 0.5)
    # street lamp (left)
    lx = 150
    pole = L.poly([(lx - 7, side_top + 26), (lx - 5, 170), (lx + 5, 170), (lx + 7, side_top + 26)])
    basep = L.rect(lx - 14, side_top - 4, lx + 14, side_top + 28, r=3)
    arm = L.stroke(bez((lx, 176), (lx + 10, 130), (lx + 60, 134)), 6)
    lamp = L.poly([(lx + 40, 132), (lx + 94, 132), (lx + 84, 150), (lx + 50, 150)])
    lampm = np.clip(pole + basep + arm + lamp, 0, 1)
    L.fill(L.dil(lampm, 2), INKT)
    L.fill(lampm, hx('#2a2030'))
    L.fill(np.clip(lampm - L.shift(lampm, -2, 0), 0, 1), RIM, 0.55)
    bulb = L.ellipse(lx + 67, 152, 16, 5)
    L.fill(L.blur(L.circle(lx + 67, 160, 46), 14), hx('#ffd890'), 0.55)
    L.fill(bulb, hx('#fff2c8'))
    cone = L.poly([(lx + 52, 154), (lx + 82, 154), (lx + 170, side_top + 30), (lx - 30, side_top + 30)])
    L.fill(L.blur(cone, 10) * np.clip((Y - 150) / 500, 0, 1) ** 0.4 * np.clip(1 - (Y - 150) / 520, 0, 1),
           hx('#ffe0a0'), 0.22)
    pool = L.ellipse(lx + 67, side_top + 22, 120, 14)
    L.fill(L.blur(pool, 8), hx('#ffd890'), 0.35)
    # hydrant + bags + newsbox (right side props)
    hx0 = 1380
    hyd = np.clip(L.rect(hx0 - 12, side_top - 20, hx0 + 12, side_top + 20, r=4) + L.ellipse(hx0, side_top - 22, 14, 8)
                  + L.rect(hx0 - 20, side_top - 6, hx0 + 20, side_top + 4, r=3), 0, 1)
    L.fill(L.dil(hyd, 2), INKT)
    sh, b, li, ink = tones(hx('#c8382e'))
    L.fill(hyd, mix(sh, hx('#2a1020'), 0.2))
    L.fill(np.clip(hyd - L.shift(hyd, -3, 1), 0, 1), RIM, 0.85)
    for (bx, by, rr) in ((1500, side_top + 4, 26), (1540, side_top + 10, 20), (60, side_top + 6, 24)):
        bag = L.ellipse(bx, by, rr, rr * 0.8)
        L.fill(L.dil(bag, 2), INKT)
        L.fill(bag, hx('#22202c'))
        L.fill(np.clip(bag - L.shift(bag, -3, 2), 0, 1), RIM, 0.5)
        L.fill(L.ellipse(bx - rr * 0.3, by - rr * 0.4, rr * 0.25, rr * 0.12), (255, 255, 255), 0.25)
    gen_ui.reg('title_street', L.image(), note='Foreground street, bottom-anchored. Suggested parallax 0.7. Player-'
               'facing ground at y=600..720 tx.', anchor='bottom', parallax=0.7)


# ------------------------------------------------------------------ hero (backlit silhouette)
def hero():
    """Nico seen from behind, facing the sunset over the city: backlit, so he reads as a dark
    silhouette edged in warm light, with no face (silhouettes stay clean and readable). Jacket
    slung over his right shoulder, taped left fist, headband tails in the wind."""
    Wd, H = 480, 640
    L = Layer(Wd, H, ss=2)
    skin = hx('#d89a6a')
    tee = hx('#e8dcc0')
    jacket = hx('#2e3a5e')
    jeans = hx('#3a4a78')
    tape = hx('#f0ece0')
    band = hx('#e03a2c')
    hair = hx('#2a1c24')
    DK = 0.30

    def dark(c, k=DK):
        return mix(tuple(int(v * k) for v in c), hx('#2a1438'), 0.4)

    allm = np.zeros((L.H, L.W), np.float32)

    def part(m, c, k=DK, contour=True):
        nonlocal allm
        col = dark(c, k)
        if contour:
            L.fill(np.clip(L.dil(m, 1.4) - m, 0, 1), INKT)
        L.fill(m, col)
        L.fill(np.clip(m - L.shift(m, 5, -2), 0, 1), mix(col, (0, 0, 0), 0.3))
        allm = np.maximum(allm, m)
        return m

    def limb(p0, p1, p2, w0, w1, w2, n=30):
        pts_l, pts_r = [], []
        path = bez(p0, p1, p2, n=n)
        for i, (x, y) in enumerate(path):
            t = i / n
            w = (w0 + (w1 - w0) * t * 2) if t < 0.5 else (w1 + (w2 - w1) * (t - 0.5) * 2)
            j = min(i, n - 1)
            dx, dy = path[j + 1][0] - path[j][0], path[j + 1][1] - path[j][1]
            nn = math.hypot(dx, dy) or 1
            nx, ny = -dy / nn, dx / nn
            pts_l.append((x + nx * w / 2, y + ny * w / 2))
            pts_r.append((x - nx * w / 2, y - ny * w / 2))
        return np.clip(L.poly(pts_l + pts_r[::-1]) + L.circle(*p0, w0 / 2) + L.circle(*p2, w2 / 2), 0, 1)

    # headband tails (behind everything, blowing left)
    t1 = L.poly(bez((236, 104), (170, 96), (96, 128)) + bez((96, 128), (88, 138), (102, 140)) + bez((102, 140), (170, 112), (238, 114)))
    t2 = L.poly(bez((236, 110), (186, 130), (130, 176)) + bez((130, 176), (128, 188), (142, 186)) + bez((142, 186), (190, 140), (240, 118)))
    part(np.clip(t1 + t2, 0, 1), band, k=0.62)
    # legs: weight on the left leg, right leg relaxed
    legL = limb((212, 360), (206, 478), (202, 588), 68, 56, 44)
    legR = limb((274, 360), (300, 474), (314, 584), 66, 54, 42)
    part(legR, jeans)
    part(legL, jeans)
    L.fill(L.stroke(bez((214, 440), (220, 470), (210, 500)), 1.4) * legL, INKT, 0.7)
    L.fill(L.stroke(bez((294, 450), (288, 476), (300, 498)), 1.4) * legR, INKT, 0.7)
    # sneakers (heels toward the camera)
    for (x, y, w) in ((202, 600, 50), (316, 598, 48)):
        sh = L.poly(bez((x - w / 2, y + 22), (x - w / 2 - 2, y - 14), (x, y - 16)) + bez((x, y - 16), (x + w / 2 + 2, y - 14), (x + w / 2, y + 22)))
        part(sh, hx('#c83a2e'), k=0.55)
        so = L.rect(x - w / 2 - 2, y + 16, x + w / 2 + 2, y + 28, r=5)
        part(so, hx('#e8e4dc'), k=0.6)
    # torso (t-shirt back)
    torso = L.poly(bez((158, 196), (150, 300), (186, 372)) + [(298, 372)] + bez((298, 372), (330, 300), (324, 196))
                   + bez((324, 196), (240, 180), (158, 196)))
    part(torso, tee, k=0.25)
    belt = L.poly([(184, 362), (300, 362), (300, 378), (184, 378)])
    part(belt, hx('#3a2a24'), k=0.5)
    L.fill(L.stroke(bez((240, 196), (238, 280), (242, 360)), 1.6) * torso, INKT, 0.55)
    for (p0, p1, p2) in (((190, 230), (206, 270), (196, 320)), ((290, 236), (276, 280), (286, 330))):
        L.fill(L.stroke(bez(p0, p1, p2), 1.4) * torso, INKT, 0.5)
    # left arm hanging, taped fist
    armL = limb((168, 206), (140, 300), (160, 388), 50, 40, 34)
    part(armL, skin, k=0.38)
    sleeve = limb((168, 206), (160, 232), (152, 256), 56, 54, 50)
    part(sleeve, tee, k=0.25)
    fist = np.clip(L.ellipse(162, 410, 20, 22) + L.rect(144, 398, 182, 428, r=9), 0, 1)
    part(fist, skin, k=0.42)
    wrap = L.rect(142, 384, 182, 404, r=7) * L.dil(fist, 3)
    part(np.clip(wrap + L.rect(144, 408, 182, 420, r=5) * fist, 0, 1), tape, k=0.6)
    # draped jacket hanging down the back from the right hand
    drape = L.poly(bez((292, 168), (338, 176), (352, 230)) + bez((352, 230), (362, 300), (346, 352)) + [(330, 344), (300, 350)]
                   + bez((300, 350), (286, 290), (296, 236)) + [(286, 190)])
    part(drape, jacket, k=0.32)
    L.fill(L.stroke(bez((318, 200), (326, 270), (318, 340)), 1.6) * drape, INKT, 0.6)
    L.fill(L.stroke(bez((300, 240), (338, 250), (346, 300)), 1.2) * drape, INKT, 0.45)
    # right arm raised: upper arm out, forearm back to the shoulder holding the collar
    upper = limb((318, 206), (346, 182), (360, 146), 50, 44, 38)
    part(upper, skin, k=0.38)
    sleeveR = limb((318, 206), (330, 196), (338, 186), 56, 54, 52)
    part(sleeveR, tee, k=0.25)
    fore = limb((360, 146), (334, 140), (304, 160), 36, 34, 32)
    part(fore, skin, k=0.38)
    hand = L.ellipse(298, 166, 16, 14)
    part(hand, skin, k=0.42)
    collar = L.poly([(284, 160), (312, 154), (318, 176), (290, 182)])
    part(collar, jacket, k=0.34)
    # neck + head (back view) + spiky hair
    neck = L.rect(220, 140, 260, 192, r=10)
    part(neck, skin, k=0.38)
    head = L.ellipse(240, 108, 40, 48)
    part(head, skin, k=0.38)
    for ex in (199, 281):
        part(L.ellipse(ex, 116, 8, 13), skin, k=0.38)
    spikes = [(196, 132), (184, 104), (166, 92), (190, 80), (176, 54), (206, 60), (210, 30), (232, 50), (246, 18),
              (258, 48), (284, 32), (280, 62), (310, 60), (292, 86), (312, 102), (286, 110), (284, 132), (240, 140)]
    part(L.poly(spikes), hair, k=0.85)
    hb = L.poly(bez((198, 98), (240, 88), (282, 98)) + [(284, 114)] + bez((284, 114), (240, 104), (196, 114)))
    part(hb, band, k=0.62)
    part(L.ellipse(240, 104, 11, 10), band, k=0.55)
    # backlight: an all-round warm rim, stronger on the sun side, plus a soft halo outside
    halo = L.blur(L.dil(allm, 3), 6)
    rim_all = np.clip(allm - L.ero(allm, 2.2), 0, 1)
    sun_side = np.clip(allm - L.shift(allm, -5, 3), 0, 1)
    top_side = np.clip(allm - L.shift(allm, 0, 4), 0, 1)
    L.fill(np.clip(rim_all * 0.7 + sun_side + top_side * 0.8, 0, 1), hx('#ffb27a'), 0.95)
    L.fill(np.clip(allm - L.shift(allm, -2, 1.2), 0, 1), hx('#fff0c8'), 0.9)
    L.fill(np.clip(allm - L.shift(allm, 3, 0), 0, 1), hx('#8a7aff'), 0.35)
    L.outline(2.6, INKT, mask=allm)
    L.under(halo, hx('#ffb27a'), 0.35)
    sh = L.blur(L.ellipse(258, 628, 150, 11), 4)
    L.under(sh, hx('#0e0a14'), 0.7)
    gen_ui.reg('title_hero', L.image(), note='Backlit Nico seen from behind (facing the sunset), feet at (258, 628) tx. '
               'Suggested parallax 0.8; place bottom-aligned beside the menu.', anchor='bottom', feet=[258, 628],
               parallax=0.8)


def main(which=None):
    for fn in (sky, far, mid, street, hero):
        if not which or fn.__name__ in which:
            fn()
    gen_ui.write_meta()
    print('title layers done')


if __name__ == '__main__':
    main(sys.argv[1:])
