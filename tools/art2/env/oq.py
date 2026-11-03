"""Backstreet Oath env v2 -- Old Quarter facades, lot pieces and the Lucky Spoon interior (world units)."""
import math

import numpy as np

from raster import C, mix, shade, light, ink_of, tone, value_noise, rng_of, blur
import kit
from kit import M, MAJOR, DETAIL, window, door, awning, cornice, parapet, brick_wall, drainpipe, fire_escape, \
    cable, string_lights, ac_unit, stoop, neon_text, painted_text, poster, tag, graffiti_piece, cast_shadow_rect, \
    concrete_panel, corrugated, plywood, stucco
from room import FACADE_BOTTOM as FB, H, INT_WALL_BOTTOM, light_pool, sun_rim, weeds, puddle

FACADES = {}


def facade(name):
    def deco(f):
        FACADES[name] = f
        return f
    return deco


BRICKS = ['#9a4a3c', '#8a5446', '#a8644a', '#7e4650', '#94503e']
TRIM = ['#d8ccb4', '#c8bca0', '#e0d4c0', '#b8b0a0']


def split(w, target, rs, minw=60):
    n = max(1, int(round(w / target)))
    ws = []
    left = w
    for i in range(n - 1):
        v = max(minw, min(left - minw * (n - i - 1), target * rs.uniform(0.8, 1.2)))
        ws.append(v)
        left -= v
    ws.append(left)
    return ws


# ----------------------------------------------------------------------------- rowhouses
@facade("rowhouse")
def f_rowhouse(R, x0, w, f):
    cv = R.cv
    rs = R.rng('row', x0)
    widths = split(w, 84, rs, 64)
    xx = x0
    houses = []
    for i, hw in enumerate(widths):
        top = rs.choice([38, 42, 46, 50])
        brick = BRICKS[(i + int(x0 / 100)) % len(BRICKS)]
        trim = TRIM[i % len(TRIM)]
        brick_wall(cv, xx, top, hw, FB - top, C(brick), seed=hash((R.id, xx)) % 99999, soot=0.32)
        cornice(cv, xx, top, hw, C(trim), h=4.5)
        parapet(cv, xx - 1, top - 5, hw + 2, C(shade(C(brick), 0.5)), h=5)
        sun_rim(R, xx, top - 5, FB - 40, w=1.0, a=0.45)
        # two upper floors
        floors = [top + 14, top + 58]
        nwin = 2 if hw < 96 else 3
        for fi, fy in enumerate(floors):
            for k in range(nwin):
                ww = 14
                wx = xx + (hw - nwin * ww) / (nwin + 1) * (k + 1) + ww * k
                lit = rs.random() < (0.45 if fi == 0 else 0.55)
                window(cv, wx, fy, ww, 26, lit=lit, seed=hash((xx, fy, k)) % 9999, frame=trim)
                if rs.random() < 0.3 and fi == 1:
                    flower_box(R, wx - 2, fy + 28, ww + 4, rs)
        # string course above the ground floor
        cv.rect(xx, top + 96, hw, 2.5, C(trim), ink=ink_of(C(trim)), iw=DETAIL)
        # ground floor: door (44 u) on a 3-step stoop + parlour window
        side = rs.random() < 0.5
        dw = 17
        dx = xx + (10 if side else hw - 10 - dw)
        door(cv, dx, FB - 9, dw, 44, C(rs.choice(['#3a5a4a', '#6a2a2a', '#2a3a5a', '#5a4a3a'])),
             lit=rs.random() < 0.5, seed=xx, frame=trim)
        stoop(cv, dx - 4, dw + 8, FB, steps=3)
        wx = xx + (hw - 34 if side else 14)
        window(cv, wx, FB - 50, 20, 32, lit=rs.random() < 0.6, seed=xx + 7, frame=trim, kind='grid')
        # basement vent (soot blackens the brick above it)
        kit.soot_above(cv, wx + 3, FB - 9, 14, h=16, a=0.22, seed=int(wx))
        cv.rect(wx + 2, FB - 9, 16, 6, C('#2a2430'), ink=C('#1a1220'), iw=DETAIL)
        for k in range(6):
            cv.rect(wx + 3 + k * 2.6, FB - 8.5, 0.8, 5, C('#4a4450'))
        houses.append((xx, hw, top))
        if i > 0:
            drainpipe(cv, xx + 0.5, top - 2, FB - 2)
        xx += hw
    # laundry line between the upper floors of two houses
    if len(houses) >= 2:
        (ax, aw, at), (bx, bw, bt) = houses[0], houses[1]
        y = max(at, bt) + 46
        pts = cable(cv, ax + aw * 0.4, y, bx + bw * 0.6, y + 2, sag=7, w=0.5)
        laundry(R, pts, rs)
    # story posters near the street
    poster(cv, x0 + widths[0] - 6, FB - 38, 11, 15, seed=hash((R.id, 'missing')) % 999, kind='missing')
    if len(houses) > 2:
        poster(cv, houses[2][0] - 6, FB - 36, 11, 14, seed=11, kind='lost_cat')
    tag(cv, x0 + 30, FB - 18, 'CD', C('#4a8ad8'), size=6, seed=3, a=0.75)


def flower_box(R, x, y, w, rs):
    cv = R.cv
    cv.rect(x, y, w, 3, C('#6a4a3a'), ink=C('#2a1a1a'), iw=DETAIL)
    for k in range(int(w / 2.2)):
        c = rs.choice([C('#e86a6a'), C('#f0d060'), C('#e8a0c8'), C('#f4f0e0')])
        fx = x + 1 + k * 2.2 + rs.uniform(-0.4, 0.4)
        cv.ellipse(fx, y - rs.uniform(0.5, 2.0), 1.0, 1.0, C('#4a7a3a'))
        if rs.random() < 0.6:
            cv.ellipse(fx, y - rs.uniform(1.0, 2.5), 0.8, 0.8, c, ink=shade(c, 1.6), iw=0.3)


def laundry(R, pts, rs):
    """Washing pegged on the line: each piece is a separate sway sprite (the line itself stays in the base)."""
    import life
    cols = ['#e8e0d0', '#c85a4a', '#5a8ac8', '#e8c860', '#8ab08a', '#f0f0f0']
    for k in range(3, len(pts) - 3, 3):
        x, y = pts[k]
        c = rs.choice(cols)
        kind = rs.choice(['shirt', 'sheet', 'sock', 'shirt'])
        life.add_sway(R, f'sway_laundry_{kind}_{c[1:]}', life.garment_draw(kind, c), 14, 15, 7.0, 2.0, x, y,
                      amp={'sheet': 2.2, 'shirt': 3.2, 'sock': 5.0}[kind], speed=round(rs.uniform(0.9, 1.4), 2))


# ----------------------------------------------------------------------------- diner (Lucky Spoon)
@facade("diner")
def f_diner(R, x0, w, f):
    cv = R.cv
    rs = R.rng('diner', x0)
    top = 104
    # setback brick block behind the diner
    bx0, bw = x0 + 26, w - 52
    brick_wall(cv, bx0, 44, bw, top - 44, C('#7a3e38'), seed=77, calm=True, soot=0.1)
    cornice(cv, bx0, 44, bw, C('#b8a890'), h=3.5)
    for k in range(5):
        window(cv, bx0 + 14 + k * (bw - 40) / 4, 56, 12, 18, lit=k % 2 == 0, seed=k + 31, frame='#b8a890',
               sill=True)
    sun_rim(R, bx0, 40, top, a=0.4)
    # roof sign on struts
    sw, sh = min(w - 50, 216), 36
    sx = x0 + (w - sw) / 2
    sy = 58
    for k in (sx + 18, sx + sw - 20):
        cv.rect(k, sy + sh, 2.5, top - sy - sh, C('#2a2630'), ink=C('#140c18'), iw=DETAIL)
        cv.line([(k, sy + sh), (k + 12, top - 1)], 1.0, C('#2a2630'))
    sm = M(C('#c0383c'))
    cv.rect(sx, sy, sw, sh, sm.b, ink=sm.i, iw=MAJOR)
    kit.proud_shadow(cv, sx, sy, sw, sh, 4.0, a=0.3)
    cv.rect(sx, sy, sw, 1.2, sm.h, mode='atop')
    cv.rect(sx + 2.5, sy + 2.5, sw - 5, sh - 5, C('#24142a'), ink=sm.d, iw=DETAIL)
    # marquee bulbs around the board
    n = int(sw / 5.2)
    for k in range(n):
        for by in (sy + 1.25, sy + sh - 1.25):
            bx = sx + 2.6 + k * (sw - 5.2) / (n - 1)
            on = (k % 3) != 1
            col = C('#ffe08a') if on else C('#8a6040')
            cv.ellipse(bx, by, 0.9, 0.9, col, em=1.0 if on else 0.0)
            if on:
                cv.radial(bx, by, 2.4, 2.4, C('#ffc060'), a=0.25, mode='add')
    neon_text(cv, f.get('sign', 'LUCKY SPOON'), sx + sw / 2 + 9, sy + sh / 2 + 0.5, 15, C('#ffd23a'), tracking=0.9,
              glow=0.45)
    for by in (sy, sy + sh - 2.5):
        kit.log(cv, {'type': 'sign', 'rect': [round(sx + 1, 1), round(by, 1), round(sw - 2, 1), 2.5],
                     'color': '#ffe08a', 'pattern': 'chase'})
    # spoon icon (cyan neon)
    ix, iy = sx + 16, sy + sh / 2
    lay = cv.layer(ix - 8, iy - 14, 16, 28)
    lay.ellipse(ix, iy - 5.5, 3.6, 5.2, C('#7af0ff'))
    lay.ellipse(ix, iy - 5.5, 1.9, 3.4, C('#000000'), mode='erase')
    lay.rect(ix - 0.9, iy - 0.5, 1.8, 10, C('#7af0ff'))
    cv.radial(ix, iy, 9, 12, C('#5ad8ff'), a=0.3, mode='add')
    cv.merge(lay)
    cv.ellipse(ix, iy - 5.5, 3.6, 5.2, None, ink=C('#d8ffff'), iw=0.5, em=1.0, a=0.6)
    R.glow(sx + sw / 2, sy + sh / 2, sw * 0.55, '#ffcf5a', 0.55, 'neon')
    R.glow(ix, iy, 16, '#6ae0ff', 0.4, 'neon')
    # streamline body
    body = M(C('#ece2cc'))
    lay = cv.layer(x0, top - 10, w, FB - top + 12)
    lay.rect(x0 + 4, top, w - 8, FB - top, body.b)
    lay.hgrad(x0 + 4, top, w - 8, FB - top, [body.l, body.b, body.b, body.s], a=0.5, mode='atop')
    # roof cap (red) with rounded ends
    cap = M(C('#b8303a'))
    lay.rect(x0 + 2, top - 7, w - 4, 7, cap.b)
    lay.rect(x0 + 2, top - 7, w - 4, 1.2, cap.h, mode='atop')
    lay.rect(x0 + 2, top - 1.5, w - 4, 1.5, cap.s, mode='atop')
    cv.merge(lay, ink=body.i, iw=MAJOR)
    sun_rim(R, x0 + 4, top - 7, FB - 30, a=0.5)
    # chrome bands + red stripe
    for yy in (top + 4, top + 82):
        chrome_band(cv, x0 + 4, yy, w - 8, 3)
    cv.rect(x0 + 4, top + 9, w - 8, 5, C('#c8343a'), ink=C('#5a1420'), iw=DETAIL)
    cv.rect(x0 + 4, top + 9, w - 8, 1, C('#f06a6a'), mode='atop')
    # window band with booths and customers
    wy0, wy1 = top + 20, top + 79
    dx = R.doors_in(x0, x0 + w)[0]['x'] if R.doors_in(x0, x0 + w) else x0 + w / 2
    xx = x0 + 12
    k = 0
    while xx < x0 + w - 30:
        ww = 34
        if abs((xx + ww / 2) - dx) < 36:
            xx = dx + 22
            continue
        if xx + ww > x0 + w - 12:
            break
        diner_window(R, xx, wy0, ww, wy1 - wy0, rs, k)
        xx += ww + 6
        k += 1
    # entrance with canopy (door 66 u: taller than a 48 u fighter)
    door_w = 24
    dl = dx - door_w / 2
    cv.rect(dl - 3, wy0 - 2, door_w + 6, FB - wy0 + 2, C('#c8c0b0'), ink=C('#3a3038'), iw=MAJOR)
    door(cv, dl, FB, door_w, 66, C('#c0383c'), glass=True, lit=True, seed=5, frame='#a8a8b0',
         step=False, transom=False)
    cv.text('OPEN', 'cond', 4.5, dx, FB - 54, C('#ff5a7a'), 'mm', em=1.0)
    cv.radial(dx, FB - 54, 7, 4, C('#ff4a6a'), a=0.35, mode='add')
    awning(cv, dl - 8, wy0 - 10, door_w + 16, 7, C('#e8e0d0'), C('#c8343a'), stripe=4, valance=2.5)
    # lower tiles: teal / cream checker skirt
    ty0 = top + 86
    mk = cv.rect(x0 + 4, ty0, w - 8, FB - 3 - ty0, C('#e8e0cc'))
    A = np.array(C('#2c8a86')[:3], np.float32) / 255
    B = np.array(C('#e8e0cc')[:3], np.float32) / 255

    def fn(X, Y):
        par = (np.floor((X - x0) / 4) + np.floor((Y - ty0) / 4)) % 2
        c = np.where(par[..., None] > 0.5, A, B)
        fx = ((X - x0) % 4) < 0.5
        fy = ((Y - ty0) % 4) < 0.5
        c = np.where((fx | fy)[..., None], c * 0.85, c)
        return c
    cv.texture(mk, fn)
    kit.weather(cv, x0 + 4, ty0, w - 8, FB - 3 - ty0, 41, soot=0.4, streak=False)
    chrome_band(cv, x0 + 4, FB - 3, w - 8, 3)
    # light spill on the sidewalk
    light_pool(R, x0 + w / 2, FB + 10, w * 0.55, 14, '#ffc070', a=0.22)
    light_pool(R, dx, FB + 8, 22, 10, '#ffd090', a=0.25)
    R.light(x0 + w / 2, FB + 14, w * 0.6, 34, '#ffb060', 0.22)
    R.glow(x0 + w / 2, top + 40, w * 0.5, '#ffc070', 0.3, 'none')
    R.glow(dx, FB - 20, 26, '#ffd090', 0.3, 'none')


def chrome_band(cv, x, y, w, h):
    cv.rect(x, y, w, h, C('#b8bcc8'), ink=C('#3a3a48'), iw=DETAIL)
    cv.rect(x, y, w, h * 0.35, C('#f4f6fa'), mode='atop')
    cv.rect(x, y + h * 0.7, w, h * 0.3, C('#7a7e90'), mode='atop')


def diner_window(R, x, y, w, h, rs, k):
    cv = R.cv
    cv.rect(x - 1.5, y - 1.5, w + 3, h + 3, C('#b8bcc8'), ink=C('#3a3a48'), iw=MAJOR)
    cv.vgrad(x, y, w, h, [C('#fff4d0'), C('#ffd890'), C('#e8a060')], em=1.0)
    # back wall line / menu board inside
    cv.rect(x, y + h * 0.22, w, 1.0, C('#d89060'), a=0.6, em=1.0)
    # pendant lamp
    cv.rect(x + w / 2 - 0.3, y, 0.6, 6, C('#5a4030'), em=1.0)
    cv.fill_poly([(x + w / 2 - 3.5, y + 9), (x + w / 2 + 3.5, y + 9), (x + w / 2 + 1.5, y + 6), (x + w / 2 - 1.5, y + 6)],
                 C('#d8343a'), em=1.0)
    cv.radial(x + w / 2, y + 10, 8, 5, C('#fff0c0'), a=0.5, mode='add')
    # booth backs, table, diners
    by = y + h - 15
    cv.rect(x, by, w, 15, C('#b8343a'), em=1.0)
    cv.rect(x, by, w, 1.2, C('#f07070'), em=1.0)
    for kk in range(0, int(w), 11):
        cv.rect(x + kk, by + 1.2, 0.6, 14, C('#7a1e26'), em=1.0)
    cv.rect(x + 4, by + 3, w - 8, 1.6, C('#e8e0d0'), em=1.0)
    sil = C('#7a4a40')
    seats = [0.3, 0.72] if rs.random() < 0.6 else [rs.uniform(0.3, 0.7)]
    if rs.random() < 0.2:
        seats = []
    for sxf in seats:
        hx = x + w * sxf
        col = mix(sil, rs.choice([C('#3a5a8a'), C('#8a3a3a'), C('#4a6a4a'), C('#6a5a3a')]), 0.4)
        cv.ellipse(hx, by - 6.5, 2.6, 3.0, sil, em=1.0)
        cv.fill_poly([(hx - 4.5, by + 3), (hx - 3.5, by - 3.5), (hx + 3.5, by - 3.5), (hx + 4.5, by + 3)], col, em=1.0)
        if rs.random() < 0.5:
            cv.rect(hx + 3, by + 1.5, 2, 2.5, C('#f4f0e8'), em=1.0)   # cup
    # glass reflection + gloss
    cv.fill_poly([(x + w * 0.1, y), (x + w * 0.3, y), (x + w * 0.05, y + h * 0.7), (x - w * 0.12, y + h * 0.7)],
                 C('#ffffff'), a=0.18, mode='atop')
    cv.rect(x, y, w, 0.8, C('#ffffff'), a=0.8, em=1.0)
    kit.log(cv, {'type': 'window', 'rect': [round(x, 1), round(y + 10, 1), round(w, 1), round(h - 25, 1)],
                 'lit': True, 'kind': 'shop'})
    # decal on the glass
    if k == 0:
        cv.text('EST. 1961', 'cond', 3.2, x + w / 2, y + h * 0.4, C('#c8343a'), 'mm', em=1.0, a=0.85)


# ----------------------------------------------------------------------------- laundromat
@facade("laundromat")
def f_laundromat(R, x0, w, f):
    cv = R.cv
    rs = R.rng('laund', x0)
    top = 60
    brick_wall(cv, x0, top, w, FB - top, C('#9a5442'), seed=1201, soot=0.35)
    cornice(cv, x0, top, w, C('#c8bca8'), h=5)
    parapet(cv, x0 - 1, top - 6, w + 2, C('#6a3a34'), h=6)
    sun_rim(R, x0, top - 6, FB - 60, a=0.4)
    for fi, fy in enumerate((top + 14,)):
        for k in range(3):
            wx = x0 + 22 + k * (w - 44 - 14) / 2
            window(cv, wx, fy, 14, 22, lit=(k + fi) % 2 == 0, seed=k * 7 + fi, frame='#c8bca8')
    ac_unit(cv, x0 + w - 40, top + 40, 11, 7)
    # lightbox sign
    sy = 112
    sm = M(C('#2a5ab0'))
    cv.rect(x0 + 10, sy, w - 20, 18, sm.b, ink=sm.i, iw=MAJOR)
    kit.proud_shadow(cv, x0 + 10, sy, w - 20, 18, 4.0, a=0.3)
    cv.vgrad(x0 + 12, sy + 2, w - 24, 14, [C('#5a9aff'), C('#2a62c8'), C('#1e4aa0')], em=1.0)
    painted_text(cv, f.get('sign', 'SUDS & DUDS'), x0 + w / 2, sy + 9.5, 11, C('#f4f8ff'), shadow=True, tracking=0.6,
                 em=1.0)
    for bx in (x0 + 15, x0 + w - 15):
        cv.ellipse(bx, sy + 9, 1.6, 1.6, C('#ffe080'), em=1.0)
    R.glow(x0 + w / 2, sy + 9, w * 0.45, '#6aa8ff', 0.35, 'none')
    # storefront glass with fluorescent interior
    gy0, gy1 = sy + 24, FB - 6
    gx0, gx1 = x0 + 12, x0 + w - 12
    cv.rect(gx0 - 2, gy0 - 2, gx1 - gx0 + 4, gy1 - gy0 + 4, C('#9aa0b0'), ink=C('#2a2a38'), iw=MAJOR)
    cv.vgrad(gx0, gy0, gx1 - gx0, gy1 - gy0, [C('#f2fbff'), C('#d4ecf4'), C('#a8c8d8')], em=1.0)
    kit.log(cv, {'type': 'window', 'rect': [round(gx0 + 4, 1), round(gy0 + 4, 1), round(gx1 - gx0 - 8, 1),
                                            round(gy1 - gy0 - 8, 1)], 'lit': True, 'kind': 'shop'})
    # ceiling tube lights
    for k in range(3):
        lx = gx0 + 14 + k * (gx1 - gx0 - 28) / 2
        cv.rect(lx - 9, gy0 + 2, 18, 1.4, C('#ffffff'), em=1.0)
        cv.radial(lx, gy0 + 4, 16, 7, C('#e8ffff'), a=0.4, mode='add')
    # back wall: a row of stacked dryers and one row of front-loading washers
    ty = gy0 + 9
    nx = int((gx1 - gx0 - 10) / 25)
    for k in range(nx):
        mx = gx0 + 6 + k * 25
        machine(cv, mx, ty, 22, 19, 'dryer')
        machine(cv, mx, ty + 20, 22, 22, 'washer', spin=k % 3 == 1)
    # folding table + figure + basket
    cv.rect(gx0 + 6, gy1 - 13, 40, 2, C('#c8c0b0'), em=1.0)
    cv.rect(gx0 + 8, gy1 - 11, 1, 11, C('#6a6a78'), em=1.0)
    cv.rect(gx0 + 42, gy1 - 11, 1, 11, C('#6a6a78'), em=1.0)
    sil = C('#6a7a90')
    px = gx1 - 22
    cv.ellipse(px, gy1 - 26, 2.8, 3.2, sil, em=1.0)
    cv.fill_poly([(px - 5, gy1), (px - 4, gy1 - 22), (px + 4, gy1 - 22), (px + 5, gy1)], C('#5a6a98'), em=1.0)
    cv.rect(px + 3, gy1 - 20, 5, 6, C('#f0e8d8'), em=1.0)   # newspaper
    cv.rect(gx0 + 14, gy1 - 18, 10, 5, C('#e8a0b0'), em=1.0)
    # window lettering / decals and reflection
    cv.text('OPEN 7AM-11PM', 'cond', 3.6, gx0 + 30, gy0 + 5, C('#2a5ab0'), 'mm', em=1.0, a=0.85)
    cv.text('WASH 75¢  DRY 25¢', 'cond', 3.4, gx1 - 32, gy1 - 3.5, C('#c83a3a'), 'mm', em=1.0, a=0.9)
    cv.fill_poly([(gx0 + 20, gy0), (gx0 + 34, gy0), (gx0 + 8, gy1), (gx0 - 6, gy1)], C('#ffffff'), a=0.16,
                 mode='atop')
    for k in range(1, 3):
        mx = gx0 + (gx1 - gx0) * k / 3
        cv.rect(mx - 0.75, gy0, 1.5, gy1 - gy0, C('#9aa0b0'), ink=C('#2a2a38'), iw=DETAIL)
    cv.rect(x0 + 6, FB - 5, w - 12, 5, C('#6a6070'), ink=C('#2a2230'), iw=DETAIL)
    light_pool(R, x0 + w / 2, FB + 10, w * 0.55, 13, '#b8e8ff', a=0.18)
    R.light(x0 + w / 2, FB + 14, w * 0.55, 32, '#a8d8ff', 0.18)
    R.glow(x0 + w / 2, (gy0 + gy1) / 2, w * 0.5, '#d8f4ff', 0.3, 'fluor')


def machine(cv, x, y, w, h, kind, spin=False):
    m = M(C('#e8ecf0'))
    cv.rect(x, y, w, h, m.b, ink=C('#6a7888'), iw=DETAIL, em=1.0)
    cv.rect(x, y, w, 2.5, C('#c8d0d8'), em=1.0)
    cx, cy = x + w / 2, y + h / 2 + 1
    r = min(w, h) * 0.32
    cv.ellipse(cx, cy, r + 0.8, r + 0.8, C('#8a98a8'), em=1.0)
    glass = C('#7ab0d0') if kind == 'washer' else C('#a0b8c8')
    cv.ellipse(cx, cy, r, r, glass, em=1.0)
    if spin:
        cv.ellipse(cx, cy + r * 0.3, r * 0.8, r * 0.5, C('#e86a6a'), a=0.8, mode='atop', em=1.0)
        cv.ellipse(cx - r * 0.2, cy + r * 0.2, r * 0.5, r * 0.4, C('#f0f0f0'), a=0.8, mode='atop', em=1.0)
    cv.ellipse(cx - r * 0.35, cy - r * 0.35, r * 0.25, r * 0.2, C('#ffffff'), a=0.7, em=1.0)


# ----------------------------------------------------------------------------- alley gap
@facade("alley_gap")
def f_alley_gap(R, x0, w, f):
    """A narrow alley between two buildings: side walls recede to a lit back door; sky above the roofs."""
    cv = R.cv
    top = 52
    back_l, back_r = x0 + w * 0.34, x0 + w * 0.66
    by0, by1 = top + 30, FB - 26
    wl = M(C('#6a3a38'))
    wr = M(C('#4e3040'))
    # left wall (catches the lamp), right wall (in shadow)
    cv.fill_poly([(x0, top), (back_l, by0), (back_l, by1), (x0, FB)], wl.s)
    cv.fill_poly([(x0 + w, top - 4), (back_r, by0), (back_r, by1), (x0 + w, FB)], wr.d)
    for k in range(1, 22):
        t = k / 22
        y = top + (FB - top) * t
        yb = by0 + (by1 - by0) * t
        cv.line([(x0, y), (back_l, yb)], 0.5, wl.d, a=0.55)
        cv.line([(x0 + w, y), (back_r, yb)], 0.5, shade(wr.d, 0.6), a=0.5)
    # back wall + lit back door
    cv.rect(back_l, by0, back_r - back_l, by1 - by0, C('#3a2836'))
    dx0 = back_l + 3
    cv.rect(dx0, by1 - 15, 8, 15, C('#ffc070'), em=1.0)
    cv.rect(dx0 + 5, by1 - 15, 3, 15, C('#c87a3a'), em=1.0)
    cv.radial(dx0 + 4, by1 - 6, 14, 12, C('#ffb060'), a=0.35, mode='add')
    # alley floor with a lamp-lit puddle
    cv.fill_poly([(x0, FB), (back_l, by1), (back_r, by1), (x0 + w, FB)], C('#3a3038'))
    cv.ellipse(x0 + w * 0.45, FB - 8, 8, 2, C('#ffc890'), a=0.35)
    # wall lamp with a warm cone
    lx, ly = x0 + w * 0.22, 118
    cv.rect(lx - 1.5, ly - 5, 3, 5, C('#1e1824'))
    cv.fill_poly([(lx - 4, ly), (lx + 4, ly), (lx + 2.5, ly + 2.5), (lx - 2.5, ly + 2.5)], C('#fff0b0'), em=1.0)
    cv.fill_poly([(lx - 3, ly + 2.5), (lx + 3, ly + 2.5), (lx + 18, FB - 6), (lx - 6, FB - 6)], C('#ffc070'), a=0.10,
                 mode='add')
    cv.radial(lx, ly + 6, 14, 18, C('#ffb860'), a=0.3, mode='add')
    R.glow(lx, ly + 1, 18, '#ffc070', 0.45, 'flame')
    # dumpster + trash bags, pipes, cables, steam
    dm = M(C('#2e5a48'))
    cv.rect(back_l - 4, by1 - 8, 16, 9, dm.b, ink=dm.i, iw=DETAIL)
    cv.rect(back_l - 4, by1 - 8, 16, 1.2, dm.l)
    for k, (bx, br) in enumerate(((x0 + 10, 4.5), (x0 + 16, 3.5), (x0 + w - 12, 4))):
        cv.ellipse(bx, FB - br, br, br * 0.9, C('#2a2a34'), ink=C('#0e0a14'), iw=DETAIL)
        cv.ellipse(bx - br * 0.3, FB - br * 1.4, br * 0.4, br * 0.25, C('#6a6a7a'), a=0.6)
    drainpipe(cv, x0 + 3, top + 4, FB - 2, '#3a3440')
    for k in range(3):
        cable(cv, x0 - 4, top + 6 + k * 16, x0 + w + 4, top + 10 + k * 16, sag=6 + k * 2, w=0.5, col='#140e18')
    R.ambient.append({"type": "steam", "x": round(x0 + w * 0.55, 1), "y": round(by1 - 2, 1), "rate": 0.6})
    if f.get('sign'):
        sx = x0 + w / 2
        cv.rect(sx - 34, top + 6, 68, 14, C('#1a1020'), ink=C('#06040a'), iw=MAJOR)
        neon_text(cv, f['sign'], sx, top + 13.5, 6.5, C('#ff4ab0'), tracking=0.4, glow=0.45)
        R.glow(sx, top + 13, 44, '#ff4ab0', 0.45, 'neon')
    # cat on the dumpster lid (environmental life)
    cx, cy = back_l + 7, by1 - 9
    cv.ellipse(cx, cy - 1.6, 2.4, 1.6, C('#1a1420'))
    cv.ellipse(cx + 2.2, cy - 3.2, 1.2, 1.1, C('#1a1420'))
    cv.ellipse(cx + 2.6, cy - 3.3, 0.35, 0.3, C('#e8f060'), em=1.0)
    # shadowed mouth edges
    cv.hgrad(x0, top, 6, FB - top, [C('#0e0a14', 140), C('#0e0a14', 0)])
    cv.hgrad(x0 + w - 6, top, 6, FB - top, [C('#0e0a14', 0), C('#0e0a14', 160)])
    R.light(x0 + w / 2, FB + 6, w * 0.8, 20, '#2a1e40', -0.15)


# ----------------------------------------------------------------------------- closed record shop
@facade("closed_shop")
def f_closed_shop(R, x0, w, f):
    cv = R.cv
    rs = R.rng('closed', x0)
    top = 54
    brick_wall(cv, x0, top, w, FB - top, C('#8c4c40'), seed=1401, soot=0.45, accent=0.1)
    cornice(cv, x0, top, w, C('#b8ac98'), h=4.5)
    parapet(cv, x0 - 1, top - 5, w + 2, C('#5a3430'), h=5)
    sun_rim(R, x0, top - 5, FB - 60, a=0.4)
    # vacant upper floor: dark windows, one broken + boarded
    for k in range(4):
        wx = x0 + 18 + k * (w - 36 - 14) / 3
        window(cv, wx, top + 14, 14, 22, lit=False, seed=k + 70, frame='#b8ac98')
        if k == 2:
            cv.fill_poly([(wx + 3, top + 14), (wx + 9, top + 14), (wx + 5, top + 22)], C('#120c18'))
            cv.line([(wx + 5, top + 22), (wx + 8, top + 30)], 0.4, C('#d8d0e0'), a=0.6)
        if k == 0:
            plywood(cv, wx, top + 14, 14, 22, seed=91)
    # faded painted sign board
    sy = 104
    sb = M(C('#4a6a58'))
    cv.rect(x0 + 10, sy, w - 20, 16, sb.b, ink=sb.i, iw=MAJOR)
    kit.weather(cv, x0 + 10, sy, w - 20, 16, 1402, soot=0.2, blotch=0.25, streak=True)
    painted_text(cv, f.get('sign', "ROSIE'S RECORDS"), x0 + w / 2, sy + 8.5, 10, C('#e8d8a8'), fade=0.45, seed=4,
                 tracking=0.5)
    # a vinyl record emblem
    cv.ellipse(x0 + 20, sy + 8, 5, 5, C('#1a1420'), ink=C('#0e0a12'), iw=DETAIL)
    cv.ellipse(x0 + 20, sy + 8, 1.6, 1.6, C('#d84a4a'))
    # storefront boarded with plywood, posters, eviction notice
    gy0, gy1 = sy + 22, FB - 4
    cv.rect(x0 + 8, gy0 - 2, w - 16, gy1 - gy0 + 4, C('#3a3036'), ink=C('#1a1220'), iw=MAJOR)
    door_w = 22
    dl = x0 + w / 2 - door_w / 2
    plywood(cv, x0 + 10, gy0, dl - x0 - 14, gy1 - gy0, seed=88)
    plywood(cv, dl + door_w + 4, gy0, x0 + w - 10 - (dl + door_w + 4), gy1 - gy0, seed=89)
    # roll-down shutter over the door
    sm = M(C('#8a8a90'))
    mk = cv.rect(dl, gy0, door_w, gy1 - gy0, sm.b, ink=sm.i, iw=DETAIL)
    yy = gy0
    while yy < gy1:
        cv.rect(dl, yy, door_w, 0.6, sm.s, mode='atop')
        cv.rect(dl, yy + 0.6, door_w, 0.5, sm.l, mode='atop')
        yy += 2.2
    kit.weather(cv, dl, gy0, door_w, gy1 - gy0, 1403, soot=0.35, streak=True)
    cv.rect(dl + door_w / 2 - 2, gy1 - 4, 4, 2.5, C('#c8a040'), ink=C('#3a2a10'), iw=DETAIL)   # padlock
    tag(cv, dl + 2, gy0 + 10, 'DOGS', C('#e84a3a'), size=6, seed=12, a=0.85)
    poster(cv, x0 + 16, gy0 + 6, 16, 22, seed=901, kind='evict')
    poster(cv, x0 + 36, gy0 + 10, 14, 19, seed=902, kind='gig')
    poster(cv, dl + door_w + 10, gy0 + 4, 14, 19, seed=903, kind='missing')
    poster(cv, dl + door_w + 28, gy0 + 9, 15, 20, seed=904, kind='boxing')
    poster(cv, x0 + w - 30, gy0 + 6, 13, 18, seed=905, kind='gig', tilt=1.5)
    cv.text('CLOSED', 'cond', 5, x0 + 25, gy1 - 10, C('#e8e0d0'), 'mm', ink=C('#6a1a1a'), iw=0.5)
    tag(cv, x0 + w - 44, gy1 - 12, 'CHAIN DOGS', C('#f0c040'), size=5, seed=13, a=0.8)
    R.light(x0 + w / 2, FB + 10, w * 0.6, 26, '#2a2040', -0.10)


# ----------------------------------------------------------------------------- brick apartment
@facade("brick_apartment")
def f_brick_apartment(R, x0, w, f):
    cv = R.cv
    rs = R.rng('apt', x0)
    top = 10
    brick_wall(cv, x0, top, w, FB - top, C('#8e4638'), seed=1501, soot=0.3)
    cornice(cv, x0, top + 2, w, C('#d0c4ac'), h=6)
    sun_rim(R, x0, top, FB - 70, a=0.5)
    # three upper floors + a tall ground floor
    floors = [top + 20, top + 60, top + 100]
    for fy in floors[1:] + [top + 138]:
        cv.rect(x0, fy - 8, w, 2.5, C('#c8bca4'), ink=C('#5a4a40'), iw=DETAIL)
    ncol = int((w - 30) / 30)
    esc_cols = {1, ncol - 2}
    for fi, fy in enumerate(floors):
        for k in range(ncol):
            wx = x0 + 18 + k * (w - 36 - 15) / max(1, ncol - 1)
            lit = rs.random() < 0.5
            window(cv, wx, fy, 15, 28, lit=lit, seed=hash((fi, k)) % 9999, frame='#d0c4ac')
            if not lit and rs.random() < 0.15:
                ac_unit(cv, wx + 2, fy + 21, 11, 7)
            if lit and rs.random() < 0.15:
                flower_box(R, wx - 2, fy + 30, 19, rs)
    for k in esc_cols:
        wx = x0 + 18 + k * (w - 36 - 15) / max(1, ncol - 1)
        fire_escape(cv, wx - 8, 31, [fy + 34 for fy in floors], ladder=True, bottom=FB - 34)
    # entrance: stone surround, double door (48 u), canopy, stoop
    ex = x0 + w / 2
    cv.rect(ex - 20, FB - 66, 40, 66, C('#cbbfa6'), ink=C('#4a3a34'), iw=MAJOR)
    cv.rect(ex - 20, FB - 66, 40, 1.2, C('#efe4cc'), mode='atop')
    door(cv, ex - 10, FB - 6, 20, 48, C('#3a2a24'), lit=True, seed=15, frame='#5a4a40', transom=True)
    cv.rect(ex - 0.4, FB - 54, 0.8, 48, C('#1e1416'))
    stoop(cv, ex - 16, 32, FB, steps=2)
    awning(cv, ex - 22, FB - 72, 44, 6, C('#2a4a3a'), None, valance=2.5, scallop=False)
    painted_text(cv, '1418', ex, FB - 68.5, 4, C('#f0e0b0'), kind='cond', shadow=False)
    cv.rect(ex + 13, FB - 40, 5, 8, C('#c8a860'), ink=C('#3a2a10'), iw=DETAIL)
    # ground-floor windows with security bars
    for k, wx in enumerate((x0 + 22, x0 + 62, x0 + w - 80, x0 + w - 40)):
        window(cv, wx, FB - 56, 18, 34, lit=k % 2 == 1, seed=200 + k, frame='#d0c4ac')
        for bb in range(5):
            cv.rect(wx + 1.5 + bb * 3.8, FB - 56, 0.8, 34, C('#1e1a24'))
    poster(cv, x0 + 102, FB - 40, 12, 16, seed=1505, kind='missing')
    poster(cv, ex + 26, FB - 44, 13, 17, seed=1506, kind='evict')
    tag(cv, x0 + w - 116, FB - 14, 'CD', C('#4a8ad8'), size=6, seed=31)
    for ax in (x0 + 60, x0 + w - 90):
        cv.line([(ax, top), (ax, top - 18)], 0.6, C('#2a2430'))
        for k in range(3):
            cv.line([(ax - 6 + k, top - 14 + k * 4), (ax + 6 - k, top - 14 + k * 4)], 0.5, C('#2a2430'))
    R.ambient.append({"type": "pigeons", "x": round(x0 + w * 0.35, 1), "y": float(top - 1), "w": 60})


# ----------------------------------------------------------------------------- Chain Lot pieces
@facade("graffiti_wall")
def f_graffiti_wall(R, x0, w, f):
    cv = R.cv
    top = 116
    concrete_panel(cv, x0, top, w, FB - top, C('#8a8478'), seed=2001, panel=40, soot=0.4)
    cv.rect(x0, top - 4, w, 5, C('#a09a8c'), ink=C('#2a2430'), iw=MAJOR)
    cv.rect(x0, top - 4, w, 1, C('#d8d0c0'), mode='atop')
    sun_rim(R, x0, top - 4, FB - 30, a=0.4)
    graffiti_piece(cv, x0 + 16, top + 22, 110, 44, 'DOGS', '#ff7a3a', '#c83a6a', seed=1)
    graffiti_piece(cv, x0 + 150, top + 14, 96, 34, 'RULE', '#5ad8a8', '#3a6ad8', seed=2)
    graffiti_piece(cv, x0 + 262, top + 40, 98, 38, 'K-ST', '#f0d040', '#e86a3a', seed=3)
    # chain emblem (spiked collar)
    cx, cy = x0 + 140, top + 72
    cv.ellipse(cx, cy, 10, 10, None, ink=C('#d8d0c8'), iw=1.8)
    for k in range(10):
        a = k * math.pi / 5
        cv.fill_poly([(cx + math.cos(a) * 9, cy + math.sin(a) * 9), (cx + math.cos(a + 0.15) * 13, cy + math.sin(a + 0.15) * 13),
                      (cx + math.cos(a + 0.3) * 9, cy + math.sin(a + 0.3) * 9)], C('#d8d0c8'))
    for k in range(4):
        tag(cv, x0 + 30 + k * 90, FB - 16 - (k % 2) * 8, ['CD', 'RAT', 'XO', 'DUKE'][k],
            [C('#f4f0e8'), C('#e84a3a'), C('#4a8ad8'), C('#f0c040')][k], size=6, seed=20 + k)
    # NO TRESPASSING sign
    sx, sy = x0 + w - 70, top + 12
    cv.rect(sx, sy, 26, 12, C('#f0ece0'), ink=C('#2a2430'), iw=DETAIL)
    cv.text('NO', 'cond', 4, sx + 13, sy + 3.6, C('#c83a3a'), 'mm')
    cv.text('TRESPASSING', 'cond', 3.2, sx + 13, sy + 8.4, C('#2a2230'), 'mm')
    # burn barrel against the wall (scenery) with fire
    bx, byb = x0 + 52, FB + 2
    burn_barrel(R, bx, byb)
    for k in range(int(w / 12)):
        weeds(R, x0 + 4 + k * 12 + (k % 3) * 2, FB + 0.5, 3, seed=2000 + k)


def burn_barrel(R, x, yb):
    cv = R.cv
    m = M(C('#6a4a3a'))
    lay = cv.layer(x - 10, yb - 32, 20, 34)
    lay.rect(x - 7, yb - 20, 14, 20, m.b)
    lay.hgrad(x - 7, yb - 20, 14, 20, [m.l, m.b, m.s, m.d], mode='atop')
    for yy in (yb - 16, yb - 6):
        lay.rect(x - 7, yy, 14, 1.2, m.s, mode='atop')
    cv.merge(lay, ink=m.i, iw=MAJOR)
    kit.weather(cv, x - 7, yb - 20, 14, 20, 77, soot=0.6, streak=False)
    cv.vgrad(x - 7, yb - 20, 14, 8, [C('#ff9a40', 180), C('#ff9a40', 0)], mode='atop', em=0.6)
    # flames
    rs = rng_of('flame', x)
    for k in range(5):
        fx = x - 5 + k * 2.5
        hgt = rs.uniform(5, 10)
        cv.fill_poly([(fx - 2, yb - 20), (fx + rs.uniform(-1, 1), yb - 20 - hgt), (fx + 2, yb - 20)], C('#ff8a2a'),
                     em=1.0)
        cv.fill_poly([(fx - 1, yb - 20), (fx, yb - 20 - hgt * 0.55), (fx + 1, yb - 20)], C('#ffe07a'), em=1.0)
    cv.radial(x, yb - 22, 22, 18, C('#ff9a40'), a=0.35, mode='add')
    R.glow(x, yb - 24, 34, '#ff9040', 0.6, 'flame')
    R.glow(x, yb - 20, 60, '#ff7a30', 0.15, 'flame', front=True)
    R.ambient.append({"type": "embers", "x": float(x), "y": float(yb - 24)})
    R.ambient.append({"type": "smoke", "x": float(x), "y": float(yb - 30), "rate": 0.5})
    R.light(x, yb + 8, 60, 34, '#ff9040', 0.26)


@facade("fence_lot")
def f_fence_lot(R, x0, w, f):
    """Chain-link fence (see-through to the room mid layer), barbed wire, weeds, a gate."""
    cv = R.cv
    top = 126
    post = M(C('#6a6a72'))
    wire = C('#a8a8b4')
    lay = cv.layer(x0 - 2, top - 14, w + 4, FB - top + 16)
    # mesh: diamond pattern via two families of diagonal lines
    mk = lay.rect_mask(x0, top, w, FB - top)
    x_0, y_0, mm = mk
    hh, ww = mm.shape
    X = (np.arange(ww, dtype=np.float32) + x_0 + lay.ox + 0.5) / lay.D
    Y = (np.arange(hh, dtype=np.float32) + y_0 + lay.oy + 0.5) / lay.D
    XX, YY = np.meshgrid(X, Y)
    p = 4.0
    d1 = np.abs(((XX + YY) % p) - p / 2)
    d2 = np.abs(((XX - YY) % p) - p / 2)
    lw = 0.32
    a1 = np.clip((p / 2 - d1 - (p / 2 - lw)) / lw + 0.5, 0, 1)
    a2 = np.clip((p / 2 - d2 - (p / 2 - lw)) / lw + 0.5, 0, 1)
    meshm = np.maximum(a1, a2) * mm
    lay.paint((x_0, y_0, meshm), wire, a=0.75)
    # rails
    lay.rect(x0, top, w, 1.2, post.b)
    lay.rect(x0, FB - 4, w, 1.0, post.b)
    xx = x0 + 6
    while xx < x0 + w:
        lay.rect(xx - 1, top - 2, 2, FB - top + 2, post.b)
        lay.rect(xx - 1, top - 2, 0.6, FB - top + 2, post.l, mode='atop')
        # barbed wire arm
        lay.line([(xx, top - 2), (xx + 4, top - 10)], 0.7, post.b)
        xx += 52
    for k in range(3):
        pts = []
        for j in range(int(w / 2) + 1):
            px = x0 + j * 2
            pts.append((px, top - 3.5 - k * 2.4 + math.sin(j * 1.3 + k) * 0.6))
        lay.line(pts, 0.4, C('#8a8a96'))
        for j in range(0, int(w), 5):
            bx = x0 + j + k
            by = top - 3.5 - k * 2.4
            lay.line([(bx - 0.8, by - 0.8), (bx + 0.8, by + 0.8)], 0.35, C('#8a8a96'))
    cv.merge(lay, ink=C('#1a1220', 200), iw=0.5)
    # sun glints on the mesh (warm, upper part)
    cv.vgrad(x0, top, w, 40, [C('#ffc890', 120), C('#ffc890', 0)], mode='atop', a=0.5)
    # weeds + litter along the base, a torn tarp hanging on the fence
    rs = R.rng('fence')
    for k in range(int(w / 9)):
        weeds(R, x0 + 3 + k * 9 + rs.uniform(-2, 2), FB + 0.5, rs.randint(2, 6), seed=3000 + k)
    tx = x0 + w * 0.62
    cv.fill_poly([(tx, top + 2), (tx + 34, top + 2), (tx + 30, top + 30), (tx + 20, top + 24), (tx + 8, top + 34),
                  (tx + 2, top + 20)], C('#3a6a8a'), ink=C('#142030'), iw=DETAIL, a=0.92)
    cv.vgrad(tx, top + 2, 34, 32, [C('#7ab0d0', 120), C('#3a6a8a', 0)], mode='atop')
    poster(cv, x0 + 120, top + 26, 18, 13, seed=3101, kind='plain')
    cv.text('KEEP OUT', 'cond', 3.6, x0 + 129, top + 32.5, C('#c83a3a'), 'mm')
    R.notes.append('fence_lot: base transparent above the ground between fence posts; mid layer shows through')


@facade("clubhouse_shed")
def f_clubhouse(R, x0, w, f):
    cv = R.cv
    top = 122
    roof_y = top - 10
    m = M(C('#a8402e'))
    corrugated(cv, x0 + 6, top, w - 12, FB - top, C('#a8402e'), seed=2201, pitch=4, rust=0.5)
    # sloped roof edge
    cv.fill_poly([(x0, top + 2), (x0 + w, top + 2), (x0 + w - 6, roof_y), (x0 + 6, roof_y)], C('#5a5058'),
                 ink=C('#1a1220'), iw=MAJOR)
    cv.rect(x0, top, w, 2, C('#8a8088'), mode='atop')
    sun_rim(R, x0 + 6, top, FB - 20, a=0.45)
    # sign board on the roof
    sb = M(C('#3a2a24'))
    sx, sw = x0 + w / 2 - 50, 100
    cv.rect(sx + 12, roof_y - 6, 2, 8, C('#2a2026'))
    cv.rect(sx + sw - 14, roof_y - 6, 2, 8, C('#2a2026'))
    cv.rect(sx, roof_y - 26, sw, 20, sb.b, ink=sb.i, iw=MAJOR)
    planks = cv.rect_mask(sx, roof_y - 26, sw, 20)
    for k in range(4):
        cv.rect(sx, roof_y - 26 + k * 5, sw, 0.5, sb.d, mode='atop')
    painted_text(cv, f.get('sign', 'DOG HOUSE'), sx + sw / 2, roof_y - 15.5, 11, C('#f0d8a0'), tracking=0.5)
    # string lights along the roof edge
    bulbs = string_lights(cv, x0 + 8, top + 3, x0 + w - 8, top + 3, sag=6, step=7, seed=4)
    for bx, by, c, on in bulbs[::4]:
        if on:
            R.glow(bx, by, 10, '#%02x%02x%02x' % c[:3], 0.25, 'neon')
    # door + glowing window
    dx = x0 + 40
    door(cv, dx, FB, 18, 34, C('#5a4030'), glass=False, seed=22, frame='#2a2026', step=False, transom=False)
    window(cv, x0 + 92, top + 30, 26, 18, lit=True, seed=223, frame='#2a2026', interior='person', curtains=False,
           sill=True, lintel=False, kind='grid')
    R.glow(x0 + 105, top + 39, 30, '#ffc070', 0.35, 'none')
    # chain-dog emblem: collar with spikes
    cx, cy = x0 + w - 60, top + 40
    cv.ellipse(cx, cy, 12, 12, C('#1a1420'), ink=C('#0e0a12'), iw=MAJOR)
    cv.ellipse(cx, cy, 9, 9, None, ink=C('#d8d0c8'), iw=1.6)
    for k in range(8):
        a = k * math.pi / 4
        cv.fill_poly([(cx + math.cos(a - 0.2) * 9.5, cy + math.sin(a - 0.2) * 9.5),
                      (cx + math.cos(a) * 13, cy + math.sin(a) * 13),
                      (cx + math.cos(a + 0.2) * 9.5, cy + math.sin(a + 0.2) * 9.5)], C('#d8d0c8'))
    cv.text('CD', 'sign', 6, cx, cy, C('#e84a3a'), 'mm')
    # beware sign, old couch silhouette by the wall, tyre
    cv.rect(dx + 24, top + 54, 20, 10, C('#f0d040'), ink=C('#2a2010'), iw=DETAIL)
    cv.text('BEWARE', 'cond', 3.4, dx + 34, top + 59, C('#2a2010'), 'mm')
    couch(R, x0 + 150, FB + 1)
    tag(cv, x0 + 12, FB - 30, 'DUKE', C('#f4f0e8'), size=7, seed=40)
    R.light(x0 + w / 2, FB + 12, w * 0.5, 28, '#ffb060', 0.14)


def couch(R, x, yb):
    cv = R.cv
    m = M(C('#6a4a7a'))
    lay = cv.layer(x - 4, yb - 20, 50, 22)
    lay.rect(x, yb - 16, 44, 9, m.b)
    lay.rect(x - 2, yb - 12, 6, 12, m.s)
    lay.rect(x + 40, yb - 12, 6, 12, m.s)
    lay.rect(x + 2, yb - 8, 40, 6, m.l)
    lay.rect(x + 22, yb - 8, 0.6, 6, m.d)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.rect(x + 8, yb - 14, 6, 3, C('#e8c860'), a=0.9)
    cv.vgrad(x - 4, yb - 1, 54, 4, [C('#140c18', 140), C('#140c18', 0)])


@facade("underpass")
def f_underpass(R, x0, w, f):
    cv = R.cv
    deck_y0, deck_y1 = 56, 110
    # bridge deck spanning, concrete with a steel girder face
    concrete_panel(cv, x0 - 10, deck_y0, w + 20, deck_y1 - deck_y0, C('#8a8478'), seed=2301, panel=30, ties=False)
    gm = M(C('#4a5462'))
    cv.rect(x0 - 10, deck_y1 - 16, w + 20, 16, gm.b, ink=gm.i, iw=MAJOR)
    xx = x0 - 6
    while xx < x0 + w + 10:
        cv.rect(xx, deck_y1 - 16, 1.5, 16, gm.l)
        for yy in (deck_y1 - 13, deck_y1 - 4):
            cv.ellipse(xx + 4, yy, 0.6, 0.6, gm.h)
        xx += 12
    kit.weather(cv, x0 - 10, deck_y1 - 16, w + 20, 16, 2302, soot=0.2, blotch=0.2)
    cv.text('RIVER LINE', 'cond', 5, x0 + w / 2, deck_y1 - 8, C('#d8d0c0'), 'mm', a=0.7)
    # tunnel mouth (dark)
    tx0, tx1 = x0 + 16, x0 + w
    cv.vgrad(tx0, deck_y1, tx1 - tx0, FB - deck_y1, [C('#0e0a16'), C('#1a1424'), C('#241c2c')])
    # pier on the left
    concrete_panel(cv, x0, deck_y1, 16, FB - deck_y1, C('#7a7468'), seed=2303, panel=16, ties=False)
    sun_rim(R, x0, deck_y0, FB - 20, a=0.35)
    # far end of the tunnel: faint cool light
    cv.radial(x0 + w * 0.75, FB - 20, 26, 36, C('#6a7aa8'), a=0.35, mode='add')
    # chain-link gate with padlocked chain
    gx0, gx1 = x0 + 24, x0 + w - 6
    lay = cv.layer(gx0 - 2, deck_y1 + 6, gx1 - gx0 + 4, FB - deck_y1)
    mk = lay.rect_mask(gx0, deck_y1 + 18, gx1 - gx0, FB - deck_y1 - 20)
    x_0, y_0, mm = mk
    hh, ww = mm.shape
    X = (np.arange(ww, dtype=np.float32) + x_0 + lay.ox + 0.5) / lay.D
    Y = (np.arange(hh, dtype=np.float32) + y_0 + lay.oy + 0.5) / lay.D
    XX, YY = np.meshgrid(X, Y)
    p = 4.0
    d1 = np.abs(((XX + YY) % p) - p / 2)
    d2 = np.abs(((XX - YY) % p) - p / 2)
    a1 = np.clip((d1 - (p / 2 - 0.35)) / 0.35, 0, 1)
    a2 = np.clip((d2 - (p / 2 - 0.35)) / 0.35, 0, 1)
    lay.paint((x_0, y_0, np.maximum(a1, a2) * mm), C('#9898a8'), a=0.8)
    pm = M(C('#6a6a74'))
    for px in (gx0, (gx0 + gx1) / 2, gx1):
        lay.rect(px - 1, deck_y1 + 16, 2, FB - deck_y1 - 16, pm.b)
    lay.rect(gx0, deck_y1 + 16, gx1 - gx0, 1.5, pm.b)
    lay.rect(gx0, FB - 4, gx1 - gx0, 1.5, pm.b)
    cv.merge(lay, ink=C('#0e0a14', 200), iw=0.5)
    mx = (gx0 + gx1) / 2
    for k in range(6):
        cv.ellipse(mx - 3 + k * 1.2, FB - 30 + abs(k - 2.5) * 1.5, 0.9, 0.6, None, ink=C('#c8c8d0'), iw=0.45)
    cv.rect(mx - 1.6, FB - 25, 3.2, 3.5, C('#d8b040'), ink=C('#3a2a10'), iw=DETAIL)
    # caged work lamp
    lx, ly = x0 + 20, deck_y1 + 4
    cv.rect(lx - 3, ly, 6, 4, C('#2a2a34'), ink=C('#0e0a14'), iw=DETAIL)
    cv.rect(lx - 2, ly + 1, 4, 2.5, C('#e8f4ff'), em=1.0)
    cv.radial(lx, ly + 18, 24, 34, C('#a8c8ff'), a=0.18, mode='add')
    R.glow(lx, ly + 2, 22, '#c8e0ff', 0.5, 'fluor')
    R.light(lx + 10, FB + 20, 70, 40, '#a8c0ff', 0.12)
    R.light(x0 + w * 0.6, FB + 10, w * 0.6, 30, '#1a1430', -0.10)
    R.ambient.append({"type": "drip", "x": float(x0 + w * 0.5), "y": float(deck_y1), "rate": 0.4})
    R.ambient.append({"type": "pigeons", "x": float(x0 + 10), "y": float(deck_y0 - 1), "w": 40})


# ----------------------------------------------------------------------------- Lucky Spoon interior
@facade("diner_interior")
def f_diner_interior(R, x0, w, f):
    cv = R.cv
    rs = R.rng('dint')
    WB = INT_WALL_BOTTOM
    # upper wall: mint, darker toward the ceiling
    cv.vgrad(x0, 0, w, 140, [C('#4e7a72'), C('#8cc4b0'), C('#a8d8c4')])
    mk = cv.rect_mask(x0, 0, w, 140)
    x_0, y_0, mm = mk
    n = value_noise(mm.shape[1], mm.shape[0], 20 * cv.D, 501, 2)
    cv.paint((x_0, y_0, (0.5 - n).clip(0, 1) * 0.12 * mm), C('#2a4a44'), mode='atop')
    # ceiling soffit with recessed strip
    cv.rect(x0, 0, w, 10, C('#3a5a54'))
    cv.rect(x0, 9, w, 1, C('#c8e8dc'), a=0.6)
    # chrome rail + red tufted wainscot + checker trim
    cv.rect(x0, 138, w, 3, C('#c8ccd8'), ink=C('#3a3a48'), iw=DETAIL)
    cv.rect(x0, 138, w, 1, C('#ffffff'), mode='atop')
    cv.rect(x0, 141, w, 4, C('#2a2430'))
    xx = x0
    k = 0
    while xx < x0 + w:
        cv.rect(xx, 141, 2, 2, C('#f4f0e8') if k % 2 == 0 else C('#1e1a24'))
        cv.rect(xx, 143, 2, 2, C('#1e1a24') if k % 2 == 0 else C('#f4f0e8'))
        xx += 2
        k += 1
    red = M(C('#b8303a'))
    cv.rect(x0, 145, w, WB - 145, red.b)
    cv.vgrad(x0, 145, w, WB - 145, [red.l, red.b, red.s], a=0.6, mode='atop')
    # tufting: diamond buttons
    yy = 151
    row = 0
    while yy < WB - 4:
        xx = x0 + (6 if row % 2 else 0)
        while xx < x0 + w:
            cv.ellipse(xx, yy, 0.7, 0.7, red.d)
            cv.line([(xx - 6, yy - 6), (xx, yy), (xx + 6, yy - 6)], 0.4, red.s, a=0.7)
            xx += 12
        yy += 12
        row += 1
    cv.rect(x0, WB - 3, w, 3, C('#c8ccd8'), ink=C('#3a3a48'), iw=DETAIL)
    # big street window (left): dusk street seen outside, reversed decal
    wx, wy, ww_, wh = x0 + 20, 34, 128, 88
    cv.rect(wx - 3, wy - 3, ww_ + 6, wh + 6, C('#c8ccd8'), ink=C('#3a3a48'), iw=MAJOR)
    cv.vgrad(wx, wy, ww_, wh, [C('#6a5a8a'), C('#e8907a'), C('#ffc890')], em=1.0)
    # buildings across the street
    bxs = [(wx, 30, 46), (wx + 30, 40, 30), (wx + 70, 34, 40), (wx + 104, 24, 50)]
    for bx, bw, bt in bxs:
        cv.rect(bx, wy + bt, bw, wh - bt, C('#6a3a48'), em=1.0)
        for r in range(3):
            for c in range(int(bw / 9)):
                if (r + c + bx) % 3:
                    cv.rect(bx + 3 + c * 9, wy + bt + 6 + r * 12, 4, 6, C('#ffd88a'), em=1.0)
    cv.rect(wx, wy + wh - 14, ww_, 14, C('#4a3a50'), em=1.0)
    cv.rect(wx, wy + wh - 14, ww_, 1, C('#a07a8a'), em=1.0)
    # mullion + glass reflection + reversed lettering
    cv.rect(wx + ww_ / 2 - 1, wy, 2, wh, C('#c8ccd8'), ink=C('#3a3a48'), iw=DETAIL)
    cv.fill_poly([(wx + 10, wy), (wx + 30, wy), (wx, wy + 40), (wx - 6, wy + 40)], C('#ffffff'), a=0.15, mode='atop')
    lay = cv.layer(wx, wy, ww_, wh)
    lay.text('LUCKY SPOON', 'sign', 7, wx + ww_ * 0.72, wy + 56, C('#e84a5a'), 'mm', tracking=0.5)
    lay.px[...] = lay.px[:, ::-1]
    cv.merge(lay, a=0.75)
    # venetian blind half drawn on the left pane
    yy = wy
    while yy < wy + 26:
        cv.rect(wx, yy, ww_ / 2 - 1, 1.2, C('#e8e0c8'), em=1.0)
        cv.rect(wx, yy + 1.2, ww_ / 2 - 1, 0.5, C('#9a8a70'), em=1.0)
        yy += 2.2
    R.glow(wx + ww_ / 2, wy + wh / 2, 80, '#ffb080', 0.25, 'none')
    R.light(wx + ww_ / 2, 250, 120, 60, '#ffb090', 0.12)
    kit.log(cv, {'type': 'window', 'rect': [wx + ww_ / 2 + 1, wy + 2, ww_ / 2 - 3, wh - 16], 'lit': True,
                 'kind': 'shop', 'interior_window': True})
    # neon sign on the wall
    neon_text(cv, 'LUCKY SPOON', x0 + 262, 36, 13, C('#ff5a9a'), tracking=0.8, glow=0.5)
    R.glow(x0 + 262, 36, 70, '#ff5a9a', 0.4, 'neon')
    # clock
    cx, cy = x0 + 186, 30
    cv.ellipse(cx, cy, 9, 9, C('#f4f0e8'), ink=C('#2a2430'), iw=MAJOR)
    cv.ellipse(cx, cy, 9, 9, None, ink=C('#c83a3a'), iw=0.8)
    for k in range(12):
        a = k * math.pi / 6
        cv.rect(cx + math.cos(a) * 7 - 0.3, cy + math.sin(a) * 7 - 0.3, 0.6, 0.6, C('#2a2430'))
    cv.line([(cx, cy), (cx + math.cos(math.radians(-60)) * 4.5, cy + math.sin(math.radians(-60)) * 4.5)], 0.8,
            C('#2a2430'))
    cv.line([(cx, cy), (cx + math.cos(math.radians(150)) * 6.5, cy + math.sin(math.radians(150)) * 6.5)], 0.5,
            C('#2a2430'))
    # menu boards
    for i, (mx, items) in enumerate(((x0 + 222, [('BURGER', '3.50'), ('FRIES', '3.00'), ('MALT', '3.50'), ('HASH', '2.25')]),
                                     (x0 + 306, [('PIE', '3.20'), ('COFFEE', '3.00'), ('EGGS', '2.50'), ('TOAST', '1.25')]))):
        my = 56
        cv.rect(mx, my, 76, 42, C('#1e1a22'), ink=C('#c8ccd8'), iw=1.0)
        cv.rect(mx + 2, my + 2, 72, 1, C('#3a3440'))
        for j, (nm, pr) in enumerate(items):
            cv.text(nm, 'cond', 4.2, mx + 5, my + 9 + j * 8.4, C('#f4f0e8'), 'lm', em=1.0, a=0.95)
            cv.text(pr, 'cond', 4.2, mx + 71, my + 9 + j * 8.4, C('#ffd060'), 'rm', em=1.0, a=0.95)
    # framed photos
    for i, px in enumerate((x0 + 160, x0 + 178)):
        cv.rect(px - 7, 64 + i * 22, 14, 16, C('#5a3a28'), ink=C('#1a1220'), iw=DETAIL)
        cv.vgrad(px - 5.5, 65.5 + i * 22, 11, 13, [C('#d8c8a0'), C('#a89070')])
        for k in range(3 if i == 0 else 2):
            hx = px - 3.5 + k * 3.5 if i == 0 else px - 2 + k * 4
            cv.ellipse(hx, 70 + i * 22, 1.1, 1.3, C('#6a4a38'))
            cv.rect(hx - 1.4, 71.5 + i * 22, 2.8, 4.5, C('#7a5a48'))
    # kitchen pass-through (right)
    kx, ky, kw, kh = x0 + 410, 52, 190, 62
    cv.rect(kx - 3, ky - 3, kw + 6, kh + 6, C('#c8ccd8'), ink=C('#3a3a48'), iw=MAJOR)
    cv.vgrad(kx, ky, kw, kh, [C('#f4e8c8'), C('#e8c890'), C('#c89a68')], em=1.0)
    # hood, pans, cook
    cv.rect(kx + 20, ky, 70, 12, C('#9aa0a8'), ink=C('#4a4a58'), iw=DETAIL, em=0.6)
    for k in range(4):
        cv.rect(kx + 100 + k * 14, ky + 8, 1, 6, C('#5a4a40'), em=1.0)
        cv.ellipse(kx + 100 + k * 14, ky + 17, 4.5, 3.2, C('#5a5a64'), em=1.0)
    px = kx + 54
    cv.ellipse(px, ky + 28, 4.2, 4.6, C('#8a6450'), em=1.0)
    cv.fill_poly([(px - 5, ky + 23), (px + 5, ky + 23), (px + 4, ky + 20), (px - 4, ky + 20)], C('#f4f4f0'), em=1.0)
    cv.ellipse(px, ky + 19, 4.5, 3, C('#f4f4f0'), em=1.0)
    cv.fill_poly([(px - 9, kh + ky), (px - 7, ky + 34), (px + 7, ky + 34), (px + 9, kh + ky)], C('#f0ece4'), em=1.0)
    cv.radial(kx + kw / 2, ky + 20, kw * 0.5, 30, C('#ffe0a0'), a=0.2, mode='add')
    # pass shelf with plates + ticket rail
    cv.rect(kx - 5, ky + kh - 2, kw + 10, 4, C('#c8ccd8'), ink=C('#3a3a48'), iw=DETAIL)
    for k in range(3):
        cv.ellipse(kx + 30 + k * 40, ky + kh - 3, 6, 1.6, C('#f4f0e8'), ink=C('#6a6070'), iw=0.4)
        cv.ellipse(kx + 30 + k * 40, ky + kh - 4, 3.5, 1.2, C('#c87a3a'))
    cv.rect(kx, ky + 2, kw, 1, C('#8a8a96'), em=0.5)
    for k in range(6):
        tx = kx + 12 + k * 28 + rs.uniform(-3, 3)
        cv.fill_poly([(tx, ky + 2.5), (tx + 6, ky + 2.5), (tx + 6, ky + 11), (tx, ky + 10)], C('#fffbe8'),
                     ink=C('#8a8070'), iw=0.4, em=0.6)
        for j in range(3):
            cv.rect(tx + 1, ky + 4.5 + j * 2, 4, 0.5, C('#8a8070'))
    cv.ellipse(kx + kw - 14, ky + kh - 6, 3, 2, C('#e0c060'), ink=C('#5a4010'), iw=0.4)   # order bell
    R.glow(kx + kw / 2, ky + kh / 2, 110, '#ffd090', 0.25, 'none')
    R.ambient.append({"type": "steam", "x": float(kx + 104), "y": float(ky + 16), "rate": 0.5})
    # back counter: stainless cabinets with the coffee station, cake dome, pie case, register, mixer
    by = 172
    bc = M(C('#c4c8d2'))
    cv.rect(x0 + 160, by, 400, WB - by, bc.b, ink=bc.i, iw=MAJOR)
    cv.rect(x0 + 160, by, 400, 2.2, C('#f4f6fa'), ink=bc.i, iw=DETAIL)
    xx = x0 + 160
    k = 0
    while xx < x0 + 556:
        pw = 25
        cv.rect(xx + 2, by + 4, pw - 4, WB - by - 7, bc.s if k % 2 else bc.b, ink=bc.d, iw=DETAIL)
        cv.hgrad(xx + 2, by + 4, pw - 4, WB - by - 7, [C('#ffffff', 90), C('#ffffff', 0), C('#000000', 0),
                                                         C('#1a1220', 40)], mode='atop')
        cv.rect(xx + pw / 2 - 3, by + 7, 6, 1.2, C('#eef0f6'), ink=bc.d, iw=0.3)
        xx += pw
        k += 1
    cv.rect(x0 + 160, WB - 3, 400, 3, C('#2a2430'))
    # shelf above with cups
    cv.rect(x0 + 170, 120, 140, 2.5, C('#c8ccd8'), ink=C('#3a3a48'), iw=DETAIL)
    for k in range(14):
        cx_ = x0 + 176 + k * 9.5
        cv.fill_poly([(cx_ - 2.5, 113), (cx_ + 2.5, 113), (cx_ + 2, 120), (cx_ - 2, 120)],
                     C('#f4f0e8') if k % 3 else C('#e8c8a0'), ink=C('#6a6070'), iw=0.4)
    for k, ux in enumerate((x0 + 196, x0 + 224)):
        cv.rect(ux - 7, by - 24, 14, 24, C('#c8ccd8'), ink=C('#3a3a48'), iw=DETAIL)
        cv.hgrad(ux - 7, by - 24, 14, 24, [C('#ffffff'), C('#c8ccd8'), C('#7a7e8a')], mode='atop', a=0.8)
        cv.ellipse(ux, by - 25, 7, 2, C('#e0e4ec'), ink=C('#3a3a48'), iw=0.4)
        cv.rect(ux - 1, by - 8, 2, 3, C('#2a2430'))
    cv.ellipse(x0 + 268, by - 9, 13, 10, C('#e8f4ff'), ink=C('#6a7888'), iw=0.5, a=0.7)
    cv.ellipse(x0 + 268, by - 3, 9, 4, C('#e8a060'))
    cv.ellipse(x0 + 268, by - 6, 8, 3, C('#f4e8d0'))
    cv.rect(x0 + 268 - 14, by - 1, 28, 1.5, C('#c8ccd8'))
    mx = x0 + 520
    cv.rect(mx - 6, by - 26, 12, 26, C('#5ad0c8'), ink=C('#1a3a3a'), iw=DETAIL)
    cv.rect(mx - 6, by - 26, 12, 3, C('#a8f0e8'), mode='atop')
    cv.rect(mx - 3, by - 14, 6, 10, C('#d8dce4'), ink=C('#3a3a48'), iw=0.4)
    cv.rect(x0 + 330, by - 22, 46, 22, C('#e8f4ff'), ink=C('#6a7888'), iw=0.6, a=0.55)
    for k in range(3):
        cv.ellipse(x0 + 340 + k * 13, by - 6, 5, 2, C('#e8a04a'), ink=C('#6a3a10'), iw=0.4)
        cv.ellipse(x0 + 340 + k * 13, by - 15, 5, 2, C('#c83a4a') if k == 1 else C('#e8c86a'), ink=C('#6a3a10'),
                   iw=0.4)
    cv.rect(x0 + 330, by - 11, 46, 0.8, C('#c8ccd8'))
    cv.rect(x0 + 410, by - 14, 18, 14, C('#5a5a64'), ink=C('#1a1220'), iw=DETAIL)
    cv.rect(x0 + 412, by - 18, 14, 5, C('#2a2a34'), ink=C('#1a1220'), iw=DETAIL)
    cv.rect(x0 + 414, by - 17, 10, 3, C('#7aff9a'), em=1.0, a=0.8)
    # toaster + napkin stack + menu stand to break the run
    cv.rect(x0 + 458, by - 9, 14, 9, C('#d8dce4'), ink=C('#3a3a48'), iw=DETAIL)
    cv.rect(x0 + 460, by - 10, 4, 1.4, C('#2a2430'))
    cv.rect(x0 + 466, by - 10, 4, 1.4, C('#2a2430'))
    cv.rect(x0 + 484, by - 6, 10, 6, C('#f4f0e8'), ink=C('#8a8070'), iw=0.4)
    # pendant lamps (in the base; foreground copies are separate fg sprites)
    for lx in (x0 + 300, x0 + 380, x0 + 460):
        cv.rect(lx - 0.4, 10, 0.8, 30, C('#2a2430'))
        cv.fill_poly([(lx - 7, 46), (lx + 7, 46), (lx + 3, 40), (lx - 3, 40)], C('#c8343a'), ink=C('#3a0a14'),
                     iw=DETAIL)
        cv.ellipse(lx, 46.5, 4, 1.2, C('#fff4d0'), em=1.0)
        cv.radial(lx, 60, 26, 30, C('#ffe0a0'), a=0.18, mode='add')
        R.glow(lx, 47, 30, '#ffd890', 0.45, 'none')
        R.light(lx, 262, 46, 40, '#ffd890', 0.16)
    # jukebox wall glow + booth corner lamp
    R.glow(x0 + 600, 220, 40, '#ff6ab0', 0.3, 'neon')
    R.light(x0 + 600, 250, 50, 40, '#ff80c0', 0.1)
    R.ambient.append({"type": "dust_motes", "x": float(wx + 10), "y": float(wy + 20), "w": ww_, "h": 120})


def doormat(R, x0, x1):
    cv = R.cv
    y = H - 8
    cv.rect(x0 + 6, y, x1 - x0 - 12, 7, C('#6a3a2a'), ink=C('#2a1410'), iw=DETAIL)
    yy = y + 1
    while yy < y + 6.5:
        cv.rect(x0 + 7, yy, x1 - x0 - 14, 0.5, C('#4a2418'))
        yy += 1.2
    cv.text('WELCOME', 'cond', 3.2, (x0 + x1) / 2, y + 3.6, C('#d8b080'), 'mm', a=0.8)
    # cool dusk light spilling in from the door below
    cv.radial((x0 + x1) / 2, H + 4, (x1 - x0) * 0.8, 26, C('#ffb890'), a=0.3, mode='add')
    R.light((x0 + x1) / 2, H - 4, (x1 - x0), 30, '#ffb090', 0.14)
