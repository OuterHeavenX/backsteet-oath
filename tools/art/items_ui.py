"""UI skin pieces: 9-patch panels/buttons/frames, cursor, gamepad glyphs, touch controls."""
import math
import os
import numpy as np
from PIL import Image, ImageDraw

import font_glyphs as FG
from pixlib import Canvas, MAT, INK, CLEAR, CREAM, hexc, mix, with_alpha, micro_width

PLUM = hexc('#1a1220')
PLUM_92 = with_alpha(PLUM, 235)
PLUM_SH = hexc('#0c0810', 235)
CREAM_D = hexc('#b8a07a')
CREAM_L = hexc('#fff4d8')
MUST = hexc('#f0c040')
MUST_D = hexc('#a87a20')
MUST_L = hexc('#fff06a')
FACE = hexc('#3a2a46')
FACE_L = hexc('#5a4466')
FACE_D = hexc('#24182c')


def A(c, a):
    return with_alpha(c, a)


def layered(c, layers, k, fill, inset0=0):
    """Concentric chamfered bands: layers = [(thickness, color), ...] outside->in."""
    i = inset0
    w, h = c.w, c.h

    def ch(n):
        kk = max(0, k - n // 2) if n else k
        return c.chamfer(n, n, w - 1 - n, h - 1 - n, kk)

    for t, col in layers:
        m = ch(i) & ~ch(i + t)
        c.fill(m, col)
        i += t
    c.fill(ch(i), fill)
    return c


def panel():
    c = Canvas(24, 24)
    return layered(c, [(1, INK), (2, CREAM), (1, PLUM_SH)], 3, PLUM_92)


def panel_light():
    c = Canvas(24, 24)
    return layered(c, [(2, INK), (1, CREAM_L), (1, CREAM_D)], 3, CREAM)


def dialog_box():
    c = Canvas(32, 32)
    layered(c, [(1, INK), (2, CREAM), (2, PLUM_92), (1, MUST_D), (1, PLUM_SH)], 4, PLUM_92)
    # rivets in the corners of the cream band
    for (x, y) in [(5, 5), (26, 5), (5, 26), (26, 26)]:
        c.px(x, y, MUST)
    return c


def _button(face, face_l, face_d, border, top_hi=None, pressed=False, depth_col=None):
    c = Canvas(24, 16)
    off = 2 if pressed else 0
    body = c.chamfer(0, off, 23, 15, 2)
    c.fill(body, INK)
    inner = c.chamfer(1, off + 1, 22, 14, 1)
    c.fill(inner, border)
    face_m = c.chamfer(2, off + 2, 21, 13 if pressed else 11, 1)
    c.fill(face_m, face)
    c.fill(face_m & (c.yy == off + 2), top_hi or face_l)
    if not pressed:
        depth = c.R(2, 12, 21, 13) & inner
        c.fill(depth, depth_col or face_d)
        c.fill(c.R(1, 14, 22, 14) & inner, face_d)
    return c


def button():
    return _button(FACE, FACE_L, FACE_D, CREAM_D)


def button_focus():
    return _button(hexc('#4a3656'), hexc('#6a5276'), FACE_D, MUST, top_hi=MUST_L)


def button_pressed():
    return _button(hexc('#2a1e34'), FACE, FACE_D, CREAM_D, top_hi=FACE_D, pressed=True)


def button_disabled():
    return _button(hexc('#3a3a46'), hexc('#4a4a56'), hexc('#24242e'), hexc('#5a5a66'))


def bar_frame():
    c = Canvas(12, 8)
    c.fill(c.chamfer(0, 0, 11, 7, 1), INK)
    c.fill(c.R(1, 1, 10, 6), CREAM)
    c.fill(c.R(2, 2, 9, 5), INK)
    c.fill(c.R(3, 3, 8, 4), hexc('#2a2030', 230))
    return c


def boss_bar_frame():
    c = Canvas(16, 12)
    c.fill(c.chamfer(0, 0, 15, 11, 2), INK)
    c.fill(c.chamfer(1, 1, 14, 10, 1), MAT['red'][0])
    c.fill(c.R(2, 2, 13, 9), MUST)
    c.fill(c.R(2, 9, 13, 9), MUST_D)
    c.fill(c.R(3, 3, 12, 8), INK)
    c.fill(c.R(4, 4, 11, 7), hexc('#2a2030', 230))
    c.px(1, 5, MUST_L)
    c.px(14, 5, MUST_L)
    return c


def key_cap():
    c = Canvas(12, 12)
    c.fill(c.rrect(0, 0, 11, 11, 2), INK)
    c.fill(c.rrect(1, 1, 10, 10, 1), CREAM_D)
    top = c.rrect(1, 1, 10, 8, 1)
    c.fill(top, CREAM)
    c.fill(c.R(2, 1, 9, 1), CREAM_L)
    c.fill(c.R(1, 9, 10, 10) & c.rrect(1, 1, 10, 10, 1), hexc('#8a7a5a'))
    return c


def portrait_frame():
    c = Canvas(70, 70)
    c.fill(c.chamfer(0, 0, 69, 69, 2), INK)
    c.fill(c.R(1, 1, 68, 68), CREAM)
    c.fill(c.R(2, 2, 67, 67), INK)
    c.fill(c.R(3, 3, 66, 66), CLEAR)
    for (x0, y0, sx, sy) in [(1, 1, 1, 1), (68, 1, -1, 1), (1, 68, 1, -1), (68, 68, -1, -1)]:
        for i in range(8):
            c.px(x0 + sx * i, y0, MUST)
            c.px(x0, y0 + sy * i, MUST)
    for x in (34, 35):
        c.px(x, 1, MUST)
        c.px(x, 68, MUST)
    return c


def cursor():
    c = Canvas(8, 8)
    fill = {1: (1, 1), 2: (1, 3), 3: (1, 5), 4: (1, 5), 5: (1, 3), 6: (1, 1)}
    for y, (x0, x1) in fill.items():
        for x in range(x0, x1 + 1):
            c.px(x, y, MUST if y >= 3 else MUST_L)
    c.pxs([(1, 5), (2, 5), (1, 6), (3, 4), (4, 4), (5, 4)], MUST_D)
    c.outline()
    return c


# ---------------------------------------------------------------- gamepad
def _text_center(c, s, cx, top, col, shadow=None):
    w = FG.text_width(s)
    x = int(round(cx - w / 2.0))
    if shadow:
        c.text(s, x + 1, top + 1, shadow)
    c.text(s, x, top, col)


def _face_button(name, letter, letter_col, shadow):
    def f():
        c = Canvas(12, 12)
        m = c.E(1, 1, 10, 10)
        c.ball(m, name, spec=False)
        c.fill(m & ((c.xx + c.yy) < 7), MAT[name][2])
        _text_center(c, letter, 6, 1, letter_col, shadow)
        c.outline()
        return c
    return f


def _shoulder(label, trigger, left):
    def f():
        c = Canvas(16, 10)
        if trigger:
            m = c.rrect(1, 1, 14, 8, 3)
            col = 'gray'
        else:
            m = c.rrect(1, 2, 14, 8, 1) & ~c.P([(1, 2), (5, 2), (1, 6)])
            col = 'charcoal'
        if not left:
            m = m[:, ::-1].copy()
        c.shade(m, col)
        _text_center(c, label, 8, 1 if trigger else 1, CREAM if not trigger else hexc('#ffffff'),
                     INK if trigger else None)
        c.outline()
        return c
    return f


def gp_start():
    """Three-line 'menu' glyph."""
    c = Canvas(12, 10)
    m = c.rrect(1, 1, 10, 8, 2)
    c.shade(m, 'charcoal')
    for y in (3, 5, 7):
        c.fill(c.R(3, y, 8, y), CREAM)
    c.outline()
    return c


def gp_select():
    c = Canvas(12, 10)
    m = c.rrect(1, 1, 10, 8, 2)
    c.shade(m, 'charcoal')
    back = c.R(3, 2, 6, 5) & ~c.R(4, 3, 5, 4)
    front = c.R(5, 4, 8, 7)
    c.fill(back, CREAM_D)
    c.fill(front, CREAM)
    c.fill(c.R(6, 5, 7, 6), MAT['charcoal'][0])
    c.outline()
    return c


def gp_dpad():
    c = Canvas(12, 12)
    m = c.R(4, 1, 7, 10) | c.R(1, 4, 10, 7)
    c.shade(m, 'charcoal')
    c.fill(c.C(6, 6, 1.4), MAT['charcoal'][1])
    tri = CREAM_D
    c.pxs([(5, 2), (6, 2), (5, 9), (6, 9), (2, 5), (2, 6), (9, 5), (9, 6)], tri)
    c.outline()
    return c


def gp_lstick():
    c = Canvas(12, 12)
    base = c.E(1, 1, 10, 10)
    c.shade(base, 'charcoal')
    knob = c.E(3, 3, 8, 8)
    c.ball(knob, 'gray', spec=False)
    c.text('L', 5, 4, INK, micro=True)
    c.outline()
    return c


# ---------------------------------------------------------------- touch
PICTO = CREAM
PICTO_D = hexc('#a08a64')


def _touch_round(size, accent, picto_fn=None, label=None, ring_w=3):
    c = Canvas(size, size)
    cx = cy = size / 2.0
    r = size / 2.0
    c.fill(c.C(cx, cy, r), A(INK, 210))
    c.fill(c.C(cx, cy, r - 1.5), A(accent, 235))
    c.fill(c.C(cx, cy, r - 1.5 - ring_w), A(PLUM, 150))
    c.fill(c.ring(cx, cy, r - 1.5 - ring_w, r - 2.5 - ring_w), A(INK, 120))
    # top gloss arc
    gl = c.ring(cx, cy, r - 2.0, r - 1.5 - ring_w + 0.5) & (c.yy < cy - r * 0.45)
    c.fill(gl, A(mix(accent, hexc('#ffffff'), 0.45), 235))
    if picto_fn:
        p = Canvas(size, size)
        picto_fn(p)
        p.outline()
        c.blit(p, 0, 0)
    if label:
        lab = Canvas(size, size)
        w = FG.text_width(label)
        x = int(round(cx - w / 2.0))
        top = int(size * 0.66)
        lab.text(label, x, top, CREAM)
        lab.outline(diag=True)
        c.blit(lab, 0, 0)
    return c


def _p_fist(p):
    ox, oy = 16, 8
    for i in range(4):
        f = p.rrect(ox + i * 6, oy, ox + i * 6 + 5, oy + 10, 2)
        p.fill(f, PICTO)
    palm = p.rrect(ox, oy + 6, ox + 23, oy + 19, 2)
    p.fill(palm, PICTO)
    for i in range(1, 4):
        p.fill(p.R(ox + i * 6, oy + 1, ox + i * 6, oy + 8), PICTO_D)
    thumb = p.rrect(ox - 1, oy + 11, ox + 14, oy + 15, 2)
    p.fill(thumb, PICTO)
    p.fill(p.edge(thumb, 'rb') & ~p.edge(palm, 'rb'), PICTO_D)
    p.fill(p.R(ox + 3, oy + 19, ox + 20, oy + 21), PICTO_D)
    p.fill(p.R(ox + 3, oy + 20, ox + 20, oy + 21), PICTO)


def _p_kick(p):
    leg = p.P([(14, 8), (21, 8), (30, 20), (25, 24)])
    p.fill(leg, PICTO)
    shoe = p.rrect(24, 17, 42, 25, 3)
    p.fill(shoe, PICTO)
    p.fill(p.R(25, 24, 42, 25) & shoe, PICTO_D)
    p.fill(p.R(31, 18, 33, 19) | p.R(35, 19, 37, 20), PICTO_D)
    for (x0, y0) in [(44, 15), (45, 20), (44, 25)]:
        p.fill(p.R(x0, y0, x0 + 4, y0), PICTO)


def _p_jump(p):
    arrow = p.P([(28, 6), (40, 18), (33, 18), (33, 30), (23, 30), (23, 18), (16, 18)])
    p.fill(arrow, PICTO)
    p.fill(p.R(23, 28, 33, 30) & arrow, PICTO_D)
    p.fill(p.R(19, 33, 37, 34), PICTO_D)


def _p_guard(p):
    sh = p.P([(16, 8), (40, 8), (40, 18), (35, 27), (28, 32), (21, 27), (16, 18)])
    p.fill(sh, PICTO)
    inner = p.P([(20, 12), (36, 12), (36, 18), (32, 25), (28, 28), (24, 25), (20, 18)])
    p.fill(p.edge(inner, 'all'), PICTO_D)
    p.fill(p.R(27, 12, 29, 27) & inner, PICTO_D)


def _p_hand(p):
    for i, (x0, y0, h) in enumerate([(18, 9, 14), (23, 6, 17), (28, 6, 17), (33, 9, 14)]):
        p.fill(p.rrect(x0, y0, x0 + 3, y0 + h, 1), PICTO)
    palm = p.rrect(18, 18, 36, 31, 3)
    p.fill(palm, PICTO)
    thumb = p.P([(13, 16), (16, 15), (21, 22), (19, 27)])
    p.fill(thumb, PICTO)
    for x in (22, 27, 32):
        p.fill(p.R(x, 12, x, 18), PICTO_D)


def _p_run(p):
    shoe = p.P([(22, 12), (30, 12), (33, 18), (42, 20), (44, 26), (20, 26), (20, 14)])
    p.fill(shoe, PICTO)
    p.fill(p.R(20, 24, 44, 26) & shoe, PICTO_D)
    p.fill(p.R(25, 15, 29, 15) | p.R(27, 18, 31, 18), PICTO_D)
    for (x0, y0, l) in [(8, 14, 9), (6, 19, 11), (8, 24, 9)]:
        p.fill(p.R(x0, y0, x0 + l, y0 + 1), PICTO)


ACCENTS = {
    'punch': MAT['red'][0], 'kick': MAT['orange'][0], 'jump': MAT['green'][0],
    'guard': MAT['blue'][0], 'grab': MAT['mustard'][0], 'run': MAT['teal'][0],
}


def _touch_btn(kind, picto, label):
    return lambda: _touch_round(56, ACCENTS[kind], picto, label)


def touch_btn_pause():
    def pic(p):
        p.fill(p.R(11, 9, 14, 22) | p.R(18, 9, 21, 22), PICTO)
    return _touch_round(32, hexc('#8a8a96'), pic, None, ring_w=2)


def touch_btn_status():
    def pic(p):
        p.fill(p.C(16, 12, 4.2), PICTO)
        p.fill(p.rrect(9, 17, 23, 24, 3), PICTO)
        p.fill(p.R(9, 23, 23, 24), PICTO_D)
    return _touch_round(32, hexc('#8a8a96'), pic, None, ring_w=2)


def touch_stick_base():
    c = Canvas(96, 96)
    cx = cy = 48
    c.fill(c.C(cx, cy, 48), A(INK, 170))
    c.fill(c.C(cx, cy, 46.5), A(CREAM, 150))
    c.fill(c.C(cx, cy, 43.0), A(PLUM, 90))
    c.fill(c.ring(cx, cy, 43.0, 41.8), A(INK, 110))
    c.fill(c.ring(cx, cy, 22, 21), A(CREAM, 70))
    for k in range(4):
        a = k * math.pi / 2
        ux, uy = math.cos(a), math.sin(a)
        px, py = -uy, ux
        tip = (cx + ux * 39, cy + uy * 39)
        b1 = (cx + ux * 33 + px * 6, cy + uy * 33 + py * 6)
        b2 = (cx + ux * 33 - px * 6, cy + uy * 33 - py * 6)
        m = c.P([tip, b1, b2])
        c.fill(c.dilate(m, 1) & ~m, A(INK, 200))
        c.fill(m, A(CREAM, 220))
    return c


def touch_stick_knob():
    c = Canvas(40, 40)
    cx = cy = 20
    c.fill(c.C(cx, cy, 20), A(INK, 220))
    c.fill(c.C(cx, cy, 18.5), A(CREAM, 200))
    c.fill(c.C(cx, cy, 18.5) & ~c.C(cx - 2, cy - 2, 17.5), A(CREAM_D, 210))
    c.fill(c.C(cx - 5, cy - 6, 5.0), A(CREAM_L, 220))
    c.fill(c.ring(cx, cy, 10, 9), A(CREAM_D, 200))
    c.fill(c.C(cx, cy, 2.0), A(CREAM_D, 200))
    return c


def rotate_device():
    c = Canvas(64, 64)
    ghost = c.rrect(24, 4, 43, 39, 3)
    c.fill(c.edge(ghost, 'all'), A(CREAM, 150))
    c.fill(c.edge(c.rrect(25, 5, 42, 38, 2), 'all') & ~c.edge(ghost, 'all'), A(INK, 120))
    phone = c.rrect(6, 30, 53, 55, 3)
    c.fill(phone, CREAM)
    c.fill(c.R(11, 33, 47, 52), hexc('#2a2040'))
    c.fill(c.R(12, 34, 30, 35), hexc('#4a4070'))
    c.fill(c.R(49, 40, 51, 45), CREAM_D)
    c.fill(c.edge(phone, 'rb'), CREAM_D)
    arc = c.ring(36, 30, 23, 19) & (c.xx >= 44) & (c.yy <= 30)
    arc &= ~(c.yy < 8)
    head = c.P([(51, 27), (63, 27), (57, 35)])
    m = arc | head
    c.fill(m, MUST)
    c.fill(c.edge(m, 'rb'), MUST_D)
    c.outline()
    return c


UI = [
    ('panel', panel), ('panel_light', panel_light), ('dialog_box', dialog_box),
    ('button', button), ('button_focus', button_focus), ('button_pressed', button_pressed),
    ('button_disabled', button_disabled), ('bar_frame', bar_frame),
    ('boss_bar_frame', boss_bar_frame), ('key_cap', key_cap),
    ('portrait_frame', portrait_frame), ('cursor', cursor),
    ('gp_a', _face_button('green', 'A', hexc('#ffffff'), MAT['green'][1])),
    ('gp_b', _face_button('red', 'B', hexc('#ffffff'), MAT['red'][1])),
    ('gp_x', _face_button('blue', 'X', hexc('#ffffff'), MAT['blue'][1])),
    ('gp_y', _face_button('yellow', 'Y', INK, None)),
    ('gp_lb', _shoulder('LB', False, True)), ('gp_rb', _shoulder('RB', False, False)),
    ('gp_lt', _shoulder('LT', True, True)), ('gp_rt', _shoulder('RT', True, False)),
    ('gp_start', gp_start), ('gp_select', gp_select), ('gp_dpad', gp_dpad),
    ('gp_lstick', gp_lstick),
    ('touch_stick_base', touch_stick_base), ('touch_stick_knob', touch_stick_knob),
    ('touch_btn_punch', _touch_btn('punch', _p_fist, 'P')),
    ('touch_btn_kick', _touch_btn('kick', _p_kick, 'K')),
    ('touch_btn_jump', _touch_btn('jump', _p_jump, 'JUMP')),
    ('touch_btn_guard', _touch_btn('guard', _p_guard, 'GRD')),
    ('touch_btn_grab', _touch_btn('grab', _p_hand, 'GRAB')),
    ('touch_btn_run', _touch_btn('run', _p_run, 'RUN')),
    ('touch_btn_pause', touch_btn_pause), ('touch_btn_status', touch_btn_status),
    # label-free variants: the engine draws live, context-sensitive labels on these
    ('touch_btn_punch_bare', _touch_btn('punch', _p_fist, None)),
    ('touch_btn_kick_bare', _touch_btn('kick', _p_kick, None)),
    ('touch_btn_jump_bare', _touch_btn('jump', _p_jump, None)),
    ('touch_btn_guard_bare', _touch_btn('guard', _p_guard, None)),
    ('touch_btn_grab_bare', _touch_btn('grab', _p_hand, None)),
    ('touch_btn_run_bare', _touch_btn('run', _p_run, None)),
    ('rotate_device', rotate_device),
]

UI_SIZES = {
    'panel': (24, 24), 'panel_light': (24, 24), 'dialog_box': (32, 32), 'button': (24, 16),
    'button_focus': (24, 16), 'button_pressed': (24, 16), 'button_disabled': (24, 16),
    'bar_frame': (12, 8), 'boss_bar_frame': (16, 12), 'key_cap': (12, 12),
    'portrait_frame': (70, 70), 'cursor': (8, 8),
    'gp_a': (12, 12), 'gp_b': (12, 12), 'gp_x': (12, 12), 'gp_y': (12, 12),
    'gp_lb': (16, 10), 'gp_rb': (16, 10), 'gp_lt': (16, 10), 'gp_rt': (16, 10),
    'gp_start': (12, 10), 'gp_select': (12, 10), 'gp_dpad': (12, 12), 'gp_lstick': (12, 12),
    'touch_stick_base': (96, 96), 'touch_stick_knob': (40, 40),
    'touch_btn_punch': (56, 56), 'touch_btn_kick': (56, 56), 'touch_btn_jump': (56, 56),
    'touch_btn_guard': (56, 56), 'touch_btn_grab': (56, 56), 'touch_btn_run': (56, 56),
    'touch_btn_pause': (32, 32), 'touch_btn_status': (32, 32), 'rotate_device': (64, 64),
    'touch_btn_punch_bare': (56, 56), 'touch_btn_kick_bare': (56, 56), 'touch_btn_jump_bare': (56, 56),
    'touch_btn_guard_bare': (56, 56), 'touch_btn_grab_bare': (56, 56), 'touch_btn_run_bare': (56, 56),
}

NINE_PATCH = {
    'panel': 8, 'panel_light': 8, 'dialog_box': 10, 'button': 6, 'button_focus': 6,
    'button_pressed': 6, 'button_disabled': 6, 'bar_frame': 3, 'boss_bar_frame': 4, 'key_cap': 4,
}


def nine_slice(im, m, w, h):
    W, H = im.size
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    xs = [(0, m, 0, m), (m, W - m, m, w - m), (W - m, W, w - m, w)]
    ys = [(0, m, 0, m), (m, H - m, m, h - m), (H - m, H, h - m, h)]
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            if dx1 <= dx0 or dy1 <= dy0:
                continue
            piece = im.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.NEAREST)
            out.paste(piece, (dx0, dy0))
    return out


def preview_extra(out_dir):
    """Mock-up: 9-patch pieces stretched, with text, over a street-ish background."""
    from PIL import ImageFont
    root = os.path.join(os.path.dirname(__file__), '..', '..', 'game', 'assets')
    font = ImageFont.truetype(os.path.join(root, 'fonts', 'oath_pixel.ttf'), 8)
    big = ImageFont.truetype(os.path.join(root, 'fonts', 'oath_big.ttf'), 12)
    W, H = 320, 200
    bg = Image.new('RGBA', (W, H), (160, 74, 58, 255))
    d = ImageDraw.Draw(bg)
    for y in range(0, H, 8):
        off = 0 if (y // 8) % 2 == 0 else 8
        for x in range(-16, W, 16):
            d.rectangle([x + off, y, x + off + 14, y + 6], fill=(168, 80, 62, 255))
        d.line([(0, y + 7), (W, y + 7)], fill=(90, 58, 52, 255))
    d.rectangle([0, 150, W, H], fill=(138, 132, 120, 255))
    ui = lambda n: Image.open(os.path.join(root, 'ui', n + '.png')).convert('RGBA')
    p = nine_slice(ui('panel'), 8, 150, 60)
    bg.alpha_composite(p, (6, 6))
    d.text((16, 14), 'QUEST LOG', font=big, fill=(240, 192, 64, 255))
    d.text((16, 32), 'Find Eli near the canal.', font=font, fill=(232, 216, 176, 255))
    d.text((16, 44), 'HP 120/150  $25', font=font, fill=(232, 216, 176, 255))
    pl = nine_slice(ui('panel_light'), 8, 120, 44)
    bg.alpha_composite(pl, (164, 6))
    d.text((174, 16), 'Lucky Spoon menu', font=font, fill=(26, 18, 32, 255))
    d.text((174, 28), 'Coffee ....... $2', font=font, fill=(26, 18, 32, 255))
    db = nine_slice(ui('dialog_box'), 10, 300, 52)
    bg.alpha_composite(db, (10, 142))
    bg.alpha_composite(ui('portrait_frame').resize((35, 35), Image.NEAREST), (18, 150))
    d.text((60, 154), 'Dot: “Keep your head down, kid.”', font=font, fill=(232, 216, 176, 255))
    d.text((60, 166), 'Rook’s men were here …', font=font, fill=(232, 216, 176, 255))
    bx = 10
    for n in ['button', 'button_focus', 'button_pressed', 'button_disabled']:
        b = nine_slice(ui(n), 6, 60, 18)
        bg.alpha_composite(b, (bx, 74))
        col = (232, 216, 176, 255) if n != 'button_disabled' else (120, 120, 130, 255)
        ty = 79 + (2 if n == 'button_pressed' else 0)
        d.text((bx + 12, ty - 1), n.split('_')[-1].upper()[:5] if n != 'button' else 'OK', font=font, fill=col)
        bx += 66
    hb = nine_slice(ui('bar_frame'), 3, 100, 8)
    bg.alpha_composite(hb, (10, 100))
    d.rectangle([13, 103, 13 + 60, 104], fill=(122, 240, 74, 255))
    bb = nine_slice(ui('boss_bar_frame'), 4, 180, 12)
    bg.alpha_composite(bb, (120, 98))
    d.rectangle([124, 102, 124 + 120, 105], fill=(224, 74, 74, 255))
    x = 10
    for n in ['key_cap']:
        for lab in ['Z', 'X', 'C']:
            kc = nine_slice(ui(n), 4, 14, 14)
            bg.alpha_composite(kc, (x, 116))
            d.text((x + 4, 117), lab, font=font, fill=(26, 18, 32, 255))
            x += 16
    kc = nine_slice(ui('key_cap'), 4, 36, 14)
    bg.alpha_composite(kc, (x, 116))
    d.text((x + 5, 117), 'SPACE', font=font, fill=(26, 18, 32, 255))
    x += 42
    for n in ['gp_a', 'gp_b', 'gp_x', 'gp_y', 'gp_lb', 'gp_rb', 'gp_lt', 'gp_rt', 'gp_start',
              'gp_select', 'gp_dpad', 'gp_lstick', 'cursor']:
        im = ui(n)
        bg.alpha_composite(im, (x, 117))
        x += im.width + 3
    bg.resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(out_dir, 'ui_mockup.png'))
    # touch controls on light and dark backgrounds
    T = Image.new('RGBA', (420, 260), (0, 0, 0, 255))
    dt = ImageDraw.Draw(T)
    dt.rectangle([0, 0, 420, 130], fill=(138, 200, 232, 255))
    dt.rectangle([0, 130, 420, 260], fill=(30, 26, 58, 255))
    for row, y in [(0, 10), (1, 140)]:
        T.alpha_composite(ui('touch_stick_base'), (8, y))
        T.alpha_composite(ui('touch_stick_knob'), (36, y + 28))
        xx = 112
        for n in ['punch', 'kick', 'jump', 'guard', 'grab', 'run']:
            T.alpha_composite(ui('touch_btn_' + n), (xx, y + (0 if n in ('punch', 'jump', 'grab') else 50)))
            xx += 40 if n in ('punch', 'jump', 'grab') else 26
            xx += 0
        T.alpha_composite(ui('touch_btn_pause'), (330, y))
        T.alpha_composite(ui('touch_btn_status'), (370, y))
        T.alpha_composite(ui('rotate_device'), (340, y + 44))
    T.resize((840, 520), Image.NEAREST).save(os.path.join(out_dir, 'ui_touch.png'))
