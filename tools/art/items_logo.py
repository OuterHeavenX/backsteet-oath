"""Title logo (logo.png, logo_small.png) and app icon (icon.png, icon_64.png).

Letterforms derive from the Oath Big glyphs, upscaled and re-cut at 1x with
45-degree chamfers (diamond opening/closing), so the lettering stays crisp
single-pixel art (no blocky upscaled pixels)."""
import math
import os
import numpy as np
from PIL import Image

import font_glyphs as FG
from pixlib import Canvas, MAT, INK, CLEAR, hexc, mix, with_alpha

INK2 = hexc('#0e0a12')
FACE_Y = [hexc('#fff6c0'), hexc('#fff06a'), hexc('#f0c040'), hexc('#e8a838'), hexc('#e07a30')]
EXTR_R = [hexc('#c03a3a'), hexc('#9a2a34'), hexc('#7a2030'), hexc('#5a1828')]
RED_F = [hexc('#ff8a70'), hexc('#e04a4a'), hexc('#c03a3a'), hexc('#a02a3a')]
TAPE = (hexc('#f4ecd8'), hexc('#d8ccb0'), hexc('#ffffff'), hexc('#b8aa8a'))


def word_mask(word, f, spacing=1, shear=0.0, r_open=None, r_close=None):
    """Return (mask, w, h) for word built from BIG glyphs upscaled by f."""
    glyphs = [FG.BIG[ch] for ch in word]
    cols = sum(len(g[1][0]) for g in glyphs) + spacing * (len(word) - 1)
    rows = 10
    W = cols * f + int(math.ceil(rows * f * shear)) + 2
    H = rows * f
    m = np.zeros((H, W), bool)
    x = 0
    for top, g, _ in glyphs:
        gw = len(g[0])
        gm = np.zeros((H, gw * f), bool)
        for ry, row in enumerate(g):
            for rx, ch in enumerate(row):
                if ch == '#':
                    gm[ry * f:(ry + 1) * f, rx * f:(rx + 1) * f] = True
        # re-cut corners at 1x resolution
        ro = r_open if r_open is not None else max(1, int(round(f * 0.6)))
        rc = r_close if r_close is not None else max(1, int(round(f * 0.4)))
        pad = 4
        gp = np.pad(gm, pad)
        gp = Canvas.dilate(Canvas.erode(gp, ro), ro)
        gp = Canvas.erode(Canvas.dilate(gp, rc), rc)
        gm = gp[pad:-pad, pad:-pad]
        m[:, x:x + gw * f] |= gm
        x += (gw + spacing) * f
    if shear:
        out = np.zeros_like(m)
        for y in range(H):
            dx = int(round((H - 1 - y) * shear))
            out[y, dx:] = m[y, :W - dx]
        m = out
    # trim right
    used = np.nonzero(m.any(axis=0))[0]
    m = m[:, :used.max() + 1]
    return m, m.shape[1], H


def place(c, m, x, y):
    out = c.empty()
    h, w = m.shape
    out[y:y + h, x:x + w] = m[:max(0, min(h, c.h - y)), :max(0, min(w, c.w - x))]
    return out


def bands(c, m, cols, y0, y1):
    """Fill m with hard horizontal color bands from y0..y1."""
    n = len(cols)
    for i, col in enumerate(cols):
        a = y0 + (y1 - y0 + 1) * i // n
        b = y0 + (y1 - y0 + 1) * (i + 1) // n - 1
        c.fill(m & (c.yy >= a) & (c.yy <= b), col)
    c.fill(m & (c.yy < y0), cols[0])
    c.fill(m & (c.yy > y1), cols[-1])


def lettering(c, m, face_cols, extr_cols, depth, outline_w, hi_col, lo_col, sheen=True):
    ys, xs = np.nonzero(m)
    y0, y1 = ys.min(), ys.max()
    # extrusion (down-right)
    ext = c.empty()
    layers = []
    for i in range(1, depth + 1):
        layer = Canvas.shift(m, i, i) & ~m & ~ext
        layers.append(layer)
        ext |= layer
    full = m | ext
    # outline
    o1 = Canvas.dilate(full, 1) & ~full
    rings = [o1]
    acc = full | o1
    for k in range(1, outline_w):
        ok = Canvas.dilate(acc, 1, diag=(k % 2 == 1)) & ~acc
        rings.append(ok)
        acc |= ok
    for r in rings:
        c.fill(r, INK)
    # extrusion shading: color by depth band, darker on the lower facets
    for i, layer in enumerate(layers):
        col = extr_cols[min(len(extr_cols) - 1, i * len(extr_cols) // max(1, depth))]
        c.fill(layer, col)
    # facet lines on extrusion: vertical faces darker than horizontal faces
    vert = ext & Canvas.shift(m, 1, 0) & ~Canvas.shift(m, 0, 1)
    c.fill(vert & layers[0] if layers else vert, extr_cols[min(1, len(extr_cols) - 1)])
    # face
    bands(c, m, face_cols, y0, y1)
    # bevel: top/left inner edge highlight, bottom/right inner edge shade
    top_edge = Canvas.edge(m, 't')
    left_edge = Canvas.edge(m, 'l') & ~top_edge
    c.fill(top_edge, hi_col)
    c.fill(left_edge & (c.yy < (y0 + y1) / 2), hi_col)
    c.fill(Canvas.edge(m, 'b') | Canvas.edge(m, 'r'), lo_col)
    if sheen:
        # diagonal glint streaks across the face
        st = m & (((c.xx + c.yy) % 41) < 2) & (c.yy < y0 + (y1 - y0) * 0.55)
        c.fill(st, mix(face_cols[0], hexc('#ffffff'), 0.5))
    return full | acc


def brick_slab(c, x0, y0, x1, y1, seed=7, bw=14, bh=6, dark=0.0):
    rng = np.random.default_rng(seed)
    m = c.R(x0, y0, x1, y1)
    # ragged broken edge: knock out brick-sized notches along the border
    rows = list(range(y0, y1 + 1, bh))
    for ri, ry in enumerate(rows):
        off = 0 if ri % 2 == 0 else bw // 2
        for bx in range(x0 - bw, x1 + 1, bw):
            bx0 = bx + off
            edge_row = ri in (0, len(rows) - 1)
            edge_col = bx0 < x0 + bw or bx0 + bw > x1 - bw
            if (edge_row or edge_col) and rng.random() < (0.45 if edge_row and edge_col else 0.3):
                m &= ~c.R(bx0, ry, bx0 + bw - 1, ry + bh - 1)
    base = [hexc('#a04a3a'), hexc('#94443a'), hexc('#ac5240'), hexc('#8a3e34')]
    mortar = hexc('#5a3a34')
    c.fill(m, mortar)
    for ri, ry in enumerate(rows):
        off = 0 if ri % 2 == 0 else bw // 2
        for bx in range(x0 - bw, x1 + 1, bw):
            bx0 = bx + off
            brick = c.R(bx0, ry, bx0 + bw - 2, ry + bh - 2) & m
            if not brick.any():
                continue
            col = base[int(rng.integers(0, len(base)))]
            if dark:
                col = mix(col, hexc('#1a1220'), dark)
            c.fill(brick, col)
            c.fill(brick & (c.yy == ry), mix(col, hexc('#c8664a'), 0.6))
            c.fill(brick & (c.yy == ry + bh - 2), mix(col, hexc('#5a2420'), 0.5))
            # chips
            for _ in range(2):
                px = bx0 + int(rng.integers(1, bw - 2))
                py = ry + int(rng.integers(1, bh - 2))
                if 0 <= px < c.w and 0 <= py < c.h and m[py, px]:
                    c.px(px, py, mix(col, hexc('#5a2420'), 0.6))
    return m


def tape_strip(c, x0, y0, x1, y1, seed=3):
    rng = np.random.default_rng(seed)
    m = c.R(x0, y0, x1, y1)
    # torn zig-zag ends
    for y in range(y0, y1 + 1):
        k = int(rng.integers(0, 4))
        m[y, x0:x0 + k] = False
        k = int(rng.integers(0, 4))
        m[y, x1 - k + 1:x1 + 1] = False
    base, shade, hi, crease = TAPE
    c.fill(m, base)
    c.fill(m & (c.yy <= y0 + 1), hi)
    c.fill(m & (c.yy >= y1 - 2), shade)
    # weave texture + creases
    tex = m & (((c.xx * 3 + c.yy * 5) % 11) == 0)
    c.fill(tex, shade)
    for cx in (x0 + (x1 - x0) // 3, x0 + 2 * (x1 - x0) // 3 + 5):
        cr = m & (c.xx == cx) & ((c.yy % 3) != 0)
        c.fill(cr, crease)
    return m


def build_logo(scale='big'):
    if scale == 'big':
        W, H = 440, 120
        fb, fo = 4, 5
        sh = 0.18
        depth_b, depth_o = 5, 4
        ow = 2
    else:
        W, H = 220, 60
        fb, fo = 2, 2
        sh = 0.18
        depth_b, depth_o = 2, 2
        ow = 1
    c = Canvas(W, H)
    mb, wb, hb = word_mask('BACKSTREET', fb, 1, sh)
    mo, wo, ho = word_mask('OATH', fo, 1, sh)
    # brick slab behind everything
    if scale == 'big':
        slab = brick_slab(c, 26, 24, 413, 104, seed=11, bw=14, bh=6, dark=0.18)
        tx0, ty0, tx1, ty1 = 130, 58, 312, 118
        bx, by = (W - wb - depth_b) // 2, 4
        ox, oy = (W - wo - depth_o) // 2 + 2, 62
    else:
        slab = brick_slab(c, 12, 12, 207, 52, seed=11, bw=8, bh=4, dark=0.18)
        tx0, ty0, tx1, ty1 = 64, 28, 155, 58
        bx, by = (W - wb - depth_b) // 2, 2
        ox, oy = (W - wo - depth_o) // 2 + 1, 33
    # slab drop shadow + outline
    sh_m = Canvas.shift(slab, 3 if scale == 'big' else 2, 3 if scale == 'big' else 2) & ~slab
    c.fill(sh_m & ~c.alpha, with_alpha(INK, 150))
    c.fill(Canvas.dilate(slab, 1) & ~slab & ~sh_m, INK)
    # tape strip carrying OATH
    tape = tape_strip(c, tx0, ty0, tx1, ty1)
    c.fill(Canvas.dilate(tape, 1) & ~tape, INK)
    c.fill(Canvas.shift(tape, 2, 2) & ~Canvas.dilate(tape, 1) & ~c.alpha, with_alpha(INK, 140))
    # OATH on the tape
    mo_p = place(c, mo, ox, oy)
    lettering(c, mo_p, RED_F, [hexc('#7a2030'), hexc('#5a1828')], depth_o, 1,
              hexc('#ffb0a0'), hexc('#7a2030'), sheen=False)
    # BACKSTREET (+ soft drop shadow on the wall)
    mb_p = place(c, mb, bx, by)
    sd = 4 if scale == 'big' else 2
    shadow = Canvas.dilate(Canvas.shift(mb_p, sd + depth_b, sd + depth_b), 1) & slab & ~tape
    c.fill(shadow, mix(hexc('#5a2a26'), INK, 0.35))
    lettering(c, mb_p, FACE_Y, EXTR_R, depth_b, ow, hexc('#ffffff'), hexc('#a87a20'))
    return c


def logo():
    return build_logo('big')


def logo_small():
    return build_logo('small')


# ------------------------------------------------------------------ app icon
def icon_64():
    c = Canvas(64, 64)
    shape = c.rrect(1, 1, 62, 62, 6)
    # brick wall background
    wall = Canvas(64, 64)
    brick_slab(wall, -8, -2, 72, 70, seed=5, bw=12, bh=6, dark=0.05)
    c.a[shape] = wall.a[shape]
    # vignette
    d = np.sqrt(((c.xx - 31.5) / 31.5) ** 2 + ((c.yy - 31.5) / 31.5) ** 2)
    vig = shape & (d > 0.95)
    c.a[vig] = (c.a[vig].astype(float) * 0.7).astype(np.uint8) | np.array([0, 0, 0, 255], np.uint8)
    # warm spotlight behind the fist
    glow = shape & (((c.xx - 31) / 26.0) ** 2 + ((c.yy - 24) / 22.0) ** 2 < 1)
    g = c.a[glow].astype(float)
    g[:, :3] = g[:, :3] * 0.75 + np.array([240, 176, 112]) * 0.25
    c.a[glow] = g.astype(np.uint8)

    # ---- taped fist (front view, knuckles toward viewer)
    f = Canvas(64, 64)
    sk, skd, skl = MAT['tanskin']
    skdd = hexc('#8a5a3a')
    tp, tpd, tpl = hexc('#f4ecd8'), hexc('#c8bca0'), hexc('#ffffff')
    wrist = f.R(22, 32, 42, 48)
    f.fill(wrist, sk)
    back = f.rrect(15, 12, 47, 35, 4)
    f.fill(back, sk)
    f.fill(f.edge(back, 'rb'), skd)
    # top row: knuckle segments
    for i in range(4):
        x0 = 16 + i * 8
        fm = f.rrect(x0, 7, x0 + 7, 19, 3)
        f.fill(fm, sk)
        f.fill(f.R(x0 + 2, 8, x0 + 5, 8) & fm, skl)
        f.fill(f.R(x0 + 1, 9, x0 + 2, 10) & fm, skl)
        f.fill(f.edge(fm, 'r') & (f.yy > 10), skd)
    for i in range(1, 4):
        f.fill(f.R(16 + i * 8, 9, 16 + i * 8, 18), skdd)
    # tape across the knuckles
    band = f.R(15, 12, 47, 16) & f.alpha
    f.fill(band, tp)
    f.fill(band & (f.yy == 12), tpl)
    f.fill(band & (f.yy == 16), tpd)
    f.fill(band & (((f.xx + f.yy) % 5) == 0), tpd)
    # second row: curled finger segments
    for i in range(4):
        x0 = 17 + i * 8
        sm = f.rrect(x0, 19, x0 + 6, 27, 2)
        f.fill(sm, sk)
        f.fill(f.R(x0 + 1, 19, x0 + 4, 19) & sm, skl)
        f.fill(f.edge(sm, 'b'), skdd)
        f.fill(f.edge(sm, 'r'), skd)
    f.fill(f.R(16, 18, 47, 18) & f.alpha, skdd)
    # thumb wrapping across the lower segments
    thumb = f.P([(12, 22), (16, 20), (34, 25), (35, 29), (32, 31), (14, 30)])
    f.fill(thumb, sk)
    f.fill(f.edge(thumb, 't') & (f.xx > 16), skl)
    f.fill(f.edge(thumb, 'b'), skdd)
    f.fill(f.R(29, 26, 32, 28) & thumb, hexc('#f0c8a8'))
    f.fill(f.edge(thumb, 'r') & (f.yy > 25), skdd)
    # wrist wraps
    wraps = f.R(21, 33, 43, 47)
    f.fill(wraps, tp)
    for y in (36, 40, 44):
        f.fill(f.R(21, y, 43, y), tpd)
    f.fill(f.L(21, 47, 34, 33), tpd)
    f.fill(f.R(21, 33, 43, 33), tpl)
    f.fill(f.R(42, 33, 43, 47), tpd)
    f.outline()
    # ---- monogram
    mb, wb, hb = word_mask('BO', 2, 2, 0.0, r_open=0, r_close=0)
    mon = Canvas(64, 64)
    mp = place(mon, mb, (64 - wb) // 2 - 1, 42)
    lettering(mon, mp, FACE_Y, EXTR_R, 2, 1, hexc('#ffffff'), hexc('#a87a20'), sheen=False)
    c.blit(f, 0, 0)
    c.blit(mon, 0, 0)
    # frame
    c.fill(c.edge(shape, 'all'), INK)
    c.fill(c.edge(c.erode(shape, 1), 'all') & ~f.alpha & ~mon.alpha, hexc('#5a2420'))
    return c


def icon():
    small = icon_64()
    big = Canvas(256, 256)
    big.a = np.repeat(np.repeat(small.a, 4, axis=0), 4, axis=1)
    return big


LOGO = [('logo', logo), ('logo_small', logo_small), ('icon_64', icon_64), ('icon', icon)]
LOGO_SIZES = {'logo': (440, 120), 'logo_small': (220, 60), 'icon_64': (64, 64), 'icon': (256, 256)}


def preview(out_dir, items):
    d = dict(items)
    for bgcol, name in [((26, 18, 32), 'dark'), ((138, 200, 232), 'sky')]:
        sheet = Image.new('RGBA', (460, 200), bgcol + (255,))
        sheet.alpha_composite(d['logo'], (10, 6))
        sheet.alpha_composite(d['logo_small'], (10, 134))
        sheet.alpha_composite(d['icon_64'], (250, 132))
        sheet.save(os.path.join(out_dir, 'logo_1x_%s.png' % name))
    big = Image.new('RGBA', (900, 250), (26, 18, 32, 255))
    big.alpha_composite(d['logo'].resize((880, 240), Image.NEAREST), (10, 5))
    big.save(os.path.join(out_dir, 'logo_2x.png'))
    ic = Image.new('RGBA', (560, 280), (58, 50, 66, 255))
    ic.alpha_composite(d['icon'], (10, 12))
    ic.alpha_composite(d['icon_64'].resize((256, 256), Image.NEAREST), (290, 12))
    ic.save(os.path.join(out_dir, 'icon_preview.png'))
