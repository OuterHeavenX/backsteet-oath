#!/usr/bin/env python3
"""BACKSTREET OATH - procedural audio generator.

Synthesizes every music track and sound effect of the game from scratch
(no samples, no third-party material).  All melodies are original
compositions written for this project.

Requirements: Python 3, numpy, ffmpeg (libvorbis) on PATH or /usr/bin.

    python3 tools/audio/gen_audio.py               # build everything
    python3 tools/audio/gen_audio.py --only title,punch_light
    python3 tools/audio/gen_audio.py --music        # music only
    python3 tools/audio/gen_audio.py --sfx          # sfx only

Output:
    game/assets/audio/music/<id>.ogg   44.1 kHz stereo Vorbis q5
    game/assets/audio/sfx/<id>.ogg     44.1 kHz mono   Vorbis q5
    docs/assets/AUDIO_ASSETS.md        asset table + level report

Design notes
------------
* Music is written with a tiny step sequencer (16th-note grid).  The
  16th-note length is rounded to a whole number of samples so a loop of
  N bars is exactly N*16*step samples long.
* Seamless loops: notes are rendered into a buffer of loop body + tail,
  the tail is added back onto the start (wrap), and every effect after
  that (EQ, echo, room reverb, limiter) is applied circularly on the
  loop body (FFT convolution), so the last sample flows into the first.
* Everything is deterministic: random sources are seeded from asset ids.
"""
import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import zlib

import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
MUSIC_DIR = os.path.join(ROOT, 'game', 'assets', 'audio', 'music')
SFX_DIR = os.path.join(ROOT, 'game', 'assets', 'audio', 'sfx')
DOC_PATH = os.path.join(ROOT, 'docs', 'assets', 'AUDIO_ASSETS.md')
FFMPEG = '/usr/bin/ffmpeg' if os.path.exists('/usr/bin/ffmpeg') else (shutil.which('ffmpeg') or 'ffmpeg')
OGG_QUALITY = 5
ORIGIN = 'procedurally synthesized by tools/audio/gen_audio.py, original, project-owned'


# ---------------------------------------------------------------------------
# small utils
# ---------------------------------------------------------------------------
def rng_for(name):
    return np.random.default_rng(zlib.crc32(name.encode('utf-8')))


def db(x):
    return 20.0 * math.log10(max(float(x), 1e-12))


def undb(d):
    return 10.0 ** (d / 20.0)


def secs(n):
    return np.arange(n) / SR


def fit(x, n):
    """Pad with zeros / truncate to length n."""
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros(n - len(x))])


def mix_into(buf, pos, sig, gain=1.0):
    """Add sig into buf at sample pos (clipped to buffer)."""
    if pos >= len(buf) or len(sig) == 0:
        return
    if pos < 0:
        sig = sig[-pos:]
        pos = 0
    end = min(len(buf), pos + len(sig))
    buf[pos:end] += sig[:end - pos] * gain


def fade(x, fin=0.002, fout=0.005):
    x = x.copy()
    a = min(len(x), max(1, int(fin * SR)))
    b = min(len(x), max(1, int(fout * SR)))
    x[:a] *= np.linspace(0, 1, a)
    x[len(x) - b:] *= np.linspace(1, 0, b)
    return x


# ---------------------------------------------------------------------------
# FFT filters (zero phase).  Responses are functions freq->gain.
# ---------------------------------------------------------------------------
def r_lp(fc, order=2):
    return lambda f: 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))


def r_hp(fc, order=2):
    return lambda f: 1.0 / np.sqrt(1.0 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def r_bp(lo, hi, order=2):
    a, b = r_hp(lo, order), r_lp(hi, order)
    return lambda f: a(f) * b(f)


def r_peak(fc, gain_db, width_oct=1.0):
    g = undb(gain_db)
    sig = max(width_oct, 0.05) / 2.0
    return lambda f: 1.0 + (g - 1.0) * np.exp(-0.5 * (np.log2(np.maximum(f, 1.0) / fc) / sig) ** 2)


def r_shelf_hi(fc, gain_db):
    g = undb(gain_db)
    return lambda f: 1.0 + (g - 1.0) / (1.0 + (fc / np.maximum(f, 1e-3)) ** 2)


def r_shelf_lo(fc, gain_db):
    g = undb(gain_db)
    return lambda f: 1.0 + (g - 1.0) / (1.0 + (f / fc) ** 2)


def _fast_len(n):
    p = 1
    while p < n:
        p *= 2
    return p


def filt(x, *resps, circular=False):
    """Zero-phase FFT filter. x: (n,) or (n,ch).  circular=True treats x as a loop."""
    if not resps or len(x) == 0:
        return x
    n = x.shape[0]
    N = n if circular else _fast_len(n + 8192)
    X = np.fft.rfft(x, n=N, axis=0)
    f = np.fft.rfftfreq(N, 1.0 / SR)
    g = np.ones_like(f)
    for r in resps:
        g = g * r(f)
    X *= g[:, None] if x.ndim == 2 else g
    return np.fft.irfft(X, n=N, axis=0)[:n]


def tv_filter(x, resp_at, frame=1024, hop=256):
    """Time-varying zero-phase filter via windowed overlap-add.
    resp_at(t_seconds, freqs) -> gain array."""
    n = len(x)
    win = np.hanning(frame + 1)[:-1]
    pad = frame
    xp = np.concatenate([np.zeros(pad), x, np.zeros(pad + frame)])
    out = np.zeros_like(xp)
    norm = np.zeros_like(xp)
    f = np.fft.rfftfreq(frame, 1.0 / SR)
    for s in range(0, len(xp) - frame, hop):
        tc = (s + frame / 2 - pad) / SR
        seg = xp[s:s + frame] * win
        X = np.fft.rfft(seg) * resp_at(max(tc, 0.0), f)
        out[s:s + frame] += np.fft.irfft(X, n=frame) * win
        norm[s:s + frame] += win * win
    norm[norm < 1e-6] = 1.0
    return (out / norm)[pad:pad + n]


def conv(x, ir, circular=False):
    """FFT convolution of mono x with mono ir."""
    n = len(x)
    if circular:
        if len(ir) > n:
            ir = ir[:n]
        return np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(ir, n=n), n=n)
    N = _fast_len(n + len(ir))
    return np.fft.irfft(np.fft.rfft(x, n=N) * np.fft.rfft(ir, n=N), n=N)[:n + len(ir) - 1]


# ---------------------------------------------------------------------------
# space: echo + room impulse responses
# ---------------------------------------------------------------------------
def echo_ir(delay_s, feedback=0.35, repeats=7, pingpong=True, lp=3200.0, hp=250.0):
    m = int(delay_s * SR * repeats) + 2
    irl = np.zeros(m)
    irr = np.zeros(m)
    for k in range(1, repeats + 1):
        g = feedback ** (k - 1)
        i = int(round(k * delay_s * SR))
        if i >= m:
            break
        if pingpong:
            (irl if k % 2 == 1 else irr)[i] += g
        else:
            irl[i] += g * 0.8
            irr[i] += g * 0.8
    irl = filt(irl, r_lp(lp, 1), r_hp(hp, 1))
    irr = filt(irr, r_lp(lp, 1), r_hp(hp, 1))
    return irl, irr


def room_ir(name, rt60=1.1, predelay=0.012, damp=5500.0, er=True):
    rng = rng_for('room:' + name)
    n = int((predelay + rt60 * 1.1) * SR)
    t = secs(n)
    irs = []
    for ch in range(2):
        nz = rng.standard_normal(n)
        lo = filt(nz, r_lp(damp, 1))
        hi = nz - lo
        tt = np.maximum(t - predelay, 0.0)
        env_lo = 10.0 ** (-3.0 * tt / rt60)
        env_hi = 10.0 ** (-3.0 * tt / (rt60 * 0.45))
        ir = lo * env_lo + 0.5 * hi * env_hi
        ir[t < predelay] = 0.0
        ramp = np.clip((t - predelay) / 0.006, 0, 1)
        ir *= ramp
        if er:
            for k in range(6):
                d = predelay * 0.4 + rng.uniform(0.004, 0.035)
                i = int(d * SR)
                if i < n:
                    ir[i] += rng.uniform(0.6, 1.4) * (0.7 ** k) * (1 if rng.random() > 0.5 else -1) * 3.0
        ir = filt(ir, r_hp(180, 1))
        ir /= math.sqrt(np.sum(ir ** 2)) + 1e-12
        irs.append(ir)
    return irs[0], irs[1]


# ---------------------------------------------------------------------------
# loudness (ITU-R BS.1770 K-weighting, implemented in the frequency domain)
# ---------------------------------------------------------------------------
def _kweight(N):
    f = np.fft.rfftfreq(N, 1.0 / SR)
    z1 = np.exp(-1j * 2 * np.pi * f / SR)
    z2 = z1 * z1
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = math.tan(math.pi * f0 / SR)
    Vh = 10 ** (G / 20.0)
    Vb = Vh ** 0.4996667741545416
    a0 = 1.0 + K / Q + K * K
    b0 = (Vh + Vb * K / Q + K * K) / a0
    b1 = 2.0 * (K * K - Vh) / a0
    b2 = (Vh - Vb * K / Q + K * K) / a0
    a1 = 2.0 * (K * K - 1.0) / a0
    a2 = (1.0 - K / Q + K * K) / a0
    h1 = (b0 + b1 * z1 + b2 * z2) / (1.0 + a1 * z1 + a2 * z2)
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = math.tan(math.pi * f0 / SR)
    a0 = 1.0 + K / Q + K * K
    a1 = 2.0 * (K * K - 1.0) / a0
    a2 = (1.0 - K / Q + K * K) / a0
    h2 = (1.0 - 2.0 * z1 + z2) / (1.0 + a1 * z1 + a2 * z2)
    return h1 * h2


def _kfilter(x, circular):
    x2 = x if x.ndim == 2 else x[:, None]
    n = x2.shape[0]
    N = n if circular else _fast_len(n + 4096)
    X = np.fft.rfft(x2, n=N, axis=0) * _kweight(N)[:, None]
    return np.fft.irfft(X, n=N, axis=0)[:n if circular else n + 2048]


def _block_loudness(y, block=0.4, step=0.1):
    bl, st = int(block * SR), int(step * SR)
    if y.shape[0] < bl:
        y = np.concatenate([y, np.zeros((bl - y.shape[0], y.shape[1]))])
    p = np.cumsum(np.concatenate([np.zeros((1, y.shape[1])), y ** 2]), axis=0)
    starts = np.arange(0, y.shape[0] - bl + 1, st)
    ms = (p[starts + bl] - p[starts]) / bl
    return -0.691 + 10 * np.log10(np.sum(ms, axis=1) + 1e-20)


def lufs(x, circular=False):
    """Gated integrated loudness."""
    y = _kfilter(x, circular)
    if circular:   # let blocks wrap around the loop
        y = np.concatenate([y, y[:int(0.4 * SR)]])
    lk = _block_loudness(y)
    lk = lk[lk > -70]
    if len(lk) == 0:
        return -70.0
    rel = 10 * np.log10(np.mean(10 ** (lk / 10))) - 10
    lk = lk[lk > rel]
    return float(10 * np.log10(np.mean(10 ** (lk / 10))))


def lufs_momentary_max(x):
    y = _kfilter(x, False)
    return float(np.max(_block_loudness(y, 0.3, 0.02)))


# ---------------------------------------------------------------------------
# dynamics + mastering
# ---------------------------------------------------------------------------
def softclip(x, ceiling=0.84, knee=0.62):
    """Memoryless soft limiter: linear below knee*ceiling, tanh above, never exceeds ceiling."""
    k = knee * ceiling
    a = np.abs(x)
    over = a > k
    y = x.copy()
    y[over] = np.sign(x[over]) * (k + (ceiling - k) * np.tanh((a[over] - k) / (ceiling - k)))
    return y


def normalize_loudness(x, target, ceiling_db=-1.5, circular=False, momentary=False):
    c = undb(ceiling_db)
    g = 1.0
    meas = (lambda y: lufs_momentary_max(y)) if momentary else (lambda y: lufs(y, circular))
    for _ in range(6):
        y = softclip(x * g, c)
        L = meas(y)
        if abs(L - target) < 0.1:
            break
        g *= undb(target - L)
    return softclip(x * g, c)


def master_music(st, target=-16.0, circular=True):
    st = st - st.mean(axis=0, keepdims=True)
    st = filt(st, r_hp(24, 2), circular=circular)
    return normalize_loudness(st, target, -1.5, circular)


# ---------------------------------------------------------------------------
# ogg i/o
# ---------------------------------------------------------------------------
def _encode(path, x, quality):
    ch = 1 if x.ndim == 1 else x.shape[1]
    cmd = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-y',
           '-f', 'f32le', '-ar', str(SR), '-ac', str(ch), '-i', 'pipe:0',
           '-c:a', 'libvorbis', '-q:a', str(quality),
           '-fflags', '+bitexact', '-flags:a', '+bitexact', '-map_metadata', '-1',
           path]
    subprocess.run(cmd, input=np.ascontiguousarray(x, dtype='<f4').tobytes(), check=True)


def decode_ogg(path, channels):
    cmd = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-i', path,
           '-f', 'f32le', '-ac', str(channels), '-ar', str(SR), 'pipe:1']
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    y = np.frombuffer(raw, dtype='<f4').astype(np.float64)
    return y.reshape(-1, channels) if channels > 1 else y


def write_ogg(path, x, quality=OGG_QUALITY, max_peak_db=-1.0):
    """Encode, decode back, and re-encode quieter if lossy overshoot breaks the ceiling."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    ch = 1 if x.ndim == 1 else x.shape[1]
    for _ in range(5):
        _encode(path, x, quality)
        y = decode_ogg(path, ch)
        pk = float(np.max(np.abs(y))) if len(y) else 0.0
        if db(pk) <= max_peak_db - 0.05:
            return y
        x = x * undb(max_peak_db - 0.25 - db(pk))
    return y


# ---------------------------------------------------------------------------
# pitch helpers
# ---------------------------------------------------------------------------
_NB = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def midi_of(s):
    if isinstance(s, (int, float)):
        return float(s)
    m = re.match(r'^([A-Ga-g])([#b]*)(-?\d+)$', s)
    if not m:
        raise ValueError('bad note ' + s)
    pc = _NB[m.group(1).upper()] + m.group(2).count('#') - m.group(2).count('b')
    return 12 * (int(m.group(3)) + 1) + pc


def hz(m):
    return 440.0 * 2.0 ** ((midi_of(m) - 69) / 12.0)


# ---------------------------------------------------------------------------
# oscillators
# ---------------------------------------------------------------------------
def _phase(freq):
    dt = freq / SR
    ph = np.cumsum(dt) - dt[0]
    return ph, dt


def _blep(t, dt):
    out = np.zeros_like(t)
    m = t < dt
    x = t[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    x = (t[m] - 1.0) / dt[m]
    out[m] = x * x + x + x + 1.0
    return out


def osc_saw(freq):
    ph, dt = _phase(freq)
    t = ph % 1.0
    return 2.0 * t - 1.0 - _blep(t, dt)


def osc_pulse(freq, duty=0.5):
    ph, dt = _phase(freq)
    t = ph % 1.0
    duty = np.broadcast_to(duty, t.shape)
    y = np.where(t < duty, 1.0, -1.0)
    y = y + _blep(t, dt) - _blep((t - duty) % 1.0, dt)
    return y - (2.0 * duty - 1.0)       # remove duty DC


def osc_tri(freq, quant=0):
    ph, _ = _phase(freq)
    t = ph % 1.0
    y = 1.0 - 4.0 * np.abs(t - 0.5)
    if quant:
        y = np.round((y + 1.0) * 0.5 * (quant - 1)) / (quant - 1) * 2.0 - 1.0
    return y


def osc_sine(freq):
    ph, _ = _phase(freq)
    return np.sin(2 * np.pi * ph)


_LFSR = {}


def lfsr_table(short=False):
    if short in _LFSR:
        return _LFSR[short]
    reg, out, tap = 1, [], 6 if short else 1
    n = 93 if short else 32767
    for _ in range(n):
        bit = (reg ^ (reg >> tap)) & 1
        reg = (reg >> 1) | (bit << 14)
        out.append(1.0 if reg & 1 else -1.0)
    _LFSR[short] = np.array(out)
    return _LFSR[short]


def osc_lfsr(n, rate, short=False, offset=0):
    """Chip-style noise: LFSR stepped at `rate` Hz (scalar or array)."""
    tab = lfsr_table(short)
    rate = np.broadcast_to(np.asarray(rate, dtype=float), (n,))
    idx = (np.floor(np.cumsum(rate / SR)).astype(np.int64) + offset) % len(tab)
    return tab[idx]


# ---------------------------------------------------------------------------
# envelopes
# ---------------------------------------------------------------------------
def adsr(n_gate, a=0.005, d=0.1, s=0.7, r=0.08):
    a = max(a, 0.0005)
    nr = max(1, int(r * SR))
    tg = secs(n_gate)
    g = np.where(tg < a, tg / a, s + (1.0 - s) * np.exp(-(tg - a) / max(d / 4.0, 1e-4)))
    L = g[-1] if n_gate else 0.0
    x = np.arange(nr) / nr
    rel = L * np.exp(-4.0 * x) * (1.0 - x)
    return np.concatenate([g, rel])


def env_exp(n, tau, attack=0.001):
    t = secs(n)
    e = np.exp(-t / tau)
    na = max(1, int(attack * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


# ---------------------------------------------------------------------------
# instruments
# ---------------------------------------------------------------------------
INST = {
    # chip leads
    'lead':      dict(wave='pulse', duty=0.25, a=0.004, d=0.18, s=0.72, r=0.09, vib=(16, 5.6, 0.16), gain=0.42),
    'lead12':    dict(wave='pulse', duty=0.125, a=0.003, d=0.15, s=0.65, r=0.08, vib=(14, 5.8, 0.14), gain=0.40),
    'lead50':    dict(wave='pulse', duty=0.5, a=0.005, d=0.2, s=0.7, r=0.1, vib=(12, 5.2, 0.2), gain=0.36),
    'leadpwm':   dict(wave='pulse', duty=(0.12, 0.42, 0.6), a=0.006, d=0.25, s=0.75, r=0.12, vib=(18, 5.4, 0.2), gain=0.40),
    'leadsaw':   dict(wave='saw', a=0.01, d=0.25, s=0.75, r=0.15, vib=(14, 5.3, 0.2), detune=8, gain=0.30),
    'harm':      dict(wave='pulse', duty=0.5, a=0.006, d=0.2, s=0.6, r=0.1, vib=(10, 5.2, 0.2), gain=0.24),
    'clav':      dict(wave='pulse', duty=0.25, a=0.002, d=0.09, s=0.0, r=0.04, gain=0.38),
    'stab':      dict(wave='saw', a=0.003, d=0.12, s=0.25, r=0.06, detune=10, gain=0.22),
    'skank':     dict(wave='pulse', duty=0.33, a=0.002, d=0.07, s=0.0, r=0.03, gain=0.4),
    'arp':       dict(wave='pulse', duty=0.125, a=0.002, d=0.09, s=0.3, r=0.05, gain=0.26),
    'arp25':     dict(wave='pulse', duty=0.25, a=0.002, d=0.1, s=0.35, r=0.05, gain=0.26),
    'pluck':     dict(wave='pluck', a=0.002, d=0.25, s=0.0, r=0.08, bright=0.07, gain=0.32),
    # bass
    'bass':      dict(wave='tri', quant=16, a=0.003, d=0.1, s=0.85, r=0.04, sub=0.35, gain=0.52),
    'bassp':     dict(wave='pulse', duty=0.25, a=0.003, d=0.12, s=0.6, r=0.04, sub=0.55, gain=0.38),
    'bassfunk':  dict(wave='pulse', duty=0.5, a=0.002, d=0.08, s=0.55, r=0.03, sub=0.6, slide=(-1.0, 0.02), gain=0.38),
    'basssaw':   dict(wave='saw', a=0.003, d=0.15, s=0.6, r=0.05, sub=0.6, drive=1.8, gain=0.34),
    'basswalk':  dict(wave='tri', quant=0, a=0.004, d=0.25, s=0.45, r=0.06, sub=0.3, gain=0.80),
    # pads / keys
    'pad':       dict(wave='supersaw', a=0.35, d=0.6, s=0.8, r=0.6, gain=0.11),
    'padsoft':   dict(wave='organ', drawbars=(1, 0.45, 0.25, 0.0, 0.1), a=0.4, d=0.6, s=0.85, r=0.7, trem=(0.12, 4.8), gain=0.15),
    'organ':     dict(wave='organ', drawbars=(1, 0.7, 0.5, 0.25, 0.2), a=0.01, d=0.3, s=0.85, r=0.12, trem=(0.1, 6.2), gain=0.14),
    'choir':     dict(wave='organ', drawbars=(1, 0.35, 0.5, 0.1, 0.05), a=0.5, d=0.8, s=0.8, r=0.9, vib=(10, 4.5, 0.3), trem=(0.15, 3.7), gain=0.14),
    'strings':   dict(wave='supersaw', a=0.18, d=0.4, s=0.85, r=0.4, vib=(8, 5.0, 0.25), gain=0.11),
    'epiano':    dict(wave='fm', ratio=1.0, index=2.2, idec=0.35, a=0.002, d=1.4, s=0.0, r=0.25, gain=0.22),
    'bell':      dict(wave='add', parts=((1, 1, 1.4), (2.76, 0.45, 0.5), (5.4, 0.25, 0.25), (8.93, 0.1, 0.1)),
                      a=0.001, d=2.0, s=0.0, r=0.3, gain=0.22),
    'vibes':     dict(wave='add', parts=((1, 1, 1.6), (4.0, 0.18, 0.35), (10.0, 0.04, 0.09)),
                      a=0.002, d=2.0, s=0.0, r=0.35, trem=(0.25, 5.5), gain=0.30),
    'marimba':   dict(wave='add', parts=((1, 1, 0.35), (4.0, 0.28, 0.07), (9.9, 0.07, 0.02)),
                      a=0.001, d=0.6, s=0.0, r=0.1, gain=0.45),
    'steel':     dict(wave='add', parts=((1, 1, 0.9), (2.0, 0.6, 0.45), (3.0, 0.32, 0.22), (4.02, 0.12, 0.12)),
                      a=0.003, d=1.2, s=0.0, r=0.15, slide=(0.25, 0.02), gain=0.55),
    'timp':      dict(wave='add', parts=((1, 1, 1.1), (1.5, 0.45, 0.7), (1.98, 0.3, 0.5), (2.44, 0.18, 0.35)),
                      a=0.002, d=1.6, s=0.0, r=0.3, pdrop=(0.6, 0.05), noise=0.25, gain=0.55),
    'flute':     dict(wave='tri', quant=0, a=0.06, d=0.3, s=0.8, r=0.2, vib=(14, 5.0, 0.25), breath=0.06, gain=0.42),
    'brass':     dict(wave='saw', a=0.03, d=0.2, s=0.8, r=0.1, vib=(10, 5.5, 0.2), detune=6, slide=(-0.6, 0.04), gain=0.22),
}


def osc_wave(p, f, t):
    w = p['wave']
    if w == 'pulse':
        duty = p.get('duty', 0.5)
        if isinstance(duty, tuple):
            d0, d1, ts = duty
            duty = d0 + (d1 - d0) * np.clip(t / ts, 0, 1)
        return osc_pulse(f, duty)
    if w == 'saw':
        return osc_saw(f)
    if w == 'tri':
        return osc_tri(f, p.get('quant', 0))
    if w == 'sine':
        return osc_sine(f)
    if w == 'supersaw':
        return (osc_saw(f * 2 ** (-11 / 1200)) + osc_saw(f) * 0.8 + osc_saw(f * 2 ** (12 / 1200))) / 2.2
    if w == 'organ':
        y = np.zeros_like(f)
        ph, _ = _phase(f)
        for h, a in zip((1, 2, 3, 4, 6), p['drawbars']):
            if a and np.max(f) * h < SR / 2.2:
                y += a * np.sin(2 * np.pi * ph * h)
        return y / sum(p['drawbars'])
    if w == 'fm':
        ph, _ = _phase(f)
        idx = p['index'] * np.exp(-t / p['idec']) + p.get('ifloor', 0.15)
        return np.sin(2 * np.pi * ph + idx * np.sin(2 * np.pi * ph * p['ratio']))
    if w == 'add':
        ph, _ = _phase(f)
        y = np.zeros_like(f)
        for r, a, tau in p['parts']:
            if np.max(f) * r < SR / 2.2:
                y += a * np.sin(2 * np.pi * ph * r + r) * np.exp(-t / tau)
        return y
    if w == 'pluck':
        br = np.exp(-t / p.get('bright', 0.08))
        return br * osc_saw(f) + (1 - br) * osc_tri(f) * 0.9
    raise ValueError(w)


def render_note(inst, pitch, dur, vel=1.0, **over):
    """Render one note. pitch: midi number / note name; dur: gate in seconds."""
    p = dict(INST[inst]) if isinstance(inst, str) else dict(inst)
    p.update(over)
    f0 = hz(pitch)
    ng = max(16, int(dur * SR))
    env = adsr(ng, p.get('a', 0.005), p.get('d', 0.1), p.get('s', 0.7), p.get('r', 0.08))
    n = len(env)
    t = secs(n)
    f = np.full(n, f0)
    if 'slide' in p:
        semi, st = p['slide']
        f *= 2.0 ** (semi * np.exp(-t / st) / 12.0)
    if 'pdrop' in p:
        semi, st = p['pdrop']
        f *= 2.0 ** (semi * np.exp(-t / st) / 12.0)
    if 'vib' in p:
        dep, rate, dl = p['vib']
        ramp = np.clip((t - dl) / 0.2, 0, 1)
        f *= 2.0 ** (dep / 1200.0 * np.sin(2 * np.pi * rate * t) * ramp)
    y = osc_wave(p, f, t)
    if p.get('detune'):
        y = 0.6 * y + 0.6 * osc_wave(p, f * 2 ** (p['detune'] / 1200.0), t)
    if p.get('sub'):
        y = y + p['sub'] * osc_sine(f * 0.5 if p.get('suboct') else f)
    if p.get('drive'):
        y = np.tanh(y * p['drive']) / math.tanh(p['drive'])
    if p.get('breath'):
        nz = rng_for('breath%d' % int(f0)).standard_normal(n)
        y = y + p['breath'] * filt(nz, r_bp(f0 * 1.5, f0 * 6, 1))
    if p.get('noise'):
        nz = rng_for('tn%d' % int(f0)).standard_normal(n)
        y = y + p['noise'] * filt(nz, r_bp(200, 2500, 1)) * np.exp(-t / 0.03)
    if 'trem' in p:
        dep, rate = p['trem']
        y = y * (1.0 - dep * 0.5 * (1 + np.sin(2 * np.pi * rate * t)))
    return y * env * vel * p.get('gain', 0.3)


# ---------------------------------------------------------------------------
# drum kit (all synthesized, cached)
# ---------------------------------------------------------------------------
_DRUM_CACHE = {}


def _sweep_sine(n, f_start, f_end, tau):
    t = secs(n)
    f = f_end + (f_start - f_end) * np.exp(-t / tau)
    return osc_sine(f)


def _noise(n, key):
    return rng_for(key).standard_normal(n)


def _metal(n, base, ratios, amps, taus, key):
    t = secs(n)
    rng = rng_for(key)
    y = np.zeros(n)
    for r, a, tau in zip(ratios, amps, taus):
        y += a * np.sin(2 * np.pi * base * r * t + rng.uniform(0, 6.28)) * np.exp(-t / tau)
    return y


def drum(name):
    if name in _DRUM_CACHE:
        return _DRUM_CACHE[name]
    L = lambda s: int(s * SR)
    if name in ('kick', 'kick_hard', 'kick_soft', 'kick_chip'):
        cfg = {'kick': (165, 50, 0.032, 0.30, 1.2), 'kick_hard': (190, 46, 0.03, 0.30, 2.2),
               'kick_soft': (120, 52, 0.03, 0.22, 1.0), 'kick_chip': (210, 55, 0.025, 0.24, 1.0)}[name]
        n = L(cfg[3] * 2.2)
        y = _sweep_sine(n, cfg[0], cfg[1], cfg[2]) * env_exp(n, cfg[3], 0.0008)
        if name == 'kick_chip':
            y = 0.6 * y + 0.4 * osc_tri(cfg[1] + (cfg[0] - cfg[1]) * np.exp(-secs(n) / cfg[2]), 16) * env_exp(n, cfg[3] * 0.7)
        click = filt(_noise(L(0.006), 'kc' + name), r_hp(1800)) * np.linspace(1, 0, L(0.006))
        y[:len(click)] += click * (0.35 if name != 'kick_soft' else 0.12)
        y = np.tanh(y * cfg[4]) / math.tanh(cfg[4])
    elif name in ('snare', 'snare_chip', 'snare_big', 'snare_gate'):
        dec = {'snare': 0.16, 'snare_chip': 0.13, 'snare_big': 0.32, 'snare_gate': 0.5}[name]
        n = L(dec * 2.5)
        t = secs(n)
        body = _sweep_sine(n, 240, 175, 0.02) * env_exp(n, 0.07)
        if name == 'snare_chip':
            nz = osc_lfsr(n, 15000 - 6000 * np.exp(-t / 0.03))
            nz = filt(nz, r_lp(9000, 1))
        else:
            nz = filt(_noise(n, 'sn' + name), r_bp(900, 9000, 1))
        y = 0.55 * body + 0.65 * nz * env_exp(n, dec)
        if name == 'snare_big':
            y = y + 0.35 * filt(_noise(n, 'snb'), r_bp(300, 2000)) * env_exp(n, 0.12)
        if name == 'snare_gate':
            g = np.clip((0.22 - t) / 0.02, 0, 1)
            y = (0.55 * body + 0.6 * nz * (0.35 + 0.65 * env_exp(n, 0.06))) * g
        y = np.tanh(1.5 * y)
    elif name == 'clap':
        n = L(0.35)
        t = secs(n)
        nz = filt(_noise(n, 'clap'), r_bp(900, 4000, 2))
        e = np.zeros(n)
        for k, d in enumerate((0.0, 0.011, 0.022, 0.031)):
            e += (t >= d) * np.exp(-np.maximum(t - d, 0) / (0.008 if k < 3 else 0.11))
        y = nz * e * 0.8
    elif name == 'rim':
        n = L(0.08)
        t = secs(n)
        y = np.sin(2 * np.pi * 1750 * t) * np.exp(-t / 0.012) + 0.5 * filt(_noise(n, 'rim'), r_bp(2000, 8000)) * np.exp(-t / 0.006)
    elif name in ('hat', 'hat_chip', 'ohat', 'ohat_chip'):
        dec = {'hat': 0.035, 'hat_chip': 0.03, 'ohat': 0.24, 'ohat_chip': 0.2}[name]
        n = L(dec * 4 + 0.01)
        if 'chip' in name:
            nz = osc_lfsr(n, 26000, short=False)
            nz = filt(nz, r_hp(6000, 2))
        else:
            nz = filt(_noise(n, name), r_hp(7000, 2))
            nz = nz + 0.3 * _metal(n, 3400, (1, 1.47, 1.83, 2.41), (1, 0.8, 0.6, 0.5), (0.05,) * 4, name)
            nz = filt(nz, r_hp(6000, 2))
        y = nz * env_exp(n, dec, 0.0005)
    elif name == 'ride':
        n = L(1.2)
        y = 0.6 * filt(_noise(n, 'ride'), r_hp(5000, 2)) * env_exp(n, 0.45)
        y += 0.5 * _metal(n, 2900, (1, 1.34, 1.79, 2.21, 2.66), (1, 0.7, 0.6, 0.4, 0.3), (0.6, 0.5, 0.4, 0.3, 0.25), 'ride')
        y = filt(y, r_hp(1800, 2))
    elif name in ('crash', 'crash_rev'):
        n = L(1.8)
        y = filt(_noise(n, 'crash'), r_hp(3500, 2), r_peak(6000, 4, 1.5)) * env_exp(n, 0.55, 0.002)
        y += 0.25 * _metal(n, 2300, (1, 1.41, 1.93, 2.37, 3.11), (1, 0.8, 0.6, 0.5, 0.4), (0.5,) * 5, 'crash')
        if name == 'crash_rev':
            y = y[::-1] * np.linspace(0.2, 1, n) ** 2
    elif name in ('brush', 'brush_tap'):
        n = L(0.25 if name == 'brush' else 0.09)
        t = secs(n)
        e = (np.minimum(t / 0.05, 1) * np.exp(-t / 0.07)) if name == 'brush' else env_exp(n, 0.025)
        y = filt(_noise(n, name), r_bp(1500, 7000, 1)) * e
    elif name == 'shaker':
        n = L(0.11)
        t = secs(n)
        y = filt(_noise(n, 'shk'), r_hp(5500, 2)) * np.minimum(t / 0.012, 1) * np.exp(-t / 0.03)
    elif name == 'cowbell':
        n = L(0.3)
        t = secs(n)
        y = osc_pulse(np.full(n, 587.0)) + osc_pulse(np.full(n, 845.0))
        y = filt(y, r_bp(550, 2600, 2)) * (0.6 * np.exp(-t / 0.03) + 0.4 * np.exp(-t / 0.12))
    elif name == 'clave':
        n = L(0.08)
        t = secs(n)
        y = np.sin(2 * np.pi * 2450 * t) * np.exp(-t / 0.018)
    elif name in ('timbale_hi', 'timbale_lo', 'tom_hi', 'tom_mid', 'tom_lo', 'tom_chip'):
        f, dec, ring = {'timbale_hi': (440, 0.14, 0.6), 'timbale_lo': (330, 0.16, 0.6), 'tom_hi': (210, 0.24, 0.2),
                        'tom_mid': (155, 0.28, 0.2), 'tom_lo': (105, 0.34, 0.2), 'tom_chip': (180, 0.2, 0.0)}[name]
        n = L(dec * 3)
        t = secs(n)
        if name == 'tom_chip':
            y = osc_tri(f * 0.6 + f * 1.4 * np.exp(-t / 0.05), 16) * env_exp(n, dec)
        else:
            y = _sweep_sine(n, f * 1.5, f, 0.03) * env_exp(n, dec)
            y += ring * np.sin(2 * np.pi * f * 2.3 * t) * np.exp(-t / dec * 1.5) * 0.4
            y += 0.3 * filt(_noise(n, name), r_bp(1000, 6000)) * np.exp(-t / 0.01)
    elif name == 'anvil':
        n = L(0.7)
        y = _metal(n, 880, (1, 2.76, 5.40, 8.93), (1, 0.6, 0.35, 0.2), (0.35, 0.22, 0.12, 0.06), 'anvil')
        y += 0.5 * filt(_noise(n, 'anv'), r_hp(3000)) * env_exp(n, 0.008)
    elif name == 'clank':
        n = L(0.6)
        y = _metal(n, 410, (1, 2.32, 4.25, 6.63, 9.1), (1, 0.7, 0.5, 0.3, 0.15), (0.3, 0.2, 0.12, 0.08, 0.05), 'clank')
        y += 0.6 * filt(_noise(n, 'clk'), r_bp(1500, 7000)) * env_exp(n, 0.02)
        y = np.tanh(1.6 * y)
    elif name == 'pipe':
        n = L(0.5)
        y = _metal(n, 262, (1, 2.76, 5.40), (1, 0.4, 0.2), (0.4, 0.18, 0.08), 'pipe')
        y += 0.4 * filt(_noise(n, 'pip'), r_bp(800, 4000)) * env_exp(n, 0.015)
    elif name == 'chain':
        n = L(0.3)
        y = np.zeros(n)
        rng = rng_for('chain')
        for k in range(9):
            pos = int(rng.uniform(0, 0.22) * SR)
            m = L(0.05)
            hit = _metal(m, rng.uniform(2500, 4200), (1, 1.6, 2.3), (1, 0.5, 0.3), (0.02, 0.012, 0.008), 'ch%d' % k)
            mix_into(y, pos, hit, rng.uniform(0.4, 1.0))
    elif name == 'hiss':
        n = L(0.9)
        t = secs(n)
        y = filt(_noise(n, 'hiss'), r_bp(2500, 9000, 1)) * np.minimum(t / 0.08, 1) * np.exp(-t / 0.28)
    elif name == 'thunder':
        n = L(3.4)
        t = secs(n)
        nz = filt(_noise(n, 'thunder'), r_lp(260, 2))
        crack = filt(_noise(n, 'thc'), r_bp(400, 3000)) * np.exp(-np.maximum(t - 0.05, 0) / 0.15) * (t > 0.05)
        y = (nz * np.minimum(t / 0.25, 1) * np.exp(-t / 1.1) * 2.5 + 0.35 * crack)
    elif name == 'tick':
        n = L(0.03)
        t = secs(n)
        y = filt(_noise(n, 'tick'), r_bp(3000, 9000)) * np.exp(-t / 0.003) + 0.6 * np.sin(2 * np.pi * 3100 * t) * np.exp(-t / 0.006)
    elif name == 'zap':
        n = L(0.12)
        t = secs(n)
        y = osc_pulse(220 + 1400 * np.exp(-t / 0.018), 0.5) * env_exp(n, 0.04) * 0.6
    elif name == 'heart':
        n = L(0.5)
        y = drum('kick_soft')[:n].copy() if len(drum('kick_soft')) >= n else fit(drum('kick_soft'), n)
        mix_into(y, L(0.17), fit(drum('kick_soft'), n) * 0.6)
        y = filt(y, r_lp(400))
    else:
        raise ValueError('unknown drum ' + name)
    y = fade(np.asarray(y, dtype=np.float64), 0.0003, 0.004)
    y /= (np.max(np.abs(y)) + 1e-9)
    _DRUM_CACHE[name] = y
    return y


# default mixer slot per drum: (bus, pan, gain, room send)
DRUM_MIX = {
    'kick': ('kick', 0.0, 0.62, 0.05), 'kick_hard': ('kick', 0.0, 0.7, 0.06), 'kick_soft': ('kick', 0.0, 0.6, 0.05),
    'kick_chip': ('kick', 0.0, 0.72, 0.05),
    'snare': ('snare', 0.04, 0.55, 0.22), 'snare_chip': ('snare', 0.04, 0.55, 0.2), 'snare_big': ('snare', 0.0, 0.6, 0.35),
    'snare_gate': ('snare', 0.0, 0.55, 0.12), 'clap': ('snare', -0.05, 0.5, 0.3), 'rim': ('perc', -0.2, 0.32, 0.25),
    'hat': ('hats', 0.28, 0.26, 0.05), 'hat_chip': ('hats', 0.28, 0.24, 0.05), 'ohat': ('hats', 0.28, 0.2, 0.1),
    'ohat_chip': ('hats', 0.28, 0.15, 0.1), 'ride': ('cym', -0.3, 0.2, 0.12), 'crash': ('cym', -0.22, 0.24, 0.15),
    'crash_rev': ('cym', 0.22, 0.2, 0.1),
    'brush': ('perc', 0.15, 0.13, 0.15), 'brush_tap': ('perc', 0.15, 0.13, 0.15), 'shaker': ('hats', 0.4, 0.18, 0.05),
    'cowbell': ('perc', -0.35, 0.12, 0.15), 'clave': ('perc', 0.38, 0.16, 0.15),
    'timbale_hi': ('perc', 0.35, 0.3, 0.2), 'timbale_lo': ('perc', -0.3, 0.3, 0.2),
    'tom_hi': ('toms', 0.3, 0.45, 0.2), 'tom_mid': ('toms', 0.0, 0.48, 0.2), 'tom_lo': ('toms', -0.3, 0.52, 0.2),
    'tom_chip': ('toms', 0.15, 0.4, 0.15),
    'anvil': ('metal', 0.35, 0.18, 0.3), 'clank': ('metal', -0.32, 0.25, 0.3), 'pipe': ('metal', 0.1, 0.24, 0.3),
    'chain': ('metal', 0.45, 0.18, 0.25), 'hiss': ('fx', -0.4, 0.12, 0.3), 'thunder': ('fx', 0.0, 0.5, 0.25),
    'tick': ('perc', 0.3, 0.14, 0.1), 'zap': ('perc', -0.3, 0.16, 0.25), 'heart': ('kick', 0.0, 0.8, 0.05),
}


# ---------------------------------------------------------------------------
# harmony helpers
# ---------------------------------------------------------------------------
CHORD_Q = {
    '': (0, 4, 7), 'm': (0, 3, 7), '7': (0, 4, 7, 10), 'm7': (0, 3, 7, 10), 'maj7': (0, 4, 7, 11),
    'dim': (0, 3, 6), 'dim7': (0, 3, 6, 9), 'm7b5': (0, 3, 6, 10), 'aug': (0, 4, 8),
    'sus4': (0, 5, 7), 'sus2': (0, 2, 7), '7sus4': (0, 5, 7, 10), 'add9': (0, 4, 7, 14),
    '6': (0, 4, 7, 9), 'm6': (0, 3, 7, 9), '9': (0, 4, 7, 10, 14), 'm9': (0, 3, 7, 10, 14),
    'maj9': (0, 4, 7, 11, 14), '5': (0, 7), 'madd9': (0, 3, 7, 14),
}
MAJOR = (0, 2, 4, 5, 7, 9, 11)
MINOR = (0, 2, 3, 5, 7, 8, 10)
HMINOR = (0, 2, 3, 5, 7, 8, 11)
MIXO = (0, 2, 4, 5, 7, 9, 10)
DORIAN = (0, 2, 3, 5, 7, 9, 10)


def _pc(s):
    return (_NB[s[0].upper()] + s[1:].count('#') - s[1:].count('b')) % 12


def parse_chord(sym):
    m = re.match(r'^([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?$', sym)
    if not m or m.group(2) not in CHORD_Q:
        raise ValueError('bad chord ' + sym)
    root = _pc(m.group(1))
    return {'root': root, 'ivs': CHORD_Q[m.group(2)], 'bass': _pc(m.group(3)) if m.group(3) else root, 'sym': sym}


def voicing(ch, center=62):
    out = []
    for iv in ch['ivs']:
        pc = (ch['root'] + iv) % 12
        m = center - 6 + ((pc - (center - 6)) % 12)
        out.append(m)
    return sorted(set(out))


def dia_shift(m, k, root, mode):
    """Move midi note m by k scale degrees in (root pc, mode)."""
    pcs = set((root + i) % 12 for i in mode)
    m = int(round(m))
    while m % 12 not in pcs:
        m -= 1
    d = 1 if k > 0 else -1
    for _ in range(abs(k)):
        m += d
        while m % 12 not in pcs:
            m += d
    return m


# ---------------------------------------------------------------------------
# sequencer
# ---------------------------------------------------------------------------
VEL = {'X': 1.0, 'x': 0.72, 'o': 0.42}


def _max_prime(n):
    p, m, best = 2, n, 1
    while p * p <= m:
        while m % p == 0:
            best, m = p, m // p
        p += 1
    return max(best, m)


def _smooth_step(exact):
    """16th-note length in whole samples; nudged (<0.3%) to an FFT-friendly size."""
    base = int(round(exact))
    cands = sorted(range(base - 16, base + 17), key=lambda s: (_max_prime(s) > 7, _max_prime(s) > 13, abs(s - exact)))
    return cands[0]


class Song:
    dry = False     # True: build the arrangement without rendering audio (metadata only)

    def __init__(self, name, bpm, bars, loop=True, swing8=0.5, swing16=0.5, tail=6.0,
                 echo=(3, 0.3), room=(1.1, 0.014), target=-16.0, key=('C', MAJOR), air=-2.0):
        self.name = name
        self.step = _smooth_step(SR * 60.0 / (bpm * 4))
        self.bpm = SR * 60.0 / (self.step * 4)
        self.bpm_nominal = bpm
        self.bars = bars
        self.body = bars * 16 * self.step
        self.loop = loop
        self.n = self.body + int(tail * SR)
        self.swing8, self.swing16 = swing8, swing16
        self.echo, self.room, self.target, self.air = echo, room, target, air
        self.key = (_pc(key[0]), key[1])
        self.key_name = key
        self.buses, self.cfg = {}, {}
        self.timeline = []

    # -- mixer
    def bus(self, name, pan=0.0, gain=1.0, echo=0.0, verb=0.15, lp=None, hp=None, width=0.0):
        self.cfg[name] = dict(pan=pan, gain=gain, echo=echo, verb=verb, lp=lp, hp=hp, width=width)
        if name not in self.buses:
            self.buses[name] = np.zeros(self.n, dtype=np.float32)

    # -- time
    def pos(self, step):
        b = math.floor(step / 4.0 + 1e-9)
        u = step - 4 * b
        if self.swing8 != 0.5:
            r = self.swing8
            u = u / 2 * 4 * r if u < 2 else 4 * r + (u - 2) / 2 * (4 - 4 * r)
        elif self.swing16 != 0.5:
            r = self.swing16
            e = math.floor(u / 2 + 1e-9) * 2
            v = u - e
            v = v * 2 * r if v < 1 else 2 * r + (v - 1) * (2 - 2 * r)
            u = e + v
        return int(round((4 * b + u) * self.step))

    def add(self, bus, step, sig, gain=1.0):
        if Song.dry:
            return
        mix_into(self.buses[bus], self.pos(step), sig.astype(np.float32), gain)

    def note(self, bus, inst, step, dur, pitch, vel=1.0, gate=0.92, **over):
        if Song.dry:
            return
        a, b = self.pos(step), self.pos(step + dur)
        sig = render_note(inst, pitch, max(b - a, 32) * gate / SR, vel, **over)
        mix_into(self.buses[bus], a, sig.astype(np.float32))

    # -- melody DSL: "E5:4 D5:2 r:2 | _:4 [C4,E4]:8 ..." durations in 16ths, '_' ties
    def parse(self, text):
        ev, pos, last = [], 0, 4
        for tok in text.split():
            if tok == '|':
                if pos % 16:
                    raise ValueError('%s: bar line misaligned at step %d in "%s"' % (self.name, pos, text[:60]))
                continue
            v = 1.0
            if tok.endswith('!'):
                v, tok = 1.18, tok[:-1]
            elif tok.endswith('?'):
                v, tok = 0.62, tok[:-1]
            nm, _, d = tok.partition(':')
            dur = float(d) if d else last
            last = dur
            if nm == 'r':
                pos += dur
                continue
            if nm == '_':
                ev[-1][1] += dur
                pos += dur
                continue
            ev.append([pos, dur, [midi_of(p) for p in nm.strip('[]').split(',')], v])
            pos += dur
        return ev, pos

    def mel(self, bus, inst, bar, text, transpose=0, vel=1.0, gate=0.92, dia=0, **over):
        ev, length = self.parse(text)
        for p, d, ps, v in ev:
            for m in ps:
                mm = self.harmonize(m, bar * 16 + p, d, dia) if dia else m
                self.note(bus, inst, bar * 16 + p, d, mm + transpose, vel * v, gate, **over)
        return length

    def harmonize(self, m, step, dur, k):
        """Harmony voice k scale degrees away; for longer notes snap to the nearest
        chord tone on that side so held harmony notes never clash with the chord."""
        d = dia_shift(m, k, *self.key)
        if dur < 3 or not self.timeline:
            return d
        ch = self.chord_at(step)
        pcs = {(ch['root'] + i) % 12 for i in ch['ivs']}
        if int(round(m)) % 12 not in pcs or d % 12 in pcs:
            return d
        lo, hi = (m - 9, m - 3) if k < 0 else (m + 3, m + 9)
        cands = [x for x in range(int(lo), int(hi) + 1) if x % 12 in pcs]
        if not cands:
            return d
        return min(cands, key=lambda x: abs(x - d))

    # -- chords
    def chords(self, bar, text):
        pos = bar * 16
        for tok in text.split():
            if tok == '|':
                continue
            sym, _, beats = tok.partition(':')
            ln = int(float(beats) * 4) if beats else 16
            self.timeline.append((pos, ln, parse_chord(sym)))
            pos += ln
        self.timeline.sort(key=lambda e: e[0])
        return pos

    def chord_at(self, step):
        step %= self.bars * 16
        cur = self.timeline[0][2]
        for s, ln, ch in self.timeline:
            if s <= step + 1e-6:
                cur = ch
            else:
                break
        return cur

    def next_chord(self, step):
        step %= self.bars * 16
        for s, ln, ch in self.timeline:
            if s > step + 1e-6:
                return ch
        return self.timeline[0][2]

    def segments(self, bar0, nbars):
        a, b = bar0 * 16, (bar0 + nbars) * 16
        out = []
        for s, ln, ch in self.timeline:
            s0, s1 = max(s, a), min(s + ln, b)
            if s1 > s0:
                out.append((s0, s1 - s0, ch))
        return out

    # -- pattern players
    @staticmethod
    def _hits(pat):
        i = 0
        while i < len(pat):
            c = pat[i]
            if c not in '.-':
                j = i + 1
                while j < len(pat) and pat[j] == '-':
                    j += 1
                yield i, j - i, c
                i = j
            else:
                i += 1

    def bassline(self, bus, inst, bar0, nbars, pattern, octave=2, vel=1.0, gate=0.86, **over):
        pats = pattern if isinstance(pattern, (list, tuple)) else [pattern]
        for bi in range(nbars):
            pat = pats[bi % len(pats)]
            for i, ln, c in self._hits(pat):
                st = (bar0 + bi) * 16 + i
                ch = self.chord_at(st)
                base = 12 * (octave + 1) + ch['bass']
                root = 12 * (octave + 1) + ch['root']
                nxt = self.next_chord(st)
                nroot = 12 * (octave + 1) + nxt['bass']
                if nroot - base > 6:
                    nroot -= 12
                elif base - nroot > 6:
                    nroot += 12
                ivs = ch['ivs']
                m = {'R': base, 'O': base + 12, 'L': base - 12, '5': root + 7, '3': root + ivs[1],
                     '7': root + (ivs[3] if len(ivs) > 3 else 10), '4': root + 5, 'b': root + 1, 'm': root + 3,
                     '6': root + 9, '2': root + 2, 'A': nroot - 1, 'W': nroot - 2, 'U': nroot + 1,
                     'T': root + 6, 'Q': root + 19}.get(c.upper() if c in 'ruowlaq' else c)
                if m is None:
                    continue
                v = vel * (0.7 if c in 'ruowlaq' else 1.0)
                self.note(bus, inst, st, ln, m, v, gate, **over)

    def comp(self, bus, inst, bar0, nbars, rhythm, center=62, vel=1.0, gate=0.8, add_bass=False, **over):
        pats = rhythm if isinstance(rhythm, (list, tuple)) else [rhythm]
        for bi in range(nbars):
            pat = pats[bi % len(pats)]
            for i, ln, c in self._hits(pat):
                st = (bar0 + bi) * 16 + i
                ch = self.chord_at(st)
                v = vel * VEL.get(c, 0.72)
                for m in voicing(ch, center):
                    self.note(bus, inst, st, ln, m, v, gate, **over)

    def pad(self, bus, inst, bar0, nbars, center=60, vel=1.0, gate=1.0, **over):
        for s, ln, ch in self.segments(bar0, nbars):
            for m in voicing(ch, center):
                self.note(bus, inst, s, ln, m, vel, gate, **over)

    def arp(self, bus, inst, bar0, nbars, pattern='0123', rate=1, center=67, span=2, vel=1.0, gate=0.7,
            accent=4, **over):
        k = 0
        for st in np.arange(bar0 * 16, (bar0 + nbars) * 16, rate):
            c = pattern[k % len(pattern)]
            k += 1
            if c == '.':
                continue
            ch = self.chord_at(st)
            base = voicing(ch, center)
            tones = [m + 12 * o for o in range(span) for m in base]
            m = tones[int(c, 36) % len(tones)]
            v = vel * (1.0 if (k - 1) % accent == 0 else 0.72)
            self.note(bus, inst, float(st), rate, m, v, gate, **over)

    def beat(self, bar0, nbars, pats, vel=1.0):
        for name, pat in pats.items():
            pat = pat.replace(' ', '').replace('|', '')
            busn, pan, g, verb = DRUM_MIX[name]
            if busn not in self.buses:
                self.bus(busn, pan=pan, verb=verb)
            sig = drum(name)
            nb = max(1, len(pat) // 16)
            for bi in range(nbars):
                seg = pat[(bi % nb) * 16:(bi % nb) * 16 + 16]
                for i, c in enumerate(seg):
                    if c in VEL:
                        self.add(busn, (bar0 + bi) * 16 + i, sig, g * vel * VEL[c])
                    elif c == 'f':   # flam / drag: two quick hits
                        self.add(busn, (bar0 + bi) * 16 + i, sig, g * vel * 0.45)
                        self.add(busn, (bar0 + bi) * 16 + i + 0.5, sig, g * vel * 0.8)

    def fx(self, bus, step, sig, gain=1.0):
        if bus not in self.buses:
            self.bus(bus, verb=0.2)
        self.add(bus, step, sig, gain)

    # -- render
    def render(self):
        body = self.body
        L = body if self.loop else self.n
        dry = np.zeros((L, 2))
        esend = np.zeros(L)
        vsend = np.zeros((L, 2))
        for name, buf in self.buses.items():
            c = self.cfg[name]
            x = buf.astype(np.float64)
            if self.loop:
                y = x[:body].copy()
                k = body
                while k < len(x):
                    seg = x[k:k + body]
                    y[:len(seg)] += seg
                    k += body
                x = y
            if c['lp'] or c['hp']:
                rs = ([r_lp(c['lp'], 2)] if c['lp'] else []) + ([r_hp(c['hp'], 2)] if c['hp'] else [])
                x = filt(x, *rs, circular=self.loop)
            x *= c['gain']
            th = (c['pan'] + 1.0) * math.pi / 4.0
            gl, gr = math.cos(th) * math.sqrt(2), math.sin(th) * math.sqrt(2)
            xr = x
            if c['width']:
                d = int(c['width'] * SR / 1000.0)
                xr = np.roll(x, d) if self.loop else np.concatenate([np.zeros(d), x[:-d]])
            st = np.stack([x * gl, xr * gr], axis=1)
            dry += st
            esend += (st[:, 0] + st[:, 1]) * 0.5 * c['echo']
            vsend += st * c['verb']
        el, er = echo_ir(self.echo[0] * self.step / SR, self.echo[1])
        rl, rr = room_ir(self.name, self.room[0], self.room[1])
        circ = self.loop
        wet = np.stack([conv(esend, el, circ)[:L], conv(esend, er, circ)[:L]], axis=1)
        vl = conv(vsend[:, 0] + 0.25 * vsend[:, 1], rl, circ)[:L]
        vr = conv(vsend[:, 1] + 0.25 * vsend[:, 0], rr, circ)[:L]
        # echoes also get a little room
        mix = dry + wet + np.stack([vl, vr], axis=1)
        mix = filt(mix, r_shelf_hi(7500, self.air), r_shelf_lo(110, 1.0), circular=circ)
        if not self.loop:
            mix[-int(0.25 * SR):] *= np.linspace(1, 0, int(0.25 * SR))[:, None]
        return master_music(mix, self.target, circular=circ)


# ===========================================================================
# MUSIC  (all melodies are original compositions for BACKSTREET OATH)
# ===========================================================================
def std_mix(s, lead_echo=0.22, pad_gain=1.0, bass_lp=2800):
    s.bus('lead', pan=0.0, gain=1.0, echo=lead_echo, verb=0.18)
    s.bus('lead2', pan=-0.18, gain=0.8, echo=lead_echo, verb=0.2)
    s.bus('harm', pan=0.32, gain=0.75, echo=lead_echo * 0.7, verb=0.2)
    s.bus('bass', pan=0.0, gain=1.0, echo=0.0, verb=0.03, lp=bass_lp)
    s.bus('padL', pan=-0.65, gain=pad_gain, verb=0.3, lp=5200)
    s.bus('padR', pan=0.65, gain=pad_gain, verb=0.3, lp=5200)
    s.bus('comp', pan=-0.3, gain=0.85, echo=0.08, verb=0.15)
    s.bus('arp', pan=0.42, gain=0.8, echo=0.3, verb=0.16)
    s.bus('keys', pan=0.25, gain=0.9, echo=0.1, verb=0.25)


def wide_pad(s, inst, bar0, nbars, center=60, vel=1.0, **kw):
    s.pad('padL', inst, bar0, nbars, center, vel, **kw)
    s.pad('padR', inst, bar0, nbars, center, vel, detune=9, **kw)


FILL_SN = 'X.x.X.xxXxXxXXXX'

# ---- TITLE: D major, 118 BPM -------------------------------------------------
TITLE_A = ('A4:2 D5:2 F#5:4 E5:2 D5:2 E5:4 | F#5:6 D5:2 B4:4 D5:4 | G5:3 F#5:3 E5:2 D5:4 B4:4 | '
           'C#5:4 E5:4 A5:8 | A4:2 D5:2 F#5:4 E5:2 D5:2 A5:4 | A5:3 G5:3 F#5:2 C#5:8 | '
           'B5:4 A5:2 G5:2 F#5:4 E5:4 | E5:2 D5:2 C#5:2 D5:2 E5:8')
TITLE_B = ('B4:4 E5:4 G5:6 F#5:2 | G5:2 A5:2 B5:4 A5:4 G5:4 | F#5:8 A5:4 F#5:4 | E5:12 r:4 | '
           'B4:4 E5:4 G5:4 B5:4 | D6:6 B5:2 G5:4 B5:4 | A5:4 C#6:4 E6:4 C#6:4 | A5:8 G5:2 F#5:2 E5:2 C#5:2')
TITLE_CH_A = 'D Bm G A D F#m G A'
TITLE_CH_B = 'Em G D A Em G A Asus4:2 A:2'


def m_title():
    s = Song('title', 118, 24, key=('D', MAJOR), echo=(3, 0.3), room=(1.2, 0.014))
    std_mix(s)
    s.chords(0, TITLE_CH_A)
    s.chords(8, TITLE_CH_B)
    s.chords(16, TITLE_CH_A)
    # lead
    s.mel('lead', 'lead', 0, TITLE_A)
    s.mel('lead', 'lead', 8, TITLE_B)
    s.mel('lead', 'lead', 16, TITLE_A, vel=1.05)
    s.mel('harm', 'harm', 16, TITLE_A, dia=-2, vel=0.9)
    s.mel('lead2', 'leadsaw', 16, TITLE_A, transpose=-12, vel=0.55)
    s.mel('harm', 'bell', 8, 'D6:16 | B5:16 | A5:16 | C#6:16 | B5:16 | D6:16 | E6:16 | E6:8 C#6:8', vel=0.6)
    # harmony bed
    wide_pad(s, 'pad', 0, 24, 60)
    s.comp('comp', 'brass', 16, 8, 'X-----x-..x-x-..', center=64, vel=0.7)
    s.arp('arp', 'arp', 8, 8, '0123', rate=1, center=72, vel=0.8)
    s.arp('arp', 'arp', 16, 8, '02130213', rate=2, center=74, vel=0.7)
    # bass
    drive = ['R.R.R.R.R.R.O.R.', 'R.R.R.R.R.R.O.R.', 'R.R.R.R.R.R.O.R.', 'R.R.R.R.R.O.R.A.']
    s.bassline('bass', 'bass', 0, 24, drive)
    # drums
    a1 = {'kick_chip': 'X.......X.x.....', 'snare_chip': '....X.......X...', 'hat_chip': 'x.x.x.x.x.x.x.x.'}
    b1 = {'kick_chip': 'X.....x.X.x.....', 'snare_chip': '....X.......X..o', 'hat_chip': 'xxoxxxoxxxoxxxox'}
    a2 = {'kick_chip': 'X...X...X...X...', 'snare_chip': '....X.......X...', 'hat_chip': 'x.x.x.x.x.x.x.x.',
          'ohat_chip': '..o...o...o...o.'}
    for bar0, pat in ((0, a1), (8, b1), (16, a2)):
        s.beat(bar0, 7, pat)
        s.beat(bar0 + 7, 1, {'kick_chip': 'X.......X.......', 'snare_chip': FILL_SN,
                             'tom_chip': '........x.x.x.x.'})
        s.beat(bar0, 1, {'crash': 'X...............'})
    s.beat(12, 1, {'crash': 'x...............'})
    return s


# ---- OLD QUARTER: G mixolydian funk, 112 BPM ---------------------------------
OQ_A = ('r:2 D5:1 F5:1 G5:2 D5:2 F5:2 G5:1 F5:1 D5:4 | C5:2 D5:2 F5:3 A5:3 G5:2 F5:4 | '
        'E5:4 G5:2 E5:2 C5:2 D5:2 E5:4 | D5:12 r:4 | r:2 D5:1 F5:1 G5:2 B5:2 A5:2 G5:1 F5:1 G5:4 | '
        'A5:3 C6:3 A5:2 G5:2 F5:2 D5:4 | E5:2 G5:2 C6:4 B5:2 A5:2 G5:4 | F#5:4 A5:4 D6:6 C6:2')
OQ_A2_END = 'F#5:2 A5:2 C6:2 B5:2 A5:2 F#5:2 D5:4'
OQ_B = ('B5:6 A5:2 G5:4 E5:4 | G5:4 A5:4 C6:4 B5:2 A5:2 | B5:8 G5:4 E5:4 | F#5:8 r:2 D5:2 E5:2 F#5:2 | '
        'G5:6 F#5:2 E5:4 B4:4 | C5:4 E5:4 A5:4 G5:2 E5:2 | G5:4 E5:2 G5:2 C6:4 B5:4 | A5:4 F#5:2 A5:2 C6:4 B5:2 A5:2')
OQ_C = ('G5:1 G5:1 r:2 Bb5:2 G5:2 F5:2 G5:2 r:4 | D5:2 F5:2 G5:2 Bb5:2 B5:1 C6:1 B5:2 G5:4 | '
        'D6:2 C6:2 Bb5:2 F5:2 E5:2 G5:2 C6:4 | A5:4 F#5:4 D5:2 E5:2 F#5:2 A5:2')
OQ_FILL = 'r:12 F5:1 G5:1 Bb5:1 B5:1'   # organ answer in the gaps


def m_old_quarter():
    s = Song('old_quarter', 112, 32, key=('G', MIXO), swing16=0.57, echo=(3, 0.28), room=(0.9, 0.012))
    std_mix(s, lead_echo=0.18)
    s.chords(0, 'G F C G G F C D')
    s.chords(8, 'G F C G G F C D')
    s.chords(16, 'Em7 Am7 Cmaj7 D Em7 Am7 C D7')
    s.chords(24, 'G7 G7 Bb C G7 G7 Bb:2 C:2 D')
    s.mel('lead', 'lead', 0, OQ_A)
    a2 = OQ_A.rsplit('|', 1)[0] + '| ' + OQ_A2_END
    s.mel('lead', 'lead', 8, a2)
    s.mel('lead2', 'lead12', 8, a2, transpose=12, vel=0.4)
    s.mel('lead', 'lead50', 16, OQ_B, vel=0.9)
    s.mel('keys', 'organ', 16, OQ_B, transpose=-12, vel=0.8)
    s.mel('lead', 'lead', 28, OQ_C)
    s.mel('lead2', 'brass', 28, OQ_C, transpose=-12, vel=0.55)
    for b in (3, 11):
        s.mel('keys', 'organ', b, OQ_FILL, vel=0.9)
    # comping
    clav = ['..x...x...x..x.x', '..x...x..x..x.x.']
    s.comp('comp', 'clav', 0, 16, clav, center=65, vel=0.9)
    s.pad('keys', 'organ', 16, 8, 60, vel=0.55)
    s.comp('comp', 'clav', 16, 8, '..x...x...x...x.', center=67, vel=0.6)
    s.comp('comp', 'stab', 24, 8, 'X..x..X.........', center=64, vel=0.9)
    s.comp('comp', 'clav', 26, 6, '..x...x..x..x.x.', center=65, vel=0.8)
    wide_pad(s, 'padsoft', 0, 32, 57, vel=0.7)
    # bass
    s.bassline('bass', 'bassfunk', 0, 16, ['R-.r..O.R.5.7.O.', 'R-.r..O.R..oR.5A'])
    s.bassline('bass', 'bassfunk', 16, 8, ['R-..R-.5R-..3-5-', 'R-..R-.5R-.oR-5A'])
    s.bassline('bass', 'bassfunk', 24, 8, ['R-.R.R-7.R-O.5.4', 'R-.R.R-7.RO.7.5A'])
    # drums
    groove = {'kick': 'X..x..x...X..x..', 'snare': '....X..o.o..X..o', 'hat': 'XxoxXxoxXxoxXxox'}
    groove2 = {'kick': 'X..x..x...X..x..', 'snare': '....X..o.o..X.o.', 'hat': 'XxoxXxoxXxoxXx..', 'ohat': '..............x.'}
    for b0 in (0, 8, 16):
        s.beat(b0, 3, groove)
        s.beat(b0 + 3, 1, groove2)
        s.beat(b0 + 4, 3, groove)
        s.beat(b0 + 7, 1, {'kick': 'X..x..x...X.....', 'snare': '....X..o..xxXxXX', 'hat': 'XxoxXxoxXx......'})
    s.beat(0, 1, {'crash': 'X...............'})
    s.beat(16, 1, {'crash': 'X...............'})
    s.beat(24, 2, {'kick': 'X.........X.....', 'snare': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.'})
    s.beat(26, 5, groove)
    s.beat(26, 1, {'crash': 'x...............'})
    s.beat(31, 1, {'kick': 'X..x..x...X..x..', 'snare': '....X..o..x.XxXX', 'hat': 'XxoxXxoxXxox....', 'ohat': '............x...'})
    s.beat(16, 8, {'cowbell': '..o...o...o...o.'})
    return s


# ---- CANAL MARKET: F major calypso/ska, 124 BPM ------------------------------
CM_A = ('C5:2 F5:3 A5:3 G5:2 F5:2 A5:4 | Bb5:3 A5:3 G5:2 F5:2 D5:2 F5:4 | E5:3 G5:3 Bb5:2 A5:2 G5:2 E5:4 | '
        'F5:6 A5:2 C6:4 r:4 | C6:3 A5:3 F5:2 G5:2 A5:2 C6:4 | D6:3 C6:3 Bb5:2 A5:2 G5:2 Bb5:4 | '
        'A5:3 G5:3 E5:2 C5:2 E5:2 G5:4 | F5:8 r:2 C5:2 D5:2 E5:2')
CM_B = ('A5:2 A5:2 r:2 A5:2 G5:2 F5:2 D5:4 | Bb5:2 Bb5:2 r:2 Bb5:2 A5:2 G5:2 D5:4 | C6:3 Bb5:3 G5:2 E5:2 G5:2 C6:4 | '
        'A5:12 r:4 | F5:2 A5:2 D6:4 C6:2 A5:2 F5:4 | G5:2 Bb5:2 D6:4 C6:2 Bb5:2 G5:4 | '
        'D6:3 C6:3 Bb5:2 C6:3 Bb5:3 G5:2 | A5:4 F5:4 C5:4 r:4')


def m_canal_market():
    s = Song('canal_market', 124, 32, key=('F', MAJOR), echo=(3, 0.25), room=(0.8, 0.01), air=-1.5)
    std_mix(s, lead_echo=0.14)
    s.bus('steel', pan=0.08, gain=1.0, echo=0.14, verb=0.22)
    s.bus('mar', pan=-0.35, gain=0.9, echo=0.05, verb=0.2)
    ca = 'F Bb C7 F F Bb C7 F'
    s.chords(0, ca)
    s.chords(8, ca)
    s.chords(16, 'Dm Gm C7 F Dm Gm Bb:2 C7:2 F')
    s.chords(24, ca)
    s.mel('steel', 'steel', 0, CM_A)
    s.mel('steel', 'steel', 8, CM_A)
    s.mel('mar', 'marimba', 8, CM_A, dia=-2, vel=0.8)
    s.mel('steel', 'steel', 16, CM_B)
    s.mel('lead', 'flute', 16, CM_B, transpose=-12, vel=0.55)
    s.mel('steel', 'steel', 24, CM_A, vel=1.05)
    s.mel('lead2', 'lead12', 24, CM_A, transpose=12, vel=0.3, gate=0.6)
    s.mel('mar', 'marimba', 24, CM_A, dia=-2, vel=0.7)
    # skank + organ bubble
    s.comp('comp', 'skank', 0, 32, '..x...x...x...x.', center=67, vel=0.9)
    s.comp('keys', 'organ', 16, 8, '.x.x.x.x.x.x.x.x', center=60, vel=0.5, gate=0.5)
    wide_pad(s, 'padsoft', 0, 32, 58, vel=0.55)
    s.arp('arp', 'marimba', 0, 8, '0.1.2.1.0.2.1.3.', rate=1, center=72, vel=0.4)
    # calypso bass
    s.bassline('bass', 'bass', 0, 32, ['R--5--R-R--5--3-', 'R--5--R-R--5--3-', 'R--5--R-R--5--3-', 'R--5--R-R-3-5-A-'])
    # drums
    g = {'kick': 'X...X...X...X...', 'snare_chip': '....X.......X..o', 'shaker': 'xoxoxoxoxoxoxoxo',
         'clave': 'X..X..X...X.X...'}
    for b0 in (0, 8, 16, 24):
        s.beat(b0, 7, g)
        s.beat(b0 + 7, 1, {'kick': 'X...X...X...X...', 'shaker': 'xoxoxoxoxoxoxoxo',
                           'timbale_hi': '........x.x.xxx.', 'timbale_lo': '..........x...xX'})
        s.beat(b0, 1, {'crash': 'x...............'})
    s.beat(16, 8, {'cowbell': 'x.o.x.o.x.o.x.o.'})
    s.beat(24, 8, {'ohat': '..o...o...o...o.'})
    return s


# ---- IRONWORKS: E minor industrial, 100 BPM ----------------------------------
IW_A = ('E5:6 F#5:2 G5:4 F#5:4 | E5:4 D5:4 B4:8 | C5:4 E5:4 G5:6 F#5:2 | F#5:8 D5:4 A4:4 | '
        'E5:6 F#5:2 G5:4 B5:4 | A5:4 G5:4 F#5:4 E5:4 | G5:6 E5:2 C5:4 E5:4 | D#5:8 F#5:4 B4:4')
IW_B = ('A5:8 C6:4 B5:4 | G5:8 E5:8 | F5:4 A5:4 C6:4 A5:4 | B5:12 r:4 | '
        'E6:6 D6:2 C6:4 A5:4 | B5:6 A5:2 G5:4 E5:4 | F5:4 A5:4 C6:4 E6:4 | D#6:8 B5:4 F#5:4')


def m_ironworks():
    s = Song('ironworks', 100, 28, key=('E', MINOR), echo=(4, 0.3), room=(1.5, 0.02), air=-2.5)
    std_mix(s, lead_echo=0.2, bass_lp=2200)
    s.bus('metal', pan=0.0, gain=1.0, verb=0.3, echo=0.12)
    s.bus('kick', gain=0.45, verb=0.06, hp=36)
    s.bus('lead', gain=1.7, echo=0.2, verb=0.2)
    s.bus('bass', gain=1.7, verb=0.03, lp=2200, hp=36)
    ca = 'Em Em C D Em Em C B'
    s.chords(0, ca)
    s.chords(8, 'Am Em F Em Am Em F B7')
    s.chords(16, 'E5 E5 E5 E5')
    s.chords(20, ca)
    s.mel('lead', 'leadsaw', 0, IW_A, vel=0.95)
    s.mel('lead2', 'lead12', 0, IW_A, transpose=12, vel=0.25)
    s.mel('lead', 'leadsaw', 8, IW_B)
    s.mel('harm', 'lead50', 8, IW_B, transpose=-12, vel=0.5)
    s.mel('lead', 'leadsaw', 20, IW_A)
    s.mel('harm', 'harm', 20, IW_A, dia=-2, vel=0.75)
    wide_pad(s, 'choir', 0, 8, 55, vel=0.8)
    wide_pad(s, 'strings', 8, 8, 57, vel=0.85)
    wide_pad(s, 'choir', 16, 12, 55, vel=0.8)
    s.mel('keys', 'bell', 16, 'E5:8 B4:8 | G5:8 F#5:8 | E5:8 B4:8 | D#5:16', vel=0.55)
    # bass riff
    em1, em2 = 'R-R.R-.bR-.O-5.m', 'R-R.R-.bR-.Om.5R'
    oth, end = 'R-R.R-R.R-.O-5.R', 'R-R.R-R.R-.O5.AW'
    s.bassline('bass', 'basssaw', 0, 8, [em1, em2, oth, oth, em1, em2, oth, end], octave=1, sub=0.25)
    s.bassline('bass', 'basssaw', 8, 8, ['R-R.R-R.R-.O-5.R'] * 7 + [end], octave=1, sub=0.25)
    s.bassline('bass', 'basssaw', 16, 4, ['R-..R-..R-..R-..', 'R-..R-..R-.bR-.b'], octave=1, sub=0.25)
    s.bassline('bass', 'basssaw', 20, 8, [em1, em2, oth, oth, em1, em2, oth, end], octave=1, sub=0.25)
    # drums: heavy half-time + metal shop
    half = {'kick_hard': 'X.....x.X.x.....', 'snare_big': '........X.......', 'hat_chip': 'x.x.x.x.x.x.x.x.',
            'anvil': '..x.......x..x..', 'clank': '......X.......x.'}
    full = {'kick_hard': 'X.x...x.X.x...x.', 'snare_big': '....X.......X...', 'hat_chip': 'xxxxxxxxxxxxxxxx',
            'anvil': '..x.......x.....', 'clank': '......X.....X...', 'pipe': 'x...............'}
    s.beat(0, 7, half)
    s.beat(7, 1, {'kick_hard': 'X.....x.X.......', 'snare_big': '........X.X.XXXX', 'clank': 'x...x...........'})
    s.beat(8, 7, full)
    s.beat(15, 1, {'kick_hard': 'X.x...x.X.......', 'snare_big': '....X...X.XXXXXX', 'tom_lo': '..........x.x...'})
    s.beat(16, 4, {'kick_hard': 'X.......X.......', 'clank': 'X.....x...x.....', 'anvil': '....x.....x..x.x',
                   'pipe': '..x.......x.....', 'chain': '........X.......'})
    s.beat(18, 2, {'hat_chip': 'x.x.x.x.x.x.x.x.'})
    s.beat(19, 1, {'snare_big': '........x.x.XXXX'})
    s.beat(20, 7, dict(half, ohat_chip='......o.......o.'))
    s.beat(27, 1, {'kick_hard': 'X.....x.X.......', 'snare_big': '........X.X.XXXX', 'clank': 'x...x...........'})
    for b in (0, 8, 16, 20):
        s.beat(b, 1, {'crash': 'X...............'})
    for b in (2, 10, 18, 24):
        s.beat(b, 1, {'chain': '........x.......'})
    for b in (3, 11, 17, 23):
        s.beat(b, 1, {'hiss': '............x...'})
    return s


# ---- NEON MILE: A minor synth-pop, 124 BPM -----------------------------------
NM_A = ('E5:4 A5:4 C6:3 B5:3 A5:2 | G5:6 A5:2 E5:8 | E5:2 G5:2 C6:4 B5:2 A5:2 G5:4 | D5:4 G5:4 B5:8 | '
        'A5:3 C6:3 E6:2 D6:4 C6:4 | C6:6 B5:2 A5:4 E5:4 | F5:4 A5:4 D6:4 C6:2 B5:2 | G#5:8 B5:4 E5:4')
NM_B = ('A5:2 C6:2 F6:4 E6:4 C6:4 | D6:6 B5:2 G5:8 | G5:2 B5:2 E6:4 D6:4 B5:4 | C6:12 A5:4 | '
        'A5:2 C6:2 F6:4 G6:4 F6:2 E6:2 | D6:8 B5:4 D6:4 | A5:8 G#5:8 | B5:4 G#5:4 E5:4 D6:4')


def m_neon_mile():
    s = Song('neon_mile', 124, 32, key=('A', MINOR), echo=(3, 0.38), room=(1.4, 0.016), air=-1.5)
    std_mix(s, lead_echo=0.3)
    ca = 'Am Fmaj7 C G Am Fmaj7 Dm E'
    s.chords(0, ca)
    s.chords(8, ca)
    s.chords(16, 'F G Em Am F G Esus4:2 E:2 E')
    s.chords(24, ca)
    s.mel('lead', 'lead50', 0, NM_A, vel=0.8)
    s.mel('lead', 'leadpwm', 8, NM_A)
    s.mel('lead2', 'leadsaw', 8, NM_A, transpose=-12, vel=0.45)
    s.mel('lead', 'leadpwm', 16, NM_B)
    s.mel('harm', 'harm', 16, NM_B, dia=-2, vel=0.7)
    s.mel('lead', 'leadpwm', 24, NM_A, vel=1.05)
    s.mel('harm', 'harm', 24, NM_A, dia=-2, vel=0.8)
    s.mel('lead2', 'leadsaw', 24, NM_A, transpose=-12, vel=0.45)
    wide_pad(s, 'pad', 0, 32, 60, vel=0.9)
    s.arp('arp', 'arp', 0, 32, '0124', rate=1, center=69, vel=0.85)
    s.arp('keys', 'pluck', 16, 8, '0.2.1.3.', rate=1, center=60, vel=0.6)
    s.bassline('bass', 'bassp', 0, 32, ['R.O.R.O.R.O.R.O.', 'R.O.R.O.R.O.R.O.', 'R.O.R.O.R.O.R.O.', 'R.O.R.O.R.O.O.A.'])
    g = {'kick': 'X...X...X...X...', 'snare_gate': '....X.......X...', 'hat': '..x...x...x...x.',
         'shaker': 'oxoooxoooxoooxoo'}
    s.beat(0, 7, {'kick': 'X...X...X...X...', 'hat': '..x...x...x...x.', 'shaker': 'oxoooxoooxoooxoo'})
    s.beat(7, 1, {'kick': 'X...X...X...X...', 'snare_gate': '........x.x.XXXX'})
    for b0 in (8, 16, 24):
        s.beat(b0, 7, g)
        s.beat(b0 + 7, 1, {'kick': 'X...X...X...X...', 'snare_gate': '....X.......X...',
                           'tom_hi': '........X.x.....', 'tom_mid': '..........X.x...', 'tom_lo': '............X.X.'})
    s.beat(16, 8, {'clap': '....X.......X...'})
    s.beat(24, 8, {'ohat': '..o...o...o...o.'})
    for b in range(1, 32, 2):
        s.beat(b, 1, {'zap': '...............x'})
    for b in (0, 8, 16, 24):
        s.beat(b, 1, {'crash': 'X...............'})
    return s


# ---- FLOODGATE: D minor storm, 132 BPM ---------------------------------------
FG_A = ('D5:2 F5:2 A5:4 G5:2 F5:2 E5:2 F5:2 | D5:8 Bb4:4 D5:4 | E5:2 G5:2 C6:4 Bb5:2 A5:2 G5:2 E5:2 | '
        'F5:8 A5:4 D5:4 | D6:4 C6:2 A5:2 F5:4 A5:4 | Bb5:4 A5:2 F5:2 D5:8 | G5:4 Bb5:4 D6:4 C6:2 Bb5:2 | '
        'A5:8 C#6:4 E6:4')
FG_B = ('Bb5:6 A5:2 G5:8 | A5:6 G5:2 F5:8 | F5:4 G5:4 Bb5:4 D6:4 | C#6:12 r:4 | D6:6 C6:2 Bb5:4 G5:4 | '
        'A5:6 F5:2 D5:4 F5:4 | G5:4 Bb5:4 Eb6:8 | E6:4 C#6:4 A5:4 E5:4')


def m_floodgate():
    s = Song('floodgate', 132, 36, key=('D', HMINOR), echo=(3, 0.3), room=(1.3, 0.016), air=-2.0)
    std_mix(s, lead_echo=0.2)
    s.bus('timp', pan=-0.15, gain=1.0, verb=0.3)
    ca = 'Dm Bb C Dm Dm Bb Gm A'
    s.chords(0, ca)
    s.chords(8, ca)
    s.chords(16, 'Gm Dm Bb A Gm Dm Eb A')
    s.chords(24, 'Dm Dm Bb A')
    s.chords(28, ca)
    s.mel('lead', 'lead', 0, FG_A)
    s.mel('lead', 'lead', 8, FG_A)
    s.mel('lead2', 'leadsaw', 8, FG_A, transpose=-12, vel=0.5)
    s.mel('lead', 'lead50', 16, FG_B)
    s.mel('lead2', 'brass', 16, FG_B, transpose=-12, vel=0.6)
    s.mel('lead', 'lead', 28, FG_A, vel=1.05)
    s.mel('harm', 'harm', 28, FG_A, dia=-2, vel=0.8)
    # tremolo strings + pads
    s.comp('comp', 'arp25', 0, 36, 'xoxoxoxoxoxoxoxo', center=62, vel=0.55, gate=0.6)
    wide_pad(s, 'strings', 0, 36, 57, vel=0.8)
    s.arp('arp', 'arp', 24, 4, '0123456789abcdef', rate=1, center=62, span=3, vel=0.8)
    # bass gallop
    gal = 'R-RRR-RRR-RRR-RR'
    s.bassline('bass', 'bassp', 0, 36, [gal, gal, gal, 'R-RRR-RRR-RRO-5A'], octave=2)
    # timpani on downbeats
    for b in range(0, 36, 2):
        ch = s.chord_at(b * 16)
        s.note('timp', 'timp', b * 16, 8, 36 + ch['root'] + (12 if ch['root'] < 2 else 0), 0.9)
    g = {'kick': 'X...X...X...X.x.', 'snare': '....X.......X...', 'hat': 'xxoxxxoxxxoxxxox'}
    for b0, nb in ((0, 8), (8, 8), (16, 8), (28, 8)):
        s.beat(b0, nb - 1, g)
        s.beat(b0 + nb - 1, 1, {'kick': 'X...X...X...X...', 'snare': FILL_SN, 'tom_hi': '........x.......',
                                'tom_lo': '..........x.x...'})
        s.beat(b0, 1, {'crash': 'X...............'})
    s.beat(24, 4, {'kick': 'X.......X.......', 'snare': 'o.o.o.o.o.o.o.o.', 'hat': 'x.x.x.x.x.x.x.x.'})
    s.beat(26, 1, {'snare': 'x.x.x.x.x.x.x.x.'})
    s.beat(27, 1, {'snare': 'xxxxxxxxXXXXXXXX', 'kick': 'X...X...X...X...'})
    s.fx('cym', 28 * 16 - len(drum('crash_rev')) / s.step, drum('crash_rev'), 0.25)
    for b in (0, 16, 28):
        s.fx('fx', b * 16, drum('thunder'), 0.35)
    return s


# ---- WAREHOUSE: C minor, dark pulse, 110 BPM ---------------------------------
WH_A = ('G5:4 Ab5:4 G5:4 D5:4 | Eb5:12 r:4 | C5:4 Eb5:4 Ab5:4 G5:4 | F5:8 Eb5:8 | '
        'C6:4 Ab5:4 F5:8 | Ab5:6 G5:2 F5:8 | G5:4 B4:4 D5:4 F5:4 | Ab5:8 G5:8')
WH_B = ('C6:6 Bb5:2 G5:8 | Ab5:6 F5:2 Db6:8 | C6:4 Eb6:4 D6:4 C6:4 | Db6:12 r:4 | '
        'Eb6:6 C6:2 Ab5:8 | F6:4 Eb6:4 C6:4 Ab5:4 | F5:4 Ab5:4 C6:8 | B5:8 D6:4 F6:4')
WH_BELL = 'G5:4 Ab5:4 G5:8 | r:16 | C5:4 Eb5:4 Ab5:8 | r:16 | C6:4 Ab5:4 F5:8 | r:16 | G5:4 B4:4 D5:8 | r:16'


def m_warehouse():
    s = Song('warehouse', 110, 32, key=('C', HMINOR), echo=(3, 0.42), room=(1.8, 0.025), air=-3.0)
    std_mix(s, lead_echo=0.32, bass_lp=1400)
    s.bus('metal', pan=0.0, gain=0.9, verb=0.4, echo=0.2)
    ca = 'Cm Cm Ab Ab Fm Fm G G'
    s.chords(0, ca)
    s.chords(8, ca)
    s.chords(16, 'Cm Db Cm Db Ab Fm Dbmaj7 G')
    s.chords(24, ca)
    eerie = dict(vib=(28, 4.6, 0.25))
    s.mel('keys', 'bell', 0, WH_BELL, vel=0.7)
    s.mel('lead', 'lead12', 8, WH_A, **eerie)
    s.mel('lead2', 'flute', 8, WH_A, transpose=-12, vel=0.5)
    s.mel('lead', 'leadsaw', 16, WH_B, vel=0.9)
    s.mel('harm', 'lead12', 16, WH_B, transpose=-12, vel=0.4, **eerie)
    s.mel('lead', 'lead12', 24, WH_A, vel=1.05, **eerie)
    s.mel('lead2', 'leadsaw', 24, WH_A, transpose=-12, vel=0.5)
    s.mel('keys', 'bell', 24, WH_BELL, transpose=12, vel=0.4)
    wide_pad(s, 'choir', 0, 16, 55, vel=0.9)
    wide_pad(s, 'strings', 16, 8, 57, vel=0.9)
    wide_pad(s, 'choir', 24, 8, 55, vel=0.9)
    s.arp('arp', 'arp', 24, 8, '0.1.2.1.', rate=1, center=60, vel=0.6)
    s.bassline('bass', 'bassp', 0, 32, ['R.r.R.r.R.r.R.r.', 'R.r.R.r.R.r.R.rA'], octave=2)
    s.bassline('bass', 'basssaw', 16, 8, ['R-------R-------'], octave=1, vel=0.5, sub=0.15)
    heart = {'kick_soft': 'X..x............', 'hat': 'o.o.o.o.o.o.o.o.'}
    full = {'kick': 'X..x......X.....', 'snare_big': '........X.......', 'hat': 'o.x.o.x.o.x.o.x.',
            'rim': '......o.......o.'}
    s.beat(0, 8, heart)
    s.beat(8, 7, {'kick_soft': 'X..x......X.....', 'snare_big': '........X.......', 'hat': 'o.o.o.o.o.o.o.o.'})
    s.beat(15, 1, {'kick_soft': 'X..x............', 'snare_big': '........x...x.xx'})
    s.beat(16, 8, full)
    s.beat(24, 7, dict(full, ohat='..............o.'))
    s.beat(31, 1, {'kick': 'X..x............', 'tom_lo': '........X..X..X.', 'tom_mid': '..........X..X..'})
    for b in range(0, 32, 4):
        s.beat(b, 1, {'pipe': 'x...............'})
    for b in range(2, 32, 4):
        s.beat(b, 1, {'clank': '..........o.....', 'chain': '....o...........'})
    for b in (8, 16, 24):
        s.beat(b, 1, {'crash': 'x...............'})
    return s


# ---- SAFE HUB: F major jazzy diner, 92 BPM, swung ----------------------------
SH_A = ('A5:4 C6:2 E6:6 D6:2 C6:2 | A5:6 F5:2 D5:8 | Bb5:2 A5:2 G5:2 F5:2 D5:4 F5:4 | E5:8 r:2 G5:2 Bb5:2 C6:2 | '
        'A5:4 C6:2 E6:4 G6:2 F6:4 | E6:4 D6:2 C6:2 A5:8 | Bb5:4 D6:2 F6:2 E6:4 D6:4 | C6:8 r:8')
SH_A2_END = 'C6:4 Bb5:2 G5:2 E5:8'
SH_B = ('D6:6 C6:2 A5:4 F5:4 | Db6:6 C6:2 G5:8 | C6:4 E6:4 G6:4 E6:4 | F#6:8 D6:4 C6:4 | '
        'Bb5:6 A5:2 G5:4 F5:4 | E5:4 G5:4 Bb5:4 D6:4 | C6:6 A5:2 F#5:4 A5:4 | Bb5:4 G5:4 E5:4 C5:4')


def m_safe_hub():
    s = Song('safe_hub', 92, 24, key=('F', MAJOR), swing8=0.64, echo=(6, 0.22), room=(1.0, 0.012),
             air=-3.0, target=-17.0)
    std_mix(s, lead_echo=0.12, bass_lp=1800)
    s.bus('keys', pan=-0.25, gain=1.0, echo=0.05, verb=0.22)
    s.bus('bass', gain=0.75, verb=0.04, lp=1800)
    ca = 'Fmaj7 Dm7 Gm7 C7 Fmaj7 Dm7 Gm7 C7'
    s.chords(0, ca)
    s.chords(8, ca)
    s.chords(16, 'Bbmaj7 Bbm6 Am7 D7 Gm7 C7 Fmaj7:2 D7:2 Gm7:2 C7:2')
    s.mel('lead', 'vibes', 0, SH_A)
    a2 = SH_A.rsplit('|', 1)[0] + '| ' + SH_A2_END
    s.mel('lead', 'vibes', 8, a2)
    s.mel('lead2', 'flute', 8, a2, transpose=-12, vel=0.35)
    s.mel('lead', 'vibes', 16, SH_B)
    s.mel('harm', 'lead50', 16, SH_B, transpose=-12, vel=0.3, gate=0.7)
    s.comp('keys', 'epiano', 0, 24, ['x-----x---......', '..x-....x-----..'], center=60, vel=0.8)
    wide_pad(s, 'padsoft', 0, 24, 55, vel=0.45)
    walk = ['R---3---5---A---', 'R---5---6---A---', 'R---O---5---W---', 'R---3---5---A---']
    s.bassline('bass', 'basswalk', 0, 16, walk, octave=2)
    s.bassline('bass', 'basswalk', 16, 6, walk, octave=2)
    s.bassline('bass', 'basswalk', 22, 2, ['R---5---R---A---'], octave=2)
    g = {'ride': 'o...X.o.o...X.o.', 'hat': '....x.......x...', 'brush': 'o...o...o...o...',
         'kick_soft': 'o.......o.......'}
    s.beat(0, 7, g)
    s.beat(7, 1, dict(g, brush_tap='..........x.x.xx'))
    s.beat(8, 16, dict(g, rim='............x...'))
    s.beat(15, 1, {'brush_tap': '..........x..xx.'})
    s.beat(23, 1, {'brush_tap': '........x.x.x.xx'})
    return s


# ---- BOSS: F minor gang-boss fight, 150 BPM ----------------------------------
BOSS_RIFF = ('F4:2 F4:1 F4:1 Ab4:2 F4:2 B4:2 C5:2 Eb5:2 C5:2 | '
             'F4:2 F4:1 F4:1 Ab4:2 F4:2 Db5:2 C5:2 Bb4:2 G4:2')
BOSS_A = ('C6:4 Ab5:2 F5:2 C6:2 Db6:2 C6:4 | Ab5:6 F5:2 Db5:8 | Eb5:2 G5:2 Bb5:4 Eb6:4 Db6:2 C6:2 | E5:4 G5:4 C6:8 | '
          'F6:4 Eb6:2 C6:2 Ab5:4 C6:4 | Db6:6 C6:2 Ab5:8 | Bb5:2 C6:2 Db6:4 F6:4 Eb6:2 Db6:2 | C6:4 Bb5:2 G5:2 E5:4 G5:4')
BOSS_B = ('F5:2 F5:2 Bb5:4 Db6:4 C6:4 | Ab5:2 Ab5:2 C6:4 F6:4 Eb6:4 | Db6:4 Bb5:4 Gb5:4 Bb5:4 | C6:4 E6:4 G6:8 | '
          'F6:6 Db6:2 Bb5:8 | C6:6 Ab5:2 F5:8 | Ab5:4 Db6:4 F6:4 Ab6:4 | G6:4 E6:4 C6:4 Bb5:4')


def m_boss():
    s = Song('boss', 150, 36, key=('F', HMINOR), echo=(3, 0.25), room=(1.0, 0.012), air=-2.0)
    std_mix(s, lead_echo=0.15, bass_lp=2600)
    s.chords(0, 'Fm Fm Fm Fm')
    s.chords(4, 'Fm Db Eb C Fm Db Bbm C7')
    s.chords(12, 'Bbm Fm Gb C Bbm Fm Db C7')
    s.chords(20, 'Fm Db Eb C Fm Db Bbm C7')
    s.chords(28, 'Fm Fm Fm Fm')
    s.chords(32, 'Db Eb C C7')
    for b in (0, 2, 28, 30):
        s.mel('lead', 'lead', b, BOSS_RIFF, vel=0.9)
        s.mel('bass', 'basssaw', b, BOSS_RIFF, transpose=-24)
        s.mel('lead2', 'stab', b, BOSS_RIFF, transpose=-12, vel=0.7)
    s.mel('lead', 'lead', 4, BOSS_A)
    s.mel('lead2', 'leadsaw', 4, BOSS_A, transpose=-12, vel=0.4)
    s.mel('lead', 'leadpwm', 12, BOSS_B)
    s.mel('harm', 'brass', 12, BOSS_B, transpose=-12, vel=0.55)
    s.mel('lead', 'lead', 20, BOSS_A, vel=1.05)
    s.mel('harm', 'harm', 20, BOSS_A, dia=-2, vel=0.75)
    s.mel('lead', 'brass', 32, 'Ab5:4 r:2 Ab5:2 Ab5:4 F5:4 | Bb5:4 r:2 Bb5:2 Bb5:4 G5:4 | '
                               'C6:4 r:2 C6:2 C6:4 E5:4 | G5:4 Bb5:4 C6:4 E6:4', vel=0.9)
    wide_pad(s, 'strings', 4, 32, 58, vel=0.75)
    s.arp('arp', 'arp', 12, 8, '0123', rate=1, center=72, vel=0.7)
    drive = ['RrOrRrOrRrOrRrOr', 'RrOrRrOrRrOrRrOA']
    s.bassline('bass', 'bassp', 4, 24, drive)
    s.bassline('bass', 'bassp', 32, 4, ['R.R.R.R.R.R.R.R.', 'R.R.R.R.R.R.RRAA'])
    rock = {'kick': 'X.x...x.X.x...x.', 'snare': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.'}
    riffbeat = {'kick': 'X..X..X.X..X..X.', 'snare': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.'}
    s.beat(0, 4, riffbeat)
    s.beat(28, 4, riffbeat)
    for b0 in (4, 12, 20):
        s.beat(b0, 7, rock)
        s.beat(b0 + 7, 1, {'kick': 'X.x...x.X.......', 'snare': FILL_SN, 'tom_hi': '........x.......',
                           'tom_mid': '..........x.....', 'tom_lo': '............x.x.'})
        s.beat(b0, 1, {'crash': 'X...............'})
    s.beat(12, 8, {'ohat': '..............o.'})
    s.beat(32, 3, {'kick': 'X...X...X...X...', 'snare': '....X.......X.x.', 'hat': 'xxxxxxxxxxxxxxxx'})
    s.beat(35, 1, {'kick': 'X...X...X...X...', 'snare': 'xxxxxxxxXXXXXXXX'})
    s.beat(0, 1, {'crash': 'X...............'})
    s.beat(28, 1, {'crash': 'X...............'})
    s.fx('cym', 36 * 16 - len(drum('crash_rev')) / s.step, drum('crash_rev'), 0.25)
    return s


# ---- ROOK: B minor final boss, 140 BPM ---------------------------------------
ROOK_A = ('B4:4 D5:4 F#5:6 E5:2 | D5:4 C#5:4 B4:8 | G5:4 F#5:2 E5:2 D5:4 B4:4 | C#5:4 E5:4 F#5:8 | '
          'G5:4 B5:4 E6:6 D6:2 | D6:4 B5:4 G5:8 | A#5:4 C#6:4 F#6:6 E6:2 | E6:4 C#6:4 A#5:4 F#5:4')
ROOK_B = ('F#5:6 A5:2 D6:8 | C#6:6 B5:2 A5:8 | B5:4 D6:4 F#6:4 E6:2 D6:2 | C#6:12 A5:4 | '
          'B5:6 D6:2 G6:8 | F#6:6 E6:2 D6:8 | E6:4 D6:4 B5:4 G5:4 | A#5:8 C#6:4 F#6:4')
ROOK_COUNTER = 'D5:16 | C#5:16 | B4:16 | A4:16 | B4:16 | A4:16 | G4:16 | A#4:16'
ROOK_RIFF = ('B3:2 B3:1 B3:1 D4:2 B3:2 F#4:2 E4:2 D4:2 C#4:2 | '
             'C4:2 C4:1 C4:1 E4:2 C4:2 G4:2 E4:2 D4:2 C#4:2')
ROOK_C_TOP = 'r:16 | r:16 | r:16 | r:16 | B5:16 | A#5:16 | G5:8 B5:8 | A#5:4 C#6:4 E6:4 F#6:4'


def m_rook():
    s = Song('rook', 140, 44, key=('B', HMINOR), echo=(3, 0.28), room=(1.7, 0.02), air=-2.0)
    std_mix(s, lead_echo=0.2, bass_lp=2400)
    s.bus('timp', pan=-0.2, gain=1.0, verb=0.35)
    s.bus('bells', pan=0.3, gain=0.8, verb=0.4, echo=0.1)
    s.bus('choirL', pan=-0.5, gain=1.0, verb=0.4)
    s.bus('choirR', pan=0.5, gain=1.0, verb=0.4)
    ca = 'Bm Bm/A G F# Em G F# F#7'
    s.chords(0, 'Bm G Em F#')
    s.chords(4, ca)
    s.chords(12, ca)
    s.chords(20, 'D A Bm F#m G D Em F#')
    s.chords(28, 'Bm C Bm C G F# Em F#7')
    s.chords(36, ca)
    # intro toll
    s.mel('bells', 'bell', 0, 'B5:16 | B5:16 | G5:16 | F#5:16')
    s.mel('bells', 'bell', 0, 'F#5:16 | D5:16 | B4:16 | A#4:16', vel=0.7)
    # themes
    s.mel('lead', 'lead', 4, ROOK_A)
    s.mel('lead2', 'leadsaw', 4, ROOK_A, transpose=-12, vel=0.4)
    s.mel('lead', 'leadpwm', 12, ROOK_A)
    s.mel('harm', 'brass', 12, ROOK_A, transpose=-12, vel=0.5)
    s.mel('lead', 'lead', 20, ROOK_B)
    s.mel('harm', 'brass', 20, ROOK_COUNTER, vel=0.7)
    s.mel('lead2', 'leadsaw', 20, ROOK_B, transpose=-12, vel=0.4)
    for b in (28, 30, 32, 34):
        s.mel('bass', 'basssaw', b, ROOK_RIFF, transpose=-12)
        s.mel('lead2', 'stab', b, ROOK_RIFF, vel=0.8)
    s.mel('lead', 'leadsaw', 28, ROOK_C_TOP)
    s.mel('lead', 'lead', 36, ROOK_A, vel=1.05)
    s.mel('harm', 'harm', 36, ROOK_A, dia=-2, vel=0.8)
    s.mel('lead2', 'brass', 36, ROOK_A, transpose=-12, vel=0.5)
    s.mel('bells', 'bell', 36, 'B5:16 | A5:16 | G5:16 | F#5:16 | E5:16 | G5:16 | F#5:16 | A#5:16', vel=0.5)
    # beds
    s.pad('choirL', 'choir', 0, 44, 57)
    s.pad('choirR', 'choir', 0, 44, 57, detune=8)
    wide_pad(s, 'strings', 12, 16, 62, vel=0.75)
    wide_pad(s, 'strings', 36, 8, 62, vel=0.8)
    s.pad('keys', 'organ', 28, 8, 60, vel=0.6)
    s.arp('arp', 'arp', 12, 8, '0124', rate=1, center=70, vel=0.7)
    s.arp('arp', 'arp', 36, 8, '0124', rate=1, center=70, vel=0.8)
    for b in range(0, 44, 2):
        ch = s.chord_at(b * 16)
        s.note('timp', 'timp', b * 16, 8, 36 + ch['root'] + (0 if ch['root'] >= 4 else 12), 0.85)
    # bass
    drive = ['R.RoR.RoR.RoR.Ro', 'R.RoR.RoR.RoO.5A']
    s.bassline('bass', 'bassp', 4, 24, drive)
    s.bassline('bass', 'bassp', 36, 8, drive)
    s.bassline('bass', 'bass', 0, 4, ['R---------------'], octave=1)
    # drums
    g = {'kick': 'X..x..X.X..x..X.', 'snare': '....X.......X...', 'hat': 'xxoxxxoxxxoxxxox'}
    s.beat(0, 3, {'tom_lo': 'x...............'})
    s.beat(3, 1, {'tom_lo': 'x.x.x.x.xxxxXXXX', 'tom_mid': '........x.x.x.x.'})
    for b0, nb in ((4, 8), (12, 8), (20, 8), (36, 8)):
        s.beat(b0, nb - 1, g)
        s.beat(b0 + nb - 1, 1, {'kick': 'X..x..X.X.......', 'snare': FILL_SN, 'tom_hi': '........X.......',
                                'tom_mid': '..........X.....', 'tom_lo': '............X.X.'})
        s.beat(b0, 1, {'crash': 'X...............'})
    s.beat(36, 8, {'ohat': '..o...o...o...o.'})
    s.beat(28, 7, {'kick': 'X.X.X.X.X.X.X.X.', 'snare': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.'})
    s.beat(35, 1, {'kick': 'X.X.X.X.X.......', 'snare': 'xxxxxxxxXXXXXXXX'})
    s.beat(28, 1, {'crash': 'X...............'})
    s.fx('cym', 4 * 16 - len(drum('crash_rev')) / s.step, drum('crash_rev'), 0.22)
    return s


# ---- SETBACK: G minor, somber, 76 BPM ----------------------------------------
SB_M = ('D5:8 Bb4:4 G4:4 | G4:6 Bb4:2 Eb5:8 | D5:4 C5:4 Eb5:4 G4:4 | F#4:12 r:4 | '
        'D5:8 G5:4 F5:2 D5:2 | Eb5:8 Bb4:8 | C5:6 Eb5:2 G5:8 | F#5:8 r:8 | '
        'G5:6 F5:2 Eb5:8 | Eb5:6 D5:2 C5:8 | Bb4:8 D5:8 | C5:4 A4:4 F#4:8')


def m_setback():
    s = Song('setback', 76, 12, key=('G', HMINOR), echo=(6, 0.3), room=(1.9, 0.02), air=-2.0, target=-18.0)
    std_mix(s, lead_echo=0.25, bass_lp=900)
    s.chords(0, 'Gm Eb Cm D Gm Eb Am7b5 D Eb Cm Gm/D D7')
    s.mel('lead', 'flute', 0, SB_M)
    s.mel('harm', 'flute', 8, SB_M.split('|', 8)[-1], dia=-2, vel=0.5)
    s.arp('keys', 'epiano', 0, 12, '0121', rate=2, center=60, vel=0.75, gate=1.0)
    s.mel('arp', 'bell', 4, 'D6:8 r:8 | G5:8 r:8 | Eb6:8 r:8 | D6:16 | G6:8 r:8 | Eb6:8 r:8 | D6:8 r:8 | A5:16', vel=0.35)
    wide_pad(s, 'strings', 0, 12, 52, vel=0.6)
    s.bassline('bass', 'basswalk', 0, 12, ['R-------R-------', 'R-------5-------'], octave=2, vel=0.8, gate=0.98)
    s.beat(0, 12, {'heart': 'X.......X.......', 'tick': 'X.x.X.x.X.x.X.x.'}, vel=0.8)
    s.beat(3, 1, {'tom_lo': '............o...'})
    s.beat(7, 1, {'tom_lo': '........o...o...'})
    s.beat(11, 1, {'tom_lo': '........o.o.x.x.'})
    return s


# ---- ENDING: D major credits, 96 BPM (reprises the title theme) --------------
END_B = ('D5:4 G5:4 B5:6 A5:2 | A5:4 E5:4 C#5:8 | C#5:4 F#5:4 A5:6 B5:2 | F#5:12 D5:4 | '
         'G5:4 B5:4 E6:6 D6:2 | C#6:4 B5:4 A5:8 | F#5:4 A5:4 D6:8 | C6:8 A5:4 F#5:4')
END_C = ('B5:6 A5:2 G5:4 D5:4 | Bb5:6 A5:2 G5:4 E5:4 | F#5:4 A5:4 D6:4 C#6:2 B5:2 | A5:12 F#5:4 | '
         'G5:4 B5:4 D6:4 E6:4 | C#6:6 B5:2 A5:4 G5:4 | F#5:8 E5:4 D5:4 | E5:4 G5:4 A5:4 C#6:4')


def m_ending():
    s = Song('ending', 96, 32, key=('D', MAJOR), echo=(3, 0.28), room=(1.5, 0.018), air=-2.5)
    std_mix(s, lead_echo=0.2)
    s.chords(0, TITLE_CH_A)
    s.chords(8, 'G A F#m Bm Em A D D7')
    s.chords(16, 'G Gm6 D/F# Bm7 Em7 A7 D A7')
    s.chords(24, TITLE_CH_B)
    # S1: triumphant title reprise
    s.mel('lead', 'brass', 0, TITLE_A, vel=1.0)
    s.mel('lead2', 'lead', 0, TITLE_A, transpose=12, vel=0.35)
    s.mel('harm', 'harm', 0, TITLE_A, dia=-2, vel=0.7)
    # S2: credits melody
    s.mel('lead', 'lead50', 8, END_B)
    s.mel('lead2', 'flute', 8, END_B, transpose=-12, vel=0.4)
    # S3: warm
    s.mel('lead', 'vibes', 16, END_C)
    s.mel('lead2', 'flute', 16, END_C, vel=0.45)
    # S4: title bridge, building back to the reprise
    s.mel('lead', 'lead', 24, TITLE_B)
    s.mel('harm', 'brass', 24, TITLE_B, transpose=-12, vel=0.55)
    s.mel('keys', 'bell', 24, 'D6:16 | B5:16 | A5:16 | C#6:16 | B5:16 | D6:16 | E6:16 | E6:8 C#6:8', vel=0.5)
    wide_pad(s, 'strings', 0, 32, 60, vel=0.8)
    s.comp('comp', 'brass', 0, 8, 'X-----x-..x-x-..', center=62, vel=0.55)
    s.comp('keys', 'epiano', 8, 16, ['x-----x---......', '..x-....x-----..'], center=62, vel=0.7)
    s.arp('arp', 'arp', 24, 8, '02130213', rate=2, center=74, vel=0.7)
    s.bassline('bass', 'bass', 0, 8, ['R.R.R.R.R.R.O.R.'] * 3 + ['R.R.R.R.R.O.R.A.'])
    s.bassline('bass', 'bass', 8, 8, ['R--R--O-R--5--O-', 'R--R--O-R--5-.A-'])
    s.bassline('bass', 'basswalk', 16, 8, ['R---5---3---A---'])
    s.bassline('bass', 'bass', 24, 8, ['R.R.R.R.R.R.O.R.'] * 3 + ['R.R.R.R.R.O.R.A.'])
    full = {'kick': 'X.......X.x.....', 'snare': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.'}
    soft = {'kick_soft': 'X.....x...x.....', 'rim': '....x.......x...', 'hat': 'x.xox.xox.xox.xo'}
    warm = {'ride': 'o...x.o.o...x.o.', 'brush': 'o...o...o...o...', 'kick_soft': 'o.......o.......'}
    for b0, pat in ((0, full), (8, soft), (16, warm), (24, full)):
        s.beat(b0, 7, pat)
        s.beat(b0, 1, {'crash': 'X...............' if pat is full else 'o...............'})
    s.beat(7, 1, {'kick': 'X.......X.......', 'snare': FILL_SN, 'tom_lo': '..........x.x...'})
    s.beat(15, 1, {'kick_soft': 'X.....x.........', 'rim': '....x...x.x.x.x.'})
    s.beat(23, 1, {'brush_tap': '........x.x.x.xx', 'kick_soft': 'o...............'})
    s.beat(31, 1, {'kick': 'X.......X.......', 'snare': FILL_SN, 'tom_hi': '........x.......', 'tom_lo': '..........x.x...'})
    s.beat(24, 8, {'ohat': '..o...o...o...o.'})
    return s


# ---- STINGERS ----------------------------------------------------------------
def m_victory():
    s = Song('victory', 150, 2, loop=False, tail=0.75, key=('C', MAJOR), echo=(3, 0.2), room=(1.2, 0.012))
    std_mix(s, lead_echo=0.12)
    s.chords(0, 'C:2 F:1 G:1 C')
    s.mel('lead', 'lead', 0, 'G4:2 C5:2 E5:2 G5:4 E5:2 G5:4 | C6:12 r:4', gate=0.9)
    s.mel('lead2', 'brass', 0, 'G4:2 C5:2 E5:2 G5:4 E5:2 G5:4 | C6:12 r:4', transpose=-12, vel=0.7)
    s.mel('harm', 'harm', 0, 'E4:2 G4:2 C5:2 E5:4 C5:2 D5:4 | E5:12 r:4', vel=0.8)
    s.comp('comp', 'brass', 0, 2, ['X-------x---x---', 'X-----------....'], center=60, vel=0.8)
    s.mel('keys', 'bell', 1, 'C6:2 E6:2 G6:2 C7:10', vel=0.5)
    s.bassline('bass', 'bass', 0, 2, ['R-R-R-R-R---R---', 'R-----------....'])
    s.beat(0, 1, {'snare': 'X.x.X.x.XxXxXXXX', 'kick': 'X.......X...X...'})
    s.beat(1, 1, {'crash': 'X...............', 'kick': 'X...............', 'tom_lo': 'X...............'})
    return s


def m_defeat():
    s = Song('defeat', 120, 2, loop=False, tail=0.0, key=('A', MINOR), echo=(3, 0.25), room=(1.6, 0.015),
             target=-18.0)
    std_mix(s, lead_echo=0.2)
    s.chords(0, 'Am:1 F:1 Dm:1 E:1 Am')
    s.mel('lead', 'lead50', 0, 'E5:4 D5:4 C5:4 B4:4 | A4:11 r:5', vel=0.9, gate=0.95, vib=(22, 4.5, 0.25))
    s.mel('lead2', 'flute', 0, 'C5:4 A4:4 A4:4 G#4:4 | E4:11 r:5', vel=0.6, gate=0.95)
    s.pad('padL', 'padsoft', 0, 2, 57, vel=0.9, gate=0.8)
    s.pad('padR', 'padsoft', 0, 2, 57, vel=0.9, gate=0.8, detune=9)
    s.bassline('bass', 'basswalk', 0, 2, ['R---R---R---R---', 'R----------.....'], octave=2)
    s.beat(0, 1, {'tom_lo': 'x...x...x...x...'}, vel=0.6)
    s.beat(1, 1, {'kick_soft': 'X...............', 'crash': 'o...............'}, vel=0.6)
    return s


MUSIC = [
    ('title', m_title, 'Anthemic, hopeful title theme; pulse lead over driving octave bass, harmony lift in the reprise'),
    ('old_quarter', m_old_quarter, 'Home-district street funk; swung 16ths, clav stabs, organ answers, slap-style bass'),
    ('canal_market', m_canal_market, 'Sunny calypso/ska bounce; steel-pan lead, offbeat skank, clave and timbales'),
    ('ironworks', m_ironworks, 'Heavy industrial half-time groove; anvil, pipe and chain percussion, saw lead'),
    ('neon_mile', m_neon_mile, 'Night-time synth-pop; 16th arpeggios, gated snare, PWM lead with echo'),
    ('floodgate', m_floodgate, 'Tense storm chase; galloping bass, tremolo pulses, timpani and thunder'),
    ('warehouse', m_warehouse, 'Dark pulsing infiltration; heartbeat kick, eerie vibrato lead, metallic hits'),
    ('safe_hub', m_safe_hub, 'Relaxed swung diner/shop jazz; vibes lead, e-piano comping, walking bass, brushes'),
    ('boss', m_boss, 'Intense gang-boss fight; chromatic unison riff, 16th bass, brass alarm stabs'),
    ('rook', m_rook, 'Dramatic final boss; bell toll intro, choir, timpani, Neapolitan riff break, layered climax'),
    ('setback', m_setback, 'Somber, tense workshop-attacked cue; heartbeat, ticking clock, flute over e-piano'),
    ('ending', m_ending, 'Credits: triumphant title reprise, new warm credits melody, jazzy interlude, title bridge'),
    ('victory', m_victory, 'Short brass/pulse fanfare after a boss win'),
    ('defeat', m_defeat, 'Short sad descending jingle'),
]


# ===========================================================================
# SOUND EFFECTS
# ===========================================================================
def S(d):
    return int(round(d * SR))


def buf(d):
    return np.zeros(S(d))


def place(b, t, sig, gain=1.0):
    mix_into(b, S(t), sig, gain)
    return b


def place_wrap(b, pos, sig, gain=1.0):
    """Circular placement for seamless loops."""
    n = len(b)
    pos %= n
    k = 0
    while k < len(sig):
        seg = sig[k:k + (n - pos)]
        b[pos:pos + len(seg)] += seg * gain
        k += len(seg)
        pos = 0


def drop_curve(n, f0, f1, tau):
    return f1 + (f0 - f1) * np.exp(-secs(n) / tau)


def sweep_curve(n, f0, f1):
    return f0 * (f1 / f0) ** (np.arange(n) / max(n - 1, 1))


def thump(d, f0, f1, tau_p, tau_a, wave='sine'):
    n = S(d)
    f = drop_curve(n, f0, f1, tau_p)
    y = osc_sine(f) if wave == 'sine' else osc_tri(f, 16) if wave == 'tri' else osc_pulse(f, 0.5)
    return y * env_exp(n, tau_a, 0.0005)


def crack(d, lo, hi, tau, key, attack=0.0005):
    n = S(d)
    return filt(_noise(n, key), r_bp(lo, hi, 2)) * env_exp(n, tau, attack)


def grit(x, drive=2.0):
    return np.tanh(x * drive) / math.tanh(drive)


def crush(x, rate):
    idx = (np.floor(np.arange(len(x)) * rate / SR) * SR / rate).astype(int)
    return x[np.minimum(idx, len(x) - 1)]


def bell_tone(f, d, parts=((1, 1, 0.5), (2.0, 0.35, 0.25), (3.0, 0.2, 0.12), (4.2, 0.1, 0.06)), attack=0.001):
    n = S(d)
    t = secs(n)
    y = np.zeros(n)
    for r, a, tau in parts:
        if f * r < SR / 2.2:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / tau)
    na = max(1, S(attack))
    y[:na] *= np.linspace(0, 1, na)
    return y


def blip(f0, f1, d, duty=0.25, tau=None, wave='pulse'):
    n = S(d)
    f = sweep_curve(n, f0, f1) if f1 != f0 else np.full(n, float(f0))
    y = osc_pulse(f, duty) if wave == 'pulse' else osc_tri(f) if wave == 'tri' else osc_sine(f)
    e = env_exp(n, tau, 0.001) if tau else np.ones(n)
    return fade(y * e, 0.001, min(0.01, d / 3))


def whoosh(d, f_path, q_oct=1.2, key='wh', amp_shape=None):
    """Band-pass noise sweep; f_path(t_frac)->centre Hz."""
    n = S(d)
    nz = _noise(n, key)

    def resp(t, f):
        fc = f_path(min(t / d, 1.0))
        lo, hi = fc * 2 ** (-q_oct / 2), fc * 2 ** (q_oct / 2)
        return r_bp(lo, hi, 2)(f)
    y = tv_filter(nz, resp)
    tt = np.linspace(0, 1, n)
    e = amp_shape(tt) if amp_shape else np.sin(np.pi * tt) ** 1.5
    return y * e


def shards(d, count, key, lo=2200, hi=7500, spread=0.25):
    b = buf(d)
    rng = rng_for(key)
    for k in range(count):
        t0 = abs(rng.normal(0, spread / 2.5))
        f = rng.uniform(lo, hi)
        dur = rng.uniform(0.05, 0.25)
        s_ = bell_tone(f, dur, ((1, 1, dur / 4), (2.71, 0.4, dur / 8)))
        place(b, min(t0, d - 0.05), s_, rng.uniform(0.2, 0.8))
    return b


def wood_knock(d, f, key):
    n = S(d)
    t = secs(n)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.035) + 0.5 * np.sin(2 * np.pi * f * 2.37 * t) * np.exp(-t / 0.02)
    y += 0.6 * filt(_noise(n, key), r_bp(f * 0.8, f * 4)) * np.exp(-t / 0.012)
    return y


def impact(d, f0, f1, tau_p, tau_a, crack_lo, crack_hi, crack_tau, key, drive=2.0, crack_gain=0.6, sub=0.0):
    b = thump(d, f0, f1, tau_p, tau_a)
    b += crack_gain * fit(crack(min(d, crack_tau * 8), crack_lo, crack_hi, crack_tau, key), len(b))
    if sub:
        b += sub * thump(d, f1 * 1.4, f1 * 0.9, 0.05, tau_a * 1.8)
    slap = filt(_noise(S(0.004), key + 's'), r_hp(2500)) * np.linspace(1, 0, S(0.004))
    b[:len(slap)] += slap * 0.5
    return grit(b, drive)


# ---- combat -----------------------------------------------------------------
def sfx_punch_light():
    return impact(0.25, 190, 72, 0.018, 0.05, 1500, 6500, 0.014, 'pl', 1.6, 0.55)


def sfx_punch_heavy():
    b = impact(0.45, 140, 44, 0.035, 0.11, 800, 5200, 0.03, 'ph', 2.4, 0.7, sub=0.6)
    b += 0.35 * fit(crush(crack(0.2, 300, 2500, 0.05, 'phc'), 9000), len(b))
    return b


def sfx_kick_light():
    b = impact(0.28, 160, 62, 0.022, 0.06, 1000, 4500, 0.02, 'kl', 1.7, 0.5)
    return b + 0.25 * fit(whoosh(0.08, lambda u: 1800 - 800 * u, key='klw'), len(b))


def sfx_kick_heavy():
    b = impact(0.5, 120, 40, 0.045, 0.14, 700, 4200, 0.035, 'kh', 2.4, 0.65, sub=0.7)
    b += 0.3 * fit(crush(crack(0.25, 250, 2000, 0.06, 'khc'), 8000), len(b))
    return b


def sfx_whiff():
    return whoosh(0.22, lambda u: 600 + 2200 * math.sin(math.pi * min(u * 1.1, 1.0)) ** 2, 1.0, 'whiff',
                  lambda tt: np.sin(np.pi * tt ** 0.7) ** 2)


def sfx_block():
    b = buf(0.16)
    place(b, 0, crack(0.06, 900, 3500, 0.008, 'blk'), 0.8)
    place(b, 0, bell_tone(1240, 0.12, ((1, 1, 0.025), (2.37, 0.6, 0.015))), 0.45)
    place(b, 0, thump(0.1, 160, 90, 0.01, 0.025), 0.7)
    return grit(b, 1.4)


def sfx_perfect_guard():
    b = buf(0.9)
    place(b, 0, crack(0.03, 3000, 10000, 0.004, 'pg'), 0.6)
    for f, g in ((1760, 1.0), (2637, 0.6), (3520, 0.35), (5274, 0.15)):
        place(b, 0.004, bell_tone(f, 0.85, ((1, 1, 0.3), (2.0, 0.2, 0.1))), g)
    sp = blip(2000, 6000, 0.25, wave='sine', tau=0.08)
    place(b, 0.01, sp, 0.15)
    return b


def sfx_hurt_player():
    n = S(0.34)
    t = secs(n)
    f = sweep_curve(n, 640, 170) * (1 + 0.06 * np.sin(2 * np.pi * 28 * t))
    y = osc_pulse(f, 0.25) * env_exp(n, 0.12, 0.002)
    y = 0.7 * crush(y, 11000) + 0.35 * crack(0.34, 400, 3000, 0.04, 'hp')
    return grit(y, 1.8)


def sfx_hurt_enemy():
    n = S(0.28)
    t = secs(n)
    f = sweep_curve(n, 430, 110) * (1 + 0.08 * np.sin(2 * np.pi * 35 * t))
    y = osc_pulse(f, 0.5) * env_exp(n, 0.09, 0.002)
    y = 0.7 * crush(y, 8000) + 0.4 * crack(0.28, 300, 2500, 0.035, 'he')
    return grit(y, 2.4)


def sfx_fall():
    b = buf(0.6)
    place(b, 0, thump(0.4, 95, 38, 0.04, 0.12), 1.0)
    place(b, 0, filt(_noise(S(0.5), 'fall'), r_lp(700)) * env_exp(S(0.5), 0.12), 0.6)
    place(b, 0.19, thump(0.25, 80, 40, 0.03, 0.06), 0.45)
    place(b, 0.19, crack(0.1, 300, 1500, 0.02, 'fall2'), 0.2)
    return grit(b, 1.6)


def sfx_land():
    b = thump(0.2, 130, 58, 0.02, 0.045)
    b += 0.45 * crack(0.2, 300, 2200, 0.035, 'land')
    return grit(b, 1.4)


def _step(key, f):
    b = thump(0.09, f * 1.4, f, 0.01, 0.02) * 0.6
    b += crack(0.09, 250, 1900, 0.018, key, 0.002) * 0.8
    return b


def sfx_footstep_a():
    return _step('fsa', 105)


def sfx_footstep_b():
    return _step('fsb', 92)


def sfx_jump():
    n = S(0.24)
    y = osc_pulse(drop_curve(n, 720, 260, 0.06)[::-1], 0.25) * env_exp(n, 0.1, 0.002)
    return 0.6 * y + 0.35 * whoosh(0.24, lambda u: 700 + 1500 * u, key='jmp')


def sfx_grab():
    b = whoosh(0.16, lambda u: 2200 - 1400 * u, 1.4, 'grab', lambda tt: np.exp(-tt * 5) * np.minimum(tt * 30, 1))
    b = fit(b, S(0.25))
    place(b, 0.02, thump(0.12, 150, 80, 0.015, 0.03), 0.6)
    return b


def sfx_slam():
    b = buf(0.65)
    place(b, 0, thump(0.6, 100, 34, 0.05, 0.18), 1.0)
    place(b, 0, crack(0.3, 400, 4000, 0.04, 'slam'), 0.6)
    place(b, 0, filt(_noise(S(0.6), 'slr'), r_lp(400)) * env_exp(S(0.6), 0.2), 0.8)
    return grit(b, 2.6)


def sfx_shockwave():
    n = S(1.0)
    b = thump(1.0, 90, 30, 0.12, 0.35)
    b += 0.7 * whoosh(1.0, lambda u: 3000 * (1 - u) ** 2 + 200, 1.6, 'shock', lambda tt: np.exp(-tt * 3.5) * np.minimum(tt * 40, 1))
    b += 0.5 * filt(_noise(n, 'shr'), r_lp(250)) * env_exp(n, 0.3)
    return grit(b, 1.8)


def sfx_ko():
    b = buf(1.25)
    place(b, 0, sfx_punch_heavy(), 1.0)
    place(b, 0, thump(1.0, 70, 30, 0.1, 0.35), 0.7)
    place(b, 0.06, bell_tone(1318, 1.1, ((1, 1, 0.45), (2.76, 0.3, 0.2))), 0.35)
    ech = fit(sfx_punch_heavy(), S(0.5)) * 0.25
    place(b, 0.28, filt(ech, r_lp(1500)), 1.0)
    place(b, 0.56, filt(ech, r_lp(900)), 0.5)
    return b


def sfx_dizzy():
    n = S(1.2)
    t = secs(n)
    y = np.zeros(n)
    for k, (base, ph) in enumerate(((1700, 0.0), (2150, 2.1), (2600, 4.2))):
        f = base + 380 * np.sin(2 * np.pi * 6.5 * t + ph)
        am = 0.5 + 0.5 * np.sin(2 * np.pi * 3.2 * t + ph)
        y += osc_tri(f) * am ** 2
    e = np.minimum(t / 0.05, 1) * np.clip((1.2 - t) / 0.4, 0, 1)
    return y * e * 0.4


def sfx_guard_break():
    b = buf(0.75)
    place(b, 0, impact(0.4, 150, 50, 0.03, 0.1, 1200, 7000, 0.03, 'gb', 2.2, 0.7), 1.0)
    place(b, 0.01, shards(0.6, 14, 'gbs', 1800, 6500, 0.2), 0.6)
    n = S(0.5)
    place(b, 0.05, osc_pulse(sweep_curve(n, 900, 140), 0.25) * env_exp(n, 0.2), 0.3)
    return b


def sfx_charge():
    n = S(1.0)
    t = secs(n)
    f = sweep_curve(n, 140, 880)
    rate = 6 + 26 * t
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(rate) / SR)
    y = (0.5 * osc_saw(f) + 0.5 * osc_pulse(f * 1.005, 0.3)) * trem
    y = filt(y, r_lp(4000, 1))
    y += 0.4 * whoosh(1.0, lambda u: 500 + 5000 * u ** 2, 1.0, 'chg', lambda tt: tt ** 2)
    return y * np.minimum(t / 0.05, 1) * np.clip((1.0 - t) / 0.04, 0, 1) * (0.4 + 0.6 * t)


# ---- weapons / objects ------------------------------------------------------
def sfx_weapon_hit_blunt():
    b = impact(0.4, 170, 70, 0.02, 0.07, 900, 4000, 0.02, 'wb', 1.8, 0.45)
    b += 0.7 * fit(wood_knock(0.25, 620, 'wbk'), len(b))
    return grit(b, 1.3)


def sfx_weapon_hit_metal():
    b = impact(0.6, 160, 60, 0.02, 0.06, 1500, 8000, 0.015, 'wm', 1.5, 0.6)
    b += 0.6 * fit(_metal(S(0.6), 520, (1, 2.32, 4.25, 6.63, 8.9), (1, 0.7, 0.5, 0.35, 0.2), (0.35, 0.25, 0.15, 0.1, 0.06), 'wm'), len(b))
    return grit(b, 1.4)


def sfx_weapon_hit_chain():
    b = impact(0.5, 160, 65, 0.02, 0.06, 1200, 6000, 0.02, 'wc', 1.6, 0.5)
    b += 0.9 * fit(drum('chain'), len(b))
    place(b, 0.09, drum('chain')[:S(0.2)], 0.5)
    return b


def sfx_weapon_swing():
    b = whoosh(0.3, lambda u: 350 + 1100 * math.sin(math.pi * u), 1.3, 'wsw', lambda tt: np.sin(np.pi * tt ** 0.8) ** 2)
    n = len(b)
    b += 0.25 * osc_sine(sweep_curve(n, 120, 70)) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return b


def sfx_throw():
    b = whoosh(0.25, lambda u: 500 + 2400 * u, 1.1, 'thr', lambda tt: np.sin(np.pi * tt) ** 2 * (1 - tt * 0.5))
    place(b, 0.0, crack(0.02, 1500, 5000, 0.004, 'thrc'), 0.4)
    return b


def sfx_bottle_break():
    b = buf(0.75)
    place(b, 0, thump(0.08, 400, 200, 0.01, 0.015), 0.5)
    place(b, 0, crack(0.4, 2000, 12000, 0.06, 'bb'), 0.7)
    place(b, 0.005, shards(0.7, 28, 'bbs', 2500, 8000, 0.3), 0.8)
    return b


def sfx_crate_break():
    b = buf(0.75)
    place(b, 0, thump(0.3, 120, 50, 0.03, 0.08), 0.9)
    rng = rng_for('crate')
    for k in range(9):
        t0 = abs(rng.normal(0, 0.08))
        place(b, t0, wood_knock(0.15, rng.uniform(380, 900), 'ck%d' % k), rng.uniform(0.3, 0.8))
    place(b, 0, crack(0.5, 800, 6000, 0.09, 'cks'), 0.45)
    return grit(b, 1.6)


def sfx_crate_fall():
    b = buf(0.85)
    place(b, 0, whoosh(0.25, lambda u: 400 + 800 * u, 1.2, 'cfw', lambda tt: tt ** 2), 0.3)
    place(b, 0.24, thump(0.35, 110, 48, 0.03, 0.09), 1.0)
    place(b, 0.24, wood_knock(0.2, 480, 'cf1'), 0.8)
    place(b, 0.24, crack(0.25, 600, 4000, 0.04, 'cf2'), 0.4)
    place(b, 0.46, wood_knock(0.15, 540, 'cf3'), 0.35)
    place(b, 0.46, thump(0.2, 100, 60, 0.02, 0.04), 0.4)
    return grit(b, 1.5)


def sfx_metal_clang():
    n = S(0.85)
    b = _metal(n, 300, (1, 2.32, 4.25, 6.63, 9.1, 11.8), (1, 0.8, 0.6, 0.4, 0.25, 0.12),
               (0.6, 0.45, 0.3, 0.2, 0.12, 0.08), 'mclang')
    b += 0.6 * crack(0.85, 1500, 8000, 0.01, 'mcl')
    b += 0.5 * thump(0.85, 140, 70, 0.02, 0.05)
    return grit(b, 1.5)


def sfx_tire_bounce():
    n = S(0.42)
    t = secs(n)
    f = 95 + 110 * np.exp(-t / 0.05) * np.cos(2 * np.pi * 9 * t) ** 2 + 40 * np.exp(-t / 0.2)
    b = osc_sine(f) * env_exp(n, 0.12, 0.002)
    b += 0.3 * osc_tri(f * 2) * env_exp(n, 0.06)
    b += 0.3 * crack(0.42, 200, 1200, 0.02, 'tire')
    return grit(b, 1.5)


def sfx_drop():
    b = buf(0.32)
    place(b, 0, thump(0.15, 220, 90, 0.015, 0.035), 0.8)
    place(b, 0, crack(0.08, 800, 4000, 0.012, 'drp'), 0.5)
    place(b, 0.11, thump(0.1, 200, 110, 0.01, 0.025), 0.35)
    place(b, 0.11, crack(0.05, 900, 4000, 0.008, 'drp2'), 0.25)
    return b


def sfx_door():
    b = buf(0.85)
    place(b, 0, crack(0.04, 2000, 7000, 0.006, 'dk'), 0.5)
    place(b, 0.012, bell_tone(1900, 0.05, ((1, 1, 0.01),)), 0.3)
    n = S(0.42)
    t = secs(n)
    rng = rng_for('creak')
    jit = np.repeat(rng.uniform(-1, 1, n // 400 + 2), 400)[:n]
    f = 190 + 70 * np.sin(np.pi * t / 0.42) + 25 * filt(jit, r_lp(30))
    cr = filt(osc_saw(f), r_bp(700, 3000, 2)) * np.sin(np.pi * np.linspace(0, 1, n)) ** 1.2
    place(b, 0.06, cr, 0.45)
    place(b, 0.52, thump(0.3, 110, 60, 0.02, 0.06), 0.9)
    place(b, 0.52, wood_knock(0.15, 300, 'dthd'), 0.6)
    return b


def sfx_bus_horn():
    n = S(0.9)
    t = secs(n)
    f = 1 - 0.015 * t
    y = osc_saw(311.1 * f) + osc_saw(370.0 * f) + 0.5 * osc_saw(466.2 * f)
    y = filt(y, r_bp(250, 2500, 2), r_peak(900, 6, 1.0))
    e = np.minimum(t / 0.03, 1) * np.clip((0.8 - t) / 0.12, 0, 1)
    return np.tanh(1.5 * y * e) * (1 + 0.04 * np.sin(2 * np.pi * 7 * t))


def sfx_alarm():
    n = S(2.4)
    t = secs(n)
    hi = (np.floor(t / 0.3) % 2) == 0
    f = np.where(hi, 950.0, 720.0)
    f = filt(f, r_lp(60, 1))
    y = osc_pulse(f, 0.5) * 0.7 + osc_tri(f * 2) * 0.3
    y = filt(y, r_bp(500, 4000, 1))
    e = np.minimum(t / 0.02, 1) * np.clip((2.4 - t) / 0.1, 0, 1)
    return y * e


def sfx_whistle():
    n = S(0.8)
    t = secs(n)
    trill = 1 + 0.035 * np.sign(np.sin(2 * np.pi * 26 * t)) * (t > 0.08)
    f = filt(2800 * trill, r_lp(300, 1))
    y = osc_sine(f) + 0.2 * osc_sine(2 * f)
    y += 0.35 * filt(_noise(n, 'whis'), r_bp(2000, 6000))
    e = np.minimum(t / 0.02, 1) * np.clip((0.75 - t) / 0.06, 0, 1)
    return y * e


def sfx_dog_bark():
    b = buf(0.55)
    for t0, f0, g, d in ((0.0, 330, 1.0, 0.18), (0.24, 300, 0.7, 0.14)):
        n = S(d)
        t = secs(n)
        f = f0 * (1 + 0.25 * np.exp(-t / 0.02)) * (1 - 0.3 * t / d)
        src = osc_pulse(f, 0.3) + 0.4 * _noise(n, 'dog%d' % int(f0))
        y = filt(src, r_peak(700, 12, 0.8), r_peak(1600, 9, 0.7), r_bp(250, 4000, 1))
        y *= np.minimum(t / 0.006, 1) * np.exp(-t / (d * 0.45))
        place(b, t0, grit(y, 2.0), g)
    return b


def sfx_splash():
    b = buf(0.85)
    place(b, 0, thump(0.15, 260, 100, 0.02, 0.04), 0.6)
    nz = _noise(S(0.8), 'spl')
    y = tv_filter(nz, lambda t, f: r_lp(6000 * math.exp(-t / 0.25) + 600, 2)(f) * r_hp(250)(f))
    place(b, 0.005, y * env_exp(S(0.8), 0.2, 0.004), 0.8)
    rng = rng_for('bub')
    for k in range(10):
        n = S(rng.uniform(0.03, 0.07))
        f0 = rng.uniform(500, 1400)
        place(b, rng.uniform(0.08, 0.6), osc_sine(sweep_curve(n, f0, f0 * 1.8)) * env_exp(n, 0.02), rng.uniform(0.1, 0.3))
    return b


def sfx_crowd_cheer():
    d = 2.8
    n = S(d)
    t = secs(n)
    y = np.zeros(n)
    for k, (f1, f2) in enumerate(((650, 1150), (720, 1250), (550, 1000), (800, 1350))):
        nz = _noise(n, 'crowd%d' % k)
        am = 0.6 + 0.4 * filt(_noise(n, 'cam%d' % k), r_lp(5, 1)) * 3
        y += filt(nz, r_peak(f1, 14, 0.5), r_peak(f2, 10, 0.5), r_peak(2600, 6, 0.6), r_bp(250, 5000, 1)) * am
    rng = rng_for('claps')
    for k in range(70):
        place(y, rng.uniform(0.15, d - 0.2), drum('clap')[:S(0.08)] * 0.15, rng.uniform(0.2, 1.0))
    for k in range(2):
        tt0 = rng.uniform(0.5, 1.8)
        m = S(0.5)
        place(y, tt0, osc_sine(sweep_curve(m, 1500, 2600) ** 1.0) * np.sin(np.pi * np.linspace(0, 1, m)) * 0.12)
    e = np.minimum(t / 0.5, 1) ** 2 * np.clip((d - t) / 0.9, 0, 1)
    return y * e


# ---- pickups / economy / feedback --------------------------------------------
def sfx_pickup():
    b = buf(0.24)
    place(b, 0, blip(1318.5, 1318.5, 0.06, 0.25, 0.04), 0.6)
    place(b, 0.06, blip(1975.5, 1975.5, 0.17, 0.25, 0.07), 0.6)
    return b


def _coin(f1, f2, gap=0.07, d=0.4):
    b = buf(d + gap)
    parts = ((1, 1, 0.12), (2.0, 0.3, 0.06), (3.0, 0.12, 0.03))
    place(b, 0, bell_tone(f1, 0.1, parts), 0.7)
    place(b, gap, bell_tone(f2, d, ((1, 1, 0.22), (2.0, 0.3, 0.1), (3.0, 0.12, 0.05))), 0.8)
    return b


def sfx_cash():
    return _coin(1975.5, 2637.0)


def sfx_cash_big():
    b = buf(1.0)
    rng = rng_for('cashbig')
    for k in range(7):
        place(b, k * 0.06 + rng.uniform(0, 0.015), _coin(rng.choice([1760, 1975.5, 2217.5]), 2637.0, 0.05, 0.25), 0.45)
    place(b, 0.45, _coin(2637.0, 3520.0, 0.08, 0.45), 0.8)
    return b


def sfx_purchase():
    b = buf(0.6)
    place(b, 0, crack(0.03, 2000, 8000, 0.005, 'reg'), 0.5)
    place(b, 0.03, wood_knock(0.08, 900, 'reg2'), 0.3)
    place(b, 0.08, _coin(1568.0, 2093.0, 0.08, 0.4), 0.9)
    place(b, 0.1, thump(0.15, 140, 80, 0.02, 0.04), 0.35)
    return b


def sfx_deny():
    b = buf(0.3)
    place(b, 0, blip(220, 220, 0.11, 0.5, 0.2), 0.5)
    place(b, 0.14, blip(185, 185, 0.15, 0.5, 0.2), 0.5)
    return filt(b, r_lp(3500, 1))


def sfx_eat():
    b = buf(0.48)
    for k, t0 in enumerate((0.0, 0.15, 0.3)):
        n = S(0.1)
        y = crack(0.1, 900, 5000, 0.025, 'eat%d' % k, 0.004) + 0.5 * thump(0.1, 220, 140, 0.01, 0.02)
        place(b, t0, crush(y, 14000), 1.0 - 0.15 * k)
    return b


def sfx_drink():
    b = buf(0.6)
    for k, t0 in enumerate((0.0, 0.19, 0.38)):
        n = S(0.13)
        t = secs(n)
        f = 260 + 300 * (t / 0.13) ** 0.7
        y = osc_sine(f) * np.sin(np.pi * t / 0.13) ** 2
        y += 0.2 * filt(_noise(n, 'drk%d' % k), r_bp(400, 1500)) * np.sin(np.pi * t / 0.13)
        place(b, t0, y, 0.8)
    return b


def _arp(freqs, step, d, inst='bell', gain=0.6):
    b = buf(d)
    for k, f in enumerate(freqs):
        if inst == 'bell':
            sig = bell_tone(f, min(0.6, d - k * step))
        else:
            sig = blip(f, f, min(0.25, d - k * step), 0.25, 0.1)
        place(b, k * step, sig, gain)
    return b


def sfx_heal():
    b = _arp([1046.5, 1318.5, 1568.0, 2093.0], 0.07, 0.9)
    nz = _noise(S(0.9), 'heal')
    b += 0.12 * filt(nz, r_bp(4000, 12000)) * np.sin(np.pi * np.linspace(0, 1, S(0.9))) ** 2
    return b


def sfx_level_up():
    notes = [523.3, 659.3, 784.0, 1046.5, 1318.5, 1568.0, 2093.0]
    b = _arp(notes, 0.06, 1.2, inst='pulse', gain=0.5)
    for f in (1046.5, 1318.5, 1568.0):
        place(b, 0.42, bell_tone(f, 0.75, ((1, 1, 0.35), (2.0, 0.25, 0.15))), 0.3)
    return b


def sfx_quest_update():
    b = buf(0.65)
    place(b, 0, bell_tone(783.99, 0.4, ((1, 1, 0.25), (2.0, 0.3, 0.1), (3.0, 0.1, 0.05))), 0.6)
    place(b, 0.12, bell_tone(1046.5, 0.5, ((1, 1, 0.3), (2.0, 0.3, 0.12), (3.0, 0.1, 0.05))), 0.7)
    return b


def sfx_quest_complete():
    b = buf(1.3)
    for k, f in enumerate((783.99, 987.77, 1174.66)):
        place(b, k * 0.1, bell_tone(f, 0.5), 0.55)
    for f in (1567.98, 1975.5, 2349.3):
        place(b, 0.32, bell_tone(f, 0.95, ((1, 1, 0.45), (2.0, 0.25, 0.18), (3.0, 0.08, 0.06))), 0.4)
    n = S(0.9)
    pad = (osc_saw(np.full(n, 392.0)) + osc_saw(np.full(n, 493.9)) + osc_saw(np.full(n, 587.3))) / 3
    pad = filt(pad, r_lp(2500, 1)) * np.sin(np.pi * np.linspace(0, 1, n) ** 0.6) ** 2
    place(b, 0.3, pad, 0.25)
    return b


def sfx_save():
    b = _arp([880.0, 1108.7, 1318.5, 1760.0], 0.09, 0.9, gain=0.5)
    n = S(0.8)
    pad = (osc_sine(np.full(n, 440.0)) + osc_sine(np.full(n, 659.3))) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    place(b, 0.05, pad, 0.18)
    return b


def sfx_boss_intro():
    d = 2.7
    b = buf(d)
    hit = 1.05
    rs = whoosh(hit, lambda u: 300 + 5000 * u ** 2, 1.4, 'riser', lambda tt: tt ** 2.5)
    place(b, 0, rs, 0.55)
    place(b, hit - 1.0, drum('crash_rev')[-S(1.0):], 0.35)
    place(b, hit, thump(1.4, 80, 32, 0.08, 0.5), 1.0)
    place(b, hit, crack(0.6, 300, 4000, 0.06, 'bi'), 0.5)
    n = S(d - hit)
    t = secs(n)
    brass = np.zeros(n)
    for f in (61.7, 123.5, 146.8, 185.0, 246.9):     # B minor cluster, low brass
        brass += osc_saw(f * (1 + 0.003 * np.sin(2 * np.pi * 5 * t)))
    brass = filt(brass, r_lp(1800, 2)) * np.minimum(t / 0.02, 1) * np.exp(-t / 0.7)
    place(b, hit, np.tanh(brass * 0.5), 0.7)
    gong = _metal(n, 110, (1, 1.48, 2.03, 2.71, 3.6), (1, 0.8, 0.6, 0.4, 0.25), (1.2, 0.9, 0.7, 0.5, 0.3), 'gong')
    place(b, hit, gong, 0.35)
    e = np.ones(len(b))
    e[-S(0.3):] = np.linspace(1, 0, S(0.3))
    return b * e


# ---- UI -----------------------------------------------------------------------
def sfx_ui_move():
    b = blip(1760, 1760, 0.045, 0.25, 0.012)
    return b + 0.5 * bell_tone(3520, 0.045, ((1, 1, 0.008),))


def sfx_ui_confirm():
    b = buf(0.11)
    place(b, 0, blip(1046.5, 1046.5, 0.04, 0.25, 0.03), 0.6)
    place(b, 0.04, blip(1568.0, 1568.0, 0.07, 0.25, 0.03), 0.6)
    return b


def sfx_ui_cancel():
    b = buf(0.1)
    place(b, 0, blip(784.0, 784.0, 0.04, 0.5, 0.03), 0.5)
    place(b, 0.04, blip(523.3, 523.3, 0.06, 0.5, 0.025), 0.5)
    return filt(b, r_lp(3000, 1))


def sfx_ui_open():
    return blip(520, 1250, 0.1, 0.25, 0.05)


def sfx_ui_close():
    return blip(1250, 520, 0.09, 0.25, 0.045)


def sfx_dialogue_blip():
    return blip(880, 830, 0.035, 0.5, 0.012)


def sfx_countdown_tick():
    b = buf(0.12)
    place(b, 0, drum('tick'), 0.6)
    place(b, 0, blip(1000, 1000, 0.08, 0.5, 0.03, wave='sine'), 0.5)
    return b


# ---- ambient loops (seamless: circular filtering, integer-cycle LFOs, wrapped events)
def _loop_noise(n, key, *resps):
    return filt(_noise(n, key), *resps, circular=True)


def _lfo(n, cycles, phase=0.0):
    return np.sin(2 * np.pi * cycles * np.arange(n) / n + phase)


def sfx_rain_loop():
    d = 10.0
    n = S(d)
    hiss = _loop_noise(n, 'rain', r_bp(500, 9000, 1), r_peak(3500, 3, 1.5))
    body = _loop_noise(n, 'rain2', r_bp(150, 900, 1))
    y = hiss * (0.85 + 0.15 * _lfo(n, 3) * _lfo(n, 7, 1.0)) + 0.45 * body * (0.8 + 0.2 * _lfo(n, 2, 0.5))
    rng = rng_for('drops')
    for k in range(260):
        m = S(rng.uniform(0.006, 0.02))
        f = rng.uniform(1800, 6000)
        drop_ = np.sin(2 * np.pi * f * secs(m)) * np.exp(-secs(m) / (m / SR / 4))
        place_wrap(y, int(rng.uniform(0, n)), drop_, rng.uniform(0.05, 0.35))
    for k in range(40):     # gutter drips
        m = S(0.05)
        f0 = rng.uniform(700, 1300)
        place_wrap(y, int(rng.uniform(0, n)), osc_sine(sweep_curve(m, f0, f0 * 1.6)) * env_exp(m, 0.015), rng.uniform(0.05, 0.15))
    return y


def sfx_street_loop():
    d = 10.0
    n = S(d)
    traffic = _loop_noise(n, 'traffic', r_bp(50, 600, 1)) * (0.7 + 0.3 * _lfo(n, 1) * _lfo(n, 3, 0.7))
    murmur = np.zeros(n)
    for k, (f1, f2) in enumerate(((550, 1100), (700, 1300), (480, 950))):
        nz = _loop_noise(n, 'mur%d' % k, r_peak(f1, 10, 0.6), r_peak(f2, 8, 0.6), r_bp(250, 3000, 1))
        syl = 0.5 + 0.5 * _lfo(n, 41 + 7 * k, k) * _lfo(n, 13 + 3 * k, 2 * k)
        murmur += nz * syl
    y = 1.0 * traffic + 0.18 * murmur
    rng = rng_for('cars')
    for k in range(3):     # passing cars (doppler-ish swell)
        m = S(3.0)
        t = secs(m)
        sw = np.exp(-((t - 1.5) / 0.7) ** 2)
        car = filt(_noise(m, 'car%d' % k), r_bp(80, 1500, 1)) * sw
        car += 0.3 * osc_saw(95 * (1.08 - 0.16 * (t / 3.0))) * sw
        place_wrap(y, int(rng.uniform(0, n)), filt(car, r_lp(1800)), rng.uniform(0.4, 0.7))
    m = S(0.5)
    horn = filt(osc_saw(np.full(m, 350.0)) + osc_saw(np.full(m, 440.0)), r_bp(300, 1500)) * np.sin(np.pi * np.linspace(0, 1, m)) ** 0.5
    place_wrap(y, S(6.3), horn, 0.06)
    return filt(y, r_lp(5000, 1), circular=True)


def sfx_industrial_loop():
    d = 10.0
    n = S(d)
    t = secs(n)
    hum = sum(a * np.sin(2 * np.pi * 60 * h * t) for h, a in ((1, 1.0), (2, 0.5), (3, 0.35), (5, 0.15)))
    y = 0.25 * hum * (0.9 + 0.1 * _lfo(n, 2))
    y += 0.4 * _loop_noise(n, 'ind', r_bp(80, 2500, 1)) * (0.8 + 0.2 * _lfo(n, 5, 0.3))
    for k in range(8):          # press thump every 1.25 s
        p = S(k * 1.25)
        place_wrap(y, p, thump(0.5, 90, 40, 0.04, 0.12) + 0.4 * crack(0.5, 300, 3000, 0.03, 'pr%d' % (k % 2)), 0.9)
        place_wrap(y, p + S(0.62), drum('pipe') * 0.5, 0.25)
    for k in range(2):          # steam vents
        place_wrap(y, S(2.6 + 5.0 * k), drum('hiss'), 0.5)
    rng = rng_for('clinks')
    for k in range(10):
        place_wrap(y, int(rng.uniform(0, n)), drum('anvil') * 0.5, rng.uniform(0.04, 0.12))
    return y


def sfx_neon_buzz_loop():
    d = 6.0
    n = S(d)
    t = secs(n)
    buzz = osc_saw(np.full(n, 120.0))
    buzz = filt(buzz, r_bp(150, 3000, 1), r_peak(1200, 5, 1.0), circular=True)
    y = 0.6 * buzz * (0.85 + 0.15 * _lfo(n, 3) * _lfo(n, 11, 0.4))
    y += 0.08 * _loop_noise(n, 'nhiss', r_hp(3000))
    rng = rng_for('flicker')
    for k in range(9):          # flicker crackles
        m = S(rng.uniform(0.03, 0.12))
        cr = _noise(m, 'fl%d' % k) * (rng.random(m) > 0.7) * env_exp(m, m / SR / 2)
        place_wrap(y, int(rng.uniform(0, n)), filt(cr, r_bp(1000, 8000)), rng.uniform(0.2, 0.5))
    return y


# id -> (function, loudness target, description)
#   target: momentary-max LUFS for one-shots, integrated LUFS for loops
SFX = [
    ('punch_light', sfx_punch_light, -13, 'Light jab impact: low thump, noise crack, pitch drop'),
    ('punch_heavy', sfx_punch_heavy, -11, 'Heavy punch: deeper thump, sub boom, crunchy crack'),
    ('kick_light', sfx_kick_light, -13, 'Light kick impact with short air slap'),
    ('kick_heavy', sfx_kick_heavy, -11, 'Heavy kick: long low thump and crunch'),
    ('whiff', sfx_whiff, -18, 'Missed attack: band-passed noise sweep'),
    ('block', sfx_block, -15, 'Blocked hit: short leathery/metallic click'),
    ('perfect_guard', sfx_perfect_guard, -14, 'Perfect guard: bright ringing ping'),
    ('hurt_player', sfx_hurt_player, -14, 'Player hurt: gritty downward pitch blip (abstract, no voice)'),
    ('hurt_enemy', sfx_hurt_enemy, -15, 'Enemy hurt: lower, grittier downward blip'),
    ('fall', sfx_fall, -13, 'Body hits the ground with a small bounce'),
    ('land', sfx_land, -17, 'Landing from a jump: short thud with grit'),
    ('footstep_a', sfx_footstep_a, -24, 'Soft footstep scuff (variant A)'),
    ('footstep_b', sfx_footstep_b, -24, 'Soft footstep scuff (variant B)'),
    ('jump', sfx_jump, -18, 'Jump: rising chip blip with air'),
    ('pickup', sfx_pickup, -17, 'Item pickup: two quick rising chip notes'),
    ('drop', sfx_drop, -18, 'Item dropped: small thud and bounce'),
    ('cash', sfx_cash, -16, 'Money pickup: bright two-note coin chime'),
    ('cash_big', sfx_cash_big, -15, 'Big money pickup: coin cascade and final chime'),
    ('purchase', sfx_purchase, -15, 'Shop purchase: register click and chime'),
    ('deny', sfx_deny, -17, 'Not allowed / cannot afford: low two-note buzz'),
    ('eat', sfx_eat, -16, 'Eating: three crunchy bites'),
    ('drink', sfx_drink, -17, 'Drinking: three gulps'),
    ('heal', sfx_heal, -16, 'Health restored: rising sparkle arpeggio'),
    ('level_up', sfx_level_up, -14, 'Level up: rising pulse arpeggio with bell chord'),
    ('weapon_hit_blunt', sfx_weapon_hit_blunt, -12, 'Bat/pipe-wood blunt hit: thock and thump'),
    ('weapon_hit_metal', sfx_weapon_hit_metal, -12, 'Metal weapon hit: clang over impact'),
    ('weapon_hit_chain', sfx_weapon_hit_chain, -12, 'Chain hit: rattling links and impact'),
    ('weapon_swing', sfx_weapon_swing, -17, 'Heavy weapon swing whoosh'),
    ('throw', sfx_throw, -18, 'Throw release whoosh'),
    ('bottle_break', sfx_bottle_break, -13, 'Glass bottle shatter'),
    ('crate_break', sfx_crate_break, -12, 'Wooden crate smashed to splinters'),
    ('metal_clang', sfx_metal_clang, -13, 'Big ringing metal clang (barrels, poles)'),
    ('tire_bounce', sfx_tire_bounce, -14, 'Rubber tire bounce'),
    ('ui_move', sfx_ui_move, -22, 'Menu cursor move tick'),
    ('ui_confirm', sfx_ui_confirm, -20, 'Menu confirm: rising two-note blip'),
    ('ui_cancel', sfx_ui_cancel, -21, 'Menu cancel: falling two-note blip'),
    ('ui_open', sfx_ui_open, -21, 'Menu open: upward blip sweep'),
    ('ui_close', sfx_ui_close, -21, 'Menu close: downward blip sweep'),
    ('door', sfx_door, -16, 'Door: latch click, creak, close thump'),
    ('dialogue_blip', sfx_dialogue_blip, -24, 'Dialogue text blip (per character)'),
    ('quest_update', sfx_quest_update, -17, 'Quest updated: two-note chime'),
    ('quest_complete', sfx_quest_complete, -15, 'Quest complete: chime triad with warm swell'),
    ('boss_intro', sfx_boss_intro, -12, 'Boss intro: riser into low boom, brass cluster and gong'),
    ('ko', sfx_ko, -11, 'Knockout: heavy hit, boom, echoes and bell ring'),
    ('dizzy', sfx_dizzy, -19, 'Dizzy/stunned: warbling circling tones'),
    ('grab', sfx_grab, -17, 'Grab: cloth swish and soft thud'),
    ('slam', sfx_slam, -11, 'Body slam: very heavy thump and rumble'),
    ('shockwave', sfx_shockwave, -12, 'Shockwave: low boom with expanding whoosh'),
    ('whistle', sfx_whistle, -17, 'Trilling whistle (police/referee style)'),
    ('crate_fall', sfx_crate_fall, -14, 'Crate falls and lands with a bounce'),
    ('alarm', sfx_alarm, -17, 'Two-tone alarm siren'),
    ('dog_bark', sfx_dog_bark, -15, 'Stylized synth dog bark (two woofs)'),
    ('splash', sfx_splash, -15, 'Water splash with bubbles'),
    ('crowd_cheer', sfx_crowd_cheer, -16, 'Abstract crowd cheer swell with claps'),
    ('countdown_tick', sfx_countdown_tick, -19, 'Countdown tick beep'),
    ('bus_horn', sfx_bus_horn, -16, 'City bus horn honk'),
    ('save', sfx_save, -17, 'Game saved: soft rising chime'),
    ('guard_break', sfx_guard_break, -12, 'Guard broken: shatter, thump, falling tone'),
    ('charge', sfx_charge, -16, 'Charging power: rising tremolo sweep'),
    ('rain_loop', sfx_rain_loop, -26, 'Seamless rain ambience loop with drips'),
    ('street_loop', sfx_street_loop, -27, 'Seamless city ambience: distant traffic, murmur, passing cars'),
    ('industrial_loop', sfx_industrial_loop, -25, 'Seamless factory ambience: hum, press thumps, steam, clinks'),
    ('neon_buzz_loop', sfx_neon_buzz_loop, -28, 'Seamless neon-sign hum with flicker crackles'),
]
SFX_LOOPS = {'rain_loop', 'street_loop', 'industrial_loop', 'neon_buzz_loop'}


def master_sfx(x, target, loop=False):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    c = undb(-1.5)
    if loop:
        x = filt(x, r_hp(30, 2), circular=True)
        return normalize_loudness(x, target, -1.5, circular=True)
    x = fade(filt(x, r_hp(30, 2)), 0.0003, 0.008)
    g = 1.0
    for _ in range(4):
        pk = np.max(np.abs(x * g)) + 1e-12
        L = lufs_momentary_max(softclip(x * g, c))
        g *= undb(target - L)
        g = min(g, 1.25 * c / (np.max(np.abs(x)) + 1e-12))   # keep limiting gentle
        if abs(target - L) < 0.2:
            break
    return softclip(x * g, c)


# ===========================================================================
# build / verify / document
# ===========================================================================
MODE_NAMES = {MAJOR: 'major', MINOR: 'minor', HMINOR: 'harmonic minor', MIXO: 'mixolydian', DORIAN: 'dorian'}


def music_meta(fn):
    Song.dry = True
    try:
        s = fn()
    finally:
        Song.dry = False
    root, mode = s.key_name
    return {'bpm': s.bpm, 'bpm_nominal': s.bpm_nominal, 'bars': s.bars, 'loop': s.loop, 'step': s.step,
            'body': s.body, 'key': '%s %s' % (root, MODE_NAMES.get(mode, ''))}


def probe(path):
    out = subprocess.run([FFMPEG.replace('ffmpeg', 'ffprobe'), '-v', 'error', '-show_entries',
                          'stream=codec_name,sample_rate,channels,duration_ts:format=duration', '-of', 'default=nw=1',
                          path],
                         capture_output=True, text=True, check=True).stdout
    d = {}
    for line in out.split():
        k, _, v = line.partition('=')
        d[k] = v
    return d


def analyse(path, channels, loop):
    pr = probe(path)
    y = decode_ogg(path, channels)
    # The container's final granule position is the authoritative length (what Godot plays).
    # ffmpeg's ogg demuxer is sloppy about end trimming on very short single-page files,
    # so trim/measure against duration_ts rather than the raw decoded sample count.
    n = int(pr.get('duration_ts', len(y)))
    if loop and len(y) != n:
        raise RuntimeError('%s: decoded %d samples, container says %d' % (path, len(y), n))
    y = y[:n]
    yy = y if y.ndim == 2 else y[:, None]
    pk = float(np.max(np.abs(yy)))
    rms = float(np.sqrt(np.mean(yy ** 2)))
    L = lufs(y, circular=loop) if loop else lufs_momentary_max(y)
    seam = None
    if loop:
        jump = float(np.max(np.abs(yy[0] - yy[-1])))
        typ = float(np.percentile(np.abs(np.diff(yy, axis=0)), 99.0))
        seam = jump / max(typ, 1e-9)
    return {'codec': pr.get('codec_name'), 'sr': int(pr.get('sample_rate', 0)), 'ch': int(pr.get('channels', 0)),
            'samples': n, 'dur': n / SR, 'peak': db(pk), 'rms': db(rms), 'lufs': L,
            'seam': seam, 'bytes': os.path.getsize(path)}


def build(selected, do_music, do_sfx):
    t_all = __import__('time').time()
    if do_music:
        for mid, fn, _ in MUSIC:
            if selected and mid not in selected:
                continue
            t0 = __import__('time').time()
            s = fn()
            y = s.render()
            if s.loop:
                assert y.shape[0] == s.body, (mid, y.shape, s.body)
            write_ogg(os.path.join(MUSIC_DIR, mid + '.ogg'), y)
            print('music %-14s %6.2fs  %2d bars @ %.2f bpm  (%.1fs)' % (
                mid, y.shape[0] / SR, s.bars, s.bpm, __import__('time').time() - t0), flush=True)
    if do_sfx:
        for sid, fn, target, _ in SFX:
            if selected and sid not in selected:
                continue
            x = master_sfx(fn(), target, loop=sid in SFX_LOOPS)
            write_ogg(os.path.join(SFX_DIR, sid + '.ogg'), x)
            print('sfx   %-16s %5.2fs' % (sid, len(x) / SR), flush=True)
    print('build time %.1fs' % (__import__('time').time() - t_all))


def verify_and_document(write_doc=True):
    problems = []
    rows_m, rows_s = [], []
    for mid, fn, desc in MUSIC:
        path = os.path.join(MUSIC_DIR, mid + '.ogg')
        if not os.path.exists(path):
            problems.append('missing ' + path)
            continue
        meta = music_meta(fn)
        a = analyse(path, 2, meta['loop'])
        if a['ch'] != 2 or a['sr'] != SR or a['codec'] != 'vorbis':
            problems.append('%s: bad format %s' % (mid, a))
        if meta['loop']:
            bars = a['samples'] / (16 * meta['step'])
            if a['samples'] != meta['body'] or abs(bars - round(bars)) > 1e-9:
                problems.append('%s: loop length %d != %d (%.4f bars)' % (mid, a['samples'], meta['body'], bars))
            if a['seam'] > 3.0:
                problems.append('%s: loop seam jump %.2fx typical' % (mid, a['seam']))
        if a['peak'] > -1.0:
            problems.append('%s: peak %.2f dBFS' % (mid, a['peak']))
        rows_m.append((mid, desc, meta, a))
    for sid, fn, target, desc in SFX:
        path = os.path.join(SFX_DIR, sid + '.ogg')
        if not os.path.exists(path):
            problems.append('missing ' + path)
            continue
        loop = sid in SFX_LOOPS
        a = analyse(path, 1, loop)
        if a['ch'] != 1 or a['sr'] != SR or a['codec'] != 'vorbis':
            problems.append('%s: bad format %s' % (sid, a))
        lim = 3.0 if sid in ('boss_intro', 'crowd_cheer', 'alarm') else 1.5
        if not loop and a['dur'] > lim + 0.01:
            problems.append('%s: too long %.2fs' % (sid, a['dur']))
        if sid.startswith('ui_') and a['dur'] > 0.12:
            problems.append('%s: ui sound longer than 120 ms' % sid)
        if sid == 'dialogue_blip' and a['dur'] > 0.04:
            problems.append('dialogue_blip longer than 40 ms')
        if loop and a['seam'] > 3.0:
            problems.append('%s: loop seam jump %.2fx typical' % (sid, a['seam']))
        if a['peak'] > -1.0:
            problems.append('%s: peak %.2f dBFS' % (sid, a['peak']))
        rows_s.append((sid, desc, loop, a))

    total = sum(r[3]['bytes'] for r in rows_m) + sum(r[3]['bytes'] for r in rows_s)
    print('\n%-16s %7s %5s %6s %7s %7s %7s %6s %7s' % ('id', 'dur', 'loop', 'bars', 'peak', 'rms', 'lufs', 'seam', 'KB'))
    for mid, _, meta, a in rows_m:
        print('%-16s %7.2f %5s %6s %7.2f %7.2f %7.2f %6s %7.0f' % (
            mid, a['dur'], 'yes' if meta['loop'] else 'no', meta['bars'] if meta['loop'] else '-', a['peak'], a['rms'],
            a['lufs'], '%.2f' % a['seam'] if a['seam'] is not None else '-', a['bytes'] / 1024))
    for sid, _, loop, a in rows_s:
        print('%-16s %7.3f %5s %6s %7.2f %7.2f %7.2f %6s %7.0f' % (
            sid, a['dur'], 'yes' if loop else 'no', '-', a['peak'], a['rms'], a['lufs'],
            '%.2f' % a['seam'] if a['seam'] is not None else '-', a['bytes'] / 1024))
    print('\nfiles: %d music + %d sfx, total %.2f MB' % (len(rows_m), len(rows_s), total / 1048576.0))
    if problems:
        print('PROBLEMS:\n  ' + '\n  '.join(problems))
    else:
        print('all checks passed')
    if write_doc:
        write_docs(rows_m, rows_s, total, problems)
    return problems


def write_docs(rows_m, rows_s, total, problems):
    L = []
    L.append('# BACKSTREET OATH - Audio Assets\n')
    L.append('All music and sound effects are **%s**. No samples, recordings or third-party material are used; '
             'every melody is an original composition written for this game.\n' % ORIGIN)
    L.append('Rebuild everything with `python3 tools/audio/gen_audio.py` (Python 3 + numpy + ffmpeg/libvorbis). '
             'Output is deterministic. Use `--only id1,id2` to rebuild single assets and `--verify` to re-run the checks '
             'and regenerate this file.\n')
    L.append('## Format\n')
    L.append('- Music: `game/assets/audio/music/<id>.ogg`, Ogg Vorbis q%d, 44.1 kHz **stereo**.' % OGG_QUALITY)
    L.append('- SFX: `game/assets/audio/sfx/<id>.ogg`, Ogg Vorbis q%d, 44.1 kHz **mono**.' % OGG_QUALITY)
    L.append('- Looping music is an exact whole number of bars; the file length *is* the loop. In Godot import the looping '
             'files with **Loop = on, Loop Offset = 0** (AudioStreamOggVorbis `loop = true`). `victory` and `defeat` '
             'are one-shots. The four `*_loop` SFX also loop with offset 0.')
    L.append('- Seamless loops: the arrangement is rendered past the loop end and the tail is wrapped onto the start; '
             'echo, room reverb, EQ and limiting are applied circularly, so the last sample flows into the first.')
    L.append('- Levels: music is normalised to about -16 LUFS integrated (BS.1770 K-weighting; `safe_hub` -17, '
             '`setback`/`defeat` -18 for their quieter mood) with a soft limiter, peaks below -1 dBFS after encoding. '
             'One-shot SFX are normalised by momentary loudness per category (impacts loudest, UI and footsteps soft); '
             'ambient loops sit at -25..-28 LUFS so they can play under music.\n')
    L.append('Total size of all OGG files: **%.2f MB** (%d files).\n' % (total / 1048576.0, len(rows_m) + len(rows_s)))
    L.append('## Music\n')
    L.append('| id | file | duration | loop | bars | BPM | key | description | origin |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for mid, desc, meta, a in rows_m:
        L.append('| `%s` | `music/%s.ogg` | %.2f s | %s | %s | %.2f | %s | %s | %s |' % (
            mid, mid, a['dur'], 'yes' if meta['loop'] else 'no', meta['bars'] if meta['loop'] else '-',
            meta['bpm'], meta['key'], desc, ORIGIN))
    L.append('\nBPM values are exact: the 16th-note is a whole number of samples (nominal tempo nudged by < 0.3 %).\n')
    L.append('## Sound effects\n')
    L.append('| id | file | duration | loop | description | origin |')
    L.append('|---|---|---|---|---|---|')
    for sid, desc, loop, a in rows_s:
        L.append('| `%s` | `sfx/%s.ogg` | %.3f s | %s | %s | %s |' % (sid, sid, a['dur'], 'yes' if loop else 'no', desc, ORIGIN))
    L.append('\n## Level report (measured from the decoded OGG files)\n')
    L.append('Peak = sample peak dBFS, RMS = whole-file RMS dBFS, LUFS = integrated loudness for loops / '
             'max momentary (300 ms) loudness for one-shots, Seam = |last-first sample| jump divided by the '
             '99th-percentile sample-to-sample step (values around 1 or below mean the loop point is inaudible).\n')
    L.append('| id | type | peak dBFS | RMS dBFS | LUFS | seam | size KB |')
    L.append('|---|---|---|---|---|---|---|')
    for mid, _, meta, a in rows_m:
        L.append('| `%s` | music | %.2f | %.2f | %.1f | %s | %.0f |' % (
            mid, a['peak'], a['rms'], a['lufs'], '%.2f' % a['seam'] if a['seam'] is not None else '-', a['bytes'] / 1024))
    for sid, _, loop, a in rows_s:
        L.append('| `%s` | sfx | %.2f | %.2f | %.1f | %s | %.0f |' % (
            sid, a['peak'], a['rms'], a['lufs'], '%.2f' % a['seam'] if a['seam'] is not None else '-', a['bytes'] / 1024))
    L.append('\nVerification: %s\n' % ('all checks passed (format, channels, sample rate, whole-bar loop lengths, '
                                        'loop seams, peaks <= -1 dBFS, SFX length limits).' if not problems
                                        else 'issues: ' + '; '.join(problems)))
    os.makedirs(os.path.dirname(DOC_PATH), exist_ok=True)
    with open(DOC_PATH, 'w') as f:
        f.write('\n'.join(L))
    print('wrote', DOC_PATH)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--only', default='', help='comma separated asset ids')
    ap.add_argument('--music', action='store_true', help='music only')
    ap.add_argument('--sfx', action='store_true', help='sfx only')
    ap.add_argument('--verify', action='store_true', help='skip building; verify files and rewrite the doc')
    ap.add_argument('--no-doc', action='store_true', help='do not rewrite docs/assets/AUDIO_ASSETS.md')
    a = ap.parse_args()
    sel = set(x for x in a.only.split(',') if x)
    known = {m[0] for m in MUSIC} | {s_[0] for s_ in SFX}
    if sel - known:
        sys.exit('unknown ids: ' + ', '.join(sorted(sel - known)))
    if not a.verify:
        do_m = not a.sfx or a.music
        do_s = not a.music or a.sfx
        build(sel, do_m, do_s)
    probs = verify_and_document(not a.no_doc)
    sys.exit(1 if probs else 0)


if __name__ == '__main__':
    main()
