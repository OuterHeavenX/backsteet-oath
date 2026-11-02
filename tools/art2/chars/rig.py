"""Skeleton, body proportions and two-bone IK for the v2 characters.

World units (u), anchor (0,0) = ground point between the feet, +y is down,
characters face +x. Poses are authored for the 'normal' body and retargeted to
other bodies by scaling limb-relative offsets.
"""
import math

# ----------------------------------------------------------------------------- bodies
# R head radius; torso = neck base -> pelvis centre; thigh/shin; ankle = ankle height;
# ua/fa arm; fist radius; w = width scale; chest/back = torso half depths at chest;
# belly = extra front bulge at the waist; stoop = forward head/neck offset.
BODY = {
    'normal': dict(R=7.0, neck=1.8, torso=13.0, thigh=8.4, shin=8.0, ankle=1.5, ua=7.0, fa=6.4,
                   fist=1.72, w=1.0, chest=4.0, back=4.3, waist=3.3, hip=3.6, belly=0.0, stoop=0.0,
                   limb=1.0, foot=1.0),
    'slim': dict(R=6.9, neck=1.9, torso=13.0, thigh=8.5, shin=8.1, ankle=1.5, ua=7.0, fa=6.4,
                 fist=1.6, w=0.86, chest=3.5, back=3.8, waist=2.8, hip=3.1, belly=0.0, stoop=0.0,
                 limb=0.86, foot=0.95),
    'heavy': dict(R=7.3, neck=1.5, torso=14.2, thigh=8.8, shin=8.4, ankle=1.6, ua=7.4, fa=6.8,
                  fist=2.15, w=1.34, chest=5.6, back=5.5, waist=5.7, hip=5.0, belly=2.4, stoop=0.0,
                  limb=1.42, foot=1.14),
    'big': dict(R=7.6, neck=1.4, torso=16.2, thigh=9.6, shin=9.0, ankle=1.7, ua=8.4, fa=7.6,
                fist=2.6, w=1.58, chest=6.9, back=6.6, waist=6.0, hip=5.6, belly=2.0, stoop=0.0,
                limb=1.7, foot=1.28),
    'tall': dict(R=7.0, neck=2.0, torso=14.6, thigh=9.6, shin=9.2, ankle=1.5, ua=7.8, fa=7.2,
                 fist=1.78, w=1.04, chest=4.1, back=4.4, waist=3.3, hip=3.6, belly=0.0, stoop=0.0,
                 limb=1.02, foot=1.05),
    'kid': dict(R=6.6, neck=1.4, torso=10.0, thigh=6.6, shin=6.2, ankle=1.3, ua=5.4, fa=5.0,
                fist=1.42, w=0.82, chest=3.2, back=3.4, waist=2.8, hip=3.0, belly=0.0, stoop=0.0,
                limb=0.82, foot=0.85),
    'elder': dict(R=6.8, neck=1.6, torso=12.0, thigh=7.8, shin=7.4, ankle=1.4, ua=6.6, fa=6.0,
                  fist=1.5, w=0.98, chest=4.0, back=4.4, waist=3.8, hip=4.0, belly=0.8, stoop=1.6,
                  limb=0.92, foot=0.95),
}
NORMAL = dict(BODY['normal'])       # authoring reference: poses are written for this body, then retargeted

# per-type overall scale (lengths and widths) so crown heights land in the contract ranges:
# normal/slim ~94 tx, tall ~104, heavy ~108, big ~116, kid ~80, elder ~88 (hair not included)
TYPE_SCALE = {'normal': 1.045, 'slim': 1.045, 'tall': 1.06, 'heavy': 1.12, 'big': 1.074, 'kid': 1.077, 'elder': 1.044}
LENGTH_KEYS = ('R', 'neck', 'torso', 'thigh', 'shin', 'ankle', 'ua', 'fa', 'fist', 'stoop')
WIDTH_KEYS = ('w', 'chest', 'back', 'waist', 'hip', 'belly', 'limb', 'foot')
for _k, _f in list(TYPE_SCALE.items()):
    for _key in LENGTH_KEYS:
        BODY[_k][_key] *= _f
    for _key in WIDTH_KEYS:
        BODY[_k][_key] *= _f ** 0.8


def body_for(spec):
    b = dict(BODY[spec.get('body', 'normal')])
    if spec.get('bulk'):
        for k in ('w', 'chest', 'back', 'waist', 'hip', 'limb'):
            b[k] *= 1.12
        b['fist'] *= 1.1
    if spec.get('wide'):
        for k in ('waist', 'hip'):
            b[k] *= 1.15
    if spec.get('boss_scale'):
        s = spec['boss_scale']
        for k in ('R', 'neck', 'torso', 'thigh', 'shin', 'ankle', 'ua', 'fa', 'fist', 'chest', 'back',
                  'waist', 'hip', 'belly', 'limb', 'foot'):
            b[k] *= s
    b['leg'] = b['thigh'] + b['shin']
    b['arm'] = b['ua'] + b['fa']
    b['stand_hip'] = b['leg'] + b['ankle']
    return b


# ----------------------------------------------------------------------------- vector helpers

def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, s):
    return (a[0] * s, a[1] * s)


def length(a):
    return math.hypot(a[0], a[1])


def norm(a):
    L = length(a) or 1e-9
    return (a[0] / L, a[1] / L)


def perp(a):
    return (-a[1], a[0])


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def ang_dir(deg):
    """Spine direction for a lean angle (deg, + = forward/right), pointing up."""
    r = math.radians(deg)
    return (math.sin(r), -math.cos(r))


def ik2(root, target, l1, l2, bend):
    """Two-bone IK. bend: 'down', 'up', 'fwd', 'back' picks the joint side."""
    d = sub(target, root)
    L = length(d)
    reach = (l1 + l2) * 0.9995
    if L < 1e-6:
        d = (1e-3, 0)
        L = 1e-3
    if L > reach:
        dirn = norm(d)
        joint = add(root, mul(dirn, l1))
        end = add(root, mul(dirn, reach))
        return joint, end
    L = max(L, abs(l1 - l2) + 1e-3)
    a = (l1 * l1 - l2 * l2 + L * L) / (2 * L)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    dirn = norm(d)
    base = add(root, mul(dirn, a))
    p = perp(dirn)
    c1 = add(base, mul(p, h))
    c2 = add(base, mul(p, -h))
    if bend == 'down':
        j = c1 if c1[1] > c2[1] else c2
    elif bend == 'up':
        j = c1 if c1[1] < c2[1] else c2
    elif bend == 'fwd':
        j = c1 if c1[0] > c2[0] else c2
    else:
        j = c1 if c1[0] < c2[0] else c2
    return j, target


# ----------------------------------------------------------------------------- pose

DEFAULT_POSE = dict(
    hip=(0.0, -16.9), lean=6.0, twist=0.0, ptwist=0.0, tilt=-3.0, head=(0.0, 0.0),
    hn=(9.5, -33.0), hf=(6.0, -35.5),           # hand targets (wrist/fist centres)
    fn=(5.4, 0.0), ff=(-5.0, 0.0),              # foot targets (sole level)
    toe_n=0.0, toe_f=0.0,                       # foot pitch (deg, + = toes down)
    eb_n='down', eb_f='down', kb_n='fwd', kb_f='fwd',
    hand_n='fist', hand_f='fist', wang=-50.0, wfront=1,
    expr='fight', look=(1.0, 0.0), blink=False,
    near_arm_back=False, far_arm_front=False, near_leg_back=False, near_arm_under=False,
    lift_n=False, lift_f=False,                 # foot is airborne (not retargeted as planted)
    fist_ang_n=None, fist_ang_f=None,
    sway=(0.0, 0.0),                            # hair/cloth drag override add (u)
)


def P(**kw):
    d = dict(DEFAULT_POSE)
    d.update(kw)
    return d


class Solved:
    pass


def solve(pose, b, retarget=True):
    """Solve joints for body b. Poses are authored for NORMAL and retargeted."""
    s = Solved()
    s.pose = pose
    s.b = b
    leg_r = b['stand_hip'] / (NORMAL['thigh'] + NORMAL['shin'] + NORMAL['ankle'])
    arm_r = b['arm'] / (NORMAL['ua'] + NORMAL['fa'])
    hx, hy = pose['hip']
    s.hip = (hx * leg_r, hy * leg_r)
    lean = pose['lean']
    s.lean = lean
    up = ang_dir(lean)
    fwd = (-up[1], up[0])           # perpendicular (toward +x when upright)
    s.up, s.fwd = up, fwd
    s.neck_base = add(s.hip, mul(up, b['torso']))
    t = pose['twist']
    s.twist = t
    sh_c = add(s.neck_base, mul(up, -1.5))
    w = b['w']
    sn = (0.8 - 1.9 * t) * w
    sf = (-1.5 + 3.0 * t) * w
    s.sh_n = add(add(sh_c, mul(fwd, sn)), mul(up, -0.15))
    s.sh_f = add(add(sh_c, mul(fwd, sf)), mul(up, 0.45))
    # pelvis
    pt = pose['ptwist']
    pang = lean * 0.35
    pup = ang_dir(pang)
    pfwd = (-pup[1], pup[0])
    s.pup, s.pfwd = pup, pfwd
    s.hj_n = add(add(s.hip, mul(pfwd, (1.0 - 1.0 * pt) * w)), mul(pup, -0.6))
    s.hj_f = add(add(s.hip, mul(pfwd, (-1.0 + 1.4 * pt) * w)), mul(pup, -0.3))
    # head
    s.neck_top = add(add(s.neck_base, mul(up, b['neck'])), (b['stoop'], 0))
    hang = lean * 0.45 + pose['tilt']
    s.head_ang = hang
    hu = ang_dir(hang)
    s.head_c = add(add(s.neck_top, mul(hu, b['R'] * 0.80)), (pose['head'][0] + b['stoop'] * 0.6,
                                                           pose['head'][1]))
    s.head_up = hu

    # normal-body references for retargeting
    if retarget and b is not NORMAL:
        ref = solve(pose, dict(NORMAL, leg=NORMAL['thigh'] + NORMAL['shin'],
                               arm=NORMAL['ua'] + NORMAL['fa'],
                               stand_hip=NORMAL['thigh'] + NORMAL['shin'] + NORMAL['ankle']),
                    retarget=False)
    else:
        ref = s

    def hand_target(name, sh, ref_sh):
        tx, ty = pose[name]
        rel = sub((tx, ty), ref_sh)
        return add(sh, mul(rel, arm_r))

    s.hand_tn = hand_target('hn', s.sh_n, ref.sh_n) if ref is not s else pose['hn']
    s.hand_tf = hand_target('hf', s.sh_f, ref.sh_f) if ref is not s else pose['hf']
    # arms: target is fist centre; wrist is fist centre pulled back along forearm
    s.elb_n, s.wr_n = _arm(s.sh_n, s.hand_tn, b, pose['eb_n'])
    s.elb_f, s.wr_f = _arm(s.sh_f, s.hand_tf, b, pose['eb_f'])
    s.fist_n = s.hand_tn
    s.fist_f = s.hand_tf
    # legs
    s.ank_n, s.knee_n, s.foot_tn = _leg(pose, 'fn', 'toe_n', 'kb_n', 'lift_n', s.hj_n, ref.hj_n if ref is not s else None,
                                        b, leg_r)
    s.ank_f, s.knee_f, s.foot_tf = _leg(pose, 'ff', 'toe_f', 'kb_f', 'lift_f', s.hj_f, ref.hj_f if ref is not s else None,
                                        b, leg_r)
    s.toe_n = pose['toe_n']
    s.toe_f = pose['toe_f']
    return s


def _arm(sh, fist, b, bend):
    d = sub(fist, sh)
    L = length(d)
    reach = b['ua'] + b['fa'] + b['fist'] * 0.8
    if L > reach:
        fist = add(sh, mul(norm(d), reach))
    # wrist sits behind the fist centre along the shoulder->fist direction (refined after IK)
    wr_guess = sub(fist, mul(norm(sub(fist, sh)), b['fist'] * 0.8))
    elb, wr = ik2(sh, wr_guess, b['ua'], b['fa'], bend)
    # re-aim: wrist -> fist along forearm
    return elb, wr


def _leg(pose, key, toe_key, kb_key, lift_key, hj, ref_hj, b, leg_r):
    fx, fy = pose[key]
    lifted = pose[lift_key] or fy < -0.6
    if ref_hj is not None and lifted:
        rel = sub((fx, fy), ref_hj)
        tgt = add(hj, mul(rel, leg_r))
    else:
        tgt = (fx * leg_r, fy * leg_r)
    toe = math.radians(pose[toe_key])
    # ankle above sole; with toe pitch the ankle rises around the ball of the foot
    ank = (tgt[0] - math.sin(toe) * 0.0, tgt[1] - b['ankle'] * math.cos(toe) - 2.4 * b['foot'] * math.sin(max(toe, 0)) * 0.55)
    knee, ank2 = ik2(hj, ank, b['thigh'], b['shin'], pose[kb_key])
    return ank2, knee, tgt
