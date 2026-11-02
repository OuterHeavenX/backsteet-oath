"""Backstreet Oath env v2 -- shared district parallax layers (seamless, repeat-x tiles of 1024 u)."""
import math

import numpy as np

from raster import Canvas, C, mix, shade, light, value_noise, rng_of, blur

TILE_U = 1024


def _wrap_draw(fn, x, *a, **k):
    """Draw an element at x and at x +/- TILE_U so the tile wraps seamlessly."""
    for dx in (-TILE_U, 0, TILE_U):
        fn(x + dx, *a, **k)


def sky(dist, seed=1):
    P = DIST[dist]
    cv = Canvas(TILE_U, 360)
    cv.vgrad(0, 0, TILE_U, 360, P['sky'])
    rs = rng_of('sky', dist, seed)
    # faint stars near the top
    for _ in range(8):
        x, y = rs.uniform(0, TILE_U), rs.uniform(2, 16)
        cv.ellipse(x, y, 0.3, 0.3, C('#fff4e0'), a=rs.uniform(0.15, 0.35))
    if P.get('stars'):
        for _ in range(P['stars']):
            x, y = rs.uniform(0, TILE_U), rs.uniform(2, 110)
            cv.ellipse(x, y, 0.35, 0.35, C('#f4f0ff'), a=rs.uniform(0.3, 0.9))
    # sun / moon
    if P.get('sun'):
        sx, sy, sr, sc = P['sun']
        for dx in (-TILE_U, 0, TILE_U):
            cv.radial(sx + dx, sy, sr * 6, sr * 4, C(sc), a=0.35, mode='addfree', falloff=1.6)
            cv.ellipse(sx + dx, sy, sr, sr, mix(C(sc), C('#ffffff'), 0.5))
            for k in range(3):
                cv.rect(sx + dx - sr, sy + sr * (0.15 + k * 0.28), sr * 2, 0.9 + k * 0.5, C('#f49a62'), mode='atop')
    # cloud streaks: cel-shaded, lit from below
    for i in range(P.get('clouds', 14)):
        cy = rs.uniform(10, 110)
        cx = rs.uniform(0, TILE_U)
        cw = rs.uniform(60, 190) * P.get('cloud_scale', 1.0)
        ch = rs.uniform(3, 8) * P.get('cloud_scale', 1.0)
        t = cy / 110
        top_c = mix(C(P['cloud_top']), C(P['cloud_low']), t * 0.6)
        under = C(P['cloud_lit'])
        def one(x, cy=cy, cw=cw, ch=ch, top_c=top_c, under=under, i=i):
            pts = []
            n = 14
            for k in range(n + 1):
                u = k / n
                bump = math.sin(u * math.pi) * ch * (0.8 + 0.4 * math.sin(u * 9 + i))
                pts.append((x + u * cw, cy - bump))
            for k in range(n, -1, -1):
                u = k / n
                pts.append((x + u * cw, cy + ch * 0.25 * math.sin(u * math.pi)))
            mk = cv.poly_mask(pts)
            cv.paint(mk, top_c, a=0.9)
            # lit underside band
            x0, y0, m = mk
            Y = (np.arange(m.shape[0], dtype=np.float32) + y0 + 0.5) / cv.D
            band = np.clip((Y - (cy - ch * 0.35)) / (ch * 0.5), 0, 1)[:, None]
            cv.paint((x0, y0, m * band), under, a=0.9)
            cv.paint((x0, y0, m * np.clip(band * 2 - 1.2, 0, 1)), mix(under, C('#ffffff'), 0.4), a=0.6)
        _wrap_draw(one, cx)
    # birds
    for _ in range(P.get('birds', 8)):
        bx, by = rs.uniform(0, TILE_U), rs.uniform(40, 140)
        cv.line([(bx - 2, by - 0.8), (bx, by), (bx + 2, by - 0.8)], 0.4, C(P['far'][0]), a=0.8)
    return cv


def _building_sil(cv, x, base_y, w, h, col, rs, lit_col, win_p=0.12, detail=True, ink=None, rim=None, deco=None):
    top = base_y - h
    pts = [(x, base_y), (x, top), (x + w, top), (x + w, base_y)]
    cv.fill_poly(pts, col, ink=ink, iw=0.5 if ink else 0)
    if rim:
        cv.rect(x, top, w, 0.8, rim, a=0.55)
        cv.rect(x, top, 0.8, h, rim, a=0.35)
    if detail:
        kind = deco or rs.choice(['flat', 'tank', 'chimney', 'stepped', 'antenna', 'flat', 'gable'])
        if kind == 'tank' and w > 18:
            tx = x + rs.uniform(3, w - 12)
            cv.rect(tx + 1, top - 5, 0.6, 5, col)
            cv.rect(tx + 7, top - 5, 0.6, 5, col)
            cv.rect(tx, top - 13, 9, 8, col, ink=ink, iw=0.5 if ink else 0)
            cv.fill_poly([(tx - 0.5, top - 13), (tx + 4.5, top - 17), (tx + 9.5, top - 13)], col)
        elif kind == 'chimney':
            cx = x + rs.uniform(2, max(3, w - 6))
            cv.rect(cx, top - rs.uniform(6, 14), 3.5, 14, col)
        elif kind == 'stepped' and w > 20:
            cv.rect(x + w * 0.2, top - 8, w * 0.6, 8, col)
            cv.rect(x + w * 0.38, top - 14, w * 0.24, 6, col)
        elif kind == 'antenna':
            ax = x + w * 0.6
            cv.line([(ax, top), (ax, top - 14)], 0.4, col)
        elif kind == 'gable':
            cv.fill_poly([(x, top), (x + w / 2, top - w * 0.35), (x + w, top)], col)
        elif kind == 'spire':
            cv.fill_poly([(x + w * 0.3, top), (x + w / 2, top - 46), (x + w * 0.7, top)], col)
    # windows
    if lit_col and win_p > 0:
        yy = top + 4
        while yy < base_y - 4:
            xx = x + 2.5
            while xx < x + w - 3:
                if rs.random() < win_p:
                    cv.rect(xx, yy, 1.4, 1.8, C(lit_col), a=rs.uniform(0.6, 1.0))
                xx += 4
            yy += 5


def far(dist, seed=2):
    P = DIST[dist]
    if P.get('far_style', 'skyline') != 'skyline':
        return FAR_STYLES[P['far_style']](dist, P, seed)
    cv = Canvas(TILE_U, 216)       # placed at y = 0 u
    rs = rng_of('far', dist, seed)
    base = 216
    c0, c1 = C(P['far'][0]), C(P['far'][1])
    # two depth rows: back row lighter (haze, downtown towers), front row slightly darker
    hz = C(P['haze'])
    for row, (col, hmin, hmax) in enumerate(((mix(c1, hz, 0.25), 110, 196), (mix(c0, c1, 0.3), 80, 150))):
        x = -40
        while x < TILE_U + 40:
            w = rs.uniform(16, 46)
            h = rs.uniform(hmin, hmax)
            deco = None
            if row == 0 and rs.random() < 0.05:
                deco = 'spire'
            def one(xx, w=w, h=h, col=col, deco=deco, s=rs.random()):
                r2 = rng_of('b', dist, xx // 1, s)
                _building_sil(cv, xx, base, w, h, col, r2, P['far_win'], win_p=0.07 if row else 0.03,
                              deco=deco, rim=C(P['rim']) if row else None)
            if 0 <= x < TILE_U:
                _wrap_draw(one, x)
            x += w + rs.uniform(-6, 2)
    # landmark: gasholder + smokestack once per tile
    def gas(x):
        cv.ellipse(x, base - 30, 26, 30, mix(c0, c1, 0.3))
        for k in range(4):
            cv.rect(x - 26, base - 50 + k * 12, 52, 0.6, shade(c0, 0.5), a=0.6)
        cv.rect(x + 40, base - 92, 6, 92, c0)
        cv.rect(x + 40, base - 92, 6, 2, shade(c0, 0.6))
    _wrap_draw(gas, rs.uniform(200, 800))
    # horizon haze at the bottom
    cv.vgrad(0, base - 50, TILE_U, 50, [C(P['haze'], 0), C(P['haze'], 160)], mode='atop')
    return cv


def mid(dist, seed=3):
    P = DIST[dist]
    if P.get('mid_style', 'rooftops') != 'rooftops':
        return MID_STYLES[P['mid_style']](dist, P, seed)
    cv = Canvas(TILE_U, 224)       # placed at y = 0 u
    rs = rng_of('mid', dist, seed)
    base = 224
    col = C(P['mid'])
    ink = shade(col, 1.5)
    x = -30
    while x < TILE_U + 30:
        w = rs.uniform(30, 80)
        h = rs.uniform(150, 196)
        def one(xx, w=w, h=h, s=rs.random()):
            r2 = rng_of('m', dist, int(xx), s)
            _building_sil(cv, xx, base, w, h, col, r2, P['mid_win'], win_p=0.16, ink=ink, rim=C(P['rim']),
                          deco=r2.choice(['tank', 'tank', 'chimney', 'antenna', 'flat', 'stepped']))
            # cornice line and a fire-escape hint
            cv.rect(xx, base - h + 3, w, 1.2, shade(col, 0.5), a=0.8)
            if r2.random() < 0.4 and w > 30:
                fx = xx + w * 0.3
                for k in range(int(h / 22)):
                    cv.rect(fx, base - h + 14 + k * 22, 12, 0.8, shade(col, 0.9))
        if 0 <= x < TILE_U:
            _wrap_draw(one, x)
        x += w + rs.uniform(0, 14)
    cv.vgrad(0, base - 40, TILE_U, 40, [C(P['haze'], 0), C(P['haze'], 90)], mode='atop')
    return cv


DIST = {
    'old_quarter': dict(
        sky=[(0.0, C('#3c4472')), (0.06, C('#6e5a80')), (0.12, C('#d0866a')), (0.20, C('#f4a460')),
             (0.32, C('#ffc87a')), (1.0, C('#ffdca0'))],
        sun=(300, 96, 15, '#ffe8b0'),
        cloud_top='#7a6478', cloud_low='#c47c6a', cloud_lit='#ffbc7a',
        far=('#8a5a6a', '#d89080'), far_win='#ffd890', haze='#f4a87a', rim='#ffb890',
        mid='#5a3a48', mid_win='#ffcf80',
    ),
}


# ----------------------------------------------------------------------------- district styles
def far_hills(dist, P, seed):
    """Canal: rolling hills, a low town across the water, a lighthouse. Base at y=132."""
    cv = Canvas(TILE_U, 136)
    rs = rng_of('hills', dist, seed)
    base = 132
    c0, c1 = C(P['far'][0]), C(P['far'][1])
    for row, (col, amp, off) in enumerate(((mix(c1, C(P['haze']), 0.3), 26, 52), (c0, 14, 30))):
        pts = [(0, base)]
        ph = rs.uniform(0, 6)
        for k in range(129):
            x = k * TILE_U / 128
            y = base - off - amp * (0.5 + 0.5 * math.sin(x / TILE_U * 2 * math.pi * 3 + ph)) \
                - amp * 0.3 * math.sin(x / TILE_U * 2 * math.pi * 7 + ph * 2)
            pts.append((x, y))
        pts.append((TILE_U, base))
        cv.fill_poly(pts, col)
    # low town strip
    x = 0
    while x < TILE_U:
        w = rs.uniform(6, 16)
        h = rs.uniform(6, 16)
        col = mix(C(rs.choice(P['house_cols'])), C(P['haze']), 0.55)
        cv.fill_poly([(x, base), (x, base - h), (x + w / 2, base - h - w * 0.4), (x + w, base - h), (x + w, base)], col)
        x += w + rs.uniform(0, 3)
    def lighthouse(xx):
        cv.fill_poly([(xx - 4, base - 10), (xx - 2.5, base - 44), (xx + 2.5, base - 44), (xx + 4, base - 10)], C('#f4f0e8'))
        cv.rect(xx - 3.5, base - 34, 7, 3, C('#c84a3a'))
        cv.rect(xx - 3.5, base - 24, 7, 3, C('#c84a3a'))
        cv.rect(xx - 3, base - 49, 6, 5, C('#fff4c0'))
        cv.fill_poly([(xx - 4, base - 49), (xx, base - 54), (xx + 4, base - 49)], C('#c84a3a'))
    _wrap_draw(lighthouse, 760)
    cv.vgrad(0, base - 30, TILE_U, 30, [C(P['haze'], 0), C(P['haze'], 150)], mode='atop')
    return cv


def mid_canal_houses(dist, P, seed):
    """Canal: colourful gabled canal houses on the far quay; quay edge at y=152 (canvas y=0)."""
    cv = Canvas(TILE_U, 156)
    rs = rng_of('canalh', dist, seed)
    base = 152
    x = -20
    while x < TILE_U + 20:
        w = rs.uniform(22, 38)
        h = rs.uniform(52, 92)
        col = C(rs.choice(P['house_cols']))
        kind = rs.choice(['step', 'bell', 'point', 'point', 'flat'])
        def one(xx, w=w, h=h, col=col, kind=kind, s=rs.random()):
            r2 = rng_of('ch', int(xx), s)
            m_ink = shade(col, 1.6)
            top = base - h
            if kind == 'point':
                pts = [(xx, base), (xx, top), (xx + w / 2, top - w * 0.45), (xx + w, top), (xx + w, base)]
            elif kind == 'step':
                st = w / 6
                pts = [(xx, base), (xx, top), (xx + st, top), (xx + st, top - 5), (xx + 2 * st, top - 5), (xx + 2 * st, top - 10),
                       (xx + 4 * st, top - 10), (xx + 4 * st, top - 5), (xx + 5 * st, top - 5), (xx + 5 * st, top), (xx + w, top), (xx + w, base)]
            elif kind == 'bell':
                pts = [(xx, base), (xx, top)] + [(xx + w / 2 + math.cos(a) * w * 0.35, top - 4 - math.sin(a) * 10)
                                                  for a in np.linspace(math.pi, 0, 10)] + [(xx + w, top), (xx + w, base)]
            else:
                pts = [(xx, base), (xx, top), (xx + w, top), (xx + w, base)]
            cv.fill_poly(pts, col, ink=m_ink, iw=0.5)
            cv.rect(xx, top, 1.0, h, C(P['rim']), a=0.5)
            # windows: 3-4 floors
            nf = int(h / 18)
            nc = 2 if w < 30 else 3
            for f in range(nf):
                for c in range(nc):
                    wx = xx + (w - nc * 4.5) / (nc + 1) * (c + 1) + 4.5 * c
                    wy = top + 6 + f * 18
                    lit = r2.random() < 0.2
                    cv.rect(wx, wy, 4.5, 8, C('#fff0c0') if lit else shade(col, 1.2), ink=m_ink, iw=0.3)
                    cv.rect(wx - 0.5, wy + 8, 5.5, 0.8, C('#f4f0e8'))
            if r2.random() < 0.5:
                cv.rect(xx + w / 2 - 3, base - 12, 6, 12, shade(col, 1.5), ink=m_ink, iw=0.3)
        if 0 <= x < TILE_U:
            _wrap_draw(one, x)
        x += w + rs.uniform(0, 2)
    # far quay edge + moored boats + bunting
    cv.rect(0, base - 1, TILE_U, 4, C('#a89a88'))
    cv.rect(0, base - 1, TILE_U, 0.8, C('#e8dcc8'))
    for k in range(6):
        def bt(xx, c=rs.choice(['#c83a3a', '#2e6a5a', '#f4f0e8', '#3a5a9a'])):
            cv.fill_poly([(xx, base + 3), (xx + 20, base + 3), (xx + 17, base + 6), (xx + 3, base + 6)], C(c))
        _wrap_draw(bt, rs.uniform(0, TILE_U))
    cv.vgrad(0, 40, TILE_U, 116, [C(P['haze'], 0), C(P['haze'], 70)], mode='atop')
    return cv


def far_industry(dist, P, seed):
    """Ironworks: factory halls, stacks with plumes, gantry cranes. Base at y=216."""
    cv = Canvas(TILE_U, 216)
    rs = rng_of('ind', dist, seed)
    base = 216
    c0, c1 = C(P['far'][0]), C(P['far'][1])
    col = mix(c1, C(P['haze']), 0.25)
    x = -30
    while x < TILE_U:
        w = rs.uniform(40, 120)
        h = rs.uniform(70, 140)
        def hall(xx, w=w, h=h):
            cv.fill_poly([(xx, base), (xx, base - h)] + [(xx + w * t, base - h - 8 * abs(math.sin(t * math.pi * 3)))
                                                         for t in np.linspace(0, 1, 7)] + [(xx + w, base - h), (xx + w, base)], col)
            for k in range(int(w / 9)):
                if rs.random() < 0.25:
                    cv.rect(xx + 3 + k * 9, base - h * 0.5, 4, 2.5, C(P['far_win']), a=0.8)
        _wrap_draw(hall, x)
        x += w + rs.uniform(10, 40)
    for k in range(6):
        sx = rs.uniform(0, TILE_U)
        sh = rs.uniform(150, 200)
        def stack(xx, sh=sh):
            cv.fill_poly([(xx - 5, base), (xx - 3.5, base - sh), (xx + 3.5, base - sh), (xx + 5, base)], mix(c0, col, 0.4))
            cv.rect(xx - 3.5, base - sh + 6, 7, 2, C('#c8b8a8'), a=0.6)
            for j in range(5):
                cv.ellipse(xx + j * 6 + 3, base - sh - 6 - j * 6, 5 + j * 2, 4 + j * 1.5, C(P['smoke']), a=0.5 - j * 0.08)
        _wrap_draw(stack, sx)
    def gantry(xx):
        cv.rect(xx, base - 160, 3, 160, c0)
        cv.rect(xx + 90, base - 160, 3, 160, c0)
        cv.rect(xx - 20, base - 166, 140, 7, c0)
        for j in range(12):
            cv.line([(xx - 20 + j * 12, base - 166), (xx - 14 + j * 12, base - 159)], 0.6, mix(c0, col, 0.5))
    _wrap_draw(gantry, rs.uniform(100, 800))
    cv.vgrad(0, base - 70, TILE_U, 70, [C(P['haze'], 0), C(P['haze'], 170)], mode='atop')
    return cv


def mid_sheds(dist, P, seed):
    """Ironworks mid: corrugated sheds, pipe racks, conveyors. Base at y=216."""
    cv = Canvas(TILE_U, 216)
    rs = rng_of('sheds', dist, seed)
    base = 216
    col = C(P['mid'])
    ink = shade(col, 1.5)
    x = -20
    while x < TILE_U:
        w = rs.uniform(60, 140)
        h = rs.uniform(110, 170)
        def shed(xx, w=w, h=h, s=rs.random()):
            r2 = rng_of('sh', int(xx), s)
            cv.fill_poly([(xx, base), (xx, base - h), (xx + w / 2, base - h - 16), (xx + w, base - h), (xx + w, base)], col,
                         ink=ink, iw=0.5)
            cv.line([(xx, base - h), (xx + w / 2, base - h - 16)], 0.8, C(P['rim']), a=0.6)
            for k in range(int(w / 6)):
                cv.rect(xx + k * 6, base - h, 0.5, h, shade(col, 0.4), a=0.6)
            for k in range(int(w / 20)):
                if r2.random() < 0.45:
                    cv.rect(xx + 6 + k * 20, base - h * 0.7, 10, 4, C(P['mid_win']), a=0.9)
        _wrap_draw(shed, x)
        x += w + rs.uniform(16, 60)
    # pipe rack across
    for k, y in enumerate((base - 70, base - 76)):
        cv.rect(0, y, TILE_U, 2.4, mix(col, C('#8a9aaa'), 0.3))
    for k in range(20):
        cv.rect(k * 52 + 10, base - 76, 2, 76, shade(col, 0.3))
    cv.vgrad(0, base - 50, TILE_U, 50, [C(P['haze'], 0), C(P['haze'], 90)], mode='atop')
    return cv


def far_towers_night(dist, P, seed):
    cv = Canvas(TILE_U, 216)
    rs = rng_of('ntw', dist, seed)
    base = 216
    c0, c1 = C(P['far'][0]), C(P['far'][1])
    for row, (col, hmin, hmax, wp) in enumerate(((c1, 120, 205, 0.18), (c0, 80, 160, 0.25))):
        x = -40
        while x < TILE_U + 40:
            w = rs.uniform(18, 50)
            h = rs.uniform(hmin, hmax)
            def one(xx, w=w, h=h, col=col, s=rs.random()):
                r2 = rng_of('nt', int(xx), s)
                cv.rect(xx, base - h, w, h, col)
                if r2.random() < 0.3:
                    cv.line([(xx + w / 2, base - h), (xx + w / 2, base - h - 16)], 0.5, col)
                    cv.ellipse(xx + w / 2, base - h - 16, 0.8, 0.8, C('#ff4a4a'))
                yy = base - h + 4
                while yy < base - 4:
                    xw = xx + 2.5
                    while xw < xx + w - 3:
                        if r2.random() < wp:
                            cv.rect(xw, yy, 1.6, 2, C(r2.choice(P['win_cols'])), a=0.9)
                        xw += 4
                    yy += 5
            if 0 <= x < TILE_U:
                _wrap_draw(one, x)
            x += w + rs.uniform(-4, 6)
    for k in range(4):
        bx = rs.uniform(0, TILE_U)
        c = rs.choice(P['neon'])
        def bill(xx, c=c):
            cv.rect(xx, 120, 40, 18, C('#1a1030'))
            cv.rect(xx + 2, 122, 36, 14, C(c), a=0.8)
        _wrap_draw(bill, bx)
    cv.vgrad(0, base - 90, TILE_U, 90, [C(P['haze'], 0), C(P['haze'], 150)], mode='atop')
    return cv


def mid_night_roofs(dist, P, seed):
    cv = Canvas(TILE_U, 224)
    rs = rng_of('nroof', dist, seed)
    base = 224
    col = C(P['mid'])
    ink = shade(col, 1.5)
    x = -30
    while x < TILE_U + 30:
        w = rs.uniform(30, 80)
        h = rs.uniform(150, 196)
        def one(xx, w=w, h=h, s=rs.random()):
            r2 = rng_of('nr', dist, int(xx), s)
            _building_sil(cv, xx, base, w, h, col, r2, None, win_p=0, ink=ink, rim=C(P['rim']),
                          deco=r2.choice(['tank', 'tank', 'antenna', 'flat', 'chimney']))
            for k in range(int(h / 9)):
                for j in range(int(w / 7)):
                    if r2.random() < 0.18:
                        cv.rect(xx + 3 + j * 7, base - h + 6 + k * 9, 2.5, 3.5, C(r2.choice(P['win_cols'])), a=0.95)
            if r2.random() < 0.35:
                c = r2.choice(P['neon'])
                sy = base - h + r2.uniform(10, 40)
                cv.rect(xx + 4, sy, w - 8, 8, C('#120a1a'))
                cv.rect(xx + 6, sy + 2, w - 12, 4, C(c))
        if 0 <= x < TILE_U:
            _wrap_draw(one, x)
        x += w + rs.uniform(0, 14)
    cv.vgrad(0, base - 40, TILE_U, 40, [C(P['haze'], 0), C(P['haze'], 90)], mode='atop')
    return cv


def far_port(dist, P, seed):
    cv = Canvas(TILE_U, 216)
    rs = rng_of('port', dist, seed)
    base = 216
    c0, c1 = C(P['far'][0]), C(P['far'][1])
    col = mix(c1, C(P['haze']), 0.2)
    x = -20
    while x < TILE_U:
        w = rs.uniform(60, 160)
        h = rs.uniform(30, 60)
        _wrap_draw(lambda xx, w=w, h=h: cv.rect(xx, base - h, w, h, col), x)
        x += w + rs.uniform(10, 50)
    for k in range(4):
        cx = rs.uniform(0, TILE_U)
        def crane(xx):
            cv.rect(xx, base - 150, 4, 150, c0)
            cv.rect(xx + 30, base - 150, 4, 150, c0)
            cv.rect(xx - 50, base - 156, 130, 6, c0)
            cv.fill_poly([(xx + 2, base - 156), (xx + 16, base - 180), (xx + 30, base - 156)], c0)
            for j in range(10):
                cv.line([(xx - 50 + j * 13, base - 156), (xx - 44 + j * 13, base - 150)], 0.6, col)
            cv.ellipse(xx + 16, base - 182, 1.2, 1.2, C('#ff4a3a'))
        _wrap_draw(crane, cx)
    def ship(xx):
        cv.fill_poly([(xx, base - 40), (xx + 220, base - 40), (xx + 200, base - 22), (xx + 10, base - 22)], c0)
        for j in range(8):
            cv.rect(xx + 30 + j * 20, base - 56, 18, 16, mix(C(rs.choice(P['container_cols'])), col, 0.5))
        cv.rect(xx + 190, base - 76, 18, 36, c0)
    _wrap_draw(ship, rs.uniform(200, 700))
    cv.vgrad(0, base - 90, TILE_U, 90, [C(P['haze'], 0), C(P['haze'], 170)], mode='atop')
    return cv


def mid_containers(dist, P, seed):
    cv = Canvas(TILE_U, 216)
    rs = rng_of('cont', dist, seed)
    base = 216
    x = -10
    while x < TILE_U:
        stacks = rs.randint(2, 5)
        w = 60
        def stack(xx, n=stacks, s=rs.random()):
            r2 = rng_of('cs', int(xx), s)
            for j in range(n):
                c = mix(C(r2.choice(P['container_cols'])), C(P['mid']), 0.55)
                y = base - (j + 1) * 22
                cv.rect(xx, y, w, 22, c, ink=shade(c, 1.4), iw=0.5)
                for k in range(1, 12):
                    cv.rect(xx + k * 5, y + 1, 0.5, 20, shade(c, 0.5))
                cv.rect(xx, y, w, 0.8, C(P['rim']), a=0.5)
        _wrap_draw(stack, x)
        x += w + rs.uniform(4, 40)
    for k in range(5):
        lx = rs.uniform(0, TILE_U)
        def lamp(xx):
            cv.rect(xx, base - 150, 2, 150, C(P['mid']))
            cv.rect(xx - 6, base - 152, 14, 4, C(P['mid']))
            cv.rect(xx - 5, base - 148, 12, 2, C(P['mid_win']))
        _wrap_draw(lamp, lx)
    cv.vgrad(0, base - 60, TILE_U, 60, [C(P['haze'], 0), C(P['haze'], 110)], mode='atop')
    return cv


FAR_STYLES = {'hills': far_hills, 'industry': far_industry, 'towers_night': far_towers_night, 'port': far_port}
MID_STYLES = {'canal_houses': mid_canal_houses, 'sheds': mid_sheds, 'night_roofs': mid_night_roofs,
              'containers': mid_containers}

DIST.update({
    'canal_market': dict(
        sky=[(0.0, C('#4a82ae')), (0.14, C('#78a8c4')), (0.28, C('#b8d0c4')), (0.38, C('#f0daa0')),
             (1.0, C('#f8e4b0'))],
        sun=(700, 50, 12, '#fff4d0'), clouds=16,
        cloud_top='#e8eef0', cloud_low='#f4e8d0', cloud_lit='#fff4d8',
        far=('#7a9aa0', '#a8c0b8'), far_win='#fff0c0', haze='#f0e0b0', rim='#fff0c0', far_style='hills',
        mid='#8a9a98', mid_win='#fff0c0', mid_style='canal_houses',
        house_cols=['#e8a060', '#c86a5a', '#e8d8b8', '#7aa8b0', '#b07a9a', '#d8b860', '#a8c890', '#e88a8a'],
    ),
    'ironworks': dict(
        sky=[(0.0, C('#3a4660')), (0.16, C('#56667e')), (0.32, C('#8494a6')), (0.44, C('#c2a68c')),
             (0.52, C('#e49a66')), (1.0, C('#f0a870'))],
        sun=None, clouds=18, cloud_scale=1.4,
        cloud_top='#5a6478', cloud_low='#8a8a98', cloud_lit='#e8a070',
        far=('#3e4658', '#6a7486'), far_win='#ffb060', haze='#b8987e', rim='#ffb070', far_style='industry',
        smoke='#8a8e9a', mid='#38404e', mid_win='#ffa850', mid_style='sheds',
    ),
    'neon_mile': dict(
        sky=[(0.0, C('#0c0c22')), (0.2, C('#181634')), (0.36, C('#2c1c48')), (0.5, C('#562868')),
             (0.6, C('#84387a')), (1.0, C('#a04a80'))],
        sun=(820, 34, 7, '#f0f0ff'), stars=60, clouds=6, birds=0,
        cloud_top='#2a2040', cloud_low='#4a2a5a', cloud_lit='#9a4a8a',
        far=('#1e1a3a', '#3a2a5a'), far_win='#ffd88a', haze='#6a2a6a', rim='#ff6ab0', far_style='towers_night',
        win_cols=['#ffd88a', '#ffd88a', '#6ae0ff', '#ff8ad0'], neon=['#ff4ab0', '#4ae0ff', '#f8e040', '#8aff8a'],
        mid='#140e22', mid_win='#ffd88a', mid_style='night_roofs',
    ),
    'floodgate': dict(
        sky=[(0.0, C('#24323c')), (0.25, C('#384c56')), (0.45, C('#56707a')), (1.0, C('#768e92'))],
        sun=None, clouds=26, cloud_scale=1.8, birds=2,
        cloud_top='#2e3c46', cloud_low='#46585e', cloud_lit='#6a8086',
        far=('#34464e', '#55686e'), far_win='#e8d890', haze='#7a9494', rim='#a8d8e0', far_style='port',
        container_cols=['#a84a3a', '#3a6a8a', '#c89a3a', '#4a7a5a', '#8a8a8a'],
        mid='#2a3a40', mid_win='#f0e0a0', mid_style='containers',
    ),
    'warehouse': dict(
        sky=[(0.0, C('#10181c')), (0.3, C('#1e2a30')), (0.5, C('#2e4044')), (1.0, C('#445854'))],
        sun=(180, 40, 8, '#e8f0e0'), stars=20, clouds=8, birds=0,
        cloud_top='#1e2a2e', cloud_low='#2e3e40', cloud_lit='#5a7a70',
        far=('#1c282e', '#34444a'), far_win='#c8ffe0', haze='#3e5450', rim='#a8f0c8', far_style='port',
        container_cols=['#7a3a2a', '#2a4a6a', '#8a7a3a', '#3a5a4a', '#5a5a5a'],
        mid='#1a2428', mid_win='#c8ffe0', mid_style='containers',
    ),
})
