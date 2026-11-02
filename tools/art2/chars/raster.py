"""Supersampled vector raster core for the v2 character generator.

Everything is drawn in *world units* (u). A Canvas maps u -> supersampled pixels
(ppu = SS * density). Shapes are filled as hard masks at the supersampled
resolution and box-downsampled at the end, which gives clean anti-aliasing.

Look: inked + cel shaded.
  * each *group* (a limb, the torso, the head ...) is one merged mask, so joints
    never show seams; its parts get 3-tone cel shading by silhouette offsets
  * where a group overlaps earlier groups, a 1 tx inner contour is inked
  * after all groups: 2 tx outer outline in a darkened, hue-shifted local colour
    and a thin cool rim light on the back edge.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4                     # supersample factor (ss px per output texel)

# Key light: upper-front (character faces +x). AWAY points from the light.
LIGHT = np.array([0.62, -0.78])
AWAY = -LIGHT
RIM_DIR = np.array([-0.85, -0.35])       # rim light comes from behind / above
INK = (26, 18, 32)
RIM_COL = (196, 214, 255)


def clamp01(x):
    return np.clip(x, 0.0, 1.0)


def lerp_c(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def _rgb_to_hsv(c):
    r, g, b = [v / 255.0 for v in c]
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        h = 0.0
    elif mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    h *= 60
    s = 0 if mx == 0 else d / mx
    return h, s, mx


def _hsv_to_rgb(h, s, v):
    h %= 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return ((r + m) * 255, (g + m) * 255, (b + m) * 255)


def shade_of(c, amt=1.0):
    """Cel shadow tone: darker, hue pushed toward violet-blue (~20 deg), a bit more saturated."""
    h, s, v = _rgb_to_hsv(c)
    target = 250.0
    dh = ((target - h + 180) % 360) - 180
    h2 = h + max(-22, min(22, dh)) * amt
    s2 = min(1.0, s * (1 + 0.12 * amt) + 0.06 * amt)
    v2 = v * (1 - 0.30 * amt)
    return _hsv_to_rgb(h2, s2, v2)


def light_of(c, amt=1.0):
    """Light tone: brighter, nudged warm."""
    out = lerp_c(c, (255, 244, 222), 0.30 * amt)
    return tuple(min(255, v * (1 + 0.04 * amt)) for v in out)


def ink_of(c):
    """Outline colour: darkened, hue-shifted local colour (never pure black)."""
    sh = shade_of(c, 1.6)
    return lerp_c(sh, INK, 0.70)


class Mat:
    """3-tone material."""

    def __init__(self, base, shadow=None, light=None, ink=None, gloss=0.0):
        self.base = tuple(float(v) for v in base)
        self.shadow = tuple(float(v) for v in (shadow if shadow is not None else shade_of(self.base)))
        self.light = tuple(float(v) for v in (light if light is not None else light_of(self.base)))
        self.ink = tuple(float(v) for v in (ink if ink is not None else ink_of(self.base)))
        self.deep = lerp_c(self.shadow, INK, 0.35)
        self.gloss = gloss

    def darker(self, t=0.25):
        return Mat(lerp_c(self.base, self.shadow, t * 2.2), lerp_c(self.shadow, INK, t), self.base)


def hexc(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


# ----------------------------------------------------------------------------- geometry

def rot(p, ang, c=(0.0, 0.0)):
    ca, sa = math.cos(ang), math.sin(ang)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)


def ellipse_pts(cx, cy, rx, ry, ang=0.0, n=40, a0=0.0, a1=2 * math.pi):
    pts = []
    for i in range(n):
        t = a0 + (a1 - a0) * i / (n - (0 if a1 - a0 < 2 * math.pi - 1e-6 else 0))
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append(rot((x, y), ang, (0, 0)))
    return [(cx + x, cy + y) for x, y in pts]


def catmull(pts, closed=True, steps=6):
    """Catmull-Rom spline through control points."""
    out = []
    n = len(pts)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if closed else pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[(i + 1) % n] if closed else pts[min(i + 1, n - 1)]
        p3 = pts[(i + 2) % n] if closed else pts[min(i + 2, n - 1)]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    if not closed:
        out.append(pts[-1])
    return out


def seg_quad(a, b, ra, rb):
    """Tapered quad between circles (a, ra) and (b, rb) (outer tangents approx)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / L, dx / L
    return [(a[0] + nx * ra, a[1] + ny * ra), (b[0] + nx * rb, b[1] + ny * rb),
            (b[0] - nx * rb, b[1] - ny * rb), (a[0] - nx * ra, a[1] - ny * ra)]


def ribbon(pts, widths):
    """Closed polygon for a variable-width stroke along an open polyline."""
    n = len(pts)
    left, right = [], []
    for i in range(n):
        if i == 0:
            d = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        elif i == n - 1:
            d = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
        else:
            d = (pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1])
        L = math.hypot(*d) or 1e-6
        nx, ny = -d[1] / L, d[0] / L
        w = widths[i] if isinstance(widths, (list, tuple)) else widths
        left.append((pts[i][0] + nx * w, pts[i][1] + ny * w))
        right.append((pts[i][0] - nx * w, pts[i][1] - ny * w))
    return left + right[::-1]


# ----------------------------------------------------------------------------- canvas

class Canvas:
    """Premultiplied float canvas in supersampled pixels.

    x0,y0,x1,y1: world-unit bounds; den: texels per world unit."""

    def __init__(self, x0, y0, x1, y1, den=2.0):
        self.x0, self.y0 = x0, y0
        self.den = den
        self.ppu = SS * den
        self.W = int(round((x1 - x0) * self.ppu))
        self.H = int(round((y1 - y0) * self.ppu))
        self.col = np.zeros((self.H, self.W, 3), np.float32)
        self.a = np.zeros((self.H, self.W), np.float32)
        self.tx = SS          # ss pixels per output texel

    # coordinates
    def P(self, p):
        return ((p[0] - self.x0) * self.ppu, (p[1] - self.y0) * self.ppu)

    def PP(self, pts):
        return [self.P(p) for p in pts]

    def u(self, tx):
        """Output texels -> world units."""
        return tx / self.den

    # masks
    def new_mask(self):
        return Image.new('L', (self.W, self.H), 0)

    def group(self, **kw):
        return Group(self, **kw)

    # finishing
    def finish(self, outline_tx=2.0, rim=True, rim_tx=1.0):
        A = self.a
        solid = A > 0.5
        m = Image.fromarray((solid * 255).astype(np.uint8))
        # octagonal dilation by outline_tx texels
        r = int(round(outline_tx * self.tx))
        d = m
        for i in range(r):
            d = d.filter(ImageFilter.MaxFilter(3)) if i % 2 == 0 else _cross_dilate(d)
        dil = np.asarray(d, np.float32) / 255.0
        ring = clamp01(dil - A)
        # local colour for the ring: blurred premultiplied colour / blurred alpha
        blur_r = r * 1.2 + 2
        pc = Image.fromarray(np.clip(self.col * 255, 0, 255).astype(np.uint8))
        pa = Image.fromarray(np.clip(A * 255, 0, 255).astype(np.uint8))
        bc = np.asarray(pc.filter(ImageFilter.GaussianBlur(blur_r)), np.float32) / 255.0
        ba = np.asarray(pa.filter(ImageFilter.GaussianBlur(blur_r)), np.float32) / 255.0
        local = bc / np.maximum(ba[..., None], 1e-3)
        ink = np.array(INK, np.float32) / 255.0
        # darken + push toward ink (keeps hue)
        lum = local.mean(axis=2, keepdims=True)
        oc = local * 0.24 + ink * 0.76
        oc = np.clip(oc * (0.82 + 0.1 * lum), 0, 1)
        if rim:
            # thin cool rim on the back/top edge
            k = int(round(rim_tx * self.tx))
            sh = _shift(solid.astype(np.float32), RIM_DIR * k)
            band = solid & (sh < 0.5)
            rc = np.array(RIM_COL, np.float32) / 255.0
            straight = self.col / np.maximum(A[..., None], 1e-4)
            mixc = straight * 0.72 + rc * 0.28 * (0.6 + 0.4 * straight.mean(axis=2, keepdims=True))
            sel = band[..., None]
            straight = np.where(sel, mixc, straight)
            self.col = straight * A[..., None]
        # composite canvas OVER ring
        ra = ring
        self.col = self.col + oc * ra[..., None] * (1 - A[..., None])
        self.a = A + ra * (1 - A)

    def downsample(self):
        """Box filter SS x SS -> RGBA uint8 image (straight alpha)."""
        H, W = self.H // SS * SS, self.W // SS * SS
        col = self.col[:H, :W].reshape(H // SS, SS, W // SS, SS, 3).mean(axis=(1, 3))
        a = self.a[:H, :W].reshape(H // SS, SS, W // SS, SS).mean(axis=(1, 3))
        straight = col / np.maximum(a[..., None], 1e-5)
        out = np.zeros((H // SS, W // SS, 4), np.uint8)
        out[..., :3] = np.clip(straight * 255 + 0.5, 0, 255).astype(np.uint8)
        out[..., 3] = np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)
        out[out[..., 3] == 0, :3] = 0
        return Image.fromarray(out, 'RGBA')

    def origin_tx(self):
        """Anchor (world 0,0) in output texels."""
        return (-self.x0 * self.den, -self.y0 * self.den)


def _cross_dilate(img):
    a = np.asarray(img, np.uint8)
    o = a.copy()
    o[1:, :] = np.maximum(o[1:, :], a[:-1, :])
    o[:-1, :] = np.maximum(o[:-1, :], a[1:, :])
    o[:, 1:] = np.maximum(o[:, 1:], a[:, :-1])
    o[:, :-1] = np.maximum(o[:, :-1], a[:, 1:])
    return Image.fromarray(o)


def _shift(arr, v):
    """Sample arr at p + v (integer px), zero outside."""
    dx, dy = int(round(v[0])), int(round(v[1]))
    H, W = arr.shape[:2]
    out = np.zeros_like(arr)
    xs0, xs1 = max(0, dx), min(W, W + dx)
    ys0, ys1 = max(0, dy), min(H, H + dy)
    xd0, yd0 = xs0 - dx, ys0 - dy
    if xs1 > xs0 and ys1 > ys0:
        out[yd0:yd0 + (ys1 - ys0), xd0:xd0 + (xs1 - xs0)] = arr[ys0:ys1, xs0:xs1]
    return out


def _erode(m, r):
    img = Image.fromarray((m * 255).astype(np.uint8))
    for i in range(r):
        img = img.filter(ImageFilter.MinFilter(3))
    return np.asarray(img, np.float32) / 255.0


class Group:
    """A merged, inked unit (limb, torso, head...). Parts are painted in order inside the group."""

    def __init__(self, cv, inner_line=True, line_tx=1.0, occlude=0.0, occ_tx=2.5):
        self.cv = cv
        self.img_col = np.zeros((cv.H, cv.W, 3), np.float32)
        self.img_a = np.zeros((cv.H, cv.W), np.float32)
        self.inner_line = inner_line
        self.line_tx = line_tx
        self.occlude = occlude
        self.occ_tx = occ_tx
        self.ink = None
        self.bbox = None

    # ---- primitive mask building
    def mask(self, polys=(), ellipses=(), circles=(), lines=()):
        cv = self.cv
        img = cv.new_mask()
        dr = ImageDraw.Draw(img)
        for pts in polys:
            if len(pts) >= 3:
                dr.polygon(cv.PP(pts), fill=255)
        for (cx, cy, rx, ry, ang) in ellipses:
            dr.polygon(cv.PP(ellipse_pts(cx, cy, rx, ry, ang, n=48)), fill=255)
        for (cx, cy, r) in circles:
            X, Y = cv.P((cx, cy))
            R = r * cv.ppu
            dr.ellipse([X - R, Y - R, X + R, Y + R], fill=255)
        for (pts, w) in lines:
            dr.line(cv.PP(pts), fill=255, width=max(1, int(round(w * cv.ppu))), joint='curve')
        return np.asarray(img, np.float32) / 255.0

    # ---- paint a mask with a material and cel shading
    def fill(self, m, mat, shade=0.9, hi=0.35, flat=False, clip=None, deep=0.0, light_dir=None):
        """shade/hi: band depths in world units for shadow and highlight."""
        cv = self.cv
        if clip is not None:
            m = m * clip
        if m.max() <= 0:
            return m
        base = np.array(mat.base, np.float32) / 255.0
        col = np.broadcast_to(base, m.shape + (3,)).copy()
        if not flat:
            away = AWAY if light_dir is None else -np.asarray(light_dir)
            if shade > 0:
                sh = _shift(m, away * shade * cv.ppu)
                band = (m > 0.5) & (sh < 0.5)
                col[band] = np.array(mat.shadow, np.float32) / 255.0
                if deep > 0:
                    sh2 = _shift(m, away * deep * cv.ppu)
                    band2 = (m > 0.5) & (sh2 < 0.5)
                    col[band2] = np.array(mat.deep, np.float32) / 255.0
            if hi > 0:
                lh = _shift(m, -away * hi * cv.ppu)
                band = (m > 0.5) & (lh < 0.5)
                if shade > 0:
                    band &= ~((m > 0.5) & (_shift(m, away * shade * cv.ppu) < 0.5))
                col[band] = np.array(mat.light, np.float32) / 255.0
        self._paint(col, m)
        if self.ink is None:
            self.ink = mat.ink
        return m

    def paint_flat(self, m, rgb, alpha=1.0):
        c = np.broadcast_to(np.array(rgb, np.float32) / 255.0, m.shape + (3,))
        self._paint(c, m * alpha)

    def _paint(self, col, m):
        a = m[..., None]
        self.img_col = self.img_col * (1 - a) + col * a
        self.img_a = self.img_a * (1 - m) + m

    def line(self, pts, w_tx, rgb, alpha=1.0, closed=False, clip_to_group=True):
        """Stroke in output texels width (inside detail lines)."""
        cv = self.cv
        img = cv.new_mask()
        dr = ImageDraw.Draw(img)
        P = cv.PP(pts)
        if closed:
            P = P + [P[0]]
        dr.line(P, fill=255, width=max(1, int(round(w_tx * SS))), joint='curve')
        m = np.asarray(img, np.float32) / 255.0
        if clip_to_group:
            m = m * (self.img_a > 0.5)
        self.paint_flat(m, rgb, alpha)
        return m

    def dot(self, x, y, r, rgb, alpha=1.0, clip_to_group=False):
        m = self.mask(circles=[(x, y, r)])
        if clip_to_group:
            m = m * (self.img_a > 0.5)
        self.paint_flat(m, rgb, alpha)

    def shade_region(self, m, rgb, alpha=1.0):
        """Paint inside existing group pixels only."""
        self.paint_flat(m * (self.img_a > 0.5), rgb, alpha)

    def commit(self):
        """Composite onto the canvas with inner contour + optional occlusion shadow."""
        cv = self.cv
        ga = self.img_a
        if ga.max() <= 0:
            return
        solid = (ga > 0.5).astype(np.float32)
        below = cv.a > 0.5
        if self.occlude > 0:
            sh = _shift(solid, -AWAY * self.occ_tx * SS)       # mask moved toward the away side
            occ = (sh > 0.5) & (solid < 0.5) & below
            f = np.array([1 - self.occlude * 0.95, 1 - self.occlude, 1 - self.occlude * 0.75], np.float32)
            cv.col[occ] = cv.col[occ] * f
        col = self.img_col.copy()
        if self.inner_line and below.any():
            w = max(1, int(round(self.line_tx * SS)))
            er = _erode(solid, w)
            ring = (solid > 0.5) & (er < 0.5) & below
            ink = np.array(self.ink if self.ink is not None else INK, np.float32) / 255.0
            col[ring] = ink
        a = ga[..., None]
        cv.col = cv.col * (1 - a) + col * a
        cv.a = cv.a * (1 - ga) + ga
