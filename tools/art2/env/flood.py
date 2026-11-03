"""Backstreet Oath env v2 -- Floodgate (rain, blue-green, sodium lamps) and the Warehouse district."""
import math

import numpy as np

from raster import C, mix, shade, light, ink_of, rng_of
import kit
from kit import M, MAJOR, DETAIL, window, door, awning, cornice, parapet, brick_wall, drainpipe, cable, \
    neon_text, painted_text, poster, tag, concrete_panel, corrugated, fire_escape
from room import FACADE_BOTTOM as FB, H, INT_WALL_BOTTOM as WB, light_pool, weeds
from common import facade, door_x, big_door, wall, shop_door, lantern, fence, storefront, shop_building, chainlink
from grounds2 import canal_water
from iron import hazard

CONT = ['#a84a3a', '#3a6a8a', '#c89a3a', '#4a7a5a', '#8a8a8a', '#6a4a7a']


def greyline_logo(cv, cx, cy, s=1.0, col='#d8dce0', bg='#2a3038'):
    cv.rect(cx - 24 * s, cy - 7 * s, 48 * s, 14 * s, C(bg), ink=C('#0e1014'), iw=MAJOR)
    cv.fill_poly([(cx - 21 * s, cy + 4 * s), (cx - 14 * s, cy - 4 * s), (cx - 7 * s, cy + 4 * s)], C(col))
    cv.text('GREYLINE', 'cond', 6 * s, cx + 4 * s, cy, C(col), 'mm', tracking=0.6)


def wet_streaks(R, x, y, w, h, a=0.25):
    cv = R.cv
    rs = R.rng('wet', x, y)
    for _ in range(int(w / 6)):
        sx = rs.uniform(x, x + w)
        ln = rs.uniform(h * 0.2, h * 0.7)
        sy = rs.uniform(y, y + h - ln)
        cv.vgrad(sx, sy, rs.uniform(0.6, 1.4), ln, [C('#c8e0e8', 0), C('#c8e0e8', 150), C('#c8e0e8', 0)], a=a,
                 mode='atop')


def container(cv, x, yb, w, h, col, label=None, doors=True, seed=0):
    m = M(C(col))
    cv.rect(x, yb - h, w, h, m.b, ink=m.i, iw=MAJOR)
    xx = x + 2
    while xx < x + w - 1:
        cv.rect(xx, yb - h + 1.5, 0.8, h - 3, m.s, mode='atop')
        cv.rect(xx + 0.8, yb - h + 1.5, 0.5, h - 3, m.l, mode='atop', a=0.6)
        xx += 3.2
    cv.rect(x, yb - h, w, 1.2, m.h, mode='atop')
    cv.rect(x, yb - 2, w, 2, m.d, mode='atop')
    if doors:
        cv.rect(x + w - 26, yb - h + 2, 24, h - 4, m.b, ink=m.d, iw=DETAIL)
        for k in range(4):
            cv.rect(x + w - 24 + k * 6, yb - h + 3, 0.7, h - 6, C('#2a2a30'))
    if label:
        cv.text(label, 'cond', h * 0.26, x + (w - 26) / 2, yb - h / 2, light(m.b, 1.8), 'mm', tracking=0.8)
    kit.brushed_metal(cv, x, yb - h, w, h, m.b, seed, a=0.08)
    kit.rust_bloom(cv, x, yb - h, w, h, seed, a=0.32, edge=3.0,
                   rivets=[(x + w - 24 + k * 6, yb - h + 4) for k in range(4)] if doors else None)
    kit.weather(cv, x, yb - h, w, h, seed, soot=0.25, streak=True)


@facade("bridge_rail")
def f_bridge_rail(R, x0, w, f):
    cv = R.cv
    # river far below/behind, steel truss bridge girders across the top, concrete parapet at the walk band edge
    canal_water(R, x0, 150, w, FB - 150, seed=31, deep='#1a3038', mid='#2e4a52', light_c='#6a8a8e')
    tm = M(C('#3e5058'))
    cv.rect(x0, 30, w, 8, tm.b, ink=tm.i, iw=MAJOR)
    cv.rect(x0, FB - 34, w, 6, tm.b, ink=tm.i, iw=MAJOR)
    xx = x0
    k = 0
    while xx < x0 + w:
        cv.rect(xx, 30, 4, FB - 60, tm.b, ink=tm.i, iw=DETAIL)
        if k % 2 == 0:
            cv.line([(xx + 2, 38), (xx + 82, FB - 34)], 2.0, tm.b, ink=tm.i, iw=DETAIL)
        else:
            cv.line([(xx + 2, FB - 34), (xx + 82, 38)], 2.0, tm.b, ink=tm.i, iw=DETAIL)
        for yy in (40, 100, 160):
            cv.ellipse(xx + 2, yy, 0.8, 0.8, tm.h)
        xx += 80
        k += 1
    cv.rect(x0, 30, w, 1, C('#a8d0d8'), a=0.6)
    # concrete parapet with lamp standards (props) and flood-level marks
    concrete_panel(cv, x0, FB - 20, w, 20, C('#7a8484'), seed=32, panel=40, ties=False)
    cv.rect(x0, FB - 22, w, 3, C('#9aa4a4'), ink=C('#1e2428'), iw=DETAIL)
    for k in range(int(w / 300) + 1):
        mx = x0 + 150 + k * 300
        cv.rect(mx, FB - 19, 14, 16, C('#e8e4d8'), ink=C('#1e2428'), iw=DETAIL)
        for j in range(4):
            cv.rect(mx + 1, FB - 17 + j * 4, 6 if j % 2 else 10, 0.7, C('#2a3038'))
    wet_streaks(R, x0, FB - 20, w, 20)
    tag(cv, x0 + w * 0.3, FB - 10, 'RATS', C('#c8c8d0'), size=6, seed=31, a=0.6)
    poster(cv, x0 + w * 0.6, FB - 19, 12, 15, seed=3101, kind='missing')
    R.ambient.append({"type": "water_shimmer", "x": float(x0), "y": 150.0, "w": float(w), "h": 40.0})


@facade("pump_station")
def f_pump_station(R, x0, w, f):
    cv = R.cv
    top = 50
    wall(cv, 'brick', x0, top, w, FB - top, '#6a5048', seed=3201, soot=0.4)
    cv.fill_poly([(x0 - 4, top + 2), (x0 + w / 2, top - 30), (x0 + w + 4, top + 2)], C('#3a4a50'), ink=C('#0e1418'),
                 iw=MAJOR)
    for k in range(5):
        wx = x0 + 26 + k * (w - 70) / 4
        window(cv, wx, top + 20, 22, 46, lit=k % 2 == 1, seed=3200 + k, frame='#c8c0b0', kind='grid',
               glass=[C('#f0f4c8'), C('#c8d890'), C('#8aa070')])
    sm = M(C('#2a4a5a'))
    cv.rect(x0 + 40, top + 76, w - 80, 18, sm.b, ink=sm.i, iw=MAJOR)
    painted_text(cv, f.get('sign', 'PUMP STATION'), x0 + w / 2, top + 85.5, 9, C('#e8f0e8'), tracking=0.6)
    # huge outflow pipes + valve wheel
    for k in range(2):
        py = FB - 34 + k * 0
        px = x0 + 40 + k * (w - 140)
        cv.rect(px, FB - 58, 60, 40, C('#4a5a60'), ink=C('#0e1418'), iw=MAJOR)
        cv.ellipse(px + 60, FB - 38, 8, 20, C('#5a6a70'), ink=C('#0e1418'), iw=MAJOR)
        cv.ellipse(px + 60, FB - 38, 5, 14, C('#141c20'))
        cv.hgrad(px, FB - 58, 60, 40, [C('#ffffff', 60), C('#ffffff', 0)], mode='atop')
    cv.ellipse(x0 + w / 2, FB - 40, 12, 12, None, ink=C('#c83a2a'), iw=2.0)
    for a in np.linspace(0, math.pi, 4):
        cv.line([(x0 + w / 2 - math.cos(a) * 12, FB - 40 - math.sin(a) * 12),
                 (x0 + w / 2 + math.cos(a) * 12, FB - 40 + math.sin(a) * 12)], 1.0, C('#c83a2a'))
    # flood level gauge
    gx = x0 + w - 30
    cv.rect(gx, FB - 100, 10, 100, C('#e8e4d8'), ink=C('#1e2428'), iw=DETAIL)
    for k in range(10):
        cv.rect(gx, FB - 100 + k * 10, 6 if k % 2 else 10, 1, C('#c83a2a'))
    cv.rect(gx, FB - 46, 10, 46, C('#3a7a8a'), a=0.5)
    wet_streaks(R, x0, top, w, FB - top, a=0.18)
    R.glow(x0 + w / 2, top + 40, w * 0.4, '#e8f0c0', 0.2, 'fluor')
    R.ambient.append({"type": "drip", "x": float(x0 + 100), "y": float(FB - 20), "rate": 0.6})


@facade("bait_shop")
def f_bait_shop(R, x0, w, f):
    cv = R.cv
    top = 90
    wall(cv, 'clap', x0, top, w, FB - top, '#5a7a7a', seed=3301)
    cv.fill_poly([(x0 - 6, top + 2), (x0 + w / 2, top - 26), (x0 + w + 6, top + 2)], C('#4a3a3a'), ink=C('#140c10'),
                 iw=MAJOR)
    dx = door_x(R, x0, w)
    sm = M(C('#e8e0c8'))
    cv.rect(x0 + 20, top + 8, w - 40, 18, sm.b, ink=sm.i, iw=MAJOR)
    painted_text(cv, f.get('sign', 'BAIT & TACKLE'), x0 + w / 2, top + 17.5, 9, C('#2e5a6a'), tracking=0.5)
    storefront(R, x0 + 14, top + 36, dx - 18 - x0 - 14, FB - top - 42, 'bait', seed=3302)
    if x0 + w - 14 - (dx + 18) > 12:
        storefront(R, dx + 18, top + 36, x0 + w - 14 - (dx + 18), FB - top - 42, 'bait', seed=3303)
    shop_door(R, dx, 22, 52, '#3a5a5a')
    awning(cv, x0 + 10, top + 30, w - 20, 6, C('#2e5a6a'), C('#e8e0c8'), stripe=6, valance=2.5)
    # hanging buoys + nets on the wall
    for k, c in enumerate(('#e84a3a', '#f8d040', '#f4f0e8', '#e84a3a')):
        bx = x0 + 30 + k * (w - 60) / 3
        cv.line([(bx, top + 2), (bx, top + 8)], 0.4, C('#2a2026'))
        cv.ellipse(bx, top + 4, 2.6, 3.4, C(c), ink=C('#1a1014'), iw=DETAIL)
    lantern(R, x0 + 14, top + 34, '#ffd890', 2.6)
    R.glow(x0 + 14, top + 34, 18, '#ffd890', 0.45, 'flame')
    poster(cv, x0 + w - 30, top + 40, 12, 16, seed=3304, kind='missing')
    wet_streaks(R, x0, top, w, FB - top)
    R.light(dx, FB + 12, 60, 30, '#ffd890', 0.18)


@facade("floodgate_wall")
def f_floodgate_wall(R, x0, w, f):
    cv = R.cv
    concrete_panel(cv, x0, 40, w, FB - 40, C('#7a8686'), seed=3401, panel=52)
    cv.rect(x0, 34, w, 8, C('#9aa4a4'), ink=C('#1e2428'), iw=MAJOR)
    # steel sluice gates with rack gears
    for k in range(int(w / 180)):
        gx = x0 + 30 + k * 180
        gm = M(C('#4a5a62'))
        cv.rect(gx, 70, 120, FB - 70, gm.b, ink=gm.i, iw=MAJOR)
        for yy in range(78, int(FB), 14):
            cv.rect(gx + 2, yy, 116, 1.4, gm.d)
            for xx in range(int(gx + 6), int(gx + 118), 12):
                cv.ellipse(xx, yy + 5, 0.6, 0.6, gm.h)
        cv.rect(gx + 56, 20, 8, 52, C('#3a4248'), ink=C('#0e1014'), iw=DETAIL)
        for j in range(8):
            cv.rect(gx + 54, 24 + j * 6, 2, 2, C('#8a9298'))
        hazard(cv, gx, 62, 120, 5)
        # water line staining
        cv.vgrad(gx, FB - 60, 120, 60, [C('#2a4a3a', 0), C('#2a4a3a', 140)], mode='atop')
    for k in range(int(w / 260) + 1):
        sx = x0 + 100 + k * 260
        cv.rect(sx, 46, 50, 16, C('#f8d040'), ink=C('#2a2010'), iw=DETAIL)
        cv.text('FLOOD GATE', 'cond', 4.4, sx + 25, 51.5, C('#2a2010'), 'mm')
        cv.text('KEEP CLEAR', 'cond', 3.6, sx + 25, 57.5, C('#2a2010'), 'mm')
    # depth markers
    for k in range(int(w / 140) + 1):
        mx = x0 + 10 + k * 140
        for j in range(6):
            cv.rect(mx, FB - 10 - j * 16, 8, 1.2, C('#e8e4d8'))
            cv.text(str(j + 1), 'cond', 3.2, mx + 12, FB - 10 - j * 16, C('#e8e4d8'), 'mm', a=0.8)
    wet_streaks(R, x0, 40, w, FB - 40, a=0.2)
    tag(cv, x0 + w * 0.5, FB - 20, 'RATS', C('#e84a3a'), size=7, seed=34)
    R.ambient.append({"type": "drip", "x": float(x0 + w * 0.3), "y": 70.0, "rate": 0.7})
    R.ambient.append({"type": "drip", "x": float(x0 + w * 0.7), "y": 70.0, "rate": 0.5})


@facade("container_stack")
def f_container_stack(R, x0, w, f):
    cv = R.cv
    rs = R.rng('cstack', x0)
    xx = x0
    while xx < x0 + w - 40:
        cw = rs.choice([120, 120, 80])
        if xx + cw > x0 + w:
            cw = x0 + w - xx
        n = rs.randint(2, 4)
        for j in range(n):
            lab = rs.choice([None, None, 'GREYLINE', 'BELLWETHER', 'RIVERLINE'])
            container(cv, xx + (j % 2) * 4, FB - j * 44, cw - 6, 44, rs.choice(CONT), label=lab,
                      seed=int(xx) + j)
        xx += cw
    for k in range(int(w / 240) + 1):
        greyline_logo(cv, x0 + 80 + k * 240, FB - 70, 1.0)
    wet_streaks(R, x0, 40, w, FB - 40, a=0.2)
    poster(cv, x0 + w * 0.4, FB - 30, 12, 16, seed=3501, kind='missing')
    R.ambient.append({"type": "drip", "x": float(x0 + w * 0.5), "y": float(FB - 132), "rate": 0.5})


@facade("warehouse_fence")
def f_warehouse_fence(R, x0, w, f):
    cv = R.cv
    # Greyline warehouse behind a high fence; the big sign is the story beat
    wall(cv, 'corrugated', x0, 60, w, FB - 60, '#5a6870', seed=3601)
    cv.rect(x0 - 2, 52, w + 4, 10, C('#3a4448'), ink=C('#0e1014'), iw=MAJOR)
    for k in range(int(w / 90)):
        cv.rect(x0 + 20 + k * 90, 74, 50, 14, C('#c8f0d8'), ink=C('#141c18'), iw=DETAIL, em=0.9)
    big_door(cv, x0 + w / 2 - 50, FB, 100, 90, '#7a8a90', kind='roller', seed=36)
    hazard(cv, x0 + w / 2 - 50, FB - 94, 100, 4)
    sign = f.get('sign', 'GREYLINE DEVELOPMENT - PRIVATE PROPERTY')
    sx, sw = x0 + 40, min(w - 80, 360)
    cv.rect(sx, 100, sw, 30, C('#e8eaec'), ink=C('#0e1014'), iw=MAJOR)
    greyline_logo(cv, sx + 34, 115, 0.9)
    parts = sign.split(' - ')
    cv.text(parts[0], 'sign', 7, sx + sw / 2 + 30, 110, C('#2a3038'), 'mm')
    if len(parts) > 1:
        cv.text(parts[1], 'cond', 6, sx + sw / 2 + 30, 122, C('#c8302a'), 'mm', tracking=0.8)
    fence(cv, x0, 130, w, FB, post='#4a5258', col='#9aa4ac')
    cv.rect(x0 + w - 120, 160, 40, 20, C('#f4f0e8'), ink=C('#2a2430'), iw=DETAIL)
    cv.text('NO ENTRY', 'cond', 4.4, x0 + w - 100, 166, C('#c8302a'), 'mm')
    cv.text('SECURITY PATROLS', 'cond', 3, x0 + w - 100, 173, C('#2a2430'), 'mm')
    wet_streaks(R, x0, 60, w, FB - 60, a=0.18)
    R.glow(x0 + w / 2, 80, w * 0.5, '#c8f0d8', 0.2, 'fluor')


# ----------------------------------------------------------------------------- Warehouse district
@facade("loading_bay")
def f_loading_bay(R, x0, w, f):
    cv = R.cv
    wall(cv, 'corrugated', x0, 50, w, FB - 50, '#5e6a68', seed=3701)
    cv.rect(x0 - 2, 42, w + 4, 10, C('#343c3e'), ink=C('#0e1014'), iw=MAJOR)
    # dock doors with levellers, bumpers and lit interiors
    n = int(w / 220)
    for k in range(n):
        dxk = x0 + 50 + k * 220
        open_ = k % 2 == 0
        cv.rect(dxk - 4, FB - 96, 108, 96, C('#2a3032'), ink=C('#0e1014'), iw=MAJOR)
        if open_:
            cv.vgrad(dxk, FB - 92, 100, 64, [C('#d8ffe8'), C('#7aa890'), C('#2a3a34')], em=0.9)
            for j in range(3):
                cv.rect(dxk + 10 + j * 30, FB - 60, 22, 26, C('#8a6a48'), ink=C('#201810'), iw=DETAIL, em=0.5)
            R.glow(dxk + 50, FB - 60, 60, '#c8ffe0', 0.3, 'fluor')
            kit.log(cv, {'type': 'window', 'rect': [dxk + 2.0, FB - 90.0, 96.0, 58.0], 'lit': True, 'kind': 'shop'})
        else:
            big_door(cv, dxk, FB - 28, 100, 64, '#8a9496', kind='roller', seed=dxk)
        cv.rect(dxk - 6, FB - 28, 112, 28, C('#4a4e50'), ink=C('#0e1014'), iw=MAJOR)
        hazard(cv, dxk - 6, FB - 28, 112, 3)
        for bx in (dxk - 4, dxk + 98):
            cv.rect(bx, FB - 26, 6, 12, C('#1a1a1e'), ink=C('#060608'), iw=DETAIL)
        cv.rect(dxk + 30, FB - 108, 40, 10, C('#e8e4d8'), ink=C('#1e2228'), iw=DETAIL)
        cv.text('DOCK %d' % (k + 1), 'cond', 5, dxk + 50, FB - 103, C('#2a3038'), 'mm')
        cv.rect(dxk + 48, FB - 120, 4, 6, C('#2a2a34'))
        cv.ellipse(dxk + 50, FB - 113, 3, 2, C('#ffb040') if open_ else C('#4ae070'), em=1.0)
    for k in range(int(w / 400) + 1):
        greyline_logo(cv, x0 + 160 + k * 400, 66, 1.2)
    R.light(x0 + w / 2, FB + 10, w, 30, '#c8ffe0', 0.06)


@facade("warehouse_wall")
def f_warehouse_wall(R, x0, w, f):
    cv = R.cv
    wall(cv, 'concrete', x0, 0, w, FB, '#6a7470', seed=hash((R.id, x0)) % 999)
    # steel portal frames + skylights
    for k in range(int(w / 160) + 1):
        cx = x0 + 60 + k * 160
        cv.rect(cx - 6, 0, 12, FB, C('#4a5a5e'), ink=C('#0e1418'), iw=MAJOR)
        cv.hgrad(cx - 6, 0, 12, FB, [C('#7a8a8e'), C('#4a5a5e'), C('#2a3438')], mode='atop')
        hazard(cv, cx - 6, FB - 30, 12, 30)
    for k in range(int(w / 160)):
        sx = x0 + 90 + k * 160
        cv.rect(sx, 14, 100, 24, C('#2a3a40'), ink=C('#0e1418'), iw=MAJOR)
        cv.vgrad(sx + 2, 16, 96, 20, [C('#3a5050'), C('#1a2a2e')])
    # pallet racking with crates against the wall
    rs = R.rng('rack', x0)
    for k in range(int(w / 160)):
        rx = x0 + 74 + k * 160
        for lv in range(3):
            ry = FB - 4 - lv * 50
            cv.rect(rx, ry - 2, 130, 3, C('#d87a30'), ink=C('#2a1408'), iw=DETAIL)
            for j in range(3):
                if rs.random() < 0.8:
                    cw = rs.uniform(30, 40)
                    hh = rs.uniform(26, 44)
                    cv.rect(rx + 4 + j * 42, ry - 2 - hh, cw, hh, C(rs.choice(['#9a7448', '#8a8a7a', '#6a7a5a'])),
                            ink=C('#1e1a14'), iw=DETAIL)
                    if rs.random() < 0.3:
                        cv.text('GL', 'cond', 5, rx + 4 + j * 42 + cw / 2, ry - 2 - hh / 2, C('#2a3038'), 'mm', a=0.6)
        for px in (rx, rx + 128):
            cv.rect(px, FB - 154, 3, 154, C('#2a5a8a'), ink=C('#0a1a2a'), iw=DETAIL)
    for k in range(int(w / 200) + 1):
        lx = x0 + 100 + k * 200
        cv.rect(lx - 20, 46, 40, 3, C('#c8ccc8'), ink=C('#2a2e2c'), iw=DETAIL)
        cv.rect(lx - 18, 48.5, 36, 1.4, C('#e8fff0'), em=1.0)
        R.glow(lx, 50, 50, '#e0fff0', 0.45, 'fluor')
        R.light(lx, 280, 110, 70, '#d8ffe8', 0.12)


@facade("conveyor_wall")
def f_conveyor_wall(R, x0, w, f):
    cv = R.cv
    wall(cv, 'concrete', x0, 0, w, FB, '#646e6a', seed=3801)
    # conveyor belt running across at mid-height with boxes, rollers and motor housings
    cy = 120
    cv.rect(x0, cy, w, 10, C('#2a2e30'), ink=C('#0a0c0e'), iw=MAJOR)
    for k in range(int(w / 8)):
        cv.ellipse(x0 + 4 + k * 8, cy + 10, 2.4, 2.4, C('#8a9296'), ink=C('#1a1e20'), iw=0.3)
    for k in range(int(w / 60)):
        cv.rect(x0 + 10 + k * 60, cy - 16, 26, 16, C('#9a7448'), ink=C('#1e1a14'), iw=DETAIL)
        cv.rect(x0 + 10 + k * 60, cy - 10, 26, 2, C('#c8a878'))
    for k in range(int(w / 100) + 1):
        lx = x0 + 20 + k * 100
        cv.rect(lx, cy + 12, 4, FB - cy - 12, C('#d87a30'), ink=C('#2a1408'), iw=DETAIL)
    cv.rect(x0 + w / 2 - 40, cy + 20, 80, 50, C('#2a6a5a'), ink=C('#0a1a16'), iw=MAJOR)
    cv.rect(x0 + w / 2 - 30, cy + 30, 30, 16, C('#1a1e20'), ink=C('#060808'), iw=DETAIL)
    for k, c in enumerate(('#4aff70', '#ffb040', '#ff4a3a')):
        cv.ellipse(x0 + w / 2 + 14 + k * 8, cy + 36, 2, 2, C(c), em=1.0)
    cv.text('LINE 2', 'cond', 5, x0 + w / 2, cy + 60, C('#e8f0e8'), 'mm')
    greyline_logo(cv, x0 + w / 2, 50, 1.4)
    for k in range(2):
        lx = x0 + 100 + k * 200
        cv.rect(lx - 20, 30, 40, 3, C('#c8ccc8'), ink=C('#2a2e2c'), iw=DETAIL)
        cv.rect(lx - 18, 32.5, 36, 1.4, C('#e8fff0'), em=1.0)
        R.glow(lx, 34, 50, '#e0fff0', 0.45, 'fluor')
        R.light(lx, 280, 110, 70, '#d8ffe8', 0.12)


@facade("office_wall")
def f_office_wall(R, x0, w, f):
    cv = R.cv
    wall(cv, 'stucco', x0, 0, w, FB, '#a8aca0', seed=3901, soot=0.15)
    cv.rect(x0, 0, w, 10, C('#6a6e66'))
    # glass partition into the holding room (where Eli is kept), blinds half drawn
    gx, gw = x0 + 360, 360
    cv.rect(gx - 4, 40, gw + 8, FB - 40, C('#4a4e4a'), ink=C('#0e100e'), iw=MAJOR)
    cv.vgrad(gx, 44, gw, FB - 48, [C('#3a4644'), C('#232a28')], em=0.0)
    for k in range(1, 4):
        cv.rect(gx + gw * k / 4 - 1, 44, 2, FB - 48, C('#4a4e4a'))
    yy = 44
    while yy < 110:
        cv.rect(gx, yy, gw, 1.4, C('#c8ccc0'))
        cv.rect(gx, yy + 1.4, gw, 0.6, C('#6a6e66'))
        yy += 2.6
    cv.rect(gx + 8, 120, gw - 16, 3, C('#7a7e76'))
    for k in range(4):
        kit.log(cv, {'type': 'window', 'rect': [round(gx + gw * k / 4 + 3, 1), 112.0, round(gw / 4 - 6, 1), 80.0],
                     'lit': False, 'kind': 'office'})
    cv.rect(gx + 150, 140, 40, 60, C('#3a3e3a'), ink=C('#0a0c0a'), iw=DETAIL)    # chair silhouette
    cv.rect(gx + 2, FB - 70, 30, 14, C('#e8e4d8'), ink=C('#1e2228'), iw=DETAIL)
    cv.text(f.get('sign', 'HOLDING'), 'cond', 6, gx + 17, FB - 63, C('#c8302a'), 'mm')
    # office side: filing wall, map, clock, Greyline plans
    cv.rect(x0 + 40, 40, 140, 80, C('#e8e4d4'), ink=C('#2a2a24'), iw=MAJOR)
    cv.vgrad(x0 + 44, 44, 132, 72, [C('#c8d8c8'), C('#a8c0b0')])
    for k in range(5):
        cv.rect(x0 + 50 + k * 26, 60 + (k % 2) * 16, 18, 12, C('#e8c070'), ink=C('#6a4a20'), iw=0.4)
    cv.line([(x0 + 50, 100), (x0 + 170, 56)], 0.6, C('#c8302a'))
    cv.text('RIVERVIEW LOFTS - PHASE 2', 'cond', 4, x0 + 110, 112, C('#2a3038'), 'mm')
    greyline_logo(cv, x0 + 260, 60, 1.2)
    cv.ellipse(x0 + 260, 100, 9, 9, C('#f4f0e4'), ink=C('#2a2026'), iw=MAJOR)
    cv.line([(x0 + 260, 100), (x0 + 264, 96)], 0.6, C('#2a2026'))
    for k in range(3):
        lx = x0 + 120 + k * 300
        cv.rect(lx - 22, 12, 44, 3, C('#c8ccc8'), ink=C('#2a2e2c'), iw=DETAIL)
        cv.rect(lx - 20, 14.5, 40, 1.4, C('#f0fff4'), em=1.0)
        R.glow(lx, 16, 50, '#e8fff0', 0.42, 'fluor')
        R.light(lx, 280, 100, 70, '#e0fff0', 0.12)
    poster(cv, x0 + 200, 130, 14, 18, seed=3902, kind='missing')


@facade("crane_hall")
def f_crane_hall(R, x0, w, f):
    cv = R.cv
    wall(cv, 'concrete', x0, 0, w, FB, '#5a6462', seed=4001)
    # huge Greyline banner, overhead crane, skylight shafts of cold light
    gm = M(C('#3a4448'))
    cv.rect(x0, 24, w, 16, C('#c8a030'), ink=C('#2a2008'), iw=MAJOR)
    hazard(cv, x0, 38, w, 3)
    tx = x0 + w * 0.88
    cv.rect(tx - 18, 40, 36, 18, gm.b, ink=gm.i, iw=MAJOR)
    for off in (-5, 5):
        cv.line([(tx + off, 58), (tx + off, 120)], 0.6, C('#2a2a34'))
    cv.fill_poly([(tx - 10, 120), (tx + 10, 120), (tx + 8, 132), (tx - 8, 132)], gm.b, ink=gm.i, iw=DETAIL)
    cv.line([(tx, 132), (tx, 142), (tx + 6, 146), (tx + 7, 140)], 1.6, C('#8a8e9a'))
    bx, bw = x0 + w / 2 - 160, 320
    cv.rect(bx, 60, bw, 70, C('#d8dcdc'), ink=C('#0e1014'), iw=MAJOR)
    cv.vgrad(bx + 3, 63, bw - 6, 64, [C('#e8ecec'), C('#b8c0c0')])
    greyline_logo(cv, bx + bw / 2, 84, 3.0)
    cv.text('BUILDING A BETTER BELLWETHER', 'cond', 6, bx + bw / 2, 114, C('#3a4448'), 'mm', tracking=0.6)
    for k in range(4):
        sx = x0 + 80 + k * 280
        cv.fill_poly([(sx, 0), (sx + 60, 0), (sx + 110, FB), (sx + 30, FB)], C('#c8e0e8'), a=0.07, mode='add')
    for k in range(int(w / 180) + 1):
        cx = x0 + 20 + k * 180
        cv.rect(cx - 6, 0, 12, FB, C('#4a5458'), ink=C('#0e1014'), iw=MAJOR)
        hazard(cv, cx - 6, FB - 30, 12, 30)
    poster(cv, x0 + 120, FB - 40, 14, 18, seed=4002, kind='missing')
    tag(cv, x0 + w - 200, FB - 20, 'ROOK', C('#c8c8d0'), size=7, seed=40, a=0.5)
    for k in range(3):
        lx = x0 + 200 + k * 360
        R.glow(lx, 60, 70, '#e0fff0', 0.35, 'fluor')
        R.light(lx, 290, 160, 80, '#d8ffe8', 0.12)
