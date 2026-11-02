#!/usr/bin/env python3
"""Build the original BACKSTREET OATH pixel fonts as TrueType files.

    python3 tools/art/gen_font.py [--preview DIR]

Outputs
    game/assets/fonts/oath_pixel.ttf   8 px em  (unitsPerEm 1000, 1 px = 125 u)
    game/assets/fonts/oath_big.ttf     12 px em (unitsPerEm 1200, 1 px = 100 u)

Every glyph outline is traced from the pixel bitmaps in font_glyphs.py into
merged rectilinear contours on the integer pixel grid (outer contours
clockwise, counters counter-clockwise, TrueType convention), so rendering at
the design size (or an integer multiple) lands exactly on the pixel grid.

Deterministic: fixed timestamps, no randomness.
Fonts are original, project-owned designs (may be released under SIL OFL 1.1).
"""
import argparse
import os
import sys

sys.dont_write_bytecode = True

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools import agl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import font_glyphs as FG  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FONT_DIR = os.path.join(ROOT, 'game', 'assets', 'fonts')

# 2026-01-01T00:00:00Z expressed as seconds since 1904-01-01 (OpenType epoch)
FIXED_TIMESTAMP = 3850329600


def trace_contours(pixels, ascent_rows):
    """Return closed rectilinear contours (lists of (x, y) in pixel units, y up).

    pixels: set of (col, row) with row 0 at the top of the ascent.
    """
    edges = set()

    def add(s, e):
        if (e, s) in edges:
            edges.remove((e, s))
        else:
            edges.add((s, e))

    for (c, r) in pixels:
        x0, x1 = c, c + 1
        y1 = ascent_rows - r
        y0 = y1 - 1
        # clockwise (filled area on the right of travel direction, y up)
        add((x0, y0), (x0, y1))
        add((x0, y1), (x1, y1))
        add((x1, y1), (x1, y0))
        add((x1, y0), (x0, y0))

    out = {}
    for s, e in edges:
        out.setdefault(s, []).append(e)

    def direction(a, b):
        return (b[0] - a[0], b[1] - a[1])

    contours = []
    remaining = set(edges)
    while remaining:
        start = min(remaining)  # deterministic
        remaining.remove(start)
        out[start[0]].remove(start[1])
        pts = [start[0], start[1]]
        cur_in = direction(start[0], start[1])
        while pts[-1] != pts[0]:
            v = pts[-1]
            cands = out[v]
            if len(cands) == 1:
                nxt = cands[0]
            else:
                dx, dy = cur_in
                prefs = [(dy, -dx), (dx, dy), (-dy, dx)]  # right, straight, left
                nxt = None
                for pd in prefs:
                    for cnd in cands:
                        if direction(v, cnd) == pd:
                            nxt = cnd
                            break
                    if nxt:
                        break
            cands.remove(nxt)
            remaining.discard((v, nxt))
            cur_in = direction(v, nxt)
            pts.append(nxt)
        pts = pts[:-1]
        # drop collinear points
        simp = []
        n = len(pts)
        for i in range(n):
            a, bpt, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            d1 = direction(a, bpt)
            d2 = direction(bpt, c)
            if d1[0] * d2[1] - d1[1] * d2[0] != 0:
                simp.append(bpt)
        # rotate so the contour starts at its min point (stable output)
        k = simp.index(min(simp))
        contours.append(simp[k:] + simp[:k])
    contours.sort()
    return contours


def glyph_name(ch):
    cp = ord(ch)
    name = agl.UV2AGL.get(cp)
    if name and cp < 0x2000:
        return name
    return 'uni%04X' % cp


def bitmap_pixels(top, rows):
    px = set()
    for ry, row in enumerate(rows):
        for rx, c in enumerate(row):
            if c == '#':
                px.add((rx, top + ry))
    return px


def build_font(path, table, notdef, units_per_px, ascent_rows, descent_rows,
               spacing, space_adv, family, cap_rows, x_rows, version='1.000'):
    upm = units_per_px * (ascent_rows + descent_rows - descent_rows)  # placeholder
    em_px = {125: 8, 100: 12}[units_per_px]
    upm = units_per_px * em_px
    chars = sorted(table.keys(), key=ord)
    order = ['.notdef', 'space'] + [glyph_name(c) for c in chars]
    assert len(set(order)) == len(order)

    glyphs = {}
    metrics = {}

    def make(px, adv_px):
        pen = TTGlyphPen(None)
        cons = trace_contours(px, ascent_rows) if px else []
        xmin = 0
        if cons:
            xmin = min(x for con in cons for x, _ in con)
        for con in cons:
            pen.moveTo((con[0][0] * units_per_px, con[0][1] * units_per_px))
            for (x, y) in con[1:]:
                pen.lineTo((x * units_per_px, y * units_per_px))
            pen.closePath()
        return pen.glyph(), (adv_px * units_per_px, xmin * units_per_px)

    top, rows, _ = notdef
    glyphs['.notdef'], metrics['.notdef'] = make(bitmap_pixels(top, rows),
                                                 len(rows[0]) + spacing)
    glyphs['space'], metrics['space'] = make(set(), space_adv)
    cmap = {32: 'space'}
    for ch in chars:
        top, rows, _ = table[ch]
        name = glyph_name(ch)
        glyphs[name], metrics[name] = make(bitmap_pixels(top, rows),
                                           FG.advance(table, ch, spacing))
        cmap[ord(ch)] = name
    # no-break space shares the space glyph
    cmap[0xA0] = 'space'

    ascent = ascent_rows * units_per_px
    descent = descent_rows * units_per_px

    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ascent, descent=-descent, lineGap=0)
    ps = family.replace(' ', '') + '-Regular'
    fb.setupNameTable({
        'copyright': 'Copyright (c) 2026 the Backstreet Oath project. Original design.',
        'familyName': family,
        'styleName': 'Regular',
        'uniqueFontIdentifier': '%s;%s;Regular' % (version, ps),
        'fullName': family,
        'version': 'Version ' + version,
        'psName': ps,
        'designer': 'Backstreet Oath art team (procedural, tools/art/gen_font.py)',
        'description': 'Original pixel font made for BACKSTREET OATH. %d px em.' % em_px,
        'licenseDescription': ('Project-owned original font. May be released under the '
                               'SIL Open Font License, Version 1.1.'),
    })
    fb.setupOS2(
        version=4,
        usWeightClass=400,
        usWidthClass=5,
        fsType=0,
        sTypoAscender=ascent,
        sTypoDescender=-descent,
        sTypoLineGap=0,
        usWinAscent=ascent,
        usWinDescent=descent,
        sxHeight=x_rows * units_per_px,
        sCapHeight=cap_rows * units_per_px,
        fsSelection=0x40 | 0x80,  # REGULAR | USE_TYPO_METRICS
        achVendID='BOTH',
        ulCodePageRange1=1,
        usDefaultChar=0,
        usBreakChar=32,
        usMaxContext=0,
    )
    fb.setupPost(isFixedPitch=0, underlinePosition=-units_per_px,
                 underlineThickness=units_per_px)
    fb.updateHead(created=FIXED_TIMESTAMP, modified=FIXED_TIMESTAMP,
                  lowestRecPPEM=em_px, fontRevision=float(version), flags=0b1011)
    fb.font.recalcTimestamp = False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fb.save(path)
    return path


def build_all():
    pix = build_font(os.path.join(FONT_DIR, 'oath_pixel.ttf'), FG.PIXEL, FG.PIXEL_NOTDEF,
                     125, FG.PIXEL_ASCENT_ROWS, FG.PIXEL_DESCENT_ROWS,
                     FG.PIXEL_SPACING, FG.PIXEL_SPACE_ADV, 'Oath Pixel',
                     cap_rows=7, x_rows=5)
    big = build_font(os.path.join(FONT_DIR, 'oath_big.ttf'), FG.BIG, FG.BIG_NOTDEF,
                     100, FG.BIG_ASCENT_ROWS, FG.BIG_DESCENT_ROWS,
                     FG.BIG_SPACING, FG.BIG_SPACE_ADV, 'Oath Big',
                     cap_rows=10, x_rows=7)
    return pix, big


SAMPLE_PIXEL = [
    "BACKSTREET OATH - Bellwether, 1988",
    "The quick brown fox jumps over the lazy dog.",
    "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG!",
    "0123456789 $25.00 HP 120/150 ATK+3 x3 50%",
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~",
    "Café á ó señor ü ‘quote’ “Dot’s Diner” – — …",
    "×3 • © ← ↑ → ↓ ★ ♥  Nico: “I made a promise.”",
    "Mara: Grab the wrench. We ride at dawn.",
]
SAMPLE_BIG = [
    "BACKSTREET OATH",
    "QUEST LOG  STAGE 3",
    "Old Quarter ★ Canal Market",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789 !?&$%#@",
    "Victory… Rook’s ♥ — (x2) [ok] {go}",
]


def preview(out_dir):
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    os.makedirs(out_dir, exist_ok=True)
    pix_path = os.path.join(FONT_DIR, 'oath_pixel.ttf')
    big_path = os.path.join(FONT_DIR, 'oath_big.ttf')
    report = []
    blocks = []
    for path, size, lines, lh in [
            (pix_path, 8, SAMPLE_PIXEL, 10), (pix_path, 16, SAMPLE_PIXEL, 20),
            (big_path, 12, SAMPLE_BIG, 14), (big_path, 24, SAMPLE_BIG, 28)]:
        font = ImageFont.truetype(path, size)
        w = 8 + max(int(font.getlength(s)) for s in lines) + 8
        h = 6 + lh * len(lines) + 6
        img = Image.new('L', (w, h), 0)
        d = ImageDraw.Draw(img)
        d.fontmode = 'L'  # antialiased on purpose: grid-aligned glyphs show no gray
        for i, s in enumerate(lines):
            d.text((8, 6 + i * lh), s, font=font, fill=255)
        arr = np.array(img)
        gray = int(((arr > 0) & (arr < 255)).sum())
        report.append('%s @%dpx: %d partial-coverage pixels' % (os.path.basename(path), size, gray))
        blocks.append(img)
    # compose a colored contact sheet
    W = max(b.width for b in blocks)
    H = sum(b.height for b in blocks) + 4 * len(blocks)
    sheet = Image.new('RGB', (W, H), (26, 18, 32))
    y = 0
    for bimg in blocks:
        col = Image.new('RGB', bimg.size, (232, 216, 176))
        sheet.paste(col, (0, y), bimg)
        y += bimg.height + 4
    sheet.resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(out_dir, 'fonts_preview.png'))
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', default=None)
    a = ap.parse_args()
    pix, big = build_all()
    print('wrote', pix)
    print('wrote', big)
    if a.preview:
        for line in preview(a.preview):
            print(line)
