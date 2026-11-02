#!/usr/bin/env python3
"""Composes the itch.io cover (630x500) and a 1280x720 key art from in-game assets.
Usage: python3 tools/make_cover.py <out_dir>"""
import sys, os
from PIL import Image

ROOT = os.path.join(os.path.dirname(__file__), "..", "game", "assets")
out = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(out, exist_ok=True)

def frame(char, idx, scale):
    sheet = Image.open(os.path.join(ROOT, "sprites/characters", char + ".png")).convert("RGBA")
    x, y = (idx % 8) * 64, (idx // 8) * 64
    f = sheet.crop((x, y, x + 64, y + 64))
    return f.resize((64 * scale, 64 * scale), Image.NEAREST)

def compose(w, h, logo_scale, char_scale, path):
    bg = Image.open(os.path.join(ROOT, "bg/title_bg.png")).convert("RGBA")
    s = max(w / bg.width, h / bg.height)
    bg = bg.resize((int(bg.width * s + 0.5), int(bg.height * s + 0.5)), Image.NEAREST)
    bg = bg.crop(((bg.width - w) // 2, (bg.height - h) // 2, (bg.width - w) // 2 + w, (bg.height - h) // 2 + h))
    canvas = bg.copy()
    # darken bottom for contrast
    shade = Image.new("RGBA", (w, h), (20, 14, 30, 0))
    px = shade.load()
    for yy in range(h):
        a = int(max(0, (yy - h * 0.45) / (h * 0.55)) * 150)
        for xx in range(w):
            px[xx, yy] = (20, 14, 30, a)
    canvas = Image.alpha_composite(canvas, shade)
    # characters: Rook looming behind, Mara and Nico in front
    cs = char_scale
    rook = frame("rook", 0, cs + 1)
    rook = rook.transpose(Image.FLIP_LEFT_RIGHT)
    canvas.alpha_composite(rook, (w - rook.width - int(w * 0.02), h - rook.height + int(4 * (cs + 1))))
    mara = frame("mara", 0, cs)
    canvas.alpha_composite(mara, (int(w * 0.02), h - mara.height + 4 * cs))
    nico = frame("nico", 11, cs)
    canvas.alpha_composite(nico, (int(w * 0.5 - nico.width * 0.55), h - nico.height + 4 * cs))
    logo = Image.open(os.path.join(ROOT, "ui/logo.png")).convert("RGBA")
    logo = logo.resize((int(logo.width * logo_scale), int(logo.height * logo_scale)), Image.NEAREST)
    canvas.alpha_composite(logo, ((w - logo.width) // 2, int(h * 0.05)))
    canvas.convert("RGB").save(path)
    print("wrote", path, canvas.size)

compose(630, 500, 1.0, 4, os.path.join(out, "cover_630x500.png"))
compose(1280, 720, 2.0, 6, os.path.join(out, "keyart_1280x720.png"))
