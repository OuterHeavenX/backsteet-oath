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
RELAX = dict(hip=(0.0, -17.6), lean=3.0, twist=0.15, tilt=0.0, hn=(3.6, -19.6), hf=(-0.8, -20.4),
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

def cycle(n, stride, beta, lift, lean, arms, expr, run=False, base=None, carry=False, civ=False):
    """Distance-planted locomotion cycle.

    Each foot is planted for `beta` of the cycle and moves back at exactly the
    body speed (stride/n per frame), so the planted foot is fixed in the world."""
    base = base or {}
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
                toe = -12.0 * (1 - prog) ** 3 + (24.0 if run else 16.0) * max(0.0, prog - 0.65) / 0.35
                lifted = False
            else:
                u = (phi - beta) / (1 - beta)
                x = -A + 2 * A * smooth(u)
                if run:
                    x -= 3.2 * math.sin(math.pi * u) * (1 - u) * 1.6
                    y = -(1.0 + lift * math.sin(math.pi * min(1.0, u * 1.15)) ** 0.9)
                    toe = 42.0 * (1 - u) - 6.0 * u
                else:
                    y = -lift * math.sin(math.pi * u) ** 1.2
                    toe = 18.0 * (1 - u) - 10.0 * u
                lifted = True
            feet[side] = (x, y, toe, lifted)
        # hip height from planted feet (natural bob), stance knee slightly bent
        hx = 0.0
        hy = -stand * (0.965 if not run else 0.92)
        planted = [f for f in feet.values() if not f[3]]
        for (x, y, toe, _) in planted:
            dx = x - hx
            reach = math.sqrt(max((NORMAL['thigh'] + NORMAL['shin']) ** 2 * 0.985 - dx * dx, 1.0)) + NORMAL['ankle']
            hy = max(hy, -reach)
        if run:
            if not planted:
                hy -= 1.0
            else:
                # compression at mid stance
                for side in ('n', 'f'):
                    phi = (ph + (0.0 if side == 'n' else 0.5)) % 1.0
                    if phi < beta:
                        hy += 1.3 * math.sin(math.pi * phi / beta)
        # arms swing opposite to the legs
        s_n = -math.cos(2 * math.pi * ph)          # near arm forward when near leg is back
        s_f = -s_n
        kw = dict(base)
        if carry:
            kw.update(hn=(2.0, -49.8 + 0.3 * s_n), hf=(5.4, -49.4 + 0.3 * s_f), hand_n='open', hand_f='open',
                      eb_n='back', eb_f='fwd', twist=0.0, lean=lean, expr='effort', near_arm_back=True)
        elif run:
            kw.update(hn=(1.5 + 7.5 * s_n, -25.5 - 3.5 * s_n), hf=(1.0 + 7.0 * s_f, -26.0 - 3.5 * s_f),
                      twist=0.32 * s_f, ptwist=-0.3 * s_f, lean=lean, eb_n='down', eb_f='down')
        elif civ:
            kw.update(hn=(2.2 + 4.2 * s_n, -19.4 + 0.6 * abs(s_n)), hf=(-0.2 + 3.8 * s_f, -20.0 + 0.5 * abs(s_f)),
                      hand_n='relax', hand_f='relax', twist=0.18 * s_f, ptwist=-0.2 * s_f, lean=lean,
                      eb_n='back', eb_f='back')
        else:
            kw.update(hn=(3.6 + 4.6 * s_n, -21.8 - 1.4 * max(s_n, 0)), hf=(2.6 + 4.4 * s_f, -22.6 - 1.4 * max(s_f, 0)),
                      twist=0.24 * s_f, ptwist=-0.28 * s_f, lean=lean, eb_n='back', eb_f='back')
        kw.update(hip=(hx, hy), fn=feet['n'][:2], ff=feet['f'][:2], toe_n=feet['n'][2], toe_f=feet['f'][2],
                  lift_n=feet['n'][3], lift_f=feet['f'][3], expr=expr,
                  tilt=-2.0 + 1.2 * math.sin(4 * math.pi * ph))
        frames.append(P(**kw))
        vels.append((stride / n, 0.0))
    return frames, vels


# ----------------------------------------------------------------------------- fighter set

def fighter_anims():
    A = {}

    # idle: breathing + small boxer weight shift, one blink
    fr = []
    for i in range(6):
        th = 2 * math.pi * i / 6
        fr.append(G(hip=(-0.3 + 0.25 * math.sin(th), -16.9 + 0.38 * math.sin(th)),
                    lean=6.0 + 0.7 * math.sin(th - 0.4),
                    hn=(7.4, -28.6 + 0.55 * math.sin(th - 0.7)), hf=(12.2 + 0.2 * math.sin(th), -33.2 + 0.5 * math.sin(th - 0.9)),
                    tilt=-3.0 + 0.9 * math.sin(th - 1.1), blink=(i == 4)))
    A['idle'] = dict(frames=fr, fps=8, loop=True, vel=[(0, 0.35 * math.cos(2 * math.pi * i / 6)) for i in range(6)])

    fr, v = cycle(8, 38.0, 0.6, 3.2, 7.0, None, 'normal')
    A['walk'] = dict(frames=fr, fps=14, loop=True, stride=38.0, vel=v)
    fr, v = cycle(8, 60.0, 0.36, 8.0, 17.0, None, 'fight', run=True)
    A['run'] = dict(frames=fr, fps=18, loop=True, stride=60.0, vel=v)

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
        G(hip=(0.0, -17.5), lean=4, hn=(-2.0, -38.0), hf=(9.0, -32.0), fn=(5.0, -8.0), ff=(-4.0, -6.0),
          toe_n=30, toe_f=30, lift_n=True, lift_f=True, expr='effort', wang=-140),
        G(hip=(0.5, -17.0), lean=16, twist=-0.8, hn=(19.0, -23.0), hf=(-3.0, -33.0), hand_f='open', fn=(2.0, -9.0),
          ff=(-6.5, -7.0), toe_n=30, toe_f=50, lift_n=True, lift_f=True, expr='shout', tilt=4, wang=20),
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

    A['guard'] = dict(frames=[
        G(hip=(-0.6, -16.4), lean=8, hn=(8.6, -34.0), hf=(10.2, -36.4), expr='effort', tilt=-6),
        G(hip=(-0.8, -15.8), lean=10, tilt=-10, hn=(8.2, -35.6), hf=(10.0, -38.2), expr='effort'),
    ], fps=12, loop=False, vel=[(0, 0), (0, 0.5)])

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
        G(hip=(1.6, -17.0), lean=14, tilt=-24, hn=(-6.0, -26.0), hf=(-8.0, -30.0), hand_n='open', hand_f='open',
          eb_n='down', eb_f='down', fn=(6.0, 0), ff=(-3.0, 0), toe_f=20, expr='pain_open'),
        G(hip=(2.4, -16.4), lean=20, tilt=-12, hn=(-3.0, -24.0), hf=(-5.0, -28.0), hand_n='open', hand_f='open',
          fn=(8.0, 0), ff=(-2.0, -2.0), toe_f=30, lift_f=True, expr='pain'),
        G(hip=(1.0, -16.6), lean=10, tilt=-4, fn=(6.0, 0), ff=(-4.6, 0), expr='fight'),
    ], fps=12, loop=False, vel=[(3, 0), (1.5, 0), (0, 0)])
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
    fr, v = cycle(6, 26.0, 0.62, 2.4, 2.0, None, 'effort', carry=True, base=dict(GUARD, tilt=-8))
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
        G(hip=(0.0, -18.0), lean=-4, hn=(4.0, -51.0), hf=(5.0, -26.0), eb_n='back', expr='happy', tilt=-8, wang=-90,
          near_arm_back=True),
        G(hip=(0.0, -18.1), lean=-5, hn=(4.4, -52.0), hf=(5.0, -26.4), eb_n='back', expr='happy', tilt=-9, wang=-90,
          near_arm_back=True),
        G(hip=(-0.2, -17.6), lean=2, hn=(5.0, -44.0), hf=(4.0, -22.0), eb_n='back', hand_f='relax', expr='grin',
          wang=-80, near_arm_back=True),
    ], fps=8, loop=False, vel=[(0, 1), (0, -3), (0, 0), (0, 1)])
    A['talk'] = dict(frames=talk_frames(), fps=6, loop=True, vel=[(0, 0)] * 4)
    A['cower'] = dict(frames=cower_frames(), fps=10, loop=True, vel=[(0.5, 0), (-0.5, 0), (0.3, 0)])
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
                     hn=(3.6, -19.6 + 0.35 * math.sin(th - 0.7)), hf=(-0.8, -20.4 + 0.3 * math.sin(th - 0.9)),
                     tilt=0.6 * math.sin(th - 1.1), blink=(i == 3)))
    A['idle'] = dict(frames=fr, fps=7, loop=True, vel=[(0, 0.3 * math.cos(2 * math.pi * i / 6)) for i in range(6)])
    fr, v = cycle(8, 34.0, 0.62, 2.6, 3.0, None, 'normal', civ=True, base=RELAX)
    A['walk'] = dict(frames=fr, fps=12, loop=True, stride=34.0, vel=v)
    fr, v = cycle(8, 52.0, 0.38, 6.0, 12.0, None, 'scared', run=True, base=RELAX)
    A['run'] = dict(frames=fr, fps=16, loop=True, stride=52.0, vel=v)
    A['talk'] = dict(frames=talk_frames(), fps=6, loop=True, vel=[(0, 0)] * 4)
    A['cower'] = dict(frames=cower_frames(), fps=10, loop=True, vel=[(0.5, 0), (-0.5, 0), (0.3, 0)])
    A['victory'] = dict(frames=[
        Rx(expr='smile'),
        Rx(hn=(2.0, -49.0), hf=(5.4, -48.0), hand_n='open', hand_f='open', eb_n='back', eb_f='fwd', expr='happy',
           hip=(0, -18.0), tilt=-6, near_arm_back=True),
        Rx(hn=(2.4, -50.0), hf=(5.8, -49.0), hand_n='open', hand_f='open', eb_n='back', eb_f='fwd', expr='happy',
           hip=(0, -17.6), tilt=-6, near_arm_back=True),
        Rx(expr='grin', hn=(6.0, -24.0), hand_n='open', eb_n='down'),
    ], fps=8, loop=False, vel=[(0, 0), (0, -2), (0, 1), (0, 0)])
    for k in ('hurt_high', 'hurt_low', 'hurt_back', 'knockdown', 'getup', 'dizzy', 'jump', 'land', 'pickup',
              'carry', 'carry_walk', 'guard'):
        A[k] = F[k]
    return A
