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
    'ohat_chip': ('hats', 0.28, 0.15, 0.1), 'ride': ('cym', -0.3, 0.13, 0.12), 'crash': ('cym', -0.22, 0.24, 0.15),
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
        mix_into(self.buses[bus], self.pos(step), sig.astype(np.float32), gain)

    def note(self, bus, inst, step, dur, pitch, vel=1.0, gate=0.92, **over):
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
                mm = dia_shift(m, dia, *self.key) if dia else m
                self.note(bus, inst, bar * 16 + p, d, mm + transpose, vel * v, gate, **over)
        return length

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
    s.mel('harm', 'bell', 8, 'D6:16 | B5:16 | A5:16 | C#6:16 | B5:16 | D6:16 | E6:16 | C#6:16', vel=0.6)
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
    s.bus('kick', gain=0.55, verb=0.06)
    s.bus('lead', gain=1.7, echo=0.2, verb=0.2)
    s.bus('bass', gain=1.7, verb=0.03, lp=2200)
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
    s.bassline('bass', 'basssaw', 0, 8, [em1, em2, oth, oth, em1, em2, oth, end], octave=1)
    s.bassline('bass', 'basssaw', 8, 8, ['R-R.R-R.R-.O-5.R'] * 7 + [end], octave=1)
    s.bassline('bass', 'basssaw', 16, 4, ['R-..R-..R-..R-..', 'R-..R-..R-.bR-.b'], octave=1)
    s.bassline('bass', 'basssaw', 20, 8, [em1, em2, oth, oth, em1, em2, oth, end], octave=1)
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
    s.bassline('bass', 'bassp', 0, 32, ['R.r.R.r.R.r.R.r.', 'R.r.R.r.R.r.R.rA'], octave=1)
    s.bassline('bass', 'basssaw', 16, 8, ['R-------R-------'], octave=1, vel=0.6)
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
    for b in range(0, 44, 2 if True else 1):
        ch = s.chord_at(b * 16)
        s.note('timp', 'timp', b * 16, 8, 36 + ((ch['root'] - 0) % 12) + (0 if ch['root'] >= 4 else 12), 0.85)
    # bass
    drive = ['R.RoR.RoR.RoR.Ro', 'R.RoR.RoR.RoO.5A']
    s.bassline('bass', 'bassp', 4, 24, drive)
    s.bassline('bass', 'bassp', 36, 8, drive)
    s.bassline('bass', 'bass', 0, 4, ['R---------------'], octave=1)
    # drums
    g = {'kick': 'X..x..X.X..x..X.', 'snare': '....X.......X...', 'hat': 'xxoxxxoxxxoxxxox'}
    s.beat(0, 3, {'timpani' if False else 'tom_lo': 'x...............'})
    s.beat(3, 1, {'tom_lo': 'x.x.x.x.xxxxXXXX', 'crash_rev' if False else 'tom_mid': '........x.x.x.x.'})
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
    s = Song('setback', 76, 12, key=('G', HMINOR), echo=(6, 0.3), room=(1.9, 0.02), air=-3.5, target=-18.0)
    std_mix(s, lead_echo=0.25, bass_lp=900)
    s.chords(0, 'Gm Eb Cm D Gm Eb Am7b5 D Eb Cm Gm/D D7')
    s.mel('lead', 'flute', 0, SB_M)
    s.mel('harm', 'flute', 8, SB_M.split('|', 8)[-1], dia=-2, vel=0.5)
    s.arp('keys', 'epiano', 0, 12, '0121', rate=2, center=60, vel=0.75, gate=1.0)
    wide_pad(s, 'strings', 0, 12, 52, vel=0.6)
    s.bassline('bass', 'basswalk', 0, 12, ['R-------R-------', 'R-------5-------'], octave=1, vel=0.8, gate=0.98)
    s.beat(0, 12, {'heart': 'X.......X.......', 'tick': 'x.o.x.o.x.o.x.o.'}, vel=0.8)
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
    s.mel('keys', 'bell', 24, 'D6:16 | B5:16 | A5:16 | C#6:16 | B5:16 | D6:16 | E6:16 | C#6:16', vel=0.5)
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
