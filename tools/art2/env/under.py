"""Backstreet Oath env v2 -- The Underline: abandoned 1970s subway under the river (opaque, no sky).

Cold green-grey tile and concrete, failing fluorescents, warm Mole work lights.
"""
import math

import numpy as np

from raster import Canvas, C, mix, shade, light, ink_of, rng_of, value_noise
import kit
from kit import M, MAJOR, DETAIL, poster, tag, painted_text, neon_text, cable, string_lights
from room import FACADE_BOTTOM as FB, H, CURB_Y, light_pool, puddle, near_curb, weeds
from common import facade, wall, chainlink, lantern
from iron import hazard
from flood import greyline_logo
import grounds2
from grounds2 import tiles, concrete_floor, depth_rows, wall_contact

TILE = '#c4ccbe'


def tile_wall(cv, x, y, w, h, base=TILE, seed=0, tw=8.0, th=4.0, grime=0.45):
    """Glazed subway tile: running bond, per-tile tone, grout, glaze highlight, grime toward the floor."""
    m = M(C(base))
    mk = cv.rect(x, y, w, h, m.b)
    rs = np.random.default_rng(seed)
    lut = rs.random((512, 512)).astype(np.float32)
    bs = np.array(m.b[:3], np.float32) / 255
    gr = np.array(shade(m.b, 0.9)[:3], np.float32) / 255
    hi = np.array(light(m.b, 1.4)[:3], np.float32) / 255

    def fn(X, Y):
        row = np.floor((Y - y) / th).astype(np.int64)
        off = (row % 2) * tw / 2
        col = np.floor((X - x + off) / tw).astype(np.int64)
        fx = (X - x + off) - col * tw
        fy = (Y - y) - row * th
        v = (lut[row % 512, col % 512] - 0.5) * 0.07
        c = bs[None, None, :] * (1 + v[..., None])
        c = np.where((fy < 0.7)[..., None], c * 0.5 + hi * 0.5, c)
        c = np.where(((fy > th - 0.5) | (fx < 0.5))[..., None], gr, c)
        return np.clip(c, 0, 1)
    cv.texture(mk, fn)
    kit.weather(cv, x, y, w, h, seed + 1, soot=grime, blotch=0.18, streak=True)
    # missing / broken tiles
    rr = rng_of('tilebreak', seed)
    for _ in range(int(w / 40)):
        bx = x + rr.uniform(0, w - tw)
        by = y + int(rr.uniform(0, h - th) / th) * th
        cv.rect(bx, by, tw - 0.5, th - 0.5, C('#5a5e56'), mode='atop')
        cv.rect(bx, by, tw - 0.5, 0.6, C('#2a2e2a'), mode='atop')
    return mk


def mosaic_band(R, x, y, w, h, text, seed=0):
    """'KESSLER ST' station-name mosaic with a border key pattern."""
    cv = R.cv
    cv.rect(x, y, w, h, C('#2e5a52'), ink=C('#0e1a18'), iw=MAJOR)
    rs = rng_of('mos', seed)
    # border tesserae
    for yy in (y + 1, y + h - 3):
        xx = x + 1
        k = 0
        while xx < x + w - 2:
            cv.rect(xx, yy, 1.8, 1.8, C(['#c8a040', '#e8e0c8', '#a8402e'][k % 3]), mode='atop')
            xx += 2.2
            k += 1
    cv.rect(x + 4, y + 4, w - 8, h - 8, C('#e8e0c8'), ink=C('#3a3a2e'), iw=DETAIL)
    mk = cv.text_mask(text, 'sign', h * 0.42, x + w / 2, y + h / 2 + 0.5, 'mm', tracking=1.2)
    x0, y0, m = mk
    # quantise lettering into tesserae
    hh, ww = m.shape
    cell = max(2, int(cv.D * 1.0))
    q = m[:hh - hh % cell, :ww - ww % cell].reshape(hh // cell, cell, ww // cell, cell).mean(axis=(1, 3))
    q = (q > 0.45).astype(np.float32)
    big = np.kron(q, np.ones((cell, cell), np.float32))
    grout = np.ones_like(big)
    grout[::cell, :] = 0.75
    grout[:, ::cell] = 0.75
    cv.paint((x0, y0, big * grout), C('#1e3e5a'))
    kit.weather(cv, x, y, w, h, seed + 3, soot=0.2, blotch=0.25, streak=True)


def retro_ad(R, x, y, w, h, kind, seed=0):
    cv = R.cv
    cv.rect(x - 2, y - 2, w + 4, h + 4, C('#5a5e5a'), ink=C('#141814'), iw=MAJOR)
    if kind == 'air':
        cv.vgrad(x, y, w, h, [C('#f0a040'), C('#e86a4a'), C('#8a3a6a')])
        for k in range(4):
            cv.rect(x, y + h * 0.45 + k * 4, w, 1.6, C('#ffd060'), a=0.9, mode='atop')
        cv.fill_poly([(x + w * 0.2, y + h * 0.3), (x + w * 0.8, y + h * 0.2), (x + w * 0.74, y + h * 0.26)], C('#f4f0e8'))
        cv.text('FLY BELLWETHER AIR', 'cond', h * 0.11, x + w / 2, y + h * 0.82, C('#f4f0e8'), 'mm')
    elif kind == 'cola':
        cv.vgrad(x, y, w, h, [C('#c8302a'), C('#8a1a1a')])
        cv.ellipse(x + w * 0.3, y + h * 0.55, w * 0.14, h * 0.32, C('#3a1a10'), ink=C('#f4f0e8'), iw=0.8)
        cv.text('FIZZ', 'sign', h * 0.22, x + w * 0.66, y + h * 0.4, C('#f4f0e8'), 'mm')
        cv.text('1971 TASTE', 'cond', h * 0.1, x + w * 0.66, y + h * 0.68, C('#f8d060'), 'mm')
    else:
        cv.vgrad(x, y, w, h, [C('#6aa0b0'), C('#2a5a6a')])
        cv.text('RIDE THE', 'cond', h * 0.12, x + w / 2, y + h * 0.3, C('#f4f0e8'), 'mm')
        cv.text('UNDERLINE', 'sign', h * 0.18, x + w / 2, y + h * 0.52, C('#f8d060'), 'mm')
    kit.weather(cv, x, y, w, h, seed, soot=0.25, blotch=0.35, streak=True)
    # peeling: torn strips showing tile/backing
    rs = rng_of('peel', seed)
    for _ in range(2):
        px = x + rs.uniform(0, w * 0.7)
        cv.fill_poly([(px, y + h), (px + rs.uniform(8, 16), y + h), (px + rs.uniform(4, 10), y + h - rs.uniform(10, 22))],
                     C('#d8d4c0'), ink=C('#6a665a'), iw=0.4)
    cv.fill_poly([(x + w, y), (x + w - 10, y), (x + w, y + 12)], C('#e8e4d0'), ink=C('#6a665a'), iw=0.4)


def route_map(R, x, y, w, h):
    cv = R.cv
    cv.rect(x - 2, y - 2, w + 4, h + 4, C('#3a3e3a'), ink=C('#0e100e'), iw=MAJOR)
    cv.rect(x, y, w, h, C('#e8e4d4'))
    cv.text('UNDERLINE  -  1968', 'cond', 4.4, x + w / 2, y + 5, C('#2a2e2a'), 'mm')
    lines = [('#c8302a', [(0.06, 0.4), (0.3, 0.4), (0.5, 0.62), (0.94, 0.62)]),
             ('#2a6ab0', [(0.06, 0.8), (0.4, 0.8), (0.55, 0.62), (0.7, 0.3), (0.94, 0.3)]),
             ('#e8b830', [(0.2, 0.2), (0.3, 0.4), (0.4, 0.8)])]
    for col, pts in lines:
        cv.line([(x + w * px, y + 10 + (h - 14) * py) for px, py in pts], 1.4, C(col))
    for name, (px, py) in (('KESSLER ST', (0.3, 0.4)), ('MILL CUT', (0.5, 0.62)), ('FLOODGATE', (0.94, 0.62)),
                           ('DOCKS', (0.94, 0.3)), ('FOUNDRY', (0.06, 0.8))):
        cx, cy = x + w * px, y + 10 + (h - 14) * py
        cv.ellipse(cx, cy, 1.6, 1.6, C('#f4f0e8'), ink=C('#1a1a1a'), iw=0.5)
        cv.text(name, 'cond', 2.6, cx, cy - 3.6, C('#2a2e2a'), 'mm')
    cv.ellipse(x + w * 0.3, y + 10 + (h - 14) * 0.4, 3.2, 3.2, None, ink=C('#c8302a'), iw=0.6)
    cv.text('YOU ARE HERE', 'cond', 2.4, x + w * 0.3, y + 10 + (h - 14) * 0.4 + 5, C('#c8302a'), 'mm')
    kit.weather(cv, x, y, w, h, 77, soot=0.2, blotch=0.3)


def mole_graffiti(R, x, y, s=1.0, col='#a88a6a', seed=0):
    """Cartoon mole with a miner's headlamp, spray-painted (white halo, drips)."""
    cv = R.cv
    lay = cv.layer(x - 30 * s, y - 34 * s, 64 * s, 72 * s)
    lay.ellipse(x, y + 8 * s, 15 * s, 17 * s, C(col))
    lay.ellipse(x, y - 8 * s, 11 * s, 10 * s, C(col))
    lay.ellipse(x + 9 * s, y - 5 * s, 4 * s, 3 * s, C('#e88a9a'))               # snout
    lay.ellipse(x + 2 * s, y - 10 * s, 1.6 * s, 1.6 * s, C('#1a1420'))
    lay.ellipse(x + 6 * s, y - 10 * s, 1.6 * s, 1.6 * s, C('#1a1420'))
    lay.fill_poly([(x - 11 * s, y - 14 * s), (x - 7 * s, y - 24 * s), (x + 8 * s, y - 24 * s), (x + 12 * s, y - 14 * s)],
                  C('#e8b830'))                                                   # helmet
    lay.ellipse(x + 2 * s, y - 20 * s, 3 * s, 3 * s, C('#fff8c0'))               # headlamp
    lay.fill_poly([(x + 4 * s, y - 22 * s), (x + 30 * s, y - 32 * s), (x + 30 * s, y - 10 * s), (x + 4 * s, y - 18 * s)],
                  C('#fff4a0'), a=0.45)
    for k in (-1, 1):
        lay.ellipse(x + k * 12 * s, y + 6 * s, 4 * s, 3 * s, C('#e88a9a'))       # paws
    lay.ellipse(x - 7 * s, y + 24 * s, 6 * s, 3 * s, C('#6a5444'))
    lay.ellipse(x + 7 * s, y + 24 * s, 6 * s, 3 * s, C('#6a5444'))
    cv.merge(lay, ink=C('#f4f0e8'), iw=1.2)
    cv.text('MOLES', 'sign', 7 * s, x, y + 34 * s, C('#e8b830'), 'mm', ink=C('#1a1420'), iw=0.8)
    for k in range(3):
        dx = x - 10 * s + k * 10 * s
        cv.line([(dx, y + 38 * s), (dx, y + 38 * s + 4 + k * 2)], 0.6, C('#e8b830'))


def work_lamp(R, x, y, on=True, cage=True, col='#ffb050'):
    """Mole clip-on cage work lamp (warm) with a short cable."""
    cv = R.cv
    cv.rect(x - 0.3, y - 8, 0.6, 8, C('#1a1418'))
    cv.fill_poly([(x - 4, y + 5), (x + 4, y + 5), (x + 2.5, y), (x - 2.5, y)], C('#3a3a40'), ink=C('#0e0a10'), iw=DETAIL)
    if on:
        cv.ellipse(x, y + 5.5, 3, 1.4, C('#fff0b0'), em=1.0)
        cv.radial(x, y + 14, 18, 22, C(col), a=0.22, mode='add')
        R.glow(x, y + 6, 26, col, 0.55, 'flame')
        R.light(x, 262, 56, 46, col, 0.18)
    if cage:
        for k in range(-2, 3):
            cv.line([(x + k * 1.6, y + 5), (x + k * 1.2, y + 8)], 0.3, C('#2a2a30'))


def fluor_tube(R, x, y, w=40, state='on'):
    cv = R.cv
    cv.rect(x - 0.3 + w * 0.2 - w / 2, y - 10, 0.6, 10, C('#2a2a30'))
    cv.rect(x - 0.3 + w * 0.3, y - 10, 0.6, 10, C('#2a2a30'))
    cv.rect(x - w / 2, y, w, 3, C('#8a908a'), ink=C('#1a1e1a'), iw=DETAIL)
    if state == 'off':
        cv.rect(x - w / 2 + 2, y + 2, w - 4, 1.4, C('#5a605a'))
        return
    cv.rect(x - w / 2 + 2, y + 2, w - 4, 1.4, C('#e0fff0'), em=1.0)
    cv.radial(x, y + 10, w * 0.7, 20, C('#d0ffe8'), a=0.14, mode='add')
    R.glow(x, y + 3, w * 0.9, '#d8ffec', 0.32 if state == 'on' else 0.22, 'fluor')
    R.light(x, 270, w * 1.6, 60, '#c8f0e0', 0.07 if state == 'on' else 0.04)


def ceiling(R, x0, w, y1=34, kind='girders'):
    cv = R.cv
    cv.vgrad(x0, 0, w, y1, [C('#1e2422'), C('#38403c')])
    if kind == 'girders':
        xx = x0
        while xx < x0 + w:
            cv.rect(xx, 0, 6, y1, C('#2a3230'), ink=C('#0a0e0c'), iw=DETAIL)
            xx += 64
        cv.rect(x0, y1 - 5, w, 5, C('#3e4844'), ink=C('#0a0e0c'), iw=MAJOR)
        hazard(cv, x0, y1 - 2, w, 2, a=0.5)
    # cable trays
    cv.rect(x0, y1 + 2, w, 2.6, C('#4a524e'), ink=C('#0e1210'), iw=DETAIL)
    for k in range(3):
        cable(cv, x0 - 5, y1 + 6 + k * 1.4, x0 + w + 5, y1 + 6 + k * 1.4, sag=0, w=0.6,
              col=['#1a1a1e', '#3a2a1e', '#1e2a3a'][k])


def drip_streaks(R, x, w, y0, y1, n=None, seed=0):
    cv = R.cv
    rs = rng_of('drips', seed)
    for _ in range(n or int(w / 30)):
        dx = rs.uniform(x, x + w)
        cv.vgrad(dx, y0, rs.uniform(1.5, 4), rs.uniform(20, y1 - y0), [C('#2a3a30', 160), C('#2a3a30', 0)], a=0.6,
                 mode='atop')
    for k in range(int(w / 260) + 1):
        R.ambient.append({"type": "drip", "x": float(x + 120 + k * 260 + rs.uniform(-40, 40)), "y": float(y0 + 10),
                          "rate": round(rs.uniform(0.3, 0.7), 2)})


# ----------------------------------------------------------------------------- Kessler St. Station
@facade("subway_platform")
def f_subway_platform(R, x0, w, f):
    cv = R.cv
    rs = R.rng('plat')
    ceiling(R, x0, w, 34)
    # far wall across the tracks
    tile_wall(cv, x0, 40, w, 136, seed=4101)
    cv.rect(x0, 40, w, 3, C('#2e5a52'))
    cv.rect(x0, 150, w, 4, C('#2e5a52'))
    mosaics = [float(m) for m in np.arange(x0 + 480, x0 + w - 100, 480)]
    for xx in mosaics:
        mosaic_band(R, xx - 90, 92, 180, 30, f.get('sign', 'KESSLER ST'), seed=int(xx))
    for k, xx in enumerate(np.arange(x0 + 150, x0 + w - 60, 240)):
        if any(abs(xx + 30 - m) < 130 for m in mosaics) or abs(xx + 30 - (x0 + 1241)) < 90 \
                or abs(xx + 30 - (x0 + 680)) < 80:
            continue
        retro_ad(R, xx, 52, 62, 36, ['air', 'cola', 'ride'][k % 3], seed=int(xx))
    route_map(R, x0 + 1196, 58, 90, 56)
    # CLOSED 1971 board hung on chains
    bx = x0 + 640
    for cx in (bx + 8, bx + 72):
        cv.line([(cx, 43), (cx, 56)], 0.5, C('#6a6a6a'))
    cv.rect(bx, 56, 80, 22, C('#e8e0c8'), ink=C('#1a1a14'), iw=MAJOR)
    cv.text('CLOSED', 'sign', 9, bx + 40, 64, C('#c8302a'), 'mm')
    cv.text('BY ORDER  -  1971', 'cond', 4, bx + 40, 73, C('#2a2a24'), 'mm')
    kit.weather(cv, bx, 56, 80, 22, 51, soot=0.2, blotch=0.3)
    mole_graffiti(R, x0 + 1300, 120, 0.9)
    tag(cv, x0 + 140, 140, 'MOLES', C('#e8b830'), size=7, seed=61)
    tag(cv, x0 + 860, 136, 'DIG DEEP', C('#f4f0e8'), size=6, seed=62, a=0.7)
    drip_streaks(R, x0, w, 43, 176, seed=1)
    # track trench + rails below the platform edge
    cv.vgrad(x0, 176, w, 34, [C('#141816'), C('#202624')])
    for ry in (192, 202):
        cv.rect(x0, ry, w, 1.8, C('#5a605c'))
        cv.rect(x0, ry, w, 0.6, C('#a8b0ac'), a=0.7)
    xx = x0
    while xx < x0 + w:
        cv.rect(xx, 189, 3, 16, C('#2a2420'), a=0.8)
        xx += 9
    for k in range(int(w / 300) + 1):
        puddle(R, x0 + 150 + k * 300, 205, 18, 2.4, sky='#6a8a80', a=0.35, reflect=False)
    # platform edge: concrete lip + worn yellow safety strip
    cv.rect(x0, 208, w, 8, C('#8a8c84'), ink=C('#1a1e1a'), iw=MAJOR)
    cv.rect(x0, 208, w, 1, C('#c8ccc0'), mode='atop')
    cv.rect(x0, 211, w, 3, C('#d8b830'), a=0.7, mode='atop')
    xx = x0
    while xx < x0 + w:
        cv.ellipse(xx, 212.5, 0.6, 0.6, C('#6a5a20'), a=0.8)
        xx += 3
    # columns standing on the platform's back edge
    for k, cx in enumerate(np.arange(x0 + 120, x0 + w, 240)):
        cv.rect(cx - 5, 34, 10, 182, C('#2e5a52'), ink=C('#0a1a16'), iw=MAJOR)
        cv.hgrad(cx - 5, 34, 10, 182, [C('#5a8a80'), C('#2e5a52'), C('#183a34')], mode='atop')
        for yy in (60, 120, 180):
            cv.ellipse(cx - 3, yy, 0.6, 0.6, C('#8ab0a8'))
            cv.ellipse(cx + 3, yy, 0.6, 0.6, C('#8ab0a8'))
        if k % 2 == 0:
            cv.rect(cx - 9, 130, 18, 10, C('#e8e0c8'), ink=C('#1a1a14'), iw=DETAIL)
            cv.text('KESSLER', 'cond', 3.6, cx, 135, C('#1e3e5a'), 'mm')
    # lights: mostly failing fluorescents, warm Mole work lights strung along the columns
    for k, lx in enumerate(np.arange(x0 + 80, x0 + w, 160)):
        fluor_tube(R, lx, 46, 40, ['on', 'flicker', 'off', 'on', 'off', 'flicker'][k % 6])
    for k, cx in enumerate(np.arange(x0 + 120, x0 + w, 240)):
        if k % 2 == 1:
            work_lamp(R, cx + 8, 150)
    string_lights(cv, x0 + 360, 160, x0 + 840, 160, sag=12, step=10, seed=7,
                  cols=[C('#ffd070'), C('#ffb050')], glow=True)
    R.ambient.append({"type": "dust_motes", "x": float(x0 + 300), "y": 60.0, "w": 400, "h": 150})
    R.ambient.append({"type": "dust_motes", "x": float(x0 + 1100), "y": 60.0, "w": 300, "h": 150})


def g_platform_tile(R, x, w):
    cv = R.cv
    tiles(R, x, w, 216, CURB_Y, '#9aa098', '#8a908a', hash((R.id, 'pt')) % 9999, tile=16, h0=6, h1=14,
          grout=C('#6a706a'))
    wall_contact(R, x, w, 216, a=90)
    rs = R.rng('ptp')
    for _ in range(int(w / 260) + 1):
        puddle(R, rs.uniform(x + 40, x + w - 40), rs.uniform(250, 334), rs.uniform(12, 22), rs.uniform(2.4, 4),
               sky='#8ab0a0', a=0.32)
    for _ in range(int(w / 60)):
        cv.ellipse(rs.uniform(x, x + w), rs.uniform(222, 340), rs.uniform(0.5, 1.2), 0.5, C('#e8e0c8'), a=0.5,
                   mode='atop')
    near_curb(R, x, w, top='#7a7e78', face='#262a28')


# ----------------------------------------------------------------------------- Service Tunnel 3
@facade("subway_tunnel")
def f_subway_tunnel(R, x0, w, f):
    cv = R.cv
    rs = R.rng('tun')
    # arched concrete tunnel: dark crown, ribs every 120 u, curved wall
    cv.vgrad(x0, 0, w, 186, [C('#141a18'), C('#2a3230'), C('#4a524e')])
    mk = cv.rect_mask(x0, 0, w, 186)
    x_0, y_0, mm = mk
    n = value_noise(mm.shape[1], mm.shape[0], 14 * cv.D, 4201, 2)
    cv.paint((x_0, y_0, (0.5 - n).clip(0, 1) * 0.3 * mm), C('#101412'), mode='atop')
    for k, rx in enumerate(np.arange(x0 + 60, x0 + w, 120)):
        cv.fill_poly([(rx - 8, 186), (rx - 8, 40), (rx - 2, 0), (rx + 6, 0), (rx + 8, 40), (rx + 8, 186)], C('#3e4642'),
                     ink=C('#0a0e0c'), iw=MAJOR)
        cv.rect(rx - 8, 40, 2, 146, C('#6a746e'), a=0.6)
    # cable trays + steam pipes along the wall
    for k, y in enumerate((70, 78, 86)):
        cv.rect(x0, y, w, 2.4, C('#4a524e'), ink=C('#0e1210'), iw=0.4)
        for j in range(3):
            cable(cv, x0 - 5, y - 1.5 - j, x0 + w + 5, y - 1.5 - j, sag=0, w=0.5, col=['#1a1a1e', '#3a2a1e', '#1e2a3a'][j])
    pm = M(C('#6a5a4a'))
    for y in (110, 120):
        cv.rect(x0, y, w, 6, pm.b, ink=pm.i, iw=MAJOR)
        cv.vgrad(x0, y, w, 6, [pm.l, pm.b, pm.d], mode='atop')
    for k, px in enumerate(np.arange(x0 + 200, x0 + w, 360)):
        cv.rect(px, 108, 6, 20, pm.s, ink=pm.i, iw=DETAIL)
        cv.ellipse(px + 3, 104, 4, 2, None, ink=C('#c83a2a'), iw=1.0)
        R.ambient.append({"type": "steam", "x": float(px + 3), "y": 110.0, "rate": 0.7})
    drip_streaks(R, x0, w, 20, 186, seed=2)
    # sodium cage lamps on the ribs
    for k, rx in enumerate(np.arange(x0 + 60, x0 + w, 240)):
        lx, ly = rx + 10, 96
        cv.rect(lx - 3, ly, 6, 5, C('#2a2a30'), ink=C('#0a0a0e'), iw=DETAIL)
        on = k % 4 != 2
        cv.rect(lx - 2, ly + 1.5, 4, 2.5, C('#ffb850') if on else C('#5a4a30'), em=1.0 if on else 0.0)
        for j in range(-1, 2):
            cv.line([(lx + j * 2, ly), (lx + j * 2, ly + 5)], 0.3, C('#1a1a1e'))
        if on:
            cv.radial(lx, ly + 20, 26, 40, C('#ffa848'), a=0.14, mode='add')
            R.glow(lx, ly + 3, 30, '#ffb050', 0.55, 'none')
            R.light(lx, 266, 70, 50, '#ffa848', 0.16)
    # track bed with rails behind the walkway
    cv.vgrad(x0, 186, w, 28, [C('#1a1e1c'), C('#2a2e2a')])
    n2 = value_noise(int(w * cv.D), int(28 * cv.D), 1.0 * cv.D, 4203, 1)
    cv.paint((int(x0 * cv.D), int(186 * cv.D), (n2 - 0.5).clip(0, 1) * 0.5), C('#5a5a56'), mode='atop')
    xx = x0
    while xx < x0 + w:
        cv.fill_poly([(xx, 194), (xx + 4, 194), (xx + 5, 208), (xx + 1, 208)], C('#3a3028'), a=0.85)
        xx += 9
    for ry in (196, 206):
        cv.rect(x0, ry, w, 2, C('#5a605c'))
        cv.rect(x0, ry, w, 0.6, C('#c8ccc8'), a=0.7)
    cv.rect(x0, 210, w, 6, C('#7a7c74'), ink=C('#141814'), iw=MAJOR)
    cv.rect(x0, 210, w, 1, C('#b8bcb0'), mode='atop')
    hazard(cv, x0, 213, w, 2.4, a=0.6)
    # Mole camp: draped tarp tent strung from the steam pipes, bedrolls, kettle, crates, oil-drum fire
    cx = x0 + 1180
    mole_camp(R, cx)
    fx = cx + 96
    dm = M(C('#4a3a34'))
    cv.rect(fx - 8, 190, 16, 22, dm.b, ink=dm.i, iw=MAJOR)
    cv.hgrad(fx - 8, 190, 16, 22, [dm.l, dm.b, dm.d], mode='atop')
    for k in range(5):
        hgt = 6 + (k * 7) % 5
        cv.fill_poly([(fx - 6 + k * 3, 190), (fx - 5 + k * 3, 190 - hgt), (fx - 3 + k * 3, 190)], C('#ff8a2a'), em=1.0)
        cv.fill_poly([(fx - 5.5 + k * 3, 190), (fx - 5 + k * 3, 190 - hgt * 0.5), (fx - 4 + k * 3, 190)], C('#ffe07a'),
                     em=1.0)
    cv.radial(fx, 186, 40, 34, C('#ff9040'), a=0.35, mode='add')
    R.glow(fx, 184, 40, '#ff9040', 0.65, 'flame')
    R.glow(fx, 190, 80, '#ff7a30', 0.15, 'flame', front=True)
    R.ambient.append({"type": "embers", "x": float(fx), "y": 182.0})
    R.ambient.append({"type": "smoke", "x": float(fx), "y": 176.0, "rate": 0.5})
    R.light(fx, 240, 110, 60, '#ff9040', 0.32)
    mole_graffiti(R, x0 + 620, 140, 0.8)
    mole_graffiti(R, x0 + 1640, 140, 0.7, col='#9a8a7a')
    tag(cv, x0 + 300, 150, 'MOLES', C('#e8b830'), size=7, seed=71)
    tag(cv, x0 + 1460, 160, 'GREYLINE OUT', C('#f4f0e8'), size=5, seed=72, a=0.6)
    # tunnel number plates
    for k, px in enumerate(np.arange(x0 + 420, x0 + w, 600)):
        cv.rect(px, 50, 30, 12, C('#e8e0c8'), ink=C('#1a1a14'), iw=DETAIL)
        cv.text('T3-%02d' % (k + 1), 'cond', 4.4, px + 15, 56, C('#1e3e5a'), 'mm')
    R.ambient.append({"type": "dust_motes", "x": float(x0 + 900), "y": 80.0, "w": 400, "h": 120})


def mole_camp(R, cx):
    """A real draped tarp: sagging ridge rope tied to the pipes, folds, scalloped hem pegged down, open flap."""
    cv = R.cv
    tm = M(C('#3a6a8a'))
    rl, rr = cx - 78, cx + 78                       # ridge rope ends (tied to the pipe brackets)
    ry = 128

    def ridge(t):
        return ry + 22 + 10 * 4 * t * (1 - t)       # sagging ridge between the tie points

    top = [(cx - 72 + 144 * t, ridge(t)) for t in np.linspace(0, 1, 25)]
    # hem: scallops between peg points along the ground line
    pegs = [cx - 82 + k * 164 / 6 for k in range(7)]
    hem = []
    for i in range(len(pegs) - 1, 0, -1):
        xa, xb = pegs[i], pegs[i - 1]
        for t in np.linspace(0, 1, 6)[:-1]:
            hem.append((xa + (xb - xa) * t, 208 - 5 * math.sin(t * math.pi)))
    hem.append((pegs[0], 208))
    poly = [(pegs[0], 208)] + top + [(pegs[-1], 208)] + hem
    lay = cv.layer(cx - 100, ry - 10, 200, 100)
    lay.fill_poly(poly, tm.b)
    # folds: alternating cel bands radiating from the ridge to the hem
    n = 9
    for k in range(n):
        t0, t1 = k / n, (k + 0.45) / n
        xa0, ya0 = cx - 72 + 144 * t0, ridge(t0)
        xa1, ya1 = cx - 72 + 144 * t1, ridge(t1)
        bx0 = pegs[0] + (pegs[-1] - pegs[0]) * t0
        bx1 = pegs[0] + (pegs[-1] - pegs[0]) * t1
        lay.fill_poly([(xa0, ya0), (xa1, ya1), (bx1, 210), (bx0, 210)], tm.l if k % 2 == 0 else tm.s, a=0.55,
                      mode='atop')
        lay.line([(xa1, ya1), (bx1, 210)], 0.5, tm.d, a=0.6, mode='atop')
    # lit ridge (warm work-light rim) and darker hem
    lay.line(top, 0.9, C('#ffc890'), a=0.55, mode='atop')
    lay.vgrad(cx - 90, 190, 180, 20, [C('#0e1a28', 0), C('#0e1a28', 120)], mode='atop')
    # weathering: patches + a taped repair
    kit.weather(lay, cx - 80, ry, 160, 82, 4401, soot=0.3, blotch=0.2, streak=True)
    lay.rect(cx + 30, 166, 12, 9, C('#6a7a5a'), ink=tm.d, iw=0.4, mode='atop')
    lay.line([(cx + 28, 168), (cx + 44, 168)], 0.6, C('#d8d0b0'), mode='atop')
    lay.line([(cx + 28, 173), (cx + 44, 173)], 0.6, C('#d8d0b0'), mode='atop')
    # tent opening: dark interior with a lantern glow and a bedroll, flap pulled back and tied
    op = [(cx - 26, 208), (cx - 14, 168), (cx - 6, ridge(0.46) + 4), (cx + 2, 168), (cx + 16, 208)]
    lay.fill_poly(op, C('#120e14'))
    lay.radial(cx - 5, 196, 18, 14, C('#ffb060'), a=0.35, mode='add')
    lay.ellipse(cx - 6, 204, 14, 3.4, C('#7a5a3a'), mode='atop')
    lay.fill_poly([(cx + 2, 168), (cx - 6, ridge(0.46) + 4), (cx + 22, 184), (cx + 16, 208)], tm.l,
                  ink=tm.d, iw=0.5)
    lay.line([(cx - 4, ridge(0.46) + 6), (cx + 12, 196)], 0.5, tm.s, a=0.8)
    lay.line([(cx + 20, 184), (cx + 6, 186)], 0.6, C('#c8b890'))
    cv.merge(lay, ink=tm.i, iw=MAJOR)
    cv.ellipse(cx - 5, 196, 1.6, 2.0, C('#fff0b0'), em=1.0)
    # ropes: ridge rope to pipe brackets, guy lines to pegs, knots
    rope = C('#c8b890')
    cv.line([(rl, ry - 4), (cx - 72, ridge(0))], 0.6, rope)
    cv.line([(rr, ry - 4), (cx + 72, ridge(1))], 0.6, rope)
    for px in (rl, rr):
        cv.rect(px - 2, ry - 8, 4, 4, C('#5a5048'), ink=C('#141010'), iw=DETAIL)
    for px in (pegs[0] - 8, pegs[-1] + 8):
        cv.line([(px + (8 if px < cx else -8), 200), (px, 212)], 0.5, rope)
        cv.rect(px - 0.8, 209, 1.6, 4, C('#5a4a3a'))
    for px in pegs:
        cv.ellipse(px, 208, 1.0, 0.8, rope, ink=C('#3a3020'), iw=0.3)
    # clutter in front: bedrolls, crate table with kettle and mug, a stool
    for k, (bx, c) in enumerate(((cx - 66, '#6a7a4a'), (cx - 50, '#8a4a3a'))):
        cv.rect(bx, 201 - k * 4, 22, 7, C(c), ink=ink_of(C(c)), iw=MAJOR)
        cv.ellipse(bx + 22, 204.5 - k * 4, 2.4, 3.5, light(C(c), 1.2), ink=ink_of(C(c)), iw=DETAIL)
        for sx in (bx + 5, bx + 15):
            cv.rect(sx, 201 - k * 4, 1.4, 7, C('#3a2a1a'))
    crx = cx + 36
    cm = M(C('#8a7454'))
    cv.rect(crx, 196, 26, 16, cm.b, ink=cm.i, iw=MAJOR)
    cv.rect(crx, 196, 26, 1, cm.h, mode='atop')
    cv.text('GREYLINE', 'cond', 3.0, crx + 13, 204, C('#2a2a2e'), 'mm', a=0.7)
    km = M(C('#9aa0a8'))
    cv.ellipse(crx + 9, 191.5, 5, 4.4, km.b, ink=km.i, iw=DETAIL)
    cv.rect(crx + 7.5, 186.4, 3, 1.4, km.d)
    cv.line([(crx + 13, 191), (crx + 17, 188)], 0.8, km.b)
    cv.line([(crx + 5, 189), (crx + 9, 185.5), (crx + 13, 189)], 0.5, C('#2a2a30'))
    cv.rect(crx + 18, 192, 3.4, 4, C('#e8e4d8'), ink=C('#3a3a40'), iw=0.3)
    R.ambient.append({"type": "steam", "x": float(crx + 17), "y": 187.0, "rate": 0.3})
    cv.rect(cx - 90, 200, 10, 10, C('#5a4a3a'), ink=C('#1a120e'), iw=DETAIL)
    cv.rect(cx - 91, 199, 12, 2, C('#7a6448'), ink=C('#1a120e'), iw=DETAIL)
    R.glow(cx - 5, 196, 22, '#ffb060', 0.35, 'flame')


def g_track_bed(R, x, w):
    """Service walkway: cracked concrete slabs with a drainage channel and puddles."""
    cv = R.cv
    concrete_floor(R, x, w, 216, CURB_Y, '#6e726c', hash((R.id, 'tb')) % 9999, joints=72)
    cv.rect(x, 330, w, 4, C('#2a2e2c'), a=0.7, mode='atop')
    xx = x + 20
    while xx < x + w:
        cv.rect(xx, 330, 16, 4, C('#141816'), mode='atop')
        for k in range(6):
            cv.rect(xx + 1 + k * 2.5, 330.5, 0.8, 3, C('#5a605c'), mode='atop')
        xx += 180
    rs = R.rng('tbp')
    for _ in range(int(w / 200) + 1):
        puddle(R, rs.uniform(x + 30, x + w - 30), rs.uniform(240, 326), rs.uniform(12, 26), rs.uniform(2.4, 4.2),
               sky='#8aa898', a=0.34)
    for _ in range(int(w / 40)):
        weeds(R, rs.uniform(x, x + w), rs.uniform(218, 340), 2, seed=rs.randint(0, 9999), col='#4a5a3a')
    wall_contact(R, x, w, 216, a=100)
    near_curb(R, x, w, top='#5e625c', face='#222624')


# ----------------------------------------------------------------------------- Greyline Cargo Vault
@facade("cargo_vault")
def f_cargo_vault(R, x0, w, f):
    cv = R.cv
    rs = R.rng('vault')
    # brick barrel vaults springing from piers
    kit.brick_wall(cv, x0, 0, w, FB, C('#6a5448'), seed=4301, soot=0.5)
    vw = 240
    for k, vx in enumerate(np.arange(x0 - 40, x0 + w, vw)):
        pts = [(vx + vw / 2 + math.cos(a) * vw / 2, 90 - math.sin(a) * 70) for a in np.linspace(0, math.pi, 30)]
        cv.line(pts, 6, C('#5a463c'), ink=C('#1a1210'), iw=MAJOR)
        cv.line(pts, 1.0, C('#a88a70'), a=0.6)
        cv.rect(vx - 10, 86, 20, FB - 86, C('#5e4a40'), ink=C('#1a1210'), iw=MAJOR)
        cv.hgrad(vx - 10, 86, 20, FB - 86, [C('#8a7060'), C('#5e4a40'), C('#3a2c26')], mode='atop')
    # old pump machinery remnants (big flywheel + pipe)
    px = x0 + 380
    cv.ellipse(px, 120, 34, 34, None, ink=C('#3a3e44'), iw=4)
    for a in np.linspace(0, math.pi, 4):
        cv.line([(px - math.cos(a) * 32, 120 - math.sin(a) * 32), (px + math.cos(a) * 32, 120 + math.sin(a) * 32)], 2.0,
                C('#3a3e44'))
    cv.ellipse(px, 120, 6, 6, C('#5a5e66'), ink=C('#141820'), iw=MAJOR)
    cv.rect(x0, 160, w, 7, C('#5a5e66'), ink=C('#141820'), iw=MAJOR)
    # Greyline depot: stencilled crates along the back wall
    k = 0
    xx = x0 + 30
    while xx < x0 + w - 120:
        n = rs.randint(1, 3)
        for j in range(n):
            cw, ch = 46, 24
            cy = FB - (j + 1) * ch
            m = M(C(rs.choice(['#8a7454', '#7a6a50', '#94805c'])))
            cv.rect(xx + (j % 2) * 3, cy, cw, ch, m.b, ink=m.i, iw=MAJOR)
            cv.rect(xx + (j % 2) * 3, cy, cw, 1, m.h, mode='atop')
            for bx in (xx + (j % 2) * 3 + 2, xx + (j % 2) * 3 + cw - 4):
                cv.rect(bx, cy, 2, ch, m.s, mode='atop')
            cv.text('GREYLINE', 'cond', 4.6, xx + (j % 2) * 3 + cw / 2, cy + 8, C('#2a2a2e'), 'mm', a=0.8)
            cv.text('BELLWETHER', 'cond', 3.2, xx + (j % 2) * 3 + cw / 2, cy + 15, C('#2a2a2e'), 'mm', a=0.8)
        xx += 70 + rs.uniform(0, 40)
        k += 1
        if k == 3:
            xx += 60
    # boxes of eviction paperwork, papers spilling
    for k, bx in enumerate((x0 + 600, x0 + 640, x0 + 618)):
        by = FB - 14 - (10 if k == 2 else 0)
        cv.rect(bx, by, 30, 14, C('#c8b890'), ink=C('#3a2e1e'), iw=DETAIL)
        cv.text('EVICTIONS' if k != 1 else 'NOTICES', 'cond', 3.4, bx + 15, by + 7, C('#8a2a1a'), 'mm')
        for j in range(3):
            cv.fill_poly([(bx + 4 + j * 8, by), (bx + 10 + j * 8, by - 1), (bx + 11 + j * 8, by + 3), (bx + 5 + j * 8, by + 4)],
                         C('#f4f0e4'), ink=C('#6a6050'), iw=0.3)
    for k in range(5):
        sx = x0 + 580 + k * 16
        cv.fill_poly([(sx, FB - 1), (sx + 7, FB - 2), (sx + 8, FB), (sx + 1, FB + 1)], C('#f0ece0'), ink=C('#6a6050'), iw=0.3)
    greyline_logo(cv, x0 + w / 2 - 40, 40, 2.2)
    cv.text('CARGO VAULT  -  AUTHORISED CREW ONLY', 'cond', 5, x0 + w / 2 - 40, 60, C('#d8dcdc'), 'mm', tracking=0.5)
    mole_graffiti(R, x0 + 860, 120, 0.8)
    tag(cv, x0 + 120, 100, 'LANTERN', C('#e8b830'), size=7, seed=81)
    # east end: chained service ladder up through a hatch + chain-link gate
    lx = x0 + w - 44
    cv.rect(lx - 16, 0, 46, 20, C('#2a2e30'), ink=C('#0a0c0e'), iw=MAJOR)
    cv.radial(lx + 7, 6, 18, 10, C('#a8c8d8'), a=0.2, mode='add')
    for side in (lx, lx + 14):
        cv.rect(side, 10, 2, FB - 10, C('#6a6e74'), ink=C('#141820'), iw=DETAIL)
    yy = 16
    while yy < FB - 4:
        cv.rect(lx, yy, 16, 1.4, C('#6a6e74'), ink=C('#141820'), iw=0.3)
        yy += 7
    chainlink(cv, lx - 18, 120, 52, FB - 120, col='#9aa0a8')
    cv.rect(lx - 18, 120, 52, 2, C('#5a5e66'), ink=C('#141820'), iw=DETAIL)
    for k in range(8):
        cv.ellipse(lx - 6 + k * 3, 168 + abs(k - 3.5) * 1.6, 1.3, 0.9, None, ink=C('#c8ccd4'), iw=0.5)
    cv.rect(lx + 4, 172, 5, 5, C('#d8b040'), ink=C('#3a2a10'), iw=DETAIL)
    cv.rect(lx - 16, 140, 48, 14, C('#f8d040'), ink=C('#2a2010'), iw=DETAIL)
    cv.text('SERVICE LADDER', 'cond', 3.6, lx + 8, 145, C('#2a2010'), 'mm')
    cv.text('FLOODGATE BRIDGE', 'cond', 3.0, lx + 8, 150.5, C('#2a2010'), 'mm')
    # big hanging work-lamp cluster in the middle of the vault (base copy; a closer fg copy hangs in front)
    hx = x0 + 560
    for k, (dx, dy) in enumerate(((-22, 70), (0, 80), (22, 68), (-10, 92), (12, 90))):
        cable(cv, hx, 0, hx + dx, dy - 8, sag=2, w=0.5, col='#1a1418')
        work_lamp(R, hx + dx, dy)
    R.glow(hx, 86, 90, '#ffb860', 0.4, 'flame')
    R.light(hx, 270, 200, 80, '#ffb060', 0.26)
    for k, lx2 in enumerate((x0 + 160, x0 + 900)):
        fluor_tube(R, lx2, 30, 44, 'flicker' if k else 'on')
    drip_streaks(R, x0, w, 10, FB - 20, seed=3)
    R.ambient.append({"type": "dust_motes", "x": float(hx - 120), "y": 80.0, "w": 240, "h": 140})


def g_vault_concrete(R, x, w):
    cv = R.cv
    concrete_floor(R, x, w, 216, CURB_Y, '#6a6a62', hash((R.id, 'vc')) % 9999, joints=90)
    rs = R.rng('vcp')
    for k in range(int(w / 280) + 1):
        gx = x + 140 + k * 280
        cv.ellipse(gx, 300, 9, 3, C('#1a1c1a'), ink=C('#0a0c0a'), iw=DETAIL)
        for j in range(-3, 4):
            cv.rect(gx + j * 2.2 - 0.3, 297.5, 0.6, 5, C('#5a5e5a'))
    for _ in range(int(w / 220) + 1):
        puddle(R, rs.uniform(x + 40, x + w - 60), rs.uniform(240, 334), rs.uniform(12, 24), rs.uniform(2.4, 4),
               sky='#a89070', a=0.3)
    # forklift tyre tracks + painted bay lines
    cv.rect(x, 236, w, 1.4, C('#d8b830'), a=0.4, mode='atop')
    for k in range(int(w / 160)):
        cv.rect(x + 80 + k * 160, 236, 1.4, 20, C('#d8b830'), a=0.35, mode='atop')
    wall_contact(R, x, w, 216, a=120)
    near_curb(R, x, w, top='#5a5a54', face='#22221e')


grounds2.GROUNDS2.update({'platform_tile': g_platform_tile, 'track_bed': g_track_bed, 'vault_concrete': g_vault_concrete})


# ----------------------------------------------------------------------------- foreground framing
def fg_pillar_stub():
    """Low tiled pillar base in the foreground (bottom edge)."""
    w, h = 40, 44
    cv = Canvas(w, h, 2)
    tile_wall(cv, 4, 6, 32, h - 6, base='#8a9a90', seed=5, grime=0.6)
    cv.rect(4, 6, 32, h - 6, None, ink=C('#0a1210'), iw=MAJOR)
    cv.rect(2, 2, 36, 5, C('#2e5a52'), ink=C('#0a1a16'), iw=MAJOR)
    cv.rect(4, 6, 1, h - 6, C('#ffc070'), a=0.4)
    return cv


def fg_lamp_cluster():
    w, h = 90, 110
    cv = Canvas(w, h, 2)
    hx = w / 2
    for (dx, dy) in ((-26, 84), (0, 98), (26, 80)):
        cable(cv, hx, 0, hx + dx, dy - 8, sag=3, w=0.8, col='#141014')
        x, y = hx + dx, dy
        cv.fill_poly([(x - 8, y + 9), (x + 8, y + 9), (x + 5, y), (x - 5, y)], C('#2a2a30'), ink=C('#0a080c'), iw=MAJOR)
        cv.ellipse(x, y + 9.5, 6, 2, C('#fff0b0'))
        cv.radial(x, y + 12, 12, 5, C('#ffd080'), a=0.6, mode='addfree')
        for k in range(-2, 3):
            cv.line([(x + k * 3, y + 9), (x + k * 2.2, y + 14)], 0.6, C('#1a1a1e'))
    return cv


def fg_rail():
    w, h = 110, 36
    cv = Canvas(w, h, 2)
    m = M(C('#3a4a46'))
    for x in (6, 54, 102):
        cv.rect(x - 1.5, 6, 3, h - 6, m.b, ink=m.i, iw=DETAIL)
    cv.rect(0, 6, w, 3, m.b, ink=m.i, iw=DETAIL)
    cv.rect(0, 18, w, 2, m.b, ink=m.i, iw=DETAIL)
    cv.rect(0, 6, w, 0.8, C('#ffc070'), a=0.5)
    return cv


import fg2  # noqa: E402
fg2.DISTRICT_FG['underline'] = [('fg_cables', fg2.fg_cables, 'top', 1.1, False),
                                ('fg_pillar', fg_pillar_stub, 'bottom', 1.28, True),
                                ('fg_rail', fg_rail, 'bottom', 1.25, True)]
