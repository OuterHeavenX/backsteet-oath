#!/usr/bin/env python3
"""Generate BACKSTREET OATH item, icon, FX, pickup and UI art.

    python3 tools/art/gen_items_ui.py [--preview DIR] [--only weapons,icons,fx,pickups,ui,logo]

All art is original and procedurally drawn (deterministic; fixed seeds only).
Outputs under game/assets/{weapons,icons,fx,pickups,ui}/ plus JSON sidecars.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pixlib import contact_sheet  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ASSETS = os.path.join(ROOT, 'game', 'assets')


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')


def gen_weapons(preview):
    import items_weapons as W
    out = {}
    items = []
    for wid in W.WEAPON_IDS:
        c, grip, tip = W.WEAPONS[wid]()
        c.save(os.path.join(ASSETS, 'weapons', wid + '.png'))
        out[wid] = {'file': 'res://assets/weapons/%s.png' % wid,
                    'grip': list(grip), 'tip': list(tip)}
        items.append((wid, c.image()))
    write_json(os.path.join(ASSETS, 'weapons', 'weapons.json'), out)
    if preview:
        # mark grip (green) / tip (red) on a copy for checking
        marked = []
        for (wid, im) in items:
            m = im.copy()
            g, t = out[wid]['grip'], out[wid]['tip']
            m.putpixel(tuple(g), (0, 255, 0, 255))
            m.putpixel(tuple(t), (255, 0, 0, 255))
            marked.append((wid, im))
            marked.append((wid + '*', m))
        contact_sheet(marked, scale=6, cols=4).save(os.path.join(preview, 'weapons.png'))
    return out


def gen_icons(preview):
    import items_icons as I
    items = []
    for group, ids in I.GROUPS:
        for iid in ids:
            c = I.ICONS[iid]()
            assert (c.w, c.h) == (16, 16), iid
            c.save(os.path.join(ASSETS, 'icons', iid + '.png'))
            items.append((iid, c.image()))
    if preview:
        n = 0
        for group, ids in I.GROUPS:
            sub = [it for it in items if it[0] in ids]
            contact_sheet(sub, scale=4, cols=8).save(os.path.join(preview, 'icons_%s.png' % group))
            n += 1
        # 1x strip for at-scale legibility check
        from PIL import Image
        cols = 26
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new('RGBA', (cols * 18 + 2, rows * 18 + 2), (58, 50, 66, 255))
        for i, (iid, im) in enumerate(items):
            sheet.paste(im, (2 + (i % cols) * 18, 2 + (i // cols) * 18), im)
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(
            os.path.join(preview, 'icons_1x_2x.png'))


def gen_fx(preview):
    import items_fx as F
    out = {}
    items = []
    for fid in F.FX_IDS:
        frames = F.FX[fid]()
        from pixlib import strip
        s = strip(frames)
        s.save(os.path.join(ASSETS, 'fx', fid + '.png'))
        out[fid] = {'file': 'res://assets/fx/%s.png' % fid,
                    'frame': [frames[0].w, frames[0].h], 'frames': len(frames)}
        items.append((fid, s.image()))
    write_json(os.path.join(ASSETS, 'fx', 'fx.json'), out)
    if preview:
        contact_sheet(items, scale=3, cols=3).save(os.path.join(preview, 'fx.png'))
    return out


def gen_pickups(preview):
    import items_fx as F
    from pixlib import strip
    out = {}
    items = []
    for pid in F.PICKUP_IDS:
        frames = F.PICKUPS[pid]()
        s = strip(frames)
        s.save(os.path.join(ASSETS, 'pickups', pid + '.png'))
        out[pid] = {'file': 'res://assets/pickups/%s.png' % pid,
                    'frame': [frames[0].w, frames[0].h], 'frames': len(frames)}
        items.append((pid, s.image()))
    write_json(os.path.join(ASSETS, 'pickups', 'pickups.json'), out)
    if preview:
        contact_sheet(items, scale=6, cols=5).save(os.path.join(preview, 'pickups.png'))
    return out


def gen_ui(preview):
    import items_ui as U
    items = []
    for uid, fn in U.UI:
        c = fn()
        c.save(os.path.join(ASSETS, 'ui', uid + '.png'))
        items.append((uid, c.image()))
    if preview:
        small = [it for it in items if it[1].width <= 24 and it[1].height <= 24]
        mid = [it for it in items if it not in small and it[1].width <= 72]
        bigs = [it for it in items if it not in small and it not in mid]
        contact_sheet(small, scale=6, cols=8).save(os.path.join(preview, 'ui_small.png'))
        contact_sheet(mid, scale=3, cols=5, bg=(120, 140, 110)).save(os.path.join(preview, 'ui_mid.png'))
        if bigs:
            contact_sheet(bigs, scale=2, cols=2).save(os.path.join(preview, 'ui_big.png'))
        U.preview_extra(preview)


def gen_logo(preview):
    import items_logo as LG
    items = []
    for uid, fn in LG.LOGO:
        c = fn()
        c.save(os.path.join(ASSETS, 'ui', uid + '.png'))
        items.append((uid, c.image()))
    if preview:
        LG.preview(preview, items)


STEPS = {
    'weapons': gen_weapons, 'icons': gen_icons, 'fx': gen_fx, 'pickups': gen_pickups,
    'ui': gen_ui, 'logo': gen_logo,
}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default=None)
    ap.add_argument('--only', default=','.join(STEPS))
    a = ap.parse_args()
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
    for step in a.only.split(','):
        STEPS[step](a.preview)
        print('generated', step)
