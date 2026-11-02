"""Backstreet Oath env v2 -- interior rooms (wall 0..196 u, floor below) and shared interior props-in-art."""
import math

import numpy as np

from raster import C, mix, shade, light, ink_of, value_noise, rng_of
import kit
from kit import M, MAJOR, DETAIL, window, door, poster, tag, neon_text, painted_text, cable
from room import INT_WALL_BOTTOM as WB, H, light_pool
from common import facade, FACADES, lantern, chainlink, big_door, stone_wall


def room_shell(R, x0, w, upper, lower, wall_kind='plaster', trim='#3a2a24', rail_y=120, seed=1):
    cv = R.cv
    um = M(C(upper))
    if wall_kind == 'brick':
        kit.brick_wall(cv, x0, 0, w, WB, C(upper), seed=seed, soot=0.15)
    elif wall_kind == 'block':
        kit.brick_wall(cv, x0, 0, w, WB, C(upper), seed=seed, bw=16, bh=8, var=0.04, mortar=light(C(upper), 1.0),
                       soot=0.1, accent=0.0)
    elif wall_kind == 'tile':
        mk = cv.rect(x0, 0, w, WB, um.b)
        xx = x0
        while xx < x0 + w:
            cv.rect(xx, 0, 0.5, WB, um.s, mode='atop')
            xx += 8
        yy = 0
        while yy < WB:
            cv.rect(x0, yy, w, 0.5, um.s, mode='atop')
            yy += 8
        cv.vgrad(x0, 0, w, WB, [C('#ffffff', 40), C('#ffffff', 0)], mode='atop')
    elif wall_kind == 'wood':
        mk = cv.rect(x0, 0, w, rail_y, um.b)
        xx = x0
        while xx < x0 + w:
            cv.rect(xx, 0, 0.5, rail_y, um.s, a=0.6, mode='atop')
            xx += 10
        kit.weather(cv, x0, 0, w, rail_y, seed, soot=0.0, blotch=0.12, streak=False)
    elif wall_kind == 'paper':
        mk = cv.rect(x0, 0, w, rail_y, um.b)
        xx = x0
        k = 0
        while xx < x0 + w:
            cv.rect(xx, 0, 3, rail_y, um.l if k % 2 else um.s, a=0.25, mode='atop')
            xx += 6
            k += 1
        kit.weather(cv, x0, 0, w, rail_y, seed, soot=0.0, blotch=0.15, streak=False)
    elif wall_kind == 'panel':
        mk = cv.rect(x0, 0, w, WB, um.b)
        xx = x0
        while xx < x0 + w:
            cv.rect(xx, 12, 0.8, WB - 12, um.d, mode='atop')
            cv.rect(xx + 0.8, 12, 0.5, WB - 12, um.l, mode='atop', a=0.6)
            for yy in (40, 100, 160):
                cv.ellipse(xx + 3, yy, 0.5, 0.5, um.d, mode='atop')
            xx += 40
    else:
        mk = cv.rect(x0, 0, w, WB, um.b)
        kit.weather(cv, x0, 0, w, WB, seed, soot=0.1, blotch=0.12, streak=False)
    if wall_kind in ('wood', 'paper', 'plaster'):
        lm = M(C(lower))
        cv.rect(x0, rail_y, w, WB - rail_y, lm.b)
        xx = x0
        while xx < x0 + w:
            cv.rect(xx + 2, rail_y + 6, 18, WB - rail_y - 12, lm.s, ink=lm.d, iw=DETAIL)
            cv.rect(xx + 2, rail_y + 6, 18, 0.6, lm.l, mode='atop')
            xx += 22
        cv.rect(x0, rail_y - 2, w, 3, C(trim), ink=ink_of(C(trim)), iw=DETAIL)
        cv.rect(x0, rail_y - 2, w, 0.8, light(C(trim), 1.5), mode='atop')
    # ceiling soffit, baseboard
    cv.rect(x0, 0, w, 8, shade(um.b, 1.4))
    cv.rect(x0, 8, w, 1, light(um.b, 1.0), a=0.5)
    cv.rect(x0, WB - 4, w, 4, C(trim), ink=ink_of(C(trim)), iw=DETAIL)
    cv.vgrad(x0, 8, w, 30, [C('#140c18', 70), C('#140c18', 0)], mode='atop')


def wall_window(R, x, y, w, h, round_=False, view='street', blinds=False):
    cv = R.cv
    fm = M(C('#d8d4c8'))
    if round_:
        cv.ellipse(x + w / 2, y + h / 2, w / 2 + 3, h / 2 + 3, fm.b, ink=fm.i, iw=MAJOR)
        mk = cv.ellipse_mask(x + w / 2, y + h / 2, w / 2, h / 2)
    else:
        cv.rect(x - 3, y - 3, w + 6, h + 6, fm.b, ink=fm.i, iw=MAJOR)
        mk = cv.rect_mask(x, y, w, h)
    sky = {'street': [C('#f8c890'), C('#e88a6a')], 'canal': [C('#a8d0e0'), C('#f8e0a8')],
           'night': [C('#1a1a3a'), C('#4a2a5a')], 'rain': [C('#5a7078'), C('#3a4a52')],
           'yard': [C('#8a9aac'), C('#d8b890')]}[view]
    cv.vgrad(x, y, w, h, sky, mk=mk, em=1.0)
    rs = rng_of('ww', x, y)
    if view == 'canal':
        for k in range(int(w / 12) + 1):
            hx = x + k * 12
            c = C(rs.choice(['#e8a060', '#c86a5a', '#e8d8b8', '#7aa8b0', '#b07a9a']))
            hy = y + h * 0.45 + rs.uniform(-6, 2)
            pm = cv.poly_mask([(hx, y + h * 0.75), (hx, hy), (hx + 5, hy - 6), (hx + 10, hy), (hx + 10, y + h * 0.75)])
            cv.paint(pm, c, mode='atop', em=1.0)
        wm = cv.rect_mask(x, y + h * 0.75, w, h * 0.25)
        cv.paint(wm, C('#3a8a94'), mode='atop', em=1.0)
    elif view in ('street', 'night', 'yard'):
        bc = {'street': C('#6a3a48'), 'night': C('#140c24'), 'yard': C('#4a4a5a')}[view]
        for k in range(int(w / 16) + 1):
            bx = x + k * 16 + rs.uniform(-3, 3)
            bt = y + h * rs.uniform(0.2, 0.5)
            pm = cv.poly_mask([(bx, y + h), (bx, bt), (bx + 14, bt), (bx + 14, y + h)])
            cv.paint(pm, bc, mode='atop', em=1.0)
            for j in range(4):
                wy = bt + 4 + j * 8
                if wy < y + h - 4 and rs.random() < 0.6:
                    pm2 = cv.rect_mask(bx + 3, wy, 3, 4)
                    cv.paint(pm2, C(rs.choice(['#ffd88a', '#ff6ab0', '#6ae0ff']) if view == 'night' else '#ffd88a'),
                             mode='atop', em=1.0)
        if view == 'yard':
            R.ambient.append({"type": "smoke", "x": float(x + w * 0.6), "y": float(y + h * 0.3), "rate": 0.3})
    elif view == 'rain':
        for k in range(int(w * h / 30)):
            px, py = rs.uniform(x, x + w), rs.uniform(y, y + h)
            pm = cv.line_mask([(px, py), (px - 0.6, py + 3)], 0.3)
            cv.paint(pm, C('#c8dce0'), a=0.5, mode='atop', em=1.0)
    if not round_:
        cv.rect(x + w / 2 - 1, y, 2, h, fm.b, ink=fm.i, iw=DETAIL)
        cv.rect(x, y + h / 2 - 1, w, 2, fm.b, ink=fm.i, iw=DETAIL)
        cv.rect(x - 4, y + h + 3, w + 8, 2.5, fm.b, ink=fm.i, iw=DETAIL)
    cv.paint(mk, C('#ffffff'), a=0.08, mode='atop')
    if blinds:
        yy = y
        while yy < y + h * 0.4:
            cv.rect(x, yy, w, 1.2, C('#e8e0c8'))
            cv.rect(x, yy + 1.2, w, 0.4, C('#8a8070'))
            yy += 2
    col = {'street': '#ffb080', 'canal': '#e8f0d8', 'night': '#c070ff', 'rain': '#a8c8d0', 'yard': '#d8d0c0'}[view]
    R.glow(x + w / 2, y + h / 2, max(w, h) * 0.8, col, 0.22, 'none')
    R.light(x + w / 2, 250, w * 1.2, 60, col, 0.08)


def pendant(R, x, y, col='#c8343a', lantern_=False, lantern=False, length=24, warm='#ffe0a0'):
    cv = R.cv
    if lantern or lantern_:
        cv.rect(x - 0.3, y, 0.6, length, C('#2a2026'))
        from common import lantern as _lan
        _lan(R, x, y + length + 4, col, 4)
        R.glow(x, y + length + 4, 26, '#ff8a5a', 0.4, 'flame')
        R.light(x, 260, 50, 40, '#ffb070', 0.12)
        return
    cv.rect(x - 0.4, y, 0.8, length, C('#2a2430'))
    m = M(C(col))
    cv.fill_poly([(x - 7, y + length + 6), (x + 7, y + length + 6), (x + 3, y + length), (x - 3, y + length)], m.b,
                 ink=m.i, iw=DETAIL)
    cv.ellipse(x, y + length + 6.5, 4, 1.2, C('#fff4d0'), em=1.0)
    cv.radial(x, y + length + 18, 24, 26, C(warm), a=0.16, mode='add')
    R.glow(x, y + length + 7, 28, warm, 0.42, 'none')
    R.light(x, 262, 46, 40, warm, 0.13)


def fluor(R, x, y, w=40, col='#e8fff8', flicker='fluor'):
    cv = R.cv
    cv.rect(x - w / 2, y, w, 3, C('#b8bcc0'), ink=C('#3a3a40'), iw=DETAIL)
    cv.rect(x - w / 2 + 2, y + 2, w - 4, 1.5, C(col), em=1.0)
    cv.radial(x, y + 10, w * 0.7, 18, C(col), a=0.18, mode='add')
    R.glow(x, y + 3, w * 0.9, col, 0.4, flicker)
    R.light(x, 270, w * 1.6, 60, col, 0.10)


def menu_board(R, x, y, w, h, title, price, bg='#1e1a22', fg='#f4f0e8'):
    cv = R.cv
    cv.rect(x, y, w, h, C(bg), ink=C('#2a1a14'), iw=MAJOR)
    cv.text(title, 'cond', h * 0.28, x + w / 2, y + h * 0.36, C(fg), 'mm')
    cv.text(price, 'cond', h * 0.26, x + w / 2, y + h * 0.72, shade(C(fg), 0.5) if bg != '#1e1a22' else C('#ffd060'),
            'mm')


def shelf_jars(R, x, y, w, rows=2):
    cv = R.cv
    rs = rng_of('jars', x, y)
    for r in range(rows):
        sy = y - r * 22
        cv.rect(x, sy, w, 2.5, C('#6a4a2a'), ink=C('#1e120c'), iw=DETAIL)
        xx = x + 3
        while xx < x + w - 6:
            jw = rs.uniform(4, 7)
            jh = rs.uniform(6, 14)
            c = C(rs.choice(['#e8a040', '#c84a3a', '#5a8a4a', '#e8d8a0', '#8a5a3a', '#4a7aa8']))
            cv.rect(xx, sy - jh, jw, jh, c, ink=shade(c, 1.8), iw=DETAIL)
            cv.rect(xx + 0.5, sy - jh, jw * 0.3, jh, light(c, 1.5), a=0.5)
            xx += jw + rs.uniform(1, 3)


def community_board(R, x, y, w, h, seed=0):
    cv = R.cv
    cv.rect(x, y, w, h, C('#b88a5a'), ink=C('#3a2414'), iw=MAJOR)
    cv.rect(x + 2, y + 2, w - 4, h - 4, C('#c89a68'))
    kinds = ['missing', 'evict', 'gig', 'lost_cat', 'boxing', 'plain']
    k = 0
    xx = x + 4
    while xx < x + w - 10:
        pw = min(14, x + w - 4 - xx)
        poster(cv, xx, y + 4 + (k % 2) * 4, pw - 2, h - 14, seed=hash((R.id, x, k)) % 999, kind=kinds[(k + seed) % 6])
        xx += pw + 1
        k += 1


def bookcase(R, x, y, w, h):
    cv = R.cv
    m = M(C('#5a3a22'))
    cv.rect(x, y, w, h, m.b, ink=m.i, iw=MAJOR)
    rs = rng_of('bc', x)
    rows = int(h / 26)
    for r in range(rows):
        sy = y + 4 + r * (h - 6) / rows
        sh_ = (h - 6) / rows
        cv.rect(x + 3, sy, w - 6, sh_ - 2.5, shade(m.b, 1.5))
        xx = x + 4
        while xx < x + w - 5:
            bw = rs.uniform(1.6, 3.2)
            bh = rs.uniform(sh_ * 0.55, sh_ - 4)
            c = C(rs.choice(['#a83a32', '#2e5a8a', '#3a7a4a', '#c8a040', '#6a3a6a', '#d8d0b8', '#2a2a30']))
            lean = rs.random() < 0.05
            cv.rect(xx, sy + sh_ - 2.5 - bh, bw, bh, c, ink=shade(c, 1.7), iw=0.3)
            cv.rect(xx + bw * 0.2, sy + sh_ - 2.5 - bh + 2, bw * 0.6, 0.6, C('#e8d8a0'), a=0.6)
            xx += bw + (2.5 if lean else 0.25)
        cv.rect(x + 2, sy + sh_ - 2.5, w - 4, 2.5, m.l, ink=m.i, iw=DETAIL)


def tool_pegboard(R, x, y, w, h):
    cv = R.cv
    cv.rect(x, y, w, h, C('#c8a878'), ink=C('#3a2a1a'), iw=MAJOR)
    for yy in np.arange(y + 3, y + h, 4):
        for xx in np.arange(x + 3, x + w, 4):
            cv.ellipse(xx, yy, 0.35, 0.35, C('#8a6a48'))
    rs = rng_of('tools', x)
    xx = x + 6
    while xx < x + w - 6:
        t = rs.choice(['wrench', 'hammer', 'saw', 'screw', 'pliers'])
        c = C('#8a8e9a')
        if t == 'wrench':
            cv.line([(xx, y + 8), (xx, y + 30)], 1.6, c, ink=C('#2a2a34'), iw=0.4)
            cv.ellipse(xx, y + 7, 2.4, 2.4, c, ink=C('#2a2a34'), iw=0.4)
        elif t == 'hammer':
            cv.line([(xx, y + 10), (xx, y + 30)], 1.4, C('#a8743e'), ink=C('#2a1a10'), iw=0.4)
            cv.rect(xx - 4, y + 7, 8, 3.5, c, ink=C('#2a2a34'), iw=0.4)
        elif t == 'saw':
            cv.fill_poly([(xx - 3, y + 8), (xx + 4, y + 8), (xx + 2, y + 34), (xx - 3, y + 34)], C('#c8ccd8'),
                         ink=C('#2a2a34'), iw=0.4)
            cv.rect(xx - 4, y + 4, 8, 5, C('#c83a2a'), ink=C('#2a1010'), iw=0.4)
        elif t == 'screw':
            cv.line([(xx, y + 16), (xx, y + 30)], 0.6, c)
            cv.rect(xx - 1.2, y + 8, 2.4, 8, C(rs.choice(['#e8c030', '#c83a2a', '#3a6ac8'])), ink=C('#201810'), iw=0.4)
        else:
            cv.line([(xx - 2, y + 30), (xx, y + 12), (xx + 2, y + 30)], 1.0, C('#c83a2a'))
        xx += rs.uniform(9, 13)


@facade("garage_interior")
def f_garage_interior(R, x0, w, f):
    cv = R.cv
    room_shell(R, x0, w, '#a8a49a', '#5a5450', wall_kind='block', trim='#3a3438')
    cv.rect(x0, 110, w, 4, C('#3a6aa8'), a=0.8)
    # roll-up door with a window strip (right)
    big_door(cv, x0 + 440, 172, 150, 130, '#b8b4a8', kind='roller', seed=12)
    cv.vgrad(x0 + 450, 68, 130, 10, [C('#f8c890'), C('#e88a6a')], em=1.0)
    for k in range(1, 5):
        cv.rect(x0 + 450 + k * 26, 68, 1.2, 10, C('#7a7a80'))
    # car on a lift (the garage's current job)
    lift = M(C('#c8302a'))
    cv.rect(x0 + 170, 110, 6, 86, lift.b, ink=lift.i, iw=MAJOR)
    cv.rect(x0 + 330, 110, 6, 86, lift.b, ink=lift.i, iw=MAJOR)
    cv.rect(x0 + 160, 106, 186, 5, C('#4a4a54'), ink=C('#141018'), iw=MAJOR)
    car = M(C('#e8b830'))
    cv.fill_poly([(x0 + 170, 106), (x0 + 172, 88), (x0 + 200, 84), (x0 + 220, 66), (x0 + 290, 64), (x0 + 314, 82),
                  (x0 + 340, 86), (x0 + 344, 106)], car.b, ink=car.i, iw=MAJOR)
    cv.vgrad(x0 + 170, 64, 174, 42, [car.h, car.l, car.b, car.s], mode='atop', a=0.8)
    cv.fill_poly([(x0 + 224, 69), (x0 + 254, 68), (x0 + 254, 82), (x0 + 208, 83)], C('#5a7a9a'), ink=car.d, iw=DETAIL)
    cv.fill_poly([(x0 + 258, 68), (x0 + 288, 67), (x0 + 306, 82), (x0 + 258, 82)], C('#5a7a9a'), ink=car.d, iw=DETAIL)
    for wx in (x0 + 200, x0 + 312):
        cv.ellipse(wx, 106, 11, 11, C('#2a2a30'), ink=C('#0e0a10'), iw=MAJOR)
        cv.ellipse(wx, 106, 5, 5, C('#a8acb8'))
    tool_pegboard(R, x0 + 14, 30, 130, 60)
    cv.rect(x0 + 360, 24, 64, 30, C('#2a5a8a'), ink=C('#0e1a2a'), iw=MAJOR)
    painted_text(cv, 'QUINN GARAGE', x0 + 392, 39, 6, C('#f4e8c0'), shadow=False)
    poster(cv, x0 + 150, 140, 16, 22, seed=401, kind='missing')
    poster(cv, x0 + 380, 70, 18, 24, seed=402, kind='boxing')
    for k in range(3):
        fluor(R, x0 + 110 + k * 210, 10, 46)
    # tyre rack + oil cans shelf
    for k in range(3):
        cv.ellipse(x0 + 30 + k * 18, 176, 9, 9, C('#2a2a30'), ink=C('#0e0a10'), iw=MAJOR)
        cv.ellipse(x0 + 30 + k * 18, 176, 4, 4, C('#5a5a64'))
    R.light(x0 + 515, 230, 90, 50, '#ffb080', 0.08)


@facade("gym_interior")
def f_gym_interior(R, x0, w, f):
    cv = R.cv
    room_shell(R, x0, w, '#b86a4a', '#3a3a5a', wall_kind='brick', trim='#2a2a3a', seed=31)
    # big banner
    sm = M(C('#c8302a'))
    cv.fill_poly([(x0 + 160, 22), (x0 + 480, 22), (x0 + 476, 46), (x0 + 164, 46)], sm.b, ink=sm.i, iw=MAJOR)
    painted_text(cv, f.get('sign', 'NOBODY FIGHTS ALONE'), x0 + 320, 34.5, 10, C('#f4f0e8'), tracking=0.6)
    # high windows
    for k in range(3):
        wall_window(R, x0 + 40 + k * 230, 54, 60, 34, view='street')
    # boxing ring corner + ropes in the back
    for k, c in enumerate(('#c8302a', '#f4f0e8', '#2a4a9a')):
        cv.line([(x0 + 220, 140 + k * 10), (x0 + 600, 140 + k * 10)], 1.2, C(c), ink=C('#1a1220'), iw=0.4)
    cv.rect(x0 + 216, 128, 8, 68, C('#c8302a'), ink=C('#2a0a0a'), iw=MAJOR)
    cv.rect(x0 + 216, 180, 400, 16, C('#2a3a6a'), ink=C('#0e1428'), iw=MAJOR)
    # trophy shelf + photos
    cv.rect(x0 + 30, 120, 110, 3, C('#6a4a2a'), ink=C('#1e120c'), iw=DETAIL)
    rs = R.rng('troph')
    for k in range(7):
        tx = x0 + 38 + k * 15
        hh = rs.uniform(10, 18)
        cv.rect(tx - 2, 120 - 3, 4, 3, C('#3a2a1a'))
        cv.fill_poly([(tx - 3, 117 - hh * 0.4), (tx + 3, 117 - hh * 0.4), (tx + 1, 117 - 3), (tx - 1, 117 - 3)],
                     C('#e8c040'), ink=C('#5a4010'), iw=0.4)
        cv.ellipse(tx, 117 - hh * 0.5, 3.5, 2, C('#f0d060'), ink=C('#5a4010'), iw=0.4)
    for k in range(3):
        cv.rect(x0 + 30 + k * 36, 132, 28, 20, C('#5a3a28'), ink=C('#1a1220'), iw=DETAIL)
        cv.vgrad(x0 + 32 + k * 36, 134, 24, 16, [C('#d8c8a0'), C('#9a8a70')])
    poster(cv, x0 + 150, 96, 20, 28, seed=501, kind='boxing')
    poster(cv, x0 + 520, 96, 14, 18, seed=502, kind='missing')
    tag(cv, x0 + 560, 124, 'BENNY', C('#f4f0e8'), size=5, seed=9, a=0.5)
    for k in range(3):
        fluor(R, x0 + 110 + k * 210, 10, 44, col='#fff4e0')


@facade("canteen_interior")
def f_canteen_interior(R, x0, w, f):
    cv = R.cv
    room_shell(R, x0, w, '#b8d0b0', '#5a7a5a', wall_kind='tile', trim='#3a4a3a', seed=41)
    cv.rect(x0, 118, w, 78, C('#6a8a6a'))
    cv.rect(x0, 118, w, 2, C('#2a3a2a'))
    wall_window(R, x0 + 30, 34, 90, 60, view='yard')
    # menu board + clock + union notice board
    cv.rect(x0 + 300, 24, 140, 50, C('#22262a'), ink=C('#0a0c0e'), iw=MAJOR)
    painted_text(cv, 'YARD CANTEEN', x0 + 370, 32, 6, C('#f8d860'), shadow=False)
    for k, (a, b) in enumerate((('STEW', '1.10'), ('PIE & MASH', '1.40'), ('TEA', '0.20'), ('SANDWICH', '0.90'))):
        cv.text(a, 'cond', 4, x0 + 310, 42 + k * 8, C('#f4f0e8'), 'lm')
        cv.text(b, 'cond', 4, x0 + 430, 42 + k * 8, C('#ffd060'), 'rm')
    cv.ellipse(x0 + 480, 40, 9, 9, C('#f4f0e4'), ink=C('#2a2026'), iw=MAJOR)
    cv.line([(x0 + 480, 40), (x0 + 484, 36)], 0.6, C('#2a2026'))
    community_board(R, x0 + 520, 44, 90, 52, seed=2)
    cv.rect(x0 + 524, 34, 82, 9, C('#c8302a'), ink=C('#2a0a0a'), iw=DETAIL)
    cv.text('IRONWORKERS LOCAL 9', 'cond', 3.4, x0 + 565, 38.5, C('#f4f0e8'), 'mm')
    # steam trays on the back counter
    cv.rect(x0 + 200, 150, 260, 46, C('#c8ccd0'), ink=C('#3a3a44'), iw=MAJOR)
    for k in range(5):
        cv.rect(x0 + 210 + k * 50, 144, 40, 8, C('#9aa0a8'), ink=C('#3a3a48'), iw=DETAIL)
        cv.ellipse(x0 + 230 + k * 50, 145, 15, 2, C(['#a8603a', '#e8c070', '#7a9a5a', '#c89a6a', '#b84a3a'][k]))
        R.ambient.append({"type": "steam", "x": float(x0 + 230 + k * 50), "y": 140.0, "rate": 0.3})
    for k in range(3):
        fluor(R, x0 + 110 + k * 210, 10, 48, col='#e8fff0')


@facade("switch_interior")
def f_switch_interior(R, x0, w, f):
    cv = R.cv
    room_shell(R, x0, w, '#7a8a96', '#4a5460', wall_kind='panel', trim='#2a3038', seed=51)
    # big illuminated track diagram
    bx, by, bw, bh = x0 + 180, 26, 440, 70
    cv.rect(bx, by, bw, bh, C('#1e2a2e'), ink=C('#0a0e10'), iw=MAJOR)
    painted_text(cv, 'SWITCH HOUSE 4 - YARD DIAGRAM', bx + bw / 2, by + 7, 4.5, C('#d8e0c8'), kind='cond',
                 shadow=False)
    for k, ty in enumerate((by + 22, by + 36, by + 50, by + 62)):
        cv.rect(bx + 14, ty, bw - 28, 1.4, C('#c8d0c0'))
        rs = R.rng('trk', k)
        for j in range(8):
            lx = bx + 24 + j * 52 + rs.uniform(-6, 6)
            c = rs.choice(['#ff4a3a', '#5aff7a', '#f8d040'])
            cv.ellipse(lx, ty + 0.7, 1.6, 1.6, C(c), em=1.0)
        if k < 3:
            cv.line([(bx + 80 + k * 110, ty + 1), (bx + 110 + k * 110, ty + 15)], 1.0, C('#c8d0c0'))
    R.glow(bx + bw / 2, by + bh / 2, 160, '#8affb0', 0.2, 'none')
    wall_window(R, x0 + 30, 34, 120, 56, view='yard')
    # phone, clipboard, warning signs
    cv.rect(x0 + 640, 110, 20, 26, C('#2a2a30'), ink=C('#0e0a10'), iw=MAJOR)
    cv.rect(x0 + 644, 112, 12, 6, C('#5a5a64'))
    cv.rect(x0 + 680, 100, 28, 36, C('#f4f0e4'), ink=C('#2a2430'), iw=DETAIL)
    for k in range(6):
        cv.rect(x0 + 684, 108 + k * 4, 20, 0.8, C('#6a6070'))
    cv.rect(x0 + 40, 120, 34, 22, C('#f8d040'), ink=C('#2a2010'), iw=DETAIL)
    cv.text('DANGER', 'cond', 4, x0 + 57, 127, C('#2a2010'), 'mm')
    cv.text('HIGH VOLTAGE', 'cond', 3, x0 + 57, 134, C('#2a2010'), 'mm')
    poster(cv, x0 + 90, 118, 16, 22, seed=601, kind='evict')
    cv.text('GREYLINE', 'cond', 3, x0 + 98, 137, C('#5a6a7a'), 'mm')
    for k in range(3):
        fluor(R, x0 + 140 + k * 260, 10, 50, col='#d8f0ff')


@facade("arcade_interior")
def f_arcade_interior(R, x0, w, f):
    cv = R.cv
    room_shell(R, x0, w, '#24183a', '#1a1028', wall_kind='plaster', trim='#0e0818', rail_y=150, seed=61)
    # starfield mural
    rs = R.rng('stars')
    for _ in range(260):
        sx, sy = rs.uniform(x0, x0 + w), rs.uniform(10, 145)
        cv.ellipse(sx, sy, rs.uniform(0.3, 0.8), rs.uniform(0.3, 0.8), C(rs.choice(['#ffffff', '#ffe8a0', '#a8e0ff'])),
                   a=rs.uniform(0.4, 1.0), em=1.0)
    for px, py, r, c in ((x0 + 120, 60, 22, '#e86a4a'), (x0 + 640, 50, 16, '#6ac0ff')):
        cv.ellipse(px, py, r, r, C(c), ink=shade(C(c), 1.6), iw=MAJOR, em=0.8)
        cv.ellipse(px, py, r * 1.7, r * 0.4, None, ink=light(C(c), 1.6), iw=1.2, em=0.8)
    neon_text(cv, 'STARLIGHT ARCADE', x0 + w / 2, 30, 14, C('#ff4ab0'), tracking=0.8, glow=0.55)
    R.glow(x0 + w / 2, 30, 160, '#ff4ab0', 0.5, 'neon')
    # neon wall stripes
    for k, c in enumerate(('#4ae0ff', '#ff4ab0', '#f8e040')):
        cv.rect(x0, 150 + k * 4, w, 1.2, C(c), em=1.0)
        R.glow(x0 + w / 2, 152 + k * 4, w * 0.6, c, 0.12, 'neon')
    # high score board
    cv.rect(x0 + 300, 70, 120, 60, C('#0e0a18'), ink=C('#4a3a6a'), iw=MAJOR)
    cv.text('HIGH SCORES', 'cond', 5, x0 + 360, 78, C('#f8e040'), 'mm', em=1.0)
    for k, (n, s) in enumerate((('JET', '98450'), ('NICO', '87200'), ('MO', '66310'), ('???', '50000'))):
        cv.text(n, 'cond', 4.4, x0 + 312, 90 + k * 9, C('#4ae0ff'), 'lm', em=1.0)
        cv.text(s, 'cond', 4.4, x0 + 408, 90 + k * 9, C('#ff8ad0'), 'rm', em=1.0)
    # prize shelf
    cv.rect(x0 + 470, 120, 140, 3, C('#5a3a6a'))
    for k in range(9):
        c = C(rs.choice(['#ff6ab0', '#6ae0ff', '#f8e060', '#8aff8a', '#ff8a4a']))
        cv.ellipse(x0 + 480 + k * 15, 113, 5, 6, c, ink=shade(c, 1.8), iw=DETAIL, em=0.5)
    R.light(x0 + w / 2, 270, w * 0.6, 80, '#c060ff', 0.10)
    R.ambient_level = 0.74


@facade("pharmacy_interior")
def f_pharmacy_interior(R, x0, w, f):
    cv = R.cv
    room_shell(R, x0, w, '#e4ecec', '#9ab8c0', wall_kind='plaster', trim='#5a7a84', rail_y=150, seed=71)
    for sx in (x0 + 10, x0 + 450):
        cv.rect(sx, 40, 180, 110, C('#d8dcdc'), ink=C('#3a4448'), iw=MAJOR)
        rs = R.rng('ph', sx)
        for r in range(4):
            sy = 48 + r * 26
            cv.rect(sx + 4, sy + 20, 172, 2, C('#a8b0b4'))
            for k in range(30):
                c = C(rs.choice(['#e84a5a', '#4a9ae8', '#f4f0e8', '#5ac08a', '#f8d040', '#c8a0e0']))
                hh = rs.uniform(8, 16)
                cv.rect(sx + 6 + k * 5.6, sy + 20 - hh, 4.4, hh, c, ink=shade(c, 1.7), iw=0.3)
    # green cross neon + sign
    cx, cy = x0 + 320, 40
    for (dx, dy, ww, hh) in ((-4, -12, 8, 24), (-12, -4, 24, 8)):
        cv.rect(cx + dx, cy + dy, ww, hh, C('#3aff8a'), ink=C('#0a3a1a'), iw=DETAIL, em=1.0)
    R.glow(cx, cy, 40, '#3aff8a', 0.55, 'neon')
    cv.rect(x0 + 240, 70, 160, 18, C('#2a6a5a'), ink=C('#0e2a24'), iw=MAJOR)
    painted_text(cv, "ROSA'S PHARMACY", x0 + 320, 79.5, 8, C('#f4f8f0'), shadow=False)
    cv.rect(x0 + 260, 100, 120, 14, C('#f4f8f8'), ink=C('#3a4448'), iw=DETAIL)
    cv.text('PRESCRIPTIONS', 'cond', 5, x0 + 320, 107, C('#2a6a5a'), 'mm')
    poster(cv, x0 + 215, 120, 15, 20, seed=801, kind='missing')
    for k in range(3):
        fluor(R, x0 + 110 + k * 210, 10, 50, col='#f0fffc')


@facade("bait_interior")
def f_bait_interior(R, x0, w, f):
    cv = R.cv
    room_shell(R, x0, w, '#6a6a58', '#4a4a3a', wall_kind='wood', trim='#2a2a22', seed=81)
    wall_window(R, x0 + 30, 40, 100, 64, view='rain')
    # rod rack
    for k in range(9):
        rx = x0 + 160 + k * 9
        cv.line([(rx, 130), (rx + 3, 20)], 0.6, C(['#c8a050', '#3a3a3a', '#a83a3a'][k % 3]))
        cv.ellipse(rx + 0.5, 112, 1.8, 1.8, C('#8a8e9a'), ink=C('#2a2a34'), iw=0.3)
    cv.rect(x0 + 154, 128, 86, 4, C('#5a3a24'), ink=C('#1e120c'), iw=DETAIL)
    # nets + mounted fish
    for k in range(10):
        cv.line([(x0 + 270 + k * 10, 20), (x0 + 265 + k * 10, 70)], 0.4, C('#c8c0a0'), a=0.7)
    for k in range(6):
        cv.line([(x0 + 266, 26 + k * 9), (x0 + 362, 24 + k * 9)], 0.4, C('#c8c0a0'), a=0.7)
    cv.ellipse(x0 + 470, 50, 30, 10, C('#6a8a7a'), ink=C('#1e2a24'), iw=MAJOR)
    cv.fill_poly([(x0 + 498, 50), (x0 + 512, 40), (x0 + 512, 60)], C('#6a8a7a'), ink=C('#1e2a24'), iw=MAJOR)
    cv.ellipse(x0 + 450, 48, 1.5, 1.5, C('#f4f0e8'))
    cv.rect(x0 + 440, 64, 60, 4, C('#5a3a24'), ink=C('#1e120c'), iw=DETAIL)
    cv.rect(x0 + 400, 80, 120, 16, C('#2e5a6a'), ink=C('#0e1a20'), iw=MAJOR)
    painted_text(cv, 'BAIT & TACKLE', x0 + 460, 88.5, 7, C('#f4e8c0'), shadow=False)
    # live bait tank
    cv.rect(x0 + 540, 120, 80, 40, C('#5aa0a8'), ink=C('#1e3a40'), iw=MAJOR, em=0.6)
    cv.vgrad(x0 + 542, 122, 76, 36, [C('#8ad0d0'), C('#3a7a80')], em=0.8)
    R.glow(x0 + 580, 140, 50, '#6ad0d8', 0.3, 'none')
    pendant(R, x0 + 300, 8, '#3a5a4a', warm='#ffd8a0')
    tag(cv, x0 + 40, 150, 'RATS', C('#c8c8d0'), size=5, seed=3, a=0.4)
    R.ambient.append({"type": "drip", "x": float(x0 + 80), "y": 106.0, "rate": 0.3})
