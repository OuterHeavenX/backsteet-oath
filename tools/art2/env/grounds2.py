"""Backstreet Oath env v2 -- ground styles for every district (world units). Calm, low-contrast playable bands."""
import math

import numpy as np

from raster import C, mix, shade, light, value_noise, rng_of
import kit
from kit import M, DETAIL
import room as rm
from room import FACADE_BOTTOM as FB, CURB_Y, H, INT_WALL_BOTTOM as WB, near_curb, weeds, puddle


def depth_rows(y0, y1, h0, h1):
    rows = [y0]
    y = y0
    while y < y1 - 0.5:
        t = (y - y0) / max(1, (y1 - y0))
        y += h0 + (h1 - h0) * t
        rows.append(min(y, y1))
    return rows


def _noise_tone(R, mk, cell, seed, amt_l=0.08, amt_d=0.08, m=None):
    cv = R.cv
    x0, y0, mm = mk
    n = value_noise(mm.shape[1], mm.shape[0], cell * cv.D, seed, 2)
    cv.paint((x0, y0, (n - 0.5).clip(0, 1) * amt_l * 2 * mm), m.l, mode='atop')
    cv.paint((x0, y0, (0.5 - n).clip(0, 1) * amt_d * 2 * mm), m.d, mode='atop')


def wall_contact(R, x, w, y0, a=150):
    R.cv.vgrad(x, y0, w, 7, [C('#140c1c', a), C('#140c1c', 0)], mode='atop')


def stones(R, x, w, y0, y1, base, seed, h0=4.0, h1=8.0, aspect=1.6, var=0.07, joint=None):
    """Perspective cobblestones: rows grow toward the viewer, rounded stones with a lit top edge."""
    cv = R.cv
    m = M(C(base))
    mk = cv.rect(x, y0, w, y1 - y0, m.b)
    jc = np.array((joint or shade(m.b, 0.85))[:3], np.float32) / 255
    bs = np.array(m.b[:3], np.float32) / 255
    lt = np.array(m.l[:3], np.float32) / 255
    sh = np.array(m.s[:3], np.float32) / 255
    rs = np.random.default_rng(seed)
    lut = rs.random((512, 512)).astype(np.float32)
    k = (h1 - h0) / max(1e-6, (y1 - y0))

    def fn(X, Y):
        hy = h0 + k * (Y - y0)
        d = np.log(hy / h0) / k if k > 1e-6 else (Y - y0) / h0
        row = np.floor(d).astype(np.int64)
        fy = d - row
        sw = hy * aspect
        off = (row % 2) * 0.5 + (lut[row % 512, 7] * 0.3)
        u = (X - x) / sw + off
        col = np.floor(u).astype(np.int64)
        fx = u - col
        v = (lut[row % 512, col % 512] - 0.5) * 2 * var
        c = bs[None, None, :] * (1 + v[..., None])
        # rounded stone: distance to the stone centre in normalised space
        dx = (fx - 0.5) * 2
        dy = (fy - 0.5) * 2
        r = np.sqrt(dx * dx * 0.8 + dy * dy)
        c = np.where((dy < -0.35)[..., None], c * 0.75 + lt * 0.25, c)
        c = np.where((dy > 0.45)[..., None], c * 0.75 + sh * 0.25, c)
        c = np.where((r > 0.92)[..., None], jc, c)
        return np.clip(c, 0, 1)
    cv.texture(mk, fn)
    _noise_tone(R, mk, 26, seed + 1, 0.05, 0.10, m)
    return mk


def planks(R, x, w, y0, y1, base, seed, h0=5.0, h1=10.0, joint_every=(40, 90), gap=None, nails=True, across=False):
    """Boards running along x (or across, for bridge decks), rows grow toward the viewer."""
    cv = R.cv
    m = M(C(base))
    mk = cv.rect(x, y0, w, y1 - y0, m.b)
    rs = rng_of('pl', seed)
    gapc = gap or shade(m.b, 1.6)
    if not across:
        rows = depth_rows(y0, y1, h0, h1)
        for i in range(len(rows) - 1):
            ya, yb = rows[i], rows[i + 1]
            t = rs.uniform(-0.06, 0.06)
            cv.rect(x, ya, w, yb - ya, m.l if t > 0 else m.s, a=abs(t) * 3, mode='atop')
            cv.rect(x, yb - 0.6, w, 0.6, gapc, a=0.85, mode='atop')
            cv.rect(x, ya, w, 0.5, m.l, a=0.4, mode='atop')
            xx = x + rs.uniform(0, joint_every[1])
            while xx < x + w:
                cv.rect(xx, ya, 0.6, yb - ya, gapc, a=0.7, mode='atop')
                if nails:
                    for nx in (xx - 1.6, xx + 1.6):
                        cv.ellipse(nx, (ya + yb) / 2, 0.35, 0.3, shade(m.b, 1.2), a=0.7, mode='atop')
                xx += rs.uniform(*joint_every)
    else:
        bw = 6.0
        xx = x
        while xx < x + w:
            t = rs.uniform(-0.07, 0.07)
            cv.rect(xx, y0, bw, y1 - y0, m.l if t > 0 else m.s, a=abs(t) * 3, mode='atop')
            cv.rect(xx + bw - 0.6, y0, 0.6, y1 - y0, gapc, a=0.85, mode='atop')
            if nails:
                for ny in (y0 + 3, y1 - 3):
                    cv.ellipse(xx + bw / 2, ny, 0.35, 0.3, shade(m.b, 1.2), a=0.7, mode='atop')
            xx += bw
    kit.wood_grain(cv, x, y0, w, y1 - y0, m.b, seed, a=0.07, along='y' if across else 'x')
    _noise_tone(R, mk, 22, seed + 3, 0.05, 0.10, m)
    return mk


def tiles(R, x, w, y0, y1, c1, c2, seed, tile=16.0, h0=6.0, h1=16.0, checker=False, grout=None, sc0=0.82,
          gloss=0.0):
    """Perspective floor tiles (optionally checker), converging slightly toward the back."""
    cv = R.cv
    A = np.array(C(c1)[:3], np.float32) / 255
    B = np.array(C(c2)[:3], np.float32) / 255
    G = np.array((grout or shade(C(c1), 0.8))[:3], np.float32) / 255
    cx = x + w / 2
    mk = cv.rect(x, y0, w, y1 - y0, C(c1))
    rs = np.random.default_rng(seed)
    lut = rs.random((256, 256)).astype(np.float32)
    k = (h1 - h0) / max(1e-6, (y1 - y0))

    def fn(X, Y):
        s = np.clip((Y - y0) / (y1 - y0), 0, 1)
        hy = h0 + k * (Y - y0)
        d = np.log(hy / h0) / k
        sc = sc0 + (1 - sc0) * s
        u = (X - cx) / sc / tile
        iu = np.floor(u).astype(np.int64)
        idd = np.floor(d).astype(np.int64)
        if checker:
            par = (iu + idd) % 2
            col = np.where(par[..., None] > 0, B, A)
        else:
            v = (lut[idd % 256, iu % 256] - 0.5) * 0.08
            col = A[None, None, :] * (1 + v[..., None])
            col = np.where((lut[(idd * 7) % 256, (iu * 3) % 256] < 0.08)[..., None], B, col)
        fu = u - iu
        fd = d - idd
        edge = ((fu < 0.04) | (fd < 0.07))[..., None]
        col = np.where(edge, G, col)
        col = col * (0.86 + 0.14 * s[..., None])
        return np.clip(col, 0, 1)
    cv.texture(mk, fn)
    m = M(C(c1))
    _noise_tone(R, mk, 20, seed + 5, 0.03, 0.10, m)
    return mk


def concrete_floor(R, x, w, y0, y1, base, seed, joints=64.0, stains=True):
    cv = R.cv
    m = M(C(base))
    mk = cv.vgrad(x, y0, w, y1 - y0, [shade(m.b, 0.3), m.b, light(m.b, 0.2)])
    _noise_tone(R, mk, 1.4, seed, 0.05, 0.05, m)
    _noise_tone(R, mk, 30, seed + 1, 0.06, 0.14, m)
    xx = (int(x / joints) + 1) * joints
    while xx < x + w:
        cv.line([(xx, y0), (xx + (xx - (x + w / 2)) * 0.12, y1)], 0.5, m.d, a=0.45, mode='atop')
        xx += joints
    for yy in depth_rows(y0, y1, 26, 50)[1:-1]:
        cv.rect(x, yy, w, 0.5, m.d, a=0.4, mode='atop')
    if stains:
        rs = rng_of('stain', seed)
        for _ in range(max(1, int(w / 140))):
            cv.radial(rs.uniform(x, x + w), rs.uniform(y0 + 12, y1 - 8), rs.uniform(8, 16), rs.uniform(3, 5),
                      C('#1e1820'), a=0.28, mode='over', falloff=1.2)
    return mk


# ----------------------------------------------------------------------------- exterior styles
def g_cobble(R, x, w):
    cv = R.cv
    cv.rect(x, FB, w, 5, C('#9a8e80'), ink=C('#3a3038'), iw=DETAIL)
    cv.rect(x, FB, w, 1, C('#d8ccb8'), mode='atop')
    stones(R, x, w, FB + 5, CURB_Y, '#8e8478', hash((R.id, x)) % 9999)
    wall_contact(R, x, w, FB)
    rs = R.rng('cob', x)
    for _ in range(int(w / 260) + 1):
        puddle(R, rs.uniform(x + 30, x + w - 30), rs.uniform(270, 330), rs.uniform(10, 18), rs.uniform(2.2, 3.4),
               sky='#e8d0a0', a=0.3)
    near_curb(R, x, w, top='#8a8074', face='#3e3640')


def g_boardwalk(R, x, w):
    planks(R, x, w, FB, CURB_Y, '#8e6a4a', hash((R.id, 'bw', x)) % 9999, h0=5, h1=11)
    wall_contact(R, x, w, FB, a=120)
    near_curb(R, x, w, top='#6a4e38', face='#2e2630')


def g_bridge_planks(R, x, w):
    """Footbridge over the canal: water strips where rooms.json has water blockers, deck between them."""
    cv = R.cv
    bl = [b for b in R.data.get('blockers', []) if b.get('kind') == 'water' and b['x'] < x + w and b['x'] + b['w'] > x]
    top_w = [b for b in bl if b['y'] <= FB + 2]
    bot_w = [b for b in bl if b['y'] > FB + 2]
    deck0 = top_w[0]['y'] + top_w[0]['h'] if top_w else FB
    deck1 = bot_w[0]['y'] if bot_w else CURB_Y
    for b in bl:
        canal_water(R, b['x'], b['y'], b['w'], b['h'] if b['y'] + b['h'] <= H else H - b['y'], seed=int(b['y']))
    planks(R, x, w, deck0, deck1, '#a07a54', hash((R.id, 'deck')) % 9999, h0=4, h1=7, joint_every=(30, 60))
    cv.vgrad(x, deck0, w, 5, [C('#140c1c', 120), C('#140c1c', 0)], mode='atop')
    # deck edges (timber kerbs) and railings at both water sides
    for yy, up in ((deck0, True), (deck1, False)):
        cv.rect(x, yy - (2.5 if up else 0), w, 2.5, C('#6a4a32'), ink=C('#20141a'), iw=DETAIL)
        cv.rect(x, yy - (2.5 if up else 0), w, 0.6, C('#c89a6a'), mode='atop')
    rail = M(C('#2e3a44'))
    for xx in np.arange(x + 4, x + w, 20):
        cv.rect(xx, deck0 - 16, 1.4, 14, rail.b, ink=rail.i, iw=DETAIL)
    cv.rect(x, deck0 - 17, w, 1.4, rail.b, ink=rail.i, iw=DETAIL)
    cv.rect(x, deck0 - 10, w, 0.7, rail.b)
    # front railing (seen low, over the near water)
    for xx in np.arange(x + 4, x + w, 20):
        cv.rect(xx, deck1 + 0.5, 1.4, 9, rail.b, ink=rail.i, iw=DETAIL)
    cv.rect(x, deck1 + 2, w, 1.2, rail.b, ink=rail.i, iw=DETAIL)
    R.ambient.append({"type": "water_shimmer", "x": float(x), "y": float(top_w[0]['y'] if top_w else FB), "w": float(w),
                      "h": float(top_w[0]['h'] if top_w else 30)})
    if bot_w:
        R.ambient.append({"type": "water_shimmer", "x": float(x), "y": float(deck1 + 4), "w": float(w),
                          "h": float(H - deck1 - 4)})


def canal_water(R, x, y, w, h, seed=0, deep='#1e4a5a', mid='#2e7a84', light_c='#8ad0c8', sky=None):
    cv = R.cv
    mk = cv.vgrad(x, y, w, h, [C(mid), C(deep)])
    x0, y0, mm = mk
    hh, ww = mm.shape
    X = (np.arange(ww, dtype=np.float32) + x0 + 0.5) / cv.D
    Y = (np.arange(hh, dtype=np.float32) + y0 + 0.5) / cv.D
    XX, YY = np.meshgrid(X, Y)
    n = value_noise(ww, hh, 6 * cv.D, seed + 11, 2)
    wav = np.sin(XX * 0.35 + YY * 1.3 + n * 6) * 0.5 + 0.5
    lines = np.clip((wav - 0.86) * 7, 0, 1) * (0.5 + 0.5 * n)
    cv.paint((x0, y0, lines * mm * 0.75), C(light_c), mode='atop')
    dk = np.clip((0.2 - wav) * 4, 0, 1)
    cv.paint((x0, y0, dk * mm * 0.35), C(deep), mode='atop')
    if sky:
        cv.vgrad(x, y, w, min(h, 12), [C(sky, 120), C(sky, 0)], mode='atop')
    if hasattr(R, 'water'):
        R.water.append({"rect": [round(x, 1), round(y, 1), round(w, 1), round(h, 1)], "kind": "canal",
                        "tint": light_c})
    return mk


def g_gravel_rail(R, x, w):
    cv = R.cv
    m = M(C('#7a7470'))
    mk = cv.vgrad(x, FB, w, CURB_Y - FB, [shade(m.b, 0.3), m.b, light(m.b, 0.15)])
    x0, y0, mm = mk
    n = value_noise(mm.shape[1], mm.shape[0], 0.9 * cv.D, hash((R.id, 'grav')) % 9999, 1)
    cv.paint((x0, y0, (n - 0.5).clip(0, 1) * 0.22 * mm), m.l, mode='atop')
    cv.paint((x0, y0, (0.5 - n).clip(0, 1) * 0.22 * mm), m.d, mode='atop')
    _noise_tone(R, mk, 26, 7, 0.05, 0.12, m)
    # embedded track: sleepers + two rails, low contrast
    ty0, ty1 = 286, 312
    xx = x
    while xx < x + w:
        cv.fill_poly([(xx, ty0 - 2), (xx + 5, ty0 - 2), (xx + 7, ty1 + 3), (xx + 2, ty1 + 3)], C('#5a4a40'), a=0.38,
                     mode='atop')
        xx += 11
    for ry in (ty0, ty1):
        cv.rect(x, ry - 1.2, w, 2.4, C('#6a6a72'), a=0.6, mode='atop')
        cv.rect(x, ry - 1.2, w, 0.7, C('#c8ccd8'), a=0.45, mode='atop')
        cv.rect(x, ry + 0.8, w, 0.6, C('#2a2430'), a=0.4, mode='atop')
    cv.rect(x, FB, w, 3, C('#5a5458'), ink=C('#2a2430'), iw=DETAIL)
    wall_contact(R, x, w, FB)
    rs = R.rng('grw')
    for _ in range(int(w / 30)):
        weeds(R, rs.uniform(x, x + w), rs.uniform(FB + 4, CURB_Y - 2), rs.randint(2, 4), seed=rs.randint(0, 9999),
              col='#6a7a4a')
    near_curb(R, x, w, top='#6a645e', face='#2e2a32')


def g_foundry(R, x, w):
    cv = R.cv
    concrete_floor(R, x, w, FB, CURB_Y, '#6a6464', hash((R.id, 'fd')) % 9999, joints=80)
    rs = R.rng('fplate')
    # steel floor plates (diamond tread) in a few bays
    for k in range(int(w / 300) + 1):
        px = x + 60 + k * 300 + rs.uniform(-20, 20)
        if px > x + w - 90:
            break
        pw, py = rs.uniform(60, 90), rs.uniform(250, 300)
        plate = M(C('#7a7c86'))
        mk = cv.fill_poly([(px, py), (px + pw, py), (px + pw + 6, py + 24), (px + 6, py + 24)], plate.b,
                          ink=plate.d, iw=DETAIL, a=0.85, mode='atop')
        x0, y0, mm = mk
        hh, ww = mm.shape
        XX, YY = np.meshgrid(np.arange(ww), np.arange(hh))
        pat = ((XX + YY * 2) % 10 < 2) | ((XX - YY * 2) % 10 < 2)
        cv.paint((x0, y0, pat.astype(np.float32) * mm * 0.35), plate.l, mode='atop')
    # painted hazard line along the wall
    xx = x
    while xx < x + w:
        cv.fill_poly([(xx, FB + 3), (xx + 6, FB + 3), (xx + 9, FB + 7), (xx + 3, FB + 7)], C('#d8b030'), a=0.6,
                     mode='atop')
        xx += 12
    wall_contact(R, x, w, FB)
    near_curb(R, x, w, top='#5a5658', face='#262228')


def g_neon(R, x, w):
    cv = R.cv
    rm.sidewalk(R, x, w, base='#5a5260')
    rm.curb(R, x, w, top='#6a6270', face='#2e2a36')
    rm.asphalt(R, x, w, base='#3a3446', lane=R.id != 'nm_backalley')
    rs = R.rng('nwet')
    for _ in range(int(w / 200) + 1):
        puddle(R, rs.uniform(x + 30, x + w - 30), rs.uniform(262, 334), rs.uniform(12, 26), rs.uniform(2.5, 4.5),
               sky=rs.choice(['#ff5aa0', '#5ae0ff', '#c070ff']), a=0.35)
    R.reflect.append({"rect": [float(x), 251.0, float(w), 93.0], "alpha": 0.16})
    near_curb(R, x, w, top='#4a4452', face='#1e1a26')


def g_wet(R, x, w):
    cv = R.cv
    rm.sidewalk(R, x, w, base='#5a6266')
    rm.curb(R, x, w, top='#6a7276', face='#2a3036')
    rm.asphalt(R, x, w, base='#3a4248', lane_y=300)
    # wet sheen: cool sky gradient + streaky reflections
    cv.vgrad(x, 251, w, 93, [C('#8ab0b8', 60), C('#8ab0b8', 0)], mode='atop')
    rs = R.rng('wetp')
    for _ in range(int(w / 150) + 1):
        puddle(R, rs.uniform(x + 20, x + w - 20), rs.uniform(258, 338), rs.uniform(14, 34), rs.uniform(2.5, 5),
               sky='#a8c8c8', a=0.4)
    R.reflect.append({"rect": [float(x), 218.0, float(w), 126.0], "alpha": 0.2})
    R.ambient.append({"type": "drip", "x": float(x + w * 0.3), "y": 120.0, "rate": 0.5})
    near_curb(R, x, w, top='#4e5458', face='#1e2428')


def g_rooftop(R, x, w):
    cv = R.cv
    m = M(C('#4e4852'))
    mk = cv.vgrad(x, FB, w, CURB_Y - FB, [shade(m.b, 0.3), m.b, light(m.b, 0.12)])
    x0, y0, mm = mk
    n = value_noise(mm.shape[1], mm.shape[0], 0.8 * cv.D, hash((R.id, 'tar')) % 9999, 1)
    cv.paint((x0, y0, (n - 0.5).clip(0, 1) * 0.18 * mm), m.l, mode='atop')
    _noise_tone(R, mk, 30, 13, 0.05, 0.12, m)
    for yy in depth_rows(FB, CURB_Y, 18, 40)[1:-1]:
        cv.rect(x, yy, w, 0.8, m.d, a=0.55, mode='atop')
        cv.rect(x, yy + 0.8, w, 0.5, m.l, a=0.4, mode='atop')
    rs = R.rng('roof')
    for _ in range(int(w / 180)):
        puddle(R, rs.uniform(x + 20, x + w - 20), rs.uniform(250, 336), rs.uniform(8, 18), rs.uniform(2, 3.5),
               sky='#6a5aa0', a=0.35)
    # roof parapet along the front edge (below the walk band)
    pm = M(C('#7a5a50'))
    cv.rect(x, CURB_Y, w, H - CURB_Y, pm.b)
    kit.brick_wall(cv, x, CURB_Y + 3, w, H - CURB_Y - 3, pm.b, seed=33, soot=0.2)
    cv.rect(x, CURB_Y, w, 3, C('#b0a090'), ink=C('#2a2026'), iw=DETAIL)
    cv.rect(x, CURB_Y, w, 0.8, C('#e8d8c0'), mode='atop')
    R.reflect.append({"rect": [float(x), 240.0, float(w), 100.0], "alpha": 0.1})


def g_warehouse_floor(R, x, w):
    cv = R.cv
    concrete_floor(R, x, w, FB, CURB_Y, '#7a7c78', hash((R.id, 'wf')) % 9999, joints=96)
    # yellow safety lines + hatched zones
    cv.rect(x, 232, w, 1.6, C('#d8b830'), a=0.55, mode='atop')
    cv.rect(x, 334, w, 1.6, C('#d8b830'), a=0.5, mode='atop')
    rs = R.rng('wfz')
    for _ in range(int(w / 500) + 1):
        hx = rs.uniform(x + 40, x + w - 120)
        for k in range(8):
            cv.fill_poly([(hx + k * 10, 236), (hx + k * 10 + 4, 236), (hx + k * 10 + 1, 244), (hx + k * 10 - 3, 244)],
                         C('#d8b830'), a=0.35, mode='atop')
    cv.vgrad(x, 251, w, 90, [C('#c8e0d0', 40), C('#c8e0d0', 0)], mode='atop')
    wall_contact(R, x, w, FB)
    R.reflect.append({"rect": [float(x), 230.0, float(w), 110.0], "alpha": 0.1})
    near_curb(R, x, w, top='#6a6c68', face='#262a28')


def g_office(R, x, w):
    tiles(R, x, w, FB, CURB_Y, '#8a8a7a', '#7a7a6c', hash((R.id, 'of')) % 9999, tile=14, h0=5, h1=13)
    wall_contact(R, x, w, FB)
    near_curb(R, x, w, top='#5a5a50', face='#24241e')


# ----------------------------------------------------------------------------- interior floors
def g_garage_floor(R, x, w):
    concrete_floor(R, x, w, WB, H, '#7a746c', hash((R.id, 'gf')) % 9999, joints=80)
    cv = R.cv
    rs = R.rng('gfo')
    for _ in range(3):
        cv.radial(rs.uniform(x + 60, x + w - 40), rs.uniform(250, 330), rs.uniform(10, 18), rs.uniform(3, 5),
                  C('#1a1418'), a=0.3, mode='over', falloff=1.1)
    wall_contact(R, x, w, WB)


def g_gym_floor(R, x, w):
    planks(R, x, w, WB, H, '#b88a56', hash((R.id, 'gym')) % 9999, h0=4, h1=9, joint_every=(60, 120), nails=False)
    cv = R.cv
    cv.rect(x, 300, w, 1.4, C('#c83a3a'), a=0.45, mode='atop')
    cv.ellipse(x + w / 2, 300, 50, 12, None, ink=C('#c83a3a'), iw=0.7, a=0.4, mode='atop')
    cv.vgrad(x, WB, w, 60, [C('#ffe8c0', 50), C('#ffe8c0', 0)], mode='atop')
    wall_contact(R, x, w, WB)
    R.reflect.append({"rect": [float(x), 236.0, float(w), 124.0], "alpha": 0.1})


def g_wood_floor(R, x, w):
    planks(R, x, w, WB, H, '#9a6a44', hash((R.id, 'wd')) % 9999, h0=4, h1=10)
    wall_contact(R, x, w, WB)
    R.reflect.append({"rect": [float(x), 236.0, float(w), 124.0], "alpha": 0.08})


def g_carpet(R, x, w):
    cv = R.cv
    m = M(C('#8a3a3e'))
    mk = cv.vgrad(x, WB, w, H - WB, [shade(m.b, 0.4), m.b, light(m.b, 0.1)])
    x0, y0, mm = mk
    hh, ww = mm.shape
    XX, YY = np.meshgrid(np.arange(ww), np.arange(hh))
    pat = (((XX // 24) + (YY // 14)) % 2 == 0) & ((XX % 24 < 3) | (YY % 14 < 2))
    cv.paint((x0, y0, pat.astype(np.float32) * mm * 0.12), C('#d8a060'), mode='atop')
    _noise_tone(R, mk, 1.0, 5, 0.04, 0.04, m)
    cv.rect(x, WB + 4, w, 3, C('#d8a060'), a=0.35, mode='atop')
    wall_contact(R, x, w, WB)


def g_tile_floor(R, x, w):
    tiles(R, x, w, WB, H, '#c8ccc0', '#b6bdb2', hash((R.id, 'tf')) % 9999, tile=10, h0=4, h1=10, checker=True)
    wall_contact(R, x, w, WB)
    R.reflect.append({"rect": [float(x), 236.0, float(w), 124.0], "alpha": 0.1})


def g_arcade_carpet(R, x, w):
    cv = R.cv
    m = M(C('#241a3a'))
    mk = cv.vgrad(x, WB, w, H - WB, [shade(m.b, 0.3), m.b, light(m.b, 0.1)])
    rs = R.rng('arc')
    cols = ['#ff4ab0', '#4ae0ff', '#f8e040', '#7aff8a']
    for _ in range(int(w * 1.1)):
        px, py = rs.uniform(x, x + w), rs.uniform(WB + 2, H)
        c = C(rs.choice(cols))
        s = 0.5 + (py - WB) / (H - WB) * 1.2
        kind = rs.random()
        if kind < 0.4:
            cv.ellipse(px, py, s, s * 0.5, c, a=0.32, mode='atop')
        elif kind < 0.7:
            cv.line([(px, py), (px + s * 2.5, py - s * 0.6)], 0.4 * s, c, a=0.3, mode='atop')
        else:
            cv.fill_poly([(px, py - s * 0.6), (px + s, py + s * 0.4), (px - s, py + s * 0.4)], c, a=0.3, mode='atop')
    wall_contact(R, x, w, WB)


def g_white_tile(R, x, w):
    tiles(R, x, w, WB, H, '#e4e8ea', '#c8d8dc', hash((R.id, 'wt')) % 9999, tile=14, h0=5, h1=14,
          grout=C('#b8c0c4'))
    wall_contact(R, x, w, WB, a=110)
    R.reflect.append({"rect": [float(x), 236.0, float(w), 124.0], "alpha": 0.12})


def g_plank_floor(R, x, w):
    planks(R, x, w, WB, H, '#7a6a54', hash((R.id, 'pk')) % 9999, h0=5, h1=11, joint_every=(30, 70))
    cv = R.cv
    rs = R.rng('pkw')
    for _ in range(4):
        cv.radial(rs.uniform(x + 40, x + w - 40), rs.uniform(250, 340), rs.uniform(8, 16), rs.uniform(2.5, 4),
                  C('#2a3a3a'), a=0.25, mode='over', falloff=1.2)
    wall_contact(R, x, w, WB)


GROUNDS2 = {
    'cobble': g_cobble, 'boardwalk': g_boardwalk, 'bridge_planks': g_bridge_planks, 'gravel_rail': g_gravel_rail,
    'foundry_floor': g_foundry, 'neon_asphalt': g_neon, 'wet_road': g_wet, 'rooftop': g_rooftop,
    'warehouse_floor': g_warehouse_floor, 'office_floor': g_office,
    'garage_floor': g_garage_floor, 'gym_floor': g_gym_floor, 'wood_floor': g_wood_floor, 'carpet_floor': g_carpet,
    'tile_floor': g_tile_floor, 'arcade_carpet': g_arcade_carpet, 'white_tile': g_white_tile,
    'plank_floor': g_plank_floor,
}
