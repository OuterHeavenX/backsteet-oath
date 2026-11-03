"""Backstreet Oath env v2.1 -- background life data and sprites (docs/visual/ASSET_CONTRACT_V2.md section 2b).

  write_shared(out_root)   game/assets/bg2/_life/: cloud_a..e, car_a..d, train_el, pigeon, bird, silhouette
  room_extras(R)           per-room additions drawn into the base before the realism pass (hanging-sign brackets,
                           ceiling grates, ...) and lane/shaft/sign data that needs the room's geometry
  sway sprites             templates for pennants, laundry, hanging signs, flags (drawn separately so they move)
  ROOM_LAYERS              extra parallax layers that carry a painted lane (road, rail viaduct, el structure)
  assemble(R, js, d)       clouds / haze / grade / life entries written into room.json
All deterministic (fixed seeds), Pillow + numpy only, inked + cel-shaded at density 2.
"""
import math
import os

import numpy as np
from PIL import Image

from raster import Canvas, C, mix, shade, light, ink_of, blur, rng_of, value_noise
import kit
from kit import M, MAJOR, DETAIL
from room import FACADE_BOTTOM as FB, H, CURB_Y, INT_WALL_BOTTOM as WB

D = 2
INK = C('#1a1220')


def _hex(c):
    return '#%02x%02x%02x' % tuple(int(v) for v in c[:3])


# ============================================================================ shared sprites
def cloud(kind, seed):
    """Soft-edged stylised cloud, near-white (the engine tints it): round puffs lit from above in two soft cel
    tones, a flat greyer underside and feathered edges."""
    rs = rng_of('cloud', kind, seed)
    W_, H_, n, style = {'a': (220, 70, 6, 'cumulus'), 'b': (310, 44, 9, 'stratus'), 'c': (130, 54, 4, 'cumulus'),
                        'd': (260, 78, 8, 'double'), 'e': (280, 36, 6, 'wisp')}[kind]
    hh, ww = int(H_ * D), int(W_ * D)
    X = (np.arange(ww, dtype=np.float32) + 0.5) / D
    Y = (np.arange(hh, dtype=np.float32) + 0.5) / D
    XX, YY = np.meshgrid(X, Y)
    base_y = H_ - 7.0
    puffs = []
    for i in range(n):
        t = (i + 0.5) / n
        if style == 'double':
            hump = max(math.sin(min(1.0, t * 1.8) * math.pi), 0.8 * math.sin(min(1.0, max(0.0, t * 1.8 - 0.8)) * math.pi))
        else:
            hump = math.sin(t * math.pi) ** 0.8
        cx = 10 + (W_ - 20) * t + rs.uniform(-3, 3)
        if style in ('stratus', 'wisp'):
            r = (H_ * 0.22 + H_ * 0.32 * hump) * rs.uniform(0.85, 1.1)
        else:
            r = (H_ * 0.2 + H_ * 0.46 * hump) * rs.uniform(0.85, 1.08)
        sx0 = 2.4 if style == 'wisp' else (1.25 if style == 'stratus' else 1.0)
        r = min(r, (base_y - 2) / 1.7, (cx - 2) / sx0, (W_ - 2 - cx) / sx0)
        cy = base_y - r * rs.uniform(0.35, 0.7)
        puffs.append((cx, cy, r))
        if style in ('cumulus', 'double') and hump > 0.6 and rs.random() < 0.7:     # small crown puffs
            r2 = r * rs.uniform(0.45, 0.6)
            puffs.append((cx + rs.uniform(-r * 0.4, r * 0.4), max(r2 + 1.5, cy - r * 0.55), r2))
    hgt = np.zeros((hh, ww), np.float32)
    for (cx, cy, r) in puffs:
        sx_ = 2.4 if style == 'wisp' else (1.25 if style == 'stratus' else 1.0)
        d2 = (((XX - cx) / sx_) ** 2 + (YY - cy) ** 2) / (r * r)
        hgt = np.maximum(hgt, np.sqrt(np.clip(1 - d2, 0, 1)) * r)
    cut = np.clip((base_y - YY) / 2.5 + 0.5, 0, 1)                    # flat underside
    a = np.clip(hgt * 1.4, 0, 1) * cut
    nz = value_noise(ww, hh, 4 * D, abs(hash(('cn', kind, seed))) % 9999, 2)
    if style == 'wisp':
        a *= 0.75 + 0.25 * np.clip(np.sin(YY * 0.9 + nz * 3.0) * 0.5 + 0.5, 0, 1)
    a = blur(np.clip(a + (nz - 0.5) * 0.25 * a, 0, 1), 1.2 * D, passes=2)
    a = np.clip((a - 0.08) * 1.25, 0, 1)
    # light from above-left: brightness from the height-field slope
    gy, gx = np.gradient(blur(hgt, 1.0 * D, passes=2))
    lit = np.clip(0.5 + gy * 1.3 + gx * 0.35, 0, 1)
    t1 = np.clip((lit - 0.42) / 0.14, 0, 1)
    t1 = t1 * t1 * (3 - 2 * t1)
    under = np.clip((YY - (base_y - H_ * 0.22)) / (H_ * 0.22), 0, 1) ** 1.3
    top_c = np.array([1.0, 1.0, 1.0], np.float32)
    mid_c = np.array([0.90, 0.91, 0.95], np.float32)
    und_c = np.array([0.78, 0.80, 0.87], np.float32)
    rgb = mid_c * (1 - t1[..., None]) + top_c * t1[..., None]
    rgb = rgb * (1 - under[..., None] * 0.85) + und_c * (under[..., None] * 0.85)
    out = np.concatenate([np.clip(rgb, 0, 1), a[..., None]], axis=2)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')


def _wheel(cv, x, yb, r, rim='#b8bcc4'):
    cv.ellipse(x, yb - r, r, r, C('#18161c'), ink=INK, iw=MAJOR)
    cv.ellipse(x, yb - r, r * 0.58, r * 0.58, C(rim), ink=C('#2a2830'), iw=DETAIL)
    cv.ellipse(x - r * 0.12, yb - r * 1.12, r * 0.28, r * 0.2, C('#f4f4f8'), a=0.7)
    cv.ellipse(x, yb - r, r * 0.18, r * 0.18, C('#4a4850'))
    for k in range(5):
        a = k * 2 * math.pi / 5
        cv.ellipse(x + math.cos(a) * r * 0.36, yb - r + math.sin(a) * r * 0.36, 0.5, 0.5, C('#6a6870'))


def _body(cv, pts, col, h0, h1):
    """Car body: inked silhouette, three-tone cel shading (lit shoulders, shaded rocker), warm rim on top."""
    m = M(C(col))
    lay = cv.layer()
    lay.fill_poly(pts, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    mk = cv.poly_mask(pts)
    cv.vgrad(0, h0, cv.W / D, h1 - h0, [(0.0, m.l), (0.32, m.b), (0.62, m.b), (0.78, m.s), (1.0, m.d)], mk=mk,
             mode='atop')
    return m, mk


def _glass(cv, pts, seed):
    mk = cv.poly_mask(pts)
    cv.stroke_fill(mk, C('#2a3044'), ink=INK, iw=DETAIL)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cv.vgrad(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys), [C('#8aa0b8'), C('#3a4860'), C('#222838')],
             mk=mk, mode='atop')
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    w = x1 - x0
    sk = cv.poly_mask([(x0 + w * 0.2, y0), (x0 + w * 0.34, y0), (x0 + w * 0.18, y1), (x0 + w * 0.04, y1)])
    cv.paint(sk, C('#d8e4f0'), a=0.35, mode='atop')
    return mk


def car_sedan(col='#7a2a34', taxi=False):
    L, Hh = 136, 46
    cv = Canvas(L, Hh, D)
    yb = Hh
    r = 7.6
    wx0, wx1 = 26, 108
    body = [(2, yb - 9), (1, yb - 18), (3, yb - 21.5), (24, yb - 23), (36, yb - 24), (48, yb - 37), (88, yb - 37.5),
            (100, yb - 25), (128, yb - 22.5), (134, yb - 19.5), (135, yb - 10), (132, yb - 7), (4, yb - 7)]
    m, mk = _body(cv, body, col, yb - 38, yb - 7)
    # wheel arches cut + wheels
    for wx in (wx0, wx1):
        cv.ellipse(wx, yb - r, r + 2.4, r + 2.0, C('#120e16'), mode='atop')
    for wx in (wx0, wx1):
        _wheel(cv, wx, yb, r)
    # glass: rear quarter, rear door, front door (B and C pillars)
    _glass(cv, [(50, yb - 35.5), (66, yb - 35.8), (66, yb - 25.5), (40, yb - 25.2)], 1)
    _glass(cv, [(68, yb - 35.8), (86.5, yb - 36), (96.5, yb - 25.6), (68, yb - 25.5)], 2)
    cv.rect(66, yb - 36, 2, 11, m.d)
    # belt chrome, door seams, handles, side trim
    cv.rect(10, yb - 24.6, 120, 0.8, C('#e8ecf0'), a=0.85)
    for sx in (67, 98):
        cv.rect(sx, yb - 25, 0.5, 15, m.d, a=0.8)
    cv.rect(37, yb - 25, 0.5, 15, m.d, a=0.8)
    for hx in (60, 91):
        cv.rect(hx, yb - 22.5, 4, 1, C('#d8dce4'), ink=m.d, iw=0.3)
    cv.rect(6, yb - 15, 124, 1.6, shade(m.b, 1.3), a=0.8)
    cv.rect(6, yb - 15, 124, 0.5, m.h, a=0.5)
    # bumpers, lamps, mirror, plate
    cv.rect(0.5, yb - 13, 5, 6, C('#c8ccd4'), ink=INK, iw=DETAIL)
    cv.rect(131, yb - 13, 5, 6, C('#c8ccd4'), ink=INK, iw=DETAIL)
    cv.rect(1.5, yb - 21, 3.5, 6.5, C('#c83a3a'), ink=INK, iw=DETAIL)          # tail light
    cv.rect(1.5, yb - 21, 3.5, 1.5, C('#ff9a8a'), a=0.8)
    cv.rect(130.5, yb - 19.5, 4.5, 5, C('#fff4c8'), ink=INK, iw=DETAIL)        # headlight (~28 % up)
    cv.rect(131, yb - 13.6, 4, 1.6, C('#f0a040'))                               # indicator
    cv.fill_poly([(96, yb - 27), (100, yb - 27), (100.5, yb - 24.5), (96, yb - 24.5)], m.b, ink=m.i, iw=DETAIL)
    # rim light along roof and hood, soft shadow under the sills
    cv.line([(48, yb - 37), (88, yb - 37.5)], 0.6, C('#ffe8c8'), a=0.75)
    cv.line([(100, yb - 25), (128, yb - 22.5)], 0.5, C('#ffe8c8'), a=0.6)
    if taxi:
        cv.rect(58, yb - 43, 22, 6, C('#f4f0e0'), ink=INK, iw=DETAIL)
        cv.text('TAXI', 'cond', 4.2, 69, yb - 40, C('#2a2026'), 'mm')
        cv.rect(64, yb - 37.5, 10, 0.8, C('#2a2026'))
        for k in range(14):
            cv.rect(38 + k * 4, yb - 20, 2, 2, C('#1e1a22') if k % 2 == 0 else C('#f4f0e0'))
            cv.rect(38 + k * 4, yb - 18, 2, 2, C('#f4f0e0') if k % 2 == 0 else C('#1e1a22'))
    return cv


def car_van(col='#d8ccb0', stripe='#c8543a'):
    L, Hh = 142, 58
    cv = Canvas(L, Hh, D)
    yb = Hh
    r = 7.8
    body = [(2, yb - 9), (1, yb - 50), (4, yb - 53), (100, yb - 54), (106, yb - 52), (117, yb - 31), (136, yb - 27),
            (141, yb - 22), (141, yb - 10), (137, yb - 7), (4, yb - 7)]
    m, mk = _body(cv, body, col, yb - 54, yb - 7)
    for wx in (26, 116):
        cv.ellipse(wx, yb - r, r + 2.4, r + 2.0, C('#120e16'), mode='atop')
        _wheel(cv, wx, yb, r)
    _glass(cv, [(88, yb - 49), (104, yb - 49), (113, yb - 32.5), (88, yb - 32.5)], 3)      # cab door window
    _glass(cv, [(8, yb - 49), (30, yb - 49), (30, yb - 36), (8, yb - 36)], 4)              # rear side window
    cv.rect(52, yb - 50, 0.5, 40, m.d, a=0.8)                                              # sliding door
    cv.rect(86, yb - 50, 0.5, 40, m.d, a=0.8)
    cv.rect(52, yb - 50.5, 34, 0.8, m.d, a=0.6)
    cv.rect(80, yb - 30, 4, 1.2, C('#d8dce4'), ink=m.d, iw=0.3)
    cv.rect(2, yb - 26, 139, 4, C(stripe), mode='atop')
    cv.rect(2, yb - 26, 139, 0.8, light(C(stripe), 1.4), a=0.7, mode='atop')
    cv.text('PIRELLI BAKERY', 'cond', 4.5, 44, yb - 40, shade(C(stripe), 0.6), 'mm', tracking=0.5)
    cv.rect(0.5, yb - 13, 5, 6, C('#a8acb4'), ink=INK, iw=DETAIL)
    cv.rect(137, yb - 13, 4.5, 6, C('#a8acb4'), ink=INK, iw=DETAIL)
    cv.rect(1.5, yb - 24, 3.5, 7, C('#c83a3a'), ink=INK, iw=DETAIL)
    cv.rect(136.5, yb - 21, 4.5, 5.5, C('#fff4c8'), ink=INK, iw=DETAIL)
    cv.line([(4, yb - 53), (100, yb - 54)], 0.6, C('#ffe8c8'), a=0.7)
    cv.rect(10, yb - 57, 70, 3, C('#5a5a64'), ink=INK, iw=DETAIL)                           # roof rack
    for k in range(6):
        cv.rect(12 + k * 13, yb - 54.5, 1, 2, C('#3a3a44'))
    return cv


def car_pickup(col='#3a5a7a'):
    L, Hh = 148, 48
    cv = Canvas(L, Hh, D)
    yb = Hh
    r = 8.0
    body = [(2, yb - 9), (1, yb - 25), (60, yb - 25), (63, yb - 27), (74, yb - 40), (98, yb - 40.5), (106, yb - 27),
            (140, yb - 24.5), (147, yb - 20), (147, yb - 10), (143, yb - 7), (4, yb - 7)]
    m, mk = _body(cv, body, col, yb - 41, yb - 7)
    cv.rect(2, yb - 26.5, 58, 2, shade(m.b, 0.6), ink=m.i, iw=DETAIL)           # bed rail
    cv.rect(61, yb - 26, 0.6, 18, m.d, a=0.9)                                     # cab / bed seam
    for wx in (28, 120):
        cv.ellipse(wx, yb - r, r + 2.4, r + 2.0, C('#120e16'), mode='atop')
        _wheel(cv, wx, yb, r, rim='#d8d0b8')
    _glass(cv, [(76, yb - 38.5), (97, yb - 38.8), (103.5, yb - 28), (70, yb - 28)], 5)
    cv.rect(86, yb - 38.8, 1.6, 11, m.d)
    cv.rect(98, yb - 25.8, 0.5, 16, m.d, a=0.8)
    cv.rect(90, yb - 24, 4, 1.1, C('#d8dce4'), ink=m.d, iw=0.3)
    # stuff in the bed: a tarp bundle and a ladder
    cv.fill_poly([(10, yb - 26), (14, yb - 31), (40, yb - 32), (46, yb - 26)], C('#6a7a4a'), ink=INK, iw=DETAIL)
    cv.line([(8, yb - 30), (58, yb - 33)], 0.8, C('#b8b0a0'), ink=INK, iw=0.3)
    cv.rect(0.5, yb - 14, 5, 7, C('#c8ccd4'), ink=INK, iw=DETAIL)
    cv.rect(142.5, yb - 14, 5, 7, C('#c8ccd4'), ink=INK, iw=DETAIL)
    cv.rect(1.5, yb - 23, 3.5, 7, C('#c83a3a'), ink=INK, iw=DETAIL)
    cv.rect(142, yb - 20, 5, 5, C('#fff4c8'), ink=INK, iw=DETAIL)
    cv.rect(4, yb - 16, 140, 1.4, C('#e8ecf0'), a=0.6)
    cv.line([(74, yb - 40), (98, yb - 40.5)], 0.6, C('#ffe8c8'), a=0.75)
    return cv


def train_el():
    """Two coupled elevated-line cars (~400 u): fluted stainless body, maroon stripe, lit windows with riders."""
    L, Hh = 400, 38
    cv = Canvas(L, Hh, D)
    rs = rng_of('train')
    car_w = 196
    for ci in range(2):
        x0 = 2 + ci * (car_w + 4)
        yb = Hh - 5
        top = 4
        body = M(C('#aab2bc'))
        pts = [(x0 + 3, yb), (x0, yb - 4), (x0, top + 4), (x0 + 4, top), (x0 + car_w - 4, top), (x0 + car_w, top + 4),
               (x0 + car_w, yb - 4), (x0 + car_w - 3, yb)]
        lay = cv.layer()
        lay.fill_poly(pts, body.b)
        cv.merge(lay, ink=body.i, iw=MAJOR)
        mk = cv.poly_mask(pts)
        cv.vgrad(x0, top, car_w, yb - top, [(0.0, body.h), (0.25, body.l), (0.6, body.b), (1.0, body.s)], mk=mk,
                 mode='atop')
        for k in range(int(car_w / 2.2)):                                  # fluting
            cv.rect(x0 + 1 + k * 2.2, yb - 9, 0.5, 7, body.s, a=0.6, mode='atop')
        cv.rect(x0, yb - 11, car_w, 2.6, C('#8a2a34'), mode='atop')       # stripe
        cv.rect(x0, yb - 11, car_w, 0.6, C('#d86a6a'), a=0.7, mode='atop')
        cv.rect(x0 + 2, top - 2.5, car_w - 4, 2.5, C('#7a828c'), ink=body.i, iw=DETAIL)   # roof
        for k in range(3):
            cv.rect(x0 + 30 + k * 60, top - 5.5, 18, 3.4, C('#8a929c'), ink=body.i, iw=DETAIL)
        # windows (lit) and doors
        doors = [x0 + 40, x0 + car_w - 58]
        wy0, wy1 = top + 5, top + 15
        xx = x0 + 8
        while xx < x0 + car_w - 14:
            if any(d - 2 <= xx <= d + 20 for d in doors):
                xx += 4
                continue
            ww = 11
            cv.rect(xx, wy0, ww, wy1 - wy0, C('#ffe8b0'), ink=C('#2a2830'), iw=DETAIL)
            cv.vgrad(xx, wy0, ww, wy1 - wy0, [C('#fff4d0'), C('#ffd890'), C('#e8a860')], mode='atop')
            if rs.random() < 0.55:                                          # rider silhouette
                px_ = xx + rs.uniform(3, ww - 3)
                sil = C('#6a4a40')
                cv.ellipse(px_, wy1 - 6, 1.5, 1.8, sil)
                cv.rect(px_ - 2.4, wy1 - 4.3, 4.8, 4.3, sil)
            cv.fill_poly([(xx + 2, wy0), (xx + 5, wy0), (xx + 2.5, wy1), (xx - 0.5, wy1)], C('#ffffff'), a=0.25,
                         mode='atop')
            xx += ww + 3
        for d in doors:
            cv.rect(d, top + 3, 18, yb - top - 4, body.s, ink=body.i, iw=DETAIL)
            cv.rect(d + 8.75, top + 3, 0.5, yb - top - 4, body.d)
            for dx_ in (d + 1.5, d + 10.5):
                cv.rect(dx_, wy0, 6, 11, C('#ffe8b0'), ink=C('#2a2830'), iw=DETAIL)
        # cab end windows + head/tail lights
        if ci == 0:
            cv.rect(x0 + 1.5, wy0, 5, 9, C('#3a4458'), ink=C('#2a2830'), iw=DETAIL)
            cv.ellipse(x0 + 2.5, yb - 6, 1.2, 1.2, C('#ff4a3a'))
        else:
            cv.rect(x0 + car_w - 6.5, wy0, 5, 9, C('#3a4458'), ink=C('#2a2830'), iw=DETAIL)
            cv.ellipse(x0 + car_w - 2.5, yb - 6, 1.4, 1.4, C('#fff4c8'))
        # bogies
        for bx in (x0 + 26, x0 + car_w - 26):
            cv.rect(bx - 14, yb, 28, 2.5, C('#2a2a30'), ink=INK, iw=DETAIL)
            for wx in (bx - 8, bx + 8):
                cv.ellipse(wx, Hh - 2.6, 2.6, 2.6, C('#3a3a42'), ink=INK, iw=DETAIL)
        cv.rect(x0, top, car_w, 0.6, C('#ffe8c8'), a=0.6)
    cv.rect(198, 14, 4, 16, C('#3a3a44'), ink=INK, iw=DETAIL)                 # gangway
    return cv


def pigeon_strip():
    """8 frames of 16x12 u (32x24 tx): idle 0-1, peck 2-3, fly 4-7. Anchor = feet, bottom-centre."""
    cv = Canvas(16 * 8, 12, D)
    body = M(C('#8c90a0'))
    wing = M(C('#6e7284'))
    neck = C('#5e8a7a')
    for f in range(8):
        ox = f * 16 + 8
        fy = 12
        lay = cv.layer(f * 16, 0, 16, 12)
        if f < 4:
            head_dx, head_dy = {0: (3.6, -8.2), 1: (4.2, -7.6), 2: (5.0, -4.8), 3: (5.4, -2.6)}[f]
            tilt = {0: 0.0, 1: 0.1, 2: 0.45, 3: 0.75}[f]
            # legs
            lay.line([(ox - 0.6, fy - 2.6), (ox - 0.9, fy - 0.2)], 0.45, C('#c86e70'))
            lay.line([(ox + 0.8, fy - 2.6), (ox + 1.0, fy - 0.2)], 0.45, C('#c86e70'))
            # body (tilts forward when pecking)
            cx, cy = ox - 0.3, fy - 4.6 + tilt * 0.6
            pts = [(cx - 5.2, cy - 0.4 - tilt), (cx - 2.5, cy - 2.6), (cx + 2.2, cy - 2.8 + tilt * 0.8),
                   (cx + head_dx - 2.2, cy + head_dy * 0.35 + 1.0), (cx + 3.4, cy + 1.6), (cx - 1.5, cy + 2.4)]
            lay.fill_poly(pts, body.b)
            lay.ellipse(cx + head_dx * 0.55, cy + head_dy * 0.42 + 0.6, 1.5, 2.0, neck)
            hx, hy = cx + head_dx, cy + head_dy * 0.62 + 2.6
            lay.ellipse(hx, hy, 1.7, 1.5, body.l)
            lay.fill_poly([(hx + 1.4, hy - 0.3), (hx + 2.7, hy + 0.2 + tilt), (hx + 1.4, hy + 0.6)], C('#3a3438'))
            lay.ellipse(hx + 0.4, hy - 0.4, 0.4, 0.4, C('#e88a3a'))
            # folded wing with two dark bars
            lay.fill_poly([(cx - 4.5, cy - 0.8), (cx + 1.6, cy - 1.8), (cx + 1.0, cy + 1.0), (cx - 3.6, cy + 1.2)],
                          wing.b, mode='atop')
            for bx in (cx - 1.4, cx - 0.2):
                lay.line([(bx, cy - 1.4), (bx - 0.6, cy + 0.8)], 0.45, C('#3a3a4a'), mode='atop')
            lay.vgrad(cx - 6, cy - 3, 14, 6, [body.l, body.b, body.s], a=0.5, mode='atop')
        else:
            k = f - 4
            cx, cy = ox, 5.6 + [0.0, 0.6, 1.2, 0.6][k]
            ang = [-1.0, -0.2, 0.75, -0.2][k]
            lay.fill_poly([(cx - 4.8, cy + 0.2), (cx - 1.0, cy - 1.6), (cx + 3.0, cy - 1.0), (cx + 4.4, cy + 0.2),
                           (cx + 2.4, cy + 1.6), (cx - 2.4, cy + 1.4)], body.b)
            lay.ellipse(cx + 4.6, cy - 0.6, 1.4, 1.2, body.l)
            lay.fill_poly([(cx + 5.6, cy - 0.8), (cx + 6.8, cy - 0.4), (cx + 5.6, cy - 0.1)], C('#3a3438'))
            lay.fill_poly([(cx - 4.8, cy + 0.2), (cx - 7.2, cy - 0.8), (cx - 7.0, cy + 1.4)], wing.s)
            # wings: far wing behind, near wing in front
            tipx = cx - 2.0
            tipy = cy + ang * 5.2
            lay.fill_poly([(cx - 1.4, cy - 0.6), (cx + 1.8, cy - 0.6), (tipx + 1.0, tipy), (tipx - 3.6, tipy + 0.6)],
                          wing.b)
            lay.line([(tipx - 3.4, tipy + 0.5), (tipx + 0.8, tipy)], 0.5, C('#3a3a4a'))
            lay.vgrad(cx - 8, cy - 6, 16, 9, [body.l, body.b, body.s], a=0.4, mode='atop')
        cv.merge(lay, ink=C('#2a2632'), iw=0.5)
    return cv


def bird_strip():
    """4-frame flap strip, 12x8 u cells (24x16 tx): a distant gull silhouette, light grey (engine darkens it)."""
    cv = Canvas(12 * 4, 8, D)
    col = C('#d8d4dc')
    for f in range(4):
        cx, cy = f * 12 + 6, 4.4
        lift = [-2.6, -0.6, 1.8, -0.6][f]
        pts = [(cx - 5.4, cy + lift), (cx - 2.4, cy + lift * 0.35 - 0.6), (cx, cy + 0.4), (cx + 2.4, cy + lift * 0.35 - 0.6),
               (cx + 5.4, cy + lift)]
        cv.line(pts, 0.9, col)
        cv.ellipse(cx, cy + 0.5, 1.3, 0.7, col)
    return cv


def silhouette_strip():
    """6-frame walk, 24x48 u cells (48x96 tx): dark person silhouette with soft frosted-glass edges."""
    cv = Canvas(24 * 6, 48, D)
    col = C('#2a2430')
    for f in range(6):
        cx = f * 24 + 12
        ph = f / 6 * 2 * math.pi
        sw = math.sin(ph)
        bob = abs(math.cos(ph)) * 0.8
        hip = (cx, 25 + bob)
        lay = cv.layer(f * 24, 0, 24, 48)
        lay.ellipse(cx + 0.6, 6.5 + bob, 3.4, 4.0, col)                       # head
        lay.fill_poly([(cx - 4.2, 11.5 + bob), (cx + 4.4, 11.5 + bob), (cx + 3.6, 26 + bob), (cx - 3.6, 26 + bob)],
                      col)                                                    # coat/torso
        for s, k in ((1, 1.0), (-1, 0.75)):                                    # legs (far one lighter later)
            a = sw * 0.42 * s
            knee = (hip[0] + math.sin(a) * 9, hip[1] + math.cos(a) * 9)
            foot = (knee[0] + math.sin(a - 0.25 * abs(s)) * 10, min(47.5, knee[1] + 10.5))
            lay.line([hip, knee, foot], 3.0, col)
            lay.line([foot, (foot[0] + 2.4, foot[1])], 1.6, col)
        for s in (1, -1):                                                      # arms
            a = -sw * 0.45 * s
            sh_ = (cx + 0.3, 13 + bob)
            el = (sh_[0] + math.sin(a) * 7, sh_[1] + math.cos(a) * 7)
            hd = (el[0] + math.sin(a + 0.25) * 6.5, el[1] + math.cos(a + 0.25) * 6.5)
            lay.line([sh_, el, hd], 2.2, col)
        cv.merge(lay)
    a = cv.px[..., 3]
    soft = blur(a, 1.6, passes=2)
    cv.px[..., :3] = np.array(col[:3], np.float32)[None, None, :] / 255.0 * soft[..., None]
    cv.px[..., 3] = soft
    return cv


def write_shared(out_root):
    d = os.path.join(out_root, '_life')
    os.makedirs(d, exist_ok=True)
    for k in 'abcde':
        cloud(k, 1).save(os.path.join(d, f'cloud_{k}.png'), optimize=True)
    cars = {'car_a': car_sedan('#7a2a34'), 'car_b': car_van(), 'car_c': car_sedan('#e8b830', taxi=True),
            'car_d': car_pickup()}
    for name, cv in cars.items():
        cv.to_image().save(os.path.join(d, f'{name}.png'), optimize=True)
    train_el().to_image().save(os.path.join(d, 'train_el.png'), optimize=True)
    pigeon_strip().to_image().save(os.path.join(d, 'pigeon.png'), optimize=True)
    bird_strip().to_image().save(os.path.join(d, 'bird.png'), optimize=True)
    silhouette_strip().to_image().save(os.path.join(d, 'silhouette.png'), optimize=True)
    print('  _life sprites written')


# ============================================================================ sway sprite templates
def add_sway(R, name, draw, w, h, px_u, py_u, x, y, amp=3.0, speed=1.2, front=False):
    """Register a sway sprite: `draw(cv)` paints it in local coords where (px_u, py_u) is the pivot."""
    R.sway.append({'name': name, 'draw': draw, 'w': w, 'h': h, 'pivot': (px_u, py_u), 'x': round(x, 1),
                   'y': round(y, 1), 'amp': amp, 'speed': speed, 'front': front})


def pennant_draw(col):
    def fn(cv):
        c = C(col)
        cv.fill_poly([(0.6, 0.6), (3.8, 0.6), (2.2, 4.8)], c, ink=shade(c, 1.8), iw=0.3)
        cv.fill_poly([(2.2, 0.6), (3.8, 0.6), (2.2, 4.8)], shade(c, 0.5), a=0.45, mode='atop')
        cv.rect(0.6, 0.6, 3.2, 0.5, light(c, 1.5), a=0.6, mode='atop')
    return fn


def garment_draw(kind, col):
    """Laundry piece hanging from a peg at (7, 2) u."""
    def fn(cv):
        c = C(col)
        x, y = 7.0, 2.0
        if kind == 'sheet':
            cv.fill_poly([(x - 4, y), (x + 4, y + 0.3), (x + 4.5, y + 11), (x - 3.5, y + 10)], c, ink=ink_of(c),
                         iw=DETAIL)
            cv.rect(x - 4, y, 8, 1.5, shade(c, 0.6), mode='atop')
            cv.line([(x + 1, y + 1), (x + 1.6, y + 10)], 0.4, shade(c, 0.7), a=0.6, mode='atop')
            cv.fill_poly([(x + 1.5, y), (x + 4, y + 0.3), (x + 4.5, y + 11), (x + 2, y + 10.5)], shade(c, 0.5), a=0.4,
                         mode='atop')
        elif kind == 'shirt':
            cv.fill_poly([(x - 3.5, y), (x + 3.5, y), (x + 5.5, y + 2.5), (x + 3.5, y + 3.5), (x + 3, y + 8),
                          (x - 3, y + 8), (x - 3.5, y + 3.5), (x - 5.5, y + 2.5)], c, ink=ink_of(c), iw=DETAIL)
            cv.fill_poly([(x + 0.5, y), (x + 3.5, y), (x + 5.5, y + 2.5), (x + 3.5, y + 3.5), (x + 3, y + 8),
                          (x + 0.5, y + 8)], shade(c, 0.5), a=0.4, mode='atop')
            cv.line([(x - 1, y), (x, y + 1.6), (x + 1, y)], 0.4, shade(c, 1.0), a=0.8)
        else:
            cv.fill_poly([(x - 1, y), (x + 1, y), (x + 1, y + 4), (x + 2.5, y + 5), (x - 1, y + 5)], c,
                         ink=ink_of(c), iw=DETAIL)
        cv.rect(x - 0.4, y - 1, 0.8, 1.6, C('#d8c8a0'))
    return fn


def hanging_sign_draw(text, w, h, bg, fg, kind='board', chain=6.0):
    """Hanging sign on two chains from a bracket; pivot at the top centre (w/2 + 2, 0.5)."""
    def fn(cv):
        cx = w / 2 + 2
        for sx in (cx - w * 0.32, cx + w * 0.32):
            cv.line([(cx, 0.5), (sx, chain)], 0.4, C('#3a3438'))
            cv.ellipse(sx, chain, 0.6, 0.6, None, ink=C('#3a3438'), iw=0.3)
        b = M(C(bg))
        y0 = chain + 0.5
        if kind == 'fish':
            pts = [(2, y0 + h / 2), (6, y0), (w - 4, y0 + h * 0.15), (w + 2, y0 + h / 2), (w - 4, y0 + h * 0.85), (6, y0 + h)]
            cv.fill_poly(pts, b.b, ink=b.i, iw=MAJOR)
            cv.fill_poly([(w - 4, y0 + h * 0.15), (w + 4, y0 - 1), (w + 4, y0 + h + 1), (w - 4, y0 + h * 0.85)], b.s,
                         ink=b.i, iw=DETAIL)
            cv.ellipse(7, y0 + h * 0.42, 0.9, 0.9, C('#1a1220'))
        elif kind == 'round':
            cv.ellipse(cx, y0 + h / 2, w / 2, h / 2, b.b, ink=b.i, iw=MAJOR)
        else:
            cv.rect(2, y0, w, h, b.b, ink=b.i, iw=MAJOR)
            cv.rect(3.2, y0 + 1.2, w - 2.4, h - 2.4, None, ink=C(fg), iw=0.3, a=0.6)
        cv.vgrad(2, y0, w, h, [b.l, b.b, b.s], a=0.5, mode='atop')
        if text:
            cv.text(text, 'sign' if len(text) <= 5 else 'cond', min(h * 0.5, w / max(1, len(text)) * 1.5), cx,
                    y0 + h / 2 + 0.3, C(fg), 'mm', tracking=0.3)
        kit.micro_speckle(cv, 2, y0, w, h, abs(hash(text)) % 999, amt=0.05)
        cv.rect(2, y0, w, 0.6, C('#ffe8c8'), a=0.5, mode='atop')
    return fn


def flag_draw(cols, w=18, h=11):
    """Cloth flag attached at its left edge (pivot (0.5, 0.5)); horizontal stripes, a soft fold shade."""
    def fn(cv):
        n = len(cols)
        pts = [(0.5, 0.5), (w * 0.5, 1.4), (w, 0.6), (w - 1, h * 0.55), (w + 0.2, h + 0.4), (w * 0.5, h - 0.6),
               (0.5, h + 0.5)]
        lay = cv.layer()
        lay.fill_poly(pts, C(cols[0]))
        for i in range(1, n):
            lay.rect(0, 0.5 + i * h / n, w + 1, h / n + 0.5, C(cols[i]), mode='atop')
        lay.hgrad(0, 0, w + 1, h + 1, [C('#ffffff', 0), C('#000000', 60), C('#ffffff', 40), C('#000000', 50)],
                  mode='atop')
        cv.merge(lay, ink=C('#1a1220'), iw=DETAIL)
    return fn


def windsock_draw():
    def fn(cv):
        segs = 5
        for k in range(segs):
            x0 = 1 + k * 4.2
            r0 = 3.4 - k * 0.45
            r1 = 3.4 - (k + 1) * 0.45
            c = C('#e8642a') if k % 2 == 0 else C('#f0ece0')
            cv.fill_poly([(x0, 4 - r0), (x0 + 4.2, 4 - r1 + k * 0.25), (x0 + 4.2, 4 + r1 + k * 0.25), (x0, 4 + r0)], c,
                         ink=INK, iw=DETAIL)
            cv.fill_poly([(x0, 4 + r0 * 0.2), (x0 + 4.2, 4 + r1 * 0.2 + k * 0.25), (x0 + 4.2, 4 + r1 + k * 0.25),
                          (x0, 4 + r0)], shade(c, 0.6), a=0.4, mode='atop')
        cv.ellipse(1, 4, 0.9, 3.5, C('#c8c8c8'), ink=INK, iw=DETAIL)
    return fn


def bracket(R, xw, y, reach, side=1, col='#2a2630'):
    """Wrought-iron sign bracket from the wall at xw reaching `reach` u (painted into the base)."""
    cv = R.cv
    m = M(C(col))
    x1 = xw + side * reach
    cv.rect(min(xw, x1), y - 0.6, abs(reach), 1.2, m.b, ink=m.i, iw=DETAIL)
    cv.line([(xw, y + 6), (xw + side * reach * 0.6, y)], 0.7, m.b, ink=m.i, iw=0.3)
    pts = [(xw + side * reach * (0.25 + 0.06 * k), y - 0.6 - math.sin(k / 4 * math.pi) * 2) for k in range(5)]
    cv.line(pts, 0.4, m.b)
    cv.rect(xw - (1.5 if side > 0 else 0), y - 3, 1.5, 10, m.b, ink=m.i, iw=DETAIL)
    kit.proud_shadow(cv, min(xw, x1), y - 0.6, abs(reach), 1.2, 4.0, a=0.22)
    return x1


def hang_sign(R, xw, y, side, text, w, h, bg, fg, kind='board', reach=None, amp=2.2, speed=1.1):
    reach = reach or (w / 2 + 5)
    tip = bracket(R, xw, y, reach, side)
    hx = xw + side * (reach - w / 2 - 1.5)
    name = 'sway_sign_' + ''.join(ch for ch in (text or kind).lower() if ch.isalnum())[:10]
    add_sway(R, name, hanging_sign_draw(text, w, h, bg, fg, kind), w + 6, h + 9, w / 2 + 2, 0.5, hx, y + 0.6,
             amp=amp, speed=speed)


def flag_pole(R, x, ytop, ybot, cols, w=18, h=11, amp=5.0, speed=1.7, name=None):
    cv = R.cv
    cv.rect(x - 0.6, ytop - 1, 1.2, ybot - ytop + 1, C('#c8c4bc'), ink=INK, iw=DETAIL)
    cv.ellipse(x, ytop - 1.5, 1.2, 1.2, C('#e8c860'), ink=INK, iw=DETAIL)
    add_sway(R, name or ('sway_flag_' + ''.join(c.strip('#')[:2] for c in cols)), flag_draw(cols, w, h), w + 2, h + 2,
             0.5, 0.5, x + 0.6, ytop + 0.5, amp=amp, speed=speed)


# ============================================================================ room lane layers (parallax)
TU = 1024


def _wrap(fn, x):
    for dx in (-TU, 0, TU):
        fn(x + dx)


def layer_chainlot_road():
    """oq_chainlot, parallax 0.85, y = 150: the street beyond the lot fence (far kerb, lamps, two-lane road)."""
    cv = Canvas(TU, 66, D, 0, 150)
    sw = M(C('#8a7670'))
    cv.rect(-2, 190, TU + 4, 7.5, sw.b)
    kit.micro_speckle(cv, 0, 190, TU, 7.5, 71, amt=0.05)
    for k in range(int(TU / 22) + 1):
        cv.rect(k * 22, 190, 0.5, 7.5, sw.d, a=0.6)
    cv.rect(-2, 190, TU + 4, 0.6, sw.h, a=0.6)
    cv.rect(-2, 197.5, TU + 4, 1.2, C('#c8b4a8'))
    cv.rect(-2, 198.7, TU + 4, 1.6, C('#4a3a44'))
    road = M(C('#6a5a64'))
    cv.vgrad(-2, 200.3, TU + 4, 15.7, [mix(road.b, C('#c89a8a'), 0.18), road.b])
    kit.micro_speckle(cv, 0, 200.3, TU, 15.7, 72, amt=0.05)
    for k in range(int(TU / 40)):
        cv.rect(k * 40 + 8, 207.5, 18, 0.9, C('#e8d8a0'), a=0.55)
    for k in range(int(TU / 170) + 1):                          # street lamps on the far kerb
        def lamp(xx):
            cv.rect(xx, 160, 1.2, 31, C('#3a2e36'))
            cv.rect(xx - 0.5, 160, 7, 1.2, C('#3a2e36'))
            cv.ellipse(xx + 6.5, 161.5, 2, 1.2, C('#ffe0a0'))
            cv.radial(xx + 6.5, 163, 6, 5, C('#ffd890'), a=0.25, mode='addfree')
        _wrap(lamp, k * 170 + 60)
    return cv


def layer_bridge_rail():
    """fr_bridge, parallax 0.5, y = 100: a low concrete rail viaduct along the far bank (train lane y = 140)."""
    cv = Canvas(TU, 56, D, 0, 100)
    c = M(C('#56686c'))
    cv.rect(-2, 140, TU + 4, 6, c.b, ink=c.i, iw=0.4)
    cv.rect(-2, 140, TU + 4, 0.8, C('#a8d0d8'), a=0.5)
    for k in range(int(TU / 3) + 1):
        cv.rect(k * 3, 138.6, 1.4, 1.4, c.s)
    cv.rect(-2, 138.2, TU + 4, 0.7, C('#8a9aa0'))
    for k in range(int(TU / 64) + 1):
        def pier(xx):
            cv.fill_poly([(xx - 3, 146), (xx + 3, 146), (xx + 4, 156), (xx - 4, 156)], c.s, ink=c.i, iw=0.3)
        _wrap(pier, k * 64 + 20)
    for k in range(int(TU / 6) + 1):
        cv.rect(k * 6, 134, 0.4, 4.2, c.d, a=0.7)
    cv.rect(-2, 134, TU + 4, 0.5, c.d, a=0.7)
    return cv


def layer_rooftops_el():
    """nm_rooftops, parallax 0.7, y = 150: a riveted steel el structure above the roofline (train lane y = 176)."""
    cv = Canvas(TU, 60, D, 0, 150)
    g = M(C('#2a2440'))
    cv.rect(-2, 176, TU + 4, 8, g.b, ink=C('#0a0814'), iw=0.5)
    for k in range(int(TU / 4)):
        cv.ellipse(k * 4 + 2, 180, 0.4, 0.4, g.l, a=0.6)
    cv.rect(-2, 176, TU + 4, 0.7, C('#ff6ab0'), a=0.35)
    cv.rect(-2, 174.6, TU + 4, 1.0, C('#5a5470'))
    for k in range(int(TU / 80) + 1):
        def col_(xx):
            cv.rect(xx - 2.5, 184, 5, 26, g.s, ink=C('#0a0814'), iw=0.4)
            cv.line([(xx - 2.5, 186), (xx - 18, 184)], 1.0, g.s)
            cv.line([(xx + 2.5, 186), (xx + 18, 184)], 1.0, g.s)
            cv.ellipse(xx + 10, 172, 0.9, 0.9, C('#ff4a3a'))
            cv.rect(xx + 9.6, 172.5, 0.6, 2.4, g.s)
        _wrap(col_, k * 80 + 30)
    return cv


ROOM_LAYERS = {
    'oq_chainlot': [('road', layer_chainlot_road, 0.85, 150)],
    'fr_bridge': [('rail', layer_bridge_rail, 0.5, 100)],
    'nm_rooftops': [('el', layer_rooftops_el, 0.7, 150)],
}


# ============================================================================ per-room extras
DAY = {'old_quarter', 'canal_market', 'ironworks', 'floodgate'}


def room_extras(R):
    """Additions that need the finished facades (called before the realism pass)."""
    fn = EXTRAS.get(R.id)
    if fn:
        fn(R)
    if R.district == 'underline' and not R.interior:
        ceiling_grates(R)


def ceiling_grates(R):
    """Street-level ventilation grates in the Underline ceiling, cold daylight falling through (shafts)."""
    cv = R.cv
    rs = R.rng('grates')
    xs = list(np.arange(200, R.W - 80, 420)) if R.id != 'ul_vault' else [300.0, 760.0]
    for gx in xs:
        gx = float(gx) + rs.uniform(-30, 30)
        if R.id == 'ul_station':
            gx = round(gx / 64) * 64 + 26
        gw = 34
        cv.rect(gx, 2, gw, 12, C('#141a18'), ink=C('#060808'), iw=MAJOR)
        cv.vgrad(gx + 1, 3, gw - 2, 10, [C('#d4e6e0'), C('#8eaaa2')], em=1.0)
        for k in range(int(gw / 3)):
            cv.rect(gx + 1 + k * 3, 3, 1.1, 10, C('#1e2624'), em=0.0)
        cv.rect(gx + 1, 7.5, gw - 2, 1, C('#1e2624'))
        cv.radial(gx + gw / 2, 24, gw * 0.9, 18, C('#c8e8e0'), a=0.10, mode='add')
        R.glow(gx + gw / 2, 10, 30, '#d8f0ea', 0.25, 'none')
        R.shafts.append({"x": round(gx + gw / 2, 1), "y": 12.0, "w": round(gw * 1.3, 1), "h": 200.0,
                         "angle": round(rs.uniform(-8, 8), 1), "color": "#cfe8e0", "energy": 0.12})


def ex_oq_kettle(R):
    hang_sign(R, 1205, 150, -1, 'PAWN', 20, 11, '#2a3a5a', '#f0d070', reach=16)


def ex_oq_brickrow(R):
    hang_sign(R, 360, 152, 1, 'ROOMS', 22, 10, '#5a2a2a', '#f4e8c8', reach=16)
    hang_sign(R, 1100, 148, -1, '', 14, 14, '#c8a040', '#2a2026', kind='round', reach=12)


def ex_cm_gate(R):
    for f in R.data['facades']:
        if f['kind'] == 'market_arch':
            x0, w = f['x'], f['w']
            flag_pole(R, x0 + 14, 40, 84, ['#e84a3a', '#f8d040'], name='sway_flag_market_a')
            flag_pole(R, x0 + w - 14, 40, 84, ['#3aa0d8', '#f4f0e8'], name='sway_flag_market_b')
        if f['kind'] == 'shopfront':
            hang_sign(R, f['x'] + f['w'] - 6, 150, -1, 'TEA', 16, 10, '#2e5a4a', '#f4e8c8', reach=13)
            break


def ex_cm_pier(R):
    for f in R.data['facades']:
        if f['kind'] == 'fish_hall':
            hang_sign(R, f['x'] + f['w'] - 4, 156, 1, '', 22, 9, '#5a8aa0', '#f4f0e8', kind='fish', reach=16)


def ex_iy_gate(R):
    f = R.data['facades'][0]
    x = f['x'] + 120
    cv = R.cv
    cv.rect(x - 0.8, 60, 1.6, FB - 60, C('#8a8e96'), ink=INK, iw=DETAIL)
    cv.rect(x - 0.8, 60, 1.6, FB - 60, C('#ffb070'), a=0.25, mode='atop')
    add_sway(R, 'sway_windsock', windsock_draw(), 24, 10, 1.0, 4.0, x + 0.8, 63, amp=7.0, speed=0.9)


def ex_fr_pumpstation(R):
    f = R.data['facades'][0]
    flag_pole(R, f['x'] + f['w'] - 8, 6, 52, ['#e8642a', '#e8642a', '#2a2a30'], w=16, h=10, amp=6.0, speed=2.0,
              name='sway_flag_flood')


def ex_ul_station(R):
    cv = R.cv
    x = 1480.0
    for cx in (x - 14, x + 14):
        cv.line([(cx, 40), (cx, 46)], 0.5, C('#6a6a6a'))
    add_sway(R, 'sway_sign_trains', hanging_sign_draw('TO TRAINS', 40, 9, '#1e3e5a', '#f4f0e8', chain=4.0), 46, 15,
             22, 0.5, x, 46.5, amp=1.2, speed=0.7)


EXTRAS = {'oq_kettle': ex_oq_kettle, 'oq_brickrow': ex_oq_brickrow, 'cm_gate': ex_cm_gate, 'cm_pier': ex_cm_pier,
          'iy_gate': ex_iy_gate, 'fr_pumpstation': ex_fr_pumpstation, 'ul_station': ex_ul_station}


# ============================================================================ presets
HAZE = {
    'old_quarter': {"color": "#f4a87a", "far": 0.14, "mid": 0.06},
    'canal_market': {"color": "#f0e0b0", "far": 0.12, "mid": 0.05},
    'ironworks': {"color": "#b8987e", "far": 0.15, "mid": 0.07},
    'neon_mile': {"color": "#6a2a6a", "far": 0.12, "mid": 0.06},
    'floodgate': {"color": "#7a9494", "far": 0.18, "mid": 0.08},
    'warehouse': {"color": "#3e5450", "far": 0.12, "mid": 0.06},
    'underline': {"color": "#3a504a", "far": 0.12, "mid": 0.06},
}
GRADE = {
    'old_quarter': {"lift": "#120a14", "gain": "#fff0dc", "saturation": 1.04, "contrast": 1.05, "vignette": 0.2},
    'canal_market': {"lift": "#06100f", "gain": "#fff3d8", "saturation": 1.05, "contrast": 1.04, "vignette": 0.16},
    'ironworks': {"lift": "#0a0e1a", "gain": "#ffe9d2", "saturation": 0.98, "contrast": 1.06, "vignette": 0.22},
    'neon_mile': {"lift": "#14081f", "gain": "#ecfbff", "saturation": 1.08, "contrast": 1.06, "vignette": 0.26},
    'floodgate': {"lift": "#081211", "gain": "#e9f8f4", "saturation": 0.92, "contrast": 1.03, "vignette": 0.24},
    'warehouse': {"lift": "#0a110c", "gain": "#ecfff0", "saturation": 0.94, "contrast": 1.04, "vignette": 0.22},
    'underline': {"lift": "#06110c", "gain": "#e4fff0", "saturation": 0.92, "contrast": 1.05, "vignette": 0.28},
}
CLOUDS = {   # tint, alpha, count, y range, speed
    'old_quarter': ('#ffd6c0', 0.85, 5, [8, 62], [2.5, 6]),
    'canal_market': ('#ffffff', 0.92, 6, [6, 70], [3, 8]),
    'ironworks': ('#c8b4ac', 0.8, 5, [6, 58], [3, 7]),
    'neon_mile': ('#4a3060', 0.55, 4, [6, 60], [2, 5]),
    'floodgate': ('#748890', 0.9, 7, [4, 56], [5, 11]),
    'warehouse': ('#30444a', 0.6, 4, [6, 50], [2, 5]),
}
SHAFT_COL = {'old_quarter': '#ffd9a0', 'canal_market': '#fff0c8', 'ironworks': '#e0e8f0', 'neon_mile': '#e0b0ff',
             'floodgate': '#c8e0e4', 'warehouse': '#d8fff0', 'underline': '#cfe8e0'}
WATER_TINT = {'canal_market': '#bfeee8', 'floodgate': '#a8d0d4', 'underline': '#a8d8c8', 'warehouse': '#c8e8e0',
              'old_quarter': '#ffd8c0', 'neon_mile': '#e0b0ff', 'ironworks': '#d0d8e8'}


# ============================================================================ assembly
def _pick_windows(R, n_lo, n_hi):
    recs = [r for r in R.life_log if r.get('type') == 'window' and r.get('ok', True)]
    recs += R.windows_extra
    recs = [r for r in recs if r['rect'][2] >= 6 and r['rect'][3] >= 6 and r['rect'][0] >= 0
            and r['rect'][0] + r['rect'][2] <= R.W]
    # de-duplicate overlapping rects
    out = []
    for r in sorted(recs, key=lambda q: (q['rect'][0], q['rect'][1])):
        x, y, w, h = r['rect']
        if any(abs(x - o['rect'][0]) < 2 and abs(y - o['rect'][1]) < 2 for o in out):
            continue
        out.append(r)
    if len(out) <= n_hi:
        return out
    # spread across the room: one per slot, alternating lit / dark preference, shops first
    slots = n_hi
    picked = []
    for s in range(slots):
        a, b = R.W * s / slots, R.W * (s + 1) / slots
        cands = [r for r in out if a <= r['rect'][0] + r['rect'][2] / 2 < b and r not in picked]
        if not cands:
            continue
        want_lit = s % 2 == 0
        cands.sort(key=lambda r: (r['kind'] != 'shop', r['lit'] != want_lit, abs(r['rect'][1] - 80)))
        picked.append(cands[0])
    if len(picked) < n_lo:
        rest = [r for r in out if r not in picked]
        picked += rest[:n_lo - len(picked)]
    return sorted(picked, key=lambda r: r['rect'][0])


def _signs(R):
    recs = [r for r in R.life_log if r.get('type') == 'sign'] + R.signs_extra
    out = []
    # merge vertical blade signs written one character at a time
    singles = [r for r in recs if len(r.get('text', 'xx')) == 1]
    others = [r for r in recs if len(r.get('text', 'xx')) != 1]
    groups = []
    for r in sorted(singles, key=lambda q: (round(q['rect'][0] + q['rect'][2] / 2), q['rect'][1])):
        cx = r['rect'][0] + r['rect'][2] / 2
        for g in groups:
            gx = g[-1]['rect'][0] + g[-1]['rect'][2] / 2
            if abs(gx - cx) < 3 and r['rect'][1] - (g[-1]['rect'][1] + g[-1]['rect'][3]) < 6 and g[-1]['color'] == r['color']:
                g.append(r)
                break
        else:
            groups.append([r])
    for g in groups:
        x0 = min(q['rect'][0] for q in g)
        y0 = min(q['rect'][1] for q in g)
        x1 = max(q['rect'][0] + q['rect'][2] for q in g)
        y1 = max(q['rect'][1] + q['rect'][3] for q in g)
        out.append({"type": "sign", "rect": [round(x0 + 1, 1), round(y0 + 1, 1), round(x1 - x0 - 2, 1),
                                              round(y1 - y0 - 2, 1)], "pattern": "blink", "color": g[0]['color']})
    for r in others:
        x, y, w, h = r['rect']
        if r.get('pattern'):
            pat = r['pattern']
        else:
            pat = 'blink' if len(r.get('text', '')) <= 7 else 'buzz'
        inset = 0 if r.get('pattern') else 1.0
        out.append({"type": "sign", "rect": [round(x + inset, 1), round(y + inset, 1), round(w - 2 * inset, 1),
                                              round(h - 2 * inset, 1)], "pattern": pat, "color": r['color']})
    return [s for s in out if 0 <= s['rect'][0] < R.W and s['rect'][2] > 2 and s['rect'][3] > 1]


def _pigeon_spots(R, n):
    walk0 = R.walk[0]
    avoid = [d['x'] for d in R.data.get('doors', [])] + [p['x'] for p in R.data.get('props', [])]
    for side, ex in R.data.get('exits', {}).items():
        if isinstance(ex, dict) and 'x0' in ex:
            avoid += [ex['x0'], ex['x1']]
    rs = R.rng('pigeons')
    spots = []
    cands = list(np.arange(80, R.W - 80, 37))
    rs.shuffle(cands)
    blk = []
    for b in R.data.get('blockers', []):
        bb = b if isinstance(b, list) else [b['x'], b['y'], b['w'], b['h']]
        blk.append((bb[0] - 30, bb[0] + bb[2] + 30))
    for x in cands:
        if any(a0 <= x <= a1 for a0, a1 in blk):
            continue
        if all(abs(x - a) > 46 for a in avoid) and all(abs(x - s[0]) > R.W / (n + 1) for s in spots):
            spots.append((float(x), float(walk0 + rs.uniform(8, 16))))
        if len(spots) >= n:
            break
    return spots


def lanes_for(R):
    rid = R.id
    if rid == 'oq_chainlot':
        return [{"type": "train", "y": 187.5, "parallax": 0.6, "file": "../_life/train_el.png", "interval": [24, 44]},
                {"type": "pedestrians", "y": 196.5, "parallax": 0.85, "scale": 0.8, "x": [0, R.W], "rate": 0.12},
                {"type": "traffic", "y": 212.0, "parallax": 0.85,
                 "files": ["../_life/car_a.png", "../_life/car_b.png", "../_life/car_c.png", "../_life/car_d.png"],
                 "rate": 0.07, "lights": True}]
    if rid == 'cm_canalwalk':
        return [{"type": "pedestrians", "y": 147.5, "parallax": 0.5, "scale": 0.34, "x": [0, R.W], "rate": 0.3}]
    if rid == 'fr_bridge':
        return [{"type": "train", "y": 140.0, "parallax": 0.5, "file": "../_life/train_el.png", "interval": [22, 40]}]
    if rid in ('iy_spur', 'iy_gate'):
        return [{"type": "train", "y": 200.0, "parallax": 0.5, "file": "../_life/train_el.png", "interval": [28, 50]}]
    if rid == 'nm_rooftops':
        return [{"type": "train", "y": 176.0, "parallax": 0.7, "file": "../_life/train_el.png", "interval": [20, 36]}]
    return []


def interior_shafts(R):
    out = []
    col = SHAFT_COL.get(R.district, '#ffe0b0')
    for r in R.life_log:
        if r.get('type') == 'window' and r.get('interior_window'):
            x, y, w, h = r['rect']
            ang = -8.0 if x + w / 2 < R.W / 2 else 8.0
            out.append({"x": round(x + w / 2, 1), "y": round(y, 1), "w": round(w * 1.25, 1),
                        "h": round(min(300.0, 318 - y), 1), "angle": ang, "color": col, "energy": 0.14})
    return out[:3]


def foundry_shafts(R):
    out = []
    for f in R.data['facades']:
        if f['kind'] == 'foundry_wall':
            for k in range(int(f['w'] / 60)):
                if k % 2:
                    continue
                wx = f['x'] + 10 + k * 60
                out.append({"x": wx + 20.0, "y": 40.0, "w": 46.0, "h": 260.0, "angle": -12.0, "color": "#d8e4f0",
                            "energy": 0.14})
    return out[:4]


def warehouse_shafts(R):
    out = []
    for f in R.data['facades']:
        if f['kind'] == 'warehouse_wall':
            for k in range(int(f['w'] / 160)):
                sx = f['x'] + 90 + k * 160
                if k % 2 == 0:
                    out.append({"x": sx + 50.0, "y": 16.0, "w": 90.0, "h": 260.0, "angle": -6.0, "color": "#cfe8e0",
                                "energy": 0.10})
        if f['kind'] == 'crane_hall':
            for k in range(4):
                sx = f['x'] + 80 + k * 280
                if sx + 30 < f['x'] + f['w']:
                    out.append({"x": sx + 30.0, "y": 0.0, "w": 70.0, "h": float(FB + 60), "angle": -10.6,
                                "color": "#c8e0e8", "energy": 0.12})
    return out[:5]


def assemble(R, js, d):
    """Write the sway sprites and return the v2.1 room.json fields."""
    ext = not R.interior
    has_sky = any(L['name'] == 'sky' for L in js['layers'])
    out = {}
    dist = R.district
    if ext and has_sky and dist in CLOUDS:
        tint, al, cnt, yr, sp = CLOUDS[dist]
        out['clouds'] = {"files": [f"../_life/cloud_{k}.png" for k in 'abcde'], "count": cnt, "y": yr, "speed": sp,
                         "parallax": 0.08, "tint": tint, "alpha": al}
    out['haze'] = dict(HAZE.get(dist, HAZE['old_quarter']))
    g = dict(GRADE.get(dist, GRADE['old_quarter']))
    if R.interior:
        g['vignette'] = round(min(g['vignette'], 0.2), 2)
        g['contrast'] = round(min(g['contrast'], 1.04), 2)
    out['grade'] = g
    life = []
    # windows
    wins = _pick_windows(R, 6 if ext else 1, 12 if ext else 4)
    for r in wins:
        life.append({"type": "window", "rect": r['rect'], "kind": r['kind'], "lit": bool(r['lit'])})
    # lanes
    life += lanes_for(R)
    # pigeons + birds (daytime exteriors with a sky)
    if ext and dist in DAY and R.id not in ('iy_foundry',):
        for (x, y) in _pigeon_spots(R, 2 if R.W >= 1400 else 1):
            life.append({"type": "pigeons", "x": round(x, 1), "y": round(y, 1), "count": 4})
        if has_sky:
            life.append({"type": "birds", "y": [14, 70], "rate": 0.04 if dist == 'floodgate' else 0.06})
    # sway sprites
    made = set()
    for s in R.sway:
        fn = s['name'] + '.png'
        if s['name'] not in made:
            cv = Canvas(s['w'], s['h'], D)
            s['draw'](cv)
            cv.to_image().save(os.path.join(d, fn), optimize=True)
            made.add(s['name'])
        life.append({"type": "sway", "file": fn, "x": s['x'], "y": s['y'],
                     "pivot": [round(s['pivot'][0] * D, 1), round(s['pivot'][1] * D, 1)], "amp": s['amp'],
                     "speed": s['speed'], "front": bool(s['front'])})
    # water
    water = []
    for wr in R.water:
        x, y, w, h = wr['rect']
        if w < 8 or h < 2:
            continue
        if R.id == 'cm_canalwalk' and wr['kind'] == 'canal' and y >= FB:
            continue           # replaced by the exact blocker rects below
        water.append(wr)
    if R.id == 'cm_canalwalk':
        for b in R.data.get('blockers', []):
            if b.get('kind') == 'water':
                water.insert(0, {"rect": [b['x'], b['y'], b['w'], b['h']], "kind": "canal", "tint": "#bfeee8"})
    puddles = [w_ for w_ in water if w_['kind'] == 'puddle'][:4]
    canals = [w_ for w_ in water if w_['kind'] != 'puddle']
    for w_ in canals:
        life.append({"type": "water", "rect": w_['rect'], "speed": 12 if w_['rect'][3] > 30 else 8,
                     "tint": WATER_TINT.get(dist, '#bfe6f0'), "alpha": 0.32})
    for w_ in puddles:
        life.append({"type": "water", "rect": w_['rect'], "speed": 5, "tint": WATER_TINT.get(dist, '#bfe6f0'),
                     "alpha": 0.24})
    # shafts
    shafts = list(R.shafts)
    if R.interior:
        shafts += interior_shafts(R)
    if R.id == 'iy_foundry':
        shafts += foundry_shafts(R)
    if dist == 'warehouse':
        shafts += warehouse_shafts(R)
    for s in shafts:
        life.append(dict({"type": "shaft"}, **s))
    # neon sign animation
    life += _signs(R)
    out['life'] = life
    return out
