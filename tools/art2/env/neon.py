"""Backstreet Oath env v2 -- Neon Mile: night, magenta/cyan neon, wet streets, marquee bulbs."""
import math

import numpy as np

from raster import C, mix, shade, light, ink_of, rng_of
import kit
from kit import M, MAJOR, DETAIL, window, door, awning, cornice, parapet, brick_wall, drainpipe, cable, \
    neon_text, painted_text, poster, tag, fire_escape, ac_unit, string_lights, graffiti_piece
from room import FACADE_BOTTOM as FB, H, light_pool, sun_rim, weeds
from common import facade, door_x, big_door, wall, shop_door, lantern, fence, storefront, shop_building, chainlink

NEONS = ['#ff4ab0', '#4ae0ff', '#f8e040', '#8aff8a', '#ff8a3a', '#c070ff']


def hexc(c):
    return '#%02x%02x%02x' % c[:3]


@facade("brick_night")
def f_brick_night(R, x0, w, f):
    cv = R.cv
    rs = R.rng('bn', x0)
    top = rs.choice([20, 30, 40])
    wall(cv, 'brick', x0, top, w, FB - top, '#7a4a48', seed=hash((R.id, x0)) % 999)
    cornice(cv, x0, top, w, C('#b8a898'), h=5)
    n = max(2, int(w / 40))
    for fl in range(3):
        for k in range(n):
            wx = x0 + (w - n * 15) / (n + 1) * (k + 1) + 15 * k
            window(cv, wx, top + 14 + fl * 44, 15, 26, lit=rs.random() < 0.5, seed=hash((x0, fl, k)) % 999,
                   frame='#b8a898', glass=rs.choice([kit.WARM_GLASS, kit.TV_GLASS, kit.WARM_GLASS]))
    fire_escape(cv, x0 + w / 2 - 15, 30, [top + 44 + fl * 44 for fl in range(3)], bottom=FB - 30)
    # blade sign
    c = rs.choice(NEONS)
    bx = x0 + w - 18
    cv.rect(bx, 90, 14, 60, C('#1a1020'), ink=C('#0a0610'), iw=MAJOR)
    word = rs.choice(['HOTEL', 'BAR', 'EATS', 'TAXI'])
    for i, ch in enumerate(word):
        neon_text(cv, ch, bx + 7, 98 + i * 11, 7, C(c), tracking=0, glow=0.35)
    R.glow(bx + 7, 120, 40, c, 0.45, 'neon')
    door(cv, x0 + 20, FB, 18, 50, C('#2a2a3a'), lit=rs.random() < 0.5, seed=int(x0), frame='#5a4a50')
    poster(cv, x0 + 50, FB - 40, 13, 18, seed=hash((R.id, x0, 'p')) % 999, kind=rs.choice(['gig', 'missing', 'boxing']))
    tag(cv, x0 + 60, FB - 14, rs.choice(['SAINTS', 'NM', 'JETT']), C(rs.choice(NEONS)), size=6, seed=int(x0) % 99)
    R.light(x0 + w / 2, FB + 10, w * 0.5, 26, c, 0.08)


@facade("theater_marquee")
def f_theater_marquee(R, x0, w, f):
    cv = R.cv
    top = 20
    wall(cv, 'stone', x0, top, w, FB - top, '#9a8478', seed=1601)
    cornice(cv, x0, top, w, C('#d8c8b0'), h=6)
    # vertical blade sign ORPHEUM
    name = f.get('sign', 'ORPHEUM')
    bx = x0 + w / 2 - 16
    cv.rect(bx, top + 6, 32, 104, C('#2a1430'), ink=C('#0a0610'), iw=MAJOR)
    for i, ch in enumerate(name[:8]):
        neon_text(cv, ch, bx + 16, top + 18 + i * 12.5, 10, C('#f8e040'), tracking=0, glow=0.35)
    for k in range(10):
        for side in (bx + 2.5, bx + 29.5):
            cv.ellipse(side, top + 10 + k * 10, 0.9, 0.9, C('#fff0a0'), em=1.0)
    for side in (bx + 2.5, bx + 29.5):
        kit.log(cv, {'type': 'sign', 'rect': [round(side - 1.5, 1), top + 8.5, 3.0, 93.0], 'color': '#fff0a0',
                     'pattern': 'blink'})
    R.glow(bx + 16, top + 60, 60, '#f8e040', 0.55, 'neon')
    # marquee canopy with bulbs + letter board
    my = 128
    cv.fill_poly([(x0 + 10, my), (x0 + w - 10, my), (x0 + w - 2, my + 30), (x0 + 2, my + 30)], C('#c8302a'),
                 ink=C('#2a0a0a'), iw=MAJOR)
    cv.rect(x0 + 24, my + 4, w - 48, 20, C('#f4ecd8'), ink=C('#2a0a0a'), iw=DETAIL, em=1.0)
    cv.text('TONIGHT  -  THE GREY MAN', 'cond', 6.5, x0 + w / 2, my + 10, C('#1a1420'), 'mm', em=1.0)
    cv.text('FIGHT NITE  10 PM', 'cond', 5.5, x0 + w / 2, my + 18.5, C('#c8302a'), 'mm', em=1.0)
    for k in range(int((w - 20) / 5)):
        bxk = x0 + 12 + k * 5
        on = (k % 4) != 2
        cv.ellipse(bxk, my + 1.5, 1.0, 1.0, C('#fff0a0') if on else C('#8a6a30'), em=1.0 if on else 0.0)
        cv.ellipse(bxk, my + 28, 1.0, 1.0, C('#fff0a0') if (k % 4) != 0 else C('#8a6a30'), em=1.0)
    for by in (my + 0.2, my + 26.7):
        kit.log(cv, {'type': 'sign', 'rect': [round(x0 + 10.5, 1), round(by, 1), round(w - 21, 1), 2.6],
                     'color': '#fff0a0', 'pattern': 'chase'})
    R.glow(x0 + w / 2, my + 14, w * 0.6, '#ffe8a0', 0.45, 'neon')
    R.glow(x0 + w / 2, my + 40, w * 0.6, '#ffd890', 0.12, 'none', front=True)
    # entrance doors + poster cases + ticket booth
    for k in range(4):
        dxk = x0 + w / 2 - 60 + k * 30
        door(cv, dxk, FB, 22, 44, C('#5a2a2a'), lit=True, seed=1610 + k, frame='#d8c8a0', step=False, transom=False)
    for px in (x0 + 20, x0 + w - 56):
        cv.rect(px, my + 40, 36, 44, C('#d8c8a0'), ink=C('#2a1a14'), iw=MAJOR)
        cv.vgrad(px + 3, my + 43, 30, 38, [C('#e84a3a'), C('#3a1a4a')], em=0.9)
        cv.text('FIGHT', 'sign', 5, px + 18, my + 52, C('#f8e040'), 'mm', em=1.0)
        cv.text('NITE', 'sign', 5, px + 18, my + 60, C('#f4f0e8'), 'mm', em=1.0)
    light_pool(R, x0 + w / 2, FB + 10, w * 0.5, 16, '#ffe0a0', a=0.3)
    R.light(x0 + w / 2, FB + 16, w * 0.6, 40, '#ffe0a0', 0.3)


@facade("neon_shopfront")
def f_neon_shopfront(R, x0, w, f):
    s = f.get('sign', '')
    kind = {'PIZZA': 'pizza', 'LOUNGE': 'lounge', 'RECORDS': 'records', 'HOTEL': 'hotel'}.get(s, 'lounge')
    col = {'pizza': '#ff8a3a', 'lounge': '#ff4ab0', 'records': '#4ae0ff', 'hotel': '#c070ff'}[kind]
    rs = R.rng('ns', x0)
    shop_building(R, x0, w, f, 'brick', rs.choice(['#6a4a5a', '#5a4a48', '#7a4a40']), '#b8a898', top=rs.choice([30, 44]),
                  upper=2, sign_style='neon', neon_col=col, display=kind, seed=int(x0) % 97,
                  glass=[C('#ffe0c0'), C('#ffb090'), C('#c86a6a')] if kind == 'pizza' else None, lit_p=0.5)
    if kind == 'hotel':
        tag(R.cv, x0 + 20, FB - 14, 'VACANCY', C('#ff4a4a'), size=5, seed=3, a=0.0)
        neon_text(R.cv, 'VACANCY', x0 + w / 2, 118, 6, C('#ff4a4a'), tracking=0.3, glow=0.4)
        R.glow(x0 + w / 2, 118, 30, '#ff4a4a', 0.4, 'neon')


@facade("pharmacy")
def f_pharmacy(R, x0, w, f):
    cv = R.cv
    dx, gy0 = shop_building(R, x0, w, f, 'stucco', '#c8c0a8', '#2a6a5a', top=40, upper=2, sign_style='lightbox',
                            sign_bg='#2a7a6a', sign_fg='#f4fff8', display='pharmacy',
                            glass=[C('#f4fffc'), C('#d0f0e8'), C('#a0c8c0')], seed=17)
    cx, cy = x0 + w - 24, 110
    cv.rect(cx - 10, cy - 10, 20, 20, C('#141c1a'), ink=C('#060a08'), iw=MAJOR)
    for (ddx, ddy, ww, hh) in ((-2.5, -8, 5, 16), (-8, -2.5, 16, 5)):
        cv.rect(cx + ddx, cy + ddy, ww, hh, C('#3aff8a'), em=1.0)
    R.glow(cx, cy, 30, '#3aff8a', 0.6, 'neon')
    poster(cv, x0 + 20, FB - 36, 12, 16, seed=1701, kind='missing')


@facade("arcade_front")
def f_arcade_front(R, x0, w, f):
    cv = R.cv
    top = 36
    wall(cv, 'stucco', x0, top, w, FB - top, '#2a2040', seed=1801, soot=0.2)
    cv.rect(x0, top, w, 4, C('#4ae0ff'), em=1.0)
    kit.log(cv, {'type': 'sign', 'rect': [x0, top, w, 4.0], 'color': '#4ae0ff', 'pattern': 'chase'})
    R.glow(x0 + w / 2, top + 2, w * 0.5, '#4ae0ff', 0.35, 'neon')
    # big starburst sign
    cx, cy = x0 + w / 2, top + 40
    pts = []
    for k in range(24):
        r = 46 if k % 2 == 0 else 30
        a = k * math.pi / 12
        pts.append((cx + math.cos(a) * r * 1.6, cy + math.sin(a) * r * 0.7))
    cv.fill_poly(pts, C('#2a1440'), ink=C('#ff4ab0'), iw=1.2, em=0.6)
    neon_text(cv, 'STARLIGHT', cx, cy - 6, 15, C('#f8e040'), tracking=0.8, glow=0.5)
    neon_text(cv, 'ARCADE', cx, cy + 12, 11, C('#ff4ab0'), tracking=1.4, glow=0.5)
    R.glow(cx, cy, 120, '#ff4ab0', 0.55, 'neon')
    R.glow(cx, cy - 6, 70, '#f8e040', 0.35, 'neon')
    # glass front: cabinets glowing inside
    dx = door_x(R, x0, w)
    gy0, gy1 = top + 96, FB - 4
    cv.rect(x0 + 10, gy0 - 2, w - 20, gy1 - gy0 + 4, C('#141020'), ink=C('#06040a'), iw=MAJOR)
    cv.vgrad(x0 + 12, gy0, w - 24, gy1 - gy0, [C('#3a1a5a'), C('#1a0e2a')], em=0.9)
    rs = R.rng('cab')
    for k in range(int((w - 30) / 26)):
        bxk = x0 + 18 + k * 26
        if abs(bxk + 10 - dx) < 24:
            continue
        cv.rect(bxk, gy0 + 14, 20, gy1 - gy0 - 14, C('#1e1630'), ink=C('#06040a'), iw=DETAIL, em=0.8)
        c = rs.choice(NEONS)
        cv.rect(bxk + 3, gy0 + 20, 14, 12, C(c), em=1.0)
        cv.rect(bxk + 2, gy0 + 15, 16, 4, C(rs.choice(NEONS)), em=1.0)
        R.glow(bxk + 10, gy0 + 26, 14, c, 0.25, 'neon')
    door(cv, dx - 12, FB, 24, 50, C('#2a1a3a'), lit=True, seed=1802, frame='#4ae0ff', step=False, transom=False)
    for k, c in enumerate(('#ff4ab0', '#4ae0ff')):
        cv.rect(x0 + 10, gy0 - 8 + k * 3, w - 20, 1.2, C(c), em=1.0)
    kit.log(cv, {'type': 'sign', 'rect': [x0 + 10, gy0 - 8.5, w - 20, 5.4], 'color': '#ff4ab0', 'pattern': 'chase'})
    tag(cv, x0 + 20, FB - 12, 'JETT', C('#4ae0ff'), size=6, seed=7)
    light_pool(R, cx, FB + 10, w * 0.5, 14, '#c070ff', a=0.3)
    R.light(cx, FB + 16, w * 0.6, 40, '#d080ff', 0.3)


@facade("fire_escape_wall")
def f_fire_escape_wall(R, x0, w, f):
    cv = R.cv
    rs = R.rng('few', x0)
    wall(cv, 'brick', x0, 10, w, FB - 10, '#6a4446', seed=1901)
    floors = [30, 74, 118]
    for fl, fy in enumerate(floors):
        for k in range(int(w / 50)):
            wx = x0 + 20 + k * 50
            window(cv, wx, fy, 16, 28, lit=rs.random() < 0.5, seed=hash((fl, k, x0)) % 999, frame='#a89888',
                   glass=rs.choice([kit.WARM_GLASS, kit.TV_GLASS]))
    for k in range(int(w / 200)):
        fire_escape(cv, x0 + 40 + k * 200, 50, [fy + 34 for fy in floors], bottom=FB - 30)
    graffiti_piece(cv, x0 + w * 0.45, 160, 120, 40, 'SAINTS', '#4ae0ff', '#c070ff', seed=11)
    for k in range(3):
        ac_unit(cv, x0 + 30 + k * 130, 64 + k * 40, 11, 7)
    string_lights(cv, x0, 150, x0 + w, 146, sag=16, step=8, seed=5, cols=[C(c) for c in NEONS[:4]])
    poster(cv, x0 + 20, FB - 40, 13, 18, seed=1902, kind='missing')
    poster(cv, x0 + w - 40, FB - 36, 14, 18, seed=1903, kind='gig')
    R.light(x0 + w / 2, FB + 10, w, 30, '#ff7ad0', 0.06)


@facade("alley_walls")
def f_alley_walls(R, x0, w, f):
    cv = R.cv
    wall(cv, 'brick', x0, 0, w, FB, '#5a3e44', seed=2001, soot=0.4)
    # back fence with a gap of night city beyond
    cv.rect(x0 + 200, 40, 240, 150, C('#1a1430'), em=0.0)
    chainlink(cv, x0 + 200, 40, 240, FB - 40, col='#7a7a8a')
    cv.radial(x0 + 320, 120, 120, 80, C('#c060ff'), a=0.25, mode='add')
    # hand-painted race banner
    name = f.get('sign', 'ALLEY CAT CUP')
    cv.fill_poly([(x0 + 170, 22), (x0 + 470, 22), (x0 + 466, 44), (x0 + 174, 44)], C('#f4f0e4'), ink=C('#1a1420'),
                 iw=MAJOR)
    painted_text(cv, name, x0 + 320, 33.5, 11, C('#c8302a'), tracking=0.6, shadow=False)
    cv.line([(x0 + 170, 22), (x0 + 120, 4)], 0.5, C('#1a1420'))
    cv.line([(x0 + 470, 22), (x0 + 520, 4)], 0.5, C('#1a1420'))
    # start line + chequered flags
    for k in range(10):
        cv.rect(x0 + 180 + k * 28, 46, 14, 6, C('#1a1420') if k % 2 else C('#f4f0e8'))
    # back windows of the flats and the kitchen that share the alley (lives behind the glass)
    for (wx, wy, lit, gl) in ((x0 + 36, 6, True, kit.WARM_GLASS), (x0 + 588, 8, False, None),
                              (x0 + 92, 158, True, kit.TV_GLASS), (x0 + 500, 158, True, kit.WARM_GLASS)):
        window(cv, wx, wy, 14, 22, lit=lit, seed=int(wx * 3 + wy), frame='#8a7a78', glass=gl,
               interior='tv' if gl is kit.TV_GLASS else None, curtains=False if wy > 100 else None)
    string_lights(cv, x0, 70, x0 + w, 66, sag=18, step=8, seed=9, cols=[C(c) for c in NEONS[:4]])
    graffiti_piece(cv, x0 + 20, 90, 150, 50, 'MO', '#f8e040', '#ff4ab0', seed=21)
    graffiti_piece(cv, x0 + 470, 100, 150, 46, 'CATS', '#8aff8a', '#4ae0ff', seed=22)
    # neon back door
    door(cv, x0 + 560, FB, 22, 52, C('#2a2a3a'), lit=True, seed=2002, frame='#ff4ab0', step=True)
    neon_text(cv, 'BIG MO', x0 + 571, FB - 62, 6, C('#ff4ab0'), tracking=0.3, glow=0.4)
    R.glow(x0 + 571, FB - 62, 30, '#ff4ab0', 0.5, 'neon')
    for k, c in enumerate(('#4ae0ff', '#ff4ab0')):
        lx = x0 + 60 + k * 400
        cv.rect(lx - 3, 140, 6, 4, C('#2a2a34'))
        cv.rect(lx - 2, 144, 4, 2, C(c), em=1.0)
        R.glow(lx, 146, 30, c, 0.5, 'neon')
        R.light(lx, 270, 90, 60, c, 0.16)
    R.ambient.append({"type": "steam", "x": float(x0 + 120), "y": float(FB - 6), "rate": 0.6})
    R.ambient.append({"type": "drip", "x": float(x0 + 400), "y": 60.0, "rate": 0.4})


@facade("rooftop_edge")
def f_rooftop_edge(R, x0, w, f):
    cv = R.cv
    rs = R.rng('roofe', x0)
    # back parapet of this roof (the city skyline beyond comes from the district layers)
    pm = M(C('#7a5a52'))
    kit.brick_wall(cv, x0, FB - 16, w, 16, pm.b, seed=int(x0) % 99, soot=0.2)
    cv.rect(x0, FB - 18, w, 3, C('#b0a090'), ink=C('#2a2026'), iw=DETAIL)
    sign = f.get('sign')
    if sign:
        # rooftop billboard on a steel frame with neon
        bx, bw = x0 + w / 2 - 110, 220
        for k in range(5):
            cv.rect(bx + 10 + k * 50, 100, 2, FB - 118, C('#2a2a34'))
        cv.line([(bx + 10, FB - 18), (bx + 210, 100)], 0.8, C('#2a2a34'))
        cv.line([(bx + 10, 100), (bx + 210, FB - 18)], 0.8, C('#2a2a34'))
        cv.rect(bx, 40, bw, 62, C('#e8e0d0'), ink=C('#141018'), iw=MAJOR)
        cv.vgrad(bx + 3, 43, bw - 6, 56, [C('#ff6a3a'), C('#c8302a')], em=0.7)
        neon_text(cv, sign, bx + bw / 2, 66, 18, C('#f8f0e0'), tracking=1.0, glow=0.4)
        cv.ellipse(bx + 30, 70, 12, 16, C('#f8e8c0'), ink=C('#3a1a10'), iw=MAJOR, em=0.7)
        cv.text('ICE COLD', 'cond', 6, bx + bw / 2, 88, C('#f8e040'), 'mm', em=1.0)
        for k in range(4):
            lx = bx + 20 + k * 60
            cv.rect(lx, 36, 2, 6, C('#2a2a34'))
            cv.radial(lx + 1, 44, 16, 12, C('#fff0c0'), a=0.3, mode='add')
        R.glow(bx + bw / 2, 70, 130, '#ff6a3a', 0.4, 'neon')
    else:
        # water tank on stilts + roof bulkhead door
        tx = x0 + rs.uniform(80, w - 160)
        tm = M(C('#7a5a40'))
        for k in range(4):
            cv.rect(tx + 4 + k * 14, 130, 2, FB - 148, C('#2a2026'))
        cv.rect(tx, 70, 50, 62, tm.b, ink=tm.i, iw=MAJOR)
        for k in range(1, 4):
            cv.rect(tx, 70 + k * 15, 50, 1.2, C('#3a2a20'))
        cv.fill_poly([(tx - 3, 70), (tx + 25, 52), (tx + 53, 70)], C('#4a4048'), ink=C('#140c10'), iw=MAJOR)
        cv.hgrad(tx, 70, 50, 62, [tm.l, tm.b, tm.s], mode='atop')
        hx = x0 + rs.uniform(w * 0.6, w - 60)
        kit.brick_wall(cv, hx, 140, 50, FB - 158, C('#6a4a44'), seed=int(hx) % 99)
        cv.rect(hx - 3, 136, 56, 5, C('#4a4048'), ink=C('#140c10'), iw=MAJOR)
        door(cv, hx + 15, FB - 18, 20, 36, C('#3a4a5a'), lit=True, seed=int(hx), frame='#2a2026', step=False,
             transom=False)
        cv.rect(hx + 22, 142, 6, 3, C('#fff0b0'), em=1.0)
        R.glow(hx + 25, 143, 20, '#fff0b0', 0.4, 'none')
        R.glow(hx + 25, FB - 30, 30, '#ffd890', 0.25, 'none')
        for k in range(3):
            cv.line([(x0 + 20 + k * 3, FB - 18), (x0 + 22 + k * 3, 90)], 0.5, C('#2a2a34'))
        cable(cv, x0, 120, x0 + w, 128, sag=12, w=0.5, col='#140e18')
        R.ambient.append({"type": "pigeons", "x": float(tx), "y": 51.0, "w": 50})
    R.light(x0 + w / 2, FB + 20, w * 0.6, 50, '#ff8ad0', 0.06)
