#!/usr/bin/env python3
"""BACKSTREET OATH -- procedural character sprite / portrait generator.

Renders every humanoid sprite sheet (8x8 grid of 64x64 cells, 58 frames in the
art-bible order), its JSON sidecar (anims + front-hand grip points), the dog
Biscuit, and 64x64 portrait strips (5 expressions) with a parametric
"paper-doll" renderer: a skeleton per body type, a pose table driving joint
angles, parts rasterised as solid pixel shapes with two-tone shading, internal
ink contours and a final 1px #1a1220 silhouette outline.

Deterministic: no randomness, no downloads. Python 3 + Pillow + numpy only.
All designs are original and project-owned.

Usage:  python3 tools/art/gen_characters.py [--only id1,id2] [--preview DIR]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_SPR = os.path.join(ROOT, 'game', 'assets', 'sprites', 'characters')
OUT_POR = os.path.join(ROOT, 'game', 'assets', 'portraits')
OUT_DOC = os.path.join(ROOT, 'docs', 'assets', 'CHARACTER_ASSETS.md')

# =============================================================================
# Colours
# =============================================================================


def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


INK = hx('#1a1220')
AUTO_HI = True
WHITE_PX = hx('#f4f0e8')
SHADOW_TGT = (44, 24, 64)          # hue-shifted shadow target (cool purple)
LIGHT_TGT = (255, 246, 226)        # warm highlight target


def mat(base, shadow=None):
    """Material = (base, shadow, highlight, deep)."""
    b = hx(base) if isinstance(base, str) else base
    if shadow is None:
        s = mix(b, SHADOW_TGT, 0.38)
    else:
        s = hx(shadow) if isinstance(shadow, str) else shadow
    h = mix(b, LIGHT_TGT, 0.28)
    d = mix(s, SHADOW_TGT, 0.42)
    return (b, s, h, d)


def far(m):
    """Darker version of a material for far-side limbs."""
    b, s, h, d = m
    return (mix(b, s, 0.72), mix(s, SHADOW_TGT, 0.30), b, mix(d, INK, 0.3))


SKIN = {
    'light': mat('#f5c9a0', '#d9a07a'),
    'tan': mat('#d9a07a', '#b07850'),
    'medium': mat('#c68858', '#9a6440'),
    'deep': mat('#8a5a3a', '#5e3a26'),
}

HAIR = {
    'black': '#2a1e24', 'brown': '#6a4028', 'auburn': '#9a4a2a', 'blonde': '#e8c060',
    'platinum': '#e8e4dc', 'gray': '#a8a0a0', 'red': '#c03a2a', 'pink': '#e06090',
    'white': '#f0ece4', 'darkbrown': '#4a2c20', 'cyan': '#4ac8d0', 'purple': '#7a4aa0',
}

C = {
    'red': mat('#c03a3a', '#7a2030'), 'orange': mat('#e07a30', '#a0501e'),
    'mustard': mat('#e0b040', '#a87a20'), 'yellow': mat('#f0c040', '#b88a20'),
    'green': mat('#4a9a4a', '#2a5a3a'), 'teal': mat('#3a9a9a', '#22605e'),
    'blue': mat('#3a6ac0', '#22408a'), 'navy': mat('#22305a', '#141c38'),
    'purple': mat('#7a4aa0', '#4a2a6a'), 'gray': mat('#8a8a96', '#5a5a66'),
    'charcoal': mat('#3a3a46', '#24242e'), 'white': mat('#e8e4dc', '#b8b0a8'),
    'denim': mat('#4a6a9a', '#30476e'), 'brown': mat('#7a5030', '#50341e'),
    'tan': mat('#c8a070', '#987048'), 'black': mat('#2a2a32', '#18181e'),
    'neon': mat('#7af04a', '#3aa02a'), 'pink': mat('#e888a8', '#b05878'),
    'burgundy': mat('#7a2a3a', '#4a1624'), 'olive': mat('#7a7a3a', '#4e4e22'),
    'khaki': mat('#b8a878', '#867850'), 'cyan': mat('#4ac8d0', '#2a8090'),
    'lightgray': mat('#b8b8c0', '#86868e'), 'cream': mat('#efe2c0', '#c0ae88'),
    'steel': mat('#9aa2b0', '#6a7280'), 'gold': mat('#f0c850', '#b08a28'),
    'rubbergreen': mat('#3a7a4a', '#22502e'), 'darkred': mat('#8a2a2a', '#561820'),
    'leather': mat('#2e2630', '#1a141c'), 'satinpurple': mat('#8a50b8', '#542c7a'),
    'satincyan': mat('#4ad0d8', '#2a8a96'), 'floral': mat('#a070b8', '#6a4880'),
    'maroon': mat('#6a2a3a', '#401824'), 'skyblue': mat('#7ab0e0', '#4a78aa'),
    'lilac': mat('#b090d0', '#7a5aa0'), 'sand': mat('#d8c090', '#a89060'),
    'checker': mat('#e8e4dc', '#b8b0a8'), 'darkbrown': mat('#5a3a24', '#3a2416'),
}
MOUTH_DARK = hx('#5a1a26')
TONGUE = hx('#c84a52')
EYE_W = hx('#f4f0ec')

# =============================================================================
# Raster helpers
# =============================================================================


class Grid:
    _cache = {}

    def __init__(self, h, w):
        key = (h, w)
        if key not in Grid._cache:
            Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
            Grid._cache[key] = (X + 0.5, Y + 0.5)
        self.X, self.Y = Grid._cache[key]
        self.h, self.w = h, w

    def uv(self, ox, oy, ang_deg):
        a = math.radians(ang_deg)
        c, s = math.cos(a), math.sin(a)
        dx = self.X - ox
        dy = self.Y - oy
        return dx * c + dy * s, -dx * s + dy * c

    def ell(self, cx, cy, rx, ry, ang=0.0):
        if ang:
            u, v = self.uv(cx, cy, ang)
        else:
            u, v = self.X - cx, self.Y - cy
        return (u / max(rx, 0.01)) ** 2 + (v / max(ry, 0.01)) ** 2 <= 1.0

    def cap(self, x0, y0, x1, y1, r):
        vx, vy = x1 - x0, y1 - y0
        L2 = vx * vx + vy * vy
        if L2 < 1e-6:
            return (self.X - x0) ** 2 + (self.Y - y0) ** 2 <= r * r
        t = np.clip(((self.X - x0) * vx + (self.Y - y0) * vy) / L2, 0.0, 1.0)
        px = x0 + t * vx
        py = y0 + t * vy
        return (self.X - px) ** 2 + (self.Y - py) ** 2 <= r * r

    def poly(self, pts):
        return inpoly(self.X, self.Y, pts)

    def rect(self, x0, y0, x1, y1):
        """Pixel-index rectangle, inclusive."""
        m = np.zeros((self.h, self.w), bool)
        x0, x1 = max(0, int(x0)), min(self.w - 1, int(x1))
        y0, y1 = max(0, int(y0)), min(self.h - 1, int(y1))
        if x1 >= x0 and y1 >= y0:
            m[y0:y1 + 1, x0:x1 + 1] = True
        return m


def inpoly(X, Y, pts):
    inside = np.zeros(X.shape, bool)
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if y0 == y1:
            continue
        cond = (y0 > Y) != (y1 > Y)
        xint = (x1 - x0) * (Y - y0) / (y1 - y0) + x0
        inside ^= cond & (X < xint)
    return inside


def shift(m, dx, dy):
    """r[y, x] = m[y+dy, x+dx] (False outside)."""
    h, w = m.shape
    r = np.zeros_like(m)
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    if ys1 > ys0 and xs1 > xs0:
        r[ys0:ys1, xs0:xs1] = m[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
    return r


def dil4(m):
    return m | shift(m, 1, 0) | shift(m, -1, 0) | shift(m, 0, 1) | shift(m, 0, -1)


def dil8(m):
    r = dil4(m)
    return r | shift(m, 1, 1) | shift(m, -1, 1) | shift(m, 1, -1) | shift(m, -1, -1)


def ero4(m):
    return m & shift(m, 1, 0) & shift(m, -1, 0) & shift(m, 0, 1) & shift(m, 0, -1)


class Canvas:
    def __init__(self, h, w):
        self.g = Grid(h, w)
        self.h, self.w = h, w
        self.rgb = np.zeros((h, w, 3), np.uint8)
        self.a = np.zeros((h, w), bool)
        self.pid = np.zeros((h, w), np.int16)
        self.sh = np.zeros((h, w, 3), np.uint8)

    def ring(self, mask, over, color=INK):
        if not over:
            return
        r = dil4(mask) & ~mask & self.a & np.isin(self.pid, list(over))
        self.rgb[r] = color
        self.sh[r] = color
        self.pid[r] = -1

    def fill(self, mask, m, pid=0, k=1, hi=False, ring=None, flat=False, rimk=None):
        """Paint mask with material m=(base, shadow, hi, deep), lower-right rim shading."""
        if not mask.any():
            return
        if ring:
            self.ring(mask, ring)
        b, s, h, d = m
        self.rgb[mask] = b
        if not hi and AUTO_HI and (b[0] * 0.3 + b[1] * 0.59 + b[2] * 0.11) < 70 and k > 0:
            hi = True
        if not flat and k > 0:
            kx, ky = (k, k) if rimk is None else rimk
            rim = mask & ~shift(mask, kx, ky)
            self.rgb[rim] = s
            if hi:
                hl = mask & ~shift(mask, -1, -1) & ~rim
                self.rgb[hl] = h
        self.a |= mask
        self.pid[mask] = pid
        self.sh[mask] = s

    def solid(self, mask, color, pid=None):
        if not mask.any():
            return
        self.rgb[mask] = color
        self.a |= mask
        if pid is not None:
            self.pid[mask] = pid

    def px(self, x, y, color, pid=None):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.rgb[y, x] = color
            self.a[y, x] = True
            if pid is not None:
                self.pid[y, x] = pid

    def blit(self, other_rgb, other_a, other_sh, ox, oy, pid, ring=None):
        """Composite a buffer at offset (ox, oy) with ring over listed pids."""
        h, w = other_a.shape
        m = np.zeros((self.h, self.w), bool)
        rgb = np.zeros((self.h, self.w, 3), np.uint8)
        shd = np.zeros((self.h, self.w, 3), np.uint8)
        x0, y0 = ox, oy
        sx0, sy0 = max(0, -x0), max(0, -y0)
        dx0, dy0 = max(0, x0), max(0, y0)
        cw = min(w - sx0, self.w - dx0)
        chh = min(h - sy0, self.h - dy0)
        if cw <= 0 or chh <= 0:
            return
        m[dy0:dy0 + chh, dx0:dx0 + cw] = other_a[sy0:sy0 + chh, sx0:sx0 + cw]
        rgb[dy0:dy0 + chh, dx0:dx0 + cw] = other_rgb[sy0:sy0 + chh, sx0:sx0 + cw]
        shd[dy0:dy0 + chh, dx0:dx0 + cw] = other_sh[sy0:sy0 + chh, sx0:sx0 + cw]
        if ring:
            self.ring(m, ring)
        self.rgb[m] = rgb[m]
        self.sh[m] = shd[m]
        self.a |= m
        self.pid[m] = pid

    def outline(self, color=INK):
        o = dil4(self.a) & ~self.a
        self.rgb[o] = color
        self.a |= o

    def to_rgba(self):
        out = np.zeros((self.h, self.w, 4), np.uint8)
        out[..., :3] = self.rgb
        out[..., 3] = np.where(self.a, 255, 0)
        return out


def V(a):
    r = math.radians(a)
    return np.array([math.cos(r), math.sin(r)])


# =============================================================================
# Body types
# =============================================================================

BODY = {
    #            head   torso  shoulders waist  legs        arms        widths
    'normal': dict(R=8.0, T=12.5, Ws=13, Ww=11, thigh=6.0, shin=6.0, ua=5.0, fa=5.5,
                   aw=4.6, fw=4.2, fist=2.2, tw=5.6, sw=5.0, foot=1.0, belly=0, stoop=0,
                   shf=1.5, shb=-2.5, nk=0),
    'slim': dict(R=8.0, T=12.5, Ws=11, Ww=9, thigh=6.0, shin=6.0, ua=5.0, fa=5.5,
                 aw=3.8, fw=3.6, fist=2.1, tw=5.0, sw=4.4, foot=0.95, belly=0, stoop=0,
                 shf=1.0, shb=-2.0, nk=0),
    'heavy': dict(R=8.5, T=13.0, Ws=16, Ww=16, thigh=6.0, shin=6.0, ua=5.0, fa=5.5,
                  aw=5.2, fw=4.8, fist=2.6, tw=6.6, sw=5.8, foot=1.08, belly=10, stoop=0,
                  shf=2.0, shb=-3.5, nk=0),
    'big': dict(R=9.0, T=16.5, Ws=21, Ww=16, thigh=7.5, shin=7.0, ua=7.0, fa=7.0,
                aw=6.4, fw=6.2, fist=3.6, tw=7.6, sw=7.0, foot=1.25, belly=6, stoop=0,
                shf=2.5, shb=-5.0, nk=0),
    'tall': dict(R=8.0, T=15.5, Ws=14, Ww=11, thigh=7.5, shin=7.5, ua=6.0, fa=6.5,
                 aw=4.4, fw=4.0, fist=2.3, tw=5.6, sw=5.0, foot=1.05, belly=0, stoop=0,
                 shf=1.5, shb=-2.5, nk=0),
    'kid': dict(R=7.5, T=9.0, Ws=10, Ww=9, thigh=4.5, shin=4.5, ua=4.0, fa=4.0,
                aw=3.6, fw=3.4, fist=1.9, tw=4.6, sw=4.2, foot=0.85, belly=0, stoop=0,
                shf=1.0, shb=-2.0, nk=0),
    'elder': dict(R=8.0, T=12.0, Ws=12, Ww=11, thigh=5.5, shin=5.5, ua=4.8, fa=5.0,
                  aw=4.0, fw=3.8, fist=2.0, tw=5.2, sw=4.6, foot=0.95, belly=3, stoop=9,
                  shf=1.5, shb=-2.5, nk=1),
}

# =============================================================================
# Poses (58 frames, art-bible order)
# =============================================================================

ANIMS = [
    ('idle', 2), ('walk', 4), ('run', 4), ('punch_a', 2), ('punch_b', 2), ('punch_c', 3),
    ('kick', 3), ('kick_c', 3), ('jump', 2), ('jump_kick', 1), ('jump_punch', 1),
    ('run_punch', 1), ('dropkick', 1), ('guard', 1), ('hurt', 2), ('knockdown', 3),
    ('getup', 2), ('dizzy', 2), ('pickup', 1), ('carry', 2), ('throw', 2), ('swing', 3),
    ('sweep', 2), ('rising_kick', 2), ('slam', 1), ('victory', 2), ('talk', 2), ('cower', 2),
]


def anim_table():
    out = {}
    i = 0
    for name, n in ANIMS:
        out[name] = [i, n]
        i += n
    assert i == 58
    return out


def P(**kw):
    d = dict(lean=5, bx=0, bob=0, air=0,
             fa=(55, -75), ba=(80, -105), fl=(68, 98), bl=(115, 100),
             head=(0, 0), hrot=0, expr='normal', fh='fist', bh='fist', wang=-55,
             ff=None, bf=None, view='front', center=False, arm_scale=1.0,
             carry=False, leg_scale=1.0, twist=0.0)
    d.update(kw)
    return d


def fighter_poses():
    F = []
    # 0-1 idle
    F.append(P(lean=6, fa=(56, -30), ba=(30, -58), fl=(66, 100), bl=(116, 98), wang=-55,
               twist=0.4))
    F.append(P(lean=6, bob=1, fa=(60, -26), ba=(34, -54), fl=(66, 100), bl=(116, 98), wang=-50,
               twist=0.4))
    # 2-5 walk  contact / pass / contact / pass
    F.append(P(lean=7, fl=(56, 78), bl=(120, 122), fa=(70, -30), ba=(58, -100), wang=-40))
    F.append(P(lean=7, fl=(86, 94), bl=(98, 140), fa=(58, -36), ba=(66, -98), wang=-48, air=0))
    F.append(P(lean=7, fl=(120, 122), bl=(56, 78), fa=(42, -44), ba=(78, -96), wang=-58))
    F.append(P(lean=7, fl=(98, 140), bl=(86, 94), fa=(52, -40), ba=(70, -98), wang=-50))
    # 6-9 run
    F.append(P(lean=20, fl=(40, 72), bl=(132, 168), fa=(122, 40), ba=(30, -62), wang=20,
               expr='determined'))
    F.append(P(lean=20, fl=(88, 104), bl=(30, 118), fa=(88, -10), ba=(80, -40), wang=-20,
               expr='determined'))
    F.append(P(lean=20, fl=(132, 168), bl=(40, 72), fa=(32, -60), ba=(120, 40), wang=-50,
               expr='determined'))
    F.append(P(lean=20, fl=(30, 118), bl=(88, 104), fa=(70, -40), ba=(90, -5), wang=-30,
               expr='determined'))
    # 10-11 punch_a (jab, near arm)
    F.append(P(lean=0, bx=-1, fa=(108, -62), ba=(80, -112), fl=(64, 96), bl=(118, 100),
               expr='determined', wang=-70))
    F.append(P(lean=12, bx=2, fa=(-2, -1), ba=(86, -116), fl=(54, 84), bl=(124, 108),
               expr='shout', wang=0))
    # 12-13 punch_b (cross, far arm)
    F.append(P(lean=-3, bx=-1, fa=(50, -82), ba=(128, -40), fl=(64, 96), bl=(118, 100),
               expr='determined', wang=-80))
    F.append(P(lean=18, bx=2, fa=(100, -100), ba=(6, 4), fl=(50, 80), bl=(126, 114),
               expr='shout', wang=-85, twist=1.0))
    # 14-16 punch_c (uppercut finisher)
    F.append(P(lean=22, bx=-1, fl=(40, 112), bl=(132, 106), fa=(112, 40), ba=(66, -104),
               expr='determined', wang=60))
    F.append(P(lean=-6, bx=4, fl=(60, 82), bl=(118, 96), fa=(-30, -58), ba=(104, -50),
               expr='shout', wang=-62))
    F.append(P(lean=-10, bx=3, fl=(66, 88), bl=(112, 96), fa=(-78, -102), ba=(112, -20),
               expr='shout', wang=-100))
    # 17-19 kick
    F.append(P(lean=-6, bx=1, fl=(-6, 96), bl=(100, 94), fa=(62, -82), ba=(82, -112),
               expr='determined', wang=-60))
    F.append(P(lean=-16, bx=5, fl=(-3, -3), bl=(108, 96), fa=(150, 112), ba=(74, -106),
               expr='shout', wang=150, ff=-3))
    F.append(P(lean=-6, bx=2, fl=(32, 116), bl=(100, 94), fa=(62, -82), ba=(82, -112),
               expr='determined', wang=-60))
    # 20-22 kick_c (roundhouse)
    F.append(P(view='back', lean=4, bx=-1, fl=(100, 96), bl=(24, 120), fa=(100, -70),
               ba=(76, -100), wang=-80))
    F.append(P(lean=-28, bx=4, fl=(-34, -36), bl=(106, 96), fa=(168, 150), ba=(130, 175),
               expr='shout', wang=165, ff=-36))
    F.append(P(lean=-6, bx=2, fl=(44, 106), bl=(100, 94), fa=(70, -72), ba=(86, -110),
               expr='determined', wang=-55))
    # 23-24 jump
    F.append(P(lean=4, fl=(12, 106), bl=(36, 128), fa=(30, -62), ba=(60, -92), wang=-50,
               expr='determined'))
    F.append(P(lean=2, fl=(80, 92), bl=(102, 104), fa=(30, -24), ba=(-40, -70), wang=-30))
    # 25 jump_kick
    F.append(P(lean=-12, fl=(30, 30), bl=(62, 156), fa=(150, 104), ba=(62, -100), wang=150,
               expr='shout', ff=30))
    # 26 jump_punch
    F.append(P(lean=34, fl=(128, 62), bl=(150, 84), fa=(48, 48), ba=(150, 100), wang=50,
               expr='shout'))
    # 27 run_punch
    F.append(P(lean=34, bx=1, fl=(52, 92), bl=(140, 166), fa=(-4, -6), ba=(132, 62), wang=0,
               expr='shout', twist=-0.3))
    # 28 dropkick
    F.append(P(lean=-72, fl=(-22, -18), bl=(-12, -8), fa=(150, 120), ba=(200, 176), hrot=90,
               expr='shout', wang=150, ff=-108, bf=-98, center=True))
    # 29 guard
    F.append(P(lean=6, fl=(56, 112), bl=(126, 104), fa=(30, -96), ba=(14, -80), expr='grit',
               wang=-95))
    # 30-31 hurt
    F.append(P(lean=-18, bx=-2, fl=(74, 96), bl=(120, 100), fa=(168, 132), ba=(-150, -172),
               head=(-1, 0), expr='pain', wang=150))
    F.append(P(lean=40, bx=-1, fl=(64, 112), bl=(120, 110), fa=(92, 10), ba=(74, -10),
               head=(1, 1), expr='pain', wang=80))
    # 32-34 knockdown
    F.append(P(lean=-60, fl=(16, 46), bl=(-6, 30), fa=(-40, -80), ba=(-150, -172), hrot=90,
               expr='pain', wang=-80, center=True))
    F.append(P(lean=-84, fl=(-26, 12), bl=(-42, -12), fa=(-50, -20), ba=(-132, -170),
               hrot=90, expr='pain', wang=-20, center=True))
    F.append(P(lean=-90, fl=(-8, 8), bl=(-3, 4), fa=(14, 4), ba=(196, 186), hrot=90,
               expr='ko', wang=0, center=True, ff=-80, bf=-85, fh='open'))
    # 35-36 getup
    F.append(P(lean=-22, fl=(-14, 30), bl=(-8, 18), fa=(118, 100), ba=(124, 104), fh='open',
               bh='open', expr='daze', wang=90))
    F.append(P(lean=26, fl=(26, 122), bl=(86, 176), fa=(58, 92), ba=(70, 96), expr='daze',
               wang=60, fh='open'))
    # 37-38 dizzy
    F.append(P(lean=-6, bx=-2, fl=(76, 100), bl=(106, 96), fa=(100, 94), ba=(96, 84),
               head=(-1, 1), expr='dizzy', fh='open', bh='open', wang=90))
    F.append(P(lean=10, bx=2, fl=(70, 96), bl=(110, 100), fa=(80, 86), ba=(84, 96),
               head=(1, 1), expr='dizzy', fh='open', bh='open', wang=90))
    # 39 pickup
    F.append(P(lean=42, fl=(32, 122), bl=(108, 150), fa=(72, 92), ba=(82, 96), fh='open',
               bh='open', wang=0))
    # 40-41 carry
    F.append(P(lean=0, fl=(62, 82), bl=(118, 124), fa=(-78, -94), ba=(-100, -88),
               arm_scale=1.4, fh='open', bh='open', carry=True, wang=0, expr='grit'))
    F.append(P(lean=0, fl=(118, 124), bl=(62, 82), fa=(-78, -94), ba=(-100, -88),
               arm_scale=1.4, fh='open', bh='open', carry=True, wang=0, expr='grit', air=0))
    # 42-43 throw
    F.append(P(lean=-14, bx=-2, fl=(60, 92), bl=(118, 110), fa=(-118, -150), ba=(-108, -140),
               expr='determined', wang=-135))
    F.append(P(lean=20, bx=3, fl=(46, 82), bl=(126, 116), fa=(-12, -2), ba=(4, 10),
               expr='shout', wang=-10))
    # 44-46 swing
    F.append(P(lean=-10, bx=-1, fl=(64, 96), bl=(116, 100), fa=(-112, -138), ba=(76, -104),
               expr='determined', wang=-125))
    F.append(P(lean=14, bx=3, fl=(50, 86), bl=(122, 108), fa=(-8, -4), ba=(92, -80),
               expr='shout', wang=-5))
    F.append(P(lean=28, bx=3, fl=(46, 92), bl=(126, 116), fa=(54, 68), ba=(102, -56),
               expr='shout', wang=70))
    # 47-48 sweep
    F.append(P(lean=32, fl=(6, 2), bl=(72, 166), fa=(82, 92), ba=(100, 96), fh='open',
               bh='open', expr='determined', wang=90, ff=-60))
    F.append(P(lean=40, fl=(72, 166), bl=(178, 178), fa=(72, 92), ba=(92, 100), fh='open',
               bh='open', expr='determined', wang=90, bf=40))
    # 49-50 rising kick
    F.append(P(lean=16, fl=(28, 126), bl=(124, 100), fa=(60, -80), ba=(84, -108),
               expr='determined', wang=-60))
    F.append(P(lean=-22, bx=2, fl=(-80, -88), bl=(102, 92), fa=(40, -30), ba=(160, 124),
               expr='shout', wang=-30, ff=-178))
    # 51 slam
    F.append(P(lean=10, fl=(82, 166), bl=(96, 172), fa=(-80, -90), ba=(-86, -96), expr='shout',
               wang=-90))
    # 52-53 victory
    F.append(P(lean=2, fl=(80, 96), bl=(106, 96), fa=(96, -76), ba=(116, 60), expr='happy',
               wang=-80))
    F.append(P(lean=-3, fl=(80, 96), bl=(106, 96), fa=(-84, -88), ba=(116, 60),
               expr='shout_happy', wang=-90))
    # 54-55 talk
    F.append(P(lean=0, fl=(82, 96), bl=(100, 94), fa=(94, 86), ba=(88, 96), expr='neutral',
               fh='fist', wang=90))
    F.append(P(lean=0, fl=(82, 96), bl=(100, 94), fa=(68, -18), ba=(88, 96), fh='open',
               expr='talk', wang=-15))
    # 56-57 cower
    F.append(P(lean=26, fl=(40, 126), bl=(110, 142), fa=(-52, 172), ba=(-70, 182),
               expr='scared', head=(1, 1), wang=170))
    F.append(P(lean=26, bx=1, fl=(40, 126), bl=(110, 142), fa=(-54, 170), ba=(-72, 180),
               expr='scared', head=(1, 0), wang=170))
    assert len(F) == 58
    return F


def civilian_poses():
    """Same table, but relaxed idle/walk/run arms and neutral faces."""
    F = fighter_poses()
    F[0] = P(lean=2, fa=(92, 84), ba=(86, 94), fl=(80, 96), bl=(104, 96), wang=80, expr='normal')
    F[1] = P(lean=2, bob=1, fa=(92, 82), ba=(86, 96), fl=(80, 96), bl=(104, 96), wang=80)
    F[2] = P(lean=4, fl=(58, 80), bl=(120, 122), fa=(118, 92), ba=(62, 70), wang=90)
    F[3] = P(lean=4, fl=(86, 94), bl=(98, 136), fa=(96, 86), ba=(84, 90), wang=90)
    F[4] = P(lean=4, fl=(120, 122), bl=(58, 80), fa=(64, 72), ba=(116, 96), wang=60)
    F[5] = P(lean=4, fl=(98, 136), bl=(86, 94), fa=(88, 84), ba=(96, 90), wang=80)
    F[6] = P(lean=16, fl=(42, 74), bl=(130, 164), fa=(126, 50), ba=(36, -40), wang=50,
             expr='scared')
    F[7] = P(lean=16, fl=(88, 104), bl=(32, 116), fa=(92, 10), ba=(82, -20), wang=20,
             expr='scared')
    F[8] = P(lean=16, fl=(130, 164), bl=(42, 74), fa=(36, -40), ba=(126, 50), wang=-30,
             expr='scared')
    F[9] = P(lean=16, fl=(32, 116), bl=(88, 104), fa=(76, -20), ba=(92, 10), wang=-10,
             expr='scared')
    return F


# =============================================================================
# Character specs
# =============================================================================

DEFAULT = dict(
    body='normal', skin='tan', hair='short', hcol='black', hcol2=None,
    hat=None, band=None, fhair=None, fhcol=None, glasses=None, marks=(),
    face='neutral', shirt='white', sleeves='short', jacket=None,
    overalls=None, apron=None, dress=None, pants='denim', pstyle='long', legs2=None,
    shoes='black', sstyle='sneaker', sole=None, gloves=None, wrist=None, studs=False,
    guards=None, armband=None, extras=(), civilian=False, stripe=None,
    eyecol=None, lashes=False,
)


def J(color, kind='jacket', sleeves='long', open=True, stripe=None, trim=None, length='waist',
      collar=None):
    return dict(color=color, kind=kind, sleeves=sleeves, open=open, stripe=stripe,
                trim=trim, length=length, collar=collar)


def CH(cid, **kw):
    d = dict(DEFAULT)
    d.update(kw)
    d['id'] = cid
    return d


STORY = [
    CH('nico', skin='tan', hair='spiky', hcol='black', band='red', face='determined',
       shirt='white', sleeves='short', jacket=J('mustard', stripe='red'), pants='denim',
       shoes='red', sole='white'),
    CH('mara', skin='deep', hair='puff', hcol='black', hat=('bandana_puff', 'green'),
       face='determined', shirt='white', sleeves='none', overalls='teal', ovstyle='tied',
       pants='teal', shoes='brown', sstyle='boot', marks=('smudge',), lashes=True),
    CH('eli', body='slim', skin='light', hair='wavy', hcol='auburn', glasses='round',
       marks=('freckles',), face='kind', shirt='gray', sleeves='long',
       jacket=J('green', kind='varsity', trim='cream', collar='hood'), pants='khaki',
       shoes='white', sole='lightgray'),
    CH('rook', body='tall', skin='light', hair='slick', hcol='black', hcol2='gray',
       marks=('scar',), face='calm', shirt='burgundy', sleeves='long',
       jacket=J('charcoal', kind='coat', length='long', collar='turtle'), pants='black',
       shoes='black', sstyle='dress', gloves='black'),
    CH('rook_p2', body='tall', skin='light', hair='loose', hcol='black', hcol2='gray',
       marks=('scar',), face='stern', shirt='burgundy', sleeves='rolled', torn=True,
       collar='turtle', pants='black', shoes='black', sstyle='dress', gloves='black'),
    CH('dot', body='elder', skin='light', hair='beehive', hcol='gray', glasses='cateye',
       face='kind', dress='pink', apron='white', shoes='white', sstyle='dress', lashes=True,
       civilian=True, wide=True, legs2='skin'),
    CH('jett', body='slim', skin='light', hair='flattop', hcol='blonde', face='cocky',
       shirt='neon', sleeves='none', jacket=J('purple', sleeves='none'), pants='black',
       pstyle='bike', legs2='gray', shoes='white', sstyle='hightop', wrist='neon'),
    CH('gus', body='heavy', skin='medium', hair='short', hcol='gray', hat=('flatcap', 'brown'),
       fhair='mustache', fhcol='gray', face='kind', shirt='denim', sleeves='long',
       jacket=J('orange', kind='safety', sleeves='none'), pants='brown', shoes='darkbrown',
       sstyle='boot', civilian=True),
    CH('duke', body='heavy', skin='light', hair='mohawk', hcol='red', face='tough',
       shirt='red', sleeves='short', jacket=J('leather', kind='vest', sleeves='none'),
       pants='denim', pstyle='ripped', shoes='black', sstyle='boot', extras=('chain',),
       wrist='black', studs=True),
    CH('rhea', body='tall', skin='tan', hair='braid', hcol='darkbrown', face='determined',
       shirt='yellow', sleeves='long', jacket=J('yellow', kind='slicker'), apron='rubbergreen',
       pants='olive', shoes='rubbergreen', sstyle='rubber', lashes=True),
    CH('lou', body='normal', skin='tan', hair='bob', hcol='darkbrown', face='cocky',
       shirt='orange', sleeves='long', jacket=J('orange', kind='slicker'), apron='rubbergreen',
       pants='olive', shoes='rubbergreen', sstyle='rubber', extras=('bag:brown',), lashes=True),
    CH('otto', body='big', skin='light', hair='bald', hcol='brown', hat=('hardhat', 'yellow'),
       fhair='beard', fhcol='brown', face='tough', shirt='gray', sleeves='rolled',
       extras=('suspenders:brown',), pants='brown', shoes='darkbrown', sstyle='boot',
       gloves='tan'),
    CH('sabine', skin='light', hair='short', hcol='platinum', hat=('cap', 'black'),
       face='stern', shirt='gray', sleeves='long', jacket=J('gray', open=False, collar='high'),
       armband='red', pants='black', shoes='black', sstyle='boot', gloves='black', lashes=True),
    CH('price', skin='medium', hair='ponytail', hcol='darkbrown', hat=('police', 'navy'),
       face='neutral', shirt='navy', sleeves='long', jacket=J('navy', open=False,
       collar='shirt'), pants='navy', shoes='black', sstyle='dress', lashes=True,
       extras=('badge',)),
    CH('hollis', body='elder', skin='light', hair='bald_fringe', hcol='white', glasses='thick',
       face='kind', shirt='white', sleeves='long', jacket=J('brown', kind='cardigan'),
       extras=('bowtie:red',), pants='khaki', shoes='brown', sstyle='dress', civilian=True),
    CH('benny', body='heavy', skin='deep', hair='bald', hcol='gray', fhair='goatee',
       fhcol='gray', face='tough', shirt='red', sleeves='long',
       jacket=J('red', kind='track', open=False, trim='white'), pants='red', shoes='white',
       sole='lightgray', extras=('whistle',), pstyle='track'),
    CH('lacey', body='slim', skin='light', hair='bob', hcol='black', hcol2='pink',
       face='cocky', shirt='black', sleeves='short', jacket=J('denim', kind='jacket',
       collar='shirt', trim='pins'), pants='black', shoes='checker', sstyle='sneaker',
       lashes=True, civilian=True),
    CH('pip', body='kid', skin='tan', hair='short', hcol='brown', hat=('cap_back', 'blue'),
       face='cheerful', shirt='stripe_rw', sleeves='short', pants='denim', pstyle='shorts',
       shoes='red', sole='white', civilian=True),
    CH('alvarez', body='elder', skin='medium', hair='bun', hcol='gray', face='kind',
       dress='floral', shawl='purple', shoes='black', sstyle='dress', lashes=True,
       civilian=True, extras=('cane',), legs2='skin'),
    CH('fong', skin='light', hair='short', hcol='black', band='red', face='cheerful',
       shirt='white', sleeves='long', jacket=J('white', kind='chef', open=False),
       pants='charcoal', shoes='black', civilian=True),
    CH('rosa', skin='medium', hair='curly', hcol='darkbrown', face='kind', shirt='teal',
       sleeves='long', jacket=J('white', kind='labcoat', length='long'), pants='navy',
       shoes='black', sstyle='dress', lashes=True, civilian=True),
    CH('bigmo', body='heavy', skin='deep', hair='short', hcol='black', hat=('fedora', 'tan'),
       glasses='shades', face='cocky', shirt='hawaii', sleeves='short', pants='cream',
       shoes='brown', sstyle='dress', extras=('goldchain',), civilian=True),
    CH('teddy', body='kid', skin='light', hair='short', hcol='auburn', hat=('flatcap', 'gray'),
       marks=('freckles',), face='cheerful', shirt='white', sleeves='long',
       jacket=J('brown', kind='vest', sleeves='none', open=False), pants='brown',
       pstyle='shorts', shoes='brown', extras=('newsbag',), civilian=True),
    CH('hank', body='heavy', skin='tan', hair='short', hcol='brown', hat=('paper', 'white'),
       face='neutral', shirt='white', sleeves='short', apron='cream', apron_stain=True,
       pants='charcoal', shoes='black', civilian=True, fhair='stubble', fhcol='brown'),
    CH('marv', skin='light', hair='combover', hcol='brown', glasses='round', face='neutral',
       shirt='white', sleeves='short', jacket=J('red', kind='vest', sleeves='none'),
       extras=('nametag',), pants='charcoal', shoes='black', sstyle='dress', civilian=True),
    CH('towna', skin='deep', hair='short', hcol='black', band='white', face='cheerful',
       shirt='white', sleeves='long', jacket=J('blue', kind='track', open=False, trim='white'),
       pants='blue', pstyle='track', shoes='white', sole='lightgray', civilian=True),
    CH('townb', skin='light', hair='sidepart', hcol='brown', face='neutral', shirt='white',
       sleeves='long', jacket=J('gray', kind='suit', collar='lapel'), extras=('tie:navy',
       'briefcase'), pants='gray', shoes='black', sstyle='dress', civilian=True),
    CH('townc', body='slim', skin='medium', hair='short', hcol='black', face='neutral',
       shirt='green', sleeves='long', jacket=J('green', kind='hoodie', open=False,
       collar='hood'), pants='denim', shoes='white', sole='lightgray', civilian=True),
    CH('townd', skin='tan', hair='long', hcol='brown', face='kind', shirt='lilac',
       sleeves='long', jacket=J('lilac', kind='cardigan'), dress='navy', shoes='brown',
       sstyle='dress', lashes=True, civilian=True, extras=('grocery',), legs2='skin'),
]

GANG_NAMES = {'dogs': 'Chain Dogs', 'rats': 'Wharf Rats', 'yard': 'Yard Boys',
              'saints': 'Neon Saints', 'grays': 'Gray Jackets'}
ARCH = ['brawler', 'flanker', 'blocker', 'heavy', 'weapon', 'thrower']
ARCH_BODY = {'brawler': 'normal', 'flanker': 'slim', 'blocker': 'normal', 'heavy': 'heavy',
             'weapon': 'normal', 'thrower': 'slim'}


def gang_specs():
    G = []
    # ---- Chain Dogs: black leather + red, spiky hair, mohawks, studs, ripped jeans
    G += [
        CH('dogs_brawler', skin='tan', hair='spiky', hcol='black', face='tough', shirt='red',
           sleeves='short', jacket=J('leather', kind='vest', sleeves='none'), pants='denim',
           pstyle='ripped', shoes='black', sstyle='boot', wrist='black', studs=True),
        CH('dogs_flanker', body='slim', skin='light', hair='spikes_up', hcol='blonde',
           band='red', face='cocky', shirt='red', sleeves='none', pants='black',
           pstyle='ripped', shoes='red', sole='white', wrist='black', studs=True),
        CH('dogs_blocker', skin='medium', hair='flattop', hcol='black', face='tough',
           shirt='red', sleeves='long', jacket=J('leather', open=True), pants='denim',
           pstyle='ripped', shoes='black', sstyle='boot', guards='red', studs=True),
        CH('dogs_heavy', body='heavy', skin='light', hair='mohawk_low', hcol='red',
           fhair='beard', fhcol='brown', face='tough', shirt='black', sleeves='short',
           jacket=J('leather', kind='vest', sleeves='none'), pants='denim', pstyle='ripped',
           shoes='black', sstyle='boot', wrist='black', studs=True),
        CH('dogs_weapon', bulk=True, skin='tan', hair='mohawk', hcol='black', marks=('scar',),
           fhair='stubble', fhcol='black', face='mean', shirt='red', sleeves='short',
           jacket=J('leather', sleeves='rolled'), extras=('chain',), pants='black',
           pstyle='ripped', shoes='black', sstyle='boot', gloves='black', studs=True),
        CH('dogs_thrower', body='slim', skin='deep', hair='spiky', hcol='red', face='cocky',
           shirt='black', sleeves='short', jacket=J('red', kind='vest', sleeves='none'),
           extras=('bag:leather',), pants='denim', pstyle='ripped', shoes='black',
           sstyle='boot', wrist='red', studs=True),
    ]
    # ---- Wharf Rats: yellow/olive rain gear, knit beanies, rubber boots, rolled sleeves
    G += [
        CH('rats_brawler', skin='light', hair='short', hcol='brown', hat=('beanie', 'navy'),
           face='tough', shirt='white', sleeves='short', jacket=J('yellow', kind='slicker',
           sleeves='rolled'), pants='olive', shoes='rubbergreen', sstyle='rubber',
           fhair='stubble', fhcol='brown'),
        CH('rats_flanker', body='slim', skin='tan', hair='short', hcol='black',
           hat=('beanie', 'red'), face='cocky', shirt='gray', sleeves='rolled',
           jacket=J('olive', kind='slicker', sleeves='none'), pants='charcoal',
           shoes='rubbergreen', sstyle='rubber'),
        CH('rats_blocker', skin='medium', hair='short', hcol='black', hat=('beanie', 'gray'),
           face='tough', shirt='navy', sleeves='rolled', jacket=J('olive', kind='slicker',
           sleeves='rolled'), guards='yellow', pants='olive', shoes='black', sstyle='rubber'),
        CH('rats_heavy', body='heavy', skin='light', hair='short', hcol='auburn',
           hat=('beanie', 'charcoal'), fhair='beard', fhcol='auburn', face='tough',
           shirt='stripe_nw', sleeves='rolled', overalls='yellow', pants='yellow',
           shoes='rubbergreen', sstyle='rubber'),
        CH('rats_weapon', bulk=True, skin='tan', hair='short', hcol='black', hat=('beanie', 'black'),
           marks=('scar',), fhair='stubble', fhcol='black', face='mean', shirt='charcoal',
           sleeves='rolled', jacket=J('olive', kind='slicker', sleeves='rolled', length='long'),
           pants='black', shoes='black', sstyle='rubber', gloves='yellow'),
        CH('rats_thrower', body='slim', skin='deep', hair='short', hcol='black',
           hat=('beanie_pom', 'orange'), face='cocky', shirt='white', sleeves='short',
           jacket=J('yellow', kind='slicker', sleeves='rolled'), extras=('bag:tan',),
           pants='olive', shoes='rubbergreen', sstyle='rubber'),
    ]
    # ---- Yard Boys: orange safety vests, hard hats / welding caps, denim overalls, soot
    G += [
        CH('yard_brawler', skin='medium', hair='short', hcol='black', hat=('hardhat', 'yellow'),
           marks=('soot',), face='tough', shirt='white', sleeves='short',
           jacket=J('orange', kind='safety', sleeves='none'), pants='denim', shoes='brown',
           sstyle='boot'),
        CH('yard_flanker', body='slim', skin='light', hair='short', hcol='auburn',
           hat=('weldcap', 'red'), marks=('soot',), face='cocky', shirt='gray',
           sleeves='rolled', jacket=J('orange', kind='safety', sleeves='none'),
           pants='denim', shoes='brown', sstyle='boot'),
        CH('yard_blocker', skin='tan', hair='short', hcol='brown', hat=('hardhat', 'white'),
           marks=('soot',), face='tough', shirt='orange', sleeves='short', overalls='denim',
           pants='denim', guards='brown', shoes='brown', sstyle='boot'),
        CH('yard_heavy', body='heavy', skin='deep', hair='short', hcol='black',
           hat=('hardhat', 'orange'), fhair='beard', fhcol='black', marks=('soot',),
           face='tough', shirt='gray', sleeves='short', overalls='denim', pants='denim',
           shoes='brown', sstyle='boot', extras=('vest_over',)),
        CH('yard_weapon', bulk=True, skin='light', hair='short', hcol='black', hat=('weldcap', 'navy'),
           marks=('soot', 'scar'), fhair='stubble', fhcol='black', face='mean',
           shirt='charcoal', sleeves='rolled', jacket=J('orange', kind='safety', sleeves='none'),
           pants='denim', shoes='black', sstyle='boot', gloves='brown'),
        CH('yard_thrower', body='slim', skin='tan', hair='short', hcol='brown',
           hat=('hardhat', 'yellow'), marks=('soot',), face='cocky', shirt='white',
           sleeves='short', overalls='denim', pants='denim', extras=('bag:brown',),
           shoes='brown', sstyle='boot'),
    ]
    # ---- Neon Saints: purple & cyan satin jackets, shades, pompadours / side-shaves
    G += [
        CH('saints_brawler', skin='light', hair='pompadour', hcol='black', glasses='shades',
           face='cocky', shirt='black', sleeves='short', jacket=J('satinpurple', kind='satin',
           trim='cyan'), pants='black', shoes='white', sole='lightgray'),
        CH('saints_flanker', body='slim', skin='tan', hair='sideshave', hcol='pink',
           face='cocky', shirt='white', sleeves='short', jacket=J('satincyan', kind='satin',
           trim='purple'), pants='black', shoes='white', sole='lightgray'),
        CH('saints_blocker', skin='deep', hair='pompadour', hcol='black', glasses='shades',
           face='tough', shirt='cyan', sleeves='short', jacket=J('satinpurple', kind='satin',
           trim='cyan'), guards='cyan', pants='black', shoes='white', sole='lightgray'),
        CH('saints_heavy', body='heavy', skin='medium', hair='pompadour', hcol='black',
           glasses='shades', face='tough', shirt='white', sleeves='short',
           jacket=J('satinpurple', kind='satin', trim='cyan'), pants='black', shoes='white',
           sole='lightgray', fhair='mustache', fhcol='black'),
        CH('saints_weapon', bulk=True, skin='light', hair='sideshave', hcol='platinum', glasses='shades',
           marks=('scar',), face='mean', shirt='purple', sleeves='short',
           jacket=J('black', kind='satin', trim='cyan', sleeves='rolled'), pants='black',
           shoes='white', sole='lightgray', gloves='black'),
        CH('saints_thrower', body='slim', skin='medium', hair='pompadour', hcol='blonde',
           face='cocky', shirt='black', sleeves='short', jacket=J('satincyan', kind='satin',
           trim='purple'), extras=('bag:purple',), pants='black', shoes='white',
           sole='lightgray'),
    ]
    # ---- Gray Jackets: gray jackets, red armbands, black caps, black pants, stern faces
    G += [
        CH('grays_brawler', skin='light', hair='short', hcol='brown', hat=('cap', 'black'),
           face='stern', shirt='black', sleeves='long', jacket=J('gray', open=False,
           collar='high'), armband='red', pants='black', shoes='black', sstyle='boot'),
        CH('grays_flanker', body='slim', skin='tan', hair='buzz', hcol='black', face='stern',
           shirt='black', sleeves='long', jacket=J('gray', open=False, collar='high'),
           armband='red', pants='black', shoes='black', sstyle='boot'),
        CH('grays_blocker', skin='medium', hair='short', hcol='black', hat=('cap', 'black'),
           face='stern', shirt='black', sleeves='long', jacket=J('gray', open=False,
           collar='high'), armband='red', guards='black', pants='black', shoes='black',
           sstyle='boot'),
        CH('grays_heavy', body='heavy', skin='light', hair='buzz', hcol='gray',
           hat=('cap', 'black'), face='stern', shirt='gray', sleeves='long',
           jacket=J('charcoal', kind='padded', sleeves='none', open=False), armband='red',
           pants='black', shoes='black', sstyle='boot'),
        CH('grays_weapon', bulk=True, skin='deep', hair='short', hcol='black', hat=('cap', 'black'),
           glasses='shades', marks=('scar',), face='mean', shirt='black', sleeves='long',
           jacket=J('gray', open=False, collar='high'), armband='red', gloves='black',
           pants='black', shoes='black', sstyle='boot'),
        CH('grays_thrower', body='slim', skin='light', hair='short', hcol='platinum',
           hat=('cap', 'black'), face='stern', shirt='black', sleeves='long',
           jacket=J('gray', open=False, collar='high'), armband='red',
           extras=('bag:lightgray',), pants='black', shoes='black', sstyle='boot'),
    ]
    return G


ALL_CHARS = STORY + gang_specs()
CHAR_BY_ID = {c['id']: c for c in ALL_CHARS}
PORTRAIT_IDS = ['nico', 'mara', 'eli', 'rook', 'dot', 'jett', 'gus', 'duke', 'rhea', 'lou',
                'otto', 'sabine', 'price', 'hollis', 'benny', 'lacey', 'pip', 'alvarez',
                'fong', 'rosa', 'bigmo', 'teddy', 'hank', 'marv']
GANG_PORTRAIT = {'dogs': 'dogs_weapon', 'rats': 'rats_brawler', 'yard': 'yard_brawler',
                 'saints': 'saints_brawler', 'grays': 'grays_brawler'}


def cm(name):
    """Resolve a cloth name to a material."""
    if name is None:
        return None
    if isinstance(name, tuple):
        return name
    if name in C:
        return C[name]
    return mat(name)


# =============================================================================
# Head drawing (shared normalised shapes for sprites and portraits)
# =============================================================================
#  Normalised head space: head radius 1, centre (0,0), y down, facing right.
#  Shapes: ('e', x, y, rx, ry[, ang]) | ('p', [(x,y)..]) | ('c', x0,y0,x1,y1,r)
#  Optional trailing dict: {'face': True} allowed over face zone, {'sub': True} own shading.


def S_e(x, y, rx, ry, ang=0, **o):
    return ('e', (x, y, rx, ry, ang), o)


def S_p(pts, **o):
    return ('p', pts, o)


def S_c(x0, y0, x1, y1, r, **o):
    return ('c', (x0, y0, x1, y1, r), o)


def shape_mask(g, sh, cx, cy, R):
    kind, a, o = sh
    if kind == 'e':
        x, y, rx, ry, ang = a
        return g.ell(cx + x * R, cy + y * R, rx * R, ry * R, ang)
    if kind == 'p':
        return g.poly([(cx + x * R, cy + y * R) for x, y in a])
    if kind == 'c':
        x0, y0, x1, y1, r = a
        return g.cap(cx + x0 * R, cy + y0 * R, cx + x1 * R, cy + y1 * R, r * R)
    raise ValueError(kind)


def hair_shapes(style):
    """Return (back_shapes, front_shapes, hairline, covers_ear)."""
    cap = S_e(-0.12, -0.32, 1.08, 0.84)
    back, front = [], []
    hl, ear = -0.42, False
    if style == 'short':
        front = [cap, S_p([(-0.2, -0.95), (0.95, -0.62), (0.85, -0.36), (0.1, -0.5)], face=True),
                 S_e(-0.55, -0.05, 0.42, 0.42)]
    elif style == 'sidepart':
        front = [cap, S_e(0.15, -0.72, 0.85, 0.38, -8, face=True), S_e(-0.55, -0.05, 0.42, 0.42)]
    elif style == 'buzz':
        front = [S_e(-0.08, -0.25, 1.02, 0.8)]
        hl = -0.5
    elif style == 'spiky':
        front = [S_e(-0.1, -0.28, 1.1, 0.86),
                 S_p([(-0.75, -0.45), (-1.55, -0.62), (-0.95, -0.05)], sub=True),
                 S_p([(-0.75, -0.6), (-1.25, -1.3), (-0.2, -0.85)], sub=True),
                 S_p([(-0.35, -0.85), (-0.15, -1.55), (0.25, -0.85)], sub=True),
                 S_p([(0.1, -0.85), (0.75, -1.35), (0.65, -0.62)], sub=True),
                 S_p([(0.35, -0.7), (1.2, -0.78), (0.72, -0.32)], sub=True, face=True),
                 S_p([(-0.95, -0.1), (-1.45, 0.25), (-0.85, 0.35)], sub=True)]
    elif style == 'spikes_up':
        front = [S_e(-0.1, -0.3, 1.08, 0.84)]
        for i, x in enumerate([-0.85, -0.45, -0.05, 0.35]):
            front.append(S_p([(x - 0.28, -0.7), (x + 0.05 - 0.1 * i, -1.62 + 0.08 * abs(i - 1.5)),
                              (x + 0.3, -0.72)], sub=True))
    elif style == 'puff':
        front = [S_e(-0.1, -0.3, 1.06, 0.82)]
        for (x, y, r) in [(-0.2, -1.2, 0.72), (-0.75, -1.05, 0.42), (0.35, -1.05, 0.42),
                          (-0.6, -1.55, 0.4), (0.15, -1.6, 0.42), (-0.25, -1.75, 0.38)]:
            front.append(S_e(x, y, r, r * 0.95, sub=True))
    elif style == 'wavy':
        front = [S_e(-0.12, -0.3, 1.1, 0.88),
                 S_e(-0.7, -0.75, 0.45, 0.4, sub=True), S_e(-0.2, -0.95, 0.5, 0.36, sub=True),
                 S_e(0.35, -0.82, 0.5, 0.34, sub=True),
                 S_p([(0.2, -0.75), (1.0, -0.6), (0.65, -0.28), (0.25, -0.45)], face=True, sub=True),
                 S_e(-0.8, 0.0, 0.38, 0.5, sub=True)]
    elif style == 'slick':
        front = [S_e(-0.15, -0.35, 1.05, 0.8), S_e(-0.55, -0.2, 0.62, 0.6),
                 S_p([(-0.2, -1.05), (0.85, -0.7), (0.6, -0.5), (-0.2, -0.75)])]
        hl = -0.5
    elif style == 'loose':
        front = [S_e(-0.15, -0.35, 1.06, 0.82), S_e(-0.6, -0.15, 0.62, 0.62),
                 S_p([(0.25, -0.8), (0.75, -0.6), (0.55, -0.05), (0.42, -0.45)], face=True,
                     sub=True),
                 S_p([(-0.1, -0.85), (0.35, -0.75), (0.2, -0.2), (0.1, -0.55)], face=True,
                     sub=True)]
    elif style == 'beehive':
        front = [S_e(-0.12, -0.32, 1.06, 0.82), S_e(-0.1, -1.15, 0.78, 0.82, sub=True),
                 S_e(-0.05, -1.75, 0.45, 0.38, sub=True)]
        hl = -0.48
    elif style == 'flattop':
        front = [S_e(-0.1, -0.25, 1.04, 0.8, sub=True),
                 S_p([(-0.9, -0.5), (-0.85, -1.45), (0.78, -1.45), (0.85, -0.58)], sub=True)]
        hl = -0.5
    elif style == 'mohawk':
        front = [S_e(-0.1, -0.25, 1.02, 0.78, sub=True, shaved=True),
                 S_p([(0.4, -0.85), (0.3, -1.7), (-0.25, -1.75), (-0.8, -1.5), (-1.35, -0.9),
                      (-1.0, -0.55), (-0.4, -0.95)], sub=True)]
        hl = -0.5
    elif style == 'mohawk_low':
        front = [S_e(-0.1, -0.25, 1.02, 0.78, sub=True, shaved=True),
                 S_p([(0.4, -0.85), (0.2, -1.35), (-0.5, -1.4), (-1.15, -0.9),
                      (-0.9, -0.6), (-0.4, -0.95)], sub=True)]
        hl = -0.5
    elif style == 'braid':
        front = [S_e(-0.12, -0.32, 1.1, 0.86),
                 S_p([(-0.1, -1.0), (0.95, -0.6), (0.75, -0.3), (0.0, -0.6)], face=True),
                 S_e(-0.75, -0.05, 0.42, 0.5)]
        for i, (x, y) in enumerate([(-0.95, 0.35), (-1.1, 0.75), (-1.15, 1.15), (-1.15, 1.55)]):
            back.append(S_e(x, y, 0.32 - 0.02 * i, 0.27, sub=True))
    elif style == 'bob':
        front = [S_e(-0.1, -0.28, 1.14, 0.92),
                 S_p([(-1.1, -0.3), (-1.08, 0.66), (-0.62, 0.74), (-0.2, 0.6), (-0.16, -0.3)], sub=True,
                     cheek=True),
                 S_p([(-0.2, -1.0), (1.02, -0.68), (1.0, -0.3), (-0.1, -0.3)], face=True)]
        ear = True
    elif style == 'ponytail':
        front = [S_e(-0.05, -0.3, 1.02, 0.8),
                 S_p([(-0.1, -0.98), (0.95, -0.62), (0.8, -0.38), (0.0, -0.55)], face=True)]
        back = [S_c(-1.12, -0.35, -1.5, 0.7, 0.2, sub=True), S_e(-1.08, -0.38, 0.2, 0.18)]
    elif style == 'bun':
        front = [S_e(-0.12, -0.32, 1.06, 0.82), S_e(-0.85, -0.75, 0.42, 0.42, sub=True)]
        hl = -0.46
    elif style == 'curly':
        front = [S_e(-0.12, -0.3, 1.1, 0.86)]
        for (x, y, r) in [(-0.85, -0.65, 0.36), (-0.45, -0.98, 0.36), (0.05, -1.05, 0.36),
                          (0.55, -0.82, 0.32), (-1.0, -0.15, 0.34), (-1.0, 0.35, 0.32)]:
            front.append(S_e(x, y, r, r, sub=True))
        front.append(S_e(0.75, -0.48, 0.24, 0.24, face=True, sub=True))
        back = [S_e(-0.95, 0.75, 0.34, 0.32, sub=True), S_e(-0.6, 0.85, 0.3, 0.28, sub=True)]
    elif style == 'long':
        front = [S_e(-0.1, -0.3, 1.12, 0.9),
                 S_p([(-0.15, -1.0), (1.0, -0.62), (0.9, -0.32), (-0.05, -0.55)], face=True),
                 S_p([(-1.12, -0.3), (-1.18, 0.95), (-0.25, 0.95), (-0.15, -0.3)], sub=True,
                     cheek=True)]
        back = [S_p([(-1.2, 0.0), (-1.3, 1.5), (-0.3, 1.5), (-0.3, 0.2)], sub=True)]
        ear = True
    elif style == 'pompadour':
        front = [S_e(-0.15, -0.28, 1.04, 0.8, shaved=True),
                 S_e(0.15, -0.95, 0.85, 0.5, -12, sub=True),
                 S_e(0.7, -0.85, 0.45, 0.32, -20, sub=True, face=True),
                 S_e(-0.55, -0.6, 0.55, 0.45, sub=True)]
    elif style == 'sideshave':
        front = [S_e(-0.1, -0.25, 1.02, 0.78, shaved=True),
                 S_p([(-0.95, -0.55), (-0.5, -1.25), (0.4, -1.3), (1.1, -0.85), (0.95, -0.4),
                      (0.3, -0.7), (-0.4, -0.75)], sub=True, face=True)]
        hl = -0.5
    elif style == 'combover':
        front = [S_e(-0.6, -0.05, 0.45, 0.45), S_e(-0.15, -0.55, 0.95, 0.42, shaved=True),
                 S_c(-0.7, -0.75, 0.6, -0.8, 0.08), S_c(-0.75, -0.55, 0.65, -0.62, 0.08)]
        hl = -0.6
    elif style == 'bald_fringe':
        front = [S_e(-0.7, 0.0, 0.42, 0.36), S_e(-0.45, 0.12, 0.3, 0.26)]
        hl = -0.8
    elif style == 'bald':
        front = []
        hl = -1.2
    else:
        raise ValueError(style)
    return back, front, hl, ear


def hat_shapes(kind):
    """Shapes for headgear: list of (shape, part) where part in 'main','dark','light','brim'."""
    out = []
    if kind == 'cap':
        out = [(S_e(-0.05, -0.52, 1.08, 0.72), 'main', 'clipy:-0.34'),
               (S_e(0.95, -0.4, 0.62, 0.14), 'brim', None),
               (S_e(0.15, -0.62, 0.22, 0.14), 'light', 'badge')]
    elif kind == 'cap_back':
        out = [(S_e(-0.05, -0.5, 1.08, 0.72), 'main', 'clipy:-0.3'),
               (S_e(-1.05, -0.38, 0.5, 0.14, 8), 'brim', None),
               (S_e(0.55, -0.42, 0.25, 0.12), 'light', None)]
    elif kind == 'flatcap':
        out = [(S_p([(-1.05, -0.32), (-0.95, -0.9), (-0.2, -1.12), (0.75, -0.88), (1.3, -0.5),
                     (1.15, -0.32)]), 'main', None),
               (S_p([(0.5, -0.45), (1.35, -0.52), (1.25, -0.3), (0.5, -0.32)]), 'dark', None)]
    elif kind == 'hardhat':
        out = [(S_e(0.0, -0.6, 1.08, 0.8), 'main', 'clipy:-0.42'),
               (S_e(0.05, -0.42, 1.32, 0.14), 'brim', None),
               (S_p([(-0.12, -1.33), (0.12, -1.33), (0.12, -0.42), (-0.12, -0.42)]), 'light',
                'clipmain')]
    elif kind in ('beanie', 'beanie_pom'):
        out = [(S_e(-0.08, -0.45, 1.1, 0.82), 'main', 'clipy:-0.3'),
               (S_p([(-1.2, -0.58), (1.05, -0.58), (1.05, -0.28), (-1.2, -0.28)]), 'dark',
                'clipmain2')]
        if kind == 'beanie_pom':
            out.append((S_e(-0.2, -1.35, 0.3, 0.28), 'light', None))
    elif kind == 'weldcap':
        out = [(S_e(-0.08, -0.42, 1.08, 0.72), 'main', 'clipy:-0.32'),
               (S_e(0.95, -0.34, 0.42, 0.12), 'brim', None)]
    elif kind == 'fedora':
        out = [(S_p([(-0.85, -0.42), (-0.75, -1.15), (-0.2, -1.3), (0.05, -1.12), (0.4, -1.3),
                     (0.85, -1.1), (0.88, -0.42)]), 'main', None),
               (S_p([(-0.86, -0.62), (0.88, -0.62), (0.88, -0.44), (-0.86, -0.44)]), 'dark',
                'clipmain'),
               (S_e(0.05, -0.4, 1.5, 0.17, -4), 'brim', None)]
    elif kind == 'police':
        out = [(S_p([(-1.05, -0.48), (-1.15, -1.0), (0.9, -1.12), (1.0, -0.48)]), 'main', None),
               (S_p([(-1.0, -0.62), (1.0, -0.62), (1.0, -0.42), (-1.0, -0.42)]), 'dark', None),
               (S_e(1.0, -0.4, 0.5, 0.13), 'brim', None),
               (S_e(0.45, -0.78, 0.16, 0.16), 'gold', None)]
    elif kind == 'paper':
        out = [(S_p([(-0.95, -0.4), (-0.85, -1.25), (0.85, -1.4), (0.95, -0.4)]), 'main', None),
               (S_p([(-1.0, -0.62), (1.0, -0.62), (1.0, -0.4), (-1.0, -0.4)]), 'dark', None)]
    elif kind == 'bandana':
        out = [(S_e(-0.1, -0.42, 1.12, 0.78), 'main', 'clipy:-0.32'),
               (S_p([(-1.0, -0.4), (-1.6, -0.15), (-1.4, 0.15), (-0.95, -0.1)]), 'main', None)]
    elif kind == 'bandana_puff':
        out = [(S_p([(-1.05, -0.95), (0.7, -0.88), (0.75, -0.62), (-1.1, -0.68)]), 'main', None),
               (S_p([(-0.95, -0.9), (-1.55, -1.25), (-1.6, -0.85), (-1.05, -0.72)]), 'main', None),
               (S_p([(-1.0, -0.78), (-1.45, -0.42), (-1.15, -0.32), (-0.9, -0.7)]), 'dark', None)]
    return out


def headband_shapes():
    return [(S_p([(-1.2, -0.62), (1.15, -0.58), (1.15, -0.36), (-1.2, -0.38)]), 'main', 'clipmain0'),
            (S_p([(-0.95, -0.55), (-1.75, -0.65), (-1.65, -0.38), (-0.95, -0.42)]), 'main', None),
            (S_p([(-0.95, -0.5), (-1.55, -0.12), (-1.35, 0.02), (-0.9, -0.4)]), 'dark', None)]


# -----------------------------------------------------------------------------


def skin_of(ch):
    return SKIN[ch['skin']]


def hair_mat(ch, which=1):
    col = ch['hcol'] if which == 1 else ch['hcol2']
    base = hx(HAIR.get(col, col)) if not col.startswith('#') else hx(col)
    s = mix(base, SHADOW_TGT, 0.42)
    if col in ('black',):
        s = hx('#160f14')
        base = hx('#2e2228')
    if col in ('platinum', 'white'):
        s = mix(base, hx('#8a8aa0'), 0.45)
    h = mix(base, LIGHT_TGT, 0.35)
    if col == 'black':
        h = hx('#5a4a5a')
    return (base, s, h, mix(s, INK, 0.4))


def shaved_mat(ch):
    sk = skin_of(ch)
    hm = hair_mat(ch)
    b = mix(sk[0], hm[0], 0.35)
    s = mix(sk[1], hm[1], 0.35)
    return (b, s, sk[2], s)


def draw_head(ch, bt, expr, view='front', portrait=False, pR=15.0, pc=(30.0, 25.0)):
    """Render a head into its own canvas.  Returns (canvas, cx, cy)."""
    if portrait:
        R = pR
        N = 64
        cv = Canvas(N, N)
        cx, cy = pc
    else:
        R = bt['R']
        N = 48
        cv = Canvas(N, N)
        cx, cy = 24.0, 24.0
    g = cv.g
    sk = skin_of(ch)
    hm = hair_mat(ch)
    style = ch['hair']
    back, front, hairline, ear_cov = hair_shapes(style)
    k_sk = 2 if not portrait else 4
    flipx = view == 'back'

    # --- back hair
    for sh in back:
        m = shape_mask(g, sh, cx, cy, R)
        cv.fill(m, hm, pid=1, k=1 if not portrait else 2, hi=True)

    # --- head skin: cranium + jaw (portrait gets more jaw)
    wide = 1.0
    if ch['body'] in ('heavy', 'big'):
        wide = 1.06
    if portrait:
        cran = g.ell(cx - 0.5, cy - 1.0, R * 1.0, R * 0.98)
        jaw = g.ell(cx + R * 0.16, cy + R * 0.3, R * 0.8 * wide, R * 0.72)
        chin = g.ell(cx + R * 0.42, cy + R * 0.62, R * 0.42, R * 0.38)
        head = cran | jaw | chin
        if ch['body'] == 'kid' or ch['body'] == 'elder' and ch.get('wide'):
            head |= g.ell(cx + R * 0.1, cy + R * 0.3, R * 0.92, R * 0.7)
    else:
        cran = g.ell(cx, cy - 0.5, R, R - 0.5)
        jaw = g.ell(cx + 1.0, cy + 2.0, R - 1.5 + (wide - 1) * 6, R - 2.8)
        head = cran | jaw
    if flipx:
        head = head[:, ::-1]
        # re-centre after flip: column c -> N-1-c ; centre maps to N - cx
        dxs = int(round((N - cx) - cx))
        head = np.roll(head, -dxs, axis=1)
    cv.fill(head, sk, pid=2, k=k_sk, hi=False)
    if portrait:
        # 3-tone: deep shadow on the outer lower-right rim
        deep = head & ~shift(head, 1, 1) & ~shift(head, 2, 0)
        cv.rgb[deep & (g.X > cx)] = sk[3]
        hl = head & ~shift(head, -2, -2)
        cv.rgb[hl & (g.Y < cy) & (g.X < cx + 4)] = sk[2]

    # face zone (for clipping hair)
    fz = (g.X > cx - 0.34 * R) & (g.Y > cy + hairline * R)
    if view == 'back':
        fz = np.zeros_like(fz)

    # --- face features
    if view != 'back':
        if portrait:
            draw_face_portrait(cv, ch, cx, cy, R, expr)
        else:
            draw_face_sprite(cv, ch, bt, cx, cy, R, expr)

    # --- facial hair (normalised shapes)
    if ch['fhair'] and view != 'back':
        fm = hair_mat(dict(ch, hcol=ch['fhcol'] or ch['hcol']))
        draw_facial_hair(cv, ch, cx, cy, R, fm, portrait, expr)
        if portrait and ch['fhair'] in ('beard', 'goatee'):
            draw_mouth_portrait(cv, ch, cx, cy, R, getattr(cv, 'mouth_kind', 'line'))

    # --- hair
    hat = ch['hat']
    total_hair = np.zeros((N, N), bool)
    shaved = np.zeros((N, N), bool)
    for sh in front:
        m = shape_mask(g, sh, cx, cy, R)
        o = sh[2]
        if o.get('cheek'):
            m &= ~(fz & (g.X > cx - 0.18 * R))
        elif not o.get('face'):
            m &= ~fz
        else:
            m &= ~(fz & (g.Y > cy + (hairline + 0.12) * R))
        if flipx:
            m = np.roll(m[:, ::-1], -int(round((N - cx) - cx)), axis=1)
        if o.get('shaved'):
            shaved |= m & ~total_hair
            continue
        if o.get('sub'):
            cv.fill(m, hm, pid=1, k=1 if not portrait else 2, hi=True)
        total_hair |= m
    if view == 'back' and style not in ('bald', 'bald_fringe', 'combover'):
        total_hair |= head & (g.Y < cy + R * 0.55)
    if shaved.any():
        cv.fill(shaved & ~total_hair, shaved_mat(ch), pid=2, k=1 if not portrait else 2)
    if total_hair.any():
        # base fill under the sub-shaded parts
        base_only = total_hair & ~(cv.pid == 1)
        cv.fill(base_only, hm, pid=1, k=1 if not portrait else 3, hi=True)
        if not portrait:
            hrim = total_hair & ~shift(total_hair, 1, 1)
            cv.rgb[hrim] = hm[1]
        else:
            draw_hair_strands(cv, total_hair, hm, cx, cy, R)
    # secondary hair colour (gray temples / pink streak)
    if ch['hcol2'] and view != 'back':
        hm2 = hair_mat(ch, 2)
        if style in ('slick', 'loose'):
            t = total_hair & (g.X < cx - 0.2 * R) & (g.X > cx - 0.62 * R) & (g.Y > cy - 0.42 * R)
            cv.fill(t, hm2, pid=1, k=1)
        elif style == 'bob':
            t = total_hair & (g.X > cx + 0.15 * R) & (g.X < cx + 0.55 * R)
            cv.fill(t, hm2, pid=1, k=1, hi=True)
    # shadow cast by hair onto the forehead
    if total_hair.any() and view != 'back':
        cast = shift(total_hair, 0, -1) & ~total_hair & (cv.pid == 2)
        if portrait:
            cast |= shift(total_hair, 0, -2) & ~total_hair & (cv.pid == 2)
        cv.rgb[cast] = sk[1]

    # --- ear
    if not ear_cov and view != 'back':
        if portrait:
            em = g.ell(cx - R * 0.47, cy + R * 0.22, R * 0.15, R * 0.21)
            cv.fill(em, sk, pid=3, k=2, ring={1, 2})
            cv.solid(g.ell(cx - R * 0.46, cy + R * 0.24, R * 0.05, R * 0.1), sk[1])
        else:
            ex, ey = int(cx - round(R * 0.36)), int(cy + 0)
            cv.px(ex, ey, sk[0]); cv.px(ex, ey + 1, sk[1]); cv.px(ex - 1, ey, sk[1])
            cv.px(ex - 1, ey + 1, sk[1])

    # --- headband / hats
    if ch['band']:
        draw_hat_parts(cv, headband_shapes(), cm(ch['band']), cx, cy, R, head, total_hair,
                       portrait, flipx)
    if hat:
        draw_hat_parts(cv, hat_shapes(hat[0]), cm(hat[1]), cx, cy, R, head, total_hair,
                       portrait, flipx)

    # --- glasses
    if ch['glasses'] and view != 'back':
        if portrait:
            draw_glasses_portrait(cv, ch, cx, cy, R, expr)
        else:
            draw_glasses_sprite(cv, ch, cx, cy, R)
    return cv, cx, cy


def draw_hat_parts(cv, parts, m, cx, cy, R, head, hair, portrait, flipx):
    g = cv.g
    N = cv.h
    main_mask = np.zeros_like(head)
    k = 1 if not portrait else 2
    for sh, part, clip in parts:
        msk = shape_mask(g, sh, cx, cy, R)
        if clip and clip.startswith('clipy:'):
            msk &= g.Y < cy + float(clip[6:]) * R
        if clip == 'clipmain':
            msk &= main_mask
        if clip == 'clipmain2':
            msk &= main_mask | (head | hair) & (g.Y < cy - 0.2 * R)
            msk &= (main_mask | head | hair)
        if clip == 'clipmain0':
            msk &= (head | hair)
        if flipx:
            msk = np.roll(msk[:, ::-1], -int(round((N - cx) - cx)), axis=1)
        if part == 'main':
            cv.fill(msk, m, pid=4, k=k, hi=True, ring={1, 2} if portrait else None)
            main_mask |= msk
        elif part == 'dark':
            cv.fill(msk, (m[1], m[3], m[0], m[3]), pid=4, k=k)
        elif part == 'brim':
            cv.fill(msk, (m[1], m[3], m[0], m[3]), pid=4, k=1, ring={1, 2, 4})
        elif part == 'light':
            cv.fill(msk, (m[2], m[0], m[2], m[1]), pid=4, k=1 if portrait else 0)
        elif part == 'gold':
            cv.fill(msk, C['gold'], pid=4, k=1 if portrait else 0)


# --- sprite face --------------------------------------------------------------

def brow_color(ch):
    hm = hair_mat(ch)
    if ch['hair'] in ('bald', 'bald_fringe') and ch['hcol'] in ('white', 'gray'):
        return mix(hm[1], INK, 0.2)
    if ch['hcol'] in ('blonde', 'platinum', 'white', 'gray', 'pink'):
        return mix(hm[1], INK, 0.35)
    return INK


def face_style(ch, expr):
    if expr in ('normal', None):
        return ch['face']
    return expr


def draw_face_sprite(cv, ch, bt, cx, cy, R, expr):
    sk = skin_of(ch)
    ex = int(cx)             # first column right of centre
    ey = int(cy)
    s = R / 8.0
    n0 = ex + int(round(-0.0 * s))       # near eye columns n0, n0+1
    f0 = ex + int(round(4.0 * s))        # far eye columns f0, f0+1
    ink = INK
    bc = brow_color(ch)
    fs = face_style(ch, expr)
    P_ = cv.px

    def eyes_open(lid=True, pupil=ink, big=False):
        for x0 in (n0, f0):
            if lid:
                P_(x0, ey - 1, ink); P_(x0 + 1, ey - 1, ink)
            P_(x0, ey, EYE_W); P_(x0 + 1, ey, pupil)
            P_(x0, ey + 1, EYE_W if big else mix(EYE_W, sk[1], 0.3)); P_(x0 + 1, ey + 1, pupil)
        if ch['lashes']:
            P_(n0 - 1, ey - 1, ink)
            P_(f0 + 2, ey - 2, ink)

    def eyes_heavy():
        for x0 in (n0, f0):
            P_(x0, ey, ink); P_(x0 + 1, ey, ink)
            P_(x0, ey + 1, EYE_W); P_(x0 + 1, ey + 1, ink)

    def brows(kind):
        # near brow over n0-1..n0+1, far brow over f0..f0+2
        y = ey - 3
        if kind == 'flat':
            for x in (n0 - 1, n0, n0 + 1):
                P_(x, y, bc)
            for x in (f0, f0 + 1, f0 + 2):
                P_(x, y, bc)
        elif kind == 'angry':
            P_(n0 - 1, y, bc); P_(n0, y, bc); P_(n0 + 1, y + 1, bc)
            P_(f0, y + 1, bc); P_(f0 + 1, y, bc); P_(f0 + 2, y, bc)
        elif kind == 'mean':
            P_(n0 - 1, y - 1, bc); P_(n0, y, bc); P_(n0 + 1, y + 1, bc)
            P_(f0, y + 1, bc); P_(f0 + 1, y, bc); P_(f0 + 2, y - 1, bc)
        elif kind == 'worried':
            P_(n0 - 1, y + 1, bc); P_(n0, y, bc); P_(n0 + 1, y - 1, bc)
            P_(f0, y - 1, bc); P_(f0 + 1, y, bc); P_(f0 + 2, y + 1, bc)
        elif kind == 'raised':
            for x in (n0 - 1, n0, n0 + 1):
                P_(x, y - 1, bc)
            for x in (f0, f0 + 1, f0 + 2):
                P_(x, y - 1, bc)
        elif kind == 'arch':
            P_(n0 - 1, y, bc); P_(n0, y - 1, bc); P_(n0 + 1, y, bc)
            P_(f0, y, bc); P_(f0 + 1, y - 1, bc); P_(f0 + 2, y, bc)

    my = ey + 4 if R >= 8 else ey + 3
    mx = ex + int(round(3 * s))
    lip = mix(sk[1], MOUTH_DARK, 0.7)

    def mouth(kind):
        if kind == 'line':
            P_(mx, my, lip); P_(mx + 1, my, lip)
        elif kind == 'smile':
            P_(mx - 1, my - 1, lip); P_(mx, my, lip); P_(mx + 1, my, lip); P_(mx + 2, my - 1, lip)
        elif kind == 'grin':
            P_(mx - 1, my - 1, ink); P_(mx, my - 1, EYE_W); P_(mx + 1, my - 1, EYE_W)
            P_(mx + 2, my - 1, ink); P_(mx, my, MOUTH_DARK); P_(mx + 1, my, MOUTH_DARK)
        elif kind == 'open':
            P_(mx, my - 1, MOUTH_DARK); P_(mx + 1, my - 1, MOUTH_DARK)
            P_(mx, my, TONGUE); P_(mx + 1, my, MOUTH_DARK)
        elif kind == 'shout':
            P_(mx - 1, my - 1, MOUTH_DARK); P_(mx, my - 1, EYE_W); P_(mx + 1, my - 1, EYE_W)
            P_(mx - 1, my, MOUTH_DARK); P_(mx, my, MOUTH_DARK); P_(mx + 1, my, TONGUE)
            P_(mx, my + 1, MOUTH_DARK)
        elif kind == 'small':
            P_(mx + 1, my, MOUTH_DARK)
        elif kind == 'grit':
            P_(mx - 1, my, ink); P_(mx, my, EYE_W); P_(mx + 1, my, EYE_W); P_(mx + 2, my, ink)
        elif kind == 'frown':
            P_(mx - 1, my, lip); P_(mx, my - 1, lip); P_(mx + 1, my - 1, lip); P_(mx + 2, my, lip)
        elif kind == 'smirk':
            P_(mx, my, lip); P_(mx + 1, my, lip); P_(mx + 2, my - 1, lip)
        elif kind == 'wavy':
            P_(mx - 1, my, lip); P_(mx, my - 1, lip); P_(mx + 1, my, lip); P_(mx + 2, my - 1, lip)

    # nose: one protruding pixel at the profile edge
    nx = ex + int(round(R)) - 0
    P_(nx, ey + 2, sk[0]); P_(nx - 1, ey + 2, sk[0])
    P_(nx - 1, ey + 3, sk[1])

    if fs in ('determined',):
        eyes_open(); brows('angry'); mouth('line')
    elif fs == 'neutral':
        eyes_open(); brows('flat'); mouth('line')
    elif fs == 'kind':
        eyes_open(); brows('arch'); mouth('smile')
    elif fs == 'cheerful':
        # closed happy eyes
        for x0 in (n0, f0):
            P_(x0 - 0, ey, ink); P_(x0 + 1, ey - 1, ink); P_(x0 + 2, ey, ink)
        brows('arch'); mouth('smile')
    elif fs == 'calm':
        eyes_heavy(); brows('flat'); mouth('line')
    elif fs == 'stern':
        eyes_open(); brows('angry'); mouth('frown')
    elif fs == 'tough':
        eyes_open(); brows('angry'); mouth('smirk')
    elif fs == 'mean':
        eyes_heavy(); brows('mean'); mouth('frown')
    elif fs == 'cocky':
        eyes_open(); brows('flat'); P_(n0 - 1, ey - 4, bc); mouth('smirk')
    elif fs == 'shout':
        eyes_open(); brows('angry'); mouth('shout')
    elif fs == 'grit':
        eyes_open(); brows('angry'); mouth('grit')
    elif fs == 'pain':
        P_(n0, ey - 1, ink); P_(n0 + 1, ey, ink); P_(n0, ey + 1, ink)
        P_(f0 + 1, ey - 1, ink); P_(f0, ey, ink); P_(f0 + 1, ey + 1, ink)
        brows('worried'); mouth('grit')
    elif fs == 'ko':
        for x0 in (n0, f0):
            P_(x0, ey, ink); P_(x0 + 1, ey, ink)
        brows('worried'); mouth('open')
    elif fs == 'daze':
        for x0 in (n0, f0):
            P_(x0, ey, ink); P_(x0 + 1, ey, ink); P_(x0 + 1, ey + 1, ink); P_(x0, ey + 1, EYE_W)
        brows('worried'); mouth('small')
    elif fs == 'dizzy':
        for x0 in (n0, f0):
            P_(x0, ey - 1, ink); P_(x0 + 1, ey - 1, ink); P_(x0 + 1, ey, ink)
            P_(x0, ey + 1, ink); P_(x0 + 1, ey + 1, ink); P_(x0, ey, EYE_W)
        brows('worried'); mouth('wavy')
    elif fs == 'happy':
        for x0 in (n0, f0):
            P_(x0, ey, ink); P_(x0 + 1, ey - 1, ink); P_(x0 + 2, ey, ink)
        brows('raised'); mouth('grin')
    elif fs == 'shout_happy':
        for x0 in (n0, f0):
            P_(x0, ey, ink); P_(x0 + 1, ey - 1, ink); P_(x0 + 2, ey, ink)
        brows('raised'); mouth('shout')
    elif fs == 'talk':
        eyes_open(); brows('raised' if ch['face'] in ('cheerful', 'kind', 'cocky') else 'flat')
        mouth('open')
    elif fs == 'scared':
        for x0 in (n0, f0):
            P_(x0, ey - 1, ink); P_(x0 + 1, ey - 1, ink)
            P_(x0, ey, EYE_W); P_(x0 + 1, ey, EYE_W); P_(x0, ey + 1, EYE_W); P_(x0 + 1, ey + 1, ink)
        brows('worried'); mouth('wavy')
    else:
        eyes_open(); brows('flat'); mouth('line')

    # marks
    marks = ch['marks']
    if 'scar' in marks:
        sc = mix(sk[0], hx('#e8b0a8'), 0.6)
        P_(f0 + 1, ey - 4, sc); P_(f0 + 1, ey - 3, sc); P_(f0 + 2, ey - 2, sc)
    if 'freckles' in marks:
        fc = mix(sk[0], hx('#a05030'), 0.45)
        P_(n0 - 1, ey + 2, fc); P_(n0 + 1, ey + 2, fc); P_(f0 + 1, ey + 2, fc)
    if 'smudge' in marks:
        P_(n0 - 1, ey + 2, mix(sk[1], INK, 0.4)); P_(n0, ey + 3, mix(sk[1], INK, 0.3))
    if 'soot' in marks:
        P_(n0, ey + 2, mix(sk[1], INK, 0.45)); P_(n0 + 1, ey + 3, mix(sk[1], INK, 0.3))
        P_(f0 + 2, ey + 2, mix(sk[1], INK, 0.3))
    # cheek blush for cheerful folks / kids
    if ch['face'] in ('cheerful',) or ch['body'] == 'kid':
        P_(f0 + 1, ey + 2, mix(sk[0], hx('#e06070'), 0.35))


def draw_glasses_sprite(cv, ch, cx, cy, R):
    ex, ey = int(cx), int(cy)
    s = R / 8.0
    n0 = ex
    f0 = ex + int(round(4 * s))
    kind = ch['glasses']
    P_ = cv.px
    if kind == 'shades':
        lens = hx('#1e1a2a')
        for x in range(n0 - 1, f0 + 3):
            P_(x, ey - 1, INK)
        for x in list(range(n0 - 1, n0 + 2)) + list(range(f0, f0 + 3)):
            P_(x, ey, lens); P_(x, ey + 1, lens)
        P_(n0, ey, hx('#7a8ab0')); P_(f0 + 1, ey, hx('#7a8ab0'))
        P_(n0 - 2, ey - 1, INK); P_(n0 - 3, ey - 1, INK)
        return
    fr = INK if kind != 'cateye' else hx('#a02a5a')
    lensc = None
    for x0 in (n0, f0):
        for x in (x0 - 1, x0 + 2):
            P_(x, ey, fr); P_(x, ey + 1, fr)
        for x in (x0, x0 + 1):
            P_(x, ey - 1, fr); P_(x, ey + 2, fr)
        if kind == 'thick':
            P_(x0 - 1, ey - 1, fr); P_(x0 + 2, ey - 1, fr)
        if kind == 'cateye':
            P_(x0 + 2, ey - 1, fr); P_(x0 + 3, ey - 2, fr)
    P_(n0 - 2, ey, fr); P_(n0 - 3, ey, fr)


def draw_facial_hair(cv, ch, cx, cy, R, fm, portrait, expr):
    g = cv.g
    kind = ch['fhair']
    head = cv.pid == 2
    sk = skin_of(ch)
    if kind == 'mustache':
        if portrait:
            m = g.ell(cx + R * 0.6, cy + R * 0.52, R * 0.36, R * 0.13) | \
                g.ell(cx + R * 0.38, cy + R * 0.6, R * 0.18, R * 0.12)
        else:
            m = g.rect(int(cx) + 2, int(cy) + 3, int(cx) + 6, int(cy) + 3) | \
                g.rect(int(cx) + 2, int(cy) + 4, int(cx) + 2, int(cy) + 4) | \
                g.rect(int(cx) + 6, int(cy) + 4, int(cx) + 6, int(cy) + 4)
        cv.fill(m, fm, pid=5, k=1)
    elif kind == 'beard':
        if portrait:
            m = (g.ell(cx + R * 0.15, cy + R * 0.6, R * 0.95, R * 0.62) & head &
                 (g.Y > cy + R * 0.5 - np.clip((cx - g.X) * 0.25, 0, R)) & (g.X > cx - R * 0.42))
            m |= g.ell(cx + R * 0.35, cy + R * 0.95, R * 0.55, R * 0.35)
            mouth_hole = g.ell(cx + R * 0.62, cy + R * 0.66, R * 0.24, R * 0.09)
            cv.fill(m & ~mouth_hole, fm, pid=5, k=2, hi=True)
            if expr in ('happy', 'surprised', 'angry'):
                pass
        else:
            m = (g.ell(cx + 1, cy + 3, R + 0.5, R - 2.5) & (g.Y > cy + 1.5) &
                 (g.X > cx - 3)) | g.ell(cx + 2.5, cy + 6.5, 4.5, 2.5)
            cv.fill(m, fm, pid=5, k=1, hi=True)
            # mouth line inside beard
            cv.px(int(cx) + 3, int(cy) + 4, mix(fm[1], INK, 0.5))
            cv.px(int(cx) + 4, int(cy) + 4, mix(fm[1], INK, 0.5))
    elif kind == 'goatee':
        if portrait:
            m = g.ell(cx + R * 0.55, cy + R * 0.88, R * 0.3, R * 0.25) | \
                g.ell(cx + R * 0.6, cy + R * 0.52, R * 0.3, R * 0.08)
        else:
            m = g.rect(int(cx) + 3, int(cy) + 5, int(cx) + 5, int(cy) + 7) | \
                g.rect(int(cx) + 2, int(cy) + 3, int(cx) + 5, int(cy) + 3)
        cv.fill(m & (head | (cv.pid == 5)) if not portrait else m, fm, pid=5, k=1)
    elif kind == 'stubble':
        st = mix(sk[1], fm[0], 0.35)
        if portrait:
            m = head & (g.Y > cy + R * 0.42 - np.clip((cx - g.X) * 0.3, 0, R)) & (g.X > cx - R * 0.42)
            m &= ~(cv.rgb == EYE_W).all(-1) & ~(cv.rgb == np.array(INK)).all(-1)
            cv.rgb[m] = (cv.rgb[m] * 0.72 + np.array(fm[1]) * 0.28).astype(np.uint8)
            pat = (((g.X.astype(int) * 73 + g.Y.astype(int) * 151) % 17) < 3) & m
            cv.rgb[pat] = (cv.rgb[pat] * 0.7 + np.array(fm[1]) * 0.3).astype(np.uint8)
        else:
            m = head & (g.Y > cy + 4.5) & (g.X > cx - 2) & (cv.rgb[..., 0] == sk[0][0])
            cv.rgb[m] = mix(sk[0], fm[1], 0.22)


# =============================================================================
# Sprite body rendering
# =============================================================================

PID_BARM, PID_BLEG, PID_TORSO, PID_FLEG, PID_SKIRT, PID_HEAD, PID_FARM = 1, 2, 3, 4, 5, 6, 7
PID_FFORE, PID_FFIST, PID_BFORE, PID_BFIST, PID_FFOOT, PID_BFOOT, PID_BAG = 8, 9, 10, 11, 12, 13, 14


def shirt_mat(ch):
    s = ch['shirt']
    if s == 'stripe_rw':
        return C['red']
    if s == 'stripe_nw':
        return C['navy']
    if s == 'hawaii':
        return C['orange']
    return cm(s)


def arm_layers(ch, near):
    """Return (upper_layers, fore_layers, fist_mat, extras).  Layers: (t0, t1, mat, dr)."""
    sk = skin_of(ch)
    sh = shirt_mat(ch)
    j = ch['jacket']
    up, fo = [(0, 1, sk, 0)], [(0, 1, sk, 0)]
    sleeves = ch['sleeves']
    if sleeves == 'short':
        up.append((0, 0.62, sh, 0.35))
    elif sleeves == 'long':
        up = [(0, 1, sh, 0)]
        fo = [(0, 1, sh, 0)]
    elif sleeves == 'rolled':
        up = [(0, 1, sh, 0)]
        fo.append((0, 0.3, sh, 0.45))
    if j:
        jm = cm(j['color'])
        js = j['sleeves']
        if js == 'long':
            up = [(0, 1, jm, 0)]
            fo = [(0, 1, jm, 0)]
            if j.get('trim') in ('white', 'cream', 'cyan', 'purple'):
                fo.append((0.78, 1.0, cm(j['trim']), 0.3))
        elif js == 'rolled':
            up = [(0, 1, jm, 0)]
            fo = [(0, 1, sk, 0), (0, 0.32, jm, 0.5)]
        elif js == 'none':
            if j['kind'] in ('vest', 'safety', 'padded'):
                pass  # sleeves come from the shirt
    if ch.get('shawl'):
        up = [(0, 1, cm(ch['shawl']), 0.2)]
        fo = [(0, 1, sk, 0), (0, 0.4, cm(ch['dress']), 0.3)]
    if ch['dress'] and not ch['jacket'] and not ch.get('shawl'):
        dm = cm(ch['dress'])
        up = [(0, 1, sk, 0), (0, 0.55, dm, 0.3)]
    if ch['armband'] and near:
        up.append((0.25, 0.6, cm(ch['armband']), 0.45))
    if ch['wrist']:
        fo.append((0.72, 1.0, cm(ch['wrist']), 0.5))
    if ch['guards']:
        fo.append((0.1, 0.92, cm(ch['guards']), 1.25, 'ring'))
    fist = cm(ch['gloves']) if ch['gloves'] else sk
    return up, fo, fist


def leg_layers(ch):
    sk = skin_of(ch)
    pm = cm(ch['pants'])
    th, sh = [(0, 1, pm, 0)], [(0, 1, pm, 0)]
    st = ch['pstyle']
    if st == 'shorts':
        th = [(0, 1, sk, 0), (0, 0.85, pm, 0.35)]
        sh = [(0, 1, sk, 0)]
        if ch['body'] == 'kid':
            sh.append((0.55, 1.0, C['white'], 0.2))
    elif st == 'bike':
        lg = cm(ch['legs2'])
        th = [(0, 1, lg, 0), (0, 0.7, pm, 0.3)]
        sh = [(0, 1, lg, 0)]
    elif st == 'track':
        sh.append((0.82, 1.0, pm, 0.4))
    if ch['dress'] and ch['legs2'] == 'skin':
        th = [(0, 1, sk, 0)]
        sh = [(0, 1, mix_mat(sk, C['tan'], 0.25), 0)]
    ss = ch['sstyle']
    if ss == 'boot':
        sh.append((0.62, 1.0, cm(ch['shoes']), 0.35))
    elif ss == 'rubber':
        sh.append((0.3, 1.0, cm(ch['shoes']), 0.55))
    elif ss == 'hightop':
        sh.append((0.75, 1.0, cm(ch['shoes']), 0.4))
    return th, sh


def mix_mat(a, b, t):
    return tuple(mix(a[i], b[i], t) for i in range(4))


def sole_mat(ch):
    if ch['sole']:
        return cm(ch['sole'])
    sm = cm(ch['shoes'])
    return (sm[3], mix(sm[3], INK, 0.4), sm[1], INK)


class Rig:
    pass


def render_frame(ch, pose, debug=False):
    bt = dict(BODY[ch['body']])
    if ch.get('bulk'):
        bt['Ws'] += 2; bt['Ww'] += 1; bt['aw'] += 0.7; bt['fw'] += 0.6; bt['fist'] += 0.35
        bt['tw'] += 0.4; bt['T'] += 0.5
    if ch.get('wide') and ch['body'] == 'elder':
        bt['Ws'] += 4; bt['Ww'] += 5; bt['belly'] = 7
    N = 96
    cv = Canvas(N, N)
    g = cv.g
    sk = skin_of(ch)
    lean = pose['lean']
    if bt['stoop'] and abs(lean) < 45:
        lean += bt['stoop']
    th = math.radians(lean)
    Fv = np.array([math.cos(th), math.sin(th)])
    Uv = np.array([math.sin(th), -math.cos(th)])
    face_dir = -1 if pose['view'] == 'back' else 1
    hip = np.array([48.0, 62.0])
    T = bt['T'] - pose['bob']

    def tl(u, w):
        return hip + u * Fv + w * Uv

    def tuv():
        dx = g.X - hip[0]
        dy = g.Y - hip[1]
        return dx * Fv[0] + dy * Fv[1], dx * Uv[0] + dy * Uv[1]

    U_, W_ = tuv()
    tw_ = pose['twist']
    sh_f = tl((bt['shf'] - 2.5 * tw_) * face_dir, T - 2.6)
    sh_b = tl((bt['shb'] + 5.5 * tw_) * face_dir, T - 2.4 - 0.5 * tw_)
    hip_f = tl(0.8, 0.5)
    hip_b = tl(-0.8, 0.5)

    asc = pose['arm_scale']
    lsc = pose['leg_scale']

    def arm(sh, angs):
        e = sh + bt['ua'] * asc * V(angs[0])
        h = e + bt['fa'] * asc * V(angs[1])
        return e, h

    def leg(hp, angs):
        k = hp + bt['thigh'] * lsc * V(angs[0])
        a = k + bt['shin'] * lsc * V(angs[1])
        return k, a

    elb_f, hand_f = arm(sh_f, pose['fa'])
    elb_b, hand_b = arm(sh_b, pose['ba'])
    knee_f, ank_f = leg(hip_f, pose['fl'])
    knee_b, ank_b = leg(hip_b, pose['bl'])

    up_l, fo_l, fist_m = arm_layers(ch, True)
    up_lb, fo_lb, fist_mb = arm_layers(ch, False)
    th_l, sh_l = leg_layers(ch)

    def seg_layers(p0, p1, layers, width, matf, pid, ring, k=1):
        for layer in layers:
            t0, t1, m, dr = layer[:4]
            a = p0 + (p1 - p0) * t0
            b = p0 + (p1 - p0) * t1
            msk = g.cap(a[0], a[1], b[0], b[1], width / 2.0 + dr)
            if len(layer) > 4:
                ring = (ring or set()) | {pid}
            cv.fill(msk, matf(m), pid=pid, k=k, ring=ring, hi=len(layer) > 4)
            if len(layer) > 4:
                strap = msk & ~shift(msk, 0, 1) & ~shift(msk, 1, 0)
                mid = p0 + (p1 - p0) * ((t0 + t1) / 2.0)
                band = g.cap(mid[0] - (p1 - p0)[1] * 0.0, mid[1], mid[0], mid[1], width / 2.0 + dr) & msk
                cv.rgb[band & ~shift(band, 0, 1)] = matf(m)[3]
            ring = None

    ident = lambda m: m

    def draw_arm(sh, e, h, angs, upl, fol, fistm, near, hand_kind):
        matf = ident if near else far
        pu, pf, pk = (PID_FARM, PID_FFORE, PID_FFIST) if near else (PID_BARM, PID_BFORE, PID_BFIST)
        under = {PID_TORSO, PID_FLEG, PID_SKIRT, PID_HEAD, PID_BAG, PID_BLEG, PID_BARM,
                 PID_BFORE, PID_BFIST, PID_FFOOT, PID_BFOOT} if near else {PID_BLEG, PID_BFOOT}
        seg_layers(sh, e, upl, bt['aw'], matf, pu, under)
        d = h - e
        L = max(np.linalg.norm(d), 1e-3)
        dn = d / L
        wrist = h - dn * (bt['fist'] * 0.6)
        bend = abs(((angs[1] - angs[0]) + 180) % 360 - 180)
        r2 = set(under) | ({pu} if bend > 100 else set())
        seg_layers(e, wrist, fol, bt['fw'], matf, pf, r2)
        fr = bt['fist']
        if hand_kind == 'open':
            hm = g.ell(h[0], h[1], fr * 1.15, fr * 0.8, math.degrees(math.atan2(dn[1], dn[0])))
        else:
            hm = g.ell(h[0], h[1], fr + 0.25, fr + 0.05) | g.ell(h[0] + dn[0] * 0.7, h[1] + dn[1] * 0.7, fr, fr)
        cv.fill(hm, matf(fistm), pid=pk, k=1, ring=r2 | {pf, pu}, hi=near)

    def foot_ang(angs, override):
        if override is not None:
            return override
        a = angs[1] - 90
        return max(-70, min(60, a))

    def draw_leg(hp, k, a, angs, fo, near):
        matf = ident if near else far
        pid = PID_FLEG if near else PID_BLEG
        pfoot = PID_FFOOT if near else PID_BFOOT
        ring = {PID_BLEG, PID_BARM, PID_BFORE, PID_BFIST, PID_BFOOT, PID_TORSO} if near else set()
        if near:
            ring.discard(PID_TORSO)
        seg_layers(hp, k, th_l, bt['tw'], matf, pid, ring)
        bend = abs(((angs[1] - angs[0]) + 180) % 360 - 180)
        r2 = set(ring) | ({pid} if bend > 110 else set())
        seg_layers(k, a, sh_l, bt['sw'], matf, pid, r2 if bend > 110 else ring)
        # foot
        fa_ = foot_ang(angs, fo)
        fs = bt['foot']
        u, v = g.uv(a[0], a[1], fa_)
        shoe_m = cm(ch['shoes'])
        if ch['sstyle'] == 'dress':
            m = ((u - 1.6 * fs) / (3.1 * fs)) ** 2 + ((v - 0.8 * fs) / (1.4 * fs)) ** 2 <= 1.0
            m &= v <= 1.8 * fs
        else:
            m = ((u - 1.4 * fs) / (3.2 * fs)) ** 2 + ((v - 0.6 * fs) / (1.9 * fs)) ** 2 <= 1.0
            m &= v <= 2.1 * fs
        cv.fill(m, matf(shoe_m), pid=pfoot, k=1, ring=ring | {pid} if near else {PID_BLEG})
        if ch['sstyle'] in ('sneaker', 'hightop') or ch['sole']:
            sole = m & (v > 1.0 * fs)
            cv.rgb[sole] = matf(sole_mat(ch))[0]
        else:
            sole = m & (v > 1.2 * fs)
            cv.rgb[sole] = matf(shoe_m)[3]
        if ch['shoes'] == 'checker':
            pat = ((g.X.astype(int) + g.Y.astype(int)) % 2 == 0) & m & (v <= 1.0 * fs)
            cv.rgb[pat] = INK if near else mix(INK, (60, 60, 60), 0.3)

    # ------------------------------------------------------------------ back limbs
    draw_arm(sh_b, elb_b, hand_b, pose['ba'], up_lb, fo_lb, fist_mb, False, pose['bh'])
    draw_leg(hip_b, knee_b, ank_b, pose['bl'], pose['bf'], False)

    # ------------------------------------------------------------------ torso
    draw_torso(cv, ch, bt, hip, Fv, Uv, U_ * face_dir, W_, T, pose)

    # ------------------------------------------------------------------ front leg
    draw_leg(hip_f, knee_f, ank_f, pose['fl'], pose['ff'], True)

    # ------------------------------------------------------------------ skirt / coat tails
    if abs(lean) < 45:
        ths = math.radians(lean * 0.3)
        Fs = np.array([math.cos(ths), math.sin(ths)])
        Us = np.array([math.sin(ths), -math.cos(ths)])
        dxs, dys = g.X - hip[0], g.Y - hip[1]
        Us_, Ws_ = dxs * Fs[0] + dys * Fs[1], dxs * Us[0] + dys * Us[1]
    else:
        Fs, Us, Us_, Ws_ = Fv, Uv, U_, W_
    draw_skirt(cv, ch, bt, hip, Fs, Us, Us_ * face_dir, Ws_, T, pose)
    draw_bag(cv, ch, bt, hip, Fv, Uv, T, face_dir)

    # ------------------------------------------------------------------ head
    hcv, hcx, hcy = draw_head(ch, bt, pose['expr'], view=pose['view'])
    rgb, a, shd = hcv.rgb, hcv.a, hcv.sh
    k = (pose['hrot'] // 90) % 4
    if k:
        rgb = np.rot90(rgb, k)
        a = np.rot90(a, k)
        shd = np.rot90(shd, k)
    neck = tl(0.4 * face_dir, T)
    R = bt['R']
    hc = neck + Uv * (R - 2.0 - bt['nk']) + np.array([0.5 * face_dir, 0.0]) * (1 if k == 0 else 0)
    if bt['stoop'] and abs(lean) < 45:
        hc = hc + np.array([2.0, 1.0])
    hc = hc + np.array(pose['head'], float)
    # head canvas centre after rotation (square canvas -> centre stays if cx==cy==N/2)
    hN = hcv.h
    ox = int(round(hc[0] - hcx))
    oy = int(round(hc[1] - hcy))
    cv.blit(rgb, a, shd, ox, oy, PID_HEAD,
            ring={PID_TORSO, PID_BARM, PID_BFORE, PID_BFIST, PID_BLEG, PID_FLEG, PID_SKIRT,
                  PID_BAG, PID_FFOOT, PID_BFOOT})
    # neck shadow under the chin
    if k == 0:
        below = shift(a.copy(), 0, 0)
        hm = np.zeros((N, N), bool)
        ys, xs = np.nonzero(a)
        ys2, xs2 = ys + oy + 1, xs + ox
        ok = (ys2 >= 0) & (ys2 < N) & (xs2 >= 0) & (xs2 < N)
        hm[ys2[ok], xs2[ok]] = True
        cast = hm & (cv.pid == PID_TORSO)
        cv.rgb[cast] = cv.sh[cast]

    # ------------------------------------------------------------------ front arm
    draw_arm(sh_f, elb_f, hand_f, pose['fa'], up_l, fo_l, fist_m, True, pose['fh'])

    # cane (Mrs. Alvarez) -- in the near hand while the hand is low
    if 'cane' in ch['extras'] and hand_f[1] > hip[1] - 6 and abs(lean) < 45:
        top = hand_f + np.array([0.5, 0])
        bot = np.array([hand_f[0] + 2.5, hip[1] + bt['thigh'] + bt['shin'] + 1.8])
        m = g.cap(top[0], top[1] - 1.5, bot[0], bot[1], 0.7)
        cv.fill(m & ~(cv.pid == PID_FFIST), C['brown'], pid=PID_BAG, k=0,
                ring={PID_TORSO, PID_FLEG, PID_BLEG, PID_SKIRT})
        hk = g.cap(top[0] - 2, top[1] - 2, top[0] + 0.5, top[1] - 2.5, 0.8)
        cv.fill(hk & ~cv.a, C['brown'], pid=PID_BAG, k=0)
    if 'briefcase' in ch['extras'] and hand_b[1] > hip[1] - 4 and abs(lean) < 45:
        bm = g.rect(int(hand_b[0]) - 3, int(hand_b[1]) + 1, int(hand_b[0]) + 3, int(hand_b[1]) + 5)
        cv.fill(bm & ~cv.a, far(C['brown']), pid=PID_BAG, k=1)
    if 'grocery' in ch['extras'] and hand_b[1] > hip[1] - 4 and abs(lean) < 45:
        bm = g.rect(int(hand_b[0]) - 3, int(hand_b[1]) - 1, int(hand_b[0]) + 3, int(hand_b[1]) + 6)
        cv.fill(bm & ~cv.a, far(C['sand']), pid=PID_BAG, k=1)
        cv.solid(g.ell(hand_b[0] - 1, hand_b[1] - 2, 1.5, 1.5) & ~cv.a, far(C['green'])[0])
        cv.solid(g.ell(hand_b[0] + 1.5, hand_b[1] - 2, 1.4, 1.2) & ~cv.a, far(C['orange'])[0])

    cv.outline()

    # ------------------------------------------------------------------ place in 64x64 cell
    ys, xs = np.nonzero(cv.a)
    bottom = ys.max()
    dy = 59 - bottom - pose['air']
    if pose['center']:
        dx = int(round(32 - (xs.min() + xs.max() + 1) / 2.0))
    else:
        dx = int(round(32 + pose['bx'] - hip[0]))
    out = np.zeros((64, 64, 4), np.uint8)
    full = cv.to_rgba()
    clipped = 0
    for y, x in zip(ys, xs):
        ny, nx = y + dy, x + dx
        if 0 <= ny < 64 and 0 <= nx < 64:
            out[ny, nx] = full[y, x]
        else:
            clipped += 1
    if pose['carry']:
        top = min(hand_f[1], hand_b[1]) - bt['fist'] - 0.5
        hp = ((hand_f[0] + hand_b[0]) / 2.0 + dx, top + dy)
    else:
        hp = (hand_f[0] + dx, hand_f[1] + dy)
    hand = [int(round(hp[0] - 0.5)), int(round(hp[1] - 0.5)), int(pose['wang'])]
    return out, hand, clipped


def draw_torso(cv, ch, bt, hip, Fv, Uv, U_, W_, T, pose):
    g = cv.g
    sk = skin_of(ch)
    Ws, Ww = bt['Ws'], bt['Ww']
    belly = bt['belly']
    pm = cm(ch['pants'])
    sm = shirt_mat(ch)
    j = ch['jacket']
    back = pose['view'] == 'back'
    # pelvis
    pel = ((U_ - 0.2) / (Ww / 2.0 + 0.3)) ** 2 + ((W_ - 1.6) / 3.2) ** 2 <= 1.0
    lowerm = pm
    if ch['dress']:
        lowerm = cm(ch['dress'])
    cv.fill(pel, lowerm, pid=PID_TORSO, k=1,
            ring={PID_BLEG, PID_BARM, PID_BFORE, PID_BFIST, PID_BFOOT})
    # torso polygon in (u, w)
    chest = 1.0
    pts = [(-Ww / 2.0, 2.0), (Ww / 2.0, 2.0), (Ws / 2.0 + chest, T - 4.5), (Ws / 2.0 - 1.0, T),
           (-Ws / 2.0 + 1.5, T), (-Ws / 2.0, T - 4.0)]
    tor = inpoly(U_, W_, pts)
    tor |= ((U_ - 0.3) / (Ws / 2.0 + 0.2)) ** 2 + ((W_ - (T - 2.6)) / 2.6) ** 2 <= 1.0
    if belly:
        tor |= ((U_ - 1.5) / (Ws / 2.0 + belly * 0.12)) ** 2 + \
               ((W_ - T * 0.36) / (T * 0.42)) ** 2 <= 1.0
    top_m = sm
    if ch['dress'] and not j:
        top_m = cm(ch['dress'])
    cv.fill(tor, top_m, pid=PID_TORSO, k=2,
            ring={PID_BLEG, PID_BARM, PID_BFORE, PID_BFIST, PID_BFOOT})
    front = U_ > (Ws / 2.0 - 2.6)
    # stripes on shirts
    if ch['shirt'] in ('stripe_rw', 'stripe_nw') and not back:
        stripe = tor & ((np.floor(W_ + 100).astype(int) % 3) == 0)
        cv.rgb[stripe] = C['white'][0] if not (U_[stripe] > 99).any() else C['white'][0]
    if ch['shirt'] == 'hawaii':
        dots = tor & (((np.floor(U_ + 100).astype(int) * 3 + np.floor(W_ + 100).astype(int) * 2) % 5) == 0)
        cv.rgb[dots] = hx('#f4e0a0')
        dots2 = tor & (((np.floor(U_ + 101).astype(int) * 2 + np.floor(W_ + 100).astype(int) * 3) % 7) == 0)
        cv.rgb[dots2] = hx('#3a9a6a')
    # belt
    if not ch['dress'] and not ch['overalls']:
        belt = tor & (W_ >= 1.6) & (W_ < 2.8)
        cv.rgb[belt] = mix(pm[1], INK, 0.35)
    # overalls bib
    if ch['overalls']:
        om = cm(ch['overalls'])
        if ch.get('ovstyle') == 'tied':
            # coverall top tied at waist: show tank on torso, tied sleeves around the waist
            band = tor & (W_ >= 1.2) & (W_ < 3.6)
            cv.fill(band | pel, om, pid=PID_TORSO, k=1)
            knot = ((U_ - (Ww / 2.0 - 0.5)) / 1.6) ** 2 + ((W_ - 1.8) / 1.6) ** 2 <= 1.0
            cv.fill(knot, (om[1], om[3], om[0], om[3]), pid=PID_TORSO, k=0)
            tail = inpoly(U_, W_, [(Ww / 2.0 - 1.5, 2.0), (Ww / 2.0 + 1.5, 1.5),
                                   (Ww / 2.0 + 1.0, -3.0), (Ww / 2.0 - 0.8, -2.5)])
            cv.fill(tail, om, pid=PID_SKIRT, k=1, ring={PID_TORSO})
        else:
            bib = tor & (U_ > -Ws / 2.0 + 2.5) & (W_ < T - 3.5)
            if back:
                bib = tor & (W_ < 4)
            cv.fill(bib | pel, om, pid=PID_TORSO, k=1)
            strap = tor & (np.abs(U_ - (Ws / 2.0 - 3.0)) < 0.9) & (W_ >= T - 4.5)
            strap |= tor & (np.abs(U_ + Ws / 2.0 - 3.0) < 0.9) & (W_ >= T - 4.5)
            cv.rgb[strap] = om[1]
            if not back:
                btn = tor & (np.abs(U_ - (Ws / 2.0 - 3.0)) < 0.6) & (np.abs(W_ - (T - 4.0)) < 0.6)
                cv.rgb[btn] = C['gold'][0]
    # jacket
    if j:
        jm = cm(j['color'])
        kind = j['kind']
        jacket = tor & (W_ >= 1.0)
        if kind in ('coat', 'labcoat') or j['length'] == 'long':
            jacket = tor | (pel & (W_ > 0.5))
        if kind == 'vest' and not j['open']:
            jacket = tor & (W_ >= 1.4)
        if kind == 'safety':
            jacket = tor & (W_ >= 1.5) & (W_ < T - 1.0)
        cv.fill(jacket, jm, pid=PID_TORSO, k=2, hi=kind in ('satin', 'leather', 'vest', 'slicker'))
        if not back:
            if j['open'] and kind not in ('chef', 'track', 'hoodie'):
                opening = jacket & (U_ > Ws / 2.0 - 2.4) & (W_ > 1.5)
                if kind == 'safety':
                    opening = jacket & (U_ > Ws / 2.0 - 2.0)
                if kind == 'suit':
                    opening = jacket & (U_ > Ws / 2.0 - 2.4) & (W_ > T - 6.5)
                cv.fill(opening, sm, pid=PID_TORSO, k=1)
                edge = jacket & (np.abs(U_ - (Ws / 2.0 - 2.9)) < 0.55) & (W_ > 1.5)
                cv.rgb[edge & ~opening] = jm[1]
            else:
                zip_ = jacket & (np.abs(U_ - (Ws / 2.0 - 1.8)) < 0.5) & (W_ > 1.5) & (W_ < T - 1)
                cv.rgb[zip_] = jm[1]
            if j['stripe']:
                st = jacket & (W_ > T - 5.0) & (W_ < T - 3.4)
                if j['open']:
                    st &= ~(U_ > Ws / 2.0 - 2.4)
                cv.rgb[st] = cm(j['stripe'])[0]
            if kind == 'safety':
                refl = jacket & (W_ > T * 0.42) & (W_ < T * 0.42 + 1.3)
                cv.rgb[refl] = hx('#e8e4a0')
                refl2 = jacket & (np.abs(U_ + 0.5) < 0.7) & (W_ > T * 0.42)
                cv.rgb[refl2] = hx('#e8e4a0')
            if kind == 'padded':
                q = jacket & ((np.floor(W_ + 100).astype(int) % 3) == 0)
                cv.rgb[q] = jm[1]
            if kind == 'satin' and j['trim']:
                tm = cm(j['trim'])
                tr = jacket & (W_ < 2.6)
                cv.rgb[tr] = tm[0]
                col = jacket & (W_ > T - 1.6)
                cv.rgb[col] = tm[0]
            if kind == 'varsity':
                tr = jacket & (W_ < 2.6)
                cv.rgb[tr] = cm('cream')[1]
                lt = jacket & (np.abs(U_ + 1.0) < 1.1) & (np.abs(W_ - (T - 5.5)) < 1.1)
                cv.rgb[lt] = cm('cream')[0]
            if kind == 'track' and j['trim']:
                tm = cm(j['trim'])
                tr = jacket & (np.abs(U_ - (Ws / 2.0 - 1.0)) < 0.5)
                cv.rgb[tr] = tm[0]
            if kind == 'chef':
                for wv in (T - 4.0, T - 7.0):
                    b = jacket & (np.abs(U_ - (Ws / 2.0 - 2.4)) < 0.6) & (np.abs(W_ - wv) < 0.6)
                    cv.rgb[b] = C['gray'][1]
            if j.get('trim') == 'pins':
                for (pu, pw, c) in [(-1.5, T - 4, 'red'), (1.0, T - 6, 'yellow'), (-2.5, T - 7.5, 'cyan')]:
                    b = jacket & (np.abs(U_ - pu) < 0.6) & (np.abs(W_ - pw) < 0.6)
                    cv.rgb[b] = C[c][0]
            if kind == 'labcoat':
                pk = jacket & (np.abs(U_ - 0.5) < 1.6) & (np.abs(W_ - (T - 5)) < 0.5)
                cv.rgb[pk] = jm[1]
        if kind == 'hoodie' or j.get('collar') == 'hood':
            hood = ((U_ + Ws / 2.0 - 1.0) / 2.6) ** 2 + ((W_ - (T + 0.3)) / 1.8) ** 2 <= 1.0
            hc = jm if kind == 'hoodie' else sm
            cv.fill(hood, hc, pid=PID_TORSO, k=1)
    # collars
    col = (j or {}).get('collar') or ch.get('collar')
    if col == 'turtle' and not back:
        tc = ((U_ - 1.0) / 3.2) ** 2 + ((W_ - (T + 0.2)) / 1.6) ** 2 <= 1.0
        cv.fill(tc, sm, pid=PID_TORSO, k=1)
    elif col == 'high' and not back:
        tc = ((U_ - 0.8) / 3.4) ** 2 + ((W_ - (T + 0.1)) / 1.5) ** 2 <= 1.0
        cv.fill(tc, cm(j['color']) if j else sm, pid=PID_TORSO, k=1)
    elif col in ('shirt', 'lapel') and not back:
        tc = (U_ > Ws / 2.0 - 4.2) & (U_ < Ws / 2.0 - 0.5) & (W_ > T - 2.2) & tor
        cv.rgb[tc] = (cm(j['color']) if j else sm)[1]
    if ch.get('torn') and not back:
        tear = tor & (U_ < -1.0) & (W_ > T - 3.5) & (((np.floor(U_ * 1.0 + 100).astype(int) + np.floor(W_ + 100).astype(int)) % 2) == 0)
        cv.rgb[tear] = sk[0]
    # suspenders
    for e in ch['extras']:
        if e.startswith('suspenders') and not back:
            smat = cm(e.split(':')[1])
            for u0 in (Ws / 2.0 - 3.0, -1.5):
                s_ = tor & (np.abs(U_ - u0) < 0.7) & (W_ > 1.5)
                cv.rgb[s_] = smat[0]
        if e == 'chain' and not back:
            ch_ = tor & (np.abs((W_ - (T - 1.0)) + 0.55 * (U_ + Ws / 2.0)) < 0.7)
            pat = ((g.X.astype(int) + g.Y.astype(int)) % 2 == 0)
            cv.rgb[ch_ & pat] = C['steel'][0]
            cv.rgb[ch_ & ~pat] = C['steel'][1]
        if e == 'goldchain' and not back:
            gc = tor & (np.abs(((U_ - 1.5) / 3.0) ** 2 + ((W_ - T) / 4.0) ** 2 - 1.0) < 0.25)
            cv.rgb[gc] = C['gold'][0]
        if e == 'whistle' and not back:
            wc = tor & (np.abs(U_ - (Ws / 2.0 - 2.6)) < 0.6) & (np.abs(W_ - (T - 5.0)) < 0.8)
            cv.rgb[wc] = C['steel'][0]
            cd = tor & (np.abs(U_ - (Ws / 2.0 - 3.4 + (W_ - T) * 0.3)) < 0.45) & (W_ > T - 5)
            cv.rgb[cd] = C['white'][1]
        if e == 'nametag' and not back:
            nt = tor & (np.abs(U_ - (Ws / 2.0 - 3.6)) < 1.1) & (np.abs(W_ - (T - 4.5)) < 0.6)
            cv.rgb[nt] = C['white'][0]
        if e == 'badge' and not back:
            nt = tor & (np.abs(U_ - (Ws / 2.0 - 3.6)) < 0.8) & (np.abs(W_ - (T - 4.0)) < 0.8)
            cv.rgb[nt] = C['gold'][0]
        if e.startswith('bowtie') and not back:
            bm = cm(e.split(':')[1])
            bw = (np.abs(U_ - (Ws / 2.0 - 1.4)) < 1.6) & (np.abs(W_ - (T - 0.6)) < 0.9)
            cv.fill(bw & ~(np.abs(U_ - (Ws / 2.0 - 1.4)) < 0.4) | (bw & (np.abs(W_ - (T - 0.6)) < 0.4)),
                    bm, pid=PID_TORSO, k=0)
        if e.startswith('tie') and not back:
            bm = cm(e.split(':')[1])
            tm_ = tor & (np.abs(U_ - (Ws / 2.0 - 1.2)) < 0.7) & (W_ > T - 6.5)
            cv.rgb[tm_] = bm[0]
    if ch.get('shawl'):
        shm = cm(ch['shawl'])
        sw = tor & (W_ > T - 4.5)
        sw |= inpoly(U_, W_, [(-Ws / 2.0 - 0.5, T - 4.0), (Ws / 2.0 + 0.8, T - 4.5),
                              (1.0, T - 7.5)])
        cv.fill(sw, shm, pid=PID_TORSO, k=1, hi=True)
    # apron upper bib
    if ch['apron'] and not back:
        am = cm(ch['apron'])
        bib = tor & (U_ > -0.5) & (W_ < T - 2.5)
        cv.fill(bib, am, pid=PID_TORSO, k=1)
        strap = tor & (np.abs((W_ - (T - 2.5)) - 0.9 * (U_ + 0.5)) < 0.6) & (U_ < -0.4)
        cv.rgb[strap] = am[1]
    # bag strap across chest
    for e in ch['extras']:
        if (e.startswith('bag') or e == 'newsbag') and not back:
            bc = cm(e.split(':')[1]) if ':' in e else C['cream']
            st = tor & (np.abs((W_ - 2.0) - 1.1 * (U_ + Ws / 2.0)) < 0.75)
            cv.rgb[st] = bc[1]


def draw_skirt(cv, ch, bt, hip, Fv, Uv, U_, W_, T, pose):
    Ww = bt['Ww']
    j = ch['jacket']
    L = bt['thigh'] * 0.95
    if ch['dress']:
        dm = cm(ch['dress'])
        pts = [(-Ww / 2.0 - 0.3, 2.5), (Ww / 2.0 + 0.6, 2.5), (Ww / 2.0 + 2.2, -L),
               (-Ww / 2.0 - 1.2, -L)]
        sk_ = inpoly(U_, W_, pts)
        cv.fill(sk_, dm, pid=PID_SKIRT, k=2, ring={PID_FLEG, PID_BLEG, PID_BARM, PID_BFORE,
                                                   PID_BFIST})
        if ch['dress'] == 'floral':
            dots = sk_ & (((np.floor(U_ + 100).astype(int) * 3 + np.floor(W_ + 100).astype(int) * 2) % 5) == 0)
            cv.rgb[dots] = hx('#f0d070')
        hem = sk_ & (W_ < -L + 1.2)
        cv.rgb[hem] = dm[1]
    if j and (j['kind'] in ('coat', 'labcoat') or j['length'] == 'long'):
        jm = cm(j['color'])
        pts = [(-Ww / 2.0 - 0.3, 2.5), (Ww / 2.0 + 0.4, 2.5), (Ww / 2.0 + 1.0, -L - 1.0),
               (-Ww / 2.0 - 2.4, -L - 1.4)]
        sk_ = inpoly(U_, W_, pts)
        cv.fill(sk_, jm, pid=PID_SKIRT, k=2, ring={PID_FLEG, PID_BLEG, PID_BARM, PID_BFORE,
                                                   PID_BFIST, PID_FFOOT})
        slit = sk_ & (np.abs(U_ - (Ww / 2.0 - 1.0)) < 0.5) & (W_ < 1.5)
        cv.rgb[slit] = jm[1]
    if ch['apron']:
        am = cm(ch['apron'])
        pts = [(-0.5, 2.8), (Ww / 2.0 + 0.8, 2.8), (Ww / 2.0 + 1.8, -L + 0.5), (-1.2, -L + 0.5)]
        ap = inpoly(U_, W_, pts)
        if pose['view'] != 'back':
            cv.fill(ap, am, pid=PID_SKIRT, k=1, ring={PID_FLEG, PID_BLEG, PID_TORSO})
            if ch.get('apron_stain'):
                st = ap & (np.abs(U_ - 2) < 1.2) & (np.abs(W_ + 1) < 1.0)
                cv.rgb[st] = mix(am[1], C['brown'][0], 0.5)
            tie = ap & (W_ > 1.8)
            cv.rgb[tie] = am[1]


def draw_bag(cv, ch, bt, hip, Fv, Uv, T, face_dir):
    g = cv.g
    for e in ch['extras']:
        if e.startswith('bag') or e == 'newsbag':
            bc = cm(e.split(':')[1]) if ':' in e else C['cream']
            Ww = bt['Ww']
            c = hip + (-Ww / 2.0 - 1.5) * face_dir * Fv + 2.5 * Uv
            m = g.ell(c[0], c[1], 3.2, 2.8) | g.rect(int(c[0]) - 3, int(c[1]) - 1, int(c[0]) + 2,
                                                       int(c[1]) + 2)
            cv.fill(m, bc, pid=PID_BAG, k=1, ring={PID_TORSO, PID_BLEG, PID_FLEG, PID_SKIRT})
            flap = m & (g.Y < c[1] - 0.5)
            cv.rgb[flap] = bc[1]
            if e == 'newsbag':
                pap = g.rect(int(c[0]) - 2, int(c[1]) - 4, int(c[0]) + 1, int(c[1]) - 2) & ~cv.a
                cv.fill(pap, C['white'], pid=PID_BAG, k=0)


# =============================================================================
# Portraits (64x64 bust, 5 expressions)
# =============================================================================

EXPRS = ['neutral', 'happy', 'angry', 'surprised', 'sad']
PF = {'en': 2.4, 'ef': 10.2, 'mx': 7.0}   # portrait feature x offsets (R=15 units)
EYECOL = {'light': '#4a7ab0', 'tan': '#5a3a24', 'medium': '#4a2e1e', 'deep': '#3a2418'}


def lip_col(sk):
    return mix(sk[3], MOUTH_DARK, 0.62)


def draw_face_portrait(cv, ch, cx, cy, R, expr):
    g = cv.g
    sk = skin_of(ch)
    s = R / 15.0
    ey = cy + 3.2 * s
    face = ch['face']
    # map expression + personality into concrete parts
    eye_kind, brow_kind, mouth_kind = 'open', 'flat', 'line'
    if expr == 'neutral':
        eye_kind = {'calm': 'heavy', 'mean': 'heavy', 'cheerful': 'open'}.get(face, 'open')
        brow_kind = {'determined': 'firm', 'stern': 'firm', 'tough': 'firm', 'mean': 'angry',
                     'kind': 'arch', 'cheerful': 'arch', 'cocky': 'cocky', 'calm': 'low'}.get(face, 'flat')
        mouth_kind = {'kind': 'smile', 'cheerful': 'smile', 'cocky': 'smirk', 'stern': 'flat',
                      'tough': 'smirk', 'mean': 'frown', 'calm': 'flat'}.get(face, 'line')
    elif expr == 'happy':
        eye_kind = 'closed_happy' if face in ('cheerful', 'kind', 'neutral', 'cocky') else 'smile'
        brow_kind = 'raised'
        mouth_kind = 'laugh' if face not in ('calm', 'mean', 'stern') else 'grin'
    elif expr == 'angry':
        eye_kind, brow_kind, mouth_kind = 'angry', 'angry', 'shout'
        if face in ('calm',):
            mouth_kind = 'grit'
    elif expr == 'surprised':
        eye_kind, brow_kind, mouth_kind = 'wide', 'high', 'o'
    elif expr == 'sad':
        eye_kind, brow_kind, mouth_kind = 'sad', 'sad', 'frown'
    bc = brow_color(ch)
    if ch['hcol'] in ('white', 'gray', 'platinum') and ch['hair'] not in ('bald',):
        bc = mix(hair_mat(ch)[1], INK, 0.25)
    eyec = hx(ch['eyecol']) if ch['eyecol'] else hx(EYECOL[ch['skin']])

    eyes = [(cx + PF['en'] * s, 3.3 * s, 'near'), (cx + PF['ef'] * s, 2.6 * s, 'far')]
    for ex, rx, which in eyes:
        ry = 4.0 * s
        if eye_kind == 'wide':
            ry += 0.9 * s
            rx += 0.3 * s
        eye = g.ell(ex, ey, rx, ry)
        inner_right = which == 'near'     # inner corner (towards nose) side
        if eye_kind in ('closed_happy',):
            arc = g.ell(ex, ey + 1.2 * s, rx + 0.4, ry * 0.8) & ~g.ell(ex, ey + 2.2 * s, rx - 0.6, ry * 0.8)
            arc &= g.Y < ey + 1.0 * s
            cv.solid(arc, INK, pid=2)
            continue
        if eye_kind == 'heavy':
            eye &= g.Y > ey - ry * 0.15
        if eye_kind == 'smile':
            eye &= ~g.ell(ex, ey + ry * 1.25, rx * 1.3, ry * 0.75)
        if eye_kind == 'angry':
            sl = 0.55 if inner_right else -0.55
            eye &= (g.Y - ey) > -ry * 0.55 + (g.X - ex) * sl
        if eye_kind == 'sad':
            sl = -0.45 if inner_right else 0.45
            eye &= (g.Y - ey) > -ry * 0.45 + (g.X - ex) * sl
        if not eye.any():
            continue
        # outline ring (dark lid on top, soft below)
        ring = dil4(eye) & ~eye
        cv.rgb[ring & (g.Y <= ey + 0.5)] = INK
        cv.rgb[ring & (g.Y > ey + 0.5)] = mix(sk[1], INK, 0.35)
        cv.solid(eye, EYE_W, pid=2)
        # iris + pupil looking right
        if eye_kind == 'wide':
            ir = g.ell(ex + rx * 0.25, ey + 0.3, rx * 0.42, ry * 0.42) & eye
            cv.solid(ir, eyec)
            cv.solid(g.ell(ex + rx * 0.3, ey + 0.3, 0.9, 1.1) & eye, INK)
        else:
            ir = g.ell(ex + rx * 0.32, ey + 0.4 * s, rx * 0.68, ry * 0.8) & eye
            cv.solid(ir, eyec)
            pr = g.ell(ex + rx * 0.42, ey + 0.5 * s, rx * 0.34, ry * 0.42) & eye
            cv.solid(pr, INK)
            hl = g.ell(ex + rx * 0.05, ey - ry * 0.25, 0.8, 0.8) & ir
            cv.solid(hl, (255, 255, 255))
        # thick upper lid
        lid = eye & ~shift(eye, 0, -1)
        cv.rgb[lid] = INK
        if ch['lashes']:
            if which == 'near':
                cv.px(int(ex - rx - 0.5), int(ey - ry * 0.5), INK)
                cv.px(int(ex - rx - 1.2), int(ey - ry * 0.75), INK)
            else:
                cv.px(int(ex + rx + 0.5), int(ey - ry * 0.55), INK)
        if eye_kind == 'sad' and which == 'near':
            tear = g.ell(ex - rx * 0.3, ey + ry + 2.2 * s, 0.9, 1.4)
            cv.solid(tear, hx('#9ad0f0'))
    # brows
    bw = 1.15 * s
    B = {
        'flat': [((-0.5, -6.0), (6.5, -6.4)), ((8.8, -6.4), (13.6, -6.0))],
        'firm': [((-0.5, -6.8), (6.8, -5.4)), ((8.6, -5.4), (13.8, -6.6))],
        'angry': [((-0.6, -7.8), (7.0, -4.2)), ((8.4, -4.2), (14.0, -7.2))],
        'low': [((-0.5, -5.2), (6.5, -5.2)), ((8.8, -5.2), (13.6, -5.0))],
        'arch': [((-0.5, -6.0), (3.0, -7.4), (6.6, -6.4)), ((8.8, -6.6), (11.5, -7.3), (13.8, -6.0))],
        'raised': [((-0.5, -7.2), (3.0, -8.6), (6.6, -7.6)), ((8.8, -7.8), (11.5, -8.5), (13.8, -7.2))],
        'high': [((-0.5, -8.0), (3.0, -9.8), (6.6, -8.8)), ((8.8, -9.0), (11.5, -9.8), (13.8, -8.2))],
        'sad': [((-0.5, -5.2), (6.6, -8.4)), ((8.6, -8.4), (13.8, -5.4))],
        'cocky': [((-0.5, -7.6), (3.0, -8.8), (6.6, -7.6)), ((8.8, -6.0), (13.8, -6.0))],
    }[brow_kind]
    bo = PF['en'] - 3.6
    for pts in B:
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            m = g.cap(cx + (x0 + bo) * s, ey + y0 * s, cx + (x1 + bo) * s, ey + y1 * s, bw)
            cv.solid(m, bc, pid=2)
    # scar through the far brow
    if 'scar' in ch['marks']:
        sc = mix(sk[0], hx('#f0c8c0'), 0.55)
        m = g.cap(cx + (PF['ef'] - 0.7) * s, ey - 10 * s, cx + (PF['ef'] + 1.3) * s, ey - 2.5 * s, 0.6)
        cv.solid(m, sc)
        cv.solid(g.cap(cx + (PF['ef'] - 0.4) * s, ey - 9.6 * s, cx + (PF['ef'] + 1.6) * s, ey - 2.2 * s, 0.45) & ~m,
                 mix(sk[1], INK, 0.1))
    # nose (profile tip + shading)
    nx = cx + R * 0.97
    nose = g.poly([(nx - 2.0 * s, ey + 1.0 * s), (nx + 2.4 * s, ey + 5.6 * s),
                   (nx + 0.4 * s, ey + 6.8 * s), (nx - 2.2 * s, ey + 6.8 * s)])
    cv.fill(nose, sk, pid=2, k=1)
    cv.solid(g.cap(nx - 3.0 * s, ey + 6.4 * s, nx - 1.0 * s, ey + 6.8 * s, 0.5), sk[1])
    cv.solid(g.cap(nx - 3.6 * s, ey + 2.0 * s, nx - 3.6 * s, ey + 5.6 * s, 0.45), sk[1])
    if ch['fhair'] not in ('beard', 'goatee'):
        draw_mouth_portrait(cv, ch, cx, cy, R, mouth_kind)
    cv.mouth_kind = mouth_kind
    # cheeks / marks
    if ch['body'] == 'kid' or face in ('cheerful',) or ch['lashes'] or expr == 'happy':
        bl = g.ell(cx + (PF['en'] + 0.2) * s, ey + 5.8 * s, 2.2 * s, 1.0 * s) & (cv.pid == 2) & ~(cv.rgb == EYE_W).all(-1)
        cv.rgb[bl] = mix(cv.rgb[bl].mean(0).astype(int).tolist() if bl.any() else sk[0], hx('#e86a7a'), 0.3)
    if 'freckles' in ch['marks']:
        fc = mix(sk[0], hx('#a85a34'), 0.5)
        for dx, dy in [(1.5, 6.5), (3.5, 5.6), (5.5, 6.8), (11.0, 6.2), (12.5, 7.0)]:
            cv.px(int(cx + dx * s), int(ey + dy * s), fc)
    if 'smudge' in ch['marks']:
        sm = g.ell(cx + 2.5 * s, ey + 7.2 * s, 2.4 * s, 1.0 * s, -20)
        cv.rgb[sm] = mix(sk[1], INK, 0.45)
    if 'soot' in ch['marks']:
        for (dx, dy, r) in [(2.0, 7.0, 1.6), (12.0, 7.5, 1.0), (-1.5, -8.0, 1.2)]:
            sm = g.ell(cx + dx * s, ey + dy * s, r * s * 1.4, r * s * 0.8) & (cv.pid == 2)
            cv.rgb[sm] = mix(sk[1], INK, 0.4)


def draw_mouth_portrait(cv, ch, cx, cy, R, mouth_kind):
    g = cv.g
    sk = skin_of(ch)
    s = R / 15.0
    mx, my = cx + PF['mx'] * s, cy + 11.4 * s
    lc = lip_col(sk)
    if mouth_kind == 'line':
        cv.solid(g.cap(mx - 2.8 * s, my, mx + 2.2 * s, my, 0.5), lc)
    elif mouth_kind == 'flat':
        cv.solid(g.cap(mx - 2.2 * s, my + 0.3, mx + 2.0 * s, my + 0.3, 0.5), lc)
        cv.solid(g.cap(mx - 3.0 * s, my + 1.0, mx - 2.2 * s, my + 0.4, 0.45), lc)
    elif mouth_kind == 'smile':
        cv.solid(g.cap(mx - 3.4 * s, my - 1.2 * s, mx - 1.4 * s, my + 0.2, 0.5), lc)
        cv.solid(g.cap(mx - 1.4 * s, my + 0.2, mx + 1.6 * s, my + 0.2, 0.5), lc)
        cv.solid(g.cap(mx + 1.6 * s, my + 0.2, mx + 2.8 * s, my - 1.0 * s, 0.5), lc)
    elif mouth_kind == 'smirk':
        cv.solid(g.cap(mx - 2.8 * s, my + 0.3, mx + 1.0 * s, my + 0.3, 0.5), lc)
        cv.solid(g.cap(mx + 1.0 * s, my + 0.3, mx + 2.8 * s, my - 1.2 * s, 0.5), lc)
    elif mouth_kind == 'frown':
        cv.solid(g.cap(mx - 3.4 * s, my + 1.6 * s, mx - 1.6 * s, my + 0.2, 0.5), lc)
        cv.solid(g.cap(mx - 1.6 * s, my + 0.2, mx + 1.2 * s, my + 0.2, 0.5), lc)
        cv.solid(g.cap(mx + 1.2 * s, my + 0.2, mx + 2.6 * s, my + 1.4 * s, 0.5), lc)
    elif mouth_kind in ('laugh', 'grin', 'shout', 'grit', 'o'):
        if mouth_kind == 'laugh':
            m = g.poly([(mx - 4.2 * s, my - 1.4 * s), (mx + 3.4 * s, my - 1.4 * s),
                        (mx + 2.0 * s, my + 2.4 * s), (mx - 0.8 * s, my + 3.4 * s),
                        (mx - 3.0 * s, my + 1.6 * s)])
        elif mouth_kind == 'grin':
            m = g.poly([(mx - 3.6 * s, my - 1.0 * s), (mx + 3.0 * s, my - 1.2 * s),
                        (mx + 1.8 * s, my + 1.4 * s), (mx - 2.4 * s, my + 1.4 * s)])
        elif mouth_kind == 'shout':
            m = g.poly([(mx - 3.4 * s, my - 1.8 * s), (mx + 3.0 * s, my - 2.2 * s),
                        (mx + 2.6 * s, my + 2.6 * s), (mx - 2.8 * s, my + 2.2 * s)])
        elif mouth_kind == 'grit':
            m = g.poly([(mx - 3.4 * s, my - 1.2 * s), (mx + 3.0 * s, my - 1.2 * s),
                        (mx + 3.0 * s, my + 1.4 * s), (mx - 3.4 * s, my + 1.4 * s)])
        else:
            m = g.ell(mx - 0.2 * s, my + 0.8 * s, 1.7 * s, 2.3 * s)
        ring = dil4(m) & ~m
        cv.solid(ring, mix(INK, MOUTH_DARK, 0.3), pid=2)
        cv.solid(m, MOUTH_DARK, pid=2)
        ys = np.nonzero(m)[0]
        if mouth_kind in ('laugh', 'grin', 'shout', 'grit') and len(ys):
            top = ys.min()
            cv.solid(m & (g.Y < top + 1.6 * s), EYE_W)
            if mouth_kind in ('shout', 'grit'):
                bot = ys.max()
                cv.solid(m & (g.Y > bot - 1.0 * s), mix(EYE_W, sk[1], 0.25))
            if mouth_kind == 'grit':
                cv.solid(m & (np.abs(g.X - mx) < 0.5), mix(EYE_W, INK, 0.4))
            if mouth_kind in ('laugh',):
                cv.solid(m & g.ell(mx - 0.5 * s, my + 3.0 * s, 2.4 * s, 1.6 * s), TONGUE)


def draw_hair_strands(cv, hair, hm, cx, cy, R):
    g = cv.g
    inner = ero4(hair)
    xc, yc = cx - 0.15 * R, cy - 0.95 * R
    ang = np.arctan2(g.Y - yc, g.X - xc)
    dist = np.hypot(g.X - xc, g.Y - yc)
    strand = inner & (np.sin(ang * 13.0 + dist * 0.15) > 0.82) & (dist > 0.25 * R)
    cv.rgb[strand & (cv.pid == 1)] = hm[1]
    shine = inner & (np.abs(dist - 0.62 * R) < 0.9) & (g.X < cx + 0.15 * R) & (g.Y < cy - 0.2 * R)
    shine &= np.sin(ang * 13.0 + dist * 0.15) < 0.5
    cv.rgb[shine & (cv.pid == 1)] = hm[2]


def draw_glasses_portrait(cv, ch, cx, cy, R, expr):
    g = cv.g
    s = R / 15.0
    ey = cy + 3.2 * s
    kind = ch['glasses']
    centers = [(cx + PF['en'] * s, 4.6 * s), (cx + (PF['ef'] + 0.2) * s, 3.6 * s)]
    if kind == 'shades':
        lens = np.zeros_like(cv.a)
        for ex, rx in centers:
            lens |= g.ell(ex, ey + 0.4 * s, rx + 0.6 * s, 3.4 * s)
        bar = g.cap(cx + (PF['en'] - 5) * s, ey - 2.6 * s, cx + (PF['ef'] + 3.4) * s, ey - 2.6 * s, 0.9 * s)
        ring = dil4(lens | bar) & ~(lens | bar)
        cv.solid(ring, INK)
        cv.solid(bar, INK)
        cv.solid(lens, hx('#22203a'))
        for ex, rx in centers:
            st = g.cap(ex - rx * 0.5, ey - 0.6 * s, ex + rx * 0.1, ey - 2.0 * s, 0.6) & lens
            cv.solid(st, hx('#8a96c8'))
            st2 = g.cap(ex + rx * 0.2, ey + 1.6 * s, ex + rx * 0.6, ey + 0.8 * s, 0.45) & lens
            cv.solid(st2, hx('#4a4a7a'))
        cv.solid(g.cap(cx + (PF['en'] - 5) * s, ey - 2.4 * s, cx - 7.0 * s, ey - 1.2 * s, 0.7 * s), INK)
        return
    fr = {'round': hx('#3a2e3a'), 'thick': INK, 'cateye': hx('#b02a62')}[kind]
    th = 0.75 if kind == 'round' else 1.1
    frames = np.zeros_like(cv.a)
    for i, (ex, rx) in enumerate(centers):
        ry = 4.2 * s if kind != 'thick' else 3.8 * s
        rxx = rx + (0.4 if kind == 'thick' else 0.0)
        outer = g.ell(ex, ey + 0.3, rxx + th, ry + th)
        inner = g.ell(ex, ey + 0.3, rxx, ry)
        ringm = outer & ~inner
        if kind == 'cateye':
            ringm |= g.poly([(ex + (rxx if i == 1 else -rxx) * 0.6, ey - ry), (ex + (rxx + 2.6 if i == 1 else -rxx - 2.6), ey - ry - 1.6),
                             (ex + (rxx + 0.6 if i == 1 else -rxx - 0.6), ey - 0.5)])
        # tint lenses
        cv.rgb[inner & cv.a] = (cv.rgb[inner & cv.a] * 0.85 + np.array([230, 240, 255]) * 0.15).astype(np.uint8)
        frames |= ringm
    mid = (PF['en'] + PF['ef']) / 2.0
    frames |= g.cap(cx + (mid - 0.6) * s, ey - 0.6 * s, cx + (mid + 0.4) * s, ey - 0.6 * s, th)
    frames |= g.cap(cx + (PF['en'] - 4.6) * s, ey - 0.4 * s, cx - 7.0 * s, ey + 0.4 * s, th * 0.8)
    cv.solid(frames, fr)
    gl = frames & ~shift(frames, -1, -1)
    if kind != 'thick':
        cv.rgb[gl] = mix(fr, (255, 255, 255), 0.3)


def fill3(cv, mask, m, pid, k=3, ring=None):
    """3-tone + highlight fill for portraits."""
    cv.fill(mask, m, pid=pid, k=k, hi=True, ring=ring)
    deep = mask & ~shift(mask, 1, 1)
    cv.rgb[deep] = m[3]


PORTRAIT_SW = {'normal': 23, 'slim': 20, 'heavy': 28, 'big': 31, 'tall': 23, 'kid': 18,
               'elder': 22}


def draw_portrait_body(cv, ch, cx, cy, R):
    g = cv.g
    X, Y = g.X, g.Y
    sk = skin_of(ch)
    sw = PORTRAIT_SW[ch['body']]
    if ch.get('wide'):
        sw += 4
    xc = cx + 3.0
    ys = cy + R * 1.08 + 3.5
    if ch['body'] == 'elder':
        ys += 1.5
    j = ch['jacket']
    sm = shirt_mat(ch)
    # neck
    nw = 5.0 if ch['body'] not in ('heavy', 'big') else 7.0
    if ch['body'] == 'kid':
        nw = 4.0
    neck = g.poly([(cx - nw - 1, cy + 8), (cx + nw - 1, cy + 8), (cx + nw + 0.5, ys + 6),
                   (cx - nw - 0.5, ys + 6)])
    fill3(cv, neck, sk, pid=10, k=3)
    # torso
    pts = [(xc - sw - 5, 64.5), (xc - sw - 1, ys + 7), (xc - sw + 6, ys), (xc + sw - 9, ys + 0.5),
           (xc + sw - 2, ys + 6), (xc + sw + 2, 64.5)]
    tor = g.poly(pts) | g.ell(xc - sw + 5.5, ys + 7, 7, 7) | g.ell(xc + sw - 7, ys + 7.5, 6.5, 6.5)
    tor &= Y >= ys - 1
    near_sh = X < xc - sw + 11          # near shoulder/arm region
    far_sh = X > xc + sw - 8
    chest_x = xc + 5.0                  # sternum line (3/4 view)
    top = sm
    if ch['dress'] and not j:
        top = cm(ch['dress'])
    tank = ch['sleeves'] == 'none' and not j
    fill3(cv, tor, sk if (tank or (ch['sleeves'] == 'none' and j and j['sleeves'] == 'none')) else top, pid=11)
    if ch['sleeves'] == 'none':
        tk = tor & ~near_sh & ~far_sh
        tk &= ~(g.ell(chest_x - 1, ys - 1, 7.5, 5.5))
        fill3(cv, tk, sm, pid=11)
    # shirt patterns
    if ch['shirt'] in ('stripe_rw', 'stripe_nw'):
        st = tor & (((Y.astype(int) - int(ys)) % 4) < 2) & (cv.rgb == top[0]).all(-1)
        cv.rgb[st] = C['white'][0]
        st2 = tor & (((Y.astype(int) - int(ys)) % 4) < 2) & (cv.rgb == top[1]).all(-1)
        cv.rgb[st2] = C['white'][1]
    if ch['shirt'] == 'hawaii':
        for (fx, fy) in [(xc - 14, ys + 8), (xc - 2, ys + 13), (xc + 12, ys + 7), (xc + 6, ys + 17),
                         (xc - 18, ys + 16), (xc + 18, ys + 15), (xc - 8, ys + 4)]:
            fl = g.ell(fx, fy, 2.2, 2.0) & tor
            cv.rgb[fl] = hx('#f4e8a0')
            cv.rgb[g.ell(fx, fy, 0.8, 0.8) & tor] = hx('#c03a3a')
            lf = g.ell(fx + 2.5, fy + 1.5, 1.6, 0.9, 30) & tor & ~fl
            cv.rgb[lf] = hx('#3a8a5a')
    # neckline of the shirt (V / crew)
    crew = g.ell(cx + 0.5, ys + 0.5, nw + 2.0, 3.2) & tor
    if not tank and ch['shirt'] not in ('hawaii',):
        cv.rgb[crew & ~g.ell(cx + 0.5, ys - 0.5, nw + 0.8, 3.0)] = top[1]
    cv.solid(neck & (Y < ys + 2.5) & ~tor, sk[0])
    # overalls / coverall
    if ch['overalls']:
        om = cm(ch['overalls'])
        if ch.get('ovstyle') == 'tied':
            pass
        else:
            bib = tor & (X > xc - sw + 9) & (X < xc + sw - 5) & (Y > ys + 9)
            fill3(cv, bib, om, pid=12, ring={11})
            for x0, x1 in ((xc - sw + 10, xc - sw + 5), (xc + sw - 7, xc + sw - 6)):
                strap = g.cap(x0, ys + 11, x1, ys + 1, 1.6) & tor
                fill3(cv, strap, om, pid=12, k=1)
            for bx_ in (xc - sw + 10.5, xc + sw - 7):
                cv.solid(g.ell(bx_, ys + 11, 1.2, 1.2), C['gold'][0])
    # jacket
    if j:
        jm = cm(j['color'])
        kind = j['kind']
        jac = tor.copy()
        if j['sleeves'] == 'none':
            jac &= ~near_sh & ~far_sh
        if kind == 'safety':
            jac = tor & (X > xc - sw + 7) & (X < xc + sw - 4)
        fill3(cv, jac, jm, pid=13, ring={11, 12})
        if kind in ('satin', 'leather', 'vest', 'slicker') or j['color'] == 'leather':
            sh_ = jac & g.ell(xc - sw + 6, ys + 6, 4, 3) & ~shift(jac, -2, -2)
            cv.rgb[jac & (np.abs((X - (xc - sw + 8)) + (Y - ys - 9) * 0.6) < 0.8) & (Y < ys + 14)] = jm[2]
        opened = j['open'] and kind not in ('chef', 'track', 'hoodie', 'padded')
        if opened:
            v = g.poly([(cx - 3, ys - 2), (cx + 9, ys - 2), (chest_x + 3, 64.5), (chest_x - 1, 64.5)])
            if kind == 'safety':
                v = g.poly([(cx - 4, ys - 2), (cx + 10, ys - 2), (chest_x + 4, 64.5), (chest_x - 2, 64.5)])
            if kind == 'cardigan':
                v = g.poly([(cx - 3, ys - 2), (cx + 9, ys - 2), (chest_x + 1, ys + 14), (chest_x, ys + 14)])
            v &= jac
            inner_col = sm
            cv.fill(v, inner_col, pid=14, k=2)
            # lapels / jacket edges
            edge = dil4(v) & ~v & jac
            cv.rgb[edge] = jm[3]
            if kind in ('coat', 'suit', 'labcoat', 'jacket'):
                lap_l = g.poly([(cx - 3, ys - 1), (cx - 6, ys + 2), (chest_x - 4, ys + 13), (chest_x - 1, ys + 11)]) & jac
                lap_r = g.poly([(cx + 9, ys - 1), (cx + 13, ys + 2), (chest_x + 5, ys + 13), (chest_x + 2.5, ys + 11)]) & jac
                for lp in (lap_l, lap_r):
                    cv.fill(lp, (jm[1], jm[3], jm[0], jm[3]), pid=13, k=1)
                    cv.rgb[dil4(lp) & ~lp & jac & ~v] = jm[3]
            if kind == 'cardigan':
                for by in (ys + 16, ys + 20, ys + 24):
                    cv.solid(g.ell(chest_x + 0.5, by, 0.9, 0.9) & jac, C['cream'][1])
        else:
            if kind == 'chef':
                for bx_ in (chest_x - 3, chest_x + 4):
                    for by in (ys + 7, ys + 12, ys + 17):
                        cv.solid(g.ell(bx_, by, 1.0, 1.0) & jac, C['gray'][1])
                cv.rgb[jac & (np.abs(X - (chest_x + 0.5) + (Y - ys) * 0.15) < 0.6) & (Y > ys + 4)] = jm[1]
            elif kind == 'padded':
                q = jac & (((Y.astype(int) - int(ys)) % 4) == 0)
                cv.rgb[q] = jm[1]
                cv.rgb[jac & (np.abs(X - chest_x) < 0.6) & (Y > ys + 2)] = jm[3]
            else:
                zp = jac & (np.abs(X - chest_x) < 0.6) & (Y > ys + 2)
                cv.rgb[zp] = jm[3]
                if kind == 'track' and j['trim']:
                    tm = cm(j['trim'])
                    for off in (-2.0, 2.0):
                        st = tor & (np.abs((X - (xc - sw + 6 + off)) - (Y - ys) * 0.35) < 0.7)
                        cv.rgb[st] = tm[0]
        if j['stripe']:
            stm = cm(j['stripe'])
            st = jac & (Y > ys + 10) & (Y < ys + 13) & (cv.pid == 13)
            cv.rgb[st] = stm[0]
            cv.rgb[st & (Y >= ys + 12)] = stm[1]
        if kind == 'safety':
            refl = jac & (((Y > ys + 12) & (Y < ys + 14.5)) | (np.abs(X - (xc - sw + 12)) < 1.2) |
                          (np.abs(X - (xc + sw - 9)) < 1.2)) & (cv.pid == 13)
            cv.rgb[refl] = hx('#f0ecb0')
        if kind == 'satin' and j['trim']:
            tm = cm(j['trim'])
            col = jac & (dil4(dil4(cv.pid == 14)) | (Y < ys + 2.5)) & (cv.pid == 13)
            cv.rgb[col] = tm[0]
        if kind == 'varsity':
            col = jac & (Y < ys + 2.5)
            cv.rgb[col] = C['cream'][0]
            patch = jac & g.ell(chest_x - 9, ys + 11, 2.6, 3.0) & (cv.pid == 13)
            cv.fill(patch, C['cream'], pid=13, k=1)
            cv.rgb[patch & g.ell(chest_x - 9, ys + 11, 1.1, 1.8)] = jm[1]
        if j.get('trim') == 'pins':
            for (px_, py_, c) in [(chest_x - 6, ys + 9, 'red'), (chest_x - 10, ys + 13, 'yellow'),
                                  (chest_x + 9, ys + 10, 'cyan'), (chest_x - 4, ys + 15, 'pink')]:
                cv.solid(g.ell(px_, py_, 1.3, 1.3) & jac, C[c][0])
                cv.px(int(px_) - 1, int(py_) - 1, C[c][2])
        if kind == 'labcoat':
            pk = jac & (np.abs(X - (chest_x - 9)) < 3) & (np.abs(Y - (ys + 13)) < 0.6)
            cv.rgb[pk] = jm[1]
        if kind == 'slicker':
            for by in (ys + 9, ys + 15):
                cv.solid(g.ell(chest_x - 2.5, by, 0.9, 0.9) & jac, jm[3])
        if kind == 'hoodie' or j.get('collar') == 'hood':
            hc = jm if kind == 'hoodie' else sm
            hood = (g.ell(cx - 7, ys + 1, 9, 4.5) | g.ell(cx + 8, ys + 1, 6, 3.5)) & ~g.ell(cx + 0.5, ys - 1.5, nw + 1, 3.5)
            fill3(cv, hood, hc, pid=15, k=2, ring={11, 13, 14})
            if kind == 'hoodie':
                for dx in (1.5, 5.0):
                    cv.solid(g.cap(cx + dx, ys + 3, cx + dx + 0.3, ys + 9, 0.5), C['white'][1])
    # collars
    col = (j or {}).get('collar') or ch.get('collar')
    if col == 'turtle':
        tc = g.poly([(cx - nw - 1.5, ys - 5), (cx + nw + 1.5, ys - 5), (cx + nw + 2.5, ys + 2.5),
                     (cx - nw - 2.5, ys + 2.5)])
        fill3(cv, tc, sm, pid=16, k=2, ring={10, 11, 13, 14})
        for yy in (ys - 2.5, ys):
            cv.rgb[tc & (np.abs(Y - yy) < 0.5) & (X > cx - nw)] = sm[1]
        if ch.get('torn'):
            tear = tor & g.ell(xc - sw + 8, ys + 4, 6, 4)
            jag = ((X.astype(int) * 3 + Y.astype(int) * 2) % 5) < 2
            cv.fill(tear & ~jag, sk, pid=11, k=1)
            cv.rgb[dil4(tear & ~jag) & ~(tear & ~jag) & tor] = sm[3]
    elif col == 'high':
        cc = cm(j['color']) if j else sm
        tc = g.poly([(cx - nw - 2.0, ys - 3.5), (cx + nw + 2.5, ys - 3.5), (cx + nw + 3.5, ys + 2.0),
                     (cx - nw - 3.0, ys + 2.0)])
        fill3(cv, tc, cc, pid=16, k=2, ring={10, 11, 13, 14})
        cv.rgb[tc & (np.abs(X - chest_x + 2) < 0.6)] = cc[3]
    elif col in ('shirt', 'lapel'):
        cc = sm if col == 'lapel' else (cm(j['color']) if j else sm)
        if col == 'lapel':
            cc = C['white']
        for sgn in (-1, 1):
            x0 = cx + 0.5 + sgn * (nw + 0.5)
            cp = g.poly([(x0, ys - 2.5), (cx + 0.5 + sgn * 1.0, ys + 1.5), (x0 + sgn * 3.5, ys + 4.0),
                         (x0 + sgn * 3.0, ys - 1.0)])
            fill3(cv, cp, cc, pid=16, k=1, ring={10, 11, 13, 14})
    # extras
    for e in ch['extras']:
        if e.startswith('suspenders'):
            smat = cm(e.split(':')[1])
            for x0, x1 in ((xc - sw + 9, xc - sw + 12), (chest_x + 7, chest_x + 6)):
                st = g.cap(x0, ys, x1, 64, 1.4) & tor
                fill3(cv, st, smat, pid=17, k=1, ring={11})
        if e == 'chain':
            for t in np.linspace(0, 1, 13):
                px_ = (xc - sw + 6) + t * (sw * 1.55)
                py_ = ys + 2 + math.sin(t * math.pi) * 9
                lk = g.ell(px_, py_, 1.6, 1.1, 30 if int(t * 12) % 2 else -30)
                cv.fill(lk & tor, C['steel'], pid=17, k=1, ring={11, 13, 14})
        if e == 'goldchain':
            ring_ = (np.abs(((X - cx - 2) / (nw + 5)) ** 2 + ((Y - ys + 1) / 8.0) ** 2 - 1.0) < 0.14) & (Y > ys) & tor
            cv.solid(ring_, C['gold'][0])
            cv.solid(g.ell(chest_x - 1, ys + 8, 1.6, 1.8), C['gold'][1])
        if e == 'whistle':
            cord = (np.abs(((X - cx - 1) / (nw + 2)) ** 2 + ((Y - ys + 2) / 11.0) ** 2 - 1.0) < 0.12) & (Y > ys) & tor
            cv.solid(cord, C['white'][0])
            wm = g.ell(chest_x - 1, ys + 11, 2.2, 1.4)
            fill3(cv, wm, C['steel'], pid=17, k=1, ring={11, 13, 14})
        if e == 'nametag':
            nt = g.rect(int(chest_x) - 11, int(ys) + 9, int(chest_x) - 5, int(ys) + 11) & tor
            fill3(cv, nt, C['white'], pid=17, k=1, ring={11, 13, 14})
            cv.rgb[nt & (Y.astype(int) == int(ys) + 10) & ((X.astype(int) % 2) == 0)] = C['charcoal'][0]
        if e == 'badge':
            bm = g.poly([(chest_x + 8, ys + 7), (chest_x + 12, ys + 7), (chest_x + 12, ys + 11),
                         (chest_x + 10, ys + 13), (chest_x + 8, ys + 11)])
            fill3(cv, bm, C['gold'], pid=17, k=1, ring={11, 13, 14})
        if e.startswith('bowtie'):
            bm = cm(e.split(':')[1])
            bt_ = g.poly([(cx - 3, ys - 1), (cx + 1, ys + 1.5), (cx - 3, ys + 4)]) | \
                g.poly([(cx + 6, ys - 1), (cx + 2, ys + 1.5), (cx + 6, ys + 4)]) | g.ell(cx + 1.5, ys + 1.5, 1.6, 1.6)
            fill3(cv, bt_, bm, pid=17, k=1, ring={10, 11, 13, 14, 16})
        if e.startswith('tie'):
            bm = cm(e.split(':')[1])
            tie = g.poly([(cx + 0.5, ys + 1), (cx + 3.5, ys + 1), (cx + 4.5, 64.5), (cx - 0.5, 64.5)])
            fill3(cv, tie, bm, pid=17, k=1, ring={14, 16})
        if e.startswith('bag') or e == 'newsbag':
            bc = cm(e.split(':')[1]) if ':' in e else C['cream']
            st = g.cap(xc - sw + 6, ys + 1, chest_x + 14, 64, 1.5) & tor
            fill3(cv, st, bc, pid=17, k=1, ring={11, 12, 13, 14})
            cv.solid(g.rect(int(chest_x) + 4, 58, int(chest_x) + 6, 60) & st, C['steel'][0])
    if ch.get('shawl'):
        shm = cm(ch['shawl'])
        sw_ = (g.poly([(xc - sw - 3, ys + 4), (cx - 3, ys - 2), (cx + 9, ys - 2), (xc + sw + 1, ys + 5),
                       (chest_x + 2, ys + 16)]) | g.ell(xc - sw + 5, ys + 8, 8, 7)) & (tor | (Y < ys + 2))
        sw_ &= Y >= ys - 2.5
        fill3(cv, sw_, shm, pid=18, ring={10, 11})
        pat = sw_ & (((X.astype(int) + Y.astype(int) * 2) % 6) == 0)
        cv.rgb[pat] = shm[2]
    if ch['apron']:
        am = cm(ch['apron'])
        bib = g.rect(int(chest_x) - 9, int(ys) + 8, int(chest_x) + 8, 63) & tor
        fill3(cv, bib, am, pid=19, k=2, ring={11, 13, 14})
        if ch.get('apron_stain'):
            cv.rgb[g.ell(chest_x + 2, ys + 16, 2.5, 1.6) & bib] = mix(am[1], C['brown'][0], 0.5)
        for x0, x1 in ((chest_x - 8, cx - nw), (chest_x + 7, cx + nw + 1)):
            st = g.cap(x0, ys + 8, x1, ys - 1, 0.9) & ~neck
            cv.solid(st & tor, am[1])
    if ch['dress'] and not j and not ch.get('shawl'):
        dm = cm(ch['dress'])
        colr = g.ell(cx + 1, ys + 1.5, nw + 4.5, 3.5) & ~g.ell(cx + 1, ys - 0.5, nw + 2.0, 3.2) & tor
        fill3(cv, colr, C['white'], pid=16, k=1)
    if ch['armband']:
        ab = tor & near_sh & (Y > ys + 13) & (Y < ys + 17)
        fill3(cv, ab, cm(ch['armband']), pid=17, k=1)
    # cast shadow of the head on the neck
    return ys


def render_portrait(ch, expr):
    bt = BODY[ch['body']]
    cv = Canvas(64, 64)
    g = cv.g
    R, cx, cy = 16.0, 29.0, 25.0
    tall_hair = ch['hair'] in ('puff', 'beehive')
    hat = ch['hat'][0] if ch['hat'] else None
    if tall_hair:
        R, cy = 14.0, 30.0
    elif hat in ('paper', 'police', 'fedora', 'hardhat') or ch['hair'] in ('mohawk', 'flattop',
                                                                           'spikes_up', 'pompadour'):
        R, cy = 15.0, 27.0
    if ch['body'] == 'kid':
        R, cy = 16.0, 27.0
    if ch['body'] == 'big':
        R, cy = 14.5, 26.0
    draw_portrait_body(cv, ch, cx, cy, R)
    hcv, hcx, hcy = draw_head(ch, bt, expr, portrait=True, pR=R, pc=(cx, cy))
    # neck shadow under the jaw
    head_m = hcv.a & (hcv.pid != 0)
    cast = shift(head_m, 0, -2) & ~head_m & (cv.pid == 10)
    cv.rgb[cast] = skin_of(ch)[1]
    cast2 = shift(head_m, 0, -1) & ~head_m & (cv.pid == 10)
    cv.rgb[cast2] = skin_of(ch)[3]
    cv.blit(hcv.rgb, hcv.a, hcv.sh, 0, 0, 20, ring={11, 12, 13, 14, 15, 16, 17, 18, 19})
    cv.outline()
    return cv.to_rgba()


def write_portrait(ch, out_id):
    strip = np.zeros((64, 320, 4), np.uint8)
    for i, e in enumerate(EXPRS):
        strip[:, i * 64:(i + 1) * 64] = render_portrait(ch, e)
    os.makedirs(OUT_POR, exist_ok=True)
    Image.fromarray(strip, 'RGBA').save(os.path.join(OUT_POR, out_id + '.png'), optimize=True)


# =============================================================================
# Biscuit -- scruffy tan terrier mix with a red collar (32x32 cells)
# =============================================================================

DOG_ANIMS = [('idle', 2), ('walk', 4), ('sit', 1), ('bark', 1)]


def render_dog_frame(f):
    cv = Canvas(48, 48)
    g = cv.g
    fur = mat('#c8a070', '#987048')
    furd = mat('#9a6a40', '#6e4628')
    fur_far = far(fur)
    collar = C['red']
    # frame params: body offset, leg phases, tail angle, head offset, sit, bark
    bob = [0, 1, 0, 1, 0, 1, 0, 0][f]
    tail = [-70, -55, -65, -80, -65, -80, -40, -75][f]
    legs = {0: (0, 0, 0, 0), 1: (0, 0, 0, 0),
            2: (24, -20, -20, 24), 3: (6, -30, -30, 6), 4: (-20, 24, 24, -20), 5: (-30, 6, 6, -30),
            6: (0, 0, 0, 0), 7: (-8, -8, 6, 6)}[f]
    sit = f == 6
    bark = f == 7
    by = 26.0 + bob * 0.5
    bx = 22.0
    body_ang = -28 if sit else (-6 if bark else 0)
    # body centre/back/front reference points
    a = math.radians(body_ang)
    fwd = np.array([math.cos(a), math.sin(a)])
    bc = np.array([bx, by])
    rear = bc - fwd * 5.0
    chest = bc + fwd * 5.0
    ground = 37.0
    # far legs
    def leg(top, ang, far_, length=7.0, thick=1.25):
        lift = 1.2 if ang <= -25 else 0.0
        footp = top + length * V(90 + ang) - np.array([0, lift])
        m = g.cap(top[0], top[1], footp[0], footp[1], thick)
        pm = g.ell(footp[0] + 0.7, footp[1] + 0.2, 1.6, 1.1)
        cv.fill(m | pm, fur_far if far_ else fur, pid=2 if far_ else 4, k=1,
                ring=None if far_ else {2})
        return footp
    if sit:
        # folded hind leg + straight front legs
        leg(chest + np.array([1.0, 2.0]), 4, True, 7.5)
        hind = g.ell(rear[0] + 1, rear[1] + 4.5, 4.2, 3.4)
        cv.fill(hind | g.ell(rear[0] + 3.5, ground - 0.5, 3.0, 1.4), fur_far, pid=2, k=1)
    else:
        leg(rear + np.array([-1.0, 2.0]), legs[1], True)
        leg(chest + np.array([-0.5, 2.0]), legs[3], True)
    # tail (scruffy, upright)
    tb = rear + np.array([-1.5, -2.0])
    tt = tb + 6.0 * V(tail - 20)
    tm = g.cap(tb[0], tb[1], tt[0], tt[1], 1.5) | g.ell(tt[0], tt[1], 1.6, 1.6)
    cv.fill(tm, fur, pid=1, k=1, hi=True)
    # body
    body = g.ell(bc[0], bc[1], 7.8, 3.9, body_ang)
    cv.fill(body, fur, pid=3, k=2, hi=True, ring={1, 2})
    saddle = g.ell(bc[0] - 1.5 * fwd[0], bc[1] - 2.6, 4.6, 2.0, body_ang) & body
    cv.fill(saddle, furd, pid=3, k=1)
    # scruffy fringe on back and belly
    for i, t in enumerate(np.linspace(-6, 5, 7)):
        p = bc + fwd * t + np.array([0, -4.2 if i % 2 == 0 else -4.6])
        cv.fill(g.ell(p[0], p[1], 1.0, 1.0) & ~cv.a | g.ell(p[0], p[1] + 0.5, 0.8, 0.8) & body,
                furd if i % 3 else fur, pid=3, k=0)
    belly = [bc + fwd * t + np.array([0, 4.4]) for t in (-3, 0, 3)]
    for p in belly:
        cv.fill(g.poly([(p[0] - 1.2, p[1] - 0.8), (p[0] + 1.2, p[1] - 0.8), (p[0], p[1] + 1.2)]),
                fur, pid=3, k=0)
    # near legs
    if sit:
        leg(chest + np.array([2.0, 2.4]), 0, False, 7.5)
        hind = g.ell(rear[0] + 2.5, rear[1] + 5.0, 4.4, 3.4)
        cv.fill(hind, fur, pid=4, k=2, ring={3, 2})
        cv.fill(g.ell(rear[0] + 5.5, ground - 0.8, 2.6, 1.3), fur, pid=4, k=1, ring={3})
    else:
        leg(rear + np.array([1.0, 2.4]), legs[0], False)
        leg(chest + np.array([1.5, 2.4]), legs[2], False)
    # head
    hc = chest + np.array([3.5, -5.0 + (-2.0 if bark else 0) + (-1.5 if sit else 0)])
    hcv = Canvas(48, 48)
    hg = hcv.g
    head = hg.ell(hc[0], hc[1], 4.3, 4.0) | hg.ell(hc[0] + 1.5, hc[1] + 1.0, 3.6, 3.2)
    hcv.fill(head, fur, pid=1, k=2, hi=True)
    snout = hg.ell(hc[0] + 4.4, hc[1] + 1.4, 2.8, 2.0)
    hcv.fill(snout, mat('#d8b488', '#a88058'), pid=2, k=1, ring={1})
    # beard tuft
    beard = hg.poly([(hc[0] + 2.4, hc[1] + 2.4), (hc[0] + 6.6, hc[1] + 2.6), (hc[0] + 4.0, hc[1] + 5.2),
                     (hc[0] + 2.0, hc[1] + 4.2)])
    hcv.fill(beard, mat('#e0c49a', '#b08860'), pid=2, k=1)
    if bark:
        mouth = hg.poly([(hc[0] + 2.6, hc[1] + 2.0), (hc[0] + 7.4, hc[1] + 2.4), (hc[0] + 6.2, hc[1] + 4.6)])
        hcv.solid(mouth, MOUTH_DARK)
        hcv.solid(hg.ell(hc[0] + 4.6, hc[1] + 3.6, 1.0, 0.6) & mouth, TONGUE)
        jaw = hg.cap(hc[0] + 2.4, hc[1] + 4.0, hc[0] + 6.2, hc[1] + 5.2, 0.9)
        hcv.fill(jaw & ~mouth, mat('#d8b488', '#a88058'), pid=2, k=0)
    # nose + eye + brow
    hcv.px(int(hc[0] + 7.0), int(hc[1] + 0.5), INK)
    hcv.px(int(hc[0] + 6.5), int(hc[1] + 0.5), INK)
    ex, ey = int(hc[0] + 1.5), int(hc[1] - 0.5)
    if f == 1:
        hcv.px(ex, ey + 1, INK); hcv.px(ex + 1, ey + 1, INK)
    else:
        hcv.px(ex, ey, EYE_W); hcv.px(ex + 1, ey, INK); hcv.px(ex + 1, ey + 1, INK)
        hcv.px(ex, ey + 1, INK)
    hcv.px(ex, ey - 2, furd[1]); hcv.px(ex + 1, ey - 2, furd[1]); hcv.px(ex + 2, ey - 1, furd[1])
    # ear: folded terrier ear
    ear = hg.poly([(hc[0] - 2.8, hc[1] - 2.6), (hc[0] + 0.6, hc[1] - 5.8), (hc[0] + 1.6, hc[1] - 2.8),
                   (hc[0] + 0.0, hc[1] - 0.6)])
    if bark or f == 0:
        ear = hg.poly([(hc[0] - 2.4, hc[1] - 3.0), (hc[0] - 0.6, hc[1] - 7.2), (hc[0] + 1.6, hc[1] - 3.2)])
    hcv.fill(ear, furd, pid=3, k=1, ring={1})
    # scruffy head tufts
    for dx, dy in [(-3.5, -3.0), (-1.0, -4.4), (-4.4, -0.5)]:
        hcv.fill(hg.ell(hc[0] + dx, hc[1] + dy, 1.1, 1.1) & ~hcv.a, fur, pid=1, k=0)
    cv.blit(hcv.rgb, hcv.a, hcv.sh, 0, 0, 5, ring={3, 4})
    # collar
    cm_ = g.cap(hc[0] - 3.8, hc[1] + 1.6, hc[0] - 0.4, hc[1] + 5.0, 1.05) & cv.a
    cv.fill(cm_, collar, pid=6, k=0)
    cv.px(int(hc[0] + 0.5), int(hc[1] + 5.2), C['gold'][0])
    cv.outline()
    # place: bottom row 29, stance centre at 16
    ys, xs = np.nonzero(cv.a)
    dy = 29 - ys.max()
    dx = int(round(16 - (xs.min() + xs.max() + 1) / 2.0))
    out = np.zeros((32, 32, 4), np.uint8)
    full = cv.to_rgba()
    clipped = 0
    for y, x in zip(ys, xs):
        ny, nx = y + dy, x + dx
        if 0 <= ny < 32 and 0 <= nx < 32:
            out[ny, nx] = full[y, x]
        else:
            clipped += 1
    return out, clipped


def write_dog():
    sheet = np.zeros((64, 128, 4), np.uint8)
    clipped = 0
    for f in range(8):
        cell, c = render_dog_frame(f)
        clipped += c
        r, col = divmod(f, 4)
        sheet[r * 32:(r + 1) * 32, col * 32:(col + 1) * 32] = cell
    os.makedirs(OUT_SPR, exist_ok=True)
    Image.fromarray(sheet, 'RGBA').save(os.path.join(OUT_SPR, 'biscuit.png'), optimize=True)
    anims = {}
    i = 0
    for n, c in DOG_ANIMS:
        anims[n] = [i, c]
        i += c
    meta = {'id': 'biscuit', 'cell': [32, 32], 'anchor': [16, 30], 'columns': 4, 'anims': anims}
    with open(os.path.join(OUT_SPR, 'biscuit.json'), 'w') as f:
        f.write(json_dump(meta))
    return clipped


# =============================================================================
# Sheet assembly
# =============================================================================

def poses_for(ch):
    return civilian_poses() if ch['civilian'] else fighter_poses()


def render_sheet(ch):
    poses = poses_for(ch)
    sheet = np.zeros((512, 512, 4), np.uint8)
    hands = []
    clipped_total = 0
    for i, p in enumerate(poses):
        cell, hand, clipped = render_frame(ch, p)
        clipped_total += clipped
        r, c = divmod(i, 8)
        sheet[r * 64:(r + 1) * 64, c * 64:(c + 1) * 64] = cell
        hands.append(hand)
    return sheet, hands, clipped_total


def write_sheet(ch, sheet, hands):
    os.makedirs(OUT_SPR, exist_ok=True)
    Image.fromarray(sheet, 'RGBA').save(os.path.join(OUT_SPR, ch['id'] + '.png'), optimize=True)
    meta = {'id': ch['id'], 'cell': [64, 64], 'anchor': [32, 60], 'columns': 8,
            'anims': anim_table(), 'hand': hands}
    with open(os.path.join(OUT_SPR, ch['id'] + '.json'), 'w') as f:
        f.write(json_dump(meta))


def json_dump(meta):
    # compact but readable: one hand entry per line group
    parts = ['{\n']
    keys = list(meta.keys())
    for i, k in enumerate(keys):
        v = meta[k]
        if k == 'hand':
            s = '[' + ', '.join(json.dumps(h) for h in v) + ']'
        elif k == 'anims':
            s = '{' + ', '.join('%s: %s' % (json.dumps(a), json.dumps(b)) for a, b in v.items()) + '}'
        else:
            s = json.dumps(v)
        parts.append('  %s: %s%s\n' % (json.dumps(k), s, ',' if i < len(keys) - 1 else ''))
    parts.append('}\n')
    return ''.join(parts)


DISPLAY = {
    'nico': 'Nico Vale', 'mara': 'Mara Quinn', 'eli': 'Eli Mercer', 'rook': 'Victor Rook',
    'rook_p2': 'Victor Rook (phase 2)', 'dot': 'Dot Kessler', 'jett': 'Jett Vance',
    'gus': 'Gus Pereira', 'duke': 'Duke Brannigan', 'rhea': 'Rhea Pike', 'lou': 'Lou Pike',
    'otto': 'Otto Kragg', 'sabine': 'Capt. Sabine Holt', 'price': 'Officer Dana Price',
    'hollis': 'Mr. Hollis', 'benny': 'Coach Benny', 'lacey': 'Lacey Tran', 'pip': 'Pip',
    'alvarez': 'Mrs. Alvarez', 'fong': 'Mr. Fong', 'rosa': 'Rosa Delgado', 'bigmo': 'Big Mo',
    'teddy': 'Teddy', 'hank': 'Hank', 'marv': 'Marv', 'towna': 'Neighbor A (jogger)',
    'townb': 'Neighbor B (suit, briefcase)', 'townc': 'Neighbor C (teen, hoodie)',
    'townd': 'Neighbor D (grocery bag)',
}


def write_doc():
    origin = 'procedurally generated by tools/art/gen_characters.py; original; project-owned'
    L = ['# Character assets', '',
         'All files below are ' + origin + '.',
         'No third-party, traced or ROM-derived imagery is used. Rebuild with:', '',
         '```', 'python3 tools/art/gen_characters.py', '```', '',
         'Sprite sheets follow `docs/ART_BIBLE.md` section 3: 512x512 PNG, 8x8 grid of 64x64 cells, '
         'frames 0-57 in art-bible order (cells 58-63 empty), foot anchor (32, 60), facing right. '
         'Each sheet has a JSON sidecar with `anims` (name -> [start, count]) and `hand` '
         '(58 x [x, y, angle_deg] front-hand grip points; carry frames give the top-centre point '
         'between the raised hands).', '',
         'Characters flagged *civilian* use relaxed idle/walk/run arm poses instead of a fighting '
         'guard; all other frames are identical in layout.', '',
         '## Humanoid sprite sheets', '',
         '| id | who | body type | civilian | files | origin |', '|---|---|---|---|---|---|']
    for ch in ALL_CHARS:
        cid = ch['id']
        if cid in DISPLAY:
            who = DISPLAY[cid]
        else:
            g, a = cid.split('_')
            who = '%s %s' % (GANG_NAMES[g], a)
        body = ch['body'] + (' (wide)' if ch.get('wide') else '') + (' (bulked)' if ch.get('bulk') else '')
        L.append('| `%s` | %s | %s | %s | `game/assets/sprites/characters/%s.png`, `%s.json` | %s |' % (
            cid, who, body, 'yes' if ch['civilian'] else 'no', cid, cid, origin))
    L += ['', '## Animal', '',
          '| id | who | body type | files | origin |', '|---|---|---|---|---|',
          '| `biscuit` | Biscuit, scruffy tan terrier mix, red collar | dog (32x32 cells, anchor (16, 30), '
          '4 columns x 2 rows: idle 2, walk 4, sit 1, bark 1) | '
          '`game/assets/sprites/characters/biscuit.png`, `biscuit.json` | ' + origin + ' |', '',
          '## Portraits', '',
          '320x64 PNG strips, five 64x64 busts: neutral, happy, angry, surprised, sad.', '',
          '| file | depicts | body type | origin |', '|---|---|---|---|']
    for pid in PORTRAIT_IDS:
        L.append('| `game/assets/portraits/%s.png` | %s | %s | %s |' % (
            pid, DISPLAY[pid], CHAR_BY_ID[pid]['body'], origin))
    for gang, rep in GANG_PORTRAIT.items():
        L.append('| `game/assets/portraits/%s.png` | %s representative (`%s`) | %s | %s |' % (
            gang, GANG_NAMES[gang], rep, CHAR_BY_ID[rep]['body'], origin))
    L += ['', '## Generator', '',
          '| file | purpose | origin |', '|---|---|---|',
          '| `tools/art/gen_characters.py` | paper-doll renderer: per-body-type skeleton, 58-frame pose '
          'table, two-tone shading, ink contours, 1px `#1a1220` outline; portraits and Biscuit | '
          'original; project-owned |', '']
    os.makedirs(os.path.dirname(OUT_DOC), exist_ok=True)
    with open(OUT_DOC, 'w') as f:
        f.write('\n'.join(L))


def main(argv):
    only = None
    if '--only' in argv:
        only = set(argv[argv.index('--only') + 1].split(','))
    chars = [c for c in ALL_CHARS if only is None or c['id'] in only]
    if '--portraits-only' in argv:
        chars = []
    for ch in chars:
        sheet, hands, clipped = render_sheet(ch)
        write_sheet(ch, sheet, hands)
        print('%-16s %s%s' % (ch['id'], ch['body'], ('  CLIPPED %d px' % clipped) if clipped else ''))
    if only is None:
        write_doc()
    if only is None or 'biscuit' in only:
        c = write_dog()
        print('biscuit          dog%s' % (('  CLIPPED %d px' % c) if c else ''))
    for pid in PORTRAIT_IDS:
        if only is None or pid in only or 'portraits' in only:
            write_portrait(CHAR_BY_ID[pid], pid)
    for gang, rep in GANG_PORTRAIT.items():
        if only is None or gang in only or 'portraits' in only:
            write_portrait(CHAR_BY_ID[rep], gang)


if __name__ == '__main__':
    main(sys.argv[1:])
