"""16x16 inventory / UI icons (1px ink outline, transparent background)."""
import math
import numpy as np

from pixlib import Canvas, MAT, INK, CLEAR, hexc, mix, with_alpha

S = 16
STEAM = (236, 232, 240, 170)
STEAM2 = (236, 232, 240, 110)


def new():
    return Canvas(S, S)


def B(n):
    return MAT[n][0]


def D(n):
    return MAT[n][1]


def H(n):
    return MAT[n][2]


def steam(c, x, y0=1, h=4, phase=0):
    for i in range(h):
        dx = [0, 1, 1, 0, -1, -1][(i + phase) % 6]
        c.px(x + dx, y0 + i, STEAM if i < h - 1 else STEAM2)


def diag(c, s0, s1, hw, off=0.0, a=1.0, b=15.0):
    """Mask of a band along the up-right diagonal starting near (a, b).

    s0..s1 = distance along the diagonal (px); hw = half thickness (px)."""
    dx = c.xx + 0.5 - a
    dy = b - (c.yy + 0.5)
    along = (dx + dy) / math.sqrt(2)
    perp = (dx - dy) / math.sqrt(2)
    return (along >= s0) & (along <= s1) & (np.abs(perp - off) <= hw)


def heart_mask(c, x0, y0, w=12):
    rows = {
        12: ["..###..###..", ".#####.####.", "############", "############", "############",
             ".##########.", "..########..", "...######...", "....####....", ".....##....."],
        10: [".##...##..", "####.####.", "##########", "##########", ".########.", "..######..",
             "...####...", "....##...."],
        8: [".##.##..", "#######.", "#######.", ".#####..", "..###...", "...#...."],
    }[w]
    return c.bitmap(rows, x0, y0)


def bowl_shape(c, x0, y0, x1, y1, rim_h=3):
    """Returns (body_mask, rim_mask, inner_mask) for a bowl seen from slightly above."""
    rim = c.E(x0, y0, x1, y0 + rim_h)
    body = c.E(x0, y0 - (y1 - y0), x1, y1) & (c.yy >= y0 + rim_h // 2 + 1)
    inner = c.E(x0 + 1, y0 + 1, x1 - 1, y0 + rim_h - 1)
    return body, rim, inner


# ============================================================== FOOD
def coffee():
    c = new()
    body = c.R(3, 5, 10, 13) & ~c.R(3, 13, 3, 13) & ~c.R(10, 13, 10, 13)
    handle = c.E(8, 6, 13, 12) & ~c.E(10, 8, 11, 10) & (c.xx >= 10)
    c.shade(handle, 'white')
    c.shade(body, 'white')
    c.fill(c.R(3, 8, 10, 9) & body, B('red'))
    c.fill(c.R(9, 8, 10, 9) & body, D('red'))
    c.fill(c.R(3, 4, 10, 5), B('white'))
    c.fill(c.R(4, 4, 9, 4), B('coffee'))
    c.fill(c.R(4, 5, 9, 5), H('coffee'))
    c.fill(c.R(3, 4, 3, 4) | c.R(10, 4, 10, 4), CLEAR)
    c.outline()
    steam(c, 5, 0, 3, 0)
    steam(c, 8, 1, 3, 3)
    return c


def pancakes():
    c = new()
    plate = c.E(1, 11, 14, 14)
    c.shade(plate, 'white')
    c.fill(c.E(3, 12, 12, 13), H('white'))
    for y in (9, 7, 5):
        m = c.E(2, y, 13, y + 3)
        c.fill(m, D('bread'))
        c.fill(c.E(2, y, 13, y + 2), B('bread'))
    c.fill(c.E(4, 5, 11, 6), H('bread'))
    c.fill(c.R(6, 4, 9, 5), B('cheese'))
    c.fill(c.R(6, 4, 8, 4), H('cheese'))
    syrup = hexc('#7a3a1a')
    c.pxs([(4, 7), (3, 8), (3, 9), (11, 7), (12, 8), (12, 9), (12, 10), (5, 6), (10, 6), (7, 6)], syrup)
    c.outline()
    return c


def meatloaf():
    c = new()
    plate = c.E(1, 10, 14, 14)
    c.shade(plate, 'white')
    back = c.rrect(5, 4, 13, 11, 1)
    c.shade(back, 'meat')
    c.fill(c.R(5, 4, 13, 5) & back, B('tomato'))
    front = c.rrect(2, 6, 10, 12, 1)
    c.shade(front, 'meat')
    c.inline(front, D('meat'), 'r')
    c.fill(c.R(2, 6, 10, 7) & front, B('tomato'))
    c.fill(c.R(3, 6, 6, 6), H('tomato'))
    for x, y in [(4, 9), (7, 10), (8, 8), (5, 11)]:
        c.px(x, y, H('meat'))
    c.px(6, 9, D('meat'))
    c.outline()
    return c


def cherry_pie():
    c = new()
    top = c.P([(2, 9), (13, 9), (13, 4)])
    front = c.R(2, 9, 13, 13)
    c.fill(front, B('crust'))
    c.fill(c.R(2, 11, 13, 12), B('cherry'))
    c.fill(c.R(2, 11, 13, 11), D('cherry'))
    c.fill(c.R(2, 13, 13, 13), D('crust'))
    c.fill(c.R(2, 9, 13, 10), B('bread'))
    c.fill(top, B('bread'))
    for x in (6, 9, 12):
        c.fill(top & c.R(x, 0, x, 15), D('bread'))
    c.fill(top & (c.yy == 7), D('bread'))
    c.pxs([(4, 9), (8, 9), (11, 9)], H('bread'))
    c.px(5, 12, H('cherry'))
    c.px(10, 12, H('cherry'))
    cherry = c.C(11.5, 3.5, 1.8)
    c.ball(cherry, 'cherry')
    c.outline()
    c.pxs([(12, 1), (13, 0)], B('green'))
    return c


def club_sandwich():
    c = new()
    tri = c.P([(2, 13), (13, 13), (13, 3)])
    layers = [(12, 13, 'bread'), (11, 11, 'leaf'), (10, 10, 'tomato'), (8, 9, 'bread'),
              (7, 7, 'pink'), (6, 6, 'cheese'), (3, 5, 'bread')]
    for y0, y1, m in layers:
        c.fill(tri & c.R(0, y0, 15, y1), B(m))
    c.fill(tri & c.R(0, 13, 15, 13), D('bread'))
    c.fill(tri & c.edge(tri, 'r'), D('crust'))
    c.fill(tri & c.edge(tri, 't'), B('crust'))
    c.fill(c.R(8, 3, 9, 13) & tri & c.edge(tri, 'tl'), H('bread'))
    c.outline()
    c.fill(c.R(11, 1, 11, 7), B('tan'))
    c.fill(c.R(10, 0, 12, 1), B('red'))
    c.px(10, 1, B('green'))
    c.px(12, 0, B('green'))
    return c


def milkshake():
    c = new()
    glass = c.P([(4, 7), (11, 7), (10, 13), (5, 13)])
    c.shade(glass, 'pink')
    c.fill(c.R(5, 7, 5, 12) & glass, H('pink'))
    c.fill(c.R(6, 14, 9, 14), B('white'))
    cream = c.E(4, 3, 11, 8) | c.C(6, 4, 1.8) | c.C(9.5, 4.2, 1.8)
    c.shade(cream & ~glass | (cream & c.R(0, 0, 15, 7)), 'white')
    straw = c.L(10, 5, 13, 0, 1) | c.L(11, 5, 14, 0, 1)
    c.fill(straw & ~c.R(0, 4, 15, 15), B('red'))
    c.pxs([(12, 2), (13, 1)], B('white'))
    cherry = c.C(7.5, 2.5, 1.6)
    c.ball(cherry, 'cherry')
    c.outline()
    c.px(8, 0, B('green'))
    return c


def pork_bun():
    c = new()
    paper = c.R(1, 12, 14, 13)
    c.shade(paper, 'cream')
    bun = c.E(2, 4, 13, 15) & (c.yy <= 12)
    c.shade(bun, 'egg', dark_w=1)
    c.fill(c.E(3, 5, 9, 9), H('egg'))
    for (x, y) in [(7, 5), (8, 5), (6, 6), (9, 6), (5, 7), (10, 7)]:
        c.px(x, y, D('egg'))
    c.px(7, 4, D('egg'))
    c.px(8, 4, D('egg'))
    c.fill(c.R(7, 6, 8, 6), B('cherry'))
    c.outline()
    steam(c, 5, 0, 3, 1)
    steam(c, 10, 0, 3, 4)
    return c


def ramen():
    c = new()
    body, rim, inner = bowl_shape(c, 1, 6, 14, 14, 3)
    c.shade(body, 'red')
    c.fill(body & (c.yy == 11), B('white'))
    c.pxs([(4, 11), (7, 11), (10, 11)], B('red'))
    c.fill(rim, B('white'))
    c.fill(inner, B('broth'))
    c.fill(c.R(3, 7, 7, 8) & inner, B('noodle'))
    c.pxs([(4, 8), (6, 7)], D('noodle'))
    c.fill(c.E(8, 7, 11, 8), B('egg'))
    c.pxs([(9, 7), (10, 7)], B('yellow'))
    c.fill(c.R(11, 7, 12, 8) & inner, B('green'))
    c.fill(c.L(4, 6, 12, 1) | c.L(6, 6, 14, 1), B('tan'))
    c.fill((c.L(4, 6, 12, 1) | c.L(6, 6, 14, 1)) & (c.yy <= 2), D('tan'))
    c.outline()
    return c


def dumplings():
    c = new()
    plate = c.E(1, 10, 14, 14)
    c.shade(plate, 'white')

    def dumpling(x0, y0):
        m = c.E(x0, y0, x0 + 6, y0 + 8) & (c.yy <= y0 + 5)
        c.shade(m, 'noodle')
        c.fill(m & (c.yy == y0 + 5), B('bread'))
        for i in range(1, 6, 2):
            c.px(x0 + i, y0 + 1 + (1 if i in (1, 5) else 0), D('noodle'))
        c.inline(m, D('noodle'), 'r')

    dumpling(2, 4)
    dumpling(8, 4)
    dumpling(5, 7)
    c.outline()
    return c


def green_tea():
    c = new()
    saucer = c.E(1, 11, 14, 14)
    c.shade(saucer, 'cream')
    cup = c.P([(3, 6), (12, 6), (11, 11), (4, 11)]) | c.E(4, 9, 11, 12)
    c.shade(cup, 'white')
    c.fill(c.R(3, 8, 12, 9) & cup, B('green'))
    c.fill(c.R(10, 8, 12, 9) & cup, D('green'))
    rim = c.E(2, 4, 13, 7)
    c.fill(rim, B('white'))
    c.fill(c.E(3, 5, 12, 6), B('leaf'))
    c.fill(c.R(5, 5, 7, 5), H('leaf'))
    c.outline()
    steam(c, 6, 0, 3, 2)
    steam(c, 9, 1, 3, 5)
    return c


def spicy_udon():
    c = new()
    body, rim, inner = bowl_shape(c, 1, 6, 14, 14, 3)
    c.shade(body, 'black')
    c.fill(body & (c.yy == 11), B('red'))
    c.fill(rim, B('charcoal'))
    c.fill(inner, B('chili'))
    for x in (3, 6, 9):
        c.fill(c.R(x, 7, x + 1, 8) & inner, B('noodle'))
    c.pxs([(4, 7), (7, 8), (10, 7)], D('noodle'))
    c.pxs([(12, 7), (5, 8)], B('leaf'))
    pep = c.P([(8, 2), (13, 5), (12, 6), (8, 4)])
    c.shade(pep, 'tomato')
    c.outline()
    c.pxs([(7, 2), (7, 1)], B('green'))
    return c


def bean_chili():
    c = new()
    body, rim, inner = bowl_shape(c, 1, 6, 14, 14, 3)
    c.shade(body, 'tan')
    c.fill(body & (c.yy == 10), D('tan'))
    c.fill(rim, B('cream'))
    c.fill(inner, B('chili'))
    c.pxs([(4, 7), (7, 8), (9, 7), (11, 8), (5, 8)], D('meat'))
    c.pxs([(6, 7), (10, 8), (12, 7)], B('cheese'))
    spoon = c.L(9, 7, 13, 1, 1)
    c.fill(spoon, B('steel'))
    c.fill(c.E(11, 0, 14, 3), B('steel'))
    c.px(12, 1, H('steel'))
    c.outline()
    return c


def grilled_cheese():
    c = new()
    bot = c.rrect(2, 9, 13, 13, 1)
    c.shade(bot, 'crust')
    cheese = c.R(1, 8, 14, 10)
    c.fill(cheese, B('cheese'))
    top = (c.C(5, 5, 3.2) | c.C(10, 5, 3.2) | c.R(2, 5, 13, 9)) & c.R(2, 2, 13, 9)
    c.fill(top, B('crust'))
    inner = c.erode(top, 1)
    c.fill(inner, B('bread'))
    c.fill(inner & c.edge(inner, 'lt'), H('bread'))
    for x0 in (5, 9):
        c.fill(c.L(x0 - 1, 8, x0 + 3, 4) & inner, D('bread'))
    drips = c.R(3, 10, 4, 12) | c.R(8, 10, 8, 13) | c.R(11, 10, 12, 11) | c.R(14, 9, 14, 11)
    c.fill(drips | c.R(1, 9, 14, 9), B('cheese'))
    c.pxs([(3, 10), (8, 10), (1, 9)], H('cheese'))
    c.pxs([(4, 12), (8, 13), (12, 11)], D('cheese'))
    c.outline()
    return c


def iron_stew():
    c = new()
    body = c.E(2, 2, 13, 14) & (c.yy >= 8)
    c.shade(body, 'black')
    c.fill(c.R(1, 7, 14, 8), B('charcoal'))
    c.fill(c.R(1, 7, 14, 7), H('charcoal'))
    c.fill(c.R(0, 8, 1, 9) | c.R(14, 8, 15, 9), B('charcoal'))
    stew = c.E(2, 4, 13, 8) & (c.yy <= 7)
    c.fill(stew, B('broth'))
    c.pxs([(4, 6), (5, 6)], B('orange'))
    c.pxs([(8, 5), (9, 5)], B('cream'))
    c.pxs([(11, 6), (7, 6)], B('meat'))
    c.pxs([(6, 5), (10, 6)], B('leaf'))
    c.outline()
    steam(c, 5, 0, 3, 0)
    steam(c, 10, 0, 3, 3)
    return c


def hard_eggs():
    c = new()
    egg = c.E(2, 2, 8, 11)
    c.ball(egg, 'egg')
    c.inline(egg & ~c.edge(egg, 'lt'), D('egg'), 'rb')
    half = c.E(6, 7, 14, 13)
    c.shade(half, 'egg')
    c.fill(c.E(6, 7, 14, 10), B('egg'))
    yolk = c.E(8, 8, 12, 10)
    c.fill(yolk, B('yellow'))
    c.px(9, 8, H('yellow'))
    c.outline()
    c.pxs([(3, 13), (5, 14)], B('white'))
    return c


def hot_dog():
    c = new()
    back = c.rrect(2, 4, 13, 9, 2)
    c.shade(back, 'bread', light=False)
    sausage = c.rrect(1, 6, 14, 9, 2)
    c.shade(sausage, 'sausage')
    c.fill(c.R(2, 6, 13, 6) & sausage, H('sausage'))
    for x in range(3, 13):
        c.px(x, 6 + (x % 2), B('yellow'))
    front = c.rrect(2, 8, 13, 13, 2)
    c.shade(front, 'bread')
    c.fill(c.R(3, 12, 12, 12) & front, D('bread'))
    c.outline()
    return c


def nachos():
    c = new()
    chip = hexc('#e8b048')
    chip_d = hexc('#b07a28')
    for pts in [[(1, 10), (4, 3), (7, 10)], [(9, 10), (13, 4), (14, 10)], [(5, 10), (8, 1), (11, 10)]]:
        m = c.P(pts)
        c.fill(m, chip)
        c.fill(c.edge(m, 'rb'), chip_d)
    c.pxs([(7, 4), (8, 5), (3, 6), (12, 6), (8, 7), (4, 8), (11, 8)], B('cheese'))
    c.pxs([(9, 6), (12, 8)], B('green'))
    tray = c.P([(1, 9), (14, 9), (12, 14), (3, 14)])
    c.fill(tray, B('white'))
    for x in range(1, 15, 3):
        c.fill(tray & c.R(x, 0, x + 1, 15), B('red'))
    c.fill(tray & (c.yy == 9), H('white'))
    c.pxs([(5, 9), (6, 10), (10, 9)], B('cheese'))
    c.outline()
    return c


def soda():
    c = new()
    can = c.rrect(4, 2, 11, 14, 1)
    c.fill(can, B('red'))
    c.fill(can & c.R(4, 0, 5, 15), H('red'))
    c.fill(can & c.R(10, 0, 11, 15), D('red'))
    wave = c.empty()
    for x in range(4, 12):
        y = 8 + int(round(math.sin((x - 4) * 0.9)))
        wave[y, x] = True
        wave[y + 1, x] = True
    c.fill(wave & can, B('white'))
    c.fill(c.R(4, 2, 11, 3) & can, B('steel'))
    c.fill(c.R(5, 2, 10, 2), H('steel'))
    c.fill(c.R(4, 14, 11, 14) & can, B('steel'))
    c.px(8, 1, B('steel'))
    c.px(9, 1, B('steel'))
    c.outline()
    return c


def popcorn():
    c = new()
    box = c.P([(3, 8), (12, 8), (11, 14), (4, 14)])
    c.fill(box, B('white'))
    for x in (4, 7, 10):
        c.fill(box & c.R(x, 0, x + 1, 15), B('red'))
    c.fill(box & c.edge(box, 'r'), D('red'))
    puffs = [(4.5, 6.5), (7, 5), (9.5, 6), (11.5, 7), (6, 3.5), (9, 3), (3.5, 8), (12, 8.5), (7.5, 7)]
    for (x, y) in puffs:
        m = c.C(x, y, 1.7)
        c.fill(m & ~box, B('cream'))
        c.px(int(x) - 1 if x > 1 else 0, int(y) - 1, H('cream'))
    c.pxs([(6, 5), (10, 4), (8, 6)], B('cheese'))
    c.outline()
    return c


def fish_taco():
    c = new()
    ang = -0.45
    cx, cy, r = 8.0, 6.5, 6.6
    ca, sa = math.cos(ang), math.sin(ang)
    def rot(x, y):
        return (cx + x * ca - y * sa, cy + x * sa + y * ca)
    pts = [rot(r * math.cos(t), r * math.sin(t)) for t in np.linspace(0, math.pi, 15)]
    shell = c.P(pts)
    # filling bumps along the straight edge
    fill = c.empty()
    for k, t in enumerate(np.linspace(-0.8, 0.8, 5)):
        x, y = rot(t * r, -0.6)
        fill |= c.C(x, y, 2.0)
    fill &= ~shell
    c.fill(fill, B('leaf'))
    for k, t in enumerate(np.linspace(-0.7, 0.7, 4)):
        x, y = rot(t * r, -1.2)
        c.px(int(x), int(y), [hexc('#e0a858'), B('white'), hexc('#a050a0'), B('tomato')][k])
    x, y = rot(0.1 * r, -1.6)
    c.fill(c.C(x, y, 1.4) & fill, hexc('#e0a858'))
    taco = (hexc('#e8b850'), hexc('#b07a30'), hexc('#f8d888'))
    c.shade(shell, *taco)
    for (x, y) in [(6, 10), (9, 9), (11, 7), (7, 12), (4, 8)]:
        if shell[y, x]:
            c.px(x, y, taco[1])
    c.outline()
    return c


def thermos_soup():
    c = new()
    th = c.rrect(3, 3, 8, 14, 1)
    c.shade(th, 'green')
    c.fill(c.R(3, 7, 8, 9) & th, B('tan'))
    c.fill(c.R(8, 7, 8, 9) & th, D('tan'))
    lid = c.R(3, 1, 8, 3)
    c.shade(lid, 'steel')
    cup = c.P([(8, 9), (14, 9), (13, 14), (9, 14)])
    c.shade(cup, 'red')
    c.fill(c.E(8, 8, 14, 10), B('broth'))
    c.fill(c.R(10, 9, 11, 9), H('broth'))
    c.outline()
    steam(c, 11, 4, 3, 1)
    return c


def jerky():
    c = new()
    jk = hexc('#8a3a24')
    jd = hexc('#5a2216')
    jl = hexc('#b05a3a')
    s1 = c.P([(1, 10), (9, 2), (11, 3), (12, 2), (13, 4), (4, 13), (2, 12)])
    c.fill(s1, jk)
    c.fill(c.edge(s1, 'rb'), jd)
    s2 = c.P([(5, 13), (12, 6), (14, 7), (14, 9), (8, 14), (6, 14)])
    c.fill(s2, jk)
    c.fill(c.edge(s2, 'rb'), jd)
    c.fill(c.edge(s2, 'lt') & ~s1 & c.shift(s1, 1, 1), jd)
    c.pxs([(5, 8), (8, 5), (7, 7), (10, 4), (9, 11), (12, 8), (4, 10)], jl)
    c.outline()
    return c


def clam_chowder():
    c = new()
    body, rim, inner = bowl_shape(c, 1, 6, 14, 14, 3)
    c.shade(body, 'white')
    c.fill(body & (c.yy == 10), B('blue'))
    c.fill(rim, B('white'))
    c.fill(inner, B('cream'))
    c.pxs([(4, 8), (11, 7), (5, 7)], B('leaf'))
    c.pxs([(9, 8), (3, 7)], H('cream'))
    shell = c.E(5, 2, 11, 9) & (c.yy <= 6)
    c.shade(shell, 'tan')
    for x in (6, 8, 10):
        c.fill(shell & c.L(8, 7, x, 2), D('tan'))
    c.fill(c.R(7, 6, 9, 7), D('tan'))
    c.outline()
    return c


def empanada():
    c = new()
    m = c.E(1, 3, 14, 22) & (c.yy <= 12)
    c.shade(m, 'bread')
    c.fill(c.E(3, 5, 9, 9) & m, H('bread'))
    arc = c.E(1, 3, 14, 22) & ~c.E(3, 5, 12, 22) & (c.yy <= 12)
    for i, (y, x) in enumerate(zip(*np.nonzero(arc))):
        if (x + y) % 2 == 0:
            c.px(x, y, D('bread'))
    c.fill(c.R(1, 12, 14, 12) & m, D('bread'))
    c.outline()
    c.fill(c.R(2, 13, 13, 13), with_alpha(INK, 255))
    c.fill(c.R(2, 14, 13, 14) & c.E(1, 13, 14, 15), CLEAR)
    return c


# ============================================================== MEDICINE
def bandage():
    c = new()
    strip = c.P([(1, 11), (10, 2), (14, 5), (5, 14)])
    strip = c.dilate(c.erode(strip, 1), 1) & strip
    c.shade(strip, 'tan')
    pad = c.P([(5, 8), (8, 5), (10, 7), (7, 10)])
    c.shade(pad, 'cream')
    for (x, y) in [(3, 11), (4, 10), (11, 4), (12, 5), (3, 10)]:
        c.px(x, y, D('tan'))
    c.outline()
    return c


def tonic():
    c = new()
    amber = hexc('#b8682a')
    amber_d = hexc('#7a401a')
    amber_l = hexc('#e09a4a')
    body = c.rrect(3, 6, 12, 14, 2)
    c.fill(body, amber)
    c.fill(body & c.edge(body, 'rb'), amber_d)
    c.fill(c.R(4, 7, 4, 12), amber_l)
    neck = c.R(6, 3, 9, 6)
    c.fill(neck, amber)
    c.fill(c.R(6, 4, 6, 6), amber_l)
    c.fill(c.R(5, 1, 10, 3), B('red'))
    c.fill(c.R(5, 1, 10, 1), H('red'))
    label = c.R(5, 9, 10, 13)
    c.fill(label, B('cream'))
    c.fill(c.R(7, 10, 8, 12) | c.R(6, 11, 9, 11), B('green'))
    c.outline()
    return c


def vitamin_pack():
    c = new()
    card = c.rrect(2, 2, 13, 14, 1)
    c.shade(card, 'steel')
    c.fill(c.R(2, 8, 13, 8) & card, D('steel'))
    colors = [('orange', 'cream'), ('yellow', 'cream'), ('red', 'white'), ('blue', 'white')]
    i = 0
    for y in (4, 10):
        for x in (3, 9):
            a, b = colors[i]
            i += 1
            c.fill(c.R(x, y, x + 3, y + 2), D('steel'))
            c.fill(c.R(x, y, x + 1, y + 1), B(a))
            c.fill(c.R(x + 2, y, x + 3, y + 1), B(b))
            c.px(x, y, H(a))
    c.outline()
    return c


def energy_drink():
    c = new()
    can = c.rrect(5, 1, 10, 14, 1)
    c.fill(can, B('navy'))
    c.fill(can & c.R(5, 0, 5, 15), H('navy'))
    c.fill(can & c.R(10, 0, 10, 15), D('navy'))
    c.fill(c.R(5, 1, 10, 2) & can, B('steel'))
    c.fill(c.R(5, 14, 10, 14) & can, B('steel'))
    bolt = c.bitmap(["..##", ".##.", "####", ".##.", "##..", "#..."], 6, 5)
    c.fill(bolt, B('neon'))
    c.px(8, 5, H('neon'))
    c.outline()
    return c


def smelling_salts():
    c = new()
    vial = c.C(7.5, 10.5, 4.2)
    c.fill(vial, B('glass'))
    c.fill(vial & (c.yy >= 10), B('white'))
    c.fill(vial & (c.yy >= 10) & c.edge(vial, 'rb'), D('white'))
    c.pxs([(5, 11), (8, 12), (10, 11), (6, 13)], B('steel'))
    c.fill(vial & c.edge(vial, 'rb') & (c.yy < 10), D('glass'))
    c.pxs([(5, 8), (5, 9)], H('glass'))
    neck = c.R(6, 3, 9, 6)
    c.fill(neck, B('glass'))
    c.fill(c.R(5, 1, 10, 3), B('tan'))
    c.fill(c.R(5, 1, 10, 1), H('tan'))
    c.outline()
    vap = (170, 240, 160, 200)
    c.pxs([(2, 3), (1, 2), (2, 1), (13, 3), (14, 2), (13, 1), (12, 5), (3, 5)], vap)
    return c


# ============================================================== KEY ITEMS
def postcard():
    c = new()
    card = c.R(1, 3, 14, 12)
    c.shade(card, 'cream')
    c.fill(c.R(10, 4, 13, 7), B('white'))
    c.fill(c.R(11, 5, 12, 6), B('red'))
    c.fill(c.R(7, 4, 7, 11), D('cream'))
    for y in (8, 10):
        c.fill(c.R(9, y, 13, y), B('gray'))
    for y in (5, 7, 9):
        c.fill(c.R(2, y, 5, y), D('cream'))
    c.pxs([(9, 4), (9, 6), (8, 5)], B('blue'))
    c.outline()
    return c


def satchel():
    c = new()
    strap = c.E(3, 1, 12, 11) & ~c.E(5, 3, 10, 9) & (c.yy <= 6)
    c.shade(strap, 'brown')
    body = c.rrect(1, 6, 14, 14, 2)
    c.shade(body, 'brown')
    flap = c.rrect(1, 6, 14, 10, 1)
    c.shade(flap, 'wood')
    c.fill(c.R(1, 10, 14, 10) & flap, D('brown'))
    c.fill(c.R(7, 9, 8, 11), B('gold'))
    c.px(7, 9, H('gold'))
    c.outline()
    return c


def manifest():
    c = new()
    board = c.rrect(2, 2, 13, 14, 1)
    c.shade(board, 'wood')
    paper = c.R(3, 4, 12, 13)
    c.shade(paper, 'paper', light=False)
    for y in (6, 8, 10, 12):
        c.fill(c.R(4, y, 5, y), B('gray'))
        c.fill(c.R(7, y, 11, y), B('gray'))
    c.pxs([(4, 6), (5, 8)], B('green'))
    clip = c.R(5, 1, 10, 4)
    c.shade(clip, 'steel')
    c.fill(c.R(7, 1, 8, 1), D('steel'))
    c.outline()
    return c


def toolbox():
    c = new()
    handle = c.R(5, 3, 10, 7) & ~c.R(6, 4, 9, 7)
    c.shade(handle, 'charcoal')
    body = c.R(1, 7, 14, 14)
    c.shade(body, 'red')
    c.fill(c.R(1, 7, 14, 8), D('red'))
    c.fill(c.R(1, 7, 14, 7), B('red'))
    c.fill(c.R(2, 7, 13, 7), H('red'))
    c.fill(c.R(7, 9, 8, 10), B('steel'))
    c.fill(c.R(1, 12, 14, 12), D('red'))
    c.outline()
    return c


def parcel():
    c = new()
    front = c.R(2, 6, 10, 14)
    top = c.P([(2, 6), (5, 3), (13, 3), (10, 6)])
    side = c.P([(10, 6), (13, 3), (13, 11), (10, 14)])
    c.fill(front, B('cardboard'))
    c.fill(top, H('cardboard'))
    c.fill(side, D('cardboard'))
    tape = hexc('#e8d8a0')
    c.fill(c.P([(5, 6), (8, 3), (9, 3), (6, 6)]), tape)
    c.fill(c.R(5, 6, 6, 14), tape)
    c.fill(c.R(7, 9, 9, 11), B('white'))
    c.fill(c.R(7, 10, 9, 10), B('gray'))
    c.outline()
    return c


def count_book():
    c = new()
    c.fill(c.R(4, 2, 13, 14), B('cream'))
    c.fill(c.R(4, 14, 13, 14), D('cream'))
    for y in range(3, 14, 2):
        c.px(13, y, D('cream'))
    cover = c.R(2, 1, 12, 13)
    c.shade(cover, 'green')
    c.fill(c.R(2, 1, 3, 13), D('green'))
    c.fill(c.R(2, 3, 3, 3) | c.R(2, 11, 3, 11), B('gold'))
    c.text('#', 6, 2, D('gold'))
    c.text('#', 5, 2, B('gold'))
    c.outline()
    return c


def payroll_pages():
    c = new()
    back = c.R(4, 1, 13, 11)
    c.shade(back, 'paper', light=False)
    front = c.R(2, 4, 11, 14)
    c.shade(front, 'paper')
    c.inline(front, D('paper'), 'lt')
    c.fill(c.R(2, 4, 11, 4), B('paper'))
    c.text('$', 3, 4, B('green'))
    for y in (7, 9, 11, 13):
        c.fill(c.R(9, y, 10, y), B('gray'))
    c.fill(c.R(3, 13, 7, 13), B('gray'))
    c.fill(c.R(10, 2, 10, 6) | c.R(12, 2, 12, 5) | c.R(11, 1, 11, 1), B('steel'))
    c.outline()
    return c


def cassette():
    c = new()
    body = c.rrect(1, 3, 14, 12, 1)
    c.shade(body, 'charcoal')
    c.fill(c.R(3, 4, 12, 7), B('cream'))
    c.fill(c.R(3, 6, 12, 6), B('red'))
    c.fill(c.R(5, 8, 10, 10), INK)
    c.fill(c.C(5.5, 9.5, 1.6) | c.C(10.5, 9.5, 1.6), B('white'))
    c.px(5, 9, INK)
    c.px(10, 9, INK)
    c.fill(c.R(7, 9, 8, 9), D('coffee'))
    c.fill(c.P([(4, 12), (11, 12), (10, 11), (5, 11)]), B('gray'))
    c.outline()
    return c


def gate_key():
    c = new()
    bow = c.C(4.5, 4.5, 3.6) & ~c.C(4.5, 4.5, 1.5)
    shaft = diag(c, 0, 12, 0.9, a=5.0, b=6.0)
    shaft = c.L(6, 6, 13, 13, 2)
    teeth = c.R(10, 13, 11, 14) | c.R(13, 10, 14, 11) | c.R(12, 12, 13, 13)
    m = bow | shaft | teeth
    c.shade(m, 'iron')
    c.fill(bow & c.edge(bow, 'lt'), H('iron'))
    c.fill(c.L(5, 5, 6, 6), B('iron'))
    c.outline()
    tag = c.R(9, 1, 13, 5)
    c.fill(c.R(9, 1, 13, 5), B('cream'))
    c.fill(c.R(10, 3, 12, 3), B('red'))
    c.fill(c.R(9, 5, 13, 5), D('cream'))
    c.pxs([(8, 2), (7, 3)], B('tan'))
    c2 = Canvas(16, 16)
    c2.a = c.a.copy()
    # re-outline the tag only
    o = c.dilate(tag, 1) & ~c.alpha
    c.fill(o, INK)
    return c


def photo():
    c = new()
    frame = c.R(2, 2, 13, 14)
    c.shade(frame, 'white', light=False)
    pic = c.R(4, 4, 11, 10)
    c.fill(pic, B('blue'))
    c.fill(c.R(4, 4, 11, 5), H('blue'))
    c.fill(c.R(4, 7, 11, 7), B('orange'))
    c.fill(c.R(4, 8, 11, 10), B('navy'))
    c.fill(c.R(6, 6, 6, 9) | c.R(9, 6, 9, 9), INK)
    c.px(6, 5, B('skin'))
    c.px(9, 5, B('tanskin'))
    c.fill(c.R(6, 1, 9, 3), (232, 224, 180, 200))
    c.outline()
    return c


def ledger():
    c = new()
    pages = c.R(4, 3, 13, 14)
    c.fill(pages, B('cream'))
    for y in (5, 7, 9, 11, 13):
        c.px(13, y, D('cream'))
    for x in (6, 9, 12):
        c.px(x, 14, D('cream'))
    cover = c.R(2, 2, 12, 13)
    c.shade(cover, 'red')
    c.fill(c.R(2, 2, 3, 13), D('red'))
    c.fill(c.R(2, 4, 3, 4) | c.R(2, 11, 3, 11), B('gold'))
    for (x, y) in [(11, 2), (12, 2), (12, 3), (11, 13), (12, 13), (12, 12)]:
        c.px(x, y, B('gold'))
    c.fill(c.R(6, 5, 10, 7), B('gold'))
    c.fill(c.R(7, 6, 9, 6), D('gold'))
    c.outline()
    return c


def eviction_notice():
    c = new()
    sheet = c.R(3, 2, 12, 14)
    c.shade(sheet, 'paper')
    c.fill(c.R(4, 3, 11, 5), B('danger'))
    c.fill(c.R(5, 4, 10, 4), B('white'))
    for y in (7, 9, 11):
        c.fill(c.R(4, y, 11 - (y == 11) * 3, y), B('gray'))
    st = c.C(10, 12, 2.2) & ~c.C(10, 12, 1.0)
    c.fill(st, B('red'))
    c.outline()
    c.fill(c.C(7.5, 1.5, 1.4), B('red'))
    c.px(7, 1, H('red'))
    return c


def leash():
    c = new()
    loop = c.E(2, 1, 12, 7) & ~c.E(4, 3, 10, 5)
    c.shade(loop, 'red')
    strap = c.Lpath([(7, 7), (5, 9), (6, 11), (9, 11), (10, 9), (12, 10)], 2)
    c.shade(strap, 'red')
    snap = c.bitmap([".##.", "#..#", "#...", "#..#", ".##."], 11, 10)
    c.fill(snap, B('steel'))
    c.fill(c.R(11, 11, 11, 13), H('steel'))
    c.fill(c.R(12, 14, 13, 14), D('steel'))
    c.outline()
    return c

def arcade_log():
    c = new()
    cover = c.rrect(2, 2, 13, 14, 1)
    c.shade(cover, 'purple')
    for x in (4, 7, 10):
        c.fill(c.R(x, 1, x, 3), B('steel'))
        c.px(x, 1, H('steel'))
    base = c.R(5, 11, 10, 12)
    c.fill(base, INK)
    c.fill(c.R(7, 7, 8, 10), INK)
    c.fill(c.C(7.5, 6.5, 2.0), B('red'))
    c.px(7, 5, H('red'))
    c.px(10, 11, B('yellow'))
    c.outline()
    return c


# ============================================================== GEAR
def courier_sneakers():
    c = new()
    upper = c.P([(2, 11), (2, 5), (6, 4), (8, 7), (12, 8), (14, 10), (14, 11)])
    c.shade(upper, 'red')
    c.fill(c.R(3, 6, 6, 6) & upper, B('white'))
    c.pxs([(7, 7), (9, 8)], B('cream'))
    stripe = c.L(4, 10, 9, 8)
    c.fill(stripe & upper, B('mustard'))
    sole = c.rrect(1, 11, 14, 13, 1)
    c.shade(sole, 'white')
    c.fill(c.R(1, 13, 14, 13) & sole, B('gray'))
    c.outline()
    for y in (6, 8):
        c.px(0, y, B('cream'))
    return c


def champion_wraps():
    c = new()
    tail = c.P([(8, 10), (14, 12), (13, 14), (7, 13)])
    c.shade(tail, 'white')
    c.fill(c.R(12, 13, 14, 14) & tail | c.R(13, 12, 14, 12) & tail, B('red'))
    body = c.R(4, 3, 9, 12) | c.E(6, 3, 11, 12)
    c.shade(body, 'white')
    c.fill(body & (c.yy == 3) | body & (c.yy == 12), B('red'))
    c.fill(body & (c.yy == 4), H('white'))
    face = c.E(1, 3, 7, 12)
    c.fill(face, B('white'))
    c.fill(c.E(2, 4, 6, 11) & ~c.E(3, 5, 5, 10), B('gray'))
    c.fill(c.E(3, 6, 5, 9), D('white'))
    c.fill(c.R(4, 7, 4, 8), INK)
    c.fill(c.edge(face, 'all') & (c.xx <= 2), B('red'))
    c.outline()
    return c


def _jacket(base, dark, trim, emblem=None):
    c = new()
    rows = [
        "....aaaaaa....",
        "...abbccbba...",
        "..aabc..cbaa..",
        ".aaabc..cbaaa.",
        ".aaaab..baaaa.",
        "aaaaab..baaaad",
        "aaaaab..baaaad",
        "aaaaab..baaaad",
        "aaaaab..baaaad",
        "taaaab..baaaat",
        "taaaab..baaaat",
        "tdtttb..btttdt",
    ]
    rows = [
        "....aaaaaa....",
        "...accddcca...",
        "..aac.ee.caa..",
        ".aaac.ee.caaa.",
        "aaaaaeeeeaaaad",
        "aaaaaaeeaaaaad",
        "aaaaaaeeaaaaad",
        "aaaaaaeeaaaaad",
        "aaaaaaeeaaaaad",
        "taaaaaeeaaaaat",
        "taaaaaeeaaaaat",
        "ttttttttttttt.",
    ]
    pal = {'a': base, 'c': trim, 'd': dark, 'e': dark, 't': trim}
    c.art(rows, 1, 2, pal)
    # sleeves separation lines
    for y in range(6, 13):
        c.px(3, y, dark)
        c.px(12, y, dark)
    c.fill(c.R(7, 5, 8, 13), dark)
    c.fill(c.R(5, 4, 10, 4) & ~c.R(7, 4, 8, 4), base)
    c.fill(c.R(2, 3, 2, 12) & c.alpha, mix(base, (255, 255, 255, 255), 0.25))
    if emblem:
        emblem(c)
    c.outline()
    return c


def token_jacket():
    def emb(c):
        coin = c.C(10.5, 7.5, 1.7)
        c.fill(coin, B('gold'))
        c.px(10, 7, H('gold'))
        c.px(11, 8, D('gold'))
    return _jacket(B('purple'), D('purple'), B('mustard'), emb)


def lucky_bandana():
    c = new()
    tri = c.P([(1, 4), (14, 4), (7.5, 13)])
    c.fill(tri, B('red'))
    c.fill(c.R(0, 4, 15, 5) & tri, D('red'))
    c.fill(c.edge(tri, 'rb') & (c.yy > 5), D('red'))
    for (x, y) in [(4, 7), (8, 7), (11, 7), (6, 9), (9, 9), (7, 11)]:
        c.px(x, y, B('white'))
    c.fill(c.R(0, 3, 2, 4) | c.R(13, 3, 15, 4), B('red'))
    c.px(1, 2, B('red'))
    c.px(14, 2, B('red'))
    c.fill(c.R(7, 5, 8, 5), B('mustard'))
    c.outline()
    return c


# ============================================================== MANUALS
EMBLEMS = {
    'shoulder': ["...#...", "...##..", "#######", "#######", "...##..", "...#..."],
    'rising': ["...#...", "..###..", ".#####.", "...#...", "...#...", ".#.#...", "..##..."],
    'heel': ["..###..", "...#...", "...#...", ".#####.", "..###..", "...#..."],
    'rapid': ["#..#...", ".#..#..", "..#..#.", ".#..#..", "#..#..."],
    'sweep': [".####..", "#....#.", "#....##", "....###", "....##."],
    'counter': ["..#....", ".######", "..#....", "....#..", "######.", "....#.."],
    'giant': [".###...", "#...#..", "#...#.#", "#....##", ".#..###", "..##..."],
    'retrieve': ["...##..", "..#..#.", "#....#.", "##...#.", "###.#..", "..##..."],
    'slam': ["#..#..#", ".#.#.#.", "..###..", "#######", "..###..", ".#.#.#."],
    'oath': ["...#...", "..###..", "#######", ".#####.", "..###..", ".##.##."],
}
MANUAL_COLORS = {
    'shoulder': 'blue', 'rising': 'green', 'heel': 'orange', 'rapid': 'red', 'sweep': 'teal',
    'counter': 'purple', 'giant': 'brown', 'retrieve': 'pink', 'slam': 'gray', 'oath': 'black',
}


def manual(kind):
    def f():
        c = new()
        col = MANUAL_COLORS[kind]
        pages = c.R(4, 2, 13, 14)
        c.fill(pages, B('cream'))
        c.fill(c.R(4, 14, 13, 14), D('cream'))
        for y in range(3, 14, 2):
            c.px(13, y, D('cream'))
        cover = c.R(2, 1, 12, 13)
        c.shade(cover, col)
        c.fill(c.R(2, 1, 3, 13), D(col))
        trim = B('gold') if kind == 'oath' else H(col)
        c.px(3, 3, trim)
        c.px(3, 11, trim)
        emb = EMBLEMS[kind]
        w = len(emb[0])
        h = len(emb)
        x0 = 5 + (7 - w) // 2
        y0 = 4 + (7 - h) // 2
        plate = c.rrect(4, 3, 11, 11, 1)
        c.fill(plate, D(col) if kind != 'oath' else B('charcoal'))
        m = c.bitmap(emb, x0 - 1 + 1, y0)
        c.fill(m, B('gold') if kind == 'oath' else B('cream'))
        if kind == 'oath':
            c.fill(c.edge(cover, 'all') & ~c.R(2, 1, 3, 13), B('gold'))
        c.outline()
        return c
    return f


# ============================================================== WEAPON ICONS
def w_wrench():
    c = new()
    handle = c.L(3, 12, 9, 6, 2)
    head = c.C(11, 4.5, 3.6)
    m = handle | head | c.C(3, 12.5, 1.5)
    c.shade(m, 'steel')
    jaw = c.P([(11, 4), (14, 1), (15, 2), (12, 5)]) | c.R(11, 3, 12, 5) & c.C(11, 4.5, 1.3)
    c.fill(jaw, CLEAR)
    c.fill(c.L(4, 11, 8, 7), D('steel'))
    c.outline()
    return c


def w_baton():
    c = new()
    m = diag(c, 1.0, 19.5, 1.25)
    c.shade(m, 'black')
    c.fill(diag(c, 2.0, 19.0, 0.5, off=-0.6) & m, H('black'))
    for s in (3.0, 5.0, 7.0):
        c.fill(diag(c, s, s + 0.8, 2) & m, B('charcoal'))
    c.fill(diag(c, 8.5, 9.5, 2) & m, B('steel'))
    c.outline()
    return c


def w_bat():
    c = new()
    m = diag(c, 1.5, 10, 0.75) | diag(c, 10, 13, 1.25) | diag(c, 13, 19.6, 1.8)
    m |= diag(c, 0.5, 1.8, 1.4)
    c.shade(m, 'tan')
    for s in (3.0, 5.0, 7.0):
        c.fill(diag(c, s, s + 0.7, 2) & m, B('charcoal'))
    c.fill(diag(c, 0.0, 1.6, 2) & m, B('wood'))
    c.outline()
    return c


def w_pipe():
    c = new()
    m = diag(c, 1.0, 17.0, 1.3)
    c.shade(m, 'iron')
    c.fill(diag(c, 1.5, 17, 0.45, off=-0.7) & m, B('steel'))
    fit = diag(c, 16.0, 19.5, 2.0)
    c.shade(fit, 'steel')
    for s, o in [(6, 0.3), (10, -0.3), (12, 0.5)]:
        c.fill(diag(c, s, s + 0.9, 0.6, off=o) & m, B('rust'))
    c.outline()
    return c


def w_broom():
    c = new()
    stick = diag(c, 0.5, 12, 0.8)
    c.shade(stick, 'wood')
    head = c.P([(8, 5), (10, 3), (15, 1), (14, 6), (12, 7)])
    head = c.P([(8, 6), (9, 4), (13, 0), (15, 2), (11, 7)])
    c.fill(head, B('mustard'))
    c.fill(c.edge(head, 'rb'), D('mustard'))
    c.pxs([(11, 3), (12, 4), (10, 5), (13, 2)], B('yellow'))
    band = diag(c, 10.5, 12.5, 1.6)
    c.shade(band, 'red')
    c.outline()
    return c


def w_chain():
    c = new()
    grip = diag(c, 0.5, 4.5, 1.5)
    c.shade(grip, 'charcoal')
    pts = [(5.5, 10.5), (8, 8), (10.5, 5.5), (13, 3)]
    for i, (x, y) in enumerate(pts):
        if i % 2 == 0:
            m = c.C(x, y, 2.2) & ~c.C(x, y, 0.9)
        else:
            m = c.C(x, y, 1.5)
        c.shade(m, 'steel')
    c.outline()
    return c


def w_belt():
    c = new()
    strap = diag(c, 0.5, 15.5, 1.2)
    c.shade(strap, 'brown')
    for s in (3, 5, 7):
        c.fill(diag(c, s, s + 0.5, 0.4) & strap, INK)
    frame = c.R(9, 2, 14, 7) & ~c.R(10, 3, 13, 6)
    c.shade(frame, 'gold')
    c.fill(c.L(10, 5, 12, 3), B('steel'))
    c.outline()
    return c


def w_newspaper():
    c = new()
    m = diag(c, 1.5, 18.5, 2.1)
    c.shade(m, 'paper')
    for s, o in [(4, 0.8), (6, -0.6), (13, 0.8), (15, -0.6), (5, 0.0)]:
        c.fill(diag(c, s, s + 1.4, 0.4, off=o) & m, B('gray'))
    c.fill(diag(c, 9.5, 11, 2.5) & m, B('red'))
    c.fill(diag(c, 0, 2.6, 2.5) & m, D('paper'))
    c.outline()
    return c


def w_spatula():
    c = new()
    handle = diag(c, 0.5, 9, 1.2)
    c.shade(handle, 'black')
    neck = diag(c, 9, 11.5, 0.5)
    c.fill(neck, B('steel'))
    blade = c.P([(9, 4), (12, 1), (15, 4), (12, 7)])
    blade = c.P([(8, 5), (11, 1), (14, 1), (14, 4), (10, 8)])
    c.shade(blade, 'steel')
    c.fill(c.L(11, 4, 13, 2), B('iron'))
    c.outline()
    return c


def w_bottle():
    c = new()
    body = diag(c, 1.5, 11.5, 2.6)
    body = c.dilate(c.erode(body, 1), 1) & body
    neck = diag(c, 11, 17.5, 1.1)
    m = body | neck
    c.shade(m, 'bottle')
    c.fill(diag(c, 4, 8.5, 2.7) & body, B('cream'))
    c.fill(diag(c, 5.5, 7, 0.6) & body, B('red'))
    c.fill(diag(c, 16.5, 18.5, 1.3), B('gold'))
    c.outline()
    return c


def w_brick():
    c = new()
    front = c.R(1, 7, 11, 13)
    top = c.P([(1, 7), (4, 4), (14, 4), (11, 7)])
    side = c.P([(11, 7), (14, 4), (14, 10), (11, 13)])
    c.fill(front, B('brick'))
    c.fill(top, H('brick'))
    c.fill(side, D('brick'))
    c.pxs([(3, 9), (7, 11), (9, 8), (5, 12)], D('brick'))
    c.pxs([(7, 5), (10, 6)], B('brick'))
    c.outline()
    return c


def w_fish():
    c = new()
    body = c.E(4, 4, 14, 11)
    tail = c.P([(1, 3), (5, 7), (5, 8), (1, 12), (2, 8), (2, 7)])
    fin = c.P([(7, 4), (9, 2), (11, 2), (11, 4)])
    c.shade(fin, 'fish', light=False)
    c.shade(tail, 'fish')
    c.ball(body, 'fish', spec=False)
    c.fill(c.R(6, 5, 12, 5) & body, H('fish'))
    c.fill(c.R(6, 10, 12, 10) & body, D('fish'))
    c.px(11, 6, INK)
    c.fill(c.R(9, 6, 9, 8), D('fish'))
    c.px(14, 8, D('fish'))
    c.outline()
    return c


def w_tire():
    c = new()
    outer = c.C(8, 8, 6.8)
    c.fill(outer, B('black'))
    c.fill(outer & ~c.C(8, 8, 5.8), D('black'))
    for i in range(10):
        a = i * math.pi / 5
        c.px(int(8 + 6.2 * math.cos(a)), int(8 + 6.2 * math.sin(a)), B('charcoal'))
    c.fill(c.ring(8, 8, 5.8, 4.6) & (c.xx + c.yy < 13), H('black'))
    hub = c.C(8, 8, 3.4)
    c.ball(hub, 'steel')
    c.fill(c.C(8, 8, 1.2), D('steel'))
    c.outline()
    return c


def w_crate():
    c = new()
    box = c.R(1, 2, 14, 14)
    c.shade(box, 'wood')
    c.fill(c.R(3, 4, 12, 12), B('wood'))
    for y in (6, 9):
        c.fill(c.R(3, y, 12, y), D('wood'))
    brace = c.L(3, 12, 12, 4) | c.L(3, 11, 11, 4)
    c.fill(brace, H('wood'))
    c.fill(c.edge(c.R(1, 2, 14, 14), 'all') | c.edge(c.R(3, 4, 12, 12), 'all'), D('wood'))
    c.fill(c.R(1, 2, 14, 3) | c.R(1, 2, 2, 14), H('wood'))
    c.fill(c.R(1, 13, 14, 14) | c.R(13, 2, 14, 14), D('wood'))
    for (x, y) in [(2, 3), (13, 3), (2, 13), (13, 13)]:
        c.px(x, y, B('steel'))
    c.outline()
    return c


def w_trash_can():
    c = new()
    body = c.P([(3, 5), (12, 5), (11, 14), (4, 14)])
    c.fill(body, B('steel'))
    for x in (5, 8, 10):
        c.fill(body & c.R(x, 0, x, 15), D('steel'))
    c.fill(body & c.R(4, 0, 4, 15), H('steel'))
    c.fill(body & c.R(0, 13, 15, 14), D('steel'))
    lid = c.E(2, 3, 13, 6)
    c.shade(lid, 'steel')
    c.fill(c.R(6, 1, 9, 2) & ~c.R(7, 2, 8, 2), B('iron'))
    c.outline()
    return c


def w_road_sign():
    c = new()
    post = c.R(7, 9, 8, 14)
    c.shade(post, 'steel')
    plate = c.R(1, 2, 14, 9)
    c.shade(plate, 'orange')
    c.fill(c.R(3, 5, 10, 6), INK)
    c.fill(c.R(9, 4, 10, 4) | c.R(9, 7, 10, 7), INK)
    c.fill(c.R(11, 5, 11, 6), INK)
    c.px(9, 3, INK)
    c.px(9, 8, INK)
    c.outline()
    return c


# ============================================================== UI / STATS
def stat_hp():
    c = new()
    m = heart_mask(c, 2, 3, 12)
    c.shade(m, 'danger')
    c.fill(c.R(7, 5, 8, 10) | c.R(5, 7, 10, 8), B('white'))
    c.pxs([(3, 4), (4, 4), (3, 5)], H('danger'))
    c.outline()
    return c


def stat_atk():
    c = new()
    wrist = c.R(4, 12, 11, 14)
    c.fill(wrist, B('white'))
    c.fill(c.R(4, 13, 11, 13), B('red'))
    back = c.rrect(3, 6, 12, 12, 1)
    c.shade(back, 'skin')
    for x0 in (3, 6, 9):
        f = c.rrect(x0, 3, x0 + 2, 7, 1)
        c.shade(f, 'skin')
    f = c.rrect(12, 4, 13, 7, 0)
    c.shade(f, 'skin')
    thumb = c.rrect(3, 8, 9, 10, 1)
    c.shade(thumb, 'skin')
    c.fill(c.R(3, 10, 9, 10) & thumb, D('skin'))
    for x in (5, 8, 11):
        c.fill(c.R(x, 4, x, 6), D('skin'))
    c.fill(c.R(4, 3, 4, 3) | c.R(7, 3, 7, 3) | c.R(10, 3, 10, 3), H('skin'))
    c.outline()
    return c


def stat_def():
    c = new()
    sh = c.bitmap([
        "############",
        "############",
        "############",
        "############",
        "############",
        "############",
        ".##########.",
        ".##########.",
        "..########..",
        "...######...",
        "....####....",
        ".....##.....",
    ], 2, 2)
    c.fill(sh, B('blue'))
    c.fill(c.edge(sh, 'rb'), D('blue'))
    c.fill(c.edge(sh, 'lt') & ~c.edge(sh, 'rb'), H('blue'))
    c.fill(c.R(7, 3, 8, 12) & sh & ~c.edge(sh, 'all'), B('steel'))
    c.fill(c.R(3, 6, 12, 7) & sh & ~c.edge(sh, 'all'), B('steel'))
    c.outline()
    return c


def stat_agi():
    c = new()
    bolt = c.bitmap([
        "......####",
        ".....####.",
        "....####..",
        "...####...",
        "..#######.",
        ".#######..",
        "....###...",
        "...###....",
        "..###.....",
        ".##.......",
        "##........",
    ], 3, 2)
    c.fill(bolt, B('yellow'))
    c.fill(c.edge(bolt, 'rb'), D('yellow'))
    c.fill(c.edge(bolt, 'lt') & ~c.edge(bolt, 'rb'), H('yellow'))
    c.outline()
    c.pxs([(1, 6), (0, 6), (1, 9), (2, 9)], B('cream'))
    return c


def stat_tec():
    c = new()
    for r, col in [(6.6, 'white'), (5.2, 'danger'), (3.8, 'white'), (2.4, 'danger')]:
        c.fill(c.C(7.5, 8.5, r), B(col))
    c.fill(c.ring(7.5, 8.5, 6.6, 5.6) & ((c.xx + c.yy) > 16), D('white'))
    c.fill(c.C(7.5, 8.5, 1.0), INK)
    c.outline()
    dart = c.L(8, 8, 13, 3)
    c.fill(dart, B('steel'))
    c.fill(c.R(12, 1, 14, 2) | c.R(13, 1, 14, 4), B('teal'))
    c.px(14, 1, H('teal'))
    return c


def cash():
    c = new()
    for i, (x, y) in enumerate([(3, 3), (2, 5)]):
        bill = c.R(x, y, x + 11, y + 6)
        c.shade(bill, 'green')
        c.fill(c.R(x + 1, y + 1, x + 10, y + 5) & ~c.R(x + 2, y + 2, x + 9, y + 4), D('green'))
        c.fill(c.C(x + 5.5 + 0.5, y + 3.5, 1.8), H('green'))
    c.fill(c.bitmap([".#.", "##.", ".#.", ".##", ".#."], 6, 6), D('green'))
    coin = c.C(11.5, 11.5, 3.0)
    c.ball(coin, 'gold')
    c.fill(c.R(11, 10, 11, 12), D('gold'))
    c.outline()
    return c


def xp():
    c = new()
    gem = c.P([(7.5, 1), (14, 7.5), (7.5, 14), (1, 7.5)])
    c.fill(gem, B('cyan'))
    c.fill(gem & ((c.xx + c.yy) > 16), D('cyan'))
    c.fill(gem & ((c.xx + c.yy) < 9), H('cyan'))
    c.text('XP', 4, 5, INK, micro=True)
    c.outline()
    return c


def level():
    c = new()
    badge = c.bitmap([
        "##############",
        "##############",
        "##############",
        "##############",
        "##############",
        "##############",
        "##############",
        "##############",
        ".############.",
        "..##########..",
        "...########...",
        "....######....",
        ".....####.....",
    ], 1, 1)
    c.fill(badge, B('mustard'))
    c.fill(c.edge(badge, 'rb'), D('mustard'))
    c.fill(c.edge(badge, 'lt') & ~c.edge(badge, 'rb'), H('mustard'))
    c.text('LV', 3, 2, D('mustard'))
    c.text('LV', 2, 1, INK)
    c.outline()
    return c


def _scroll(mark):
    def f():
        c = new()
        paper = c.R(3, 3, 12, 12)
        c.shade(paper, 'cream', light=False)
        top = c.rrect(2, 1, 13, 3, 1)
        bot = c.rrect(2, 12, 13, 14, 1)
        c.shade(top, 'tan')
        c.shade(bot, 'tan')
        mark(c)
        c.outline()
        return c
    return f


def _mark_new(c):
    m = c.R(7, 4, 8, 8) | c.R(7, 10, 8, 11)
    c.fill(m, B('danger'))
    c.fill(c.R(7, 4, 7, 8), H('danger'))


def _mark_active(c):
    m = c.bitmap(["#...", "##..", "###.", "####", "###.", "##..", "#..."], 6, 4)
    c.fill(m, B('blue'))
    c.fill(c.R(4, 7, 5, 7), B('blue'))


def _mark_done(c):
    m = c.bitmap([".......##", "......##.", "#....##..", "##..##...", ".####....", "..##....."], 3, 5)
    c.fill(m, B('green'))


def lock():
    c = new()
    shackle = c.E(4, 1, 11, 10) & ~c.E(6, 3, 9, 10) & (c.yy <= 7)
    c.shade(shackle, 'steel')
    body = c.rrect(2, 7, 13, 14, 1)
    c.shade(body, 'gold')
    c.fill(c.R(7, 9, 8, 10) | c.R(7, 11, 8, 12) & c.R(7, 11, 8, 12), INK)
    c.fill(c.R(6, 9, 9, 10), INK)
    c.fill(c.R(7, 11, 8, 12), INK)
    c.fill(c.R(2, 7, 13, 7) & body, H('gold'))
    c.outline()
    return c


def bus():
    c = new()
    body = c.rrect(1, 3, 14, 12, 2)
    c.shade(body, 'mustard')
    c.fill(c.R(1, 9, 14, 9) & body, B('orange'))
    for x0 in (2, 5, 8):
        c.fill(c.R(x0, 5, x0 + 1, 7), B('glass'))
        c.px(x0, 5, H('glass'))
    c.fill(c.R(11, 5, 13, 10), B('glass'))
    c.fill(c.R(11, 8, 13, 10), D('glass'))
    c.fill(c.R(12, 5, 12, 10), D('mustard'))
    c.px(14, 10, B('white'))
    c.px(1, 10, B('red'))
    for x in (4, 10):
        w = c.C(x + 0.5, 12.5, 2.0)
        c.fill(w, B('black'))
        c.px(x, 12, B('steel'))
    c.outline()
    return c


def save():
    c = new()
    disk = c.R(2, 2, 13, 13) & ~c.P([(12, 2), (13, 2), (13, 3)])
    c.shade(disk, 'blue')
    sh = c.R(5, 2, 10, 6)
    c.shade(sh, 'steel')
    c.fill(c.R(8, 3, 9, 5), D('steel'))
    lab = c.R(4, 8, 11, 13)
    c.fill(lab, B('white'))
    for y in (9, 11):
        c.fill(c.R(5, y, 10, y), B('gray'))
    c.outline()
    return c


def map_pin():
    c = new()
    sh = c.E(4, 13, 11, 15)
    c.fill(sh, (26, 18, 32, 110))
    pin = c.C(7.5, 6, 5.0) | c.P([(3, 8), (12, 8), (7.5, 14)])
    c.shade(pin, 'danger')
    c.fill(c.C(7.5, 6, 2.0), B('white'))
    c.pxs([(4, 4), (5, 3)], H('danger'))
    c.outline(where=~sh)
    return c


def star_mask(c, cx, cy, ro, ri, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return c.P(pts)


def star():
    c = new()
    m = star_mask(c, 7.5, 8.2, 7.2, 3.0)
    c.fill(m, B('yellow'))
    c.fill(m & ((c.xx - 7.5) * 0.6 + (c.yy - 8) > 2.5), D('yellow'))
    c.fill(m & ((c.xx - 7.5) * 0.6 + (c.yy - 8) < -2.2), H('yellow'))
    c.outline()
    return c


def heart():
    c = new()
    m = heart_mask(c, 2, 3, 12)
    c.shade(m, 'danger')
    c.pxs([(3, 4), (4, 4), (3, 5), (4, 5)], H('danger'))
    c.outline()
    return c


def journal():
    c = new()
    c.fill(c.R(4, 2, 13, 14), B('cream'))
    c.fill(c.R(4, 14, 13, 14), D('cream'))
    for y in range(3, 14, 2):
        c.px(13, y, D('cream'))
    cover = c.R(2, 1, 12, 13)
    c.shade(cover, 'brown')
    c.fill(c.R(2, 1, 3, 13), D('brown'))
    c.fill(c.R(10, 6, 13, 8), B('tan'))
    c.fill(c.R(13, 6, 13, 8), D('tan'))
    c.fill(c.R(5, 3, 9, 4), B('cream'))
    c.outline()
    c.fill(c.R(7, 14, 7, 15), B('red'))
    c.px(8, 15, B('red'))
    return c


def settings():
    c = new()
    teeth = c.empty()
    for i in range(8):
        a = i * math.pi / 4
        teeth |= c.C(7.5 + 5.3 * math.cos(a), 7.5 + 5.3 * math.sin(a), 1.6)
    m = (c.C(7.5, 7.5, 5.0) | teeth) & ~c.C(7.5, 7.5, 1.9)
    c.shade(m, 'gray')
    c.fill(c.ring(7.5, 7.5, 2.9, 1.9), D('gray'))
    c.outline()
    return c


def check():
    c = new()
    m = c.bitmap([
        "..........###",
        ".........###.",
        "........###..",
        "###....###...",
        ".###..###....",
        "..######.....",
        "...####......",
        "....##.......",
    ], 1, 3)
    c.fill(m, B('neon'))
    c.fill(c.edge(m, 'b'), D('neon'))
    c.outline()
    return c


def cross():
    c = new()
    m = c.L(3, 3, 12, 12, 3) | c.L(12, 3, 3, 12, 3)
    m &= c.R(2, 2, 13, 13)
    c.fill(m, B('danger'))
    c.fill(c.edge(m, 'b'), D('danger'))
    c.outline()
    return c


ARROW = [
    ".....##.....",
    "....####....",
    "...######...",
    "..########..",
    ".##########.",
    "############",
    "....####....",
    "....####....",
    "....####....",
    "....####....",
]


def arrow(direction):
    def f():
        c = new()
        m = c.bitmap(ARROW, 2, 3)
        c.fill(m, B('cream'))
        c.fill(c.edge(m, 'b') | (m & (c.xx >= 8) & (c.yy >= 9)), D('cream'))
        c.outline()
        k = {'up': 0, 'left': 1, 'down': 2, 'right': 3}[direction]
        c.a = np.rot90(c.a, k).copy()
        return c
    return f


def food():
    c = new()
    fork = c.R(3, 1, 3, 5) | c.R(5, 1, 5, 5) | c.R(7, 1, 7, 5) | c.R(3, 5, 7, 7) | c.R(4, 7, 6, 14)
    c.shade(fork, 'steel')
    knife = c.rrect(10, 1, 12, 8, 1) & ~c.R(10, 1, 10, 2) | c.R(10, 8, 12, 14)
    c.shade(knife, 'steel')
    c.fill(c.R(10, 9, 12, 14), B('wood'))
    c.fill(c.R(12, 9, 12, 14), D('wood'))
    c.outline()
    return c


def skill():
    c = new()
    m = star_mask(c, 7.5, 7.5, 7.4, 3.6, n=8, rot=-math.pi / 2 + 0.2)
    c.fill(m, B('orange'))
    inner = star_mask(c, 7.5, 7.5, 4.8, 2.4, n=8, rot=-math.pi / 2 + 0.2)
    c.fill(inner, B('yellow'))
    c.fill(c.C(7.5, 7.5, 1.6), H('yellow'))
    c.outline()
    return c


def gear():
    return _jacket(B('mustard'), D('mustard'), B('red'))


def key_item():
    c = new()
    bow = c.C(4.5, 9.5, 3.4) & ~c.C(4.5, 9.5, 1.3)
    shaft = c.R(7, 9, 14, 10)
    teeth = c.R(11, 11, 11, 12) | c.R(13, 11, 14, 12)
    m = bow | shaft | teeth
    c.shade(m, 'gold')
    c.outline()
    sp = B('white')
    c.pxs([(11, 1), (11, 2), (11, 4), (11, 5), (9, 3), (10, 3), (12, 3), (13, 3)], H('yellow'))
    c.px(11, 3, sp)
    return c


# ============================================================== REGISTRY
GROUPS = [
    ('food', ['coffee', 'pancakes', 'meatloaf', 'cherry_pie', 'club_sandwich', 'milkshake',
              'pork_bun', 'ramen', 'dumplings', 'green_tea', 'spicy_udon', 'bean_chili',
              'grilled_cheese', 'iron_stew', 'hard_eggs', 'hot_dog', 'nachos', 'soda', 'popcorn',
              'fish_taco', 'thermos_soup', 'jerky', 'clam_chowder', 'empanada']),
    ('medicine', ['bandage', 'tonic', 'vitamin_pack', 'energy_drink', 'smelling_salts']),
    ('key', ['postcard', 'satchel', 'manifest', 'toolbox', 'parcel', 'count_book', 'payroll_pages',
             'cassette', 'gate_key', 'photo', 'ledger', 'eviction_notice', 'leash', 'arcade_log']),
    ('gear', ['courier_sneakers', 'champion_wraps', 'token_jacket', 'lucky_bandana']),
    ('manuals', ['manual_' + k for k in ['shoulder', 'rising', 'heel', 'rapid', 'sweep', 'counter',
                                         'giant', 'retrieve', 'slam', 'oath']]),
    ('weapons', ['w_' + k for k in ['wrench', 'baton', 'bat', 'pipe', 'broom', 'chain', 'belt',
                                    'newspaper', 'spatula', 'bottle', 'brick', 'fish', 'tire',
                                    'crate', 'trash_can', 'road_sign']]),
    ('ui', ['stat_hp', 'stat_atk', 'stat_def', 'stat_agi', 'stat_tec', 'cash', 'xp', 'level',
            'quest_new', 'quest_active', 'quest_done', 'lock', 'bus', 'save', 'map_pin', 'star',
            'heart', 'journal', 'settings', 'check', 'cross', 'arrow_up', 'arrow_down', 'arrow_left',
            'arrow_right', 'food', 'skill', 'gear', 'key_item']),
]

ICONS = {}
_g = globals()
for _grp, _ids in GROUPS:
    for _id in _ids:
        if _id.startswith('manual_'):
            ICONS[_id] = manual(_id[7:])
        elif _id.startswith('arrow_'):
            ICONS[_id] = arrow(_id[6:])
        elif _id == 'quest_new':
            ICONS[_id] = _scroll(_mark_new)
        elif _id == 'quest_active':
            ICONS[_id] = _scroll(_mark_active)
        elif _id == 'quest_done':
            ICONS[_id] = _scroll(_mark_done)
        else:
            ICONS[_id] = _g[_id]
