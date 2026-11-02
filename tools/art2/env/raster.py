"""Backstreet Oath env v2 -- anti-aliased vector raster helpers (Pillow + numpy only).

All public drawing calls take WORLD UNITS (u). A Canvas renders at density D texels per unit (default 2).
Pixels are stored premultiplied float32 RGBA in 0..1. Shapes are rasterised with 4x4 supersampling on their
bounding box only, so big canvases stay cheap.
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SS = 4
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
FONT_DIR = os.path.join(ROOT, 'game', 'assets', 'fonts', 'ofl')
FONTS = {
    'sign': 'Bungee-Regular.ttf',
    'bold': 'Barlow-Bold.ttf',
    'semi': 'Barlow-SemiBold.ttf',
    'cond': 'BarlowCondensed-Bold.ttf',
    'condsemi': 'BarlowCondensed-SemiBold.ttf',
}
_font_cache = {}


def font(kind, px):
    key = (kind, int(px))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(os.path.join(FONT_DIR, FONTS[kind]), int(px))
    return _font_cache[key]


# ----------------------------------------------------------------------------- colour
def C(h, a=255):
    if isinstance(h, tuple):
        return tuple(h[:3]) + ((h[3] if len(h) > 3 else 255) if a == 255 else a,)
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3)) + (a[3] if len(a) > 3 else 255,)


def _rgb2hsv(c):
    r, g, b = [v / 255.0 for v in c[:3]]
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    h = 0.0
    if d > 1e-6:
        if mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h *= 60
    s = 0 if mx == 0 else d / mx
    return h, s, mx


def _hsv2rgb(h, s, v):
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return (int(round((r + m) * 255)), int(round((g + m) * 255)), int(round((b + m) * 255)))


def _hue_toward(h, target, amt):
    d = ((target - h + 540) % 360) - 180
    return h + d * amt


def shade(c, k=1.0):
    """Cel shadow tone: darker, hue shifted ~20 deg toward violet-blue, slightly more saturated."""
    h, s, v = _rgb2hsv(c)
    h2 = _hue_toward(h, 255, 0.22 * k) if s > 0.05 else 255
    s2 = min(1.0, s * (1 + 0.18 * k) + 0.06 * k)
    v2 = v * (1 - 0.30 * k)
    return _hsv2rgb(h2, s2, v2) + (c[3] if len(c) > 3 else 255,)


def light(c, k=1.0):
    """Cel light tone: brighter, pushed toward warm."""
    w = (255, 236, 200)
    out = tuple(int(round(c[i] + (w[i] - c[i]) * 0.32 * k)) for i in range(3))
    return out + (c[3] if len(c) > 3 else 255,)


def ink_of(c):
    """Outline colour: darkened, hue-shifted local colour (L* ~ 10-18), never pure black."""
    base = (26, 18, 32)
    return mix(base + (255,), c, 0.22)


def tone(c, f):
    """f<1 darker (via shade curve), f>1 lighter (via light curve)."""
    if f < 1:
        return shade(c, (1 - f) / 0.3)
    return light(c, (f - 1) / 0.32)


# ----------------------------------------------------------------------------- numpy helpers
def blur(a, r, passes=3):
    """Approximate gaussian blur of a 2D or 3D float array (separable box blur, r in texels)."""
    r = int(max(1, round(r)))
    out = a.astype(np.float32)
    for _ in range(passes):
        for axis in (0, 1):
            n = out.shape[axis]
            pad = [(0, 0)] * out.ndim
            pad[axis] = (r + 1, r)
            p = np.pad(out, pad, mode='edge')
            cs = np.cumsum(p, axis=axis, dtype=np.float64)
            hi = np.take(cs, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
            lo = np.take(cs, np.arange(0, n), axis=axis)
            out = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return out


def dilate(m, r):
    """Grey dilation of an alpha mask by radius r texels (disk)."""
    if r <= 0:
        return m
    R = int(math.ceil(r))
    h, w = m.shape
    p = np.pad(m, R)
    out = np.zeros_like(m)
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            d = math.hypot(dx, dy)
            if d > r + 0.35:
                continue
            wgt = 1.0 if d <= r - 0.35 else max(0.0, min(1.0, r + 0.35 - d) / 0.7)
            sl = p[R + dy:R + dy + h, R + dx:R + dx + w]
            np.maximum(out, sl * wgt, out=out)
    return out


def value_noise(w, h, cell, seed, octaves=1):
    """Smooth value noise (0..1) of size h x w texels with feature size ~cell texels."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    c = float(cell)
    for _ in range(octaves):
        gw, gh = int(w / c) + 3, int(h / c) + 3
        g = rng.random((gh, gw)).astype(np.float32)
        im = Image.fromarray(g, 'F').resize((int(gw * c), int(gh * c)), Image.BICUBIC)
        a = np.asarray(im, np.float32)[:h, :w]
        out += a * amp
        tot += amp
        amp *= 0.5
        c = max(2.0, c / 2)
    return np.clip(out / tot, 0, 1)


# ----------------------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w_u, h_u, D=2, ox_u=0.0, oy_u=0.0):
        self.D = D
        self.W = int(round(w_u * D))
        self.H = int(round(h_u * D))
        self.ox = int(round(ox_u * D))   # texel offset of this canvas in the parent coordinate system
        self.oy = int(round(oy_u * D))
        self.px = np.zeros((self.H, self.W, 4), np.float32)
        self.clipx = None
        self.em = None          # optional emission mask (texels that ignore lighting grades)
        self.em_level = 0.0     # default emission written by 'over' paints

    def enable_em(self):
        self.em = np.zeros((self.H, self.W), np.float32)
        return self

    # -- geometry -------------------------------------------------------------------------------------------
    def t(self, v):
        return v * self.D

    def layer(self, x_u=None, y_u=None, w_u=None, h_u=None):
        """Transparent sub-canvas in the same coordinate system (optionally only a window of it)."""
        if x_u is None:
            c = Canvas(self.W / self.D, self.H / self.D, self.D, self.ox / self.D, self.oy / self.D)
        else:
            c = Canvas(w_u, h_u, self.D, x_u, y_u)
        if self.em is not None:
            c.enable_em()
        return c

    def _bbox_mask(self, P, draw_fn):
        xs = [p[0] for p in P]
        ys = [p[1] for p in P]
        x0 = int(math.floor(min(xs))) - 1
        y0 = int(math.floor(min(ys))) - 1
        x1 = int(math.ceil(max(xs))) + 2
        y1 = int(math.ceil(max(ys))) + 2
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0 or w * h > 40_000_000:
            return x0, y0, np.zeros((max(h, 1), max(w, 1)), np.float32)
        im = Image.new('L', (w * SS, h * SS), 0)
        d = ImageDraw.Draw(im)
        draw_fn(d, x0, y0)
        m = np.asarray(im, np.float32).reshape(h, SS, w, SS).mean(axis=(1, 3)) / 255.0
        return x0, y0, m

    def _P(self, pts):
        return [((x * self.D) - self.ox, (y * self.D) - self.oy) for x, y in pts]

    def poly_mask(self, pts):
        P = self._P(pts)

        def fn(d, x0, y0):
            d.polygon([((x - x0) * SS, (y - y0) * SS) for x, y in P], fill=255)
        return self._bbox_mask(P, fn)

    def rect_mask(self, x, y, w, h):
        return self.poly_mask([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])

    def ellipse_mask(self, cx, cy, rx, ry):
        P = self._P([(cx - rx, cy - ry), (cx + rx, cy + ry)])

        def fn(d, x0, y0):
            d.ellipse([(P[0][0] - x0) * SS, (P[0][1] - y0) * SS, (P[1][0] - x0) * SS, (P[1][1] - y0) * SS],
                      fill=255)
        return self._bbox_mask(P, fn)

    def line_mask(self, pts, width_u, round_caps=True):
        P = self._P(pts)
        wt = width_u * self.D
        pad = wt / 2 + 1
        PP = P + [(P[0][0] - pad, P[0][1] - pad), (P[-1][0] + pad, P[-1][1] + pad)]
        xs = [p[0] for p in P]
        ys = [p[1] for p in P]
        PP = [(min(xs) - pad, min(ys) - pad), (max(xs) + pad, max(ys) + pad)]

        def fn(d, x0, y0):
            Q = [((x - x0) * SS, (y - y0) * SS) for x, y in P]
            d.line(Q, fill=255, width=max(1, int(round(wt * SS))), joint='curve')
            if round_caps:
                r = wt * SS / 2
                for qx, qy in (Q[0], Q[-1]):
                    d.ellipse([qx - r, qy - r, qx + r, qy + r], fill=255)
        return self._bbox_mask(PP, fn)

    # -- compositing ----------------------------------------------------------------------------------------
    def _region(self, x0, y0, m):
        h, w = m.shape
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(self.W, x0 + w), min(self.H, y0 + h)
        if self.clipx is not None:
            xa = max(xa, self.clipx[0])
            xb = min(xb, self.clipx[1])
        if xa >= xb or ya >= yb:
            return None
        return (slice(ya, yb), slice(xa, xb)), m[ya - y0:yb - y0, xa - x0:xb - x0]

    def paint(self, mk, col, a=1.0, mode='over', rgb=None, em=None):
        """Composite a mask (x0, y0, m) with a flat colour (or per-texel rgb array matching m).
        em: emission level written to the emission mask (None = keep for additive/mul modes, 0 for over)."""
        x0, y0, m = mk
        r = self._region(x0, y0, m)
        if r is None:
            return
        (sy, sx), mm = r
        mm = mm * (a * (col[3] / 255.0 if col is not None and len(col) > 3 else 1.0))
        if self.em is not None:
            e = self.em[sy, sx]
            if mode in ('over', 'atop', 'behind'):
                k = mm if mode != 'atop' else mm * self.px[sy, sx, 3]
                if mode == 'behind':
                    k = mm * (1 - self.px[sy, sx, 3])
                lev = self.em_level if em is None else em
                e[...] = e * (1 - k) + k * lev
            elif em is not None:
                e[...] = np.maximum(e, mm * em)
        dst = self.px[sy, sx]
        if rgb is not None:
            h, w = m.shape
            c = rgb[sy.start - y0:sy.stop - y0, sx.start - x0:sx.stop - x0]
        else:
            c = np.array(col[:3], np.float32) / 255.0
        if mode == 'over':
            dst[..., :3] = c * mm[..., None] + dst[..., :3] * (1 - mm[..., None])
            dst[..., 3] = mm + dst[..., 3] * (1 - mm)
        elif mode == 'atop':          # only where something is already drawn; alpha preserved
            k = mm * dst[..., 3]
            dst[..., :3] = c * k[..., None] + dst[..., :3] * (1 - mm[..., None])
        elif mode == 'add':           # additive light (premultiplied), restricted to drawn texels
            dst[..., :3] += c * (mm * dst[..., 3])[..., None]
        elif mode == 'addfree':       # additive light that can also create alpha (glow halos)
            dst[..., :3] += c * mm[..., None]
            dst[..., 3] = dst[..., 3] + (1 - dst[..., 3]) * np.clip(mm * 0.8, 0, 1)
        elif mode == 'mul':           # multiply tint where drawn
            f = 1 - mm[..., None] + c * mm[..., None]
            dst[..., :3] *= f
        elif mode == 'behind':        # draw under existing pixels
            ia = 1 - dst[..., 3]
            k = mm * ia
            dst[..., :3] += c * k[..., None]
            dst[..., 3] += k
        elif mode == 'erase':
            dst *= (1 - mm[..., None])
        self.px[sy, sx] = dst

    def fill_poly(self, pts, col, ink=None, iw=2.0, a=1.0, mode='over', em=None):
        mk = self.poly_mask(pts)
        self.stroke_fill(mk, col, ink, iw, a, mode, em)
        return mk

    def stroke_fill(self, mk, col, ink=None, iw=2.0, a=1.0, mode='over', em=None):
        if ink is not None and iw > 0:
            x0, y0, m = mk
            R = int(math.ceil(iw)) + 1
            mp = np.pad(m, R)
            self.paint((x0 - R, y0 - R, dilate(mp, iw)), ink, a, mode, em=em)
        if col is not None:
            self.paint(mk, col, a, mode, em=em)

    def rect(self, x, y, w, h, col, ink=None, iw=2.0, a=1.0, mode='over', em=None):
        mk = self.rect_mask(x, y, w, h)
        self.stroke_fill(mk, col, ink, iw, a, mode, em)
        return mk

    def ellipse(self, cx, cy, rx, ry, col, ink=None, iw=2.0, a=1.0, mode='over', em=None):
        mk = self.ellipse_mask(cx, cy, rx, ry)
        self.stroke_fill(mk, col, ink, iw, a, mode, em)
        return mk

    def line(self, pts, w_u, col, ink=None, iw=1.0, a=1.0, mode='over', caps=True, em=None):
        mk = self.line_mask(pts, w_u, caps)
        self.stroke_fill(mk, col, ink, iw, a, mode, em)
        return mk

    def hline(self, x, y, w, th, col, a=1.0, mode='over'):
        return self.rect(x, y, w, th, col, a=a, mode=mode)

    def vline(self, x, y, h, th, col, a=1.0, mode='over'):
        return self.rect(x, y, th, h, col, a=a, mode=mode)

    def vgrad(self, x, y, w, h, stops, a=1.0, mode='over', mk=None, em=None):
        """Vertical gradient over rect (or given mask). stops: list of colours or (t, colour)."""
        if mk is None:
            mk = self.rect_mask(x, y, w, h)
        x0, y0, m = mk
        hh = m.shape[0]
        ys = (np.arange(hh, dtype=np.float32) + y0 + self.oy) / self.D
        t = np.clip((ys - y) / max(1e-6, h), 0, 1)
        rgb = _ramp(stops, t)
        rgb = np.broadcast_to(rgb[:, None, :], (hh, m.shape[1], 3))
        self.paint(mk, (255, 255, 255, 255), a, mode, rgb=rgb, em=em)
        return mk

    def hgrad(self, x, y, w, h, stops, a=1.0, mode='over', mk=None, em=None):
        if mk is None:
            mk = self.rect_mask(x, y, w, h)
        x0, y0, m = mk
        ww = m.shape[1]
        xs = (np.arange(ww, dtype=np.float32) + x0 + self.ox) / self.D
        t = np.clip((xs - x) / max(1e-6, w), 0, 1)
        rgb = _ramp(stops, t)
        rgb = np.broadcast_to(rgb[None, :, :], (m.shape[0], ww, 3))
        self.paint(mk, (255, 255, 255, 255), a, mode, rgb=rgb, em=em)
        return mk

    def radial(self, cx, cy, rx, ry, col, a=1.0, mode='addfree', falloff=2.0, core=0.0, em=None):
        """Soft radial light: alpha = (1 - d)^falloff, d normalised ellipse distance."""
        x0 = int(math.floor((cx - rx) * self.D)) - self.ox
        y0 = int(math.floor((cy - ry) * self.D)) - self.oy
        w = int(math.ceil(2 * rx * self.D)) + 2
        h = int(math.ceil(2 * ry * self.D)) + 2
        xs = (np.arange(w, dtype=np.float32) + x0 + self.ox + 0.5) / self.D
        ys = (np.arange(h, dtype=np.float32) + y0 + self.oy + 0.5) / self.D
        dx = (xs[None, :] - cx) / rx
        dy = (ys[:, None] - cy) / ry
        d = np.sqrt(dx * dx + dy * dy)
        m = np.clip(1 - d, 0, 1) ** falloff
        if core > 0:
            m = np.clip(m * (1 + core), 0, 1)
        self.paint((x0, y0, m.astype(np.float32)), col, a, mode, em=em)

    def texture(self, mk, fn, mode='atop', a=1.0, em=None):
        """Per-texel colour from fn(X_u, Y_u) -> (h, w, 3) float 0..1, applied through mask."""
        x0, y0, m = mk
        h, w = m.shape
        X = (np.arange(w, dtype=np.float32) + x0 + self.ox + 0.5) / self.D
        Y = (np.arange(h, dtype=np.float32) + y0 + self.oy + 0.5) / self.D
        rgb = fn(X[None, :].repeat(h, 0), Y[:, None].repeat(w, 1))
        self.paint(mk, (255, 255, 255, 255), a, mode, rgb=rgb, em=em)

    def text_mask(self, s, kind, size_u, x, y, anchor='la', tracking=0.0, scale_x=1.0):
        """Text mask; (x, y) in u with PIL anchor semantics (e.g. 'mm' centre, 'ls' left baseline)."""
        px = max(4, int(round(size_u * self.D * 2)))        # rendered at 2x then reduced
        f = font(kind, px)
        if tracking:
            widths = [f.getlength(ch) for ch in s]
            tw = sum(widths) + tracking * self.D * 2 * (len(s) - 1)
        else:
            tw = f.getlength(s)
        asc, desc = f.getmetrics()
        W = int(tw + px) + 8
        H = int(asc + desc + px * 0.3) + 8
        im = Image.new('L', (W, H), 0)
        d = ImageDraw.Draw(im)
        if tracking:
            cx = 4.0
            for ch, wch in zip(s, widths):
                d.text((cx, 4 + asc), ch, font=f, fill=255, anchor='ls')
                cx += wch + tracking * self.D * 2
        else:
            d.text((4, 4 + asc), s, font=f, fill=255, anchor='ls')
        bb = im.getbbox() or (0, 0, 1, 1)
        im = im.crop(bb)
        if scale_x != 1.0:
            im = im.resize((max(1, int(im.width * scale_x)), im.height), Image.LANCZOS)
        im = im.resize((max(1, im.width // 2), max(1, im.height // 2)), Image.LANCZOS)
        m = np.asarray(im, np.float32) / 255.0
        h, w = m.shape
        X = x * self.D - self.ox
        Y = y * self.D - self.oy
        ax, ay = anchor[0], anchor[1]
        if ax == 'm':
            X -= w / 2
        elif ax == 'r':
            X -= w
        if ay == 'm':
            Y -= h / 2
        elif ay in ('b', 's', 'd'):
            Y -= h
        return int(round(X)), int(round(Y)), m

    def text(self, s, kind, size_u, x, y, col, anchor='la', ink=None, iw=1.5, tracking=0.0, a=1.0,
             scale_x=1.0, mode='over', em=None):
        mk = self.text_mask(s, kind, size_u, x, y, anchor, tracking, scale_x)
        self.stroke_fill(mk, col, ink, iw, a, mode, em)
        return mk

    # -- layers ------------------------------------------------------------------------------------------------
    def merge(self, other, ink=None, iw=2.0, a=1.0, shadow=None):
        """Composite another canvas (same coordinate system) over this one, optionally with an ink contour
        around its union silhouette and a soft drop shadow (dx_u, dy_u, blur_u, alpha, colour)."""
        ox = other.ox - self.ox
        oy = other.oy - self.oy
        src = other.px
        al = src[..., 3]
        if shadow is not None:
            dx, dy, bl, sa, sc = shadow
            m = blur(al, bl * self.D) * sa
            self.paint((ox + int(dx * self.D), oy + int(dy * self.D), m), sc)
        if ink is not None and iw > 0:
            R = int(math.ceil(iw)) + 1
            mp = np.pad(al, R)
            self.paint((ox - R, oy - R, dilate(mp, iw)), ink, a)
        h, w = al.shape
        xa, ya = max(0, ox), max(0, oy)
        xb, yb = min(self.W, ox + w), min(self.H, oy + h)
        if self.clipx is not None:
            xa = max(xa, self.clipx[0])
            xb = min(xb, self.clipx[1])
        if xa >= xb or ya >= yb:
            return
        s = src[ya - oy:yb - oy, xa - ox:xb - ox] * a
        if self.em is not None:
            k = s[..., 3]
            se = other.em[ya - oy:yb - oy, xa - ox:xb - ox] if other.em is not None else other.em_level
            self.em[ya:yb, xa:xb] = self.em[ya:yb, xa:xb] * (1 - k) + k * se
        d = self.px[ya:yb, xa:xb]
        d[..., :3] = s[..., :3] + d[..., :3] * (1 - s[..., 3:4])
        d[..., 3] = s[..., 3] + d[..., 3] * (1 - s[..., 3])
        self.px[ya:yb, xa:xb] = d

    def alpha_mask(self):
        return (0, 0, self.px[..., 3].copy())

    # -- output --------------------------------------------------------------------------------------------------
    def to_image(self, opaque=False):
        a = np.clip(self.px[..., 3], 0, 1)
        rgb = np.clip(self.px[..., :3], 0, None)
        with np.errstate(invalid='ignore', divide='ignore'):
            st = np.where(a[..., None] > 1e-5, rgb / np.maximum(a[..., None], 1e-5), 0)
        st = np.clip(st, 0, 1)
        out = np.concatenate([st, a[..., None]], axis=2)
        if opaque:
            out[..., 3] = 1.0
        return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')


def _ramp(stops, t):
    """stops: [col,...] evenly spaced or [(t, col), ...]; t array -> (n, 3) float rgb."""
    if isinstance(stops[0][1], tuple):
        st = stops
    else:
        st = [(i / max(1, len(stops) - 1), s) for i, s in enumerate(stops)]
    ts = np.array([s[0] for s in st], np.float32)
    cs = np.array([s[1][:3] for s in st], np.float32) / 255.0
    out = np.zeros(t.shape + (3,), np.float32)
    for ch in range(3):
        out[..., ch] = np.interp(t, ts, cs[:, ch])
    return out


def rng_of(*parts):
    return random.Random('|'.join(str(p) for p in parts))
