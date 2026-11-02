"""Backstreet Oath env v2 -- foreground framing sprites per district (drawn darker, rim-lit, close to camera)."""
import math

import numpy as np

from raster import Canvas, C, mix, shade, light, rng_of
import kit
from kit import M, MAJOR, DETAIL

D = 2


def fg_bollards(rim='#fff0c0'):
    w, h = 110, 40
    cv = Canvas(w, h, D)
    m = M(C('#2a2a34'))
    for k, x in enumerate((14, 56, 98)):
        cv.fill_poly([(x - 6, h), (x - 5, 10), (x + 5, 10), (x + 6, h)], m.b, ink=m.i, iw=MAJOR)
        cv.ellipse(x, 10, 7, 3, m.l, ink=m.i, iw=MAJOR)
        cv.rect(x - 5, 10, 1, h - 10, C(rim), a=0.5)
    for a, b in ((14, 56), (56, 98)):
        kit.cable(cv, a + 5, 16, b - 5, 16, sag=8, w=1.2, col='#4a4a54')
    return cv


def fg_bunting(cols=None):
    w, h = 300, 40
    cv = Canvas(w, h, D)
    pts = kit.cable(cv, -4, 4, w + 4, 6, sag=20, w=0.6, col='#2a2026')
    cols = cols or ['#e84a3a', '#f8d040', '#3aa0d8', '#5ac06a', '#f4f0e8']
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        c = C(cols[i % len(cols)])
        cv.fill_poly([(x - 4, y), (x + 4, y), (x, y + 10)], shade(c, 0.5), ink=shade(c, 2.0), iw=DETAIL)
    return cv


def fg_fish_crates():
    w, h = 80, 40
    cv = Canvas(w, h, D)
    m = M(C('#5a6a74'))
    for (x, y, ww) in ((4, 20, 40), (40, 18, 36), (18, 4, 40)):
        cv.rect(x, y, ww, 18, m.b, ink=m.i, iw=MAJOR)
        for k in range(3):
            cv.rect(x, y + 4 + k * 4, ww, 0.6, m.s)
        cv.rect(x, y, ww, 1, C('#fff0c0'), a=0.5)
    return cv


def fg_pipes(rim='#ff9a50'):
    w, h = 420, 44
    cv = Canvas(w, h, D)
    for k, (y, r, col) in enumerate(((8, 6, '#3a4250'), (20, 4, '#4a3a34'), (30, 5, '#343c48'))):
        m = M(C(col))
        cv.rect(-2, y - r, w + 4, r * 2, m.b, ink=m.i, iw=MAJOR)
        cv.vgrad(-2, y - r, w + 4, r * 2, [m.l, m.b, m.d], mode='atop')
        cv.rect(-2, y - r, w + 4, 0.8, C(rim), a=0.6)
        for x in range(30, w, 90):
            cv.rect(x, y - r - 1, 4, r * 2 + 2, m.s, ink=m.i, iw=DETAIL)
    for x in (60, 260):
        cv.rect(x, 0, 3, 40, C('#2a2a34'))
    return cv


def fg_beam(rim='#ff9a50'):
    w, h = 140, 34
    cv = Canvas(w, h, D)
    m = M(C('#3a4250'))
    cv.rect(10, 16, 22, 18, C('#4a4a50'), ink=C('#0e0a10'), iw=MAJOR)
    cv.rect(108, 16, 22, 18, C('#4a4a50'), ink=C('#0e0a10'), iw=MAJOR)
    cv.rect(0, 4, w, 4, m.b, ink=m.i, iw=MAJOR)
    cv.rect(0, 14, w, 4, m.b, ink=m.i, iw=MAJOR)
    cv.rect(0, 8, w, 6, m.s, ink=m.i, iw=DETAIL)
    cv.rect(0, 4, w, 0.8, C(rim), a=0.6)
    return cv


def fg_hook(rim='#c8e0ff'):
    w, h = 40, 130
    cv = Canvas(w, h, D)
    for k in range(18):
        y = k * 5.6
        cv.ellipse(20, y + 2.8, 2.2 if k % 2 else 1.0, 3.0, None, ink=C('#2a2a34'), iw=1.2)
    cv.fill_poly([(12, 102), (28, 102), (26, 112), (14, 112)], C('#3a3e48'), ink=C('#0e0a10'), iw=MAJOR)
    cv.line([(20, 112), (20, 120), (27, 126), (30, 118)], 2.2, C('#5a5e6a'), ink=C('#0e0a10'), iw=DETAIL)
    cv.rect(18, 0, 0.8, 100, C(rim), a=0.3)
    return cv


def fg_jersey(rim='#a8e8f0'):
    w, h = 100, 34
    cv = Canvas(w, h, D)
    m = M(C('#6a7476'))
    cv.fill_poly([(2, h), (8, 16), (14, 6), (86, 6), (92, 16), (98, h)], m.b, ink=m.i, iw=MAJOR)
    cv.vgrad(2, 6, 96, h - 6, [m.l, m.b, m.s], mode='atop')
    for x in range(10, 90, 12):
        cv.fill_poly([(x, 10), (x + 6, 10), (x + 3, 16), (x - 3, 16)], C('#e8b830'), a=0.6, mode='atop')
    cv.line([(14, 6), (86, 6)], 0.8, C(rim), a=0.7)
    cv.vgrad(2, 6, 96, h - 6, [C('#c8e0e8', 60), C('#c8e0e8', 0)], mode='atop')
    return cv


def fg_cables(col='#140e18', n=4):
    w, h = 340, 56
    cv = Canvas(w, h, D)
    for k in range(n):
        kit.cable(cv, -5, 3 + k * 5, w + 5, 2 + k * 6, sag=14 + k * 5, w=0.6, col=col)
    return cv


def fg_neon_blade():
    w, h = 34, 120
    cv = Canvas(w, h, D)
    cv.rect(15, 0, 4, 10, C('#1a1420'))
    cv.rect(4, 10, 26, 106, C('#120a18'), ink=C('#06040a'), iw=MAJOR)
    for i, ch in enumerate('BAR'):
        kit.neon_text(cv, ch, 17, 30 + i * 30, 18, C('#ff4ab0'), tracking=0, glow=0.3)
    return cv


def fg_pallets():
    w, h = 70, 40
    cv = Canvas(w, h, D)
    m = M(C('#7a6448'))
    for k in range(4):
        y = h - 8 - k * 7
        cv.rect(2, y, 66, 2.4, m.b, ink=m.i, iw=DETAIL)
        cv.rect(2, y, 66, 0.6, C('#c8ffe0'), a=0.35)
        for x in (3, 32, 61):
            cv.rect(x, y + 2.4, 5, 4.2, m.s, ink=m.i, iw=DETAIL)
    return cv


def fg_shade(col='#6a2a2a', glow='#ffe0a0'):
    w, h = 44, 56
    cv = Canvas(w, h, D)
    cv.rect(w / 2 - 0.5, 0, 1, 34, C('#140e18'))
    m = M(C(col))
    cv.fill_poly([(w / 2 - 18, 52), (w / 2 + 18, 52), (w / 2 + 7, 34), (w / 2 - 7, 34)], m.b, ink=m.i, iw=MAJOR)
    cv.vgrad(w / 2 - 18, 34, 36, 18, [m.l, m.b, m.d], mode='atop')
    cv.ellipse(w / 2, 52.5, 16, 2.5, C(glow))
    cv.radial(w / 2, 54, 14, 3, C('#ffffff'), a=0.5, mode='addfree')
    return cv


def fg_tube(col='#e8fff4'):
    w, h = 70, 30
    cv = Canvas(w, h, D)
    for x in (10, 60):
        cv.rect(x, 0, 0.8, 22, C('#2a2a30'))
    cv.rect(2, 20, 66, 5, C('#9aa0a4'), ink=C('#1a1e20'), iw=MAJOR)
    cv.rect(5, 24, 60, 2, C(col))
    return cv


def fg_stack_boxes():
    w, h = 60, 64
    cv = Canvas(w, h, D)
    rs = rng_of('fgbox')
    for (x, y, ww, hh) in ((4, 36, 30, 28), (30, 40, 26, 24), (12, 10, 28, 26)):
        c = C(rs.choice(['#6a5038', '#5a4a3a', '#4a4a44']))
        m = M(c)
        cv.rect(x, y, ww, hh, m.b, ink=m.i, iw=MAJOR)
        cv.rect(x, y + hh / 2 - 1, ww, 2, m.l, a=0.6)
    return cv


# district -> list of (name, fn, kind 'bottom'|'top', parallax, fade)
DISTRICT_FG = {
    'canal_market': [('fg_bollards', fg_bollards, 'bottom', 1.25, True), ('fg_bunting', fg_bunting, 'top', 1.12, False),
                     ('fg_fishcrates', fg_fish_crates, 'bottom', 1.3, True)],
    'ironworks': [('fg_pipes', fg_pipes, 'top', 1.12, False), ('fg_beam', fg_beam, 'bottom', 1.25, True),
                  ('fg_hook', fg_hook, 'top', 1.18, False)],
    'neon_mile': [('fg_blade', fg_neon_blade, 'top', 1.15, False), ('fg_cables', fg_cables, 'top', 1.1, False),
                  ('fg_boxes', fg_stack_boxes, 'bottom', 1.28, True)],
    'floodgate': [('fg_jersey', fg_jersey, 'bottom', 1.25, True), ('fg_cables', fg_cables, 'top', 1.1, False)],
    'warehouse': [('fg_pallets', fg_pallets, 'bottom', 1.25, True), ('fg_hook', lambda: fg_hook('#c8ffe0'), 'top', 1.18,
                                                                       False)],
    'old_quarter': [],
}
INTERIOR_FG = {
    'int_garage': [('fg_tube', fg_tube, 'top', 1.15, False), ('fg_boxes', fg_stack_boxes, 'bottom', 1.2, True)],
    'int_rec': [('fg_tube', lambda: fg_tube('#fff4e0'), 'top', 1.15, False)],
    'int_noodle': [('fg_shade', lambda: fg_shade('#a8282a', '#ffd0a0'), 'top', 1.15, False)],
    'int_books': [('fg_shade', lambda: fg_shade('#2e5a3e'), 'top', 1.15, False),
                  ('fg_boxes', fg_stack_boxes, 'bottom', 1.2, True)],
    'int_canteen': [('fg_tube', fg_tube, 'top', 1.15, False)],
    'int_switch': [('fg_tube', lambda: fg_tube('#d8f0ff'), 'top', 1.15, False)],
    'int_arcade': [('fg_shade', lambda: fg_shade('#3a1a5a', '#ff8ad0'), 'top', 1.15, False)],
    'int_pharmacy': [('fg_tube', lambda: fg_tube('#f0fffc'), 'top', 1.15, False)],
    'int_bait': [('fg_shade', lambda: fg_shade('#3a5a4a'), 'top', 1.15, False),
                 ('fg_boxes', fg_stack_boxes, 'bottom', 1.2, True)],
}


def auto_fg(room_id, district, interior, width, south=None, spec=None):
    """Spread the district's fg sprites along the room, keeping clear of a south exit."""
    spec = spec if spec is not None else (INTERIOR_FG.get(room_id, []) if interior else DISTRICT_FG.get(district, []))
    out = []
    bottoms = [s for s in spec if s[2] == 'bottom']
    tops = [s for s in spec if s[2] == 'top']
    if bottoms:
        xs = [width - 40] if width <= 800 else list(np.arange(300, width - 100, 620))
        for i, x in enumerate(xs):
            if south and south[0] - 60 < x < south[1] + 60:
                continue
            name, fn, _, par, fade = bottoms[i % len(bottoms)]
            out.append((name, fn, float(x), 384.0, par, fade))
    if tops:
        xs = [width * 0.3, width * 0.75] if width <= 800 else list(np.arange(560, width - 60, 760))
        for i, x in enumerate(xs):
            name, fn, _, par, fade = tops[i % len(tops)]
            ytop = {'fg_pipes': 44.0, 'fg_hook': 130.0, 'fg_blade': 120.0, 'fg_shade': 52.0, 'fg_tube': 30.0,
                    'fg_bunting': 40.0, 'fg_cables': 56.0}.get(name, 50.0)
            out.append((name, fn, float(x), ytop, par, fade))
    return out
