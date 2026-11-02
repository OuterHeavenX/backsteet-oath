"""Backstreet Oath env v2 -- room model, grounds, grading, lightmap and data export (world units)."""
import json
import math
import os

import numpy as np
from PIL import Image

from raster import Canvas, C, mix, shade, light, ink_of, value_noise, rng_of, blur
import kit
from kit import M, MAJOR, DETAIL

H = 360
FACADE_BOTTOM = 214       # exterior wall base meets the sidewalk
SIDEWALK_FRONT = 244      # curb top
STREET_TOP = 251
CURB_Y = 344              # bottom of the walk band; below = foreground curb strip
INT_WALL_BOTTOM = 196


class Room:
    def __init__(self, rid, data, enc=None, D=2):
        self.id = rid
        self.data = data
        self.enc = enc or {}
        self.D = D
        self.W = int(data['width'])
        self.interior = data.get('kind') == 'interior'
        self.district = data.get('district', 'old_quarter')
        self.walk = data.get('walk', [218, 344])
        self.cv = Canvas(self.W, H, D).enable_em()
        self.glows = []          # engine glows (contract)
        self.lights = []         # lightmap sources: (x, y_ground, rx, ry, colour, strength)
        self.ambient = []
        self.reflect = []
        self.fg = []             # (name, Canvas-or-Image, x_center_u, y_bottom_u, parallax, fade)
        self.mid_layers = []     # room-specific layers: dict(name, image, parallax, y, repeat)
        self.rim = {"color": "#ffb070", "dir": [1.0, 0.25], "strength": 0.45}
        self.cast_shadow = {"dir": [0.6, 0.22], "alpha": 0.22}
        self.ambient_color = '#fff0e0'
        self.ambient_level = 0.86
        self.district_layers = []
        self.notes = []

    def rng(self, *p):
        return rng_of(self.id, *p)

    def doors_in(self, x0, x1):
        return [d for d in self.data.get('doors', []) if x0 <= d['x'] < x1]

    def props_of(self, t):
        return [p for p in self.data.get('props', []) if p['type'] == t]

    def glow(self, x, y, r, color, energy=0.5, flicker='none', front=False):
        self.glows.append({"x": round(x, 1), "y": round(y, 1), "r": round(r, 1), "color": color,
                           "energy": round(energy, 2), "flicker": flicker, "front": bool(front)})

    def light(self, x, y, rx, ry, color, strength):
        self.lights.append((x, y, rx, ry, C(color) if isinstance(color, str) else color, strength))


# ----------------------------------------------------------------------------- grounds
def sidewalk(R, x, w, y0=FACADE_BOTTOM, y1=SIDEWALK_FRONT, base='#8a7e7c', slab=32.0):
    cv = R.cv
    m = M(base)
    mk = cv.rect(x, y0, w, y1 - y0, m.b)
    x0, yy0, mm = mk
    hh, ww = mm.shape
    n = value_noise(ww, hh, 6 * cv.D, hash((R.id, 'sw')) % 9999, 2)
    cv.paint((x0, yy0, (n - 0.5).clip(0, 1) * 0.10 * mm), m.l, mode='atop')
    cv.paint((x0, yy0, (0.5 - n).clip(0, 1) * 0.12 * mm), m.s, mode='atop')
    rs = R.rng('slab', x)
    # per-slab tone, seams
    xx = (int(x / slab)) * slab
    while xx < x + w:
        t = rs.uniform(-0.035, 0.035)
        cv.rect(xx, y0, slab, y1 - y0, m.l if t > 0 else m.s, a=abs(t) * 3, mode='atop')
        cv.rect(xx, y0, 0.5, y1 - y0, m.d, a=0.55, mode='atop')
        cv.rect(xx + 0.5, y0, 0.5, y1 - y0, m.l, a=0.45, mode='atop')
        xx += slab
    mid = y0 + (y1 - y0) * 0.45
    cv.rect(x, mid, w, 0.5, m.d, a=0.45, mode='atop')
    cv.rect(x, mid + 0.5, w, 0.5, m.l, a=0.35, mode='atop')
    # gum spots + small cracks
    for _ in range(int(w / 14)):
        gx, gy = rs.uniform(x, x + w), rs.uniform(y0 + 3, y1 - 2)
        cv.ellipse(gx, gy, rs.uniform(0.4, 0.9), 0.4, m.d, a=0.35, mode='atop')
    for _ in range(int(w / 120)):
        cx, cy = rs.uniform(x, x + w), rs.uniform(y0 + 4, y1 - 4)
        pts = [(cx, cy)]
        for _k in range(rs.randint(3, 5)):
            cx += rs.uniform(1.5, 4)
            cy += rs.uniform(-1, 1)
            pts.append((cx, cy))
        cv.line(pts, 0.5, m.d, a=0.5, mode='atop')
    # contact shadow along the building base
    cv.vgrad(x, y0, w, 7, [C('#1c1226', 150), C('#1c1226', 0)], mode='atop')


def curb(R, x, w, y=SIDEWALK_FRONT, top='#a09490', face='#5e5662'):
    cv = R.cv
    t = M(top)
    f = M(face)
    cv.rect(x, y, w, 1.0, t.h)
    cv.rect(x, y + 1, w, 2.0, t.b)
    cv.rect(x, y + 3, w, 4.0, f.b)
    cv.rect(x, y + 3, w, 0.5, f.l, a=0.6)
    cv.vgrad(x, y + 3, w, 4, [f.b, f.s], a=0.7, mode='atop')
    cv.rect(x, y + 7, w, 0.8, C('#1e1824'), a=0.8)


def asphalt(R, x, w, y0=STREET_TOP, y1=CURB_Y, base='#5c5464', lane=True, lane_y=None, seed=0):
    cv = R.cv
    m = M(base)
    mk = cv.vgrad(x, y0, w, y1 - y0, [mix(m.b, C('#b07a7a'), 0.22), m.b, shade(m.b, 0.2)])
    x0, yy0, mm = mk
    hh, ww = mm.shape
    n1 = value_noise(ww, hh, 1.2 * cv.D, hash((R.id, 'agg', seed)) % 9999, 1)
    n2 = value_noise(ww, hh, 40 * cv.D, hash((R.id, 'patch', seed)) % 9999, 2)
    cv.paint((x0, yy0, (n1 - 0.5).clip(0, 1) * 0.07 * mm), m.l, mode='atop')
    cv.paint((x0, yy0, (0.5 - n1).clip(0, 1) * 0.07 * mm), m.s, mode='atop')
    cv.paint((x0, yy0, (n2 - 0.55).clip(0, 1) * 0.16 * mm), m.l, mode='atop')
    cv.paint((x0, yy0, (0.45 - n2).clip(0, 1) * 0.16 * mm), m.d, mode='atop')
    rs = R.rng('asph', x, seed)
    # repair patches (irregular, low contrast, faint edge)
    for _ in range(max(1, int(w / 300))):
        px, py = rs.uniform(x, x + w - 50), rs.uniform(y0 + 8, y1 - 24)
        pw, ph = rs.uniform(26, 60), rs.uniform(8, 16)
        pts = [(px + rs.uniform(-2, 2), py + rs.uniform(-1, 1)), (px + pw + rs.uniform(-2, 2), py + rs.uniform(-1, 1)),
               (px + pw + rs.uniform(-3, 3), py + ph + rs.uniform(-1, 1)), (px + rs.uniform(-3, 3), py + ph + rs.uniform(-1, 1))]
        cv.fill_poly(pts, shade(m.b, 0.2), a=0.13, mode='atop')
        cv.fill_poly(pts, None, ink=m.d, iw=DETAIL, a=0.10, mode='atop')
    # cracks
    for _ in range(max(1, int(w / 140))):
        cx, cy = rs.uniform(x, x + w), rs.uniform(y0 + 4, y1 - 4)
        pts = [(cx, cy)]
        for _k in range(rs.randint(4, 9)):
            cx += rs.uniform(1.5, 5)
            cy += rs.uniform(-1.5, 1.5)
            pts.append((cx, cy))
        cv.line(pts, 0.5, m.d, a=0.55, mode='atop')
    # oil stains
    for _ in range(max(1, int(w / 220))):
        ox_, oy_ = rs.uniform(x, x + w), rs.uniform(y0 + 10, y1 - 10)
        cv.radial(ox_, oy_, rs.uniform(6, 12), rs.uniform(2, 4), C('#1a1420'), a=0.35, mode='over', falloff=1.2)
    if lane:
        ly = lane_y or (y0 + y1) / 2 + 3
        lc = C('#d8c48a')
        xx = (int(x / 56)) * 56
        while xx < x + w:
            mk2 = cv.rect(xx, ly, 26, 1.6, lc, a=0.55, mode='atop')
            lx0, ly0, lm = mk2
            nn = value_noise(lm.shape[1], lm.shape[0], 2 * cv.D, int(xx), 1)
            cv.paint((lx0, ly0, lm * np.clip((nn - 0.55) * 2.5, 0, 1)), m.b, a=0.9, mode='atop')
            xx += 56


def manhole(R, x, y, rx=9.0, ry=3.2):
    cv = R.cv
    cv.ellipse(x, y, rx + 1.2, ry + 0.6, C('#2a2430'), a=0.85)
    cv.ellipse(x, y, rx, ry, C('#4a4250'))
    for k in range(-3, 4):
        cv.rect(x - rx * 0.75, y + k * ry * 0.22 - 0.2, rx * 1.5, 0.4, C('#2e2834'), a=0.8, mode='atop')
    cv.ellipse(x - rx * 0.3, y - ry * 0.4, rx * 0.5, ry * 0.25, C('#6a6070'), a=0.5, mode='atop')


def storm_drain(R, x, y=SIDEWALK_FRONT + 3):
    cv = R.cv
    cv.rect(x, y, 14, 4, C('#18141c'))
    for k in range(7):
        cv.rect(x + 1 + k * 2, y + 0.5, 0.8, 3, C('#4a4450'))


def puddle(R, x, y, rx, ry, sky='#c8889a', a=0.38, reflect=True):
    cv = R.cv
    mk = cv.ellipse_mask(x, y, rx, ry)
    x0, y0, m = mk
    # irregular edge
    n = value_noise(m.shape[1], m.shape[0], 3 * cv.D, int(x * 7 + y), 1)
    m2 = np.clip((m - 0.25 - (n - 0.5) * 0.5) * 2.2, 0, 1)
    cv.paint((x0, y0, m2), C('#2a2232'), a=0.45, mode='atop')
    cv.paint((x0, y0, m2), C(sky), a=a, mode='atop')
    # bright edge glint (top edge)
    cv.ellipse(x - rx * 0.2, y - ry * 0.55, rx * 0.5, ry * 0.18, C('#ffe0c0'), a=0.25, mode='atop')
    if reflect:
        R.reflect.append({"rect": [round(x - rx, 1), round(y - ry, 1), round(rx * 2, 1), round(ry * 2, 1)],
                          "alpha": 0.22})


def near_curb(R, x, w, top='#7e7470', face='#3a3440'):
    """Foreground strip below the walk band (y 344..360)."""
    cv = R.cv
    t = M(top)
    cv.rect(x, CURB_Y, w, 0.8, C('#1e1824'), a=0.7)
    cv.rect(x, CURB_Y + 0.8, w, 1.0, t.h, a=0.9)
    cv.rect(x, CURB_Y + 1.8, w, 4.2, t.b)
    cv.vgrad(x, CURB_Y + 6, w, H - CURB_Y - 6, [C(face), shade(C(face), 1.4)])
    xx = (int(x / 64)) * 64 + 31
    while xx < x + w:
        cv.rect(xx, CURB_Y + 1.8, 0.5, 4.2, t.d, a=0.7)
        xx += 64


def g_street(R, x, w):
    sidewalk(R, x, w)
    curb(R, x, w)
    asphalt(R, x, w)
    rs = R.rng('drains')
    xx = x + 90
    while xx < x + w - 20:
        storm_drain(R, xx)
        xx += rs.choice([300, 380, 420])
    near_curb(R, x, w)


def g_lot(R, x, w, base='#7e766c'):
    cv = R.cv
    m = M(base)
    y0, y1 = FACADE_BOTTOM, CURB_Y
    mk = cv.vgrad(x, y0, w, y1 - y0, [shade(m.b, 0.35), m.b, mix(m.b, C('#5a5060'), 0.25)])
    x0, yy0, mm = mk
    hh, ww = mm.shape
    n1 = value_noise(ww, hh, 1.4 * cv.D, hash((R.id, 'lot1')) % 9999, 1)
    n2 = value_noise(ww, hh, 30 * cv.D, hash((R.id, 'lot2')) % 9999, 2)
    cv.paint((x0, yy0, (n1 - 0.5).clip(0, 1) * 0.08 * mm), m.l, mode='atop')
    cv.paint((x0, yy0, (0.5 - n1).clip(0, 1) * 0.08 * mm), m.s, mode='atop')
    cv.paint((x0, yy0, (0.48 - n2).clip(0, 1) * 0.22 * mm), C('#5a4e4a'), mode='atop')
    rs = R.rng('lot')
    # slab rows in perspective
    y = y0 + 6
    hrow = 16.0
    rows = []
    while y < y1:
        rows.append(y)
        cv.rect(x, y, w, 0.5, m.d, a=0.6, mode='atop')
        cv.rect(x, y + 0.5, w, 0.5, m.l, a=0.4, mode='atop')
        y += hrow
        hrow *= 1.12
    rows.append(y1)
    for i in range(len(rows) - 1):
        ya, yb = rows[i], rows[i + 1]
        sw = 46 + 12 * i
        xx = x + rs.uniform(0, sw)
        while xx < x + w:
            cv.rect(xx, ya, 0.5, yb - ya, m.d, a=0.55, mode='atop')
            # broken corner on some slabs
            if rs.random() < 0.12:
                cx = xx + rs.uniform(4, sw - 8)
                cv.fill_poly([(cx, ya + 1), (cx + rs.uniform(4, 9), ya + 1), (cx + rs.uniform(1, 4), ya + rs.uniform(3, 6))],
                             m.d, a=0.45, mode='atop')
            # weeds in seams
            if rs.random() < 0.25:
                weeds(R, xx, yb - 0.5, rs.randint(2, 5), seed=int(xx * 3 + yb))
            xx += sw * rs.uniform(0.8, 1.2)
    # cracks
    for _ in range(int(w / 70)):
        cx, cy = rs.uniform(x, x + w), rs.uniform(y0 + 6, y1 - 6)
        pts = [(cx, cy)]
        for _k in range(rs.randint(4, 10)):
            cx += rs.uniform(-4, 4)
            cy += rs.uniform(-2, 3)
            pts.append((cx, cy))
        cv.line(pts, 0.5, m.d, a=0.6, mode='atop')
    # oil stains + tyre marks + litter
    for _ in range(int(w / 160)):
        cv.radial(rs.uniform(x, x + w), rs.uniform(y0 + 12, y1 - 10), rs.uniform(7, 14), rs.uniform(2.5, 5),
                  C('#241c24'), a=0.35, mode='over', falloff=1.2)
    for _ in range(int(w / 400) + 1):
        tx, ty = rs.uniform(x, x + w - 120), rs.uniform(y0 + 30, y1 - 20)
        pts = [(tx + k * 6, ty + math.sin(k * 0.35) * 4) for k in range(20)]
        cv.line(pts, 2.2, C('#3a3036'), a=0.18, mode='atop')
        cv.line([(px, py + 6) for px, py in pts], 2.2, C('#3a3036'), a=0.18, mode='atop')
    for _ in range(int(w / 25)):
        lx, ly = rs.uniform(x, x + w), rs.uniform(y0 + 4, y1 - 3)
        c = rs.choice([C('#c8b8a0'), C('#8a6a4a'), C('#6a8a5a'), C('#b8a070')])
        cv.ellipse(lx, ly, rs.uniform(0.5, 1.2), 0.45, c, a=0.55, mode='atop')
    cv.vgrad(x, y0, w, 8, [C('#1c1226', 140), C('#1c1226', 0)], mode='atop')
    near_curb(R, x, w, top='#6e665e', face='#36303a')


def weeds(R, x, y, n=3, seed=0, col='#5a7a3a'):
    cv = R.cv
    rs = rng_of('weed', seed)
    base = C(col)
    for k in range(n):
        a = -math.pi / 2 + rs.uniform(-0.7, 0.7)
        ln = rs.uniform(2.5, 6.0)
        x0 = x + rs.uniform(-2, 2)
        c = mix(base, C('#a8b858'), rs.uniform(0, 0.5))
        cv.line([(x0, y), (x0 + math.cos(a) * ln * 0.5 + rs.uniform(-1, 1), y + math.sin(a) * ln * 0.6),
                 (x0 + math.cos(a) * ln, y + math.sin(a) * ln)], 0.6, c, ink=shade(c, 2.0), iw=0.3)


def g_checker(R, x, w, y0=INT_WALL_BOTTOM, c1='#e6dccb', c2='#a89aa6', tile=16.0):
    """Muted perspective checker floor (low contrast, polished)."""
    cv = R.cv
    y1 = H
    A = np.array(C(c1)[:3], np.float32) / 255
    B = np.array(C(c2)[:3], np.float32) / 255
    # perspective rows: depth param s from 0 (back) to 1 (front)
    cx = x + w / 2
    mk = cv.rect(x, y0, w, y1 - y0, C(c1))

    def fn(X, Y):
        s = np.clip((Y - y0) / (y1 - y0), 0, 1)
        # row index via integral of height: rows grow 6u -> 16u
        h0, h1 = 6.0, 16.0
        k = (h1 - h0) / (y1 - y0)
        # depth coordinate d with dd/dy = 1/h(y)
        hy = h0 + k * (Y - y0)
        d = np.log(hy / h0) / k
        sc = 0.82 + 0.18 * s
        u = (X - cx) / sc / tile
        par = (np.floor(u) + np.floor(d)) % 2
        col = np.where(par[..., None] > 0.5, B, A)
        # subtle tile bevel at edges
        fu = u - np.floor(u)
        fd = d - np.floor(d)
        edge = ((fu < 0.035) | (fd < 0.06))[..., None]
        col = np.where(edge, col * 0.88, col)
        # depth falloff: darker at the back
        col = col * (0.84 + 0.16 * s[..., None])
        return np.clip(col, 0, 1)
    cv.texture(mk, fn, mode='atop')
    x0, yy0, mm = mk
    hh, ww = mm.shape
    n = value_noise(ww, hh, 18 * cv.D, hash((R.id, 'floor')) % 9999, 2)
    cv.paint((x0, yy0, (0.5 - n).clip(0, 1) * 0.2 * mm), C('#4a3a40'), mode='atop')
    cv.vgrad(x, y0, w, 10, [C('#1c1226', 160), C('#1c1226', 0)], mode='atop')


# ----------------------------------------------------------------------------- grading
def grade_exterior(R, top=(1.06, 0.98, 0.90), mid=(0.97, 0.90, 0.86), base=(0.74, 0.72, 0.88), mid_y=120.0,
                   ground_far=(0.98, 0.94, 0.94), ground_near=(0.88, 0.87, 0.95)):
    cv = R.cv
    ys = (np.arange(cv.H, dtype=np.float32) + 0.5) / cv.D
    g = np.zeros((cv.H, 3), np.float32)
    for i, y in enumerate(ys):
        if y <= mid_y:
            t = y / mid_y
            g[i] = np.array(top) * (1 - t) + np.array(mid) * t
        elif y <= FACADE_BOTTOM:
            t = (y - mid_y) / (FACADE_BOTTOM - mid_y)
            t = t ** 0.8
            g[i] = np.array(mid) * (1 - t) + np.array(base) * t
        else:
            t = (y - FACADE_BOTTOM) / (H - FACADE_BOTTOM)
            g[i] = np.array(ground_far) * (1 - t) + np.array(ground_near) * t
    e = R.cv.em[..., None]
    f = g[:, None, :] * (1 - e) + e
    cv.px[..., :3] *= f


def grade_interior(R, top=(1.02, 0.97, 0.92), bottom=(0.86, 0.82, 0.86)):
    cv = R.cv
    ys = (np.arange(cv.H, dtype=np.float32) + 0.5) / cv.D
    t = (ys / H)[:, None]
    g = np.array(top)[None, :] * (1 - t) + np.array(bottom)[None, :] * t
    e = R.cv.em[..., None]
    cv.px[..., :3] *= g[:, None, :] * (1 - e) + e


def light_pool(R, x, y, rx, ry, color, a=0.25):
    """Baked additive light pool on the ground (subtle) + matching lightmap source."""
    R.cv.radial(x, y, rx, ry, C(color), a=a, mode='add', falloff=1.6)


def sun_rim(R, x, y0, y1, w=1.0, col='#ffc890', a=0.55):
    """Warm rim light on a left-facing edge (low sun from the west)."""
    R.cv.vgrad(x, y0, w, y1 - y0, [C(col), C(col, 0)], a=a, mode='atop')


# ----------------------------------------------------------------------------- lightmap
def build_lightmap(R, cell=8):
    W = int(math.ceil(R.W / cell))
    Hh = 45
    xs = (np.arange(W, dtype=np.float32) + 0.5) * cell
    ys = (np.arange(Hh, dtype=np.float32) + 0.5) * cell
    X, Y = np.meshgrid(xs, ys)
    amb = np.array(C(R.ambient_color)[:3], np.float32) / 255 * R.ambient_level
    L = np.broadcast_to(amb, (Hh, W, 3)).copy()
    for (x, y, rx, ry, col, s) in R.lights:
        d = np.sqrt(((X - x) / rx) ** 2 + ((Y - y) / ry) ** 2)
        f = np.clip(1 - d, 0, 1) ** 1.5
        c = np.array(col[:3], np.float32) / 255
        L += f[..., None] * c[None, None, :] * s
    # value/204 = multiplier; clamp the playable band to 140..240
    v = np.clip(L * 204, 0, 255)
    band = (Y >= R.walk[0] - 40) & (Y <= R.walk[1] + 8)
    v = np.where(band[..., None], np.clip(v, 140, 240), v)
    return Image.fromarray(v.astype(np.uint8), 'RGB')


# ----------------------------------------------------------------------------- export
def save_tiles(img, out_dir, prefix, max_w=2048):
    W = img.width
    files = []
    n = int(math.ceil(W / max_w))
    for i in range(n):
        x0 = i * max_w
        x1 = min(W, x0 + max_w)
        fn = f'{prefix}_{i}.png'
        img.crop((x0, 0, x1, img.height)).save(os.path.join(out_dir, fn), optimize=True)
        files.append(fn)
    return files


def crosswalk(R, x, w=60.0, y0=STREET_TOP + 1, y1=CURB_Y - 1, a=0.22, col='#e8dcc0', bars=6, slant=10.0):
    """Faded zebra crossing in oblique projection (bars slant with depth)."""
    cv = R.cv
    bw = w / (bars * 2 - 1)
    for k in range(bars):
        bx = x + k * 2 * bw
        mk = cv.poly_mask([(bx, y0), (bx + bw, y0), (bx + bw + slant, y1), (bx + slant, y1)])
        x_0, y_0, m = mk
        n = value_noise(m.shape[1], m.shape[0], 2.5 * cv.D, int(bx * 3), 2)
        cv.paint((x_0, y_0, m * np.clip(0.4 + (n - 0.5) * 2.0, 0, 1)), C(col), a=a, mode='atop')


def road_text(R, s, x, y, size=9.0, col='#e8d8a8', a=0.36):
    """Stencilled road marking squashed by the oblique view."""
    cv = R.cv
    mk = cv.text_mask(s, 'cond', size, x, y, 'mm', 0.8, 1.6)
    x0, y0, m = mk
    from PIL import Image as _I
    im = _I.fromarray((m * 255).astype(np.uint8), 'L')
    im = im.resize((im.width, max(1, int(im.height * 0.42))), _I.LANCZOS)
    m2 = np.asarray(im, np.float32) / 255
    n = value_noise(m2.shape[1], m2.shape[0], 2 * cv.D, int(x), 2)
    cv.paint((x0, y0 + (m.shape[0] - m2.shape[0]) // 2, m2 * np.clip(0.5 + (n - 0.5) * 1.6, 0, 1)), C(col), a=a,
             mode='atop')


def painted_curb(R, x, w, col='#e8c040', a=0.55):
    R.cv.rect(x, SIDEWALK_FRONT + 3, w, 4, C(col), a=a, mode='atop')
