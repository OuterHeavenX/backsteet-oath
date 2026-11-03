"""Backstreet Oath env v2.1 -- room-level realism pass (docs/visual/ASSET_CONTRACT_V2.md section 2b).

Runs on the finished base canvas of a room, after every facade/ground/extra has been drawn and before the dusk
grade. Everything here is low contrast and deterministic:
  - deferred cast shadows queued by kit primitives (awnings, fire escapes, pipes, AC units), following the
    room's light direction;
  - material micro-texture (multiplicative, <= ~5 % luminance, reduced to a third inside the walk band);
  - a grime gradient over the bottom 20 u of walls, ambient occlusion along the wall/ground contact and in the
    inner corners between buildings;
  - baked light: warm spill from lit windows/signs onto the sidewalk or floor, a soft bounce halo around
    emissive texels and faint pools consistent with the room's glows;
  - wet ground: vertical colour smears mirroring signs and lights (rain districts, neon streets, puddles) and
    a few specular streaks;
  - sparse weeds in the wall/pavement crack.
It also checks which logged windows are still plain glass (not covered by later signs) for the life data.
"""
import math

import numpy as np

from raster import C, mix, blur, value_noise, rng_of
import kit
import room as roommod
from room import FACADE_BOTTOM as FB, INT_WALL_BOTTOM as WB, H, CURB_Y

# glass reflects this (sky / opposite street) colour, per district
SKY_REFLECT = {'old_quarter': '#c88a8a', 'canal_market': '#a8c8d8', 'ironworks': '#8a94a8', 'neon_mile': '#5a3a7a',
               'floodgate': '#7a9098', 'warehouse': '#3a5050', 'underline': '#3a504a'}
# wet ground reflections: strength of the mirrored smear (0 = dry)
WET = {'floodgate': 0.36, 'neon_mile': 0.42, 'underline': 0.12, 'warehouse': 0.06}
WEEDY = {'old_quarter', 'canal_market', 'ironworks', 'floodgate'}
NO_SKY = {'iy_foundry', 'rw_storage', 'rw_office', 'rw_floor', 'nm_backalley', 'ul_station', 'ul_tunnel', 'ul_vault'}


def begin_room(R):
    """Attach the life log to the room canvas and set the kit light context for this room."""
    R.life_log = []
    R.cv.log = R.life_log
    R.puddles = []
    R.water = []
    R.shafts = []
    R.sway = []
    R.signs_extra = []
    R.windows_extra = []
    R.lanes = []
    kit.LIGHT.update(dir=tuple(R.cast_shadow.get('dir', (0.0, 0.2))), alpha=float(R.cast_shadow.get('alpha', 0.0)),
                     interior=bool(R.interior), clip=None, sky=SKY_REFLECT.get(R.district, '#8a7aa0'),
                     wet=R.district in WET)


def _blur_axis(a, r, axis):
    """Box blur (3 passes) along one axis of an array."""
    r = int(max(1, round(r)))
    out = a.astype(np.float32)
    for _ in range(3):
        n = out.shape[axis]
        pad = [(0, 0)] * out.ndim
        pad[axis] = (r + 1, r)
        p = np.pad(out, pad, mode='edge')
        cs = np.cumsum(p, axis=axis, dtype=np.float64)
        hi = np.take(cs, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
        lo = np.take(cs, np.arange(0, n), axis=axis)
        out = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return out


def check_windows(R):
    """Mark logged windows whose glass was later painted over (signs, awnings, other facades)."""
    cv = R.cv
    D = cv.D
    for rec in R.life_log:
        if rec.get('type') != 'window':
            continue
        x, y, w, h = rec['rect']
        has_snap = 'snap' in rec
        snap = rec.pop('snap', None)
        clip = rec.get('clip')
        ok = 0 <= x and x + w <= R.W and (not has_snap or (snap is not None and snap.size > 0))
        if not has_snap:
            rec['ok'] = bool(ok)
            continue
        if ok and clip is not None and (x < clip[0] - 0.5 or x + w > clip[1] + 0.5):
            ok = False
        if ok:
            tx0, ty0 = int(round(x * D)), int(round(y * D))
            cur = cv.px[ty0:ty0 + snap.shape[0], tx0:tx0 + snap.shape[1], :3]
            if cur.shape != snap.shape:
                ok = False
            else:
                diff = np.abs(cur - snap).max(axis=2) > 0.06
                ok = diff.mean() < 0.12
        rec['ok'] = bool(ok)


def apply_shadows(R):
    cv = R.cv
    D = cv.D
    em = cv.em
    for rec in R.life_log:
        if rec.get('type') != 'shadow':
            continue
        x0, y0, m = cv.poly_mask(rec['poly'])
        rpad = int(rec.get('soft', 1.2) * D * 2) + 2
        mp = blur(np.pad(m, rpad), rec.get('soft', 1.2) * D, passes=2)
        xa, ya = x0 - rpad, y0 - rpad
        h, w = mp.shape
        sx0, sy0 = max(0, xa), max(0, ya)
        sx1, sy1 = min(cv.W, xa + w), min(cv.H, ya + h)
        if sx1 <= sx0 or sy1 <= sy0:
            continue
        mm = mp[sy0 - ya:sy1 - ya, sx0 - xa:sx1 - xa]
        k = 1 - rec['a'] * mm * (1 - em[sy0:sy1, sx0:sx1])
        cv.px[sy0:sy1, sx0:sx1, :3] *= k[..., None]


LIGHT_MODE = {'old_quarter': 'sun', 'canal_market': 'sun', 'ironworks': 'sun', 'floodgate': 'sky',
              'neon_mile': 'street', 'warehouse': 'overhead', 'underline': 'overhead'}
ROADS = {'street', 'wet_road', 'neon_asphalt'}


def _aniso_noise(W, H, cx, cy, seed):
    """Value noise with feature size cx x cy texels (stretched along y when cy > cx)."""
    from PIL import Image
    hs = max(4, int(H * cx / cy))
    n = value_noise(W, hs, cx, seed, 2)
    return np.asarray(Image.fromarray(n, 'F').resize((W, H), Image.BICUBIC), np.float32)


def _tint(col):
    c = np.array(C(col)[:3] if isinstance(col, str) else col[:3], np.float32) / 255.0
    c = c / max(1e-3, c.max())
    return c * 0.65 + 0.35


def post_room(R):
    cv = R.cv
    D = cv.D
    Ht, Wt = cv.H, cv.W
    px = cv.px
    em = cv.em
    alpha = px[..., 3]
    seed = abs(hash(('real', R.id))) % 99991
    B = WB if R.interior else FB
    Bt = int(B * D)
    ys = (np.arange(Ht, dtype=np.float32) + 0.5) / D
    xs = (np.arange(Wt, dtype=np.float32) + 0.5) / D
    walk0, walk1 = R.walk
    rs = rng_of('post', R.id)
    check_windows(R)
    apply_shadows(R)
    ne = 1 - em
    # painted canal/river water is not a wall: keep it out of the facade gradient, grime and weeds
    water = np.zeros((Ht, Wt), np.float32)
    wcols = []
    for wr in R.water:
        if wr.get('kind') != 'canal':
            continue
        x, y, w, h = wr['rect']
        water[max(0, int(y * D)):int((y + h) * D), max(0, int(x * D)):int((x + w) * D)] = 1.0
        wcols.append((x, x + w))
    dry = 1 - water

    # --- facade light gradient, per column from the roofline to the wall base, matching the light source
    if not R.interior:
        opq = alpha > 0.5
        top_t = np.where(opq[:Bt].any(0), opq[:Bt].argmax(0), Bt).astype(np.float32)
        top_u = top_t / D
        span = np.maximum(B - top_u, 30.0)[None, :]
        t = np.clip((ys[:, None] - top_u[None, :]) / span, 0, 1)
        mode = LIGHT_MODE.get(R.district, 'sun')
        if mode == 'sun':
            f = 1.10 - 0.22 * t
        elif mode == 'sky':
            f = 1.08 - 0.17 * t
        elif mode == 'street':
            f = 0.82 + 0.32 * t ** 1.5
        else:
            f = 1.08 - 0.18 * t
        wall = (ys < B)[:, None]
        px[..., :3] *= np.where(wall, 1 + (f - 1) * ne * dry, 1.0)[..., None]

    # --- material micro-texture: multiplicative, low contrast, calmer in the walk band
    n2 = value_noise(Wt, Ht, 6.0 * D, seed + 1, 2)
    n3 = value_noise(Wt, Ht, 24.0 * D, seed + 2, 2)
    mod = (n2 - 0.5) * 0.015 + (n3 - 0.5) * 0.05
    band = ((ys >= walk0 - 2) & (ys <= walk1 + 2)).astype(np.float32)[:, None]
    px[..., :3] *= (1 + mod * (1 - 0.68 * band) * ne)[..., None]

    # --- walk band / floor: low-frequency wear only (stains, patched asphalt, tyre tracks), about +-5 %
    g_rows = slice(Bt, min(Ht, int(CURB_Y * D)) if not R.interior else Ht)
    gh = (g_rows.stop - g_rows.start)
    if gh > 0:
        nL = value_noise(Wt, gh, 34 * D, seed + 11, 2)
        lf = 1 + (nL - 0.5) * (0.10 if not R.interior else 0.06)
        styles = {g['style'] for g in R.data.get('ground', [])}
        if not R.interior:
            yy = ys[g_rows][:, None]
            for _ in range(int(R.W / 260) + 1):                    # patched / resurfaced rectangles
                pw, ph = rs.uniform(30, 90), rs.uniform(8, 22)
                px0, py0 = rs.uniform(0, R.W - pw), rs.uniform(B + 6, CURB_Y - ph - 2)
                mk = np.clip(1 - np.maximum(np.abs(xs[None, :] - (px0 + pw / 2)) - pw / 2,
                                            np.abs(yy - (py0 + ph / 2)) - ph / 2) / 3.0, 0, 1)
                lf = lf * (1 + mk * rs.choice([-0.045, 0.035]))
            if styles & ROADS:
                tn = value_noise(Wt, 1, 60 * D, seed + 12, 2)[0]
                for _ in range(2):                                  # tyre tracks along the lanes
                    ty = rs.uniform(262, CURB_Y - 18)
                    for dy in (0.0, 9.0):
                        prof = np.exp(-((yy - ty - dy) / 1.8) ** 2)
                        lf = lf * (1 - 0.05 * prof * np.clip((tn[None, :] - 0.3) * 2, 0, 1))
        px[g_rows, :, :3] *= (1 + (lf - 1) * ne[g_rows])[..., None]

    # --- grime band at street level (splashed, irregular top) + contact AO either side of the base line
    nx = value_noise(Wt, 1, 9 * D, seed + 3, 2)[0]
    gtop = B - 24 + (nx - 0.5) * 10
    tg = np.clip((ys[:, None] - gtop[None, :]) / (B - gtop[None, :]), 0, 1) * (ys < B)[:, None]
    sn = _aniso_noise(Wt, Ht, 2.0 * D, 9 * D, seed + 4)
    grime = tg ** 1.3 * (0.16 + 0.14 * sn) + (np.clip(1 - (B - ys) / 3.0, 0, 1) * (ys < B))[:, None] * 0.14
    below = (np.clip(1 - (ys - B) / 6.0, 0, 1) * (ys >= B))[:, None] * 0.14
    px[..., :3] *= (1 - (grime + below) * ne * dry)[..., None]

    # --- inner-corner AO where two buildings meet (exterior) / toward the side walls (interior)
    if not R.interior:
        edges = set()
        for f_ in R.data.get('facades', []):
            edges.add(round(f_['x'], 1))
            edges.add(round(f_['x'] + f_['w'], 1))
        edges = [e for e in edges if 2 < e < R.W - 2]
        if edges:
            prof = np.zeros(Wt, np.float32)
            for e in edges:
                prof = np.maximum(prof, np.exp(-np.abs(xs - e) / 4.0))
            wallm = (ys < B)[:, None] * (alpha > 0.5)
            px[..., :3] *= (1 - 0.32 * prof[None, :] * wallm * ne)[..., None]
    else:
        side = np.exp(-xs / 30.0) + np.exp(-(R.W - xs) / 30.0)
        wallm = (ys < B)[:, None].astype(np.float32)
        px[..., :3] *= (1 - 0.24 * np.clip(side, 0, 1)[None, :] * wallm * ne)[..., None]
        top = np.clip(1 - ys / 40.0, 0, 1)[:, None] ** 1.5
        px[..., :3] *= (1 - 0.18 * top * ne)[..., None]

    # --- baked light: spill onto pavement/floor (additive) ...
    E = px[..., :3] * em[..., None]
    span_ = 150 if R.interior else 90
    s0 = max(0, int((B - span_) * D))
    src = E[s0:Bt]
    if src.shape[0] > 0:
        wgt = np.linspace(0.35, 1.0, src.shape[0], dtype=np.float32)[:, None, None]
        S = (src * wgt).sum(0) / max(1, src.shape[0])
        S_near = _blur_axis(S, 4 * D, 0)
        S_far = _blur_axis(S, 16 * D, 0)
        L = 60.0 if R.interior else 50.0
        rows = np.arange(Bt, min(Ht, int((B + L) * D)))
        if len(rows):
            tt = ((rows + 0.5) / D - B) / L
            fs = ((1 - tt) ** 2) * np.clip(((rows + 0.5) / D - B) / 1.5, 0, 1)
            ks = 0.6 if R.interior else 0.8
            for i, r in enumerate(rows):
                Sy = S_near * (1 - tt[i]) + S_far * tt[i]
                px[r, :, :3] += ks * fs[i] * Sy * alpha[r][:, None] * ne[r][:, None]
            for xu in range(16, R.W, 32):
                c = S_far[min(Wt - 1, int(xu * D))]
                lum = float(c.mean())
                if lum > 0.05:
                    col = np.clip(c / max(1e-3, c.max()), 0, 1)
                    R.light(xu, B + 12, 34, 22, (int(col[0] * 255), int(col[1] * 255), int(col[2] * 255), 255),
                            min(0.12, lum * 0.4))
    # ... and multiplicative light pools on every lit surface around windows, signs, glows and lamps
    G1 = blur(E, 4 * D, passes=2)
    G2 = blur(E, 15 * D, passes=2)
    pool = np.minimum(1.1 * G1 + 2.2 * G2, 0.42)
    hz = Ht
    for g in list(R.glows):
        if g.get('front'):
            continue
        en = float(g.get('energy', 0.5))
        down = g.get('flicker') in ('none', 'fluor', 'flame') and g['y'] < B - 40 and \
            (R.interior or R.district in ('underline', 'warehouse'))
        if down:            # ceiling light: a cone of light washing down the wall below it
            gx, gy, rx_, ry_ = g['x'], g['y'] + g['r'] * 1.4, g['r'] * 1.5, g['r'] * 2.6
        else:
            gx, gy, rx_, ry_ = g['x'], g['y'], g['r'] * 1.25, g['r'] * 1.25
        x0, x1 = max(0, int((gx - rx_) * D)), min(Wt, int((gx + rx_) * D) + 1)
        y0, y1 = max(0, int((gy - ry_) * D)), min(hz, int((gy + ry_) * D) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        d = np.sqrt(((xs[None, x0:x1] - gx) / rx_) ** 2 + ((ys[y0:y1, None] - gy) / ry_) ** 2)
        k = np.clip(1 - d, 0, 1) ** (1.6 if down else 2.0) * (min(0.55, 1.3 * en) if down else min(0.5, 0.8 * en))
        pool[y0:y1, x0:x1] += k[..., None] * _tint(g['color'])[None, None, :] * 0.8
    for (hx, hy, gy_, col) in getattr(R, 'lamps', []):
        for (cx_, cy_, rx_, ry_, a_) in ((hx, hy + 6, 58.0, 62.0, 0.30), (hx, gy_ + 4, 46.0, 15.0, 0.26)):
            x0, x1 = max(0, int((cx_ - rx_) * D)), min(Wt, int((cx_ + rx_) * D) + 1)
            y0, y1 = max(0, int((cy_ - ry_) * D)), min(hz, int((cy_ + ry_) * D) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            d = np.sqrt(((xs[None, x0:x1] - cx_) / rx_) ** 2 + ((ys[y0:y1, None] - cy_) / ry_) ** 2)
            pool[y0:y1, x0:x1] += (np.clip(1 - d, 0, 1) ** 1.8 * a_)[..., None] * _tint(col)[None, None, :]
    pool = np.minimum(pool, 0.6)
    v_ = np.clip(px[..., :3].max(axis=2) / np.maximum(alpha, 1e-3), 0, 1.5)
    mult = 1 + pool * (alpha * ne * np.clip(1 - 0.9 * np.minimum(v_, 1) ** 1.5, 0, 1))[..., None]
    lim = np.maximum(1.0, 0.86 / np.maximum(v_, 1e-3))[..., None]       # never push a surface past ~0.86
    mult = np.minimum(mult, lim)
    # night / indoor: light is local, so surfaces away from every source fall off (relative light pools)
    mode = 'interior' if R.interior else LIGHT_MODE.get(R.district, 'sun')
    dk = {'interior': 0.16, 'overhead': 0.2, 'street': 0.16, 'sky': 0.06}.get(mode, 0.0)
    if dk > 0:
        P = np.clip(pool.mean(axis=2) / 0.22, 0, 1)
        P = blur(P, 3 * D, passes=1)
        fall = 1 - dk * (1 - P) * (alpha * ne)
        if not R.interior:
            fall = np.where((ys < B)[:, None], fall, 1 - (1 - fall) * 0.6)
        mult = mult * fall[..., None]
    px[..., :3] *= mult

    # --- wet ground: coloured vertical reflection streaks under every light, longer for higher sources
    wet = WET.get(R.district, 0.0) if not R.interior else 0.0
    if R.district in ('underline', 'warehouse'):
        wet = 0.0
    wmask = np.zeros((Ht, Wt), np.float32)
    if wet > 0:
        wn = value_noise(Wt, Ht, 30 * D, seed + 5, 2)
        wmask[Bt:] = 0.6 + 0.4 * np.clip((wn[Bt:] - 0.3) * 2, 0, 1)
    for (x0, y0, m) in R.puddles:
        h, w = m.shape
        sx0, sy0 = max(0, x0), max(0, y0)
        sx1, sy1 = min(Wt, x0 + w), min(Ht, y0 + h)
        if sx1 > sx0 and sy1 > sy0:
            wmask[sy0:sy1, sx0:sx1] = np.maximum(wmask[sy0:sy1, sx0:sx1],
                                                 2.0 * m[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0])
    if wmask.max() > 0:
        Hg = Ht - Bt
        d = (np.arange(Hg, dtype=np.float32) + 0.5) / D
        acc = np.zeros((Hg, Wt, 3), np.float32)
        for (ya, yb, Ls, gain) in ((B - 60, B, 100.0, 0.55), (B - 150, B - 60, 150.0, 0.9), (0, B - 150, 200.0, 1.2)):
            a_, b_ = max(0, int(ya * D)), max(0, int(yb * D))
            if b_ <= a_:
                continue
            colr = E[a_:b_].mean(0) * gain
            colr = _blur_axis(colr, 2.2 * D, 0)
            prof = np.exp(-d / (Ls * 0.55)) * np.clip(d / 3.0, 0, 1)
            acc += prof[:, None, None] * colr[None, :, :]
        for g in R.glows:
            if g.get('front') or g['y'] >= B - 2:
                continue
            Ls = (B - g['y']) * 0.9 + 40
            sig = max(3.0, g['r'] * 0.12)
            gx_ = np.exp(-((xs - g['x']) / sig) ** 2)
            prof = np.exp(-d / (Ls * 0.55)) * np.clip(d / 3.0, 0, 1)
            acc += (prof[:, None] * gx_[None, :])[..., None] * (_tint(g['color']) * 0.35 * float(g['energy']))
        for (hx, hy, gy_, col) in getattr(R, 'lamps', []):
            gx_ = np.exp(-((xs - hx) / 5.0) ** 2)
            dd = ys[Bt:] - gy_
            prof = np.exp(-np.clip(dd, 0, None) / 70.0) * np.clip(dd / 2.0, 0, 1)
            acc += (prof[:, None] * gx_[None, :])[..., None] * (_tint(col) * 0.9)
        acc = np.minimum(acc, 0.6)
        nb = _aniso_noise(Wt, Hg, 3.2 * D, 22 * D, seed + 6)
        streak = np.clip(0.5 + 0.9 * (nb - 0.45), 0.25, 1)
        rip = (0.88 + 0.12 * np.sin(d * 1.6 + np.sin(d * 0.41) * 2.0))[:, None]
        inband = (((Bt + np.arange(Hg) + 0.5) / D) >= walk0).astype(np.float32)[:, None]
        amt = max(wet, 0.35)
        k = amt * streak * rip * wmask[Bt:] * alpha[Bt:] * ne[Bt:] * (1 - 0.15 * inband)
        px[Bt:, :, :3] += acc * k[..., None]
    if wet > 0:
        skyc = C(kit.LIGHT.get('sky', '#8a9aa8'))
        for _ in range(int(R.W / 40)):
            sx, sy = rs.uniform(0, R.W), rs.uniform(B + 8, CURB_Y - 3)
            ln = rs.uniform(6, 26)
            inb = walk0 <= sy <= walk1
            cv.rect(sx, sy, ln, 0.5, mix(skyc, C('#ffffff'), 0.5), a=(0.09 if inb else 0.14) * (wet / 0.3),
                    mode='add')

    # --- sparse weeds in the crack between wall and pavement
    if not R.interior and R.district in WEEDY and R.id not in NO_SKY:
        wr = rng_of('weeds', R.id)
        doors = [d_['x'] for d_ in R.data.get('doors', [])]
        props = [p['x'] for p in R.data.get('props', [])]
        x = wr.uniform(10, 50)
        while x < R.W - 10:
            if all(abs(x - d_) > 16 for d_ in doors) and all(abs(x - p) > 10 for p in props) and \
                    not any(a0 - 4 <= x <= a1 + 4 for a0, a1 in wcols):
                yy_ = B + 0.6
                if alpha[min(Ht - 1, int(yy_ * D)), min(Wt - 1, int(x * D))] > 0.9:
                    roommod.weeds(R, x, yy_, wr.randint(2, 4), seed=int(x * 7), col='#566e38')
            x += wr.uniform(40, 120)
        x = wr.uniform(30, 90)
        while x < R.W - 10:
            if not any(a0 - 4 <= x <= a1 + 4 for a0, a1 in wcols):
                roommod.weeds(R, x, CURB_Y + 0.4, wr.randint(1, 3), seed=int(x * 11 + 3), col='#4e6634')
            x += wr.uniform(90, 220)

    # --- large glass stays at or below ~0.8 value (the engine blooms > 0.7); small sources keep their punch
    v = px[..., :3].max(axis=2)
    brt = em * np.clip((px[..., :3].min(axis=2) - 0.55) / 0.2, 0, 1)      # near-white glass, not coloured light
    A = blur(brt, 4 * D, passes=2)
    cap = 0.8 + 0.2 * np.clip((0.65 - A) / 0.4, 0, 1)
    knee = cap - 0.08
    v2 = np.where(v > knee, knee + (v - knee) * (cap - knee) / np.maximum(1.0 - knee, 1e-3), v)
    sc = np.where(v > 1e-4, v2 / np.maximum(v, 1e-4), 1.0)
    sc = 1 + (sc - 1) * np.clip(em * 1.5, 0, 1)
    px[..., :3] *= sc[..., None]


# ----------------------------------------------------------------------------- district layers
def _gauss1d(a, sigma, axis, wrap):
    r = int(math.ceil(sigma * 3))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2).astype(np.float32)
    k /= k.sum()
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    p = np.pad(a, pad, mode='wrap' if wrap else 'edge')
    out = np.zeros_like(a)
    n = a.shape[axis]
    for i, kv in enumerate(k):
        out += kv * np.take(p, np.arange(i, i + n), axis=axis)
    return out


def atmos(img, haze, amount, desat, sigma=0.0, lift_ink=0.0, soften=0.0):
    """Atmospheric perspective for a repeating parallax layer (straight-alpha PIL image -> new image): lift dark
    outlines toward the local colour, defocus with a Gaussian of `sigma` tx (wrapping horizontally so the tile
    stays seamless), desaturate and blend toward the haze colour."""
    from PIL import Image
    a = np.asarray(img.convert('RGBA'), np.float32) / 255.0
    rgb = a[..., :3]
    al = a[..., 3:4]
    if lift_ink > 0:
        pm = rgb * al
        bp = blur(pm, 1.0, passes=1)
        ba = blur(al[..., 0], 1.0, passes=1)[..., None]
        loc = np.where(ba > 1e-3, bp / np.maximum(ba, 1e-3), rgb)
        lum = rgb.mean(axis=2, keepdims=True)
        llum = loc.mean(axis=2, keepdims=True)
        ink = np.clip((llum - lum - 0.04) * 6, 0, 1)
        rgb = rgb + (loc - rgb) * ink * lift_ink
    if sigma > 0.05:
        pm = np.concatenate([rgb * al, al], axis=2)
        pm = _gauss1d(pm, sigma, 1, True)
        pm = _gauss1d(pm, sigma, 0, False)
        al = pm[..., 3:4]
        rgb = np.where(al > 1e-4, pm[..., :3] / np.maximum(al, 1e-4), 0)
    hz = np.array(C(haze)[:3], np.float32) / 255.0
    lum = (rgb * np.array([0.3, 0.59, 0.11], np.float32)).sum(axis=2, keepdims=True)
    rgb = rgb + (lum - rgb) * desat
    rgb = rgb * (1 - amount) + hz * amount
    out = np.concatenate([np.clip(rgb, 0, 1), np.clip(al, 0, 1)], axis=2)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')
