"""Backstreet Oath env v2 -- remaining Old Quarter facades (Brickrow Lane): garage, rec centre, rail tunnel."""
import math

import numpy as np

from raster import C, mix, shade, light, ink_of, rng_of
import kit
from kit import M, MAJOR, DETAIL, window, door, awning, cornice, parapet, brick_wall, drainpipe, cable, \
    neon_text, painted_text, poster, tag, concrete_panel, ac_unit
from room import FACADE_BOTTOM as FB, H, light_pool, sun_rim
from common import facade, door_x, big_door, wall, shop_door, gable, lantern


@facade("garage")
def f_garage(R, x0, w, f):
    cv = R.cv
    top = 74
    wall(cv, 'brick', x0, top, w, FB - top, '#8a5a48', seed=701)
    cv.rect(x0 - 2, top - 6, w + 4, 8, C('#4a5a6a'), ink=C('#141c24'), iw=MAJOR)
    sun_rim(R, x0, top - 6, FB - 40, a=0.4)
    sm = M(C('#2a5a8a'))
    cv.rect(x0 + 30, top + 6, w - 60, 20, sm.b, ink=sm.i, iw=MAJOR)
    painted_text(cv, f.get('sign', 'QUINN GARAGE'), x0 + w / 2, top + 16.5, 11, C('#f4e8c0'), tracking=0.6)
    dx = door_x(R, x0, w)
    # two service bays (left closed roller, right open with work light) + office door at the door x
    big_door(cv, x0 + 16, FB, 100, 80, '#b8b4a8', kind='roller', seed=3)
    bx = x0 + w - 116
    cv.rect(bx - 2, FB - 82, 104, 82, C('#3a3438'), ink=C('#140c10'), iw=MAJOR)
    cv.vgrad(bx, FB - 80, 100, 80, [C('#ffe0a0'), C('#e8a060'), C('#7a4a3a')], em=1.0)
    cv.rect(bx + 10, FB - 34, 60, 22, C('#3a6aa8'), ink=C('#0e1a2a'), iw=DETAIL, em=0.6)   # car in the bay
    cv.ellipse(bx + 22, FB - 12, 6, 6, C('#1a1a20'), em=0.4)
    cv.ellipse(bx + 60, FB - 12, 6, 6, C('#1a1a20'), em=0.4)
    cv.ellipse(bx + 80, FB - 30, 3, 3.4, C('#7a4a3a'), em=1.0)
    cv.fill_poly([(bx + 74, FB), (bx + 76, FB - 26), (bx + 86, FB - 26), (bx + 88, FB)], C('#2a4a7a'), em=1.0)
    R.glow(bx + 50, FB - 50, 70, '#ffc070', 0.35, 'none')
    light_pool(R, bx + 50, FB + 10, 60, 12, '#ffc070', a=0.22)
    R.light(bx + 50, FB + 16, 80, 34, '#ffb060', 0.2)
    shop_door(R, dx, 22, 56, '#2a5a4a')
    cv.rect(dx - 14, FB - 70, 28, 10, C('#f4f0e8'), ink=C('#2a2430'), iw=DETAIL)
    cv.text('OFFICE', 'cond', 4, dx, FB - 65, C('#2a2430'), 'mm')
    # tyre stack, oil sign, gas pump
    cv.rect(x0 + w / 2 - 50, FB - 46, 18, 20, C('#f0d040'), ink=C('#2a2010'), iw=DETAIL)
    cv.text('OIL', 'sign', 5, x0 + w / 2 - 41, FB - 36, C('#c83a2a'), 'mm')
    poster(cv, x0 + 124, FB - 50, 12, 16, seed=7011, kind='missing')
    tag(cv, x0 + 30, FB - 92, 'MARA', C('#f4f0e8'), size=6, seed=5, a=0.5)


@facade("rec_center")
def f_rec_center(R, x0, w, f):
    cv = R.cv
    top = 56
    wall(cv, 'brick', x0, top, w, FB - top, '#a85a3e', seed=801)
    cornice(cv, x0, top, w, C('#e0d4bc'), h=6)
    parapet(cv, x0 - 1, top - 6, w + 2, C('#6a3a2a'), h=6)
    sun_rim(R, x0, top - 6, FB - 40, a=0.45)
    for k in range(5):
        wx = x0 + 20 + k * (w - 56) / 4
        window(cv, wx, top + 14, 16, 30, lit=k % 2 == 0, seed=800 + k, frame='#e0d4bc', kind='grid')
    sm = M(C('#2a3a6a'))
    cv.rect(x0 + 20, top + 52, w - 40, 22, sm.b, ink=sm.i, iw=MAJOR)
    painted_text(cv, f.get('sign', "BENNY'S REC CENTER"), x0 + w / 2, top + 63.5, 10, C('#f8d860'), tracking=0.5)
    # boxing glove emblem
    gx = x0 + 34
    cv.ellipse(gx, top + 63, 6, 6.5, C('#c8302a'), ink=C('#3a0a0a'), iw=DETAIL)
    cv.rect(gx - 4, top + 68, 8, 4, C('#f4f0e8'), ink=C('#3a0a0a'), iw=DETAIL)
    dx = door_x(R, x0, w)
    cv.rect(dx - 22, FB - 72, 44, 72, C('#e0d4bc'), ink=C('#3a2a26'), iw=MAJOR)
    door(cv, dx - 14, FB - 6, 28, 56, C('#2a3a6a'), lit=True, seed=81, frame='#5a4a40')
    cv.rect(dx - 0.4, FB - 62, 0.8, 56, C('#141020'))
    kit.stoop(cv, dx - 18, 36, FB, steps=2)
    lantern(R, dx - 26, FB - 60, '#f8d080', 2.6)
    lantern(R, dx + 26, FB - 60, '#f8d080', 2.6)
    R.glow(dx, FB - 40, 40, '#ffd090', 0.3, 'none')
    for k, wx in enumerate((x0 + 30, x0 + 80, x0 + w - 110, x0 + w - 60)):
        window(cv, wx, FB - 58, 22, 34, lit=True, seed=820 + k, frame='#e0d4bc', interior='person', curtains=False)
    poster(cv, x0 + 130, FB - 44, 16, 22, seed=8101, kind='boxing')
    poster(cv, x0 + w - 140, FB - 40, 12, 16, seed=8102, kind='missing')
    cv.rect(x0 + w / 2 + 40, FB - 50, 30, 18, C('#f4f0e8'), ink=C('#2a2430'), iw=DETAIL)
    cv.text('YOUTH', 'cond', 3.6, x0 + w / 2 + 55, FB - 45, C('#c8302a'), 'mm')
    cv.text('BOXING 6PM', 'cond', 3.2, x0 + w / 2 + 55, FB - 39, C('#2a2430'), 'mm')
    light_pool(R, dx, FB + 8, 40, 10, '#ffd090', a=0.2)
    R.light(dx, FB + 14, 60, 30, '#ffc070', 0.16)


@facade("tunnel_arch")
def f_tunnel_arch(R, x0, w, f):
    cv = R.cv
    # rail embankment wall with an arched tunnel mouth at the door/exit
    concrete_panel(cv, x0, 70, w, FB - 70, C('#8a8274'), seed=901, panel=36)
    cv.rect(x0, 64, w, 7, C('#a09888'), ink=C('#2a2430'), iw=MAJOR)
    gm = M(C('#3e4a5a'))
    cv.rect(x0 - 4, 40, w + 8, 24, gm.b, ink=gm.i, iw=MAJOR)
    for xx in np.arange(x0, x0 + w, 14):
        cv.rect(xx, 40, 1.4, 24, gm.l)
    cv.rect(x0 - 4, 40, w + 8, 1, C('#ffc890'), a=0.6)
    dx = door_x(R, x0, w, x0 + w / 2)
    aw, ah = 84, 110
    pts = [(dx - aw / 2, FB)] + [(dx + math.cos(a) * aw / 2, FB - ah + aw / 2 - math.sin(a) * aw / 2)
                                 for a in np.linspace(math.pi, 0, 30)] + [(dx + aw / 2, FB)]
    cv.fill_poly([(px + (3 if px > dx else -3), py - 3) for px, py in pts], C('#b0a490'), ink=C('#2a2430'), iw=MAJOR)
    cv.fill_poly(pts, C('#120e18'))
    mk = cv.poly_mask(pts)
    cv.vgrad(dx - aw / 2, FB - ah, aw, ah, [C('#1e1828'), C('#0e0a14')], mk=mk)
    cv.radial(dx, FB - 20, 20, 30, C('#ffd890'), a=0.25, mode='add')     # far end light
    cv.rect(dx - 30, FB - ah - 14, 60, 12, C('#2a2a30'), ink=C('#0e0a10'), iw=MAJOR)
    painted_text(cv, f.get('sign', 'RAIL TUNNEL'), dx, FB - ah - 7.5, 6, C('#f4e8c0'), shadow=False)
    # rails disappearing into the tunnel
    for off in (-12, 12):
        cv.line([(dx + off * 1.6, FB), (dx + off * 0.6, FB - 30)], 0.8, C('#8a8e9a'), a=0.6)
    tag(cv, x0 + 12, FB - 40, 'DOGS', C('#e84a3a'), size=7, seed=91)
    R.drawn_doors.add('tunnel')
    R.light(dx, FB + 6, 60, 24, '#1a1430', -0.10)
    R.ambient.append({"type": "drip", "x": float(dx - 20), "y": float(FB - ah + 10), "rate": 0.4})
