"""Effect frame strips and world pickups."""
import math
import numpy as np

from pixlib import Canvas, MAT, INK, CLEAR, hexc, mix, with_alpha

WHITE = hexc('#ffffff')
PALE = hexc('#fff6c0')
YEL = hexc('#fff06a')
GOLD = hexc('#f0c040')
ORA = hexc('#e07a30')
RED = hexc('#e04a4a')
CYAN = hexc('#4af0f0')
CYAN_D = hexc('#2aa0b0')
ICE = hexc('#c8ffff')
CREAM = hexc('#e8d8b0')
DUST = (hexc('#e8dcc8'), hexc('#c8b8a0'), hexc('#8a7a6a'))
SMOKE = (hexc('#b0b0ba'), hexc('#8a8a96'), hexc('#5a5a66'))
WATER = (hexc('#c8f0f8'), hexc('#6ab0c8'), hexc('#3a7a9a'), hexc('#2a5a7a'))


def A(c, a):
    return with_alpha(c, a)


def ray(c, cx, cy, ang, r0, r1, w0, w1):
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx
    pts = [(cx + dx * r0 + px * w0, cy + dy * r0 + py * w0),
           (cx + dx * r1 + px * w1, cy + dy * r1 + py * w1),
           (cx + dx * r1 - px * w1, cy + dy * r1 - py * w1),
           (cx + dx * r0 - px * w0, cy + dy * r0 - py * w0)]
    return c.P(pts)


def star_mask(c, cx, cy, ro, ri, n=5, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = rot + i * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return c.P(pts)


def fade(c, alpha):
    """Scale the alpha of every pixel (0..1)."""
    a = c.a[..., 3].astype(float) * alpha
    c.a[..., 3] = np.clip(a.round(), 0, 255).astype(np.uint8)


def puff(c, cx, cy, r, cols, alpha=255):
    lt, base, dk = cols
    m = c.C(cx, cy, r)
    c.fill(m, A(base, alpha))
    sh = m & ~c.C(cx - r * 0.25, cy - r * 0.3, r * 0.92)
    c.fill(sh, A(dk, alpha))
    hl = c.C(cx - r * 0.35, cy - r * 0.35, r * 0.45) & m
    c.fill(hl, A(lt, alpha))


# ================================================================ FX
def hit_spark():
    frames = []
    cx = cy = 12
    # f0: flash core
    c = Canvas(24, 24)
    c.fill(c.C(cx, cy, 5.0), YEL)
    for k in range(4):
        c.fill(ray(c, cx, cy, k * math.pi / 2 + math.pi / 4, 3, 8, 1.6, 0.4), YEL)
    c.fill(c.C(cx, cy, 3.4), WHITE)
    frames.append(c)
    # f1: big star burst
    c = Canvas(24, 24)
    for k in range(8):
        long = k % 2 == 0
        a = k * math.pi / 4 + 0.15
        c.fill(ray(c, cx, cy, a, 0, 11.5 if long else 8, 2.6 if long else 1.8, 0.3), ORA)
        c.fill(ray(c, cx, cy, a, 0, 9.5 if long else 6.5, 1.8 if long else 1.2, 0.3), YEL)
    c.fill(c.C(cx, cy, 4.0), PALE)
    c.fill(c.C(cx, cy, 2.6), WHITE)
    frames.append(c)
    # f2: broken rays
    c = Canvas(24, 24)
    for k in range(8):
        long = k % 2 == 0
        a = k * math.pi / 4 + 0.15
        c.fill(ray(c, cx, cy, a, 6, 11.5 if long else 9, 1.4, 0.3), ORA)
        c.fill(ray(c, cx, cy, a, 6, 9.0 if long else 7.5, 1.0, 0.3), YEL)
    c.fill(c.ring(cx, cy, 4.2, 2.8), A(WHITE, 200))
    frames.append(c)
    # f3: embers
    c = Canvas(24, 24)
    for k in range(8):
        a = k * math.pi / 4 + 0.15 + (0.2 if k % 2 else 0)
        r = 10.5 if k % 2 == 0 else 8.5
        x, y = int(cx + r * math.cos(a)), int(cy + r * math.sin(a))
        c.px(x, y, A(ORA, 200))
        if k % 2 == 0:
            c.px(int(cx + (r - 1.5) * math.cos(a)), int(cy + (r - 1.5) * math.sin(a)), A(YEL, 160))
    frames.append(c)
    return frames


def hit_heavy():
    frames = []
    cx = cy = 16
    c = Canvas(32, 32)
    c.fill(c.C(cx, cy, 7.5), ORA)
    c.fill(c.C(cx, cy, 6.0), YEL)
    c.fill(c.C(cx, cy, 4.2), WHITE)
    frames.append(c)
    c = Canvas(32, 32)
    for k in range(10):
        a = k * math.pi / 5 + 0.3
        r = 15.5 if k % 2 == 0 else 11
        c.fill(ray(c, cx, cy, a, 0, r, 3.2, 0.4), RED)
        c.fill(ray(c, cx, cy, a, 0, r - 2.5, 2.4, 0.4), ORA)
        c.fill(ray(c, cx, cy, a, 0, r - 5.5, 1.6, 0.4), YEL)
    c.fill(c.C(cx, cy, 5.0), PALE)
    c.fill(c.C(cx, cy, 3.5), WHITE)
    frames.append(c)
    c = Canvas(32, 32)
    c.fill(c.ring(cx, cy, 12.5, 10.8), A(WHITE, 230))
    for k in range(10):
        a = k * math.pi / 5 + 0.3
        r = 15.5 if k % 2 == 0 else 12.5
        c.fill(ray(c, cx, cy, a, 8, r, 1.8, 0.3), ORA)
        c.fill(ray(c, cx, cy, a, 8, r - 2.5, 1.2, 0.3), YEL)
    c.fill(c.C(cx, cy, 3.0), A(PALE, 200))
    frames.append(c)
    c = Canvas(32, 32)
    ringm = c.ring(cx, cy, 15.0, 13.8)
    for k in range(16):
        if k % 3 == 1:
            continue
        a0 = k * math.pi / 8
        seg = ringm & ray(c, cx, cy, a0 + 0.2, 10, 17, 3.5, 3.5)
        c.fill(seg, A(CREAM, 150))
    for k in range(6):
        a = k * math.pi / 3 + 0.6
        c.px(int(cx + 12 * math.cos(a)), int(cy + 12 * math.sin(a)), A(ORA, 210))
    frames.append(c)
    return frames


def block_spark():
    frames = []
    cx = cy = 10
    c = Canvas(20, 20)
    c.fill(c.C(cx, cy, 6.0), A(CYAN, 220))
    c.fill(c.C(cx, cy, 4.6), ICE)
    c.fill(c.C(cx, cy, 3.0), WHITE)
    frames.append(c)
    c = Canvas(20, 20)
    hexm = c.P([(cx + 8 * math.cos(k * math.pi / 3 + math.pi / 6), cy + 8 * math.sin(k * math.pi / 3 + math.pi / 6)) for k in range(6)])
    hexi = c.P([(cx + 6 * math.cos(k * math.pi / 3 + math.pi / 6), cy + 6 * math.sin(k * math.pi / 3 + math.pi / 6)) for k in range(6)])
    c.fill(hexm & ~hexi, A(CYAN, 230))
    c.fill(hexi & ~c.C(cx, cy, 4.5), A(ICE, 120))
    for k in range(6):
        a = k * math.pi / 3
        c.fill(ray(c, cx, cy, a, 7.5, 9.8, 0.9, 0.3), WHITE)
    c.fill(c.C(cx, cy, 2.2), WHITE)
    frames.append(c)
    c = Canvas(20, 20)
    for k in range(6):
        a = k * math.pi / 3 + 0.25
        x, y = cx + 8.6 * math.cos(a), cy + 8.6 * math.sin(a)
        c.px(int(x), int(y), A(ICE, 220))
        c.px(int(cx + 7 * math.cos(a)), int(cy + 7 * math.sin(a)), A(CYAN, 170))
    c.fill(c.ring(cx, cy, 5.0, 4.0), A(CYAN, 110))
    frames.append(c)
    return frames


def perfect_flash():
    frames = []
    cx = cy = 16
    c = Canvas(32, 32)
    c.fill(c.P([(cx, cy - 6), (cx + 6, cy), (cx, cy + 6), (cx - 6, cy)]), ICE)
    c.fill(c.C(cx, cy, 3.0), WHITE)
    frames.append(c)
    c = Canvas(32, 32)
    c.fill(c.ring(cx, cy, 7.5, 6.3), CYAN)
    for k in range(4):
        a = k * math.pi / 2
        c.fill(ray(c, cx, cy, a, 0, 15.5, 2.2, 0.2), ICE)
        c.fill(ray(c, cx, cy, a, 0, 12.5, 1.1, 0.2), WHITE)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        c.fill(ray(c, cx, cy, a, 0, 7.0, 1.2, 0.2), WHITE)
    c.fill(c.C(cx, cy, 3.2), WHITE)
    frames.append(c)
    c = Canvas(32, 32)
    c.fill(c.ring(cx, cy, 11.5, 10.4), A(CYAN, 220))
    for k in range(4):
        a = k * math.pi / 2
        c.fill(ray(c, cx, cy, a, 3, 14.5, 1.2, 0.2), A(ICE, 230))
    c.fill(c.C(cx, cy, 1.8), WHITE)
    frames.append(c)
    c = Canvas(32, 32)
    c.fill(c.ring(cx, cy, 14.5, 13.6), A(CYAN, 120))
    for (x, y) in [(6, 8), (25, 7), (24, 25), (7, 24)]:
        c.fill(c.R(x - 1, y, x + 1, y) | c.R(x, y - 1, x, y + 1), A(WHITE, 200))
    frames.append(c)
    return frames


def dust():
    frames = []
    specs = [
        [(12, 8.5, 2.6)],
        [(10, 8, 3.4), (14.5, 8.5, 2.8)],
        [(8, 7.5, 3.8), (13.5, 7, 3.6), (17.5, 8.5, 2.5)],
        [(6.5, 6.5, 3.2), (12.5, 5.5, 3.0), (17.5, 7.5, 2.0)],
    ]
    alphas = [255, 240, 200, 120]
    for i, sp in enumerate(specs):
        c = Canvas(24, 12)
        for (x, y, r) in sp:
            puff(c, x, y, r, DUST, alphas[i])
        if i == 3:
            for (x, y) in [(4, 4), (9, 3), (15, 3), (20, 5)]:
                c.px(x, y, A(DUST[1], 90))
        frames.append(c)
    return frames


def land_dust():
    frames = []
    specs = [(11, 21, 2.2, 255), (7, 25, 3.2, 230), (3.5, 28.5, 3.0, 130)]
    for i, (xl, xr, r, a) in enumerate(specs):
        c = Canvas(32, 10)
        y = 9 - r
        for x, s in [(xl, -1), (xr, 1)]:
            puff(c, x, y + 0.5, r, DUST, a)
            puff(c, x - s * r * 0.9, y + 1.2, r * 0.7, DUST, a)
        if i == 0:
            c.fill(c.R(12, 8, 19, 9), A(DUST[1], 200))
        frames.append(c)
    return frames


def stars():
    frames = []
    cx, cy, rx, ry = 12, 6, 8.0, 1.8
    for f in range(4):
        c = Canvas(24, 12)
        items = []
        for k in range(3):
            a = f * (2 * math.pi / 12) + k * 2 * math.pi / 3
            x = cx + rx * math.cos(a)
            y = cy + ry * math.sin(a)
            items.append((math.sin(a), x, y))
        items.sort()
        for depth, x, y in items:
            front = depth > -0.2
            if front:
                rows = ["..#..", ".###.", "#####", ".###.", ".#.#."]
            else:
                rows = [".#.", "###", ".#."]
            n = len(rows)
            m = c.bitmap(rows, int(round(x - n / 2.0)), int(round(y - n / 2.0)))
            c.fill(c.dilate(m, 1) & ~m, INK)
            c.fill(m, YEL if front else GOLD)
            if front:
                ys, xs = np.nonzero(m)
                c.px(int(xs.min()) + 1, int(ys.min()) + 2, WHITE)
        frames.append(c)
    return frames


def shockwave():
    frames = []
    W, H = 72, 20
    cx, cy = 36, 13
    specs = [(9, 230), (19, 210), (28, 160), (34, 90)]
    for i, (rx, a) in enumerate(specs):
        c = Canvas(W, H)
        ry = max(2.5, rx * 0.22)
        outer = c.E(cx - rx, cy - ry, cx + rx - 1, cy + ry - 1)
        inner = c.E(cx - rx + 3, cy - ry + 1.5, cx + rx - 4, cy + ry - 2.5)
        band = outer & ~inner
        c.fill(band, A(DUST[1], a))
        top = band & (c.yy < cy)
        c.fill(top, A(WHITE if i < 2 else CREAM, a))
        c.fill(band & (c.yy >= cy + ry - 2), A(DUST[2], a))
        if i < 3:
            for k in range(6):
                t = (k + 0.5) / 6 * 2 * math.pi
                x = cx + (rx + 1) * math.cos(t)
                y = cy + (ry + 0.5) * math.sin(t) - 2
                c.px(int(x), int(y), A(DUST[0], a))
        frames.append(c)
    return frames


def splash():
    frames = []
    lt, base, mid, dk = WATER
    c = Canvas(24, 16)
    c.fill(c.E(7, 11, 16, 15), base)
    c.fill(c.E(9, 9, 14, 13), lt)
    c.pxs([(6, 10), (17, 10), (11, 7), (12, 7)], lt)
    frames.append(c)
    c = Canvas(24, 16)
    c.fill(c.E(5, 12, 18, 15), mid)
    crown = c.P([(6, 13), (7, 6), (9, 10), (11, 3), (13, 10), (15, 5), (17, 13)])
    c.fill(crown, base)
    c.fill(crown & (c.yy < 9), lt)
    c.pxs([(4, 5), (19, 4), (11, 1), (12, 0), (8, 2), (16, 2)], lt)
    frames.append(c)
    c = Canvas(24, 16)
    c.fill(c.E(4, 12, 19, 15), mid)
    c.fill(c.E(7, 12, 16, 14), base)
    for (x, y) in [(3, 7), (20, 6), (6, 4), (17, 3), (11, 2), (13, 5), (2, 10), (21, 9)]:
        c.fill(c.R(x, y, x, y + 1), lt)
    frames.append(c)
    c = Canvas(24, 16)
    ring = c.E(2, 11, 21, 15) & ~c.E(5, 12, 18, 14)
    c.fill(ring, A(base, 200))
    c.fill(ring & (c.yy <= 12), A(lt, 200))
    c.pxs([(1, 10), (22, 10), (4, 9)], A(lt, 180))
    frames.append(c)
    return frames


def debris_wood():
    frames = []
    shapes = [
        lambda c: c.P([(1, 3), (3, 1), (4, 2), (2, 4)]),
        lambda c: c.R(1, 2, 4, 3),
        lambda c: c.R(1, 1, 2, 4) | c.R(1, 3, 4, 4),
        lambda c: c.P([(1, 4), (4, 1), (4, 2), (2, 4)]),
    ]
    for f in shapes:
        c = Canvas(6, 6)
        m = f(c)
        c.fill(m, MAT['wood'][0])
        c.fill(c.edge(m, 'rb'), MAT['wood'][1])
        c.fill(c.edge(m, 'lt') & ~c.edge(m, 'rb'), MAT['wood'][2])
        c.outline()
        frames.append(c)
    return frames


def debris_glass():
    frames = []
    pats = [["##..", "###.", ".#..", "...."], [".#..", "###.", "..#.", "...."],
            ["#...", "##..", "###.", "...."], ["..#.", ".##.", "##..", "#..."]]
    for p in pats:
        c = Canvas(4, 4)
        m = c.bitmap(p, 0, 0)
        c.fill(m, A(hexc('#a8e0f0'), 230))
        c.fill(c.edge(m, 'rb'), A(hexc('#4a8aa8'), 255))
        ys, xs = np.nonzero(m)
        c.px(xs[0], ys[0], WHITE)
        frames.append(c)
    return frames


def debris_metal():
    frames = []
    c = Canvas(6, 6)  # bolt
    m = c.R(2, 1, 3, 4) | c.R(1, 1, 4, 1)
    c.shade(m, 'steel')
    c.outline()
    frames.append(c)
    c = Canvas(6, 6)  # nut
    m = c.C(3, 3, 1.9) & ~c.R(2, 2, 2, 2)
    c.shade(m, 'steel')
    c.px(2, 2, INK)
    c.outline()
    frames.append(c)
    c = Canvas(6, 6)  # bent strip
    m = c.R(1, 3, 3, 4) | c.R(3, 1, 4, 3)
    c.shade(m, 'iron')
    c.outline()
    frames.append(c)
    c = Canvas(6, 6)  # rusty scrap
    m = c.P([(1, 2), (4, 1), (4, 4), (2, 4)])
    c.shade(m, 'rust')
    c.px(3, 2, MAT['steel'][0])
    c.outline()
    frames.append(c)
    return frames


def coin_sparkle():
    frames = []
    cx = cy = 6
    for f, (r, diag) in enumerate([(2, 0), (5, 2), (4, 1), (1, 0)]):
        c = Canvas(12, 12)
        c.fill(c.R(cx - r, cy, cx + r - 1, cy) | c.R(cx - 1, cy, cx, cy) |
               c.R(cx, cy - r, cx, cy + r - 1), YEL)
        c.fill(c.R(cx - r, cy, cx - r, cy) | c.R(cx + r - 1, cy, cx + r - 1, cy) |
               c.R(cx, cy - r, cx, cy - r) | c.R(cx, cy + r - 1, cx, cy + r - 1), GOLD)
        for k in range(1, diag + 1):
            for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                c.px(cx + sx * k - (1 if sx > 0 else 0) + (1 if sx > 0 else 0), cy + sy * k, A(PALE, 200))
        c.px(cx, cy, WHITE)
        if r >= 4:
            c.fill(c.R(cx - 1, cy - 1, cx + 1, cy + 1) & (c.C(cx + 0.5, cy + 0.5, 1.6)), WHITE)
        frames.append(c)
    return frames


def levelup_burst():
    frames = []
    cx = cy = 24
    ring_r = [5, 11, 16, 20, 22.5, 23.5]
    ring_a = [255, 255, 230, 180, 120, 60]
    for f in range(6):
        c = Canvas(48, 48)
        r = ring_r[f]
        c.fill(c.ring(cx, cy, r, r - (2.2 if f < 3 else 1.2)), A(CYAN, ring_a[f]))
        if f == 0:
            c.fill(c.C(cx, cy, 4.0), WHITE)
        if 1 <= f <= 3:
            for k in range(8):
                a = k * math.pi / 4 + math.pi / 8
                r0 = 3 + f * 3
                c.fill(ray(c, cx, cy, a, r0, r0 + 9 - f, 1.4, 0.3), A(YEL, 255 - f * 40))
            c.fill(c.C(cx, cy, 4.5 - f), A(WHITE, 255 - f * 50))
        if f >= 1:
            # light pillars rising
            for k, x in enumerate([cx - 9, cx, cx + 9]):
                top = cy - 6 - f * 5 - (4 if k == 1 else 0)
                bot = top + 10
                c.fill(c.R(x, max(0, top), x, min(47, bot)), A(PALE, max(40, 220 - f * 35)))
        if f >= 2:
            for k, (x0, y0) in enumerate([(12, 18), (34, 14), (20, 9), (30, 26), (16, 30)]):
                y = y0 - (f - 2) * 4
                if y < 1:
                    continue
                s = star_mask(c, x0, y, 2.6 if k % 2 == 0 else 2.0, 1.0, n=4, rot=0)
                c.fill(s, A(YEL if k % 2 else WHITE, max(60, 255 - (f - 2) * 50)))
        frames.append(c)
    return frames


def smoke():
    frames = []
    specs = [
        [(8, 10, 3.0)],
        [(6.5, 9.5, 3.4), (10, 8.5, 3.6)],
        [(5.5, 8, 3.6), (10, 6.5, 4.2), (9, 10.5, 3.0)],
        [(5, 6, 3.4), (10.5, 4.5, 3.8)],
    ]
    alphas = [255, 240, 200, 110]
    for i, sp in enumerate(specs):
        c = Canvas(16, 16)
        for (x, y, r) in sp:
            puff(c, x, y, r, SMOKE, alphas[i])
        frames.append(c)
    return frames


def rain_splash():
    lt, base = WATER[0], WATER[1]
    frames = []
    c = Canvas(8, 4)
    c.pxs([(3, 2), (4, 2), (2, 1), (5, 1)], A(lt, 230))
    c.fill(c.R(2, 3, 5, 3), A(base, 200))
    frames.append(c)
    c = Canvas(8, 4)
    c.pxs([(1, 0), (6, 0), (2, 1), (5, 1)], A(lt, 210))
    c.fill(c.R(1, 3, 6, 3), A(base, 180))
    frames.append(c)
    c = Canvas(8, 4)
    c.fill(c.R(0, 3, 1, 3) | c.R(6, 3, 7, 3), A(base, 140))
    c.pxs([(0, 1), (7, 1)], A(lt, 120))
    frames.append(c)
    return frames


def _bubble(mark_rows, col):
    c = Canvas(12, 16)
    body = c.rrect(1, 1, 10, 11, 2)
    tail = c.P([(3, 11), (6, 11), (3, 14)])
    c.fill(body | tail, WHITE)
    c.fill(c.edge(body | tail, 'rb'), hexc('#c8c0d0'))
    m = c.bitmap(mark_rows, 4, 2)
    c.fill(m, col)
    c.outline()
    return c


def exclaim():
    return [_bubble(["..##..", "..##..", "..##..", "..##..", "..##..", "......", "..##..", "..##.."][0:8],
                    RED)]


def question():
    return [_bubble([".###..", "##.##.", "...##.", "..##..", "..##..", "......", "..##..", "..##.."],
                    MAT['blue'][1])]


def sweat():
    c = Canvas(8, 8)
    m = c.C(3.5, 4.8, 2.4) | c.P([(3, 0), (5.2, 4), (1.8, 4)])
    m = c.bitmap(["..#..", ".###.", ".###.", "#####", "#####", ".###."], 1, 1)
    c.fill(m, MAT['glass'][0])
    c.fill(c.edge(m, 'rb'), MAT['glass'][1])
    c.px(2, 4, WHITE)
    c.px(2, 5, MAT['glass'][2])
    c.outline()
    return [c]


def charge_glow():
    frames = []
    cx = cy = 12
    for f in range(4):
        c = Canvas(24, 24)
        glow_r = [5.5, 7, 8.5, 9.5][f]
        ga = [110, 140, 170, 120][f]
        c.fill(c.C(cx, cy, glow_r), A(YEL, ga))
        c.fill(c.ring(cx, cy, glow_r, glow_r - 1.2), A(YEL, min(255, ga + 70)))
        c.fill(c.C(cx, cy, glow_r * 0.6), A(PALE, min(255, ga + 60)))
        pr = [10.5, 8.0, 5.5, 11][f]
        for k in range(8):
            a = k * math.pi / 4 + f * 0.3
            x, y = cx + pr * math.cos(a), cy + pr * math.sin(a)
            col = ORA if k % 2 else YEL
            c.fill(c.C(x, y, 1.0 if f < 3 else 0.8), col)
            if f < 3:
                tx, ty = cx + (pr + 2) * math.cos(a), cy + (pr + 2) * math.sin(a)
                c.px(int(tx), int(ty), A(col, 120))
        if f == 2:
            c.fill(c.C(cx, cy, 2.0), WHITE)
        frames.append(c)
    return frames


def shadow():
    c = Canvas(24, 8)
    cx, cy, rx, ry = 12, 4, 12, 4
    d = ((c.xx + 0.5 - cx) / rx) ** 2 + ((c.yy + 0.5 - cy) / ry) ** 2
    a = np.where(d < 1, 0.40 * np.clip(1 - d, 0, 1) ** 0.55, 0)
    q = np.round(a * 255 / 13) * 13
    c.a[..., 0:3] = (10, 6, 14)
    c.a[..., 3] = np.clip(q, 0, 255).astype(np.uint8)
    return [c]


def target_shadow():
    c = Canvas(32, 10)
    cx, cy, rx, ry = 16, 5, 16, 5
    d = ((c.xx + 0.5 - cx) / rx) ** 2 + ((c.yy + 0.5 - cy) / ry) ** 2
    inside = d < 1
    c.a[inside] = (120, 20, 30, 90)
    ring = inside & (d > 0.62)
    c.a[ring] = (224, 74, 74, 190)
    inner = (d < 0.18)
    c.a[inner] = (90, 10, 20, 130)
    # tick marks
    for x in (2, 3, 28, 29):
        c.px(x, 5, (255, 140, 120, 230))
    for y in (1, 8):
        c.px(16, y, (255, 140, 120, 230))
        c.px(15, y, (255, 140, 120, 230))
    return [c]


FX = {
    'hit_spark': hit_spark, 'hit_heavy': hit_heavy, 'block_spark': block_spark,
    'perfect_flash': perfect_flash, 'dust': dust, 'land_dust': land_dust, 'stars': stars,
    'shockwave': shockwave, 'splash': splash, 'debris_wood': debris_wood,
    'debris_glass': debris_glass, 'debris_metal': debris_metal, 'coin_sparkle': coin_sparkle,
    'levelup_burst': levelup_burst, 'smoke': smoke, 'rain_splash': rain_splash,
    'exclaim': exclaim, 'question': question, 'sweat': sweat, 'charge_glow': charge_glow,
    'shadow': shadow, 'target_shadow': target_shadow,
}
FX_IDS = list(FX.keys())

FX_SPEC = {
    'hit_spark': (4, 24, 24), 'hit_heavy': (4, 32, 32), 'block_spark': (3, 20, 20),
    'perfect_flash': (4, 32, 32), 'dust': (4, 24, 12), 'land_dust': (3, 32, 10),
    'stars': (4, 24, 12), 'shockwave': (4, 72, 20), 'splash': (4, 24, 16),
    'debris_wood': (4, 6, 6), 'debris_glass': (4, 4, 4), 'debris_metal': (4, 6, 6),
    'coin_sparkle': (4, 12, 12), 'levelup_burst': (6, 48, 48), 'smoke': (4, 16, 16),
    'rain_splash': (3, 8, 4), 'exclaim': (1, 12, 16), 'question': (1, 12, 16), 'sweat': (1, 8, 8),
    'charge_glow': (4, 24, 24), 'shadow': (1, 24, 8), 'target_shadow': (1, 32, 10),
}


# ================================================================ PICKUPS
def coin():
    frames = []
    g, gd, gl = MAT['gold']
    for w in (6, 4, 2, 4):
        c = Canvas(8, 8)
        x0 = 1 + (6 - w) // 2
        m = c.E(x0, 1, x0 + w - 1, 6)
        if w == 2:
            m = c.R(3, 1, 4, 6)
            c.fill(m, gd)
            c.fill(c.R(3, 1, 3, 6), g)
        else:
            c.fill(m, g)
            c.fill(c.edge(m, 'rb'), gd)
            c.fill(c.edge(m, 'lt') & ~c.edge(m, 'rb'), gl)
            if w == 6:
                c.fill(c.R(3, 3, 4, 4), gd)
                c.px(3, 3, gl)
            else:
                c.fill(c.R(3, 3, 4, 4) & m & ~c.edge(m, 'all'), gd)
        c.outline()
        frames.append(c)
    return frames


def bill():
    c = Canvas(12, 8)
    m = c.R(1, 1, 10, 6)
    c.shade(m, 'green')
    c.fill(c.R(2, 2, 9, 5) & ~c.R(3, 3, 8, 4), MAT['green'][1])
    c.fill(c.C(6, 4, 1.6), MAT['green'][2])
    c.px(5, 3, MAT['green'][1])
    c.px(6, 4, MAT['green'][1])
    c.outline()
    return [c]


def cash_stack():
    c = Canvas(14, 10)
    for y in (6, 4, 2):
        m = c.R(1, y, 12, y + 2)
        c.fill(m, MAT['green'][0])
        c.fill(c.R(1, y + 2, 12, y + 2), MAT['green'][1])
        c.fill(c.R(1, y, 12, y), MAT['green'][2])
    c.fill(c.R(1, 1, 12, 2), MAT['green'][0])
    c.fill(c.R(1, 1, 12, 1), MAT['green'][2])
    c.fill(c.R(3, 1, 10, 2) & ~c.R(4, 1, 9, 1), MAT['green'][1])
    band = c.R(5, 1, 7, 8)
    c.fill(band, MAT['mustard'][0])
    c.fill(c.R(7, 1, 7, 8), MAT['mustard'][1])
    c.fill(c.R(5, 1, 7, 1), MAT['mustard'][2])
    c.outline()
    return [c]


def heal_bun():
    c = Canvas(12, 10)
    paper = c.R(1, 7, 10, 8)
    c.shade(paper, 'cream')
    bun = c.E(2, 3, 9, 12) & (c.yy <= 7)
    c.shade(bun, 'egg')
    c.fill(c.E(3, 3, 6, 5), MAT['egg'][2])
    c.pxs([(5, 3), (6, 3), (4, 4), (7, 4)], MAT['egg'][1])
    c.fill(c.R(5, 4, 6, 4), MAT['cherry'][0])
    c.outline()
    c.pxs([(4, 0), (5, 1), (7, 0), (8, 1)], (236, 232, 240, 170))
    return [c]


def parcel():
    c = Canvas(12, 12)
    front = c.R(1, 4, 8, 10)
    top = c.P([(1, 4), (3, 2), (10, 2), (8, 4)])
    side = c.P([(8, 4), (10, 2), (10, 8), (8, 10)])
    c.fill(front, MAT['cardboard'][0])
    c.fill(top, MAT['cardboard'][2])
    c.fill(side, MAT['cardboard'][1])
    tape = hexc('#e8d8a0')
    c.fill(c.R(4, 4, 5, 10), tape)
    c.fill(c.P([(4, 4), (6, 2), (7, 2), (5, 4)]), tape)
    c.outline()
    return [c]


def toolbox():
    c = Canvas(16, 10)
    handle = c.R(5, 1, 10, 3) & ~c.R(6, 2, 9, 3)
    c.shade(handle, 'charcoal')
    body = c.R(1, 3, 14, 8)
    c.shade(body, 'red')
    c.fill(c.R(1, 4, 14, 4), MAT['red'][1])
    c.fill(c.R(7, 5, 8, 6), MAT['steel'][0])
    c.outline()
    return [c]


def satchel():
    c = Canvas(14, 12)
    strap = c.E(2, 1, 11, 9) & ~c.E(4, 3, 9, 7) & (c.yy <= 5)
    c.shade(strap, 'brown')
    body = c.rrect(1, 5, 12, 10, 1)
    c.shade(body, 'brown')
    flap = c.rrect(1, 5, 12, 8, 1)
    c.shade(flap, 'wood')
    c.fill(c.R(6, 7, 7, 8), MAT['gold'][0])
    c.outline()
    return [c]


def ledger():
    c = Canvas(12, 10)
    c.fill(c.R(3, 2, 10, 8), MAT['cream'][0])
    c.fill(c.R(3, 8, 10, 8), MAT['cream'][1])
    cover = c.R(1, 1, 9, 7)
    c.shade(cover, 'red')
    c.fill(c.R(1, 1, 2, 7), MAT['red'][1])
    c.fill(c.R(4, 3, 7, 4), MAT['gold'][0])
    c.outline()
    return [c]


def key():
    c = Canvas(10, 6)
    bow = c.C(2.5, 2.5, 1.9) & ~c.R(2, 2, 2, 2)
    shaft = c.R(4, 2, 8, 2)
    teeth = c.R(6, 3, 6, 4) | c.R(8, 3, 8, 3)
    c.shade(bow | shaft | teeth, 'gold')
    c.px(2, 2, INK)
    c.outline()
    return [c]


PICKUPS = {
    'coin': coin, 'bill': bill, 'cash_stack': cash_stack, 'heal_bun': heal_bun, 'parcel': parcel,
    'toolbox': toolbox, 'satchel': satchel, 'ledger': ledger, 'key': key,
}
PICKUP_IDS = list(PICKUPS.keys())
PICKUP_SPEC = {
    'coin': (4, 8, 8), 'bill': (1, 12, 8), 'cash_stack': (1, 14, 10), 'heal_bun': (1, 12, 10),
    'parcel': (1, 12, 12), 'toolbox': (1, 16, 10), 'satchel': (1, 14, 12), 'ledger': (1, 12, 10),
    'key': (1, 10, 6),
}
