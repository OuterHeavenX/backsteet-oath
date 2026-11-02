#!/usr/bin/env python3
"""v2 combat / ambient FX strips (density 2) -> game/assets/fx2/*.png + fx.json.

Each effect is a horizontal strip of equal cells. Impacts are inked, cel-toned bursts
that read on both warm and cold backgrounds; arcs are pure white with tapered alpha so
the engine can tint them per attack; glows/sparks flagged `additive` are white/warm and
meant for an additive blend. Deterministic (fixed seeds).

Usage: python3 tools/art2/ui/gen_fx.py
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vec import (Layer, hx, mix, tones, strip, save, star_pts, ell_pts, rot_pts, bez, ease_out,  # noqa: E402
                 lerp, INK, ASSETS)

OUT = os.path.join(ASSETS, 'fx2')
META = {}

WHITE = (255, 255, 255)
HOT = hx('#fff6d6')
YEL = hx('#ffd84a')
ORG = hx('#ff9a2e')
RED = hx('#e8462e')
FX_INK = hx('#2a1626')
DUST = hx('#c9b9a4')
DUST_SH = hx('#8c7c80')
DUST_LI = hx('#f1e6d4')
DUST_INK = hx('#4e3e4a')


def reg(name, frames, anchor, fps, additive=False, loop=False):
    im = strip(frames)
    save(im, os.path.join(OUT, name + '.png'))
    w, h = frames[0].size
    META[name] = {'file': name + '.png', 'cell': [w, h], 'count': len(frames), 'anchor': list(anchor),
                  'fps': fps, 'additive': additive}
    if loop:
        META[name]['loop'] = True


def rng(seed):
    return np.random.default_rng(seed)


# ---------------------------------------------------------------- shared shapes
def burst(L, cx, cy, r_out, r_in, n, cols, rot=0.0, ink=2.0, jit=None, sx=1.0):
    """Inked multi-tone impact star: outer col, mid col, white core."""
    def pts(ro, ri):
        p = star_pts(cx, cy, ro, ri, n, rot, jit)
        return [(cx + (x - cx) * sx, y) for x, y in p]
    outer = L.poly(pts(r_out, r_in))
    if ink:
        L.fill(L.dil(outer, ink), FX_INK)
    L.fill(outer, cols[0])
    L.fill(L.poly(pts(r_out * 0.72, r_in * 0.7)), cols[1])
    L.fill(L.poly(pts(r_out * 0.42, r_in * 0.45)), cols[2])
    return outer


def ring(L, cx, cy, r, w, col, a=1.0, sy=1.0):
    o = L.ellipse(cx, cy, r, r * sy)
    i = L.ellipse(cx, cy, max(r - w, 0.1), max(r - w, 0.1) * sy)
    L.fill(np.clip(o - i, 0, 1), col, a)


def streak(L, x0, y0, x1, y1, w0, w1):
    """Tapered quad from (x0,y0) width w0 to (x1,y1) width w1."""
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy) or 1
    nx, ny = -dy / n, dx / n
    p = [(x0 + nx * w0 / 2, y0 + ny * w0 / 2), (x1 + nx * w1 / 2, y1 + ny * w1 / 2),
         (x1 - nx * w1 / 2, y1 - ny * w1 / 2), (x0 - nx * w0 / 2, y0 - ny * w0 / 2)]
    m = L.poly(p)
    if w1 > 0.6:
        m = np.maximum(m, L.circle(x1, y1, w1 / 2))
    if w0 > 0.6:
        m = np.maximum(m, L.circle(x0, y0, w0 / 2))
    return m


def rays(L, cx, cy, n, r0, r1, w, col, a=1.0, rot=0.0, jit=None, sx=1.0):
    acc = np.zeros((L.H, L.W), np.float32)
    for i in range(n):
        ang = math.radians(rot + i * 360.0 / n)
        k = jit[i % len(jit)] if jit is not None else 1.0
        x0, y0 = cx + math.cos(ang) * r0 * sx, cy + math.sin(ang) * r0
        x1, y1 = cx + math.cos(ang) * r1 * k * sx, cy + math.sin(ang) * r1 * k
        acc = np.maximum(acc, streak(L, x0, y0, x1, y1, w, w * 0.25))
    L.fill(acc, col, a)
    return acc


def puff(L, circles, a=1.0, ink=1.5, base=DUST, sh=DUST_SH, li=DUST_LI, inkc=DUST_INK):
    """Cel-shaded cloud from (x, y, r) circles; light from upper-left, shadow underneath."""
    if not circles:
        return
    m = np.zeros((L.H, L.W), np.float32)
    for x, y, r in circles:
        if r > 0.3:
            m = np.maximum(m, L.circle(x, y, r))
    tmp = Layer(L.w, L.h, L.ss)
    if ink:
        tmp.fill(tmp.dil(m, ink), inkc)
    tmp.fill(m, base)
    tmp.fill(np.clip(m - tmp.shift(m, 0, -max(1.5, min(r for _, _, r in circles) * 0.45)), 0, 1), sh)
    li_m = np.zeros_like(m)
    for x, y, r in circles:
        if r > 1.2:
            li_m = np.maximum(li_m, L.circle(x - r * 0.25, y - r * 0.3, r * 0.55))
    tmp.fill(li_m * m, li)
    tmp.c *= a
    tmp.a *= a
    L.over(tmp)


def soft_puff(L, circles, col, a=1.0, soft=2.0):
    m = np.zeros((L.H, L.W), np.float32)
    for x, y, r in circles:
        m = np.maximum(m, L.circle(x, y, r))
    m = L.blur(m, soft)
    L.fill(m, col, a)


def smooth(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def crescent(L, cx, cy, R, T, a_start, a_end, head=1.0, alpha=1.0, sy=1.0, lines=2, line_a=0.25):
    """White smear arc around pivot (cx,cy) from a_start to a_end (deg, screen), head at a_end.
    Thickness grows from the tail to T and ends in a round cap; alpha ramps tail -> head."""
    n = 64
    outer, inner = [], []
    for i in range(n + 1):
        t = i / n
        ang = math.radians(a_start + (a_end - a_start) * t)
        th = T * (0.08 + 0.92 * smooth(0.0, 0.6, t))
        if t > 0.9:
            u = (t - 0.9) / 0.1
            th *= math.sqrt(max(1 - u * u, 0.0)) * 0.6 + 0.4 * (1 - u)
        mid = R - T * 0.5
        outer.append((cx + (mid + th / 2) * math.cos(ang), cy + (mid + th / 2) * math.sin(ang) * sy))
        inner.append((cx + (mid - th / 2) * math.cos(ang), cy + (mid - th / 2) * math.sin(ang) * sy))
    m = L.poly(outer + inner[::-1])
    X, Y = L.coords()
    ang = np.degrees(np.arctan2((Y - cy) / max(sy, 1e-3), X - cx))
    span = a_end - a_start
    t = (ang - a_start) / span
    for k in (-360, 360):
        t2 = (ang + k - a_start) / span
        t = np.where(np.abs(t2 - 0.5) < np.abs(t - 0.5), t2, t)
    tt = np.clip(t, 0, 1)
    fade = 0.15 + 0.85 * (tt * tt * (3 - 2 * tt)) ** 0.8
    # brighter outer (leading) edge, softer inner edge
    rr = np.sqrt((X - cx) ** 2 + ((Y - cy) / max(sy, 1e-3)) ** 2)
    edge = np.clip((rr - (R - T)) / max(T, 1e-3), 0, 1) * 0.45 + 0.55
    L.fill(m * fade * edge, WHITE, alpha)
    for j in range(lines):
        r2 = R - T * (0.3 + 0.28 * j)
        pts = []
        for i in range(n + 1):
            u = 0.3 + 0.55 * i / n
            a = math.radians(a_start + (a_end - a_start) * u)
            pts.append((cx + r2 * math.cos(a), cy + r2 * math.sin(a) * sy))
        lm = L.stroke(pts, 0.8)
        L.erase(lm * m, line_a)
    return m


def arc_band(L, cx, cy, R, T, a0, a1, col, alpha=1.0):
    """Symmetric ring segment (impact wave), thick in the middle, pointed ends."""
    n = 48
    outer, inner = [], []
    for i in range(n + 1):
        t = i / n
        ang = math.radians(a0 + (a1 - a0) * t)
        th = T * math.sin(t * math.pi) ** 0.7
        outer.append((cx + R * math.cos(ang), cy + R * math.sin(ang)))
        inner.append((cx + (R - th) * math.cos(ang), cy + (R - th) * math.sin(ang)))
    m = L.poly(outer + inner[::-1])
    L.fill(m, col, alpha)
    return m


# ---------------------------------------------------------------- impacts
def fx_hit_light():
    fr = []
    jit = [1.0, 0.8, 0.95, 0.75, 1.0, 0.85]
    for f in range(4):
        L = Layer(64, 64)
        cx = cy = 32
        if f == 0:
            burst(L, cx, cy, 15, 6, 6, (YEL, HOT, WHITE), rot=10, jit=jit)
        elif f == 1:
            burst(L, cx, cy, 23, 7.5, 6, (YEL, HOT, WHITE), rot=14, jit=jit)
        elif f == 2:
            rays(L, cx, cy, 6, 11, 27, 3.4, HOT, 1.0, rot=-76, jit=jit)
            L.fill(L.circle(cx, cy, 4), WHITE, 0.6)
        else:
            rays(L, cx, cy, 6, 21, 29, 2.0, HOT, 0.45, rot=-76, jit=jit)
        fr.append(L.image())
    reg('hit_light', fr, (32, 32), 30)


def fx_hit_heavy():
    fr = []
    jit = [1.0, 0.78, 0.92, 0.7, 1.0, 0.82, 0.95, 0.74]
    for f in range(5):
        L = Layer(96, 96)
        c = 48
        if f == 0:
            L.fill(L.circle(c, c, 16), WHITE)
            burst(L, c, c, 26, 10, 8, (ORG, YEL, WHITE), rot=6, jit=jit)
        elif f == 1:
            burst(L, c, c, 40, 13, 8, (ORG, YEL, WHITE), rot=10, jit=jit)
            ring(L, c, c, 36, 3.0, WHITE, 0.9)
        elif f == 2:
            rays(L, c, c, 8, 20, 44, 4.5, YEL, 1.0, rot=-80, jit=jit)
            rays(L, c, c, 8, 22, 40, 2.0, WHITE, 1.0, rot=-80, jit=jit)
            ring(L, c, c, 41, 2.4, WHITE, 0.7)
            L.fill(L.circle(c, c, 8), WHITE, 0.8)
        elif f == 3:
            rays(L, c, c, 8, 32, 46, 2.8, HOT, 0.6, rot=-80, jit=jit)
            ring(L, c, c, 45, 1.4, WHITE, 0.4)
        else:
            rays(L, c, c, 8, 39, 47, 1.6, HOT, 0.3, rot=-80, jit=jit)
        fr.append(L.image())
    reg('hit_heavy', fr, (48, 48), 30)


def fx_hit_kick():
    fr = []
    jit = [1.0, 0.7, 0.9, 0.7, 1.0, 0.75, 0.85]
    for f in range(5):
        L = Layer(80, 80)
        c = 40
        if f == 0:
            burst(L, c, c, 16, 7, 7, (YEL, HOT, WHITE), rot=0, jit=jit, sx=1.25)
        elif f == 1:
            arc_band(L, c - 8, c, 26, 6, -60, 60, WHITE, 0.95)
            burst(L, c, c, 25, 9, 7, (YEL, HOT, WHITE), rot=4, jit=jit, sx=1.3)
        elif f == 2:
            arc_band(L, c - 8, c, 31, 4.5, -64, 64, WHITE, 0.7)
            rays(L, c, c, 7, 12, 30, 3.0, HOT, 1.0, rot=-90, jit=jit, sx=1.3)
            L.fill(L.circle(c, c, 5), WHITE, 0.8)
        elif f == 3:
            arc_band(L, c - 8, c, 35, 2.5, -66, 66, WHITE, 0.4)
            rays(L, c, c, 7, 22, 34, 2.0, HOT, 0.5, rot=-90, jit=jit, sx=1.3)
        else:
            rays(L, c, c, 7, 29, 36, 1.4, HOT, 0.25, rot=-90, jit=jit, sx=1.3)
        fr.append(L.image())
    reg('hit_kick', fr, (40, 40), 30)


def sparks(L, cx, cy, t, seed, n=12, spread=150, base=-20, speed=34, grav=30, col=HOT, tail=ORG, w=2.2):
    r = rng(seed)
    angs = base + (r.random(n) - 0.5) * spread
    sp = speed * (0.55 + 0.6 * r.random(n))
    for i in range(n):
        a = math.radians(angs[i])
        vx, vy = math.cos(a) * sp[i], math.sin(a) * sp[i]
        x1, y1 = cx + vx * t, cy + vy * t + grav * t * t
        lag = 0.12 + 0.1 * r.random()
        tt = max(t - lag, 0)
        x0, y0 = cx + vx * tt, cy + vy * tt + grav * tt * tt
        k = max(0.0, 1 - t * 0.8)
        if k <= 0:
            continue
        m = streak(L, x0, y0, x1, y1, w * 0.35 * k, w * k)
        L.fill(L.dil(m, 0.9), tail, k)
        L.fill(m, col, k)


def fx_hit_metal():
    fr = []
    for f in range(5):
        L = Layer(80, 80)
        c = 40
        t = (f + 0.6) / 5
        if f <= 1:
            L.fill(L.poly(star_pts(c, c, 20 + f * 6, 2.6, 4, rot=12)), WHITE)
            L.fill(L.circle(c, c, 7 - f * 2), WHITE)
        sparks(L, c, c, t, 11, n=16, spread=210, base=-40, speed=46, grav=26, col=WHITE, tail=hx('#ff8a1e'), w=3.0)
        fr.append(L.image())
    reg('hit_metal', fr, (40, 40), 30)


def chips(L, cx, cy, t, seed, n, kind):
    r = rng(seed)
    for i in range(n):
        a = math.radians(-70 + (r.random() - 0.5) * 260)
        sp = 26 + 22 * r.random()
        x = cx + math.cos(a) * sp * t
        y = cy + math.sin(a) * sp * t + 34 * t * t
        rot = r.random() * 360 + t * 400 * (1 if i % 2 else -1)
        k = 1.0 if t < 0.7 else max(0.0, 1 - (t - 0.7) / 0.35)
        if k <= 0:
            continue
        if kind == 'wood':
            ln, wd = 5 + 4 * r.random(), 1.8 + 1.2 * r.random()
            p = rot_pts([(x - ln, y - wd * 0.3), (x + ln, y - wd * 0.6), (x + ln * 0.7, y + wd * 0.5), (x - ln * 0.8, y + wd * 0.6)], rot, x, y)
            draw_chip(L, p, hx('#b97f4a'), k)
        elif kind == 'glass':
            s = 3 + 3 * r.random()
            p = rot_pts([(x, y - s), (x + s * 0.7, y + s * 0.6), (x - s * 0.6, y + s * 0.3)], rot, x, y)
            draw_chip(L, p, hx('#a8e4ee'), k, ink=hx('#1c3c48'), hi=WHITE)
        elif kind == 'stone':
            s = 2.6 + 2.6 * r.random()
            p = rot_pts([(x - s, y - s * 0.4), (x - s * 0.2, y - s), (x + s, y - s * 0.3), (x + s * 0.6, y + s * 0.8), (x - s * 0.7, y + s * 0.7)], rot, x, y)
            draw_chip(L, p, hx('#9a8f88'), k)
        elif kind == 'paper':
            s = 3 + 2 * r.random()
            p = rot_pts([(x - s, y - s * 0.6), (x + s, y - s * 0.7), (x + s * 0.8, y + s * 0.6), (x - s * 0.9, y + s * 0.7)], rot, x, y)
            draw_chip(L, p, hx('#eee4cc'), k, ink=hx('#5a4a50'))


def draw_chip(L, pts, base, a, ink=FX_INK, hi=None):
    tmp = Layer(L.w, L.h, L.ss)
    m = tmp.poly(pts)
    tmp.fill(tmp.dil(m, 1.2), ink)
    sh, b, li, _ = tones(base)
    tmp.fill(m, b)
    tmp.fill(np.clip(m - tmp.shift(m, 0, -1.2), 0, 1), sh)
    tmp.fill(np.clip(m - tmp.shift(m, 0.8, 0.8), 0, 1), hi or li)
    tmp.c *= a
    tmp.a *= a
    L.over(tmp)


def fx_hit_material(name, kind, seed, dust_col=None, flash_cols=(YEL, HOT, WHITE)):
    fr = []
    for f in range(5):
        L = Layer(80, 80)
        c = 40
        t = (f + 0.7) / 5
        if f == 0:
            burst(L, c, c, 14, 6, 6, flash_cols, rot=8, ink=2.0)
        elif f == 1:
            burst(L, c, c, 18, 6, 6, flash_cols, rot=12, ink=1.5)
        if dust_col is not None and f >= 1:
            k = 1 - (f - 1) / 4
            rr = rng(seed + 5)
            cs = []
            for i in range(6):
                a = i / 6 * math.tau + rr.random() * 0.8
                d = 3 + 12 * t * (0.6 + 0.4 * rr.random())
                cs.append((c + math.cos(a) * d, c + 2 + math.sin(a) * d * 0.6, 3.5 + 4 * t))
            puff(L, cs, a=0.85 * k, ink=1.2, base=dust_col, sh=mix(dust_col, hx('#5a4a5e'), 0.45),
                 li=mix(dust_col, WHITE, 0.4))
        chips(L, c, c, t, seed, 9, kind)
        if kind == 'glass' and f in (1, 2):
            L.fill(L.poly(star_pts(c + 10, c - 12, 7 - f, 1.2, 4)), WHITE)
        fr.append(L.image())
    reg(name, fr, (40, 40), 28)


def fx_hit_soft():
    fr = []
    for f in range(4):
        L = Layer(64, 64)
        c = 32
        t = (f + 1) / 4
        r = rng(3)
        cs = []
        for i in range(7):
            a = i / 7 * math.tau + 0.3
            d = 4 + 13 * t
            cs.append((c + math.cos(a) * d, c + math.sin(a) * d * 0.8, 5 + 3 * t - 1.5 * r.random()))
        cs.append((c, c, 7 * (1 - t) + 3))
        puff(L, cs, a=1 - 0.75 * t ** 1.5, ink=1.2, base=hx('#f2ead8'), sh=hx('#bcae9e'), li=WHITE)
        chips(L, c, c, t, 9, 4, 'paper')
        fr.append(L.image())
    reg('hit_soft', fr, (32, 32), 24)


def fx_block():
    fr = []
    CY = hx('#8fdcff')
    for f in range(4):
        L = Layer(64, 64)
        c = 32
        k = [1.0, 0.95, 0.6, 0.3][f]
        R = [16, 20, 23, 25][f]
        T = [7, 6, 4, 2.5][f]
        n = 40
        outer = [(c - 6 + R * math.cos(math.radians(a)), c + R * 1.15 * math.sin(math.radians(a))) for a in np.linspace(-75, 75, n)]
        inner = [(c - 6 + (R - T) * math.cos(math.radians(a)), c + (R - T) * 1.15 * math.sin(math.radians(a))) for a in np.linspace(75, -75, n)]
        m = L.poly(outer + inner)
        L.fill(L.dil(m, 1.6), hx('#16304a'), k)
        L.fill(m, CY, k)
        L.fill(L.poly(outer[5:-5] + [(x - 1.2, y) for x, y in inner[5:-5]]) * m, WHITE, k)
        if f < 3:
            sparks(L, c + R - 8, c, (f + 0.8) / 4, 21, n=7, spread=120, base=0, speed=30, grav=10, col=WHITE, tail=CY, w=1.8)
        fr.append(L.image())
    reg('block', fr, (32, 32), 28)


def fx_perfect_block():
    fr = []
    GOLD = hx('#ffd24a')
    for f in range(5):
        L = Layer(96, 96)
        c = 48
        if f == 0:
            L.fill(L.circle(c, c, 12), WHITE)
            L.fill(L.poly(star_pts(c, c, 34, 3.2, 4)), WHITE)
        elif f == 1:
            ring(L, c, c, 22, 5, GOLD)
            ring(L, c, c, 19, 2, WHITE)
            L.fill(L.poly(star_pts(c, c, 44, 3.4, 4)), WHITE)
            L.fill(L.poly(star_pts(c, c, 22, 2.4, 4, rot=45)), GOLD)
        elif f == 2:
            ring(L, c, c, 32, 4, GOLD)
            ring(L, c, c, 29, 1.5, WHITE)
            L.fill(L.poly(star_pts(c, c, 40, 2.4, 4)), WHITE, 0.8)
        elif f == 3:
            ring(L, c, c, 40, 2.5, GOLD, 0.7)
            L.fill(L.poly(star_pts(c, c, 30, 1.6, 4)), WHITE, 0.4)
        else:
            ring(L, c, c, 45, 1.4, GOLD, 0.35)
        fr.append(L.image())
    reg('perfect_block', fr, (48, 48), 28)


# ---------------------------------------------------------------- arcs (white, engine-tinted)
def arc_set(name, size, anchor, cx, cy, R, T, a0, a1, sy=1.0, nfr=4, lines=2):
    fr = []
    for f in range(nfr):
        L = Layer(*size)
        if f == 0:
            crescent(L, cx, cy, R, T * 0.8, a0, a0 + (a1 - a0) * 0.55, alpha=0.9, sy=sy, lines=lines)
        elif f == 1:
            crescent(L, cx, cy, R, T, a0, a1, alpha=1.0, sy=sy, lines=lines)
        elif f == 2:
            crescent(L, cx, cy, R + 1.5, T * 0.6, a0 + (a1 - a0) * 0.3, a1 + (a1 - a0) * 0.05, alpha=0.6, sy=sy, lines=1)
        else:
            crescent(L, cx, cy, R + 2.5, T * 0.32, a0 + (a1 - a0) * 0.55, a1 + (a1 - a0) * 0.08, alpha=0.3, sy=sy, lines=0)
        fr.append(L.image())
    reg(name, fr, anchor, 24)


def fx_arc_punch():
    fr = []
    for f in range(3):
        L = Layer(72, 80)
        y = 12
        x0, x1 = 14, [42, 66, 68][f]
        w = [8, 10, 5][f]
        a = [0.9, 1.0, 0.45][f]
        if f == 2:
            x0 = 36
        m = streak(L, x0, y, x1, y, 0.5, w)
        X, Y = L.coords()
        fade = np.clip((X - x0) / max(x1 - x0, 1), 0, 1) ** 1.2
        L.fill(m * fade, WHITE, a)
        for dy in (-2.2, 2.0):
            lm = L.stroke([(x0 + 10, y + dy), (x1 - 4, y + dy * 0.6)], 0.8)
            L.erase(lm * m, 0.3)
        fr.append(L.image())
    reg('arc_punch', fr, (8, 76), 24)


# ---------------------------------------------------------------- dust & motion
def fx_dust_land():
    fr = []
    for f in range(5):
        L = Layer(96, 32)
        t = (f + 1) / 5
        d = 6 + 34 * ease_out(t)
        r = 7 * (1 - t) + 4 + 3 * t
        a = 1.0 if f < 3 else (0.6 if f == 3 else 0.3)
        cs = []
        for s in (-1, 1):
            cs += [(48 + s * d, 25 - 2 * t, r), (48 + s * (d - r * 0.9), 26, r * 0.8), (48 + s * (d + r * 0.6), 24 - 3 * t, r * 0.6)]
        puff(L, cs, a=a)
        fr.append(L.image())
    reg('dust_land', fr, (48, 30), 20)


def fx_dust_step():
    fr = []
    for f in range(4):
        L = Layer(32, 20)
        t = (f + 1) / 4
        x = 18 - 9 * t
        cs = [(x, 15 - 3 * t, 2.5 + 3 * t), (x + 3 + 2 * t, 16 - t, 2 + 2 * t)]
        puff(L, cs, a=[1, 0.85, 0.6, 0.3][f], ink=1.0)
        fr.append(L.image())
    reg('dust_step', fr, (16, 18), 16)


def fx_dust_slide():
    fr = []
    for f in range(5):
        L = Layer(64, 28)
        t = (f + 1) / 5
        cs = []
        for i in range(5):
            x = 54 - i * 9 - 6 * t
            r = (2 + i * 1.2) * (0.6 + 0.6 * t)
            cs.append((x, 22 - i * 0.8 - 2 * t, min(r, 8)))
        puff(L, cs, a=[1, 0.9, 0.75, 0.5, 0.25][f], ink=1.2)
        fr.append(L.image())
    reg('dust_slide', fr, (56, 26), 18)


def fx_dust_fall():
    fr = []
    r0 = rng(7)
    base = [(r0.random() - 0.5, r0.random()) for _ in range(10)]
    for f in range(6):
        L = Layer(128, 40)
        t = (f + 1) / 6
        cs = []
        for i, (u, v) in enumerate(base):
            x = 64 + u * (30 + 70 * ease_out(t))
            y = 32 - v * (4 + 10 * t)
            r = (5 + 4 * v) * (0.7 + 0.6 * t)
            cs.append((x, y, r))
        puff(L, cs, a=[1, 1, 0.85, 0.6, 0.35, 0.15][f])
        fr.append(L.image())
    reg('dust_fall', fr, (64, 36), 18)


def fx_dust_jump():
    fr = []
    for f in range(4):
        L = Layer(64, 28)
        t = (f + 1) / 4
        cs = []
        for i in range(8):
            a = i / 8 * math.tau
            cs.append((32 + math.cos(a) * (6 + 20 * t), 22 + math.sin(a) * (2 + 5 * t), 2.2 + 2.4 * t))
        puff(L, cs, a=[1, 0.85, 0.55, 0.25][f], ink=1.0)
        fr.append(L.image())
    reg('dust_jump', fr, (32, 24), 20)


# ---------------------------------------------------------------- status & specials
def fx_ko_burst():
    fr = []
    jit = [1.0, 0.7, 0.9, 0.65, 1.0, 0.8, 0.95, 0.7, 1.0, 0.75, 0.88, 0.68]
    for f in range(6):
        L = Layer(160, 160)
        c = 80
        if f == 0:
            L.fill(L.circle(c, c, 22), WHITE)
            burst(L, c, c, 36, 14, 12, (ORG, YEL, WHITE), jit=jit)
        elif f == 1:
            ring(L, c, c, 42, 10, YEL)
            ring(L, c, c, 38, 4, WHITE)
            rays(L, c, c, 12, 46, 74, 3.0, WHITE, 1.0, jit=jit)
        elif f == 2:
            ring(L, c, c, 56, 6, YEL, 0.9)
            rays(L, c, c, 12, 58, 78, 2.2, WHITE, 0.8, jit=jit)
        elif f == 3:
            ring(L, c, c, 66, 3, YEL, 0.6)
            rays(L, c, c, 12, 66, 78, 1.6, WHITE, 0.5, jit=jit)
        elif f == 4:
            ring(L, c, c, 72, 1.8, YEL, 0.35)
        else:
            ring(L, c, c, 76, 1.0, YEL, 0.15)
        fr.append(L.image())
    reg('ko_burst', fr, (80, 80), 24)


def small_star(L, x, y, r, col, a=1.0, rot=0.0, ink=1.5):
    m = L.poly(star_pts(x, y, r, r * 0.45, 5, rot))
    tmp = Layer(L.w, L.h, L.ss)
    tmp.fill(tmp.dil(m, ink), FX_INK)
    sh, b, li, _ = tones(col)
    tmp.fill(m, b)
    tmp.fill(np.clip(m - tmp.shift(m, -0.8, -0.8), 0, 1), sh)
    tmp.fill(L.circle(x - r * 0.15, y - r * 0.15, r * 0.3) * m, li)
    tmp.c *= a
    tmp.a *= a
    L.over(tmp)


def fx_stars_dizzy():
    fr = []
    for f in range(4):
        L = Layer(64, 32)
        items = []
        for i in range(3):
            th = math.radians(f * 30 + i * 120)
            x, y = 32 + 22 * math.cos(th), 18 + 7 * math.sin(th)
            depth = (math.sin(th) + 1) / 2
            items.append((depth, x, y, 4.0 + 1.8 * depth, f * 25 + i * 40))
        for depth, x, y, r, rot in sorted(items):
            small_star(L, x, y, r, mix(hx('#c9a030'), hx('#ffe46a'), depth), 0.75 + 0.25 * depth, rot)
        fr.append(L.image())
    reg('stars_dizzy', fr, (32, 20), 8, loop=True)


def fx_levelup():
    fr = []
    GOLD = hx('#ffd34d')
    for f in range(6):
        L = Layer(128, 128)
        t = (f + 1) / 6
        k = 1.0 if f < 4 else (0.55 if f == 4 else 0.25)
        # beam
        X, Y = L.coords()
        beam = np.clip(1 - np.abs(X - 64) / (10 + 8 * t), 0, 1) ** 1.5 * np.clip((112 - Y) / 100, 0, 1) ** 0.6 * (Y < 112)
        L.fill(beam.astype(np.float32), hx('#fff4c0'), 0.55 * k)
        ring(L, 64, 112, 16 + 34 * ease_out(t), 3.0, GOLD, k, sy=0.32)
        ring(L, 64, 112, 12 + 22 * ease_out(t), 1.5, WHITE, k, sy=0.32)
        for i in range(3):
            y = 104 - (t * 70 + i * 22) % 90
            chev = [(52, y + 8), (64, y - 2), (76, y + 8), (76, y + 13), (64, y + 3), (52, y + 13)]
            m = L.poly(chev)
            L.fill(L.dil(m, 1.4), hx('#6a3a10'), k)
            L.fill(m, GOLD, k)
        rr = rng(31)
        for i in range(8):
            x = 64 + (rr.random() - 0.5) * 70
            y = 110 - rr.random() * 30 - t * 60
            s = 2 + 3 * rr.random()
            L.fill(L.poly(star_pts(x, y, s * (1 - 0.5 * t) + 1, 0.8, 4)), WHITE, k)
        fr.append(L.image())
    reg('levelup_burst', fr, (64, 112), 14)


def fx_charge_glow():
    fr = []
    for f in range(4):
        L = Layer(64, 64)
        X, Y = L.coords()
        d = np.sqrt((X - 32) ** 2 + (Y - 32) ** 2)
        pul = 0.8 + 0.2 * math.sin(f / 4 * math.tau)
        g = np.clip(1 - d / (26 * pul), 0, 1) ** 2
        L.fill(g.astype(np.float32), hx('#fff0c8'), 0.85)
        for i in range(4):
            a = f / 4 * math.tau / 4 + i * math.tau / 4
            L.fill(L.circle(32 + math.cos(a) * 18, 32 + math.sin(a) * 18, 2.0), WHITE)
        fr.append(L.image())
    reg('charge_glow', fr, (32, 32), 12, additive=True, loop=True)


def fx_coin_sparkle():
    fr = []
    for f in range(4):
        L = Layer(32, 32)
        s = [6, 13, 9, 4][f]
        L.fill(L.poly(star_pts(16, 16, s, 1.1, 4)), WHITE)
        L.fill(L.poly(star_pts(16, 16, s * 0.5, 0.9, 4, rot=45)), hx('#fff2b0'), 0.8)
        X, Y = L.coords()
        g = np.clip(1 - np.sqrt((X - 16) ** 2 + (Y - 16) ** 2) / (s * 0.7 + 1), 0, 1) ** 2
        L.fill(g.astype(np.float32), WHITE, 0.6)
        fr.append(L.image())
    reg('coin_sparkle', fr, (16, 16), 16, additive=True)


def mark(name, ch, col, size=(24, 32)):
    L = Layer(*size)
    w, h = size
    from vec import F_BUNGEE
    m = L.text(ch, F_BUNGEE, 26, w / 2, h - 4, anchor='ms')
    sh, b, li, ink = tones(col)
    L.fill(L.dil(m, 2.0), FX_INK)
    L.fill(m, b)
    L.fill(np.clip(m - L.shift(m, -1.2, -1.2), 0, 1), sh)
    L.fill(np.clip(m - L.shift(m, 1.0, 1.0), 0, 1), li)
    reg(name, [L.image()], (w // 2, h - 2), 1)


def fx_shockwave():
    fr = []
    for f in range(4):
        L = Layer(144, 40)
        t = (f + 1) / 4
        rx = 18 + 52 * ease_out(t)
        k = [1, 0.8, 0.5, 0.25][f]
        o = L.ellipse(72, 22, rx, rx * 0.26)
        i = L.ellipse(72, 22 - 1, rx - 7 * (1 - t) - 2, (rx - 7 * (1 - t) - 2) * 0.24)
        m = np.clip(o - i, 0, 1)
        L.fill(L.dil(m, 1.2), DUST_INK, k * 0.8)
        L.fill(m, hx('#fff0d4'), k)
        L.fill(np.clip(m - L.shift(m, 0, -1.2), 0, 1), DUST, k)
        rr = rng(17)
        for j in range(10):
            a = rr.random() * math.tau
            x = 72 + math.cos(a) * rx * (0.9 + 0.2 * rr.random())
            y = 22 + math.sin(a) * rx * 0.26 - (8 * t * (1 - t) * 4) * rr.random()
            L.fill(L.circle(x, y, 1.2 + rr.random()), hx('#8c7c80'), k)
        fr.append(L.image())
    reg('shockwave', fr, (72, 22), 20)


WATER = (hx('#2f6e98'), hx('#6fb8e0'), hx('#d6f2ff'), hx('#16304a'))


def water_drop(L, x, y, r, a=1.0, stretch=1.0):
    m = L.ellipse(x, y, r, r * stretch)
    tmp = Layer(L.w, L.h, L.ss)
    tmp.fill(tmp.dil(m, 1.0), WATER[3])
    tmp.fill(m, WATER[1])
    tmp.fill(np.clip(m - tmp.shift(m, -0.7, -0.7), 0, 1), WATER[0])
    tmp.fill(L.circle(x - r * 0.3, y - r * 0.35 * stretch, r * 0.35) * m, WATER[2])
    tmp.c *= a
    tmp.a *= a
    L.over(tmp)


def fx_splash():
    fr = []
    for f in range(5):
        L = Layer(64, 48)
        t = (f + 1) / 5
        cx, by = 32, 44
        if f <= 2:
            hgt = [10, 22, 26][f]
            wid = [10, 14, 18][f]
            pts = [(cx - wid, by)]
            for i, u in enumerate(np.linspace(-1, 1, 9)):
                spike = hgt * (0.55 + 0.45 * (i % 2 == 0)) * (1 - 0.35 * abs(u))
                pts.append((cx + u * wid * 0.85, by - spike))
            pts.append((cx + wid, by))
            m = L.poly(pts)
            L.fill(L.dil(m, 1.4), WATER[3])
            L.fill(m, WATER[1])
            L.fill(np.clip(m - L.shift(m, -1.2, 0), 0, 1), WATER[0])
            L.fill(np.clip(m - L.shift(m, 1.0, 1.4), 0, 1), WATER[2])
        rr = rng(41)
        for i in range(9):
            a = math.radians(-90 + (rr.random() - 0.5) * 140)
            sp = 30 + 18 * rr.random()
            x = cx + math.cos(a) * sp * t
            y = by - 6 + math.sin(a) * sp * t + 60 * t * t
            if y < by and f >= 1:
                water_drop(L, x, y, 1.6 + rr.random() * 1.2, a=1 - 0.6 * t, stretch=1.3)
        ring(L, cx, by - 1, 8 + 22 * t, 1.6, WATER[2], 0.9 - 0.7 * t, sy=0.25)
        fr.append(L.image())
    reg('splash', fr, (32, 44), 20)


def fx_steam_puff():
    fr = []
    for f in range(6):
        L = Layer(48, 64)
        t = (f + 1) / 6
        y = 56 - 36 * t
        r = 3.5 + 8 * t
        cs = [(24, y, r), (24 - r * 0.8, y + r * 0.35, r * 0.7), (24 + r * 0.8, y + r * 0.3, r * 0.72),
              (24 + r * 0.15, y - r * 0.6, r * 0.62), (24 - r * 0.45, y - r * 0.2, r * 0.55)]
        soft_puff(L, cs, hx('#f2f2f6'), a=0.75 * (1 - t ** 1.6), soft=1.5 + 2 * t)
        fr.append(L.image())
    reg('steam_puff', fr, (24, 60), 12)


def fx_smoke_puff():
    fr = []
    for f in range(6):
        L = Layer(48, 48)
        t = (f + 1) / 6
        y = 36 - 16 * t
        r = 3.5 + 7 * t
        cs = [(24, y, r), (24 - r * 0.8, y + r * 0.35, r * 0.7), (24 + r * 0.8, y + r * 0.3, r * 0.72),
              (24 + r * 0.15, y - r * 0.6, r * 0.62)]
        soft_puff(L, cs, hx('#58525e'), a=0.85 * (1 - t ** 1.5), soft=1.0 + 1.5 * t)
        soft_puff(L, [(x - 1.5, y - 2, r * 0.5) for x, y, r in cs], hx('#8e8896'), a=0.5 * (1 - t), soft=1.5)
        fr.append(L.image())
    reg('smoke_puff', fr, (24, 40), 12)


def fx_rain_splash():
    fr = []
    col = hx('#d8ecfa')
    for f in range(4):
        L = Layer(24, 12)
        if f == 0:
            L.fill(L.ellipse(12, 9, 2, 1.2), col, 0.9)
        elif f == 1:
            for s in (-1, 1):
                L.fill(L.stroke([(12, 9), (12 + s * 4, 4)], 1.2), col, 0.85)
            L.fill(L.circle(12, 3, 1.0), col, 0.85)
        elif f == 2:
            ring(L, 12, 9, 6, 1.2, col, 0.7, sy=0.35)
            L.fill(L.circle(7, 5, 0.9), col, 0.6)
            L.fill(L.circle(17, 5, 0.9), col, 0.6)
        else:
            ring(L, 12, 9, 9, 1.0, col, 0.35, sy=0.35)
        fr.append(L.image())
    reg('rain_splash', fr, (12, 9), 20)


def fx_drip():
    fr = []
    for f in range(4):
        L = Layer(16, 32)
        if f == 0:
            water_drop(L, 8, 6, 2.2, stretch=1.4)
        elif f == 1:
            water_drop(L, 8, 18, 2.0, stretch=1.8)
        elif f == 2:
            for s in (-1, 1):
                L.fill(L.stroke([(8, 29), (8 + s * 4, 25)], 1.1), WATER[2], 0.9)
            L.fill(L.ellipse(8, 29, 3, 1), WATER[1], 0.9)
        else:
            ring(L, 8, 29, 6, 1.0, WATER[2], 0.5, sy=0.3)
        fr.append(L.image())
    reg('drip', fr, (8, 29), 12)


# ---------------------------------------------------------------- debris (variants)
def debris_set(name, size, kind, seed):
    fr = []
    r = rng(seed)
    w, h = size
    for v in range(4):
        L = Layer(w, h)
        cx, cy = w / 2, h / 2
        rot = r.random() * 360
        if kind == 'wood':
            ln, wd = 5 + v, 1.8 + 0.4 * (v % 2)
            p = rot_pts([(cx - ln, cy - wd * 0.2), (cx - ln * 0.2, cy - wd), (cx + ln, cy - wd * 0.3),
                         (cx + ln * 0.5, cy + wd * 0.7), (cx - ln * 0.7, cy + wd * 0.6)], rot, cx, cy)
            draw_chip(L, p, hx('#b97f4a'), 1.0)
        elif kind == 'glass':
            s = 4 + v * 0.8
            p = rot_pts([(cx, cy - s), (cx + s * 0.75, cy + s * 0.55), (cx - s * 0.55, cy + s * 0.35)], rot, cx, cy)
            draw_chip(L, p, hx('#a8e4ee'), 0.95, ink=hx('#1c3c48'), hi=WHITE)
        elif kind == 'stone':
            s = 3.4 + v * 0.7
            p = rot_pts([(cx - s, cy - s * 0.3), (cx - s * 0.1, cy - s), (cx + s, cy - s * 0.4), (cx + s * 0.6, cy + s * 0.8),
                         (cx - s * 0.8, cy + s * 0.7)], rot, cx, cy)
            draw_chip(L, p, hx('#9a8f88'), 1.0)
        elif kind == 'paper':
            s = 4 + v * 0.6
            p = rot_pts([(cx - s, cy - s * 0.6), (cx + s, cy - s * 0.8), (cx + s * 0.8, cy + s * 0.6), (cx - s * 0.9, cy + s * 0.7)], rot, cx, cy)
            draw_chip(L, p, hx('#eee4cc'), 1.0, ink=hx('#5a4a50'))
            L.fill(L.stroke(rot_pts([(cx - s * 0.5, cy - 0.5), (cx + s * 0.5, cy - 0.8)], rot, cx, cy), 0.6), hx('#7a6a70'), 0.8)
        elif kind == 'metal':
            s = 3 + v * 0.5
            if v % 2 == 0:
                p = [(cx + s * math.cos(math.radians(a + rot)), cy + s * math.sin(math.radians(a + rot))) for a in range(0, 360, 60)]
                draw_chip(L, p, hx('#9aa4b4'), 1.0, ink=hx('#1c2030'), hi=WHITE)
                L.fill(L.circle(cx, cy, s * 0.4), hx('#3a4050'))
            else:
                p = rot_pts([(cx - s * 1.2, cy - 1.1), (cx + s * 1.2, cy - 1.1), (cx + s * 1.2, cy + 1.1), (cx - s * 1.2, cy + 1.1)], rot, cx, cy)
                draw_chip(L, p, hx('#9aa4b4'), 1.0, ink=hx('#1c2030'), hi=WHITE)
        elif kind == 'spark':
            ln = 10 + v * 2.5
            m = streak(L, cx - ln, cy + (v - 1.5) * 0.6, cx + ln * 0.5, cy, 0.4, 2.4)
            X, Y = L.coords()
            t = np.clip((X - (cx - ln)) / (ln * 1.5), 0, 1)
            col = np.dstack([np.ones_like(t), 0.55 + 0.45 * t, 0.15 + 0.85 * t ** 2]).astype(np.float32)
            L.fill_rgb(m, col, 1.0)
        fr.append(L.image())
    reg(name, fr, (w // 2, h // 2), 1, additive=(kind == 'spark'))


# ---------------------------------------------------------------- shared textures
def tex_glow_soft():
    L = Layer(256, 256, ss=1)
    X, Y = L.coords()
    d = np.sqrt((X - 128) ** 2 + (Y - 128) ** 2) / 128
    g = np.clip(1 - d, 0, 1)
    a = (g ** 2 * (3 - 2 * g)) ** 1.6
    L.fill(a.astype(np.float32), WHITE)
    reg('glow_soft', [L.image()], (128, 128), 1, additive=True)


def tex_glow_streak():
    L = Layer(256, 64, ss=1)
    X, Y = L.coords()
    gx = np.clip(1 - np.abs(X - 128) / 128, 0, 1)
    gy = np.exp(-((Y - 32) / 9.0) ** 2)
    a = (gx ** 2 * (3 - 2 * gx)) * gy
    L.fill(a.astype(np.float32), WHITE)
    reg('glow_streak', [L.image()], (128, 32), 1, additive=True)


def tex_shadow_soft():
    L = Layer(128, 48, ss=1)
    X, Y = L.coords()
    d = np.sqrt(((X - 64) / 62) ** 2 + ((Y - 24) / 22) ** 2)
    g = np.clip((1 - d) / 0.85, 0, 1)
    a = g ** 1.6 * (3 - 2 * g) / 1.0
    L.fill(np.clip(a, 0, 1).astype(np.float32), (0, 0, 0))
    reg('shadow_soft', [L.image()], (64, 24), 1)


def tex_light_cone():
    L = Layer(128, 192, ss=1)
    X, Y = L.coords()
    t = Y / 192
    half = 10 + 54 * t
    gx = np.clip(1 - np.abs(X - 64) / half, 0, 1)
    gx = gx ** 2 * (3 - 2 * gx)
    gy = np.clip(1 - t, 0, 1) ** 1.3 * np.clip(Y / 10, 0, 1)
    L.fill((gx * gy * 0.95).astype(np.float32), WHITE)
    reg('light_cone', [L.image()], (64, 0), 1, additive=True)


def tex_sweat():
    L = Layer(16, 16)
    m = L.poly(bez((8, 2), (13, 10), (8, 14)) + bez((8, 14), (3, 10), (8, 2)))
    L.fill(L.dil(m, 1.2), WATER[3])
    L.fill(m, hx('#9fd8f4'))
    L.fill(L.ellipse(6.8, 9.5, 1.2, 2) * m, WHITE)
    reg('sweat', [L.image()], (8, 8), 1)


def tex_target_shadow():
    L = Layer(64, 20)
    m = L.ellipse(32, 10, 28, 7)
    L.fill(m, (0, 0, 0), 0.35)
    ring(L, 32, 10, 28, 1.6, hx('#ffffff'), 0.5, sy=0.25)
    reg('target_shadow', [L.image()], (32, 10), 1)


def main():
    os.makedirs(OUT, exist_ok=True)
    fx_hit_light()
    fx_hit_heavy()
    fx_hit_kick()
    fx_hit_metal()
    fx_hit_material('hit_wood', 'wood', 101, dust_col=hx('#c9b49a'))
    fx_hit_material('hit_glass', 'glass', 202, flash_cols=(hx('#bff0ff'), hx('#e8fbff'), WHITE))
    fx_hit_material('hit_stone', 'stone', 303, dust_col=hx('#b0a69c'))
    fx_hit_soft()
    fx_block()
    fx_perfect_block()
    fx_arc_punch()
    # arcs: anchor = the attacker's FEET (ground point) for a standard 96 tx adult facing right
    arc_set('arc_kick', (72, 80), (16, 76), 16, 30, 36, 12, 80, -20)
    arc_set('arc_swing', (96, 128), (32, 124), 36, 54, 48, 16, -125, 40)
    arc_set('arc_sweep', (136, 56), (68, 40), 68, 36, 62, 12, 190, -5, sy=0.3, lines=1)
    arc_set('arc_heavy', (104, 128), (40, 124), 44, 54, 52, 24, -135, 45, lines=3)
    arc_set('arc_rising', (72, 136), (24, 132), 24, 88, 50, 13, 60, -100)
    fx_dust_land()
    fx_dust_step()
    fx_dust_slide()
    fx_dust_fall()
    fx_dust_jump()
    fx_ko_burst()
    fx_stars_dizzy()
    fx_levelup()
    fx_charge_glow()
    fx_coin_sparkle()
    mark('exclaim', '!', hx('#ff6a3a'))
    mark('question', '?', hx('#ffd84a'))
    fx_shockwave()
    fx_splash()
    fx_steam_puff()
    fx_smoke_puff()
    fx_rain_splash()
    fx_drip()
    debris_set('chip_wood', (16, 16), 'wood', 1)
    debris_set('shard_glass', (16, 16), 'glass', 2)
    debris_set('spark_streak', (24, 8), 'spark', 3)
    debris_set('chunk_stone', (16, 16), 'stone', 4)
    debris_set('scrap_paper', (16, 16), 'paper', 5)
    debris_set('bit_metal', (12, 12), 'metal', 6)
    tex_glow_soft()
    tex_glow_streak()
    tex_shadow_soft()
    tex_light_cone()
    tex_sweat()
    tex_target_shadow()
    meta = {'_meta': {'density': 2, 'doc': 'v2 FX strips at density 2 (draw at scale 0.5). anchor = pivot in tx '
                      'within a cell; arc_* anchors are the attacker FEET for a 96 tx adult (scale by height/96); effects face RIGHT (mirror for left). additive = meant for additive blend; '
                      'arc_* are white for engine tinting. See docs/visual/ASSET_CONTRACT_V2.md.'}}
    meta.update(dict(sorted(META.items())))
    with open(os.path.join(OUT, 'fx.json'), 'w') as fh:
        json.dump(meta, fh, indent=1)
    print('fx2:', len(META), 'effects')


if __name__ == '__main__':
    main()
