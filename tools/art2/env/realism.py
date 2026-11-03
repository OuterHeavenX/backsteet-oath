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
WET = {'floodgate': 0.34, 'neon_mile': 0.26, 'underline': 0.12, 'warehouse': 0.06}
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
    check_windows(R)
    apply_shadows(R)

    # --- material micro-texture: multiplicative, low contrast, calmer in the walk band
    n2 = value_noise(Wt, Ht, 6.0 * D, seed + 1, 2)
    n3 = value_noise(Wt, Ht, 24.0 * D, seed + 2, 2)
    mod = (n2 - 0.5) * 0.015 + (n3 - 0.5) * 0.05
    walk0, walk1 = R.walk
    band = ((ys >= walk0 - 2) & (ys <= walk1 + 2)).astype(np.float32)[:, None]
    k = (1 - 0.68 * band) * (1 - em)
    px[..., :3] *= (1 + mod * k)[..., None]

    # --- grime gradient over the bottom 20 u of the walls + contact AO on both sides of the base line
    g0 = B - 20
    t = np.clip((ys - g0) / 20.0, 0, 1) * (ys < B)
    grime = (t ** 1.5)[:, None] * (0.13 + 0.12 * n2) + (np.clip(1 - (B - ys) / 3.0, 0, 1) * (ys < B))[:, None] * 0.12
    below = (np.clip(1 - (ys - B) / 5.0, 0, 1) * (ys >= B))[:, None] * 0.09
    px[..., :3] *= (1 - (grime + below) * (1 - em))[..., None]

    # --- inner-corner AO where two buildings meet (vertical soft seams)
    if not R.interior:
        edges = set()
        for f in R.data.get('facades', []):
            edges.add(round(f['x'], 1))
            edges.add(round(f['x'] + f['w'], 1))
        edges = [e for e in edges if 2 < e < R.W - 2]
        if edges:
            prof = np.zeros(Wt, np.float32)
            for e in edges:
                prof = np.maximum(prof, np.exp(-np.abs(xs - e) / 3.0))
            wall = (ys < B)[:, None] * (alpha > 0.5)
            px[..., :3] *= (1 - 0.2 * prof[None, :] * wall * (1 - em))[..., None]
    else:
        # interior: soft occlusion toward the side walls and in the wall/ceiling corner
        side = np.exp(-xs / 26.0) + np.exp(-(R.W - xs) / 26.0)
        wallm = (ys < B)[:, None].astype(np.float32)
        px[..., :3] *= (1 - 0.16 * np.clip(side, 0, 1)[None, :] * wallm * (1 - em))[..., None]

    # --- baked light from emissive texels: sidewalk/floor spill + bounce halo on nearby surfaces
    E = px[..., :3] * em[..., None]
    span = 150 if R.interior else 90
    s0 = max(0, int((B - span) * D))
    src = E[s0:Bt]
    if src.shape[0] > 0:
        wgt = np.linspace(0.35, 1.0, src.shape[0], dtype=np.float32)[:, None, None]
        S = (src * wgt).sum(0) / max(1, src.shape[0])
        S_near = _blur_axis(S, 4 * D, 0)
        S_far = _blur_axis(S, 16 * D, 0)
        L = 60.0 if R.interior else 46.0
        g_rows = np.arange(Bt, min(Ht, int((B + L) * D)))
        if len(g_rows):
            tt = ((g_rows + 0.5) / D - B) / L
            f = ((1 - tt) ** 2) * np.clip(((g_rows + 0.5) / D - B) / 1.5, 0, 1)
            ks = 0.5 if R.interior else 0.66
            for i, r in enumerate(g_rows):
                Sy = S_near * (1 - tt[i]) + S_far * tt[i]
                px[r, :, :3] += ks * f[i] * Sy * alpha[r][:, None] * (1 - em[r])[:, None]
            # matching lightmap sources so actors standing in the spill are lit by it too
            step = 32
            for xu in range(16, R.W, step):
                c = S_far[min(Wt - 1, int(xu * D))]
                lum = float(c.mean())
                if lum > 0.05:
                    col = np.clip(c / max(1e-3, c.max()), 0, 1)
                    R.light(xu, B + 12, 34, 22, (int(col[0] * 255), int(col[1] * 255), int(col[2] * 255), 255),
                            min(0.10, lum * 0.35))
    G = blur(E, 7 * D, passes=2)
    sh = int(3 * D)
    G[sh:] = G[:-sh].copy()
    G[:sh] = 0
    px[..., :3] += 0.15 * G * (alpha * (1 - em))[..., None]

    # --- faint baked pools consistent with the engine glows (the engine adds the bright part)
    for g in list(R.glows):
        if g.get('front'):
            continue
        gx, gy, r = g['x'], g['y'], g['r']
        col = C(g['color'])
        en = float(g.get('energy', 0.5))
        if gy < B - 2:
            cv.radial(gx, gy + r * 0.15, r * 0.85, r * 0.95, col, a=0.06 * en, mode='add', falloff=1.8)
            if gy > B - 140:
                cv.radial(gx, B + 9, r * 0.75, max(4.0, r * 0.2), col, a=0.09 * en, mode='add', falloff=1.6)

    # --- wet ground: mirrored vertical smears of signs and lights + specular streaks
    wet = WET.get(R.district, 0.0) if not R.interior else 0.0
    wmask = np.zeros((Ht, Wt), np.float32)
    if wet > 0:
        wn = value_noise(Wt, Ht, 30 * D, seed + 5, 2)
        wmask[Bt:] = (0.55 + 0.45 * np.clip((wn[Bt:] - 0.3) * 2, 0, 1))
    for (x0, y0, m) in R.puddles:
        h, w = m.shape
        sx0, sy0 = max(0, x0), max(0, y0)
        sx1, sy1 = min(Wt, x0 + w), min(Ht, y0 + h)
        if sx1 > sx0 and sy1 > sy0:
            wmask[sy0:sy1, sx0:sx1] = np.maximum(wmask[sy0:sy1, sx0:sx1],
                                                 1.7 * m[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0])
    if wmask.max() > 0:
        lum = px[..., :3].mean(axis=2)
        bright = np.clip((lum - 0.62) / 0.3, 0, 1) * alpha * 0.55
        srcw = px[:Bt, :, :3] * np.maximum(em[:Bt], bright[:Bt])[..., None]
        Hg = min(Ht - Bt, Bt)
        idx = Bt - 1 - (np.arange(Hg) * 0.9).astype(np.int64)
        idx = np.clip(idx, 0, Bt - 1)
        Rf = srcw[idx]
        Rf = _blur_axis(Rf, 7 * D, 0)
        Rf = _blur_axis(Rf, 1.2 * D, 1)
        sn = value_noise(Wt, 1, 1.6 * D, seed + 6, 1)[0]
        sn2 = value_noise(Wt, 1, 7.0 * D, seed + 7, 1)[0]
        streak = np.clip(0.15 + 1.1 * (sn - 0.35) + 0.5 * (sn2 - 0.5), 0, 1)
        d = (np.arange(Hg) + 0.5) / D
        fall = np.clip(1 - d / 78.0, 0, 1) ** 1.8
        # ripple breaks: thin horizontal gaps so the smear reads as wet tarmac, not a painted block
        rip = 0.75 + 0.25 * np.sin(d * 2.1 + np.sin(d * 0.37) * 2.0)
        fall = fall * rip
        amt = max(wet, 0.30)
        reg = px[Bt:Bt + Hg, :, :3]
        inband = ((Bt + np.arange(Hg) + 0.5) / D >= walk0).astype(np.float32)[:, None]
        k = (amt * fall[:, None] * streak[None, :] * wmask[Bt:Bt + Hg] * alpha[Bt:Bt + Hg] * (1 - em[Bt:Bt + Hg])
             * (1 - 0.3 * inband))
        Rf = np.minimum(Rf, 0.85)
        reg += Rf * k[..., None]
        px[Bt:Bt + Hg, :, :3] = reg
    if wet > 0:
        rs = rng_of('spec', R.id)
        skyc = C(kit.LIGHT.get('sky', '#8a9aa8'))
        for _ in range(int(R.W / 40)):
            sx, sy = rs.uniform(0, R.W), rs.uniform(B + 8, CURB_Y - 3)
            ln = rs.uniform(6, 26)
            inband = walk0 <= sy <= walk1
            cv.rect(sx, sy, ln, 0.5, mix(skyc, C('#ffffff'), 0.5), a=(0.09 if inband else 0.14) * (wet / 0.3),
                    mode='add')

    # --- sparse weeds in the crack between wall and pavement
    if not R.interior and R.district in WEEDY and R.id not in NO_SKY:
        rs = rng_of('weeds', R.id)
        doors = [d['x'] for d in R.data.get('doors', [])]
        props = [p['x'] for p in R.data.get('props', [])]
        x = rs.uniform(10, 50)
        while x < R.W - 10:
            if all(abs(x - d) > 16 for d in doors) and all(abs(x - p) > 10 for p in props):
                yy = B + 0.6
                if alpha[min(Ht - 1, int(yy * D)), min(Wt - 1, int(x * D))] > 0.9:
                    roommod.weeds(R, x, yy, rs.randint(2, 4), seed=int(x * 7), col='#566e38')
            x += rs.uniform(40, 120)
        x = rs.uniform(30, 90)
        while x < R.W - 10:
            roommod.weeds(R, x, CURB_Y + 0.4, rs.randint(1, 3), seed=int(x * 11 + 3), col='#4e6634')
            x += rs.uniform(90, 220)


# ----------------------------------------------------------------------------- district layers
def atmos(img, haze, amount, desat, soften=0.0, lift_ink=0.0):
    """Atmospheric perspective for a parallax layer (straight-alpha PIL image -> new image): blend toward the
    haze colour, desaturate, optionally soften and lift dark outlines toward the local colour."""
    from PIL import Image
    a = np.asarray(img.convert('RGBA'), np.float32) / 255.0
    rgb = a[..., :3]
    al = a[..., 3:4]
    if soften > 0 or lift_ink > 0:
        pm = rgb * al
        bp = blur(pm, 1.0, passes=1)
        ba = blur(al[..., 0], 1.0, passes=1)[..., None]
        loc = np.where(ba > 1e-3, bp / np.maximum(ba, 1e-3), rgb)
        if lift_ink > 0:
            lum = rgb.mean(axis=2, keepdims=True)
            llum = loc.mean(axis=2, keepdims=True)
            ink = np.clip((llum - lum - 0.04) * 6, 0, 1)
            rgb = rgb + (loc - rgb) * ink * lift_ink
        if soften > 0:
            rgb = rgb * (1 - soften) + loc * soften
    hz = np.array(C(haze)[:3], np.float32) / 255.0
    lum = (rgb * np.array([0.3, 0.59, 0.11], np.float32)).sum(axis=2, keepdims=True)
    rgb = rgb + (lum - rgb) * desat
    rgb = rgb * (1 - amount) + hz * amount
    out = np.concatenate([np.clip(rgb, 0, 1), al], axis=2)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')
