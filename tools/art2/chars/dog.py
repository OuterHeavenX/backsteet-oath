"""Biscuit (scruffy tan terrier mix, red collar) -- v2 quadruped renderer.

Same ink + cel pipeline as the humanoids (raster.py). Facing +x, anchor =
ground point under the body centre, world units. Anims follow the v1 keys
(idle, walk, sit, bark) plus a `run` alias.
"""
import math

from raster import Canvas, Mat, ellipse_pts, seg_quad, ribbon, catmull, rot
from rig import ik2, lerp, add, sub, mul, norm, perp

TAN = Mat((206, 162, 110), (156, 108, 70), (236, 204, 156))
SADDLE = Mat((132, 86, 52), (92, 56, 36), (168, 120, 80))
TAN_FAR = Mat((170, 126, 84), (122, 84, 56), (196, 158, 110))
COLLAR = Mat((204, 52, 52), (130, 28, 40), (240, 120, 110))
TAG = Mat((240, 200, 80), (170, 120, 40), (255, 240, 170))
NOSE = (36, 24, 30)
EYE = (30, 20, 26)
MOUTH = (96, 30, 44)
TONGUE = (220, 96, 110)


def pose(body_y=0.0, body_tilt=0.0, head=(0.0, 0.0), head_tilt=0.0, jaw=0.0, tail=0.0, ear=0.0,
         paws=None, sit=False, blink=False):
    return dict(body_y=body_y, body_tilt=body_tilt, head=head, head_tilt=head_tilt, jaw=jaw, tail=tail, ear=ear,
                paws=paws or {'fn': (4.6, 0.0), 'ff': (5.6, 0.0), 'bn': (-5.0, 0.0), 'bf': (-4.0, 0.0)},
                sit=sit, blink=blink)


def anims():
    A = {}
    fr = []
    for i in range(4):
        t = 2 * math.pi * i / 4
        fr.append(pose(body_y=0.2 * math.sin(t), tail=28 * math.sin(t * 2), ear=4 * (i == 3), blink=(i == 2)))
    A['idle'] = dict(frames=fr, fps=6, loop=True)
    # walk: diagonal gait, distance planted paws
    n, stride, beta = 8, 20.0, 0.6
    half = beta * stride / 2
    fr = []
    for i in range(n):
        ph = i / n
        paws = {}
        for key, base_x, off in (('fn', 4.8, 0.0), ('bf', -4.2, 0.0), ('ff', 5.6, 0.5), ('bn', -5.0, 0.5)):
            phi = (ph + off) % 1.0
            if phi < beta:
                x, y = half - phi * stride, 0.0
            else:
                u = (phi - beta) / (1 - beta)
                x = -half + 2 * half * (u * u * (3 - 2 * u))
                y = -1.7 * math.sin(math.pi * u)
            paws[key] = (base_x + x, y)
        fr.append(pose(body_y=-0.3 * math.cos(4 * math.pi * ph), head=(0.0, 0.3 * math.cos(4 * math.pi * ph)),
                       tail=18 * math.sin(2 * math.pi * ph), paws=paws))
    A['walk'] = dict(frames=fr, fps=12, loop=True, stride=stride)
    A['sit'] = dict(frames=[pose(sit=True, tail=10, head_tilt=-4), pose(sit=True, tail=-14, head_tilt=-6, ear=5)],
                    fps=3, loop=True)
    A['bark'] = dict(frames=[pose(body_y=0.4, head=(0.4, 0.8), head_tilt=8, tail=20),
                             pose(body_y=-0.4, head=(-0.3, -1.0), head_tilt=-16, jaw=34, ear=10, tail=-10),
                             pose(body_y=-0.1, head=(0.0, -0.4), head_tilt=-8, jaw=14, ear=4, tail=14)],
                     fps=8, loop=False, contact=1)
    return A


def render(p, den=2.0):
    cv = Canvas(-16.0, -30.0, 20.0, 3.0, den=den)
    by = p['body_y']
    tilt = math.radians(p['body_tilt'])
    sit = p['sit']
    # body frame
    chest = (4.6, -11.6 + by)
    rump = (-5.4, -12.2 + by)
    if sit:
        chest = (4.8, -13.6)
        rump = (-3.6, -4.8)
    # ---- far legs (darker), tail, far ear behind
    _tail(cv, p, rump, sit)
    _legs(cv, p, chest, rump, far=True)
    # ---- body
    g = cv.group(occlude=0.25)
    if sit:
        body = catmull([(chest[0] + 3.2, chest[1] - 1.0), (chest[0] + 2.0, chest[1] + 4.0), (rump[0] + 4.0, rump[1] + 2.6),
                        (rump[0] - 3.6, rump[1] + 2.4), (rump[0] - 3.8, rump[1] - 2.4), (chest[0] - 2.6, chest[1] - 3.0)],
                       True, 5)
    else:
        body = catmull([(chest[0] + 3.4, chest[1] - 0.6), (chest[0] + 2.0, chest[1] + 3.6), (0.0, -8.6 + by),
                        (rump[0] - 1.0, rump[1] + 3.0), (rump[0] - 3.4, rump[1] - 0.4), (rump[0] - 1.2, rump[1] - 3.4),
                        (0.0, -15.6 + by), (chest[0] - 0.6, chest[1] - 3.8)], True, 5)
    m = g.mask(polys=[body])
    g.fill(m, TAN, shade=1.4, hi=0.5)
    sad = ellipse_pts(-1.0 if not sit else -0.6, -14.0 + by if not sit else -11.4, 5.6, 2.4,
                      0.0 if not sit else -1.1, n=30)
    g.fill(g.mask(polys=[sad]) * (g.img_a > 0.5), SADDLE, shade=0.5, hi=0.25)
    # scruffy chest tufts
    for k in range(3):
        bx, byy = chest[0] + 2.6 - k * 0.6, chest[1] + 1.6 + k * 1.1
        g.fill(g.mask(polys=[[(bx, byy - 0.6), (bx + 1.2, byy + 0.2), (bx - 0.1, byy + 0.6)]]), TAN, shade=0.2, hi=0.0)
    g.line([(chest[0] - 1.0, chest[1] + 2.2), (chest[0] + 0.4, chest[1] + 3.2)], 0.7, TAN.shadow, 0.8)
    g.commit()
    _legs(cv, p, chest, rump, far=False)
    _head(cv, p, chest, sit)
    cv.finish()
    return cv


def _tail(cv, p, rump, sit):
    g = cv.group()
    base = (rump[0] - 2.8, rump[1] - 1.6) if not sit else (rump[0] - 3.0, rump[1] + 1.4)
    ang = math.radians(-115 + p['tail']) if not sit else math.radians(178 + p['tail'] * 0.6)
    pts = [base]
    for k in range(1, 6):
        t = k / 5.0
        a = ang + 0.5 * t * (1 if not sit else -0.3)
        prev = pts[-1]
        pts.append((prev[0] + math.cos(a) * 1.25, prev[1] + math.sin(a) * 1.25))
    poly = ribbon(pts, [1.1, 1.05, 0.95, 0.8, 0.6, 0.35])
    g.fill(g.mask(polys=[poly]), TAN, shade=0.5, hi=0.2)
    g.commit()


def _legs(cv, p, chest, rump, far):
    mat = TAN_FAR if far else TAN
    keys = ('ff', 'bf') if far else ('fn', 'bn')
    for key in keys:
        g = cv.group()
        paw = p['paws'][key]
        front = key[0] == 'f'
        if p['sit']:
            if front:
                top = (chest[0] - 0.2 + (0.8 if far else 0.0), chest[1] + 2.0)
                paw = (chest[0] + 1.2 + (0.9 if far else 0.0), 0.0)
                knee, end = ik2(top, (paw[0], paw[1] - 0.7), 5.4, 5.6, 'back')
                polys = [seg_quad(top, knee, 1.6, 1.2), seg_quad(knee, end, 1.2, 1.0)]
            else:
                c = (rump[0] + 1.6 + (0.8 if far else 0.0), rump[1] + 0.4)
                polys = [ellipse_pts(c[0], c[1], 3.0, 2.2, -0.3, n=24)]
                end = (rump[0] + 4.6 + (0.6 if far else 0.0), -0.7)
                polys.append(seg_quad(c, end, 1.4, 1.0))
            m = g.mask(polys=polys, circles=[(end[0] + 0.5, end[1] + 0.1, 1.0)])
            g.fill(m, mat, shade=0.6, hi=0.25)
            g.commit()
            continue
        if front:
            top = (chest[0] - 0.4 + (0.7 if far else 0.0), chest[1] + 1.6)
            knee, end = ik2(top, (paw[0], paw[1] - 0.7), 5.2, 5.4, 'back')
            polys = [seg_quad(top, knee, 1.7, 1.25), seg_quad(knee, end, 1.25, 1.0)]
            circ = [(knee[0], knee[1], 1.25)]
        else:
            top = (rump[0] + 0.4 + (0.7 if far else 0.0), rump[1] + 0.6)
            stifle, end = ik2(top, (paw[0], paw[1] - 0.7), 5.6, 6.2, 'fwd')
            hock = add(lerp(stifle, end, 0.5), (-1.1, 0.0))
            polys = [seg_quad(top, stifle, 2.4, 1.5), seg_quad(stifle, hock, 1.5, 1.0), seg_quad(hock, end, 1.0, 0.95)]
            circ = [(top[0], top[1], 2.4), (stifle[0], stifle[1], 1.5), (hock[0], hock[1], 1.0)]
        m = g.mask(polys=polys, circles=circ + [(end[0] + 0.5, end[1] + 0.1, 1.05)])
        g.fill(m, mat, shade=0.55, hi=0.25)
        g.line([(end[0] + 0.6, end[1] - 0.2), (end[0] + 0.7, end[1] + 0.8)], 0.6, mat.shadow, 0.8)
        g.commit()


def _head(cv, p, chest, sit):
    hx, hy = chest[0] + 4.4 + p['head'][0], chest[1] - 6.6 + p['head'][1]
    if sit:
        hx, hy = chest[0] + 3.6 + p['head'][0], chest[1] - 6.6 + p['head'][1]
    ang = math.radians(p['head_tilt'])
    c = (hx, hy)

    HS = 1.22

    def H(x, y):
        return add(c, rot((x * HS, y * HS), ang))
    # neck
    g = cv.group()
    g.fill(g.mask(polys=[seg_quad((chest[0] + 0.6, chest[1] - 1.6), H(-1.0, 1.6), 2.9, 2.4)]), TAN, shade=0.7, hi=0.3)
    # collar
    cm = g.mask(polys=[seg_quad(lerp((chest[0] + 0.6, chest[1] - 1.6), H(-1.0, 1.6), 0.45),
                                lerp((chest[0] + 0.6, chest[1] - 1.6), H(-1.0, 1.6), 0.7), 3.1, 2.9)])
    g.fill(cm, COLLAR, shade=0.4, hi=0.2)
    tg = lerp((chest[0] + 0.6, chest[1] - 1.6), H(-1.0, 1.6), 0.58)
    g.fill(g.mask(circles=[(tg[0] + 2.4, tg[1] + 1.4, 0.7)]), TAG, shade=0.2, hi=0.2)
    g.commit()
    g = cv.group(occlude=0.3)
    skull = ellipse_pts(c[0], c[1], 3.7 * HS, 3.4 * HS, ang, n=36)
    snout_top = [H(1.4, -1.4), H(4.9, -0.6), H(5.5, 0.4), H(4.9, 1.0), H(1.6, 1.2)]
    jaw_ang = math.radians(p['jaw'])
    jaw = [H(1.2, 0.8)] + [add(H(1.6, 0.9), rot(sub(H(x, y), H(1.6, 0.9)), jaw_ang)) for (x, y) in
                           ((4.6, 1.0), (4.4, 2.0), (1.8, 2.2))]
    m = g.mask(polys=[skull, catmull(snout_top, True, 3), jaw])
    g.fill(m, TAN, shade=0.9, hi=0.35)
    if p['jaw'] > 2:
        mouth = [H(1.8, 1.0), H(5.0, 0.9)] + [add(H(1.6, 0.9), rot(sub(H(x, y), H(1.6, 0.9)), jaw_ang)) for (x, y) in
                                              ((4.4, 1.1), (2.0, 1.4))]
        mm = g.mask(polys=[mouth])
        g.paint_flat(mm, MOUTH)
        g.paint_flat(mm * g.mask(polys=[ellipse_pts(*add(H(3.2, 1.6), (0, 0.3)), 1.2, 0.6, ang, n=14)]), TONGUE)
    else:
        g.line([H(2.2, 1.2), H(4.4, 1.0)], 0.7, MOUTH, 0.9)
    # nose, eye, brow tuft, cheek fur
    g.fill(g.mask(polys=[ellipse_pts(*H(5.2, -0.2), 0.75, 0.6, ang, n=14)]), Mat(NOSE, (10, 6, 10), (120, 110, 130)),
           shade=0.0, hi=0.2)
    e = H(1.9, -1.0)
    if p['blink']:
        g.line([add(e, (-0.6, 0.1)), add(e, (0.6, 0.1))], 0.8, EYE)
    else:
        g.paint_flat(g.mask(polys=[ellipse_pts(e[0], e[1], 0.62, 0.72, ang, n=14)]), EYE)
        g.paint_flat(g.mask(circles=[(e[0] + 0.22, e[1] - 0.25, 0.2)]), (255, 255, 255))
    g.line([H(1.1, -1.9), H(2.0, -2.3), H(2.7, -1.8)], 0.8, SADDLE.shadow, 0.9)
    for k in range(3):
        bx, byy = H(4.0 - k * 0.9, 2.2 + (p['jaw'] / 30.0))
        g.line([(bx, byy - 0.3), (bx + 0.3, byy + 0.5)], 0.6, TAN.shadow, 0.8)
    g.commit()
    # ear (folded, darker), lifts on bark
    g = cv.group()
    er = math.radians(-p['ear'])
    base = H(-0.6, -2.8)
    ear = [base, add(base, rot((3.2, -0.7), ang + er)), add(base, rot((3.0, 2.3), ang + er)), add(base, rot((0.7, 3.0), ang + er))]
    g.fill(g.mask(polys=[catmull(ear, True, 3)]), SADDLE, shade=0.4, hi=0.2)
    g.commit()
