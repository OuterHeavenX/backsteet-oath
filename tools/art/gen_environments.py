#!/usr/bin/env python3
"""BACKSTREET OATH - environment art generator.

Procedurally draws every room background, the district parallax layers, all props
(+ props.json), the title backdrop and the district map.  Pure Python 3 + Pillow +
numpy, fully deterministic (RNGs are seeded from room ids / x positions).

All imagery is original and project-owned.  Re-run to rebuild:

    python3 tools/art/gen_environments.py            # everything
    python3 tools/art/gen_environments.py --rooms oq_kettle int_diner
    python3 tools/art/gen_environments.py --only props

Contract: docs/ART_BIBLE.md, game/data/rooms.json (read-only input).
"""
import argparse
import hashlib
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ROOMS_JSON = os.path.join(ROOT, "game", "data", "rooms.json")
BG_DIR = os.path.join(ROOT, "game", "assets", "bg")
PROP_DIR = os.path.join(ROOT, "game", "assets", "props")
UI_DIR = os.path.join(ROOT, "game", "assets", "ui")

H = 360
FACADE_BOTTOM = 214      # exterior facade / ground boundary
INT_WALL_BOTTOM = 196    # interior wall / floor boundary
CURB_Y = 344             # bottom of walkable band; below = foreground strip


# ----------------------------------------------------------------------------
# colour helpers
# ----------------------------------------------------------------------------
def C(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def dk(c, f=0.25):
    return tuple(max(0, int(v * (1 - f))) for v in c)


def lt(c, f=0.25):
    return tuple(min(255, int(v + (255 - v) * f)) for v in c)


INK = C("#1a1220")
P = {k: C(v) for k, v in dict(
    ink="#1a1220",
    brick="#a04a3a", brick_d="#7a3428", brick_l="#c8664a", mortar="#5a3a34",
    asphalt="#3a3a48", asphalt_l="#4a4a5a", sidewalk="#8a8478", sidewalk_l="#a8a090",
    curb="#6a6660", wood="#8a5a34", wood_d="#5e3a1e", rust="#9a5a30",
    steel="#6a7280", steel_l="#9aa2b0", water="#2a5a7a", water_m="#3a7a9a", water_l="#6ab0c8",
    red="#c03a3a", red_d="#7a2030", orange="#e07a30", orange_d="#a0501e",
    mustard="#e0b040", mustard_d="#a87a20", yellow="#f0c040", green="#4a9a4a", green_d="#2a5a3a",
    teal="#3a9a9a", teal_d="#22605e", blue="#3a6ac0", blue_d="#22408a", navy="#22305a",
    navy_d="#141c38", purple="#7a4aa0", purple_d="#4a2a6a", gray="#8a8a96", gray_d="#5a5a66",
    char="#3a3a46", char_d="#24242e", white="#e8e4dc", white_d="#b8b0a8", denim="#4a6a9a",
    brown="#7a5030", brown_d="#50341e", tan="#c8a070", tan_d="#987048", black="#2a2a32",
    black_d="#18181e", cream="#e8d8b0",
    n_pink="#ff4aa0", n_cyan="#4af0f0", n_yellow="#fff06a", n_green="#7af04a",
    lamp="#ffd890", lamp_d="#f0b060", sodium="#ffb050",
).items()}

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16.0 + 1 / 32.0


def seed_of(*parts):
    s = ":".join(str(p) for p in parts)
    return int(hashlib.sha1(s.encode()).hexdigest()[:12], 16)


def rng_of(*parts):
    return random.Random(seed_of(*parts))


# ----------------------------------------------------------------------------
# pixel font (original 5x7 caps)
# ----------------------------------------------------------------------------
_GLYPHS = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.####",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": "###|.#.|.#.|.#.|.#.|.#.|###",
    "J": "..###|...#.|...#.|...#.|#..#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|##..#|##..#|#.#.#|#..##|#..##|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    "1": ".#.|##.|.#.|.#.|.#.|.#.|###",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": "####.|....#|....#|.###.|....#|....#|####.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": ".###.|#....|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|....#|.###.",
    "&": ".##..|#..#.|#.#..|.#...|#.#.#|#..#.|.##.#",
    "'": "#|#|.|.|.|.|.",
    "-": "....|....|....|####|....|....|....",
    ".": ".|.|.|.|.|.|#",
    ",": "..|..|..|..|..|.#|#.",
    "!": "#|#|#|#|#|.|#",
    "?": ".###.|#...#|....#|...#.|..#..|.....|..#..",
    ":": ".|.|#|.|#|.|.",
    "/": "....#|...#.|...#.|..#..|.#...|.#...|#....",
    "+": ".....|..#..|..#..|#####|..#..|..#..|.....",
    "$": "..#..|.####|#.#..|.###.|..#.#|####.|..#..",
    "*": ".....|#.#.#|.###.|#####|.###.|#.#.#|.....",
    " ": "...|...|...|...|...|...|...",
}
GLYPH = {}
for _k, _v in _GLYPHS.items():
    rows = _v.split("|")
    GLYPH[_k] = [[ch == "#" for ch in r] for r in rows]


def text_w(s, scale=1, bold=False, spacing=1):
    w = 0
    for ch in s.upper():
        g = GLYPH.get(ch, GLYPH[" "])
        w += (len(g[0]) + (1 if bold else 0)) * scale + spacing * scale
    return max(0, w - spacing * scale)


def text_mask(s, scale=1, bold=False, spacing=1):
    w = text_w(s, scale, bold, spacing)
    m = np.zeros((7 * scale, max(1, w)), bool)
    x = 0
    for ch in s.upper():
        g = GLYPH.get(ch, GLYPH[" "])
        gw = len(g[0])
        for yy, row in enumerate(g):
            for xx, on in enumerate(row):
                if on:
                    m[yy * scale:(yy + 1) * scale, x + xx * scale:x + (xx + 1 + (1 if bold else 0)) * scale] = True
        x += (gw + (1 if bold else 0)) * scale + spacing * scale
    return m


# ----------------------------------------------------------------------------
# canvas
# ----------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, fill=None):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), np.uint8)
        self.em = np.zeros((h, w), np.uint8)     # emissive mask (protected from grading)
        self.cx0, self.cx1 = 0, w                # horizontal clip window
        if fill is not None:
            self.a[..., :3] = fill
            self.a[..., 3] = 255

    # -- primitives ---------------------------------------------------------
    def clipped(self, x0, x1):
        cv = self

        class _Ctx:
            def __enter__(s):
                s.old = (cv.cx0, cv.cx1)
                cv.cx0, cv.cx1 = max(0, int(x0)), min(cv.w, int(x1))
                return cv

            def __exit__(s, *a):
                cv.cx0, cv.cx1 = s.old
        return _Ctx()

    def _clip(self, x0, y0, x1, y1):
        x0 = max(self.cx0, min(self.cx1, int(x0)))
        x1 = max(self.cx0, min(self.cx1, int(x1)))
        y0 = max(0, min(self.h, int(y0)))
        y1 = max(0, min(self.h, int(y1)))
        return x0, y0, x1, y1

    def rect(self, x, y, w, h, c, em=0):
        x0, y0, x1, y1 = self._clip(x, y, x + w, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        self.a[y0:y1, x0:x1, :3] = c[:3]
        self.a[y0:y1, x0:x1, 3] = 255
        self.em[y0:y1, x0:x1] = em

    def box(self, x, y, w, h, c, edge=None, em=0):
        """Filled rect with optional 1px edge colour."""
        self.rect(x, y, w, h, edge if edge else c, em)
        if edge:
            self.rect(x + 1, y + 1, w - 2, h - 2, c, em)

    def px(self, x, y, c, em=0):
        x, y = int(x), int(y)
        if self.cx0 <= x < self.cx1 and 0 <= y < self.h:
            self.a[y, x, :3] = c[:3]
            self.a[y, x, 3] = 255
            self.em[y, x] = em

    def hl(self, x, y, w, c, em=0):
        self.rect(x, y, w, 1, c, em)

    def vl(self, x, y, h, c, em=0):
        self.rect(x, y, 1, h, c, em)

    def clear(self, x, y, w, h):
        x0, y0, x1, y1 = self._clip(x, y, x + w, y + h)
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = 0
            self.em[y0:y1, x0:x1] = 0

    def blend(self, x, y, w, h, c, t, only_opaque=True):
        x0, y0, x1, y1 = self._clip(x, y, x + w, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        reg = self.a[y0:y1, x0:x1, :3].astype(np.float32)
        reg = reg * (1 - t) + np.array(c[:3], np.float32) * t
        if only_opaque:
            m = self.a[y0:y1, x0:x1, 3:4] > 0
            self.a[y0:y1, x0:x1, :3] = np.where(m, reg, self.a[y0:y1, x0:x1, :3]).astype(np.uint8)
        else:
            self.a[y0:y1, x0:x1, :3] = reg.astype(np.uint8)
            self.a[y0:y1, x0:x1, 3] = 255

    def mask_fill(self, x, y, mask, c, em=0):
        """Paint colour where boolean mask (h,w) is True, mask placed at x,y."""
        mh, mw = mask.shape
        x0, y0, x1, y1 = self._clip(x, y, x + mw, y + mh)
        if x1 <= x0 or y1 <= y0:
            return
        sub = mask[y0 - y:y1 - y, x0 - x:x1 - x]
        reg = self.a[y0:y1, x0:x1]
        reg[sub, :3] = c[:3]
        reg[sub, 3] = 255
        self.em[y0:y1, x0:x1][sub] = em

    def _shape_mask(self, bbox, drawfn):
        x0, y0, x1, y1 = [int(math.floor(v)) for v in bbox]
        w, h = x1 - x0 + 2, y1 - y0 + 2
        if w <= 0 or h <= 0:
            return
        im = Image.new("L", (w, h), 0)
        drawfn(ImageDraw.Draw(im), x0, y0)
        return x0, y0, np.array(im) > 127

    def poly(self, pts, c, em=0):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        r = self._shape_mask((min(xs), min(ys), max(xs), max(ys)),
                             lambda d, ox, oy: d.polygon([(px - ox, py - oy) for px, py in pts], fill=255))
        if r:
            self.mask_fill(r[0], r[1], r[2], c, em)

    def ellipse(self, x0, y0, x1, y1, c, em=0):
        """Filled ellipse inside inclusive bbox."""
        r = self._shape_mask((x0, y0, x1, y1),
                             lambda d, ox, oy: d.ellipse([x0 - ox, y0 - oy, x1 - ox, y1 - oy], fill=255))
        if r:
            self.mask_fill(r[0], r[1], r[2], c, em)

    def line(self, x0, y0, x1, y1, c, em=0):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, c, em)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def sag(self, x0, y0, x1, y1, depth, c, em=0, step=1):
        """Catenary-ish sagging wire; returns list of points."""
        pts = []
        n = max(2, int(abs(x1 - x0) / step))
        for i in range(n + 1):
            t = i / n
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t + depth * 4 * t * (1 - t)
            pts.append((int(round(x)), int(round(y))))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            self.line(ax, ay, bx, by, c, em)
        return pts

    def text(self, x, y, s, c, scale=1, bold=False, shadow=None, outline=None, em=0, spacing=1):
        m = text_mask(s, scale, bold, spacing)
        if outline is not None:
            o = np.zeros((m.shape[0] + 2, m.shape[1] + 2), bool)
            for dy in (0, 1, 2):
                for dx in (0, 1, 2):
                    o[dy:dy + m.shape[0], dx:dx + m.shape[1]] |= m
            self.mask_fill(x - 1, y - 1, o, outline, 0)
        if shadow is not None:
            self.mask_fill(x + 1, y + 1, m, shadow, 0)
        self.mask_fill(x, y, m, c, em)
        return m.shape[1]

    def text_c(self, cx, y, s, c, scale=1, **kw):
        w = text_w(s, scale, kw.get("bold", False), kw.get("spacing", 1))
        self.text(int(cx - w / 2), y, s, c, scale, **kw)
        return w

    # -- gradients / textures --------------------------------------------------
    def vgrad(self, x, y, w, h, stops, em=0, levels=None):
        """Dithered vertical gradient through colour stops."""
        x0, y0, x1, y1 = self._clip(x, y, x + w, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        n = len(stops)
        levels = levels or max(2, min(24, h // 3))
        pal = []
        for i in range(levels):
            t = i / (levels - 1) * (n - 1)
            j = min(n - 2, int(t))
            pal.append(mix(stops[j], stops[j + 1], t - j))
        pal = np.array(pal, np.float32)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        t = (yy - y) / max(1, h - 1) * (levels - 1)
        base = np.floor(t).astype(int)
        frac = t - base
        thr = BAYER[yy % 4, xx % 4]
        idx = np.clip(base + (frac > thr), 0, levels - 1)
        self.a[y0:y1, x0:x1, :3] = pal[idx].astype(np.uint8)
        self.a[y0:y1, x0:x1, 3] = 255
        self.em[y0:y1, x0:x1] = em

    def hgrad(self, x, y, w, h, stops, em=0, levels=None):
        x0, y0, x1, y1 = self._clip(x, y, x + w, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        n = len(stops)
        levels = levels or max(2, min(24, w // 3))
        pal = np.array([mix(stops[min(n - 2, int(i / (levels - 1) * (n - 1)))],
                            stops[min(n - 2, int(i / (levels - 1) * (n - 1))) + 1],
                            i / (levels - 1) * (n - 1) - min(n - 2, int(i / (levels - 1) * (n - 1))))
                        for i in range(levels)], np.float32)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        t = (xx - x) / max(1, w - 1) * (levels - 1)
        base = np.floor(t).astype(int)
        idx = np.clip(base + ((t - base) > BAYER[yy % 4, xx % 4]), 0, levels - 1)
        self.a[y0:y1, x0:x1, :3] = pal[idx].astype(np.uint8)
        self.a[y0:y1, x0:x1, 3] = 255
        self.em[y0:y1, x0:x1] = em

    def dither_blend(self, x, y, w, h, c, t):
        """Ordered-dither a colour over a region at coverage t (0..1)."""
        x0, y0, x1, y1 = self._clip(x, y, x + w, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        m = (BAYER[yy % 4, xx % 4] < t) & (self.a[y0:y1, x0:x1, 3] > 0)
        reg = self.a[y0:y1, x0:x1]
        reg[m, :3] = c[:3]

    def noise_tint(self, x, y, w, h, rng, amount=6, density=0.08, cell=1):
        """Sparse low-contrast speckle."""
        x0, y0, x1, y1 = self._clip(x, y, x + w, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        r = np.random.default_rng(rng.randrange(1 << 30))
        hh, ww = (y1 - y0 + cell - 1) // cell, (x1 - x0 + cell - 1) // cell
        n = r.random((hh, ww))
        d = np.where(n < density / 2, -amount, np.where(n > 1 - density / 2, amount, 0)).astype(np.int16)
        if cell > 1:
            d = np.kron(d, np.ones((cell, cell), np.int16))[:y1 - y0, :x1 - x0]
        reg = self.a[y0:y1, x0:x1, :3].astype(np.int16) + d[..., None]
        self.a[y0:y1, x0:x1, :3] = np.clip(reg, 0, 255).astype(np.uint8)

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Image.fromarray(self.a, "RGBA").save(path, optimize=True)


# ----------------------------------------------------------------------------
# material textures
# ----------------------------------------------------------------------------
def tex_brick(cv, x, y, w, h, base=None, shadow=None, hi=None, mortar=None, seed=0, bw=8, bh=4,
              weather=0.0, calm=False):
    base = base or P["brick"]
    shadow = shadow or P["brick_d"]
    hi = hi or P["brick_l"]
    mortar = mortar or mix(P["mortar"], base, 0.35)
    x0, y0, x1, y1 = cv._clip(x, y, x + w, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    row = (yy - y) // bh
    off = (row % 2) * (bw // 2)
    col = (xx - x + off) // bw
    is_m = ((yy - y) % bh == bh - 1) | ((xx - x + off) % bw == bw - 1)
    sd = int(seed) % 100003
    hsh = ((row * 7919 + 13) * (col * 104729 + 7) + sd * 31337) % 65521
    hv = (hsh % 100)
    pal = np.array([base, mix(base, shadow, 0.35), mix(base, hi, 0.3), mix(base, shadow, 0.6),
                    mortar], np.float32)
    if calm:
        idx = np.where(hv < 80, 0, np.where(hv < 93, 1, 2))
    else:
        idx = np.where(hv < 70, 0, np.where(hv < 85, 1, np.where(hv < 95, 2, 3)))
    idx = np.where(is_m, 4, idx)
    # top-edge highlight of each brick (light from above)
    out = pal[idx]
    if weather > 0:
        t = ((yy - y) / max(1, h)) ** 2 * weather
        out = out * (1 - t[..., None] * 0.35)
    cv.a[y0:y1, x0:x1, :3] = out.astype(np.uint8)
    cv.a[y0:y1, x0:x1, 3] = 255
    cv.em[y0:y1, x0:x1] = 0


def tex_siding(cv, x, y, w, h, base, pitch=5):
    cv.rect(x, y, w, h, base)
    sh = dk(base, 0.22)
    hi = lt(base, 0.12)
    for yy in range(y, y + h, pitch):
        cv.hl(x, yy + pitch - 1, w, sh)
        cv.hl(x, yy, w, hi)


def tex_corrugated(cv, x, y, w, h, base, pitch=4, seed=0, rust=0.0):
    x0, y0, x1, y1 = cv._clip(x, y, x + w, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    pal = np.array([lt(base, 0.18), base, base, dk(base, 0.18), dk(base, 0.3)][:pitch + 1], np.float32)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    k = (xx - x) % pitch
    idx = np.where(k == 0, 0, np.where(k == pitch - 1, 3, 1))
    out = pal[idx]
    if rust > 0:
        r = np.random.default_rng(seed)
        # vertical rust streaks
        cols = r.random(x1 - x0) < rust
        streak = np.zeros((y1 - y0, x1 - x0), bool)
        for ci in np.nonzero(cols)[0]:
            ln = r.integers(4, max(5, (y1 - y0) // 2))
            st = r.integers(0, max(1, y1 - y0 - ln))
            streak[st:st + ln, ci] = True
        rc = np.array(mix(P["rust"], base, 0.3), np.float32)
        out[streak] = out[streak] * 0.4 + rc * 0.6
    cv.a[y0:y1, x0:x1, :3] = out.astype(np.uint8)
    cv.a[y0:y1, x0:x1, 3] = 255
    cv.em[y0:y1, x0:x1] = 0


def tex_concrete(cv, x, y, w, h, base, seed=0, panel=None, stains=True):
    cv.rect(x, y, w, h, base)
    rng = rng_of("conc", seed, x, y)
    cv.noise_tint(x, y, w, h, rng, amount=5, density=0.10)
    if panel:
        pw, ph = panel
        sh = dk(base, 0.18)
        for xx in range(x + pw, x + w, pw):
            cv.vl(xx, y, h, sh)
        for yy in range(y + ph, y + h, ph):
            cv.hl(x, yy, w, sh)
    if stains:
        for _ in range(max(1, w // 40)):
            sx = rng.randrange(x, x + max(1, w - 6))
            sw = rng.randrange(2, 6)
            sy = rng.randrange(y, y + max(1, h // 2))
            cv.dither_blend(sx, sy, sw, rng.randrange(h // 4 + 1, h // 2 + 2), dk(base, 0.15), 0.5)


def tex_planks_h(cv, x, y, w, h, base, ph=6, seed=0, joints=True, nails=True):
    rng = rng_of("planks", seed, x, y)
    sh = dk(base, 0.3)
    hi = lt(base, 0.12)
    yy = y
    while yy < y + h:
        hh = min(ph, y + h - yy)
        tone = mix(base, dk(base, 0.15), rng.random() * 0.8)
        cv.rect(x, yy, w, hh, tone)
        cv.hl(x, yy, w, mix(tone, hi, 0.6))
        cv.hl(x, yy + hh - 1, w, sh)
        if joints:
            jx = x + rng.randrange(0, 40)
            while jx < x + w:
                cv.vl(jx, yy, hh, sh)
                if nails and hh > 3:
                    cv.px(jx + 2, yy + 1, dk(base, 0.45))
                    cv.px(jx - 2, yy + 1, dk(base, 0.45))
                jx += rng.randrange(36, 72)
        yy += ph


def tex_planks_v(cv, x, y, w, h, base, pw=6, seed=0):
    rng = rng_of("vplanks", seed, x, y)
    sh = dk(base, 0.3)
    hi = lt(base, 0.12)
    for xx in range(x, x + w, pw):
        tone = mix(base, dk(base, 0.15), rng.random() * 0.8)
        cv.rect(xx, y, pw, h, tone)
        cv.vl(xx, y, h, mix(tone, hi, 0.5))
        cv.vl(xx + pw - 1, y, h, sh)


def tex_stone(cv, x, y, w, h, base, seed=0, bh=8, bw=(10, 22)):
    """Dressed stone blocks."""
    rng = rng_of("stone", seed, x, y)
    sh = dk(base, 0.3)
    hi = lt(base, 0.15)
    yy = y
    r = 0
    while yy < y + h:
        hh = min(bh, y + h - yy)
        xx = x - (r % 2) * (bw[0] // 2)
        while xx < x + w:
            ww = rng.randrange(bw[0], bw[1])
            tone = mix(base, sh, rng.random() * 0.35)
            if rng.random() < 0.15:
                tone = mix(base, hi, 0.3)
            cv.rect(xx, yy, ww, hh, tone)
            cv.hl(xx, yy, ww, mix(tone, hi, 0.5))
            cv.vl(xx + ww - 1, yy, hh, sh)
            cv.hl(xx, yy + hh - 1, ww, sh)
            xx += ww
        yy += bh
        r += 1


# ----------------------------------------------------------------------------
# themes (district lighting)
# ----------------------------------------------------------------------------
THEMES = {
    "old_quarter": dict(night=False, grade_f=(1.07, 0.93, 0.84), grade_g=(1.04, 0.96, 0.90), bloom=0.55,
                        glass=[C("#f0c090"), C("#c07a6a"), C("#5a3a50")], top_light=C("#ffb070"),
                        top_light_amt=0.24, shade=C("#5a3050")),
    "canal_market": dict(night=False, grade_f=(1.02, 1.01, 1.0), grade_g=(1.02, 1.01, 1.0), bloom=0.3,
                         glass=[C("#c8e8f0"), C("#8ac8e8"), C("#3a6a8a")], top_light=C("#fff4d0"),
                         top_light_amt=0.08, shade=C("#2a3a5a")),
    "ironworks": dict(night=False, grade_f=(1.03, 0.83, 0.74), grade_g=(1.0, 0.88, 0.80), bloom=0.7,
                      glass=[C("#f0a060"), C("#a05040"), C("#4a2a3a")], top_light=C("#ff8a40"),
                      top_light_amt=0.2, shade=C("#3a1a2a")),
    "neon_mile": dict(night=True, grade_f=(0.44, 0.42, 0.68), grade_g=(0.56, 0.53, 0.76), bloom=1.0,
                      glass=[C("#3a3a6a"), C("#24244a"), C("#14142a")], top_light=C("#6a5aa0"),
                      top_light_amt=0.0, shade=C("#0c0a1a")),
    "floodgate": dict(night=True, grade_f=(0.46, 0.52, 0.62), grade_g=(0.60, 0.65, 0.73), bloom=0.9,
                      glass=[C("#5a6478"), C("#2a3040"), C("#1a1e2a")], top_light=C("#8090a8"),
                      top_light_amt=0.0, shade=C("#0e1018")),
    "warehouse": dict(night=True, grade_f=(0.62, 0.62, 0.68), grade_g=(0.74, 0.74, 0.78), bloom=0.8,
                      glass=[C("#4a5060"), C("#2a2e3a"), C("#1a1c24")], top_light=C("#9098a8"),
                      top_light_amt=0.0, shade=C("#101016")),
}
INTERIOR_THEMES = {
    "diner_interior": dict(grade=(1.02, 0.99, 0.95), bloom=0.28),
    "garage_interior": dict(grade=(1.0, 0.97, 0.92), bloom=0.22),
    "gym_interior": dict(grade=(1.0, 0.98, 0.94), bloom=0.22),
    "noodle_interior": dict(grade=(1.03, 0.97, 0.9), bloom=0.33),
    "bookshop_interior": dict(grade=(1.0, 0.95, 0.86), bloom=0.28),
    "canteen_interior": dict(grade=(1.0, 0.96, 0.9), bloom=0.22),
    "switch_interior": dict(grade=(0.98, 0.88, 0.82), bloom=0.33),
    "arcade_interior": dict(grade=(0.62, 0.58, 0.82), bloom=0.7),
    "pharmacy_interior": dict(grade=(0.98, 1.0, 1.0), bloom=0.22),
    "bait_interior": dict(grade=(0.95, 0.9, 0.82), bloom=0.33),
}


class Room:
    def __init__(self, rid, data):
        self.id = rid
        self.d = data
        self.w = data["width"]
        self.interior = data["kind"] == "interior"
        self.district = data["district"]
        self.theme_name = data.get("theme", self.district)
        self.T = THEMES[self.district]
        self.cv = Canvas(self.w, H)
        self.lights = []      # (x, y, color, radius, strength)  -> light pools / halos
        self.refl = []        # (x0, x1, y_src, color, strength) -> wet-ground reflections
        self.doors_drawn = []
        self.night = self.T["night"]

    def rng(self, *k):
        return rng_of(self.id, *k)

    def doors_in(self, x0, x1):
        return [d for d in self.d.get("doors", []) if x0 <= d["x"] < x1]


# ----------------------------------------------------------------------------
# building components
# ----------------------------------------------------------------------------
LIT = [C("#fff0b8"), C("#ffd27a"), C("#f0a050")]
LIT_COOL = [C("#e8f8ff"), C("#a8d8f0"), C("#6aa0c8")]
LIT_TV = [C("#c8e0ff"), C("#7aa0e0"), C("#4a5aa0")]


def glass_unlit(cv, R, x, y, w, h):
    g = R.T["glass"] if R else THEMES["old_quarter"]["glass"]
    cv.vgrad(x, y, w, h, g, levels=max(3, h // 2))
    # diagonal sheen
    for i in range(0, w + h, 9):
        for k in range(2):
            xx = x + i - k
            for yy in range(y, y + h):
                xxx = xx - (yy - y)
                if x <= xxx < x + w and (i // 9) % 2 == 0:
                    cv.px(xxx, yy, mix(cv_get(cv, xxx, yy), g[0], 0.35))


def cv_get(cv, x, y):
    x = max(0, min(cv.w - 1, int(x)))
    y = max(0, min(cv.h - 1, int(y)))
    return tuple(int(v) for v in cv.a[y, x, :3])


def glass_lit(cv, x, y, w, h, pal=None, rng=None, deco=True):
    pal = pal or LIT
    cv.vgrad(x, y, w, h, pal, em=1, levels=max(3, h // 2))
    if deco and rng is not None and w >= 6 and h >= 8:
        r = rng.random()
        sil = dk(pal[2], 0.45)
        if r < 0.3:      # curtains
            cc = rng.choice([P["red"], P["mustard"], P["teal"], P["purple"], P["cream"]])
            cc = mix(cc, pal[1], 0.35)
            cv.rect(x, y, max(2, w // 4), h, cc, em=1)
            cv.rect(x + w - max(2, w // 4), y, max(2, w // 4), h, cc, em=1)
            cv.hl(x, y, w, dk(cc, 0.2), em=1)
        elif r < 0.45:   # plant on sill
            cv.rect(x + w // 2 - 2, y + h - 3, 4, 3, mix(P["brown"], pal[2], 0.3), em=1)
            cv.ellipse(x + w // 2 - 3, y + h - 8, x + w // 2 + 2, y + h - 3, mix(P["green_d"], pal[2], 0.25), em=1)
        elif r < 0.55:   # silhouette
            cx = x + rng.randrange(2, max(3, w - 4))
            cv.ellipse(cx - 2, y + h - 11, cx + 2, y + h - 7, sil, em=1)
            cv.rect(cx - 3, y + h - 6, 7, 6, sil, em=1)
        elif r < 0.7:    # blind half drawn
            bl = mix(pal[1], P["cream"], 0.4)
            hh = rng.randrange(2, max(3, h // 2))
            cv.rect(x, y, w, hh, bl, em=1)
            for yy in range(y + 1, y + hh, 2):
                cv.hl(x, yy, w, dk(bl, 0.12), em=1)


def window(cv, R, x, y, w, h, lit=False, frame=None, sill=None, lintel=None, bars=True, rng=None,
           pal=None, arch=False, shutters=None, deco=True):
    """Generic sash window.  x,y = outer top-left (frame included)."""
    frame = frame or P["white_d"]
    fr_d = dk(frame, 0.3)
    if lintel:
        cv.rect(x - 2, y - 3, w + 4, 3, lintel)
        cv.hl(x - 2, y - 3, w + 4, lt(lintel, 0.2))
    if arch:
        cv.ellipse(x, y - w // 2, x + w - 1, y + w // 2, frame)
    cv.rect(x, y, w, h, frame)
    gx, gy, gw, gh = x + 1, y + 1, w - 2, h - 2
    if lit:
        glass_lit(cv, gx, gy, gw, gh, pal, rng, deco)
        if arch:
            cv.ellipse(gx, y - w // 2 + 1, gx + gw - 1, y + w // 2 - 1, (pal or LIT)[0], em=1)
    else:
        glass_unlit(cv, R, gx, gy, gw, gh)
        if arch:
            cv.ellipse(gx, y - w // 2 + 1, gx + gw - 1, y + w // 2 - 1, (R.T["glass"] if R else LIT)[0])
    em = 1 if lit else 0
    if bars:
        mid = gy + gh // 2
        cv.hl(gx, mid, gw, frame, em=0)
        if gw >= 10:
            cv.vl(gx + gw // 2, gy, gh, frame, em=0)
    # inner shadow under top frame
    cv.hl(gx, gy, gw, dk(cv_get(cv, gx, gy), 0.35), em=em)
    cv.vl(x + w - 1, y, h, fr_d)
    if sill is not False:
        sc = sill or lt(frame, 0.1)
        cv.rect(x - 1, y + h, w + 2, 2, sc)
        cv.hl(x - 1, y + h + 1, w + 2, dk(sc, 0.35))
    if shutters:
        sw = max(3, w // 3)
        for sx in (x - sw - 1, x + w + 1):
            cv.rect(sx, y, sw, h, shutters)
            for yy in range(y + 1, y + h - 1, 2):
                cv.hl(sx + 1, yy, sw - 2, dk(shutters, 0.25))
            cv.vl(sx + sw - 1, y, h, dk(shutters, 0.35))


def deco_door(cv, x, yb, w, h, color, frame=None, glass=True, step=True, R=None):
    """Decorative (non-interactive) door: darker, closed."""
    frame = frame or P["white_d"]
    y = yb - h
    cv.rect(x - 2, y - 2, w + 4, h + 2, frame)
    cv.rect(x, y, w, h, color)
    cv.vl(x + w - 1, y, h, dk(color, 0.35))
    cv.hl(x, y, w, dk(color, 0.4))
    # panels
    pw = (w - 6) // 2
    for px_ in (x + 2, x + 4 + pw):
        cv.rect(px_, y + h // 2 + 2, pw, h // 2 - 5, dk(color, 0.18))
        if not glass:
            cv.rect(px_, y + 4, pw, h // 2 - 5, dk(color, 0.18))
    if glass:
        cv.rect(x + 2, y + 3, w - 4, h // 2 - 4, dk(color, 0.5))
        cv.hl(x + 2, y + 3, w - 4, dk(color, 0.65))
    cv.px(x + w - 4, y + h // 2, P["mustard"])
    if step:
        cv.rect(x - 4, yb, w + 8, 1, lt(frame, 0.1))


def awning(cv, x, y, w, h, c1, c2=None, stripe=6, scallop=True, shade=True):
    """Front-view sloped awning; y = top attach line, h = total drop."""
    c2 = c2 or lt(c1, 0.75)
    top_h = max(3, h - 5)
    for i in range(top_h):
        t = i / max(1, top_h - 1)
        yy = y + i
        inset = int((1 - t) * 2)
        for xx in range(x + inset, x + w - inset):
            k = ((xx - x) // stripe) % 2
            base = c1 if k == 0 else c2
            col = mix(dk(base, 0.25), base, t)
            cv.px(xx, yy, col)
    vy = y + top_h
    for xx in range(x, x + w):
        k = ((xx - x) // stripe) % 2
        base = c1 if k == 0 else c2
        cv.vl(xx, vy, 3, dk(base, 0.08))
        if scallop:
            ph = (xx - x) % stripe
            if 1 <= ph <= stripe - 2:
                cv.px(xx, vy + 3, dk(base, 0.15))
            if 2 <= ph <= stripe - 3:
                cv.px(xx, vy + 4, dk(base, 0.25))
    cv.hl(x, vy, w, lt(c2, 0.3))
    if shade:
        cv.dither_blend(x, vy + 4, w, 6, (0, 0, 0), 0.25)
        cv.dither_blend(x, vy + 3, w, 3, (0, 0, 0), 0.5)


def fit_scale(s, maxw, prefer=2):
    for sc, b in ((prefer, False), (2, False), (1, True), (1, False)):
        if text_w(s, sc, b) <= maxw:
            return sc, b
    return 1, False


def signboard(cv, x, y, w, h, s, bg, fg, border=None, shadow=True, scale=None, em_text=0, bevel=True,
              bold=None):
    border = border or dk(bg, 0.5)
    cv.rect(x, y, w, h, border)
    cv.rect(x + 1, y + 1, w - 2, h - 2, bg)
    if bevel:
        cv.hl(x + 1, y + 1, w - 2, lt(bg, 0.25))
        cv.hl(x + 1, y + h - 2, w - 2, dk(bg, 0.25))
    if s:
        if scale is None:
            sc, b = fit_scale(s, w - 6, 2 if h >= 18 else 1)
        else:
            sc, b = scale, bool(bold)
        if bold is not None:
            b = bold
        tw = text_w(s, sc, b)
        tx = x + (w - tw) // 2
        ty = y + (h - 7 * sc) // 2
        cv.text(tx, ty, s, fg, sc, bold=b, shadow=dk(bg, 0.55) if shadow else None, em=em_text)


def neon_mask(s, gap=2):
    """1px tube-style letters on a 2x grid (looks like bent neon)."""
    glyphs = [GLYPH.get(ch, GLYPH[" "]) for ch in s.upper()]
    W = sum((len(g[0]) - 1) * gap + 1 + gap * 2 for g in glyphs) - gap * 2
    m = np.zeros((6 * gap + 1, max(1, W)), bool)
    ox = 0
    for g in glyphs:
        gw = len(g[0])
        for yy in range(7):
            for xx in range(gw):
                if not g[yy][xx]:
                    continue
                px_, py_ = ox + xx * gap, yy * gap
                m[py_, px_] = True
                for dx, dy in ((1, 0), (0, 1), (1, 1), (-1, 1)):
                    nx, ny = xx + dx, yy + dy
                    if 0 <= nx < gw and ny < 7 and g[ny][nx]:
                        if dx and dy and (g[yy][nx] or g[ny][xx]):
                            continue
                        for k in range(1, gap):
                            m[py_ + dy * k, px_ + dx * k] = True
                        m[py_ + dy * gap, px_ + dx * gap] = True
        ox += (gw - 1) * gap + 1 + gap * 2
    return m


def dilate(m, r=1):
    o = m.copy()
    for _ in range(r):
        n = o.copy()
        n[1:, :] |= o[:-1, :]
        n[:-1, :] |= o[1:, :]
        n[:, 1:] |= o[:, :-1]
        n[:, :-1] |= o[:, 1:]
        o = n
    return o


def neon_text(cv, R, cx, y, s, color, gap=2, backing=None, flicker=None):
    m = neon_mask(s, gap)
    h, w = m.shape
    x = int(cx - w / 2)
    big = np.zeros((h + 4, w + 4), bool)
    big[2:2 + h, 2:2 + w] = m
    halo = dilate(big, 1)
    if backing is not None:
        cv.rect(x - 5, y - 5, w + 10, h + 10, backing)
    cv.mask_fill(x - 2, y - 2, halo & ~big, mix(color, (0, 0, 0), 0.35), em=1)
    cv.mask_fill(x - 2, y - 2, big, lt(color, 0.55), em=1)
    if R is not None:
        R.lights.append((x + w // 2, y + h // 2, color, max(w // 2, 20), 0.7))
        R.refl.append((x, x + w, y + h, color, 0.8))
    return x, w, h


def bulbs(cv, x, y, w, h, on=None, off=None, step=4, phase=0):
    """Chaser bulbs around a rectangle outline."""
    on = on or P["n_yellow"]
    off = off or C("#a07a3a")
    pts = []
    for xx in range(x, x + w, step):
        pts.append((xx, y))
    for yy in range(y + step, y + h, step):
        pts.append((x + w - 1, yy))
    for xx in range(x + w - 1 - step, x - 1, -step):
        pts.append((xx, y + h - 1))
    for yy in range(y + h - 1 - step, y, -step):
        pts.append((x, yy))
    for i, (px_, py_) in enumerate(pts):
        if (i + phase) % 3:
            cv.rect(px_, py_, 2, 2, on, em=1)
            cv.px(px_, py_, (255, 255, 230), em=1)
        else:
            cv.rect(px_, py_, 2, 2, off)


def drainpipe(cv, x, y0, y1, c=None):
    c = c or P["gray_d"]
    cv.rect(x, y0, 3, y1 - y0, c)
    cv.vl(x, y0, y1 - y0, lt(c, 0.25))
    cv.vl(x + 2, y0, y1 - y0, dk(c, 0.3))
    for yy in range(y0 + 10, y1, 28):
        cv.rect(x - 1, yy, 5, 2, dk(c, 0.2))
    cv.rect(x - 1, y1 - 4, 6, 4, c)


def fire_escape(cv, x, w, floors, c=None, ladder=True, bottom=None):
    """floors = list of platform y.  Zigzag stairs between them."""
    c = c or C("#2e2a34")
    hi = lt(c, 0.25)
    floors = sorted(floors)
    for i, fy in enumerate(floors):
        # platform grate
        cv.rect(x, fy, w, 2, c)
        cv.hl(x, fy, w, hi)
        # railing
        cv.hl(x, fy - 9, w, c)
        cv.hl(x, fy - 5, w, dk(c, 0.1))
        for xx in range(x, x + w, 3):
            cv.vl(xx, fy - 9, 9, c)
        cv.vl(x + w - 1, fy - 9, 11, c)
        cv.vl(x, fy - 9, 11, c)
        # brackets
        cv.line(x + 2, fy + 2, x + 6, fy + 7, c)
        cv.line(x + w - 3, fy + 2, x + w - 7, fy + 7, c)
        if i + 1 < len(floors):
            ny = floors[i + 1]
            if i % 2 == 0:
                sx0, sx1 = x + 4, x + w - 8
            else:
                sx0, sx1 = x + w - 8, x + 4
            cv.line(sx0, fy + 1, sx1, ny - 1, c)
            cv.line(sx0, fy - 6, sx1, ny - 8, c)
            n = 7
            for k in range(1, n):
                t = k / n
                cv.hl(int(sx0 + (sx1 - sx0) * t) - 1, int(fy + (ny - fy) * t), 3, hi)
    if ladder and floors:
        lb = bottom or floors[-1] + 34
        lx = x + w - 10
        cv.vl(lx, floors[-1], lb - floors[-1], c)
        cv.vl(lx + 5, floors[-1], lb - floors[-1], c)
        for yy in range(floors[-1] + 3, lb, 4):
            cv.hl(lx, yy, 6, c)


def chainlink(cv, x, y, w, h, wire=None, post=None, pitch=5, posts=48, top_rail=True, sag=0):
    wire = wire or C("#8a9098")
    post = post or dk(wire, 0.35)
    x0, y0, x1, y1 = cv._clip(x, y, x + w, y + h)
    if x1 > x0 and y1 > y0:
        yy, xx = np.mgrid[y0:y1, x0:x1]
        m = ((xx + yy) % pitch == 0) | ((xx - yy) % pitch == 0)
        reg = cv.a[y0:y1, x0:x1]
        light = ((xx + yy) % pitch == 0)
        reg[m & light, :3] = wire
        reg[m & ~light, :3] = dk(wire, 0.2)
        reg[m, 3] = 255
        cv.em[y0:y1, x0:x1][m] = 0
    if top_rail:
        cv.rect(x, y - 1, w, 2, post)
        cv.hl(x, y - 1, w, lt(post, 0.3))
    for px_ in range(x, x + w + 1, posts):
        cv.rect(px_, y - 3, 3, h + 3, post)
        cv.vl(px_, y - 3, h + 3, lt(post, 0.3))
        cv.rect(px_ - 1, y - 4, 5, 2, dk(post, 0.2))


def barbed(cv, x, y, w, c=None):
    c = c or C("#5a5a66")
    for xx in range(x, x + w):
        yy = y + int(2 * math.sin(xx * 0.9))
        cv.px(xx, yy, c)
        if xx % 6 == 0:
            cv.px(xx, yy - 1, c)
            cv.px(xx + 1, yy + 1, c)
    for xx in range(x, x + w):
        cv.px(xx, y + 4, c)


def wall_lamp(cv, R, x, y, color=None, em_strength=0.8):
    color = color or P["lamp"]
    cv.rect(x - 1, y - 4, 2, 4, P["char"])
    cv.rect(x - 3, y, 7, 3, P["char_d"])
    cv.rect(x - 2, y + 3, 5, 3, color, em=1)
    cv.hl(x - 2, y + 3, 5, (255, 250, 220), em=1)
    if R is not None:
        R.lights.append((x, y + 6, color, 26, em_strength))
        R.refl.append((x - 3, x + 3, y + 6, color, 0.5))


def stoop(cv, x, w, steps=3, c=None, rail=True):
    c = c or C("#a8a090")
    for i in range(steps):
        sy = FACADE_BOTTOM - (i + 1) * 3
        inset = i * 2
        cv.rect(x + inset, sy, w - 2 * inset, 3, mix(c, dk(c, 0.3), i / max(1, steps)))
        cv.hl(x + inset, sy, w - 2 * inset, lt(c, 0.2))
    if rail:
        rc = C("#2a2630")
        for rx in (x + 1, x + w - 2):
            cv.vl(rx, FACADE_BOTTOM - steps * 3 - 10, steps * 3 + 10, rc)
            cv.line(rx, FACADE_BOTTOM - steps * 3 - 10, rx + (3 if rx < x + w // 2 else -3), FACADE_BOTTOM - 8, rc)


def laundry_line(cv, x0, y0, x1, y1, rng):
    cv.sag(x0, y0, x1, y1, 6, C("#e8e4dc"))
    n = max(2, abs(x1 - x0) // 14)
    cols = [P["white"], P["red"], P["blue"], P["mustard"], P["teal"], C("#e890a0"), P["green"]]
    for i in range(1, n):
        t = i / n + rng.uniform(-0.03, 0.03)
        xx = int(x0 + (x1 - x0) * t)
        yy = int(y0 + (y1 - y0) * t + 6 * 4 * t * (1 - t))
        c = rng.choice(cols)
        kind = rng.random()
        if kind < 0.4:   # shirt
            cv.rect(xx - 3, yy + 1, 7, 7, c)
            cv.rect(xx - 5, yy + 1, 2, 3, c)
            cv.rect(xx + 4, yy + 1, 2, 3, c)
            cv.vl(xx + 3, yy + 1, 7, dk(c, 0.25))
        elif kind < 0.7:  # towel / sheet
            hh = rng.randrange(6, 11)
            cv.rect(xx - 3, yy + 1, 6, hh, c)
            cv.vl(xx + 2, yy + 1, hh, dk(c, 0.25))
            cv.hl(xx - 3, yy + hh - 1, 6, dk(c, 0.15))
        else:            # trousers
            cv.rect(xx - 3, yy + 1, 6, 3, c)
            cv.rect(xx - 3, yy + 4, 2, 6, c)
            cv.rect(xx + 1, yy + 4, 2, 6, c)
        cv.px(xx - 2, yy, P["tan_d"])
        cv.px(xx + 2, yy, P["tan_d"])


def ac_box(cv, x, y, w=12, h=8, c=None):
    c = c or C("#b8b4a8")
    cv.rect(x, y, w, h, c)
    cv.hl(x, y, w, lt(c, 0.3))
    cv.vl(x + w - 1, y, h, dk(c, 0.3))
    cv.hl(x, y + h - 1, w, dk(c, 0.35))
    for yy in range(y + 2, y + h - 1, 2):
        cv.hl(x + 2, yy, w - 4, dk(c, 0.25))
    cv.px(x + 1, y + h, dk(c, 0.5))
    cv.px(x + w - 2, y + h, dk(c, 0.5))


def notice(cv, x, y, w=7, h=9, header=None):
    paper = C("#ece6d4")
    cv.rect(x, y, w, h, paper)
    cv.hl(x, y + 1, w, header or P["red"])
    for yy in range(y + 3, y + h - 1, 2):
        cv.hl(x + 1, yy, w - 2 - (yy % 3), C("#8a8478"))
    cv.px(x + w - 1, y + h - 1, dk(paper, 0.3))
    cv.px(x + w // 2, y, C("#5a5a66"))


def poster(cv, x, y, w, h, rng, palette=None):
    palette = palette or [P["red"], P["mustard"], P["teal"], P["purple"], P["blue"], P["orange"], P["cream"]]
    bg = rng.choice(palette)
    fg = rng.choice([c for c in palette if c != bg])
    cv.rect(x, y, w, h, bg)
    cv.rect(x + 1, y + 1, w - 2, max(2, h // 3), fg)
    cv.ellipse(x + w // 4, y + h // 3, x + 3 * w // 4, y + 2 * h // 3 + 1, lt(fg, 0.3))
    for yy in range(y + 2 * h // 3 + 2, y + h - 1, 2):
        cv.hl(x + 1, yy, w - 2, dk(bg, 0.35))
    if rng.random() < 0.5:
        cv.px(x + w - 1, y, dk(bg, 0.6))
        cv.px(x + w - 2, y, dk(bg, 0.6))
        cv.px(x + w - 1, y + 1, dk(bg, 0.6))


def graffiti(cv, x, y, w, h, rng, cols=None):
    """Abstract bubble-style graffiti piece (original, no lettering)."""
    cols = cols or rng.sample([P["n_pink"], P["n_cyan"], P["mustard"], P["n_green"], P["orange"], P["purple"],
                               C("#e05a5a"), C("#5a8ae0")], 3)
    m = np.zeros((h, w), bool)
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    n = max(2, w // 14)
    xx = 2
    for i in range(n):
        bw = rng.randrange(10, 18)
        bh = rng.randrange(int(h * 0.55), h - 2)
        by = rng.randrange(1, max(2, h - bh))
        shape = rng.random()
        if shape < 0.5:
            d.rounded_rectangle([xx, by, xx + bw, by + bh], radius=rng.randrange(3, 6), fill=255)
        else:
            d.ellipse([xx, by, xx + bw, by + bh], fill=255)
        if rng.random() < 0.6:
            d.polygon([(xx + bw // 2, by - 3), (xx + bw, by + 4), (xx + 2, by + 3)], fill=255)
        xx += bw - rng.randrange(2, 5)
        if xx > w - 12:
            break
    m = np.array(im) > 127
    o1 = dilate(m, 1)
    o2 = dilate(o1, 1)
    cv.mask_fill(x, y, o2 & ~o1, P["white"])
    cv.mask_fill(x, y, o1 & ~m, INK)
    # fill with vertical two-tone
    top = np.zeros_like(m)
    top[: h // 2] = True
    cv.mask_fill(x, y, m & top, cols[0])
    cv.mask_fill(x, y, m & ~top, cols[1])
    # highlight dashes + inner stripe
    hl = m & ~dilate(~m, 2)
    stripe = np.zeros_like(m)
    stripe[h // 2 - 1:h // 2 + 1] = True
    cv.mask_fill(x, y, hl & stripe, cols[2])
    for _ in range(4):
        sx = rng.randrange(0, w)
        sy = rng.randrange(0, h)
        if 0 <= sy < h and m[sy, sx]:
            cv.px(x + sx, y + sy, P["white"])
            cv.px(x + sx + 1, y + sy, P["white"])
    # drips
    for _ in range(rng.randrange(2, 5)):
        sx = rng.randrange(4, w - 4)
        col = np.nonzero(m[:, sx])[0]
        if len(col):
            cv.vl(x + sx, y + col[-1] + 1, rng.randrange(2, 7), cols[1])
    # sparkle star
    sx, sy = x + w - rng.randrange(2, 8), y + rng.randrange(0, 5)
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        cv.px(sx + dx, sy + dy, P["white"])


def tag_scribble(cv, x, y, rng, c=None):
    """Small abstract tag: loopy squiggle."""
    c = c or rng.choice([P["n_pink"], P["n_cyan"], P["white"], P["mustard"], C("#e05a5a")])
    px_, py_ = x, y
    for i in range(rng.randrange(10, 20)):
        nx = px_ + rng.randrange(1, 4)
        ny = y + int(3 * math.sin(i * rng.uniform(0.8, 1.6)))
        cv.line(px_, py_, nx, ny, c)
        px_, py_ = nx, ny
    cv.line(x, y + 4, px_, y + 5, c)


def cornice(cv, x, w, y, c, h=5):
    cv.rect(x - 2, y, w + 4, h, c)
    cv.hl(x - 2, y, w + 4, lt(c, 0.3))
    cv.hl(x - 2, y + h - 1, w + 4, dk(c, 0.4))
    for xx in range(x, x + w, 4):
        cv.px(xx, y + h, dk(c, 0.35))
        cv.px(xx, y + h + 1, dk(c, 0.5))


def roof_clear(cv, x, w, ytop):
    """Clear (sky) everything above ytop in [x, x+w)."""
    if ytop > 0:
        cv.clear(x, 0, w, ytop)


def base_plinth(cv, x, w, c=None, h=4):
    c = c or C("#6a625a")
    cv.rect(x, FACADE_BOTTOM - h, w, h, c)
    cv.hl(x, FACADE_BOTTOM - h, w, lt(c, 0.2))


# ----------------------------------------------------------------------------
# entrance doors (interactive doors from rooms.json)
# ----------------------------------------------------------------------------
DOOR_W, DOOR_H = 28, 48


def entrance(R, d, style="shop", accent=None):
    cv = R.cv
    x = int(d["x"])
    yb = FACADE_BOTTOM
    accent = accent or P["red"]
    W, Hh = DOOR_W, DOOR_H
    x0 = x - W // 2
    y0 = yb - Hh
    R.doors_drawn.append((d["id"], x))
    if style == "tunnel":
        aw, ah = 44, 62
        ax0 = x - aw // 2
        stone = C("#8a8274")
        # voussoir ring
        cv.ellipse(ax0 - 6, yb - ah - 6, ax0 + aw + 5, yb - ah + aw + 6, dk(stone, 0.1))
        cv.rect(ax0 - 6, yb - ah + aw // 2, aw + 12, ah - aw // 2, dk(stone, 0.1))
        for i in range(13):
            a = math.pi * (i / 12)
            px_ = x + int(math.cos(a) * (aw // 2 + 3))
            py_ = yb - ah + aw // 2 - int(math.sin(a) * (aw // 2 + 3))
            cv.rect(px_ - 1, py_ - 1, 3, 3, lt(stone, 0.15))
        cv.ellipse(ax0, yb - ah, ax0 + aw - 1, yb - ah + aw, C("#0c0a10"))
        cv.rect(ax0, yb - ah + aw // 2, aw, ah - aw // 2, C("#0c0a10"))
        # depth: faint far light + rails converging inside
        cv.ellipse(x - 5, yb - 22, x + 5, yb - 12, C("#2a2430"))
        cv.ellipse(x - 2, yb - 19, x + 2, yb - 15, C("#4a3a40"))
        for s in (-1, 1):
            cv.line(x + s * 3, yb - 14, x + s * 14, yb - 1, C("#6a6470"))
        cv.rect(x - 1, yb - ah - 10, 3, 4, C("#2a2630"))
        cv.rect(x - 4, yb - ah - 6, 9, 3, C("#2a2630"))
        cv.rect(x - 3, yb - ah - 3, 7, 3, P["lamp"], em=1)
        R.lights.append((x, yb - ah, P["lamp"], 22, 0.6))
        return
    if style == "alley":
        aw = 40
        ax0 = x - aw // 2
        cv.vgrad(ax0, yb - 70, aw, 70, [C("#1a1626"), C("#2a2236"), C("#3a2a3a")])
        # far wall + light at the end of the alley
        cv.rect(ax0 + 8, yb - 50, aw - 16, 50, C("#2a2230"))
        cv.rect(ax0 + 14, yb - 30, 12, 30, C("#ffcf7a"), em=1)
        cv.rect(ax0 + 15, yb - 29, 10, 3, C("#fff0c0"), em=1)
        cv.vl(ax0, yb - 70, 70, C("#120e18"))
        cv.vl(ax0 + aw - 1, yb - 70, 70, C("#120e18"))
        R.lights.append((x, yb - 15, C("#ffcf7a"), 24, 0.6))
        return
    # ---- regular doors -----------------------------------------------------
    frames = {
        "shop": (P["wood_d"], C("#3a2418")), "diner": (P["steel_l"], P["steel"]),
        "garage": (P["steel"], P["char"]), "civic": (C("#c8bca8"), C("#8a8070")),
        "neon": (C("#30304a"), C("#1a1a2a")), "shack": (P["wood"], P["wood_d"]),
        "industrial": (C("#5a6068"), C("#34383e")),
    }
    fc, fd = frames.get(style, frames["shop"])
    wide = style == "civic"
    if wide:
        W = 36
        x0 = x - W // 2
    # frame
    cv.rect(x0 - 3, y0 - 3, W + 6, Hh + 3, fc)
    cv.hl(x0 - 3, y0 - 3, W + 6, lt(fc, 0.3))
    cv.vl(x0 + W + 2, y0 - 3, Hh + 3, fd)
    # lit interior
    lit = LIT_COOL if style == "neon" and accent in (P["n_cyan"], P["green"], P["teal"]) else LIT
    cv.vgrad(x0, y0, W, Hh, [lit[0], lit[1], lit[2]], em=1)
    # interior hint: floor + a counter edge
    cv.rect(x0, yb - 8, W, 8, mix(lit[2], P["brown_d"], 0.45), em=1)
    cv.hl(x0, yb - 8, W, mix(lit[1], P["brown"], 0.3), em=1)
    if style in ("diner", "shop", "neon"):
        cv.rect(x0 + 3, yb - 20, W - 6, 4, mix(lit[2], accent, 0.5), em=1)
    # door leaf (propped open) on the left: dark slab seen edge-on
    leaf = dk(fc, 0.35) if style != "civic" else C("#6a4a2e")
    if wide:
        cv.rect(x0, y0, 5, Hh, leaf)
        cv.rect(x0 + W - 5, y0, 5, Hh, leaf)
        cv.vl(x0 + 4, y0, Hh, dk(leaf, 0.4))
        cv.vl(x0 + W - 5, y0, Hh, dk(leaf, 0.4))
    else:
        cv.rect(x0, y0, 6, Hh, leaf)
        cv.vl(x0 + 5, y0, Hh, dk(leaf, 0.4))
        cv.rect(x0 + 2, y0 + 6, 2, Hh - 14, mix(lit[1], leaf, 0.5), em=1)
        cv.px(x0 + 4, y0 + Hh // 2, P["mustard"])
    # transom
    cv.rect(x0 - 3, y0 - 9, W + 6, 6, fc)
    cv.rect(x0 - 1, y0 - 8, W + 2, 4, lit[0], em=1)
    for xx in range(x0 + 3, x0 + W, 6):
        cv.vl(xx, y0 - 8, 4, fc)
    # threshold step on the ground
    cv.rect(x0 - 5, yb, W + 10, 2, C("#b8b0a0"))
    cv.hl(x0 - 5, yb + 2, W + 10, C("#5a5650"))
    # small awning / lamp per style
    if style in ("shop", "diner", "civic", "neon"):
        aw_c = accent
        awning(cv, x0 - 7, y0 - 18, W + 14, 9, aw_c, lt(aw_c, 0.75) if style != "neon" else dk(aw_c, 0.4),
               stripe=5, shade=False)
    if style in ("garage", "industrial", "shack", "civic"):
        lx = x0 + W + 7 if not wide else x0 - 8
        wall_lamp(cv, R, lx, y0 - 2)
        if wide:
            wall_lamp(cv, R, x0 + W + 7, y0 - 2)
    if style == "industrial":
        # porthole hint on the frame + hazard step
        for xx in range(x0 - 5, x0 + W + 5, 4):
            cv.rect(xx, yb, 2, 2, P["yellow"])
    if style == "neon":
        for xx in range(x0 - 3, x0 + W + 3, 1):
            cv.px(xx, y0 - 10, lt(accent, 0.4), em=1)
        cv.vl(x0 - 4, y0 - 10, Hh + 10, lt(accent, 0.3), em=1)
        cv.vl(x0 + W + 3, y0 - 10, Hh + 10, lt(accent, 0.3), em=1)
        R.refl.append((x0 - 4, x0 + W + 4, y0, accent, 0.5))
    R.lights.append((x, yb - 10, lit[1], 30, 0.75))
    R.refl.append((x0, x0 + W, yb - 20, lit[1], 0.45))


# ----------------------------------------------------------------------------
# ground styles
# ----------------------------------------------------------------------------
GROUNDS = {}


def ground(name):
    def deco(f):
        GROUNDS[name] = f
        return f
    return deco


def persp_rows(y0, y1, h0, h1):
    rows = []
    y = y0
    while y < y1:
        t = (y - y0) / max(1, y1 - y0)
        h = int(round(h0 + (h1 - h0) * t))
        rows.append((y, min(h, y1 - y)))
        y += h
    return rows


def fg_curb(cv, x, w, top=None, face=None, hi=None):
    top = top or C("#6a6660")
    face = face or C("#34303a")
    hi = hi or lt(top, 0.25)
    cv.hl(x, CURB_Y, w, hi)
    cv.rect(x, CURB_Y + 1, w, 4, top)
    cv.hl(x, CURB_Y + 5, w, dk(top, 0.3))
    cv.vgrad(x, CURB_Y + 6, w, H - CURB_Y - 6, [face, dk(face, 0.4)], levels=4)
    for xx in range(x + 31, x + w, 64):
        cv.vl(xx, CURB_Y + 1, 5, dk(top, 0.35))


def sidewalk(cv, x, w, y0, y1, base=None, slab=32, seed=0):
    base = base or P["sidewalk"]
    cv.rect(x, y0, w, y1 - y0, base)
    rng = rng_of("sw", seed, x)
    cv.noise_tint(x, y0, w, y1 - y0, rng, amount=4, density=0.12)
    jc = mix(base, P["curb"], 0.7)
    for xx in range((x // slab + 1) * slab, x + w, slab):
        cv.vl(xx, y0, y1 - y0, jc)
        cv.vl(xx + 1, y0, y1 - y0, lt(base, 0.1))
    mid = y0 + (y1 - y0) // 2
    cv.hl(x, mid, w, jc)
    # shadow at base of buildings
    cv.dither_blend(x, y0, w, 3, dk(base, 0.4), 0.6)
    cv.dither_blend(x, y0 + 3, w, 3, dk(base, 0.4), 0.25)


def curb(cv, x, w, y, top=None):
    top = top or P["sidewalk_l"]
    cv.hl(x, y, w, lt(top, 0.15))
    cv.rect(x, y + 1, w, 2, top)
    cv.rect(x, y + 3, w, 3, P["curb"])
    cv.hl(x, y + 6, w, dk(P["asphalt"], 0.35))


def asphalt(cv, x, w, y0, y1, base=None, seed=0, lane=True, cracks=True, lane_col=None):
    base = base or P["asphalt"]
    cv.rect(x, y0, w, y1 - y0, base)
    rng = rng_of("asph", seed, x)
    cv.noise_tint(x, y0, w, y1 - y0, rng, amount=5, density=0.10)
    # big patches (repairs), very low contrast
    for _ in range(max(1, w // 260)):
        px_ = rng.randrange(x, x + max(1, w - 60))
        py_ = rng.randrange(y0 + 6, y1 - 20)
        cv.dither_blend(px_, py_, rng.randrange(30, 70), rng.randrange(8, 16), lt(base, 0.06), 0.5)
    if cracks:
        for _ in range(max(1, w // 200)):
            cx_ = rng.randrange(x, x + w)
            cy_ = rng.randrange(y0 + 4, y1 - 4)
            for k in range(rng.randrange(6, 16)):
                cv.px(cx_, cy_, dk(base, 0.3))
                cx_ += rng.choice((1, 1, 2))
                cy_ += rng.choice((-1, 0, 0, 1))
    if lane:
        ly = (y0 + y1) // 2 + 2
        lc = lane_col or mix(base, C("#d8c890"), 0.45)
        for xx in range((x // 56) * 56, x + w, 56):
            cv.rect(xx, ly, 28, 2, lc)
            cv.dither_blend(xx, ly, 28, 2, base, 0.35)   # faded
    return


@ground("street")
def g_street(R, x, w):
    cv = R.cv
    sidewalk(cv, x, w, 214, 244, seed=R.id)
    curb(cv, x, w, 244)
    asphalt(cv, x, w, 251, CURB_Y, seed=R.id)
    # storm drains
    rng = R.rng("drain", x)
    for xx in range(x + 90, x + w - 20, 380):
        cv.rect(xx, 247, 14, 4, C("#24222a"))
        for k in range(xx + 1, xx + 14, 2):
            cv.vl(k, 247, 4, C("#4a4650"))
    fg_curb(cv, x, w)


@ground("lot")
def g_lot(R, x, w):
    cv = R.cv
    base = C("#7a7266")
    cv.rect(x, 214, w, CURB_Y - 214, base)
    rng = R.rng("lot", x)
    cv.noise_tint(x, 214, w, CURB_Y - 214, rng, amount=4, density=0.12)
    # slab seams (broken concrete)
    for (yy, hh) in persp_rows(214, CURB_Y, 22, 34):
        cv.hl(x, yy, w, dk(base, 0.18))
        off = rng.randrange(0, 50)
        for xx in range(x + off, x + w, rng.randrange(60, 90)):
            cv.vl(xx, yy, hh, dk(base, 0.18))
    # dirt + gravel patches
    for _ in range(w // 160):
        px_ = rng.randrange(x, x + w - 50)
        py_ = rng.randrange(224, CURB_Y - 14)
        cv.ellipse(px_, py_, px_ + rng.randrange(24, 50), py_ + rng.randrange(6, 12), mix(base, C("#6a5a48"), 0.5))
    # oil stains
    for _ in range(w // 220):
        px_ = rng.randrange(x, x + w - 30)
        py_ = rng.randrange(240, CURB_Y - 16)
        cv.ellipse(px_, py_, px_ + rng.randrange(14, 30), py_ + rng.randrange(4, 8), dk(base, 0.22))
    # weeds along the back edge
    for xx in range(x, x + w, 3):
        if rng.random() < 0.35:
            hh = rng.randrange(2, 6)
            cv.vl(xx, 216 - hh + 2, hh, rng.choice([P["green_d"], C("#5a7a3a"), C("#7a8a4a")]))
    cv.dither_blend(x, 214, w, 4, dk(base, 0.4), 0.5)
    fg_curb(cv, x, w, top=C("#5a544c"), face=C("#2e2a2a"))


@ground("cobble")
def g_cobble(R, x, w):
    cv = R.cv
    base = C("#9a8e7e")
    mortar = C("#5e564e")
    # flagstone strip along the facades
    cv.rect(x, 214, w, 10, C("#a8a090"))
    for xx in range((x // 24 + 1) * 24, x + w, 24):
        cv.vl(xx, 214, 10, dk(C("#a8a090"), 0.2))
    cv.hl(x, 223, w, mortar)
    cv.dither_blend(x, 214, w, 3, (40, 30, 30), 0.4)
    rng = R.rng("cob", x)
    cv.rect(x, 224, w, CURB_Y - 224, mortar)
    for (yy, hh) in persp_rows(224, CURB_Y, 6, 9):
        sw = int(hh * 1.6)
        xx = x - rng.randrange(0, sw)
        while xx < x + w:
            ww = sw + rng.randrange(-2, 3)
            tone = mix(base, dk(base, 0.18), rng.random())
            if rng.random() < 0.08:
                tone = mix(base, C("#8a7e8a"), 0.5)
            cv.rect(xx + 1, yy + 1, ww - 1, hh - 1, tone)
            cv.hl(xx + 2, yy + 1, ww - 3, lt(tone, 0.14))
            cv.px(xx + 1, yy + 1, mortar)
            cv.px(xx + ww - 1, yy + 1, mortar)
            cv.px(xx + 1, yy + hh - 1, mortar)
            cv.px(xx + ww - 1, yy + hh - 1, mortar)
            cv.hl(xx + 2, yy + hh - 1, ww - 3, dk(tone, 0.15))
            xx += ww
    fg_curb(cv, x, w, top=C("#8a8274"), face=C("#3e3834"))


@ground("boardwalk")
def g_boardwalk(R, x, w):
    cv = R.cv
    base = C("#9a7650")
    for (yy, hh) in persp_rows(214, CURB_Y, 6, 9):
        tex_planks_h(cv, x, yy, w, hh, base, ph=hh, seed=f"{R.id}{yy}")
    cv.dither_blend(x, 214, w, 3, (30, 20, 20), 0.4)
    # front beam + pilings
    cv.rect(x, CURB_Y, w, 6, C("#6a4a2e"))
    cv.hl(x, CURB_Y, w, C("#a07a50"))
    cv.vgrad(x, CURB_Y + 6, w, H - CURB_Y - 6, [C("#2a3a4a"), C("#16202a")], levels=4)
    for xx in range(x + 10, x + w, 48):
        cv.rect(xx, CURB_Y + 6, 6, H - CURB_Y - 6, C("#4a3220"))
        cv.vl(xx, CURB_Y + 6, H - CURB_Y - 6, C("#6a4a2e"))


@ground("bridge_planks")
def g_bridge(R, x, w):
    cv = R.cv
    base = C("#a8835a")
    for (yy, hh) in persp_rows(214, H, 6, 9):
        pass
    tex_planks_v(cv, x, 214, w, H - 214, base, pw=7, seed=R.id)
    rng = R.rng("bp", x)
    for xx in range(x, x + w, 7):
        for yy in (258, 286, 310):
            cv.px(xx + 2, yy, dk(base, 0.5))
            cv.px(xx + 4, yy, dk(base, 0.5))
    # stringers visible as shade bands
    cv.dither_blend(x, 252, w, 3, (30, 20, 10), 0.45)


@ground("gravel_rail")
def g_gravel_rail(R, x, w):
    cv = R.cv
    base = C("#7a6e62")
    cv.rect(x, 214, w, CURB_Y - 214, base)
    rng = R.rng("grav", x)
    r = np.random.default_rng(seed_of(R.id, "gravel", x))
    x0, y0, x1, y1 = cv._clip(x, 214, x + w, CURB_Y)
    n = r.random((y1 - y0, x1 - x0))
    reg = cv.a[y0:y1, x0:x1, :3].astype(np.int16)
    reg += np.where(n < 0.12, -14, np.where(n > 0.9, 10, 0)).astype(np.int16)[..., None]
    cv.a[y0:y1, x0:x1, :3] = np.clip(reg, 0, 255).astype(np.uint8)
    cv.dither_blend(x, 214, w, 4, (40, 30, 30), 0.5)

    def track(ty):
        tie = C("#4e3e34")
        for xx in range((x // 12) * 12, x + w, 12):
            cv.rect(xx, ty - 2, 6, 14, tie)
            cv.hl(xx, ty - 2, 6, lt(tie, 0.15))
            cv.vl(xx + 5, ty - 2, 14, dk(tie, 0.3))
        for ry in (ty, ty + 8):
            cv.rect(x, ry, w, 2, P["steel"])
            cv.hl(x, ry, w, P["steel_l"])
            cv.hl(x, ry + 2, w, dk(base, 0.45))
    track(258)
    track(306)
    fg_curb(cv, x, w, top=C("#5a5048"), face=C("#2e2826"))


@ground("foundry_floor")
def g_foundry(R, x, w):
    cv = R.cv
    base = C("#5a5254")
    rng = R.rng("ff", x)
    for (yy, hh) in persp_rows(214, CURB_Y, 22, 32):
        xx = x - rng.randrange(0, 40)
        while xx < x + w:
            ww = rng.randrange(44, 64)
            tone = mix(base, dk(base, 0.2), rng.random() * 0.6)
            cv.rect(xx, yy, ww, hh, tone)
            cv.hl(xx, yy, ww, lt(tone, 0.15))
            cv.vl(xx + ww - 1, yy, hh, dk(tone, 0.35))
            cv.hl(xx, yy + hh - 1, ww, dk(tone, 0.35))
            for (rx, ry) in ((2, 2), (ww - 4, 2), (2, hh - 4), (ww - 4, hh - 4)):
                cv.px(xx + rx, yy + ry, lt(tone, 0.3))
            if rng.random() < 0.25:   # tread plate
                for ty in range(yy + 4, yy + hh - 4, 4):
                    for tx in range(xx + 4 + (ty // 4 % 2) * 2, xx + ww - 4, 5):
                        cv.px(tx, ty, lt(tone, 0.12))
                        cv.px(tx + 1, ty, dk(tone, 0.2))
            xx += ww
    for _ in range(w // 160):
        cv.ellipse(*(lambda a, b: (a, b, a + rng.randrange(16, 36), b + rng.randrange(4, 9)))(
            rng.randrange(x, x + w - 30), rng.randrange(230, CURB_Y - 10)), dk(base, 0.3))
    cv.dither_blend(x, 214, w, 4, (20, 10, 10), 0.5)
    fg_curb(cv, x, w, top=C("#4a4446"), face=C("#221e22"))
    # hazard edge
    for xx in range(x, x + w, 8):
        cv.poly([(xx, CURB_Y + 1), (xx + 4, CURB_Y + 1), (xx + 2, CURB_Y + 5), (xx - 2, CURB_Y + 5)], P["yellow"])


@ground("neon_asphalt")
def g_neon(R, x, w):
    cv = R.cv
    sidewalk(cv, x, w, 214, 240, base=C("#7a7486"), slab=28, seed=R.id)
    curb(cv, x, w, 240, top=C("#9a94a4"))
    asphalt(cv, x, w, 247, CURB_Y, base=C("#34324a"), seed=R.id, lane_col=C("#7a7890"))
    # wet sheen: faint horizontal streaks
    rng = R.rng("sheen", x)
    for _ in range(w // 18):
        sx = rng.randrange(x, x + w)
        sy = rng.randrange(250, CURB_Y - 2)
        cv.hl(sx, sy, rng.randrange(6, 26), C("#46445e"))
    fg_curb(cv, x, w, top=C("#5a5668"), face=C("#1e1c2c"))


@ground("wet_road")
def g_wet(R, x, w):
    cv = R.cv
    sidewalk(cv, x, w, 214, 238, base=C("#7e8288"), slab=30, seed=R.id)
    curb(cv, x, w, 238, top=C("#9aa0a6"))
    asphalt(cv, x, w, 245, CURB_Y, base=C("#3a3e4a"), seed=R.id, lane_col=C("#c8c0a0"))
    rng = R.rng("pud", x)
    for _ in range(max(2, w // 120)):
        px_ = rng.randrange(x, x + w - 40)
        py_ = rng.randrange(252, CURB_Y - 14)
        pw, ph = rng.randrange(24, 60), rng.randrange(5, 10)
        cv.ellipse(px_, py_, px_ + pw, py_ + ph, C("#4e586a"))
        cv.ellipse(px_ + 3, py_ + 1, px_ + pw - 3, py_ + ph - 2, C("#5a667a"))
        cv.hl(px_ + pw // 3, py_ + 2, pw // 3, C("#8a96a8"))
    for _ in range(w // 14):
        sx = rng.randrange(x, x + w)
        sy = rng.randrange(248, CURB_Y - 2)
        cv.hl(sx, sy, rng.randrange(4, 16), C("#464c5a"))
    fg_curb(cv, x, w, top=C("#5e6268"), face=C("#1e2028"))


@ground("rooftop")
def g_rooftop(R, x, w):
    cv = R.cv
    base = C("#4a4648")
    rng = R.rng("roof", x)
    cv.rect(x, 214, w, CURB_Y - 214, base)
    cv.noise_tint(x, 214, w, CURB_Y - 214, rng, amount=7, density=0.25)
    for (yy, hh) in persp_rows(214, CURB_Y, 26, 40):
        cv.hl(x, yy, w, dk(base, 0.25))
        cv.hl(x, yy + 1, w, lt(base, 0.08))
        off = rng.randrange(0, 80)
        for xx in range(x + off, x + w, 110):
            cv.vl(xx, yy, hh, dk(base, 0.2))
    for _ in range(w // 200):
        px_ = rng.randrange(x, x + w - 50)
        py_ = rng.randrange(236, CURB_Y - 12)
        cv.ellipse(px_, py_, px_ + rng.randrange(20, 50), py_ + rng.randrange(4, 8), C("#3a3a48"))
    cv.dither_blend(x, 214, w, 5, (10, 10, 20), 0.5)
    # front parapet coping
    tex_brick(cv, x, CURB_Y + 4, w, H - CURB_Y - 4, base=C("#7a3a32"), seed=seed_of(R.id), calm=True)
    cv.rect(x, CURB_Y, w, 5, C("#8a8478"))
    cv.hl(x, CURB_Y, w, C("#b8b0a0"))
    cv.hl(x, CURB_Y + 4, w, C("#4a4440"))


@ground("warehouse_floor")
def g_wfloor(R, x, w):
    cv = R.cv
    base = C("#727078")
    cv.rect(x, 214, w, CURB_Y - 214, base)
    rng = R.rng("wf", x)
    cv.noise_tint(x, 214, w, CURB_Y - 214, rng, amount=4, density=0.1)
    for (yy, hh) in persp_rows(214, CURB_Y, 30, 44):
        cv.hl(x, yy, w, dk(base, 0.15))
        for xx in range((x // 96) * 96, x + w, 96):
            cv.vl(xx, yy, hh, dk(base, 0.15))
    for _ in range(w // 150):
        px_ = rng.randrange(x, x + w - 40)
        py_ = rng.randrange(240, CURB_Y - 12)
        cv.ellipse(px_, py_, px_ + rng.randrange(14, 40), py_ + rng.randrange(4, 9), dk(base, 0.18))
    # tyre marks
    for _ in range(w // 300):
        px_ = rng.randrange(x, x + w - 120)
        py_ = rng.randrange(260, CURB_Y - 20)
        for k in range(rng.randrange(60, 140)):
            cv.px(px_ + k, py_ + int(3 * math.sin(k / 30)), dk(base, 0.12))
            cv.px(px_ + k, py_ + 8 + int(3 * math.sin(k / 30)), dk(base, 0.12))
    yl = P["yellow"]
    for yy in (226, 332):
        cv.rect(x, yy, w, 2, yl)
        cv.dither_blend(x, yy, w, 2, base, 0.2)
    cv.dither_blend(x, 214, w, 4, (20, 20, 30), 0.5)
    for xx in range(x, x + w, 10):
        cv.poly([(xx, CURB_Y), (xx + 5, CURB_Y), (xx + 1, CURB_Y + 5), (xx - 4, CURB_Y + 5)], yl)
        cv.poly([(xx + 5, CURB_Y), (xx + 10, CURB_Y), (xx + 6, CURB_Y + 5), (xx + 1, CURB_Y + 5)], C("#24222a"))
    cv.vgrad(x, CURB_Y + 5, w, H - CURB_Y - 5, [C("#4a4850"), C("#24222a")], levels=4)


@ground("office_floor")
def g_office(R, x, w):
    cv = R.cv
    base = C("#5a6474")
    for (yy, hh) in persp_rows(214, CURB_Y, 12, 18):
        for xx in range((x // 24) * 24, x + w, 24):
            k = ((xx // 24) + (yy // 7)) % 2
            tone = base if k else mix(base, C("#6a7484"), 0.5)
            cv.rect(xx, yy, 24, hh, tone)
            cv.hl(xx, yy, 24, dk(base, 0.15))
    cv.dither_blend(x, 214, w, 4, (10, 10, 20), 0.5)
    fg_curb(cv, x, w, top=C("#4a505a"), face=C("#22262e"))


# ---- interior floors ---------------------------------------------------------
def int_floor_fg(cv, x, w):
    cv.dither_blend(x, CURB_Y + 4, w, H - CURB_Y - 4, (0, 0, 0), 0.25)
    cv.dither_blend(x, 196, w, 4, (0, 0, 0), 0.45)


@ground("checker_floor")
def g_checker(R, x, w):
    cv = R.cv
    a, b = C("#d8d0c2"), C("#9a8e9e")
    for i, (yy, hh) in enumerate(persp_rows(196, H, 12, 22)):
        sz = int(hh * 1.6)
        off = (yy - 196) // 6
        for xx in range(x - sz, x + w, sz):
            k = ((xx - x) // sz + i) % 2
            col = a if k else b
            cv.rect(xx, yy, sz, hh, col)
            cv.hl(xx, yy, sz, lt(col, 0.12) if k else lt(col, 0.08))
    cv.rect(x, 196, w, 6, C("#5a3a3a"))
    cv.hl(x, 196, w, C("#c8c0b0"))
    int_floor_fg(cv, x, w)


@ground("garage_floor")
def g_garage_floor(R, x, w):
    cv = R.cv
    base = C("#7e7a74")
    cv.rect(x, 196, w, H - 196, base)
    rng = R.rng("gf", x)
    cv.noise_tint(x, 196, w, H - 196, rng, amount=5, density=0.14)
    for (yy, hh) in persp_rows(196, H, 34, 50):
        cv.hl(x, yy, w, dk(base, 0.15))
    for xx in range(x + 160, x + w, 160):
        cv.vl(xx, 196, H - 196, dk(base, 0.15))
    for _ in range(max(2, w // 120)):
        px_ = rng.randrange(x, x + w - 40)
        py_ = rng.randrange(220, H - 30)
        cv.ellipse(px_, py_, px_ + rng.randrange(16, 40), py_ + rng.randrange(5, 10), dk(base, 0.25))
        cv.ellipse(px_ + 4, py_ + 2, px_ + 12, py_ + 4, dk(base, 0.35))
    for yy in (204,):
        cv.rect(x, yy, w, 2, P["yellow"])
        cv.dither_blend(x, yy, w, 2, base, 0.3)
    int_floor_fg(cv, x, w)


def wood_floor(cv, x, w, base, seed, y0=196):
    for (yy, hh) in persp_rows(y0, H, 6, 11):
        tex_planks_h(cv, x, yy, w, hh, base, ph=hh, seed=f"{seed}{yy}", nails=False)


@ground("gym_floor")
def g_gym(R, x, w):
    cv = R.cv
    wood_floor(cv, x, w, C("#c08a52"), R.id)
    cv.rect(x, 300, w, 2, P["red"])
    cv.rect(x, 210, w, 2, P["blue"])
    int_floor_fg(cv, x, w)


@ground("wood_floor")
def g_wood(R, x, w):
    wood_floor(R.cv, x, w, C("#9a6a40"), R.id)
    int_floor_fg(R.cv, x, w)


@ground("plank_floor")
def g_plank(R, x, w):
    cv = R.cv
    wood_floor(cv, x, w, C("#86725a"), R.id)
    int_floor_fg(cv, x, w)


@ground("carpet_floor")
def g_carpet(R, x, w):
    cv = R.cv
    base = C("#7a3a3a")
    cv.rect(x, 196, w, H - 196, base)
    yy, xx = np.mgrid[196:H, x:x + w]
    m = (((xx // 8) + (yy // 6)) % 4 == 0) & (((xx // 8) - (yy // 6)) % 4 == 0)
    cv.a[196:H, x:x + w][m, :3] = dk(base, 0.1)
    m2 = (((xx + 4) // 8 + (yy + 3) // 6) % 8 == 0) & ((((xx + 4) // 8) - ((yy + 3) // 6)) % 8 == 0)
    cv.a[196:H, x:x + w][m2, :3] = mix(base, C("#a8763a"), 0.45)
    cv.rect(x, 206, w, 3, C("#a8763a"))
    cv.rect(x, 209, w, 2, dk(base, 0.3))
    int_floor_fg(cv, x, w)


@ground("tile_floor")
def g_tile(R, x, w):
    cv = R.cv
    a = C("#d8ccb0")
    g = C("#9a907c")
    for i, (yy, hh) in enumerate(persp_rows(196, H, 9, 15)):
        sz = int(hh * 1.3)
        for xx in range(x - (i % 2) * sz // 2, x + w, sz):
            tone = mix(a, C("#c8b898"), ((xx // sz + i) % 3) / 4)
            cv.rect(xx, yy, sz, hh, tone)
            cv.hl(xx, yy, sz, g)
            cv.vl(xx, yy, hh, g)
    int_floor_fg(cv, x, w)


@ground("white_tile")
def g_white_tile(R, x, w):
    cv = R.cv
    a = C("#e4e8e8")
    g = C("#b4bcc0")
    for i, (yy, hh) in enumerate(persp_rows(196, H, 10, 16)):
        sz = int(hh * 1.4)
        for xx in range(x, x + w, sz):
            cv.rect(xx, yy, sz, hh, a if (xx // sz + i) % 2 else mix(a, C("#d0e0e4"), 0.5))
            cv.hl(xx, yy, sz, g)
            cv.vl(xx, yy, hh, g)
    int_floor_fg(cv, x, w)


@ground("arcade_carpet")
def g_arcade_carpet(R, x, w):
    cv = R.cv
    base = C("#1e1a3a")
    cv.rect(x, 196, w, H - 196, base)
    rng = R.rng("ac", x)
    cols = [C("#5a2e6a"), C("#24606e"), C("#6a5e30"), C("#2e4078")]
    for _ in range(w * (H - 196) // 260):
        sx = rng.randrange(x, x + w)
        sy = rng.randrange(198, H)
        c = rng.choice(cols)
        k = rng.random()
        if k < 0.35:
            cv.line(sx, sy, sx + 3, sy - 2, c)
            cv.line(sx + 3, sy - 2, sx + 6, sy, c)
        elif k < 0.6:
            cv.poly([(sx, sy), (sx + 4, sy), (sx + 2, sy - 3)], c)
        elif k < 0.8:
            cv.rect(sx, sy, 2, 2, c)
        else:
            cv.px(sx, sy, c)
            cv.px(sx + 2, sy + 1, c)
    int_floor_fg(cv, x, w)


# ----------------------------------------------------------------------------
# water
# ----------------------------------------------------------------------------
def water(cv, R, x, y, w, h, deep=None, mid=None, light=None, seed=0, sparkle=True, em_spark=False):
    deep = deep or P["water"]
    mid = mid or P["water_m"]
    light = light or P["water_l"]
    cv.vgrad(x, y, w, h, [mid, deep, dk(deep, 0.2)], levels=max(3, h // 6))
    rng = rng_of("water", seed, x, y)
    n = max(1, w * h // 150)
    for _ in range(n):
        sx = rng.randrange(x, x + w)
        sy = rng.randrange(y, y + h)
        t = (sy - y) / max(1, h)
        ln = rng.randrange(3, 9) + int(t * 6)
        c = mix(mid, light, 0.6) if rng.random() < 0.6 else dk(deep, 0.25)
        cv.hl(sx, sy, ln, c)
    if sparkle:
        for _ in range(max(1, w * h // 900)):
            sx = rng.randrange(x, x + w)
            sy = rng.randrange(y, y + h)
            cv.hl(sx, sy, 2, (240, 250, 255), em=1 if em_spark else 0)


# ----------------------------------------------------------------------------
# post processing
# ----------------------------------------------------------------------------
def _quant_dither(v, step, yy, xx):
    return np.floor(v / step + BAYER[yy % 4, xx % 4]) * step


def post_grade(R):
    a = R.cv.a
    em = R.cv.em
    rgb = a[..., :3].astype(np.float32)
    op = a[..., 3] > 0
    keep = (~op) | (em > 0)
    if R.interior:
        it = INTERIOR_THEMES.get(R.d["facades"][0]["kind"], dict(grade=(1, 1, 1)))
        rgb *= np.array(it["grade"], np.float32)
    else:
        top = FACADE_BOTTOM
        rgb[:top] *= np.array(R.T["grade_f"], np.float32)
        rgb[top:] *= np.array(R.T["grade_g"], np.float32)
        amt = R.T.get("top_light_amt", 0)
        if amt > 0:
            ys = np.arange(top, dtype=np.float32)
            t = ((1 - ys / top) ** 1.4 * amt)[:, None, None]
            rgb[:top] = rgb[:top] * (1 - t) + np.array(R.T["top_light"], np.float32) * t
        # ambient occlusion where facades meet ground
        ys = np.arange(top - 16, top, dtype=np.float32)
        t = ((ys - (top - 16)) / 16.0)[:, None, None] * 0.18
        rgb[top - 16:top] *= (1 - t)
    out = np.clip(rgb, 0, 255).astype(np.uint8)
    a[..., :3] = np.where(keep[..., None], a[..., :3], out)


def post_lights(R):
    cv = R.cv
    if not R.lights:
        return
    s_mul = 1.0 if (R.night or R.interior) else (0.5 if R.district in ("old_quarter", "ironworks") else 0.3)
    acc = np.zeros((H, R.w, 3), np.float32)
    for L in R.lights:
        x, y, col, r, st = L[:5]
        kind = L[5] if len(L) > 5 else "halo"
        ry = r * (0.35 if kind == "pool" else 1.0)
        x0, x1 = int(max(0, x - r)), int(min(R.w, x + r + 1))
        y0, y1 = int(max(0, y - ry)), int(min(H, y + ry + 1))
        if x1 <= x0 or y1 <= y0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = np.sqrt(((xx - x) / r) ** 2 + ((yy - y) / max(1, ry)) ** 2)
        v = np.clip(1 - d, 0, 1) ** 1.6 * st * s_mul
        acc[y0:y1, x0:x1] += v[..., None] * np.array(col, np.float32)[None, None, :] * 0.55
    yy, xx = np.mgrid[0:H, 0:R.w]
    acc = _quant_dither(acc, 10.0, yy[..., None], xx[..., None])
    op = cv.a[..., 3] > 0
    out = cv.a[..., :3].astype(np.float32) + acc
    cv.a[..., :3] = np.where(op[..., None], np.clip(out, 0, 255), cv.a[..., :3]).astype(np.uint8)


WET_STYLES = {"neon_asphalt", "wet_road", "white_tile", "rooftop"}


def ground_style_at(R, x):
    for g in R.d.get("ground", []):
        if g["x"] <= x < g["x"] + g["w"]:
            return g["style"]
    return None


def post_reflections(R):
    cv = R.cv
    if R.interior:
        return
    for (x0, x1, ysrc, col, st) in R.refl:
        st0 = st
        cx = (x0 + x1) // 2
        style = ground_style_at(R, cx)
        if style not in WET_STYLES:
            continue
        if style in ("rooftop",):
            st0 *= 0.4
        if style == "foundry_floor":
            st0 *= 0.6
        span = int(min(CURB_Y - FACADE_BOTTOM - 8, max(16, (FACADE_BOTTOM - ysrc) * 0.8)))
        rng = R.rng("refl", x0, ysrc)
        cx = (x0 + x1) // 2
        for k in range(span):
            yy = FACADE_BOTTOM + 4 + k
            t = k / span
            if k % 4 == 3 or (t > 0.3 and k % 4 == 1 and rng.random() < 0.5):
                continue
            al = st0 * 0.34 * (1 - t) ** 1.6
            al = math.floor(al / 0.06) * 0.06
            if al <= 0:
                continue
            wv = max(2, int((x1 - x0) * (0.85 - 0.35 * t)))
            jit = int(round(math.sin(k * 0.8 + x0 * 0.13) * (1 + 3 * t)))
            xa = cx - wv // 2 + jit
            # break the streak into ripple dashes
            xx = xa
            while xx < xa + wv:
                dl = rng.randrange(4, 14)
                cv.blend(xx, yy, min(dl, xa + wv - xx), 1, lt(col, 0.15), al)
                xx += dl + (rng.randrange(1, 4) if t > 0.2 else 0)


def post_bloom(R):
    cv = R.cv
    st = INTERIOR_THEMES.get(R.d["facades"][0]["kind"], {}).get("bloom", 0.5) if R.interior else R.T["bloom"]
    if st <= 0:
        return
    src = np.zeros((H, R.w, 3), np.uint8)
    m = cv.em > 0
    src[m] = cv.a[..., :3][m]
    im = Image.fromarray(src, "RGB")
    b1 = np.array(im.filter(ImageFilter.GaussianBlur(3)), np.float32)
    b2 = np.array(im.filter(ImageFilter.GaussianBlur(9)), np.float32)
    acc = (b1 * 0.55 + b2 * 0.9) * st
    yy, xx = np.mgrid[0:H, 0:R.w]
    acc = _quant_dither(acc, 12.0, yy[..., None], xx[..., None])
    op = cv.a[..., 3] > 0
    out = cv.a[..., :3].astype(np.float32) + acc * np.where(m, 0.3, 1.0)[..., None]
    cv.a[..., :3] = np.where(op[..., None], np.clip(out, 0, 255), cv.a[..., :3]).astype(np.uint8)


def lamp_pools(R):
    """Light pools on the ground under lamp-type props listed in rooms.json."""
    cols = {"lamp_post": P["lamp"], "lamp_sodium": P["sodium"], "floodlight": C("#f0f4ff"),
            "neon_post": P["n_pink"]}
    for p in R.d.get("props", []):
        c = cols.get(p["type"])
        if c is None:
            continue
        R.lights.append((p["x"], p["y"] + 14, c, 54, 0.5, "pool"))
        if p["type"] in ("lamp_sodium", "lamp_post", "neon_post"):
            R.refl.append((p["x"] - 3, p["x"] + 4, 150, c, 0.6))


def doormat(R, x0, x1):
    cv = R.cv
    w = x1 - x0
    if R.interior:
        # doorway gap in the foreground wall: light spilling in from outside
        cv.rect(x0 - 4, CURB_Y + 6, 4, H - CURB_Y - 6, C("#5a4a3a"))
        cv.rect(x1, CURB_Y + 6, 4, H - CURB_Y - 6, C("#5a4a3a"))
        cv.vgrad(x0, H - 6, w, 6, [C("#c8b890"), C("#f0e0b0")], em=1)
        cv.hl(x0 - 4, H - 7, w + 8, C("#8a8070"))
        # rubber/coir doormat
        mx0, my0, mw, mh = x0 + 8, CURB_Y - 10, w - 16, 16
        mat = C("#8a5a34")
        cv.rect(mx0, my0, mw, mh, dk(mat, 0.45))
        cv.rect(mx0 + 1, my0 + 1, mw - 2, mh - 2, mat)
        cv.rect(mx0 + 3, my0 + 3, mw - 6, mh - 6, dk(mat, 0.15))
        for xx in range(mx0 + 4, mx0 + mw - 4, 3):
            cv.vl(xx, my0 + 3, mh - 6, dk(mat, 0.25))
        cv.hl(mx0 + 1, my0 + 1, mw - 2, lt(mat, 0.25))
        R.lights.append(((x0 + x1) // 2, H, C("#ffe8b0"), 60, 0.5, "pool"))
    else:
        # alley mouth: lighter street glow at the foreground edge
        cv.vgrad(x0, CURB_Y, w, H - CURB_Y, [C("#6a6680"), C("#a09ab8")])
        for xx in range(x0, x1, 6):
            cv.vl(xx, CURB_Y, H - CURB_Y, C("#5a5670"))
        R.lights.append(((x0 + x1) // 2, H - 4, C("#ffd890"), 50, 0.7, "pool"))


def water_blockers(R):
    cv = R.cv
    for b in R.d.get("blockers", []):
        if b.get("kind") != "water":
            continue
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        water(cv, R, x, y, w, h, seed=R.id + str(y), sparkle=True)
        wood = C("#6a4a2e")
        wood_l = C("#a07a50")
        # quay edges on either side (boardwalk ends)
        for ex in (x - 6, x + w):
            cv.rect(ex, y, 6, h, C("#4a3220"))
            cv.vl(ex + (5 if ex < x else 0), y, h, C("#2a1a10"))
            for yy in range(y + 4, y + h, 10):
                cv.hl(ex, yy, 6, wood)
        if y <= FACADE_BOTTOM + 2:
            # far water: back railing of the deck along the bottom edge of this rect
            ey = y + h
            cv.rect(x, ey - 3, w, 3, wood)
            cv.hl(x, ey - 3, w, wood_l)
            cv.rect(x, ey - 16, w, 2, wood)
            cv.hl(x, ey - 16, w, wood_l)
            cv.rect(x, ey - 10, w, 1, dk(wood, 0.2))
            for px_ in range(x, x + w + 1, 25):
                cv.rect(px_, ey - 18, 3, 18, dk(wood, 0.15))
                cv.vl(px_, ey - 18, 18, wood_l)
            # shadow line where water meets deck
            cv.hl(x, ey, w, dk(C("#a8835a"), 0.5))
        else:
            # near water: front edge beam + pilings sinking into water
            cv.rect(x, y, w, 4, wood)
            cv.hl(x, y, w, wood_l)
            cv.hl(x, y + 4, w, C("#2a1a10"))
            for px_ in range(x + 4, x + w, 25):
                cv.rect(px_, y + 4, 4, 14, C("#4a3220"))
                cv.vl(px_, y + 4, 14, wood)
                cv.hl(px_ - 2, y + 18, 8, P["water_l"])
            cv.dither_blend(x, y + 5, w, 4, (0, 0, 0), 0.4)


def door_style(R, d):
    styles = {"diner": "diner", "garage": "garage", "rec_center": "civic", "tunnel_arch": "tunnel",
              "shopfront": "shop", "canteen": "industrial", "switch_house": "industrial", "pharmacy": "neon",
              "arcade_front": "neon", "alley_gap": "alley", "bait_shop": "shack", "neon_shopfront": "neon"}
    for f in R.d["facades"]:
        if f["x"] <= d["x"] < f["x"] + f["w"]:
            acc = R.accents.get(f["x"])
            return styles.get(f["kind"], "shop"), acc
    return "shop", None


FACADES = {}


def facade(name):
    def deco(f):
        FACADES[name] = f
        return f
    return deco


def build_room(rid, data):
    R = Room(rid, data)
    R.accents = {}
    cv = R.cv
    for g in data.get("ground", []):
        fn = GROUNDS.get(g["style"])
        if fn is None:
            raise SystemExit(f"[{rid}] unknown ground style {g['style']}")
        with cv.clipped(g["x"], g["x"] + g["w"]):
            fn(R, g["x"], g["w"])
    for f in data.get("facades", []):
        fn = FACADES.get(f["kind"])
        if fn is None:
            raise SystemExit(f"[{rid}] unknown facade kind {f['kind']}")
        with cv.clipped(f["x"], f["x"] + f["w"]):
            fn(R, f["x"], f["w"], f)
    for d in data.get("doors", []):
        st, acc = door_style(R, d)
        entrance(R, d, st, acc)
    water_blockers(R)
    south = data.get("exits", {}).get("south")
    if south:
        doormat(R, south["x0"], south["x1"])
    if not R.interior:
        lamp_pools(R)
    post_grade(R)
    post_lights(R)
    post_reflections(R)
    post_bloom(R)
    if R.interior:
        cv.a[..., 3] = 255
    return R


# ============================================================================
# FACADES - Old Quarter
# ============================================================================
BRICKS = [
    (C("#a04a3a"), C("#7a3428"), C("#c8664a")),
    (C("#8e4434"), C("#6a2e24"), C("#b45a44")),
    (C("#a85a3e"), C("#7e3e2a"), C("#c87454")),
    (C("#7e4a3e"), C("#5a3228"), C("#a0624e")),
]
PAINTS = [C("#d8c8a0"), C("#9ab0a0"), C("#c89a7a"), C("#8a9ab8"), C("#c8b078")]


def split_widths(w, target, rng, minw=60):
    n = max(1, int(round(w / target)))
    base = w / n
    xs = [0]
    for i in range(1, n):
        xs.append(int(round(i * base + rng.uniform(-base * 0.12, base * 0.12))))
    xs.append(w)
    return [(xs[i], xs[i + 1] - xs[i]) for i in range(n)]


@facade("rowhouse")
def f_rowhouse(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("row", x0)
    houses = split_widths(w, 100 if var == 0 else 96, rng)
    tops = []
    for i, (hx, hw) in enumerate(houses):
        x = x0 + hx
        top = rng.randrange(44, 74)
        tops.append(top)
        roof_clear(cv, x, hw, top - 8)
        if var == 1 and i % 2 == 1:
            col = rng.choice(PAINTS)
            cv.rect(x, top, hw, FACADE_BOTTOM - top, col)
            tex_siding(cv, x, top, hw, FACADE_BOTTOM - top, col, pitch=4)
            trim = P["white"]
        else:
            b = BRICKS[(i + var + rng.randrange(4)) % 4]
            tex_brick(cv, x, top, hw, FACADE_BOTTOM - top, base=b[0], shadow=b[1], hi=b[2],
                      seed=seed_of(R.id, x), weather=0.6)
            trim = rng.choice([C("#d8ccb4"), C("#c8b898"), C("#e0d8c8")])
        # party wall shadow
        cv.vl(x, top, FACADE_BOTTOM - top, dk(cv_get(cv, x + 3, top + 10), 0.35))
        cv.vl(x + hw - 1, top, FACADE_BOTTOM - top, dk(cv_get(cv, x + 3, top + 10), 0.25))
        # cornice & parapet
        cornice(cv, x + 2, hw - 4, top - 6, trim, h=6)
        cv.rect(x + 2, top - 8, hw - 4, 2, dk(trim, 0.1))
        for bx in range(x + 6, x + hw - 4, 12):
            cv.rect(bx, top, 3, 4, dk(trim, 0.15))
        if rng.random() < 0.6:
            chx = x + rng.randrange(8, max(9, hw - 18))
            chh = rng.randrange(8, 16)
            tex_brick(cv, chx, top - 8 - chh, 10, chh, base=C("#8a4434"), seed=chx, calm=True)
            cv.rect(chx - 1, top - 8 - chh - 2, 12, 2, C("#6a625a"))
            cv.vl(chx + 9, top - 8 - chh, chh, C("#5a2a22"))
        # floors
        floors = [(top + 12, 22), (top + 12 + 44, 22)] if FACADE_BOTTOM - top > 120 else [(top + 12, 22)]
        ncol = 2 if hw < 110 else 3
        door_left = rng.random() < 0.5
        for fy, fh in floors:
            for k in range(ncol):
                wx = x + int((k + 0.5) * hw / ncol) - 8
                lit = rng.random() < 0.38
                window(cv, R, wx, fy, 16, fh, lit=lit, frame=trim, lintel=dk(trim, 0.05), rng=rng)
                if rng.random() < 0.2:
                    cv.rect(wx - 1, fy + fh + 2, 18, 4, P["wood_d"])
                    for fx in range(wx, wx + 16, 3):
                        cv.px(fx, fy + fh + 1, rng.choice([P["red"], P["n_pink"], P["mustard"], P["white"]]))
                        cv.px(fx + 1, fy + fh + 1, P["green"])
                elif rng.random() < 0.12:
                    ac_box(cv, wx + 2, fy + fh - 6)
        # ground floor: stoop + door + parlor window
        dw = 16
        dx = x + (10 if door_left else hw - 10 - dw)
        stoop(cv, dx - 4, dw + 8, steps=3)
        deco_door(cv, dx, FACADE_BOTTOM - 9, dw, 30, rng.choice([C("#2a4a3a"), C("#5a2a2a"), C("#2a3a5a"),
                                                                C("#3a2a22")]), frame=trim, step=False)
        cv.rect(dx - 2, FACADE_BOTTOM - 46, dw + 4, 5, trim)   # door hood
        cv.hl(dx - 2, FACADE_BOTTOM - 42, dw + 4, dk(trim, 0.4))
        pwx = x + (hw - 38 if door_left else 12)
        window(cv, R, pwx, FACADE_BOTTOM - 46, 26, 26, lit=rng.random() < 0.5, frame=trim,
               lintel=dk(trim, 0.05), rng=rng)
        # basement grate
        bx = pwx + 4
        cv.rect(bx, FACADE_BOTTOM - 10, 18, 7, C("#1e1a20"))
        for gx in range(bx + 1, bx + 18, 3):
            cv.vl(gx, FACADE_BOTTOM - 10, 7, C("#4a4450"))
        base_plinth(cv, x, hw, h=3)
        if i + 1 < len(houses):
            drainpipe(cv, x + hw - 2, top, FACADE_BOTTOM)
    # laundry lines across house pairs
    if len(houses) >= 2 and var == 0:
        for i in range(len(houses) - 1):
            if rng.random() < 0.7 or i == 0:
                xa = x0 + houses[i][0] + houses[i][1] // 2
                xb = x0 + houses[i + 1][0] + houses[i + 1][1] // 2
                ya = max(tops[i], tops[i + 1]) + 40
                laundry_line(cv, xa, ya, xb, ya + rng.randrange(-3, 4), rng)


@facade("diner")
def f_diner(R, x0, w, f):
    cv = R.cv
    rng = R.rng("diner", x0)
    top = 104
    # rear brick building set back (darker), gives the sign something to sit against
    roof_clear(cv, x0, w, top)
    bx0, bw = x0 + 30, w - 60
    tex_brick(cv, bx0, 56, bw, top - 56, base=C("#7a3c34"), seed=seed_of(R.id, "dinerback"), calm=True)
    cv.rect(bx0 - 2, 52, bw + 4, 4, C("#5a4a44"))
    for k in range(4):
        window(cv, R, bx0 + 16 + k * (bw - 32) // 3 - 7, 62, 14, 18, lit=k % 2 == 0, frame=C("#b8a890"),
               rng=rng)
    # roof sign on struts
    sw, sh = min(w - 40, 210), 34
    sx = x0 + (w - sw) // 2
    sy = 60
    for k in (sx + 16, sx + sw - 18):
        cv.rect(k, sy + sh, 3, top - sy - sh, C("#2a2630"))
        cv.line(k, sy + sh, k + 10, top - 1, C("#2a2630"))
    cv.rect(sx, sy, sw, sh, C("#c03a3a"))
    cv.rect(sx + 2, sy + 2, sw - 4, sh - 4, C("#2a1a2a"))
    bulbs(cv, sx + 1, sy + 1, sw - 2, sh - 2, step=4)
    neon_text(cv, R, sx + sw // 2 + 8, sy + 10, f.get("sign", "DINER"), P["n_yellow"])
    # spoon icon (neon)
    ix, iy = sx + 14, sy + 9
    cv.ellipse(ix - 3, iy, ix + 4, iy + 8, lt(P["n_cyan"], 0.4), em=1)
    cv.ellipse(ix - 1, iy + 2, ix + 2, iy + 6, C("#2a1a2a"))
    cv.rect(ix, iy + 9, 2, 8, lt(P["n_cyan"], 0.4), em=1)
    # streamline body
    body_top = top
    cv.rect(x0 + 4, body_top, w - 8, FACADE_BOTTOM - body_top, C("#e8e0cc"))
    # rounded ends
    for ex, sgn in ((x0 + 4, 1), (x0 + w - 5, -1)):
        for k in range(12):
            cv.vl(ex + sgn * 0, body_top, FACADE_BOTTOM - body_top, C("#d0c8b4"))
        cv.vl(ex, body_top, FACADE_BOTTOM - body_top, C("#a89e8a") if sgn > 0 else C("#8a8270"))
    # roof cap
    cv.rect(x0 + 2, body_top - 6, w - 4, 6, C("#b02e34"))
    cv.hl(x0 + 2, body_top - 6, w - 4, C("#e05a5a"))
    cv.hl(x0 + 2, body_top - 1, w - 4, C("#6a1a22"))
    # chrome bands
    for yy in (body_top + 4, body_top + 66):
        cv.rect(x0 + 4, yy, w - 8, 3, P["steel_l"])
        cv.hl(x0 + 4, yy, w - 8, (240, 244, 250))
        cv.hl(x0 + 4, yy + 2, w - 8, P["steel"])
    cv.rect(x0 + 4, body_top + 9, w - 8, 5, P["red"])
    cv.hl(x0 + 4, body_top + 13, w - 8, P["red_d"])
    # windows band with booths inside
    wy0, wy1 = body_top + 18, body_top + 62
    door_x = R.doors_in(x0, x0 + w)[0]["x"] if R.doors_in(x0, x0 + w) else x0 + w // 2
    xx = x0 + 12
    while xx < x0 + w - 30:
        ww = 34
        if abs((xx + ww // 2) - door_x) < 36:
            xx = door_x + 22
            continue
        if xx + ww > x0 + w - 12:
            break
        cv.rect(xx - 1, wy0 - 1, ww + 2, wy1 - wy0 + 2, P["steel"])
        cv.vgrad(xx, wy0, ww, wy1 - wy0, [C("#fff0c0"), C("#ffd890"), C("#e8a060")], em=1)
        # pendant lamps
        cv.vl(xx + ww // 2, wy0, 6, C("#5a4a3a"), em=1)
        cv.rect(xx + ww // 2 - 3, wy0 + 6, 7, 3, P["red"], em=1)
        # booth backs + table + diners silhouettes
        cv.rect(xx, wy1 - 14, ww, 14, C("#b8343a"), em=1)
        cv.hl(xx, wy1 - 14, ww, C("#e8686a"), em=1)
        for k in range(0, ww, 17):
            cv.vl(xx + k, wy1 - 14, 14, C("#7a2028"), em=1)
        if rng.random() < 0.6:
            hx = xx + rng.randrange(4, ww - 8)
            sil = C("#6a4038")
            cv.ellipse(hx, wy1 - 25, hx + 6, wy1 - 18, sil, em=1)
            cv.rect(hx - 1, wy1 - 18, 9, 6, sil, em=1)
        cv.hl(xx, wy0, ww, C("#ffffff"), em=1)
        xx += ww + 6
    # lower panel: red/teal tiles
    for yy in range(body_top + 70, FACADE_BOTTOM - 3, 4):
        for xx in range(x0 + 4, x0 + w - 4, 4):
            k = ((xx - x0) // 4 + (yy // 4)) % 2
            cv.rect(xx, yy, 4, 4, C("#2a8a8a") if k else C("#e8e0cc"))
    cv.rect(x0 + 4, FACADE_BOTTOM - 3, w - 8, 3, P["steel"])
    R.accents[x0] = P["red"]
    R.lights.append((x0 + w // 2, wy1, C("#ffd890"), w // 2, 0.5))
    R.refl.append((sx, sx + sw, sy + sh, P["n_yellow"], 0.6))


@facade("laundromat")
def f_laundromat(R, x0, w, f):
    cv = R.cv
    rng = R.rng("laund", x0)
    top = 62
    roof_clear(cv, x0, w, top - 8)
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=C("#9a5040"), seed=seed_of(R.id, x0), weather=0.5)
    cornice(cv, x0 + 2, w - 4, top - 6, C("#c8bca8"))
    cv.rect(x0 + 2, top - 8, w - 4, 2, C("#a89c88"))
    # upper windows
    for k in range(3):
        wx = x0 + int((k + 0.5) * w / 3) - 9
        window(cv, R, wx, top + 14, 18, 26, lit=rng.random() < 0.5, frame=C("#d8ccb4"), lintel=C("#c8bca8"),
               rng=rng)
    # sign band
    sy = 122
    signboard(cv, x0 + 10, sy, w - 20, 20, f.get("sign", "LAUNDRY"), C("#2a6ac0"), P["white"],
              border=C("#163a7a"))
    for bx, by in ((x0 + 16, sy + 4), (x0 + w - 20, sy + 12), (x0 + w - 16, sy + 4)):
        cv.ellipse(bx, by, bx + 3, by + 3, C("#a8d8f0"))
        cv.px(bx + 1, by + 1, P["white"])
    # storefront
    fy = 146
    cv.rect(x0 + 6, fy, w - 12, FACADE_BOTTOM - fy, C("#3a3a46"))
    gx, gy, gw, gh = x0 + 9, fy + 3, w - 18, FACADE_BOTTOM - fy - 12
    cv.vgrad(gx, gy, gw, gh, [C("#f0fbff"), C("#c0e4f0"), C("#88c0d8")], em=1)
    # washers
    for k, mx in enumerate(range(gx + 4, gx + gw - 22, 24)):
        cv.rect(mx, gy + gh - 26, 20, 26, C("#f4f4f0"), em=1)
        cv.hl(mx, gy + gh - 26, 20, C("#ffffff"), em=1)
        cv.rect(mx, gy + gh - 22, 20, 1, C("#b8c0c8"), em=1)
        cv.ellipse(mx + 3, gy + gh - 19, mx + 16, gy + gh - 6, C("#5a6a7a"), em=1)
        cv.ellipse(mx + 5, gy + gh - 17, mx + 14, gy + gh - 8, C("#4a90c0") if k % 2 else C("#7ab0d8"), em=1)
        cv.px(mx + 7, gy + gh - 15, C("#e0f4ff"), em=1)
        cv.px(mx + 16, gy + gh - 24, P["red"], em=1)
    # fluorescent tubes
    for tx in range(gx + 10, gx + gw - 20, 40):
        cv.rect(tx, gy + 2, 26, 2, (255, 255, 255), em=1)
    for xx in range(gx, gx + gw, max(30, gw // 3)):
        cv.vl(xx, gy, gh, C("#3a3a46"))
    cv.hl(gx, gy, gw, C("#2a2a36"))
    cv.rect(x0 + 6, FACADE_BOTTOM - 9, w - 12, 9, C("#5a5a66"))
    cv.hl(x0 + 6, FACADE_BOTTOM - 9, w - 12, C("#8a8a96"))
    R.lights.append((x0 + w // 2, fy + 30, C("#c0e8ff"), w // 2, 0.4))
    R.refl.append((gx, gx + gw, fy + 20, C("#c0e8ff"), 0.4))


@facade("alley_gap")
def f_alley_gap(R, x0, w, f):
    cv = R.cv
    rng = R.rng("alley", x0)
    roof_clear(cv, x0, w, 28 if w < 100 else 0)
    # far wall
    far_top = 28
    tex_brick(cv, x0, far_top, w, FACADE_BOTTOM - far_top, base=C("#5a3a3a"), seed=seed_of(R.id, x0), calm=True)
    cv.blend(x0, far_top, w, FACADE_BOTTOM - far_top, C("#1a1424"), 0.55)
    # side walls in perspective (left and right return walls)
    side = max(8, w // 6)
    cv.poly([(x0, 0), (x0 + side, 18), (x0 + side, FACADE_BOTTOM - 14), (x0, FACADE_BOTTOM)], C("#2a2028"))
    cv.poly([(x0 + w - 1, 0), (x0 + w - 1 - side, 18), (x0 + w - 1 - side, FACADE_BOTTOM - 14),
             (x0 + w - 1, FACADE_BOTTOM)], C("#221a24"))
    # alley floor receding
    cv.poly([(x0, FACADE_BOTTOM), (x0 + side, FACADE_BOTTOM - 14), (x0 + w - 1 - side, FACADE_BOTTOM - 14),
             (x0 + w - 1, FACADE_BOTTOM)], C("#3a3440"))
    cv.hl(x0 + side, FACADE_BOTTOM - 14, w - 2 * side, C("#4a4450"))
    # pipes and a fire escape ladder on the far wall
    cv.rect(x0 + side + 3, far_top, 2, FACADE_BOTTOM - far_top - 14, C("#3a3440"))
    if w >= 100:
        fire_escape(cv, x0 + side + 10, min(60, w - 2 * side - 20), [90, 140], c=C("#1e1a24"), ladder=False)
    # trash silhouettes
    for k in range(2):
        tx = x0 + side + 4 + k * (w - 2 * side - 16)
        cv.rect(tx, FACADE_BOTTOM - 24, 9, 11, C("#2a2a34"))
        cv.hl(tx - 1, FACADE_BOTTOM - 25, 11, C("#3a3a46"))
    # dim lamp
    wall_lamp(cv, R, x0 + w // 2, 70, color=C("#ffcf7a"), em_strength=0.5)
    if f.get("sign"):
        s = f["sign"]
        # overhead arch with neon sign
        cv.rect(x0, 40, w, 4, C("#2a2630"))
        cv.rect(x0 + 6, 44, 3, FACADE_BOTTOM - 44, C("#2a2630"))
        cv.rect(x0 + w - 9, 44, 3, FACADE_BOTTOM - 44, C("#2a2630"))
        sw = min(w - 16, text_w(s, 1, True) + 16)
        signboard(cv, x0 + (w - sw) // 2, 46, sw, 16, None, C("#1a1424"), P["n_pink"], border=C("#3a2a3a"))
        neon_text(cv, R, x0 + w // 2, 50, s, P["n_pink"], gap=1)
        # string lights
        pts = cv.sag(x0 + 8, 72, x0 + w - 8, 72, 10, C("#2a2630"))
        for i, (px_, py_) in enumerate(pts[::6]):
            col = [P["n_yellow"], P["n_pink"], P["n_cyan"]][i % 3]
            cv.rect(px_, py_ + 1, 2, 2, col, em=1)
            R.lights.append((px_, py_ + 2, col, 10, 0.3))


@facade("closed_shop")
def f_closed_shop(R, x0, w, f):
    cv = R.cv
    rng = R.rng("closed", x0)
    top = rng.randrange(50, 64)
    roof_clear(cv, x0, w, top - 8)
    b = BRICKS[1]
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=b[0], shadow=b[1], hi=b[2], seed=seed_of(R.id, x0),
              weather=0.8)
    cornice(cv, x0 + 2, w - 4, top - 6, C("#9a9080"))
    cv.rect(x0 + 2, top - 8, w - 4, 2, C("#8a8070"))
    # dark upper windows, one broken, one FOR LEASE
    ncol = max(2, w // 70)
    for k in range(ncol):
        wx = x0 + int((k + 0.5) * w / ncol) - 9
        window(cv, R, wx, top + 14, 18, 26, lit=False, frame=C("#a89c88"), lintel=C("#9a9080"))
        if k == 0:
            cv.line(wx + 3, top + 16, wx + 9, top + 24, C("#e0e0e8"))
            cv.line(wx + 9, top + 24, wx + 6, top + 30, C("#e0e0e8"))
            cv.line(wx + 9, top + 24, wx + 14, top + 22, C("#e0e0e8"))
        if k == ncol - 1:
            cv.rect(wx + 2, top + 18, 14, 9, C("#e8e0c8"))
            cv.text(wx + 3, top + 20, "4", P["red"], 1)
            cv.hl(wx + 8, top + 20, 6, P["red"])
            cv.hl(wx + 8, top + 22, 5, C("#5a5a66"))
            cv.hl(wx + 8, top + 24, 6, C("#5a5a66"))
    # faded sign board (chipped)
    sy = 120
    s = f.get("sign", "SHOP")
    signboard(cv, x0 + 12, sy, w - 24, 20, s, C("#7a8a7a"), C("#d8d0b0"), border=C("#4a5248"))
    for _ in range(w // 6):
        px_ = rng.randrange(x0 + 13, x0 + w - 13)
        py_ = rng.randrange(sy + 1, sy + 19)
        if rng.random() < 0.5:
            cv.px(px_, py_, C("#6a7a6a"))
    cv.line(x0 + w - 30, sy + 19, x0 + w - 20, sy + 28, C("#4a5248"))   # sagging corner
    # storefront with boarded windows
    fy = 146
    cv.rect(x0 + 6, fy, w - 12, FACADE_BOTTOM - fy, C("#4a3a34"))
    door_w = 28
    dx = x0 + w // 2 - door_w // 2
    for (bx, bw) in ((x0 + 10, dx - x0 - 16), (dx + door_w + 6, x0 + w - 10 - dx - door_w - 6)):
        if bw < 10:
            continue
        tex_planks_v(cv, bx, fy + 4, bw, FACADE_BOTTOM - fy - 14, C("#b8955e"), pw=8, seed=bx)
        cv.line(bx + 1, fy + 5, bx + bw - 2, FACADE_BOTTOM - 12, C("#8a6a3a"))
        cv.line(bx + bw - 2, fy + 5, bx + 1, FACADE_BOTTOM - 12, C("#8a6a3a"))
        for nx, ny in ((bx + 2, fy + 6), (bx + bw - 3, fy + 6), (bx + 2, FACADE_BOTTOM - 13),
                       (bx + bw - 3, FACADE_BOTTOM - 13)):
            cv.px(nx, ny, C("#3a2a1a"))
        for k in range(rng.randrange(2, 4)):
            notice(cv, bx + rng.randrange(2, max(3, bw - 9)), fy + rng.randrange(8, 30),
                   header=rng.choice([P["red"], C("#3a3a46")]))
        if rng.random() < 0.8:
            tag_scribble(cv, bx + rng.randrange(2, max(3, bw - 24)), FACADE_BOTTOM - 26, rng)
    # roll-down shutter on the door
    tex_corrugated(cv, dx, fy + 4, door_w, FACADE_BOTTOM - fy - 4, C("#8a8a96"), pitch=3)
    cv.rect(dx - 1, fy + 2, door_w + 2, 4, C("#5a5a66"))
    cv.rect(dx + door_w // 2 - 2, FACADE_BOTTOM - 6, 4, 4, P["mustard_d"])
    notice(cv, dx + 10, fy + 18, w=9, h=11)
    tag_scribble(cv, dx + 2, fy + 34, rng, P["n_pink"])
    cv.rect(x0 + 6, FACADE_BOTTOM - 8, w - 12, 8, C("#5a4a40"))


@facade("brick_apartment")
def f_brick_apartment(R, x0, w, f):
    cv = R.cv
    rng = R.rng("apt", x0)
    var = f.get("variant", 0)
    top = 30
    roof_clear(cv, x0, w, top - 8)
    b = BRICKS[(3 + var) % 4]
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=b[0], shadow=b[1], hi=b[2], seed=seed_of(R.id, x0),
              weather=0.5)
    trim = C("#c8bca0")
    cornice(cv, x0 + 2, w - 4, top - 6, trim, h=6)
    for bx in range(x0 + 4, x0 + w - 4, 8):
        cv.rect(bx, top, 4, 3, dk(trim, 0.15))
    # stone band courses
    floors = [top + 12, top + 46, top + 80, top + 114]
    for fy in floors[1:]:
        cv.rect(x0, fy - 7, w, 3, mix(trim, b[0], 0.3))
    ncol = max(3, w // 52)
    fe_cols = {1, ncol - 2} if ncol >= 5 else {1}
    for k in range(ncol):
        cx = x0 + int((k + 0.5) * w / ncol)
        for j, fy in enumerate(floors):
            lit = rng.random() < 0.42
            pal = LIT_TV if (lit and rng.random() < 0.15) else None
            window(cv, R, cx - 8, fy, 16, 24, lit=lit, frame=trim, lintel=dk(trim, 0.05), rng=rng, pal=pal)
            if not lit and rng.random() < 0.1:
                ac_box(cv, cx - 6, fy + 16)
    for k in sorted(fe_cols):
        cx = x0 + int((k + 0.5) * w / ncol)
        fire_escape(cv, cx - 22, 44, [fy + 26 for fy in floors], bottom=floors[-1] + 26 + 30)
    # entrance with columns (decorative)
    ex = x0 + w // 2
    if ncol % 2 == 1:
        ex = x0 + int((ncol // 2 + 0.5) * w / ncol) + w // (2 * ncol)
    cv.rect(ex - 18, FACADE_BOTTOM - 52, 36, 4, trim)
    cv.hl(ex - 18, FACADE_BOTTOM - 52, 36, lt(trim, 0.3))
    for cxx in (ex - 16, ex + 12):
        cv.rect(cxx, FACADE_BOTTOM - 48, 4, 40, trim)
        cv.vl(cxx + 3, FACADE_BOTTOM - 48, 40, dk(trim, 0.3))
    deco_door(cv, ex - 9, FACADE_BOTTOM - 9, 18, 34, C("#3a2a22"), frame=dk(trim, 0.1), step=False)
    stoop(cv, ex - 18, 36, steps=3, rail=False)
    base_plinth(cv, x0, w, h=5)
    # rooftop water tank near one end
    if var == 0:
        water_tank(cv, x0 + w - 70, top - 6, w=26, h=16, legs=8)


@facade("garage")
def f_garage(R, x0, w, f):
    cv = R.cv
    rng = R.rng("garage", x0)
    top = 92
    roof_clear(cv, x0, w, top - 22)
    # cinder block walls
    blk = C("#b8ae98")
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=blk, shadow=C("#948a76"), hi=C("#d0c8b0"),
              mortar=C("#8a8270"), seed=seed_of(R.id, x0), bw=12, bh=6, weather=0.7, calm=True)
    # parapet + painted sign
    cv.rect(x0, top - 4, w, 4, C("#8a8270"))
    cv.hl(x0, top - 4, w, C("#d8d0b8"))
    s = f.get("sign", "GARAGE")
    sw = min(w - 30, text_w(s, 2) + 26)
    sx = x0 + (w - sw) // 2
    signboard(cv, sx, top - 24, sw, 24, s, C("#e8dcc0"), C("#b02e34"), border=C("#3a3a46"), scale=2)
    for k in (sx + 8, sx + sw - 10):
        cv.rect(k, top - 4, 2, 4, C("#3a3a46"))
    # gooseneck lamps over the sign
    for k in (sx + 20, sx + sw - 22):
        cv.line(k, top - 2, k, top - 30, C("#2a2a32"))
        cv.line(k, top - 30, k + 6, top - 30, C("#2a2a32"))
        cv.rect(k + 5, top - 30, 5, 3, C("#2a2a32"))
        cv.rect(k + 6, top - 27, 3, 1, P["lamp"], em=1)
        R.lights.append((k + 7, top - 20, P["lamp"], 18, 0.5))
    # roll-up doors
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else x0 + w // 2
    bays = [(x0 + 14, dx - 24 - (x0 + 14)), (dx + 24, x0 + w - 14 - (dx + 24))]
    for i, (bx, bw) in enumerate(bays):
        if bw < 30:
            continue
        by = 132
        cv.rect(bx - 3, by - 4, bw + 6, FACADE_BOTTOM - by + 4, C("#5a5a66"))
        cv.hl(bx - 3, by - 4, bw + 6, C("#8a8a96"))
        if i == 0:
            # half-open: lit shop interior + car front
            op = 34
            cv.vgrad(bx, by + op, bw, FACADE_BOTTOM - by - op, [C("#ffe0a0"), C("#e0a060")], em=1)
            cv.rect(bx, FACADE_BOTTOM - 6, bw, 6, C("#8a6a4a"), em=1)
            cx = bx + bw // 2
            car = C("#3a6ac0")
            cv.rect(cx - 30, FACADE_BOTTOM - 26, 60, 18, car, em=1)
            cv.rect(cx - 22, FACADE_BOTTOM - 34, 44, 9, dk(car, 0.15), em=1)
            cv.rect(cx - 19, FACADE_BOTTOM - 32, 38, 6, C("#bfe0f0"), em=1)
            cv.rect(cx - 28, FACADE_BOTTOM - 18, 8, 4, C("#fff0b0"), em=1)
            cv.rect(cx + 20, FACADE_BOTTOM - 18, 8, 4, C("#fff0b0"), em=1)
            cv.rect(cx - 12, FACADE_BOTTOM - 18, 24, 5, C("#2a2a32"), em=1)
            cv.rect(cx - 30, FACADE_BOTTOM - 10, 60, 3, P["steel_l"], em=1)
            cv.rect(cx - 28, FACADE_BOTTOM - 7, 9, 7, C("#18181e"), em=1)
            cv.rect(cx + 19, FACADE_BOTTOM - 7, 9, 7, C("#18181e"), em=1)
            # tools on the back wall
            for tx in range(bx + 4, bx + bw - 4, 7):
                cv.vl(tx, by + op + 3, rng.randrange(4, 9), C("#7a5a3a"), em=1)
            tex_corrugated(cv, bx, by, bw, op, C("#c8c4b8"), pitch=3)
            cv.hl(bx, by + op, bw, C("#4a4a56"))
            R.lights.append((cx, FACADE_BOTTOM - 10, C("#ffd890"), bw // 2 + 10, 0.6))
            R.refl.append((bx, bx + bw, by + op, C("#ffd890"), 0.4))
        else:
            tex_corrugated(cv, bx, by, bw, FACADE_BOTTOM - by, C("#c8c4b8"), pitch=3)
            for yy in range(by + 8, FACADE_BOTTOM, 10):
                cv.hl(bx, yy, bw, C("#9a968a"))
            cv.rect(bx + bw // 2 - 4, FACADE_BOTTOM - 8, 8, 3, C("#4a4a56"))
            # dent + oil stain
            cv.ellipse(bx + 10, by + 22, bx + 18, by + 28, C("#a8a498"))
            cv.dither_blend(bx + bw - 30, FACADE_BOTTOM - 20, 20, 20, C("#5a4a3a"), 0.3)
        # painted bay number
        cv.text(bx + 3, by - 13, str(i + 1), C("#b02e34"), 1, bold=True)
    # hanging SERVICE sign + tyre
    hx = x0 + w - 26
    cv.hl(hx - 6, 104, 16, C("#2a2a32"))
    cv.vl(hx - 4, 104, 4, C("#2a2a32"))
    cv.vl(hx + 7, 104, 4, C("#2a2a32"))
    signboard(cv, hx - 8, 108, 20, 9, None, C("#e0b040"), INK, border=C("#7a5a20"))
    cv.ellipse(hx - 4, 110, hx + 7, 115, C("#3a3a46"))
    cv.ellipse(hx - 1, 111, hx + 4, 114, C("#e0b040"))
    # oil-can logos (abstract shapes)
    for k, cx in enumerate((x0 + 30, x0 + w - 60)):
        cv.rect(cx, 106, 16, 16, [P["teal"], P["red"]][k])
        cv.ellipse(cx + 3, 109, cx + 12, 118, P["white"])
        cv.ellipse(cx + 5, 111, cx + 10, 116, [P["teal"], P["red"]][k])
    R.accents[x0] = P["red"]


@facade("rec_center")
def f_rec_center(R, x0, w, f):
    cv = R.cv
    rng = R.rng("rec", x0)
    top = 46
    roof_clear(cv, x0, w, top - 14)
    b = BRICKS[2]
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=b[0], shadow=b[1], hi=b[2], seed=seed_of(R.id, x0),
              weather=0.4)
    stone = C("#d8ccb0")
    # pediment parapet with flagpole
    cv.rect(x0, top - 6, w, 6, stone)
    cv.hl(x0, top - 6, w, lt(stone, 0.3))
    cx = x0 + w // 2
    cv.poly([(cx - 50, top - 6), (cx, top - 22), (cx + 50, top - 6)], stone)
    cv.poly([(cx - 42, top - 7), (cx, top - 18), (cx + 42, top - 7)], dk(stone, 0.15))
    cv.ellipse(cx - 5, top - 16, cx + 5, top - 8, P["red"])
    cv.ellipse(cx - 3, top - 14, cx + 3, top - 10, P["white"])
    fx = x0 + 18
    cv.vl(fx, 0, top, C("#c8c8d0"))
    cv.rect(fx + 1, 4, 18, 11, C("#3a6ac0"))
    cv.rect(fx + 1, 9, 18, 2, P["white"])
    cv.rect(fx + 7, 4, 2, 11, P["white"])
    # pilasters
    for px_ in (x0 + 2, x0 + w - 10):
        cv.rect(px_, top, 8, FACADE_BOTTOM - top, stone)
        cv.vl(px_ + 7, top, FACADE_BOTTOM - top, dk(stone, 0.3))
    # glass-block windows upper floor
    for k in range(4):
        wx = x0 + 22 + k * (w - 44) // 4 + 6
        ww = (w - 44) // 4 - 12
        cv.rect(wx - 2, top + 16, ww + 4, 34, stone)
        for gy in range(top + 18, top + 48, 5):
            for gx in range(wx, wx + ww - 1, 5):
                lit = rng.random() < 0.6
                c = C("#d8f0f0") if lit else C("#9ab8c0")
                cv.rect(gx, gy, 4, 4, c, em=1 if lit else 0)
                cv.px(gx, gy, P["white"], em=1 if lit else 0)
    # sign band
    s = f.get("sign", "REC CENTER")
    signboard(cv, x0 + 16, 104, w - 32, 20, s, C("#22305a"), C("#f0c040"), border=C("#141c38"))
    # entrance surround
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else cx
    cv.rect(dx - 30, 140, 60, FACADE_BOTTOM - 140, stone)
    cv.hl(dx - 30, 140, 60, lt(stone, 0.3))
    cv.rect(dx - 26, 144, 52, FACADE_BOTTOM - 144, dk(stone, 0.12))
    # mural (boxing glove + stars) on the left, posters on the right
    mx = x0 + 20
    mw = dx - 40 - mx
    if mw > 40:
        cv.rect(mx, 134, mw, 66, C("#e8d8b0"))
        cv.rect(mx + 2, 136, mw - 4, 62, C("#3a9a9a"))
        gx, gy = mx + mw // 2 - 12, 146
        cv.ellipse(gx, gy, gx + 24, gy + 22, INK)
        cv.ellipse(gx + 1, gy + 1, gx + 23, gy + 21, P["red"])
        cv.ellipse(gx + 4, gy + 3, gx + 12, gy + 9, lt(P["red"], 0.4))
        cv.rect(gx + 4, gy + 20, 16, 10, INK)
        cv.rect(gx + 5, gy + 21, 14, 8, P["white"])
        cv.ellipse(gx - 4, gy + 6, gx + 6, gy + 16, INK)
        cv.ellipse(gx - 3, gy + 7, gx + 5, gy + 15, P["red"])
        for sx, sy in ((mx + 8, 142), (mx + mw - 12, 150), (mx + 10, 182), (mx + mw - 14, 186)):
            for ddx, ddy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                cv.px(sx + ddx, sy + ddy, P["yellow"])
    px0 = dx + 40
    k = 0
    while px0 + 20 < x0 + w - 14:
        poster(cv, px0, 146 + (k % 2) * 6, 20, 28, rng)
        px0 += 28
        k += 1
    base_plinth(cv, x0, w, c=stone, h=5)
    R.accents[x0] = P["red"]


@facade("tunnel_arch")
def f_tunnel_arch(R, x0, w, f):
    cv = R.cv
    rng = R.rng("tunnel", x0)
    top = 66
    roof_clear(cv, x0, w, top - 12)
    # embankment top: grass + bushes
    cv.rect(x0, top - 10, w, 12, C("#4a6a3a"))
    for xx in range(x0, x0 + w, 2):
        hh = rng.randrange(0, 5)
        cv.vl(xx, top - 10 - hh, hh, rng.choice([C("#4a6a3a"), C("#5a7a42"), C("#3a5a32")]))
    for _ in range(w // 30):
        bx = rng.randrange(x0, x0 + w - 16)
        cv.ellipse(bx, top - 22, bx + rng.randrange(12, 22), top - 6, C("#3a5a32"))
        cv.ellipse(bx + 3, top - 20, bx + 10, top - 12, C("#5a7a42"))
    # retaining wall of dressed stone
    tex_stone(cv, x0, top, w, FACADE_BOTTOM - top, C("#8a8274"), seed=seed_of(R.id, x0))
    cv.blend(x0, top, w, FACADE_BOTTOM - top, C("#3a3040"), 0.15)
    # coping
    cv.rect(x0, top, w, 5, C("#a89c88"))
    cv.hl(x0, top, w, C("#c8bca8"))
    cv.hl(x0, top + 4, w, C("#5a5248"))
    # buttresses at both ends
    for bx in (x0, x0 + w - 14):
        cv.rect(bx, top + 5, 14, FACADE_BOTTOM - top - 5, C("#7a7266"))
        cv.vl(bx + 13, top + 5, FACADE_BOTTOM - top - 5, C("#4a443e"))
        cv.vl(bx, top + 5, FACADE_BOTTOM - top - 5, C("#9a9284"))
    # sign plate
    s = f.get("sign", "TUNNEL")
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else x0 + w // 2
    sw = text_w(s, 1, True) + 12
    signboard(cv, dx - sw // 2, top + 22, sw, 13, s, C("#2a2a32"), C("#e8d8b0"), border=C("#5a5248"))
    # ivy
    for _ in range(3):
        ix = rng.randrange(x0 + 16, x0 + w - 16)
        ln = rng.randrange(20, 70)
        for k in range(ln):
            cv.px(ix + int(3 * math.sin(k / 5)), top + 5 + k, C("#3a5a32"))
            if k % 3 == 0:
                cv.px(ix + int(3 * math.sin(k / 5)) + 1, top + 5 + k, C("#5a7a42"))
    # warning sign
    wx = dx + 40
    if wx + 14 < x0 + w - 14:
        cv.poly([(wx, 150), (wx + 14, 150), (wx + 7, 138)], P["yellow"])
        cv.vl(wx + 7, 142, 5, INK)
        cv.px(wx + 7, 148, INK)
    # rails heading into the tunnel across the sidewalk
    for s_ in (-12, 10):
        cv.rect(dx + s_, FACADE_BOTTOM, 2, 30, P["steel"])
        cv.vl(dx + s_, FACADE_BOTTOM, 30, P["steel_l"])


@facade("graffiti_wall")
def f_graffiti_wall(R, x0, w, f):
    cv = R.cv
    rng = R.rng("graf", x0)
    top = 92
    roof_clear(cv, x0, w, top - 4)
    tex_concrete(cv, x0, top, w, FACADE_BOTTOM - top, C("#9a948a"), seed=seed_of(R.id, x0), panel=(64, 200))
    cv.rect(x0, top - 4, w, 5, C("#7a746a"))
    cv.hl(x0, top - 4, w, C("#b8b2a8"))
    # pieces
    xx = x0 + 8
    while xx < x0 + w - 60:
        pw = rng.randrange(70, 120)
        pw = min(pw, x0 + w - 8 - xx)
        if pw < 50:
            break
        ph = rng.randrange(34, 50)
        graffiti(cv, xx, rng.randrange(top + 14, FACADE_BOTTOM - ph - 12), pw, ph, rng)
        xx += pw + rng.randrange(6, 20)
    for _ in range(w // 50):
        tag_scribble(cv, rng.randrange(x0 + 4, x0 + w - 30), rng.randrange(top + 6, FACADE_BOTTOM - 10), rng)
    # weeds at the base
    for xx in range(x0, x0 + w, 2):
        if rng.random() < 0.4:
            hh = rng.randrange(2, 9)
            cv.vl(xx, FACADE_BOTTOM - hh, hh, rng.choice([P["green_d"], C("#5a7a3a"), C("#7a8a4a")]))
    # stains
    cv.dither_blend(x0, FACADE_BOTTOM - 20, w, 20, C("#5a5048"), 0.3)


@facade("fence_lot")
def f_fence_lot(R, x0, w, f):
    cv = R.cv
    rng = R.rng("fence", x0)
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    # stuff behind the fence: billboard frame, junk heap, weeds
    bx = x0 + w // 2 - 70
    for k in (bx + 20, bx + 116):
        cv.rect(k, 70, 4, FACADE_BOTTOM - 70, C("#4a3a32"))
        cv.vl(k, 70, FACADE_BOTTOM - 70, C("#6a5242"))
    cv.line(bx + 22, 120, bx + 118, 150, C("#4a3a32"))
    cv.rect(bx, 34, 140, 52, C("#3a3236"))
    cv.rect(bx + 3, 37, 134, 46, C("#d8cca8"))
    # peeling billboard: faded abstract ad
    cv.rect(bx + 3, 37, 134, 18, C("#c06a4a"))
    cv.ellipse(bx + 90, 44, bx + 126, 80, C("#e0b040"))
    cv.rect(bx + 10, 62, 60, 4, C("#8a7a6a"))
    cv.rect(bx + 10, 70, 44, 3, C("#8a7a6a"))
    for _ in range(40):
        px_ = rng.randrange(bx + 3, bx + 137)
        py_ = rng.randrange(37, 83)
        cv.rect(px_, py_, rng.randrange(2, 7), rng.randrange(2, 5), C("#a89c80"))
    cv.clear(bx + 100, 37, 37, 14)  # torn corner showing sky
    cv.rect(bx + 98, 37, 2, 14, C("#3a3236"))
    # junk heap left
    hx = x0 + 30
    for _ in range(26):
        jx = hx + rng.randrange(0, 110)
        jy = FACADE_BOTTOM - rng.randrange(4, 34) + int(abs(jx - hx - 55) * 0.4)
        c = rng.choice([C("#5a5a66"), C("#7a5a3a"), C("#3a3a46"), C("#8a4a3a"), C("#6a7280")])
        cv.rect(jx, jy, rng.randrange(6, 16), rng.randrange(3, 8), c)
    cv.ellipse(hx + 20, FACADE_BOTTOM - 28, hx + 36, FACADE_BOTTOM - 16, C("#24242e"))
    cv.ellipse(hx + 25, FACADE_BOTTOM - 25, hx + 31, FACADE_BOTTOM - 19, C("#4a4a56"))
    # weeds and grass strip
    cv.rect(x0, FACADE_BOTTOM - 8, w, 8, C("#5a6a3a"))
    for xx in range(x0, x0 + w):
        if rng.random() < 0.55:
            hh = rng.randrange(3, 16)
            cv.vl(xx, FACADE_BOTTOM - 8 - hh, hh, rng.choice([C("#4a6a3a"), C("#6a7a3a"), C("#3a5a32"),
                                                               C("#8a8a4a")]))
    # chain-link fence in front
    fy = 132
    chainlink(cv, x0, fy, w, FACADE_BOTTOM - fy, wire=C("#a8acb4"), post=C("#6a7078"), posts=60)
    for px_ in range(x0, x0 + w + 1, 60):
        cv.line(px_ + 1, fy - 3, px_ + 8, fy - 10, C("#6a7078"))
    barbed(cv, x0, fy - 11, w)
    # a sign zip-tied to the fence
    sx = x0 + w - 120
    cv.rect(sx, 160, 34, 18, C("#e8e4dc"))
    cv.rect(sx + 1, 161, 32, 4, P["red"])
    for yy in (168, 171, 174):
        cv.hl(sx + 3, yy, 28 - (yy % 5), C("#5a5a66"))


@facade("clubhouse_shed")
def f_clubhouse(R, x0, w, f):
    cv = R.cv
    rng = R.rng("club", x0)
    top = 100
    roof_clear(cv, x0, w, top - 16)
    # sloped roof
    cv.poly([(x0 + 4, top), (x0 + w - 4, top), (x0 + w - 12, top - 14), (x0 + 12, top - 14)], C("#5a3a32"))
    for xx in range(x0 + 12, x0 + w - 12, 4):
        cv.vl(xx, top - 13, 13, C("#6a4a3e"))
    cv.hl(x0 + 4, top - 1, w - 8, C("#3a2420"))
    tex_corrugated(cv, x0 + 6, top, w - 12, FACADE_BOTTOM - top, C("#8a3a30"), pitch=4, seed=x0, rust=0.35)
    # patches of different metal
    cv.rect(x0 + 40, 150, 30, 26, C("#6a7280"))
    tex_corrugated(cv, x0 + 40, 150, 30, 26, C("#6a7280"), pitch=4)
    for px_ in range(x0 + 41, x0 + 70, 6):
        cv.px(px_, 151, C("#2a2a32"))
        cv.px(px_, 174, C("#2a2a32"))
    # hand-painted sign board
    s = f.get("sign", "CLUB")
    sw = text_w(s, 2) + 18
    sx = x0 + (w - sw) // 2
    cv.rect(sx - 2, top - 30, sw + 4, 24, C("#2a1a14"))
    tex_planks_h(cv, sx, top - 28, sw, 20, C("#7a5030"), ph=5, seed=sx, joints=False)
    cv.text(sx + 9, top - 24, s, C("#e8e0d0"), 2, shadow=C("#3a1a10"))
    # drips from paint
    for k in range(4):
        cv.vl(sx + 12 + k * (sw - 24) // 3, top - 10, rng.randrange(2, 5), C("#e8e0d0"))
    # emblem: spiked collar ring (original)
    ex, ey = x0 + w - 56, 130
    cv.ellipse(ex - 14, ey - 14, ex + 14, ey + 14, INK)
    cv.ellipse(ex - 12, ey - 12, ex + 12, ey + 12, P["red"])
    cv.ellipse(ex - 7, ey - 7, ex + 7, ey + 7, INK)
    for k in range(8):
        a = k * math.pi / 4
        sx_, sy_ = ex + int(math.cos(a) * 10), ey + int(math.sin(a) * 10)
        cv.rect(sx_ - 1, sy_ - 1, 2, 2, P["steel_l"])
    cv.line(ex - 4, ey + 3, ex + 4, ey - 3, P["white"])
    # door (closed, chained) + window with dim light
    dxx = x0 + 30
    cv.rect(dxx - 2, 150, 28, FACADE_BOTTOM - 150, C("#2a1a14"))
    tex_planks_v(cv, dxx, 152, 24, FACADE_BOTTOM - 152, C("#6a4a30"), pw=6, seed=dxx)
    cv.line(dxx, 160, dxx + 24, 190, C("#5a5a66"))
    cv.rect(dxx + 10, 172, 5, 5, P["mustard_d"])
    wx = x0 + w // 2 + 10
    cv.rect(wx - 1, 140, 30, 22, C("#2a1a14"))
    cv.vgrad(wx, 141, 28, 20, [C("#ffb060"), C("#c06030")], em=1)
    cv.vl(wx + 14, 141, 20, C("#2a1a14"))
    cv.hl(wx, 151, 28, C("#2a1a14"))
    R.lights.append((wx + 14, 152, C("#ffa050"), 30, 0.5))
    # string of bulbs along the eave
    pts = cv.sag(x0 + 8, top + 2, x0 + w - 8, top + 2, 6, C("#2a2a32"))
    for i, (px_, py_) in enumerate(pts[::8]):
        col = [P["red"], P["n_yellow"], P["n_green"], P["n_cyan"]][i % 4]
        cv.rect(px_, py_ + 1, 2, 2, col, em=1)
    # tyre + oil drum fire
    cv.ellipse(x0 + w - 30, FACADE_BOTTOM - 14, x0 + w - 12, FACADE_BOTTOM - 2, C("#24242e"))
    cv.ellipse(x0 + w - 25, FACADE_BOTTOM - 11, x0 + w - 17, FACADE_BOTTOM - 5, C("#5a5a66"))


@facade("underpass")
def f_underpass(R, x0, w, f):
    cv = R.cv
    rng = R.rng("under", x0)
    roof_clear(cv, x0, w, 30)
    # deck beam
    cv.rect(x0, 30, w, 60, C("#8a867e"))
    tex_concrete(cv, x0, 30, w, 60, C("#8a867e"), seed=x0, panel=(48, 60))
    cv.rect(x0, 30, w, 6, C("#6a665e"))
    cv.hl(x0, 30, w, C("#b0aca2"))
    cv.rect(x0, 84, w, 6, C("#5a564e"))
    # railing on the overpass deck
    cv.hl(x0, 20, w, C("#5a5a66"))
    for xx in range(x0, x0 + w, 6):
        cv.vl(xx, 20, 10, C("#5a5a66"))
    # dark opening under
    cv.vgrad(x0, 90, w, FACADE_BOTTOM - 90, [C("#141218"), C("#221e28"), C("#2e2a34")])
    # far end light
    cv.rect(x0 + w // 2 - 20, 150, 40, FACADE_BOTTOM - 150, C("#5a5048"))
    cv.vgrad(x0 + w // 2 - 16, 156, 32, FACADE_BOTTOM - 156, [C("#c89a6a"), C("#8a6a5a")], em=1)
    # pillar
    cv.rect(x0, 90, 18, FACADE_BOTTOM - 90, C("#7a766e"))
    cv.vl(x0 + 17, 90, FACADE_BOTTOM - 90, C("#4a463e"))
    tag_scribble(cv, x0 + 2, 150, rng)
    # padlocked chain-link gate
    gx0 = x0 + 22
    chainlink(cv, gx0, 104, w - 26, FACADE_BOTTOM - 104, wire=C("#9aa0a8"), post=C("#5a6068"), posts=56)
    cv.rect(gx0 + (w - 26) // 2 - 1, 104, 3, FACADE_BOTTOM - 104, C("#5a6068"))
    cv.line(gx0 + (w - 26) // 2 - 12, 150, gx0 + (w - 26) // 2 + 12, 160, C("#7a7a86"))
    cv.line(gx0 + (w - 26) // 2 - 12, 160, gx0 + (w - 26) // 2 + 12, 150, C("#7a7a86"))
    cv.rect(gx0 + (w - 26) // 2 - 3, 156, 7, 8, P["mustard"])
    cv.rect(gx0 + (w - 26) // 2 - 2, 152, 5, 4, P["steel_l"])
    # drips/stains under the deck
    for _ in range(8):
        dx_ = rng.randrange(x0, x0 + w)
        cv.vl(dx_, 90, rng.randrange(3, 12), C("#3a3632"))



# ============================================================================
# FACADES - Canal Market
# ============================================================================
CANAL_HOUSES = [C("#d8a868"), C("#c86a4a"), C("#e8d8b8"), C("#7aa0a8"), C("#a87a9a"), C("#c8b060"),
                C("#9a5a3a"), C("#e8c8a0")]


def gable_house(cv, R, x, w, base_y, top, col, rng, scale=1.0, lit_p=0.2, far=False):
    """Narrow canal-house with a gable/stepped top. base_y = ground line of the house."""
    trim = lt(col, 0.45)
    sh = dk(col, 0.25)
    cv.rect(x, top, w, base_y - top, col)
    cv.vl(x + w - 1, top, base_y - top, sh)
    kind = rng.random()
    cx = x + w // 2
    if kind < 0.4:      # pointed gable
        gh = w // 2
        cv.poly([(x - 1, top), (cx, top - gh), (x + w, top)], col)
        cv.line(x - 1, top, cx, top - gh, trim)
        cv.line(cx, top - gh, x + w, top, sh)
    elif kind < 0.75:   # stepped gable
        steps = 3
        sw = w // (steps * 2 + 1)
        for k in range(steps):
            cv.rect(x + sw * (k + 1), top - (k + 1) * 4, w - 2 * sw * (k + 1), 4, col)
            cv.hl(x + sw * (k + 1), top - (k + 1) * 4, w - 2 * sw * (k + 1), trim)
    else:               # bell gable
        cv.ellipse(x + 2, top - w // 2, x + w - 3, top + w // 3, col)
        cv.rect(cx - 1, top - w // 2 - 3, 2, 3, trim)
    # windows grid
    ww = max(4, int(5 * scale))
    wh = max(5, int(8 * scale))
    rows = max(1, int((base_y - top - 10) / (wh + 6)))
    cols = max(1, (w - 4) // (ww + 4))
    for r in range(rows):
        for c_ in range(cols):
            wx = x + 3 + c_ * ((w - 6) // cols) + ((w - 6) // cols - ww) // 2
            wy = top + 5 + r * (wh + 6)
            if wy + wh > base_y - 3:
                continue
            if rng.random() < lit_p:
                cv.rect(wx, wy, ww, wh, LIT[1], em=1)
                cv.hl(wx, wy, ww, LIT[0], em=1)
            else:
                g = R.T["glass"]
                cv.rect(wx, wy, ww, wh, g[1] if not far else mix(g[1], col, 0.3))
                cv.hl(wx, wy, ww, g[0])
            cv.hl(wx - 1, wy + wh, ww + 2, trim)
    if rng.random() < 0.5 and w > 20:
        cv.rect(cx - 3, base_y - 10, 6, 10, dk(col, 0.45))


def canal_far_bank(cv, R, x0, w, rng, water_y=150, var=0):
    """Far-bank houses along the water line + their reflections."""
    xx = x0 - rng.randrange(0, 20)
    while xx < x0 + w:
        hw = rng.randrange(22, 36)
        top = water_y - rng.randrange(44, 76)
        col = mix(rng.choice(CANAL_HOUSES), C("#c8e0f0"), 0.18)
        if var == 1 and rng.random() < 0.35:
            # warehouse block
            hw = rng.randrange(50, 80)
            top = water_y - rng.randrange(36, 50)
            col = mix(C("#9a5a40"), C("#c8e0f0"), 0.2)
            cv.rect(xx, top, hw, water_y - top, col)
            cv.poly([(xx - 1, top), (xx + hw // 2, top - 12), (xx + hw, top)], dk(col, 0.1))
            for k in range(xx + 6, xx + hw - 8, 12):
                cv.rect(k, top + 8, 6, 9, dk(col, 0.35))
                cv.rect(k, top + 22, 6, 9, dk(col, 0.35))
            cv.rect(xx + hw // 2 - 6, water_y - 14, 12, 14, dk(col, 0.4))
        else:
            gable_house(cv, R, xx, hw, water_y, top, col, rng, far=True)
        xx += hw + rng.randrange(0, 3)
    # quay wall
    cv.rect(x0, water_y - 3, w, 4, C("#a8a090"))
    cv.hl(x0, water_y - 3, w, C("#d0c8b8"))
    cv.hl(x0, water_y + 1, w, C("#6a6458"))


def mirror_into_water(cv, x0, w, src_y0, src_y1, dst_y, h, tint, amt=0.55):
    """Reflect rows [src_y0, src_y1) upside-down into water starting at dst_y with ripple breaks."""
    x0c, _, x1c, _ = cv._clip(x0, 0, x0 + w, 1)
    if x1c <= x0c:
        return
    for k in range(h):
        sy = src_y1 - 1 - int(k * 1.15)
        if sy < src_y0:
            break
        dy = dst_y + k
        if dy >= cv.h:
            break
        if k % 4 == 3:
            continue
        shift = int(round(math.sin(k * 0.9) * (1 + k / 12)))
        src = cv.a[sy, x0c:x1c, :3].astype(np.float32)
        srca = cv.a[sy, x0c:x1c, 3]
        src = np.roll(src, shift, axis=0)
        dst = cv.a[dy, x0c:x1c, :3].astype(np.float32)
        m = (np.roll(srca, shift) > 0)[:, None]
        t = amt * (1 - k / max(1, h)) ** 0.8
        out = dst * (1 - t) + (src * 0.6 + np.array(tint, np.float32) * 0.4) * t
        cv.a[dy, x0c:x1c, :3] = np.where(m, out, dst).astype(np.uint8)


def canal_water(cv, R, x0, w, y0, y1, seed):
    water(cv, R, x0, y0, w, y1 - y0, deep=C("#2a6a8a"), mid=C("#4a90b0"), light=C("#9ad0e0"), seed=seed)


def railing_iron(cv, x0, w, y_top, y_bot, c=None, step=10):
    c = c or C("#2e3440")
    hi = lt(c, 0.35)
    cv.rect(x0, y_top, w, 2, c)
    cv.hl(x0, y_top, w, hi)
    cv.hl(x0, y_top + (y_bot - y_top) // 2, w, c)
    for xx in range(x0, x0 + w, step):
        cv.vl(xx, y_top, y_bot - y_top, c)
    for xx in range(x0, x0 + w, step * 4):
        cv.rect(xx - 1, y_top - 2, 3, y_bot - y_top + 2, c)
        cv.px(xx, y_top - 3, hi)


@facade("canal_rail")
def f_canal_rail(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("canal", x0)
    water_y = 150
    roof_clear(cv, x0, w, water_y)
    canal_far_bank(cv, R, x0, w, rng, water_y, var)
    canal_water(cv, R, x0, w, water_y + 1, FACADE_BOTTOM, seed=f"{R.id}{x0}")
    mirror_into_water(cv, x0, w, water_y - 70, water_y - 2, water_y + 2, 50, C("#3a7a9a"))
    # boats on the canal
    for _ in range(max(1, w // 300)):
        bx = rng.randrange(x0 + 20, x0 + w - 90)
        by = water_y + rng.randrange(14, 26)
        if var == 1:
            col = rng.choice([C("#2a5a3a"), C("#7a2030"), C("#22305a")])
            cv.rect(bx, by - 10, 80, 10, col)
            cv.hl(bx, by - 10, 80, lt(col, 0.3))
            cv.rect(bx + 10, by - 18, 54, 8, C("#e8d8b0"))
            for k in range(bx + 14, bx + 60, 10):
                cv.rect(k, by - 16, 5, 4, C("#5a6a7a"))
            cv.rect(bx, by, 80, 2, dk(col, 0.4))
            cv.hl(bx - 2, by + 2, 84, C("#9ad0e0"))
        else:
            col = rng.choice([C("#c03a3a"), C("#e0b040"), C("#3a6ac0"), C("#e8e4dc")])
            cv.poly([(bx, by - 8), (bx + 40, by - 8), (bx + 34, by), (bx + 5, by)], col)
            cv.hl(bx, by - 8, 40, lt(col, 0.4))
            cv.hl(bx + 3, by - 6, 34, dk(col, 0.4))
            cv.hl(bx + 2, by + 1, 36, C("#9ad0e0"))
    # quay coping + iron railing
    cv.rect(x0, FACADE_BOTTOM - 6, w, 6, C("#a8a090"))
    cv.hl(x0, FACADE_BOTTOM - 6, w, C("#d0c8b8"))
    cv.hl(x0, FACADE_BOTTOM - 1, w, C("#6a6458"))
    railing_iron(cv, x0, w, FACADE_BOTTOM - 26, FACADE_BOTTOM - 6)
    # bunting overhead from lamp to lamp
    for bx in range(x0, x0 + w, 160):
        pts = cv.sag(bx, 96, bx + 160, 96, 12, C("#e8e4dc"))
        for i, (px_, py_) in enumerate(pts[4::8]):
            col = [P["red"], P["yellow"], P["blue"], P["green"], P["white"]][i % 5]
            cv.poly([(px_ - 2, py_ + 1), (px_ + 3, py_ + 1), (px_, py_ + 6)], col)


@facade("footbridge")
def f_footbridge(R, x0, w, f):
    cv = R.cv
    rng = R.rng("fb", x0)
    water_y = 150
    roof_clear(cv, x0, w, water_y)
    canal_far_bank(cv, R, x0, w, rng, water_y, 0)
    canal_water(cv, R, x0, w, water_y + 1, FACADE_BOTTOM, seed=f"{R.id}{x0}")
    mirror_into_water(cv, x0, w, water_y - 70, water_y - 2, water_y + 2, 50, C("#3a7a9a"))
    # side canal opening: darker water channel running toward the viewer
    cv.blend(x0, FACADE_BOTTOM - 20, w, 20, C("#1a4a6a"), 0.35)
    # ornamental iron arch posts at both bridge ends + overhead arch with plaque
    iron = C("#2e3440")
    for px_ in (x0 + 2, x0 + w - 8):
        cv.rect(px_, 120, 6, 132 - 120 + FACADE_BOTTOM - 120, iron)
        cv.vl(px_, 120, FACADE_BOTTOM + 38 - 120, lt(iron, 0.35))
        cv.rect(px_ - 2, 116, 10, 5, iron)
        cv.rect(px_ - 1, 108, 8, 8, C("#3a4250"))
        cv.rect(px_ + 1, 110, 4, 5, P["lamp"], em=1)
        R.lights.append((px_ + 3, 112, P["lamp"], 18, 0.5))
    cx = x0 + w // 2
    for k in range(w - 8):
        t = k / (w - 9)
        yy = int(124 - math.sin(t * math.pi) * 26)
        cv.rect(x0 + 4 + k, yy, 1, 3, iron)
        if k % 12 == 0:
            cv.vl(x0 + 4 + k, yy, 124 - yy + 2, iron)
    cv.hl(x0 + 4, 124, w - 8, iron)
    # bunting along the arch
    for k in range(6, w - 12, 10):
        t = k / (w - 9)
        yy = int(127 - math.sin(t * math.pi) * 26)
        col = [P["red"], P["yellow"], P["blue"], P["green"]][(k // 10) % 4]
        cv.poly([(x0 + 4 + k - 2, yy), (x0 + 4 + k + 3, yy), (x0 + 4 + k, yy + 5)], col)


@facade("fish_hall")
def f_fish_hall(R, x0, w, f):
    cv = R.cv
    rng = R.rng("fish", x0)
    top = 52
    roof_clear(cv, x0, w, 0)
    cx = x0 + w // 2
    # roof
    cv.poly([(x0, top), (x0 + 30, top - 26), (x0 + w - 30, top - 26), (x0 + w, top)], C("#5a6a7a"))
    for xx in range(x0 + 6, x0 + w - 6, 5):
        cv.vl(xx, top - 24, 24, C("#6a7a8a"))
    cv.hl(x0 + 30, top - 26, w - 60, C("#8a9aaa"))
    # gable front centre with clock + fish weather vane
    cv.poly([(cx - 70, top), (cx, top - 46), (cx + 70, top)], C("#b05a40"))
    cv.line(cx - 70, top, cx, top - 46, C("#e8d8b0"))
    cv.line(cx, top - 46, cx + 70, top, C("#e8d8b0"))
    cv.ellipse(cx - 9, top - 30, cx + 9, top - 12, C("#e8d8b0"))
    cv.ellipse(cx - 7, top - 28, cx + 7, top - 14, C("#f8f4e8"))
    cv.line(cx, top - 21, cx, top - 26, INK)
    cv.line(cx, top - 21, cx + 4, top - 21, INK)
    cv.vl(cx, top - 62, 16, C("#3a3a46"))
    cv.ellipse(cx - 8, top - 64, cx + 6, top - 59, C("#c8a040"))
    cv.poly([(cx + 6, top - 62), (cx + 11, top - 66), (cx + 11, top - 57)], C("#c8a040"))
    cv.px(cx - 5, top - 62, INK)
    # walls
    b = BRICKS[2]
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=b[0], shadow=b[1], hi=b[2], seed=seed_of(R.id, x0))
    cv.rect(x0, top, w, 4, C("#e8d8b0"))
    # tall arched windows
    n = max(4, w // 70)
    for k in range(n):
        wx = x0 + int((k + 0.5) * w / n) - 12
        window(cv, R, wx, top + 26, 24, 36, lit=False, frame=C("#e8d8b0"), arch=True, bars=True)
        for yy in range(top + 30, top + 60, 8):
            cv.hl(wx + 1, yy, 22, C("#e8d8b0"))
    # sign banner
    s = f.get("sign", "FISH HALL")
    signboard(cv, x0 + 30, 110, w - 60, 22, s, C("#1e4a6a"), C("#f8f4e8"), border=C("#0e2a40"))
    # open market bays with ice tables
    by = 144
    cv.rect(x0 + 8, by, w - 16, FACADE_BOTTOM - by, C("#4a3a34"))
    awning(cv, x0 + 4, by - 6, w - 8, 12, C("#1e6aa0"), P["white"], stripe=8)
    for k in range(3):
        bx = x0 + 16 + k * (w - 32) // 3
        bw = (w - 32) // 3 - 12
        cv.vgrad(bx, by + 8, bw, FACADE_BOTTOM - by - 8, [C("#c8d8e0"), C("#8a9aa8")])
        # ice table with fish
        ty = FACADE_BOTTOM - 22
        cv.rect(bx + 2, ty, bw - 4, 6, C("#e8f4f8"))
        cv.rect(bx + 2, ty + 6, bw - 4, 16, C("#6a4a30"))
        cv.hl(bx + 2, ty + 6, bw - 4, C("#8a6a4a"))
        for fx in range(bx + 4, bx + bw - 10, 8):
            fc = rng.choice([C("#9aa8b8"), C("#c87a5a"), C("#c8b8a8"), C("#7a8aa0")])
            cv.ellipse(fx, ty - 2, fx + 7, ty + 1, fc)
            cv.px(fx + 1, ty - 1, INK)
        # hanging scale and lights
        cv.vl(bx + bw // 2, by + 8, 10, C("#3a3a46"))
        cv.rect(bx + bw // 2 - 4, by + 18, 9, 3, P["steel_l"])
        cv.rect(bx + 10, by + 10, 10, 2, (255, 255, 240), em=1)
    for k in range(4):
        pxx = x0 + 8 + k * (w - 22) // 3
        cv.rect(pxx, by, 6, FACADE_BOTTOM - by, C("#e8d8b0"))
        cv.vl(pxx + 5, by, FACADE_BOTTOM - by, C("#a89c88"))
    # gulls
    for _ in range(3):
        gx, gy = rng.randrange(x0 + 10, x0 + w - 10), rng.randrange(4, 30)
        cv.line(gx - 3, gy, gx, gy + 2, P["white"])
        cv.line(gx, gy + 2, gx + 3, gy, P["white"])


@facade("pier")
def f_pier(R, x0, w, f):
    cv = R.cv
    rng = R.rng("pier", x0)
    hz = 118
    roof_clear(cv, x0, w, hz)
    # far shore silhouette on the horizon
    for xx in range(x0, x0 + w):
        hh = int(6 + 4 * math.sin(xx * 0.02) + 3 * math.sin(xx * 0.07))
        cv.vl(xx, hz - hh, hh, C("#8aa0a8"))
    for _ in range(4):
        bx = rng.randrange(x0, x0 + w - 20)
        cv.rect(bx, hz - 16, rng.randrange(6, 16), 10, C("#7a909a"))
    water(cv, R, x0, hz, w, FACADE_BOTTOM - hz, deep=C("#2a6a8a"), mid=C("#5aa0c0"), light=C("#b0e0f0"),
          seed=f"{R.id}pier")
    # long pier jutting out with posts
    py = 170
    cv.rect(x0, py, w, 6, C("#9a7650"))
    cv.hl(x0, py, w, C("#c8a070"))
    cv.hl(x0, py + 5, w, C("#5e3a1e"))
    for xx in range(x0 + 8, x0 + w, 30):
        cv.rect(xx, py + 6, 5, 30, C("#5e3a1e"))
        cv.vl(xx, py + 6, 30, C("#8a5a34"))
        cv.rect(xx, py - 14, 4, 14, C("#6a4a2e"))
        cv.hl(xx - 1, py - 15, 6, C("#9a7650"))
        cv.hl(xx - 2, py + 34, 9, C("#b0e0f0"))
    cv.hl(x0, py - 10, w, C("#7a5a3a"))
    # moored boats in front of / beside the pier
    bxs = [x0 + 40, x0 + w // 2 - 20, x0 + w - 170]
    for i, bx in enumerate(bxs):
        if bx + 120 > x0 + w:
            continue
        by = 200
        hull = [C("#e8e4dc"), C("#c03a3a"), C("#22605e")][i % 3]
        trimc = [P["blue"], P["white"], P["mustard"]][i % 3]
        cv.poly([(bx, by - 16), (bx + 120, by - 18), (bx + 110, by), (bx + 10, by)], hull)
        cv.hl(bx + 2, by - 15, 116, trimc)
        cv.hl(bx + 8, by - 3, 104, dk(hull, 0.35))
        cv.rect(bx + 60, by - 36, 36, 20, C("#e8e4dc"))
        cv.rect(bx + 58, by - 38, 40, 3, trimc)
        for k in range(bx + 64, bx + 94, 9):
            cv.rect(k, by - 31, 6, 6, C("#5a8aa0"))
        cv.vl(bx + 30, by - 60, 44, C("#5a4a3a"))
        cv.line(bx + 30, by - 60, bx + 60, by - 38, C("#3a3a46"))
        cv.line(bx + 30, by - 58, bx + 4, by - 17, C("#3a3a46"))
        cv.ellipse(bx + 14, by - 22, bx + 20, by - 16, P["orange"])
        cv.hl(bx + 6, by + 1, 108, C("#b0e0f0"))
        cv.line(bx + 110, by - 10, bx + 130, py + 4, C("#c8b898"))   # mooring line
    # quay edge + bollards
    cv.rect(x0, FACADE_BOTTOM - 8, w, 8, C("#a8a090"))
    cv.hl(x0, FACADE_BOTTOM - 8, w, C("#d0c8b8"))
    cv.hl(x0, FACADE_BOTTOM - 1, w, C("#6a6458"))
    for xx in range(x0 + 20, x0 + w, 100):
        cv.rect(xx, FACADE_BOTTOM - 14, 8, 6, C("#3a3a46"))
        cv.rect(xx - 1, FACADE_BOTTOM - 15, 10, 2, C("#5a5a66"))
    # buoys + gulls
    for _ in range(4):
        gx, gy = rng.randrange(x0 + 10, x0 + w - 10), rng.randrange(10, 90)
        cv.line(gx - 3, gy, gx, gy + 2, P["white"])
        cv.line(gx, gy + 2, gx + 3, gy, P["white"])


@facade("warehouse_small")
def f_warehouse_small(R, x0, w, f):
    cv = R.cv
    rng = R.rng("whs", x0)
    var = f.get("variant", 0)
    if var == 1 and f.get("sign"):
        return drawbridge_house(R, x0, w, f)
    top = 64
    roof_clear(cv, x0, w, 0)
    cx = x0 + w // 2
    col = C("#9a6a48")
    # gabled timber/brick front
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=C("#8a4a38"), seed=seed_of(R.id, x0), weather=0.5)
    cv.poly([(x0 - 1, top), (cx, top - 40), (x0 + w, top)], C("#7a4a34"))
    tex_planks_v(cv, x0 + 20, top - 30, w - 40, 30, col, pw=6, seed=x0)
    cv.poly([(x0 - 1, top), (cx, top - 40), (x0 - 1, top - 40)], (0, 0, 0))
    cv.clear(x0, top - 41, cx - x0, 1)
    # redo gable cleanly: clear outside triangle
    for yy in range(top - 41, top):
        half = int((yy - (top - 40)) * (w / 2) / 40)
        cv.clear(x0, yy, max(0, cx - half - x0), 1)
        cv.clear(cx + half + 1, yy, max(0, x0 + w - (cx + half + 1)), 1)
    for k in range(41):
        half = int(k * (w / 2) / 40)
        yy = top - 40 + k
        cv.rect(cx - half - 2, yy, 3, 1, C("#e8d8b0"))
        cv.rect(cx + half, yy, 3, 1, C("#c8b898"))
    # hoist beam + pulley
    cv.rect(cx - 2, top - 34, 4, 6, C("#3a2a22"))
    cv.rect(cx - 1, top - 30, 18, 3, C("#5e3a1e"))
    cv.vl(cx + 14, top - 27, 40, C("#c8b898"))
    cv.rect(cx + 11, top + 12, 7, 6, C("#5e3a1e"))
    # loft door
    cv.rect(cx - 12, top - 4, 24, 30, C("#3a2a22"))
    tex_planks_v(cv, cx - 10, top - 2, 20, 28, C("#7a3a2a"), pw=5, seed=cx)
    cv.line(cx - 10, top - 2, cx + 9, top + 25, C("#5a2a1e"))
    # big ground door + windows
    cv.rect(cx - 30, 150, 60, FACADE_BOTTOM - 150, C("#3a2a22"))
    tex_planks_v(cv, cx - 28, 152, 56, FACADE_BOTTOM - 152, C("#7a3a2a"), pw=7, seed=cx + 1)
    cv.vl(cx, 152, FACADE_BOTTOM - 152, C("#3a2a22"))
    for k in (cx - 28, cx + 1):
        cv.line(k, 152, k + 27, FACADE_BOTTOM - 1, C("#5a2a1e"))
    for wx in (x0 + 14, x0 + w - 32):
        if x0 + 4 < wx < x0 + w - 20:
            window(cv, R, wx, 100, 18, 24, lit=False, frame=C("#e8d8b0"), lintel=C("#c8b898"))
            window(cv, R, wx, 160, 18, 24, lit=rng.random() < 0.3, frame=C("#e8d8b0"), lintel=C("#c8b898"),
                   rng=rng)
    if f.get("sign"):
        signboard(cv, cx - 50, 128, 100, 16, f["sign"], C("#e8d8b0"), C("#7a2030"))
    base_plinth(cv, x0, w)


def drawbridge_house(R, x0, w, f):
    cv = R.cv
    rng = R.rng("draw", x0)
    roof_clear(cv, x0, w, 0)
    # water channel behind the bridge machinery
    water_y = 150
    canal_water(cv, R, x0, w, water_y, FACADE_BOTTOM, seed=f"{R.id}draw")
    cv.rect(x0, water_y - 3, w, 4, C("#a8a090"))
    # tender's house (left)
    hx, hw = x0 + 10, 110
    top = 70
    tex_brick(cv, hx, top, hw, FACADE_BOTTOM - top, base=C("#9a5040"), seed=seed_of(R.id, "dh"))
    cv.poly([(hx - 6, top), (hx + hw // 2, top - 30), (hx + hw + 6, top)], C("#3a4a5a"))
    cv.line(hx - 6, top, hx + hw // 2, top - 30, C("#6a7a8a"))
    cv.rect(hx + hw // 2 - 4, top - 44, 8, 16, C("#3a4a5a"))
    cv.rect(hx + hw // 2 - 6, top - 46, 12, 3, C("#2a3440"))
    # wraparound control windows
    cv.rect(hx + 6, top + 10, hw - 12, 30, C("#e8d8b0"))
    for k in range(4):
        window(cv, R, hx + 9 + k * (hw - 18) // 4, top + 12, (hw - 18) // 4 - 2, 26, lit=k == 1,
               frame=C("#e8d8b0"), sill=False, rng=rng)
    signboard(cv, hx + 8, top + 48, hw - 16, 16, f.get("sign", ""), C("#e8d8b0"), C("#7a2030"))
    deco_door(cv, hx + hw // 2 - 9, FACADE_BOTTOM, 18, 34, C("#22605e"), frame=C("#e8d8b0"))
    # raised bascule leaf (right): steel truss pointing skyward
    bx = x0 + w - 60
    by = FACADE_BOTTOM - 20
    steel = C("#6a7280")
    ang = math.radians(76)
    L = 190
    ex, ey = bx + int(math.cos(ang) * L) - 40, by - int(math.sin(ang) * L)
    for off in (0, 18):
        cv.line(bx - 40 + off, by, ex + off, ey, steel)
        cv.line(bx - 39 + off, by, ex + 1 + off, ey, lt(steel, 0.25))
    for k in range(12):
        t = k / 11
        ax_ = int(bx - 40 + (ex - bx + 40) * t)
        ay_ = int(by + (ey - by) * t)
        cv.line(ax_, ay_, ax_ + 18, ay_, steel)
        if k < 11:
            t2 = (k + 1) / 11
            cv.line(ax_, ay_, int(bx - 40 + (ex - bx + 40) * t2) + 18, int(by + (ey - by) * t2), dk(steel, 0.2))
    # red/white stripes on leaf tip + warning light
    for k in range(4):
        t = 0.85 + k * 0.04
        ax_ = int(bx - 40 + (ex - bx + 40) * t)
        ay_ = int(by + (ey - by) * t)
        cv.rect(ax_, ay_, 19, 3, P["red"] if k % 2 == 0 else P["white"])
    cv.rect(ex + 7, ey - 6, 5, 5, C("#ff4a3a"), em=1)
    R.lights.append((ex + 9, ey - 4, C("#ff4a3a"), 16, 0.6))
    # counterweight + gear housing
    cv.rect(bx - 54, by - 26, 40, 30, C("#4a5260"))
    cv.hl(bx - 54, by - 26, 40, C("#7a8290"))
    cv.ellipse(bx - 44, by - 20, bx - 24, by, C("#3a4050"))
    cv.ellipse(bx - 38, by - 14, bx - 30, by - 6, C("#9aa2b0"))
    # barrier arm with stop sign + signal
    cv.rect(x0 + 134, 176, 4, FACADE_BOTTOM - 176, C("#3a3a46"))
    for k in range(0, 60, 8):
        cv.rect(x0 + 138 + k, 180, 8, 4, P["red"] if (k // 8) % 2 == 0 else P["white"])
    cv.rect(x0 + 124, 150, 10, 22, C("#24242e"))
    cv.ellipse(x0 + 126, 152, x0 + 131, 157, C("#ff3a3a"), em=1)
    cv.ellipse(x0 + 126, 162, x0 + 131, 167, C("#3a2a2a"))
    R.lights.append((x0 + 129, 155, C("#ff3a3a"), 14, 0.6))
    cv.rect(x0, FACADE_BOTTOM - 6, w, 6, C("#a8a090"))
    cv.hl(x0, FACADE_BOTTOM - 6, w, C("#d0c8b8"))


@facade("market_arch")
def f_market_arch(R, x0, w, f):
    cv = R.cv
    rng = R.rng("march", x0)
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    cx = x0 + w // 2
    # hazy market buildings beyond the gate
    hz = C("#c8e8f0")
    k = x0
    while k < x0 + w:
        hw = rng.randrange(26, 44)
        hh = rng.randrange(60, 100)
        col = mix(rng.choice(CANAL_HOUSES), hz, 0.45)
        cv.rect(k, FACADE_BOTTOM - hh, hw, hh, col)
        cv.poly([(k, FACADE_BOTTOM - hh), (k + hw // 2, FACADE_BOTTOM - hh - 10), (k + hw, FACADE_BOTTOM - hh)], col)
        for wy in range(FACADE_BOTTOM - hh + 8, FACADE_BOTTOM - 40, 14):
            for wx in range(k + 5, k + hw - 6, 10):
                cv.rect(wx, wy, 4, 6, mix(col, C("#5a7a9a"), 0.4))
        k += hw
    # distant stalls seen through the arch (small, hazy)
    for k in range(x0 + 30, x0 + w - 40, 34):
        col = rng.choice([P["red"], P["blue"], P["mustard"], P["green"], P["orange"]])
        col = mix(col, C("#c8e8f0"), 0.35)
        cv.rect(k, 170, 30, FACADE_BOTTOM - 170, mix(C("#8a6a4a"), C("#c8e8f0"), 0.3))
        awning(cv, k - 2, 162, 34, 9, col, mix(P["white"], C("#c8e8f0"), 0.3), stripe=4, shade=False)
        for fx in range(k + 2, k + 28, 3):
            cv.px(fx, 184, rng.choice([P["red"], P["orange"], P["yellow"], P["green"]]))
    cv.rect(x0 + 20, 196, w - 40, FACADE_BOTTOM - 196, mix(C("#9a8e7e"), C("#c8e8f0"), 0.25))
    # brick pillars
    pw = 30
    for px_ in (x0 + 6, x0 + w - 6 - pw):
        tex_brick(cv, px_, 60, pw, FACADE_BOTTOM - 60, seed=seed_of(R.id, px_))
        cv.rect(px_ - 3, 54, pw + 6, 8, C("#d8ccb0"))
        cv.hl(px_ - 3, 54, pw + 6, C("#f0e8d0"))
        cv.rect(px_ + 4, 40, pw - 8, 14, C("#d8ccb0"))
        cv.ellipse(px_ + 6, 30, px_ + pw - 7, 46, C("#d8ccb0"))
        cv.rect(px_ - 3, FACADE_BOTTOM - 14, pw + 6, 14, C("#c8bca0"))
        cv.vl(px_ + pw - 1, 62, FACADE_BOTTOM - 76, dk(C("#a04a3a"), 0.3))
        # lantern on bracket
        lx = px_ + pw // 2
        cv.rect(lx - 3, 92, 7, 9, C("#2e3440"))
        cv.rect(lx - 2, 94, 5, 6, P["lamp"], em=1)
        R.lights.append((lx, 97, P["lamp"], 16, 0.4))
    # iron arch
    iron = C("#2e3440")
    ax0, ax1 = x0 + 6 + pw, x0 + w - 6 - pw
    span = ax1 - ax0
    for k in range(span):
        t = k / max(1, span - 1)
        yy = int(70 - math.sin(t * math.pi) * 34)
        cv.rect(ax0 + k, yy, 1, 3, iron)
        cv.px(ax0 + k, yy + 12, iron)
        if k % 8 == 0:
            cv.line(ax0 + k, yy + 2, ax0 + k + 4, yy + 12, iron)
    cv.rect(ax0, 82, span, 3, iron)
    for k in range(0, span, 16):
        cv.ellipse(ax0 + k + 3, 86, ax0 + k + 12, 95, iron)
        cv.ellipse(ax0 + k + 5, 88, ax0 + k + 10, 93, (0, 0, 0))
        cv.clear(ax0 + k + 6, 89, 4, 4)
    # sign plaque at the crown
    s = f.get("sign", "MARKET")
    sw = text_w(s, 2) + 20
    signboard(cv, cx - sw // 2, 22, sw, 24, s, C("#1e5a3a"), C("#f0d890"), border=C("#0e3a22"))
    cv.rect(cx - sw // 2 + 2, 24, sw - 4, 1, C("#c8a040"))
    # bunting hanging from the arch
    pts = cv.sag(ax0, 100, ax1, 100, 14, C("#e8e4dc"))
    for i, (px_, py_) in enumerate(pts[3::7]):
        col = [P["red"], P["yellow"], P["blue"], P["green"], P["white"]][i % 5]
        cv.poly([(px_ - 3, py_ + 1), (px_ + 3, py_ + 1), (px_, py_ + 7)], col)


SHOP_STYLES = {
    0: dict(wall=C("#c8a070"), front=C("#22605e"), awn=(C("#3a9a9a"), P["white"]), sign=(C("#f0e8d0"), C("#22605e"))),
    1: dict(wall=C("#c84a3a"), front=C("#7a2030"), awn=(C("#c03a3a"), C("#f0c040")), sign=(C("#1a1220"), C("#f0c040"))),
    2: dict(wall=C("#d8c8a8"), front=C("#2a5a3a"), awn=(C("#2a5a3a"), C("#e8d8b0")), sign=(C("#2a5a3a"), C("#f0d890"))),
}


@facade("shopfront")
def f_shopfront(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    st = SHOP_STYLES.get(var, SHOP_STYLES[0])
    rng = R.rng("shop", x0)
    top = 54
    roof_clear(cv, x0, w, top - 10)
    if var == 1:
        tex_siding(cv, x0, top, w, FACADE_BOTTOM - top, st["wall"], pitch=4)
    else:
        tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=st["wall"], shadow=dk(st["wall"], 0.2),
                  hi=lt(st["wall"], 0.2), mortar=dk(st["wall"], 0.3), seed=seed_of(R.id, x0), calm=True)
    trim = C("#f0e8d8")
    cornice(cv, x0 + 2, w - 4, top - 6, trim)
    cv.rect(x0 + 2, top - 10, w - 4, 4, dk(trim, 0.1))
    # upper windows with flower boxes
    n = max(2, w // 64)
    for k in range(n):
        wx = x0 + int((k + 0.5) * w / n) - 10
        window(cv, R, wx, top + 16, 20, 28, lit=rng.random() < 0.3, frame=trim, lintel=dk(trim, 0.1), rng=rng,
               shutters=st["front"] if var != 1 else None)
        cv.rect(wx - 1, top + 46, 22, 4, P["wood_d"])
        for fx in range(wx, wx + 20, 2):
            cv.px(fx, top + 45, rng.choice([P["red"], P["n_pink"], P["yellow"], P["white"]]))
            cv.px(fx + 1, top + 45, P["green"])
    # shop front
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else x0 + w // 2
    fy = 126
    cv.rect(x0 + 6, fy, w - 12, FACADE_BOTTOM - fy, st["front"])
    cv.hl(x0 + 6, fy, w - 12, lt(st["front"], 0.3))
    # sign board
    s = f.get("sign", "SHOP")
    signboard(cv, x0 + 12, fy + 2, w - 24, 20, s, st["sign"][0], st["sign"][1], border=dk(st["front"], 0.4))
    awning(cv, x0 + 8, fy + 24, w - 16, 14, st["awn"][0], st["awn"][1], stripe=8)
    # display windows either side of the door
    for (bx, bw) in ((x0 + 12, dx - 22 - (x0 + 12)), (dx + 22, x0 + w - 12 - (dx + 22))):
        if bw < 16:
            continue
        wy = fy + 40
        wh = FACADE_BOTTOM - wy - 14
        cv.rect(bx - 1, wy - 1, bw + 2, wh + 2, dk(st["front"], 0.4))
        cv.vgrad(bx, wy, bw, wh, LIT, em=1)
        if var == 1:      # noodle bar: steam bowls + lantern
            for k in range(bx + 6, bx + bw - 10, 18):
                cv.ellipse(k, wy + wh - 10, k + 12, wy + wh - 2, C("#e8e4dc"), em=1)
                cv.rect(k, wy + wh - 7, 13, 2, C("#c03a3a"), em=1)
                for sx in (k + 3, k + 7):
                    for sy in range(wy + wh - 18, wy + wh - 11, 2):
                        cv.px(sx + (sy // 2) % 2, sy, C("#fff8e8"), em=1)
        elif var == 2:    # books: stacks and a reading lamp
            for k in range(bx + 3, bx + bw - 4, 4):
                hh = rng.randrange(8, 18)
                cv.rect(k, wy + wh - hh, 3, hh, rng.choice([P["red_d"], P["navy"], P["green_d"], P["mustard_d"],
                                                              P["brown"]]), em=1)
            cv.rect(bx + bw // 2 - 8, wy + 6, 16, 2, C("#5a3a20"), em=1)
            for k in range(bx + bw // 2 - 8, bx + bw // 2 + 8, 3):
                cv.rect(k, wy + 2, 2, 4, rng.choice([P["red"], P["blue"], P["mustard"]]), em=1)
        else:
            for k in range(bx + 4, bx + bw - 8, 12):
                cv.rect(k, wy + wh - 12, 8, 12, rng.choice([P["mustard"], P["teal"], P["red"]]), em=1)
        cv.hl(bx, wy, bw, (255, 255, 240), em=1)
        cv.line(bx + 3, wy + 3, bx + 10, wy + wh - 3, lt(LIT[0], 0.5), em=1)
        cv.rect(bx - 1, wy + wh + 1, bw + 2, 13, dk(st["front"], 0.2))
        cv.hl(bx - 1, wy + wh + 1, bw + 2, lt(st["front"], 0.2))
    if var == 1:
        # red paper lanterns along the awning
        for k in range(x0 + 20, x0 + w - 16, 30):
            cv.vl(k, fy + 38, 4, C("#2a2a32"))
            cv.ellipse(k - 4, fy + 42, k + 4, fy + 52, C("#e04a3a"), em=1)
            cv.hl(k - 2, fy + 42, 5, C("#f0c040"), em=1)
            cv.hl(k - 2, fy + 52, 5, C("#f0c040"), em=1)
            cv.vl(k, fy + 53, 3, C("#f0c040"), em=1)
            R.lights.append((k, fy + 47, C("#ff6a4a"), 14, 0.35))
    R.accents[x0] = st["awn"][0]
    R.lights.append((dx, FACADE_BOTTOM - 20, LIT[1], w // 2, 0.35))


@facade("stall_row")
def f_stall_row(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("stalls", x0)
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    # back wall: timber market shed (set back) with sky above
    top = 112
    tex_planks_v(cv, x0, top, w, FACADE_BOTTOM - top, C("#8a6a4a"), pw=8, seed=x0)
    cv.blend(x0, top, w, FACADE_BOTTOM - top, C("#5a4a5a"), 0.25)
    cv.poly([(x0, top), (x0 + w, top), (x0 + w, top - 10), (x0, top - 10)], C("#7a4a3a"))
    for xx in range(x0, x0 + w, 4):
        cv.vl(xx, top - 10, 10, C("#8a5a44"))
    cv.hl(x0, top - 10, w, C("#a87a5a"))
    for xx in range(x0 + 20, x0 + w - 10, 60):
        cv.rect(xx, top + 10, 14, 10, C("#3a2a2a"))
    # stalls
    n = max(2, w // 66)
    sw = w // n
    awn_cols = [(P["red"], P["white"]), (P["blue"], P["white"]), (P["green"], C("#f0e8b0")),
                (P["orange"], P["white"]), (C("#e0b040"), C("#7a2030"))]
    for k in range(n):
        sx = x0 + k * sw + 3
        ww = sw - 6
        c1, c2 = awn_cols[(k + var * 2) % len(awn_cols)]
        # posts
        for pxx in (sx + 1, sx + ww - 3):
            cv.rect(pxx, 150, 2, FACADE_BOTTOM - 150, C("#5e3a1e"))
        # back cloth
        cv.rect(sx + 3, 158, ww - 6, 24, mix(c1, C("#2a2a32"), 0.55))
        # canvas canopy
        awning(cv, sx - 2, 142, ww + 4, 16, c1, c2, stripe=7)
        # counter with produce crates
        cy = FACADE_BOTTOM - 26
        cv.rect(sx, cy, ww, 26, C("#7a5030"))
        cv.hl(sx, cy, ww, C("#a87a50"))
        for yy in range(cy + 6, FACADE_BOTTOM, 6):
            cv.hl(sx, yy, ww, C("#5e3a1e"))
        goods = [[C("#e04a3a"), C("#c03a3a")], [C("#f0a030"), C("#e07a20")], [C("#8ac040"), C("#5a9a30")],
                 [C("#f0d040"), C("#d0a020")], [C("#7a3a7a"), C("#5a2a6a")]]
        if var == 1:
            goods = [[C("#ff8ab0"), C("#e04a80")], [C("#ffffff"), C("#f0e040")], [C("#c89050"), C("#a06a30")],
                     [C("#ffd040"), C("#e0a020")], [C("#9ad0e0"), C("#6aa0c8")]]
        cw = 14
        for cxx in range(sx + 2, sx + ww - cw, cw + 2):
            g = rng.choice(goods)
            cv.rect(cxx, cy - 8, cw, 8, C("#c8a070"))
            cv.hl(cxx, cy - 8, cw, C("#e0c090"))
            cv.vl(cxx + cw - 1, cy - 8, 8, C("#987048"))
            for fy_ in range(cy - 12, cy - 6, 2):
                for fx_ in range(cxx + 1 + (fy_ // 2) % 2, cxx + cw - 1, 3):
                    cv.rect(fx_, fy_, 2, 2, g[0])
                    cv.px(fx_ + 1, fy_ + 1, g[1])
        # price sign
        signboard(cv, sx + ww // 2 - 8, 166, 16, 9, None, C("#f0e8d0"), INK, border=C("#3a2a22"))
        cv.hl(sx + ww // 2 - 5, 170, 10, C("#3a3a46"))
    # bunting across the row
    pts = cv.sag(x0, 136, x0 + w, 136, 8, C("#e8e4dc"))
    for i, (px_, py_) in enumerate(pts[2::7]):
        col = [P["red"], P["yellow"], P["blue"], P["green"], P["white"]][i % 5]
        cv.poly([(px_ - 3, py_ + 1), (px_ + 3, py_ + 1), (px_, py_ + 7)], col)



# ============================================================================
# FACADES - Ironworks Yard
# ============================================================================
def smoke_puff(cv, x, y, r, col, rng):
    for _ in range(5):
        dx = rng.randrange(-r, r + 1)
        dy = rng.randrange(-r // 2, r // 2 + 1)
        rr = rng.randrange(max(2, r // 2), r + 1)
        cv.ellipse(x + dx - rr, y + dy - rr, x + dx + rr, y + dy + rr, col)
    cv.ellipse(x - r // 2, y - r // 2 - 1, x, y - 1, lt(col, 0.15))


def smokestack(cv, R, x, top, bottom, w=16, col=None, rng=None, band=True):
    col = col or C("#8a4a3a")
    tex_brick(cv, x, top, w, bottom - top, base=col, shadow=dk(col, 0.25), hi=lt(col, 0.2), seed=x, bw=6, bh=3,
              calm=True)
    cv.vl(x + w - 1, top, bottom - top, dk(col, 0.4))
    cv.vl(x, top, bottom - top, lt(col, 0.15))
    cv.rect(x - 2, top, w + 4, 4, dk(col, 0.3))
    cv.hl(x - 2, top, w + 4, lt(col, 0.1))
    if band:
        for by in (top + 12, top + 18):
            cv.rect(x, by, w, 2, C("#e8e4dc"))
    cv.rect(x + 2, top - 1, w - 4, 1, C("#2a1a1a"))
    if rng is not None:
        sc = C("#9a8a88")
        for k in range(4):
            smoke_puff(cv, x + w // 2 + k * 9, top - 8 - k * 9, 6 + k * 2, mix(sc, C("#c8a090"), k / 4), rng)


def rail_tracks_into(cv, x, w):
    """Short rail stubs running from the facade into the gravel."""
    for s in (0, 9):
        cv.rect(x, FACADE_BOTTOM - 4 + s // 3, w, 2, P["steel"])


@facade("yard_gate")
def f_yard_gate(R, x0, w, f):
    cv = R.cv
    rng = R.rng("ygate", x0)
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    # yard beyond: sheds silhouettes (set back, hazy)
    for k in range(x0, x0 + w, 70):
        hh = rng.randrange(50, 90)
        cv.rect(k, FACADE_BOTTOM - hh, 66, hh, C("#6a4a44"))
        cv.poly([(k, FACADE_BOTTOM - hh), (k + 33, FACADE_BOTTOM - hh - 14), (k + 66, FACADE_BOTTOM - hh)],
                C("#5a3e3a"))
        for wx in range(k + 6, k + 60, 12):
            cv.rect(wx, FACADE_BOTTOM - hh + 10, 6, 8, C("#e0904a") if rng.random() < 0.3 else C("#3a2a2e"),
                    em=0)
    # brick gate posts
    pw = 32
    posts = (x0 + 14, x0 + w - 14 - pw)
    for px_ in posts:
        tex_brick(cv, px_, 70, pw, FACADE_BOTTOM - 70, seed=px_, weather=0.5)
        cv.rect(px_ - 3, 64, pw + 6, 8, C("#a89c88"))
        cv.hl(px_ - 3, 64, pw + 6, C("#c8bca8"))
        cv.rect(px_ + 8, 52, pw - 16, 12, C("#a89c88"))
        cv.ellipse(px_ + 8, 44, px_ + pw - 9, 58, C("#3a3a46"))
        cv.rect(px_ + 12, 48, pw - 24, 6, P["lamp"], em=1)
        R.lights.append((px_ + pw // 2, 52, P["lamp"], 20, 0.5))
    # iron arch with lettering
    iron = C("#2a2630")
    ax0, ax1 = posts[0] + pw, posts[1]
    span = ax1 - ax0
    s = f.get("sign", "IRONWORKS")
    sc, b = fit_scale(s, span - 10, 2)
    for k in range(span):
        t = k / max(1, span - 1)
        yy = int(76 - math.sin(t * math.pi) * 18)
        cv.rect(ax0 + k, yy, 1, 2, iron)
        cv.rect(ax0 + k, yy + 18, 1, 2, iron)
        if k % 10 == 0:
            cv.line(ax0 + k, yy + 2, ax0 + k + 5, yy + 18, iron)
    cv.text_c((ax0 + ax1) // 2, 64, s, C("#e8d8b0"), sc, bold=b, outline=iron)
    # open gate leaves swung back against the posts
    for side, gx in ((1, ax0), (-1, ax1 - 26)):
        for k in range(0, 26, 4):
            cv.vl(gx + k, 110, FACADE_BOTTOM - 110, iron)
            cv.px(gx + k, 108, iron)
            cv.px(gx + k, 107, P["orange_d"])
        cv.hl(gx, 112, 26, iron)
        cv.hl(gx, 150, 26, iron)
        cv.hl(gx, FACADE_BOTTOM - 6, 26, iron)
    # guard hut
    hx = x0 + w // 2 - 20
    cv.rect(hx, 160, 40, FACADE_BOTTOM - 160, C("#a8a48a"))
    cv.rect(hx - 3, 156, 46, 5, C("#5a5a66"))
    cv.rect(hx + 5, 168, 30, 14, C("#ffcf8a"), em=1)
    cv.vl(hx + 20, 168, 14, C("#5a5a66"))
    R.lights.append((hx + 20, 175, C("#ffcf8a"), 22, 0.4))
    rail_tracks_into(cv, x0, w)


@facade("rail_shed")
def f_rail_shed(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("rshed", x0)
    top = 70
    roof_clear(cv, x0, w, top - 30)
    # sawtooth roof
    tooth = 50
    for k in range(x0, x0 + w, tooth):
        cv.poly([(k, top), (k, top - 26), (k + tooth, top)], C("#5a4a48"))
        cv.rect(k, top - 26, 4, 26, C("#e0a060") if rng.random() < 0.5 else C("#4a5a6a"))
        cv.line(k, top - 26, k + tooth, top, C("#7a6a64"))
    tex_corrugated(cv, x0, top, w, FACADE_BOTTOM - top, C("#9a6a4a"), pitch=4, seed=x0, rust=0.4)
    cv.rect(x0, top, w, 4, C("#5a4a48"))
    # big sliding doors (one open with locomotive nose)
    dw = min(110, w // 2 - 20)
    dx = x0 + w // 2 - dw // 2
    cv.rect(dx - 4, 96, dw + 8, FACADE_BOTTOM - 96, C("#3a2e2e"))
    cv.vgrad(dx, 100, dw, FACADE_BOTTOM - 100, [C("#1a1418"), C("#2a2026")])
    if var == 0:
        # locomotive front
        lc = C("#2a5a3a")
        cv.rect(dx + 14, 130, dw - 28, FACADE_BOTTOM - 136, lc)
        cv.rect(dx + 20, 120, dw - 40, 12, dk(lc, 0.2))
        cv.rect(dx + 24, 136, dw - 48, 14, C("#c8e0e8"))
        cv.vl(dx + dw // 2, 136, 14, lc)
        cv.ellipse(dx + dw // 2 - 6, 158, dx + dw // 2 + 6, 170, C("#fff0b0"), em=1)
        cv.rect(dx + 14, 176, dw - 28, 4, P["yellow"])
        for k in range(dx + 14, dx + dw - 14, 8):
            cv.rect(k, 176, 4, 4, INK)
        cv.rect(dx + 10, FACADE_BOTTOM - 8, dw - 20, 4, C("#3a3a46"))
        R.lights.append((dx + dw // 2, 164, C("#fff0b0"), 24, 0.6))
    else:
        # flatcars with coils
        cv.rect(dx + 8, FACADE_BOTTOM - 22, dw - 16, 8, C("#5a3a2a"))
        for k in range(dx + 14, dx + dw - 24, 24):
            cv.ellipse(k, FACADE_BOTTOM - 42, k + 20, FACADE_BOTTOM - 22, C("#7a7480"))
            cv.ellipse(k + 6, FACADE_BOTTOM - 36, k + 14, FACADE_BOTTOM - 28, C("#2a2630"))
    # door leaf slid aside
    tex_corrugated(cv, dx + dw + 4, 100, min(dw // 2, x0 + w - dx - dw - 10), FACADE_BOTTOM - 100,
                   C("#7a5040"), pitch=4)
    cv.rect(dx - 6, 94, dw + 12, 4, C("#3a3a46"))
    # number + windows
    cv.text(x0 + 16, 84, str(3 + var * 4), C("#e8d8b0"), 2, bold=True)
    for wx in range(x0 + 14, x0 + w - 30, 46):
        if dx - 8 < wx < dx + dw + 8 or dx - 8 < wx + 24 < dx + dw + 8:
            continue
        cv.rect(wx, 120, 26, 18, C("#3a3a46"))
        for gx in range(wx + 1, wx + 25, 6):
            for gy in range(121, 137, 6):
                lit = rng.random() < 0.25
                cv.rect(gx, gy, 5, 5, C("#f0a050") if lit else C("#6a5a5a"), em=1 if lit else 0)
    rail_tracks_into(cv, x0, w)


def pipes_and_cranes(cv, R, x0, w, rng):
    """Background industrial clutter seen through chain-link (opaque objects, sky elsewhere)."""
    # gantry crane silhouette
    gx = x0 + rng.randrange(20, max(21, w - 160))
    gc = C("#c87a30")
    cv.rect(gx, 40, 6, FACADE_BOTTOM - 40, gc)
    cv.rect(gx + 120, 40, 6, FACADE_BOTTOM - 40, gc)
    cv.rect(gx - 10, 34, 150, 8, gc)
    cv.hl(gx - 10, 34, 150, lt(gc, 0.3))
    for k in range(gx - 8, gx + 136, 10):
        cv.line(k, 41, k + 5, 35, dk(gc, 0.3))
    cv.rect(gx + 50, 42, 20, 10, C("#3a3a46"))
    cv.vl(gx + 60, 52, 50, C("#2a2630"))
    cv.rect(gx + 56, 102, 9, 5, C("#2a2630"))
    for k in range(48, FACADE_BOTTOM, 14):
        cv.line(gx, k, gx + 6, k + 14, dk(gc, 0.3))
        cv.line(gx + 120, k, gx + 126, k + 14, dk(gc, 0.3))
    # pipe racks
    py = 150
    for k in range(3):
        yy = py + k * 10
        col = [C("#8a8a96"), C("#9a6a3a"), C("#6a7280")][k]
        cv.rect(x0, yy, w, 7, col)
        cv.hl(x0, yy + 1, w, lt(col, 0.3))
        cv.hl(x0, yy + 6, w, dk(col, 0.35))
        for fx in range(x0 + rng.randrange(0, 40), x0 + w, 60):
            cv.rect(fx, yy - 1, 3, 9, dk(col, 0.2))
    for k in range(x0 + 10, x0 + w, 80):
        cv.rect(k, 146, 4, FACADE_BOTTOM - 146, C("#4a3a3a"))
    # storage tank
    tx = x0 + w - 110
    cv.rect(tx, 92, 70, FACADE_BOTTOM - 92, C("#9a948a"))
    cv.ellipse(tx, 84, tx + 69, 100, C("#b0aaa0"))
    cv.vl(tx + 69, 92, FACADE_BOTTOM - 92, C("#6a645a"))
    for k in range(98, FACADE_BOTTOM, 16):
        cv.hl(tx, k, 70, C("#8a847a"))
    cv.line(tx + 60, 90, tx + 50, FACADE_BOTTOM, C("#5a5a66"))


@facade("chainlink_yard")
def f_chainlink_yard(R, x0, w, f):
    cv = R.cv
    rng = R.rng("cly", x0 + f.get("variant", 0))
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    pipes_and_cranes(cv, R, x0, w, rng)
    # coil stacks / scrap
    for k in range(4):
        cx = x0 + rng.randrange(0, w - 30)
        cv.ellipse(cx, FACADE_BOTTOM - 24, cx + 24, FACADE_BOTTOM, C("#6a6470"))
        cv.ellipse(cx + 7, FACADE_BOTTOM - 17, cx + 17, FACADE_BOTTOM - 7, C("#2a2630"))
    fy = 120
    chainlink(cv, x0, fy, w, FACADE_BOTTOM - fy, wire=C("#a8a49c"), post=C("#5a5a62"), posts=50)
    barbed(cv, x0, fy - 10, w)
    for px_ in range(x0, x0 + w + 1, 50):
        cv.line(px_ + 1, fy - 3, px_ + 7, fy - 10, C("#5a5a62"))
    # danger sign
    sx = x0 + w // 2 - 14
    cv.rect(sx, 150, 28, 20, C("#e8e4dc"))
    cv.rect(sx + 1, 151, 26, 6, P["red"])
    cv.text_c(sx + 14, 151, "KEEP", P["white"], 1) if False else None
    cv.hl(sx + 4, 160, 20, C("#3a3a46"))
    cv.hl(sx + 4, 163, 16, C("#3a3a46"))
    cv.hl(sx + 4, 166, 18, C("#3a3a46"))


@facade("brick_factory")
def f_brick_factory(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("bfac", x0)
    top = 64
    roof_clear(cv, x0, w, 0)
    # smokestacks behind
    for k, sx in enumerate((x0 + w // 4, x0 + 3 * w // 4 - 10)[:1 + (w > 300)]):
        smokestack(cv, R, sx, 18 + k * 10, top, w=18, rng=rng)
    # sawtooth roof
    for k in range(x0, x0 + w, 40):
        cv.poly([(k, top), (k + 40, top), (k + 40, top - 18)], C("#4a3e3e"))
        cv.rect(k + 36, top - 16, 3, 16, C("#e8904a"), em=1)
    b = (C("#8a4434"), C("#6a2e24"), C("#a85a44"))
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=b[0], shadow=b[1], hi=b[2], seed=seed_of(R.id, x0),
              weather=0.9)
    # soot band at the top
    cv.dither_blend(x0, top, w, 20, C("#2a1a1a"), 0.35)
    # tall multi-pane windows
    n = max(3, w // 60)
    for k in range(n):
        wx = x0 + int((k + 0.5) * w / n) - 15
        cv.rect(wx - 2, 88, 34, 84, C("#6a5a50"))
        cv.ellipse(wx - 2, 80, wx + 31, 96, C("#6a5a50"))
        for gy in range(90, 170, 8):
            for gx in range(wx, wx + 30, 6):
                lit = rng.random() < (0.35 if var == 0 else 0.2)
                broken = rng.random() < 0.06
                c = C("#f0a050") if lit else (C("#1a1418") if broken else C("#4a4a5a"))
                cv.rect(gx, gy, 5, 7, c, em=1 if lit else 0)
                if lit:
                    cv.hl(gx, gy, 5, C("#ffd090"), em=1)
    # pipe and ladder
    drainpipe(cv, x0 + w - 12, top, FACADE_BOTTOM, c=C("#6a6a72"))
    lx = x0 + 6
    cv.vl(lx, 70, FACADE_BOTTOM - 70, C("#3a3a46"))
    cv.vl(lx + 6, 70, FACADE_BOTTOM - 70, C("#3a3a46"))
    for yy in range(72, FACADE_BOTTOM, 5):
        cv.hl(lx, yy, 7, C("#3a3a46"))
    # ghost sign
    cv.text(x0 + 30, 72, "EST 1898" if var == 0 else "NO 2 MILL", mix(b[0], C("#e8d8b0"), 0.4), 1, bold=True)
    # loading door
    dx = x0 + w // 2 - 24
    cv.rect(dx, 176, 48, FACADE_BOTTOM - 176, C("#3a3a46"))
    tex_corrugated(cv, dx + 2, 178, 44, FACADE_BOTTOM - 178, C("#7a7a86"), pitch=3)
    base_plinth(cv, x0, w, c=C("#5a4a44"), h=6)


@facade("canteen")
def f_canteen(R, x0, w, f):
    cv = R.cv
    rng = R.rng("cant", x0)
    top = 104
    roof_clear(cv, x0, w, top - 24)
    # prefab corrugated with brick base
    tex_corrugated(cv, x0, top, w, FACADE_BOTTOM - top, C("#5a7a6a"), pitch=4, seed=x0, rust=0.15)
    tex_brick(cv, x0, FACADE_BOTTOM - 30, w, 30, base=C("#8a4a3a"), seed=x0, calm=True)
    cv.rect(x0, top - 4, w, 6, C("#3a4a44"))
    cv.hl(x0, top - 4, w, C("#7a9a8a"))
    # chimney pipe with steam
    px_ = x0 + w - 40
    cv.rect(px_, top - 30, 8, 26, C("#6a6a72"))
    cv.rect(px_ - 2, top - 34, 12, 4, C("#4a4a52"))
    smoke_puff(cv, px_ + 4, top - 44, 6, C("#c8b8b0"), rng)
    smoke_puff(cv, px_ + 10, top - 58, 8, C("#d8c8c0"), rng)
    # sign on the roof edge
    s = f.get("sign", "CANTEEN")
    sw = text_w(s, 2) + 20
    signboard(cv, x0 + (w - sw) // 2, top - 26, sw, 22, s, C("#f0e8d0"), C("#a0301e"), border=C("#3a2a22"))
    # steamy lit windows
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else x0 + w // 2
    for wx in (x0 + 16, x0 + 70, dx + 30, dx + 84):
        if wx + 40 > x0 + w - 8 or abs(wx + 20 - dx) < 34:
            continue
        cv.rect(wx - 2, 124, 44, 34, C("#e8e4dc"))
        cv.vgrad(wx, 126, 40, 30, [C("#fff0c8"), C("#ffc070"), C("#e09050")], em=1)
        cv.dither_blend(wx, 126, 40, 12, C("#fff8f0"), 0.35)
        cv.vl(wx + 20, 126, 30, C("#e8e4dc"))
        cv.rect(wx + 4, 148, 10, 8, C("#a0603a"), em=1)
        cv.ellipse(wx + 24, 146, wx + 32, 150, C("#c87a4a"), em=1)
        R.lights.append((wx + 20, 145, C("#ffc070"), 26, 0.45))
    # chalk menu board leaning
    mx = x0 + w - 40
    if abs(mx - dx) > 36:
        cv.rect(mx, 168, 26, 34, C("#5a3a20"))
        cv.rect(mx + 2, 170, 22, 28, C("#2a3a32"))
        for yy in range(174, 196, 4):
            cv.hl(mx + 4, yy, rng.randrange(10, 18), C("#e8e4dc"))
        cv.line(mx + 3, 202, mx - 2, FACADE_BOTTOM, C("#5a3a20"))
        cv.line(mx + 22, 202, mx + 27, FACADE_BOTTOM, C("#5a3a20"))
    R.accents[x0] = P["red"]


@facade("switch_house")
def f_switch_house(R, x0, w, f):
    cv = R.cv
    rng = R.rng("sw", x0)
    top = 60
    roof_clear(cv, x0, w, top - 22)
    bx0, bw = x0 + 20, w - 40
    # hipped roof
    cv.poly([(bx0 - 8, top), (bx0 + 20, top - 22), (bx0 + bw - 20, top - 22), (bx0 + bw + 8, top)], C("#3a4050"))
    for k in range(bx0, bx0 + bw, 5):
        cv.vl(k, top - 20, 20, C("#4a5060"))
    cv.hl(bx0 - 8, top, bw + 16, C("#2a2e3a"))
    # upper glazed operating floor
    cv.rect(bx0, top, bw, 54, C("#c8bca0"))
    n = max(4, bw // 34)
    for k in range(n):
        wx = bx0 + 4 + k * (bw - 8) // n
        ww = (bw - 8) // n - 4
        lit = k in (1, 2)
        window(cv, R, wx, top + 6, ww, 36, lit=lit, frame=C("#e8e4dc"), sill=False, rng=rng)
        if lit:
            for lx in range(wx + 3, wx + ww - 3, 4):
                cv.line(lx, top + 40, lx + 1, top + 30, C("#7a3a2a"), em=1)
    cv.rect(bx0 - 4, top + 50, bw + 8, 5, C("#5a4a40"))
    cv.hl(bx0 - 4, top + 50, bw + 8, C("#8a7a6a"))
    # brick lower floor
    tex_brick(cv, bx0, top + 55, bw, FACADE_BOTTOM - top - 55, seed=seed_of(R.id, x0), weather=0.6)
    s = f.get("sign", "SWITCH HOUSE")
    signboard(cv, bx0 + 10, top + 62, bw - 20, 18, s, C("#1e2a4a"), C("#f0e8d0"), border=C("#0e1a2a"))
    # external staircase to the upper door
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else x0 + w // 2
    sx0 = bx0 + bw - 6
    for k in range(14):
        cv.rect(sx0 - k * 4, top + 54 + k * 6, 12, 2, C("#3a3a46"))
    cv.line(sx0 + 12, top + 46, sx0 - 52 + 12, FACADE_BOTTOM - 30, C("#3a3a46"))
    # signal arms on a post
    px_ = x0 + 8
    cv.rect(px_, 30, 3, FACADE_BOTTOM - 30, C("#3a3a46"))
    cv.rect(px_ - 2, 40, 14, 4, P["red"])
    cv.rect(px_ + 10, 40, 2, 4, P["white"])
    cv.ellipse(px_ - 4, 46, px_ + 2, 52, C("#ff3a3a"), em=1)
    R.lights.append((px_ - 1, 49, C("#ff3a3a"), 12, 0.5))
    # windows ground floor
    for wx in (bx0 + 14, bx0 + bw - 40):
        if abs(wx + 10 - dx) > 30:
            window(cv, R, wx, 150, 20, 24, lit=rng.random() < 0.5, frame=C("#e8e4dc"), lintel=C("#c8bca0"),
                   rng=rng)
    R.accents[x0] = C("#1e2a4a")


@facade("foundry_wall")
def f_foundry_wall(R, x0, w, f):
    cv = R.cv
    rng = R.rng("fwall", x0)
    roof_clear(cv, x0, w, 0)
    # interior back wall of the foundry: soot-black brick, steel columns, pipes, gauges
    tex_brick(cv, x0, 0, w, FACADE_BOTTOM, base=C("#5a3430"), shadow=C("#3a2220"), hi=C("#7a4a40"),
              seed=seed_of(R.id, x0), weather=0.3)
    cv.dither_blend(x0, 0, w, 60, C("#140c10"), 0.5)
    # steel columns + roof truss
    steel = C("#4a4a56")
    for cxx in range(x0 + 20, x0 + w, 120):
        cv.rect(cxx, 0, 10, FACADE_BOTTOM, steel)
        cv.vl(cxx, 0, FACADE_BOTTOM, lt(steel, 0.25))
        cv.vl(cxx + 9, 0, FACADE_BOTTOM, dk(steel, 0.35))
        for yy in range(6, FACADE_BOTTOM, 24):
            cv.px(cxx + 2, yy, lt(steel, 0.4))
            cv.px(cxx + 7, yy, lt(steel, 0.4))
    cv.rect(x0, 18, w, 6, steel)
    for k in range(x0, x0 + w, 20):
        cv.line(k, 24, k + 10, 40, steel)
        cv.line(k + 10, 40, k + 20, 24, steel)
    cv.hl(x0, 40, w, steel)
    # pipes
    for k, yy in enumerate((70, 80)):
        col = [C("#8a6a4a"), C("#6a7280")][k]
        cv.rect(x0, yy, w, 6, col)
        cv.hl(x0, yy + 1, w, lt(col, 0.3))
        cv.hl(x0, yy + 5, w, dk(col, 0.4))
    # gauges + valve wheels + hazard plates
    for gx in range(x0 + 50, x0 + w - 40, 120):
        cv.ellipse(gx, 100, gx + 14, 114, C("#2a2630"))
        cv.ellipse(gx + 2, 102, gx + 12, 112, C("#e8e4dc"))
        cv.line(gx + 7, 107, gx + 10, 104, P["red"])
        cv.ellipse(gx + 30, 98, gx + 46, 114, P["red"])
        cv.ellipse(gx + 33, 101, gx + 43, 111, C("#5a3430"))
        cv.line(gx + 30, 106, gx + 46, 106, P["red"])
        cv.line(gx + 38, 98, gx + 38, 114, P["red"])
        cv.poly([(gx + 60, 140), (gx + 80, 140), (gx + 70, 124)], P["yellow"])
        cv.vl(gx + 70, 129, 6, INK)
        cv.px(gx + 70, 137, INK)
    # vent with steam
    vx = x0 + w // 2
    cv.rect(vx - 14, 130, 28, 20, C("#3a3a46"))
    for yy in range(132, 150, 3):
        cv.hl(vx - 12, yy, 24, C("#5a5a66"))
    smoke_puff(cv, vx, 120, 7, C("#8a7a7a"), rng)
    # hazard stripe skirting
    for xx in range(x0, x0 + w, 12):
        cv.poly([(xx, FACADE_BOTTOM - 10), (xx + 6, FACADE_BOTTOM - 10), (xx + 2, FACADE_BOTTOM),
                 (xx - 4, FACADE_BOTTOM)], P["yellow"])
        cv.poly([(xx + 6, FACADE_BOTTOM - 10), (xx + 12, FACADE_BOTTOM - 10), (xx + 8, FACADE_BOTTOM),
                 (xx + 2, FACADE_BOTTOM)], C("#24242e"))
    cv.hl(x0, FACADE_BOTTOM - 11, w, C("#2a2630"))


@facade("furnace")
def f_furnace(R, x0, w, f):
    cv = R.cv
    rng = R.rng("furn", x0)
    roof_clear(cv, x0, w, 0)
    tex_brick(cv, x0, 0, w, FACADE_BOTTOM, base=C("#5a3430"), shadow=C("#3a2220"), hi=C("#7a4a40"),
              seed=seed_of(R.id, x0), weather=0.3)
    cv.dither_blend(x0, 0, w, 60, C("#140c10"), 0.5)
    cx = x0 + w // 2
    # hood / chimney breast
    cv.poly([(cx - 150, 60), (cx + 150, 60), (cx + 100, 0), (cx - 100, 0)], C("#3a3a46"))
    for k in range(cx - 100, cx + 100, 8):
        cv.vl(k, 0, 60 - abs(k - cx) // 6, C("#4a4a56"))
    cv.rect(cx - 156, 58, 312, 8, C("#2a2a32"))
    cv.hl(cx - 156, 58, 312, C("#6a6a76"))
    # furnace body
    fb_x0, fb_w = cx - 130, 260
    cv.rect(fb_x0, 66, fb_w, FACADE_BOTTOM - 66, C("#4a3a3a"))
    tex_brick(cv, fb_x0 + 6, 70, fb_w - 12, FACADE_BOTTOM - 76, base=C("#7a4a3a"), shadow=C("#5a3028"),
              hi=C("#a06a50"), seed=fb_x0, bw=10, bh=5)
    # glowing mouth
    mx0, mw = cx - 70, 140
    my0 = 104
    cv.rect(mx0 - 6, my0 - 8, mw + 12, FACADE_BOTTOM - my0 + 8, C("#2a2026"))
    cv.ellipse(mx0 - 6, my0 - 30, mx0 + mw + 5, my0 + 20, C("#2a2026"))
    cv.vgrad(mx0, my0, mw, FACADE_BOTTOM - my0 - 4, [C("#fff4c0"), C("#ffc040"), C("#ff7a20"), C("#c03a10")],
             em=1)
    cv.ellipse(mx0, my0 - 22, mx0 + mw - 1, my0 + 14, C("#fff4c0"), em=1)
    # inner coals texture + organic flame tongues
    for _ in range(60):
        fx = rng.randrange(mx0, mx0 + mw)
        fy = rng.randrange(my0 + 40, FACADE_BOTTOM - 6)
        cv.rect(fx, fy, rng.randrange(2, 5), 2, rng.choice([C("#ff6a18"), C("#ffd060"), C("#d0400c")]), em=1)
    base_y = FACADE_BOTTOM - 14
    k = mx0 + 4
    while k < mx0 + mw - 10:
        fw = rng.randrange(10, 20)
        hh = rng.randrange(24, 60)
        lean = rng.randrange(-4, 5)
        for j in range(hh):
            t = j / hh
            half = int((fw / 2) * (1 - t) ** 0.7 * (0.8 + 0.2 * math.sin(j * 0.5)))
            cxf = k + fw // 2 + int(lean * t + math.sin(j * 0.25 + k) * 2 * t)
            col = mix(C("#ffb030"), C("#fff6c8"), min(1, t * 1.4)) if half > 1 else C("#fff6c8")
            cv.hl(cxf - half, base_y - j, max(1, 2 * half), col, em=1)
        k += fw - rng.randrange(2, 6)
    cv.rect(mx0, base_y, mw, FACADE_BOTTOM - base_y - 4, C("#ff9a30"), em=1)
    for _ in range(30):
        fx = rng.randrange(mx0, mx0 + mw)
        cv.rect(fx, rng.randrange(base_y, FACADE_BOTTOM - 4), 3, 2, C("#c0300a"), em=1)
    # door frame rivets + chains
    for k in range(mx0 - 4, mx0 + mw + 4, 8):
        cv.px(k, my0 - 6, C("#8a8a96"))
    for chx in (mx0 - 20, mx0 + mw + 18):
        for yy in range(66, my0 + 30, 4):
            cv.rect(chx, yy, 3, 3, C("#5a5a66"))
            cv.px(chx + 1, yy + 1, C("#2a2a32"))
    # molten channel at the base spilling forward
    cv.rect(mx0 + 10, FACADE_BOTTOM - 4, mw - 20, 4, C("#ff8a20"), em=1)
    R.lights.append((cx, my0 + 40, C("#ff8a30"), 200, 1.0))
    R.lights.append((cx, FACADE_BOTTOM + 40, C("#ff7a20"), 180, 0.8, "pool"))
    R.refl.append((mx0, mx0 + mw, my0, C("#ff9a40"), 1.0))
    # gauges either side
    for gx in (fb_x0 + 14, fb_x0 + fb_w - 30):
        cv.ellipse(gx, 80, gx + 16, 96, C("#2a2630"))
        cv.ellipse(gx + 2, 82, gx + 14, 94, C("#e8e4dc"))
        cv.line(gx + 8, 88, gx + 12, 84, P["red"])


@facade("crane_bay")
def f_crane_bay(R, x0, w, f):
    cv = R.cv
    rng = R.rng("cbay", x0)
    roof_clear(cv, x0, w, 0)
    # open bay: back wall far away (darker), roof girders, overhead crane, hook
    cv.vgrad(x0, 0, w, FACADE_BOTTOM, [C("#2a1e24"), C("#3a2a2e"), C("#4a3634")])
    # far wall corrugated, lit by distant dusk through high windows
    tex_corrugated(cv, x0, 60, w, FACADE_BOTTOM - 60, C("#5a4440"), pitch=5, seed=x0, rust=0.2)
    cv.blend(x0, 60, w, FACADE_BOTTOM - 60, C("#2a1e24"), 0.4)
    for k in range(x0 + 10, x0 + w - 30, 46):
        cv.rect(k, 70, 36, 16, C("#e08a4a"), em=1)
        cv.vl(k + 12, 70, 16, C("#3a2a2e"))
        cv.vl(k + 24, 70, 16, C("#3a2a2e"))
    # crane rails + bridge girder
    gc = C("#d0902a")
    cv.rect(x0, 30, w, 10, gc)
    cv.hl(x0, 30, w, lt(gc, 0.35))
    cv.hl(x0, 39, w, dk(gc, 0.4))
    for k in range(x0, x0 + w, 12):
        cv.line(k, 31, k + 6, 38, dk(gc, 0.25))
        cv.line(k + 6, 38, k + 12, 31, dk(gc, 0.25))
    # trolley + hook with chain
    tx = x0 + w // 2 - 20
    cv.rect(tx, 40, 40, 14, C("#3a3a46"))
    cv.rect(tx + 4, 44, 32, 6, P["yellow"])
    for k in range(0, 4):
        cv.text(tx + 6 + k * 8, 44, "", INK)
    for yy in range(54, 140, 4):
        cv.rect(tx + 19, yy, 3, 3, C("#6a6a76"))
    cv.rect(tx + 12, 140, 16, 8, C("#4a4a56"))
    cv.ellipse(tx + 12, 146, tx + 26, 162, C("#5a5a66"))
    cv.ellipse(tx + 16, 148, tx + 24, 156, C("#2a1e24"))
    cv.clear(tx + 12, 146, 0, 0)
    # hanging steel beam load
    cv.line(tx + 19, 160, tx - 10, 176, C("#6a6a76"))
    cv.line(tx + 21, 160, tx + 50, 176, C("#6a6a76"))
    cv.rect(tx - 40, 176, 120, 8, C("#7a7480"))
    cv.hl(tx - 40, 176, 120, C("#a8a2ae"))
    cv.hl(tx - 40, 183, 120, C("#3a3640"))
    # columns
    for cxx in (x0 + 6, x0 + w - 16):
        cv.rect(cxx, 0, 10, FACADE_BOTTOM, C("#4a4a56"))
        cv.vl(cxx, 0, FACADE_BOTTOM, C("#6a6a76"))
    # stacked steel plates at the back
    for k in range(4):
        cv.rect(x0 + 30, FACADE_BOTTOM - 8 - k * 6, 90, 5, C("#6a6470"))
        cv.hl(x0 + 30, FACADE_BOTTOM - 8 - k * 6, 90, C("#9a94a0"))
    cv.dither_blend(x0, FACADE_BOTTOM - 20, w, 20, C("#000000"), 0.2)



# ============================================================================
# FACADES - Neon Mile (drawn in day colours; night grading + emissive neon)
# ============================================================================
def water_tank(cv, x, ybase, w=28, h=26, legs=14):
    wood = C("#7a5a3e")
    for lx in (x + 2, x + w - 4):
        cv.rect(lx, ybase - legs, 2, legs, C("#3a2e2a"))
    cv.line(x + 2, ybase - 2, x + w - 3, ybase - legs + 2, C("#3a2e2a"))
    cv.line(x + w - 3, ybase - 2, x + 2, ybase - legs + 2, C("#3a2e2a"))
    tex_planks_v(cv, x, ybase - legs - h, w, h, wood, pw=4, seed=x)
    cv.hl(x, ybase - legs - h + 5, w, C("#4a3a2a"))
    cv.hl(x, ybase - legs - 6, w, C("#4a3a2a"))
    cv.poly([(x - 2, ybase - legs - h), (x + w // 2, ybase - legs - h - 10), (x + w + 1, ybase - legs - h)],
            C("#5a4a3a"))


def night_block(R, x0, w, top, rng, brick=None, lit_p=0.35, fe=False, var=0):
    cv = R.cv
    b = brick or BRICKS[(var + 1) % 4]
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=b[0], shadow=b[1], hi=b[2], seed=seed_of(R.id, x0),
              weather=0.4)
    trim = C("#b8ac98")
    cornice(cv, x0 + 2, w - 4, top - 6, trim)
    floors = list(range(top + 14, 120, 38))
    ncol = max(2, w // 50)
    for fy in floors:
        for k in range(ncol):
            cx = x0 + int((k + 0.5) * w / ncol)
            lit = rng.random() < lit_p
            pal = LIT_TV if lit and rng.random() < 0.25 else (
                [C("#ffb0d0"), C("#e070a0"), C("#a04070")] if lit and rng.random() < 0.15 else None)
            window(cv, R, cx - 8, fy, 16, 22, lit=lit, frame=trim, lintel=dk(trim, 0.1), rng=rng, pal=pal)
    if fe and floors:
        k = rng.randrange(ncol)
        cx = x0 + int((k + 0.5) * w / ncol)
        fire_escape(cv, cx - 22, 44, [fy + 24 for fy in floors], bottom=floors[-1] + 24 + 26)
    return floors


@facade("brick_night")
def f_brick_night(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("bn", x0)
    top = 40 if var == 0 else 56
    roof_clear(cv, x0, w, top - 8)
    night_block(R, x0, w, top, rng, fe=True, var=var)
    water_tank(cv, x0 + w - 60, top - 6)
    # ground floor: closed shop with a small neon "OPEN"/"BAR" and a lit doorway
    fy = 150
    cv.rect(x0 + 6, fy, w - 12, FACADE_BOTTOM - fy, C("#2a2a36"))
    gx = x0 + 14
    gw = w - 28
    cv.vgrad(gx, fy + 8, gw, FACADE_BOTTOM - fy - 18, [C("#6a4a7a"), C("#3a2a4a")])
    for k in range(gx, gx + gw, 40):
        cv.vl(k, fy + 8, FACADE_BOTTOM - fy - 18, C("#2a2a36"))
    word = "BAR" if var == 0 else "OPEN"
    col = P["n_pink"] if var == 0 else P["n_cyan"]
    neon_text(cv, R, x0 + w // 2, fy + 18, word, col)
    awning(cv, x0 + 10, fy - 6, w - 20, 10, C("#3a2a5a"), C("#5a4a7a"), stripe=10, shade=False)


@facade("theater_marquee")
def f_theater(R, x0, w, f):
    cv = R.cv
    rng = R.rng("thr", x0)
    top = 34
    roof_clear(cv, x0, w, 0)
    cx = x0 + w // 2
    # deco facade
    wall = C("#c8b090")
    cv.rect(x0, top, w, FACADE_BOTTOM - top, wall)
    for k in range(x0 + 8, x0 + w - 8, 10):
        cv.vl(k, top + 6, 90, dk(wall, 0.15))
        cv.vl(k + 1, top + 6, 90, lt(wall, 0.15))
    # stepped deco crown
    for i, (ww, hh) in enumerate(((w, 0), (w - 60, 10), (w - 140, 20), (w - 220, 28))):
        if ww <= 0:
            continue
        cv.rect(cx - ww // 2, top - hh, ww, hh + 6, mix(wall, C("#e8d8b0"), i * 0.15))
        cv.hl(cx - ww // 2, top - hh, ww, lt(wall, 0.3))
    cv.rect(x0, top + 96, w, 4, C("#a08a6a"))
    # vertical blade sign
    s = f.get("sign", "THEATER")
    bw = 30
    bx = cx - bw // 2
    bh = len(s) * 16 + 12
    by = max(2, 118 - bh)
    cv.rect(bx - 2, by - 2, bw + 4, bh + 4, C("#1a1424"))
    cv.rect(bx, by, bw, bh, C("#7a2030"))
    bulbs(cv, bx + 1, by + 1, bw - 2, bh - 2, step=4)
    for i, ch in enumerate(s):
        neon_text(cv, None, cx, by + 8 + i * 16, ch, P["n_yellow"])
    R.lights.append((cx, by + bh // 2, P["n_yellow"], 60, 0.8))
    R.refl.append((bx, bx + bw, by + bh, P["n_yellow"], 0.9))
    # marquee canopy
    my = 122
    mh = 30
    cv.rect(x0 + 16, my, w - 32, mh, C("#1a1424"))
    cv.rect(x0 + 18, my + 2, w - 36, mh - 4, C("#3a2a4a"))
    bulbs(cv, x0 + 17, my + 1, w - 34, mh - 2, step=4, phase=1)
    # reader board
    rbx, rbw = x0 + 30, w - 60
    cv.rect(rbx, my + 5, rbw, mh - 10, C("#fff8e0"), em=1)
    cv.text_c(cx, my + 6, "MIDNIGHT SHOW", INK, 1, em=1)
    cv.text_c(cx, my + 15, "THE IRON SPARROW", P["red_d"], 1, em=1)
    cv.rect(x0 + 16, my + mh, w - 32, 4, C("#2a1a2a"))
    cv.dither_blend(x0 + 16, my + mh + 4, w - 32, 8, (0, 0, 0), 0.5)
    R.lights.append((cx, my + mh, C("#fff0b0"), w // 2, 0.9))
    R.refl.append((x0 + 20, x0 + w - 20, my + mh, C("#fff0b0"), 0.9))
    # ticket booth
    tw = 40
    tx = cx - tw // 2
    cv.rect(tx - 2, 160, tw + 4, FACADE_BOTTOM - 160, C("#c8a040"))
    cv.ellipse(tx - 2, 152, tx + tw + 1, 170, C("#c8a040"))
    cv.vgrad(tx + 3, 164, tw - 6, 26, [C("#fff4d0"), C("#ffd080")], em=1)
    cv.ellipse(tx + 10, 172, tx + 18, 180, C("#7a4a3a"), em=1)
    cv.rect(tx + 8, 180, 12, 10, C("#7a2030"), em=1)
    cv.rect(tx - 2, 190, tw + 4, FACADE_BOTTOM - 190, C("#7a2030"))
    cv.hl(tx - 2, 190, tw + 4, C("#e0b040"))
    # dark glass doors + lit poster cases
    for side in (-1, 1):
        dx = cx + side * 60 - 18
        cv.rect(dx - 2, 160, 40, FACADE_BOTTOM - 160, C("#a08a6a"))
        cv.vgrad(dx, 162, 36, FACADE_BOTTOM - 162, [C("#4a3a5a"), C("#2a2236")])
        cv.vl(dx + 18, 162, FACADE_BOTTOM - 162, C("#a08a6a"))
        cv.px(dx + 16, 190, P["mustard"])
        cv.px(dx + 20, 190, P["mustard"])
        px_ = cx + side * 130 - 14
        if x0 + 4 < px_ < x0 + w - 32:
            cv.rect(px_ - 2, 158, 32, 44, C("#c8a040"))
            cv.rect(px_, 160, 28, 40, C("#fff4d0"), em=1)
            poster(cv, px_ + 2, 162, 24, 36, rng, palette=[P["red"], P["navy"], P["purple"], P["teal"],
                                                            P["mustard"]])
            for yy in range(162, 198, 6):
                cv.px(px_ + 1, yy, C("#fff8d0"), em=1)
            R.lights.append((px_ + 14, 180, C("#fff4d0"), 20, 0.5))
    # velvet rope posts
    for k in (cx - 46, cx + 44):
        cv.rect(k, FACADE_BOTTOM - 14, 3, 14, C("#c8a040"))
    cv.sag(cx - 44, FACADE_BOTTOM - 12, cx + 44, FACADE_BOTTOM - 12, 4, C("#a0203a"))


NEON_SHOPS = {
    0: dict(col=P["n_yellow"], col2=C("#ff6a3a"), glow=[C("#ffe0a0"), C("#ffa060"), C("#c05a30")],
            wall=C("#9a6a5a")),
    1: dict(col=P["n_pink"], col2=P["n_cyan"], glow=[C("#ffb0e0"), C("#c060a0"), C("#5a2a5a")],
            wall=C("#6a5a7a")),
    2: dict(col=P["n_cyan"], col2=C("#c06aff"), glow=[C("#b0f0ff"), C("#5aa0d0"), C("#2a4a7a")],
            wall=C("#5a6a7a")),
    3: dict(col=C("#ff4a4a"), col2=P["n_yellow"], glow=[C("#ffe0b0"), C("#e0a060"), C("#7a4a3a")],
            wall=C("#8a7a6a")),
}


@facade("neon_shopfront")
def f_neon_shopfront(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    st = NEON_SHOPS.get(var, NEON_SHOPS[0])
    rng = R.rng("ns", x0)
    top = rng.randrange(36, 60) if var != 3 else 20
    roof_clear(cv, x0, w, top - 8)
    if var in (1, 2):
        cv.rect(x0, top, w, FACADE_BOTTOM - top, st["wall"])
        cv.noise_tint(x0, top, w, FACADE_BOTTOM - top, rng, 5, 0.2)
        trim = lt(st["wall"], 0.4)
        cornice(cv, x0 + 2, w - 4, top - 6, trim)
        for fy in range(top + 14, 120, 38):
            for k in range(max(2, w // 60)):
                cx = x0 + int((k + 0.5) * w / max(2, w // 60))
                window(cv, R, cx - 9, fy, 18, 22, lit=rng.random() < 0.4, frame=trim, rng=rng)
    else:
        night_block(R, x0, w, top, rng, lit_p=0.45, var=var)
    s = f.get("sign", "SHOP")
    fy = 150
    # storefront glowing window
    cv.rect(x0 + 6, fy, w - 12, FACADE_BOTTOM - fy, C("#1e1c2a"))
    gx, gw = x0 + 12, w - 24
    cv.vgrad(gx, fy + 6, gw, FACADE_BOTTOM - fy - 14, st["glow"], em=1)
    # interior silhouettes
    for k in range(gx + 6, gx + gw - 12, 22):
        hh = rng.randrange(10, 22)
        cv.rect(k, FACADE_BOTTOM - 8 - hh, rng.randrange(8, 16), hh, dk(st["glow"][2], 0.4), em=1)
    for k in range(gx, gx + gw, 46):
        cv.vl(k, fy + 6, FACADE_BOTTOM - fy - 14, C("#1e1c2a"))
    cv.rect(x0 + 6, FACADE_BOTTOM - 8, w - 12, 8, C("#2a2836"))
    R.lights.append((x0 + w // 2, FACADE_BOTTOM - 20, st["glow"][1], w // 2, 0.6))
    R.refl.append((gx, gx + gw, fy + 10, st["glow"][1], 0.5))
    # neon sign above storefront on a dark backing
    if var == 3:
        # vertical HOTEL blade + VACANCY
        bx = x0 + w - 44
        bh = len(s) * 16 + 10
        by = 30
        cv.rect(bx, by, 30, bh, C("#1a1424"))
        cv.rect(bx - 6, by + 10, 6, 3, C("#3a3a46"))
        for i, ch in enumerate(s):
            neon_text(cv, None, bx + 15, by + 6 + i * 16, ch, st["col"])
        R.lights.append((bx + 15, by + bh // 2, st["col"], 50, 0.8))
        R.refl.append((bx, bx + 30, by + bh, st["col"], 0.9))
        cv.rect(x0 + 20, fy - 22, 80, 16, C("#1a1424"))
        neon_text(cv, R, x0 + 60, fy - 19, "VACANCY", st["col2"], gap=1)
    else:
        nw = neon_mask(s).shape[1]
        cv.rect(x0 + w // 2 - nw // 2 - 26, fy - 30, nw + 52, 24, C("#1a1424"))
        cv.rect(x0 + w // 2 - nw // 2 - 24, fy - 28, nw + 48, 20, C("#241c30"))
        neon_text(cv, R, x0 + w // 2 + 8, fy - 25, s, st["col"])
        ix = x0 + w // 2 - nw // 2 - 12
        iy = fy - 26
        c2 = lt(st["col2"], 0.4)
        if var == 0:     # pizza slice
            cv.poly([(ix - 7, iy), (ix + 7, iy), (ix, iy + 15)], st["col2"], em=1)
            cv.hl(ix - 7, iy, 15, c2, em=1)
            for (px_, py_) in ((ix - 2, iy + 4), (ix + 2, iy + 7), (ix, iy + 3)):
                cv.rect(px_, py_, 2, 2, P["n_yellow"], em=1)
        elif var == 1:   # cocktail glass
            cv.poly([(ix - 7, iy), (ix + 7, iy), (ix, iy + 8)], c2, em=1)
            cv.vl(ix, iy + 8, 6, c2, em=1)
            cv.hl(ix - 4, iy + 14, 9, c2, em=1)
            cv.px(ix + 5, iy - 2, P["n_green"], em=1)
        elif var == 2:   # vinyl record
            cv.ellipse(ix - 8, iy - 1, ix + 8, iy + 15, c2, em=1)
            cv.ellipse(ix - 6, iy + 1, ix + 6, iy + 13, C("#241c30"))
            cv.ellipse(ix - 2, iy + 5, ix + 2, iy + 9, c2, em=1)
        R.lights.append((ix, iy + 8, st["col2"], 24, 0.6))


@facade("pharmacy")
def f_pharmacy(R, x0, w, f):
    cv = R.cv
    rng = R.rng("phar", x0)
    top = 44
    roof_clear(cv, x0, w, top - 8)
    cv.rect(x0, top, w, FACADE_BOTTOM - top, C("#d8d0c0"))
    cv.noise_tint(x0, top, w, FACADE_BOTTOM - top, rng, 4, 0.15)
    for yy in range(top + 8, 140, 8):
        cv.hl(x0, yy, w, C("#c8c0b0"))
    cornice(cv, x0 + 2, w - 4, top - 6, C("#e8e4dc"))
    for fy in (top + 16, top + 54):
        for k in range(4):
            cx = x0 + int((k + 0.5) * w / 4)
            window(cv, R, cx - 9, fy, 18, 24, lit=rng.random() < 0.35, frame=C("#f0ece4"), rng=rng)
    # projecting green cross
    gx, gy = x0 + 24, 66
    cv.rect(gx - 8, gy + 6, 8, 3, C("#3a3a46"))
    cv.rect(gx, gy, 30, 30, C("#1a2a22"))
    for (rx, ry, rw, rh) in ((gx + 10, gy + 3, 10, 24), (gx + 3, gy + 10, 24, 10)):
        cv.rect(rx, ry, rw, rh, C("#3aff7a"), em=1)
        cv.rect(rx + 2, ry + 2, rw - 4, rh - 4, C("#c8ffd8"), em=1)
    R.lights.append((gx + 15, gy + 15, C("#4af07a"), 40, 0.9))
    R.refl.append((gx, gx + 30, gy + 30, C("#4af07a"), 0.9))
    # light-box sign
    s = f.get("sign", "PHARMACY")
    sy = 128
    cv.rect(x0 + 10, sy, w - 20, 20, C("#2a3a32"))
    cv.rect(x0 + 12, sy + 2, w - 24, 16, C("#f4fff8"), em=1)
    sc, b = fit_scale(s, w - 30, 2)
    cv.text_c(x0 + w // 2, sy + (20 - 7 * sc) // 2, s, C("#1a8a4a"), sc, bold=b, em=1)
    R.lights.append((x0 + w // 2, sy + 10, C("#e0fff0"), w // 2, 0.5))
    R.refl.append((x0 + 12, x0 + w - 12, sy + 18, C("#e0fff0"), 0.6))
    # bright windows with shelves
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else x0 + w // 2
    fy = 154
    cv.rect(x0 + 6, fy, w - 12, FACADE_BOTTOM - fy, C("#3a4a44"))
    for (bx, bw) in ((x0 + 12, dx - 22 - (x0 + 12)), (dx + 22, x0 + w - 12 - (dx + 22))):
        if bw < 16:
            continue
        cv.vgrad(bx, fy + 4, bw, FACADE_BOTTOM - fy - 14, [C("#ffffff"), C("#e0f4f0"), C("#b0d8d0")], em=1)
        for sy_ in range(fy + 12, FACADE_BOTTOM - 12, 12):
            cv.hl(bx, sy_, bw, C("#8aa8a0"), em=1)
            for k in range(bx + 1, bx + bw - 3, 4):
                if rng.random() < 0.8:
                    cv.rect(k, sy_ - rng.randrange(4, 9), 3, 8, rng.choice(
                        [P["red"], P["blue"], P["mustard"], P["teal"], P["white"], C("#e890b0")]), em=1)
        cv.rect(bx - 1, FACADE_BOTTOM - 10, bw + 2, 10, C("#3a4a44"))
        R.refl.append((bx, bx + bw, fy, C("#e0fff0"), 0.4))
    R.accents[x0] = C("#2a9a5a")


@facade("arcade_front")
def f_arcade_front(R, x0, w, f):
    cv = R.cv
    rng = R.rng("arc", x0)
    top = 50
    roof_clear(cv, x0, w, top - 8)
    cv.rect(x0, top, w, FACADE_BOTTOM - top, C("#4a3a6a"))
    # checker band + chrome stripes
    for yy in (top + 4, 116):
        for xx in range(x0, x0 + w, 6):
            cv.rect(xx, yy, 6, 6, P["white"] if (xx // 6) % 2 else INK)
    cornice(cv, x0 + 2, w - 4, top - 6, C("#6a5a8a"))
    # giant marquee
    s = f.get("sign", "ARCADE")
    my, mh = top + 14, 46
    cv.rect(x0 + 10, my, w - 20, mh, C("#120c1e"))
    bulbs(cv, x0 + 11, my + 1, w - 22, mh - 2, step=4)
    words = s.split()
    if len(words) >= 2:
        neon_text(cv, R, x0 + w // 2, my + 6, words[0], P["n_pink"])
        neon_text(cv, R, x0 + w // 2, my + 24, " ".join(words[1:]), P["n_cyan"])
    else:
        neon_text(cv, R, x0 + w // 2, my + 16, s, P["n_pink"])
    for sx, sy in ((x0 + 26, my + 12), (x0 + w - 30, my + 30), (x0 + 40, my + 32), (x0 + w - 44, my + 10)):
        for ddx, ddy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
            cv.px(sx + ddx, sy + ddy, P["n_yellow"], em=1)
        cv.px(sx, sy, (255, 255, 255), em=1)
    # glowing windows full of cabinets
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else x0 + w // 2
    fy = 128
    cv.rect(x0 + 6, fy, w - 12, FACADE_BOTTOM - fy, C("#1e1a2e"))
    for (bx, bw) in ((x0 + 12, dx - 24 - (x0 + 12)), (dx + 24, x0 + w - 12 - (dx + 24))):
        if bw < 20:
            continue
        cv.vgrad(bx, fy + 4, bw, FACADE_BOTTOM - fy - 14, [C("#5a2a8a"), C("#2a1a4a")], em=1)
        for k in range(bx + 4, bx + bw - 18, 22):
            cab = rng.choice([C("#c03a3a"), C("#3a6ac0"), C("#2a2a32"), C("#e0b040")])
            cv.rect(k, fy + 22, 18, FACADE_BOTTOM - fy - 32, cab, em=1)
            cv.rect(k, fy + 18, 18, 6, dk(cab, 0.2), em=1)
            scr = rng.choice([P["n_cyan"], P["n_green"], P["n_pink"], P["n_yellow"]])
            cv.rect(k + 3, fy + 26, 12, 10, scr, em=1)
            cv.rect(k + 5, fy + 29, 4, 3, (255, 255, 255), em=1)
            cv.rect(k + 2, fy + 40, 14, 4, dk(cab, 0.35), em=1)
            R.lights.append((k + 9, fy + 31, scr, 16, 0.35))
        cv.hl(bx, fy + 4, bw, C("#ff80d0"), em=1)
        cv.rect(bx - 1, FACADE_BOTTOM - 10, bw + 2, 10, C("#2a2440"))
        R.refl.append((bx, bx + bw, fy + 10, C("#c060ff"), 0.6))
    R.accents[x0] = P["n_pink"]


@facade("fire_escape_wall")
def f_fire_escape_wall(R, x0, w, f):
    cv = R.cv
    rng = R.rng("few", x0)
    top = 14
    roof_clear(cv, x0, w, top - 8)
    floors = night_block(R, x0, w, top, rng, brick=BRICKS[3], lit_p=0.25)
    for k in range(2):
        fx = x0 + 40 + k * (w - 140)
        fire_escape(cv, fx, 64, [fy + 24 for fy in floors] + [floors[-1] + 62], bottom=FACADE_BOTTOM - 20)
    # ghost sign (faded painted ad, original)
    gx, gy = x0 + w // 2 - 60, top + 4
    cv.dither_blend(gx, gy, 120, 10, C("#e8d8b0"), 0.35)
    cv.text(gx + 6, gy + 2, "BELL SOAP CO", mix(C("#7a4a3e"), C("#e8d8b0"), 0.5), 1, bold=True)
    # ground floor: back doors, pipes, wall lamps
    cv.rect(x0, 160, w, FACADE_BOTTOM - 160, C("#4a3a3a"))
    tex_brick(cv, x0, 160, w, FACADE_BOTTOM - 160, base=C("#6a3a32"), seed=x0 + 9, calm=True)
    for dx in (x0 + 90, x0 + w - 110):
        deco_door(cv, dx, FACADE_BOTTOM, 20, 36, C("#3a4a5a"), frame=C("#5a5a66"), glass=False)
        wall_lamp(cv, R, dx + 10, 168, color=C("#ffd890"))
    drainpipe(cv, x0 + w // 2, top, FACADE_BOTTOM)
    for k in range(3):
        tag_scribble(cv, rng.randrange(x0 + 10, x0 + w - 40), rng.randrange(176, 200), rng)


@facade("alley_walls")
def f_alley_walls(R, x0, w, f):
    cv = R.cv
    rng = R.rng("aw", x0)
    roof_clear(cv, x0, w, 0)
    side = 120
    # back wall (dead end)
    bx0, bx1 = x0 + side, x0 + w - side
    tex_brick(cv, bx0, 20, bx1 - bx0, FACADE_BOTTOM - 20, base=C("#7a4038"), seed=seed_of(R.id, "back"),
              weather=0.5)
    cv.rect(bx0, 14, bx1 - bx0, 6, C("#9a9080"))
    # side walls (perspective trapezoids), brick textured then shaded
    tex_brick(cv, x0, 0, side, FACADE_BOTTOM, base=C("#6a3630"), seed=seed_of(R.id, "L"), weather=0.3)
    tex_brick(cv, bx1, 0, side, FACADE_BOTTOM, base=C("#6a3630"), seed=seed_of(R.id, "R"), weather=0.3)
    # clear sky above the walls' perspective top edges
    for xx in range(x0, bx0):
        t = (xx - x0) / side
        yt = int(t * 14)
        cv.clear(xx, 0, 1, yt)
        cv.px(xx, yt, C("#9a9080"))
    for xx in range(bx1, x0 + w):
        t = (x0 + w - 1 - xx) / side
        yt = int(t * 14)
        cv.clear(xx, 0, 1, yt)
        cv.px(xx, yt, C("#9a9080"))
    cv.clear(bx0, 0, bx1 - bx0, 14)
    # floor wedge on both sides (alley floor receding into the side walls)
    for xx in range(x0, bx0):
        t = (xx - x0) / side
        yb = FACADE_BOTTOM - int(t * 0)
        cv.blend(xx, 0, 1, FACADE_BOTTOM, C("#1a1424"), 0.35 - 0.2 * t)
    for xx in range(bx1, x0 + w):
        t = (x0 + w - 1 - xx) / side
        cv.blend(xx, 0, 1, FACADE_BOTTOM, C("#1a1424"), 0.45 - 0.2 * t)
    cv.vl(bx0, 14, FACADE_BOTTOM - 14, C("#2a1a20"))
    cv.vl(bx1 - 1, 14, FACADE_BOTTOM - 14, C("#2a1a20"))
    # fire escapes on side walls
    fire_escape(cv, x0 + 20, 70, [70, 120], c=C("#1e1a24"), ladder=False)
    fire_escape(cv, bx1 + 30, 70, [60, 112], c=C("#1e1a24"), ladder=False)
    # back door (lit) + steam vent + chain-link section
    dxc = x0 + w // 2
    deco_door(cv, dxc - 60, FACADE_BOTTOM, 22, 40, C("#3a4a3a"), frame=C("#5a5a66"), glass=False)
    wall_lamp(cv, R, dxc - 49, 162, color=C("#ffd890"))
    chainlink(cv, dxc + 30, 150, 80, FACADE_BOTTOM - 150, wire=C("#9aa0a8"), posts=40)
    cv.rect(bx0 + 10, 110, 24, 14, C("#3a3a46"))
    for yy in range(112, 124, 3):
        cv.hl(bx0 + 12, yy, 20, C("#5a5a66"))
    smoke_puff(cv, bx0 + 22, 100, 7, C("#9a9aa8"), rng)
    # graffiti on the back wall
    graffiti(cv, dxc - 30, 120, 70, 30, rng)
    # banner with sign text strung across
    s = f.get("sign", "ALLEY")
    sw = text_w(s, 2) + 24
    sx = dxc - sw // 2
    cv.line(x0 + 30, 40, sx, 54, C("#2a2630"))
    cv.line(sx + sw, 54, x0 + w - 30, 40, C("#2a2630"))
    cv.rect(sx, 50, sw, 26, C("#e8d8b0"))
    cv.rect(sx + 2, 52, sw - 4, 22, C("#c03a3a"))
    cv.text(sx + 12, 56, s, C("#fff0c0"), 2, shadow=C("#5a1a1a"))
    for k in range(sx, sx + sw, 8):
        cv.poly([(k, 76), (k + 8, 76), (k + 4, 80)], C("#e8d8b0"))
    R.lights.append((dxc, 64, C("#ffb070"), 50, 0.4))
    # crisscrossing string lights
    for (ax, ay, bx_, by_) in ((x0 + 10, 30, x0 + w - 10, 96), (x0 + 10, 96, x0 + w - 10, 30),
                               (x0 + 10, 60, x0 + w - 10, 60)):
        pts = cv.sag(ax, ay, bx_, by_, 18, C("#2a2630"))
        for i, (px_, py_) in enumerate(pts[::10]):
            col = [P["n_yellow"], P["n_pink"], P["n_cyan"], P["n_green"]][i % 4]
            cv.rect(px_, py_ + 1, 2, 2, col, em=1)
            if i % 2 == 0:
                R.lights.append((px_, py_ + 2, col, 12, 0.25))


@facade("rooftop_edge")
def f_rooftop_edge(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("roofe", x0)
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    py = 186
    # features behind the parapet
    if var == 0:
        tx = x0 + w // 2 - 40
        legs = 50
        wood = C("#7a5a3e")
        for lx in (tx + 6, tx + 36, tx + 66):
            cv.rect(lx, py - legs, 4, legs, C("#3a2e2a"))
        for k in range(0, 2):
            cv.line(tx + 6, py - 4 - k * 24, tx + 70, py - 24 - k * 24, C("#3a2e2a"))
            cv.line(tx + 70, py - 4 - k * 24, tx + 6, py - 24 - k * 24, C("#3a2e2a"))
        cv.rect(tx, py - legs - 4, 80, 4, C("#3a2e2a"))
        tex_planks_v(cv, tx + 4, py - legs - 50, 72, 46, wood, pw=4, seed=tx)
        for yy in (py - legs - 40, py - legs - 24, py - legs - 10):
            cv.hl(tx + 4, yy, 72, C("#3a2e2a"))
        cv.poly([(tx, py - legs - 50), (tx + 40, py - legs - 72), (tx + 80, py - legs - 50)], C("#5a4a3a"))
        cv.line(tx, py - legs - 50, tx + 40, py - legs - 72, C("#8a7a6a"))
        cv.vl(tx + 40, py - legs - 80, 8, C("#3a2e2a"))
        cv.rect(tx + 39, py - legs - 82, 3, 3, C("#ff3a3a"), em=1)
        # skylight
        sx = x0 + 60
        cv.poly([(sx, py), (sx + 50, py), (sx + 44, py - 14), (sx + 6, py - 14)], C("#5a5a66"))
        cv.poly([(sx + 4, py - 1), (sx + 46, py - 1), (sx + 41, py - 12), (sx + 9, py - 12)], C("#ffd890"), em=1)
        for k in range(sx + 12, sx + 44, 8):
            cv.vl(k, py - 12, 12, C("#5a5a66"))
        R.lights.append((sx + 25, py - 6, C("#ffd890"), 30, 0.5))
    elif var == 1:
        bx, bw, bh = x0 + 60, w - 120, 70
        by = 70
        for lx in range(bx + 20, bx + bw, 60):
            cv.rect(lx, by + bh, 4, py - by - bh, C("#3a3a46"))
            cv.line(lx, by + bh + 10, lx + 30, py, C("#3a3a46"))
        cv.hl(bx, by + bh + 14, bw, C("#3a3a46"))
        cv.rect(bx - 3, by - 3, bw + 6, bh + 6, C("#1a1424"))
        cv.vgrad(bx, by, bw, bh, [C("#ff6a9a"), C("#c03a6a"), C("#7a2a6a")], em=1)
        # fizz bottle + bubbles
        cv.rect(bx + 20, by + 18, 14, 40, C("#7af0c0"), em=1)
        cv.rect(bx + 24, by + 8, 6, 12, C("#7af0c0"), em=1)
        cv.rect(bx + 23, by + 6, 8, 3, C("#e0e0e0"), em=1)
        cv.rect(bx + 20, by + 30, 14, 10, C("#fff6e0"), em=1)
        for k in range(10):
            bxx = bx + 40 + rng.randrange(0, 40)
            byy = by + rng.randrange(6, bh - 6)
            cv.ellipse(bxx, byy, bxx + 3, byy + 3, C("#ffe0f0"), em=1)
        s = f.get("sign", "DRINK")
        sc, b = fit_scale(s, bw - 100, 2)
        cv.text(bx + 90, by + bh // 2 - 7 * sc // 2, s, C("#fff8e0"), sc, bold=b, shadow=C("#5a1a3a"), em=1)
        for lx in range(bx + 10, bx + bw, 50):
            cv.rect(lx, by + bh + 3, 4, 3, C("#2a2a32"))
            cv.line(lx + 2, by + bh + 3, lx + 6, by + bh - 2, C("#2a2a32"))
        R.lights.append((bx + bw // 2, by + bh // 2, C("#ff6a9a"), bw // 2, 0.8))
        R.refl.append((bx, bx + bw, by + bh, C("#ff6a9a"), 0.5))
    else:
        # stair bulkhead with door + antenna + pigeon coop
        hx = x0 + 70
        tex_brick(cv, hx, 120, 70, py - 120, base=C("#7a4038"), seed=hx, calm=True)
        cv.rect(hx - 3, 116, 76, 5, C("#8a8478"))
        deco_door(cv, hx + 24, py, 20, 36, C("#5a2a2a"), frame=C("#8a8478"), glass=False)
        wall_lamp(cv, R, hx + 34, 132, color=C("#ffd890"))
        ax = x0 + w - 120
        cv.vl(ax, 40, py - 40, C("#5a5a66"))
        for yy, ww in ((50, 30), (64, 22), (78, 14)):
            cv.hl(ax - ww // 2, yy, ww, C("#5a5a66"))
        cv.rect(ax - 1, 38, 3, 3, C("#ff3a3a"), em=1)
        cx = x0 + w // 2
        tex_planks_h(cv, cx - 30, 150, 60, py - 150, C("#8a7a6a"), ph=6, seed=cx)
        chainlink(cv, cx - 28, 154, 56, 20, wire=C("#c8c8d0"), posts=28, top_rail=False)
        cv.poly([(cx - 34, 150), (cx + 34, 150), (cx + 26, 140), (cx - 26, 140)], C("#4a4a56"))
    # neighbouring taller building edge / antennas for variety
    if var == 2:
        nx = x0 + w - 150
        tex_brick(cv, nx, 70, 150, py - 70, base=C("#6a4038"), seed=nx, weather=0.3)
        cv.rect(nx - 2, 66, 154, 5, C("#8a8478"))
        for wy in (84, 120, 156):
            for wx in range(nx + 14, nx + 140, 34):
                window(cv, R, wx, wy, 14, 20, lit=rng.random() < 0.5, frame=C("#b8ac98"), rng=rng)
        pts = cv.sag(x0 + 150, 150, nx, 128, 10, C("#c8c4bc"))
        for i, (px_, py_) in enumerate(pts[8::14]):
            col = rng.choice([P["white"], P["red"], P["blue"], P["mustard"]])
            cv.rect(px_ - 3, py_ + 1, 6, 8, col)
    if var in (0, 2):
        for ax in range(x0 + 20, x0 + w - 20, 190):
            if var == 0 and x0 + w // 2 - 60 < ax < x0 + w // 2 + 60:
                continue
            ah = rng.randrange(24, 44)
            cv.vl(ax, py - ah, ah, C("#5a5a66"))
            cv.hl(ax - 8, py - ah + 4, 17, C("#5a5a66"))
            cv.hl(ax - 5, py - ah + 9, 11, C("#5a5a66"))
            cv.line(ax, py - ah + 2, ax + 12, py - 2, C("#4a4a56"))
    # parapet wall
    tex_brick(cv, x0, py, w, FACADE_BOTTOM - py, base=C("#7a3a32"), seed=seed_of(R.id, x0, "par"), calm=True)
    cv.rect(x0, py - 4, w, 5, C("#8a8478"))
    cv.hl(x0, py - 4, w, C("#b8b0a0"))
    cv.hl(x0, py, w, C("#4a4440"))
    for xx in range(x0 + 30, x0 + w, 150):
        cv.rect(xx, py + 10, 10, 6, C("#2a2a32"))



# ============================================================================
# FACADES - Floodgate Road (storm night)
# ============================================================================
def floodgate_tower(cv, R, x, top, base, w=46):
    conc = C("#9a9a96")
    cv.rect(x, top, w, base - top, conc)
    tex_concrete(cv, x, top, w, base - top, conc, seed=x, panel=(w, 24), stains=True)
    cv.vl(x + w - 1, top, base - top, dk(conc, 0.4))
    cv.vl(x, top, base - top, lt(conc, 0.2))
    cv.rect(x - 4, top - 6, w + 8, 6, dk(conc, 0.2))
    cv.hl(x - 4, top - 6, w + 8, lt(conc, 0.1))
    # machinery hut on top
    cv.rect(x + 6, top - 20, w - 12, 14, C("#6a6a72"))
    cv.rect(x + 10, top - 16, 8, 6, C("#ffd890"), em=1)
    cv.rect(x + w - 18, top - 16, 8, 6, C("#ffd890"), em=1)
    cv.rect(x + w // 2 - 1, top - 30, 2, 10, C("#3a3a46"))
    cv.rect(x + w // 2 - 2, top - 33, 4, 3, C("#ff3a3a"), em=1)
    R.lights.append((x + w // 2, top - 31, C("#ff3a3a"), 14, 0.7))
    for wy in range(top + 14, base - 20, 30):
        cv.rect(x + w // 2 - 4, wy, 8, 10, C("#ffd890") if (wy // 30) % 2 else C("#2a3040"),
                em=1 if (wy // 30) % 2 else 0)


@facade("bridge_rail")
def f_bridge_rail(R, x0, w, f):
    cv = R.cv
    rng = R.rng("brail", x0)
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    water_y = 128
    # far bank silhouettes: low industrial shoreline with lights
    for xx in range(x0, x0 + w):
        hh = int(10 + 6 * math.sin(xx * 0.013) + 4 * math.sin(xx * 0.051))
        cv.vl(xx, water_y - hh, hh, C("#4a5464"))
    for _ in range(w // 40):
        bx = rng.randrange(x0, x0 + w - 30)
        bw = rng.randrange(16, 40)
        bh = rng.randrange(12, 30)
        cv.rect(bx, water_y - bh, bw, bh, C("#3e4858"))
        for k in range(bx + 2, bx + bw - 2, 5):
            if rng.random() < 0.25:
                cv.rect(k, water_y - bh + 4, 2, 2, C("#ffc870"), em=1)
    # river
    water(cv, R, x0, water_y, w, FACADE_BOTTOM - water_y, deep=C("#22384a"), mid=C("#3a5a70"),
          light=C("#7a98b0"), seed=f"{R.id}river", sparkle=False)
    # floodgate towers with gates between them
    towers = list(range(x0 + 160, x0 + w, 420))
    for i, tx in enumerate(towers):
        floodgate_tower(cv, R, tx, 36 + (i % 2) * 10, water_y + 20)
        if i + 1 < len(towers):
            gx0, gx1 = tx + 46, towers[i + 1]
            cv.rect(gx0, water_y - 18, gx1 - gx0, 26, C("#5a6470"))
            for k in range(gx0, gx1, 24):
                cv.vl(k, water_y - 18, 26, C("#3a4450"))
            cv.hl(gx0, water_y - 18, gx1 - gx0, C("#8a94a0"))
            cv.hl(gx0, water_y + 8, gx1 - gx0, C("#9ab0c0"))
            # catwalk + lamps over the gates
            cv.hl(gx0, water_y - 30, gx1 - gx0, C("#3a3a46"))
            for k in range(gx0, gx1, 6):
                cv.vl(k, water_y - 30, 12, C("#3a3a46"))
            for k in range(gx0 + 40, gx1, 120):
                cv.rect(k, water_y - 40, 4, 3, C("#ffb050"), em=1)
                R.lights.append((k + 2, water_y - 38, C("#ffb050"), 14, 0.5))
                R.refl.append((k, k + 4, water_y - 120, C("#ffb050"), 0.6))
    # sodium light reflections on the river (streaks)
    for k in range(x0 + 60, x0 + w, 160):
        for j in range(0, FACADE_BOTTOM - water_y - 20, 3):
            ww = rng.randrange(3, 9)
            cv.hl(k + rng.randrange(-3, 4), water_y + 10 + j, ww, C("#c89a5a"), em=0)
    # truss girders of the bridge (far side)
    steel = C("#4e6058")
    hi = lt(steel, 0.3)
    cv.rect(x0, 24, w, 7, steel)
    cv.hl(x0, 24, w, hi)
    cv.hl(x0, 30, w, dk(steel, 0.4))
    panel = 110
    for k in range((x0 // panel) * panel, x0 + w + panel, panel):
        cv.rect(k, 31, 6, FACADE_BOTTOM - 31, steel)
        cv.vl(k, 31, FACADE_BOTTOM - 31, hi)
        for j in range(6):
            cv.line(k + 6 + j, 31, k + panel // 2 + j, FACADE_BOTTOM - 26, steel)
            cv.line(k + panel - j, 31, k + panel // 2 - j + 6, FACADE_BOTTOM - 26, steel)
        for yy in range(36, FACADE_BOTTOM - 30, 12):
            cv.px(k + 2, yy, lt(steel, 0.5))
        cv.rect(k - 3, 22, 12, 12, dk(steel, 0.15))
    # deck parapet with balusters
    py = FACADE_BOTTOM - 26
    cv.rect(x0, py, w, 6, C("#8a8a86"))
    cv.hl(x0, py, w, C("#b0b0aa"))
    for k in range(x0, x0 + w, 8):
        cv.rect(k + 2, py + 6, 4, 14, C("#7a7a76"))
        cv.vl(k + 2, py + 6, 14, C("#9a9a96"))
    cv.rect(x0, FACADE_BOTTOM - 6, w, 6, C("#6a6a66"))
    cv.hl(x0, FACADE_BOTTOM - 6, w, C("#8a8a86"))
    # flood warning signs on the parapet
    for k in range(x0 + 300, x0 + w, 600):
        cv.rect(k, py - 20, 24, 18, C("#e0b040"))
        cv.rect(k + 1, py - 19, 22, 16, C("#f0c840"))
        cv.poly([(k + 4, py - 6), (k + 20, py - 6), (k + 12, py - 17)], INK)
        cv.poly([(k + 7, py - 8), (k + 17, py - 8), (k + 12, py - 14)], C("#f0c840"))
        cv.vl(k + 11, py - 2, 2, C("#3a3a46"))


@facade("pump_station")
def f_pump_station(R, x0, w, f):
    cv = R.cv
    rng = R.rng("pump", x0)
    top = 60
    roof_clear(cv, x0, w, top - 40)
    tex_brick(cv, x0, top, w, FACADE_BOTTOM - top, base=C("#8a5a4a"), seed=seed_of(R.id, x0), weather=0.6)
    cv.rect(x0, top - 6, w, 8, C("#7a7a76"))
    cv.hl(x0, top - 6, w, C("#a8a8a2"))
    # vent tower on roof
    vx = x0 + w // 2 - 30
    cv.rect(vx, top - 36, 60, 30, C("#6a6a72"))
    for yy in range(top - 32, top - 8, 4):
        cv.hl(vx + 4, yy, 52, C("#4a4a52"))
    cv.poly([(vx - 4, top - 36), (vx + 64, top - 36), (vx + 56, top - 44), (vx + 4, top - 44)], C("#4a4a56"))
    # tall arched windows with greenish work light
    for k in range(4):
        wx = x0 + 30 + k * (w - 60) // 4 + ((w - 60) // 4 - 30) // 2
        window(cv, R, wx, 84, 30, 50, lit=k % 2 == 0, frame=C("#c8c0b0"), arch=True,
               pal=[C("#e8fff0"), C("#a8e0c8"), C("#6aa090")], rng=None, deco=False)
        for yy in range(88, 132, 8):
            cv.hl(wx + 1, yy, 28, C("#c8c0b0"))
    # sign plate
    s = f.get("sign", "PUMP STATION")
    signboard(cv, x0 + w // 2 - 80, 142, 160, 18, s, C("#e8e4dc"), C("#22305a"), border=C("#3a3a46"))
    # big pipes exiting the wall into the ground
    for k, px_ in enumerate((x0 + 30, x0 + w - 70)):
        col = [C("#3a6a8a"), C("#6a7280")][k]
        cv.rect(px_, 166, 40, 14, col)
        cv.hl(px_, 167, 40, lt(col, 0.35))
        cv.hl(px_, 179, 40, dk(col, 0.4))
        cv.rect(px_ + 26, 166, 14, FACADE_BOTTOM - 166, col)
        cv.vl(px_ + 27, 166, FACADE_BOTTOM - 166, lt(col, 0.35))
        cv.vl(px_ + 39, 166, FACADE_BOTTOM - 166, dk(col, 0.4))
        cv.rect(px_ + 22, 186, 22, 4, dk(col, 0.25))
        cv.ellipse(px_ + 4, 158, px_ + 20, 174, P["red"])
        cv.ellipse(px_ + 8, 162, px_ + 16, 170, dk(col, 0.2))
        cv.line(px_ + 4, 166, px_ + 20, 166, P["red"])
    # amber warning beacon + overflow spout with falling water
    bx = x0 + w // 2
    cv.rect(bx - 4, 168, 8, 8, C("#ffb030"), em=1)
    cv.rect(bx - 5, 176, 10, 2, C("#3a3a46"))
    R.lights.append((bx, 172, C("#ffb030"), 30, 0.7))
    R.refl.append((bx - 4, bx + 4, 172, C("#ffb030"), 0.7))
    sx = x0 + w // 2 + 60
    cv.rect(sx, 182, 12, 6, C("#5a5a66"))
    for yy in range(188, FACADE_BOTTOM):
        cv.hl(sx + 3 + (yy % 3 == 0), yy, 6, C("#8ab0c8") if yy % 2 else C("#b8d0e0"))
    cv.ellipse(sx - 4, FACADE_BOTTOM - 4, sx + 16, FACADE_BOTTOM + 2, C("#a8c8e0"))
    deco_door(cv, x0 + 20 + (w - 60) // 2, FACADE_BOTTOM, 0, 0, C("#3a3a46")) if False else None


@facade("bait_shop")
def f_bait_shop(R, x0, w, f):
    cv = R.cv
    rng = R.rng("bait", x0)
    top = 104
    roof_clear(cv, x0, w, top - 22)
    # tin roof
    cv.poly([(x0 + 2, top), (x0 + w - 2, top), (x0 + w - 14, top - 18), (x0 + 14, top - 18)], C("#6a7078"))
    for k in range(x0 + 14, x0 + w - 14, 5):
        cv.vl(k, top - 17, 17, C("#8a9098"))
    cv.hl(x0 + 2, top, w - 4, C("#3a3e46"))
    tex_siding(cv, x0 + 6, top + 1, w - 12, FACADE_BOTTOM - top - 1, C("#5a8a9a"), pitch=5)
    # sign board
    s = f.get("sign", "BAIT")
    sw = text_w(s, 2) + 20
    signboard(cv, x0 + (w - sw) // 2, top - 40, sw, 22, s, C("#e8e4dc"), C("#c03a3a"), border=C("#2a2a32"))
    for k in (x0 + (w - sw) // 2 + 10, x0 + (w + sw) // 2 - 12):
        cv.rect(k, top - 18, 2, 18, C("#2a2a32"))
    # LIVE BAIT neon fish
    fx, fy = x0 + 40, top + 14
    cv.rect(fx - 8, fy - 4, 56, 22, C("#1a1424"))
    neon_text(cv, R, fx + 22, fy + 2, "LIVE", P["n_cyan"], gap=1)
    cv.ellipse(fx + 2, fy + 10, fx + 30, fy + 16, P["n_green"], em=1)
    cv.ellipse(fx + 4, fy + 11, fx + 28, fy + 15, C("#1a1424"))
    cv.poly([(fx + 30, fy + 13), (fx + 38, fy + 9), (fx + 38, fy + 17)], P["n_green"], em=1)
    R.lights.append((fx + 20, fy + 10, P["n_cyan"], 30, 0.7))
    R.refl.append((fx - 6, fx + 46, fy + 18, P["n_cyan"], 0.7))
    # lit window with rods
    doors = R.doors_in(x0, x0 + w)
    dx = doors[0]["x"] if doors else x0 + w // 2
    wx = dx + 30
    if wx + 50 < x0 + w:
        cv.rect(wx - 2, 136, 54, 40, C("#e8e4dc"))
        cv.vgrad(wx, 138, 50, 36, LIT, em=1)
        for k in range(wx + 4, wx + 46, 6):
            cv.line(k, 172, k + 3, 140, C("#5a3a20"), em=1)
        cv.vl(wx + 25, 138, 36, C("#e8e4dc"))
        R.lights.append((wx + 25, 156, LIT[1], 34, 0.6))
        R.refl.append((wx, wx + 50, 170, LIT[1], 0.5))
    # nets + buoys
    nx = x0 + 14
    for k in range(5):
        cv.line(nx + k * 6, top + 44, nx + k * 6 + 6, top + 84, C("#c8c0a0"))
        cv.line(nx + k * 6 + 12, top + 44, nx + k * 6 - 2, top + 84, C("#c8c0a0"))
    for bx_, by_, col in ((x0 + 20, top + 90, P["red"]), (x0 + 36, top + 96, P["orange"]),
                          (x0 + w - 24, top + 60, P["white"])):
        cv.ellipse(bx_, by_, bx_ + 9, by_ + 9, col)
        cv.hl(bx_ + 1, by_ + 4, 8, P["white"] if col != P["white"] else P["red"])
    R.accents[x0] = P["teal"]


@facade("floodgate_wall")
def f_floodgate_wall(R, x0, w, f):
    cv = R.cv
    rng = R.rng("fgw", x0)
    top = 30
    roof_clear(cv, x0, w, top - 14)
    conc = C("#8e8e8a")
    tex_concrete(cv, x0, top, w, FACADE_BOTTOM - top, conc, seed=x0, panel=(64, 40))
    # catwalk with railing on top
    cv.rect(x0, top - 2, w, 4, C("#3a3a46"))
    cv.hl(x0, top - 14, w, C("#3a3a46"))
    for k in range(x0, x0 + w, 8):
        cv.vl(k, top - 14, 12, C("#3a3a46"))
    # flood level markings
    mx = x0 + 18
    cv.rect(mx, 50, 14, 150, C("#e8e4dc"))
    for i, yy in enumerate(range(56, 196, 28)):
        cv.rect(mx, yy, 14, 3, P["red"] if i < 2 else C("#22305a"))
        cv.text(mx + 4, yy + 6, str(5 - i), C("#22305a"), 1)
    # huge steel gate
    gx0, gw = x0 + 60, w - 120
    gy0 = 54
    cv.rect(gx0 - 6, gy0 - 6, gw + 12, FACADE_BOTTOM - gy0 + 6, C("#4a4a52"))
    cv.rect(gx0, gy0, gw, FACADE_BOTTOM - gy0, C("#5a6a74"))
    for yy in range(gy0, FACADE_BOTTOM, 30):
        cv.rect(gx0, yy, gw, 5, C("#46545e"))
        cv.hl(gx0, yy, gw, C("#7a8a94"))
        for k in range(gx0 + 4, gx0 + gw, 10):
            cv.px(k, yy + 2, C("#9aaab4"))
    for k in range(gx0, gx0 + gw, gw // 4):
        cv.rect(k, gy0, 4, FACADE_BOTTOM - gy0, C("#46545e"))
        cv.vl(k, gy0, FACADE_BOTTOM - gy0, C("#7a8a94"))
    # rust streaks
    for _ in range(gw // 12):
        rx = rng.randrange(gx0, gx0 + gw)
        cv.vl(rx, rng.randrange(gy0, gy0 + 80), rng.randrange(10, 50), mix(P["rust"], C("#5a6a74"), 0.4))
    # hazard stripe edges
    for yy in range(gy0, FACADE_BOTTOM, 8):
        for ex in (gx0 - 6, gx0 + gw):
            cv.rect(ex, yy, 6, 4, P["yellow"])
            cv.rect(ex, yy + 4, 6, 4, C("#24242e"))
    # warning lights
    for lx in (gx0 + 10, gx0 + gw - 18):
        cv.rect(lx, gy0 - 16, 8, 8, C("#ff4a2a"), em=1)
        cv.rect(lx - 1, gy0 - 8, 10, 2, C("#3a3a46"))
        R.lights.append((lx + 4, gy0 - 12, C("#ff4a2a"), 30, 0.8))
        R.refl.append((lx, lx + 8, gy0 - 12, C("#ff4a2a"), 0.7))
    # stencil
    cv.text_c(gx0 + gw // 2, 100, "FLOODGATE 3", C("#e8e4dc"), 2, bold=False)
    cv.text_c(gx0 + gw // 2, 120, "KEEP CLEAR", P["yellow"], 1, bold=True)
    # drain outlets with trickles
    for k in range(x0 + 40, x0 + w, 220):
        cv.ellipse(k, 190, k + 12, 198, C("#24242e"))
        for yy in range(196, FACADE_BOTTOM):
            cv.px(k + 6 + (yy % 2), yy, C("#a8c8e0"))
    cv.dither_blend(x0, FACADE_BOTTOM - 30, w, 30, C("#2a3040"), 0.3)


CONTAINER_COLS = [C("#a8402e"), C("#2e5a8a"), C("#3a7a4a"), C("#c87a2a"), C("#7a7a86"), C("#8a2a4a"),
                  C("#c8a030")]


def container(cv, x, y, w, h, col, rng, code=True):
    cv.rect(x, y, w, h, dk(col, 0.4))
    tex_corrugated(cv, x + 2, y + 2, w - 4, h - 4, col, pitch=4)
    cv.hl(x, y, w, lt(col, 0.3))
    cv.rect(x, y, 3, h, dk(col, 0.25))
    cv.rect(x + w - 3, y, 3, h, dk(col, 0.45))
    cv.hl(x, y + h - 2, w, dk(col, 0.5))
    if code:
        cv.text(x + 8, y + 6, rng.choice(["BLW", "GRL", "OTH", "RVR", "MKT"]) + " " + str(rng.randrange(100, 999)),
                lt(col, 0.6), 1)
    if rng.random() < 0.4:
        for _ in range(3):
            rx = rng.randrange(x + 4, x + w - 4)
            cv.vl(rx, y + 2, rng.randrange(4, h - 4), mix(P["rust"], col, 0.4))


@facade("container_stack")
def f_container_stack(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("cont", x0, var)
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    # gantry crane silhouette in the back
    gx = x0 + w // 2 - 80
    gc = C("#5a6470")
    for lx in (gx, gx + 150):
        cv.rect(lx, 20, 8, FACADE_BOTTOM - 20, gc)
        for yy in range(26, FACADE_BOTTOM, 16):
            cv.line(lx, yy, lx + 8, yy + 16, dk(gc, 0.3))
    cv.rect(gx - 60, 14, 290, 10, gc)
    cv.hl(gx - 60, 14, 290, lt(gc, 0.3))
    for k in range(gx - 60, gx + 230, 10):
        cv.line(k, 23, k + 5, 15, dk(gc, 0.3))
    cv.rect(gx + 60, 24, 24, 12, C("#3a3a46"))
    cv.vl(gx + 72, 36, 40, C("#2a2a32"))
    cv.rect(gx - 58, 10, 4, 4, C("#ff3a3a"), em=1)
    cv.rect(gx + 226, 10, 4, 4, C("#ff3a3a"), em=1)
    R.lights.append((gx - 56, 12, C("#ff3a3a"), 12, 0.6))
    # stacks
    cw, ch = 124, 38
    xx = x0 - rng.randrange(0, 40)
    while xx < x0 + w:
        levels = rng.choice([2, 3, 3, 4]) if var == 0 else rng.choice([2, 3])
        for lv in range(levels):
            y = FACADE_BOTTOM - (lv + 1) * ch
            off = rng.choice([0, 0, 6, -6]) if lv else 0
            container(cv, xx + off, y, cw, ch, rng.choice(CONTAINER_COLS), rng)
        xx += cw + rng.choice([0, 0, 4, 30])
    # floodlight poles
    for k in range(x0 + 100, x0 + w, 300):
        cv.rect(k, 40, 3, FACADE_BOTTOM - 40, C("#3a3a46"))
        cv.rect(k - 8, 36, 19, 6, C("#2a2a32"))
        cv.rect(k - 6, 42, 15, 2, C("#f0f4ff"), em=1)
        R.lights.append((k + 1, 60, C("#e8f0ff"), 60, 0.5))


@facade("warehouse_fence")
def f_warehouse_fence(R, x0, w, f):
    cv = R.cv
    rng = R.rng("whf", x0)
    roof_clear(cv, x0, w, FACADE_BOTTOM)
    # Rook's warehouse behind the fence
    top = 56
    tex_corrugated(cv, x0, top, w, FACADE_BOTTOM - top, C("#7a8088"), pitch=5, seed=x0, rust=0.1)
    cv.poly([(x0, top), (x0 + w, top), (x0 + w, top - 12), (x0, top - 12)], C("#4a5058"))
    cv.hl(x0, top - 12, w, C("#8a9098"))
    for k in range(x0 + 20, x0 + w - 40, 70):
        lit = rng.random() < 0.4
        cv.rect(k, top + 12, 50, 14, C("#ffe8b0") if lit else C("#2a3040"), em=1 if lit else 0)
        for j in range(k + 10, k + 50, 10):
            cv.vl(j, top + 12, 14, C("#4a5058"))
    # lit loading door
    dx = x0 + w - 160
    cv.rect(dx, 120, 90, FACADE_BOTTOM - 120, C("#3a3e46"))
    cv.vgrad(dx + 4, 124, 82, FACADE_BOTTOM - 124, [C("#fff0c8"), C("#d8a060")], em=1)
    R.lights.append((dx + 45, FACADE_BOTTOM - 20, C("#ffd890"), 70, 0.6))
    # security lights on the wall
    for k in range(x0 + 60, x0 + w, 180):
        cv.rect(k, top + 34, 10, 5, C("#2a2a32"))
        cv.rect(k + 1, top + 39, 8, 2, C("#f0f4ff"), em=1)
        R.lights.append((k + 5, top + 50, C("#e8f0ff"), 36, 0.5))
    # fence
    fy = 104
    chainlink(cv, x0, fy, w, FACADE_BOTTOM - fy, wire=C("#a8acb4"), post=C("#5a6068"), posts=60)
    for k in range(x0, x0 + w + 1, 60):
        cv.line(k + 1, fy - 3, k + 8, fy - 12, C("#5a6068"))
    barbed(cv, x0, fy - 13, w)
    barbed(cv, x0, fy - 8, w)
    # big sign mounted on the fence
    s = f.get("sign", "PRIVATE PROPERTY")
    parts = s.split(" - ")
    sw = min(w - 80, max(text_w(p, 2) for p in parts) + 40)
    sx = x0 + 60
    sh = 22 + 18 * len(parts)
    cv.rect(sx - 2, 120, sw + 4, sh + 4, C("#2a2a32"))
    cv.rect(sx, 122, sw, sh, C("#ece8e0"))
    cv.rect(sx, 122, sw, 8, P["red"])
    cv.rect(sx, 122 + sh - 4, sw, 4, P["red"])
    for i, ptxt in enumerate(parts):
        sc, b = fit_scale(ptxt, sw - 16, 2)
        cv.text_c(sx + sw // 2, 134 + i * 18, ptxt, INK if i == 0 else P["red_d"], sc, bold=b)
    # camera
    cx = x0 + w - 40
    cv.rect(cx, 70, 3, 30, C("#3a3a46"))
    cv.rect(cx - 10, 66, 14, 7, C("#d8d8d8"))
    cv.px(cx - 9, 70, C("#ff3a3a"), em=1)


# ============================================================================
# FACADES - Rook's Warehouse (dim industrial)
# ============================================================================
def roof_truss_band(cv, x0, w, y1=40, open_top=True):
    """Top band: leave transparent (parallax shows high windows) behind truss members."""
    steel = C("#4a4a56")
    if open_top:
        cv.clear(x0, 0, w, y1)
    cv.rect(x0, y1 - 6, w, 6, steel)
    cv.hl(x0, y1 - 6, w, lt(steel, 0.25))
    cv.rect(x0, 2, w, 4, steel)
    for k in range((x0 // 40) * 40, x0 + w, 40):
        cv.line(k, 6, k + 20, y1 - 6, steel)
        cv.line(k + 20, y1 - 6, k + 40, 6, steel)
        cv.vl(k, 6, y1 - 12, dk(steel, 0.2))


def hanging_lamp(cv, R, x, y, col=None):
    col = col or C("#f0e8c8")
    cv.vl(x, 0, y, C("#2a2a32"))
    cv.poly([(x - 8, y + 6), (x + 8, y + 6), (x + 4, y), (x - 4, y)], C("#3a3a46"))
    cv.rect(x - 5, y + 6, 11, 2, col, em=1)
    R.lights.append((x, y + 30, col, 70, 0.55))


def hazard_band(cv, x, y, w, h=8):
    for xx in range(x - h, x + w, h * 2):
        cv.poly([(xx, y + h), (xx + h, y), (xx + 2 * h, y), (xx + h, y + h)], P["yellow"])
        cv.poly([(xx + h, y + h), (xx + 2 * h, y), (xx + 3 * h, y), (xx + 2 * h, y + h)], C("#24242e"))


@facade("loading_bay")
def f_loading_bay(R, x0, w, f):
    cv = R.cv
    rng = R.rng("lbay", x0)
    wall = C("#7a8088")
    tex_corrugated(cv, x0, 0, w, FACADE_BOTTOM, wall, pitch=5, seed=x0, rust=0.12)
    # upper band + canopy
    cv.rect(x0, 0, w, 24, C("#5a6068"))
    cv.text(x0 + 40, 6, "GREYLINE LOGISTICS", C("#c8ccd0"), 2, bold=False)
    cv.text(x0 + w - 300, 6, "GREYLINE LOGISTICS", C("#c8ccd0"), 2, bold=False)
    cv.rect(x0, 40, w, 10, C("#3a3e46"))
    cv.hl(x0, 40, w, C("#8a9098"))
    cv.dither_blend(x0, 50, w, 12, C("#101018"), 0.5)
    for k in range(x0 + 40, x0 + w, 80):
        cv.line(k, 24, k + 30, 40, C("#3a3e46"))
    # bays
    bw, gap = 88, 40
    n = 0
    xx = x0 + 30
    while xx + bw < x0 + w - 10:
        n += 1
        top = 86
        cv.rect(xx - 6, top - 6, bw + 12, FACADE_BOTTOM - top + 6, C("#3a3e46"))
        state = rng.random()
        if n == 3 or n == 8:
            # truck trailer backed into the bay
            cv.vgrad(xx, top, bw, FACADE_BOTTOM - top, [C("#14141c"), C("#22222c")])
            tx0 = xx + 4
            cv.rect(tx0, top + 6, bw - 8, FACADE_BOTTOM - top - 18, C("#c8ccd0"))
            cv.vl(tx0 + (bw - 8) // 2, top + 6, FACADE_BOTTOM - top - 18, C("#7a8088"))
            for k in range(tx0 + 4, tx0 + bw - 12, 6):
                cv.vl(k, top + 10, FACADE_BOTTOM - top - 28, C("#a8acb0"))
            for k in range(tx0, tx0 + bw - 8, 8):
                cv.rect(k, FACADE_BOTTOM - 22, 4, 3, P["red"])
                cv.rect(k + 4, FACADE_BOTTOM - 22, 4, 3, P["white"])
            cv.rect(tx0 + 4, FACADE_BOTTOM - 18, 6, 4, C("#ff3a3a"), em=1)
            cv.rect(tx0 + bw - 18, FACADE_BOTTOM - 18, 6, 4, C("#ff3a3a"), em=1)
            cv.rect(tx0 + bw // 2 - 12, FACADE_BOTTOM - 16, 16, 5, C("#e8e4dc"))
            cv.rect(xx, FACADE_BOTTOM - 12, bw, 2, C("#18181e"))
        elif state < 0.3:
            # open: dark interior with stacked boxes
            cv.vgrad(xx, top, bw, FACADE_BOTTOM - top, [C("#14141c"), C("#22222c")])
            for k in range(3):
                cv.rect(xx + 6 + k * 26, FACADE_BOTTOM - 40, 22, 22, C("#6a5038"))
                cv.hl(xx + 6 + k * 26, FACADE_BOTTOM - 40, 22, C("#8a6a4a"))
            cv.rect(xx, FACADE_BOTTOM - 18, bw, 4, C("#5a4a3a"))
            tex_corrugated(cv, xx, top, bw, 14, C("#c8b048"), pitch=3)
        else:
            tex_corrugated(cv, xx, top, bw, FACADE_BOTTOM - top - 12, C("#c8b048") if n % 3 else C("#9aa0a8"),
                           pitch=3)
            for yy in range(top + 10, FACADE_BOTTOM - 12, 10):
                cv.hl(xx, yy, bw, dk(C("#c8b048"), 0.25))
        # number plate + light
        cv.rect(xx + bw // 2 - 12, top - 22, 24, 14, P["yellow"])
        cv.text_c(xx + bw // 2, top - 19, f"{n:02d}", INK, 1, bold=True)
        cv.rect(xx + bw // 2 - 3, top - 32, 6, 4, C("#2a2a32"))
        cv.rect(xx + bw // 2 - 2, top - 28, 4, 2, C("#ffd890"), em=1)
        R.lights.append((xx + bw // 2, top - 20, C("#ffd890"), 36, 0.5))
        # dock bumpers + edge stripe
        for bx_ in (xx - 4, xx + bw - 4):
            cv.rect(bx_, FACADE_BOTTOM - 26, 8, 14, C("#18181e"))
        xx += bw + gap
    cv.rect(x0, FACADE_BOTTOM - 12, w, 12, C("#5a5a62"))
    hazard_band(cv, x0, FACADE_BOTTOM - 10, w, 6)
    cv.hl(x0, FACADE_BOTTOM - 12, w, C("#8a8a92"))


def shelving(cv, x, w, top, rng, var=0):
    up = C("#d07a2a")
    beam = C("#2e5a9a")
    levels = [top + 30, top + 72, top + 114, FACADE_BOTTOM - 8]
    for k in range(x, x + w, 80):
        cv.rect(k, top, 5, FACADE_BOTTOM - top, up)
        cv.vl(k, top, FACADE_BOTTOM - top, lt(up, 0.3))
        for yy in range(top + 4, FACADE_BOTTOM, 8):
            cv.px(k + 2, yy, dk(up, 0.5))
    for ly in levels:
        cv.rect(x, ly, w, 4, beam)
        cv.hl(x, ly, w, lt(beam, 0.3))
    # goods on each level
    for i in range(len(levels) - 1):
        y1 = levels[i + 1] if i + 1 < len(levels) else FACADE_BOTTOM
        y0 = levels[i] + 4
        for k in range(x, x + w - 5, 80):
            bx = k + 6
            while bx < k + 76:
                kind = rng.random()
                if var == 1 and kind < 0.4:
                    # barrels
                    bw = 14
                    cv.rect(bx, levels[i + 1] - 22 if i + 1 < len(levels) else y1 - 22, bw, 20,
                            rng.choice([C("#3a6ac0"), C("#4a4a56"), C("#2a7a4a")]))
                else:
                    bw = rng.randrange(14, 26)
                    bh = rng.randrange(12, 30)
                    yb = (levels[i + 1] if i + 1 < len(levels) else y1)
                    col = rng.choice([C("#8a6a4a"), C("#a07a50"), C("#7a5a3a"), C("#c8b898")])
                    cv.rect(bx, yb - bh, bw, bh, col)
                    cv.hl(bx, yb - bh, bw, lt(col, 0.2))
                    cv.vl(bx + bw - 1, yb - bh, bh, dk(col, 0.3))
                    cv.hl(bx, yb - bh + bh // 2, bw, C("#c8a060"))
                bx += bw + 2


@facade("warehouse_wall")
def f_warehouse_wall(R, x0, w, f):
    cv = R.cv
    var = f.get("variant", 0)
    rng = R.rng("wwall", x0, var)
    tex_corrugated(cv, x0, 0, w, FACADE_BOTTOM, C("#6a7078"), pitch=5, seed=x0)
    roof_truss_band(cv, x0, w, 40)
    shelving(cv, x0 + 10, w - 20, 54, rng, var)
    for k in range(x0 + 60, x0 + w, 200):
        hanging_lamp(cv, R, k, 46)
    hazard_band(cv, x0, FACADE_BOTTOM - 6, w, 6)
    # stencil aisle markers
    for i, k in enumerate(range(x0 + 30, x0 + w, 240)):
        cv.rect(k, 44, 30, 14, P["yellow"])
        cv.text_c(k + 15, 47, ("A" if var == 0 else "D") + str(i + 1), INK, 1, bold=True)


@facade("conveyor_wall")
def f_conveyor_wall(R, x0, w, f):
    cv = R.cv
    rng = R.rng("conv", x0)
    tex_corrugated(cv, x0, 0, w, FACADE_BOTTOM, C("#5e646c"), pitch=5, seed=x0)
    roof_truss_band(cv, x0, w, 40)
    # chutes from the ceiling
    for k in range(x0 + 60, x0 + w - 40, 160):
        cv.poly([(k, 40), (k + 30, 40), (k + 24, 110), (k + 6, 110)], C("#7a8088"))
        cv.vl(k + 6, 50, 60, C("#9aa0a8"))
        hazard_band(cv, k + 6, 104, 18, 4)
    # conveyor frame
    cy = 140
    cv.rect(x0, cy, w, 10, C("#2a2a32"))
    for k in range(x0, x0 + w, 8):
        cv.ellipse(k, cy + 1, k + 6, cy + 7, C("#6a6a76"))
        cv.px(k + 3, cy + 4, C("#9a9aa6"))
    cv.rect(x0, cy - 4, w, 4, C("#1a1a20"))
    for k in range(x0 + 10, x0 + w, 60):
        cv.rect(k, cy + 10, 6, FACADE_BOTTOM - cy - 10, C("#d07a2a"))
        cv.vl(k, cy + 10, FACADE_BOTTOM - cy - 10, lt(C("#d07a2a"), 0.3))
        cv.line(k + 6, cy + 14, k + 26, cy + 40, C("#d07a2a"))
    # boxes riding the belt
    k = x0 + 10
    while k < x0 + w - 30:
        bw = rng.randrange(18, 30)
        bh = rng.randrange(12, 22)
        col = rng.choice([C("#a07a50"), C("#8a6a4a"), C("#c8b898")])
        cv.rect(k, cy - 4 - bh, bw, bh, col)
        cv.hl(k, cy - 4 - bh, bw, lt(col, 0.2))
        cv.hl(k, cy - 4 - bh // 2, bw, C("#c8a060"))
        cv.vl(k + bw - 1, cy - 4 - bh, bh, dk(col, 0.3))
        k += bw + rng.randrange(14, 40)
    # control panel with lamps
    px_ = x0 + w // 2 - 30
    cv.rect(px_, 166, 60, 36, C("#4a5058"))
    cv.hl(px_, 166, 60, C("#7a8088"))
    for i, k in enumerate(range(px_ + 6, px_ + 56, 10)):
        col = [C("#ff3a3a"), C("#3aff6a"), C("#ffb030"), C("#3aff6a"), C("#4af0f0")][i % 5]
        cv.rect(k, 172, 5, 5, col, em=1)
    cv.rect(px_ + 8, 184, 44, 12, C("#1a2a1a"))
    cv.hl(px_ + 10, 188, 30, C("#3aff6a"), em=1)
    R.lights.append((px_ + 30, 176, C("#8affb0"), 30, 0.4))
    hanging_lamp(cv, R, x0 + w // 2, 46)
    hazard_band(cv, x0, FACADE_BOTTOM - 6, w, 6)


@facade("office_wall")
def f_office_wall(R, x0, w, f):
    cv = R.cv
    rng = R.rng("off", x0)
    # ceiling with fluorescent panels
    cv.rect(x0, 0, w, 30, C("#3a3e46"))
    for k in range(x0 + 20, x0 + w, 120):
        cv.rect(k, 12, 60, 6, C("#e8f4ff"), em=1)
        cv.hl(k, 18, 60, C("#8a9098"))
        R.lights.append((k + 30, 40, C("#e8f4ff"), 80, 0.5))
    cv.hl(x0, 30, w, C("#2a2a32"))
    # wall: upper painted, lower wood panelling
    cv.rect(x0, 31, w, FACADE_BOTTOM - 31, C("#8a9a8a"))
    cv.noise_tint(x0, 31, w, 150, rng, 3, 0.1)
    tex_planks_v(cv, x0, 160, w, FACADE_BOTTOM - 160, C("#6a4a34"), pw=10, seed=x0)
    cv.rect(x0, 156, w, 4, C("#4a3424"))
    cv.hl(x0, 156, w, C("#8a6a4a"))
    # office windows with blinds and filing cabinets behind
    for k in range(x0 + 40, x0 + w - 290, 220):
        ww = 150
        cv.rect(k - 3, 52, ww + 6, 100, C("#5a5a62"))
        cv.vgrad(k, 55, ww, 94, [C("#9ab0c0"), C("#6a8090")], em=1)
        for j in range(k + 6, k + ww - 20, 24):
            cv.rect(j, 110, 18, 39, C("#6a7078"), em=1)
            for yy in (116, 128, 140):
                cv.hl(j + 2, yy, 14, C("#3a4048"), em=1)
                cv.rect(j + 7, yy + 3, 4, 1, C("#a8acb0"), em=1)
        for yy in range(56, 100, 3):
            cv.hl(k, yy, ww, C("#a8b0b8"), em=1)
        cv.vl(k + ww // 2, 55, 94, C("#5a5a62"))
        R.lights.append((k + ww // 2, 100, C("#d8e8f0"), 80, 0.35))
    # HOLDING door
    s = f.get("sign", "OFFICE")
    dx = x0 + w - 110
    cv.rect(dx - 4, 120, 48, FACADE_BOTTOM - 120, C("#4a4a52"))
    cv.rect(dx, 124, 40, FACADE_BOTTOM - 124, C("#6a7078"))
    cv.rect(dx + 14, 132, 12, 14, C("#1a1a20"))
    for yy in range(133, 146, 3):
        cv.hl(dx + 14, yy, 12, C("#5a5a62"))
    cv.rect(dx + 32, 172, 4, 3, P["steel_l"])
    sw = text_w(s, 1, True) + 10
    signboard(cv, dx + 20 - sw // 2, 104, sw, 13, s, C("#c03a3a"), P["white"], border=C("#5a1a1a"))
    # clock + bulletin board + water cooler
    cv.ellipse(x0 + 20, 40, x0 + 34, 54, C("#2a2a32"))
    cv.ellipse(x0 + 22, 42, x0 + 32, 52, C("#f0f0e8"))
    cv.line(x0 + 27, 47, x0 + 27, 43, INK)
    cv.line(x0 + 27, 47, x0 + 30, 47, INK)
    bx = x0 + w - 220
    cv.rect(bx, 70, 70, 50, C("#8a6a4a"))
    cv.rect(bx + 3, 73, 64, 44, C("#c8a070"))
    for _ in range(7):
        notice(cv, bx + rng.randrange(4, 56), rng.randrange(75, 106), header=rng.choice([P["red"], P["blue"],
                                                                                         C("#3a3a46")]))
    cv.rect(x0 + w - 40, 166, 16, 30, C("#d8d8d8"))
    cv.rect(x0 + w - 38, 144, 12, 22, C("#7ab0e0"))
    cv.hl(x0 + w - 38, 146, 12, C("#a8d0f0"))
    cv.rect(x0, FACADE_BOTTOM - 4, w, 4, C("#2a2a32"))


@facade("crane_hall")
def f_crane_hall(R, x0, w, f):
    cv = R.cv
    rng = R.rng("ch", x0)
    tex_corrugated(cv, x0, 0, w, FACADE_BOTTOM, C("#5a5e66"), pitch=6, seed=x0)
    cv.blend(x0, 0, w, FACADE_BOTTOM, C("#1a1a24"), 0.25)
    roof_truss_band(cv, x0, w, 34)
    # crane runway beams + bridge crane
    gc = C("#d0a02a")
    cv.rect(x0, 48, w, 8, gc)
    cv.hl(x0, 48, w, lt(gc, 0.3))
    cv.hl(x0, 55, w, dk(gc, 0.4))
    for k in range(x0, x0 + w, 120):
        cv.rect(k + 4, 56, 10, FACADE_BOTTOM - 56, C("#4a4a56"))
        cv.vl(k + 4, 56, FACADE_BOTTOM - 56, C("#6a6a76"))
        cv.rect(k, 52, 18, 6, C("#3a3a46"))
    bx = x0 + w // 2 - 140
    cv.rect(bx, 60, 280, 14, gc)
    cv.hl(bx, 60, 280, lt(gc, 0.3))
    for k in range(bx, bx + 280, 14):
        cv.line(k, 61, k + 7, 73, dk(gc, 0.25))
    hazard_band(cv, bx, 74, 280, 4)
    cv.rect(bx + 120, 78, 40, 16, C("#3a3a46"))
    for yy in range(94, 150, 4):
        cv.rect(bx + 139, yy, 3, 3, C("#7a7a86"))
    cv.ellipse(bx + 132, 150, bx + 148, 166, C("#5a5a66"))
    cv.ellipse(bx + 136, 152, bx + 144, 160, C("#2a2a32"))
    # giant painted logo on the back wall
    s = f.get("sign", "BANNER")
    cv.text_c(x0 + w // 2, 100, s, mix(C("#5a5e66"), C("#c8ccd0"), 0.35), 4)
    # crates at the back wall
    for k in range(x0 + 10, x0 + w - 40, 70):
        for lv in range(rng.randrange(1, 3)):
            col = rng.choice([C("#8a6a4a"), C("#a07a50"), C("#6a5a4a")])
            yb = FACADE_BOTTOM - 30 - lv * 28
            cv.rect(k, yb, 40, 28, col)
            cv.hl(k, yb, 40, lt(col, 0.2))
            cv.line(k, yb, k + 39, yb + 27, dk(col, 0.25))
            cv.rect(k, yb, 40, 1, dk(col, 0.4))
            cv.vl(k + 39, yb, 28, dk(col, 0.35))
    # hanging banners
    for k in range(x0 + 40, x0 + w - 40, 220):
        bwid = 40
        cv.rect(k - 2, 80, bwid + 4, 4, C("#2a2a32"))
        cv.rect(k, 84, bwid, 96, C("#9a2028"))
        cv.rect(k + 3, 84, bwid - 6, 96, C("#b02a32"))
        cv.poly([(k, 180), (k + bwid, 180), (k + bwid, 190), (k + bwid // 2, 182), (k, 190)], C("#9a2028"))
        for i, ch in enumerate(s[:8]):
            cv.text_c(k + bwid // 2, 90 + i * 9, ch, C("#e8e4dc"), 1, bold=True)
        cv.ellipse(k + bwid // 2 - 7, 164, k + bwid // 2 + 7, 177, C("#e8e4dc"))
        cv.ellipse(k + bwid // 2 - 4, 167, k + bwid // 2 + 4, 174, C("#b02a32"))
    for k in range(x0 + 120, x0 + w, 280):
        hanging_lamp(cv, R, k, 40)
    hazard_band(cv, x0, FACADE_BOTTOM - 6, w, 6)



# ============================================================================
# INTERIORS (back wall y 0-196)
# ============================================================================
W_BOT = INT_WALL_BOTTOM


def int_shell(cv, x, w, wall, wains=None, rail_y=140, ceil=None, base=None, paper=None, seed=0):
    ceil = ceil or dk(wall, 0.45)
    cv.rect(x, 0, w, W_BOT, wall)
    if paper == "stripe":
        for xx in range(x, x + w, 8):
            cv.rect(xx, 14, 3, rail_y - 14, mix(wall, lt(wall, 0.3), 0.5))
    elif paper == "diamond":
        yy, xx = np.mgrid[14:rail_y, x:x + w]
        m = (((xx - x) + yy) % 12 == 0) | (((xx - x) - yy) % 12 == 0)
        cv.a[14:rail_y, x:x + w][m, :3] = dk(wall, 0.1)
    elif paper == "tile":
        for yy in range(14, rail_y, 8):
            cv.hl(x, yy, w, dk(wall, 0.12))
        for yy in range(14, rail_y, 8):
            for xx in range(x + ((yy // 8) % 2) * 4, x + w, 8):
                cv.vl(xx, yy, 8, dk(wall, 0.12))
    elif paper == "planks":
        tex_planks_h(cv, x, 14, w, rail_y - 14, wall, ph=8, seed=seed)
    # ceiling band
    cv.rect(x, 0, w, 14, ceil)
    cv.hl(x, 13, w, dk(ceil, 0.3))
    cv.dither_blend(x, 14, w, 6, (0, 0, 0), 0.25)
    if wains:
        tex_planks_v(cv, x, rail_y, w, W_BOT - rail_y, wains, pw=10, seed=seed)
        cv.rect(x, rail_y - 3, w, 4, dk(wains, 0.2))
        cv.hl(x, rail_y - 3, w, lt(wains, 0.3))
    base = base or dk(wains or wall, 0.4)
    cv.rect(x, W_BOT - 6, w, 6, base)
    cv.hl(x, W_BOT - 6, w, lt(base, 0.25))


def ceiling_lamps(cv, R, x, w, step=160, col=None, kind="pendant", skip=()):
    col = col or C("#fff0c0")
    for k in range(x + step // 2, x + w, step):
        if any(a <= k <= b for a, b in skip):
            continue
        if kind == "pendant":
            cv.vl(k, 0, 20, C("#2a2a32"))
            cv.poly([(k - 9, 28), (k + 9, 28), (k + 4, 20), (k - 4, 20)], C("#c03a3a"))
            cv.rect(k - 6, 28, 13, 2, col, em=1)
        else:
            cv.rect(k - 24, 4, 48, 5, C("#d8d8d8"))
            cv.rect(k - 22, 9, 44, 2, col, em=1)
        R.lights.append((k, 40, col, 90, 0.45))


def int_window(cv, R, x, y, w, h, scene="street", frame=None, blinds=False):
    frame = frame or C("#e8e4dc")
    cv.rect(x - 3, y - 3, w + 6, h + 6, frame)
    if scene == "street":       # sunset street outside
        cv.vgrad(x, y, w, h, [C("#e0a068"), C("#c87a54"), C("#6a425e")], em=1)
        for k in range(x, x + w, 22):
            hh = 10 + (k * 7) % 18
            cv.rect(k, y + h - hh, 20, hh, C("#6a3a4a"), em=1)
            for j in range(k + 3, k + 18, 6):
                cv.rect(j, y + h - hh + 4, 2, 3, C("#ffd890"), em=1)
    elif scene == "day":
        cv.vgrad(x, y, w, h, [C("#8ac8e8"), C("#c8e8f0")], em=1)
        for k in range(x, x + w, 18):
            hh = 14 + (k * 5) % 16
            cv.rect(k, y + h - hh, 16, hh, C("#c89a7a"), em=1)
            cv.poly([(k, y + h - hh), (k + 8, y + h - hh - 6), (k + 16, y + h - hh)], C("#a87a5a"), em=1)
    elif scene == "dusk":
        cv.vgrad(x, y, w, h, [C("#c86a3a"), C("#8a4040"), C("#5a2e40")], em=1)
        for k in range(x + 6, x + w, 34):
            cv.rect(k, y + h - 30, 6, 30, C("#4a2a2e"), em=1)
        cv.rect(x, y + h - 10, w, 10, C("#5a2a2e"), em=1)
    elif scene == "storm":
        cv.vgrad(x, y, w, h, [C("#2a3040"), C("#4a5466")], em=1)
        for k in range(x, x + w, 3):
            for j in range(y + (k * 7) % 9, y + h, 9):
                cv.px(k, j, C("#8a9ab0"), em=1)
        cv.rect(x, y + h - 8, w, 8, C("#1a2028"), em=1)
    elif scene == "night":
        cv.vgrad(x, y, w, h, [C("#1c1a3a"), C("#2c2a5a")], em=1)
        for k in range(x, x + w, 14):
            cv.rect(k, y + h - 16, 12, 16, C("#141228"), em=1)
            cv.px(k + 4, y + h - 10, P["n_pink"], em=1)
    cv.vl(x + w // 2, y, h, frame)
    cv.hl(x, y + h // 2, w, frame)
    if blinds:
        for yy in range(y, y + h // 3, 2):
            cv.hl(x, yy, w, C("#d8d0c0"), em=1)
    cv.rect(x - 4, y + h + 3, w + 8, 3, dk(frame, 0.15))
    R.lights.append((x + w // 2, y + h // 2, cv_get(cv, x + 2, y + h // 2), w, 0.3))


def wall_sign(cv, R, cx, y, s, col, neon=True, backing=None):
    if neon:
        m = neon_mask(s)
        if backing:
            cv.rect(cx - m.shape[1] // 2 - 8, y - 5, m.shape[1] + 16, m.shape[0] + 10, backing)
        neon_text(cv, R, cx, y, s, col)
    else:
        sc, b = fit_scale(s, 400, 2)
        cv.text_c(cx, y, s, col, sc, bold=b, shadow=dk(col, 0.6))


def shelf_items(cv, x, w, y, rng, palette, hmin=6, hmax=14, em=0, gap=1):
    cv.rect(x, y, w, 3, C("#6a4a30"))
    cv.hl(x, y, w, C("#9a7a50"))
    k = x + 1
    while k < x + w - 4:
        iw = rng.randrange(3, 7)
        ih = rng.randrange(hmin, hmax)
        col = rng.choice(palette)
        cv.rect(k, y - ih, iw, ih, col, em=em)
        cv.vl(k, y - ih, ih, lt(col, 0.25), em=em)
        k += iw + gap


def clock(cv, x, y, r=7):
    cv.ellipse(x - r, y - r, x + r, y + r, C("#2a2a32"))
    cv.ellipse(x - r + 2, y - r + 2, x + r - 2, y + r - 2, C("#f4f0e4"))
    cv.line(x, y, x, y - r + 3, INK)
    cv.line(x, y, x + r - 4, y, INK)


def room_title(R):
    n = R.d.get("name", "")
    for suf in (" Diner", " Center"):
        if n.endswith(suf):
            n = n[: -len(suf)]
    return n.upper()


@facade("diner_interior")
def i_diner(R, x0, w, f):
    cv = R.cv
    rng = R.rng("idiner", x0)
    int_shell(cv, x0, w, C("#b8e0d0"), wains=None, rail_y=150, ceil=C("#5a6a6a"))
    # checker band + chrome rail + red lower wall
    cv.rect(x0, 150, w, W_BOT - 150, C("#c03a3a"))
    for xx in range(x0, x0 + w, 6):
        cv.rect(xx, 144, 6, 6, P["white"] if (xx // 6) % 2 else INK)
    cv.rect(x0, 142, w, 2, P["steel_l"])
    cv.rect(x0, 150, w, 2, P["steel_l"])
    for yy in range(158, W_BOT - 6, 8):
        cv.hl(x0, yy, w, dk(P["red"], 0.15))
    # windows on the left with blinds (sunset street)
    int_window(cv, R, x0 + 20, 40, 110, 70, "street", frame=P["steel_l"], blinds=True)
    # neon name sign
    wall_sign(cv, R, x0 + 250, 30, room_title(R), P["n_pink"], backing=C("#2a1a2a"))
    # menu boards
    for k, items in enumerate((("BURGER", "FRIES", "MALT"), ("PIE", "COFFEE", "EGGS"))):
        mx = x0 + 190 + k * 110
        cv.rect(mx, 56, 96, 40, C("#3a2a22"))
        cv.rect(mx + 2, 58, 92, 36, C("#1e1e24"))
        for i, it in enumerate(items):
            cv.text(mx + 6, 61 + i * 11, it, C("#f0e8d0"), 1)
            cv.text(mx + 70, 61 + i * 11, str(rng.randrange(1, 5)) + str(rng.choice([0, 5])) + "C"
                    if False else f"{rng.randrange(1, 4)}.{rng.choice([0, 2, 5])}0", P["yellow"], 1)
    # kitchen pass-through with cook bell and plates
    kx = x0 + 420
    cv.rect(kx - 4, 50, 170, 74, P["steel"])
    cv.vgrad(kx, 54, 162, 66, [C("#f0d8a8"), C("#d8a870"), C("#a07048")], em=1)
    # cook silhouette + hanging pans
    cv.ellipse(kx + 118, 70, kx + 130, 82, C("#7a5040"), em=1)
    cv.rect(kx + 120, 66, 8, 5, C("#f4f0e8"), em=1)
    cv.rect(kx + 114, 82, 20, 22, C("#e8e4dc"), em=1)
    for px_ in range(kx + 20, kx + 60, 12):
        cv.vl(px_ + 4, 54, 6, C("#3a3a46"), em=1)
        cv.ellipse(px_, 60, px_ + 8, 66, C("#4a4a56"), em=1)
    cv.rect(kx + 10, 70, 30, 20, C("#d8d8d8"), em=1)   # hood/fridge
    cv.rect(kx + 60, 84, 40, 6, C("#5a5a62"), em=1)    # grill
    for sx in (kx + 66, kx + 80, kx + 94):
        for sy in range(66, 82, 3):
            cv.px(sx + (sy // 3) % 2, sy, C("#fffaf0"), em=1)
    cv.rect(kx - 6, 120, 174, 6, P["steel_l"])
    cv.hl(kx - 6, 120, 174, (240, 244, 250))
    cv.ellipse(kx + 120, 114, kx + 130, 120, C("#e0b040"))
    for px_ in (kx + 20, kx + 50):
        cv.ellipse(px_, 116, px_ + 18, 121, C("#f4f4f0"))
        cv.ellipse(px_ + 4, 115, px_ + 12, 118, C("#c86a3a"))
    R.lights.append((kx + 80, 90, C("#ffd08a"), 100, 0.5))
    clock(cv, x0 + 160, 30)
    # pie case on the back counter + coffee machine
    cv.rect(x0 + 160, W_BOT - 30, 46, 24, P["steel_l"])
    cv.rect(x0 + 162, W_BOT - 28, 42, 18, C("#e8f4f8"))
    for k in range(x0 + 166, x0 + 200, 12):
        cv.ellipse(k, W_BOT - 18, k + 10, W_BOT - 12, C("#d8a050"))
        cv.hl(k + 2, W_BOT - 18, 6, C("#f0d090"))
    cv.rect(x0 + 230, W_BOT - 40, 22, 34, C("#5a5a62"))
    cv.rect(x0 + 233, W_BOT - 36, 16, 8, C("#2a2a32"))
    cv.px(x0 + 236, W_BOT - 32, P["red"], em=1)
    ceiling_lamps(cv, R, x0, w, 160, skip=((x0 + 170, x0 + 330),))


@facade("garage_interior")
def i_garage(R, x0, w, f):
    cv = R.cv
    rng = R.rng("igar", x0)
    cv.rect(x0, 0, w, W_BOT, C("#a8a090"))
    tex_brick(cv, x0, 14, w, W_BOT - 14, base=C("#b0a894"), shadow=C("#948a76"), hi=C("#c8c0aa"),
              mortar=C("#8a8270"), seed=x0, bw=12, bh=6, calm=True)
    cv.rect(x0, 0, w, 14, C("#4a4a52"))
    cv.dither_blend(x0, 14, w, 6, (0, 0, 0), 0.3)
    cv.rect(x0, 100, w, 3, C("#3a6ac0"))
    # closed roll-up door with window strip (dusk outside)
    dx = x0 + w - 200
    cv.rect(dx - 4, 40, 180, W_BOT - 40, C("#5a5a66"))
    tex_corrugated(cv, dx, 44, 172, W_BOT - 44, C("#c8c4b8"), pitch=3)
    cv.rect(dx + 10, 70, 152, 10, C("#3a3a46"))
    for k in range(dx + 12, dx + 160, 19):
        cv.rect(k, 71, 17, 8, C("#f0a060"), em=1)
    cv.rect(dx + 80, W_BOT - 14, 12, 4, C("#3a3a46"))
    # pegboard with tool silhouettes
    px_ = x0 + 30
    cv.rect(px_, 40, 150, 80, C("#b8956a"))
    for yy in range(44, 118, 6):
        for xx in range(px_ + 4, px_ + 148, 6):
            cv.px(xx, yy, C("#8a6a4a"))
    tools = [(12, 40), (30, 30), (46, 44), (62, 34), (80, 40), (98, 28), (116, 46), (132, 36)]
    for i, (tx, th) in enumerate(tools):
        col = [C("#c03a3a"), C("#5a5a66"), C("#e0b040"), C("#3a6ac0")][i % 4]
        cv.rect(px_ + tx, 50, 3, th, P["steel"])
        cv.rect(px_ + tx - 2, 50 + th, 7, 8, col)
    cv.rect(px_ + 10, 104, 130, 10, C("#5a3a20"))
    # wall sign from room name
    s = room_title(R)
    signboard(cv, x0 + 200, 24, text_w(s, 2) + 20, 22, s, C("#e8dcc0"), C("#b02e34"), border=C("#3a3a46"))
    # car on a lift (left back)
    lx = x0 + 210
    cv.rect(lx + 10, 130, 6, W_BOT - 130, C("#c03a3a"))
    cv.rect(lx + 130, 130, 6, W_BOT - 130, C("#c03a3a"))
    cv.rect(lx, 126, 146, 6, C("#5a5a66"))
    car = C("#e0b040")
    cv.rect(lx + 8, 96, 130, 30, car)
    cv.rect(lx + 30, 78, 80, 20, dk(car, 0.1))
    cv.rect(lx + 36, 82, 30, 14, C("#bfe0f0"))
    cv.rect(lx + 72, 82, 32, 14, C("#bfe0f0"))
    cv.ellipse(lx + 18, 112, lx + 40, 134, C("#18181e"))
    cv.ellipse(lx + 106, 112, lx + 128, 134, C("#18181e"))
    cv.ellipse(lx + 24, 118, lx + 34, 128, P["steel_l"])
    cv.ellipse(lx + 112, 118, lx + 122, 128, P["steel_l"])
    cv.hl(lx + 8, 104, 130, lt(car, 0.3))
    # calendar poster + work lights
    poster(cv, x0 + 190, 60, 22, 30, rng)
    for k in (x0 + 120, x0 + 360, x0 + 540):
        cv.vl(k, 0, 24, C("#2a2a32"))
        cv.rect(k - 8, 24, 17, 4, C("#3a3a46"))
        cv.rect(k - 6, 28, 13, 2, C("#fff4d0"), em=1)
        R.lights.append((k, 40, C("#fff0c0"), 100, 0.4))
    cv.rect(x0, W_BOT - 6, w, 6, C("#5a5650"))


@facade("gym_interior")
def i_gym(R, x0, w, f):
    cv = R.cv
    rng = R.rng("igym", x0)
    tex_brick(cv, x0, 0, w, W_BOT, base=C("#9a5040"), seed=x0, calm=True)
    cv.rect(x0, 110, w, W_BOT - 110, C("#3a5a8a"))
    cv.hl(x0, 110, w, C("#e8e4dc"))
    cv.hl(x0, 113, w, C("#c03a3a"))
    cv.rect(x0, 0, w, 14, C("#3a3a46"))
    # high windows
    for k in range(x0 + 20, x0 + w, 110):
        cv.rect(k - 2, 22, 64, 24, C("#e8e4dc"))
        cv.vgrad(k, 24, 60, 20, [C("#ffe8b0"), C("#f0b070")], em=1)
        for j in range(k + 15, k + 60, 15):
            cv.vl(j, 24, 20, C("#e8e4dc"))
        R.lights.append((k + 30, 40, C("#ffe0a0"), 60, 0.3))
    # banner with sign
    s = f.get("sign", "TRAIN HARD")
    sc, b = fit_scale(s, w - 120, 2)
    bw = text_w(s, sc, b) + 30
    bx = x0 + (w - bw) // 2
    cv.rect(bx, 56, bw, 26, C("#e8e4dc"))
    cv.rect(bx + 2, 58, bw - 4, 22, C("#c03a3a"))
    cv.text(bx + 15, 69 - 7 * sc // 2, s, C("#fff0c0"), sc, bold=b, shadow=C("#5a1a1a"))
    for k in (bx, bx + bw - 4):
        cv.rect(k, 52, 4, 4, C("#2a2a32"))
    # lockers on the right
    lx = x0 + w - 130
    for k in range(5):
        cv.rect(lx + k * 22, 118, 20, W_BOT - 124, C("#5a7a8a"))
        cv.vl(lx + k * 22 + 19, 118, W_BOT - 124, C("#3a5a6a"))
        for yy in (124, 128, 132):
            cv.hl(lx + k * 22 + 5, yy, 10, C("#3a5a6a"))
        cv.px(lx + k * 22 + 15, 150, P["steel_l"])
    # trophies shelf + posters
    shelf_items(cv, x0 + 240, 120, 106, rng, [C("#e0b040"), C("#c8c8d0"), C("#c87a3a")], 6, 14)
    for k in range(3):
        poster(cv, x0 + 250 + k * 40, 124, 28, 38, rng, palette=[P["red"], P["mustard"], P["navy"], P["cream"]])
    clock(cv, x0 + 220, 30)
    # boxing ring at back-left (apron on the floor, ropes in front of wall)
    rx0, rx1 = x0 + 10, x0 + 220
    ry = W_BOT + 26
    cv.rect(rx0, W_BOT + 6, rx1 - rx0, 20, C("#2a5a9a"))
    cv.hl(rx0, W_BOT + 6, rx1 - rx0, C("#4a7aba"))
    cv.rect(rx0, ry, rx1 - rx0, 6, C("#1e3a6a"))
    for pxx in (rx0, rx1 - 6):
        cv.rect(pxx, 120, 6, ry - 120, C("#c8c8d0"))
        cv.vl(pxx, 120, ry - 120, P["white"])
        cv.rect(pxx - 1, 118, 8, 6, C("#c03a3a"))
    for i, yy in enumerate((132, 150, 168)):
        cv.rect(rx0 + 6, yy, rx1 - rx0 - 12, 2, [C("#c03a3a"), P["white"], C("#3a6ac0")][i])
    # speed bag platform
    sx = x0 + 400
    cv.rect(sx, 120, 40, 6, C("#5a3a20"))
    cv.vl(sx + 20, 126, 6, C("#2a2a32"))
    cv.ellipse(sx + 15, 132, sx + 25, 146, C("#c03a3a"))
    cv.rect(x0, W_BOT - 6, w, 6, C("#2a3a5a"))


@facade("noodle_interior")
def i_noodle(R, x0, w, f):
    cv = R.cv
    rng = R.rng("inood", x0)
    int_shell(cv, x0, w, C("#d8b890"), wains=C("#7a4a2a"), rail_y=140, ceil=C("#4a2a1e"), paper="planks",
              seed=x0)
    # kitchen pass with steam and pots
    kx = x0 + 200
    cv.rect(kx - 4, 40, 300, 90, C("#5a2a1e"))
    cv.vgrad(kx, 44, 292, 82, [C("#f0d0a0"), C("#d8a060"), C("#a06838")], em=1)
    for k in range(kx + 20, kx + 280, 60):
        cv.rect(k, 92, 40, 24, C("#9aa2b0"), em=1)
        cv.hl(k, 92, 40, C("#d8dce4"), em=1)
        cv.rect(k - 2, 90, 44, 3, C("#6a7280"), em=1)
        for sx in range(k + 6, k + 36, 8):
            for sy in range(60, 90, 3):
                cv.px(sx + int(2 * math.sin(sy * 0.4 + sx)), sy, C("#fffaf0"), em=1)
    cv.rect(kx - 6, 126, 304, 6, C("#7a4a2a"))
    cv.hl(kx - 6, 126, 304, C("#a87a50"))
    R.lights.append((kx + 150, 90, C("#ffc070"), 150, 0.5))
    # menu strips
    for i, it in enumerate(("NOODLES", "DUMPLING", "BROTH", "TEA")):
        mx = kx + 6 + i * 72
        cv.rect(mx, 18, 64, 18, C("#c03a3a"))
        cv.rect(mx + 1, 19, 62, 16, C("#e8d8b0"))
        cv.text_c(mx + 32, 24, it, C("#5a1a1a"), 1)
    # name sign (left) + round window
    s = room_title(R)
    signboard(cv, x0 + 20, 26, 150, 24, s, C("#1a1220"), C("#f0c040"), border=C("#c03a3a"))
    cv.ellipse(x0 + 50, 62, x0 + 130, 136, C("#7a4a2a"))
    cv.ellipse(x0 + 54, 66, x0 + 126, 132, C("#c03a3a"))
    cv.ellipse(x0 + 58, 70, x0 + 122, 128, C("#8ac8e8"), em=1)
    cv.rect(x0 + 58, 110, 64, 18, C("#c89a7a"), em=1)
    cv.ellipse(x0 + 54, 66, x0 + 126, 132, C("#7a4a2a")) if False else None
    cv.vl(x0 + 90, 70, 58, C("#7a4a2a"))
    cv.hl(x0 + 58, 99, 64, C("#7a4a2a"))
    # lanterns
    for k in (x0 + 186, x0 + 512, x0 + 600):
        cv.vl(k, 0, 18, C("#2a2a32"))
        cv.ellipse(k - 8, 18, k + 8, 36, C("#e04a3a"), em=1)
        cv.hl(k - 5, 18, 11, C("#f0c040"), em=1)
        cv.hl(k - 5, 36, 11, C("#f0c040"), em=1)
        for yy in (23, 28, 33):
            cv.hl(k - 7, yy, 15, C("#c03a2a"), em=1)
        cv.vl(k, 37, 5, C("#f0c040"), em=1)
        R.lights.append((k, 27, C("#ff7a4a"), 40, 0.4))
    # shelf with bowls
    shelf_items(cv, x0 + 530, 90, 150, rng, [C("#e8e4dc"), C("#3a6ac0"), C("#c03a3a")], 4, 8)
    shelf_items(cv, x0 + 530, 90, 172, rng, [C("#e8e4dc"), C("#2a5a3a"), C("#e0b040")], 4, 8)


@facade("bookshop_interior")
def i_books(R, x0, w, f):
    cv = R.cv
    rng = R.rng("ibook", x0)
    int_shell(cv, x0, w, C("#5a3a28"), ceil=C("#2a1a12"), rail_y=190)
    spines = [C("#7a2030"), C("#22305a"), C("#2a5a3a"), C("#a87a20"), C("#5a2a6a"), C("#7a5030"),
              C("#c8b898"), C("#3a6a7a"), C("#9a4a2a"), C("#4a4a56")]
    # tall bookcases
    cases = [(x0 + 10, 180), (x0 + 210, 120), (x0 + 450, 180)]
    for (bx, bw) in cases:
        cv.rect(bx, 16, bw, W_BOT - 22, C("#4a2a18"))
        cv.rect(bx + 3, 18, bw - 6, W_BOT - 26, C("#2a1810"))
        for sy in range(46, W_BOT - 6, 30):
            shelf_items(cv, bx + 3, bw - 6, sy, rng, spines, 14, 24)
            # occasional leaning book
            if rng.random() < 0.5:
                lx = bx + rng.randrange(10, bw - 20)
                cv.line(lx, sy - 1, lx + 8, sy - 20, rng.choice(spines))
        cv.rect(bx, 14, bw, 4, C("#6a4a30"))
        cv.hl(bx, 14, bw, C("#8a6a4a"))
        cv.vl(bx, 16, W_BOT - 22, C("#6a4a30"))
    # rolling ladder
    lx = x0 + 120
    cv.line(lx, 20, lx + 30, W_BOT - 2, C("#8a6a40"))
    cv.line(lx + 14, 20, lx + 44, W_BOT - 2, C("#8a6a40"))
    for k in range(10):
        t = k / 10
        cv.hl(int(lx + 30 * t), int(26 + (W_BOT - 30) * t), 15, C("#a87a50"))
    cv.hl(x0 + 10, 18, 180, C("#c8a040"))
    # window (canal market day) + name sign + reading lamp
    wx = x0 + 220
    int_window(cv, R, wx + 10, 40, 100, 64, "day", frame=C("#6a4a30"))
    s = room_title(R)
    sw = text_w(s, 1, True) + 16
    signboard(cv, wx + 60 - sw // 2, 114, sw, 14, s, C("#2a5a3a"), C("#f0d890"), border=C("#c8a040"))
    cv.vl(wx + 60, 130, 20, C("#2a2a32"))
    cv.poly([(wx + 50, 150), (wx + 70, 150), (wx + 64, 140), (wx + 56, 140)], C("#2a7a4a"))
    cv.rect(wx + 54, 150, 13, 2, C("#fff0c0"), em=1)
    R.lights.append((wx + 60, 160, C("#ffe0a0"), 60, 0.5))
    clock(cv, wx + 60, 168, 6)


@facade("canteen_interior")
def i_canteen(R, x0, w, f):
    cv = R.cv
    rng = R.rng("icant", x0)
    int_shell(cv, x0, w, C("#e8e0c8"), rail_y=120, ceil=C("#5a5a52"), paper="tile")
    cv.rect(x0, 120, w, W_BOT - 120, C("#5a8a7a"))
    cv.hl(x0, 120, w, C("#3a6a5a"))
    for yy in range(126, W_BOT - 6, 8):
        cv.hl(x0, yy, w, C("#4e7e6e"))
    # serving hatch
    hx = x0 + 230
    cv.rect(hx - 4, 40, 240, 70, C("#8a9098"))
    cv.vgrad(hx, 44, 232, 62, [C("#f0dcb0"), C("#d8a870"), C("#a87850")], em=1)
    for k in range(hx + 16, hx + 220, 50):
        cv.rect(k, 84, 34, 18, C("#9aa2b0"), em=1)
        cv.hl(k, 84, 34, C("#d8dce4"), em=1)
        for sx in range(k + 6, k + 30, 9):
            for sy in range(62, 82, 3):
                cv.px(sx + (sy // 3) % 2, sy, C("#fffaf0"), em=1)
    cv.rect(hx - 6, 106, 244, 6, P["steel_l"])
    R.lights.append((hx + 116, 80, C("#ffd090"), 130, 0.5))
    # chalkboard menu
    s = room_title(R)
    cv.rect(x0 + 30, 24, 160, 86, C("#6a4a30"))
    cv.rect(x0 + 34, 28, 152, 78, C("#2a3a32"))
    cv.text_c(x0 + 110, 32, s, C("#f0e8d0"), 1, bold=True)
    for i, (it, pr) in enumerate((("STEW", "1.20"), ("PIE + MASH", "1.50"), ("TEA", "0.30"), ("TOAST", "0.40"))):
        cv.text(x0 + 42, 48 + i * 12, it, C("#e8e4dc"), 1)
        cv.text(x0 + 150, 48 + i * 12, pr, C("#f0c040"), 1)
    # safety poster + clock + window (dusk yard)
    cv.rect(x0 + 490, 30, 40, 52, C("#e8e4dc"))
    cv.rect(x0 + 492, 32, 36, 12, P["yellow"])
    cv.poly([(x0 + 500, 74), (x0 + 520, 74), (x0 + 510, 54)], P["red"])
    cv.vl(x0 + 510, 60, 8, P["white"])
    clock(cv, x0 + 210, 30)
    int_window(cv, R, x0 + 550, 40, 70, 60, "dusk")
    # lockers
    for k in range(4):
        cv.rect(x0 + 30 + k * 22, 126, 20, W_BOT - 132, C("#7a8a9a"))
        cv.vl(x0 + 49 + k * 22, 126, W_BOT - 132, C("#5a6a7a"))
        for yy in (132, 136):
            cv.hl(x0 + 35 + k * 22, yy, 10, C("#5a6a7a"))
    ceiling_lamps(cv, R, x0, w, 200, kind="tube")


@facade("switch_interior")
def i_switch(R, x0, w, f):
    cv = R.cv
    rng = R.rng("isw", x0)
    int_shell(cv, x0, w, C("#c8b898"), wains=C("#6a4a30"), rail_y=120, ceil=C("#3a3028"), seed=x0)
    # big windows over the yard at dusk
    for k in range(x0 + 20, x0 + w - 60, 130):
        int_window(cv, R, k, 22, 110, 70, "dusk", frame=C("#e8e4dc"))
    # track diagram board with lamps
    bx = x0 + w // 2 - 150
    cv.rect(bx, 96, 300, 22, C("#2a2a32"))
    cv.rect(bx + 2, 98, 296, 18, C("#1e2a3a"))
    cv.hl(bx + 6, 106, 288, C("#e8e4dc"))
    for k in range(bx + 20, bx + 290, 50):
        cv.line(k, 106, k + 20, 101, C("#e8e4dc"))
        cv.line(k + 20, 101, k + 40, 101, C("#e8e4dc"))
    for i, k in enumerate(range(bx + 12, bx + 296, 22)):
        col = [C("#ff3a3a"), C("#3aff6a"), C("#ffd040")][i % 3]
        cv.rect(k, 108, 3, 3, col, em=1)
    R.lights.append((bx + 150, 107, C("#a0ffb0"), 120, 0.3))
    # bell, telephone, logbook shelf
    cv.ellipse(x0 + 30, 128, x0 + 44, 140, C("#c8a040"))
    cv.rect(x0 + 36, 124, 2, 4, C("#2a2a32"))
    cv.rect(x0 + w - 70, 130, 22, 28, C("#2a2a32"))
    cv.rect(x0 + w - 68, 132, 18, 6, C("#1a1a20"))
    cv.ellipse(x0 + w - 66, 142, x0 + w - 52, 152, C("#3a3a46"))
    shelf_items(cv, x0 + 80, 100, 150, rng, [C("#7a2030"), C("#22305a"), C("#2a5a3a"), C("#a87a20")], 10, 18)
    # wall-mounted cabinet with keys
    cv.rect(x0 + 220, 130, 50, 40, C("#5a3a20"))
    cv.rect(x0 + 223, 133, 44, 34, C("#3a2a1a"))
    for k in range(x0 + 227, x0 + 265, 7):
        cv.rect(k, 140, 3, 6, C("#c8a040"))
    ceiling_lamps(cv, R, x0, w, 260)


@facade("arcade_interior")
def i_arcade(R, x0, w, f):
    cv = R.cv
    rng = R.rng("iarc", x0)
    cv.rect(x0, 0, w, W_BOT, C("#2a2040"))
    # neon stripes
    for yy, col in ((40, P["n_pink"]), (44, P["n_cyan"])):
        cv.rect(x0, yy, w, 2, col, em=1)
    cv.rect(x0, 0, w, 14, C("#141020"))
    for k in range(x0 + 20, x0 + w, 80):
        cv.rect(k, 6, 40, 3, C("#e0e0ff"), em=1)
    # star sprinkle wallpaper
    for _ in range(w // 6):
        sx = rng.randrange(x0, x0 + w)
        sy = rng.randrange(50, 120)
        cv.px(sx, sy, rng.choice([C("#5a4a8a"), C("#7a5aa0"), C("#4a6a9a")]))
    # name sign
    s = room_title(R).split()[0]
    wall_sign(cv, R, x0 + w // 2, 18, s, P["n_yellow"], backing=C("#141020"))
    # back row of cabinets (behind props)
    k = x0 + 10
    while k < x0 + w - 30:
        cab = rng.choice([C("#c03a3a"), C("#3a6ac0"), C("#2a2a32"), C("#e0b040"), C("#7a4aa0")])
        cw = 26
        cv.rect(k, 70, cw, W_BOT - 76, dk(cab, 0.2))
        cv.rect(k + 1, 66, cw - 2, 10, cab)
        scr = rng.choice([P["n_cyan"], P["n_green"], P["n_pink"], P["n_yellow"], C("#ff8a3a")])
        cv.rect(k + 4, 80, cw - 8, 20, C("#101018"))
        cv.rect(k + 5, 81, cw - 10, 18, mix(scr, C("#101018"), 0.3), em=1)
        for _ in range(4):
            cv.rect(k + rng.randrange(6, cw - 8), rng.randrange(83, 96), 2, 2, (255, 255, 255), em=1)
        cv.rect(k + 3, 104, cw - 6, 6, dk(cab, 0.4))
        cv.px(k + 8, 106, P["red"], em=1)
        cv.px(k + 14, 106, P["n_yellow"], em=1)
        cv.rect(k + 1, 66, cw - 2, 3, lt(cab, 0.4), em=1)
        R.lights.append((k + cw // 2, 90, scr, 30, 0.4))
        k += cw + 4
    # high score board
    hx = x0 + w - 170
    cv.rect(hx, 120, 150, 60, C("#101018"))
    cv.rect(hx + 2, 122, 146, 56, C("#141428"))
    cv.text_c(hx + 75, 126, "HIGH SCORES", P["n_pink"], 1, em=1)
    for i, (nm, sc) in enumerate((("LAC", "98450"), ("PIP", "61200"), ("MRV", "40010"), ("ELI", "33300"))):
        cv.text(hx + 20, 138 + i * 9, nm, P["n_cyan"], 1, em=1)
        cv.text(hx + 80, 138 + i * 9, sc, P["n_yellow"], 1, em=1)
    # prize shelf (behind counter area)
    shelf_items(cv, x0 + 420, 150, 150, rng, [C("#ff8ab0"), C("#8ad0ff"), C("#ffe070"), C("#a0f070")], 8, 16)
    shelf_items(cv, x0 + 420, 150, 176, rng, [C("#ff8ab0"), C("#8ad0ff"), C("#ffe070"), C("#ffffff")], 8, 16)
    cv.rect(x0, W_BOT - 6, w, 6, C("#141020"))
    cv.hl(x0, W_BOT - 6, w, P["n_pink"], em=1)


@facade("pharmacy_interior")
def i_pharmacy(R, x0, w, f):
    cv = R.cv
    rng = R.rng("iph", x0)
    int_shell(cv, x0, w, C("#eef2f0"), rail_y=170, ceil=C("#a8b0b0"))
    cv.rect(x0, 170, w, W_BOT - 170, C("#3a9a7a"))
    # shelving units full of boxes
    goods = [P["red"], P["blue"], P["mustard"], P["teal"], P["white"], C("#e890b0"), C("#7ab0e0"), P["green"]]
    for bx in (x0 + 10, x0 + 450):
        cv.rect(bx, 30, 180, 160, C("#d8dcdc"))
        for sy in range(56, 190, 26):
            shelf_items(cv, bx + 3, 174, sy, rng, goods, 8, 16)
            cv.rect(bx + 3, sy, 174, 3, C("#b8c0c0"))
    # dispensary window + sign + green cross
    dx = x0 + 230
    cv.rect(dx, 60, 180, 90, C("#c8d0d0"))
    cv.vgrad(dx + 4, 64, 172, 82, [C("#ffffff"), C("#d8f0e8")], em=1)
    shelf_items(cv, dx + 10, 160, 110, rng, goods, 6, 12, em=1)
    shelf_items(cv, dx + 10, 160, 136, rng, goods, 6, 12, em=1)
    sign = "PHARMACY"
    cv.rect(dx + 10, 30, 160, 22, C("#2a3a32"))
    cv.rect(dx + 12, 32, 156, 18, C("#f4fff8"), em=1)
    cv.text_c(dx + 90, 34, sign, C("#1a8a4a"), 2, em=1)
    cx = dx - 14
    for (rx, ry, rw, rh) in ((cx - 4, 30, 8, 22), (cx - 11, 37, 22, 8)):
        cv.rect(rx, ry, rw, rh, C("#3aff7a"), em=1)
    R.lights.append((cx, 41, C("#4af07a"), 40, 0.6))
    ceiling_lamps(cv, R, x0, w, 160, col=C("#f0fff8"), kind="tube")


@facade("bait_interior")
def i_bait(R, x0, w, f):
    cv = R.cv
    rng = R.rng("ibait", x0)
    int_shell(cv, x0, w, C("#8a7458"), rail_y=196, ceil=C("#3a3028"), paper="planks", seed=x0)
    # stormy window
    int_window(cv, R, x0 + 250, 40, 120, 70, "storm", frame=C("#5a4a3a"))
    # rod rack
    rx = x0 + 30
    cv.rect(rx, 150, 150, 6, C("#5a3a20"))
    cv.rect(rx, 40, 150, 4, C("#5a3a20"))
    for k in range(rx + 8, rx + 150, 14):
        cv.line(k, 150, k + 4, 44, C("#3a2a1a"))
        cv.px(k + 4, 44, P["steel_l"])
        cv.rect(k - 1, 140, 4, 6, rng.choice([P["red"], P["mustard"], C("#2a2a32")]))
    # mounted fish trophy
    fx = x0 + 420
    cv.rect(fx, 40, 70, 30, C("#5a3a20"))
    cv.ellipse(fx + 6, 46, fx + 54, 64, C("#6a8a6a"))
    cv.poly([(fx + 52, 55), (fx + 66, 46), (fx + 66, 64)], C("#5a7a5a"))
    cv.px(fx + 14, 52, INK)
    for k in range(fx + 20, fx + 50, 5):
        cv.px(k, 58, C("#9ab09a"))
    # nets + life ring + lantern
    for k in range(6):
        cv.line(x0 + 520 + k * 8, 20, x0 + 530 + k * 8, 120, C("#c8c0a0"))
        cv.line(x0 + 560 + k * 4, 20, x0 + 510 + k * 8, 120, C("#c8c0a0"))
    cv.ellipse(x0 + 200, 70, x0 + 236, 106, P["red"])
    cv.ellipse(x0 + 208, 78, x0 + 228, 98, C("#8a7458"))
    for (a0, a1) in ((210, 72), (232, 86), (214, 100), (200, 84)):
        cv.rect(x0 + a0, a1, 5, 5, P["white"])
    s = room_title(R)
    signboard(cv, x0 + 250, 120, 120, 20, s, C("#e8e4dc"), C("#c03a3a"), border=C("#2a2a32"))
    # tackle shelf
    shelf_items(cv, x0 + 420, 200 - 40, 140 + 30, rng, [C("#3a6a5a"), C("#c86a3a"), C("#3a4a6a"), C("#e0b040")],
                8, 14)
    shelf_items(cv, x0 + 420, 200 - 40, 140, rng, [C("#3a6a5a"), C("#c86a3a"), C("#3a4a6a"), C("#e0b040")], 8, 14)
    for k in (x0 + 140, x0 + 480):
        cv.vl(k, 0, 18, C("#2a2a32"))
        cv.rect(k - 5, 18, 11, 12, C("#3a3028"))
        cv.rect(k - 3, 20, 7, 8, C("#ffc870"), em=1)
        R.lights.append((k, 30, C("#ffc870"), 110, 0.6))



# ============================================================================
# PARALLAX far layers (960x220, horizontally tileable)
# ============================================================================
PW, PH = 960, 220


def wrapped(fn, x, *a, **k):
    for off in (-PW, 0, PW):
        fn(x + off, *a, **k)


def p_cloud(cv, x, y, w, h, base, hi, sh, rng):
    """Chunky pixel cloud: bumps lit from upper-left, flat shaded base."""
    n = max(3, w // 12)
    bumps = []
    for i in range(n):
        cx = x + int((i + 0.5) * w / n)
        r = max(3, int(h * (0.4 + 0.6 * math.sin(math.pi * (i + 0.5) / n))) + rng.randrange(-2, 3))
        bumps.append((cx, r))
    for cx, r in bumps:
        wrapped(lambda xx, r=r: cv.ellipse(xx - r, y + h - 2 * r, xx + r, y + h, hi), cx)
    for cx, r in bumps:
        wrapped(lambda xx, r=r: cv.ellipse(xx - r + 2, y + h - 2 * r + 2, xx + r, y + h, base), cx)
    wrapped(lambda xx: cv.rect(xx, y + h - 5, w, 5, base), x)
    wrapped(lambda xx: cv.rect(xx + 3, y + h - 2, w - 6, 2, sh), x)


def p_streak(cv, x, y, w, c, c2=None):
    wrapped(lambda xx: cv.rect(xx, y, w, 2, c), x)
    if c2:
        wrapped(lambda xx: cv.rect(xx + 6, y + 2, w - 12, 1, c2), x)


def skyline_layer(cv, rng, y_base, hmin, hmax, col, lit=None, lit_p=0.15, kinds=("flat", "gable", "chimney"),
                  wmin=18, wmax=46, top_detail=True):
    x = 0
    while x < PW:
        bw = rng.randrange(wmin, wmax)
        bh = rng.randrange(hmin, hmax)
        k = rng.choice(kinds)
        top = y_base - bh

        def draw(xx, bw=bw, bh=bh, k=k, top=top):
            cv.rect(xx, top, bw, PH - top, col)
            if k == "gable":
                cv.poly([(xx, top), (xx + bw // 2, top - bw // 3), (xx + bw - 1, top)], col)
            elif k == "chimney":
                cv.rect(xx + bw // 4, top - 8, 4, 8, col)
                cv.rect(xx + bw // 2 + 4, top - 6, 3, 6, col)
            elif k == "tower":
                cv.rect(xx + bw // 2 - 2, top - 20, 5, 20, col)
                cv.poly([(xx + bw // 2 - 4, top - 20), (xx + bw // 2, top - 30), (xx + bw // 2 + 4, top - 20)], col)
            elif k == "tank":
                cv.rect(xx + 4, top - 14, 12, 10, col)
                cv.rect(xx + 5, top - 4, 2, 4, col)
                cv.rect(xx + 13, top - 4, 2, 4, col)
                cv.poly([(xx + 3, top - 14), (xx + 10, top - 19), (xx + 17, top - 14)], col)
            elif k == "stack":
                cv.rect(xx + bw // 2 - 3, top - 40, 7, 40, col)
            elif k == "antenna":
                cv.rect(xx + bw // 2, top - 22, 1, 22, col)
                cv.rect(xx + bw // 2 - 3, top - 16, 7, 1, col)
        wrapped(draw, x)
        if lit is not None:
            for wy in range(top + 4, PH - 4, 6):
                for wx in range(x + 3, x + bw - 3, 5):
                    if rng.random() < lit_p:
                        c = lit if not isinstance(lit, list) else rng.choice(lit)
                        wrapped(lambda xx, wy=wy: cv.rect(xx, wy, 2, 2, c), wx)
        x += bw + rng.randrange(0, 4)


def gen_parallax():
    out = {}
    # ---------------- Old Quarter: warm sunset ----------------
    cv = Canvas(PW, PH)
    rng = rng_of("par", "oq")
    cv.vgrad(0, 0, PW, PH, [C("#f0b070"), C("#ec9e64"), C("#e08a5a"), C("#a8606a"), C("#7a4a6a")], levels=22)
    # sun low behind the roofs with banded clouds crossing it
    sx, sy = 640, 112
    for off in (-PW, 0, PW):
        cv.ellipse(sx + off - 34, sy - 34, sx + off + 34, sy + 34, C("#f8d890"))
        cv.ellipse(sx + off - 28, sy - 28, sx + off + 28, sy + 28, C("#fff0b8"))
    for yy in range(sy - 4, sy + 34, 7):
        wrapped(lambda xx, yy=yy: cv.rect(xx - 40, yy, 80, 2, C("#f0a070")), sx)
    for _ in range(14):
        p_streak(cv, rng.randrange(0, PW), rng.randrange(16, 110), rng.randrange(40, 140), C("#f8c890"),
                 C("#d07a6a"))
    for _ in range(8):
        p_streak(cv, rng.randrange(0, PW), rng.randrange(60, 130), rng.randrange(60, 160), C("#c86a6a"),
                 C("#9a5068"))
    skyline_layer(cv, rng, 168, 20, 60, C("#a86070"), kinds=("flat", "gable", "tower", "tank", "chimney"))
    skyline_layer(cv, rng, 196, 18, 54, C("#6a3a52"), lit=[C("#ffc870"), C("#ffe0a0")], lit_p=0.08,
                  kinds=("flat", "gable", "chimney", "chimney", "tank"))
    for _ in range(6):
        bx, by = rng.randrange(0, PW), rng.randrange(20, 80)
        wrapped(lambda xx: (cv.line(xx - 3, by, xx, by + 2, C("#5a3048")), cv.line(xx, by + 2, xx + 3, by,
                                                                                    C("#5a3048"))), bx)
    out["old_quarter"] = cv
    # ---------------- Canal Market: bright day ----------------
    cv = Canvas(PW, PH)
    rng = rng_of("par", "cm")
    cv.vgrad(0, 0, PW, PH, [C("#8ac8e8"), C("#a8d8ee"), C("#c8e8f0")], levels=18)
    for _ in range(9):
        p_cloud(cv, rng.randrange(0, PW), rng.randrange(8, 90), rng.randrange(50, 120), rng.randrange(12, 22),
                C("#f4fbff"), C("#ffffff"), C("#c8dcea"), rng)
    # hills
    for xx in range(PW):
        h1 = int(40 + 12 * math.sin(2 * math.pi * xx / PW * 2) + 6 * math.sin(2 * math.pi * xx / PW * 5 + 1))
        cv.vl(xx, PH - 60 - h1 + 40, PH, C("#8ab8a8"))
    for xx in range(PW):
        h2 = int(24 + 8 * math.sin(2 * math.pi * xx / PW * 3 + 2) + 4 * math.sin(2 * math.pi * xx / PW * 7))
        cv.vl(xx, PH - 30 - h2, PH, C("#6aa090"))
    skyline_layer(cv, rng, 200, 14, 40, C("#b8c8cc"), kinds=("gable", "gable", "tower", "flat"), wmin=14, wmax=30)
    skyline_layer(cv, rng, 214, 12, 34, C("#98aab4"), kinds=("gable", "gable", "chimney"), wmin=14, wmax=28)
    for _ in range(8):
        bx, by = rng.randrange(0, PW), rng.randrange(20, 110)
        wrapped(lambda xx: (cv.line(xx - 3, by, xx, by + 2, C("#f8f8f8")), cv.line(xx, by + 2, xx + 3, by,
                                                                                    C("#f8f8f8"))), bx)
    out["canal_market"] = cv
    # ---------------- Ironworks: orange dusk, smoke ----------------
    cv = Canvas(PW, PH)
    rng = rng_of("par", "iy")
    cv.vgrad(0, 0, PW, PH, [C("#e07a3a"), C("#c86a3a"), C("#a04a40"), C("#7a3a4a")], levels=20)
    for _ in range(10):
        p_streak(cv, rng.randrange(0, PW), rng.randrange(10, 100), rng.randrange(60, 180), C("#f09a5a"),
                 C("#b05a40"))
    # smoke plumes from tall stacks
    stacks = [rng.randrange(0, PW) for _ in range(5)]
    for sxp in stacks:
        top = rng.randrange(60, 100)
        wrapped(lambda xx, top=top: cv.rect(xx, top, 9, PH - top, C("#5a2a34")), sxp)
        wrapped(lambda xx, top=top: cv.rect(xx - 1, top, 11, 3, C("#4a2230")), sxp)
        for k in range(8):
            r = 6 + k * 2
            px_ = sxp + 4 + k * 12
            py_ = top - 8 - k * 5
            col = mix(C("#8a5a5a"), C("#c88a6a"), k / 8)
            wrapped(lambda xx, r=r, py_=py_, col=col: cv.ellipse(xx - r, py_ - r // 2, xx + r, py_ + r // 2, col),
                    px_)
    skyline_layer(cv, rng, 180, 20, 50, C("#7a3a44"), kinds=("flat", "gable", "stack", "flat"), wmin=24, wmax=60)
    # gantry cranes + pylons
    for gx in (120, 520, 800):
        def crane(xx):
            c = C("#5a2834")
            cv.rect(xx, 100, 4, 100, c)
            cv.rect(xx + 60, 100, 4, 100, c)
            cv.rect(xx - 20, 96, 110, 5, c)
            for k in range(xx - 20, xx + 90, 8):
                cv.line(k, 100, k + 4, 96, c)
        wrapped(crane, gx)
    for px_ in range(0, PW, 240):
        def pylon(xx):
            c = C("#4a2230")
            cv.line(xx, 200, xx + 10, 110, c)
            cv.line(xx + 20, 200, xx + 10, 110, c)
            cv.hl(xx + 2, 126, 17, c)
            cv.hl(xx + 4, 140, 13, c)
            for k in range(130, 200, 14):
                cv.line(xx + 3, k, xx + 17, k + 12, c)
        wrapped(pylon, px_)
        for k in range(240):
            yy = 128 + int(14 * 4 * (k / 240) * (1 - k / 240))
            wrapped(lambda xx, yy=yy: cv.px(xx, yy, C("#4a2230")), px_ + 10 + k)
    skyline_layer(cv, rng, 206, 14, 40, C("#4a2230"), lit=C("#ffa050"), lit_p=0.06,
                  kinds=("flat", "flat", "gable", "chimney"), wmin=30, wmax=70)
    out["ironworks"] = cv
    # ---------------- Neon Mile: night city ----------------
    cv = Canvas(PW, PH)
    rng = rng_of("par", "nm")
    cv.vgrad(0, 0, PW, PH, [C("#1c1a3a"), C("#22204a"), C("#2c2a5a"), C("#4a2a5a")], levels=18)
    for _ in range(140):
        sx, sy = rng.randrange(0, PW), rng.randrange(0, 120)
        c = rng.choice([C("#8a88b0"), C("#c8c8e8"), C("#5a5880")])
        cv.px(sx, sy, c)
        if rng.random() < 0.08:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                cv.px(sx + dx, sy + dy, C("#6a68a0"))
    mx, my = 760, 40
    cv.ellipse(mx - 12, my - 12, mx + 12, my + 12, C("#f0eccc"))
    cv.ellipse(mx - 6, my - 15, mx + 16, my + 8, C("#1c1a3a"))
    skyline_layer(cv, rng, 150, 40, 110, C("#2a2850"), lit=[C("#5a5aa0"), C("#8a7ac0")], lit_p=0.06,
                  kinds=("flat", "antenna", "tower", "flat"), wmin=24, wmax=50)
    skyline_layer(cv, rng, 190, 30, 90, C("#1a1834"), lit=[C("#ffd870"), C("#7af0f0"), C("#ff9ad0")], lit_p=0.12,
                  kinds=("flat", "antenna", "tank", "flat"), wmin=26, wmax=56)
    # faint neon haze at the base
    for yy in range(PH - 40, PH):
        t = (yy - (PH - 40)) / 40
        cv.dither_blend(0, yy, PW, 1, C("#7a2a6a"), t * 0.35)
    for bxp in (180, 640):
        def board(xx):
            cv.rect(xx, 118, 50, 20, C("#3a2a5a"))
            cv.rect(xx + 2, 120, 46, 16, C("#c04a8a"))
            cv.rect(xx + 10, 124, 30, 3, C("#ffd0e8"))
            cv.rect(xx + 24, 138, 2, 12, C("#1a1834"))
        wrapped(board, bxp)
    out["neon_mile"] = cv
    # ---------------- Floodgate: storm night ----------------
    cv = Canvas(PW, PH)
    rng = rng_of("par", "fr")
    cv.vgrad(0, 0, PW, PH, [C("#2a3040"), C("#343c4e"), C("#4a5466")], levels=16)
    for _ in range(14):
        p_cloud(cv, rng.randrange(0, PW), rng.randrange(-6, 80), rng.randrange(90, 200), rng.randrange(14, 30),
                C("#3a4254"), C("#4e586c"), C("#252b38"), rng)
    for _ in range(10):
        p_streak(cv, rng.randrange(0, PW), rng.randrange(90, 150), rng.randrange(80, 200), C("#5a6478"),
                 C("#3a4254"))
    # distant lightning (thin, far)
    lx = 300
    pts = [(lx, 30)]
    for k in range(6):
        pts.append((pts[-1][0] + rng.randrange(-6, 7), pts[-1][1] + rng.randrange(8, 14)))
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, C("#b8c8e8"))
    # far towers + levee
    for tx in (90, 410, 730):
        def tower(xx):
            c = C("#2e3646")
            cv.rect(xx, 120, 22, 80, c)
            cv.rect(xx - 2, 116, 26, 5, c)
            cv.rect(xx + 9, 108, 4, 8, c)
            cv.rect(xx + 9, 105, 3, 3, C("#ff4a3a"))
            cv.rect(xx + 8, 130, 5, 4, C("#ffc870"))
        wrapped(tower, tx)
    for xx in range(PW):
        h = int(18 + 4 * math.sin(2 * math.pi * xx / PW * 4))
        cv.vl(xx, PH - 30 - h, PH, C("#262c3a"))
    skyline_layer(cv, rng, 204, 10, 30, C("#1e2430"), lit=C("#ffb050"), lit_p=0.05, kinds=("flat", "gable"),
                  wmin=30, wmax=70)
    out["floodgate"] = cv
    # ---------------- Warehouse: dark interior strip with high windows ----------------
    cv = Canvas(PW, PH)
    rng = rng_of("par", "rw")
    cv.rect(0, 0, PW, PH, C("#1e1c26"))
    tex_corrugated(cv, 0, 0, PW, PH, C("#26242e"), pitch=6)
    for k in range(0, PW, 120):
        cv.rect(k + 6, 6, 100, 30, C("#14121a"))
        cv.vgrad(k + 8, 8, 96, 26, [C("#4a5466"), C("#2e3646")])
        for j in range(k + 8, k + 104, 3):
            for yy in range(8 + (j * 5) % 7, 34, 7):
                cv.px(j, yy, C("#6a7a90"))
        for j in range(k + 8, k + 104, 24):
            cv.vl(j, 8, 26, C("#14121a"))
        cv.hl(k + 8, 20, 96, C("#14121a"))
    for k in range(0, PW, 60):
        cv.line(k, 40, k + 30, 70, C("#2e2c38"))
        cv.line(k + 30, 70, k + 60, 40, C("#2e2c38"))
    cv.rect(0, 38, PW, 3, C("#2e2c38"))
    cv.rect(0, 70, PW, 3, C("#2e2c38"))
    for k in range(40, PW, 160):
        cv.vl(k, 73, 30, C("#14121a"))
        cv.rect(k - 5, 103, 11, 3, C("#3a3846"))
        cv.rect(k - 3, 106, 7, 1, C("#c8b890"))
    cv.dither_blend(0, 110, PW, 110, C("#121018"), 0.5)
    out["warehouse"] = cv
    for name, c in out.items():
        c.a[..., 3] = 255
        c.save(os.path.join(BG_DIR, f"parallax_{name}.png"))
        print(f"parallax {name}")


# ============================================================================
# main
# ============================================================================
def load_rooms():
    with open(ROOMS_JSON) as fh:
        return json.load(fh)["rooms"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rooms", nargs="*", help="only these room ids")
    ap.add_argument("--only", nargs="*", choices=["rooms", "parallax", "props", "title", "map"],
                    help="only these asset groups")
    ap.add_argument("--placeholder", action="store_true", help="draw grey blocks for unknown facades (dev)")
    args = ap.parse_args(argv)
    groups = set(args.only or ["rooms", "parallax", "props", "title", "map"])
    rooms = load_rooms()
    if args.placeholder:
        for r in rooms.values():
            for f in r.get("facades", []):
                if f["kind"] not in FACADES:
                    FACADES[f["kind"]] = lambda R, x, w, f: R.cv.rect(x, 60, w, 154, C("#606070"))
            for g in r.get("ground", []):
                if g["style"] not in GROUNDS:
                    GROUNDS[g["style"]] = lambda R, x, w: R.cv.rect(x, 214, w, 146, C("#505060"))
    if "rooms" in groups:
        for rid, data in rooms.items():
            if args.rooms and rid not in args.rooms:
                continue
            R = build_room(rid, data)
            R.cv.save(os.path.join(BG_DIR, f"{rid}.png"))
            print(f"room {rid:16s} {R.w}x{H}")
    if "parallax" in groups and "gen_parallax" in globals():
        gen_parallax()
    if "props" in groups and "gen_props" in globals():
        gen_props(rooms)
    if "title" in groups and "gen_title" in globals():
        gen_title()
    if "map" in groups and "gen_map" in globals():
        gen_map()


if __name__ == "__main__":
    main()
