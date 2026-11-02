"""Tiny deterministic pixel-art toolkit used by the BACKSTREET OATH generators.

Canvas = numpy RGBA uint8 array. Shapes are boolean masks; painting helpers
fill masks with flat colors plus simple upper-left-lit 2-tone shading, then an
automatic 1px ink outline (#1a1220) is added around silhouettes.
"""
import os
import numpy as np
from PIL import Image, ImageDraw

import font_glyphs as FG


def hexc(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def with_alpha(c, a):
    return (c[0], c[1], c[2], a)


def mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(4))


INK = hexc('#1a1220')
CLEAR = (0, 0, 0, 0)
CREAM = hexc('#e8d8b0')
MUSTARD_HI = hexc('#f0c040')
DANGER = hexc('#e04a4a')
XP = hexc('#4af0f0')
CASH = hexc('#7af04a')
WHITE = hexc('#ffffff')

# material -> (base, dark, light)
MAT = {k: tuple(hexc(c) for c in v) for k, v in {
    'red': ('#c03a3a', '#7a2030', '#e06a5a'),
    'danger': ('#e04a4a', '#a02a3a', '#f08070'),
    'orange': ('#e07a30', '#a0501e', '#f0a060'),
    'mustard': ('#e0b040', '#a87a20', '#f0d070'),
    'yellow': ('#f0c040', '#c09020', '#fff06a'),
    'gold': ('#f0c040', '#a87a20', '#fff4a0'),
    'green': ('#4a9a4a', '#2a5a3a', '#7ac06a'),
    'leaf': ('#7ac04a', '#4a8a3a', '#a8e070'),
    'teal': ('#3a9a9a', '#22605e', '#6ac0c0'),
    'blue': ('#3a6ac0', '#22408a', '#6a9ae0'),
    'navy': ('#22305a', '#141c38', '#3a4a7a'),
    'purple': ('#7a4aa0', '#4a2a6a', '#a070c8'),
    'pink': ('#e06090', '#a03a6a', '#f8a0c0'),
    'gray': ('#8a8a96', '#5a5a66', '#b0b0ba'),
    'charcoal': ('#3a3a46', '#24242e', '#5a5a66'),
    'black': ('#2a2a32', '#18181e', '#4a4a56'),
    'white': ('#e8e4dc', '#b8b0a8', '#ffffff'),
    'paper': ('#e8e4dc', '#b8b0a8', '#ffffff'),
    'cream': ('#e8d8b0', '#b8a07a', '#fff4d8'),
    'denim': ('#4a6a9a', '#30476e', '#7090c0'),
    'brown': ('#7a5030', '#50341e', '#9a6a40'),
    'tan': ('#c8a070', '#987048', '#e0c090'),
    'wood': ('#8a5a34', '#5e3a1e', '#b07a48'),
    'steel': ('#9aa2b0', '#6a7280', '#d0d8e0'),
    'iron': ('#5a6270', '#3a4050', '#8a92a0'),
    'rust': ('#9a5a30', '#6a3a1e', '#c07a40'),
    'brick': ('#a04a3a', '#7a3428', '#c8664a'),
    'skin': ('#f5c9a0', '#d9a07a', '#ffe4c4'),
    'tanskin': ('#d9a07a', '#b07850', '#f0c098'),
    'bread': ('#e0a050', '#a86a30', '#f0c880'),
    'crust': ('#c8803a', '#8a5226', '#e8a85a'),
    'cheese': ('#f0d060', '#c8a030', '#fff4a0'),
    'meat': ('#9a4a30', '#6a2a1e', '#c06a48'),
    'sausage': ('#c05a3a', '#8a3a26', '#e08060'),
    'tomato': ('#e04a3a', '#a02a2a', '#f08070'),
    'coffee': ('#5e3a1e', '#3a2010', '#8a5a34'),
    'chili': ('#a83a26', '#702418', '#d0603a'),
    'noodle': ('#f0d890', '#c8a860', '#fff4c8'),
    'broth': ('#d88a40', '#a0602a', '#f0b060'),
    'glass': ('#6ab0c8', '#3a7a9a', '#c8f0f8'),
    'bottle': ('#4a9a6a', '#2a5a3a', '#9ae0b0'),
    'fish': ('#8ab0c8', '#4a7090', '#d0e8f0'),
    'cardboard': ('#c89a60', '#98703a', '#e0bc84'),
    'egg': ('#f4efe4', '#c8c0b0', '#ffffff'),
    'cherry': ('#d02a3a', '#8a1a2a', '#f07080'),
    'neon': ('#7af04a', '#3aa02a', '#c8ff9a'),
    'cyan': ('#4af0f0', '#2aa0b0', '#c8ffff'),
    'plum': ('#3a2a46', '#24182c', '#5a4466'),
}.items()}


def mat(name):
    return MAT[name]


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), np.uint8)
        yy, xx = np.mgrid[0:h, 0:w]
        self.yy, self.xx = yy, xx

    # ------------------------------------------------------------ masks
    def empty(self):
        return np.zeros((self.h, self.w), bool)

    def R(self, x0, y0, x1, y1):
        """Inclusive rectangle mask."""
        m = self.empty()
        x0c, y0c = max(0, int(x0)), max(0, int(y0))
        x1c, y1c = min(self.w - 1, int(x1)), min(self.h - 1, int(y1))
        if x1c >= x0c and y1c >= y0c:
            m[y0c:y1c + 1, x0c:x1c + 1] = True
        return m

    def E(self, x0, y0, x1, y1, thresh=1.0):
        """Ellipse inscribed in the inclusive bbox."""
        cx = (x0 + x1 + 1) / 2.0
        cy = (y0 + y1 + 1) / 2.0
        rx = (x1 - x0 + 1) / 2.0
        ry = (y1 - y0 + 1) / 2.0
        dx = (self.xx + 0.5 - cx) / rx
        dy = (self.yy + 0.5 - cy) / ry
        return dx * dx + dy * dy <= thresh

    def C(self, cx, cy, r, thresh=1.0):
        """Circle by float center/radius (pixel centers tested)."""
        dx = self.xx + 0.5 - cx
        dy = self.yy + 0.5 - cy
        return dx * dx + dy * dy <= r * r * thresh

    def ring(self, cx, cy, r_out, r_in):
        return self.C(cx, cy, r_out) & ~self.C(cx, cy, r_in)

    def P(self, pts):
        """Filled polygon (PIL semantics, edges included)."""
        im = Image.new('L', (self.w, self.h), 0)
        ImageDraw.Draw(im).polygon([tuple(p) for p in pts], fill=1, outline=1)
        return np.array(im).astype(bool)

    def L(self, x0, y0, x1, y1, w=1):
        im = Image.new('L', (self.w, self.h), 0)
        d = ImageDraw.Draw(im)
        if w <= 1:
            d.line([(x0, y0), (x1, y1)], fill=1, width=1)
        else:
            d.line([(x0, y0), (x1, y1)], fill=1, width=w)
        return np.array(im).astype(bool)

    def Lpath(self, pts, w=1):
        im = Image.new('L', (self.w, self.h), 0)
        ImageDraw.Draw(im).line([tuple(p) for p in pts], fill=1, width=w)
        return np.array(im).astype(bool)

    def chamfer(self, x0, y0, x1, y1, k):
        """Rectangle with 45-degree cut corners of size k."""
        xx, yy = self.xx, self.yy
        m = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
        m &= (xx - x0) + (yy - y0) >= k
        m &= (x1 - xx) + (yy - y0) >= k
        m &= (xx - x0) + (y1 - yy) >= k
        m &= (x1 - xx) + (y1 - yy) >= k
        return m

    def rrect(self, x0, y0, x1, y1, r):
        """Rounded rectangle with pixel-art corner radius r (0..4)."""
        m = self.R(x0, y0, x1, y1)
        if r <= 0:
            return m
        cut = {1: [1], 2: [2, 1], 3: [3, 1, 1], 4: [4, 2, 1, 1], 5: [5, 3, 2, 1, 1],
               6: [6, 4, 3, 2, 1, 1]}[r]
        for i, n in enumerate(cut):
            for (yy, xs) in [(y0 + i, range(x0, x0 + n)), (y0 + i, range(x1 - n + 1, x1 + 1)),
                             (y1 - i, range(x0, x0 + n)), (y1 - i, range(x1 - n + 1, x1 + 1))]:
                for xv in xs:
                    if 0 <= yy < self.h and 0 <= xv < self.w:
                        m[yy, xv] = False
        return m

    def bitmap(self, rows, x, y, ch='#'):
        m = self.empty()
        for ry, row in enumerate(rows):
            for rx, c in enumerate(row):
                if c == ch:
                    X, Y = x + rx, y + ry
                    if 0 <= X < self.w and 0 <= Y < self.h:
                        m[Y, X] = True
        return m

    def textm(self, s, x, y, big=False, micro=False):
        """Mask of string s; (x, y) = top-left of the ascent box."""
        m = self.empty()
        if micro:
            pts = micro_pixels(s)
        else:
            pts = FG.text_pixels(s, big)
        for px, py in pts:
            X, Y = x + px, y + py
            if 0 <= X < self.w and 0 <= Y < self.h:
                m[Y, X] = True
        return m

    # ------------------------------------------------------------ mask ops
    @staticmethod
    def shift(m, dx, dy):
        out = np.zeros_like(m)
        h, w = m.shape
        xs0, xs1 = max(0, -dx), min(w, w - dx)
        ys0, ys1 = max(0, -dy), min(h, h - dy)
        if xs1 > xs0 and ys1 > ys0:
            out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = m[ys0:ys1, xs0:xs1]
        return out

    @classmethod
    def dilate(cls, m, n=1, diag=False):
        for _ in range(n):
            o = m | cls.shift(m, 1, 0) | cls.shift(m, -1, 0) | cls.shift(m, 0, 1) | cls.shift(m, 0, -1)
            if diag:
                o |= cls.shift(m, 1, 1) | cls.shift(m, -1, 1) | cls.shift(m, 1, -1) | cls.shift(m, -1, -1)
            m = o
        return m

    @classmethod
    def erode(cls, m, n=1, diag=False):
        return ~cls.dilate(~m, n, diag)

    @classmethod
    def edge(cls, m, sides='all'):
        """Pixels of m that touch the outside on the given sides."""
        out = np.zeros_like(m)
        sel = {'l': (1, 0), 'r': (-1, 0), 't': (0, 1), 'b': (0, -1)}
        keys = 'lrtb' if sides == 'all' else sides
        for k in keys:
            dx, dy = sel[k]
            out |= m & ~cls.shift(m, dx, dy)
        return out

    # ------------------------------------------------------------ painting
    @property
    def alpha(self):
        return self.a[..., 3] > 0

    def fill(self, m, c):
        if m is None:
            return
        self.a[m] = c

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = c

    def pxs(self, pts, c):
        for x, y in pts:
            self.px(x, y, c)

    def shade(self, m, base, dark=None, light=None, dark_sides='rb', light_sides='lt',
              dark_w=1, light_w=1):
        """Fill m with base, darken bottom/right rim, lighten top/left rim."""
        if isinstance(base, str):
            base, d2, l2 = MAT[base]
            dark = d2 if dark is None else dark
            light = l2 if light is None else light
            if dark is False:
                dark = None
            if light is False:
                light = None
        self.fill(m, base)
        dm = None
        if dark is not None:
            dm = np.zeros_like(m)
            mm = m
            for _ in range(dark_w):
                e = self.edge(mm, dark_sides)
                dm |= e
                mm = mm & ~e
            self.fill(dm, dark)
        if light is not None:
            lm = np.zeros_like(m)
            mm = m if dm is None else (m & ~dm)
            for _ in range(light_w):
                e = self.edge(mm, light_sides) & ~self.edge(m, dark_sides)
                lm |= e
                mm = mm & ~e
            self.fill(lm, light)

    def shade_mat(self, m, name, light=True, dark=True, **kw):
        base, dk, lt = MAT[name]
        self.shade(m, base, dk if dark else None, lt if light else None, **kw)

    def ball(self, m, name, cx=None, cy=None, spec=True):
        """Round-volume shading: dark lower-right crescent, highlight spot upper-left."""
        base, dk, lt = MAT[name]
        ys, xs = np.nonzero(m)
        if len(xs) == 0:
            return
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        cx = (x0 + x1) / 2.0 if cx is None else cx
        cy = (y0 + y1) / 2.0 if cy is None else cy
        rx = max(1.0, (x1 - x0) / 2.0)
        ry = max(1.0, (y1 - y0) / 2.0)
        self.fill(m, base)
        # shadow: pixels on the lower-right that border the outside of a shifted copy
        inner = m & self.shift(m, -1, -1) & self.shift(m, -1, 0) & self.shift(m, 0, -1)
        shadow = m & ~self.shift(inner, 1, 1)
        dxn = (self.xx - cx) / rx
        dyn = (self.yy - cy) / ry
        shadow |= m & ((dxn + dyn) > 1.05)
        self.fill(shadow & ((dxn + dyn) > -0.2), dk)
        if spec:
            hx = cx - rx * 0.45
            hy = cy - ry * 0.45
            hl = m & (((self.xx - hx) / max(1, rx * 0.35)) ** 2 + ((self.yy - hy) / max(1, ry * 0.35)) ** 2 <= 1.0)
            self.fill(hl, lt)

    def outline(self, c=INK, diag=False, where=None):
        m = self.alpha
        if where is not None:
            m = m & where
        o = self.dilate(m, 1, diag) & ~self.alpha
        self.fill(o, c)
        return o

    def inline(self, m, c=INK, sides='all'):
        """Ink the border pixels of a part (an internal outline that eats 1px)."""
        self.fill(self.edge(m, sides), c)

    def blit(self, other, x, y):
        """Alpha-over another canvas or RGBA array at (x, y)."""
        src = other.a if isinstance(other, Canvas) else other
        h, w = src.shape[:2]
        for yy in range(h):
            Y = y + yy
            if not (0 <= Y < self.h):
                continue
            for xx in range(w):
                X = x + xx
                if not (0 <= X < self.w):
                    continue
                s = src[yy, xx]
                if s[3] == 0:
                    continue
                if s[3] == 255:
                    self.a[Y, X] = s
                else:
                    d = self.a[Y, X].astype(float)
                    sa = s[3] / 255.0
                    da = d[3] / 255.0
                    oa = sa + da * (1 - sa)
                    rgb = (s[:3] * sa + d[:3] * da * (1 - sa)) / max(oa, 1e-6)
                    self.a[Y, X] = np.array([*rgb, oa * 255]).round().astype(np.uint8)

    def art(self, rows, x, y, pal):
        """Stamp ASCII art; pal maps chars to RGBA (missing chars = skip)."""
        for ry, row in enumerate(rows):
            for rx, ch in enumerate(row):
                if ch in pal:
                    self.px(x + rx, y + ry, pal[ch])

    def text(self, s, x, y, c, big=False, micro=False, shadow=None):
        if shadow is not None:
            self.fill(self.shift(self.textm(s, x, y, big, micro), 1, 1), shadow)
        self.fill(self.textm(s, x, y, big, micro), c)

    def flip_h(self):
        self.a = self.a[:, ::-1].copy()
        return self

    def image(self):
        return Image.fromarray(self.a, 'RGBA')

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.image().save(path, optimize=False)
        return path


def strip(frames):
    """Concatenate canvases horizontally into a new Canvas."""
    h = max(f.h for f in frames)
    w = sum(f.w for f in frames)
    out = Canvas(w, h)
    x = 0
    for f in frames:
        out.a[0:f.h, x:x + f.w] = f.a
        x += f.w
    return out


# ---------------------------------------------------------------- micro font
MICRO = {k: v.split() for k, v in {
    'A': ".#. #.# ### #.# #.#", 'B': "##. #.# ##. #.# ##.", 'C': ".## #.. #.. #.. .##",
    'D': "##. #.# #.# #.# ##.", 'E': "### #.. ##. #.. ###", 'F': "### #.. ##. #.. #..",
    'G': ".## #.. #.# #.# .##", 'H': "#.# #.# ### #.# #.#", 'I': "### .#. .#. .#. ###",
    'J': "..# ..# ..# #.# .#.", 'K': "#.# #.# ##. #.# #.#", 'L': "#.. #.. #.. #.. ###",
    'M': "#.# ### ### #.# #.#", 'N': "##. #.# #.# #.# #.#", 'O': ".#. #.# #.# #.# .#.",
    'P': "##. #.# ##. #.. #..", 'Q': ".#. #.# #.# ##. .##", 'R': "##. #.# ##. #.# #.#",
    'S': ".## #.. .#. ..# ##.", 'T': "### .#. .#. .#. .#.", 'U': "#.# #.# #.# #.# ###",
    'V': "#.# #.# #.# #.# .#.", 'W': "#.# #.# ### ### #.#", 'X': "#.# #.# .#. #.# #.#",
    'Y': "#.# #.# .#. .#. .#.", 'Z': "### ..# .#. #.. ###",
    '0': "### #.# #.# #.# ###", '1': ".#. ##. .#. .#. ###", '2': "##. ..# .#. #.. ###",
    '3': "##. ..# .#. ..# ##.", '4': "#.# #.# ### ..# ..#", '5': "### #.. ##. ..# ##.",
    '6': ".## #.. ### #.# ###", '7': "### ..# .#. .#. .#.", '8': "### #.# ### #.# ###",
    '9': "### #.# ### ..# ##.", '+': "... .#. ### .#. ...", '-': "... ... ### ... ...",
    '!': ".#. .#. .#. ... .#.", '?': "##. ..# .#. ... .#.", '$': ".## ##. .#. .## ##.",
    '.': "... ... ... ... .#.",
}.items()}


def micro_pixels(s):
    x = 0
    for ch in s:
        if ch == ' ':
            x += 2
            continue
        rows = MICRO.get(ch.upper())
        if rows is None:
            continue
        for ry, row in enumerate(rows):
            for rx, c in enumerate(row):
                if c == '#':
                    yield x + rx, ry
        x += 4


def micro_width(s):
    w = 0
    for ch in s:
        w += 2 if ch == ' ' else 4
    return max(0, w - 1)


def contact_sheet(items, scale=4, cols=8, bg=(58, 50, 66), label=True, cell_pad=6,
                  checker=True):
    """items: list of (name, PIL.Image). Returns a PIL RGB sheet (scaled)."""
    from PIL import ImageFont
    font_path = os.path.join(os.path.dirname(__file__), '..', '..', 'game', 'assets', 'fonts',
                             'oath_pixel.ttf')
    font = ImageFont.truetype(font_path, 8) if os.path.exists(font_path) else None
    cw = max(im.width for _, im in items) * scale + cell_pad * 2
    lab_h = 12 if label else 0
    ch = max(im.height for _, im in items) * scale + cell_pad * 2 + lab_h
    if label and font is not None:
        cw = max(cw, max(int(font.getlength(n)) for n, _ in items) + 8)
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cw, rows * ch), bg)
    d = ImageDraw.Draw(sheet)
    d.fontmode = '1'
    for i, (name, im) in enumerate(items):
        cx, cy = (i % cols) * cw, (i // cols) * ch
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        ox = cx + (cw - big.width) // 2
        oy = cy + cell_pad
        if checker:
            tile = Image.new('RGB', big.size, (90, 82, 98))
            td = ImageDraw.Draw(tile)
            s = max(scale * 2, 4)
            for yy in range(0, big.height, s):
                for xx in range(0, big.width, s):
                    if (xx // s + yy // s) % 2:
                        td.rectangle([xx, yy, xx + s - 1, yy + s - 1], fill=(110, 102, 118))
            sheet.paste(tile, (ox, oy))
        sheet.paste(big, (ox, oy), big)
        if label and font is not None:
            d.text((cx + 4, cy + ch - lab_h), name, font=font, fill=(232, 216, 176))
    return sheet
