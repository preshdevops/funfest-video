#!/usr/bin/env python3
"""Original instrumental for the teaser (no vocals, no samples), synthesized to match teaser_timing.py:
ticks per poster -> heartbeat + riser -> hits on each 'ARE YOU READY' flash -> slice groove (Am F G) -> drop on the reveal.
Writes ../teaser_music.wav (stereo 44.1k)."""
import numpy as np, os, sys
from scipy.signal import lfilter, fftconvolve
import scipy.io.wavfile as wav
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import teaser_timing as T

SR = 44100; N = int(SR * T.DUR); rng = np.random.default_rng(11); B = T.SLICE_DUR
def mk(): return [np.zeros(N), np.zeros(N)]
DR, LOW, PAD, KEYS, FX, BELL = mk(), mk(), mk(), mk(), mk(), mk()
def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
def tt(d): return np.arange(int(SR * d)) / SR
def add(bus, sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i < 0 or i >= N: return
    sig = sig[: N - i]; bus[0][i:i + len(sig)] += sig * gain * (1 - max(pan, 0)); bus[1][i:i + len(sig)] += sig * gain * (1 + min(pan, 0))
def lp(x, fc): a = np.exp(-2 * np.pi * fc / SR); return lfilter([1 - a], [1, -a], x)
def hp(x, fc): return x - lp(x, fc)

def tick(f):
    t = tt(0.06); return (np.sin(2 * np.pi * f * t) * np.exp(-t * 80) + 0.6 * hp(rng.standard_normal(len(t)), 3500) * np.exp(-t * 110)) * 0.7
def boom(dur=1.3):
    t = tt(dur); f = 38 + 90 * np.exp(-t * 7); y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6) + 0.35 * lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 12)
    return np.tanh(1.4 * y)
def kick():
    t = tt(0.35); f = 45 + 95 * np.exp(-t * 28); return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
def clap():
    t = tt(0.22); return lp(hp(rng.standard_normal(len(t)), 1200), 7000) * np.exp(-t * 22) * 0.6
def hat(open_=False):
    t = tt(0.25 if open_ else 0.06); return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * (14 if open_ else 70)) * 0.35
def snare():
    t = tt(0.2); return (0.7 * hp(rng.standard_normal(len(t)), 1500) * np.exp(-t * 20) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)) * 0.8
def riser(dur):
    t = tt(dur); u = t / dur; n = hp(rng.standard_normal(len(t)), 1800) * u ** 2.2
    s = np.sin(2 * np.pi * np.cumsum(300 * (8 ** u)) / SR) * u ** 2 * 0.25
    return (0.5 * n + s) * np.minimum(1, (dur - t) / 0.02)
def whoosh(dur=0.4):
    t = tt(dur); u = t / dur; e = np.sin(np.pi * u) ** 1.5
    return hp(lp(rng.standard_normal(len(t)), 6000), 600) * e * 0.5 + np.sin(2 * np.pi * np.cumsum(500 + 1800 * u) / SR) * e * 0.08
def crash(dur=3.0):
    t = tt(dur); return hp(rng.standard_normal(len(t)), 4500) * np.exp(-t * 1.7)
def epiano(f, dur=0.9, vel=1.0):
    t = tt(dur); y = np.sin(2 * np.pi * f * t + 1.6 * np.exp(-t * 4) * vel * np.sin(2 * np.pi * f * t)) * np.exp(-t * 2.6) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 9)
    return y * np.minimum(1, t / 0.004)
def bell(f, dur=1.8):
    t = tt(dur); return np.sin(2 * np.pi * f * t + 2.0 * np.exp(-t * 3) * np.sin(2 * np.pi * 3.5 * f * t)) * np.exp(-t * 2.2) * np.minimum(1, t / 0.002)
def pad(freqs, dur, att=0.6, cut=1100):
    t = tt(dur); y = np.zeros_like(t)
    for f in freqs:
        for det in (-0.004, 0.0, 0.004): y += (2 * ((f * (1 + det) * t) % 1.0) - 1)
    return lp(y, cut) / (len(freqs) * 3) * np.minimum(1, t / att) * np.minimum(1, (dur - t) / 0.4)
def bass(f, dur):
    t = tt(dur); return np.tanh(1.6 * np.sin(2 * np.pi * f * t)) * np.exp(-t * 1.6) * np.minimum(1, t / 0.01)
def roll(t0, t1, g0, g1, gap0=0.14):
    t, gap = t0, gap0
    while t < t1:
        add(DR, snare(), t, g0 + (g1 - g0) * (t - t0) / (t1 - t0)); gap = max(0.045, gap * 0.84); t += gap

# ---- beat 1 (0 - 3.6): ticks, rising drone, heartbeat
add(PAD, pad([midi(36), midi(43), midi(48)], 3.8, att=2.0, cut=700), 0.0, 0.55)
for k, t in enumerate(T.POSTER_T): add(FX, tick(700 + k * 90), t, 0.55, pan=(-0.3 if k % 2 else 0.3))
for t in (2.2, 2.45, 2.95, 3.2): add(DR, kick(), t, 0.5)
add(FX, riser(1.2), 2.4, 0.6)
# ---- beat 2 (3.6 - 6.3): hits on each flash, tension drone, rising pings, snare roll
add(PAD, pad([midi(33), midi(40), midi(45), midi(48)], 3.0, att=0.3, cut=800), 3.6, 0.6)
add(FX, boom(1.4), 3.62, 0.5)
for t, g, d in ((3.80, 0.7, 1.0), (4.15, 0.8, 1.2), (4.45, 1.0, 1.6)): add(FX, boom(d), t, g); add(DR, kick(), t, g)
add(FX, crash(1.6), 4.45, 0.35); add(FX, riser(1.8), 4.5, 0.8)
tt_, gap = 4.6, 0.34
for m in (69, 72, 76, 79, 81, 84, 88, 91):
    if tt_ > 6.2: break
    add(KEYS, epiano(midi(m), 0.8, 0.9), tt_, 0.45, pan=(0.35 if m % 2 else -0.35)); tt_ += gap; gap = max(0.12, gap * 0.8)
roll(5.75, 6.30, 0.35, 0.75)
# ---- beat 3 (6.4 - 10.12): slice groove on Am - F - G
chords = [(33, [57, 60, 64]), (29, [53, 57, 60]), (31, [55, 59, 62])]
for ci, (root, tri) in enumerate(chords):
    t0 = T.SLICE_T0 + ci * 2 * B
    add(PAD, pad([midi(m) for m in tri] + [midi(root + 12)], 2 * B + 0.3, att=0.15), t0, 0.5)
    for k in range(8): add(KEYS, epiano(midi(tri[[0, 1, 2, 1, 2, 1, 2, 1][k]] + 12), 0.8, 0.9), t0 + k * B / 4, 0.4, pan=(-0.35 if k % 2 else 0.35))
    for j in range(2): add(LOW, bass(midi(root), B * 0.9), t0 + j * B, 0.9); add(LOW, bass(midi(root + 12), B * 0.3), t0 + j * B + B / 2, 0.4)
for b in range(6):
    tb = T.SLICE_T0 + b * B
    add(FX, whoosh(0.4), tb - 0.12, 0.6)
    if b < 5: add(DR, kick(), tb, 0.9)
    if b % 2 == 1 and b < 5: add(DR, clap(), tb, 0.5, pan=0.1)
    for k in range(2): add(DR, hat(k == 1 and b % 2 == 1), tb + k * B / 2, 0.3, pan=(0.25 if k else -0.25))
add(FX, riser(2 * B), T.REVEAL - 2 * B, 0.7); roll(T.REVEAL - B, T.REVEAL - 0.04, 0.3, 0.8, 0.12)
# ---- beat 4: the drop on the reveal
R = T.REVEAL
add(DR, kick(), R, 1.0); add(FX, boom(2.2), R, 1.0); add(FX, crash(3.4), R, 0.5)
add(PAD, pad([midi(m) for m in (48, 52, 55, 60, 64, 67)], 3.7, att=0.05, cut=1500), R, 0.75)
for k, m in enumerate((84, 88, 91, 96, 91, 88, 96, 100)): add(BELL, bell(midi(m)), R + 0.12 + k * 0.11, 0.33, pan=(-0.4 if k % 2 else 0.4))
add(LOW, bass(midi(36), 1.3), R, 0.9)
for j in (1, 2): add(DR, kick(), R + j * B, 0.7); add(DR, clap(), R + j * B, 0.4)
for k, m in enumerate((72, 76, 79, 76, 72, 79)): add(KEYS, epiano(midi(m), 0.9, 0.8), R + 0.9 + k * 0.31, 0.3, pan=(0.3 if k % 2 else -0.3))

# ---- mix
ir_t = tt(1.8); ir = [rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2) for _ in range(2)]
def verb(x, i): return fftconvolve(x, lp(ir[i], 5000) * 0.03)[:N]
ch = []
for i in range(2):
    wet = verb(PAD[i], i) * 0.7 + verb(KEYS[i], i) * 0.9 + verb(BELL[i], i) * 1.1 + verb(FX[i], i) * 0.3
    ch.append(DR[i] + LOW[i] + PAD[i] * 0.9 + KEYS[i] + FX[i] + BELL[i] + wet)
out = np.stack(ch, 1); t = np.arange(N) / SR
gate = np.ones(N)
for a, b in ((T.READY_END + 0.03, T.SLICE_T0), (T.REVEAL - 0.07, T.REVEAL)): gate[(t > a) & (t < b)] = 0.0
gate = lp(gate, 600)
fade = np.minimum(1, t / 0.05) * np.clip((T.DUR - t) / 0.9, 0, 1)
x = out * gate[:, None]; x = x / np.percentile(np.abs(x), 99.5) * 0.9
out = np.tanh(x) * fade[:, None]; out = out / np.abs(out).max() * 0.89 * 10 ** (-4.1 / 20)   # about -14 LUFS, like the reference
wav.write(os.path.join(HERE, "..", "teaser_music.wav"), SR, (out * 32767).astype(np.int16)); print("teaser music ready", T.DUR, "s")
