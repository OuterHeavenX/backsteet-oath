#!/usr/bin/env python3
"""Post-process step for v2 art (run after the generators): palette-quantise the large atlases and layers so the
web download stays reasonable, then turn off mipmap generation for textures that are always drawn near 1:1.

- characters (sprites/chars):  256 colours, no dithering (flat cel shading; measured 38-39 dB PSNR, visually identical)
- room layers + fg (bg2):      256 colours, light dithering (avoids banding in light gradients)
- lightmaps (light.png):       untouched (sampled numerically by the engine)
- portraits2:                   untouched (drawn small in the HUD, keep full quality + mipmaps)

Quantisation uses libimagequant through the `imagequant` Python package (BSD-3 bindings; the library is a build
tool only and is not shipped with the game). Idempotent: already-paletted files are skipped.
Usage: python3 tools/art2/optimize_textures.py [--dry-run]
"""
import glob, io, os, re, sys
from PIL import Image
import numpy as np
import imagequant

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'game'))
DRY = '--dry-run' in sys.argv

def psnr(a, b):
    a = np.asarray(a.convert('RGBA')).astype(float); b = np.asarray(b.convert('RGBA')).astype(float)
    m = a[..., 3] > 8
    if not m.any():
        return 99.0
    mse = ((a[..., :3] - b[..., :3]) ** 2)[m].mean()
    return 99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)

def quantise(path, dither):
    im = Image.open(path)
    if im.mode == 'P':
        return None
    im = im.convert('RGBA')
    q = imagequant.quantize_pil_image(im, dithering_level=dither, max_colors=256, min_quality=0, max_quality=100)
    p = psnr(im, q)
    before = os.path.getsize(path)
    if not DRY:
        q.save(path, 'PNG', optimize=True)
    return before, os.path.getsize(path) if not DRY else before, p

def no_mipmaps(path):
    imp = path + '.import'
    if not os.path.exists(imp):
        return
    s = open(imp).read()
    s2 = re.sub(r'^mipmaps/generate=true$', 'mipmaps/generate=false', s, flags=re.M)
    if s2 != s and not DRY:
        open(imp, 'w').write(s2)

jobs = [(p, 0.0) for p in sorted(glob.glob(os.path.join(ROOT, 'assets/sprites/chars/*.png')))]
jobs += [(p, 0.6) for p in sorted(glob.glob(os.path.join(ROOT, 'assets/bg2/**/*.png'), recursive=True))
         if os.path.basename(p) != 'light.png']
tot_b = tot_a = 0
worst = (99.0, '')
for p, d in jobs:
    r = quantise(p, d)
    no_mipmaps(p)
    if r is None:
        continue
    b, a, ps = r
    tot_b += b; tot_a += a
    worst = min(worst, (ps, os.path.relpath(p, ROOT)))
print(f"quantised {len(jobs)} files: {tot_b/1e6:.1f} MB -> {tot_a/1e6:.1f} MB; lowest PSNR {worst[0]:.1f} dB ({worst[1]})")
