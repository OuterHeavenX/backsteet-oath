"""Tiny supersampled vector painter for the v2 UI / FX / item art (density 2).

Everything is drawn at `ss`x supersampling into premultiplied float layers and
box-filtered down on export, so edges are anti-aliased. Coordinates are given in
*final texels* (floats). Pillow + numpy only; deterministic.

Inking: `Layer.outline(w)` dilates the layer's coverage by `w` texels with a disc
and paints the ring underneath (silhouette contour). Cel shading: `cel()` builds
shadow / light regions by offsetting the shape's own mask against the key light
(upper-left-front), the same convention as the characters.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
ASSETS = os.path.join(ROOT, 'game', 'assets')
FONT_DIR = os.path.join(ASSETS, 'fonts', 'ofl')
F_BUNGEE = os.path.join(FONT_DIR, 'Bungee-Regular.ttf')
F_BARLOW_B = os.path.join(FONT_DIR, 'Barlow-Bold.ttf')
F_BARLOW_SB = os.path.join(FONT_DIR, 'Barlow-SemiBold.ttf')
F_COND_B = os.path.join(FONT_DIR, 'BarlowCondensed-Bold.ttf')


# ----------------------------------------------------------------------------- colour
def hx(s):
    s = s.lstrip('#')
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


INK = hx('#1a1220')
SHADOW_TGT = hx('#2c1840')   # violet-blue shadow pull
LIGHT_TGT = hx('#fff4dc')    # warm light pull
WHITE = (255, 255, 255)


def tones(base):
    """(shadow, base, light, ink) for a local colour, hue-shifted per ART_DIRECTION."""
    base = hx(base) if isinstance(base, str) else base
    sh = mix(tuple(int(c * 0.72) for c in base), SHADOW_TGT, 0.30)
    li = mix(base, LIGHT_TGT, 0.38)
    ink = mix(tuple(int(c * 0.35) for c in base), INK, 0.72)
    return sh, base, li, ink


def C(c):
    return hx(c) if isinstance(c, str) else tuple(c)


# ----------------------------------------------------------------------------- mask ops
def shift(m, dx, dy):
    """Translate a mask by integer SS pixels (zero fill)."""
    dx, dy = int(round(dx)), int(round(dy))
    out = np.zeros_like(m)
    H, W = m.shape
    xs0, xs1 = max(0, -dx), min(W, W - dx)
    ys0, ys1 = max(0, -dy), min(H, H - dy)
    if xs0 >= xs1 or ys0 >= ys1:
        return out
    out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = m[ys0:ys1, xs0:xs1]
    return out


def dilate(m, r):
    """Disc dilation (radius r in SS pixels) of a 0..1 mask."""
    if r <= 0:
        return m.copy()
    ri = int(math.ceil(r))
    H, W = m.shape
    p = np.pad(m, ri)
    out = m.copy()
    for dy in range(-ri, ri + 1):
        rem = r * r - dy * dy
        if rem < 0:
            continue
        wi = int(math.floor(math.sqrt(rem)))
        rows = p[ri + dy:ri + dy + H, :]
        acc = rows[:, ri:ri + W].copy()
        for dx in range(1, wi + 1):
            np.maximum(acc, rows[:, ri + dx:ri + dx + W], out=acc)
            np.maximum(acc, rows[:, ri - dx:ri - dx + W], out=acc)
        np.maximum(out, acc, out=out)
    return out


def erode(m, r):
    """Disc erosion; outside the array counts as empty, so shapes touching the edge erode too."""
    ri = int(math.ceil(r)) + 1
    p = np.pad(m, ri)
    return (1.0 - dilate(1.0 - p, r))[ri:-ri, ri:-ri]


def blur(m, r):
    """Cheap separable box blur x3 (≈ gaussian), r in pixels of the array."""
    r = int(max(1, round(r)))
    out = m.astype(np.float32)
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.pad(out, [(r + 1, r) if a == ax else (0, 0) for a in (0, 1)], mode='edge'), axis=ax)
            if ax == 0:
                out = (c[2 * r + 1:, :] - c[:-2 * r - 1, :]) / (2 * r + 1)
            else:
                out = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
    return out


def bez(p0, p1, p2, p3=None, n=24):
    """Quadratic (3 pts) or cubic (4 pts) bezier -> list of points."""
    pts = []
    for i in range(n + 1):
        t = i / n
        if p3 is None:
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        else:
            x = ((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0])
            y = ((1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1])
        pts.append((x, y))
    return pts


def rot_pts(pts, ang_deg, cx, cy):
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca) for x, y in pts]


def ell_pts(cx, cy, rx, ry, rot=0.0, n=72, a0=0.0, a1=360.0):
    pts = []
    for i in range(n + 1):
        t = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    return rot_pts(pts, rot, cx, cy) if rot else pts


def star_pts(cx, cy, r_out, r_in, n, rot=0.0, jitter=None):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        if jitter is not None and i % 2 == 0:
            r *= jitter[(i // 2) % len(jitter)]
        a = math.radians(rot + i * 180.0 / n - 90)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ----------------------------------------------------------------------------- layer
class Layer:
    def __init__(self, w, h, ss=4):
        self.w, self.h, self.ss = int(w), int(h), int(ss)
        self.W, self.H = self.w * self.ss, self.h * self.ss
        self.c = np.zeros((self.H, self.W, 3), np.float32)
        self.a = np.zeros((self.H, self.W), np.float32)

    # ---- masks
    def _im(self):
        return Image.new('L', (self.W, self.H), 0)

    def _arr(self, im):
        return np.asarray(im, dtype=np.float32) / 255.0

    def _p(self, pts):
        s = self.ss
        return [(x * s, y * s) for x, y in pts]

    def poly(self, pts):
        im = self._im()
        ImageDraw.Draw(im).polygon(self._p(pts), fill=255)
        return self._arr(im)

    def ellipse(self, cx, cy, rx, ry, rot=0.0):
        if rot:
            return self.poly(ell_pts(cx, cy, rx, ry, rot, 96))
        s = self.ss
        im = self._im()
        ImageDraw.Draw(im).ellipse([(cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s], fill=255)
        return self._arr(im)

    def circle(self, cx, cy, r):
        return self.ellipse(cx, cy, r, r)

    def rect(self, x0, y0, x1, y1, r=0.0):
        s = self.ss
        im = self._im()
        d = ImageDraw.Draw(im)
        if r > 0:
            d.rounded_rectangle([x0 * s, y0 * s, x1 * s - 1, y1 * s - 1], radius=r * s, fill=255)
        else:
            d.rectangle([x0 * s, y0 * s, x1 * s - 1, y1 * s - 1], fill=255)
        return self._arr(im)

    def stroke(self, pts, w, closed=False, cap=True):
        s = self.ss
        im = self._im()
        d = ImageDraw.Draw(im)
        p = self._p(pts)
        if closed:
            p = p + [p[0]]
        ww = max(1, int(round(w * s)))
        d.line(p, fill=255, width=ww, joint='curve')
        if cap:
            r = w * s / 2.0
            for (x, y) in ([p[0], p[-1]] if not closed else []):
                d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return self._arr(im)

    def text(self, txt, font_path, size, x, y, anchor='mm', spacing=0.0, stroke=0):
        s = self.ss
        f = ImageFont.truetype(font_path, int(round(size * s)))
        im = self._im()
        d = ImageDraw.Draw(im)
        if spacing == 0.0:
            d.text((x * s, y * s), txt, font=f, fill=255, anchor=anchor, stroke_width=int(stroke * s))
        else:
            widths = [f.getlength(ch) for ch in txt]
            total = sum(widths) + spacing * s * (len(txt) - 1)
            if anchor[0] == 'm':
                cx = x * s - total / 2
            elif anchor[0] == 'r':
                cx = x * s - total
            else:
                cx = x * s
            for ch, wd in zip(txt, widths):
                d.text((cx, y * s), ch, font=f, fill=255, anchor='l' + anchor[1], stroke_width=int(stroke * s))
                cx += wd + spacing * s
        return self._arr(im)

    def full(self):
        return np.ones((self.H, self.W), np.float32)

    def shift(self, m, dx, dy):
        return shift(m, dx * self.ss, dy * self.ss)

    def dil(self, m, r):
        return dilate(m, r * self.ss)

    def ero(self, m, r):
        return erode(m, r * self.ss)

    def blur(self, m, r):
        return blur(m, r * self.ss)

    def coords(self):
        ys, xs = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        return (xs + 0.5) / self.ss, (ys + 0.5) / self.ss

    # ---- painting (source-over, premultiplied)
    def fill(self, m, col, a=1.0):
        col = np.array(C(col), np.float32) / 255.0
        k = np.clip(m * a, 0, 1)
        self.c = self.c * (1 - k[..., None]) + col[None, None, :] * k[..., None]
        self.a = self.a * (1 - k) + k

    def fill_rgb(self, m, rgb, a=1.0):
        """rgb: HxWx3 float 0..1 colour field."""
        k = np.clip(m * a, 0, 1)
        self.c = self.c * (1 - k[..., None]) + rgb * k[..., None]
        self.a = self.a * (1 - k) + k

    def lin(self, m, c0, c1, p0, p1, a=1.0, gamma=1.0):
        X, Y = self.coords()
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L2 = dx * dx + dy * dy or 1.0
        t = np.clip(((X - p0[0]) * dx + (Y - p0[1]) * dy) / L2, 0, 1) ** gamma
        c0 = np.array(C(c0), np.float32) / 255.0
        c1 = np.array(C(c1), np.float32) / 255.0
        rgb = c0[None, None, :] * (1 - t[..., None]) + c1[None, None, :] * t[..., None]
        self.fill_rgb(m, rgb, a)

    def rad(self, m, c0, c1, cx, cy, r, a=1.0, gamma=1.0):
        X, Y = self.coords()
        t = np.clip(np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / max(r, 1e-3), 0, 1) ** gamma
        c0 = np.array(C(c0), np.float32) / 255.0
        c1 = np.array(C(c1), np.float32) / 255.0
        rgb = c0[None, None, :] * (1 - t[..., None]) + c1[None, None, :] * t[..., None]
        self.fill_rgb(m, rgb, a)

    def under(self, m, col, a=1.0):
        """Destination-over: paint only where the layer is not already opaque."""
        col = np.array(C(col), np.float32) / 255.0
        k = np.clip(m * a, 0, 1) * (1 - self.a)
        self.c = self.c + col[None, None, :] * k[..., None]
        self.a = self.a + k

    def add(self, m, col, a=1.0):
        """Additive light (clamped); also raises alpha."""
        col = np.array(C(col), np.float32) / 255.0
        k = np.clip(m * a, 0, 1)
        self.c = np.clip(self.c + col[None, None, :] * k[..., None], 0, 1)
        self.a = np.clip(self.a + k, 0, 1)

    def erase(self, m, a=1.0):
        k = 1 - np.clip(m * a, 0, 1)
        self.c *= k[..., None]
        self.a *= k

    def clip(self, m):
        self.c *= m[..., None]
        self.a *= m

    def over(self, other, dx=0.0, dy=0.0):
        """Composite another Layer (same ss) over this one, offset in texels."""
        oc, oa = other.c, other.a
        if dx or dy or other.W != self.W or other.H != self.H:
            c = np.zeros_like(self.c)
            a = np.zeros_like(self.a)
            ox, oy = int(round(dx * self.ss)), int(round(dy * self.ss))
            H, W = min(other.H, self.H - oy), min(other.W, self.W - ox)
            sy0, sx0 = max(0, -oy), max(0, -ox)
            if H > sy0 and W > sx0:
                c[oy + sy0:oy + H, ox + sx0:ox + W] = oc[sy0:H, sx0:W]
                a[oy + sy0:oy + H, ox + sx0:ox + W] = oa[sy0:H, sx0:W]
            oc, oa = c, a
        self.c = oc + self.c * (1 - oa[..., None])
        self.a = oa + self.a * (1 - oa)

    # ---- inking & shading
    def outline(self, w=2.0, col=INK, mask=None, a=1.0):
        base = self.a if mask is None else mask
        ring = dilate(np.clip(base * 1.0, 0, 1), w * self.ss)
        self.under(ring, col, a)

    def cel(self, m, base, light=(-1, -1), sh_off=2.0, li_off=1.2, li_trim=None, ink=None, sh=None, li=None):
        """Flat cel shading of shape `m`: base fill, shadow crescent away from the key light,
        thin light rim toward it."""
        t = tones(base)
        sh = sh or t[0]
        li = li or t[2]
        self.fill(m, t[1])
        lx, ly = light
        n = math.hypot(lx, ly) or 1
        lx, ly = lx / n, ly / n
        moved = shift(m, lx * sh_off * self.ss, ly * sh_off * self.ss)
        self.fill(np.clip(m - moved, 0, 1), sh)
        if li_off:
            moved2 = shift(m, -lx * li_off * self.ss, -ly * li_off * self.ss)
            lm = np.clip(m - moved2, 0, 1)
            if li_trim is not None:
                lm = lm * li_trim
            self.fill(lm, li)
        return t

    # ---- export
    def image(self):
        s = self.ss
        c = self.c.reshape(self.h, s, self.w, s, 3).mean(axis=(1, 3))
        a = self.a.reshape(self.h, s, self.w, s).mean(axis=(1, 3))
        rgb = np.where(a[..., None] > 1e-4, c / np.maximum(a[..., None], 1e-4), 0)
        out = np.dstack([np.clip(rgb, 0, 1) * 255, np.clip(a, 0, 1) * 255]).round().astype(np.uint8)
        return Image.fromarray(out, 'RGBA')


def strip(frames):
    """Concatenate equal-size PIL frames horizontally."""
    w, h = frames[0].size
    out = Image.new('RGBA', (w * len(frames), h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        out.paste(f, (i * w, 0))
    return out


def save(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in(t):
    return t ** 2


def lerp(a, b, t):
    return a + (b - a) * t
