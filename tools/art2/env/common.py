"""Backstreet Oath env v2 -- shared facade building blocks used by every district module (world units)."""
import math

import numpy as np

from raster import C, mix, shade, light, ink_of, value_noise, rng_of
import kit
from kit import M, MAJOR, DETAIL, window, door, awning, cornice, parapet, brick_wall, drainpipe, cable, ac_unit, \
    neon_text, painted_text, poster, tag, concrete_panel, corrugated, plywood, stucco, cast_shadow_rect
from room import FACADE_BOTTOM as FB, H, INT_WALL_BOTTOM as WB, light_pool, sun_rim, weeds

FACADES = {}


def facade(name):
    def deco(f):
        FACADES[name] = f
        return f
    return deco


def door_x(R, x0, w, default=None):
    ds = R.doors_in(x0, x0 + w)
    if ds:
        R.drawn_doors.add(ds[0]['id'])
        return ds[0]['x']
    return default if default is not None else x0 + w / 2


def wall(cv, kind, x, y, w, h, color, seed, soot=0.3):
    if kind == 'brick':
        return brick_wall(cv, x, y, w, h, C(color), seed=seed, soot=soot)
    if kind == 'stone':
        return stone_wall(cv, x, y, w, h, color, seed, soot)
    if kind == 'concrete':
        return concrete_panel(cv, x, y, w, h, C(color), seed=seed, soot=soot)
    if kind == 'corrugated':
        return corrugated(cv, x, y, w, h, C(color), seed=seed)
    if kind == 'clap':
        return clapboard(cv, x, y, w, h, color, seed)
    return stucco(cv, x, y, w, h, C(color), seed, soot=soot)


def stone_wall(cv, x, y, w, h, color, seed, soot=0.3):
    return brick_wall(cv, x, y, w, h, C(color), seed=seed, bw=14, bh=6, var=0.05, mortar=light(C(color), 1.2),
                      soot=soot, accent=0.03)


def clapboard(cv, x, y, w, h, color, seed):
    m = M(C(color))
    mk = cv.rect(x, y, w, h, m.b)
    yy = y
    while yy < y + h:
        cv.rect(x, yy, w, 0.8, m.l, a=0.8, mode='atop')
        cv.rect(x, yy + 3.2, w, 0.8, m.s, mode='atop')
        yy += 4
    kit.weather(cv, x, y, w, h, seed, soot=0.25, streak=True)
    return mk


def lantern(R, x, y, col='#e83a3a', r=3.0, glow=True):
    cv = R.cv
    cv.rect(x - 0.3, y - r - 3, 0.6, 3, C('#2a2026'))
    cv.ellipse(x, y, r, r * 1.2, C(col), ink=shade(C(col), 1.8), iw=DETAIL, em=1.0)
    cv.ellipse(x - r * 0.3, y - r * 0.3, r * 0.4, r * 0.5, light(C(col), 2.0), a=0.7, em=1.0)
    cv.rect(x - r * 0.6, y - r * 1.25, r * 1.2, 0.8, C('#d8b040'), em=1.0)
    cv.rect(x - r * 0.6, y + r * 1.0, r * 1.2, 0.8, C('#d8b040'), em=1.0)
    if glow:
        cv.radial(x, y, r * 4, r * 4, C(col), a=0.3, mode='add')


def bunting(R, x0, y0, x1, y1, sag=6.0, cols=None, seed=0):
    cv = R.cv
    pts = cable(cv, x0, y0, x1, y1, sag, 0.4, '#3a2e34')
    cols = cols or ['#e84a3a', '#f8d040', '#3aa0d8', '#5ac06a', '#f4f0e8']
    for i in range(2, len(pts) - 1, 2):
        x, y = pts[i]
        c = C(cols[(i // 2 + seed) % len(cols)])
        cv.fill_poly([(x - 1.6, y), (x + 1.6, y), (x, y + 4)], c, ink=shade(c, 1.8), iw=0.3)


def storefront(R, x, y, w, h, kind, seed, frame='#3a3440', lit=True, pal=None):
    """Glazed shop window with a display. kind: noodle, books, pharmacy, pizza, lounge, records, hotel, bait, plain."""
    cv = R.cv
    rs = rng_of('sf', seed)
    fm = M(C(frame))
    cv.rect(x - 2, y - 2, w + 4, h + 4, fm.b, ink=fm.i, iw=MAJOR)
    pal = pal or kit.WARM_GLASS
    if lit:
        cv.vgrad(x, y, w, h, pal, em=1.0)
    else:
        cv.vgrad(x, y, w, h, [C('#3e3a5c'), C('#2a2840')])
    by = y + h
    if kind == 'noodle':
        for k in range(int(w / 16)):
            lantern(R, x + 8 + k * 16, y + 7, '#e8403a', 2.6, glow=False)
        cv.rect(x, by - 12, w, 12, C('#7a3a2a'), em=1.0)
        cv.rect(x, by - 12, w, 1.2, C('#c87a4a'), em=1.0)
        for k in range(int(w / 12)):
            bx = x + 6 + k * 12
            cv.ellipse(bx, by - 13.5, 4, 1.6, C('#f4f0e8'), ink=C('#6a4a3a'), iw=0.3, em=1.0)
            cv.ellipse(bx, by - 14.2, 3, 0.8, C('#e8a040'), em=1.0)
            R.cv.line([(bx - 1, by - 16), (bx - 0.5, by - 20), (bx - 1.5, by - 24)], 0.4, C('#ffffff'), a=0.5, em=1.0)
    elif kind == 'books':
        for row in range(3):
            yy = y + 5 + row * (h - 8) / 3
            cv.rect(x + 1, yy + (h - 8) / 3 - 2, w - 2, 1.2, C('#6a4a2a'), em=1.0)
            xx = x + 2
            while xx < x + w - 3:
                bw = rs.uniform(1.4, 2.6)
                bh = rs.uniform(5, (h - 8) / 3 - 2.5)
                c = rs.choice([C('#c84a3a'), C('#3a6aa8'), C('#4a8a5a'), C('#d8b050'), C('#7a4a7a'), C('#e8e0d0')])
                cv.rect(xx, yy + (h - 8) / 3 - 2 - bh, bw, bh, c, em=1.0)
                xx += bw + 0.3
    elif kind == 'pharmacy':
        for row in range(3):
            yy = y + 6 + row * (h - 8) / 3
            cv.rect(x + 1, yy + 8, w - 2, 1, C('#c8d8e0'), em=1.0)
            for k in range(int(w / 5)):
                c = rs.choice([C('#e84a5a'), C('#4a9ae8'), C('#f4f0e8'), C('#5ac08a'), C('#f8d040')])
                cv.rect(x + 2 + k * 5, yy + 8 - rs.uniform(3, 6), 3.2, 6, c, em=1.0)
    elif kind == 'pizza':
        cv.ellipse(x + w * 0.3, by - 10, 9, 3.5, C('#e8a040'), ink=C('#7a4a1a'), iw=0.4, em=1.0)
        for k in range(6):
            cv.ellipse(x + w * 0.3 + rs.uniform(-6, 6), by - 10 + rs.uniform(-1.5, 1.5), 1, 0.6, C('#c8302a'), em=1.0)
        px = x + w * 0.7
        cv.ellipse(px, by - 24, 3, 3.4, C('#6a4a40'), em=1.0)
        cv.fill_poly([(px - 6, by), (px - 5, by - 20), (px + 5, by - 20), (px + 6, by)], C('#f0ece4'), em=1.0)
        cv.ellipse(px, by - 27.5, 3.5, 1.6, C('#f4f4f0'), em=1.0)
    elif kind in ('lounge', 'hotel', 'records'):
        cv.vgrad(x, y, w, h, [C('#3a1a4a'), C('#6a2a6a'), C('#a84a7a')], em=1.0)
        for k in range(3):
            px = x + w * (0.2 + k * 0.3)
            cv.ellipse(px, by - 16, 2.4, 2.8, C('#1e1024'), em=1.0)
            cv.fill_poly([(px - 4, by), (px - 3, by - 13), (px + 3, by - 13), (px + 4, by)], C('#1e1024'), em=1.0)
        if kind == 'records':
            for k in range(int(w / 12)):
                cv.ellipse(x + 6 + k * 12, y + 8, 4.5, 4.5, C('#141018'), ink=C('#5a3a6a'), iw=0.3, em=1.0)
                cv.ellipse(x + 6 + k * 12, y + 8, 1.4, 1.4, rs.choice([C('#ff4a8a'), C('#4ae0ff'), C('#f8d040')]),
                           em=1.0)
    elif kind == 'bait':
        cv.vgrad(x, y, w, h, [C('#d8e8c8'), C('#a8c8a0'), C('#6a8a70')], em=1.0)
        for k in range(int(w / 8)):
            cv.line([(x + 4 + k * 8, y + 2), (x + 4 + k * 8, y + 16)], 0.3, C('#3a4a3a'), em=1.0)
            cv.ellipse(x + 4 + k * 8, y + 17, 1.2, 2.2, rs.choice([C('#e84a3a'), C('#f8d040'), C('#4ac0e8')]), em=1.0)
        cv.rect(x, by - 8, w, 8, C('#4a5a4a'), em=1.0)
    # glass reflection + top highlight
    cv.fill_poly([(x + w * 0.12, y), (x + w * 0.24, y), (x + w * 0.04, y + h), (x - w * 0.08, y + h)], C('#ffffff'),
                 a=0.12, mode='atop')
    cv.rect(x, y, w, 0.8, C('#ffffff'), a=0.6)


def shop_door(R, cx, w=24.0, h=58.0, color='#5a3a2a', lit=True, frame='#3a3440'):
    door(R.cv, cx - w / 2, FB, w, h, C(color), glass=True, lit=lit, seed=int(cx), frame=frame, step=False,
         transom=True)
    if lit:
        light_pool(R, cx, FB + 8, 22, 9, '#ffd090', a=0.2)


def shop_building(R, x0, w, f, wallkind='brick', wallcol='#9a5442', trim='#d8ccb4', top=60, upper=1,
                  sign_bg='#2a5a3a', sign_fg='#f4e8c0', sign_style='painted', display='plain', awn=None, glass=None,
                  door_col='#5a3a2a', seed=0, lit_p=0.55, neon_col='#ff5aa0', sign_y=None):
    cv = R.cv
    rs = rng_of('shop', R.id, x0, seed)
    wall(cv, wallkind, x0, top, w, FB - top, wallcol, seed=hash((R.id, x0)) % 9999)
    cornice(cv, x0, top, w, C(trim), h=4.5)
    parapet(cv, x0 - 1, top - 5, w + 2, shade(C(wallcol), 0.6), h=5)
    sun_rim(R, x0, top - 5, FB - 50, a=0.35)
    for fl in range(upper):
        fy = top + 12 + fl * 42
        n = max(2, int(w / 52))
        for k in range(n):
            wx = x0 + (w - n * 15) / (n + 1) * (k + 1) + 15 * k
            window(cv, wx, fy, 15, 26, lit=rs.random() < lit_p, seed=hash((x0, fy, k)) % 9999, frame=trim)
    sy = sign_y if sign_y is not None else top + 12 + upper * 42
    dx = door_x(R, x0, w)
    # sign band
    if sign_style == 'neon':
        cv.rect(x0 + 8, sy, w - 16, 18, C('#1a1420'), ink=C('#0a0610'), iw=MAJOR)
        neon_text(cv, f.get('sign', ''), x0 + w / 2, sy + 9.5, 10, C(neon_col), tracking=0.6, glow=0.5)
        R.glow(x0 + w / 2, sy + 9, w * 0.45, '#%02x%02x%02x' % C(neon_col)[:3], 0.45, 'neon')
    elif sign_style == 'lightbox':
        sm = M(C(sign_bg))
        cv.rect(x0 + 8, sy, w - 16, 18, sm.b, ink=sm.i, iw=MAJOR)
        cv.vgrad(x0 + 10, sy + 2, w - 20, 14, [light(sm.b, 1.4), sm.b, sm.s], em=1.0)
        painted_text(cv, f.get('sign', ''), x0 + w / 2, sy + 9.5, 10, C(sign_fg), tracking=0.5, em=1.0)
        R.glow(x0 + w / 2, sy + 9, w * 0.4, '#%02x%02x%02x' % light(sm.b, 1.5)[:3], 0.3, 'none')
    else:
        sm = M(C(sign_bg))
        cv.rect(x0 + 8, sy, w - 16, 17, sm.b, ink=sm.i, iw=MAJOR)
        cv.rect(x0 + 8, sy, w - 16, 1, sm.h, mode='atop')
        painted_text(cv, f.get('sign', ''), x0 + w / 2, sy + 9, 10, C(sign_fg), tracking=0.5)
    # storefront glass either side of the door
    gy0 = sy + 22
    gy1 = FB - 5
    left_w = dx - 16 - (x0 + 10)
    right_x = dx + 16
    if left_w > 12:
        storefront(R, x0 + 10, gy0, left_w, gy1 - gy0, display, seed=seed * 3 + 1, pal=glass)
    if x0 + w - 10 - right_x > 12:
        storefront(R, right_x, gy0, x0 + w - 10 - right_x, gy1 - gy0, display, seed=seed * 3 + 2, pal=glass)
    cv.rect(x0 + 6, FB - 5, w - 12, 5, shade(C(wallcol), 0.5), ink=C('#1a1220'), iw=DETAIL)
    shop_door(R, dx, 24, min(60, FB - gy0 + 2), door_col)
    if awn:
        awning(cv, x0 + 8, gy0 - 8, w - 16, 7, C(awn[0]), C(awn[1]) if len(awn) > 1 else None, stripe=6,
               valance=3)
    light_pool(R, x0 + w / 2, FB + 10, w * 0.5, 12, '#ffc070', a=0.16)
    R.light(x0 + w / 2, FB + 14, w * 0.55, 30, '#ffb060', 0.14)
    R.glow(x0 + w / 2, (gy0 + gy1) / 2, w * 0.45, '#ffc070', 0.22, 'none')
    return dx, gy0


def generic_entrance(R, d):
    """Fallback door for a rooms.json door no facade drew."""
    shop_door(R, d['x'], 24, 56, '#4a3a34')


def chainlink(cv, x, y, w, h, col='#9898a8', a=0.75, pitch=4.0):
    lay = cv.layer(x - 1, y - 1, w + 2, h + 2)
    mk = lay.rect_mask(x, y, w, h)
    x_0, y_0, mm = mk
    hh, ww = mm.shape
    X = (np.arange(ww, dtype=np.float32) + x_0 + lay.ox + 0.5) / lay.D
    Y = (np.arange(hh, dtype=np.float32) + y_0 + lay.oy + 0.5) / lay.D
    XX, YY = np.meshgrid(X, Y)
    p = pitch
    d1 = np.abs(((XX + YY) % p) - p / 2)
    d2 = np.abs(((XX - YY) % p) - p / 2)
    a1 = np.clip((d1 - (p / 2 - 0.33)) / 0.33, 0, 1)
    a2 = np.clip((d2 - (p / 2 - 0.33)) / 0.33, 0, 1)
    lay.paint((x_0, y_0, np.maximum(a1, a2) * mm), C(col), a=a)
    cv.merge(lay, ink=C('#0e0a14', 160), iw=0.4)


def fence(cv, x, top, w, bottom=FB, post='#6a6a72', barbed=True, pitch=4.0, col='#a8a8b4'):
    chainlink(cv, x, top, w, bottom - top, col=col, pitch=pitch)
    pm = M(C(post))
    cv.rect(x, top, w, 1.2, pm.b, ink=pm.i, iw=0.4)
    xx = x + 4
    while xx < x + w:
        cv.rect(xx - 1, top - 2, 2, bottom - top + 2, pm.b, ink=pm.i, iw=0.4)
        if barbed:
            cv.line([(xx, top - 2), (xx + 4, top - 9)], 0.6, pm.b)
        xx += 50
    if barbed:
        for k in range(3):
            pts = [(x + j * 2, top - 3.5 - k * 2.2 + math.sin(j * 1.3 + k) * 0.5) for j in range(int(w / 2) + 1)]
            cv.line(pts, 0.35, C('#8a8a96'))


def smokestack(R, x, top, bottom, w=14.0, col='#7a4a3a', smoke=True, band='#e8e0d0'):
    cv = R.cv
    m = M(C(col))
    cv.fill_poly([(x - w / 2, bottom), (x - w * 0.42, top), (x + w * 0.42, top), (x + w / 2, bottom)], m.b,
                 ink=m.i, iw=MAJOR)
    cv.hgrad(x - w / 2, top, w, bottom - top, [m.l, m.b, m.s, m.d], mode='atop')
    cv.rect(x - w * 0.45, top, w * 0.9, 3, m.s, mode='atop')
    if band:
        for yy in (top + 10, top + 16):
            cv.rect(x - w * 0.45, yy, w * 0.9, 2, C(band), mode='atop', a=0.7)
    if smoke:
        R.ambient.append({"type": "smoke", "x": float(x), "y": float(top - 2), "rate": 0.8})


def big_door(cv, x, yb, w, h, color, kind='roller', seed=0):
    """Loading door: 'roller' shutter or 'barn' doors."""
    m = M(C(color))
    cv.rect(x - 2, yb - h - 2, w + 4, h + 2, shade(m.b, 1.2), ink=m.i, iw=MAJOR)
    mk = cv.rect(x, yb - h, w, h, m.b, ink=m.i, iw=DETAIL)
    if kind == 'roller':
        yy = yb - h
        while yy < yb:
            cv.rect(x, yy, w, 0.6, m.s, mode='atop')
            cv.rect(x, yy + 0.6, w, 0.5, m.l, mode='atop', a=0.7)
            yy += 2.4
    else:
        cv.rect(x + w / 2 - 0.4, yb - h, 0.8, h, m.d)
        for side in (0, 1):
            xa = x + side * w / 2
            cv.line([(xa + 1, yb - 1), (xa + w / 2 - 1, yb - h + 1)], 1.2, m.l)
            cv.rect(xa + 1, yb - h + 1, w / 2 - 2, h - 2, None, ink=m.d, iw=DETAIL)
    kit.weather(cv, x, yb - h, w, h, seed, soot=0.4, streak=True)
    return mk


def gable(cv, x, y, w, rise, color, ink=None):
    m = M(C(color))
    cv.fill_poly([(x - 3, y), (x + w / 2, y - rise), (x + w + 3, y)], m.b, ink=ink or m.i, iw=MAJOR)
    cv.fill_poly([(x - 3, y), (x + w / 2, y - rise), (x + w / 2, y)], m.l, a=0.35, mode='atop')
