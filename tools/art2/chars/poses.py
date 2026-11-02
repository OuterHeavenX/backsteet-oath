"""Animation tables for the v2 characters.

Poses are authored for the 'normal' body (world units, facing +x, anchor at the
ground between the feet). The frame lists here are the *design* of the
animation: anticipation -> contact -> follow-through -> recovery for attacks,
distance-planted walk/run cycles, spring-driven secondary motion.
"""
import math

from rig import P, solve, body_for, NORMAL

GUARD = dict(hip=(-0.3, -16.9), lean=6.0, twist=0.1, hn=(7.4, -28.6), hf=(12.2, -33.2),
             fn=(5.6, 0.0), ff=(-5.2, 0.0), toe_f=8.0, expr='fight', tilt=-3.0, wang=-58.0)
RELAX = dict(hip=(0.0, -17.6), lean=3.0, twist=0.15, tilt=0.0, hn=(3.2, -16.9), hf=(-0.4, -17.5),
             hand_n='relax', hand_f='relax', fn=(3.4, 0.0), ff=(-3.0, 0.0), toe_f=0.0, expr='normal',
             eb_n='back', eb_f='back', wang=70.0)


def G(**kw):
    d = dict(GUARD)
    d.update(kw)
    return P(**d)


def Rx(**kw):
    d = dict(RELAX)
    d.update(kw)
    return P(**d)


def smooth(u):
    return u * u * (3 - 2 * u)


# ----------------------------------------------------------------------------- locomotion

def cycle(n, stride, beta, lift, lean, mode, expr, run=False, base=None, toe_bias=0.0, sway=0.0, roll=0.0,
          twist_amp=None):
    """Distance-planted locomotion cycle.

    Each foot is planted for `beta` of the cycle and moves back at exactly the
    body speed (stride/n per frame), so the planted foot is fixed in the world.
    mode picks the arm action (hero/brawler/heavy/flanker/blocker/weapon/thrower/civ/carry)."""
    base = dict(base or GUARD)
    A = beta * stride / 2.0
    frames, vels = [], []
    stand = NORMAL['thigh'] + NORMAL['shin'] + NORMAL['ankle']
    for i in range(n):
        ph = i / n
        feet = {}
        for side, off in (('n', 0.0), ('f', 0.5)):
            phi = (ph + off) % 1.0
            if phi < beta:
                x = A - phi * stride
                y = 0.0
                prog = phi / beta
                toe = -12.0 * (1 - prog) ** 3 + (26.0 if run else 16.0) * max(0.0, prog - 0.6) / 0.4 + toe_bias * prog
                lifted = False
            else:
                u = (phi - beta) / (1 - beta)
                x = -A + 2 * A * smooth(u)
                if run:
                    x -= 5.0 * math.sin(math.pi * u) * (1 - u)          # heel kick behind
                    y = -(1.2 + lift * math.sin(math.pi * min(1.0, u * 1.1)) ** 0.85)
                    toe = 48.0 * (1 - u) - 8.0 * u
                else:
                    y = -lift * math.sin(math.pi * u) ** 1.2
                    toe = 18.0 * (1 - u) - 10.0 * u + toe_bias * 0.5
                lifted = True
            feet[side] = (x, y, toe, lifted)
        hx = sway * math.sin(2 * math.pi * ph)
        hy = -stand * (0.965 if not run else 0.915)
        planted = [f for f in feet.values() if not f[3]]
        for (x, y, toe, _) in planted:
            dx = x - hx
            reach = math.sqrt(max((NORMAL['thigh'] + NORMAL['shin']) ** 2 * 0.985 - dx * dx, 1.0)) + NORMAL['ankle']
            hy = max(hy, -reach)
        hy += roll * (0.5 + 0.5 * math.cos(4 * math.pi * ph))
        if run:
            if not planted:
                hy -= 1.6
            else:
                for side in ('n', 'f'):
                    phi = (ph + (0.0 if side == 'n' else 0.5)) % 1.0
                    if phi < beta:
                        hy += 1.5 * math.sin(math.pi * phi / beta)
        s_n = -math.cos(2 * math.pi * ph)          # near arm forward when near leg is back
        s_f = -s_n
        ta = twist_amp if twist_amp is not None else 0.24
        kw = dict(base)
        kw.update(hand_n='fist', hand_f='fist')
        if mode == 'carry':
            kw.update(hn=(2.0, -49.8 + 0.3 * s_n), hf=(5.4, -49.4 + 0.3 * s_f), hand_n='open', hand_f='open',
                      eb_n='back', eb_f='fwd', twist=0.0, expr='effort', near_arm_back=True)
        elif run:
            kw.update(hn=(2.0 + 9.0 * s_n, -25.0 - 5.0 * s_n), hf=(1.5 + 8.4 * s_f, -25.6 - 4.8 * s_f),
                      twist=0.4 * s_f, ptwist=-0.34 * s_f, eb_n='down', eb_f='down')
        elif mode == 'civ':
            kw.update(hn=(2.4 + 4.6 * s_n, -17.2 - 0.9 * abs(s_n)), hf=(0.2 + 4.2 * s_f, -17.8 - 0.8 * abs(s_f)),
                      hand_n='relax', hand_f='relax', twist=0.18 * s_f, ptwist=-0.2 * s_f, eb_n='back', eb_f='back')
        elif mode == 'heavy':
            kw.update(hn=(5.6 + (3.6 if s_n > 0 else 2.4) * s_n, -23.6 - 1.2 * max(s_n, 0)),
                      hf=(7.2 + (3.4 if s_f > 0 else 2.2) * s_f, -24.6 - 1.2 * max(s_f, 0)),
                      twist=0.34 * s_f, ptwist=-0.3 * s_f, eb_n='down', eb_f='down')
        elif mode == 'flanker':
            kw.update(hn=(8.0 + 2.2 * s_n, -27.0 - 0.9 * abs(s_n)), hf=(12.0 + 2.0 * s_f, -29.4 - 0.8 * abs(s_f)),
                      twist=0.2 * s_f, ptwist=-0.2 * s_f, eb_n='down', eb_f='down')
        elif mode == 'blocker':
            kw.update(hn=(8.4 + 0.6 * s_n, -34.2 + 0.3 * s_n), hf=(10.6 + 0.6 * s_f, -36.4 + 0.3 * s_f),
                      twist=0.12 * s_f, ptwist=-0.18 * s_f, eb_n='down', eb_f='down')
        elif mode == 'weapon':
            kw.update(hn=(6.2 + 1.6 * s_n, -25.2 - 0.6 * max(s_n, 0)), wang=-42.0 + 10.0 * s_n,
                      hf=(3.0 + (4.4 if s_f > 0 else 2.4) * s_f, -21.6 - 1.6 * max(s_f, 0)), hand_f='fist',
                      twist=0.22 * s_f, ptwist=-0.26 * s_f, eb_n='down', eb_f='back')
        elif mode == 'thrower':
            kw.update(hn=(5.4 + 0.8 * s_n, -28.6 + 0.4 * s_n), hand_n='open',
                      hf=(3.0 + (4.4 if s_f > 0 else 2.4) * s_f, -21.6 - 1.6 * max(s_f, 0)),
                      twist=0.22 * s_f, ptwist=-0.26 * s_f, eb_n='down', eb_f='back')
        else:   # hero / brawler
            k = 1.25 if mode == 'brawler' else 1.0
            sw_n = 4.6 * k * s_n if s_n > 0 else 2.6 * k * s_n
            sw_f = 4.4 * k * s_f if s_f > 0 else 2.4 * k * s_f
            kw.update(hn=(3.6 + sw_n, -21.0 - 1.6 * max(s_n, 0)), hf=(3.0 + sw_f, -21.6 - 1.6 * max(s_f, 0)),
                      twist=ta * s_f, ptwist=-0.28 * s_f, eb_n='back', eb_f='back')
        kw.update(hip=(hx, hy), fn=feet['n'][:2], ff=feet['f'][:2], toe_n=feet['n'][2], toe_f=feet['f'][2],
                  lift_n=feet['n'][3], lift_f=feet['f'][3], expr=expr, lean=lean + (2.0 * math.sin(4 * math.pi * ph) if roll else 0.0),
                  tilt=base.get('tilt', -2.0) * 0.5 - 1.0 + 1.2 * math.sin(4 * math.pi * ph))
        frames.append(P(**kw))
        vels.append((stride / n, 0.0))
    return frames, vels


STYLE_BASE = {
    'hero': GUARD,
    'brawler': dict(GUARD, hip=(-0.4, -16.6), lean=8.0, twist=0.2, hn=(7.8, -27.0), hf=(12.6, -30.6), fn=(6.0, 0.0),
                    ff=(-5.6, 0.0), toe_f=6.0, tilt=-4.0),
    'heavy': dict(GUARD, hip=(-0.6, -15.6), lean=11.0, twist=0.15, hn=(9.0, -25.2), hf=(13.2, -27.4), fn=(7.0, 0.0),
                  ff=(-6.6, 0.0), toe_f=0.0, tilt=-5.0),
    'flanker': dict(GUARD, hip=(-0.8, -15.3), lean=13.0, twist=0.3, hn=(9.0, -27.2), hf=(13.4, -29.8), fn=(6.4, 0.0),
                    ff=(-6.0, 0.0), toe_f=26.0, tilt=-6.0),
    'blocker': dict(GUARD, hip=(-0.4, -16.4), lean=9.0, twist=0.0, hn=(8.6, -34.6), hf=(10.8, -36.8), fn=(5.0, 0.0),
                    ff=(-5.4, 0.0), toe_f=4.0, tilt=-9.0),
    'weapon': dict(GUARD, hip=(-0.6, -16.6), lean=6.0, twist=0.45, hn=(7.0, -27.6), hf=(12.0, -29.6), hand_f='open',
                   fn=(6.0, 0.0), ff=(-5.6, 0.0), toe_f=6.0, tilt=-3.0, wang=-118.0),
    'thrower': dict(GUARD, hip=(-0.6, -16.8), lean=5.0, twist=0.35, hn=(6.4, -27.2), hand_n='open', hf=(11.6, -28.6),
                    hand_f='open', fn=(5.6, 0.0), ff=(-5.4, 0.0), toe_f=10.0, tilt=-2.0, wang=-60.0),
}
# locomotion per style: walk (stride, beta, lift, lean, toe_bias, sway, roll, twist), run (stride, lean, lift)
STYLE_WALK = {
    'hero': (38.0, 0.60, 3.2, 7.0, 0.0, 0.0, 0.0, 0.24), 'brawler': (36.0, 0.60, 3.0, 5.0, 0.0, 0.0, 0.0, 0.36),
    'heavy': (30.0, 0.64, 2.4, 10.0, 0.0, 0.7, 0.7, 0.34), 'flanker': (42.0, 0.55, 4.4, 12.0, 14.0, 0.0, 0.0, 0.2),
    'blocker': (32.0, 0.62, 2.6, 8.0, 0.0, 0.0, 0.0, 0.12), 'weapon': (36.0, 0.60, 3.0, 6.0, 0.0, 0.0, 0.0, 0.22),
    'thrower': (36.0, 0.60, 3.0, 5.0, 0.0, 0.0, 0.0, 0.22),
}
STYLE_RUN = {'hero': (62.0, 22.0, 9.5), 'brawler': (60.0, 21.0, 9.0), 'heavy': (54.0, 17.0, 7.5),
             'flanker': (68.0, 25.0, 10.5), 'blocker': (58.0, 20.0, 8.5), 'weapon': (60.0, 21.0, 9.0),
             'thrower': (60.0, 21.0, 9.0)}


def idle_frames(style, base):
    fr, vel = [], []
    hx, hy = base['hip']
    nx, ny = base['hn']
    fx, fy = base['hf']
    for i in range(6):
        th = 2 * math.pi * i / 6
        s1 = math.sin(th)
        d = dict(base)
        if style == 'heavy':
            d.update(hip=(hx + 0.2 * s1, hy + 0.55 * s1), lean=base['lean'] + 1.5 * math.sin(th - 0.5),
                     hn=(nx, ny + 0.9 * math.sin(th - 0.6)), hf=(fx + 0.3 * s1, fy + 0.8 * math.sin(th - 0.8)),
                     tilt=base['tilt'] + 1.3 * math.sin(th - 1.0))
        elif style == 'flanker':
            b = abs(math.sin(th))
            d.update(hip=(hx, hy - 0.9 * b + 0.25), toe_f=base['toe_f'] + 12 * b, toe_n=7 * b,
                     hn=(nx, ny - 0.9 * b), hf=(fx + 0.4 * s1, fy - 0.8 * b), tilt=base['tilt'] + 0.8 * s1)
        elif style == 'blocker':
            d.update(hip=(hx, hy + 0.25 * s1), hn=(nx, ny + 0.3 * math.sin(th - 0.6)), hf=(fx, fy + 0.3 * math.sin(th - 0.8)),
                     tilt=base['tilt'] + 0.4 * s1, lean=base['lean'] + 0.4 * s1)
        elif style == 'weapon':
            d.update(hip=(hx, hy + 0.35 * s1), hn=(nx, ny + 0.6 * math.sin(th - 0.4)), wang=base['wang'] + 9.0 * s1,
                     hf=(fx + 0.3 * s1, fy + 0.5 * math.sin(th - 0.8)), tilt=base['tilt'] + 0.8 * math.sin(th - 1.1))
        elif style == 'thrower':
            toss = max(0.0, s1)
            d.update(hip=(hx, hy + 0.3 * s1), hn=(nx, ny - 3.4 * toss), hf=(fx, fy + 0.4 * math.sin(th - 0.8)),
                     tilt=base['tilt'] - 2.0 * toss)
        elif style == 'brawler':
            d.update(hip=(hx + 0.45 * s1, hy + 0.35 * s1), twist=base['twist'] + 0.16 * s1,
                     hn=(nx, ny + 0.5 * math.sin(th - 0.7)), hf=(fx + 0.3 * s1, fy + 0.5 * math.sin(th - 0.9)),
                     tilt=base['tilt'] + 0.9 * math.sin(th - 1.1))
        else:
            d.update(hip=(hx + 0.25 * s1, hy + 0.38 * s1), lean=base['lean'] + 0.7 * math.sin(th - 0.4),
                     hn=(nx, ny + 0.55 * math.sin(th - 0.7)), hf=(fx + 0.2 * s1, fy + 0.5 * math.sin(th - 0.9)),
                     tilt=base['tilt'] + 0.9 * math.sin(th - 1.1))
        d['blink'] = (i == 4)
        fr.append(P(**d))
        vel.append((0.0, 0.35 * math.cos(th)))
    fps = {'heavy': 6, 'flanker': 10, 'thrower': 8}.get(style, 8)
    return dict(frames=fr, fps=fps, loop=True, vel=vel)


def guard_frames(style, G):
    if style == 'heavy':
        return [G(hip=(-0.8, -15.4), lean=12, hn=(9.6, -32.0), hf=(12.4, -34.0), expr='effort', tilt=-8),
                G(hip=(-1.0, -15.0), lean=13, hn=(9.4, -33.6), hf=(12.2, -35.6), expr='effort', tilt=-11)]
    if style == 'blocker':
        return [G(hip=(-0.6, -15.8), lean=11, hn=(8.6, -36.2), hf=(10.0, -38.0), expr='effort', tilt=-12),
                G(hip=(-0.8, -15.2), lean=14, hn=(8.4, -37.0), hf=(9.8, -38.8), expr='effort', tilt=-15)]
    if style == 'flanker':
        return [G(hip=(-1.2, -15.8), lean=6, hn=(8.0, -34.6), hf=(10.0, -37.0), toe_f=30, expr='effort', tilt=-8),
                G(hip=(-1.6, -15.6), lean=3, hn=(7.8, -35.4), hf=(9.6, -37.8), toe_f=34, expr='effort', tilt=-10)]
    if style == 'weapon':
        return [G(hip=(-0.6, -16.2), lean=8, hn=(8.6, -35.0), wang=-20, hf=(12.4, -34.6), hand_f='open', expr='effort'),
                G(hip=(-0.8, -15.8), lean=9, hn=(9.0, -36.4), wang=-8, hf=(12.8, -36.0), hand_f='open', expr='effort',
                  tilt=-8)]
    return [G(hip=(-0.6, -16.4), lean=8, hn=(8.6, -34.0), hf=(10.2, -36.4), expr='effort', tilt=-6),
            G(hip=(-0.8, -15.8), lean=10, tilt=-10, hn=(8.2, -35.6), hf=(10.0, -38.2), expr='effort')]


def signature(sig, base, G):
    """Boss / signature idle (6) + victory (4) overrides."""
    out = {}
    T = [2 * math.pi * i / 6 for i in range(6)]
    if sig == 'duke':
        out['idle'] = [G(hip=(-0.5, -16.2 + 0.5 * math.sin(t)), lean=5 + 1.2 * math.sin(t - 0.5), tilt=-9,
                         hn=(7.6, -22.6 + 0.6 * math.sin(t)), wang=86 + 8 * math.sin(t), eb_n='back',
                         hf=(11.2, -28.6 + 1.2 * max(0.0, math.sin(2 * t))), fn=(6.8, 0), ff=(-6.6, 0), toe_f=0,
                         blink=(i == 4)) for i, t in enumerate(T)]
        out['victory'] = [G(hn=(6.0, -22.0), hf=(8.0, -23.0), expr='grin', lean=4),
                          G(hn=(12.4, -40.6), hf=(-9.6, -37.0), eb_n='down', eb_f='down', expr='shout', lean=-2, tilt=-8,
                            hip=(0.0, -17.2), wang=-90),
                          G(hn=(12.6, -41.4), hf=(-9.8, -37.6), eb_n='down', eb_f='down', expr='shout', lean=-3, tilt=-9,
                            hip=(0.0, -17.4), wang=-90),
                          G(hn=(11.0, -35.0), hf=(-5.0, -33.0), eb_n='down', eb_f='down', expr='grin', lean=0, wang=-80)]
    elif sig == 'otto':
        out['idle'] = [G(hip=(-0.6, -15.0 + 0.6 * math.sin(t)), lean=18 + 1.5 * math.sin(t - 0.5), tilt=-16,
                         hn=(10.6, -15.8 + 0.6 * math.sin(t)), hf=(13.6, -16.6 + 0.6 * math.sin(t - 0.7)), eb_n='back',
                         eb_f='back', fn=(7.4, 0), ff=(-7.0, 0), toe_f=0, blink=(i == 4)) for i, t in enumerate(T)]
        out['victory'] = [G(hn=(6.0, -24.0), hf=(12.0, -30.0), hand_f='open', expr='fight'),
                          G(hn=(12.6, -31.0), hf=(13.4, -30.0), hand_f='open', expr='shout', hip=(0.0, -17.0)),
                          G(hn=(12.8, -31.4), hf=(13.6, -30.4), hand_f='open', expr='shout', hip=(0.0, -17.4)),
                          G(hn=(13.0, -30.0), hf=(-7.0, -30.0), hand_n='open', hand_f='open', eb_f='down', expr='grin')]
    elif sig == 'sergeant':
        out['idle'] = [G(hip=(-0.4, -16.0 + 0.3 * math.sin(t)), tilt=-12 + 16 * max(0.0, math.sin(t)) - 4,
                         hn=(5.0, -21.0), hf=(8.0, -22.0), eb_n='back', eb_f='back', fn=(6.6, 0), ff=(-6.2, 0),
                         toe_f=0, blink=(i == 4)) for i, t in enumerate(T)]
        up = dict(hip=(0.0, -17.6), lean=0, fn=(3.4, 0), ff=(-3.0, 0), toe_f=0, tilt=-6)
        out['victory'] = [G(hn=(5.0, -21.0), hf=(1.0, -18.0), hand_f='relax', **up),
                          G(hn=(8.6, -41.4), hand_n='open', eb_n='down', hf=(1.0, -18.0), hand_f='relax', expr='normal', **up),
                          G(hn=(8.6, -41.6), hand_n='open', eb_n='down', hf=(1.0, -18.0), hand_f='relax', expr='normal', **up),
                          G(hn=(7.0, -30.0), hf=(1.0, -18.0), hand_f='relax', expr='grin', **up)]
    elif sig == 'jett':
        out['idle'] = []
        for i, t in enumerate(T):
            b = abs(math.sin(t))
            out['idle'].append(G(hip=(-0.8, -15.3 - 0.9 * b + 0.25), lean=11, toe_f=28 + 10 * b, toe_n=6 * b,
                                 hn=(11.6 - (1.4 if i % 3 == 1 else 0.0), -27.4 - 0.6 * b),
                                 hand_n='open' if i % 3 != 2 else 'relax', hf=(6.0, -26.6 - 0.6 * b), tilt=-4,
                                 expr='normal', blink=(i == 4)))
        out['victory'] = [G(expr='normal'),
                          G(hn=(17.0, -35.0), hand_n='point', eb_n='down', hf=(-1.0, -23.0), eb_f='back', expr='grin',
                            lean=0, tilt=-6, hip=(0.0, -17.4)),
                          G(hn=(17.2, -35.4), hand_n='point', eb_n='down', hf=(-1.0, -23.0), eb_f='back', expr='grin',
                            lean=-2, tilt=-8, hip=(0.0, -17.5)),
                          G(hn=(15.0, -33.0), hand_n='point', eb_n='down', hf=(-1.0, -23.0), eb_f='back', expr='normal',
                            lean=0, hip=(0.0, -17.4))]
    elif sig == 'rhea':
        out['idle'] = [G(hip=(0.0, -17.2 + 0.3 * math.sin(t)), lean=2, tilt=-6, hn=(7.6, -29.0 + 0.3 * math.sin(t)),
                         wang=92, eb_n='down', hf=(-1.2, -22.6), eb_f='back', fn=(4.8, 0), ff=(-4.6, 0), toe_f=0,
                         expr='normal', blink=(i == 4)) for i, t in enumerate(T)]
        out['victory'] = [out['idle'][0],
                          G(hip=(0.0, -17.4), lean=-1, tilt=-8, hn=(3.8, -33.0), wang=-150, eb_n='down', hf=(-1.0, -23.0),
                            eb_f='back', fn=(4.8, 0), ff=(-4.6, 0), toe_f=0, expr='grin'),
                          G(hip=(0.0, -17.5), lean=-2, tilt=-9, hn=(3.8, -33.2), wang=-150, eb_n='down', hf=(-1.0, -23.0),
                            eb_f='back', fn=(4.8, 0), ff=(-4.6, 0), toe_f=0, expr='grin'),
                          G(hip=(0.0, -17.4), lean=0, tilt=-6, hn=(3.8, -33.0), wang=-150, eb_n='down', hf=(-1.0, -23.0),
                            eb_f='back', fn=(4.8, 0), ff=(-4.6, 0), toe_f=0, expr='normal')]
    elif sig == 'lou':
        out['idle'] = []
        for i, t in enumerate(T):
            b = abs(math.sin(t))
            toss = max(0.0, math.sin(t))
            out['idle'].append(G(hip=(-0.4, -16.6 - 0.7 * b + 0.2), lean=5, toe_f=14 + 8 * b, hn=(6.2, -27.2 - 3.0 * toss),
                                 hand_n='open', hf=(-1.0, -22.4), eb_f='back', tilt=-3 - 2 * toss, expr='normal',
                                 blink=(i == 4)))
        hips = dict(hn=(3.2, -21.6), hf=(-1.4, -22.0), eb_n='back', eb_f='back')
        out['victory'] = [G(expr='grin', **hips), G(lean=-8, tilt=-14, expr='happy', hip=(0.0, -17.4), **hips),
                          G(lean=-10, tilt=-16, expr='happy', hip=(0.0, -17.6), **hips),
                          G(lean=-6, tilt=-10, expr='grin', hip=(0.0, -17.4), **hips)]
    elif sig == 'sabine':
        out['idle'] = [G(hip=(0.0, -17.4), lean=2, tilt=-7, hn=(8.6, -27.0 + 0.8 * max(0.0, math.sin(t))),
                         wang=-15 + 12 * math.sin(t), hf=(11.6, -26.0), hand_f='open', fn=(4.4, 0), ff=(-4.6, 0),
                         toe_f=0, expr='normal', blink=(i == 4)) for i, t in enumerate(T)]
        bk = dict(hip=(0.0, -17.7), lean=0, tilt=-8, hn=(-3.2, -21.5), hf=(-4.0, -21.0), near_arm_under=True,
                  wang=120, fn=(3.4, 0), ff=(-3.2, 0), toe_f=0, expr='normal', eb_n='down', eb_f='down')
        out['victory'] = [out['idle'][0], G(**bk), G(**dict(bk, blink=True)), G(**dict(bk, tilt=-10))]
    elif sig == 'rook':
        out['idle'] = [G(hip=(0.0, -17.5 + 0.2 * math.sin(t)), lean=1, tilt=-5, hn=(6.4 + 0.5 * math.sin(t), -24.6),
                         hand_n='open', hf=(7.6, -25.4), fn=(4.0, 0), ff=(-4.4, 0), toe_f=0, expr='normal',
                         blink=(i == 4)) for i, t in enumerate(T)]
        out['victory'] = [out['idle'][0],
                          G(hip=(0.0, -17.6), lean=0, tilt=-6, hn=(5.8, -33.6), hand_n='open', hf=(-1.0, -20.0),
                            hand_f='relax', eb_f='back', fn=(4.0, 0), ff=(-4.4, 0), toe_f=0, expr='normal'),
                          G(hip=(0.0, -17.6), lean=0, tilt=-7, hn=(5.8, -33.8), hand_n='open', hf=(-1.0, -20.0),
                            hand_f='relax', eb_f='back', fn=(4.0, 0), ff=(-4.4, 0), toe_f=0, expr='smile'),
                          G(hip=(0.0, -17.6), lean=0, tilt=-5, hn=(5.5, -32.6), hand_n='open', hf=(-1.0, -20.0),
                            hand_f='relax', eb_f='back', fn=(4.0, 0), ff=(-4.4, 0), toe_f=0, expr='smile')]
    elif sig == 'kowal':
        out['idle'] = [G(hip=(-0.4, -17.0 + 0.3 * math.sin(t)), lean=10 + 0.8 * math.sin(t - 0.5), twist=0.1, tilt=-4,
                         hn=(10.4, -31.4 + 0.3 * math.sin(t)), hf=(10.0, -33.4 + 0.3 * math.sin(t)), wang=100,
                         eb_n='down', eb_f='down', fn=(3.6, 0), ff=(-4.6, 0), toe_f=0, expr='normal', blink=(i == 4))
                       for i, t in enumerate(T)]
        out['victory'] = [out['idle'][0],
                          G(hip=(0.0, -17.6), lean=-4, tilt=-10, hn=(5.6, -47.0), hf=(-1.6, -46.0), wang=-15,
                            eb_n='back', eb_f='back', near_arm_back=True, fn=(4.6, 0), ff=(-4.6, 0), toe_f=0, expr='shout'),
                          G(hip=(0.0, -17.8), lean=-5, tilt=-11, hn=(5.8, -47.6), hf=(-1.4, -46.6), wang=-18,
                            eb_n='back', eb_f='back', near_arm_back=True, fn=(4.6, 0), ff=(-4.6, 0), toe_f=0, expr='shout'),
                          G(hip=(0.0, -17.6), lean=-2, tilt=-8, hn=(5.4, -46.0), hf=(-1.6, -45.0), wang=-12,
                            eb_n='back', eb_f='back', near_arm_back=True, fn=(4.6, 0), ff=(-4.6, 0), toe_f=0, expr='grin')]
    elif sig == 'mae':
        out['idle'] = []
        for i, t in enumerate(T):
            b = abs(math.sin(t))
            out['idle'].append(G(hip=(-0.5, -16.2 - 1.0 * b + 0.3), lean=8, toe_f=18 + 12 * b, toe_n=8 * b,
                                 hn=(8.0, -31.6 - 0.8 * b), hf=(12.6, -34.0 - 0.8 * b), tilt=-6, expr='fight',
                                 blink=(i == 4)))
        out['victory'] = [G(expr='grin'),
                          G(hip=(0.0, -17.8), lean=-3, tilt=-8, hn=(11.6, -44.0), hf=(-5.6, -46.0), eb_n='down',
                            eb_f='down', expr='happy'),
                          G(hip=(0.0, -18.0), lean=-4, tilt=-9, hn=(11.8, -44.8), hf=(-5.8, -46.8), eb_n='down',
                            eb_f='down', expr='happy'),
                          G(hip=(0.0, -17.6), lean=-1, tilt=-6, hn=(10.6, -40.0), hf=(-4.8, -42.0), eb_n='down',
                            eb_f='down', expr='grin')]
    elif sig == 'rook_p2':
        out['idle'] = [G(hip=(-0.8, -14.6 + 0.5 * math.sin(t)), lean=17 + 1.2 * math.sin(t - 0.5), tilt=-12,
                         hn=(11.6, -25.6 + 0.7 * math.sin(t)), hand_n='open', hf=(14.6, -28.6 + 0.6 * math.sin(t - 0.7)),
                         hand_f='open', fn=(6.8, 0), ff=(-6.6, 0), toe_f=8, expr='angry', blink=(i == 4))
                         for i, t in enumerate(T)]
        out['victory'] = [out['idle'][0],
                          G(hip=(0.0, -17.2), lean=-6, tilt=-12, hn=(13.0, -38.0), hf=(-8.0, -39.0), hand_n='open',
                            hand_f='open', eb_n='down', eb_f='down', expr='shout'),
                          G(hip=(0.0, -17.4), lean=-7, tilt=-14, hn=(13.2, -38.6), hf=(-8.2, -39.6), hand_n='open',
                            hand_f='open', eb_n='down', eb_f='down', expr='shout'),
                          G(hip=(0.0, -17.0), lean=-2, tilt=-8, hn=(11.0, -30.0), hf=(-6.0, -30.0), hand_n='open',
                            hand_f='open', eb_n='down', eb_f='down', expr='grin')]
    return out


# ----------------------------------------------------------------------------- fighter set

def fighter_anims(style='hero', sig=None):
    A = {}
    base = STYLE_BASE.get(style, GUARD)

    def G(**kw):
        d = dict(base)
        d.update(hand_n='fist', hand_f='fist')
        d.update(kw)
        return P(**d)

    A['idle'] = idle_frames(style, dict(base))
    ws, wb, wl, wlean, wtoe, wsway, wroll, wtw = STYLE_WALK.get(style, STYLE_WALK['hero'])
    fr, v = cycle(8, ws, wb, wl, wlean, style, 'normal', base=base, toe_bias=wtoe, sway=wsway, roll=wroll,
                  twist_amp=wtw)
    A['walk'] = dict(frames=fr, fps=12 if style == 'heavy' else 14, loop=True, stride=ws, vel=v)
    rs, rlean, rlift = STYLE_RUN.get(style, STYLE_RUN['hero'])
    fr, v = cycle(8, rs, 0.32, rlift, rlean, 'run', 'fight', run=True, base=base)
    A['run'] = dict(frames=fr, fps=18, loop=True, stride=rs, vel=v)

    A['jump'] = dict(frames=[
        G(hip=(-0.5, -13.4), lean=14, fn=(5.2, 0), ff=(-4.6, 0), toe_f=10, hn=(-2.5, -20.5), hf=(-0.5, -21.5),
          hand_n='open', hand_f='open', eb_n='back', eb_f='back', expr='effort', tilt=4),
        G(hip=(0.0, -17.8), lean=2, fn=(4.2, -7.5), ff=(-3.6, -5.2), toe_n=25, toe_f=35, lift_n=True, lift_f=True,
          hn=(6.0, -40.0), hf=(9.0, -38.5), hand_n='open', hand_f='open', expr='fight', tilt=-6),
        G(hip=(0.0, -17.6), lean=5, fn=(4.4, -2.4), ff=(-3.8, -3.2), toe_n=18, toe_f=24, lift_n=True, lift_f=True,
          hn=(10.5, -30.0), hf=(-5.5, -32.0), hand_n='open', hand_f='open', expr='fight'),
    ], fps=10, loop=False, vel=[(0, 2), (0, -7), (0, 6)])
    A['land'] = dict(frames=[
        G(hip=(0.0, -13.0), lean=15, fn=(5.4, 0), ff=(-5.2, 0), hn=(9.5, -24.0), hf=(11.5, -26.5),
          hand_n='open', hand_f='open', expr='effort', tilt=6),
        G(hip=(-0.2, -15.9), lean=8, hn=(8.0, -27.5), hf=(11.8, -31.5)),
    ], fps=12, loop=False, vel=[(0, 6), (0, -2)])

    # ---- jab (lead / far arm)
    A['punch_a'] = dict(frames=[
        G(hip=(-0.7, -16.7), lean=4, twist=0.0, hf=(9.6, -32.8), expr='fight'),
        G(hip=(0.7, -16.8), lean=11, twist=0.55, hf=(21.6, -31.6), hn=(7.0, -29.4), fn=(6.6, 0), head=(0.6, 0.2),
          expr='effort'),
        G(hip=(0.6, -16.8), lean=10, twist=0.45, hf=(19.6, -31.2), hn=(7.1, -29.2), fn=(6.6, 0), expr='effort'),
        G(hip=(0.1, -16.85), lean=7, twist=0.2, hf=(14.2, -32.6), fn=(6.0, 0)),
    ], contact=1, fps=15, vel=[(-0.4, 0), (1.6, 0), (0.3, 0), (0, 0)])

    # ---- cross (rear / near arm): coil, hips + shoulders drive through
    A['punch_b'] = dict(frames=[
        G(hip=(-0.9, -16.6), lean=4, twist=0.55, ptwist=0.3, hn=(4.6, -30.6), hf=(13.0, -33.2), toe_f=8, expr='fight'),
        G(hip=(1.0, -16.6), lean=13, twist=-0.85, ptwist=-0.6, hn=(22.4, -31.0), hf=(8.6, -33.8), toe_f=32,
          ff=(-4.6, 0), head=(0.8, 0.3), expr='effort', wang=-10),
        G(hip=(0.9, -16.6), lean=12, twist=-0.75, ptwist=-0.5, hn=(20.2, -30.6), hf=(8.8, -33.6), toe_f=28,
          ff=(-4.6, 0), expr='effort', wang=-15),
        G(hip=(0.2, -16.8), lean=8, twist=-0.2, hn=(11.0, -30.0), toe_f=12),
    ], contact=1, fps=15, vel=[(-0.5, 0), (1.8, 0), (0.4, 0), (0, 0)])

    # ---- uppercut finisher (near arm, dip and rise)
    A['punch_c'] = dict(frames=[
        G(hip=(-1.2, -14.6), lean=16, twist=0.6, ptwist=0.3, hn=(1.0, -21.2), hf=(11.0, -31.0), toe_f=0,
          expr='effort', tilt=4, wang=30),
        G(hip=(-1.1, -14.0), lean=18, twist=0.72, ptwist=0.35, hn=(0.0, -19.6), hf=(10.4, -31.4), expr='effort',
          tilt=5, wang=40),
        G(hip=(1.2, -17.7), lean=-2, twist=-0.9, ptwist=-0.6, hn=(15.6, -41.6), hf=(5.4, -30.2), toe_f=38,
          ff=(-4.2, 0), fn=(6.2, 0), expr='shout', tilt=-8, wang=-80),
        G(hip=(1.0, -18.0), lean=-4, twist=-0.8, ptwist=-0.5, hn=(14.0, -45.4), hf=(5.6, -30.0), toe_f=40,
          ff=(-4.2, 0), fn=(6.2, 0), expr='shout', tilt=-9, wang=-90),
        G(hip=(0.4, -16.7), lean=6, twist=-0.3, hn=(11.0, -36.0), toe_f=15, fn=(6.0, 0), wang=-70),
        G(),
    ], contact=2, fps=14, vel=[(-0.3, 1), (0, 0.5), (1.2, -2.5), (0.3, -0.8), (0, 1), (0, 0)])

    # ---- front kick (near leg): weight back, chamber, extend, re-chamber
    A['kick'] = dict(frames=[
        G(hip=(-1.6, -16.6), lean=-2, fn=(5.0, 0), ff=(-5.6, 0), expr='fight'),
        G(hip=(-1.8, -17.5), lean=-8, fn=(7.6, -10.6), toe_n=30, lift_n=True, ff=(-4.2, 0), toe_f=0,
          hf=(11.2, -34.0), hn=(5.0, -29.2), expr='effort'),
        G(hip=(-1.2, -17.7), lean=-16, fn=(20.6, -15.4), toe_n=-72, lift_n=True, ff=(-3.8, 0), toe_f=0,
          hf=(6.0, -36.4), hn=(-3.4, -27.0), hand_n='open', eb_n='down', expr='shout', tilt=2),
        G(hip=(-1.4, -17.4), lean=-8, fn=(8.2, -9.6), toe_n=20, lift_n=True, ff=(-4.0, 0), toe_f=0,
          hf=(10.0, -34.6), hn=(4.2, -28.8), expr='effort'),
        G(hip=(-0.6, -16.9), lean=4, fn=(5.8, 0)),
    ], contact=2, fps=14, vel=[(-0.5, 0), (0, -0.6), (1.0, 0), (0, 0.4), (0, 0)])

    # ---- roundhouse finisher (near leg, pivot on the base foot, lean back counterweight)
    A['kick_c'] = dict(frames=[
        G(hip=(-0.6, -16.4), lean=2, twist=-0.8, ptwist=-0.6, fn=(4.0, 0), toe_n=18, ff=(-5.0, 0),
          hn=(5.2, -32.0), hf=(8.4, -34.2), expr='effort'),
        G(hip=(-2.0, -17.6), lean=-14, twist=-0.6, ptwist=-0.5, fn=(5.6, -17.6), toe_n=40, lift_n=True,
          ff=(-3.6, 0), toe_f=14, hn=(-6.0, -30.0), hf=(8.4, -33.4), expr='effort', tilt=3),
        G(hip=(-3.0, -18.0), lean=-30, twist=-0.3, ptwist=-0.3, fn=(17.4, -30.6), toe_n=-18, lift_n=True,
          ff=(-3.0, 0), toe_f=18, hn=(-10.0, -28.6), hf=(6.0, -38.4), hand_n='open', expr='shout', tilt=8),
        G(hip=(-2.6, -17.8), lean=-26, twist=-0.3, fn=(17.0, -24.6), toe_n=0, lift_n=True, ff=(-3.0, 0),
          toe_f=14, hn=(-9.0, -27.2), hf=(7.0, -36.8), hand_n='open', expr='shout', tilt=6),
        G(hip=(-1.4, -17.2), lean=-10, fn=(6.2, -11.0), toe_n=30, lift_n=True, ff=(-4.0, 0), toe_f=0,
          hn=(2.0, -28.4), hf=(9.4, -33.0), expr='effort'),
        G(hip=(-0.4, -16.8), lean=5, fn=(5.8, 0)),
    ], contact=2, fps=14, vel=[(0, 0), (-1.5, -1), (2.5, -1.5), (2.0, 0), (0, 0.5), (0, 0)])

    A['jump_kick'] = dict(frames=[
        G(hip=(0.0, -17.5), lean=-4, fn=(7.0, -9.0), toe_n=30, ff=(-3.0, -7.0), toe_f=30, lift_n=True, lift_f=True,
          expr='effort'),
        G(hip=(-1.5, -17.8), lean=-22, fn=(19.0, -9.6), toe_n=-22, ff=(-2.4, -8.6), toe_f=40, lift_n=True,
          lift_f=True, hn=(-6.0, -32.0), hf=(4.0, -37.0), hand_n='open', expr='shout', tilt=4),
    ], contact=1, fps=12, vel=[(1, -2), (3, 0)])
    A['jump_punch'] = dict(frames=[
        G(hip=(0.0, -17.6), lean=2, twist=0.5, hn=(-3.0, -39.0), hf=(10.0, -31.0), fn=(5.0, -8.6), ff=(-4.0, -6.4),
          toe_n=30, toe_f=30, lift_n=True, lift_f=True, expr='effort', wang=-140, tilt=-4),
        G(hip=(0.5, -17.2), lean=14, twist=-0.9, ptwist=-0.4, hn=(20.6, -23.4), hf=(-6.0, -35.0), hand_f='open',
          eb_f='down', fn=(5.6, -10.4), ff=(-5.4, -7.6), toe_n=35, toe_f=55, lift_n=True, lift_f=True, expr='shout',
          tilt=2, wang=25),
    ], contact=1, fps=12, vel=[(1, -2), (3, 3)])
    A['run_punch'] = dict(frames=[
        G(hip=(0.0, -15.8), lean=22, hn=(-1.0, -24.0), hf=(10.0, -32.0), fn=(7.0, 0), ff=(-8.0, -3.0), toe_f=40,
          lift_f=True, expr='effort', wang=20),
        G(hip=(2.0, -15.4), lean=24, twist=-0.9, ptwist=-0.5, hn=(23.6, -28.6), hf=(3.0, -30.0), fn=(8.6, 0), toe_n=-5,
          ff=(-11.0, -2.6), toe_f=50, lift_f=True, expr='shout', wang=-5),
        G(hip=(1.0, -16.3), lean=14, twist=-0.3, hn=(14.0, -30.0), fn=(6.6, 0), ff=(-5.0, 0), toe_f=20, expr='fight'),
    ], contact=1, fps=14, vel=[(4, 0), (5, 0), (2, 0)])
    A['dropkick'] = dict(frames=[
        G(hip=(0.0, -17.5), lean=-20, fn=(6.0, -8.0), ff=(3.0, -9.0), toe_n=20, toe_f=20, lift_n=True, lift_f=True,
          hn=(-6.0, -36.0), hf=(-3.0, -38.0), hand_n='open', hand_f='open', expr='effort'),
        G(hip=(0.0, -15.0), lean=-75, fn=(17.0, -13.0), ff=(16.0, -17.2), toe_n=-60, toe_f=-60, lift_n=True,
          lift_f=True, hn=(-10.0, -18.0), hf=(-9.0, -22.0), hand_n='open', hand_f='open', expr='shout', tilt=-25),
        G(hip=(0.0, -14.5), lean=-55, fn=(12.0, -7.0), ff=(10.0, -10.0), toe_n=-30, toe_f=-30, lift_n=True,
          lift_f=True, hn=(-9.0, -24.0), hf=(-6.0, -30.0), hand_n='open', hand_f='open', expr='effort', tilt=-18),
    ], contact=1, fps=12, vel=[(2, -3), (5, 0), (2, 3)])

    A['guard'] = dict(frames=guard_frames(style, G), fps=12, loop=False, vel=[(0, 0), (0, 0.5)])

    # ---- hit reactions (direction + strength)
    A['hurt_high'] = dict(frames=[
        G(hip=(-2.4, -17.0), lean=-14, tilt=-22, head=(-1.0, 0.0), hn=(2.0, -22.0), hf=(-4.0, -33.0),
          hand_n='open', hand_f='open', fn=(4.6, 0), ff=(-6.6, 0), expr='pain', eb_f='down'),
        G(hip=(-3.0, -16.8), lean=-18, tilt=-26, head=(-1.2, 0.2), hn=(0.0, -20.0), hf=(-7.0, -30.0),
          hand_n='open', hand_f='open', fn=(4.6, 0), ff=(-6.6, 0), expr='pain'),
        G(hip=(-2.0, -16.6), lean=-6, tilt=-10, hn=(6.0, -27.0), hf=(9.0, -31.0), fn=(4.8, 0), ff=(-6.4, 0),
          expr='fight'),
    ], fps=12, loop=False, vel=[(-3, 0), (-1.5, 0), (0, 0)])
    A['hurt_low'] = dict(frames=[
        G(hip=(-2.0, -15.8), lean=30, tilt=20, hn=(5.6, -21.0), hf=(7.2, -20.4), fn=(4.6, 0), ff=(-6.0, 0),
          expr='pain_open', wang=60),
        G(hip=(-2.6, -15.2), lean=36, tilt=24, hn=(5.0, -19.8), hf=(6.6, -19.4), fn=(4.6, 0), ff=(-6.0, 0),
          expr='pain_open', wang=60),
        G(hip=(-1.5, -16.2), lean=18, tilt=10, hn=(6.4, -24.0), hf=(9.0, -27.0), fn=(4.8, 0), ff=(-5.8, 0),
          expr='pain'),
    ], fps=12, loop=False, vel=[(-2, 1), (-1, 0.5), (0, 0)])
    A['hurt_back'] = dict(frames=[
        G(hip=(2.6, -16.8), lean=22, tilt=-42, head=(-0.8, 0.4), hn=(-7.0, -34.0), hf=(-9.0, -38.0), hand_n='open',
          hand_f='open', eb_n='down', eb_f='down', fn=(8.6, 0), ff=(-4.0, -1.6), toe_f=40, lift_f=True,
          expr='pain_open'),
        G(hip=(3.6, -15.8), lean=27, tilt=-30, head=(-0.6, 0.3), hn=(-5.0, -30.0), hf=(-7.4, -34.0), hand_n='open',
          hand_f='open', eb_n='down', eb_f='down', fn=(10.0, 0), ff=(-2.4, -2.4), toe_f=45, lift_f=True, expr='pain'),
        G(hip=(1.6, -16.4), lean=12, tilt=-6, fn=(7.0, 0), ff=(-4.4, 0), expr='fight'),
    ], fps=12, loop=False, vel=[(3.5, 0), (2.0, 0), (0, 0)])
    KD = dict(tilt=-50, head=(0.0, -2.4))
    A['knockdown'] = dict(frames=[
        G(hip=(-1.5, -18.0), lean=-38, tilt=-20, fn=(6.0, -4.0), ff=(3.0, -6.0), toe_n=-10, toe_f=0, lift_n=True,
          lift_f=True, hn=(-2.0, -40.0), hf=(-6.0, -37.0), hand_n='open', hand_f='open', expr='pain'),
        G(hip=(0.0, -13.0), lean=-72, tilt=-24, fn=(12.0, -18.0), ff=(9.0, -21.0), toe_n=-30, toe_f=-30,
          lift_n=True, lift_f=True, hn=(-12.0, -20.0), hf=(-13.0, -16.0), hand_n='open', hand_f='open', expr='pain'),
        G(hip=(2.0, -4.8), lean=-88, fn=(12.0, -9.0), ff=(10.0, -11.0), toe_n=-30, toe_f=-30, lift_n=True,
          lift_f=True, hn=(-10.0, -9.0), hf=(-12.0, -7.0), hand_n='open', hand_f='open', expr='pain', **KD),
        G(hip=(2.0, -6.4), lean=-80, fn=(11.0, -12.0), ff=(9.0, -14.0), toe_n=-30, toe_f=-30, lift_n=True,
          lift_f=True, hn=(-8.0, -13.0), hf=(-10.0, -12.0), hand_n='open', hand_f='open', expr='ko',
          tilt=-46, head=(0.0, -2.2)),
        G(hip=(3.0, -4.6), lean=-90, fn=(15.6, -1.2), ff=(14.0, -1.6), toe_n=-80, toe_f=-70, lift_n=True,
          lift_f=True, hn=(-6.0, -3.6), hf=(-8.0, -2.6), hand_n='open', hand_f='open', expr='ko', **KD),
    ], fps=10, loop=False, vel=[(-3, -3), (-3, 0), (-1, 3), (0, -1), (0, 0)])
    A['getup'] = dict(frames=[
        G(hip=(1.0, -4.8), lean=-35, tilt=-12, hn=(-7.0, -2.0), hf=(-8.0, -3.0), hand_n='open', hand_f='open',
          eb_n='up', eb_f='up', fn=(11.0, -0.6), ff=(9.5, -0.8), toe_n=-50, toe_f=-40, lift_n=True, lift_f=True,
          expr='pain'),
        G(hip=(-1.0, -9.6), lean=25, fn=(5.0, 0), ff=(-7.4, -1.0), toe_f=70, lift_f=True, hn=(7.0, -12.0),
          hf=(4.0, -10.0), hand_n='open', hand_f='open', expr='fight', tilt=6),
        G(hip=(-0.5, -14.5), lean=16, fn=(5.0, 0), ff=(-5.0, 0), toe_f=20, hn=(8.0, -25.0), hf=(10.0, -27.0),
          expr='fight'),
        G(),
    ], fps=10, loop=False, vel=[(0, -1), (0, -2), (0, -1), (0, 0)])
    fr = []
    for i, (sx, ln, tl) in enumerate(((-1.2, 10, 8), (0.0, 13, 16), (1.2, 16, 22), (0.0, 13, 16))):
        fr.append(G(hip=(sx, -16.0), lean=ln, tilt=tl, hn=(4.0 + sx, -18.0), hf=(1.0 + sx, -19.0),
                    hand_n='relax', hand_f='relax', eb_n='back', eb_f='back', fn=(4.0, 0), ff=(-4.0, 0), toe_f=0,
                    expr='dizzy', wang=70))
    A['dizzy'] = dict(frames=fr, fps=6, loop=True, vel=[(-1, 0), (1, 0), (1, 0), (-1, 0)])

    A['pickup'] = dict(frames=[
        G(hip=(-1.0, -11.5), lean=32, fn=(5.5, 0), ff=(-4.5, 0), toe_f=25, hn=(11.0, -3.4), hf=(6.0, -12.0),
          hand_n='open', hand_f='open', tilt=15, wang=0),
        G(hip=(-0.8, -11.0), lean=34, fn=(5.5, 0), ff=(-4.5, 0), toe_f=25, hn=(11.5, -2.8), hf=(7.0, -11.0),
          hand_n='fist', hand_f='open', tilt=15, wang=0),
        G(hip=(-0.3, -15.8), lean=12, hn=(9.0, -20.0), hf=(6.0, -24.0), hand_f='open', wang=-30),
    ], fps=12, loop=False, vel=[(0, 2), (0, 0), (0, -2)])
    A['carry'] = dict(frames=[
        G(hip=(-0.3, -17.4), lean=-2, hn=(2.0, -50.0), hf=(5.4, -49.6), hand_n='open', hand_f='open',
          eb_n='back', eb_f='fwd', fn=(4.6, 0), ff=(-4.6, 0), toe_f=0, expr='effort', tilt=-6, twist=0.0,
          near_arm_back=True),
        G(hip=(-0.3, -17.0), lean=-1, hn=(2.0, -49.6), hf=(5.4, -49.2), hand_n='open', hand_f='open',
          eb_n='back', eb_f='fwd', fn=(4.6, 0), ff=(-4.6, 0), toe_f=0, expr='effort', tilt=-5, twist=0.0,
          near_arm_back=True),
    ], fps=4, loop=True, vel=[(0, 0.3), (0, -0.3)])
    fr, v = cycle(6, 26.0, 0.62, 2.4, 2.0, 'carry', 'effort', base=dict(GUARD, tilt=-8))
    A['carry_walk'] = dict(frames=fr, fps=10, loop=True, stride=26.0, vel=v)
    A['throw'] = dict(frames=[
        G(hip=(-1.5, -16.8), lean=-14, hn=(-4.0, -49.0), hf=(-2.0, -50.0), hand_n='open', hand_f='open',
          eb_n='back', eb_f='back', expr='effort', tilt=-8, near_arm_back=True),
        G(hip=(-0.5, -17.2), lean=-4, hn=(2.0, -51.0), hf=(5.0, -50.6), hand_n='open', hand_f='open',
          eb_n='back', eb_f='fwd', expr='effort', tilt=-6, near_arm_back=True),
        G(hip=(1.0, -16.8), lean=18, twist=-0.4, hn=(18.0, -36.0), hf=(19.0, -34.0), hand_n='open', hand_f='open',
          fn=(6.6, 0), ff=(-5.0, 0), toe_f=25, expr='shout'),
        G(hip=(0.8, -16.4), lean=22, twist=-0.3, hn=(15.0, -25.0), hf=(16.0, -23.0), hand_n='open', hand_f='open',
          fn=(6.6, 0), toe_f=20, expr='fight'),
    ], contact=2, fps=12, vel=[(-1, 0), (0, -1), (2, 0), (0.5, 0)])

    # ---- weapon swing (near hand grip), big wind-up and follow-through
    A['swing'] = dict(frames=[
        G(hip=(-1.2, -16.8), lean=-6, twist=0.6, ptwist=0.3, hn=(-3.0, -43.0), hf=(8.0, -32.0), eb_n='down',
          wang=-120, expr='effort', near_arm_back=True),
        G(hip=(-1.6, -16.6), lean=-10, twist=0.8, ptwist=0.4, hn=(-6.0, -44.6), hf=(8.4, -31.6), eb_n='down',
          wang=-152, expr='effort', near_arm_back=True),
        G(hip=(1.2, -16.4), lean=14, twist=-0.8, ptwist=-0.6, hn=(16.4, -33.0), hf=(4.0, -30.0), toe_f=30,
          ff=(-4.6, 0), wang=-8, expr='shout'),
        G(hip=(1.4, -16.2), lean=18, twist=-0.9, ptwist=-0.6, hn=(12.4, -19.4), hf=(4.6, -29.0), toe_f=28,
          ff=(-4.6, 0), wang=56, expr='effort'),
        G(hip=(0.4, -16.6), lean=8, twist=-0.3, hn=(8.4, -28.0), wang=-40, toe_f=12),
    ], contact=2, fps=14, vel=[(-0.5, 0), (-0.5, 0), (2.0, 0), (0.6, 0), (0, 0)])
    A['sweep'] = dict(frames=[
        G(hip=(-1.0, -9.2), lean=20, fn=(4.2, 0), ff=(-6.6, -1.0), toe_f=70, lift_f=True, hn=(6.0, -5.0),
          hf=(3.0, -6.0), hand_n='open', hand_f='open', expr='effort', tilt=8),
        G(hip=(-2.0, -8.6), lean=30, fn=(19.4, -1.6), toe_n=-15, lift_n=True, ff=(-5.0, -1.0), toe_f=70, lift_f=True,
          hn=(2.0, -3.0), hf=(-1.0, -4.0), hand_n='open', hand_f='open', expr='shout', tilt=10),
        G(hip=(-1.5, -8.8), lean=26, fn=(16.0, -2.6), toe_n=-10, lift_n=True, ff=(-5.0, -1.0), toe_f=70, lift_f=True,
          hn=(3.0, -3.4), hf=(0.0, -4.0), hand_n='open', hand_f='open', expr='effort', tilt=8),
        G(hip=(-0.5, -13.6), lean=14, fn=(5.0, 0), ff=(-5.0, 0), toe_f=20, hn=(7.0, -24.0), hf=(10.0, -27.0)),
    ], contact=1, fps=12, vel=[(0, 3), (0.5, 0), (0, 0), (0, -2)])
    A['rising_kick'] = dict(frames=[
        G(hip=(-1.0, -12.6), lean=16, fn=(5.0, 0), ff=(-5.0, 0), toe_f=15, hn=(7.0, -20.0), hf=(9.0, -22.0),
          expr='effort', tilt=6),
        G(hip=(-1.5, -17.8), lean=-6, fn=(6.0, -14.0), toe_n=30, lift_n=True, ff=(-4.0, 0), toe_f=0, expr='effort'),
        G(hip=(-2.5, -18.2), lean=-22, fn=(9.0, -33.0), toe_n=-62, lift_n=True, ff=(-3.5, 0), toe_f=20,
          hn=(-6.0, -28.0), hf=(10.0, -28.0), hand_n='open', expr='shout', tilt=-4),
        G(hip=(-1.0, -16.8), lean=6, fn=(6.0, 0)),
    ], contact=2, fps=13, vel=[(0, 2), (0, -3), (0.5, -3), (0, 2)])
    A['slam'] = dict(frames=[
        G(hip=(0.0, -18.0), lean=-8, hn=(3.0, -51.0), hf=(4.6, -50.4), eb_n='back', eb_f='fwd', fn=(4.0, -3.0),
          ff=(-4.0, -2.0), lift_n=True, lift_f=True, toe_n=20, toe_f=20, expr='shout', tilt=-10, near_arm_back=True),
        G(hip=(0.5, -11.5), lean=26, hn=(13.0, -8.0), hf=(14.0, -9.0), fn=(5.0, 0), ff=(-5.5, -1.0), toe_f=60,
          lift_f=True, expr='shout', tilt=8),
        G(hip=(0.4, -10.5), lean=30, hn=(13.0, -3.0), hf=(14.0, -3.5), fn=(5.0, 0), ff=(-5.5, -1.0), toe_f=60,
          lift_f=True, expr='effort', tilt=10),
    ], contact=1, fps=12, vel=[(0, -3), (1, 5), (0, 1)])

    A['victory'] = dict(frames=[
        G(hip=(-0.3, -17.2), lean=4, hn=(3.0, -20.0), hf=(6.0, -25.0), expr='grin', wang=60),
        G(hip=(0.0, -18.0), lean=-3, hn=(12.6, -41.0), hf=(4.0, -24.0), eb_n='down', hand_f='relax', expr='happy',
          tilt=-8, wang=-90),
        G(hip=(0.0, -18.1), lean=-4, hn=(12.9, -42.6), hf=(4.0, -24.4), eb_n='down', hand_f='relax', expr='happy',
          tilt=-9, wang=-90),
        G(hip=(-0.2, -17.6), lean=2, hn=(11.0, -36.0), hf=(4.0, -22.0), eb_n='down', hand_f='relax', expr='grin',
          wang=-80),
    ], fps=8, loop=False, vel=[(0, 1), (0, -3), (0, 0), (0, 1)])
    A['talk'] = dict(frames=talk_frames(), fps=6, loop=True, vel=[(0, 0)] * 4)
    A['cower'] = dict(frames=cower_frames(), fps=10, loop=True, vel=[(0.5, 0), (-0.5, 0), (0.3, 0)])
    if sig:
        ov = signature(sig, base, G)
        if 'idle' in ov:
            A['idle'] = dict(frames=ov['idle'], fps=7, loop=True, vel=[(0, 0.3 * math.cos(2 * math.pi * i / 6)) for i in range(6)])
        if 'victory' in ov:
            A['victory'] = dict(frames=ov['victory'], fps=8, loop=False, vel=[(0, 1), (0, -3), (0, 0), (0, 1)])
    return A


def talk_frames():
    return [Rx(expr='normal'),
            Rx(expr='talk', hn=(9.4, -26.2), hand_n='open', eb_n='down', tilt=-2),
            Rx(expr='talk_b', hn=(10.0, -27.4), hand_n='open', eb_n='down', tilt=-3),
            Rx(expr='talk', hn=(6.4, -22.4), hand_n='relax', tilt=-1)]


def cower_frames():
    out = []
    for dx in (0.4, -0.4, 0.15):
        out.append(G(hip=(-1.5 + dx, -12.0), lean=24, tilt=22, hn=(5.0 + dx, -33.0), hf=(7.0 + dx, -35.0),
                     hand_n='open', hand_f='open', fn=(4.5, 0), ff=(-5.0, 0), toe_f=20, expr='scared', wang=-90))
    return out


# ----------------------------------------------------------------------------- civilian set

ALIAS_ATTACKS = ['punch_a', 'punch_b', 'punch_c', 'kick', 'kick_c', 'jump_kick', 'jump_punch', 'run_punch',
                 'dropkick', 'throw', 'swing', 'sweep', 'rising_kick', 'slam']


def civilian_anims():
    F = fighter_anims()
    A = {}
    fr = []
    for i in range(6):
        th = 2 * math.pi * i / 6
        fr.append(Rx(hip=(0.15 * math.sin(th), -17.6 + 0.3 * math.sin(th)), lean=3.0 + 0.5 * math.sin(th - 0.4),
                     hn=(3.2, -16.9 + 0.35 * math.sin(th - 0.7)), hf=(-0.4, -17.5 + 0.3 * math.sin(th - 0.9)),
                     tilt=0.6 * math.sin(th - 1.1), blink=(i == 3)))
    A['idle'] = dict(frames=fr, fps=7, loop=True, vel=[(0, 0.3 * math.cos(2 * math.pi * i / 6)) for i in range(6)])
    fr, v = cycle(8, 34.0, 0.62, 2.6, 3.0, 'civ', 'normal', base=RELAX)
    A['walk'] = dict(frames=fr, fps=12, loop=True, stride=34.0, vel=v)
    fr, v = cycle(8, 54.0, 0.34, 7.0, 16.0, 'run', 'scared', run=True, base=RELAX)
    A['run'] = dict(frames=fr, fps=16, loop=True, stride=52.0, vel=v)
    A['talk'] = dict(frames=talk_frames(), fps=6, loop=True, vel=[(0, 0)] * 4)
    A['cower'] = dict(frames=cower_frames(), fps=10, loop=True, vel=[(0.5, 0), (-0.5, 0), (0.3, 0)])
    A['victory'] = dict(frames=[
        Rx(expr='smile'),
        Rx(hn=(13.0, -36.5), hf=(-5.0, -44.0), hand_n='open', hand_f='open', eb_n='down', eb_f='down', expr='happy',
           hip=(0, -18.0), tilt=-6),
        Rx(hn=(13.4, -37.5), hf=(-5.6, -45.0), hand_n='open', hand_f='open', eb_n='down', eb_f='down', expr='happy',
           hip=(0, -17.6), tilt=-6),
        Rx(expr='grin', hn=(6.0, -24.0), hand_n='open', eb_n='down'),
    ], fps=8, loop=False, vel=[(0, 0), (0, -2), (0, 1), (0, 0)])
    for k in ('hurt_high', 'hurt_low', 'hurt_back', 'knockdown', 'getup', 'dizzy', 'jump', 'land', 'pickup',
              'carry', 'carry_walk', 'guard'):
        A[k] = F[k]
    return A
