#!/usr/bin/env python3
"""itch.io page art for the v1.1 visual upgrade: a 630x500 cover and 1280x720 key art composed from the v2 title
layers and logo, plus gameplay screenshots copied from a capture_set run.
Usage: python3 tools/make_itch_assets.py <capture_dir> [out_dir]   (out_dir defaults to release/itch)"""
import json, os, shutil, sys
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UI = os.path.join(ROOT, 'game', 'assets', 'ui2')
cap = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'release', 'itch')
os.makedirs(out, exist_ok=True)
meta = json.load(open(os.path.join(UI, 'ui.json')))

def scene(w, h, hero_x, hero_scale, logo_w, logo_y):
    """Bottom-anchored title layers cropped to w:h (texel space), then hero + logo."""
    H = 720
    W = int(round(H * w / h))
    canvas = Image.new('RGBA', (W, H), (20, 14, 26, 255))
    for n in ['title_sky', 'title_far', 'title_mid', 'title_street']:
        im = Image.open(os.path.join(UI, n + '.png')).convert('RGBA')
        x = (W - im.width) // 2
        canvas.alpha_composite(im, (x, H - im.height)) if x >= 0 else canvas.alpha_composite(im.crop((-x, 0, -x + W, im.height)), (0, H - im.height))
    hero = Image.open(os.path.join(UI, 'title_hero.png')).convert('RGBA')
    fx, fy = meta['title_hero']['feet']
    hero = hero.resize((int(hero.width * hero_scale), int(hero.height * hero_scale)), Image.LANCZOS)
    canvas.alpha_composite(hero, (int(W * hero_x - fx * hero_scale), int(H - 8 - fy * hero_scale)))
    logo = Image.open(os.path.join(UI, 'logo.png')).convert('RGBA')
    lw = int(W * logo_w)
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    canvas.alpha_composite(logo, ((W - lw) // 2, int(H * logo_y)))
    return canvas.resize((w, h), Image.LANCZOS).convert('RGB')

scene(630, 500, 0.74, 0.75, 0.9, 0.02).save(os.path.join(out, 'cover_630x500.png'))
scene(1280, 720, 0.78, 0.7, 0.62, 0.02).save(os.path.join(out, 'key_art_1280x720.png'))
picks = [('c01_kettle_fight', 'screenshot_1_kettle_street.png'), ('c04_duke', 'screenshot_2_duke_boss.png'),
         ('c05_canal', 'screenshot_3_canal_market.png'), ('c06_foundry', 'screenshot_4_foundry_boss.png'),
         ('c07_neon', 'screenshot_5_neon_mile.png'), ('c08_rain', 'screenshot_6_floodgate_rain.png'),
         ('c11_dialogue', 'screenshot_7_dialogue.png'), ('c03_diner_shop', 'screenshot_8_diner_shop.png')]
for src, dst in picks:
    p = os.path.join(cap, src + '.png')
    if os.path.exists(p):
        shutil.copy(p, os.path.join(out, dst))
print('itch assets ->', out, sorted(os.listdir(out)))
