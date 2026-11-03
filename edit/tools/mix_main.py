#!/usr/bin/env python3
"""Mix speakers + instrumental for the main video. Music rides ~16 dB under the speech (never louder than a fixed ceiling,
never fully silent), then the mix is set to about -14 LUFS. usage: mix_main.py voice.wav music.wav out.wav"""
import sys, subprocess, numpy as np, scipy.io.wavfile as w
from scipy.signal import lfilter
vp, mp, op = sys.argv[1:4]; SR = 44100
sr, v = w.read(vp); _, m = w.read(mp); assert sr == SR
v = v.astype(np.float64) / 32768; m = m.astype(np.float64) / 32768
N = min(len(v), len(m), int(52.94 * SR)); v, m = v[:N], m[:N]
v = np.vstack([np.zeros((int(0.04 * SR), 2)), v])[:N]     # voice track trails the picture by ~40 ms
def smooth(x, tc):
    a = np.exp(-1.0 / (tc * SR)); return lfilter([1 - a], [1, -a], x)
def env(x, tc): return np.sqrt(smooth(x.mean(1) ** 2, tc) + 1e-12)
ve = env(v, 0.25); ve = np.maximum(ve, np.convolve(ve, np.ones(int(0.6 * SR)) / int(0.6 * SR), "same"))   # hold through short gaps
me = env(m, 0.4)
target = np.clip(ve * 10 ** (-16 / 20), 10 ** (-54 / 20), 10 ** (-27 / 20))     # music rms target: 16 dB under voice, between -54 and -27 dBFS
g = np.clip(target / me, 0, 3); g = smooth(g, 0.15)
mix = v + m * g[:, None]
tmp = op + ".tmp.wav"; w.write(tmp, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", tmp, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
lufs = float([l for l in out.splitlines() if l.strip().startswith("I:")][-1].split()[1])
gain = 10 ** ((-14.0 - lufs) / 20); mix = np.tanh(mix * gain * 0.9) / np.tanh(0.9)           # gentle limiter
mix = mix / max(1.0, np.abs(mix).max() / 0.89)
w.write(op, SR, (mix * 32767).astype(np.int16)); print("measured %.1f LUFS before gain, applied %+.1f dB" % (lufs, 20 * np.log10(gain)))
db = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9); hop = int(SR * 0.25); gaps = []
for i in range(0, N - hop, hop):
    a, b = db(v[i:i + hop]), db((m * g[:, None])[i:i + hop])
    if a > -38: gaps.append(a - b)
print("speech windows", len(gaps), "| median voice-music gap %.1f dB | worst 10%% %.1f dB" % (np.median(gaps), np.percentile(gaps, 10)))
