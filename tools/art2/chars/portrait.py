"""v2 dialogue portraits: 192x192 tx busts, 5 expressions, same renderer as the sprites."""
from PIL import Image

from raster import Canvas
from rig import body_for, solve
from draw import Frame, Look
from poses import Rx

SIZE = 192
MAP = {'neutral': 'normal', 'happy': 'happy', 'angry': 'angry', 'surprised': 'surprised', 'sad': 'sad'}
HEADROOM = {'beehive': 2.4, 'mohawk': 2.15, 'mohawk_low': 1.8, 'spikes_up': 2.0, 'spiky': 1.85,
            'puff': 2.05, 'pompadour': 1.7, 'flattop': 1.65, 'sideshave': 1.6, 'bun': 1.45}
TILT = {'neutral': -1.0, 'happy': -4.0, 'angry': 3.0, 'surprised': -6.0, 'sad': 7.0}


def render(spec, exprs):
    b = body_for(spec)
    look = Look(spec)
    strip = Image.new('RGBA', (SIZE * len(exprs), SIZE), (0, 0, 0, 0))
    R = b['R']
    top = R * HEADROOM.get(spec.get('hair'), 1.45) + 0.8
    if spec.get('hat'):
        top = max(top, R * 1.8)
    span = top + R * 1.9                       # crown .. upper chest
    den = round(SIZE / span * 8) / 8.0         # texel grid friendly
    span = SIZE / den
    for i, e in enumerate(exprs):
        pose = Rx(expr=MAP[e], tilt=TILT[e], lean=2.0, twist=0.25, hn=(2.6, -12.0), hf=(-1.2, -12.5))
        s = solve(pose, b)
        hx, hy = s.head_c
        x0 = hx - span * 0.52
        y0 = hy - top
        cv = Canvas(x0, y0, x0 + span, y0 + span, den=den)
        cv.line_scale = max(1.6, den / 3.0)
        f = Frame(cv, look, s, {'tails': (0.0, 0.0)}, portrait=True)
        f.render()
        cv.finish(outline_tx=max(2.5, den * 0.45), rim_tx=max(1.5, den * 0.25))
        img = cv.downsample()
        if img.size != (SIZE, SIZE):
            img = img.resize((SIZE, SIZE), Image.LANCZOS)
        strip.alpha_composite(img, (i * SIZE, 0))
    return strip
