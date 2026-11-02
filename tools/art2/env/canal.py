"""Backstreet Oath env v2 -- Canal Market: gold + teal late afternoon, water shimmer, market life."""
import math

import numpy as np

from raster import Canvas, C, mix, shade, light, ink_of, value_noise, rng_of
import kit
from kit import M, MAJOR, DETAIL, window, door, awning, cornice, parapet, brick_wall, drainpipe, cable, \
    neon_text, painted_text, poster, tag, string_lights
from room import FACADE_BOTTOM as FB, H, light_pool, sun_rim, weeds
from common import facade, FACADES, shop_building, door_x, lantern, bunting, big_door, gable, wall, stone_wall, \
    storefront, shop_door
from grounds2 import canal_water

WATER_TOP = 150      # canal water band behind the railing (far quay edge sits in the district mid layer)


@facade("warehouse_small")
def f_warehouse_small(R, x0, w, f):
    cv = R.cv
    if f.get('sign') == 'DRAWBRIDGE':
        return drawbridge_house(R, x0, w, f)
    top = 70
    wall(cv, 'brick', x0, top, w, FB - top, '#8a4a3a', seed=hash((R.id, x0)) % 9999)
    gable(cv, x0, top, w, 34, '#6a5a58')
    cv.rect(x0 - 3, top - 1, w + 6, 2, C('#4a3a3a'))
    sun_rim(R, x0, top - 30, FB - 40, a=0.45)
    # hoist beam + loft door
    lx = x0 + w / 2
    cv.rect(lx - 9, top - 8, 18, 24, C('#5a3a2a'), ink=C('#1e1418'), iw=MAJOR)
    cv.rect(lx - 1, top - 16, 2, 10, C('#3a2a2a'))
    cv.rect(lx - 1, top - 16, 14, 2, C('#3a2a2a'), ink=C('#140c10'), iw=DETAIL)
    cv.line([(lx + 12, top - 14), (lx + 12, top + 10)], 0.4, C('#2a2026'))
    cv.rect(lx + 10.5, top + 10, 3, 2.5, C('#8a8a96'))
    for k, wx in enumerate((x0 + 18, x0 + w - 34)):
        window(cv, wx, top + 30, 16, 22, lit=k == 0, seed=k + 3, frame='#d8ccb4', kind='grid')
    big_door(cv, x0 + w / 2 - 26, FB, 52, 58, '#6a3a2a', kind='barn', seed=5)
    painted_text(cv, 'GOODS', x0 + w / 2, top + 64, 6, C('#e8dcc0'), shadow=False, fade=0.4, seed=2)
    poster(cv, x0 + 14, FB - 34, 12, 16, seed=hash((R.id, 'wh')) % 999, kind='missing')


def drawbridge_house(R, x0, w, f):
    """Control house + channel; the bridge leaf itself is a conditional layer (see gen_env2 cm_pier)."""
    cv = R.cv
    hx, hw = x0 + 14, 66
    # channel water to the right of the house
    canal_water(R, hx + hw, 120, x0 + w - hx - hw, FB - 120, seed=3)
    cv.rect(hx + hw, 116, x0 + w - hx - hw, 4, C('#8a8478'), ink=C('#2a2430'), iw=DETAIL)
    # quay walls
    stone_wall(cv, hx + hw, 196, x0 + w - hx - hw, FB - 196, '#8a8070', 41)
    # bridge pivot pier + counterweight block
    px = hx + hw + 14
    cv.rect(px - 10, 150, 22, 64, C('#7a7468'), ink=C('#2a2430'), iw=MAJOR)
    cv.ellipse(px, 160, 6, 6, C('#5a5c66'), ink=C('#1a1420'), iw=MAJOR)
    cv.ellipse(px, 160, 2, 2, C('#c8ccd8'))
    # control house: brick tower with a glazed cab and hip roof
    wall(cv, 'brick', hx, 90, hw, FB - 90, '#8a3e32', seed=77)
    cv.fill_poly([(hx - 4, 62), (hx + hw / 2, 44), (hx + hw + 4, 62)], C('#3a3a46'), ink=C('#140c18'), iw=MAJOR)
    cv.rect(hx - 3, 60, hw + 6, 32, C('#d8ccb4'), ink=C('#2a2026'), iw=MAJOR)
    for k in range(4):
        window(cv, hx + 2 + k * 16, 64, 13, 22, lit=True, seed=900 + k, frame='#d8ccb4', sill=False, lintel=False,
               interior='person' if k == 1 else 'blank', curtains=False, mull=False)
    cv.rect(hx + 4, 98, hw - 8, 14, C('#f0e8d0'), ink=C('#2a2026'), iw=MAJOR)
    painted_text(cv, 'DRAWBRIDGE', hx + hw / 2, 105.5, 6, C('#7a2a2a'), shadow=False)
    door(cv, hx + hw / 2 - 9, FB, 18, 46, C('#2e5a4a'), lit=False, seed=31, frame='#d8ccb4')
    window(cv, hx + 8, 124, 14, 22, lit=False, seed=33, frame='#d8ccb4')
    # traffic signal + warning sign
    cv.rect(x0 + w - 30, 120, 2, FB - 120, C('#2a2a34'))
    cv.rect(x0 + w - 35, 118, 12, 20, C('#2a2a34'), ink=C('#0e0a14'), iw=DETAIL)
    cv.ellipse(x0 + w - 29, 123, 2.4, 2.4, C('#ff4a3a'), em=1.0)
    cv.ellipse(x0 + w - 29, 132, 2.4, 2.4, C('#3a2a2a'))
    R.glow(x0 + w - 29, 123, 14, '#ff4a3a', 0.5, 'neon')
    cv.rect(x0 + w - 60, 150, 22, 14, C('#f8d040'), ink=C('#2a2010'), iw=DETAIL)
    cv.text('BRIDGE', 'cond', 3.6, x0 + w - 49, 154.5, C('#2a2010'), 'mm')
    cv.text('OPENS', 'cond', 3.6, x0 + w - 49, 159.5, C('#2a2010'), 'mm')
    R.ambient.append({"type": "water_shimmer", "x": float(hx + hw), "y": 120.0, "w": float(x0 + w - hx - hw),
                      "h": float(FB - 120)})
    R.drawbridge = (px, 160, x0 + w)


@facade("market_arch")
def f_market_arch(R, x0, w, f):
    cv = R.cv
    # through the arch: back stalls + low wall (sky above is transparent)
    cv.rect(x0 + 24, 150, w - 48, FB - 150, C('#a89a80'))
    kit.brick_wall(cv, x0 + 24, 176, w - 48, FB - 176, C('#9a6a50'), seed=61, soot=0.2)
    for k in range(5):
        sx = x0 + 40 + k * (w - 80) / 5
        c1 = ['#e84a3a', '#3aa0d8', '#f8d040', '#5ac06a', '#e86aa0'][k]
        awning(cv, sx, 152, (w - 80) / 5 - 6, 8, C(c1), C('#f4f0e8'), stripe=4, valance=2)
        cv.rect(sx + 2, 164, (w - 80) / 5 - 10, 12, C('#7a5a3a'), ink=C('#2a1a14'), iw=DETAIL)
        for j in range(4):
            cv.ellipse(sx + 5 + j * 6, 163, 2, 1.6, C(['#f08a30', '#e8d040', '#c83a3a', '#8ac050'][j]))
    cv.vgrad(x0 + 24, 150, w - 48, 64, [C('#f8e0b0', 90), C('#f8e0b0', 0)], mode='atop')
    # pillars
    for px in (x0, x0 + w - 24):
        stone_wall(cv, px, 70, 24, FB - 70, '#b89a7a', hash((R.id, px)) % 999)
        cv.rect(px - 2, 64, 28, 7, C('#d8c8a8'), ink=C('#3a2a26'), iw=MAJOR)
        cv.fill_poly([(px + 4, 64), (px + 12, 52), (px + 20, 64)], C('#d8c8a8'), ink=C('#3a2a26'), iw=MAJOR)
        lantern(R, px + 12, 96, '#f8c860', 3.2)
        R.glow(px + 12, 96, 18, '#ffd080', 0.4, 'flame')
    # iron arch with sign
    ac = M(C('#2e3a44'))
    pts_o = [(x0 + 24 + (w - 48) * t, 76 - math.sin(t * math.pi) * 34) for t in np.linspace(0, 1, 40)]
    pts_i = [(x0 + 24 + (w - 48) * t, 86 - math.sin(t * math.pi) * 26) for t in np.linspace(0, 1, 40)]
    cv.line(pts_o, 2.0, ac.b, ink=ac.i, iw=DETAIL)
    cv.line(pts_i, 1.4, ac.b, ink=ac.i, iw=DETAIL)
    for t in np.linspace(0.05, 0.95, 14):
        a = pts_o[int(t * 39)]
        b = pts_i[int(t * 39)]
        cv.line([a, b], 0.7, ac.b)
    sm = M(C('#2a5a3a'))
    cv.rect(x0 + w / 2 - 46, 26, 92, 18, sm.b, ink=sm.i, iw=MAJOR)
    cv.rect(x0 + w / 2 - 46, 26, 92, 1, sm.h, mode='atop')
    painted_text(cv, f.get('sign', 'CANAL MARKET'), x0 + w / 2, 35.5, 9, C('#f4e8c0'), tracking=0.6)
    bunting(R, x0 + 24, 100, x0 + w - 24, 100, sag=12, seed=1)
    bunting(R, x0 + 24, 112, x0 + w - 24, 112, sag=8, seed=3)
    R.ambient.append({"type": "pigeons", "x": float(x0 + w / 2 - 30), "y": 25.0, "w": 60})


@facade("shopfront")
def f_shopfront(R, x0, w, f):
    s = f.get('sign', '')
    if 'NOODLE' in s:
        shop_building(R, x0, w, f, 'brick', '#a83a32', '#e8d8b8', top=54, upper=1, sign_bg='#1e1418',
                      sign_fg='#f8d860', sign_style='painted', display='noodle', awn=('#c8302a', '#f4e8c0'), seed=11)
        for k in range(5):
            lantern(cv_r(R), x0 + 20 + k * (w - 40) / 4, 138, '#e8403a', 3.0)
        R.glow(x0 + w / 2, 138, w * 0.5, '#ff6a4a', 0.25, 'flame')
    elif 'BOOK' in s:
        shop_building(R, x0, w, f, 'stone', '#c8b896', '#2e5a3e', top=50, upper=1, sign_bg='#2e5a3e',
                      sign_fg='#f4e8c0', display='books', awn=('#2e5a3e', '#e8dcc0'), seed=12)
        poster(R.cv, x0 + 12, FB - 30, 11, 14, seed=hash((R.id, 'bk')) % 999, kind='missing')
    else:
        shop_building(R, x0, w, f, 'brick', '#9a5442', '#d8ccb4', top=60, upper=1, display='plain', seed=13)


def cv_r(R):
    return R


@facade("stall_row")
def f_stall_row(R, x0, w, f):
    cv = R.cv
    rs = R.rng('stall', x0)
    # long low market shed behind the stalls
    wall(cv, 'clap', x0, 112, w, FB - 112, '#9a7a5a', hash((R.id, x0)) % 999)
    cv.fill_poly([(x0 - 2, 114), (x0 + w + 2, 114), (x0 + w + 2, 100), (x0 - 2, 100)], C('#6a4a40'),
                 ink=C('#1e1418'), iw=MAJOR)
    k = 0
    xx = x0 + 4
    while xx < x0 + w - 30:
        sw = rs.uniform(52, 66)
        if xx + sw > x0 + w - 4:
            break
        c = rs.choice(['#e84a3a', '#3aa0d8', '#f8b030', '#5ac06a', '#e86aa0'])
        awning(cv, xx, 128, sw, 9, C(c), C('#f4f0e8'), stripe=5, valance=2.5)
        # counter with produce/fish/goods
        cv.rect(xx + 2, 172, sw - 4, FB - 172, C('#7a5436'), ink=C('#20140e'), iw=MAJOR)
        planks_front(cv, xx + 2, 172, sw - 4, FB - 172)
        goods = rs.choice(['fruit', 'veg', 'fish', 'cloth', 'flowers'])
        for j in range(int((sw - 8) / 5)):
            gx = xx + 6 + j * 5
            if goods == 'fruit':
                cv.ellipse(gx, 170, 2.2, 2, C(rs.choice(['#f08a30', '#e8d040', '#c83a3a', '#8ac050'])),
                           ink=C('#3a2010'), iw=0.3)
            elif goods == 'veg':
                cv.ellipse(gx, 170, 2.4, 1.8, C(rs.choice(['#6aa040', '#8ac050', '#e8a040', '#a8304a'])),
                           ink=C('#203010'), iw=0.3)
            elif goods == 'fish':
                cv.ellipse(gx, 170.5, 2.6, 1.0, C('#a8b8c8'), ink=C('#3a4a5a'), iw=0.3)
            elif goods == 'cloth':
                cv.rect(gx - 2, 166, 4, 5, C(rs.choice(['#c84a6a', '#4a8ac8', '#e8c040', '#5ab08a'])),
                        ink=C('#201820'), iw=0.3)
            else:
                cv.ellipse(gx, 169, 1.6, 1.6, C(rs.choice(['#f0a0c0', '#f8e060', '#f4f0e8', '#e84a4a'])))
                cv.rect(gx - 0.3, 170, 0.6, 2, C('#4a7a3a'))
        # vendor
        if rs.random() < 0.6:
            vx = xx + sw * rs.uniform(0.3, 0.7)
            cv.ellipse(vx, 150, 3.2, 3.6, C('#8a5a48'), ink=C('#2a1a18'), iw=DETAIL)
            cv.fill_poly([(vx - 6, 168), (vx - 5, 155), (vx + 5, 155), (vx + 6, 168)],
                         C(rs.choice(['#4a6a9a', '#9a4a4a', '#e8e0d0', '#5a7a4a'])), ink=C('#201820'), iw=DETAIL)
        # price chalkboard
        cv.rect(xx + sw - 14, 176, 10, 8, C('#2a2a2e'), ink=C('#6a4a2a'), iw=0.6)
        cv.text('25¢', 'cond', 3, xx + sw - 9, 180, C('#f4f0e8'), 'mm')
        xx += sw + 6
        k += 1
    bunting(R, x0, 118, x0 + w, 120, sag=6, seed=int(x0) % 5)
    sun_rim(R, x0, 100, 170, a=0.35)
    R.light(x0 + w / 2, FB + 12, w * 0.5, 26, '#ffd890', 0.08)


def planks_front(cv, x, y, w, h):
    yy = y
    while yy < y + h:
        cv.rect(x, yy, w, 0.5, C('#4a3020'), mode='atop')
        yy += 4


@facade("canal_rail")
def f_canal_rail(R, x0, w, f):
    cv = R.cv
    canal_water(R, x0, WATER_TOP, w, FB - WATER_TOP - 12, seed=int(x0), sky='#f8e0a8')
    # reflections of the far houses: coloured soft vertical smears
    rs = R.rng('refl', x0)
    for k in range(int(w / 16)):
        cx = x0 + k * 16 + rs.uniform(-3, 3)
        c = C(rs.choice(['#e8a060', '#c86a5a', '#e8d8b8', '#7aa8b0', '#b07a9a', '#d8b860']))
        cv.vgrad(cx, WATER_TOP, rs.uniform(6, 12), 22, [mix(c, C('#2e7a84'), 0.5), C('#2e7a84', 0)], a=0.5,
                 mode='atop')
    # quay wall (near side) + iron railing
    stone_wall(cv, x0, FB - 12, w, 12, '#9a8e7e', hash((R.id, x0, 'q')) % 999, soot=0.25)
    cv.rect(x0, FB - 13, w, 2.2, C('#c8bca8'), ink=C('#2a2430'), iw=DETAIL)
    rail = M(C('#2a3640'))
    cv.rect(x0, FB - 30, w, 1.5, rail.b, ink=rail.i, iw=DETAIL)
    cv.rect(x0, FB - 22, w, 0.8, rail.b)
    xx = x0 + 3
    while xx < x0 + w:
        cv.rect(xx, FB - 30, 0.8, 18, rail.b)
        if int(xx) % 30 < 4:
            cv.rect(xx - 0.8, FB - 32, 2.4, 20, rail.b, ink=rail.i, iw=DETAIL)
            cv.ellipse(xx + 0.4, FB - 33, 1.4, 1.4, rail.b)
        xx += 5
    cv.rect(x0, FB - 30, w, 0.5, C('#f8d8a0'), a=0.7)
    # moored boats & a lifebuoy
    for k in range(int(w / 380) + 1):
        bx = x0 + 120 + k * 380 + rs.uniform(-40, 40)
        if bx < x0 + w - 60:
            boat(R, bx, FB - 22, rs.choice(['#e8e0d0', '#c83a3a', '#2e6a5a', '#3a5a9a']), rs)
    lb = x0 + w * 0.5
    cv.ellipse(lb, FB - 22, 4, 4, C('#f06a3a'), ink=C('#3a1a10'), iw=DETAIL)
    cv.ellipse(lb, FB - 22, 2, 2, C('#2e7a84'))
    for a in (0.4, 2.0, 3.5, 5.1):
        cv.rect(lb + math.cos(a) * 3 - 0.6, FB - 22 + math.sin(a) * 3 - 0.6, 1.2, 1.2, C('#f4f0e8'))
    R.ambient.append({"type": "water_shimmer", "x": float(x0), "y": float(WATER_TOP), "w": float(w),
                      "h": float(FB - WATER_TOP - 14)})
    R.light(x0 + w / 2, FB + 6, w, 24, '#a8e0e0', 0.08)


def boat(R, x, y, col, rs):
    cv = R.cv
    m = M(C(col))
    cv.fill_poly([(x - 24, y - 8), (x + 26, y - 8), (x + 20, y), (x - 20, y)], m.b, ink=m.i, iw=MAJOR)
    cv.rect(x - 24, y - 8, 50, 1.2, m.h, mode='atop')
    cv.rect(x - 6, y - 16, 16, 8, C('#e8e4d8'), ink=C('#2a2430'), iw=DETAIL)
    cv.rect(x - 4, y - 14, 4, 3, C('#5a8aa8'))
    cv.rect(x + 2, y - 14, 4, 3, C('#5a8aa8'))
    cv.ellipse(x, y + 1.5, 22, 1.4, C('#1e4a5a'), a=0.5)


@facade("footbridge")
def f_footbridge(R, x0, w, f):
    cv = R.cv
    canal_water(R, x0, WATER_TOP, w, FB - WATER_TOP, seed=99, sky='#f8e0a8')
    # bridge abutments at both ends
    for ax in (x0 - 4, x0 + w - 10):
        stone_wall(cv, ax, FB - 34, 14, 34, '#9a8e7e', int(ax) % 999)
    # lattice arch truss over the deck
    ac = M(C('#2a3a48'))
    pts_o = [(x0 + w * t, 150 - math.sin(t * math.pi) * 70) for t in np.linspace(0, 1, 48)]
    pts_i = [(x0 + w * t, 162 - math.sin(t * math.pi) * 56) for t in np.linspace(0, 1, 48)]
    cv.line(pts_o, 2.6, ac.b, ink=ac.i, iw=DETAIL)
    cv.line(pts_i, 1.8, ac.b, ink=ac.i, iw=DETAIL)
    for i in range(1, 47, 2):
        cv.line([pts_o[i], pts_i[i + 1]], 0.8, ac.b)
        cv.line([pts_i[i], pts_o[i + 1]], 0.8, ac.b)
    for i in range(4, 47, 6):
        cv.line([pts_i[i], (pts_i[i][0], FB - 18)], 0.9, ac.b)
    cv.line(pts_o, 0.5, C('#f8d8a0'), a=0.6)
    cv.rect(x0, FB - 20, w, 2, ac.b, ink=ac.i, iw=DETAIL)
    bunting(R, x0 + 10, 112, x0 + w - 10, 112, sag=10, seed=2)
    string_lights(cv, x0 + 30, 96, x0 + w - 30, 96, sag=14, step=9, seed=6, glow=True)
    sign_x = x0 + w / 2
    cv.rect(sign_x - 30, 68, 60, 12, C('#2a5a3a'), ink=C('#0e1a12'), iw=MAJOR)
    painted_text(cv, 'MILL CUT BRIDGE', sign_x, 74.5, 5.5, C('#f4e8c0'), shadow=False, tracking=0.3)
    R.ambient.append({"type": "water_shimmer", "x": float(x0), "y": float(WATER_TOP), "w": float(w),
                      "h": float(FB - WATER_TOP)})


@facade("fish_hall")
def f_fish_hall(R, x0, w, f):
    cv = R.cv
    top = 72
    wall(cv, 'brick', x0, top, w, FB - top, '#9a4a3a', seed=501)
    cv.fill_poly([(x0 - 4, top + 2), (x0 + 30, top - 18), (x0 + w - 30, top - 18), (x0 + w + 4, top + 2)],
                 C('#4a5a68'), ink=C('#141820'), iw=MAJOR)
    # central gable with clock
    gx = x0 + w / 2
    cv.fill_poly([(gx - 46, top - 10), (gx, top - 46), (gx + 46, top - 10)], C('#9a4a3a'), ink=C('#2a1214'), iw=MAJOR)
    cv.ellipse(gx, top - 24, 9, 9, C('#f4f0e4'), ink=C('#2a2026'), iw=MAJOR)
    cv.line([(gx, top - 24), (gx + 4, top - 26)], 0.7, C('#2a2026'))
    cv.line([(gx, top - 24), (gx - 1, top - 30)], 0.5, C('#2a2026'))
    sun_rim(R, x0, top - 18, FB - 50, a=0.4)
    for k in range(6):
        wx = x0 + 20 + k * (w - 54) / 5
        window(cv, wx, top + 6, 14, 22, lit=k % 2 == 0, seed=k + 70, frame='#e8dcc4', kind='grid')
        cv.ellipse(wx + 7, top + 6, 8.5, 5, C('#e8dcc4'), ink=C('#2a2026'), iw=DETAIL)
    sm = M(C('#1e3a5a'))
    cv.rect(x0 + 14, top + 38, w - 28, 18, sm.b, ink=sm.i, iw=MAJOR)
    painted_text(cv, f.get('sign', 'FISH HALL'), gx, top + 47.5, 10, C('#f4f0e8'), tracking=0.6)
    awning(cv, x0 + 8, top + 60, w - 16, 7, C('#2e5a8a'), C('#f4f0e8'), stripe=6, valance=3)
    # open stalls: ice beds with fish, fishmongers, scales
    sy = top + 74
    nb = int((w - 20) / 96)
    for k in range(nb):
        bx = x0 + 12 + k * (w - 24) / nb
        bw = (w - 24) / nb - 6
        cv.vgrad(bx, sy, bw, FB - sy - 4, [C('#3a4a5a'), C('#2a3442')])
        cv.rect(bx, FB - 26, bw, 22, C('#8a8a96'), ink=C('#2a2a34'), iw=MAJOR)
        cv.rect(bx + 2, FB - 30, bw - 4, 5, C('#e8f4fa'), ink=C('#6a7a88'), iw=DETAIL)
        rs = R.rng('fish', k)
        for j in range(int((bw - 8) / 7)):
            cv.ellipse(bx + 6 + j * 7, FB - 29.5, 3, 1.2, C(rs.choice(['#a8b8c8', '#c8a0a0', '#8aa0b0'])),
                       ink=C('#3a4a5a'), iw=0.3)
        px = bx + bw * 0.5
        cv.ellipse(px, sy + 14, 3.2, 3.6, C('#8a5a48'), ink=C('#2a1a18'), iw=DETAIL)
        cv.fill_poly([(px - 6, FB - 30), (px - 5, sy + 18), (px + 5, sy + 18), (px + 6, FB - 30)], C('#e8e8f0'),
                     ink=C('#3a3a48'), iw=DETAIL)
        cv.rect(bx + 4, sy + 4, 1, 10, C('#6a6a72'))
        cv.ellipse(bx + 4.5, sy + 15, 3, 1, C('#c8ccd8'), ink=C('#3a3a48'), iw=0.3)
    R.ambient.append({"type": "pigeons", "x": float(gx - 40), "y": float(top - 19), "w": 80})
    R.light(x0 + w / 2, FB + 12, w * 0.5, 26, '#c8e0ff', 0.06)


@facade("pier")
def f_pier(R, x0, w, f):
    cv = R.cv
    sea_top = 128
    canal_water(R, x0, sea_top, w, FB - sea_top, seed=7, deep='#1e5068', mid='#3a8aa0', light_c='#b8e8e8',
                sky='#f8e8b8')
    rs = R.rng('pier')
    # sun glitter path
    for _ in range(140):
        gx = rs.gauss(x0 + w * 0.55, w * 0.12)
        gy = rs.uniform(sea_top + 2, sea_top + 40)
        cv.rect(gx, gy, rs.uniform(1.5, 5), 0.5, C('#fff4c8'), a=rs.uniform(0.4, 0.9), em=0.7)
    # wooden pier receding with pilings
    pm = M(C('#7a5a40'))
    cv.fill_poly([(x0 + 60, sea_top + 22), (x0 + w - 60, sea_top + 22), (x0 + w - 40, sea_top + 30),
                  (x0 + 40, sea_top + 30)], pm.b, ink=pm.i, iw=DETAIL)
    for k in range(int((w - 80) / 16)):
        px = x0 + 44 + k * 16
        cv.rect(px, sea_top + 30, 2, 12, pm.s, ink=pm.i, iw=0.4)
    for k, c in enumerate(('#e8e0d0', '#c83a3a', '#2e6a5a')):
        bx = x0 + 110 + k * 170 + rs.uniform(-20, 20)
        fishing_boat(R, bx, sea_top + 64 + k * 6, c)
    # near quay edge with bollards and a low chain
    stone_wall(cv, x0, FB - 14, w, 14, '#9a8e7e', 512)
    cv.rect(x0, FB - 15, w, 2.2, C('#c8bca8'), ink=C('#2a2430'), iw=DETAIL)
    xx = x0 + 20
    while xx < x0 + w:
        cv.rect(xx - 2.5, FB - 23, 5, 9, C('#2a2a34'), ink=C('#0e0a14'), iw=DETAIL)
        cv.ellipse(xx, FB - 23, 3.2, 1.4, C('#3a3a46'))
        xx += 60
    for xx in range(int(x0 + 20), int(x0 + w - 60), 60):
        cable(cv, xx + 2.5, FB - 20, xx + 57.5, FB - 20, sag=4, w=0.6, col='#3a3440')
    R.ambient.append({"type": "water_shimmer", "x": float(x0), "y": float(sea_top), "w": float(w),
                      "h": float(FB - sea_top - 16)})
    R.ambient.append({"type": "pigeons", "x": float(x0 + w * 0.3), "y": float(sea_top + 21), "w": 60})
    R.light(x0 + w / 2, FB + 8, w, 26, '#fff0c8', 0.08)


def fishing_boat(R, x, y, col):
    cv = R.cv
    m = M(C(col))
    cv.fill_poly([(x - 34, y - 12), (x + 38, y - 12), (x + 30, y), (x - 28, y)], m.b, ink=m.i, iw=MAJOR)
    cv.rect(x - 34, y - 12, 72, 1.4, m.h, mode='atop')
    cv.rect(x - 34, y - 6, 72, 1.0, C('#2a2430'), a=0.6, mode='atop')
    cv.rect(x - 12, y - 26, 22, 14, C('#f4f0e4'), ink=C('#2a2430'), iw=MAJOR)
    for k in range(3):
        cv.rect(x - 9 + k * 6.5, y - 23, 4, 4, C('#5a8aa8'))
    cv.rect(x + 18, y - 44, 1.2, 32, C('#3a3036'))
    cv.line([(x + 18.6, y - 44), (x - 30, y - 13)], 0.4, C('#3a3036'))
    cv.line([(x + 18.6, y - 44), (x + 36, y - 13)], 0.4, C('#3a3036'))
    cv.ellipse(x, y + 2, 32, 1.8, C('#1e4a5a'), a=0.5)


# ----------------------------------------------------------------------------- interiors
@facade("noodle_interior")
def f_noodle_interior(R, x0, w, f):
    from interiors import room_shell, menu_board, wall_window, pendant, shelf_jars, community_board
    cv = R.cv
    room_shell(R, x0, w, '#d8b88a', '#7a4a2a', wall_kind='wood', trim='#4a2a1a')
    cv.rect(x0 + 14, 22, 92, 16, C('#1e1418'), ink=C('#0a0608'), iw=MAJOR)
    painted_text(cv, "FONG'S NOODLES", x0 + 60, 30.5, 7.5, C('#f8d860'), tracking=0.4)
    wall_window(R, x0 + 30, 60, 50, 50, round_=True, view='canal')
    for k, (t, p) in enumerate((('NOODLES', '2.75'), ('DUMPLING', '1.50'), ('BROTH', '1.25'), ('TEA', '0.50'))):
        menu_board(R, x0 + 196 + k * 56, 20, 50, 30, t, p, bg='#f4e8c8', fg='#7a1a1a')
    # kitchen pass with steam
    kx, ky, kw, kh = x0 + 200, 64, 220, 54
    cv.rect(kx - 3, ky - 3, kw + 6, kh + 6, C('#5a3a24'), ink=C('#1e120c'), iw=MAJOR)
    cv.vgrad(kx, ky, kw, kh, [C('#fff0c8'), C('#f0c888'), C('#c8945a')], em=1.0)
    for k in range(5):
        cv.ellipse(kx + 24 + k * 42, ky + kh - 10, 12, 4, C('#9aa0a8'), ink=C('#3a3a48'), iw=DETAIL, em=1.0)
        R.ambient.append({"type": "steam", "x": float(kx + 24 + k * 42), "y": float(ky + kh - 14), "rate": 0.4})
    cv.ellipse(kx + 110, ky + 22, 4.5, 5, C('#c89a7a'), em=1.0)
    cv.fill_poly([(kx + 100, ky + kh), (kx + 102, ky + 30), (kx + 118, ky + 30), (kx + 120, ky + kh)], C('#f4f0e8'),
                 em=1.0)
    cv.rect(kx - 5, ky + kh, kw + 10, 4, C('#7a4a2a'), ink=C('#1e120c'), iw=DETAIL)
    for k in range(6):
        pendant(R, x0 + 120 + k * 90, 12, '#e8403a', lantern=True)
    shelf_jars(R, x0 + 460, 140, 150)
    community_board(R, x0 + 540, 56, 70, 44)
    R.glow(kx + kw / 2, ky + kh / 2, 120, '#ffc880', 0.25, 'none')


@facade("bookshop_interior")
def f_bookshop_interior(R, x0, w, f):
    from interiors import room_shell, bookcase, wall_window, pendant, community_board
    cv = R.cv
    room_shell(R, x0, w, '#5a6a4a', '#5a3a24', wall_kind='paper', trim='#3a2416')
    bookcase(R, x0 + 6, 18, 140, WB - 18)
    bookcase(R, x0 + 300, 18, 150, WB - 18)
    bookcase(R, x0 + 470, 18, 164, WB - 18)
    wall_window(R, x0 + 168, 40, 110, 76, view='canal')
    cv.rect(x0 + 186, 126, 74, 14, C('#2e5a3e'), ink=C('#0e1a12'), iw=MAJOR)
    painted_text(cv, 'HOLLIS BOOKS', x0 + 223, 133.5, 6.5, C('#f4e8c0'), shadow=False)
    # rolling ladder
    lc = C('#7a5434')
    cv.line([(x0 + 120, 24), (x0 + 140, WB - 2)], 1.2, lc)
    cv.line([(x0 + 128, 24), (x0 + 148, WB - 2)], 1.2, lc)
    for k in range(12):
        t = k / 12
        cv.line([(x0 + 120 + 20 * t, 24 + (WB - 26) * t), (x0 + 128 + 20 * t, 24 + (WB - 26) * t)], 0.7, lc)
    pendant(R, x0 + 223, 8, '#2e6a4a')
    pendant(R, x0 + 560, 8, '#2e6a4a')
    community_board(R, x0 + 190, 148, 70, 40)
    R.ambient.append({"type": "dust_motes", "x": float(x0 + 170), "y": 50.0, "w": 110, "h": 150})
