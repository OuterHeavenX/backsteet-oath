"""Backstreet Oath env v2 -- architectural kit (all coordinates in world units).

Style rules (docs/ART_DIRECTION.md): 2 tx (1 u) ink on major forms, 1 tx (0.5 u) on details, three-tone cel
shading (shade() hue-shifts toward violet, light() toward warm), low-contrast texture, no photo noise.
"""
import math

import numpy as np

from raster import C, mix, shade, light, ink_of, tone, value_noise, rng_of, blur

MAJOR = 1.0      # ink width in u (2 tx)
DETAIL = 0.5     # 1 tx
INK = C('#1a1220')


class M:
    """Material: base / shadow / deep / light / highlight / ink."""

    def __init__(self, base):
        self.b = base if isinstance(base, tuple) else C(base)
        self.s = shade(self.b, 1.0)
        self.d = shade(self.b, 1.9)
        self.l = light(self.b, 1.0)
        self.h = light(self.b, 2.0)
        self.i = ink_of(self.b)


# ----------------------------------------------------------------------------- surfaces
def brick_wall(cv, x, y, w, h, base, seed, bw=8.0, bh=3.5, var=0.085, mortar=None, calm=False, soot=0.35,
               accent=0.06):
    """Running-bond brick: per-brick tone variation, 1 tx mortar, top light/bottom shade edge per course."""
    m = M(base)
    mk = cv.rect(x, y, w, h, m.b)
    mort = mortar or mix(m.b, C('#c8b8a8'), 0.35)
    mort_s = shade(mort, 0.6)
    rs = np.random.default_rng(abs(hash(('brick', seed))) % (2 ** 32))
    lut = rs.random((512, 512)).astype(np.float32)
    acc = rs.random((512, 512)).astype(np.float32)
    hue = rs.random((512, 512)).astype(np.float32)
    chip = rs.random((512, 512)).astype(np.float32)
    spk = rs.random((256, 256)).astype(np.float32)
    D = cv.D
    nz = None

    def fn(X, Y):
        nonlocal nz
        row = np.floor((Y - y) / bh).astype(np.int64)
        off = (row % 2) * (bw / 2)
        col = np.floor((X - x + off) / bw).astype(np.int64)
        fx = (X - x + off) - col * bw
        fy = (Y - y) - row * bh
        r = lut[row % 512, col % 512]
        a = acc[row % 512, col % 512]
        hv = (hue[row % 512, col % 512] - 0.5) * 2
        cp = chip[row % 512, col % 512]
        v = (r - 0.5) * 2 * (var * (0.5 if calm else 1.0))
        base_rgb = np.array(m.b[:3], np.float32) / 255
        lt_rgb = np.array(m.l[:3], np.float32) / 255
        sh_rgb = np.array(m.s[:3], np.float32) / 255
        out = base_rgb[None, None, :] * (1 + v[..., None])
        # per-brick hue drift (warmer / cooler firing) and a fine fired-clay speckle, both low contrast
        hk = (0.5 if calm else 1.0) * 0.06
        out = out * (1 + hv[..., None] * np.array([hk, hk * 0.15, -hk], np.float32))
        tx = np.floor(X * D).astype(np.int64) % 256
        ty = np.floor(Y * D).astype(np.int64) % 256
        out = out * (1 + (spk[ty, tx][..., None] - 0.5) * (0.04 if calm else 0.06))
        # occasional accent bricks (darker, burnt)
        if accent > 0:
            sel = (a < accent)[..., None]
            out = np.where(sel, out * 0.82 + sh_rgb * 0.1, out)
        # per-course bevel: top 1 tx light, bottom 1 tx shade
        top = (fy < 0.5 + 1e-3)[..., None]
        bot = (fy > bh - 1.0)[..., None]
        out = np.where(top, out * 0.6 + lt_rgb * 0.4, out)
        out = np.where(bot, out * 0.55 + sh_rgb * 0.45, out)
        # chipped arrises: a few bricks lose a corner, showing recessed mortar shadow
        cs = 0.6 + (cp * 7 % 1) * 0.7
        sel_c = cp < (0.05 if calm else 0.10)
        corner = (cp * 13 % 1) < 0.5
        near = np.where(corner, (fx < cs + 0.5) & (fy < cs * 0.8), (fx > bw - cs) & (fy > bh - 0.5 - cs * 0.8))
        chipm = (sel_c & near)[..., None]
        ms_rgb = np.array(mort_s[:3], np.float32) / 255
        out = np.where(chipm, ms_rgb * 0.7 + out * 0.3, out)
        # mortar: recessed, so it sits in the brick's shadow (darker under each course, lit on the head joints)
        mor_bed = (fy > bh - 0.5)[..., None]
        mor_head = (fx < 0.5)[..., None]
        mc = np.array(mort[:3], np.float32) / 255
        dk = sh_rgb * 0.72
        out = np.where(mor_head, mc * 0.25 + ms_rgb * 0.3 + dk * 0.45, out)
        out = np.where(mor_bed, mc * 0.12 + ms_rgb * 0.28 + dk * 0.6, out)
        return np.clip(out, 0, 1)
    cv.texture(mk, fn, mode='atop')
    # broad low-frequency weathering + soot toward the ground
    weather(cv, x, y, w, h, seed, soot=soot)
    return mk


def weather(cv, x, y, w, h, seed, soot=0.35, blotch=0.10, streak=True):
    """Low-frequency grime: blotches, darkening toward the base, faint rain streaks."""
    mk = cv.rect_mask(x, y, w, h)
    x0, y0, m = mk
    hh, ww = m.shape
    n = value_noise(ww, hh, 28 * cv.D, seed, octaves=3)

    def fn(X, Y):
        return np.zeros(X.shape + (3,), np.float32)
    # darkening multiplier built as alpha of a dark tint
    t = np.clip((Y_of(cv, y0, hh) - (y + h * 0.55)) / (h * 0.45 + 1e-6), 0, 1)[:, None]
    al = blotch * np.clip((n - 0.45) * 3.0, 0, 1) + soot * (t ** 1.6) * (0.7 + 0.6 * n)
    if streak:
        rs = rng_of('streak', seed)
        cols = np.zeros(ww, np.float32)
        for _ in range(max(1, int(w / 22))):
            cx = rs.uniform(0, ww)
            wdt = rs.uniform(1.5, 4) * cv.D
            amp = rs.uniform(0.04, 0.10)
            xs = np.arange(ww)
            cols += amp * np.exp(-((xs - cx) / wdt) ** 2)
        fade = np.clip((Y_of(cv, y0, hh) - y) / (h + 1e-6), 0, 1)[:, None]
        al = al + cols[None, :] * (1 - fade) * 0.9
    al = np.clip(al, 0, 0.6) * m
    cv.paint((x0, y0, al.astype(np.float32)), C('#2a1e2e'), mode='atop')


def Y_of(cv, y0, hh):
    return (np.arange(hh, dtype=np.float32) + y0 + cv.oy + 0.5) / cv.D


def stucco(cv, x, y, w, h, base, seed, soot=0.3, cracks=2, peel=True):
    m = M(base)
    mk = cv.rect(x, y, w, h, m.b)
    x0, y0, mm = mk
    hh, ww = mm.shape
    n = value_noise(ww, hh, 10 * cv.D, seed, octaves=2)
    cv.paint((x0, y0, ((n - 0.5) * 0.10).clip(0, 1) * mm), m.l, mode='atop')
    cv.paint((x0, y0, ((0.5 - n) * 0.12).clip(0, 1) * mm), m.s, mode='atop')
    # mottling at two scales + grain (each well under 6 % luminance)
    n2 = value_noise(ww, hh, 3.5 * cv.D, seed + 11, octaves=2)
    cv.paint((x0, y0, ((n2 - 0.5) * 2).clip(0, 1) * mm), m.l, a=0.17, mode='atop')
    cv.paint((x0, y0, ((0.5 - n2) * 2).clip(0, 1) * mm), m.s, a=0.17, mode='atop')
    n3 = value_noise(ww, hh, 18 * cv.D, seed + 23, octaves=2)
    cv.paint((x0, y0, ((0.45 - n3) * 2.5).clip(0, 1) * mm), m.s, a=0.16, mode='atop')
    micro_speckle(cv, x, y, w, h, seed, amt=0.025)
    patch_repairs(cv, x, y, w, h, base, seed)
    if peel:
        peel_paint(cv, x, y, w, h, base, seed)
    weather(cv, x, y, w, h, seed, soot=soot)
    rs = rng_of('crk', seed)
    for _ in range(cracks):
        cx, cy = rs.uniform(x + 4, x + w - 4), rs.uniform(y + 4, y + h * 0.7)
        pts = [(cx, cy)]
        for _k in range(rs.randint(3, 6)):
            cx += rs.uniform(-3, 3)
            cy += rs.uniform(2, 5)
            pts.append((cx, cy))
        cv.line(pts, 0.5, m.d, a=0.7, mode='atop')
    return mk


def concrete_panel(cv, x, y, w, h, base, seed, panel=32.0, soot=0.35, ties=True):
    """Poured concrete with form-panel seams and tie holes."""
    m = M(base)
    mk = stucco(cv, x, y, w, h, base, seed, soot=soot, cracks=1, peel=False)
    xx = x + panel
    while xx < x + w - 2:
        cv.rect(xx, y, 0.5, h, m.s, mode='atop')
        cv.rect(xx + 0.5, y, 0.5, h, m.l, a=0.6, mode='atop')
        # lime/water bleed along the form seams
        stain_streaks(cv, xx - 1.5, y, 3, seed + int(xx), length=(h * 0.15, h * 0.45), n=1, a=0.08)
        xx += panel
    if ties:
        rs = rng_of('ties', seed)
        yy = y + 8
        while yy < y + h - 4:
            xx = x + panel / 4
            while xx < x + w:
                cv.ellipse(xx, yy, 0.8, 0.8, m.d, a=0.6, mode='atop')
                if rs.random() < 0.3:          # rust bleeding from the tie rods
                    stain_streaks(cv, xx - 0.6, yy + 0.6, 1.2, int(xx * 7 + yy), length=(3, 9), n=1, a=0.14,
                                  col='#6a3a24', light_frac=0.0)
                xx += panel / 2
            yy += 14
    return mk


def corrugated(cv, x, y, w, h, base, seed, pitch=4.0, rust=0.3):
    """Vertical corrugated sheet: each ridge has light/base/shade bands; rust streaks hang from the top."""
    m = M(base)
    mk = cv.rect(x, y, w, h, m.b)
    lt = np.array(m.l[:3], np.float32) / 255
    bs = np.array(m.b[:3], np.float32) / 255
    sh = np.array(m.s[:3], np.float32) / 255

    def fn(X, Y):
        f = ((X - x) % pitch) / pitch
        out = np.where((f < 0.3)[..., None], lt, np.where((f < 0.62)[..., None], bs, sh))
        return out
    cv.texture(mk, fn)
    if rust > 0:
        rs = rng_of('rust', seed)
        x0, y0, mm = mk
        hh, ww = mm.shape
        al = np.zeros((hh, ww), np.float32)
        ys = Y_of(cv, y0, hh)
        for _ in range(int(w / 10 * rust) + 1):
            cx = (rs.uniform(x, x + w) * cv.D) - cv.ox - x0
            ln = rs.uniform(0.2, 0.8) * h
            wd = rs.uniform(1, 3) * cv.D
            xs = np.arange(ww)
            prof = np.exp(-((xs - cx) / wd) ** 2)
            vert = np.clip(1 - (ys - y) / ln, 0, 1) ** 0.8
            al += 0.45 * prof[None, :] * vert[:, None]
        cv.paint((x0, y0, np.clip(al, 0, 0.55) * mm), C('#8a4422'), mode='atop')
    brushed_metal(cv, x, y, w, h, base, seed, a=0.16)
    # fastener rows at the sheet laps, rust blooming from the sheet edges and around the screws
    lap = 48.0
    rv = []
    yy = y + lap
    while yy < y + h - 4:
        cv.rect(x, yy - 0.3, w, 0.6, M(base).d, a=0.35, mode='atop')
        xx = x + pitch * 0.5
        while xx < x + w:
            rv.append((xx, yy + 1.2))
            xx += pitch * 2
        yy += lap
    for (rx, ry) in rv:
        cv.ellipse(rx, ry, 0.45, 0.45, M(base).h, a=0.7, mode='atop')
    rust_bloom(cv, x, y, w, h, seed, a=0.42 * (0.6 + rust), edge=6.0, rivets=rv[::2])
    weather(cv, x, y, w, h, seed + 7, soot=0.3, streak=False)
    return mk


def planks_h(cv, x, y, w, h, base, seed, ph=5.0):
    m = M(base)
    mk = cv.rect(x, y, w, h, m.b)
    rs = rng_of('pl', seed)
    yy = y
    while yy < y + h:
        t = rs.uniform(-0.06, 0.06)
        cv.rect(x, yy, w, ph, tone(m.b, 1 + t), mode='atop')
        cv.rect(x, yy + ph - 0.5, w, 0.5, m.d, mode='atop')
        cv.rect(x, yy, w, 0.5, m.l, a=0.6, mode='atop')
        # butt joints
        xx = x + rs.uniform(10, 40)
        while xx < x + w:
            cv.rect(xx, yy, 0.5, ph, m.d, a=0.8, mode='atop')
            xx += rs.uniform(30, 60)
        yy += ph
    wood_grain(cv, x, y, w, h, base, seed, a=0.14)
    weather(cv, x, y, w, h, seed, soot=0.25, streak=False)
    return mk


def plywood(cv, x, y, w, h, seed):
    """Boarding plywood sheets: warm pale wood with grain, darker joints, screws, water marks."""
    base = C('#b8935e')
    m = M(base)
    mk = cv.rect(x, y, w, h, m.b, ink=m.i, iw=DETAIL)
    x0, y0, mm = mk
    hh, ww = mm.shape
    n = value_noise(ww, hh, 3 * cv.D, seed, octaves=1)
    grain = np.sin((Y_of(cv, y0, hh)[:, None] * 2.2 + n * 6.0)) * 0.5 + 0.5
    cv.paint((x0, y0, (grain * 0.12) * mm), m.s, mode='atop')
    sheet = 24.0
    xx = x + sheet
    while xx < x + w - 1:
        cv.rect(xx - 0.5, y, 1, h, m.d, mode='atop')
        xx += sheet
    for yy in (y + 2, y + h - 2):
        xx = x + 3
        while xx < x + w:
            cv.ellipse(xx, yy, 0.5, 0.5, C('#4a3a30'), mode='atop')
            xx += 8
    weather(cv, x, y, w, h, seed, soot=0.45, streak=True)
    return mk


# ----------------------------------------------------------------------------- openings
GLASS_DARK = C('#2a2c48')
WARM_GLASS = [C('#fff2c8'), C('#ffd68a'), C('#e89a58')]
COOL_GLASS = [C('#f0fbff'), C('#bfe6f4'), C('#78a8c8')]
TV_GLASS = [C('#d8e8ff'), C('#90a8e0'), C('#5060a0')]


def window(cv, x, y, w, h, lit=False, seed=0, frame='#d8ccb4', sill=True, lintel=True, kind='sash',
           interior=None, curtains=None, glass=None, frame_w=1.5, mull=True, blind=None, life=None):
    """A recessed window with frame, sill, lintel and glass. Lit glass shows a room box (back wall, side walls,
    ceiling lamp, furniture silhouettes); dark glass shows faint room depth under sky/opposite-building
    reflections and a diagonal sheen. `life`: False = not offered to the engine, str = window kind."""
    rs = rng_of('win', seed, x, y)
    fm = M(frame)
    # lintel / sill
    if lintel:
        cv.rect(x - 1.5, y - 2.5, w + 3, 2.5, fm.b, ink=fm.i, iw=DETAIL)
        cv.rect(x - 1.5, y - 2.5, w + 3, 0.5, fm.l, mode='atop')
    # frame
    cv.rect(x - frame_w, y - 0.5, w + 2 * frame_w, h + 1, fm.b, ink=fm.i, iw=MAJOR)
    gx, gy, gw, gh = x, y, w, h
    is_tv = False
    # room-box geometry (inset back wall)
    ix0, ix1 = gx + gw * 0.16, gx + gw * 0.84
    iy0, iy1 = gy + gh * 0.14, gy + gh * 0.74
    if lit:
        pal = glass or (WARM_GLASS if rs.random() < 0.85 else TV_GLASS)
        is_tv = pal is TV_GLASS
        gm = cv.vgrad(gx, gy, gw, gh, pal, em=1.0)
        deep = mix(pal[2], C('#3a2030'), 0.35)
        cv.fill_poly([(gx, gy), (gx + gw, gy), (ix1, iy0), (ix0, iy0)], deep, a=0.22, em=1.0)           # ceiling
        cv.fill_poly([(gx, gy), (ix0, iy0), (ix0, iy1), (gx, gy + gh)], deep, a=0.16, em=1.0)            # left wall
        cv.fill_poly([(gx + gw, gy), (ix1, iy0), (ix1, iy1), (gx + gw, gy + gh)], deep, a=0.26, em=1.0)  # right wall
        cv.fill_poly([(gx, gy + gh), (ix0, iy1), (ix1, iy1), (gx + gw, gy + gh)], deep, a=0.34, em=1.0)  # floor
        cv.radial((ix0 + ix1) / 2, iy0 + 0.5, gw * 0.42, gh * 0.22, mix(pal[0], C('#ffffff'), 0.5), a=0.45,
                  mode='atop', em=1.0)
        # interior: furniture silhouettes, lamp, person
        sil = mix(pal[2], C('#3a2030'), 0.55)
        interior = interior or rs.choice(['lamp', 'shelf', 'person', 'plant', 'blank', 'tv'])
        base_y = gy + gh
        if interior == 'lamp':
            lx = gx + rs.uniform(0.25, 0.75) * gw
            cv.rect(lx - 0.5, base_y - gh * 0.45, 1, gh * 0.45, sil, em=1.0)
            cv.fill_poly([(lx - 2.5, base_y - gh * 0.45), (lx + 2.5, base_y - gh * 0.45),
                          (lx + 1.5, base_y - gh * 0.62), (lx - 1.5, base_y - gh * 0.62)],
                         mix(pal[0], C('#ffffff'), 0.5), em=1.0)
            cv.radial(lx, base_y - gh * 0.5, 5, 6, mix(pal[0], C('#ffffff'), 0.4), a=0.35, mode='atop', em=1.0)
        elif interior == 'shelf':
            cv.rect(gx, base_y - gh * 0.38, gw, gh * 0.38, sil, a=0.85, em=1.0)
            for k in range(int(gw / 2.5)):
                cv.rect(gx + 0.5 + k * 2.5, base_y - gh * 0.38 - rs.uniform(1.5, 3.5), 1.6, 4,
                        mix(sil, pal[1], rs.uniform(0.1, 0.4)), em=1.0)
        elif interior == 'person':
            px = gx + rs.uniform(0.3, 0.7) * gw
            cv.ellipse(px, base_y - gh * 0.55, 2.2, 2.6, sil, em=1.0)
            cv.fill_poly([(px - 4, base_y), (px - 3.2, base_y - gh * 0.38), (px + 3.2, base_y - gh * 0.38),
                          (px + 4, base_y)], sil, em=1.0)
        elif interior == 'plant':
            px = gx + rs.uniform(0.2, 0.8) * gw
            cv.rect(px - 1.5, base_y - 3, 3, 3, sil, em=1.0)
            for k in range(5):
                a = -math.pi / 2 + (k - 2) * 0.45
                cv.line([(px, base_y - 3), (px + math.cos(a) * 4, base_y - 3 + math.sin(a) * 5)], 1.0, sil,
                        em=1.0)
        elif interior == 'tv':
            cv.vgrad(gx, gy, gw, gh, TV_GLASS, a=0.22, em=1.0)
            tx_ = gx + rs.uniform(0.15, 0.45) * gw
            sw_, sh_ = max(3.0, gw * 0.32), max(2.5, gh * 0.16)
            cv.rect(tx_ - 0.6, base_y - gh * 0.2 - sh_ - 0.6, sw_ + 1.2, sh_ + 1.2, C('#1a1428'), em=1.0)
            cv.rect(tx_, base_y - gh * 0.2 - sh_, sw_, sh_, C('#c8e0ff'), em=1.0)
            cv.radial(tx_ + sw_ / 2, base_y - gh * 0.2 - sh_ / 2, gw * 0.7, gh * 0.4, C('#8ab0ff'), a=0.35, mode='atop',
                      em=1.0)
            is_tv = True
        else:
            # sofa back / table edge low in the room
            cv.rect(ix0 - gw * 0.05, base_y - gh * 0.2, (ix1 - ix0) * 0.8, gh * 0.2, sil, a=0.55, em=1.0)
        # window dressing: paired curtains, one half-drawn curtain, venetian blind, net curtain or bare
        style = rs.choice(['pair', 'pair', 'half', 'blind', 'net', 'none']) if curtains is None else \
            ('pair' if curtains else 'none')
        if style == 'half':
            cc = rs.choice([C('#c85a4a'), C('#d8b860'), C('#8a9a6a'), C('#c8a0b0'), C('#5a7ab0')])
            ccol = mix(cc, pal[1], 0.3)
            cw = gw * rs.uniform(0.4, 0.55)
            left = rs.random() < 0.5
            xa, xb = (gx, gx + cw) if left else (gx + gw - cw, gx + gw)
            cv.fill_poly([(xa, gy), (xb, gy), (xb - (cw * 0.2 if left else -cw * 0.2), gy + gh * 0.55),
                          (xb, gy + gh), (xa, gy + gh)], ccol, em=1.0)
            for k in range(3):
                fx = xa + cw * (0.25 + 0.25 * k)
                cv.line([(fx, gy + 1), (fx + (0.4 if left else -0.4), gy + gh)], 0.4, shade(ccol, 0.6), a=0.7, em=1.0)
            cv.rect(gx, gy, gw, 1.0, shade(ccol, 0.6), em=1.0)
        elif style == 'blind' and not blind:
            blind = rs.uniform(0.3, 0.65)
        elif style == 'net':
            cv.rect(gx, gy + gh * 0.45, gw, gh * 0.55, C('#f4f0e8'), a=0.38, em=1.0)
            for k in range(int(gw / 1.6)):
                cv.rect(gx + k * 1.6, gy + gh * 0.45, 0.4, gh * 0.55, C('#ffffff'), a=0.25, em=1.0)
            cv.rect(gx, gy + gh * 0.45, gw, 0.6, C('#d8d0c0'), em=1.0)
        if rs.random() < 0.3:                                  # pot plant on the inside sill
            px_ = gx + rs.uniform(0.2, 0.8) * gw
            pc = mix(pal[2], C('#2a3a20'), 0.6)
            cv.rect(px_ - 1.4, gy + gh - 2.6, 2.8, 2.6, mix(pal[2], C('#6a3020'), 0.5), em=1.0)
            for k in range(5):
                a_ = -math.pi / 2 + (k - 2) * 0.5
                cv.ellipse(px_ + math.cos(a_) * 2.2, gy + gh - 3.6 + math.sin(a_) * 2.0, 1.2, 0.8, pc, em=1.0)
        if style == 'pair':
            cc = rs.choice([C('#c85a4a'), C('#d8b860'), C('#8a9a6a'), C('#c8a0b0'), C('#e8e0c8')])
            ccol = mix(cc, pal[1], 0.35)
            cw = gw * rs.uniform(0.18, 0.3)
            cv.fill_poly([(gx, gy), (gx + cw, gy), (gx + cw * 0.55, gy + gh), (gx, gy + gh)], ccol, em=1.0)
            cv.fill_poly([(gx + gw - cw, gy), (gx + gw, gy), (gx + gw, gy + gh), (gx + gw - cw * 0.55, gy + gh)],
                         ccol, em=1.0)
            cv.line([(gx + cw * 0.5, gy + 1), (gx + cw * 0.3, gy + gh)], 0.4, shade(ccol, 0.5), a=0.6, em=1.0)
            cv.line([(gx + gw - cw * 0.5, gy + 1), (gx + gw - cw * 0.3, gy + gh)], 0.4, shade(ccol, 0.5), a=0.6,
                    em=1.0)
            cv.rect(gx, gy, gw, 1.0, shade(ccol, 0.6), em=1.0)
        if blind:
            yy = gy
            while yy < gy + gh * blind:
                cv.rect(gx, yy, gw, 0.8, mix(pal[0], C('#ffffff'), 0.3), em=1.0)
                cv.rect(gx, yy + 0.8, gw, 0.5, mix(pal[2], sil, 0.5), em=1.0)
                yy += 1.6
        # glass still reads as glass: sky reflection along the head and a diagonal sheen over the lit room
        sky_l = C(LIGHT.get('sky', '#8a7aa0'))
        cv.vgrad(gx, gy, gw, gh * 0.45, [C(sky_l[:3], 70), C(sky_l[:3], 0)], mode='atop', em=1.0)
        sheen(cv, gx, gy, gw, gh, [[(gx + gw * 0.55, gy), (gx + gw * 0.75, gy), (gx + gw * 0.25, gy + gh),
                                    (gx + gw * 0.05, gy + gh)]], C('#ffffff'), 0.12, em=1.0)
    else:
        sky = C(LIGHT.get('sky', '#8a7aa0'))
        top = mix(C('#3e3a5c'), sky, 0.55)
        gm = cv.vgrad(gx, gy, gw, gh, [top, C('#2e2c48'), C('#22223a')])
        # faint room depth behind the reflections
        cv.rect(ix0, iy0, ix1 - ix0, iy1 - iy0, C('#4a4660'), a=0.22, mode='atop')
        cv.fill_poly([(gx, gy + gh), (ix0, iy1), (ix1, iy1), (gx + gw, gy + gh)], C('#12101e'), a=0.35, mode='atop')
        furn = rs.choice(['sofa', 'lamp', 'chair', 'none', 'shelf'])
        fc = C('#14121e')
        if furn == 'sofa':
            cv.rect(ix0, iy1 - gh * 0.16, (ix1 - ix0) * 0.9, gh * 0.18, fc, a=0.45, mode='atop')
        elif furn == 'lamp':
            lx = rs.uniform(ix0 + 1, ix1 - 1)
            cv.rect(lx - 0.3, iy1 - gh * 0.36, 0.6, gh * 0.36, fc, a=0.5, mode='atop')
            cv.fill_poly([(lx - 2, iy1 - gh * 0.36), (lx + 2, iy1 - gh * 0.36), (lx + 1.3, iy1 - gh * 0.48),
                          (lx - 1.3, iy1 - gh * 0.48)], C('#4a4256'), a=0.5, mode='atop')
        elif furn == 'chair':
            cx_ = rs.uniform(ix0 + 2, ix1 - 2)
            cv.rect(cx_ - 1.6, iy1 - gh * 0.26, 3.2, gh * 0.26, fc, a=0.45, mode='atop')
        elif furn == 'shelf':
            cv.rect(ix0, iy0 + (iy1 - iy0) * 0.3, (ix1 - ix0), 0.6, fc, a=0.5, mode='atop')
        # opposite-building reflection: a darker skyline across the middle of the pane
        sk_y = gy + gh * rs.uniform(0.3, 0.5)
        pts = [(gx, gy + gh)]
        xx = gx
        while xx < gx + gw:
            ty = sk_y + rs.uniform(-gh * 0.12, gh * 0.12)
            nx = min(gx + gw, xx + rs.uniform(3, 7))
            pts += [(xx, ty), (nx, ty)]
            xx = nx
        pts.append((gx + gw, gy + gh))
        cv.fill_poly(pts, C('#1c1a2c'), a=0.42, mode='atop')
        for k in range(int(gw / 4)):                            # lit windows across the street, reflected
            if rs.random() < 0.35:
                cv.rect(gx + 1 + k * 4, sk_y + rs.uniform(2, gh * 0.25), 1.2, 1.6, C('#ffd890'), a=0.45, mode='atop')
        # sky reflection streaks: one broad, one thin diagonal sheen
        sheen(cv, gx, gy, gw, gh, [[(gx + gw * 0.15, gy), (gx + gw * 0.45, gy), (gx + gw * 0.05, gy + gh),
                                    (gx - gw * 0.25, gy + gh)]], mix(sky, C('#ffffff'), 0.25), 0.32)
        sheen(cv, gx, gy, gw, gh, [[(gx + gw * 0.58, gy), (gx + gw * 0.66, gy), (gx + gw * 0.36, gy + gh),
                                    (gx + gw * 0.28, gy + gh)]], mix(sky, C('#ffffff'), 0.5), 0.28)
        if rs.random() < 0.5:
            yy = gy
            while yy < gy + gh * rs.uniform(0.3, 0.7):
                cv.rect(gx, yy, gw, 0.8, C('#9a8a9a'), a=0.8)
                cv.rect(gx, yy + 0.8, gw, 0.4, C('#4a3a4a'), a=0.8)
                yy += 1.4
    # inner recess: shadow on the top/left reveal, light catching the bottom/right reveal
    cv.rect(gx, gy, gw, 1.4, C('#1a1428'), a=0.58, em=1.0 if lit else None)
    cv.rect(gx, gy + 1.4, gw, 1.6, C('#1a1428'), a=0.26, em=1.0 if lit else None)
    cv.rect(gx, gy, 1.2, gh, C('#1a1428'), a=0.42, em=1.0 if lit else None)
    cv.rect(gx, gy + gh - 0.5, gw, 0.5, fm.h, a=0.35, em=1.0 if lit else None)
    cv.rect(gx + gw - 0.5, gy, 0.5, gh, fm.l, a=0.25, em=1.0 if lit else None)
    # mullions
    if mull:
        mc = fm.b
        if kind == 'sash':
            cv.rect(gx, gy + gh / 2 - 0.5, gw, 1, mc, ink=fm.i, iw=DETAIL)
            cv.rect(gx, gy + gh / 2 + 0.5, gw, 0.5, C('#1a1428'), a=0.25, em=1.0 if lit else None)
            if gw > 9:
                cv.rect(gx + gw / 2 - 0.4, gy, 0.8, gh, mc)
        elif kind == 'grid':
            for k in range(1, 3):
                cv.rect(gx + gw * k / 3 - 0.35, gy, 0.7, gh, mc)
            cv.rect(gx, gy + gh / 2 - 0.35, gw, 0.7, mc)
    if getattr(cv, 'log', None) is not None and life is not False:
        D = cv.D
        tx0, ty0 = int(round(gx * D)) - cv.ox, int(round(gy * D)) - cv.oy
        tx1, ty1 = int(round((gx + gw) * D)) - cv.ox, int(round((gy + gh) * D)) - cv.oy
        snap = cv.px[max(0, ty0):max(0, ty1), max(0, tx0):max(0, tx1), :3].copy()
        k_ = life if isinstance(life, str) else ('tv' if is_tv else 'home')
        log(cv, {'type': 'window', 'rect': [round(gx, 1), round(gy, 1), round(gw, 1), round(gh, 1)], 'lit': bool(lit),
                 'kind': k_, 'snap': snap})
    if sill:
        cv.rect(x - 2.5, y + h + 0.5, w + 5, 2, fm.b, ink=fm.i, iw=DETAIL)
        cv.rect(x - 2.5, y + h + 0.5, w + 5, 0.6, fm.h, mode='atop')
        ao_under(cv, x - 2.5, y + h + 3.0, w + 5, 5.0, a=0.42)
        stain_streaks(cv, x - 1, y + h + 3.0, w + 2, seed * 31 + int(x), length=(8, 24 + h * 0.8), a=0.38)
    return (gx, gy, gw, gh)


def door(cv, x, yb, w, h, color, glass=True, lit=False, seed=0, frame='#3a2e34', step=True, knob=True,
         transom=True):
    """Panel door standing on y=yb, x = left edge."""
    m = M(color)
    fm = M(frame)
    y = yb - h
    cv.rect(x - 1.5, y - 1.5, w + 3, h + 1.5, fm.b, ink=fm.i, iw=MAJOR)
    cv.rect(x, y, w, h, m.b, ink=m.i, iw=DETAIL)
    cv.hgrad(x, y, w, h, [m.l, m.b, m.s], a=0.6, mode='atop')
    if glass:
        gw, gh = w - 5, h * 0.36
        if lit:
            cv.vgrad(x + 2.5, y + 3, gw, gh, WARM_GLASS, em=1.0)
        else:
            cv.vgrad(x + 2.5, y + 3, gw, gh, [C('#4a4468'), C('#2a2840')])
        cv.rect(x + 2.5, y + 3, gw, gh, None, ink=m.i, iw=DETAIL)
    # panels
    py = y + (h * 0.45 if glass else 3)
    ph = (yb - py - 3) / 2 - 1
    for k in range(2):
        cv.rect(x + 2.5, py + k * (ph + 2), w - 5, ph, m.s, ink=m.d, iw=DETAIL)
        cv.rect(x + 2.5, py + k * (ph + 2), w - 5, 0.6, m.l, mode='atop')
    ao_under(cv, x, y, w, 7.0, a=0.5)
    cv.rect(x, y, 1.2, h, C('#1a1428'), a=0.4, mode='atop')
    cv.rect(x + w - 0.8, y, 0.8, h, C('#1a1428'), a=0.2, mode='atop')
    cv.rect(x - 1.5, y - 1.5, w + 3, h + 1.5, C('#1a1428'), a=0.12, mode='atop')
    if knob:
        cv.ellipse(x + w - 3, y + h * 0.55, 0.9, 0.9, C('#e8c870'), ink=C('#4a3a20'), iw=DETAIL)
    if transom:
        tm = (x, y - 5, w, 3.5)
        if lit:
            cv.vgrad(*tm, WARM_GLASS, em=1.0)
        else:
            cv.vgrad(*tm, [C('#4a4468'), C('#2a2840')])
        cv.rect(*tm, None, ink=fm.i, iw=DETAIL)
    if step:
        cv.rect(x - 3, yb - 0.5, w + 6, 2.5, C('#8a8078'), ink=C('#2a2228'), iw=DETAIL)
        cv.rect(x - 3, yb - 0.5, w + 6, 0.6, C('#b8ae9e'), mode='atop')


def awning(cv, x, y, w, h, c1, c2=None, stripe=6.0, valance=3.5, scallop=True, seed=0, slope=0.5):
    """Sloped striped canvas awning with valance; returns its bottom y (for cast shadow)."""
    m1 = M(c1)
    m2 = M(c2) if c2 else m1
    top = [(x, y), (x + w, y), (x + w + 2, y + h), (x - 2, y + h)]
    lay = cv.layer()
    lay.fill_poly(top, m1.b)
    if c2:
        k = 0
        xx = x - 2
        while xx < x + w + 2:
            if k % 2:
                lay.fill_poly([(xx + 2 * (1 - 0) * 0, y), (xx + stripe, y), (xx + stripe, y + h), (xx, y + h)], m2.b,
                              mode='atop')
            xx += stripe
            k += 1
    # slope shading: lighter at top fold
    lay.vgrad(x - 2, y, w + 4, h, [(0.0, m1.h), (0.35, m1.b), (1.0, m1.s)], a=0.45, mode='atop')
    # valance
    vy = y + h
    lay.rect(x - 2, vy, w + 4, valance, m1.s)
    if c2:
        k = 0
        xx = x - 2
        while xx < x + w + 2:
            if k % 2:
                lay.rect(xx, vy, min(stripe, x + w + 2 - xx), valance, m2.s, mode='atop')
            xx += stripe
            k += 1
    if scallop:
        xx = x - 2
        while xx < x + w + 2:
            r = stripe / 2
            lay.ellipse(xx + r, vy + valance, r, r * 0.7, (m1.s if int((xx - x + 2) / stripe) % 2 == 0 or not c2 else m2.s))
            xx += stripe
    cv.merge(lay, ink=m1.i, iw=MAJOR)
    depth = h * 1.5 + 4
    ox, oy = wall_shadow_offset(depth)
    bot = vy + valance + 0.5
    defer_shadow(cv, [(x - 2, bot), (x + w + 2, bot), (x + w + 2 + ox, bot + oy), (x - 2 + ox, bot + oy)],
                 a=0.44, soft=1.6)
    return vy + valance + 1.5


def cast_shadow_rect(cv, x, y, w, h, a=0.35, soft=1.5, col='#1a1030'):
    """Soft flat-tone cast shadow (e.g. under an awning or cornice) drawn only on existing pixels."""
    mk = cv.rect_mask(x, y, w, h)
    x0, y0, m = mk
    R = int(soft * cv.D * 2) + 2
    mp = np.pad(m, R)
    mp = blur(mp, soft * cv.D, passes=2)
    cv.paint((x0 - R, y0 - R, mp), C(col), a=a, mode='atop')


def cornice(cv, x, y, w, color, h=4.0, dentils=True):
    m = M(color)
    cv.rect(x - 2, y, w + 4, h, m.b, ink=m.i, iw=MAJOR)
    cv.rect(x - 2, y, w + 4, 0.8, m.h, mode='atop')
    cv.rect(x - 2, y + h - 1.2, w + 4, 1.2, m.s, mode='atop')
    if dentils:
        xx = x
        while xx < x + w:
            cv.rect(xx, y + h, 1.5, 1.5, m.s, ink=m.i, iw=DETAIL)
            xx += 3.5
    cast_shadow_rect(cv, x - 1, y + h + 1.5, w + 2, 2.5, a=0.35)
    ao_under(cv, x - 1, y + h + 1.5, w + 2, 12.0, a=0.38)
    stain_streaks(cv, x, y + h + 1.5, w, int(x * 3 + y), length=(14, 56), n=max(2, int(w / 10)), a=0.32)


def parapet(cv, x, y, w, color, h=5.0):
    m = M(color)
    cv.rect(x, y, w, h, m.b, ink=m.i, iw=MAJOR)
    cv.rect(x, y, w, 1, m.l, mode='atop')
    cv.rect(x, y + h - 1, w, 1, m.s, mode='atop')
    stain_streaks(cv, x, y + h, w, int(x * 5 + y), length=(5, 20), n=max(1, int(w / 14)), a=0.26)


def drainpipe(cv, x, y0, y1, color='#5a5660'):
    m = M(color)
    cv.rect(x - 1, y0, 2, y1 - y0, m.b, ink=m.i, iw=DETAIL)
    cv.rect(x - 1, y0, 0.6, y1 - y0, m.l, mode='atop')
    yy = y0 + 8
    while yy < y1:
        cv.rect(x - 1.6, yy, 3.2, 1.2, m.s, ink=m.i, iw=DETAIL)
        yy += 22
    cv.fill_poly([(x - 1, y1 - 2), (x + 1, y1 - 2), (x + 3, y1), (x - 1, y1)], m.b, ink=m.i, iw=DETAIL)
    proud_shadow(cv, x - 1, y0, 2, y1 - y0, 2.0, a=0.22, soft=0.8)
    yy = y0 + 8
    while yy < y1:
        stain_streaks(cv, x - 1.2, yy + 1.2, 2.4, int(yy * 13 + x), length=(3, 10), n=1, a=0.16, col='#6a3a24',
                      light_frac=0.0)
        yy += 22


def fire_escape(cv, x, w, floors, color='#2e2a36', ladder=True, bottom=None):
    """Iron fire escape: platforms at each y in floors (platform top), railings, stair flights between."""
    m = M(color)
    lay = cv.layer()
    for i, fy in enumerate(floors):
        lay.rect(x - 3, fy, w + 6, 1.5, m.b)
        # rail
        lay.rect(x - 3, fy - 7, w + 6, 0.8, m.b)
        lay.rect(x - 3, fy - 3.5, w + 6, 0.5, m.b)
        xx = x - 3
        while xx <= x + w + 3:
            lay.rect(xx, fy - 7, 0.6, 7, m.b)
            xx += 3
        # brackets
        for bx in (x, x + w):
            lay.line([(bx, fy + 1.5), (bx - 2.5 if bx == x else bx + 2.5, fy + 6)], 0.8, m.b)
        # stairs to next platform
        if i + 1 < len(floors):
            ny = floors[i + 1]
            sx0, sx1 = (x + w * 0.15, x + w * 0.8) if i % 2 == 0 else (x + w * 0.8, x + w * 0.15)
            lay.line([(sx0, fy), (sx1, ny)], 1.0, m.b)
            lay.line([(sx0, fy - 6), (sx1, ny - 6)], 0.6, m.b)
            n = 8
            for k in range(1, n):
                t = k / n
                px = sx0 + (sx1 - sx0) * t
                py = fy + (ny - fy) * t
                lay.rect(px - 1.2, py - 0.3, 2.4, 0.6, m.b)
    if ladder and floors:
        ly0 = floors[-1]
        ly1 = bottom if bottom else ly0 + 30
        for lx in (x + w - 6, x + w - 2):
            lay.rect(lx, ly0, 0.6, ly1 - ly0, m.b)
        yy = ly0 + 2
        while yy < ly1:
            lay.rect(x + w - 6, yy, 4.6, 0.5, m.b)
            yy += 2.5
    cv.merge(lay, ink=None)
    # rim light on the metal (warm top edges)
    for fy in floors:
        cv.rect(x - 3, fy, w + 6, 0.5, M(color).l, a=0.7)
    # cast shadow on the wall
    for fy in floors:
        ox_, oy_ = wall_shadow_offset(5.0)
        defer_shadow(cv, [(x - 3, fy + 1.5), (x + w + 3, fy + 1.5), (x + w + 3 + ox_, fy + 1.5 + oy_),
                          (x - 3 + ox_, fy + 1.5 + oy_)], a=0.40, soft=1.0)


def cable(cv, x0, y0, x1, y1, sag=6.0, w=0.6, col='#1e1824', a=0.9):
    pts = []
    for k in range(25):
        t = k / 24
        pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)))
    cv.line(pts, w, C(col), a=a)
    return pts


def string_lights(cv, x0, y0, x1, y1, sag=5.0, step=6.0, cols=None, seed=0, glow=True):
    pts = cable(cv, x0, y0, x1, y1, sag, 0.5)
    cols = cols or [C('#ffd870'), C('#ff7a6a'), C('#8ad8ff'), C('#a8f088')]
    rs = rng_of('sl', seed)
    n = max(2, int(abs(x1 - x0) / step))
    bulbs = []
    for k in range(1, n):
        t = k / n
        bx = x0 + (x1 - x0) * t
        by = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t) + 1.2
        c = cols[(k + seed) % len(cols)]
        on = rs.random() > 0.08
        if on:
            if glow:
                cv.radial(bx, by, 3.2, 3.2, c, a=0.35, mode='add', falloff=2.0)
            cv.ellipse(bx, by, 0.9, 1.1, mix(c, C('#ffffff'), 0.45), ink=shade(c, 1.4), iw=DETAIL, em=1.0)
        else:
            cv.ellipse(bx, by, 0.9, 1.1, shade(c, 1.5), ink=INK, iw=DETAIL)
        bulbs.append((bx, by, c, on))
    return bulbs


def ac_unit(cv, x, y, w=10.0, h=7.0, color='#b8b4a8'):
    m = M(color)
    cv.rect(x, y, w, h, m.b, ink=m.i, iw=MAJOR)
    yy = y + 1.5
    while yy < y + h - 1:
        cv.rect(x + 1, yy, w - 2, 0.5, m.s)
        yy += 1.2
    cv.rect(x, y, w, 0.6, m.h, mode='atop')
    cv.rect(x + 1, y + h, 1, 2, m.s, ink=m.i, iw=DETAIL)
    cv.rect(x + w - 2, y + h, 1, 2, m.s, ink=m.i, iw=DETAIL)
    rust_bloom(cv, x, y, w, h, int(x * 3 + y), a=0.25, edge=1.5)
    proud_shadow(cv, x, y, w, h, 4.0, a=0.36)
    stain_streaks(cv, x + 1, y + h + 2, w - 2, int(x * 7 + y), length=(8, 28), n=2, a=0.3, light_frac=0.0)
    soot_above(cv, x + 1, y, w - 2, h=12, a=0.22, seed=int(x))


def stoop(cv, x, w, yb, steps=3, color='#8a8078', rail=True, rail_col='#2a2630'):
    m = M(color)
    for k in range(steps):
        sy = yb - (k + 1) * 3
        inset = k * 2.5
        cv.rect(x + inset, sy, w - 2 * inset, 3, m.b, ink=m.i, iw=DETAIL)
        cv.rect(x + inset, sy, w - 2 * inset, 0.7, m.h, mode='atop')
        cv.rect(x + inset, sy + 2.2, w - 2 * inset, 0.8, m.s, mode='atop')
    if rail:
        r = M(rail_col)
        for side in (0, 1):
            rx = x + (1 if side == 0 else w - 1)
            top = yb - steps * 3
            cv.line([(rx, yb - 1), (rx, yb - 12)], 0.7, r.b)
            cv.line([(rx, yb - 12), (rx + (6 if side == 0 else -6), top - 12)], 0.7, r.b)
            cv.line([(rx + (6 if side == 0 else -6), top - 12), (rx + (6 if side == 0 else -6), top)], 0.7, r.b)


# ----------------------------------------------------------------------------- signage & posters
def neon_text(cv, s, cx, cy, size, color, kind='sign', tracking=0.6, glow=0.55, tube=0.8, flicker_off=None):
    """Neon lettering: tube core near-white, coloured tube, dark backing shadow, restrained baked glow."""
    lay = cv.layer()
    mk = lay.text_mask(s, kind, size, cx, cy, 'mm', tracking)
    x0, y0, m = mk
    # outline tube from the glyph edge: draw stroked silhouette (glyph boundary band)
    from raster import dilate as _dil
    R = 4
    mp = np.pad(m, R)
    outer = _dil(mp, tube * cv.D)
    inner = np.clip(1 - _dil(1 - mp, tube * cv.D * 0.9), 0, 1)
    band = np.clip(outer - inner, 0, 1)
    core = np.clip(band * 1.0 - 0.0, 0, 1)
    # backing shadow
    cv.paint((x0 - R + int(cv.D * 1.0), y0 - R + int(cv.D * 1.2), blur(outer, cv.D * 0.8) * 0.6), C('#120a18'))
    # glow halo
    if glow > 0:
        g = blur(outer, cv.D * 4.0, passes=3)
        cv.paint((x0 - R, y0 - R, np.clip(g * 1.4, 0, 1)), color, a=glow, mode='add', em=None)
    cv.paint((x0 - R, y0 - R, band), shade(color, 0.4), em=1.0)
    thin = np.clip(band - (1 - _dil(1 - band, cv.D * 0.45)), 0, 1)
    cv.paint((x0 - R, y0 - R, np.clip(band * 0.85, 0, 1)), mix(color, C('#ffffff'), 0.35), em=1.0)
    hot = np.clip(1 - _dil(1 - band, cv.D * 0.35), 0, 1)
    cv.paint((x0 - R, y0 - R, hot), mix(color, C('#ffffff'), 0.85), em=1.0)
    hh, ww = outer.shape
    log(cv, {'type': 'sign', 'text': s, 'rect': [round((x0 - R + cv.ox) / cv.D, 1), round((y0 - R + cv.oy) / cv.D, 1),
                                                   round(ww / cv.D, 1), round(hh / cv.D, 1)],
             'color': '#%02x%02x%02x' % tuple(color[:3])})
    return (x0 - R, y0 - R, outer)


def painted_text(cv, s, x, y, size, col, kind='sign', anchor='mm', shadow=True, tracking=0.4, ink=None,
                 iw=0.5, a=1.0, fade=0.0, seed=0, scale_x=1.0, em=None):
    if shadow:
        cv.text(s, kind, size, x + 0.6, y + 0.8, shade(col, 2.2), anchor, tracking=tracking, a=0.6 * a,
                scale_x=scale_x, em=em)
    mk = cv.text(s, kind, size, x, y, col, anchor, ink=ink, iw=iw, tracking=tracking, a=a, scale_x=scale_x, em=em)
    if fade > 0:
        x0, y0, m = mk
        n = value_noise(m.shape[1], m.shape[0], 3 * cv.D, seed, 2)
        cv.paint((x0, y0, m * np.clip((n - (1 - fade)) * 3, 0, 1)), shade(col, 0.8), mode='atop')
    return mk


def poster(cv, x, y, w, h, seed, kind=None, tilt=0.0):
    """Paper poster/flyer with simple layout; kinds: missing, evict, gig, boxing, lost_cat, sale, plain."""
    rs = rng_of('poster', seed)
    kind = kind or rs.choice(['gig', 'boxing', 'sale', 'plain', 'lost_cat'])
    paper = {'missing': C('#f0ead8'), 'evict': C('#f4f0e0'), 'gig': rs.choice([C('#e86a4a'), C('#f0c040'), C('#6ab0c8')]),
             'boxing': C('#e8d8b0'), 'sale': C('#f0e060'), 'plain': C('#e8e2d0'), 'lost_cat': C('#f0ece0')}[kind]
    pm = M(paper)
    lay = cv.layer(x - 4, y - 4, w + 8, h + 8)
    lay.fill_poly([(x, y), (x + w, y + tilt), (x + w, y + h + tilt), (x, y + h)], pm.b)
    lay.vgrad(x, y, w, h, [pm.l, pm.b, pm.s], a=0.4, mode='atop')
    dark = C('#2a2230')
    red = C('#b8343a')
    if kind == 'missing':
        lay.text('MISSING', 'cond', h * 0.16, x + w / 2, y + h * 0.13, red, 'mm')
        # photo box with simple face sketch
        px, py, pw, ph = x + w * 0.22, y + h * 0.24, w * 0.56, h * 0.42
        lay.rect(px, py, pw, ph, C('#b8b0a0'))
        lay.ellipse(px + pw / 2, py + ph * 0.42, pw * 0.22, ph * 0.26, C('#8a7a6a'))
        lay.fill_poly([(px + pw * 0.15, py + ph), (px + pw * 0.3, py + ph * 0.68), (px + pw * 0.7, py + ph * 0.68),
                       (px + pw * 0.85, py + ph)], C('#6a5a50'))
        lay.text('ELI', 'cond', h * 0.14, x + w / 2, y + h * 0.76, dark, 'mm')
        for k in range(2):
            lay.rect(x + w * 0.15, y + h * (0.86 + k * 0.06), w * 0.7, h * 0.025, C('#7a7070'))
    elif kind == 'evict':
        lay.text('NOTICE', 'cond', h * 0.15, x + w / 2, y + h * 0.13, red, 'mm')
        lay.text('TO VACATE', 'cond', h * 0.09, x + w / 2, y + h * 0.27, dark, 'mm')
        for k in range(6):
            lay.rect(x + w * 0.12, y + h * (0.38 + k * 0.08), w * (0.76 if k % 3 else 0.5), h * 0.025, C('#8a8080'))
        lay.ellipse(x + w * 0.75, y + h * 0.86, w * 0.1, w * 0.1, C('#c84040'), a=0.8)
    elif kind == 'gig':
        lay.rect(x + 1, y + 1, w - 2, h * 0.45, shade(paper, 1.6))
        lay.ellipse(x + w * 0.5, y + h * 0.25, w * 0.22, h * 0.14, light(paper, 1.5))
        lay.text(rs.choice(['LIVE', 'TONITE', 'BAND', 'DANCE']), 'sign', h * 0.13, x + w / 2, y + h * 0.62, dark, 'mm')
        lay.rect(x + w * 0.2, y + h * 0.78, w * 0.6, h * 0.04, dark, a=0.7)
        lay.rect(x + w * 0.3, y + h * 0.86, w * 0.4, h * 0.04, dark, a=0.7)
    elif kind == 'boxing':
        lay.text('FIGHT', 'sign', h * 0.15, x + w / 2, y + h * 0.15, red, 'mm')
        lay.text('NIGHT', 'sign', h * 0.12, x + w / 2, y + h * 0.3, dark, 'mm')
        lay.ellipse(x + w * 0.32, y + h * 0.58, w * 0.13, h * 0.12, red)
        lay.ellipse(x + w * 0.68, y + h * 0.58, w * 0.13, h * 0.12, C('#3a6ab0'))
        lay.rect(x + w * 0.15, y + h * 0.82, w * 0.7, h * 0.05, dark, a=0.7)
    elif kind == 'sale':
        lay.text('SALE', 'sign', h * 0.22, x + w / 2, y + h * 0.35, red, 'mm')
        lay.text('50%', 'cond', h * 0.18, x + w / 2, y + h * 0.7, dark, 'mm')
    elif kind == 'lost_cat':
        lay.text('LOST CAT', 'cond', h * 0.13, x + w / 2, y + h * 0.13, dark, 'mm')
        lay.ellipse(x + w / 2, y + h * 0.48, w * 0.22, h * 0.17, C('#e0a060'))
        lay.fill_poly([(x + w * 0.33, y + h * 0.38), (x + w * 0.38, y + h * 0.26), (x + w * 0.43, y + h * 0.36)], C('#e0a060'))
        lay.fill_poly([(x + w * 0.57, y + h * 0.36), (x + w * 0.62, y + h * 0.26), (x + w * 0.67, y + h * 0.38)], C('#e0a060'))
        for k in range(3):
            lay.rect(x + w * 0.15, y + h * (0.74 + k * 0.07), w * 0.7, h * 0.03, C('#7a7070'))
    else:
        for k in range(5):
            lay.rect(x + w * 0.15, y + h * (0.2 + k * 0.13), w * (0.7 if k % 2 else 0.5), h * 0.04, C('#6a6070'))
    # weathering: sun-faded, grimy lower edge, a torn corner with the paper curling off it, tape
    lay.rect(x, y, w, h + tilt, C('#f4ecd8'), a=0.16, mode='atop')
    lay.vgrad(x, y + h * 0.6, w, h * 0.4 + tilt, [C('#3a2a20', 0), C('#3a2a20', 90)], mode='atop')
    corner = rs.randrange(4)
    tw, th = w * rs.uniform(0.22, 0.38), h * rs.uniform(0.16, 0.28)
    cx_ = x + w if corner in (1, 3) else x
    cy_ = (y + h + tilt) if corner in (2, 3) else y
    sx_ = -1 if corner in (1, 3) else 1
    sy_ = -1 if corner in (2, 3) else 1
    tri = [(cx_, cy_), (cx_ + sx_ * tw, cy_), (cx_, cy_ + sy_ * th)]
    lay.fill_poly(tri, C('#000000'), mode='erase')
    lay.fill_poly([(cx_ + sx_ * tw, cy_), (cx_, cy_ + sy_ * th), (cx_ + sx_ * tw * 0.55, cy_ + sy_ * th * 0.75)],
                  shade(paper, 0.9))
    lay.line([(cx_ + sx_ * tw, cy_), (cx_, cy_ + sy_ * th)], 0.4, light(paper, 1.5), a=0.8)
    lay.rect(x + w * 0.4, y - 1, w * 0.2, 2, C('#e8e0c0'), a=0.75)
    cv.merge(lay, ink=shade(paper, 2.5), iw=DETAIL, shadow=(0.6, 0.8, 0.6, 0.35, C('#140c18')))


def tag(cv, x, y, s, col, size=7.0, seed=0, a=0.9, slant=-0.15):
    """Spray tag: condensed letters, skewed, drips, overspray."""
    lay = cv.layer(x - size * 4, y - size * 2, size * (len(s) + 8), size * 5)
    mk = lay.text(s, 'cond', size, x, y, col, 'lm', tracking=-0.2, scale_x=0.9)
    rs = rng_of('tag', seed)
    x0, y0, m = mk
    # skew by shifting rows
    h, w = m.shape
    sk = np.zeros_like(m)
    for r in range(h):
        sh = int(round((h - r) * slant * 1.0))
        if sh >= 0:
            sk[r, sh:] = m[r, :w - sh] if sh < w else 0
        else:
            sk[r, :w + sh] = m[r, -sh:]
    lay.px[...] = 0
    lay.paint((x0, y0, sk), col)
    for _ in range(rs.randint(2, 5)):
        dx = rs.uniform(0, w) / cv.D + x0 / cv.D + lay.ox / cv.D
        dy = (y0 + h * 0.85) / cv.D + lay.oy / cv.D
        lay.line([(dx, dy), (dx, dy + rs.uniform(2, 7))], 0.45, col)
    cv.merge(lay, a=a, shadow=(0.0, 0.0, 1.2, 0.25, col))


def graffiti_piece(cv, x, y, w, h, word, fill1, fill2, outline='#1a1220', shadow_col='#2a1a40', seed=0):
    """Wildstyle-lite piece: chunky letters with gradient fill, 3D drop extrusion, white outline + highlights."""
    lay = cv.layer(x - 10, y - 10, w + 20, h + 20)
    size = h * 0.72
    mk = lay.text_mask(word, 'sign', size, x + w / 2, y + h / 2, 'mm', tracking=-0.5)
    x0, y0, m = mk
    sc = min(1.0, (w * cv.D) / max(1, m.shape[1]))
    from raster import dilate as _dil
    R = int(cv.D * 3)
    mp = np.pad(m, R)
    # extrusion
    for k in range(int(cv.D * 3), 0, -1):
        lay.paint((x0 - R + k, y0 - R + k, mp), C(shadow_col))
    # outer white-ish outline, then ink
    lay.paint((x0 - R, y0 - R, _dil(mp, cv.D * 1.6)), C(outline))
    lay.paint((x0 - R, y0 - R, _dil(mp, cv.D * 1.0)), C('#f4f0e8'))
    # gradient fill
    hh = mp.shape[0]
    t = np.linspace(0, 1, hh, dtype=np.float32)[:, None]
    c1 = np.array(C(fill1)[:3], np.float32) / 255
    c2 = np.array(C(fill2)[:3], np.float32) / 255
    rgb = (c1[None, None, :] * (1 - t[..., None]) + c2[None, None, :] * t[..., None])
    rgb = np.broadcast_to(rgb, (hh, mp.shape[1], 3))
    lay.paint((x0 - R, y0 - R, mp), (255, 255, 255, 255), rgb=rgb)
    # highlight stripe + bubbles
    rs = rng_of('gp', seed)
    band = np.zeros_like(mp)
    yy = int(hh * 0.3)
    band[yy:yy + max(1, int(cv.D * 0.8)), :] = 1
    lay.paint((x0 - R, y0 - R, band * mp), C('#ffffff'), a=0.55)
    for _ in range(6):
        bx = rs.uniform(x + 4, x + w - 4)
        by = rs.uniform(y + 4, y + h - 4)
        lay.ellipse(bx, by, 1.0, 1.0, C('#ffffff'), a=0.8, mode='atop')
    # drips
    for _ in range(rs.randint(3, 6)):
        dx = rs.uniform(x + 3, x + w - 3)
        lay.line([(dx, y + h * 0.75), (dx, y + h * 0.75 + rs.uniform(3, 9))], 0.7, C(fill2), mode='over')
    cv.merge(lay)


# ----------------------------------------------------------------------------- realism helpers (v2.1)
# Per-room light context, set by realism.begin_room(): `dir` is the cast-shadow direction (world units, x right /
# y down), `alpha` its strength, `clip` the current facade span (world u) and `sky` the colour reflected by glass.
LIGHT = {'dir': (0.6, 0.22), 'alpha': 0.22, 'interior': False, 'clip': None, 'sky': '#8a7aa0', 'wet': False}


def log(cv, rec):
    """Record life/realism data (window rects, sign rects, deferred shadows) for the room being drawn."""
    if getattr(cv, 'log', None) is None:
        return
    rec.setdefault('clip', LIGHT.get('clip'))
    cv.log.append(rec)


def _grid(cv, x, y, w, h):
    """Texel region of a world rect: (x0, y0, mask, X, Y) with X/Y world-unit coordinate grids."""
    x0, y0, m = cv.rect_mask(x, y, w, h)
    hh, ww = m.shape
    X = (np.arange(ww, dtype=np.float32) + x0 + cv.ox + 0.5) / cv.D
    Y = (np.arange(hh, dtype=np.float32) + y0 + cv.oy + 0.5) / cv.D
    return x0, y0, m, X[None, :], Y[:, None]


def sheen(cv, x, y, w, h, polys, col, a, em=None):
    """Glass reflections clipped to the pane rect (x, y, w, h): each poly is painted at alpha a."""
    x0, y0, rm = cv.rect_mask(x, y, w, h)
    acc = np.zeros_like(rm)
    for pts in polys:
        px0, py0, pm = cv.poly_mask(pts)
        hh, ww = rm.shape
        sx0, sy0 = max(x0, px0), max(y0, py0)
        sx1, sy1 = min(x0 + ww, px0 + pm.shape[1]), min(y0 + hh, py0 + pm.shape[0])
        if sx1 > sx0 and sy1 > sy0:
            acc[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = np.maximum(
                acc[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0], pm[sy0 - py0:sy1 - py0, sx0 - px0:sx1 - px0])
    cv.paint((x0, y0, acc * rm), col, a=a, mode='atop', em=em)


def wall_shadow_offset(depth):
    """Offset (u) of the shadow a wall-mounted object `depth` u proud of the wall throws onto it."""
    if LIGHT.get('interior'):
        return 0.0, depth * 0.8
    dx, dy = LIGHT['dir']
    return dx * depth, (0.55 + abs(dy) * 1.6) * depth


def defer_shadow(cv, pts, a=0.3, soft=1.2):
    """Queue a soft cast shadow polygon; realism.post_room applies it once everything is drawn."""
    log(cv, {'type': 'shadow', 'poly': [(float(px), float(py)) for px, py in pts], 'a': float(a), 'soft': soft})


def proud_shadow(cv, x, y, w, h, depth, a=0.28, soft=1.0):
    """Shadow of a box (x, y, w, h) standing `depth` u proud of the wall, following the room light."""
    if LIGHT.get('alpha', 0) <= 0.01 and not LIGHT.get('interior'):
        a *= 0.5
        ox, oy = 0.0, depth * 0.6
    else:
        ox, oy = wall_shadow_offset(depth)
    pts = [(x, y + h), (x + w, y + h), (x + w + ox, y + h + oy), (x + ox, y + h + oy)]
    if ox > 0:
        pts = [(x + w, y), (x + w + ox, y + oy), (x + w + ox, y + h + oy), (x + ox, y + h + oy), (x, y + h),
               (x + w, y + h)]
    elif ox < 0:
        pts = [(x, y), (x + ox, y + oy), (x + ox, y + h + oy), (x + w + ox, y + h + oy), (x + w, y + h), (x, y + h)]
    defer_shadow(cv, pts, a=a, soft=soft)


def ao_under(cv, x, y, w, h=5.0, a=0.22, col='#1a1028'):
    """Ambient occlusion: soft quadratic falloff below a ledge spanning x..x+w (feathered ends)."""
    x0, y0, m, X, Y = _grid(cv, x - 1.5, y, w + 3, h)
    t = np.clip((Y - y) / max(h, 1e-3), 0, 1)
    ends = np.clip((X - (x - 1.5)) / 2.0, 0, 1) * np.clip(((x + w + 1.5) - X) / 2.0, 0, 1)
    cv.paint((x0, y0, (m * ((1 - t) ** 2) * ends).astype(np.float32)), C(col), a=a, mode='atop')


def stain_streaks(cv, x, y, w, seed, length=(6.0, 22.0), n=None, a=0.16, col='#2a1e2e', light_frac=0.25,
                  light_col='#e8e0d0'):
    """Water stains running down from a ledge at y: irregular soft streaks with tapering tails."""
    rs = rng_of('stain', seed, round(x, 1), round(y, 1))
    n = n if n is not None else max(1, int(w / 9) + (1 if rs.random() < 0.5 else 0))
    Lmax = length[1]
    x0, y0, m, X, Y = _grid(cv, x - 2, y, w + 4, Lmax)
    dark = np.zeros(np.broadcast(X, Y).shape, np.float32)
    lite = np.zeros_like(dark)
    for _ in range(n):
        cx = rs.uniform(x + 0.5, x + w - 0.5)
        wd = rs.uniform(0.5, 2.0)
        L = rs.uniform(*length)
        ph = rs.uniform(0, 6.3)
        amp = rs.uniform(0.6, 1.0)
        t = np.clip((Y - y) / L, 0, 1)
        xc = cx + 0.35 * np.sin(Y * 0.55 + ph) * t
        prof = np.exp(-((X - xc) / (wd * (1 - 0.45 * t))) ** 2)
        tail = (1 - t) ** 1.3 * (Y >= y)
        if rs.random() < light_frac:
            lite = np.maximum(lite, prof * tail * amp)
        else:
            dark = np.maximum(dark, prof * tail * amp)
    # a faint wash right under the ledge
    wash = np.clip(1 - (Y - y) / 2.5, 0, 1) * ((X >= x) & (X <= x + w))
    dark = np.maximum(dark, wash * 0.5)
    cv.paint((x0, y0, (dark * m).astype(np.float32)), C(col), a=a, mode='atop')
    if lite.any():
        cv.paint((x0, y0, (lite * m).astype(np.float32)), C(light_col), a=a * 0.55, mode='atop')


def soot_above(cv, x, y, w, h=22.0, a=0.4, seed=0, col='#1c1420'):
    """Soot plume blackening the wall above a vent/flue mouth spanning x..x+w at y (rises and spreads)."""
    cx = x + w / 2
    spread = w * 0.5 + h * 0.35
    x0, y0, m, X, Y = _grid(cv, cx - spread - 2, y - h, 2 * spread + 4, h + 1)
    t = np.clip((y - Y) / h, 0, 1)
    half = w * 0.5 + t * h * 0.35
    prof = np.exp(-((X - cx) / np.maximum(half, 0.5)) ** 2)
    hh, ww = m.shape
    nz = value_noise(ww, hh, 3 * cv.D, abs(hash(('soot', seed, round(x), round(y)))) % 99991, 2)
    al = prof * (1 - t) ** 1.2 * (0.55 + 0.9 * nz) * (Y <= y)
    cv.paint((x0, y0, (np.clip(al, 0, 1) * m).astype(np.float32)), C(col), a=a, mode='atop')


def peel_paint(cv, x, y, w, h, base, seed, n=None, under=None):
    """Peeling paint: irregular flakes showing the older coat beneath, with a lit lip and a dark curl edge."""
    rs = rng_of('peel', seed, round(x), round(y))
    m = M(base)
    under = under or mix(m.b, C('#cfc6b4'), 0.42)          # the older plaster coat shows through
    n = n if n is not None else max(1, int(w * h / 3200) + (1 if rs.random() < 0.6 else 0))
    for _ in range(n):
        pw, ph = rs.uniform(5, 14), rs.uniform(3, 8)
        px_, py_ = rs.uniform(x + 2, x + w - pw - 2), rs.uniform(y + 4, y + h - ph - 4)
        x0, y0, mm, X, Y = _grid(cv, px_, py_, pw, ph)
        hh, ww = mm.shape
        if hh < 3 or ww < 3:
            continue
        nz = value_noise(ww, hh, 2.0 * cv.D, rs.randint(0, 99999), 2)
        d = np.sqrt(((X - (px_ + pw / 2)) / (pw / 2)) ** 2 + ((Y - (py_ + ph / 2)) / (ph / 2)) ** 2)
        flake = np.clip((0.95 - d - (nz - 0.5) * 0.9) * 6, 0, 1) * mm
        if flake.max() <= 0:
            continue
        cv.paint((x0, y0, flake.astype(np.float32)), under, a=0.85, mode='atop')
        # curled paint edge: a lit lip along the top, a thin shadow where it lifts at the bottom
        up = np.zeros_like(flake)
        up[1:] = flake[:-1]
        dn = np.zeros_like(flake)
        dn[:-1] = flake[1:]
        cv.paint((x0, y0, np.clip(dn - flake, 0, 1).astype(np.float32)), m.h, a=0.6, mode='atop')
        cv.paint((x0, y0, np.clip(up - flake, 0, 1).astype(np.float32)), m.d, a=0.55, mode='atop')


def patch_repairs(cv, x, y, w, h, base, seed, n=None):
    """Patched render/concrete: soft rectangles of a slightly different mix with a faint seam."""
    rs = rng_of('patch', seed, round(x), round(y))
    m = M(base)
    n = n if n is not None else max(1, int(w * h / 3000))
    for _ in range(n):
        pw, ph = rs.uniform(8, 26), rs.uniform(5, 16)
        px_, py_ = rs.uniform(x, x + max(1, w - pw)), rs.uniform(y + 2, y + max(3, h - ph))
        tone_c = m.l if rs.random() < 0.5 else m.s
        x0, y0, mm = cv.rect_mask(px_, py_, pw, ph)
        R_ = int(cv.D * 2)
        soft = blur(np.pad(mm, R_), cv.D * 0.8, passes=2)
        cv.paint((x0 - R_, y0 - R_, soft), tone_c, a=rs.uniform(0.24, 0.36), mode='atop')
        cv.rect(px_, py_, pw, 0.5, m.d, a=0.06, mode='atop')


def wood_grain(cv, x, y, w, h, base, seed, a=0.16, along='x'):
    """Fine wood grain: wavy dark lines along the board plus occasional knots (low contrast)."""
    m = M(base)
    x0, y0, mm, X, Y = _grid(cv, x, y, w, h)
    hh, ww = mm.shape
    nz = value_noise(ww, hh, 4 * cv.D, abs(hash(('grain', seed))) % 99991, 2)
    if along == 'x':
        g = np.sin(Y * 3.1 + nz * 7.0 + np.sin(X * 0.08) * 1.5)
    else:
        g = np.sin(X * 3.1 + nz * 7.0 + np.sin(Y * 0.08) * 1.5)
    lines = np.clip((g - 0.72) / 0.28, 0, 1)
    cv.paint((x0, y0, (lines * mm).astype(np.float32)), m.d, a=a, mode='atop')
    cv.paint((x0, y0, (np.clip((nz - 0.55) * 2.5, 0, 1) * mm).astype(np.float32)), m.l, a=a * 0.5, mode='atop')
    rs = rng_of('knot', seed)
    for _ in range(int(w * h / 900)):
        kx, ky = rs.uniform(x + 2, x + w - 2), rs.uniform(y + 1, y + h - 1)
        cv.ellipse(kx, ky, rs.uniform(0.6, 1.2), 0.5, m.d, a=a * 2.2, mode='atop')


def brushed_metal(cv, x, y, w, h, base, seed, a=0.10, vertical=True):
    """Brushed/rolled sheet streaks: long thin value streaks along the rolling direction."""
    m = M(base)
    x0, y0, mm, X, Y = _grid(cv, x, y, w, h)
    hh, ww = mm.shape
    r = np.random.default_rng(abs(hash(('brush', seed))) % (2 ** 32))
    if vertical:
        s = r.random(ww).astype(np.float32)
        s = np.convolve(s, np.ones(3) / 3, mode='same')[None, :]
        s = s * (0.7 + 0.3 * value_noise(ww, hh, 18 * cv.D, int(r.integers(99999)), 1))
    else:
        s = r.random(hh).astype(np.float32)
        s = np.convolve(s, np.ones(3) / 3, mode='same')[:, None]
        s = s * (0.7 + 0.3 * value_noise(ww, hh, 18 * cv.D, int(r.integers(99999)), 1))
    cv.paint((x0, y0, (np.clip(s - 0.55, 0, 1) * 2 * mm).astype(np.float32)), m.l, a=a, mode='atop')
    cv.paint((x0, y0, (np.clip(0.45 - s, 0, 1) * 2 * mm).astype(np.float32)), m.s, a=a, mode='atop')


def rust_bloom(cv, x, y, w, h, seed, a=0.35, edge=4.0, rivets=None, col='#8a4626'):
    """Rust blooming from sheet edges (top/bottom/sides) and around rivet heads, broken up by noise."""
    x0, y0, mm, X, Y = _grid(cv, x, y, w, h)
    hh, ww = mm.shape
    nz = value_noise(ww, hh, 2.2 * cv.D, abs(hash(('rust', seed))) % 99991, 3)
    de = np.minimum(np.minimum(Y - y, (y + h) - Y), np.minimum(X - x, (x + w) - X))
    al = np.clip(1 - de / edge, 0, 1) ** 1.5 * np.clip((nz - 0.38) * 2.6, 0, 1)
    if rivets:
        for (rx, ry) in rivets:
            d = np.sqrt((X - rx) ** 2 + ((Y - ry) * 1.2) ** 2)
            al = np.maximum(al, np.clip(1 - d / 1.8, 0, 1) * np.clip((nz - 0.3) * 2.2, 0, 1))
            tail = np.exp(-((X - rx) / 0.6) ** 2) * np.clip(1 - (Y - ry) / 7.0, 0, 1) * (Y > ry)
            al = np.maximum(al, tail * 0.45)
    cv.paint((x0, y0, (np.clip(al, 0, 1) * mm).astype(np.float32)), C(col), a=a, mode='atop')
    cv.paint((x0, y0, (np.clip(al - 0.6, 0, 1) * mm).astype(np.float32)), C('#c8743a'), a=a * 0.6, mode='atop')


def micro_speckle(cv, x, y, w, h, seed, amt=0.045):
    """Very fine, low-contrast value speckle (aggregate / plaster grain), centred on zero."""
    x0, y0, mm, X, Y = _grid(cv, x, y, w, h)
    hh, ww = mm.shape
    nz = value_noise(ww, hh, 1.5 * cv.D, abs(hash(('speck', seed))) % 99991, 1)
    cv.paint((x0, y0, (np.clip(nz - 0.5, 0, 1) * 2 * mm).astype(np.float32)), C('#fff4e4'), a=amt * 0.6,
             mode='atop')
    cv.paint((x0, y0, (np.clip(0.5 - nz, 0, 1) * 2 * mm).astype(np.float32)), C('#1a1024'), a=amt, mode='atop')
