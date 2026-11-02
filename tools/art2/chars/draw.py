"""Character renderer (v2): body, clothing, head, face, hair, accessories.

All geometry in world units around the anchor; head features in head-local
units of R (head radius), facing +x, y down, rotated by the solved head angle.
"""
import importlib.util
import math
import os

import numpy as np

from raster import Mat, lerp_c, hexc, ellipse_pts, catmull, seg_quad, ribbon, rot, shade_of, light_of
from rig import add, sub, mul, norm, perp, length, lerp

HERE = os.path.dirname(os.path.abspath(__file__))
V1_PATH = os.path.join(HERE, '..', '..', 'art', 'gen_characters.py')
_spec = importlib.util.spec_from_file_location('gen_characters_v1', V1_PATH)
V1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V1)

EYE_W = (246, 242, 238)
TEETH = (248, 244, 234)
MOUTH_DARK = (92, 24, 40)
TONGUE = (206, 80, 90)
METAL = Mat((196, 200, 212), (120, 124, 146), (250, 250, 255))
GOLD = Mat((240, 196, 80), (170, 120, 40), (255, 240, 170))


# ============================================================================= materials

def _m(t, shadow_mix=0.55):
    """v1 material tuple (base, shadow, hi, deep) -> Mat with hue-shifted shading."""
    base, sh = t[0], t[1]
    my_sh = shade_of(base)
    s = lerp_c(sh, my_sh, shadow_mix)
    return Mat(base, s, light_of(base))


def cloth(name):
    if name is None:
        return None
    if name in ('skin', 'pins'):
        return None
    if name in V1.C:
        return _m(V1.C[name])
    if isinstance(name, str) and name.startswith('#'):
        return Mat(hexc(name))
    return _m(V1.cm(name))


def skin_mat(spec):
    b, s, h, d = V1.SKIN[spec['skin']]
    sh = lerp_c(s, shade_of(b, 0.8), 0.35)
    return Mat(b, sh, light_of(b, 0.8))


def hair_mat(spec, which=1):
    t = V1.hair_mat(spec, which)
    base = t[0]
    sh = lerp_c(t[1], shade_of(base, 1.2), 0.5)
    li = lerp_c(t[2], light_of(base, 1.4), 0.5)
    return Mat(base, sh, li)


class Look:
    """Resolved materials / options for a character spec."""

    def __init__(self, spec):
        self.spec = spec
        self.skin = skin_mat(spec)
        self.hair = hair_mat(spec) if spec.get('hcol') else self.skin
        self.hair2 = hair_mat(spec, 2) if spec.get('hcol2') else None
        self.shirt = cloth(spec['shirt']) if spec.get('shirt') and not str(spec['shirt']).startswith('stripe') \
            and spec['shirt'] != 'hawaii' else cloth('white')
        self.shirt_pattern = spec.get('shirt') if str(spec.get('shirt')).startswith('stripe') or \
            spec.get('shirt') == 'hawaii' else None
        self.pants = cloth(spec.get('pants') or 'denim')
        self.shoe = cloth(spec.get('shoes') or 'black')
        self.sole = cloth(spec.get('sole')) if spec.get('sole') else None
        self.jacket = spec.get('jacket')
        self.jmat = cloth(self.jacket['color']) if self.jacket else None
        if self.jacket and self.jacket['color'] == 'leather':
            self.jmat = Mat((52, 44, 58), (28, 22, 36), (104, 96, 118))
            self.jmat.gloss = 1.0
        self.glove = cloth(spec['gloves']) if spec.get('gloves') else None
        self.wrist = cloth(spec['wrist']) if spec.get('wrist') else None
        self.band = cloth(spec['band']) if spec.get('band') else None
        self.dress = cloth(spec['dress']) if spec.get('dress') else None
        self.apron = cloth(spec['apron']) if spec.get('apron') else None
        self.overalls = cloth(spec['overalls']) if spec.get('overalls') else None
        self.guards = cloth(spec['guards']) if spec.get('guards') else None
        self.armband = cloth(spec['armband']) if spec.get('armband') else None
        self.legs2 = spec.get('legs2')
        self.sleeves = spec.get('sleeves', 'short')
        self.lashes = spec.get('lashes', False)
        eyecol = {'light': (70, 110, 168), 'tan': (86, 56, 36), 'medium': (72, 46, 30), 'deep': (58, 36, 24)}
        self.iris = eyecol.get(spec['skin'], (70, 46, 30))
        if spec.get('eyecol'):
            self.iris = hexc(spec['eyecol'])
        bc = self.hair.shadow if spec.get('hair') not in ('bald',) else self.skin.deep
        if spec.get('hcol') in ('platinum', 'white', 'gray', 'blonde'):
            bc = lerp_c(self.hair.shadow, (90, 70, 60), 0.45)
        self.brow = bc
        self.face = spec.get('face', 'neutral')


# ============================================================================= expressions

PERSONA = {
    # face: (brow angle deg (+ = inner end raised), brow lift, lid cut 0..1 angry, mouth neutral)
    'neutral': (0, 0.0, 0.0, 'line'), 'determined': (-10, 0.0, 0.15, 'firm'),
    'tough': (-16, 0.02, 0.28, 'frown'), 'cocky': (-6, 0.0, 0.2, 'smirk'),
    'kind': (12, 0.04, 0.0, 'smile'), 'cheerful': (6, 0.05, 0.0, 'smile'),
    'calm': (0, 0.0, 0.3, 'line'), 'stern': (-12, 0.0, 0.25, 'line'),
    'mean': (-22, 0.0, 0.42, 'frown'),
}


def expression(look, expr, blink=False):
    """-> dict(eye, lid, brow_ang, brow_lift, mouth, blush, sweat)."""
    ba, bl, lid, mouth = PERSONA.get(look.face, PERSONA['neutral'])
    e = dict(eye='open', lid=lid, brow_ang=ba, brow_lift=bl, mouth=mouth, blush=0.0, look=1.0)
    if expr in ('normal', 'neutral'):
        pass
    elif expr == 'fight':
        e.update(brow_ang=min(ba, -12) - 4, lid=max(lid, 0.22),
                 mouth='firm' if mouth not in ('smirk', 'frown') else mouth)
    elif expr == 'effort':
        e.update(brow_ang=-24, lid=0.45, mouth='grit', brow_lift=-0.03)
    elif expr == 'shout':
        e.update(brow_ang=-26, lid=0.4, mouth='shout', brow_lift=-0.02)
    elif expr == 'pain':
        e.update(eye='squeeze', brow_ang=22, mouth='grimace')
    elif expr == 'pain_open':
        e.update(eye='wide', brow_ang=24, brow_lift=0.06, mouth='O')
    elif expr == 'ko':
        e.update(eye='ko', brow_ang=16, mouth='slack')
    elif expr == 'dizzy':
        e.update(eye='swirl', brow_ang=14, mouth='wavy')
    elif expr == 'happy':
        e.update(eye='happy', brow_ang=10, brow_lift=0.05, mouth='grin_open', blush=0.3)
    elif expr == 'smile':
        e.update(mouth='smile', lid=0.0, brow_ang=max(ba, 4))
    elif expr == 'scared':
        e.update(eye='wide', brow_ang=28, brow_lift=0.08, mouth='wavy')
    elif expr == 'talk':
        e.update(mouth='open_small', lid=min(lid, 0.15))
    elif expr == 'talk_b':
        e.update(mouth='talk_wide', lid=min(lid, 0.15), brow_lift=bl + 0.03)
    elif expr == 'angry':
        e.update(brow_ang=-28, lid=0.45, mouth='shout_small')
    elif expr == 'surprised':
        e.update(eye='wide', brow_ang=8, brow_lift=0.1, mouth='O', lid=0.0)
    elif expr == 'sad':
        e.update(eye='open', lid=0.0, sad=0.4, brow_ang=24, brow_lift=0.03, mouth='frown')
    elif expr == 'grin':
        e.update(mouth='grin_open', lid=0.1)
    if blink and e['eye'] == 'open':
        e['eye'] = 'closed'
    return e


# ============================================================================= renderer

class Frame:
    """Render one pose of one character onto a Canvas."""

    def __init__(self, cv, look, s, sec=None, portrait=False):
        self.cv = cv
        self.L = look
        self.s = s
        self.b = s.b
        self.sec = sec or {}
        self.portrait = portrait
        self.R = s.b['R']
        self.portrait_expr_override = {}

    # ------------------------------------------------------------------ head-local transform
    def H(self, p):
        """head-local (units of R) -> world."""
        R = self.R
        ang = math.radians(self.s.head_ang)
        x, y = p[0] * R, p[1] * R
        ca, sa = math.cos(ang), math.sin(ang)
        c = self.s.head_c
        return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)

    def HP(self, pts):
        return [self.H(p) for p in pts]

    def H_ell(self, cx, cy, rx, ry, ang=0.0, n=40):
        pts = ellipse_pts(cx, cy, rx, ry, math.radians(ang), n=n)
        return self.HP(pts)

    def drag(self, key='hair', k=1.0):
        d = self.sec.get(key, (0.0, 0.0))
        return (d[0] * k, d[1] * k)

    def drag_local(self, key='hair', k=1.0):
        """Drag vector in head-local units (rotated into head frame, / R)."""
        d = self.drag(key, k)
        ang = -math.radians(self.s.head_ang)
        x, y = rot(d, ang)
        return (x / self.R, y / self.R)

    # ================================================================== full figure
    def render(self):
        s, L = self.s, self.L
        p = s.pose
        self.back_hair()
        self.tails(behind=True)
        if not p['far_arm_front']:
            self.arm('f')
        if p.get('near_arm_under'):
            self.arm('n')
        self.leg('f')
        if L.dress is not None:
            self.skirt(back=True)
        self.lower_body()
        if L.dress is not None:
            self.skirt(back=False)
        self.neck()
        self.torso()
        self.outerwear()
        self.extras_front()
        if p['far_arm_front']:
            self.arm('f')
        if p['near_arm_back']:
            self.arm('n')
        self.head()
        self.tails(behind=False)
        if not p['near_arm_back'] and not p.get('near_arm_under'):
            self.arm('n')
        self.held_extras()

    # ================================================================== legs
    def leg_geom(self, side):
        s, b = self.s, self.b
        hj = s.hj_n if side == 'n' else s.hj_f
        kn = s.knee_n if side == 'n' else s.knee_f
        an = s.ank_n if side == 'n' else s.ank_f
        lw = b['limb']
        return hj, kn, an, lw

    def leg(self, side):
        L = self.L
        cv = self.cv
        hj, kn, an, lw = self.leg_geom(side)
        g = cv.group(occlude=0.0)
        skin_leg = L.legs2 == 'skin' or (L.dress is not None and L.legs2 != 'tights')
        pst = L.spec.get('pstyle', 'long')
        rh, rk, ra = 2.85 * lw, 2.1 * lw, 1.55 * lw
        if pst in ('bike',):
            rh, rk, ra = 2.5 * lw, 1.85 * lw, 1.35 * lw
        polys = [seg_quad(hj, kn, rh, rk), seg_quad(kn, an, rk, ra)]
        circles = [(hj[0], hj[1], rh), (kn[0], kn[1], rk)]
        m = g.mask(polys=polys, circles=circles)
        far = side == 'f'
        if skin_leg:
            sk = self.L.skin
            g.fill(g.mask(polys=[seg_quad(hj, kn, rh * 0.82, rk * 0.8), seg_quad(kn, an, rk * 0.8, ra * 0.8)],
                          circles=[(kn[0], kn[1], rk * 0.8), (hj[0], hj[1], rh * 0.82)]),
                   self._far(sk, far), shade=0.9, hi=0.3)
        else:
            pm = self._far(L.pants if L.overalls is None else L.overalls, far)
            g.fill(m, pm, shade=1.1, hi=0.35)
            if pst in ('shorts', 'bike'):
                # skin below the hem
                cut = lerp(hj, kn, 0.78 if pst == 'shorts' else 0.9)
                lower = g.mask(polys=[seg_quad(cut, kn, rk * 0.86, rk * 0.8), seg_quad(kn, an, rk * 0.8, ra * 0.82)],
                               circles=[(kn[0], kn[1], rk * 0.8)])
                if pst == 'bike':
                    l2 = cloth(L.legs2) if L.legs2 and L.legs2 != 'skin' else None
                    g.fill(lower, self._far(l2 or L.skin, far), shade=0.9, hi=0.3)
                else:
                    g.fill(lower, self._far(L.skin, far), shade=0.9, hi=0.3)
            else:
                self._pants_detail(g, hj, kn, an, rh, rk, ra, far, pst)
        self.shoe(g, side)
        g.commit()

    def _far(self, m, far):
        if not far:
            return m
        return Mat(lerp_c(m.base, m.shadow, 0.38), lerp_c(m.shadow, (30, 20, 44), 0.18), lerp_c(m.light, m.base, 0.5))

    def _pants_detail(self, g, hj, kn, an, rh, rk, ra, far, pst):
        L = self.L
        pm = L.pants
        # knee crease when bent
        a1 = norm(sub(kn, hj))
        a2 = norm(sub(an, kn))
        bend = a1[0] * a2[0] + a1[1] * a2[1]
        n1 = perp(a1)
        if bend < 0.93:
            for i, k in enumerate((0.55, 0.0, -0.5)):
                c = add(kn, mul(n1, k * rk * 0.6))
                p0 = add(c, mul(a1, -rk * 0.8))
                p1 = add(c, mul(a2, rk * 0.5))
                g.line([p0, kn if i == 1 else c, p1], 0.9, pm.shadow, 0.9)
        # outer seam / shin highlight
        mid = lerp(kn, an, 0.5)
        n2 = perp(a2)
        g.line([add(lerp(kn, an, 0.15), mul(n2, -rk * 0.45)), add(lerp(kn, an, 0.85), mul(n2, -ra * 0.5))],
               0.8, pm.light, 0.55)
        if pst == 'ripped':
            # knee tear (skin peeking) + thread lines
            tc = add(kn, mul(a1, -rk * 0.15))
            pts = [add(tc, rot((rk * 0.55 * math.cos(t), rk * 0.32 * math.sin(t)), math.atan2(a1[1], a1[0])))
                   for t in np.linspace(0, 2 * math.pi, 14)]
            sk = self._far(L.skin, far)
            m = g.mask(polys=[pts]) * (g.img_a > 0.5)
            g.paint_flat(m, sk.shadow)
            g.line(pts[2:7], 0.8, pm.light, 0.9)
            g.line(pts[9:13], 0.8, lerp_c(pm.light, (255, 255, 255), 0.4), 0.9)
            tc2 = lerp(hj, kn, 0.45)
            g.line([add(tc2, mul(n1, rh * 0.2)), add(tc2, mul(n1, -rh * 0.25))], 0.9, pm.light, 0.8)
        if pst == 'track':
            g.line([add(hj, mul(n1, -rh * 0.75)), add(kn, mul(n1, -rk * 0.82)), add(an, mul(n2, -ra * 0.9))],
                   1.2, (240, 240, 236), 0.95)
        # hem at the ankle
        h0 = add(an, mul(n2, ra * 1.05))
        h1 = add(an, mul(n2, -ra * 1.05))
        g.line([add(h0, mul(a2, -0.5)), add(h1, mul(a2, -0.5))], 0.9, pm.shadow, 0.9)

    def shoe(self, g, side):
        L, b, s = self.L, self.b, self.s
        an = s.ank_n if side == 'n' else s.ank_f
        toe = s.toe_n if side == 'n' else s.toe_f
        far = side == 'f'
        fs = b['foot']
        st = L.spec.get('sstyle', 'sneaker')
        ang = math.radians(toe)

        def T(x, y):
            x, y = x * fs, y * fs
            ca, sa = math.cos(ang), math.sin(ang)
            return (an[0] + x * ca - y * sa, an[1] + x * sa + y * ca)
        if st == 'boot':
            body = [(-1.7, -2.6), (-1.8, 0.4), (-1.6, 1.55), (3.5, 1.55), (4.5, 1.0), (4.4, 0.1),
                    (3.0, -0.5), (1.2, -1.2), (0.9, -2.7)]
        elif st == 'rubber':
            body = [(-1.7, -5.5), (-1.8, 0.4), (-1.6, 1.55), (3.4, 1.55), (4.4, 0.9), (4.1, 0.0),
                    (2.6, -0.6), (1.4, -1.6), (1.4, -5.4)]
        elif st == 'dress':
            body = [(-1.4, -0.9), (-1.5, 0.6), (-1.3, 1.5), (3.6, 1.5), (4.5, 1.1), (4.1, 0.3),
                    (2.4, -0.4), (0.8, -1.1)]
        elif st == 'hightop':
            body = [(-1.6, -2.4), (-1.7, 0.5), (-1.5, 1.55), (3.5, 1.55), (4.5, 0.95), (4.1, -0.1),
                    (2.6, -0.7), (1.0, -1.4), (0.8, -2.5)]
        else:
            body = [(-1.5, -0.9), (-1.6, 0.6), (-1.4, 1.55), (3.5, 1.55), (4.5, 1.0), (4.2, 0.0),
                    (2.7, -0.7), (0.9, -1.5), (-0.8, -1.5)]
        pts = [T(*p) for p in catmull(body, closed=True, steps=4)]
        m = g.mask(polys=[pts])
        sm = self._far(L.shoe, far)
        g.fill(m, sm, shade=0.6, hi=0.3)
        # sole
        sole = L.sole or (cloth('lightgray') if st in ('sneaker', 'hightop') else None)
        sole_pts = [T(-1.8, 0.85), T(4.7, 0.85), T(4.7, 2.0), T(-1.8, 2.0)]
        sm2 = g.mask(polys=[sole_pts]) * m
        if sole is not None:
            g.fill(sm2, self._far(sole, far), shade=0.0, hi=0.0)
        else:
            g.paint_flat(sm2, lerp_c(sm.shadow, (20, 14, 24), 0.4))
        if not far:
            if st in ('sneaker', 'hightop'):
                g.line([T(0.6, -1.0), T(1.3, -0.55)], 0.8, sm.light, 0.9)
                g.line([T(1.4, -0.75), T(2.0, -0.35)], 0.8, sm.light, 0.9)
                stripe = (240, 238, 232) if L.spec.get('shoes') != 'white' else (200, 60, 60)
                g.line([T(-0.6, 0.3), T(1.2, 0.1), T(2.6, 0.55)], 0.9, stripe, 0.8)
            elif st == 'boot':
                g.line([T(0.4, -2.2), T(1.2, -2.0)], 0.8, sm.light, 0.8)
                g.line([T(0.6, -1.3), T(1.6, -0.9)], 0.8, sm.light, 0.8)
                g.dot(*T(3.2, 0.2), 0.25 * fs, sm.light, 0.8, clip_to_group=True)

    # ================================================================== torso
    def torso_points(self, expand=0.0, hem_drop=0.0):
        s, b = self.s, self.b
        up, fwd, pup, pfwd = s.up, s.fwd, s.pup, s.pfwd
        N, Hc = s.neck_base, s.hip
        t = s.twist
        w = b['w']
        ch = b['chest'] * (1 + 0.08 * t) + expand
        bk = b['back'] * (1 + 0.05 * t) + expand
        wa = b['waist'] + expand
        hp = b['hip'] + expand
        bel = b['belly']
        sh_c = add(N, mul(up, -1.5))
        pts = [
            add(add(N, mul(fwd, 1.1 * w + expand * 0.6)), mul(up, 0.3)),              # neck front
            add(add(sh_c, mul(fwd, ch * 0.78)), mul(up, 1.0)),
            add(add(N, mul(up, -4.2)), mul(fwd, ch)),                                 # chest front
            add(add(Hc, mul(up, 5.2)), mul(fwd, wa + bel)),                           # waist / belly
            add(add(Hc, mul(pup, 1.4)), mul(pfwd, hp * 0.98 + bel * 0.4)),            # hip front
            add(add(Hc, mul(pup, -1.6 - hem_drop)), mul(pfwd, hp * 0.82)),
            add(add(Hc, mul(pup, -2.4 - hem_drop)), mul(pfwd, 0.3)),                 # crotch
            add(add(Hc, mul(pup, -1.8 - hem_drop)), mul(pfwd, -hp * 0.95)),
            add(add(Hc, mul(pup, 0.8)), mul(pfwd, -hp * 1.02)),                       # seat
            add(add(Hc, mul(up, 5.6)), mul(fwd, -wa * 1.02)),                         # small of back
            add(add(N, mul(up, -3.6)), mul(fwd, -bk)),                                # shoulder blade
            add(add(sh_c, mul(fwd, -bk * 0.82)), mul(up, 1.1)),
            add(add(N, mul(fwd, -1.3 * w - expand * 0.6)), mul(up, 0.2)),             # neck back
        ]
        return catmull(pts, closed=True, steps=5)

    def halfplane(self, origin, normal_up, big=80):
        """Polygon covering the side of the line through origin that normal_up points to."""
        d = perp(normal_up)
        a = add(origin, mul(d, big))
        c = add(origin, mul(d, -big))
        return [a, c, add(c, mul(normal_up, big)), add(a, mul(normal_up, big))]

    def lower_body(self):
        """Pelvis (pants) + near leg as ONE group (no seam at the hip)."""
        L, s = self.L, self.s
        cv = self.cv
        g = cv.group(occlude=0.0)
        tp = self.torso_points()
        belt_o = add(s.hip, mul(s.up, 2.6))
        torso_m = g.mask(polys=[tp])
        below = g.mask(polys=[self.halfplane(belt_o, mul(s.up, -1))])
        pel = torso_m * below
        hj, kn, an, lw = self.leg_geom('n')
        skin_leg = L.legs2 == 'skin' or (L.dress is not None and L.legs2 != 'tights')
        pm = L.pants if L.overalls is None else L.overalls
        if L.dress is not None:
            pm = L.dress
        g.fill(pel, pm, shade=1.1, hi=0.35)
        # belt
        if L.dress is None and L.overalls is None:
            bo = add(s.hip, mul(s.up, 2.2))
            band = g.mask(polys=[self.halfplane(add(bo, mul(s.up, -0.9)), s.up)]) * \
                g.mask(polys=[self.halfplane(add(bo, mul(s.up, 0.5)), mul(s.up, -1))]) * pel
            bm = Mat((46, 34, 36), (26, 18, 26), (96, 80, 80))
            g.fill(band, bm, shade=0.4, hi=0.0)
            buckle = add(add(bo, mul(s.fwd, self.b['waist'] * 0.75)), mul(s.up, -0.2))
            g.dot(buckle[0], buckle[1], 0.55, (210, 200, 170), clip_to_group=True)
        g.commit()
        # near leg is its own pass but drawn over the pelvis with the SAME material and no inner line
        g2 = cv.group(inner_line=False)
        self._near_leg_into(g2)
        g2.commit()
        # re-ink only where the near leg crosses the far leg / outside the pelvis
        if skin_leg:
            pass

    def _near_leg_into(self, g):
        # reuse leg() drawing into a provided group
        L = self.L
        hj, kn, an, lw = self.leg_geom('n')
        skin_leg = L.legs2 == 'skin' or (L.dress is not None and L.legs2 != 'tights')
        pst = L.spec.get('pstyle', 'long')
        rh, rk, ra = 2.85 * lw, 2.1 * lw, 1.55 * lw
        if pst == 'bike':
            rh, rk, ra = 2.5 * lw, 1.85 * lw, 1.35 * lw
        polys = [seg_quad(hj, kn, rh, rk), seg_quad(kn, an, rk, ra)]
        circles = [(hj[0], hj[1], rh), (kn[0], kn[1], rk)]
        m = g.mask(polys=polys, circles=circles)
        if skin_leg:
            g.fill(g.mask(polys=[seg_quad(hj, kn, rh * 0.82, rk * 0.8), seg_quad(kn, an, rk * 0.8, ra * 0.8)],
                          circles=[(kn[0], kn[1], rk * 0.8), (hj[0], hj[1], rh * 0.82)]),
                   L.skin, shade=0.9, hi=0.3)
        else:
            pm = L.pants if L.overalls is None else L.overalls
            g.fill(m, pm, shade=1.1, hi=0.35)
            if pst in ('shorts', 'bike'):
                cut = lerp(hj, kn, 0.78 if pst == 'shorts' else 0.9)
                lower = g.mask(polys=[seg_quad(cut, kn, rk * 0.86, rk * 0.8), seg_quad(kn, an, rk * 0.8, ra * 0.82)],
                               circles=[(kn[0], kn[1], rk * 0.8)])
                l2 = cloth(L.legs2) if (pst == 'bike' and L.legs2 and L.legs2 != 'skin') else None
                g.fill(lower, l2 or L.skin, shade=0.9, hi=0.3)
            else:
                self._pants_detail(g, hj, kn, an, rh, rk, ra, False, pst)
        self.shoe(g, 'n')
        # ink the near leg's outline where it overlaps the pelvis/far leg, except the hip root
        cv = self.cv
        solid = (g.img_a > 0.5).astype(np.float32)
        from raster import _erode
        er = _erode(solid, 4)
        ring = (solid > 0.5) & (er < 0.5) & (cv.a > 0.5)
        # suppress the line around the hip joint (keeps the thigh joined to the pelvis)
        hip_zone = g.mask(circles=[(hj[0], hj[1], rh * 1.25)])
        tz = g.mask(polys=[self.torso_points()])
        ring &= ~((hip_zone > 0.5) & (tz > 0.5))
        g.img_col[ring] = np.array(L.pants.ink if not skin_leg else L.skin.ink, np.float32) / 255.0

    def skirt(self, back=False):
        L, s, b = self.L, self.s, self.b
        g = self.cv.group()
        waist = add(s.hip, mul(s.up, 4.0))
        kn_y = max(s.knee_n[1], s.knee_f[1]) + 1.2
        dx, dy = self.drag('hem', 1.0)
        top_w = b['waist'] + 0.6
        hw = b['hip'] + 1.6
        fwdp = s.pfwd
        if back:
            pts = [add(waist, mul(fwdp, -top_w)), add(waist, mul(fwdp, top_w * 0.4)),
                   (s.hip[0] + 1.0 + dx * 0.4, kn_y + 0.3), (s.hip[0] - hw - 0.8 + dx, kn_y + dy * 0.2)]
            m = g.mask(polys=[pts])
            g.fill(m, self._far(L.dress, True), shade=0.8, hi=0.0)
            g.commit()
            return
        pts = [add(waist, mul(fwdp, -top_w - 0.3)), add(waist, mul(fwdp, top_w + 0.3)),
               add(s.hip, mul(fwdp, hw * 0.95)),
               (s.hip[0] + hw + 0.9 + dx * 0.6, kn_y - 0.3 + dy * 0.3),
               (s.hip[0] + 1.0 + dx * 0.8, kn_y + 0.5),
               (s.hip[0] - hw * 0.8 + dx, kn_y + 0.3 + dy * 0.3),
               add(s.hip, mul(fwdp, -hw * 0.95))]
        m = g.mask(polys=[pts])
        g.fill(m, L.dress, shade=1.0, hi=0.35)
        # folds
        for k in (-0.3, 0.25):
            p0 = add(s.hip, mul(fwdp, k * hw))
            g.line([p0, (p0[0] + k * 1.6 + dx * 0.5, kn_y - 0.3)], 0.9, L.dress.shadow, 0.9)
        g.commit()

    def neck(self):
        L, s = self.L, self.s
        g = self.cv.group()
        nw = 1.35 * self.b['w'] if self.b['w'] < 1.2 else 1.75 * self.b['w'] * 0.85
        top = self.H((-0.05, 0.6))
        pts = seg_quad(s.neck_base, top, nw, nw * 0.92)
        g.fill(g.mask(polys=[pts], circles=[(s.neck_base[0], s.neck_base[1], nw)]), L.skin, shade=0.5, hi=0.0)
        # jaw shadow on the neck
        jaw = self.HP([(-0.6, 0.35), (0.1, 1.15), (0.7, 0.95), (0.9, 0.5), (0.2, 0.3)])
        g.shade_region(g.mask(polys=[jaw]) , L.skin.shadow)
        g.commit()

    def torso(self):
        L, s, b = self.L, self.s, self.b
        g = self.cv.group(occlude=0.35)
        tp = self.torso_points(hem_drop=0.0)
        torso_m = g.mask(polys=[tp])
        tuck = L.jacket is None and L.overalls is None
        hem_o = add(s.hip, mul(s.up, 1.9 if not tuck else 1.2))
        top = g.mask(polys=[self.halfplane(hem_o, s.up)])
        shirt = torso_m * top
        sm = L.shirt
        if L.dress is not None and L.apron is None and L.jacket is None:
            sm = L.dress
        g.fill(shirt, sm, shade=1.3, hi=0.45, deep=0.0)
        if L.shirt_pattern and L.shirt_pattern.startswith('stripe'):
            sc = (200, 50, 50) if L.shirt_pattern == 'stripe_rw' else (40, 52, 96)
            for i in range(6):
                o = add(s.neck_base, mul(s.up, -2.0 - i * 2.0))
                band = g.mask(polys=[self.halfplane(o, s.up)]) * g.mask(polys=[self.halfplane(add(o, mul(s.up, -0.9)),
                                                                                             mul(s.up, -1))]) * shirt
                g.paint_flat(band * (g.img_a > 0.5), sc)
        if L.shirt_pattern == 'hawaii':
            import random as _r
            rr = _r.Random(3)
            for k in range(9):
                u_ = rr.uniform(1.5, 11.0)
                v_ = rr.uniform(-b['back'] + 0.5, b['chest'] - 0.5)
                c_ = add(add(s.hip, mul(s.up, u_)), mul(s.fwd, v_))
                g.dot(c_[0], c_[1], 0.7, [(240, 90, 60), (250, 200, 60), (70, 170, 120)][k % 3], clip_to_group=True)
        # collar / neckline
        nl = [add(add(s.neck_base, mul(s.fwd, 1.4)), mul(s.up, 0.1)), add(add(s.neck_base, mul(s.fwd, 0.2)), mul(s.up, -1.3)),
              add(add(s.neck_base, mul(s.fwd, -1.3)), mul(s.up, 0.0))]
        g.line(nl, 1.0, sm.shadow, 0.95)
        # cloth folds: a few diagonal creases from the twist
        t = s.twist
        for k in (0.0, 1.0):
            a = add(add(s.hip, mul(s.up, 4.0 + k * 3.0)), mul(s.fwd, b['waist'] * (0.2 - 0.6 * k)))
            c = add(a, add(mul(s.up, 2.2), mul(s.fwd, 1.4 + 1.2 * t)))
            g.line([a, c], 0.8, sm.shadow, 0.7)
        if not tuck or L.dress is not None:
            pass
        # untucked hem line
        g.line([add(hem_o, mul(s.fwd, -b['waist'] - 1.0)), add(hem_o, mul(s.fwd, b['waist'] + b['belly'] + 1.0))],
               0.9, sm.shadow, 0.8)
        if L.armband is not None and L.jacket is None:
            pass
        g.commit()

    def outerwear(self):
        L, s, b = self.L, self.s, self.b
        if L.apron is not None and L.jacket is None:
            self.apron()
            return
        if L.overalls is not None:
            self.overall_bib()
        if not L.jacket:
            if L.apron is not None:
                self.apron()
            return
        J = L.jacket
        kind = J['kind']
        jm = L.jmat
        g = self.cv.group(occlude=0.3)
        length_drop = {'waist': 0.4, 'hip': 1.6, 'long': 0.0}.get(J.get('length', 'waist'), 0.4)
        if kind in ('vest', 'safety'):
            length_drop = 0.0
        exp = 0.45 if kind not in ('vest', 'safety') else 0.25
        tp = self.torso_points(expand=exp)
        m = g.mask(polys=[tp])
        hem_o = add(s.hip, mul(s.up, 1.2 - length_drop))
        dx, dy = self.drag('hem', 1.0)
        if J.get('length') == 'long':
            # long coat: skirt panel to the knees, trailing with drag
            kn_y = max(s.knee_n[1], s.knee_f[1]) + 1.5
            hw = b['hip'] + 1.4
            coat = [add(s.hip, mul(s.pfwd, -hw)), add(s.hip, mul(s.pfwd, hw * 0.9)),
                    (s.hip[0] + hw * 0.8 + dx * 0.5, kn_y + dy * 0.2), (s.hip[0] - hw - 1.0 + dx, kn_y + 0.4 + dy * 0.3)]
            m = np.maximum(m, g.mask(polys=[catmull(coat, closed=True, steps=3)]))
        else:
            m = m * g.mask(polys=[self.halfplane(hem_o, s.up)])
            # trailing back hem flap (secondary motion)
            if kind not in ('vest', 'safety') and (abs(dx) + abs(dy)) > 0.05:
                bp = add(add(s.hip, mul(s.pfwd, -b['hip'] - 0.4)), mul(s.up, 1.2 - length_drop))
                flap = [add(bp, mul(s.up, 2.6)), add(bp, mul(s.pfwd, 2.5)),
                        add(add(bp, (dx * 0.9, dy * 0.6)), mul(s.up, -0.6)), add(bp, (dx * 1.1 - 0.4, dy * 0.6 + 0.6))]
                m = np.maximum(m, g.mask(polys=[flap]))
        # open front: cut a strip at the front so the shirt shows
        if J.get('open', True) and kind not in ('chef', 'padded'):
            front = add(add(s.neck_base, mul(s.fwd, b['chest'] - 1.9)), mul(s.up, 0))
            cutp = [add(add(s.neck_base, mul(s.fwd, 0.6)), mul(s.up, 0.6)), add(add(s.neck_base, mul(s.fwd, b['chest'] + 3)), mul(s.up, 0.6)),
                    add(add(s.hip, mul(s.fwd, b['waist'] + b['belly'] + 3)), mul(s.up, -4)),
                    add(add(s.hip, mul(s.fwd, b['waist'] * 0.55 + b['belly'])), mul(s.up, -4)),
                    add(front, mul(s.up, -4.0))]
            cutm = g.mask(polys=[cutp])
            m = m * (1 - cutm)
        if kind in ('vest', 'safety'):
            # deep arm hole: remove the shoulder cap area
            pass
        g.fill(m, jm, shade=1.2, hi=0.5, deep=0.0)
        if jm.gloss:
            # leather sheen streak
            a = add(add(s.neck_base, mul(s.up, -3.0)), mul(s.fwd, -b['back'] * 0.3))
            c = add(add(s.hip, mul(s.up, 4.5)), mul(s.fwd, -b['waist'] * 0.2))
            g.line([a, c], 1.4, jm.light, 0.65)
        # stripe (Nico's jacket: red chest band)
        if J.get('stripe'):
            sc = cloth(J['stripe'])
            o = add(s.neck_base, mul(s.up, -5.2))
            band = g.mask(polys=[self.halfplane(o, s.up)]) * g.mask(polys=[self.halfplane(add(o, mul(s.up, -1.6)), mul(s.up, -1))])
            g.fill(band * (g.img_a > 0.5), sc, shade=1.2, hi=0.3)
        if J.get('trim') == 'pins':
            for k, pc in enumerate(((236, 80, 120), (250, 210, 70), (90, 190, 220))):
                p0 = add(add(s.neck_base, mul(s.up, -2.4 - k * 1.7)), mul(s.fwd, b['chest'] - 2.6 + k * 0.3))
                g.dot(p0[0], p0[1], 0.55, pc, clip_to_group=True)
        elif kind == 'track' or J.get('trim'):
            trim = cloth(J.get('trim') or 'white')
            if kind in ('track',) and not J.get('open', True):
                z0 = add(s.neck_base, mul(s.fwd, b['chest'] * 0.55))
                z1 = add(s.hip, mul(s.fwd, b['waist'] * 0.55 + b['belly']))
                g.line([z0, z1], 0.8, jm.shadow, 1.0)
                g.dot(z0[0], z0[1] + 0.8, 0.35, (220, 220, 230), clip_to_group=True)
            if kind in ('satin', 'varsity'):
                # ribbed hem + collar trim
                g.line([add(hem_o, mul(s.fwd, -b['waist'] - 1)), add(hem_o, mul(s.fwd, b['waist'] + 1))], 1.6,
                       trim.base, 1.0)
        # collar
        col_pts = [add(add(s.neck_base, mul(s.fwd, -1.6)), mul(s.up, 0.9)), add(add(s.neck_base, mul(s.fwd, 0.4)), mul(s.up, 1.2)),
                   add(add(s.neck_base, mul(s.fwd, 2.0)), mul(s.up, -0.6)), add(add(s.neck_base, mul(s.fwd, 0.2)), mul(s.up, -1.3)),
                   add(add(s.neck_base, mul(s.fwd, -2.2)), mul(s.up, -0.6))]
        if kind not in ('vest', 'safety', 'chef'):
            cm_ = g.mask(polys=[catmull(col_pts, closed=True, steps=3)])
            g.fill(cm_, jm, shade=0.5, hi=0.3)
            g.line([col_pts[0], col_pts[1], col_pts[2]], 0.9, jm.shadow, 0.9)
        # lapel edge line
        if J.get('open', True) and kind not in ('chef', 'padded'):
            e0 = add(add(s.neck_base, mul(s.fwd, 1.2)), mul(s.up, -0.6))
            e1 = add(add(s.hip, mul(s.fwd, b['waist'] * 0.7 + b['belly'] * 0.9)), mul(s.up, 1.6 - length_drop))
            g.line([e0, lerp(e0, e1, 0.5), e1], 1.0, jm.ink, 1.0)
        # studs
        if L.spec.get('studs'):
            for i in range(4):
                p = add(add(s.neck_base, mul(s.up, -1.4 - i * 2.2)), mul(s.fwd, b['chest'] - 2.2 - i * 0.25))
                g.dot(p[0], p[1], 0.42, (220, 222, 232), clip_to_group=True)
                g.dot(p[0] + 0.12, p[1] - 0.12, 0.16, (255, 255, 255), clip_to_group=True)
            for i in range(3):
                p = add(add(s.neck_base, mul(s.up, -0.7)), mul(s.fwd, -2.5 + i * 1.3))
                g.dot(p[0], p[1], 0.38, (220, 222, 232), clip_to_group=True)
        if kind == 'safety':
            # reflective stripes
            for k in (5.0, 8.0):
                o = add(s.hip, mul(s.up, k))
                band = g.mask(polys=[self.halfplane(o, s.up)]) * g.mask(polys=[self.halfplane(add(o, mul(s.up, -0.9)), mul(s.up, -1))])
                g.paint_flat(band * (g.img_a > 0.5), (236, 236, 214))
        if kind == 'cardigan':
            for k in range(3):
                p0 = add(add(s.neck_base, mul(s.up, -3 - k * 3)), mul(s.fwd, b['chest'] - 2.4))
                g.dot(p0[0], p0[1], 0.32, jm.shadow, clip_to_group=True)
        if L.armband is not None:
            pass
        g.commit()
        if L.apron is not None:
            self.apron()

    def overall_bib(self):
        L, s, b = self.L, self.s, self.b
        g = self.cv.group()
        bib = [add(add(s.neck_base, mul(s.up, -4.5)), mul(s.fwd, b['chest'] - 0.1)),
               add(add(s.neck_base, mul(s.up, -4.5)), mul(s.fwd, b['chest'] - 4.2)),
               add(add(s.hip, mul(s.up, 2.0)), mul(s.fwd, b['waist'] - 4.0)),
               add(add(s.hip, mul(s.up, 2.0)), mul(s.fwd, b['waist'] + b['belly'] + 0.4))]
        tm = g.mask(polys=[self.torso_points(expand=0.2)])
        g.fill(g.mask(polys=[bib]) * tm, L.overalls, shade=1.0, hi=0.3)
        strap = [add(add(s.neck_base, mul(s.fwd, 0.6)), mul(s.up, -0.5)), bib[1]]
        g.line(strap, 1.6, L.overalls.base, 1.0, clip_to_group=False)
        g.commit()

    def apron(self):
        L, s, b = self.L, self.s, self.b
        g = self.cv.group()
        kn_y = (s.knee_n[1] + s.knee_f[1]) * 0.5 + 0.6
        dx, dy = self.drag('hem', 0.6)
        top = add(add(s.neck_base, mul(s.up, -2.6)), mul(s.fwd, b['chest'] - 0.4))
        pts = [top, add(top, mul(s.fwd, -4.2)), add(add(s.hip, mul(s.up, 4.0)), mul(s.fwd, -1.2)),
               (s.hip[0] - 1.0 + dx, kn_y + dy * 0.3), (s.hip[0] + b['hip'] + 1.2 + dx * 0.5, kn_y - 0.4),
               add(add(s.hip, mul(s.up, 5.0)), mul(s.fwd, b['waist'] + b['belly'] + 0.3))]
        m = g.mask(polys=[catmull(pts, closed=True, steps=3)])
        g.fill(m, L.apron, shade=0.9, hi=0.4)
        # waist tie + pocket
        o = add(s.hip, mul(s.up, 4.6))
        g.line([add(o, mul(s.fwd, -b['waist'] - 0.6)), add(o, mul(s.fwd, b['waist'] + 0.6))], 0.9,
               L.apron.shadow, 1.0, clip_to_group=False)
        pk = add(add(s.hip, mul(s.up, 1.2)), mul(s.fwd, 1.2))
        g.line([add(pk, (-1.6, 0)), add(pk, (1.6, 0)), add(pk, (1.5, 1.8)), add(pk, (-1.5, 1.8))], 0.8,
               L.apron.shadow, 0.9)
        if L.spec.get('apron_stain'):
            g.dot(pk[0] + 0.5, pk[1] - 2.0, 0.8, (180, 150, 110), 0.7, clip_to_group=True)
        g.commit()

    # ================================================================== arms
    def arm(self, side):
        L, s, b = self.L, self.s, self.b
        cv = self.cv
        far = side == 'f'
        sh = s.sh_n if side == 'n' else s.sh_f
        el = s.elb_n if side == 'n' else s.elb_f
        wr = s.wr_n if side == 'n' else s.wr_f
        fist = s.fist_n if side == 'n' else s.fist_f
        hand = s.pose['hand_n'] if side == 'n' else s.pose['hand_f']
        lw = b['limb']
        g = cv.group(occlude=0.0 if far else 0.32, occ_tx=2.0)
        # tapered, muscled limb: deltoid -> bicep -> elbow -> forearm belly -> wrist (one merged mask)
        rs, rb, re, rf, rw = 2.25 * lw, 2.1 * lw, 1.62 * lw, 1.82 * lw, 1.22 * lw
        bic = lerp(sh, el, 0.42)
        fore = lerp(el, wr, 0.3)
        skin = self._far(L.skin, far)
        arm_poly = [seg_quad(sh, bic, rs, rb), seg_quad(bic, el, rb, re), seg_quad(el, fore, re, rf),
                    seg_quad(fore, wr, rf, rw)]
        circ = [(sh[0], sh[1], rs), (bic[0], bic[1], rb), (el[0], el[1], re), (fore[0], fore[1], rf)]
        g.fill(g.mask(polys=arm_poly, circles=circ), skin, shade=0.8, hi=0.32)
        if L.sleeves == 'none' and not (L.jacket and L.jacket.get('sleeves', 'long') != 'none'
                                        and L.jacket['kind'] not in ('vest', 'safety')):
            # bare arm: bicep / forearm muscle hints
            a1 = norm(sub(el, sh))
            g.line([add(lerp(sh, el, 0.3), mul(perp(a1), rb * 0.35)), add(lerp(sh, el, 0.62), mul(perp(a1), rb * 0.45))],
                   0.7, skin.shadow, 0.6)
        # sleeves
        sleeves = L.sleeves
        smat = L.shirt
        jk = L.jacket
        if jk and jk.get('sleeves', 'long') != 'none' and jk['kind'] not in ('vest', 'safety'):
            sleeves = jk.get('sleeves', 'long')
            smat = L.jmat
        if L.dress is not None and L.jacket is None and L.apron is not None:
            smat = L.dress
        smat = self._far(smat, far)
        if sleeves != 'none':
            ext = 0.45
            if sleeves == 'short':
                end = lerp(sh, el, 0.58)
                poly = [seg_quad(sh, end, rs + ext, rb + ext + 0.2)]
                cc = [(sh[0], sh[1], rs + ext)]
            elif sleeves == 'rolled':
                end = lerp(el, wr, 0.32)
                poly = [seg_quad(sh, bic, rs + ext, rb + ext), seg_quad(bic, el, rb + ext, re + ext),
                        seg_quad(el, end, re + ext, rf + ext * 0.6)]
                cc = [(sh[0], sh[1], rs + ext), (bic[0], bic[1], rb + ext), (el[0], el[1], re + ext)]
            else:
                end = lerp(el, wr, 0.86)
                poly = [seg_quad(sh, bic, rs + ext, rb + ext), seg_quad(bic, el, rb + ext, re + ext),
                        seg_quad(el, fore, re + ext, rf + ext), seg_quad(fore, end, rf + ext, rw + ext + 0.35)]
                cc = [(sh[0], sh[1], rs + ext), (bic[0], bic[1], rb + ext), (el[0], el[1], re + ext),
                      (fore[0], fore[1], rf + ext)]
            sm_ = g.mask(polys=poly, circles=cc)
            g.fill(sm_, smat, shade=0.95, hi=0.38)
            seg_from = el if sleeves != 'short' else sh
            d = norm(sub(end, seg_from))
            n = perp(d)
            w_ = (rb + ext + 0.25) if sleeves == 'short' else (rw + ext + 0.4)
            if sleeves == 'long':
                # cuff band
                c0 = add(end, mul(d, -1.0))
                cuff = g.mask(polys=[seg_quad(c0, end, rw + ext + 0.45, rw + ext + 0.45)]) * (sm_ > 0.5)
                g.fill(cuff, smat.darker(0.12), shade=0.4, hi=0.2)
                g.line([add(c0, mul(n, w_)), add(c0, mul(n, -w_))], 0.8, smat.shadow, 0.9)
            elif sleeves == 'rolled':
                r0 = add(end, mul(d, -1.3))
                roll = g.mask(polys=[seg_quad(r0, end, rf + ext + 0.4, rf + ext * 0.6 + 0.4)])
                g.fill(roll, smat, shade=0.5, hi=0.4)
                g.line([add(r0, mul(n, w_)), add(r0, mul(n, -w_))], 0.9, smat.shadow, 1.0)
            else:
                h0 = add(end, mul(d, -0.8))
                g.line([add(h0, mul(n, w_)), add(h0, mul(n, -w_))], 0.8, smat.shadow, 0.8)
            g.line([add(end, mul(n, w_)), add(end, mul(n, -w_))], 1.0, smat.shadow, 1.0)
            # folds: inner elbow crease + forearm / upper-arm wrinkles
            a1, a2 = norm(sub(el, sh)), norm(sub(wr, el))
            bend = a1[0] * a2[0] + a1[1] * a2[1]
            if sleeves in ('long', 'rolled'):
                if bend < 0.92:
                    inner = add(el, mul(perp(a1), -re * 0.45))
                    g.line([add(inner, mul(a1, -1.4)), inner, add(inner, mul(a2, 1.2))], 0.8, smat.shadow, 0.95)
                p0 = lerp(el, wr, 0.45)
                g.line([add(p0, mul(perp(a2), rf * 0.6)), add(add(p0, mul(a2, 0.9)), mul(perp(a2), -rf * 0.1))], 0.7,
                       smat.shadow, 0.75)
            p1 = lerp(sh, el, 0.35)
            g.line([add(p1, mul(perp(a1), -rb * 0.55)), add(add(p1, mul(a1, 1.0)), mul(perp(a1), rb * 0.05))], 0.7,
                   smat.shadow, 0.7)
            if jk and jk.get('stripe') and not far:
                st = cloth(jk['stripe'])
                p0, p1 = lerp(sh, el, 0.22), lerp(sh, el, 0.40)
                band = g.mask(polys=[seg_quad(p0, p1, rs + ext + 0.2, rb + ext + 0.2)]) * (sm_ > 0.5)
                g.fill(band, st, shade=0.6, hi=0.2)
            if jk and jk['kind'] == 'track':
                trim = cloth(jk.get('trim') or 'white')
                nrm = perp(norm(sub(el, sh)))
                g.line([add(sh, mul(nrm, -rs * 0.62)), add(el, mul(nrm, -re * 0.75)),
                        add(end, mul(perp(norm(sub(end, el))), -rw * 0.9))], 1.1, trim.base, 0.95)
        # wristband / armband / guards
        if L.wrist is not None:
            a = lerp(el, wr, 0.74)
            g.fill(g.mask(polys=[seg_quad(a, wr, rf * 0.95 + 0.3, rw + 0.35)]), self._far(L.wrist, far), shade=0.5, hi=0.25)
            if L.spec.get('studs'):
                m_ = lerp(a, wr, 0.5)
                g.dot(m_[0], m_[1], 0.32, (220, 222, 232), clip_to_group=True)
        if L.armband is not None:
            a, c = lerp(sh, el, 0.35), lerp(sh, el, 0.6)
            g.fill(g.mask(polys=[seg_quad(a, c, rs + 0.7, rb + 0.7)]), self._far(L.armband, far), shade=0.5, hi=0.2)
        if L.guards is not None:
            a, c = lerp(el, wr, 0.15), lerp(el, wr, 0.85)
            g.fill(g.mask(polys=[seg_quad(a, c, rf + 0.55, rw + 0.55)]), self._far(L.guards, far), shade=0.6, hi=0.3)
            g.line([lerp(a, c, 0.5), lerp(a, c, 0.52)], 0.8, self._far(L.guards, far).shadow, 0.9)
        hm = self._far(L.glove, far) if L.glove is not None else skin
        self.hand(g, wr, fist, hand, hm, lw, far)
        g.commit()

    def hand(self, g, wr, fist, kind, hm, lw, far):
        d = norm(sub(fist, wr))
        n = perp(d)
        fr = self.b['fist']

        def F(u, v, c):
            return (c[0] + d[0] * u * fr + n[0] * v * fr, c[1] + d[1] * u * fr + n[1] * v * fr)
        if kind in ('open', 'relax', 'point'):
            pc = add(wr, mul(d, fr * 0.55))
            palm = [F(u, v, pc) for (u, v) in ((-0.45, -0.8), (0.55, -0.85), (0.7, 0.0), (0.55, 0.85), (-0.45, 0.8))]
            ln = 1.75 if kind == 'open' else 1.25
            if kind == 'point':
                ln = 1.1
            fingers = [F(0.45, -0.82, pc), F(ln, -0.62, pc), F(ln + 0.08, 0.0, pc), F(ln, 0.62, pc), F(0.45, 0.82, pc)]
            polys = [catmull(palm, True, 3), catmull(fingers + [F(0.3, 0.0, pc)], True, 3)]
            if kind == 'point':
                polys.append(seg_quad(F(0.6, -0.5, pc), F(2.4, -0.55, pc), fr * 0.24, fr * 0.2))
            th0, th1 = F(0.0, -0.75, pc), F(0.75, -1.35, pc)
            polys.append(seg_quad(th0, th1, fr * 0.3, fr * 0.22))
            m = g.mask(polys=polys, circles=[(th1[0], th1[1], fr * 0.22)])
            g.fill(m, hm, shade=0.45, hi=0.25)
            for v in (-0.3, 0.3):
                g.line([F(0.75, v, pc), F(ln - 0.15, v, pc)], 0.6, hm.shadow, 0.85)
            g.line([F(0.05, -0.55, pc), F(0.55, -0.85, pc)], 0.6, hm.shadow, 0.8)
            return
        # fist: squarish block with knuckle ridge, finger grooves and thumb wrap
        c = fist
        box = [F(-0.62, -0.92, c), F(0.62, -0.98, c), F(1.0, -0.62, c), F(1.04, 0.0, c), F(1.0, 0.62, c),
               F(0.62, 0.95, c), F(-0.62, 0.9, c)]
        m = g.mask(polys=[catmull(box, True, 3), seg_quad(wr, F(-0.4, 0.0, c), fr * 0.72, fr * 0.86)])
        g.fill(m, hm, shade=0.55, hi=0.32)
        g.line([F(0.5, -0.86, c), F(0.62, 0.0, c), F(0.5, 0.86, c)], 0.75, hm.shadow, 0.95)
        for v in (-0.3, 0.3):
            g.line([F(0.62, v, c), F(1.0, v, c)], 0.6, hm.shadow, 0.8)
        th = [F(-0.35, -0.9, c), F(0.38, -0.25, c)]
        tm = g.mask(polys=[seg_quad(th[0], th[1], fr * 0.32, fr * 0.27)], circles=[(th[1][0], th[1][1], fr * 0.27)])
        g.fill(tm, Mat(light_of(hm.base, 0.4), hm.shadow, light_of(hm.base, 0.9)), shade=0.25, hi=0.12)
        g.line(th, 0.55, hm.shadow, 0.9)

    # ================================================================== head
    def head_shape_pts(self):
        cran = ellipse_pts(-0.04, -0.06, 1.0, 0.98, 0.0, n=48)
        jaw = catmull([(-0.62, 0.2), (-0.42, 0.66), (0.0, 0.95), (0.42, 1.03), (0.74, 0.86), (0.93, 0.52),
                       (0.99, 0.12), (0.4, -0.1)], closed=True, steps=5)
        if self.L.spec.get('body') in ('heavy', 'big') or self.L.spec.get('bulk'):
            jaw = catmull([(-0.66, 0.2), (-0.5, 0.74), (0.0, 1.02), (0.5, 1.06), (0.84, 0.86), (0.99, 0.5),
                           (1.0, 0.1), (0.4, -0.1)], closed=True, steps=5)
        return self.HP(cran), self.HP(jaw)

    def head(self):
        L = self.L
        cv = self.cv
        g = cv.group(occlude=0.45, occ_tx=2.2)
        cran, jaw = self.head_shape_pts()
        m = g.mask(polys=[cran, jaw])
        g.fill(m, L.skin, shade=0.95, hi=0.0, light_dir=(0.75, -0.66))
        # soft cheek/jaw light + forehead highlight
        hl = self.HP(ellipse_pts(0.45, -0.45, 0.35, 0.18, -0.3, n=18))
        g.shade_region(g.mask(polys=[hl]), L.skin.light, 0.55)
        # ear
        ec = (-0.28, 0.22)
        ear = self.H_ell(ec[0], ec[1], 0.17, 0.25, 8)
        g.fill(g.mask(polys=[ear]), L.skin, shade=0.18, hi=0.0)
        g.line(self.HP([(-0.25, 0.12), (-0.33, 0.22), (-0.27, 0.32)]), 0.8, L.skin.shadow, 1.0)
        self.face(g)
        g.commit()
        self.front_hair()
        self.hat()
        self.glasses()

    # ---------------------------------------------------------------- face
    def face(self, g):
        L = self.L
        e = expression(L, self.s.pose['expr'], self.s.pose.get('blink', False))
        if self.portrait:
            e = dict(e, **self.portrait_expr_override)
        eyes = [((0.33, 0.15), 0.20, 0.27, True), ((0.80, 0.13), 0.135, 0.26, False)]
        # stubble/beard below everything else
        self.facial_hair(g, e, under=True)
        for (c, rx, ry, near) in eyes:
            self.eye(g, c, rx, ry, near, e)
        self.brows(g, e)
        self.nose(g)
        self.mouth(g, e)
        if e.get('blush', 0) > 0 or L.face in ('kind', 'cheerful') and L.lashes:
            bl = self.H_ell(0.52, 0.52, 0.16, 0.08, 0)
            g.shade_region(g.mask(polys=[bl]), (232, 120, 120), 0.35 + e.get('blush', 0) * 0.4)
        self.marks(g)
        self.facial_hair(g, e, under=False)

    def eye(self, g, c, rx, ry, near, e):
        L = self.L
        cx, cy = c
        kind = e['eye']
        ink = (34, 22, 36)
        lw = 1.15
        if kind in ('closed',):
            g.line(self.HP([(cx - rx, cy + 0.02), (cx, cy + ry * 0.35), (cx + rx, cy + 0.02)]), lw, ink)
            if L.lashes:
                g.line(self.HP([(cx - rx, cy + 0.02), (cx - rx - 0.07, cy - 0.04)]), lw * 0.8, ink)
            return
        if kind == 'happy':
            g.line(self.HP([(cx - rx, cy + ry * 0.25), (cx, cy - ry * 0.45), (cx + rx, cy + ry * 0.25)]), lw * 1.1, ink)
            return
        if kind == 'squeeze':
            if near:
                g.line(self.HP([(cx - rx, cy - ry * 0.5), (cx + rx * 0.6, cy), (cx - rx, cy + ry * 0.45)]), lw * 1.1, ink)
            else:
                g.line(self.HP([(cx + rx, cy - ry * 0.5), (cx - rx * 0.6, cy), (cx + rx, cy + ry * 0.45)]), lw * 1.1, ink)
            return
        if kind == 'ko':
            g.line(self.HP([(cx - rx, cy - ry * 0.6), (cx + rx, cy + ry * 0.6)]), lw, ink)
            g.line(self.HP([(cx - rx, cy + ry * 0.6), (cx + rx, cy - ry * 0.6)]), lw, ink)
            return
        if kind == 'swirl':
            pts = [(cx + math.cos(t) * rx * (t / 9.0), cy + math.sin(t) * ry * (t / 9.0)) for t in np.linspace(0.5, 9.0, 18)]
            g.paint_flat(g.mask(polys=[self.H_ell(cx, cy, rx, ry)]), EYE_W)
            g.line(self.HP(pts), lw * 0.8, ink)
            return
        sc = 1.12 if kind == 'wide' else 1.0
        white = self.H_ell(cx, cy, rx * sc, ry * sc, 0, n=28)
        wm = g.mask(polys=[white])
        g.paint_flat(wm, EYE_W)
        # lower-lid shading inside the white (depth)
        g.shade_region(wm * g.mask(polys=[self.H_ell(cx, cy - ry * 0.55, rx * 1.3, ry * 0.6)]), lerp_c(EYE_W, L.skin.shadow, 0.35))
        # iris & pupil (looking forward)
        ir = 0.62 if kind != 'wide' else 0.42
        icx = cx + rx * 0.22 * e.get('look', 1.0)
        icy = cy + ry * 0.08
        im = g.mask(polys=[self.H_ell(icx, icy, rx * ir * 1.05, ry * ir * 1.0)]) * wm
        g.paint_flat(im, L.iris)
        g.paint_flat(g.mask(polys=[self.H_ell(icx, icy + ry * 0.12, rx * ir * 0.9, ry * ir * 0.45)]) * im,
                     lerp_c(L.iris, (255, 255, 255), 0.18))
        g.paint_flat(g.mask(polys=[self.H_ell(icx + rx * 0.05, icy, rx * ir * 0.5, ry * ir * 0.55)]) * wm, (18, 12, 20))
        hlr = max(rx * 0.22, 0.09)
        g.paint_flat(g.mask(polys=[self.H_ell(icx + rx * 0.22, icy - ry * 0.3, hlr, hlr * 1.1)]), (255, 255, 255))
        # lids: angry cut (inner end low), sad (outer low), half-closed
        lid = e.get('lid', 0.0)
        sad = e.get('sad', 0.0)
        inner = +1 if near else -1      # inner corner toward the nose (+x for near eye)
        top = cy - ry * sc
        if lid > 0 or sad > 0:
            # polygon of skin above a slanted line
            yl_in = top + ry * 2 * sc * (lid * 0.95)
            yl_out = top + ry * 2 * sc * (lid * 0.35 + sad * 0.7)
            if sad > 0:
                yl_in, yl_out = top + ry * 2 * sc * 0.08, top + ry * 2 * sc * (0.2 + sad * 0.45)
            xin = cx + inner * rx * 1.2
            xout = cx - inner * rx * 1.2
            lidp = [(xout, yl_out), (xin, yl_in), (xin, top - ry), (xout, top - ry)]
            lm = g.mask(polys=[self.HP(lidp)]) * g.mask(polys=[self.H_ell(cx, cy, rx * 1.25, ry * 1.25)])
            g.paint_flat(lm, L.skin.base)
            g.line(self.HP([(xout, yl_out), (xin, yl_in)]), lw * 1.15, ink)
        else:
            arc = [(cx + rx * sc * math.cos(t), cy + ry * sc * math.sin(t)) for t in np.linspace(math.pi * 1.05, math.pi * 1.95, 9)]
            g.line(self.HP(arc), lw * 1.15, ink)
        # outline around the white (thin)
        g.line(self.HP(ellipse_pts(cx, cy, rx * sc, ry * sc, 0, n=24)), lw * 0.55, lerp_c(ink, L.skin.shadow, 0.3), 0.9,
               closed=True)
        if L.lashes:
            o = cx - rx * 1.0 if near else cx + rx * 1.0
            g.line(self.HP([(o, cy - ry * 0.55), (o - 0.09 * (1 if near else -1), cy - ry * 0.85)]), lw * 0.9, ink)

    def brows(self, g, e):
        L = self.L
        ang = e['brow_ang']
        lift = e['brow_lift']
        th = 0.085 if L.spec.get('face') not in ('tough', 'mean', 'stern') else 0.11
        for (x0, x1, near) in ((0.18, 0.50, True), (0.68, 0.93, False)):
            y = -0.16 - lift
            # inner end = toward nose: near brow -> x1 side, far brow -> x0 side
            k = math.tan(math.radians(ang)) * (x1 - x0)
            if near:
                p0, p1 = (x0, y + k * 0.15), (x1, y - k * 0.85)
            else:
                p0, p1 = (x0, y - k * 0.85), (x1, y + k * 0.15)
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 - 0.03)
            pts = ribbon([p0, mid, p1], [th * 0.6, th, th * 0.7])
            g.paint_flat(g.mask(polys=[self.HP(pts)]), L.brow)

    def nose(self, g):
        L = self.L
        tip = [(0.92, 0.26), (1.06, 0.46), (0.93, 0.53)]
        g.fill(g.mask(polys=[self.HP(tip)]), L.skin, shade=0.0, hi=0.0)
        g.line(self.HP([(0.92, 0.3), (1.04, 0.47), (0.92, 0.52)]), 0.8, L.skin.shadow, 1.0)
        g.line(self.HP([(0.80, 0.50), (0.88, 0.53)]), 0.7, lerp_c(L.skin.shadow, (60, 30, 40), 0.3), 0.9)

    def mouth(self, g, e):
        L = self.L
        k = e['mouth']
        cx, cy = 0.64, 0.73
        w = 0.20
        lip = lerp_c(L.skin.shadow, MOUTH_DARK, 0.55)
        lw = 0.95
        if k == 'line':
            g.line(self.HP([(cx - w, cy), (cx + w * 0.8, cy - 0.01)]), lw, lip)
        elif k == 'firm':
            g.line(self.HP([(cx - w, cy + 0.03), (cx - w * 0.2, cy), (cx + w * 0.8, cy - 0.01)]), lw * 1.1, lip)
        elif k == 'frown':
            g.line(self.HP([(cx - w, cy + 0.06), (cx, cy - 0.01), (cx + w * 0.85, cy + 0.04)]), lw * 1.1, lip)
        elif k == 'smile':
            g.line(self.HP([(cx - w * 1.05, cy - 0.06), (cx - w * 0.2, cy + 0.04), (cx + w * 0.85, cy - 0.04)]), lw * 1.1, lip)
        elif k == 'smirk':
            g.line(self.HP([(cx - w * 1.05, cy - 0.07), (cx - w * 0.4, cy + 0.02), (cx + w * 0.8, cy + 0.01)]), lw * 1.1, lip)
        elif k == 'wavy':
            pts = [(cx - w + i * w * 2 / 6, cy + (0.025 if i % 2 else -0.02)) for i in range(7)]
            g.line(self.HP(pts), lw, lip)
        elif k in ('grit', 'grimace'):
            hh = 0.075 if k == 'grit' else 0.11
            box = [(cx - w * 1.1, cy - hh), (cx + w * 0.9, cy - hh * 1.1), (cx + w * 0.95, cy + hh), (cx - w * 1.05, cy + hh * 1.2)]
            if k == 'grimace':
                box = [(cx - w * 1.15, cy - hh * 0.6), (cx + w * 0.95, cy - hh * 1.2), (cx + w * 0.95, cy + hh), (cx - w * 1.1, cy + hh * 1.3)]
            m = g.mask(polys=[self.HP(box)])
            g.paint_flat(m, MOUTH_DARK)
            g.paint_flat(m * g.mask(polys=[self.HP(catmull(box, True, 2))]), TEETH)
            g.line(self.HP([(cx - w * 1.05, cy + 0.005), (cx + w * 0.92, cy - 0.005)]), lw * 0.7, (150, 130, 130))
            g.line(self.HP(box + [box[0]]), lw * 0.9, lip)
        elif k in ('shout', 'shout_small', 'grin_open', 'talk_wide'):
            if k == 'shout':
                pts = [(cx - w * 1.1, cy - 0.08), (cx + w * 0.95, cy - 0.12), (cx + w * 0.8, cy + 0.2), (cx - w * 0.6, cy + 0.24)]
            elif k == 'shout_small':
                pts = [(cx - w * 0.8, cy - 0.05), (cx + w * 0.8, cy - 0.08), (cx + w * 0.55, cy + 0.12), (cx - w * 0.45, cy + 0.14)]
            elif k == 'talk_wide':
                pts = [(cx - w * 0.8, cy - 0.03), (cx + w * 0.8, cy - 0.05), (cx + w * 0.5, cy + 0.12), (cx - w * 0.5, cy + 0.12)]
            else:
                pts = [(cx - w * 1.05, cy - 0.06), (cx + w * 0.95, cy - 0.08), (cx + w * 0.6, cy + 0.15), (cx - w * 0.55, cy + 0.14)]
            sm = catmull(pts, True, 4)
            m = g.mask(polys=[self.HP(sm)])
            g.paint_flat(m, MOUTH_DARK)
            # upper teeth band
            tb = g.mask(polys=[self.HP([(cx - w * 1.3, cy - 0.3), (cx + w * 1.3, cy - 0.3), (cx + w * 1.3, cy - 0.02 if k != 'shout' else cy - 0.01),
                                        (cx - w * 1.3, cy - 0.0)])]) * m
            g.paint_flat(tb, TEETH)
            tg = g.mask(polys=[self.H_ell(cx - w * 0.05, cy + 0.17, w * 0.55, 0.07)]) * m
            g.paint_flat(tg, TONGUE)
            g.line(self.HP(sm + [sm[0]]), lw * 0.9, lip)
        elif k in ('O', 'open_small', 'slack'):
            rx, ry = (0.075, 0.1) if k == 'O' else ((0.09, 0.055) if k == 'open_small' else (0.11, 0.07))
            m = g.mask(polys=[self.H_ell(cx, cy + 0.02, rx, ry)])
            g.paint_flat(m, MOUTH_DARK)
            g.paint_flat(g.mask(polys=[self.H_ell(cx, cy + 0.02 + ry * 0.5, rx * 0.7, ry * 0.4)]) * m, TONGUE)
            g.line(self.HP(ellipse_pts(cx, cy + 0.02, rx, ry, 0, n=16)), lw * 0.8, lip, closed=True)

    def marks(self, g):
        L = self.L
        mk = L.spec.get('marks', ())
        if 'scar' in mk:
            g.line(self.HP([(0.18, -0.30), (0.42, 0.05), (0.50, 0.32)]), 0.9,
                   lerp_c(L.skin.light, (255, 220, 220), 0.4), 1.0)
        if 'freckles' in mk:
            for (x, y) in ((0.42, 0.45), (0.55, 0.42), (0.48, 0.52), (0.84, 0.44), (0.9, 0.5)):
                g.dot(*self.H((x, y)), 0.12 * self.R / 7.0 * (1), L.skin.shadow, 0.9)
        if 'smudge' in mk:
            g.shade_region(g.mask(polys=[self.H_ell(0.6, 0.5, 0.14, 0.06, -10)]), (90, 70, 70), 0.5)
        if 'soot' in mk:
            g.shade_region(g.mask(polys=[self.H_ell(0.4, 0.55, 0.22, 0.1, 10)]), (70, 60, 66), 0.35)

    def facial_hair(self, g, e, under):
        L = self.L
        fh = L.spec.get('fhair')
        if not fh:
            return
        fc = hair_mat(dict(L.spec, hcol=L.spec.get('fhcol') or L.spec.get('hcol')))
        if under and fh == 'stubble':
            jaw = self.HP(catmull([(-0.2, 0.55), (0.2, 0.95), (0.6, 1.0), (0.9, 0.72), (0.98, 0.55), (0.5, 0.6)], True, 3))
            g.shade_region(g.mask(polys=[jaw]), fc.shadow, 0.35)
            return
        if under:
            return
        if fh in ('beard',):
            pts = catmull([(-0.45, 0.25), (-0.3, 0.75), (0.1, 1.08), (0.55, 1.12), (0.9, 0.8), (1.0, 0.55),
                           (0.8, 0.62), (0.62, 0.84), (0.4, 0.86), (0.2, 0.6), (-0.1, 0.35)], True, 3)
            g.fill(g.mask(polys=[self.HP(pts)]), fc, shade=0.4, hi=0.0)
        if fh in ('mustache', 'beard'):
            pts = [(0.42, 0.62), (0.98, 0.58), (1.0, 0.68), (0.7, 0.68), (0.5, 0.74)]
            g.fill(g.mask(polys=[self.HP(catmull(pts, True, 3))]), fc, shade=0.2, hi=0.0)
        if fh == 'goatee':
            pts = [(0.45, 0.86), (0.85, 0.84), (0.72, 1.08), (0.5, 1.05)]
            g.fill(g.mask(polys=[self.HP(catmull(pts, True, 3))]), fc, shade=0.2, hi=0.0)

    # ---------------------------------------------------------------- hair
    def _hair_shapes(self):
        st = self.L.spec.get('hair', 'short')
        return V1.hair_shapes(st)

    def _shape_pts(self, sh, drag=(0.0, 0.0), tipk=0.0):
        kind, a, o = sh
        if kind == 'e':
            x, y, rx, ry, ang = a
            return ellipse_pts(x, y, rx, ry, math.radians(ang), n=36)
        if kind == 'p':
            pts = list(a)
            if tipk and o.get('sub'):
                # move the outermost point (spike tip) with drag
                cxm = sum(p[0] for p in pts) / len(pts)
                cym = sum(p[1] for p in pts) / len(pts)
                far_i = max(range(len(pts)), key=lambda i: (pts[i][0]) ** 2 + (pts[i][1] + 0.1) ** 2)
                px, py = pts[far_i]
                pts[far_i] = (px + drag[0] * tipk, py + drag[1] * tipk)
            return pts
        if kind == 'c':
            x0, y0, x1, y1, r = a
            return seg_quad((x0, y0), (x1, y1), r, r) + ellipse_pts(x1, y1, r, r, 0, 12)
        return []

    def back_hair(self):
        L = self.L
        st = L.spec.get('hair')
        if st in ('bald',) or st is None:
            return
        back, front, hl, ear = self._hair_shapes()
        custom = CUSTOM_BACK.get(st)
        if not back and custom is None:
            return
        g = self.cv.group()
        d = self.drag_local('hair', 1.0)
        polys = []
        if custom is not None:
            polys = [self.HP(p) for p in custom(d)]
        else:
            for sh in back:
                pts = self._shape_pts(sh, d, 0.5)
                polys.append(self.HP(pts))
        m = g.mask(polys=polys)
        g.fill(m, self._far(L.hair, True), shade=0.6, hi=0.2)
        self._strands(g, polys, L.hair, far=True)
        g.commit()

    def front_hair(self):
        L = self.L
        st = L.spec.get('hair')
        if st in ('bald', None):
            return
        back, front, hl, ear = self._hair_shapes()
        g = self.cv.group()
        d = self.drag_local('hair', 1.0)
        custom = CUSTOM_FRONT.get(st)
        hm = L.hair
        shaved = Mat(lerp_c(L.skin.base, hm.shadow, 0.30), lerp_c(L.skin.shadow, hm.shadow, 0.45), lerp_c(L.skin.light, hm.base, 0.2))
        # face zone: hair (non 'face' shapes) cannot cover it
        fz = g.mask(polys=[self.HP([(-0.30, hl), (2.0, hl - 0.12), (2.0, 2.0), (-0.30, 2.0)])])
        if custom is not None:
            parts = custom(d)
        else:
            parts = [(self._shape_pts(sh, d, 0.35), sh[2]) for sh in front]
        shaved_m = None
        main = []
        for pts, o in parts:
            m = g.mask(polys=[self.HP(pts)])
            if not o.get('face'):
                m = m * (1 - fz)
            if o.get('shaved'):
                shaved_m = m if shaved_m is None else np.maximum(shaved_m, m)
            else:
                main.append((m, o, pts))
        if shaved_m is not None:
            # shaved sides: tinted into the scalp, no ink contour
            gs = self.cv.group(inner_line=False)
            gs.fill(shaved_m * (self.cv.a > 0.5), shaved, shade=0.5, hi=0.0)
            rng = np.random.RandomState(7)
            for i in range(14):
                x, y = rng.uniform(-0.9, 0.3), rng.uniform(-0.9, 0.0)
                gs.dot(*self.H((x, y)), 0.1, hm.shadow, 0.35, clip_to_group=True)
            gs.commit()
        if main:
            allm = main[0][0]
            for m, o, pts in main[1:]:
                allm = np.maximum(allm, m)
            g.fill(allm, hm, shade=0.7, hi=0.3)
            # per-sub-shape inner separation lines (spikes / curls)
            for m, o, pts in main:
                if o.get('sub'):
                    g.line(self.HP(pts[:max(2, len(pts) - 1)]), 0.7, hm.shadow, 0.8)
            # shine band
            sh_pts = self.HP(ellipse_pts(0.15, -0.72, 0.42, 0.12, -0.35, n=18))
            g.paint_flat(g.mask(polys=[sh_pts]) * (allm > 0.5), hm.light, 0.85)
            self._strands(g, [self.HP(p) for _, _, p in main], hm)
        if L.hair2 is not None:
            # streak / two-tone (top front)
            st_pts = self.HP([(-0.2, -1.0), (0.6, -0.9), (0.4, -0.55), (-0.3, -0.7)])
            g.paint_flat(g.mask(polys=[st_pts]) * (g.img_a > 0.5), L.hair2.base)
        g.commit()
        if L.band is not None:
            self.headband()

    def _strands(self, g, polys, hm, far=False):
        """A few inner strand lines following each hair shape."""
        for P_ in polys[:8]:
            if len(P_) < 4:
                continue
            n = len(P_)
            cx = sum(p[0] for p in P_) / n
            cy = sum(p[1] for p in P_) / n
            i = n // 3
            a = P_[i]
            g.line([lerp((cx, cy), a, 0.2), lerp((cx, cy), a, 0.75)], 0.6,
                   hm.shadow, 0.55)

    def headband(self):
        L = self.L
        g = self.cv.group()
        band = [(-1.08, -0.52), (0.9, -0.62), (0.98, -0.40), (-1.08, -0.28)]
        bm = g.mask(polys=[self.HP(band)]) * g.mask(polys=[self.HP(ellipse_pts(-0.04, -0.12, 1.12, 1.1, 0, 40))])
        g.fill(bm, L.band, shade=0.25, hi=0.12)
        knot = self.H_ell(-1.04, -0.40, 0.17, 0.15)
        g.fill(g.mask(polys=[knot]), L.band, shade=0.15, hi=0.1)
        g.commit()

    def tails(self, behind):
        """Headband tails: ribbons trailing from the knot, spring-driven."""
        L = self.L
        if L.band is None or self.portrait and not behind:
            return
        g = self.cv.group()
        d = self.drag('tails', 1.0)
        base = self.H((-1.08, -0.40))
        R = self.R
        for i, (ln, w0, ph) in enumerate(((1.0, 0.16, 0.0), (0.78, 0.14, 1.3))):
            if (i == 0) != behind:
                continue
            pts = [base]
            # rest direction: hang back and down; drag adds streaming
            dirx = -0.55 + d[0] * 0.12
            diry = 0.65 + d[1] * 0.12 - i * 0.12
            L_ = ln * R * 0.95
            v = norm((dirx, diry))
            for k in range(1, 5):
                t = k / 4.0
                wob = math.sin(ph + t * 3.0 + d[0] * 0.3) * 0.12 * R * t
                p = add(base, add(mul(v, L_ * t), mul(perp(v), wob)))
                pts.append(p)
            ws = [w0 * R * (1 - 0.35 * (k / 4)) for k in range(5)]
            poly = ribbon(pts, ws)
            g.fill(g.mask(polys=[poly]), self._far(L.band, behind), shade=0.35, hi=0.15)
        g.commit()

    def hat(self):
        L = self.L
        if not L.spec.get('hat'):
            return
        kind, col = L.spec['hat']
        hm = cloth(col)
        g = self.cv.group()
        for (sh, part, clip) in V1.hat_shapes(kind):
            pts = self._shape_pts(sh)
            m = g.mask(polys=[self.HP(pts)])
            if clip and clip.startswith('clipy:'):
                yv = float(clip.split(':')[1])
                m = m * g.mask(polys=[self.HP([(-3, -3), (3, -3), (3, yv), (-3, yv)])])
            mat = hm
            if part == 'dark':
                mat = hm.darker(0.3)
            elif part == 'light':
                mat = Mat(light_of(hm.base, 1.5))
            elif part == 'gold':
                mat = GOLD
            elif part == 'brim':
                mat = hm.darker(0.15)
            if clip in ('clipmain', 'clipmain2', 'clipmain0', 'badge'):
                m = m * (g.img_a > 0.5)
            g.fill(m, mat, shade=0.5, hi=0.25)
        g.commit()

    def glasses(self):
        L = self.L
        gl = L.spec.get('glasses')
        if not gl:
            return
        g = self.cv.group(inner_line=False)
        if gl == 'shades':
            for (cx, cy, rx, ry) in ((0.34, 0.12, 0.26, 0.2), (0.80, 0.10, 0.17, 0.19)):
                m = g.mask(polys=[self.H_ell(cx, cy, rx, ry)])
                g.fill(m, Mat((30, 28, 40), (14, 12, 20), (110, 110, 140)), shade=0.0, hi=0.0)
                g.line(self.HP([(cx - rx * 0.4, cy - ry * 0.3), (cx + rx * 0.2, cy - ry * 0.6)]), 0.8, (200, 210, 240), 0.8)
            g.line(self.HP([(0.6, 0.06), (0.64, 0.05)]), 1.0, (30, 28, 40))
            g.line(self.HP([(0.08, 0.08), (-0.25, 0.12)]), 1.0, (30, 28, 40))
        else:
            fc = (232, 110, 160) if gl == 'cateye' else ((60, 44, 40) if gl == 'thick' else (70, 60, 70))
            w = 1.0 if gl != 'thick' else 1.5
            for (cx, cy, rx, ry, near) in ((0.34, 0.15, 0.25, 0.22, True), (0.80, 0.13, 0.16, 0.21, False)):
                pts = ellipse_pts(cx, cy, rx, ry, 0, n=24)
                if gl == 'cateye':
                    # pointed outer-upper corner
                    k = 0 if near else 0
                    pts = catmull([(cx - rx, cy - ry * 0.9 - (0.08 if near else 0)), (cx + rx, cy - ry * 0.7 - (0 if near else 0.06)),
                                   (cx + rx * 0.9, cy + ry * 0.6), (cx - rx * 0.8, cy + ry * 0.7)], True, 4)
                g.line(self.HP(pts + [pts[0]]), w * (1.2 if gl == 'cateye' else 1.0), fc, 1.0, clip_to_group=False)
                g.paint_flat(g.mask(polys=[self.HP(pts)]), (220, 230, 255), 0.12)
            g.line(self.HP([(0.59, 0.1), (0.64, 0.1)]), w, fc, clip_to_group=False)
            g.line(self.HP([(0.09, 0.1), (-0.25, 0.14)]), w, fc, clip_to_group=False)
        g.commit()

    # ================================================================== extras
    def extras_front(self):
        L, s, b = self.L, self.s, self.b
        ex = L.spec.get('extras', ())
        self._wearables(ex)
        if 'chain' in ex:
            g = self.cv.group(inner_line=True)
            d = self.drag('chain', 1.0)
            a = add(add(s.hip, mul(s.up, 1.8)), mul(s.pfwd, b['hip'] * 0.55))
            c = add(add(s.hip, mul(s.up, 1.4)), mul(s.pfwd, -b['hip'] * 0.95))
            mid = add(lerp(a, c, 0.5), (d[0] * 0.8, 3.2 + d[1] * 0.6))
            pts = catmull([a, mid, c], closed=False, steps=6)
            for i in range(0, len(pts) - 1):
                p0, p1 = pts[i], pts[i + 1]
                cc = lerp(p0, p1, 0.5)
                ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                vert = i % 2 == 1
                rr = (0.62, 0.36) if not vert else (0.55, 0.22)
                m = g.mask(polys=[ellipse_pts(cc[0], cc[1], rr[0], rr[1], ang, n=14)])
                g.fill(m, METAL, shade=0.12, hi=0.08)
            g.commit()
        if 'goldchain' in ex:
            g = self.cv.group(inner_line=False)
            pts = [add(add(s.neck_base, mul(s.fwd, -1.0)), mul(s.up, -0.4)), add(add(s.neck_base, mul(s.fwd, 1.2)), mul(s.up, -2.6)),
                   add(add(s.neck_base, mul(s.fwd, 2.4)), mul(s.up, -0.6))]
            g.line(catmull(pts, False, 4), 1.2, GOLD.base, 1.0, clip_to_group=False)
            g.commit()

    def _wearables(self, ex):
        L, s, b = self.L, self.s, self.b
        N, up, fwd = s.neck_base, s.up, s.fwd

        def at(u, v):
            return add(add(N, mul(up, -u)), mul(fwd, v))
        tm = None
        for e in ex:
            name, _, col = e.partition(':')
            if name in ('bag', 'newsbag'):
                bm = cloth(col) if col else Mat((196, 168, 120))
                if name == 'newsbag':
                    bm = Mat((214, 196, 160))
                g = self.cv.group()
                g.line([at(0.6, 1.2), at(6.5, -1.0), add(add(s.hip, mul(up, 1.0)), mul(s.pfwd, -b['hip'] * 0.9))],
                       1.4, bm.shadow, 1.0, clip_to_group=False)
                c = add(add(s.hip, mul(up, 0.6)), mul(s.pfwd, -b['hip'] * 1.05))
                bag = [add(c, (-2.6, -2.0)), add(c, (2.0, -2.0)), add(c, (2.4, 2.6)), add(c, (-2.8, 2.6))]
                g.fill(g.mask(polys=[catmull(bag, True, 2)]), bm, shade=0.7, hi=0.3)
                g.line([add(c, (-2.6, -0.6)), add(c, (2.1, -0.6))], 0.8, bm.shadow, 0.9)
                if name == 'newsbag':
                    g.paint_flat(g.mask(polys=[[add(c, (-1.8, -3.4)), add(c, (1.4, -3.4)), add(c, (1.4, -1.6)), add(c, (-1.8, -1.6))]]),
                                 (236, 232, 222))
                g.commit()
            elif name == 'suspenders':
                g = self.cv.group(inner_line=False)
                sm = cloth(col) if col else cloth('brown')
                for v in (b['chest'] - 1.6, -1.2):
                    g.line([at(0.4, v * 0.6), at(4.0, v), add(add(s.hip, mul(up, 2.6)), mul(fwd, v * 0.9))], 1.1, sm.base, 1.0,
                           clip_to_group=False)
                g.img_col *= (self.cv.a[..., None] > 0.5)
                g.img_a *= (self.cv.a > 0.5)
                g.commit()
            elif name in ('tie', 'bowtie', 'badge', 'whistle', 'nametag', 'vest_over'):
                g = self.cv.group()
                tc = cloth(col) if col else None
                if name == 'tie':
                    pts = [at(0.6, b['chest'] - 1.4), at(0.9, b['chest'] - 0.4), at(8.5, b['chest'] - 0.2),
                           at(9.4, b['chest'] - 1.0), at(8.5, b['chest'] - 1.8)]
                    g.fill(g.mask(polys=[pts]), tc, shade=0.3, hi=0.2)
                elif name == 'bowtie':
                    c = at(0.6, b['chest'] - 0.6)
                    g.fill(g.mask(polys=[[add(c, (-1.4, -0.9)), add(c, (1.4, 0.9)), add(c, (1.4, -0.9)), add(c, (-1.4, 0.9))]]), tc,
                           shade=0.2, hi=0.2)
                elif name == 'badge':
                    c = at(4.0, b['chest'] - 2.0)
                    g.fill(g.mask(polys=[ellipse_pts(c[0], c[1], 0.9, 1.1, 0, 12)]), GOLD, shade=0.2, hi=0.2)
                elif name == 'whistle':
                    g.line([at(0.2, -0.6), at(4.6, b['chest'] - 1.6), at(0.2, b['chest'] - 1.0)], 0.7, (220, 220, 230), 1.0,
                           clip_to_group=False)
                    c = at(4.8, b['chest'] - 1.4)
                    g.fill(g.mask(polys=[ellipse_pts(c[0], c[1], 0.9, 0.6, 0, 12)]), METAL, shade=0.2, hi=0.2)
                elif name == 'nametag':
                    c = at(4.2, b['chest'] - 2.2)
                    g.fill(g.mask(polys=[[add(c, (-1.2, -0.7)), add(c, (1.2, -0.7)), add(c, (1.2, 0.7)), add(c, (-1.2, 0.7))]]),
                           Mat((244, 244, 238)), shade=0.2, hi=0.0)
                    g.line([add(c, (-0.7, 0.0)), add(c, (0.7, 0.0))], 0.6, (60, 60, 120), 1.0)
                elif name == 'vest_over':
                    vm = cloth('orange')
                    tp = self.torso_points(expand=0.3)
                    m = g.mask(polys=[tp]) * g.mask(polys=[self.halfplane(add(s.hip, mul(up, 3.0)), up)]) * \
                        g.mask(polys=[self.halfplane(add(N, mul(up, -1.8)), mul(up, -1))])
                    g.fill(m, vm, shade=1.0, hi=0.3)
                    o = add(s.hip, mul(up, 7.0))
                    band = g.mask(polys=[self.halfplane(o, up)]) * g.mask(polys=[self.halfplane(add(o, mul(up, -0.9)), mul(up, -1))])
                    g.paint_flat(band * (g.img_a > 0.5), (236, 236, 214))
                g.commit()
        if L.spec.get('shawl'):
            g = self.cv.group()
            sm = cloth(L.spec['shawl'])
            pts = [at(-0.6, -b['back'] - 0.6), at(-0.4, b['chest'] * 0.4), at(1.6, b['chest'] + 0.6),
                   at(6.0, b['chest'] - 0.4), at(5.0, -b['back'] * 0.2), at(6.6, -b['back'] - 0.8)]
            g.fill(g.mask(polys=[catmull(pts, True, 3)]), sm, shade=0.9, hi=0.3)
            g.line([at(1.8, b['chest'] - 1.0), at(5.4, b['chest'] - 1.6)], 0.8, sm.shadow, 0.9)
            g.commit()

    def held_extras(self):
        L, s = self.L, self.s
        ex = L.spec.get('extras', ())
        h = s.fist_f
        if 'cane' in ex and abs(s.lean) < 45:
            g = self.cv.group()
            g.fill(g.mask(polys=[seg_quad((h[0] + 0.4, h[1] - 0.6), (h[0] + 1.6, -0.2), 0.42, 0.38)],
                          circles=[(h[0] - 0.4, h[1] - 0.8, 0.9)]), Mat((110, 72, 44)), shade=0.3, hi=0.2)
            g.commit()
        if 'briefcase' in ex and h[1] > s.hip[1] - 6 and abs(s.lean) < 45:
            g = self.cv.group()
            case = [(h[0] - 3.2, h[1] + 0.8), (h[0] + 3.0, h[1] + 0.8), (h[0] + 3.0, h[1] + 5.4), (h[0] - 3.2, h[1] + 5.4)]
            g.fill(g.mask(polys=[case]), Mat((96, 60, 40)), shade=0.6, hi=0.3)
            g.line([(h[0] - 0.8, h[1] + 0.8), (h[0] - 0.8, h[1] - 0.2), (h[0] + 0.8, h[1] - 0.2), (h[0] + 0.8, h[1] + 0.8)], 0.8,
                   (60, 40, 30), 1.0, clip_to_group=False)
            g.paint_flat(g.mask(circles=[(h[0], h[1] + 2.0, 0.3)]), (230, 200, 90))
            g.commit()
        if 'grocery' in ex and s.fist_f[1] > s.hip[1] - 6 and abs(s.lean) < 45:
            g = self.cv.group()
            h = s.fist_f
            bag = [(h[0] - 2.6, h[1] + 0.2), (h[0] + 2.4, h[1] + 0.2), (h[0] + 2.8, h[1] + 7.2), (h[0] - 2.9, h[1] + 7.2)]
            g.fill(g.mask(polys=[bag]), Mat((196, 160, 112), (150, 112, 74), (226, 200, 160)), shade=0.9, hi=0.3)
            g.fill(g.mask(polys=[ellipse_pts(h[0] - 0.8, h[1] - 0.4, 1.2, 1.0, 0, 12)]), Mat((90, 170, 70)), shade=0.3, hi=0.2)
            g.fill(g.mask(polys=[[(h[0] + 0.6, h[1] - 2.4), (h[0] + 1.6, h[1] - 2.4), (h[0] + 1.6, h[1] + 0.5), (h[0] + 0.6, h[1] + 0.5)]]),
                   Mat((240, 236, 226)), shade=0.3, hi=0.0)
            g.line([(h[0] - 2.6, h[1] + 1.0), (h[0] + 2.5, h[1] + 1.0)], 0.8, (150, 112, 74))
            g.commit()


# ============================================================================= custom hair (refined styles)
# Each returns list of (points_in_head_local, opts); drag d is in head-local units (R).

def _spiky(d):
    k = 0.32
    parts = [(ellipse_pts(-0.1, -0.28, 1.1, 0.86, 0, 40), {})]
    spikes = [
        [(-0.70, -0.40), (-1.62 + d[0] * k, -0.66 + d[1] * k), (-0.92, -0.02)],
        [(-0.72, -0.62), (-1.30 + d[0] * k, -1.36 + d[1] * k), (-0.18, -0.86)],
        [(-0.38, -0.86), (-0.14 + d[0] * k * 0.8, -1.62 + d[1] * k * 0.8), (0.26, -0.86)],
        [(0.06, -0.86), (0.80 + d[0] * k * 0.7, -1.40 + d[1] * k * 0.7), (0.66, -0.60)],
        [(0.30, -0.72), (1.24 + d[0] * k * 0.4, -0.80 + d[1] * k * 0.4), (0.70, -0.32)],
        [(-0.92, -0.10), (-1.48 + d[0] * k, 0.24 + d[1] * k), (-0.84, 0.36)],
    ]
    for i, sp in enumerate(spikes):
        parts.append((sp, {'sub': True, 'face': i == 4}))
    # bangs over the forehead
    parts.append(([(0.25, -0.62), (0.92, -0.58), (0.62, -0.24), (0.42, -0.44), (0.30, -0.18), (0.10, -0.50)], {'face': True}))
    return parts


def _spikes_up(d):
    k = 0.3
    parts = [(ellipse_pts(-0.1, -0.3, 1.08, 0.84, 0, 40), {})]
    for i, x in enumerate([-0.88, -0.48, -0.06, 0.36]):
        tipx = x + 0.05 - 0.12 * i + d[0] * k
        tipy = -1.7 + 0.08 * abs(i - 1.5) + d[1] * k * 0.5
        parts.append(([(x - 0.3, -0.7), (tipx, tipy), (x + 0.32, -0.72)], {'sub': True}))
    parts.append(([(0.3, -0.62), (0.95, -0.55), (0.6, -0.3), (0.35, -0.4)], {'face': True}))
    return parts


def _mohawk(d, low=False):
    k = 0.18
    parts = [(ellipse_pts(-0.08, -0.25, 1.02, 0.78, 0, 40), {'shaved': True})]
    h = 0.55 if low else 1.0
    crest = [(0.45, -0.82), (0.42, -0.82 - 0.95 * h + d[1] * k), (0.0 + d[0] * k, -0.85 - 1.0 * h + d[1] * k),
             (-0.55 + d[0] * k, -0.8 - 0.95 * h + d[1] * k), (-1.05 + d[0] * k * 1.3, -0.7 - 0.75 * h + d[1] * k),
             (-1.42 + d[0] * k * 1.5, -0.3 - 0.4 * h), (-1.0, -0.42), (-0.4, -0.88)]
    parts.append((crest, {'sub': False}))
    # crest spikes (serrated top edge)
    for i, x in enumerate((0.35, -0.05, -0.5, -0.95)):
        top = -0.85 - 1.0 * h * (1.0 - 0.12 * i)
        parts.append(([(x - 0.18, top + 0.25), (x + 0.15 + d[0] * k, top - 0.18 + d[1] * k), (x + 0.22, top + 0.3)], {'sub': True}))
    return parts


def _beehive(d):
    return [(ellipse_pts(-0.12, -0.32, 1.06, 0.82, 0, 40), {}),
            (ellipse_pts(-0.12, -1.12, 0.80, 0.84, 0, 40), {'sub': True}),
            (ellipse_pts(-0.08, -1.78, 0.48, 0.40, 0, 30), {'sub': True}),
            ([(0.30, -0.7), (0.95, -0.55), (0.75, -0.30), (0.42, -0.40)], {'face': True}),
            (ellipse_pts(-0.85, -0.05, 0.36, 0.42, 0, 24), {})]


def _short(d):
    return [(ellipse_pts(-0.1, -0.30, 1.08, 0.84, 0, 40), {}),
            ([(-0.2, -0.98), (0.98, -0.62), (0.88, -0.34), (0.42, -0.42), (0.1, -0.5)], {'face': True}),
            (ellipse_pts(-0.58, -0.06, 0.44, 0.44, 0, 24), {})]


def _long_front(d):
    k = 0.25
    return [(ellipse_pts(-0.1, -0.3, 1.12, 0.9, 0, 40), {}),
            ([(-0.15, -1.02), (1.02, -0.62), (0.92, -0.30), (0.5, -0.42), (-0.05, -0.55)], {'face': True}),
            ([(-1.14, -0.3), (-1.22 + d[0] * k, 0.98 + d[1] * k), (-0.28 + d[0] * k, 1.0 + d[1] * k), (-0.15, -0.3)],
             {'sub': True})]


def _long_back(d):
    k = 0.45
    return [[(-1.2, -0.1), (-1.42 + d[0] * k, 1.6 + d[1] * k), (-0.9 + d[0] * k, 2.05 + d[1] * k),
             (-0.25 + d[0] * k * 0.7, 1.65 + d[1] * k), (-0.3, 0.2)]]


CUSTOM_FRONT = {
    'spiky': _spiky, 'spikes_up': _spikes_up, 'mohawk': _mohawk, 'mohawk_low': lambda d: _mohawk(d, True),
    'beehive': _beehive, 'short': _short, 'long': _long_front,
}
CUSTOM_BACK = {'long': _long_back}
