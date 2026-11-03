"""Backstreet Oath env v2 -- Ironworks: cold steel blue, soot-black brick, furnace orange, sparks and steam."""
import math

import numpy as np

from raster import C, mix, shade, light, ink_of, rng_of, value_noise
import kit
from kit import M, MAJOR, DETAIL, window, door, awning, cornice, parapet, brick_wall, drainpipe, cable, \
    neon_text, painted_text, poster, tag, concrete_panel, corrugated, ac_unit, fire_escape, cast_shadow_rect
from room import FACADE_BOTTOM as FB, H, light_pool, sun_rim, weeds
from common import facade, door_x, big_door, wall, shop_door, gable, lantern, fence, smokestack, chainlink

STEEL = '#6e7a8c'
SOOT_BRICK = '#6e4a42'


def furnace_window(R, x, y, w, h, heat=1.0):
    cv = R.cv
    pts = [(x, y + h), (x, y + w / 2)] + [(x + w / 2 + math.cos(a) * w / 2, y + w / 2 - math.sin(a) * w / 2)
                                          for a in np.linspace(math.pi, 0, 16)] + [(x + w, y + h)]
    cv.fill_poly([(px + (1.5 if px > x + w / 2 else -1.5), py - 1.5) for px, py in pts], C('#c8b8a0'),
                 ink=C('#1e1418'), iw=DETAIL)
    mk = cv.poly_mask(pts)
    cv.vgrad(x, y, w, h, [C('#ffd890'), C('#ff9a40'), C('#c8502a')], mk=mk, em=heat)
    for k in range(1, 4):
        cv.rect(x + w * k / 4 - 0.4, y, 0.8, h, C('#2a1e20'), em=0.0)
    cv.rect(x, y + h * 0.5, w, 0.8, C('#2a1e20'))
    kit.log(cv, {'type': 'window', 'rect': [round(x + 1, 1), round(y + w / 2 + 2, 1), round(w - 2, 1),
                                            round(h - w / 2 - 4, 1)], 'lit': True, 'kind': 'office'})


def hazard(cv, x, y, w, h, a=1.0):
    mk = cv.rect(x, y, w, h, C('#e8b830'), ink=C('#1e1810'), iw=DETAIL, a=a)
    xx = x - h
    while xx < x + w:
        cv.fill_poly([(xx, y + h), (xx + 3, y + h), (xx + 3 + h, y), (xx + h, y)], C('#1e1a1e'), a=a, mode='atop')
        xx += 6


@facade("yard_gate")
def f_yard_gate(R, x0, w, f):
    cv = R.cv
    # gate piers + arched truss sign across; yard beyond stays open (mid layer shows through above the wall)
    for px in (x0 + 10, x0 + w - 40):
        wall(cv, 'brick', px, 70, 30, FB - 70, SOOT_BRICK, seed=int(px))
        cv.rect(px - 3, 62, 36, 9, C('#9a9488'), ink=C('#1e1418'), iw=MAJOR)
        lantern(R, px + 15, 92, '#ffd890', 3)
        R.glow(px + 15, 92, 20, '#ffd890', 0.4, 'flame')
    ac = M(C('#3a4452'))
    pts_o = [(x0 + 40 + (w - 80) * t, 72 - math.sin(t * math.pi) * 22) for t in np.linspace(0, 1, 36)]
    cv.line(pts_o, 2.2, ac.b, ink=ac.i, iw=DETAIL)
    cv.line([(x0 + 40, 86), (x0 + w - 40, 86)], 2.0, ac.b, ink=ac.i, iw=DETAIL)
    for t in np.linspace(0.04, 0.96, 18):
        px, py = pts_o[int(t * 35)]
        cv.line([(px, py), (px, 86)], 0.7, ac.b)
    sw = min(w - 90, 200)
    cv.rect(x0 + w / 2 - sw / 2, 50, sw, 16, C('#2a3038'), ink=C('#0e1014'), iw=MAJOR)
    painted_text(cv, f.get('sign', 'IRONWORKS'), x0 + w / 2, 58.5, 7.5, C('#f0d8a8'), tracking=0.6)
    # the gate leaves: steel bars (closed one side, open the other) and a guard hut
    gm = M(C('#4a5462'))
    for k in range(int((w - 80) / 2 / 6)):
        bx = x0 + 40 + k * 6
        cv.rect(bx, 100, 1.6, FB - 100, gm.b, ink=gm.i, iw=0.4)
    cv.rect(x0 + 40, 100, (w - 80) / 2, 3, gm.b, ink=gm.i, iw=DETAIL)
    cv.rect(x0 + 40, 150, (w - 80) / 2, 2.4, gm.b, ink=gm.i, iw=DETAIL)
    cv.rect(x0 + 40, FB - 6, (w - 80) / 2, 3, gm.b, ink=gm.i, iw=DETAIL)
    hut_x = x0 + w / 2 + 24
    wall(cv, 'concrete', hut_x, 150, 52, FB - 150, '#8a8a84', seed=31)
    cv.rect(hut_x - 3, 144, 58, 7, C('#3a4452'), ink=C('#0e1014'), iw=MAJOR)
    window(cv, hut_x + 8, 160, 36, 20, lit=True, seed=4, frame='#9a9a94', interior='person', curtains=False, life='office',
           kind='grid')
    poster(cv, hut_x + 14, 186, 14, 18, seed=hash((R.id, 'sold')) % 999, kind='evict')
    cv.text('GREYLINE', 'cond', 2.8, hut_x + 21, 202, C('#5a6a7a'), 'mm')
    R.glow(hut_x + 26, 170, 40, '#ffd890', 0.3, 'none')
    R.light(x0 + w / 2, FB + 10, w * 0.5, 30, '#ffc070', 0.1)


@facade("rail_shed")
def f_rail_shed(R, x0, w, f):
    cv = R.cv
    top = 84
    corrugated(cv, x0, top, w, FB - top, C(STEEL), seed=hash((R.id, x0)) % 999, rust=0.6)
    # clerestory roof
    cv.fill_poly([(x0 - 4, top + 2), (x0 + w * 0.3, top - 22), (x0 + w * 0.7, top - 22), (x0 + w + 4, top + 2)],
                 C('#4a5260'), ink=C('#141820'), iw=MAJOR)
    cv.rect(x0 + w * 0.3, top - 34, w * 0.4, 13, C('#5a6474'), ink=C('#141820'), iw=MAJOR)
    for k in range(int(w * 0.4 / 14)):
        cv.rect(x0 + w * 0.3 + 4 + k * 14, top - 31, 9, 7, C('#ffb060'), em=0.9)
    cv.line([(x0 - 4, top + 2), (x0 + w * 0.3, top - 22)], 0.8, C('#ffb070'), a=0.6)
    # big open bay with tracks going in and a furnace-lit interior
    bx, bw = x0 + w * 0.5 - 50, 100
    cv.rect(bx - 4, top + 26, bw + 8, FB - top - 26, C('#2a2e36'), ink=C('#0e0a10'), iw=MAJOR)
    cv.vgrad(bx, top + 30, bw, FB - top - 30, [C('#1a1418'), C('#3a2420'), C('#8a4a2a')], em=0.7)
    cv.radial(bx + bw * 0.6, FB - 20, 40, 30, C('#ff8a3a'), a=0.4, mode='add')
    for off in (-14, 14):
        cv.line([(bx + bw / 2 + off * 2, FB), (bx + bw / 2 + off * 0.8, top + 70)], 0.8, C('#8a8e9a'), a=0.6)
    # a locomotive nose in the doorway
    cv.fill_poly([(bx + 20, FB - 4), (bx + 20, FB - 44), (bx + 34, FB - 52), (bx + 80, FB - 52), (bx + 80, FB - 4)],
                 C('#c84a2a'), ink=C('#2a0e0a'), iw=MAJOR, em=0.3)
    cv.rect(bx + 30, FB - 44, 16, 10, C('#ffd890'), ink=C('#2a0e0a'), iw=DETAIL, em=1.0)
    hazard(cv, bx + 20, FB - 14, 60, 4)
    R.glow(bx + bw / 2, FB - 30, 60, '#ff9a40', 0.4, 'flame')
    painted_text(cv, 'SHED 3', x0 + 50, top + 20, 8, C('#e8dcc0'), shadow=False, fade=0.35, seed=3)
    for k in range(2):
        window(cv, x0 + 30 + k * (w - 90), top + 40, 26, 30, lit=k == 1, seed=33 + k, frame='#8a8e96', kind='grid', life='office',
               glass=[C('#ffd890'), C('#ff9a50'), C('#c85a2a')])
    tag(cv, x0 + w - 70, FB - 20, 'YARD', C('#f0c040'), size=6, seed=4)
    R.light(bx + bw / 2, FB + 10, 70, 30, '#ff9040', 0.16)
    R.ambient.append({"type": "steam", "x": float(x0 + w * 0.2), "y": float(top - 2), "rate": 0.5})


@facade("chainlink_yard")
def f_chainlink_yard(R, x0, w, f):
    cv = R.cv
    rs = R.rng('scrap', x0)
    # scrap heaps + stacked I-beams behind the fence (yard is open; sky/mid show above)
    for k in range(int(w / 110) + 1):
        sx = x0 + 20 + k * 110 + rs.uniform(-10, 10)
        pts = [(sx, FB)]
        for j in range(9):
            pts.append((sx + j * 10, FB - 26 - 18 * math.sin(j / 8 * math.pi) - rs.uniform(-4, 4)))
        pts.append((sx + 80, FB))
        cv.fill_poly(pts, C('#5a5a64'), ink=C('#1a161e'), iw=MAJOR)
        for j in range(12):
            px, py = sx + rs.uniform(6, 74), FB - rs.uniform(4, 34)
            c = C(rs.choice(['#8a5a3a', '#7a8494', '#a8643a', '#4a4a54']))
            cv.line([(px, py), (px + rs.uniform(-8, 8), py + rs.uniform(-3, 3))], rs.uniform(1, 2.4), c,
                    ink=C('#1a161e'), iw=0.3, mode='atop')
    bx = x0 + w * 0.5
    for j in range(4):
        cv.rect(bx - 30 + j * 3, FB - 14 - j * 6, 70, 5, C('#8a7060'), ink=C('#1e1418'), iw=DETAIL)
        cv.rect(bx - 30 + j * 3, FB - 14 - j * 6, 70, 1, C('#ffb070'), a=0.5)
    fence(cv, x0, 130, w, FB, post='#5a6070')
    cv.rect(x0 + w * 0.2, 150, 34, 16, C('#f4f0e8'), ink=C('#2a2430'), iw=DETAIL)
    cv.text('DANGER', 'cond', 4.2, x0 + w * 0.2 + 17, 155, C('#c83a2a'), 'mm')
    cv.text('SCRAP YARD', 'cond', 3.2, x0 + w * 0.2 + 17, 161, C('#2a2430'), 'mm')
    for k in range(int(w / 10)):
        weeds(R, x0 + 4 + k * 10, FB + 0.5, 3, seed=7000 + k, col='#5a6a3a')


@facade("brick_factory")
def f_brick_factory(R, x0, w, f):
    cv = R.cv
    top = 40
    wall(cv, 'brick', x0, top, w, FB - top, SOOT_BRICK, seed=hash((R.id, x0)) % 999, soot=0.5)
    cv.rect(x0 - 2, top - 6, w + 4, 8, C('#4a3a38'), ink=C('#140c10'), iw=MAJOR)
    # saw-tooth roof
    for k in range(int(w / 50)):
        sx = x0 + k * 50
        cv.fill_poly([(sx, top - 6), (sx + 34, top - 26), (sx + 34, top - 6)], C('#4a5260'), ink=C('#141820'),
                     iw=DETAIL)
        cv.rect(sx + 30, top - 26, 4, 20, C('#ffb060'), em=0.8)
    smokestack(R, x0 + w - 40, -40, top - 6, 18, '#6a4038')
    # tall arched windows glowing from the works inside
    n = int((w - 40) / 46)
    for k in range(n):
        wx = x0 + 24 + k * (w - 48) / n
        furnace_window(R, wx, top + 26, 26, 96, heat=0.9 if k % 3 else 0.6)
    painted_text(cv, 'BELLWETHER IRON & STEEL CO.', x0 + w / 2, top + 12, 7, C('#e8dcc0'), shadow=False, fade=0.4,
                 seed=8)
    # loading door + pipes + greyline notice
    big_door(cv, x0 + w / 2 - 30, FB, 60, 60, '#5a6270', kind='roller', seed=9)
    for k in range(3):
        y = top + 140 + k * 5
        cv.rect(x0, y, w, 2.2, C('#7a8494'), ink=C('#141820'), iw=0.4)
    poster(cv, x0 + 30, FB - 40, 16, 22, seed=hash((R.id, 'gl')) % 999, kind='evict')
    cv.rect(x0 + w / 2 + 50, FB - 50, 44, 18, C('#e8e8ec'), ink=C('#1e2228'), iw=DETAIL)
    cv.text('SOLD', 'sign', 5, x0 + w / 2 + 72, FB - 45, C('#c8302a'), 'mm')
    cv.text('GREYLINE DEV.', 'cond', 3.2, x0 + w / 2 + 72, FB - 38, C('#3a4a5a'), 'mm')
    R.glow(x0 + w / 2, top + 80, w * 0.5, '#ff9a40', 0.25, 'flame')
    R.light(x0 + w / 2, FB + 10, w * 0.6, 30, '#ff9040', 0.1)
    R.ambient.append({"type": "sparks", "x": float(x0 + w * 0.3), "y": float(top + 100), "rate": 0.3})


@facade("canteen")
def f_canteen(R, x0, w, f):
    cv = R.cv
    top = 110
    wall(cv, 'brick', x0, top, w, FB - top, '#8a5a48', seed=1101)
    cv.rect(x0 - 3, top - 8, w + 6, 9, C('#3a4452'), ink=C('#0e1014'), iw=MAJOR)
    dx = door_x(R, x0, w)
    sm = M(C('#2a5a3a'))
    cv.rect(x0 + 20, top + 6, w - 40, 18, sm.b, ink=sm.i, iw=MAJOR)
    cv.vgrad(x0 + 22, top + 8, w - 44, 14, [light(sm.b, 1.2), sm.b], em=0.8)
    painted_text(cv, f.get('sign', 'CANTEEN'), x0 + w / 2, top + 15.5, 9, C('#f8e8b0'), tracking=0.5, em=1.0)
    for k, wx in enumerate((x0 + 20, x0 + w - 80)):
        if abs(wx + 30 - dx) < 40:
            continue
        window(cv, wx, top + 34, 60, 34, lit=True, seed=1100 + k, frame='#d8d0c0', kind='grid', interior='person', life='office',
               curtains=False)
    shop_door(R, dx, 24, 56, '#2a5a3a')
    cv.rect(x0 + w - 24, top - 22, 10, 14, C('#7a8494'), ink=C('#141820'), iw=DETAIL)
    R.ambient.append({"type": "steam", "x": float(x0 + w - 19), "y": float(top - 22), "rate": 0.7})
    community = poster(cv, x0 + w / 2 + 34, FB - 44, 14, 18, seed=1102, kind='plain')
    cv.text('STRIKE?', 'cond', 3.2, x0 + w / 2 + 41, FB - 38, C('#c83a2a'), 'mm')
    R.glow(x0 + w / 2, top + 50, w * 0.45, '#ffd890', 0.3, 'none')
    light_pool(R, x0 + w / 2, FB + 8, w * 0.4, 10, '#ffd890', a=0.18)
    R.light(x0 + w / 2, FB + 14, w * 0.5, 30, '#ffc070', 0.16)


@facade("switch_house")
def f_switch_house(R, x0, w, f):
    cv = R.cv
    hx, hw = x0 + w / 2 - 70, 140
    top = 60
    wall(cv, 'brick', hx, top + 40, hw, FB - top - 40, '#7a4a3e', seed=1201)
    # glazed operating floor upstairs
    cv.rect(hx - 4, top, hw + 8, 44, C('#c8c0b0'), ink=C('#1e1418'), iw=MAJOR)
    for k in range(6):
        window(cv, hx + 2 + k * 23, top + 6, 20, 30, lit=True, seed=1200 + k, frame='#c8c0b0', sill=False, life='office',
               lintel=False, interior='blank', curtains=False, mull=False)
    cv.rect(hx + 10, top + 26, hw - 20, 10, C('#3a3036'), em=0.6)
    for k in range(14):
        cv.rect(hx + 14 + k * 8.5, top + 18, 1.4, 9, C('#c83a2a') if k % 3 == 0 else C('#c8ccd8'), em=0.8)
    cv.fill_poly([(hx - 8, top), (hx + hw / 2, top - 22), (hx + hw + 8, top)], C('#3a4452'), ink=C('#0e1014'),
                 iw=MAJOR)
    cv.rect(hx + 20, top + 46, hw - 40, 14, C('#f4f0e4'), ink=C('#2a2430'), iw=MAJOR)
    painted_text(cv, f.get('sign', 'SWITCH HOUSE'), hx + hw / 2, top + 53.5, 6.5, C('#2a2430'), shadow=False)
    dx = door_x(R, x0, w)
    door(cv, dx - 11, FB, 22, 50, C('#2e4a5a'), lit=True, seed=1202, frame='#c8c0b0', step=False)
    # external stair to the upper floor
    sm = M(C('#3a4452'))
    cv.line([(hx + hw + 2, FB), (hx + hw + 30, top + 44)], 1.6, sm.b)
    for k in range(14):
        t = k / 14
        cv.rect(hx + hw + 2 + 28 * t - 1, FB - (FB - top - 44) * t, 6, 0.8, sm.b)
    cv.line([(hx + hw + 6, FB - 12), (hx + hw + 34, top + 32)], 0.6, sm.b)
    # signal mast
    mx = x0 + 20
    cv.rect(mx, 90, 2, FB - 90, C('#2a2a34'))
    for k, c in enumerate(('#ff4a3a', '#3ad870')):
        cv.ellipse(mx + 1, 96 + k * 8, 2.6, 2.6, C('#141018'))
        cv.ellipse(mx + 1, 96 + k * 8, 1.8, 1.8, C(c), em=1.0)
        R.glow(mx + 1, 96 + k * 8, 10, c, 0.4, 'none')
    R.glow(hx + hw / 2, top + 22, 70, '#ffe0a0', 0.3, 'none')
    R.light(dx, FB + 10, 50, 26, '#ffd090', 0.12)


@facade("foundry_wall")
def f_foundry_wall(R, x0, w, f):
    cv = R.cv
    wall(cv, 'brick', x0, 0, w, FB, SOOT_BRICK, seed=1301, soot=0.55)
    # crane rail at the top + steel columns
    cv.rect(x0, 18, w, 10, C('#4a5260'), ink=C('#141820'), iw=MAJOR)
    hazard(cv, x0, 26, w, 3, a=0.8)
    for k in range(int(w / 120) + 1):
        cx = x0 + 40 + k * 120
        cv.rect(cx - 5, 28, 10, FB - 28, C('#5a6474'), ink=C('#141820'), iw=MAJOR)
        cv.hgrad(cx - 5, 28, 10, FB - 28, [C('#8a96a8'), C('#5a6474'), C('#3a4250')], mode='atop')
    # clerestory windows (cold daylight)
    for k in range(int(w / 60)):
        wx = x0 + 10 + k * 60
        cv.rect(wx, 40, 40, 24, C('#a8b8c8'), ink=C('#1e2228'), iw=MAJOR, em=0.7)
        for j in range(1, 4):
            cv.rect(wx + j * 10 - 0.4, 40, 0.8, 24, C('#3a4250'))
    # gauges, pipes, valve wheels
    for k in range(4):
        y = 110 + k * 7
        cv.rect(x0, y, w, 3, C('#7a6a5a') if k % 2 else C('#5a6474'), ink=C('#141820'), iw=0.4)
    for k in range(3):
        gx = x0 + 80 + k * 130
        cv.ellipse(gx, 150, 7, 7, C('#e8e4d8'), ink=C('#1e1820'), iw=MAJOR)
        cv.line([(gx, 150), (gx + 4, 146)], 0.6, C('#c83a2a'))
        cv.ellipse(gx + 30, 160, 6, 6, None, ink=C('#c83a2a'), iw=1.2)
    poster(cv, x0 + 30, 160, 16, 22, seed=1302, kind='evict')
    tag(cv, x0 + 200, 180, 'OTTO', C('#f0c040'), size=7, seed=5, a=0.7)
    R.light(x0 + w / 2, 280, w, 70, '#a8b8d8', 0.04)


@facade("furnace")
def f_furnace(R, x0, w, f):
    cv = R.cv
    wall(cv, 'brick', x0, 0, w, FB, '#5a3a36', seed=1401, soot=0.6)
    cx = x0 + w / 2
    # furnace body: riveted steel shell with a glowing mouth
    sm = M(C('#4a4e5a'))
    cv.fill_poly([(cx - 150, FB), (cx - 120, 40), (cx + 120, 40), (cx + 150, FB)], sm.b, ink=sm.i, iw=MAJOR)
    cv.hgrad(cx - 150, 40, 300, FB - 40, [sm.l, sm.b, sm.s, sm.d], mode='atop')
    for yy in range(56, int(FB), 22):
        cv.rect(cx - 140, yy, 280, 1.2, sm.d, mode='atop')
        for xx in range(int(cx - 130), int(cx + 130), 10):
            cv.ellipse(xx, yy + 3, 0.6, 0.6, sm.h, mode='atop')
    mouth = [(cx - 70, FB - 10), (cx - 70, 120)] + [(cx + math.cos(a) * 70, 120 - math.sin(a) * 40)
                                                       for a in np.linspace(math.pi, 0, 20)] + [(cx + 70, FB - 10)]
    cv.fill_poly([(px * 1.0, py) for px, py in mouth], C('#2a1a18'), ink=C('#0e0808'), iw=MAJOR)
    mk = cv.poly_mask([(px + (-6 if px < cx else 6) * 0, py + 6) for px, py in mouth])
    cv.vgrad(cx - 70, 80, 140, FB - 90, [C('#fff4c0'), C('#ffc060'), C('#ff7a2a'), C('#c83a1a')], mk=mk, em=1.0)
    rs = R.rng('molten')
    for _ in range(40):
        px, py = rs.uniform(cx - 60, cx + 60), rs.uniform(110, FB - 20)
        cv.ellipse(px, py, rs.uniform(2, 6), rs.uniform(1, 3), C('#fff8d8'), a=0.5, em=1.0, mode='atop')
    cv.radial(cx, 160, 150, 110, C('#ff8a30'), a=0.35, mode='add')
    # pouring ladle + stream
    lx = cx + 96
    cv.fill_poly([(lx - 20, 60), (lx + 20, 60), (lx + 16, 92), (lx - 16, 92)], C('#3a3e48'), ink=C('#0e0a10'),
                 iw=MAJOR)
    cv.ellipse(lx, 60, 20, 4, C('#ffb040'), em=1.0)
    cv.line([(lx - 18, 62), (lx - 30, 70), (lx - 34, 120)], 2.0, C('#ffd060'), em=1.0)
    cv.line([(lx, 20), (lx, 56)], 1.0, C('#2a2a34'))
    hazard(cv, cx - 150, FB - 8, 300, 4)
    R.glow(cx, 150, 160, '#ff8a30', 0.75, 'flame')
    R.glow(cx, 150, 220, '#ff7a20', 0.2, 'flame', front=True)
    R.glow(lx - 30, 90, 40, '#ffc050', 0.5, 'flame')
    R.light(cx, FB + 30, 200, 90, '#ff8a3a', 0.45)
    for k in range(3):
        R.ambient.append({"type": "sparks", "x": float(cx - 50 + k * 50), "y": float(FB - 30), "rate": 0.8})
    R.ambient.append({"type": "embers", "x": float(cx), "y": 100.0, "w": 200})
    R.ambient.append({"type": "smoke", "x": float(cx - 60), "y": 40.0, "rate": 0.4})


@facade("crane_bay")
def f_crane_bay(R, x0, w, f):
    cv = R.cv
    wall(cv, 'corrugated', x0, 0, w, FB, '#5a6474', seed=1501)
    # overhead gantry crane with hook and chains
    gm = M(C('#d8a830'))
    cv.rect(x0, 30, w, 14, gm.b, ink=gm.i, iw=MAJOR)
    hazard(cv, x0, 44, w, 3)
    for k in range(int(w / 16)):
        cv.line([(x0 + k * 16, 30), (x0 + k * 16 + 8, 44)], 0.8, gm.s)
    tx = x0 + w * 0.4
    cv.rect(tx - 14, 44, 28, 16, C('#3a4452'), ink=C('#0e1014'), iw=MAJOR)
    for off in (-4, 4):
        cv.line([(tx + off, 60), (tx + off, 130)], 0.6, C('#2a2a34'))
    cv.fill_poly([(tx - 8, 130), (tx + 8, 130), (tx + 6, 140), (tx - 6, 140)], C('#3a3e48'), ink=C('#0e0a10'),
                 iw=DETAIL)
    cv.line([(tx, 140), (tx, 150), (tx + 5, 154), (tx + 6, 148)], 1.4, C('#8a8e9a'), ink=C('#141018'), iw=0.4)
    # stacked steel plate, coils and chains on the wall
    for j in range(5):
        cv.rect(x0 + 40 + j * 2, FB - 10 - j * 7, 120, 6, C('#7a8494'), ink=C('#141820'), iw=DETAIL)
        cv.rect(x0 + 40 + j * 2, FB - 10 - j * 7, 120, 1, C('#c8d0e0'), a=0.6)
    for k in range(3):
        cx = x0 + w - 150 + k * 40
        cv.ellipse(cx, FB - 18, 17, 18, C('#8a7060'), ink=C('#1e1418'), iw=MAJOR)
        cv.ellipse(cx, FB - 18, 6, 6, C('#2a2026'))
        for r in (9, 12, 15):
            cv.ellipse(cx, FB - 18, r, r, None, ink=C('#6a5244'), iw=0.4)
    for k in range(5):
        cv.line([(x0 + 200 + k * 20, 70), (x0 + 205 + k * 20, 130)], 1.0, C('#5a5e6a'))
    cv.rect(x0 + w - 80, 70, 60, 24, C('#2a3038'), ink=C('#0e1014'), iw=MAJOR)
    painted_text(cv, 'BAY 2', x0 + w - 50, 82, 8, C('#f0c040'), shadow=False)
    R.light(x0 + w / 2, 280, w, 70, '#a8b8d8', 0.05)
