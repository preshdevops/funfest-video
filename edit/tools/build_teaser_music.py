#!/usr/bin/env python3
"""Cinematic trailer-style score for the type-only teaser. Built from scratch (no samples, no vocals).

Sound design, in the order you hear it: paper slaps for each poster + a heartbeat and a riser -> a sudden suck-out ->
three impacts on the 'ARE YOU READY' flashes -> tension strings, toms and a riser -> suck-out -> six word hits with
brass stabs, sub booms and a driving string ostinato (Am - F - G) -> suck-out -> one huge impact + major chord on 'STAY TUNED'.
Hall/room reverbs are convolution with synthetic impulse responses; master chain is EQ, compressor, limiter at about -14 LUFS.
Writes ../teaser_music.wav (stereo 44.1k)."""
import numpy as np, os, sys, subprocess
from scipy.signal import butter, sosfilt, lfilter, fftconvolve
import scipy.io.wavfile as wav
from pedalboard import Pedalboard, Compressor, Limiter, HighpassFilter, LowShelfFilter, HighShelfFilter, Gain
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import teaser_timing as T

SR = 44100; N = int(SR * T.DUR); rng = np.random.default_rng(21); B = T.SLICE_DUR; R = T.REVEAL
def tt(d): return np.arange(int(SR * d)) / SR
def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
def chord(ms): return [midi(m) for m in ms]

# ------------------------------------------------------------------ filters
def bw(x, fc, kind, order=4):
    return sosfilt(butter(order, np.clip(fc, 20, SR / 2 - 200) / (SR / 2), btype=kind, output="sos"), x, axis=0)
def band(x, lo, hi): return bw(bw(x, hi, "low", 3), lo, "high", 3)
def sweep(x, f0, f1, q=1.0, kind="lp", blk=128):
    """time-varying resonant biquad (RBJ cookbook); cutoff glides f0 -> f1 exponentially over the sound"""
    n = len(x); out = np.empty(n); zi = np.zeros(2); nb = (n + blk - 1) // blk
    for k in range(nb):
        i0, i1 = k * blk, min(n, (k + 1) * blk); f = f0 * (f1 / f0) ** ((k + 0.5) / nb)
        w0 = 2 * np.pi * min(f, SR * 0.45) / SR; al = np.sin(w0) / (2 * q); cw = np.cos(w0)
        b = {"lp": [(1 - cw) / 2, 1 - cw, (1 - cw) / 2], "bp": [al, 0, -al], "hp": [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]}[kind]
        a = [1 + al, -2 * cw, 1 - al]
        out[i0:i1], zi = lfilter(np.array(b) / a[0], np.array(a) / a[0], x[i0:i1], zi=zi)
    return out
def sweep2(x, *a, **k): return np.stack([sweep(x[:, c], *a, **k) for c in range(x.shape[1])], 1)

# ------------------------------------------------------------------ oscillators
def saw(f, n, ph0=0.0):
    f = np.broadcast_to(f, (n,)).astype(float); dt = f / SR; ph = (ph0 + np.cumsum(dt)) % 1.0; y = 2 * ph - 1
    m = ph < dt; x = ph[m] / dt[m]; y[m] -= (2 * x - x * x - 1)
    m = ph > 1 - dt; x = (ph[m] - 1) / dt[m]; y[m] -= (x * x + 2 * x + 1)
    return y
def ens(freqs, dur, voices=6, cents=10, vib=0.0, vib_delay=0.4):
    n = int(SR * dur); t = np.arange(n) / SR; y = np.zeros((n, 2))
    for f in freqs:
        for v in range(voices):
            d = (v / (voices - 1) - 0.5) * 2 * cents if voices > 1 else 0
            vv = 1 + vib * np.clip((t - vib_delay) / 0.8, 0, 1) * np.sin(2 * np.pi * (5.0 + 0.35 * v) * t + v)
            s = saw(f * 2 ** (d / 1200) * vv, n, rng.random()); p = v / (voices - 1) if voices > 1 else 0.5
            y[:, 0] += s * (1 - p); y[:, 1] += s * p
    return y / (len(freqs) * voices * 0.45)

# ------------------------------------------------------------------ sounds
def sub_boom(dur=2.6, f0=34.0, drop=60.0, tc=0.9):
    t = tt(dur); ph = 2 * np.pi * np.cumsum(f0 + drop * np.exp(-t * 16)) / SR
    return np.tanh(1.7 * np.sin(ph) * np.exp(-t / tc) * np.minimum(1, t / 0.003)) * 0.9 + 0.25 * np.sin(2 * ph) * np.exp(-t / (tc * 0.4))
def whump(dur=1.8):
    n = int(SR * dur); t = np.arange(n) / SR
    return sweep2(rng.standard_normal((n, 2)), 6500, 160, 0.9, "lp") * (np.exp(-t / 0.55) * np.minimum(1, t / 0.004))[:, None] * 0.9
def tom(f=90, dur=0.9, hard=1.0):
    t = tt(dur); body = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.2 * np.exp(-t * 45))) / SR) * np.exp(-t * 6.5)
    return np.tanh(1.3 * (body + band(rng.standard_normal(len(t)), 200, 2500) * np.exp(-t * 60) * 0.5 * hard))
def clap():
    n = int(SR * 0.35); t = np.arange(n) / SR; e = np.exp(-t * 14) * 0.35 * (t > 0.03)
    for dl in (0, 0.011, 0.022): m = t >= dl; e[m] += np.exp(-(t[m] - dl) * 180) * 0.6
    return band(rng.standard_normal(n), 900, 5000) * e
def snare():
    n = int(SR * 0.4); t = np.arange(n) / SR
    return np.tanh(np.sin(2 * np.pi * 185 * t * (1 + 0.25 * np.exp(-t * 50))) * np.exp(-t * 26) * 0.7 + band(rng.standard_normal(n), 1500, 9000) * np.exp(-t * 16) * 0.9)
def hat():
    n = int(SR * 0.07); return bw(rng.standard_normal(n), 7000, "high", 3) * np.exp(-np.arange(n) / SR * 70)
def slap():
    """a sheet of paper smacked onto a wall"""
    n = int(SR * 0.28); t = np.arange(n) / SR
    flap = band(rng.standard_normal(n), 1100, 7000) * np.exp(-t * 85); flut = band(rng.standard_normal(n), 350, 1800) * np.exp(-t * 30) * 0.35 * (t > 0.01)
    thump = np.sin(2 * np.pi * np.cumsum(120 - 45 * (1 - np.exp(-t * 60))) / SR) * np.exp(-t * 38) * 0.9
    return np.tanh(0.8 * (flap * 0.9 + flut + thump))
def glitch():
    n = int(SR * 0.04); x = np.repeat(rng.standard_normal(n // 24 + 1), 24)[:n]
    return band(x, 500, 9000) * np.exp(-np.arange(n) / SR * 55) * 0.5
def metal(f0=170, dur=3.2):
    t = tt(dur); y = np.zeros_like(t)
    for r, a, d in ((1, 1, 1.9), (2.76, .7, 1.4), (5.40, .5, 1.0), (8.93, .35, .7), (11.34, .25, .55)): y += a * np.sin(2 * np.pi * f0 * r * t + rng.random() * 6) * np.exp(-t / d)
    return (y * np.minimum(1, t / 0.002) + 0.3 * band(rng.standard_normal(len(t)), 3000, 9000) * np.exp(-t * 40)) * 0.35
def crash(dur=4.0):
    n = int(SR * dur); t = np.arange(n) / SR
    return np.stack([band(rng.standard_normal(n), 3000, 15000) for _ in range(2)], 1) * (np.exp(-t / 1.2) * np.minimum(1, t / 0.01))[:, None] * 0.6
def rev(x): return x[::-1].copy()
def riser(dur, f0=260, f1=9500):
    n = int(SR * dur); t = np.arange(n) / SR; u = t / dur
    y = sweep2(rng.standard_normal((n, 2)), f0, f1, 2.2, "bp") * (u ** 2.2 * 1.1)[:, None]
    sh = sweep(saw(180 * (8 ** u), n) * u ** 2.5 * 0.30, 500, 4200, 0.9, "lp"); y += np.stack([sh, sh], 1) * 0.7
    return y * np.minimum(1, (dur - t) / 0.01)[:, None]
def whoosh(dur=0.45):
    n = int(SR * dur); t = np.arange(n) / SR
    return sweep2(rng.standard_normal((n, 2)), 500, 5500, 1.6, "bp") * (np.sin(np.pi * t / dur) ** 1.6)[:, None] * 1.2
def spic(f, dur=0.2, bright=2600):
    y = ens([f], dur, voices=4, cents=9); t = tt(dur)
    return sweep2(y, bright, bright * 0.5, 0.8, "lp") * (np.minimum(1, t / 0.006) * np.exp(-t / 0.07))[:, None]
def brass(freqs, dur=1.0, peak=3800):
    y = ens(freqs, dur, voices=5, cents=7, vib=0.004); t = tt(dur)
    return sweep2(y, peak, peak * 0.18, 0.9, "lp") * (np.minimum(1, t / 0.02) * (0.45 + 0.55 * np.exp(-t * 3.2)) * np.minimum(1, (dur - t) / 0.15))[:, None]
def drone(freqs, dur, lp0, lp1, voices=6, vib=0.003):
    return sweep2(ens(freqs, dur, voices=voices, cents=12, vib=vib, vib_delay=1.0), lp0, lp1, 0.8, "lp")

# ------------------------------------------------------------------ buses + reverbs
BUS = {k: np.zeros((N, 2)) for k in ("dry", "room", "hall", "pad")}
def add(bus, sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i < 0 or i >= N: return
    sig = sig[: N - i]; a = (pan + 1) * np.pi / 4; g = np.array([np.cos(a), np.sin(a)]) * gain * 1.414
    BUS[bus][i:i + len(sig)] += (sig[:, None] * g) if sig.ndim == 1 else sig * g
def make_ir(rts, pre, seed):
    r = np.random.default_rng(seed); n = int(SR * (max(rts) + pre)); t = np.arange(n) / SR - pre; tp = np.clip(t, 0, None); ir = np.zeros((n, 2))
    for c in range(2):
        nz = r.standard_normal(n)
        sig = (bw(nz, 250, "low", 2) * np.exp(-6.9 * tp / rts[0]) + band(nz, 250, 3500) * np.exp(-6.9 * tp / rts[1]) + bw(nz, 3500, "high", 2) * 0.7 * np.exp(-6.9 * tp / rts[2])) * (t >= 0)
        for _ in range(14): sig[int((pre + r.uniform(0.004, 0.06)) * SR)] += r.uniform(0.3, 1.0) * r.choice([-2, 2])
        ir[:, c] = sig
    return ir / np.sqrt((ir ** 2).sum(0).mean())
def conv(x, ir): return np.stack([fftconvolve(x[:, c], ir[:, c])[:N] for c in range(2)], 1)

# ------------------------------------------------------------------ the score
def impact(t, size=1.0, metal_f=170):
    add("dry", sub_boom(2.6 * size + 0.4, 34, 60, 0.9 * size + 0.2), t, 0.9 * size)
    add("dry", tom(78, 1.0), t, 0.6 * size); add("hall", tom(78, 1.0), t, 0.3 * size); add("hall", whump(1.8), t, 0.5 * size)
    if size >= 0.7: add("dry", snare(), t, 0.35 * size)
    if size >= 0.8: add("hall", metal(metal_f), t, 0.45 * size); add("hall", crash(3.5), t, 0.35 * size)

# beat 1: posters (0 - 3.6)
add("pad", drone(chord([33, 40, 45]), 3.9, 180, 1400) * (np.linspace(0.12, 0.8, int(SR * 3.9)) ** 1.5)[:, None], 0.0, 0.55)
add("hall", sweep2(rng.standard_normal((int(SR * 3.6), 2)), 600, 5000, 1.0, "bp") * (np.linspace(0, 1, int(SR * 3.6)) ** 2 * 0.05)[:, None], 0.0)
for k, t in enumerate(T.POSTER_T):
    s = slap(); g = 0.5 + 0.5 * k / (len(T.POSTER_T) - 1); p = (-0.5 if k % 2 else 0.5) * 0.6
    add("dry", s, t, g, p); add("room", s, t, g * 0.8, p)
for t, g in ((2.0, 0.6), (2.18, 0.45), (2.62, 0.6), (2.80, 0.45), (3.24, 0.65), (3.42, 0.5)): add("dry", sub_boom(0.9, 38, 40, 0.22), t, g)
add("hall", riser(1.95), 1.6, 0.8); add("hall", rev(crash(1.6)), 3.56 - 1.6, 0.35)
GATES = [(3.555, 3.60)]
# beat 2: ARE YOU READY (3.6 - 6.3)
add("dry", glitch(), 3.60, 0.5); add("dry", glitch(), 4.00, 0.45)
impact(3.80, 0.6); impact(4.15, 0.8); add("hall", rev(whump(0.45)), 4.15 - 0.45, 0.4)
add("hall", rev(whump(0.45)), 4.45 - 0.45, 0.6); add("hall", rev(crash(0.6)), 4.45 - 0.6, 0.35); impact(4.45, 1.1, 150)
add("pad", drone(chord([33, 40, 45, 48]), 2.0, 700, 2600) * 1.0, 4.45, 0.6)
add("pad", ens([midi(69), midi(76)], 2.0, voices=5, cents=12, vib=0.006) * (np.linspace(0.1, 1, int(SR * 2.0)) ** 1.6)[:, None], 4.45, 0.20)
for k, nt in enumerate((45, 45, 48, 45, 52, 45)):
    t = 4.45 + 0.31 * k
    if t < 6.25: add("dry", spic(midi(nt)), t, 0.20 + 0.08 * k, -0.4 if k % 2 else 0.4); add("room", spic(midi(nt)), t, 0.2 + 0.05 * k)
add("hall", riser(1.8, 300, 9000), 4.5, 0.85)
t, gap = 5.55, 0.17
while t < 6.28:
    g = 0.2 + 0.7 * (t - 5.55) / 0.73; add("dry", tom(100, 0.5), t, g); add("hall", tom(100, 0.5), t, g * 0.5); gap = max(0.05, gap * 0.85); t += gap
GATES.append((T.READY_END + 0.03, T.SLICE_T0))
# beat 3: six word hits (6.4 - 10.12), Am - F - G
prog = [[45, 52, 57, 60, 64], [41, 48, 53, 57, 60], [43, 50, 55, 59, 62]]
for ci, ms in enumerate(prog):
    add("pad", drone(chord([ms[0] - 12, ms[0]]), 2 * B + 0.5, 500, 900), T.SLICE_T0 + ci * 2 * B, 0.5)
for i in range(6):
    ti = T.SLICE_T0 + i * B; ms = prog[i // 2]
    add("hall", brass(chord(ms), 1.0, 3800 + 200 * i), ti, 0.55 + 0.06 * i); add("dry", sub_boom(1.5, 36, 55, 0.5), ti, 0.8)
    add("dry", tom(85, 0.7), ti, 0.5); add("hall", whoosh(0.4), ti - 0.38, 0.55)
    if i % 2 == 1: add("dry", clap(), ti, 0.5); add("hall", clap(), ti, 0.3)
    for k in range(2):
        tk = ti + k * B / 2; step = i * 2 + k
        nt = [ms[0], ms[0], ms[1], ms[0], ms[2], ms[0], ms[1], ms[0]][step % 8]
        if tk < R - 0.12: add("dry", spic(midi(nt)), tk, 0.35 + 0.08 * i, -0.4 if step % 2 else 0.4); add("room", spic(midi(nt)), tk, 0.25)
    if i >= 1:
        for k in range(4): add("dry", hat(), ti + k * B / 4, 0.10 if k % 2 == 0 else 0.07, 0.3 if k % 2 else -0.3)
add("hall", riser(1.2, 400, 10000), R - 0.08 - 1.2, 0.8)
t, gap = R - B, 0.13
while t < R - 0.08:
    g = 0.25 + 0.65 * (t - (R - B)) / (B - 0.08); add("dry", tom(110, 0.45), t, g); add("hall", tom(110, 0.45), t, g * 0.5); gap = max(0.045, gap * 0.85); t += gap
GATES.append((R - 0.075, R))
# beat 4: STAY TUNED (10.12 -)
impact(R, 1.5, 190)
add("hall", brass(chord([45, 52, 57, 61, 64, 69]), 3.2, 5200), R, 0.75)
add("pad", drone(chord([57, 64, 69, 73, 76]), 3.5, 2500, 6500, voices=6, vib=0.004) * (np.minimum(1, tt(3.5) / 0.4))[:, None], R, 0.40)
for j in (1, 2): add("dry", sub_boom(1.2, 36, 50, 0.4), R + j * B, 0.35)

# ------------------------------------------------------------------ mix + master
HALL = make_ir((3.4, 2.8, 1.5), 0.02, 3); ROOM = make_ir((0.55, 0.45, 0.28), 0.008, 5)
mix = BUS["dry"] + BUS["pad"] + conv(BUS["hall"], HALL) * 0.55 + conv(BUS["room"], ROOM) * 0.5 + conv(BUS["pad"], HALL) * 0.35
t = np.arange(N) / SR; gate = np.ones(N)
for a, b in GATES: gate[(t > a) & (t < b)] = 0.0
gate = sosfilt(butter(2, 700 / (SR / 2), output="sos"), gate)
mix = mix * gate[:, None] * (np.minimum(1, t / 0.03) * np.clip((T.DUR - t) / 0.9, 0, 1))[:, None]
board = Pedalboard([HighpassFilter(30), LowShelfFilter(120, gain_db=1.5), HighShelfFilter(9000, gain_db=-2.0), Compressor(threshold_db=-19, ratio=2.2, attack_ms=20, release_ms=180)])
x = board(mix.T.astype(np.float32), SR).T
out = os.path.join(HERE, "..", "teaser_music.wav"); tmp = out + ".tmp.wav"
def save(a, path): wav.write(path, SR, (np.clip(a, -1, 1) * 32767).astype(np.int16))
x = x / max(1e-9, np.abs(x).max()) * 0.5; save(x, tmp)
rep = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
lufs = float([l for l in rep.splitlines() if l.strip().startswith("I:")][-1].split()[1])
y = Pedalboard([Gain(-14.0 - lufs), Limiter(threshold_db=-1.5, release_ms=150)])(x.T.astype(np.float32), SR).T
save(y, out); os.remove(tmp); print("teaser score ready: %.1fs, pre-master %.1f LUFS -> gain %+.1f dB, peak %.2f" % (T.DUR, lufs, -14.0 - lufs, np.abs(y).max()))
