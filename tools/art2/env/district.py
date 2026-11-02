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
    # sun / moon
    if P.get('sun'):
        sx, sy, sr, sc = P['sun']
        for dx in (-TILE_U, 0, TILE_U):
            cv.radial(sx + dx, sy, sr * 6, sr * 4, C(sc), a=0.35, mode='addfree', falloff=1.6)
            cv.ellipse(sx + dx, sy, sr, sr, mix(C(sc), C('#ffffff'), 0.5))
            for k in range(3):
                cv.rect(sx + dx - sr, sy + sr * (0.15 + k * 0.28), sr * 2, 0.9 + k * 0.5, C('#f49a62'), mode='atop')
    # cloud streaks: cel-shaded, lit from below
    for i in range(14):
        cy = rs.uniform(10, 110)
        cx = rs.uniform(0, TILE_U)
        cw = rs.uniform(60, 190)
        ch = rs.uniform(3, 8)
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
    for _ in range(8):
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
