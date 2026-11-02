#!/usr/bin/env python3
"""Validate v2 character atlases against docs/visual/ASSET_CONTRACT_V2.md section 1."""
import json, os, sys
from PIL import Image
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'game', 'assets', 'sprites', 'chars')
MIN = dict(idle=6, walk=8, run=8, jump=3, land=2, punch_a=4, punch_b=4, punch_c=6, kick=5, kick_c=6, jump_kick=2,
           jump_punch=2, run_punch=3, dropkick=3, guard=2, hurt_high=3, hurt_low=3, hurt_back=3, knockdown=5,
           getup=4, dizzy=4, pickup=3, carry=2, carry_walk=6, throw=4, swing=5, sweep=4, rising_kick=4, slam=3,
           victory=4, talk=4, cower=3)
CIV = ['idle', 'walk', 'run', 'talk', 'cower', 'victory']
ATTACKS = ['punch_a', 'punch_b', 'punch_c', 'kick', 'kick_c', 'jump_kick', 'jump_punch', 'run_punch', 'dropkick',
           'throw', 'swing', 'sweep', 'rising_kick', 'slam']
V1D = os.path.join(D, '..', 'characters')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
bad = 0
ids = sys.argv[1:] or sorted(f[:-5] for f in os.listdir(D) if f.endswith('.json'))
RANGES = {'normal': (92, 100), 'slim': (92, 100), 'tall': (96, 108), 'heavy': (104, 116), 'big': (104, 120),
          'kid': (76, 84), 'elder': (84, 100)}


def body_height(cid):
    """Crown height without hair (tx) in the relaxed stance, from the rig."""
    import gen_chars2 as g
    from rig import body_for, solve
    from poses import Rx
    sp = g.spec_for(cid)
    b = body_for(sp)
    s = solve(Rx(), b)
    return int(round((-s.head_c[1] + b['R'] * 1.0) * 2)), sp.get('body', 'normal')
for cid in ids:
    js = json.load(open(os.path.join(D, cid + '.json')))
    im = Image.open(os.path.join(D, cid + '.png'))
    errs = []
    W, H = im.size
    if W > 2048 or H > 2048:
        errs.append('atlas too big %dx%d' % (W, H))
    n = len(js['frames'])
    if len(js['hand']) != n or len(js['head']) != n:
        errs.append('hand/head length')
    rects = [f[:4] for f in js['frames']]
    for i, (x, y, w, h) in enumerate(rects):
        if x < 6 or y < 6 or x + w > W - 6 or y + h > H - 6:
            errs.append('edge pad frame %d' % i)
    for i in range(n):
        xi, yi, wi, hi = rects[i]
        for j in range(i + 1, n):
            xj, yj, wj, hj = rects[j]
            if xi < xj + wj + 6 and xj < xi + wi + 6 and yi < yj + hj + 6 and yj < yi + hi + 6:
                errs.append('pad %d/%d' % (i, j))
    a = js['anims']
    v1 = json.load(open(os.path.join(V1D, cid + '.json')))
    for k in v1['anims']:
        if k not in a:
            errs.append('missing v1 key ' + k)
    if cid == 'biscuit':
        print('%-14s %3d frames %4dx%-4d height %3d %s' % (cid, n, W, H, js['height'], 'OK' if not errs else 'FAIL ' + '; '.join(errs[:6])))
        bad += bool(errs)
        continue
    bh, bt = body_height(cid)
    lo, hi = RANGES.get(bt, (92, 100))
    if not (lo - 2 <= bh <= hi + 2):
        errs.append('body height %d outside %s %d-%d' % (bh, bt, lo, hi))
    civ = 'punch_a' in a and a['punch_a']['frames'] == a['talk']['frames'][:3]
    for k, m in MIN.items():
        if k not in a:
            errs.append('missing ' + k)
            continue
        if not civ or k in CIV:
            if len(a[k]['frames']) < m and not (civ and k in ATTACKS):
                errs.append('%s has %d < %d' % (k, len(a[k]['frames']), m))
        if k in ATTACKS:
            c = a[k].get('contact')
            if c is None or not (1 <= c < len(a[k]['frames'])):
                errs.append('bad contact ' + k)
    for k in ('walk', 'run', 'carry_walk'):
        if 'stride' not in a.get(k, {}):
            errs.append('no stride ' + k)
    print('%-14s %3d frames %4dx%-4d height %3d (body %3d %s) %s' % (cid, n, W, H, js['height'], bh, bt,
          'OK' if not errs else 'FAIL ' + '; '.join(errs[:6])))
    bad += bool(errs)
sys.exit(1 if bad else 0)
