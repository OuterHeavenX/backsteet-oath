#!/usr/bin/env python3
"""BACKSTREET OATH -- v2 character generator (density 2, packed atlases).

Deterministic, offline: Python 3 + Pillow + numpy. Character identities come
from the v1 spec tables (tools/art/gen_characters.py); bodies, poses, faces and
rendering are new (see docs/assets/CHARACTERS_V2.md and
docs/visual/ASSET_CONTRACT_V2.md section 1).

Usage:
  python3 tools/art2/chars/gen_chars2.py --only nico,duke [--preview DIR] [--jobs 4]
  python3 tools/art2/chars/gen_chars2.py --benchmark
  python3 tools/art2/chars/gen_chars2.py --all
  python3 tools/art2/chars/gen_chars2.py --portraits nico,dot   (portraits only)
"""
import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np                       # noqa: E402
from PIL import Image                    # noqa: E402

from raster import Canvas                # noqa: E402
from rig import body_for, solve, NORMAL  # noqa: E402
from draw import Frame, Look, V1         # noqa: E402
import poses                             # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT_SPR = os.path.join(ROOT, 'game', 'assets', 'sprites', 'chars')
OUT_POR = os.path.join(ROOT, 'game', 'assets', 'portraits2')
DEN = 2
PAD = 8                    # transparent padding between packed rects and to the atlas edge (>= 6 tx)

BENCHMARK = ['nico', 'dogs_brawler', 'dogs_flanker', 'duke', 'dot', 'towna', 'townd']
BENCH_PORTRAITS = ['nico', 'dot', 'duke', 'dogs_weapon']

# v2 spec extensions (bosses read bigger; everything else inherits v1 identity)
EXT = {
    'duke': dict(boss_scale=1.06),
    'otto': dict(boss_scale=1.04),
    'rook': dict(boss_scale=1.03),
    'rook_p2': dict(boss_scale=1.03),
}

FIGHTER_ORDER = ['idle', 'walk', 'run', 'jump', 'land', 'punch_a', 'punch_b', 'punch_c', 'kick', 'kick_c',
                 'jump_kick', 'jump_punch', 'run_punch', 'dropkick', 'guard', 'hurt_high', 'hurt_low', 'hurt_back',
                 'knockdown', 'getup', 'dizzy', 'pickup', 'carry', 'carry_walk', 'throw', 'swing', 'sweep',
                 'rising_kick', 'slam', 'victory', 'talk', 'cower']

SPRINGS = {           # k, damping, gain, clamp (u)
    'hair': (0.34, 0.52, 1.7, 5.0),
    'tails': (0.16, 0.30, 1.0, 9.0),
    'hem': (0.28, 0.48, 1.0, 4.0),
    'chain': (0.20, 0.36, 1.0, 4.0),
}


def spec_for(cid):
    s = dict(V1.CHAR_BY_ID[cid])
    s.update(EXT.get(cid, {}))
    return s


def anims_for(spec):
    return poses.civilian_anims() if spec.get('civilian') else poses.fighter_anims()


# ----------------------------------------------------------------------------- secondary motion

def secondary(A, solved, leg_r):
    """Spring-lagged drag vectors per frame for hair / tails / hem / chain."""
    n = len(solved)
    vel = A.get('vel') or [(0.0, 0.0)] * n
    loop = A.get('loop', False)
    out = [dict() for _ in range(n)]
    for key, (k, d, gain, clamp) in SPRINGS.items():
        # driver: head for hair/tails, hip for hem/chain
        travel = [0.0, 0.0]
        targets = []
        cycles = 3 if loop else 1
        for c in range(cycles):
            for i in range(n):
                s = solved[i]
                travel[0] += vel[i][0] * leg_r
                travel[1] += vel[i][1] * leg_r
                p = s.head_c if key in ('hair', 'tails') else s.hip
                targets.append((p[0] + travel[0], p[1] + travel[1], i, c))
        x = [targets[0][0], targets[0][1]]
        v = [0.0, 0.0]
        for (tx, ty, i, c) in targets:
            for _ in range(2):                    # two sub-steps per frame
                ax = k * (tx - x[0]) - d * v[0]
                ay = k * (ty - x[1]) - d * v[1]
                v[0] += ax
                v[1] += ay
                x[0] += v[0]
                x[1] += v[1]
            if c == cycles - 1:
                dx, dy = (x[0] - tx) * gain, (x[1] - ty) * gain
                L = math.hypot(dx, dy)
                if L > clamp:
                    dx, dy = dx * clamp / L, dy * clamp / L
                out[i][key] = (dx, dy)
    return out


# ----------------------------------------------------------------------------- rendering

def canvas_bounds(b):
    h = b['stand_hip'] + b['torso'] + b['neck'] + b['R'] * 2.2
    s = h / 48.0
    return (-46 * s, -70 * s, 46 * s, 6 * s)


def pose_bounds(s, b):
    """Tight world-unit canvas bounds for a solved pose (aligned to the texel grid)."""
    R = b['R']
    pts = [s.hip, s.neck_base, s.sh_n, s.sh_f, s.elb_n, s.elb_f, s.wr_n, s.wr_f, s.fist_n, s.fist_f,
           s.knee_n, s.knee_f, s.ank_n, s.ank_f, s.hj_n, s.hj_f]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    hx, hy = s.head_c
    xs += [hx - R * 2.6, hx + R * 1.8]
    ys += [hy - R * 2.7, hy + R * 1.6]
    m = 7.0 * max(1.0, b['w'])
    x0 = math.floor((min(xs) - m) * 2) / 2.0
    x1 = math.ceil((max(xs) + m) * 2) / 2.0
    y0 = math.floor((min(ys) - m) * 2) / 2.0
    y1 = math.ceil((max(max(ys), 0.0) + 4.0) * 2) / 2.0
    return x0, y0, x1, y1


def render_frame(args):
    cid, name, idx = args
    spec = spec_for(cid)
    b = body_for(spec)
    look = Look(spec)
    A = anims_for(spec)[name]
    leg_r = b['stand_hip'] / (NORMAL['thigh'] + NORMAL['shin'] + NORMAL['ankle'])
    solved = [solve(p, b) for p in A['frames']]
    sec = secondary(A, solved, leg_r)
    s = solved[idx]
    x0, y0, x1, y1 = pose_bounds(s, b)
    cv = Canvas(x0, y0, x1, y1, den=DEN)
    Frame(cv, look, s, sec[idx]).render()
    cv.finish()
    img = cv.downsample()
    ox, oy = cv.origin_tx()
    a = np.asarray(img)[..., 3]
    ys, xs = np.nonzero(a > 0)
    if xs.min() <= 0 or ys.min() <= 0 or xs.max() >= img.width - 1:
        print('WARNING clipped frame', cid, name, idx, file=sys.stderr)
    x_0, x_1 = max(xs.min() - 1, 0), min(xs.max() + 2, img.width)
    y_0, y_1 = max(ys.min() - 1, 0), min(ys.max() + 2, img.height)
    crop = img.crop((x_0, y_0, x_1, y_1))
    p = s.pose
    hand = [round(s.fist_n[0] * DEN, 1), round(s.fist_n[1] * DEN, 1), round(float(p['wang']), 1),
            0 if p['near_arm_back'] else 1]
    head = [round(s.head_c[0] * DEN, 1), round(s.head_c[1] * DEN, 1)]
    meta = dict(ox=int(x_0 - round(ox)), oy=int(y_0 - round(oy)), hand=hand, head=head,
                feet=[(s.ank_n[0], s.ank_n[1]), (s.ank_f[0], s.ank_f[1])], lift=(p['lift_n'] or p['fn'][1] < -0.6,
                                                                                   p['lift_f'] or p['ff'][1] < -0.6))
    return (name, idx, crop.tobytes(), crop.size, meta)


def pack(sizes, width):
    """Shelf packer with PAD spacing. Returns positions and atlas height."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    pos = [None] * len(sizes)
    x, y, shelf_h = PAD, PAD, 0
    for i in order:
        w, h = sizes[i]
        if x + w + PAD > width:
            x = PAD
            y += shelf_h + PAD
            shelf_h = 0
        pos[i] = (x, y)
        x += w + PAD
        shelf_h = max(shelf_h, h)
    return pos, y + shelf_h + PAD


def build_character(cid, pool, preview=None):
    t0 = time.time()
    spec = spec_for(cid)
    b = body_for(spec)
    A = anims_for(spec)
    civ = bool(spec.get('civilian'))
    names = [n for n in FIGHTER_ORDER if n in A]
    jobs = [(cid, n, i) for n in names for i in range(len(A[n]['frames']))]
    results = pool.map(render_frame, jobs, chunksize=2)
    frames, metas, anim_frames = [], [], {n: [] for n in names}
    for (name, idx, data, size, meta) in results:
        img = Image.frombytes('RGBA', size, data)
        anim_frames[name].append(len(frames))
        frames.append(img)
        metas.append(meta)
    sizes = [f.size for f in frames]
    width = 1024
    pos, H = pack(sizes, width)
    if H > 2048:
        width = 2048
        pos, H = pack(sizes, width)
    H = int(math.ceil(H / 8.0) * 8)
    atlas = Image.new('RGBA', (width, H), (0, 0, 0, 0))
    for f, p in zip(frames, pos):
        atlas.alpha_composite(f, p)
    leg_r = b['stand_hip'] / (NORMAL['thigh'] + NORMAL['shin'] + NORMAL['ankle'])
    anims = {}
    for n in names:
        a = A[n]
        e = {'frames': anim_frames[n], 'fps': a.get('fps', 12), 'loop': bool(a.get('loop', False))}
        if 'stride' in a:
            e['stride'] = round(a['stride'] * leg_r, 2)
        if 'contact' in a:
            e['contact'] = a['contact']
        anims[n] = e
    if civ:
        # civilians never attack: alias attack keys to the talk gesture (contact on the gesture frame)
        for k in poses.ALIAS_ATTACKS:
            if k not in anims:
                anims[k] = {'frames': anims['talk']['frames'][:3], 'fps': 10, 'loop': False, 'contact': 1}
    # v1 compatibility alias
    anims['hurt'] = dict(anims['hurt_high'])
    # standing crown height incl. hair: top of the relaxed 'talk' frame (trim margin is 1 tx)
    height = int(-metas[anim_frames['talk'][0]]['oy'] - 1)
    js = {
        'id': cid, 'version': 2, 'density': DEN, 'height': height,
        'frames': [[p[0], p[1], f.size[0], f.size[1], m['ox'], m['oy']] for f, p, m in zip(frames, pos, metas)],
        'hand': [m['hand'] for m in metas],
        'head': [m['head'] for m in metas],
        'anims': anims,
    }
    os.makedirs(OUT_SPR, exist_ok=True)
    atlas.save(os.path.join(OUT_SPR, cid + '.png'), optimize=True)
    with open(os.path.join(OUT_SPR, cid + '.json'), 'w') as fh:
        json.dump(js, fh, separators=(',', ':'))
    # numeric foot-plant check
    drift = foot_drift(A, metas, anim_frames, leg_r)
    dt = time.time() - t0
    print('%-14s %3d frames  atlas %dx%d  %.1fs  drift(tx) %s' % (cid, len(frames), width, H, dt,
                                                                   ' '.join('%s=%.2f' % kv for kv in drift.items())))
    if preview:
        make_previews(cid, frames, metas, anim_frames, anims, preview)
    return js


def foot_drift(A, metas, anim_frames, leg_r):
    """Max world-x drift (tx) of a planted foot across consecutive planted frames."""
    out = {}
    for n in ('walk', 'run', 'carry_walk'):
        if n not in anim_frames:
            continue
        idxs = anim_frames[n]
        stride = A[n]['stride'] * leg_r
        k = len(idxs)
        worst = 0.0
        for side in (0, 1):
            for i in range(k):
                j = (i + 1) % k
                mi, mj = metas[idxs[i]], metas[idxs[j]]
                if mi['lift'][side] or mj['lift'][side]:
                    continue
                xi = mi['feet'][side][0] + i * stride / k
                xj = mj['feet'][side][0] + (i + 1) * stride / k
                worst = max(worst, abs(xj - xi) * DEN)
        out[n] = worst
    return out


# ----------------------------------------------------------------------------- previews

def make_previews(cid, frames, metas, anim_frames, anims, outdir):
    os.makedirs(outdir, exist_ok=True)
    z = 2
    cellw = max(f.size[0] for f in frames) + 8
    cellh = max(f.size[1] for f in frames) + 8
    # contact sheet: one row per anim, frames placed by anchor on a ground line
    names = [n for n in FIGHTER_ORDER if n in anim_frames]
    maxn = max(len(anim_frames[n]) for n in names)
    cw, ch = 120, 150
    sheet = Image.new('RGBA', (cw * maxn + 90, ch * len(names)), (104, 106, 116, 255))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    for r, n in enumerate(names):
        dr.text((4, r * ch + 4), n, fill=(255, 255, 255, 255))
        gy = r * ch + 128
        dr.line([(90, gy), (sheet.width, gy)], fill=(80, 82, 90, 255))
        for c, fi in enumerate(anim_frames[n]):
            f, m = frames[fi], metas[fi]
            ax = 90 + c * cw + cw // 2
            sheet.alpha_composite(f, (ax + m['ox'], gy + m['oy']))
            if anims[n].get('contact') == c:
                dr.rectangle([90 + c * cw + 2, r * ch + 2, 90 + (c + 1) * cw - 2, r * ch + ch - 2], outline=(255, 200, 60, 255))
    sheet.save(os.path.join(outdir, '%s_sheet.png' % cid))
    # animated GIFs per anim (2x, grey + dark panels)
    for n in names:
        idxs = anim_frames[n]
        W, H = 200, 150
        imgs = []
        dur = int(1000 / max(anims[n].get('fps', 12), 1))
        for fi in idxs:
            f, m = frames[fi], metas[fi]
            pan = Image.new('RGBA', (W * 2, H), (110, 112, 122, 255))
            pan.paste((28, 26, 36, 255), (W, 0, W * 2, H))
            for k in range(2):
                pan.alpha_composite(f, (k * W + W // 2 + m['ox'], 130 + m['oy']))
            imgs.append(pan.resize((W * 2 * z, H * z), Image.NEAREST).convert('P', palette=Image.ADAPTIVE))
        imgs[0].save(os.path.join(outdir, '%s_%s.gif' % (cid, n)), save_all=True, append_images=imgs[1:],
                     duration=dur, loop=0)


# ----------------------------------------------------------------------------- portraits

PEXPR = ['neutral', 'happy', 'angry', 'surprised', 'sad']


def render_portrait(cid):
    import portrait
    return portrait.render(spec_for(cid), PEXPR)


def build_portraits(ids):
    os.makedirs(OUT_POR, exist_ok=True)
    import portrait
    for cid in ids:
        strip = portrait.render(spec_for(cid), PEXPR)
        strip.save(os.path.join(OUT_POR, cid + '.png'), optimize=True)
        print('portrait', cid, strip.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--benchmark', action='store_true')
    ap.add_argument('--portraits', default=None)
    ap.add_argument('--no-portraits', action='store_true')
    ap.add_argument('--preview', default=None)
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    if a.all:
        ids = [c['id'] for c in V1.ALL_CHARS]
        pids = list(V1.PORTRAIT_IDS) + list(V1.GANG_PORTRAIT.values())
    elif a.benchmark:
        ids, pids = BENCHMARK, BENCH_PORTRAITS
    else:
        ids = [x for x in a.only.split(',') if x]
        pids = []
    if a.portraits is not None:
        pids = [x for x in a.portraits.split(',') if x]
        ids = [] if not a.only else ids
    with Pool(a.jobs) as pool:
        for cid in ids:
            build_character(cid, pool, a.preview)
    if pids and not a.no_portraits:
        build_portraits(pids)


if __name__ == '__main__':
    main()
