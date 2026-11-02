#!/usr/bin/env python3
"""v2 touch buttons, gamepad/key glyphs, district map, rotate hint and transition wipe
(density 2) -> game/assets/ui2/. Same names as the v1 files in assets/ui/.

Usage: python3 tools/art2/ui/gen_ui_extra.py [touch|glyphs|map|misc|all]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vec import Layer, hx, mix, tones, bez, ell_pts, star_pts, rot_pts, F_BUNGEE, F_COND_B, F_BARLOW_B, INK, ASSETS  # noqa: E402
import gen_ui  # noqa: E402
from gen_ui import UI_INK, BRASS, BRASS_LI, BRASS_SH, AMBER, CREAM, brass_line, ring_mask, rivet  # noqa: E402

WHITE = (255, 255, 255)
PICTO = hx('#f6ecd6')
PICTO_D = hx('#b8a07a')
ACCENT = {'punch': '#e8483a', 'kick': '#f08a2e', 'jump': '#4ab84a', 'guard': '#3a7ad8', 'grab': '#e8b83a',
          'run': '#2ab0b0'}


# ------------------------------------------------------------------ touch
def round_button(size, accent, picto=None, label=None, ring_w=6.0, alpha=0.92, pscale=None):
    L = Layer(size, size, ss=4)
    c = size / 2
    r = c - 1
    acc = hx(accent) if isinstance(accent, str) else accent
    L.fill(L.circle(c, c, r), UI_INK)
    ring = np.clip(L.circle(c, c, r - 2.5) - L.circle(c, c, r - 2.5 - ring_w), 0, 1)
    L.lin(ring, mix(acc, WHITE, 0.35), mix(acc, UI_INK, 0.35), (0, 0), (0, size))
    gloss = ring * (L.coords()[1] < c - r * 0.4)
    L.fill(gloss, mix(acc, WHITE, 0.6), 0.8)
    face = L.circle(c, c, r - 2.5 - ring_w)
    L.lin(face, hx('#3a3050'), hx('#1c1628'), (0, 0), (0, size))
    L.fill(np.clip(face - L.shift(face, 0, 1.5), 0, 1), WHITE, 0.12)
    L.fill(np.clip(L.dil(face, 1.0) - face, 0, 1), UI_INK, 0.8)
    if picto:
        P = Layer(size, size, ss=4)
        m = picto(P, c, c - (size * 0.07 if label else 0), pscale or size / 112.0)
        P.fill(np.clip(m - P.shift(m, 0, -1.6 * size / 112), 0, 1), PICTO_D)
        P.outline(2.4 * size / 112, UI_INK)
        L.over(P)
    if label:
        t = L.text(label, F_COND_B, size * 0.17, c, c + size * 0.3, anchor='mm', spacing=0.5)
        L.fill(L.dil(t, 1.6 * size / 112), UI_INK)
        L.fill(t, PICTO)
    L.c *= alpha
    L.a *= alpha
    return L.image()


def p_fist(P, cx, cy, s):
    m = np.zeros((P.H, P.W), np.float32)
    ox, oy = cx - 22 * s, cy - 20 * s
    for i in range(4):
        m = np.maximum(m, P.rect(ox + i * 11 * s, oy, ox + i * 11 * s + 10 * s, oy + 20 * s, r=4 * s))
    m = np.maximum(m, P.rect(ox, oy + 10 * s, ox + 43 * s, oy + 36 * s, r=6 * s))
    th = P.rect(ox - 3 * s, oy + 20 * s, ox + 26 * s, oy + 29 * s, r=4.5 * s)
    P.fill(m, PICTO)
    for i in range(1, 4):
        P.fill(P.rect(ox + i * 11 * s - 0.7 * s, oy + 2 * s, ox + i * 11 * s + 0.7 * s, oy + 15 * s), PICTO_D)
    P.fill(np.clip(P.dil(th, 1.4 * s) - th, 0, 1) * m, PICTO_D)
    P.fill(th, PICTO)
    return np.clip(m + th, 0, 1)


def p_kick(P, cx, cy, s):
    leg = P.poly([(cx - 20 * s, cy - 26 * s), (cx - 7 * s, cy - 26 * s), (cx + 8 * s, cy - 2 * s), (cx - 2 * s, cy + 6 * s)])
    shoe = P.rect(cx - 4 * s, cy - 8 * s, cx + 30 * s, cy + 8 * s, r=7 * s)
    m = np.clip(leg + shoe, 0, 1)
    P.fill(m, PICTO)
    P.fill(P.rect(cx - 4 * s, cy + 4 * s, cx + 30 * s, cy + 8 * s) * shoe, PICTO_D)
    for k, dy in enumerate((-10, 0, 10)):
        ln = P.rect(cx + 34 * s, cy + (dy - 1.6) * s, cx + (42 - 3 * (k % 2)) * s, cy + (dy + 1.6) * s, r=1.6 * s)
        P.fill(ln, PICTO)
        m = np.maximum(m, ln)
    return m


def p_jump(P, cx, cy, s):
    m = P.poly([(cx, cy - 28 * s), (cx + 22 * s, cy - 4 * s), (cx + 9 * s, cy - 4 * s), (cx + 9 * s, cy + 20 * s),
                (cx - 9 * s, cy + 20 * s), (cx - 9 * s, cy - 4 * s), (cx - 22 * s, cy - 4 * s)])
    P.fill(m, PICTO)
    bar = P.rect(cx - 18 * s, cy + 25 * s, cx + 18 * s, cy + 28.5 * s, r=1.6 * s)
    P.fill(bar, PICTO_D)
    return np.clip(m + bar, 0, 1)


def p_guard(P, cx, cy, s):
    m = P.poly(bez((cx - 22 * s, cy - 24 * s), (cx, cy - 30 * s), (cx + 22 * s, cy - 24 * s)) +
               bez((cx + 22 * s, cy - 24 * s), (cx + 22 * s, cy + 8 * s), (cx, cy + 26 * s)) +
               bez((cx, cy + 26 * s), (cx - 22 * s, cy + 8 * s), (cx - 22 * s, cy - 24 * s)))
    P.fill(m, PICTO)
    inner = P.ero(m, 5 * s)
    P.fill(np.clip(inner - P.ero(inner, 1.6 * s), 0, 1), PICTO_D)
    P.fill(P.rect(cx - 1.2 * s, cy - 20 * s, cx + 1.2 * s, cy + 16 * s) * inner, PICTO_D)
    return m


def p_hand(P, cx, cy, s):
    m = np.zeros((P.H, P.W), np.float32)
    for i, (dx, dy, h) in enumerate(((-16, -16, 26), (-7, -24, 32), (2, -24, 32), (11, -16, 26))):
        m = np.maximum(m, P.rect(cx + dx * s, cy + dy * s, cx + (dx + 7.5) * s, cy + (dy + h) * s, r=3.6 * s))
    palm = P.rect(cx - 16 * s, cy, cx + 18.5 * s, cy + 24 * s, r=7 * s)
    th = P.poly([(cx - 28 * s, cy - 6 * s), (cx - 21 * s, cy - 9 * s), (cx - 8 * s, cy + 6 * s), (cx - 14 * s, cy + 14 * s)])
    m = np.clip(m + palm + th, 0, 1)
    P.fill(m, PICTO)
    for dx in (-8.5, 0.5, 9.5):
        P.fill(P.rect(cx + dx * s - 0.7 * s, cy - 10 * s, cx + dx * s + 0.7 * s, cy + 2 * s), PICTO_D)
    return m


def p_run(P, cx, cy, s):
    shoe = P.poly([(cx - 10 * s, cy - 18 * s), (cx + 4 * s, cy - 18 * s), (cx + 8 * s, cy - 6 * s), (cx + 26 * s, cy - 2 * s),
                   (cx + 30 * s, cy + 10 * s), (cx - 12 * s, cy + 10 * s), (cx - 12 * s, cy - 14 * s)])
    P.fill(shoe, PICTO)
    P.fill(P.rect(cx - 12 * s, cy + 6 * s, cx + 30 * s, cy + 10 * s) * shoe, PICTO_D)
    for dy in (-12, -4):
        P.fill(P.rect(cx - 4 * s, cy + dy * s, cx + 4 * s, cy + (dy + 1.6) * s), PICTO_D)
    m = shoe
    for k, (dy, ln) in enumerate(((-12, 16), (-2, 20), (8, 16))):
        l = P.rect(cx - (18 + ln) * s, cy + (dy - 1.6) * s, cx - 18 * s, cy + (dy + 1.6) * s, r=1.6 * s)
        P.fill(l, PICTO)
        m = np.maximum(m, l)
    return m


def p_pause(P, cx, cy, s):
    m = np.clip(P.rect(cx - 10 * s, cy - 13 * s, cx - 3 * s, cy + 13 * s, r=1.5 * s) +
                P.rect(cx + 3 * s, cy - 13 * s, cx + 10 * s, cy + 13 * s, r=1.5 * s), 0, 1)
    P.fill(m, PICTO)
    return m


def p_bag(P, cx, cy, s):
    """Status: a head-and-shoulders bust, as in v1."""
    head = P.circle(cx, cy - 7 * s, 7.5 * s)
    body = P.poly(bez((cx - 15 * s, cy + 14 * s), (cx - 14 * s, cy + 1 * s), (cx, cy + 1 * s)) +
                  bez((cx, cy + 1 * s), (cx + 14 * s, cy + 1 * s), (cx + 15 * s, cy + 14 * s)))
    m = np.clip(head + body, 0, 1)
    P.fill(m, PICTO)
    P.fill(P.rect(cx - 15 * s, cy + 11 * s, cx + 15 * s, cy + 14 * s) * body, PICTO_D)
    return m


def touch():
    for kind, picto, label in (('punch', p_fist, 'P'), ('kick', p_kick, 'K'), ('jump', p_jump, 'JUMP'),
                               ('guard', p_guard, 'GRD'), ('grab', p_hand, 'GRAB'), ('run', p_run, 'RUN')):
        gen_ui.reg('touch_btn_' + kind, round_button(112, ACCENT[kind], picto, label))
        gen_ui.reg('touch_btn_%s_bare' % kind, round_button(112, ACCENT[kind], picto, None))
    gen_ui.reg('touch_btn_pause', round_button(64, '#8a8a9a', p_pause, None, ring_w=4, pscale=0.95))
    gen_ui.reg('touch_btn_status', round_button(64, '#8a8a9a', p_bag, None, ring_w=4, pscale=0.9))
    # stick base + knob
    L = Layer(192, 192, ss=3)
    c = 96
    L.fill(L.circle(c, c, 95), UI_INK, 0.7)
    L.fill(np.clip(L.circle(c, c, 93) - L.circle(c, c, 88), 0, 1), CREAM, 0.6)
    L.lin(L.circle(c, c, 88), hx('#3a3050'), hx('#1c1628'), (0, 0), (0, 192), a=0.55)
    L.fill(np.clip(L.circle(c, c, 44) - L.circle(c, c, 42), 0, 1), CREAM, 0.3)
    for k in range(4):
        tri = L.poly(rot_pts([(c, c - 80), (c + 12, c - 66), (c - 12, c - 66)], k * 90, c, c))
        L.fill(L.dil(tri, 2), UI_INK, 0.85)
        L.fill(tri, CREAM, 0.9)
    gen_ui.reg('touch_stick_base', L.image())
    L = Layer(80, 80, ss=4)
    c = 40
    L.fill(L.circle(c, c, 39), UI_INK, 0.9)
    knob = L.circle(c, c, 36)
    L.rad(knob, hx('#fff8e8'), hx('#c8b48c'), c - 10, c - 12, 52)
    L.fill(np.clip(L.circle(c, c, 21) - L.circle(c, c, 19), 0, 1), hx('#a8946c'), 0.8)
    L.fill(L.ellipse(c - 10, c - 13, 9, 6, rot=-30), WHITE, 0.7)
    gen_ui.reg('touch_stick_knob', L.image())
    gen_ui.write_meta()


# ------------------------------------------------------------------ gamepad / key glyphs
def face_btn(letter, col):
    L = Layer(24, 24, ss=6)
    L.fill(L.circle(12, 12, 11.6), UI_INK)
    b = L.circle(12, 12, 10)
    sh, base, li, ink = tones(col)
    L.lin(b, li, sh, (0, 2), (0, 22))
    L.fill(np.clip(b - L.shift(b, 0, 1.0), 0, 1), WHITE, 0.4)
    t = L.text(letter, F_BUNGEE, 12.5, 12, 12.6, anchor='mm')
    L.fill(L.dil(t, 0.9), UI_INK, 0.8)
    L.fill(t, WHITE)
    return L.image()


def shoulder(label, trigger):
    L = Layer(32, 20, ss=6)
    if trigger:
        m = L.poly(bez((3, 18), (2, 4), (10, 2)) + [(24, 2)] + bez((24, 2), (30, 4), (29, 18)))
    else:
        m = L.rect(1.5, 4, 30.5, 17, r=5)
    L.fill(L.dil(m, 1.4), UI_INK)
    L.lin(m, hx('#6a6478'), hx('#2e2a38'), (0, 2), (0, 18))
    L.fill(np.clip(m - L.shift(m, 0, 1.0), 0, 1), WHITE, 0.3)
    t = L.text(label, F_BUNGEE, 9.5, 16, 11.4 if trigger else 11.0, anchor='mm', spacing=0.3)
    L.fill(t, WHITE)
    return L.image()


def glyphs():
    for k, col in (('a', '#4ab84a'), ('b', '#e8483a'), ('x', '#3a7ad8'), ('y', '#e8b83a')):
        gen_ui.reg('gp_' + k, face_btn(k.upper(), hx(col)))
    for lab, trig in (('LB', False), ('RB', False), ('LT', True), ('RT', True)):
        gen_ui.reg('gp_' + lab.lower(), shoulder(lab, trig))
    # d-pad
    L = Layer(24, 24, ss=6)
    m = np.clip(L.rect(8.5, 2, 15.5, 22, r=1.5) + L.rect(2, 8.5, 22, 15.5, r=1.5), 0, 1)
    L.fill(L.dil(m, 1.3), UI_INK)
    L.lin(m, hx('#6a6478'), hx('#2e2a38'), (0, 2), (0, 22))
    for k in range(4):
        tri = L.poly(rot_pts([(12, 3.6), (14, 6.4), (10, 6.4)], k * 90, 12, 12))
        L.fill(tri, hx('#d8d0c0'))
    L.fill(L.circle(12, 12, 2), hx('#24202c'))
    gen_ui.reg('gp_dpad', L.image())
    # left stick
    L = Layer(24, 24, ss=6)
    L.fill(L.circle(12, 12, 11.6), UI_INK)
    L.lin(L.circle(12, 12, 10.2), hx('#4a4458'), hx('#22202a'), (0, 2), (0, 22))
    top = L.circle(12, 11, 7)
    L.rad(top, hx('#8a849a'), hx('#3a3646'), 10, 8, 9)
    L.fill(np.clip(L.circle(12, 11, 7) - L.circle(12, 11, 5.6), 0, 1), hx('#24202c'), 0.7)
    t = L.text('L', F_BUNGEE, 7, 12, 11.4, anchor='mm')
    L.fill(t, WHITE, 0.9)
    gen_ui.reg('gp_lstick', L.image())
    # select (view) / start (menu)
    for name in ('select', 'start'):
        L = Layer(24, 20, ss=6)
        m = L.rect(1.5, 2, 22.5, 18, r=8)
        L.fill(L.dil(m, 1.2), UI_INK)
        L.lin(m, hx('#6a6478'), hx('#2e2a38'), (0, 2), (0, 18))
        if name == 'select':
            a = L.rect(6.5, 6, 14, 12, r=1)
            b = L.rect(10, 8.5, 17.5, 14.5, r=1)
            L.fill(np.clip(a - L.ero(a, 1.1), 0, 1), WHITE)
            L.fill(np.clip(b - L.ero(b, 1.1), 0, 1), WHITE)
        else:
            for y in (6.5, 9.7, 12.9):
                L.fill(L.rect(7, y, 17, y + 1.4, r=0.6), WHITE)
        gen_ui.reg('gp_' + name, L.image())
    # key cap (9-slice)
    L = Layer(24, 24, ss=6)
    m = L.rect(0.5, 0.5, 23.5, 23.5, r=4)
    L.fill(m, UI_INK)
    L.fill(L.rect(2, 2.5, 22, 22.5, r=3), hx('#b8ac98'))
    face = L.rect(2.5, 2, 21.5, 19.5, r=3)
    L.lin(face, hx('#fbf4e4'), hx('#e2d6be'), (0, 2), (0, 19.5))
    L.fill(np.clip(face - L.shift(face, 0, 0.8), 0, 1), WHITE, 0.8)
    gen_ui.reg9('key_cap', L.image(), [8, 7, 8, 9], note='Keyboard key; draw the key label in #120c18 centred on the top '
                'face (bottom 4 tx is the key side).')
    gen_ui.write_meta()


# ------------------------------------------------------------------ map
DIST = {'old_quarter': (70, 112), 'canal_market': (148, 150), 'ironworks': (226, 98), 'neon_mile': (300, 132),
        'floodgate': (366, 168), 'warehouse': (430, 204)}
UL_MARK = (658, 406)   # Underline roundel, texels of ui2/map.png (content 1.2)
DCOL = {'old_quarter': '#f08a6a', 'canal_market': '#5ac8b8', 'ironworks': '#f0a050', 'neon_mile': '#b87ad8',
        'floodgate': '#7a9ad8', 'warehouse': '#a89a8a'}


def map_art():
    W, H = 960, 520
    L = Layer(W, H, ss=2)
    X, Y = L.coords()
    full = L.full()
    # parchment with mottling + vignette
    r = np.random.default_rng(9)
    base = np.array(hx('#efe2c4'), np.float32) / 255
    noise = np.zeros((H // 8 + 2, W // 8 + 2), np.float32)
    noise[:] = r.random(noise.shape)
    nb = np.kron(noise, np.ones((16, 16), np.float32))[:L.H, :L.W]
    from vec import blur
    nb = blur(nb, 12)
    vig = np.clip(np.sqrt(((X - W / 2) / (W / 2)) ** 2 + ((Y - H / 2) / (H / 2)) ** 2), 0, 1.5)
    shade = (0.92 + 0.12 * nb - 0.12 * vig ** 2)[..., None]
    rgb = base[None, None, :] * shade * np.array([1.0, 0.98, 0.94], np.float32)
    L.fill_rgb(full, rgb.astype(np.float32))
    # stains
    for (cx, cy, rr) in ((120, 420, 60), (820, 90, 46), (520, 470, 36)):
        st = L.blur(L.circle(cx, cy, rr), 10)
        L.fill(st, hx('#c8a878'), 0.18)
        L.fill(np.clip(L.circle(cx, cy, rr) - L.circle(cx, cy, rr - 2.5), 0, 1), hx('#b89060'), 0.15)
    # fold creases
    for x in (320, 640):
        L.fill(L.rect(x - 1, 0, x + 1, H), hx('#c8b08a'), 0.45)
        L.fill(L.rect(x + 1, 0, x + 3, H), WHITE, 0.25)
    L.fill(L.rect(0, 259, W, 261), hx('#c8b08a'), 0.45)
    L.fill(L.rect(0, 261, W, 263), WHITE, 0.25)
    # bay (bottom-right) + river
    bay = L.poly(bez((780, 520), (800, 440), (900, 432)) + [(960, 420), (960, 520)])
    river_pts_top = [(x, 374 + 16 * math.sin(x / 140.0) - (x / 960.0) * 20) for x in range(0, 961, 8)]
    river_pts_bot = [(x, y + 26 + 6 * math.sin(x / 90.0)) for x, y in river_pts_top]
    river = L.poly(river_pts_top + river_pts_bot[::-1])
    water = np.clip(river + bay, 0, 1)
    L.fill(L.dil(water, 2.5), hx('#7a9aa8'), 0.8)
    L.lin(water, hx('#8ac8e0'), hx('#5a9ac0'), (0, 360), (0, 520))
    for k in range(6):
        y0 = 380 + k * 22
        wave = L.stroke([(x, y0 + 3 * math.sin(x / 20.0 + k)) for x in range(0, 961, 6)], 1.0) * water
        L.fill(wave, WHITE, 0.35)
    # canal branch
    canal = L.stroke(bez((296, 300), (300, 340), (290, 380)), 9)
    L.fill(L.dil(canal, 2), hx('#7a9aa8'), 0.8)
    L.fill(canal, hx('#7ab8d8'))
    # district zones: soft inked blobs with street grids
    for d, (x, y) in DIST.items():
        cx, cy = x * 2, y * 2
        col = hx(DCOL[d])
        blob = L.ellipse(cx, cy, 86, 64, rot=(hash(d) % 30) - 15)
        L.fill(blob, col, 0.35)
        L.fill(np.clip(blob - L.ero(blob, 2.5), 0, 1), mix(col, INK, 0.4), 0.6)
        for gx in np.arange(cx - 80, cx + 80, 18):
            L.fill(L.rect(gx, cy - 64, gx + 1.2, cy + 64) * blob, mix(col, INK, 0.5), 0.35)
        for gy in np.arange(cy - 60, cy + 60, 16):
            L.fill(L.rect(cx - 86, gy, cx + 86, gy + 1.2) * blob, mix(col, INK, 0.5), 0.35)
    # railway (dashed, top)
    rail = bez((190, 172), (300, 110), (430, 160), n=60)
    for i in range(0, 60, 2):
        L.fill(L.stroke(rail[i:i + 2], 3), hx('#3a2a2a'))
    for i in range(0, 61, 3):
        x, y = rail[i]
        L.fill(L.stroke([(x, y - 5), (x, y + 5)], 1.4), hx('#3a2a2a'))
    # route between districts
    pts = [(x * 2, y * 2) for x, y in DIST.values()]
    route = []
    for a, b in zip(pts, pts[1:]):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 18)
        route += bez(a, mid, b, n=30)
    rm = L.stroke(route, 7)
    L.fill(L.dil(rm, 2), hx('#8a5a2a'), 0.9)
    L.fill(rm, hx('#e8b868'))
    for i in range(0, len(route) - 1, 6):
        L.fill(L.stroke(route[i:i + 3], 2), hx('#8a5a2a'), 0.6)
    # the Underline (content 1.2): dashed subway line UNDER the river, Neon Mile -> Floodgate,
    # drawn faint where it passes beneath the water; roundel marker + label on the south bank.
    ul = bez((600, 264), (596, 430), (716, 452), (732, 336), n=90)
    ULC = hx('#9a2a52')
    for i in range(0, 90, 3):
        seg = L.stroke(ul[i:i + 2], 4.2)
        inside = water[int(ul[i][1] * L.ss) % L.H, int(ul[i][0] * L.ss) % L.W] > 0.5
        a = 0.45 if inside else 1.0
        L.fill(np.clip(L.dil(seg, 1.4) - seg, 0, 1), INK, 0.8 * a)
        L.fill(seg, ULC, a)
    ux, uy = UL_MARK
    disc = L.circle(ux, uy, 11)
    L.fill(L.dil(disc, 2), INK)
    L.fill(disc, ULC)
    L.fill(L.circle(ux, uy, 6.2), hx('#f6ecd6'))
    bar = L.rect(ux - 15, uy - 3, ux + 15, uy + 3)
    L.fill(L.dil(bar, 1.6), INK)
    L.fill(bar, hx('#2a3a6a'))
    lab = L.text('UNDERLINE', F_COND_B, 13, ux, uy + 24, anchor='mm', spacing=1.2)
    L.fill(L.dil(lab, 2.0), hx('#f3e7cb'))
    L.fill(lab, ULC)
    # bridges over the river
    for bx in (220, 520, 680):
        yb = 374 + 16 * math.sin(bx / 140.0) - (bx / 960.0) * 20
        br = L.rect(bx - 7, yb - 8, bx + 7, yb + 40)
        L.fill(L.dil(br, 2), INK)
        L.fill(br, hx('#8a7a6a'))
        for yy in np.arange(yb - 6, yb + 38, 6):
            L.fill(L.rect(bx - 7, yy, bx + 7, yy + 1.2), hx('#5a4a3a'))
    # landmark glyphs (inked)
    def lm_house(x, y):
        for k in range(3):
            hx0 = x + k * 16
            m = L.poly([(hx0, y), (hx0 + 7, y - 9), (hx0 + 14, y), (hx0 + 14, y + 12), (hx0, y + 12)])
            L.fill(L.dil(m, 2), INK)
            L.fill(m, hx('#b84a3a'))
            L.fill(L.rect(hx0 + 5, y + 4, hx0 + 9, y + 12), hx('#3a2020'))

    def lm_factory(x, y):
        m = np.clip(L.poly([(x, y + 14), (x, y), (x + 10, y + 6), (x + 10, y), (x + 20, y + 6), (x + 20, y), (x + 30, y + 6),
                            (x + 30, y + 14)]) + L.rect(x + 22, y - 18, x + 28, y + 2), 0, 1)
        L.fill(L.dil(m, 2), INK)
        L.fill(m, hx('#7a4a3a'))
        for k in range(3):
            L.fill(L.blur(L.circle(x + 26 + k * 6, y - 24 - k * 7, 5 + k * 2), 2), hx('#8a8a8a'), 0.5)

    def lm_star(x, y):
        m = L.poly(star_pts(x, y, 13, 5.5, 5))
        L.fill(L.dil(m, 2), INK)
        L.fill(m, hx('#e84aa8'))
        L.fill(np.clip(m - L.shift(m, 0, -1.5), 0, 1), hx('#a82a78'))

    def lm_stall(x, y):
        aw = L.poly([(x - 2, y), (x + 26, y), (x + 22, y + 7), (x + 2, y + 7)])
        bd = L.rect(x + 2, y + 7, x + 22, y + 18)
        m = np.clip(aw + bd, 0, 1)
        L.fill(L.dil(m, 2), INK)
        L.fill(bd, hx('#c8a878'))
        Xs = L.coords()[0]
        L.fill(aw, hx('#e8483a'))
        L.fill(aw * (((Xs - x) // 5) % 2 == 0), WHITE)

    def lm_gate(x, y):
        m = np.clip(L.rect(x, y - 12, x + 7, y + 14) + L.rect(x + 17, y - 12, x + 24, y + 14) + L.rect(x, y - 6, x + 24, y), 0, 1)
        L.fill(L.dil(m, 2), INK)
        L.fill(m, hx('#6a7a9a'))

    def lm_crane(x, y):
        m = np.clip(L.rect(x, y - 20, x + 4, y + 14) + L.rect(x - 4, y - 22, x + 30, y - 18) + L.rect(x + 24, y - 18, x + 25.5, y - 4)
                    + L.rect(x + 8, y + 2, x + 34, y + 14), 0, 1)
        L.fill(L.dil(m, 2), INK)
        L.fill(m, hx('#8a7a6a'))
        L.fill(L.rect(x + 8, y + 2, x + 34, y + 6), hx('#5a6a8a'))

    lm_house(118, 152)
    lm_stall(288, 330)
    lm_factory(478, 130)
    lm_star(586, 204)
    lm_gate(752, 268)
    lm_crane(816, 330)
    # compass rose
    cx, cy = 878, 88
    ring = np.clip(L.circle(cx, cy, 30) - L.circle(cx, cy, 26), 0, 1)
    L.fill(L.dil(ring, 1.5), INK)
    brass_line(L, ring)
    n = L.poly([(cx, cy - 40), (cx + 7, cy), (cx - 7, cy)])
    s_ = L.poly([(cx, cy + 40), (cx + 7, cy), (cx - 7, cy)])
    e = L.poly([(cx + 26, cy), (cx, cy + 5), (cx, cy - 5)])
    w = L.poly([(cx - 26, cy), (cx, cy + 5), (cx, cy - 5)])
    for m, col in ((e, '#8a7a6a'), (w, '#8a7a6a'), (s_, '#3a2a2a'), (n, '#d8402e')):
        L.fill(L.dil(m, 1.4), INK)
        L.fill(m, hx(col))
    L.fill(L.circle(cx, cy, 3), BRASS_LI)
    # scale bar
    for k in range(4):
        L.fill(L.rect(60 + k * 24, 470, 84 + k * 24, 476), INK if k % 2 == 0 else WHITE)
    L.fill(np.clip(L.dil(L.rect(60, 470, 156, 476), 1.4) - L.rect(60, 470, 156, 476), 0, 1), INK)
    # frame: inked border + corner brass
    bd = np.clip(L.rect(0, 0, W, H) - L.rect(10, 10, W - 10, H - 10), 0, 1)
    L.fill(bd, hx('#5a3a2a'))
    L.fill(np.clip(L.rect(10, 10, W - 10, H - 10) - L.rect(14, 14, W - 14, H - 14), 0, 1), hx('#c8a878'))
    for (x, y) in ((12, 12), (W - 12, 12), (12, H - 12), (W - 12, H - 12)):
        rivet(L, x, y, 4.5)
    gen_ui.reg('map', L.image(), note='District map (2x of v1 480x260) + the Underline subway line. District dot and Underline marker '
               'coordinates are in ui2/map.json (texels of this image).')
    meta = {'_meta': {'density': 2, 'doc': 'District dot positions in texels of ui2/map.png (v1 coordinates x2).'}}
    for d, (x, y) in DIST.items():
        meta[d] = [x * 2, y * 2]
    meta['underline'] = list(UL_MARK)
    with open(os.path.join(gen_ui.OUT, 'map.json'), 'w') as fh:
        json.dump(meta, fh, indent=1)
    gen_ui.write_meta()


# ------------------------------------------------------------------ misc: rotate hint, wipe
def misc():
    L = Layer(128, 128, ss=4)
    ghost = L.rect(48, 8, 82, 70, r=6)
    L.fill(np.clip(ghost - L.ero(ghost, 2.4), 0, 1), CREAM, 0.45)
    arc = ell_pts(64, 64, 46, 46, a0=-60, a1=10, n=30)
    am = L.stroke(arc, 4.5)
    tip = L.poly([(arc[-1][0] + 9, arc[-1][1] - 6), (arc[-1][0] - 8, arc[-1][1] - 3), (arc[-1][0] + 2, arc[-1][1] + 10)])
    L.fill(L.dil(np.clip(am + tip, 0, 1), 2), UI_INK)
    L.fill(np.clip(am + tip, 0, 1), AMBER)
    phone = L.rect(12, 62, 106, 112, r=8)
    L.fill(L.dil(phone, 2.4), UI_INK)
    L.fill(phone, CREAM)
    scr = L.rect(22, 68, 96, 106, r=3)
    L.lin(scr, hx('#3a2a5a'), hx('#1c1628'), (0, 68), (0, 106))
    L.fill(L.rect(28, 92, 90, 100, r=2), hx('#5a4a6a'))
    L.fill(L.circle(101, 87, 2.2), hx('#a89878'))
    gen_ui.reg('rotate_device', L.image())
    # transition wipe: grey ramp (R=G=B) = reveal order 0..1 for a threshold shader.
    Wd, Hd = 640, 360
    Wp = Layer(Wd, Hd, ss=1)
    X, Y = Wp.coords()
    ang = math.radians(28)
    u = X * math.cos(ang) + Y * math.sin(ang)          # across stripes
    v = -X * math.sin(ang) + Y * math.cos(ang)         # along stripes
    umin, umax = 0, Wd * math.cos(ang) + Hd * math.sin(ang)
    band = 54.0
    idx = np.floor((u - umin) / band)
    nb = math.ceil((umax - umin) / band)
    vmin = -Wd * math.sin(ang)
    vmax = Hd * math.cos(ang)
    along = (v - vmin) / (vmax - vmin)
    along = np.where(idx % 2 == 0, along, 1 - along)    # alternate sliding direction
    val = np.clip(idx / nb * 0.55 + along * 0.45, 0, 1)
    g = (val * 255).astype(np.float32) / 255
    Wp.fill_rgb(Wp.full(), np.dstack([g, g, g]).astype(np.float32))
    gen_ui.reg('wipe', Wp.image(), note='Transition mask (opaque greyscale). In a shader, cover where value < '
               'progress (0..1); stripes slide in alternately. Stretch to the viewport.')
    gen_ui.write_meta()


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for fn, key in ((touch, 'touch'), (glyphs, 'glyphs'), (map_art, 'map'), (misc, 'misc')):
        if what in ('all', key):
            fn()
    print('ui2 entries:', len(gen_ui.META) - 1)
