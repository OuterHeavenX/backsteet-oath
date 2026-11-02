"""World weapon sprites (horizontal, pointing right, 1px ink outline)."""
from pixlib import Canvas, MAT, INK, hexc, mat

WEAPON_IDS = ['wrench', 'baton', 'bat', 'pipe', 'broom', 'chain', 'belt', 'newspaper',
              'spatula', 'bottle', 'brick', 'fish', 'tire', 'road_sign']


def wrench():
    c = Canvas(16, 7)
    handle = c.rrect(1, 2, 10, 4, 1)
    c.shade(handle, 'steel')
    head = c.E(9, 1, 14, 5)
    c.shade(head, 'steel')
    c.fill(c.R(12, 3, 14, 3), (0, 0, 0, 0))  # open jaw
    c.px(13, 2, MAT['steel'][2])
    c.fill(c.R(3, 3, 8, 3), MAT['steel'][1])  # handle groove
    c.outline()
    return c, (4, 3), (14, 3)


def baton():
    c = Canvas(18, 5)
    body = c.rrect(1, 1, 16, 3, 1)
    c.shade(body, 'black')
    for x in range(2, 7, 2):
        c.fill(c.R(x, 1, x, 3), MAT['charcoal'][0])
    c.fill(c.R(7, 1, 7, 3), MAT['steel'][0])
    c.fill(c.R(8, 1, 15, 1), MAT['black'][2])
    c.outline()
    return c, (4, 2), (16, 2)


def bat():
    c = Canvas(30, 6)
    body = c.P([(3, 2), (13, 2), (19, 1), (27, 1), (28, 2), (28, 3), (27, 4), (19, 4), (13, 3), (3, 3)])
    c.shade(body, 'tan')
    knob = c.rrect(1, 1, 2, 4, 0)
    c.shade(knob, 'wood')
    c.fill(c.R(19, 1, 27, 1), MAT['tan'][2])
    for x in range(4, 11, 2):  # grip tape
        c.fill(c.R(x, 2, x, 3), MAT['charcoal'][0])
    c.fill(c.R(22, 3, 24, 3), MAT['tan'][1])  # wood grain
    c.px(26, 2, MAT['tan'][1])
    c.outline()
    return c, (6, 2), (28, 2)


def pipe():
    c = Canvas(32, 5)
    body = c.R(1, 1, 27, 3)
    c.shade(body, 'iron')
    c.fill(c.R(1, 1, 27, 1), MAT['steel'][0])
    fit = c.R(27, 0, 30, 4)
    c.shade(fit, 'steel')
    c.fill(c.R(28, 0, 28, 4), MAT['steel'][1])
    for x, y in [(9, 2), (10, 3), (17, 2), (18, 2), (22, 3)]:
        c.px(x, y, MAT['rust'][0])
    c.px(16, 3, MAT['rust'][1])
    c.outline()
    return c, (4, 2), (30, 2)


def broom():
    c = Canvas(40, 8)
    stick = c.R(1, 3, 26, 4)
    c.shade(stick, 'wood')
    head = c.P([(27, 2), (37, 1), (38, 1), (38, 6), (37, 6), (27, 5)])
    c.fill(head, MAT['mustard'][0])
    cols = [MAT['yellow'][2], MAT['yellow'][0], MAT['mustard'][0], MAT['mustard'][1],
            MAT['yellow'][0], MAT['mustard'][1]]
    for i, y in enumerate(range(1, 7)):
        c.fill(c.R(27, y, 38, y) & head, cols[i])
    for x, y in [(38, 2), (38, 4), (37, 6), (38, 5)]:
        c.px(x, y, (0, 0, 0, 0))
    for x, y in [(33, 2), (31, 4), (35, 3), (34, 5)]:
        c.px(x, y, MAT['mustard'][1])
    band = c.R(25, 2, 28, 5)
    c.shade(band, 'red')
    c.fill(c.R(26, 2, 26, 5), MAT['red'][2])
    c.outline()
    return c, (4, 3), (38, 3)


def chain():
    c = Canvas(40, 6)
    grip = c.R(1, 1, 6, 4)
    c.shade(grip, 'charcoal')
    for x in (2, 4):
        c.fill(c.R(x, 1, x, 4), MAT['gray'][1])
    x = 7
    face = True
    links = []
    while x + 5 <= 38:
        if face:
            m = c.rrect(x, 1, x + 5, 4, 1) & ~c.R(x + 2, 2, x + 3, 3)
        else:
            m = c.R(x, 2, x + 5, 3)
        links.append((m, face))
        x += 5
        face = not face
    for m, face in links:
        if not face:
            c.shade(m, 'steel')
    for m, face in links:
        if face:
            c.shade(m, 'steel')
    c.outline()
    return c, (3, 2), (37, 2)


def belt():
    c = Canvas(28, 5)
    strap = c.R(1, 1, 22, 3)
    c.shade(strap, 'brown')
    for x in range(2, 21, 2):
        c.px(x, 2, MAT['brown'][2])
    for x in (5, 8, 11):
        c.px(x, 2, INK)
    c.fill(c.R(1, 1, 1, 3), MAT['brown'][1])
    buckle = c.R(21, 0, 26, 4) & ~c.R(23, 2, 24, 2)
    c.shade(buckle, 'gold')
    c.fill(c.R(22, 2, 25, 2), MAT['gold'][1])
    c.outline()
    return c, (3, 2), (26, 2)


def newspaper():
    c = Canvas(18, 6)
    roll = c.rrect(1, 1, 16, 4, 1)
    c.shade(roll, 'paper')
    for x0 in (4, 11):
        c.fill(c.R(x0, 2, x0 + 2, 2), MAT['gray'][0])
        c.fill(c.R(x0 + 1, 3, x0 + 3, 3), MAT['gray'][0])
    c.fill(c.R(14, 2, 15, 2), MAT['gray'][0])
    c.fill(c.R(8, 1, 9, 4), MAT['red'][0])
    c.px(8, 1, MAT['red'][2])
    c.fill(c.R(1, 2, 1, 3), MAT['paper'][1])
    c.px(2, 2, MAT['gray'][0])
    c.outline()
    return c, (3, 2), (16, 2)


def spatula():
    c = Canvas(18, 7)
    handle = c.rrect(1, 2, 8, 4, 1)
    c.shade(handle, 'black')
    c.px(2, 3, INK)
    neck = c.R(9, 3, 11, 3)
    c.fill(neck, MAT['steel'][1])
    blade = c.rrect(11, 1, 16, 5, 1)
    c.shade(blade, 'steel')
    for y in (2, 4):
        c.fill(c.R(13, y, 15, y), MAT['iron'][1])
    c.outline()
    return c, (4, 3), (16, 3)


def bottle():
    c = Canvas(12, 6)
    body = c.rrect(1, 1, 7, 4, 1)
    c.shade(body, 'bottle')
    neck = c.R(8, 2, 10, 3)
    c.shade(neck, 'bottle')
    c.fill(c.R(7, 1, 7, 4) & body, MAT['bottle'][0])
    label = c.R(3, 1, 5, 4)
    c.fill(label, MAT['cream'][0])
    c.fill(c.R(3, 4, 5, 4), MAT['cream'][1])
    c.px(4, 2, MAT['red'][0])
    c.fill(c.R(10, 2, 10, 3), MAT['gold'][0])
    c.fill(c.R(2, 1, 2, 1), MAT['bottle'][2])
    c.outline()
    return c, (5, 2), (10, 2)


def brick():
    c = Canvas(10, 7)
    front = c.R(1, 2, 8, 5)
    c.shade(front, 'brick', light=False)
    top = c.R(1, 1, 8, 1)
    c.fill(top, MAT['brick'][2])
    for x, y in [(3, 3), (6, 4), (4, 5), (7, 2)]:
        c.px(x, y, MAT['brick'][1])
    c.px(2, 3, hexc('#d88a6a'))
    c.outline()
    return c, (4, 3), (8, 3)


def fish():
    c = Canvas(16, 8)
    body = c.E(4, 1, 14, 6)
    c.ball(body, 'fish', spec=False)
    c.fill(c.R(5, 2, 12, 2) & body, MAT['fish'][2])
    tail = c.P([(1, 1), (4, 3), (4, 4), (1, 6), (2, 4), (2, 3)])
    c.shade(tail, 'fish')
    fin = c.P([(7, 1), (10, 0), (11, 1)])
    c.fill(fin & ~body, MAT['fish'][1])
    c.px(12, 3, INK)
    c.px(10, 3, MAT['fish'][1])
    c.px(10, 4, MAT['fish'][1])
    c.fill(c.R(6, 5, 11, 5) & body, MAT['fish'][1])
    c.outline()
    return c, (8, 4), (14, 4)


def tire():
    c = Canvas(18, 18)
    outer = c.C(9, 9, 8)
    hub = c.C(9, 9, 4.2)
    c.fill(outer, MAT['black'][0])
    rim_l = outer & ~c.C(9, 9, 7.0)
    c.fill(rim_l, MAT['black'][1])
    # tread notches around the rim
    import math
    for i in range(12):
        a = i * math.pi / 6
        x = int(round(9 + 7.4 * math.cos(a) - 0.5))
        y = int(round(9 + 7.4 * math.sin(a) - 0.5))
        c.px(x, y, MAT['charcoal'][0])
    hi = outer & c.ring(9, 9, 7.0, 5.6) & (c.xx + c.yy < 13)
    c.fill(hi, MAT['charcoal'][2])
    c.fill(c.C(9, 9, 5.0) & ~hub, MAT['black'][1])
    c.ball(hub, 'steel')
    c.fill(c.C(9, 9, 1.5), MAT['iron'][1])
    for x, y in [(9, 6), (12, 9), (9, 11), (6, 8)]:
        c.px(x, y, MAT['iron'][0])
    c.outline()
    return c, (9, 9), (16, 9)


def road_sign():
    from pixlib import micro_width
    c = Canvas(44, 14)
    post = c.R(1, 6, 16, 7)
    c.shade(post, 'steel', light=False)
    c.fill(c.R(1, 6, 15, 6), MAT['steel'][2])
    for x in (3, 5, 7):
        c.px(x, 7, MAT['steel'][1])
    face = c.R(15, 1, 42, 12)
    c.shade(face, 'orange', light_w=1)
    tw = micro_width('DETOUR')
    tx = 15 + (28 - tw + 1) // 2
    c.text('DETOUR', tx, 2, INK, micro=True)
    c.fill(c.R(19, 9, 34, 9), INK)
    c.fill(c.R(32, 8, 33, 8) | c.R(32, 10, 33, 10), INK)
    c.px(32, 7, INK)
    c.px(32, 11, INK)
    # bolts
    c.px(17, 2, MAT['steel'][2])
    c.px(40, 2, MAT['steel'][2])
    c.outline()
    return c, (4, 6), (42, 7)


WEAPONS = {
    'wrench': wrench, 'baton': baton, 'bat': bat, 'pipe': pipe, 'broom': broom,
    'chain': chain, 'belt': belt, 'newspaper': newspaper, 'spatula': spatula,
    'bottle': bottle, 'brick': brick, 'fish': fish, 'tire': tire, 'road_sign': road_sign,
}
