"""Backstreet Oath env v2 -- props at density 2. Canvas size and anchor/footprint (u) match v1 props.json exactly.

Props are drawn in neutral albedo (the room lightmap tints them in-engine). Key light from the upper left:
left faces use the light tone, right faces the shade tone. 2 tx ink on silhouettes, 1 tx on details.
"""
import math

import numpy as np

from raster import Canvas, C, mix, shade, light, ink_of, value_noise, rng_of
import kit
from kit import M, MAJOR, DETAIL

PROPS = {}


def prop(name):
    def deco(f):
        PROPS[name] = f
        return f
    return deco


def ao(cv, x, yb, w, a=0.45):
    cv.vgrad(x, yb - 2, w, 2, [C('#140c18', 0), C('#140c18', int(255 * a))])


def cyl(cv, x, y, w, h, m, a=1.0, mode='over'):
    """Cel-shaded cylinder body (light left, shade right)."""
    return cv.hgrad(x, y, w, h, [(0.0, m.s), (0.12, m.l), (0.35, m.b), (0.75, m.b), (0.86, m.s), (1.0, m.d)],
                    a=a, mode=mode)


@prop('lamp_post')
def p_lamp_post(cv, W, Hh):
    m = M(C('#2e3a3a'))
    lay = cv.layer()
    cx = 7
    lay.rect(cx - 3.5, Hh - 6, 7, 6, m.b)          # base
    lay.rect(cx - 2.5, Hh - 9, 5, 3, m.b)
    lay.rect(cx - 1.2, 16, 2.4, Hh - 25, m.b)       # shaft
    lay.rect(cx - 2, 40, 4, 2, m.b)
    lay.rect(cx - 2, 14, 4, 3, m.b)
    # lantern
    lay.fill_poly([(cx - 4.5, 4.5), (cx + 4.5, 4.5), (cx + 3.2, 14), (cx - 3.2, 14)], m.b)
    lay.fill_poly([(cx - 5, 4.5), (cx, 0.5), (cx + 5, 4.5)], m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.hgrad(cx - 1.2, 16, 2.4, Hh - 25, [m.l, m.b, m.d], mode='atop')
    cv.hgrad(cx - 3.5, Hh - 6, 7, 6, [m.l, m.b, m.d], mode='atop')
    # glass panes (bright)
    cv.fill_poly([(cx - 3.3, 5.6), (cx + 3.3, 5.6), (cx + 2.4, 13), (cx - 2.4, 13)], C('#fff2c0'))
    cv.rect(cx - 0.35, 5.6, 0.7, 7.4, m.b)
    cv.radial(cx, 9, 3, 4, C('#ffffff'), a=0.6, mode='add')
    cv.rect(cx - 4.5, 4.5, 9, 0.6, m.h, a=0.8)
    ao(cv, cx - 4, Hh, 8)


@prop('bus_stop')
def p_bus_stop(cv, W, Hh):
    frame = M(C('#2e5a4e'))
    glass = C('#b8d8e0')
    # sign pole + round sign (left)
    cv.rect(4, 8, 2, Hh - 8, frame.b, ink=frame.i, iw=DETAIL)
    cv.ellipse(5, 7, 5, 5, C('#2a5ab0'), ink=C('#0e1a3a'), iw=MAJOR)
    cv.ellipse(5, 7, 3.6, 3.6, C('#f4f4f0'))
    cv.text('BUS', 'cond', 3, 5, 7, C('#2a5ab0'), 'mm')
    cv.rect(2.5, 15, 5, 7, C('#f0ece0'), ink=C('#2a2430'), iw=DETAIL)
    for k in range(4):
        cv.rect(3.2, 16.2 + k * 1.4, 3.6, 0.5, C('#6a6070'))
    # shelter: back glass, roof, side frames, bench, ad panel
    x0, x1 = 12, 60
    top = 18
    cv.rect(x0 + 2, top + 6, x1 - x0 - 4, Hh - top - 12, glass, a=0.45)
    cv.fill_poly([(x0 + 6, top + 8), (x0 + 12, top + 8), (x0 + 2, Hh - 10), (x0 + 2, Hh - 22)], C('#ffffff'), a=0.25)
    lay = cv.layer()
    lay.rect(x0 - 2, top, x1 - x0 + 4, 5, frame.b)                # roof
    lay.rect(x0, top + 5, 2.2, Hh - top - 5, frame.b)
    lay.rect(x1 - 2.2, top + 5, 2.2, Hh - top - 5, frame.b)
    lay.rect(x0, Hh - 12, x1 - x0, 1.5, frame.b)
    cv.merge(lay, ink=frame.i, iw=MAJOR)
    cv.rect(x0 - 2, top, x1 - x0 + 4, 1, frame.h, a=0.9)
    cv.rect(x0 - 2, top + 4, x1 - x0 + 4, 1, frame.d)
    # ad panel (lightbox) on the right half
    ax0 = x0 + 26
    cv.rect(ax0, top + 9, 18, 30, C('#f4ecd8'), ink=C('#1e2a28'), iw=DETAIL)
    cv.vgrad(ax0 + 1, top + 10, 16, 28, [C('#e86a4a'), C('#f0b050'), C('#f4e8c0')])
    cv.text('CANAL', 'sign', 3.2, ax0 + 9, top + 16, C('#ffffff'), 'mm')
    cv.text('MARKET', 'cond', 3.0, ax0 + 9, top + 21, C('#3a1a14'), 'mm')
    cv.ellipse(ax0 + 9, top + 30, 4, 3, C('#5aa0b0'))
    # bench
    bm = M(C('#9a6a3a'))
    cv.rect(x0 + 3, Hh - 20, x1 - x0 - 6, 3, bm.b, ink=bm.i, iw=DETAIL)
    cv.rect(x0 + 3, Hh - 20, x1 - x0 - 6, 0.7, bm.h, mode='atop')
    cv.rect(x0 + 6, Hh - 17, 1.5, 5, frame.b)
    cv.rect(x1 - 7.5, Hh - 17, 1.5, 5, frame.b)
    cv.text('RIVER LINE', 'cond', 2.6, (x0 + x1) / 2, top + 2.6, C('#e8f0e0'), 'mm')
    ao(cv, 0, Hh, W)


@prop('newsbox')
def p_newsbox(cv, W, Hh):
    m = M(C('#c83a34'))
    cv.rect(1.5, 2, 13, Hh - 7, m.b, ink=m.i, iw=MAJOR)
    cv.hgrad(1.5, 2, 13, Hh - 7, [m.l, m.b, m.s], mode='atop', a=0.8)
    cv.fill_poly([(1, 2), (15, 2), (14, 0.5), (2, 0.5)], m.s, ink=m.i, iw=DETAIL)
    cv.rect(3.5, 5, 9, 9, C('#d8dce0'), ink=m.d, iw=DETAIL)
    cv.rect(4.5, 6, 7, 7, C('#f4f0e4'))
    cv.text('NEWS', 'cond', 2.4, 8, 7.3, C('#2a2430'), 'mm')
    for k in range(3):
        cv.rect(5, 9 + k * 1.3, 6, 0.4, C('#7a7480'))
    cv.text('BELLWETHER', 'cond', 1.9, 8, 16.5, C('#f4e8d0'), 'mm')
    cv.rect(10.5, 18, 2.5, 1.5, C('#e8c860'), ink=C('#3a2a10'), iw=0.3)
    cv.rect(3, Hh - 5, 1.5, 5, C('#3a3440'))
    cv.rect(11.5, Hh - 5, 1.5, 5, C('#3a3440'))
    ao(cv, 0, Hh, W)


@prop('hydrant')
def p_hydrant(cv, W, Hh):
    m = M(C('#d03a30'))
    cx = 9
    lay = cv.layer()
    lay.rect(cx - 6, Hh - 3, 12, 3, m.b)
    lay.rect(cx - 4.2, 7, 8.4, Hh - 10, m.b)
    lay.ellipse(cx, 6.5, 4.6, 4.2, m.b)
    lay.rect(cx - 1.2, 0.8, 2.4, 3, m.b)
    lay.rect(cx - 7.5, 10.5, 15, 4, m.b)                   # side nozzles
    lay.ellipse(cx, 15.5, 2.4, 2.4, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cyl(cv, cx - 4.2, 7, 8.4, Hh - 10, m, mode='atop')
    cv.ellipse(cx - 1.6, 5.2, 1.6, 1.2, m.h, a=0.8)
    cv.rect(cx - 4.4, 8.2, 8.8, 0.8, m.d)
    cv.ellipse(cx, 15.5, 1.2, 1.2, m.d)
    cv.rect(cx - 7.5, 10.5, 15, 0.8, m.l, mode='atop')
    ao(cv, 2, Hh, 14)


@prop('trash_can')
def p_trash_can(cv, W, Hh):
    m = M(C('#8a9098'))
    lay = cv.layer()
    lay.fill_poly([(2.5, 6), (16.5, 6), (15.5, Hh), (3.5, Hh)], m.b)
    lay.ellipse(9.5, 5, 8.2, 2.4, m.b)
    lay.rect(7.5, 0.8, 4, 2.4, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cyl(cv, 2.5, 6, 14, Hh - 6, m, mode='atop')
    for yy in (10, 16, 22):
        cv.rect(2.8, yy, 13.5, 0.7, m.d, a=0.8, mode='atop')
        cv.rect(2.8, yy + 0.7, 13.5, 0.5, m.h, a=0.6, mode='atop')
    cv.ellipse(9.5, 4.6, 8.2, 2.1, m.l)
    cv.ellipse(9.5, 4.6, 6.5, 1.2, m.b)
    kit.weather(cv, 2.5, 6, 14, Hh - 6, 5, soot=0.3, streak=False)
    ao(cv, 3, Hh, 13)


@prop('mailbox')
def p_mailbox(cv, W, Hh):
    m = M(C('#2e6a52'))
    lay = cv.layer()
    lay.rect(1.5, 6, 15, Hh - 12, m.b)
    lay.ellipse(9, 6.5, 7.5, 5.5, m.b)
    lay.rect(2.5, Hh - 6, 2.5, 6, m.b)
    lay.rect(13, Hh - 6, 2.5, 6, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.hgrad(1.5, 1, 15, Hh - 7, [m.l, m.b, m.s], mode='atop', a=0.9)
    cv.rect(4, 8, 10, 2.2, m.d, ink=m.i, iw=DETAIL)
    cv.rect(5, 13, 8, 5, C('#e8e4d4'), ink=m.d, iw=DETAIL)
    cv.text('MAIL', 'cond', 2.6, 9, 15.5, C('#2e4a3e'), 'mm')
    cv.rect(1.5, Hh - 7, 15, 1, m.d)
    ao(cv, 1, Hh, 16)


@prop('bench')
def p_bench(cv, W, Hh):
    wm = M(C('#a8743e'))
    im = M(C('#2e3436'))
    lay = cv.layer()
    for x in (4, W - 7):
        lay.rect(x, 6, 3, Hh - 6, im.b)
        lay.fill_poly([(x - 1, Hh), (x + 4, Hh), (x + 3, Hh - 2), (x, Hh - 2)], im.b)
    cv.merge(lay, ink=im.i, iw=MAJOR)
    for k, y in enumerate((2, 6.5, 13)):
        hgt = 3.2 if k < 2 else 3.6
        cv.rect(1, y, W - 2, hgt, wm.b, ink=wm.i, iw=MAJOR if k == 2 else DETAIL)
        cv.rect(1, y, W - 2, 0.8, wm.h, mode='atop')
        cv.rect(1, y + hgt - 0.8, W - 2, 0.8, wm.s, mode='atop')
    cv.rect(2, 16.6, W - 4, 0.8, C('#140c18'), a=0.4)
    for x in (6, W - 10):
        cv.ellipse(x, 3.6, 0.5, 0.5, im.b)
        cv.ellipse(x, 8.1, 0.5, 0.5, im.b)
    ao(cv, 1, Hh, W - 2)


@prop('crate')
def p_crate(cv, W, Hh):
    m = M(C('#b8874e'))
    lay = cv.layer()
    lay.rect(1, 1, 22, Hh - 1, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    for k in range(4):
        cv.rect(1, 1 + k * 6, 22, 0.5, m.s, mode='atop')
    # frame boards + diagonal brace
    for (x, y, w, h) in ((1, 1, 22, 3), (1, Hh - 3, 22, 3), (1, 1, 3, Hh - 1), (20, 1, 3, Hh - 1)):
        cv.rect(x, y, w, h, m.l, ink=m.d, iw=DETAIL)
    cv.line([(4, Hh - 3.5), (20, 4)], 2.6, m.l, ink=m.d, iw=DETAIL)
    for (x, y) in ((2.5, 2.5), (21.5, 2.5), (2.5, Hh - 1.5), (21.5, Hh - 1.5)):
        cv.ellipse(x, y, 0.5, 0.5, C('#4a3a30'))
    cv.text('FRAGILE', 'cond', 2.2, 12, Hh * 0.55, C('#8a3a2a'), 'mm', a=0.6)
    ao(cv, 1, Hh, 22)


@prop('traffic_cone')
def p_cone(cv, W, Hh):
    m = M(C('#f07a2a'))
    lay = cv.layer()
    lay.rect(1, Hh - 2.5, 14, 2.5, C('#3a3036'))
    lay.fill_poly([(4, Hh - 2.5), (12, Hh - 2.5), (9, 1.5), (7, 1.5)], m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.hgrad(4, 1.5, 8, Hh - 4, [m.l, m.b, m.s], mode='atop')
    for y0, y1 in ((5.5, 7.5), (10, 12)):
        cv.fill_poly([(8 - (y0 / Hh) * 4 - 0.5, y0), (8 + (y0 / Hh) * 4 + 0.5, y0), (8 + (y1 / Hh) * 4 + 0.8, y1),
                      (8 - (y1 / Hh) * 4 - 0.8, y1)], C('#f4f4f0'), mode='atop')
    ao(cv, 1, Hh, 14)


@prop('dumpster')
def p_dumpster(cv, W, Hh):
    m = M(C('#3e7a5a'))
    lay = cv.layer()
    lay.fill_poly([(3, 8), (W - 3, 8), (W - 5, Hh - 5), (5, Hh - 5)], m.b)
    lay.fill_poly([(1, 8), (W / 2, 8), (W / 2, 3), (2.5, 5)], m.s)                   # lids
    lay.fill_poly([(W / 2, 8), (W - 1, 8), (W - 2.5, 4.5), (W / 2, 4)], m.s)
    for x in (9, W - 11):
        lay.ellipse(x, Hh - 3, 3, 3, C('#2a2430'))
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.hgrad(3, 8, W - 6, Hh - 13, [m.l, m.b, m.b, m.s], mode='atop', a=0.9)
    for x in range(8, int(W) - 6, 7):
        cv.rect(x, 10, 1, Hh - 17, m.s, mode='atop')
        cv.rect(x + 1, 10, 0.5, Hh - 17, m.l, mode='atop', a=0.6)
    cv.rect(3, 8, W - 6, 1.2, m.h, mode='atop')
    cv.rect(W / 2 - 10, 16, 20, 5, C('#e8e4d4'), ink=m.d, iw=DETAIL)
    cv.text('CITY SANITATION', 'cond', 1.9, W / 2, 18.5, C('#2a3a30'), 'mm')
    kit.weather(cv, 3, 8, W - 6, Hh - 13, 9, soot=0.45, streak=True)
    for x in (9, W - 11):
        cv.ellipse(x, Hh - 3, 1.2, 1.2, C('#8a8a96'))
    ao(cv, 3, Hh, W - 6)


@prop('oil_drum')
def p_oil_drum(cv, W, Hh):
    m = M(C('#3a5a8a'))
    lay = cv.layer()
    lay.rect(1.5, 2, 14, Hh - 2, m.b)
    lay.ellipse(8.5, 2.2, 7, 1.8, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cyl(cv, 1.5, 2, 14, Hh - 2, m, mode='atop')
    for yy in (8, 16):
        cv.rect(1.5, yy, 14, 1, m.d, mode='atop')
        cv.rect(1.5, yy + 1, 14, 0.5, m.h, a=0.6, mode='atop')
    cv.ellipse(8.5, 2.2, 6.4, 1.4, m.l)
    cv.ellipse(11, 2.2, 1, 0.5, m.d)
    kit.corrugated  # noqa
    rs = rng_of('drum')
    for _ in range(4):
        x = rs.uniform(3, 14)
        cv.vgrad(x, rs.uniform(3, 10), rs.uniform(1, 2.5), rs.uniform(5, 12), [C('#9a4a20', 150), C('#9a4a20', 0)],
                 mode='atop')
    ao(cv, 1.5, Hh, 14)


@prop('car_wreck')
def p_car_wreck(cv, W, Hh):
    body = M(C('#8a5a3a'))
    lay = cv.layer()
    # body profile (sedan), no wheels: sits on cinder blocks
    pts = [(3, 26), (6, 19), (22, 17), (34, 6), (64, 6), (76, 17), (94, 19), (97, 24), (97, 31), (3, 31)]
    lay.fill_poly(pts, body.b)
    cv.merge(lay, ink=body.i, iw=MAJOR)
    cv.vgrad(3, 6, 94, 25, [body.h, body.l, body.b, body.s], mode='atop', a=0.8)
    # windows (broken/dark)
    cv.fill_poly([(37, 8.5), (48, 8.5), (48, 17), (27, 17)], C('#2a2836'), ink=body.d, iw=DETAIL)
    cv.fill_poly([(51, 8.5), (62.5, 8.5), (72, 17), (51, 17)], C('#2a2836'), ink=body.d, iw=DETAIL)
    cv.line([(40, 9), (44, 13), (41, 16)], 0.4, C('#c8c8d8'), a=0.7)
    cv.fill_poly([(55, 9), (60, 9), (57, 13)], C('#3a3a4a'))
    # door seams, handles, trim, rust
    for x in (49.5,):
        cv.rect(x, 17, 0.6, 13, body.d)
    cv.rect(3, 23.5, 94, 1, C('#c8c0b0'), a=0.6)
    cv.rect(91, 20, 5, 3, C('#e8d8a0'), ink=body.d, iw=DETAIL)     # headlight
    cv.rect(3.5, 20, 3, 2.5, C('#c83a3a'), ink=body.d, iw=DETAIL)
    rs = rng_of('rust_car')
    for _ in range(10):
        cv.ellipse(rs.uniform(8, 92), rs.uniform(18, 30), rs.uniform(1.5, 4), rs.uniform(1, 2.5), C('#6a3a1e'),
                   a=0.6, mode='atop')
    # wheel wells (empty) and cinder blocks
    for x in (20, 78):
        cv.ellipse(x, 31, 8, 7, C('#1a1420'), mode='atop')
        cv.rect(x - 5, 31, 10, Hh - 31, C('#9a948a'), ink=C('#2a2430'), iw=DETAIL)
        cv.rect(x - 3, 33, 2.5, 3, C('#5a544e'))
        cv.rect(x + 0.5, 33, 2.5, 3, C('#5a544e'))
    kit.weather(cv, 3, 6, 94, 25, 3, soot=0.25, streak=False)
    ao(cv, 3, Hh, 94)


@prop('tire_stack')
def p_tire_stack(cv, W, Hh):
    m = M(C('#34303a'))
    for k in range(4):
        y = Hh - 4 - k * 7.5
        cv.ellipse(12, y, 11, 4.2, m.b, ink=m.i, iw=MAJOR)
        cv.rect(1, y - 3.5, 22, 3.5, m.b)
        cv.hgrad(1, y - 3.5, 22, 3.5, [m.l, m.b, m.d], mode='atop')
        cv.ellipse(12, y - 3.5, 11, 4.2, m.l, ink=m.i, iw=MAJOR)
        cv.ellipse(12, y - 3.5, 5.5, 2, C('#140e18'))
        for j in range(8):
            cv.rect(2 + j * 2.6, y - 3.2, 0.6, 3, m.d, a=0.8)
    ao(cv, 1, Hh, 22)


@prop('pallet')
def p_pallet(cv, W, Hh):
    m = M(C('#c09a64'))
    for k in range(2):
        y = Hh - 8 - k * 7
        cv.rect(1, y, 32, 2.2, m.b, ink=m.i, iw=DETAIL)
        cv.rect(1, y, 32, 0.6, m.h, mode='atop')
        for x in (2, 15.5, 29):
            cv.rect(x, y + 2.2, 3, 3, m.s, ink=m.i, iw=DETAIL)
        cv.rect(1, y + 5.2, 32, 1.8, m.b, ink=m.i, iw=DETAIL)
    kit.weather(cv, 1, 1, 32, Hh - 1, 11, soot=0.3, streak=False)
    ao(cv, 1, Hh, 32)


@prop('counter_diner')
def p_counter(cv, W, Hh):
    top = M(C('#f0ece4'))
    red = M(C('#c0343a'))
    # counter top (laminate) with chrome edge
    cv.rect(1, 6, W - 2, 6, top.b, ink=top.i, iw=MAJOR)
    cv.vgrad(1, 6, W - 2, 6, [top.h, top.b, top.s], mode='atop', a=0.7)
    cv.rect(1, 12, W - 2, 2.5, C('#c8ccd8'), ink=C('#3a3a48'), iw=DETAIL)
    cv.rect(1, 12, W - 2, 0.8, C('#ffffff'), mode='atop')
    # front: red quilted panel with chrome strips
    cv.rect(2, 14.5, W - 4, Hh - 17, red.b, ink=red.i, iw=MAJOR)
    cv.vgrad(2, 14.5, W - 4, Hh - 17, [red.l, red.b, red.s], mode='atop', a=0.8)
    x = 2 + 10
    while x < W - 4:
        cv.rect(x, 15, 1.2, Hh - 18, C('#d8dce4'), mode='atop')
        cv.rect(x + 1.2, 15, 0.6, Hh - 18, red.d, mode='atop')
        x += 13
    cv.rect(2, Hh - 3, W - 4, 3, C('#3a3440'), ink=C('#140c18'), iw=DETAIL)       # kick plate
    cv.rect(2, Hh - 3, W - 4, 0.8, C('#8a8a96'), mode='atop')
    # items on the counter
    def napkins(x):
        cv.rect(x, 1.5, 5, 5, C('#c8ccd8'), ink=C('#3a3a48'), iw=DETAIL)
        cv.rect(x + 1, 0.5, 3, 1.5, C('#ffffff'))
    napkins(20)
    for x, c in ((30, C('#c8302a')), (33, C('#e8c030'))):
        cv.fill_poly([(x - 1.2, 6), (x + 1.2, 6), (x + 0.8, 1), (x - 0.8, 1)], c, ink=shade(c, 1.8), iw=DETAIL)
    cv.ellipse(70, 5.5, 6, 1.4, C('#f4f0e8'), ink=C('#6a6070'), iw=0.4)
    cv.ellipse(70, 4.6, 3.5, 1.2, C('#c8803a'))                                          # pie slice plate
    cv.fill_poly([(100, 6), (106, 6), (105, 2), (101, 2)], C('#f4f0e8'), ink=C('#6a6070'), iw=0.4)   # mug
    cv.rect(106, 3, 1.5, 2, C('#f4f0e8'), ink=C('#6a6070'), iw=0.3)
    cv.ellipse(130, 4, 3.5, 3, C('#e8f4ff'), ink=C('#6a7888'), iw=0.4, a=0.75)          # sugar jar
    cv.rect(129, 0.5, 2, 1.2, C('#c8ccd8'))
    ao(cv, 2, Hh, W - 4)


@prop('jukebox')
def p_jukebox(cv, W, Hh):
    wood = M(C('#8a4a2a'))
    lay = cv.layer()
    lay.fill_poly([(2, Hh), (2, 14), (16, 1.5), (30, 14), (30, Hh)], wood.b)
    lay.ellipse(16, 14, 14, 13, wood.b)
    cv.merge(lay, ink=wood.i, iw=MAJOR)
    cv.hgrad(2, 1, 28, Hh - 1, [wood.l, wood.b, wood.b, wood.s], mode='atop')
    # rainbow arch tubes
    for k, c in enumerate(('#ff5a7a', '#ffb43a', '#f8f060', '#6ae08a', '#5ab8ff')):
        r = 12 - k * 1.6
        pts = [(16 + math.cos(a) * r, 15 + math.sin(a) * r * 1.05) for a in np.linspace(math.pi, 2 * math.pi, 24)]
        cv.line(pts, 1.4, C(c))
    cv.ellipse(16, 15, 4.5, 4.5, C('#2a1a2a'))
    # record window + selector
    cv.rect(7, 17, 18, 10, C('#f4e0b0'), ink=wood.d, iw=DETAIL)
    for k in range(6):
        cv.rect(8 + k * 3, 18, 1.8, 8, C('#c8a060'), a=0.7)
    cv.rect(7, 29, 18, 6, C('#c8ccd8'), ink=wood.d, iw=DETAIL)
    for k in range(8):
        cv.rect(8 + k * 2.1, 30, 1.4, 4, C('#e8e4dc'))
    # speaker grille + bubble tubes on the sides
    cv.rect(8, 37, 16, 6, C('#5a2a1a'), ink=wood.d, iw=DETAIL)
    for k in range(5):
        cv.rect(9, 38 + k * 1.1, 14, 0.4, C('#c8a060'), a=0.7)
    for x in (4, 28):
        cv.rect(x - 1, 16, 2, 26, C('#ff8ac8'))
        for k in range(4):
            cv.ellipse(x, 20 + k * 6, 0.5, 0.5, C('#ffffff'))
    ao(cv, 2, Hh, 28)


@prop('booth_seat')
def p_booth(cv, W, Hh):
    red = M(C('#c0343a'))
    chrome = M(C('#c8ccd8'))
    # two seat backs facing each other, table in the middle (front view)
    for x0 in (1, W - 17):
        lay = cv.layer()
        lay.rect(x0, 2, 16, Hh - 6, red.b)
        lay.ellipse(x0 + 8, 3, 8, 2.6, red.b)
        cv.merge(lay, ink=red.i, iw=MAJOR)
        cv.hgrad(x0, 2, 16, Hh - 6, [red.l, red.b, red.s], mode='atop')
        for k in range(3):
            cv.rect(x0 + 2 + k * 5, 5, 0.6, Hh - 12, red.d, mode='atop')
        cv.rect(x0, Hh - 6, 16, 2, chrome.b, ink=chrome.i, iw=DETAIL)
    # table
    cv.rect(18, 18, W - 36, 3, C('#f0ece4'), ink=C('#3a3a48'), iw=MAJOR)
    cv.rect(18, 21, W - 36, 1.2, chrome.b)
    cv.rect(W / 2 - 1.2, 22, 2.4, Hh - 26, chrome.b, ink=chrome.i, iw=DETAIL)
    cv.ellipse(W / 2, Hh - 3.5, 7, 1.6, chrome.b, ink=chrome.i, iw=DETAIL)
    cv.fill_poly([(24, 18), (28, 18), (27.5, 14), (24.5, 14)], C('#f4f0e8'), ink=C('#6a6070'), iw=0.4)
    cv.rect(38, 13.5, 3, 4.5, C('#c8302a'), ink=C('#3a0a10'), iw=0.4)
    cv.rect(42, 15, 3, 3, C('#c8ccd8'), ink=C('#3a3a48'), iw=0.4)
    ao(cv, 1, Hh, W - 2)


@prop('stool')
def p_stool(cv, W, Hh):
    red = M(C('#c0343a'))
    chrome = M(C('#c8ccd8'))
    cv.rect(7, 6, 2, Hh - 9, chrome.b, ink=chrome.i, iw=DETAIL)
    cv.rect(7, 6, 0.7, Hh - 9, chrome.h)
    cv.ellipse(8, Hh - 2.5, 5.5, 1.8, chrome.b, ink=chrome.i, iw=MAJOR)
    cv.ellipse(8, 5, 7, 3, red.b, ink=red.i, iw=MAJOR)
    cv.ellipse(8, 3.8, 6.4, 2.2, red.l)
    cv.rect(1, 6, 14, 1.4, chrome.b, ink=chrome.i, iw=DETAIL)
    cv.rect(4, Hh - 10, 8, 1, chrome.b)
    ao(cv, 2, Hh, 12)
