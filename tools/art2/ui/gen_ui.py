#!/usr/bin/env python3
"""v2 UI art at density 2 -> game/assets/ui2/ (+ ui.json 9-slice margins).

Visual language: street-sign plates. Deep ink-violet bodies, a 2 tx dark contour, and a brass
trim line with a top-left highlight. Amber marks focus, cream paper is used for notes, and
Bungee is the display face. Everything is drawn here as vectors; nothing is upscaled.

Usage: python3 tools/art2/ui/gen_ui.py [core|title|logo|touch|glyphs|map|misc|all]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vec import (Layer, hx, mix, tones, save, bez, ell_pts, star_pts, rot_pts, F_BUNGEE, F_BARLOW_B,  # noqa: E402
                 F_COND_B, INK, ASSETS, blur, dilate)

OUT = os.path.join(ASSETS, 'ui2')
UIJSON = os.path.join(OUT, 'ui.json')

UI_INK = hx('#120c18')
BODY_T = hx('#2c2342')
BODY_B = hx('#191326')
BRASS = hx('#d0a050')
BRASS_LI = hx('#f6dc98')
BRASS_SH = hx('#7a5428')
AMBER = hx('#ffb444')
CREAM = hx('#f3e7cb')
CREAM_B = hx('#e3d1aa')
RED = hx('#d8392c')


def load_meta():
    if os.path.exists(UIJSON):
        return json.load(open(UIJSON))
    return {'_meta': {'density': 2, 'doc': 'margins are 9-slice insets in TEXELS [left, top, right, bottom] of the 2x '
                      'image; draw at scale 0.5 so a 12 tx margin is 6 u on screen.'}}


META = load_meta()


def reg9(name, im, margins, note=None):
    save(im, os.path.join(OUT, name + '.png'))
    e = {'file': name + '.png', 'size': list(im.size), 'margins': list(margins)}
    if note:
        e['note'] = note
    META[name] = e


def reg(name, im, note=None, **extra):
    save(im, os.path.join(OUT, name + '.png'))
    e = {'file': name + '.png', 'size': list(im.size)}
    if note:
        e['note'] = note
    e.update(extra)
    META[name] = e


def write_meta():
    with open(UIJSON, 'w') as fh:
        json.dump(dict(sorted(META.items(), key=lambda kv: (kv[0] != '_meta', kv[0]))), fh, indent=1)


# ------------------------------------------------------------------ plate helpers
def ring_mask(L, outer, w):
    return np.clip(outer - L.ero(outer, w), 0, 1)


def brass_line(L, m, base=BRASS, li=BRASS_LI, sh=BRASS_SH):
    L.fill(m, base)
    L.fill(np.clip(m - L.shift(m, 0.8, 0.8), 0, 1), li)
    L.fill(np.clip(m - L.shift(m, -0.8, -0.8), 0, 1), sh)


def rivet(L, x, y, r=1.6):
    m = L.circle(x, y, r)
    L.fill(L.dil(m, 0.7), UI_INK)
    L.fill(m, BRASS)
    L.fill(L.circle(x - r * 0.35, y - r * 0.35, r * 0.45), BRASS_LI)


def dark_plate(w, h, r=7, trim=4.0, trim_w=1.5, alpha=0.95, rivets=False, double=False, chamfer=0):
    L = Layer(w, h)
    if chamfer:
        c = chamfer
        shape = L.poly([(c, 0), (w, 0), (w, h - c), (w - c, h), (0, h), (0, c)])
        inner_pts = lambda k: [(c + k * 0.4, k), (w - k, k), (w - k, h - c - k * 0.4), (w - c - k * 0.4, h - k),
                               (k, h - k), (k, c + k * 0.4)]
    else:
        shape = L.rect(0, 0, w, h, r=r)
        inner_pts = None
    body = L.ero(shape, 2.0)
    L.fill(shape, UI_INK)
    L.lin(body, BODY_T, BODY_B, (0, 0), (0, h))
    L.fill(np.clip(body - L.shift(body, 0, 1.0), 0, 1), (255, 255, 255), 0.10)
    if trim:
        if chamfer:
            o = L.poly(inner_pts(trim))
            tm = ring_mask(L, o, trim_w)
        else:
            o = L.rect(trim, trim, w - trim, h - trim, r=max(r - trim + 1, 1))
            tm = ring_mask(L, o, trim_w)
        brass_line(L, tm)
        if double:
            o2 = L.rect(trim + trim_w + 1.5, trim + trim_w + 1.5, w - trim - trim_w - 1.5, h - trim - trim_w - 1.5,
                        r=max(r - trim - 2, 1))
            L.fill(ring_mask(L, o2, 1.0), mix(BRASS, BODY_B, 0.55))
    if rivets:
        k = trim + trim_w / 2
        for x, y in ((k, k), (w - k, k), (k, h - k), (w - k, h - k)):
            rivet(L, x, y, 1.9)
    L.c *= alpha
    L.a *= alpha
    return L


# ------------------------------------------------------------------ core UI
def core():
    reg9('panel', dark_plate(48, 48).image(), [14, 14, 14, 14])
    # light paper panel
    L = Layer(48, 48)
    shape = L.rect(0, 0, 48, 48, r=6)
    L.fill(shape, hx('#2a1a20'))
    body = L.ero(shape, 2.0)
    L.lin(body, CREAM, CREAM_B, (0, 0), (0, 48))
    L.fill(ring_mask(L, L.rect(4.5, 4.5, 43.5, 43.5, r=3), 1.0), hx('#b4986a'))
    L.fill(np.clip(body - L.shift(body, 0, 1.0), 0, 1), (255, 255, 255), 0.5)
    reg9('panel_light', L.image(), [14, 14, 14, 14])
    reg9('dialog_box', dark_plate(64, 64, r=8, trim=4.5, trim_w=1.6, rivets=True, double=True).image(), [20, 20, 20, 20])
    reg9('tooltip', dark_plate(32, 32, r=5, trim=3.0, trim_w=1.0).image(), [10, 10, 10, 10])
    reg9('hud_frame', dark_plate(64, 48, r=6, trim=4, trim_w=1.5, chamfer=12).image(), [18, 16, 18, 16],
         note='HUD plate (cut corner top-left / bottom-right).')
    # name tag: amber plate with chamfered ends
    L = Layer(48, 24)
    c = 6
    shape = L.poly([(c, 0), (48 - c, 0), (48, c), (48, 24 - c), (48 - c, 24), (c, 24), (0, 24 - c), (0, c)])
    L.fill(shape, UI_INK)
    body = L.ero(shape, 2.0)
    L.lin(body, hx('#ffc65a'), hx('#e08a26'), (0, 2), (0, 22))
    L.fill(np.clip(body - L.shift(body, 0, 1.2), 0, 1), hx('#fff0c0'), 0.9)
    L.fill(np.clip(body - L.shift(body, 0, -1.2), 0, 1), hx('#a85a18'), 0.9)
    reg9('name_tag', L.image(), [12, 8, 12, 8], note='Speaker name plate; dark text (#120c18) reads on it.')
    # buttons
    def button(face_t, face_b, border=None, pressed=False, disabled=False):
        L = Layer(48, 32)
        shape = L.rect(0, 0, 48, 32, r=6)
        L.fill(shape, UI_INK)
        top = 2.0 + (2.0 if pressed else 0.0)
        face = L.rect(2, top, 46, 30 - (0 if pressed else 3), r=4)
        depth = L.rect(2, 4, 46, 30, r=4)
        L.fill(depth, mix(face_b, UI_INK, 0.6))
        L.lin(face, face_t, face_b, (0, top), (0, 28))
        L.fill(np.clip(face - L.shift(face, 0, 1.0), 0, 1), (255, 255, 255), 0.18 if not disabled else 0.06)
        if border is not None:
            L.fill(ring_mask(L, face, 2.0), border)
            L.fill(ring_mask(L, L.ero(face, 2.0), 1.0), mix(border, (255, 255, 255), 0.5), 0.6)
        if disabled:
            L.c *= 0.75
            L.a *= 0.75
        return L.image()
    reg9('button', button(hx('#3e3858'), hx('#2a2540')), [12, 12, 12, 14])
    reg9('button_focus', button(hx('#4a3e5e'), hx('#30283f'), border=AMBER), [12, 12, 12, 14])
    reg9('button_pressed', button(hx('#2a2440'), hx('#211c33'), border=AMBER, pressed=True), [12, 12, 12, 14])
    reg9('button_disabled', button(hx('#3a3840'), hx('#2c2a32'), disabled=True), [12, 12, 12, 14])
    # bars
    L = Layer(24, 20)
    shape = L.rect(0, 0, 24, 20, r=5)
    L.fill(shape, UI_INK)
    rim = L.rect(1.8, 1.8, 22.2, 18.2, r=3.5)
    brass_line(L, ring_mask(L, rim, 1.4))
    rec = L.rect(3.6, 3.6, 20.4, 16.4, r=2)
    L.lin(rec, hx('#08060c'), hx('#1c1626'), (0, 3.6), (0, 16.4))
    reg9('bar_frame', L.image(), [8, 8, 8, 8], note='Fill area inset = 4 tx on every side.')
    L = Layer(48, 32)
    shape = L.rect(0, 0, 48, 32, r=6)
    L.fill(shape, UI_INK)
    rim = L.rect(2, 2, 46, 30, r=4.5)
    brass_line(L, ring_mask(L, rim, 2.2))
    rec = L.rect(5, 5, 43, 27, r=2.4)
    L.lin(rec, hx('#08060c'), hx('#22182a'), (0, 5), (0, 27))
    for x, y in ((3.1, 3.1), (44.9, 3.1), (3.1, 28.9), (44.9, 28.9)):
        rivet(L, x, y, 1.6)
    reg9('boss_bar_frame', L.image(), [16, 12, 16, 12], note='Fill area inset = 6 tx.')
    for name, top, mid, bot in (('bar_fill_hp', '#ff8a62', '#e03a2c', '#8a1624'),
                                ('bar_fill_xp', '#9af2e6', '#2fb0bc', '#16606e'),
                                ('bar_fill_boss', '#ffb050', '#e04a1e', '#7a1018'),
                                ('bar_fill_lag', '#fff8e0', '#f2dca8', '#c8a870'),
                                ('bar_fill_guard', '#c8d8ff', '#6a8ae0', '#2a3a8a')):
        L = Layer(16, 12, ss=4)
        full = L.full()
        X, Y = L.coords()
        t = Y / 12
        c0, c1, c2 = np.array(hx(top)) / 255, np.array(hx(mid)) / 255, np.array(hx(bot)) / 255
        tt = t[..., None]
        rgb = np.where(tt < 0.45, c0 + (c1 - c0) * (tt / 0.45), c1 + (c2 - c1) * ((tt - 0.45) / 0.55))
        L.fill_rgb(full, rgb.astype(np.float32))
        L.fill(L.rect(0, 2, 16, 3), (255, 255, 255), 0.45)
        reg(name, L.image(), note='Tile/stretch horizontally; vertical gradient.', margins=[2, 2, 2, 2])
    # portrait frame 208 for a 192 portrait
    L = Layer(208, 208, ss=3)
    shape = L.rect(0, 0, 208, 208, r=10)
    hole = L.rect(8, 8, 200, 200, r=4)
    frame = np.clip(shape - hole, 0, 1)
    L.fill(frame, UI_INK)
    bev = np.clip(L.ero(shape, 2) - L.dil(hole, 1.5), 0, 1)
    L.lin(bev, BRASS_LI, BRASS_SH, (0, 0), (208, 208))
    L.fill(np.clip(bev - L.ero(bev, 1.0), 0, 1), BRASS_SH, 0.8)
    inner = np.clip(L.dil(hole, 1.5) - hole, 0, 1)
    L.fill(inner, UI_INK)
    vig = np.clip(hole - L.ero(hole, 6), 0, 1) * np.clip(1 - (L.coords()[0] * 0), 0, 1)
    d = L.blur(np.clip(hole - L.ero(hole, 3), 0, 1), 2) * hole
    L.fill(d, (0, 0, 0), 0.45)
    for (x, y, sx, sy) in ((4, 4, 1, 1), (204, 4, -1, 1), (4, 204, 1, -1), (204, 204, -1, -1)):
        br = L.poly([(x, y), (x + sx * 30, y), (x + sx * 30, y + sy * 4), (x + sx * 4, y + sy * 4),
                     (x + sx * 4, y + sy * 30), (x, y + sy * 30)])
        L.fill(L.dil(br, 1.0), UI_INK)
        brass_line(L, br, base=AMBER, li=hx('#fff0c0'), sh=hx('#b0681c'))
    reg9('portrait_frame', L.image(), [24, 24, 24, 24], note='Frame over a 192x192 portrait placed at (8, 8).')
    # HUD badge ring (level / mini portrait)
    L = Layer(64, 64)
    o = L.circle(32, 32, 31)
    L.fill(o, UI_INK)
    L.lin(L.circle(32, 32, 29), BRASS_LI, BRASS_SH, (8, 8), (56, 56))
    L.fill(L.circle(32, 32, 24), UI_INK)
    L.lin(L.circle(32, 32, 22.5), BODY_T, BODY_B, (0, 10), (0, 54))
    reg('hud_badge', L.image(), note='Round brass badge; centre disc radius 22 tx for level number or mini portrait.')
    # cursor
    L = Layer(24, 24)
    m = L.poly([(4, 3), (21, 12), (4, 21), (8, 12)])
    L.fill(L.dil(m, 2.0), UI_INK)
    L.fill(m, AMBER)
    L.fill(L.poly([(4, 3), (21, 12), (8, 12)]), hx('#ffe08a'))
    L.fill(np.clip(m - L.shift(m, 0, -1.2), 0, 1), hx('#b86a1c'))
    reg('cursor', L.image(), note='Points right; hotspot (21, 12).')
    # boss card
    W, H = 720, 160
    L = Layer(W, H, ss=2)
    sk = 40
    plate = L.poly([(sk, 14), (W, 14), (W - sk, H - 14), (0, H - 14)])
    L.fill(L.dil(plate, 3), UI_INK)
    L.lin(plate, hx('#2e2244'), hx('#140e20'), (0, 14), (0, H - 14))
    X, Y = L.coords()
    stripes = (((X + Y) // 18) % 2 == 0).astype(np.float32) * plate
    L.fill(stripes, (255, 255, 255), 0.035)
    top = L.poly([(sk - 1, 14), (W, 14), (W - 1.6, 20), (sk - 2.6, 20)])
    bot = L.poly([(1.6, H - 20), (W - sk + 2.6, H - 20), (W - sk + 1, H - 14), (0, H - 14)])
    brass_line(L, top)
    brass_line(L, bot)
    red = L.poly([(sk - 4, 26), (sk + 34, 26), (sk + 2, H - 26), (-30 + sk, H - 26)])
    L.fill(L.dil(red, 2), UI_INK)
    L.lin(red, hx('#ff5a3c'), hx('#a81c20'), (0, 26), (0, H - 26))
    L.fill(np.clip(red - L.shift(red, 0, 2), 0, 1), hx('#ffb08a'), 0.9)
    reg('boss_card', L.image(), note='Boss name card. Text area x 110..640, y 36..124 (tx). Slides in from the left.',
        text_rect=[110, 36, 530, 88])
    write_meta()


# ------------------------------------------------------------------ logo
def logo_layer(W, H, ss=2):
    L = Layer(W, H, ss)
    # top line
    top_txt = 'BACKSTREET'
    # measure and build masks
    m_top = L.text(top_txt, F_BUNGEE, 96, W / 2, 104, anchor='ms', spacing=2)
    m_oath = L.text('OATH', F_BUNGEE, 168, W / 2 + 4, 292, anchor='ms', spacing=6)
    # brass bars flanking OATH (kept clear of the letters)
    ys, xs = np.nonzero(m_oath > 0.5)
    ox0, ox1 = xs.min() / ss, xs.max() / ss
    gap = 34
    bx0, bx1 = ox0 - gap, ox1 + gap
    bars = np.clip(L.rect(60, 214, bx0, 230, r=4) + L.rect(bx1, 214, W - 60, 230, r=4), 0, 1)
    bars2 = np.clip(L.rect(96, 238, bx0 - 8, 248, r=3) + L.rect(bx1 + 8, 238, W - 96, 248, r=3), 0, 1)
    allm = np.clip(m_top + m_oath + bars + bars2, 0, 1)
    # extrusion (hard 3D drop) down-right
    ext = np.zeros_like(allm)
    for k in range(1, 13):
        ext = np.maximum(ext, L.shift(allm, k * 0.5, k * 0.85))
    ext = np.clip(ext - allm, 0, 1)
    # outer ink around everything (letters + extrusion)
    sil = np.clip(allm + ext, 0, 1)
    L.fill(L.dil(sil, 7), UI_INK)
    L.fill(L.dil(sil, 4.5), hx('#3a1a2a'))
    L.fill(L.dil(sil, 3.5), UI_INK)
    # extrusion colour (deep violet with lighter top facets)
    L.lin(ext, hx('#5a2a52'), hx('#1e0e26'), (0, 120), (0, 300))
    # letters: cream top line
    L.lin(m_top, hx('#fffaf0'), hx('#e8d4b0'), (0, 30), (0, 104))
    L.fill(np.clip(m_top - L.shift(m_top, 0, 3.0), 0, 1), (255, 255, 255))
    L.fill(np.clip(m_top - L.shift(m_top, 0, -2.5), 0, 1), hx('#b89a78'))
    # OATH: amber -> red, hard cel split
    X, Y = L.coords()
    L.lin(m_oath, hx('#ffd65a'), hx('#ff7a2a'), (0, 150), (0, 230))
    lower = (Y > 236).astype(np.float32) * m_oath
    L.lin(lower, hx('#f0502a'), hx('#b8241e'), (0, 236), (0, 292))
    L.fill(np.clip(m_oath - L.shift(m_oath, 0, 4.0), 0, 1), hx('#fff4c8'))
    L.fill(np.clip(m_oath - L.shift(m_oath, 0, -3.0), 0, 1), hx('#7a1416'))
    # glint
    gl = L.poly([(470, 140), (490, 140), (440, 300), (420, 300)]) * m_oath
    L.fill(gl, (255, 255, 255), 0.35)
    # bars brass
    brass_line(L, bars)
    brass_line(L, bars2)
    # thin inner ink line between letters and extrusion edge (crisp)
    L.fill(np.clip(L.dil(np.clip(m_top + m_oath, 0, 1), 1.2) - np.clip(m_top + m_oath, 0, 1), 0, 1) * ext, UI_INK)
    # small stars on bars
    for x in (bx0 - 2, bx1 + 2):
        s = L.poly(star_pts(x, 222, 14, 5.5, 5, rot=0))
        L.fill(L.dil(s, 3), UI_INK)
        L.fill(s, hx('#ffd65a'))
        L.fill(np.clip(s - L.shift(s, 0, -1.5), 0, 1), hx('#d0802a'))
    return L


def logo():
    W, H = 1100, 330
    L = logo_layer(W, H, ss=2)
    im = L.image()
    bbox = im.getbbox()
    reg('logo', im, note='Title logo (Bungee, OFL). Draw at scale 0.5 => 550x165 u.', bbox=list(bbox))
    small = im.resize((W // 2, H // 2), Image.LANCZOS)
    reg('logo_small', small, note='Half-size logo for menus/credits (downscaled from logo.png).')
    write_meta()


# ------------------------------------------------------------------ app icons
def icon(size):
    s = size / 256.0
    L = Layer(size, size, ss=4 if size <= 64 else 2)
    sq = L.rect(0, 0, size, size, r=44 * s)
    L.fill(sq, UI_INK)
    inner = L.ero(sq, 6 * s)
    L.lin(inner, hx('#ff9a4a'), hx('#3a1e52'), (0, 10 * s), (0, 200 * s))
    sun = L.circle(170 * s, 120 * s, 70 * s) * inner
    L.fill(sun, hx('#ffd08a'), 0.55)
    # skyline silhouette
    sky = L.poly([(0, 200 * s), (0, 150 * s), (40 * s, 150 * s), (40 * s, 120 * s), (70 * s, 120 * s), (70 * s, 160 * s),
                  (110 * s, 160 * s), (110 * s, 100 * s), (124 * s, 100 * s), (124 * s, 70 * s), (132 * s, 70 * s),
                  (132 * s, 100 * s), (150 * s, 100 * s), (150 * s, 140 * s), (200 * s, 140 * s), (200 * s, 112 * s),
                  (230 * s, 112 * s), (230 * s, 150 * s), (256 * s, 150 * s), (256 * s, 256 * s), (0, 256 * s)]) * inner
    L.fill(sky, hx('#2a1638'))
    for (x, y) in ((50, 130), (58, 140), (84, 170), (138, 112), (140, 124), (212, 122), (216, 134)):
        L.fill(L.rect(x * s, y * s, (x + 5) * s, (y + 6) * s), hx('#ffc860'), 0.9)
    # headband ribbon
    band = L.poly([(-10 * s, 176 * s), (266 * s, 112 * s), (266 * s, 140 * s), (-10 * s, 204 * s)]) * inner
    L.fill(L.dil(band, 3 * s) * inner, UI_INK)
    L.lin(band, hx('#ff5a3c'), hx('#a81c20'), (0, 110 * s), (0, 200 * s))
    tails = L.poly([(196 * s, 128 * s), (246 * s, 188 * s), (232 * s, 196 * s), (188 * s, 140 * s)])
    tails = np.clip(tails + L.poly([(200 * s, 126 * s), (256 * s, 160 * s), (252 * s, 172 * s), (194 * s, 138 * s)]), 0, 1) * inner
    L.fill(L.dil(tails, 3 * s) * inner, UI_INK)
    L.fill(tails, hx('#e03a2c'))
    # monogram
    m = L.text('BO', F_BUNGEE, 118 * s, 128 * s, 132 * s, anchor='mm', spacing=2 * s)
    ext = np.zeros_like(m)
    for k in range(1, 6):
        ext = np.maximum(ext, L.shift(m, k * 0.8 * s, k * 1.2 * s))
    ext = np.clip(ext - m, 0, 1)
    L.fill(L.dil(np.clip(m + ext, 0, 1), 6 * s), UI_INK)
    L.fill(ext, hx('#4a1e4a'))
    L.lin(m, hx('#fffaf0'), hx('#f0c86a'), (0, 80 * s), (0, 170 * s))
    L.fill(np.clip(m - L.shift(m, 0, 4 * s), 0, 1), (255, 255, 255))
    return L.image()


def icons():
    reg('icon', icon(256), note='App icon 256.')
    reg('icon_64', icon(64), note='App icon 64 (rendered at 64, not downscaled).')
    write_meta()


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    os.makedirs(OUT, exist_ok=True)
    if what in ('core', 'all'):
        core()
    if what in ('logo', 'all'):
        logo()
    if what in ('icons', 'all'):
        icons()
    print('ui2 entries:', len(META) - 1)
