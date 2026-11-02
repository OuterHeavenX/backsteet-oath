"""Backstreet Oath env v2 -- the remaining 39 prop types (canvas size, anchor and footprint match v1)."""
import math

import numpy as np

from raster import Canvas, C, mix, shade, light, ink_of, rng_of
import kit
from kit import M, MAJOR, DETAIL
from props2 import prop, ao, cyl, PROPS


def box3(cv, x, y, w, h, col, iw=MAJOR):
    m = M(C(col))
    cv.rect(x, y, w, h, m.b, ink=m.i, iw=iw)
    cv.hgrad(x, y, w, h, [m.l, m.b, m.b, m.s], mode='atop', a=0.8)
    cv.rect(x, y, w, 0.8, m.h, mode='atop')
    return m


@prop('ac_unit')
def p_ac(cv, W, Hh):
    m = box3(cv, 2, 6, 32, Hh - 6, '#a8aca8')
    for k in range(5):
        cv.rect(5, 10 + k * 3, 14, 1, m.s)
    cv.ellipse(26, Hh / 2 + 3, 6, 6, m.s, ink=m.i, iw=DETAIL)
    for a in range(4):
        aa = a * math.pi / 2 + 0.4
        cv.line([(26, Hh / 2 + 3), (26 + math.cos(aa) * 5, Hh / 2 + 3 + math.sin(aa) * 5)], 0.8, m.d)
    kit.weather(cv, 2, 6, 32, Hh - 6, 5, soot=0.3, streak=True)
    ao(cv, 2, Hh, 32)


@prop('arcade_cabinet')
def p_arcade(cv, W, Hh):
    rs = rng_of('arc', W)
    body = M(C('#2a1e4a'))
    lay = cv.layer()
    lay.fill_poly([(2, Hh), (2, 6), (8, 1), (26, 1), (26, Hh)], body.b)
    cv.merge(lay, ink=body.i, iw=MAJOR)
    cv.hgrad(2, 1, 24, Hh - 1, [body.l, body.b, body.s], mode='atop')
    cv.rect(4, 3, 20, 6, C('#ff4ab0'), ink=body.d, iw=DETAIL)
    cv.text('STAR', 'sign', 3, 14, 6, C('#f8e040'), 'mm')
    cv.rect(5, 11, 18, 14, C('#0a0e1a'), ink=body.d, iw=DETAIL)
    cv.rect(6, 12, 16, 12, C('#3a8aff'), a=0.8)
    for k in range(5):
        cv.rect(7 + k * 3, 14 + (k % 3) * 3, 1.6, 1.6, C(rs.choice(['#f8e040', '#ff4ab0', '#8aff8a'])))
    cv.fill_poly([(3, 27), (25, 27), (27, 32), (1, 32)], C('#3a2a5a'), ink=body.d, iw=DETAIL)
    cv.ellipse(9, 29.5, 1.4, 1, C('#c83a3a'))
    for k in range(3):
        cv.ellipse(15 + k * 3.4, 29.5, 1.1, 0.8, C(['#f8e040', '#4ae0ff', '#ff4ab0'][k]))
    cv.rect(10, 38, 8, 6, C('#1a1428'), ink=body.d, iw=DETAIL)
    cv.rect(12, 40, 4, 1.2, C('#f8e040'))
    cv.rect(2, 6, 1, Hh - 6, C('#ff4ab0'), a=0.8)
    ao(cv, 2, Hh, 24)


@prop('barrel')
def p_barrel(cv, W, Hh):
    m = M(C('#9a6438'))
    lay = cv.layer()
    lay.fill_poly([(3, 2), (16, 2), (17.5, Hh / 2), (16, Hh), (3, Hh), (1.5, Hh / 2)], m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cyl(cv, 1.5, 2, 16, Hh - 2, m, mode='atop')
    for k in range(4):
        cv.rect(1.5 + k * 4.2, 3, 0.5, Hh - 4, m.d, a=0.5, mode='atop')
    for yy in (5, Hh - 6):
        cv.rect(1.5, yy, 16, 1.6, C('#4a4a54'), mode='atop')
    cv.ellipse(9.5, 2.5, 6.5, 1.4, m.l, ink=m.i, iw=DETAIL)
    ao(cv, 2, Hh, 15)


@prop('barrier')
def p_barrier(cv, W, Hh):
    for x in (5, W - 8):
        cv.rect(x, 8, 3, Hh - 8, C('#3a3a44'), ink=C('#0e0a10'), iw=DETAIL)
        cv.fill_poly([(x - 3, Hh), (x + 6, Hh), (x + 4, Hh - 3), (x - 1, Hh - 3)], C('#3a3a44'), ink=C('#0e0a10'),
                     iw=DETAIL)
    for y in (6, 15):
        mk = cv.rect(1, y, W - 2, 6, C('#f4f0e8'), ink=C('#2a1410'), iw=MAJOR)
        xx = 1
        while xx < W:
            cv.fill_poly([(xx, y + 6), (xx + 4, y + 6), (xx + 8, y), (xx + 4, y)], C('#e8402a'), mode='atop')
            xx += 8
    cv.ellipse(6.5, 4, 2, 2, C('#ffb040'), ink=C('#3a2010'), iw=DETAIL)
    ao(cv, 1, Hh, W - 2)


@prop('book_pile')
def p_book_pile(cv, W, Hh):
    rs = rng_of('bp')
    y = Hh
    k = 0
    while y > 4:
        bh = rs.uniform(2.5, 4)
        bw = rs.uniform(18, 26)
        x = (W - bw) / 2 + rs.uniform(-3, 3)
        c = C(rs.choice(['#a83a32', '#2e5a8a', '#3a7a4a', '#c8a040', '#6a3a6a', '#d8d0b8']))
        cv.rect(x, y - bh, bw, bh, c, ink=shade(c, 1.8), iw=DETAIL)
        cv.rect(x + 1, y - bh + 0.6, bw - 2, 0.6, C('#f4f0e0'), a=0.7)
        y -= bh
        k += 1
        if k > 5:
            break
    ao(cv, 3, Hh, W - 6)


@prop('car_parked')
def p_car_parked(cv, W, Hh):
    body = M(C('#3a5aa0'))
    lay = cv.layer()
    lay.fill_poly([(2, 30), (4, 20), (20, 17), (32, 5), (68, 5), (80, 17), (96, 19), (98, 30)], body.b)
    cv.merge(lay, ink=body.i, iw=MAJOR)
    cv.vgrad(2, 5, 96, 25, [body.h, body.l, body.b, body.s], mode='atop', a=0.85)
    cv.fill_poly([(35, 7.5), (49, 7.5), (49, 16), (24, 16.5)], C('#8ab0d0'), ink=body.d, iw=DETAIL)
    cv.fill_poly([(52, 7.5), (66, 7.5), (77, 16.5), (52, 16)], C('#8ab0d0'), ink=body.d, iw=DETAIL)
    cv.fill_poly([(38, 8), (42, 8), (33, 16), (29, 16)], C('#ffffff'), a=0.4, mode='atop')
    cv.rect(50.5, 16, 0.6, 13, body.d)
    cv.rect(2, 23, 96, 1, C('#e8e8f0'), a=0.7)
    cv.rect(92, 20, 5, 3, C('#fff4c0'), ink=body.d, iw=DETAIL)
    cv.rect(2.5, 20, 3, 3, C('#ff4a3a'), ink=body.d, iw=DETAIL)
    for x in (22, 78):
        cv.ellipse(x, 30, 8, 8, C('#1a1a20'), ink=C('#060608'), iw=MAJOR)
        cv.ellipse(x, 30, 3.6, 3.6, C('#a8acb8'), ink=C('#3a3a48'), iw=0.4)
    ao(cv, 6, Hh, 88)


@prop('chimney')
def p_chimney(cv, W, Hh):
    kit.brick_wall(cv, 5, 8, 20, Hh - 8, C('#8a4a3a'), seed=5, bw=6, bh=3, soot=0.5)
    cv.rect(5, 8, 20, Hh - 8, None, ink=C('#2a1214'), iw=MAJOR)
    cv.rect(3, 4, 24, 5, C('#9a948a'), ink=C('#2a2430'), iw=MAJOR)
    cv.rect(9, 0.5, 4, 4, C('#5a5458'), ink=C('#1a1418'), iw=DETAIL)
    cv.rect(17, 0.5, 4, 4, C('#5a5458'), ink=C('#1a1418'), iw=DETAIL)
    cv.rect(5, 8, 1, Hh - 8, C('#ffb890'), a=0.5)
    ao(cv, 5, Hh, 20)


def counter(cv, W, Hh, top_col, front_col, trim='#c8ccd8', front='panel', items=None, seed=0):
    top = M(C(top_col))
    fr = M(C(front_col))
    cv.rect(1, 6, W - 2, 6, top.b, ink=top.i, iw=MAJOR)
    cv.vgrad(1, 6, W - 2, 6, [top.h, top.b, top.s], mode='atop', a=0.7)
    cv.rect(1, 12, W - 2, 2.5, C(trim), ink=C('#2a2a34'), iw=DETAIL)
    cv.rect(2, 14.5, W - 4, Hh - 17, fr.b, ink=fr.i, iw=MAJOR)
    cv.vgrad(2, 14.5, W - 4, Hh - 17, [fr.l, fr.b, fr.s], mode='atop', a=0.8)
    if front == 'panel':
        x = 8
        while x < W - 12:
            cv.rect(x, 17, 18, Hh - 23, fr.s, ink=fr.d, iw=DETAIL)
            cv.rect(x, 17, 18, 0.6, fr.l, mode='atop')
            x += 22
    elif front == 'planks':
        y = 15
        while y < Hh - 4:
            cv.rect(2, y, W - 4, 0.6, fr.d, mode='atop')
            y += 4
    elif front == 'glass':
        cv.rect(6, 16, W - 12, Hh - 22, C('#d8f0f4'), ink=fr.d, iw=DETAIL, a=0.8)
        rs = rng_of('cg', seed)
        for k in range(int((W - 16) / 6)):
            c = C(rs.choice(['#e84a5a', '#4a9ae8', '#f4f0e8', '#5ac08a', '#f8d040']))
            cv.rect(9 + k * 6, Hh - 12 - rs.uniform(3, 8), 4, 8, c, ink=shade(c, 1.6), iw=0.3)
    elif front == 'neon':
        for k, c in enumerate(('#ff4ab0', '#4ae0ff', '#f8e040')):
            cv.rect(3, 18 + k * 4, W - 6, 1.2, C(c))
    cv.rect(2, Hh - 3, W - 4, 3, C('#2a2430'), ink=C('#0e0a10'), iw=DETAIL)
    rs = rng_of('ci', seed)
    for it in (items or []):
        kind, x = it
        if kind == 'register':
            cv.rect(x, -0.5, 14, 7, C('#5a5a64'), ink=C('#1a1220'), iw=DETAIL)
            cv.rect(x + 2, 0.5, 10, 2.5, C('#7aff9a'))
        elif kind == 'jar':
            cv.ellipse(x, 3.5, 3.5, 3, C('#e8f4ff'), ink=C('#6a7888'), iw=0.4, a=0.8)
            cv.rect(x - 2, 1, 4, 3, C(rs.choice(['#e8a040', '#c84a3a', '#5ac08a'])), a=0.7)
        elif kind == 'bowl':
            cv.ellipse(x, 5, 5, 1.5, C('#f4f0e8'), ink=C('#6a4a3a'), iw=0.4)
            cv.ellipse(x, 4.4, 3.5, 0.8, C('#e8a040'))
        elif kind == 'bell':
            cv.ellipse(x, 4.5, 2.4, 1.8, C('#e0c060'), ink=C('#5a4010'), iw=0.4)
        elif kind == 'books':
            for k in range(3):
                cv.rect(x - 6 + k * 1, 4 - k * 1.6, 12, 1.6, C(rs.choice(['#a83a32', '#2e5a8a', '#3a7a4a'])),
                        ink=C('#1a1220'), iw=0.3)
        elif kind == 'tokens':
            cv.rect(x, 0, 10, 6, C('#c8a030'), ink=C('#3a2a08'), iw=DETAIL)
            cv.text('$', 'cond', 3, x + 5, 3, C('#2a2008'), 'mm')
        elif kind == 'bait':
            cv.rect(x - 5, 1, 10, 5, C('#5aa0a8'), ink=C('#1e3a40'), iw=DETAIL)
            cv.rect(x - 4, 2, 8, 3, C('#8ad0d0'), a=0.8)
        elif kind == 'tray':
            cv.rect(x - 8, 4.5, 16, 1.5, C('#9aa0a8'), ink=C('#3a3a48'), iw=0.4)
            cv.ellipse(x - 3, 4, 2.5, 1, C('#a8603a'))
            cv.ellipse(x + 3, 4, 2.5, 1, C('#e8c070'))
        elif kind == 'pills':
            for k in range(3):
                cv.rect(x - 4 + k * 3, 1.5, 2.2, 4.5, C(['#f4f0e8', '#e84a5a', '#4a9ae8'][k]), ink=C('#2a2430'), iw=0.3)
    ao(cv, 2, Hh, W - 4)


@prop('counter_arcade')
def p_counter_arcade(cv, W, Hh):
    counter(cv, W, Hh, '#2a2040', '#1e1630', trim='#ff4ab0', front='neon',
            items=[('tokens', 20), ('register', 60), ('jar', 110)], seed=1)


@prop('counter_bait')
def p_counter_bait(cv, W, Hh):
    counter(cv, W, Hh, '#8a7a5a', '#5a4a34', trim='#3a3a30', front='planks',
            items=[('bait', 30), ('register', 80), ('jar', 130)], seed=2)


@prop('counter_canteen')
def p_counter_canteen(cv, W, Hh):
    counter(cv, W, Hh, '#c8ccd0', '#5a7a5a', trim='#e8eef0', front='panel',
            items=[('tray', 30), ('tray', 60), ('register', 110), ('jar', 140)], seed=3)


@prop('counter_noodle')
def p_counter_noodle(cv, W, Hh):
    counter(cv, W, Hh, '#c89a68', '#7a3a2a', trim='#3a2416', front='planks',
            items=[('bowl', 30), ('bowl', 52), ('bell', 80), ('jar', 120), ('bowl', 140)], seed=4)


@prop('counter_pharmacy')
def p_counter_pharmacy(cv, W, Hh):
    counter(cv, W, Hh, '#f0f4f4', '#c8d8dc', trim='#2a6a5a', front='glass',
            items=[('pills', 30), ('register', 70), ('jar', 120)], seed=5)


@prop('counter_shop')
def p_counter_shop(cv, W, Hh):
    counter(cv, W, Hh, '#b8925e', '#6a4a2e', trim='#3a2416', front='panel',
            items=[('books', 26), ('register', 70), ('bell', 110)], seed=6)


@prop('crate_stack')
def p_crate_stack(cv, W, Hh):
    def crate(x, y, w, h, col):
        m = M(C(col))
        cv.rect(x, y, w, h, m.b, ink=m.i, iw=MAJOR)
        for (bx, by, bw, bh) in ((x, y, w, 2.5), (x, y + h - 2.5, w, 2.5), (x, y, 2.5, h), (x + w - 2.5, y, 2.5, h)):
            cv.rect(bx, by, bw, bh, m.l, ink=m.d, iw=DETAIL)
        cv.line([(x + 3, y + h - 3), (x + w - 3, y + 3)], 2.0, m.l, ink=m.d, iw=DETAIL)
    crate(1, Hh - 22, 22, 22, '#b8874e')
    crate(23, Hh - 22, 22, 22, '#a87a46')
    crate(10, Hh - 44, 24, 22, '#c0905a')
    cv.text('FRAGILE', 'cond', 2.2, 22, Hh - 33, C('#8a3a2a'), 'mm', a=0.6)
    ao(cv, 1, Hh, 44)


@prop('desk')
def p_desk(cv, W, Hh):
    m = M(C('#7a5a3e'))
    cv.rect(1, 14, W - 2, 4, m.l, ink=m.i, iw=MAJOR)
    cv.rect(3, 18, 18, Hh - 18, m.b, ink=m.i, iw=MAJOR)
    cv.rect(W - 21, 18, 18, Hh - 18, m.b, ink=m.i, iw=MAJOR)
    for k in range(3):
        cv.rect(5, 20 + k * 6.5, 14, 5.5, m.s, ink=m.d, iw=DETAIL)
        cv.rect(10, 22 + k * 6.5, 4, 1, C('#d8c080'))
    cv.rect(21, 18, W - 42, 10, shade(m.b, 1.4))
    # papers, lamp, phone, ledger
    cv.rect(26, 11, 14, 3.5, C('#f4f0e4'), ink=C('#6a6070'), iw=0.3)
    cv.rect(28, 10, 12, 3, C('#e8e4d4'), ink=C('#6a6070'), iw=0.3)
    cv.line([(48, 14), (50, 4), (54, 4)], 0.8, C('#2a5a3a'))
    cv.fill_poly([(51, 4), (58, 4), (56, 1), (53, 1)], C('#2a5a3a'), ink=C('#0e1a12'), iw=DETAIL)
    cv.rect(8, 9, 10, 5, C('#2a2a30'), ink=C('#0e0a10'), iw=DETAIL)
    ao(cv, 2, Hh, W - 4)


@prop('filing_cabinet')
def p_filing(cv, W, Hh):
    m = box3(cv, 2, 2, 18, Hh - 2, '#7a8480')
    for k in range(4):
        cv.rect(4, 4 + k * 9.2, 14, 8, m.s, ink=m.d, iw=DETAIL)
        cv.rect(8, 6.5 + k * 9.2, 6, 1.4, C('#d8dcd8'), ink=m.d, iw=0.3)
        cv.rect(7, 9 + k * 9.2, 8, 2, C('#f4f0e4'))
    ao(cv, 2, Hh, 18)


@prop('fish_crate')
def p_fish_crate(cv, W, Hh):
    m = M(C('#8aa0a8'))
    cv.rect(1, 6, 23, Hh - 6, m.b, ink=m.i, iw=MAJOR)
    cv.rect(1, 6, 23, 1, m.h, mode='atop')
    for k in range(3):
        cv.rect(1, 9 + k * 3, 23, 0.6, m.s, mode='atop')
    rs = rng_of('fc')
    for k in range(5):
        cv.ellipse(4 + k * 4.4, 5.5, 3, 1.4, C(rs.choice(['#a8b8c8', '#c8a8a0', '#98a8b8'])), ink=C('#3a4a5a'),
                   iw=0.3)
        cv.fill_poly([(1.5 + k * 4.4, 5.5), (0 + k * 4.4, 4.2), (0 + k * 4.4, 6.8)], C('#8a9aa8'))
    cv.ellipse(8, 3.6, 3, 1.2, C('#e8f4fa'), a=0.8)
    ao(cv, 1, Hh, 23)


@prop('floodlight')
def p_floodlight(cv, W, Hh):
    m = M(C('#4a5058'))
    cv.rect(10, 12, 2.4, Hh - 12, m.b, ink=m.i, iw=DETAIL)
    cv.rect(7, Hh - 4, 8, 4, m.b, ink=m.i, iw=DETAIL)
    cv.rect(1, 6, 20, 2, m.b, ink=m.i, iw=DETAIL)
    for x in (2, 13):
        cv.rect(x, 1, 7, 6, m.s, ink=m.i, iw=DETAIL)
        cv.rect(x + 1, 4, 5, 2.6, C('#f4fbff'))
    cv.rect(10, 12, 0.8, Hh - 12, m.l)
    ao(cv, 7, Hh, 8)


@prop('forklift')
def p_forklift(cv, W, Hh):
    m = M(C('#e8a830'))
    lay = cv.layer()
    lay.fill_poly([(14, Hh - 8), (14, 26), (22, 22), (46, 22), (52, 30), (52, Hh - 8)], m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.vgrad(14, 22, 38, Hh - 30, [m.h, m.l, m.b, m.s], mode='atop', a=0.8)
    # cage + mast + forks
    for x in (20, 46):
        cv.rect(x, 4, 2, 20, C('#2a2a30'), ink=C('#0e0a10'), iw=0.4)
    cv.rect(20, 3, 28, 2, C('#2a2a30'), ink=C('#0e0a10'), iw=0.4)
    cv.rect(8, 6, 3, Hh - 10, C('#3a3a44'), ink=C('#0e0a10'), iw=DETAIL)
    cv.rect(12, 6, 2, Hh - 10, C('#3a3a44'), ink=C('#0e0a10'), iw=DETAIL)
    cv.rect(0, Hh - 6, 14, 2, C('#4a4a54'), ink=C('#0e0a10'), iw=DETAIL)
    cv.rect(28, 26, 12, 8, C('#1e1e24'))
    cv.rect(24, 34, 18, 3, C('#1e1e24'))
    cv.text('GL', 'sign', 4, 46, Hh - 18, C('#2a2008'), 'mm')
    for x, r in ((22, 7), (48, 6)):
        cv.ellipse(x, Hh - 7, r, r, C('#1a1a20'), ink=C('#060608'), iw=MAJOR)
        cv.ellipse(x, Hh - 7, r * 0.4, r * 0.4, C('#8a8e9a'))
    ao(cv, 2, Hh, W - 4)


@prop('guard_booth')
def p_guard_booth(cv, W, Hh):
    m = box3(cv, 3, 12, 40, Hh - 12, '#c8ccc4')
    cv.rect(1, 6, 44, 7, C('#2a3038'), ink=C('#0e1014'), iw=MAJOR)
    cv.rect(7, 18, 32, 18, C('#e8f8ff'), ink=m.i, iw=DETAIL)
    cv.vgrad(7, 18, 32, 18, [C('#f0fff8'), C('#b8e0d8')], mode='atop')
    cv.ellipse(23, 26, 3, 3.4, C('#4a4a54'))
    cv.rect(19, 29, 8, 7, C('#3a4a5a'))
    cv.rect(16, 38, 14, 4, C('#f4f0e8'), ink=C('#2a2430'), iw=0.4)
    cv.text('GREYLINE', 'cond', 2.2, 23, 40, C('#3a4a5a'), 'mm')
    cv.rect(3, 44, 40, 2, C('#e8b830'))
    ao(cv, 3, Hh, 40)


@prop('ice_chest')
def p_ice_chest(cv, W, Hh):
    m = box3(cv, 2, 6, 30, Hh - 6, '#3a8ab0')
    cv.rect(1, 3, 32, 4, C('#f4f8fa'), ink=m.i, iw=MAJOR)
    cv.rect(13, 8, 8, 2.4, C('#f4f8fa'), ink=m.i, iw=DETAIL)
    cv.text('ICE', 'sign', 3.4, 17, 14.5, C('#f4f8fa'), 'mm')
    ao(cv, 2, Hh, 30)


@prop('ingot_stack')
def p_ingot(cv, W, Hh):
    m = M(C('#8a8e9a'))
    rows = [(4, 5), (3, 3), (2, 2)]
    y = Hh
    for r, (n, _) in enumerate(rows):
        bw = 8.4
        x0 = (W - n * bw) / 2
        for k in range(n):
            x = x0 + k * bw
            cv.fill_poly([(x, y), (x + bw, y), (x + bw - 1.2, y - 6), (x + 1.2, y - 6)], m.b, ink=m.i, iw=DETAIL)
            cv.rect(x + 1.2, y - 6, bw - 2.4, 1, m.h)
            cv.rect(x + bw - 2.4, y - 5, 1.2, 5, m.s)
        y -= 6.4
    cv.text('GL', 'cond', 2.4, W / 2, Hh - 3, C('#3a3e48'), 'mm', a=0.6)
    ao(cv, 2, Hh, W - 4)


@prop('lamp_sodium')
def p_lamp_sodium(cv, W, Hh):
    m = M(C('#4a5058'))
    cv.rect(13, 8, 2.6, Hh - 8, m.b, ink=m.i, iw=DETAIL)
    cv.rect(10, Hh - 6, 9, 6, m.b, ink=m.i, iw=DETAIL)
    cv.line([(14, 9), (18, 4), (26, 4)], 1.6, m.b, ink=m.i, iw=0.4)
    cv.fill_poly([(19, 3), (28, 3), (27, 7), (20, 7)], m.s, ink=m.i, iw=DETAIL)
    cv.rect(20.5, 6, 6, 1.6, C('#ffc060'))
    cv.rect(13, 8, 0.8, Hh - 8, m.l)
    ao(cv, 10, Hh, 9)


@prop('lever_panel')
def p_lever_panel(cv, W, Hh):
    m = box3(cv, 2, 24, W - 4, Hh - 24, '#5a6a72')
    cv.rect(1, 22, W - 2, 3, C('#3a4448'), ink=C('#0e1014'), iw=DETAIL)
    for k in range(8):
        lx = 8 + k * 7
        up = k % 3 != 1
        col = ['#c83a2a', '#2a5aa8', '#e8b830'][k % 3]
        cv.line([(lx, 24), (lx + (2 if up else -2), 4 if up else 10)], 1.2, C('#c8ccd8'), ink=C('#2a2a34'), iw=0.3)
        cv.rect(lx - 1.6 + (2 if up else -2), (1.5 if up else 7.5), 3.2, 3, C(col), ink=C('#1a1220'), iw=0.3)
        cv.rect(lx - 2, 26, 4, 2, C('#e8e4d8'), ink=C('#2a2430'), iw=0.3)
    cv.rect(8, 34, W - 16, 10, C('#1e2a2e'), ink=C('#0a0e10'), iw=DETAIL)
    for k in range(6):
        cv.ellipse(12 + k * 8, 39, 1.2, 1.2, C(['#ff4a3a', '#5aff7a', '#f8d040'][k % 3]))
    ao(cv, 2, Hh, W - 4)


def stall(cv, W, Hh, goods, canopy):
    rs = rng_of('st', goods)
    for x in (4, W - 7):
        cv.rect(x, 10, 3, Hh - 10, C('#6a4a30'), ink=C('#1e1410'), iw=DETAIL)
    kit.awning(cv, 2, 3, W - 4, 9, C(canopy), C('#f4f0e8'), stripe=6, valance=3)
    cv.rect(3, 34, W - 6, Hh - 34, C('#8a6440'), ink=C('#20140e'), iw=MAJOR)
    y = 36
    while y < Hh - 2:
        cv.rect(3, y, W - 6, 0.6, C('#5a3a24'), mode='atop')
        y += 4
    # angled display tray with goods
    cv.fill_poly([(3, 34), (W - 3, 34), (W - 6, 26), (6, 26)], C('#a87a50'), ink=C('#20140e'), iw=DETAIL)
    for k in range(int((W - 14) / 5.5)):
        for row in range(2):
            gx = 9 + k * 5.5 + row * 2.5
            gy = 29 + row * 3
            if goods == 'fish':
                cv.ellipse(gx, gy, 2.6, 1.0, C(rs.choice(['#a8b8c8', '#c8a0a0', '#8aa0b0'])), ink=C('#3a4a5a'), iw=0.3)
            else:
                cv.ellipse(gx, gy, 2.2, 1.9, C(rs.choice(['#f08a30', '#e8d040', '#c83a3a', '#8ac050'])),
                           ink=C('#3a2010'), iw=0.3)
    if goods == 'fish':
        cv.rect(6, 26, W - 12, 2, C('#e8f4fa'), a=0.7)
    cv.rect(W / 2 - 10, 38, 20, 9, C('#2a2a2e'), ink=C('#6a4a2a'), iw=0.6)
    cv.text('FRESH' if goods == 'fish' else '3/$1', 'cond', 3.6, W / 2, 42.5, C('#f4f0e8'), 'mm')
    ao(cv, 3, Hh, W - 6)


@prop('market_stall_fish')
def p_stall_fish(cv, W, Hh):
    stall(cv, W, Hh, 'fish', '#2e5a8a')


@prop('market_stall_fruit')
def p_stall_fruit(cv, W, Hh):
    stall(cv, W, Hh, 'fruit', '#c8302a')


@prop('mooring_post')
def p_mooring(cv, W, Hh):
    m = M(C('#3a3a46'))
    lay = cv.layer()
    lay.fill_poly([(3, Hh), (4, 6), (12, 6), (13, Hh)], m.b)
    lay.ellipse(8, 5, 6, 2.8, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cyl(cv, 3, 6, 10, Hh - 6, m, mode='atop')
    cv.ellipse(8, 4.6, 5, 2, m.l)
    cv.line([(3, 12), (0, 15)], 1.0, C('#c8b890'))
    ao(cv, 3, Hh, 10)


@prop('neon_post')
def p_neon_post(cv, W, Hh):
    m = M(C('#2a2a34'))
    cv.rect(10, 20, 2.4, Hh - 20, m.b, ink=m.i, iw=DETAIL)
    cv.rect(7, Hh - 5, 8, 5, m.b, ink=m.i, iw=DETAIL)
    cv.rect(1, 2, 20, 18, C('#1a1020'), ink=m.i, iw=MAJOR)
    cv.text('OPEN', 'sign', 4.2, 11, 8, C('#ff4ab0'), 'mm')
    cv.text('24H', 'sign', 4.2, 11, 15, C('#4ae0ff'), 'mm')
    ao(cv, 7, Hh, 8)


@prop('phone_booth')
def p_phone_booth(cv, W, Hh):
    m = M(C('#c83a2a'))
    lay = cv.layer()
    lay.rect(2, 6, 24, Hh - 6, m.b)
    lay.rect(1, 2, 26, 5, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.hgrad(2, 6, 24, Hh - 6, [m.l, m.b, m.s], mode='atop')
    cv.rect(4, 3, 20, 3, C('#f4f0e8'))
    cv.text('PHONE', 'cond', 2.6, 14, 4.6, C('#2a1410'), 'mm')
    cv.rect(5, 10, 18, Hh - 22, C('#a8c8d0'), ink=m.d, iw=DETAIL, a=0.85)
    for yy in range(14, int(Hh - 12), 6):
        cv.rect(5, yy, 18, 0.8, m.b)
    cv.rect(10, 22, 7, 10, C('#2a2a30'), ink=C('#0e0a10'), iw=DETAIL)
    cv.rect(16, 24, 1.4, 6, C('#1a1a20'))
    cv.rect(5, 12, 4, Hh - 26, C('#ffffff'), a=0.3)
    ao(cv, 2, Hh, 24)


@prop('pipe_stack')
def p_pipe_stack(cv, W, Hh):
    m = M(C('#8a8e9a'))
    rows = [(5, 7), (4, 7), (3, 7)]
    y = Hh - 6
    for r, (n, rr) in enumerate(rows):
        x0 = (W - n * 12) / 2 + 6
        for k in range(n):
            cx = x0 + k * 12
            cv.ellipse(cx, y, 6, 6, m.b, ink=m.i, iw=DETAIL)
            cv.ellipse(cx, y, 3.6, 3.6, C('#2a2a34'))
            cv.ellipse(cx - 1.8, y - 2, 2, 1.4, m.h, a=0.6)
        y -= 10.4
    cv.rect(2, Hh - 3, W - 4, 3, C('#6a4a30'), ink=C('#1e1410'), iw=DETAIL)
    ao(cv, 2, Hh, W - 4)


@prop('planter')
def p_planter(cv, W, Hh):
    m = box3(cv, 3, 12, 24, Hh - 12, '#9a8a78')
    rs = rng_of('pl')
    for k in range(9):
        a = -math.pi / 2 + (k - 4) * 0.3
        L = rs.uniform(8, 13)
        c = C(rs.choice(['#4a8a3a', '#3a7a4a', '#5a9a4a']))
        cv.line([(15, 12), (15 + math.cos(a) * L, 12 + math.sin(a) * L)], 1.6, c, ink=shade(c, 1.8), iw=0.3)
    for k in range(4):
        cv.ellipse(8 + k * 5, 4 + (k % 2) * 3, 1.4, 1.4, C(rs.choice(['#f0a0c0', '#f8e060', '#e84a4a'])))
    ao(cv, 3, Hh, 24)


@prop('punching_bag')
def p_punching_bag(cv, W, Hh):
    cv.rect(0, 0, W, 2.5, C('#3a3a44'), ink=C('#0e0a10'), iw=DETAIL)
    cv.line([(17, 2), (17, 10)], 0.8, C('#8a8e9a'))
    for dx in (-5, 5):
        cv.line([(17, 10), (17 + dx, 14)], 0.6, C('#8a8e9a'))
    m = M(C('#c8302a'))
    lay = cv.layer()
    lay.rect(10, 14, 14, 36, m.b)
    lay.ellipse(17, 14, 7, 2.4, m.b)
    lay.ellipse(17, 50, 7, 2.4, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cyl(cv, 10, 14, 14, 36, m, mode='atop')
    cv.rect(10, 24, 14, 1.4, m.d, mode='atop')
    cv.rect(10, 40, 14, 1.4, m.d, mode='atop')
    cv.ellipse(17, Hh - 1.5, 9, 1.4, C('#140c18'), a=0.35)


@prop('rail_cart')
def p_rail_cart(cv, W, Hh):
    m = M(C('#7a5a44'))
    lay = cv.layer()
    lay.fill_poly([(2, 6), (W - 2, 6), (W - 6, Hh - 10), (6, Hh - 10)], m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.vgrad(2, 6, W - 4, Hh - 16, [m.l, m.b, m.s], mode='atop')
    for k in range(4):
        cv.ellipse(10 + k * 10, 6, 4, 2, C('#3a3a40'), ink=C('#0e0a10'), iw=0.4)
    cv.rect(2, 6, W - 4, 1, C('#ffb070'), a=0.6)
    cv.rect(4, Hh - 10, W - 8, 3, C('#3a3a44'), ink=C('#0e0a10'), iw=DETAIL)
    for x in (12, W - 12):
        cv.ellipse(x, Hh - 4, 4.5, 4.5, C('#3a3a44'), ink=C('#0e0a10'), iw=MAJOR)
        cv.ellipse(x, Hh - 4, 1.6, 1.6, C('#8a8e9a'))
    kit.weather(cv, 2, 6, W - 4, Hh - 16, 4, soot=0.3, streak=True)
    ao(cv, 3, Hh, W - 6)


@prop('sandbags')
def p_sandbags(cv, W, Hh):
    m = M(C('#b8a070'))
    rows = [(5, Hh - 4), (4, Hh - 11), (3, Hh - 18)]
    for n, y in rows:
        x0 = (W - n * 10) / 2
        for k in range(n):
            cv.ellipse(x0 + 5 + k * 10, y, 5.6, 3.6, m.b, ink=m.i, iw=DETAIL)
            cv.ellipse(x0 + 4 + k * 10, y - 1.2, 3.2, 1.4, m.l, a=0.7)
            cv.line([(x0 + 2 + k * 10, y - 1), (x0 + 3 + k * 10, y + 2)], 0.4, m.d)
    cv.vgrad(0, Hh - 8, W, 8, [C('#2a3a3a', 0), C('#2a3a3a', 90)], mode='atop')
    ao(cv, 2, Hh, W - 4)


@prop('shelf')
def p_shelf(cv, W, Hh):
    rs = rng_of('shelfp')
    for x in (2, W - 5):
        cv.rect(x, 2, 3, Hh - 2, C('#2a5a8a'), ink=C('#0a1a2a'), iw=DETAIL)
    for lv in range(3):
        y = Hh - 2 - lv * 24
        cv.rect(1, y - 2.5, W - 2, 2.5, C('#d87a30'), ink=C('#2a1408'), iw=DETAIL)
        x = 6
        while x < W - 12:
            bw = rs.uniform(12, 20)
            bh = rs.uniform(10, 18)
            c = C(rs.choice(['#9a7448', '#8a8a7a', '#b8925e']))
            cv.rect(x, y - 2.5 - bh, bw, bh, c, ink=shade(c, 1.8), iw=DETAIL)
            cv.rect(x + 2, y - 2.5 - bh + 3, bw - 4, 1, C('#e8dcc0'), a=0.6)
            x += bw + rs.uniform(1, 3)
    ao(cv, 2, Hh, W - 4)


@prop('training_dummy')
def p_dummy(cv, W, Hh):
    m = M(C('#c8a068'))
    cv.rect(11.5, 22, 3, Hh - 26, C('#6a4a30'), ink=C('#1e1410'), iw=DETAIL)
    cv.fill_poly([(4, Hh), (22, Hh), (18, Hh - 4), (8, Hh - 4)], C('#3a3a44'), ink=C('#0e0a10'), iw=DETAIL)
    lay = cv.layer()
    lay.ellipse(13, 7, 5.5, 6, m.b)
    lay.fill_poly([(5, 14), (21, 14), (19, 34), (7, 34)], m.b)
    lay.rect(1, 17, 24, 3.4, m.b)
    cv.merge(lay, ink=m.i, iw=MAJOR)
    cv.hgrad(1, 1, 24, 33, [m.l, m.b, m.s], mode='atop', a=0.8)
    cv.line([(8, 20), (18, 30)], 0.5, m.d)
    cv.line([(18, 20), (8, 30)], 0.5, m.d)
    cv.ellipse(13, 25, 3.5, 3.5, None, ink=C('#c8302a'), iw=0.8)
    ao(cv, 4, Hh, 18)


@prop('vending_machine')
def p_vending(cv, W, Hh):
    m = box3(cv, 2, 2, 26, Hh - 2, '#c8302a')
    cv.rect(4, 4, 15, 30, C('#e8f4ff'), ink=m.d, iw=DETAIL)
    rs = rng_of('vend')
    for r in range(4):
        for k in range(3):
            c = C(rs.choice(['#e84a3a', '#3a8ae8', '#f8d040', '#5ac08a', '#f4f0e8']))
            cv.rect(5.5 + k * 4.6, 6 + r * 7, 3.4, 5, c, ink=shade(c, 1.7), iw=0.3)
    cv.rect(20, 6, 6, 14, C('#2a2a30'), ink=m.d, iw=DETAIL)
    for k in range(4):
        cv.rect(21.5, 8 + k * 3, 3, 1.6, C('#f8e040'))
    cv.rect(6, 38, 18, 6, C('#1a1a20'), ink=m.d, iw=DETAIL)
    cv.text('FIZZ', 'sign', 3.4, 15, 46.5, C('#f4f0e8'), 'mm')
    ao(cv, 2, Hh, 26)


@prop('vent')
def p_vent(cv, W, Hh):
    m = M(C('#9aa0a8'))
    cv.rect(6, 12, 12, Hh - 12, m.b, ink=m.i, iw=MAJOR)
    cyl(cv, 6, 12, 12, Hh - 12, m, mode='atop')
    cv.ellipse(12, 8, 10, 6, m.b, ink=m.i, iw=MAJOR)
    for k in range(3):
        cv.ellipse(12, 6 + k * 2.4, 9 - k * 2, 1.4, m.s if k % 2 else m.l)
    cv.ellipse(12, 3, 3, 1.6, m.d)
    ao(cv, 5, Hh, 14)


@prop('workbench')
def p_workbench(cv, W, Hh):
    m = M(C('#9a6a3e'))
    cv.rect(1, 18, W - 2, 5, m.l, ink=m.i, iw=MAJOR)
    cv.rect(1, 18, W - 2, 1, m.h, mode='atop')
    for x in (4, W - 9, W / 2 - 2):
        cv.rect(x, 23, 5, Hh - 23, m.b, ink=m.i, iw=DETAIL)
    cv.rect(4, Hh - 10, W - 8, 3, m.s, ink=m.i, iw=DETAIL)
    # vice, toolbox, parts, lamp
    cv.rect(8, 11, 12, 7, C('#3a5a8a'), ink=C('#0e1a2a'), iw=DETAIL)
    cv.rect(10, 9, 8, 2.5, C('#8a8e9a'), ink=C('#1a1a20'), iw=0.3)
    cv.rect(40, 9, 26, 9, C('#c83a2a'), ink=C('#2a0a0a'), iw=DETAIL)
    cv.rect(46, 6, 14, 3, C('#2a2a30'))
    rs = rng_of('wbp')
    for k in range(8):
        cv.ellipse(76 + k * 4, 16.5, 1.4, 1, C(rs.choice(['#8a8e9a', '#c8a040', '#6a6a72'])), ink=C('#1a1a20'), iw=0.3)
    cv.line([(104, 18), (106, 6), (112, 4)], 0.9, C('#2a2a30'))
    cv.fill_poly([(110, 2), (117, 2), (116, 6), (111, 6)], C('#3a6a4a'), ink=C('#0e1a12'), iw=DETAIL)
    cv.rect(20, 25, 16, 10, C('#6a6a72'), ink=C('#1a1a20'), iw=DETAIL)
    ao(cv, 2, Hh, W - 4)
