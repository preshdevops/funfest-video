#!/usr/bin/env python3
"""Synthesize an original instrumental bed (no vocals, no samples): warm pads + electric piano,
sparse and rising until the reveal, then a full uplifting groove. Writes music_instrumental.wav."""
import numpy as np, os, sys
from scipy.signal import lfilter, fftconvolve
import scipy.io.wavfile as wav
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL

SR = 44100; DUR = 53.2
T_REV = TL.to_video(13.62)            # the reveal: card pop + "FUN FEST 1.0!"
BARS_PRE = 6
BAR = T_REV / BARS_PRE; BEAT = BAR / 4
N = int(SR * DUR); rng = np.random.default_rng(3)
L = np.zeros(N); R = np.zeros(N)

def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
def add(buf_pair, sig, t, pan=0.0, gain=1.0):
    i = int(t * SR)
    if i >= N: return
    sig = sig[: N - i]
    buf_pair[0][i:i + len(sig)] += sig * gain * (1 - max(pan, 0)); buf_pair[1][i:i + len(sig)] += sig * gain * (1 + min(pan, 0))
def lp(x, fc): a = np.exp(-2 * np.pi * fc / SR); return lfilter([1 - a], [1, -a], x)
def hp(x, fc): return x - lp(x, fc)

def epiano(f, dur=1.4, vel=1.0):
    t = np.arange(int(SR * dur)) / SR
    idx = 1.6 * np.exp(-t * 4.0) * vel
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t)) * np.exp(-t * 2.6)
    y += 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 9)  # tine
    return y * np.minimum(1, t / 0.004)
def pad(freqs, dur, att=0.6):
    t = np.arange(int(SR * dur)) / SR; y = np.zeros_like(t)
    for f in freqs:
        for det in (-0.004, 0.0, 0.004):
            ph = (f * (1 + det) * t) % 1.0; y += (2 * ph - 1)
    y = lp(y, 1100) / (len(freqs) * 3)
    env = np.minimum(1, t / att) * np.minimum(1, (dur - t) / 0.5)
    return y * env
def bass(f, dur):
    t = np.arange(int(SR * dur)) / SR
    y = np.tanh(1.6 * np.sin(2 * np.pi * f * t)) * np.exp(-t * 1.6)
    return y * np.minimum(1, t / 0.01)
def kick():
    t = np.arange(int(SR * 0.35)) / SR; f = 45 + 95 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
def clap():
    t = np.arange(int(SR * 0.22)) / SR; n = hp(rng.standard_normal(len(t)), 1200)
    return lp(n, 7000) * np.exp(-t * 22) * 0.6
def hat(open_=False):
    t = np.arange(int(SR * (0.25 if open_ else 0.06))) / SR
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * (14 if open_ else 70)) * 0.35
def swell(dur):
    t = np.arange(int(SR * dur)) / SR; n = rng.standard_normal(len(t))
    return hp(n, 2500) * (t / dur) ** 2.2 * 0.8

# chords: (bass root midi, [triad midi])
C = (36, [60, 64, 67]); G = (43, [59, 62, 67]); Am = (45, [60, 64, 69]); F = (41, [60, 65, 69]); Fa = (41, [57, 60, 65]); G7 = (43, [59, 62, 65, 67])
prog_pre = [C, G, Am, F, C, G7]                         # 6 bars of anticipation
prog_main = [C, G, Am, F]
total_bars = int((DUR - T_REV) / BAR) + 2
bars = [(i * BAR, prog_pre[i], 'pre') for i in range(BARS_PRE)]
bars += [(T_REV + k * BAR, prog_main[k % 4], 'main') for k in range(total_bars)]

PAD = [np.zeros(N), np.zeros(N)]; KEYS = [np.zeros(N), np.zeros(N)]; RHY = [np.zeros(N), np.zeros(N)]; LOW = [np.zeros(N), np.zeros(N)]
arp = [0, 2, 1, 2, 0, 2, 1, 2]
for bi, (t0, (root, tri), sect) in enumerate(bars):
    if t0 >= DUR: break
    add(PAD, pad([midi(m - 12) for m in tri] + [midi(tri[0] - 24)], BAR + 0.6), t0, 0, 0.5 if sect == 'pre' else 0.6)
    # electric piano arpeggio (eighths); softer + sparser before the reveal
    for k in range(8):
        if sect == 'pre' and (bi < 2 and k % 2): continue
        f = midi(tri[arp[k] % len(tri)] + (12 if k % 4 == 2 else 0))
        vel = (0.35 + 0.12 * bi / BARS_PRE) if sect == 'pre' else 0.7
        add(KEYS, epiano(f, 1.3, 0.8) * vel, t0 + k * BEAT / 2, (-0.35 if k % 2 else 0.35), 0.5)
    if sect == 'main' or bi >= 4:
        add(LOW, bass(midi(root), BEAT * 1.9), t0, 0, 0.9)
        add(LOW, bass(midi(root), BEAT * 1.4), t0 + 2 * BEAT, 0, 0.7)
        if sect == 'main': add(LOW, bass(midi(root + 12), BEAT * 0.8), t0 + 3.5 * BEAT, 0, 0.45)
    if sect == 'main':
        for b in range(4):
            if b in (0, 2): add(LOW, kick(), t0 + b * BEAT, 0, 0.9)
            if b in (1, 3): add(RHY, clap(), t0 + b * BEAT, 0.1, 0.5)
        for k in range(8): add(RHY, hat(k == 7), t0 + k * BEAT / 2, 0.25 if k % 2 else -0.25, 0.38 if k % 2 else 0.25)
        add(KEYS, epiano(midi(tri[0] + 12), 1.0, 1.0), t0, 0, 0.35)
    elif bi >= 4:   # building heartbeat kick in the last 2 bars before the reveal
        for b in range(4): add(LOW, kick(), t0 + b * BEAT, 0, 0.35 * (1 if bi == 5 else 0.6))
# riser into the reveal + crash on it
add(RHY, swell(2 * BAR * 0.9), T_REV - 2 * BAR * 0.9, 0, 0.55)
crash = hp(rng.standard_normal(int(SR * 2.4)), 4500) * np.exp(-np.arange(int(SR * 2.4)) / SR * 2.4)
add(RHY, crash, T_REV, 0, 0.45)
add(LOW, kick() * 1.0, T_REV, 0, 1.0)
# a silent beat right before the drop for impact
gap = (np.arange(N) / SR > T_REV - BEAT * 0.45) & (np.arange(N) / SR < T_REV)
for b in (LOW, KEYS): b[0][gap] *= 0.0; b[1][gap] *= 0.0

# reverb on pad + keys
ir_t = np.arange(int(SR * 1.8)) / SR
ir = [rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2) for _ in range(2)]
def verb(x, i): return fftconvolve(x, lp(ir[i], 5000) * 0.03)[:N]
for i in range(2):
    wet = verb(PAD[i], i) * 0.9 + verb(KEYS[i], i) * 1.0
    L_, R_ = (L, R)[i], None
mix = []
for i, bus in enumerate((L, R)):
    wet = verb(PAD[i], i) * 0.8 + verb(KEYS[i], i) * 0.9
    mix.append(PAD[i] * 0.9 + KEYS[i] * 1.0 + RHY[i] * 0.9 + LOW[i] * 1.0 + wet)
out = np.stack(mix, 1)
# fades: in 0.6s, out last 2.2s ; soft clip + normalise to -3 dBFS peak
t = np.arange(N) / SR
fade = np.minimum(1, t / 0.6) * np.clip((DUR - t) / 2.2, 0, 1)
out = np.tanh(out * 1.2) * fade[:, None]
out = out / np.abs(out).max() * 0.70
wav.write(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "music_instrumental.wav"), SR, (out * 32767).astype(np.int16))
print("music ready; reveal at %.2fs, bpm %.1f" % (T_REV, 60 / BEAT))
